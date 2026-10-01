#pragma once

// Building blocks of the algorithmic reverbs (TimeFxReverb.cpp: reverb, gatedreverb; PremiumShimmer.cpp:
// shimmer). Internal to engine/fx; the signal flow is described in TimeFxReverb.cpp. Header-only so
// several effects share the exact same (tested) late-reverb core.

#include "fx/TimeFxUtil.h"

#include <array>
#include <bit>
#include <complex>
#include <numeric>

namespace as::timefx {

inline constexpr int kReverbChunk = kMaxBlock;  // feed-forward chunk (host blocks are split to this size)

inline bool isPrime(int n) {
    if (n < 2) return false;
    if (n % 2 == 0) return n == 2;
    for (int d = 3; d * d <= n; d += 2)
        if (n % d == 0) return false;
    return true;
}

// Nearest prime >= lo to n not yet used (keeps all delay lengths mutually prime). The lower bound
// matters: the block-wise FDN needs every loop delay to exceed a sub-block.
inline int uniquePrimeNear(int n, int lo, std::vector<int>& used) {
    lo = std::max(lo, 3);
    n = std::max(n, lo);
    for (int k = 0;; ++k) {
        for (const int c : {n + k, n - k}) {
            if (c >= lo && isPrime(c) && std::find(used.begin(), used.end(), c) == used.end()) {
                used.push_back(c);
                return c;
            }
        }
    }
}

template <std::size_t N>
inline void shuffle(std::array<int, N>& a, dsp::Rng& rng) {
    std::iota(a.begin(), a.end(), 0);
    for (std::size_t i = N - 1; i > 0; --i) {
        const std::size_t j = static_cast<std::size_t>(rng.next() % (i + 1));
        std::swap(a[i], a[j]);
    }
}

// ---------------------------------------------------------------------------------------------
// Late reverb core. diffuse() handles a whole chunk (feed-forward); late() runs the FDN on
// sub-blocks of <= kBlock samples. Every loop delay (FDN line minus modulation, in-loop all-pass)
// is longer than a sub-block, so a line's outputs for a sub-block can be read before its inputs
// are written.
// ---------------------------------------------------------------------------------------------

class ReverbCore {
public:
    static constexpr int N = 16;
    static constexpr int kSteps = 4;
    static constexpr int kBlock = kCtrl;

