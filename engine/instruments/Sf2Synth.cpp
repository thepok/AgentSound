#include "instruments/Sf2Synth.h"

#include "dsp/Dsp.h"
#include "instruments/SamplerCore.h"
#include "instruments/Sf2File.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <memory>
#include <string>
#include <vector>

namespace as {
namespace {

using sf2::kGenCount;
using sf2::Modulator;

// Output calibration: a GM piano (GeneralUser GS "Grand Piano") playing held 4-note chords at velocity
// 100 sits around -18 LUFS at level 0; the font's own balance sets every other preset relative to it.
constexpr double kOutGain = 1.0;
constexpr const char* kDefaultFile = "GeneralUser-GS.sf2";  // in assets/soundfonts/
// initialAttenuation generators are applied x 0.4, like the EMU8000/10K1 hardware and FluidSynth do and
// GM SoundFonts (GeneralUser GS included) are balanced for. Modulator contributions (velocity) are not scaled.
constexpr double kAttenuationFactor = 0.4;
constexpr double kStealSeconds = 0.004;       // stolen / mono-replaced voices fade out linearly
constexpr double kChokeSeconds = 0.1;         // exclusive-class choke: 96 dB in 100 ms (-20 dB after ~20 ms)
constexpr double kMinReleaseSeconds = 0.0156; // shortest volume release (-7200 timecents, as FluidSynth)
constexpr double kGainTau = 0.0015;           // level, pan, width, pitch bend smoothing (~5 ms 10-90 %)
constexpr double kToneTau = 0.002;            // cutoff, brightness (~7 ms)
constexpr float kSilentAmp = 1e-5f;           // a decaying voice below -100 dB is finished

enum Param { kLevel, kPan, kWidth, kTranspose, kTune, kPitchbend, kCutoff, kBrightness, kVelsens, kAttack, kRelease,
             kPolyphony, kMono, kBank, kProgram, kPedal, kExpression };

std::vector<ParamSpec> makeSpecs() {
    return {
        num("level", -60.0f, 12.0f, 0.0f, "dB",
            "Output level. At 0 dB a GM piano playing 4-note chords at velocity 100 sits around -18 LUFS; the "
            "SoundFont's own balance places every other preset relative to it (GM-balanced fonts: similar loudness)."),
        num("pan", -1.0f, 1.0f, 0.0f, "",
            "Moves the whole stereo image -1 (left) .. 1 (right); the preset's own per-key / per-layer panning is "
            "kept around it (scaled by width)."),
        num("width", 0.0f, 2.0f, 1.0f, "",
            "Stereo width of the preset's own panning (stereo pianos pan bass left / treble right, linked stereo "
            "samples hard left/right): 1 = as designed, 0 = mono, up to 2 = exaggerated. Mono presets stay centred: "
            "widen them with fx (ensemble, chorus) and reverb sends."),
        num("transpose", -36.0f, 36.0f, 0.0f, "st",
            "Whole semitones added to every note before the key zones are chosen (plays the samples a real "
            "instrument would use there).", false),
        num("tune", -100.0f, 100.0f, 0.0f, "ct", "Fine tuning in cents for every voice.", false),
        num("pitchbend", -24.0f, 24.0f, 0.0f, "st",
            "Pitch bend in (fractional) semitones for all sounding voices; automate for bends, dives and "
            "tape-stop effects. Smoothed."),
        num("cutoff", -96.0f, 48.0f, 0.0f, "st",
            "Moves every voice's resonant lowpass (the SoundFont's own filter, fully open = 19.9 kHz) by this many "
            "semitones: -12 = an octave darker, -36..-60 = muffled / underwater, 0 = as designed. Voices without a "
            "filter in the font get one when it is below 0. Automatable for filter sweeps on samples. Smoothed."),
        num("brightness", -1.0f, 1.0f, 0.0f, "",
            "Gentle tilt EQ on the output: negative tames bright or harsh presets (down to -10 dB above ~2.5 kHz, "
            "+2 dB lows), positive adds air (up to +6 dB). 0 = untouched."),
        num("velsens", 0.0f, 1.0f, 1.0f, "",
            "Velocity response: 1 = as the font designs it (velocity picks layers and sets level / brightness), "
            "lower squeezes note velocities towards 100, 0 = every note plays as velocity 100.", false),
        num("attack", 0.05f, 20.0f, 1.0f, "x",
            "Multiplies the preset's attack times (volume and modulation envelope): 3-10 = softer swells for "
            "strings/pads, 0.3 = snappier.", false),
        num("release", 0.05f, 20.0f, 1.0f, "x",
            "Multiplies the preset's release times (volume and modulation envelope): 2-4 = longer, lusher tails, "
            "0.3 = tighter, drier notes (never below 16 ms).", false),
        num("polyphony", 1.0f, 256.0f, 64.0f, "voices",
            "Max simultaneous voices (a note can use several: layers, stereo pairs). When full, the oldest "
            "released (else oldest) voice is stolen with a 4 ms fade.", false),
        choice("mono", {"off", "on"}, 0,
               "on: one note at a time; a new note fades the previous one out in 4 ms (basses, solo leads). "
               "off: polyphonic."),
        num("bank", -1.0f, 128.0f, -1.0f, "",
            "Bank of the preset (with 'program'), instead of the 'preset' name: 0 = GM melodic, 128 = GM drum "
            "kits, 8/16/... = variations. -1 = use 'preset' (default: the file's first preset, GM 0:0 Grand Piano).",
            false),
        num("program", -1.0f, 127.0f, -1.0f, "",
            "Program number 0..127 of the preset (with 'bank'; bank defaults to 0). -1 = use 'preset'. List them: "
            "`agentsound sf2 [search]`.", false),
        num("pedal", 0.0f, 1.0f, 0.0f, "",
            "Sustain pedal (CC64): >= 0.5 is down. While down, note-offs are held (the notes ring on until the pedal is "
            "released; a re-struck key starts a new voice and the old one rings on). A step: automate it with 'step' "
            "points at bar or chord changes."),
        num("expression", 0.0f, 1.0f, 1.0f, "",
            "Expression (CC11): output gain = expression^2 (0.5 = -12 dB, 0 = silent), smoothed. Automate for swells "
            "and phrase dynamics on top of the note velocities."),
    };
}

std::array<float, kGenCount> generatorDefaults() {
    std::array<float, kGenCount> g{};
    g[sf2::InitialFilterFc] = 13500;
    for (int i : {sf2::DelayModLfo, sf2::DelayVibLfo, sf2::DelayModEnv, sf2::AttackModEnv, sf2::HoldModEnv, sf2::DecayModEnv,
                  sf2::ReleaseModEnv, sf2::DelayVolEnv, sf2::AttackVolEnv, sf2::HoldVolEnv, sf2::DecayVolEnv, sf2::ReleaseVolEnv})
        g[static_cast<std::size_t>(i)] = -12000;
    g[sf2::Keynum] = -1;
    g[sf2::Velocity] = -1;
    g[sf2::ScaleTuning] = 100;
    g[sf2::OverridingRootKey] = -1;
    return g;
}

// Generators that may appear at preset level (SF2.04 8.5: sample offsets, key/velocity overrides, sample
// modes, exclusive class and root key are instrument-only).
bool presetLevelGen(int g) {
    switch (g) {
        case sf2::StartAddrsOffset: case sf2::EndAddrsOffset: case sf2::StartloopAddrsOffset: case sf2::EndloopAddrsOffset:
        case sf2::StartAddrsCoarseOffset: case sf2::EndAddrsCoarseOffset: case sf2::StartloopAddrsCoarseOffset:
        case sf2::EndloopAddrsCoarseOffset: case sf2::Keynum: case sf2::Velocity: case sf2::SampleModes:
        case sf2::ExclusiveClass: case sf2::OverridingRootKey: case sf2::InstrumentGen: case sf2::KeyRange:
        case sf2::VelRange: case sf2::SampleID:
            return false;
        default:
            return g >= 0 && g < kGenCount;
    }
}

// Default modulators that act without MIDI controllers (SF2.04 8.4.1 and 8.4.2). The velocity->filter
// one is in its SF2 2.01 form (secondary source: velocity, switch, negative), the identity GeneralUser GS
// and Polyphone-built fonts use to switch it off.
const std::array<Modulator, 2> kDefaultMods = {{
    {0x0502, sf2::InitialAttenuation, 960, 0, 0},
    {0x0102, sf2::InitialFilterFc, -2400, 0x0D02, 0},
}};

bool supportedSource(std::uint16_t src) {
    const int index = src & 0x7F;
    const int type = src >> 10;
    if (type > 3) return false;
    if (src & 0x80) {  // MIDI CC: legal numbers only
        return !(index == 0 || index == 6 || (index >= 32 && index <= 63) || (index >= 98 && index <= 101) || index >= 120);
    }
    return index == 0 || index == 2 || index == 3 || index == 10 || index == 13 || index == 14 || index == 16;
}

bool supportedDest(std::uint16_t dest) {
    if (dest & 0x8000) return false;  // modulator links
    if (dest >= kGenCount) return false;
    return presetLevelGen(dest) || dest == sf2::StartAddrsOffset || dest == sf2::EndAddrsOffset ||
           dest == sf2::StartAddrsCoarseOffset || dest == sf2::EndAddrsCoarseOffset;
}

double concave(double x) { return x >= 1.0 ? 1.0 : x <= 0.0 ? 0.0 : std::clamp(-(5.0 / 12.0) * std::log10(1.0 - x), 0.0, 1.0); }
double convex(double x) { return x <= 0.0 ? 0.0 : x >= 1.0 ? 1.0 : std::clamp(1.0 + (5.0 / 12.0) * std::log10(x), 0.0, 1.0); }

// Mapped value of a modulator source at note-on (SF2.04 8.2: direction, polarity, curve). Controllers
// sit at their MIDI power-on values: CC7 100, CC10 64, CC11 127, other CCs and pressure 0, pitch wheel
// centred, pitch wheel sensitivity 2.
double sourceValue(std::uint16_t src, int key, int vel) {
    const int index = src & 0x7F;
    double x = 0.0;
    if (src & 0x80) {
        x = (index == 7 ? 100.0 : index == 10 ? 64.0 : index == 11 ? 127.0 : 0.0) / 127.0;
    } else {
        switch (index) {
            case 0: return 1.0;  // no controller
            case 2: x = vel / 127.0; break;
            case 3: x = key / 127.0; break;
            case 14: x = 0.5; break;
            case 16: x = 2.0 / 127.0; break;
            default: x = 0.0; break;  // poly / channel pressure
        }
    }
    if ((src >> 8) & 1) x = 1.0 - x;
    const int type = src >> 10;
    auto curve = [type](double v) {
        switch (type) {
            case 1: return concave(v);
            case 2: return convex(v);
            case 3: return v >= 0.5 ? 1.0 : 0.0;
            default: return v;
        }
    };
    if (!((src >> 9) & 1)) return curve(x);
    if (type == 3) return x >= 0.5 ? 1.0 : -1.0;
    if (type == 0) return 2.0 * x - 1.0;
    return x > 0.5 ? curve(2.0 * (x - 0.5)) : -curve(2.0 * (0.5 - x));
}

// Adds `m` to `list`: replaces an identical modulator (override) or appends.
void overrideMod(std::vector<Modulator>& list, const Modulator& m) {
    for (auto& x : list) {
        if (x.sameAs(m)) { x = m; return; }
    }
    list.push_back(m);
}

double timecents(double tc) { return tc <= -32768.0 ? 0.0 : std::exp2(tc / 1200.0); }

// One playable (preset zone x instrument zone) combination, resolved at prepare().
struct ZonePair {
    int keyLo{0}, keyHi{127}, velLo{0}, velHi{127};
    std::array<float, kGenCount> gen{};  // instrument value (local > global > default) + preset offset
    std::vector<Modulator> mods;         // resolved: defaults < instrument global < instrument local, + preset
    int sample{0};
    int loopMode{0};                     // 0 none, 1 continuous, 3 until release
    bool panSet{false};
    std::shared_ptr<const smp::Region> region;
};

struct Env {
    enum Stage : std::uint8_t { Delay, Attack, Hold, Decay, Sustain, Release, Done };
    Stage stage{Done};
    bool volume{false};
    float value{0.0f};
    float delayLeft{0.0f}, attackRate{1.0f}, holdLeft{0.0f}, decayRate{1.0f}, sustain{0.0f}, releaseRate{1.0f};

