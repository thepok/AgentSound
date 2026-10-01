#include "fx/ConvolverEngine.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace as::conv {

namespace {

bool isPow2(std::int64_t x) { return x > 0 && (x & (x - 1)) == 0; }

std::uint64_t pow2AtLeast(std::uint64_t x) {
    std::uint64_t p = 1;
    while (p < x) p <<= 1;
    return p;
}

// Copies n samples starting at absolute position `at` out of / into a power-of-two ring.
void ringRead(const std::vector<float>& ring, std::uint64_t mask, std::uint64_t at, float* dst, int n) noexcept {
    const std::uint64_t from = at & mask;
    const auto first = static_cast<int>(std::min<std::uint64_t>(static_cast<std::uint64_t>(n), mask + 1 - from));
    std::memcpy(dst, ring.data() + from, static_cast<std::size_t>(first) * sizeof(float));
    std::memcpy(dst + first, ring.data(), static_cast<std::size_t>(n - first) * sizeof(float));
}
void ringWrite(std::vector<float>& ring, std::uint64_t mask, std::uint64_t at, const float* src, int n) noexcept {
    const std::uint64_t from = at & mask;
    const auto first = static_cast<int>(std::min<std::uint64_t>(static_cast<std::uint64_t>(n), mask + 1 - from));
    std::memcpy(ring.data() + from, src, static_cast<std::size_t>(first) * sizeof(float));
    std::memcpy(ring.data(), src + first, static_cast<std::size_t>(n - first) * sizeof(float));
}

}  // namespace

