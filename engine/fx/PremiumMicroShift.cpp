// microshift: stereo micro-pitch-shift widener (Eventide H910 / H3000 doubling, Soundtoys MicroShift
// style). The left side is shifted up and the right side down by a few cents, each at its own short
// delay; the detuned voices beat slowly against each other and the dry signal, which reads as width
// and thickness instead of an echo, and the mono sum keeps its level (the voices are not static
// copies, so no fixed comb filter).
//
//   x -> 4-pole split at 'focus' (lows pass dry and centred) -> grain pitch shifters (fx/PremiumUtil.h):
//        L +detune at delay dL, R -detune at delay dR (per channel input) -> style tone low-pass
//     -> 4-pole high-pass at 'focus' -> equal-power mix with the dry highs (the dry lows stay at full
//        level up to mix 0.5 and fade out above it, so mix 1 on a send bus is voices only).
//
// Styles: classic = H910-like blind splices (short crossfade, slightly grainy, vintage 9.5 kHz
// top), smooth = H3000-like correlation-aligned splices (long crossfade, clean), wide = smooth plus
// slow delay modulation (the detune breathes) and more spread.

#include "fx/PremiumUtil.h"

namespace as::premium {
namespace {

using namespace timefx;

enum MsParam { kMStyle, kMDetune, kMDelay, kMFocus, kMMix };

struct MsStyle {
    double spacingMs, fadeMs, searchMs;  // grain geometry
    double centerL, centerR;             // mean voice delays (ms) before the 'delay' param
    double detuneR;                      // right detune relative to the left
    double detuneMul;                    // style scaling of the 'detune' param
    double lpHz;                         // tone of the voices
    double lfoMs, lfoL, lfoR;            // delay modulation depth (ms) and rates (Hz) per side
};
constexpr MsStyle kStyles[3] = {
    //  spc  fade srch  cL    cR   detR  mul   lp     lfo  rateL rateR
    {8.0, 6.0, 0.0, 9.0, 13.0, 1.0, 1.0, 9500, 0.0, 0.0, 0.0},       // classic (H910)
    {10.0, 24.0, 5.5, 13.0, 17.0, 1.0, 1.0, 14000, 0.0, 0.0, 0.0},   // smooth (H3000)
    {10.0, 24.0, 5.5, 14.0, 20.0, 0.85, 1.3, 12000, 1.2, 0.23, 0.31},  // wide (+ delay modulation)
};
constexpr double kMaxDetune = 50.0;  // cents
constexpr double kMaxDelayMs = 50.0;
constexpr float kSqrt2 = 1.41421356f;

const std::vector<ParamSpec>& msSpecs() {
    static const std::vector<ParamSpec> s = {
        choice("style", {"classic", "smooth", "wide"}, 1,
               "classic = H910-style doubler (blind splices, slightly grainy, vintage top end), smooth = H3000-style "
               "(correlation-aligned splices: clean on vocals, leads and chords), wide = smooth plus slowly breathing "
               "delays and more spread (pads, guitars)"),
        num("detune", 0, static_cast<float>(kMaxDetune), 9, "ct",
            "Pitch shift of the voices: left +detune, right -detune. 5-12 = classic doubling/width, 15-25 = obvious "
            "chorus-like detune, 0 = static delays only (Haas width)"),
        num("delay", 0, static_cast<float>(kMaxDelayMs), 0, "ms",
            "Extra delay of the voices on top of the style's own ~9-20 ms (right side later than left): 0 = tight "
            "doubling, 15-40 = slapback double"),
        num("focus", 20, 2000, 150, "Hz",
            "The effect works above this frequency; lows stay dry and mono (150-300 keeps bass and kick focused)"),
        num("mix", 0, 1, 0.5f, "",
            "Dry/voices balance (equal power; the dry lows below 'focus' stay at full level up to 0.5, then fade with "
            "the dry). 0.3-0.5 as an insert on a mono lead/vocal/synth, 1.0 = voices only on a send bus"),
    };
    return s;
}

class MicroShift final : public ParamEffect {
public:
    MicroShift() : ParamEffect(msSpecs(), "microshift") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        style_ = kStyles[std::clamp(getInt(kMStyle), 0, 2)];
        const double ms = sr_ / 1000.0;
        const double maxDev = std::pow(2.0, kMaxDetune * style_.detuneMul / 1200.0) - 1.0;
        for (int c = 0; c < 2; ++c) {
            GrainShifter::Shape& s = shape_[c];
            s.center = (c ? style_.centerR : style_.centerL) * ms;
            s.spacing = style_.spacingMs * ms;
            s.fade = style_.fadeMs * ms;
            s.search = std::min(GrainShifter::kMaxSearch, static_cast<int>(std::lround(style_.searchMs * ms)));
            s.corrLen = static_cast<int>(std::lround(10.0 * ms));
            s.equalPower = false;
            const double hi = GrainShifter::highestDelay(s, maxDev) + (kMaxDelayMs + 2.0 * style_.lfoMs) * ms + s.corrLen + 8;
            line_[c].init(static_cast<int>(std::ceil(hi)));
        }
        detune_.snap(get(kMDetune));
        for (int c = 0; c < 2; ++c) sh_[c].setup(shape_[c], c == 0, ratio(c, detune_.v), startSample_);
        delay_.prepare(sr_, 0.03, get(kMDelay) * ms);
        // delay modulation (wide): phases run from the song start
        const double t0 = startSeconds();
        lfoPh_[0] = wrap01(0.0 + style_.lfoL * t0);
        lfoPh_[1] = wrap01(0.37 + style_.lfoR * t0);
        lfoAmp_ = 0.5 * style_.lfoMs * ms;
        ctrlK_ = ctrlCoeff(sr_, kCtrl, 0.003);
        focus_.snap(get(kMFocus));
        for (int c = 0; c < 2; ++c) {
            for (int s = 0; s < 2; ++s) {
                split_[c][s] = TptFilter(TptFilter::Mode::Low);
                hp_[c][s] = TptFilter(TptFilter::Mode::High);
                split_[c][s].setCutoff(sr_, focus_.v, 0);
                hp_[c][s].setCutoff(sr_, focus_.v, 0);
            }
            lp_[c] = TptFilter(TptFilter::Mode::Low);
            lp_[c].setCutoff(sr_, style_.lpHz, 0);
        }
        float dry, wet;
        equalPowerMix(get(kMMix), dry, wet);
        dry_.prepare(sr_, 0.0015, dry);
        wet_.prepare(sr_, 0.0015, wet);
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) pullTargets();
        float* io[2] = {left, right};
        forEachCtrlBlock(pos_, frames, [&](int off, int n, bool tick) {
            if (tick) controlTick();
            double extra[2][kCtrl];
            for (int k = 0; k < n; ++k) {
                const double base = delay_.next();
                for (int c = 0; c < 2; ++c) {
                    double e = base;
                    if (lfoAmp_ > 0.0) {
                        lfoPh_[c] = wrap01(lfoPh_[c] + (c ? style_.lfoR : style_.lfoL) / sr_);
                        e += lfoAmp_ * (1.0 + sinCycles(lfoPh_[c]));
                    }
                    extra[c][k] = e;
                }
            }
            float voice[2][kCtrl];
            for (int c = 0; c < 2; ++c) {
                sh_[c].read(line_[c], voice[c], n, extra[c]);
                line_[c].write(io[c] + off, n);
            }
            for (int k = 0; k < n; ++k) {
                const float dg = dry_.next(), wg = wet_.next();
                // the lows below 'focus' stay at full level up to mix 0.5 and fade out with the dry
                // above it: mix 1 is voices only (a send return must not add a second copy of the lows)
                const float lg = std::min(1.0f, kSqrt2 * dg);
                for (int c = 0; c < 2; ++c) {
                    const float x = io[c][off + k];
                    const float lo = split_[c][1].process(split_[c][0].process(x));
                    const float v = hp_[c][1].process(hp_[c][0].process(lp_[c].process(voice[c][k])));
                    io[c][off + k] = lg * lo + dg * (x - lo) + wg * v;
                }
            }
        });
    }

