// Tests for the convolution effect 'convolver' (engine/fx/Convolver*.cpp, engine/dsp/Fft.h).
// Deterministic; prints every check; returns nonzero on failure.
//
//   FFT against a double-precision DFT; the partitioned engine against direct convolution (< -100 dB) for
//   true-stereo IRs, many lengths and odd host blocks; a unit-impulse IR passes the input bit for bit;
//   zero latency; mono / stereo / true-stereo routing (also through the FFT partitions); block-size
//   independence and determinism; preview renders equal full renders; IR preparation (start, length,
//   reverse, stretch, normalize, trailing silence, windowed-sinc resampling of other sample rates); the
//   wet-path params; config errors that name the file; an end-to-end render; speed (>= 20x realtime with a
//   5 s stereo IR at 48 kHz).

#include "dsp/Dsp.h"
#include "dsp/Fft.h"
#include "fx/ConvolverEngine.h"
#include "fx/ConvolverIr.h"
#include "render/Registry.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"
#include "io/WavReader.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <limits>
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
namespace fs = std::filesystem;

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
fs::path gTmp;

using Channels = std::vector<std::vector<float>>;

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
    std::size_t size() const { return l.size(); }
};

double db(double x) { return 20.0 * std::log10(std::max(x, 1e-30)); }

// 32-bit float WAV (format 3) with any number of channels.
void writeWav(const fs::path& p, const Channels& ch, int rate) {
    const auto nch = static_cast<std::uint32_t>(ch.size());
    const auto frames = static_cast<std::uint32_t>(ch[0].size());
    const std::uint32_t data = frames * nch * 4;
    std::vector<unsigned char> b;
    auto u32 = [&](std::uint32_t v) { for (int i = 0; i < 4; ++i) b.push_back(static_cast<unsigned char>((v >> (8 * i)) & 0xFF)); };
    auto u16 = [&](std::uint32_t v) { b.push_back(static_cast<unsigned char>(v & 0xFF)); b.push_back(static_cast<unsigned char>((v >> 8) & 0xFF)); };
    auto tag = [&](const char* t) { b.insert(b.end(), t, t + 4); };
    tag("RIFF"); u32(36 + data); tag("WAVE");
    tag("fmt "); u32(16); u16(3); u16(nch); u32(static_cast<std::uint32_t>(rate)); u32(static_cast<std::uint32_t>(rate) * nch * 4); u16(nch * 4); u16(32);
    tag("data"); u32(data);
    for (std::uint32_t i = 0; i < frames; ++i)
        for (std::uint32_t c = 0; c < nch; ++c) {
            std::uint32_t u;
            std::memcpy(&u, &ch[c][i], 4);
            u32(u);
        }
    std::ofstream(p, std::ios::binary).write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
}

std::string irFile(const std::string& name, const Channels& ch, int rate = 48000) {
    const fs::path p = gTmp / name;
    writeWav(p, ch, rate);
    return p.generic_string();
}

std::vector<float> dirac(std::size_t len, std::size_t at, float v = 1.0f) {
    std::vector<float> h(len, 0.0f);
    h[at] = v;
    return h;
}

// Exponentially decaying noise (-60 dB after t60 samples), optionally with a first tap.
std::vector<float> decayingNoise(std::size_t n, double t60, std::uint64_t seed, float amp = 0.5f) {
    std::vector<float> h(n);
    dsp::Rng rng(seed);
    for (std::size_t i = 0; i < n; ++i) h[i] = amp * rng.bipolar() * static_cast<float>(std::pow(10.0, -3.0 * static_cast<double>(i) / t60));
    return h;
}

Stereo noise(std::size_t n, float amp, std::uint64_t seed) {
    Stereo s(n);
    dsp::Rng rng(seed);
    for (std::size_t i = 0; i < n; ++i) {
        s.l[i] = amp * rng.bipolar();
        s.r[i] = amp * rng.bipolar();
    }
    return s;
}

RenderContext context(double sr = kSr, double startBeat = 0.0, double bpm = 120.0) {
    RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.bpm = bpm;
    ctx.assetDir = "assets";
    ctx.startBeat = startBeat;
    ctx.maxBlock = 256;
    return ctx;
}

std::unique_ptr<Effect> makeFx(const json& cfg, double sr = kSr, double startBeat = 0.0) {
    auto fx = createEffect("convolver");
    fx->configure(cfg);
    fx->prepare(context(sr, startBeat));
    return fx;
}

// Runs s through fx in place, block sizes cycling through `sizes`.
void run(Effect& fx, Stereo& s, const std::vector<int>& sizes = {32}) {
    std::size_t pos = 0, k = 0;
    while (pos < s.size()) {
        const int n = static_cast<int>(std::min<std::size_t>(static_cast<std::size_t>(sizes[k++ % sizes.size()]), s.size() - pos));
        fx.process(s.l.data() + pos, s.r.data() + pos, n, nullptr, nullptr);
        pos += static_cast<std::size_t>(n);
    }
}

const std::vector<int> kOddBlocks = {32, 7, 1, 100, 256, 3, 64, 33, 250, 17};

bool identical(const Stereo& a, const Stereo& b, std::size_t offB = 0, std::size_t n = ~std::size_t{0}) {
    n = std::min(n, a.size());
    for (std::size_t i = 0; i < n; ++i)
        if (a.l[i] != b.l[offB + i] || a.r[i] != b.r[offB + i]) return false;
    return true;
}

double maxDiff(const Stereo& a, const Stereo& b, std::size_t offB = 0) {
    double d = 0.0;
    for (std::size_t i = 0; i < a.size() && offB + i < b.size(); ++i)
        d = std::max({d, double(std::fabs(a.l[i] - b.l[offB + i])), double(std::fabs(a.r[i] - b.r[offB + i]))});
    return d;
}

double rms(const std::vector<float>& x, std::size_t a, std::size_t b) {
    double e = 0.0;
    for (std::size_t i = a; i < b; ++i) e += double(x[i]) * x[i];
    return std::sqrt(e / static_cast<double>(std::max<std::size_t>(1, b - a)));
}

// Direct (double precision) convolution sample.
double direct(const Channels& ir, const std::vector<conv::Route>& routes, const Stereo& x, int out, std::size_t i) {
    double s = 0.0;
    for (const auto& r : routes) {
        if (r.out != out) continue;
        const auto& h = ir[static_cast<std::size_t>(r.ir)];
        const auto& in = r.in ? x.r : x.l;
        const std::size_t kmax = std::min(h.size(), i + 1);
        for (std::size_t k = 0; k < kmax; ++k) s += double(h[k]) * in[i - k];
    }
    return s;
}

template <class F>
std::string configError(F&& f) {
    try {
        f();
    } catch (const ConfigError& e) {
        return e.what();
    } catch (const std::exception& e) {
        return std::string("<other exception> ") + e.what();
    }
    return "";
}

// ---------------------------------------------------------------------------------------------

