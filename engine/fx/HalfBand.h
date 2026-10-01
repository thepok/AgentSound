#pragma once

// Polyphase IIR half-band filters for 2x / 4x oversampling (saturator, tape, exciter). Low latency
// (~5.5 samples at 1x for a 2-stage 4x chain) instead of the ~70 of linear-phase FIRs: the engine
// does not compensate latency on tracks/buses. Both channels run side by side in a two-lane vector.

#include "dsp/Dsp.h"

#include <array>
#include <cmath>
#include <cstddef>

namespace as::hb {

inline double flushD(double x) noexcept { return std::fabs(x) < 1e-30 ? 0.0 : x; }

// Polyphase IIR half-band: H(z) = (A0(z^2) + z^-1 A1(z^2)) / 2, where A0 / A1 are cascades of
// first-order allpasses (a + z^-2) / (1 + a z^-2) taking the even / odd coefficients. Closed-form
// elliptic coefficient design as in L. de Soras' hiir (after Valenzuela & Constantinides 1983).
// `transition` = transition bandwidth relative to the high rate (passband edge 0.25 - t/2).
template <int N>
std::array<double, N> designHalfBand(double transition) {
    double k = std::tan((1.0 - 2.0 * transition) * dsp::kPi / 4.0);
    k *= k;
    const double kk = std::pow(1.0 - k * k, 0.25);
    const double e = 0.5 * (1.0 - kk) / (1.0 + kk);
    const double e4 = e * e * e * e;
    const double q = e * (1.0 + e4 * (2.0 + e4 * (15.0 + 150.0 * e4)));  // elliptic nome
    const int order = 2 * N + 1;
    std::array<double, N> a{};
    for (int i = 0; i < N; ++i) {
        const double c = i + 1.0;
        double num = 0.0, den = 0.5;
        for (int m = 0; m < 30; ++m)
            num += (m % 2 ? -1.0 : 1.0) * std::pow(q, m * (m + 1)) * std::sin((2 * m + 1) * c * dsp::kPi / order);
        for (int m = 1; m < 30; ++m)
            den += (m % 2 ? -1.0 : 1.0) * std::pow(q, m * m) * std::cos(2 * m * c * dsp::kPi / order);
        const double ww = num * std::pow(q, 0.25) / den;
        const double w2 = ww * ww;
        const double x = std::sqrt((1.0 - w2 * k) * (1.0 - w2 / k)) / (1.0 + w2);
        a[static_cast<std::size_t>(i)] = (1.0 - x) / (1.0 + x);
    }
    return a;
}

// Two lanes (left, right) processed together: the allpass cascades are latency-bound serial
// chains, so running both channels side by side doubles throughput.
#if defined(__GNUC__)
typedef double D2 __attribute__((vector_size(16)));
#else
struct D2 {
    double v[2];
    double& operator[](int i) noexcept { return v[i]; }
    double operator[](int i) const noexcept { return v[i]; }
    friend D2 operator+(D2 a, D2 b) noexcept { return {{a.v[0] + b.v[0], a.v[1] + b.v[1]}}; }
    friend D2 operator-(D2 a, D2 b) noexcept { return {{a.v[0] - b.v[0], a.v[1] - b.v[1]}}; }
    friend D2 operator*(D2 a, D2 b) noexcept { return {{a.v[0] * b.v[0], a.v[1] * b.v[1]}}; }
    friend D2 operator*(D2 a, double b) noexcept { return {{a.v[0] * b, a.v[1] * b}}; }
};
#endif
inline D2 d2(double l, double r) noexcept { D2 v; v[0] = l; v[1] = r; return v; }
inline void flushD2(D2& v) noexcept { v[0] = flushD(v[0]); v[1] = flushD(v[1]); }

template <int N>
class HalfBand {
    static_assert(N % 2 == 0, "coefficients come in (even path, odd path) pairs");

public:
    using Coefs = std::array<double, N>;
    void reset() noexcept { m_.fill(d2(0.0, 0.0)); }
    void flush() noexcept { for (auto& v : m_) flushD2(v); }
    // 1 -> 2: the two output phases, earlier first.
    void up(const Coefs& c, D2 x, D2& o0, D2& o1) noexcept {
        o0 = o1 = x;
        run(c, o0, o1);
    }
    // 2 -> 1 from two consecutive high-rate samples.
    D2 down(const Coefs& c, D2 early, D2 late) noexcept {
        D2 s0 = late, s1 = early;
        run(c, s0, s1);
        return (s0 + s1) * 0.5;
    }

private:
    // m_[i] = previous input of section i, m_[i + 2] = its previous output.
    void run(const Coefs& c, D2& s0, D2& s1) noexcept {
        for (std::size_t i = 0; i < static_cast<std::size_t>(N); i += 2) {
            const D2 t0 = (s0 - m_[i + 2]) * c[i] + m_[i];
            const D2 t1 = (s1 - m_[i + 3]) * c[i + 1] + m_[i + 1];
            m_[i] = s0;
            m_[i + 1] = s1;
            s0 = t0;
            s1 = t1;
        }
        m_[N] = s0;
        m_[N + 1] = s1;
    }
    std::array<D2, N + 2> m_{};
};

}  // namespace as::hb
