// Amp: a tube guitar amplifier head - the preamp, the tone stack and the power amp (the speaker cabinet is a
// 'convolver' with a cab IR after it: cab/* patches).
//
// Why not a saturator: one static waveshaper at 25-30 dB of drive on a DI guitar is a fuzz box - every harmonic
// comes from one curve, an asymmetric curve gives a hollow, even-harmonic (octave-up) tone, and the fizz it makes
// has to be filtered away afterwards (measured on the old hero lead: the 2nd harmonic louder than the 3rd, 4-8 kHz
// cut to -19 dB of the energy). A real lead amp gets its singing, compressed, odd-harmonic tone from several gain
// stages in a row, each clipping a little, with filters between them:
//
//   [boost]  an optional mid-hump overdrive pedal in front (Tube Screamer: x + clip(drive * highpass720(x)),
//            then a 5 kHz low-pass) - tightens the lows and focuses the mids before the amp.
//   preamp   'stages' cascaded triode stages (1 = a clean-ish combo, 2 = a Plexi, 3 = a hot-rodded lead channel,
//            4 = modern high gain), 'gain' spread over them. Each stage: a coupling high-pass ('tight' on the first,
//            fixed ones later), a cathode-bypass shelf (lows get less gain than mids in the later stages: tight,
//            not thin), an asymmetric soft clip (grid conduction limits one side earlier than cutoff the other),
//            the phase inversion of a common-cathode stage (the asymmetries of consecutive stages partly cancel:
//            the cascade ends up odd-harmonic heavy like the real thing) and a Miller-capacitance low-pass that
//            closes a little more stage by stage (the next stage clips a smoother signal: less fizz, less
//            aliasing). 'bright' is the bright cap: a treble shelf before the first stage.
//   tone     the passive bass / mid / treble tone stack (the Fender / Marshall TMB network, analytic transfer
//            function after Yeh & Smith, DAFx 2006 - 'stack' british (Marshall values) or american (Fender)).
//   power    a push-pull power stage ('master' = how hard it is driven): a near-symmetric soft clip (odd
//            harmonics, a small bias mismatch), 'presence' / 'resonance' (the negative-feedback loop's treble /
//            low-resonance controls) and supply SAG: the rectifier's voltage drops under a loud note, the stage
//            clips earlier and quieter, and recovers as the note decays - compression with a breathing bloom.
//
// The whole nonlinear path runs 4x oversampled (polyphase IIR half-bands, ~5.5 samples of latency at 1x like the
// saturator), double precision. A track whose two channels are identical (a mono DI) is processed once.

#include "core/Module.h"
#include "fx/HalfBand.h"
#include "fx/TimeFxUtil.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>

