#include "instruments/Sampler.h"

#include "core/TempoMap.h"
#include "dsp/Dsp.h"
#include "instruments/SamplerCore.h"
#include "instruments/SamplerFiles.h"
#include "instruments/Sf2File.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

namespace as {
namespace {

namespace fs = std::filesystem;

constexpr double kStealSeconds = 0.004;   // stolen / mono-replaced voices fade out linearly
constexpr double kOffFastSeconds = 0.005; // SFZ off_mode "fast": a voice turned off by a group fades out linearly
constexpr double kChokeSeconds = 0.05;    // choke group: -60 dB in 50 ms
constexpr double kRestrikeSeconds = 0.004;  // re-strike damping: time constant of the glide (~12 ms to settle)
constexpr double kMinRelease = 0.001;     // shortest zone release (s)
constexpr double kGainTau = 0.0015;       // level, expression, pan, width, pitch bend smoothing (~5 ms 10-90 %)
constexpr double kToneTau = 0.002;        // cutoff, resonance (~7 ms)
constexpr double kHarmTau = 0.0025;       // 'harmonic' amount smoothing (~8 ms 10-90 %)
constexpr double kHarmWarm = 0.015;       // 'harmonic' cold start: the partial fades in over 15 ms
constexpr double kHarmEnvTau = 0.012;     // 'harmonic' level match: power envelopes of the note and its partial
constexpr double kHarmPeakFallDb = 1.5;   // 'harmonic' held peak level: falls this many dB per second
constexpr float kSilent = 1e-4f;          // envelope level that ends a release (-80 dB)
constexpr int kMaxHeld = 512;             // notes tracked for legato detection and release triggers
constexpr float kNoValue = std::numeric_limits<float>::quiet_NaN();

constexpr double kLineFadeSeconds = 0.03; // legato mode, a new phrase: the previous line's release fades out in 30 ms
constexpr double kMatchMinSeconds = 0.5;  // scripted legato: the level match relaxes to the note's own level over
                                          // at least 0.5 s (3 x the crossfade when longer): a drift, not a step
constexpr float kMatchLimitDb = 12.0f;    // largest level-match correction
constexpr int kMaxSwitchNotes = 16;       // keyswitch notes tracked while held (sw_down)

enum Param { kLevel, kPan, kWidth, kTranspose, kTune, kPitchbend, kCutoff, kResonance, kAttack, kDecay, kSustain, kRelease,
             kVelsens, kStart, kOneshot, kReverse, kMono, kPolyphony, kPedal, kExpression, kDynamics, kDynTone, kDynRange,
             kLayers, kXfSpread, kLegatoTime, kLegatoOffset, kLegatoMatch, kGlide, kGlideShape, kVibrato, kVibratoRate,
             kSympathetic, kBendFollow, kHarmonic, kHarmonicNum, kHarmonicFocus, kRestrike };

constexpr double kHalfDampDb = 16.0;      // half pedal: extra decay (dB/s) of pedal-held treble notes at pedal 0.5
                                          // (0 at 1; the heavy bass strings get 40 % of it: the bass rings through)

std::vector<ParamSpec> makeSpecs() {
    return {
        num("level", -60.0f, 24.0f, 0.0f, "dB",
            "Output level. 0 dB plays the files at their own level (a full-scale file peaks at 0 dBFS at velocity 127; "
            "mono files are panned equal-power, -3 dB at centre). Calibrate a kit / instrument with it."),
        num("pan", -1.0f, 1.0f, 0.0f, "", "Stereo position -1 (left) .. 1 (right) of the whole instrument."),
        num("width", 0.0f, 2.0f, 1.0f, "",
            "Stereo width: stereo files 0 = mono .. 1 = as recorded .. 2 = extra wide (mid/side); mono zones: scales "
            "their 'pan' (drum kit spread)."),
        num("transpose", -36.0f, 36.0f, 0.0f, "st", "Whole semitones added to every note before the zones are chosen.", false),
        num("tune", -1200.0f, 1200.0f, 0.0f, "ct", "Fine / coarse tuning of every voice in cents.", false),
        num("pitchbend", -24.0f, 24.0f, 0.0f, "st",
            "Pitch bend in (fractional) semitones for all sounding voices (808 glides, dives, tape stops). Smoothed."),
        num("cutoff", 20.0f, 20000.0f, 20000.0f, "Hz",
            "Resonant 12 dB/oct lowpass per voice; 20000 = open (bypassed). Automate for sweeps. Smoothed. (Zones with "
            "a filter of their own keep it; this one comes on top.)"),
        num("resonance", 0.0f, 1.0f, 0.0f, "", "Lowpass resonance: 0 = none (Q 0.7), 0.5 = Q 2.8, 1 = Q 11 (whistling)."),
        num("attack", 0.0f, 10.0f, 0.001f, "s",
            "Linear attack of the amplitude envelope (1 ms default avoids clicks with start offsets; 0.2-2 s swells). "
            "Zones with an 'attack' of their own (SFZ ampeg_attack) use theirs.", false),
        num("decay", 0.001f, 30.0f, 1.0f, "s", "Decay towards 'sustain' (time to fall 60 dB of the way). Zone 'decay' wins.",
            false),
        num("sustain", 0.0f, 1.0f, 1.0f, "",
            "Sustain level while the key is held (1 = the sample plays at full level until the key is released). "
            "Zone 'sustain' wins.", false),
        num("release", 0.001f, 30.0f, 0.1f, "s",
            "Release time after the key is released (60 dB fall). Ignored in one-shot mode. Zone 'release' wins.", false),
        num("velsens", 0.0f, 1.0f, 1.0f, "",
            "Velocity to level: 1 = level ~ (velocity/127)^2 (-12 dB at velocity 64), 0.5 = gentler, 0 = every note at full "
            "level. Velocity also picks zones with vello/velhi. Zones with their own 'ampVeltrack' (SFZ amp_veltrack) or "
            "'velcurve' are scaled by it too (0.8 = flatter dynamics for any sampled instrument).", false),
        num("start", 0.0f, 60000.0f, 0.0f, "ms",
            "Start offset into the sample (skip a slow attack or silence, chop a phrase). Applies to the next note, so "
            "automating it steps through a loop per note."),
        choice("oneshot", {"off", "on"}, 0,
               "on: every note plays the whole sample (loops off) and note-offs are ignored: drums and hits. off: the "
               "envelope follows the note length (zones with loop 'oneshot' ignore note-offs anyway)."),
        choice("reverse", {"off", "on"}, 0, "on: play every sample backwards (reverse cymbals, risers, ghostly pads)."),
        choice("mono", {"off", "on", "legato"}, 0,
               "on: one note at a time; a new note fades the previous one out in 4 ms. legato: a monophonic player (sax, "
               "brass, winds, solo strings, bass): a note that starts while another is held does not re-attack - "
               "library legato transitions (zones with trigger 'legato') play when there are any, else the new note "
               "enters past its attack ('legatooffset') while the old one crossfades out over 'legatotime' (equal "
               "power, level-matched), with optional portamento ('glide'). Releasing the newest note while an earlier "
               "key is held goes back to it (legato). Notes after a rest attack normally."),
        num("polyphony", 1.0f, 256.0f, 32.0f, "voices",
            "Max simultaneous voices (a note can use several: layers, microphones, release samples). When full, the "
            "oldest released (else oldest) voice is stolen with a 4 ms fade. Sampled pianos with pedal: 128+.", false),
        num("pedal", 0.0f, 1.0f, 0.0f, "",
            "Sustain pedal (CC64): >= 0.5 is down. While down, note-offs are held (the notes ring on until the pedal is "
            "released; a re-struck key starts a new voice and the old one rings on); release-triggered zones (piano "
            "damper / key-up samples) fire at pedal-up. Half pedal: between 0.5 and 1 the dampers touch the strings - "
            "the held notes ring on but die faster (extra decay in the treble 16 dB/s at 0.5, 8 at 0.75, none at 1; the "
            "heavy bass strings 40 % of that), a pianist's half pedal that keeps the bass under a clearing harmony. A "
            "step: automate it with 'step' points at bar or chord changes."),
        num("expression", 0.0f, 1.0f, 1.0f, "",
            "Expression (CC11): output gain = expression^2 (0.5 = -12 dB, 0 = silent), smoothed. Automate for swells and "
            "phrase dynamics on top of the note velocities."),
        num("dynamics", 0.0f, 1.0f, 1.0f, "",
            "Played dynamics (the mod wheel / CC1 of sample libraries, 0 = ppp .. 1 = fff), moving WHILE notes sound: "
            "crossfades dynamic layers live (zones with xfinLoDyn .. / dynGain / dynCutoff: SFZ CC crossfades imported "
            "live; velocity layers with layers='dynamics'), opens the tone with 'dyntone' and the level with "
            "'dynrange'. Smoothed (~5 ms). Automate it for crescendi, swells, fp and sforzando."),
        num("dyntone", 0.0f, 1.0f, 0.5f, "",
            "How much 'dynamics' also moves the brightness: a gentle tilt EQ, darker below dynamics 1 (at dynamics 0: "
            "-10 dB x dyntone above ~2.5 kHz, a little warmth below 250 Hz). 0 = off (libraries whose layers carry the "
            "timbre: inst.sfz sets 0 when the file crossfades or filters by the controller, or when the file's default "
            "controller value is below the top, so the default sound stays the file's own; set it to use both).",
            false),
        num("dynrange", 0.0f, 48.0f, 0.0f, "dB",
            "Level range of 'dynamics': at dynamics 0 the instrument is this much quieter than at 1 (e.g. 18 for a "
            "velocity-layered solo instrument whose crescendi should also grow louder). 0 = dynamics does not move "
            "the level by itself.", false),
        choice("layers", {"velocity", "dynamics"}, 0,
               "velocity: the note velocity picks the velocity layer (vello / velhi) as recorded. dynamics: velocity "
               "layers become a dynamics stack - a note starts its layers together (phase-aligned; 'xfspread' "
               "layers on each side of the current one) and 'dynamics' crossfades between them live (equal power), so "
               "a held note can swell from p to f. Velocity then only sets the note's level (velsens)."),
        num("xfspread", 0.0f, 16.0f, 1.0f, "layers",
            "layers='dynamics': extra layers started on each side of the pair 'dynamics' is between at the note-on "
            "(the reach of a crescendo or diminuendo within one note; beyond it the outermost started layer holds). "
            "Silent layers cost no DSP.", false),
        num("legatotime", 5.0f, 500.0f, 60.0f, "ms",
            "mono='legato': crossfade time of a legato transition (the old note out, the new one in, equal power). "
            "Applies to the next transition."),
        num("legatooffset", 0.0f, 1000.0f, 0.0f, "ms",
            "mono='legato', scripted transitions: where the new note's sample starts - past its attack. 0 = auto (per "
            "sample, from its level envelope: where the attack has settled); zones with 'legatoOffset' use theirs. "
            "Applies to the next transition."),
        num("legatomatch", 0.0f, 1.0f, 1.0f, "",
            "mono='legato', scripted transitions: 1 = the new note enters at the level of the old one and drifts to its "
            "own level (its sample, its velocity) over ~0.5 s: no bump or dip at the transition, however the "
            "recordings differ; 0 = no matching.", false),
        num("glide", 0.0f, 2000.0f, 0.0f, "ms",
            "mono='legato': portamento time of the next legato transition: the old note bends to the new pitch while "
            "the new one bends in from the old pitch, crossfading over max(legatotime, glide). 0 = none. Latched per "
            "transition: clip.glide(ms) marks the notes to glide into (the compiler steps this param just before "
            "them), or automate it with steps."),
        choice("glideshape", {"linear", "ease", "fast"}, 1,
               "Portamento curve: linear (constant speed in cents), ease (S-curve: leaves and lands gently, like a "
               "string player's slide), fast (moves early, settles into the note)."),
        num("vibrato", 0.0f, 200.0f, 0.0f, "ct",
            "Vibrato depth (+- cents) of all sounding notes, smoothed; phase starts at 0 with each new phrase (a note "
            "after a rest) and runs on through legato transitions. Automate it per note for delayed vibrato "
            "(articulation.vibrato): 0 on the attack, growing to 10-30 ct on long notes. Zones with a "
            "'vibrato' of their own add theirs."),
        num("vibratorate", 0.5f, 12.0f, 5.5f, "Hz",
            "Vibrato speed (4.5-6 Hz for strings and horns; slightly faster as a long note intensifies). Phase-"
            "continuous when it changes."),
        num("sympathetic", 0.0f, 1.0f, 0.0f, "",
            "Sympathetic string resonance of a piano (0 = off, no cost): 88 tuned strings (A0-C8, comb resonators with "
            "their harmonics) pick up what is played and ring on while their dampers are lifted - all of them while the "
            "sustain pedal is down (a half pedal damps them part-way), only the keys held otherwise - and die out in "
            "~60 ms when the dampers fall. The halo a real grand adds with the pedal: the sound blooms and decays more "
            "slowly (undamped strings ~20 s at A0 .. ~4 s at C8), silently held keys ring when others are struck. "
            "0.5-0.9 for a classical / ballad piano (a sampled grand, pedalled chord: 0.5 lifts its tail 2 s later ~0.3 dB, "
            "0.7 ~1.3 dB, 1 ~4.5 dB; in the Gymnopedie etude 0.9 slowed a held note's decay from 4.7 to 3.4 dB/s like the "
            "concert recording). The struck keys' own strings are left out (the samples carry them), the lowest octave "
            "does not couple and the bass couples less (no boom)."),
        num("bendfollow", 0.0f, 1.0f, 1.0f, "",
            "How much of 'pitchbend' a note follows, LATCHED when the note starts (1 = all of it, 0 = it stays put). "
            "Per-note bends on one instrument: an oblique / unison bend on a guitar - the held string latched at 0, "
            "the bent one at 1 (step it just before each note; agentsound.fretwork does)."),
        num("harmonic", 0.0f, 1.0f, 0.0f, "",
            "The string's harmonic, live on every sounding note: 0 = the plain note .. 1 = only its partial "
            "'harmonicnum' - isolated by two band-passes that track the note's pitch (bends, glides, vibrato) and "
            "level-matched to it, sustaining towards the note's held peak level as it rises to 1 (an amp holding a "
            "feedback note). Before an amp: a pinch harmonic (stepped up at the pick, 0.6-0.9, partial 3-6: the "
            "squeal) or controlled feedback (a held note morphing into partial 2-3 over 1-2 s). Smoothed; 0 costs "
            "nothing and is bit-transparent."),
        num("harmonicnum", 1.0f, 8.0f, 3.0f, "",
            "Which partial 'harmonic' brings out (x the note's frequency): 2 = the octave, 3 = octave + fifth, 4 = two "
            "octaves, 5 = two octaves + major third, 6 = two octaves + fifth. Set it while 'harmonic' is 0."),
        num("harmonicfocus", 2.0f, 40.0f, 10.0f, "Q",
            "Q of each of the two band-passes that isolate the partial (higher = purer, a whistle; lower = more "
            "of the neighbouring partials, grittier)."),
        num("restrike", 0.0f, 24.0f, 0.0f, "dB",
            "Re-strike damping: when a key is struck again while its earlier notes still sound, those voices fall by "
            "this much within ~12 ms and ring on from there (each new strike again). A drum head or a cymbal struck "
            "again does not keep its old vibration on top of the new one - the stick touches it - so sampled rolls, "
            "tom runs and cymbal swells stop piling up boom and wash (layering every hit fully: a 16th-note floor-tom "
            "run ~+7 dB of low ring over one hit; 6 dB of damping leaves ~+1.2 dB). 0 = off (every hit layers fully, "
            "bit-identical to before); drum kits 4-9, a piano's repeated notes 3-6.", false),
    };
}

// General MIDI drum names (the same table as agentsound/patterns.py DRUMS).
const std::map<std::string, int>& drumNames() {
    static const std::map<std::string, int> m = {
        {"kick", 36}, {"bd", 36}, {"rim", 37}, {"rimshot", 37}, {"rs", 37}, {"snare", 38}, {"sd", 38}, {"sn", 38},
        {"clap", 39}, {"cp", 39}, {"tom_lo", 41}, {"tom_low", 41}, {"lt", 41}, {"hat", 42}, {"hh", 42}, {"chh", 42},
        {"closed_hat", 42}, {"ch", 42}, {"pedal", 44}, {"pedal_hat", 44}, {"ph", 44}, {"tom_mid", 45}, {"mt", 45},
        {"open_hat", 46}, {"ohh", 46}, {"oh", 46}, {"tom_hi", 48}, {"tom_high", 48}, {"ht", 48}, {"crash", 49},
        {"cr", 49}, {"ride", 51}, {"rd", 51}, {"tamb", 54}, {"tambourine", 54}, {"cowbell", 56}, {"cb", 56},
    };
    return m;
}

// "C4" = 60, "F#3", "Bb2", "c-1" = 0, or a MIDI number "60".
bool parseNoteName(const std::string& text, int& key) {
    std::string s;
    for (const char c : text) s.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    if (!s.empty() && std::all_of(s.begin(), s.end(), [](char c) { return c >= '0' && c <= '9'; })) {
        if (s.size() > 3) return false;
        key = std::stoi(s);
        return key <= 127;
    }
    static const int pcs[7] = {9, 11, 0, 2, 4, 5, 7};  // a b c d e f g
    if (s.size() < 2 || s[0] < 'a' || s[0] > 'g') return false;
    int pc = pcs[s[0] - 'a'];
    std::size_t i = 1;
    if (s[i] == '#' || s[i] == 's') { ++pc; ++i; }
    else if (s[i] == 'b' && i + 1 < s.size()) { --pc; ++i; }
    bool neg = false;
    if (i < s.size() && s[i] == '-') { neg = true; ++i; }
    if (i >= s.size() || i + 1 < s.size() || s[i] < '0' || s[i] > '9') return false;
    const int octave = (neg ? -1 : 1) * (s[i] - '0');
    key = 12 * (octave + 1) + pc;
    return key >= 0 && key <= 127;
}

std::string lowerExt(const fs::path& p) {
    std::string e = p.extension().string();
    for (auto& c : e) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return e;
}

std::string resolveAsset(const std::string& assetDir, const std::string& path) {
    const fs::path p(path);
    return p.is_absolute() ? p.string() : (fs::path(assetDir) / p).string();
}

bool verbose() {
    const char* v = std::getenv("AGENTSOUND_VERBOSE");
    return v && *v && std::string(v) != "0";
}

// ------------------------------------------------------------------------------------ zone model

enum class Trigger : std::uint8_t { Attack, Release, ReleaseKey, First, Legato };
enum class OffMode : std::uint8_t { Fast, Normal, Time };
enum class ZoneLoop : std::uint8_t { None, OneShot, Forward, PingPong, Sustain, Auto };
enum class Filter : std::uint8_t { None, Lp1, Lp2, Hp1, Hp2, Bp2 };
enum class Gen : std::uint8_t { None, Silence, Sine, Noise };

struct ZoneSpec {
    std::string file, sample;
    Gen gen{Gen::None};
    std::optional<double> root;
    bool rootFromFile{false};
    int lo{0}, hi{127}, vello{0}, velhi{127};
    ZoneLoop loop{ZoneLoop::None};
    std::optional<std::int64_t> loopStart, loopEnd;
    double gainDb{0.0}, tune{0.0}, pan{0.0};
    int choke{0};
    int seqLength{1}, seqPosition{1};
    double lorand{0.0}, hirand{1.0};
    Trigger trigger{Trigger::Attack};
    double rtDecay{0.0};
    std::int64_t offset{0};
    std::optional<std::int64_t> end;
    double keytrack{100.0};
    std::int64_t group{0};
    std::optional<std::int64_t> offBy;
    OffMode offMode{OffMode::Fast};
    double offTime{0.006};
    int notePolyphony{0}, groupPolyphony{0};
    std::optional<double> veltrack;
    std::vector<std::pair<double, double>> velcurve;
    std::array<int, 8> xf{0, 0, 127, 127, 0, 0, 127, 127};  // vel in lo/hi, vel out lo/hi, key in lo/hi, key out lo/hi
    bool xfVelPower{true}, xfKeyPower{true};
    std::optional<double> envDelay, attack, hold, decay, sustain, release;
    double velAttack{0.0}, velHold{0.0}, velDecay{0.0}, velSustain{0.0}, velRelease{0.0};
    Filter filter{Filter::None};
    double cutoff{20000.0}, resonance{0.0}, filKeytrack{0.0}, filKeycenter{60.0}, filVeltrack{0.0};
    std::vector<std::array<double, 3>> eq;
    double ampRandom{0.0}, pitchRandom{0.0}, delay{0.0}, delayRandom{0.0};
    std::int64_t offsetRandom{0};
    double width{1.0};
    bool pedal{true};
    std::array<double, 4> vibrato{}, tremolo{};
    std::array<double, 7> fenv{};  // filter envelope: depth cents, delay, attack, hold, decay, sustain 0..1, release
    std::vector<smp::ChannelGain> channels;  // channel mix of a multichannel file into stereo (empty: first two channels)
    // live 'dynamics' (0..127 scale, like the controller it replaces)
    std::array<int, 4> xfDyn{0, 0, 127, 127};  // fade in lo/hi, fade out lo/hi
    bool xfDynPower{true};
    int dynLo{0}, dynHi{127};
    std::vector<std::pair<double, double>> dynGain;
    double dynCutoff{0.0};
    std::optional<double> legatoOffset;       // ms
    int swLastLo{-1}, swLastHi{-1}, swDown{-1}, swLo{-1}, swHi{-1}, swDefault{-1};
    std::string where;
};

struct Zone {
    std::shared_ptr<const smp::Region> region;  // null: silent zone ('*silence': plays nothing, only turns voices off)
    int lo{0}, hi{127}, vello{0}, velhi{127};
    double root{60.0}, tune{0.0}, keytrack{100.0};
    float gain{1.0f}, pan{0.0f};
    int choke{0};
    int seqLength{1}, seqPosition{1};
    float lorand{0.0f}, hirand{1.0f};
    Trigger trigger{Trigger::Attack};
    float rtDecay{0.0f};
    double offset{0.0}, end{0.0};   // played frames [offset, end) of the region
    bool loops{false}, sustainLoop{false}, oneshot{false};
    std::int64_t group{0};
    bool hasOffBy{false};
    std::int64_t offBy{0};
    OffMode offMode{OffMode::Fast};
    float offTime{0.006f};
    int notePolyphony{0}, groupPolyphony{0};
    bool hasVeltrack{false};
    float veltrack{1.0f};
    std::vector<std::pair<float, float>> velcurve;  // with the (0, 0) / (127, 1) end points
    std::array<int, 8> xf{0, 0, 127, 127, 0, 0, 127, 127};
    bool xfVelPower{true}, xfKeyPower{true};
    float envDelay{0.0f}, attack{kNoValue}, hold{0.0f}, decay{kNoValue}, sustain{kNoValue}, release{kNoValue};
    float velAttack{0.0f}, velHold{0.0f}, velDecay{0.0f}, velSustain{0.0f}, velRelease{0.0f};
    Filter filter{Filter::None};
    float cutoff{20000.0f}, filterQ{0.7071f}, filKeytrack{0.0f}, filKeycenter{60.0f}, filVeltrack{0.0f};
    int eqCount{0};
    std::array<std::array<float, 3>, 3> eq{};
    float ampRandom{0.0f}, pitchRandom{0.0f}, delay{0.0f}, delayRandom{0.0f};
    double offsetRandom{0.0};
    float width{1.0f};
    bool pedal{true};
    std::array<float, 4> vibrato{}, tremolo{};  // depth (cents / dB), rate Hz, delay s, fade s
    std::array<float, 7> fenv{};                // filter envelope (see ZoneSpec)
    std::uint64_t salt{0};                      // per-zone random stream: from the zone's content, not its index
    // live dynamics: crossfade on 'dynamics' (0..127), gain curve, filter cutoff move; the note-on condition
    std::array<float, 4> xfDyn{0.0f, 0.0f, 127.0f, 127.0f};
    bool xfDynPower{true}, hasXfDyn{false};
    int dynLo{0}, dynHi{127};
    std::vector<std::pair<float, float>> dynGain;   // with end points (0, g0) / (127, g127)
    float dynCutoff{0.0f};                          // cents at dynamics 1
    bool dynLive{false};                            // any of the three
    float legatoOffset{kNoValue};                   // ms (scripted legato entry)
    double legatoStart{0.0};                        // frames: where a scripted legato note starts (set in prepare)
    std::shared_ptr<const smp::LevelTrack> levels;  // mono='legato': the sample's level track
    int swLastLo{-1}, swLastHi{-1}, swDown{-1};     // keyswitch conditions (-1: none)
};

// ------------------------------------------------------------------------------------ JSON checks

[[noreturn]] void fail(const std::string& where, const std::string& what) { throw ConfigError("sampler: " + where + " " + what); }

void allowOnly(const json& j, const std::vector<std::string>& keys, const std::string& where) {
    for (auto it = j.begin(); it != j.end(); ++it) {
        if (std::find(keys.begin(), keys.end(), it.key()) == keys.end()) {
            std::ostringstream k;
            for (std::size_t i = 0; i < keys.size(); ++i) k << (i ? ", " : "") << keys[i];
            fail(where, "has unknown key '" + it.key() + "' (allowed: " + k.str() + ")");
        }
    }
}

double numberValue(const json& v, const std::string& where, double lo, double hi) {
    if (!v.is_number() || !std::isfinite(v.get<double>())) fail(where, "must be a number");
    const double x = v.get<double>();
    if (x < lo || x > hi) {
        std::ostringstream m;
        m << "= " << x << " is outside " << lo << ".." << hi;
        fail(where, m.str());
    }
    return x;
}

double number(const json& j, const std::string& key, const std::string& where, double lo, double hi) {
    return numberValue(j[key], where + "." + key, lo, hi);
}

std::int64_t integer64(const json& j, const std::string& key, const std::string& where, double lo, double hi) {
    const double x = number(j, key, where, lo, hi);
    if (x != std::round(x)) fail(where + "." + key, "must be a whole number");
    return static_cast<std::int64_t>(x);
}

int integer(const json& j, const std::string& key, const std::string& where, int lo, int hi) {
    return static_cast<int>(integer64(j, key, where, lo, hi));
}

std::string text(const json& j, const std::string& key, const std::string& where, const std::vector<std::string>& options) {
    std::ostringstream all;
    for (std::size_t i = 0; i < options.size(); ++i) all << (i ? ", " : "") << '"' << options[i] << '"';
    if (!j[key].is_string()) fail(where + "." + key, "must be one of " + all.str());
    const auto s = j[key].get<std::string>();
    if (std::find(options.begin(), options.end(), s) == options.end()) fail(where + "." + key, "must be one of " + all.str() + ", got \"" + s + "\"");
    return s;
}

ZoneLoop zoneLoop(const std::string& s) {
    if (s == "oneshot") return ZoneLoop::OneShot;
    if (s == "forward") return ZoneLoop::Forward;
    if (s == "pingpong") return ZoneLoop::PingPong;
    if (s == "sustain") return ZoneLoop::Sustain;
    if (s == "auto") return ZoneLoop::Auto;
    return ZoneLoop::None;
}

const std::vector<std::string> kLoopNames = {"none", "oneshot", "forward", "pingpong", "sustain", "auto"};

const std::vector<std::string> kZoneKeys = {
    "file", "sample", "root", "lo", "hi", "vello", "velhi", "loop", "loopStart", "loopEnd", "gain", "tune", "pan", "choke",
    "seqLength", "seqPosition", "lorand", "hirand", "trigger", "rtDecay", "offset", "end", "pitchKeytrack", "group", "offBy",
    "offMode", "offTime", "notePolyphony", "groupPolyphony", "ampVeltrack", "velcurve", "xfinLo", "xfinHi", "xfoutLo",
    "xfoutHi", "xfinLoKey", "xfinHiKey", "xfoutLoKey", "xfoutHiKey", "xfVelCurve", "xfKeyCurve", "envDelay", "attack", "hold", "decay", "sustain",
    "release", "velAttack", "velHold", "velDecay", "velSustain", "velRelease", "filter", "cutoff", "resonance", "filKeytrack",
    "filKeycenter", "filVeltrack", "eq", "ampRandom", "pitchRandom", "offsetRandom", "delay", "delayRandom", "width", "pedal",
    "vibrato", "tremolo", "filterEnv", "channels",
    // realism: live dynamics, legato, keyswitches
    "xfinLoDyn", "xfinHiDyn", "xfoutLoDyn", "xfoutHiDyn", "xfDynCurve", "dynLo", "dynHi", "dynGain", "dynCutoff",
    "legatoOffset", "swLast", "swDown", "swLo", "swHi", "swDefault"};

// [a, b, c, d] of numbers inside the given ranges.
std::array<double, 4> quad(const json& j, const std::string& key, const std::string& where, const std::array<std::pair<double, double>, 4>& r,
                           const char* shape) {
    const json& v = j[key];
    if (!v.is_array() || v.size() != 4) fail(where + "." + key, std::string("must be ") + shape);
    std::array<double, 4> out{};
    for (std::size_t i = 0; i < 4; ++i) out[i] = numberValue(v[i], where + "." + key + "[" + std::to_string(i) + "]", r[i].first, r[i].second);
    return out;
}

ZoneSpec parseZone(const json& z, const std::string& where) {
    if (!z.is_object()) fail(where, "must be an object such as {\"file\": \"samples/pad/C4.wav\", \"root\": 60}");
    allowOnly(z, kZoneKeys, where);
    ZoneSpec s;
    s.where = where;
    if (!z.contains("file") || !z["file"].is_string() || z["file"].get<std::string>().empty()) {
        fail(where, "needs \"file\": a WAV (or .sf2) path relative to assets/ or absolute, or a generator \"*silence\" / \"*sine\" / \"*noise\"");
    }
    s.file = z["file"].get<std::string>();
    if (s.file[0] == '*') {
        if (s.file == "*silence") s.gen = Gen::Silence;
        else if (s.file == "*sine") s.gen = Gen::Sine;
        else if (s.file == "*noise") s.gen = Gen::Noise;
        else fail(where + ".file", "'" + s.file + "' is not a generator (\"*silence\", \"*sine\", \"*noise\")");
    }
    const bool sf2 = s.gen == Gen::None && lowerExt(fs::path(s.file)) == ".sf2";
    if (z.contains("sample")) {
        if (!sf2) fail(where + ".sample", "is only for SoundFont files (.sf2)");
        if (!z["sample"].is_string() || z["sample"].get<std::string>().empty()) fail(where + ".sample", "must be a sample name");
        s.sample = z["sample"].get<std::string>();
    } else if (sf2) {
        fail(where, "uses a SoundFont: name the sample with \"sample\" (list them: agentsound sf2 --samples [search])");
    }
    if (z.contains("root")) {
        if (z["root"].is_string()) {
            if (z["root"].get<std::string>() != "sample") fail(where + ".root", "must be a key 0..127 or \"sample\" (the WAV's own root key)");
            if (sf2 || s.gen != Gen::None) fail(where + ".root", "\"sample\" reads the WAV's smpl chunk: only for WAV zones");
            s.rootFromFile = true;
        } else {
            s.root = number(z, "root", where, 0.0, 127.0);
        }
    }
    if (z.contains("lo")) s.lo = integer(z, "lo", where, 0, 127);
    if (z.contains("hi")) s.hi = integer(z, "hi", where, 0, 127);
    if (z.contains("vello")) s.vello = integer(z, "vello", where, 0, 127);
    if (z.contains("velhi")) s.velhi = integer(z, "velhi", where, 0, 127);
    if (s.lo > s.hi) fail(where, "has lo > hi");
    if (s.vello > s.velhi) fail(where, "has vello > velhi");
    if (z.contains("loop")) s.loop = zoneLoop(text(z, "loop", where, kLoopNames));
    if (z.contains("loopStart")) s.loopStart = integer64(z, "loopStart", where, 0, 4e9);
    if (z.contains("loopEnd")) s.loopEnd = integer64(z, "loopEnd", where, 1, 4e9);
    const bool looping = s.loop == ZoneLoop::Forward || s.loop == ZoneLoop::PingPong || s.loop == ZoneLoop::Sustain;
    if ((s.loopStart || s.loopEnd) && !looping) fail(where, "sets loop points but \"loop\" is not \"forward\", \"pingpong\" or \"sustain\"");
    if (s.loopStart && s.loopEnd && *s.loopStart >= *s.loopEnd) fail(where, "has loopStart >= loopEnd");
    if (z.contains("gain")) s.gainDb = number(z, "gain", where, -144.0, 48.0);
    if (z.contains("tune")) s.tune = number(z, "tune", where, -9600.0, 9600.0);
    if (z.contains("pan")) s.pan = number(z, "pan", where, -1.0, 1.0);
    if (z.contains("choke")) s.choke = integer(z, "choke", where, 0, 127);
    if (z.contains("seqLength")) s.seqLength = integer(z, "seqLength", where, 1, 128);
    if (z.contains("seqPosition")) s.seqPosition = integer(z, "seqPosition", where, 1, 128);
    if (s.seqPosition > s.seqLength) fail(where, "has seqPosition " + std::to_string(s.seqPosition) + " > seqLength " + std::to_string(s.seqLength));
    if (z.contains("lorand")) s.lorand = number(z, "lorand", where, 0.0, 1.0);
    if (z.contains("hirand")) s.hirand = number(z, "hirand", where, 0.0, 1.0);
    if (s.lorand >= s.hirand) fail(where, "has lorand >= hirand (the zone would never play)");
    if (z.contains("trigger")) {
        const auto t = text(z, "trigger", where, {"attack", "release", "release_key", "first", "legato"});
        s.trigger = t == "release" ? Trigger::Release : t == "release_key" ? Trigger::ReleaseKey : t == "first" ? Trigger::First
                  : t == "legato" ? Trigger::Legato : Trigger::Attack;
    }
    if (z.contains("rtDecay")) s.rtDecay = number(z, "rtDecay", where, 0.0, 200.0);
    if (z.contains("offset")) s.offset = integer64(z, "offset", where, 0, 4e9);
    if (z.contains("end")) s.end = integer64(z, "end", where, 1, 4e9);
    if (s.end && *s.end <= s.offset) fail(where, "has end <= offset (nothing to play)");
    if (z.contains("pitchKeytrack")) s.keytrack = number(z, "pitchKeytrack", where, -1200.0, 1200.0);
    if (z.contains("group")) s.group = integer64(z, "group", where, -2147483648.0, 2147483647.0);
    if (z.contains("offBy")) s.offBy = integer64(z, "offBy", where, -2147483648.0, 2147483647.0);
    if (z.contains("offMode")) {
        const auto m = text(z, "offMode", where, {"fast", "normal", "time"});
        s.offMode = m == "normal" ? OffMode::Normal : m == "time" ? OffMode::Time : OffMode::Fast;
    }
    if (z.contains("offTime")) s.offTime = number(z, "offTime", where, 0.0, 60.0);
    if (z.contains("notePolyphony")) s.notePolyphony = integer(z, "notePolyphony", where, 1, 128);
    if (z.contains("groupPolyphony")) s.groupPolyphony = integer(z, "groupPolyphony", where, 1, 256);
    if (z.contains("ampVeltrack")) s.veltrack = number(z, "ampVeltrack", where, -1.0, 1.0);
    if (z.contains("velcurve")) {
        const json& c = z["velcurve"];
        if (!c.is_array() || c.empty()) fail(where + ".velcurve", "must be a list of [velocity, gain] points");
        int last = -1;
        for (std::size_t i = 0; i < c.size(); ++i) {
            const std::string w = where + ".velcurve[" + std::to_string(i) + "]";
            if (!c[i].is_array() || c[i].size() != 2) fail(w, "must be [velocity 0..127, gain 0..4]");
            const double v = numberValue(c[i][0], w + "[0]", 0.0, 127.0);
            if (v != std::round(v)) fail(w + "[0]", "must be a whole velocity");
            if (static_cast<int>(v) <= last) fail(w, "velocities must be strictly increasing");
            last = static_cast<int>(v);
            s.velcurve.push_back({v, numberValue(c[i][1], w + "[1]", 0.0, 4.0)});
        }
    }
    const char* xfKeys[8] = {"xfinLo", "xfinHi", "xfoutLo", "xfoutHi", "xfinLoKey", "xfinHiKey", "xfoutLoKey", "xfoutHiKey"};
    for (int k = 0; k < 8; ++k) {
        if (z.contains(xfKeys[k])) s.xf[static_cast<std::size_t>(k)] = integer(z, xfKeys[k], where, 0, 127);
    }
    for (int k = 0; k < 8; k += 2) {
        if (s.xf[static_cast<std::size_t>(k)] > s.xf[static_cast<std::size_t>(k + 1)]) {
            fail(where, std::string("has ") + xfKeys[k] + " > " + xfKeys[k + 1]);
        }
    }
    if (z.contains("xfVelCurve")) s.xfVelPower = text(z, "xfVelCurve", where, {"power", "gain"}) == "power";
    if (z.contains("xfKeyCurve")) s.xfKeyPower = text(z, "xfKeyCurve", where, {"power", "gain"}) == "power";
    if (z.contains("envDelay")) s.envDelay = number(z, "envDelay", where, 0.0, 100.0);
    if (z.contains("attack")) s.attack = number(z, "attack", where, 0.0, 100.0);
    if (z.contains("hold")) s.hold = number(z, "hold", where, 0.0, 100.0);
    if (z.contains("decay")) s.decay = number(z, "decay", where, 0.0, 100.0);
    if (z.contains("sustain")) s.sustain = number(z, "sustain", where, 0.0, 1.0);
    if (z.contains("release")) s.release = number(z, "release", where, 0.0, 100.0);
    if (z.contains("velAttack")) s.velAttack = number(z, "velAttack", where, -100.0, 100.0);
    if (z.contains("velHold")) s.velHold = number(z, "velHold", where, -100.0, 100.0);
    if (z.contains("velDecay")) s.velDecay = number(z, "velDecay", where, -100.0, 100.0);
    if (z.contains("velSustain")) s.velSustain = number(z, "velSustain", where, -1.0, 1.0);
    if (z.contains("velRelease")) s.velRelease = number(z, "velRelease", where, -100.0, 100.0);
    if (z.contains("filter")) {
        const auto f = text(z, "filter", where, {"lpf_1p", "lpf_2p", "hpf_1p", "hpf_2p", "bpf_2p"});
        s.filter = f == "lpf_1p" ? Filter::Lp1 : f == "hpf_1p" ? Filter::Hp1 : f == "hpf_2p" ? Filter::Hp2 : f == "bpf_2p" ? Filter::Bp2 : Filter::Lp2;
    }
    if (z.contains("cutoff")) {
        s.cutoff = number(z, "cutoff", where, 1.0, 40000.0);
        if (s.filter == Filter::None) s.filter = Filter::Lp2;
    } else if (s.filter != Filter::None) {
        fail(where, "has a \"filter\" but no \"cutoff\" (Hz)");
    }
    for (const char* k : {"resonance", "filKeytrack", "filKeycenter", "filVeltrack"}) {
        if (z.contains(k) && s.filter == Filter::None) fail(where + "." + k, "needs a zone filter (\"cutoff\")");
    }
    if (z.contains("resonance")) s.resonance = number(z, "resonance", where, 0.0, 40.0);
    if (z.contains("filKeytrack")) s.filKeytrack = number(z, "filKeytrack", where, -1200.0, 1200.0);
    if (z.contains("filKeycenter")) s.filKeycenter = number(z, "filKeycenter", where, 0.0, 127.0);
    if (z.contains("filVeltrack")) s.filVeltrack = number(z, "filVeltrack", where, -9600.0, 9600.0);
    if (z.contains("eq")) {
        const json& e = z["eq"];
        if (!e.is_array() || e.empty() || e.size() > 3) fail(where + ".eq", "must be a list of 1..3 bands [freq Hz, bandwidth octaves, gain dB]");
        for (std::size_t i = 0; i < e.size(); ++i) {
            const std::string w = where + ".eq[" + std::to_string(i) + "]";
            if (!e[i].is_array() || e[i].size() != 3) fail(w, "must be [freq Hz, bandwidth octaves, gain dB]");
            s.eq.push_back({numberValue(e[i][0], w + "[0]", 10.0, 24000.0), numberValue(e[i][1], w + "[1]", 0.01, 8.0),
                            numberValue(e[i][2], w + "[2]", -96.0, 24.0)});
        }
    }
    if (z.contains("ampRandom")) s.ampRandom = number(z, "ampRandom", where, 0.0, 48.0);
    if (z.contains("pitchRandom")) s.pitchRandom = number(z, "pitchRandom", where, 0.0, 9600.0);
    if (z.contains("offsetRandom")) s.offsetRandom = integer64(z, "offsetRandom", where, 0, 4e9);
    if (z.contains("delay")) s.delay = number(z, "delay", where, 0.0, 100.0);
    if (z.contains("delayRandom")) s.delayRandom = number(z, "delayRandom", where, 0.0, 100.0);
    if (z.contains("width")) s.width = number(z, "width", where, 0.0, 2.0);
    if (z.contains("pedal")) {
        if (!z["pedal"].is_boolean()) fail(where + ".pedal", "must be true or false");
        s.pedal = z["pedal"].get<bool>();
    }
    if (z.contains("vibrato")) s.vibrato = quad(z, "vibrato", where, {{{-1200.0, 1200.0}, {0.0, 100.0}, {0.0, 100.0}, {0.0, 100.0}}},
                                                "[depth cents, rate Hz, delay s, fade s]");
    if (z.contains("tremolo")) s.tremolo = quad(z, "tremolo", where, {{{-96.0, 96.0}, {0.0, 100.0}, {0.0, 100.0}, {0.0, 100.0}}},
                                                "[depth dB, rate Hz, delay s, fade s]");
    if (z.contains("filterEnv")) {
        if (s.filter == Filter::None) fail(where + ".filterEnv", "needs a zone filter (\"cutoff\")");
        const json& e = z["filterEnv"];
        const char* shape = "[depth cents, delay s, attack s, hold s, decay s, sustain 0..1, release s]";
        if (!e.is_array() || e.size() != 7) fail(where + ".filterEnv", std::string("must be ") + shape);
        const double lim[7][2] = {{-12000, 12000}, {0, 100}, {0, 100}, {0, 100}, {0, 100}, {0, 1}, {0, 100}};
        for (std::size_t i = 0; i < 7; ++i) {
            s.fenv[i] = numberValue(e[i], where + ".filterEnv[" + std::to_string(i) + "]", lim[i][0], lim[i][1]);
        }
    }
    if (z.contains("channels")) {
        const json& c = z["channels"];
        const char* shape = "must be a list of [channel 0..63, gain left, gain right] (linear gains -16..16)";
        if (!c.is_array() || c.empty() || c.size() > 64) fail(where + ".channels", shape);
        if (sf2 || s.gen != Gen::None) fail(where + ".channels", "mixes the channels of a WAV file: only for WAV zones");
        for (std::size_t i = 0; i < c.size(); ++i) {
            const std::string w = where + ".channels[" + std::to_string(i) + "]";
            if (!c[i].is_array() || c[i].size() != 3) fail(w, shape);
            const double ch = numberValue(c[i][0], w + "[0]", 0.0, 63.0);
            if (ch != std::round(ch)) fail(w + "[0]", "must be a whole channel number (0 = the first)");
            s.channels.push_back({static_cast<int>(ch), static_cast<float>(numberValue(c[i][1], w + "[1]", -16.0, 16.0)),
                                  static_cast<float>(numberValue(c[i][2], w + "[2]", -16.0, 16.0))});
        }
    }
    const char* dynKeys[4] = {"xfinLoDyn", "xfinHiDyn", "xfoutLoDyn", "xfoutHiDyn"};
    for (int k = 0; k < 4; ++k) {
        if (z.contains(dynKeys[k])) s.xfDyn[static_cast<std::size_t>(k)] = integer(z, dynKeys[k], where, 0, 127);
    }
    for (int k = 0; k < 4; k += 2) {
        if (s.xfDyn[static_cast<std::size_t>(k)] > s.xfDyn[static_cast<std::size_t>(k + 1)]) {
            fail(where, std::string("has ") + dynKeys[k] + " > " + dynKeys[k + 1]);
        }
    }
    if (z.contains("xfDynCurve")) s.xfDynPower = text(z, "xfDynCurve", where, {"power", "gain"}) == "power";
    if (z.contains("dynLo")) s.dynLo = integer(z, "dynLo", where, 0, 127);
    if (z.contains("dynHi")) s.dynHi = integer(z, "dynHi", where, 0, 127);
    if (s.dynLo > s.dynHi) fail(where, "has dynLo > dynHi");
    if (z.contains("dynGain")) {
        const json& c = z["dynGain"];
        if (!c.is_array() || c.empty()) fail(where + ".dynGain", "must be a list of [dynamics 0..127, gain 0..16] points");
        double last = -1.0;
        for (std::size_t i = 0; i < c.size(); ++i) {
            const std::string w = where + ".dynGain[" + std::to_string(i) + "]";
            if (!c[i].is_array() || c[i].size() != 2) fail(w, "must be [dynamics 0..127, gain 0..16]");
            const double x = numberValue(c[i][0], w + "[0]", 0.0, 127.0);
            if (x <= last) fail(w, "dynamics values must be strictly increasing");
            last = x;
            s.dynGain.push_back({x, numberValue(c[i][1], w + "[1]", 0.0, 16.0)});
        }
    }
    if (z.contains("dynCutoff")) {
        if (s.filter == Filter::None) fail(where + ".dynCutoff", "needs a zone filter (\"cutoff\")");
        s.dynCutoff = number(z, "dynCutoff", where, -12000.0, 12000.0);
    }
    if (z.contains("legatoOffset")) s.legatoOffset = number(z, "legatoOffset", where, 0.0, 10000.0);
    if (z.contains("swLast")) {
        const json& v = z["swLast"];
        if (v.is_array()) {
            if (v.size() != 2) fail(where + ".swLast", "must be a key 0..127 or a range [lo, hi]");
            s.swLastLo = static_cast<int>(numberValue(v[0], where + ".swLast[0]", 0.0, 127.0));
            s.swLastHi = static_cast<int>(numberValue(v[1], where + ".swLast[1]", 0.0, 127.0));
            if (v[0].get<double>() != std::round(v[0].get<double>()) || v[1].get<double>() != std::round(v[1].get<double>())) {
                fail(where + ".swLast", "keys must be whole numbers");
            }
            if (s.swLastLo > s.swLastHi) fail(where + ".swLast", "has lo > hi");
        } else {
            s.swLastLo = s.swLastHi = integer(z, "swLast", where, 0, 127);
        }
    }
    if (z.contains("swDown")) s.swDown = integer(z, "swDown", where, 0, 127);
    if (z.contains("swLo")) s.swLo = integer(z, "swLo", where, 0, 127);
    if (z.contains("swHi")) s.swHi = integer(z, "swHi", where, 0, 127);
    if ((s.swLo >= 0) != (s.swHi >= 0)) fail(where, "needs both swLo and swHi (the keyswitch range)");
    if (s.swLo > s.swHi) fail(where, "has swLo > swHi");
    if (z.contains("swDefault")) s.swDefault = integer(z, "swDefault", where, 0, 127);
    if (s.gen != Gen::None) {
        for (const char* k : {"loopStart", "loopEnd", "offset", "end", "offsetRandom"}) {
            if (z.contains(k)) fail(where + "." + k, "does not apply to a generator ('" + s.file + "')");
        }
    }
    return s;
}

// ------------------------------------------------------------------------------------ regions

// Shared regions of WAV files: one per (file, reverse, loop); segment A of the file is shared by all of them.
std::shared_ptr<const smp::Region> fileRegion(const std::shared_ptr<const smp::SampleFile>& file, smp::LoopMode mode, std::int64_t ls,
                                              std::int64_t le) {
    using Key = std::tuple<std::string, bool, int, std::int64_t, std::int64_t>;
    static std::mutex mu;
    static std::map<Key, std::shared_ptr<const smp::Region>> cache;
    if (mode == smp::LoopMode::None) ls = le = 0;
    const Key key{file->path, file->reversed, static_cast<int>(mode), ls, le};
    std::lock_guard<std::mutex> lock(mu);
    const auto it = cache.find(key);
    if (it != cache.end()) return it->second;
    auto r = std::make_shared<const smp::Region>(smp::makeRegion(file->a, file->channels, file->rate, file->frames, mode, ls, le));
    cache.emplace(key, r);
    return r;
}

// Piecewise-linear velocity curve through the zone's points (plus (0, 0) and (127, 1) unless given).
float curveAt(const std::vector<std::pair<float, float>>& c, float vel) noexcept {
    if (vel <= c.front().first) return c.front().second;
    for (std::size_t i = 1; i < c.size(); ++i) {
        if (vel <= c[i].first) {
            const float t = (vel - c[i - 1].first) / std::max(1e-6f, c[i].first - c[i - 1].first);
            return c[i - 1].second + t * (c[i].second - c[i - 1].second);
        }
    }
    return c.back().second;
}

// SFZ crossfade gain of value x (velocity or key) for a fade-in [lo, hi] and a fade-out [lo, hi].
float crossfade(int x, int inLo, int inHi, int outLo, int outHi, bool power) noexcept {
    float g = 1.0f;
    if (inHi > inLo) g *= x <= inLo ? 0.0f : x >= inHi ? 1.0f : static_cast<float>(x - inLo) / static_cast<float>(inHi - inLo);
    else if (x < inLo) g = 0.0f;
    if (outHi > outLo) g *= x <= outLo ? 1.0f : x >= outHi ? 0.0f : static_cast<float>(outHi - x) / static_cast<float>(outHi - outLo);
    else if (x > outHi) g = 0.0f;
    return power ? std::sqrt(g) : g;
}

std::uint64_t mix64(std::uint64_t x) noexcept {  // splitmix64 finaliser
    x += 0x9E3779B97F4A7C15ull;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ull;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBull;
    return x ^ (x >> 31);
}

// ----------------------------------------------------------------------------------------- voice

// Envelope (amplitude or filter): delay, linear attack, hold, exponential decay to the sustain level and
// exponential release (times: 60 dB of the way), advanced once per control block of n samples.
struct Eg {
    enum Stage : std::uint8_t { Delay, Attack, Hold, Decay, Sustain, Release, Done };
    Stage stage{Done};
    float level{0.0f}, attackRate{1.0f}, decayCoef{0.0f}, sustain{1.0f}, releaseCoef{0.0f};
    int wait{0}, holdLeft{0};  // delay / hold left (samples)

