#include "analysis/StreamStats.h"

#include "analysis/Loudness.h"

#include <algorithm>
#include <cmath>
#include <utility>

namespace as::analysis {

namespace {
// ~85 ms frames; halved until the hop fits in one 100 ms tick so every tick gets a spectrum.
int fftSizeFor(double sr) {
    int n = sr > 60000.0 ? 8192 : 4096;
    while (n > 256 && n / 2 > static_cast<int>(sr / 10.0)) n /= 2;
    return n;
}
}  // namespace

SpectralSetup::SpectralSetup(double sr)
    : sampleRate(sr), n(fftSizeFor(sr)), hop(n / 2), fft(n), window(sineWindow(n)) {
    const int half = n / 2;
    binSlot.resize(static_cast<std::size_t>(half + 1));
    binK.resize(static_cast<std::size_t>(half + 1));
    binLog2Hz.resize(static_cast<std::size_t>(half + 1));
    const KWeighting kw(sr);
    lowBins = 0;
    for (int k = 0; k <= half; ++k) {
        const double f = k * sr / n;
        int slot = kUltraSlot;
        if (f < kBandEdgesHz[0]) {
            slot = kInfraSlot;
        } else {
            for (int b = 0; b < kNumBands; ++b)
                if (f < kBandEdgesHz[b + 1]) { slot = b; break; }
        }
        const auto i = static_cast<std::size_t>(k);
        binSlot[i] = static_cast<std::uint8_t>(slot);
        binK[i] = static_cast<float>(kw.powerGain(std::max(f, 0.1), sr));
        binLog2Hz[i] = static_cast<float>(std::log2(std::max(f, 1.0)));
        if (f < kLowMonoHz) lowBins = k + 1;
    }
    // Slots are contiguous bin ranges (frequency order: infra, 7 bands, ultra).
    for (int sl = 0; sl < kBandSlots; ++sl) { slotBegin[sl] = half + 1; slotEnd[sl] = 0; }
    for (int k = 0; k <= half; ++k) {
        const int sl = binSlot[static_cast<std::size_t>(k)];
        slotBegin[sl] = std::min(slotBegin[sl], k);
        slotEnd[sl] = std::max(slotEnd[sl], k + 1);
    }
    for (int sl = 0; sl < kBandSlots; ++sl)
        if (slotEnd[sl] < slotBegin[sl]) slotBegin[sl] = slotEnd[sl] = 0;
    re.resize(static_cast<std::size_t>(n));
    im.resize(static_cast<std::size_t>(n));
    power.resize(static_cast<std::size_t>(n));
    binPower.resize(static_cast<std::size_t>(half + 1));
}

StreamStats::StreamStats(SpectralSetup& setup, int tickLen, std::size_t reserveTicks, bool keepSpectrum, bool lowEnvelope)
    : s_(setup), tickLen_(tickLen), mask_(setup.n - 1),
      ringL_(static_cast<std::size_t>(setup.n), 0.0f), ringR_(static_cast<std::size_t>(setup.n), 0.0f),
      // The ring starts with n/2 zeros so the first window is centred on sample 0.
      ringPos_(setup.n / 2), nextWindow_(setup.n), keepSpectrum_(keepSpectrum), lowEnvOn_(lowEnvelope),
      envLen_(std::max(1, tickLen / 10)),
      // 4th-order Butterworth low-pass at kLowMonoHz (two biquads, Q 0.541 / 1.307).
      envLp1_(Biquad64::lowPass(setup.sampleRate, kLowMonoHz, 0.5411961)),
      envLp2_(Biquad64::lowPass(setup.sampleRate, kLowMonoHz, 1.3065630)) {
    ticks_.reserve(reserveTicks);
    if (lowEnvOn_) lowEnv_.reserve(reserveTicks * 10);
    if (keepSpectrum_) spectrum_.assign(static_cast<std::size_t>(setup.n / 2 + 1), 0.0);
}

void StreamStats::setBoundaries(std::vector<std::int64_t> explicitBoundaries, double startBeat, double bpm) {
    BarGrid grid;
    grid.startBeat = startBeat;
    grid.bpm = bpm;
    grid.sampleRate = s_.sampleRate;
    setBoundaries(std::move(explicitBoundaries), grid);
}

void StreamStats::setBoundaries(std::vector<std::int64_t> explicitBoundaries, const BarGrid& bars) {
    std::sort(explicitBoundaries.begin(), explicitBoundaries.end());
    explicit_ = std::move(explicitBoundaries);
    explicitIdx_ = 0;
    grid_ = bars;
    gridBar_ = std::floor(grid_.barAt(grid_.startBeat));
    nextBoundary_ = nextBoundaryAfter(frames_);
}

std::int64_t StreamStats::nextBoundaryAfter(std::int64_t pos) {
    std::int64_t next = INT64_MAX;
    while (explicitIdx_ < explicit_.size() && explicit_[explicitIdx_] <= pos) ++explicitIdx_;
    if (explicitIdx_ < explicit_.size()) next = explicit_[explicitIdx_];
    if (grid_.enabled()) {
        while (grid_.barStartSample(gridBar_) <= pos) gridBar_ += 1.0;
        next = std::min(next, grid_.barStartSample(gridBar_));
    }
    return next;
}

bool StreamStats::segmentRange(std::int64_t s0, std::int64_t s1, std::size_t& i0, std::size_t& i1) const noexcept {
    s0 = std::max<std::int64_t>(s0, 0);
    s1 = std::min(s1, frames_);
    if (s1 <= s0) return false;
    auto startOf = [&](std::int64_t s, std::size_t& idx) {
        const auto it = std::lower_bound(segs_.begin(), segs_.end(), s, [](const Segment& g, std::int64_t v) { return g.start < v; });
        if (it == segs_.end() || it->start != s) return false;
        idx = static_cast<std::size_t>(it - segs_.begin());
        return true;
    };
    if (!startOf(s0, i0)) return false;
    if (s1 >= frames_) {
        i1 = segs_.size();
        return true;
    }
    return startOf(s1, i1);
}

Tick& StreamStats::tickAt(std::size_t i) {
    if (i >= ticks_.size()) ticks_.resize(i + 1);
    return ticks_[i];
}

double StreamStats::tickFrames(std::size_t i) const noexcept {
    const std::int64_t start = static_cast<std::int64_t>(i) * tickLen_;
    return static_cast<double>(std::clamp<std::int64_t>(frames_ - start, 0, tickLen_));
}

double StreamStats::centroidHz() const noexcept {
    return centroidDen_ > 0.0 ? std::exp2(centroidNum_ / centroidDen_) : 0.0;
}

void StreamStats::feed(const float* L, const float* R, int frames) {
    int i = 0;
    while (i < frames) {
        const int n = static_cast<int>(std::min<std::int64_t>({static_cast<std::int64_t>(frames - i),
                                                              static_cast<std::int64_t>(tickLen_ - tickFill_),
                                                              nextWindow_ - ringPos_, nextBoundary_ - frames_}));
        double ll = 0.0, rr = 0.0, lr = 0.0;
        float peak = 0.0f;
        for (int k = 0; k < n; ++k) {
            float l = L[i + k], r = R[i + k];
            if (!(std::fabs(l) < 1e30f)) { l = 0.0f; ++nonFinite_; }
            if (!(std::fabs(r) < 1e30f)) { r = 0.0f; ++nonFinite_; }
            const auto idx = static_cast<std::size_t>((ringPos_ + k) & mask_);
            ringL_[idx] = l;
            ringR_[idx] = r;
            ll += static_cast<double>(l) * l;
            rr += static_cast<double>(r) * r;
            lr += static_cast<double>(l) * r;
            peak = std::max(peak, std::max(std::fabs(l), std::fabs(r)));
        }
        const bool envIdle = ll + rr == 0.0 && envLp1_.x1 == 0.0 && envLp1_.x2 == 0.0 && envLp1_.y1 == 0.0 &&
                             envLp1_.y2 == 0.0 && envLp2_.x1 == 0.0 && envLp2_.x2 == 0.0 && envLp2_.y1 == 0.0 && envLp2_.y2 == 0.0;
        if (lowEnvOn_ && envIdle) {  // silent input, settled filters: only the frame count advances
            for (int left = n; left > 0;) {
                const int step = std::min(left, envLen_ - envFill_);
                envFill_ += step;
                left -= step;
                if (envFill_ == envLen_) {
                    lowEnv_.push_back(static_cast<float>(envAcc_));
                    envAcc_ = 0.0;
                    envFill_ = 0;
                }
            }
        } else if (lowEnvOn_) {
            for (int k = 0; k < n; ++k) {
                const auto idx = static_cast<std::size_t>((ringPos_ + k) & mask_);  // sanitised samples
                const double y = envLp2_.process(envLp1_.process(0.5 * (static_cast<double>(ringL_[idx]) + ringR_[idx])));
                envAcc_ += y * y;
                if (++envFill_ == envLen_) {
                    lowEnv_.push_back(static_cast<float>(envAcc_));
                    envAcc_ = 0.0;
                    envFill_ = 0;
                }
            }
        }
        if (ll + rr > 0.0) lastNonZero_ = ringPos_ + n - 1;
        accLL_ += ll;
        accRR_ += rr;
        accLR_ += lr;
        Segment& seg = segs_.back();
        seg.ll += ll;
        seg.rr += rr;
        seg.lr += lr;
        seg.peak = std::max(seg.peak, peak);
        accPeak_ = std::max(accPeak_, peak);
        tickFill_ += n;
        ringPos_ += n;
        frames_ += n;
        i += n;
        if (frames_ == nextBoundary_) {
            segs_.push_back(Segment{frames_});
            nextBoundary_ = nextBoundaryAfter(frames_);
        }
        if (tickFill_ == tickLen_) {
            Tick& t = tickAt(static_cast<std::size_t>((frames_ - 1) / tickLen_));
            t.ll = static_cast<float>(accLL_);
            t.rr = static_cast<float>(accRR_);
            t.lr = static_cast<float>(accLR_);
            t.peak = accPeak_;
            accLL_ = accRR_ = accLR_ = 0.0;
            accPeak_ = 0.0f;
            tickFill_ = 0;
        }
        if (ringPos_ == nextWindow_) {
            processWindow(false);
            nextWindow_ += s_.hop;
        }
    }
}

void StreamStats::processWindow(bool flushing) {
    const int n = s_.n;
    if (lastNonZero_ < ringPos_ - n) return;  // all-zero window: nothing to add
    const std::int64_t centre = ringPos_ - n;  // in stream samples
    std::size_t tick = static_cast<std::size_t>(std::max<std::int64_t>(0, centre) / tickLen_);
    if (flushing) {
        if (ticks_.empty()) return;
        tick = std::min(tick, ticks_.size() - 1);
    }

    float* re = s_.re.data();
    float* im = s_.im.data();
    const float* w = s_.window.data();
    // Oldest sample first: ring[first..n) then ring[0..first).
    const auto first = static_cast<int>((ringPos_ - n) & mask_);
    const float* rl = ringL_.data();
    const float* rr = ringR_.data();
    const int n1 = n - first;
    for (int i = 0; i < n1; ++i) {
        re[i] = rl[first + i] * w[i];
        im[i] = rr[first + i] * w[i];
    }
    for (int i = n1; i < n; ++i) {
        re[i] = rl[i - n1] * w[i];
        im[i] = rr[i - n1] * w[i];
    }
    s_.fft.forwardDif(re, im);  // bin k lives at rev[k]
    const int* rev = s_.fft.bitReversed().data();

    // |XL|^2 + |XR|^2 = (|Z[k]|^2 + |Z[N-k]|^2) / 2; one-sided (x2) power per bin.
    const int half = n / 2;
    float* q = s_.power.data();  // |Z|^2 in transform order
    for (int j = 0; j < n; ++j) q[j] = re[j] * re[j] + im[j] * im[j];
    float* p = s_.binPower.data();
    p[0] = q[rev[0]];
    p[half] = q[rev[half]];
    for (int k = 1; k < half; ++k) p[k] = q[rev[k]] + q[rev[n - k]];

    double slot[kBandSlots] = {};
    for (int sl = 0; sl < kBandSlots; ++sl) {
        float acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};
        int k = s_.slotBegin[sl];
        const int end = s_.slotEnd[sl];
        for (; k + 4 <= end; k += 4) {
            acc[0] += p[k]; acc[1] += p[k + 1]; acc[2] += p[k + 2]; acc[3] += p[k + 3];
        }
        for (; k < end; ++k) acc[0] += p[k];
        slot[sl] = static_cast<double>(acc[0]) + acc[1] + acc[2] + acc[3];
    }
    float kAcc[4] = {0.0f, 0.0f, 0.0f, 0.0f}, cAcc[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    const float* wk = s_.binK.data();
    const float* lf = s_.binLog2Hz.data();
    int k = 0;
    for (; k + 4 <= half + 1; k += 4) {
        kAcc[0] += p[k] * wk[k]; kAcc[1] += p[k + 1] * wk[k + 1]; kAcc[2] += p[k + 2] * wk[k + 2]; kAcc[3] += p[k + 3] * wk[k + 3];
        cAcc[0] += p[k] * lf[k]; cAcc[1] += p[k + 1] * lf[k + 1]; cAcc[2] += p[k + 2] * lf[k + 2]; cAcc[3] += p[k + 3] * lf[k + 3];
    }
    for (; k <= half; ++k) { kAcc[0] += p[k] * wk[k]; cAcc[0] += p[k] * lf[k]; }
    const double kSum = static_cast<double>(kAcc[0]) + kAcc[1] + kAcc[2] + kAcc[3];
    // Centroid over 20 Hz..20 kHz only: remove the infra/ultra bins from the log-frequency sum.
    double cNum = static_cast<double>(cAcc[0]) + cAcc[1] + cAcc[2] + cAcc[3], cDen = 0.0;
    for (int sl : {kInfraSlot, kUltraSlot})
        for (int b = s_.slotBegin[sl]; b < s_.slotEnd[sl]; ++b) cNum -= static_cast<double>(p[b]) * lf[b];
    for (int b = 0; b < kNumBands; ++b) cDen += slot[b];

    double lowLL = 0.0, lowRR = 0.0, lowLR = 0.0;
    for (int b = 0; b < s_.lowBins; ++b) {
        const int zk = rev[b], zm = rev[(n - b) & (n - 1)];
        const StereoBin sb = splitStereo(re[zk], im[zk], re[zm], im[zm], b == 0);
        const double scale = (b == 0 || b == half) ? 1.0 : 2.0;
        lowLL += sb.pl * scale;
        lowRR += sb.pr * scale;
        lowLR += sb.cross * scale;
    }
    if (keepSpectrum_)
        for (int b = 0; b <= half; ++b) spectrum_[static_cast<std::size_t>(b)] += p[b];

    Tick& t = tickAt(tick);
    double total = 0.0;
    for (int s = 0; s < kBandSlots; ++s) {
        t.band[s] += static_cast<float>(slot[s]);
        total += slot[s];
    }
    t.spec += static_cast<float>(total);
    t.k += static_cast<float>(kSum);
    t.lowLL += static_cast<float>(lowLL);
    t.lowRR += static_cast<float>(lowRR);
    t.lowLR += static_cast<float>(lowLR);
    centroidNum_ += cNum;
    centroidDen_ += cDen;
}

void StreamStats::finalize() {
    if (finalized_) return;
    finalized_ = true;
    const auto numTicks = static_cast<std::size_t>((frames_ + tickLen_ - 1) / tickLen_);
    if (tickFill_ > 0) {
        Tick& t = tickAt(numTicks - 1);
        t.ll = static_cast<float>(accLL_);
        t.rr = static_cast<float>(accRR_);
        t.lr = static_cast<float>(accLR_);
        t.peak = accPeak_;
    }
    ticks_.resize(numTicks);
    if (lowEnvOn_ && envFill_ > 0) lowEnv_.push_back(static_cast<float>(envAcc_));
    // Flush: every window whose support still overlaps the signal.
    while (numTicks > 0 && nextWindow_ - s_.n < frames_ + s_.n / 2) {
        for (; ringPos_ < nextWindow_; ++ringPos_) {
            const auto idx = static_cast<std::size_t>(ringPos_ & mask_);
            ringL_[idx] = 0.0f;
            ringR_[idx] = 0.0f;
        }
        processWindow(true);
        nextWindow_ += s_.hop;
    }
    // Spectral fields carry band *proportions*; scale them to the exact time-domain energy.
    for (Tick& t : ticks_) {
        const double e = static_cast<double>(t.ll) + t.rr;
        const double g = (t.spec > 0.0f && e > 0.0) ? e / t.spec : 0.0;
        for (float& b : t.band) b = static_cast<float>(b * g);
        t.k = static_cast<float>(t.k * g);
        t.lowLL = static_cast<float>(t.lowLL * g);
        t.lowRR = static_cast<float>(t.lowRR * g);
        t.lowLR = static_cast<float>(t.lowLR * g);
        t.spec = static_cast<float>(e);
    }
}

}  // namespace as::analysis
