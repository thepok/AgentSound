// Tests for the premium effects (engine/fx/Premium*.cpp): microshift, shimmer, tape, exciter.
// Deterministic; prints every check; returns nonzero on failure. (Click safety, automation response
// and preview parity of every parameter: test_param_jumps.)

#include "dsp/Dsp.h"
#include "fx/PremiumFx.h"
#include "render/Registry.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstring>
#include <functional>
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

std::string fmt(const char* f, double a = 0, double b = 0, double c = 0, double d = 0, double e = 0) {
    char buf[512];
    std::snprintf(buf, sizeof buf, f, a, b, c, d, e);
    return buf;
}

constexpr double kSr = 48000.0;

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
    std::size_t size() const { return l.size(); }
};

std::unique_ptr<Effect> make(const std::string& type, const json& p, double sr = kSr, std::uint64_t seed = 1,
                             double startBeat = 0.0) {
    auto fx = createPremiumEffect(type);
    if (!fx) return nullptr;
    fx->configure(p);
    RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.bpm = 120.0;
    ctx.seed = seed;
    ctx.startBeat = startBeat;
    fx->prepare(ctx);
    return fx;
}

void run(Effect& fx, Stereo& s, int block = 256, const std::function<void(std::size_t)>& perBlock = {}) {
    for (std::size_t i = 0; i < s.size(); i += static_cast<std::size_t>(block)) {
        const int n = static_cast<int>(std::min<std::size_t>(static_cast<std::size_t>(block), s.size() - i));
        if (perBlock) perBlock(i);
        fx.process(s.l.data() + i, s.r.data() + i, n, nullptr, nullptr);
    }
}

std::size_t sec(double s, double sr = kSr) { return static_cast<std::size_t>(std::lround(s * sr)); }
double db(double g) { return 20.0 * std::log10(std::max(g, 1e-15)); }