void testFft() {
    std::printf("dsp::Fft: radix-2^2 DIF / DIT against a double-precision DFT\n");
    dsp::Rng rng(11);
    double worst = 0.0, worstRound = 0.0;
    for (int n = 4; n <= 4096; n *= 2) {
        std::vector<float> re(static_cast<std::size_t>(n)), im(re.size());
        for (int i = 0; i < n; ++i) { re[static_cast<std::size_t>(i)] = rng.bipolar(); im[static_cast<std::size_t>(i)] = rng.bipolar(); }
        std::vector<std::complex<double>> X(re.size()), w(re.size());
        for (int j = 0; j < n; ++j) w[static_cast<std::size_t>(j)] = std::polar(1.0, -dsp::kTwoPi * j / n);
        double peak = 0.0;
        for (int k = 0; k < n; ++k) {
            std::complex<double> s = 0.0;
            for (int t = 0; t < n; ++t)
                s += std::complex<double>(re[static_cast<std::size_t>(t)], im[static_cast<std::size_t>(t)]) *
                     w[static_cast<std::size_t>((static_cast<long long>(k) * t) % n)];
            X[static_cast<std::size_t>(k)] = s;
            peak = std::max(peak, std::abs(s));
        }
        dsp::Fft f(n);
        auto a = re, b = im;
        f.forwardDif(a.data(), b.data());
        auto c = std::vector<float>(re.size()), d = c;
        for (int t = 0; t < n; ++t) {
            c[static_cast<std::size_t>(f.bitReversed()[t])] = re[static_cast<std::size_t>(t)];
            d[static_cast<std::size_t>(f.bitReversed()[t])] = im[static_cast<std::size_t>(t)];
        }
        f.forwardDit(c.data(), d.data());
        double e = 0.0;
        for (int k = 0; k < n; ++k) {
            const auto p = static_cast<std::size_t>(f.bitReversed()[k]);
            e = std::max(e, std::abs(std::complex<double>(a[p], b[p]) - X[static_cast<std::size_t>(k)]));
            e = std::max(e, std::abs(std::complex<double>(c[static_cast<std::size_t>(k)], d[static_cast<std::size_t>(k)]) - X[static_cast<std::size_t>(k)]));
        }
        worst = std::max(worst, e / peak);
        // inverse through the forward DIT on conjugated bit-reversed bins
        for (auto& v : b) v = -v;
        f.forwardDit(a.data(), b.data());
        double r = 0.0;
        for (int t = 0; t < n; ++t)
            r = std::max({r, double(std::fabs(a[static_cast<std::size_t>(t)] / n - re[static_cast<std::size_t>(t)])),
                          double(std::fabs(-b[static_cast<std::size_t>(t)] / n - im[static_cast<std::size_t>(t)]))});
        worstRound = std::max(worstRound, r);
    }
    check(worst < 1e-6, fmt("sizes 4..4096: max error %.1f dB re the spectrum peak (DIF bit-reversed out, DIT bit-reversed in)", db(worst)));
    check(worstRound < 1e-6, fmt("DIF -> conjugate -> DIT round trip: max error %.2g", worstRound));
}

void testEngine() {
    std::printf("conv::Engine: partitioned convolution vs direct convolution (true stereo, odd host blocks)\n");
    const std::vector<conv::Route> ts = {{0, 0, 0}, {0, 1, 1}, {1, 0, 2}, {1, 1, 3}};
    struct Case { int head, growth, maxBlock; std::vector<int> lengths; };
    const std::vector<Case> cases = {
        {64, 4, 16384, {1, 63, 64, 65, 300, 4097, 70001}},
        {16, 2, 256, {1, 17, 1000, 9000}},
        {32, 8, 2048, {33, 2048, 30000}},
    };
    double worst = -400.0;
    std::string where;
    bool covered = true;
    for (const Case& c : cases) {
        for (int len : c.lengths) {
            Channels ir;
            for (int k = 0; k < 4; ++k) ir.push_back(decayingNoise(static_cast<std::size_t>(len), len * 0.7 + 1, 100 + static_cast<std::uint64_t>(k * 7 + len)));
            const std::size_t n = static_cast<std::size_t>(len) + 12000;
            const Stereo x = noise(n, 0.5f, static_cast<std::uint64_t>(len));
            conv::Engine e;
            e.prepare(ir, ts, 0, {c.head, c.growth, c.maxBlock});
            const auto plan = e.plan();
            const long long end = plan.empty() ? c.head : static_cast<long long>(plan.back().block) * (plan.back().firstPartition + plan.back().partitions);
            covered = covered && (end >= len) && (plan.empty() || plan.front().block == c.head);
            Stereo y(n);
            std::size_t pos = 0, k = 0;
            while (pos < n) {
                const int m = static_cast<int>(std::min<std::size_t>(static_cast<std::size_t>(kOddBlocks[k++ % kOddBlocks.size()]), n - pos));
                e.process(x.l.data() + pos, x.r.data() + pos, y.l.data() + pos, y.r.data() + pos, m);
                pos += static_cast<std::size_t>(m);
            }
            double err = 0.0, peak = 0.0;
            const std::size_t step = std::max<std::size_t>(1, n / 300);
            for (std::size_t i = 0; i < n; i += step) {
                for (int o = 0; o < 2; ++o) {
                    const double ref = direct(ir, ts, x, o, i);
                    err = std::max(err, std::fabs(ref - (o ? y.r[i] : y.l[i])));
                    peak = std::max(peak, std::fabs(ref));
                }
            }
            const double rel = db(err / peak);
            if (rel > worst) { worst = rel; where = fmt("head %d growth %d max %d, IR %d", c.head, c.growth, c.maxBlock, len); }
        }
    }
    check(worst < -100.0, fmt("max error %.1f dB re the output peak (worst: %s)", worst, where.c_str()));
    check(covered, "the partition plan starts at the head and covers every IR sample");
    conv::Engine e;
    e.prepare({std::vector<float>(240000, 0.001f), std::vector<float>(240000, 0.001f)}, {{0, 0, 0}, {1, 1, 1}}, 0);
    std::string plan;
    for (const auto& L : e.plan()) plan += fmt(" %dx%d", L.block, L.partitions);
    check(plan == " 64x3 256x3 1024x3 4096x3 16384x14", "default plan for a 5 s IR at 48 kHz:" + plan);
}

void testUnitImpulse() {
    std::printf("unit-impulse IR: the input passes through bit for bit; delayed impulse: a pure delay\n");
    const Stereo x = noise(30000, 0.7f, 5);
    const std::vector<std::pair<std::string, Channels>> irs = {
        {"mono", {{1.0f}}},
        {"stereo", {{1.0f}, {1.0f}}},
        {"true stereo", {{1.0f}, {0.0f}, {0.0f}, {1.0f}}},
    };
    for (const auto& [name, ch] : irs) {
        const std::string path = irFile("unit_" + std::to_string(ch.size()) + ".wav", ch);
        for (const bool norm : {true, false}) {
            auto fx = makeFx({{"ir", path}, {"normalize", norm}});
            Stereo y = x;
            run(*fx, y, kOddBlocks);
            check(identical(y, x), fmt("%s unit impulse, normalize %s: output == input (bit-identical, odd blocks)", name.c_str(), norm ? "on" : "off"));
        }
    }
    const std::string delayed = irFile("delayed.wav", {dirac(3001, 3000)});
    auto fx = makeFx({{"ir", delayed}, {"normalize", false}});
    Stereo y = x;
    run(*fx, y, kOddBlocks);
    double err = 0.0;
    for (std::size_t i = 0; i < y.size(); ++i) {
        const float wl = i < 3000 ? 0.0f : x.l[i - 3000], wr = i < 3000 ? 0.0f : x.r[i - 3000];
        err = std::max({err, double(std::fabs(y.l[i] - wl)), double(std::fabs(y.r[i] - wr))});
    }
    check(err < 1e-6, fmt("impulse at 3000 (through the FFT partitions): output = input delayed 3000 samples, max error %.2g", err));

    // the file cache notices a rewritten file (same path, new content)
    const std::string again = irFile("rewritten.wav", {{1.0f}});
    Stereo a = x;
    run(*makeFx({{"ir", again}, {"normalize", false}}), a);
    irFile("rewritten.wav", {dirac(6, 5, 0.5f)});
    Stereo b = x;
    run(*makeFx({{"ir", again}, {"normalize", false}}), b);
    check(identical(a, x) && b.l[5] == 0.5f * x.l[0] && b.l[0] == 0.0f, "an IR file rewritten between two renders of one process is read again");
}

