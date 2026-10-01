// Algorithmic reverb (plate | hall | room | chamber | cathedral) and the 80s gated reverb.
//
// Signal flow:
//   predelay -> early reflections (sparse stereo tapped delay, smeared by two short all-passes)
//            -> 16-channel diffuser: 4 steps of {per-channel delay spread, shuffle + polarity flip,
//               Hadamard mix} (Signalsmith "Let's write a reverb" style: dense, colourless onset)
//            -> 16-line feedback delay network: cubic-interpolated delays modulated by slow sines at
//               16 different rates (breaks up modal ringing), one Schroeder all-pass per line
//               (echo density growth), two-band decay filter (low shelf + HF damping one-pole,
//               as in zita-rev1), Hadamard feedback matrix; all delay lengths are distinct primes.
//   wet = orthogonal L/R output taps of the FDN (line outputs + one tap inside each line, which
//         fills the build-up) + a diffuser tap (onset) + early reflections
//         -> low-cut / high-cut -> width (M/S) -> equal-power dry/wet.
//
// The feed-forward parts (predelay, reflections, diffuser) run on whole host blocks; the FDN runs
// in sub-blocks on an absolute 32-sample grid, so output never depends on the host block size.
// The layout comes from a fixed structural seed (independent of the song seed), so the tested
// quality (density, decorrelation, RT60 accuracy) holds for every render.

#include "fx/ReverbCore.h"

namespace as::timefx {
namespace {

constexpr int kChunk = kReverbChunk;  // feed-forward chunk (host blocks are split to this size)

// ---------------------------------------------------------------------------------------------
// reverb
// ---------------------------------------------------------------------------------------------

enum ReverbParam {
    kRType, kRMix, kRSize, kRDecay, kRLowMult, kRLowXover, kRDamping, kRDiffusion, kREarly,
    kRPredelay, kRPredelayBeats, kRModRate, kRModDepth, kRLowCut, kRHighCut, kRWidth
};

struct TypePreset {
    float size, decay, lowmult, lowxover, damping, diffusion, early, predelay, modrate, moddepth, lowcut, highcut, width;
};
constexpr TypePreset kPresets[5] = {
    // size  decay lowm  xover damping diff  early pre  mrate mdepth lowcut highcut width
    {0.50f, 2.2f, 0.85f, 500, 9000, 1.00f, 0.00f, 10, 0.80f, 0.35f, 150, 16000, 1.0f},  // plate
    {0.75f, 2.8f, 1.20f, 400, 5500, 0.80f, 0.35f, 25, 0.60f, 0.45f, 120, 12000, 1.0f},  // hall
    {0.30f, 0.8f, 1.10f, 400, 6500, 0.60f, 0.60f, 5, 0.90f, 0.25f, 100, 12000, 0.9f},   // room
    {0.45f, 1.4f, 1.10f, 400, 5000, 0.80f, 0.45f, 12, 0.70f, 0.30f, 120, 11000, 1.0f},  // chamber
    {1.00f, 6.0f, 1.30f, 350, 3500, 0.85f, 0.30f, 40, 0.40f, 0.50f, 80, 9000, 1.0f},    // cathedral
};

std::vector<ParamSpec> buildReverbSpecs(int type) {
    const TypePreset& p = kPresets[type];
    return {
        choice("type", {"plate", "hall", "room", "chamber", "cathedral"}, type,
               "Algorithm preset; sets the defaults of every other param (explicit params override): "
               "plate = bright dense 80s plate (snares, vocals, leads), hall = big lush hall (pads, strings), "
               "room = small tight room, chamber = warm mid-size, cathedral = huge dark space"),
        num("mix", 0, 1, 0.3f, "", "Dry/wet balance (equal power); 1.0 = wet only for send/return buses, 0.15-0.35 as an insert"),
        num("size", 0, 1, p.size, "",
            "Space size: scales network delays, diffusion span and early reflections (0 = tiny, 1 = cathedral); not automatable", false),
        num("decay", 0.1f, 30, p.decay, "s", "RT60 at mid frequencies: time for the tail to fall by 60 dB"),
        num("lowmult", 0.25f, 4, p.lowmult, "x", "Bass decay multiplier: RT60 below 'lowxover' = decay * lowmult (<1 tight, >1 warm/boomy)"),
        num("lowxover", 50, 1500, p.lowxover, "Hz", "Crossover between the low and mid decay bands"),
        num("damping", 500, 20000, p.damping, "Hz",
            "HF damping: frequency where the RT60 is half of 'decay' (lower = darker tail; 20000 = undamped)"),
        num("diffusion", 0, 1, p.diffusion, "",
            "Onset density: 1 = instantly dense (plate), lower = more distinct early echoes; not automatable", false),
        num("early", 0, 1, p.early, "", "Early-reflection level (room character; 0 for plate)"),
        num("predelay", 0, 500, p.predelay, "ms", "Gap before the reverb; 10-40 ms keeps snares and vocals clear of the wash"),
        num("predelaybeats", 0, 2, 0, "beats", "Tempo-synced predelay; overrides 'predelay' when > 0 (e.g. 0.125 = 1/32 note)"),
        num("modrate", 0.05f, 5, p.modrate, "Hz", "Rate of the delay-line modulation that smears resonances"),
        num("moddepth", 0, 1, p.moddepth, "",
            "Delay-line modulation depth: 0 = static (may ring on pure tones), 0.3-0.6 lush, 1 = audible chorusing"),
        num("lowcut", 20, 2000, p.lowcut, "Hz", "High-pass on the wet signal (150-300 Hz keeps the bass clean)"),
        num("highcut", 1000, 20000, p.highcut, "Hz", "Low-pass on the wet signal"),
        num("width", 0, 1.5f, p.width, "", "Stereo width of the wet signal (0 = mono, 1 = natural, 1.5 = extra wide)"),
    };
}

const std::vector<ParamSpec>& reverbSpecs() {
    static const std::vector<ParamSpec> s = buildReverbSpecs(1);
    return s;
}

class Reverb final : public ParamEffect {
public:
    Reverb() : ParamEffect(reverbSpecs(), "reverb") {}