    void prepare(double sr, float size, float diffusion) {
        sr_ = sr;
        dsp::Rng rng(0x7E5E4B5A11C0FFEEull);
        std::vector<int> used;
        const double msToS = sr / 1000.0;
        const double meanMs = 10.0 + 90.0 * size * size;
        modMax_ = std::min(1.2 * msToS, 0.2 * meanMs * 0.45 * msToS);
        const int minLine = static_cast<int>(modMax_) + kBlock + 8;

        // FDN lines: geometric spread 0.45..1.55 x mean (jittered), shuffled over the channels.
        std::array<int, N> order;
        shuffle(order, rng);
        for (int i = 0; i < N; ++i) {
            const double r = (order[static_cast<std::size_t>(i)] + 0.5 + 0.35 * rng.bipolar()) / N;
            const double ms = meanMs * 0.45 * std::pow(1.55 / 0.45, r);
            len_[i] = uniquePrimeNear(static_cast<int>(std::lround(ms * msToS)), minLine, used);
        }
        double sumLoop = 0.0;
        for (int i = 0; i < N; ++i) {
            const double ms = meanMs * (0.06 + 0.08 * rng.uniform());
            apLen_[i] = uniquePrimeNear(static_cast<int>(std::lround(ms * msToS)), kBlock + 1, used);
            ap_[i].init(apLen_[i] + 2);
            line_[i].init(len_[i] + static_cast<int>(modMax_) + 8);
            loop_[i] = len_[i] + apLen_[i];  // mean group delay of the all-pass = its length
            sumLoop += loop_[i];
            rateMul_[i] = 0.55 + 0.9 * rng.uniform();
            modPhase_[i] = rng.uniform();
        }
        meanLoop_ = sumLoop / N;
        apG_ = 0.3f + 0.35f * diffusion;

        // Diffuser: total spread D ~ 0.85 x mean line (the onset tap then bridges into the late
        // field); the 4 steps take 40/30/20/10 % of it, each channel has its own slot in a step.
        diffSamples_ = diffusion * (2.0 + 0.85 * meanMs) * msToS;
        static constexpr double kStepFrac[kSteps] = {0.4, 0.3, 0.2, 0.1};
        for (int s = 0; s < kSteps; ++s) {
            Step& st = steps_[s];
            std::array<int, N> slot, perm;
            shuffle(slot, rng);
            shuffle(perm, rng);
            for (int i = 0; i < N; ++i) {
                const double range = diffSamples_ * kStepFrac[s];
                st.len[i] = static_cast<int>((slot[static_cast<std::size_t>(i)] + rng.uniform()) / N * range);
                st.line[i].init(st.len[i] + kReverbChunk + 4);
                st.sign[i] = rng.uniform() < 0.5f ? -1.0f : 1.0f;
                st.perm[i] = perm[static_cast<std::size_t>(i)];
            }
        }

        // Output taps: random signs a, and a (.) (Hadamard row) -> orthogonal => decorrelated L/R.
        // Line outputs and inner taps each carry half the output energy.
        for (int i = 0; i < N; ++i) {
            const float s = 0.25f * 0.70710678f;
            const float a = rng.uniform() < 0.5f ? -s : s;
            const float b = rng.uniform() < 0.5f ? -s : s;
            const auto parity = [i](unsigned row) { return (std::popcount(static_cast<unsigned>(i) & row) & 1) ? -1.0f : 1.0f; };
            outL_[i] = a;
            outR_[i] = a * parity(11);
            innerL_[i] = b;
            innerR_[i] = b * parity(6);
            inner_[i] = std::max(kBlock + 1, static_cast<int>(len_[i] * (0.2 + 0.4 * rng.uniform())));
        }
        clear();
    }

    void clear() {
        for (auto& st : steps_)
            for (auto& l : st.line) l.clear();
        for (auto& l : line_) l.clear();
        for (auto& l : ap_) l.clear();
        for (int i = 0; i < N; ++i) lowZ_[i] = dampZ_[i] = modCur_[i] = modInc_[i] = 0.0f;
        modCountdown_ = 0;
    }

