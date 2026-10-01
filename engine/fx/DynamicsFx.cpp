#include "fx/DynamicsFx.h"

#include "core/TempoMap.h"
#include "dsp/Dsp.h"
#include "fx/HalfBand.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace as {
namespace dynfx {
namespace {

using dsp::kPi;

// ---------------------------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------------------------

inline double flushD(double x) noexcept { return std::fabs(x) < 1e-30 ? 0.0 : x; }
inline float dbToLin(float db) noexcept { return std::exp2(db * 0.166096404744f); }  // 10^(db/20)
inline float linToDb(float g) noexcept { return 6.02059991328f * std::log2(std::max(g, 1e-9f)); }

// Automation glide: two cascaded one-poles (time constant `seconds` each, at `rate` updates per
// second). Unlike a one-pole it has no kink where a change starts, so fast glides stay free of
// high-frequency clicks; 10-90 % step response = 3.36 x seconds. Lands exactly on its target once
// within eps, so settled/neutral states are detectable and bit-exact.
class Glide {
public:
    void prepare(double rate, double seconds, float value, float eps) noexcept {
        coeff_ = seconds <= 0.0 ? 0.0f : static_cast<float>(std::exp(-1.0 / (seconds * rate)));
        eps_ = eps;
        snap(value);
    }
    void setTarget(float t) noexcept {
        target_ = t;
        moving_ = stage_ != target_ || value_ != target_;
    }
    void snap(float v) noexcept {
        stage_ = value_ = target_ = v;
        moving_ = false;
    }
    void set(float v, bool snapNow) noexcept { snapNow ? snap(v) : setTarget(v); }
    float next() noexcept {
        if (moving_) {
            stage_ = target_ + (stage_ - target_) * coeff_;
            value_ = stage_ + (value_ - stage_) * coeff_;
            if (std::fabs(stage_ - target_) <= eps_ && std::fabs(value_ - target_) <= eps_) {
                stage_ = value_ = target_;
                moving_ = false;
            }
        }
        return value_;
    }
    float value() const noexcept { return value_; }
    bool moving() const noexcept { return moving_; }

private:
    float coeff_{0.0f}, eps_{1e-6f}, stage_{0.0f}, value_{0.0f}, target_{0.0f};
    bool moving_{false};
};

// Automation time constants (per stage of Glide): gains, mixes and makeup ~5 ms 10-90 %, filter,
// drive and threshold settings ~7 ms. Short enough for gates and step modulation, long enough to be
// click-free on bass and pads.
constexpr double kGainTau = 0.0015;
constexpr double kShapeTau = 0.002;

// Pass filters at their "off" extreme fade out over the last 10% of frequency (log2(1.1) octaves),
// so automating a cutoff to the extreme and back is continuous and the extreme is bit-transparent.
// Computed in float exactly like the glided log2(freq) values, so the extreme itself gives w == 0.
constexpr double kBlend = 0.137503523749935;  // log2(1.1)
inline double offLog2(float hz) noexcept { return static_cast<double>(std::log2(hz)); }

inline float onePoleCoeff(double fs, double seconds) {
    return seconds <= 0.0 ? 0.0f : static_cast<float>(std::exp(-1.0 / (seconds * fs)));
}

// Chronological buffer for block FIR filtering: `hist` past samples followed by the current
// block, so data() + j is the window of the last hist+1 inputs ending at block sample j.
class BlockBuf {
public:
    void init(int hist, int maxBlock) {
        hist_ = hist;
        buf_.assign(static_cast<std::size_t>(hist + maxBlock), 0.0f);
    }
    float* block() noexcept { return buf_.data() + hist_; }
    const float* data() const noexcept { return buf_.data(); }
    void advance(int n) noexcept {  // after n new samples: keep the newest `hist` as history
        std::memmove(buf_.data(), buf_.data() + n, static_cast<std::size_t>(hist_) * sizeof(float));
    }

private:
    std::vector<float> buf_;
    int hist_{0};
};

// Three dot products over the same n-float window (n a multiple of 8), for the limiter's 4x
// interpolator. Packed SIMD via GCC/Clang vector extensions, scalar lanes otherwise.
#if defined(__GNUC__)
typedef float V4 __attribute__((vector_size(16)));
inline V4 load4(const float* p) noexcept {
    V4 v;
    std::memcpy(&v, p, sizeof v);
    return v;
}
inline void dot3(const float* c0, const float* c1, const float* c2, const float* x, int n, float* out) noexcept {
    V4 a0 = {0, 0, 0, 0}, a1 = a0, a2 = a0, b0 = a0, b1 = a0, b2 = a0;
    for (int i = 0; i < n; i += 8) {
        const V4 x0 = load4(x + i), x1 = load4(x + i + 4);
        a0 += load4(c0 + i) * x0;
        b0 += load4(c0 + i + 4) * x1;
        a1 += load4(c1 + i) * x0;
        b1 += load4(c1 + i + 4) * x1;
        a2 += load4(c2 + i) * x0;
        b2 += load4(c2 + i + 4) * x1;
    }
    const V4 s0 = a0 + b0, s1 = a1 + b1, s2 = a2 + b2;
    out[0] = (s0[0] + s0[2]) + (s0[1] + s0[3]);
    out[1] = (s1[0] + s1[2]) + (s1[1] + s1[3]);
    out[2] = (s2[0] + s2[2]) + (s2[1] + s2[3]);
}
#else
inline float dot(const float* a, const float* b, int n) noexcept {
    float acc[8] = {};
    for (int i = 0; i < n; i += 8)
        for (int k = 0; k < 8; ++k) acc[k] += a[i + k] * b[i + k];
    return ((acc[0] + acc[4]) + (acc[1] + acc[5])) + ((acc[2] + acc[6]) + (acc[3] + acc[7]));
}
inline void dot3(const float* c0, const float* c1, const float* c2, const float* x, int n, float* out) noexcept {
    out[0] = dot(c0, x, n);
    out[1] = dot(c1, x, n);
    out[2] = dot(c2, x, n);
}
#endif

// Fixed integer delay (0 = passthrough).
class DelayRing {
public:
    void init(int delay) {
        delay_ = std::max(0, delay);
        buf_.assign(static_cast<std::size_t>(std::max(1, delay_)), 0.0f);
        pos_ = 0;
    }
    float pushPop(float x) noexcept {
        if (delay_ == 0) return x;
        const float y = buf_[static_cast<std::size_t>(pos_)];
        buf_[static_cast<std::size_t>(pos_)] = x;
        if (++pos_ == delay_) pos_ = 0;
        return y;
    }

private:
    std::vector<float> buf_;
    int delay_{0}, pos_{0};
};

// Kaiser window design helpers (run in prepare only).
double besselI0(double x) {
    double sum = 1.0, term = 1.0;
    const double y = 0.25 * x * x;
    for (int k = 1; k < 500; ++k) {
        term *= y / (static_cast<double>(k) * k);
        sum += term;
        if (term < 1e-17 * sum) break;
    }
    return sum;
}
double kaiser(double pos, double beta) {  // pos in [-1, 1]
    const double r = 1.0 - pos * pos;
    return r <= 0.0 ? besselI0(0.0) / besselI0(beta) : besselI0(beta * std::sqrt(r)) / besselI0(beta);
}

// ---------------------------------------------------------------------------------------------
// Topology-preserving state-variable filter (A. Simper, "Linear trapezoidal integrated SVF",
// Cytomic 2013). Double precision, stable under per-sample modulation, exact analog-prototype
// responses (bilinear with prewarp) for all modes via output mixing m0*v0 + m1*v1 + m2*v2.
// ---------------------------------------------------------------------------------------------

enum class SvfMode { Low, Band, High, AllPass, Bell, LowShelf, HighShelf };

struct SvfCoef {
    double a1{1.0}, a2{0.0}, a3{0.0};
    double m0{1.0}, m1{0.0}, m2{0.0};
    double g{0.0}, k{1.0};  // the prototype the a's derive from (for per-sample interpolation)
    void derive() noexcept {
        a1 = 1.0 / (1.0 + g * (g + k));
        a2 = g * a1;
        a3 = g * a2;
    }
};

// Per-sample linear interpolation of an SVF's (g, k, m0, m1, m2) towards coefficients computed at
// control rate. Every intermediate set is a valid, stable SVF, and the output mix no longer steps at
// the control rate (a stepped m1 on a boosted bell buzzes and clicks during fast gain changes).
struct CoefRamp {
    SvfCoef c{}, target{};
    double dg{0.0}, dk{0.0}, dm0{0.0}, dm1{0.0}, dm2{0.0};
    int left{0};
    void snap(const SvfCoef& t) noexcept {
        c = target = t;
        left = 0;
    }
    void to(const SvfCoef& t, int n) noexcept {
        target = t;
        const double inv = 1.0 / n;
        dg = (t.g - c.g) * inv;
        dk = (t.k - c.k) * inv;
        dm0 = (t.m0 - c.m0) * inv;
        dm1 = (t.m1 - c.m1) * inv;
        dm2 = (t.m2 - c.m2) * inv;
        left = n;
    }
    void step() noexcept {
        if (left <= 0) return;
        if (--left == 0) {
            c = target;
            return;
        }
        c.g += dg;
        c.k += dk;
        c.m0 += dm0;
        c.m1 += dm1;
        c.m2 += dm2;
        c.derive();
    }
};

SvfCoef svfDesign(SvfMode mode, double fs, double freq, double q, double gainDb = 0.0) noexcept {
    freq = std::clamp(freq, 1.0, 0.495 * fs);
    q = std::max(q, 0.025);
    double g = std::tan(kPi * freq / fs);
    double k = 1.0 / q;
    SvfCoef c;
    switch (mode) {
        case SvfMode::Low: c.m0 = 0; c.m1 = 0; c.m2 = 1; break;
        case SvfMode::Band: c.m0 = 0; c.m1 = k; c.m2 = 0; break;  // unity gain at the centre
        case SvfMode::High: c.m0 = 1; c.m1 = -k; c.m2 = -1; break;
        case SvfMode::AllPass: c.m0 = 1; c.m1 = -2 * k; c.m2 = 0; break;
        case SvfMode::Bell: {
            const double A = std::pow(10.0, gainDb / 40.0);
            k = 1.0 / (q * A);
            c.m0 = 1; c.m1 = k * (A * A - 1); c.m2 = 0;
            break;
        }
        case SvfMode::LowShelf: {
            const double A = std::pow(10.0, gainDb / 40.0);
            g /= std::sqrt(A);
            c.m0 = 1; c.m1 = k * (A - 1); c.m2 = A * A - 1;
            break;
        }
        case SvfMode::HighShelf: {
            const double A = std::pow(10.0, gainDb / 40.0);
            g *= std::sqrt(A);
            c.m0 = A * A; c.m1 = k * (1 - A) * A; c.m2 = 1 - A * A;
            break;
        }
    }
    c.g = g;
    c.k = k;
    c.derive();
    return c;
}

// Any stable digital biquad (b0 + b1 z^-1 + b2 z^-2) / (1 + a1 z^-1 + a2 z^-2) as SVF coefficients:
// in s1 = (1 - z^-1)/(1 + z^-1) the denominator is A s1^2 + B s1 + C; g = sqrt(C/A) normalises it
// to s^2 + k s + 1, and the numerator maps onto the m0/m1/m2 output mix.
SvfCoef svfFromBiquad(double b0, double b1, double b2, double a1, double a2) noexcept {
    const double A = 1.0 - a1 + a2, B = 2.0 * (1.0 - a2), C = 1.0 + a1 + a2;
    const double g = std::sqrt(C / A), k = B / std::sqrt(A * C);
    SvfCoef c;
    c.m0 = (b0 - b1 + b2) / A;
    c.m1 = 2.0 * (b0 - b2) * g / C - c.m0 * k;
    c.m2 = (b0 + b1 + b2) / C - c.m0;
    c.g = g;
    c.k = k;
    c.derive();
    return c;
}

// Peaking EQ matched to the analog prototype (M. Vicanek, "Matched Second Order Digital Filters",
// 2016): impulse-invariant poles, zeros chosen so the magnitude is exact at DC and at the centre
// (with zero slope there). Unlike the bilinear design it does not cramp towards Nyquist: a
// 10 kHz, Q 1 bell at 48 kHz keeps its analog width (bilinear: up to 2.5 dB off).
SvfCoef bellMatched(double fs, double freq, double q, double gainDb) noexcept {
    freq = std::clamp(freq, 1.0, 0.495 * fs);
    q = std::max(q, 0.025);
    const double w0 = 2.0 * kPi * freq / fs;
    const double A = std::pow(10.0, gainDb / 40.0), G2 = A * A * A * A;  // |H(w0)|^2
    const double z = 1.0 / (2.0 * q * A);                                // pole damping
    const double r = std::exp(-z * w0);
    const double a1 = z <= 1.0 ? -2.0 * r * std::cos(std::sqrt(1.0 - z * z) * w0)
                               : -2.0 * r * std::cosh(std::sqrt(z * z - 1.0) * w0);
    const double a2 = r * r;
    const double A0 = (1.0 + a1 + a2) * (1.0 + a1 + a2), A1 = (1.0 - a1 + a2) * (1.0 - a1 + a2), A2 = -4.0 * a2;
    const double p1 = std::sin(0.5 * w0) * std::sin(0.5 * w0), p0 = 1.0 - p1, p2 = 4.0 * p0 * p1;
    const double R1 = (A0 * p0 + A1 * p1 + A2 * p2) * G2;
    const double R2 = (-A0 + A1 + 4.0 * (p0 - p1) * A2) * G2;
    const double B0 = A0, B2 = (R1 - R2 * p1 - B0) / (4.0 * p1 * p1), B1 = R2 + B0 + 4.0 * (p1 - p0) * B2;
    const double sB0 = std::sqrt(B0), sB1 = std::sqrt(std::max(B1, 0.0));
    const double W = 0.5 * (sB0 + sB1);
    const double b0 = 0.5 * (W + std::sqrt(std::max(W * W + B2, 0.0)));
    return svfFromBiquad(b0, 0.5 * (sB0 - sB1), -B2 / (4.0 * b0), a1, a2);
}

struct Svf {
    double ic1{0.0}, ic2{0.0};
    void reset() noexcept { ic1 = ic2 = 0.0; }
    double process(double v0, const SvfCoef& c) noexcept {
        const double v3 = v0 - ic2;
        const double v1 = c.a1 * ic1 + c.a2 * v3;
        const double v2 = ic2 + c.a2 * ic1 + c.a3 * v3;
        ic1 = flushD(2.0 * v1 - ic1);
        ic2 = flushD(2.0 * v2 - ic2);
        return c.m0 * v0 + c.m1 * v1 + c.m2 * v2;
    }
};

// Both channels in lock-step (SIMD-friendly, no per-sample branches). Call flush() once per block.
struct Svf2 {
    double ic1[2]{}, ic2[2]{};
    void reset() noexcept { ic1[0] = ic1[1] = ic2[0] = ic2[1] = 0.0; }
    void flush() noexcept {
        for (int k = 0; k < 2; ++k) { ic1[k] = flushD(ic1[k]); ic2[k] = flushD(ic2[k]); }
    }
    void process(double* v, const SvfCoef& c) noexcept {
        for (int k = 0; k < 2; ++k) {
            const double v0 = v[k];
            const double v3 = v0 - ic2[k];
            const double v1 = c.a1 * ic1[k] + c.a2 * v3;
            const double v2 = ic2[k] + c.a2 * ic1[k] + c.a3 * v3;
            ic1[k] = 2.0 * v1 - ic1[k];
            ic2[k] = 2.0 * v2 - ic2[k];
            v[k] = c.m0 * v0 + c.m1 * v1 + c.m2 * v2;
        }
    }
};

// ---------------------------------------------------------------------------------------------
// Common effect base: strict params, change detection for process().
// ---------------------------------------------------------------------------------------------

class FxBase : public Effect {
public:
    FxBase(const char* type, std::vector<ParamSpec> specs, int expectedCount)
        : type_(type), params_(std::move(specs)) {
        if (static_cast<int>(params_.specs().size()) != expectedCount)
            throw std::logic_error(std::string("dynamics fx '") + type + "': param table mismatch");
    }
    void configure(const json& params) override {
        params_.configure(params, type_);
        validate();
    }
    bool setParam(std::string_view name, float value) override { return params_.set(name, value); }
    const std::vector<ParamSpec>& paramSpecs() const override { return params_.specs(); }

protected:
    virtual void validate() {}
    float p(int i) const noexcept { return params_.get(i); }
    int pc(int i) const noexcept { return static_cast<int>(params_.get(i) + 0.5f); }
    // True once after every configure/setParam; call at the top of process().
    bool paramsChanged() noexcept {
        const unsigned v = params_.version();
        if (v == seen_) return false;
        seen_ = v;
        return true;
    }
    void markSeen() noexcept { seen_ = params_.version(); }

