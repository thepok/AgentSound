// exciter: harmonic exciter (Aphex Aural Exciter / BBE idea): new harmonics are generated from the
// upper band of the signal and added back at a low level, for air and sparkle that EQ cannot add
// (EQ only lifts what is there; dull synths have nothing up there to lift).
//
//   x -> 4-pole high-pass at 'freq' -> 4x oversampled (polyphase IIR half-bands, fx/HalfBand.h)
//        harmonic generator -> 4-pole high-pass at 'freq' (removes DC and difference tones) -> x + side
//
// Generator: the band is scaled by 'drive' and, above full scale, by a gain that follows its
// envelope E, so the normalised band u stays within about +-1. E is the larger of a smooth RMS
// envelope (sqrt(2 x mean square), exact for steady tones, 50 Hz smoothing) and 0.9 x a fast peak
// follower (bounds transients). Harmonics come from the Chebyshev polynomials T2(u) = 2u^2 - 1 (even:
// warm) and T3(u) = 4u^3 - 3u (odd: crisp), with their DC / fundamental terms taken out through the
// envelope, rescaled back to the band level. Below full scale the harmonics grow with the level
// (2nd ~ level^2, 3rd ~ level^3) like a real curve; above it they keep a fixed ratio to the band.
// Polynomials of order <= 3 on a band-limited input produce nothing above 3 x 24 kHz, which the 4x
// rate (96 kHz Nyquist) holds without folding, so the result is alias-free by construction. The dry
// path is untouched: mix 0 or amount 0 is an exact bypass.

#include "fx/HalfBand.h"
#include "fx/PremiumUtil.h"

namespace as::premium {
namespace {

using namespace timefx;
using hb::D2;
using hb::d2;
using hb::HalfBand;

enum ExParam { kEFreq, kEDrive, kEAmount, kECharacter, kEMix };

const std::vector<ParamSpec>& exciterSpecs() {
    static const std::vector<ParamSpec> s = {
        num("freq", 500, 12000, 2500, "Hz",
            "Lowest frequency that drives the harmonic generator (and the high-pass on the added harmonics). The band "
            "above it must carry some signal: 800-1500 Hz for dull/filtered pads and basses, 2-4 kHz for air on leads, "
            "keys and mixes, 6+ kHz for top sheen only"),
        num("drive", 0, 60, 30, "dB",
            "Generator sensitivity: harmonics reach full strength for band peaks above -drive dBFS and fade below that "
            "(2nd ~ level^2); 20-30 = normal, 40+ = excites quiet detail and noise too"),
        num("amount", 0, 1, 0.4f, "",
            "Level of the added harmonics relative to the band above 'freq' (1 = about the band's own level): 0.2-0.4 "
            "subtle air, 0.5-0.7 obvious sparkle, 1 = sizzle"),
        num("character", 0, 1, 0.3f, "", "Harmonic colour: 0 = even (2nd, smooth/warm), 1 = odd (3rd, crisp/edgy)"),
        num("mix", 0, 1, 1, "", "Effect blend (scales the added harmonics; 0 = exact bypass)"),
    };
    return s;
}

class Exciter final : public ParamEffect {
    static constexpr int kN1 = 8, kN2 = 4;
    static constexpr float kSide = 1.0f;  // harmonic level at amount 1, relative to the band (loud regime)

public:
    Exciter() : ParamEffect(exciterSpecs(), "exciter") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        hb1_ = hb::designHalfBand<kN1>(0.05);
        hb2_ = hb::designHalfBand<kN2>(0.25);
        up1_.reset(); up2_.reset(); dn1_.reset(); dn2_.reset();
        ctrlK_ = ctrlCoeff(sr_, kCtrl, 0.003);
        freq_.snap(get(kEFreq));
        for (int c = 0; c < 2; ++c) {
            for (auto& f : bandHp_[c]) f = TptFilter(TptFilter::Mode::High);
            for (auto& f : postHp_[c]) f = TptFilter(TptFilter::Mode::High);
            ms1_[c] = ms2_[c] = 0.0;
            peak_[c] = 0.0f;
        }
        setFreq(0);
        msK_ = 1.0 - std::exp(-dsp::kTwoPi * 50.0 / sr_);
        rel_ = static_cast<float>(std::exp(-1.0 / (0.04 * sr_)));
        drive_.prepare(sr_, 0.0015, get(kEDrive));  // glides in dB
        char_.prepare(sr_, 0.0015, get(kECharacter));
        gain_.prepare(sr_, 0.0015, sideGain());
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) pullTargets();
        forEachCtrlBlock(pos_, frames, [&](int off, int n, bool tick) {
            if (tick && freq_.step(ctrlK_)) setFreq(kCtrl);
            float* L = left + off;
            float* R = right + off;
            for (int k = 0; k < n; ++k) {
                const float drvDb = drive_.next(), ch = char_.next(), g = gain_.next();
                if (drvDb != drvDb_) {
                    drvDb_ = drvDb;
                    drv_ = dsp::dbToGain(drvDb);
                }
                const float drv = drv_;
                float band[2], scale[2], env[2];
                for (int c = 0; c < 2; ++c) {
                    const float x = c ? R[k] : L[k];
                    const float b = bandHp_[c][1].process(bandHp_[c][0].process(x));
                    band[c] = b;
                    // envelope: max(RMS (exact for steady tones), 0.9 x peak (transients))
                    ms1_[c] = hb::flushD(ms1_[c] + msK_ * (static_cast<double>(b) * b - ms1_[c]));
                    ms2_[c] = hb::flushD(ms2_[c] + msK_ * (ms1_[c] - ms2_[c]));
                    const float a = std::fabs(b);
                    peak_[c] = a > peak_[c] ? a : dsp::flush(peak_[c] * rel_);
                    const float E = std::max(static_cast<float>(std::sqrt(2.0 * ms2_[c])), 0.9f * peak_[c]);
                    scale[c] = drv / std::max(1.0f, drv * E);  // band -> u
                    env[c] = E * scale[c];                     // envelope of u (<= 1)
                }
                D2 a0, a1, u[4];
                up1_.up(hb1_, d2(band[0], band[1]), a0, a1);
                up2_.up(hb2_, a0, u[0], u[1]);
                up2_.up(hb2_, a1, u[2], u[3]);
                D2 h[4];
                for (int i = 0; i < 4; ++i) {
                    float o[2];
                    for (int c = 0; c < 2; ++c) o[c] = harmonics(static_cast<float>(u[i][c]), scale[c], env[c], ch);
                    h[i] = d2(o[0], o[1]);
                }
                const D2 q0 = dn2_.down(hb2_, h[0], h[1]);
                const D2 q1 = dn2_.down(hb2_, h[2], h[3]);
                const D2 y = dn1_.down(hb1_, q0, q1);
                for (int c = 0; c < 2; ++c) {  // g == 0: x + 0 * side, an exact bypass
                    const float side = postHp_[c][1].process(postHp_[c][0].process(static_cast<float>(y[c])));
                    (c ? R : L)[k] += g * side;
                }
            }
        });
        up1_.flush(); up2_.flush(); dn1_.flush(); dn2_.flush();
    }

