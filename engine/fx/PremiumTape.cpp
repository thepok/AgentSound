// tape: tape-machine colour (warm 80s multitrack / cassette).
//
//   x -> drive -> pre-emphasis (high shelf) -> 4x oversampled asymmetric tanh saturation (polyphase
//        IIR half-bands, fx/HalfBand.h) -> de-emphasis (exact inverse shelf): loud highs saturate
//        first, as on tape (level-dependent HF compression)
//     -> transport: wow (slow, capstan sine + random drift) and flutter (fast, two sines + scrape
//        noise) as a modulated delay, seeded, stereo-linked or independent per side
//     -> + hiss (off by default) -> low roll-off, head bump (+ the dip above it), high roll-off (per
//        tape speed) -> dry/wet mix (the dry passes the same half-bands and transport delay, so a
//        parallel blend stays phase-coherent) -> output gain.
//
// The transport delays the whole effect (wet and dry alike) by the current wow / flutter depth only:
// ~0.2 ms at the defaults, ~1 sample without wow and flutter, up to ~2.7 ms at wow = flutter = 1 on
// cassette (the delay a pitch modulation needs; tracks are not latency-compensated).

#include "fx/HalfBand.h"
#include "fx/PremiumUtil.h"

namespace as::premium {
namespace {

using namespace timefx;
using hb::D2;
using hb::d2;
using hb::HalfBand;

enum TapeParam { kTSpeed, kTDrive, kTBias, kTBump, kTWow, kTFlutter, kTLink, kTHiss, kTMix, kTOutput };

struct TapeSpeed {
    double bumpHz, lpHz, hpHz;      // head bump centre, HF and LF roll-off (-3 dB)
    double preDb, preHz;            // record pre-emphasis (undone after the curve)
    double wowScale, flutterScale;  // transport quality
    double flutterHz;
};
constexpr TapeSpeed kSpeeds[4] = {
    // bump   lp     hp   pre   preHz wow  flut  flHz
    {60.0, 10500.0, 30.0, 9.0, 2500.0, 1.4, 1.5, 9.5},   // cassette (1 7/8 ips)
    {70.0, 14000.0, 25.0, 6.0, 3000.0, 1.2, 1.2, 7.8},   // 7.5 ips
    {90.0, 18500.0, 25.0, 4.0, 4000.0, 1.0, 1.0, 7.0},   // 15 ips
    {120.0, 22000.0, 35.0, 3.0, 5000.0, 0.8, 0.8, 6.3},  // 30 ips
};

// Peak pitch deviation at wow / flutter = 1 (scaled by the speed): 0.6 % wow, 0.15 % flutter.
constexpr double kWowDev = 0.006, kFlutterDev = 0.0015;
constexpr double kWowHz = 0.55, kWowDriftHz = 0.9, kFlutter2Mul = 1.63, kScrapeHz = 13.0;
// Smoothing of wow / flutter changes (2-pole). The transport delay is centre + modulation, both
// proportional to the depth: a depth change moves the delay by up to twice its amplitude (~170
// samples at wow 1 on 15 ips): a 20 ms glide bent the pitch by ~2 %. At 0.25 s even a
// 0 <-> 1 jump bends it by less than ~0.3 % (a few cents).
constexpr double kDepthTau = 0.25;

ParamSpec fixedToggle(std::string name, bool def, std::string help) {
    ParamSpec s = toggle(std::move(name), def, std::move(help));
    s.automatable = false;
    return s;
}

const std::vector<ParamSpec>& tapeSpecs() {
    static const std::vector<ParamSpec> s = {
        choice("speed", {"cassette", "7.5", "15", "30"}, 2,
               "Tape speed (ips): sets head bump, HF roll-off and transport. cassette = dark lo-fi (bump 60 Hz, top ~10.5 "
               "kHz, more wow), 7.5 = warm (70 Hz, ~14 kHz), 15 = classic 80s multitrack (90 Hz, ~18.5 kHz), 30 = "
               "hi-fi mastering deck (120 Hz, full top)"),
        num("drive", -12, 24, 3, "dB",
            "Record level into the tape: 0-6 = gentle glue and warmth (default: -12 dBFS peaks get ~1 % 3rd harmonic), "
            "9-15 = obvious saturation, 18+ = squashed. Small signals keep their level (auto-compensated); loud peaks "
            "and highs compress. On a hot master/bus use -6..0"),
        num("bias", 0, 1, 0.2f, "", "Asymmetry of the tape curve (like an under-biased machine): adds even harmonics"),
        num("bump", 0, 6, 2, "dB", "Head bump: low-end lift at the speed's bump frequency (2-3 dB = classic tape bass)"),
        num("wow", 0, 1, 0.1f, "", "Wow: slow pitch drift (~0.5 Hz; 1 = +-0.6 % seasick warble, 0.1-0.2 subtle). Changes glide over ~0.5 s"),
        num("flutter", 0, 1, 0.1f, "", "Flutter: fast pitch shimmer (~7-10 Hz with scrape noise; 1 = worn machine). Changes glide over ~0.5 s"),
        fixedToggle("link", true, "on: both sides share one transport (real tape); off: independent wow/flutter per side (wide, lo-fi)"),
        num("hiss", 0, 1, 0, "", "Tape hiss level: 0 = off, 0.3 ~ -75 dBFS (quiet), 1 ~ -50 dBFS (worn cassette)"),
        num("mix", 0, 1, 1, "", "Dry/tape blend (phase-coherent); 1 = full tape"),
        num("output", -24, 12, 0, "dB", "Output gain"),
    };
    return s;
}

class Tape final : public ParamEffect {
    // Oversampling: 1x <-> 2x (8 coefficients, passband to 21.6 kHz at 48k, ~106 dB stopband),
    // 2x <-> 4x (4 coefficients, wide transition, ~117 dB): as the saturator.
    static constexpr int kN1 = 8, kN2 = 4;

public:
    Tape() : ParamEffect(tapeSpecs(), "tape") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        spd_ = kSpeeds[std::clamp(getInt(kTSpeed), 0, 3)];
        link_ = on(kTLink);
        hb1_ = hb::designHalfBand<kN1>(0.05);
        hb2_ = hb::designHalfBand<kN2>(0.25);
        up1_.reset(); up2_.reset(); dn1_.reset(); dn2_.reset(); dn1Dry_.reset(); dn2Dry_.reset();
        for (int c = 0; c < 2; ++c) {
            pre_[c].set(dsp::Biquad::Type::HighShelf, sr_, spd_.preHz, 0.7071, spd_.preDb);
            de_[c].set(dsp::Biquad::Type::HighShelf, sr_, spd_.preHz, 0.7071, -spd_.preDb);
            deDry_[c] = de_[c];
            pre_[c].reset(); de_[c].reset(); deDry_[c].reset();
            hp_[c] = TptFilter(TptFilter::Mode::High);
            lp_[c] = TptFilter(TptFilter::Mode::Low);
            hp_[c].setCutoff(sr_, spd_.hpHz, 0);
            lp_[c].setCutoff(sr_, std::min(spd_.lpHz, 0.45 * sr_), 0);
            bump_[c].setFreq(sr_, spd_.bumpHz);
            dip_[c].setFreq(sr_, 2.3 * spd_.bumpHz);
            bump_[c].reset();
            dip_[c].reset();
            hissHp_[c].setLowPass(sr_, 400.0);
            hissHp_[c].reset();
        }
        // transport: modulation amplitudes in samples (deviation = 2 pi f A / sr); the centre delay
        // follows the current wow / flutter depth (0 at wow = flutter = 0), the lines hold the deepest
        wowAmp_ = kWowDev * spd_.wowScale * sr_ / (dsp::kTwoPi * kWowHz);
        flAmp_ = kFlutterDev * spd_.flutterScale * sr_ / (dsp::kTwoPi * spd_.flutterHz);
        maxCenter_ = std::ceil(wowAmp_ + flAmp_) + 4.0;
        for (int c = 0; c < 2; ++c) {
            line_[c].init(static_cast<int>(2.0 * maxCenter_) + 8);
            dryLine_[c].init(static_cast<int>(maxCenter_) + 8);
        }
        const std::uint64_t seed = ctx.seed ^ dsp::hashString("premium.tape");
        dsp::Rng rng(seed);
        const double t0 = startSeconds();
        for (int c = 0; c < 2; ++c) {
            // one transport per side (the right one is only used unlinked); runs from the song start
            wowPh_[c] = wrap01(rng.uniform() + kWowHz * t0);
            flPh_[c] = wrap01(rng.uniform() + spd_.flutterHz * t0);
            flPh2_[c] = wrap01(rng.uniform() + kFlutter2Mul * spd_.flutterHz * t0);
            drift_[c].reset(seed + 11 + c);
            drift_[c].skip(kWowDriftHz * t0);
            scrape_[c].reset(seed + 23 + c);
            scrape_[c].skip(kScrapeHz * t0);
            hissSeed_[c] = seed * 31 + 7 + static_cast<std::uint64_t>(c) * 0x51ED270B27u;
        }
        drive_.prepare(sr_, 0.0015, get(kTDrive));
        bias_.prepare(sr_, 0.0015, get(kTBias));
        bumpDb_.prepare(sr_, 0.0015, get(kTBump));
        wow_.prepare(sr_, kDepthTau, get(kTWow));
        flutter_.prepare(sr_, kDepthTau, get(kTFlutter));
        hissG_.prepare(sr_, 0.0015, hissGain(get(kTHiss)));
        mix_.prepare(sr_, 0.0015, get(kTMix));
        out_.prepare(sr_, 0.0015, dsp::dbToGain(get(kTOutput)));
        shape_ = shapeFor(drive_.value(), bias_.value());
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) pullTargets();
        forEachCtrlBlock(pos_, frames, [&](int off, int n, bool) { block(left + off, right + off, n); });
        up1_.flush(); up2_.flush(); dn1_.flush(); dn2_.flush(); dn1Dry_.flush(); dn2Dry_.flush();
    }