namespace as::timefx {

namespace {

enum AmpParam {
    kAGain, kAStages, kABoost, kATight, kABright, kABass, kAMid, kATreble, kAStack, kAPresence, kAResonance,
    kAMaster, kASag, kAOutput
};

const std::vector<ParamSpec>& ampSpecs() {
    static const std::vector<ParamSpec> s = {
        num("gain", 0, 10, 6, "",
            "Preamp gain (the gain knob), spread over the stages: 0-2 clean / edge of breakup, 3-5 crunch, 6-8 a "
            "singing lead, 9-10 saturated high gain. 6 dB + 5.4 dB per step in total (60 dB at 10)."),
        num("stages", 1, 4, 3, "",
            "Cascaded preamp gain stages (whole number): 1 = a simple combo, 2 = a Plexi, 3 = a hot-rodded lead "
            "channel (default), 4 = modern high gain. More stages = smoother, more compressed, more sustain at the "
            "same gain.", false),
        num("boost", 0, 30, 0, "dB",
            "An overdrive pedal in front (Tube Screamer style, 0 = off): mid-hump drive (the lows pass clean, the "
            "mids above ~720 Hz clip), then a 5 kHz low-pass. 6-12 dB = the classic lead boost: tighter lows, "
            "focused singing mids."),
        num("tight", 20, 500, 90, "Hz",
            "High-pass before the first gain stage (the input coupling): 60-90 = full Plexi lows, 120-200 = tight "
            "(no farting low notes under heavy gain), 300+ = thin."),
        num("bright", 0, 12, 3, "dB", "Bright cap: a treble shelf (~1.2 kHz) before the first stage: more bite and pick attack."),
        num("bass", 0, 10, 5, "", "Tone stack bass (log pot) - the stack is passive: it shapes, it never boosts."),
        num("mid", 0, 10, 5, "", "Tone stack middle: 0 = the scooped metal mid, 6-8 = a mid-forward lead that cuts."),
        num("treble", 0, 10, 5, "", "Tone stack treble."),
        choice("stack", {"british", "american"}, 0,
               "Tone stack values: british = Marshall (tighter, mid-forward), american = Fender Bassman (deeper mid "
               "scoop, rounder)."),
        num("presence", 0, 10, 5, "",
            "Power-amp presence (the feedback loop's treble, a shelf ~3.5 kHz): 0 = -7 dB, 5 = flat, 10 = +7 dB."),
        num("resonance", 0, 10, 5, "",
            "Power-amp resonance / depth (the speaker's low resonance, a peak ~110 Hz): 0 = -6 dB, 5 = flat, 10 = +6 dB."),
        num("master", 0, 10, 5, "",
            "Master volume: how hard the push-pull power stage is driven (-6 dB + 3 dB per step): 2-4 = preamp "
            "distortion only, 5-7 = the power amp joins in (thicker, compressed), 8-10 = a cranked Plexi."),
        num("sag", 0, 1, 0.3f, "",
            "Supply sag (tube rectifier): a loud note pulls the supply down - the power stage clips earlier and "
            "quieter, then recovers as the note rings (compression with a bloom). 0 = a stiff solid-state supply, "
            "0.3 = a lead amp, 0.7-1 = spongy vintage."),
        num("output", -36, 12, 0, "dB", "Output level (after the power amp; a cranked amp sits around -16 dBFS RMS, peaks near -9 dBFS at 0 dB: +6 dB for a hot track)."),
    };
    return s;
}

// tanh by a Pade approximant, exact +-1 beyond +-3 (continuous value and slope there).
inline double softClip(double x) noexcept {
    if (x >= 3.0) return 1.0;
    if (x <= -3.0) return -1.0;
    const double x2 = x * x;
    return x * (27.0 + x2) / (27.0 + 9.0 * x2);
}

// Its antiderivative (0 at 0): x^2/18 + 4/3 ln((9x^2 + 27) / 27), |x| - 3 + F(3) beyond +-3.
inline double softClipF(double x) noexcept {
    constexpr double kF3 = 0.5 + 4.0 / 3.0 * 1.3862943611198906;   // F(3) = 1/2 + 4/3 ln 4
    const double ax = std::fabs(x);
    if (ax >= 3.0) return ax - 3.0 + kF3;
    return x * x / 18.0 + 4.0 / 3.0 * std::log1p(x * x / 3.0);
}

// A triode stage's transfer curve: grid conduction limits the positive swing early (+1), cutoff the negative one
// later and softer (-1.6). Slope 1 at rest.
constexpr double kTriPos = 1.0, kTriNeg = 1.6;
inline double triode(double v) noexcept {
    return v >= 0.0 ? kTriPos * softClip(v / kTriPos) : kTriNeg * softClip(v / kTriNeg);
}
inline double triodeF(double v) noexcept {
    return v >= 0.0 ? kTriPos * kTriPos * softClipF(v / kTriPos) : kTriNeg * kTriNeg * softClipF(v / kTriNeg);
}

// First-order antiderivative anti-aliasing (Parker, Zavalishin & Le Bihan, DAFx 2016): the mean of the curve over
// the segment between consecutive inputs - on top of the 4x oversampling it takes the folded-back fizz of a
// cascade of clipping stages down by another ~10-20 dB.
template <double (*f)(double), double (*F)(double)>
struct Adaa {
    double x1{0.0}, F1{0.0};
    double operator()(double x) noexcept {
        const double Fx = F(x), dx = x - x1;
        const double y = std::fabs(dx) > 1e-7 ? (Fx - F1) / dx : f(0.5 * (x + x1));
        x1 = x;
        F1 = Fx;
        return y;
    }
};
using TriodeAdaa = Adaa<triode, triodeF>;
using ClipAdaa = Adaa<softClip, softClipF>;

// One-pole TPT filter (low-pass output; high-pass = x - low-pass).
struct OnePole {
    double s{0.0};
    double lp(double x, double G) noexcept {
        const double v = (x - s) * G;
        const double y = v + s;
        s = y + v;
        return y;
    }
};

inline double tptG(double fc, double fs) noexcept {
    const double g = std::tan(dsp::kPi * std::min(fc, 0.45 * fs) / fs);
    return g / (1.0 + g);
}

constexpr int kMaxStages = 4;

struct Coefs {
    // boost
    bool boost{false};
    double tsG{0.0}, tsHp{0.0}, tsLp{0.0};
    // preamp
    int stages{3};
    double stageGain{1.0};
    double tightG{0.0}, brightG{0.0}, brightA{1.0};
    std::array<double, kMaxStages> shelfG{}, shelfA{}, coupleG{}, millerG{};
    // tone stack (3rd order, direct form II transposed), makeup
    double b[4]{1, 0, 0, 0}, a[4]{1, 0, 0, 0};
    // power amp
    double presG{0.0}, presA{1.0};
    double rb0{1}, rb1{0}, rb2{0}, ra1{0}, ra2{0};   // resonance peak (RBJ)
    double paGain{1.0}, sag{0.3}, envAtt{0.0}, envRel{0.0}, outG{0.5};
};

struct Chan {
    OnePole tsHp, tsLp, tight, bright;
    std::array<OnePole, kMaxStages> shelf{}, couple{}, miller{};
    std::array<TriodeAdaa, kMaxStages> tri{};
    ClipAdaa tsClip, paClip;
    double ts1{0}, ts2{0}, ts3{0};              // tone stack state
    OnePole pres;
    double r1{0}, r2{0};                         // resonance biquad state (TDF2)
    double env{0.0};
    double dcX{0.0}, dcY{0.0};                   // 1x output DC blocker

