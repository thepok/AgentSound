// shimmer: lush reverb whose feedback path is pitch-shifted (+12 st, optionally +7 st), after the
// Eventide / Valhalla / Strymon "shimmer" idea: every pass through the loop lifts the tail by another
// octave, so the tail blooms into a bright, choir-like halo while the original notes fade.
//
//   in -> predelay -> (+ shifted feedback) -> reverb core (fx/ReverbCore.h: 16-line diffuser + FDN,
//         the same core as 'reverb') -> wet
//   wet -> feedback filters (low cut, tone / anti-alias low-pass) -> grain pitch shifters (equal-power
//         overlapping grains, +12 st and +7 st, fx/PremiumUtil.h) x shimmer / fifth -> soft limiter
//         -> back into the reverb input
//   out = equal-power mix of dry and (wet -> low/high cut -> width).
//
// The loop gain is normalised to the reverb's own energy gain for the current decay, so 'shimmer' = 1
// sustains a strong octave bloom at any decay time and still decays. The loop runs in 32-sample
// sub-blocks on the absolute control grid (the shifters' shortest delay exceeds a sub-block), so the
// output does not depend on host block sizes, and a preview render (silent before its start) matches
// the same span of a full render.

#include "fx/PremiumUtil.h"
#include "fx/ReverbCore.h"

namespace as::premium {
namespace {

using namespace timefx;

enum ShParam { kSMix, kSDecay, kSSize, kSShimmer, kSFifth, kSDamping, kSPredelay, kSModRate, kSModDepth, kSLowCut,
               kSHighCut, kSWidth };

const std::vector<ParamSpec>& shimmerSpecs() {
    static const std::vector<ParamSpec> s = {
        num("mix", 0, 1, 0.35f, "", "Dry/wet balance (equal power); 1.0 = wet only for a send bus, 0.2-0.4 as an insert"),
        num("decay", 0.5f, 30, 7, "s", "RT60 of the reverb (the shimmer feedback makes the octave halo last longer still)"),
        num("size", 0, 1, 0.85f, "", "Space size of the reverb core; not automatable", false),
        num("shimmer", 0, 1, 0.6f, "",
            "Octave-up (+12 st) feedback: 0 = plain lush reverb, 0.3-0.6 = soft halo, 0.8-1 = bright cascading octaves"),
        num("fifth", 0, 1, 0, "",
            "+7 st (fifth) feedback voice for a more organ/choir-like bloom; 0 = off (shimmer and fifth share the loop: "
            "shimmer^2 + fifth^2 above 1 is scaled back)"),
        num("damping", 1000, 20000, 7000, "Hz",
            "HF damping of the tail (RT60 halves there); also limits how bright the upper octaves get"),
        num("predelay", 0, 500, 40, "ms", "Gap before the reverb (keeps the attack of the dry notes clear)"),
        num("modrate", 0.05f, 5, 0.5f, "Hz", "Rate of the reverb's delay-line modulation"),
        num("moddepth", 0, 1, 0.6f, "", "Delay-line modulation depth: 0.4-0.8 lush and chorused"),
        num("lowcut", 20, 2000, 180, "Hz", "High-pass on the wet signal and in the feedback loop (keeps the halo out of the bass)"),
        num("highcut", 1000, 20000, 14000, "Hz", "Low-pass on the wet signal"),
        num("width", 0, 1.5f, 1.0f, "", "Stereo width of the wet signal (0 = mono, 1 = natural and mono-safe, >1 wider but phasey in mono)"),
    };
    return s;
}

class Shimmer final : public ParamEffect {
public:
    Shimmer() : ParamEffect(shimmerSpecs(), "shimmer") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        core_.prepare(sr_, get(kSSize), 0.9f);
        maxPre_ = 0.5 * sr_;
        pre_.prepare(sr_, maxPre_, predelaySamples());

        // Pitch shifters: equal-power, fully overlapping grains (a new grain every 60 ms, each 120 ms
        // long); the dense reverb tail needs no splice alignment.
        const double spacing = std::round(0.06 * sr_);
        GrainShifter::Shape shape;
        shape.spacing = spacing;
        shape.fade = 1e9;  // limited to the grain period: full overlap
        shape.search = 0;
        shape.equalPower = true;
        // the fastest grain (octave: 1 sample/sample) must stay kCtrl + 4 samples behind the write head
        shape.center = static_cast<double>(kCtrl + 8) + 1.5 * spacing;
        for (int c = 0; c < 2; ++c) {
            line_[c].init(static_cast<int>(GrainShifter::highestDelay(shape, 1.0) + 16));
            oct_[c].setup(shape, true, 2.0, startSample_);
            fifth_[c].setup(shape, true, std::pow(2.0, 7.0 / 12.0), startSample_);
        }

