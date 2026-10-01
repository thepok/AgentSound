#pragma once

// Internal helpers shared by the time-based / modulation effects (TimeFx*.cpp). Not a public API.

#include "core/Module.h"
#include "core/TempoMap.h"
#include "dsp/Dsp.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace as::timefx {

inline constexpr int kCtrl = 32;  // control-rate sub-block for coefficient updates (samples)

// Power-of-two ring buffer. Taps are addressed relative to the NEXT write:
// called before write(x[n]), tap(d) returns x[n-d] for d >= 1.
class RingDelay {
public:
    void init(int maxDelay) {
        std::size_t n = 16;
        while (n < static_cast<std::size_t>(std::max(maxDelay, 1)) + 8) n <<= 1;
        buf_.assign(n, 0.0f);
        mask_ = static_cast<std::uint32_t>(n - 1);
        w_ = 0;
        maxCubic_ = static_cast<double>(n - 4);
    }
    void clear() noexcept { std::fill(buf_.begin(), buf_.end(), 0.0f); w_ = 0; }
    void write(float x) noexcept { buf_[w_] = x; w_ = (w_ + 1) & mask_; }
    // Block write (n <= capacity), split into at most two contiguous copies.
    void write(const float* x, int n) noexcept {
        const std::uint32_t un = static_cast<std::uint32_t>(n);
        const std::uint32_t first = std::min(un, mask_ + 1 - w_);
        std::copy(x, x + first, buf_.data() + w_);
        std::copy(x + first, x + un, buf_.data());
        w_ = (w_ + un) & mask_;
    }
    float tap(int d) const noexcept { return buf_[(w_ - static_cast<std::uint32_t>(d)) & mask_]; }
    // out[k] (+)= g * tap(d - k) for k in [0, n): n consecutive samples, oldest first.
    template <bool Accumulate>
    void read(int d, float g, float* out, int n) const noexcept {
        const std::uint32_t start = (w_ - static_cast<std::uint32_t>(d)) & mask_;
        const int first = static_cast<int>(std::min(static_cast<std::uint32_t>(n), mask_ + 1 - start));
        const float* a = buf_.data() + start;
        const float* b = buf_.data();
        float* o2 = out + first;
        for (int k = 0; k < first; ++k) out[k] = Accumulate ? out[k] + g * a[k] : g * a[k];
        for (int k = 0; k < n - first; ++k) o2[k] = Accumulate ? o2[k] + g * b[k] : g * b[k];
    }
    // Fractional tap, 4-point cubic Hermite (Catmull-Rom); d is clamped to [2, capacity].
    float tapCubic(double d) const noexcept {
        d = std::clamp(d, 2.0, maxCubic_);
        const int i = static_cast<int>(d);
        const float f = static_cast<float>(d - i);
        const float xm1 = tap(i - 1), x0 = tap(i), x1 = tap(i + 1), x2 = tap(i + 2);
        const float c1 = 0.5f * (x1 - xm1);
        const float c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2;
        const float c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
        return ((c3 * f + c2) * f + c1) * f + x0;
    }
    double capacity() const noexcept { return maxCubic_; }
    // Raw access for hot loops.
    const float* data() const noexcept { return buf_.data(); }
    std::uint32_t mask() const noexcept { return mask_; }
    std::uint32_t writeIndex() const noexcept { return w_; }

private:
    std::vector<float> buf_;
    std::uint32_t mask_{0}, w_{0};
    double maxCubic_{2.0};
};

// sin(2*pi*phase), phase in cycles. Odd Taylor polynomial on a folded range; |error| < 4e-6.
inline float sinCycles(double phase) noexcept {
    float x = static_cast<float>(phase - std::floor(phase));  // [0,1)
    if (x >= 0.5f) x -= 1.0f;                                 // [-0.5,0.5)
    float y = 2.0f * x;                                       // sin(pi*y), y in [-1,1)
    if (y > 0.5f) y = 1.0f - y;
    else if (y < -0.5f) y = -1.0f - y;
    const float y2 = y * y;
    return y * (3.14159265f + y2 * (-5.16771278f + y2 * (2.55016404f + y2 * (-0.59926453f + y2 * 0.08214589f))));
}
inline float cosCycles(double phase) noexcept { return sinCycles(phase + 0.25); }

