#include "instruments/Dx7Synth.h"

#include "analysis/Fft.h"
#include "analysis/Loudness.h"
#include "core/TempoMap.h"
#include "dsp/Dsp.h"
#include "instruments/Dx7Banks.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

// MSFA headers go last: synth.h defines the macro `N` and global min/max templates.
#include "msfa/synth.h"
#include "msfa/controllers.h"
#include "msfa/dx7note.h"
#include "msfa/exp2.h"
#include "msfa/freqlut.h"
#include "msfa/lfo.h"
#include "msfa/sin.h"

namespace as {
namespace {

constexpr int kQ = 64;  // MSFA render quantum (samples per envelope/LFO tick)
static_assert(kQ == N, "MSFA quantum mismatch");

constexpr int kMinFadeSlots = 4;               // extra slots that fade out stolen voices (>= polyphony)
constexpr double kStealFadeSeconds = 0.004;
constexpr double kSafetyFadeSeconds = 0.050;   // fade applied when the release safety limit ends a voice
constexpr double kDcBlockHz = 10.0;            // output AC coupling (the DX7's analog stage has one too)
constexpr double kSilenceSeconds = 0.010;      // released voice this long below kSilenceLevel -> freed
constexpr double kReleaseSafetySeconds = 30.0; // patches whose release level L4 > 0 never decay (x 'release')
constexpr std::int32_t kSilencePeak = 512;     // in (msfa >> 4) units, 1 << 24 = full scale (~-90 dBFS)
constexpr float kFullScale = 1.0f / 16777216.0f;
constexpr float kSilenceLevel = static_cast<float>(kSilencePeak) * kFullScale;
constexpr double kQ24PerCent = 16777216.0 / 1200.0;  // MSFA log-frequency units (1 << 24 = octave)
// Automation smoothing (two cascaded one-poles at block rate, gains ramped per sample inside a block):
// C1-continuous, so fast steps stay click-free. 10-90 % = 3.36 x tau.
constexpr double kGainTau = 0.0015;  // level, pan, width, pitch bend: ~5 ms
constexpr double kToneTau = 0.002;   // mod wheel, brightness: ~7 ms
// Brightness tilt: high shelf 2.5 kHz (+6 .. -10 dB) and opposite low shelf 250 Hz (-/+2 dB), Q 0.5.
constexpr double kTiltK = 2.0;
constexpr double kTiltHighHz = 2500.0, kTiltLowHz = 250.0;

// Per-voice DC / infrasonic removal. FM with integer ratio pairs (1:1, 1:2, 0.5:1 ...) puts a sideband on
// 0 Hz, slightly detuned operators turn it into a few-Hz wobble, and stacked modulators add near-DC
// intermodulation (E.PIANO 1, SYNBRASS 1, MARIMBA, VOICE 1 ...); free-running sines that start or stop
// instantly (E.ORGAN 1) step as well. That component follows the note's envelope, so every note start and
// end is a DC step: summed and AC-coupled at the output it was a low thump (visible down to 30 Hz, a
// 50-250 Hz haze under dense arps). No filter on the sum can separate it from the other notes'
// fundamentals, but each voice knows where its own sound starts: a 4th-order Butterworth high-pass per
// voice (and doubled set) removes the voice's DC and the sub-note part of its steps before the voices are
// summed. Its cutoff is kVoiceHpfRatio x the note's lowest carrier (-0.02 dB there: the fundamental, or the
// sub-octave of 0.5-ratio patches), but at most kPartialGuard x the voice's lowest significant partial
// (measured once per patch: sidebands below the carriers, e.g. GUITAR 2's fundamental under a ratio-3
// carrier or MARIMBA's quarter-ratio partial, keep within 0.25 dB). Below the cutoff: -24 dB an octave
// down, -48 dB two octaves down. Cutoffs follow the pitch EG's deepest level and downward pitch bend.
constexpr double kVoiceHpfRatio = 0.5;
constexpr double kPartialGuard = 0.7;
constexpr double kPartialFloorDb = -33.0;  // "significant": within this of the strongest spectral peak
constexpr double kPartialMinRatio = 0.1;   // components below 0.1 x key are DC / infrasonic products
constexpr double kVoiceHpfMinHz = 5.0;
constexpr int kCarrierLevelSpan = 30;  // carriers > 30 output-level steps (~22 dB) below the loudest are ignored
constexpr int kHpfSections = 2;
constexpr double kHpfBendTau = 0.02;  // the cutoffs follow downward pitch bends with this time constant
constexpr std::array<double, kHpfSections> kHpfK = {1.8477590650225735, 0.7653668647301796};  // 1/Q

// Auto level: every patch is calibrated once (at kCalRate, cached per patch) by rendering a standard
// phrase (kCalPhrase: a held middle C, a melody of quarter and eighth notes in C5-A5 and a 4-note chord
// around C4, velocity 100/84) through the per-voice high-pass and measuring its K-weighted, gated loudness
// (BS.1770). The gain brings that phrase to kAutoLevelTargetLufs (mono = centre-panned stereo) ...
constexpr double kAutoLevelTargetLufs = -22.0;
// ...unless that would put the held note's peak above this (percussive, high-crest patches such as CLAV 2
// or HARPSICH 3 would otherwise make 4-note chords peak near 0 dBFS).
constexpr double kAutoLevelPeakTarget = 0.355;  // -9 dB -> -12 dBFS per channel after centre pan
constexpr double kAutoLevelMinGain = 0.25;  // -12 dB
constexpr double kAutoLevelMaxGain = 5.62;  // +15 dB
constexpr double kCalRate = 48000.0;
constexpr double kCalMaxRelease = 1.5;  // seconds a released calibration note may ring on

using Patch = dx7::UnpackedVoice;

// Operator routing flags of the 32 algorithms, in patch order (index 0 = OP6), as in msfa/fm_core.cc.
// Output bus 0 (low two bits clear) = carrier.
constexpr std::uint8_t kAlgorithmFlags[32][6] = {
    {0xc1, 0x11, 0x11, 0x14, 0x01, 0x14}, {0x01, 0x11, 0x11, 0x14, 0xc1, 0x14}, {0xc1, 0x11, 0x14, 0x01, 0x11, 0x14},
    {0xc1, 0x11, 0x94, 0x01, 0x11, 0x14}, {0xc1, 0x14, 0x01, 0x14, 0x01, 0x14}, {0xc1, 0x94, 0x01, 0x14, 0x01, 0x14},
    {0xc1, 0x11, 0x05, 0x14, 0x01, 0x14}, {0x01, 0x11, 0xc5, 0x14, 0x01, 0x14}, {0x01, 0x11, 0x05, 0x14, 0xc1, 0x14},
    {0x01, 0x05, 0x14, 0xc1, 0x11, 0x14}, {0xc1, 0x05, 0x14, 0x01, 0x11, 0x14}, {0x01, 0x05, 0x05, 0x14, 0xc1, 0x14},
    {0xc1, 0x05, 0x05, 0x14, 0x01, 0x14}, {0xc1, 0x05, 0x11, 0x14, 0x01, 0x14}, {0x01, 0x05, 0x11, 0x14, 0xc1, 0x14},
    {0xc1, 0x11, 0x02, 0x25, 0x05, 0x14}, {0x01, 0x11, 0x02, 0x25, 0xc5, 0x14}, {0x01, 0x11, 0x11, 0xc5, 0x05, 0x14},
    {0xc1, 0x14, 0x14, 0x01, 0x11, 0x14}, {0x01, 0x05, 0x14, 0xc1, 0x14, 0x14}, {0x01, 0x14, 0x14, 0xc1, 0x14, 0x14},
    {0xc1, 0x14, 0x14, 0x14, 0x01, 0x14}, {0xc1, 0x14, 0x14, 0x01, 0x14, 0x04}, {0xc1, 0x14, 0x14, 0x14, 0x04, 0x04},
    {0xc1, 0x14, 0x14, 0x04, 0x04, 0x04}, {0xc1, 0x05, 0x14, 0x01, 0x14, 0x04}, {0x01, 0x05, 0x14, 0xc1, 0x14, 0x04},
    {0x04, 0xc1, 0x11, 0x14, 0x01, 0x14}, {0xc1, 0x14, 0x01, 0x14, 0x04, 0x04}, {0x04, 0xc1, 0x11, 0x14, 0x04, 0x04},
    {0xc1, 0x14, 0x04, 0x04, 0x04, 0x04}, {0xc4, 0x04, 0x04, 0x04, 0x04, 0x04},
};

// Pitch EG level -> pitch offset in 1/32 octave (msfa/pitchenv.cc pitchenv_tab).
constexpr std::int8_t kPitchEnvTab[100] = {
    -128, -116, -104, -95, -85, -76, -68, -61, -56, -52, -49, -46, -43, -41, -39, -37, -35, -33, -32, -31, -30, -29,
    -28,  -27,  -26,  -25, -24, -23, -22, -21, -20, -19, -18, -17, -16, -15, -14, -13, -12, -11, -10, -9,  -8,  -7,
    -6,   -5,   -4,   -3,  -2,  -1,  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,   10,  11,  12,  13,  14,  15,
    16,   17,   18,   19,  20,  21,  22,  23,  24,  25,  26,  27,  28,  29,  30,  31,  32,  33,  34,  35,  38,  40,
    43,   46,   49,   53,  58,  65,  73,  82,  92,  103, 115, 127};

// Lowest audible carrier (Hz) of a note: ratio carriers at ratio x key, fixed ones at their frequency.
double lowestCarrierHz(const Patch& p, int note) {
    const double keyHz = dsp::midiToHz(note);
    const auto& flags = kAlgorithmFlags[std::min<int>(p[134], 31)];
    int loudest = 0;
    for (int op = 0; op < 6; ++op) {
        if ((flags[op] & 3) == 0) loudest = std::max<int>(loudest, p[op * 21 + 16]);
    }
    double base = 0.0;
    for (int op = 0; op < 6; ++op) {
        const int off = op * 21, level = p[off + 16];
        if ((flags[op] & 3) != 0 || level <= 0 || level < loudest - kCarrierLevelSpan) continue;
        const int coarse = p[off + 18], fine = p[off + 19];
        const double hz = p[off + 17] == 0 ? keyHz * (coarse == 0 ? 0.5 : coarse) * (1.0 + fine * 0.01)
                                           : std::pow(10.0, (coarse & 3) + fine * 0.01);
        base = base > 0.0 ? std::min(base, hz) : hz;
    }
    return base > 0.0 ? base : keyHz;  // no audible carrier (silent patch)
}

// Prewarped cutoff coefficient g = tan(pi fc / rate) of a note's DC high-pass (see kVoiceHpfRatio);
// `lowestPartial` in key units (measureLowestPartial).
double voiceHpfG(const Patch& p, int note, double lowestPartial, double rate) {
    double fc = std::min(kVoiceHpfRatio * lowestCarrierHz(p, note), kPartialGuard * lowestPartial * dsp::midiToHz(note));
    const int deepest = std::min({p[130], p[131], p[132], p[133]});  // pitch EG may take the note lower
    if (kPitchEnvTab[deepest] < 0) fc *= std::exp2(kPitchEnvTab[deepest] / 32.0);
    fc = std::clamp(fc, kVoiceHpfMinHz, 0.1 * rate);
    return std::tan(dsp::kPi * fc / rate);
}

// Per-voice high-pass: cascaded linear TPT state-variable filters (A. Simper) in double precision (the
// cutoff can be < 1e-4 of the internal rate). Coefficients change smoothly with the cutoff (pitch bend).
struct HpfCoef {
    double a1{1.0}, a2{0.0}, a3{0.0};
};
struct HpfState {
    double ic1{0.0}, ic2{0.0};
};
using HpfCoefs = std::array<HpfCoef, kHpfSections>;
using HpfStates = std::array<HpfState, kHpfSections>;

void hpfTune(double g, HpfCoefs& c) noexcept {
    for (int s = 0; s < kHpfSections; ++s) {
        c[s].a1 = 1.0 / (1.0 + g * (g + kHpfK[s]));
        c[s].a2 = g * c[s].a1;
        c[s].a3 = g * c[s].a2;
    }
}

inline double hpfTick(double x, const HpfCoefs& c, HpfStates& st) noexcept {
    for (int s = 0; s < kHpfSections; ++s) {
        HpfState& z = st[s];
        const double v3 = x - z.ic2;
        const double v1 = c[s].a1 * z.ic1 + c[s].a2 * v3;
        const double v2 = z.ic2 + c[s].a2 * z.ic1 + c[s].a3 * v3;
        z.ic1 = 2.0 * v1 - z.ic1;
        z.ic2 = 2.0 * v2 - z.ic2;
        x = x - kHpfK[s] * v1 - v2;
    }
    return x;
}

void hpfFlush(HpfStates& st) noexcept {
    for (auto& z : st) {
        if (std::fabs(z.ic1) < 1e-30) z.ic1 = 0.0;
        if (std::fabs(z.ic2) < 1e-30) z.ic2 = 0.0;
    }
}

// Envelope time scaling. A DX7 EG rate r (0..99) runs at qrate = (r * 41 >> 6) + keyboard rate scaling
// (max 63), and every 4 qrate steps double the speed. A time multiplier m is a qrate offset of
// -4 log2(m); it is applied by rewriting the patch rate so the resulting qrate (after rate scaling and
// the 63 cap) lands on the target, which also scales the hold times of flat segments.
constexpr int envQrate(int rate) { return (rate * 41) >> 6; }

constexpr std::array<std::uint8_t, 64> makeInverseQrate() {
    std::array<std::uint8_t, 64> inv{};
    for (int r = 99; r >= 0; --r) inv[static_cast<std::size_t>(envQrate(r))] = static_cast<std::uint8_t>(r);
    return inv;
}
constexpr std::array<std::uint8_t, 64> kInverseQrate = makeInverseQrate();  // smallest rate per qrate

int keyRateScaling(int note, int sensitivity) {  // msfa ScaleRate()
    return (sensitivity * std::clamp(note / 3 - 7, 0, 31)) >> 3;
}

int qrateOffset(float multiplier) {  // > 0 = faster
    return -static_cast<int>(std::lround(4.0 * std::log2(std::max(multiplier, 1e-3f))));
}

int scaleRate(int rate, int rateScaling, int dq) {
    if (dq == 0) return rate;
    const int q = envQrate(rate);
    int target = std::clamp(std::min(63, q + rateScaling) + dq - rateScaling, 0, 63);
    target = dq > 0 ? std::max(target, q) : std::min(target, q);  // never the wrong way (63 cap)
    return target == q ? rate : kInverseQrate[static_cast<std::size_t>(target)];
}

struct EnvScale {
    int attack{0}, decay{0}, release{0};  // qrate offsets
    bool identity() const noexcept { return attack == 0 && decay == 0 && release == 0; }
};

// The patch with every operator's R1 (attack), R2/R3 (decay) and R4 (release) rescaled for `note`.
Patch scaledPatch(const Patch& base, int note, const EnvScale& e) {
    Patch p = base;
    if (e.identity()) return p;
    for (int op = 0; op < 6; ++op) {
        const int off = op * 21;
        const int rs = keyRateScaling(note, base[off + 13]);
        p[off + 0] = static_cast<std::uint8_t>(scaleRate(base[off + 0], rs, e.attack));
        p[off + 1] = static_cast<std::uint8_t>(scaleRate(base[off + 1], rs, e.decay));
        p[off + 2] = static_cast<std::uint8_t>(scaleRate(base[off + 2], rs, e.decay));
        p[off + 3] = static_cast<std::uint8_t>(scaleRate(base[off + 3], rs, e.release));
    }
    return p;
}

// MSFA keeps its lookup tables in globals that depend on the sample rate. Rendering is
// single-threaded, so each instance simply re-initialises them when its (internal) rate differs
// from the one currently loaded; with a shared rate this is a no-op compare.
double gMsfaRate = 0.0;
bool gMsfaStaticInit = false;

void ensureMsfaTables(double rate) {
    if (!gMsfaStaticInit) {
        Exp2::init();
        Tanh::init();
        Sin::init();
        gMsfaStaticInit = true;
    }
    if (rate != gMsfaRate) {
        Freqlut::init(rate);
        Lfo::init(rate);
        PitchEnv::init(rate);
        Env::init_sr(rate);
        gMsfaRate = rate;
    }
}

// 2:1 decimator: polyphase IIR half-band, two parallel chains of first-order allpass sections in z^-2
// (Valenzuela & Constantinides), coefficients from Laurent de Soras' HIIR design procedure.
// kHalfband2x (120 dB, transition 0.02 fs_in): flat pass band to 0.23 fs_in (22 kHz at 48 kHz out),
// aliases from above 0.26 fs_in rejected by > 120 dB. kHalfband4x (first stage of 4x, transition
// 0.125): only has to reject what would fold below 0.125 fs_in (> 130 dB). Group delay ~1.9 output
// samples at low/mid frequencies; a linear-phase FIR of equal quality would add ~20 samples.
constexpr std::array<double, 12> kHalfband2x = {
    0.027155856726483182, 0.10300238556004077, 0.21303004592041422, 0.33933626891036295,
    0.46602752012040527,  0.58224701385700428, 0.68259076485235193, 0.76595528238687738,
    0.83396924102510472,  0.88969265368750716, 0.93680311116581549, 0.97923872973422221};
constexpr std::array<double, 7> kHalfband4x = {
    0.025297819489407972, 0.097760856478586816, 0.20859350128275564, 0.34732425726670929,
    0.50599695798948208,  0.68265586184492222,  0.88427503941619989};

// DC / infrasonic safety net on the output: 2nd-order Butterworth high-pass at kDcBlockHz (RBJ, direct
// form I in double because fc/fs is tiny), like the DX7's AC-coupled analog output stage. The voices'
// own DC is already removed per voice (see kVoiceHpfRatio); this catches what is left.
// -0.25 dB at 20.6 Hz (E1 with a 0.5-ratio carrier), -28 dB at 2 Hz.
class DcBlocker {
public:
    void prepare(double sampleRate) noexcept {
        const double w = dsp::kTwoPi * kDcBlockHz / sampleRate;
        const double alpha = std::sin(w) / (2.0 * 0.70710678118654752);
        const double cw = std::cos(w), a0 = 1.0 + alpha;
        b0_ = (1.0 + cw) * 0.5 / a0;
        b1_ = -(1.0 + cw) / a0;
        a1_ = -2.0 * cw / a0;
        a2_ = (1.0 - alpha) / a0;
        x1_ = x2_ = y1_ = y2_ = 0.0;
    }
    double process(double x) noexcept {
        double y = b0_ * (x + x2_) + b1_ * x1_ - a1_ * y1_ - a2_ * y2_;  // b2 == b0
        if (std::fabs(y) < 1e-30) y = 0.0;
        x2_ = x1_;
        x1_ = x;
        y2_ = y1_;
        y1_ = y;
        return y;
    }
    // True once the filter's own tail (the removed DC swinging back after the voices stopped) is inaudible.
    bool settled() const noexcept {
        return std::fabs(x1_) + std::fabs(x2_) + std::fabs(y1_) + std::fabs(y2_) < 1e-6;
    }

private:
    double b0_{1.0}, b1_{0.0}, a1_{0.0}, a2_{0.0};
    double x1_{0.0}, x2_{0.0}, y1_{0.0}, y2_{0.0};
};

// Linear TPT state-variable filter (A. Simper) with a fixed tuning, used for the brightness tilt: the
// shelf gain lives only in the output mix (m0 x + m1 band + m2 low), so brightness automation never
// disturbs the filter state and is click-free at any speed (a biquad whose coefficients follow the
// gain thumps on every update, most audibly the 250 Hz shelf).
class TiltSvf {
public:
    void tune(double sampleRate, double hz, double k) noexcept {
        const double g = std::tan(dsp::kPi * hz / sampleRate);
        a1_ = static_cast<float>(1.0 / (1.0 + g * (g + k)));
        a2_ = static_cast<float>(g) * a1_;
        a3_ = static_cast<float>(g) * a2_;
    }
    void reset() noexcept { ic1_ = ic2_ = 0.0f; }
    void flush() noexcept { ic1_ = dsp::flush(ic1_); ic2_ = dsp::flush(ic2_); }
    // band (v1) and low (v2) outputs for input v0
    void tick(float v0, float& v1, float& v2) noexcept {
        const float v3 = v0 - ic2_;
        v1 = a1_ * ic1_ + a2_ * v3;
        v2 = ic2_ + a2_ * ic1_ + a3_ * v3;
        ic1_ = 2.0f * v1 - ic1_;
        ic2_ = 2.0f * v2 - ic2_;
    }

private:
    float a1_{1.0f}, a2_{0.0f}, a3_{0.0f}, ic1_{0.0f}, ic2_{0.0f};
};

class HalfbandDecimator {
public:
    template <std::size_t kCount>
    void init(const std::array<double, kCount>& coefs) noexcept {
        static_assert(kCount <= kMaxCoefs);
        coef_ = coefs.data();
        count_ = static_cast<int>(kCount);
        xm_.fill(0.0);
        ym_.fill(0.0);
    }