    // RT60 (s) at mid frequencies, low-band multiplier below xoverHz, and the frequency at which the
    // RT60 is half the mid value (HF damping; >= 19999 Hz = none). "Mid" is the 1 kHz reference, or
    // half the damping frequency for damping below 2 kHz: normalising the loop at a frequency the
    // damping filter already attenuates would lift everything below it to a loop gain of ~1 (a dark
    // tail whose lows ring for minutes). With `ramp`, the loop coefficients and
    // output gains move there linearly over the next kBlock samples (the next late() call): stepping
    // them at the control rate would put small steps into the recirculating signal and the output.
    void setDecay(double t60, double lowMult, double xoverHz, double dampHz, bool ramp) {
        Coefs& t = tgt_;
        const double lc = 1.0 - std::exp(-dsp::kTwoPi * xoverHz / sr_);
        t.lowC = static_cast<float>(lc);
        const bool damp = dampHz < 19999.0;
        const double cw = std::cos(dsp::kTwoPi * std::min(dampHz, 0.45 * sr_) / sr_);
        const double refHz = damp ? std::min(1000.0, 0.5 * dampHz) : 1000.0;
        const std::complex<double> zr = std::polar(1.0, -dsp::kTwoPi * refHz / sr_);  // z^-1 at the reference
        for (int i = 0; i < N; ++i) {
            const double L = loop_[i];
            const double gm = std::pow(10.0, -3.0 * L / (sr_ * t60));
            const double gl = std::pow(10.0, -3.0 * L / (sr_ * t60 * lowMult));
            const double lowK = gl / gm - 1.0;
            // One-pole low-pass (1-a)/(1-a z^-1) whose gain at dampHz equals gm, so the loop gain
            // there is gm^2 (RT60 halved): solve a^2 - 2ba + 1 = 0 for the stable root.
            double a = 0.0;
            if (damp) {
                const double r2 = gm * gm;
                const double b = (1.0 - r2 * cw) / (1.0 - r2);
                a = 1.0 / (b + std::sqrt(std::max(0.0, b * b - 1.0)));
            }
            // Normalise the loop gain at the reference to exactly gm (the shelf and damping filters both
            // leak a little into the mids), keeping every frequency's loop gain below 1.
            const std::complex<double> shelf = 1.0 + lowK * lc / (1.0 - (1.0 - lc) * zr);
            const std::complex<double> hd = (1.0 - a) / (1.0 - a * zr);
            const double corr = std::min(1.0 / std::abs(shelf * hd), 0.99999 / std::max(gl, gm));
            t.gMid[i] = static_cast<float>(gm * corr);
            t.lowK[i] = static_cast<float>(lowK);
            t.dampA[i] = static_cast<float>(a);
        }
        // Level: late energy for a unit centred impulse ~ 2*sr*T / (6 ln10 * N * meanLoop).
        // Normalise to 0.35*sqrt(T) so the wet level grows only gently with decay time.
        const double predicted = 2.0 * sr_ * t60 / (6.0 * std::log(10.0) * N * meanLoop_);
        t.outGain = static_cast<float>(std::sqrt(0.35 * std::sqrt(t60) / predicted));
        // Diffuser tap at ~0.6x the initial late-field level per sample, spread over the diffuser span.
        t.onsetGain = diffSamples_ > 8.0
                          ? static_cast<float>(t.outGain * std::sqrt(0.6 * std::min(1.0, diffSamples_ / meanLoop_)))
                          : 0.0f;
        if (!ramp) {
            cur_ = t;
            rampLeft_ = 0;
            return;
        }
        const float inv = 1.0f / kBlock;
        for (int i = 0; i < N; ++i) {
            inc_.gMid[i] = (t.gMid[i] - cur_.gMid[i]) * inv;
            inc_.lowK[i] = (t.lowK[i] - cur_.lowK[i]) * inv;
            inc_.dampA[i] = (t.dampA[i] - cur_.dampA[i]) * inv;
        }
        inc_.lowC = (t.lowC - cur_.lowC) * inv;
        inc_.outGain = (t.outGain - cur_.outGain) * inv;
        inc_.onsetGain = (t.onsetGain - cur_.onsetGain) * inv;
        rampLeft_ = kBlock;
    }

    // Longest RT60 (s) of the target loop coefficients of the last setDecay(t60, ...): t60 itself, or
    // longer at low frequencies (bass multiplier > 1; the damping filter's leak into the reference
    // frequency, which the loop-gain correction makes up, lifts everything below it a little). Used to
    // bound feedback around the core.
    double longestDecay(double t60) const noexcept {
        double t = t60;
        for (int i = 0; i < N; ++i) {
            const double g = static_cast<double>(tgt_.gMid[i]) * (1.0 + tgt_.lowK[i]);  // loop gain at DC
            if (g >= 1.0) return 1e9;
            if (g > 0.0) t = std::max(t, -3.0 * loop_[i] / (sr_ * std::log10(g)));
        }
        return t;
    }

    void setModulation(double rateHz, double depth01) {
        modRate_ = rateHz;
        modDepth_ = depth01 * modMax_;
    }