// Bipolar triangle in phase with sinCycles: 0 at 0, +1 at 0.25, -1 at 0.75.
inline float triCycles(double phase) noexcept {
    const float x = static_cast<float>(phase - std::floor(phase));
    return x < 0.25f ? 4.0f * x : (x < 0.75f ? 2.0f - 4.0f * x : 4.0f * x - 4.0f);
}

inline double wrap01(double p) noexcept { return p - std::floor(p); }

// Normalised fast Walsh-Hadamard transform (orthogonal, self-inverse) applied across N channels
// for each of the first n samples of a channel-major block. N must be a power of two.
template <int N, int B>
inline void hadamardBlock(float (&x)[N][B], int n) noexcept {
    for (int h = 1; h < N; h *= 2)
        for (int i = 0; i < N; i += 2 * h)
            for (int j = i; j < i + h; ++j) {
                float* a = x[j];
                float* b = x[j + h];
                for (int k = 0; k < n; ++k) {
                    const float p = a[k], q = b[k];
                    a[k] = p + q;
                    b[k] = p - q;
                }
            }
    const float s = 1.0f / std::sqrt(static_cast<float>(N));
    for (int i = 0; i < N; ++i)
        for (int k = 0; k < n; ++k) x[i][k] *= s;
}

// Splits a host block into sub-blocks aligned to an absolute kCtrl grid, so control-rate updates
// (and therefore the output) do not depend on the host's block sizes.
// fn(offset, length, atGridStart) is called for each sub-block.
template <class Fn>
inline void forEachCtrlBlock(std::uint64_t& pos, int frames, Fn&& fn) {
    int n = 0;
    while (n < frames) {
        const int phase = static_cast<int>(pos % kCtrl);
        const int len = std::min(frames - n, kCtrl - phase);
        fn(n, len, phase == 0);
        n += len;
        pos += static_cast<std::uint64_t>(len);
    }
}

// Linear up to |x| = 0.6, then a tanh-shaped knee towards +-1.2. C1-continuous.
// Used inside feedback loops: transparent at normal levels, bounds runaway feedback.
inline float softSat(float x) noexcept {
    constexpr float knee = 0.6f, room = 0.6f;
    const float a = std::fabs(x);
    if (a <= knee) return x;
    const float y = knee + room * dsp::fastTanh((a - knee) / room);
    return x < 0.0f ? -y : y;
}

// Equal-power dry/wet gains (for effects whose wet signal is largely decorrelated: delay, reverb).
// Exact 0/1 at the ends (mix 1 = no dry leak on send buses).
inline void equalPowerMix(float mix, float& dry, float& wet) noexcept {
    const double a = std::clamp(mix, 0.0f, 1.0f) * 0.5 * dsp::kPi;
    dry = mix >= 1.0f ? 0.0f : static_cast<float>(std::cos(a));
    wet = mix <= 0.0f ? 0.0f : static_cast<float>(std::sin(a));
}

// Linear crossfade rescaled to constant power for uncorrelated dry/wet: dry and wet stay equal at
// 0.5 (deepest comb/phase notches) while the broadband level stays put (flanger, phaser).
inline void notchMix(float mix, float& dry, float& wet) noexcept {
    const float m = std::clamp(mix, 0.0f, 1.0f);
    const float c = 1.0f / std::sqrt((1.0f - m) * (1.0f - m) + m * m);
    dry = (1.0f - m) * c;
    wet = m * c;
}

inline double beatsToSeconds(double beats, double bpm) noexcept { return beats * 60.0 / std::max(bpm, 1.0); }

// Phase (cycles, [0,1)) of a tempo-synced LFO whose period is `beats`, at song beat `beat`: cycles start
// on every multiple of `beats` counted from song beat 0, so a preview render that starts mid-song is
// phase-identical to the same span of a full render.
inline double gridPhase(double beat, double beats) noexcept { return wrap01(beat / std::max(beats, 1e-6)); }

