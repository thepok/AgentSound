// Tests for the time-based & modulation effects (engine/fx/TimeFx*.cpp, engine/fx/FormantFx.cpp):
// chorus, flanger, phaser, delay, reverb, gatedreverb, tremolo, ensemble, vowel, wah (engine/fx/WahFx.cpp).
// Deterministic; prints every check; returns nonzero on failure.

#include "dsp/Dsp.h"
#include "fx/TimeFx.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstring>
#include <functional>
#include <numeric>
#include <string>
#include <vector>

using namespace as;

namespace {

int g_fail = 0, g_checks = 0;

void check(bool ok, const std::string& what) {
    ++g_checks;
    if (!ok) ++g_fail;
    std::printf("  [%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
}

std::string fmt(const char* f, double a = 0, double b = 0, double c = 0, double d = 0) {
    char buf[512];
    std::snprintf(buf, sizeof buf, f, a, b, c, d);
    return buf;
}

constexpr double kSr = 48000.0;

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
    std::size_t size() const { return l.size(); }
};

std::unique_ptr<Effect> make(const char* type, const json& p, double sr = kSr, double bpm = 120.0, std::uint64_t seed = 1) {
    auto fx = createTimeEffect(type);
    if (!fx) return nullptr;
    fx->configure(p);
    RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.bpm = bpm;
    ctx.seed = seed;
    fx->prepare(ctx);
    return fx;
}

// Runs the whole buffer through fx in blocks; perBlock(frameIndex) is called before each block.
void run(Effect& fx, Stereo& s, int block = 256, const std::function<void(std::size_t)>& perBlock = {},
         const Stereo* sc = nullptr) {
    for (std::size_t i = 0; i < s.size(); i += static_cast<std::size_t>(block)) {
        const int n = static_cast<int>(std::min<std::size_t>(static_cast<std::size_t>(block), s.size() - i));
        if (perBlock) perBlock(i);
        fx.process(s.l.data() + i, s.r.data() + i, n, sc ? sc->l.data() + i : nullptr, sc ? sc->r.data() + i : nullptr);
    }
}

Stereo noise(std::size_t n, float amp, std::uint64_t seed, bool mono = true) {
    Stereo s(n);
    dsp::Rng rng(seed);
    for (std::size_t i = 0; i < n; ++i) {
        s.l[i] = amp * rng.bipolar() * 1.7320508f;  // RMS = amp
        s.r[i] = mono ? s.l[i] : amp * rng.bipolar() * 1.7320508f;
    }
    return s;
}

// Pink noise (Kellet's filter), independent channels, RMS = amp.
Stereo pinkNoise(std::size_t n, float amp, std::uint64_t seed) {
    Stereo s(n);
    dsp::Rng rng(seed);
    for (int ch = 0; ch < 2; ++ch) {
        std::vector<float>& x = ch ? s.r : s.l;
        float b0 = 0, b1 = 0, b2 = 0;
        for (std::size_t i = 0; i < n; ++i) {
            const float w = rng.bipolar();
            b0 = 0.99765f * b0 + w * 0.0990460f;
            b1 = 0.96300f * b1 + w * 0.2965164f;
            b2 = 0.57000f * b2 + w * 1.0526913f;
            x[i] = b0 + b1 + b2 + w * 0.1848f;
        }
        double e = 0.0;
        for (float v : x) e += double(v) * v;
        const float g = amp / static_cast<float>(std::sqrt(e / static_cast<double>(n)));
        for (float& v : x) v *= g;
    }
    return s;
}

// Input for the "typical level" checks: white noise, except for the vowel filter, a formant bank
// normalised for musical (saw-like, falling) spectra, which removes most of white noise's top octaves
// (half of them at 96 kHz): it gets pink noise.
Stereo levelTestInput(const std::string& type, std::size_t n, float amp, std::uint64_t seed) {
    return type == "vowel" || type == "wah" ? pinkNoise(n, amp, seed) : noise(n, amp, seed, false);
}

Stereo sine(std::size_t n, double hz, float amp) {
    Stereo s(n);
    for (std::size_t i = 0; i < n; ++i) s.l[i] = s.r[i] = amp * static_cast<float>(std::sin(dsp::kTwoPi * hz * i / kSr));
    return s;
}

double rms(const std::vector<float>& x, std::size_t a, std::size_t b) {
    b = std::min(b, x.size());
    if (b <= a) return 0.0;
    double e = 0.0;
    for (std::size_t i = a; i < b; ++i) e += static_cast<double>(x[i]) * x[i];
    return std::sqrt(e / static_cast<double>(b - a));
}
double db(double g) { return 20.0 * std::log10(std::max(g, 1e-12)); }
std::size_t sec(double s) { return static_cast<std::size_t>(std::lround(s * kSr)); }

bool allFinite(const Stereo& s, float bound = 1e30f) {
    for (std::size_t i = 0; i < s.size(); ++i)
        if (!std::isfinite(s.l[i]) || !std::isfinite(s.r[i]) || std::fabs(s.l[i]) > bound || std::fabs(s.r[i]) > bound)
            return false;
    return true;
}
float maxAbs(const std::vector<float>& x, std::size_t a = 0, std::size_t b = ~std::size_t{0}) {
    float m = 0.0f;
    for (std::size_t i = a; i < std::min(b, x.size()); ++i) m = std::max(m, std::fabs(x[i]));
    return m;
}
float maxJump(const std::vector<float>& x, std::size_t a, std::size_t b) {
    float m = 0.0f;
    for (std::size_t i = std::max<std::size_t>(a, 1); i < std::min(b, x.size()); ++i) m = std::max(m, std::fabs(x[i] - x[i - 1]));
    return m;
}

// RT60 from Schroeder backward integration, linear fit of the EDC between -5 dB and `lowDb`.
double schroederRt60(const std::vector<float>& h, double lowDb) {
    std::vector<double> edc(h.size() + 1, 0.0);
    for (std::size_t i = h.size(); i-- > 0;) edc[i] = edc[i + 1] + static_cast<double>(h[i]) * h[i];
    const double e0 = edc[0];
    std::size_t a = 0, b = 0;
    for (std::size_t i = 0; i < h.size(); ++i) {
        const double d = 10.0 * std::log10(edc[i] / e0 + 1e-300);
        if (!a && d <= -5.0) a = i;
        if (d <= lowDb) { b = i; break; }
    }
    if (!a || b <= a + 10) return -1.0;
    double sx = 0, sy = 0, sxx = 0, sxy = 0;
    const double n = static_cast<double>(b - a);
    for (std::size_t i = a; i < b; ++i) {
        const double x = static_cast<double>(i), y = 10.0 * std::log10(edc[i] / e0);
        sx += x; sy += y; sxx += x * x; sxy += x * y;
    }
    const double slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);  // dB per sample
    return -60.0 / slope / kSr;
}

std::vector<float> bandpass(const std::vector<float>& x, double hz) {
    dsp::Biquad bp;
    bp.set(dsp::Biquad::Type::BandPass, kSr, hz, 1.41);
    std::vector<float> y(x.size());
    for (std::size_t i = 0; i < x.size(); ++i) y[i] = bp.process(x[i]);
    return y;
}

Stereo impulse(std::size_t n, std::size_t at = 0, float amp = 1.0f) {
    Stereo s(n);
    s.l[at] = s.r[at] = amp;
    return s;
}

// ---------------------------------------------------------------------------------------------

void testFactory() {
    std::printf("factory & param specs\n");
    const auto types = timeEffectTypes();
    check(types.size() == 11, "11 time effect types");
    check(createTimeEffect("nope") == nullptr, "unknown type -> nullptr");
    check(createTimeEffect("compressor") == nullptr, "foreign type -> nullptr");
    for (const auto& t : types) {
        auto fx = createTimeEffect(t);
        check(fx != nullptr, "create '" + t + "'");
        if (!fx) continue;
        bool specsOk = !fx->paramSpecs().empty();
        for (const auto& s : fx->paramSpecs())
            specsOk = specsOk && !s.help.empty() && s.min <= s.def && s.def <= s.max && !s.name.empty();
        check(specsOk, "'" + t + "' specs have help and valid ranges");
        bool threwUnknown = false, threwRange = false, threwType = false;
        try { createTimeEffect(t)->configure(json{{"bogus", 1}}); } catch (const ConfigError&) { threwUnknown = true; }
        const char* level = t == "tremolo" ? "depth" : "mix";
        try { createTimeEffect(t)->configure(json{{level, 7}}); } catch (const ConfigError&) { threwRange = true; }
        try { createTimeEffect(t)->configure(json{{fx->paramSpecs()[1].name, "loud"}}); } catch (const ConfigError&) { threwType = true; }
        check(threwUnknown, "'" + t + "' rejects unknown key");
        check(threwRange, "'" + t + "' rejects out-of-range " + level);
        check(threwType, "'" + t + "' rejects wrong type");
        check(fx->setParam("definitely_not_a_param", 1.0f) == false, "'" + t + "' setParam unknown -> false");
    }
    auto rv = createTimeEffect("reverb");
    bool ok = true;
    try { rv->configure(json{{"type", "plate"}, {"decay", 3.0}}); } catch (...) { ok = false; }
    check(ok, "reverb accepts type=plate + override");
    bool threw = false;
    try { createTimeEffect("reverb")->configure(json{{"type", "garage"}}); } catch (const ConfigError&) { threw = true; }
    check(threw, "reverb rejects unknown type choice");
    check(rv->setParam("size", 0.5f) == false, "reverb size is not automatable");
    check(rv->setParam("decay", 2.0f) == true, "reverb decay is automatable");
}

