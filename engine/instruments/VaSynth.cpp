#include "instruments/VaSynth.h"

#include "core/TempoMap.h"
#include "dsp/Dsp.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>

namespace as {
namespace va {
namespace {

using dsp::kPi;

constexpr int kMaxPoly = 32;             // polyphony limit
constexpr int kPool = kMaxPoly + 8;      // spare slots so stolen voices can fade out
constexpr int kMaxUni = 9;
constexpr int kCtl = 16;                 // control period in internal (oversampled) samples
constexpr int kHeld = 64;                // mono-mode note stack
constexpr int kMaxMods = 64;             // modulation matrix routings
constexpr int kMacros = 8;
constexpr float kVoiceGain = 0.4f;       // per-voice output scale: one note ~-19.5 dBFS RMS, 4-note chord ~-13.5
constexpr float kSqrt2 = 1.41421356237f;
constexpr float kPinkScale = 0.166f;     // pink RMS matched to white noise RMS within the audio band
constexpr double kCentToRatio = 0.000577622650466621;  // ln(2)/1200, small-angle cents -> ratio
constexpr float kLadderMaxFb = 4.2f;     // ladder feedback at resonance 1 (self-oscillation from ~0.95)
constexpr float kLadderComp = 0.45f;     // partial passband-loss compensation vs. feedback
constexpr float kLadderLevel = 0.8f;     // ladder input level (its transistor nonlinearity adds warmth)
constexpr float kSvfLevel = 0.45f;       // SVF input level (cleaner, SEM-like)
constexpr float kDriveDb = 24.0f;        // drive stage gain at filter.drive = 1
constexpr float kDbToLog2 = 0.166096404744f;  // log2(10) / 20: dB -> log2 of the gain
constexpr float kInv2Pi = 0.159154943092f;
// Automation smoothing: two cascaded one-poles (C1-continuous, so even big jumps are click-free while
// staying fast enough for gates and step modulation). 10-90 % = 3.36 x tau.
constexpr double kParamTau = 0.0018;     // continuous params (levels, cutoff, pitch, depths, mod amounts): ~6 ms
constexpr double kLevelTau = 0.0015;     // output level: ~5 ms
constexpr double kHpfTau = 0.002;        // global high-pass: ~7 ms
constexpr double kLfoTau = 0.0007;       // LFO jump de-click (phase restarts, square / S&H / saw edges): ~2.4 ms
constexpr double kNoteTau = 0.003;       // per-note values changing in a mono retrigger (velocity, random, key)

// ---------------------------------------------------------------------------------------------
// Parameters (enum order == spec order). The modulation matrix adds one automatable
// 'mod.<id|index>.amount' parameter per routing after these (see configure()).

enum P : int {
    kOsc1Wave, kOsc1Level, kOsc1Pw, kOsc1Semi, kOsc1Fine,
    kOsc2Wave, kOsc2Level, kOsc2Pw, kOsc2Semi, kOsc2Fine, kOsc2Sync, kOsc2Phase, kFm,
    kSubLevel, kSubOctave, kNoiseLevel, kNoiseColor, kNoiseStereo, kOscRetrig,
    kUnison, kUniDetune, kUniSpread, kDriftPitch, kDriftCutoff,
    kFilterType, kCutoff, kResonance, kDrive, kKeytrack, kFilterEnv, kFilterVel, kHpf,
    kAmpA, kAmpD, kAmpS, kAmpR, kAmpVel,
    kFenvA, kFenvD, kFenvS, kFenvR,
    kMacro1, kMacro2, kMacro3, kMacro4, kMacro5, kMacro6, kMacro7, kMacro8,
    kMods,
    kMode, kPolyphony, kGlide, kPitchbend, kLevel, kPan,
    kParamCount
};

// Continuous parameters smoothed at control rate (cutoff and envelope times in the log2 domain).
constexpr int kSmoothed[] = {
    kOsc1Level, kOsc1Pw, kOsc1Semi, kOsc1Fine, kOsc2Level, kOsc2Pw, kOsc2Semi, kOsc2Fine, kFm,
    kSubLevel, kNoiseLevel, kNoiseStereo, kUniDetune, kUniSpread, kDriftPitch, kDriftCutoff,
    kCutoff, kResonance, kDrive, kKeytrack, kFilterEnv, kFilterVel, kAmpVel,
    kMacro1, kMacro2, kMacro3, kMacro4, kMacro5, kMacro6, kMacro7, kMacro8,
    kPitchbend, kPan, kAmpA, kAmpD, kAmpR, kFenvA, kFenvD, kFenvR};
// Envelope times: a jump (release 20 s -> 1 ms while notes ring) glides, so the running stage speeds up
// over a few ms instead of cutting the note off within a fraction of a millisecond.
constexpr int kEnvTimes[] = {kAmpA, kAmpD, kAmpR, kFenvA, kFenvD, kFenvR};

// ---------------------------------------------------------------------------------------------
// Modulation matrix: destinations. Amount units per target; 'global' targets act after the voices
// and only take global sources (global LFOs, macros).

enum Tgt : int {
    kTPitch, kTOsc1Pitch, kTOsc2Pitch, kTOsc1Pw, kTOsc2Pw, kTOsc1Level, kTOsc2Level, kTSubLevel, kTNoiseLevel,
    kTCutoff, kTResonance, kTDrive, kTAmp, kTPan, kTDetune, kTFm, kTHpf,
    kTargetCount
};
struct TargetInfo {
    const char* name;
    float lo, hi;       // amount range
    const char* unit;
    bool global;
    const char* what;   // for the amount parameter's help text
};
constexpr TargetInfo kTargets[kTargetCount] = {
    {"pitch", -4800, 4800, "ct", false, "pitch of every oscillator and the sub, in cents"},
    {"osc1.pitch", -4800, 4800, "ct", false, "osc1 (and the sub) pitch in cents"},
    {"osc2.pitch", -4800, 4800, "ct", false, "osc2 pitch in cents"},
    {"osc1.pw", -0.9f, 0.9f, "", false, "osc1 pulse width (added to osc1.pw, kept in 0.02..0.98)"},
    {"osc2.pw", -0.9f, 0.9f, "", false, "osc2 pulse width (added to osc2.pw, kept in 0.02..0.98)"},
    {"osc1.level", -1, 1, "", false, "osc1 level (added to osc1.level, kept in 0..1)"},
    {"osc2.level", -1, 1, "", false, "osc2 level (added to osc2.level, kept in 0..1)"},
    {"sub.level", -1, 1, "", false, "sub level (added to sub.level, kept in 0..1)"},
    {"noise.level", -1, 1, "", false, "noise level (added to noise.level, kept in 0..1)"},
    {"cutoff", -10, 10, "oct", false, "filter cutoff in octaves"},
    {"resonance", -1, 1, "", false, "resonance (added to resonance, kept in 0..1)"},
    {"filter.drive", -1, 1, "", false, "filter drive (added to filter.drive, kept in 0..1)"},
    {"amp", -96, 24, "dB", false, "voice gain in dB (all amp routings add up; -96 = silent)"},
    {"pan", -2, 2, "", false, "voice pan (added to pan, kept in -1..1)"},
    {"unison.detune", -1, 1, "", false, "unison detune (added to unison.detune, kept in 0..1)"},
    {"fm", -10, 10, "rad", false, "osc2 -> osc1 phase-modulation index (added to fm, kept in 0..10)"},
    {"hpf", -10, 10, "oct", true, "global high-pass cutoff in octaves"},
};

std::vector<ParamSpec> buildSpecs() {
    const std::vector<std::string> waves{"saw", "square", "triangle", "sine"};
    std::vector<ParamSpec> s;
    auto add = [&](ParamSpec p) { s.push_back(std::move(p)); };

    add(choice("osc1.wave", waves, 0,
               "Oscillator 1 waveform: saw (bright; brass, strings, supersaw), square (hollow; width via osc1.pw), "
               "triangle (soft, flute-like), sine (pure, sub bass; the FM carrier, see fm)."));
    add(num("osc1.level", 0, 1, 1, "", "Oscillator 1 level into the filter (0 = off)."));
    add(num("osc1.pw", 0.05f, 0.95f, 0.5f, "",
            "Pulse width of osc1 square (0.5 = square, 0.1/0.9 = thin nasal pulse). PWM: a mods routing "
            "lfo -> osc1.pw."));
    add(num("osc1.semi", -24, 24, 0, "st", "Oscillator 1 transpose in semitones (-12 = one octave down)."));
    add(num("osc1.fine", -100, 100, 0, "ct", "Oscillator 1 fine tune in cents."));
    add(choice("osc2.wave", waves, 0, "Oscillator 2 waveform: saw | square | triangle | sine."));
    add(num("osc2.level", 0, 1, 0,  "",
            "Oscillator 2 level (0 = off). 0.6-1 with osc2.fine 5-12 ct = the classic fat two-oscillator analog sound."));
    add(num("osc2.pw", 0.05f, 0.95f, 0.5f, "", "Pulse width of osc2 square (0.5 = square)."));
    add(num("osc2.semi", -24, 24, 0, "st",
            "Oscillator 2 transpose in semitones (7 = fifth, 12 = octave up, -12 = octave down)."));
    add(num("osc2.fine", -100, 100, 0, "ct", "Oscillator 2 detune in cents against osc1 (4-12 = warm analog beating)."));
    add(toggle("osc2.sync", false,
               "Hard-sync osc2 to osc1 (osc2 restarts every osc1 cycle). Raise osc2.semi, or sweep it with a mods "
               "routing env -> osc2.pitch, for the screaming Prophet sync lead."));
    add(num("osc2.phase", 0, 1, 0, "",
            "Start phase of osc2 (0..1 of a cycle) when osc.retrig restarts the oscillators; 0.25-0.5 keeps osc1 and "
            "osc2 from peaking together on every attack (same pitch and wave: 0 = double; 0.5 = cancel for square / "
            "triangle / sine, an octave-up saw for saws).", false));
    add(num("fm", 0, 10, 0, "rad",
            "osc2 -> osc1 phase modulation index (DX7-style FM, pitch-stable): 0 = off, 0.5-2 warm/electric, 3-8 "
            "bells and clangs (ratio from osc2.semi/fine; osc2.level may stay 0: osc2 then only modulates). Needs "
            "osc1.wave sine. Envelope it with a mods routing env -> fm."));
    add(num("sub.level", 0, 1, 0, "", "Sub oscillator level: square one or two octaves below osc1 (bass weight)."));
    add(num("sub.octave", -2, -1, -1, "oct", "Sub oscillator octave, -1 or -2 (whole number).", false));
    add(num("noise.level", 0, 1, 0, "", "Noise level into the filter (breath, chiff, risers with cutoff automation)."));
    add(choice("noise.color", {"white", "pink"}, 0, "Noise colour: white (bright hiss) or pink (darker, fuller)."));
    add(num("noise.stereo", 0, 1, 0, "",
            "Stereo noise: 0 = the same noise on both sides (centred), 1 = independent left/right noise (wide "
            "risers, sweeps, breath); the filter then runs in stereo."));
    add(toggle("osc.retrig", false,
               "off = free-running analog oscillators (every note starts at a different phase); on = oscillators "
               "restart on each note for identical, punchy attacks (basses, plucks; osc2 at osc2.phase)."));

    add(num("unison", 1, 9, 1, "voices",
            "Oscillator copies stacked per note, 1..9 (whole number). 7 with unison.detune ~0.65 = JP-8000 supersaw. "
            "Loudness stays about constant; CPU grows with it.", false));
    add(num("unison.detune", 0, 1, 0.5f, "",
            "Unison detune, JP-8000 curve (fine at low values, steep near 1): 0.2 subtle chorus, 0.4-0.5 lush, "
            "0.6-0.75 classic supersaw (outer voices ~25-45 ct), 0.9+ extreme."));
    add(num("unison.spread", 0, 1, 0.7f, "", "Stereo width of the unison voices (0 = mono, 1 = full width)."));
    add(num("drift.pitch", 0, 50, 3, "ct",
            "Analog pitch drift: slow random wander of every oscillator in cents (0 = digital, 2-5 = vintage, "
            "10+ = wobbly/detuned tape feel)."));
    add(num("drift.cutoff", 0, 12, 0.5f, "st",
            "Analog voice-card spread: per-voice random cutoff offset plus slow wander, in semitones."));

    add(choice("filter.type", {"ladder", "lp12", "bp12", "hp12", "notch"}, 0,
               "ladder = 24 dB/oct transistor-ladder lowpass (Moog/Jupiter/Prophet; self-oscillates at resonance "
               "~0.95+); lp12 | bp12 | hp12 | notch = 12 dB/oct state-variable filter (Oberheim SEM-like, softer)."));
    add(num("cutoff", 20, 20000, 2500, "Hz",
            "Filter cutoff in Hz (at C4 when filter.keytrack > 0). Plus filter.env, key tracking, velocity and mods "
            "routings. Automate with 'exp' curves for sweeps."));
    add(num("resonance", 0, 1, 0.15f, "",
            "Filter resonance 0..1. The ladder thins the bass as it rises and self-oscillates above ~0.95."));
    add(num("filter.drive", 0, 1, 0.2f, "",
            "Overdrive of the mixer into the filter (Minimoog-style): 0 clean, 0.2-0.4 warm, 0.6-1 gritty/saturated. "
            "Loudness stays roughly constant; anti-aliased."));
    add(num("filter.keytrack", 0, 1, 0.3f, "",
            "Cutoff key tracking (0 = fixed, 1 = cutoff follows the note 1:1). Keeps high notes bright."));
    add(num("filter.env", -8, 8, 2, "oct",
            "Filter envelope amount in octaves (bipolar): 2-4 plucks/brass, 5+ zappy, negative = inverted sweep."));
    add(num("filter.velocity", 0, 4, 0.5f, "oct",
            "Velocity to cutoff: full velocity plays the set cutoff, softer notes are up to this many octaves darker."));
    add(num("hpf", 10, 4000, 10, "Hz",
            "Global 12 dB/oct high-pass after the voices (Juno HPF). 10 = off (DC/subsonic only); 150-400 thins pads "
            "so they sit above the bass."));

    add(num("amp.attack", 0.001f, 20, 0.005f, "s",
            "Amplitude attack in seconds (analog RC curve): 0.001-0.005 snappy, 0.3-1.5 pad swell."));
    add(num("amp.decay", 0.001f, 20, 0.5f, "s", "Amplitude decay in seconds towards amp.sustain (exponential, ~-60 dB time)."));
    add(num("amp.sustain", 0, 1, 0.8f, "", "Amplitude sustain level while held (0 = pluck/percussive: decays to silence)."));
    add(num("amp.release", 0.001f, 20, 0.3f, "s", "Amplitude release in seconds after note-off (exponential, ~-60 dB time)."));
    add(num("amp.velocity", 0, 1, 0.5f, "", "Velocity to loudness (0 = none, 1 = full range; soft notes quieter)."));
    add(num("fenv.attack", 0.001f, 20, 0.003f, "s", "Filter envelope attack in seconds."));
    add(num("fenv.decay", 0.001f, 20, 0.6f, "s",
            "Filter envelope decay in seconds (pluck 0.1-0.3, brass 0.3-0.8, slow sweep 2+)."));
    add(num("fenv.sustain", 0, 1, 0.3f, "", "Filter envelope sustain level 0..1."));
    add(num("fenv.release", 0.001f, 20, 0.4f, "s", "Filter envelope release in seconds."));

    for (int m = 1; m <= kMacros; ++m) {
        add(num("macro" + std::to_string(m), 0, 1, 0, "",
                "Macro " + std::to_string(m) + " (0..1): the value of every mods source {\"type\": \"macro\", \"index\": " +
                    std::to_string(m) + "}. Automate / modulate 'instrument.macro" + std::to_string(m) +
                    "' to move all its routings at once (smoothed)."));
    }
    add(num("mods", 0, kMaxMods, 0, "list",
            "Modulation matrix - a list, not a number: [{\"source\": {...}, \"target\": T, \"amount\": x, \"id\": name}, "
            "...], up to 64 routings, each with its own source. Each amount is the automatable param "
            "mod.<id or index>.amount (smoothed ~5 ms; a flat 'mod.<id>.amount' key overrides the entry). Sources: "
            "lfo {shape sine / triangle / saw (falls) / ramp (rises) / square / samplehold / smoothrandom, rateHz or "
            "rateBeats, phase 0..1, delay s, fade s, mode voice (restarts per note) or global (free-running, on the song "
            "grid), unipolar} -1..1 (unipolar 0..1); env {attack, decay, sustain, release (s), curve exp or linear} 0..1 per "
            "note; velocity 0..1; key {low, high} octaves from A4 (with low/high MIDI notes: 0..1 across them); random "
            "{seed, unipolar} -1..1 per note; macro {index 1..8} 0..1. Targets (amount unit): pitch, osc1.pitch, "
            "osc2.pitch (ct); osc1.pw, osc2.pw; osc1.level, osc2.level, sub.level, noise.level; cutoff (oct); "
            "resonance; filter.drive; amp (dB); pan; unison.detune; fm (rad); hpf (oct, global sources only). "
            "Python: agentsound.vamod; docs/COMPOSE_API.md 'VA modulation matrix'.",
            false));

    add(choice("mode", {"poly", "mono", "legato"}, 0,
               "poly = chords; mono = one voice, every note retriggers the envelopes; legato = one voice, overlapping "
               "notes continue without retrigger and glide (TB-303/SH-101 style)."));
    add(num("polyphony", 1, kMaxPoly, 16, "voices",
            "Max simultaneous notes in poly mode (whole number). Beyond it the oldest released, then oldest held, "
            "note is stolen with a short fade.", false));
    add(num("glide", 0, 10, 0, "s",
            "Portamento time in seconds (analog exponential). mono: every note glides from the previous one; legato: only "
            "overlapping notes; poly: each new note slides from the nearest pitch still sounding, else from the last "
            "note played (chord-to-chord slides)."));
    add(num("pitchbend", -24, 24, 0, "st", "Pitch bend in semitones (automate for bends and dives; smoothed)."));
    add(num("level", -60, 12, 0, "dB", "Output level in dB."));
    add(num("pan", -1, 1, 0, "", "Stereo pan, -1 left .. 1 right."));
    return s;
}

const std::vector<ParamSpec>& specs() {
    static const std::vector<ParamSpec> s = [] {
        auto v = buildSpecs();
        if (v.size() != static_cast<std::size_t>(kParamCount)) throw std::logic_error("va: spec table mismatch");
        return v;
    }();
    return s;
}

// ---------------------------------------------------------------------------------------------
// DSP helpers

// sin(2*pi*t) for t in [0,1): fold to |z| <= pi/2, Taylor series to z^11 (error < 6e-8).
inline float sin2pi(double t) noexcept {
    double x = t - 0.5;  // sin(2 pi t) = -sin(2 pi x)
    if (x > 0.25) x = 0.5 - x;
    else if (x < -0.25) x = -0.5 - x;
    const double z = 2.0 * kPi * x, z2 = z * z;
    const double s = z * (1 - z2 / 6 * (1 - z2 / 20 * (1 - z2 / 42 * (1 - z2 / 72 * (1 - z2 / 110)))));
    return static_cast<float>(-s);
}
inline float cos2pi(double t) noexcept { return sin2pi(t < 0.75 ? t + 0.25 : t - 0.75); }

// Pade approximant of tanh(x)/x (Teemu Voipio, "cheap non-linear zero-delay filters"); tends to 1/15.
inline float tanhXdX(float x) noexcept {
    const float a = x * x;
    return ((a + 105.0f) * a + 945.0f) / ((15.0f * a + 420.0f) * a + 945.0f);
}

// Transparent below 0 dBFS, soft knee above, never exceeds +6 dBFS (pathological dense chords only).
inline float safetyClip(float x) noexcept {
    const float a = std::fabs(x);
    return a <= 1.0f ? x : std::copysign(1.0f + std::tanh(a - 1.0f), x);
}

inline float clampFrac(double d) noexcept { return static_cast<float>(d < 0.0 ? 0.0 : (d > 0.99999 ? 0.99999 : d)); }

// Adam Szabo, "How to Emulate the Super Saw" (2010): JP-8000 detune knob -> detune factor.
inline double jpDetuneCurve(double x) noexcept {
    static constexpr double c[] = {10028.7312891634, -50818.8652045924, 111363.4808729368, -138150.6761080548,
                                   106649.6679158292, -53046.9642751875, 17019.9518580080,  -3425.0836591318,
                                   404.2703938388,    -24.1878824391,    0.6717417634,      0.0030115596};
    double r = 0.0;
    for (double k : c) r = r * x + k;
    return std::max(0.0, r - c[11]);
}

enum class Wave : int { Saw, Square, Triangle, Sine };

// 4-point band-limited step (BLEP) and ramp (BLAMP) residuals: the naive waveform convolved with a
// cubic B-spline (frequency response sinc^4, so images near the sample rate are ~ -50 dB before the
// harmonic roll-off). For an event d in [0,1) samples before the current sample n the residual
// touches n-2 .. n+1; with e = 1-d:  BLEP  n-2: q(d)   n-1: -p(e)  n: p(d)   n+1: -q(e)
//                                    BLAMP n-2: q2(d)  n-1: p2(e)  n: p2(d)  n+1: q2(e)
inline float blepP(float x) noexcept { return -0.5f + x * (2.0f / 3.0f + x * x * (-1.0f / 3.0f + x * 0.125f)); }
inline float blepQ(float x) noexcept { const float x2 = x * x; return x2 * x2 * (1.0f / 24.0f); }
inline float blampP(float x) noexcept {
    return 7.0f / 30.0f + x * (-0.5f + x * (1.0f / 3.0f + x * x * (-1.0f / 12.0f + x * (1.0f / 40.0f))));
}
inline float blampQ(float x) noexcept { const float x2 = x * x; return x2 * x2 * x * (1.0f / 120.0f); }

// Band-limited oscillator. Output runs two samples late so residuals can reach back to n-2.
struct Osc {
    double t = 0.0;                        // phase [0,1)
    float z1 = 0.0f, z2 = 0.0f, fut = 0.0f;  // samples n-1, n-2 (pending) and residual for n+1
    bool hi = true;                        // square: in the high half; triangle: in the rising half

