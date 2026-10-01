// vowel: formant filter for choir / voice pads and talking leads.
//
// A parallel bank of resonant band-passes (the formants F1..F5 of a sung tenor vowel, from the classic
// FOF / CHANT singing-voice tables, plus a broad breath band) with alternating signs: between two
// adjacent formants one band-pass is above and the other below its centre, i.e. ~180 degrees apart,
// so equal signs would carve deep holes between the peaks; alternating signs make them add there
// like a vocal-tract (cascade) response does (Klatt's parallel formant synthesiser does the same).
// F1 is a resonant low-pass rather than a band-pass (same peak): below F1 a vocal tract passes the
// signal flat at about peak/Q, so the fundamental and low harmonics of low notes keep the body a
// real voice has there (a band-pass F1 would be ~10 dB thinner at 110 Hz).
//
// Formant gains are the tables' spectral peak levels plus 6 dB/oct: a saw falls at 6 dB/oct like the
// voice source (glottal pulse -12 dB/oct, lip radiation +6), so a saw pad comes out with the sung
// vowel's spectral envelope. The bank is normalised so a saw keeps its level for every vowel, size
// and resonance: on a spectrum falling 6 dB/oct the output power of the bank is proportional to
// sum(a_k^2 * B_k) (peak level a_k, bandwidth B_k), which is divided out continuously.
//
// Vowel position, size and resonance move the formants (log-frequency / log-bandwidth / dB
// interpolation between the vowel tables), smoothed at control rate and ramped per sample on
// trapezoidal state-variable filters (A. Simper), whose state stays valid under any modulation:
// vowel sweeps from modulators are smooth and click-free.

#include "fx/TimeFxUtil.h"

