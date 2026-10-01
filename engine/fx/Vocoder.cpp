// vocoder (see Vocoder.h).
//
// Per sample:
//   modulator m = mono sum of the sidechain (the effect's own input when a host passes none)
//     -> level follower (gate G), voiced/unvoiced detector u (energy above 3 kHz vs below 1 kHz)
//   classic: m -> 'bands' complex gammatone band-passes (4 cascaded complex one-poles: the magnitude of the
//            analytic output is a ripple-free band envelope) -> attack/release followers -> x emphasis tilt
//            carrier (+ band-limited noise x u) -> the same bands on the carrier (two cascaded TPT band-passes,
//            centres shifted by 'shift', ramped per sample) -> x flatten gain (each band's carrier level pulled
//            towards the mean) -> x envelope -> summed with alternating signs (4th-order neighbours are ~180
//            degrees apart at their crossover), panned alternately by 'width'
//   lpc:     pre-emphasised m -> frequency-warped autocorrelation over an exponential window, computed
//            exactly and recursively (the all-pass chain of the windowed frame equals a damped chain on the
//            raw signal) -> smoothed by attack/release (a convex combination: stays positive definite)
//            -> Levinson every 32 samples -> reflection coefficients interpolated every 8 samples
//            carrier -> whitening A_c(z / flatten^(1/3)) (running order-8 LPC of the carrier) (+ noise x u)
//            -> de-emphasis (undoes the analysis pre-emphasis) -> emphasis shelf -> warp correction
//            sqrt(1-l^2)/(1-l z^-1) -> x gain -> warped all-pole 1/A(D(z)) (delay-free loop solved per sample);
//            'shift' re-warps D(z)
//   + sibilance: the modulator's highs (> 5 kHz) on unvoiced sounds; then mix / output.
// Level: a white modulator at kRef RMS reproduces the carrier (every band gain 1, both modes); speech at -18 dBFS
// active level keeps the carrier at about its own loudness.

#include "fx/Vocoder.h"

