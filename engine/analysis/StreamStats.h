#pragma once

// Streaming per-signal statistics on a 100 ms grid ("ticks"): exact time-domain energy, L/R
// cross terms and peaks, plus a spectral split into the report's frequency bands, K-weighted
// (BS.1770) energy and low-frequency (< 150 Hz) stereo terms from a 50 %-overlapped
// sine-windowed STFT, and exact time-domain sums between bar/section boundaries. Memory is
// O(duration / 100 ms); no audio is stored.

#include "analysis/Fft.h"
#include "analysis/Loudness.h"
#include "core/TempoMap.h"

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace as::analysis {

inline constexpr int kNumBands = 7;
inline constexpr int kInfraSlot = 7;  // < 20 Hz
inline constexpr int kUltraSlot = 8;  // >= 20 kHz
inline constexpr int kBandSlots = 9;
inline constexpr double kBandEdgesHz[kNumBands + 1] = {20, 60, 250, 800, 2500, 6000, 12000, 20000};
inline constexpr const char* kBandNames[kNumBands] = {"sub", "bass", "lowmid", "mid", "presence", "brilliance", "air"};
inline constexpr const char* kBandRanges[kNumBands] = {"20-60 Hz", "60-250 Hz", "250-800 Hz", "800 Hz-2.5 kHz",
                                                       "2.5-6 kHz", "6-12 kHz", "12-20 kHz"};
inline constexpr double kLowMonoHz = 150.0;

// One 100 ms tick. After StreamStats::finalize() every spectral field is on the same scale as
// ll + rr (sum of squared samples over both channels), i.e. band[0..8] sums to ll + rr.
struct Tick {
    float ll{0}, rr{0}, lr{0};   // sum L^2, R^2, L*R
    float peak{0};               // max |sample|
    float k{0};                  // K-weighted energy, both channels
    float band[kBandSlots]{};    // band energies (7 bands, infra, ultra)
    float lowLL{0}, lowRR{0}, lowLR{0};  // < 150 Hz auto/cross energies
    float spec{0};               // raw spectral total (normalisation helper)
    float energy() const noexcept { return ll + rr; }
};

// Exact time-domain sums between consecutive boundaries (bar starts and section edges), so that
// per-bar and per-section levels do not leak across boundaries that fall inside a 100 ms tick.
struct Segment {
    std::int64_t start{0};  // first sample
    double ll{0}, rr{0}, lr{0};
    float peak{0};
};

// First sample of 0-based song bar `bar` (4/4) for a render starting at song beat `startBeat`.
// Shared by the streams and the report so both round identically.
inline std::int64_t barStartSample(double bar, double startBeat, double bpm, double sampleRate) noexcept {
    return static_cast<std::int64_t>(std::llround((4.0 * bar - startBeat) * 60.0 / bpm * sampleRate));
}

// The song's bars seen from a render that starts at song beat `startBeat`: first sample (counted from the
// render's first sample) of 0-based song bar `bar`. Without a tempo map and a meter this is exactly
// barStartSample() (constant tempo, 4/4); with them bars follow the meter and samples the tempo map.
struct BarGrid {
    double startBeat{0.0}, bpm{0.0}, sampleRate{48000.0};  // bpm <= 0: no bar grid
    const TempoMap* tempo{nullptr};  // a changing tempo (else the constant bpm)
    const MeterMap* meter{nullptr};  // bars other than 4/4 (else 4 beats per bar)
    double startSample{0.0};         // with `tempo`: song sample of the render's first sample
    bool enabled() const noexcept { return bpm > 0.0; }
    double barAt(double beat) const noexcept { return meter ? meter->barAt(beat) : beat / 4.0; }
    double barBeat(double bar) const noexcept { return meter ? meter->barStart(bar) : 4.0 * bar; }
    std::int64_t barStartSample(double bar) const noexcept {
        if (tempo) return static_cast<std::int64_t>(std::llround(tempo->sampleAt(barBeat(bar)) - startSample));
        return static_cast<std::int64_t>(std::llround((barBeat(bar) - startBeat) * 60.0 / bpm * sampleRate));
    }
};

// Per-sample-rate spectral set-up shared by all streams (FFT, window, bin maps, scratch).
struct SpectralSetup {
    explicit SpectralSetup(double sampleRate);
    double sampleRate;
    int n;    // FFT size (4096 at 44.1/48 kHz, 8192 at 88.2/96 kHz: ~11 Hz bins; smaller below 41 kHz so hop <= tick)
    int hop;  // n / 2
    Fft fft;
    std::vector<float> window;           // sine window
    std::vector<std::uint8_t> binSlot;   // band slot of each bin 0..n/2
    std::vector<float> binK;             // K-weighting power gain per bin
    std::vector<float> binLog2Hz;
    int lowBins;                         // bins below kLowMonoHz
    int slotBegin[kBandSlots];           // bins [slotBegin[s], slotEnd[s]) belong to slot s
    int slotEnd[kBandSlots];
    std::vector<float> re, im, power, binPower;  // scratch (single-threaded use)
};

class StreamStats {
public:
    // lowEnvelope: also keep the < 150 Hz energy of the mid signal on a 10 ms grid (for judging
    // whether kick and bass alternate, i.e. whether sidechain ducking works).
    StreamStats(SpectralSetup& setup, int tickLen, std::size_t reserveTicks, bool keepSpectrum, bool lowEnvelope = false);

    // Segment boundaries: explicit sample positions plus every bar start. Call before feeding.
    void setBoundaries(std::vector<std::int64_t> explicitBoundaries, double startBeat, double bpm);
    void setBoundaries(std::vector<std::int64_t> explicitBoundaries, const BarGrid& bars);

    void feed(const float* left, const float* right, int frames);
    void finalize();  // flushes the STFT and normalises spectral fields; call once after feeding

    const std::vector<Tick>& ticks() const noexcept { return ticks_; }
    std::int64_t frames() const noexcept { return frames_; }
    int tickLen() const noexcept { return tickLen_; }
    double tickFrames(std::size_t i) const noexcept;
    // Long-term power spectrum (sum over windows, bins 0..n/2), only if keepSpectrum.
    const std::vector<double>& spectrum() const noexcept { return spectrum_; }
    double centroidHz() const noexcept;  // energy-weighted mean of log2(f) over 20 Hz..20 kHz
    std::int64_t nonFiniteSamples() const noexcept { return nonFinite_; }
    const std::vector<float>& lowEnvelope() const noexcept { return lowEnv_; }  // energy per envFrames() samples
    int envFrames() const noexcept { return envLen_; }

    const std::vector<Segment>& segments() const noexcept { return segs_; }
    // Segments [i0, i1) covering exactly [s0, s1) (clipped to the stream); false if s0 or s1 is not
    // a boundary.
    bool segmentRange(std::int64_t s0, std::int64_t s1, std::size_t& i0, std::size_t& i1) const noexcept;

private:
    void processWindow(bool flushing);
    Tick& tickAt(std::size_t i);
    std::int64_t nextBoundaryAfter(std::int64_t pos);

    SpectralSetup& s_;
    int tickLen_;
    std::int64_t mask_;
    std::vector<float> ringL_, ringR_;
    std::int64_t ringPos_, nextWindow_, lastNonZero_{-1};
    double accLL_{0}, accRR_{0}, accLR_{0};
    float accPeak_{0};
    int tickFill_{0};
    std::int64_t frames_{0}, nonFinite_{0};
    std::vector<Tick> ticks_;
    bool keepSpectrum_;
    std::vector<double> spectrum_;
    double centroidNum_{0}, centroidDen_{0};
    bool finalized_{false};
    std::vector<Segment> segs_{Segment{}};
    std::vector<std::int64_t> explicit_;
    std::size_t explicitIdx_{0};
    BarGrid grid_;
    double gridBar_{0};  // next bar index to test
    std::int64_t nextBoundary_{INT64_MAX};
    bool lowEnvOn_;
    int envLen_, envFill_{0};
    double envAcc_{0};
    Biquad64 envLp1_, envLp2_;
    std::vector<float> lowEnv_;
};

}  // namespace as::analysis