    // in[0 .. 2*nOut) -> out[0 .. nOut); may run in place (out == in).
    void process(const float* in, float* out, int nOut) noexcept {
        for (int m = 0; m < nOut; ++m) {
            double path[2] = {in[2 * m + 1], in[2 * m]};  // even coefficients take the newer sample
            for (int k = 0; k < count_; ++k) {
                double& x = path[k & 1];
                const double y = (x - ym_[k]) * coef_[k] + xm_[k];  // y[n] = c (x[n] - y[n-1]) + x[n-1]
                xm_[k] = x;
                ym_[k] = std::fabs(y) < 1e-30 ? 0.0 : y;             // no denormals in the recursion
                x = ym_[k];
            }
            out[m] = static_cast<float>(0.5 * (path[0] + path[1]));
        }
    }

private:
    static constexpr std::size_t kMaxCoefs = 12;
    const double* coef_{kHalfband2x.data()};
    int count_{0};
    std::array<double, kMaxCoefs> xm_{};
    std::array<double, kMaxCoefs> ym_{};
};

enum Param { kLevel, kPan, kTranspose, kPolyphony, kPitchbend, kModwheel, kDetune, kWidth, kBrightness, kVelsens,
             kOversample, kAutolevel, kAttack, kDecay, kRelease };

std::vector<ParamSpec> makeSpecs() {
    return {
        num("level", -60.0f, 12.0f, 0.0f, "dB",
            "Output level. With autolevel on, at 0 dB any voice plays a typical melody at about -23 LUFS and "
            "whole-bar 4-note chords at about -20.5 LUFS (centred), a single note peaks <= -12 dBFS; lower it for "
            "dense 8+ note detuned pads, which can peak near 0 dBFS."),
        num("pan", -1.0f, 1.0f, 0.0f, "",
            "Stereo position -1 (left) .. 1 (right); with detune > 0 it moves the whole doubled image."),
        num("transpose", -36.0f, 36.0f, 0.0f, "st",
            "Whole semitones added to every note, on top of the patch's own transpose.", false),
        num("polyphony", 1.0f, 32.0f, 16.0f, "voices",
            "Max simultaneous notes (DX7: 16). 1 = mono. When full, the oldest released (else oldest) note "
            "is stolen with a 4 ms fade.", false),
        num("pitchbend", -24.0f, 24.0f, 0.0f, "st",
            "Pitch bend in (fractional) semitones for all sounding notes; automate for bends and dives. "
            "Smoothed."),
        num("modwheel", 0.0f, 1.0f, 0.0f, "",
            "DX7 mod wheel: brings in the patch's LFO vibrato (and tremolo/wah on operators with amp-mod "
            "sensitivity). 0.1-0.3 = gentle vibrato, 1 = extreme."),
        num("detune", 0.0f, 30.0f, 0.0f, "ct",
            "Stereo doubling: > 0 plays a second DX7 voice per note, the pair tuned -/+ detune/2 cents and "
            "spread by width (the classic lush DX chorus; 5-12 ct typical). 0 = one mono voice (half the CPU).",
            false),
        num("width", 0.0f, 1.0f, 0.7f, "",
            "Stereo spread of the two doubled voices when detune > 0: 0 = both centred, 1 = hard left/right."),
        num("brightness", -1.0f, 1.0f, 0.0f, "",
            "Gentle tilt EQ after the DX7: negative tames harsh or glassy patches (down to -10 dB above "
            "~2.5 kHz), positive adds air (up to +6 dB). 0 = untouched."),
        num("velsens", 0.0f, 1.0f, 1.0f, "",
            "Velocity response: 1 = authentic DX7 (patch-defined, often very dynamic), lower squeezes note "
            "velocities towards 100, 0 = every note plays as velocity 100."),
        choice("oversample", {"1x", "2x", "4x"}, 1,
               "FM engine rate: 2x (default) runs it at twice the sample rate and filters down, removing most "
               "aliasing on bright/high notes; 4x for extreme bright patches high up (2x the CPU of 2x); 1x = "
               "raw single-rate DX7 grit. The internal rate is capped at 192 kHz."),
        choice("autolevel", {"off", "on"}, 1,
               "on: every voice is loudness-matched at load by the K-weighted loudness (BS.1770) of a standard "
               "phrase (held note, melody, chord): at level 0 a typical melody plays at about -23 LUFS and chords at "
               "about -20.5 LUFS, ~9 in 10 ROM voices within +-2 LU of the median. High-crest percussion (GLOKENSPL, "
               "COW BELL, XYLOPHONE ...) sits 2-5 LU lower so a single note peaks <= -12 dBFS, and slow-attack pads "
               "read quiet on short notes. off: raw DX7 patch levels (they differ by up to ~20 dB)."),
        num("attack", 0.25f, 16.0f, 1.0f, "x",
            "Attack time multiplier for all six operator EGs (rate 1): 2-8 = slower bows and swells (STRINGS 1 "
            "reaches full level in 0.2 s at 1, 0.7 s at 4), 0.5 = snappier. It scales the patch's own attack, so "
            "an instant one (rate 99) stays short. Applied as DX7 EG rate steps: the factor lands within ~10 % "
            "(powers of 2 exactly; within 9 % of 1 = unchanged). Per note: a note uses the value at its note-on."),
        num("decay", 0.25f, 16.0f, 1.0f, "x",
            "Decay time multiplier for all operator EGs (rates 2 and 3): > 1 lets pianos, plucks and bells "
            "ring longer before they settle (MARIMBA at 2 rings twice as long), < 1 shortens them. DX7 EG rate "
            "steps (~10 %). Per note: a note uses the value at its note-on."),
        num("release", 0.25f, 16.0f, 1.0f, "x",
            "Release time multiplier for all operator EGs (rate 4): 2-4 lets released chords keep sounding under "
            "the next ones (DX voices as pads: STRINGS 1 falls 20 dB in 0.4 s at 1, 1.5 s at 4; BRASS 1's short "
            "release needs 8-16), 0.25-0.5 tightens staccato. DX7 EG rate steps (~10 %). Per note: a note uses "
            "the value at its note-off (automate it before the notes end)."),
    };
}

struct CalNote {
    double start, length;  // seconds
    int pitch, velocity;
};
// Held middle C (its peak drives the peak cap), a melody of quarter and eighth notes at 100 BPM, a chord.
constexpr CalNote kCalPhrase[] = {
    {0.00, 1.10, 60, 100},
    {1.20, 0.55, 72, 100}, {1.80, 0.28, 76, 100}, {2.10, 0.28, 79, 100}, {2.40, 0.55, 81, 100},
    {3.00, 0.28, 79, 100}, {3.30, 0.28, 76, 100}, {3.60, 0.55, 74, 100}, {4.20, 1.10, 72, 100},
    {5.40, 1.80, 57, 84},  {5.40, 1.80, 60, 84},  {5.40, 1.80, 64, 84},  {5.40, 1.80, 67, 84},
};
constexpr int kCalNotes = static_cast<int>(sizeof(kCalPhrase) / sizeof(kCalPhrase[0]));
constexpr double kCalLength = 7.70;
constexpr double kPeakSeconds = 1.2;  // the peak cap looks at this much of a held middle C

// Controllers of a private measurement voice: no wheel, no bend.
void initMeasureControllers(Controllers& ctrl, FmCore& core) {
    ctrl.core = &core;
    std::fill(std::begin(ctrl.values_), std::end(ctrl.values_), 0);
    ctrl.values_[kControllerPitch] = 0x2000;
    ctrl.values_[kControllerPitchRange] = 2;
    ctrl.masterTune = ctrl.modwheel_cc = ctrl.foot_cc = ctrl.breath_cc = ctrl.aftertouch_cc = 0;
    ctrl.refresh();
}

// Lowest significant partial of the patch in key units (see kPartialGuard): raw notes (no high-pass) on C3,
// C4 and C5 at velocities 64, 100 and 127 (modulation depth and level scaling change which sidebands
// matter), 32768 samples at kCalRate after the first 21 ms, Hann window; per note the lowest spectral peak
// within kPartialFloorDb of its strongest and at or above kPartialMinRatio x key. Returns a large value if
// there is none.
double measureLowestPartial(const Patch& patch) {
    ensureMsfaTables(kCalRate);
    constexpr int n = 32768, skip = 1024;
    const analysis::Fft fft(n);
    const std::vector<float> window = analysis::hannWindow(n);
    std::vector<float> x(static_cast<std::size_t>(skip + n)), re(static_cast<std::size_t>(n)), im(static_cast<std::size_t>(n));
    double lowest = 1e9;
    for (int run = 0; run < 9; ++run) {
        const int key = std::clamp(48 + 12 * (run / 3) + static_cast<int>(patch[144]) - 24, 0, 127);
        FmCore core;
        Controllers ctrl;
        initMeasureControllers(ctrl, core);
        Lfo lfo;
        lfo.reset(patch.data() + 137);
        Dx7Note note;
        note.init(patch.data(), key, std::array<int, 3>{64, 100, 127}[static_cast<std::size_t>(run % 3)]);
        if (patch[136] != 0) note.oscSync();
        else note.oscFreeRun(0);
        lfo.keydown();
        double mean = 0.0;
        for (int pos = 0; pos < skip + n; pos += kQ) {
            alignas(16) std::int32_t buf[kQ] = {};
            const std::int32_t value = lfo.getsample();
            note.compute(buf, value, lfo.getdelay(), &ctrl);
            for (int j = 0; j < kQ; ++j) {
                x[static_cast<std::size_t>(pos + j)] = static_cast<float>(std::clamp<std::int32_t>(buf[j] >> 4, -(1 << 24), (1 << 24) - 1)) * kFullScale;
                if (pos + j >= skip) mean += x[static_cast<std::size_t>(pos + j)];
            }
        }
        mean /= n;
        for (int i = 0; i < n; ++i) {
            re[static_cast<std::size_t>(i)] = static_cast<float>((x[static_cast<std::size_t>(skip + i)] - mean) * window[static_cast<std::size_t>(i)]);
            im[static_cast<std::size_t>(i)] = 0.0f;
        }
        fft.forward(re.data(), im.data());
        auto power = [&](int k) {
            const auto u = static_cast<std::size_t>(k);
            return static_cast<double>(re[u]) * re[u] + static_cast<double>(im[u]) * im[u];
        };
        const double binHz = kCalRate / n, keyHz = dsp::midiToHz(key);
        const int first = std::max(2, static_cast<int>(std::ceil(std::max(20.0, kPartialMinRatio * keyHz) / binHz)));
        const int last = std::min(n / 2 - 2, static_cast<int>(20000.0 / binHz));
        double strongest = 0.0;
        for (int k = first; k <= last; ++k) strongest = std::max(strongest, power(k));
        if (strongest <= 1e-24) continue;  // silent at this velocity / key
        const double threshold = strongest * std::pow(10.0, kPartialFloorDb / 10.0);
        for (int k = first; k <= last; ++k) {
            const double pk = power(k);
            if (pk >= threshold && pk >= power(k - 1) && pk >= power(k + 1)) {
                lowest = std::min(lowest, k * binHz / keyHz);
                break;
            }
        }
    }
    return lowest;
}

// Autolevel calibration (see kAutoLevelTargetLufs): gated K-weighted loudness (LUFS) of the standard phrase,
// mono voice at the MSFA output scale, rendered at kCalRate.
double measureLoudness(const Patch& patch, double lowestPartial) {
    ensureMsfaTables(kCalRate);
    FmCore core;
    Controllers ctrl;
    initMeasureControllers(ctrl, core);
    Lfo lfo;
    lfo.reset(patch.data() + 137);

    struct Voice {
        Dx7Note note;
        HpfCoefs hpf{};
        HpfStates state{};
        int on{0}, off{0}, end{0}, silent{0};  // quanta
        bool active{false};
    };
    std::vector<Voice> voices(static_cast<std::size_t>(kCalNotes));
    auto quantum = [](double seconds) { return static_cast<int>(std::lround(seconds * kCalRate / kQ)); };
    const int total = quantum(kCalLength);
    const int maxRelease = quantum(kCalMaxRelease), silence = static_cast<int>(std::ceil(kSilenceSeconds * kCalRate / kQ));
    for (int i = 0; i < kCalNotes; ++i) {
        Voice& v = voices[static_cast<std::size_t>(i)];
        v.on = quantum(kCalPhrase[i].start);
        v.off = quantum(kCalPhrase[i].start + kCalPhrase[i].length);
        v.end = std::min(total, v.off + maxRelease);
    }

    analysis::KWeighting kw(kCalRate);
    const int sub = quantum(0.1) * kQ;  // 100 ms sub-blocks -> 400 ms gating blocks with 75 % overlap
    std::vector<double> subEnergy;
    double acc = 0.0;
    int accN = 0;
    for (int q = 0; q < total; ++q) {
        for (int i = 0; i < kCalNotes; ++i) {
            Voice& v = voices[static_cast<std::size_t>(i)];
            const int key = std::clamp(kCalPhrase[i].pitch + static_cast<int>(patch[144]) - 24, 0, 127);
            if (q == v.on) {
                v.note.init(patch.data(), key, kCalPhrase[i].velocity);
                if (patch[136] != 0) v.note.oscSync();
                else v.note.oscFreeRun(static_cast<std::uint64_t>(q) * kQ);
                hpfTune(voiceHpfG(patch, key, lowestPartial, kCalRate), v.hpf);
                v.active = true;
                lfo.keydown();
            }
            if (q == v.off) v.note.keyup();
        }
        const std::int32_t lfoValue = lfo.getsample(), lfoDelay = lfo.getdelay();
        double mix[kQ] = {};
        for (Voice& v : voices) {
            if (!v.active) continue;
            alignas(16) std::int32_t buf[kQ] = {};
            v.note.compute(buf, lfoValue, lfoDelay, &ctrl);
            double peak = 0.0;
            for (int j = 0; j < kQ; ++j) {
                const double x = std::clamp<std::int32_t>(buf[j] >> 4, -(1 << 24), (1 << 24) - 1) * static_cast<double>(kFullScale);
                const double y = hpfTick(x, v.hpf, v.state);
                mix[j] += y;
                peak = std::max(peak, std::fabs(y));
            }
            hpfFlush(v.state);
            if (q >= v.off) {  // released: stop at silence or after kCalMaxRelease
                v.silent = peak <= kSilenceLevel ? v.silent + 1 : 0;
                if (v.silent >= silence || q + 1 >= v.end) v.active = false;
            }
        }
        for (int j = 0; j < kQ; ++j) {
            const double k = kw.process(mix[j]);
            acc += k * k;
            if (++accN == sub) {
                subEnergy.push_back(acc);
                acc = 0.0;
                accN = 0;
            }
        }
    }
    std::vector<double> blocks;
    for (std::size_t b = 0; b + 4 <= subEnergy.size(); ++b) {
        blocks.push_back((subEnergy[b] + subEnergy[b + 1] + subEnergy[b + 2] + subEnergy[b + 3]) / (4.0 * sub));
    }
    return analysis::integratedLoudness(blocks);
}

// Sample peak of a held middle C (velocity 100) at the internal rate `rate`, through the voice high-pass.
// Measured at the real rate: feedback operators and aliasing make spiky patches peak differently at 1x/2x.
double measurePeak(const Patch& patch, double lowestPartial, double rate) {
    ensureMsfaTables(rate);
    FmCore core;
    Controllers ctrl;
    initMeasureControllers(ctrl, core);
    Lfo lfo;
    lfo.reset(patch.data() + 137);
    Dx7Note note;
    const int key = std::clamp(60 + static_cast<int>(patch[144]) - 24, 0, 127);
    note.init(patch.data(), key, 100);
    if (patch[136] != 0) note.oscSync();
    else note.oscFreeRun(0);
    lfo.keydown();
    HpfCoefs hpf{};
    HpfStates state{};
    hpfTune(voiceHpfG(patch, key, lowestPartial, rate), hpf);
    double peak = 0.0;
    const int quanta = static_cast<int>(std::ceil(kPeakSeconds * rate / kQ));
    for (int q = 0; q < quanta; ++q) {
        alignas(16) std::int32_t buf[kQ] = {};
        const std::int32_t value = lfo.getsample();
        note.compute(buf, value, lfo.getdelay(), &ctrl);
        for (const std::int32_t raw : buf) {
            const double x = std::clamp<std::int32_t>(raw >> 4, -(1 << 24), (1 << 24) - 1) * static_cast<double>(kFullScale);
            peak = std::max(peak, std::fabs(hpfTick(x, hpf, state)));
        }
        hpfFlush(state);
    }
    return peak;
}

// The measurements are pure functions of their inputs: computed once per process and cached (rendering is
// single-threaded, like the MSFA tables).
double patchLowestPartial(const Patch& patch) {
    static std::map<Patch, double> cache;
    auto it = cache.find(patch);
    if (it == cache.end()) it = cache.emplace(patch, measureLowestPartial(patch)).first;
    return it->second;
}

double patchLoudness(const Patch& patch) {
    static std::map<Patch, double> cache;
    auto it = cache.find(patch);
    if (it == cache.end()) it = cache.emplace(patch, measureLoudness(patch, patchLowestPartial(patch))).first;
    return it->second;
}

double patchPeak(const Patch& patch, double rate) {
    static std::map<std::pair<Patch, double>, double> cache;
    const auto key = std::make_pair(patch, rate);
    auto it = cache.find(key);
    if (it == cache.end()) it = cache.emplace(key, measurePeak(patch, patchLowestPartial(patch), rate)).first;
    return it->second;
}

struct Slot {
    Dx7Note note[2];            // [0] = main voice, [1] = doubled voice (detune > 0)
    alignas(16) float out[2][kQ]{};
    HpfCoefs hpf{};             // per-voice DC high-pass (shared by both sets)
    HpfStates hpfState[2]{};
    double hpfG{0.0};           // its cutoff coefficient before pitch bend
    int pos{kQ};                // read position in out; kQ = next quantum must be computed
    int noteId{-1};
    int key{60};                // MSFA note number and velocity the voice was started with
    int velocity{100};
    EnvScale env{};             // envelope time scaling the voice was started (released) with
    std::uint64_t age{0};
    std::uint32_t releasedQuanta{0};
    std::uint32_t silentQuanta{0};
    std::uint32_t safetyQuanta{0};  // release safety limit of this note (scaled by its 'release' multiplier)
    float fade{1.0f};
    float fadeStep{0.0f};       // > 0 while fading out (stolen, or release safety limit reached)
    bool active{false};
    bool keyDown{false};
};

class Dx7Synth final : public Instrument {
public:
    Dx7Synth() : params_(makeSpecs()) {}

