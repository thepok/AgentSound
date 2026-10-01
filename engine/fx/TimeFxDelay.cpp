// Stereo / ping-pong / mono delay with tape character (tempo sync, saturating feedback loop,
// echo-path filters, wow & flutter, input ducking).
//
// Ping-pong: the (mono-summed) input runs through its own line for the first repeat, which then
// feeds the two side lines that bounce the echoes. Classic ping-pong puts the first repeat hard on
// the 'start' side, so that side gets repeats 1, 3, 5... and the other 2, 4, 6...: the return leans
// towards 'start' by 10*log10(1/fb^2) dB (9 dB at feedback 0.35). Balanced (the default) puts the first
// repeat near the centre and bounces start side, other side, ... from the second repeat on; the first
// repeat is panned slightly towards the far side (energy share (1/2 + fb^2) / (1 + fb^2)) so the total
// echo energy is the same on both sides for any feedback. Echo times are the same either way.

#include "fx/TimeFxUtil.h"

namespace as::timefx {
namespace {

enum DelayParam {
    kDMode, kDStart, kDBalanced, kDSync, kDTime, kDTimeMs, kDOffset, kDFeedback, kDHighCut, kDLowCut,
    kDWow, kDFlutter, kDDuck, kDWidth, kDMix
};
enum DelayMode { kStereo, kPingPong, kMono };

ParamSpec fixedToggle(std::string name, bool def, std::string help) {
    ParamSpec s = toggle(std::move(name), def, std::move(help));
    s.automatable = false;
    return s;
}

const std::vector<ParamSpec>& delaySpecs() {
    static const std::vector<ParamSpec> s = {
        choice("mode", {"stereo", "pingpong", "mono"}, 0,
               "stereo = independent L/R echo lines, pingpong = echoes bounce left/right (input summed to mono; see "
               "'start' and 'balanced'), mono = one centred echo line"),
        choice("start", {"left", "right"}, 0,
               "pingpong: side of the first bounce (balanced: the second repeat; classic: the first repeat)"),
        fixedToggle("balanced", true,
                    "pingpong: on = first repeat near the centre, then start side, other side, ...; both sides get the "
                    "same echo energy. off = classic: first repeat hard on the 'start' side, the return leans that way"),
        toggle("sync", true, "on: 'time' is in beats (tempo-synced); off: 'timems' is used"),
        num("time", 0.03125f, 4, 0.75f, "beats",
            "Delay time in beats when sync is on: 0.25 = 1/16, 0.5 = 1/8, 0.75 = dotted 1/8, 1 = 1/4, 0.3333 = 1/8 triplet"),
        num("timems", 1, 4000, 375, "ms", "Delay time in milliseconds when sync is off"),
        num("offset", -50, 100, 0, "%",
            "Right time relative to left: right = left * (1 + offset/100); e.g. time 0.5 + offset 50 = 1/8 left, dotted 1/8 right"),
        num("feedback", 0, 1.1f, 0.35f, "",
            "Echo repeats: 0 = single echo, 0.3-0.6 typical, >= 1 self-oscillates (soft-saturated, stays bounded)"),
        num("highcut", 500, 20000, 8000, "Hz", "Low-pass in the echo path: each repeat gets darker (20000 = off)"),
        num("lowcut", 20, 2000, 100, "Hz", "High-pass in the echo path: each repeat gets thinner (20 = off)"),
        num("wow", 0, 1, 0, "", "Tape wow: slow pitch drift of the echoes (~0.6 Hz, 1 = +-0.5 % pitch)"),
        num("flutter", 0, 1, 0, "", "Tape flutter: fast pitch shimmer of the echoes (~7 Hz)"),
        num("duck", 0, 1, 0, "",
            "Duck the echoes while the input (or the sidechain) is loud, up to -30 dB at 1; echoes bloom in the gaps"),
        num("width", 0, 1.5f, 1, "", "Stereo width of the echoes (0 = mono, 1 = as designed, 1.5 = wider)"),
        num("mix", 0, 1, 0.3f, "", "Dry/wet balance (equal power); 1.0 = wet only, for send buses"),
    };
    return s;
}

class Delay final : public ParamEffect {
public:
    Delay() : ParamEffect(delaySpecs(), "delay") {}

