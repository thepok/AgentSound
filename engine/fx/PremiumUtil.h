#pragma once

// Internal helpers shared by the premium effects (Premium*.cpp): a splicing delay-line pitch shifter,
// a double-precision state-variable filter with per-sample coefficient changes, counter-based noise.
// Not a public API.

#include "fx/TimeFxUtil.h"

#include <cstdint>
#include <limits>

namespace as::premium {

using timefx::RingDelay;

// ---------------------------------------------------------------------------------------------
// GrainShifter: delay-line pitch shifter for one channel (Eventide H910 / H3000 principle).
//
// A read grain moves through a delay line at the pitch ratio: for a ratio r its delay changes by
// (1 - r) samples per sample (shrinks when shifting up, grows when shifting down). After one grain
// period it has moved by `spacing` and the next grain starts at the nominal start delay; the two are
// crossfaded over `fade` samples (raised cosine = sum to one, for correlated material; or equal
// power, for dense/uncorrelated material such as a reverb tail). With `search` > 0 the new grain's
// start is moved by up to +-search samples to where its signal best matches the outgoing grain
// (normalised cross-correlation, a WSOLA-style splice): tonal material then splices without the
// comb-filter dip / phase jump of a blind splice.
//
// Timing runs on an integer grain period derived from the song sample, so a preview render that
// starts mid-song has the grains exactly where a full render has them (alignment offsets are 0 on
// silence, so this holds whenever the input before the preview start was silent).
//
// Grains read a RingDelay owned by the caller (several shifters can share one line). read() must be
// called before the block's input is written; every grain delay is >= lowestDelay() >= n + 2.
// ---------------------------------------------------------------------------------------------

class GrainShifter {
public:
    struct Shape {
        double center{480.0};    // middle of a grain's nominal delay path (samples)
        double spacing{480.0};   // delay distance between consecutive grains (samples)
        double fade{960.0};      // crossfade length (samples); limited to one grain period
        int search{0};           // splice alignment range +- samples (0 = blind splices)
        int corrLen{384};        // alignment window (samples looking back from the splice point)
        bool equalPower{false};  // crossfade law: equal power (uncorrelated) or raised cosine (sum 1)
    };

    // Delay range (samples) the grains of `s` can read for pitch deviations |r - 1| <= maxDev (a
    // fading-out grain keeps moving; the fade never exceeds one grain period = spacing / |r - 1|).
    static double lowestDelay(const Shape& s, double maxDev) noexcept {
        return s.center - 0.5 * s.spacing - s.search - std::min(maxDev * s.fade, s.spacing);
    }
    static double highestDelay(const Shape& s, double maxDev) noexcept {
        return s.center + 0.5 * s.spacing + s.search + std::min(maxDev * s.fade, s.spacing) + 1.0;
    }

    // Places the grains where a render running from song sample 0 has them at `songSample`.
    void setup(const Shape& shape, bool up, double ratio, std::uint64_t songSample) noexcept {
        shape_ = shape;
        shape_.search = std::clamp(shape.search, 0, kMaxSearch);
        up_ = up;
        period_ = periodFor(ratio);
        hasOld_ = false;
        fadePos_ = fadeLen_ = 0;
        if (period_ == 0) {
            young_ = {shape_.center, 0.0, 0.0, 0};
            untilNext_ = kNever;
            return;
        }
        const auto c = static_cast<std::int64_t>(songSample % static_cast<std::uint64_t>(period_));
        const double slope = slopeFor(period_);
        young_ = {startDelay(), slope, 0.0, c};
        fadeLen_ = std::max<std::int64_t>(1, std::min<std::int64_t>(fadeCfg(), period_));
        if (c < fadeLen_) {
            old_ = {startDelay(), slope, 0.0, c + period_};
            hasOld_ = true;
            fadePos_ = c;
        }
        untilNext_ = period_ - c;
    }

    // New pitch ratio (same direction), continuing the grains from where they are.
    void setRatio(double ratio) noexcept {
        const std::int64_t p = periodFor(ratio);
        if (p == period_) return;
        period_ = p;
        const double slope = p ? slopeFor(p) : 0.0;
        reanchor(young_, slope);
        if (hasOld_) reanchor(old_, slope);
        if (p == 0) {
            untilNext_ = kNever;
            return;
        }
        const double end = (up_ ? shape_.center - 0.5 * shape_.spacing : shape_.center + 0.5 * shape_.spacing) + young_.off;
        const double dist = std::max(0.0, up_ ? young_.d0 - end : end - young_.d0);
        std::int64_t n = static_cast<std::int64_t>(std::llround(dist / std::fabs(slope)));
        if (hasOld_) n = std::max(n, fadeLen_ - fadePos_);
        untilNext_ = std::max<std::int64_t>(n, 1);
    }