#include "dsp/Dsp.h"
#include "fx/TimeFxUtil.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace as {
namespace {

using timefx::CtrlSmooth;
using timefx::ParamEffect;
using timefx::Smooth2;
using timefx::ctrlCoeff;
using timefx::forEachCtrlBlock;
using timefx::kCtrl;

enum Param {
    kMode, kBands, kLo, kHi, kBandwidth, kAttack, kRelease, kShift, kEmphasis, kFlatten, kUnvoiced, kSibilance, kGate,
    kHold, kWidth, kOrder, kMix, kOutput
};

const std::vector<ParamSpec>& vocoderSpecs() {
    static const std::vector<ParamSpec> s = {
        choice("mode", {"classic", "lpc"}, 0,
               "classic = analog channel vocoder: 'bands' band-pass filters on the modulator open the same bands of the "
               "carrier (the Kraftwerk / Daft Punk robot; chords on the carrier = robot choir); lpc = talkbox: the "
               "modulator's vocal-tract resonances (running LPC) filter the carrier - smoother, most intelligible "
               "(Zapp, The Midnight)"),
        num("bands", 8, 40, 20, "",
            "classic: number of bands, log-spaced over lo..hi: 8-12 = lo-fi 70s robot, 16-24 = classic and intelligible, "
            "28-40 = smooth, almost natural",
            false),
        num("lo", 50, 1000, 100, "Hz", "classic: centre of the lowest band", false),
        num("hi", 2000, 16000, 8000, "Hz",
            "classic: centre of the highest band (speech has little above 8 kHz; 'unvoiced' and 'sibilance' add the air)",
            false),
        num("bandwidth", 0.5f, 2, 1, "",
            "classic: band width relative to the band spacing: 1 = neighbours cross at -3 dB, 0.5-0.7 = narrow, ringing, "
            "more robotic bands, 1.3-2 = broad, smooth, softer consonants"),
        num("attack", 0.5f, 100, 2, "ms",
            "How fast the vocoder opens on a syllable (envelope attack): 1-3 ms crisp consonants, 10-30 ms soft"),
        num("release", 5, 1000, 15, "ms",
            "How fast it closes (envelope release, also the gate and the glide out of 'hold'; lpc: at least ~16 ms, its "
            "analysis window): 8-25 ms intelligible speech, 60-300 ms smeared and pad-like, 500+ ms washes"),
        num("shift", -12, 12, 0, "st",
            "Formant shift: the carrier bands (classic) / the vocal tract (lpc) move against the analysis: -3..-6 = bigger, "
            "deeper robot, +3..+6 = smaller, cartoon voice; the pitch stays the carrier's notes"),
        num("emphasis", 0, 12, 4, "dB/oct",
            "Treble lift of the modulator above ~800 Hz before it shapes the carrier: 3-6 = clear and present, 8-12 = "
            "bright, whispery, 0 = dark, muffled"),
        num("flatten", 0, 1, 0.7f, "",
            "How much of the carrier's own spectral balance is evened out before the voice shapes it (classic: each "
            "band pulled towards the average band level, at most +-24 dB; lpc: running whitening filter), so the output "
            "follows the voice's spectrum: 0 = the carrier's timbre (a dark pad stays dark and mumbles), 0.7 = "
            "balanced, 1 = speech-like on any carrier"),
        num("unvoiced", 0, 1, 0.5f, "",
            "Noise mixed into the carrier while the modulator is unvoiced ('s', 'f', 't', 'sh': detected from its "
            "high/low energy ratio), so consonants stay intelligible even on dark carriers; 0 = off"),
        num("sibilance", 0, 1, 0.3f, "",
            "The modulator's own highs (above 5 kHz) passed through on unvoiced sounds: crisp 's' and 't' on top of the "
            "robot; 0 = off"),
        num("gate", -90, -20, -60, "dB",
            "Modulator level (dBFS) below which the vocoder closes: breaths and noise between words stay silent"),
        toggle("hold", false,
               "Freeze: on keeps the current spectrum (the vowel being sung) and sustains it on the carrier while the "
               "modulator goes on; off follows the modulator again (gliding there over 'release', also into silence). "
               "Automate it for robot 'aaah' holds at phrase ends"),
        num("width", 0, 1, 0.5f, "",
            "classic: stereo spread, alternate bands panned left / right (bands below ~150 Hz stay centred); 0 = the "
            "carrier's own stereo image"),
        num("order", 8, 40, 24, "",
            "lpc: prediction order (vocal-tract detail): 12-16 = smooth, soft formants, 24 = natural, 32-40 = sharp, "
            "may whistle",
            false),
        num("mix", 0, 1, 1, "", "Dry/wet: 1 = vocoder only, 0.1-0.3 = some of the plain carrier underneath"),
        num("output", -24, 24, 0, "dB",
            "Output level. The vocoder follows the carrier and the modulator: speech at -18 dBFS active level (what "
            "agentsound.speech writes) keeps the carrier at about its own loudness (+-2 LU)"),
    };
    return s;
}

constexpr int kMaxBands = 40;
constexpr int kMaxOrder = 40;
constexpr int kSub = 8;              // lpc: reflection-coefficient interpolation step (samples)
constexpr double kShapeTau = 0.002;  // shift / bandwidth / emphasis / width smoothing (control rate, ~7 ms 10-90 %)
constexpr double kGainTau = 0.0015;  // mix / output / unvoiced / sibilance (per sample)

// Levels: a white modulator of kRef RMS gives every band gain 1 (the carrier comes out unchanged).
// Calibrated with Windows TTS phrases (active speech level -18 dBFS) on saw chords, a dark pad, a lead and a bass:
// the vocoded output lands within +-2 LU of the dry carrier's integrated loudness in both modes.
constexpr double kRef = 0.46;
// Unvoiced noise RMS re the carrier RMS at unvoiced = 1 (classic loses more of it in the band gaps): at 0.5 the
// 's' / vowel balance of the output matches the voice's (measured on the same phrases).
constexpr double kNoiseClassic = 1.4;
constexpr double kNoiseLpc = 1.0;
constexpr double kSibHz = 7000.0;  // sibilance gets the emphasis lift of this frequency (matches the vocoded 's')

// Detectors.
constexpr double kLevelAttack = 0.002, kLevelRelease = 0.040;   // gate level follower (s)
constexpr double kVuTau = 0.006;                                // voiced/unvoiced band energies (s)
constexpr double kUAttack = 0.003, kURelease = 0.025;           // unvoiced amount smoothing (s)
constexpr double kCarrierAttack = 0.005, kCarrierRelease = 0.1; // carrier level follower (s)
constexpr double kGateKnee = 12.0;                              // dB: G rises 0 -> 1 over gate -6 .. gate +6 dB
constexpr double kMinGateFall = 0.005;                          // s: fastest gate closing (time constant)
// Carrier band levels for 'flatten' (s): fast up, so a band that suddenly gets louder (a new note, the unvoiced
// noise) is not boosted by the gain of its quiet past; slower down (no flutter on beating partials).
constexpr double kFlattenAttack = 0.0015, kFlattenRelease = 0.03;

// LPC analysis.
constexpr double kLpcWindow = 0.008;   // s: energy time constant of the exponential analysis window
constexpr double kPreEmph = 0.9;       // analysis pre-emphasis (1 - 0.9 z^-1: +6 dB/oct above ~800 Hz)
constexpr double kWarpMidHz = 3000.0;  // frequency the warped axis puts at its middle (Bark-like at 48 kHz)
constexpr double kLagWindow = 0.03;    // Gaussian lag window (warped radians): mild bandwidth expansion
constexpr double kNoiseFloor = 1e-4;   // white-noise correction (-40 dB)
constexpr double kMaxReflection = 0.995;
constexpr int kWhiten = 8;             // lpc 'flatten': order of the carrier whitening filter
constexpr double kWhitenWindow = 0.02; // s: its analysis window
constexpr double kTiltPivotHz = 800.0; // emphasis: lift above this
constexpr double kTiltTopHz = 8000.0;  // lpc shelf: the lift reaches emphasis x log2(10) dB here

inline float hashNoise(std::uint64_t x) noexcept {  // uniform [-1, 1): splitmix64 finaliser of a counter
    x += 0x9E3779B97F4A7C15ull;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ull;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBull;
    x ^= x >> 31;
    return static_cast<float>(static_cast<double>(x >> 40) * (2.0 / 16777216.0) - 1.0);
}

inline float coeff(double fs, double seconds) noexcept {  // one-pole smoothing coefficient (1 - exp(-1 / (tau fs)))
    return seconds <= 0.0 ? 1.0f : static_cast<float>(1.0 - std::exp(-1.0 / (seconds * fs)));
}

inline float smoothstep(float x) noexcept {
    x = std::clamp(x, 0.0f, 1.0f);
    return x * x * (3.0f - 2.0f * x);
}

// First-order TPT (trapezoidal) one-pole with low-pass and high-pass outputs; stable under modulation.
struct OnePoleTpt {
    float g{0.0f}, s{0.0f};
    void set(double fs, double hz) noexcept {
        const double t = std::tan(dsp::kPi * std::clamp(hz, 1.0, 0.49 * fs) / fs);
        g = static_cast<float>(t / (1.0 + t));
    }
    float lp(float x) noexcept {
        const float v = (x - s) * g;
        const float y = v + s;
        s = dsp::flush(y + v);
        return y;
    }
};

class Vocoder final : public ParamEffect {
public:
    Vocoder() : ParamEffect(vocoderSpecs(), "vocoder") {}

    void configure(const json& params) override {
        ParamEffect::configure(params);
        requireInteger("bands");
        requireInteger("order");
        // (the lo / hi ranges keep hi at least an octave above lo)
    }

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        fs_ = sr_;
        lpc_ = getInt(kMode) == 1;
        bands_ = getInt(kBands);
        order_ = getInt(kOrder);
        noiseSeed_ = ctx.seed * 0xD1B54A32D192ED03ull + 0x632BE59BD9B4E019ull;
        ctrlK_ = ctrlCoeff(fs_, kCtrl, kShapeTau);

        readParams();
        shift_.snap(get(kShift));
        bw_.snap(get(kBandwidth));
        emph_.snap(get(kEmphasis));
        width_.snap(get(kWidth));
        flat_.snap(get(kFlatten));
        sibLift_ = liftAt(kSibHz);
        mix_.prepare(fs_, kGainTau, get(kMix));
        out_.prepare(fs_, kGainTau, dsp::dbToGain(get(kOutput)));
        unv_.prepare(fs_, kGainTau, get(kUnvoiced));
        sib_.prepare(fs_, kGainTau, get(kSibilance));