void testPingPong(const json& base);

void testDelay() {
    std::printf("delay\n");
    const json base = {{"mix", 1.0}, {"feedback", 0.5}, {"highcut", 20000}, {"lowcut", 20}, {"time", 0.5}};
    {
        auto fx = make("delay", base);
        Stereo s = impulse(sec(1.0));
        run(*fx, s);
        const std::size_t p = 12000;  // 0.5 beat at 120 bpm, 48 kHz
        check(std::fabs(s.l[p] - 1.0f) < 1e-5f && std::fabs(s.r[p] - 1.0f) < 1e-5f, fmt("echo 1 exactly at 12000 samples (%.6f)", s.l[p]));
        check(std::fabs(s.l[2 * p] - 0.5f) < 1e-5f, fmt("echo 2 at 24000, level 0.5 (%.6f)", s.l[2 * p]));
        check(std::fabs(s.l[3 * p] - 0.25f) < 1e-5f, fmt("echo 3 at 36000, level 0.25 (%.6f)", s.l[3 * p]));
        float stray = 0.0f;
        for (std::size_t i = 0; i < s.size(); ++i)
            if (i != p && i != 2 * p && i != 3 * p) stray = std::max(stray, std::fabs(s.l[i]));
        check(stray < 1e-6f, fmt("no energy between echoes (max %.2e)", stray));
        check(std::fabs(fx->tailSeconds() - 0.25 * (1.0 + 3.0 / std::log10(2.0))) < 0.05, fmt("tailSeconds from feedback (%.3f s)", fx->tailSeconds()));
    }
    {
        json p = base;
        p["mode"] = "pingpong";
        p["balanced"] = false;
        auto fx = make("delay", p);
        Stereo s = impulse(sec(1.0));
        run(*fx, s);
        const bool alt = std::fabs(s.l[12000] - 1.0f) < 1e-5f && std::fabs(s.r[12000]) < 1e-6f &&
                         std::fabs(s.r[24000] - 0.5f) < 1e-5f && std::fabs(s.l[24000]) < 1e-6f &&
                         std::fabs(s.l[36000] - 0.25f) < 1e-5f && std::fabs(s.r[36000]) < 1e-6f;
        check(alt, fmt("classic pingpong alternates L(1.0) R(%.3f) L(%.3f)", s.r[24000], s.l[36000]));
        p["start"] = "right";  // the exact mirror image
        auto fr = make("delay", p);
        Stereo m = impulse(sec(1.0));
        run(*fr, m);
        float diff = 0.0f;
        for (std::size_t i = 0; i < s.size(); ++i) diff = std::max({diff, std::fabs(m.l[i] - s.r[i]), std::fabs(m.r[i] - s.l[i])});
        check(diff == 0.0f && std::fabs(m.r[12000] - 1.0f) < 1e-5f, fmt("classic pingpong start=right mirrors start=left exactly (max diff %.1e)", diff));
    }
    testPingPong(base);
    {
        json p = base;
        p["sync"] = false;
        p["timems"] = 100;
        p["offset"] = 50;
        auto fx = make("delay", p);
        Stereo s = impulse(sec(0.5));
        run(*fx, s);
        check(std::fabs(s.l[4800] - 1.0f) < 1e-5f && std::fabs(s.r[7200] - 1.0f) < 1e-5f,
              "ms mode: left 100 ms = 4800, right +50 % = 7200 samples");
    }
    {
        auto fx = make("delay", {{"mix", 1.0}, {"feedback", 0.0}, {"highcut", 20000}, {"lowcut", 20}, {"time", 0.75}}, kSr, 100.0);
        Stereo s = impulse(sec(1.0));
        run(*fx, s);
        check(std::fabs(s.l[21600] - 1.0f) < 1e-5f, "dotted 1/8 at 100 bpm = 21600 samples");
    }
    {  // default filters darken each repeat
        auto fx = make("delay", {{"mix", 1.0}, {"feedback", 0.7}, {"time", 0.25}});
        Stereo s = impulse(sec(1.0));
        run(*fx, s);
        const double e1 = rms(s.l, 6000 - 50, 6000 + 400), e3 = rms(s.l, 18000 - 50, 18000 + 400);
        check(e3 < e1 * 0.7 * 0.7, fmt("echo-path filters: repeat 3 below 0.49 x repeat 1 (%.3f)", e3 / e1));
    }
    {  // runaway feedback stays bounded
        auto fx = make("delay", {{"mix", 1.0}, {"feedback", 1.1}, {"time", 0.125}, {"highcut", 20000}, {"lowcut", 20}});
        Stereo s = noise(sec(10.0), 0.5f, 7);
        run(*fx, s);
        check(allFinite(s, 4.0f), fmt("feedback 1.1 with loud noise: finite and bounded (peak %.2f)", maxAbs(s.l)));
    }
    for (const char* mode : {"stereo", "pingpong"}) {  // time automation glides without clicks
        auto mk = [&] { return make("delay", {{"mode", mode}, {"mix", 1.0}, {"feedback", 0.3}, {"time", 0.5}, {"wow", 0.3}, {"flutter", 0.3}}); };
        Stereo ref = sine(sec(4.0), 220.0, 0.5f);
        auto fx0 = mk();
        run(*fx0, ref, 32);
        const float refJump = std::max(maxJump(ref.l, sec(1.0), ref.size()), maxJump(ref.r, sec(1.0), ref.size()));
        Stereo s = sine(sec(4.0), 220.0, 0.5f);
        auto fx = mk();
        run(*fx, s, 32, [&](std::size_t i) {
            const double t = i / kSr;
            float v = 0.5f;
            if (t >= 1.0 && t < 2.0) v = 0.25f;
            else if (t >= 2.0 && t < 3.0) v = static_cast<float>(0.25 + 0.5 * (t - 2.0));  // ramp
            else if (t >= 3.0) v = 1.5f;
            fx->setParam("time", v);
        });
        const float jump = std::max(maxJump(s.l, sec(0.9), s.size()), maxJump(s.r, sec(0.9), s.size()));
        check(allFinite(s) && jump < 4.0f * refJump && jump < 0.12f,
              std::string(mode) + fmt(": delay-time automation: max step %.4f (static %.4f), no discontinuity", jump, refJump));
    }
    {  // a fast time ramp (dub delay throw: 400 -> 100 ms in 0.3 s, a new value every 32 samples) is one
       // continuous tape glide (a Doppler-shifted sine of steady level), not a chain of head crossfades
        auto fx = make("delay", {{"mix", 1.0}, {"feedback", 0.0}, {"highcut", 20000}, {"lowcut", 20}, {"sync", false}, {"timems", 400}});
        Stereo s = sine(sec(2.0), 1000.0, 0.3f);
        const std::size_t a = sec(0.5), b = sec(0.8);
        run(*fx, s, 32, [&](std::size_t i) {
            if (i >= a && i <= b) fx->setParam("timems", static_cast<float>(400.0 - 300.0 * double(i - a) / double(b - a)));
        });
        double lo = 1e9, hi = 0.0;
        for (std::size_t w = a + sec(0.2); w + 96 < b + sec(0.2); w += 48) {
            const double r = rms(s.l, w, w + 96);
            lo = std::min(lo, r);
            hi = std::max(hi, r);
        }
        check(allFinite(s) && db(hi / lo) < 1.0, fmt("fast delay-time ramp glides: level ripple %.2f dB during the sweep", db(hi / lo)));
    }
    {  // ducking
        auto mk = [&](double duck) { return make("delay", {{"mix", 1.0}, {"feedback", 0.5}, {"time", 0.25}, {"duck", duck}}); };
        Stereo a = noise(sec(2.0), 0.2f, 3), b = a;
        for (std::size_t i = sec(1.0); i < a.size(); ++i) a.l[i] = a.r[i] = b.l[i] = b.r[i] = 0.0f;
        auto f0 = mk(0.0), f1 = mk(1.0);
        run(*f0, a);
        run(*f1, b);
        const double during0 = rms(a.l, sec(0.5), sec(1.0)), during1 = rms(b.l, sec(0.5), sec(1.0));
        const double after0 = rms(a.l, sec(1.4), sec(1.7)), after1 = rms(b.l, sec(1.4), sec(1.7));
        check(db(during1 / during0) < -15.0, fmt("duck=1 lowers echoes under the input by %.1f dB", db(during1 / during0)));
        check(std::fabs(db(after1 / after0)) < 3.0, fmt("echoes return after the input stops (%.1f dB)", db(after1 / after0)));
    }
}