// Two cascaded one-pole smoothers in single precision for gains, mixes and filter settings: the
// glide is C1-continuous (no kink where a change starts, unlike a one-pole), so even fast
// automation steps stay free of high-frequency clicks. 10-90 % step response = 3.36 x tau; lands
// exactly on the target.
class Smooth2 {
public:
    void prepare(double sampleRate, double tauSeconds, float value) noexcept {
        c_ = tauSeconds <= 0.0 ? 0.0f : static_cast<float>(std::exp(-1.0 / (tauSeconds * sampleRate)));
        snap(value);
    }
    void snap(float v) noexcept { a_ = b_ = t_ = v; moving_ = false; }
    void setTarget(float t) noexcept {
        t_ = t;
        moving_ = a_ != t_ || b_ != t_;
    }
    float next() noexcept {
        if (moving_) {
            a_ = t_ + (a_ - t_) * c_;
            b_ = a_ + (b_ - a_) * c_;
            if (std::fabs(a_ - t_) + std::fabs(b_ - t_) <= 1e-7f * (1.0f + std::fabs(t_))) {
                a_ = b_ = t_;
                moving_ = false;
            }
        }
        return b_;
    }
    float value() const noexcept { return b_; }
    float target() const noexcept { return t_; }
    bool moving() const noexcept { return moving_; }

private:
    float c_{0.0f}, a_{0.0f}, b_{0.0f}, t_{0.0f};
    bool moving_{false};
};

// Two cascaded one-pole smoothers in double precision: C1-continuous glide without overshoot.
// Used for delay times so that time changes glide (tape-like) instead of clicking.
class Glide {
public:
    void prepare(double sampleRate, double tauSeconds, double value) noexcept {
        c_ = std::exp(-1.0 / (tauSeconds * sampleRate));
        snap(value);
    }
    void snap(double v) noexcept { a_ = b_ = t_ = v; }
    void setTarget(double t) noexcept { t_ = t; }
    double next() noexcept {
        a_ = t_ + (a_ - t_) * c_;
        b_ = a_ + (b_ - a_) * c_;
        if (std::fabs(a_ - t_) < 1e-9 && std::fabs(b_ - t_) < 1e-9) a_ = b_ = t_;  // settle exactly
        return b_;
    }
    double value() const noexcept { return b_; }
    double target() const noexcept { return t_; }
    // Moves the whole glide (state and target) by `delta`: an external drift (a tempo-synced delay time
    // following a tempo map) passes through at once while target changes keep gliding.
    void shift(double delta) noexcept { a_ += delta; b_ += delta; t_ += delta; }

private:
    double c_{0.0}, a_{0.0}, b_{0.0}, t_{0.0};
};

// 12 dB/oct Butterworth low- or high-pass as a linear TPT state-variable filter (A. Simper). Cutoff
// changes are interpolated per sample and never disturb the filter state, so even fast automation is
// transient-free (a direct-form biquad whose coefficients are swapped every control block thumps).
class TptFilter {
public:
    enum class Mode { Low, High };
    TptFilter(Mode mode = Mode::Low) noexcept : mode_(mode) {}  // NOLINT: implicit, for array initialisers
    void reset() noexcept { ic1_ = ic2_ = 0.0f; }
    // New cutoff, reached linearly over `samples` (0 = at once).
    void setCutoff(double sampleRate, double hz, int samples) noexcept {
        const float g = static_cast<float>(std::tan(dsp::kPi * std::clamp(hz, 5.0, 0.49 * sampleRate) / sampleRate));
        target_ = g;
        if (samples <= 0) {
            left_ = 0;
            setG(g);
        } else {
            left_ = samples;
            step_ = (g - g_) / static_cast<float>(samples);
        }
    }
    float process(float v0) noexcept {
        if (left_ > 0) setG(--left_ > 0 ? g_ + step_ : target_);
        const float v3 = v0 - ic2_;
        const float v1 = a1_ * ic1_ + a2_ * v3;
        const float v2 = ic2_ + a2_ * ic1_ + a3_ * v3;
        ic1_ = dsp::flush(2.0f * v1 - ic1_);
        ic2_ = dsp::flush(2.0f * v2 - ic2_);
        return mode_ == Mode::Low ? v2 : v0 - kK * v1 - v2;
    }

private:
    static constexpr float kK = 1.41421356f;  // 1/Q, Butterworth
    void setG(float g) noexcept {
        g_ = g;
        a1_ = 1.0f / (1.0f + g * (g + kK));
        a2_ = g * a1_;
        a3_ = g * a2_;
    }
    Mode mode_;
    float g_{0.0f}, target_{0.0f}, step_{0.0f}, a1_{1.0f}, a2_{0.0f}, a3_{0.0f}, ic1_{0.0f}, ic2_{0.0f};
    int left_{0};
};

