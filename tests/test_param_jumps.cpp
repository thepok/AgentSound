// Click safety, automation response and tempo-grid alignment of EVERY module (enumerated from the
// registry, so a new module or parameter is covered automatically).
//
// 1. Jumps: for every automatable parameter of every instrument and effect, a musical signal is
//    rendered while the parameter jumps abruptly between min, max, default and random values every
//    50 ms (setParam between 32-sample blocks, like the renderer's automation). The energy above
//    9 kHz (4th-order Butterworth high-pass) in 1 ms windows right after each jump is compared with
//    the signal's own high-frequency content at that moment: renders with the parameter held at the
//    value before / after the jump (and, if needed, at values in between: a fast sweep may pass
//    brighter states), and the settled parts of the segments around the jump. A jump that is clearly
//    louder up there is a click (a raw discontinuity). Intended timbre changes (a toggle, a bit depth)
//    are fine as long as the transition itself does not click. The instrument and effect test
//    signals are dark (effects: saw chord to 4 kHz + low-passed noise bursts), so clicks are not
//    masked. A calibration run proves the detector flags an unsmoothed gain.
// 2. Step response: the 10-90 % response time of every parameter (projection of a stepped render onto
//    the difference of two renders held at the two values; pitch parameters with a pitch tracker).
//    Automation must stay snappy: <= 10 ms, so trance gates and step modulation keep their shape.
//    The listed exceptions are slower on purpose (delay-time glides), act through a time constant of
//    their own, or apply to the next note/hit/cycle.
// 3. Tempo grid: every tempo-synced module renders a preview starting at song beat 13.5 that is
//    phase-identical to the same span of a full render (also free-running LFOs at a constant rate and
//    the reverbs' delay-line modulation).

#include "dsp/Dsp.h"
#include "instruments/Dx7Banks.h"
#include "render/Registry.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <string_view>
#include <string>
#include <vector>

#ifdef _WIN32
#include <process.h>
#define AS_TEST_PID _getpid()
#else
#include <unistd.h>
#define AS_TEST_PID getpid()
#endif

using namespace as;

namespace {

int gFail = 0, gChecks = 0;

void check(bool ok, const std::string& what) {
    ++gChecks;
    if (!ok) ++gFail;
    std::printf("  [%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
}

template <typename... A>
std::string fmt(const char* f, A... a) {
    char buf[1024];
    std::snprintf(buf, sizeof buf, f, a...);
    return buf;
}

constexpr double kSr = 48000.0;
constexpr double kBpm = 120.0;
constexpr int kBlock = kAutomationStep;   // 32: the renderer's automation granularity
constexpr int kWin = 48;                  // 1 ms analysis window
constexpr long kSeg = 2400;               // 50 ms between jumps (75 blocks)
constexpr long kFirstJump = 7808;         // 162.7 ms (block aligned, off the beat and note grids)
constexpr int kJumps = 12;
constexpr double kClickLimit = 4.0;       // jump HF energy / the signal's own HF energy (+6 dB)
constexpr double kRiseLimitMs = 10.0;     // 10-90 % response
constexpr double kLatencyLimitMs = 5.0;   // step -> 10 % (1 ms analysis window, control-rate updates, and
                                          // the part of a log-frequency glide that barely changes the sound)

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
    std::size_t size() const { return l.size(); }
};

struct Note {
    long on, off;  // samples
    int pitch;
    float vel;
};
struct Set {
    long at;  // sample (block aligned)
    std::string name;
    float value;
};

long blocks(double sec) { return static_cast<long>(std::lround(sec * kSr / kBlock)) * kBlock; }

// ---------------------------------------------------------------------------------------------
// Material

// Sustained chord (+ repeated notes every 150 ms, onsets 25 ms before a jump, 60 ms long).
std::vector<Note> synthNotes(long length, bool repeated = true) {
    std::vector<Note> n;
    for (int p : {48, 55, 60, 64}) n.push_back({blocks(0.02), length - blocks(0.05), p, 0.8f});
    if (!repeated) return n;
    for (long t = kFirstJump - 1200; t + 3000 < length; t += 3 * kSeg) {
        const long at = t - t % kBlock;
        n.push_back({at, at + blocks(0.06), 72 + static_cast<int>((t / kSeg) % 3) * 2, 0.7f});
    }
    return n;
}

// Drum hits (every 100 ms, 25 ms before every other jump) of the piece a parameter belongs to;
// global parameters get a small groove.
std::vector<Note> drumNotes(const std::string& param, long length) {
    std::vector<int> pitches;
    auto starts = [&](const char* p) { return param.rfind(p, 0) == 0; };
    if (starts("kick.")) pitches = {36};
    else if (starts("snare.")) pitches = {38};
    else if (starts("clap.")) pitches = {39};
    else if (starts("hat.")) pitches = {42, 46};
    else if (starts("tom.")) pitches = {45, 48, 41};
    else if (starts("crash.")) pitches = {49};
    else if (starts("ride.")) pitches = {51, 59};
    else if (starts("rim.")) pitches = {37};
    else if (starts("cowbell.")) pitches = {56};
    else if (starts("tamb.")) pitches = {54};
    else pitches = {36, 42, 38, 42};
    std::vector<Note> n;
    int k = 0;
    for (long t = kFirstJump - 1200 - 2 * kSeg; t + 2400 < length; t += 2 * kSeg, ++k) {
        const long at = std::max<long>(0, t - t % kBlock);
        n.push_back({at, at + blocks(0.05), pitches[static_cast<std::size_t>(k) % pitches.size()], 0.85f});
    }
    return n;
}

// Effect input: dark saw chord (harmonics to 4 kHz, different phases per side) plus low-passed noise
// bursts every 125 ms; ~-14 dBFS RMS, almost nothing above 8 kHz so clicks stand out.
const Stereo& fxInput() {
    static const Stereo s = [] {
        const std::size_t n = static_cast<std::size_t>(9.5 * kSr);
        Stereo x(n);
        const double f0[3] = {110.0, 164.81, 277.18};
        for (int v = 0; v < 3; ++v) {
            const int harmonics = static_cast<int>(4000.0 / f0[v]);
            for (int h = 1; h <= harmonics; ++h) {
                const double a = 0.12 / h, w = dsp::kTwoPi * f0[v] * h / kSr;
                const double phL = 0.37 * h * (v + 1), phR = phL + 0.5 * h;
                double cL = std::cos(phL), sL = std::sin(phL), cR = std::cos(phR), sR = std::sin(phR);
                const double cw = std::cos(w), sw = std::sin(w);
                for (std::size_t i = 0; i < n; ++i) {  // complex rotation (double: accurate for seconds)
                    x.l[i] += static_cast<float>(a * sL);
                    x.r[i] += static_cast<float>(a * sR);
                    const double c1 = cL * cw - sL * sw, s1 = sL * cw + cL * sw;
                    const double c2 = cR * cw - sR * sw, s2 = sR * cw + cR * sw;
                    cL = c1; sL = s1; cR = c2; sR = s2;
                }
            }
        }
        dsp::Rng rng(12345);
        dsp::Biquad lp[4];
        for (int k = 0; k < 4; ++k) lp[k].set(dsp::Biquad::Type::LowPass, kSr, 3000.0, k % 2 ? 1.3066 : 0.5412);
        for (std::size_t i = 0; i < n; ++i) {
            const long t = static_cast<long>(i) % 6000;
            const double env = t < 240 ? 0.5 - 0.5 * std::cos(dsp::kPi * t / 240.0) : std::exp(-(t - 240) / 2400.0);
            const float w = rng.bipolar();
            const float yl = lp[1].process(lp[0].process(w));
            const float yr = lp[3].process(lp[2].process(0.7f * w + 0.3f * rng.bipolar()));
            x.l[i] += static_cast<float>(0.5 * env) * yl;
            x.r[i] += static_cast<float>(0.5 * env) * yr;
        }
        return x;
    }();
    return s;
}

// Sidechain key for the effects that need one (the vocoder's modulator): a "talking" signal repeating every
// 0.9 s - voiced 'a' (110 Hz pulses through formants), unvoiced 's' (noise 3-6 kHz; also around the step at
// 0.3 s, so the consonant parameters are audible there), voiced 'i', 100 ms of silence, voiced 'o' with breath.
// ~-20 dBFS, nothing above ~7 kHz.
bool keyed(const std::string& type) { return effectRequiresSidechain(type) || type.rfind("vocoder", 0) == 0; }
const std::vector<float>& keyInput() {
    static const std::vector<float> k = [] {
        const std::size_t n = static_cast<std::size_t>(9.5 * kSr);
        std::vector<float> y(n, 0.0f);
        struct Seg { double a, b; int kind; double f1, f2, f3; };  // kind 0 voiced, 1 unvoiced, 2 silent
        const Seg segs[] = {{0.0, 0.25, 0, 700, 1200, 2600}, {0.25, 0.47, 1, 0, 0, 0}, {0.47, 0.62, 0, 300, 2300, 3000},
                            {0.62, 0.72, 2, 0, 0, 0}, {0.72, 0.9, 0, 500, 900, 2500}};
        dsp::Rng rng(777);
        dsp::Biquad form[3], hiss[2], lp[2];
        for (int k = 0; k < 2; ++k) {
            hiss[k].set(dsp::Biquad::Type::BandPass, kSr, 4200.0, 1.2);
            lp[k].set(dsp::Biquad::Type::LowPass, kSr, 7000.0, k ? 1.3066 : 0.5412);
        }
        double phase = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            const double t = std::fmod(static_cast<double>(i) / kSr, 0.9);
            const Seg* s = &segs[0];
            for (const Seg& g : segs)
                if (t >= g.a && t < g.b) s = &g;
            const double edge = std::min(t - s->a, s->b - t);
            const double fade = std::clamp(edge / 0.005, 0.0, 1.0);
            if (i % 480 == 0 && s->kind == 0)
                for (int f = 0; f < 3; ++f) form[f].set(dsp::Biquad::Type::BandPass, kSr, f == 0 ? s->f1 : f == 1 ? s->f2 : s->f3, 6.0);
            phase += 110.0 / kSr;
            const float pulse = phase >= 1.0 ? (phase -= 1.0, 1.0f) : 0.0f;
            const float noise = rng.bipolar();
            float v = 0.0f;
            if (s->kind == 0) v = 1.2f * (form[0].process(pulse) + 0.6f * form[1].process(pulse) + 0.3f * form[2].process(pulse)) + 0.01f * noise;
            else if (s->kind == 1) v = 0.25f * hiss[1].process(hiss[0].process(noise));
            y[i] = static_cast<float>(fade) * lp[1].process(lp[0].process(v));
        }
        return y;
    }();
    return k;
}