void testZeroLatency() {
    std::printf("zero latency\n");
    std::vector<float> h = decayingNoise(24000, 20000, 3);
    h[0] = 0.8f;
    const std::string path = irFile("latency.wav", {h});
    auto fx = makeFx({{"ir", path}, {"normalize", false}});
    check(fx->latencySamples() == 0, "latencySamples() == 0");
    Stereo s(40000);
    s.l[777] = 1.0f;
    run(*fx, s);
    bool before = true;
    for (std::size_t i = 0; i < 777; ++i) before = before && s.l[i] == 0.0f;
    double err = 0.0, rightPeak = 0.0;
    for (std::size_t k = 0; k < h.size(); ++k) err = std::max(err, double(std::fabs(s.l[777 + k] - h[k])));
    for (float v : s.r) rightPeak = std::max(rightPeak, double(std::fabs(v)));
    check(before && s.l[777] == 0.8f, fmt("an impulse at sample 777 answers at sample 777 (%.6f = the IR's first tap), nothing before", s.l[777]));
    check(err < 1e-6 && rightPeak < 1e-6,
          fmt("the whole impulse response is the IR (max error %.2g); mono IR: no crosstalk (right %.2g: FFT rounding)", err, rightPeak));
    check(std::fabs(fx->tailSeconds() - (24000.0 / kSr + 0.05)) < 1e-6, fmt("tailSeconds = IR length + predelay (+50 ms): %.3f s", fx->tailSeconds()));
}

void testRouting() {
    std::printf("routing: mono, stereo, true stereo (direct part and FFT partitions)\n");
    auto response = [](const std::string& path, bool fromRight, std::size_t n) {
        auto fx = makeFx({{"ir", path}, {"normalize", false}});
        Stereo s(n);
        (fromRight ? s.r : s.l)[100] = 1.0f;
        run(*fx, s, kOddBlocks);
        return s;
    };
    // expected: list of (channel, index, value); everything else ~0
    auto matches = [](const Stereo& s, const std::vector<std::tuple<int, std::size_t, float>>& peaks, double tol) {
        Stereo want(s.size());
        for (const auto& [c, i, v] : peaks) (c ? want.r : want.l)[i] = v;
        return maxDiff(s, want) <= tol;
    };
    const std::string ts = irFile("ts_short.wav", {dirac(31, 0, 1.0f), dirac(31, 10, 0.5f), dirac(31, 20, 0.25f), dirac(31, 30, 0.125f)});
    check(matches(response(ts, false, 400), {{0, 100, 1.0f}, {1, 110, 0.5f}}, 0.0) &&
              matches(response(ts, true, 400), {{0, 120, 0.25f}, {1, 130, 0.125f}}, 0.0),
          "true stereo (4 ch, direct part): L -> LL to L + LR to R, R -> RL to L + RR to R, exact");
    const std::string tl = irFile("ts_long.wav", {dirac(20001, 0, 1.0f), dirac(20001, 5000, 0.5f), dirac(20001, 9000, 0.25f), dirac(20001, 20000, 0.125f)});
    check(matches(response(tl, false, 22000), {{0, 100, 1.0f}, {1, 5100, 0.5f}}, 1e-6) &&
              matches(response(tl, true, 22000), {{0, 9100, 0.25f}, {1, 20100, 0.125f}}, 1e-6),
          "true stereo through the FFT partitions (taps at 5000 / 9000 / 20000): routed right within 1e-6");
    const std::string st = irFile("st.wav", {dirac(6, 0, 1.0f), dirac(6, 5, 0.5f)});
    check(matches(response(st, false, 300), {{0, 100, 1.0f}}, 0.0) && matches(response(st, true, 300), {{1, 105, 0.5f}}, 0.0),
          "stereo IR: L -> L and R -> R only, no crosstalk");
    const std::string mo = irFile("mono3.wav", {dirac(4, 3, 1.0f)});
    check(matches(response(mo, false, 300), {{0, 103, 1.0f}}, 0.0) && matches(response(mo, true, 300), {{1, 103, 1.0f}}, 0.0),
          "mono IR: the same IR on each side, no crosstalk");

    // several files = one IR: 4 mono (LL, LR, RL, RR: the Lexicon 224XL sets), 2 stereo (left-input file,
    // right-input file: Bricasti .L/.R pairs), 2 mono (left, right)
    auto responseOf = [](const json& ir, bool fromRight, std::size_t n) {
        auto fx = makeFx({{"ir", ir}, {"normalize", false}});
        Stereo s(n);
        (fromRight ? s.r : s.l)[100] = 1.0f;
        run(*fx, s, kOddBlocks);
        return s;
    };
    const json four = json::array({irFile("q_ll.wav", {dirac(31, 0, 1.0f)}), irFile("q_lr.wav", {dirac(31, 10, 0.5f)}),
                                   irFile("q_rl.wav", {dirac(31, 20, 0.25f)}), irFile("q_rr.wav", {dirac(31, 30, 0.125f)})});
    check(matches(responseOf(four, false, 400), {{0, 100, 1.0f}, {1, 110, 0.5f}}, 0.0) &&
              matches(responseOf(four, true, 400), {{0, 120, 0.25f}, {1, 130, 0.125f}}, 0.0),
          "4 mono files = true stereo LL, LR, RL, RR");
    const json two = json::array({irFile("p_l.wav", {dirac(31, 0, 1.0f), dirac(31, 10, 0.5f)}),
                                  irFile("p_r.wav", {dirac(31, 20, 0.25f), dirac(31, 30, 0.125f)})});
    check(matches(responseOf(two, false, 400), {{0, 100, 1.0f}, {1, 110, 0.5f}}, 0.0) &&
              matches(responseOf(two, true, 400), {{0, 120, 0.25f}, {1, 130, 0.125f}}, 0.0),
          "2 stereo files = true stereo (the left input's response, then the right input's)");
    const json monos = json::array({irFile("m_l.wav", {dirac(6, 0, 1.0f)}), irFile("m_r.wav", {dirac(6, 5, 0.5f)})});
    check(matches(responseOf(monos, false, 300), {{0, 100, 1.0f}}, 0.0) && matches(responseOf(monos, true, 300), {{1, 105, 0.5f}}, 0.0),
          "2 mono files = stereo (left, right)");
}