namespace as::timefx {
namespace {

enum VowelParam { kVVowel, kVMorph, kVGender, kVResonance, kVPresence, kVMix };

const std::vector<ParamSpec>& vowelSpecs() {
    static const std::vector<ParamSpec> s = {
        choice("vowel", {"a", "e", "i", "o", "u"}, 0,
               "Vowel (tenor formants): a = 'aah' (650/1080/2650 Hz), e = 'eh' (400/1700/2600), i = 'ee' "
               "(290/1870/2800), o = 'oh' (400/800/2600), u = 'ooh' (350/600/2700)"),
        num("morph", 0, 4, 0, "",
            "Moves the vowel continuously on from 'vowel' through a > e > i > o > u (> a again): 0 = 'vowel' itself, "
            "1 = the next vowel, 0.5 = halfway; with vowel a, 0..4 = a, e, i, o, u. Automate / modulate it for "
            "talking 'wah-yah' sweeps (smooth at any speed)"),
        num("gender", -1, 1, 0, "",
            "Formant shift = vocal-tract size: 0 = adult male (tenor), 0.4 = female, 0.8 = child, -0.3 = bass, "
            "-1 = giant (+-1 = +-6 semitones; the pitch of the input is unchanged)"),
        num("resonance", 0, 1, 0.5f, "",
            "Formant sharpness: 0.5 = natural voice bandwidths, 0.7-1 = narrower, ringing, whistling vowels, "
            "0-0.3 = broad, subtle vowel colouring (the level stays matched)"),
        num("presence", 0, 1, 0.5f, "",
            "Level of the upper formants (F3-F5, the 2.5-3.5 kHz 'singer's formant'): 0.5 = blended choir, "
            "1 = operatic soloist / cutting talking lead (+9 dB), 0 = dark, muffled (-9 dB)"),
        num("mix", 0, 1, 1, "",
            "Dry/wet: 1 = fully vowel-filtered (a saw pad becomes a choir 'aah'), 0.3-0.6 = vowel colour on top of "
            "the dry sound"),
    };
    return s;
}

constexpr int kFormants = 6;
constexpr int kVowelCount = 5;

struct FormantData {
    float hz, db, bw;  // centre, spectral peak level re F1 (dB), -3 dB bandwidth (Hz)
};
// Tenor formants F1..F5 (singing-voice tables used for FOF / CHANT synthesis): a, e, i, o, u; plus a
// broad, quiet breath band above them, so the top of the voice fades out instead of stopping dead at
// ~3.5 kHz (higher formants and aspiration in a real voice). The tables are a trained soloist's, with
// a strong 'singer's formant' (F3-F5 only 7-20 dB below F1); 'presence' scales F3 and up from there
// (default -9 dB: a blended choir).
constexpr FormantData kVowels[kVowelCount][kFormants] = {
    {{650, 0, 80}, {1080, -6, 90}, {2650, -7, 120}, {2900, -8, 130}, {3250, -22, 140}, {4700, -32, 1500}},
    {{400, 0, 70}, {1700, -14, 80}, {2600, -12, 100}, {3200, -14, 120}, {3580, -20, 120}, {4700, -32, 1500}},
    {{290, 0, 40}, {1870, -15, 90}, {2800, -18, 100}, {3250, -20, 120}, {3540, -30, 120}, {4900, -30, 1500}},
    {{400, 0, 40}, {800, -10, 80}, {2600, -12, 100}, {2800, -12, 120}, {3000, -26, 120}, {4500, -36, 1500}},
    {{350, 0, 40}, {600, -20, 60}, {2700, -17, 100}, {2900, -14, 120}, {3300, -26, 120}, {4500, -38, 1500}},
};
// Level trim per vowel (dB), measured on saw chords: the dark vowels pass a little less of a saw than
// the power estimate below predicts, so a vowel sweep would dip on 'oo'.
constexpr float kVowelTrimDb[kVowelCount] = {0.0f, 0.0f, 0.3f, 0.3f, 0.5f};
constexpr float kMinBandwidth = 40.0f;  // narrowest table bandwidth (tail estimate)
constexpr double kPresenceDb = 18.0;    // upper-formant level range: presence 0..1 = -18..0 dB re the table

// Level reference: the normalisation assumes a saw around this fundamental. A formant bank passes the
// harmonics that sit near the formants, so single notes vary by a few dB with pitch (chords average
// out: saw chords from 110 to 220 Hz stay within ~1 dB of their input level, see the tests).
constexpr double kRefF0 = 220.0;

// Automation smoothing of the formant shape (control rate, then per-sample coefficient ramps):
// ~5 ms 10-90 %, fast enough for talking sweeps from a modulator.
constexpr double kShapeTau = 0.002;
constexpr double kMixTau = 0.0015;

class Vowel final : public ParamEffect {
public:
    Vowel() : ParamEffect(vowelSpecs(), "vowel") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        ctrlK_ = ctrlCoeff(sr_, kCtrl, kShapeTau);
        where_.snap(position());
        size_.snap(get(kVGender));
        res_.snap(get(kVResonance));
        presence_.snap(get(kVPresence));
        mix_.prepare(sr_, kMixTau, get(kVMix));
        design(tgt_);
        for (int k = 0; k < kFormants; ++k) {
            cur_[k] = tgt_[k];
            step_[k] = {0.0f, 0.0f, 0.0f};
            update(k);
        }
        ramp_ = 0;
        for (auto& ch : ic1_) std::fill(std::begin(ch), std::end(ch), 0.0f);
        for (auto& ch : ic2_) std::fill(std::begin(ch), std::end(ch), 0.0f);
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) {
            where_.t = position();
            size_.t = get(kVGender);
            res_.t = get(kVResonance);
            presence_.t = get(kVPresence);
            mix_.setTarget(get(kVMix));
        }
        float* io[2] = {left, right};
        forEachCtrlBlock(pos_, frames, [&](int start, int len, bool tick) {
            if (tick) {
                const bool a = where_.step(ctrlK_), b = size_.step(ctrlK_), c = res_.step(ctrlK_);
                const bool d = presence_.step(ctrlK_);
                if (a || b || c || d) retarget();
            }
            for (int n = start; n < start + len; ++n) {
                if (ramp_ > 0) advanceRamp();
                const float m = mix_.next();
                for (int ch = 0; ch < 2; ++ch) {
                    const float x = io[ch][n];
                    float* s1 = ic1_[ch];
                    float* s2 = ic2_[ch];
                    float y = 0.0f;
                    for (int k = 0; k < kFormants; ++k) {  // TPT SVF: v1 band-pass, v2 low-pass
                        const float v3 = x - s2[k];
                        const float v1 = a1_[k] * s1[k] + a2_[k] * v3;
                        const float v2 = s2[k] + a2_[k] * s1[k] + a3_[k] * v3;
                        s1[k] = dsp::flush(2.0f * v1 - s1[k]);
                        s2[k] = dsp::flush(2.0f * v2 - s2[k]);
                        y += cur_[k].c * (k == 0 ? v2 : v1);
                    }
                    io[ch][n] = x + m * (y - x);
                }
            }
        });
    }

    // The narrowest formant rings longest: -60 dB after ln(1000) / (pi * B) seconds.
    double tailSeconds() const override {
        const double bw = kMinBandwidth * bandwidthScale(get(kVResonance)) * std::exp2(0.5 * get(kVGender));
        return 0.02 + 6.91 / (dsp::kPi * bw);
    }

private:
    struct Coef {
        float g{0.0f}, kd{1.0f}, c{0.0f};  // tan(pi f / sr), damping 1/Q, gain of the v1 (F1: v2) output
    };

