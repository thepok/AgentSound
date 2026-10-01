// ensemble: string-machine ensemble chorus (ARP Solina / Roland RS style).
//
// Three bucket-brigade delay lines around ~5 ms, each swept by the sum of a slow chorus LFO (~0.6 Hz)
// and a fast shimmer LFO (~6 Hz); both LFOs have three outputs 120 degrees apart, one per line. At
// any moment one voice is sharp, one flat and one in between, and the three delays always add up to
// the same value, so the ensemble thickens and animates without an overall pitch wobble: the lush,
// slightly seasick string-machine shimmer. The three voices sit left / centre / right ('spread'), each
// side taps its own input channel (a stereo source keeps its image), and a low-pass on the wet signal
// gives the bucket-brigade darkness.
//
// Bass: at low frequencies a few ms of sweep barely move the phase, so the voices add up coherently with
// each other and with the dry signal ~5.5 ms earlier: a static comb (+3 dB at 40 Hz, a -6 dB notch near
// 90 Hz, the lows half out of phase between the sides). A Linkwitz-Riley split ('lowcut', 24 dB/oct)
// keeps everything below it out of the ensemble: the lows pass dry, centred and at unity (also at mix
// 1), the split sums flat (all-pass), and only the band above it is chorused.

#include "fx/TimeFxUtil.h"

namespace as::timefx {
namespace {

enum EnsembleParam { kEMix, kERate, kEDepth, kEShimmer, kEShimmerRate, kESpread, kETone, kELowCut };

const std::vector<ParamSpec>& ensembleSpecs() {
    static const std::vector<ParamSpec> s = {
        num("mix", 0, 1, 0.6f, "",
            "Dry/wet balance (equal power); 0.5-0.7 = classic string machine, 1 = ensemble only (the lows below 'lowcut' "
            "stay dry)"),
        num("rate", 0.05f, 3, 0.63f, "Hz",
            "Slow chorus LFO rate (three phases, 120 degrees apart); ~0.6 Hz like the Solina"),
        num("depth", 0, 1, 0.5f, "",
            "Slow chorus sweep: 0.5 = classic Solina depth (about +-13 cents at 0.63 Hz), 1 = deep and seasick, 0 = off"),
        num("shimmer", 0, 1, 0.5f, "",
            "Fast shimmer LFO depth: 0.5 = classic ensemble shimmer (about +-13 cents at 5.9 Hz), 1 = wide vibrato, "
            "0 = slow chorus only"),
        num("shimmerrate", 2, 12, 5.9f, "Hz", "Fast shimmer LFO rate (three phases); 5-7 Hz = string ensemble"),
        num("spread", 0, 1, 1, "",
            "Stereo spread of the three voices: 1 = left / centre / right (wide), 0 = mono ensemble"),
        num("tone", 2000, 20000, 8000, "Hz",
            "Low-pass on the ensemble signal (bucket-brigade darkness; ~8 kHz like the originals)"),
        num("lowcut", 20, 1000, 150, "Hz",
            "Below this the signal bypasses the ensemble (24 dB/oct split): bass notes stay solid, centred and mono "
            "(no comb notch); 100-250 typical, 20 = everything through the ensemble"),
    };
    return s;
}

// Automation smoothing (see TimeFxMod.cpp): delay-time parameters glide slowly on purpose (a fast
// delay-time change is a pitch jump), gains and tone are fast, LFO rates glide over ~50 ms.
constexpr double kGainTau = 0.0015;
constexpr double kToneTau = 0.002;
constexpr double kDelayTau = 0.025;
constexpr double kRateTau = 0.05;

// Delay sweep at depth / shimmer 1: pitch deviation = 2 pi f A, i.e. +-1.5 % (26 cents) for both
// LFOs at their default rates; the defaults (0.5) give +-13 cents each.
constexpr double kCentreMs = 5.5;
constexpr double kSlowMs = 3.8;
constexpr double kFastMs = 0.4;

class Ensemble final : public ParamEffect {
public:
    Ensemble() : ParamEffect(ensembleSpecs(), "ensemble") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        msToS_ = sr_ / 1000.0;
        for (auto& l : line_) l.init(static_cast<int>(std::ceil((kCentreMs + kSlowMs + kFastMs + 1.0) * msToS_)) + 4);
        // free-running LFOs: a preview render starts where a full render (at constant rates) would be
        slow_ = wrap01(get(kERate) * startSeconds());
        fast_ = wrap01(get(kEShimmerRate) * startSeconds());
        rate_.prepare(sr_, kRateTau, get(kERate));
        fastRate_.prepare(sr_, kRateTau, get(kEShimmerRate));
        depth_.prepare(sr_, kDelayTau, get(kEDepth));
        shimmer_.prepare(sr_, kDelayTau, get(kEShimmer));
        spread_.prepare(sr_, kGainTau, get(kESpread));
        float dry, wet;
        equalPowerMix(get(kEMix), dry, wet);
        dry_.prepare(sr_, kGainTau, dry);
        wet_.prepare(sr_, kGainTau, wet);
        tone_.snap(get(kETone));
        toneK_ = ctrlCoeff(sr_, kCtrl, kToneTau);
        for (auto& f : lp_) {
            f.setCutoff(sr_, tone_.v, 0);
            f.reset();
        }
        lowCut_.snap(get(kELowCut));
        setSplit(0);
        for (auto& ch : split_)
            for (auto& f : ch) f.reset();
        pans(spread_.value());
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) {
            rate_.setTarget(get(kERate));
            fastRate_.setTarget(get(kEShimmerRate));
            depth_.setTarget(get(kEDepth));
            shimmer_.setTarget(get(kEShimmer));
            spread_.setTarget(get(kESpread));
            float dry, wet;
            equalPowerMix(get(kEMix), dry, wet);
            dry_.setTarget(dry);
            wet_.setTarget(wet);
            tone_.t = get(kETone);
            lowCut_.t = get(kELowCut);
        }
        float* io[2] = {left, right};
        const double slowAmp = kSlowMs * msToS_, fastAmp = kFastMs * msToS_, centre = kCentreMs * msToS_;
        forEachCtrlBlock(pos_, frames, [&](int start, int len, bool tick) {
            if (tick && tone_.step(toneK_))
                for (auto& f : lp_) f.setCutoff(sr_, tone_.v, kCtrl);
            if (tick && lowCut_.step(toneK_)) setSplit(kCtrl);
            for (int n = start; n < start + len; ++n) {
                slow_ = wrap01(slow_ + rate_.next() / sr_);
                fast_ = wrap01(fast_ + fastRate_.next() / sr_);
                const double ds = depth_.next() * slowAmp, df = shimmer_.next() * fastAmp;
                if (spread_.moving()) pans(spread_.next());
                double d[3];
                for (int v = 0; v < 3; ++v)
                    d[v] = centre + ds * sinCycles(slow_ + v / 3.0) + df * sinCycles(fast_ + v / 3.0);
                const float dg = dry_.next(), wg = wet_.next();
                for (int ch = 0; ch < 2; ++ch) {
                    // Linkwitz-Riley split: lo + hi = all-pass of the input
                    TptFilter* f = split_[ch];
                    const float x = io[ch][n];
                    const float lo = f[1].process(f[0].process(x)), hi = f[3].process(f[2].process(x));
                    float w = 0.0f;
                    for (int v = 0; v < 3; ++v)
                        if (gain_[ch][v] != 0.0f) w += gain_[ch][v] * line_[ch].tapCubic(d[v]);
                    line_[ch].write(hi);
                    io[ch][n] = lo + dg * hi + wg * lp_[ch].process(w);
                }
            }
        });
    }

