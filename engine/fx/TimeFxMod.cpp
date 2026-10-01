// Modulation effects: chorus (Juno-60 BBD modes + custom), flanger, phaser, tremolo.

#include "fx/TimeFxUtil.h"

namespace as::timefx {
namespace {

using dsp::Smoother;

// Automation smoothing (see Smooth2): gains/mixes glide in ~5 ms (10-90 %), feedback and filter /
// sweep settings in ~7 ms. Parameters that move a delay time (depth, delay, stereo phase of a swept
// delay) glide slower on purpose: a fast delay-time change is an audible pitch jump. LFO rates glide
// over ~50 ms (the LFO phase itself is always continuous).
constexpr double kGainTau = 0.0015;
constexpr double kFbTau = 0.002;
constexpr double kToneTau = 0.002;
constexpr double kDelayTau = 0.025;
constexpr double kRateTau = 0.05;

// ---------------------------------------------------------------------------------------------
// Chorus
// ---------------------------------------------------------------------------------------------

enum ChorusParam { kCMode, kCMix, kCRate, kCDepth, kCDelay, kCVoices, kCSpread, kCFeedback, kCTone, kCNoise };

const std::vector<ParamSpec>& chorusSpecs() {
    static const std::vector<ParamSpec> s = {
        choice("mode", {"I", "II", "I+II", "custom"}, 0,
               "Juno-60 chorus: I = gentle slow sweep (0.51 Hz), II = deeper, faster, lusher (0.86 Hz), "
               "I+II = fast shallow shimmer/vibrato (9.75 Hz); custom = use rate/depth/delay/voices/spread/feedback"),
        num("mix", 0, 1, 0.5f, "", "Dry/wet balance (equal power); 0.5 = the classic Juno balance (equal dry and chorus)"),
        num("rate", 0.01f, 10, 0.8f, "Hz", "custom mode: LFO rate"),
        num("depth", 0, 10, 2, "ms", "custom mode: peak delay modulation (more = more pitch wobble)"),
        num("delay", 0.5f, 40, 7, "ms",
            "custom mode: centre delay; 2-5 ms tight, 7-20 ms classic chorus, 25-40 ms doubling "
            "(raised to depth + 0.1 ms when 'depth' is larger, so the sweep never hits zero)"),
        num("voices", 1, 4, 2, "", "custom mode: chorus voices per side (integer 1..4), LFO phases evenly spread", false),
        num("spread", 0, 1, 1, "", "custom mode: stereo spread; 0 = mono chorus, 1 = right-side LFOs halfway between the left ones (widest)"),
        num("feedback", -0.9f, 0.9f, 0, "", "custom mode: feedback into the delay (adds flanger-like resonance)"),
        num("tone", 2000, 20000, 10000, "Hz", "Low-pass on the chorus signal (bucket-brigade character; ~10 kHz like the Juno)"),
        num("noise", 0, 1, 0, "", "Bucket-brigade hiss on the chorus signal (1 = authentic noisy Juno, about -60 dBFS)"),
    };
    return s;
}

struct JunoMode { double rateHz, centreMs, swingMs; };
// Juno-60 measurements: triangle LFO, BBD delay swept 1.66..5.35 ms (I, II), 3.3..3.7 ms (I+II);
// right channel uses the inverted LFO.
constexpr JunoMode kJuno[3] = {{0.513, 3.505, 1.845}, {0.863, 3.505, 1.845}, {9.75, 3.5, 0.2}};

class Chorus final : public ParamEffect {
public:
    Chorus() : ParamEffect(chorusSpecs(), "chorus") {}

