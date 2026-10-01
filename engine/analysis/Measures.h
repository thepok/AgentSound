#pragma once

// Arrangement-independent measurements of a finished stereo signal (a render's mix, a bounce, a
// commercial reference track): report["measures"] of `agentsound analyze`, the numbers
// `python -m agentsound compare` puts side by side. Everything is either level-independent or in
// dBFS / LUFS, so two files can be compared loudness-matched:
//   spectrum    long-term 1/3-octave band levels 25 Hz-20 kHz (dBFS, mean square per band) of the
//               active signal (frames more than 20 dB under the average are left out, like the gated
//               integrated loudness)
//   stereo      width (side/mid energy %) and L/R correlation per octave band and per report band,
//               below 120 Hz (low-end mono) and above 150 Hz
//   loudness    integrated (BS.1770), the short-term (3 s) loudness distribution relative to it (EBU
//               R128 gating as for LRA: percentiles, 1 LU histogram), short-term / momentary maxima,
//               PSR (median of sample peak in the 3 s window minus short-term loudness)
//   transients  onsets per second and attack prominence (dB the envelope rises above its lowest
//               level just before) of the low (< 150 Hz: kick/bass), mid (150 Hz-4 kHz) and high
//               (> 2 kHz) signal; crest factors (whole signal, low, mid)
//   decay       blind tail estimate from free decays of the 400 Hz-4 kHz envelope (T60 of each decay
//               that falls >= 10 dB as a straight line in dB), "robust" only with >= 8 consistent decays
//   sustain     energy 80-300 ms after strong hits vs the first 50 ms (late/early, dB), robust only
//               with enough isolated hits and a consistent spread
//   tempo       BPM estimate from the autocorrelation of the spectral-flux onset envelope

#include "core/Params.h"  // as::json

#include <cstddef>

namespace as::analysis {

struct TempoEstimate {
    double bpm{0.0};         // 0 = no estimate (too short, no onsets)
    double confidence{0.0};  // normalised autocorrelation at the beat period, 0..1 (> ~0.15: a steady beat)
};

// Tempo of a stereo signal (searched 60..200 BPM, perceptually weighted towards ~120 BPM).
TempoEstimate estimateTempo(const float* left, const float* right, std::size_t frames, double sampleRate);

// report["measures"] (see the header comment). sampleRate 8 kHz..384 kHz; any length (very short
// signals give empty statistics). Deterministic.
json measureSignal(const float* left, const float* right, std::size_t frames, double sampleRate);

}  // namespace as::analysis