    void flushAll() noexcept {
        auto f = [](double& v) { v = hb::flushD(v); };
        for (OnePole* p : {&tsHp, &tsLp, &tight, &bright, &pres}) f(p->s);
        for (int i = 0; i < kMaxStages; ++i) {
            f(shelf[static_cast<std::size_t>(i)].s);
            f(couple[static_cast<std::size_t>(i)].s);
            f(miller[static_cast<std::size_t>(i)].s);
        }
        for (double* v : {&ts1, &ts2, &ts3, &r1, &r2, &env, &dcX, &dcY, &tsClip.x1, &tsClip.F1, &paClip.x1, &paClip.F1}) f(*v);
        for (auto& t : tri) { f(t.x1); f(t.F1); }
    }
};

class Amp final : public ParamEffect {
    static constexpr int kN1 = 8, kN2 = 4;     // half-band sections (as the saturator)
    static constexpr double kTbw1 = 0.05, kTbw2 = 0.25;
    static constexpr double kGlideTau = 0.0015;   // two-pole knob glide (~5 ms 10-90 %, like the other fx gains)
    static constexpr double kStackMakeupDb = 8.0;   // the passive stack's insertion loss, given back
    static constexpr double kOutScale = 0.25;
    static constexpr int kCoefEvery = 4;           // coefficient updates while a knob glides (samples)
    static constexpr double kBias = 0.08;          // the power stage: a little push-pull mismatch

public:
    Amp() : ParamEffect(ampSpecs(), "amp") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        requireInteger("stages");
        fs4_ = 4.0 * sr_;
        hb1_ = hb::designHalfBand<kN1>(kTbw1);
        hb2_ = hb::designHalfBand<kN2>(kTbw2);
        up1_.reset(); up2_.reset(); dn1_.reset(); dn2_.reset();
        for (auto& c : ch_) {
            c = Chan{};
            c.paClip.x1 = kBias;               // the power stage rests at its bias point
            c.paClip.F1 = softClipF(kBias);
        }
        mono_ = true;
        const int knobs[] = {kAGain, kABoost, kATight, kABright, kABass, kAMid, kATreble, kAPresence, kAResonance,
                             kAMaster, kASag, kAOutput};
        for (int i = 0; i < kKnobs; ++i) knob_[i].prepare(sr_, kGlideTau, get(knobs[i]));
        dcR_ = std::exp(-2.0 * dsp::kPi * 5.0 / sr_);
        ctl_ = 0;
        updateCoefs();
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) {
            const int knobs[] = {kAGain, kABoost, kATight, kABright, kABass, kAMid, kATreble, kAPresence, kAResonance,
                                 kAMaster, kASag, kAOutput};
            for (int i = 0; i < kKnobs; ++i) knob_[i].setTarget(get(knobs[i]));
        }
        const bool monoBlock = mono_ && std::memcmp(left, right, sizeof(float) * static_cast<std::size_t>(frames)) == 0;
        if (!monoBlock) mono_ = false;
        for (int n = 0; n < frames; ++n) {
            bool moving = false;
            for (auto& k : knob_) {
                k.next();
                moving = moving || k.moving();
            }
            if (moving) {                      // coefficients at control rate while a knob glides, once after
                if (++ctl_ >= kCoefEvery) {
                    ctl_ = 0;
                    updateCoefs();
                }
                gliding_ = true;
            } else if (gliding_) {
                updateCoefs();
                gliding_ = false;
                ctl_ = 0;
            }
            // the level-type knobs glide per sample (the filters follow at control rate)
            if (knob_[0].moving()) c_.stageGain = stageGain(knob_[0].value(), c_.stages);
            if (knob_[9].moving()) c_.paGain = paGain(knob_[9].value());
            const double outG = knob_[11].moving() ? std::pow(10.0, knob_[11].value() / 20.0) * kOutScale : c_.outG;
            hb::D2 a0, a1, u[4];
            up1_.up(hb1_, hb::d2(left[n], right[n]), a0, a1);
            up2_.up(hb2_, a0, u[0], u[1]);
            up2_.up(hb2_, a1, u[2], u[3]);
            for (auto& v : u) {
                const double y0 = tick(ch_[0], v[0]);
                v[1] = monoBlock ? y0 : tick(ch_[1], v[1]);
                v[0] = y0;
            }
            const hb::D2 h0 = dn2_.down(hb2_, u[0], u[1]);
            const hb::D2 h1 = dn2_.down(hb2_, u[2], u[3]);
            const hb::D2 d = dn1_.down(hb1_, h0, h1);
            for (int c = 0; c < 2; ++c) {
                Chan& s = ch_[c];
                const double x = d[c];
                const double y = x - s.dcX + dcR_ * s.dcY;     // DC blocker (5 Hz)
                s.dcX = x;
                s.dcY = y;
                (c == 0 ? left : right)[n] = static_cast<float>(y * outG);
            }
        }
        if (monoBlock) ch_[1] = ch_[0];
        for (auto& c : ch_) c.flushAll();
        up1_.flush(); up2_.flush(); dn1_.flush(); dn2_.flush();
        pos_ += static_cast<std::uint64_t>(frames);
    }