    const char* type_;
    Params params_;
    double fs_{48000.0};

private:
    unsigned seen_{~0u};
};

// =============================================================================================
// eq: hp (12/24) -> low shelf -> 3 bells (matched, no cramping) -> high shelf -> lp (12/24)
// =============================================================================================

class Eq final : public FxBase {
    enum { HpFreq, HpQ, HpSlope, LowFreq, LowGain, LowQ, P1Freq, P1Gain, P1Q, P2Freq, P2Gain, P2Q,
           P3Freq, P3Gain, P3Q, HighFreq, HighGain, HighQ, LpFreq, LpQ, LpSlope, Output, kCount };
    // Smoothed values: frequencies and q in log2, gains in dB.
    enum { gHpF, gHpQ, gLowF, gLowG, gLowQ, gP1F, gP1G, gP1Q, gP2F, gP2G, gP2Q, gP3F, gP3G, gP3Q,
           gHighF, gHighG, gHighQ, gLpF, gLpQ, kGlides };
    static constexpr int kStep = 16;  // coefficient update interval while parameters glide

    static std::vector<ParamSpec> specs() {
        auto bellSpecs = [](std::vector<ParamSpec>& v, const std::string& n, float f, const char* where) {
            v.push_back(num(n + ".freq", 20, 20000, f, "Hz", std::string("Bell ") + where + " centre frequency."));
            v.push_back(num(n + ".gain", -24, 24, 0, "dB", "Bell boost/cut; 0 = band off. Cut narrow, boost wide."));
            v.push_back(num(n + ".q", 0.1f, 20, 1, "", "Bell bandwidth: 0.5 broad, 1 musical, 4-10 surgical notch/resonance."));
        };
        std::vector<ParamSpec> v;
        v.push_back(num("hp.freq", 10, 20000, 10, "Hz",
                        "High-pass cutoff; 10 = off. 30-40 cleans sub rumble, 100-300 thins pads/leads out of the bass range."));
        v.push_back(num("hp.q", 0.5f, 10, 0.7071f, "", "High-pass resonance; 0.707 = flat Butterworth, higher adds a bump at the cutoff."));
        v.push_back(num("hp.slope", 12, 24, 12, "dB/oct", "High-pass steepness: 12 or 24.", false));
        v.push_back(num("low.freq", 20, 5000, 100, "Hz", "Low shelf corner frequency."));
        v.push_back(num("low.gain", -24, 24, 0, "dB", "Low shelf gain; 0 = band off."));
        v.push_back(num("low.q", 0.3f, 3, 0.7071f, "", "Low shelf slope; 0.707 = smooth, higher = steeper with a small bump."));
        bellSpecs(v, "peak1", 200, "1 (lows/low-mids, e.g. 200-400 Hz mud)");
        bellSpecs(v, "peak2", 1000, "2 (mids, e.g. 800-2k honk/presence)");
        bellSpecs(v, "peak3", 5000, "3 (highs, e.g. 3-6k bite, 8-12k air)");
        v.push_back(num("high.freq", 200, 20000, 8000, "Hz", "High shelf corner frequency."));
        v.push_back(num("high.gain", -24, 24, 0, "dB", "High shelf gain; 0 = band off. +2..+4 at 8-12k adds air."));
        v.push_back(num("high.q", 0.3f, 3, 0.7071f, "", "High shelf slope; 0.707 = smooth."));
        v.push_back(num("lp.freq", 20, 20000, 20000, "Hz", "Low-pass cutoff; 20000 = off. 6-12k tames harsh synths."));
        v.push_back(num("lp.q", 0.5f, 10, 0.7071f, "", "Low-pass resonance; 0.707 = flat Butterworth."));
        v.push_back(num("lp.slope", 12, 24, 12, "dB/oct", "Low-pass steepness: 12 or 24.", false));
        v.push_back(num("output", -24, 24, 0, "dB", "Output gain after the EQ."));
        return v;
    }

    struct GainBand {
        SvfMode mode;
        int f, g, q;
        CoefRamp c{};
        bool on{false};
        Svf2 st{};
    };
    struct PassBand {
        SvfMode mode;
        int f, q;
        bool steep{false};
        double w{0.0}, dw{0.0}, wTarget{0.0};  // 0 = bypassed .. 1 = fully active (continuous blend at the "off" extreme)
        CoefRamp c[2]{};
        bool on{false};
        Svf2 st[2]{};
    };

public:
    Eq() : FxBase("eq", specs(), kCount) {}

    void validate() override {
        for (int i : {static_cast<int>(HpSlope), static_cast<int>(LpSlope)}) {
            const float v = p(i);
            if (v != 12.0f && v != 24.0f)
                throw ConfigError("eq: '" + params_.specs()[static_cast<std::size_t>(i)].name + "' must be 12 or 24");
        }
    }

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        // Band gains (dB) glide like other gains (~5 ms), frequencies and q like filter settings (~7 ms).
        for (int g = 0; g < kGlides; ++g) {
            const bool gain = g == gLowG || g == gP1G || g == gP2G || g == gP3G || g == gHighG;
            glide_[static_cast<std::size_t>(g)].prepare(fs_ / kStep, gain ? kGainTau : kShapeTau, 0.0f, 1e-5f);
        }
        out_.prepare(fs_, kGainTau, 1.0f, 1e-7f);
        for (auto& b : gain_) { b.on = false; b.st.reset(); }
        for (auto& b : pass_) {
            b.on = false;
            b.st[0].reset();
            b.st[1].reset();
        }
        setTargets(true);
        markSeen();
        sub_ = 0;
        rampLeft_ = 0;
        updateCoefs(true);
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (paramsChanged()) setTargets(false);
        for (int i = 0; i < frames; ++i) {
            if (sub_ == 0 && moving_) {
                bool mv = false;
                for (auto& g : glide_) { g.next(); mv = mv || g.moving(); }
                moving_ = mv;
                updateCoefs(false);  // coefficients ramp there over the next kStep samples
                rampLeft_ = kStep;
            }
            if (++sub_ == kStep) sub_ = 0;
            if (rampLeft_ > 0) {
                --rampLeft_;
                for (auto& b : gain_)
                    if (b.on) b.c.step();
                for (auto& b : pass_) {
                    if (!b.on) continue;
                    b.w = rampLeft_ > 0 ? b.w + b.dw : b.wTarget;
                    b.c[0].step();
                    b.c[1].step();
                }
            }
            double x[2] = {left[i], right[i]};
            runPass(pass_[0], x);
            for (auto& b : gain_)
                if (b.on) b.st.process(x, b.c.c);
            runPass(pass_[1], x);
            const float g = out_.next();
            left[i] = static_cast<float>(x[0]) * g;
            right[i] = static_cast<float>(x[1]) * g;
        }
        for (auto& b : gain_) b.st.flush();
        for (auto& b : pass_) { b.st[0].flush(); b.st[1].flush(); }
    }