    void configure(const json& params) override {
        params_.configure(params, "dx7", {"voice"});
        if (params.is_object() && params.contains("voice")) {
            const json& v = params["voice"];
            if (!v.is_string()) {
                throw ConfigError("dx7: 'voice' must be a string such as \"E.PIANO 1\" or \"rom1a:10\"");
            }
            voiceSpec_ = v.get<std::string>();
        }
        dx7::checkVoiceSpec(voiceSpec_);
        for (const int p : {kTranspose, kPolyphony}) {
            const float value = params_.get(p);
            if (value != std::round(value)) {
                throw ConfigError("dx7: '" + params_.specs()[static_cast<std::size_t>(p)].name +
                                  "' must be a whole number");
            }
        }
    }

    // (only the song position of a preview's first sample depends on the tempo map: the LFO is free-running)
    void setTempoMap(const TempoMap& map) override { tempo_ = &map; }

    void prepare(const RenderContext& ctx) override {
        const auto banks = dx7::loadBanks(ctx.assetDir);
        const auto voice = dx7::resolveVoice(banks, voiceSpec_);
        patch_ = dx7::unpackVoice(voice.data);

        sampleRate_ = ctx.sampleRate;
        os_ = 1 << params_.choice("oversample");
        while (os_ > 1 && ctx.sampleRate * os_ > 192000.0 + 1.0) os_ /= 2;
        rate_ = sampleRate_ * os_;

        lowestPartial_ = patchLowestPartial(patch_);  // (the measurements switch the MSFA tables)
        outGain_ = 1.0f;
        if (params_.choice("autolevel") == 1) {
            const double lufs = patchLoudness(patch_), peak = patchPeak(patch_, rate_);
            if (lufs > analysis::kDbFloor && peak > 0.0) {
                const double gain = std::min(std::pow(10.0, (kAutoLevelTargetLufs - lufs) / 20.0),
                                             kAutoLevelPeakTarget / peak);
                outGain_ = static_cast<float>(std::clamp(gain, kAutoLevelMinGain, kAutoLevelMaxGain));
            }
        }
        ensureMsfaTables(rate_);

        poly_ = static_cast<int>(params_.get(kPolyphony));
        // One spare fade slot per playable voice, so even a full-polyphony chord change that steals every
        // voice at once fades each victim instead of hard-cutting some of them.
        slots_.assign(static_cast<std::size_t>(poly_ + std::max(kMinFadeSlots, poly_)), Slot{});
        doubled_ = params_.get(kDetune) > 0.0f;
        sets_ = doubled_ ? 2 : 1;
        transpose_ = static_cast<int>(params_.get(kTranspose));

        const int maxBlock = std::max(1, ctx.maxBlock);
        for (auto& b : bus_) b.assign(static_cast<std::size_t>(maxBlock * os_), 0.0f);
        for (int b = 0; b < 2; ++b) {
            dec2_[b].init(kHalfband2x);
            dec4_[b].init(kHalfband4x);
            dcBlock_[b].prepare(sampleRate_);
        }

        for (int s = 0; s < 2; ++s) {
            Controllers& c = ctrl_[s];
            c = Controllers{};
            c.core = &core_;
            std::fill(std::begin(c.values_), std::end(c.values_), 0);
            c.values_[kControllerPitch] = 0x2000;  // bend is applied through masterTune instead
            c.values_[kControllerPitchRange] = 2;
            c.values_[kControllerPitchStep] = 0;
            c.masterTune = 0;
            c.modwheel_cc = c.foot_cc = c.breath_cc = c.aftertouch_cc = 0;
            c.wheel.range = 99;  // DX7 function: MW range 99, assign pitch + amp
            c.wheel.pitch = true;
            c.wheel.amp = true;
            c.wheel.eg = false;
            c.refresh();
        }
        lfo_.reset(patch_.data() + 137);
        lfoPos_ = 0;
        lfoValue_ = lfoDelay_ = 0;
        // A render that starts mid-song (preview) continues where a full render is at that song
        // sample: the global LFO (free-running from the song start, one tick per quantum, also mid
        // quantum) and the clock that places the free-running oscillator phases of new notes.
        const std::uint64_t startInternal =
            static_cast<std::uint64_t>(songStartSample(ctx.startBeat, ctx.sampleRate, ctx.bpm, tempo_)) * static_cast<std::uint64_t>(os_);
        const std::uint64_t ticks = startInternal / kQ + (startInternal % kQ ? 1 : 0);
        for (std::uint64_t t = 0; t < ticks; ++t) {
            lfoValue_ = lfo_.getsample();
            lfoDelay_ = lfo_.getdelay();
        }
        lfoPos_ = static_cast<int>(startInternal % kQ);
        clock_ = startInternal;  // internal samples since the song start
        ageCounter_ = 0;
        modwheelCc_ = 0;

        dsp::Rng rng(ctx.seed ^ dsp::hashString("dx7") ^ 0xD7D7D7D7ull);
        phaseOffset_[0] = 0;
        phaseOffset_[1] = rng.next() >> 20;  // decorrelates the doubled voice's free-running oscillators

        fadeStep_ = static_cast<float>(1.0 / (kStealFadeSeconds * rate_));
        safetyFadeStep_ = static_cast<float>(1.0 / (kSafetyFadeSeconds * rate_));
        silenceQuanta_ = static_cast<std::uint32_t>(std::ceil(kSilenceSeconds * rate_ / kQ));
        safetyQuanta_ = static_cast<std::uint32_t>(kReleaseSafetySeconds * rate_ / kQ);

        // Block-rate smoothing starts at the configured values.
        bend_ = bend1_ = params_.get(kPitchbend);
        modwheel_ = modwheel1_ = params_.get(kModwheel);
        level_ = level1_ = dsp::dbToGain(params_.get(kLevel)) * outGain_;
        pan_ = pan1_ = params_.get(kPan);
        width_ = width1_ = params_.get(kWidth);
        bright_ = bright1_ = params_.get(kBrightness);
        hpfBend_ = bendFactor();
        computeBusGains(busGain_);
        for (int b = 0; b < 2; ++b) {
            tiltHigh_[b].tune(sampleRate_, kTiltHighHz, kTiltK);
            tiltLow_[b].tune(sampleRate_, kTiltLowHz, kTiltK);
            tiltHigh_[b].reset();
            tiltLow_[b].reset();
        }
        tiltMix(bright_, tiltM_);
        applyControllers();
    }