    // Render starting at song sample `songSample` (a preview): the delay-line modulation, which runs
    // from the song start at the prepared rate and depth, continues where a full render has it (also
    // mid control block), so a preview matches the same span of a full render. Call after
    // setModulation, before the first late().
    void alignModulation(std::uint64_t songSample) noexcept {
        const std::uint64_t k = songSample / kBlock;  // block being rendered; `r` samples of it are done
        const int r = static_cast<int>(songSample % kBlock);
        const double inc = modRate_ * kBlock / sr_;
        for (int i = 0; i < N; ++i) {
            const double ph0 = modPhase_[i];
            // phase after the update at the start of block j (updateMod advances before use)
            auto phaseAt = [&](std::uint64_t j) { return wrap01(ph0 + static_cast<double>(j + 1) * inc * rateMul_[i]); };
            const float from = k > 0 ? static_cast<float>(modDepth_) * sinCycles(phaseAt(k - 1)) : 0.0f;
            if (r == 0) {
                modPhase_[i] = k > 0 ? phaseAt(k - 1) : ph0;
                modCur_[i] = from;
                modInc_[i] = 0.0f;
            } else {
                modPhase_[i] = phaseAt(k);
                modInc_[i] = (static_cast<float>(modDepth_) * sinCycles(modPhase_[i]) - from) * (1.0f / kBlock);
                modCur_[i] = from + static_cast<float>(r) * modInc_[i];
            }
        }
        modCountdown_ = r == 0 ? 0 : kBlock - r;
    }

    // Stereo -> 16 channels -> diffuser, for a whole chunk (n <= kReverbChunk). Must precede late().
    void diffuse(const float* inL, const float* inR, int n) noexcept {
        for (int i = 0; i < N; ++i) {
            const float* src = (i & 1) ? inR : inL;
            for (int k = 0; k < n; ++k) x_[i][k] = src[k] * kInGain;
        }
        for (auto& st : steps_) {
            for (int i = 0; i < N; ++i) {
                st.line[i].write(x_[i], n);  // feed-forward: write the chunk, read it back delayed
                st.line[i].read<false>(st.len[i] + n, st.sign[i], t_[st.perm[i]], n);
            }
            for (int i = 0; i < N; ++i) std::copy(t_[i], t_[i] + n, x_[i]);
            hadamardBlock(x_, n);
        }
    }