    // The type preset provides the defaults; explicit params override them.
    void configure(const json& j) override {
        Params probe(reverbSpecs());
        probe.configure(j, type_);  // validates everything and yields the type
        params_ = Params(buildReverbSpecs(std::clamp(probe.choice("type"), 0, 4)));
        params_.configure(j, type_);
        seen_ = ~0u;
    }
    const std::vector<ParamSpec>& paramSpecs() const override { return reverbSpecs(); }

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        const float size = get(kRSize);
        core_.prepare(sr_, size, get(kRDiffusion));
        early_.prepare(sr_, size);
        maxPre_ = std::max(0.5, std::min(beatsToSeconds(2.0, slowestBpm()), 8.0)) * sr_;  // (8 s: a slow tempo-map spot)
        tempoPre_ = predelaySamples();
        pre_.prepare(sr_, maxPre_, tempoPre_);

        // Automation smoothing: the tail shape (decay, bass multiplier, crossover, damping) and the wet
        // filters glide in ~7 ms (10-90 %); the delay-line modulation depth over ~100 ms (it moves delay
        // times); levels in ~5 ms (Smooth2, click-free).
        ctrlK_ = ctrlCoeff(sr_, kCtrl, 0.003);
        modK_ = ctrlCoeff(sr_, kCtrl, 0.05);
        decay_.snap(get(kRDecay));
        lowMult_.snap(get(kRLowMult));
        xover_.snap(get(kRLowXover));
        damp_.snap(get(kRDamping));
        lowCut_.snap(get(kRLowCut));
        highCut_.snap(get(kRHighCut));
        modDepth_.snap(get(kRModDepth));
        modRate_ = get(kRModRate);
        applyDecay(false);
        core_.setModulation(modRate_, modDepth_.v);
        core_.alignModulation(startSample_);
        wet_.reset();
        wet_.setLowCut(sr_, lowCut_.v, 0);
        wet_.setHighCut(sr_, highCut_.v, 0);