    double tailSeconds() const override { return 0.1; }

private:
    static void runPass(PassBand& b, double* x) noexcept {
        if (!b.on) return;
        double y[2] = {x[0], x[1]};
        b.st[0].process(y, b.c[0].c);
        if (b.steep) b.st[1].process(y, b.c[1].c);
        for (int k = 0; k < 2; ++k) x[k] += b.w * (y[k] - x[k]);
    }

    void setTargets(bool snap) {
        auto put = [&](int g, float v) { glide_[static_cast<std::size_t>(g)].set(v, snap); };
        put(gHpF, std::log2(p(HpFreq)));   put(gHpQ, std::log2(p(HpQ)));
        put(gLowF, std::log2(p(LowFreq))); put(gLowG, p(LowGain));   put(gLowQ, std::log2(p(LowQ)));
        put(gP1F, std::log2(p(P1Freq)));   put(gP1G, p(P1Gain));     put(gP1Q, std::log2(p(P1Q)));
        put(gP2F, std::log2(p(P2Freq)));   put(gP2G, p(P2Gain));     put(gP2Q, std::log2(p(P2Q)));
        put(gP3F, std::log2(p(P3Freq)));   put(gP3G, p(P3Gain));     put(gP3Q, std::log2(p(P3Q)));
        put(gHighF, std::log2(p(HighFreq))); put(gHighG, p(HighGain)); put(gHighQ, std::log2(p(HighQ)));
        put(gLpF, std::log2(p(LpFreq)));   put(gLpQ, std::log2(p(LpQ)));
        pass_[0].steep = p(HpSlope) > 18.0f;
        pass_[1].steep = p(LpSlope) > 18.0f;
        out_.set(dbToLin(p(Output)), snap);
        moving_ = true;
    }

    // New coefficients from the glided values: snapped (prepare) or ramped per sample over kStep.
    // A band switches off only once its glide has landed on the neutral value (gain exactly 0 dB, pass
    // filter at its "off" extreme), where it is transparent, so switching is seamless.
    void updateCoefs(bool snap) noexcept {
        auto val = [&](int g) { return static_cast<double>(glide_[static_cast<std::size_t>(g)].value()); };
        auto set = [&](CoefRamp& r, const SvfCoef& c) { snap ? r.snap(c) : r.to(c, kStep); };
        for (auto& b : gain_) {
            const double gain = val(b.g);
            const bool on = gain != 0.0;
            if (on) {
                const double f = std::exp2(val(b.f)), q = std::exp2(val(b.q));
                const SvfCoef c = b.mode == SvfMode::Bell ? bellMatched(fs_, f, q, gain) : svfDesign(b.mode, fs_, f, q, gain);
                if (!b.on) {  // start from the neutral version of this band: the output ramps in from 0 dB
                    b.st.reset();
                    b.c.snap(b.mode == SvfMode::Bell ? bellMatched(fs_, f, q, 0.0) : svfDesign(b.mode, fs_, f, q, 0.0));
                }
                set(b.c, c);
            }
            else if (b.on) b.st.reset();
            b.on = on;
        }
        for (int k = 0; k < 2; ++k) {
            PassBand& b = pass_[k];
            const double lf = val(b.f);
            const double w = std::clamp(k == 0 ? (lf - offLog2(10.0f)) / kBlend : (offLog2(20000.0f) - lf) / kBlend, 0.0, 1.0);
            const bool on = w > 0.0;
            if (on) {
                const double f = std::exp2(lf), q = std::exp2(val(b.q));
                if (!b.on) b.w = 0.0;
                if (b.steep) {  // 4th-order Butterworth pole pair split, second stage carries the user's q
                    const SvfCoef c0 = svfDesign(b.mode, fs_, f, 0.541196100146);
                    const SvfCoef c1 = svfDesign(b.mode, fs_, f, 1.306562964876 * q / 0.707106781187);
                    if (!b.on) { b.c[0].snap(c0); b.c[1].snap(c1); }
                    set(b.c[0], c0);
                    set(b.c[1], c1);
                } else {
                    const SvfCoef c0 = svfDesign(b.mode, fs_, f, q);
                    if (!b.on) b.c[0].snap(c0);
                    set(b.c[0], c0);
                }
                b.wTarget = w;
                if (snap) {
                    b.w = w;
                    b.dw = 0.0;
                } else {
                    b.dw = (w - b.w) / kStep;
                }
            } else if (b.on) {
                b.st[0].reset();
                b.st[1].reset();
                b.w = 0.0;
            }
            b.on = on;
        }
    }

    std::array<Glide, kGlides> glide_{};
    Glide out_;
    std::array<GainBand, 5> gain_{{
        {SvfMode::LowShelf, gLowF, gLowG, gLowQ},
        {SvfMode::Bell, gP1F, gP1G, gP1Q},
        {SvfMode::Bell, gP2F, gP2G, gP2Q},
        {SvfMode::Bell, gP3F, gP3G, gP3Q},
        {SvfMode::HighShelf, gHighF, gHighG, gHighQ},
    }};
    std::array<PassBand, 2> pass_{{{SvfMode::High, gHpF, gHpQ}, {SvfMode::Low, gLpF, gLpQ}}};
    int sub_{0}, rampLeft_{0};
    bool moving_{true};
};

// =============================================================================================
// filter: resonant multimode (SVF lp|bp|hp, 4-pole ZDF ladder lp) for sweeps
// =============================================================================================

class Filter final : public FxBase {
    enum { Mode, Cutoff, Resonance, Drive, Mix, kCount };
    enum { Lp, Bp, Hp, Ladder };

    static std::vector<ParamSpec> specs() {
        return {
            choice("mode", {"lp", "bp", "hp", "ladder"}, 0,
                   "lp/bp/hp = 12 dB/oct state-variable filter; ladder = 24 dB/oct Moog-style low-pass (fatter, steeper)."),
            num("cutoff", 20, 20000, 20000, "Hz",
                "Cutoff; automate with 'exp' curves for sweeps. lp/ladder fully open (bypassed) at 20000, hp open at 20."),
            num("resonance", 0, 1, 0.15f, "",
                "Peak at the cutoff: 0 = none, 0.3-0.6 = classic DJ sweep, 1 = screaming (~+21 dB peak, careful)."),
            num("drive", 0, 24, 0, "dB", "Pre-filter tanh saturation (level-compensated); 0 = clean. Heavy distortion: use saturator."),
            num("mix", 0, 1, 1, "", "Dry/wet mix."),
        };
    }

public:
    Filter() : FxBase("filter", specs(), kCount) {}

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        mode_ = pc(Mode);
        cutG_.prepare(fs_, kShapeTau, std::log2(p(Cutoff)), 1e-5f);
        resG_.prepare(fs_, kShapeTau, p(Resonance), 1e-5f);
        driveG_.prepare(fs_, kShapeTau, p(Drive), 1e-4f);
        mixG_.prepare(fs_, kGainTau, p(Mix), 1e-6f);
        for (auto& s : svf_) s.reset();
        for (auto& l : lad_) l.fill(0.0);
        markSeen();
        updateCoefs();
        updateDrive();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (paramsChanged()) {
            cutG_.setTarget(std::log2(p(Cutoff)));
            resG_.setTarget(p(Resonance));
            driveG_.setTarget(p(Drive));
            mixG_.setTarget(p(Mix));
        }
        float* io[2] = {left, right};
        for (int i = 0; i < frames; ++i) {
            if (cutG_.moving() || resG_.moving()) {
                cutG_.next();
                resG_.next();
                updateCoefs();
            }
            if (driveG_.moving()) { driveG_.next(); updateDrive(); }
            const double mix = mixG_.next();
            for (int ch = 0; ch < 2; ++ch) {
                const double x = io[ch][i];
                double xd = x;
                if (driveW_ > 0.0) xd = x + driveW_ * (driveC_ * std::tanh(driveD_ * x) - x);
                double y = mode_ == Ladder ? ladder(lad_[ch], xd) : svf_[ch].process(xd, coef_);
                y = xd + openW_ * (y - xd);
                io[ch][i] = static_cast<float>(x + mix * (y - x));
            }
        }
    }

    double tailSeconds() const override { return 0.25; }

private:
    void updateCoefs() noexcept {
        const double lf = cutG_.value();
        const double f = std::exp2(lf), r = resG_.value();
        switch (mode_) {
            case Hp: openW_ = std::clamp((lf - offLog2(20.0f)) / kBlend, 0.0, 1.0); break;
            case Bp: openW_ = 1.0; break;
            default: openW_ = std::clamp((offLog2(20000.0f) - lf) / kBlend, 0.0, 1.0); break;
        }
        if (mode_ == Ladder) {
            const double g = std::tan(kPi * std::clamp(f, 5.0, 0.49 * fs_) / fs_);
            G_ = g / (1.0 + g);
            G4_ = G_ * G_ * G_ * G_;
            // Linear ladder: gain at the cutoff = (1 + k) / (4 - k) after the passband compensation.
            // Map resonance so that peak rises exponentially from -12 dB (k = 0) to +21 dB (k = 3.6),
            // matching the SVF modes; k -> 4 would be a +34 dB, barely damped peak.
            const double peak = 0.25 * std::pow(46.0, r);
            k_ = (4.0 * peak - 1.0) / (1.0 + peak);
        } else {
            const double q = 0.70710678 * std::pow(16.0, r);
            coef_ = svfDesign(mode_ == Lp ? SvfMode::Low : mode_ == Bp ? SvfMode::Band : SvfMode::High, fs_, f, q);
        }
    }
    void updateDrive() noexcept {
        const double db = driveG_.value();
        driveD_ = std::pow(10.0, db / 20.0);
        driveC_ = 0.5 / std::tanh(0.5 * driveD_);  // a 0.5 peak keeps its level
        driveW_ = std::clamp(db / 3.0, 0.0, 1.0);  // fade the curve in over the first 3 dB
    }
    // Zero-delay-feedback 4-pole ladder (Zavalishin, "The Art of VA Filter Design", ch. 5):
    // each stage y = G*x + (1-G)*s, the feedback loop solved in closed form.
    double ladder(std::array<double, 4>& s, double x) const noexcept {
        const double G = G_, B = 1.0 - G_;
        const double sigma = B * (G * G * G * s[0] + G * G * s[1] + G * s[2] + s[3]);
        const double y4 = (G4_ * x + sigma) / (1.0 + k_ * G4_);
        double u = x - k_ * y4;
        for (int j = 0; j < 4; ++j) {
            const double v = (u - s[j]) * G;
            const double y = v + s[j];
            s[j] = flushD(y + v);
            u = y;
        }
        return u * (1.0 + k_);  // unity passband gain regardless of resonance
    }