void testDeterminism() {
    std::printf("determinism and block-size independence\n");
    const std::string st = irFile("room_st.wav", {decayingNoise(57600, 40000, 21), decayingNoise(57600, 40000, 22)});
    const std::string ts = irFile("room_ts.wav", {decayingNoise(30000, 20000, 31), decayingNoise(30000, 20000, 32),
                                                  decayingNoise(30000, 20000, 33), decayingNoise(30000, 20000, 34)});
    const Stereo x = noise(96000, 0.5f, 77);
    for (const auto& path : {st, ts}) {
        const json cfg = {{"ir", path}, {"mix", 0.6}, {"predelay", 12}, {"lowcut", 150}, {"highcut", 9000}, {"width", 1.3}};
        Stereo a = x, b = x, c = x, d = x;
        run(*makeFx(cfg), a, {32});
        run(*makeFx(cfg), b, {32});
        run(*makeFx(cfg), c, {256});
        run(*makeFx(cfg), d, kOddBlocks);
        const char* what = path == st ? "stereo" : "true stereo";
        check(identical(a, b), fmt("%s: two renders are bit-identical", what));
        check(identical(a, c) && identical(a, d), fmt("%s: 32-sample, 256-sample and odd host blocks give bit-identical output", what));
    }
}

void testPreview() {
    std::printf("preview renders (startBeat) equal the same span of a full render\n");
    const std::string st = irFile("preview_st.wav", {decayingNoise(60000, 40000, 41), decayingNoise(60000, 40000, 42)});
    const json cfg = {{"ir", st}, {"mix", 0.5}, {"predelay", 20}, {"lowcut", 200}};
    for (const double beat : {13.5, 13.5 + 5.0 / 24000.0, 7.0 + 1.0 / 3.0}) {
        const auto start = static_cast<std::size_t>(std::llround(beat * kSr * 60.0 / 120.0));
        const std::size_t span = 60000;
        const Stereo in = noise(span, 0.5f, 99);
        Stereo full(start + span);
        std::copy(in.l.begin(), in.l.end(), full.l.begin() + static_cast<std::ptrdiff_t>(start));
        std::copy(in.r.begin(), in.r.end(), full.r.begin() + static_cast<std::ptrdiff_t>(start));
        run(*makeFx(cfg), full, {32});
        Stereo prev = in;
        run(*makeFx(cfg, kSr, beat), prev, {32});
        double peak = 0.0;
        for (std::size_t i = 0; i < span; ++i) peak = std::max(peak, double(std::fabs(full.l[start + i])));
        check(identical(prev, full, start) && peak > 0.01,
              fmt("beat %.6g: preview == full render from sample %zu (bit-identical, peak %.2f)", beat, start, peak));
    }
}