    double tailSeconds() const override { return (kCentreMs + kSlowMs + kFastMs) * 1e-3 + 0.01; }

private:
    void setSplit(int samples) noexcept {
        for (auto& ch : split_)
            for (auto& f : ch) f.setCutoff(sr_, lowCut_.v, samples);
    }

    // Voices at -spread, 0, +spread (equal-power pan). The per-side power sum is 1.5 at any spread, so
    // 1/sqrt(1.5) keeps decorrelated (mid / high) content at the input level.
    void pans(float spread) noexcept {
        const float norm = 0.81649658f;
        for (int v = 0; v < 3; ++v) {
            float gl, gr;
            dsp::panGains(spread * static_cast<float>(v - 1), gl, gr);
            gain_[0][v] = norm * gl;
            gain_[1][v] = norm * gr;
        }
    }

    RingDelay line_[2];
    TptFilter lp_[2];
    // per channel: two cascaded Butterworth low-passes, then two high-passes (LR4 low / high band)
    TptFilter split_[2][4]{{TptFilter::Mode::Low, TptFilter::Mode::Low, TptFilter::Mode::High, TptFilter::Mode::High},
                           {TptFilter::Mode::Low, TptFilter::Mode::Low, TptFilter::Mode::High, TptFilter::Mode::High}};
    dsp::Smoother rate_, fastRate_;
    Smooth2 depth_, shimmer_, spread_, dry_, wet_;
    CtrlSmooth tone_, lowCut_;
    float toneK_{0.0f};
    float gain_[2][3]{};
    double slow_{0.0}, fast_{0.0}, msToS_{48.0};
};

}  // namespace

std::unique_ptr<Effect> makeEnsemble() { return std::make_unique<Ensemble>(); }

}  // namespace as::timefx