    struct Res {
        float m2 = 0.0f, m1 = 0.0f, c = 0.0f, f = 0.0f;
        void step(float h, float d) noexcept {  // value jump h
            const float e = 1.0f - d;
            m2 += h * blepQ(d); m1 -= h * blepP(e); c += h * blepP(d); f -= h * blepQ(e);
        }
        void corner(float m, float d) noexcept {  // slope change m per sample
            const float e = 1.0f - d;
            m2 += m * blampQ(d); m1 += m * blampP(e); c += m * blampP(d); f += m * blampQ(e);
        }
    };

    float emit(float naive, const Res& r) noexcept {
        const float out = z2 + r.m2;
        z2 = z1 + r.m1;
        z1 = naive + fut + r.c;
        fut = r.f;
        return out;
    }

    template <Wave W>
    static float naive(double t, bool hi, float pw) noexcept {
        if constexpr (W == Wave::Saw) return static_cast<float>(2.0 * t - 1.0);
        else if constexpr (W == Wave::Square) return (hi ? 1.0f : -1.0f) + 1.0f - 2.0f * pw;  // DC-free for any width
        else if constexpr (W == Wave::Triangle) return static_cast<float>(hi ? 4.0 * t - 1.0 : 3.0 - 4.0 * t);
        else return sin2pi(t);
    }

    // Square falling edge at pw / triangle peak at 0.5, reached at phase ph (not wrapped), `extra`
    // samples before the current sample's own offset.
    template <Wave W>
    void midEdge(Res& r, double ph, double dt, float pw, float extra) noexcept {
        if constexpr (W == Wave::Square) {
            if (hi && ph >= pw) { r.step(-2.0f, clampFrac(extra + (ph - pw) / dt)); hi = false; }
        } else if constexpr (W == Wave::Triangle) {
            if (hi && ph >= 0.5) { r.corner(static_cast<float>(-8.0 * dt), clampFrac(extra + (ph - 0.5) / dt)); hi = false; }
        }
    }

    // Free-running step. wrapD >= 0 reports a phase wrap (sync source), else -1.
    template <Wave W>
    float tick(double dt, float pw, float& wrapD) noexcept {
        Res r;
        t += dt;
        wrapD = -1.0f;
        // Mid-cycle edge first (on the unwrapped phase): with a thin pulse at a high note the falling
        // edge and the wrap can both land in one sample, and neither may be skipped.
        midEdge<W>(r, t, dt, pw, 0.0f);
        if (t >= 1.0) {
            t -= 1.0;
            wrapD = clampFrac(t / dt);
            if constexpr (W == Wave::Saw) r.step(-2.0f, wrapD);
            else if constexpr (W == Wave::Square) { if (!hi) { r.step(2.0f, wrapD); hi = true; } }
            else if constexpr (W == Wave::Triangle) { if (!hi) { r.corner(static_cast<float>(8.0 * dt), wrapD); hi = true; } }
            midEdge<W>(r, t, dt, pw, 0.0f);  // pulse narrower than one sample: falls again right away
        }
        return emit(naive<W>(t, hi, pw), r);
    }