    void configure(const json& params) override {
        ParamEffect::configure(params);
        requireInteger("voices");
    }

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        msToS_ = sr_ / 1000.0;
        for (auto& l : line_) l.init(static_cast<int>(std::ceil(0.052 * sr_)) + 4);
        rng_.reseed(ctx.seed ^ dsp::hashString("timefx.chorus"));
        mode_ = std::clamp(getInt(kCMode), 0, 3);
        voices_ = std::clamp(getInt(kCVoices), 1, 4);
        // free-running LFO: a preview render starts where a full render (at a constant rate) would be
        phase_ = wrap01((mode_ < 3 ? kJuno[mode_].rateHz : get(kCRate)) * startSeconds());
        float dry, wet;
        equalPowerMix(get(kCMix), dry, wet);
        dry_.prepare(sr_, kGainTau, dry);
        wet_.prepare(sr_, kGainTau, wet);
        rate_.prepare(sr_, kRateTau, get(kCRate));
        depth_.prepare(sr_, kDelayTau, get(kCDepth));
        delay_.prepare(sr_, kDelayTau, get(kCDelay));
        spread_.prepare(sr_, kDelayTau, get(kCSpread));
        fb_.prepare(sr_, kFbTau, get(kCFeedback));
        noise_.prepare(sr_, kGainTau, get(kCNoise));
        tone_.snap(get(kCTone));
        toneK_ = ctrlCoeff(sr_, kCtrl, kToneTau);
        setTone(tone_.v, 0);
        for (auto& f : tone2_) f.reset();
        for (auto& n : noiseLp_) { n.setLowPass(sr_, 7000.0); n.reset(); }
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) pullTargets();
        float* io[2] = {left, right};
        forEachCtrlBlock(pos_, frames, [&](int start, int len, bool tick) {
            if (tick && tone_.step(toneK_)) setTone(tone_.v, kCtrl);
            for (int n = start; n < start + len; ++n) {
                const float dg = dry_.next(), wg = wet_.next();
                const float noiseAmp = 0.0026f * noise_.next();
                double d[2][4];
                int nv = 1;
                float fb = 0.0f;
                if (mode_ < 3) {
                    const JunoMode& m = kJuno[mode_];
                    phase_ = wrap01(phase_ + m.rateHz / sr_);
                    for (int ch = 0; ch < 2; ++ch)
                        d[ch][0] = (m.centreMs + m.swingMs * triCycles(phase_ + 0.5 * ch)) * msToS_;
                } else {
                    phase_ = wrap01(phase_ + rate_.next() / sr_);
                    const double depth = depth_.next(), spread = spread_.next();
                    const double delay = std::max<double>(delay_.next(), depth + 0.1);  // sweep stays > 0
                    fb = fb_.next();
                    nv = voices_;
                    // right-side voices sit halfway between the left ones at spread 1 (inverted for 1 voice)
                    for (int ch = 0; ch < 2; ++ch)
                        for (int v = 0; v < nv; ++v) {
                            const double ph = phase_ + (v + 0.5 * spread * ch) / nv;
                            d[ch][v] = (delay + depth * sinCycles(ph)) * msToS_;
                        }
                }
                const float norm = 1.0f / std::sqrt(static_cast<float>(nv));  // voices are mostly decorrelated
                for (int ch = 0; ch < 2; ++ch) {
                    const float x = io[ch][n];
                    float wet = 0.0f;
                    for (int v = 0; v < nv; ++v) wet += line_[ch].tapCubic(d[ch][v]);
                    wet *= norm;
                    line_[ch].write(dsp::flush(x + softSat(fb * wet)));
                    float w = tone2_[ch].process(wet);
                    w += noiseAmp * noiseLp_[ch].lowPass(rng_.bipolar());
                    io[ch][n] = dg * x + wg * w;
                }
            }
        });
    }

    double tailSeconds() const override {
        const double fb = std::fabs(get(kCFeedback));
        return 0.06 + (fb > 0.01 ? 0.05 * 3.0 / -std::log10(fb) : 0.0);
    }

private:
    void pullTargets() {
        float dry, wet;
        equalPowerMix(get(kCMix), dry, wet);
        dry_.setTarget(dry);
        wet_.setTarget(wet);
        rate_.setTarget(get(kCRate));
        depth_.setTarget(get(kCDepth));
        delay_.setTarget(get(kCDelay));
        spread_.setTarget(get(kCSpread));
        fb_.setTarget(get(kCFeedback));
        noise_.setTarget(get(kCNoise));
        tone_.t = get(kCTone);
    }
    void setTone(float hz, int samples) {
        for (auto& f : tone2_) f.setCutoff(sr_, hz, samples);
    }