    double tailSeconds() const override { return 0.01; }

private:
    static constexpr int kKnobs = 12;   // gain boost tight bright bass mid treble presence resonance master sag output

    // One 4x sample through boost -> preamp -> tone stack -> power amp.
    double tick(Chan& s, double x) const noexcept {
        const Coefs& k = c_;
        if (k.boost) {   // x + clip(drive * hp720(x)) -> lp 5 kHz
            const double hp = x - s.tsHp.lp(x, k.tsHp);
            x = s.tsLp.lp(x + 0.45 * s.tsClip(k.tsG * hp / 0.45), k.tsLp);
        }
        x -= s.tight.lp(x, k.tightG);                                    // input coupling (tight)
        x += (k.brightA - 1.0) * (x - s.bright.lp(x, k.brightG));        // bright cap
        for (int i = 0; i < k.stages; ++i) {
            const std::size_t j = static_cast<std::size_t>(i);
            if (i > 0) {
                x -= s.couple[j].lp(x, k.coupleG[j]);                     // coupling cap
                const double lo = s.shelf[j].lp(x, k.shelfG[j]);          // cathode bypass: lows get less gain
                x = x - lo + k.shelfA[j] * lo;
            }
            x = -s.tri[j](k.stageGain * x);                               // the stage (inverting)
            x = s.miller[j].lp(x, k.millerG[j]);                          // Miller capacitance
        }
        // tone stack (TDF2)
        const double t = k.b[0] * x + s.ts1;
        s.ts1 = k.b[1] * x - k.a[1] * t + s.ts2;
        s.ts2 = k.b[2] * x - k.a[2] * t + s.ts3;
        s.ts3 = k.b[3] * x - k.a[3] * t;
        x = t;
        // power amp: the sagging push-pull clip. A sagging supply lowers both the clip ceiling (supply) and the
        // stage's gain (sqrt(supply): less plate voltage, less gain), so it compresses below clipping too.
        const double supply = 1.0 / (1.0 + 2.5 * k.sag * s.env);
        double y = supply * (s.paClip(k.paGain * x / std::sqrt(supply) + kBias) - softClip(kBias));
        const double e = std::fabs(y);
        s.env += (e > s.env ? k.envAtt : k.envRel) * (e - s.env);
        // presence / resonance live in the power amp's feedback loop: they shape its OUTPUT even while it clips
        // (in front of the clipper the clipping would flatten them again)
        y += (k.presA - 1.0) * (y - s.pres.lp(y, k.presG));
        const double r = k.rb0 * y + s.r1;
        s.r1 = k.rb1 * y - k.ra1 * r + s.r2;
        s.r2 = k.rb2 * y - k.ra2 * r;
        return r;
    }