        // detectors
        levelA_ = coeff(fs_, kLevelAttack);
        levelR_ = coeff(fs_, kLevelRelease);
        vuK_ = coeff(fs_, kVuTau);
        uA_ = ctrlCoeff(fs_, kCtrl, kUAttack);
        uR_ = ctrlCoeff(fs_, kCtrl, kURelease);
        carA_ = coeff(fs_, kCarrierAttack);
        carR_ = coeff(fs_, kCarrierRelease);
        for (int k = 0; k < 2; ++k) {
            lowDet_[k].set(dsp::Biquad::Type::LowPass, fs_, 1000.0, k ? 1.3066 : 0.5412);
            highDet_[k].set(dsp::Biquad::Type::HighPass, fs_, 3000.0, k ? 1.3066 : 0.5412);
            sibHp_[k].set(dsp::Biquad::Type::HighPass, fs_, 5000.0, k ? 1.3066 : 0.5412);
            // unvoiced noise: 1.5-11 kHz (4th-order edges), where fricatives live (speech has little above)
            for (int ch = 0; ch < 2; ++ch) {
                noiseHp_[ch][k].set(dsp::Biquad::Type::HighPass, fs_, 1500.0, k ? 1.3066 : 0.5412);
                noiseLp_[ch][k].set(dsp::Biquad::Type::LowPass, fs_, std::min(11000.0, 0.45 * fs_), k ? 1.3066 : 0.5412);
            }
        }
        level_ = eLow_ = eHigh_ = carrier_ = 0.0f;
        gateFrom_ = gateTo_ = 0.0f;
        uFrom_ = uTo_ = u_ = 0.0f;
        carFrom_ = carTo_ = 0.0f;
        hold_ = on(kHold);  // (a render held from its start: no release transition)
        unhold_ = 0;

        if (lpc_) prepareLpc();
        else prepareClassic();
        changed();
    }

    void process(float* left, float* right, int frames, const float* scLeft, const float* scRight) override {
        if (changed()) readParams();
        const bool keyed = scLeft != nullptr && scRight != nullptr;
        forEachCtrlBlock(pos_, frames, [&](int start, int len, bool tick) {
            const int phase = static_cast<int>(pos_ % kCtrl);
            if (tick) control();
            const float* kl = keyed ? scLeft + start : left + start;
            const float* kr = keyed ? scRight + start : right + start;
            if (lpc_) runLpc(left + start, right + start, kl, kr, len, phase);
            else runClassic(left + start, right + start, kl, kr, len, phase);
        });
    }

    double tailSeconds() const override { return 0.25 + 7.0 * 0.001 * get(kRelease); }

private:
    // ------------------------------------------------------------------------------------ parameters

    void readParams() {
        shift_.t = get(kShift);
        bw_.t = get(kBandwidth);
        emph_.t = get(kEmphasis);
        width_.t = get(kWidth);
        flat_.t = get(kFlatten);
        mix_.setTarget(get(kMix));
        out_.setTarget(dsp::dbToGain(get(kOutput)));
        unv_.setTarget(get(kUnvoiced));
        sib_.setTarget(get(kSibilance));
        gateDb_ = get(kGate);
        envCoefs();
        const bool hold = on(kHold);
        if (hold_ && !hold) unhold_ = unholdTicks_;  // hold released: glide from the frozen spectrum (see control())
        hold_ = hold;
    }

    void envCoefs() {
        att_ = coeff(fs_, 0.001 * get(kAttack));
        rel_ = coeff(fs_, 0.001 * get(kRelease));
        // lpc: the autocorrelation is a power (amplitude time constants halve) updated every kCtrl samples; the
        // analysis window already decays like a ~2 x kLpcWindow amplitude release
        attHop_ = ctrlCoeff(fs_, kCtrl, std::max(0.5e-3 * get(kAttack), 1e-5));
        relHop_ = ctrlCoeff(fs_, kCtrl, std::max(0.5 * (0.001 * get(kRelease) - 2.0 * kLpcWindow), 1e-5));
        // Falling gate and (lpc) the model right after 'hold' is released: the frozen spectrum may be far from the
        // modulator's current one (e.g. silence), so it decays with the release time (the analysis window at least)
        // instead of snapping there within one control period (an audible click on a held chord).
        gateFall_ = ctrlCoeff(fs_, kCtrl, std::max(0.001 * get(kRelease), kMinGateFall));
        const double tau = std::max(0.5e-3 * get(kRelease), kLpcWindow);
        relUnhold_ = ctrlCoeff(fs_, kCtrl, tau);
        unholdTicks_ = static_cast<int>(std::ceil(6.0 * tau * fs_ / kCtrl));
    }

    // Control rate (every kCtrl samples on the song grid): smoothed shape params, detector-derived gains.
    void control() {
        const bool a = shift_.step(ctrlK_), b = bw_.step(ctrlK_), c = emph_.step(ctrlK_), d = width_.step(ctrlK_);
        if (c) sibLift_ = liftAt(kSibHz);
        // gate: G rises from 0 to 1 over gate-6 .. gate+6 dB of the modulator level; exactly 0 in digital silence
        gateFrom_ = gateTo_;
        uFrom_ = uTo_;
        carFrom_ = carTo_;
        if (!hold_) {
            const float db = level_ > 1e-20f ? 10.0f * std::log10(level_) : -400.0f;
            float g = smoothstep((db - gateDb_) / static_cast<float>(kGateKnee) + 0.5f);
            if (g < gateTo_) {  // closing: never faster than the release (the level follower is slower anyway,
                                // except right after 'hold' or a 'gate' jump)
                g = std::max(g, gateTo_ + gateFall_ * (g - gateTo_));
                if (g < 1e-5f) g = 0.0f;
            }
            gateTo_ = g;
            // unvoiced: high-band share of the energy, 0 below 30 %, 1 above 65 %
            const float total = eLow_ + eHigh_;
            const float ratio = total > 1e-20f ? eHigh_ / total : 0.0f;
            const float target = smoothstep((ratio - 0.3f) / 0.35f) * (gateTo_ > 0.0f ? 1.0f : 0.0f);
            u_ += (target > u_ ? uA_ : uR_) * (target - u_);
            if (u_ < 1e-6f) u_ = 0.0f;
            uTo_ = u_;
        }
        carTo_ = std::sqrt(std::max(carrier_, 0.0f));
        if (lpc_) {
            if (a) lpcWarp();
            if (c) lpcTilt();
            lpcAnalyse();
            flat_.step(ctrlK_);
            whitenDesign();
        } else {
            if (a || b || c || d) retargetBands(false);
            flat_.step(ctrlK_);
            flattenGains();
        }
        if (unhold_ > 0) --unhold_;
    }

