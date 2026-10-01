#pragma once

// Small shared DSP building blocks. Header-only, allocation-free after init.
// Modules should use these instead of re-implementing them.

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace as::dsp {

inline constexpr double kPi = 3.14159265358979323846;
inline constexpr double kTwoPi = 2.0 * kPi;

inline float dbToGain(float db) noexcept { return std::pow(10.0f, db * 0.05f); }
inline float gainToDb(float g) noexcept { return 20.0f * std::log10(std::max(g, 1e-12f)); }
inline double midiToHz(double note) noexcept { return 440.0 * std::pow(2.0, (note - 69.0) / 12.0); }

// Flush tiny values to zero (avoid denormal slowdowns in feedback paths).
inline float flush(float x) noexcept { return std::fabs(x) < 1e-20f ? 0.0f : x; }

// Equal-power pan, pan in -1..1 → (gainL, gainR); centre = -3 dB each.
inline void panGains(float pan, float& gl, float& gr) noexcept {
    const float a = (std::clamp(pan, -1.0f, 1.0f) + 1.0f) * 0.25f * static_cast<float>(kPi);
    gl = std::cos(a);
    gr = std::sin(a);
}

// Soft saturators.
inline float softClip(float x) noexcept {  // cubic, unity slope at 0, saturates at |x| >= 1.5
    if (x > 1.5f) return 1.0f;
    if (x < -1.5f) return -1.0f;
    return x - (4.0f / 27.0f) * x * x * x;
}
inline float fastTanh(float x) noexcept {  // Padé approximant, accurate to ~1e-3 on |x|<3
    x = std::clamp(x, -3.0f, 3.0f);
    const float x2 = x * x;
    return x * (27.0f + x2) / (27.0f + 9.0f * x2);
}

// Deterministic RNG (xorshift64*). Seed with RenderContext::seed ^ hash(module id).
class Rng {
public:
    explicit Rng(std::uint64_t seed = 0x9E3779B97F4A7C15ull) noexcept { reseed(seed); }
    void reseed(std::uint64_t seed) noexcept { state_ = seed ? seed : 0x9E3779B97F4A7C15ull; }
    std::uint64_t next() noexcept {
        state_ ^= state_ >> 12;
        state_ ^= state_ << 25;
        state_ ^= state_ >> 27;
        return state_ * 2685821657736338717ull;
    }
    float uniform() noexcept { return static_cast<float>((next() >> 40) * (1.0 / 16777216.0)); }  // [0,1)
    float bipolar() noexcept { return uniform() * 2.0f - 1.0f; }                                   // [-1,1)
private:
    std::uint64_t state_{};
};

inline std::uint64_t hashString(const char* s) noexcept {  // FNV-1a
    std::uint64_t h = 1469598103934665603ull;
    while (*s) { h ^= static_cast<unsigned char>(*s++); h *= 1099511628211ull; }
    return h;
}

// One-pole parameter smoother (exponential approach), time constant in seconds.
class Smoother {
public:
    void prepare(double sampleRate, double seconds, float initial) noexcept {
        coeff_ = seconds <= 0.0 ? 0.0f : static_cast<float>(std::exp(-1.0 / (seconds * sampleRate)));
        value_ = target_ = initial;
    }
    void setTarget(float t) noexcept { target_ = t; }
    void snap(float v) noexcept { value_ = target_ = v; }
    float next() noexcept { value_ = target_ + (value_ - target_) * coeff_; return value_; }
    float value() const noexcept { return value_; }
    float target() const noexcept { return target_; }
private:
    float coeff_{0.0f}, value_{0.0f}, target_{0.0f};
};

// RBJ-cookbook biquad, transposed direct form II, single channel.
class Biquad {
public:
    enum class Type { LowPass, HighPass, BandPass, Notch, Peak, LowShelf, HighShelf, AllPass };

    void set(Type type, double sampleRate, double freq, double q, double gainDb = 0.0) noexcept {
        freq = std::clamp(freq, 1.0, sampleRate * 0.49);
        q = std::max(q, 1e-3);
        const double A = std::pow(10.0, gainDb / 40.0);
        const double w0 = kTwoPi * freq / sampleRate;
        const double cw = std::cos(w0), sw = std::sin(w0);
        const double alpha = sw / (2.0 * q);
        double b0 = 1, b1 = 0, b2 = 0, a0 = 1, a1 = 0, a2 = 0;
        switch (type) {
            case Type::LowPass:  b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = (1 - cw) / 2; a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha; break;
            case Type::HighPass: b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = (1 + cw) / 2; a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha; break;
            case Type::BandPass: b0 = alpha; b1 = 0; b2 = -alpha; a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha; break;
            case Type::Notch:    b0 = 1; b1 = -2 * cw; b2 = 1; a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha; break;
            case Type::AllPass:  b0 = 1 - alpha; b1 = -2 * cw; b2 = 1 + alpha; a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha; break;
            case Type::Peak:     b0 = 1 + alpha * A; b1 = -2 * cw; b2 = 1 - alpha * A; a0 = 1 + alpha / A; a1 = -2 * cw; a2 = 1 - alpha / A; break;
            case Type::LowShelf: {
                const double s = 2 * std::sqrt(A) * alpha;
                b0 = A * ((A + 1) - (A - 1) * cw + s); b1 = 2 * A * ((A - 1) - (A + 1) * cw); b2 = A * ((A + 1) - (A - 1) * cw - s);
                a0 = (A + 1) + (A - 1) * cw + s; a1 = -2 * ((A - 1) + (A + 1) * cw); a2 = (A + 1) + (A - 1) * cw - s; break;
            }
            case Type::HighShelf: {
                const double s = 2 * std::sqrt(A) * alpha;
                b0 = A * ((A + 1) + (A - 1) * cw + s); b1 = -2 * A * ((A - 1) + (A + 1) * cw); b2 = A * ((A + 1) + (A - 1) * cw - s);
                a0 = (A + 1) - (A - 1) * cw + s; a1 = 2 * ((A - 1) - (A + 1) * cw); a2 = (A + 1) - (A - 1) * cw - s; break;
            }
        }
        b0_ = static_cast<float>(b0 / a0); b1_ = static_cast<float>(b1 / a0); b2_ = static_cast<float>(b2 / a0);
        a1_ = static_cast<float>(a1 / a0); a2_ = static_cast<float>(a2 / a0);
    }
    float process(float x) noexcept {
        const float y = b0_ * x + z1_;
        z1_ = flush(b1_ * x - a1_ * y + z2_);
        z2_ = flush(b2_ * x - a2_ * y);
        return y;
    }
    void reset() noexcept { z1_ = z2_ = 0.0f; }
private:
    float b0_{1}, b1_{0}, b2_{0}, a1_{0}, a2_{0};
    float z1_{0}, z2_{0};
};

// One-pole low/high pass (6 dB/oct), cheap damping filter.
class OnePole {
public:
    void setLowPass(double sampleRate, double freq) noexcept {
        a_ = static_cast<float>(std::exp(-kTwoPi * std::clamp(freq, 1.0, sampleRate * 0.49) / sampleRate));
    }
    float lowPass(float x) noexcept { z_ = flush(x + (z_ - x) * a_); return z_; }
    float highPass(float x) noexcept { return x - lowPass(x); }
    void reset() noexcept { z_ = 0.0f; }
private:
    float a_{0.0f}, z_{0.0f};
};

// Circular delay line with fractional (cubic Hermite) read. Size fixed at init.
class DelayLine {
public:
    void init(int maxSamples) { buf_.assign(static_cast<std::size_t>(std::max(4, maxSamples + 4)), 0.0f); w_ = 0; }
    void reset() noexcept { std::fill(buf_.begin(), buf_.end(), 0.0f); w_ = 0; }
    void push(float x) noexcept { buf_[w_] = x; w_ = (w_ + 1) % buf_.size(); }
    // delay in samples, >= 1 (1 = the most recently pushed sample).
    float read(float delay) const noexcept {
        const int n = static_cast<int>(buf_.size());
        delay = std::clamp(delay, 1.0f, static_cast<float>(n - 3));
        const int d = static_cast<int>(delay);
        const float f = delay - static_cast<float>(d);
        auto at = [&](int k) { int i = static_cast<int>(w_) - k; while (i < 0) i += n; return buf_[static_cast<std::size_t>(i)]; };
        const float xm1 = at(d - 1 < 1 ? 1 : d - 1), x0 = at(d), x1 = at(d + 1), x2 = at(d + 2);
        const float c1 = 0.5f * (x1 - xm1);
        const float c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2;
        const float c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
        return ((c3 * f + c2) * f + c1) * f + x0;
    }
    float readInt(int delay) const noexcept {
        const int n = static_cast<int>(buf_.size());
        int i = static_cast<int>(w_) - std::clamp(delay, 1, n - 1);
        if (i < 0) i += n;
        return buf_[static_cast<std::size_t>(i)];
    }
    int capacity() const noexcept { return static_cast<int>(buf_.size()) - 4; }
private:
    std::vector<float> buf_;
    std::size_t w_{0};
};

// Linear ADSR, times in seconds, sustain 0..1. Exponential-ish release via curve.
class Adsr {
public:
    void prepare(double sampleRate) noexcept { sr_ = sampleRate; }
    void set(float a, float d, float s, float r) noexcept { a_ = a; d_ = d; s_ = std::clamp(s, 0.0f, 1.0f); r_ = r; }
    void gate(bool on) noexcept {
        if (on) { stage_ = Stage::Attack; }
        else if (stage_ != Stage::Idle) { stage_ = Stage::Release; releaseFrom_ = level_; }
    }
    void kill() noexcept { stage_ = Stage::Idle; level_ = 0.0f; }
    float next() noexcept {
        switch (stage_) {
            case Stage::Idle: level_ = 0.0f; break;
            case Stage::Attack:
                level_ += a_ <= 0.0f ? 1.0f : static_cast<float>(1.0 / (a_ * sr_));
                if (level_ >= 1.0f) { level_ = 1.0f; stage_ = Stage::Decay; }
                break;
            case Stage::Decay: {
                // exponential decay towards sustain, ~-60 dB in d_ seconds
                const float k = d_ <= 0.0f ? 1.0f : static_cast<float>(1.0 - std::exp(-6.9 / (d_ * sr_)));
                level_ += (s_ - level_) * k;
                if (std::fabs(level_ - s_) < 1e-4f) { level_ = s_; stage_ = Stage::Sustain; }
                break;
            }
            case Stage::Sustain: level_ = s_; break;
            case Stage::Release: {
                const float k = r_ <= 0.0f ? 1.0f : static_cast<float>(1.0 - std::exp(-6.9 / (r_ * sr_)));
                level_ -= level_ * k;
                if (level_ < 1e-5f) { level_ = 0.0f; stage_ = Stage::Idle; }
                break;
            }
        }
        return level_;
    }
    bool idle() const noexcept { return stage_ == Stage::Idle; }
    bool released() const noexcept { return stage_ == Stage::Release || stage_ == Stage::Idle; }
    float level() const noexcept { return level_; }
private:
    enum class Stage { Idle, Attack, Decay, Sustain, Release };
    double sr_{48000.0};
    float a_{0.01f}, d_{0.1f}, s_{1.0f}, r_{0.1f};
    float level_{0.0f}, releaseFrom_{0.0f};
    Stage stage_{Stage::Idle};
};

// PolyBLEP residual for band-limited saw/pulse. t = phase in [0,1), dt = phase increment.
inline float polyBlep(float t, float dt) noexcept {
    if (t < dt) { t /= dt; return t + t - t * t - 1.0f; }
    if (t > 1.0f - dt) { t = (t - 1.0f) / dt; return t * t + t + t + 1.0f; }
    return 0.0f;
}

}  // namespace as::dsp