    // FDN for samples [off, off+n) of the diffused chunk; n <= kBlock and calls must not cross the
    // absolute kBlock grid (see forEachCtrlBlock).
    void late(int off, float* outL, float* outR, int n) noexcept {
        if (modCountdown_ <= 0) updateMod();
        modCountdown_ -= n;

        // 1. modulated Catmull-Rom read per line. Sample k sits at index w + k - len - m; the
        //    integer/fraction split is done on (kModOffset - m) > 0 to stay in float precision.
        for (int i = 0; i < N; ++i) {
            const RingDelay& line = line_[i];
            const float* buf = line.data();
            const std::uint32_t mask = line.mask();
            const std::uint32_t base = line.writeIndex() - static_cast<std::uint32_t>(len_[i] + kModOffset);
            const float mi = modInc_[i];
            float m = modCur_[i];
            float* v = v_[i];
            for (int k = 0; k < n; ++k) {
                m += mi;
                const float q = static_cast<float>(kModOffset) - m;
                const int qi = static_cast<int>(q);
                const float t = q - static_cast<float>(qi);
                const std::uint32_t j = base + static_cast<std::uint32_t>(k + qi);
                const float ym1 = buf[(j - 1) & mask], y0 = buf[j & mask], y1 = buf[(j + 1) & mask],
                            y2 = buf[(j + 2) & mask];
                const float c1 = 0.5f * (y1 - ym1);
                const float c2 = ym1 - 2.5f * y0 + 2.0f * y1 - 0.5f * y2;
                const float c3 = 0.5f * (y2 - ym1) + 1.5f * (y0 - y1);
                v[k] = ((c3 * t + c2) * t + c1) * t + y0;
            }
            modCur_[i] = m;
            ap_[i].read<false>(apLen_[i], 1.0f, wd_[i], n);
        }

        // 2. in-loop all-pass and two-band decay; the 16 lines are independent recursions, so they
        //    are interleaved per sample (instruction-level parallelism across lines). Decay changes
        //    ramp the loop coefficients per sample (see setDecay).
        const bool ramping = rampLeft_ > 0;
        float outG[kBlock], onsetG[kBlock];
        for (int k = 0; k < n; ++k) {
            if (rampLeft_ > 0) stepRamp();
            outG[k] = cur_.outGain;
            onsetG[k] = cur_.onsetGain;
            const float lowC = cur_.lowC;
            for (int i = 0; i < N; ++i) {
                // Schroeder all-pass, single buffer: w = v + g*w[n-M], u = w[n-M] - g*w
                const float wd = wd_[i][k];
                const float w = dsp::flush(v_[i][k] + apG_ * wd);
                w_[i][k] = w;
                const float u = wd - apG_ * w;
                u_[i][k] = u;
                // low shelf (gain gl below xover, gm above), then the HF damping one-pole
                lowZ_[i] = dsp::flush(lowZ_[i] + lowC * (u - lowZ_[i]));
                const float s = cur_.gMid[i] * (u + cur_.lowK[i] * lowZ_[i]);
                dampZ_[i] = dsp::flush(s + cur_.dampA[i] * (dampZ_[i] - s));
                y_[i][k] = dampZ_[i];
            }
        }
        for (int i = 0; i < N; ++i) ap_[i].write(w_[i], n);

        // 3. outputs: orthogonal L/R taps of the line outputs, inner line taps and the diffuser
        //    (late part x outGain, onset part x onsetGain; per sample while a decay change ramps)
        std::fill(outL, outL + n, 0.0f);
        std::fill(outR, outR + n, 0.0f);
        if (!ramping) {
            const float og = cur_.outGain, ong = cur_.onsetGain;
            for (int i = 0; i < N; ++i) {
                line_[i].read<true>(inner_[i], innerL_[i] * og, outL, n);
                line_[i].read<true>(inner_[i], innerR_[i] * og, outR, n);
            }
            for (int i = 0; i < N; ++i) {
                const float a = outL_[i] * og, b = outR_[i] * og;
                const float c = outL_[i] * ong, d = outR_[i] * ong;
                const float* u = u_[i];
                const float* x = x_[i] + off;
                for (int k = 0; k < n; ++k) {
                    outL[k] += a * u[k] + c * x[k];
                    outR[k] += b * u[k] + d * x[k];
                }
            }
        } else {
            float onL[kBlock]{}, onR[kBlock]{};
            for (int i = 0; i < N; ++i) {
                line_[i].read<true>(inner_[i], innerL_[i], outL, n);
                line_[i].read<true>(inner_[i], innerR_[i], outR, n);
            }
            for (int i = 0; i < N; ++i) {
                const float a = outL_[i], b = outR_[i];
                const float* u = u_[i];
                const float* x = x_[i] + off;
                for (int k = 0; k < n; ++k) {
                    outL[k] += a * u[k];
                    outR[k] += b * u[k];
                    onL[k] += a * x[k];
                    onR[k] += b * x[k];
                }
            }
            for (int k = 0; k < n; ++k) {
                outL[k] = outL[k] * outG[k] + onL[k] * onsetG[k];
                outR[k] = outR[k] * outG[k] + onR[k] * onsetG[k];
            }
        }

        // 4. feedback matrix + input, write the lines
        hadamardBlock(y_, n);
        for (int i = 0; i < N; ++i) {
            float* y = y_[i];
            const float* x = x_[i] + off;
            for (int k = 0; k < n; ++k) y[k] += x[k];
            line_[i].write(y, n);
        }
    }

private:
    static constexpr float kInGain = 0.35355339f;  // 1/sqrt(N/2): stereo -> 16 channels, energy preserving
    static constexpr int kModOffset = 512;         // > max modulation depth in samples

    struct Step {
        RingDelay line[N];
        int len[N]{};
        float sign[N]{};
        int perm[N]{};
    };

    // Loop coefficients and output gains (the target of a ramp, the current values, per-sample steps).
    struct Coefs {
        float gMid[N]{}, lowK[N]{}, dampA[N]{};
        float lowC{0.0f}, outGain{1.0f}, onsetGain{0.0f};
    };