    void start(bool vol, double sr, double delay, double attack, double hold, double decay, double sus, double release) noexcept {
        volume = vol;
        stage = Delay;
        value = 0.0f;
        delayLeft = static_cast<float>(delay * sr);
        attackRate = static_cast<float>(1.0 / std::max(1.0, attack * sr));
        holdLeft = static_cast<float>(hold * sr);
        decayRate = static_cast<float>(1.0 / std::max(1.0, decay * sr));
        sustain = static_cast<float>(std::clamp(sus, 0.0, 1.0));
        releaseRate = static_cast<float>(1.0 / std::max(1.0, release * sr));
    }

    void advance(float n) noexcept {
        while (n > 0.0f) {
            switch (stage) {
                case Delay:
                    if (delayLeft > n) { delayLeft -= n; return; }
                    n -= delayLeft;
                    delayLeft = 0.0f;
                    stage = Attack;
                    break;
                case Attack: {
                    const float need = (1.0f - value) / attackRate;
                    if (need > n) { value += attackRate * n; return; }
                    n -= need;
                    value = 1.0f;
                    stage = Hold;
                    break;
                }
                case Hold:
                    if (holdLeft > n) { holdLeft -= n; return; }
                    n -= holdLeft;
                    holdLeft = 0.0f;
                    stage = Decay;
                    break;
                case Decay: {
                    const float need = (value - sustain) / decayRate;
                    if (need > n) { value -= decayRate * n; return; }
                    n -= std::max(0.0f, need);
                    value = sustain;
                    stage = Sustain;
                    break;
                }
                case Sustain:
                    return;
                case Release: {
                    const float need = value / releaseRate;
                    if (need > n) { value -= releaseRate * n; return; }
                    value = 0.0f;
                    stage = Done;
                    return;
                }
                case Done:
                    value = 0.0f;
                    return;
            }
        }
    }

