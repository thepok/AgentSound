// Tests for the 'amp' effect (engine/fx/AmpFx.cpp): a cascaded tube preamp + TMB tone stack + sagging push-pull
// power amp. Gain adds harmonics and compresses; the high-gain tone is odd-harmonic heavy (a single asymmetric
// waveshaper is not); the tone stack shapes; the half-band oversampling keeps aliasing down; sag compresses the
// attack and lets the note bloom back; strict config, determinism, a mono input processed once is still exact.

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
    auto fx = createTimeEffect("amp");
    fx->configure(p);
    RenderContext ctx;
    ctx.sampleRate = kSr;
    fx->prepare(ctx);
    return fx;
}

std::vector<float> run(const json& p, std::vector<float> l, std::vector<float>* rOut = nullptr, int block = 256) {
    auto fx = make(p);
    std::vector<float> r = rOut ? *rOut : l;
    const long n = static_cast<long>(l.size());
    for (long o = 0; o < n; o += block)
        fx->process(l.data() + o, r.data() + o, static_cast<int>(std::min<long>(block, n - o)), nullptr, nullptr);
    if (rOut) *rOut = r;
    return l;
}

std::vector<float> sine(double hz, double amp, long n) {
    std::vector<float> x(static_cast<std::size_t>(n));
    for (long i = 0; i < n; ++i) x[static_cast<std::size_t>(i)] = static_cast<float>(amp * std::sin(2.0 * kPi * hz * i / kSr));
    return x;
}

// Amplitude of the component at hz over [from, from + n) (Hann-windowed DFT bin).
double amp(const std::vector<float>& x, long from, long n, double hz) {
    std::complex<double> acc = 0.0;
    double wsum = 0.0;
    for (long i = 0; i < n; ++i) {
        const double w = 0.5 - 0.5 * std::cos(2.0 * kPi * i / n);
        acc += w * static_cast<double>(x[static_cast<std::size_t>(from + i)]) * std::polar(1.0, -2.0 * kPi * hz * i / kSr);
        wsum += w;
    }
    return 2.0 * std::abs(acc) / wsum;
}

double rms(const std::vector<float>& x, long from, long n) {
    double s = 0.0;
    for (long i = from; i < from + n; ++i) s += static_cast<double>(x[static_cast<std::size_t>(i)]) * x[static_cast<std::size_t>(i)];
    return std::sqrt(s / n);
}

double db(double v) { return 20.0 * std::log10(std::max(v, 1e-12)); }

void testHarmonics() {
    std::printf("amp: gain adds harmonics and compresses; odd harmonics lead at high gain\n");
    const long n = 48000;
    const double f0 = 440.0;
    auto thd = [&](const json& p, double a) {
        const auto y = run(p, sine(f0, a, n));
        double h = 0.0;
        for (int k = 2; k <= 9; ++k) h += std::pow(amp(y, 24000, 8192, f0 * k), 2);
        return std::sqrt(h) / amp(y, 24000, 8192, f0);
    };
    const double low = thd({{"gain", 1}}, 0.05), high = thd({{"gain", 8}}, 0.05);
    check(high > 4.0 * low && high > 0.3, fmt("gain 8 is much dirtier than gain 1 (THD %.3f vs %.3f)", high, low));
    // compression: 20 dB more input -> far less than 20 dB more output at high gain
    const double q = rms(run({{"gain", 8}}, sine(f0, 0.02, n)), 24000, 12000);
    const double L = rms(run({{"gain", 8}}, sine(f0, 0.2, n)), 24000, 12000);
    check(db(L / q) < 6.0, fmt("high gain compresses: +20 dB in -> %+.1f dB out", db(L / q)));
    // odd vs even at a lead setting
    const auto y = run({{"gain", 7}, {"stages", 3}}, sine(f0, 0.2, n));
    const double h2 = amp(y, 24000, 8192, 2 * f0), h3 = amp(y, 24000, 8192, 3 * f0);
    const double h4 = amp(y, 24000, 8192, 4 * f0), h5 = amp(y, 24000, 8192, 5 * f0);
    check(h3 * h3 + h5 * h5 > 4.0 * (h2 * h2 + h4 * h4),
          fmt("lead setting: odd harmonics lead (h3+h5 %.1f dB vs h2+h4 %.1f dB re h1)",
              db(std::hypot(h3, h5) / amp(y, 24000, 8192, f0)), db(std::hypot(h2, h4) / amp(y, 24000, 8192, f0))));
}

void testAliasing() {
    std::printf("amp: oversampling keeps aliasing down at high gain\n");
    const long n = 48000;
    // a guitar's top note (D6) and a tone far above it; harmonics fold back between the 'true' ones
    for (const auto& [f0, limit] : {std::pair{1174.7, -50.0}, std::pair{2960.0, -30.0}}) {
        const auto y = run({{"gain", 9}, {"stages", 4}, {"tight", 120}}, sine(f0, 0.3, n));
        double harm = 0.0, alias = 0.0;
        for (double hz = 100.0; hz < 20000.0; hz += 37.0) {
            const double m = std::fmod(hz, f0);
            const bool isHarm = std::min(m, f0 - m) < 60.0;
            const double a = amp(y, 24000, 8192, hz);
            (isHarm ? harm : alias) += a * a;
        }
        const double r = 10.0 * std::log10(alias / harm);
        check(r < limit, fmt("energy off the harmonics of a %.0f Hz tone at gain 9 / 4 stages: %.1f dB (< %.0f)", f0, r,
                             limit));
    }
}