    RingDelay line_[2];
    TptFilter tone2_[2];  // low-pass, ramped per sample
    dsp::OnePole noiseLp_[2];
    dsp::Rng rng_;
    Smoother rate_;
    Smooth2 dry_, wet_, depth_, delay_, spread_, fb_, noise_;
    CtrlSmooth tone_;
    float toneK_{0.0f};
    double phase_{0.0}, msToS_{48.0};
    int mode_{0}, voices_{2};
};

// ---------------------------------------------------------------------------------------------
// Flanger
// ---------------------------------------------------------------------------------------------

enum FlangerParam { kFRate, kFDepth, kFDelay, kFFeedback, kFMix, kFStereo };

const std::vector<ParamSpec>& flangerSpecs() {
    static const std::vector<ParamSpec> s = {
        num("rate", 0.01f, 10, 0.2f, "Hz", "Sweep rate (one full up-and-down sweep per cycle; 0.05-0.3 for jet sweeps)"),
        num("depth", 0, 1, 0.7f, "", "Sweep width: 1 = delay sweeps 4 octaves up from 'delay', 0 = static comb"),
        num("delay", 0.1f, 10, 0.5f, "ms", "Shortest delay of the sweep (sets the highest notch frequency)"),
        num("feedback", -0.95f, 0.95f, 0.5f, "", "Resonance: positive = metallic jet, negative = hollow; level is compensated"),
        num("mix", 0, 1, 0.5f, "", "Dry/wet balance (level-compensated); 0.5 = deepest notches"),
        num("stereo", 0, 180, 90, "deg", "LFO phase offset of the right channel (0 = mono sweep, 90-180 = wide)"),
    };
    return s;
}

class Flanger final : public ParamEffect {
public:
    Flanger() : ParamEffect(flangerSpecs(), "flanger") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        msToS_ = sr_ / 1000.0;
        for (auto& l : line_) l.init(static_cast<int>(std::ceil(0.165 * sr_)) + 4);
        phase_ = wrap01(get(kFRate) * startSeconds());
        rate_.prepare(sr_, kRateTau, get(kFRate));
        depth_.prepare(sr_, kDelayTau, get(kFDepth));
        delay_.prepare(sr_, kDelayTau, get(kFDelay));
        fb_.prepare(sr_, kFbTau, get(kFFeedback));
        float dry, wet;
        notchMix(get(kFMix), dry, wet);
        dry_.prepare(sr_, kGainTau, dry);
        wet_.prepare(sr_, kGainTau, wet);
        stereo_.prepare(sr_, kDelayTau, get(kFStereo));
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) {
            rate_.setTarget(get(kFRate));
            depth_.setTarget(get(kFDepth));
            delay_.setTarget(get(kFDelay));
            fb_.setTarget(get(kFFeedback));
            float dry, wet;
            notchMix(get(kFMix), dry, wet);
            dry_.setTarget(dry);
            wet_.setTarget(wet);
            stereo_.setTarget(get(kFStereo));
        }
        float* io[2] = {left, right};
        for (int n = 0; n < frames; ++n) {
            phase_ = wrap01(phase_ + rate_.next() / sr_);
            const float depth = depth_.next(), delayMs = delay_.next(), fb = fb_.next();
            const float dg = dry_.next();
            // Flat broadband level vs feedback: the comb's mean power gain 1/(1 - fb^2) is compensated where the
            // signal enters the loop, so a fast feedback change never re-scales the energy stored in the line
            // (compensating at the output made a feedback swing through 0 burst out the stored resonance).
            const float wg = wet_.next(), in = std::sqrt(std::max(0.0f, 1.0f - fb * fb));
            const double st = stereo_.next() / 360.0;
            for (int ch = 0; ch < 2; ++ch) {
                const float u = 0.5f * (1.0f + triCycles(phase_ + st * ch));
                const double d = delayMs * std::exp2(4.0f * depth * u) * msToS_;
                const float x = io[ch][n];
                const float w = line_[ch].tapCubic(d);
                line_[ch].write(dsp::flush(in * x + softSat(fb * w)));
                io[ch][n] = dg * x + wg * w;
            }
        }
    }

    double tailSeconds() const override {
        const double fb = std::fabs(get(kFFeedback));
        const double maxDelay = get(kFDelay) * std::exp2(4.0 * get(kFDepth)) * 1e-3;
        return maxDelay + (fb > 0.01 ? maxDelay * 3.0 / -std::log10(fb) : 0.0) + 0.01;
    }

