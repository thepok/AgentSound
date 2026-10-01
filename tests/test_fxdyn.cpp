// Tests for the dynamics and tone effects (engine/fx/DynamicsFx.*).
// Deterministic; prints every check and returns nonzero on any failure.

#include "fx/DynamicsFx.h"

#include "core/Module.h"
#include "core/Params.h"
#include "dsp/Dsp.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

namespace {

using as::json;
constexpr double kFs = 48000.0;
constexpr double kPi = 3.14159265358979323846;
int g_failures = 0;
int g_checks = 0;

void check(bool ok, const std::string& what, double value = NAN) {
    ++g_checks;
    if (!ok) ++g_failures;
    if (std::isnan(value)) std::printf("[%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
    else std::printf("[%s] %s  (%.4f)\n", ok ? " ok " : "FAIL", what.c_str(), value);
}

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
    std::size_t size() const { return l.size(); }
};

std::unique_ptr<as::Effect> make(const std::string& type, const json& params = json::object(), double bpm = 120.0,
                                 double fs = kFs) {
    auto fx = as::createDynamicsEffect(type);
    if (!fx) return nullptr;
    fx->configure(params);
    as::RenderContext ctx;
    ctx.sampleRate = fs;
    ctx.bpm = bpm;
    ctx.seed = 1;
    fx->prepare(ctx);
    return fx;
}

// Processes `io` in place in blocks; `before(pos)` runs before every block (automation hook).
void run(as::Effect& fx, Stereo& io, const Stereo* key = nullptr, int block = 256,
         const std::function<void(std::size_t)>& before = {}) {
    for (std::size_t pos = 0; pos < io.size();) {
        const int n = static_cast<int>(std::min<std::size_t>(static_cast<std::size_t>(block), io.size() - pos));
        if (before) before(pos);
        fx.process(io.l.data() + pos, io.r.data() + pos, n, key ? key->l.data() + pos : nullptr,
                   key ? key->r.data() + pos : nullptr);
        pos += static_cast<std::size_t>(n);
    }
}

Stereo sine(std::size_t n, double freq, double amp, double phaseR = 0.0) {
    Stereo s(n);
    for (std::size_t i = 0; i < n; ++i) {
        const double t = static_cast<double>(i) / kFs;
        s.l[i] = static_cast<float>(amp * std::sin(2 * kPi * freq * t));
        s.r[i] = static_cast<float>(amp * std::sin(2 * kPi * freq * t + phaseR));
    }
    return s;
}

Stereo noise(std::size_t n, double amp, std::uint64_t seed) {
    as::dsp::Rng rng(seed);
    Stereo s(n);
    for (std::size_t i = 0; i < n; ++i) {
        s.l[i] = static_cast<float>(amp * rng.bipolar());
        s.r[i] = static_cast<float>(amp * rng.bipolar());
    }
    return s;
}

// Amplitude of the `freq` component over [start, start+len) (len should hold whole cycles).
double toneAmp(const std::vector<float>& x, std::size_t start, std::size_t len, double freq) {
    double re = 0, im = 0;
    for (std::size_t i = 0; i < len; ++i) {
        const double w = 2 * kPi * freq * static_cast<double>(start + i) / kFs;
        re += x[start + i] * std::cos(w);
        im += x[start + i] * std::sin(w);
    }
    return 2.0 * std::sqrt(re * re + im * im) / static_cast<double>(len);
}
double db(double x) { return 20.0 * std::log10(std::max(x, 1e-12)); }
double peakAbs(const std::vector<float>& x, std::size_t a, std::size_t b) {
    double p = 0;
    for (std::size_t i = a; i < b; ++i) p = std::max(p, static_cast<double>(std::fabs(x[i])));
    return p;
}
double rmsOf(const std::vector<float>& x, std::size_t a, std::size_t b) {
    double s = 0;
    for (std::size_t i = a; i < b; ++i) s += static_cast<double>(x[i]) * x[i];
    return std::sqrt(s / static_cast<double>(b - a));
}
bool allFinite(const Stereo& s) {
    for (std::size_t i = 0; i < s.size(); ++i)
        if (!std::isfinite(s.l[i]) || !std::isfinite(s.r[i])) return false;
    return true;
}
double maxAbs(const Stereo& s) { return std::max(peakAbs(s.l, 0, s.size()), peakAbs(s.r, 0, s.size())); }
double maxSecondDiff(const std::vector<float>& x, std::size_t a, std::size_t b) {
    double m = 0;
    for (std::size_t i = a + 2; i < b; ++i) m = std::max(m, std::fabs(static_cast<double>(x[i]) - 2.0 * x[i - 1] + x[i - 2]));
    return m;
}

// Gain in dB that `type` applies to a sine of `freq` (steady state, whole cycles measured).
double sineGainDb(const std::string& type, const json& params, double freq, double amp = 0.1) {
    auto fx = make(type, params);
    Stereo s = sine(48000, freq, amp);
    run(*fx, s);
    const std::size_t len = 24000;  // 0.5 s, whole cycles for multiples of 2 Hz
    return db(toneAmp(s.l, 24000, len, freq) / amp);
}

// True peak by 16x windowed-sinc interpolation (reference meter, independent of the limiter).
double truePeak(const std::vector<float>& x, std::size_t a, std::size_t b) {
    constexpr int kHalf = 48, kOver = 16;
    auto i0 = [](double v) {
        double s = 1, t = 1;
        for (int k = 1; k < 200; ++k) { t *= (v * v / 4) / (static_cast<double>(k) * k); s += t; if (t < 1e-17 * s) break; }
        return s;
    };
    const double beta = 10.0, norm = i0(beta);
    std::vector<std::vector<double>> taps(kOver, std::vector<double>(2 * kHalf));
    for (int ph = 1; ph < kOver; ++ph) {
        const double t = static_cast<double>(ph) / kOver;
        for (int j = 0; j < 2 * kHalf; ++j) {
            const double d = t - (j - kHalf + 1);  // distance to sample (n - kHalf + 1 + j)
            const double r = 1 - (d / kHalf) * (d / kHalf);
            const double w = r > 0 ? i0(beta * std::sqrt(r)) / norm : 0;
            taps[ph][j] = std::sin(kPi * d) / (kPi * d) * w;
        }
    }
    double p = peakAbs(x, a, b);
    for (std::size_t n = std::max<std::size_t>(a, kHalf); n + kHalf < b; ++n) {
        for (int ph = 1; ph < kOver; ++ph) {
            double acc = 0;
            for (int j = 0; j < 2 * kHalf; ++j) acc += taps[ph][j] * x[n - kHalf + 1 + j];
            p = std::max(p, std::fabs(acc));
        }
    }
    return p;
}

// ------------------------------------------------------------------------------------------

void testFactoryAndSpecs() {
    std::printf("\n== factory & param specs ==\n");
    const auto types = as::dynamicsEffectTypes();
    check(types.size() == 10, "10 effect types");
    check(as::createDynamicsEffect("reverb") == nullptr, "unknown type -> nullptr");
    check(as::dynamicsEffectAcceptsSidechain("compressor") && as::dynamicsEffectAcceptsSidechain("ducker") &&
              !as::dynamicsEffectAcceptsSidechain("eq") && !as::dynamicsEffectAcceptsSidechain("limiter"),
          "sidechain accepted only by compressor and ducker");
    bool specsOk = true;
    for (const auto& t : types) {
        auto fx = as::createDynamicsEffect(t);
        if (!fx) { specsOk = false; continue; }
        for (const auto& s : fx->paramSpecs()) {
            if (s.name.empty() || s.help.size() < 10 || !(s.min <= s.def && s.def <= s.max)) {
                std::printf("   bad spec %s.%s\n", t.c_str(), s.name.c_str());
                specsOk = false;
            }
        }
    }
    check(specsOk, "every type creates; every spec has name, help, min<=def<=max");

    auto throws = [](const std::string& type, const json& p) {
        auto fx = as::createDynamicsEffect(type);
        try { fx->configure(p); } catch (const as::ConfigError&) { return true; }
        return false;
    };
    check(throws("compressor", {{"bogus", 1}}), "unknown param rejected");
    check(throws("compressor", {{"threshold", 5}}), "out-of-range param rejected");
    check(throws("saturator", {{"mode", "fuzz"}}), "unknown enum choice rejected");
    check(throws("eq", {{"hp.slope", 18}}), "eq slope must be 12 or 24");
    check(!throws("eq", {{"hp.slope", 24}, {"lp.slope", 12}}), "eq slope 24 accepted");
    auto lim = make("limiter");
    check(!lim->setParam("ceiling", -3.0f) && !lim->setParam("nope", 1.0f) && lim->setParam("gain", 3.0f),
          "setParam: non-automatable/unknown refused, automatable accepted");
}

void testEq() {
    std::printf("\n== eq ==\n");
    {
        auto fx = make("eq");
        Stereo in = noise(48000, 0.5, 11), out = in;
        run(*fx, out);
        check(out.l == in.l && out.r == in.r, "default eq is bit-transparent");
    }
    const double g1 = sineGainDb("eq", {{"peak2.freq", 1000}, {"peak2.gain", 6}, {"peak2.q", 1}}, 1000);
    check(std::fabs(g1 - 6.0) < 0.1, "peak +6 dB @1k: gain at 1 kHz", g1);
    const double g1off = sineGainDb("eq", {{"peak2.freq", 1000}, {"peak2.gain", 6}, {"peak2.q", 1}}, 100);
    check(std::fabs(g1off) < 0.3, "peak +6 dB @1k: gain at 100 Hz ~0", g1off);
    const double g2 = sineGainDb("eq", {{"peak3.freq", 3000}, {"peak3.gain", -9}, {"peak3.q", 2}}, 3000);
    check(std::fabs(g2 + 9.0) < 0.1, "peak -9 dB @3k q2: gain at 3 kHz", g2);
    {   // high bells keep their analog shape (no bilinear cramping): 10 kHz, Q 1, +9 dB at 48k.
        // Analog prototype: 2.89 dB at 5 kHz, 7.34 dB at 12.5 kHz (bilinear gave 2.24 / 6.08).
        const json bell = {{"peak3.freq", 10000}, {"peak3.gain", 9}, {"peak3.q", 1}};
        const double lo = sineGainDb("eq", bell, 5000), hi = sineGainDb("eq", bell, 12500);
        const double worst = std::max(std::fabs(lo - 2.89), std::fabs(hi - 7.34));
        check(worst < 0.15, "peak +9 dB @10k q1: matches analog shape at 5k and 12.5k (worst dB error)", worst);
        const double c = sineGainDb("eq", bell, 10000);
        check(std::fabs(c - 9.0) < 0.05, "peak +9 dB @10k: exact at centre", c);
    }
    const double g3 = sineGainDb("eq", {{"low.freq", 200}, {"low.gain", 6}}, 30);
    check(std::fabs(g3 - 6.0) < 0.3, "low shelf +6 @200: gain at 30 Hz", g3);
    const double g4 = sineGainDb("eq", {{"high.freq", 4000}, {"high.gain", -6}}, 16000);
    check(std::fabs(g4 + 6.0) < 0.3, "high shelf -6 @4k: gain at 16 kHz", g4);
    const double g5 = sineGainDb("eq", {{"hp.freq", 120}, {"hp.slope", 24}}, 30);
    check(g5 < -40.0, "hp 24 dB @120: 30 Hz sine removed", g5);
    const double g5b = sineGainDb("eq", {{"hp.freq", 120}, {"hp.slope", 24}}, 1000);
    check(std::fabs(g5b) < 0.05, "hp 24 dB @120: 1 kHz untouched", g5b);
    const double g6 = sineGainDb("eq", {{"hp.freq", 120}}, 30);
    check(g6 < -20.0, "hp 12 dB @120: 30 Hz attenuated", g6);
    const double g7 = sineGainDb("eq", {{"lp.freq", 2000}, {"lp.slope", 24}}, 10000);
    check(g7 < -50.0, "lp 24 dB @2k: 10 kHz attenuated", g7);

    // Automation: random jumps every 32 samples must not click (glide + 16-sample coefficient steps).
    auto fx = make("eq", {{"peak2.gain", 0}});
    Stereo s = sine(96000, 1000, 0.25);
    as::dsp::Rng rng(7);
    run(*fx, s, nullptr, 32, [&](std::size_t) {
        fx->setParam("peak2.gain", -12 + 24 * rng.uniform());
        fx->setParam("peak2.freq", 300 + 3000 * rng.uniform());
        fx->setParam("hp.freq", 10 + 500 * rng.uniform());
        fx->setParam("low.gain", -10 + 20 * rng.uniform());
    });
    const double sd = maxSecondDiff(s.l, 0, s.size());
    check(sd < 0.03 && allFinite(s), "eq automated every 32 samples: no clicks (max 2nd difference)", sd);
}

void testFilter() {
    std::printf("\n== filter ==\n");
    {
        auto fx = make("filter");
        Stereo in = noise(48000, 0.5, 12), out = in;
        run(*fx, out);
        check(out.l == in.l && out.r == in.r, "default filter (lp fully open) is bit-transparent");
    }
    const double a = sineGainDb("filter", {{"cutoff", 500}}, 100);
    check(std::fabs(a) < 1.0, "lp 500: 100 Hz passes", a);
    const double b = sineGainDb("filter", {{"cutoff", 500}}, 5000);
    check(b < -35.0, "lp 500: 5 kHz attenuated (12 dB/oct)", b);
    const double c = sineGainDb("filter", {{"mode", "ladder"}, {"cutoff", 500}}, 5000);
    check(c < -70.0, "ladder 500: 5 kHz attenuated (24 dB/oct)", c);
    const double c2 = sineGainDb("filter", {{"mode", "ladder"}, {"cutoff", 2000}, {"resonance", 0.8}}, 100);
    check(std::fabs(c2) < 0.5, "ladder: passband gain compensated at high resonance", c2);
    const double d = sineGainDb("filter", {{"mode", "hp"}, {"cutoff", 1000}}, 100);
    check(d < -35.0, "hp 1k: 100 Hz attenuated", d);
    const double e = sineGainDb("filter", {{"mode", "bp"}, {"cutoff", 1000}, {"resonance", 0.5}}, 1000);
    check(std::fabs(e) < 0.2, "bp 1k: unity at centre", e);
    const double f = sineGainDb("filter", {{"cutoff", 1000}, {"resonance", 1.0}}, 1000);
    check(f > 18.0 && f < 23.0, "lp resonance 1: ~+21 dB peak at cutoff", f);
    const double f2 = sineGainDb("filter", {{"mode", "ladder"}, {"cutoff", 1000}, {"resonance", 1.0}}, 1000, 0.01);
    check(f2 > 18.0 && f2 < 23.0, "ladder resonance 1: ~+21 dB peak like the SVF modes (was +34 dB)", f2);
    const double f3 = sineGainDb("filter", {{"mode", "ladder"}, {"cutoff", 1000}, {"resonance", 0.0}}, 1000, 0.01);
    check(std::fabs(f3 + 12.04) < 0.3, "ladder resonance 0: -12 dB at cutoff (4 poles)", f3);

    // Fast DJ sweeps with high resonance and drive on loud noise stay finite and bounded.
    for (const char* mode : {"lp", "hp", "bp", "ladder"}) {
        auto fx = make("filter", {{"mode", mode}, {"resonance", 0.95}, {"drive", 12}});
        Stereo s = noise(96000, 0.9, 13);
        std::size_t k = 0;
        run(*fx, s, nullptr, 32, [&](std::size_t pos) {
            const double ph = static_cast<double>(pos) / 24000.0;
            fx->setParam("cutoff", static_cast<float>(40.0 * std::pow(400.0, 0.5 + 0.5 * std::sin(2 * kPi * ph))));
            if (++k % 50 == 0) fx->setParam("cutoff", 20000.0f);  // abrupt jumps too
        });
        check(allFinite(s) && maxAbs(s) < 30.0, std::string("filter ") + mode + " sweep: finite and bounded", maxAbs(s));
    }
}

void testCompressorGainReduction();

void testCompressor() {
    std::printf("\n== compressor ==\n");
    {  // peak detector: -6 dBFS sine, thr -30, 4:1 -> -24 dBFS peaks
        auto fx = make("compressor", {{"threshold", -30}, {"ratio", 4}, {"knee", 0}, {"attack", 1}, {"release", 300}});
        Stereo s = sine(96000, 1000, 0.5);
        run(*fx, s);
        const double out = db(peakAbs(s.l, 72000, 96000));
        check(std::fabs(out + 24.0) < 1.0, "peak: -6 dBFS sine, thr -30, 4:1 -> output peak ~-24 dBFS", out);
    }
    {  // rms detector: sine RMS -9.03 -> -30 + 20.97/4 = -24.76 dBFS RMS
        auto fx = make("compressor",
                       {{"threshold", -30}, {"ratio", 4}, {"knee", 0}, {"attack", 5}, {"release", 300}, {"detector", "rms"}});
        Stereo s = sine(96000, 1000, 0.5);
        run(*fx, s);
        const double out = db(rmsOf(s.l, 72000, 96000));
        check(std::fabs(out + 24.76) < 1.0, "rms: output RMS ~-24.8 dBFS", out);
    }
    {  // below threshold: untouched
        auto fx = make("compressor", {{"threshold", -20}, {"knee", 6}});
        Stereo s = sine(48000, 1000, 0.01);
        run(*fx, s);
        const double g = db(toneAmp(s.l, 24000, 24000, 1000) / 0.01);
        check(std::fabs(g) < 0.02, "below threshold: unity gain", g);
    }
    {  // sidechain: loud key compresses a quiet input
        auto fx = make("compressor", {{"threshold", -30}, {"ratio", 4}, {"knee", 0}, {"attack", 1}, {"release", 300}});
        Stereo s = sine(96000, 440, 0.1), key = sine(96000, 1000, 0.5);
        run(*fx, s, &key);
        const double g = db(peakAbs(s.l, 72000, 96000) / 0.1);
        check(std::fabs(g + 18.0) < 1.0, "sidechain key -6 dBFS: input reduced by ~18 dB", g);
    }
    {  // automakeup restores a -10 dBFS peak
        auto fx = make("compressor",
                       {{"threshold", -30}, {"ratio", 4}, {"knee", 0}, {"attack", 1}, {"release", 300}, {"automakeup", true}});
        Stereo s = sine(96000, 1000, std::pow(10.0, -0.5));
        run(*fx, s);
        const double out = db(peakAbs(s.l, 72000, 96000));
        check(std::fabs(out + 10.0) < 1.0, "automakeup: -10 dBFS peak comes out near -10", out);
    }
    {
        auto fx = make("compressor", {{"threshold", -40}, {"mix", 0}});
        Stereo in = noise(24000, 0.5, 14), out = in;
        run(*fx, out);
        check(out.l == in.l, "mix 0 = dry, bit-exact");
    }
    {  // range caps the reduction: -6 dBFS sine, thr -30, 4:1 would take 18 dB; range 6 -> 6 dB
        auto fx = make("compressor", {{"threshold", -30}, {"ratio", 4}, {"knee", 0}, {"attack", 1}, {"release", 300},
                                      {"range", 6}});
        Stereo s = sine(96000, 1000, 0.5);
        run(*fx, s);
        const double g = db(peakAbs(s.l, 72000, 96000) / 0.5);
        check(std::fabs(g + 6.0) < 0.3, "range 6: reduction capped at 6 dB", g);
    }
    {  // band mode (dynamic EQ) keyed from a lead: only the band around 2.5 kHz dips, by at most 'range'
        auto fx = make("compressor", {{"threshold", -40}, {"ratio", 10}, {"knee", 0}, {"attack", 5}, {"release", 200},
                                      {"range", 6}, {"band", 2500}, {"bandq", 0.7}});
        Stereo lo = sine(96000, 300, 0.1), hi = sine(96000, 2500, 0.1), key = sine(96000, 2500, 0.5);
        Stereo s(96000);
        for (std::size_t i = 0; i < s.size(); ++i) {
            s.l[i] = lo.l[i] + hi.l[i];
            s.r[i] = lo.r[i] + hi.r[i];
        }
        run(*fx, s, &key);
        const double gHi = db(toneAmp(s.l, 48000, 48000, 2500) / 0.1), gLo = db(toneAmp(s.l, 48000, 48000, 300) / 0.1);
        check(std::fabs(gHi + 6.0) < 0.4, "band 2.5 kHz, keyed: the 2.5 kHz tone dips by the range (dB)", gHi);
        check(std::fabs(gLo) < 0.4, "band 2.5 kHz, keyed: a 300 Hz tone stays (dB)", gLo);
        check(allFinite(s), "band mode: finite");
    }
    {  // band mode with a quiet key: no reduction -> the signal passes bit-exact (x + 0 * band)
        auto fx = make("compressor", {{"threshold", -20}, {"ratio", 4}, {"band", 2500}});
        Stereo in = noise(24000, 0.01, 21), out = in, key = sine(24000, 2500, 0.001);
        run(*fx, out, &key);
        check(out.l == in.l && out.r == in.r, "band mode, key under the threshold: bit-exact pass-through");
    }
    {  // band mode, unkeyed de-esser: a loud 6 kHz tone is reduced, a quiet 500 Hz tone is not
        auto fx = make("compressor", {{"threshold", -30}, {"ratio", 4}, {"knee", 0}, {"attack", 1}, {"release", 100},
                                      {"band", 6000}, {"bandq", 1.0}});
        Stereo a = sine(96000, 6000, 0.5), b = sine(96000, 500, 0.05), s(96000);
        for (std::size_t i = 0; i < s.size(); ++i) {
            s.l[i] = a.l[i] + b.l[i];
            s.r[i] = a.r[i] + b.r[i];
        }
        run(*fx, s);
        const double g6 = db(toneAmp(s.l, 48000, 48000, 6000) / 0.5), g5 = db(toneAmp(s.l, 48000, 48000, 500) / 0.05);
        check(g6 < -10.0, "band 6 kHz de-esser: the loud 6 kHz tone is reduced (dB)", g6);
        check(std::fabs(g5) < 0.5, "band 6 kHz de-esser: 500 Hz untouched (dB)", g5);
    }
    testCompressorGainReduction();
}

// Gain reduction must follow the static curve on steady tones at any frequency and any attack /
// release (a branching peak detector on the instantaneous level re-attacks every cycle: it read up to
// 3 dB short and rippled at twice the signal frequency, distorting bass), and attack / release must
// keep their meaning as time constants.
void testCompressorGainReduction() {
    // steady state: -6 dBFS sine, threshold -20, 4:1, hard knee -> 10.5 dB (peak), 8.24 dB (rms, -9.03 dBFS)
    auto steady = [](const char* det, double attack, double release, double freq, double& thdDb) {
        auto fx = make("compressor", {{"threshold", -20}, {"ratio", 4}, {"knee", 0}, {"attack", attack}, {"release", release},
                                      {"detector", det}});
        Stereo s = sine(96000, freq, 0.5);
        run(*fx, s);
        const double fund = toneAmp(s.l, 48000, 48000, freq);
        double harm = 0.0;
        for (int k = 2; k <= 6; ++k) harm += std::pow(toneAmp(s.l, 48000, 48000, freq * k), 2);
        thdDb = db(std::sqrt(harm) / fund);
        return -db(fund / 0.5);
    };
    double worstPeak = 0.0, worstRms = 0.0, thdDefault = -200.0, thdFast = -200.0;
    for (const double freq : {50.0, 100.0, 1000.0})
        for (const auto& ar : {std::pair{10.0, 120.0}, std::pair{1.0, 50.0}, std::pair{30.0, 50.0}, std::pair{30.0, 400.0}}) {
            double thd = 0.0;
            worstPeak = std::max(worstPeak, std::fabs(steady("peak", ar.first, ar.second, freq, thd) - 10.5));
            if (freq == 50.0 && ar.first == 10.0) thdDefault = thd;
            if (freq == 50.0 && ar.first == 30.0 && ar.second == 50.0) thdFast = thd;
            worstRms = std::max(worstRms, std::fabs(steady("rms", ar.first, ar.second, freq, thd) - 8.24));
        }
    // (the worst case is fast release on bass: attack 30 / release 50 at 50 Hz, ~0.6 dB short)
    check(worstPeak < 0.7, "peak detector: steady gain reduction = static curve (10.5 dB) within 0.7 dB, 50 Hz-1 kHz, "
                           "attack 1-30 / release 50-400 ms (worst dB error)", worstPeak);
    check(worstRms < 0.75, "rms detector: steady gain reduction = static curve (8.2 dB) within 0.75 dB (worst dB error)", worstRms);
    check(thdDefault < -50.0 && thdFast < -45.0,
          "50 Hz sine under 10 dB of reduction: gain ripple distortion (THD dB at defaults; attack 30 / release 50: " +
              std::to_string(thdFast).substr(0, 5) + ")", thdDefault);

    // timing: -40 dBFS -> -6 dBFS tone burst (1 kHz) and back; gain reduction from the output envelope.
    // The release runs through both detector stages; without compensation it took attack + release
    // (attack 30 / release 50 recovered in 85 ms, attack 100 / release 50 in 158 ms).
    auto burst = [](double attack, double release, double& full, double& tAtt, double& tRel) {
        auto fx = make("compressor", {{"threshold", -20}, {"ratio", 4}, {"knee", 0}, {"attack", attack}, {"release", release}});
        const std::size_t n = 144000, on = 24000, off = 72000;
        Stereo s = sine(n, 1000, 1.0);
        for (std::size_t i = 0; i < n; ++i) {
            const float a = (i >= on && i < off) ? 0.5f : 0.01f;
            s.l[i] *= a;
            s.r[i] *= a;
        }
        Stereo in = s;
        run(*fx, s);
        auto grAt = [&](std::size_t i) {  // 1 ms windows (whole cycles)
            return db(peakAbs(in.l, i, i + 48) / std::max(peakAbs(s.l, i, i + 48), 1e-12));
        };
        full = grAt(off - 480);
        tAtt = tRel = -1.0;
        for (std::size_t i = on; i < off; i += 12)
            if (grAt(i) >= 0.632 * full) { tAtt = (static_cast<double>(i) + 24.0 - on) / 48.0; break; }
        for (std::size_t i = off; i < n - 48; i += 12)
            if (grAt(i) <= 0.368 * full) { tRel = (static_cast<double>(i) + 24.0 - off) / 48.0; break; }
    };
    {
        double full = 0.0, tAtt = 0.0, tRel = 0.0;
        burst(10.0, 120.0, full, tAtt, tRel);
        check(std::fabs(full - 10.5) < 0.3, "tone burst: full reduction reached (dB)", full);
        check(tAtt > 7.0 && tAtt < 13.0, "attack 10 ms: 63 % of the reduction after (ms)", tAtt);
        check(tRel > 110.0 && tRel < 132.0, "release 120 ms: back to 37 % after (ms)", tRel);
    }
    {
        double worst = 0.0;
        std::string detail;
        for (const auto& ar : {std::pair{1.0, 50.0}, std::pair{30.0, 50.0}, std::pair{50.0, 400.0}, std::pair{5.0, 20.0}}) {
            double full = 0.0, tAtt = 0.0, tRel = 0.0;
            burst(ar.first, ar.second, full, tAtt, tRel);
            worst = std::max(worst, std::fabs(tRel / ar.second - 1.0));
            detail += " " + std::to_string(static_cast<int>(ar.first)) + "/" + std::to_string(static_cast<int>(ar.second)) + ": " +
                      std::to_string(static_cast<int>(tRel + 0.5));
        }
        check(worst < 0.2, "release time independent of the attack (attack/release ms: measured release ms)" + detail, worst);
    }
}

// Kick-like key: 60 Hz bursts with exponential decay; each hit chokes the previous one (a drum voice).
Stereo kickKey(std::size_t n, const std::vector<double>& startsSec, double decaySec, double amp) {
    Stereo k(n);
    for (std::size_t h = 0; h < startsSec.size(); ++h) {
        const std::size_t s0 = static_cast<std::size_t>(startsSec[h] * kFs);
        const std::size_t s1 = h + 1 < startsSec.size() ? static_cast<std::size_t>(startsSec[h + 1] * kFs) : n;
        for (std::size_t i = s0; i < std::min(s1, n); ++i) {
            const double t = static_cast<double>(i - s0) / kFs;
            const double v = amp * std::exp(-t / decaySec) * std::sin(2 * kPi * 60 * t);
            k.l[i] = static_cast<float>(v);
            k.r[i] = static_cast<float>(v);
        }
    }
    return k;
}

void testDucker() {
    std::printf("\n== ducker ==\n");
    const std::size_t n = static_cast<std::size_t>(3.0 * kFs);
    std::vector<double> starts;
    for (int k = 0; k < 5; ++k) starts.push_back(0.3 + 0.5 * k);
    for (double decay : {0.05, 0.4}) {  // short kick, and a boomy kick whose tail never drops below threshold
        auto fx = make("ducker", {{"depth", 12}, {"attack", 2}, {"hold", 20}, {"release", 150}, {"threshold", -30}});
        Stereo s(n);
        std::fill(s.l.begin(), s.l.end(), 0.25f);
        std::fill(s.r.begin(), s.r.end(), 0.25f);
        Stereo key = kickKey(n, starts, decay, 0.8);
        run(*fx, s, &key);
        std::vector<double> gdb(n);
        for (std::size_t i = 0; i < n; ++i) gdb[i] = db(s.l[i] / 0.25);
        bool dipsOk = true, recoverOk = true, onsetOk = true;
        double worstDip = 0, worstRecover = 0;
        for (double t0 : starts) {
            const std::size_t s0 = static_cast<std::size_t>(t0 * kFs);
            double mn = 0;
            for (std::size_t i = s0; i < s0 + 2400; ++i) mn = std::min(mn, gdb[i]);
            worstDip = std::max(worstDip, std::fabs(mn + 12.0));
            dipsOk = dipsOk && std::fabs(mn + 12.0) < 0.5;
            onsetOk = onsetOk && gdb[s0 + 240] < -6.0;  // ducked within 5 ms
            const double before = gdb[s0 - 48];          // 1 ms before the next hit: recovered
            worstRecover = std::min(worstRecover, before);
            recoverOk = recoverOk && before > -0.5;
        }
        double maxStep = 0;
        for (std::size_t i = 1; i < n; ++i) maxStep = std::max(maxStep, std::fabs(static_cast<double>(s.l[i] - s.l[i - 1])) / 0.25);
        const std::string tag = decay < 0.1 ? "short kick: " : "boomy kick, tail above threshold: ";
        check(dipsOk, tag + "every hit dips to -12 dB (worst error dB)", worstDip);
        check(onsetOk, tag + "duck starts within 5 ms of each hit");
        check(recoverOk, tag + "recovers to ~0 dB before the next hit (worst dB)", worstRecover);
        check(maxStep < 0.02, tag + "click-free (max gain step per sample)", maxStep);
    }
    {   // key mode without a sidechain falls back to the tempo grid (instead of silently doing nothing)
        auto fxKey = make("ducker", {{"depth", 12}});
        auto fxTempo = make("ducker", {{"mode", "tempo"}, {"depth", 12}});
        Stereo a = noise(48000, 0.5, 15), b = a;
        run(*fxKey, a);
        run(*fxTempo, b);
        check(a.l == b.l && a.r == b.r, "key mode without a sidechain = tempo grid (bit-identical)");
    }
    // Tempo mode: 120 bpm at 48 kHz -> one beat = 24000 samples.
    auto tempoCheck = [&](double rate, double offset, const std::string& label) {
        auto fx = make("ducker", {{"mode", "tempo"}, {"rate", rate}, {"offset", offset}, {"depth", 12}, {"attack", 2},
                                  {"hold", 0}, {"release", 100}},
                       120.0);
        const std::size_t len = 4 * 24000;
        Stereo s(len);
        std::fill(s.l.begin(), s.l.end(), 1.0f);
        std::fill(s.r.begin(), s.r.end(), 1.0f);
        run(*fx, s, nullptr, 100);
        const double period = rate * 24000.0;
        bool ok = true;
        int dips = 0;
        for (double pos = offset * 24000.0; pos + 200 < static_cast<double>(len); pos += period) {
            if (pos < 1) continue;
            const std::size_t p = static_cast<std::size_t>(std::llround(pos));
            ok = ok && s.l[p - 1] == 1.0f && s.l[p] < 1.0f && std::fabs(db(s.l[p + 96]) + 12.0) < 0.2;
            ++dips;
        }
        check(ok && dips >= 3, "tempo mode " + label + ": dips start exactly on the grid and reach -12 dB");
    };
    tempoCheck(1.0, 0.0, "rate 1");
    tempoCheck(0.5, 0.0, "rate 0.5");
    tempoCheck(1.0, 0.5, "offset 0.5 beat");
    {   // release curve -1 (fast recovery) must start without a gain jump
        double worst = 0;
        for (double curve : {-1.0, -0.5, 0.0, 0.5, 1.0}) {
            auto fx = make("ducker", {{"mode", "tempo"}, {"depth", 12}, {"curve", curve}, {"release", 50}, {"hold", 0}});
            Stereo s(48000);
            std::fill(s.l.begin(), s.l.end(), 0.5f);
            std::fill(s.r.begin(), s.r.end(), 0.5f);
            run(*fx, s);
            for (std::size_t i = 1; i < s.size(); ++i) worst = std::max(worst, std::fabs(static_cast<double>(s.l[i]) - s.l[i - 1]) / 0.5);
        }
        check(worst < 0.03, "release curves -1..1, 50 ms: max per-sample gain step", worst);
    }
    {   // changing rate/offset mid-song must not fire extra ducks: count trigger onsets
        auto fx = make("ducker", {{"mode", "tempo"}, {"depth", 12}, {"attack", 0.5}, {"hold", 0}, {"release", 10}});
        Stereo s(48000 * 4);
        std::fill(s.l.begin(), s.l.end(), 1.0f);
        std::fill(s.r.begin(), s.r.end(), 1.0f);
        run(*fx, s, nullptr, 256, [&](std::size_t pos) {
            if (pos == 256 * 50) fx->setParam("rate", 0.75f);     // at beat 0.53: grid 0.75, 1.5, ...
            if (pos == 256 * 300) fx->setParam("offset", 0.3f);  // at beat 3.2: grid 3.3, 4.05, ...
        });
        std::vector<double> starts;
        for (std::size_t i = 0; i < s.size(); ++i)
            if (s.l[i] < 0.9999f && (i == 0 || s.l[i - 1] >= 0.9999f)) starts.push_back(static_cast<double>(i) / 24000.0);
        const std::vector<double> expect = {0.0, 0.75, 1.5, 2.25, 3.0, 3.3, 4.05, 4.8, 5.55, 6.3, 7.05, 7.8};
        bool ok = starts.size() == expect.size();
        for (std::size_t k = 0; ok && k < expect.size(); ++k) ok = std::fabs(starts[k] - expect[k]) < 0.001;
        check(ok, "rate/offset automation: ducks follow the new grid, no spurious extra duck", static_cast<double>(starts.size()));
    }
}

void testSaturator() {
    std::printf("\n== saturator ==\n");
    auto harmonicDb = [](const json& params, int harmonic) {
        auto fx = make("saturator", params);
        Stereo s = sine(48000, 1000, 0.5);
        run(*fx, s);
        const double h1 = toneAmp(s.l, 24000, 24000, 1000);
        return db(toneAmp(s.l, 24000, 24000, 1000.0 * harmonic) / h1);
    };
    const double t3 = harmonicDb({{"mode", "tape"}, {"drive", 12}}, 3);
    check(t3 > -35.0, "tape drive 12: strong 3rd harmonic (dB rel. fundamental)", t3);
    const double u2 = harmonicDb({{"mode", "tube"}, {"drive", 6}}, 2);
    const double u3 = harmonicDb({{"mode", "tube"}, {"drive", 6}}, 3);
    check(u2 > -40.0, "tube drive 6: 2nd harmonic present", u2);
    std::printf("       tube drive 6: H3 %.1f dB\n", u3);
    const double tape2 = harmonicDb({{"mode", "tape"}, {"drive", 6}}, 2);
    check(tape2 < -90.0, "tape (symmetric, no bias): no 2nd harmonic", tape2);

    // Aliasing: 15 kHz sine driven hard. In-band (20 Hz..20 kHz) energy other than the 15 kHz
    // fundamental is aliasing (all real harmonics are above Nyquist).
    const std::size_t N = 4800;  // 10 Hz bins, 15 kHz = bin 1500
    std::vector<double> cs(N), sn(N);
    for (std::size_t k = 0; k < N; ++k) { cs[k] = std::cos(2 * kPi * k / N); sn[k] = std::sin(2 * kPi * k / N); }
    auto aliasDb = [&](const std::vector<float>& x, std::size_t start) {
        double fund = 0, alias = 0;
        for (std::size_t bin = 2; bin <= 2000; ++bin) {
            double re = 0, im = 0;
            for (std::size_t i = 0; i < N; ++i) {
                const std::size_t idx = (bin * i) % N;
                re += x[start + i] * cs[idx];
                im += x[start + i] * sn[idx];
            }
            const double e = re * re + im * im;
            if (bin == 1500) fund = e;
            else alias += e;
        }
        return 10.0 * std::log10(std::max(alias, 1e-30) / fund);
    };
    {   // reference: naive hard clip without oversampling
        Stereo s = sine(3 * N, 15000, 0.5);
        for (auto& v : s.l) v = std::clamp(v * 16.0f, -1.0f, 1.0f);
        std::printf("       reference naive 1x hard clip @+24 dB: aliasing %.1f dB\n", aliasDb(s.l, N));
    }
    for (const char* mode : {"tape", "tube", "hard", "fold"}) {
        auto fx = make("saturator", {{"mode", mode}, {"drive", 24}});
        Stereo s = sine(6 * N, 15000, 0.5);  // analyse the last 0.1 s, after the DC blocker settled
        run(*fx, s);
        const double a = aliasDb(s.l, 5 * N);
        const double limit = std::string(mode) == "fold" ? -40.0 : -50.0;
        check(a < limit, std::string("aliasing of a 15 kHz sine, ") + mode + " drive +24 dB (dB rel. fundamental)", a);
    }

    // Latency alignment and flat passband: linear region (hard mode, low drive) wet == delayed dry.
    {
        Stereo in(48000);
        for (std::size_t i = 0; i < in.size(); ++i) {
            const double t = static_cast<double>(i) / kFs;
            const double v = 0.1 * (std::sin(2 * kPi * 997 * t + 1) + std::sin(2 * kPi * 5003 * t + 2) +
                                    std::sin(2 * kPi * 12011 * t + 3) + std::sin(2 * kPi * 17989 * t + 4));
            in.l[i] = in.r[i] = static_cast<float>(v);
        }
        auto dryFx = make("saturator", {{"mode", "hard"}, {"drive", -12}, {"mix", 0}});
        auto wetFx = make("saturator", {{"mode", "hard"}, {"drive", -12}, {"mix", 1}});
        Stereo dry = in, wet = in;
        run(*dryFx, dry);
        run(*wetFx, wet);
        // The oversampling is minimum-delay IIR (no latency compensation exists on tracks): the
        // dry path at mix 0 must be flat and only a few samples late.
        double worstFlat = 0, delay1k = 0;
        for (double f : {50.0, 1000.0, 5000.0, 12000.0, 18000.0}) {
            auto fx = make("saturator", {{"mode", "hard"}, {"drive", -12}, {"mix", 0}});
            Stereo s = sine(48000, f, 0.2);
            run(*fx, s);
            double re = 0, im = 0;
            for (std::size_t i = 24000; i < 48000; ++i) {
                const double w = 2 * kPi * f * static_cast<double>(i) / kFs;
                re += s.l[i] * std::cos(w);
                im += s.l[i] * std::sin(w);
            }
            worstFlat = std::max(worstFlat, std::fabs(db(2.0 * std::hypot(re, im) / 24000.0 / 0.2)));
            if (f == 1000.0) delay1k = -std::atan2(re, im) / (2 * kPi * f) * kFs;  // input phase is 0 (sin)
        }
        check(worstFlat < 0.05, "mix 0: dry path flat 50 Hz..18 kHz (worst dB)", worstFlat);
        check(delay1k > 0.0 && delay1k < 7.0, "oversampling delay at 1 kHz is a few samples, not ~70 (samples)", delay1k);
        {   // parallel (send-bus) use: dry + saturated copy must add up, not comb-filter
            Stereo a = sine(48000, 500, 0.1), b = a;
            auto fx = make("saturator", {{"mode", "tape"}, {"drive", -12}});
            run(*fx, b);
            for (std::size_t i = 0; i < a.size(); ++i) a.l[i] += b.l[i];
            const double g = db(toneAmp(a.l, 24000, 24000, 500) / 0.1);
            check(g > 5.8, "parallel dry + wet at 500 Hz sums coherently (dB, 6.02 ideal)", g);
        }
        double err = 0, ref = 0;
        for (std::size_t i = 4800; i < in.size(); ++i) {
            err += (wet.l[i] - dry.l[i]) * static_cast<double>(wet.l[i] - dry.l[i]);
            ref += static_cast<double>(dry.l[i]) * dry.l[i];
        }
        const double e = 10 * std::log10(err / ref);
        check(e < -45.0, "linear region: wet matches the phase-aligned dry, 1-18 kHz (error dB)", e);
    }
    {  // Low end: only the 3 Hz DC blocker differs from the dry path -> coherent parallel mixing.
        Stereo in = sine(48000, 60, 0.3);
        auto dryFx = make("saturator", {{"mode", "hard"}, {"drive", -12}, {"mix", 0}});
        auto halfFx = make("saturator", {{"mode", "hard"}, {"drive", -12}, {"mix", 0.5}});
        Stereo dry = in, half = in;
        run(*dryFx, dry);
        run(*halfFx, half);
        const double g = db(toneAmp(half.l, 24000, 24000, 60) / toneAmp(dry.l, 24000, 24000, 60));
        check(std::fabs(g) < 0.01, "60 Hz at mix 0.5 vs dry: no comb/phase loss (dB)", g);
    }
    {  // Bias adds DC internally; the output must be DC-free.
        auto fx = make("saturator", {{"mode", "tube"}, {"drive", 12}, {"bias", 1}});
        Stereo s = sine(96000, 220, 0.5);
        run(*fx, s);
        double mean = 0;
        for (std::size_t i = 48000; i < 96000; ++i) mean += s.l[i];
        mean /= 48000.0;
        check(std::fabs(mean) < 1e-3, "tube + bias: output DC removed (mean)", mean);
    }
    for (const char* mode : {"tape", "tube", "hard", "fold"}) {
        auto fx = make("saturator", {{"mode", mode}, {"drive", 36}, {"bias", -1}, {"tone", 12}});
        Stereo s = noise(48000, 4.0, 16);
        run(*fx, s);
        check(allFinite(s) && maxAbs(s) < 10.0, std::string("saturator ") + mode + " extreme settings: finite, bounded", maxAbs(s));
    }
    {  // loudness compensation: a -12 dBFS sine keeps its RMS at any drive, in every mode
        double worst = 0;
        for (const char* mode : {"tape", "tube", "hard", "fold"}) {
            for (double drive : {-12.0, 0.0, 6.0, 12.0, 24.0, 36.0}) {
                auto fx = make("saturator", {{"mode", mode}, {"drive", drive}, {"bias", 0.3}});
                Stereo s = sine(48000, 200, 0.25);
                run(*fx, s);
                worst = std::max(worst, std::fabs(db(rmsOf(s.l, 24000, 48000) / (0.25 / std::sqrt(2.0)))));
            }
        }
        check(worst < 0.5, "-12 dBFS sine keeps its RMS level at drive -12..36 in all modes (worst dB)", worst);
    }
}

void testLimiter() {
    std::printf("\n== limiter ==\n");
    {
        auto fx = make("limiter");
        const int lat = fx->latencySamples();
        check(lat == 240 + 48, "latencySamples = 5 ms lookahead + 48 interpolator samples at 48 kHz", lat);
        Stereo s(4000);
        s.l[1000] = s.r[1000] = 0.5f;
        run(*fx, s);
        bool ok = s.l[1000 + static_cast<std::size_t>(lat)] == 0.5f;
        for (std::size_t i = 0; i < s.size(); ++i)
            if (i != 1000 + static_cast<std::size_t>(lat)) ok = ok && s.l[i] == 0.0f;
        check(ok, "impulse below ceiling comes out exactly latencySamples later, unchanged");
        auto fx2 = make("limiter");
        Stereo in = noise(48000, 0.3, 17), out = in;
        run(*fx2, out);
        bool same = true;
        for (std::size_t i = static_cast<std::size_t>(lat); i < in.size(); ++i)
            same = same && out.l[i] == in.l[i - static_cast<std::size_t>(lat)] && out.r[i] == in.r[i - static_cast<std::size_t>(lat)];
        check(same, "signal below ceiling passes bit-exact (delayed)");
    }
    for (int variant = 0; variant < 3; ++variant) {
        const double ceilDb = variant == 2 ? -0.3 : -1.0;
        json params = {{"gain", 6}, {"ceiling", ceilDb}};
        if (variant == 1) params["release"] = 10, params["lookahead"] = 1;
        auto fx = make("limiter", params);
        const std::size_t n = 96000;
        Stereo s = noise(n, 3.0, 18 + static_cast<std::uint64_t>(variant));
        for (std::size_t i = 0; i < n; ++i) {
            const double t = static_cast<double>(i) / kFs;
            const double env = (i / 12000) % 2 ? 1.0 : 0.2;  // loud/quiet sections
            const double tones = 2.0 * std::sin(2 * kPi * 50 * t) + 1.0 * std::sin(2 * kPi * 1000 * t) +
                                 1.5 * std::sin(2 * kPi * 9500 * t) + 1.0 * std::sin(2 * kPi * 17000 * t);
            s.l[i] = static_cast<float>(env * (s.l[i] + tones));
            s.r[i] = static_cast<float>(env * (s.r[i] - tones));
        }
        run(*fx, s, nullptr, 173);
        const double c = std::pow(10.0, ceilDb / 20.0);
        const double sp = std::max(peakAbs(s.l, 0, n), peakAbs(s.r, 0, n));
        const std::string tag = "limiter variant " + std::to_string(variant) + " (ceiling " + std::to_string(ceilDb).substr(0, 4) + "): ";
        check(sp <= c * (1.0 + 1e-6) && allFinite(s), tag + "sample peak <= ceiling (dBFS)", db(sp));
        const double tp = std::max(truePeak(s.l, 0, n), truePeak(s.r, 0, n));
        check(db(tp) <= ceilDb + 0.1, tag + "true peak <= ceiling + 0.1 dB (dBTP)", db(tp));
    }
    {  // A steady loud tone settles to a constant gain: output peak at the ceiling, no distortion.
        auto fx = make("limiter", {{"gain", 6}});
        Stereo s = sine(96000, 1000, 0.9);
        run(*fx, s);
        const double pk = db(peakAbs(s.l, 48000, 96000));
        const double h1 = toneAmp(s.l, 48000, 48000, 1000);
        double hsum = 0;
        for (int h = 2; h <= 9; ++h) hsum += std::pow(toneAmp(s.l, 48000, 48000, 1000.0 * h), 2);
        const double thd = 10 * std::log10(std::max(hsum, 1e-30) / (h1 * h1));
        check(std::fabs(pk + 1.0) < 0.05, "steady +5 dBFS tone: output peak at the -1 dBFS ceiling", pk);
        check(thd < -80.0, "steady tone: limiter adds no distortion (THD dB)", thd);
    }
}

void testWidth() {
    std::printf("\n== width ==\n");
    {
        auto fx = make("width", {{"width", 0}});
        Stereo s = noise(24000, 0.5, 19);
        run(*fx, s);
        check(s.l == s.r, "width 0: L == R exactly");
    }
    auto sideDb = [](const json& p, double freq, bool sideInput) {
        auto fx = make("width", p);
        Stereo s = sine(48000, freq, 0.25, sideInput ? kPi : 0.0);
        const Stereo in = s;
        run(*fx, s);
        std::vector<float> side(s.size()), mid(s.size());
        for (std::size_t i = 0; i < s.size(); ++i) {
            side[i] = 0.5f * (s.l[i] - s.r[i]);
            mid[i] = 0.5f * (s.l[i] + s.r[i]);
        }
        return std::make_pair(db(toneAmp(side, 24000, 24000, freq) / 0.25), db(toneAmp(mid, 24000, 24000, freq) / 0.25));
    };
    const auto lo = sideDb({{"monobass", 150}}, 50, true);
    check(lo.first < -30.0, "monobass 150: 50 Hz side content removed (side dB)", lo.first);
    const auto hi = sideDb({{"monobass", 150}}, 5000, true);
    check(std::fabs(hi.first) < 0.1, "monobass 150: 5 kHz stays stereo (side dB)", hi.first);
    const auto mid = sideDb({{"monobass", 150}}, 50, false);
    check(std::fabs(mid.second) < 0.05, "monobass 150: 50 Hz mid content keeps its level (mid dB)", mid.second);
    const auto wide = sideDb({{"width", 2}}, 1000, true);
    check(std::fabs(wide.first - 6.02) < 0.05, "width 2: side +6 dB", wide.first);
    {
        auto fx = make("width", {{"balance", 1}});
        Stereo s = noise(4800, 0.5, 20);
        run(*fx, s);
        check(peakAbs(s.l, 0, s.size()) == 0.0, "balance 1: left silent");
    }
}

void testBitcrushUtility() {
    std::printf("\n== bitcrush / utility ==\n");
    {
        auto fx = make("bitcrush", {{"bits", 4}, {"downsample", 4}});
        Stereo s = noise(4800, 0.9, 21);
        run(*fx, s);
        bool quant = true, held = true;
        for (std::size_t i = 0; i < s.size(); ++i) quant = quant && std::fabs(s.l[i] * 8.0f - std::round(s.l[i] * 8.0f)) < 1e-5f;
        for (std::size_t i = 0; i + 4 <= s.size(); i += 4)
            held = held && s.l[i] == s.l[i + 1] && s.l[i] == s.l[i + 2] && s.l[i] == s.l[i + 3];
        check(quant, "bits 4: output on a 1/8 grid");
        check(held, "downsample 4: sample-and-hold runs of 4");
        auto dry = make("bitcrush", {{"mix", 0}});
        Stereo in = noise(4800, 0.9, 22), out = in;
        run(*dry, out);
        check(out.l == in.l, "bitcrush mix 0 = dry");
    }
    {
        Stereo in = noise(4800, 0.5, 23);
        auto inv = make("utility", {{"invertl", true}});
        Stereo a = in;
        run(*inv, a);
        bool ok = true;
        for (std::size_t i = 0; i < in.size(); ++i) ok = ok && a.l[i] == -in.l[i] && a.r[i] == in.r[i];
        check(ok, "utility invertl: left negated exactly, right untouched");
        auto mono = make("utility", {{"mono", true}});
        Stereo b = in;
        run(*mono, b);
        check(b.l == b.r, "utility mono: L == R");
        auto gain = make("utility", {{"gain", -6.0206}});
        Stereo c = in;
        run(*gain, c);
        check(std::fabs(c.l[100] / in.l[100] - 0.5f) < 1e-4f, "utility gain -6.02 dB halves the level", c.l[100] / in.l[100]);
        auto pan = make("utility", {{"pan", -1}});
        Stereo d = in;
        run(*pan, d);
        check(peakAbs(d.r, 0, d.size()) < 1e-6 && d.l == in.l, "utility pan -1: right silent, left unity");
    }
}

// Every type: random automation of every automatable param each 32 samples on loud noise ->
// finite and bounded; two identical runs are bit-identical; block partitioning does not matter.
void testAllTypesRobust() {
    std::printf("\n== all types: automation robustness, determinism, block independence ==\n");
    for (const auto& type : as::dynamicsEffectTypes()) {
        auto render = [&](bool automate, bool randomBlocks) {
            auto fx = make(type, type == "ducker" ? json{{"threshold", -20}} : json::object(), 128.0);
            Stereo s = noise(48000, 0.7, 30);
            Stereo key = kickKey(48000, {0.1, 0.4, 0.7}, 0.1, 0.9);
            const Stereo* k = as::dynamicsEffectAcceptsSidechain(type) ? &key : nullptr;
            as::dsp::Rng rng(99), blocks(5);
            const auto& specs = fx->paramSpecs();
            if (!randomBlocks) {
                run(*fx, s, k, 32, [&](std::size_t) {
                    if (!automate) return;
                    for (const auto& sp : specs)
                        if (sp.automatable && rng.uniform() < 0.3f)
                            fx->setParam(sp.name, sp.min + (sp.max - sp.min) * rng.uniform());
                });
            } else {
                for (std::size_t pos = 0; pos < s.size();) {
                    const int n = std::min<int>(1 + static_cast<int>(blocks.uniform() * 256), static_cast<int>(s.size() - pos));
                    fx->process(s.l.data() + pos, s.r.data() + pos, n, k ? k->l.data() + pos : nullptr, k ? k->r.data() + pos : nullptr);
                    pos += static_cast<std::size_t>(n);
                }
            }
            return s;
        };
        const Stereo a = render(true, false), b = render(true, false);
        // The eq can legitimately stack five +24 dB bands and +24 dB output gain (static worst case
        // ~1e6 on this noise), so its bound only catches blow-ups; the others stay near unity gain.
        const double bound = type == "eq" ? 1e4 : 100.0;
        check(allFinite(a) && maxAbs(a) < bound, type + ": random automation keeps output finite/bounded", maxAbs(a));
        check(a.l == b.l && a.r == b.r, type + ": deterministic (bit-identical reruns)");
        const Stereo c = render(false, false), d = render(false, true);
        check(c.l == d.l && c.r == d.r, type + ": output independent of block sizes");
    }
}

// Other sample rates: every type stays finite; key behaviours hold at 44.1 and 96 kHz.
void testSampleRates() {
    std::printf("\n== 44.1 kHz and 96 kHz ==\n");
    for (double fs : {44100.0, 96000.0}) {
        const std::string tag = std::to_string(static_cast<int>(fs)) + " Hz: ";
        bool finite = true;
        for (const auto& type : as::dynamicsEffectTypes()) {
            auto fx = make(type, json::object(), 120.0, fs);
            Stereo s = noise(static_cast<std::size_t>(fs / 2), 0.9, 40);
            Stereo key = noise(static_cast<std::size_t>(fs / 2), 0.9, 41);
            run(*fx, s, as::dynamicsEffectAcceptsSidechain(type) ? &key : nullptr);
            finite = finite && allFinite(s) && maxAbs(s) < 10.0;
        }
        check(finite, tag + "all types finite and bounded on loud noise");
        {
            auto fx = make("eq", {{"peak2.freq", 1000}, {"peak2.gain", 6}}, 120.0, fs);
            const std::size_t n = static_cast<std::size_t>(fs);
            Stereo s(n);
            for (std::size_t i = 0; i < n; ++i) s.l[i] = s.r[i] = static_cast<float>(0.1 * std::sin(2 * kPi * 1000 * i / fs));
            run(*fx, s);
            double re = 0, im = 0;
            for (std::size_t i = n / 2; i < n; ++i) {
                re += s.l[i] * std::cos(2 * kPi * 1000 * i / fs);
                im += s.l[i] * std::sin(2 * kPi * 1000 * i / fs);
            }
            const double g = db(2.0 * std::sqrt(re * re + im * im) / static_cast<double>(n / 2) / 0.1);
            check(std::fabs(g - 6.0) < 0.1, tag + "eq peak +6 dB at 1 kHz", g);
        }
        {
            auto fx = make("limiter", {{"gain", 12}}, 120.0, fs);
            Stereo s = noise(static_cast<std::size_t>(fs / 2), 1.0, 42);
            run(*fx, s);
            const double lat = fx->latencySamples();
            check(maxAbs(s) <= std::pow(10.0, -0.05) * (1 + 1e-6) && std::lround(lat) == std::lround(0.005 * fs) + 48,
                  tag + "limiter sample peak <= -1 dBFS, latency = 5 ms + 48", lat);
        }
        {   // inter-sample peaks: near-fs/4 tones whose samples miss the crests by up to 3 dB
            auto fx = make("limiter", {{"gain", 3}}, 120.0, fs);
            const std::size_t n = static_cast<std::size_t>(fs / 2);
            Stereo s(n);
            for (std::size_t i = 0; i < n; ++i) {
                const double t = static_cast<double>(i) / fs;
                s.l[i] = static_cast<float>(0.7 * std::sin(2 * kPi * fs / 4 * t + kPi / 4) + 0.3 * std::sin(2 * kPi * 0.23 * fs * t));
                s.r[i] = static_cast<float>(0.9 * std::sin(2 * kPi * 0.2 * fs * t + 1.0));
            }
            run(*fx, s);
            const double tp = db(std::max(truePeak(s.l, 0, n), truePeak(s.r, 0, n)));
            check(tp <= -0.9, tag + "limiter true peak <= ceiling + 0.1 dB on inter-sample-peak tones (dBTP)", tp);
        }
    }
}

}  // namespace

int main() {
    testFactoryAndSpecs();
    testEq();
    testFilter();
    testCompressor();
    testDucker();
    testSaturator();
    testLimiter();
    testWidth();
    testBitcrushUtility();
    testAllTypesRobust();
    testSampleRates();
    std::printf("\n%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