    void prepare(const RenderContext& ctx) override {
        prepareClock(ctx);
        mode_ = std::clamp(getInt(kDMode), 0, 2);
        start_ = std::clamp(getInt(kDStart), 0, 1);
        balanced_ = on(kDBalanced);
        // (a tempo map: long enough for the slowest tempo, e.g. inside a fermata, but at most a minute of tape)
        maxSec_ = std::min(std::max(beatsToSeconds(4.0, slowestBpm()), 4.0) * 2.0, 60.0);
        const int lineLen = static_cast<int>(std::ceil((maxSec_ + 0.01) * sr_)) + 8;
        line_[0].init(lineLen);
        line_[1].init(mode_ == kMono ? 1 : lineLen);
        line_[2].init(mode_ == kPingPong ? lineLen : 1);  // ping-pong: the first repeat's own line

        // Automation smoothing: delay times glide like tape (~200 ms, a musical pitch sweep) when they
        // change by up to kJumpSeconds; bigger jumps crossfade to a second read head at the new time
        // (a glide across seconds of tape would be a wild pitch sweep). Wow/flutter depths ~70 ms (they
        // modulate the delay time); everything else is fast (~5-7 ms, 10-90 %) and click-free (Smooth2).
        double tl, tr;
        times(tl, tr);
        for (auto& h : head_) {
            h[0].prepare(sr_, 0.06, tl);
            h[1].prepare(sr_, 0.06, tr);
        }
        tempoT_[0] = tl;
        tempoT_[1] = tr;
        tempoInc_[0] = tempoInc_[1] = 0.0;
        tempoExact_ = false;
        active_ = 0;
        xf_ = 1.0f;
        xfStep_ = static_cast<float>(1.0 / (kXfadeSeconds * sr_));
        pendingJump_ = false;
        fb_.prepare(sr_, 0.002, get(kDFeedback));
        wow_.prepare(sr_, 0.02, get(kDWow));
        flutter_.prepare(sr_, 0.02, get(kDFlutter));
        duck_.prepare(sr_, 0.0015, get(kDDuck));
        width_.prepare(sr_, 0.0015, get(kDWidth));
        float dry, wet;
        equalPowerMix(get(kDMix), dry, wet);
        dry_.prepare(sr_, 0.0015, dry);
        wet_.prepare(sr_, 0.0015, wet);

        ctrlK_ = ctrlCoeff(sr_, kCtrl, 0.002);
        hc_.snap(get(kDHighCut));
        lc_.snap(get(kDLowCut));
        hcW_.prepare(sr_, 0.0015, hcActive());
        lcW_.prepare(sr_, 0.0015, lcActive());
        setHighCut(hc_.v, 0);
        setLowCut(lc_.v, 0);
        for (auto& f : hcF_) f.reset();
        for (auto& f : lcF_) f.reset();

        envAtt_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.001 * sr_)));
        envRel_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.04 * sr_)));
        duckAtt_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.01 * sr_)));
        duckRel_ = static_cast<float>(1.0 - std::exp(-1.0 / (0.15 * sr_)));
        env_ = duckDb_ = 0.0f;
        const std::uint64_t seed = ctx.seed ^ dsp::hashString("timefx.delay");
        wowNoise_.reset(seed);
        dsp::Rng rng(seed + 1);
        // tape wow/flutter run from the song start: a preview render continues where a full render is
        const double t0 = startSeconds();
        wowPh_ = wrap01(rng.uniform() + kWowHz * t0);
        flPh_ = wrap01(rng.uniform() + kFlutterHz * t0);
        flPh2_ = wrap01(rng.uniform() + kFlutter2Hz * t0);
        wowNoise_.skip(kDriftHz * t0);
        changed();
    }

    void process(float* left, float* right, int frames, const float* scL, const float* scR) override {
        if (changed()) pullTargets();
        // Tape speed modulation amplitudes (samples) for 100 % wow / flutter:
        // pitch deviation = 2*pi*f*A, i.e. 0.5 % at 0.63 Hz and 0.15 % at 7.1 Hz.
        const double wowAmp = 0.005 / (dsp::kTwoPi * kWowHz) * sr_;
        const double flAmp = 0.0015 / (dsp::kTwoPi * kFlutterHz) * sr_;
        const double wowInc = kWowHz / sr_, flInc = kFlutterHz / sr_, flInc2 = kFlutter2Hz / sr_, noiseInc = kDriftHz / sr_;

        const bool follow = followTempo();
        forEachCtrlBlock(pos_, frames, [&](int start, int len, bool tick) {
            if (tick) {
                if (hc_.step(ctrlK_)) setHighCut(hc_.v, kCtrl);
                if (lc_.step(ctrlK_)) setLowCut(lc_.v, kCtrl);
                if (follow) {  // synced times follow the tempo map: exact on every 32-sample grid point, linear between
                    double tl, tr, ml, mr;
                    times(tl, tr, static_cast<std::int64_t>(pos_) + kCtrl);
                    times(ml, mr, static_cast<std::int64_t>(pos_) + kCtrl / 2);
                    tempoInc_[0] = (tl - tempoT_[0]) / kCtrl;
                    tempoInc_[1] = (tr - tempoT_[1]) / kCtrl;
                    // a tempo step inside the block (now or `time` beats ago): follow it sample by sample
                    tempoExact_ = std::fabs(ml - tempoT_[0] - tempoInc_[0] * (kCtrl / 2)) > 1e-3 ||
                                  std::fabs(mr - tempoT_[1] - tempoInc_[1] * (kCtrl / 2)) > 1e-3;
                }
            }
            for (int n = start; n < start + len; ++n) {
                wowPh_ = wrap01(wowPh_ + wowInc);
                flPh_ = wrap01(flPh_ + flInc);
                flPh2_ = wrap01(flPh2_ + flInc2);
                const float drift = wowNoise_.next(noiseInc);
                const float wow = wow_.next(), flutter = flutter_.next();
                const double mod = wow * wowAmp * (0.65f * sinCycles(wowPh_) + 0.35f * drift) +
                                   flutter * flAmp * (0.7f * sinCycles(flPh_) + 0.3f * sinCycles(flPh2_));
                const bool pp = mode_ == kPingPong, stereo = mode_ != kMono;
                auto& in = head_[active_];
                const double dl = in[0].next() + mod, dr = in[1].next() + mod;
                float eL = line_[0].tapCubic(dl);
                float eR = stereo ? line_[1].tapCubic(dr) : 0.0f;
                float e1 = pp ? line_[2].tapCubic(start_ ? dr : dl) : 0.0f;  // ping-pong: first repeat
                if (xf_ < 1.0f) {  // equal-power crossfade from the previous head, C1 at both ends
                    xf_ = std::min(1.0f, xf_ + xfStep_);
                    const double w = 0.25 * (0.5 - 0.5 * cosCycles(0.5 * xf_));  // raised cosine, in quarter cycles
                    const float gIn = sinCycles(w), gOut = cosCycles(w);
                    auto& out = head_[active_ ^ 1];
                    const double ol = out[0].next() + mod, orr = out[1].next() + mod;
                    eL = gIn * eL + gOut * line_[0].tapCubic(ol);
                    if (stereo) eR = gIn * eR + gOut * line_[1].tapCubic(orr);
                    if (pp) e1 = gIn * e1 + gOut * line_[2].tapCubic(start_ ? orr : ol);
                    if (xf_ >= 1.0f && pendingJump_) {
                        pendingJump_ = false;
                        retime(static_cast<std::int64_t>(pos_) + (n - start));
                    }
                }
                const float hw = hcW_.next(), lw = lcW_.next();
                eL = echoFilter(eL, 0, hw, lw);
                if (stereo) eR = echoFilter(eR, 1, hw, lw);
                if (pp) e1 = echoFilter(e1, 2, hw, lw);

                const float fb = fb_.next();
                const float xl = left[n], xr = right[n];
                switch (mode_) {
                    case kPingPong: {
                        // side lines: s = start side, o = the other; the first repeat (e1) feeds the side that
                        // takes the next bounce
                        float e[2] = {eL, eR};
                        const int s = start_, o = start_ ^ 1;
                        const float ws = balanced_ ? fb * (e1 + e[o]) : fb * e[o];
                        const float wo = balanced_ ? fb * e[s] : fb * (e1 + e[s]);
                        line_[s].write(dsp::flush(softSat(ws)));
                        line_[o].write(dsp::flush(softSat(wo)));
                        line_[2].write(dsp::flush(0.5f * (xl + xr)));
                        if (balanced_) {
                            const float f2 = std::min(fb * fb, 1.0f);
                            e[s] += std::sqrt(0.5f / (1.0f + f2)) * e1;
                            e[o] += std::sqrt((0.5f + f2) / (1.0f + f2)) * e1;
                        } else {
                            e[s] += e1;
                        }
                        eL = e[0];
                        eR = e[1];
                        break;
                    }
                    case kMono:
                        line_[0].write(dsp::flush(0.5f * (xl + xr) + softSat(fb * eL)));
                        eR = eL;
                        break;
                    default:
                        line_[0].write(dsp::flush(xl + softSat(fb * eL)));
                        line_[1].write(dsp::flush(xr + softSat(fb * eR)));
                        break;
                }

                // ducking: fast peak envelope of the key -> reduction target (-40..-10 dBFS maps to
                // 0..30 dB x duck) -> smoothed in dB (10 ms down, 150 ms back up)
                const float key = scL ? std::max(std::fabs(scL[n]), scR ? std::fabs(scR[n]) : 0.0f)
                                      : std::max(std::fabs(xl), std::fabs(xr));
                env_ = dsp::flush(env_ + (key - env_) * (key > env_ ? envAtt_ : envRel_));
                const float duck = duck_.next();
                float g = 1.0f;
                if (duck > 1e-4f || duckDb_ < -1e-3f) {
                    const float lvl = std::clamp((dsp::gainToDb(env_) + 40.0f) / 30.0f, 0.0f, 1.0f);
                    const float target = -30.0f * duck * lvl;
                    duckDb_ = dsp::flush(duckDb_ + (target - duckDb_) * (target < duckDb_ ? duckAtt_ : duckRel_));
                    g = dsp::dbToGain(duckDb_);
                }
                const float m = 0.5f * (eL + eR) * g, s = 0.5f * (eL - eR) * g * width_.next();
                const float dg = dry_.next(), wg = wet_.next();
                left[n] = dg * xl + wg * (m + s);
                right[n] = dg * xr + wg * (m - s);
                if (follow) {  // the tempo part of the delay time moves at once (both heads); param changes still glide
                    double il = tempoInc_[0], ir = tempoInc_[1];
                    const auto at = static_cast<std::int64_t>(pos_) + (n - start);
                    if (tempoExact_) {
                        double nl, nr;
                        times(nl, nr, at + 1);
                        il = nl - tempoT_[0];
                        ir = nr - tempoT_[1];
                        if (tempoJumpBetween(at, at + 1)) {  // a tempo jump: the new time at once, crossfaded
                            tempoT_[0] = nl;
                            tempoT_[1] = nr;
                            tempoJump(il, ir);
                            continue;
                        }
                    }
                    tempoT_[0] += il;
                    tempoT_[1] += ir;
                    for (auto& h : head_) {
                        h[0].shift(il);
                        h[1].shift(ir);
                    }
                }
            }
        });
    }

    double tailSeconds() const override {
        double tl, tr;
        times(tl, tr);
        const double t = std::max(tl, tr) / sr_;
        const double fb = get(kDFeedback);
        if (fb < 0.001) return t + 0.01;
        if (fb >= 0.999) return 30.0;
        return std::min(30.0, t * (1.0 + 3.0 / -std::log10(fb)) + 0.01);
    }

