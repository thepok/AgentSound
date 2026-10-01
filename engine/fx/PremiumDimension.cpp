// dimension: Roland SDD-320 "Dimension D" style spatial chorus (4 modes).
//
// The mono sum of the input feeds two short BBD-like delay lines whose delay times are swept by the
// same slow triangle LFO in opposite directions. Each output gets the dry signal plus the difference
// of the two delays, with opposite polarity on the other side:
//     L = dry_L + g (D1 - D2),   R = dry_R - g (D1 - D2)
// so the effect is a pure side signal: the stereo image gets wide and animated, but the mono sum is
// exactly the dry signal (no chorus wobble or comb filtering in mono), and lows (where D1 ~ D2)
// stay centred. The triangle keeps the pitch deviation constant and tiny (a few cents), which is why
// the Dimension sounds like "space" rather than chorus. Modes 1-3 deepen the sweep at 0.25 Hz,
// mode 4 is faster and deep. The delayed voices are band-limited like a BBD (~9 kHz) and high-passed
// at 150 Hz (4-pole).

#include "fx/PremiumUtil.h"

namespace as::premium {
namespace {

using namespace timefx;

enum DimParam { kDMode, kDMix, kDWidth };

struct DimMode {
    double rateHz, depthMs, gain;
};
constexpr DimMode kModes[4] = {
    {0.25, 0.45, 0.28},  // 1: subtle
    {0.25, 0.75, 0.36},  // 2
    {0.25, 1.10, 0.45},  // 3: the classic pad setting
    {0.50, 0.95, 0.50},  // 4: faster, most animated
};
constexpr double kBaseMs = 3.2;  // centre delay of both lines

const std::vector<ParamSpec>& dimSpecs() {
    static const std::vector<ParamSpec> s = {
        num("mode", 1, 4, 3, "",
            "Dimension mode (whole number, like the unit's buttons): 1 = subtle space, 2 = wider, 3 = classic lush pad "
            "width, 4 = fastest and most animated. On a mono source mode 3 gives ~50 % width (correlation ~0.6); on "
            "sources that are already wide (ensemble/chorus pads) use 1-2. Not automatable", false),
        num("mix", 0, 1, 1, "", "Effect amount (the dry signal always passes at full level; 0 = bypass)"),
        num("width", 0, 2, 1, "", "Scales the side signal the effect adds (1 = the unit, 2 = exaggerated)"),
    };
    return s;
}

class Dimension final : public ParamEffect {
public:
    Dimension() : ParamEffect(dimSpecs(), "dimension") {}

    void configure(const json& params) override {
        ParamEffect::configure(params);
        requireInteger("mode");
    }

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        mode_ = kModes[std::clamp(getInt(kDMode), 1, 4) - 1];
        const double ms = sr_ / 1000.0;
        base_ = kBaseMs * ms;
        depth_ = mode_.depthMs * ms;
        line_.init(static_cast<int>(std::ceil(base_ + depth_)) + 8);
        ph_ = wrap01(0.25 + mode_.rateHz * startSeconds());  // runs from the song start
        for (int i = 0; i < 2; ++i) {
            lp_[i] = TptFilter(TptFilter::Mode::Low);
            lp_[i].setCutoff(sr_, std::min(9000.0, 0.45 * sr_), 0);
            for (auto& h : hp_[i]) {
                h = TptFilter(TptFilter::Mode::High);
                h.setCutoff(sr_, 150.0, 0);
            }
        }
        amt_.prepare(sr_, 0.0015, get(kDMix) * get(kDWidth));
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) amt_.setTarget(get(kDMix) * get(kDWidth));
        const double inc = mode_.rateHz / sr_;
        const float g = static_cast<float>(mode_.gain);
        forEachCtrlBlock(pos_, frames, [&](int off, int n, bool) {
            for (int k = off; k < off + n; ++k) {
                ph_ = wrap01(ph_ + inc);
                const double t = triCycles(ph_) * depth_;
                const float m = 0.5f * (left[k] + right[k]);
                line_.write(m);
                // two taps swept in opposite directions (read after the write: delay 1 = this sample)
                const float d1 = hp_[0][1].process(hp_[0][0].process(lp_[0].process(line_.tapCubic(base_ + t + 1.0))));
                const float d2 = hp_[1][1].process(hp_[1][0].process(lp_[1].process(line_.tapCubic(base_ - t + 1.0))));
                const float s = amt_.next() * g * (d1 - d2);
                left[k] += s;
                right[k] -= s;
            }
        });
    }

    double tailSeconds() const override { return (base_ + depth_) / sr_ + 0.01; }

private:
    DimMode mode_{kModes[2]};
    RingDelay line_;
    TptFilter lp_[2], hp_[2][2];  // BBD band limit, 4-pole low cut (lows stay centred)
    Smooth2 amt_;
    double base_{150.0}, depth_{50.0}, ph_{0.0};
};

}  // namespace

std::unique_ptr<Effect> makeDimension() { return std::make_unique<Dimension>(); }

}  // namespace as::premium