    void stepRamp() noexcept {
        if (--rampLeft_ == 0) {
            cur_ = tgt_;
            return;
        }
        for (int i = 0; i < N; ++i) {
            cur_.gMid[i] += inc_.gMid[i];
            cur_.lowK[i] += inc_.lowK[i];
            cur_.dampA[i] += inc_.dampA[i];
        }
        cur_.lowC += inc_.lowC;
        cur_.outGain += inc_.outGain;
        cur_.onsetGain += inc_.onsetGain;
    }

    void updateMod() noexcept {
        modCountdown_ = kBlock;
        const double inc = modRate_ * kBlock / sr_;
        for (int i = 0; i < N; ++i) {
            modPhase_[i] = wrap01(modPhase_[i] + inc * rateMul_[i]);
            const float target = static_cast<float>(modDepth_) * sinCycles(modPhase_[i]);
            modInc_[i] = (target - modCur_[i]) * (1.0f / kBlock);
        }
    }

    double sr_{48000.0};
    Step steps_[kSteps];
    RingDelay line_[N], ap_[N];
    int len_[N]{}, apLen_[N]{};
    double loop_[N]{}, rateMul_[N]{}, modPhase_[N]{};
    double meanLoop_{1.0}, diffSamples_{0.0}, modMax_{0.0}, modRate_{0.5}, modDepth_{0.0};
    Coefs cur_{}, tgt_{}, inc_{};
    int rampLeft_{0};
    float lowZ_[N]{}, dampZ_[N]{};
    float modCur_[N]{}, modInc_[N]{};
    float outL_[N]{}, outR_[N]{}, innerL_[N]{}, innerR_[N]{};
    int inner_[N]{};
    float apG_{0.5f};
    int modCountdown_{0};
    // channel-major scratch
    float x_[N][kReverbChunk]{}, t_[N][kReverbChunk]{};
    float v_[N][kBlock]{}, wd_[N][kBlock]{}, w_[N][kBlock]{}, u_[N][kBlock]{}, y_[N][kBlock]{};
};

// ---------------------------------------------------------------------------------------------
// Early reflections: sparse stereo tapped delay (own-side taps plus weaker cross taps); each side
// is smeared by two short all-passes so reflections read as surfaces rather than clicks. The
// air-absorption low-pass is applied per sample by the caller (its coefficient is automatable).
// ---------------------------------------------------------------------------------------------

class EarlyReflections {
public:
    static constexpr int kOwn = 12, kCross = 6, kTaps = kOwn + kCross;