// Ping-pong 'start' and 'balanced': echo times, levels and the L/R energy of the return.
void testPingPong(const json& base) {
    {  // balanced (default): repeat 1 near the centre, then start side, other side, ... (exact levels)
        json p = base;
        p["mode"] = "pingpong";
        auto fx = make("delay", p);
        Stereo s = impulse(sec(1.1));
        run(*fx, s);
        const double fb2 = 0.25;  // feedback 0.5
        const float near = static_cast<float>(std::sqrt(0.5 / (1.0 + fb2))), far = static_cast<float>(std::sqrt((0.5 + fb2) / (1.0 + fb2)));
        const bool ok = std::fabs(s.l[12000] - near) < 1e-5f && std::fabs(s.r[12000] - far) < 1e-5f &&
                        std::fabs(s.l[24000] - 0.5f) < 1e-5f && std::fabs(s.r[24000]) < 1e-6f &&
                        std::fabs(s.r[36000] - 0.25f) < 1e-5f && std::fabs(s.l[36000]) < 1e-6f &&
                        std::fabs(s.l[48000] - 0.125f) < 1e-5f && std::fabs(s.r[48000]) < 1e-6f;
        float stray = 0.0f;
        for (std::size_t i = 0; i < s.size(); ++i)
            if (i % 12000 != 0 || i == 0) stray = std::max({stray, std::fabs(s.l[i]), std::fabs(s.r[i])});
        check(ok && stray < 1e-6f, fmt("balanced pingpong: repeat 1 at 12000 L %.4f / R %.4f (near centre), then L 0.5, R 0.25, L 0.125 "
                                       "exactly on the grid (stray %.1e)", s.l[12000], s.r[12000], stray));
    }
    {  // timing unchanged: synced dotted 1/8 at 100 bpm, and offset times with start = right
        auto fx = make("delay", {{"mode", "pingpong"}, {"mix", 1.0}, {"feedback", 0.5}, {"highcut", 20000}, {"lowcut", 20}, {"time", 0.75}},
                       kSr, 100.0);
        Stereo s = impulse(sec(1.5));
        run(*fx, s);
        const bool t1 = s.l[21600] > 0.5f && s.r[21600] > 0.5f && std::fabs(s.l[43200] - 0.5f) < 1e-5f && std::fabs(s.r[64800] - 0.25f) < 1e-5f;
        auto fo = make("delay", {{"mode", "pingpong"}, {"start", "right"}, {"mix", 1.0}, {"feedback", 0.5}, {"highcut", 20000}, {"lowcut", 20},
                                 {"sync", false}, {"timems", 100}, {"offset", 50}});
        Stereo o = impulse(sec(1.5));
        run(*fo, o);  // right 150 ms = 7200: repeat 1 at 7200 (both), repeat 2 right at 14400, repeat 3 left at 14400 + 4800
        const bool t2 = o.l[7200] > 0.5f && o.r[7200] > 0.5f && std::fabs(o.r[14400] - 0.5f) < 1e-5f && std::fabs(o.l[19200] - 0.25f) < 1e-5f;
        check(t1 && t2, "balanced pingpong timing: synced dotted 1/8 at 100 bpm = 21600 samples per repeat; offset times per side");
    }
    // Energy of the return: pink noise burst, every feedback, default and open echo filters (1/32 notes:
    // 96 repeats in the 6 s render, the tail is below -80 dB at feedback 0.9).
    auto balance = [](const json& extra, double fb, bool filters) {
        json p = {{"mode", "pingpong"}, {"mix", 1.0}, {"time", 0.125}, {"feedback", fb}};
        if (!filters) { p["highcut"] = 20000; p["lowcut"] = 20; }
        for (auto it = extra.begin(); it != extra.end(); ++it) p[it.key()] = it.value();
        auto fx = make("delay", p);
        Stereo s(sec(6.0));
        dsp::Rng rng(5);
        float b0 = 0, b1 = 0, b2 = 0;  // pink (Kellet), 0.3 s
        for (std::size_t i = 0; i < sec(0.3); ++i) {
            const float w = rng.bipolar();
            b0 = 0.99765f * b0 + w * 0.0990460f;
            b1 = 0.96300f * b1 + w * 0.2965164f;
            b2 = 0.57000f * b2 + w * 1.0526913f;
            s.l[i] = s.r[i] = 0.1f * (b0 + b1 + b2 + w * 0.1848f);
        }
        run(*fx, s);
        double el = 0, er = 0;
        for (std::size_t i = 0; i < s.size(); ++i) { el += double(s.l[i]) * s.l[i]; er += double(s.r[i]) * s.r[i]; }
        return 10.0 * std::log10(el / er);
    };
    double worstBal = 0.0, worstLean = 0.0;
    bool mirror = true;
    for (const double fb : {0.2, 0.35, 0.6, 0.9})
        for (const bool filters : {true, false}) {
            const double bl = balance(json::object(), fb, filters), br = balance({{"start", "right"}}, fb, filters);
            worstBal = std::max({worstBal, std::fabs(bl), std::fabs(br)});
            const double cl = balance({{"balanced", false}}, fb, filters);  // (start=right: exact mirror, see above)
            worstLean = std::max(worstLean, std::fabs(cl - 10.0 * std::log10(1.0 / (fb * fb))));
            mirror = mirror && std::fabs(bl + br) < 0.05;
        }
    check(worstBal < 1.0, fmt("balanced pingpong: L/R echo energy within %.2f dB for feedback 0.2-0.9, start left/right, filters on/off", worstBal));
    check(worstLean < 1.0 && mirror,
          fmt("classic pingpong leans 10*log10(1/fb^2) dB towards 'start' (worst error %.2f dB); balanced start=right mirrors left", worstLean));
}