private:
    // Tempo-synced delay in a song whose tempo changes: an echo `time` beats after a note lands `time` beats
    // later on the moving grid, i.e. the delay is the duration of the last `time` beats (every repeat too).
    bool followTempo() const noexcept { return tempo_ && on(kDSync); }
    void times(double& tl, double& tr) const { times(tl, tr, static_cast<std::int64_t>(pos_)); }
    void times(double& tl, double& tr, std::int64_t at) const {
        const double maxS = maxSec_ * sr_;
        if (followTempo()) {
            const double beats = get(kDTime);
            tl = std::clamp(lookbackSamples(beats, at), 2.0, maxS);
            tr = std::clamp(lookbackSamples(beats * (1.0 + get(kDOffset) * 0.01), at), 2.0, maxS);
            return;
        }
        const double sec = on(kDSync) ? beatsToSeconds(get(kDTime), bpm_) : get(kDTimeMs) * 1e-3;
        tl = std::clamp(sec * sr_, 2.0, maxS);
        tr = std::clamp(sec * (1.0 + get(kDOffset) * 0.01) * sr_, 2.0, maxS);
    }
    float hcActive() const { return get(kDHighCut) < 19999.0f ? 1.0f : 0.0f; }
    float lcActive() const { return get(kDLowCut) > 20.01f ? 1.0f : 0.0f; }
    void setHighCut(float hz, int samples) { for (auto& f : hcF_) f.setCutoff(sr_, hz, samples); }
    void setLowCut(float hz, int samples) { for (auto& f : lcF_) f.setCutoff(sr_, hz, samples); }

    // New delay times: the active head glides there (tape), or, for a jump, the other head is placed at
    // the new time and faded in. A jump during a crossfade waits for it to finish. The step is measured
    // against the head's previous target, not its (lagging) position: a fast automation ramp (a dub
    // delay-throw pitch sweep) arrives as many small steps and must stay one continuous tape glide.
    void retime() { retime(static_cast<std::int64_t>(pos_)); }
    void retime(std::int64_t at) {  // (at: the song sample being processed)
        double tl, tr;
        times(tl, tr, at);
        tempoT_[0] = tl;  // (tempo following continues from the new times)
        tempoT_[1] = tr;
        auto& in = head_[active_];
        const double jump = std::max(std::fabs(tl - in[0].target()), std::fabs(tr - in[1].target()));
        if (jump <= kJumpSeconds * sr_) {
            in[0].setTarget(tl);
            in[1].setTarget(tr);
            pendingJump_ = false;
        } else if (xf_ < 1.0f) {
            pendingJump_ = true;
        } else {
            active_ ^= 1;
            head_[active_][0].snap(tl);
            head_[active_][1].snap(tr);
            xf_ = 0.0f;
        }
    }

    // A tempo jump moved the synced times by (dl, dr) at once: a second read head starts there (keeping any
    // param glide in progress) and fades in, like a big time change. During a crossfade the jump waits for it
    // to finish (retime then places the head at the synced time of that moment).
    void tempoJump(double dl, double dr) {
        if (xf_ < 1.0f) {
            pendingJump_ = true;
            return;
        }
        const int from = active_;
        active_ ^= 1;
        for (int c = 0; c < 2; ++c) head_[active_][c] = head_[from][c];
        head_[active_][0].shift(dl);
        head_[active_][1].shift(dr);
        xf_ = 0.0f;
    }

    // Filters always run (warm state); the extreme settings crossfade them out so 'off' is exact.
    float echoFilter(float e, int ch, float hw, float lw) noexcept {
        const float a = e + hw * (hcF_[ch].process(e) - e);
        return a + lw * (lcF_[ch].process(a) - a);
    }

    void pullTargets() {
        retime();
        fb_.setTarget(get(kDFeedback));
        wow_.setTarget(get(kDWow));
        flutter_.setTarget(get(kDFlutter));
        duck_.setTarget(get(kDDuck));
        width_.setTarget(get(kDWidth));
        float dry, wet;
        equalPowerMix(get(kDMix), dry, wet);
        dry_.setTarget(dry);
        wet_.setTarget(wet);
        hc_.t = get(kDHighCut);
        lc_.t = get(kDLowCut);
        hcW_.setTarget(hcActive());
        lcW_.setTarget(lcActive());
    }

    static constexpr double kWowHz = 0.63, kFlutterHz = 7.1, kFlutter2Hz = 11.3, kDriftHz = 1.7;
    // Time changes up to this glide (the tape pitch bend stays within about +-5 semitones); larger
    // ones crossfade over kXfadeSeconds.
    static constexpr double kJumpSeconds = 0.05, kXfadeSeconds = 0.03;

    RingDelay line_[3];  // left, right, ping-pong first repeat
    Glide head_[2][2];  // [read head][channel]; head_[active_] is the audible one
    double tempoT_[2]{}, tempoInc_[2]{};  // tempo map: synced times at the current sample, per-sample drift
    bool tempoExact_{false};              // tempo map: this 32-sample block holds a tempo step (per-sample times)
    int active_{0};
    float xf_{1.0f}, xfStep_{0.001f};  // crossfade progress towards head_[active_] (1 = done)
    bool pendingJump_{false};
    TptFilter hcF_[3]{TptFilter::Mode::Low, TptFilter::Mode::Low, TptFilter::Mode::Low};
    TptFilter lcF_[3]{TptFilter::Mode::High, TptFilter::Mode::High, TptFilter::Mode::High};
    Smooth2 fb_, wow_, flutter_, duck_, width_, dry_, wet_, hcW_, lcW_;
    CtrlSmooth hc_, lc_;
    SmoothNoise wowNoise_;
    float ctrlK_{0.0f}, env_{0.0f}, envAtt_{0.0f}, envRel_{0.0f}, duckDb_{0.0f}, duckAtt_{0.0f}, duckRel_{0.0f};
    double maxSec_{8.0}, wowPh_{0.0}, flPh_{0.0}, flPh2_{0.0};
    int mode_{0}, start_{0};
    bool balanced_{true};
};

}  // namespace

std::unique_ptr<Effect> makeDelay() { return std::make_unique<Delay>(); }

}  // namespace as::timefx