    // classic 'flatten': each band's carrier level (energy over the last control period, followed 1.5 ms up / 30 ms
    // down) is pulled towards the mean band level by (mean / level)^(flatten / 2), within +-24 dB; ramped over the
    // next period.
    void flattenGains() noexcept {
        const int n = bands_;
        if (bandCount_ > 0) {
            const float inv = 1.0f / (2.0f * static_cast<float>(bandCount_));
            for (int b = 0; b < n; ++b) {
                const float e = bandE_[b] * inv;
                bandLvl_[b] += (e > bandLvl_[b] ? flatA_ : flatR_) * (e - bandLvl_[b]);
                if (bandLvl_[b] < 1e-30f) bandLvl_[b] = 0.0f;
                bandE_[b] = 0.0f;
            }
            bandCount_ = 0;
        }
        double mean = 0.0;
        for (int b = 0; b < n; ++b) mean += bandLvl_[b];
        mean /= n;
        const float amount = flat_.v;
        for (int b = 0; b < n; ++b) {
            flatFrom_[b] = flatTo_[b];
            float f = 1.0f;
            if (amount > 0.0f && mean > 1e-24) {
                const double ratio = mean / std::max(static_cast<double>(bandLvl_[b]), mean * 1e-5);
                f = static_cast<float>(std::clamp(std::pow(ratio, 0.5 * amount), 1.0 / 16.0, 16.0));
            }
            flatTo_[b] = f;
        }
    }

    // Emphasis lift (linear gain) at `hz`: emphasis dB per octave above the pivot.
    float liftAt(double hz) const noexcept {
        return static_cast<float>(std::pow(10.0, emph_.v * std::max(0.0, std::log2(hz / kTiltPivotHz)) / 20.0));
    }

    // Per-sample detector update from the modulator sample m and the carrier (stereo) sample.
    void detect(float m, float cl, float cr) noexcept {
        const float m2 = m * m;
        level_ += (m2 > level_ ? levelA_ : levelR_) * (m2 - level_);
        const float lo = lowDet_[1].process(lowDet_[0].process(m));
        const float hi = highDet_[1].process(highDet_[0].process(m));
        eLow_ += vuK_ * (lo * lo - eLow_);
        eHigh_ += vuK_ * (hi * hi - eHigh_);
        const float c2 = 0.5f * (cl * cl + cr * cr);
        carrier_ += (c2 > carrier_ ? carA_ : carR_) * (c2 - carrier_);
    }

    // Band-limited noise for the unvoiced excitation: a hash of the song sample position (preview == full render).
    void noise(std::uint64_t at, float& nl, float& nr) noexcept {
        float out[2];
        for (int ch = 0; ch < 2; ++ch) {
            const float w = hashNoise(noiseSeed_ + 2 * at + static_cast<std::uint64_t>(ch));
            const float hp = noiseHp_[ch][1].process(noiseHp_[ch][0].process(w));
            out[ch] = noiseLp_[ch][1].process(noiseLp_[ch][0].process(hp));
        }
        nl = out[0];
        nr = out[1];
    }
    void flushDetectors() noexcept {
        if (level_ < 1e-30f) level_ = 0.0f;
        if (eLow_ < 1e-30f) eLow_ = 0.0f;
        if (eHigh_ < 1e-30f) eHigh_ = 0.0f;
        if (carrier_ < 1e-30f) carrier_ = 0.0f;
    }

    // ----------------------------------------------------------------------------------- classic

    void prepareClassic() {
        std::memset(zr_, 0, sizeof zr_);
        std::memset(zi_, 0, sizeof zi_);
        std::memset(env_, 0, sizeof env_);
        std::memset(bandE_, 0, sizeof bandE_);
        std::memset(bandLvl_, 0, sizeof bandLvl_);
        std::fill(std::begin(flatFrom_), std::end(flatFrom_), 1.0f);
        std::fill(std::begin(flatTo_), std::end(flatTo_), 1.0f);
        bandCount_ = 0;
        flatA_ = ctrlCoeff(fs_, kCtrl, kFlattenAttack);
        flatR_ = ctrlCoeff(fs_, kCtrl, kFlattenRelease);
        std::memset(s1a_, 0, sizeof s1a_);
        std::memset(s2a_, 0, sizeof s2a_);
        std::memset(s1b_, 0, sizeof s1b_);
        std::memset(s2b_, 0, sizeof s2b_);
        retargetBands(true);
    }