// The convolver's impulse response: a synthetic stereo room (0.4 s of decaying noise), written once per run as
// a float WAV to the temp folder (removed at exit), so the tests do not depend on downloaded IR packs.
std::string convolverIr() {
    struct TempFile {
        std::string path;
        ~TempFile() {
            std::error_code ec;
            std::filesystem::remove(path, ec);
        }
    };
    static const TempFile file{[] {
        const auto n = static_cast<std::uint32_t>(0.4 * kSr);
        std::vector<float> frames(2 * static_cast<std::size_t>(n));
        dsp::Rng rng(4242);
        for (std::uint32_t i = 0; i < n; ++i)
            for (std::uint32_t c = 0; c < 2; ++c)
                frames[2 * i + c] = 0.5f * rng.bipolar() * std::pow(10.0f, -3.0f * static_cast<float>(i) / (0.35f * static_cast<float>(kSr)));
        std::vector<unsigned char> b;
        auto u32 = [&](std::uint32_t v) { for (int k = 0; k < 4; ++k) b.push_back(static_cast<unsigned char>((v >> (8 * k)) & 0xFF)); };
        auto u16 = [&](std::uint32_t v) { b.push_back(static_cast<unsigned char>(v & 0xFF)); b.push_back(static_cast<unsigned char>(v >> 8)); };
        auto tag = [&](const char* t) { b.insert(b.end(), t, t + 4); };
        const std::uint32_t data = n * 8;
        tag("RIFF"); u32(36 + data); tag("WAVE");
        tag("fmt "); u32(16); u16(3); u16(2); u32(48000); u32(48000 * 8); u16(8); u16(32);
        tag("data"); u32(data);
        for (float v : frames) { std::uint32_t u; std::memcpy(&u, &v, 4); u32(u); }
        const auto p = std::filesystem::temp_directory_path() / ("agentsound_test_param_jumps_ir_" + std::to_string(AS_TEST_PID) + ".wav");
        std::ofstream(p, std::ios::binary).write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
        return p.generic_string();
    }()};
    return file.path;
}

// ---------------------------------------------------------------------------------------------
// Module configurations

// The VA's modulation matrix for the tests: every source type (voice and global LFOs, free and tempo-synced,
// envelopes, velocity, random, a macro) on every kind of target, including the global hpf. Each routing's
// amount is an automatable 'mod.<id>.amount' parameter, so it is jump- and step-tested like any other.
json vaMods() {
    auto lfo = [](const char* shape, double hz, json extra = json::object()) {
        json s = {{"type", "lfo"}, {"shape", shape}, {"rateHz", hz}};
        for (auto it = extra.begin(); it != extra.end(); ++it) s[it.key()] = it.value();
        return s;
    };
    auto route = [](const char* id, const json& src, const char* target, double amount) {
        return json{{"id", id}, {"source", src}, {"target", target}, {"amount", amount}};
    };
    const json env = {{"type", "env"}, {"attack", 0}, {"decay", 0.3}};
    return json::array({
        route("vib", lfo("sine", 5.5, {{"delay", 0.05}, {"fade", 0.1}}), "pitch", 15),
        route("wah", lfo("triangle", 3, {{"mode", "global"}}), "cutoff", 0.5),
        route("pwm", lfo("triangle", 0.7), "osc1.pw", 0.1),
        route("trem", lfo("sine", 0.5, {{"mode", "global"}}), "amp", -3),
        route("apan", lfo("sine", 0.5, {{"mode", "global"}}), "pan", 0.3),
        route("wob", json{{"type", "lfo"}, {"shape", "sine"}, {"rateBeats", 4}, {"mode", "global"}}, "cutoff", 0.3),
        route("penv", env, "pitch", 50),
        route("sweep", env, "osc2.pitch", 200),
        route("vel", {{"type", "velocity"}}, "cutoff", 0.5),
        route("rnd", {{"type", "random"}}, "pan", 0.2),
        route("mres", {{"type", "macro"}, {"index", 1}}, "resonance", 0.2),
        route("hp", {{"type", "macro"}, {"index", 1}}, "hpf", 1),
    });
}

// The target of the routing behind 'mod.<id>.amount' ("" for other params).
std::string vaModTarget(const std::string& param) {
    for (const auto& m : vaMods())
        if (param == "mod." + m["id"].get<std::string>() + ".amount") return m["target"].get<std::string>();
    return "";
}

// LFOs parked (slow ramp from -1) and envelopes held at full level: the routing amounts act as static
// offsets, so their step response can be measured against held renders.
json vaParked(json mods) {
    for (auto& m : mods) {
        json& s = m["source"];
        if (s["type"] == "lfo") {
            s.erase("rateBeats");
            s["shape"] = "ramp";
            s["rateHz"] = 0.01;
        } else if (s["type"] == "env") {
            s["decay"] = 0.05;
            s["sustain"] = 1;
        }
    }
    return mods;
}

// Base configuration per module: everything audible, so that every parameter matters.
json baseConfig(const std::string& type) {
    if (type == "va")  // two oscillators, sub, unison, the modulation matrix above; a dark patch (the ladder
                       // leaves almost nothing near 9 kHz), so even small clicks would stand out
        return {{"osc2.level", 0.6}, {"osc2.fine", 7}, {"sub.level", 0.3}, {"unison", 3}, {"cutoff", 900},
                {"filter.env", 1}, {"glide", 0.02}, {"macro1", 0.5}, {"mods", vaMods()}};
    if (type == "dx7") return {{"detune", 7}, {"modwheel", 0.2}};
    if (type == "sampler") return {{"cutoff", 3000}, {"samples", {{"file", "soundfonts/GeneralUser-GS.sf2"}, {"sample", "StrLoop - C3"}, {"loop", "forward"}, {"pan", 0.5}}}};
    if (type == "stack")  // a dx7 layer with a chorus insert + the sampler strings an octave up (every kind of stack param)
        return json::parse(R"({"modwheel": 0.2, "layers": [
            {"id": "a", "instrument": {"type": "dx7", "params": {"detune": 7}}, "fx": [{"type": "chorus", "params": {"mode": "custom"}}]},
            {"id": "b", "instrument": {"type": "sampler", "params": {"cutoff": 3000, "samples": {"file": "soundfonts/GeneralUser-GS.sf2",
             "sample": "StrLoop - C3", "loop": "forward", "pan": 0.5}}}, "transpose": 12, "level": -6}]})");
    if (type == "chorus") return {{"mode", "custom"}};
    if (type == "ducker") return {{"mode", "tempo"}, {"attack", 4}};  // gentle duck onsets: only jump clicks count
    if (type == "filter") return {{"cutoff", 1500}, {"resonance", 0.3}};
    if (type == "delay") return {{"sync", false}, {"timems", 40}};    // echoes overlap the dry signal at once
    if (type == "vocoder:lpc") return {{"mode", "lpc"}};               // (the vocoder's second mode, keyed like it)
    if (type == "convolver") return {{"ir", convolverIr()}, {"mix", 0.5}, {"lowcut", 120}, {"highcut", 12000}};
    return json::object();
}