    // n shifted samples into out[]; extra[k] >= 0 is added to every grain delay (delay glides, LFOs).
    void read(const RingDelay& line, float* out, int n, const double* extra) noexcept {
        for (int k = 0; k < n; ++k) {
            if (untilNext_ <= 0) spawn(line, k, extra[k]);
            --untilNext_;
            const double e = extra[k] - static_cast<double>(k);
            float y = line.tapCubic(delayOf(young_) + e);
            if (hasOld_) {
                const double t = static_cast<double>(fadePos_) / static_cast<double>(fadeLen_);
                float gIn, gOut;
                if (shape_.equalPower) {
                    gIn = timefx::sinCycles(0.25 * t);
                    gOut = timefx::cosCycles(0.25 * t);
                } else {
                    gIn = 0.5f - 0.5f * timefx::cosCycles(0.5 * t);
                    gOut = 1.0f - gIn;
                }
                y = gIn * y + gOut * line.tapCubic(delayOf(old_) + e);
                ++old_.age;
                if (++fadePos_ >= fadeLen_) hasOld_ = false;
            }
            ++young_.age;
            out[k] = y;
        }
    }

private:
    struct Grain {
        double d0{0.0}, slope{0.0}, off{0.0};  // delay = d0 + slope * age; off = alignment offset
        std::int64_t age{0};
    };
    static constexpr std::int64_t kNever = std::numeric_limits<std::int64_t>::max() / 4;

    static double delayOf(const Grain& g) noexcept { return g.d0 + g.slope * static_cast<double>(g.age); }
    static void reanchor(Grain& g, double slope) noexcept {
        g.d0 = delayOf(g);
        g.age = 0;
        g.slope = slope;
    }
    double startDelay() const noexcept {
        return up_ ? shape_.center + 0.5 * shape_.spacing : shape_.center - 0.5 * shape_.spacing;
    }
    std::int64_t fadeCfg() const noexcept { return static_cast<std::int64_t>(std::llround(std::max(1.0, shape_.fade))); }
    // Integer grain period for a ratio (0 = no shift); the effective slope spacing/period differs from
    // |r - 1| by less than half a sample per period.
    std::int64_t periodFor(double ratio) const noexcept {
        const double dev = std::fabs(ratio - 1.0);
        if (!(dev > 1e-9)) return 0;
        const double p = shape_.spacing / dev;
        if (p > 1e12) return 0;
        return std::max<std::int64_t>(1, static_cast<std::int64_t>(std::llround(p)));
    }
    double slopeFor(std::int64_t period) const noexcept {
        const double s = shape_.spacing / static_cast<double>(period);
        return up_ ? -s : s;
    }

    void spawn(const RingDelay& line, int k, double extra) noexcept {
        const double e = extra - static_cast<double>(k);
        double a = 0.0;
        if (shape_.search > 0) a = align(line, delayOf(young_) + e, startDelay() + e);
        old_ = young_;
        hasOld_ = true;
        young_ = {startDelay() + a, slopeFor(period_), a, 0};
        fadeLen_ = std::max<std::int64_t>(1, std::min<std::int64_t>(fadeCfg(), period_));
        fadePos_ = 0;
        untilNext_ = period_;
    }