void testReverb() {
    std::printf("reverb\n");
    const json neutral = {{"mix", 1.0}, {"damping", 20000}, {"lowmult", 1.0}, {"early", 0.0},
                          {"predelay", 0}, {"lowcut", 20}, {"highcut", 20000}};
    for (const double T : {1.0, 3.0}) {
        json p = neutral;
        p["decay"] = T;
        auto fx = make("reverb", p);
        Stereo s = impulse(sec(T * 2.5 + 0.5));
        run(*fx, s);
        const double t30 = schroederRt60(s.l, -35.0), t20 = schroederRt60(s.l, -25.0);
        const double t30r = schroederRt60(s.r, -35.0);
        check(std::fabs(t30 / T - 1.0) < 0.25 && std::fabs(t30r / T - 1.0) < 0.25 && std::fabs(t20 / T - 1.0) < 0.25,
              fmt("RT60 for decay %.1f s: T30 L %.3f R %.3f, T20 %.3f", T, t30, t30r, t20));
        check(allFinite(s), "impulse response finite");
    }
    const std::pair<const char*, double> types[] = {{"hall", 2.8}, {"plate", 2.2}, {"room", 0.8}, {"chamber", 1.4}, {"cathedral", 6.0}};
    for (const auto& [type, T60] : types) {  // T60 = the preset's mid-frequency decay
        auto fx = make("reverb", {{"type", type}, {"mix", 1.0}});
        Stereo s = impulse(sec(T60 * 2.5 + 0.5));
        run(*fx, s);
        const double t1k = schroederRt60(bandpass(s.l, 1000.0), -25.0);
        const double t500 = schroederRt60(bandpass(s.l, 500.0), -25.0);
        const double t4k = schroederRt60(bandpass(s.l, 4000.0), -25.0);
        check(std::fabs(t1k / T60 - 1.0) < 0.25,
              std::string(type) + fmt(": 1 kHz band RT60 %.2f s (requested %.1f); 500 Hz %.2f s, 4 kHz %.2f s", t1k, T60, t500, t4k));

        // Density / smoothness of the tail: kurtosis of 10 ms windows (Gaussian = 3) after 100 ms,
        // L/R decorrelation, and smooth energy envelope (no flutter / isolated spikes).
        const float peak = maxAbs(s.l);
        double kSum = 0.0, kMax = 0.0;
        int kN = 0;
        double num = 0, el = 0, er = 0;
        std::vector<double> envDb;
        for (std::size_t w = sec(0.1); w + 480 < s.size(); w += 480) {
            double m2 = 0, m4 = 0;
            for (std::size_t i = w; i < w + 480; ++i) {
                const double x = s.l[i];
                m2 += x * x;
                m4 += x * x * x * x;
                num += static_cast<double>(s.l[i]) * s.r[i];
                el += x * x;
                er += static_cast<double>(s.r[i]) * s.r[i];
            }
            m2 /= 480.0;
            m4 /= 480.0;
            if (std::sqrt(m2) < peak * 1e-3) break;  // stop at -60 dB re peak
            const double k = m4 / (m2 * m2);
            kSum += k;
            kMax = std::max(kMax, k);
            ++kN;
            envDb.push_back(10.0 * std::log10(m2));
        }
        const double corr = num / std::sqrt(el * er);
        check(kN > 10 && kSum / kN < 3.6 && kMax < 6.0,
              std::string(type) + fmt(": tail dense after 100 ms: mean kurtosis %.2f, max %.2f over %.0f windows (Gaussian = 3)", kSum / kN, kMax, kN));
        check(std::fabs(corr) < 0.5, std::string(type) + fmt(": L/R tail correlation %.3f", corr));
        // envelope smoothness: residual of the 10 ms energy envelope around a linear fit
        double sx = 0, sy = 0, sxx = 0, sxy = 0;
        const double n = static_cast<double>(envDb.size());
        for (std::size_t i = 0; i < envDb.size(); ++i) { sx += i; sy += envDb[i]; sxx += double(i) * i; sxy += i * envDb[i]; }
        const double slope = (n * sxy - sx * sy) / (n * sxx - sx * sx), icpt = (sy - slope * sx) / n;
        double resid = 0.0;
        for (std::size_t i = 0; i < envDb.size(); ++i) resid = std::max(resid, std::fabs(envDb[i] - (icpt + slope * i)));
        check(resid < 6.0, std::string(type) + fmt(": tail envelope within %.1f dB of an exponential decay", resid));
        check(allFinite(s), std::string(type) + ": finite");
    }
    {  // tail decays to silence
        auto fx = make("reverb", {{"mix", 1.0}, {"decay", 1.0}});
        Stereo s = noise(sec(12.0), 0.3f, 5);
        for (std::size_t i = sec(1.0); i < s.size(); ++i) s.l[i] = s.r[i] = 0.0f;
        run(*fx, s);
        const float last = std::max(maxAbs(s.l, sec(11.0)), maxAbs(s.r, sec(11.0)));
        check(last < 1e-6f, fmt("decay 1 s: tail is silent 10 s after the input (%.2e)", last));
    }
    {  // level for typical use and wet level vs decay
        for (const char* type : {"plate", "hall", "room"}) {
            auto fx = make("reverb", {{"type", type}, {"mix", 1.0}});
            Stereo s = noise(sec(4.0), dsp::dbToGain(-18.0f), 11, false);
            run(*fx, s);
            const double lvl = db(rms(s.l, sec(2.0), sec(4.0)));
            check(lvl > -28.0 && lvl < -12.0 && maxAbs(s.l) < 0.5f,
                  std::string(type) + fmt(" 100%% wet on -18 dBFS noise: %.1f dBFS RMS, peak %.2f", lvl, maxAbs(s.l)));
        }
    }
    {  // automation: no clicks, finite
        auto fx = make("reverb", {{"mix", 0.4}});
        Stereo s = sine(sec(6.0), 330.0, 0.3f);
        Stereo ref = s;
        auto fr = make("reverb", {{"mix", 0.4}});
        run(*fr, ref, 32);
        run(*fx, s, 32, [&](std::size_t i) {
            const float t = static_cast<float>(i / kSr);
            fx->setParam("decay", 1.0f + 3.0f * t / 6.0f);
            fx->setParam("damping", 2000.0f + 2000.0f * t);
            fx->setParam("predelay", 10.0f + 20.0f * t);
            fx->setParam("mix", 0.2f + 0.1f * t);
            fx->setParam("lowcut", 100.0f + 40.0f * t);
            fx->setParam("moddepth", 0.2f + 0.1f * t);
            fx->setParam("width", 1.0f - 0.1f * t);
        });
        const float j = maxJump(s.l, sec(0.5), s.size()), jr = maxJump(ref.l, sec(0.5), ref.size());
        check(allFinite(s) && j < 2.0f * jr + 0.01f, fmt("automating decay/damping/predelay/mix: max step %.4f (static %.4f)", j, jr));
    }
}

void testGatedReverb() {
    std::printf("gatedreverb\n");
    auto fx = make("gatedreverb", {{"mix", 1.0}, {"threshold", -30}, {"hold", 250}, {"release", 30}});
    Stereo s(sec(1.5));
    dsp::Rng rng(3);
    const std::size_t hit = sec(0.1), hit2 = sec(0.9);
    for (const std::size_t h : {hit, hit2})
        for (std::size_t i = 0; i < sec(0.005); ++i) s.l[h + i] = s.r[h + i] = 0.5f * rng.bipolar();
    Stereo dry = s;
    run(*fx, s);
    const double loud = rms(s.l, hit + sec(0.03), hit + sec(0.22));
    const double late = rms(s.l, hit + sec(0.20), hit + sec(0.25));
    const double quiet = rms(s.l, hit + sec(0.285), hit + sec(0.7));  // hold 250 + release 30 ms
    check(db(loud) > -40.0, fmt("burst present: %.1f dBFS RMS", db(loud)));
    check(db(late / loud) > -10.0, fmt("burst stays up until the hold time (%.1f dB at 200-250 ms)", db(late / loud)));
    check(db(quiet / loud) < -40.0, fmt("gate closes within the release window: %.1f dB below the burst", db(quiet / loud)));
    const double second = rms(s.l, hit2 + sec(0.03), hit2 + sec(0.2));
    check(std::fabs(db(second / loud)) < 3.0, fmt("second hit retriggers the gate (%.1f dB)", db(second / loud)));
    check(allFinite(s), "finite");
    const double dryLvl = rms(dry.l, hit, hit + sec(0.005));
    std::printf("      (dry hit %.1f dBFS RMS over 5 ms, gated burst %.1f dBFS RMS)\n", db(dryLvl), db(loud));

    // sidechain key: silent key -> gate never opens
    auto fk = make("gatedreverb", {{"mix", 1.0}});
    Stereo t = dry, key(dry.size());
    run(*fk, t, 256, {}, &key);
    check(maxAbs(t.l) == 0.0f, "silent sidechain key keeps the gate shut");
}

void testChorus() {
    std::printf("chorus\n");
    for (const char* mode : {"I", "II", "I+II", "custom"}) {
        auto fx = make("chorus", {{"mode", mode}});
        Stereo in = noise(sec(4.0), 0.1f, 21);
        Stereo s = in;
        run(*fx, s);
        const double inL = rms(in.l, sec(0.2), s.size()), outL = rms(s.l, sec(0.2), s.size());
        double diff = 0.0;
        for (std::size_t i = sec(0.2); i < s.size(); ++i) diff += double(s.l[i] - s.r[i]) * (s.l[i] - s.r[i]);
        diff = std::sqrt(diff / double(s.size() - sec(0.2)));
        double wmin = 1e9, wmax = 0.0;
        for (std::size_t w = sec(0.2); w + sec(0.1) <= s.size(); w += sec(0.1)) {
            const double r = rms(s.l, w, w + sec(0.1));
            wmin = std::min(wmin, r);
            wmax = std::max(wmax, r);
        }
        check(diff > 0.1 * outL, std::string(mode) + fmt(": stereo L/R differ (side %.1f dB re out)", db(diff / outL)));
        check(std::fabs(db(outL / inL)) < 2.0, std::string(mode) + fmt(": level vs dry %.2f dB", db(outL / inL)));
        check(db(wmax / wmin) < 1.5, std::string(mode) + fmt(": no level jumps (100 ms windows within %.2f dB)", db(wmax / wmin)));
        check(allFinite(s), std::string(mode) + ": finite");
    }
    {
        auto fx = make("chorus", {{"mode", "custom"}, {"voices", 4}, {"feedback", 0.9}, {"depth", 10}, {"delay", 1}});
        Stereo s = noise(sec(3.0), 0.7f, 5);
        run(*fx, s);
        check(allFinite(s, 4.0f), "custom extreme (4 voices, feedback 0.9): finite, bounded");
    }
    {
        auto fx = make("chorus", {{"noise", 1.0}});
        Stereo s(sec(1.0));
        run(*fx, s);
        const double n = db(rms(s.l, sec(0.1), s.size()));
        check(n > -75.0 && n < -60.0, fmt("noise=1 adds BBD hiss at %.1f dBFS", n));
    }
}

