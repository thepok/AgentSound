// Wah: the guitarist's foot pedal (a Cry Baby-style resonant sweep) and an auto-wah (the envelope of the playing
// moves the pedal).
//
// The pedal position 0 (heel, dark) .. 1 (toe, bright) sets the resonance frequency on a log scale between 'lo' and
// 'hi'; the voice is a resonant band-pass (unity gain at the centre) over a little of the low-pass (the pedal's body:
// a real wah is a resonant low-pass whose lows are thinned), a TPT state-variable filter re-tuned every 8 samples
// from a smoothed position, so automation sweeps (the "wacka" on 16ths, a slow cocked-wah sweep into a note) are
// click-free. mode 'auto': the pedal position is 'pedal' + 'sens' x the input's envelope (attack / release ms) -
// every pick opens the filter and it closes as the note decays. Before an amp (in a guitar's insert chain ahead of the
// amp, or a stack zone's chain) it sounds like the pedal; after, like a studio filter.

#include "core/Module.h"
#include "fx/TimeFxUtil.h"

#include <algorithm>
#include <cmath>

namespace as::timefx {

namespace {

enum WahParam { kWPedal, kWMode, kWSens, kWAttack, kWRelease, kWLo, kWHi, kWQ, kWBody, kWMix, kWGain };

const std::vector<ParamSpec>& wahSpecs() {
    static const std::vector<ParamSpec> s = {
        num("pedal", 0, 1, 0.5f, "",
            "Pedal position: 0 = heel (dark, the resonance at 'lo') .. 1 = toe (bright, at 'hi'), log-scaled. Automate "
            "it for sweeps (a 'wacka' on 16ths: 0.1 <-> 0.9 per 8th; a slow cocked sweep into a held note). Smoothed "
            "(~8 ms)."),
        choice("mode", {"pedal", "auto"}, 0,
               "pedal: the position is 'pedal'. auto: an auto-wah - 'pedal' + 'sens' x the input's envelope (0 dB at "
               "-6 dBFS .. 40 dB below: closed), so every pick opens it and it closes as the note decays."),
        num("sens", 0, 1, 0.6f, "", "auto mode: how far the playing opens the pedal (0..1 of its travel)."),
        num("attack", 0.5f, 100, 6, "ms", "auto mode: envelope attack."),
        num("release", 10, 2000, 180, "ms", "auto mode: envelope release (how slowly the filter closes)."),
        num("lo", 150, 1200, 380, "Hz", "Resonance at the heel (Cry Baby ~350-450 Hz)."),
        num("hi", 700, 6000, 2200, "Hz", "Resonance at the toe (Cry Baby ~2-2.5 kHz)."),
        num("q", 1, 20, 5.5f, "", "Resonance (Q): 3-4 = smooth, 5-7 = vocal, 10+ = quacky."),
        num("body", 0, 1, 0.25f, "",
            "Share of the low-pass under the resonant peak (the pedal's body: 0 = a thin band-pass, 0.5 = fuller)."),
        num("mix", 0, 1, 1, "", "Wet share (1 = all through the pedal)."),
        num("gain", -24, 12, 0, "dB",
            "Output level. The resonance peaks at Q^0.6 (+9 dB at Q 5.5) like a real pedal; broadband material (a full "
            "chord, noise) still comes out quieter than it went in - make it good here."),
    };
    return s;
}

class Wah final : public ParamEffect {
public:
    Wah() : ParamEffect(wahSpecs(), "wah") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        if (get(kWLo) >= get(kWHi)) throw ConfigError("wah: 'lo' must be below 'hi'");
        pedal_.prepare(sr_, kPedalTau, get(kWPedal));
        mix_.prepare(sr_, kGainTau, get(kWMix));
        gain_.prepare(sr_, kGainTau, dsp::dbToGain(get(kWGain)));
        lo_.prepare(sr_, kShapeTau, std::log(get(kWLo)));
        hi_.prepare(sr_, kShapeTau, std::log(get(kWHi)));
        q_.prepare(sr_, kShapeTau, get(kWQ));
        body_.prepare(sr_, kShapeTau, get(kWBody));
        env_ = 0.0f;
        for (auto& st : s_) st = {};
        ctl_ = 0;
        retune(pedal_.value());
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) {
            pedal_.setTarget(get(kWPedal));
            mix_.setTarget(get(kWMix));
            gain_.setTarget(dsp::dbToGain(get(kWGain)));
            lo_.setTarget(std::log(get(kWLo)));
            hi_.setTarget(std::log(get(kWHi)));
            q_.setTarget(get(kWQ));
            body_.setTarget(get(kWBody));
        }
        const bool autoMode = getInt(kWMode) == 1;
        const float sens = get(kWSens);
        const float att = static_cast<float>(std::exp(-1.0 / (get(kWAttack) * 0.001 * sr_)));
        const float rel = static_cast<float>(std::exp(-1.0 / (get(kWRelease) * 0.001 * sr_)));
        for (int n = 0; n < frames; ++n) {
            const float p = pedal_.next();
            lo_.next();
            hi_.next();
            q_.next();
            body_.next();
            const float x0 = left[n], x1 = right[n];
            if (autoMode) {
                const float a = std::max(std::fabs(x0), std::fabs(x1));
                env_ = a > env_ ? a + (env_ - a) * att : a + (env_ - a) * rel;
            }
            if (ctl_ == 0 || lo_.moving() || hi_.moving() || q_.moving() || body_.moving()) {
                float pos = p;
                if (autoMode) {
                    const float db = 20.0f * std::log10(env_ + 1e-9f);
                    pos += sens * std::clamp((db + 46.0f) / 40.0f, 0.0f, 1.0f);
                }
                retune(pos);
                ctl_ = kRetune;
            }
            --ctl_;
            const float m = mix_.next(), g = gain_.next();
            left[n] = g * (x0 + m * (tick(s_[0], x0) - x0));
            right[n] = g * (x1 + m * (tick(s_[1], x1) - x1));
        }
        for (auto& st : s_) {
            st.ic1 = dsp::flush(st.ic1);
            st.ic2 = dsp::flush(st.ic2);
        }
        env_ = dsp::flush(env_);
        pos_ += static_cast<std::uint64_t>(frames);
    }

private:
    static constexpr double kPedalTau = 0.0024;   // ~8 ms 10-90 %
    static constexpr double kGainTau = 0.0015;
    static constexpr double kShapeTau = 0.0024;   // lo / hi / q / body glide like the pedal
    static constexpr int kRetune = 8;