    int mode_{Lp};
    Glide cutG_, resG_, driveG_, mixG_;
    SvfCoef coef_{};
    Svf svf_[2]{};
    std::array<double, 4> lad_[2]{};
    double G_{0.5}, G4_{0.0625}, k_{0.0}, openW_{1.0};
    double driveD_{1.0}, driveC_{1.0}, driveW_{0.0};
};

// =============================================================================================
// compressor: feed-forward, stereo-linked, log-domain smooth decoupled peak detector
// (Giannoulis, Massberg & Reiss, "Digital Dynamic Range Compressor Design", JAES 2012, fig. 5b):
// the gain computer's reduction is peak-held with the release time constant, then smoothed with
// the attack time constant. A branching detector (attack while rising, release while falling) on
// the instantaneous level releases between the waveform peaks and has to re-attack every cycle, so
// it settles 1-3 dB short of the static curve (more with slow attack / fast release) and ripples at
// twice the signal frequency (audible distortion on bass). The decoupled one reads within ~0.5 dB
// of the curve on steady tones with a fraction of the ripple; attack and release keep their meaning
// (the hold stage's release is shortened by the attack time, which the second stage adds back).
// Band mode (band > 0) makes it a dynamic EQ: the detector hears only a band (a unity-peak band-pass
// on the key, after keyhp) and the gain acts only on that band of the signal: out = x + (g - 1) * bp(x)
// with the same band-pass, which is exactly a peaking bell of gain g at 'band' (phase-coherent, no
// latency). Keyed from a lead ("sidechain"), it carves the lead's presence band out of a bed only while
// the lead plays. 'range' caps the reduction (a dynamic EQ's maximum cut).
// =============================================================================================

class Compressor final : public FxBase {
    enum { Threshold, Ratio, Knee, Attack, Release, Makeup, AutoMakeup, Mix, Detector, KeyHp, Range, Band, BandQ, kCount };

    static std::vector<ParamSpec> specs() {
        return {
            num("threshold", -60, 0, -18, "dB", "Level (dBFS) above which gain reduction starts."),
            num("ratio", 1, 30, 4, ":1", "Compression ratio: 1.5-2 gentle glue, 4 firm, 8-30 limiting."),
            num("knee", 0, 24, 6, "dB", "Soft-knee width around the threshold; 0 = hard knee, 6-12 = smooth and musical."),
            num("attack", 0.05f, 300, 10, "ms",
                "Clamp-down time constant: 0.1-1 catches transients, 10-30 lets drum attacks punch through."),
            num("release", 5, 3000, 120, "ms", "Recovery time constant: 50-150 drums, 200-600 bus glue."),
            num("makeup", -24, 24, 0, "dB", "Output gain after compression."),
            toggle("automakeup", false, "Adds makeup gain so a -10 dBFS peak comes out at about -10 dBFS again."),
            num("mix", 0, 1, 1, "", "Parallel (New York) compression: 1 = fully compressed, 0.3-0.5 = dense but natural."),
            choice("detector", {"peak", "rms"}, 0, "peak = fast and precise (drums), rms = smoother, program-dependent (buses, pads)."),
            num("keyhp", 20, 500, 20, "Hz", "High-pass on the detector key so low end triggers less reduction (100-150 on a mix bus); 20 = off."),
            num("range", 0, 60, 60, "dB",
                "Maximum gain reduction (a dynamic EQ's largest cut): 3-6 for carving a bed under a lead, 60 = unlimited."),
            num("band", 0, 16000, 0, "Hz",
                "0 = broadband compressor. > 0 = dynamic EQ: the detector listens only around this frequency and the "
                "reduction (and makeup) acts only on that band - a bell that dips as the key gets loud. Keyed from a lead "
                "(\"sidechain\": the sax) at 2000-3000 Hz, Q 0.7, range 3-6: the bed's presence steps aside while the lead "
                "plays (song.carve()); unkeyed at 5-8 kHz: a de-esser.", false),
            num("bandq", 0.2f, 8, 0.7f, "",
                "Band mode: width of the band (Q; 0.5-0.8 = 2 octaves: 1.2-4.5 kHz around 2.5 kHz, 2-4 = narrow).", false),
        };
    }

public:
    Compressor() : FxBase("compressor", specs(), kCount) {}

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        thrG_.prepare(fs_, kShapeTau, p(Threshold), 1e-4f);
        ratioG_.prepare(fs_, kShapeTau, p(Ratio), 1e-5f);
        kneeG_.prepare(fs_, kShapeTau, p(Knee), 1e-4f);
        makeupG_.prepare(fs_, kGainTau, p(Makeup), 1e-4f);
        autoG_.prepare(fs_, kGainTau, p(AutoMakeup), 1e-5f);
        mixG_.prepare(fs_, kGainTau, p(Mix), 1e-6f);
        rmsCoeff_ = onePoleCoeff(fs_, 0.008);
        rangeG_.prepare(fs_, kShapeTau, p(Range), 1e-4f);
        for (int c = 0; c < 2; ++c) {
            key_[c].reset();
            keyBand_[c].reset();
            sigBand_[c].reset();
        }
        env_ = hold_ = 0.0f;
        ms_ = 0.0f;
        markSeen();
        updateStatic();
    }

    void process(float* left, float* right, int frames, const float* scLeft, const float* scRight) override {
        if (paramsChanged()) {
            thrG_.setTarget(p(Threshold));
            ratioG_.setTarget(p(Ratio));
            kneeG_.setTarget(p(Knee));
            makeupG_.setTarget(p(Makeup));
            autoG_.setTarget(p(AutoMakeup));
            mixG_.setTarget(p(Mix));
            rangeG_.setTarget(p(Range));
            updateStatic();
        }
        const bool sc = scLeft != nullptr && scRight != nullptr;
        for (int i = 0; i < frames; ++i) {
            const float thr = thrG_.next(), ratio = ratioG_.next(), knee = kneeG_.next();
            const float makeup = makeupG_.next(), autoAmt = autoG_.next(), mix = mixG_.next(), range = rangeG_.next();
            double kl = key_[0].process(sc ? scLeft[i] : left[i], keyCoef_);
            double kr = key_[1].process(sc ? scRight[i] : right[i], keyCoef_);
            if (band_) {
                kl = keyBand_[0].process(kl, bandCoef_);
                kr = keyBand_[1].process(kr, bandCoef_);
            }
            float levelDb;
            if (rms_) {
                const float e = static_cast<float>(0.5 * (kl * kl + kr * kr));
                ms_ = dsp::flush(e + (ms_ - e) * rmsCoeff_);
                levelDb = 3.01029995664f * std::log2(std::max(ms_, 1e-12f));  // 10*log10
            } else {
                const float e = static_cast<float>(std::max(kl * kl, kr * kr));
                levelDb = 3.01029995664f * std::log2(std::max(e, 1e-12f));
            }
            const float reduction = std::min(levelDb - curve(levelDb, thr, ratio, knee), range);
            hold_ = dsp::flush(std::max(reduction, reduction + (hold_ - reduction) * relCoeff_));
            env_ = dsp::flush(hold_ + (env_ - hold_) * attCoeff_);
            float gainDb = makeup - env_;
            if (autoAmt > 0.0f) gainDb += autoAmt * (-10.0f - curve(-10.0f, thr, ratio, knee));
            const float g = 1.0f + mix * (dbToLin(gainDb) - 1.0f);
            if (band_) {  // a bell of gain g: x + (g - 1) * band-pass(x) (the band-pass has unity gain at its centre)
                const double bl = sigBand_[0].process(left[i], bandCoef_);
                const double br = sigBand_[1].process(right[i], bandCoef_);
                left[i] = static_cast<float>(left[i] + (g - 1.0f) * bl);
                right[i] = static_cast<float>(right[i] + (g - 1.0f) * br);
            } else {
                left[i] *= g;
                right[i] *= g;
            }
        }
    }

private:
    static float curve(float x, float thr, float ratio, float knee) noexcept {
        const float over = x - thr;
        if (knee > 0.0f && 2.0f * std::fabs(over) <= knee) {
            const float t = over + 0.5f * knee;
            return x + (1.0f / ratio - 1.0f) * t * t / (2.0f * knee);
        }
        return over > 0.0f ? thr + over / ratio : x;
    }
    void updateStatic() noexcept {
        attCoeff_ = onePoleCoeff(fs_, p(Attack) * 0.001);
        // The release runs through both stages (peak hold, then the attack smoother), which would add
        // the attack time to it: the hold stage gets the difference (at least half the release).
        relCoeff_ = onePoleCoeff(fs_, std::max(p(Release) - p(Attack), 0.5f * p(Release)) * 0.001);
        rms_ = pc(Detector) == 1;
        keyCoef_ = svfDesign(SvfMode::High, fs_, p(KeyHp), 0.70710678);
        band_ = p(Band) > 0.0f;
        if (band_) bandCoef_ = svfDesign(SvfMode::Band, fs_, std::max(p(Band), 20.0f), p(BandQ));
    }

    Glide thrG_, ratioG_, kneeG_, makeupG_, autoG_, mixG_, rangeG_;
    float attCoeff_{0.0f}, relCoeff_{0.0f}, rmsCoeff_{0.0f};
    float env_{0.0f}, hold_{0.0f}, ms_{0.0f};
    bool rms_{false}, band_{false};
    SvfCoef keyCoef_{}, bandCoef_{};
    Svf key_[2]{}, keyBand_[2]{}, sigBand_[2]{};
};

// =============================================================================================
// ducker: the sidechain pump. Triggered by key transients or a tempo grid; gain envelope
// attack (raised cosine) -> hold -> release (shaped, dB-linear at curve 0).
// =============================================================================================

class Ducker final : public FxBase {
    enum { Mode, Threshold, Depth, Attack, Hold, Release, Curve, Rate, Offset, kCount };
    enum class Phase { Idle, Attack, Hold, Release };

    static std::vector<ParamSpec> specs() {
        return {
            choice("mode", {"key", "tempo"}, 0,
                   "key = duck whenever the sidechain (e.g. the kick) hits (without a \"sidechain\" it falls back to the tempo grid); tempo = duck on a beat grid, no sidechain needed."),
            num("threshold", -60, 0, -30, "dB", "Key mode: key peak level (dBFS) that triggers a duck."),
            num("depth", 0, 48, 10, "dB", "Gain reduction at the bottom of each duck: 4-6 subtle, 8-14 classic synthwave pump, 24+ gating."),
            num("attack", 0.5f, 50, 2, "ms", "Fade-down time after a trigger (raised cosine, click-free)."),
            num("hold", 0, 1000, 10, "ms", "Time held at full depth before releasing."),
            num("release", 10, 2000, 200, "ms",
                "Recovery time back to 0 dB; for a breathing pump use roughly 60-80% of the beat (60000/bpm ms)."),
            num("curve", -1, 1, 0, "",
                "Release shape: 0 = even (dB-linear), >0 = stays down longer then swells back (punchier pump), <0 = fast initial recovery."),
            num("rate", 0.125f, 8, 1, "beats", "Tempo mode: duck every this many beats (1 = quarter notes, 0.5 = eighths, 2 = half notes)."),
            num("offset", -1, 1, 0, "beats", "Tempo mode: shift of the duck grid (negative = earlier than the beat)."),
        };
    }

public:
    Ducker() : FxBase("ducker", specs(), kCount) {}