void testIrPreparation() {
    std::printf("IR preparation: start, length, trailing silence, reverse, stretch, normalize, resampling\n");
    conv::IrOptions raw;
    raw.normalize = false;
    {
        std::vector<float> h(961, 0.0f);
        h[480] = 1.0f;
        h[960] = 0.5f;
        conv::IrOptions o = raw;
        o.startMs = 10.0;
        const auto ir = conv::prepareIr({h}, 48000, o, "t");
        check(ir.channels[0].size() == 481 && ir.channels[0][0] == 1.0f && ir.channels[0][480] == 0.5f,
              "start 10 ms skips 480 samples of a 48 kHz file (the IR starts at its direct sound)");
    }
    {
        const auto h = decayingNoise(48000, 1e9, 5);
        conv::IrOptions o = raw;
        o.lengthSec = 0.5;
        const auto ir = conv::prepareIr({h}, 48000, o, "t");
        const auto& c = ir.channels[0];
        const bool fade = c.size() == 24000 && c[23999] == 0.0f && c[17999] == h[17999] &&
                          std::fabs(c[20999] - 0.5f * h[20999]) < 1e-6f;
        check(fade, "length 0.5 s keeps 24000 samples, raised-cosine fade over the last quarter (ends at 0)");
    }
    {
        // a 0.5 s decay into 4 s of noise floor 100 dB under the peak (24-bit dither): cut where the decay passes
        // -80 dB, the decay itself untouched; a decay that is still going on is kept whole
        auto h = decayingNoise(static_cast<std::size_t>(4.5 * kSr), 0.5 * kSr, 44, 0.5f);
        dsp::Rng rng(45);
        for (float& v : h) v += 0.5f * 1e-5f * rng.bipolar();
        const auto cut = conv::prepareIr({h}, 48000, raw, "t");
        const std::size_t n = cut.channels[0].size();
        bool same = true;
        for (std::size_t i = 0; i < 24000; ++i) same = same && cut.channels[0][i] == h[i];
        check(n > static_cast<std::size_t>(0.6 * kSr) && n < static_cast<std::size_t>(0.9 * kSr) && same,
              fmt("the tail 80 dB under the peak (here a -100 dB noise floor after a 0.5 s decay) is dropped: 4.5 s -> %.2f s, "
                  "the decay unchanged", n / kSr));
        const auto longDecay = decayingNoise(static_cast<std::size_t>(4.5 * kSr), 6.0 * kSr, 46, 0.5f);
        check(conv::prepareIr({longDecay}, 48000, raw, "t").channels[0].size() == longDecay.size(), "a decay that is still going on is kept whole");
    }
    {
        // float IR files keep denormal / near-denormal 'silence' (before the direct sound, in fades): every product
        // with such a tap is a denormal (several times slower on x86), so taps 200 dB under the peak become zeros
        auto h = decayingNoise(20000, 15000, 12);
        for (std::size_t i = 0; i < 300; ++i) h[i] = (i % 2 ? 1e-40f : -3e-39f);  // denormal pre-delay
        for (std::size_t i = 5000; i < 5100; ++i) h[i] = 1e-12f;                  // -200 dB and more under the peak
        const auto ir = conv::prepareIr({h, h}, 48000, raw, "t");
        bool denormal = false, zeroed = true, kept = true;
        for (const auto& c : ir.channels) {
            for (std::size_t i = 0; i < c.size(); ++i) {
                denormal = denormal || std::fpclassify(c[i]) == FP_SUBNORMAL;
                if (i < 300 || (i >= 5000 && i < 5100)) zeroed = zeroed && c[i] == 0.0f;
                else kept = kept && c[i] == h[i];
            }
        }
        check(!denormal && zeroed && kept, "taps more than 200 dB under the peak (denormals) become exact zeros, the rest is untouched");
        conv::Engine a, b;
        std::vector<float> dn = h, zero = h;
        for (std::size_t i = 0; i < 300; ++i) zero[i] = 0.0f;
        a.prepare({dn}, {{0, 0, 0}, {1, 1, 0}}, 0);
        b.prepare({zero}, {{0, 0, 0}, {1, 1, 0}}, 0);
        Stereo x = noise(30000, 0.5f, 13), ya(30000), yb(30000);
        a.process(x.l.data(), x.r.data(), ya.l.data(), ya.r.data(), 30000);
        b.process(x.l.data(), x.r.data(), yb.l.data(), yb.r.data(), 30000);
        check(identical(ya, yb), "conv::Engine: denormal IR taps are flushed (same output as zero taps)");
        std::vector<float> bad = decayingNoise(1000, 800, 14);
        bad[400] = std::numeric_limits<float>::quiet_NaN();
        const std::string m = configError([&] { conv::prepareIr({bad}, 48000, raw, "IR 'nan.wav'"); });
        check(m.find("nan.wav") != std::string::npos && m.find("NaN") != std::string::npos, "an IR with NaN samples is a config error: " + m);
        bad[400] = std::numeric_limits<float>::infinity();
        check(!configError([&] { conv::prepareIr({bad}, 48000, raw, "t"); }).empty(), "an IR with infinite samples is a config error");
    }
    {
        const auto ir = conv::prepareIr({{1.0f, 0.5f, 0.0f, 0.0f, 1e-9f}}, 48000, raw, "t");
        check(ir.channels[0].size() == 2, "trailing silence (below -120 dB re the peak) is dropped");
        conv::IrOptions o = raw;
        o.reverse = true;
        const auto rv = conv::prepareIr({{1.0f, 0.5f, 0.25f}}, 48000, o, "t");
        check(rv.channels[0] == std::vector<float>({0.25f, 0.5f, 1.0f}), "reverse plays the IR backwards");
    }
    {
        // a smooth (low-passed) noise IR: stretch 2 doubles its length and keeps its energy
        auto h = decayingNoise(24000, 30000, 8);
        float z = 0.0f;
        for (float& v : h) v = z += 0.2f * (v - z);
        conv::IrOptions o = raw;
        o.stretch = 2.0;
        const auto ir = conv::prepareIr({h}, 48000, o, "t");
        double e0 = 0.0, e1 = 0.0;
        for (float v : h) e0 += double(v) * v;
        for (float v : ir.channels[0]) e1 += double(v) * v;
        // (the resampler's kernel support: up to resampleDelay samples of pre-ringing, trimmed where under -70 dB)
        const long n = static_cast<long>(ir.channels[0].size()), body = 2 * (24000 - 1) + 1, d = conv::resampleDelay(2.0);
        check(n >= body + d - 2 && n <= body + 2 * d + 2 && std::fabs(db(std::sqrt(e1 / e0))) < 0.1,
              fmt("stretch 2: twice as long (%ld samples), energy kept (%.3f dB)", n, db(std::sqrt(e1 / e0))));
    }
    {
        bool ok = true;
        for (int nch : {1, 2, 4}) {
            Channels loud, quiet;
            for (int c = 0; c < nch; ++c) {
                loud.push_back(decayingNoise(5000, 3000, 50 + static_cast<std::uint64_t>(c)));
                quiet.push_back(loud.back());
                for (float& v : quiet.back()) v *= 0.01f;
            }
            const auto a = conv::prepareIr(loud, 48000, {}, "t"), b = conv::prepareIr(quiet, 48000, {}, "t");
            double e = 0.0, d = 0.0;
            for (const auto& r : a.routes)
                for (float v : a.channels[static_cast<std::size_t>(r.ir)]) e += double(v) * v;
            for (std::size_t c = 0; c < a.channels.size(); ++c)
                for (std::size_t i = 0; i < a.channels[c].size(); ++i) d = std::max(d, double(std::fabs(a.channels[c][i] - b.channels[c][i])));
            ok = ok && std::fabs(e / 2.0 - 1.0) < 1e-5 && d < 1e-5;
        }
        check(ok, "normalize: unit energy per output channel (mono, stereo, true stereo); a -40 dB copy of an IR ends up the same");
    }
    // windowed-sinc resampling
    auto sineErr = [](double fromRate, double toRate, std::vector<double> hz, double amp) {
        const std::size_t n = static_cast<std::size_t>(fromRate);  // 1 s
        std::vector<float> x(n);
        for (std::size_t i = 0; i < n; ++i) {
            double v = 0.0;
            for (double f : hz) v += amp * std::sin(dsp::kTwoPi * f * static_cast<double>(i) / fromRate);
            x[i] = static_cast<float>(v);
        }
        const double ratio = toRate / fromRate;
        const auto y = conv::resample(x, ratio);
        const int delay = conv::resampleDelay(ratio);
        double err = 0.0, peak = 0.0;
        for (std::size_t m = static_cast<std::size_t>(delay) + 4000; m < static_cast<std::size_t>(delay) + static_cast<std::size_t>(0.9 * toRate); ++m) {
            const double t = static_cast<double>(static_cast<long long>(m) - delay) / toRate;
            double v = 0.0;
            for (double f : hz)  // components above the new Nyquist must vanish
                if (f < 0.5 * toRate) v += amp * std::sin(dsp::kTwoPi * f * t);
            err = std::max(err, std::fabs(y[m] - v));
            peak = std::max(peak, std::fabs(v));
        }
        return std::pair<double, double>{err, peak};
    };
    const auto [e1, p1] = sineErr(44100, 48000, {1000.0, 10000.0}, 0.4);
    const auto [e2, p2] = sineErr(96000, 48000, {1000.0, 15000.0}, 0.4);
    const auto [e3, p3] = sineErr(96000, 48000, {30000.0}, 0.8);  // above the new Nyquist: must vanish
    check(db(e1 / p1) < -100.0 && db(e2 / p2) < -100.0,
          fmt("resampling 44.1 -> 48 kHz and 96 -> 48 kHz: 1 / 10 / 15 kHz sines within %.1f / %.1f dB of exact", db(e1 / p1), db(e2 / p2)));
    check(db(e3 / 0.8) < -90.0, fmt("96 -> 48 kHz: a 30 kHz sine (above the new Nyquist) is suppressed to %.1f dB", db(e3 / 0.8)));
    check(conv::resampleDelay(48000.0 / 44100.0) <= 60 && conv::resampleDelay(0.5) <= 60,
          fmt("resample() keeps the kernel's whole support: its output starts %d / %d samples (about 1 ms) early",
              conv::resampleDelay(48000.0 / 44100.0), conv::resampleDelay(0.5)));

    // zero latency through resampling: prepareIr trims the pre-ringing head where it is under -70 dB, so an IR keeps
    // the file's timing (exactly when there is silence before the direct sound; a hard onset at sample 0 keeps only
    // the part of the pre-ringing that matters)
    for (const int rate : {44100, 96000, 32000}) {
        std::vector<float> h(static_cast<std::size_t>(rate / 5), 0.0f);  // 10 ms silence, a smooth 1 ms pulse, a decay
        const std::size_t at = static_cast<std::size_t>(rate / 100), w = static_cast<std::size_t>(rate / 1000);
        for (std::size_t i = 0; i < w; ++i) h[at + i] = static_cast<float>(0.5 - 0.5 * std::cos(dsp::kTwoPi * (i + 0.5) / w));
        dsp::Rng rng(static_cast<std::uint64_t>(rate));
        for (std::size_t i = at + w; i < h.size(); ++i) h[i] = 0.1f * rng.bipolar() * std::exp(-static_cast<float>(i - at) / (0.03f * rate));
        const auto ir = conv::prepareIr({h}, rate, raw, "t");
        std::size_t pk = 0;
        for (std::size_t i = 0; i < ir.channels[0].size(); ++i)
            if (std::fabs(ir.channels[0][i]) > std::fabs(ir.channels[0][pk])) pk = i;
        const double want = (static_cast<double>(at) + 0.5 * static_cast<double>(w) - 0.5) * 48000.0 / rate;
        check(std::fabs(static_cast<double>(pk) - want) <= 1.0,
              fmt("%d Hz IR with 10 ms of silence: its pulse lands at 48 kHz sample %zu (file time: %.1f) - no resampling delay", rate, pk, want));
    }
    {
        const auto hard = decayingNoise(4410, 3000, 15);  // full level from the first sample: the worst case
        const auto ir = conv::prepareIr({hard}, 44100, raw, "t");
        const auto full = conv::resample(hard, 48000.0 / 44100.0);
        const long shift = static_cast<long>(full.size() - ir.channels[0].size());
        double lost = 0.0, total = 0.0;
        for (long i = 0; i < static_cast<long>(full.size()); ++i) (i < shift ? lost : total) += double(full[static_cast<std::size_t>(i)]) * full[static_cast<std::size_t>(i)];
        bool same = true;  // the rest is the resampled IR (scaled by the rate)
        const float g = static_cast<float>(44100.0 / 48000.0);
        for (std::size_t i = 0; i < ir.channels[0].size(); ++i) same = same && std::fabs(ir.channels[0][i] - g * full[i + static_cast<std::size_t>(shift)]) < 1e-6f;
        check(shift >= 0 && shift <= conv::resampleDelay(48000.0 / 44100.0) && db(std::sqrt(lost / total)) < -69.0 && same,
              fmt("a hard onset at 44.1 kHz: %ld of %d pre-ringing samples trimmed (%.1f dB of the energy), the rest kept", shift,
                  conv::resampleDelay(48000.0 / 44100.0), 10.0 * std::log10(std::max(lost, 1e-300) / total)));
    }

    // an IR at another rate, through the effect: same filter (DC gain kept, normalize off)
    for (const int rate : {44100, 24000, 96000}) {
        const std::string path = irFile("rate_" + std::to_string(rate) + ".wav", {dirac(static_cast<std::size_t>(rate / 100), 0)}, rate);
        auto fx = makeFx({{"ir", path}, {"normalize", false}});
        Stereo s(24000);
        for (std::size_t i = 0; i < s.size(); ++i) s.l[i] = s.r[i] = 0.25f;
        run(*fx, s);
        const double dc = rms(s.l, 12000, 24000);
        check(std::fabs(dc / 0.25 - 1.0) < 1e-3,  // (the kernel's far pre-ringing, under -70 dB, is trimmed)
              fmt("unit impulse at %d Hz rendered at 48 kHz: DC gain %.6f (within 0.01 dB)", rate, dc / 0.25));
    }
}