        ctrlK_ = ctrlCoeff(sr_, kCtrl, 0.003);
        modK_ = ctrlCoeff(sr_, kCtrl, 0.05);
        decay_.snap(get(kSDecay));
        damp_.snap(get(kSDamping));
        lowCut_.snap(get(kSLowCut));
        highCut_.snap(get(kSHighCut));
        modDepth_.snap(get(kSModDepth));
        modRate_ = get(kSModRate);
        core_.setDecay(decay_.v, kLowMult, kLowXover, damp_.v, false);
        tMax_ = core_.longestDecay(decay_.v);
        core_.setModulation(modRate_, modDepth_.v);
        core_.alignModulation(startSample_);
        wet_.reset();
        wet_.setLowCut(sr_, lowCut_.v, 0);
        wet_.setHighCut(sr_, highCut_.v, 0);
        for (int c = 0; c < 2; ++c) {
            fbHp_[c] = TptFilter(TptFilter::Mode::High);
            fbLp_[c][0] = fbLp_[c][1] = TptFilter(TptFilter::Mode::Low);
        }
        setFeedbackFilters(0);

        octG_.prepare(sr_, 0.0015, loopGain(get(kSShimmer) / voiceNorm()));
        fifthG_.prepare(sr_, 0.0015, loopGain(get(kSFifth) / voiceNorm()));
        width_.prepare(sr_, 0.0015, get(kSWidth));
        float dry, wet;
        equalPowerMix(get(kSMix), dry, wet);
        dry_.prepare(sr_, 0.0015, dry);
        wetG_.prepare(sr_, 0.0015, wet);
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) pullTargets();
        forEachCtrlBlock(pos_, frames, [&](int off, int n, bool tick) {
            if (tick) controlTick();
            float* L = left + off;
            float* R = right + off;
            float in[2][kCtrl], sh[2][kCtrl], sf[2][kCtrl];
            for (int k = 0; k < n; ++k) pre_.tick(L[k], R[k], in[0][k], in[1][k]);
            static constexpr double kNoExtra[kCtrl] = {};
            for (int c = 0; c < 2; ++c) {
                oct_[c].read(line_[c], sh[c], n, kNoExtra);
                fifth_[c].read(line_[c], sf[c], n, kNoExtra);
            }
            for (int k = 0; k < n; ++k) {
                const float go = octG_.next(), gf = fifthG_.next();
                for (int c = 0; c < 2; ++c) in[c][k] += softSat(go * sh[c][k] + gf * sf[c][k]);
            }
            float wl[kCtrl], wr[kCtrl];
            core_.diffuse(in[0], in[1], n);
            core_.late(0, wl, wr, n);
            float fb[kCtrl];
            float* w[2] = {wl, wr};
            for (int c = 0; c < 2; ++c) {
                for (int k = 0; k < n; ++k) fb[k] = dsp::flush(fbLp_[c][1].process(fbLp_[c][0].process(fbHp_[c].process(w[c][k]))));
                line_[c].write(fb, n);
            }
            for (int k = 0; k < n; ++k) {
                const float a = wet_.process(0, wl[k]), b = wet_.process(1, wr[k]);
                const float m = 0.5f * (a + b), s = 0.5f * (a - b) * width_.next();
                const float dg = dry_.next(), wg = wetG_.next();
                L[k] = dg * L[k] + wg * (m + s);
                R[k] = dg * R[k] + wg * (m - s);
            }
        });
    }

    double tailSeconds() const override {
        // the longest-ringing band (bass below the damping reference) sets the tail, stretched by the loop
        const double fb = std::max(get(kSShimmer), get(kSFifth));
        return predelaySamples() / sr_ + std::max(static_cast<double>(get(kSDecay)), tMax_) * (1.5 + 2.5 * fb) + 0.3;
    }

private:
    static constexpr double kLowMult = 0.9, kLowXover = 350.0;
    // Loop power gain at shimmer = 1 (relative to the reverb's own energy gain): < 1, so the halo
    // always decays; the feedback filters take a little more.
    static constexpr double kLoop = 0.72;
    static constexpr double kLoopLowCut = 120.0;  // the loop never recirculates the deep lows