    // A changing tempo: the tempo grid follows the song's beats (tempo mode and key mode without a key).
    void setTempoMap(const TempoMap& map) override {
        tempo_ = &map;
        clock_.attach(&map);
    }

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        beatsPerSample_ = ctx.bpm / (60.0 * fs_);
        // The grid counts from song beat 0, also in a preview render (first sample = song beat startBeat,
        // rounded to a song sample exactly like the renderer does).
        startSample_ = songStartSample(ctx.startBeat, fs_, ctx.bpm, tempo_);
        depthG_.prepare(fs_, kGainTau, p(Depth), 1e-4f);
        curveG_.prepare(fs_, kGainTau, p(Curve), 1e-5f);
        holdN_ = static_cast<int>(0.010 * fs_);
        fastRel_ = onePoleCoeff(fs_, 0.020);
        slowCoeff_ = onePoleCoeff(fs_, 0.030);
        holdCount_ = 0;
        refractory_ = static_cast<int>(0.030 * fs_);
        phase_ = Phase::Idle;
        e_ = e0_ = 0.0f;
        t_ = 0.0f;
        holdLeft_ = 0;
        fast_ = slow_ = 0.0f;
        armed_ = true;
        sinceTrigger_ = refractory_;
        sample_ = 0;
        mode_ = pc(Mode);
        markSeen();
        updateStatic();
        lastCell_ = cellAt(-1);
        caughtUp_ = false;
    }

    void process(float* left, float* right, int frames, const float* scLeft, const float* scRight) override {
        if (paramsChanged()) {
            depthG_.setTarget(p(Depth));
            curveG_.setTarget(p(Curve));
            updateStatic();
            lastCell_ = cellAt(sample_ - 1);  // a new rate/offset must not fire a spurious duck
        }
        // Key mode without a sidechain would silently do nothing: it follows the tempo grid instead.
        const bool key = mode_ == 0 && scLeft != nullptr && scRight != nullptr;
        if (!caughtUp_) {
            caughtUp_ = true;
            if (!key) catchUp();
        }
        for (int i = 0; i < frames; ++i, ++sample_) {
            bool trigger = false;
            if (key) {
                trigger = keyTrigger(std::max(std::fabs(scLeft[i]), std::fabs(scRight[i])));
            } else {
                const std::int64_t cell = cellAt(sample_);
                trigger = cell != lastCell_;
                lastCell_ = cell;
            }
            advance(trigger, curveG_.next());
            const float depth = depthG_.next();
            const float g = e_ > 0.0f ? dbToLin(-depth * e_) : 1.0f;
            left[i] *= g;
            right[i] *= g;
        }
    }

private:
    // One sample of the gain envelope (0 = no reduction, 1 = full depth).
    void advance(bool trigger, float curveV) noexcept {
        if (trigger) {
            phase_ = Phase::Attack;
            e0_ = e_;
            t_ = 0.0f;
            sinceTrigger_ = 0;
        } else if (sinceTrigger_ < refractory_) {
            ++sinceTrigger_;
        }
        switch (phase_) {
            case Phase::Attack:
                t_ += attInc_;
                if (t_ >= 1.0f) {
                    e_ = 1.0f;
                    phase_ = Phase::Hold;
                    holdLeft_ = holdSamples_;
                } else {
                    e_ = e0_ + (1.0f - e0_) * 0.5f * (1.0f - std::cos(static_cast<float>(kPi) * t_));
                }
                break;
            case Phase::Hold:
                e_ = 1.0f;
                if (--holdLeft_ <= 0) { phase_ = Phase::Release; t_ = 0.0f; }
                break;
            case Phase::Release:
                t_ += relInc_;
                if (t_ >= 1.0f) {
                    e_ = 0.0f;
                    phase_ = Phase::Idle;
                } else {
                    // curve >= 0: 1 - t^p (slow start); curve < 0: (1 - t)^p (fast start,
                    // finite initial slope so there is no gain jump at the start of the release).
                    e_ = curveV >= 0.0f ? 1.0f - std::pow(t_, std::exp2(2.0f * curveV))
                                        : std::pow(1.0f - t_, std::exp2(-2.0f * curveV));
                }
                break;
            case Phase::Idle: e_ = 0.0f; break;
        }
    }

    // Tempo grid in a render that starts mid-song (preview): replay the envelope over the last grid
    // cells before the first sample (never before song beat 0), so a duck in progress there is exactly
    // where a full render would have it.
    void catchUp() noexcept {
        const std::int64_t songStart = -startSample_;
        if (songStart >= 0 || beatsPerSample_ <= 0.0) return;
        // (with a tempo map: cells at the slowest tempo, the longest span back)
        const double cellSamples = rate_ / (tempo_ ? tempo_->minBpm() / (60.0 * fs_) : beatsPerSample_);
        const double span = (2.0 + std::ceil(0.1 * fs_ / cellSamples)) * cellSamples;  // covers any attack
        std::int64_t n = std::max(songStart, -static_cast<std::int64_t>(std::ceil(span)));
        lastCell_ = cellAt(n - 1);
        const float curveV = curveG_.value();
        for (; n < 0; ++n) {
            const std::int64_t cell = cellAt(n);
            advance(cell != lastCell_, curveV);
            lastCell_ = cell;
        }
    }

    // Key envelope: peak hold (10 ms, so 50 Hz+ kicks give a ripple-free envelope) then 20 ms
    // release. Schmitt trigger at the threshold (re-arms 6 dB below), plus an onset path (envelope
    // jumps > 6 dB over a 30 ms follower) so a new hit retriggers while a boomy tail is still
    // above the threshold.
    bool keyTrigger(float level) noexcept {
        if (level >= fast_) {
            fast_ = level;
            holdCount_ = holdN_;
        } else if (holdCount_ > 0) {
            --holdCount_;
        } else {
            fast_ = dsp::flush(fast_ * fastRel_);
        }
        const float slowBefore = slow_;
        slow_ = dsp::flush(fast_ + (slow_ - fast_) * slowCoeff_);
        const float fastDb = linToDb(fast_);
        bool trig = false;
        if (armed_) {
            if (fastDb >= thrDb_) { trig = true; armed_ = false; }
        } else if (fastDb < thrDb_ - 6.0f) {
            armed_ = true;
        }
        if (!trig && fastDb >= thrDb_ && sinceTrigger_ >= refractory_ && fast_ > 2.0f * slowBefore) trig = true;
        return trig;
    }
    // Grid cell of rendered sample n (song sample startSample + n).
    std::int64_t cellAt(std::int64_t n) const noexcept {
        const double beats = tempo_ ? clock_.beatAt(startSample_ + n) : static_cast<double>(startSample_ + n) * beatsPerSample_;
        return static_cast<std::int64_t>(std::floor((beats - offset_) / rate_ + 1e-9));
    }
    void updateStatic() noexcept {
        thrDb_ = p(Threshold);
        attInc_ = static_cast<float>(1.0 / std::max(1.0, p(Attack) * 0.001 * fs_));
        holdSamples_ = static_cast<int>(p(Hold) * 0.001 * fs_ + 0.5);
        relInc_ = static_cast<float>(1.0 / std::max(1.0, p(Release) * 0.001 * fs_));
        rate_ = p(Rate);
        offset_ = p(Offset);
    }

    int mode_{0};
    Glide depthG_, curveG_;
    double beatsPerSample_{120.0 / 2880000.0}, rate_{1.0}, offset_{0.0};
    std::int64_t startSample_{0};
    const TempoMap* tempo_{nullptr};  // set when the song's tempo changes
    BeatClock clock_;
    float thrDb_{-30.0f}, attInc_{0.01f}, relInc_{0.001f};
    int holdSamples_{0}, holdLeft_{0}, refractory_{1440}, sinceTrigger_{0}, holdN_{480}, holdCount_{0};
    Phase phase_{Phase::Idle};
    float e_{0.0f}, e0_{0.0f}, t_{0.0f};
    float fast_{0.0f}, slow_{0.0f}, fastRel_{0.0f}, slowCoeff_{0.0f};
    bool armed_{true}, caughtUp_{false};
    std::int64_t sample_{0}, lastCell_{0};
};

// =============================================================================================
// saturator: 4x oversampled waveshaper with first-order antiderivative anti-aliasing (Parker,
// Zavalishin & Le Bihan, DAFx 2016). Oversampling uses polyphase IIR half-bands (below) instead
// of linear-phase FIRs: the group delay is ~5.5 samples at 1x instead of ~70. The engine does not
// compensate latency on tracks/buses, and 70 samples put the track 1.5 ms late and comb-filtered
// any parallel (send-bus) use. The dry signal runs through the same linear chain (the curve
// replaced by its small-signal equivalent), so dry/wet mixing is phase-coherent.
// =============================================================================================

// Oversampling half-bands: fx/HalfBand.h.
using hb::D2;
using hb::d2;
using hb::designHalfBand;
using hb::flushD2;
using hb::HalfBand;

class Saturator final : public FxBase {
    enum { Mode, Drive, Bias, Tone, Output, Mix, kCount };
    enum { Tape, Tube, Hard, Fold };
    // Stage 1 (1x <-> 2x): 8 coefficients, passband to 0.225 of the 2x rate (21.6 kHz at 48k),
    // ~106 dB stopband. Stage 2 (2x <-> 4x): 4 coefficients, wide transition, ~117 dB.
    static constexpr int kN1 = 8, kN2 = 4;
    static constexpr double kTbw1 = 0.05, kTbw2 = 0.25;

    static std::vector<ParamSpec> specs() {
        return {
            choice("mode", {"tape", "tube", "hard", "fold"}, 0,
                   "tape = soft symmetric (odd harmonics, glue), tube = asymmetric warmth (even+odd), hard = clipper, fold = wavefolder (metallic)."),
            num("drive", -12, 36, 6, "dB",
                "Input gain into the curve; loudness is auto-compensated (a -12 dBFS sine keeps its RMS). 0-6 warmth, 9-18 grit, 24+ fuzz."),
            num("bias", -1, 1, 0, "", "Asymmetry: adds even harmonics (DC is removed)."),
            num("tone", -12, 12, 0, "dB", "Tilt EQ after the curve, pivot ~800 Hz: negative = darker, positive = brighter."),
            num("output", -24, 24, 0, "dB", "Output gain (after the mix)."),
            num("mix", 0, 1, 1, "", "Dry/wet; the dry path is phase-aligned with the wet so parallel saturation stays coherent."),
        };
    }