    bool setParam(std::string_view name, float value) override { return params_.set(name, value); }

    void noteOn(int noteId, int pitch, float velocity) override {
        ensureMsfaTables(rate_);
        int vel = std::clamp(static_cast<int>(std::lround(velocity * 127.0f)), 1, 127);
        const float sens = params_.get(kVelsens);
        vel = std::clamp(static_cast<int>(std::lround(100.0f + (static_cast<float>(vel) - 100.0f) * sens)), 1, 127);
        const int note = std::clamp(pitch + transpose_ + static_cast<int>(patch_[144]) - 24, 0, 127);
        const EnvScale env{qrateOffset(params_.get(kAttack)), qrateOffset(params_.get(kDecay)),
                           qrateOffset(params_.get(kRelease))};
        const Patch patch = scaledPatch(patch_, note, env);

        Slot& s = allocate();
        for (int set = 0; set < sets_; ++set) {
            s.note[set].init(patch.data(), note, vel);
            if (patch_[136] != 0) s.note[set].oscSync();
            else s.note[set].oscFreeRun(clock_ + phaseOffset_[set]);
            s.hpfState[set] = HpfStates{};
        }
        s.hpfG = voiceHpfG(patch_, note, lowestPartial_, rate_);
        hpfTune(s.hpfG * hpfBend_, s.hpf);
        s.pos = kQ;
        s.noteId = noteId;
        s.key = note;
        s.velocity = vel;
        s.env = env;
        s.age = ++ageCounter_;
        s.releasedQuanta = s.silentQuanta = 0;
        s.safetyQuanta = releaseSafetyQuanta(env.release);
        s.fade = 1.0f;
        s.fadeStep = 0.0f;
        s.active = s.keyDown = true;
        lfo_.keydown();
    }