void testParams() {
    std::printf("wet path: mix, gain, predelay, lowcut, highcut, width; automation\n");
    const std::string unit = irFile("unit_p.wav", {{1.0f}});
    const Stereo x = noise(24000, 0.5f, 123);
    {
        auto fx = makeFx({{"ir", unit}, {"mix", 0}});
        Stereo y = x;
        run(*fx, y);
        check(identical(y, x), "mix 0: dry only, bit-identical");
    }
    {
        auto fx = makeFx({{"ir", unit}, {"gain", -6}});
        Stereo y = x;
        run(*fx, y);
        double err = 0.0;
        const float g = dsp::dbToGain(-6.0f);
        for (std::size_t i = 0; i < y.size(); ++i) err = std::max(err, double(std::fabs(y.l[i] - g * x.l[i])));
        check(err < 1e-7, "gain -6 dB scales the wet signal");
    }
    {
        auto fx = makeFx({{"ir", unit}, {"predelay", 10}});
        Stereo y = x;
        run(*fx, y, kOddBlocks);
        bool ok = true;
        for (std::size_t i = 0; i < y.size(); ++i) ok = ok && y.l[i] == (i < 480 ? 0.0f : x.l[i - 480]) && y.r[i] == (i < 480 ? 0.0f : x.r[i - 480]);
        check(ok, "predelay 10 ms: the wet signal is the input 480 samples later, exactly");
        check(std::fabs(fx->tailSeconds() - (1.0 / kSr + 0.01 + 0.05)) < 1e-6, "tailSeconds includes the predelay");
    }
    {
        // predelay automation glides (no jumps), then settles on exact whole-sample taps
        auto fx = makeFx({{"ir", unit}, {"predelay", 5}});
        const std::size_t n = 144000;
        Stereo s(n);
        for (std::size_t i = 0; i < n; ++i) s.l[i] = s.r[i] = static_cast<float>(0.5 * std::sin(dsp::kTwoPi * 220.0 * static_cast<double>(i) / kSr));
        const Stereo in = s;
        std::size_t pos = 0;
        while (pos < n) {
            if (pos == 9600) fx->setParam("predelay", 25.0f);
            fx->process(s.l.data() + pos, s.r.data() + pos, 32, nullptr, nullptr);
            pos += 32;
        }
        double jump = 0.0;
        for (std::size_t i = 241; i < n; ++i) jump = std::max(jump, double(std::fabs(s.l[i] - s.l[i - 1])));
        bool settled = true;
        for (std::size_t i = 120000; i < n; ++i) settled = settled && s.l[i] == in.l[i - 1200];
        check(jump < 0.03, fmt("predelay 5 -> 25 ms: a glide, largest step %.4f (a 220 Hz sine moves up to 0.0144 per sample)", jump));
        check(settled, "after the glide the delay reads exact whole samples again (1200)");
    }
    {
        auto tone = [&](const json& cfg, double hz) {
            auto fx = makeFx(cfg);
            Stereo s(24000);
            for (std::size_t i = 0; i < s.size(); ++i) s.l[i] = s.r[i] = static_cast<float>(0.5 * std::sin(dsp::kTwoPi * hz * static_cast<double>(i) / kSr));
            const double in = rms(s.l, 12000, 24000);
            run(*fx, s);
            return db(rms(s.l, 12000, 24000) / in);
        };
        const double lo100 = tone({{"ir", unit}, {"lowcut", 1000}}, 100), lo5k = tone({{"ir", unit}, {"lowcut", 1000}}, 5000);
        const double hi10k = tone({{"ir", unit}, {"highcut", 2000}}, 10000), hi200 = tone({{"ir", unit}, {"highcut", 2000}}, 200);
        check(lo100 < -30.0 && std::fabs(lo5k) < 0.5, fmt("lowcut 1 kHz: 100 Hz %.1f dB, 5 kHz %.2f dB", lo100, lo5k));
        check(hi10k < -20.0 && std::fabs(hi200) < 0.5, fmt("highcut 2 kHz: 10 kHz %.1f dB, 200 Hz %.2f dB", hi10k, hi200));
    }
    {
        const std::string st = irFile("wide.wav", {decayingNoise(2000, 1500, 61), decayingNoise(2000, 1500, 62)});
        auto fx = makeFx({{"ir", st}, {"width", 0}});
        Stereo y = x;
        run(*fx, y);
        double d = 0.0;
        for (std::size_t i = 0; i < y.size(); ++i) d = std::max(d, double(std::fabs(y.l[i] - y.r[i])));
        check(d < 1e-6, "width 0: the wet signal is mono");
    }
    {
        // crossfeed: each input side into the other before the IR, power-kept; 0 = exact pass-through
        const std::string st = irFile("xfeed.wav", {decayingNoise(2400, 2000, 81), decayingNoise(2400, 2000, 82)});
        Stereo left(24000);  // a hard-left source
        {
            dsp::Rng rng(91);
            for (std::size_t i = 0; i < left.size(); ++i) left.l[i] = 0.5f * rng.bipolar();
        }
        auto wet = [&](const json& cfg, const Stereo& in) {
            auto fx = makeFx(cfg);
            Stereo y = in;
            run(*fx, y, kOddBlocks);
            return y;
        };
        const Stereo plain = wet({{"ir", st}}, left), zero = wet({{"ir", st}, {"crossfeed", 0}}, left);
        check(identical(plain, zero), "crossfeed 0: bit-identical to no crossfeed");
        const double rPlain = rms(plain.r, 2400, 24000), lPlain = rms(plain.l, 2400, 24000);
        check(rPlain < 1e-6 * lPlain, "2-channel IR, crossfeed 0: a hard-left source leaves the right side silent");
        const Stereo half = wet({{"ir", st}, {"crossfeed", 0.5}}, left);
        const double lHalf = rms(half.l, 2400, 24000), rHalf = rms(half.r, 2400, 24000);
        const double side = db(rHalf / lHalf), total = db(std::sqrt(lHalf * lHalf + rHalf * rHalf) / lPlain);
        check(side > -8.0 && side < -4.0, fmt("crossfeed 0.5: the right side answers a hard-left source %.1f dB under the "
                                             "left (20log 0.5 = -6)", side));
        check(std::fabs(total) < 0.5, fmt("crossfeed 0.5: power kept for a panned source (%.2f dB)", total));
        Stereo centre(24000);
        for (std::size_t i = 0; i < centre.size(); ++i) centre.l[i] = centre.r[i] = left.l[i];
        const Stereo c0 = wet({{"ir", st}}, centre), c1 = wet({{"ir", st}, {"crossfeed", 1}}, centre);
        const double gain = db(rms(c1.l, 2400, 24000) / rms(c0.l, 2400, 24000));
        check(std::fabs(gain - 3.01) < 0.05, fmt("crossfeed 1 on a centred source: +3 dB (%.2f)", gain));
        auto fx = makeFx({{"ir", st}});
        check(fx->setParam("crossfeed", 0.4f), "crossfeed is automatable");
    }
    {
        auto fx = makeFx({{"ir", unit}});
        check(fx->setParam("mix", 0.5f) && fx->setParam("lowcut", 300.0f) && fx->setParam("predelay", 40.0f),
              "mix / lowcut / predelay are automatable");
        check(!fx->setParam("ir", 1.0f) && !fx->setParam("start", 5.0f) && !fx->setParam("length", 1.0f) && !fx->setParam("stretch", 1.5f) &&
                  !fx->setParam("normalize", 0.0f) && !fx->setParam("reverse", 1.0f),
              "ir / start / length / stretch / normalize / reverse are fixed at prepare (setParam refuses them)");
    }
    {
        std::vector<float> h = decayingNoise(4800, 4000, 71);
        const std::string path = irFile("rev.wav", {h});
        auto fx = makeFx({{"ir", path}, {"reverse", true}, {"normalize", false}});
        Stereo s(6000);
        s.l[10] = 1.0f;
        run(*fx, s);
        double err = 0.0;
        for (std::size_t k = 0; k < h.size(); ++k) err = std::max(err, double(std::fabs(s.l[10 + k] - h[h.size() - 1 - k])));
        check(err < 1e-6, "reverse on: the impulse response is the IR backwards");
    }
}