    double tailSeconds() const override {
        return (std::max(style_.centerL, style_.centerR) + style_.spacingMs + kMaxDelayMs + 2.0 * style_.lfoMs) * 1e-3;
    }

private:
    double ratio(int c, double cents) const {
        const double ct = cents * style_.detuneMul * (c ? style_.detuneR : 1.0);
        return std::pow(2.0, (c ? -ct : ct) / 1200.0);
    }
    void pullTargets() {
        detune_.t = get(kMDetune);
        focus_.t = get(kMFocus);
        delay_.setTarget(get(kMDelay) * sr_ / 1000.0);
        float dry, wet;
        equalPowerMix(get(kMMix), dry, wet);
        dry_.setTarget(dry);
        wet_.setTarget(wet);
    }
    void controlTick() {
        if (detune_.step(ctrlK_))
            for (int c = 0; c < 2; ++c) sh_[c].setRatio(ratio(c, detune_.v));
        if (focus_.step(ctrlK_))
            for (int c = 0; c < 2; ++c)
                for (int s = 0; s < 2; ++s) {
                    split_[c][s].setCutoff(sr_, focus_.v, kCtrl);
                    hp_[c][s].setCutoff(sr_, focus_.v, kCtrl);
                }
    }

    MsStyle style_{kStyles[1]};
    GrainShifter::Shape shape_[2];
    GrainShifter sh_[2];
    RingDelay line_[2];
    Glide delay_;
    CtrlSmooth detune_, focus_;
    TptFilter split_[2][2], hp_[2][2], lp_[2];  // 4-pole split / voice high-pass at 'focus'
    Smooth2 dry_, wet_;
    double lfoPh_[2]{}, lfoAmp_{0.0};
    float ctrlK_{0.0f};
};

}  // namespace

std::unique_ptr<Effect> makeMicroShift() { return std::make_unique<MicroShift>(); }

}  // namespace as::premium