void testToneStack() {
    std::printf("amp: the tone stack shapes\n");
    const long n = 24000;
    auto at = [&](const json& p, double hz) {   // small signal: no clipping
        json q = p;
        q["gain"] = 0;
        q["master"] = 0;
        q["stages"] = 1;
        q["sag"] = 0;
        const auto y = run(q, sine(hz, 0.002, n));
        return amp(y, 12000, 8192, hz);
    };
    const double b0 = at({{"bass", 0}}, 100), b10 = at({{"bass", 10}}, 100);
    check(db(b10 / b0) > 3.5, fmt("bass 10 vs 0 at 100 Hz: %+.1f dB (a Marshall stack at mid 5)", db(b10 / b0)));
    const double t0 = at({{"treble", 0}}, 5000), t10 = at({{"treble", 10}}, 5000);
    check(db(t10 / t0) > 6.0, fmt("treble 10 vs 0 at 5 kHz: %+.1f dB", db(t10 / t0)));
    const double m0 = at({{"mid", 0}}, 600), m10 = at({{"mid", 10}}, 600);
    check(db(m10 / m0) > 4.0, fmt("mid 10 vs 0 at 600 Hz: %+.1f dB", db(m10 / m0)));
    const double p0 = at({{"presence", 0}}, 6000), p10 = at({{"presence", 10}}, 6000);
    check(db(p10 / p0) > 8.0, fmt("presence 10 vs 0 at 6 kHz: %+.1f dB", db(p10 / p0)));
}

void testSag() {
    std::printf("amp: sag compresses the attack and blooms back\n");
    const long n = 48000;
    auto burst = [&](double sagv) {   // a loud picked note: 30 ms hard attack then a held level; the power amp clips
        std::vector<float> x = sine(330.0, 0.5, n);
        for (long i = 0; i < n; ++i) x[static_cast<std::size_t>(i)] *= static_cast<float>(i < 1440 ? 1.0 : 0.1);
        const auto y = run({{"gain", 1}, {"master", 4}, {"sag", sagv}, {"stages", 1}}, x);
        return std::make_pair(rms(y, 1920, 2400), rms(y, 24000, 9600));   // just after the attack vs held
    };
    const auto stiff = burst(0.0), spongy = burst(1.0);
    check(db(spongy.second / spongy.first) > db(stiff.second / stiff.first) + 0.5,
          fmt("after the attack the sagging supply recovers: held vs post-attack %+.1f dB (sag 1) vs %+.1f dB (sag 0)",
              db(spongy.second / spongy.first), db(stiff.second / stiff.first)));
}

void testStrictAndDeterministic() {
    std::printf("amp: strict, finite, deterministic, mono shortcut exact\n");
    bool threw = false;
    try { make({{"drive", 3}}); } catch (const std::exception&) { threw = true; }
    check(threw, "unknown param rejected");
    threw = false;
    try { make({{"stages", 2.5}}); } catch (const std::exception&) { threw = true; }
    check(threw, "stages must be a whole number");
    threw = false;
    try { make({{"stack", "vox"}}); } catch (const std::exception&) { threw = true; }
    check(threw, "unknown stack rejected");
    const long n = 48000;
    std::vector<float> x(static_cast<std::size_t>(n));
    unsigned s = 7;
    for (auto& v : x) {
        s = s * 1664525u + 1013904223u;
        v = 1.5f * (static_cast<float>(s >> 8) / 8388608.0f - 1.0f);
    }
    const json p = {{"gain", 10}, {"stages", 4}, {"boost", 20}, {"master", 10}, {"sag", 1}};
    const auto a = run(p, x), b = run(p, x);
    check(a == b, "deterministic");
    bool finite = true;
    float peak = 0.0f;
    for (float v : a) {
        finite = finite && std::isfinite(v);
        peak = std::max(peak, std::fabs(v));
    }
    check(finite && peak < 1.5f, fmt("finite and bounded on loud noise (peak %.2f)", peak));
    // a mono block is processed once: the same as a stereo pair that happens to differ nowhere
    std::vector<float> r = x;
    r[100] += 1e-3f;   // block 0 stereo -> processed per channel from then on
    std::vector<float> l2 = run(p, x, &r);
    double diff = 0.0;
    for (long i = 256; i < n; ++i) diff = std::max(diff, static_cast<double>(std::fabs(l2[static_cast<std::size_t>(i)] - a[static_cast<std::size_t>(i)])));
    check(diff < 1e-6, fmt("the left channel does not depend on the mono shortcut (max diff %.2g)", diff));
    // silence in -> silence out (no DC, no denormal residue)
    const auto z = run(p, std::vector<float>(static_cast<std::size_t>(n), 0.0f));
    check(rms(z, 0, n) < 1e-9, "silence stays silent");
    // automation glides without a jump
    // automation glides: no sample step during the change larger than the steady tone's own (after it)
    auto fx = make({{"gain", 2}});
    std::vector<float> l = sine(220.0, 0.02, n), rr = l;
    for (long o = 0; o < n; o += 64) {
        if (o == n / 2) { fx->setParam("gain", 9.0f); fx->setParam("treble", 9.0f); }
        fx->process(l.data() + o, rr.data() + o, 64, nullptr, nullptr);
    }
    auto maxStep = [&](long a, long b) {
        double m = 0.0;
        for (long i = a; i < b; ++i)
            m = std::max(m, static_cast<double>(std::fabs(l[static_cast<std::size_t>(i)] - l[static_cast<std::size_t>(i - 1)])));
        return m;
    };
    const double during = maxStep(n / 2, n / 2 + 2400), after = maxStep(n - 9600, n);
    check(during <= 1.05 * after, fmt("gain / treble automation glides (largest step %.3f, steady %.3f)", during, after));
}

}  // namespace

int main() {
    testHarmonics();
    testAliasing();
    testToneStack();
    testSag();
    testStrictAndDeterministic();
    std::printf("%d/%d checks passed\n", gChecks - gFail, gChecks);
    return gFail ? 1 : 0;
}