void Engine::prepare(const std::vector<std::vector<float>>& irs, const std::vector<Route>& routes, std::uint64_t position,
                     const Partitioning& p) {
    if (irs.empty() || irs[0].empty()) throw std::invalid_argument("conv::Engine: empty impulse response");
    if (irs[0].size() > (1u << 28)) throw std::invalid_argument("conv::Engine: impulse response too long");
    for (const auto& c : irs)
        if (c.size() != irs[0].size()) throw std::invalid_argument("conv::Engine: IR channels differ in length");
    if (routes.empty()) throw std::invalid_argument("conv::Engine: no routes");
    for (const Route& r : routes)
        if (r.in < 0 || r.in > 1 || r.out < 0 || r.out > 1 || r.ir < 0 || r.ir >= static_cast<int>(irs.size()))
            throw std::invalid_argument("conv::Engine: bad route");
    if (!isPow2(p.head) || !isPow2(p.growth) || p.growth < 2 || !isPow2(p.maxBlock) || p.maxBlock < p.head)
        throw std::invalid_argument("conv::Engine: bad partitioning");

    length_ = static_cast<int>(irs[0].size());
    nIr_ = static_cast<int>(irs.size());
    routes_ = routes;
    head_ = p.head;
    headTaps_ = std::min(head_, length_);
    headIr_.assign(static_cast<std::size_t>(nIr_), {});
    for (int c = 0; c < nIr_; ++c) headIr_[static_cast<std::size_t>(c)].assign(irs[static_cast<std::size_t>(c)].begin(),
                                                                                irs[static_cast<std::size_t>(c)].begin() + headTaps_);
    for (auto& h : headIr_)
        for (float& v : h)
            if (std::fabs(v) < 1e-30f) v = 0.0f;  // (denormal taps would make every product a denormal)

    // Levels: block S covers IR [S, nextS) with nextS / S - 1 partitions while the IR goes on past nextS;
    // the last level (at maxBlock, or where the IR ends) takes the rest.
    levels_.clear();
    ffts_.clear();
    int S = head_;
    std::int64_t off = head_;
    while (off < length_) {
        const int nextS = std::min(S * p.growth, p.maxBlock);
        const std::int64_t remaining = length_ - off;
        const bool grow = nextS > S && remaining > nextS - off;
        Level L;
        L.S = S;
        L.N = 2 * S;
        L.q0 = static_cast<int>(off / S);
        L.P = static_cast<int>(grow ? (nextS - off) / S : (remaining + S - 1) / S);
        levels_.push_back(std::move(L));
        off += static_cast<std::int64_t>(levels_.back().P) * S;
        if (!grow) break;
        S = nextS;
    }

    int maxS = head_;
    for (Level& L : levels_) {
        auto& fft = ffts_[L.N];
        if (!fft) fft = std::make_unique<dsp::Fft>(L.N);
        L.fft = fft.get();
        L.ring = std::max(1, L.q0 + L.P - 1);
        const auto bins = static_cast<std::size_t>(L.S + 1);
        L.xr.assign(static_cast<std::size_t>(L.ring) * 2 * bins, 0.0f);
        L.xi.assign(L.xr.size(), 0.0f);
        L.hr.assign(static_cast<std::size_t>(L.P) * static_cast<std::size_t>(nIr_) * bins, 0.0f);
        L.hi.assign(L.hr.size(), 0.0f);
        L.pk.resize(bins);
        L.pnk.resize(bins);
        const int* rev = L.fft->bitReversed();
        for (int k = 0; k <= L.S; ++k) {
            L.pk[static_cast<std::size_t>(k)] = rev[k];
            L.pnk[static_cast<std::size_t>(k)] = rev[(L.N - k) & (L.N - 1)];
        }
        maxS = std::max(maxS, L.S);
    }
    fr_.assign(static_cast<std::size_t>(2 * maxS), 0.0f);
    fi_.assign(fr_.size(), 0.0f);
    for (int o = 0; o < 2; ++o) {
        yr_[o].assign(static_cast<std::size_t>(maxS + 1), 0.0f);
        yi_[o].assign(static_cast<std::size_t>(maxS + 1), 0.0f);
    }

    // IR partition spectra (the real partition in the real part: the spectrum needs no separation),
    // scaled by 0.5 / N: 0.5 undoes the doubled L/R separation, 1 / N the unnormalised inverse.
    for (Level& L : levels_) {
        const auto bins = static_cast<std::size_t>(L.S + 1);
        const float scale = 0.5f / static_cast<float>(L.N);  // a power of two: exact
        for (int q = 0; q < L.P; ++q) {
            for (int c = 0; c < nIr_; ++c) {
                std::fill(fr_.begin(), fr_.begin() + L.N, 0.0f);
                std::fill(fi_.begin(), fi_.begin() + L.N, 0.0f);
                const std::int64_t start = static_cast<std::int64_t>(L.q0 + q) * L.S;
                const std::int64_t count = std::min<std::int64_t>(L.S, length_ - start);
                const auto& h = irs[static_cast<std::size_t>(c)];
                if (count > 0) std::copy(h.begin() + start, h.begin() + start + count, fr_.begin());
                L.fft->forwardDif(fr_.data(), fi_.data());
                float* hr = &L.hr[(static_cast<std::size_t>(q) * static_cast<std::size_t>(nIr_) + static_cast<std::size_t>(c)) * bins];
                float* hi = &L.hi[(static_cast<std::size_t>(q) * static_cast<std::size_t>(nIr_) + static_cast<std::size_t>(c)) * bins];
                auto flush = [](float v) { return std::fabs(v) < 1e-30f ? 0.0f : v; };  // no denormal products
                for (std::size_t k = 0; k < bins; ++k) {
                    hr[k] = flush(fr_[static_cast<std::size_t>(L.pk[k])] * scale);
                    hi[k] = flush(fi_[static_cast<std::size_t>(L.pk[k])] * scale);
                }
            }
        }
    }

    const std::uint64_t inSize = pow2AtLeast(2 * static_cast<std::uint64_t>(maxS));
    const std::uint64_t accSize = pow2AtLeast(4 * static_cast<std::uint64_t>(maxS));
    inMask_ = inSize - 1;
    accMask_ = accSize - 1;
    for (int c = 0; c < 2; ++c) {
        inRing_[c].assign(levels_.empty() ? 0 : inSize, 0.0f);
        acc_[c].assign(accSize, 0.0f);
        hist_[c].assign(static_cast<std::size_t>(2 * head_ - 1), 0.0f);
        y_[c].assign(static_cast<std::size_t>(head_), 0.0f);
    }
    pos_ = position;
}