    struct Shape {
        float d{1.0f}, b{0.0f}, c{1.0f}, fb{0.0f};  // drive, bias, output scale, curve(bias)
    };
    struct Chan {
        float adaaV{0.0f}, adaaS{1.0f};  // previous curve input and its sqrt term (tape/tube)
        double dcX{0.0}, dcY{0.0}, tilt{0.0};
        std::vector<float> z, wet, dry;  // 4x work buffer, 1x wet and dry reference
    };
    struct Chain {  // both channels
        HalfBand<kN1> up1, dn1, dn1Dry;
        HalfBand<kN2> up2, dn2, dn2Dry;
        D2 eq1{}, eq2{};                // droop equaliser memory (wet)
        D2 dryPrev{}, dq1{}, dq2{};     // dry: small-signal ADAA mean + droop equaliser
    };

public:
    Saturator() : FxBase("saturator", specs(), kCount) {}

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        maxBlock_ = std::max(1, ctx.maxBlock);
        hb1_ = designHalfBand<kN1>(kTbw1);
        hb2_ = designHalfBand<kN2>(kTbw2);
        for (std::size_t k = 0; k < sineTable_.size(); ++k)
            sineTable_[k] = std::sin(2.0 * kPi * (static_cast<double>(k) + 0.5) / static_cast<double>(sineTable_.size()));
        mode_ = pc(Mode);
        chain_ = Chain{};
        for (auto& c : ch_) {
            c = Chan{};
            c.z.assign(static_cast<std::size_t>(4 * maxBlock_), 0.0f);
            c.wet.assign(static_cast<std::size_t>(maxBlock_), 0.0f);
            c.dry.assign(static_cast<std::size_t>(maxBlock_), 0.0f);
        }
        shapes_.assign(static_cast<std::size_t>(maxBlock_), Shape{});
        driveG_.prepare(fs_, kShapeTau, p(Drive), 1e-4f);
        biasG_.prepare(fs_, kShapeTau, p(Bias), 1e-5f);
        toneG_.prepare(fs_, kShapeTau, p(Tone), 1e-4f);
        outG_.prepare(fs_, kGainTau, dbToLin(p(Output)), 1e-7f);
        mixG_.prepare(fs_, kGainTau, p(Mix), 1e-6f);
        dcR_ = std::exp(-2.0 * kPi * 3.0 / fs_);
        tiltA_ = 1.0 - std::exp(-2.0 * kPi * 800.0 / fs_);
        markSeen();
        updateShape();
        prevShape_ = shape_;
        updateTone();
        for (auto& c : ch_) {  // start the ADAA memory at the resting point of the curve
            c.adaaV = shape_.b;
            c.adaaS = sqrtTerm(shape_.b);
        }
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (paramsChanged()) {
            driveG_.setTarget(p(Drive));
            biasG_.setTarget(p(Bias));
            toneG_.setTarget(p(Tone));
            outG_.setTarget(dbToLin(p(Output)));
            mixG_.setTarget(p(Mix));
        }
        for (int off = 0; off < frames; off += maxBlock_) {
            const int n = std::min(maxBlock_, frames - off);
            for (int j = 0; j < n; ++j) {
                if (driveG_.moving() || biasG_.moving()) {
                    driveG_.next();
                    biasG_.next();
                    updateShape();
                }
                shapes_[static_cast<std::size_t>(j)] = shape_;
            }
            float* io[2] = {left + off, right + off};
            runChain(io[0], io[1], n);
            for (int j = 0; j < n; ++j) {
                if (toneG_.moving()) { toneG_.next(); updateTone(); }
                const float mix = mixG_.next(), out = outG_.next();
                for (int ch = 0; ch < 2; ++ch) {
                    Chan& c = ch_[ch];
                    const std::size_t js = static_cast<std::size_t>(j);
                    const double wet = c.wet[js];
                    const double hp = wet - c.dcX + dcR_ * c.dcY;  // DC blocker (3 Hz)
                    c.dcX = wet;
                    c.dcY = flushD(hp);
                    c.tilt = flushD(c.tilt + tiltA_ * (hp - c.tilt));
                    const float toned = static_cast<float>(tiltLow_ * c.tilt + tiltHigh_ * (hp - c.tilt));
                    io[ch][j] = (toned * mix + c.dry[js] * (1.0f - mix)) * out;
                }
            }
        }
    }

    double tailSeconds() const override { return 0.01; }

private:
    // Inverse of the ADAA's (1 + z^-1)/2 droop: 1 + (1 - cos w)/4, within 0.04 dB up to 20 kHz
    // at 48k. Symmetric 3 taps at 4x (one 4x sample of delay).
    static D2 droopEq(D2& x1, D2& x2, D2 x) noexcept {
        const D2 y = x1 * 1.25 - (x + x2) * 0.125;
        x2 = x1;
        x1 = x;
        return y;
    }

    // 1x -> 2x -> 4x, shape (ADAA), equalise, 4x -> 2x -> 1x. The dry reference takes the same
    // path with the curve replaced by the ADAA's small-signal response (the two-sample mean).
    void runChain(const float* inL, const float* inR, int n) noexcept {
        Chain& k = chain_;
        float* zl = ch_[0].z.data();
        float* zr = ch_[1].z.data();
        for (int j = 0; j < n; ++j) {
            D2 a0, a1, u[4];
            k.up1.up(hb1_, d2(inL[j], inR[j]), a0, a1);
            k.up2.up(hb2_, a0, u[0], u[1]);
            k.up2.up(hb2_, a1, u[2], u[3]);
            for (int i = 0; i < 4; ++i) {
                zl[4 * j + i] = static_cast<float>(u[i][0]);
                zr[4 * j + i] = static_cast<float>(u[i][1]);
                const D2 mean = (u[i] + k.dryPrev) * 0.5;
                k.dryPrev = u[i];
                u[i] = droopEq(k.dq1, k.dq2, mean);
            }
            const D2 h0 = k.dn2Dry.down(hb2_, u[0], u[1]);  // (sequenced: stateful calls)
            const D2 h1 = k.dn2Dry.down(hb2_, u[2], u[3]);
            const D2 d = k.dn1Dry.down(hb1_, h0, h1);
            ch_[0].dry[static_cast<std::size_t>(j)] = static_cast<float>(d[0]);
            ch_[1].dry[static_cast<std::size_t>(j)] = static_cast<float>(d[1]);
        }
        // While drive/bias glide, the curve parameters are interpolated per 4x sample (stepping them at
        // 1x would add a buzz at the sample rate / 4 and small steps to the output).
        bool varying = false;
        for (int j = 0; j < n && !varying; ++j) {
            const Shape& a = j ? shapes_[static_cast<std::size_t>(j - 1)] : prevShape_;
            const Shape& b = shapes_[static_cast<std::size_t>(j)];
            varying = a.d != b.d || a.b != b.b || a.c != b.c || a.fb != b.fb;
        }
        for (Chan& c : ch_) {
            if (varying) {
                switch (mode_) {
                    case Tape: shapeBlock<Tape, true>(c, c.z.data(), 4 * n); break;
                    case Tube: shapeBlock<Tube, true>(c, c.z.data(), 4 * n); break;
                    case Hard: shapeBlock<Hard, true>(c, c.z.data(), 4 * n); break;
                    default: shapeBlock<Fold, true>(c, c.z.data(), 4 * n); break;
                }
            } else {
                switch (mode_) {
                    case Tape: shapeBlock<Tape, false>(c, c.z.data(), 4 * n); break;
                    case Tube: shapeBlock<Tube, false>(c, c.z.data(), 4 * n); break;
                    case Hard: shapeBlock<Hard, false>(c, c.z.data(), 4 * n); break;
                    default: shapeBlock<Fold, false>(c, c.z.data(), 4 * n); break;
                }
            }
        }
        prevShape_ = shapes_[static_cast<std::size_t>(n - 1)];
        for (int j = 0; j < n; ++j) {
            D2 w[4];
            for (int i = 0; i < 4; ++i) w[i] = droopEq(k.eq1, k.eq2, d2(zl[4 * j + i], zr[4 * j + i]));
            const D2 h0 = k.dn2.down(hb2_, w[0], w[1]);
            const D2 h1 = k.dn2.down(hb2_, w[2], w[3]);
            const D2 d = k.dn1.down(hb1_, h0, h1);
            ch_[0].wet[static_cast<std::size_t>(j)] = static_cast<float>(d[0]);
            ch_[1].wet[static_cast<std::size_t>(j)] = static_cast<float>(d[1]);
        }
        k.up1.flush(); k.up2.flush(); k.dn1.flush(); k.dn2.flush(); k.dn1Dry.flush(); k.dn2Dry.flush();
        for (D2* v : {&k.eq1, &k.eq2, &k.dryPrev, &k.dq1, &k.dq2}) flushD2(*v);
    }

    // First-order ADAA: y = (F(v) - F(v0)) / (v - v0), the mean of the curve over the segment
    // between consecutive inputs, in closed forms free of cancellation:
    //   tape/tube F = a^2 (s - 1), s = sqrt(1 + (v/a)^2)  ->  y = (v + v0) / (s + s0) on one side
    //   fold      F = 1 - cos v                         ->  y = sin(mid) * sin(h) / h
    template <int kMode, bool kInterp>
    void shapeBlock(Chan& c, float* z, int count) const noexcept {
        float v0 = c.adaaV, s0 = c.adaaS;
        for (int i = 0; i < count; ++i) {
            Shape sh = shapes_[static_cast<std::size_t>(i >> 2)];
            if constexpr (kInterp) {  // from the previous 1x sample's shape to this one's
                const int j = i >> 2;
                const Shape& a = j ? shapes_[static_cast<std::size_t>(j - 1)] : prevShape_;
                const float t = static_cast<float>((i & 3) + 1) * 0.25f;
                sh.d = a.d + t * (sh.d - a.d);
                sh.b = a.b + t * (sh.b - a.b);
                sh.c = a.c + t * (sh.c - a.c);
                sh.fb = a.fb + t * (sh.fb - a.fb);
            }
            const float v = sh.d * z[i] + sh.b;
            float y;
            if constexpr (kMode == Tape) {
                const float s = std::sqrt(1.0f + v * v);
                y = (v + v0) / (s + s0);
                s0 = s;
            } else if constexpr (kMode == Tube) {
                const float av = v >= 0.0f ? kTubePos : kTubeNeg;
                const float s = std::sqrt(1.0f + (v / av) * (v / av));
                if ((v >= 0.0f) == (v0 >= 0.0f)) y = (v + v0) / (s + s0);
                else y = (v * v / (s + 1.0f) - v0 * v0 / (s0 + 1.0f)) / (v - v0);  // F = v^2/(s+1)
                s0 = s;
            } else if constexpr (kMode == Hard) {
                if (std::fabs(v) <= 1.0f && std::fabs(v0) <= 1.0f) {
                    y = 0.5f * (v + v0);
                } else if (v >= 1.0f && v0 >= 1.0f) {
                    y = 1.0f;
                } else if (v <= -1.0f && v0 <= -1.0f) {
                    y = -1.0f;
                } else {
                    auto F = [](double x) { return std::fabs(x) <= 1.0 ? 0.5 * x * x : std::fabs(x) - 0.5; };
                    const double dv = static_cast<double>(v) - v0;
                    y = std::fabs(dv) > 1e-9 ? static_cast<float>((F(v) - F(v0)) / dv)
                                             : std::clamp(0.5f * (v + v0), -1.0f, 1.0f);
                }
            } else {
                const float h = 0.5f * (v - v0);
                const float sinc = std::fabs(h) < 1e-3f ? 1.0f - h * h * (1.0f / 6.0f) : std::sin(h) / h;
                y = std::sin(0.5f * (v + v0)) * sinc;
            }
            z[i] = sh.c * (y - sh.fb);
            v0 = v;
        }
        c.adaaV = v0;
        c.adaaS = s0;
    }

    double curve(double v) const noexcept {
        switch (mode_) {
            case Tape: return v / std::sqrt(1.0 + v * v);
            case Tube: {
                const double a = v >= 0.0 ? kTubePos : kTubeNeg;
                return v / std::sqrt(1.0 + (v / a) * (v / a));
            }
            case Hard: return std::clamp(v, -1.0, 1.0);
            default: return std::sin(v);
        }
    }
    float sqrtTerm(float v) const noexcept {
        const float a = mode_ == Tube ? (v >= 0.0f ? kTubePos : kTubeNeg) : 1.0f;
        return std::sqrt(1.0f + (v / a) * (v / a));
    }

    // Loudness compensation: scale so a -12 dBFS sine (typical track level) comes out with the
    // same RMS (DC removed) at any drive/bias; louder material is compressed, quieter lifted.
    void updateShape() noexcept {
        constexpr int kN = 48;
        constexpr double kAmp = 0.25;
        const double d = std::pow(10.0, driveG_.value() / 20.0);
        const double b = 0.5 * biasG_.value() + (mode_ == Tube ? kTubeBias : 0.0);
        const double fb = curve(b);
        double s1 = 0.0, s2 = 0.0;
        for (int k = 0; k < kN; ++k) {
            const double y = curve(d * kAmp * sineTable_[static_cast<std::size_t>(k)] + b) - fb;
            s1 += y;
            s2 += y * y;
        }
        const double rms = std::sqrt(std::max(0.0, s2 / kN - (s1 / kN) * (s1 / kN)));
        const double c = std::min(64.0, kAmp * 0.70710678118654752 / std::max(rms, 1e-9));
        shape_ = {static_cast<float>(d), static_cast<float>(b), static_cast<float>(c), static_cast<float>(fb)};
    }
    void updateTone() noexcept {
        const double t = toneG_.value();
        tiltLow_ = std::pow(10.0, -t / 40.0);
        tiltHigh_ = std::pow(10.0, t / 40.0);
    }

    static constexpr float kTubePos = 0.85f, kTubeNeg = 1.6f, kTubeBias = 0.18f;

    int mode_{Tape};
    int maxBlock_{kMaxBlock};
    HalfBand<kN1>::Coefs hb1_{};
    HalfBand<kN2>::Coefs hb2_{};
    Chan ch_[2];
    Chain chain_;
    std::vector<Shape> shapes_;
    Shape shape_{}, prevShape_{};
    std::array<double, 48> sineTable_{};
    Glide driveG_, biasG_, toneG_, outG_, mixG_;
    double dcR_{0.999}, tiltA_{0.1}, tiltLow_{1.0}, tiltHigh_{1.0};
};