    void noteOff(int noteId) override {
        ensureMsfaTables(rate_);
        const int release = qrateOffset(params_.get(kRelease));
        for (int i = 0; i < poly_; ++i) {
            Slot& s = slots_[static_cast<std::size_t>(i)];
            if (s.active && s.keyDown && s.noteId == noteId) {
                s.keyDown = false;
                s.releasedQuanta = 0;
                if (release != s.env.release) {  // 'release' changed since the note started: new R4 rates
                    s.env.release = release;
                    const Patch patch = scaledPatch(patch_, s.key, s.env);
                    for (int set = 0; set < sets_; ++set) s.note[set].updateVoicePreservingState(patch.data(), s.key, s.velocity);
                    s.safetyQuanta = releaseSafetyQuanta(release);
                }
                for (int set = 0; set < sets_; ++set) s.note[set].keyup();
            }
        }
    }

    void process(float* left, float* right, int frames) override {
        std::fill_n(left, frames, 0.0f);
        std::fill_n(right, frames, 0.0f);
        if (frames <= 0) return;
        ensureMsfaTables(rate_);
        updateControls(frames);

        const int n = frames * os_;
        for (int b = 0; b < sets_; ++b) std::fill_n(bus_[b].data(), n, 0.0f);
        for (int done = 0; done < n;) {
            if (lfoPos_ == 0) {  // the DX7 LFO is global and ticks once per quantum
                lfoValue_ = lfo_.getsample();
                lfoDelay_ = lfo_.getdelay();
            }
            const int chunk = std::min(n - done, kQ - lfoPos_);
            for (auto& s : slots_) {
                if (s.active) renderSlot(s, done, chunk);
            }
            lfoPos_ = (lfoPos_ + chunk) % kQ;
            clock_ += static_cast<std::uint64_t>(chunk);
            done += chunk;
        }

        std::array<float, 4> target{};
        computeBusGains(target);
        std::array<float, 5> tiltTarget{};
        tiltMix(bright_, tiltTarget);
        const bool tiltFlat = tiltM_ == kTiltFlat && tiltTarget == kTiltFlat;
        const float inv = 1.0f / static_cast<float>(frames);
        for (int b = 0; b < sets_; ++b) {
            float* x = bus_[b].data();  // decimated in place
            if (os_ == 4) dec4_[b].process(x, x, 2 * frames);
            if (os_ >= 2) dec2_[b].process(x, x, frames);
            for (int i = 0; i < frames; ++i) x[i] = static_cast<float>(dcBlock_[b].process(x[i]));
            // Tilt: the filters always run (warm state); the shelf gains are ramped in the output mix.
            std::array<float, 5> m = tiltM_, dm{};
            for (std::size_t k = 0; k < m.size(); ++k) dm[k] = (tiltTarget[k] - m[k]) * inv;
            for (int i = 0; i < frames; ++i) {
                float bh, lh, bl, ll;
                tiltHigh_[b].tick(x[i], bh, lh);
                if (tiltFlat) {
                    tiltLow_[b].tick(x[i], bl, ll);
                    continue;
                }
                for (std::size_t k = 0; k < m.size(); ++k) m[k] += dm[k];
                const float y = m[0] * x[i] + m[1] * bh + m[2] * lh;  // high shelf
                tiltLow_[b].tick(y, bl, ll);
                x[i] = y + m[3] * bl + m[4] * ll;                     // low shelf
            }
            tiltHigh_[b].flush();
            tiltLow_[b].flush();
            float gl = busGain_[2 * b], gr = busGain_[2 * b + 1];
            const float dl = (target[2 * b] - gl) * inv, dr = (target[2 * b + 1] - gr) * inv;
            for (int i = 0; i < frames; ++i) {
                gl += dl;
                gr += dr;
                left[i] += x[i] * gl;
                right[i] += x[i] * gr;
            }
        }
        busGain_ = target;
        tiltM_ = tiltTarget;
    }