    // Slave step: syncD >= 0 means the master wrapped syncD samples ago -> reset phase to 0.
    template <Wave W>
    float tickSync(double dt, float pw, float syncD) noexcept {
        if (syncD < 0.0f) {
            float unused;
            return tick<W>(dt, pw, unused);
        }
        Res r;
        double tb = t + dt * (1.0 - syncD);  // phase at the reset instant
        // natural events between the previous sample and the reset
        midEdge<W>(r, tb, dt, pw, syncD);
        if (tb >= 1.0) {
            tb -= 1.0;
            const float dw = clampFrac(syncD + tb / dt);
            if constexpr (W == Wave::Saw) r.step(-2.0f, dw);
            else if constexpr (W == Wave::Square) { if (!hi) { r.step(2.0f, dw); hi = true; } }
            else if constexpr (W == Wave::Triangle) { if (!hi) { r.corner(static_cast<float>(8.0 * dt), dw); hi = true; } }
            midEdge<W>(r, tb, dt, pw, syncD);
        }
        // the reset itself: value jump and slope jump
        r.step(naive<W>(0.0, true, pw) - naive<W>(tb, hi, pw), syncD);
        if constexpr (W == Wave::Triangle) {
            if (!hi) r.corner(static_cast<float>(8.0 * dt), syncD);
        } else if constexpr (W == Wave::Sine) {
            r.corner(static_cast<float>(2.0 * kPi * dt) * (1.0f - cos2pi(tb)), syncD);
        }
        t = syncD * dt;
        hi = true;
        if constexpr (W == Wave::Square) {
            if (t >= pw) { r.step(-2.0f, clampFrac((t - pw) / dt)); hi = false; }
        }
        return emit(naive<W>(t, hi, pw), r);
    }
};

// One oscillator over a control sub-block, accumulating g * osc into x. wrap: sync positions
// (written by a free-running oscillator, read by a synced one).
template <Wave W, bool kSync>
void oscLoop(Osc& o, double& inc, double dinc, float pw, float dpw, float g, float dg, float* wrap, float* x,
             int len) noexcept {
    for (int n = 0; n < len; ++n) {
        inc += dinc; pw += dpw; g += dg;
        if constexpr (kSync) x[n] += g * o.tickSync<W>(inc, pw, wrap[n]);
        else x[n] += g * o.tick<W>(inc, pw, wrap[n]);
    }
}
template <bool kSync>
void oscRun(Wave w, Osc& o, double& inc, double dinc, float pw, float dpw, float g, float dg, float* wrap, float* x,
            int len) noexcept {
    switch (w) {
        case Wave::Saw: oscLoop<Wave::Saw, kSync>(o, inc, dinc, pw, dpw, g, dg, wrap, x, len); break;
        case Wave::Square: oscLoop<Wave::Square, kSync>(o, inc, dinc, pw, dpw, g, dg, wrap, x, len); break;
        case Wave::Triangle: oscLoop<Wave::Triangle, kSync>(o, inc, dinc, pw, dpw, g, dg, wrap, x, len); break;
        case Wave::Sine: oscLoop<Wave::Sine, kSync>(o, inc, dinc, pw, dpw, g, dg, wrap, x, len); break;
    }
}

// FM pair (DX7-style phase modulation of a sine osc1 by osc2): per sample the carrier's phase advances
// (its wraps still hard-sync osc2), osc2 runs (audible with g2, or only as the modulator) and the carrier
// is read at its phase + index * osc2 / 2 pi. The band-limited osc2 output is two samples late, a constant
// delay of the modulator that does not change the spectrum. The carrier's pitch stays exact at any index.
struct OscPairRamps {
    double inc1, dinc1, inc2, dinc2;
    float pw2, dpw2, g1, dg1, g2, dg2, fm, dfm;
};
template <Wave W2, bool kSync>
void fmLoop(Osc& o1, Osc& o2, OscPairRamps r, float* x, int len) noexcept {
    const Osc::Res none{};
    for (int n = 0; n < len; ++n) {
        r.inc1 += r.dinc1; r.inc2 += r.dinc2; r.pw2 += r.dpw2; r.g1 += r.dg1; r.g2 += r.dg2; r.fm += r.dfm;
        o1.t += r.inc1;
        float wrap = -1.0f;
        if (o1.t >= 1.0) {
            o1.t -= 1.0;
            wrap = clampFrac(o1.t / r.inc1);
        }
        float y2;
        if constexpr (kSync) {
            y2 = o2.tickSync<W2>(r.inc2, r.pw2, wrap);
        } else {
            float unused;
            y2 = o2.tick<W2>(r.inc2, r.pw2, unused);
        }
        double ph = o1.t + static_cast<double>(r.fm * kInv2Pi * y2);
        ph -= std::floor(ph);
        x[n] += r.g1 * o1.emit(sin2pi(ph), none) + r.g2 * y2;
    }
}
template <bool kSync>
void fmRun(Wave w2, Osc& o1, Osc& o2, const OscPairRamps& r, float* x, int len) noexcept {
    switch (w2) {
        case Wave::Saw: fmLoop<Wave::Saw, kSync>(o1, o2, r, x, len); break;
        case Wave::Square: fmLoop<Wave::Square, kSync>(o1, o2, r, x, len); break;
        case Wave::Triangle: fmLoop<Wave::Triangle, kSync>(o1, o2, r, x, len); break;
        case Wave::Sine: fmLoop<Wave::Sine, kSync>(o1, o2, r, x, len); break;
    }
}

// Transistor ladder, zero-delay feedback with per-stage tanh-like nonlinearities evaluated from the
// previous state ("cheap non-linear ZDF", T. Voipio / mystran, KVR 2012). f = tan(pi fc / fs), r = feedback.
struct Ladder {
    float s[4] = {0, 0, 0, 0};
    float zi = 0.0f;
    void reset() noexcept { s[0] = s[1] = s[2] = s[3] = zi = 0.0f; }
    float tick(float in, float f, float r) noexcept {
        const float ih = 0.5f * (in + zi);  // half-sample-delayed input for evaluating the nonlinearity
        zi = in;
        const float t0 = tanhXdX(ih - r * s[3]);
        const float t1 = tanhXdX(s[0]), t2 = tanhXdX(s[1]), t3 = tanhXdX(s[2]), t4 = tanhXdX(s[3]);
        const float g0 = 1.0f / (1.0f + f * t1), g1 = 1.0f / (1.0f + f * t2);
        const float g2 = 1.0f / (1.0f + f * t3), g3 = 1.0f / (1.0f + f * t4);
        const float f3 = f * t3 * g3, f2 = f * t2 * g2 * f3, f1 = f * t1 * g1 * f2, f0 = f * t0 * g0 * f1;
        const float y3 = (g3 * s[3] + f3 * g2 * s[2] + f2 * g1 * s[1] + f1 * g0 * s[0] + f0 * in) / (1.0f + r * f0);
        const float xx = t0 * (in - r * y3);
        const float y0 = t1 * g0 * (s[0] + f * xx);
        const float y1 = t2 * g1 * (s[1] + f * y0);
        const float y2 = t3 * g2 * (s[2] + f * y1);
        s[0] += 2.0f * f * (xx - y0);
        s[1] += 2.0f * f * (y0 - y1);
        s[2] += 2.0f * f * (y1 - y2);
        s[3] += 2.0f * f * (y2 - t4 * y3);
        return y3;
    }
    void flush() noexcept { for (float& x : s) x = dsp::flush(x); zi = dsp::flush(zi); }
};

// TPT state-variable filter (A. Simper / V. Zavalishin), g = tan(pi fc / fs), k = 1/Q.
// The band integrator is softly limited like a saturating OTA, which keeps high Q musical.
struct Svf {
    float ic1 = 0.0f, ic2 = 0.0f;
    void reset() noexcept { ic1 = ic2 = 0.0f; }
    float tick(float v0, float g, float k, float bpGain, int mode) noexcept {
        const float a1 = 1.0f / (1.0f + g * (g + k)), a2 = g * a1, a3 = g * a2;
        const float v3 = v0 - ic2;
        const float v1 = a1 * ic1 + a2 * v3;
        const float v2 = ic2 + a2 * ic1 + a3 * v3;
        ic1 = 3.0f * dsp::fastTanh((2.0f * v1 - ic1) * (1.0f / 3.0f));
        ic2 = 2.0f * v2 - ic2;
        switch (mode) {
            case 0: return v2;                  // lowpass
            case 1: return v1 * bpGain;         // bandpass
            case 2: return v0 - k * v1 - v2;    // highpass
            default: return v0 - k * v1;        // notch
        }
    }
    void flush() noexcept { ic1 = dsp::flush(ic1); ic2 = dsp::flush(ic2); }
};

// Linear TPT SVF high-pass, Butterworth (k = sqrt 2). Cutoff changes computed at control rate are
// interpolated per sample (stepping them every 16 samples would put small steps into the output).
struct HighPass {
    float ic1 = 0.0f, ic2 = 0.0f, a1 = 1.0f, a2 = 0.0f, a3 = 0.0f;
    float g = 0.0f, gTarget = 0.0f, gStep = 0.0f;
    int left = 0;
    static constexpr float kK = 1.41421356f;
    void set(float gNew) noexcept { g = gTarget = gNew; left = 0; derive(); }
    void glideTo(float gNew, int samples) noexcept {
        gTarget = gNew;
        gStep = (gNew - g) / static_cast<float>(samples);
        left = samples;
    }
    void derive() noexcept { a1 = 1.0f / (1.0f + g * (g + kK)); a2 = g * a1; a3 = g * a2; }
    void reset() noexcept { ic1 = ic2 = 0.0f; }
    float tick(float v0) noexcept {
        if (left > 0) {
            g = --left > 0 ? g + gStep : gTarget;
            derive();
        }
        const float v3 = v0 - ic2;
        const float v1 = a1 * ic1 + a2 * v3;
        const float v2 = ic2 + a2 * ic1 + a3 * v3;
        ic1 = 2.0f * v1 - ic1;
        ic2 = 2.0f * v2 - ic2;
        return v0 - kK * v1 - v2;
    }
    void flush() noexcept { ic1 = dsp::flush(ic1); ic2 = dsp::flush(ic2); }
};

// Drive stage: y = x / sqrt(1 + x^2) with first-order antiderivative anti-aliasing (ADAA,
// Parker et al. 2016). With F(x) = sqrt(1 + x^2):  (F(x) - F(x1)) / (x - x1) = (x + x1) / (F(x) + F(x1)),
// which needs no ill-conditioning guard. Cuts aliasing of a hard-driven saw by 20-40 dB.
struct DriveSat {
    float x1 = 0.0f, f1 = 1.0f;
    void reset() noexcept { x1 = 0.0f; f1 = 1.0f; }
    float tick(float x) noexcept {
        const float f = std::sqrt(1.0f + x * x);
        const float y = (x + x1) / (f + f1);
        x1 = x;
        f1 = f;
        return y;
    }
};

// Analog-style envelope: attack charges towards 1.3 (RC overshoot, concave), decay/release fall
// exponentially towards slightly past their target so they land in finite time (~-60 dB time).
struct EnvCoefs {
    float atkC = 0, atkB = 0, decC = 0, decB = 0, relC = 0, relB = 0, sus = 1, susC = 1;
    void set(double fs, int step, double a, double d, double s, double rel) noexcept {
        constexpr double kOver = 1.3, kRatio = 0.001;
        const double lr = std::log((1.0 + kRatio) / kRatio);
        atkC = static_cast<float>(std::exp(-step * std::log(kOver / (kOver - 1.0)) / (a * fs)));
        atkB = static_cast<float>(kOver * (1.0 - atkC));
        decC = static_cast<float>(std::exp(-step * lr / (d * fs)));
        decB = static_cast<float>((s - kRatio) * (1.0 - decC));
        relC = static_cast<float>(std::exp(-step * lr / (rel * fs)));
        relB = static_cast<float>(-kRatio * (1.0 - relC));
        sus = static_cast<float>(s);
        susC = static_cast<float>(1.0 - std::exp(-step / (kParamTau * fs)));  // sustain automation: ~6 ms
    }
};

struct Env {
    enum Stage : std::uint8_t { Idle, Attack, Decay, Sustain, Release };
    Stage st = Idle;
    float lv = 0.0f, s1 = 0.0f;  // level; first stage of the (two-pole) sustain-level smoothing
    void gateOn() noexcept { st = Attack; }
    void gateOff() noexcept { if (st != Idle) st = Release; }
    float tick(const EnvCoefs& c) noexcept {
        switch (st) {
            case Idle: break;
            case Attack:
                lv = c.atkB + lv * c.atkC;
                if (lv >= 1.0f) { lv = 1.0f; st = Decay; }
                break;
            case Decay:
                lv = c.decB + lv * c.decC;
                if (lv <= c.sus) { lv = std::max(lv, 0.0f); s1 = lv; st = Sustain; }
                break;
            case Sustain:  // follows sustain automation C1-smoothly
                s1 += (c.sus - s1) * c.susC;
                lv += (s1 - lv) * c.susC;
                break;
            case Release:
                lv = c.relB + lv * c.relC;
                if (lv <= 0.0f) { lv = 0.0f; st = Idle; }
                break;
        }
        return lv;
    }
};

// ---------------------------------------------------------------------------------------------
// Modulation matrix: sources

// Hash of a song-grid / per-note key -> uniform -1..1 (splitmix64 finaliser, then dsp::Rng). The random
// sources and the S&H / smooth-random LFO steps are functions of the song position, so a preview render
// draws exactly the values the full render has there.
inline std::uint64_t mix64(std::uint64_t h) noexcept {
    h ^= h >> 31;
    h *= 0x94D049BB133111EBull;
    h ^= h >> 29;
    h *= 0xBF58476D1CE4E5B9ull;
    h ^= h >> 32;
    return h;
}
inline float hashBipolar(std::uint64_t a, std::uint64_t b, std::uint64_t c, std::uint64_t d) noexcept {
    std::uint64_t h = mix64(a ^ 0x9E3779B97F4A7C15ull);
    h = mix64(h ^ (b * 0xD6E8FEB86659FD93ull));
    h = mix64(h ^ (c * 0xA0761D6478BD642Full));
    h = mix64(h ^ (d * 0xE7037ED1A0B428DBull));
    return dsp::Rng(h | 1u).bipolar();
}

enum class Src : std::uint8_t { Lfo, Env, Velocity, Key, Random, Macro };
enum class Shape : std::uint8_t { Sine, Triangle, Saw, Ramp, Square, SampleHold, SmoothRandom };
constexpr const char* kShapeNames[] = {"sine", "triangle", "saw", "ramp", "square", "samplehold", "smoothrandom"};
constexpr int kShapeCount = 7;

// LFO waveform at phase ph in [0,1). Phase 0: sine / triangle at 0 rising (peak at 1/4), saw falls from +1,
// ramp rises from -1, square is +1 for the first half. r0 / r1: this / the next cycle's random value.
inline float lfoWave(Shape sh, double ph, float r0, float r1) noexcept {
    switch (sh) {
        case Shape::Sine: return sin2pi(ph);
        case Shape::Triangle:
            return static_cast<float>(ph < 0.25 ? 4.0 * ph : (ph < 0.75 ? 2.0 - 4.0 * ph : 4.0 * ph - 4.0));
        case Shape::Saw: return static_cast<float>(1.0 - 2.0 * ph);
        case Shape::Ramp: return static_cast<float>(2.0 * ph - 1.0);
        case Shape::Square: return ph < 0.5 ? 1.0f : -1.0f;
        case Shape::SampleHold: return r0;
        case Shape::SmoothRandom: return r0 + (r1 - r0) * 0.5f * (1.0f - cos2pi(0.5 * ph));  // cosine glide
    }
    return 0.0f;
}

// One source definition. Identical definitions (same canonical key) share one instance per voice.
struct SourceDef {
    Src type = Src::Lfo;
    Shape shape = Shape::Sine;
    bool beats = false, global = false, unipolar = false, linear = false, keyRange = false;
    double rate = 1.0;                             // lfo: Hz, or beats per cycle when `beats`
    double phase = 0.0, delay = 0.0, fade = 0.0;   // lfo: start phase (cycles), per-note delay / fade-in (s)
    double a = 0.0, d = 0.3, s = 0.0, r = 0.3;     // env (s, level)
    double keyLo = 0.0, keyHi = 127.0;             // key range (MIDI notes)
    std::uint64_t seed = 0;                        // random stream
    int macro = 0;                                 // 0-based macro index
    std::string key, label;                        // canonical definition, short description
    // derived in prepare()
    double inc = 0.0, delayS = 0.0, fadeS = 0.0;   // cycles per internal sample, internal samples
    bool instant = false;                          // env attack shorter than one control period
    EnvCoefs ec;
    float linA = 1.0f, linD = 1.0f, linR = 1.0f;   // linear env: level steps per control period
    bool randomShape() const noexcept { return shape == Shape::SampleHold || shape == Shape::SmoothRandom; }
};

struct ModDef {
    int src = 0, target = 0, param = 0;  // param: index of its 'mod.<id|index>.amount' in the Params
};

// LFO de-click: only the discontinuities of an LFO are smoothed, not the LFO itself (smoothing the whole
// signal would also attenuate and delay fast LFOs: -5 dB at 200 Hz). A jump J of the raw value is moved
// into a residual that glides back to 0 through two one-poles (C1-continuous, ~2.4 ms 10-90 %); the
// output is raw + residual. For piecewise-constant shapes (square, S&H) this equals smoothing the signal;
// sine / triangle / smooth-random pass untouched, saw / ramp keep their slope and only lose the reset step.
struct Declick {
    float a = 0.0f, b = 0.0f;
    void reset() noexcept { a = b = 0.0f; }
    float step(float jump, float c) noexcept {  // returns the residual to add to the raw value
        a -= jump;
        b -= jump;
        a -= a * c;
        b += (a - b) * c;
        if (std::fabs(a) + std::fabs(b) < 1e-7f) a = b = 0.0f;  // (lands; no denormal tails)
        return b;
    }
};

// Discontinuity of an LFO's raw value (after the unipolar mapping) within one control period: the change
// minus its continuous part. `wrapped`: a new cycle began in this period.
inline float lfoJump(Shape sh, bool unipolar, bool wrapped, float raw, float prevRaw) noexcept {
    const float scale = unipolar ? 0.5f : 1.0f;
    switch (sh) {
        case Shape::Saw: return wrapped ? 2.0f * scale : 0.0f;    // -1 -> +1 reset
        case Shape::Ramp: return wrapped ? -2.0f * scale : 0.0f;  // +1 -> -1 reset
        case Shape::Square:
        case Shape::SampleHold: return raw - prevRaw;              // piecewise constant: every change is a step
        default: return 0.0f;                                      // continuous shapes
    }
}

// Per-voice state of one source instance.
struct SrcState {
    double ph = 0.0;              // voice LFO phase [0,1)
    std::int64_t cycle = 0;       // voice LFO cycles since the (re)trigger: keys the S&H / smooth-random values
    Env env;                      // env source (exp curve: EnvCoefs; linear: own steps, env.s1 = release step)
    float rnd = 0.0f;             // random source: this note's value
    float s1 = 0.0f, out = 0.0f;  // per-note values: two-pole smoother; `out` is what the routings read
    // LFO: de-click residual, last raw wave value, last value x delay/fade depth, last depth
    Declick dc;
    float prevRaw = 0.0f, prevX = 0.0f, prevDepth = 0.0f;
    bool restart = false;         // phase / delay restarted by a retrigger of a sounding voice: a jump
};

// Two cascaded one-poles, stepped once per call (C1-continuous glide, lands exactly on the target).
struct Smooth2 {
    float a = 0.0f, b = 0.0f;
    float next(float target, float c) noexcept {
        a += (target - a) * c;
        b += (a - b) * c;
        if (std::fabs(target - a) + std::fabs(target - b) < 1e-6f * (1.0f + std::fabs(target))) a = b = target;
        return b;
    }
    void snap(float v) noexcept { a = b = v; }
};

// Slow random wander: random targets every 0.15-0.5 s through two one-pole lowpasses.
struct Drift {
    float target = 0.0f, s1 = 0.0f, s2 = 0.0f;
    int count = 0;
    void init(dsp::Rng& rng) noexcept { target = s1 = s2 = rng.bipolar(); count = 0; }
    float tick(dsp::Rng& rng, float a, int minChunks, int rangeChunks) noexcept {
        if (--count <= 0) {
            target = rng.bipolar();
            count = minChunks + static_cast<int>(rng.uniform() * static_cast<float>(rangeChunks));
        }
        s1 += (target - s1) * a;
        s2 += (s1 - s2) * a;
        return s2;
    }
};

// 2x polyphase IIR halfband decimator (two allpass chains, 10 coefficients, O. Niemitalo / L. de Soras
// "hiir" design with transition 0.04): > 120 dB rejection above 0.27 fs, flat passband to 0.23 fs.
struct Halfband {
    static constexpr int kN = 10;
    static constexpr double kC[kN] = {0.026872581726589895, 0.10211979750762737, 0.21186457986634402,
                                      0.33896530820005222,  0.46822765324642385, 0.58941249499690829,
                                      0.69777813051993742,  0.79313125288556097, 0.87850905287240721,
                                      0.95921252955741709};
    double x1[kN] = {}, y1[kN] = {};
    void reset() noexcept { std::fill(x1, x1 + kN, 0.0); std::fill(y1, y1 + kN, 0.0); }
    float process(float older, float newer) noexcept {
        double p0 = newer, p1 = older;
        for (int i = 0; i < kN; i += 2) {
            const double y = kC[i] * (p0 - y1[i]) + x1[i];
            x1[i] = p0; y1[i] = y; p0 = y;
        }
        for (int i = 1; i < kN; i += 2) {
            const double y = kC[i] * (p1 - y1[i]) + x1[i];
            x1[i] = p1; y1[i] = y; p1 = y;
        }
        return static_cast<float>(0.5 * (p0 + p1));
    }
    void flush() noexcept {
        for (int i = 0; i < kN; ++i) {
            if (std::fabs(x1[i]) < 1e-30) x1[i] = 0.0;
            if (std::fabs(y1[i]) < 1e-30) y1[i] = 0.0;
        }
    }
};

struct Ramp {  // per-sample linear interpolation between control points
    float v = 0.0f, d = 0.0f;
    void to(float target, bool snap) noexcept {
        if (snap) { v = target; d = 0.0f; }
        else d = (target - v) * (1.0f / kCtl);
    }
    void adv(int n) noexcept { v += d * static_cast<float>(n); }
    bool zero() const noexcept { return v == 0.0f && d == 0.0f; }
};
struct RampD {
    double v = 0.0, d = 0.0;
    void to(double target, bool snap) noexcept {
        if (snap) { v = target; d = 0.0; }
        else d = (target - v) * (1.0 / kCtl);
    }
};

// ---------------------------------------------------------------------------------------------

class VaSynth final : public Instrument {
public:
    VaSynth() : params_(specs()) {}