    void release() noexcept {
        if (stage == Done || stage == Release) return;
        if (stage == Delay) {
            value = 0.0f;
        } else if (volume && stage == Attack) {
            // The attack is linear in amplitude, the release linear in dB: continue from the same level.
            value = value > 1.6e-5f ? std::max(0.0f, 1.0f + std::log10(value) / 4.8f) : 0.0f;
        }
        stage = Release;
    }

    // Volume envelope: amplitude (attack linear, then -96 dB .. 0 dB over value 0..1). Mod envelope: value.
    float amp() const noexcept {
        if (!volume) return value;
        switch (stage) {
            case Delay: case Done: return 0.0f;
            case Attack: return value;
            default: return value <= 0.0f ? 0.0f : std::pow(10.0f, -4.8f * (1.0f - value));
        }
    }
};

struct Lfo {
    float delayLeft{0.0f}, phase{0.0f}, inc{0.0f}, value{0.0f};
    void start(double sr, double delay, double hz) noexcept {
        delayLeft = static_cast<float>(delay * sr);
        phase = 0.0f;
        inc = static_cast<float>(hz / sr);
        value = 0.0f;
    }
    void advance(float n) noexcept {
        if (delayLeft >= n) { delayLeft -= n; return; }
        n -= delayLeft;
        delayLeft = 0.0f;
        phase += inc * n;
        phase -= std::floor(phase);
        // triangle starting at 0, rising: +1 at 1/4, -1 at 3/4
        value = phase < 0.25f ? 4.0f * phase : phase < 0.75f ? 2.0f - 4.0f * phase : 4.0f * phase - 4.0f;
    }
};

struct Voice {
    bool active{false}, keyDown{false}, finishing{false}, untilRelease{false};
    bool sustained{false};  // key up, held by the sustain pedal
    int noteId{-1};
    int exclusive{0};
    std::uint64_t age{0};
    smp::Reader reader;
    double baseInc{1.0}, inc{1.0};
    float pitchEnv{0.0f}, pitchModLfo{0.0f}, pitchVib{0.0f};  // cents at full scale
    float fcCents{13500.0f}, fcEnv{0.0f}, fcLfo{0.0f}, q{0.707f};
    float amp{1.0f}, lfoVol{0.0f}, silentBelow{kSilentAmp}, pan{0.0f};
    Env volEnv, modEnv;
    Lfo modLfo, vibLfo;
    smp::Lowpass lp;
    smp::LowpassCoefs coefs;
    int ctl{0};
    float gl{0.0f}, gr{0.0f}, dgl{0.0f}, dgr{0.0f};
    float fade{1.0f}, fadeStep{0.0f};
};

class Sf2Synth final : public Instrument {
public:
    Sf2Synth() : params_(makeSpecs()) {}