    // Feedback gain for an amount: sqrt(kLoop / reverb energy gain), never above 1. The core's output
    // is normalised to an impulse energy of 0.35 sqrt(decay) (fx/ReverbCore.h); a band ringing for
    // tMax_ > decay (low damping lifts the lows) holds 0.35 tMax_ / sqrt(decay), and the loop is sized
    // for the longest-ringing band.
    float loopGain(float amount) const {
        const double t = std::max(0.5, static_cast<double>(decay_.v));
        const double e = 0.35 * std::max(t, tMax_) / std::sqrt(t);
        return static_cast<float>(amount * std::min(1.0, std::sqrt(kLoop / e)));
    }
    double predelaySamples() const { return std::clamp(get(kSPredelay) * 1e-3 * sr_, 2.0, std::max(2.0, maxPre_)); }
    // Feedback: low cut with the wet low cut (at least kLoopLowCut); 4-pole low-pass at the damping
    // frequency (x1.2), never above 0.2 x sample rate: the octave shifter reads at twice the speed,
    // and content above a quarter of the sample rate would alias.
    void setFeedbackFilters(int samples) {
        const double lp = std::min(1.2 * damp_.v, 0.2 * sr_);
        for (int c = 0; c < 2; ++c) {
            fbHp_[c].setCutoff(sr_, std::max(static_cast<double>(lowCut_.v), kLoopLowCut), samples);
            fbLp_[c][0].setCutoff(sr_, lp, samples);
            fbLp_[c][1].setCutoff(sr_, lp, samples);
        }
    }
    void pullTargets() {
        decay_.t = get(kSDecay);
        damp_.t = get(kSDamping);
        lowCut_.t = get(kSLowCut);
        highCut_.t = get(kSHighCut);
        modDepth_.t = get(kSModDepth);
        modRate_ = get(kSModRate);
        pre_.glide.setTarget(predelaySamples());
        width_.setTarget(get(kSWidth));
        float dry, wet;
        equalPowerMix(get(kSMix), dry, wet);
        dry_.setTarget(dry);
        wetG_.setTarget(wet);
        gainTargets();
    }
    // The two voices share one loop budget: shimmer^2 + fifth^2 above 1 is scaled back to 1.
    float voiceNorm() const {
        return std::max(1.0f, std::sqrt(get(kSShimmer) * get(kSShimmer) + get(kSFifth) * get(kSFifth)));
    }
    void gainTargets() {
        const float norm = voiceNorm();
        octG_.setTarget(loopGain(get(kSShimmer) / norm));
        fifthG_.setTarget(loopGain(get(kSFifth) / norm));
    }
    void controlTick() {
        bool d = decay_.step(ctrlK_);
        d |= damp_.step(ctrlK_);
        if (d) {
            core_.setDecay(decay_.v, kLowMult, kLowXover, damp_.v, true);
            tMax_ = core_.longestDecay(decay_.v);
            gainTargets();
        }
        const bool lc = lowCut_.step(ctrlK_);
        if (lc) wet_.setLowCut(sr_, lowCut_.v, kCtrl);
        if (d || lc) setFeedbackFilters(kCtrl);
        if (highCut_.step(ctrlK_)) wet_.setHighCut(sr_, highCut_.v, kCtrl);
        modDepth_.step(modK_);
        core_.setModulation(modRate_, modDepth_.v);
    }

    ReverbCore core_;
    WetFilter wet_;
    Predelay pre_;
    RingDelay line_[2];
    GrainShifter oct_[2], fifth_[2];
    TptFilter fbHp_[2], fbLp_[2][2];
    CtrlSmooth decay_, damp_, lowCut_, highCut_, modDepth_;
    Smooth2 octG_, fifthG_, width_, dry_, wetG_;
    float ctrlK_{0.0f}, modK_{0.0f};
    double modRate_{0.5}, maxPre_{24000.0}, tMax_{7.0};
};

}  // namespace

std::unique_ptr<Effect> makeShimmer() { return std::make_unique<Shimmer>(); }

}  // namespace as::premium