// =============================================================================================
// limiter: true-peak-aware lookahead brickwall. Detection on a 4x interpolated signal (96-tap
// Kaiser sinc per phase) with parabolic peak refinement; the gain is a sliding minimum over the
// lookahead window, a log-domain release, then two cascaded moving averages (smooth S-shaped
// attack). The window lengths guarantee gain <= required gain at every sample; a final clamp
// covers float rounding. Latency = lookahead + 48 samples of interpolator delay.
// =============================================================================================

class Limiter final : public FxBase {
    enum { Ceiling, Gain, Release, Lookahead, kCount };
    static constexpr int kTaps = 96;  // interpolator taps per fractional phase (multiple of 8)
    static constexpr int kDetDelay = kTaps / 2;

    static std::vector<ParamSpec> specs() {
        return {
            num("ceiling", -12, 0, -1, "dBFS", "Maximum output level (true-peak aware); -1 is safe for streaming/mp3.", false),
            num("gain", -12, 24, 0, "dB", "Input drive into the limiter: raise to make the master louder (3-8 dB typical)."),
            num("release", 1, 1000, 80, "ms", "Gain recovery time: 30-80 loud and punchy, 150-500 smooth and transparent."),
            num("lookahead", 1, 10, 5, "ms",
                "Look-ahead window (latency = lookahead + 48 samples, compensated by the engine on the master); longer = cleaner transients.",
                false),
        };
    }

    // Monotonic-deque sliding minimum over the last `window` pushes (power-of-two ring).
    class SlidingMin {
    public:
        void init(int window) {
            window_ = window;
            std::size_t cap = 4;
            while (cap < static_cast<std::size_t>(window) + 2) cap <<= 1;
            mask_ = cap - 1;
            val_.assign(cap, 1.0f);
            idx_.assign(cap, 0);
            head_ = tail_ = 0;
        }
        float push(std::int64_t n, float v) noexcept {
            while (tail_ != head_ && val_[(tail_ - 1) & mask_] >= v) --tail_;
            val_[tail_ & mask_] = v;
            idx_[tail_ & mask_] = n;
            ++tail_;
            while (idx_[head_ & mask_] <= n - window_) ++head_;
            return val_[head_ & mask_];
        }

    private:
        std::vector<float> val_;
        std::vector<std::int64_t> idx_;
        std::size_t mask_{3}, head_{0}, tail_{0};
        std::int64_t window_{1};
    };

    // Moving average with an exact running sum (recomputed once per cycle to cancel drift).
    class Box {
    public:
        void init(int len) {
            len_ = std::max(1, len);
            buf_.assign(static_cast<std::size_t>(len_), 1.0);
            pos_ = 0;
            sum_ = len_;
        }
        double push(double v) noexcept {
            sum_ += v - buf_[static_cast<std::size_t>(pos_)];
            buf_[static_cast<std::size_t>(pos_)] = v;
            if (++pos_ == len_) {
                pos_ = 0;
                double s = 0.0;
                for (double b : buf_) s += b;
                sum_ = s;
            }
            return sum_ / len_;
        }

    private:
        std::vector<double> buf_;
        int len_{1}, pos_{0};
        double sum_{1.0};
    };

public:
    Limiter() : FxBase("limiter", specs(), kCount) {}

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        maxBlock_ = std::max(1, ctx.maxBlock);
        ceil_ = dbToLin(p(Ceiling));
        const int span = std::max(4, static_cast<int>(std::lround(p(Lookahead) * 0.001 * fs_)));  // attack ramp
        latency_ = span + kDetDelay;
        const int len1 = (span + 1) / 2, len2 = span + 1 - len1;
        box1_.init(len1);
        box2_.init(len2);
        minWin_.init(span + 2);
        winMax_.init(kTaps);
        for (int ch = 0; ch < 2; ++ch) {
            hist_[ch].init(kTaps - 1, maxBlock_);
            delay_[ch].init(latency_);
            prev75_[ch] = 0.0f;
            interpOut_[ch].assign(static_cast<std::size_t>(maxBlock_), {0.0f, 0.0f, 0.0f});
        }
        active_.assign(static_cast<std::size_t>(maxBlock_), 0);
        quietBound_ = 1.0f;
        for (int ph = 0; ph < 3; ++ph) {  // fractional positions 0.25, 0.5, 0.75 between x[m] and x[m+1]
            const double t = 0.25 * (ph + 1);
            double sum = 0.0, l1 = 0.0;
            std::array<double, kTaps> h{};
            for (int k = 0; k < kTaps; ++k) {  // chronological tap k holds x[m - kDetDelay + 1 + k]
                const double d = t + kDetDelay - 1 - k;  // distance from that sample to the point
                h[static_cast<std::size_t>(k)] = std::sin(kPi * d) / (kPi * d) * kaiser(d / kDetDelay, 10.0);
                sum += h[static_cast<std::size_t>(k)];
            }
            for (int k = 0; k < kTaps; ++k) {
                interp_[ph][static_cast<std::size_t>(k)] = static_cast<float>(h[static_cast<std::size_t>(k)] / sum);
                l1 += std::fabs(h[static_cast<std::size_t>(k)] / sum);
            }
            quietBound_ = std::max(quietBound_, static_cast<float>(l1 * 1.01));
        }
        gainG_.prepare(fs_, kGainTau, dbToLin(p(Gain)), 1e-7f);
        relCoeff_ = onePoleCoeff(fs_, p(Release) * 0.001);
        relDb_ = 0.0f;
        step_ = 0;
        markSeen();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (paramsChanged()) {
            gainG_.setTarget(dbToLin(p(Gain)));
            relCoeff_ = onePoleCoeff(fs_, p(Release) * 0.001);
        }
        for (int off = 0; off < frames; off += maxBlock_) {
            const int n = std::min(maxBlock_, frames - off);
            float* io[2] = {left + off, right + off};
            // 1) drive, sanitise, and flag where true-peak interpolation is needed: no interpolated
            //    point can exceed (L1 norm of the interpolator) * (window max).
            for (int j = 0; j < n; ++j) {
                const float gin = gainG_.next();
                float mx = 0.0f;
                for (int ch = 0; ch < 2; ++ch) {
                    float x = io[ch][j] * gin;
                    if (!std::isfinite(x)) x = 0.0f;
                    hist_[ch].block()[j] = x;
                    mx = std::max(mx, std::fabs(x));
                }
                const float winMax = -winMax_.push(step_ + j, -mx);
                active_[static_cast<std::size_t>(j)] = winMax * quietBound_ > ceil_;
            }
            // 2) 4x interpolation (independent SIMD dot products).
            for (int ch = 0; ch < 2; ++ch) {
                const float* H = hist_[ch].data();
                for (int j = 0; j < n; ++j) {
                    if (!active_[static_cast<std::size_t>(j)]) continue;
                    dot3(interp_[0].data(), interp_[1].data(), interp_[2].data(), H + j, kTaps,
                         interpOut_[ch][static_cast<std::size_t>(j)].data());
                }
            }
            // 3) gain computer and output.
            for (int j = 0; j < n; ++j, ++step_) {
                float peak = 0.0f;
                if (active_[static_cast<std::size_t>(j)]) {
                    for (int ch = 0; ch < 2; ++ch) peak = std::max(peak, intervalPeak(ch, j));
                } else {
                    prev75_[0] = prev75_[1] = 0.0f;
                }
                const float need = peak > ceil_ ? ceil_ / peak : 1.0f;
                const float h = minWin_.push(step_, need);
                float r = 1.0f;
                if (h < 1.0f || relDb_ < 0.0f) {
                    const float hDb = h < 1.0f ? linToDb(h) : 0.0f;
                    if (hDb <= relDb_) {
                        relDb_ = hDb;
                    } else {
                        relDb_ = std::min(hDb, hDb + (relDb_ - hDb) * relCoeff_);
                        if (hDb == 0.0f && relDb_ > -1e-4f) relDb_ = 0.0f;
                    }
                    r = std::min(h, dbToLin(relDb_));
                }
                const float g = static_cast<float>(box2_.push(box1_.push(r)));
                for (int ch = 0; ch < 2; ++ch) {
                    const float delayed = delay_[ch].pushPop(hist_[ch].block()[j]);
                    io[ch][j] = std::clamp(delayed * g, -ceil_, ceil_);
                }
            }
            hist_[0].advance(n);
            hist_[1].advance(n);
        }
    }

    int latencySamples() const override { return latency_; }
    double tailSeconds() const override { return latency_ / fs_; }