    void configure(const json& params) override {
        params_.configure(params, "sf2", {"file", "preset"});
        file_ = kDefaultFile;
        preset_.clear();
        if (params.is_object()) {
            if (params.contains("file")) {
                const json& f = params["file"];
                if (!f.is_string() || f.get<std::string>().empty()) {
                    throw ConfigError("sf2: 'file' must be a SoundFont file name such as \"GeneralUser-GS.sf2\" (in assets/soundfonts/) or an absolute path");
                }
                file_ = f.get<std::string>();
            }
            if (params.contains("preset")) {
                const json& p = params["preset"];
                if (!p.is_string() || sf2::normalizeName(p.get<std::string>()).empty()) {
                    throw ConfigError("sf2: 'preset' must be a preset name such as \"Grand Piano\" or \"bank:program\" such as \"0:48\"");
                }
                preset_ = p.get<std::string>();
            }
        }
        for (const int p : {kTranspose, kPolyphony, kBank, kProgram}) {
            const float value = params_.get(p);
            if (value != std::round(value)) {
                throw ConfigError("sf2: '" + params_.specs()[static_cast<std::size_t>(p)].name + "' must be a whole number");
            }
        }
        const bool numeric = params_.get(kBank) >= 0.0f || params_.get(kProgram) >= 0.0f;
        if (!preset_.empty() && numeric) throw ConfigError("sf2: give either 'preset' or 'bank' + 'program', not both");
        if (params_.get(kBank) >= 0.0f && params_.get(kProgram) < 0.0f) throw ConfigError("sf2: 'bank' needs a 'program' (0..127)");
    }

    void prepare(const RenderContext& ctx) override {
        sr_ = ctx.sampleRate;
        smp::Kernel::get();  // build the interpolation tables now, not in the first process()
        file_ptr_ = sf2::load(sf2::resolvePath(ctx.assetDir, file_));
        const sf2::File& file = *file_ptr_;
        const sf2::Preset* preset = nullptr;
        if (!preset_.empty()) preset = &file.resolvePreset(preset_);
        else if (params_.get(kProgram) >= 0.0f)
            preset = &file.resolvePreset(std::max(0, static_cast<int>(params_.get(kBank))), static_cast<int>(params_.get(kProgram)));
        else preset = file.sortedPresets().front();
        buildPairs(file, *preset);
        if (pairs_.empty()) throw ConfigError("sf2: preset '" + preset->name + "' has no playable zones");

        poly_ = static_cast<int>(params_.get(kPolyphony));
        voices_.assign(static_cast<std::size_t>(poly_ + std::max(8, poly_ / 2)), Voice{});
        const int maxBlock = std::max(1, ctx.maxBlock);
        mixL_.assign(static_cast<std::size_t>(maxBlock), 0.0f);
        mixR_.assign(static_cast<std::size_t>(maxBlock), 0.0f);
        transpose_ = static_cast<int>(params_.get(kTranspose));
        mono_ = params_.choice("mono") == 1;
        stealStep_ = static_cast<float>(1.0 / (kStealSeconds * sr_));
        chokeRate_ = static_cast<float>(1.0 / (kChokeSeconds * sr_));
        age_ = 0;

        bend_ = bend1_ = params_.get(kPitchbend);
        cutoff_ = cutoff1_ = params_.get(kCutoff);
        pan_ = pan1_ = params_.get(kPan);
        width_ = width1_ = params_.get(kWidth);
        bright_ = bright1_ = params_.get(kBrightness);
        gain_ = gain1_ = outGain_ = outputGain();
        tilt_.prepare(sr_, bright_);
        pedalDown_ = params_.get(kPedal) >= 0.5f;
    }