private:
    RingDelay line_[2];
    Smoother rate_;
    Smooth2 depth_, delay_, fb_, dry_, wet_, stereo_;
    double phase_{0.0}, msToS_{48.0};
};

// ---------------------------------------------------------------------------------------------
// Phaser
// ---------------------------------------------------------------------------------------------

enum PhaserParam { kPStages, kPRate, kPSync, kPBeats, kPDepth, kPFeedback, kPCentre, kPMix, kPStereo };

const std::vector<ParamSpec>& phaserSpecs() {
    static const std::vector<ParamSpec> s = {
        num("stages", 4, 12, 6, "", "Number of all-pass stages (integer 4..12): 4 = subtle (Phase 90), 8-12 = deep, more notches", false),
        num("rate", 0.01f, 10, 0.3f, "Hz", "LFO rate (when sync is off)"),
        toggle("sync", false, "Tempo-sync the LFO: period = 'beats' instead of 'rate'"),
        num("beats", 0.25f, 32, 4, "beats", "LFO period in beats when sync is on (4 = one bar in 4/4)"),
        num("depth", 0, 1, 0.7f, "", "Sweep range: 1 = +-2.5 octaves around 'centre'"),
        num("feedback", -0.95f, 0.95f, 0.4f, "",
            "Resonance of the notches (negative shifts the notch pattern); broadband level is compensated"),
        num("centre", 100, 8000, 700, "Hz", "Centre frequency of the sweep"),
        num("mix", 0, 1, 0.5f, "", "Dry/wet balance (level-compensated); 0.5 = deepest notches"),
        num("stereo", 0, 180, 90, "deg", "LFO phase offset of the right channel"),
    };
    return s;
}

class Phaser final : public ParamEffect {
public:
    Phaser() : ParamEffect(phaserSpecs(), "phaser") {}

    void configure(const json& params) override {
        ParamEffect::configure(params);
        requireInteger("stages");
    }

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        stages_ = std::clamp(getInt(kPStages), 4, 12);
        hz_.prepare(sr_, kRateTau, get(kPRate));
        // Synced: phase from the song position; free: a preview render starts where a full render at a
        // constant rate would be.
        phase_ = on(kPSync) ? gridPhase(songBeat(), get(kPBeats)) : wrap01(get(kPRate) * startSeconds());
        fb_.prepare(sr_, kFbTau, get(kPFeedback));
        float dry, wet;
        notchMix(get(kPMix), dry, wet);
        dry_.prepare(sr_, kGainTau, dry);
        wet_.prepare(sr_, kGainTau, wet);
        for (int ch = 0; ch < 2; ++ch) sweep_[ch].prepare(sr_, kToneTau, sweepTarget(sweep(), ch));
        for (auto& ch : z_) std::fill(std::begin(ch), std::end(ch), 0.0f);
        last_[0] = last_[1] = 0.0f;
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) {
            hz_.setTarget(get(kPRate));
            fb_.setTarget(get(kPFeedback));
            float dry, wet;
            notchMix(get(kPMix), dry, wet);
            dry_.setTarget(dry);
            wet_.setTarget(wet);
        }
        float* io[2] = {left, right};
        const double nyqLimit = 0.45 * sr_;
        const bool sync = on(kPSync);
        const double beats = get(kPBeats);
        const Sweep sw = sweep();
        for (int n = 0; n < frames; ++n) {
            // Synced: phase straight from the song grid (a 'beats'/'sync' change jumps it; the sweep
            // smoother turns that into a fast glide). Free: integrated (smoothed) rate.
            const float hz = hz_.next();
            phase_ = sync ? gridPhase(songBeat(), beats) : wrap01(phase_ + hz / sr_);
            ++pos_;
            const float fb = fb_.next(), dg = dry_.next();
            // A/(1 - fb*A) with |A| = 1 has mean power 1/(1 - fb^2): the broadband level is kept flat by
            // scaling the loop input (not the output: see the flanger), click-free under fast feedback changes
            const float wg = wet_.next(), in = std::sqrt(std::max(0.0f, 1.0f - fb * fb));
            for (int ch = 0; ch < 2; ++ch) {
                sweep_[ch].setTarget(sweepTarget(sw, ch));
                const double f = std::clamp(std::exp2(static_cast<double>(sweep_[ch].next())), 20.0, nyqLimit);
                const double t = std::tan(dsp::kPi * f / sr_);
                const float a = static_cast<float>((t - 1.0) / (t + 1.0));
                const float x = io[ch][n];
                float v = in * x + softSat(fb * last_[ch]);
                float* z = z_[ch];
                for (int s = 0; s < stages_; ++s) {  // first-order all-pass: H = (a + z^-1) / (1 + a z^-1)
                    const float y = a * v + z[s];
                    z[s] = dsp::flush(v - a * y);
                    v = y;
                }
                last_[ch] = dsp::flush(v);
                io[ch][n] = dg * x + wg * v;
            }
        }
    }

    // Resonances ring for (loop group delay) x (loops to -60 dB); the all-pass chain's group delay
    // is largest at the bottom of the sweep: stages / (pi * f) seconds.
    double tailSeconds() const override {
        const double fb = std::fabs(get(kPFeedback));
        const double fLow = std::max(20.0, get(kPCentre) * std::exp2(-2.5 * get(kPDepth)));
        const double loop = std::clamp(getInt(kPStages), 4, 12) / (dsp::kPi * fLow);
        return 0.05 + (fb > 0.01 ? std::min(10.0, loop * 3.0 / -std::log10(fb)) : 0.0);
    }

