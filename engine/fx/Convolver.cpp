// Convolution effect: input -> predelay (gliding, exact whole-sample taps when settled) -> zero-latency
// partitioned convolution with the prepared IR (ConvolverEngine) -> wet low-cut / high-cut (TPT, each
// cross-faded in from an exact bypass at its 'off' end) -> width (M/S) -> gain -> equal-power dry/wet.
//
// At the defaults (predelay 0, filters off, width 1, gain 0 dB, mix 1) the output is exactly the
// convolution, so a unit-impulse IR passes the input through bit for bit.

#include "fx/Convolver.h"

#include "fx/ConvolverEngine.h"
#include "fx/ConvolverIr.h"
#include "fx/TimeFxUtil.h"

namespace as {
namespace {

using namespace timefx;

enum Param { kIr, kMix, kGain, kPredelay, kLowCut, kHighCut, kWidth, kStart, kLength, kStretch, kNormalize, kReverse };

constexpr float kLowOff = 20.0f;      // lowcut at (or below) this: bypassed
constexpr float kHighOff = 20000.0f;  // highcut at (or above) this: bypassed
constexpr double kMaxPredelayMs = 500.0;
constexpr int kChunk = 256;           // internal block (host blocks are split to this size)

const std::vector<ParamSpec>& convolverSpecs() {
    static const std::vector<ParamSpec> s = {
        num("ir", 0, 0, 0, "path",
            "The impulse response - a path, not a number (required): a WAV relative to assets/ (\"samples/<pack>/...\") or "
            "absolute. 1 channel = the same IR on both sides, 2 = stereo (L->L, R->R), 4 = true stereo (LL, LR, RL, RR). "
            "A list of files is one IR from their channels in order: [left, right] mono files, [left-input, right-input] "
            "stereo files (true stereo, e.g. Bricasti .L/.R pairs) or 4 mono files LL, LR, RL, RR (e.g. Lexicon 224XL "
            "V1.1.L, V1.1.R, V1.2.L, V1.2.R). Any sample rate (resampled). Find IRs: python -m agentsound find ir; ready-made "
            "returns and cabinets: the patches bus/ir_* and cab/*.",
            false),
        num("mix", 0, 1, 1, "",
            "Dry/wet balance (equal power): 1 = wet only - return buses and cabinet IRs; 0.15-0.35 for a reverb IR as an insert"),
        num("gain", -40, 24, 0, "dB", "Level of the wet signal (after 'normalize')"),
        num("predelay", 0, kMaxPredelayMs, 0, "ms",
            "Delay before the IR (glides when automated); 10-40 ms keeps attacks clear of a hall. Adds to any silence at the "
            "start of the IR file (see 'start')"),
        num("lowcut", kLowOff, 2000, kLowOff, "Hz", "High-pass on the wet signal (12 dB/oct); 20 = off. 150-300 keeps a reverb out of the bass"),
        num("highcut", 1000, kHighOff, kHighOff, "Hz", "Low-pass on the wet signal (12 dB/oct); 20000 = off. Darkens bright rooms and plates"),
        num("width", 0, 2, 1, "", "Stereo width of the wet signal (mid/side): 0 = mono, 1 = as recorded, 2 = extra wide"),
        num("start", 0, 2000, 0, "ms",
            "Skips the head of the IR file: its silence before the direct sound, or the direct sound itself (the dry path "
            "already has it). File time (before 'stretch'); not automatable",
            false),
        num("length", 0, conv::kMaxIrSeconds, 0, "s",
            "Keeps at most this much of the IR after 'start' (a shorter tail, less CPU), faded out over its last quarter "
            "(<= 0.5 s); 0 = the whole IR (its tail once it has fallen 80 dB under its peak is always dropped). File time; not automatable",
            false),
        num("stretch", 0.5f, 2, 1, "x",
            "Resamples the IR: 2 = a room twice as large (twice as long, an octave darker), 0.5 = smaller and brighter; "
            "energy kept. Not automatable",
            false),
        choice("normalize", {"off", "on"}, 1,
               "on: the IR is scaled to unit energy (white noise comes out at its input level), so IRs from different packs "
               "sit at comparable levels; off: the file's own level (cabinet IRs made for unity gain). Not automatable"),
        choice("reverse", {"off", "on"}, 0,
               "on: plays the IR backwards (after start / length): a swell that ends where the note was - reverse reverb; "
               "set 'length' to the swell time. Not automatable"),
    };
    return s;
}

// Predelay glide: a critically damped approach (tau 50 ms, C1: no clicks) whose speed is capped at half a
// sample per sample, so a large jump never shifts the pitch of the wet signal by more than x0.5 .. x1.5
// (an uncapped glide over 500 ms races at ~3 samples per sample: the input two octaves up). Settles
// exactly on the (whole-sample) target.
class DelayGlide {
public:
    void prepare(double sampleRate, double tauSeconds, double maxSpeed, double value) noexcept {
        k_ = 1.0 / (tauSeconds * sampleRate);
        vmax_ = maxSpeed;
        x_ = t_ = value;
        v_ = 0.0;
    }
    void setTarget(double t) noexcept { t_ = t; }
    double next() noexcept {
        if (x_ == t_ && v_ == 0.0) return x_;
        v_ = std::clamp(v_ + k_ * k_ * (t_ - x_) - 2.0 * k_ * v_, -vmax_, vmax_);
        x_ += v_;
        if (std::fabs(t_ - x_) < 1e-9 && std::fabs(v_) < 1e-9) {
            x_ = t_;
            v_ = 0.0;
        }
        return x_;
    }
    double value() const noexcept { return x_; }
    double target() const noexcept { return t_; }

private:
    double k_{0.0}, vmax_{0.5}, x_{0.0}, t_{0.0}, v_{0.0};
};

// Stereo predelay that reads whole-sample delays exactly (a settled glide), cubic in between, linear
// below one sample (no look-ahead).
class PreDelay {
public:
    void init(double maxSamples) {
        std::size_t n = 16;
        while (n < static_cast<std::size_t>(maxSamples) + 8) n <<= 1;
        for (auto& b : buf_) b.assign(n, 0.0f);
        mask_ = static_cast<std::uint32_t>(n - 1);
        w_ = 0;
        max_ = maxSamples;
    }
    void tick(float l, float r, double d, float& ol, float& orr) noexcept {
        buf_[0][w_ & mask_] = l;
        buf_[1][w_ & mask_] = r;
        const double fl = std::floor(std::clamp(d, 0.0, max_));
        const auto i = static_cast<std::uint32_t>(fl);
        const auto f = static_cast<float>(std::clamp(d, 0.0, max_) - fl);
        if (f == 0.0f) {
            ol = tap(0, i);
            orr = tap(1, i);
        } else if (i == 0) {
            ol = tap(0, 0) + f * (tap(0, 1) - tap(0, 0));
            orr = tap(1, 0) + f * (tap(1, 1) - tap(1, 0));
        } else {
            ol = cubic(0, i, f);
            orr = cubic(1, i, f);
        }
        ++w_;
    }

private:
    float tap(int c, std::uint32_t d) const noexcept { return buf_[c][(w_ - d) & mask_]; }
    float cubic(int c, std::uint32_t i, float f) const noexcept {  // Catmull-Rom between delays i and i + 1
        const float xm1 = tap(c, i - 1), x0 = tap(c, i), x1 = tap(c, i + 1), x2 = tap(c, i + 2);
        const float c1 = 0.5f * (x1 - xm1);
        const float c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2;
        const float c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
        return ((c3 * f + c2) * f + c1) * f + x0;
    }
    std::vector<float> buf_[2];
    std::uint32_t mask_{0}, w_{0};
    double max_{0.0};
};

class Convolver final : public ParamEffect {
public:
    Convolver() : ParamEffect(convolverSpecs(), "convolver") {}