    bool idle() const override {
        return std::none_of(slots_.begin(), slots_.end(), [](const Slot& s) { return s.active; }) &&
               dcBlock_[0].settled() && dcBlock_[1].settled();
    }

    const std::vector<ParamSpec>& paramSpecs() const override { return params_.specs(); }

private:
    // Free slot, else the oldest released note, else the oldest note (DX7-style stealing).
    Slot& allocate() {
        Slot* pick = nullptr;
        for (int i = 0; i < poly_ && !pick; ++i) {
            if (!slots_[static_cast<std::size_t>(i)].active) pick = &slots_[static_cast<std::size_t>(i)];
        }
        auto oldest = [this](bool releasedOnly) {
            Slot* found = nullptr;
            for (int k = 0; k < poly_; ++k) {
                Slot& s = slots_[static_cast<std::size_t>(k)];
                if (releasedOnly && s.keyDown) continue;
                if (!found || s.age < found->age) found = &s;
            }
            return found;
        };
        if (!pick) pick = oldest(true);
        if (!pick) pick = oldest(false);
        if (pick->active) startFade(*pick);
        return *pick;
    }

    // Release safety limit (quanta) of a note released with the qrate offset `release`: kReleaseSafetySeconds,
    // stretched by the release time multiplier so that slowed-down tails that still decay are not cut.
    std::uint32_t releaseSafetyQuanta(int release) const noexcept {
        const double stretch = std::max(1.0, std::exp2(-release / 4.0));
        return static_cast<std::uint32_t>(std::min(4.0e9, static_cast<double>(safetyQuanta_) * stretch));
    }