        earlyLevel_.prepare(sr_, 0.0015, get(kREarly));
        width_.prepare(sr_, 0.0015, get(kRWidth));
        float dry, wet;
        equalPowerMix(get(kRMix), dry, wet);
        dry_.prepare(sr_, 0.0015, dry);
        wetG_.prepare(sr_, 0.0015, wet);
        changed();
    }

    void process(float* left, float* right, int frames, const float*, const float*) override {
        if (changed()) pullTargets();
        for (int c = 0; c < frames; c += kChunk) processChunk(left + c, right + c, std::min(kChunk, frames - c));
    }

    double tailSeconds() const override {
        return predelaySamples() / sr_ + 1.5 * get(kRDecay) * std::max(1.0f, get(kRLowMult)) + 0.1;
    }

private:
    void processChunk(float* L, float* R, int frames) noexcept {
        // A synced predelay follows the tempo map at once (exact at the chunk ends, linear between); the glide
        // keeps smoothing param changes only.
        double inc = 0.0;
        if (followTempo()) {
            const auto at = static_cast<std::int64_t>(pos_);
            const double target = predelaySamples(at + frames);
            if (tempoJumpBetween(at, at + frames)) {
                pre_.jump(target - tempoPre_);  // a tempo jump: the new predelay at once, crossfaded
            } else {
                inc = (target - tempoPre_) / frames;
            }
            tempoPre_ = target;
        }
        for (int k = 0; k < frames; ++k) {
            pre_.tick(L[k], R[k], pl_[k], pr_[k]);
            if (inc != 0.0) pre_.glide.shift(inc);
        }
        early_.taps(pl_, pr_, el_, er_, frames);
        core_.diffuse(pl_, pr_, frames);
        forEachCtrlBlock(pos_, frames, [&](int off, int n, bool tick) {
            if (tick) controlTick();
            float wl[kCtrl], wr[kCtrl];
            core_.late(off, wl, wr, n);
            for (int k = 0; k < n; ++k) {
                const int i = off + k;
                const float eg = earlyLevel_.next();
                const float a = wet_.process(0, wl[k] + eg * early_.lowPass(0, el_[i]));
                const float b = wet_.process(1, wr[k] + eg * early_.lowPass(1, er_[i]));
                const float m = 0.5f * (a + b), s = 0.5f * (a - b) * width_.next();
                const float dg = dry_.next(), wg = wetG_.next();
                L[i] = dg * L[i] + wg * (m + s);
                R[i] = dg * R[i] + wg * (m - s);
            }
        });
    }
    bool followTempo() const noexcept { return tempo_ && get(kRPredelayBeats) > 0.0f; }
    double predelaySamples() const { return predelaySamples(static_cast<std::int64_t>(pos_)); }
    double predelaySamples(std::int64_t at) const {
        const double beats = get(kRPredelayBeats);
        // (tempo map: the duration of the last `beats` beats, so the reverb starts `beats` after the note on the grid)
        if (tempo_ && beats > 0.0) return std::clamp(lookbackSamples(beats, at), 2.0, std::max(2.0, maxPre_));
        const double sec = beats > 0.0 ? beatsToSeconds(beats, bpm_) : get(kRPredelay) * 1e-3;
        return std::clamp(sec * sr_, 2.0, std::max(2.0, maxPre_));
    }
    void pullTargets() {
        decay_.t = get(kRDecay);
        lowMult_.t = get(kRLowMult);
        xover_.t = get(kRLowXover);
        damp_.t = get(kRDamping);
        lowCut_.t = get(kRLowCut);
        highCut_.t = get(kRHighCut);
        modDepth_.t = get(kRModDepth);
        modRate_ = get(kRModRate);
        tempoPre_ = predelaySamples();
        pre_.glide.setTarget(tempoPre_);
        earlyLevel_.setTarget(get(kREarly));
        width_.setTarget(get(kRWidth));
        float dry, wet;
        equalPowerMix(get(kRMix), dry, wet);
        dry_.setTarget(dry);
        wetG_.setTarget(wet);
    }
    void controlTick() {
        bool d = decay_.step(ctrlK_);
        d |= lowMult_.step(ctrlK_);
        d |= xover_.step(ctrlK_);
        d |= damp_.step(ctrlK_);
        if (d) applyDecay(true);
        if (lowCut_.step(ctrlK_)) wet_.setLowCut(sr_, lowCut_.v, kCtrl);
        if (highCut_.step(ctrlK_)) wet_.setHighCut(sr_, highCut_.v, kCtrl);
        modDepth_.step(modK_);
        core_.setModulation(modRate_, modDepth_.v);
    }
    void applyDecay(bool ramp) {
        core_.setDecay(decay_.v, lowMult_.v, xover_.v, damp_.v, ramp);
        early_.setDamping(damp_.v);
    }