void testFlangerPhaser() {
    std::printf("flanger / phaser\n");
    {  // static comb: delay 1 ms, mix 0.5 -> notch at 500 Hz, peak at 1 kHz
        auto mk = [] { return make("flanger", {{"depth", 0.0}, {"delay", 1.0}, {"feedback", 0.0}, {"mix", 0.5}}); };
        Stereo a = sine(sec(0.5), 500.0, 0.5f), b = sine(sec(0.5), 1000.0, 0.5f);
        auto f1 = mk(), f2 = mk();
        run(*f1, a);
        run(*f2, b);
        const double na = rms(a.l, sec(0.2), a.size()) / (0.5 / std::sqrt(2.0));
        const double nb = rms(b.l, sec(0.2), b.size()) / (0.5 / std::sqrt(2.0));
        check(db(na) < -30.0 && std::fabs(db(nb) - 3.01) < 0.5, fmt("flanger comb: 500 Hz notch %.1f dB, 1 kHz peak %+.2f dB", db(na), db(nb)));
    }
    {
        auto fx = make("flanger", {{"feedback", -0.95}, {"depth", 1.0}, {"rate", 5.0}, {"delay", 10}});
        Stereo s = noise(sec(3.0), 0.7f, 8);
        run(*fx, s);
        check(allFinite(s, 4.0f), fmt("flanger extreme feedback: bounded (peak %.2f)", maxAbs(s.l)));
    }
    {  // static 4-stage phaser, fc 1 kHz: notch where each stage gives -45 deg, in phase at fc
        auto mk = [] { return make("phaser", {{"stages", 4}, {"depth", 0.0}, {"feedback", 0.0}, {"centre", 1000}, {"mix", 0.5}}); };
        const double fn = std::atan(std::tan(dsp::kPi / 8.0) * std::tan(dsp::kPi * 1000.0 / kSr)) * kSr / dsp::kPi;
        Stereo a = sine(sec(0.5), fn, 0.5f), b = sine(sec(0.5), 1000.0, 0.5f);
        auto f1 = mk(), f2 = mk();
        run(*f1, a);
        run(*f2, b);
        const double na = rms(a.l, sec(0.2), a.size()) / (0.5 / std::sqrt(2.0));
        const double nb = rms(b.l, sec(0.2), b.size()) / (0.5 / std::sqrt(2.0));
        check(db(na) < -30.0 && std::fabs(db(nb) - 3.01) < 0.5,
              fmt("phaser: notch at %.1f Hz %.1f dB, in phase at centre %+.2f dB", fn, db(na), db(nb)));
    }
    {
        auto fx = make("phaser", {{"stages", 12}, {"feedback", 0.95}, {"depth", 1.0}, {"sync", true}, {"beats", 0.25}});
        Stereo s = noise(sec(3.0), 0.7f, 9);
        run(*fx, s);
        check(allFinite(s, 6.0f), fmt("phaser extreme (12 stages, fb 0.95, synced): bounded (peak %.2f)", maxAbs(s.l)));
    }
}

void testTremolo() {
    std::printf("tremolo\n");
    auto envelope = [](const std::vector<float>& x, std::size_t a, std::size_t b, double& mn, double& mx) {
        mn = 1e9;
        mx = 0;
        for (std::size_t w = a; w + 48 <= b; w += 48) {  // 1 ms peak windows on a 1 kHz sine
            const double p = maxAbs(x, w, w + 48);
            mn = std::min(mn, p);
            mx = std::max(mx, p);
        }
    };
    {
        auto fx = make("tremolo", {{"rate", 4.0}, {"depth", 0.5}});
        Stereo s = sine(sec(2.0), 1000.0, 0.5f);
        run(*fx, s);
        double mn, mx;
        envelope(s.l, sec(0.5), s.size(), mn, mx);
        check(std::fabs(mn / mx - 0.5) < 0.03, fmt("sine depth 0.5: min/max gain %.3f (expect 0.5)", mn / mx));
    }
    {
        auto fx = make("tremolo", {{"sync", true}, {"beats", 1.0}, {"depth", 1.0}, {"shape", "square"}, {"stereo", 180}});
        Stereo s = sine(sec(2.0), 1000.0, 0.5f);
        run(*fx, s);
        // period 0.5 s: left open for the first half of each beat, right (180 deg) for the second half
        const double onL = rms(s.l, sec(0.02), sec(0.22)), offL = rms(s.l, sec(0.27), sec(0.47));
        const double onR = rms(s.r, sec(0.27), sec(0.47)), offR = rms(s.r, sec(0.02), sec(0.22));
        check(db(offL / onL) < -60.0 && db(offR / onR) < -60.0,
              fmt("synced square autopan: L on-beat/off-beat %.1f dB, R inverse %.1f dB", db(offL / onL), db(offR / onR)));
        check(maxJump(s.l, 0, s.size()) < 0.1f, fmt("square edges are click-free (max step %.3f)", maxJump(s.l, 0, s.size())));
    }
}

// Magnitude (dB) of an impulse response at `hz` (DFT over the first n samples).
double magDb(const std::vector<float>& h, double hz, std::size_t n = 8192) {
    std::complex<double> acc = 0.0;
    const std::complex<double> w = std::polar(1.0, -dsp::kTwoPi * hz / kSr);
    std::complex<double> z = 1.0;
    for (std::size_t i = 0; i < std::min(n, h.size()); ++i, z *= w) acc += static_cast<double>(h[i]) * z;
    return db(std::abs(acc));
}

// PolyBLEP saw chord (minor triad, peak amplitude `amp` per voice), identical on both channels.
Stereo sawChord(std::size_t n, double root, float amp) {
    Stereo s(n);
    for (const double f0 : {root, root * 1.189207, root * 1.498307}) {
        const double inc = f0 / kSr;
        double ph = 0.0;
        for (std::size_t i = 0; i < n; ++i) {
            const float t = static_cast<float>(ph), dt = static_cast<float>(inc);
            s.l[i] += amp * (2.0f * t - 1.0f - dsp::polyBlep(t, dt));
            ph += inc;
            if (ph >= 1.0) ph -= 1.0;
        }
    }
    s.r = s.l;
    return s;
}