    // Designs both banks from the smoothed shift / bandwidth / emphasis / width. snap: jump there (prepare),
    // else ramp the synthesis coefficients and band weights linearly over the next control period.
    void retargetBands(bool snap) {
        const int n = bands_;
        const double lo = get(kLo), hi = get(kHi);
        const double spacing = std::log2(hi / lo) / (n - 1);                        // octaves between centres
        const double relBw = (std::exp2(0.5 * spacing) - std::exp2(-0.5 * spacing)) * bw_.v;  // -3 dB width / centre
        const double ratio = std::exp2(shift_.v / 12.0);
        const double q = std::pow(2.0, 0.25), qa = q - 1.0;
        for (int b = 0; b < n; ++b) {
            const double f = lo * std::exp2(spacing * b);
            // analysis: 4 cascaded complex one-poles (1 - r) / (1 - r e^{i w} z^-1), overall -3 dB width f * relBw
            const double half = std::min(dsp::kPi * f * relBw / fs_, 1.2);
            const double cd = q - std::cos(half);
            const double r = std::clamp((cd - std::sqrt(std::max(cd * cd - qa * qa, 0.0))) / qa, 0.05, 0.99999);
            const double w = dsp::kTwoPi * std::min(f, 0.45 * fs_) / fs_;
            aRe_[b] = static_cast<float>(r * std::cos(w));
            aIm_[b] = static_cast<float>(r * std::sin(w));
            aIn_[b] = static_cast<float>(1.0 - r);
            // white-noise power gain of the cascade: (1-r)^8 (1 + 9 r^2 + 9 r^4 + r^6) / (1 - r^2)^7
            const double r2 = r * r;
            const double power =
                std::pow(1.0 - r, 8) * (1.0 + 9.0 * r2 + 9.0 * r2 * r2 + r2 * r2 * r2) / std::pow(1.0 - r2, 7);
            // synthesis: two TPT band-passes at the shifted centre (overall -3 dB width f * relBw: stage width / 0.6436)
            const double fsyn = f * ratio;
            const double fc = std::min(fsyn, 0.45 * fs_);
            tg_[b] = static_cast<float>(std::tan(dsp::kPi * fc / fs_));
            tk_[b] = static_cast<float>(std::min(relBw / 0.6436, 3.0));
            // weight: envelope normalisation x emphasis tilt x fade of bands shifted past 0.45 fs; alternating signs
            const double tiltDb = emph_.v * std::max(0.0, std::log2(f / kTiltPivotHz));
            const double fade = std::clamp((0.45 * fs_ - fsyn) / (0.05 * fs_), 0.0, 1.0);
            const double weight = (b % 2 ? -1.0 : 1.0) * std::pow(10.0, tiltDb / 20.0) * fade / (kRef * std::sqrt(power));
            // stereo: alternate bands left / right, tapered to the centre below ~150 Hz
            const double taper = std::clamp((fsyn - 150.0) / 350.0, 0.0, 1.0);
            const double pan = (b % 2 ? 1.0 : -1.0) * width_.v * taper;
            twL_[b] = static_cast<float>(weight * std::sqrt(1.0 - pan));
            twR_[b] = static_cast<float>(weight * std::sqrt(1.0 + pan));
        }
        if (snap) {
            for (int b = 0; b < n; ++b) {
                g_[b] = tg_[b];
                kd_[b] = tk_[b];
                wL_[b] = twL_[b];
                wR_[b] = twR_[b];
                dg_[b] = dk_[b] = dwL_[b] = dwR_[b] = 0.0f;
                svf(b);
            }
            ramp_ = 0;
        } else {
            const float inv = 1.0f / static_cast<float>(kCtrl);
            for (int b = 0; b < n; ++b) {
                dg_[b] = (tg_[b] - g_[b]) * inv;
                dk_[b] = (tk_[b] - kd_[b]) * inv;
                dwL_[b] = (twL_[b] - wL_[b]) * inv;
                dwR_[b] = (twR_[b] - wR_[b]) * inv;
            }
            ramp_ = kCtrl;
        }
    }
    void svf(int b) noexcept {
        const float g = g_[b];
        a1_[b] = 1.0f / (1.0f + g * (g + kd_[b]));
        a2_[b] = g * a1_[b];
        a3_[b] = g * a2_[b];
    }
    void advanceRamp() noexcept {
        --ramp_;
        const int n = bands_;
        if (ramp_ == 0) {
            for (int b = 0; b < n; ++b) {
                g_[b] = tg_[b];
                kd_[b] = tk_[b];
                wL_[b] = twL_[b];
                wR_[b] = twR_[b];
            }
        } else {
            for (int b = 0; b < n; ++b) {
                g_[b] += dg_[b];
                kd_[b] += dk_[b];
                wL_[b] += dwL_[b];
                wR_[b] += dwR_[b];
            }
        }
        for (int b = 0; b < n; ++b) svf(b);
    }