// Extra settings that make one parameter matter (e.g. a bell's q needs a bell gain).
json paramContext(const std::string& type, const std::string& p) {
    if (type == "va") {
        if (p == "osc1.pw" || p == "mod.pwm.amount") return {{"osc1.wave", "square"}};
        if (p == "osc2.pw") return {{"osc2.wave", "square"}};
        if (p == "noise.stereo") return {{"noise.level", 0.3}};
        if (p == "fm") return {{"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"osc2.semi", 12}};
        if (p.rfind("macro", 0) == 0 && p != "macro1") {  // (macro1 already drives resonance and hpf)
            json mods = vaMods();
            mods.push_back({{"source", {{"type", "macro"}, {"index", std::stoi(p.substr(5))}}}, {"target", "cutoff"},
                            {"amount", 2}});
            return {{"mods", mods}};
        }
    } else if (type == "stack") {
        // the dx7 layer's own params are measured dry (through the layer's chorus, delay-line smearing slows the response)
        if (p.rfind("layers.a.", 0) == 0 && p.rfind("layers.a.fx.", 0) != 0) return {{"layers.a.fx.0.mix", 0}};
    } else if (type == "eq") {
        if (p == "hp.q") return {{"hp.freq", 300}};
        if (p == "lp.q") return {{"lp.freq", 3000}};
        for (const char* band : {"low", "peak1", "peak2", "peak3", "high"}) {
            const std::string b = band;
            if (p == b + ".freq" || p == b + ".q") return {{b + ".gain", 9}};
        }
    } else if (type == "filter") {
        if (p == "cutoff") return {{"cutoff", 20000}};
    } else if (type == "phaser" || type == "tremolo") {
        if (p == "beats") return {{"sync", true}};
    } else if (type == "delay") {
        if (p == "time") return {{"sync", true}, {"time", 0.125}};
        if (p == "sync") return {{"time", 0.125}};
        // the echo filters themselves (with feedback, echoes filtered before the step keep coming back)
        if (p == "highcut" || p == "lowcut") return {{"feedback", 0}};
    }
    return json::object();
}

json merged(json a, const json& b) {
    for (auto it = b.begin(); it != b.end(); ++it) a[it.key()] = it.value();
    return a;
}

// ---------------------------------------------------------------------------------------------
// Detector calibration: a gain effect with an unsmoothed / one-pole / two-pole gain ("test.raw",
// "test.onepole", "test.twopole"), so the test can prove it flags a real click and passes a good
// smoother.

class TestGain final : public Effect {
public:
    explicit TestGain(int mode) : mode_(mode), params_({num("gain", -60, 12, 0, "dB", "test gain")}) {}
    void configure(const json& p) override { params_.configure(p, "testgain"); }
    void prepare(const RenderContext& ctx) override {
        c1_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.005 * ctx.sampleRate)));  // one-pole 5 ms (old engine)
        c2_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.0015 * ctx.sampleRate))); // two-pole 1.5 ms (new engine)
        a_ = g_ = dsp::dbToGain(params_.get(0));
    }
    bool setParam(std::string_view name, float value) override { return params_.set(name, value); }
    void process(float* l, float* r, int frames, const float*, const float*) override {
        const float t = dsp::dbToGain(params_.get(0));
        for (int i = 0; i < frames; ++i) {
            if (mode_ == 0) g_ = t;
            else if (mode_ == 1) g_ += (t - g_) * c1_;
            else { a_ += (t - a_) * c2_; g_ += (a_ - g_) * c2_; }
            l[i] *= g_;
            r[i] *= g_;
        }
    }
    const std::vector<ParamSpec>& paramSpecs() const override { return params_.specs(); }

private:
    int mode_;
    Params params_;
    float c1_{1.0f}, c2_{1.0f}, a_{1.0f}, g_{1.0f};
};

std::unique_ptr<Effect> makeEffect(const std::string& type) {
    if (type == "test.raw") return std::make_unique<TestGain>(0);
    if (type == "test.onepole") return std::make_unique<TestGain>(1);
    if (type == "test.twopole") return std::make_unique<TestGain>(2);
    if (type == "vocoder:lpc") return createEffect("vocoder");
    return createEffect(type);
}

// ---------------------------------------------------------------------------------------------
// Host

RenderContext context(double startBeat = 0.0) {
    RenderContext ctx;
    ctx.sampleRate = kSr;
    ctx.bpm = kBpm;
    ctx.seed = 7;
    ctx.assetDir = "assets";
    ctx.startBeat = startBeat;
    ctx.maxBlock = kBlock;
    return ctx;
}

// Renders `length` samples in 32-sample blocks; notes and parameter sets apply at block starts.
// Effects process fxInput() from sample `inputOffset`, silent before input sample `silentUntil`.
Stereo render(bool instrument, const std::string& type, const json& config, const std::vector<Note>& notes,
              std::vector<Set> sets, long length, double startBeat = 0.0, long inputOffset = 0, long silentUntil = 0) {
    std::unique_ptr<Instrument> inst;
    std::unique_ptr<Effect> fx;
    const RenderContext ctx = context(startBeat);
    if (instrument) {
        inst = createInstrument(type);
        inst->configure(config);
        inst->prepare(ctx);
    } else {
        fx = makeEffect(type);
        fx->configure(config);
        fx->prepare(ctx);
    }
    std::stable_sort(sets.begin(), sets.end(), [](const Set& a, const Set& b) { return a.at < b.at; });
    struct Ev { long at; bool on; int id; int pitch; float vel; };
    std::vector<Ev> evs;
    for (std::size_t i = 0; i < notes.size(); ++i) {
        evs.push_back({notes[i].on, true, static_cast<int>(i), notes[i].pitch, notes[i].vel});
        evs.push_back({notes[i].off, false, static_cast<int>(i), notes[i].pitch, 0.0f});
    }
    std::stable_sort(evs.begin(), evs.end(), [](const Ev& a, const Ev& b) {
        if (a.at != b.at) return a.at < b.at;
        return !a.on && b.on;
    });
    Stereo out(static_cast<std::size_t>(length));
    const Stereo& in = fxInput();
    const bool withKey = !instrument && keyed(type);
    std::vector<float> key(withKey ? static_cast<std::size_t>(kBlock) : 0);
    std::size_t ei = 0, si = 0;
    for (long pos = 0; pos < length;) {
        long end = std::min(length, (pos / kBlock + 1) * kBlock);
        if (pos % kBlock == 0) {
            for (; si < sets.size() && sets[si].at <= pos; ++si) {
                const bool ok = inst ? inst->setParam(sets[si].name, sets[si].value) : fx->setParam(sets[si].name, sets[si].value);
                if (!ok) check(false, type + ": setParam(" + sets[si].name + ") refused");
            }
        }
        float* L = out.l.data() + pos;
        float* R = out.r.data() + pos;
        if (inst) {  // sample-accurate notes (blocks split at events, like the renderer)
            for (; ei < evs.size() && evs[ei].at <= pos; ++ei) {
                if (evs[ei].on) inst->noteOn(evs[ei].id, evs[ei].pitch, evs[ei].vel);
                else inst->noteOff(evs[ei].id);
            }
            if (ei < evs.size()) end = std::min(end, evs[ei].at);
            inst->process(L, R, static_cast<int>(end - pos));
        } else {
            const auto src = static_cast<std::ptrdiff_t>(inputOffset + pos);
            const int n = static_cast<int>(end - pos);
            std::copy(in.l.begin() + src, in.l.begin() + src + n, L);
            std::copy(in.r.begin() + src, in.r.begin() + src + n, R);
            for (long k = 0; k < n && src + k < silentUntil; ++k) L[k] = R[k] = 0.0f;
            if (withKey) {  // the key signal runs in step with the input (same offset, same silence)
                for (int k = 0; k < n; ++k)
                    key[static_cast<std::size_t>(k)] = src + k < silentUntil ? 0.0f : keyInput()[static_cast<std::size_t>(src + k)];
                fx->process(L, R, n, key.data(), key.data());
            } else {
                fx->process(L, R, n, nullptr, nullptr);
            }
        }
        pos = end;
    }
    return out;
}