void testVowel() {
    std::printf("vowel\n");
    auto response = [](const json& p) {
        auto fx = make("vowel", p);
        Stereo s = impulse(8192);
        run(*fx, s);
        return s.l;
    };
    // A local maximum of the response within 5 % of a table formant (the highest one there). With
    // `prominence`, it must also stand 3 dB above the response 12 % either side (F1, F2; F3 sits in the
    // F3-F5 'singer's formant' cluster, where neighbouring peaks are only slightly separated).
    auto peakNear = [](const std::vector<float>& h, double target, double& found, bool prominence = true) {
        std::vector<double> f, m;
        for (double x = target * 0.95; x <= target * 1.05; x *= 1.001) {
            f.push_back(x);
            m.push_back(magDb(h, x));
        }
        double best = -1e9;
        for (std::size_t i = 1; i + 1 < f.size(); ++i)
            if (m[i] > m[i - 1] && m[i] >= m[i + 1] && m[i] > best) { best = m[i]; found = f[i]; }
        if (best < -1e8) return false;
        return !prominence || (best > magDb(h, target * 0.88) + 3.0 && best > magDb(h, target * 1.12) + 3.0);
    };
    const char* vowels[5] = {"a", "e", "i", "o", "u"};
    const double table[5][3] = {{650, 1080, 2650}, {400, 1700, 2600}, {290, 1870, 2800}, {400, 800, 2600}, {350, 600, 2700}};
    for (int v = 0; v < 5; ++v) {
        const auto h = response({{"vowel", vowels[v]}});
        double f[3] = {0, 0, 0};
        bool ok = true;
        for (int k = 0; k < 3; ++k) ok = peakNear(h, table[v][k], f[k], k < 2) && ok;
        check(ok, std::string("vowel ") + vowels[v] + fmt(": formant peaks at %.0f / %.0f / %.0f Hz", f[0], f[1], f[2]) +
                      fmt(" (table %.0f / %.0f / %.0f)", table[v][0], table[v][1], table[v][2]));
    }
    {
        const auto h = response({{"vowel", "a"}});
        double f1 = 0, f2 = 0, f3 = 0;
        const bool ok = peakNear(h, 650, f1) && peakNear(h, 1080, f2) && peakNear(h, 2650, f3, false) && f1 > 600 && f1 < 750 &&
                        f2 > 1000 && f2 < 1200 && f3 > 2450 && f3 < 2850;
        check(ok, fmt("male 'a' ~ 700 / 1100 / 2600 Hz: %.0f / %.0f / %.0f", f1, f2, f3));
        // the vowel shape: F2 well above the F2-F3 valley, the singer's formant well above the top
        const double valley = magDb(h, 1850), top = magDb(h, 6000);
        check(magDb(h, f2) > valley + 15.0 && magDb(h, f3) > top + 10.0,
              fmt("'a': F2 %.1f dB over the F2-F3 valley, F3 %.1f dB over 6 kHz", magDb(h, f2) - valley, magDb(h, f3) - top));
    }
    {  // presence moves the singer's formant (F3) against F1: +-9 dB from the default
        auto f3re1 = [&](double presence) {
            const auto h = response({{"vowel", "a"}, {"presence", presence}});
            double f1 = 650, f3 = 2650;
            peakNear(h, 650, f1);
            peakNear(h, 2650, f3, false);
            return magDb(h, f3) - magDb(h, f1);
        };
        const double lo = f3re1(0.0), mid = f3re1(0.5), hi = f3re1(1.0);
        check(std::fabs(hi - mid - 9.0) < 1.5 && std::fabs(mid - lo - 9.0) < 1.5,
              fmt("presence 0 / 0.5 / 1: F3 at %+.1f / %+.1f / %+.1f dB re F1 (filter response)", lo, mid, hi));
    }
    {  // gender shifts every formant (female 0.4 = x 2^0.2)
        const auto h = response({{"vowel", "a"}, {"gender", 0.4}});
        double f1 = 0, f2 = 0;
        const double k = std::exp2(0.2);
        const bool ok = peakNear(h, 650 * k, f1) && peakNear(h, 1080 * k, f2) && std::fabs(f1 / (650 * k) - 1) < 0.05 &&
                        std::fabs(f2 / (1080 * k) - 1) < 0.05;
        check(ok, fmt("gender 0.4: 'a' formants move up x%.3f to %.0f / %.0f Hz", k, f1, f2));
    }
    {  // resonance narrows / widens the formants: -3 dB width of F2 of 'a'
        auto width = [&](double res) {
            const auto h = response({{"vowel", "a"}, {"resonance", res}});
            double fp = 1080.0;
            peakNear(h, 1080, fp);
            const double top = magDb(h, fp);
            double lo = fp, hi = fp;
            while (lo > 700 && magDb(h, lo) > top - 3.0) lo *= 0.998;
            while (hi < 1600 && magDb(h, hi) > top - 3.0) hi *= 1.002;
            return hi - lo;
        };
        const double w0 = width(0.25), w5 = width(0.5), w1 = width(1.0);
        check(w1 < 0.5 * w5 && w5 < 0.8 * w0 && w5 > 50 && w5 < 150,
              fmt("resonance: F2 bandwidth %.0f Hz at 0.25, %.0f at 0.5 (table 90), %.0f at 1", w0, w5, w1));
    }
    {  // morph: vowel + morph lands exactly on the table vowels (cyclic), and is continuous in between
        auto render = [](const json& p) {
            auto fx = make("vowel", p);
            Stereo s = sawChord(sec(0.25), 110.0, 0.1f);
            run(*fx, s);
            return s;
        };
        const Stereo e = render({{"vowel", "e"}}), ae = render({{"vowel", "a"}, {"morph", 1.0}});
        const Stereo u = render({{"vowel", "u"}}), au = render({{"vowel", "a"}, {"morph", 4.0}});
        const Stereo a = render({{"vowel", "a"}}), ua = render({{"vowel", "u"}, {"morph", 1.0}});
        check(e.l == ae.l && u.l == au.l && a.l == ua.l, "morph: a+1 = e, a+4 = u, u+1 = a (wraps), bit-identical");
        // Continuity: the largest response change between neighbouring morph values halves when the step
        // halves (a jump anywhere in 0..4 would not shrink).
        const double probes[] = {250, 400, 600, 800, 1100, 1500, 1900, 2300, 2700, 3200, 4000};
        auto worstStep = [&](int steps) {
            std::vector<double> prev;
            double worst = 0.0;
            for (int k = 0; k <= steps; ++k) {
                auto fx = make("vowel", {{"vowel", "a"}, {"morph", 4.0 * k / steps}});
                Stereo s = impulse(8192);
                run(*fx, s);
                std::vector<double> cur;
                for (double f : probes) cur.push_back(magDb(s.l, f, 8192));
                if (!prev.empty())
                    for (std::size_t i = 0; i < cur.size(); ++i) worst = std::max(worst, std::fabs(cur[i] - prev[i]));
                prev = cur;
            }
            return worst;
        };
        const double w1 = worstStep(200), w2 = worstStep(400);
        check(w1 < 5.0 && w2 < 0.6 * w1,
              fmt("morph 0..4 is continuous: max response change %.2f dB per 0.02 step, %.2f dB per 0.01 step (11 frequencies)", w1, w2));
    }
    {  // fast vowel sweep from a modulator (4 Hz, 0..4, set every 32 samples): smooth, no clicks
        auto sweep = [](bool moving, float fixedMorph) {
            auto fx = make("vowel", {{"vowel", "a"}});
            Stereo s = sawChord(sec(1.5), 110.0, 0.1f);
            run(*fx, s, 32, [&](std::size_t i) {
                fx->setParam("morph", moving ? static_cast<float>(2.0 - 2.0 * std::cos(dsp::kTwoPi * 4.0 * i / kSr)) : fixedMorph);
            });
            return s;
        };
        const Stereo sw = sweep(true, 0.0f);
        float ref = 0.0f;
        for (float m : {0.0f, 1.0f, 2.0f, 3.0f, 4.0f}) {
            const Stereo st = sweep(false, m);
            ref = std::max(ref, maxJump(st.l, sec(0.2), st.size()));
        }
        const float j = maxJump(sw.l, sec(0.2), sw.size());
        check(allFinite(sw) && j < 1.5f * ref, fmt("4 Hz vowel sweep: max sample step %.4f (static vowels up to %.4f)", j, ref));
    }
    {  // a saw pad keeps its level: every vowel, averaged over four chords, within 2 dB; single chords
       // within 5 dB (a formant bank passes whichever harmonics sit near the formants)
        double worstMean = 0.0, worstOne = 0.0;
        std::string detail;
        for (const char* v : vowels) {
            double mean = 0.0;
            for (const double root : {110.0, 131.0, 165.0, 196.0}) {
                auto fx = make("vowel", {{"vowel", v}});
                Stereo s = sawChord(sec(0.5), root, 0.1f);
                const double in = rms(s.l, sec(0.2), s.size());
                run(*fx, s);
                const double g = db(rms(s.l, sec(0.2), s.size()) / in);
                worstOne = std::max(worstOne, std::fabs(g));
                mean += g / 4.0;
            }
            worstMean = std::max(worstMean, std::fabs(mean));
            detail += fmt(" %+.1f", mean);
        }
        check(worstMean < 2.0 && worstOne < 5.0,
              "saw chords keep their level through the vowels (a e i o u:" + detail + fmt(" dB; single chords within %.1f dB)", worstOne));
    }
    {
        auto fx = make("vowel", {{"vowel", "o"}, {"mix", 0.0}});
        Stereo in = noise(sec(0.5), 0.2f, 3, false), s = in;
        run(*fx, s);
        check(s.l == in.l && s.r == in.r, "mix 0 = dry, bit-exact");
    }
}

void testEnsemble() {
    std::printf("ensemble\n");
    {  // the three voices' delays are 120 degrees apart: their sum keeps a steady phase (a 50 Hz sine shows
       // no pitch wobble in the mono sum), while each side alone is a chorus
        auto zeroCrossWobble = [](const std::vector<float>& x) {
            std::vector<double> zc;
            for (std::size_t i = sec(0.3); i < x.size(); ++i)
                if (x[i - 1] < 0.0f && x[i] >= 0.0f) zc.push_back(static_cast<double>(i - 1) + x[i - 1] / (x[i - 1] - x[i]));
            double sx = 0, sy = 0, sxx = 0, sxy = 0;
            const double n = static_cast<double>(zc.size());
            for (std::size_t k = 0; k < zc.size(); ++k) {
                const double kk = static_cast<double>(k);
                sx += kk; sy += zc[k]; sxx += kk * kk; sxy += kk * zc[k];
            }
            const double slope = (n * sxy - sx * sy) / (n * sxx - sx * sx), icpt = (sy - slope * sx) / n;
            double dev = 0.0;
            for (std::size_t k = 0; k < zc.size(); ++k) dev = std::max(dev, std::fabs(zc[k] - (icpt + slope * static_cast<double>(k))));
            return dev / kSr * 1000.0;  // ms
        };
        // (the residue of the sum is third order: 2 J3(wA) / J0(wA) rad for a sweep of +-A seconds)
        auto mk = [](double spread) {
            return make("ensemble", {{"mix", 1.0}, {"spread", spread}, {"shimmer", 0.0}, {"tone", 20000}, {"lowcut", 20}});
        };
        Stereo mono = sine(sec(4.0), 50.0, 0.5f), wide = mono;
        auto f0 = mk(0.0), f1 = mk(1.0);
        run(*f0, mono);
        run(*f1, wide);
        const double sumWobble = zeroCrossWobble(mono.l), sideWobble = zeroCrossWobble(wide.l);
        check(sideWobble > 0.3 && sumWobble < 0.1 * sideWobble,
              fmt("3-phase: mono sum phase wobble %.3f ms vs one side %.2f ms (50 Hz, default depth)", sumWobble, sideWobble));
        check(mono.l == mono.r, "spread 0: mono ensemble (L = R)");
    }
    {
        auto fx = make("ensemble", {{"mix", 1.0}, {"tone", 20000}});
        Stereo in = noise(sec(4.0), 0.1f, 21), s = in;
        run(*fx, s);
        double c = 0.0, el = 0.0, er = 0.0, wmin = 1e9, wmax = 0.0;
        for (std::size_t i = sec(0.2); i < s.size(); ++i) {
            c += double(s.l[i]) * s.r[i];
            el += double(s.l[i]) * s.l[i];
            er += double(s.r[i]) * s.r[i];
        }
        for (std::size_t w = sec(0.2); w + sec(0.1) <= s.size(); w += sec(0.1)) {
            const double r = rms(s.l, w, w + sec(0.1));
            wmin = std::min(wmin, r);
            wmax = std::max(wmax, r);
        }
        const double lvl = db(rms(s.l, sec(0.2), s.size()) / rms(in.l, sec(0.2), in.size()));
        check(c / std::sqrt(el * er) < 0.5, fmt("spread 1 on a mono source: wide (L/R correlation %.2f)", c / std::sqrt(el * er)));
        check(std::fabs(lvl) < 1.5 && db(wmax / wmin) < 1.5, fmt("wet level %.2f dB vs dry, 100 ms windows within %.2f dB", lvl, db(wmax / wmin)));
    }
    {  // defaults: classic dry/wet balance, dark wet signal
        auto fx = make("ensemble", json::object());
        Stereo s = noise(sec(2.0), 0.1f, 22), in = s;
        run(*fx, s);
        const double lvl = db(rms(s.l, sec(0.2), s.size()) / rms(in.l, sec(0.2), in.size()));
        check(lvl > -4.0 && lvl < 1.0 && allFinite(s), fmt("defaults on noise: %.2f dB", lvl));
    }
    {  // bass: without the split, the coherent low end of the voices combs against the dry signal ~5.5 ms
       // earlier (a notch near 90 Hz, the sides half out of phase); 'lowcut' keeps it out of the ensemble:
       // the lows stay centred and at unity (also at mix 1), the response stays flat
        auto sweep = [](const json& p, double lo, double hi, double& worstDb, double& worstCorr) {
            worstDb = 0.0;
            worstCorr = 1.0;
            for (double hz = lo; hz <= hi; hz *= 1.12) {
                auto fx = make("ensemble", p);
                Stereo s = sine(sec(4.0), hz, 0.3f);
                run(*fx, s);
                const double ref = 0.3 / std::sqrt(2.0);
                double c = 0.0, el = 0.0, er = 0.0;
                for (std::size_t i = sec(1.0); i < s.size(); ++i) {
                    c += double(s.l[i]) * s.r[i];
                    el += double(s.l[i]) * s.l[i];
                    er += double(s.r[i]) * s.r[i];
                }
                worstCorr = std::min(worstCorr, c / std::sqrt(el * er));
                for (const auto* ch : {&s.l, &s.r}) {
                    const double g = db(rms(*ch, sec(1.0), s.size()) / ref);
                    if (std::fabs(g) > std::fabs(worstDb)) worstDb = g;
                }
            }
        };
        double combDb = 0.0, combCorr = 0.0, bassDb = 0.0, bassCorr = 0.0, wetDb = 0.0, wetCorr = 0.0, fullDb = 0.0, fullCorr = 0.0;
        sweep({{"lowcut", 20}}, 40.0, 120.0, combDb, combCorr);
        sweep(json::object(), 30.0, 120.0, bassDb, bassCorr);
        sweep({{"mix", 1.0}}, 30.0, 60.0, wetDb, wetCorr);
        sweep(json::object(), 30.0, 3000.0, fullDb, fullCorr);
        check(std::fabs(combDb) > 4.0 && combCorr < 0.0,
              fmt("lowcut 20 (no split): bass comb, worst %+.1f dB, L/R correlation down to %.2f (40-120 Hz)", combDb, combCorr));
        check(std::fabs(bassDb) < 2.5 && bassCorr > 0.95 && std::fabs(wetDb) < 0.5 && wetCorr > 0.99,
              fmt("default lowcut 150: bass 30-120 Hz within %+.1f dB and mono (corr >= %.2f); mix 1, 30-60 Hz: %+.2f dB (dry lows)",
                  bassDb, bassCorr, wetDb));
        check(std::fabs(fullDb) < 3.0, fmt("defaults: sine response 30 Hz-3 kHz within %+.1f dB (time-averaged chorus comb)", fullDb));
    }
}