    // Moves a stolen voice into a spare slot where it fades out over kStealFadeSeconds.
    void startFade(const Slot& victim) {
        Slot* spare = nullptr;
        for (std::size_t i = static_cast<std::size_t>(poly_); i < slots_.size(); ++i) {
            Slot& s = slots_[i];
            if (!s.active) { spare = &s; break; }
            if (!spare || s.fade < spare->fade) spare = &s;
        }
        *spare = victim;
        spare->keyDown = false;
        spare->noteId = -1;
        spare->fadeStep = fadeStep_;
    }

    // Renders MSFA quantum for every voice set of the slot through the voice's DC high-pass. Returns false
    // if the slot was freed.
    bool computeQuantum(Slot& s) noexcept {
        std::int32_t rawPeak = 0;
        float peak = 0.0f;
        for (int set = 0; set < sets_; ++set) {
            alignas(16) std::int32_t buf[kQ] = {};
            s.note[set].compute(buf, lfoValue_, lfoDelay_, &ctrl_[set]);
            float* out = s.out[set];
            HpfStates& st = s.hpfState[set];
            for (int j = 0; j < kQ; ++j) {
                // Dexed/Msound2 output stage: >> 4, per-voice clip at +-2^24 (= full scale 1.0).
                const std::int32_t x = buf[j] >> 4;
                rawPeak = std::max(rawPeak, x < 0 ? -x : x);
                const float clipped = static_cast<float>(std::clamp<std::int32_t>(x, -(1 << 24), (1 << 24) - 1)) * kFullScale;
                out[j] = static_cast<float>(hpfTick(clipped, s.hpf, st));
                peak = std::max(peak, std::fabs(out[j]));
            }
            hpfFlush(st);
        }
        s.pos = 0;
        if (!s.keyDown) {
            ++s.releasedQuanta;
            // Silent = the voice and its high-pass tail (the removed DC swinging back) are both inaudible.
            s.silentQuanta = rawPeak <= kSilencePeak && peak <= kSilenceLevel ? s.silentQuanta + 1 : 0;
            if (s.silentQuanta >= silenceQuanta_) {
                s.active = false;
                return false;
            }
            // Patches whose release level L4 > 0 never decay: end them with a short fade, not a cut.
            if (s.releasedQuanta >= s.safetyQuanta && s.fadeStep <= 0.0f) s.fadeStep = safetyFadeStep_;
        }
        return true;
    }