    static float coef(double seconds, double sr) noexcept {
        return seconds <= 0.0 ? 0.0f : static_cast<float>(std::exp(-6.9 * smp::kControl / (seconds * sr)));
    }
    void start(double sr, double delay, double attack, double hold, double decay, double sus, double release) noexcept {
        constexpr double n = smp::kControl;
        attackRate = static_cast<float>(attack <= 0.0 ? 1.0 : std::min(1.0, n / (attack * sr)));
        decayCoef = coef(decay, sr);
        sustain = static_cast<float>(std::clamp(sus, 0.0, 1.0));
        releaseCoef = coef(std::max(kMinRelease, release), sr);
        wait = static_cast<int>(std::lround(delay * sr));
        holdLeft = static_cast<int>(std::lround(hold * sr));
        stage = wait > 0 ? Delay : Attack;
        level = 0.0f;
    }
    void release() noexcept {
        if (stage != Done) stage = Release;
    }
    void advance() noexcept {
        constexpr int n = smp::kControl;
        switch (stage) {
            case Delay:
                wait -= n;
                if (wait <= 0) stage = Attack;
                break;
            case Attack:
                level += attackRate;
                if (level >= 1.0f) {
                    level = 1.0f;
                    stage = holdLeft > 0 ? Hold : Decay;
                }
                break;
            case Hold:
                holdLeft -= n;
                if (holdLeft <= 0) stage = Decay;
                break;
            case Decay:
                level = sustain + (level - sustain) * decayCoef;
                if (std::fabs(level - sustain) < 1e-4f) {
                    level = sustain;
                    stage = Sustain;
                }
                break;
            case Sustain:
                level = sustain;
                break;
            case Release:
                level *= releaseCoef;
                if (level < kSilent) {
                    level = 0.0f;
                    stage = Done;
                }
                break;
            case Done:
                level = 0.0f;
                break;
        }
    }
};

struct Voice {
    bool active{false}, keyDown{false}, finishing{false}, stereo{false};
    bool sustained{false};   // key up, held by the sustain pedal
    bool pedalSens{true};    // the zone reacts to the pedal
    bool oneshot{false};     // ignores note-offs (zone loop "oneshot", instrument oneshot, release-triggered)
    bool untilRelease{false};
    int noteId{-1}, key{0}, vel{0};
    int choke{0};
    const Zone* zone{nullptr};
    std::uint64_t age{0};
    smp::Reader reader;
    double baseInc{1.0}, inc{1.0};
    double played{0.0};            // source frames played since the start (the level window of a legato handover)
    float amp{1.0f}, pan{0.0f}, width{1.0f};
    Eg env;                        // amplitude envelope
    int startDelay{0};             // samples before playback starts (SFZ delay)
    smp::Lowpass lp[2];
    smp::LowpassCoefs coefs;
    Filter zf{Filter::None};       // the zone's own filter: static per note, or moved by its filter envelope
    float zfHz{20000.0f}, zfQ{0.7071f}, fenvDepth{0.0f};
    Eg fenv;
    dsp::Biquad zb[2];
    dsp::OnePole zo[2];
    int eqCount{0};
    dsp::Biquad eq[3][2];
    float vibDepth{0.0f}, vibInc{0.0f}, vibPhase{0.0f}, vibFade{1.0f}, vibFadeStep{1.0f};
    float tremDepth{0.0f}, tremInc{0.0f}, tremPhase{0.0f}, tremFade{1.0f}, tremFadeStep{1.0f};
    int vibWait{0}, tremWait{0};   // LFO delays (control blocks)
    int ctl{0};
    std::array<float, 4> g{}, dg{};  // mono: L, R; stereo: LL, LR, RL, RR
    std::array<float, 4> tg{};       // the targets the gains ramp to in the current control block
    float fade{1.0f}, fadeStep{0.0f};
    // live dynamics: the zone's own mapping and / or a place in the note's layer stack (layers='dynamics')
    bool dynLive{false}, layered{false};
    float layerLo{-1.0f}, layerMid{0.0f}, layerHi{-1.0f};   // neighbour layer centres (-1: none) and its own
    float dynG{1.0f};                // last dynamics gain
    bool zfMoves{false};             // zone filter recomputed per control block (filter envelope, dynCutoff)
    bool silent{false};              // skipped while silent (a layer faded out): resumes phase-aligned
    // legato: equal-power handover (lgDir +1 fading in, -1 fading out), level match, portamento
    int lgDir{0};
    float lgPos{1.0f}, lgStep{0.0f}, lgFrom{1.0f};   // fading out: lgFrom x cos(lgPos pi/2)
    float matchDb{0.0f}, matchStep{0.0f};
    int matchLeft{0};
    float glideCents{0.0f}, glideFrom{0.0f}, glideTo{0.0f}, glidePos{1.0f}, glideStep{0.0f};
    int glideShape{1};
    float damp{1.0f};                // half pedal: extra damping of a pedal-held note
    float bendScale{1.0f};           // 'bendfollow' latched at the note-on
    // 'harmonic': the note's partial isolated (two band-passes per channel) and level-matched
    double hz0{440.0};               // the note's fundamental (Hz) before bends / glides / vibrato
    bool hOn{false};
    float ha1{1.0f}, ha2{0.0f}, ha3{0.0f}, hk{0.1f};
    float hs[2][2][2]{};             // [channel][stage][ic1, ic2]
    float hEnvX{0.0f}, hEnvH{0.0f}, hPeak{0.0f}, hGain{1.0f}, hdGain{0.0f};
    float hWarm{0.0f};               // a cold start fades the partial in while its band-passes and envelopes settle
    float hA{0.0f};                  // the amount at the end of the last block (ramped per sample: no zipper)
    float rs{1.0f}, rsTarget{1.0f};  // re-strike damping: the gain and where it glides (restrike)
};

struct Held {
    int noteId{-1}, key{0}, vel{0};
    std::int64_t onSample{0};
    bool down{false}, pending{false};  // pending: released while the pedal was down (release zones wait for pedal-up)
    bool handed{false};                // mono='legato': its voices crossfaded into a later note (no release zones)
};

// Equal-power legato gain at crossfade position p (0..1) for a voice fading in (+1) or out (-1).
// A voice fading out scales the gain it had when its fade began (`from`) by cos: every voice of a line fades out
// together, so a transition that starts before the previous one ended keeps the line's power (sum of squares).
inline float legatoGain(int dir, float p, float from = 1.0f) noexcept {
    if (dir == 0) return 1.0f;
    const float x = std::clamp(p, 0.0f, 1.0f) * 1.57079633f;
    return dir > 0 ? std::sin(x) : from * std::cos(x);
}

// Crossfade gain of a (float) value x for a fade-in [lo, hi] and a fade-out [lo, hi] (the SFZ rule on a live value).
float crossfadeAt(float x, const std::array<float, 4>& f, bool power) noexcept {
    float g = 1.0f;
    if (f[1] > f[0]) g *= x <= f[0] ? 0.0f : x >= f[1] ? 1.0f : (x - f[0]) / (f[1] - f[0]);
    else if (x < f[0]) g = 0.0f;
    if (f[3] > f[2]) g *= x <= f[2] ? 1.0f : x >= f[3] ? 0.0f : (f[3] - x) / (f[3] - f[2]);
    else if (x > f[3]) g = 0.0f;
    return power ? std::sqrt(g) : g;
}

// Gain of a velocity layer (centre `mid`) in a dynamics stack at x (0..127): equal-power crossfades between
// neighbouring centres; a layer without a neighbour on one side holds full level there.
float layerGain(float x, float lo, float mid, float hi) noexcept {
    if (x < mid) {
        if (lo < 0.0f) return 1.0f;
        const float t = (x - lo) / std::max(1e-3f, mid - lo);
        return t <= 0.0f ? 0.0f : std::sin(std::min(t, 1.0f) * 1.57079633f);
    }
    if (hi < 0.0f) return 1.0f;
    const float t = (hi - x) / std::max(1e-3f, hi - mid);
    return t <= 0.0f ? 0.0f : std::sin(std::min(t, 1.0f) * 1.57079633f);
}

// Portamento curve 0..1 -> 0..1: linear, ease (smoothstep), fast (exponential approach).
inline float glideCurve(int shape, float p) noexcept {
    p = std::clamp(p, 0.0f, 1.0f);
    if (shape == 0) return p;
    if (shape == 1) return p * p * (3.0f - 2.0f * p);
    return (1.0f - std::exp(-5.0f * p)) / (1.0f - std::exp(-5.0f));
}

// Sympathetic resonance: 88 piano strings (A0..C8) as feedback combs (each rings at its fundamental and harmonics)
// excited by the instrument's own output. A string rings long while its damper is lifted (pedal down, or its key
// held) and is damped in ~60 ms otherwise; the keys that sound themselves take no input (their strings are in the
// samples). Mono excitation, each string panned by pitch like a piano heard from the player (bass left) at half
// width. All buffers are sized in prepare(); process() does no allocation.
class StringBank {
public:
    static constexpr int kLow = 21, kCount = 88;