    void configure(const json& j) override {
        params_.configure(j, type_, {"ir"});
        seen_ = ~0u;
        if (!j.is_object() || !j.contains("ir")) {
            throw ConfigError("convolver: 'ir' is required: the impulse-response WAV, relative to assets/ (e.g. "
                              "\"samples/<pack>/<file>.wav\") or absolute");
        }
        const json& v = j["ir"];
        ir_.clear();
        const std::string what = "convolver: 'ir' must be a WAV path (relative to assets/ or absolute) or a list of 2 or 4 of them";
        if (v.is_string()) {
            ir_.push_back(v.get<std::string>());
        } else if (v.is_array() && (v.size() == 1 || v.size() == 2 || v.size() == 4)) {
            for (const json& e : v) {
                if (!e.is_string()) throw ConfigError(what);
                ir_.push_back(e.get<std::string>());
            }
        } else {
            throw ConfigError(what);
        }
        for (const auto& p : ir_)
            if (p.empty()) throw ConfigError(what + " (got an empty path)");
    }
    const std::vector<ParamSpec>& paramSpecs() const override { return convolverSpecs(); }

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        conv::IrOptions o;
        o.sampleRate = sr_;
        o.startMs = get(kStart);
        o.lengthSec = get(kLength);
        o.stretch = get(kStretch);
        o.normalize = on(kNormalize);
        o.reverse = on(kReverse);
        const conv::Ir ir = [&] {
            try {
                std::vector<std::string> paths;
                for (const auto& p : ir_) paths.push_back(conv::resolveIrPath(ctx.assetDir, p));
                return conv::loadIr(paths, ir_, o);
            } catch (const ConfigError& e) {
                throw ConfigError(std::string("convolver: ") + e.what());
            }
        }();
        engine_.prepare(ir.channels, ir.routes, startSample_);
        irSeconds_ = static_cast<double>(engine_.irLength()) / sr_;