    void renderSlot(Slot& s, int offset, int len) noexcept {
        for (int i = 0; i < len;) {
            if (s.pos == kQ && !computeQuantum(s)) return;
            const int n = std::min(len - i, kQ - s.pos);
            for (int set = 0; set < sets_; ++set) {
                const float* x = s.out[set] + s.pos;
                float* y = bus_[set].data() + offset + i;
                if (s.fadeStep > 0.0f) {
                    float g = s.fade;
                    for (int k = 0; k < n; ++k) {
                        g = std::max(0.0f, g - s.fadeStep);
                        y[k] += x[k] * g;
                    }
                } else {
                    for (int k = 0; k < n; ++k) y[k] += x[k];
                }
            }
            if (s.fadeStep > 0.0f) {
                s.fade = std::max(0.0f, s.fade - s.fadeStep * static_cast<float>(n));
                if (s.fade <= 0.0f) {
                    s.active = false;
                    return;
                }
            }
            s.pos += n;
            i += n;
        }
    }

    // Two cascaded one-poles (stage a, output b) advanced by one block; lands exactly on the target.
    static void glide(float& a, float& b, float target, float e) noexcept {
        a = target + (a - target) * e;
        b = a + (b - a) * e;
        if (std::fabs(a - target) + std::fabs(b - target) <= 1e-7f * (1.0f + std::fabs(target))) a = b = target;
    }

    // Block-rate smoothing of the continuous parameters, then MSFA controller updates.
    void updateControls(int frames) noexcept {
        const double t = static_cast<double>(frames) / sampleRate_;
        const float fast = static_cast<float>(std::exp(-t / kGainTau)), tone = static_cast<float>(std::exp(-t / kToneTau));
        glide(bend1_, bend_, params_.get(kPitchbend), fast);
        glide(modwheel1_, modwheel_, params_.get(kModwheel), tone);
        glide(level1_, level_, dsp::dbToGain(params_.get(kLevel)) * outGain_, fast);
        glide(pan1_, pan_, params_.get(kPan), fast);
        glide(width1_, width_, params_.get(kWidth), fast);
        glide(bright1_, bright_, params_.get(kBrightness), tone);
        applyControllers();
        // Downward bends take the voices' DC high-passes with them (cutoff ~ tan-linear at these ratios),
        // gliding with a slower time constant so the per-block coefficient steps stay tiny.
        const double factor = bendFactor();
        if (factor != hpfBend_) {
            hpfBend_ = factor + (hpfBend_ - factor) * std::exp(-t / kHpfBendTau);
            if (std::fabs(hpfBend_ - factor) < 1e-4 * factor) hpfBend_ = factor;
            for (auto& s : slots_) {
                if (s.active) hpfTune(s.hpfG * hpfBend_, s.hpf);
            }
        }
    }

    double bendFactor() const noexcept { return bend_ < 0.0f ? std::exp2(static_cast<double>(bend_) / 12.0) : 1.0; }

    void applyControllers() noexcept {
        const float detune = doubled_ ? params_.get(kDetune) : 0.0f;
        const double cents[2] = {bend_ * 100.0 - detune * 0.5, bend_ * 100.0 + detune * 0.5};
        for (int s = 0; s < 2; ++s) ctrl_[s].masterTune = static_cast<int>(std::lround(cents[s] * kQ24PerCent));
        const int cc = std::clamp(static_cast<int>(std::lround(modwheel_ * 127.0f)), 0, 127);
        if (cc != modwheelCc_) {
            modwheelCc_ = cc;
            for (auto& c : ctrl_) {
                c.modwheel_cc = cc;
                c.refresh();
            }
        }
    }

    // Output-mix coefficients of the tilt for a brightness value: high shelf m0 x + m1 band + m2 low
    // (gain A^2 above 2.5 kHz), low shelf y + m3 band + m4 low (gain A^2 below 250 Hz). Brightness 0
    // gives exactly {1, 0, 0, 0, 0}: bit-transparent.
    static void tiltMix(float bright, std::array<float, 5>& m) noexcept {
        const double hsDb = bright >= 0.0f ? 6.0 * bright : 10.0 * bright;
        const double lsDb = -2.0 * bright;
        const double ah = std::pow(10.0, hsDb / 40.0), al = std::pow(10.0, lsDb / 40.0);
        m[0] = static_cast<float>(ah * ah);
        m[1] = static_cast<float>(kTiltK * (1.0 - ah) * ah);
        m[2] = static_cast<float>(1.0 - ah * ah);
        m[3] = static_cast<float>(kTiltK * (al - 1.0));
        m[4] = static_cast<float>(al * al - 1.0);
    }
    static constexpr std::array<float, 5> kTiltFlat = {1.0f, 0.0f, 0.0f, 0.0f, 0.0f};

    // Per-bus L/R gains: bus 0 = main voices, bus 1 = doubled voices (each -3 dB when doubled).
    void computeBusGains(std::array<float, 4>& g) const noexcept {
        if (!doubled_) {
            dsp::panGains(pan_, g[0], g[1]);
            g[0] *= level_;
            g[1] *= level_;
            g[2] = g[3] = 0.0f;
            return;
        }
        const float trim = level_ * 0.70710678f;
        dsp::panGains(std::clamp(pan_ - width_, -1.0f, 1.0f), g[0], g[1]);
        dsp::panGains(std::clamp(pan_ + width_, -1.0f, 1.0f), g[2], g[3]);
        for (auto& x : g) x *= trim;
    }

    Params params_;
    std::string voiceSpec_{"E.PIANO 1"};
    Patch patch_{};

    double sampleRate_{48000.0};
    double rate_{48000.0};  // internal (possibly oversampled) MSFA rate
    int os_{1};  // oversampling factor 1, 2 or 4
    int poly_{16};
    int sets_{1};
    int transpose_{0};
    bool doubled_{false};

    std::vector<Slot> slots_;
    FmCore core_;
    Controllers ctrl_[2];
    Lfo lfo_;
    int lfoPos_{0};
    std::int32_t lfoValue_{0};
    std::int32_t lfoDelay_{0};
    std::uint64_t clock_{0};  // internal (oversampled) samples since the song start
    const TempoMap* tempo_{nullptr};
    std::uint64_t ageCounter_{0};
    std::uint64_t phaseOffset_[2]{};
    float fadeStep_{0.0f};
    float safetyFadeStep_{0.0f};
    std::uint32_t silenceQuanta_{1};
    std::uint32_t safetyQuanta_{1};

    std::array<std::vector<float>, 2> bus_;  // internal-rate voice sums, decimated in place
    std::array<HalfbandDecimator, 2> dec2_;
    std::array<HalfbandDecimator, 2> dec4_;
    std::array<DcBlocker, 2> dcBlock_;
    std::array<TiltSvf, 2> tiltHigh_, tiltLow_;  // per bus
    std::array<float, 5> tiltM_{kTiltFlat};      // current tilt output mix (see tiltMix)

    float outGain_{1.0f};  // auto-level (or raw) gain applied on top of 'level'
    double lowestPartial_{1e9};  // the patch's lowest significant partial in key units (voice high-pass guard)
    double hpfBend_{1.0};  // pitch-bend factor applied to the voices' DC high-pass cutoffs
    // smoothed values (and their first smoothing stage)
    float bend_{0.0f}, modwheel_{0.0f}, level_{1.0f}, pan_{0.0f}, width_{0.7f}, bright_{0.0f};
    float bend1_{0.0f}, modwheel1_{0.0f}, level1_{1.0f}, pan1_{0.0f}, width1_{0.7f}, bright1_{0.0f};
    int modwheelCc_{0};
    std::array<float, 4> busGain_{};
};

}  // namespace

std::unique_ptr<Instrument> makeDx7Synth() { return std::make_unique<Dx7Synth>(); }

}  // namespace as