void testErrors() {
    std::printf("config errors name the problem and the file\n");
    auto prep = [](const json& cfg) {
        return configError([&] {
            auto fx = createEffect("convolver");
            fx->configure(cfg);
            fx->prepare(context());
        });
    };
    auto has = [](const std::string& msg, std::initializer_list<const char*> parts) {
        for (const char* p : parts)
            if (msg.find(p) == std::string::npos) return false;
        return true;
    };
    std::string m = prep(json::object());
    check(has(m, {"'ir' is required"}), "no 'ir': " + m);
    m = prep({{"ir", 3}});
    check(has(m, {"'ir' must be a WAV path"}), "'ir' a number: " + m);
    m = prep({{"ir", ""}});
    check(has(m, {"'ir' must be a WAV path", "empty"}), "'ir' empty: " + m);
    m = prep({{"ir", json::array({"a.wav", "b.wav", "c.wav"})}});
    check(has(m, {"'ir' must be a WAV path", "list of 2 or 4"}), "'ir' with 3 files: " + m);
    const std::string unit = irFile("unit_e.wav", {{1.0f}});
    m = prep({{"ir", unit}, {"room", 3}});
    check(has(m, {"unknown parameter 'room'"}), "unknown key: " + m);
    m = prep({{"ir", unit}, {"mix", 2}});
    check(has(m, {"'mix'", "outside"}), "mix out of range: " + m);
    m = prep({{"ir", "nowhere/missing.wav"}});
    check(has(m, {"convolver", "nowhere/missing.wav", "not found", "resolved to"}), "missing file: " + m);
    m = prep({{"ir", "samples/no-such-pack-xyz/hall.wav"}});
    check(has(m, {"samples/no-such-pack-xyz/hall.wav", "not installed", "samples fetch no-such-pack-xyz"}), "pack not installed: " + m);
    std::ofstream(gTmp / "garbage.wav", std::ios::binary) << "hello, this is not a wave file at all";
    const std::string garbage = (gTmp / "garbage.wav").generic_string();
    m = prep({{"ir", garbage}});
    check(has(m, {"garbage.wav", "cannot load"}), "not a WAV: " + m);
    std::ofstream(gTmp / "room.flac", std::ios::binary) << "fLaC";
    m = prep({{"ir", (gTmp / "room.flac").generic_string()}});
    check(has(m, {"room.flac", "not a .wav"}), "a .flac: " + m);
    m = prep({{"ir", irFile("three.wav", {{1.0f}, {1.0f}, {1.0f}})}});
    check(has(m, {"three.wav", "3 channels"}), "3 channels: " + m);
    m = prep({{"ir", irFile("silent.wav", {std::vector<float>(100, 0.0f)})}});
    check(has(m, {"silent.wav", "silent"}), "silent IR: " + m);
    m = prep({{"ir", irFile("short.wav", {std::vector<float>(480, 0.5f)})}, {"start", 20}});
    check(has(m, {"short.wav", "'start'"}), "start past the end: " + m);
    m = prep({{"ir", irFile("long16.wav", {decayingNoise(static_cast<std::size_t>(16 * kSr), 1e9, 3)})}, {"stretch", 2}});
    check(has(m, {"long16.wav", "up to 30 s"}), "longer than 30 s after stretch: " + m);
    const std::string m1 = irFile("pair_l.wav", {{1.0f}}), m2 = irFile("pair_r44.wav", {{1.0f}}, 44100), s1 = irFile("pair_s.wav", {{1.0f}, {1.0f}});
    m = prep({{"ir", json::array({m1, m2})}});
    check(has(m, {"pair_r44.wav", "44100 Hz", "pair_l.wav", "same sample rate"}), "files at different rates: " + m);
    m = prep({{"ir", json::array({m1, s1})}});
    check(has(m, {"pair_l.wav", "pair_s.wav", "same channel count"}), "mono + stereo file: " + m);
    m = prep({{"ir", json::array({s1, s1, s1, s1})}});
    check(has(m, {"4 files of 2 channel(s)", "4 mono files (LL, LR, RL, RR)"}), "4 stereo files: " + m);
    m = prep({{"ir", json::array({m1, "samples/no-such-pack-xyz/r.wav"})}});
    check(has(m, {"samples/no-such-pack-xyz/r.wav", "not installed"}), "one of two files missing: " + m);
}