void testSampleRates() {
    std::printf("sample rates\n");
    for (const double sr : {44100.0, 96000.0}) {
        {
            auto fx = make("delay", {{"mix", 1.0}, {"feedback", 0.0}, {"highcut", 20000}, {"lowcut", 20}, {"time", 0.5}}, sr);
            Stereo s = impulse(static_cast<std::size_t>(sr * 0.5));
            run(*fx, s);
            const std::size_t p = static_cast<std::size_t>(std::lround(0.25 * sr));
            check(std::fabs(s.l[p] - 1.0f) < 1e-5f, fmt("delay 1/8 at 120 bpm lands on sample %.0f at %.0f Hz", double(p), sr));
        }
        {
            auto fx = make("reverb", {{"mix", 1.0}, {"decay", 2.0}, {"damping", 20000}, {"lowmult", 1.0}, {"early", 0.0},
                                      {"lowcut", 20}, {"highcut", 20000}}, sr);
            Stereo s = impulse(static_cast<std::size_t>(sr * 5.5));
            run(*fx, s);
            // schroederRt60 assumes kSr; rescale
            const double t30 = schroederRt60(s.l, -35.0) * kSr / sr;
            check(std::fabs(t30 / 2.0 - 1.0) < 0.25 && allFinite(s), fmt("reverb decay 2 s at %.0f Hz: T30 %.3f s", sr, t30));
        }
        for (const auto& t : timeEffectTypes()) {
            auto fx = make(t.c_str(), json::object(), sr);
            Stereo s = levelTestInput(t, static_cast<std::size_t>(sr * 2.0), dsp::dbToGain(-18.0f), 4);
            run(*fx, s);
            const double l = db(rms(s.l, s.size() / 2, s.size()));
            check(allFinite(s) && l > -24.0 && l < -13.0, t + fmt(" at %.0f Hz: finite, %.1f dBFS RMS", sr, l));
        }
    }
}

void testCommon() {
    std::printf("determinism, robustness, automation fuzz, levels, speed\n");
    for (const auto& t : timeEffectTypes()) {
        // determinism across instances, and block-size independence for static params
        auto a = make(t.c_str(), json::object(), kSr, 120.0, 42), b = make(t.c_str(), json::object(), kSr, 120.0, 42);
        Stereo x = noise(sec(2.0), 0.2f, 99, false), y = x, z = x;
        run(*a, x, 256);
        run(*b, y, 37);
        check(std::memcmp(x.l.data(), y.l.data(), x.size() * sizeof(float)) == 0 &&
                  std::memcmp(x.r.data(), y.r.data(), x.size() * sizeof(float)) == 0,
              t + ": deterministic and block-size independent");

        // extremes: every numeric param at min, then at max, with loud input
        for (int ext = 0; ext < 2; ++ext) {
            json p = json::object();
            for (const auto& s : a->paramSpecs())
                if (s.choices.empty()) p[s.name] = ext ? s.max : s.min;
            if (t == "delay") p["time"] = 0.25;  // keep the render short enough to see many repeats
            auto fx = make(t.c_str(), p);
            Stereo s = noise(sec(3.0), 0.5f, 5 + ext);
            run(*fx, s);
            check(allFinite(s, 8.0f), t + (ext ? ": all params at max" : ": all params at min") + fmt(" -> finite, peak %.2f", maxAbs(s.l)));
        }

        // automation fuzz: random in-range values for every automatable param every 32 samples
        {
            auto fx = make(t.c_str(), json::object());
            dsp::Rng rng(1234);
            std::vector<ParamSpec> specs = fx->paramSpecs();
            Stereo s = noise(sec(3.0), 0.2f, 17);
            run(*fx, s, 32, [&](std::size_t) {
                const auto& sp = specs[static_cast<std::size_t>(rng.next() % specs.size())];
                const bool accepted = fx->setParam(sp.name, sp.min + (sp.max - sp.min) * rng.uniform());
                (void)accepted;
            });
            check(allFinite(s, 8.0f), t + fmt(": automation fuzz finite (peak %.2f)", maxAbs(s.l)));
        }

        // silence in -> silence out (chorus hiss off by default)
        {
            auto fx = make(t.c_str(), json::object());
            Stereo s(sec(1.0));
            run(*fx, s);
            check(maxAbs(s.l) == 0.0f && maxAbs(s.r) == 0.0f, t + ": silence in -> exact silence out");
        }

        // typical level: -18 dBFS noise at default params
        {
            auto fx = make(t.c_str(), json::object());
            Stereo s = levelTestInput(t, sec(3.0), dsp::dbToGain(-18.0f), 4);
            run(*fx, s);
            const double l = db(rms(s.l, sec(1.0), s.size()));
            check(l > -24.0 && l < -13.0 && maxAbs(s.l) < 0.6f, t + fmt(": defaults on -18 dBFS noise -> %.1f dBFS RMS", l));
        }

        // tails reach exact digital silence (denormal-safe feedback paths) without slowing down
        {
            auto fn = make(t.c_str(), json::object()), fi = make(t.c_str(), json::object());
            Stereo busy = noise(sec(8.0), 0.2f, 2, false), tail = impulse(sec(40.0));
            for (std::size_t i = 0; i < sec(0.5); ++i) tail.l[i] = tail.r[i] = busy.l[i];
            const auto t0 = std::chrono::steady_clock::now();
            run(*fn, busy);
            const auto t1 = std::chrono::steady_clock::now();
            run(*fi, tail);
            const auto t2 = std::chrono::steady_clock::now();
            const double perBusy = std::chrono::duration<double>(t1 - t0).count() / 8.0;
            const double perTail = std::chrono::duration<double>(t2 - t1).count() / 40.0;
            const float last = std::max(maxAbs(tail.l, sec(39.0)), maxAbs(tail.r, sec(39.0)));
            check(last == 0.0f, t + fmt(": tail reaches exact silence (last second peak %.1e)", last));
            check(perTail < 3.0 * perBusy + 0.002, t + fmt(": decaying tail costs %.2fx of busy processing (no denormal stalls)", perTail / perBusy));
        }

        // speed
        {
            auto fx = make(t.c_str(), json::object());
            Stereo s = noise(sec(10.0), 0.2f, 1, false);
            const auto t0 = std::chrono::steady_clock::now();
            run(*fx, s);
            const double el = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            std::printf("      %-12s %7.1f x realtime (10 s stereo in %.3f s)\n", t.c_str(), 10.0 / el, el);
        }
    }
}

