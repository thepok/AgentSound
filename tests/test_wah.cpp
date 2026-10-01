// Tests for the 'wah' effect (engine/fx/WahFx.cpp): the pedal sweeps a resonance between lo and hi (heel dark, toe
// bright), automation sweeps are click-free, the auto-wah opens with the playing, strict config, determinism.

#include "analysis/ClickDetector.h"
#include "dsp/Dsp.h"
#include "fx/TimeFx.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdio>
#include <string>
#include <vector>

using namespace as;

namespace {

int gFail = 0, gChecks = 0;

void check(bool ok, const std::string& what) {
    ++gChecks;
    if (!ok) ++gFail;
    std::printf("  [%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
}

std::string fmt(const char* f, double a = 0, double b = 0, double c = 0) {
    char buf[512];
    std::snprintf(buf, sizeof buf, f, a, b, c);
    return buf;
}

constexpr double kSr = 48000.0;
constexpr double kPi = 3.14159265358979;

std::unique_ptr<Effect> make(const json& p) {
    auto fx = createTimeEffect("wah");
    fx->configure(p);
    RenderContext ctx;
    ctx.sampleRate = kSr;
    fx->prepare(ctx);
    return fx;
}

// White-ish noise (deterministic LCG).
std::vector<float> noise(long n, float amp = 0.3f) {
    std::vector<float> x(static_cast<std::size_t>(n));
    unsigned s = 12345;
    for (auto& v : x) {
        s = s * 1664525u + 1013904223u;
        v = amp * (static_cast<float>(s >> 8) / 8388608.0f - 1.0f);
    }
    return x;
}

// Amplitude of a sine at hz through the effect (steady state).
double gainAt(const json& p, double hz) {
    auto fx = make(p);
    const long n = 24000;
    std::vector<float> l(n), r(n);
    for (long i = 0; i < n; ++i) l[i] = r[i] = static_cast<float>(0.1 * std::sin(2.0 * kPi * hz * i / kSr));
    for (long o = 0; o < n; o += 256) fx->process(l.data() + o, r.data() + o, static_cast<int>(std::min(256L, n - o)), nullptr, nullptr);
    double s = 0.0;
    for (long i = n / 2; i < n; ++i) s += static_cast<double>(l[i]) * l[i];
    return std::sqrt(2.0 * s / (n / 2)) / 0.1;
}

// Spectral centroid (Hz) of a buffer span (DFT on a coarse grid).
double centroid(const std::vector<float>& x, long from, int n) {
    double num = 0.0, den = 0.0;
    for (double hz = 100.0; hz < 8000.0; hz *= 1.06) {
        std::complex<double> acc = 0.0;
        for (int i = 0; i < n; ++i) acc += static_cast<double>(x[static_cast<std::size_t>(from + i)]) * std::polar(1.0, -2.0 * kPi * hz * i / kSr);
        const double m = std::abs(acc);
        num += hz * m * m;
        den += m * m;
    }
    return num / std::max(den, 1e-12);
}

void testResponse() {
    std::printf("wah: the pedal sweeps the resonance\n");
    const json heel = {{"pedal", 0.0}, {"lo", 400}, {"hi", 2000}, {"q", 6}};
    const json toe = {{"pedal", 1.0}, {"lo", 400}, {"hi", 2000}, {"q", 6}};
    const double h400 = gainAt(heel, 400), h2000 = gainAt(heel, 2000), t400 = gainAt(toe, 400), t2000 = gainAt(toe, 2000);
    const double peak = std::pow(6.0, 0.6);
    check(std::fabs(h400 / peak - 1.0) < 0.15, fmt("heel: the resonance at 400 Hz peaks at Q^0.6 (%.2f, Q^0.6 = %.2f)", h400, peak));
    check(h400 > 4.0 * h2000, fmt("heel: dark (400 Hz %.2f vs 2 kHz %.3f)", h400, h2000));
    check(t2000 > 0.9 * peak && t2000 > 2.5 * t400, fmt("toe: bright (2 kHz %.2f vs 400 Hz %.3f)", t2000, t400));
    const double mid = gainAt({{"pedal", 0.5}, {"lo", 400}, {"hi", 2000}, {"q", 6}}, std::sqrt(400.0 * 2000.0));
    check(mid > 0.85 * peak, fmt("half-way: the resonance at the geometric middle (894 Hz gain %.2f)", mid));
    const double dry = gainAt({{"pedal", 0.0}, {"mix", 0.0}}, 3000);
    check(std::fabs(dry - 1.0) < 1e-3, fmt("mix 0 = dry (%.4f)", dry));
}

void testSweepAndAuto() {
    std::printf("wah: automation sweeps, auto-wah, determinism\n");
    const long n = 96000;
    auto run = [&](bool autoMode) {
        auto fx = make(autoMode ? json{{"mode", "auto"}, {"pedal", 0.0}, {"sens", 0.9}} : json{{"pedal", 0.0}});
        std::vector<float> l = noise(n), r = noise(n);
        if (autoMode) {   // a decaying pluck every 0.5 s
            for (long i = 0; i < n; ++i) {
                const double t = std::fmod(static_cast<double>(i) / kSr, 0.5);
                l[static_cast<std::size_t>(i)] *= static_cast<float>(std::exp(-t / 0.06));
                r[static_cast<std::size_t>(i)] = l[static_cast<std::size_t>(i)];
            }
        }
        for (long o = 0; o < n; o += 128) {
            if (!autoMode) fx->setParam("pedal", static_cast<float>(0.5 + 0.5 * std::sin(2.0 * kPi * 4.0 * o / kSr)));  // a fast wacka
            fx->process(l.data() + o, r.data() + o, 128, nullptr, nullptr);
        }
        return std::make_pair(l, r);
    };
    const auto a = run(false), b = run(false);
    check(a.first == b.first, "deterministic");
    bool finite = true;
    for (float x : a.first) finite = finite && std::isfinite(x);
    check(finite, "finite under a fast sweep");
    analysis::ClickDetector det(kSr);
    det.feed(a.first.data(), a.second.data(), static_cast<int>(n));
    det.finish();
    check(det.events().empty(), fmt("a 4 Hz pedal sweep on noise is click-free (%.0f events)", static_cast<double>(det.events().size())));
    const auto au = run(true);
    // right after a pluck the filter is open (bright), at the end of the decay closed (dark)
    const double open = centroid(au.first, static_cast<long>(0.505 * kSr), 1024), shut = centroid(au.first, static_cast<long>(0.84 * kSr), 1024);
    check(open > 1.4 * shut, fmt("auto-wah: open on the pick (centroid %.0f Hz), closing as it decays (%.0f Hz)", open, shut));
}

void testConfig() {
    std::printf("wah: strict config\n");
    bool threw = false;
    try { make({{"lo", 2000}, {"hi", 1000}}); } catch (const ConfigError&) { threw = true; }
    check(threw, "lo >= hi is an error");
    threw = false;
    try { make({{"pedal", 2}}); } catch (const ConfigError&) { threw = true; }
    check(threw, "pedal out of range is an error");
    threw = false;
    try { make({{"mode", "envelope"}}); } catch (const ConfigError&) { threw = true; }
    check(threw, "unknown mode is an error");
    auto fx = make({});
    check(fx->setParam("pedal", 0.3f) && fx->setParam("q", 7.0f) && !fx->setParam("nope", 1.0f), "pedal / q automatable, unknown -> false");
    bool help = true;
    for (const auto& sp : fx->paramSpecs()) help = help && !sp.help.empty();
    check(help, "every param has help");
}

}  // namespace

int main() {
    testResponse();
    testSweepAndAuto();
    testConfig();
    std::printf("%d/%d checks passed\n", gChecks - gFail, gChecks);
    return gFail == 0 ? 0 : 1;
}