    void prepare(double sr, int maxBlock) {
        sr_ = sr;
        mono_.assign(static_cast<std::size_t>(std::max(1, maxBlock)), 0.0f);
        std::size_t total = 0;
        for (int i = 0; i < kCount; ++i) {
            const double f0 = 440.0 * std::exp2((kLow + i - 69) / 12.0);
            S& s = s_[static_cast<std::size_t>(i)];
            // loop lowpass: the higher partials of a string die faster (brighter strings in the treble); its delay
            // at low frequencies (c / (1 - c) samples) comes off the line so the string stays in tune
            s.lpc = static_cast<float>(std::clamp(0.45 - 0.35 * i / (kCount - 1.0), 0.08, 0.45));
            const double d = sr / f0 - s.lpc / (1.0 - s.lpc);
            s.len = static_cast<int>(std::floor(d)) + 2;
            s.frac = static_cast<float>(d - std::floor(d));
            s.off = total;
            total += static_cast<std::size_t>(s.len) + 1;
            // undamped decay: ~20 s at A0 .. ~4 s at C8 (the aftersound of a grand's strings); damped: 60 ms
            const double t60 = 20.0 * std::pow(4.0 / 20.0, static_cast<double>(i) / (kCount - 1));
            s.gFree = static_cast<float>(std::pow(10.0, -3.0 * d / (sr * t60)));
            s.gDamped = static_cast<float>(std::pow(10.0, -3.0 * d / (sr * 0.06)));
            // excitation: 0.07 x sqrt(1 - loop gain) (between flat and resonance-normalised coupling);
            // the bass strings couple less (a sampled grand's low notes carry their own long ring; a full-strength
            // bass halo reads boomier, +1..1.5 dB of sub and bass): none below A1, 35 % at A1 rising to full coupling at C4
            s.in = i < 12 ? 0.0f : static_cast<float>(0.07 * std::sqrt(1.0 - s.gFree) * std::min(1.0, 0.35 + 0.65 * (i - 12) / 27.0));
            float gl = 0.0f, gr = 0.0f;
            dsp::panGains(static_cast<float>((i - kCount / 2.0) / (kCount / 2.0) * 0.5), gl, gr);
            s.gl = gl;
            s.gr = gr;
            s.g = s.gDamped;
            s.w = 0;
            s.run = 0;
            s.quiet = true;
            s.lp = 0.0f;
        }
        buf_.assign(total, 0.0f);
        gSmooth_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.005 * sr)));
        energy_ = 0.0f;
    }

    bool ringing() const noexcept { return energy_ > 1e-9f; }

    // amount 0..1, pedal 0..1 (0 = up, 1 = fully down), lifted: keys held down, struck: keys sounding now
    void process(float* L, float* R, int frames, float amount, float pedal, const std::array<bool, 128>& lifted,
                 const std::array<bool, 128>& struck) noexcept {
        const float drive = amount * amount * 2.0f;
        float peak = 0.0f;
        const int n0 = std::min(frames, static_cast<int>(mono_.size()));
        for (int n = 0; n < n0; ++n) mono_[static_cast<std::size_t>(n)] = 0.5f * (L[n] + R[n]);   // the dry excitation
        frames = n0;
        for (int i = 0; i < kCount; ++i) {
            S& s = s_[static_cast<std::size_t>(i)];
            const auto key = static_cast<std::size_t>(kLow + i);
            const float open = lifted[key] ? 1.0f : pedal;           // 0 damped .. 1 free
            const float target = s.gDamped + (s.gFree - s.gDamped) * open * open;
            const float in = struck[key] ? 0.0f : s.in * drive;
            if (in == 0.0f && s.quiet) continue;   // silent and not being excited: nothing to do
            // the damper moves over ~5 ms (per sample, so the output does not depend on the block size); a string
            // that starts ringing again starts at its damper's position (that happens at an event: a block start)
            if (s.quiet) s.g = target;
            float g = s.g;
            const float gk = gSmooth_;
            float* b = buf_.data() + s.off;
            float lp = s.lp;
            int w = s.w, run = s.run;
            const int len = s.len;
            const float fr = s.frac, c = s.lpc;
            bool quiet = false;
            for (int n = 0; n < frames; ++n) {
                // read the delayed sample d = len - 2 + frac behind the write position (linear interpolation)
                int r0 = w - (len - 2);
                if (r0 < 0) r0 += len;
                int r1 = r0 - 1;
                if (r1 < 0) r1 += len;
                const float y = b[r0] + (b[r1] - b[r0]) * fr;
                lp += (1.0f - c) * (y - lp);
                g += (target - g) * gk;
                const float ring = g * lp;                              // what the string radiates
                b[w] = mono_[static_cast<std::size_t>(n)] * in + ring;  // excitation + the travelling wave
                if (++w == len) w = 0;
                L[n] += ring * s.gl;
                R[n] += ring * s.gr;
                const float a = std::fabs(ring);
                peak = std::max(peak, a);
                run = a < 1e-7f && in == 0.0f ? run + 1 : 0;
                if (run > len) {   // a whole period under -140 dB and no input: the string has died away
                    std::fill_n(b, len, 0.0f);
                    lp = 0.0f;
                    run = 0;
                    quiet = true;
                    break;
                }
            }
            s.lp = lp;
            s.g = g;
            s.w = w;
            s.run = run;
            s.quiet = quiet;
        }
        energy_ = peak;
    }