    double tailSeconds() const override { return 2.0 * maxCenter_ / sr_ + 0.05; }

private:
    struct Shape {
        float d{1.0f}, b{0.0f}, tb{0.0f}, nrm{1.0f};  // drive, bias offset, tanh(bias), 1/(d sech^2 b)
    };
    static Shape shapeFor(float driveDb, float bias) {
        Shape s;
        s.d = dsp::dbToGain(driveDb);
        s.b = 0.4f * bias;
        s.tb = std::tanh(s.b);
        s.nrm = 1.0f / (s.d * (1.0f - s.tb * s.tb));
        return s;
    }
    static float curve(float x, const Shape& s) noexcept { return (std::tanh(s.d * x + s.b) - s.tb) * s.nrm; }
    static float hissGain(float amount) {
        return amount <= 0.0f ? 0.0f : dsp::dbToGain(-85.0f + 35.0f * amount) * 1.7320508f;  // uniform: RMS 1/sqrt3
    }

    void block(float* L, float* R, int n) noexcept {
        for (int k = 0; k < n; ++k) {
            // saturation stage (4x)
            const Shape prev = shape_;
            if (drive_.moving() || bias_.moving()) shape_ = shapeFor(drive_.next(), bias_.next());
            const D2 x = d2(pre_[0].process(L[k]), pre_[1].process(R[k]));
            D2 a0, a1, u[4];
            up1_.up(hb1_, x, a0, a1);
            up2_.up(hb2_, a0, u[0], u[1]);
            up2_.up(hb2_, a1, u[2], u[3]);
            D2 w[4];
            for (int i = 0; i < 4; ++i) {
                Shape s = shape_;
                if (prev.d != shape_.d || prev.b != shape_.b) {  // glide the curve per 4x sample
                    const float f = 0.25f * static_cast<float>(i + 1);
                    s.d = prev.d + (shape_.d - prev.d) * f;
                    s.b = prev.b + (shape_.b - prev.b) * f;
                    s.tb = prev.tb + (shape_.tb - prev.tb) * f;
                    s.nrm = prev.nrm + (shape_.nrm - prev.nrm) * f;
                }
                w[i] = d2(curve(static_cast<float>(u[i][0]), s), curve(static_cast<float>(u[i][1]), s));
            }
            const D2 h0 = dn2_.down(hb2_, w[0], w[1]);
            const D2 h1 = dn2_.down(hb2_, w[2], w[3]);
            const D2 y = dn1_.down(hb1_, h0, h1);
            const D2 g0 = dn2Dry_.down(hb2_, u[0], u[1]);
            const D2 g1 = dn2Dry_.down(hb2_, u[2], u[3]);
            const D2 yd = dn1Dry_.down(hb1_, g0, g1);

            // transport: centre delay = the current modulation depth, the deepest the modulation can go
            // (no delay beyond that: 1 sample + the half-bands' ~5 without wow and flutter)
            const float wow = wow_.next(), flutter = flutter_.next();
            const double center = wow * wowAmp_ + flutter * flAmp_;
            double mod[2];
            for (int c = 0; c < 2; ++c) {
                if (c == 1 && link_) {
                    mod[1] = mod[0];
                    continue;
                }
                wowPh_[c] = wrap01(wowPh_[c] + kWowHz / sr_);
                flPh_[c] = wrap01(flPh_[c] + spd_.flutterHz / sr_);
                flPh2_[c] = wrap01(flPh2_[c] + kFlutter2Mul * spd_.flutterHz / sr_);
                const float dr = drift_[c].next(kWowDriftHz / sr_);
                const float sc = scrape_[c].next(kScrapeHz / sr_);
                mod[c] = wow * wowAmp_ * (0.6f * sinCycles(wowPh_[c]) + 0.4f * dr) +
                         flutter * flAmp_ * (0.6f * sinCycles(flPh_[c]) + 0.25f * sinCycles(flPh2_[c]) + 0.15f * sc);
            }
            const float hg = hissG_.next(), bump = bumpDb_.next(), mix = mix_.next(), og = out_.next();
            const std::uint64_t songSample = pos_ + static_cast<std::uint64_t>(k);
            float* io[2] = {L, R};
            for (int c = 0; c < 2; ++c) {
                line_[c].write(de_[c].process(static_cast<float>(y[c])));
                dryLine_[c].write(deDry_[c].process(static_cast<float>(yd[c])));
                // read after the write: delay 1 = this sample, 2 = the shortest cubic read (1 sample late)
                float v = line_[c].tapCubic(2.0 + center + mod[c]);
                const float dry = dryLine_[c].tapCubic(2.0 + center);
                if (hg > 0.0f) v += hg * hissHp_[c].highPass(counterNoise(hissSeed_[c], songSample));
                v = lp_[c].process(hp_[c].process(v));
                v = static_cast<float>(dip_[c].bell(bump_[c].bell(v, bump, 1.0), -0.35 * bump, 1.4));
                io[c][k] = (dry + mix * (v - dry)) * og;
            }
        }
    }

