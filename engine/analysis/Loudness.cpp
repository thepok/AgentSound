#include "analysis/Loudness.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <utility>

namespace as::analysis {

namespace {

constexpr double kPi = 3.14159265358979323846;

double besselI0(double x) {
    double sum = 1.0, term = 1.0;
    for (int k = 1; k < 64; ++k) {
        term *= (x / (2.0 * k)) * (x / (2.0 * k));
        sum += term;
        if (term < sum * 1e-17) break;
    }
    return sum;
}

double percentile(const std::vector<double>& sorted, double p) {
    if (sorted.empty()) return 0.0;
    const double pos = p * static_cast<double>(sorted.size() - 1);
    const auto i = static_cast<std::size_t>(pos);
    const double f = pos - static_cast<double>(i);
    if (i + 1 >= sorted.size()) return sorted.back();
    return sorted[i] + (sorted[i + 1] - sorted[i]) * f;
}

}  // namespace

double Biquad64::powerGain(double freqHz, double sampleRate) const noexcept {
    const double w = 2.0 * kPi * freqHz / sampleRate;
    const std::complex<double> z1 = std::polar(1.0, -w), z2 = std::polar(1.0, -2.0 * w);
    const std::complex<double> num = b0 + b1 * z1 + b2 * z2;
    const std::complex<double> den = 1.0 + a1 * z1 + a2 * z2;
    return std::norm(num) / std::max(std::norm(den), 1e-300);
}

Biquad64 Biquad64::lowPass(double sampleRate, double freqHz, double q) {
    const double w0 = 2.0 * kPi * std::clamp(freqHz, 1.0, sampleRate * 0.49) / sampleRate;
    const double cw = std::cos(w0), alpha = std::sin(w0) / (2.0 * q);
    const double a0 = 1.0 + alpha;
    Biquad64 f;
    f.b0 = (1.0 - cw) / 2.0 / a0;
    f.b1 = (1.0 - cw) / a0;
    f.b2 = f.b0;
    f.a1 = -2.0 * cw / a0;
    f.a2 = (1.0 - alpha) / a0;
    return f;
}

KWeighting::KWeighting(double sampleRate) {
    {   // Stage 1: high shelf, +4 dB above ~1.7 kHz (head acoustics).
        const double f0 = 1681.974450955533, gainDb = 3.999843853973347, q = 0.7071752369554196;
        const double k = std::tan(kPi * f0 / sampleRate);
        const double vh = std::pow(10.0, gainDb / 20.0);
        const double vb = std::pow(vh, 0.4996667741545416);
        const double a0 = 1.0 + k / q + k * k;
        shelf.b0 = (vh + vb * k / q + k * k) / a0;
        shelf.b1 = 2.0 * (k * k - vh) / a0;
        shelf.b2 = (vh - vb * k / q + k * k) / a0;
        shelf.a1 = 2.0 * (k * k - 1.0) / a0;
        shelf.a2 = (1.0 - k / q + k * k) / a0;
    }
    {   // Stage 2: RLB high-pass at ~38 Hz. Numerator is exactly [1, -2, 1] as in the standard.
        const double f0 = 38.13547087602444, q = 0.5003270373238773;
        const double k = std::tan(kPi * f0 / sampleRate);
        const double a0 = 1.0 + k / q + k * k;
        highpass.b0 = 1.0;
        highpass.b1 = -2.0;
        highpass.b2 = 1.0;
        highpass.a1 = 2.0 * (k * k - 1.0) / a0;
        highpass.a2 = (1.0 - k / q + k * k) / a0;
    }
}

double lufsFromMeanSquare(double ms) noexcept {
    if (!(ms > 0.0)) return kDbFloor;
    return std::max(kDbFloor, -0.691 + 10.0 * std::log10(ms));
}

double dbFromPower(double ms) noexcept {
    if (!(ms > 0.0)) return kDbFloor;
    return std::max(kDbFloor, 10.0 * std::log10(ms));
}

double dbFromAmplitude(double a) noexcept {
    if (!(a > 0.0)) return kDbFloor;
    return std::max(kDbFloor, 20.0 * std::log10(a));
}

double integratedLoudness(const std::vector<double>& blocks) {
    double sum = 0.0;
    std::size_t count = 0;
    for (double ms : blocks)
        if (lufsFromMeanSquare(ms) > -70.0) { sum += ms; ++count; }
    if (count == 0) return kDbFloor;
    const double relativeGate = lufsFromMeanSquare(sum / static_cast<double>(count)) - 10.0;
    double sum2 = 0.0;
    std::size_t count2 = 0;
    for (double ms : blocks) {
        const double l = lufsFromMeanSquare(ms);
        if (l > -70.0 && l > relativeGate) { sum2 += ms; ++count2; }
    }
    return count2 ? lufsFromMeanSquare(sum2 / static_cast<double>(count2)) : kDbFloor;
}

double loudnessRange(const std::vector<double>& shortTerm) {
    double sum = 0.0;
    std::size_t count = 0;
    for (double ms : shortTerm)
        if (lufsFromMeanSquare(ms) > -70.0) { sum += ms; ++count; }
    if (count < 2) return 0.0;
    const double relativeGate = lufsFromMeanSquare(sum / static_cast<double>(count)) - 20.0;
    std::vector<double> values;
    values.reserve(count);
    for (double ms : shortTerm) {
        const double l = lufsFromMeanSquare(ms);
        if (l > -70.0 && l > relativeGate) values.push_back(l);
    }
    if (values.size() < 2) return 0.0;
    std::sort(values.begin(), values.end());
    return std::max(0.0, percentile(values, 0.95) - percentile(values, 0.10));
}

TruePeak::TruePeak() {
    // y(n + p/4) = sum_j x[n - 15 + j] * g(p/4 + 15 - j),  g = sinc * Kaiser(half-length 16, beta 7).
    constexpr double kBeta = 7.0, kHalf = kTaps / 2;
    const double i0b = besselI0(kBeta);
    l1Max_ = 1.0;
    for (int p = 1; p <= 3; ++p) {
        const double phi = p / 4.0;
        double taps[kTaps], sum = 0.0;
        for (int j = 0; j < kTaps; ++j) {
            const double t = phi + (kHalf - 1) - j;
            const double u = t / kHalf;
            taps[j] = std::sin(kPi * t) / (kPi * t) * besselI0(kBeta * std::sqrt(std::max(0.0, 1.0 - u * u))) / i0b;
            sum += taps[j];
        }
        double l1 = 0.0;
        for (int j = 0; j < kTaps; ++j) {
            taps[j] /= sum;  // unity DC gain per phase
            l1 += std::fabs(taps[j]);
            coef_[static_cast<std::size_t>(p - 1)][static_cast<std::size_t>(j)] = static_cast<float>(taps[j]);
        }
        l1Max_ = std::max(l1Max_, l1);
    }
}

double TruePeak::measure(const float* x, std::size_t n) const {
    if (n == 0) return 0.0;
    constexpr int kBlock = 64, kHalf = kTaps / 2;
    const std::size_t nb = (n + kBlock - 1) / kBlock;
    std::vector<float> blockMax(nb, 0.0f);
    double peak = 0.0;
    for (std::size_t b = 0; b < nb; ++b) {
        float m = 0.0f;
        const std::size_t end = std::min(n, (b + 1) * kBlock);
        for (std::size_t i = b * kBlock; i < end; ++i) m = std::max(m, std::fabs(x[i]));
        blockMax[b] = m;
        peak = std::max(peak, static_cast<double>(m));
    }
    // Loudest neighbourhoods first, so the running maximum rises early and the rest can be skipped.
    std::vector<std::pair<float, std::uint32_t>> order(nb);
    for (std::size_t b = 0; b < nb; ++b) {
        float near = blockMax[b];
        if (b > 0) near = std::max(near, blockMax[b - 1]);
        if (b + 1 < nb) near = std::max(near, blockMax[b + 1]);
        order[b] = {near, static_cast<std::uint32_t>(b)};
    }
    std::sort(order.begin(), order.end(), [](const auto& a, const auto& b) { return a.first > b.first || (a.first == b.first && a.second < b.second); });

    const auto sn = static_cast<std::ptrdiff_t>(n);
    float buf[kBlock + kTaps];
    for (const auto& [near, b] : order) {
        if (static_cast<double>(near) * l1Max_ <= peak) break;
        // Output between x[m] and x[m+1] for m in this block needs x[m-15 .. m+16].
        const std::ptrdiff_t first = static_cast<std::ptrdiff_t>(b) * kBlock - (kHalf - 1);
        for (int i = 0; i < kBlock + kTaps; ++i) {
            const std::ptrdiff_t idx = first + i;
            buf[i] = (idx >= 0 && idx < sn) ? x[idx] : 0.0f;
        }
        float y1[kBlock] = {}, y2[kBlock] = {}, y3[kBlock] = {};
        for (int j = 0; j < kTaps; ++j) {
            const float c1 = coef_[0][static_cast<std::size_t>(j)], c2 = coef_[1][static_cast<std::size_t>(j)],
                        c3 = coef_[2][static_cast<std::size_t>(j)];
            const float* xs = buf + j;
            for (int i = 0; i < kBlock; ++i) {
                y1[i] += c1 * xs[i];
                y2[i] += c2 * xs[i];
                y3[i] += c3 * xs[i];
            }
        }
        float m = 0.0f;
        for (int i = 0; i < kBlock; ++i) m = std::max(m, std::max(std::fabs(y1[i]), std::max(std::fabs(y2[i]), std::fabs(y3[i]))));
        peak = std::max(peak, static_cast<double>(m));
    }
    return peak;
}

}  // namespace as::analysis