private:
    struct S {
        std::size_t off{0};
        int len{2}, w{0};
        float frac{0.0f}, g{0.0f}, gFree{0.0f}, gDamped{0.0f}, lpc{0.3f}, lp{0.0f}, in{0.0f}, gl{0.7f}, gr{0.7f};
        int run{0};         // consecutive samples under -140 dB without input
        bool quiet{true};
    };
    double sr_{48000.0};
    std::array<S, kCount> s_{};
    std::vector<float> buf_, mono_;
    float energy_{0.0f}, gSmooth_{0.004f};
};

class Sampler final : public Instrument {
public:
    Sampler() : params_(makeSpecs()) {}

    void configure(const json& params) override {
        params_.configure(params, "sampler", {"samples"});
        if (!params.is_object() || !params.contains("samples")) {
            throw ConfigError("sampler: 'samples' is required: {\"dir\": \"samples/<folder>\"} (WAVs named by note or GM drum), "
                              "{\"file\": \"samples/x.wav\", \"root\": 60} or a list of such zones");
        }
        const json& s = params["samples"];
        dir_.clear();
        dirLoop_ = ZoneLoop::None;
        dirGain_ = 0.0;
        specs_.clear();
        if (s.is_object() && s.contains("dir")) {
            allowOnly(s, {"dir", "loop", "gain"}, "samples");
            if (!s["dir"].is_string() || s["dir"].get<std::string>().empty()) fail("samples.dir", "must be a folder path (relative to assets/ or absolute)");
            dir_ = s["dir"].get<std::string>();
            if (s.contains("loop")) dirLoop_ = zoneLoop(text(s, "loop", "samples", {"none", "oneshot", "forward", "pingpong", "sustain", "auto"}));
            if (s.contains("gain")) dirGain_ = number(s, "gain", "samples", -60.0, 24.0);
        } else if (s.is_object()) {
            specs_.push_back(parseZone(s, "samples"));
        } else if (s.is_array()) {
            if (s.empty()) fail("samples", "is an empty list");
            specs_.reserve(s.size());
            for (std::size_t i = 0; i < s.size(); ++i) specs_.push_back(parseZone(s[i], "samples[" + std::to_string(i) + "]"));
        } else {
            fail("samples", "must be {\"dir\": ...}, one zone object or a list of zones");
        }
        for (const int p : {kTranspose, kPolyphony, kXfSpread}) {
            const float value = params_.get(p);
            if (value != std::round(value)) throw ConfigError("sampler: '" + params_.specs()[static_cast<std::size_t>(p)].name + "' must be a whole number");
        }
    }

    void setTempoMap(const TempoMap& map) override { tempoMap_ = &map; }

    void prepare(const RenderContext& ctx) override {
        sr_ = ctx.sampleRate;
        smp::Kernel::get();  // build the interpolation tables now, not in the first process()
        reverse_ = params_.choice("reverse") == 1;
        oneshot_ = params_.choice("oneshot") == 1;
        mono_ = params_.choice("mono") == 1;
        legatoMode_ = params_.choice("mono") == 2;
        layersDyn_ = params_.choice("layers") == 1;
        xfSpread_ = static_cast<int>(params_.get(kXfSpread));
        std::vector<ZoneSpec> specs = dir_.empty() ? specs_ : expandDir(ctx.assetDir);
        loadZones(ctx.assetDir, specs);

        poly_ = static_cast<int>(params_.get(kPolyphony));
        voices_.assign(static_cast<std::size_t>(poly_ + std::max(8, poly_ / 2)), Voice{});
        playLayer_.clear();
        playLayer_.reserve(zones_.size() + 1);
        if (legatoMode_) {  // level tracks: the scripted-legato entry points and the level match
            for (auto& z : zones_) {
                if (z.region) z.levels = smp::levelTrack(*z.region);
            }
        }
        const int maxBlock = std::max(1, ctx.maxBlock);
        mixL_.assign(static_cast<std::size_t>(maxBlock), 0.0f);
        mixR_.assign(static_cast<std::size_t>(maxBlock), 0.0f);
        transpose_ = static_cast<int>(params_.get(kTranspose));
        stealStep_ = static_cast<float>(1.0 / (kStealSeconds * sr_));
        offStep_ = static_cast<float>(1.0 / (kOffFastSeconds * sr_));
        chokeCoef_ = static_cast<float>(std::exp(-6.9 * smp::kControl / (kChokeSeconds * sr_)));
        rsCoef_ = static_cast<float>(std::exp(-smp::kControl / (kRestrikeSeconds * sr_)));
        age_ = 0;
        seed_ = ctx.seed ^ dsp::hashString("as.instrument.sampler");
        startSample_ = songStartSample(ctx.startBeat, sr_, ctx.bpm, tempoMap_);   // song position (tempo map aware)
        clock_ = 0;
        seqCount_.assign(zones_.size(), 0u);
        playing_.clear();
        playing_.reserve(zones_.size() + 1);
        heldCount_ = 0;
        keysDown_ = 0;
        pedalDown_ = params_.get(kPedal) >= 0.5f;
        applyPedal();
        strings_.prepare(sr_, std::max(1, ctx.maxBlock));
        bend_ = bend1_ = params_.get(kPitchbend);
        cutoff_ = cutoff1_ = params_.get(kCutoff);
        res_ = res1_ = params_.get(kResonance);
        pan_ = pan1_ = params_.get(kPan);
        width_ = width1_ = params_.get(kWidth);
        gain_ = gain1_ = outGain_ = outputGain();
        dyn_ = dyn1_ = params_.get(kDynamics);
        vib_ = vib1_ = params_.get(kVibrato);
        vibRate_ = vibRate1_ = params_.get(kVibratoRate);
        vibPhase_ = 0.0;
        harm_ = harm1_ = params_.get(kHarmonic);
        harmActive_ = harm_ > 0.0f;
        hEnvCoef_ = static_cast<float>(1.0 - std::exp(-1.0 / (kHarmEnvTau * sr_)));
        hPeakFall_ = static_cast<float>(std::pow(10.0, -kHarmPeakFallDb / 10.0 * smp::kControl / sr_));
        dynTone_ = params_.get(kDynTone);
        const float bright = dynTone_ > 0.0f ? -dynTone_ * (1.0f - dyn_) : 0.0f;
        tiltOn_ = bright != 0.0f;   // at its initial brightness already (a preview render starts where a full one is)
        tilt_.prepare(sr_, bright);
        lineFadeStep_ = static_cast<float>(1.0 / (kLineFadeSeconds * sr_));
        swLast_ = swDefault_;
        swHeld_.fill(false);
        swNoteCount_ = 0;
    }

    bool setParam(std::string_view name, float value) override {
        if (!params_.set(name, value)) return false;
        if (name == "pedal") applyPedal();
        return true;
    }

    void noteOn(int noteId, int pitch, float velocity) override {
        if (pitch >= 0 && pitch <= 127 && swKey_[static_cast<std::size_t>(pitch)]) {  // a keyswitch: selects, never sounds
            keyswitchOn(noteId, pitch);
            return;
        }
        const int key = pitch + transpose_;
        const int vel = std::clamp(static_cast<int>(std::lround(velocity * 127.0f)), 1, 127);
        const std::int64_t now = startSample_ + clock_;
        const bool legato = keysDown_ > 0;
        if (heldCount_ == kMaxHeld) {  // full (a pedal held down for a very long time): forget the oldest released note
            for (int i = 0; i < heldCount_; ++i) {
                if (!held_[static_cast<std::size_t>(i)].down) {
                    removeHeld(i);
                    break;
                }
            }
        }
        if (heldCount_ < kMaxHeld) {
            held_[static_cast<std::size_t>(heldCount_++)] = Held{noteId, key, vel, now, true, false};
            ++keysDown_;
        }
        if (key < 0 || key > 127) return;
        playNote(noteId, key, vel, now, legato, false);
    }