    // One channel of the synthesis bank: returns sum_b band_b(x) * gain_b (gain = envelope x flatten x weight);
    // accumulates each band's carrier energy (for 'flatten').
    float synth(float x, float (&s1a)[kMaxBands], float (&s2a)[kMaxBands], float (&s1b)[kMaxBands], float (&s2b)[kMaxBands],
                const float* w, float* energy) noexcept {
        const int n = bands_;
        for (int b = 0; b < n; ++b) {
            float v3 = x - s2a[b];
            float v1 = a1_[b] * s1a[b] + a2_[b] * v3;
            float v2 = s2a[b] + a2_[b] * s1a[b] + a3_[b] * v3;
            s1a[b] = 2.0f * v1 - s1a[b];
            s2a[b] = 2.0f * v2 - s2a[b];
            const float y = kd_[b] * v1;
            v3 = y - s2b[b];
            v1 = a1_[b] * s1b[b] + a2_[b] * v3;
            v2 = s2b[b] + a2_[b] * s1b[b] + a3_[b] * v3;
            s1b[b] = 2.0f * v1 - s1b[b];
            s2b[b] = 2.0f * v2 - s2b[b];
            const float band = kd_[b] * v1;
            energy[b] += band * band;
            tmp_[b] = band * gain_[b] * w[b];
        }
        float acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};
        int b = 0;
        for (; b + 4 <= n; b += 4) {
            acc[0] += tmp_[b];
            acc[1] += tmp_[b + 1];
            acc[2] += tmp_[b + 2];
            acc[3] += tmp_[b + 3];
        }
        for (; b < n; ++b) acc[0] += tmp_[b];
        return (acc[0] + acc[2]) + (acc[1] + acc[3]);
    }

    void runClassic(float* L, float* R, const float* kl, const float* kr, int len, int phase) {
        const int n = bands_;
        const float inv = 1.0f / static_cast<float>(kCtrl);
        for (int i = 0; i < len; ++i) {
            const float ramp = static_cast<float>(phase + i + 1) * inv;  // position in the control period
            const float m = 0.5f * (kl[i] + kr[i]);
            const float dryL = L[i], dryR = R[i];
            detect(m, dryL, dryR);
            if (ramp_ > 0) advanceRamp();

            // analysis: complex gammatone bank -> band envelopes
            for (int b = 0; b < n; ++b) {
                const float pr = aRe_[b], pi = aIm_[b], gi = aIn_[b];
                float re = gi * m + pr * zr_[0][b] - pi * zi_[0][b];
                float im = pi * zr_[0][b] + pr * zi_[0][b];
                zr_[0][b] = re;
                zi_[0][b] = im;
                for (int s = 1; s < 4; ++s) {
                    const float r2 = gi * re + pr * zr_[s][b] - pi * zi_[s][b];
                    const float i2 = gi * im + pi * zr_[s][b] + pr * zi_[s][b];
                    zr_[s][b] = re = r2;
                    zi_[s][b] = im = i2;
                }
                amp_[b] = std::sqrt(re * re + im * im);
            }
            if (!hold_)
                for (int b = 0; b < n; ++b) env_[b] += (amp_[b] > env_[b] ? att_ : rel_) * (amp_[b] - env_[b]);
            for (int b = 0; b < n; ++b) gain_[b] = env_[b] * (flatFrom_[b] + (flatTo_[b] - flatFrom_[b]) * ramp);

            // carrier (+ noise while unvoiced) through the synthesis bank
            const float u = uFrom_ + (uTo_ - uFrom_) * ramp;
            const float car = carFrom_ + (carTo_ - carFrom_) * ramp;
            const float noise = static_cast<float>(kNoiseClassic * 1.7320508) * unv_.next() * u * car;
            float nl, nr;
            this->noise(pos_ + static_cast<std::uint64_t>(i), nl, nr);
            const float wetL = synth(dryL + noise * nl, s1a_[0], s2a_[0], s1b_[0], s2b_[0], wL_, bandE_);
            const float wetR = synth(dryR + noise * nr, s1a_[1], s2a_[1], s1b_[1], s2b_[1], wR_, bandE_);
            ++bandCount_;
            const float gate = gateFrom_ + (gateTo_ - gateFrom_) * ramp;
            const float sib = sibilance(m, u, gate, car);
            finish(L[i], R[i], dryL, dryR, gate * wetL + sib, gate * wetR + sib);
        }
        flushDetectors();
        for (int s = 0; s < 4; ++s)
            for (int b = 0; b < n; ++b) {
                if (std::fabs(zr_[s][b]) < 1e-20f) zr_[s][b] = 0.0f;
                if (std::fabs(zi_[s][b]) < 1e-20f) zi_[s][b] = 0.0f;
            }
        for (int b = 0; b < n; ++b) {
            if (env_[b] < 1e-20f) env_[b] = 0.0f;
            for (int ch = 0; ch < 2; ++ch) {
                s1a_[ch][b] = dsp::flush(s1a_[ch][b]);
                s2a_[ch][b] = dsp::flush(s2a_[ch][b]);
                s1b_[ch][b] = dsp::flush(s1b_[ch][b]);
                s2b_[ch][b] = dsp::flush(s2b_[ch][b]);
            }
        }
    }

    // The modulator's highs on unvoiced sounds, at the level the vocoded bands have there (a white carrier of RMS
    // `car` gives band level = modulator band level x car / kRef, lifted by the emphasis at ~7 kHz).
    float sibilance(float m, float u, float gate, float car) noexcept {
        const float hp = sibHp_[1].process(sibHp_[0].process(m));
        const float amount = sib_.next();
        if (amount <= 0.0f || u <= 0.0f) return 0.0f;
        return static_cast<float>(sibLift_ / kRef) * amount * u * gate * car * hp;
    }

    void finish(float& l, float& r, float dryL, float dryR, float wetL, float wetR) noexcept {
        const float mix = mix_.next(), g = out_.next() * mix, dry = 1.0f - mix;
        l = dry * dryL + g * wetL;
        r = dry * dryR + g * wetR;
    }

    // --------------------------------------------------------------------------------------- lpc

    void prepareLpc() {
        alpha_ = std::exp(-1.0 / (kLpcWindow * fs_));
        beta_ = std::sqrt(alpha_);
        const double t = std::tan(dsp::kPi * kWarpMidHz / fs_);
        lamA_ = (1.0 - t) / (1.0 + t);
        warpK_ = 1.0 / t;
        std::fill(std::begin(ast_), std::end(ast_), 0.0);
        std::fill(std::begin(r_), std::end(r_), 0.0);
        std::fill(std::begin(rs_), std::end(rs_), 0.0);
        std::fill(std::begin(kFrom_), std::end(kFrom_), 0.0);
        std::fill(std::begin(kTo_), std::end(kTo_), 0.0);
        std::fill(std::begin(a_), std::end(a_), 0.0);
        for (auto& ch : sst_) std::fill(std::begin(ch), std::end(ch), 0.0);
        std::fill(std::begin(vPrev_), std::end(vPrev_), 0.0);
        std::fill(std::begin(deEmph_), std::end(deEmph_), 0.0);
        preX_ = 0.0;
        gFrom_ = gTo_ = 0.0;
        cAlpha_ = std::exp(-1.0 / (kWhitenWindow * fs_));
        cBeta_ = std::sqrt(cAlpha_);
        std::fill(std::begin(rc_), std::end(rc_), 0.0);
        std::fill(std::begin(cHist_), std::end(cHist_), 0.0);
        for (auto& h : xHist_) std::fill(std::begin(h), std::end(h), 0.0f);
        std::fill(std::begin(wFrom_), std::end(wFrom_), 0.0f);
        std::fill(std::begin(wTo_), std::end(wTo_), 0.0f);
        wFrom_[0] = wTo_[0] = 1.0f;
        nFrom_ = nTo_ = 1.0f;
        for (int k = 0; k <= order_; ++k) lag_[k] = std::exp(-0.5 * (kLagWindow * k) * (kLagWindow * k));
        lpcWarp();
        lamFrom_ = lamCur_ = lamTo_;
        lpcTilt();
        for (auto& f : tilt_) f.s = 0.0f;
        tiltC_ = tiltCTo_;
        stepUp(0.0);
    }

    // Synthesis warp from the (smoothed) formant shift: tan(theta/2) = K tan(w/2); shifting the formants by
    // a ratio divides K.
    void lpcWarp() {
        const double ks = warpK_ / std::exp2(shift_.v / 12.0);
        lamTo_ = (ks - 1.0) / (ks + 1.0);
    }

    // Emphasis: a first-order shelf lifting everything above 800 Hz by up to emphasis x log2(10) dB at 8 kHz
    // (zero at 800 Hz, pole where the lift is reached); the analysis pre-emphasis is undone separately.
    void lpcTilt() {
        const double db = emph_.v * std::log2(kTiltTopHz / kTiltPivotHz);
        const double c = std::pow(10.0, db / 20.0);
        for (auto& f : tilt_) f.set(fs_, kTiltPivotHz * c);
        tiltCTo_ = static_cast<float>(c);
    }

    // Levinson-Durbin on the smoothed autocorrelation -> reflection coefficients and residual power.
    void lpcAnalyse() {
        const int p = order_;
        if (!hold_) {
            const double c = r_[0] > rs_[0] ? attHop_ : unhold_ > 0 ? std::min(relHop_, relUnhold_) : relHop_;
            for (int k = 0; k <= p; ++k) rs_[k] += c * (r_[k] - rs_[k]);
        }
        for (int k = 1; k <= p; ++k) kFrom_[k] = kTo_[k];
        gFrom_ = gTo_;
        lamFrom_ = lamCur_;
        if (hold_) return;
        double e = rs_[0] * (1.0 + kNoiseFloor);
        double a[kMaxOrder + 1] = {1.0};
        double tmp[kMaxOrder + 1];
        if (e <= 1e-24) {
            for (int k = 1; k <= p; ++k) kTo_[k] = 0.0;
            gTo_ = 0.0;
            return;
        }
        for (int m = 1; m <= p; ++m) {
            double acc = rs_[m] * lag_[m];
            for (int j = 1; j < m; ++j) acc += a[j] * rs_[m - j] * lag_[m - j];
            const double k = std::clamp(-acc / e, -kMaxReflection, kMaxReflection);
            kTo_[m] = k;
            for (int j = 1; j < m; ++j) tmp[j] = a[j] + k * a[m - j];
            for (int j = 1; j < m; ++j) a[j] = tmp[j];
            a[m] = k;
            e *= 1.0 - k * k;
        }
        gTo_ = std::sqrt(std::max(e, 0.0) * (1.0 - alpha_)) / kRef * gateTo_;
    }

    // lpc 'flatten': order-8 LPC of the carrier (exponential window, autocorrelation corrected by alpha^(k/2) so it
    // is that of a windowed signal: positive definite), inverse filter A(z / flatten) (0 = none, 1 = white), level kept.
    void whitenDesign() noexcept {
        for (int k = 0; k <= kWhiten; ++k) wFrom_[k] = wTo_[k];
        nFrom_ = nTo_;
        double r[kWhiten + 1];
        double sq = 1.0;
        for (int k = 0; k <= kWhiten; ++k) {
            r[k] = rc_[k] * sq;
            sq *= cBeta_;
        }
        const double gamma = std::cbrt(std::clamp(static_cast<double>(flat_.v), 0.0, 1.0));  // ~linear in dB
        double w[kWhiten + 1] = {1.0};
        if (gamma > 0.0 && r[0] > 1e-20) {
            double a[kWhiten + 1] = {1.0}, tmp[kWhiten + 1];
            double e = r[0] * (1.0 + 1e-6);
            for (int m = 1; m <= kWhiten; ++m) {
                double acc = r[m];
                for (int j = 1; j < m; ++j) acc += a[j] * r[m - j];
                const double k = std::clamp(-acc / e, -0.99, 0.99);
                for (int j = 1; j < m; ++j) tmp[j] = a[j] + k * a[m - j];
                for (int j = 1; j < m; ++j) a[j] = tmp[j];
                a[m] = k;
                e *= 1.0 - k * k;
            }
            double gk = 1.0;
            for (int k = 1; k <= kWhiten; ++k) {
                gk *= gamma;
                w[k] = a[k] * gk;
            }
        }
        double power = 0.0;  // output power of the filtered carrier: sum_ij w_i w_j r_|i-j|
        for (int i = 0; i <= kWhiten; ++i)
            for (int j = 0; j <= kWhiten; ++j) power += w[i] * w[j] * r[i > j ? i - j : j - i];
        for (int k = 0; k <= kWhiten; ++k) wTo_[k] = static_cast<float>(w[k]);
        nTo_ = power > 1e-24 && r[0] > 1e-24 ? static_cast<float>(std::min(std::sqrt(r[0] / power), 64.0)) : 1.0f;
    }

    // Reflection coefficients (interpolated kFrom -> kTo by f) to the direct form A(z) = 1 + sum a_k z^-k,
    // and the delay-free-loop denominator 1 + sum a_k (-lambda)^k of the warped filter.
    void stepUp(double f) noexcept {
        const int p = order_;
        double tmp[kMaxOrder + 1];
        a_[0] = 1.0;
        for (int m = 1; m <= p; ++m) {
            const double k = kFrom_[m] + (kTo_[m] - kFrom_[m]) * f;
            for (int j = 1; j < m; ++j) tmp[j] = a_[j] + k * a_[m - j];
            for (int j = 1; j < m; ++j) a_[j] = tmp[j];
            a_[m] = k;
        }
        lamCur_ = lamFrom_ + (lamTo_ - lamFrom_) * f;
        const double nl = -lamCur_;
        double pw = 1.0, den = 1.0;
        for (int k = 1; k <= p; ++k) {
            pw *= nl;
            den += a_[k] * pw;
        }
        den_ = den;
        csGain_ = std::sqrt(std::max(0.0, 1.0 - lamCur_ * lamCur_));
    }

    void runLpc(float* L, float* R, const float* kl, const float* kr, int len, int phase) {
        const int p = order_;
        const double lamA = lamA_, beta = beta_, lb = lamA_ * beta_, alpha = alpha_;
        const float inv = 1.0f / static_cast<float>(kCtrl);
        for (int i = 0; i < len; ++i) {
            const int ph = phase + i;
            const float ramp = static_cast<float>(ph + 1) * inv;
            if (ph % kSub == 0) stepUp(static_cast<double>(ph / kSub + 1) / (kCtrl / kSub));
            const float m = 0.5f * (kl[i] + kr[i]);
            const float dryL = L[i], dryR = R[i];
            detect(m, dryL, dryR);

            // analysis: warped autocorrelation of the exponentially windowed, pre-emphasised modulator
            const double x = static_cast<double>(m) - kPreEmph * preX_;
            preX_ = m;
            r_[0] = alpha * r_[0] + x * x;
            double in = x;
            for (int k = 1; k <= p; ++k) {
                const double out = -lamA * in + ast_[k];
                ast_[k] = beta * in + lb * out;
                r_[k] = alpha * r_[k] + x * out;
                in = out;
            }

            // carrier whitening ('flatten'): running order-8 LPC of the mono carrier, inverse filter A(z / flatten)
            const double cm = 0.5 * (static_cast<double>(dryL) + dryR);
            for (int k = kWhiten; k > 0; --k) cHist_[k] = cHist_[k - 1];
            cHist_[0] = cm;
            for (int k = 0; k <= kWhiten; ++k) rc_[k] = cAlpha_ * rc_[k] + cm * cHist_[k];
            float white[2];
            const float nrm = nFrom_ + (nTo_ - nFrom_) * ramp;
            const float dry[2] = {dryL, dryR};
            for (int ch = 0; ch < 2; ++ch) {
                float* h = xHist_[ch];
                for (int k = kWhiten; k > 0; --k) h[k] = h[k - 1];
                h[0] = dry[ch];
                float y = 0.0f;
                for (int k = 0; k <= kWhiten; ++k) y += (wFrom_[k] + (wTo_[k] - wFrom_[k]) * ramp) * h[k];
                white[ch] = y * nrm;
            }

            // synthesis: excitation -> de-emphasis -> shelf -> warp correction -> gain -> warped all-pole
            const float u = uFrom_ + (uTo_ - uFrom_) * ramp;
            const float car = carFrom_ + (carTo_ - carFrom_) * ramp;
            const float noise = static_cast<float>(kNoiseLpc * 1.7320508) * unv_.next() * u * car;
            float nl, nr;
            this->noise(pos_ + static_cast<std::uint64_t>(i), nl, nr);
            const double g = gFrom_ + (gTo_ - gFrom_) * ramp;
            tiltC_ += (tiltCTo_ - tiltC_) * 0.02f;
            const double lam = lamCur_;
            float wet[2];
            const float exc[2] = {white[0] + noise * nl, white[1] + noise * nr};
            for (int ch = 0; ch < 2; ++ch) {
                deEmph_[ch] = static_cast<double>(exc[ch]) + kPreEmph * deEmph_[ch];  // undoes the analysis pre-emphasis
                const float de = static_cast<float>(deEmph_[ch]);
                const float lp = tilt_[ch].lp(de);
                const float shelved = lp + tiltC_ * (de - lp);
                const double v = csGain_ * g * static_cast<double>(shelved) + lam * vPrev_[ch];
                vPrev_[ch] = v;
                double* st = sst_[ch];
                double c = 0.0, acc = 0.0;
                for (int k = 1; k <= p; ++k) {
                    c = -lam * c + st[k];
                    acc += a_[k] * c;
                }
                double y = (v - acc) / den_;
                if (!(std::fabs(y) < 1e4)) {  // never expected: reset rather than blow up
                    std::fill(st, st + kMaxOrder + 1, 0.0);
                    vPrev_[ch] = 0.0;
                    y = 0.0;
                }
                double uk = y;
                for (int k = 1; k <= p; ++k) {
                    const double next = -lam * uk + st[k];
                    st[k] = uk + lam * next;
                    uk = next;
                }
                wet[ch] = static_cast<float>(y);
            }
            const float gate = gateFrom_ + (gateTo_ - gateFrom_) * ramp;
            const float sib = sibilance(m, u, gate, car);
            finish(L[i], R[i], dryL, dryR, wet[0] + sib, wet[1] + sib);
        }
        flushDetectors();
        for (int k = 0; k <= p; ++k) {
            if (std::fabs(ast_[k]) < 1e-30) ast_[k] = 0.0;
            for (auto& ch : sst_)
                if (std::fabs(ch[k]) < 1e-30) ch[k] = 0.0;
        }
        for (double& v : vPrev_)
            if (std::fabs(v) < 1e-30) v = 0.0;
        for (double& v : deEmph_)
            if (std::fabs(v) < 1e-30) v = 0.0;
    }

    // ------------------------------------------------------------------------------------- state

    double fs_{48000.0};
    bool lpc_{false};
    bool hold_{false};
    int bands_{20};
    int order_{24};
    std::uint64_t noiseSeed_{0};
    float ctrlK_{0.0f};
    CtrlSmooth shift_, bw_, emph_, width_;
    Smooth2 mix_, out_, unv_, sib_;
    float att_{0.0f}, rel_{0.0f};
    double attHop_{0.0}, relHop_{0.0}, relUnhold_{0.0};
    float gateFall_{1.0f};
    int unhold_{0}, unholdTicks_{0};  // control periods left of the post-hold release glide
    float gateDb_{-60.0f};
    float sibLift_{1.0f};

    // detectors
    float levelA_{0.0f}, levelR_{0.0f}, vuK_{0.0f}, uA_{0.0f}, uR_{0.0f}, carA_{0.0f}, carR_{0.0f};
    float level_{0.0f}, eLow_{0.0f}, eHigh_{0.0f}, carrier_{0.0f};
    float gateFrom_{0.0f}, gateTo_{0.0f}, u_{0.0f}, uFrom_{0.0f}, uTo_{0.0f}, carFrom_{0.0f}, carTo_{0.0f};
    dsp::Biquad lowDet_[2], highDet_[2], sibHp_[2], noiseHp_[2][2], noiseLp_[2][2];

    // classic: analysis (complex one-pole cascade) and synthesis (two TPT band-passes per band and channel)
    float aRe_[kMaxBands]{}, aIm_[kMaxBands]{}, aIn_[kMaxBands]{};
    float zr_[4][kMaxBands]{}, zi_[4][kMaxBands]{};
    float amp_[kMaxBands]{}, env_[kMaxBands]{}, tmp_[kMaxBands]{};
    float g_[kMaxBands]{}, kd_[kMaxBands]{}, a1_[kMaxBands]{}, a2_[kMaxBands]{}, a3_[kMaxBands]{};
    float tg_[kMaxBands]{}, tk_[kMaxBands]{}, dg_[kMaxBands]{}, dk_[kMaxBands]{};
    float wL_[kMaxBands]{}, wR_[kMaxBands]{}, twL_[kMaxBands]{}, twR_[kMaxBands]{}, dwL_[kMaxBands]{}, dwR_[kMaxBands]{};
    float s1a_[2][kMaxBands]{}, s2a_[2][kMaxBands]{}, s1b_[2][kMaxBands]{}, s2b_[2][kMaxBands]{};
    int ramp_{0};
    float gain_[kMaxBands]{}, bandE_[kMaxBands]{}, bandLvl_[kMaxBands]{}, flatFrom_[kMaxBands]{}, flatTo_[kMaxBands]{};
    int bandCount_{0};
    float flatA_{0.0f}, flatR_{0.0f};
    CtrlSmooth flat_;

    // lpc
    double alpha_{0.0}, beta_{0.0}, lamA_{0.0}, warpK_{1.0};
    double lamFrom_{0.0}, lamTo_{0.0}, lamCur_{0.0}, den_{1.0}, csGain_{1.0};
    double preX_{0.0};
    double ast_[kMaxOrder + 1]{}, r_[kMaxOrder + 1]{}, rs_[kMaxOrder + 1]{}, lag_[kMaxOrder + 1]{};
    double kFrom_[kMaxOrder + 1]{}, kTo_[kMaxOrder + 1]{}, a_[kMaxOrder + 1]{};
    double sst_[2][kMaxOrder + 1]{}, vPrev_[2]{}, deEmph_[2]{};
    double gFrom_{0.0}, gTo_{0.0};
    double cAlpha_{0.0}, cBeta_{0.0}, rc_[kWhiten + 1]{}, cHist_[kWhiten + 1]{};
    float xHist_[2][kWhiten + 1]{}, wFrom_[kWhiten + 1]{}, wTo_[kWhiten + 1]{}, nFrom_{1.0f}, nTo_{1.0f};
    OnePoleTpt tilt_[2];
    float tiltC_{1.0f}, tiltCTo_{1.0f};
};

}  // namespace

std::unique_ptr<Effect> makeVocoder() { return std::make_unique<Vocoder>(); }

}  // namespace as
