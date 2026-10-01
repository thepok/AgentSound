#pragma once

// Loudness and peak measurement building blocks (ITU-R BS.1770-4, EBU Tech 3341/3342).

#include <array>
#include <cstddef>
#include <vector>

namespace as::analysis {

// Double-precision biquad (direct form I). Measurement filters run in double so that
// K-weighting at 38 Hz stays exact at 96 kHz; tiny outputs are flushed so long silences never
// decay into denormals.
struct Biquad64 {
    double b0{1}, b1{0}, b2{0}, a1{0}, a2{0};
    double x1{0}, x2{0}, y1{0}, y2{0};

    double process(double x) noexcept {
        const double y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1; x1 = x;
        y2 = y1; y1 = (y > -1e-30 && y < 1e-30) ? 0.0 : y;
        return y;
    }
    void reset() noexcept { x1 = x2 = y1 = y2 = 0.0; }
    double powerGain(double freqHz, double sampleRate) const noexcept;  // |H(f)|^2
    static Biquad64 lowPass(double sampleRate, double freqHz, double q);  // RBJ cookbook
};

// BS.1770-4 K-weighting (high-shelf pre-filter + RLB high-pass). Coefficients are derived from the
// analogue prototype for any sample rate; at 48 kHz they reproduce the values printed in the standard.
struct KWeighting {
    Biquad64 shelf, highpass;
    explicit KWeighting(double sampleRate = 48000.0);
    double process(double x) noexcept { return highpass.process(shelf.process(x)); }
    double powerGain(double freqHz, double sampleRate) const noexcept {
        return shelf.powerGain(freqHz, sampleRate) * highpass.powerGain(freqHz, sampleRate);
    }
    void reset() noexcept { shelf.reset(); highpass.reset(); }
};

inline constexpr double kDbFloor = -120.0;  // reported for silence

// -0.691 + 10*log10(sum of channel mean squares), floored at kDbFloor.
double lufsFromMeanSquare(double channelSummedMeanSquare) noexcept;
double dbFromPower(double meanSquare) noexcept;  // 10*log10, floored
double dbFromAmplitude(double amplitude) noexcept;  // 20*log10, floored

// Gated integrated loudness (BS.1770-4): absolute gate -70 LUFS, relative gate -10 LU.
// Input: mean squares (summed over channels) of 400 ms blocks overlapping by 75 %.
double integratedLoudness(const std::vector<double>& blockMeanSquares);

// Loudness range (EBU Tech 3342): short-term (3 s) values, absolute gate -70 LUFS, relative gate
// -20 LU, LRA = 95th - 10th percentile. Input: short-term mean squares at >= 10 Hz.
double loudnessRange(const std::vector<double>& shortTermMeanSquares);

// True-peak meter (BS.1770-4 Annex 2 method: 4x oversampling with a polyphase FIR interpolator).
// Instead of the 12-tap-per-phase example filter of the annex, a 32-tap-per-phase Kaiser-windowed
// sinc (beta 7) is used: gain error < 0.01 dB up to 0.43 fs (20.6 kHz at 48 kHz). The oversampled
// grid includes the original samples, so the result is never below the sample peak.
class TruePeak {
public:
    static constexpr int kTaps = 32;
    TruePeak();
    // Linear true peak of one channel. Blocks are visited loudest first and skipped once their
    // neighbourhood cannot exceed the running maximum (L1 bound of the filter): exact but fast.
    double measure(const float* x, std::size_t n) const;

private:
    std::array<std::array<float, kTaps>, 3> coef_{};  // phases 1/4, 2/4, 3/4
    double l1Max_{1.0};
};

}  // namespace as::analysis
