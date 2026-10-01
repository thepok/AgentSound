#pragma once

// Radix-2 complex FFT (single precision) and analysis windows used by the mix analyser.

#include <vector>

namespace as::analysis {

// In-place iterative radix-2 complex FFT, forward and unnormalised:
//   X[k] = sum_n x[n] * exp(-2*pi*i*k*n/N).
// Real stereo signals are analysed two at a time (left in re, right in im), see splitStereo().
// Callers that copy their input anyway can write it straight into bit-reversed order
// (buffer[bitReversed()[n]] = x[n]) and call transformPermuted(), saving the permutation pass.
class Fft {
public:
    explicit Fft(int size);  // size: power of two >= 8, throws std::invalid_argument otherwise
    int size() const noexcept { return n_; }
    const std::vector<int>& bitReversed() const noexcept { return rev_; }
    void transformPermuted(float* re, float* im) const noexcept;
    void forward(float* re, float* im) const noexcept;  // natural-order input and output
    // Decimation in frequency: natural-order input, bit-reversed output (X[k] is at bitReversed()[k]).
    // Cheapest when the caller only reads a few derived quantities per bin.
    void forwardDif(float* re, float* im) const noexcept;

private:
    int n_;
    std::vector<int> rev_;
    std::vector<float> twr_, twi_;  // stage twiddles: tw[h + j] = exp(-i*pi*j/h)
};

// Recovers bin k of the spectra of two real signals packed as re=left, im=right
// (0 < k < N/2): XL = (Z[k] + conj Z[N-k]) / 2, XR = (Z[k] - conj Z[N-k]) / 2i.
// Returns |XL|^2, |XR|^2 and Re(XL * conj XR).
struct StereoBin { double pl, pr, cross; };
// From Z[k] = a + ib and Z[N-k] = c + id (for k == 0 or N/2 pass c = a, d = b).
inline StereoBin splitStereo(double a, double b, double c, double d, bool selfConjugate) noexcept {
    if (selfConjugate) return {a * a, b * b, a * b};
    const double lr = 0.5 * (a + c), li = 0.5 * (b - d);   // XL
    const double rr = 0.5 * (b + d), ri = 0.5 * (c - a);   // XR
    return {lr * lr + li * li, rr * rr + ri * ri, lr * rr + li * ri};
}
// Natural-order spectrum.
inline StereoBin splitStereo(const float* re, const float* im, int n, int k) noexcept {
    const int m = (n - k) & (n - 1);
    return splitStereo(re[k], im[k], re[m], im[m], k == 0 || k == n / 2);
}

std::vector<float> hannWindow(int n);  // periodic Hann
std::vector<float> sineWindow(int n);  // periodic sine window: w^2 sums to exactly 1 at 50 % overlap

}  // namespace as::analysis