    static double bandwidthScale(double resonance) noexcept { return std::exp2(2.0 - 4.0 * resonance); }
    // Unwrapped vowel position 0..8 (vowel index + morph); the table is read cyclically.
    float position() const { return static_cast<float>(getInt(kVVowel)) + get(kVMorph); }

    void design(Coef (&out)[kFormants]) const {
        const double p = std::fmod(static_cast<double>(where_.v), static_cast<double>(kVowelCount));
        const int i0 = std::clamp(static_cast<int>(p), 0, kVowelCount - 1), i1 = (i0 + 1) % kVowelCount;
        const double f = std::clamp(p - i0, 0.0, 1.0);
        const double scale = std::exp2(0.5 * size_.v);
        const double bwMul = bandwidthScale(res_.v) * scale;
        const double upperDb = kPresenceDb * (presence_.v - 1.0);  // F3 and up
        auto logLerp = [f](double a, double b) { return std::exp2(std::log2(a) + f * (std::log2(b) - std::log2(a))); };
        double hz[kFormants], bw[kFormants], amp[kFormants], power = 0.0;
        for (int k = 0; k < kFormants; ++k) {
            const FormantData& a = kVowels[i0][k];
            const FormantData& b = kVowels[i1][k];
            hz[k] = std::clamp(logLerp(a.hz, b.hz) * scale, 20.0, 0.45 * sr_);
            bw[k] = std::min(logLerp(a.bw, b.bw) * bwMul, 2.0 * hz[k]);
            amp[k] = std::pow(10.0, (a.db + f * (b.db - a.db) + (k >= 2 ? upperDb : 0.0)) / 20.0);
            power += amp[k] * amp[k] * bw[k];
        }
        // Saw of amplitude A at f0: harmonic power density A^2 f0 / (2 f^2); a band-pass of peak gain G
        // at f_k passes G^2 * density * (pi/2) B_k. With G_k = a_k f_k * norm the output power is
        // norm^2 A^2 f0 (pi/4) sum(a_k^2 B_k); the saw's own power is A^2 pi^2 / 12.
        // (+ a small empirical trim measured on saw chords: narrow formants catch a little less of a
        // harmonic spectrum than of a continuous one, small tracts a little more)
        const double vowelTrim = kVowelTrimDb[i0] + f * (kVowelTrimDb[i1] - kVowelTrimDb[i0]);
        const double trimDb = -0.6 + vowelTrim + 3.0 * (res_.v - 0.5) - 0.5 * size_.v;
        const double norm = std::sqrt(dsp::kPi / (3.0 * kRefF0 * power)) * std::pow(10.0, trimDb / 20.0);
        for (int k = 0; k < kFormants; ++k) {
            out[k].g = static_cast<float>(std::tan(dsp::kPi * hz[k] / sr_));
            out[k].kd = static_cast<float>(bw[k] / hz[k]);
            // unity-peak band-pass = kd * v1 (F1's low-pass: kd * v2), so the gain is G_k * kd = a_k * B_k * norm
            out[k].c = static_cast<float>((k % 2 ? -1.0 : 1.0) * amp[k] * bw[k] * norm);
        }
    }

    // New targets: every coefficient ramps linearly over the next control period.
    void retarget() {
        design(tgt_);
        const float inv = 1.0f / static_cast<float>(kCtrl);
        for (int k = 0; k < kFormants; ++k)
            step_[k] = {(tgt_[k].g - cur_[k].g) * inv, (tgt_[k].kd - cur_[k].kd) * inv, (tgt_[k].c - cur_[k].c) * inv};
        ramp_ = kCtrl;
    }
    void advanceRamp() noexcept {
        --ramp_;
        for (int k = 0; k < kFormants; ++k) {
            if (ramp_ == 0) {
                cur_[k] = tgt_[k];
            } else {
                cur_[k].g += step_[k].g;
                cur_[k].kd += step_[k].kd;
                cur_[k].c += step_[k].c;
            }
            update(k);
        }
    }
    void update(int k) noexcept {
        const float g = cur_[k].g;
        a1_[k] = 1.0f / (1.0f + g * (g + cur_[k].kd));
        a2_[k] = g * a1_[k];
        a3_[k] = g * a2_[k];
    }

    CtrlSmooth where_, size_, res_, presence_;
    Smooth2 mix_;
    float ctrlK_{0.0f};
    Coef cur_[kFormants]{}, tgt_[kFormants]{}, step_[kFormants]{};
    float a1_[kFormants]{}, a2_[kFormants]{}, a3_[kFormants]{};
    float ic1_[2][kFormants]{}, ic2_[2][kFormants]{};
    int ramp_{0};
};

}  // namespace

std::unique_ptr<Effect> makeVowel() { return std::make_unique<Vowel>(); }

}  // namespace as::timefx