    // The preamp gain (6 dB + 5.4 dB per knob step in total) spread evenly over the stages.
    static double stageGain(double gain, int stages) noexcept {
        return std::pow(10.0, (6.0 + 5.4 * gain) / stages / 20.0);
    }
    // The power stage drive: -6 dB + 3 dB per master step, plus the tone stack's insertion loss given back.
    static double paGain(double master) noexcept {
        return std::pow(10.0, (kStackMakeupDb - 6.0 + 3.0 * master) / 20.0);
    }

    // Coefficients from the smoothed knobs (control rate while they move).
    void updateCoefs() noexcept {
        Coefs& k = c_;
        const double gain = knob_[0].value(), boost = knob_[1].value(), tight = knob_[2].value();
        const double bright = knob_[3].value(), bass = knob_[4].value(), mid = knob_[5].value();
        const double treble = knob_[6].value(), presence = knob_[7].value(), reso = knob_[8].value();
        const double master = knob_[9].value();
        k.sag = knob_[10].value();
        k.boost = boost > 1e-3;
        k.tsG = std::pow(10.0, boost / 20.0);
        k.tsHp = tptG(720.0, fs4_);
        k.tsLp = tptG(5000.0, fs4_);
        k.stages = std::clamp(getInt(kAStages), 1, kMaxStages);
        k.stageGain = stageGain(gain, k.stages);
        k.tightG = tptG(tight, fs4_);
        k.brightG = tptG(1200.0, fs4_);
        k.brightA = std::pow(10.0, bright / 20.0);
        static constexpr double kMiller[kMaxStages] = {12000.0, 9000.0, 7000.0, 6000.0};
        static constexpr double kShelfDb[kMaxStages] = {0.0, -6.0, -8.0, -9.0};
        static constexpr double kCouple[kMaxStages] = {0.0, 25.0, 40.0, 60.0};
        for (int i = 0; i < kMaxStages; ++i) {
            const std::size_t j = static_cast<std::size_t>(i);
            k.millerG[j] = tptG(kMiller[i], fs4_);
            k.shelfG[j] = tptG(280.0, fs4_);
            k.shelfA[j] = std::pow(10.0, kShelfDb[i] / 20.0);
            k.coupleG[j] = tptG(std::max(kCouple[i], 5.0), fs4_);
        }
        toneStack(bass, mid, treble);
        k.presG = tptG(3500.0, fs4_);
        k.presA = std::pow(10.0, (presence - 5.0) * 1.4 / 20.0);
        peak(110.0, 0.8, (reso - 5.0) * 1.2);
        k.paGain = paGain(master);
        k.envAtt = 1.0 - std::exp(-1.0 / (0.002 * fs4_));
        k.envRel = 1.0 - std::exp(-1.0 / (0.12 * fs4_));
        k.outG = std::pow(10.0, knob_[11].value() / 20.0) * kOutScale;
    }