    // Offset (samples, |a| <= search) of the new grain that best continues the outgoing one:
    // maximum normalised correlation of the corrLen samples before the two read points, slightly
    // favouring small offsets (keeps the delay near nominal on periodic material). 0 on silence.
    double align(const RingDelay& line, double dOld, double dNew) const noexcept {
        const int T = shape_.search, L = std::max(8, shape_.corrLen);
        const float* buf = line.data();
        const std::uint32_t mask = line.mask(), w = line.writeIndex();
        auto tap = [&](long d) { return buf[(w - static_cast<std::uint32_t>(d)) & mask]; };
        const long io = std::lround(dOld), in = std::lround(dNew);
        double eo = 0.0;
        for (int j = 0; j < L; ++j) {
            const double v = tap(io + j);
            eo += v * v;
        }
        if (eo < 1e-14 * L) return 0.0;
        // energy of every candidate window (a sliding sum over a = -T..T)
        double en = 0.0;
        for (int j = 0; j < L; ++j) {
            const double v = tap(in - T + j);
            en += v * v;
        }
        double best = -2.0;
        int bestA = 0;
        double eBuf[2 * kMaxSearch + 1];
        for (int a = -T; a <= T; ++a) {
            eBuf[a + T] = en;
            const double out = tap(in + a), inn = tap(in + a + L);
            en += inn * inn - out * out;
        }
        for (int step = 0; step <= 2 * T; ++step) {  // candidates by distance: 0, -1, +1, -2, +2, ...
            const int a = (step & 1) ? -(step + 1) / 2 : step / 2;
            const double e = eBuf[a + T];
            if (e < 1e-14 * L) continue;
            double dot = 0.0;
            for (int j = 0; j < L; ++j) dot += static_cast<double>(tap(io + j)) * tap(in + a + j);
            const double score = dot / std::sqrt(e * eo) * (1.0 - 0.1 * std::abs(a) / T);
            if (score > best) {
                best = score;
                bestA = a;
            }
        }
        return static_cast<double>(bestA);
    }

public:
    static constexpr int kMaxSearch = 1024;  // longer search ranges are clamped (~10 ms at 96 kHz)

private:
    Shape shape_{};
    bool up_{true};
    Grain young_{}, old_{};
    bool hasOld_{false};
    std::int64_t fadePos_{0}, fadeLen_{1}, untilNext_{kNever}, period_{0};
};

// ---------------------------------------------------------------------------------------------
// Topology-preserving state-variable filter (A. Simper, Cytomic "Linear trapezoidal integrated SVF"),
// double precision, as a bell. The frequency is fixed after setFreq(); the gain may change every
// sample without transients (damping and output mix are recomputed, the filter state is kept).
// ---------------------------------------------------------------------------------------------

class Svf {
public:
    void setFreq(double sampleRate, double hz) noexcept {
        g_ = std::tan(dsp::kPi * std::clamp(hz, 5.0, 0.49 * sampleRate) / sampleRate);
        setK(k_);
    }
    void setK(double k) noexcept {
        k_ = k;
        a1_ = 1.0 / (1.0 + g_ * (g_ + k_));
        a2_ = g_ * a1_;
        a3_ = g_ * a2_;
    }
    // Bell (peaking) filter with gain `db` and quality q at the set frequency (Simper's form: the
    // bandwidth stays symmetric in dB).
    double bell(double x, double db, double q) noexcept {
        if (db != lastDb_ || q != lastQ_) {  // the pow only while the gain moves
            const double A = std::pow(10.0, db / 40.0);
            lastDb_ = db;
            lastQ_ = q;
            setK(1.0 / (q * A));
            m1_ = k_ * (A * A - 1.0);
        }
        tick(x);
        return x + m1_ * v1_;
    }
    void reset() noexcept { ic1_ = ic2_ = v1_ = v2_ = 0.0; }

private:
    void tick(double v0) noexcept {
        const double v3 = v0 - ic2_;
        v1_ = a1_ * ic1_ + a2_ * v3;
        v2_ = ic2_ + a2_ * ic1_ + a3_ * v3;
        ic1_ = 2.0 * v1_ - ic1_;
        ic2_ = 2.0 * v2_ - ic2_;
        if (std::fabs(ic1_) < 1e-30) ic1_ = 0.0;
        if (std::fabs(ic2_) < 1e-30) ic2_ = 0.0;
    }
    double g_{0.1}, k_{1.41421356}, a1_{1.0}, a2_{0.0}, a3_{0.0};
    double ic1_{0.0}, ic2_{0.0}, v1_{0.0}, v2_{0.0};
    double m1_{0.0}, lastDb_{-1e300}, lastQ_{-1.0};
};

// ---------------------------------------------------------------------------------------------
// Counter-based white noise: a pure function of (seed, sample index), so any song position can be
// rendered directly (preview renders match full renders). Uniform in [-1, 1).
// ---------------------------------------------------------------------------------------------

inline float counterNoise(std::uint64_t seed, std::uint64_t index) noexcept {
    std::uint64_t z = seed + index * 0x9E3779B97F4A7C15ull;  // splitmix64
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    z ^= z >> 31;
    return static_cast<float>(static_cast<double>(z >> 40) * (2.0 / 16777216.0) - 1.0);
}

// Factories (one per Premium*.cpp).
std::unique_ptr<Effect> makeMicroShift();
std::unique_ptr<Effect> makeShimmer();
std::unique_ptr<Effect> makeTape();
std::unique_ptr<Effect> makeExciter();
std::unique_ptr<Effect> makeDimension();

}  // namespace as::premium