// Control-rate exponential smoother for coefficient-type parameters (stepped once per sub-block).
struct CtrlSmooth {
    float v{0.0f}, t{0.0f};
    void snap(float x) noexcept { v = t = x; }
    // Returns true if the value moved (caller recomputes coefficients).
    bool step(float k) noexcept {
        if (v == t) return false;
        v += (t - v) * k;
        if (std::fabs(t - v) <= 1e-5f * std::max(std::fabs(t), 1e-3f)) v = t;
        return true;
    }
};
inline float ctrlCoeff(double sampleRate, int samples, double tauSeconds) noexcept {
    return static_cast<float>(1.0 - std::exp(-samples / (tauSeconds * sampleRate)));
}

// Smoothly interpolated random value in [-1,1] (cubic ease between random targets), for tape wow etc.
class SmoothNoise {
public:
    void reset(std::uint64_t seed) noexcept { rng_.reseed(seed); a_ = rng_.bipolar(); b_ = rng_.bipolar(); ph_ = 0.0; }
    // Fast-forwards by `cycles` (e.g. to the song position of a preview render).
    void skip(double cycles) noexcept {
        ph_ += std::max(0.0, cycles);
        while (ph_ >= 1.0) { ph_ -= 1.0; a_ = b_; b_ = rng_.bipolar(); }
    }
    float next(double inc) noexcept {
        ph_ += inc;
        if (ph_ >= 1.0) { ph_ -= std::floor(ph_); a_ = b_; b_ = rng_.bipolar(); }
        const float x = static_cast<float>(ph_);
        return a_ + (b_ - a_) * x * x * (3.0f - 2.0f * x);
    }

private:
    dsp::Rng rng_;
    float a_{0.0f}, b_{0.0f};
    double ph_{0.0};
};

// Common plumbing: strict ParamSpec-driven configure/automation, change detection.
class ParamEffect : public Effect {
public:
    ParamEffect(const std::vector<ParamSpec>& specs, const char* type) : params_(specs), type_(type) {}
    void configure(const json& params) override { params_.configure(params, type_); seen_ = ~0u; }
    // Songs whose tempo changes: the song position, beat grids and synced times follow the map.
    void setTempoMap(const TempoMap& map) override {
        tempo_ = &map;
        clock_.attach(&map);
    }
    bool setParam(std::string_view name, float value) override { return params_.set(name, value); }
    const std::vector<ParamSpec>& paramSpecs() const override { return params_.specs(); }

protected:
    // Strictness for count-type params declared as numbers (e.g. voices, stages).
    void requireInteger(const char* name) const {
        const float v = params_.get(name);
        if (v != std::round(v))
            throw ConfigError(std::string(type_) + ": '" + name + "' must be a whole number, got " + std::to_string(v));
    }
    float get(int i) const noexcept { return params_.get(i); }
    int getInt(int i) const noexcept { return static_cast<int>(std::lround(params_.get(i))); }
    bool on(int i) const noexcept { return params_.get(i) >= 0.5f; }
    // True once after every configure/setParam (cheap per-block check).
    bool changed() noexcept {
        const unsigned v = params_.version();
        if (v == seen_) return false;
        seen_ = v;
        return true;
    }