    struct State {
        float ic1{0.0f}, ic2{0.0f};
    };

    // Re-tunes the filter for pedal position `pos` from the smoothed lo / hi (log Hz), q and body.
    void retune(float pos) noexcept {
        const double lo = lo_.value(), hi = std::max(static_cast<double>(hi_.value()), lo + 0.01);
        const double hz = std::exp(lo + (hi - lo) * std::clamp(static_cast<double>(pos), 0.0, 1.0));
        const double g = std::tan(dsp::kPi * std::min(hz, 0.45 * sr_) / sr_);
        const double q = std::max(1.0f, q_.value());
        const double k = 1.0 / q;
        a1_ = static_cast<float>(1.0 / (1.0 + g * (g + k)));
        a2_ = static_cast<float>(g) * a1_;
        a3_ = static_cast<float>(g) * a2_;
        k_ = static_cast<float>(k);
        body0_ = body_.value();
        // the resonance peaks at min(Q, 10)^0.6 (+9 dB at Q 5.5, like the pedal's own boost: a narrow sweep keeps
        // its level on a guitar); the body's low-pass (Q at the resonance, 90 degrees from the band-pass) included
        norm_ = static_cast<float>(std::pow(std::min(q, 10.0), 0.6) / std::sqrt(1.0 + (body0_ * q) * (body0_ * q)));
    }

    float tick(State& s, float x) const noexcept {
        const float v3 = x - s.ic2;
        const float v1 = a1_ * s.ic1 + a2_ * v3;
        const float v2 = s.ic2 + a2_ * s.ic1 + a3_ * v3;
        s.ic1 = 2.0f * v1 - s.ic1;
        s.ic2 = 2.0f * v2 - s.ic2;
        return norm_ * (k_ * v1 + body0_ * v2);   // band-pass (unity at the centre) + the low-pass body
    }

    Smooth2 pedal_, mix_, gain_, lo_, hi_, q_, body_;
    State s_[2];
    float env_{0.0f};
    float a1_{1.0f}, a2_{0.0f}, a3_{0.0f}, k_{0.2f}, norm_{1.0f}, body0_{0.25f};
    int ctl_{0};
};


}  // namespace

std::unique_ptr<Effect> makeWah() { return std::make_unique<Wah>(); }

}  // namespace as::timefx