// Regression tests for defects found in review.
void testReviewFixes() {
    std::printf("review regressions\n");
    {  // sidechain support is advertised for exactly the types that use a key
        bool ok = timeEffectAcceptsSidechain("delay") && timeEffectAcceptsSidechain("gatedreverb");
        for (const char* t : {"chorus", "flanger", "phaser", "reverb", "tremolo", "ensemble", "vowel", "compressor"})
            ok = ok && !timeEffectAcceptsSidechain(t);
        check(ok, "timeEffectAcceptsSidechain: delay + gatedreverb only");
    }
    // Small spaces: every FDN loop delay (incl. the in-loop all-passes) must exceed the 32-sample
    // sub-block, else the core reads unwritten samples and stops being time-invariant. With the
    // modulation off the reverb is LTI, so an impulse 5 samples later must give the same response
    // shifted by 5 samples. (gatedreverb shares the same core and sizing.)
    for (const double sr : {44100.0, 48000.0})
        for (const double size : {0.0, 0.1, 0.3}) {
            {
                const char* type = "reverb";
                const json p = {{"mix", 1.0}, {"size", size}, {"moddepth", 0.0}, {"diffusion", 1.0}};
                const std::size_t n = static_cast<std::size_t>(sr * 1.0), shift = 5;
                auto a = make(type, p, sr), b = make(type, p, sr);
                Stereo x = impulse(n, 100), y = impulse(n, 100 + shift);
                run(*a, x);
                run(*b, y);
                float err = 0.0f;
                for (std::size_t i = 100; i + shift < n; ++i)
                    err = std::max({err, std::fabs(x.l[i] - y.l[i + shift]), std::fabs(x.r[i] - y.r[i + shift])});
                const float pk = std::max(maxAbs(x.l), 1e-9f);
                check(err <= 1e-5f * pk && pk > 1e-4f,
                      std::string(type) + fmt(" size %.1f at %.0f Hz: time-invariant (shifted-impulse error %.1e re peak)", size, sr, err / pk));
            }
        }
    {  // gatedreverb 'flat': the burst stays level through the hold instead of sagging
        auto burst = [](double flat) {
            auto fx = make("gatedreverb", {{"mix", 1.0}, {"flat", flat}, {"decay", 2.0}, {"hold", 300}});
            Stereo s(sec(0.6));
            dsp::Rng rng(1);
            for (std::size_t i = 0; i < sec(0.05); ++i) s.l[i] = s.r[i] = 0.5f * std::exp(-static_cast<float>(i) / 600.0f) * rng.bipolar();
            run(*fx, s);
            return db(rms(s.l, sec(0.25), sec(0.29)) / rms(s.l, sec(0.05), sec(0.09)));
        };
        const double sag0 = burst(0.0), sag1 = burst(1.0);
        check(sag1 > -3.5 && sag1 < 1.5 && sag0 < sag1 - 4.0,
              fmt("gatedreverb burst 250 ms vs 50 ms: flat=1 %+.1f dB, flat=0 %+.1f dB (natural decay)", sag1, sag0));
    }
    // Synced LFOs re-lock to the song grid after 'beats' automation: tremolo square gate, 1/8 notes,
    // switched to 1/16 at an off-grid moment; afterwards every 1/16 must open on the grid.
    {
        auto fx = make("tremolo", {{"sync", true}, {"beats", 0.5}, {"depth", 1.0}, {"shape", "square"}});
        Stereo s(sec(4.0));
        std::fill(s.l.begin(), s.l.end(), 0.5f);
        s.r = s.l;
        run(*fx, s, 32, [&](std::size_t i) { fx->setParam("beats", i < sec(1.37) ? 0.5f : 0.25f); });
        float worst = 0.0f;  // period 0.125 s: open ~2..60 ms after each grid point, shut ~65..123 ms
        for (int k = 0; k < 8; ++k) {
            const std::size_t g = sec(3.0 + 0.125 * k);
            worst = std::max(worst, 0.5f - s.l[g + sec(0.03)]);
            worst = std::max(worst, s.l[g + sec(0.095)]);
        }
        check(worst < 0.01f, fmt("tremolo sync re-locks to the 1/16 grid after beats automation (worst error %.3f)", worst));
    }
    {
        auto fx = make("phaser", {{"sync", true}, {"beats", 1.0}, {"depth", 1.0}, {"feedback", 0.0}, {"mix", 1.0}});
        auto ref = make("phaser", {{"sync", true}, {"beats", 0.5}, {"depth", 1.0}, {"feedback", 0.0}, {"mix", 1.0}});
        Stereo s = noise(sec(4.0), 0.1f, 12), r = s;
        run(*fx, s, 32, [&](std::size_t i) { fx->setParam("beats", i < sec(0.61) ? 1.0f : 0.5f); });
        run(*ref, r, 32);
        float err = 0.0f;
        for (std::size_t i = sec(3.0); i < s.size(); ++i) err = std::max(err, std::fabs(s.l[i] - r.l[i]));
        check(err < 0.01f, fmt("phaser sync re-locks: matches a phaser synced from the start (max diff %.4f)", err));
    }
    {  // chorus custom with depth > delay: the sweep is raised, never clipped at zero delay
        auto fx = make("chorus", {{"mode", "custom"}, {"delay", 0.5}, {"depth", 5.0}, {"voices", 1}, {"mix", 1.0}, {"rate", 0.8}, {"tone", 20000}});
        Stereo s = sine(sec(3.0), 1000.0, 0.5f);
        run(*fx, s);
        std::vector<double> zc;  // interpolated upward zero crossings
        for (std::size_t i = sec(0.5); i < s.size(); ++i)
            if (s.l[i - 1] < 0.0f && s.l[i] >= 0.0f) zc.push_back(static_cast<double>(i - 1) + s.l[i - 1] / (s.l[i - 1] - s.l[i]));
        int flat = 0;
        for (std::size_t i = 1; i < zc.size(); ++i) flat += std::fabs((zc[i] - zc[i - 1]) - 48.0) < 0.0005;
        check(zc.size() > 100 && flat < static_cast<int>(zc.size()) / 20,
              fmt("chorus depth > delay: pitch keeps moving (%.0f of %.0f periods unmodulated)", flat, double(zc.size())));
    }
    {  // phaser broadband level does not jump with feedback (like the flanger)
        auto level = [](double fb) {
            auto fx = make("phaser", {{"feedback", fb}, {"mix", 1.0}});
            Stereo s = noise(sec(3.0), 0.1f, 31);
            run(*fx, s);
            return db(rms(s.l, sec(0.5), s.size()) / 0.1);
        };
        const double l0 = level(0.0), l9 = level(0.9), lm = level(-0.9);
        check(std::fabs(l9 - l0) < 2.0 && std::fabs(lm - l0) < 2.0,
              fmt("phaser wet level vs feedback: 0 -> %+.1f dB, 0.9 -> %+.1f dB, -0.9 -> %+.1f dB", l0, l9, lm));
    }
    {  // count params must be whole numbers
        bool c = false, p = false;
        try { createTimeEffect("chorus")->configure({{"voices", 2.5}}); } catch (const ConfigError&) { c = true; }
        try { createTimeEffect("phaser")->configure({{"stages", 6.5}}); } catch (const ConfigError&) { p = true; }
        bool okInt = true;
        try { createTimeEffect("phaser")->configure({{"stages", 8}}); } catch (...) { okInt = false; }
        check(c && p && okInt, "chorus voices / phaser stages reject fractional values");
    }
    {  // phaser tail accounts for feedback resonance
        auto lo = createTimeEffect("phaser"), hi = createTimeEffect("phaser");
        lo->configure({{"feedback", 0.0}});
        hi->configure({{"feedback", 0.95}, {"centre", 200}});
        check(hi->tailSeconds() > 0.3 && lo->tailSeconds() < 0.1,
              fmt("phaser tailSeconds: %.2f s without feedback, %.2f s at feedback 0.95", lo->tailSeconds(), hi->tailSeconds()));
    }
}

}  // namespace

int main() {
    testFactory();
    testDelay();
    testReverb();
    testGatedReverb();
    testChorus();
    testFlangerPhaser();
    testTremolo();
    testVowel();
    testEnsemble();
    testSampleRates();
    testCommon();
    testReviewFixes();
    std::printf("\n%d checks, %d failed\n", g_checks, g_fail);
    return g_fail ? 1 : 0;
}