std::vector<Engine::LevelInfo> Engine::plan() const {
    std::vector<LevelInfo> out;
    for (const Level& L : levels_) out.push_back({L.S, L.q0, L.P});
    return out;
}

void Engine::process(const float* inL, const float* inR, float* outL, float* outR, int n) noexcept {
    int done = 0;
    while (done < n) {
        const int phase = static_cast<int>(pos_ & static_cast<std::uint64_t>(head_ - 1));
        const int m = std::min(n - done, head_ - phase);  // never crosses the head grid
        float* cur[2] = {hist_[0].data() + (head_ - 1), hist_[1].data() + (head_ - 1)};
        std::memcpy(cur[0], inL + done, static_cast<std::size_t>(m) * sizeof(float));  // (before any output: in may alias out)
        std::memcpy(cur[1], inR + done, static_cast<std::size_t>(m) * sizeof(float));
        if (!levels_.empty()) {
            ringWrite(inRing_[0], inMask_, pos_, cur[0], m);
            ringWrite(inRing_[1], inMask_, pos_, cur[1], m);
        }
        runHead(m);
        for (int c = 0; c < 2; ++c) {
            float* out = (c ? outR : outL) + done;
            const float* y = y_[c].data();
            float* acc = acc_[c].data();
            for (int i = 0; i < m; ++i) {
                const std::uint64_t a = (pos_ + static_cast<std::uint64_t>(i)) & accMask_;
                out[i] = y[i] + acc[a];
                acc[a] = 0.0f;
            }
            std::memmove(hist_[c].data(), hist_[c].data() + m, static_cast<std::size_t>(head_ - 1) * sizeof(float));
        }
        pos_ += static_cast<std::uint64_t>(m);
        done += m;
        if ((pos_ & static_cast<std::uint64_t>(head_ - 1)) == 0)
            for (Level& L : levels_)
                if ((pos_ & static_cast<std::uint64_t>(L.S - 1)) == 0) runLevel(L);
    }
}

// Direct form for IR [0, head): y[i] = sum_k h[k] x[i - k], k outer so the loop over i vectorises
// (each lane is one output sample; the summation order over k is fixed).
void Engine::runHead(int m) noexcept {
    std::fill(y_[0].begin(), y_[0].begin() + m, 0.0f);
    std::fill(y_[1].begin(), y_[1].begin() + m, 0.0f);
    for (const Route& r : routes_) {
        const float* h = headIr_[static_cast<std::size_t>(r.ir)].data();
        const float* x = hist_[r.in].data() + (head_ - 1);
        float* y = y_[r.out].data();
        for (int k = 0; k < headTaps_; ++k) {
            const float c = h[k];
            const float* xs = x - k;
            AS_IVDEP
            for (int i = 0; i < m; ++i) y[i] += c * xs[i];
        }
    }
}

