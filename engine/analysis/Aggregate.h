#pragma once

// Internal: sums of a stream's statistics over a time range (MixAnalyzer.cpp, Space.cpp) and the
// stereo measures derived from L/R energies.

#include "analysis/Loudness.h"
#include "analysis/StreamStats.h"

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace as::analysis {

// L/R correlation from energies: +1 mono, 0 uncorrelated, -1 anti-phase (1 for silence).
inline double correlation(double ll, double rr, double lr) {
    if (ll <= 0.0 && rr <= 0.0) return 1.0;
    if (ll <= 0.0 || rr <= 0.0) return 0.0;
    return std::clamp(lr / std::sqrt(ll * rr), -1.0, 1.0);
}

// Left vs right energy in dB (+ = louder left), limited to +-40 dB for one-sided signals.
inline double lrBalanceDb(double ll, double rr) {
    if (ll <= 0.0 && rr <= 0.0) return 0.0;
    return std::clamp(10.0 * std::log10(std::max(ll, 1e-30) / std::max(rr, 1e-30)), -40.0, 40.0);
}

// Side/mid energy ratio in %: 0 = mono, 100 = as much side as mid, capped at 999.
inline double widthPct(double ll, double rr, double lr) {
    const double side = ll + rr - 2.0 * lr, mid = ll + rr + 2.0 * lr;
    if (side <= 0.0) return 0.0;
    if (mid <= 0.0) return 999.0;
    return std::min(999.0, 100.0 * side / mid);
}

struct Agg {
    double frames{0}, ll{0}, rr{0}, lr{0}, k{0}, lowLL{0}, lowRR{0}, lowLR{0};
    double band[kBandSlots]{};
    double peak{0};

    void add(const Tick& t, double w, double f) {
        frames += f;
        ll += w * t.ll; rr += w * t.rr; lr += w * t.lr; k += w * t.k;
        lowLL += w * t.lowLL; lowRR += w * t.lowRR; lowLR += w * t.lowLR;
        for (int b = 0; b < kBandSlots; ++b) band[b] += w * t.band[b];
        peak = std::max(peak, static_cast<double>(t.peak));
    }
    // Adds another stream's sums over the same time range (frames are not added): the statistics
    // of the sum of uncorrelated streams.
    void merge(const Agg& o) {
        ll += o.ll; rr += o.rr; lr += o.lr; k += o.k;
        lowLL += o.lowLL; lowRR += o.lowRR; lowLR += o.lowLR;
        for (int b = 0; b < kBandSlots; ++b) band[b] += o.band[b];
        peak = std::max(peak, o.peak);
        frames = std::max(frames, o.frames);
    }
    // Adds the same stream's sums over another time range (frames add up).
    void append(const Agg& o) {
        const double f = frames + o.frames;
        merge(o);
        frames = f;
    }
    double energy() const { return ll + rr; }
    double bandSum() const {
        double s = 0.0;
        for (int b = 0; b < kNumBands; ++b) s += band[b];
        return s;
    }
    double ms() const { return frames > 0 ? energy() / (2.0 * frames) : 0.0; }
    double rmsDb() const { return dbFromPower(ms()); }
    double lufs() const { return frames > 0 ? lufsFromMeanSquare(k / frames) : kDbFloor; }
    double bandPct(int b) const { const double s = bandSum(); return s > 0 ? 100.0 * band[b] / s : 0.0; }
    double bandDbFs(int b) const { return frames > 0 ? dbFromPower(band[b] / (2.0 * frames)) : kDbFloor; }
    double corr() const { return correlation(ll, rr, lr); }
    double width() const { return widthPct(ll, rr, lr); }
    double lowCorr() const { return correlation(lowLL, lowRR, lowLR); }
    double lowShare() const { return energy() > 0 ? (lowLL + lowRR) / energy() : 0.0; }
    // Stereo image above kLowMonoHz (150 Hz): the part of the mix that is meant to be wide, while
    // the kick/bass fundamentals below stay mono.
    double hiLL() const { return std::max(0.0, ll - lowLL); }
    double hiRR() const { return std::max(0.0, rr - lowRR); }
    double hiLR() const { return lr - lowLR; }
    double hiWidth() const { return widthPct(hiLL(), hiRR(), hiLR()); }
    double hiCorr() const { return correlation(hiLL(), hiRR(), hiLR()); }
};

// Stats of a stream over samples [s0, s1). Spectral quantities come from the overlapping 100 ms
// ticks; when s0/s1 are segment boundaries (bars, section edges) energy, stereo terms and peak are
// exact, and the spectral split is taken from the ticks fully inside the range (so a loud
// neighbour sharing a boundary tick cannot leak into it) and rescaled to that exact energy.
inline Agg aggregate(const StreamStats& s, std::int64_t s0, std::int64_t s1) {
    Agg a, inner;
    const double T = s.tickLen();
    const double f0 = static_cast<double>(std::max<std::int64_t>(0, s0));
    const double f1 = static_cast<double>(std::min(s.frames(), s1));
    if (!(f1 > f0)) return a;
    const auto& ticks = s.ticks();
    const auto i0 = static_cast<std::size_t>(f0 / T);
    const auto i1 = std::min(ticks.size(), static_cast<std::size_t>(std::ceil(f1 / T)));
    for (std::size_t i = i0; i < i1; ++i) {
        const double start = static_cast<double>(i) * T, tf = s.tickFrames(i);
        if (tf <= 0) continue;
        const double ov = std::min(start + tf, f1) - std::max(start, f0);
        if (ov > 0) a.add(ticks[i], ov / tf, ov);
        if (ov >= tf) inner.add(ticks[i], 1.0, tf);
    }
    std::size_t g0 = 0, g1 = 0;
    if (s.segmentRange(s0, s1, g0, g1)) {
        double ll = 0.0, rr = 0.0, lr = 0.0, peak = 0.0;
        for (std::size_t g = g0; g < g1; ++g) {
            const Segment& seg = s.segments()[g];
            ll += seg.ll; rr += seg.rr; lr += seg.lr;
            peak = std::max(peak, static_cast<double>(seg.peak));
        }
        if (inner.energy() > 0.0) {
            for (int b = 0; b < kBandSlots; ++b) a.band[b] = inner.band[b];
            a.k = inner.k; a.lowLL = inner.lowLL; a.lowRR = inner.lowRR; a.lowLR = inner.lowLR;
            a.ll = inner.ll; a.rr = inner.rr;
        }
        const double approx = a.energy(), exact = ll + rr;
        const double scale = approx > 0.0 ? exact / approx : 0.0;
        for (double& b : a.band) b *= scale;
        a.k *= scale; a.lowLL *= scale; a.lowRR *= scale; a.lowLR *= scale;
        a.ll = ll; a.rr = rr; a.lr = lr; a.peak = peak;
        a.frames = f1 - f0;
    }
    return a;
}

}  // namespace as::analysis