bool finite(const Stereo& s) {
    for (std::size_t i = 0; i < s.size(); ++i)
        if (!std::isfinite(s.l[i]) || !std::isfinite(s.r[i])) return false;
    return true;
}

// ---------------------------------------------------------------------------------------------
// 1. Click analysis

// Prefix sums of the energy above ~9 kHz (both channels).
std::vector<double> hfPrefix(const Stereo& s) {
    std::vector<double> p(s.size() + 1, 0.0);
    dsp::Biquad hp[4];
    for (int k = 0; k < 4; ++k) hp[k].set(dsp::Biquad::Type::HighPass, kSr, 9000.0, k % 2 ? 1.3066 : 0.5412);
    for (std::size_t i = 0; i < s.size(); ++i) {
        const double a = hp[1].process(hp[0].process(s.l[i]));
        const double b = hp[3].process(hp[2].process(s.r[i]));
        p[i + 1] = p[i] + a * a + b * b;
    }
    return p;
}
double winE(const std::vector<double>& p, long a) {
    a = std::clamp<long>(a, 0, static_cast<long>(p.size()) - 1 - kWin);
    return p[static_cast<std::size_t>(a + kWin)] - p[static_cast<std::size_t>(a)];
}
double meanWindowEnergy(const Stereo& s) {
    double e = 0.0;
    for (std::size_t i = 0; i < s.size(); ++i) e += double(s.l[i]) * s.l[i] + double(s.r[i]) * s.r[i];
    return e / std::max<double>(1.0, static_cast<double>(s.size()) / kWin);
}
double median(std::vector<double> v) {
    if (v.empty()) return 0.0;
    std::nth_element(v.begin(), v.begin() + static_cast<std::ptrdiff_t>(v.size() / 2), v.end());
    return v[v.size() / 2];
}
// Max window energy in the span a jump at j can affect ([-1, +8] ms: covers look-ahead latency).
double spikeE(const std::vector<double>& p, long j) {
    double m = 0.0;
    for (long a = j - 48; a <= j + 8 * 48; a += 24) m = std::max(m, winE(p, a));
    return m;
}

struct ClickResult {
    double ratio{0.0};
    float from{0.0f}, to{0.0f};
    bool finite{true};
};

bool gDiag = false;  // "test_param_jumps <type> <param>": per-jump details for one parameter
// The DX7 ROM banks are not distributed (assets/dx7/README.md): without them the dx7 and stack (a dx7 layer) cases skip.
bool needsDx7Banks(const std::string& type) { return (type == "dx7" || type == "stack") && !as::dx7BanksInstalled("assets"); }

ClickResult clickTest(bool instrument, const std::string& type, const json& config, const std::vector<Note>& notes,
                      const ParamSpec& p, long length, dsp::Rng& rng) {
    // min, max, default, random: an order that contains all 12 ordered pairs
    static const int kOrder[kJumps + 1] = {0, 1, 2, 3, 0, 2, 0, 3, 2, 1, 3, 1, 0};
    std::vector<float> v;
    for (int sym : kOrder)
        v.push_back(sym == 0 ? p.min : sym == 1 ? p.max : sym == 2 ? p.def : p.min + (p.max - p.min) * rng.uniform());
    std::vector<Set> sets{{kFirstJump - 2 * kSeg, p.name, v[0]}};
    for (int k = 1; k <= kJumps; ++k) sets.push_back({kFirstJump + (k - 1) * kSeg, p.name, v[static_cast<std::size_t>(k)]});
    const Stereo jumped = render(instrument, type, config, notes, sets, length);
    const auto pj = hfPrefix(jumped);
    std::map<float, std::vector<double>> held;  // renders with the parameter held at each value
    double level = meanWindowEnergy(jumped);
    for (float x : v) {
        if (held.count(x)) continue;
        const Stereo h = render(instrument, type, merged(config, {{p.name, x}}), notes, {}, length);
        held[x] = hfPrefix(h);
        level = std::max(level, meanWindowEnergy(h));
    }
    const double floorE = 1e-7 * level + 1e-14;  // -70 dB re the signal: inaudible
    ClickResult r;
    r.finite = finite(jumped);
    for (int k = 1; k <= kJumps; ++k) {
        const long j = sets[static_cast<std::size_t>(k)].at;
        const float from = v[static_cast<std::size_t>(k - 1)], to = v[static_cast<std::size_t>(k)];
        std::vector<double> before, after;
        for (long a = j - 20 * 48; a <= j - 3 * 48; a += 48) before.push_back(winE(pj, a));
        for (long a = j + 20 * 48; a <= j + 47 * 48 - kWin; a += 48) after.push_back(winE(pj, a));
        double base = std::max({spikeE(held[from], j), spikeE(held[to], j), median(before), median(after), floorE});
        double ratio = spikeE(pj, j) / base;
        // A fast glide of a continuous parameter passes through the values in between, and some of
        // them can be brighter than both ends (a bell swept through the band where the signal has its
        // top end). Those states are the sound of the sweep, not a click: compare with them too.
        double path = 0.0;
        if (ratio > kClickLimit && p.choices.empty()) {
            const bool logScale = p.unit == "Hz" && from > 0.0f && to > 0.0f;
            for (int m = 1; m < 8; ++m) {
                const float x = logScale ? from * std::pow(to / from, m / 8.0f) : from + (to - from) * (m / 8.0f);
                if (!held.count(x)) held[x] = hfPrefix(render(instrument, type, merged(config, {{p.name, x}}), notes, {}, length));
                path = std::max(path, spikeE(held[x], j));
            }
            base = std::max(base, path);
            ratio = spikeE(pj, j) / base;
        }
        if (gDiag) {
            long where = j - 48;
            for (long a = j - 48; a <= j + 8 * 48; a += 24)
                if (winE(pj, a) > winE(pj, where)) where = a;
            std::printf("    jump %2d %9.4g -> %-9.4g ratio %7.2f  spike %.3g at %+.1f ms | held %.3g / %.3g, path %.3g, "
                        "around %.3g / %.3g\n", k, from, to, ratio, spikeE(pj, j), (where - j) / 48.0, spikeE(held[from], j),
                        spikeE(held[to], j), path, median(before), median(after));
        }
        if (ratio > r.ratio) { r.ratio = ratio; r.from = from; r.to = to; }
    }
    return r;
}

// ---------------------------------------------------------------------------------------------
// 2. Step response

struct Response {
    bool measured{false};
    double latencyMs{0.0}, riseMs{0.0};
    std::string why;  // when not measured
};