private:
    // Peak estimate around x[m] (m = current step - kDetDelay) from the 4x points
    // {prev 0.75, x[m], 0.25, 0.5, 0.75, x[m+1]} with parabolic refinement of the maximum.
    float intervalPeak(int ch, int j) noexcept {
        const float* H = hist_[ch].data() + j;  // H[k] = x[step - kTaps + 1 + k]
        const std::size_t js = static_cast<std::size_t>(j);
        float pts[6];
        pts[0] = prev75_[ch];
        pts[1] = H[kDetDelay - 1];
        pts[2] = interpOut_[ch][js][0];
        pts[3] = interpOut_[ch][js][1];
        pts[4] = interpOut_[ch][js][2];
        pts[5] = H[kDetDelay];
        prev75_[ch] = pts[4];
        int k = 0;
        for (int i = 1; i < 6; ++i)
            if (std::fabs(pts[i]) > std::fabs(pts[k])) k = i;
        float best = std::fabs(pts[k]);
        if (k >= 1 && k <= 4) {
            const float s = pts[k] >= 0.0f ? 1.0f : -1.0f;
            const float ym = s * pts[k - 1], y0 = s * pts[k], yp = s * pts[k + 1];
            const float a = 0.5f * (yp + ym) - y0, b = 0.5f * (yp - ym);
            if (a < 0.0f) best = std::min(std::max(best, y0 - b * b / (4.0f * a)), 1.5f * best);
        }
        return best;
    }

    float ceil_{0.89125f};
    int latency_{288}, maxBlock_{kMaxBlock};
    BlockBuf hist_[2];
    DelayRing delay_[2];
    float prev75_[2]{};
    std::array<std::array<float, kTaps>, 3> interp_{};
    std::vector<std::array<float, 3>> interpOut_[2];  // 0.25, 0.5, 0.75 points per sample
    std::vector<char> active_;
    SlidingMin minWin_, winMax_;
    Box box1_, box2_;
    float quietBound_{1.0f};
    Glide gainG_;
    float relCoeff_{0.0f}, relDb_{0.0f};
    std::int64_t step_{0};
};

// =============================================================================================
// width: M/S width, Linkwitz-Riley mono-bass, balance
// =============================================================================================

class Width final : public FxBase {
    enum { WidthP, MonoBass, Balance, kCount };

    static std::vector<ParamSpec> specs() {
        return {
            num("width", 0, 2, 1, "", "Stereo width: 0 = mono, 1 = unchanged, 1.3-1.6 wide pads, 2 = side +6 dB."),
            num("monobass", 0, 500, 0, "Hz",
                "Content below this frequency is made mono (24 dB Linkwitz-Riley crossover, phase-coherent); 0 = off, 100-150 typical.",
                false),
            num("balance", -1, 1, 0, "", "Left/right balance: -1 = left only, 0 = centre (unity), 1 = right only."),
        };
    }

public:
    Width() : FxBase("width", specs(), kCount) {}

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        widthG_.prepare(fs_, kGainTau, p(WidthP), 1e-6f);
        balG_.prepare(fs_, kGainTau, p(Balance), 1e-6f);
        const double f = p(MonoBass);
        monoBass_ = f > 0.0;
        if (monoBass_) {
            const double fc = std::max(10.0, f);
            ap_ = svfDesign(SvfMode::AllPass, fs_, fc, 0.70710678118);
            hp_ = svfDesign(SvfMode::High, fs_, fc, 0.70710678118);
        }
        apM_.reset();
        hpS_[0].reset();
        hpS_[1].reset();
        markSeen();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (paramsChanged()) {
            widthG_.setTarget(p(WidthP));
            balG_.setTarget(p(Balance));
        }
        for (int i = 0; i < frames; ++i) {
            const float w = widthG_.next(), bal = balG_.next();
            float m = 0.5f * (left[i] + right[i]);
            float s = 0.5f * (left[i] - right[i]);
            if (monoBass_) {
                // LR4: LP4 + HP4 = 2nd-order allpass, so mid gets the allpass, side only the HP4.
                m = static_cast<float>(apM_.process(m, ap_));
                s = static_cast<float>(hpS_[1].process(hpS_[0].process(s, hp_), hp_));
            }
            s *= w;
            left[i] = (m + s) * std::min(1.0f, 1.0f - bal);
            right[i] = (m - s) * std::min(1.0f, 1.0f + bal);
        }
    }

private:
    Glide widthG_, balG_;
    bool monoBass_{false};
    SvfCoef ap_{}, hp_{};
    Svf apM_{}, hpS_[2]{};
};

// =============================================================================================
// bitcrush: sample-and-hold rate reduction + quantisation (lo-fi colour)
// =============================================================================================

class Bitcrush final : public FxBase {
    enum { Bits, Downsample, Mix, kCount };

    static std::vector<ParamSpec> specs() {
        return {
            num("bits", 1, 16, 8, "bits", "Quantisation depth (fractional allowed): 12 subtle grit, 8 retro sampler, 4 harsh, 1-2 broken."),
            num("downsample", 1, 64, 1, "x", "Sample-and-hold rate reduction (fractional allowed): 1 = off, 2-4 = 80s sampler aliasing, 16+ = destroyed."),
            num("mix", 0, 1, 1, "", "Dry/wet mix."),
        };
    }

public:
    Bitcrush() : FxBase("bitcrush", specs(), kCount) {}

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        mixG_.prepare(fs_, kGainTau, p(Mix), 1e-6f);
        qTo_ = qFrom_ = std::exp2(p(Bits) - 1.0f);
        xf_ = 1.0f;
        xfStep_ = static_cast<float>(1.0 / (kFadeSeconds * fs_));
        raw_[0] = raw_[1] = 0.0f;
        markSeen();
        factor_ = p(Downsample);
        phase_ = factor_ - 1.0f;  // latch on the very first sample
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (paramsChanged()) {
            mixG_.setTarget(p(Mix));
            factor_ = p(Downsample);
            // A new bit depth crossfades from the old quantiser (sweeping the depth through the noisier
            // depths in between would add a burst of grain). A change during a fade continues from the
            // depth heard at that moment.
            const float q = std::exp2(p(Bits) - 1.0f);
            if (q != qTo_) {
                if (xf_ < 1.0f) qFrom_ = std::exp2(std::log2(qFrom_) + fadeShape() * (std::log2(qTo_) - std::log2(qFrom_)));
                else qFrom_ = qTo_;
                qTo_ = q;
                xf_ = 0.0f;
            }
        }
        for (int i = 0; i < frames; ++i) {
            phase_ += 1.0f;
            if (phase_ >= factor_) {
                phase_ = std::fmod(phase_, factor_);
                raw_[0] = left[i];
                raw_[1] = right[i];
            }
            float yl = quantise(raw_[0], qTo_), yr = quantise(raw_[1], qTo_);
            if (xf_ < 1.0f) {
                xf_ = std::min(1.0f, xf_ + xfStep_);
                const float w = fadeShape();
                const float al = quantise(raw_[0], qFrom_), ar = quantise(raw_[1], qFrom_);
                yl = al + w * (yl - al);
                yr = ar + w * (yr - ar);
            }
            const float mix = mixG_.next();  // two-term form: exact at mix 0 and 1
            left[i] = yl * mix + left[i] * (1.0f - mix);
            right[i] = yr * mix + right[i] * (1.0f - mix);
        }
    }

private:
    static constexpr double kFadeSeconds = 0.004;
    static float quantise(float x, float q) noexcept { return std::round(x * q) / q; }
    float fadeShape() const noexcept { return 0.5f - 0.5f * std::cos(static_cast<float>(kPi) * xf_); }  // C1 ends

    Glide mixG_;
    float qFrom_{128.0f}, qTo_{128.0f}, xf_{1.0f}, xfStep_{0.005f}, factor_{1.0f}, phase_{0.0f};
    float raw_[2]{};  // latched (sample-and-hold) input
};

// =============================================================================================
// utility: gain, balance, polarity, mono
// =============================================================================================

class Utility final : public FxBase {
    enum { Gain, Pan, InvertL, InvertR, Mono, kCount };

    static std::vector<ParamSpec> specs() {
        return {
            num("gain", -96, 24, 0, "dB", "Gain; automate for trims and fades."),
            num("pan", -1, 1, 0, "", "Stereo balance: -1 = left only, 0 = unity, 1 = right only (constant-power taper)."),
            toggle("invertl", false, "Invert the left channel's polarity."),
            toggle("invertr", false, "Invert the right channel's polarity."),
            toggle("mono", false, "Sum to mono, (L+R)/2 on both sides."),
        };
    }

public:
    Utility() : FxBase("utility", specs(), kCount) {}

    void prepare(const RenderContext& ctx) override {
        fs_ = ctx.sampleRate;
        gainG_.prepare(fs_, kGainTau, dbToLin(p(Gain)), 1e-7f);
        panG_.prepare(fs_, kGainTau, p(Pan), 1e-6f);
        polL_.prepare(fs_, kGainTau, pc(InvertL) ? -1.0f : 1.0f, 1e-6f);
        polR_.prepare(fs_, kGainTau, pc(InvertR) ? -1.0f : 1.0f, 1e-6f);
        monoG_.prepare(fs_, kGainTau, static_cast<float>(pc(Mono)), 1e-6f);
        updatePan();
        markSeen();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (paramsChanged()) {
            gainG_.setTarget(dbToLin(p(Gain)));
            panG_.setTarget(p(Pan));
            polL_.setTarget(pc(InvertL) ? -1.0f : 1.0f);
            polR_.setTarget(pc(InvertR) ? -1.0f : 1.0f);
            monoG_.setTarget(static_cast<float>(pc(Mono)));
        }
        for (int i = 0; i < frames; ++i) {
            const float g = gainG_.next(), mono = monoG_.next();
            if (panG_.moving()) {
                panG_.next();
                updatePan();
            }
            float l = left[i] * polL_.next(), r = right[i] * polR_.next();
            const float m = 0.5f * (l + r);
            l += mono * (m - l);
            r += mono * (m - r);
            left[i] = l * panL_ * g;
            right[i] = r * panR_ * g;
        }
    }

private:
    void updatePan() noexcept {  // unity at centre, constant-power taper on the attenuated side
        const float pan = panG_.value();
        const float a = (pan + 1.0f) * 0.25f * static_cast<float>(kPi);
        panL_ = pan > 0.0f ? std::min(1.0f, 1.41421356f * std::cos(a)) : 1.0f;
        panR_ = pan < 0.0f ? std::min(1.0f, 1.41421356f * std::sin(a)) : 1.0f;
    }

    Glide gainG_, panG_, polL_, polR_, monoG_;
    float panL_{1.0f}, panR_{1.0f};
};

}  // namespace
}  // namespace dynfx

std::unique_ptr<Effect> createDynamicsEffect(std::string_view type) {
    using namespace dynfx;
    if (type == "eq") return std::make_unique<Eq>();
    if (type == "filter") return std::make_unique<Filter>();
    if (type == "compressor") return std::make_unique<Compressor>();
    if (type == "ducker") return std::make_unique<Ducker>();
    if (type == "saturator") return std::make_unique<Saturator>();
    if (type == "limiter") return std::make_unique<Limiter>();
    if (type == "width") return std::make_unique<Width>();
    if (type == "bitcrush") return std::make_unique<Bitcrush>();
    if (type == "utility") return std::make_unique<Utility>();
    return nullptr;
}

std::vector<std::string> dynamicsEffectTypes() {
    return {"eq", "filter", "compressor", "ducker", "saturator", "limiter", "width", "bitcrush", "utility"};
}

bool dynamicsEffectAcceptsSidechain(std::string_view type) { return type == "compressor" || type == "ducker"; }

}  // namespace as