    void pullTargets() {
        drive_.setTarget(get(kTDrive));
        bias_.setTarget(get(kTBias));
        bumpDb_.setTarget(get(kTBump));
        wow_.setTarget(get(kTWow));
        flutter_.setTarget(get(kTFlutter));
        hissG_.setTarget(hissGain(get(kTHiss)));
        mix_.setTarget(get(kTMix));
        out_.setTarget(dsp::dbToGain(get(kTOutput)));
    }

    TapeSpeed spd_{kSpeeds[2]};
    bool link_{true};
    HalfBand<kN1>::Coefs hb1_{};
    HalfBand<kN2>::Coefs hb2_{};
    HalfBand<kN1> up1_, dn1_, dn1Dry_;
    HalfBand<kN2> up2_, dn2_, dn2Dry_;
    dsp::Biquad pre_[2], de_[2], deDry_[2];
    TptFilter hp_[2], lp_[2];
    Svf bump_[2], dip_[2];
    dsp::OnePole hissHp_[2];
    RingDelay line_[2], dryLine_[2];
    SmoothNoise drift_[2], scrape_[2];
    double wowPh_[2]{}, flPh_[2]{}, flPh2_[2]{};
    double wowAmp_{0.0}, flAmp_{0.0}, maxCenter_{8.0};
    std::uint64_t hissSeed_[2]{};
    Smooth2 drive_, bias_, bumpDb_, wow_, flutter_, hissG_, mix_, out_;
    Shape shape_{};
};

}  // namespace

std::unique_ptr<Effect> makeTape() { return std::make_unique<Tape>(); }

}  // namespace as::premium