// Waveform projection: p(t) = <S - A, B - A> / |B - A|^2 in 1 ms windows (0.5 ms hop).
Response waveResponse(const Stereo& A, const Stereo& B, const Stereo& S, long at) {
    const long end = std::min<long>(static_cast<long>(S.size()) - kWin, at + static_cast<long>(0.12 * kSr));
    struct W { long c; double num, den, res; };
    std::vector<W> w;
    double meanDen = 0.0, sig = 0.0;
    for (long a = at - 24; a < end; a += 24) {
        W x{a + kWin / 2, 0.0, 0.0, 0.0};
        for (long i = a; i < a + kWin; ++i) {
            const auto k = static_cast<std::size_t>(i);
            for (int ch = 0; ch < 2; ++ch) {
                const double sa = ch ? A.r[k] : A.l[k], sb = ch ? B.r[k] : B.l[k], ss = ch ? S.r[k] : S.l[k];
                x.num += (ss - sa) * (sb - sa);
                x.den += (sb - sa) * (sb - sa);
                x.res += (ss - sb) * (ss - sb);
                sig += sb * sb;
            }
        }
        w.push_back(x);
        meanDen += x.den;
    }
    meanDen /= std::max<std::size_t>(1, w.size());
    sig /= std::max<std::size_t>(1, w.size());
    Response r;
    if (meanDen <= 1e-6 * sig || meanDen <= 1e-14) {
        r.why = "no audible effect here";
        return r;
    }
    double num = 0.0, den = 0.0, res = 0.0;  // the last 40 ms must have converged to B
    for (const W& x : w)
        if (x.c >= end - static_cast<long>(0.04 * kSr)) { num += x.num; den += x.den; res += x.res; }
    const double residual = den > 0.0 ? res / den : 1e9, pEnd = den > 0.0 ? num / den : 0.0;
    if (residual > 0.05 || pEnd < 0.9 || pEnd > 1.1) {
        r.why = fmt("does not settle onto the held render (residual %.2f)", residual);
        return r;
    }
    double t10 = -1.0, t90 = -1.0, p = 0.0;
    for (const W& x : w) {
        if (x.den > 0.05 * meanDen) p = x.num / x.den;
        const double t = (x.c - at) * 1000.0 / kSr;
        if (t10 < 0.0 && p >= 0.1) t10 = t;
        if (t90 < 0.0 && p >= 0.9) t90 = t;
    }
    if (t10 < 0.0 || t90 < 0.0) {
        r.why = "no 10-90 % transition found";
        return r;
    }
    r.measured = true;
    r.latencyMs = std::max(0.0, t10);
    r.riseMs = t90 - t10;
    return r;
}

// Pitch tracker for pitch parameters (single sine-like note): semitones at each upward zero crossing.
Response pitchResponse(const Stereo& S, long at) {
    std::vector<double> tz;
    for (std::size_t i = 1; i < S.size(); ++i)
        if (S.l[i - 1] < 0.0f && S.l[i] >= 0.0f) tz.push_back(static_cast<double>(i - 1) + S.l[i - 1] / (S.l[i - 1] - S.l[i]));
    std::vector<std::pair<double, double>> st;  // (time, semitones)
    for (std::size_t k = 1; k < tz.size(); ++k)
        st.push_back({0.5 * (tz[k] + tz[k - 1]), 12.0 * std::log2(kSr / (tz[k] - tz[k - 1]))});
    auto medianIn = [&](double a, double b) {
        std::vector<double> v;
        for (const auto& [t, s] : st)
            if (t >= a && t < b) v.push_back(s);
        return median(v);
    };
    const double sA = medianIn(at - 0.05 * kSr, at), sB = medianIn(at + 0.06 * kSr, at + 0.1 * kSr);
    Response r;
    if (std::fabs(sB - sA) < 0.05) { r.why = "no pitch change"; return r; }
    double t10 = -1.0, t90 = -1.0;
    for (const auto& [t, s] : st) {
        if (t < at) continue;
        const double p = (s - sA) / (sB - sA), ms = (t - at) * 1000.0 / kSr;
        if (t10 < 0.0 && p >= 0.1) t10 = ms;
        if (t90 < 0.0 && p >= 0.9) t90 = ms;
    }
    if (t10 < 0.0 || t90 < 0.0) { r.why = "no 10-90 % transition found"; return r; }
    r.measured = true;
    r.latencyMs = t10;
    r.riseMs = t90 - t10;
    return r;
}

// Pitch parameters measured with the pitch tracker: config for a single clean note.
bool pitchSetup(const std::string& type, const std::string& p, json& config, int& note) {
    const std::string modTarget = type == "va" ? vaModTarget(p) : "";
    if (type == "va" && (p == "osc1.semi" || p == "osc1.fine" || p == "osc2.semi" || p == "osc2.fine" ||
                         p == "pitchbend" || modTarget == "pitch" || modTarget == "osc1.pitch" || modTarget == "osc2.pitch")) {
        const bool o2 = p.rfind("osc2", 0) == 0 || modTarget == "osc2.pitch";
        config = {{"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"osc1.level", o2 ? 0 : 1}, {"osc2.level", o2 ? 1 : 0},
                  {"drift.pitch", 0}, {"drift.cutoff", 0}, {"cutoff", 20000}, {"filter.env", 0}, {"filter.keytrack", 0},
                  {"resonance", 0}, {"filter.drive", 0}, {"amp.attack", 0.001}, {"macro1", 0.5}};
        if (!modTarget.empty()) config["mods"] = vaParked(vaMods());  // (the amount params exist with the matrix)
        note = 93;  // A6: short periods, fine time resolution
        return true;
    }
    if (type == "dx7" && p == "pitchbend") {
        config = {{"voice", "FLUTE 1"}};
        note = 84;
        return true;
    }
    if (type == "stack" && (p == "pitchbend" || (p.rfind("layers.", 0) == 0 && p.size() > 5 && p.substr(p.size() - 5) == ".fine"))) {
        // one clean looped sine layer, named like the parameter's layer
        const std::string id = p == "pitchbend" ? "a" : p.substr(7, p.size() - 12);
        config = json::parse(R"({"layers": [{"instrument": {"type": "sampler", "params": {"samples": {"file": "soundfonts/GeneralUser-GS.sf2",
                                 "sample": "Sine-750Hz", "loop": "forward"}}}}]})");
        config["layers"][0]["id"] = id;
        note = 84;
        return true;
    }
    if ((type == "sf2" || type == "sampler") && p == "pitchbend") {  // a clean looped sine
        config = type == "sf2" ? json{{"preset", "Sine Wave"}}
                               : json{{"samples", {{"file", "soundfonts/GeneralUser-GS.sf2"}, {"sample", "Sine-750Hz"}, {"loop", "forward"}}}};
        note = 84;
        return true;
    }
    return false;
}

// Parameters that may respond slower than kRiseLimitMs, or whose response is not a waveform glide
// that can be measured against held renders. Every entry says why; everything else must be fast.
const char* const kNextNote = "applies to the next note";
const char* const kNextHit = "latched per hit: applies to the next hit";
const char* const kEnvTime = "time constant of the running envelope stage";
const char* const kLfoRate = "LFO rate: phase-continuous speed change";
const char* const kLfoPhase = "LFO phase / period change (the waveform stays shifted)";
const char* const kPhase = "detunes free-running oscillators (phase-dependent; same ~6 ms smoother)";
const char* const kDelayTime = "moves a delay time: glides slowly on purpose (a fast change is a pitch jump)";
const char* const kTail = "shapes the reverb tail (loop coefficients ramp in ~7 ms; the tail keeps its history)";
const char* const kDetector = "acts through the attack/release of the gain computer";
const char* const kTiming = "envelope / grid timing: applies to the next duck or hit";
const char* const kLoop = "feedback amount: the pitch-shifted halo builds up / fades through the reverb loop";
const char* const kVocEnv = "time constant of the band envelope followers / LPC model smoothing (acts on the next changes)";
const char* const kVocGate = "threshold: acts only where the modulator level crosses it (the test key is far above it)";
const char* const kVocHold = "freeze: keeps the spectrum captured at the switch (a render held from the start has none)";
const char* const kPedal = "sustain pedal: a step that holds the next note-offs / releases the held notes at pedal-up "
                           "(their release envelopes); no level of its own";