    bool setParam(std::string_view name, float value) override {
        if (!params_.set(name, value)) return false;
        if (name == "pedal") applyPedal();
        return true;
    }

    void noteOn(int noteId, int pitch, float velocity) override {
        const int key = pitch + transpose_;
        if (key < 0 || key > 127) return;
        int vel = std::clamp(static_cast<int>(std::lround(velocity * 127.0f)), 1, 127);
        vel = std::clamp(static_cast<int>(std::lround(100.0f + (static_cast<float>(vel) - 100.0f) * params_.get(kVelsens))), 1, 127);
        if (mono_) {
            for (auto& v : voices_) {
                if (v.active && v.fadeStep <= 0.0f) fadeInPlace(v);
            }
        }
        for (const auto& p : pairs_) {  // exclusive classes: a new note chokes other notes of its class
            if (key < p.keyLo || key > p.keyHi || vel < p.velLo || vel > p.velHi) continue;
            const int cls = static_cast<int>(p.gen[sf2::ExclusiveClass]);
            if (cls == 0) continue;
            for (auto& v : voices_) {
                if (v.active && v.exclusive == cls && v.noteId != noteId) choke(v);
            }
        }
        for (const auto& p : pairs_) {
            if (key < p.keyLo || key > p.keyHi || vel < p.velLo || vel > p.velHi) continue;
            startVoice(allocate(), p, key, vel, noteId);
        }
    }

    void noteOff(int noteId) override {
        for (auto& v : voices_) {
            if (v.active && v.keyDown && v.noteId == noteId) {
                v.keyDown = false;
                if (pedalDown_) v.sustained = true;  // rings on until pedal-up
                else release(v);
            }
        }
    }

    void process(float* left, float* right, int frames) override {
        if (frames <= 0) return;
        updateControls(frames);
        std::fill_n(mixL_.data(), frames, 0.0f);
        std::fill_n(mixR_.data(), frames, 0.0f);
        for (auto& v : voices_) {
            if (v.active) renderVoice(v, mixL_.data(), mixR_.data(), frames);
        }
        tilt_.process(mixL_.data(), mixR_.data(), frames, bright_);
        float g = outGain_;
        const float dg = (gain_ - outGain_) / static_cast<float>(frames);
        for (int i = 0; i < frames; ++i) {
            g += dg;
            left[i] = mixL_[static_cast<std::size_t>(i)] * g;
            right[i] = mixR_[static_cast<std::size_t>(i)] * g;
        }
        outGain_ = gain_;
    }

    bool idle() const override {
        return std::none_of(voices_.begin(), voices_.end(), [](const Voice& v) { return v.active; }) && tilt_.settled();
    }

    const std::vector<ParamSpec>& paramSpecs() const override { return params_.specs(); }

private:
    void release(Voice& v) noexcept {
        v.volEnv.release();
        v.modEnv.release();
        if (v.untilRelease) v.reader.exitAtWrap = true;
    }

    // Sustain pedal changes (between blocks): pedal-up releases every note it held.
    void applyPedal() noexcept {
        const bool down = params_.get(kPedal) >= 0.5f;
        if (down == pedalDown_) return;
        pedalDown_ = down;
        if (down) return;
        for (auto& v : voices_) {
            if (v.active && v.sustained) {
                v.sustained = false;
                release(v);
            }
        }
    }

    float outputGain() const noexcept {
        const float e = params_.get(kExpression);
        return static_cast<float>(dsp::dbToGain(params_.get(kLevel)) * kOutGain) * e * e;
    }