void testRender() {
    std::printf("end to end: a convolver return bus in a song\n");
    const std::string hall = irFile("song_hall.wav", {decayingNoise(96000, 96000, 81), decayingNoise(96000, 96000, 82)});
    json song = json::parse(R"({
      "format": "agentsound.render", "version": 1, "title": "convolver test",
      "tempo": 120, "lengthBeats": 4, "tailSeconds": 2, "seed": 3,
      "sections": [{"name": "a", "startBeat": 0, "endBeat": 4}],
      "tracks": [{"id": "keys", "instrument": {"type": "va", "params": {}}, "sends": {"hall": -6},
                  "notes": [[0, 0.5, 60, 100], [1, 0.5, 64, 100]]}],
      "buses": [{"id": "hall", "fx": [{"type": "convolver", "params": {"mix": 1, "predelay": 20, "lowcut": 200}}]}],
      "master": {"fx": []}
    })");
    song["buses"][0]["fx"][0]["params"]["ir"] = hall;
    RenderOptions opt;
    opt.outDir = (gTmp / "render").string();
    opt.assetDir = "assets";
    opt.analysis = false;
    opt.pngs = false;
    opt.quiet = true;
    std::string err = configError([&] {
        const auto r = renderSong(parseSong(song), opt);
        const WavData w = readWav(r.mixPath);
        double tail = 0.0;  // the 2 s hall rings on after the last note (1.5 s .. 2.5 s)
        for (std::size_t i = 72000; i < std::min<std::size_t>(w.left.size(), 120000); ++i) tail = std::max(tail, double(std::fabs(w.left[i])));
        check(tail > 1e-3, fmt("the rendered hall return rings after the notes (peak %.4f from 1.5 s on)", tail));
    });
    check(err.empty(), "render ok" + (err.empty() ? std::string() : ": " + err));

    // the space assessment: a convolver return is a reverb return; a convolver insert at a partial mix is a reverb
    // insert (not a dry mix), one at mix 1 is a cabinet (no reverb)
    auto dryWarning = [&](const json& s) {
        RenderOptions o = opt;
        o.analysis = true;
        o.outDir = (gTmp / "render_space").string();
        bool dry = false;
        const std::string e = configError([&] {
            const auto r = renderSong(parseSong(s), o);
            std::ifstream in(r.reportPath);
            const json rep = json::parse(in);
            for (const auto& w : rep["warnings"]) dry = dry || w.value("code", "") == "dry_mix";
        });
        return e.empty() ? (dry ? 1 : 0) : -1;
    };
    json ret = song;
    json insert = song;
    insert["buses"] = json::array();
    insert["tracks"][0].erase("sends");
    insert["tracks"][0]["fx"] = json::array({{{"type", "convolver"}, {"params", {{"ir", hall}, {"mix", 0.3}}}}});
    json cab = insert;
    cab["tracks"][0]["fx"][0]["params"]["mix"] = 1.0;
    const int r1 = dryWarning(ret), r2 = dryWarning(insert), r3 = dryWarning(cab);
    check(r1 == 0 && r2 == 0 && r3 == 1,
          fmt("report: no 'dry_mix' with a convolver return (%d) or a convolver reverb insert at mix 0.3 (%d); a mix-1 convolver "
              "(a cabinet) is no reverb (%d)", r1, r2, r3));

    song["buses"][0]["fx"][0]["params"]["ir"] = "samples/not-there/hall.wav";
    err = configError([&] { validateSong(parseSong(song), "assets"); });
    check(err.find("buses[0].fx[0]") != std::string::npos && err.find("samples/not-there/hall.wav") != std::string::npos,
          "validate names the fx path and the file: " + err);
}

void testSpeed() {
    std::printf("speed (target >= 20x realtime per 5 s stereo IR at 48 kHz)\n");
    const std::string st = irFile("speed_st.wav", {decayingNoise(240000, 200000, 91), decayingNoise(240000, 200000, 92)});
    const std::string ts = irFile("speed_ts.wav", {decayingNoise(240000, 200000, 93), decayingNoise(240000, 200000, 94),
                                                   decayingNoise(240000, 200000, 95), decayingNoise(240000, 200000, 96)});
    const std::size_t n = static_cast<std::size_t>(4 * kSr);
    const Stereo x = noise(n, 0.3f, 17);
    auto speed = [&](const std::string& path) {
        double best = 1e9;
        for (int rep = 0; rep < 3; ++rep) {
            auto fx = makeFx({{"ir", path}, {"mix", 1}, {"lowcut", 120}});
            Stereo s = x;
            const auto t0 = std::chrono::steady_clock::now();
            run(*fx, s, {32});
            best = std::min(best, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
        }
        return (static_cast<double>(n) / kSr) / best;
    };
    const double a = speed(st), b = speed(ts);
    check(a >= 20.0, fmt("5 s stereo IR: %.0fx realtime (32-sample host blocks)", a));
    check(b >= 10.0, fmt("5 s true-stereo IR (4 channels): %.0fx realtime", b));
    const std::string r441 = irFile("speed_441.wav", {decayingNoise(220500, 180000, 97), decayingNoise(220500, 180000, 98)}, 44100);
    auto t0 = std::chrono::steady_clock::now();
    auto fx = makeFx({{"ir", r441}});
    const double prep = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    check(prep < 3.0, fmt("prepare of a 5 s stereo 44.1 kHz IR (resampled to 48 kHz): %.2f s", prep));
    json quad = json::array();
    for (int k = 0; k < 4; ++k) quad.push_back(irFile("quad96_" + std::to_string(k) + ".wav", {decayingNoise(768000, 300000, 200 + static_cast<std::uint64_t>(k), 0.01f)}, 96000));
    t0 = std::chrono::steady_clock::now();
    fx = makeFx({{"ir", quad}});
    const double prepQuad = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    check(prepQuad < 5.0, fmt("prepare of an 8 s 96 kHz true-stereo IR in 4 files (224XL style): %.2f s", prepQuad));
}

}  // namespace

int main() {
    std::printf("test_convolver\n");
    gTmp = fs::temp_directory_path() / ("agentsound_test_convolver_" + std::to_string(AS_TEST_PID));  // (parallel runs)
    std::error_code ec;
    fs::remove_all(gTmp, ec);
    fs::create_directories(gTmp);
    testFft();
    testEngine();
    testUnitImpulse();
    testZeroLatency();
    testRouting();
    testDeterminism();
    testPreview();
    testIrPreparation();
    testParams();
    testErrors();
    testRender();
    testSpeed();
    fs::remove_all(gTmp, ec);
    if (gFail) std::printf("FAILED: %d of %d check(s)\n", gFail, gChecks);
    else std::printf("all %d checks passed\n", gChecks);
    return gFail ? 1 : 0;
}
