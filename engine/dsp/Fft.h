#pragma once

// Complex FFT for fast convolution (engine/fx/Convolver*): single precision, split re / im arrays,
// radix-2^2 (radix-4 butterflies arranged like two radix-2 stages, so the spectrum is in plain
// bit-reversed order). Header-only; everything is allocated in the constructor.
//
//   forwardDif: natural-order input  -> bit-reversed spectrum   (X[k] lands at bitReversed()[k])
//   forwardDit: bit-reversed input   -> natural-order spectrum  (the same forward DFT)
//
// A convolution never reorders: forwardDif the signal, multiply bin by bin with a spectrum kept in the
// same bit-reversed order, then invert with forwardDit on the conjugated bins (IDFT(Z) = conj(DFT(conj Z)) / N).
// Unnormalised: X[k] = sum_n x[n] exp(-2 pi i k n / N). Twiddles are computed in double precision.
// The butterfly loops touch disjoint quarters of the arrays; AS_IVDEP tells the compiler so, which lets it
// vectorise them (without it, the 14 pointers exceed GCC's runtime alias-check budget).

#include <cmath>
#include <stdexcept>
#include <vector>

#if defined(__clang__)
#define AS_IVDEP _Pragma("clang loop vectorize(assume_safety)")
#elif defined(__GNUC__)
#define AS_IVDEP _Pragma("GCC ivdep")
#else
#define AS_IVDEP
#endif

namespace as::dsp {

class Fft {
public:
    explicit Fft(int n) : n_(n) {
        if (n < 4 || (n & (n - 1)) != 0) throw std::invalid_argument("dsp::Fft size must be a power of two >= 4");
        while ((1 << log2n_) < n) ++log2n_;
        rev_.resize(static_cast<std::size_t>(n));
        for (int i = 0; i < n; ++i) {
            int r = 0;
            for (int b = 0; b < log2n_; ++b)
                if (i & (1 << b)) r |= 1 << (log2n_ - 1 - b);
            rev_[static_cast<std::size_t>(i)] = r;
        }
        // Radix-4 stages in DIF order: quarter spans n/4, n/16, ... down to 1 (even log2 n) or 2 (odd
        // log2 n: then one radix-2 stage of span 1 ends the DIF and starts the DIT).
        constexpr double kTwoPi = 6.283185307179586476925286766559;
        for (int q = n / 4; q >= 1; q /= 4) {
            Stage s;
            s.q = q;
            const auto m = static_cast<std::size_t>(q);
            for (auto* w : {&s.w1r, &s.w1i, &s.w2r, &s.w2i, &s.w3r, &s.w3i}) w->resize(m);
            for (int j = 0; j < q; ++j) {
                const double a = -kTwoPi * j / (4.0 * q);
                const auto k = static_cast<std::size_t>(j);
                s.w1r[k] = static_cast<float>(std::cos(a));
                s.w1i[k] = static_cast<float>(std::sin(a));
                s.w2r[k] = static_cast<float>(std::cos(2.0 * a));
                s.w2i[k] = static_cast<float>(std::sin(2.0 * a));
                s.w3r[k] = static_cast<float>(std::cos(3.0 * a));
                s.w3i[k] = static_cast<float>(std::sin(3.0 * a));
            }
            stages_.push_back(std::move(s));
        }
        oddTail_ = (log2n_ & 1) != 0;
    }

    int size() const noexcept { return n_; }
    const int* bitReversed() const noexcept { return rev_.data(); }

    void forwardDif(float* re, float* im) const noexcept {
        for (const Stage& s : stages_) difStage(s, re, im);
        if (oddTail_) radix2(re, im);
    }

    void forwardDit(float* re, float* im) const noexcept {
        if (oddTail_) radix2(re, im);
        for (auto it = stages_.rbegin(); it != stages_.rend(); ++it) ditStage(*it, re, im);
    }

private:
    struct Stage {
        int q{1};
        std::vector<float> w1r, w1i, w2r, w2i, w3r, w3i;  // W^j, W^2j, W^3j with W = exp(-2 pi i / 4q)
    };

