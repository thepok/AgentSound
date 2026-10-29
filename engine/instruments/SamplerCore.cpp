#include "instruments/SamplerCore.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <mutex>
#include <tuple>
#include <type_traits>

#if defined(__SSE2__) || defined(_M_X64)
#include <emmintrin.h>
#define AS_SAMPLER_SSE 1
#endif

namespace as::smp {
namespace {

// Kaiser-windowed sinc prototype: cutoff 0.47 of the source rate, beta 7 (~70 dB stop band). The pass
// band is flat to ~0.40 fs and images of content below 0.46 fs are rejected by ~70 dB.
constexpr double kCutoff = 0.47;
constexpr double kBeta = 7.0;
constexpr int kFine = 1024;  // points per source frame of the table the stretched kernels are sampled from

double besselI0(double x) {
    double sum = 1.0, term = 1.0;
    const double q = x * x * 0.25;
    for (int k = 1; k < 64; ++k) {
        term *= q / (static_cast<double>(k) * k);
        sum += term;
        if (term < 1e-17 * sum) break;
    }
    return sum;
}

double prototype(double t) {
    if (std::fabs(t) >= kHalf) return 0.0;
    const double x = 2.0 * kCutoff * t;
    const double sinc = std::fabs(x) < 1e-12 ? 1.0 : std::sin(dsp::kPi * x) / (dsp::kPi * x);
    const double r = t / kHalf;
    const double w = besselI0(kBeta * std::sqrt(std::max(0.0, 1.0 - r * r))) / besselI0(kBeta);
    return 2.0 * kCutoff * sinc * w;
}

// Dot products in a fixed summation order (8 lanes, then a fixed horizontal sum): the SSE and the scalar
// versions give the same result on every run.
#ifdef AS_SAMPLER_SSE
inline float hsum(__m128 a, __m128 b) noexcept {
    const __m128 s = _mm_add_ps(a, b);                                   // lanes j + (j + 4)
    const __m128 t = _mm_add_ps(s, _mm_movehl_ps(s, s));                  // (0+2), (1+3)
    return _mm_cvtss_f32(_mm_add_ss(t, _mm_shuffle_ps(t, t, 1)));
}
#else
inline float hsum8(const float* acc) noexcept {
    return ((acc[0] + acc[4]) + (acc[2] + acc[6])) + ((acc[1] + acc[5]) + (acc[3] + acc[7]));
}
#endif

constexpr std::array<float, 5> kTiltFlat = {1.0f, 0.0f, 0.0f, 0.0f, 0.0f};
constexpr double kTiltK = 2.0;
constexpr double kTiltHighHz = 2500.0, kTiltLowHz = 250.0;

}  // namespace

// ------------------------------------------------------------------------------------------ kernel

Kernel::Kernel() {
    coef_.assign(static_cast<std::size_t>(kPhases + 1) * kTaps, 0.0f);
    delta_.assign(static_cast<std::size_t>(kPhases) * kTaps, 0.0f);
    for (int p = 0; p <= kPhases; ++p) {
        const double phi = static_cast<double>(p) / kPhases;
        double row[kTaps];
        double sum = 0.0;
        for (int m = 0; m < kTaps; ++m) {
            row[m] = prototype(static_cast<double>(m - (kHalf - 1)) - phi);
            sum += row[m];
        }
        for (int m = 0; m < kTaps; ++m) coef_[static_cast<std::size_t>(p) * kTaps + static_cast<std::size_t>(m)] = static_cast<float>(row[m] / sum);
    }
    for (int p = 0; p < kPhases; ++p) {
        for (int m = 0; m < kTaps; ++m) {
            const std::size_t i = static_cast<std::size_t>(p) * kTaps + static_cast<std::size_t>(m);
            delta_[i] = coef_[i + kTaps] - coef_[i];
        }
    }
    // Stretched kernels h(u / st) / st, st on a semitone grid (2^(k/12), k = 1..kWideTables), sampled from a
    // fine table of the prototype (linear interpolation, error < 1e-7) and normalized per phase to unity DC gain.
    const int n = 2 * kHalf * kFine;
    std::vector<double> fine(static_cast<std::size_t>(n) + 2, 0.0);
    for (int i = 0; i <= n; ++i) fine[static_cast<std::size_t>(i)] = prototype(static_cast<double>(i) / kFine - kHalf);
    auto h = [&](double u) {
        const double x = (u + kHalf) * kFine;
        if (!(x > 0.0) || x >= n) return 0.0;
        const auto k = static_cast<std::size_t>(x);
        return fine[k] + (x - static_cast<double>(k)) * (fine[k + 1] - fine[k]);
    };
    wide_.resize(kWideTables);
    std::vector<double> row;
    for (int k = 0; k < kWideTables; ++k) {
        WideKernel& w = wide_[static_cast<std::size_t>(k)];
        w.stretch = std::exp2(static_cast<double>(k + 1) / kWideSteps);
        w.half = static_cast<int>(std::ceil(kHalf * w.stretch - 1e-9));
        w.taps = (2 * w.half + 7) & ~7;
        const auto taps = static_cast<std::size_t>(w.taps);
        w.coef.assign(static_cast<std::size_t>(kWidePhases + 1) * taps, 0.0f);
        w.delta.assign(static_cast<std::size_t>(kWidePhases) * taps, 0.0f);
        row.assign(taps, 0.0);
        for (int p = 0; p <= kWidePhases; ++p) {
            const double phi = static_cast<double>(p) / kWidePhases;
            double sum = 0.0;
            for (std::size_t m = 0; m < taps; ++m) {
                row[m] = h((static_cast<double>(m) - (w.half - 1) - phi) / w.stretch);
                sum += row[m];
            }
            for (std::size_t m = 0; m < taps; ++m) w.coef[static_cast<std::size_t>(p) * taps + m] = static_cast<float>(row[m] / sum);
        }
        for (std::size_t i = 0; i < w.delta.size(); ++i) w.delta[i] = w.coef[i + taps] - w.coef[i];
    }
}

const Kernel& Kernel::get() {
    static const Kernel kernel;
    return kernel;
}

const WideKernel& Kernel::wide(double stretch) const noexcept {
    // the smallest grid stretch >= the requested one (cutoff at most a semitone below the output Nyquist)
    const double k = std::ceil(kWideSteps * std::log2(std::max(stretch, 1.0)) - 1e-6);
    const int index = std::clamp(static_cast<int>(k), 1, kWideTables) - 1;
    return wide_[static_cast<std::size_t>(index)];
}

// ------------------------------------------------------------------------------------------ region

namespace {

// Segment B of a loop (see the header): real data before loopStart, the loop period after it.
template <typename T>
void buildLoop(const std::vector<T>& a, std::vector<T>& b, std::int64_t bFirst, std::int64_t size, std::int64_t loopStart,
               std::int64_t len, std::int64_t period, bool pingpong) {
    b.resize(static_cast<std::size_t>(size));
    for (std::int64_t j = 0; j < size; ++j) {
        const std::int64_t f = bFirst + j;
        if (f < loopStart) {  // the real data before the loop (what the first pass reads), zeros before the sample
            b[static_cast<std::size_t>(j)] = f + kGuardA >= 0 ? a[static_cast<std::size_t>(f + kGuardA)] : T{0};
            continue;
        }
        const std::int64_t m = (f - loopStart) % period;
        const std::int64_t src = (pingpong && m >= len) ? loopStart + (2 * len - 2 - m) : loopStart + m;
        b[static_cast<std::size_t>(j)] = a[static_cast<std::size_t>(src + kGuardA)];
    }
}

}  // namespace

std::shared_ptr<const Segment> repairSegment(const Segment& a, int channels, std::int64_t frames, double rate,
                                             double contrastDb, int* count, const std::vector<std::int64_t>& keep) {
    auto out = std::make_shared<Segment>(a);
    int fixed = 0;
    const int nch = std::clamp(channels, 1, 2);
    const std::int64_t blk = std::max<std::int64_t>(1, std::llround(rate * 0.00067));      // the detector's ~0.67 ms
    const std::int64_t ctxN = std::max<std::int64_t>(3, std::llround(0.03 * rate / static_cast<double>(blk)));
    const std::int64_t skip = std::llround(0.05 * rate);
    const std::int64_t maxHalf = std::max<std::int64_t>(4, std::llround(0.002 * rate));
    const double ratio = std::pow(10.0, contrastDb / 20.0);
    std::vector<double> y(static_cast<std::size_t>(std::max<std::int64_t>(frames, 0)));
    for (int c = 0; c < nch && frames > 2 * skip; ++c) {
        const auto cc = static_cast<std::size_t>(c);
        for (std::int64_t f = 0; f < frames; ++f) {
            const auto i = static_cast<std::size_t>(f + kGuardA);
            y[static_cast<std::size_t>(f)] = a.is16 ? a.s[cc][i] / 32768.0 : static_cast<double>(a.f[cc][i]);
        }
        auto d3 = [&](std::int64_t n) {
            const auto k = static_cast<std::size_t>(n);
            return std::abs(y[k] - 3.0 * y[k - 1] + 3.0 * y[k - 2] - y[k - 3]);
        };
        const std::int64_t nb = frames / blk;
        std::vector<double> pk(static_cast<std::size_t>(nb), 0.0);
        std::vector<std::int64_t> at(static_cast<std::size_t>(nb), 0);
        for (std::int64_t n = 3; n < nb * blk; ++n) {
            const auto j = static_cast<std::size_t>(n / blk);
            const double v = d3(n);
            if (v > pk[j]) {
                pk[j] = v;
                at[j] = n;
            }
        }
        bool changed = false;
        for (std::int64_t j = 0; j < nb; ++j) {
            const std::int64_t n = at[static_cast<std::size_t>(j)];
            const double p = pk[static_cast<std::size_t>(j)];
            if (n < skip || p < 1e-3) continue;
            if (std::any_of(keep.begin(), keep.end(), [&](std::int64_t k) { return std::llabs(n - k) <= maxHalf + 8; })) continue;
            double ctx = 0.0;                       // the neighbourhood without the adjacent blocks
            for (std::int64_t k = std::max<std::int64_t>(0, j - ctxN); k <= std::min(nb - 1, j + ctxN); ++k) {
                if (k < j - 1 || k > j + 1) ctx = std::max(ctx, pk[static_cast<std::size_t>(k)]);
            }
            if (ctx <= 0.0 || p < ratio * ctx) continue;
            for (std::int64_t half = 4; half <= maxHalf; half *= 2) {   // bridge (g0, g1), wider while it spikes
                const std::int64_t g0 = n - half - 1, g1 = n + half / 2 + 1;
                if (g0 < 3 || g1 + 3 >= frames) break;
                const double y0 = y[static_cast<std::size_t>(g0)], y1 = y[static_cast<std::size_t>(g1)];
                const double m0 = (y0 - y[static_cast<std::size_t>(g0 - 2)]) * 0.5;
                const double m1 = (y[static_cast<std::size_t>(g1 + 2)] - y1) * 0.5;
                const double L = static_cast<double>(g1 - g0);
                for (std::int64_t i = g0 + 1; i < g1; ++i) {
                    const double t = static_cast<double>(i - g0) / L, t2 = t * t, t3 = t2 * t;
                    y[static_cast<std::size_t>(i)] = (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * L * m0 +
                                                     (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * L * m1;
                }
                double m = 0.0;
                for (std::int64_t k = std::max<std::int64_t>(3, g0 - 3); k <= std::min(frames - 1, g1 + 4); ++k) m = std::max(m, d3(k));
                if (m < ratio * ctx) break;
            }
            ++fixed;
            changed = true;
        }
        if (!changed) continue;
        for (std::int64_t f = 0; f < frames; ++f) {
            const auto i = static_cast<std::size_t>(f + kGuardA);
            const double v = y[static_cast<std::size_t>(f)];
            if (out->is16) out->s[cc][i] = static_cast<std::int16_t>(std::clamp(std::lround(v * 32768.0), -32768L, 32767L));
            else out->f[cc][i] = static_cast<float>(v);
        }
    }
    if (count) *count = fixed;
    return out;
}

std::shared_ptr<const Segment> smoothSeam(const std::shared_ptr<const Segment>& a, int channels, std::int64_t frames,
                                          double rate, std::int64_t loopStart, std::int64_t loopEnd, double contrastDb,
                                          bool* fixed) {
    if (fixed) *fixed = false;
    const int nch = std::clamp(channels, 1, 2);
    const std::int64_t ls = loopStart, le = loopEnd, len = loopEnd - loopStart;
    const std::int64_t ctx = std::llround(0.03 * rate), guard = std::max<std::int64_t>(8, std::llround(0.0015 * rate));
    const std::int64_t fade = std::min<std::int64_t>({std::llround(0.025 * rate), ls, len / 2});
    if (!a || le > frames || fade < 16 || len < 2 * (ctx + guard) || ls < ctx) return a;
    const double ratio = std::pow(10.0, contrastDb / 20.0);
    auto val = [&](int c, std::int64_t f) {
        const auto i = static_cast<std::size_t>(f + kGuardA);
        const auto cc = static_cast<std::size_t>(c);
        return a->is16 ? a->s[cc][i] / 32768.0 : static_cast<double>(a->f[cc][i]);
    };
    auto d3 = [](double y3, double y2, double y1, double y0) { return std::abs(y0 - 3.0 * y1 + 3.0 * y2 - y3); };
    bool broken = false;
    for (int c = 0; c < nch && !broken; ++c) {
        auto played = [&](std::int64_t k) { return k < 0 ? val(c, le + k) : val(c, ls + k); };   // the seam at k = 0
        double seam = 0.0;
        for (std::int64_t k = 0; k < 3; ++k) seam = std::max(seam, d3(played(k - 3), played(k - 2), played(k - 1), played(k)));
        double near = 0.0;                         // the loop's own movement within 30 ms of the seam
        for (std::int64_t f = le - ctx; f < le - guard; ++f) near = std::max(near, d3(val(c, f - 3), val(c, f - 2), val(c, f - 1), val(c, f)));
        for (std::int64_t f = ls + guard; f < ls + ctx; ++f) near = std::max(near, d3(val(c, f - 3), val(c, f - 2), val(c, f - 1), val(c, f)));
        broken = seam >= 1e-3 && seam >= ratio * std::max(near, 1e-9);
    }
    if (!broken) return a;
    auto out = std::make_shared<Segment>(*a);
    const double kPiD = 3.14159265358979323846;
    for (int c = 0; c < nch; ++c) {
        const auto cc = static_cast<std::size_t>(c);
        for (std::int64_t i = 0; i < fade; ++i) {   // [le - fade, le) -> [ls - fade, ls): the end runs into the start
            const double w = 0.5 - 0.5 * std::cos(kPiD * static_cast<double>(i + 1) / static_cast<double>(fade));
            const double v = (1.0 - w) * val(c, le - fade + i) + w * val(c, ls - fade + i);
            const auto k = static_cast<std::size_t>(le - fade + i + kGuardA);
            if (out->is16) out->s[cc][k] = static_cast<std::int16_t>(std::clamp(std::lround(v * 32768.0), -32768L, 32767L));
            else out->f[cc][k] = static_cast<float>(v);
        }
    }
    if (fixed) *fixed = true;
    return out;
}

Region makeRegion(const std::vector<float>* channels, int channelCount, double rate, LoopMode loop,
                  std::int64_t loopStart, std::int64_t loopEnd, bool reverse) {
    const int count = std::clamp(channelCount, 1, 2);
    const auto frames = static_cast<std::int64_t>(channels[0].size());
    auto seg = std::make_shared<Segment>();
    for (int c = 0; c < count; ++c) {
        const auto& src = channels[c];
        auto& dst = seg->f[static_cast<std::size_t>(c)];
        dst.assign(static_cast<std::size_t>(frames + 2 * kGuardA), 0.0f);
        for (std::int64_t f = 0; f < frames; ++f) {
            dst[static_cast<std::size_t>(f + kGuardA)] = src[static_cast<std::size_t>(reverse ? frames - 1 - f : f)];
        }
    }
    if (loop != LoopMode::None && reverse) {
        const std::int64_t s = frames - loopEnd, e = frames - loopStart;
        loopStart = s;
        loopEnd = e;
    }
    return makeRegion(std::move(seg), count, rate, frames, loop, loopStart, loopEnd);
}

Region makeRegion(std::shared_ptr<const Segment> a, int channelCount, double rate, std::int64_t frames, LoopMode loop,
                  std::int64_t loopStart, std::int64_t loopEnd) {
    Region r;
    r.channels = std::clamp(channelCount, 1, 2);
    r.rate = rate;
    r.frames = frames;
    r.a = std::move(a);
    r.b.is16 = r.a->is16;
    if (loop == LoopMode::None) return r;
    const std::int64_t len = loopEnd - loopStart;
    r.loop = true;
    r.loopStart = loopStart;
    r.loopEnd = loopEnd;
    r.period = loop == LoopMode::PingPong ? 2 * len - 2 : len;
    r.bFirst = loopStart - kGuardB;
    const std::int64_t size = r.period + 2 * kGuardB;
    for (std::size_t c = 0; c < static_cast<std::size_t>(r.channels); ++c) {
        if (r.a->is16) buildLoop(r.a->s[c], r.b.s[c], r.bFirst, size, loopStart, len, r.period, loop == LoopMode::PingPong);
        else buildLoop(r.a->f[c], r.b.f[c], r.bFirst, size, loopStart, len, r.period, loop == LoopMode::PingPong);
    }
    return r;
}

// ------------------------------------------------------------------------------------------ reader

void Reader::start(const Region& r, double startFrame, double endFrame, bool loop) noexcept {
    region = &r;
    pos = std::max(0.0, startFrame);
    end = std::clamp(endFrame, 0.0, static_cast<double>(r.frames));
    looping = loop && r.loop;
    exitAtWrap = false;
    inB = false;
    done = pos >= end && !looping;
}

namespace {

#ifdef AS_SAMPLER_SSE
// 8 consecutive samples as two float vectors (16-bit data: the integers, scaled once at the end).
inline void load8(const float* p, __m128& lo, __m128& hi) noexcept {
    lo = _mm_loadu_ps(p);
    hi = _mm_loadu_ps(p + 4);
}
inline void load8(const std::int16_t* p, __m128& lo, __m128& hi) noexcept {
    const __m128i v = _mm_loadu_si128(reinterpret_cast<const __m128i*>(p));
    lo = _mm_cvtepi32_ps(_mm_srai_epi32(_mm_unpacklo_epi16(v, v), 16));
    hi = _mm_cvtepi32_ps(_mm_srai_epi32(_mm_unpackhi_epi16(v, v), 16));
}
#endif

// Output scale of a sample type: 16-bit data is summed as integers and scaled by 2^-15 at the end (exact:
// the products and sums are the float ones scaled by a power of two).
template <typename T>
constexpr float kScale = 1.0f;
template <>
constexpr float kScale<std::int16_t> = 1.0f / 32768.0f;

// Polyphase FIR: `taps` coefficients (a multiple of 8) interpolated between the two nearest of `phases` rows.
// Tap t of output frame j reads frame i - (half - 1) + t, i = floor(pos). `x0` / `x1`: element of frame 0 in
// each channel's segment. Fixed summation order (8 lanes, fixed horizontal sum): the SSE and the scalar
// versions give the same result on every run. Returns the new position.
template <bool kStereo, typename T>
double runPoly(const float* coef, const float* delta, int taps, int half, int phases, const T* x0, const T* x1,
               float* out0, float* out1, int m, double pos, double inc) noexcept {
    const auto rowSize = static_cast<std::size_t>(taps);
    for (int j = 0; j < m; ++j) {
        const auto i = static_cast<std::int64_t>(pos);  // pos >= 0: truncation is floor
        const float fp = static_cast<float>(pos - static_cast<double>(i)) * static_cast<float>(phases);
        int ph = static_cast<int>(fp);
        if (ph >= phases) ph = phases - 1;
        const float pf = fp - static_cast<float>(ph);
        const float* c = coef + static_cast<std::size_t>(ph) * rowSize;
        const float* d = delta + static_cast<std::size_t>(ph) * rowSize;
        const std::int64_t first = i - (half - 1);
        const T* a = x0 + first;
#ifdef AS_SAMPLER_SSE
        const __m128 vpf = _mm_set1_ps(pf);
        __m128 a0 = _mm_setzero_ps(), a1 = _mm_setzero_ps(), b0 = _mm_setzero_ps(), b1 = _mm_setzero_ps();
        for (int t = 0; t < taps; t += 8) {
            const __m128 w0 = _mm_add_ps(_mm_loadu_ps(c + t), _mm_mul_ps(vpf, _mm_loadu_ps(d + t)));
            const __m128 w1 = _mm_add_ps(_mm_loadu_ps(c + t + 4), _mm_mul_ps(vpf, _mm_loadu_ps(d + t + 4)));
            __m128 lo, hi;
            load8(a + t, lo, hi);
            a0 = _mm_add_ps(a0, _mm_mul_ps(lo, w0));
            a1 = _mm_add_ps(a1, _mm_mul_ps(hi, w1));
            if constexpr (kStereo) {
                load8(x1 + first + t, lo, hi);
                b0 = _mm_add_ps(b0, _mm_mul_ps(lo, w0));
                b1 = _mm_add_ps(b1, _mm_mul_ps(hi, w1));
            }
        }
        out0[j] = hsum(a0, a1) * kScale<T>;
        if constexpr (kStereo) out1[j] = hsum(b0, b1) * kScale<T>;
#else
        float acc0[8] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f}, acc1[8] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
        for (int t = 0; t < taps; t += 8) {
            for (int l = 0; l < 8; ++l) {
                const float w = c[t + l] + pf * d[t + l];
                acc0[l] += static_cast<float>(a[t + l]) * w;
                if constexpr (kStereo) acc1[l] += static_cast<float>(x1[first + t + l]) * w;
            }
        }
        out0[j] = hsum8(acc0) * kScale<T>;
        if constexpr (kStereo) out1[j] = hsum8(acc1) * kScale<T>;
#endif
        pos += inc;
    }
    return pos;
}

}  // namespace

double Reader::leaveLoop(double ls, double le, double per, int half, double inc) noexcept {
    // Loop until release, released while reading B: the rest of a pass, then the tail of the sample.
    // Segment A holds exactly that from the same point of the pass (pA) when the window does not reach
    // back before loopStart (pA >= first) and the frames already rendered have not looked past the loop
    // end of this pass yet (pA < last). Switch then; else render up to the first such position (later in
    // this pass, or in the next one). Loops shorter than the kernel have no such position: leave at once.
    const double q = pos - ls;
    const double passes = q < 0.0 ? 0.0 : std::floor(q / per);
    const double pA = pos - passes * per;
    const double first = ls + static_cast<double>(half - 1);
    const double last = le - static_cast<double>(half) + inc;
    const bool tooShort = last - first < inc;
    if ((pA >= first && pA < last) || (tooShort && pA < le)) {
        pos = pA;
        inB = false;
        looping = false;
        return 0.0;
    }
    if (tooShort) return pos + (ls + per - pA);  // backward half of a ping-pong pass: wait for the next pass
    return pos + (pA < first ? first - pA : ls + per - pA + static_cast<double>(half - 1));
}

void Reader::read(float* out0, float* out1, int n, double inc) noexcept { run<true>(out0, out1, n, inc); }

void Reader::skip(int n, double inc) noexcept { run<false>(nullptr, nullptr, n, inc); }

template <bool kOut>
void Reader::run(float* out0, float* out1, int n, double inc) noexcept {
    const Region& r = *region;
    const Kernel& K = Kernel::get();
    const bool stereo = r.channels == 2;
    // played faster than recorded: a stretched kernel whose cutoff sits at (or just below) the output Nyquist
    const WideKernel* wk = inc > 1.0 ? &K.wide(inc) : nullptr;
    const int half = wk ? wk->half : kHalf;
    const double ls = static_cast<double>(r.loopStart);
    const double le = static_cast<double>(r.loopEnd);
    const double per = static_cast<double>(r.period);
    // B wraps by one period once the position passes `wrapAt`: afterwards every window starts at or after
    // loopStart (periodic data), before the first wrap windows may reach into the real pre-loop data.
    const double wrapAt = ls + static_cast<double>(kMaxHalfWidth) + per;
    int k = 0;
    while (k < n) {
        double exitAt = wrapAt;  // (B) position where a released loop-until-release voice can leave the loop
        if (looping) {
            if (!inB) {
                // released before the loop was reached: play straight through (A is exact); else switch to B
                // before the window reaches the loop end
                if (exitAtWrap) looping = false;
                else if (pos + half >= le) inB = true;
            }
            if (inB) {
                while (pos >= wrapAt) pos -= per;
                if (exitAtWrap) exitAt = std::min(wrapAt, leaveLoop(ls, le, per, half, inc));
            }
        }
        if (done || (!looping && pos >= end)) {
            done = true;
            if constexpr (kOut) {
                std::fill(out0 + k, out0 + n, 0.0f);
                if (stereo) std::fill(out1 + k, out1 + n, 0.0f);
            }
            return;
        }
        // Frames until the next boundary (switch to B, wrap, leaving the loop, end): no per-frame checks.
        const double limit = !looping ? end : inB ? exitAt : le - half;
        int m = n - k;
        const double room = (limit - pos) / inc;
        if (room < m) m = std::max(1, static_cast<int>(std::ceil(room)));
        if constexpr (!kOut) {  // the same position arithmetic as runPoly, no samples
            for (int j = 0; j < m; ++j) pos += inc;
            k += m;
            continue;
        }
        const Segment& seg = inB ? r.b : *r.a;
        const std::int64_t base = inB ? -r.bFirst : kGuardA;  // element index = frame + base
        const float* coef = wk ? wk->coef.data() : K.row(0);
        const float* delta = wk ? wk->delta.data() : K.delta(0);
        const int taps = wk ? wk->taps : kTaps;
        const int phases = wk ? kWidePhases : kPhases;
        if (seg.is16) {
            const std::int16_t* x0 = seg.s[0].data() + base;
            if (stereo) pos = runPoly<true>(coef, delta, taps, half, phases, x0, seg.s[1].data() + base, out0 + k, out1 + k, m, pos, inc);
            else pos = runPoly<false>(coef, delta, taps, half, phases, x0, x0, out0 + k, nullptr, m, pos, inc);
        } else {
            const float* x0 = seg.f[0].data() + base;
            if (stereo) pos = runPoly<true>(coef, delta, taps, half, phases, x0, seg.f[1].data() + base, out0 + k, out1 + k, m, pos, inc);
            else pos = runPoly<false>(coef, delta, taps, half, phases, x0, x0, out0 + k, nullptr, m, pos, inc);
        }
        k += m;
    }
}

// ------------------------------------------------------------------------------------------- levels

double loopedFrame(const Region& r, double pos) noexcept {
    const double ls = static_cast<double>(r.loopStart);
    if (!r.loop || pos < ls || r.period <= 0) return pos;
    const double per = static_cast<double>(r.period);
    const double len = static_cast<double>(r.loopEnd - r.loopStart);
    double m = std::fmod(pos - ls, per);
    if (m >= len) m = per - m;   // ping-pong (period 2 L - 2): the backward half of the period
    return ls + std::min(m, len - 1.0);
}

float LevelTrack::at(double frame) const noexcept {
    if (rms.empty()) return 0.0f;
    const double x = std::max(0.0, frame / hop);
    const auto i = static_cast<std::size_t>(x);
    if (i + 1 >= rms.size()) return rms.back();
    const float t = static_cast<float>(x - static_cast<double>(i));
    return rms[i] + t * (rms[i + 1] - rms[i]);
}

float LevelTrack::mean(double a, double b) const noexcept {
    if (rms.empty()) return 0.0f;
    const auto last = static_cast<double>(rms.size() - 1);
    const auto i0 = static_cast<std::size_t>(std::clamp(std::floor(a / hop), 0.0, last));
    const auto i1 = static_cast<std::size_t>(std::clamp(std::ceil(b / hop), static_cast<double>(i0), last));
    double s = 0.0;
    for (std::size_t i = i0; i <= i1; ++i) s += static_cast<double>(rms[i]) * rms[i];
    return static_cast<float>(std::sqrt(s / static_cast<double>(i1 - i0 + 1)));
}

namespace {

template <typename T>
void squares(const Segment& a, int channels, std::int64_t frames, std::vector<double>& sq) {
    const double scale = std::is_same_v<T, std::int16_t> ? 1.0 / 32768.0 : 1.0;
    sq.assign(static_cast<std::size_t>(frames), 0.0);
    for (int c = 0; c < channels; ++c) {
        const T* x = nullptr;
        if constexpr (std::is_same_v<T, std::int16_t>) x = a.s[static_cast<std::size_t>(c)].data() + kGuardA;
        else x = a.f[static_cast<std::size_t>(c)].data() + kGuardA;
        for (std::int64_t f = 0; f < frames; ++f) {
            const double v = static_cast<double>(x[f]) * scale;
            sq[static_cast<std::size_t>(f)] += v * v / channels;
        }
    }
}

LevelTrack computeLevels(const Region& r) {
    LevelTrack t;
    t.hop = std::max(1.0, std::round(r.rate * 0.005));
    const std::int64_t frames = r.frames;
    std::vector<double> sq;
    if (r.a->is16) squares<std::int16_t>(*r.a, r.channels, frames, sq);
    else squares<float>(*r.a, r.channels, frames, sq);
    const auto hop = static_cast<std::int64_t>(t.hop);
    const std::int64_t count = std::max<std::int64_t>(1, (frames + hop - 1) / hop);
    t.rms.assign(static_cast<std::size_t>(count), 0.0f);
    for (std::int64_t i = 0; i < count; ++i) {   // 10 ms window centred on frame i * hop
        const std::int64_t a = std::max<std::int64_t>(0, i * hop - hop), b = std::min(frames, i * hop + hop);
        double s = 0.0;
        for (std::int64_t f = a; f < b; ++f) s += sq[static_cast<std::size_t>(f)];
        t.rms[static_cast<std::size_t>(i)] = static_cast<float>(std::sqrt(s / static_cast<double>(std::max<std::int64_t>(1, b - a))));
    }
    // attack end: the peak of the first second, the sustain level after it (median of the next 0.5 s)
    const auto n = static_cast<std::int64_t>(t.rms.size());
    const std::int64_t first = std::min<std::int64_t>(n, static_cast<std::int64_t>(std::ceil(r.rate / t.hop)));
    std::int64_t peak = 0;
    for (std::int64_t i = 1; i < first; ++i) if (t.rms[static_cast<std::size_t>(i)] > t.rms[static_cast<std::size_t>(peak)]) peak = i;
    const float top = t.rms[static_cast<std::size_t>(peak)];
    if (!(top > 1e-6f)) return t;
    const std::int64_t span = std::max<std::int64_t>(1, std::min(n - peak, static_cast<std::int64_t>(std::ceil(0.5 * r.rate / t.hop))));
    std::vector<float> after(t.rms.begin() + peak, t.rms.begin() + peak + span);
    std::nth_element(after.begin(), after.begin() + static_cast<std::ptrdiff_t>(after.size() / 2), after.end());
    const float sustain = std::max(after[after.size() / 2], 1e-6f);
    std::int64_t onset = 0;
    while (onset < peak && t.rms[static_cast<std::size_t>(onset)] < 0.1f * top) ++onset;
    // settled: from here on (within the first 0.45 s) the level averaged over the last 120 ms stays within +-2 dB of
    // the sustain level and the level itself within +-3.5 dB (a vibrato's amplitude wobble passes, the dip between a
    // noisy transient and the rising tone does not) - past a rising attack, a transient and an overshoot alike
    const std::int64_t window = std::min<std::int64_t>(n, onset + static_cast<std::int64_t>(std::ceil(0.45 * r.rate / t.hop)));
    const auto span120 = static_cast<std::int64_t>(std::max(1.0, std::round(0.12 * r.rate / t.hop)));
    std::int64_t end = onset;
    double acc = 0.0;
    for (std::int64_t i = onset; i < window; ++i) {
        const double v2 = static_cast<double>(t.rms[static_cast<std::size_t>(i)]) * t.rms[static_cast<std::size_t>(i)];
        acc += v2;
        if (i - span120 >= onset) {
            const double old = t.rms[static_cast<std::size_t>(i - span120)];
            acc -= old * old;
        }
        const auto count = static_cast<double>(std::min(span120, i - onset + 1));
        const auto v = static_cast<float>(std::sqrt(std::max(0.0, acc) / count));
        const float now = t.rms[static_cast<std::size_t>(i)];
        if (v < 0.79f * sustain || v > 1.26f * sustain || now < 0.67f * sustain || now > 1.5f * sustain) end = i + 1;
    }
    const double lo = static_cast<double>(onset) * t.hop + 0.01 * r.rate, hi = std::min(0.35 * r.rate, 0.5 * static_cast<double>(frames));
    t.attackEnd = std::max(0.0, std::min(std::max(static_cast<double>(end) * t.hop, lo), hi));
    return t;
}

}  // namespace

namespace {

// mono mix of frames [from, from + n) of a region's sample data (zeros past its end)
std::vector<double> monoFrames(const Region& r, std::int64_t from, std::int64_t n) {
    std::vector<double> out(static_cast<std::size_t>(std::max<std::int64_t>(0, n)), 0.0);
    const Segment& a = *r.a;
    for (int c = 0; c < r.channels; ++c) {
        for (std::int64_t i = 0; i < n; ++i) {
            const std::int64_t f = from + i;
            if (f < 0 || f >= r.frames) continue;
            const auto at = static_cast<std::size_t>(f + kGuardA);
            const double v = a.is16 ? a.s[static_cast<std::size_t>(c)][at] / 32768.0 : a.f[static_cast<std::size_t>(c)][at];
            out[static_cast<std::size_t>(i)] += v / r.channels;
        }
    }
    return out;
}

}  // namespace

Lead leadOf(const Region& a, double offA, const Region& b, double offB, double window, double maxLag) {
    if (!a.a || !b.a || a.rate != b.rate) return {};
    const auto n = static_cast<std::int64_t>(std::lround(window * a.rate));
    const auto L = static_cast<std::int64_t>(std::lround(maxLag * a.rate));
    const auto x = monoFrames(a, static_cast<std::int64_t>(offA) - L, n + 2 * L);   // a with L frames either side
    const auto y = monoFrames(b, static_cast<std::int64_t>(offB), n);
    double yy = 0.0;
    for (const double v : y) yy += v * v;
    if (!(yy > 1e-12)) return {};
    double best = -2.0;
    std::int64_t bestLag = 0;
    for (std::int64_t lag = -L; lag <= L; ++lag) {   // b[i] against a[i + lag]
        double xy = 0.0, xx = 0.0;
        for (std::int64_t i = 0; i < n; ++i) {
            const double u = x[static_cast<std::size_t>(i + lag + L)];
            xy += u * y[static_cast<std::size_t>(i)];
            xx += u * u;
        }
        const double c = xx > 1e-12 ? xy / std::sqrt(xx * yy) : -2.0;
        if (c > best) {
            best = c;
            bestLag = lag;
        }
    }
    return {best >= 0.5 ? static_cast<double>(bestLag) / a.rate : 0.0, std::max(0.0, best)};
}

Colour attackColour(const Region& r, double off, double window) {
    if (!r.a) return {};
    const auto n = static_cast<std::int64_t>(std::lround(window * r.rate));
    const auto x = monoFrames(r, static_cast<std::int64_t>(off), n);
    double e = 0.0, d = 0.0;
    for (std::size_t i = 0; i < x.size(); ++i) {
        e += x[i] * x[i];
        if (i > 0) d += (x[i] - x[i - 1]) * (x[i] - x[i - 1]);
    }
    if (!(e > 1e-12)) return {};
    return {10.0 * std::log10(e / static_cast<double>(std::max<std::int64_t>(1, n))), 10.0 * std::log10(std::max(d, 1e-30) / e)};
}

std::shared_ptr<const LevelTrack> levelTrack(const Region& r) {
    struct Entry {
        std::shared_ptr<const Segment> seg;   // keeps the key's data alive
        std::shared_ptr<const LevelTrack> track;
    };
    static std::mutex mu;
    static std::map<std::tuple<const Segment*, int, std::int64_t>, Entry> cache;
    const auto key = std::make_tuple(r.a.get(), r.channels, r.frames);
    {
        std::lock_guard<std::mutex> lock(mu);
        const auto it = cache.find(key);
        if (it != cache.end()) return it->second.track;
    }
    auto t = std::make_shared<const LevelTrack>(computeLevels(r));
    std::lock_guard<std::mutex> lock(mu);
    return cache.emplace(key, Entry{r.a, std::move(t)}).first->second.track;
}

// ----------------------------------------------------------------------------------------- filters

void LowpassCoefs::set(double sampleRate, double hz, double q) noexcept {
    const double top = std::min(20000.0, 0.45 * sampleRate);
    const double f = std::clamp(hz, 10.0, top);
    const double g = std::tan(dsp::kPi * f / sampleRate);
    const double k = 1.0 / std::max(q, 0.05);
    const double d = 1.0 / (1.0 + g * (g + k));
    a1 = static_cast<float>(d);
    a2 = static_cast<float>(g * d);
    a3 = static_cast<float>(g * g * d);
    // Fully open above ~19 kHz (SF2 13500 cents = 19.9 kHz means "no filter"): blend to the dry signal
    // between 14 and 19 kHz so a sweep through the top stays continuous.
    open = static_cast<float>(std::clamp((hz - 14000.0) / 5000.0, 0.0, 1.0));
}

void Tilt::Svf::tune(double sampleRate, double hz, double k) noexcept {
    const double g = std::tan(dsp::kPi * hz / sampleRate);
    a1 = static_cast<float>(1.0 / (1.0 + g * (g + k)));
    a2 = static_cast<float>(g) * a1;
    a3 = static_cast<float>(g) * a2;
    ic1 = ic2 = 0.0f;
}

void Tilt::Svf::tick(float v0, float& band, float& low) noexcept {
    const float v3 = v0 - ic2;
    band = a1 * ic1 + a2 * v3;
    low = ic2 + a2 * ic1 + a3 * v3;
    ic1 = 2.0f * band - ic1;
    ic2 = 2.0f * low - ic2;
}

void Tilt::prepare(double sampleRate, float brightness) noexcept {
    for (int c = 0; c < 2; ++c) {
        high_[static_cast<std::size_t>(c)].tune(sampleRate, kTiltHighHz, kTiltK);
        low_[static_cast<std::size_t>(c)].tune(sampleRate, kTiltLowHz, kTiltK);
    }
    mix(brightness, m_);
}

void Tilt::mix(float bright, std::array<float, 5>& m) noexcept {
    const double hsDb = bright >= 0.0f ? 6.0 * bright : 10.0 * bright;
    const double lsDb = -2.0 * bright;
    const double ah = std::pow(10.0, hsDb / 40.0), al = std::pow(10.0, lsDb / 40.0);
    m[0] = static_cast<float>(ah * ah);
    m[1] = static_cast<float>(kTiltK * (1.0 - ah) * ah);
    m[2] = static_cast<float>(1.0 - ah * ah);
    m[3] = static_cast<float>(kTiltK * (al - 1.0));
    m[4] = static_cast<float>(al * al - 1.0);
}

void Tilt::process(float* l, float* r, int n, float brightness) noexcept {
    if (n <= 0) return;
    std::array<float, 5> target{};
    mix(brightness, target);
    const bool flat = m_ == kTiltFlat && target == kTiltFlat;
    const float inv = 1.0f / static_cast<float>(n);
    for (int c = 0; c < 2; ++c) {
        float* x = c ? r : l;
        Svf& hi = high_[static_cast<std::size_t>(c)];
        Svf& lo = low_[static_cast<std::size_t>(c)];
        std::array<float, 5> m = m_, dm{};
        for (std::size_t k = 0; k < m.size(); ++k) dm[k] = (target[k] - m[k]) * inv;
        for (int i = 0; i < n; ++i) {
            float bh, lh, bl, ll;
            hi.tick(x[i], bh, lh);
            if (flat) {  // keep the filters warm, output untouched
                lo.tick(x[i], bl, ll);
                continue;
            }
            for (std::size_t k = 0; k < m.size(); ++k) m[k] += dm[k];
            const float y = m[0] * x[i] + m[1] * bh + m[2] * lh;
            lo.tick(y, bl, ll);
            x[i] = y + m[3] * bl + m[4] * ll;
        }
        hi.ic1 = dsp::flush(hi.ic1);
        hi.ic2 = dsp::flush(hi.ic2);
        lo.ic1 = dsp::flush(lo.ic1);
        lo.ic2 = dsp::flush(lo.ic2);
    }
    m_ = target;
}

bool Tilt::settled() const noexcept {
    float s = 0.0f;
    for (int c = 0; c < 2; ++c) {
        s += std::fabs(high_[static_cast<std::size_t>(c)].ic1) + std::fabs(high_[static_cast<std::size_t>(c)].ic2) +
             std::fabs(low_[static_cast<std::size_t>(c)].ic1) + std::fabs(low_[static_cast<std::size_t>(c)].ic2);
    }
    return s < 1e-6f;
}

}  // namespace as::smp