const std::map<std::string, std::string>& slowAllowed() {
    static const std::map<std::string, std::string> m = {
        {"va.osc2.sync", "hard sync switches at the next oscillator cycle (band-limited); a timbre, not a level"},
        {"va.osc.retrig", kNextNote},
        {"va.unison.detune", kPhase},
        {"va.drift.pitch", "depth of a random pitch drift (phase-dependent)"},
        {"va.amp.attack", kEnvTime},
        {"va.amp.decay", kEnvTime},
        {"va.amp.release", kEnvTime},
        {"va.amp.velocity", kNextNote},
        {"va.fenv.attack", kEnvTime},
        {"va.fenv.decay", kEnvTime},
        {"va.fenv.release", kEnvTime},
        {"va.glide", "portamento time constant"},
        {"dx7.modwheel", "depth of the patch LFO (vibrato, phase-dependent)"},
        {"dx7.velsens", kNextNote},
        {"dx7.attack", kNextNote},
        {"dx7.decay", kNextNote},
        {"dx7.release", "applies to the next note-off (the release rates of that note)"},
        {"sampler.start", kNextNote},
        {"sampler.pedal", kPedal},
        {"sampler.legatotime", "mono='legato' only: applies to the next legato transition"},
        {"sampler.legatooffset", "mono='legato' only: applies to the next legato transition"},
        {"sampler.glide", "mono='legato' only: portamento of the next legato transition"},
        {"sampler.vibrato", "depth of a pitch LFO (phase-dependent; smoothed ~5 ms)"},
        {"sampler.vibratorate", kLfoRate},
        {"sampler.bendfollow", "latched: applies to the next note (how much of the bend it follows)"},
        {"sampler.harmonic", "the isolated partial is level-matched by envelope followers (~12 ms) and fades in over "
                             "15 ms when it starts cold"},
        {"sampler.harmonicnum", "which partial 'harmonic' isolates: no effect while harmonic is 0 (the default)"},
        {"sampler.harmonicfocus", "Q of the partial's band-passes: no effect while harmonic is 0 (the default)"},
        {"sf2.pedal", kPedal},
        {"drums.velocity", kNextHit},
        {"drums.humanize", kNextHit},
        {"drums.crash.level", "the stereo-width part passes the ~6 ms decorrelator (mid part: ~5 ms)"},
        {"eq.hp.q", "resonant filter: settles at its own ring time (Q / pi f)"},
        {"eq.peak1.q", "resonant filter: settles at its own ring time (Q / pi f)"},
        {"compressor.threshold", kDetector},
        {"compressor.ratio", kDetector},
        {"compressor.knee", kDetector},
        {"compressor.attack", kDetector},
        {"compressor.release", kDetector},
        {"compressor.keyhp", kDetector},
        {"compressor.range", "caps the reduction of the gain computer: no effect unless the reduction exceeds it (the default is the top)"},
        {"ducker.threshold", "key mode only (the test runs the tempo grid)"},
        {"ducker.attack", kTiming},
        {"ducker.hold", kTiming},
        {"ducker.release", kTiming},
        {"ducker.rate", kTiming},
        {"ducker.offset", kTiming},
        {"limiter.gain", "drives the limiter: its own gain reduction and release shape the response"},
        {"limiter.release", kDetector},
        {"bitcrush.downsample", "sample-and-hold rate: the hold grid shifts (phase-dependent)"},
        {"chorus.rate", kLfoRate},
        {"chorus.depth", kDelayTime},
        {"chorus.delay", kDelayTime},
        {"chorus.spread", kDelayTime},
        {"chorus.feedback", "acts through the feedback path: audible after the delay time"},
        {"flanger.rate", kLfoRate},
        {"flanger.depth", kDelayTime},
        {"flanger.delay", kDelayTime},
        {"flanger.stereo", kDelayTime},
        {"phaser.rate", kLfoRate},
        {"phaser.sync", kLfoPhase},
        {"delay.sync", kDelayTime},
        {"delay.time", kDelayTime},
        {"delay.timems", kDelayTime},
        {"delay.offset", kDelayTime},
        {"delay.feedback", "acts on the next repeat (through the echo path)"},
        {"delay.wow", kDelayTime},
        {"delay.flutter", kDelayTime},
        {"delay.duck", "acts through the ducking envelope (10 ms down, 150 ms up)"},
        {"reverb.decay", kTail},
        {"reverb.lowmult", kTail},
        {"reverb.lowxover", kTail},
        {"reverb.damping", kTail},
        {"reverb.predelay", kDelayTime},
        {"reverb.predelaybeats", kDelayTime},
        {"reverb.modrate", "delay-line modulation rate (phase-continuous)"},
        {"reverb.moddepth", kDelayTime},
        {"gatedreverb.threshold", kTiming},
        {"gatedreverb.hold", kTiming},
        {"gatedreverb.release", kTiming},
        {"gatedreverb.flat", kTiming},
        {"gatedreverb.predelay", kDelayTime},
        {"gatedreverb.decay", kTail},
        {"gatedreverb.tone", kTail},
        {"tremolo.rate", kLfoRate},
        {"tremolo.sync", kLfoPhase},
        {"ensemble.rate", kLfoRate},
        {"ensemble.shimmerrate", kLfoRate},
        {"ensemble.depth", kDelayTime},
        {"ensemble.shimmer", kDelayTime},
        {"wah.sens", "auto mode only (the test runs the pedal mode)"},
        {"wah.attack", "auto mode only (the test runs the pedal mode)"},
        {"wah.release", "auto mode only (the test runs the pedal mode)"},
        {"vowel.resonance", "narrower formants build up and ring out at their own ring time (1 / pi B, ~8 ms at B = 40 Hz)"},
        {"microshift.detune", "pitch-shift amount: the voices drift in phase against a held render (a pitch change, no level step)"},
        {"microshift.delay", kDelayTime},
        {"shimmer.decay", kTail},
        {"shimmer.damping", kTail},
        {"shimmer.shimmer", kLoop},
        {"shimmer.fifth", kLoop},
        {"shimmer.lowcut", "also filters the shimmer feedback loop (the tail keeps its history)"},
        {"shimmer.predelay", kDelayTime},
        {"shimmer.modrate", "delay-line modulation rate (phase-continuous)"},
        {"shimmer.moddepth", kDelayTime},
        {"tape.wow", kDelayTime},
        {"tape.flutter", kDelayTime},
        {"exciter.freq", "the harmonic generator's level detector (40 ms peak release) re-settles on the new band"},
        {"vocoder.attack", kVocEnv},
        {"vocoder.release", kVocEnv},
        {"vocoder.gate", kVocGate},
        {"vocoder.hold", kVocHold},
        {"vocoder:lpc.attack", kVocEnv},
        {"vocoder:lpc.release", kVocEnv},
        {"vocoder:lpc.gate", kVocGate},
        {"vocoder:lpc.hold", kVocHold},
        {"vocoder:lpc.bandwidth", "classic mode only (no effect in lpc mode)"},
        {"vocoder:lpc.width", "classic mode only (no effect in lpc mode)"},
        {"convolver.predelay", kDelayTime},
    };
    return m;
}
const char* allowedReason(const std::string& type, const std::string& p) {
    if (type == "stack") {  // the stack's params act like the child's / the layer effect's they drive
        if (p == "pedal") return kPedal;
        if (p == "modwheel") return allowedReason("dx7", "modwheel");
        if (p.rfind("layers.", 0) == 0) {
            const std::string rest = p.substr(7), id = rest.substr(0, rest.find('.')), sub = rest.substr(rest.find('.') + 1);
            if (sub.rfind("fx.0.", 0) == 0) return allowedReason("chorus", sub.substr(5));
            return allowedReason(id == "a" ? "dx7" : "sampler", sub);
        }
    }
    const auto& m = slowAllowed();
    const auto it = m.find(type + "." + p);
    if (it != m.end()) return it->second.c_str();
    if (type == "drums" && p.find('.') != std::string::npos) {  // per-piece sound parameters
        const std::string field = p.substr(p.find('.') + 1);
        if (field != "level" && field != "pan" && field != "width") return kNextHit;
    }
    return nullptr;
}

void stepValues(const ParamSpec& p, float& a, float& b) {
    if (!p.choices.empty()) { a = p.min; b = p.max; return; }
    if (p.unit == "Hz" && p.min > 0.0f) {
        a = p.min * std::pow(p.max / p.min, 0.25f);
        b = p.min * std::pow(p.max / p.min, 0.75f);
    } else {
        a = p.min + 0.25f * (p.max - p.min);
        b = p.min + 0.75f * (p.max - p.min);
    }
}