    void buildPairs(const sf2::File& file, const sf2::Preset& preset) {
        pairs_.clear();
        const auto defaults = generatorDefaults();
        for (const sf2::Zone& pz : preset.zones) {
            const sf2::Instrument& ins = file.instruments[static_cast<std::size_t>(pz.target)];
            // preset-level offsets: local zone overrides the global zone
            std::array<float, kGenCount> offset{};
            bool presetPan = false;
            for (int g = 0; g < kGenCount; ++g) {
                if (!presetLevelGen(g)) continue;
                if (pz.has(g)) offset[static_cast<std::size_t>(g)] = pz.gen[static_cast<std::size_t>(g)];
                else if (preset.global.has(g)) offset[static_cast<std::size_t>(g)] = preset.global.gen[static_cast<std::size_t>(g)];
                if (g == sf2::Pan && (pz.has(g) || preset.global.has(g))) presetPan = true;
            }
            std::vector<Modulator> presetMods;
            for (const auto& m : preset.global.mods) overrideMod(presetMods, m);
            for (const auto& m : pz.mods) overrideMod(presetMods, m);

            for (const sf2::Zone& iz : ins.zones) {
                ZonePair p;
                p.keyLo = std::max(pz.keyLo, iz.keyLo);
                p.keyHi = std::min(pz.keyHi, iz.keyHi);
                p.velLo = std::max(pz.velLo, iz.velLo);
                p.velHi = std::min(pz.velHi, iz.velHi);
                if (p.keyLo > p.keyHi || p.velLo > p.velHi) continue;
                std::array<float, kGenCount> inst = defaults;
                for (int g = 0; g < kGenCount; ++g) {
                    if (iz.has(g)) inst[static_cast<std::size_t>(g)] = iz.gen[static_cast<std::size_t>(g)];
                    else if (ins.global.has(g)) inst[static_cast<std::size_t>(g)] = ins.global.gen[static_cast<std::size_t>(g)];
                }
                for (int g = 0; g < kGenCount; ++g) p.gen[static_cast<std::size_t>(g)] = inst[static_cast<std::size_t>(g)] + offset[static_cast<std::size_t>(g)];
                p.panSet = presetPan || iz.has(sf2::Pan) || ins.global.has(sf2::Pan);

                // modulators: defaults, overridden by the instrument global zone, then the local zone;
                // preset modulators add to identical ones (or are appended)
                std::vector<Modulator> mods(kDefaultMods.begin(), kDefaultMods.end());
                for (const auto& m : ins.global.mods) overrideMod(mods, m);
                for (const auto& m : iz.mods) overrideMod(mods, m);
                for (const auto& m : presetMods) {
                    bool merged = false;
                    for (auto& x : mods) {
                        if (x.sameAs(m)) {
                            x.amount = static_cast<std::int16_t>(std::clamp(x.amount + m.amount, -32768, 32767));
                            merged = true;
                            break;
                        }
                    }
                    if (!merged) mods.push_back(m);
                }
                for (const auto& m : mods) {
                    if (m.amount != 0 && supportedSource(m.src) && supportedSource(m.amtSrc) && supportedDest(m.dest) &&
                        (m.trans == 0 || m.trans == 2))
                        p.mods.push_back(m);
                }

                p.sample = iz.target;
                const sf2::Sample& s = file.samples[static_cast<std::size_t>(p.sample)];
                if (s.rom()) {
                    throw ConfigError("sf2: preset '" + preset.name + "' uses sample '" + s.name + "' from a sound ROM (not in the file)");
                }
                const std::int64_t frames = s.frames();
                const int mode = static_cast<int>(inst[sf2::SampleModes]) & 3;
                p.loopMode = mode == 2 ? 0 : mode;
                const std::int64_t ls = static_cast<std::int64_t>(s.loopStart) - s.start +
                                        static_cast<std::int64_t>(inst[sf2::StartloopAddrsOffset]) +
                                        32768 * static_cast<std::int64_t>(inst[sf2::StartloopAddrsCoarseOffset]);
                const std::int64_t le = static_cast<std::int64_t>(s.loopEnd) - s.start +
                                        static_cast<std::int64_t>(inst[sf2::EndloopAddrsOffset]) +
                                        32768 * static_cast<std::int64_t>(inst[sf2::EndloopAddrsCoarseOffset]);
                if (p.loopMode != 0 && !(ls >= 0 && le <= frames && le - ls >= 1)) p.loopMode = 0;  // invalid loop: play through
                if (frames < 1) continue;
                p.region = file.region(p.sample, p.loopMode != 0 ? smp::LoopMode::Forward : smp::LoopMode::None, ls, le);
                pairs_.push_back(std::move(p));
            }
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
        // move the victim into a spare slot where it fades out
        Voice* spare = nullptr;
        for (std::size_t i = static_cast<std::size_t>(poly_); i < voices_.size(); ++i) {
            Voice& s = voices_[i];
            if (!s.active) { spare = &s; break; }
            if (!spare || s.fade < spare->fade) spare = &s;
        }
        *spare = *victim;
        fadeInPlace(*spare);
        victim->active = false;
        return *victim;
    }

    void fadeInPlace(Voice& v) noexcept {
        v.keyDown = false;
        v.sustained = false;
        v.noteId = -1;
        v.fadeStep = stealStep_;
    }

    void choke(Voice& v) noexcept {
        v.keyDown = false;
        v.sustained = false;
        v.volEnv.release();
        v.volEnv.releaseRate = std::max(v.volEnv.releaseRate, chokeRate_);
        v.modEnv.release();
    }

    void startVoice(Voice& v, const ZonePair& p, int key, int vel, int noteId) {
        const sf2::Sample& s = file_ptr_->samples[static_cast<std::size_t>(p.sample)];
        const int keyEff = p.gen[sf2::Keynum] >= 0.0f ? static_cast<int>(p.gen[sf2::Keynum]) : key;
        const int velEff = p.gen[sf2::Velocity] >= 0.0f ? static_cast<int>(p.gen[sf2::Velocity]) : vel;
        std::array<float, kGenCount> mod{};
        for (const auto& m : p.mods) {
            if ((m.src & 0xFF) == 0) continue;  // primary source "no controller": no output
            double value = m.amount * sourceValue(m.src, keyEff, velEff) * sourceValue(m.amtSrc, keyEff, velEff);
            if (m.trans == 2) value = std::fabs(value);
            mod[m.dest] += static_cast<float>(value);
        }
        auto G = [&](int g) { return static_cast<double>(p.gen[static_cast<std::size_t>(g)]) + mod[static_cast<std::size_t>(g)]; };

        const smp::Region& r = *p.region;
        const double frames = static_cast<double>(r.frames);
        const double start = std::clamp(G(sf2::StartAddrsOffset) + 32768.0 * G(sf2::StartAddrsCoarseOffset), 0.0, frames - 1.0);
        const double end = std::clamp(frames + G(sf2::EndAddrsOffset) + 32768.0 * G(sf2::EndAddrsCoarseOffset), start + 1.0, frames);
        v.reader.start(r, start, end, p.loopMode != 0);
        v.untilRelease = p.loopMode == 3;

        const int root = p.gen[sf2::OverridingRootKey] >= 0.0f ? static_cast<int>(p.gen[sf2::OverridingRootKey]) : (s.pitch <= 127 ? s.pitch : 60);
        const double cents = G(sf2::ScaleTuning) * (keyEff - root) + 100.0 * G(sf2::CoarseTune) + G(sf2::FineTune) + s.correction +
                             params_.get(kTune);
        v.baseInc = static_cast<double>(s.rate) / sr_ * std::exp2(cents / 1200.0);
        v.inc = v.baseInc;
        v.pitchEnv = static_cast<float>(std::clamp(G(sf2::ModEnvToPitch), -12000.0, 12000.0));
        v.pitchModLfo = static_cast<float>(std::clamp(G(sf2::ModLfoToPitch), -12000.0, 12000.0));
        v.pitchVib = static_cast<float>(std::clamp(G(sf2::VibLfoToPitch), -12000.0, 12000.0));

        v.fcCents = static_cast<float>(std::clamp(G(sf2::InitialFilterFc), 1500.0, 13500.0));
        v.fcEnv = static_cast<float>(std::clamp(G(sf2::ModEnvToFilterFc), -12000.0, 12000.0));
        v.fcLfo = static_cast<float>(std::clamp(G(sf2::ModLfoToFilterFc), -12000.0, 12000.0));
        const double qcb = std::clamp(G(sf2::InitialFilterQ), 0.0, 960.0);
        v.q = static_cast<float>(std::pow(10.0, (qcb / 10.0 - 3.01) / 20.0));

        // attenuation: generators x 0.4 (see kAttenuationFactor), modulators as they are; the resonance
        // peak is compensated by half its height (SF2.04 8.1.3, initialFilterQ)
        const double atten = std::clamp(kAttenuationFactor * p.gen[sf2::InitialAttenuation] + mod[sf2::InitialAttenuation], 0.0, 1440.0);
        v.amp = static_cast<float>(std::pow(10.0, -atten / 200.0) * std::pow(10.0, -qcb / 400.0));
        v.lfoVol = static_cast<float>(std::clamp(G(sf2::ModLfoToVolume), -960.0, 960.0));
        v.silentBelow = static_cast<float>(kSilentAmp / std::pow(10.0, std::fabs(v.lfoVol) / 200.0));

        double pan = std::clamp(G(sf2::Pan), -500.0, 500.0) / 500.0;
        if (!p.panSet) {  // linked stereo samples: left / right side unless the font pans them itself
            if (s.type & 4) pan = -1.0;
            else if (s.type & 2) pan = 1.0;
        }
        v.pan = static_cast<float>(pan);

        const double keyOff = 60.0 - keyEff;
        const double attackScale = params_.get(kAttack), releaseScale = params_.get(kRelease);
        v.volEnv.start(true, sr_, timecents(std::clamp(G(sf2::DelayVolEnv), -12000.0, 5000.0)),
                       timecents(std::clamp(G(sf2::AttackVolEnv), -12000.0, 8000.0)) * attackScale,
                       timecents(std::clamp(G(sf2::HoldVolEnv) + G(sf2::KeynumToVolEnvHold) * keyOff, -12000.0, 5000.0)),
                       timecents(std::clamp(G(sf2::DecayVolEnv) + G(sf2::KeynumToVolEnvDecay) * keyOff, -12000.0, 8000.0)),
                       1.0 - std::clamp(G(sf2::SustainVolEnv), 0.0, 1440.0) / 960.0,
                       std::max(kMinReleaseSeconds, timecents(std::clamp(G(sf2::ReleaseVolEnv), -12000.0, 8000.0)) * releaseScale));
        v.modEnv.start(false, sr_, timecents(std::clamp(G(sf2::DelayModEnv), -12000.0, 5000.0)),
                       timecents(std::clamp(G(sf2::AttackModEnv), -12000.0, 8000.0)) * attackScale,
                       timecents(std::clamp(G(sf2::HoldModEnv) + G(sf2::KeynumToModEnvHold) * keyOff, -12000.0, 5000.0)),
                       timecents(std::clamp(G(sf2::DecayModEnv) + G(sf2::KeynumToModEnvDecay) * keyOff, -12000.0, 8000.0)),
                       1.0 - std::clamp(G(sf2::SustainModEnv), 0.0, 1000.0) / 1000.0,
                       timecents(std::clamp(G(sf2::ReleaseModEnv), -12000.0, 8000.0)) * releaseScale);
        v.modLfo.start(sr_, timecents(std::clamp(G(sf2::DelayModLfo), -12000.0, 5000.0)),
                       smp::centsToHz(std::clamp(G(sf2::FreqModLfo), -16000.0, 4500.0)));
        v.vibLfo.start(sr_, timecents(std::clamp(G(sf2::DelayVibLfo), -12000.0, 5000.0)),
                       smp::centsToHz(std::clamp(G(sf2::FreqVibLfo), -16000.0, 4500.0)));

        v.exclusive = static_cast<int>(p.gen[sf2::ExclusiveClass]);
        v.active = true;
        v.keyDown = true;
        v.sustained = false;
        v.finishing = false;
        v.noteId = noteId;
        v.age = ++age_;
        v.ctl = 0;
        v.gl = v.gr = v.dgl = v.dgr = 0.0f;
        v.fade = 1.0f;
        v.fadeStep = 0.0f;
        v.lp.reset();
    }

    // Starts a control block: envelopes/LFOs advance to its end, pitch / filter / gain targets are set.
    bool beginBlock(Voice& v) noexcept {
        if (v.finishing) {
            v.active = false;
            return false;
        }
        constexpr float n = static_cast<float>(smp::kControl);
        v.volEnv.advance(n);
        v.modEnv.advance(n);
        v.modLfo.advance(n);
        v.vibLfo.advance(n);
        const float me = v.modEnv.value, ml = v.modLfo.value, vl = v.vibLfo.value;
        const double cents = v.pitchEnv * me + v.pitchModLfo * ml + v.pitchVib * vl + bend_ * 100.0;
        v.inc = cents == 0.0 ? v.baseInc : v.baseInc * std::exp2(cents / 1200.0);
        const double fc = v.fcCents + v.fcEnv * me + v.fcLfo * ml + cutoff_ * 100.0;
        v.coefs.set(sr_, smp::centsToHz(fc), v.q);

        const float env = v.amp * v.volEnv.amp();
        float a = env;
        if (v.lfoVol != 0.0f) a *= std::pow(10.0f, ml * v.lfoVol / 200.0f);
        if (v.fadeStep > 0.0f) {
            v.fade = std::max(0.0f, v.fade - v.fadeStep * n);
            a *= v.fade;
        }
        if (v.volEnv.stage == Env::Done || (v.fadeStep > 0.0f && v.fade <= 0.0f) || v.reader.done ||
            (v.volEnv.stage >= Env::Decay && env < v.silentBelow)) {
            v.finishing = true;  // ramp to silence over this block, then free the voice
            a = 0.0f;
        }
        float gl, gr;
        dsp::panGains(std::clamp(pan_ + v.pan * width_, -1.0f, 1.0f), gl, gr);
        v.dgl = (a * gl - v.gl) / n;
        v.dgr = (a * gr - v.gr) / n;
        v.ctl = smp::kControl;
        return true;
    }

    void renderVoice(Voice& v, float* L, float* R, int frames) noexcept {
        float buf[smp::kControl];
        int done = 0;
        while (done < frames) {
            if (v.ctl == 0 && !beginBlock(v)) return;
            const int m = std::min(frames - done, v.ctl);
            v.reader.read(buf, nullptr, m, v.inc);
            float gl = v.gl, gr = v.gr;
            for (int i = 0; i < m; ++i) {
                const float x = v.coefs.process(v.lp, buf[i]);
                gl += v.dgl;
                gr += v.dgr;
                L[done + i] += x * gl;
                R[done + i] += x * gr;
            }
            v.gl = gl;
            v.gr = gr;
            v.ctl -= m;
            done += m;
        }
        v.lp.flush();
    }

    void updateControls(int frames) noexcept {
        const double t = static_cast<double>(frames) / sr_;
        const float fast = static_cast<float>(std::exp(-t / kGainTau)), tone = static_cast<float>(std::exp(-t / kToneTau));
        smp::glide(bend1_, bend_, params_.get(kPitchbend), fast);
        smp::glide(pan1_, pan_, params_.get(kPan), fast);
        smp::glide(width1_, width_, params_.get(kWidth), fast);
        smp::glide(gain1_, gain_, outputGain(), fast);
        smp::glide(cutoff1_, cutoff_, params_.get(kCutoff), tone);
        smp::glide(bright1_, bright_, params_.get(kBrightness), tone);
    }

    Params params_;
    std::string file_{kDefaultFile};
    std::string preset_;
    std::shared_ptr<const sf2::File> file_ptr_;
    std::vector<ZonePair> pairs_;
    std::vector<Voice> voices_;
    std::vector<float> mixL_, mixR_;
    smp::Tilt tilt_;
    double sr_{48000.0};
    int poly_{64};
    int transpose_{0};
    bool mono_{false}, pedalDown_{false};
    float stealStep_{0.0f}, chokeRate_{0.0f};
    std::uint64_t age_{0};
    // smoothed controls (and their first smoothing stage)
    float bend_{0.0f}, cutoff_{0.0f}, pan_{0.0f}, width_{1.0f}, bright_{0.0f}, gain_{1.0f};
    float bend1_{0.0f}, cutoff1_{0.0f}, pan1_{0.0f}, width1_{1.0f}, bright1_{0.0f}, gain1_{1.0f};
    float outGain_{1.0f};
};

}  // namespace

std::unique_ptr<Instrument> makeSf2Synth() { return std::make_unique<Sf2Synth>(); }

}  // namespace as
