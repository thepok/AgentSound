#include "analysis/Fft.h"

#include <cmath>
#include <stdexcept>
#include <utility>

namespace as::analysis {

namespace {
constexpr double kPi = 3.14159265358979323846;
}

Fft::Fft(int size) : n_(size) {
    if (size < 8 || (size & (size - 1)) != 0) throw std::invalid_argument("Fft size must be a power of two >= 8");
    int bits = 0;
    while ((1 << bits) < size) ++bits;
    rev_.resize(static_cast<std::size_t>(size));
    for (int i = 0; i < size; ++i) {
        int r = 0;
        for (int b = 0; b < bits; ++b)
            if (i & (1 << b)) r |= 1 << (bits - 1 - b);
        rev_[static_cast<std::size_t>(i)] = r;
    }
    twr_.assign(static_cast<std::size_t>(size), 0.0f);
    twi_.assign(static_cast<std::size_t>(size), 0.0f);
    for (int h = 1; h < size; h <<= 1) {
        for (int j = 0; j < h; ++j) {
            const double a = -kPi * j / h;
            twr_[static_cast<std::size_t>(h + j)] = static_cast<float>(std::cos(a));
            twi_[static_cast<std::size_t>(h + j)] = static_cast<float>(std::sin(a));
        }
    }
}

void Fft::forward(float* re, float* im) const noexcept {
    for (int i = 0; i < n_; ++i) {
        const int r = rev_[static_cast<std::size_t>(i)];
        if (r > i) { std::swap(re[i], re[r]); std::swap(im[i], im[r]); }
    }
    transformPermuted(re, im);
}

void Fft::transformPermuted(float* re, float* im) const noexcept {
    // First two stages as a radix-4 pass (twiddles 1 and -i).
    for (int i = 0; i < n_; i += 4) {
        const float r0 = re[i] + re[i + 1], i0 = im[i] + im[i + 1];
        const float r1 = re[i] - re[i + 1], i1 = im[i] - im[i + 1];
        const float r2 = re[i + 2] + re[i + 3], i2 = im[i + 2] + im[i + 3];
        const float r3 = re[i + 2] - re[i + 3], i3 = im[i + 2] - im[i + 3];
        re[i] = r0 + r2; im[i] = i0 + i2;
        re[i + 2] = r0 - r2; im[i + 2] = i0 - i2;
        re[i + 1] = r1 + i3; im[i + 1] = i1 - r3;  // (r3 + i*i3) * (-i) = i3 - i*r3
        re[i + 3] = r1 - i3; im[i + 3] = i1 + r3;
    }
    // Remaining radix-2 stages; h is a multiple of 4, the 4-way unrolled body lets the
    // compiler's SLP vectoriser use SIMD without -ffast-math.
    for (int h = 4; h < n_; h <<= 1) {
        const float* __restrict wr = twr_.data() + h;
        const float* __restrict wi = twi_.data() + h;
        for (int i = 0; i < n_; i += 2 * h) {
            float* __restrict ar = re + i;
            float* __restrict ai = im + i;
            float* __restrict br = re + i + h;
            float* __restrict bi = im + i + h;
            for (int j = 0; j < h; j += 4) {
                // Straight-line 4-lane body (SLP-vectorisable).
                const float b0r = br[j], b1r = br[j + 1], b2r = br[j + 2], b3r = br[j + 3];
                const float b0i = bi[j], b1i = bi[j + 1], b2i = bi[j + 2], b3i = bi[j + 3];
                const float w0r = wr[j], w1r = wr[j + 1], w2r = wr[j + 2], w3r = wr[j + 3];
                const float w0i = wi[j], w1i = wi[j + 1], w2i = wi[j + 2], w3i = wi[j + 3];
                const float t0r = b0r * w0r - b0i * w0i, t1r = b1r * w1r - b1i * w1i;
                const float t2r = b2r * w2r - b2i * w2i, t3r = b3r * w3r - b3i * w3i;
                const float t0i = b0r * w0i + b0i * w0r, t1i = b1r * w1i + b1i * w1r;
                const float t2i = b2r * w2i + b2i * w2r, t3i = b3r * w3i + b3i * w3r;
                const float a0r = ar[j], a1r = ar[j + 1], a2r = ar[j + 2], a3r = ar[j + 3];
                const float a0i = ai[j], a1i = ai[j + 1], a2i = ai[j + 2], a3i = ai[j + 3];
                br[j] = a0r - t0r; br[j + 1] = a1r - t1r; br[j + 2] = a2r - t2r; br[j + 3] = a3r - t3r;
                bi[j] = a0i - t0i; bi[j + 1] = a1i - t1i; bi[j + 2] = a2i - t2i; bi[j + 3] = a3i - t3i;
                ar[j] = a0r + t0r; ar[j + 1] = a1r + t1r; ar[j + 2] = a2r + t2r; ar[j + 3] = a3r + t3r;
                ai[j] = a0i + t0i; ai[j + 1] = a1i + t1i; ai[j + 2] = a2i + t2i; ai[j + 3] = a3i + t3i;
            }
        }
    }
}

void Fft::forwardDif(float* re, float* im) const noexcept {
    for (int h = n_ / 2; h >= 4; h >>= 1) {
        const float* __restrict wr = twr_.data() + h;
        const float* __restrict wi = twi_.data() + h;
        for (int i = 0; i < n_; i += 2 * h) {
            float* __restrict ar = re + i;
            float* __restrict ai = im + i;
            float* __restrict br = re + i + h;
            float* __restrict bi = im + i + h;
            for (int j = 0; j < h; j += 4) {
                // (a, b) -> (a + b, (a - b) * w), straight-line 4-lane body (SLP-vectorisable).
                const float a0r = ar[j], a1r = ar[j + 1], a2r = ar[j + 2], a3r = ar[j + 3];
                const float a0i = ai[j], a1i = ai[j + 1], a2i = ai[j + 2], a3i = ai[j + 3];
                const float b0r = br[j], b1r = br[j + 1], b2r = br[j + 2], b3r = br[j + 3];
                const float b0i = bi[j], b1i = bi[j + 1], b2i = bi[j + 2], b3i = bi[j + 3];
                const float w0r = wr[j], w1r = wr[j + 1], w2r = wr[j + 2], w3r = wr[j + 3];
                const float w0i = wi[j], w1i = wi[j + 1], w2i = wi[j + 2], w3i = wi[j + 3];
                const float d0r = a0r - b0r, d1r = a1r - b1r, d2r = a2r - b2r, d3r = a3r - b3r;
                const float d0i = a0i - b0i, d1i = a1i - b1i, d2i = a2i - b2i, d3i = a3i - b3i;
                ar[j] = a0r + b0r; ar[j + 1] = a1r + b1r; ar[j + 2] = a2r + b2r; ar[j + 3] = a3r + b3r;
                ai[j] = a0i + b0i; ai[j + 1] = a1i + b1i; ai[j + 2] = a2i + b2i; ai[j + 3] = a3i + b3i;
                br[j] = d0r * w0r - d0i * w0i; br[j + 1] = d1r * w1r - d1i * w1i;
                br[j + 2] = d2r * w2r - d2i * w2i; br[j + 3] = d3r * w3r - d3i * w3i;
                bi[j] = d0r * w0i + d0i * w0r; bi[j + 1] = d1r * w1i + d1i * w1r;
                bi[j + 2] = d2r * w2i + d2i * w2r; bi[j + 3] = d3r * w3i + d3i * w3r;
            }
        }
    }
    // Last two stages (h = 2 with twiddles 1, -i; then h = 1) as one radix-4 pass.
    for (int i = 0; i < n_; i += 4) {
        const float a0r = re[i] + re[i + 2], a0i = im[i] + im[i + 2];
        const float a2r = re[i] - re[i + 2], a2i = im[i] - im[i + 2];
        const float a1r = re[i + 1] + re[i + 3], a1i = im[i + 1] + im[i + 3];
        const float a3r = im[i + 1] - im[i + 3], a3i = re[i + 3] - re[i + 1];  // (x1 - x3) * (-i)
        re[i] = a0r + a1r; im[i] = a0i + a1i;
        re[i + 1] = a0r - a1r; im[i + 1] = a0i - a1i;
        re[i + 2] = a2r + a3r; im[i + 2] = a2i + a3i;
        re[i + 3] = a2r - a3r; im[i + 3] = a2i - a3i;
    }
}

std::vector<float> hannWindow(int n) {
    std::vector<float> w(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) w[static_cast<std::size_t>(i)] = static_cast<float>(0.5 - 0.5 * std::cos(2.0 * kPi * i / n));
    return w;
}

std::vector<float> sineWindow(int n) {
    std::vector<float> w(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) w[static_cast<std::size_t>(i)] = static_cast<float>(std::sin(kPi * (i + 0.5) / n));
    return w;
}

}  // namespace as::analysis