    // The TMB tone stack (Yeh & Smith): analog H(s) from the pot positions, bilinear transform at the 4x rate.
    void toneStack(double bass, double mid, double treble) noexcept {
        const bool brit = getInt(kAStack) == 0;
        const double C1 = brit ? 470e-12 : 250e-12, C2 = brit ? 22e-9 : 20e-9, C3 = brit ? 22e-9 : 20e-9;
        const double R1 = brit ? 220e3 : 250e3, R2 = 1e6, R3 = brit ? 22e3 : 25e3, R4 = brit ? 33e3 : 56e3;
        const double t = std::clamp(treble / 10.0, 0.0, 1.0), m = std::clamp(mid / 10.0, 0.0, 1.0);
        const double l = std::exp((std::clamp(bass / 10.0, 0.0, 1.0) - 1.0) * 3.4);   // log taper
        const double b1 = t * C1 * R1 + m * C3 * R3 + l * (C1 * R2 + C2 * R2) + (C1 * R3 + C2 * R3);
        const double b2 = t * (C1 * C2 * R1 * R4 + C1 * C3 * R1 * R4) - m * m * (C1 * C3 * R3 * R3 + C2 * C3 * R3 * R3)
                          + m * (C1 * C3 * R1 * R3 + C1 * C3 * R3 * R3 + C2 * C3 * R3 * R3)
                          + l * (C1 * C2 * R1 * R2 + C1 * C2 * R2 * R4 + C1 * C3 * R2 * R4)
                          + l * m * (C1 * C3 * R2 * R3 + C2 * C3 * R2 * R3)
                          + (C1 * C2 * R1 * R3 + C1 * C2 * R3 * R4 + C1 * C3 * R3 * R4);
        const double C123 = C1 * C2 * C3;
        const double b3 = l * m * (C123 * R1 * R2 * R3 + C123 * R2 * R3 * R4) - m * m * (C123 * R1 * R3 * R3 + C123 * R3 * R3 * R4)
                          + m * (C123 * R1 * R3 * R3 + C123 * R3 * R3 * R4) + t * C123 * R1 * R3 * R4
                          - t * m * C123 * R1 * R3 * R4 + t * l * C123 * R1 * R2 * R4;
        const double a1 = (C1 * R1 + C1 * R3 + C2 * R3 + C2 * R4 + C3 * R4) + m * C3 * R3 + l * (C1 * R2 + C2 * R2);
        const double a2 = m * (C1 * C3 * R1 * R3 - C2 * C3 * R3 * R4 + C1 * C3 * R3 * R3 + C2 * C3 * R3 * R3)
                          + l * m * (C1 * C3 * R2 * R3 + C2 * C3 * R2 * R3) - m * m * (C1 * C3 * R3 * R3 + C2 * C3 * R3 * R3)
                          + l * (C1 * C2 * R2 * R4 + C1 * C2 * R1 * R2 + C1 * C3 * R2 * R4 + C2 * C3 * R2 * R4)
                          + (C1 * C2 * R1 * R4 + C1 * C3 * R1 * R4 + C1 * C2 * R3 * R4 + C1 * C2 * R1 * R3
                             + C1 * C3 * R3 * R4 + C2 * C3 * R3 * R4);
        const double a3 = l * m * (C123 * R1 * R2 * R3 + C123 * R2 * R3 * R4) - m * m * (C123 * R1 * R3 * R3 + C123 * R3 * R3 * R4)
                          + m * (C123 * R3 * R3 * R4 + C123 * R1 * R3 * R3 - C123 * R1 * R3 * R4) + l * C123 * R1 * R2 * R4
                          + C123 * R1 * R3 * R4;
        // bilinear: s^k -> c^k (1 - z^-1)^k (1 + z^-1)^(3-k)
        static constexpr double E[4][4] = {{1, 3, 3, 1}, {1, 1, -1, -1}, {1, -1, -1, 1}, {1, -3, 3, -1}};
        const double c = 2.0 * fs4_;
        const double bs[4] = {0.0, b1 * c, b2 * c * c, b3 * c * c * c};
        const double as[4] = {1.0, a1 * c, a2 * c * c, a3 * c * c * c};
        double B[4] = {0, 0, 0, 0}, A[4] = {0, 0, 0, 0};
        for (int kk = 0; kk < 4; ++kk)
            for (int j = 0; j < 4; ++j) {
                B[j] += bs[kk] * E[kk][j];
                A[j] += as[kk] * E[kk][j];
            }
        for (int j = 0; j < 4; ++j) {   // (the stack's insertion loss is given back in the power amp's paGain)
            c_.b[j] = B[j] / A[0];
            c_.a[j] = A[j] / A[0];
        }
    }

    // RBJ peaking EQ at the 4x rate (the resonance control).
    void peak(double f, double q, double db) noexcept {
        const double A = std::pow(10.0, db / 40.0), w = 2.0 * dsp::kPi * f / fs4_;
        const double al = std::sin(w) / (2.0 * q), cw = std::cos(w);
        const double a0 = 1.0 + al / A;
        c_.rb0 = (1.0 + al * A) / a0;
        c_.rb1 = (-2.0 * cw) / a0;
        c_.rb2 = (1.0 - al * A) / a0;
        c_.ra1 = (-2.0 * cw) / a0;
        c_.ra2 = (1.0 - al / A) / a0;
    }

    double fs4_{192000.0};
    hb::HalfBand<kN1>::Coefs hb1_{};
    hb::HalfBand<kN2>::Coefs hb2_{};
    hb::HalfBand<kN1> up1_, dn1_;
    hb::HalfBand<kN2> up2_, dn2_;
    Chan ch_[2];
    Coefs c_;
    Smooth2 knob_[kKnobs];
    double dcR_{0.999};
    bool mono_{true}, gliding_{false};
    int ctl_{0};
};

}  // namespace

std::unique_ptr<Effect> makeAmp() { return std::make_unique<Amp>(); }

}  // namespace as::timefx