void Engine::runLevel(Level& L) noexcept {
    const int S = L.S, N = L.N;
    const auto bins = static_cast<std::size_t>(S + 1);
    const std::uint64_t blk = pos_ / static_cast<std::uint64_t>(S);  // block blk - 1 = [pos - S, pos) is complete
    float* fr = fr_.data();
    float* fi = fi_.data();
    ringRead(inRing_[0], inMask_, pos_ - static_cast<std::uint64_t>(S), fr, S);
    ringRead(inRing_[1], inMask_, pos_ - static_cast<std::uint64_t>(S), fi, S);
    std::fill(fr + S, fr + N, 0.0f);
    std::fill(fi + S, fi + N, 0.0f);
    L.fft->forwardDif(fr, fi);

    // Separate the two real channels (x2, undone by the IR scale) into the slot of block blk - 1:
    // XL = Z[k] + conj Z[N-k], XR = -i (Z[k] - conj Z[N-k]).
    {
        const std::size_t slot = static_cast<std::size_t>((blk - 1) % static_cast<std::uint64_t>(L.ring));
        float* xlr = &L.xr[(slot * 2) * bins];
        float* xli = &L.xi[(slot * 2) * bins];
        float* xrr = &L.xr[(slot * 2 + 1) * bins];
        float* xri = &L.xi[(slot * 2 + 1) * bins];
        const int* pk = L.pk.data();
        const int* pnk = L.pnk.data();
        for (std::size_t k = 0; k < bins; ++k) {
            const float a = fr[pk[k]], b = fi[pk[k]], c = fr[pnk[k]], d = fi[pnk[k]];
            xlr[k] = a + c;
            xli[k] = b - d;
            xrr[k] = b + d;
            xri[k] = c - a;
        }
    }

    // Y_out = sum over partitions q and routes to `out` of X[blk - q] * H[q] (fixed order).
    for (int o = 0; o < 2; ++o) {
        float* yr = yr_[o].data();
        float* yi = yi_[o].data();
        std::fill(yr, yr + bins, 0.0f);
        std::fill(yi, yi + bins, 0.0f);
        for (int q = 0; q < L.P; ++q) {
            const auto qa = static_cast<std::uint64_t>(L.q0 + q);
            if (blk < qa) break;  // before the stream start: silent
            const std::size_t slot = static_cast<std::size_t>((blk - qa) % static_cast<std::uint64_t>(L.ring));
            for (const Route& r : routes_) {
                if (r.out != o) continue;
                const float* xr = &L.xr[(slot * 2 + static_cast<std::size_t>(r.in)) * bins];
                const float* xi = &L.xi[(slot * 2 + static_cast<std::size_t>(r.in)) * bins];
                const std::size_t h = (static_cast<std::size_t>(q) * static_cast<std::size_t>(nIr_) + static_cast<std::size_t>(r.ir)) * bins;
                const float* hr = &L.hr[h];
                const float* hi = &L.hi[h];
                AS_IVDEP
                for (std::size_t k = 0; k < bins; ++k) {
                    yr[k] += xr[k] * hr[k] - xi[k] * hi[k];
                    yi[k] += xr[k] * hi[k] + xi[k] * hr[k];
                }
            }
        }
    }

    // Pack the two real outputs into one spectrum Z = YL + i YR (both Hermitian, so bins S+1..N-1 follow
    // from 1..S-1), conjugated for the inverse through the forward DIT: y = conj(DFT(conj Z)) (the 1 / N is
    // in the IR scale): left = real part, right = minus the imaginary part.
    {
        const float* ylr = yr_[0].data();
        const float* yli = yi_[0].data();
        const float* yrr = yr_[1].data();
        const float* yri = yi_[1].data();
        const int* pk = L.pk.data();
        const int* pnk = L.pnk.data();
        for (int k = 0; k <= S; ++k) {
            const float a = ylr[k], b = yli[k], c = yrr[k], d = yri[k];
            fr[pk[k]] = a - d;
            fi[pk[k]] = -(b + c);
            if (k > 0 && k < S) {
                fr[pnk[k]] = a + d;
                fi[pnk[k]] = b - c;
            }
        }
    }
    L.fft->forwardDit(fr, fi);

    // Overlap-add from pos_ on.
    const std::uint64_t from = pos_ & accMask_;
    const auto first = static_cast<int>(std::min<std::uint64_t>(static_cast<std::uint64_t>(N), accMask_ + 1 - from));
    float* al = acc_[0].data() + from;
    float* ar = acc_[1].data() + from;
    for (int i = 0; i < first; ++i) {
        al[i] += fr[i];
        ar[i] -= fi[i];
    }
    al = acc_[0].data();
    ar = acc_[1].data();
    for (int i = first; i < N; ++i) {
        al[i - first] += fr[i];
        ar[i - first] -= fi[i];
    }
}

}  // namespace as::conv