    // A note of a held key starts sounding: at its note-on, or (returning) when mono='legato' goes back to a key
    // still held after the line's newer note was released. Returning only continues a legato line (else nothing
    // happens and false is returned).
    bool playNote(int noteId, int key, int vel, std::int64_t now, bool legato, bool returning) {
        if (returning && !hasLineVoices()) return false;
        if (mono_) {
            for (auto& v : voices_) {
                if (v.active && v.fadeStep <= 0.0f) fadeInPlace(v, stealStep_);
            }
        }
        if (!legato) vibPhase_ = 0.0;   // vibrato starts afresh with a phrase, runs on through legato notes
        const float rnd = random01(static_cast<std::uint64_t>(now), static_cast<std::uint64_t>(key), 0x6E6F74656F6Eull);
        const int dynNow = static_cast<int>(std::lround(params_.get(kDynamics) * 127.0f));
        playing_.clear();
        for (const int zi : onZones_[static_cast<std::size_t>(key)]) {
            const Zone& z = zones_[static_cast<std::size_t>(zi)];
            if ((!layersDyn_ && (vel < z.vello || vel > z.velhi)) || rnd < z.lorand || rnd >= z.hirand) continue;
            if ((z.trigger == Trigger::First && legato) || (z.trigger == Trigger::Legato && !legato)) continue;
            if (!switchOk(z) || dynNow < z.dynLo || dynNow > z.dynHi) continue;
            if (!nextInSequence(zi, z)) continue;
            playing_.push_back(zi);
        }
        playLayer_.assign(playing_.size(), {-1.0f, -1.0f, -1.0f});
        if (layersDyn_) assignLayers(params_.get(kDynamics) * 127.0f);
        // a legato transition needs a line to continue and a sustained note to go to (one-shot zones - staccato,
        // pizzicato programs - attack: detached notes)
        const bool line = legatoMode_ && legato && hasLineVoices() &&
                          std::any_of(playing_.begin(), playing_.end(), [this](int zi) {
                              const Zone& z = zones_[static_cast<std::size_t>(zi)];
                              return z.region && !z.oneshot && !oneshot_;
                          });
        if (returning && !line) return false;
        if (legatoMode_ && !line) {  // a new phrase of a monophonic player: the tail of the previous one gives way
            for (auto& v : voices_) {
                if (v.active && !v.oneshot && v.fadeStep <= 0.0f) fadeInPlace(v, lineFadeStep_);
            }
        }
        if (line) {
            Handoff ho;
            beginHandoff(ho, key, noteId);
            startZones(noteId, key, vel, now, 0.0, false, &ho);
            finishHandoff(ho, noteId);
            return true;
        }
        startZones(noteId, key, vel, now, 0.0, false);
        return true;
    }

    // mono='legato': the sounding note of the line is released while an earlier key is still held (a trill or
    // grace note played over a held note): the line goes back to that key with a legato transition, like a player
    // (last-note priority). The released note hands over (no key-up noise); the key it returns to plays on.
    bool returnToHeld(int h) {
        const int released = held_[static_cast<std::size_t>(h)].noteId;
        const bool sounding = std::any_of(voices_.begin(), voices_.end(), [&](const Voice& v) { return lineVoice(v) && v.noteId == released; });
        if (!sounding) return false;
        int back = -1;   // the latest key still held
        for (int i = 0; i < heldCount_; ++i) {
            const Held& b = held_[static_cast<std::size_t>(i)];
            if (b.down && b.key >= 0 && b.key <= 127) back = i;
        }
        if (back < 0) return false;
        const Held target = held_[static_cast<std::size_t>(back)];
        if (!playNote(target.noteId, target.key, target.vel, startSample_ + clock_, true, true)) return false;
        held_[static_cast<std::size_t>(back)].handed = false;   // it sounds again: its key-up noises fire at its note-off
        held_[static_cast<std::size_t>(h)].handed = true;
        return true;
    }

    void noteOff(int noteId) override {
        for (int i = 0; i < swNoteCount_; ++i) {  // a keyswitch note
            if (swNotes_[static_cast<std::size_t>(i)].first != noteId) continue;
            const int k = swNotes_[static_cast<std::size_t>(i)].second;
            for (int j = i; j + 1 < swNoteCount_; ++j) swNotes_[static_cast<std::size_t>(j)] = swNotes_[static_cast<std::size_t>(j + 1)];
            --swNoteCount_;
            bool still = false;
            for (int j = 0; j < swNoteCount_; ++j) still = still || swNotes_[static_cast<std::size_t>(j)].second == k;
            swHeld_[static_cast<std::size_t>(k)] = still;
            return;
        }
        int h = -1;
        for (int i = 0; i < heldCount_; ++i) {
            if (held_[static_cast<std::size_t>(i)].noteId == noteId && held_[static_cast<std::size_t>(i)].down) { h = i; break; }
        }
        if (h >= 0) {
            held_[static_cast<std::size_t>(h)].down = false;
            --keysDown_;
        }
        if (oneshot_) {
            if (h >= 0) removeHeld(h);
            return;
        }
        if (legatoMode_ && h >= 0 && keysDown_ > 0) returnToHeld(h);   // its voices hand over (none left to release)
        for (auto& v : voices_) {
            if (!v.active || !v.keyDown || v.noteId != noteId) continue;
            v.keyDown = false;
            if (v.oneshot) continue;
            if (pedalDown_ && v.pedalSens) {
                v.sustained = true;
                continue;
            }
            release(v);
        }
        if (h < 0) return;
        const Held note = held_[static_cast<std::size_t>(h)];
        if (note.handed) {  // legato: this note's sound went on into the next one (no key-up noises)
            removeHeld(h);
            return;
        }
        fireRelease(note, false);
        if (pedalDown_ && hasPedalReleaseZones_) held_[static_cast<std::size_t>(h)].pending = true;
        else removeHeld(h);
    }

    void process(float* left, float* right, int frames) override {
        if (frames <= 0) return;
        updateControls(frames);
        std::fill_n(mixL_.data(), frames, 0.0f);
        std::fill_n(mixR_.data(), frames, 0.0f);
        for (auto& v : voices_) {
            if (v.active) renderVoice(v, mixL_.data(), mixR_.data(), frames);
        }
        const float symp = params_.get(kSympathetic);
        if (symp > 0.0f || strings_.ringing()) {
            // dampers: lifted by the pedal (a half pedal lifts them part-way) or by a held key; the struck keys'
            // own strings are in the samples, so they take no input
            std::array<bool, 128> lifted{}, struck{};
            for (int i = 0; i < heldCount_; ++i) {
                const Held& h = held_[static_cast<std::size_t>(i)];
                if (h.down && h.key >= 0 && h.key <= 127) lifted[static_cast<std::size_t>(h.key)] = true;
            }
            for (const auto& v : voices_) {
                if (v.active && !v.finishing && (v.keyDown || v.sustained) && v.key >= 0 && v.key <= 127)
                    struck[static_cast<std::size_t>(v.key)] = true;
            }
            const float p = params_.get(kPedal);
            const float pedal = p < 0.5f ? 0.0f : std::min(1.0f, (p - 0.5f) / 0.495f);
            strings_.process(mixL_.data(), mixR_.data(), frames, symp, pedal, lifted, struck);
        }
        vibPhase_ += static_cast<double>(vibRate_) / sr_ * frames;
        vibPhase_ -= std::floor(vibPhase_);
        // dynamics-linked brightness (a tilt: darker below dynamics 1); bypassed while flat
        const float bright = dynTone_ > 0.0f ? -dynTone_ * (1.0f - dyn_) : 0.0f;
        if (bright != 0.0f || tiltOn_) {
            if (!tiltOn_) tilt_.prepare(sr_, 0.0f);   // fresh filter states: the tilt ramps in from flat
            tilt_.process(mixL_.data(), mixR_.data(), frames, bright);
            tiltOn_ = bright != 0.0f;
        }
        float g = outGain_;
        const float dg = (gain_ - outGain_) / static_cast<float>(frames);
        for (int i = 0; i < frames; ++i) {
            g += dg;
            left[i] = mixL_[static_cast<std::size_t>(i)] * g;
            right[i] = mixR_[static_cast<std::size_t>(i)] * g;
        }
        outGain_ = gain_;
        clock_ += frames;
    }

    bool idle() const override {
        return std::none_of(voices_.begin(), voices_.end(), [](const Voice& v) { return v.active; }) &&
               (!tiltOn_ || tilt_.settled()) && !strings_.ringing();
    }

    const std::vector<ParamSpec>& paramSpecs() const override { return params_.specs(); }

private:
    // ------------------------------------------------------------------------------ loading