    // Sample rate, tempo and song position from the context. pos_ starts at the render's first song
    // sample, so control-rate grids (and everything derived from the song position) line up between
    // a preview render and the same span of a full render.
    void prepareClock(const RenderContext& ctx) noexcept {
        sr_ = ctx.sampleRate;
        bpm_ = ctx.bpm;
        // the renderer's own rounding of the start beat (RenderContext::startBeat) to a song sample
        startSample_ = static_cast<std::uint64_t>(songStartSample(ctx.startBeat, sr_, bpm_, tempo_));
        pos_ = startSample_;
    }
    double startSeconds() const noexcept { return static_cast<double>(startSample_) / sr_; }
    // Song beat of the sample at pos_ (from the integer song sample, so a preview and a full render
    // compute bit-identical grid phases; with a tempo map through the BeatClock's 32-sample grid).
    double songBeat() const noexcept { return songBeatAt(static_cast<std::int64_t>(pos_)); }
    double songBeatAt(std::int64_t sample) const noexcept {
        if (tempo_) return clock_.beatAt(sample);
        return static_cast<double>(sample) * std::max(bpm_, 1.0) / (60.0 * sr_);
    }
    // Tempo at pos_ (the constant song tempo without a tempo map).
    double songBpm() const noexcept { return tempo_ ? clock_.bpmAt(static_cast<std::int64_t>(pos_)) : bpm_; }
    // Slowest tempo of the song (buffer sizes for tempo-synced times).
    double slowestBpm() const noexcept { return tempo_ ? std::min(bpm_, tempo_->minBpm()) : bpm_; }
    // Samples spanned by the `beats` beats before song sample `sample` (without a tempo map: beats at the
    // song tempo). A tempo-synced echo / predelay of `beats` then lands `beats` later on the moving grid
    // (ramps: the read head drifts, tape-style). A tempo jump ("step": set_tempo, fermata, a tempo) inside
    // that window restarts the grid: the beats before the jump count at the new tempo, so the time changes
    // at once at the jump (the caller crossfades) instead of replaying the window at the jump's speed ratio
    // (a fermata at a quarter of the tempo would play every echo two octaves down).
    double lookbackSamples(double beats, std::int64_t sample) const noexcept {
        if (!tempo_) return beats * 60.0 / std::max(bpm_, 1.0) * sr_;
        const double b = clock_.beatAt(sample), b0 = b - beats;
        const double jump = tempo_->lastJumpIn(b0, b);
        if (std::isnan(jump)) return static_cast<double>(sample) - tempo_->sampleAt(b0);
        return std::max(0.0, static_cast<double>(sample) - tempo_->sampleAt(jump)) + (jump - b0) * 60.0 * sr_ / tempo_->bpmAt(jump);
    }
    // True when a tempo jump falls between song samples `from` and `to` (from < to): the synced times of
    // lookbackSamples change at once there.
    bool tempoJumpBetween(std::int64_t from, std::int64_t to) const noexcept {
        return tempo_ && tempo_->hasJumps() && !std::isnan(tempo_->lastJumpIn(clock_.beatAt(from), clock_.beatAt(to)));
    }

    Params params_;
    const char* type_;
    unsigned seen_{~0u};
    double sr_{48000.0};
    double bpm_{120.0};
    std::uint64_t startSample_{0};   // song sample of the first rendered sample
    std::uint64_t pos_{0};           // song sample being processed (absolute control grid)
    const TempoMap* tempo_{nullptr}; // set for songs whose tempo changes (setTempoMap)
    BeatClock clock_;
};

// Per-type factories (TimeFxMod.cpp, TimeFxDelay.cpp, TimeFxReverb.cpp, TimeFxEnsemble.cpp, FormantFx.cpp).
std::unique_ptr<Effect> makeChorus();
std::unique_ptr<Effect> makeEnsemble();
std::unique_ptr<Effect> makeVowel();
std::unique_ptr<Effect> makeFlanger();
std::unique_ptr<Effect> makePhaser();
std::unique_ptr<Effect> makeTremolo();
std::unique_ptr<Effect> makeWah();
std::unique_ptr<Effect> makeAmp();
std::unique_ptr<Effect> makeDelay();
std::unique_ptr<Effect> makeReverb();
std::unique_ptr<Effect> makeGatedReverb();

}  // namespace as::timefx