    ReverbCore core_;
    EarlyReflections early_;
    WetFilter wet_;
    Predelay pre_;
    CtrlSmooth decay_, lowMult_, xover_, damp_, lowCut_, highCut_, modDepth_;
    Smooth2 earlyLevel_, width_, dry_, wetG_;
    float ctrlK_{0.0f}, modK_{0.0f};
    double modRate_{0.6}, maxPre_{24000.0}, tempoPre_{0.0};  // tempoPre_: synced predelay at the chunk start
    float pl_[kChunk]{}, pr_[kChunk]{}, el_[kChunk]{}, er_[kChunk]{};
};

// ---------------------------------------------------------------------------------------------
// gatedreverb
// ---------------------------------------------------------------------------------------------

enum GatedParam { kGMix, kGThreshold, kGHold, kGRelease, kGPredelay, kGSize, kGDecay, kGTone, kGLowCut, kGWidth, kGFlat };

const std::vector<ParamSpec>& gatedSpecs() {
    static const std::vector<ParamSpec> s = {
        num("mix", 0, 1, 0.5f, "", "Dry/wet balance (equal power); 1.0 = wet only for a send bus"),
        num("threshold", -70, 0, -30, "dB", "Input peak level that opens the gate; set a little below the snare hits"),
        num("hold", 10, 2000, 250, "ms",
            "Length of the burst: the gate stays open this long after each hit (longer only while the input stays above the threshold); 150-400 typical"),
        num("release", 1, 500, 30, "ms", "Gate closing time; 10-60 ms gives the classic abrupt cut"),
        num("predelay", 0, 100, 0, "ms", "Gap before the reverb burst (the gate timing follows it)"),
        num("size", 0, 1, 0.35f, "", "Space size of the reverb behind the gate; not automatable", false),
        num("decay", 0.2f, 10, 4.0f, "s", "RT60 of the reverb behind the gate; long = flat burst until the cut (classic), short = decaying burst"),
        num("tone", 0, 1, 0.65f, "", "Brightness of the burst (0 = dark, 1 = very bright)"),
        num("lowcut", 20, 1000, 180, "Hz", "High-pass on the burst"),
        num("width", 0, 1.5f, 1, "", "Stereo width of the burst"),
        num("flat", 0, 1, 1, "",
            "Decay compensation while the gate is open: 1 = flat burst that is then cut dead (classic 80s "
            "gated/non-linear reverb), 0 = the reverb's natural decay behind the gate"),
    };
    return s;
}

class GatedReverb final : public ParamEffect {
public:
    GatedReverb() : ParamEffect(gatedSpecs(), "gatedreverb") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        const float size = get(kGSize);
        core_.prepare(sr_, size, 1.0f);
        early_.prepare(sr_, size);
        maxPre_ = 0.1 * sr_;
        pre_.prepare(sr_, maxPre_, predelaySamples());
        key_.init(static_cast<int>(std::ceil(maxPre_)) + 8);
        ctrlK_ = ctrlCoeff(sr_, kCtrl, 0.003);  // tone / decay / lowcut: ~7 ms (10-90 %)
        decay_.snap(get(kGDecay));
        tone_.snap(get(kGTone));
        lowCut_.snap(get(kGLowCut));
        wet_.reset();
        applyTone(false);
        wet_.setLowCut(sr_, lowCut_.v, 0);
        core_.setModulation(0.7, 0.2);
        core_.alignModulation(startSample_);
        width_.prepare(sr_, 0.0015, get(kGWidth));
        float dry, wet;
        equalPowerMix(get(kGMix), dry, wet);
        dry_.prepare(sr_, 0.0015, dry);
        wetG_.prepare(sr_, 0.0015, wet);
        env_ = gate_ = 0.0f;
        holdLeft_ = 0;
        armed_ = true;
        envRel_ = static_cast<float>(std::exp(-1.0 / (0.005 * sr_)));
        attStep_ = static_cast<float>(1.0 / (0.0005 * sr_));
        compLog_ = 0.0f;
        comp_ = 1.0f;
        compK_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.003 * sr_)));
        pullGate();
        changed();
    }

    void process(float* left, float* right, int frames, const float* scL, const float* scR) override {
        if (changed()) pullTargets();
        for (int c = 0; c < frames; c += kChunk)
            processChunk(left + c, right + c, std::min(kChunk, frames - c), scL ? scL + c : nullptr, scR ? scR + c : nullptr);
    }

    double tailSeconds() const override {
        return (get(kGPredelay) + get(kGHold) + get(kGRelease)) * 1e-3 + 0.05;
    }