Response stepTest(bool instrument, const std::string& type, const json& config, const ParamSpec& p) {
    float a, b;
    stepValues(p, a, b);
    // The step lands where the parameter is audible: drums 5 ms into a hit, the ducker in the release
    // of the duck on beat 1 (attack 4 ms + hold 10 ms).
    const long at = type == "drums" ? 11648 : type == "ducker" ? 25440 : blocks(0.3);
    const long len = type == "ducker" ? blocks(0.65) : blocks(0.45);
    json pc;
    int note = 0;
    if (pitchSetup(type, p.name, pc, note)) {
        const std::vector<Note> notes{{0, len, note, 0.8f}};
        const Stereo up = render(true, type, merged(pc, {{p.name, a}}), notes, {{at, p.name, b}}, len);
        const Stereo down = render(true, type, merged(pc, {{p.name, b}}), notes, {{at, p.name, a}}, len);
        Response r1 = pitchResponse(up, at), r2 = pitchResponse(down, at);
        if (!r1.measured) return r1;
        if (!r2.measured) return r2;
        r1.latencyMs = std::max(r1.latencyMs, r2.latencyMs);
        r1.riseMs = std::max(r1.riseMs, r2.riseMs);
        return r1;
    }
    // Instruments: held chord only (steady state); drums: the piece's hits; effects: fxInput.
    const std::vector<Note> notes = !instrument ? std::vector<Note>{}
                                    : type == "drums" ? drumNotes(p.name, len) : synthNotes(len, false);
    json c = config;
    if (type == "va") {  // matrix LFOs parked and envelopes held (vaParked): the routing amounts act as static
        c["mods"] = vaParked(c["mods"]);  // offsets; short decays: the chord sits on its sustain levels
        c["amp.decay"] = c["fenv.decay"] = 0.05;
    }
    const Stereo A = render(instrument, type, merged(c, {{p.name, a}}), notes, {}, len);
    const Stereo B = render(instrument, type, merged(c, {{p.name, b}}), notes, {}, len);
    const Stereo S = render(instrument, type, merged(c, {{p.name, a}}), notes, {{at, p.name, b}}, len);
    const Stereo S2 = render(instrument, type, merged(c, {{p.name, b}}), notes, {{at, p.name, a}}, len);
    Response r1 = waveResponse(A, B, S, at), r2 = waveResponse(B, A, S2, at);
    if (!r1.measured) return r1;
    if (!r2.measured) return r2;
    r1.latencyMs = std::max(r1.latencyMs, r2.latencyMs);
    r1.riseMs = std::max(r1.riseMs, r2.riseMs);
    return r1;
}

void testModule(bool instrument, const std::string& type, const std::string& only = "") {
    std::unique_ptr<Instrument> probeI;
    std::unique_ptr<Effect> probeF;
    if (instrument) {
        probeI = createInstrument(type);
        // (the va's matrix adds the 'mod.<id>.amount' params; a stack's params are its layers')
        if (type == "va" || type == "stack") probeI->configure(baseConfig(type));
    } else {
        probeF = makeEffect(type);
    }
    const std::vector<ParamSpec>& specs = instrument ? probeI->paramSpecs() : probeF->paramSpecs();
    const long length = kFirstJump + kJumps * kSeg + kSeg;
    dsp::Rng rng(dsp::hashString(type.c_str()));
    for (const ParamSpec& p : specs) {
        if (!p.automatable) continue;
        if (!only.empty() && p.name != only) {
            for (int k = 0; k < 3; ++k) rng.uniform();  // same random values as a full run
            continue;
        }
        const json config = merged(baseConfig(type), paramContext(type, p.name));
        const std::vector<Note> notes = !instrument ? std::vector<Note>{}
                                        : type == "drums" ? drumNotes(p.name, length) : synthNotes(length);
        const ClickResult c = clickTest(instrument, type, config, notes, p, length, rng);
        const Response r = stepTest(instrument, type, config, p);

        const char* reason = allowedReason(type, p.name);
        std::string resp;
        bool respOk;
        if (r.measured) {
            resp = fmt("%5.1f ms (+%.1f)", r.riseMs, r.latencyMs);
            respOk = r.riseMs <= kRiseLimitMs && r.latencyMs <= kLatencyLimitMs;
        } else {
            resp = "  n/a (" + r.why + ")";
            respOk = false;
        }
        if (!respOk && reason) {
            resp += std::string("  allowed: ") + reason;
            respOk = true;
        }
        const bool clickOk = c.finite && c.ratio <= kClickLimit;
        std::printf("  %-11s %-17s %7.2f  (%-9.4g -> %-9.4g) %s%s\n", type.c_str(), p.name.c_str(), c.ratio, c.from, c.to,
                    resp.c_str(), clickOk && respOk ? "" : (clickOk ? "   <<< response" : "   <<< CLICK"));
        ++gChecks;
        if (!clickOk || !respOk) ++gFail;
    }
}

void testCalibration() {
    std::printf("detector calibration (gain -60..12 dB jumping on the effect test signal)\n");
    ParamSpec gain = num("gain", -60, 12, 0, "dB", "test gain");
    const long length = kFirstJump + kJumps * kSeg + kSeg;
    double ratio[3];
    const char* names[3] = {"test.raw", "test.onepole", "test.twopole"};
    for (int m = 0; m < 3; ++m) {
        dsp::Rng rng(99);
        ratio[m] = clickTest(false, names[m], json::object(), {}, gain, length, rng).ratio;
    }
    check(ratio[0] > 10.0 * kClickLimit, fmt("an unsmoothed gain jump is flagged (ratio %.0f)", ratio[0]));
    check(ratio[2] <= kClickLimit, fmt("two-pole 1.5 ms smoothing is click-free (ratio %.2f; one-pole 5 ms: %.2f)", ratio[2], ratio[1]));
    const Response r = stepTest(false, "test.twopole", json::object(), gain);
    check(r.measured && std::fabs(r.riseMs - 5.0) < 1.0,
          fmt("response measurement: two-pole 1.5 ms reads %.1f ms 10-90 %% (theory 5.0)", r.riseMs));
}

// ---------------------------------------------------------------------------------------------
// 3. Tempo grid: a preview render starting at song beat 13.5 against the same span of a full render

struct PreviewCase {
    bool instrument;
    std::string type;
    json config;
    double warmup;  // seconds before comparing (effect state that depends on the input history)
    bool synced;    // tempo-synced: a render that ignored the song position would be off the grid
    bool silentBefore = false;  // effects: no input before the preview start (long reverb tails)
};

void testPreview(const PreviewCase& pc, double startBeat) {
    if (needsDx7Banks(pc.type)) {
        std::printf("  SKIP: %s preview case (%s)\n", pc.type.c_str(), as::kDx7NoBanksHint);
        return;
    }
    const long start = std::llround(startBeat * kSr * 60.0 / kBpm), span = blocks(1.5);
    // instruments: the same note at the preview start in both renders
    const std::vector<Note> fullNotes = pc.instrument ? std::vector<Note>{{start, start + span, 57, 0.8f}} : std::vector<Note>{};
    const std::vector<Note> prevNotes = pc.instrument ? std::vector<Note>{{0, span, 57, 0.8f}} : std::vector<Note>{};
    const long silent = pc.silentBefore ? start : 0;
    const Stereo full = render(pc.instrument, pc.type, pc.config, fullNotes, {}, start + span, 0.0, 0, silent);
    const Stereo prev = render(pc.instrument, pc.type, pc.config, prevNotes, {}, span, startBeat, start);
    // the same preview from a module that ignored the song position (proves the check can fail)
    const Stereo naive = render(pc.instrument, pc.type, pc.config, prevNotes, {}, span, 0.0, start);
    double diff = 0.0, naiveDiff = 0.0, peak = 0.0;
    for (long i = static_cast<long>(pc.warmup * kSr); i < span; ++i) {
        const auto k = static_cast<std::size_t>(i), f = static_cast<std::size_t>(start + i);
        diff = std::max({diff, double(std::fabs(prev.l[k] - full.l[f])), double(std::fabs(prev.r[k] - full.r[f]))});
        naiveDiff = std::max({naiveDiff, double(std::fabs(naive.l[k] - full.l[f])), double(std::fabs(naive.r[k] - full.r[f]))});
        peak = std::max({peak, double(std::fabs(full.l[f])), double(std::fabs(full.r[f]))});
    }
    const bool ok = peak > 1e-3 && diff <= 1e-4 * std::max(1.0, peak / 0.3) && (!pc.synced || naiveDiff > 0.05 * peak);
    check(ok, fmt("%-8s %-40s beat %.4g: preview vs full max diff %.1e (peak %.2f)%s", pc.type.c_str(),
                  pc.config.dump().substr(0, 40).c_str(), startBeat, diff, peak,
                  pc.synced ? fmt(", ignoring the song position: %.2f", naiveDiff).c_str() : ""));
}