        maxPre_ = kMaxPredelayMs * 1e-3 * sr_;
        pre_.init(maxPre_);
        preGlide_.prepare(sr_, 0.05, 0.5, predelaySamples());

        ctrlK_ = ctrlCoeff(sr_, kCtrl, 0.003);  // wet filters: ~7 ms (10-90 %)
        lowCut_.snap(get(kLowCut));
        highCut_.snap(get(kHighCut));
        for (int c = 0; c < 2; ++c) {
            lc_[c].reset();
            hc_[c].reset();
            lc_[c].setCutoff(sr_, lowCut_.v, 0);
            hc_[c].setCutoff(sr_, highCut_.v, 0);
        }
        lowOn_.prepare(sr_, 0.0015, lowEngaged() ? 1.0f : 0.0f);
        highOn_.prepare(sr_, 0.0015, highEngaged() ? 1.0f : 0.0f);
        width_.prepare(sr_, 0.0015, get(kWidth));
        gain_.prepare(sr_, 0.0015, dsp::dbToGain(get(kGain)));
        float dry, wet;
        equalPowerMix(get(kMix), dry, wet);
        dry_.prepare(sr_, 0.0015, dry);
        wet_.prepare(sr_, 0.0015, wet);
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) pullTargets();
        for (int c = 0; c < frames; c += kChunk) processChunk(left + c, right + c, std::min(kChunk, frames - c));
    }

    double tailSeconds() const override {
        return irSeconds_ + std::max(preGlide_.target(), preGlide_.value()) / sr_ + 0.05;
    }

private:
    void processChunk(float* L, float* R, int n) noexcept {
        for (int i = 0; i < n; ++i) pre_.tick(L[i], R[i], preGlide_.next(), dl_[i], dr_[i]);
        engine_.process(dl_, dr_, wl_, wr_, n);
        forEachCtrlBlock(pos_, n, [&](int off, int m, bool tick) {
            if (tick) controlTick();
            for (int k = 0; k < m; ++k) {
                const int i = off + k;
                float a = wl_[i], b = wr_[i];
                const float el = lowOn_.next(), eh = highOn_.next();
                const float la = lc_[0].process(a), lb = lc_[1].process(b);
                a += el * (la - a);
                b += el * (lb - b);
                const float ha = hc_[0].process(a), hb = hc_[1].process(b);
                a += eh * (ha - a);
                b += eh * (hb - b);
                const float s = 0.5f * (a - b) * (width_.next() - 1.0f);  // exact at width 1
                a += s;
                b -= s;
                const float g = wet_.next() * gain_.next();
                const float dg = dry_.next();
                L[i] = dg * L[i] + g * a;
                R[i] = dg * R[i] + g * b;
            }
        });
    }

    bool lowEngaged() const noexcept { return get(kLowCut) > kLowOff; }
    bool highEngaged() const noexcept { return get(kHighCut) < kHighOff; }
    double predelaySamples() const noexcept {  // whole samples: a settled predelay reads exact taps
        return std::clamp(std::round(get(kPredelay) * 1e-3 * sr_), 0.0, std::floor(maxPre_));
    }

    void pullTargets() {
        lowCut_.t = get(kLowCut);
        highCut_.t = get(kHighCut);
        lowOn_.setTarget(lowEngaged() ? 1.0f : 0.0f);
        highOn_.setTarget(highEngaged() ? 1.0f : 0.0f);
        width_.setTarget(get(kWidth));
        gain_.setTarget(dsp::dbToGain(get(kGain)));
        float dry, wet;
        equalPowerMix(get(kMix), dry, wet);
        dry_.setTarget(dry);
        wet_.setTarget(wet);
        preGlide_.setTarget(predelaySamples());
    }

    void controlTick() noexcept {
        if (lowCut_.step(ctrlK_))
            for (auto& f : lc_) f.setCutoff(sr_, lowCut_.v, kCtrl);
        if (highCut_.step(ctrlK_))
            for (auto& f : hc_) f.setCutoff(sr_, highCut_.v, kCtrl);
    }

    std::vector<std::string> ir_;
    conv::Engine engine_;
    double irSeconds_{0.0};
    PreDelay pre_;
    DelayGlide preGlide_;
    double maxPre_{24000.0};
    TptFilter lc_[2]{TptFilter::Mode::High, TptFilter::Mode::High};
    TptFilter hc_[2]{TptFilter::Mode::Low, TptFilter::Mode::Low};
    CtrlSmooth lowCut_, highCut_;
    Smooth2 lowOn_, highOn_, width_, gain_, dry_, wet_;
    float ctrlK_{0.0f};
    float dl_[kChunk]{}, dr_[kChunk]{}, wl_[kChunk]{}, wr_[kChunk]{};
};

}  // namespace

std::unique_ptr<Effect> makeConvolver() { return std::make_unique<Convolver>(); }

}  // namespace as