    std::vector<ZoneSpec> expandDir(const std::string& assetDir) const {
        const std::string path = resolveAsset(assetDir, dir_);
        std::error_code ec;
        if (!fs::is_directory(fs::path(path), ec)) fail("samples.dir", "'" + dir_ + "' is not a folder (resolved to '" + path + "')");
        std::vector<fs::path> files;
        for (const auto& e : fs::directory_iterator(fs::path(path), ec)) {
            if (e.is_regular_file() && lowerExt(e.path()) == ".wav") files.push_back(e.path());
        }
        std::sort(files.begin(), files.end());
        if (files.empty()) fail("samples.dir", "'" + path + "' contains no .wav files");
        struct Mapped { fs::path file; int key; bool drum; };
        std::vector<Mapped> mapped;
        for (const auto& f : files) {
            std::string stem = f.stem().string();
            std::string norm;
            for (const char c : stem) norm.push_back(c == ' ' || c == '-' ? '_' : static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
            int key = -1;
            bool drum = false;
            const auto& drums = drumNames();
            if (const auto it = drums.find(norm); it != drums.end()) {
                key = it->second;
                drum = true;
            } else if (!parseNoteName(stem, key)) {
                fail("samples.dir", "cannot map '" + f.filename().string() + "': name the files by note (C4.wav, F#3.wav, Bb2.wav, "
                     "60.wav) or by GM drum (kick, snare, rim, clap, hat, pedal, ohh, tom_lo, tom_mid, tom_hi, crash, ride, tamb, cowbell)");
            }
            for (const auto& m : mapped) {
                if (m.key == key) fail("samples.dir", "'" + m.file.filename().string() + "' and '" + f.filename().string() + "' both map to key " + std::to_string(key));
            }
            mapped.push_back({f, key, drum});
        }
        const bool drumKit = std::any_of(mapped.begin(), mapped.end(), [](const Mapped& m) { return m.drum; });
        std::sort(mapped.begin(), mapped.end(), [](const Mapped& a, const Mapped& b) { return a.key < b.key; });
        std::vector<ZoneSpec> out;
        for (std::size_t i = 0; i < mapped.size(); ++i) {
            ZoneSpec s;
            s.file = mapped[i].file.string();
            s.where = "samples.dir file '" + mapped[i].file.filename().string() + "'";
            s.root = mapped[i].key;
            s.loop = dirLoop_;
            s.gainDb = dirGain_;
            if (drumKit) {  // every file on its own key; the hi-hats choke each other
                s.lo = s.hi = mapped[i].key;
                if (s.lo == 42 || s.lo == 44 || s.lo == 46) s.choke = 1;
            } else {        // spread: each sample covers the keys closest to its root
                s.lo = i == 0 ? 0 : (mapped[i - 1].key + mapped[i].key) / 2 + 1;
                s.hi = i + 1 == mapped.size() ? 127 : (mapped[i].key + mapped[i + 1].key) / 2;
            }
            out.push_back(std::move(s));
        }
        return out;
    }

    void loadZones(const std::string& assetDir, const std::vector<ZoneSpec>& specs) {
        // every WAV at once (in parallel, shared with other instruments and tracks), then the zones
        std::vector<smp::FileRequest> paths;
        for (const auto& s : specs) {
            if (s.gen == Gen::None && lowerExt(fs::path(s.file)) != ".sf2") paths.push_back({resolveAsset(assetDir, s.file), s.channels});
        }
        smp::LoadStats stats;
        const auto errors = smp::preloadSampleFiles(paths, reverse_, &stats);
        zones_.clear();
        zones_.reserve(specs.size());
        for (const auto& spec : specs) zones_.push_back(loadZone(assetDir, spec, errors));
        // Per-zone randomness (amp / pitch / offset / delay random) is keyed by what the zone is, not by its position in
        // the list, so dropping zones (Song.compile prunes the ones no note reaches) leaves the other notes unchanged.
        std::map<std::uint64_t, std::uint64_t> seen;
        for (std::size_t i = 0; i < zones_.size(); ++i) {
            const ZoneSpec& sp = specs[i];
            const Zone& z = zones_[i];
            std::uint64_t h = dsp::hashString((sp.file + '|' + sp.sample).c_str());
            for (const std::int64_t x : {static_cast<std::int64_t>(z.lo), static_cast<std::int64_t>(z.hi),
                                         static_cast<std::int64_t>(z.vello), static_cast<std::int64_t>(z.velhi),
                                         static_cast<std::int64_t>(z.seqPosition), static_cast<std::int64_t>(z.trigger),
                                         static_cast<std::int64_t>(std::llround(sp.lorand * 1e6)), z.group}) {
                h = mix64(h ^ static_cast<std::uint64_t>(x));
            }
            zones_[i].salt = mix64(h + seen[h]++);   // identical zones (layers of one file) still differ
        }
        for (auto& list : onZones_) list.clear();
        for (auto& list : offZones_) list.clear();
        // keyswitches: the keys that select articulations (explicit ranges, sw_last keys, sw_down keys) never sound
        swKey_.fill(false);
        swLastKey_.fill(false);
        swDefault_ = -1;
        for (const auto& sp : specs) {
            auto mark = [&](int lo, int hi, bool last) {
                for (int k = std::max(0, lo); k <= std::min(127, hi); ++k) {
                    swKey_[static_cast<std::size_t>(k)] = true;
                    if (last) swLastKey_[static_cast<std::size_t>(k)] = true;
                }
            };
            if (sp.swLo >= 0) mark(sp.swLo, sp.swHi, true);
            if (sp.swLastLo >= 0) mark(sp.swLastLo, sp.swLastHi, true);
            if (sp.swDown >= 0) mark(sp.swDown, sp.swDown, false);
            if (sp.swDefault >= 0) {
                if (swDefault_ >= 0 && swDefault_ != sp.swDefault) {
                    fail(sp.where, "has swDefault " + std::to_string(sp.swDefault) + " but an earlier zone set " + std::to_string(swDefault_) +
                                   " (one default articulation per instrument)");
                }
                swDefault_ = sp.swDefault;
            }
        }
        hasPedalReleaseZones_ = false;
        for (std::size_t i = 0; i < zones_.size(); ++i) {
            const Zone& z = zones_[i];
            const bool release = z.trigger == Trigger::Release || z.trigger == Trigger::ReleaseKey;
            if (z.trigger == Trigger::Release && z.pedal) hasPedalReleaseZones_ = true;
            for (int k = z.lo; k <= z.hi; ++k) (release ? offZones_ : onZones_)[static_cast<std::size_t>(k)].push_back(static_cast<int>(i));
        }
        if (verbose()) {
            std::fprintf(stderr, "sampler: %zu zones, %d files (%d loaded, %d shared) %.1f MB in memory (%.1f MB read) in %.2f s\n",
                         zones_.size(), stats.requested, stats.loaded, stats.cached, static_cast<double>(stats.bytes) / 1048576.0,
                         static_cast<double>(stats.fileBytes) / 1048576.0, stats.seconds);
        }
    }

    Zone loadZone(const std::string& assetDir, const ZoneSpec& spec, const std::map<std::string, std::string>& errors) const {
        Zone z;
        z.lo = spec.lo;
        z.hi = spec.hi;
        z.vello = spec.vello;
        z.velhi = spec.velhi;
        z.gain = dsp::dbToGain(static_cast<float>(spec.gainDb));
        z.pan = static_cast<float>(spec.pan);
        z.choke = spec.choke;
        z.tune = spec.tune;
        z.keytrack = spec.keytrack;
        z.seqLength = spec.seqLength;
        z.seqPosition = spec.seqPosition;
        z.lorand = static_cast<float>(spec.lorand);
        z.hirand = spec.hirand >= 1.0 ? 2.0f : static_cast<float>(spec.hirand);  // hirand 1 includes the top
        z.trigger = spec.trigger;
        z.rtDecay = static_cast<float>(spec.rtDecay);
        z.group = spec.group;
        z.hasOffBy = spec.offBy.has_value();
        z.offBy = spec.offBy.value_or(0);
        z.offMode = spec.offMode;
        z.offTime = static_cast<float>(spec.offTime);
        z.notePolyphony = spec.notePolyphony;
        z.groupPolyphony = spec.groupPolyphony;
        z.hasVeltrack = spec.veltrack.has_value();
        z.veltrack = static_cast<float>(spec.veltrack.value_or(1.0));
        if (!spec.velcurve.empty()) {
            if (spec.velcurve.front().first > 0.0) z.velcurve.push_back({0.0f, 0.0f});
            for (const auto& [v, gg] : spec.velcurve) z.velcurve.push_back({static_cast<float>(v), static_cast<float>(gg)});
            if (spec.velcurve.back().first < 127.0) z.velcurve.push_back({127.0f, 1.0f});
        }
        z.xf = spec.xf;
        z.xfVelPower = spec.xfVelPower;
        z.xfKeyPower = spec.xfKeyPower;
        auto opt = [](const std::optional<double>& o) { return o ? static_cast<float>(*o) : kNoValue; };
        z.envDelay = static_cast<float>(spec.envDelay.value_or(0.0));
        z.attack = opt(spec.attack);
        z.hold = static_cast<float>(spec.hold.value_or(0.0));
        z.decay = opt(spec.decay);
        z.sustain = opt(spec.sustain);
        z.release = opt(spec.release);
        z.velAttack = static_cast<float>(spec.velAttack);
        z.velHold = static_cast<float>(spec.velHold);
        z.velDecay = static_cast<float>(spec.velDecay);
        z.velSustain = static_cast<float>(spec.velSustain);
        z.velRelease = static_cast<float>(spec.velRelease);
        z.filter = spec.filter;
        z.cutoff = static_cast<float>(spec.cutoff);
        z.filterQ = static_cast<float>(std::max(0.7071, std::pow(10.0, spec.resonance / 20.0)));
        z.filKeytrack = static_cast<float>(spec.filKeytrack);
        z.filKeycenter = static_cast<float>(spec.filKeycenter);
        z.filVeltrack = static_cast<float>(spec.filVeltrack);
        z.eqCount = 0;
        for (const auto& band : spec.eq) {
            if (band[2] == 0.0) continue;
            z.eq[static_cast<std::size_t>(z.eqCount++)] = {static_cast<float>(band[0]), static_cast<float>(band[1]), static_cast<float>(band[2])};
        }
        z.ampRandom = static_cast<float>(spec.ampRandom);
        z.pitchRandom = static_cast<float>(spec.pitchRandom);
        z.offsetRandom = static_cast<double>(spec.offsetRandom);
        z.delay = static_cast<float>(spec.delay);
        z.delayRandom = static_cast<float>(spec.delayRandom);
        z.width = static_cast<float>(spec.width);
        z.pedal = spec.pedal;
        for (std::size_t i = 0; i < 4; ++i) {
            z.vibrato[i] = static_cast<float>(spec.vibrato[i]);
            z.tremolo[i] = static_cast<float>(spec.tremolo[i]);
        }
        for (std::size_t i = 0; i < 7; ++i) z.fenv[i] = static_cast<float>(spec.fenv[i]);
        z.oneshot = spec.loop == ZoneLoop::OneShot;
        z.sustainLoop = spec.loop == ZoneLoop::Sustain;
        z.offset = static_cast<double>(spec.offset);
        for (std::size_t i = 0; i < 4; ++i) z.xfDyn[i] = static_cast<float>(spec.xfDyn[i]);
        z.xfDynPower = spec.xfDynPower;
        z.hasXfDyn = spec.xfDyn != std::array<int, 4>{0, 0, 127, 127};
        z.dynLo = spec.dynLo;
        z.dynHi = spec.dynHi;
        if (!spec.dynGain.empty()) {
            if (spec.dynGain.front().first > 0.0) z.dynGain.push_back({0.0f, static_cast<float>(spec.dynGain.front().second)});
            for (const auto& [x, gg] : spec.dynGain) z.dynGain.push_back({static_cast<float>(x), static_cast<float>(gg)});
            if (spec.dynGain.back().first < 127.0) z.dynGain.push_back({127.0f, static_cast<float>(spec.dynGain.back().second)});
        }
        z.dynCutoff = static_cast<float>(spec.dynCutoff);
        z.dynLive = z.hasXfDyn || !z.dynGain.empty() || z.dynCutoff != 0.0f;
        z.legatoOffset = spec.legatoOffset ? static_cast<float>(*spec.legatoOffset) : kNoValue;
        z.swLastLo = spec.swLastLo;
        z.swLastHi = spec.swLastHi;
        z.swDown = spec.swDown;

        if (spec.gen == Gen::Silence) {
            z.root = spec.root.value_or(60.0);
            return z;
        }
        if (spec.gen == Gen::Sine || spec.gen == Gen::Noise) {
            z.region = spec.gen == Gen::Sine ? smp::sineRegion() : smp::noiseRegion();
            z.root = spec.root.value_or(60.0);
            z.end = static_cast<double>(z.region->frames);
            z.loops = true;
            z.sustainLoop = false;
            return z;
        }
        const std::string path = resolveAsset(assetDir, spec.file);
        smp::LoopMode mode = spec.loop == ZoneLoop::PingPong ? smp::LoopMode::PingPong
                           : (spec.loop == ZoneLoop::Forward || spec.loop == ZoneLoop::Sustain) ? smp::LoopMode::Forward
                                                                                                 : smp::LoopMode::None;
        auto checkLoop = [&](std::int64_t frames, std::int64_t ls, std::int64_t le) {
            const std::int64_t minLen = mode == smp::LoopMode::PingPong ? 2 : 1;
            if (ls < 0 || le > frames || le - ls < minLen) {
                fail(spec.where, "loop [" + std::to_string(ls) + ", " + std::to_string(le) + ") must lie inside the sample (" +
                     std::to_string(frames) + " frames)");
            }
        };
        if (lowerExt(fs::path(path)) == ".sf2") {
            const auto file = sf2::load(path);
            const int index = file->resolveSample(spec.sample);
            const sf2::Sample& s = file->samples[static_cast<std::size_t>(index)];
            const std::int64_t frames = s.frames();
            if (frames < 1) fail(spec.where, "sample '" + s.name + "' is empty");
            std::int64_t defStart = static_cast<std::int64_t>(s.loopStart) - s.start, defEnd = static_cast<std::int64_t>(s.loopEnd) - s.start;
            if (!(defStart >= 0 && defEnd <= frames && defEnd - defStart >= 2)) { defStart = 0; defEnd = frames; }
            if (spec.loop == ZoneLoop::Auto) mode = smp::LoopMode::Forward;
            std::int64_t ls = spec.loopStart.value_or(defStart), le = spec.loopEnd.value_or(defEnd);
            if (mode != smp::LoopMode::None) checkLoop(frames, ls, le);
            z.region = file->region(index, mode, ls, le, reverse_);
            z.root = spec.root.value_or(s.pitch <= 127 ? s.pitch : 60);
            z.tune += s.correction;
        } else {
            if (const auto it = errors.find(smp::fileKey(path, spec.channels)); it != errors.end()) {
                std::error_code ec;
                if (!fs::is_regular_file(fs::path(path), ec)) fail(spec.where, "file '" + spec.file + "' not found (resolved to '" + path + "')");
                fail(spec.where, "cannot load its WAV: " + it->second);
            }
            const auto file = smp::loadSampleFile(path, reverse_, spec.channels);  // cached by the preload
            const std::int64_t frames = file->frames;
            std::int64_t ls = 0, le = frames;
            if (spec.loop == ZoneLoop::Auto) {
                if (file->loop) {
                    mode = file->loop->pingpong ? smp::LoopMode::PingPong : smp::LoopMode::Forward;
                    ls = file->loop->start;
                    le = file->loop->end;
                }
            } else if (mode != smp::LoopMode::None) {
                if (!spec.loopStart && !spec.loopEnd && file->loop) {  // the file's own loop points
                    ls = file->loop->start;
                    le = file->loop->end;
                } else {
                    ls = spec.loopStart.value_or(0);
                    le = spec.loopEnd.value_or(frames);
                    if (reverse_) {
                        const std::int64_t s0 = frames - le, e0 = frames - ls;
                        ls = s0;
                        le = e0;
                    }
                }
                checkLoop(frames, ls, le);
            }
            const std::int64_t end = spec.end ? std::min<std::int64_t>(*spec.end, frames) : frames;
            if (mode != smp::LoopMode::None && le > end) {
                if (spec.loop == ZoneLoop::Auto) mode = smp::LoopMode::None;  // the file's loop lies beyond the played end
                else fail(spec.where, "loop end " + std::to_string(le) + " lies beyond the played end " + std::to_string(end));
            }
            z.region = fileRegion(file, mode, ls, le);
            if (spec.rootFromFile) {
                z.root = file->unityNote.value_or(60.0);
            } else {
                z.root = spec.root.value_or(60.0);
            }
        }
        const auto frames = static_cast<double>(z.region->frames);
        z.end = spec.end ? std::min(frames, static_cast<double>(*spec.end)) : frames;
        z.loops = z.region->loop;
        z.sustainLoop = z.sustainLoop && z.loops;
        if (z.offset >= z.end) fail(spec.where, "offset " + std::to_string(spec.offset) + " lies at or beyond the end of the sample");
        return z;
    }

    // ------------------------------------------------------------------------------ notes

    float random01(std::uint64_t a, std::uint64_t b, std::uint64_t c) const noexcept {
        const std::uint64_t x = mix64(seed_ ^ mix64(a ^ mix64(b ^ mix64(c))));
        return static_cast<float>(static_cast<double>(x >> 40) * (1.0 / 16777216.0));  // [0, 1)
    }

    // SFZ round robin: the zone's counter advances whenever its key / velocity / random conditions match.
    bool nextInSequence(int zi, const Zone& z) noexcept {
        if (z.seqLength <= 1) return true;
        const std::uint32_t n = seqCount_[static_cast<std::size_t>(zi)]++;
        return static_cast<int>(n % static_cast<std::uint32_t>(z.seqLength)) == z.seqPosition - 1;
    }

    // ------------------------------------------------------------------------------ keyswitches

    void keyswitchOn(int noteId, int key) noexcept {
        if (swLastKey_[static_cast<std::size_t>(key)]) swLast_ = key;
        swHeld_[static_cast<std::size_t>(key)] = true;
        if (swNoteCount_ == kMaxSwitchNotes) {  // forget the oldest held one
            for (int j = 0; j + 1 < swNoteCount_; ++j) swNotes_[static_cast<std::size_t>(j)] = swNotes_[static_cast<std::size_t>(j + 1)];
            --swNoteCount_;
        }
        swNotes_[static_cast<std::size_t>(swNoteCount_++)] = {noteId, key};
    }

    // The zone's articulation is selected: its sw_last range holds the last keyswitch, its sw_down key is held.
    bool switchOk(const Zone& z) const noexcept {
        if (z.swLastLo >= 0 && (swLast_ < z.swLastLo || swLast_ > z.swLastHi)) return false;
        if (z.swDown >= 0 && !swHeld_[static_cast<std::size_t>(z.swDown)]) return false;
        return true;
    }

    // ------------------------------------------------------------------------------ dynamics layers

    // layers='dynamics': the velocity layers among playing_ form a stack by the centres of their velocity ranges;
    // the layers around x (the dynamics at the note-on) and xfspread on each side of them start, each with its
    // neighbours' centres (for the equal-power crossfade); the others are dropped.
    void assignLayers(float x) noexcept {
        std::array<float, 128> c{};
        int n = 0;
        for (const int zi : playing_) {
            const Zone& z = zones_[static_cast<std::size_t>(zi)];
            const float mid = 0.5f * static_cast<float>(z.vello + z.velhi);
            int i = 0;
            while (i < n && c[static_cast<std::size_t>(i)] < mid) ++i;
            if (i < n && c[static_cast<std::size_t>(i)] == mid) continue;
            if (n == 128) continue;
            for (int j = n; j > i; --j) c[static_cast<std::size_t>(j)] = c[static_cast<std::size_t>(j - 1)];
            c[static_cast<std::size_t>(i)] = mid;
            ++n;
        }
        if (n <= 1) return;   // one layer: nothing to crossfade
        int a = 0;   // the pair of layers x lies between (the first / last pair beyond the outer centres)
        while (a + 2 < n && c[static_cast<std::size_t>(a + 1)] <= x) ++a;
        const int b = a + 1;
        const int first = std::max(0, a - xfSpread_), last = std::min(n - 1, b + xfSpread_);
        std::size_t out = 0;
        for (std::size_t i = 0; i < playing_.size(); ++i) {
            const Zone& z = zones_[static_cast<std::size_t>(playing_[i])];
            const float mid = 0.5f * static_cast<float>(z.vello + z.velhi);
            int k = 0;
            while (k < n && c[static_cast<std::size_t>(k)] != mid) ++k;
            if (k < first || k > last) continue;
            playing_[out] = playing_[i];
            playLayer_[out] = {k > first ? c[static_cast<std::size_t>(k - 1)] : -1.0f, mid, k < last ? c[static_cast<std::size_t>(k + 1)] : -1.0f};
            ++out;
        }
        playing_.resize(out);
        playLayer_.resize(out);
    }

    // ------------------------------------------------------------------------------ legato

    struct Handoff {
        int oldKey{-1};
        float oldLevel2{0.0f};          // summed squared level of the line before the transition
        float xfBlocks{1.0f};           // crossfade length (control blocks)
        float glideBlocks{0.0f};        // portamento length (control blocks; 0 = none)
        int glideShape{1};
        bool scripted{true};            // no library legato zones: enter past the attack, level-matched
        float offsetMs{0.0f};           // 'legatooffset' (0 = auto)
        bool haveVib{false};            // zone vibrato state of the line (continued by the new note)
        float vibPhase{0.0f}, vibFade{1.0f};
        int vibWait{0};
    };

    // A voice of the sounding line (mono='legato'): a held note, not a release sample, not on its way out.
    static bool lineVoice(const Voice& v) noexcept {
        return v.active && v.keyDown && !v.oneshot && v.fadeStep <= 0.0f && v.lgDir >= 0 && !v.finishing;
    }

    bool hasLineVoices() const noexcept {
        return std::any_of(voices_.begin(), voices_.end(), [](const Voice& v) { return lineVoice(v); });
    }

    // Level of a voice as heard lately (its gains times the sample's level over the last 150 ms it played: long
    // enough to average a vibrato's amplitude wobble).
    float voiceLevel(const Voice& v) const noexcept {
        if (!v.zone || !v.zone->levels) return 0.0f;
        const smp::Region& r = *v.zone->region;
        // only what the voice has played: a note entered past its attack a moment ago has not played the attack
        const double back = std::min(0.15 * sr_ * v.inc, v.played);
        const double p = smp::loopedFrame(r, v.reader.pos), q = smp::loopedFrame(r, std::max(0.0, v.reader.pos - back));
        const float at = v.zone->levels->mean(std::min(p, q), std::max(p, q));
        // a note still fading in (a transition faster than the crossfade) counts at its full level: the equal-power
        // crossfade keeps the line's level, so the line sounds at that level, not at the fading voice's share of it
        return v.amp * v.env.level * v.dynG * dsp::dbToGain(v.matchDb) * at;
    }

    // The line hands over to a new note: its voices fade out (equal power, from their current gain) and bend to the
    // new pitch; the held notes behind them fire no release zones.
    void beginHandoff(Handoff& ho, int newKey, int noteId) noexcept {
        const double blocksPerMs = sr_ / smp::kControl / 1000.0;
        const float glideMs = params_.get(kGlide);
        const float xfMs = std::max(params_.get(kLegatoTime), glideMs);
        ho.xfBlocks = static_cast<float>(std::max(1.0, xfMs * blocksPerMs));
        ho.glideBlocks = glideMs > 0.0f ? static_cast<float>(std::max(1.0, glideMs * blocksPerMs)) : 0.0f;
        ho.glideShape = params_.choice("glideshape");
        ho.offsetMs = params_.get(kLegatoOffset);
        ho.scripted = std::none_of(playing_.begin(), playing_.end(),
                                   [this](int zi) { return zones_[static_cast<std::size_t>(zi)].trigger == Trigger::Legato; });
        if (!ho.scripted) {  // library transitions attack on their own: the old line fades while they come in
            float attack = 0.0f;
            for (const int zi : playing_) {
                const Zone& z = zones_[static_cast<std::size_t>(zi)];
                attack = std::max(attack, (std::isnan(z.attack) ? params_.get(kAttack) : z.attack) + z.envDelay + z.delay);
            }
            ho.xfBlocks = std::max(ho.xfBlocks, static_cast<float>(attack * sr_ / smp::kControl));
        }
        std::uint64_t newest = 0;
        for (auto& v : voices_) {
            // voices of an earlier transition still fading out fade out with the line, from where they are
            if (v.active && v.lgDir < 0 && !v.finishing && v.fadeStep <= 0.0f) {
                v.lgFrom = legatoGain(v.lgDir, v.lgPos, v.lgFrom);
                v.lgPos = 0.0f;
                v.lgStep = 1.0f / ho.xfBlocks;
                continue;
            }
            if (!lineVoice(v)) continue;
            const float lvl = voiceLevel(v);
            ho.oldLevel2 += lvl * lvl;
            if (v.age >= newest) {
                newest = v.age;
                ho.oldKey = v.key;
                if (v.vibDepth != 0.0f) {
                    ho.haveVib = true;
                    ho.vibPhase = v.vibPhase;
                    ho.vibFade = v.vibFade;
                    ho.vibWait = v.vibWait;
                }
            }
            v.lgFrom = legatoGain(v.lgDir, v.lgPos, v.lgFrom);   // from its current gain (a note still fading in: sin)
            v.lgDir = -1;
            v.lgPos = 0.0f;
            v.lgStep = 1.0f / ho.xfBlocks;
            v.keyDown = false;
            v.sustained = false;
            v.noteId = -1;
            if (ho.glideBlocks > 0.0f && v.zone) {
                v.glideFrom = v.glideCents;
                v.glideTo = static_cast<float>((newKey - v.key) * v.zone->keytrack);
                v.glidePos = 0.0f;
                v.glideStep = 1.0f / ho.glideBlocks;
                v.glideShape = ho.glideShape;
            }
        }
        for (int i = 0; i < heldCount_; ++i) {
            Held& h = held_[static_cast<std::size_t>(i)];
            if (h.down && h.noteId != noteId) h.handed = true;
        }
    }

    // After the new note's voices started: scripted transitions enter at the level of the old line (level match,
    // relaxing to the note's own level).
    void finishHandoff(const Handoff& ho, int noteId) noexcept {
        const float amount = params_.get(kLegatoMatch);
        if (!ho.scripted || amount <= 0.0f || ho.oldLevel2 <= 0.0f) return;
        float newLevel2 = 0.0f;   // the new note's own level over its first 150 ms
        for (const auto& v : voices_) {
            if (!v.active || v.noteId != noteId || !v.zone || !v.zone->levels) continue;
            const smp::Region& r = *v.zone->region;
            const double p = v.reader.pos;
            const float at = v.zone->levels->mean(smp::loopedFrame(r, p), smp::loopedFrame(r, std::min(p + 0.15 * sr_ * v.baseInc,
                                                                                                        static_cast<double>(r.frames) - 1.0)));
            const float lvl = v.amp * v.env.level * v.dynG * at;
            newLevel2 += lvl * lvl;
        }
        if (newLevel2 <= 1e-20f) return;
        const float db = std::clamp(10.0f * std::log10(ho.oldLevel2 / newLevel2), -kMatchLimitDb, kMatchLimitDb) * amount;
        const double seconds = std::max(kMatchMinSeconds, 3.0 * ho.xfBlocks * smp::kControl / sr_);
        const int blocks = std::max(1, static_cast<int>(std::lround(seconds * sr_ / smp::kControl)));
        for (auto& v : voices_) {
            if (!v.active || v.noteId != noteId) continue;
            v.matchDb = db;
            v.matchLeft = blocks;
            v.matchStep = -db / static_cast<float>(blocks);
        }
    }

    // Starts the zones in playing_ for a note (note-on, or a release trigger `heldSeconds` after its note-on):
    // first every group / choke / note polyphony effect of the new zones on the sounding voices (never on voices
    // of this same note), then the voices.
    void startZones(int noteId, int key, int vel, std::int64_t now, double heldSeconds, bool released,
                    const Handoff* ho = nullptr) {
        const float restrike = params_.get(kRestrike);
        if (restrike > 0.0f && !released && !playing_.empty()) {   // the stick touches the ringing head / cymbal
            const float g = dsp::dbToGain(-restrike);
            for (auto& v : voices_) {
                if (v.active && !v.finishing && v.key == key && v.noteId != noteId && v.fadeStep <= 0.0f && v.lgDir >= 0)
                    v.rsTarget *= g;
            }
        }
        for (const int zi : playing_) {
            const Zone& z = zones_[static_cast<std::size_t>(zi)];
            for (auto& v : voices_) {
                if (!v.active || v.noteId == noteId || v.fadeStep > 0.0f || v.lgDir < 0) continue;
                if (z.choke != 0 && v.choke == z.choke) choke(v);
                else if (v.zone && v.zone->hasOffBy && v.zone->offBy == z.group) off(v);
            }
            if (z.notePolyphony > 0 && !released) limitNote(z, key, noteId);
        }
        for (std::size_t i = 0; i < playing_.size(); ++i) {
            const Zone& z = zones_[static_cast<std::size_t>(playing_[i])];
            if (!z.region) continue;
            // release samples fade with the time the key was held: rtDecay dB per second
            const float gain = released ? dsp::dbToGain(static_cast<float>(-z.rtDecay * heldSeconds)) : 1.0f;
            if (gain < 1e-5f) continue;  // decayed below -100 dB
            if (z.groupPolyphony > 0) limitGroup(z, noteId);
            const std::array<float, 3>* layer = (!released && i < playLayer_.size() && playLayer_[i][1] >= 0.0f) ? &playLayer_[i] : nullptr;
            startVoice(allocate(), z, key, vel, noteId, now, gain, released, layer, ho);
        }
    }

    // SFZ polyphony: at most n voices of the zone's group (group 0: of this zone) sound at once; the oldest voice of
    // another note is faded out (5 ms) to make room for the new one.
    void limitGroup(const Zone& z, int noteId) noexcept {
        while (true) {
            int count = 0;
            Voice* oldest = nullptr;
            for (auto& v : voices_) {
                if (!v.active || v.fadeStep > 0.0f || v.lgDir < 0 || !v.zone) continue;
                if (z.group != 0 ? v.zone->group != z.group : v.zone != &z) continue;
                ++count;
                if (v.noteId != noteId && (!oldest || v.age < oldest->age)) oldest = &v;
            }
            if (count < z.groupPolyphony || !oldest) return;
            fadeInPlace(*oldest, offStep_);
        }
    }

    // SFZ note_polyphony: at most n sounding (not released) voices of this key in the zone's group.
    void limitNote(const Zone& z, int key, int noteId) noexcept {
        while (true) {
            int count = 0;
            Voice* oldest = nullptr;
            for (auto& v : voices_) {
                if (!v.active || v.fadeStep > 0.0f || v.lgDir < 0 || v.noteId == noteId || !v.zone || v.key != key || v.zone->group != z.group) continue;
                if (v.env.stage == Eg::Release || v.env.stage == Eg::Done) continue;
                ++count;
                if (!oldest || v.age < oldest->age) oldest = &v;
            }
            if (count < z.notePolyphony || !oldest) return;
            off(*oldest);
        }
    }

    // Release-triggered zones of a note: at its note-off (release_key, and release zones the pedal does not hold)
    // or at pedal-up (release zones held by the pedal). Attenuated by rtDecay dB per second since the note-on.
    void fireRelease(const Held& note, bool pedalUp) {
        if (note.key < 0 || note.key > 127) return;
        const std::int64_t now = startSample_ + clock_;
        const float rnd = random01(static_cast<std::uint64_t>(now), static_cast<std::uint64_t>(note.key), 0x72656C65617365ull);
        const double heldSeconds = static_cast<double>(now - note.onSample) / sr_;
        playing_.clear();
        for (const int zi : offZones_[static_cast<std::size_t>(note.key)]) {
            const Zone& z = zones_[static_cast<std::size_t>(zi)];
            const bool held = z.trigger == Trigger::Release && z.pedal;
            if (pedalUp ? !held : (held && pedalDown_)) continue;
            if (note.vel < z.vello || note.vel > z.velhi || rnd < z.lorand || rnd >= z.hirand) continue;
            if (!switchOk(z)) continue;
            if (!nextInSequence(zi, z)) continue;
            playing_.push_back(zi);
        }
        if (!playing_.empty()) startZones(note.noteId, note.key, note.vel, now, heldSeconds, true);
    }

    void removeHeld(int i) noexcept {
        for (int k = i; k + 1 < heldCount_; ++k) held_[static_cast<std::size_t>(k)] = held_[static_cast<std::size_t>(k + 1)];
        --heldCount_;
    }

    void applyPedal() {
        const float p = params_.get(kPedal);
        halfDb_ = p >= 0.5f && p < 0.995f ? static_cast<float>(kHalfDampDb * (1.0 - p) / 0.5 * smp::kControl / sr_) : 0.0f;
        const bool down = p >= 0.5f;
        if (down == pedalDown_) return;
        pedalDown_ = down;
        if (down) return;
        for (auto& v : voices_) {
            if (v.active && v.sustained) {
                v.sustained = false;
                release(v);
            }
        }
        for (int i = 0; i < heldCount_;) {
            if (!held_[static_cast<std::size_t>(i)].pending) { ++i; continue; }
            const Held note = held_[static_cast<std::size_t>(i)];
            removeHeld(i);
            // a key has one damper: a key struck several times under the pedal fires its release zones once (its latest
            // note), and not at all while it is struck again and still held (they fire at that note's note-off)
            bool later = false;
            for (int j = i; j < heldCount_ && !later; ++j) {
                const Held& h = held_[static_cast<std::size_t>(j)];
                later = (h.pending || h.down) && h.key == note.key;
            }
            if (!later) fireRelease(note, true);
        }
    }

    Voice& allocate() {
        for (int i = 0; i < poly_; ++i) {
            if (!voices_[static_cast<std::size_t>(i)].active) return voices_[static_cast<std::size_t>(i)];
        }
        auto oldest = [this](bool releasedOnly) {
            Voice* found = nullptr;
            for (int i = 0; i < poly_; ++i) {
                Voice& v = voices_[static_cast<std::size_t>(i)];
                if (releasedOnly && (v.keyDown || v.sustained)) continue;
                if (!found || v.age < found->age) found = &v;
            }
            return found;
        };
        Voice* victim = oldest(true);
        if (!victim) victim = oldest(false);
        Voice* spare = nullptr;
        for (std::size_t i = static_cast<std::size_t>(poly_); i < voices_.size(); ++i) {
            Voice& s = voices_[i];
            if (!s.active) { spare = &s; break; }
            if (!spare || s.fade < spare->fade) spare = &s;
        }
        *spare = *victim;
        fadeInPlace(*spare, stealStep_);
        victim->active = false;
        return *victim;
    }

    void fadeInPlace(Voice& v, float step) noexcept {
        v.keyDown = false;
        v.sustained = false;
        v.noteId = -1;
        v.fadeStep = std::max(v.fadeStep, step);
    }

    void release(Voice& v) noexcept {
        v.env.release();
        v.fenv.release();
        if (v.untilRelease) v.reader.exitAtWrap = true;
    }

    void choke(Voice& v) noexcept {
        v.keyDown = false;
        v.sustained = false;
        v.env.stage = Eg::Release;
        v.env.releaseCoef = std::min(v.env.releaseCoef, chokeCoef_);
        v.fenv.release();
    }

    // A voice turned off by a group (SFZ off_by) or by note polyphony, in the way its zone asks for.
    void off(Voice& v) noexcept {
        const Zone* z = v.zone;
        if (!z || z->offMode == OffMode::Fast) {
            fadeInPlace(v, offStep_);
            return;
        }
        v.keyDown = false;
        v.sustained = false;
        v.noteId = -1;
        if (z->offMode == OffMode::Time) v.env.releaseCoef = releaseCoef(std::max<double>(kMinRelease, z->offTime));
        release(v);
    }

    float releaseCoef(double seconds) const noexcept {
        return static_cast<float>(std::exp(-6.9 * smp::kControl / (std::max(kMinRelease, seconds) * sr_)));
    }

    float velocityGain(const Zone& z, int vel) const noexcept {
        const float x = static_cast<float>(vel) / 127.0f;
        const float velsens = params_.get(kVelsens);
        if (!z.hasVeltrack && z.velcurve.empty()) return std::pow(x, 2.0f * velsens);  // the instrument's own response
        const float c = z.velcurve.empty() ? x * x : curveAt(z.velcurve, static_cast<float>(vel));
        const float t = z.hasVeltrack ? z.veltrack * velsens : velsens;
        return t >= 0.0f ? 1.0f - t * (1.0f - c) : 1.0f + t * c;
    }

    void startVoice(Voice& v, const Zone& z, int key, int vel, int noteId, std::int64_t now, float gain, bool released,
                    const std::array<float, 3>* layer = nullptr, const Handoff* ho = nullptr) {
        const smp::Region& r = *z.region;
        auto zr = [&](std::uint64_t salt) {
            return random01(static_cast<std::uint64_t>(now), static_cast<std::uint64_t>(key) ^ z.salt, salt);
        };
        // scripted legato: the sample enters past its attack (the zone's legatoOffset, the param, else its level track)
        const bool scripted = ho && ho->scripted;
        double offset = z.offset;
        if (z.offsetRandom > 0.0) offset += std::floor(static_cast<double>(zr(1)) * (z.offsetRandom + 1.0));
        offset += params_.get(kStart) * 0.001 * r.rate;
        if (scripted) {
            if (!std::isnan(z.legatoOffset)) offset += z.legatoOffset * 0.001 * r.rate;
            else if (ho->offsetMs > 0.0f) offset += ho->offsetMs * 0.001 * r.rate;
            else if (z.levels) offset = std::max(offset, z.levels->attackEnd);
        }
        offset = std::min(offset, z.end - 1.0);
        const bool loop = z.loops && !oneshot_ && !released;
        v.reader.start(r, offset, z.end, loop);
        v.untilRelease = z.sustainLoop && loop;
        v.stereo = r.channels == 2;
        double cents = (key - z.root) * z.keytrack + z.tune + params_.get(kTune);
        if (z.pitchRandom > 0.0f) cents += (2.0 * zr(2) - 1.0) * z.pitchRandom;
        v.baseInc = r.rate / sr_ * std::exp2(cents / 1200.0);
        v.inc = v.baseInc;
        v.played = 0.0;
        float amp = z.gain * gain * velocityGain(z, vel);
        if (!layer) amp *= crossfade(vel, z.xf[0], z.xf[1], z.xf[2], z.xf[3], z.xfVelPower);  // a dynamics stack crossfades itself
        amp *= crossfade(key, z.xf[4], z.xf[5], z.xf[6], z.xf[7], z.xfKeyPower);
        if (z.ampRandom > 0.0f) amp *= dsp::dbToGain(zr(3) * z.ampRandom);
        v.amp = amp;
        v.pan = z.pan;
        v.width = z.width;
        v.choke = z.choke;
        v.zone = &z;
        v.dynLive = z.dynLive && !released;
        v.layered = layer != nullptr;
        if (layer) {
            v.layerLo = (*layer)[0];
            v.layerMid = (*layer)[1];
            v.layerHi = (*layer)[2];
        }
        v.key = key;
        v.vel = vel;
        v.bendScale = params_.get(kBendFollow);
        v.hz0 = 440.0 * std::exp2((key - 69) / 12.0 + params_.get(kTune) / 1200.0);
        v.hOn = false;
        // envelope: the zone's times (+ velocity tracking), else the instrument's
        constexpr double n = smp::kControl;
        const double x = vel / 127.0;
        const double a = std::max(0.0, (std::isnan(z.attack) ? params_.get(kAttack) : z.attack) + z.velAttack * x);
        const double d = std::max(0.0, (std::isnan(z.decay) ? params_.get(kDecay) : z.decay) + z.velDecay * x);
        const double sus = std::clamp((std::isnan(z.sustain) ? params_.get(kSustain) : z.sustain) + z.velSustain * x, 0.0, 1.0);
        const double rel = std::isnan(z.release) ? params_.get(kRelease) : z.release + z.velRelease * x;
        const double hold = std::max(0.0, static_cast<double>(z.hold) + z.velHold * x);
        v.env.start(sr_, z.envDelay, a, hold, d, sus, rel);
        double delay = z.delay;
        if (z.delayRandom > 0.0f) delay += zr(4) * z.delayRandom;
        v.startDelay = static_cast<int>(std::lround(delay * sr_));
        if (scripted) {  // a legato note does not attack: its envelope starts settled, no start delay
            v.env.level = 1.0f;
            v.env.stage = Eg::Decay;
            v.env.wait = 0;
            v.startDelay = 0;
        }
        // the zone's filter (static per note, or moved by the filter envelope) and EQ
        v.zf = z.filter;
        v.fenvDepth = z.filter != Filter::None ? z.fenv[0] : 0.0f;
        if (z.filter != Filter::None) {
            v.zfHz = static_cast<float>(z.cutoff * std::exp2((z.filKeytrack * (key - z.filKeycenter) + z.filVeltrack * x) / 1200.0));
            v.zfQ = z.filterQ;
            for (int c = 0; c < 2; ++c) {
                v.zb[c].reset();
                v.zo[c].reset();
            }
            if (v.fenvDepth != 0.0f) {
                v.fenv.start(sr_, z.fenv[1], z.fenv[2], z.fenv[3], z.fenv[4], z.fenv[5], z.fenv[6]);
                if (scripted) {
                    v.fenv.level = 1.0f;
                    v.fenv.stage = Eg::Decay;
                    v.fenv.wait = 0;
                }
            }
            setZoneFilter(v, zoneCents(v, z));
        }
        v.zfMoves = z.filter != Filter::None && (v.fenvDepth != 0.0f || z.dynCutoff != 0.0f);
        v.eqCount = z.eqCount;
        for (int b = 0; b < z.eqCount; ++b) {
            const auto& band = z.eq[static_cast<std::size_t>(b)];
            // RBJ peaking EQ: Q from the bandwidth in octaves
            const double w0 = dsp::kTwoPi * std::min<double>(band[0], 0.45 * sr_) / sr_;
            const double q = 1.0 / (2.0 * std::sinh(std::log(2.0) / 2.0 * band[1] * w0 / std::sin(w0)));
            for (int c = 0; c < 2; ++c) {
                v.eq[b][c].reset();
                v.eq[b][c].set(dsp::Biquad::Type::Peak, sr_, band[0], q, band[2]);
            }
        }
        // LFOs (control rate): phase 0 after their delay, faded in over their fade time
        const double blocksPerSec = sr_ / n;
        auto lfo = [&](const std::array<float, 4>& p, float& depth, float& inc, float& phase, float& fade, float& step, int& wait) {
            depth = p[0];
            inc = static_cast<float>(p[1] / blocksPerSec);
            phase = 0.0f;
            wait = static_cast<int>(std::lround(p[2] * blocksPerSec));
            step = p[3] > 0.0f ? static_cast<float>(1.0 / (p[3] * blocksPerSec)) : 1.0f;
            fade = p[3] > 0.0f ? 0.0f : 1.0f;
        };
        lfo(z.vibrato, v.vibDepth, v.vibInc, v.vibPhase, v.vibFade, v.vibFadeStep, v.vibWait);
        lfo(z.tremolo, v.tremDepth, v.tremInc, v.tremPhase, v.tremFade, v.tremFadeStep, v.tremWait);
        if (ho && ho->haveVib && v.vibDepth != 0.0f) {  // legato: the player's vibrato runs on
            v.vibPhase = ho->vibPhase;
            v.vibFade = ho->vibFade;
            v.vibWait = ho->vibWait;
        }
        v.active = true;
        v.keyDown = !released;
        v.sustained = false;
        v.pedalSens = z.pedal;
        v.oneshot = released || z.oneshot || oneshot_;
        v.finishing = false;
        v.noteId = noteId;
        v.age = ++age_;
        v.ctl = 0;
        v.g.fill(0.0f);
        v.dg.fill(0.0f);
        v.fade = 1.0f;
        v.fadeStep = 0.0f;
        v.damp = 1.0f;
        v.rs = 1.0f;
        v.rsTarget = 1.0f;
        v.lp[0].reset();
        v.lp[1].reset();
        v.tg.fill(0.0f);
        v.dynG = dynamicsGain(v);
        v.silent = false;
        // legato handover: fade in (scripted and library transitions alike get the old line's crossfade), bend in
        v.lgDir = 0;
        v.lgPos = 1.0f;
        v.lgStep = 0.0f;
        v.lgFrom = 1.0f;
        v.matchDb = 0.0f;
        v.matchStep = 0.0f;
        v.matchLeft = 0;
        v.glideCents = v.glideFrom = v.glideTo = 0.0f;
        v.glidePos = 1.0f;
        v.glideStep = 0.0f;
        if (ho) {
            if (ho->scripted) {
                v.lgDir = 1;
                v.lgPos = 0.0f;
                v.lgStep = 1.0f / ho->xfBlocks;
            }
            if (ho->glideBlocks > 0.0f && ho->oldKey >= 0) {
                v.glideCents = v.glideFrom = static_cast<float>((ho->oldKey - key) * z.keytrack);
                v.glidePos = 0.0f;
                v.glideStep = 1.0f / ho->glideBlocks;
                v.glideShape = ho->glideShape;
            }
        }
    }

    // Live 'dynamics' gain of a voice: the zone's crossfade and gain curve, its place in the layer stack.
    float dynamicsGain(const Voice& v) const noexcept {
        if (!v.dynLive && !v.layered) return 1.0f;
        const float x = dyn_ * 127.0f;
        float g = 1.0f;
        if (v.dynLive) {
            const Zone& z = *v.zone;
            if (z.hasXfDyn) g *= crossfadeAt(x, z.xfDyn, z.xfDynPower);
            if (!z.dynGain.empty()) g *= curveAt(z.dynGain, x);
        }
        if (v.layered) g *= layerGain(x, v.layerLo, v.layerMid, v.layerHi);
        return g;
    }

    // Zone filter offset in cents: its filter envelope and the dynamics cutoff move.
    float zoneCents(const Voice& v, const Zone& z) const noexcept {
        return v.fenvDepth * v.fenv.level + (v.dynLive ? z.dynCutoff * dyn_ : 0.0f);
    }

    // ------------------------------------------------------------------------------ rendering

    // Coefficients of the zone filter with its cutoff moved by `cents` (filter envelope, dynamics).
    void setZoneFilter(Voice& v, float cents) const noexcept {
        const double hz = std::clamp(static_cast<double>(v.zfHz) * std::exp2(cents / 1200.0), 10.0, 0.45 * sr_);
        for (int c = 0; c < 2; ++c) {
            switch (v.zf) {
                case Filter::Lp2: v.zb[c].set(dsp::Biquad::Type::LowPass, sr_, hz, v.zfQ); break;
                case Filter::Hp2: v.zb[c].set(dsp::Biquad::Type::HighPass, sr_, hz, v.zfQ); break;
                case Filter::Bp2: v.zb[c].set(dsp::Biquad::Type::BandPass, sr_, hz, v.zfQ); break;
                case Filter::Lp1:
                case Filter::Hp1: v.zo[c].setLowPass(sr_, hz); break;
                case Filter::None: break;
            }
        }
    }

    static float lfoStep(float& phase, float inc, float& fade, float step, int& wait) noexcept {
        if (wait > 0) {
            --wait;
            return 0.0f;
        }
        const float value = std::sin(static_cast<float>(dsp::kTwoPi) * phase) * fade;
        phase += inc;
        phase -= std::floor(phase);
        fade = std::min(1.0f, fade + step);
        return value;
    }

    // `offset`: the block's first sample within this process() call (the instrument vibrato's phase there).
    bool beginBlock(Voice& v, int offset) noexcept {
        if (v.finishing) {
            v.active = false;
            return false;
        }
        constexpr float n = static_cast<float>(smp::kControl);
        v.env.advance();
        if (v.fenvDepth != 0.0f) v.fenv.advance();
        if (v.zfMoves) setZoneFilter(v, zoneCents(v, *v.zone));
        if (v.glidePos < 1.0f) {
            v.glidePos = std::min(1.0f, v.glidePos + v.glideStep);
            v.glideCents = v.glideFrom + (v.glideTo - v.glideFrom) * glideCurve(v.glideShape, v.glidePos);
        }
        double cents = (v.bendScale == 1.0f ? bend_ : bend_ * v.bendScale) * 100.0 + v.glideCents;
        if (v.vibDepth != 0.0f) cents += v.vibDepth * lfoStep(v.vibPhase, v.vibInc, v.vibFade, v.vibFadeStep, v.vibWait);
        if (vib_ != 0.0f) {
            const double ph = vibPhase_ + static_cast<double>(vibRate_) / sr_ * offset;
            cents += vib_ * std::sin(dsp::kTwoPi * ph);
        }
        if (harmActive_) harmonicBlock(v, cents);
        else if (v.hOn) v.hOn = false;
        v.inc = cents == 0.0 ? v.baseInc : v.baseInc * std::exp2(cents / 1200.0);
        v.played += n * v.inc;
        v.coefs.set(sr_, cutoff_, 0.70710678 * std::exp2(4.0 * res_));
        v.dynG = dynamicsGain(v);
        float a = v.amp * v.env.level * v.dynG;
        if (v.tremDepth != 0.0f) a *= dsp::dbToGain(v.tremDepth * lfoStep(v.tremPhase, v.tremInc, v.tremFade, v.tremFadeStep, v.tremWait));
        if (v.fadeStep > 0.0f) {
            v.fade = std::max(0.0f, v.fade - v.fadeStep * n);
            a *= v.fade;
        }
        if (v.lgDir != 0) {
            v.lgPos = std::min(1.0f, v.lgPos + v.lgStep);
            a *= legatoGain(v.lgDir, v.lgPos, v.lgFrom);
            if (v.lgDir > 0 && v.lgPos >= 1.0f) v.lgDir = 0;
        }
        if (v.matchLeft > 0) {
            v.matchDb = --v.matchLeft > 0 ? v.matchDb + v.matchStep : 0.0f;
            a *= dsp::dbToGain(v.matchDb);
        }
        if (v.sustained && halfDb_ > 0.0f)   // half pedal: the dampers touch the strings (the bass less)
            v.damp *= dsp::dbToGain(-halfDb_ * (0.4f + 0.6f * std::clamp((v.key - 21) / 87.0f, 0.0f, 1.0f)));
        a *= v.damp;
        if (v.rs != v.rsTarget) {    // re-strike damping glides there in ~12 ms (one-pole per control block)
            v.rs = std::fabs(v.rs - v.rsTarget) < 1e-6f ? v.rsTarget : v.rsTarget + (v.rs - v.rsTarget) * rsCoef_;
        }
        a *= v.rs;
        if (v.env.stage == Eg::Done || (v.fadeStep > 0.0f && v.fade <= 0.0f) || v.reader.done || v.damp < kSilent ||
            v.rs < kSilent ||
            (v.lgDir < 0 && v.lgPos >= 1.0f) || (v.env.stage == Eg::Sustain && v.env.sustain * v.amp < kSilent * 0.1f)) {
            v.finishing = true;
            a = 0.0f;
        }
        std::array<float, 4> t{};
        if (!v.stereo) {
            dsp::panGains(std::clamp(pan_ + v.pan * width_, -1.0f, 1.0f), t[0], t[1]);
            t[0] *= a;
            t[1] *= a;
        } else {
            const float p = std::clamp(pan_ + v.pan, -1.0f, 1.0f);
            const float w = std::clamp(width_ * v.width, 0.0f, 2.0f);
            const float bl = std::min(1.0f, 1.0f - p), br = std::min(1.0f, 1.0f + p);
            const float same = 0.5f * (1.0f + w), cross = 0.5f * (1.0f - w);
            t = {a * bl * same, a * bl * cross, a * br * cross, a * br * same};
        }
        v.g = v.tg;   // the last ramp landed there (up to rounding): exact, so a silent voice is exactly silent
        for (std::size_t k = 0; k < 4; ++k) v.dg[k] = (t[k] - v.g[k]) / n;
        v.tg = t;
        v.ctl = smp::kControl;
        // a silent layer (dynamics crossfaded it out) only keeps its place in the sample; the zone filter / EQ state
        // must run on, and the lowpass must be open (its state restarts when the layer comes back)
        const bool wasSilent = v.silent;
        v.silent = a == 0.0f && !v.finishing && v.g == std::array<float, 4>{} && t == std::array<float, 4>{} &&
                   v.zf == Filter::None && v.eqCount == 0 && v.coefs.open >= 1.0f;
        if (wasSilent && !v.silent) {
            v.lp[0].reset();
            v.lp[1].reset();
        }
        return true;
    }

    // The zone filter and EQ of channel c on a buffer.
    static void zoneTone(Voice& v, int c, float* x, int m) noexcept {
        if (v.zf != Filter::None) {
            switch (v.zf) {
                case Filter::Lp1: for (int i = 0; i < m; ++i) x[i] = v.zo[c].lowPass(x[i]); break;
                case Filter::Hp1: for (int i = 0; i < m; ++i) x[i] = v.zo[c].highPass(x[i]); break;
                default: for (int i = 0; i < m; ++i) x[i] = v.zb[c].process(x[i]); break;
            }
        }
        for (int b = 0; b < v.eqCount; ++b) {
            for (int i = 0; i < m; ++i) x[i] = v.eq[b][c].process(x[i]);
        }
    }

    void renderVoice(Voice& v, float* L, float* R, int frames) noexcept {
        float b0[smp::kControl], b1[smp::kControl];
        int done = 0;
        if (v.startDelay > 0) {  // SFZ delay: the voice starts later
            const int skip = std::min(frames, v.startDelay);
            v.startDelay -= skip;
            done = skip;
        }
        const bool tone = v.zf != Filter::None || v.eqCount > 0;
        while (done < frames) {
            if (v.ctl == 0 && !beginBlock(v, done)) return;
            const int m = std::min(frames - done, v.ctl);
            if (v.silent) {
                v.reader.skip(m, v.inc);
                v.ctl -= m;
                done += m;
                continue;
            }
            v.reader.read(b0, b1, m, v.inc);
            if (tone) {
                zoneTone(v, 0, b0, m);
                if (v.stereo) zoneTone(v, 1, b1, m);
            }
            if (v.hOn) {
                for (int i = 0; i < m; ++i) b0[i] = v.coefs.process(v.lp[0], b0[i]);
                if (v.stereo) {
                    for (int i = 0; i < m; ++i) b1[i] = v.coefs.process(v.lp[1], b1[i]);
                }
                harmonicRun(v, b0, v.stereo ? b1 : nullptr, m);
                std::array<float, 4> g = v.g;
                for (int i = 0; i < m; ++i) {
                    for (std::size_t k = 0; k < 4; ++k) g[k] += v.dg[k];
                    if (!v.stereo) {
                        L[done + i] += b0[i] * g[0];
                        R[done + i] += b0[i] * g[1];
                    } else {
                        L[done + i] += b0[i] * g[0] + b1[i] * g[1];
                        R[done + i] += b0[i] * g[2] + b1[i] * g[3];
                    }
                }
                v.g = g;
            } else if (!v.stereo) {
                float gl = v.g[0], gr = v.g[1];
                for (int i = 0; i < m; ++i) {
                    const float s = v.coefs.process(v.lp[0], b0[i]);
                    gl += v.dg[0];
                    gr += v.dg[1];
                    L[done + i] += s * gl;
                    R[done + i] += s * gr;
                }
                v.g[0] = gl;
                v.g[1] = gr;
            } else {
                std::array<float, 4> g = v.g;
                for (int i = 0; i < m; ++i) {
                    const float l = v.coefs.process(v.lp[0], b0[i]);
                    const float r = v.coefs.process(v.lp[1], b1[i]);
                    for (std::size_t k = 0; k < 4; ++k) g[k] += v.dg[k];
                    L[done + i] += l * g[0] + r * g[1];
                    R[done + i] += l * g[2] + r * g[3];
                }
                v.g = g;
            }
            v.ctl -= m;
            done += m;
        }
        v.lp[0].flush();
        v.lp[1].flush();
    }

    float outputGain() const noexcept {
        const float e = params_.get(kExpression);
        const float range = params_.get(kDynRange);
        const float dyn = range > 0.0f ? dsp::dbToGain(-range * (1.0f - params_.get(kDynamics))) : 1.0f;
        return dsp::dbToGain(params_.get(kLevel)) * e * e * dyn;
    }

    void updateControls(int frames) noexcept {
        const double t = static_cast<double>(frames) / sr_;
        const float fast = static_cast<float>(std::exp(-t / kGainTau)), tone = static_cast<float>(std::exp(-t / kToneTau));
        smp::glide(bend1_, bend_, params_.get(kPitchbend), fast);
        smp::glide(pan1_, pan_, params_.get(kPan), fast);
        smp::glide(width1_, width_, params_.get(kWidth), fast);
        smp::glide(gain1_, gain_, outputGain(), fast);
        smp::glide(cutoff1_, cutoff_, params_.get(kCutoff), tone);
        smp::glide(res1_, res_, params_.get(kResonance), tone);
        smp::glide(dyn1_, dyn_, params_.get(kDynamics), fast);
        smp::glide(vib1_, vib_, params_.get(kVibrato), fast);
        smp::glide(vibRate1_, vibRate_, params_.get(kVibratoRate), fast);
        const float harmTarget = params_.get(kHarmonic);
        if (harmTarget > 0.0f || harm_ != 0.0f || harm1_ != 0.0f) {
            smp::glide(harm1_, harm_, harmTarget, static_cast<float>(std::exp(-t / kHarmTau)));
            harmActive_ = true;
        } else {
            harmActive_ = false;
        }
    }

    // 'harmonic', per control block: the band-pass pair re-tuned to partial n of the note as it sounds now (bends,
    // glides, vibrato), and the level-matching gain for the next block - the isolated partial at the note's level,
    // rising towards the note's held peak level as 'harmonic' goes to 1 (a feedback note sustains).
    void harmonicBlock(Voice& v, double cents) noexcept {
        const double f = v.hz0 * std::exp2(cents / 1200.0) * params_.get(kHarmonicNum);
        if (!(f < 0.45 * sr_) || f < 20.0) {
            v.hOn = false;
            return;
        }
        if (!v.hOn) {   // starts afresh (zero filter state: the band-passes ring up within a few ms)
            v.hOn = true;
            std::memset(v.hs, 0, sizeof(v.hs));
            v.hEnvX = v.hEnvH = v.hPeak = 0.0f;
            v.hGain = 1.0f;
            v.hdGain = 0.0f;
            v.hWarm = 0.0f;
            v.hA = 0.0f;
        }
        v.hWarm = std::min(1.0f, v.hWarm + static_cast<float>(smp::kControl / (kHarmWarm * sr_)));
        const double g = std::tan(dsp::kPi * f / sr_);
        const double k = 1.0 / params_.get(kHarmonicFocus);
        v.hk = static_cast<float>(k);
        v.ha1 = static_cast<float>(1.0 / (1.0 + g * (g + k)));
        v.ha2 = static_cast<float>(g) * v.ha1;
        v.ha3 = static_cast<float>(g) * v.ha2;
        // level match: ref = envX^(1-a) * peak^a (power); the gain ramps there over the block
        constexpr float kMaxGain = 100.0f;   // +40 dB
        const float a = std::clamp(harm_, 0.0f, 1.0f);
        v.hPeak = std::max(v.hPeak * hPeakFall_, v.hEnvX);
        const float ref = a <= 0.0f ? v.hEnvX
                                    : std::exp((1.0f - a) * std::log(v.hEnvX + 1e-20f) + a * std::log(v.hPeak + 1e-20f));
        float target = v.hEnvH > 1e-14f ? std::sqrt(ref / v.hEnvH) : v.hGain;
        if (!(target <= kMaxGain)) target = kMaxGain;
        v.hdGain = (target - v.hGain) / static_cast<float>(smp::kControl);
    }

    // 'harmonic' on m samples of a voice (after its low-pass): x -> (1 - a) x + a g h.
    void harmonicRun(Voice& v, float* x0, float* x1, int m) noexcept {
        const float aEnd = std::clamp(harm_, 0.0f, 1.0f) * v.hWarm;
        float a = v.hA;
        const float da = (aEnd - v.hA) / static_cast<float>(std::max(1, m));
        const float a1 = v.ha1, a2 = v.ha2, a3 = v.ha3, k = v.hk, c = hEnvCoef_;
        float* xs[2] = {x0, x1};
        float h[2][smp::kControl];
        const int chans = x1 ? 2 : 1;
        for (int ch = 0; ch < chans; ++ch) {
            const float* x = xs[ch];
            for (int i = 0; i < m; ++i) {
                float y = x[i];
                for (int st = 0; st < 2; ++st) {
                    float& ic1 = v.hs[ch][st][0];
                    float& ic2 = v.hs[ch][st][1];
                    const float v3 = y - ic2;
                    const float v1 = a1 * ic1 + a2 * v3;
                    const float v2 = ic2 + a2 * ic1 + a3 * v3;
                    ic1 = 2.0f * v1 - ic1;
                    ic2 = 2.0f * v2 - ic2;
                    y = k * v1;   // unity gain at the centre
                }
                h[ch][i] = y;
            }
            for (int st = 0; st < 2; ++st) {
                v.hs[ch][st][0] = dsp::flush(v.hs[ch][st][0]);
                v.hs[ch][st][1] = dsp::flush(v.hs[ch][st][1]);
            }
        }
        float gn = v.hGain;
        for (int i = 0; i < m; ++i) {
            const float px = chans == 2 ? 0.5f * (x0[i] * x0[i] + x1[i] * x1[i]) : x0[i] * x0[i];
            const float ph = chans == 2 ? 0.5f * (h[0][i] * h[0][i] + h[1][i] * h[1][i]) : h[0][i] * h[0][i];
            v.hEnvX += c * (px - v.hEnvX);
            v.hEnvH += c * (ph - v.hEnvH);
            gn += v.hdGain;
            a += da;
            for (int ch = 0; ch < chans; ++ch) xs[ch][i] += a * (gn * h[ch][i] - xs[ch][i]);
        }
        v.hGain = gn;
        v.hA = aEnd;
        v.hEnvX = dsp::flush(v.hEnvX);
        v.hEnvH = dsp::flush(v.hEnvH);
    }

    Params params_;
    std::string dir_;
    ZoneLoop dirLoop_{ZoneLoop::None};
    double dirGain_{0.0};
    std::vector<ZoneSpec> specs_;
    std::vector<Zone> zones_;
    std::array<std::vector<int>, 128> onZones_, offZones_;  // zones by key: note-on (attack/first/legato), release
    std::vector<std::uint32_t> seqCount_;
    std::vector<int> playing_;
    std::vector<Voice> voices_;
    std::vector<float> mixL_, mixR_;
    std::array<Held, kMaxHeld> held_{};
    int heldCount_{0}, keysDown_{0};
    bool pedalDown_{false}, hasPedalReleaseZones_{false};
    float halfDb_{0.0f};        // half pedal: dB per control block a pedal-held treble note loses (0 = full pedal)
    StringBank strings_;
    double sr_{48000.0};
    int poly_{32};
    int transpose_{0};
    bool reverse_{false}, oneshot_{false}, mono_{false};
    float stealStep_{0.0f}, offStep_{0.0f}, chokeCoef_{0.0f}, rsCoef_{0.0f};
    std::uint64_t age_{0}, seed_{0};
    std::int64_t startSample_{0}, clock_{0};
    const TempoMap* tempoMap_{nullptr};   // set only for songs whose tempo changes
    float bend_{0.0f}, cutoff_{20000.0f}, res_{0.0f}, pan_{0.0f}, width_{1.0f}, gain_{1.0f};
    float bend1_{0.0f}, cutoff1_{20000.0f}, res1_{0.0f}, pan1_{0.0f}, width1_{1.0f}, gain1_{1.0f};
    float outGain_{1.0f};
    // realism: live dynamics, layers, legato, vibrato, keyswitches
    bool legatoMode_{false}, layersDyn_{false};
    int xfSpread_{1};
    std::vector<std::array<float, 3>> playLayer_;   // per playing_ entry: layer neighbours (lo, mid, hi) or mid -1
    float dyn_{1.0f}, dyn1_{1.0f}, vib_{0.0f}, vib1_{0.0f}, vibRate_{5.5f}, vibRate1_{5.5f};
    double vibPhase_{0.0};
    float harm_{0.0f}, harm1_{0.0f}, hEnvCoef_{0.0f}, hPeakFall_{1.0f};
    bool harmActive_{false};
    float dynTone_{0.5f}, lineFadeStep_{0.0f};
    bool tiltOn_{false};
    smp::Tilt tilt_;
    std::array<bool, 128> swKey_{}, swLastKey_{}, swHeld_{};   // keyswitch keys (silent), those that set the last one, held
    int swDefault_{-1}, swLast_{-1}, swNoteCount_{0};
    std::array<std::pair<int, int>, kMaxSwitchNotes> swNotes_{};   // held keyswitch notes (id, key)
};

}  // namespace

std::unique_ptr<Instrument> makeSampler() { return std::make_unique<Sampler>(); }

}  // namespace as