private:
    // log2 of one channel's all-pass frequency: centre +- 2.5 octaves x depth x LFO. Centre, depth,
    // stereo offset and LFO phase jumps (sync / beats changes) all glide through sweep_.
    struct Sweep {
        float logCentre, range;
        double stereo;
    };
    Sweep sweep() const { return {std::log2(get(kPCentre)), 2.5f * get(kPDepth), get(kPStereo) / 360.0}; }
    float sweepTarget(const Sweep& s, int ch) const {
        return s.logCentre + s.range * sinCycles(phase_ + (ch ? s.stereo : 0.0));
    }

    float z_[2][12]{};
    float last_[2]{};
    Smoother hz_;
    Smooth2 fb_, dry_, wet_, sweep_[2];
    double phase_{0.0};
    int stages_{6};
};

// ---------------------------------------------------------------------------------------------
// Tremolo / autopan
// ---------------------------------------------------------------------------------------------

enum TremoloParam { kTRate, kTSync, kTBeats, kTDepth, kTShape, kTStereo };

const std::vector<ParamSpec>& tremoloSpecs() {
    static const std::vector<ParamSpec> s = {
        num("rate", 0.05f, 20, 5, "Hz", "LFO rate (when sync is off)"),
        toggle("sync", false, "Tempo-sync: period = 'beats', phase-locked to the song grid"),
        num("beats", 0.0625f, 8, 0.25f, "beats", "LFO period in beats when sync is on: 0.25 = 16ths, 0.5 = 8ths, 1 = quarters"),
        num("depth", 0, 1, 0.5f, "", "Modulation depth: level swings between 1 and 1-depth (1 = full chop)"),
        choice("shape", {"sine", "triangle", "square"}, 0,
               "LFO shape; sine/triangle peak on the beat; square = trance-gate chop, open for the first half "
               "of each period with ~4 ms click-free edges"),
        num("stereo", 0, 180, 0, "deg", "Right-channel LFO phase offset; 180 = autopan (left/right alternate)"),
    };
    return s;
}