    double tailSeconds() const override { return 0.05; }

private:
    // One 4x sample of the generator: band sample b, its scale to u and the envelope e of u.
    static float harmonics(float b, float scale, float e, float character) noexcept {
        const float u = b * scale;
        const float t2 = 2.0f * u * u - e * e;                 // T2 without its DC (steady tone)
        const float t3 = 4.0f * u * u * u - 3.0f * e * e * u;  // T3 without its fundamental
        return ((1.0f - character) * t2 + character * t3) / scale;
    }
    float sideGain() const { return kSide * get(kEAmount) * get(kEMix); }
    void setFreq(int samples) {
        for (int c = 0; c < 2; ++c)
            for (int s = 0; s < 2; ++s) {
                bandHp_[c][s].setCutoff(sr_, freq_.v, samples);
                postHp_[c][s].setCutoff(sr_, freq_.v, samples);
            }
    }
    void pullTargets() {
        freq_.t = get(kEFreq);
        drive_.setTarget(get(kEDrive));
        char_.setTarget(get(kECharacter));
        gain_.setTarget(sideGain());
    }

    HalfBand<kN1>::Coefs hb1_{};
    HalfBand<kN2>::Coefs hb2_{};
    HalfBand<kN1> up1_, dn1_;
    HalfBand<kN2> up2_, dn2_;
    TptFilter bandHp_[2][2], postHp_[2][2];
    CtrlSmooth freq_;
    Smooth2 drive_, char_, gain_;
    float drvDb_{-1000.0f}, drv_{1.0f};
    double ms1_[2]{}, ms2_[2]{}, msK_{0.0};
    float peak_[2]{}, rel_{0.0f}, ctrlK_{0.0f};
};

}  // namespace

std::unique_ptr<Effect> makeExciter() { return std::make_unique<Exciter>(); }

}  // namespace as::premium