void testTempoGrid() {
    std::printf("tempo grid: preview renders are phase-identical to full renders\n");
    const std::vector<PreviewCase> cases = {
        // (periods chosen so that beat 13.5 is mid-cycle: a render starting at phase 0 would be off)
        // va: global matrix LFOs on the song grid (tempo-synced gate + S&H) and on the song clock (free)
        {true, "va", {{"mods", json::array({
                          {{"source", {{"type", "lfo"}, {"shape", "square"}, {"rateBeats", 1.25}, {"mode", "global"}, {"unipolar", true}}},
                           {"target", "amp"}, {"amount", -60}},
                          {{"source", {{"type", "lfo"}, {"shape", "samplehold"}, {"rateBeats", 1.5}, {"mode", "global"}}},
                           {"target", "cutoff"}, {"amount", 2}}})}}, 0.0, true},
        {true, "va", {{"mods", json::array({
                          {{"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateHz", 3.3}, {"mode", "global"}}}, {"target", "pitch"}, {"amount", 40}},
                          {{"source", {{"type", "lfo"}, {"shape", "smoothrandom"}, {"rateHz", 1.7}, {"mode", "global"}}}, {"target", "pan"}, {"amount", 1}},
                          {{"source", {{"type", "lfo"}, {"shape", "triangle"}, {"rateHz", 0.37}, {"mode", "global"}}}, {"target", "hpf"}, {"amount", 3}}})}},
         0.02, false},
        // va: per-note sources (voice LFOs, envelopes, random) run from the note, on either render's grid
        {true, "va", {{"noise.level", 0.2}, {"noise.stereo", 1}, {"mods", json::array({
                          {{"source", {{"type", "lfo"}, {"shape", "samplehold"}, {"rateBeats", 0.75}}}, {"target", "cutoff"}, {"amount", 1.5}},
                          {{"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateHz", 5.1}, {"delay", 0.1}, {"fade", 0.2}}}, {"target", "pitch"}, {"amount", 30}},
                          {{"source", {{"type", "env"}, {"attack", 0.02}, {"decay", 0.4}, {"sustain", 0.3}}}, {"target", "cutoff"}, {"amount", 2}},
                          {{"source", {{"type", "random"}}}, {"target", "pan"}, {"amount", 0.5}}})}}, 0.0, false},
        // dx7: the global patch LFO and the free-running oscillator phases of new notes
        {true, "dx7", {{"voice", "E.PIANO 1"}, {"modwheel", 1}}, 0.0, false},
        {true, "dx7", {{"voice", "FLUTE 1"}, {"modwheel", 1}}, 0.0, false},
        // dx7: scaled envelopes, doubled voices and the voice high-passes following a downward bend
        {true, "dx7", {{"voice", "STRINGS 1"}, {"attack", 3}, {"decay", 2}, {"release", 4}, {"detune", 8}, {"pitchbend", -7}}, 0.0, false},
        // stack: a synced va gate layer + a dx7 layer through a synced tremolo (children and layer fx on the song grid)
        {true, "stack", json::parse(R"({"layers": [
             {"id": "gate", "instrument": {"type": "va", "params": {"mods": [{"source": {"type": "lfo", "shape": "square",
              "rateBeats": 1.25, "mode": "global", "unipolar": true}, "target": "amp", "amount": -60}]}}},
             {"id": "ep", "instrument": {"type": "dx7", "params": {"voice": "E.PIANO 1"}}, "transpose": 12,
              "fx": [{"type": "tremolo", "params": {"sync": true, "beats": 1.25, "shape": "square", "depth": 1}}]}]})"), 0.0, true},
        {false, "ducker", {{"mode", "tempo"}, {"rate", 0.75}, {"offset", 0.25}, {"release", 400}, {"depth", 12}}, 0.0, true},
        {false, "tremolo", {{"sync", true}, {"beats", 1.25}, {"shape", "square"}, {"depth", 1}, {"stereo", 90}}, 0.0, true},
        {false, "tremolo", {{"rate", 3.7}, {"depth", 0.8}}, 0.0, false},
        {false, "phaser", {{"sync", true}, {"beats", 3}, {"depth", 1}, {"feedback", 0.5}}, 0.3, true},
        {false, "phaser", {{"rate", 0.37}, {"depth", 1}}, 0.3, false},
        {false, "chorus", {{"mode", "II"}}, 0.1, false},
        {false, "flanger", {{"rate", 0.3}, {"feedback", 0.3}}, 0.3, false},
        {false, "delay", {{"sync", false}, {"timems", 30}, {"feedback", 0}, {"wow", 1}, {"flutter", 1}}, 0.1, false},
        {false, "delay", {{"mode", "pingpong"}, {"start", "right"}, {"sync", false}, {"timems", 30}, {"feedback", 0}, {"wow", 1}}, 0.1, false},
        {false, "ensemble", {{"depth", 1}, {"shimmer", 1}, {"rate", 0.37}}, 0.1, false},
        // reverbs: the delay-line modulation runs from the song start (input silent before the start)
        {false, "reverb", {{"mix", 0.5}, {"moddepth", 1}}, 0.0, false, true},
        {false, "gatedreverb", {{"mix", 0.5}}, 0.0, false, true},
        // premium: pitch-shifter grain grids, the shimmer loop, the tape transport and hiss run from the song start;
        // correlation-aligned splices (smooth / wide) and the shimmer tail depend on the input history
        {false, "microshift", {{"style", "classic"}, {"detune", 20}, {"delay", 10}}, 0.2, false},
        {false, "microshift", {{"style", "wide"}, {"detune", 20}}, 0.0, false, true},
        {false, "shimmer", {{"mix", 0.5}, {"shimmer", 1}, {"fifth", 0.5}, {"moddepth", 1}}, 0.0, false, true},
        {false, "tape", {{"wow", 1}, {"flutter", 1}, {"hiss", 0.5}, {"link", false}}, 0.1, false},
        {false, "exciter", {{"amount", 1}}, 0.3, false},
        {false, "dimension", {{"mode", 4}}, 0.05, false},
        // vocoder: envelopes / LPC model follow the key's history; the unvoiced noise is a hash of the song position
        {false, "vocoder", {{"unvoiced", 1}, {"width", 1}}, 0.5, false},
        {false, "vocoder:lpc", {{"mode", "lpc"}, {"unvoiced", 1}}, 0.5, false},
        // sampler: the instrument vibrato starts with the note, live dynamics (layers crossfaded, tone, range)
        {true, "sampler", {{"vibrato", 40}, {"dynamics", 0.4}, {"dynrange", 12}, {"layers", "dynamics"},
                           {"samples", json::array({{{"file", "soundfonts/GeneralUser-GS.sf2"}, {"sample", "StrLoop - C3"}, {"loop", "forward"}, {"velhi", 63}},
                                                    {{"file", "soundfonts/GeneralUser-GS.sf2"}, {"sample", "Sine-750Hz"}, {"loop", "forward"}, {"vello", 64}}})}},
         0.0, false},
        // convolver: FFT partitions on the absolute song grid (input silent before the start)
        {false, "convolver", {{"ir", convolverIr()}, {"mix", 0.5}, {"predelay", 15}, {"lowcut", 150}}, 0.0, false, true},
    };
    for (const auto& c : cases) testPreview(c, 13.5);
    // starts that are not on the control grids (partial first control period / 32-sample block)
    testPreview(cases[0], 13.5 + 5.0 / 24000.0);
    for (const auto& c : cases)
        if (c.type == "reverb" || c.type == "phaser" || c.type == "dx7" || c.type == "microshift" || c.type == "shimmer" ||
            c.type == "tape" || c.type == "dimension" || c.type == "convolver")
            testPreview(c, 13.5 + 7.0 / 24000.0);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc == 3) {  // diagnostics for one parameter
        gDiag = true;
        const std::string type = argv[1];
        const auto inst = instrumentTypes();
        testModule(std::find(inst.begin(), inst.end(), type) != inst.end(), type, argv[2]);
        return 0;
    }
    std::printf("test_param_jumps\n");
    std::printf("  jumps: worst HF ratio (limit %.1f); step: 10-90 %% rise (+ latency to 10 %%), limit %.0f ms\n",
                kClickLimit, kRiseLimitMs);
    testCalibration();
    std::printf("  module      param             ratio  (worst jump)             response\n");
    for (const auto& t : instrumentTypes()) {
        if (needsDx7Banks(t)) std::printf("  SKIP: %s (%s)\n", t.c_str(), as::kDx7NoBanksHint);
        else testModule(true, t);
    }
    for (const auto& t : effectTypes()) testModule(false, t);
    testModule(false, "vocoder:lpc");
    testTempoGrid();
    if (gFail) std::printf("FAILED: %d of %d check(s)\n", gFail, gChecks);
    else std::printf("all %d checks passed\n", gChecks);
    return gFail ? 1 : 0;
}