class Tremolo final : public ParamEffect {
public:
    Tremolo() : ParamEffect(tremoloSpecs(), "tremolo") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        shape_ = std::clamp(getInt(kTShape), 0, 2);
        hz_.prepare(sr_, kRateTau, get(kTRate));
        depth_.prepare(sr_, kGainTau, get(kTDepth));
        // Synced: the phase comes from the song position; free: a preview starts where a full render
        // at a constant rate would be. The gain smoothers are pre-rolled over the last ~20 ms before
        // the start (from the song start if closer), so their lag matches a full render too.
        const bool sync = on(kTSync);
        const float hz = sync ? syncHz() : get(kTRate);
        const float depth = get(kTDepth);
        const double stereo = get(kTStereo) / 360.0;
        const std::int64_t start = static_cast<std::int64_t>(startSample_);
        const std::int64_t n0 = std::max<std::int64_t>(0, start - static_cast<std::int64_t>(0.02 * sr_));
        phase_ = n0 == 0 ? 0.0 : phaseAt(n0 - 1, sync, hz);
        for (int ch = 0; ch < 2; ++ch)
            gain_[ch].prepare(sr_, kEdgeTau, 1.0f - depth * (1.0f - shapeAt(phase_ + (ch ? stereo : 0.0), hz)));
        for (std::int64_t n = n0; n < start; ++n) {
            phase_ = phaseAt(n, sync, hz);
            for (int ch = 0; ch < 2; ++ch) {
                gain_[ch].setTarget(1.0f - depth * (1.0f - shapeAt(phase_ + (ch ? stereo : 0.0), hz)));
                gain_[ch].next();
            }
        }
        phase_ = sync ? gridPhase(songBeat(), get(kTBeats)) : phaseAt(start - 1, false, hz);
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) {
            hz_.setTarget(get(kTRate));
            depth_.setTarget(get(kTDepth));
        }
        float* io[2] = {left, right};
        const bool sync = on(kTSync);
        const double beats = get(kTBeats), stereo = get(kTStereo) / 360.0;
        const float hzSync = syncHz();
        for (int n = 0; n < frames; ++n) {
            // Synced: phase straight from the song grid, so the pattern follows 'beats' changes at once
            // (the gain smoother keeps the jump click-free) and previews match full renders.
            const float freeHz = hz_.next();
            phase_ = sync ? gridPhase(songBeat(), beats) : wrap01(phase_ + freeHz / sr_);
            ++pos_;
            const float hz = sync ? hzSync : freeHz;
            const float depth = depth_.next();
            for (int ch = 0; ch < 2; ++ch) {
                gain_[ch].setTarget(1.0f - depth * (1.0f - shapeAt(phase_ + (ch ? stereo : 0.0), hz)));
                io[ch][n] *= gain_[ch].next();
            }
        }
    }

private:
    // Gain smoother after the LFO: turns phase / stereo / shape jumps into ~2 ms glides; transparent for
    // the LFO itself (a 20 Hz sine is delayed by ~1 ms).
    static constexpr double kEdgeTau = 0.0006;

    float syncHz() const { return static_cast<float>(1.0 / beatsToSeconds(get(kTBeats), songBpm())); }
    // LFO phase at song sample n (free-running: integrated at a constant rate from the song start,
    // i.e. (n + 1) steps, as process() advances before use).
    double phaseAt(std::int64_t n, bool sync, float hz) const {
        if (sync) return gridPhase(songBeatAt(n), get(kTBeats));
        return wrap01(static_cast<double>(n + 1) * hz / sr_);
    }

    // LFO level 0..1 at phase ph (cycles).
    float shapeAt(double ph, float hz) const {
        switch (shape_) {
            case 1: return std::fabs(1.0f - 2.0f * static_cast<float>(wrap01(ph)));
            case 2: {
                // clipped, scaled sine = trapezoid with ~4 ms edges at any rate, shifted by half an edge
                // so it is fully open on the beat and closed by mid-period
                const float k = std::max(0.5f, 1.0f / (static_cast<float>(dsp::kTwoPi) * hz * 0.004f));
                return std::clamp(0.5f + k * sinCycles(ph + 0.002 * hz), 0.0f, 1.0f);
            }
            default: return 0.5f * (1.0f + cosCycles(ph));
        }
    }

    Smoother hz_;
    Smooth2 depth_, gain_[2];
    double phase_{0.0};
    int shape_{0};
};

}  // namespace

std::unique_ptr<Effect> makeChorus() { return std::make_unique<Chorus>(); }
std::unique_ptr<Effect> makeFlanger() { return std::make_unique<Flanger>(); }
std::unique_ptr<Effect> makePhaser() { return std::make_unique<Phaser>(); }
std::unique_ptr<Effect> makeTremolo() { return std::make_unique<Tremolo>(); }

}  // namespace as::timefx