    void configure(const json& params) override;
    // A changing tempo: tempo-synced LFOs (voice and global) follow the song's beats.
    void setTempoMap(const TempoMap& map) override { tempo_ = &map; }
    void prepare(const RenderContext& ctx) override;
    bool setParam(std::string_view name, float value) override { return params_.set(name, value); }
    void noteOn(int noteId, int pitch, float velocity) override;
    void noteOff(int noteId) override;
    void process(float* left, float* right, int frames) override;
    bool idle() const override {
        for (const auto& v : pool_) if (v.active) return false;
        return true;
    }
    // After configure() this includes one 'mod.<id|index>.amount' per modulation routing.
    const std::vector<ParamSpec>& paramSpecs() const override { return params_.specs(); }

private:
    struct Voice {
        bool active = false, released = false, killing = false, hasPitch = false, stereo = false;
        int noteId = -1, note = 60;
        float vel = 1.0f, velGain = 1.0f, velTarget = 1.0f, killGain = 1.0f, cutStatic = 0.0f;
        float panPos = 2.0f, panL = 1.0f, panR = 1.0f;  // cached pan law (panPos 2 = not computed yet)
        std::uint64_t onStamp = 0, offStamp = 0, lastUsed = 0;
        std::int64_t startClock = -1;        // sample clock at note start
        std::int64_t noteSample = 0;         // song sample of the last (re)trigger: keys the per-note random values
        double pitch = 60.0, target = 60.0;  // current (gliding) and target pitch, semitones
        std::int64_t age = 0;                // internal samples since (re)trigger, for LFO delay/fade
        Env amp, fenv;
        std::vector<SrcState> src;           // modulation sources, one per instance (sized in prepare)
        dsp::Rng rng{1};
        Drift drift1[kMaxUni], drift2[kMaxUni], driftCut;
        Osc o1[kMaxUni], o2[kMaxUni], sub;
        float pink[7] = {}, pink2[7] = {};
        DriveSat satL, satR;
        Ladder ladL, ladR;
        Svf svfL, svfR;
        RampD inc1[kMaxUni], inc2[kMaxUni], incSub;
        Ramp pw1, pw2, fco, gainL, gainR, g1, g2, gSub, gNoise, res, pre, bpg, fm;
    };
    struct Held { int id; int pitch; float vel; };

    float p(int i) const noexcept { return params_.get(i); }
    int ichoice(int i) const noexcept { return static_cast<int>(params_.get(i) + 0.5f); }

    void parseMods(const json& list, std::vector<ParamSpec>& specsOut);
    int parseSource(const json& j, const std::string& where, int modIndex);
    void refresh();
    void updateUnison(bool snap);
    void updateGlobals(bool snap);
    void updateEnvCoefs();
    void snapEnvTimes();
    void control();
    void evalGlobalSources(std::int64_t internalSample, bool snap);
    void controlVoice(Voice& v, bool snap);
    void evalMods(Voice& v, bool snap, std::int64_t age, float* T);
    void renderVoice(Voice& v, float* outL, float* outR, int len);
    void advanceGlobalRamps(int n);
    Voice& allocate();
    void startVoice(Voice& v, int id, int note, float vel, double fromPitch);
    void retrigger(Voice& v, float vel);
    void triggerMods(Voice& v, bool fresh);
    void releaseVoice(Voice& v);
    void resetOscPhases(Voice& v);
    void resonanceCoefs(float res, float& k, float& bpg, float& comp) const noexcept;
    void driveGains(float drive, float& pre, float& post) const noexcept;
    float velGainFor(float vel) const noexcept {
        const float a = sm_[kAmpVel];
        return 1.0f - a + a * vel * vel;
    }
    static float depthMul(const SourceDef& d, std::int64_t age) noexcept {
        if (d.delayS <= 0.0 && d.fadeS <= 0.0) return 1.0f;
        const double a = static_cast<double>(age) - d.delayS;
        if (a < 0.0) return 0.0f;
        if (d.fadeS <= 0.0) return 1.0f;
        return static_cast<float>(std::min(1.0, a / d.fadeS));
    }
    bool glideOn() const noexcept { return p(kGlide) > 0.0f; }
    bool noiseWide() const noexcept { return sm_[kNoiseStereo] > 1e-4f; }

    Params params_;
    unsigned seenVersion_ = ~0u;
    double fs_ = 48000.0, fsi_ = 96000.0, bpm_ = 120.0, hzToInc_ = 440.0 / 96000.0;
    float maxCutoff_ = 40000.0f, piOverFsi_ = 0.0f;
    int os_ = 2;

    std::array<Voice, kPool> pool_{};
    std::vector<float> mixL_, mixR_;
    Halfband hbL_, hbR_;
    HighPass hpL_, hpR_;
    Smooth2 hpLog_, level_;
    float hpLogApplied_ = 0.0f, hpA_ = 0.0f, levelC_ = 0.0f, hpLogMin_ = 2.3f, hpLogMax_ = 14.0f;
    bool hpFirst_ = true;
    dsp::Rng rng_{1};
    int ctlLeft_ = 0;
    std::uint64_t stamp_ = 0;
    std::int64_t clock_ = 0;  // output samples rendered so far
    // Song position: sample / internal (oversampled) sample of the render's first sample. Control periods
    // sit on an absolute grid (multiples of kCtl internal samples from the song start) and global LFOs take
    // their phase from it, so a preview render is phase-identical to the same span of a full render.
    std::int64_t startSample_ = 0, startInternal_ = 0;
    const TempoMap* tempo_ = nullptr;  // songs whose tempo changes: synced LFOs follow the beats
    double ctlBeatEnd_ = 0.0, ctlBeats_ = 0.0;  // tempo map: song beat at the end of the control period, its length
    double lastPitch_ = -1.0;

    // modulation matrix (built in configure)
    std::vector<SourceDef> srcs_;
    std::vector<ModDef> mods_;
    std::vector<float> amt_, amt1_;         // smoothed amounts (two one-poles) per routing
    // global sources: raw value of this period, its discontinuity, de-clicked value (global targets)
    std::vector<float> gRaw_, gJump_, gOut_;
    std::vector<Declick> gDc_;
    std::vector<std::int64_t> gCycle_;
    std::vector<int> hpfPos_;               // hpf routings: offsets (octaves) per control period of this block
    std::vector<float> hpfVal_;
    int hpfCount_ = 0;
    float hpfMod_ = 0.0f, hpfCur_ = 0.0f;
    bool used_[kTargetCount] = {};
    bool globalTargets_ = false, fmCarrier_ = false;
    std::uint64_t modSeed_ = 1;

    // derived from params (refresh)
    Wave w1_ = Wave::Saw, w2_ = Wave::Saw;
    bool sync_ = false, pink_ = false, oscRetrig_ = false;
    int ftype_ = 0, mode_ = 0, poly_ = 16, unison_ = 1;
    float subScale_ = 0.5f;
    std::int64_t ctlClock_ = 0;  // internal samples since the render start at the end of the current control period
    EnvCoefs ampC_, fenvC_;
    float glideC_ = 0.0f;
    float smC_ = 0.0f, lfoSmC_ = 0.0f, velC_ = 0.0f, noteC_ = 0.0f, driftA_ = 0.0f, killStep_ = 0.0f;
    int driftMin_ = 1, driftRange_ = 1;

    std::array<float, kParamCount> sm_{}, sm1_{}, tgt_{};  // smoothed value, first smoother stage, target
    float envApplied_[6] = {};  // smoothed envelope times the coefficients were computed from
    bool envDirty_ = true;

    float uniOff_[kMaxUni] = {}, uniPos_[kMaxUni] = {}, panTL_[kMaxUni] = {}, panTR_[kMaxUni] = {};
    double detRatio_[kMaxUni] = {};
    float lastDet_ = -1.0f, lastSpread_ = -1.0f;
    bool stereoUni_ = false;
    // per control period (global part of the per-voice filter / gain staging)
    float resG_ = 0.0f, bpgG_ = 1.0f, compG_ = 1.0f, preG_ = 0.5f, postG_ = 1.0f, mid_ = 1.0f;
    Ramp uPanL_[kMaxUni], uPanR_[kMaxUni], nsC_, nsD_;

