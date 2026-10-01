// Tests for the de-esser (engine/fx/DynamicsFx.cpp, type "deesser"): vowels pass bit-transparent, a sibilant band
// over the threshold is reduced by about range (and never more), split mode keeps the low band intact while the
// high band dips, wide mode dips everything, the reduction recovers after the s, listen outputs the band,
// params are strict and the output is deterministic and finite. Prints every check; nonzero exit on failure.

#include "fx/DynamicsFx.h"

#include "core/Module.h"
#include "core/Params.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <memory>
#include <string>
#include <vector>

namespace {

using as::json;
constexpr double kFs = 48000.0;
constexpr double kPi = 3.14159265358979323846;
int g_failures = 0;

void check(bool ok, const std::string& what, double value = NAN) {
    if (!ok) ++g_failures;
    if (std::isnan(value)) std::printf("[%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
    else std::printf("[%s] %s  (%.3f)\n", ok ? " ok " : "FAIL", what.c_str(), value);
}

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
    std::size_t size() const { return l.size(); }
};

std::unique_ptr<as::Effect> make(const json& params = json::object()) {
    auto fx = as::createDynamicsEffect("deesser");
    fx->configure(params);
    as::RenderContext ctx;
    ctx.sampleRate = kFs;
    fx->prepare(ctx);
    return fx;
}

void run(as::Effect& fx, Stereo& io, int block = 256) {
    for (std::size_t pos = 0; pos < io.size();) {
        const int n = static_cast<int>(std::min<std::size_t>(static_cast<std::size_t>(block), io.size() - pos));
        fx.process(io.l.data() + pos, io.r.data() + pos, n, nullptr, nullptr);
        pos += static_cast<std::size_t>(n);
    }
}

void addSine(Stereo& s, double freq, double amp, std::size_t from = 0, std::size_t to = ~std::size_t{0}) {
    to = std::min(to, s.size());
    for (std::size_t i = from; i < to; ++i) {
        const auto v = static_cast<float>(amp * std::sin(2 * kPi * freq * static_cast<double>(i) / kFs));
        s.l[i] += v;
        s.r[i] += v;
    }
}

double rmsDb(const std::vector<float>& x, std::size_t a, std::size_t b) {
    double e = 0.0;
    for (std::size_t i = a; i < b; ++i) e += static_cast<double>(x[i]) * x[i];
    return 10.0 * std::log10(std::max(e / static_cast<double>(b - a), 1e-20));
}

// Amplitude of one frequency in x[a, b) (single-bin DFT).
double toneDb(const std::vector<float>& x, double freq, std::size_t a, std::size_t b) {
    double re = 0.0, im = 0.0;
    for (std::size_t i = a; i < b; ++i) {
        const double w = 2 * kPi * freq * static_cast<double>(i) / kFs;
        re += x[i] * std::cos(w);
        im += x[i] * std::sin(w);
    }
    return 20.0 * std::log10(std::max(2.0 * std::sqrt(re * re + im * im) / static_cast<double>(b - a), 1e-12));
}

bool finite(const Stereo& s) {
    for (std::size_t i = 0; i < s.size(); ++i)
        if (!std::isfinite(s.l[i]) || !std::isfinite(s.r[i])) return false;
    return true;
}

}  // namespace