private:
    static constexpr float kBurstGain = 2.0f;  // the gated burst is a foreground effect
    static constexpr float kEarly = 0.15f;     // a little room crunch in the burst (more spikes the onset)
    static constexpr float kCompMaxLog = 1.3862944f;  // decay compensation capped at +12 dB

    void processChunk(float* L, float* R, int frames, const float* scL, const float* scR) noexcept {
        for (int k = 0; k < frames; ++k) {
            const double d = pre_.tick(L[k], R[k], pl_[k], pr_[k]);
            // gate key: sidechain if given, else the input; delayed like the reverb input
            const float key = std::fabs(key_.tapCubic(d));
            key_.write(scL ? std::max(std::fabs(scL[k]), scR ? std::fabs(scR[k]) : 0.0f)
                           : std::max(std::fabs(L[k]), std::fabs(R[k])));
            // A hit (threshold crossing, re-armed once the key falls 6 dB below the threshold)
            // opens the gate for 'hold'; it also stays open while the key is above the threshold.
            env_ = std::max(key, dsp::flush(env_ * envRel_));
            if (env_ > thr_) {
                if (armed_) {
                    holdLeft_ = holdSamples_;
                    compLog_ = 0.0f;  // new hit: restart the decay compensation (comp_ glides down)
                }
                armed_ = false;
            } else if (env_ < 0.5f * thr_) {
                armed_ = true;
            }
            const bool open = holdLeft_ > 0 || env_ > thr_;
            if (holdLeft_ > 0) --holdLeft_;
            if (open) {
                gate_ = std::min(1.0f, gate_ + attStep_);
                // Hold phase after the hit (key below threshold, nothing feeds the reverb): undo its
                // own exponential decay (60 dB per 'decay' seconds) so the burst stays flat.
                if (env_ <= thr_) compLog_ = std::min(compLog_ + compRate_, kCompMaxLog);
            } else {
                gate_ = gate_ > 1e-4f ? gate_ * relCoef_ : 0.0f;  // exponential close, then hard zero
                if (gate_ == 0.0f) compLog_ = 0.0f, comp_ = 1.0f;  // shut: next burst starts flat
            }
            comp_ += (std::exp(compLog_) - comp_) * compK_;
            gain_[k] = gate_ * comp_ * kBurstGain;
        }
        early_.taps(pl_, pr_, el_, er_, frames);
        core_.diffuse(pl_, pr_, frames);
        forEachCtrlBlock(pos_, frames, [&](int off, int n, bool tick) {
            if (tick) {
                bool t = tone_.step(ctrlK_);
                t |= decay_.step(ctrlK_);
                if (t) applyTone(true);
                if (lowCut_.step(ctrlK_)) wet_.setLowCut(sr_, lowCut_.v, kCtrl);
            }
            float wl[kCtrl], wr[kCtrl];
            core_.late(off, wl, wr, n);
            for (int k = 0; k < n; ++k) {
                const int i = off + k;
                const float a = wet_.process(0, wl[k] + kEarly * early_.lowPass(0, el_[i])) * gain_[i];
                const float b = wet_.process(1, wr[k] + kEarly * early_.lowPass(1, er_[i])) * gain_[i];
                const float m = 0.5f * (a + b), s = 0.5f * (a - b) * width_.next();
                const float dg = dry_.next(), wg = wetG_.next();
                L[i] = dg * L[i] + wg * (m + s);
                R[i] = dg * R[i] + wg * (m - s);
            }
        });
    }

    double predelaySamples() const { return std::clamp(get(kGPredelay) * 1e-3 * sr_, 2.0, maxPre_); }
    void pullGate() {
        thr_ = dsp::dbToGain(get(kGThreshold));
        holdSamples_ = std::max(1, static_cast<int>(std::lround(get(kGHold) * 1e-3 * sr_)));
        relCoef_ = static_cast<float>(std::pow(1e-4, 1.0 / std::max(1.0, get(kGRelease) * 1e-3 * sr_)));  // -80 dB
        compRate_ = static_cast<float>(get(kGFlat) * std::log(1000.0) / (get(kGDecay) * sr_));
    }
    void pullTargets() {
        pullGate();
        decay_.t = get(kGDecay);
        tone_.t = get(kGTone);
        lowCut_.t = get(kGLowCut);
        pre_.glide.setTarget(predelaySamples());
        width_.setTarget(get(kGWidth));
        float dry, wet;
        equalPowerMix(get(kGMix), dry, wet);
        dry_.setTarget(dry);
        wetG_.setTarget(wet);
    }
    void applyTone(bool ramp) {
        const double t = tone_.v;
        const double damp = 2000.0 * std::pow(9.0, t);  // 2 kHz .. 18 kHz
        core_.setDecay(decay_.v, 0.8, 400.0, damp, ramp);
        early_.setDamping(damp);
        wet_.setHighCut(sr_, 4000.0 * std::pow(5.0, t), ramp ? kCtrl : 0);  // 4 kHz .. 20 kHz
    }

    ReverbCore core_;
    EarlyReflections early_;
    WetFilter wet_;
    Predelay pre_;
    RingDelay key_;
    CtrlSmooth decay_, tone_, lowCut_;
    Smooth2 width_, dry_, wetG_;
    float ctrlK_{0.0f}, env_{0.0f}, envRel_{0.0f}, gate_{0.0f}, attStep_{0.0f}, relCoef_{0.0f}, thr_{0.03f};
    float compLog_{0.0f}, comp_{1.0f}, compK_{0.0f}, compRate_{0.0f};
    int holdLeft_{0}, holdSamples_{12000};
    bool armed_{true};
    double maxPre_{4800.0};
    float pl_[kChunk]{}, pr_[kChunk]{}, el_[kChunk]{}, er_[kChunk]{}, gain_[kChunk]{};
};

}  // namespace

std::unique_ptr<Effect> makeReverb() { return std::make_unique<Reverb>(); }
std::unique_ptr<Effect> makeGatedReverb() { return std::make_unique<GatedReverb>(); }

}  // namespace as::timefx