    std::array<Held, kHeld> held_{};
    int heldCount_ = 0;
};

// ---------------------------------------------------------------------------------------------
// Configuration: plain params + the modulation matrix

std::string fmtNum(double x) {
    char b[32];
    std::snprintf(b, sizeof b, "%g", x);
    return b;
}

void VaSynth::configure(const json& params) {
    if (!params.is_null() && !params.is_object()) throw ConfigError("va: params must be a JSON object");
    srcs_.clear();
    mods_.clear();
    std::vector<ParamSpec> all = specs();
    if (params.is_object()) {
        const auto it = params.find("mods");
        if (it != params.end()) parseMods(*it, all);
    }
    params_ = Params(all);
    params_.configure(params, "va", {"mods"});  // (a flat 'mod.<id>.amount' key overrides the entry's amount)
    if (ichoice(kOsc1Wave) != static_cast<int>(Wave::Sine)) {
        // fm only acts on a sine osc1: elsewhere automating it would be silently ignored, so it is not
        // automatable (the renderer then rejects such a lane).
        ParamSpec& f = all[static_cast<std::size_t>(kFm)];
        f.automatable = false;
        f.help += " (Not automatable here: osc1.wave is not sine.)";
        params_ = Params(std::move(all));
        params_.configure(params, "va", {"mods"});
    }
    for (int i : {static_cast<int>(kUnison), static_cast<int>(kPolyphony), static_cast<int>(kSubOctave)}) {
        const float v = params_.get(i);
        if (v != std::round(v))
            throw ConfigError("va: '" + specs()[static_cast<std::size_t>(i)].name + "' must be a whole number");
    }
    std::fill(std::begin(used_), std::end(used_), false);
    globalTargets_ = false;
    for (const auto& m : mods_) {
        used_[m.target] = true;
        globalTargets_ = globalTargets_ || kTargets[m.target].global;
    }
    if ((p(kFm) > 0.0f || used_[kTFm]) && ichoice(kOsc1Wave) != static_cast<int>(Wave::Sine)) {
        throw ConfigError("va: 'fm' phase-modulates a sine carrier: set \"osc1.wave\": \"sine\" (osc2 is the modulator; "
                          "its ratio comes from osc2.semi / osc2.fine)");
    }
}

void VaSynth::parseMods(const json& list, std::vector<ParamSpec>& specsOut) {
    if (!list.is_array()) {
        throw ConfigError("va: 'mods' must be a list of routings [{\"source\": {\"type\": \"lfo\", ...}, \"target\": "
                          "\"cutoff\", \"amount\": 1.5, \"id\": \"wob\"}, ...]");
    }
    if (list.size() > static_cast<std::size_t>(kMaxMods)) {
        throw ConfigError("va: 'mods' has " + std::to_string(list.size()) + " routings; at most " +
                          std::to_string(kMaxMods));
    }
    std::string targets;
    for (int t = 0; t < kTargetCount; ++t) targets += (t ? ", " : "") + std::string(kTargets[t].name);
    std::vector<std::string> ids;
    for (std::size_t i = 0; i < list.size(); ++i) {
        const json& e = list[i];
        const std::string w = "va: mods[" + std::to_string(i) + "]";
        if (!e.is_object()) {
            throw ConfigError(w + " must be an object {\"source\": {...}, \"target\": \"cutoff\", \"amount\": 1.5, "
                                  "\"id\": \"name\"}");
        }
        for (auto it = e.begin(); it != e.end(); ++it) {
            const std::string& k = it.key();
            if (k != "source" && k != "target" && k != "amount" && k != "id")
                throw ConfigError(w + ": unknown key '" + k + "' (keys: source, target, amount, id)");
        }
        for (const char* k : {"source", "target", "amount"})
            if (!e.contains(k)) throw ConfigError(w + ": missing '" + k + "'");
        std::string id;
        if (e.contains("id")) {
            const json& ij = e.at("id");
            bool ok = ij.is_string();
            if (ok) {
                id = ij.get<std::string>();
                ok = !id.empty() && id.size() <= 32 && id[0] >= 'a' && id[0] <= 'z';
                for (char c : id) ok = ok && ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_');
            }
            if (!ok) throw ConfigError(w + ": 'id' must be a lowercase name like \"vib\" or \"pwm_1\" (a-z, 0-9, _)");
            if (std::find(ids.begin(), ids.end(), id) != ids.end())
                throw ConfigError(w + ": id '" + id + "' is used twice (ids name the automatable 'mod.<id>.amount')");
            ids.push_back(id);
        }
        const json& tj = e.at("target");
        int t = -1;
        if (tj.is_string()) {
            const std::string tn = tj.get<std::string>();
            for (int k = 0; k < kTargetCount; ++k)
                if (tn == kTargets[k].name) t = k;
            if (t < 0) throw ConfigError(w + ": unknown target '" + tn + "' (targets: " + targets + ")");
        } else {
            throw ConfigError(w + ": 'target' must be a string (" + targets + ")");
        }
        const TargetInfo& ti = kTargets[t];
        const json& aj = e.at("amount");
        const std::string range = fmtNum(ti.lo) + ".." + fmtNum(ti.hi) + (*ti.unit ? std::string(" ") + ti.unit : "");
        if (!aj.is_number()) throw ConfigError(w + ": 'amount' must be a number (" + ti.name + ": " + range + ")");
        const double ad = aj.get<double>();
        const float amount = static_cast<float>(ad);
        if (!std::isfinite(ad) || amount < ti.lo || amount > ti.hi)
            throw ConfigError(w + ": amount " + fmtNum(ad) + " for '" + ti.name + "' is outside " + range);
        const int src = parseSource(e.at("source"), w + ".source", static_cast<int>(i));
        const SourceDef& sd = srcs_[static_cast<std::size_t>(src)];
        if (ti.global) {
            if (!((sd.type == Src::Lfo && sd.global) || sd.type == Src::Macro)) {
                throw ConfigError(w + ": '" + ti.name + "' acts after the voices (one filter for all notes), so it needs a "
                                  "global source: an lfo with \"mode\": \"global\" or a macro, not '" + sd.label + "'");
            }
            if (sd.delay > 0.0 || sd.fade > 0.0) {
                throw ConfigError(w + ": an lfo's delay / fade count from each note start; they can't drive the global '" +
                                  ti.name + "'");
            }
        }
        ModDef md;
        md.src = src;
        md.target = t;
        md.param = static_cast<int>(specsOut.size());
        mods_.push_back(md);
        const std::string label = id.empty() ? "#" + std::to_string(i) : "#" + std::to_string(i) + " '" + id + "'";
        specsOut.push_back(num("mod." + (id.empty() ? std::to_string(i) : id) + ".amount", ti.lo, ti.hi, amount, ti.unit,
                               "Amount of mods routing " + label + ": " + sd.label + " -> " + ti.name + " (" + ti.what +
                                   ", at full source). Automatable, smoothed ~5 ms."));
    }
}

int VaSynth::parseSource(const json& j, const std::string& w, int modIndex) {
    if (!j.is_object() || !j.contains("type") || !j.at("type").is_string())
        throw ConfigError(w + " must be an object with a \"type\": lfo | env | velocity | key | random | macro");
    const std::string type = j.at("type").get<std::string>();
    auto allow = [&](std::initializer_list<const char*> keys) {
        for (auto it = j.begin(); it != j.end(); ++it) {
            bool ok = it.key() == "type";
            for (const char* k : keys) ok = ok || it.key() == k;
            if (!ok) {
                std::string all = "type";
                for (const char* k : keys) all += std::string(", ") + k;
                throw ConfigError(w + ": unknown key '" + it.key() + "' for a " + type + " source (keys: " + all + ")");
            }
        }
    };
    auto number = [&](const char* k, double lo, double hi, double def) {
        if (!j.contains(k)) return def;
        const json& v = j.at(k);
        if (!v.is_number()) throw ConfigError(w + "." + k + " must be a number (" + fmtNum(lo) + ".." + fmtNum(hi) + ")");
        const double x = v.get<double>();
        if (!std::isfinite(x) || x < lo || x > hi)
            throw ConfigError(w + "." + k + " = " + fmtNum(x) + " is outside " + fmtNum(lo) + ".." + fmtNum(hi));
        return x;
    };
    auto whole = [&](const char* k, double x) {
        if (x != std::floor(x)) throw ConfigError(w + "." + k + " must be a whole number, got " + fmtNum(x));
        return x;
    };
    auto flag = [&](const char* k) {
        if (!j.contains(k)) return false;
        if (!j.at(k).is_boolean()) throw ConfigError(w + "." + k + " must be true or false");
        return j.at(k).get<bool>();
    };
    auto word = [&](const char* k, std::initializer_list<const char*> opts, int def) {
        if (!j.contains(k)) return def;
        std::string all;
        int idx = 0, found = -1;
        for (const char* o : opts) {
            all += (idx ? " | " : "") + std::string(o);
            if (j.at(k).is_string() && j.at(k).get<std::string>() == o) found = idx;
            ++idx;
        }
        if (found < 0) throw ConfigError(w + "." + k + " must be one of " + all);
        return found;
    };

    SourceDef d;
    char buf[256];
    if (type == "lfo") {
        allow({"shape", "rateHz", "rateBeats", "phase", "delay", "fade", "mode", "unipolar"});
        d.type = Src::Lfo;
        d.shape = static_cast<Shape>(word("shape", {"sine", "triangle", "saw", "ramp", "square", "samplehold", "smoothrandom"}, 0));
        const bool hz = j.contains("rateHz"), beats = j.contains("rateBeats");
        if (hz == beats) {
            throw ConfigError(w + ": give exactly one of \"rateHz\" (free-running, 0.001..200 Hz) or \"rateBeats\" "
                                  "(tempo-synced cycle length in beats: 0.5 = 1/8 note, 4 = one 4/4 bar)");
        }
        d.beats = beats;
        d.rate = hz ? number("rateHz", 0.001, 200.0, 1.0) : number("rateBeats", 1.0 / 1024.0, 1024.0, 1.0);
        d.phase = number("phase", 0.0, 1.0, 0.0);
        d.delay = number("delay", 0.0, 30.0, 0.0);
        d.fade = number("fade", 0.0, 30.0, 0.0);
        d.global = word("mode", {"voice", "global"}, 0) == 1;
        d.unipolar = flag("unipolar");
        std::snprintf(buf, sizeof buf, "lfo|%d|%c|%.9g|%.9g|%.9g|%.9g|%d|%d", static_cast<int>(d.shape), beats ? 'b' : 'h',
                      d.rate, d.phase, d.delay, d.fade, d.global ? 1 : 0, d.unipolar ? 1 : 0);
        d.key = buf;
        std::snprintf(buf, sizeof buf, "lfo %s %g %s%s%s", kShapeNames[static_cast<int>(d.shape)], d.rate,
                      beats ? "beats" : "Hz", d.global ? " global" : "", d.unipolar ? " unipolar" : "");
        d.label = buf;
    } else if (type == "env") {
        allow({"attack", "decay", "sustain", "release", "curve"});
        d.type = Src::Env;
        d.a = number("attack", 0.0, 30.0, 0.0);
        d.d = number("decay", 0.001, 30.0, 0.3);
        d.s = number("sustain", 0.0, 1.0, 0.0);
        d.r = number("release", 0.001, 30.0, 0.3);
        d.linear = word("curve", {"exp", "linear"}, 0) == 1;
        std::snprintf(buf, sizeof buf, "env|%.9g|%.9g|%.9g|%.9g|%d", d.a, d.d, d.s, d.r, d.linear ? 1 : 0);
        d.key = buf;
        std::snprintf(buf, sizeof buf, "env %g/%g/%g/%g%s", d.a, d.d, d.s, d.r, d.linear ? " linear" : "");
        d.label = buf;
    } else if (type == "velocity") {
        allow({});
        d.type = Src::Velocity;
        d.key = d.label = "velocity";
    } else if (type == "key") {
        allow({"low", "high"});
        d.type = Src::Key;
        const bool lo = j.contains("low"), hi = j.contains("high");
        if (lo != hi) {
            throw ConfigError(w + ": give both \"low\" and \"high\" (MIDI notes: the source is 0..1 across them) or "
                                  "neither (octaves from A4)");
        }
        d.keyRange = lo;
        if (lo) {
            d.keyLo = number("low", 0.0, 127.0, 0.0);
            d.keyHi = number("high", 0.0, 127.0, 127.0);
            if (!(d.keyHi > d.keyLo)) throw ConfigError(w + ": \"high\" must be above \"low\"");
        }
        std::snprintf(buf, sizeof buf, "key|%d|%.9g|%.9g", lo ? 1 : 0, d.keyLo, d.keyHi);
        d.key = buf;
        d.label = lo ? "key " + fmtNum(d.keyLo) + ".." + fmtNum(d.keyHi) : "key";
    } else if (type == "random") {
        allow({"seed", "unipolar"});
        d.type = Src::Random;
        d.unipolar = flag("unipolar");
        if (j.contains("seed")) {  // same seed = the same value per note (shared); no seed = its own stream
            d.seed = static_cast<std::uint64_t>(whole("seed", number("seed", 0.0, 1e9, 0.0)));
            std::snprintf(buf, sizeof buf, "random|s%llu|%d", static_cast<unsigned long long>(d.seed), d.unipolar ? 1 : 0);
        } else {
            d.seed = 0x100000000ull + static_cast<std::uint64_t>(modIndex);
            std::snprintf(buf, sizeof buf, "random|#%d|%d", modIndex, d.unipolar ? 1 : 0);
        }
        d.key = buf;
        d.label = d.unipolar ? "random unipolar" : "random";
    } else if (type == "macro") {
        allow({"index"});
        d.type = Src::Macro;
        if (!j.contains("index")) throw ConfigError(w + ": missing \"index\" (1..8: reads the param macroN)");
        d.macro = static_cast<int>(whole("index", number("index", 1.0, kMacros, 1.0))) - 1;
        d.key = d.label = "macro" + std::to_string(d.macro + 1);
    } else {
        throw ConfigError(w + ": unknown source type '" + type + "' (lfo | env | velocity | key | random | macro)");
    }
    for (std::size_t i = 0; i < srcs_.size(); ++i)
        if (srcs_[i].key == d.key) return static_cast<int>(i);
    srcs_.push_back(std::move(d));
    return static_cast<int>(srcs_.size()) - 1;
}

// ---------------------------------------------------------------------------------------------

void VaSynth::prepare(const RenderContext& ctx) {
    fs_ = ctx.sampleRate;
    os_ = fs_ < 80000.0 ? 2 : 1;  // oscillators + filters run at >= 88.2 kHz
    fsi_ = fs_ * os_;
    bpm_ = ctx.bpm;
    hzToInc_ = 440.0 / fsi_;
    maxCutoff_ = static_cast<float>(0.42 * fsi_);
    piOverFsi_ = static_cast<float>(kPi / fsi_);
    const int cap = std::max(1, ctx.maxBlock) * os_;
    mixL_.assign(static_cast<std::size_t>(cap), 0.0f);
    mixR_.assign(static_cast<std::size_t>(cap), 0.0f);

    smC_ = static_cast<float>(1.0 - std::exp(-kCtl / (kParamTau * fsi_)));
    lfoSmC_ = static_cast<float>(1.0 - std::exp(-kCtl / (kLfoTau * fsi_)));
    velC_ = static_cast<float>(1.0 - std::exp(-kCtl / (0.003 * fsi_)));
    noteC_ = static_cast<float>(1.0 - std::exp(-kCtl / (kNoteTau * fsi_)));
    driftA_ = static_cast<float>(1.0 - std::exp(-kCtl / (0.3 * fsi_)));
    driftMin_ = std::max(1, static_cast<int>(0.15 * fsi_ / kCtl));
    driftRange_ = std::max(1, static_cast<int>(0.35 * fsi_ / kCtl));
    killStep_ = static_cast<float>(1.0 / (0.005 * fsi_));
    hpA_ = static_cast<float>(1.0 - std::exp(-16.0 / (kHpfTau * fs_)));
    levelC_ = static_cast<float>(1.0 - std::exp(-1.0 / (kLevelTau * fs_)));
    hpLogMin_ = std::log2(5.0f);
    hpLogMax_ = static_cast<float>(std::log2(0.45 * fs_));

    rng_.reseed(ctx.seed ^ dsp::hashString("as.instrument.va"));
    modSeed_ = ctx.seed ^ dsp::hashString("as.instrument.va.mods");
    stamp_ = 0;
    clock_ = 0;
    // Song position (the renderer's rounding of startBeat to a sample). A render that does not start on
    // the absolute control grid begins with a partial control period, so every later control point
    // falls exactly where a full render has it.
    startSample_ = songStartSample(ctx.startBeat, fs_, ctx.bpm, tempo_);
    startInternal_ = startSample_ * os_;
    const int firstCtl = static_cast<int>((kCtl - startInternal_ % kCtl) % kCtl);
    ctlLeft_ = firstCtl;
    ctlClock_ = firstCtl;
    if (tempo_) ctlBeatEnd_ = tempo_->beatAtSample(static_cast<double>(startInternal_ + ctlClock_) / os_);
    ctlBeats_ = 0.0;
    lastPitch_ = -1.0;
    heldCount_ = 0;
    seenVersion_ = ~0u;

    // modulation sources: rates / times in internal samples and control periods
    for (auto& d : srcs_) {
        d.inc = d.type == Src::Lfo ? (d.beats ? bpm_ / 60.0 / d.rate : d.rate) / fsi_ : 0.0;
        d.delayS = d.delay * fsi_;
        d.fadeS = d.fade * fsi_;
        d.instant = d.a * fsi_ < kCtl;
        d.ec.set(fsi_, kCtl, std::max(d.a, 1e-4), d.d, d.s, d.r);
        d.linA = d.instant ? 1.0f : static_cast<float>(kCtl / (d.a * fsi_));
        d.linD = static_cast<float>((1.0 - d.s) * kCtl / (d.d * fsi_));
        d.linR = static_cast<float>(kCtl / (d.r * fsi_));
    }
    amt_.assign(mods_.size(), 0.0f);
    amt1_.assign(mods_.size(), 0.0f);
    for (std::size_t m = 0; m < mods_.size(); ++m) amt_[m] = amt1_[m] = p(mods_[m].param);
    gRaw_.assign(srcs_.size(), 0.0f);
    gJump_.assign(srcs_.size(), 0.0f);
    gOut_.assign(srcs_.size(), 0.0f);
    gDc_.assign(srcs_.size(), Declick{});
    gCycle_.assign(srcs_.size(), 0);
    hpfPos_.assign(static_cast<std::size_t>(cap / kCtl + 2), 0);
    hpfVal_.assign(static_cast<std::size_t>(cap / kCtl + 2), 0.0f);
    hpfCount_ = 0;
    hpfMod_ = hpfCur_ = 0.0f;

    refresh();
    for (int i : kSmoothed) sm_[static_cast<std::size_t>(i)] = sm1_[static_cast<std::size_t>(i)] = tgt_[static_cast<std::size_t>(i)];
    updateEnvCoefs();

    for (auto& v : pool_) {
        v = Voice{};
        v.src.assign(srcs_.size(), SrcState{});
        v.rng.reseed(rng_.next() | 1u);
        for (int u = 0; u < kMaxUni; ++u) {
            v.o1[u].t = v.rng.uniform();
            v.o2[u].t = v.rng.uniform();
            v.drift1[u].init(v.rng);
            v.drift2[u].init(v.rng);
        }
        v.sub.t = v.rng.uniform();
        resetOscPhases(v);  // derives the square/triangle half-cycle flags from the phases
        v.driftCut.init(v.rng);
        v.cutStatic = v.rng.bipolar();
    }
    // Global LFOs start where a full render has them at this song position, i.e. at the value of this
    // render's first control point.
    if (!srcs_.empty()) evalGlobalSources(startInternal_ + firstCtl, true);
    hpfCur_ = hpfMod_;
    lastDet_ = lastSpread_ = -1.0f;
    updateUnison(true);
    updateGlobals(true);

    hbL_.reset(); hbR_.reset();
    hpL_.reset(); hpR_.reset();
    hpLog_.snap(std::clamp(std::log2(p(kHpf)) + hpfCur_, hpLogMin_, hpLogMax_));
    hpFirst_ = true;
    level_.snap(dsp::dbToGain(p(kLevel)));
}

// Global sources at internal song sample n: global LFOs from the song position (tempo-synced ones on the
// song grid: cycles start on multiples of rateBeats from song beat 0; free ones at a constant rate from
// the song start; S&H / smooth-random steps are a hash of the cycle), so previews match full renders.
// Macros read their (smoothed) params. Global targets (hpf) use the de-clicked values.
void VaSynth::evalGlobalSources(std::int64_t n, bool snap) {
    for (std::size_t i = 0; i < srcs_.size(); ++i) {
        const SourceDef& d = srcs_[i];
        if (d.type == Src::Lfo && d.global) {
            // (tempo map: synced cycles counted in song beats from beat 0)
            const double cyc = (tempo_ && d.beats ? tempo_->beatAtSample(static_cast<double>(n) / os_) / d.rate
                                                  : static_cast<double>(n) * d.inc) + d.phase;
            const double k = std::floor(cyc);
            const auto ki = static_cast<std::int64_t>(k);
            float r0 = 0.0f, r1 = 0.0f;
            if (d.randomShape()) {
                const auto kc = static_cast<std::uint64_t>(ki);
                r0 = hashBipolar(modSeed_, i + 1, kc, 0x676C6F62ull);
                if (d.shape == Shape::SmoothRandom) r1 = hashBipolar(modSeed_, i + 1, kc + 1, 0x676C6F62ull);
            }
            float x = lfoWave(d.shape, cyc - k, r0, r1);
            if (d.unipolar) x = 0.5f * (x + 1.0f);
            if (snap) {
                gJump_[i] = 0.0f;
                gDc_[i].reset();
            } else {
                gJump_[i] = lfoJump(d.shape, d.unipolar, ki != gCycle_[i], x, gRaw_[i]);
                gDc_[i].step(gJump_[i], lfoSmC_);
            }
            gCycle_[i] = ki;
            gRaw_[i] = x;
            gOut_[i] = x + gDc_[i].b;
        } else if (d.type == Src::Macro) {
            gRaw_[i] = gOut_[i] = sm_[static_cast<std::size_t>(kMacro1 + d.macro)];
        }
    }
    if (globalTargets_) {  // (amounts unsmoothed here: the hpf glide smooths the sum, as for the hpf param)
        float h = 0.0f;
        for (std::size_t m = 0; m < mods_.size(); ++m)
            if (kTargets[mods_[m].target].global) h += gOut_[static_cast<std::size_t>(mods_[m].src)] * p(mods_[m].param);
        hpfMod_ = h;
    }
}

// Re-derive everything that depends on raw parameter values (runs when Params::version() changes).
void VaSynth::refresh() {
    seenVersion_ = params_.version();
    for (int i : kSmoothed) tgt_[static_cast<std::size_t>(i)] = p(i);
    tgt_[kCutoff] = std::log2(p(kCutoff));
    for (int i : kEnvTimes) tgt_[static_cast<std::size_t>(i)] = std::log2(p(i));
    envDirty_ = true;  // (sustain levels enter the coefficients directly)

    w1_ = static_cast<Wave>(ichoice(kOsc1Wave));
    w2_ = static_cast<Wave>(ichoice(kOsc2Wave));
    fmCarrier_ = w1_ == Wave::Sine;
    sync_ = p(kOsc2Sync) > 0.5f;
    pink_ = ichoice(kNoiseColor) == 1;
    oscRetrig_ = p(kOscRetrig) > 0.5f;
    ftype_ = ichoice(kFilterType);
    mode_ = ichoice(kMode);
    poly_ = std::clamp(static_cast<int>(std::lround(p(kPolyphony))), 1, kMaxPoly);
    subScale_ = std::lround(p(kSubOctave)) <= -2 ? 0.25f : 0.5f;

    const int u = std::clamp(static_cast<int>(std::lround(p(kUnison))), 1, kMaxUni);
    if (u != unison_ || lastDet_ < 0.0f) {
        unison_ = u;
        static constexpr float kJp7[7] = {-0.11002313f, -0.06288439f, -0.01952356f, 0.0f,
                                          0.01991221f,  0.06216538f,  0.10745242f};
        const int pairs = u / 2;
        for (int i = 0; i < u; ++i) {
            if (u == 1) { uniOff_[i] = 0.0f; uniPos_[i] = 0.0f; continue; }
            // JP-8000 offsets for 7 voices; otherwise the same shape (|x|^1.5, slightly asymmetric).
            const float x = -1.0f + 2.0f * static_cast<float>(i) / static_cast<float>(u - 1);
            uniOff_[i] = u == 7 ? kJp7[i]
                                : 0.11f * std::copysign(std::pow(std::fabs(x), 1.5f), x) * (x > 0.0f ? 0.977f : 1.0f);
            // Pan: outer pairs widest; alternate which side gets the sharp voice so both sides get
            // a similar mix of detunes.
            const int k = std::min(i, u - 1 - i);
            if (2 * i == u - 1) { uniPos_[i] = 0.0f; continue; }
            const float mag = 1.0f - static_cast<float>(k) / static_cast<float>(pairs);
            const bool flat = i < u - 1 - i;
            const bool left = (k % 2 == 0) ? flat : !flat;
            uniPos_[i] = left ? -mag : mag;
        }
        lastDet_ = lastSpread_ = -1.0f;
    }
    // exponential glide, time constant glide/3 (~95% of the interval covered in 'glide' seconds)
    glideC_ = p(kGlide) > 0.0f ? static_cast<float>(std::exp(-kCtl * 3.0 / (p(kGlide) * fsi_))) : 0.0f;
}

void VaSynth::updateUnison(bool snap) {
    const float det = sm_[kUniDetune], spr = sm_[kUniSpread];
    if (det != lastDet_) {
        lastDet_ = det;
        const double c = jpDetuneCurve(det);
        for (int u = 0; u < unison_; ++u) detRatio_[u] = 1.0 + uniOff_[u] * c;
    }
    stereoUni_ = unison_ > 1 && spr > 1e-3f;
    if (spr != lastSpread_) {
        lastSpread_ = spr;
        const float norm = 1.0f / std::sqrt(static_cast<float>(unison_));
        for (int u = 0; u < unison_; ++u) {
            const float a = (spr * uniPos_[u] + 1.0f) * 0.25f * static_cast<float>(kPi);
            panTL_[u] = norm * kSqrt2 * std::cos(a);
            panTR_[u] = norm * kSqrt2 * std::sin(a);
        }
    }
    for (int u = 0; u < unison_; ++u) {
        uPanL_[u].to(panTL_[u], snap);
        uPanR_[u].to(panTR_[u], snap);
    }
}

// Filter coefficient for a resonance: ladder feedback (plus its partial passband make-up `comp`) or the
// SVF damping k = 1/Q (Q 0.6 .. 24) with its band-pass gain.
void VaSynth::resonanceCoefs(float res, float& k, float& bpg, float& comp) const noexcept {
    if (ftype_ == 0) {
        k = kLadderMaxFb * res;
        comp = 1.0f + kLadderComp * k;
        bpg = 1.0f;
    } else {
        k = 1.0f / (0.6f * std::pow(40.0f, res));
        bpg = 2.0f * std::sqrt(k);
        comp = 1.0f;
    }
}

// Gain staging: oscillators -> x pre -> drive stage (|y| < 1) -> x mid -> filter -> x post (in the voice
// gain). At drive 0 the stage is almost linear (input 0.5) and the filter sees `level` x the mix; the
// make-up keeps loudness within ~1 dB across the drive range.
void VaSynth::driveGains(float drive, float& pre, float& post) const noexcept {
    const float level = ftype_ == 0 ? kLadderLevel : kSvfLevel;
    pre = 0.5f * dsp::dbToGain(drive * kDriveDb);
    post = 1.0f / (level * (1.0f + 2.3f * std::pow(drive, 0.85f)));
}

void VaSynth::updateGlobals(bool snap) {
    resonanceCoefs(sm_[kResonance], resG_, bpgG_, compG_);
    driveGains(sm_[kDrive], preG_, postG_);
    mid_ = 2.0f * (ftype_ == 0 ? kLadderLevel : kSvfLevel);
    const float th = sm_[kNoiseStereo] * 0.25f * static_cast<float>(kPi);  // mid/side mix of two noise streams
    nsC_.to(std::cos(th), snap);
    nsD_.to(th > 0.0f ? std::sin(th) : 0.0f, snap);
}

void VaSynth::advanceGlobalRamps(int n) {
    for (int u = 0; u < unison_; ++u) { uPanL_[u].adv(n); uPanR_[u].adv(n); }
    nsC_.adv(n);
    nsD_.adv(n);
}

// Envelope coefficients from the smoothed (log2) times and the sustain levels; only when they moved.
// A note start lands envelope-time glides at once: automation that switches e.g. amp.attack from a pad
// swell to a pluck exactly at a note (a per_section step on the downbeat) must give that note the new
// attack from its first sample, not a softened transient. The new note's onset masks the (slope-only)
// change of the stages still running on other voices.
void VaSynth::snapEnvTimes() {
    for (int i : kEnvTimes) {
        const auto k = static_cast<std::size_t>(i);
        sm_[k] = sm1_[k] = tgt_[k];
    }
    updateEnvCoefs();
}

void VaSynth::updateEnvCoefs() {
    bool moved = envDirty_;
    for (int k = 0; k < 6; ++k) moved = moved || sm_[static_cast<std::size_t>(kEnvTimes[k])] != envApplied_[k];
    if (!moved) return;
    envDirty_ = false;
    for (int k = 0; k < 6; ++k) envApplied_[k] = sm_[static_cast<std::size_t>(kEnvTimes[k])];
    auto sec = [&](int i) { return std::exp2(static_cast<double>(sm_[static_cast<std::size_t>(i)])); };
    ampC_.set(fsi_, 1, sec(kAmpA), sec(kAmpD), p(kAmpS), sec(kAmpR));
    fenvC_.set(fsi_, kCtl, sec(kFenvA), sec(kFenvD), p(kFenvS), sec(kFenvR));
}

void VaSynth::control() {
    if (params_.version() != seenVersion_) refresh();
    for (int i : kSmoothed) {  // two one-poles per parameter: C1-smooth, ~6 ms 10-90 %
        float& a = sm1_[static_cast<std::size_t>(i)];
        float& s = sm_[static_cast<std::size_t>(i)];
        const float t = tgt_[static_cast<std::size_t>(i)];
        a += (t - a) * smC_;
        s += (a - s) * smC_;
        if (std::fabs(t - a) + std::fabs(t - s) < 1e-6f * (1.0f + std::fabs(t))) a = s = t;
    }
    for (std::size_t m = 0; m < mods_.size(); ++m) {  // routing amounts: the same smoother
        const float t = p(mods_[m].param);
        float& a = amt1_[m];
        float& s = amt_[m];
        a += (t - a) * smC_;
        s += (a - s) * smC_;
        if (std::fabs(t - a) + std::fabs(t - s) < 1e-6f * (1.0f + std::fabs(t))) a = s = t;
    }
    updateEnvCoefs();
    ctlClock_ += kCtl;  // targets are for the end of this period
    if (tempo_) {  // beats this period spans (synced voice LFOs advance by them)
        const double end = tempo_->beatAtSample(static_cast<double>(startInternal_ + ctlClock_) / os_);
        ctlBeats_ = end - ctlBeatEnd_;
        ctlBeatEnd_ = end;
    }
    if (!srcs_.empty()) evalGlobalSources(startInternal_ + ctlClock_, false);
    updateUnison(false);
    updateGlobals(false);
    for (auto& v : pool_)
        if (v.active) controlVoice(v, false);
}

// Linear-segment envelope (env source with "curve": "linear"), stepped once per control period.
inline float tickLinear(Env& e, const SourceDef& d) noexcept {
    switch (e.st) {
        case Env::Idle: break;
        case Env::Attack:
            e.lv += d.linA;
            if (e.lv >= 1.0f) { e.lv = 1.0f; e.st = Env::Decay; }
            break;
        case Env::Decay:
            e.lv -= d.linD;
            if (e.lv <= static_cast<float>(d.s)) { e.lv = static_cast<float>(d.s); e.st = Env::Sustain; }
            break;
        case Env::Sustain: e.lv = static_cast<float>(d.s); break;
        case Env::Release:
            e.lv -= e.s1;  // (release step, fixed at note-off: lands at 0 after `release` seconds)
            if (e.lv <= 0.0f) { e.lv = 0.0f; e.st = Env::Idle; }
            break;
    }
    return e.lv;
}

// The modulation matrix for one voice: every source instance once (voice LFOs advance, envelopes step,
// per-note values), de-clicked where a value can jump (only the jumps of LFOs - edges, phase restarts, delay
// onsets - glide out in ~2.4 ms, so fast LFOs keep their full depth; per-note values changing in a mono
// retrigger: ~10 ms; envelopes are not smoothed, like the filter envelope), then every routing adds
// source x smoothed amount to its target.
void VaSynth::evalMods(Voice& v, bool snap, std::int64_t age, float* T) {
    for (std::size_t i = 0; i < srcs_.size(); ++i) {
        const SourceDef& d = srcs_[i];
        SrcState& s = v.src[i];
        float x = 0.0f, c = 0.0f;
        switch (d.type) {
            case Src::Lfo: {
                float raw, rawJump = 0.0f;
                if (d.global) {
                    raw = gRaw_[i];
                    rawJump = gJump_[i];
                } else {
                    bool wrapped = false;
                    if (!snap) {
                        s.ph += tempo_ && d.beats ? ctlBeats_ / d.rate : d.inc * kCtl;
                        if (s.ph >= 1.0) {
                            const double wraps = std::floor(s.ph);
                            s.ph -= wraps;
                            s.cycle += static_cast<std::int64_t>(wraps);
                            wrapped = true;
                        }
                    }
                    float r0 = 0.0f, r1 = 0.0f;
                    if (d.randomShape()) {
                        const std::uint64_t k = modSeed_ ^ (static_cast<std::uint64_t>(i + 1) * 0x9E3779B97F4A7C15ull);
                        const std::uint64_t note = static_cast<std::uint64_t>(v.noteSample) * 131u + static_cast<std::uint64_t>(v.note);
                        r0 = hashBipolar(k, note, static_cast<std::uint64_t>(s.cycle), 0x766F6963ull);
                        if (d.shape == Shape::SmoothRandom)
                            r1 = hashBipolar(k, note, static_cast<std::uint64_t>(s.cycle + 1), 0x766F6963ull);
                    }
                    raw = lfoWave(d.shape, s.ph, r0, r1);
                    if (d.unipolar) raw = 0.5f * (raw + 1.0f);
                    if (!snap) rawJump = lfoJump(d.shape, d.unipolar, wrapped, raw, s.prevRaw);
                }
                const float depth = depthMul(d, age);
                x = raw * depth;
                if (snap) {
                    s.dc.reset();
                } else {
                    // A retrigger (phase / delay restart) or a delay ending without fade is a jump of the whole
                    // value; otherwise only the wave's own edges are.
                    const bool event = s.restart || (depth != s.prevDepth && d.fadeS <= 0.0);
                    s.dc.step(event ? x - s.prevX : rawJump * depth, lfoSmC_);
                }
                s.restart = false;
                s.prevRaw = raw;
                s.prevX = x;
                s.prevDepth = depth;
                s.out = x + s.dc.b;
                continue;
            }
            case Src::Env:
                x = snap ? s.env.lv : (d.linear ? tickLinear(s.env, d) : s.env.tick(d.ec));
                break;
            case Src::Velocity:
                x = v.vel;
                c = noteC_;
                break;
            case Src::Key:
                x = d.keyRange ? std::clamp(static_cast<float>((v.pitch - d.keyLo) / (d.keyHi - d.keyLo)), 0.0f, 1.0f)
                               : static_cast<float>((v.pitch - 69.0) * (1.0 / 12.0));
                c = noteC_;
                break;
            case Src::Random:
                x = s.rnd;
                c = noteC_;
                break;
            case Src::Macro:
                x = sm_[static_cast<std::size_t>(kMacro1 + d.macro)];
                break;
        }
        if (snap || c == 0.0f) {
            s.s1 = s.out = x;
        } else {
            s.s1 += (x - s.s1) * c;
            s.out += (s.s1 - s.out) * c;
            if (std::fabs(x - s.s1) + std::fabs(x - s.out) < 1e-7f) s.s1 = s.out = x;  // (lands; no denormal tails)
        }
    }
    for (std::size_t m = 0; m < mods_.size(); ++m) {
        const ModDef& md = mods_[m];
        T[md.target] += v.src[static_cast<std::size_t>(md.src)].out * amt_[m];
    }
}

// Per-voice modulation at control rate: glide, drift, envelopes, the modulation matrix -> pitch
// increments, oscillator levels, filter coefficients and output gains (targets for the end of the next
// control period).
void VaSynth::controlVoice(Voice& v, bool snap) {
    const std::int64_t age = v.age;  // (LFO delay / fade: the age at the start of this period)
    float fe;
    if (snap) {
        fe = v.fenv.lv;
        v.velGain = v.velTarget;
    } else {
        v.age += kCtl;
        fe = v.fenv.tick(fenvC_);
        v.velGain += (v.velTarget - v.velGain) * velC_;
        v.pitch = v.target + (v.pitch - v.target) * glideC_;
    }
    float T[kTargetCount] = {};
    if (!mods_.empty()) evalMods(v, snap, age, T);

    // pitch
    const double dp = sm_[kDriftPitch] * kCentToRatio;
    const double base = v.pitch + sm_[kPitchbend] + T[kTPitch] * 0.01;
    const double p1 = base + sm_[kOsc1Semi] + sm_[kOsc1Fine] * 0.01 + T[kTOsc1Pitch] * 0.01;
    const double p2 = base + sm_[kOsc2Semi] + sm_[kOsc2Fine] * 0.01 + T[kTOsc2Pitch] * 0.01;
    const double f1 = std::exp2(static_cast<float>((p1 - 69.0) * (1.0 / 12.0))) * hzToInc_;
    const double f2 = std::exp2(static_cast<float>((p2 - 69.0) * (1.0 / 12.0))) * hzToInc_;
    auto clampInc = [](double x) { return std::clamp(x, 1e-7, 0.45); };
    const double* det = detRatio_;
    double detV[kMaxUni];
    if (used_[kTDetune]) {
        const double c = jpDetuneCurve(std::clamp(sm_[kUniDetune] + T[kTDetune], 0.0f, 1.0f));
        for (int u = 0; u < unison_; ++u) detV[u] = 1.0 + uniOff_[u] * c;
        det = detV;
    }
    for (int u = 0; u < unison_; ++u) {
        const float d1 = snap ? v.drift1[u].s2 : v.drift1[u].tick(v.rng, driftA_, driftMin_, driftRange_);
        const float d2 = snap ? v.drift2[u].s2 : v.drift2[u].tick(v.rng, driftA_, driftMin_, driftRange_);
        v.inc1[u].to(clampInc(f1 * det[u] * (1.0 + d1 * dp)), snap);
        v.inc2[u].to(clampInc(f2 * det[u] * (1.0 + d2 * dp)), snap);
    }
    v.incSub.to(clampInc(f1 * (1.0 + v.drift1[0].s2 * dp) * subScale_), snap);
    v.pw1.to(std::clamp(sm_[kOsc1Pw] + T[kTOsc1Pw], 0.02f, 0.98f), snap);
    v.pw2.to(std::clamp(sm_[kOsc2Pw] + T[kTOsc2Pw], 0.02f, 0.98f), snap);

    // source levels, FM index
    auto level = [&](int param, int t) { return std::clamp(sm_[static_cast<std::size_t>(param)] + T[t], 0.0f, 1.0f); };
    v.g1.to(level(kOsc1Level, kTOsc1Level), snap);
    v.g2.to(level(kOsc2Level, kTOsc2Level), snap);
    v.gSub.to(level(kSubLevel, kTSubLevel), snap);
    const float noise = level(kNoiseLevel, kTNoiseLevel);
    v.gNoise.to(noise, snap);
    v.fm.to(fmCarrier_ ? std::clamp(sm_[kFm] + T[kTFm], 0.0f, 10.0f) : 0.0f, snap);

    // filter
    const float dc = snap ? v.driftCut.s2 : v.driftCut.tick(v.rng, driftA_, driftMin_, driftRange_);
    const float oct = sm_[kCutoff] + sm_[kKeytrack] * static_cast<float>(v.pitch - 60.0) / 12.0f +
                      sm_[kFilterEnv] * fe + sm_[kFilterVel] * (v.vel - 1.0f) + T[kTCutoff] +
                      sm_[kDriftCutoff] * (v.cutStatic + 0.5f * dc) / 12.0f;
    const float fc = std::clamp(std::exp2(oct), 16.0f, maxCutoff_);
    v.fco.to(std::tan(fc * piOverFsi_), snap);
    float k = resG_, bpg = bpgG_, comp = compG_, pre = preG_, post = postG_;
    if (used_[kTResonance]) resonanceCoefs(std::clamp(sm_[kResonance] + T[kTResonance], 0.0f, 1.0f), k, bpg, comp);
    if (used_[kTDrive]) driveGains(std::clamp(sm_[kDrive] + T[kTDrive], 0.0f, 1.0f), pre, post);
    v.res.to(k, snap);
    v.bpg.to(bpg, snap);
    v.pre.to(pre, snap);

    // output gains: velocity, amp routings (dB), filter make-up, pan (equal power, unity at centre)
    const float pan = std::clamp(sm_[kPan] + T[kTPan], -1.0f, 1.0f);
    if (pan != v.panPos) {
        v.panPos = pan;
        const float a = (pan + 1.0f) * 0.25f * static_cast<float>(kPi);
        v.panL = kSqrt2 * std::cos(a);
        v.panR = kSqrt2 * std::sin(a);
    }
    float g = kVoiceGain * v.velGain * post * comp;
    if (used_[kTAmp]) g *= std::exp2(std::clamp(T[kTAmp], -120.0f, 24.0f) * kDbToLog2);
    v.gainL.to(g * v.panL, snap);
    v.gainR.to(g * v.panR, snap);

    const bool wide = stereoUni_ || (noiseWide() && noise > 0.0f);
    if (wide && !v.stereo) {  // leaving the mono path: right filter continues from the left one
        v.satR = v.satL;
        v.ladR = v.ladL;
        v.svfR = v.svfL;
        v.stereo = true;  // sticky for the rest of the note: falling back would jump R to L (click)
    }
}

void VaSynth::renderVoice(Voice& v, float* outL, float* outR, int len) {
    float bL[kCtl], bR[kCtl], bM[kCtl];
    std::fill(bL, bL + len, 0.0f);
    std::fill(bR, bR + len, 0.0f);
    std::fill(bM, bM + len, 0.0f);
    const bool st = v.stereo;
    const bool osc1On = !v.g1.zero();
    const bool osc2On = !v.g2.zero();
    const bool fmOn = !v.fm.zero();  // (only ever non-zero with a sine osc1)

    // Oscillators. Osc1 also runs silently when it is the sync master of an audible osc2; osc2 also
    // runs silently as the FM modulator.
    const bool runA = osc1On || (osc2On && sync_);
    for (int u = 0; u < unison_; ++u) {
        float x[kCtl], wrap[kCtl], unusedWrap[kCtl];
        std::fill(x, x + len, 0.0f);
        double i1 = v.inc1[u].v, i2 = v.inc2[u].v;
        if (fmOn) {
            const OscPairRamps r{i1, v.inc1[u].d, i2, v.inc2[u].d, v.pw2.v, v.pw2.d,
                                 v.g1.v, v.g1.d, v.g2.v, v.g2.d, v.fm.v, v.fm.d};
            if (sync_) fmRun<true>(w2_, v.o1[u], v.o2[u], r, x, len);
            else fmRun<false>(w2_, v.o1[u], v.o2[u], r, x, len);
            i1 += v.inc1[u].d * len;
            i2 += v.inc2[u].d * len;
        } else {
            if (runA) oscRun<false>(w1_, v.o1[u], i1, v.inc1[u].d, v.pw1.v, v.pw1.d, v.g1.v, v.g1.d, wrap, x, len);
            else i1 += v.inc1[u].d * len;
            if (osc2On && sync_) oscRun<true>(w2_, v.o2[u], i2, v.inc2[u].d, v.pw2.v, v.pw2.d, v.g2.v, v.g2.d, wrap, x, len);
            else if (osc2On) oscRun<false>(w2_, v.o2[u], i2, v.inc2[u].d, v.pw2.v, v.pw2.d, v.g2.v, v.g2.d, unusedWrap, x, len);
            else i2 += v.inc2[u].d * len;
        }
        v.inc1[u].v = i1;
        v.inc2[u].v = i2;
        float pl = uPanL_[u].v, pr = uPanR_[u].v;
        const float dpl = uPanL_[u].d, dpr = uPanR_[u].d;
        if (st) {
            for (int n = 0; n < len; ++n) { pl += dpl; pr += dpr; bL[n] += x[n] * pl; bR[n] += x[n] * pr; }
        } else {
            for (int n = 0; n < len; ++n) { pl += dpl; bL[n] += x[n] * pl; }
        }
    }

    if (!v.gSub.zero()) {
        double is = v.incSub.v;
        float gs = v.gSub.v;
        const float dgs = v.gSub.d;
        for (int n = 0; n < len; ++n) {
            is += v.incSub.d; gs += dgs;
            float unused;
            bM[n] += gs * v.sub.tick<Wave::Square>(is, 0.5f, unused);
        }
    }
    v.incSub.v += v.incSub.d * len;

    if (!v.gNoise.zero()) {
        auto noise = [&](float* b) {
            float w = v.rng.bipolar();
            if (pink_) {  // Paul Kellet's refined pink filter
                b[0] = 0.99886f * b[0] + w * 0.0555179f;
                b[1] = 0.99332f * b[1] + w * 0.0750759f;
                b[2] = 0.96900f * b[2] + w * 0.1538520f;
                b[3] = 0.86650f * b[3] + w * 0.3104856f;
                b[4] = 0.55000f * b[4] + w * 0.5329522f;
                b[5] = -0.7616f * b[5] - w * 0.0168980f;
                const float pk = b[0] + b[1] + b[2] + b[3] + b[4] + b[5] + b[6] + w * 0.5362f;
                b[6] = w * 0.115926f;
                w = pk * kPinkScale;
            }
            return w;
        };
        float gn = v.gNoise.v;
        const float dgn = v.gNoise.d;
        if (st && !nsD_.zero()) {  // stereo noise: mid/side of two independent streams (equal power per side)
            float c = nsC_.v, s = nsD_.v;
            const float dcs = nsC_.d, dss = nsD_.d;
            for (int n = 0; n < len; ++n) {
                gn += dgn; c += dcs; s += dss;
                const float m = c * noise(v.pink), sd = s * noise(v.pink2);
                bL[n] += gn * (m + sd);
                bR[n] += gn * (m - sd);
            }
        } else {
            for (int n = 0; n < len; ++n) {
                gn += dgn;
                bM[n] += gn * noise(v.pink);
            }
        }
    }

    // Filter, amp envelope, output.
    float f = v.fco.v, k = v.res.v, pre = v.pre.v, bpg = v.bpg.v, gl = v.gainL.v, gr = v.gainR.v;
    const float df = v.fco.d, dk = v.res.d, dpre = v.pre.d, dbpg = v.bpg.d, dgl = v.gainL.d, dgr = v.gainR.d;
    const float mid = mid_;
    const int svfMode = ftype_ - 1;
    for (int n = 0; n < len; ++n) {
        f += df; k += dk; pre += dpre; bpg += dbpg; gl += dgl; gr += dgr;
        float e = v.amp.tick(ampC_);
        if (v.killing) {
            v.killGain = std::max(0.0f, v.killGain - killStep_);
            e *= v.killGain;
        }
        const float xl = v.satL.tick((bL[n] + bM[n]) * pre) * mid;
        float yl, yr;
        if (ftype_ == 0) {
            yl = v.ladL.tick(xl, f, k);
            yr = st ? v.ladR.tick(v.satR.tick((bR[n] + bM[n]) * pre) * mid, f, k) : yl;
        } else {
            yl = v.svfL.tick(xl, f, k, bpg, svfMode);
            yr = st ? v.svfR.tick(v.satR.tick((bR[n] + bM[n]) * pre) * mid, f, k, bpg, svfMode) : yl;
        }
        outL[n] += yl * e * gl;
        outR[n] += yr * e * gr;
    }
    for (Ramp* r : {&v.fco, &v.res, &v.pre, &v.bpg, &v.gainL, &v.gainR, &v.g1, &v.g2, &v.gSub, &v.gNoise, &v.pw1,
                    &v.pw2, &v.fm})
        r->adv(len);
    v.ladL.flush(); v.ladR.flush(); v.svfL.flush(); v.svfR.flush();

    const bool silentSustain = v.amp.st == Env::Sustain && ampC_.sus <= 0.0f && v.amp.lv < 1e-5f;
    if (v.amp.st == Env::Idle || silentSustain || (v.killing && v.killGain <= 0.0f)) {
        v.active = false;
        v.killing = false;
        v.amp.st = Env::Idle;
        v.amp.lv = 0.0f;
    }
}

// ---------------------------------------------------------------------------------------------
// Voice management

void VaSynth::resetOscPhases(Voice& v) {
    auto init = [](Osc& o, double ph, Wave w, float pw) {
        o.t = ph;
        o.hi = w == Wave::Triangle ? ph < 0.5 : ph < pw;
    };
    for (int u = 0; u < kMaxUni; ++u) {
        init(v.o1[u], v.o1[u].t, w1_, v.pw1.v > 0.0f ? v.pw1.v : 0.5f);
        init(v.o2[u], v.o2[u].t, w2_, v.pw2.v > 0.0f ? v.pw2.v : 0.5f);
    }
    init(v.sub, v.sub.t, Wave::Square, 0.5f);
}

VaSynth::Voice& VaSynth::allocate() {
    int activeCount = 0;
    for (const auto& v : pool_) if (v.active && !v.killing) ++activeCount;
    if (activeCount >= poly_) {
        // steal: the longest-released voice, else the oldest held one; it fades out in 5 ms
        Voice* victim = nullptr;
        for (auto& v : pool_) {
            if (!v.active || v.killing) continue;
            if (!victim) { victim = &v; continue; }
            if (v.released != victim->released) {
                if (v.released) victim = &v;
            } else if (v.released ? v.offStamp < victim->offStamp : v.onStamp < victim->onStamp) {
                victim = &v;
            }
        }
        if (victim) { victim->killing = true; victim->noteId = -1; }
    }
    Voice* best = nullptr;
    for (auto& v : pool_)  // least recently used idle slot (rotates through voice "cards")
        if (!v.active && (!best || v.lastUsed < best->lastUsed)) best = &v;
    if (!best) {  // every slot is still fading: reuse the quietest one
        for (auto& v : pool_)
            if (v.killing && (!best || v.killGain < best->killGain)) best = &v;
    }
    if (!best) best = &pool_[0];
    return *best;
}

// (Re)trigger of the per-note modulation sources: voice LFOs restart at their phase, envelopes attack
// (from their current level unless the voice is fresh), per-note random values are drawn from the song
// position and the note (so a preview draws what the full render has).
void VaSynth::triggerMods(Voice& v, bool fresh) {
    v.noteSample = startSample_ + clock_;
    v.note = static_cast<int>(std::lround(v.target));
    for (std::size_t i = 0; i < srcs_.size(); ++i) {
        const SourceDef& d = srcs_[i];
        SrcState& s = v.src[i];
        switch (d.type) {
            case Src::Lfo:
                if (!d.global) {
                    s.ph = d.phase - std::floor(d.phase);
                    s.cycle = 0;
                }
                // (a sounding voice's value jumps: phase restart, delay / fade from the start again)
                s.restart = !d.global || d.delay > 0.0 || d.fade > 0.0;
                break;
            case Src::Env:
                if (fresh) s.env.lv = 0.0f;
                s.env.gateOn();
                if (d.instant) {
                    s.env.lv = 1.0f;
                    s.env.st = Env::Decay;
                }
                break;
            case Src::Random: {
                const float r = hashBipolar(modSeed_ ^ 0x72616E646F6Dull, d.seed, static_cast<std::uint64_t>(v.noteSample),
                                            static_cast<std::uint64_t>(v.note));
                s.rnd = d.unipolar ? 0.5f * (r + 1.0f) : r;
                break;
            }
            default: break;
        }
    }
}

void VaSynth::releaseVoice(Voice& v) {
    v.released = true;
    v.offStamp = stamp_;
    v.amp.gateOff();
    v.fenv.gateOff();
    for (std::size_t i = 0; i < srcs_.size(); ++i) {
        const SourceDef& d = srcs_[i];
        if (d.type != Src::Env) continue;
        SrcState& s = v.src[i];
        if (d.linear) s.env.s1 = s.env.lv * d.linR;
        s.env.gateOff();
    }
}

void VaSynth::startVoice(Voice& v, int id, int note, float vel, double fromPitch) {
    const bool wasActive = v.active;
    v.active = true;
    v.released = false;
    v.killing = false;
    v.killGain = 1.0f;
    v.noteId = id;
    v.vel = vel;
    v.velTarget = velGainFor(vel);
    v.onStamp = v.lastUsed = stamp_;
    v.startClock = clock_;
    v.target = note;
    v.pitch = fromPitch;
    v.hasPitch = true;
    v.age = 0;
    if (!wasActive) {
        v.amp.lv = 0.0f;
        v.fenv.lv = 0.0f;
        v.satL.reset(); v.satR.reset();
        v.ladL.reset(); v.ladR.reset(); v.svfL.reset(); v.svfR.reset();
        v.stereo = stereoUni_;
    }
    if (oscRetrig_ && (!wasActive || v.amp.lv < 1e-3f)) {
        const double ph2 = p(kOsc2Phase) - std::floor(p(kOsc2Phase));
        for (int u = 0; u < kMaxUni; ++u) {
            v.o1[u].t = u == 0 ? 0.0 : v.rng.uniform();
            v.o2[u].t = u == 0 ? ph2 : v.rng.uniform();
        }
        v.sub.t = 0.0;
        resetOscPhases(v);
    }
    v.amp.gateOn();
    v.fenv.gateOn();
    triggerMods(v, !wasActive);
    controlVoice(v, !wasActive);
}

// Mono-mode retrigger of a sounding voice: envelopes restart from their current level.
void VaSynth::retrigger(Voice& v, float vel) {
    v.vel = vel;
    v.velTarget = velGainFor(vel);
    v.age = 0;
    v.amp.gateOn();
    v.fenv.gateOn();
    triggerMods(v, false);
}

void VaSynth::noteOn(int noteId, int pitch, float velocity) {
    if (params_.version() != seenVersion_) refresh();
    snapEnvTimes();  // (no-op unless an envelope time is gliding)
    ++stamp_;
    const float vel = std::clamp(velocity, 0.0f, 1.0f);

    if (mode_ == 0) {  // poly
        double from = pitch;
        if (glideOn()) {  // slide from the nearest pitch still sounding (not from this same chord)
            double best = 1e9;
            for (const auto& v : pool_) {
                if (!v.active || v.startClock == clock_) continue;
                const double d = std::fabs(v.pitch - pitch);
                if (d < best) { best = d; from = v.pitch; }
            }
            if (best > 1e8 && lastPitch_ >= 0.0) from = lastPitch_;
        }
        startVoice(allocate(), noteId, pitch, vel, from);
        lastPitch_ = pitch;
        return;
    }

    // mono / legato: one voice, last-note priority
    const bool wasHeld = heldCount_ > 0;
    if (heldCount_ == kHeld) {
        std::move(held_.begin() + 1, held_.end(), held_.begin());
        --heldCount_;
    }
    held_[static_cast<std::size_t>(heldCount_++)] = Held{noteId, pitch, vel};

    Voice& v = pool_[0];
    const bool legato = mode_ == 2;
    if (!v.active || v.killing) {
        const double from = (!legato && glideOn() && v.hasPitch) ? v.pitch : static_cast<double>(pitch);
        startVoice(v, noteId, pitch, vel, from);
        return;
    }
    v.noteId = noteId;
    v.target = pitch;
    v.released = false;
    v.lastUsed = v.onStamp = stamp_;
    if (legato && wasHeld) {
        if (!glideOn()) v.pitch = pitch;  // fingered legato: no retrigger
    } else {
        if (!glideOn() || legato) v.pitch = pitch;
        retrigger(v, vel);
    }
}

void VaSynth::noteOff(int noteId) {
    ++stamp_;
    if (mode_ == 0) {
        for (auto& v : pool_) {
            if (v.active && !v.killing && !v.released && v.noteId == noteId) releaseVoice(v);
        }
        return;
    }
    for (int i = 0; i < heldCount_; ++i) {
        if (held_[static_cast<std::size_t>(i)].id == noteId) {
            std::move(held_.begin() + i + 1, held_.begin() + heldCount_, held_.begin() + i);
            --heldCount_;
            break;
        }
    }
    Voice& v = pool_[0];
    if (!v.active || v.released || v.noteId != noteId) return;
    if (heldCount_ > 0) {  // fall back to the most recent still-held note
        const Held& h = held_[static_cast<std::size_t>(heldCount_ - 1)];
        v.noteId = h.id;
        v.target = h.pitch;
        if (!glideOn()) v.pitch = h.pitch;
        if (mode_ == 1) retrigger(v, h.vel);
    } else {
        releaseVoice(v);
    }
}

// ---------------------------------------------------------------------------------------------

void VaSynth::process(float* left, float* right, int frames) {
    const int capFrames = static_cast<int>(mixL_.size()) / os_;
    while (frames > capFrames) {  // never expected (host respects maxBlock), but stay safe
        process(left, right, capFrames);
        left += capFrames; right += capFrames; frames -= capFrames;
    }
    if (frames <= 0) return;

    const int n = frames * os_;
    float* mL = mixL_.data();
    float* mR = mixR_.data();
    std::fill(mL, mL + n, 0.0f);
    std::fill(mR, mR + n, 0.0f);

    hpfCount_ = 0;
    for (int pos = 0; pos < n;) {
        if (ctlLeft_ == 0) {
            control();
            ctlLeft_ = kCtl;
            if (globalTargets_ && hpfCount_ < static_cast<int>(hpfPos_.size())) {  // hpf routings: per control period
                hpfPos_[static_cast<std::size_t>(hpfCount_)] = pos;
                hpfVal_[static_cast<std::size_t>(hpfCount_)] = hpfMod_;
                ++hpfCount_;
            }
        }
        const int len = std::min(ctlLeft_, n - pos);  // (<= kCtl: the first period may be partial)
        for (auto& v : pool_)
            if (v.active) renderVoice(v, mL + pos, mR + pos, len);
        advanceGlobalRamps(len);
        pos += len;
        ctlLeft_ -= len;
    }

    if (os_ == 2) {
        for (int i = 0; i < frames; ++i) {
            left[i] = hbL_.process(mL[2 * i], mL[2 * i + 1]);
            right[i] = hbR_.process(mR[2 * i], mR[2 * i + 1]);
        }
        hbL_.flush();
        hbR_.flush();
    } else {
        std::copy(mL, mL + frames, left);
        std::copy(mR, mR + frames, right);
    }
    clock_ += frames;

    // Global high-pass (smoothed in log2 Hz, plus the hpf routings) and output level.
    const float levelTarget = dsp::dbToGain(p(kLevel));
    const float hpBase = std::log2(p(kHpf));
    int hj = 0;
    for (int i0 = 0; i0 < frames; i0 += 16) {
        const int end = std::min(frames, i0 + 16);
        while (hj < hpfCount_ && hpfPos_[static_cast<std::size_t>(hj)] <= i0 * os_) hpfCur_ = hpfVal_[static_cast<std::size_t>(hj++)];
        const float hpLog = hpLog_.next(std::clamp(hpBase + hpfCur_, hpLogMin_, hpLogMax_), hpA_);
        if (hpFirst_ || hpLog != hpLogApplied_) {
            const bool first = hpFirst_;
            hpFirst_ = false;
            hpLogApplied_ = hpLog;
            const double fc = std::min(std::exp2(static_cast<double>(hpLog)), 0.45 * fs_);
            const float g = static_cast<float>(std::tan(kPi * fc / fs_));
            if (first) {
                hpL_.set(g);
                hpR_.set(g);
            } else {
                hpL_.glideTo(g, end - i0);
                hpR_.glideTo(g, end - i0);
            }
        }
        for (int i = i0; i < end; ++i) {
            const float g = level_.next(levelTarget, levelC_);
            left[i] = safetyClip(hpL_.tick(left[i]) * g);
            right[i] = safetyClip(hpR_.tick(right[i]) * g);
        }
    }
    hpL_.flush();
    hpR_.flush();
}

}  // namespace
}  // namespace va

std::unique_ptr<Instrument> makeVaSynth() { return std::make_unique<va::VaSynth>(); }

}  // namespace as