double rms(const std::vector<float>& x, std::size_t a, std::size_t b) {
    b = std::min(b, x.size());
    if (b <= a) return 0.0;
    double e = 0.0;
    for (std::size_t i = a; i < b; ++i) e += static_cast<double>(x[i]) * x[i];
    return std::sqrt(e / static_cast<double>(b - a));
}
float maxAbs(const std::vector<float>& x, std::size_t a = 0, std::size_t b = ~std::size_t{0}) {
    float m = 0.0f;
    for (std::size_t i = a; i < std::min(b, x.size()); ++i) m = std::max(m, std::fabs(x[i]));
    return m;
}
bool allFinite(const Stereo& s, float bound = 1e30f) {
    for (std::size_t i = 0; i < s.size(); ++i)
        if (!std::isfinite(s.l[i]) || !std::isfinite(s.r[i]) || std::fabs(s.l[i]) > bound || std::fabs(s.r[i]) > bound)
            return false;
    return true;
}
bool identical(const Stereo& a, const Stereo& b) {
    return a.size() == b.size() && std::memcmp(a.l.data(), b.l.data(), a.size() * sizeof(float)) == 0 &&
           std::memcmp(a.r.data(), b.r.data(), a.size() * sizeof(float)) == 0;
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
Stereo sine(std::size_t n, double hz, float amp, double sr = kSr) {
    Stereo s(n);
    for (std::size_t i = 0; i < n; ++i) s.l[i] = s.r[i] = amp * static_cast<float>(std::sin(dsp::kTwoPi * hz * i / sr));
    return s;
}
// Band-limited saw (additive, harmonics below 10 kHz), mono.
Stereo saw(std::size_t n, double hz, float amp) {
    Stereo s(n);
    for (int h = 1; h * hz < 10000.0; ++h) {
        const double w = dsp::kTwoPi * hz * h / kSr, a = amp * 0.55 / h;
        for (std::size_t i = 0; i < n; ++i) s.l[i] += static_cast<float>(a * std::sin(w * static_cast<double>(i)));
    }
    s.r = s.l;
    return s;
}

// Hann-windowed amplitude of a sinusoid at `hz` in x[a, b).
double amp(const std::vector<float>& x, std::size_t a, std::size_t b, double hz) {
    std::complex<double> acc = 0.0;
    double wsum = 0.0;
    for (std::size_t i = a; i < b; ++i) {
        const double w = 0.5 - 0.5 * std::cos(dsp::kTwoPi * static_cast<double>(i - a) / static_cast<double>(b - a));
        acc += w * static_cast<double>(x[i]) * std::polar(1.0, -dsp::kTwoPi * hz * static_cast<double>(i) / kSr);
        wsum += w;
    }
    return 2.0 * std::abs(acc) / wsum;
}

// Frequency from upward zero crossings in x[a, b).
double zeroCrossHz(const std::vector<float>& x, std::size_t a, std::size_t b) {
    double first = -1.0, last = -1.0;
    int n = 0;
    for (std::size_t i = std::max<std::size_t>(a, 1); i < b; ++i)
        if (x[i - 1] < 0.0f && x[i] >= 0.0f) {
            const double t = static_cast<double>(i - 1) + x[i - 1] / (x[i - 1] - x[i]);
            if (first < 0.0) first = t;
            else ++n;
            last = t;
        }
    return n > 0 ? n * kSr / (last - first) : 0.0;
}

// ---------------------------------------------------------------------------------------------

void testFactory() {
    std::printf("factory & param specs\n");
    const auto types = premiumEffectTypes();
    check(types == std::vector<std::string>{"microshift", "shimmer", "tape", "exciter", "dimension"}, "5 premium effect types");
    check(createPremiumEffect("reverb") == nullptr && createPremiumEffect("nope") == nullptr, "foreign / unknown type -> nullptr");
    const auto all = effectTypes();
    for (const auto& t : types) {
        check(std::find(all.begin(), all.end(), t) != all.end() && createEffect(t) != nullptr && !effectAcceptsSidechain(t),
              "'" + t + "' registered (no sidechain)");
        auto fx = createPremiumEffect(t);
        bool specsOk = !fx->paramSpecs().empty();
        for (const auto& s : fx->paramSpecs())
            specsOk = specsOk && !s.help.empty() && s.min <= s.def && s.def <= s.max && !s.name.empty() &&
                      (s.choices.empty() || !s.automatable);
        check(specsOk, "'" + t + "' specs have help, valid ranges, choices not automatable");
        bool unknown = false, range = false, type = false;
        try { createPremiumEffect(t)->configure(json{{"bogus", 1}}); } catch (const ConfigError&) { unknown = true; }
        try { createPremiumEffect(t)->configure(json{{"mix", 7}}); } catch (const ConfigError&) { range = true; }
        try { createPremiumEffect(t)->configure(json{{"mix", "loud"}}); } catch (const ConfigError&) { type = true; }
        check(unknown && range && type, "'" + t + "' rejects unknown key, out-of-range mix, wrong type");
        check(!fx->setParam("definitely_not_a_param", 1.0f) && fx->setParam("mix", 0.5f), "'" + t + "' setParam");
    }
    bool threw = false;
    try { createPremiumEffect("microshift")->configure(json{{"style", "h910"}}); } catch (const ConfigError&) { threw = true; }
    check(threw, "microshift rejects an unknown style");
    check(!createPremiumEffect("microshift")->setParam("style", 1) && !createPremiumEffect("tape")->setParam("speed", 1) &&
              !createPremiumEffect("tape")->setParam("link", 0) && !createPremiumEffect("shimmer")->setParam("size", 0.2f),
          "style / speed / link / size are not automatable");
}

void testMicroShift() {
    std::printf("microshift\n");
    // voices: left +detune, right -detune (grain period rounding: exact to << 0.1 ct)
    for (const char* style : {"classic", "smooth", "wide"}) {
        Stereo s = sine(sec(3.0), 1000.0, 0.3f);
        auto fx = make("microshift", {{"style", style}, {"mix", 1.0}, {"focus", 20}, {"detune", 20}});
        run(*fx, s);
        const double fl = zeroCrossHz(s.l, sec(0.3), s.size()), fr = zeroCrossHz(s.r, sec(0.3), s.size());
        const double cl = 1200.0 * std::log2(fl / 1000.0), cr = 1200.0 * std::log2(fr / 1000.0);
        // wide scales the detune by 1.3 (right voice by 0.85 of that) and breathes +-3 ct around it
        const bool wide = std::string(style) == "wide";
        const double want = wide ? 26.0 : 20.0, wantR = wide ? -26.0 * 0.85 : -20.0, tol = wide ? 1.5 : 0.3;
        check(std::fabs(cl - want) < tol && std::fabs(cr - wantR) < tol,
              std::string(style) + fmt(": detune 20 -> left voice %+.2f ct, right %+.2f ct", cl, cr));
    }

    // a mono lead gets wide and stays mono-compatible at the default mix
    for (const char* style : {"classic", "smooth", "wide"}) {
        const Stereo in = saw(sec(4.0), 220.0, 0.25f);
        Stereo s = in;
        auto fx = make("microshift", {{"style", style}});
        run(*fx, s);
        const std::size_t a = sec(0.5), b = s.size();
        double el = 0, er = 0, lr = 0, mono = 0, ein = 0, side = 0, minCorr = 1.0;
        for (std::size_t i = a; i < b; ++i) {
            el += double(s.l[i]) * s.l[i];
            er += double(s.r[i]) * s.r[i];
            lr += double(s.l[i]) * s.r[i];
            const double m = 0.5 * (s.l[i] + s.r[i]), d = 0.5 * (s.l[i] - s.r[i]);
            mono += m * m;
            side += d * d;
            ein += double(in.l[i]) * in.l[i];
        }
        for (std::size_t w = a; w + 4800 <= b; w += 4800) {
            double x = 0, y = 0, z = 0;
            for (std::size_t i = w; i < w + 4800; ++i) {
                x += double(s.l[i]) * s.l[i];
                y += double(s.r[i]) * s.r[i];
                z += double(s.l[i]) * s.r[i];
            }
            minCorr = std::min(minCorr, z / std::sqrt(x * y));
        }
        const double corr = lr / std::sqrt(el * er), foldDb = 10.0 * std::log10(mono / ein);
        const double stereoDb = 10.0 * std::log10(0.5 * (el + er) / ein), widthPct = 100.0 * std::sqrt(side / mono);
        check(corr > 0.3 && minCorr > 0.0 && foldDb > -2.0 && foldDb < 0.5 && std::fabs(stereoDb) < 1.0 && widthPct > 40.0,
              std::string(style) + fmt(": mono saw lead -> correlation %.2f (min %.2f per 100 ms), width %.0f %%, "
                                       "mono fold-down %.2f dB, stereo level %+.2f dB",
                                       corr, minCorr, widthPct, foldDb, stereoDb));
    }

    // splices: the voice alone on a steady tone keeps its level (smooth: correlation-aligned splices)
    for (const char* style : {"classic", "smooth"}) {
        double worst = 0.0;
        for (const double det : {9.0, 30.0}) {
            Stereo s = sine(sec(6.0), 440.0, 0.3f);
            auto fx = make("microshift", {{"style", style}, {"mix", 1.0}, {"focus", 20}, {"detune", det}});
            run(*fx, s);
            double mn = 1e9, mx = 0.0;
            for (std::size_t w = sec(0.3); w + 480 <= s.size(); w += 120) {
                const double r = rms(s.l, w, w + 480);
                mn = std::min(mn, r);
                mx = std::max(mx, r);
            }
            worst = std::max(worst, db(mx / mn));
        }
        const bool smooth = std::string(style) == "smooth";
        check(worst < (smooth ? 0.5 : 3.0), std::string(style) + fmt(": voice level through splices within %.2f dB (sine, 9 and 30 ct)", worst));
    }

    // focus: lows stay dry and centred
    {
        const Stereo in = sine(sec(2.0), 60.0, 0.4f);
        Stereo s = in;
        auto fx = make("microshift", {{"focus", 300}, {"mix", 0.5}});
        run(*fx, s);
        double d = 0.0, e = 0.0;
        for (std::size_t i = sec(0.5); i < s.size(); ++i) {
            d += std::pow(double(s.l[i]) - s.r[i], 2.0);
            e += double(s.l[i]) * s.l[i];
        }
        const double lvl = db(rms(s.l, sec(0.5), s.size()) / rms(in.l, sec(0.5), s.size()));
        check(10.0 * std::log10(d / e) < -30.0 && std::fabs(lvl) < 0.5,
              fmt("focus 300 Hz: a 60 Hz tone stays mono (side %.1f dB) at its level (%+.2f dB)", 10.0 * std::log10(d / e), lvl));
    }
    // mix 1 (send bus) returns the voices only: no second copy of the lows below 'focus' in the mix
    {
        double lv[3];
        const double mixes[3] = {0.5, 0.75, 1.0};
        for (int m = 0; m < 3; ++m) {
            Stereo s = sine(sec(1.0), 60.0, 0.4f);
            auto fx = make("microshift", {{"mix", mixes[m]}, {"focus", 300}});
            run(*fx, s);
            lv[m] = db(rms(s.l, sec(0.5), s.size()) / (0.4 / std::sqrt(2.0)));
        }
        check(std::fabs(lv[0]) < 0.3 && lv[1] < -2.0 && lv[1] > -7.0 && lv[2] < -30.0,
              fmt("60 Hz below focus 300: %+.1f dB at mix 0.5, %+.1f dB at 0.75, %+.1f dB at mix 1 (send: voices only)", lv[0], lv[1], lv[2]));
    }

    // mix 0 = dry; detune 0 = static delays (no pitch change)
    {
        const Stereo in = saw(sec(1.0), 330.0, 0.3f);
        Stereo s = in;
        auto fx = make("microshift", {{"mix", 0.0}});
        run(*fx, s);
        float dev = 0.0f;
        for (std::size_t i = 0; i < s.size(); ++i) dev = std::max(dev, std::fabs(s.l[i] - in.l[i]));
        check(dev < 1e-5f, fmt("mix 0 passes the dry signal (max deviation %.1e)", dev));
        Stereo t = sine(sec(2.0), 1000.0, 0.3f);
        auto f0 = make("microshift", {{"mix", 1.0}, {"detune", 0}, {"focus", 20}});
        run(*f0, t);
        const double hz = zeroCrossHz(t.l, sec(0.2), t.size());
        check(std::fabs(1200.0 * std::log2(hz / 1000.0)) < 0.05, fmt("detune 0: no pitch shift (%.3f Hz)", hz));
    }
}

void testShimmer() {
    std::printf("shimmer\n");
    // a 400 Hz burst: the octave (800) and double octave (1600) grow in the tail relative to the note
    auto burst = [](double hz) {
        Stereo s(sec(8.0));
        for (std::size_t i = 0; i < sec(0.5); ++i) s.l[i] = s.r[i] = 0.3f * static_cast<float>(std::sin(dsp::kTwoPi * hz * i / kSr));
        return s;
    };
    for (const double sh : {0.0, 0.6}) {
        Stereo s = burst(400.0);
        auto fx = make("shimmer", {{"mix", 1.0}, {"shimmer", sh}, {"decay", 6}});
        run(*fx, s);
        // octaves above the note (800, 1600, 3200 Hz) relative to the note, in 0.5 s windows
        auto octaves = [&](double t) {
            const std::size_t a = sec(t), b = sec(t + 0.5);
            double e = 0.0;
            for (const double hz : {800.0, 1600.0, 3200.0}) e += std::pow(amp(s.l, a, b, hz), 2.0);
            return 10.0 * std::log10(e / std::pow(amp(s.l, a, b, 400.0), 2.0));
        };
        const double early = octaves(0.6), mid = octaves(3.0), late = octaves(4.5);
        if (sh == 0.0)
            check(late < -20.0, fmt("shimmer 0: plain reverb, no octaves in the tail (%.1f dB re the note at 4.5 s)", late));
        else
            check(mid > early + 10.0 && late > mid && late > 6.0,
                  fmt("shimmer 0.6: octaves above the note %.1f dB re the note at 0.6 s -> %+.1f dB at 3 s -> %+.1f dB at 4.5 s",
                      early, mid, late));
    }
    {  // the fifth voice (+7 st: 400 -> 599.3 Hz, then 897.9 Hz)
        Stereo s = burst(400.0);
        auto fx = make("shimmer", {{"mix", 1.0}, {"shimmer", 0.0}, {"fifth", 0.8}, {"decay", 6}});
        run(*fx, s);
        const double f5 = 400.0 * std::pow(2.0, 7.0 / 12.0);
        const double late = db(amp(s.l, sec(3.0), sec(3.5), f5) / amp(s.l, sec(3.0), sec(3.5), 400.0));
        const double oct = db(amp(s.l, sec(3.0), sec(3.5), 800.0) / amp(s.l, sec(3.0), sec(3.5), 400.0));
        check(late > -6.0 && oct < late - 10.0, fmt("fifth 0.8: +7 st voice %+.1f dB re note at 3 s (octave only %+.1f dB)", late, oct));
    }
    {  // stability: everything at max still decays
        Stereo s = noise(sec(40.0), 0.5f, 4);
        for (std::size_t i = sec(2.0); i < s.size(); ++i) s.l[i] = s.r[i] = 0.0f;
        auto fx = make("shimmer", {{"mix", 1.0}, {"shimmer", 1}, {"fifth", 1}, {"decay", 30}, {"damping", 20000}, {"lowcut", 20},
                                   {"highcut", 20000}});
        run(*fx, s);
        const double a = db(rms(s.l, sec(2.0), sec(4.0))), b = db(rms(s.l, sec(20.0), sec(22.0))), c = db(rms(s.l, sec(36.0), sec(38.0)));
        check(allFinite(s) && maxAbs(s.l) < 2.0f && b < a - 3.0 && c < b - 3.0,
              fmt("shimmer + fifth 1, decay 30 s, no damping: bounded (peak %.2f) and decaying (%.1f / %.1f / %.1f dB at 3 / 21 / 37 s)",
                  maxAbs(s.l), a, b, c));
    }
    // the loop gain follows the core's longest-ringing band: dark (low damping lifts the lows), short,
    // huge-room and unfiltered corners all decay
    for (const json& corner : {json{{"size", 1.0}, {"decay", 0.5}, {"damping", 20000}, {"lowcut", 20}},
                               json{{"size", 0.0}, {"decay", 3.0}, {"damping", 1000}, {"lowcut", 20}},
                               json{{"size", 1.0}, {"decay", 3.0}, {"damping", 1000}, {"lowcut", 20}}}) {
        json p = corner;
        p["mix"] = 1.0;
        p["shimmer"] = 1.0;
        p["fifth"] = 1.0;
        p["highcut"] = 20000;
        auto fx = make("shimmer", p);
        Stereo s = noise(sec(20.0), 0.5f, 3, false);
        for (std::size_t i = sec(1.0); i < s.size(); ++i) s.l[i] = s.r[i] = 0.0f;
        run(*fx, s);
        const double a = db(rms(s.l, sec(1.0), sec(3.0))), b = db(rms(s.l, sec(8.0), sec(10.0))), c = db(rms(s.l, sec(17.0), sec(19.0)));
        check(maxAbs(s.l) < 4.0f && b < a - 6.0 && c < b - 6.0,
              corner.dump() + fmt(": shimmer + fifth 1 on -6 dBFS noise: peak %.2f, decays (%.0f / %.0f / %.0f dB at 2 / 9 / 18 s)", maxAbs(s.l), a, b, c));
    }
    {  // tail: silent after tailSeconds
        auto fx = make("shimmer", json::object());
        Stereo s = noise(sec(30.0), 0.3f, 6, false);
        for (std::size_t i = sec(1.0); i < s.size(); ++i) s.l[i] = s.r[i] = 0.0f;
        const double tail = fx->tailSeconds();
        run(*fx, s);
        const float after = std::max(maxAbs(s.l, sec(1.0 + tail)), maxAbs(s.r, sec(1.0 + tail)));
        check(tail < 29.0 && db(after / 0.3) < -60.0, fmt("defaults: tail %.1f s long, below -60 dB after it (%.1f dB)", tail, db(after / 0.3)));
    }
    // dark tails (damping at or below 1 kHz, the shared reverb core): the decay stays near 'decay' at every
    // frequency. (The core used to normalise its loop at 1 kHz even when the damping filter already
    // attenuated there, lifting the lows to a loop gain of ~1: minutes-long bass tails.)
    for (const char* type : {"shimmer", "reverb"})
        for (const double damp : {500.0, 1000.0, 1500.0}) {
            if (std::string(type) == "shimmer" && damp < 1000.0) continue;
            Stereo s(sec(20.0));
            dsp::Rng rng(5);
            for (std::size_t i = 0; i < sec(0.5); ++i) {
                s.l[i] = 0.3f * rng.bipolar();
                s.r[i] = 0.3f * rng.bipolar();
            }
            json p = {{"mix", 1.0}, {"decay", 3.0}, {"damping", damp}};
            if (std::string(type) == "shimmer") p["shimmer"] = 0.6;
            auto fx = createEffect(type);
            fx->configure(p);
            RenderContext ctx;
            ctx.sampleRate = kSr;
            fx->prepare(ctx);
            run(*fx, s);
            auto lvl = [&](double t) { return db(std::max(rms(s.l, sec(t), sec(t + 0.2)), rms(s.r, sec(t), sec(t + 0.2)))); };
            const double t60 = 60.0 * (8.0 - 2.0) / (lvl(2.0) - lvl(8.0));
            check(t60 > 2.0 && t60 < 6.0 && lvl(12.0) - lvl(1.0) < -60.0 && fx->tailSeconds() > t60,
                  std::string(type) + fmt(" damping %.0f Hz, decay 3 s: broadband RT60 %.1f s (tailSeconds %.1f)", damp, t60, fx->tailSeconds()));
        }
    {  // wet level and stereo: the core's normalisation, natural width (decorrelated, not phasey)
        Stereo s = noise(sec(6.0), dsp::dbToGain(-18.0f), 11, false);
        auto fx = make("shimmer", {{"mix", 1.0}});
        run(*fx, s);
        double el = 0, er = 0, lr = 0;
        for (std::size_t i = sec(2.0); i < s.size(); ++i) {
            el += double(s.l[i]) * s.l[i];
            er += double(s.r[i]) * s.r[i];
            lr += double(s.l[i]) * s.r[i];
        }
        const double lvl = db(rms(s.l, sec(2.0), s.size())), corr = lr / std::sqrt(el * er);
        check(lvl > -28.0 && lvl < -12.0 && std::fabs(corr) < 0.3,
              fmt("100%% wet on -18 dBFS noise: %.1f dBFS, L/R correlation %.2f", lvl, corr));
    }
}

void testTape() {
    std::printf("tape\n");
    // frequency response at a low level (linear), transport off
    auto response = [](const char* speed, double bump, double hz) {
        Stereo s = sine(sec(1.0), hz, 0.01f);
        auto fx = make("tape", {{"speed", speed}, {"wow", 0}, {"flutter", 0}, {"bump", bump}});
        run(*fx, s);
        return db(amp(s.l, sec(0.5), sec(1.0), hz) / 0.01);
    };
    {
        const double b90 = response("15", 3, 90), k1 = response("15", 3, 1000), hf = response("15", 3, 18500), b0 = response("15", 0, 90);
        check(b90 > 2.0 && b90 < 3.5 && std::fabs(k1) < 0.3 && hf < -1.5 && hf > -4.5 && std::fabs(b0) < 0.8,
              fmt("15 ips, bump 3: 90 Hz %+.1f dB (bump 0: %+.1f), 1 kHz %+.2f dB, 18.5 kHz %+.1f dB", b90, b0, k1, hf));
        const double c60 = response("cassette", 3, 60), c10 = response("cassette", 3, 10500), c16 = response("cassette", 3, 16000);
        check(c60 > 2.0 && c10 < -1.5 && c10 > -4.5 && c16 < -10.0,
              fmt("cassette: bump at 60 Hz %+.1f dB, 10.5 kHz %+.1f dB, 16 kHz %+.1f dB", c60, c10, c16));
        const double t30 = response("30", 3, 120), t30hf = response("30", 3, 18000), t30lo = response("30", 3, 25);
        check(t30 > 2.0 && t30hf > -1.0 && t30lo < -3.0, fmt("30 ips: bump at 120 Hz %+.1f dB, 18 kHz %+.1f dB, 25 Hz roll-off %+.1f dB", t30, t30hf, t30lo));
    }
    // saturation: level dependent, asymmetric with bias
    auto thd = [](double levelDb, double bias, double& gainDb, double& h2, double& h3) {
        const float a = dsp::dbToGain(static_cast<float>(levelDb));
        Stereo s = sine(sec(1.0), 200.0, a);
        auto fx = make("tape", {{"wow", 0}, {"flutter", 0}, {"drive", 6}, {"bias", bias}});
        run(*fx, s);
        const double f = amp(s.l, sec(0.5), sec(1.0), 200.0);
        gainDb = db(f / a);
        h2 = db(amp(s.l, sec(0.5), sec(1.0), 400.0) / f);
        h3 = db(amp(s.l, sec(0.5), sec(1.0), 600.0) / f);
    };
    {
        double g1, h21, h31, g2, h22, h32, g3, h23, h33;
        thd(-30.0, 0.2, g1, h21, h31);
        thd(-6.0, 0.2, g2, h22, h32);
        thd(-12.0, 0.0, g3, h23, h33);
        check(std::fabs(g1) < 0.5 && h31 < -50.0 && h32 > -35.0 && g2 < -0.5,
              fmt("drive 6: -30 dBFS clean (gain %+.2f dB, H3 %.0f dB), -6 dBFS saturates (H3 %.0f dB, gain %+.1f dB)", g1, h31, h32, g2));
        check(h23 < -70.0 && h22 > -45.0, fmt("bias 0: symmetric (H2 %.0f dB); bias 0.2 adds even harmonics (H2 %.0f dB at -6 dBFS)", h23, h22));
    }
    // wow / flutter: pitch deviation, stereo link
    {
        Stereo s = sine(sec(6.0), 1000.0, 0.3f);
        auto fx = make("tape", {{"speed", "15"}, {"wow", 1}, {"flutter", 1}});
        run(*fx, s);
        double fmin = 1e9, fmax = 0.0;
        for (std::size_t w = sec(0.2); w + 2400 <= s.size(); w += 1200) {
            const double f = zeroCrossHz(s.l, w, w + 2400);
            fmin = std::min(fmin, f);
            fmax = std::max(fmax, f);
        }
        const double dev = 50.0 * (fmax - fmin) / 1000.0;  // +- percent
        check(dev > 0.3 && dev < 1.0 && std::memcmp(s.l.data(), s.r.data(), s.size() * sizeof(float)) == 0,
              fmt("wow + flutter 1: pitch +-%.2f %% (mono in -> identical sides: linked transport)", dev));
        Stereo u = sine(sec(2.0), 1000.0, 0.3f);
        auto fu = make("tape", {{"wow", 1}, {"flutter", 1}, {"link", false}});
        run(*fu, u);
        double d = 0.0;
        for (std::size_t i = sec(0.5); i < u.size(); ++i) d = std::max(d, double(std::fabs(u.l[i] - u.r[i])));
        check(d > 0.01, fmt("link off: independent transports per side (max L-R %.3f)", d));
        Stereo t = sine(sec(2.0), 1000.0, 0.3f);
        auto ft = make("tape", {{"wow", 0}, {"flutter", 0}});
        run(*ft, t);
        const double hz = zeroCrossHz(t.l, sec(0.2), t.size());
        check(std::fabs(hz - 1000.0) < 0.01, fmt("wow / flutter 0: steady pitch (%.4f Hz)", hz));
    }
    // dry/wet phase-coherent: a parallel blend has no comb notches (mix 0.5 sits between dry and tape)
    {
        double worst = 0.0;
        for (const double hz : {100.0, 1000.0, 4000.0, 10000.0}) {
            double lv[3];
            for (int m = 0; m < 3; ++m) {
                Stereo s = sine(sec(0.5), hz, 0.05f);
                auto fx = make("tape", {{"mix", 0.5 * m}, {"wow", 0}, {"flutter", 0}});
                run(*fx, s);
                lv[m] = amp(s.l, sec(0.25), s.size(), hz);
            }
            worst = std::max(worst, std::fabs(db(lv[1] / (0.5 * (lv[0] + lv[2])))));
        }
        Stereo a(4800);
        a.l[100] = a.r[100] = 0.5f;
        auto f0 = make("tape", {{"mix", 0.0}});
        run(*f0, a);
        std::size_t pa = 0;
        for (std::size_t i = 0; i < a.size(); ++i)
            if (std::fabs(a.l[i]) > std::fabs(a.l[pa])) pa = i;
        const double lat = static_cast<double>(pa - 100) / kSr * 1000.0;
        check(worst < 0.3 && lat < 3.0,
              fmt("dry and tape paths aligned: mix 0.5 within %.2f dB of the dry/tape mean (100 Hz-10 kHz); transport delay %.2f ms",
                  worst, lat));
    }
    // the transport delays only as much as the current wow / flutter depth needs (tracks are not
    // latency-compensated): an impulse comes out after ~6 samples without wow / flutter, ~0.3 ms at the defaults
    {
        auto delayOf = [](const json& p) {
            Stereo a(9600);
            a.l[100] = a.r[100] = 0.5f;
            auto fx = make("tape", p);
            run(*fx, a);
            std::size_t pk = 0;
            for (std::size_t i = 0; i < a.size(); ++i)
                if (std::fabs(a.l[i]) > std::fabs(a.l[pk])) pk = i;
            return static_cast<double>(pk) - 100.0;
        };
        const double d0 = delayOf({{"wow", 0}, {"flutter", 0}}), dd = delayOf(json::object()),
                     dc = delayOf({{"speed", "cassette"}, {"wow", 1}, {"flutter", 1}});
        check(d0 <= 8.0 && dd < 0.5e-3 * kSr && dc < 3.5e-3 * kSr,
              fmt("transport delay: %.0f samples at wow = flutter = 0, %.2f ms at the defaults, %.2f ms at cassette wow = flutter = 1",
                  d0, dd / kSr * 1e3, dc / kSr * 1e3));
    }
    // wow automation 0 -> 1 -> 0 on a steady tone: the depth (and with it the centre delay) glides over
    // ~0.25 s, so the change bends the pitch by a few cents only (the former 20 ms glide bent it by ~2 %); afterwards
    // the full wow depth
    {
        Stereo s = sine(sec(8.0), 1000.0, 0.3f);
        auto fx = make("tape", {{"wow", 0}, {"flutter", 0}});
        run(*fx, s, 256, [&](std::size_t i) {
            if (i == sec(1.0) / 256 * 256) fx->setParam("wow", 1.0f);
            if (i == sec(5.0) / 256 * 256) fx->setParam("wow", 0.0f);
        });
        double worstStep = 0.0, fmin = 1e9, fmax = 0.0;
        for (std::size_t i = sec(0.5); i < s.size(); ++i) worstStep = std::max(worstStep, double(std::fabs(s.l[i] - s.l[i - 1])));
        // pitch through both depth changes (25 ms windows): never beyond the wow's own swing plus a few cents
        double bend = 0.0;
        for (std::size_t w = sec(0.9); w + 1200 <= sec(7.0); w += 600)
            bend = std::max(bend, std::fabs(zeroCrossHz(s.l, w, w + 1200) - 1000.0) / 10.0);
        for (std::size_t w = sec(2.5); w + 2400 <= sec(5.0); w += 1200) {
            const double f = zeroCrossHz(s.l, w, w + 2400);
            fmin = std::min(fmin, f);
            fmax = std::max(fmax, f);
        }
        const double hzAfter = zeroCrossHz(s.l, sec(7.0), s.size());
        // largest sample step of the same tone at a constant wow 0 / 1 (the glide must not add to it)
        double refStep = 0.0;
        for (const float w : {0.0f, 1.0f}) {
            Stereo r = sine(sec(3.0), 1000.0, 0.3f);
            auto fr = make("tape", {{"wow", w}, {"flutter", 0}});
            run(*fr, r);
            for (std::size_t i = sec(0.5); i < r.size(); ++i) refStep = std::max(refStep, double(std::fabs(r.l[i] - r.l[i - 1])));
        }
        check(worstStep < 1.01 * refStep && bend < 1.0 && 50.0 * (fmax - fmin) / 1000.0 > 0.2 && std::fabs(hzAfter - 1000.0) < 0.05,
              fmt("wow 0 -> 1 -> 0: smooth (max step %.4f, constant wow %.4f; pitch within +-%.2f %%), full depth +-%.2f %% after the glide, steady %.3f Hz after wow 0",
                  worstStep, refStep, bend, 50.0 * (fmax - fmin) / 1000.0, hzAfter));
    }
    // hiss
    {
        Stereo s(sec(2.0)), z(sec(1.0));
        auto fh = make("tape", {{"hiss", 1}}), fz = make("tape", {{"hiss", 0}});
        run(*fh, s);
        run(*fz, z);
        const double h = db(rms(s.l, sec(1.0), s.size()));
        double lr = 0, ll = 0;
        for (std::size_t i = sec(1.0); i < s.size(); ++i) {
            lr += double(s.l[i]) * s.r[i];
            ll += double(s.l[i]) * s.l[i];
        }
        check(h > -56.0 && h < -46.0 && std::fabs(lr / ll) < 0.1 && maxAbs(z.l) == 0.0f,
              fmt("hiss 1: %.1f dBFS, decorrelated (%.2f); hiss 0: exact silence", h, lr / ll));
    }
}

void testExciter() {
    std::printf("exciter\n");
    // harmonics above 'freq', nothing below it, and no aliasing
    for (const double f0 : {4000.0, 9500.0}) {
        Stereo s = sine(sec(1.0), f0, 0.25f);
        auto fx = make("exciter", {{"amount", 1.0}, {"character", 0.5}, {"freq", 3000}});
        run(*fx, s);
        const std::size_t a = sec(0.5), b = s.size();
        const double h2 = db(amp(s.l, a, b, 2 * f0) / 0.25);
        const double h3 = 3 * f0 < 24000 ? db(amp(s.l, a, b, 3 * f0) / 0.25) : -200.0;
        double worst = -300.0, where = 0.0;
        for (double hz = 100.0; hz < 23900.0; hz += 37.0) {
            bool harmonic = false;
            for (int h = 1; h <= 3; ++h) harmonic = harmonic || (h * f0 < 24000.0 && std::fabs(hz - h * f0) < 150.0);
            if (harmonic) continue;
            const double v = db(amp(s.l, a, b, hz) / 0.25);
            if (v > worst) { worst = v; where = hz; }
        }
        if (f0 < 5000.0)
            check(h2 > -20.0 && h3 > -20.0 && worst < -100.0,
                  fmt("%.0f Hz tone: 2nd %.1f dB, 3rd %.1f dB; everything else below %.0f dB (at %.0f Hz)", f0, h2, h3, worst, where));
        else
            check(h2 > -20.0 && worst < -95.0,
                  fmt("%.0f Hz tone: 2nd (19 kHz) %.1f dB; 3rd (28.5 kHz) does not alias: worst other %.0f dB (at %.0f Hz)", f0, h2, worst, where));
    }
    {  // below 'freq': untouched; level dependence; bypass
        Stereo s = sine(sec(1.0), 500.0, 0.3f), in = s;
        auto fx = make("exciter", {{"amount", 1.0}, {"freq", 3000}});
        run(*fx, s);
        double d = 0.0;
        for (std::size_t i = sec(0.3); i < s.size(); ++i) d = std::max(d, double(std::fabs(s.l[i] - in.l[i])));
        check(db(d / 0.3) < -60.0, fmt("500 Hz tone with freq 3 kHz: output = input within %.0f dB", db(d / 0.3)));
        auto rel = [](float level) {
            Stereo t = sine(sec(1.0), 4000.0, level);
            auto f = make("exciter", {{"amount", 1.0}, {"drive", 20}, {"character", 0.0}});
            run(*f, t);
            return db(amp(t.l, sec(0.5), sec(1.0), 8000.0) / level);
        };
        const double loud = rel(0.3f), quiet = rel(0.003f);
        check(loud > quiet + 25.0, fmt("level dependent (drive 20): 2nd harmonic %.1f dB re tone at -10 dBFS, %.1f dB at -50 dBFS", loud, quiet));
        for (const char* key : {"amount", "mix"}) {
            Stereo n = noise(sec(1.0), 0.2f, 3, false), ref = n;
            auto f = make("exciter", {{key, 0.0}});
            run(*f, n);
            check(identical(n, ref), std::string(key) + " 0: bit-exact bypass");
        }
    }
    {  // dull material gets new top end
        Stereo s = saw(sec(2.0), 220.0, 0.3f);
        dsp::Biquad lp[4];
        for (int k = 0; k < 4; ++k) lp[k].set(dsp::Biquad::Type::LowPass, kSr, 1200.0, 0.7071);
        for (std::size_t i = 0; i < s.size(); ++i) s.l[i] = s.r[i] = lp[1].process(lp[0].process(s.l[i]));
        Stereo in = s;
        auto fx = make("exciter", {{"freq", 1000}, {"amount", 0.6}});
        run(*fx, s);
        auto band = [](const std::vector<float>& x) {
            dsp::Biquad hp[2];
            for (auto& h : hp) h.set(dsp::Biquad::Type::HighPass, kSr, 4000.0, 0.7071);
            double e = 0.0;
            for (std::size_t i = 0; i < x.size(); ++i) {
                const double v = hp[1].process(hp[0].process(x[i]));
                if (i >= static_cast<std::size_t>(kSr / 2)) e += v * v;
            }
            return e;
        };
        const double gain = 10.0 * std::log10(band(s.l) / band(in.l));
        const double total = db(rms(s.l, sec(0.5), s.size()) / rms(in.l, sec(0.5), s.size()));
        check(gain > 10.0 && std::fabs(total) < 1.0,
              fmt("dull saw (low-passed at 1.2 kHz): +%.1f dB above 4 kHz, overall level %+.2f dB", gain, total));
    }
}

void testDimension() {
    std::printf("dimension\n");
    // the effect is a pure side signal: the mono sum is the dry signal
    double prevWidth = 0.0;
    bool widening = true;
    for (int mode = 1; mode <= 4; ++mode) {
        const Stereo in = saw(sec(3.0), 196.0, 0.25f);
        Stereo s = in;
        auto fx = make("dimension", {{"mode", mode}});
        run(*fx, s);
        double dev = 0.0, mid = 0.0, side = 0.0;
        for (std::size_t i = sec(0.2); i < s.size(); ++i) {
            const double m = 0.5 * (double(s.l[i]) + s.r[i]), d = 0.5 * (double(s.l[i]) - s.r[i]);
            dev = std::max(dev, std::fabs(m - in.l[i]));
            mid += m * m;
            side += d * d;
        }
        const double width = 100.0 * std::sqrt(side / mid);
        if (mode <= 3) widening = widening && width > prevWidth;
        prevWidth = width;
        check(dev < 1e-6 && width > 10.0, fmt("mode %.0f: mono sum = dry (max deviation %.1e), width %.0f %%", mode, dev, width));
    }
    check(widening, "modes 1-3 get wider");
    {  // lows stay centred
        Stereo s = sine(sec(2.0), 70.0, 0.4f);
        auto fx = make("dimension", {{"mode", 4}});
        run(*fx, s);
        double side = 0.0, e = 0.0;
        for (std::size_t i = sec(0.5); i < s.size(); ++i) {
            side += std::pow(0.5 * (double(s.l[i]) - s.r[i]), 2.0);
            e += double(s.l[i]) * s.l[i];
        }
        check(10.0 * std::log10(side / e) < -30.0, fmt("70 Hz stays centred (side %.1f dB)", 10.0 * std::log10(side / e)));
    }
    bool threw = false;
    try { createPremiumEffect("dimension")->configure(json{{"mode", 2.5}}); } catch (const ConfigError&) { threw = true; }
    check(threw && !createPremiumEffect("dimension")->setParam("mode", 2), "mode: whole numbers only, not automatable");
}

void testCommon() {
    std::printf("determinism, block sizes, robustness, levels, tails, sample rates, speed\n");
    for (const auto& t : premiumEffectTypes()) {
        json busy = json::object();
        if (t == "tape") busy = {{"wow", 0.7}, {"flutter", 0.7}, {"hiss", 0.5}, {"link", false}};
        if (t == "shimmer") busy = {{"fifth", 0.5}};
        {  // determinism across instances and block-size independence
            auto a = make(t, busy, kSr, 42), b = make(t, busy, kSr, 42), c = make(t, busy, kSr, 43);
            Stereo x = noise(sec(2.0), 0.2f, 99, false), y = x, z = x;
            run(*a, x, 256);
            run(*b, y, 37);
            run(*c, z, 256);
            check(identical(x, y), t + ": deterministic and block-size independent");
            if (t == "tape") check(!identical(x, z), t + ": another song seed gives another transport / hiss");
        }
        for (int ext = 0; ext < 2; ++ext) {  // every numeric param at min / max, loud input
            auto probe = createPremiumEffect(t);
            json p = json::object();
            for (const auto& s : probe->paramSpecs())
                if (s.choices.empty() && s.name != "link") p[s.name] = ext ? s.max : s.min;
            auto fx = make(t, p);
            Stereo s = noise(sec(3.0), 0.5f, 5 + ext);
            run(*fx, s);
            check(allFinite(s, 8.0f), t + (ext ? ": all params at max" : ": all params at min") + fmt(" -> finite, peak %.2f", maxAbs(s.l)));
        }
        {  // automation fuzz
            auto fx = make(t, json::object());
            dsp::Rng rng(1234);
            const std::vector<ParamSpec> specs = fx->paramSpecs();
            Stereo s = noise(sec(3.0), 0.2f, 17);
            run(*fx, s, 32, [&](std::size_t) {
                const auto& sp = specs[static_cast<std::size_t>(rng.next() % specs.size())];
                fx->setParam(sp.name, sp.min + (sp.max - sp.min) * rng.uniform());
            });
            check(allFinite(s, 8.0f), t + fmt(": automation fuzz finite (peak %.2f)", maxAbs(s.l)));
        }
        {  // silence in -> exact silence out
            auto fx = make(t, json::object());
            Stereo s(sec(1.0));
            run(*fx, s);
            check(maxAbs(s.l) == 0.0f && maxAbs(s.r) == 0.0f, t + ": silence in -> exact silence out");
        }
        {  // typical level
            auto fx = make(t, json::object());
            Stereo s = noise(sec(3.0), dsp::dbToGain(-18.0f), 4, false);
            run(*fx, s);
            const double l = db(rms(s.l, sec(1.0), s.size()));
            check(l > -21.0 && l < -15.0 && maxAbs(s.l) < 0.6f, t + fmt(": defaults on -18 dBFS noise -> %.1f dBFS RMS", l));
        }
        {  // tails reach exact digital silence without denormal slowdowns (shimmer: a 2 s decay fits in 40 s)
            const json tc = t == "shimmer" ? json{{"decay", 2.0}} : json::object();
            auto fn = make(t, tc), fi = make(t, tc);
            Stereo busyIn = noise(sec(8.0), 0.2f, 2, false), tail(sec(40.0));
            for (std::size_t i = 0; i < sec(0.5); ++i) tail.l[i] = tail.r[i] = busyIn.l[i];
            const auto t0 = std::chrono::steady_clock::now();
            run(*fn, busyIn);
            const auto t1 = std::chrono::steady_clock::now();
            run(*fi, tail);
            const auto t2 = std::chrono::steady_clock::now();
            const double perBusy = std::chrono::duration<double>(t1 - t0).count() / 8.0;
            const double perTail = std::chrono::duration<double>(t2 - t1).count() / 40.0;
            const float last = std::max(maxAbs(tail.l, sec(39.0)), maxAbs(tail.r, sec(39.0)));
            check(last == 0.0f, t + fmt(": tail reaches exact silence (last second peak %.1e)", last));
            check(perTail < 3.0 * perBusy + 0.002, t + fmt(": decaying tail costs %.2fx of busy processing", perTail / perBusy));
            std::printf("      %-12s %7.1f x realtime\n", t.c_str(), 1.0 / perBusy);
        }
        for (const double sr : {44100.0, 96000.0}) {  // noise band-limited to 8 kHz (tape rolls off the top)
            auto fx = make(t, json::object(), sr);
            Stereo s = noise(sec(2.0, sr), dsp::dbToGain(-18.0f), 4, false);
            dsp::Biquad lp[4];
            for (int k = 0; k < 4; ++k) lp[k].set(dsp::Biquad::Type::LowPass, sr, 8000.0, k % 2 ? 1.3066 : 0.5412);
            for (std::size_t i = 0; i < s.size(); ++i) {
                s.l[i] = 1.5f * lp[1].process(lp[0].process(s.l[i]));
                s.r[i] = 1.5f * lp[3].process(lp[2].process(s.r[i]));
            }
            const double in = db(rms(s.l, s.size() / 2, s.size()));
            run(*fx, s);
            const double l = db(rms(s.l, s.size() / 2, s.size()));
            check(allFinite(s) && std::fabs(l - in) < 3.0, t + fmt(" at %.0f Hz: finite, %+.1f dB re input", sr, l - in));
        }
    }
    {  // microshift detune is exact at other sample rates too
        for (const double sr : {44100.0, 96000.0}) {
            Stereo s = sine(sec(2.0, sr), 1000.0, 0.3f, sr);
            auto fx = make("microshift", {{"mix", 1.0}, {"focus", 20}, {"detune", 15}}, sr);
            run(*fx, s);
            double first = -1, last = -1;
            int n = 0;
            for (std::size_t i = sec(0.3, sr); i < s.size(); ++i)
                if (s.l[i - 1] < 0.0f && s.l[i] >= 0.0f) {
                    const double z = static_cast<double>(i - 1) + s.l[i - 1] / (s.l[i - 1] - s.l[i]);
                    if (first < 0) first = z; else ++n;
                    last = z;
                }
            const double ct = 1200.0 * std::log2(n * sr / (last - first) / 1000.0);
            check(std::fabs(ct - 15.0) < 0.3, fmt("microshift at %.0f Hz: left voice %+.2f ct", sr, ct));
        }
    }
}

}  // namespace

int main() {
    std::printf("test_fxpremium\n");
    testFactory();
    testMicroShift();
    testShimmer();
    testTape();
    testExciter();
    testDimension();
    testCommon();
    if (g_fail) std::printf("FAILED: %d of %d check(s)\n", g_fail, g_checks);
    else std::printf("all %d checks passed\n", g_checks);
    return g_fail ? 1 : 0;
}