    void prepare(double sr, float size) {
        sr_ = sr;
        dsp::Rng rng(0xEA51E5EC7A9Eull);
        const double msToS = sr / 1000.0;
        const double erMs = 8.0 + 72.0 * size;
        for (int side = 0; side < 2; ++side) {
            double energy = 0.0;
            for (int k = 0; k < kTaps; ++k) {
                const bool own = k < kOwn;
                const double u = rng.uniform();
                // reflection density grows with time: t ~ sqrt(uniform)
                double ms = own ? erMs * std::sqrt((k + u) / kOwn) : 0.5 + 0.9 * erMs * std::sqrt((k - kOwn + u) / kCross);
                ms = std::max(ms, 0.8);
                const double g = (0.5 + 0.5 * rng.uniform()) * (1.0 - 0.7 * ms / (erMs + 1.0)) * (own ? 1.0 : 0.55);
                Tap& t = taps_[side][k];
                t.delay = std::max(1, static_cast<int>(std::lround(ms * msToS)));
                t.src = own ? side : 1 - side;
                t.gain = static_cast<float>(rng.uniform() < 0.5f ? -g : g);
                energy += g * g;
            }
            const float norm = static_cast<float>(1.0 / std::sqrt(energy));
            for (auto& t : taps_[side]) t.gain *= norm;
            for (int a = 0; a < 2; ++a) {
                const double ms = a ? 2.3 + 0.4 * side : 1.1 + 0.2 * side;
                apLen_[side][a] = std::max(2, static_cast<int>(std::lround(ms * msToS)));
                ap_[side][a].init(apLen_[side][a] + 2);
            }
        }
        for (auto& b : buf_) b.init(static_cast<int>(std::ceil((erMs + 2.0) * msToS)) + kReverbChunk + 4);
        for (auto& f : lp_) f.reset();
    }
    void setDamping(double dampHz) {
        for (auto& f : lp_) f.setLowPass(sr_, std::min(0.45 * sr_, 1.6 * dampHz));
    }
    // Taps + diffusion for a whole chunk (n <= kReverbChunk).
    void taps(const float* inL, const float* inR, float* outL, float* outR, int n) noexcept {
        buf_[0].write(inL, n);
        buf_[1].write(inR, n);
        float* out[2] = {outL, outR};
        for (int side = 0; side < 2; ++side) {
            float* o = out[side];
            std::fill(o, o + n, 0.0f);
            for (const Tap& t : taps_[side]) buf_[t.src].read<true>(t.delay + n, t.gain, o, n);
            for (int k = 0; k < n; ++k) {
                float v = o[k];
                for (int a = 0; a < 2; ++a) {
                    RingDelay& ap = ap_[side][a];
                    const float wd = ap.tap(apLen_[side][a]);
                    const float w = dsp::flush(v + kApG * wd);
                    ap.write(w);
                    v = wd - kApG * w;
                }
                o[k] = v;
            }
        }
    }
    float lowPass(int side, float x) noexcept { return lp_[side].lowPass(x); }

private:
    static constexpr float kApG = 0.55f;
    struct Tap { int delay{1}; int src{0}; float gain{0.0f}; };
    double sr_{48000.0};
    Tap taps_[2][kTaps];
    RingDelay buf_[2];
    RingDelay ap_[2][2];
    int apLen_[2][2]{};
    dsp::OnePole lp_[2];
};

// Stereo wet-signal filters (2nd-order Butterworth low-cut and high-cut, TPT: click-free under
// automation). `samples` > 0 ramps to the new cutoff over that many samples.
struct WetFilter {
    TptFilter lc[2]{TptFilter::Mode::High, TptFilter::Mode::High}, hc[2]{TptFilter::Mode::Low, TptFilter::Mode::Low};
    void setLowCut(double sr, double hz, int samples) { for (auto& f : lc) f.setCutoff(sr, hz, samples); }
    void setHighCut(double sr, double hz, int samples) { for (auto& f : hc) f.setCutoff(sr, hz, samples); }
    void reset() {
        for (auto& f : lc) f.reset();
        for (auto& f : hc) f.reset();
    }
    float process(int ch, float x) noexcept { return hc[ch].process(lc[ch].process(x)); }
};

// Stereo predelay line with a gliding (click-free) delay time; jump() moves it at once with a short
// equal-power crossfade from the old tap (a tempo-synced predelay at a tempo jump).
struct Predelay {
    RingDelay line[2];
    Glide glide;
    double old{0.0};              // the tap faded out after a jump
    float xf{1.0f}, xfStep{0.0f};  // crossfade progress (1 = done)
    void prepare(double sr, double maxSamples, double initial) {
        for (auto& l : line) l.init(static_cast<int>(std::ceil(maxSamples)) + 8);
        glide.prepare(sr, 0.05, initial);
        xf = 1.0f;
        xfStep = static_cast<float>(1.0 / (0.03 * sr));
    }
    void jump(double delta) noexcept {
        old = glide.value();
        glide.shift(delta);
        xf = 0.0f;
    }
    // One sample: returns the gliding delay used (>= 2 samples).
    double tick(float l, float r, float& pl, float& pr) noexcept {
        const double d = glide.next();
        pl = line[0].tapCubic(d);
        pr = line[1].tapCubic(d);
        if (xf < 1.0f) {
            xf = std::min(1.0f, xf + xfStep);
            const double w = 0.25 * (0.5 - 0.5 * cosCycles(0.5 * xf));  // raised cosine, in quarter cycles
            const float gIn = sinCycles(w), gOut = cosCycles(w);
            pl = gIn * pl + gOut * line[0].tapCubic(old);
            pr = gIn * pr + gOut * line[1].tapCubic(old);
        }
        line[0].write(l);
        line[1].write(r);
        return d;
    }
};

}  // namespace as::timefx