int main() {
    const std::size_t n = static_cast<std::size_t>(kFs);   // 1 s

    {   // a vowel (300 Hz + harmonics under the threshold above 6.5 kHz) passes bit-transparent
        Stereo in(n);
        addSine(in, 300, 0.4);
        addSine(in, 900, 0.1);
        Stereo out = in;
        auto fx = make({{"threshold", -30}});
        run(*fx, out);
        bool same = true;
        for (std::size_t i = 0; i < n; ++i) same = same && out.l[i] == in.l[i] && out.r[i] == in.r[i];
        check(same, "a vowel under the threshold passes bit-transparent");
    }
    {   // a loud 8 kHz 's' is pushed down by about range (ratio high enough to reach it)
        Stereo in(n);
        addSine(in, 8000, 0.5);                            // -6 dBFS peak, 24 dB over -30
        Stereo out = in;
        auto fx = make({{"threshold", -30}, {"ratio", 20}, {"range", 8}});
        run(*fx, out);
        const double cut = rmsDb(in.l, n / 2, n) - rmsDb(out.l, n / 2, n);
        check(cut > 7.0 && cut < 8.6, "a loud sibilant band is reduced by about range (8 dB)", cut);
        check(finite(out), "finite output");
    }
    {   // range caps the reduction (wide: exactly; split: the band edge's phase may add up to ~1 dB near freq)
        Stereo in(n);
        addSine(in, 9000, 0.8);
        Stereo wide = in, split = in;
        auto fx = make({{"threshold", -50}, {"ratio", 20}, {"range", 4}, {"mode", "wide"}});
        run(*fx, wide);
        const double cut = rmsDb(in.l, n / 2, n) - rmsDb(wide.l, n / 2, n);
        check(cut < 4.05 && cut > 3.9, "range caps the reduction at 4 dB (wide)", cut);
        auto fs = make({{"threshold", -50}, {"ratio", 20}, {"range", 4}});
        run(*fs, split);
        const double cs = rmsDb(in.l, n / 2, n) - rmsDb(split.l, n / 2, n);
        check(cs > 3.0 && cs < 5.0, "split stays near range just above freq", cs);
    }
    {   // split: a vowel at 300 Hz under an 's' at 8 kHz keeps its level; the 8 kHz band dips. wide dips both.
        Stereo in(n);
        addSine(in, 300, 0.3);
        addSine(in, 8000, 0.3);
        Stereo split = in, wide = in;
        auto a = make({{"threshold", -30}, {"ratio", 10}, {"range", 10}});
        auto b = make({{"threshold", -30}, {"ratio", 10}, {"range", 10}, {"mode", "wide"}});
        run(*a, split);
        run(*b, wide);
        const std::size_t s0 = n / 2;
        const double lowSplit = toneDb(split.l, 300, s0, n) - toneDb(in.l, 300, s0, n);
        const double hiSplit = toneDb(split.l, 8000, s0, n) - toneDb(in.l, 8000, s0, n);
        const double lowWide = toneDb(wide.l, 300, s0, n) - toneDb(in.l, 300, s0, n);
        check(std::fabs(lowSplit) < 0.5, "split: the vowel at 300 Hz keeps its level", lowSplit);
        check(hiSplit < -6.0, "split: the 's' band at 8 kHz dips", hiSplit);
        check(lowWide < -6.0, "wide: the whole signal dips (the vowel too)", lowWide);
    }
    {   // the reduction recovers after the 's': a short burst, then the vowel alone at full level again
        Stereo in(n);
        addSine(in, 300, 0.3);
        addSine(in, 8000, 0.5, n / 10, n / 10 + n / 20);   // 50 ms 's' at 0.1 s
        Stereo out = in;
        auto fx = make({{"threshold", -30}, {"ratio", 10}, {"range", 10}, {"release", 60}, {"mode", "wide"}});
        run(*fx, out);
        const double during = rmsDb(out.l, n / 10 + n / 40, n / 10 + n / 20) - rmsDb(in.l, n / 10 + n / 40, n / 10 + n / 20);
        const double after = rmsDb(out.l, n / 2, n) - rmsDb(in.l, n / 2, n);
        check(during < -5.0, "during the 's' the gain is down", during);
        check(std::fabs(after) < 0.05, "0.35 s after it the gain is back", after);
    }
    {   // listen: the band alone
        Stereo in(n);
        addSine(in, 300, 0.4);
        addSine(in, 10000, 0.05);
        Stereo out = in;
        auto fx = make({{"listen", true}, {"threshold", 0}});
        run(*fx, out);
        const double low = toneDb(out.l, 300, n / 2, n), hi = toneDb(out.l, 10000, n / 2, n);
        check(low < -40.0 && hi > -27.0, "listen outputs the band above freq (300 Hz gone, 10 kHz there)", hi - low);
    }
    {   // strict params, determinism
        bool threw = false;
        try {
            make({{"treshold", -20}});
        } catch (const std::exception&) {
            threw = true;
        }
        check(threw, "an unknown param is an error");
        threw = false;
        try {
            make({{"freq", 500}});
        } catch (const std::exception&) {
            threw = true;
        }
        check(threw, "freq out of range is an error");
        Stereo a(n), b(n);
        addSine(a, 7000, 0.6);
        addSine(a, 200, 0.3);
        b = a;
        auto f1 = make({{"threshold", -35}}), f2 = make({{"threshold", -35}});
        run(*f1, a, 128);
        run(*f2, b, 333);
        bool same = true;
        for (std::size_t i = 0; i < n; ++i) same = same && a.l[i] == b.l[i];
        check(same, "deterministic and block-size independent");
        auto spec = as::createDynamicsEffect("deesser");
        check(spec->paramSpecs().size() == 8, "8 params, every one with a help text");
        bool help = true;
        for (const auto& ps : spec->paramSpecs()) help = help && !ps.help.empty();
        check(help, "every param has help");
    }
    std::printf("%s (%d failure%s)\n", g_failures ? "FAILED" : "PASSED", g_failures, g_failures == 1 ? "" : "s");
    return g_failures ? 1 : 0;
}