    // Two radix-2 DIF stages (spans 2q, q) fused; x0..x3 at j, j+q, j+2q, j+3q become
    //   j: (x0+x2)+(x1+x3)   j+q: [(x0+x2)-(x1+x3)] W^2j   j+2q: [(x0-x2)-i(x1-x3)] W^j   j+3q: [(x0-x2)+i(x1-x3)] W^3j
    void difStage(const Stage& s, float* re, float* im) const noexcept {
        const int q = s.q;
        const float* w1r = s.w1r.data();
        const float* w1i = s.w1i.data();
        const float* w2r = s.w2r.data();
        const float* w2i = s.w2i.data();
        const float* w3r = s.w3r.data();
        const float* w3i = s.w3i.data();
        for (int b = 0; b < n_; b += 4 * q) {
            float* r0 = re + b;
            float* r1 = r0 + q;
            float* r2 = r1 + q;
            float* r3 = r2 + q;
            float* i0 = im + b;
            float* i1 = i0 + q;
            float* i2 = i1 + q;
            float* i3 = i2 + q;
            AS_IVDEP
            for (int j = 0; j < q; ++j) {
                const float s0r = r0[j] + r2[j], s0i = i0[j] + i2[j];
                const float d0r = r0[j] - r2[j], d0i = i0[j] - i2[j];
                const float s1r = r1[j] + r3[j], s1i = i1[j] + i3[j];
                const float d1r = r1[j] - r3[j], d1i = i1[j] - i3[j];
                const float t1r = s0r - s1r, t1i = s0i - s1i;
                const float t2r = d0r + d1i, t2i = d0i - d1r;  // d0 - i d1
                const float t3r = d0r - d1i, t3i = d0i + d1r;  // d0 + i d1
                r0[j] = s0r + s1r;
                i0[j] = s0i + s1i;
                r1[j] = t1r * w2r[j] - t1i * w2i[j];
                i1[j] = t1r * w2i[j] + t1i * w2r[j];
                r2[j] = t2r * w1r[j] - t2i * w1i[j];
                i2[j] = t2r * w1i[j] + t2i * w1r[j];
                r3[j] = t3r * w3r[j] - t3i * w3i[j];
                i3[j] = t3r * w3i[j] + t3i * w3r[j];
            }
        }
    }

    // Two radix-2 DIT stages (spans q, 2q) fused, the mirror of difStage: with p0 = x0, p1 = x1 W^2j,
    // p2 = x2 W^j, p3 = x3 W^3j:  j: (p0+p1)+(p2+p3)  j+q: (p0-p1)-i(p2-p3)  j+2q: (p0+p1)-(p2+p3)
    // j+3q: (p0-p1)+i(p2-p3).
    void ditStage(const Stage& s, float* re, float* im) const noexcept {
        const int q = s.q;
        const float* w1r = s.w1r.data();
        const float* w1i = s.w1i.data();
        const float* w2r = s.w2r.data();
        const float* w2i = s.w2i.data();
        const float* w3r = s.w3r.data();
        const float* w3i = s.w3i.data();
        for (int b = 0; b < n_; b += 4 * q) {
            float* r0 = re + b;
            float* r1 = r0 + q;
            float* r2 = r1 + q;
            float* r3 = r2 + q;
            float* i0 = im + b;
            float* i1 = i0 + q;
            float* i2 = i1 + q;
            float* i3 = i2 + q;
            AS_IVDEP
            for (int j = 0; j < q; ++j) {
                const float p1r = r1[j] * w2r[j] - i1[j] * w2i[j], p1i = r1[j] * w2i[j] + i1[j] * w2r[j];
                const float p2r = r2[j] * w1r[j] - i2[j] * w1i[j], p2i = r2[j] * w1i[j] + i2[j] * w1r[j];
                const float p3r = r3[j] * w3r[j] - i3[j] * w3i[j], p3i = r3[j] * w3i[j] + i3[j] * w3r[j];
                const float ar = r0[j] + p1r, ai = i0[j] + p1i;
                const float br = r0[j] - p1r, bi = i0[j] - p1i;
                const float cr = p2r + p3r, ci = p2i + p3i;
                const float dr = p2r - p3r, di = p2i - p3i;
                r0[j] = ar + cr;
                i0[j] = ai + ci;
                r2[j] = ar - cr;
                i2[j] = ai - ci;
                r1[j] = br + di;  // b - i d
                i1[j] = bi - dr;
                r3[j] = br - di;  // b + i d
                i3[j] = bi + dr;
            }
        }
    }

    // Radix-2 stage of span 1 (twiddle 1): (x[2m], x[2m+1]) -> (sum, difference).
    void radix2(float* re, float* im) const noexcept {
        for (int b = 0; b < n_; b += 2) {
            const float ar = re[b], ai = im[b], br = re[b + 1], bi = im[b + 1];
            re[b] = ar + br;
            im[b] = ai + bi;
            re[b + 1] = ar - br;
            im[b + 1] = ai - bi;
        }
    }

    int n_;
    int log2n_{0};
    bool oddTail_{false};
    std::vector<int> rev_;
    std::vector<Stage> stages_;  // DIF order (largest quarter span first)
};

}  // namespace as::dsp
