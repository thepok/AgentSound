#pragma once

// Impulse responses for the 'convolver' effect: load a WAV (mono / stereo / 4-channel true stereo), trim,
// truncate, reverse, resample to the render rate (windowed sinc; 'stretch' resamples on top) and
// normalise it, and route its channels (conv::Route).

#include "fx/ConvolverEngine.h"

#include <string>
#include <vector>

namespace as::conv {

inline constexpr double kMaxIrSeconds = 30.0;  // prepared IR length limit (the song tail limit)

struct IrOptions {
    double sampleRate{48000.0};  // render rate
    double startMs{0.0};         // skip this much of the file (direct sound / pre-delay of the recording)
    double lengthSec{0.0};       // then keep at most this much, faded out (0 = to the end)
    double stretch{1.0};         // resampling factor on top of the rate conversion (2 = twice as long)
    bool reverse{false};
    bool normalize{true};        // scale to unit energy per output channel
};

struct Ir {
    std::vector<std::vector<float>> channels;  // prepared IR channels: 1, 2 or 4, equal length
    std::vector<Route> routes;
    int fileChannels{0};
    double fileRate{0.0};
    double gain{1.0};  // scale applied (normalisation, or the level compensation of resampling)
};

// Loads and prepares the IR in `paths` (resolved; `shown`: as written in the render JSON). One file of 1, 2
// or 4 channels, or several files whose channels are taken in order: 2 mono files (left, right), 2 stereo
// files (the response to the left input, then to the right input: true stereo) or 4 mono files (LL, LR,
// RL, RR). Throws ConfigError naming the file(s) on a missing, unreadable or unsupported file.
Ir loadIr(const std::vector<std::string>& paths, const std::vector<std::string>& shown, const IrOptions& o);

// Prepares IR channels already in memory (loadIr after reading the file; tests). `where` prefixes errors.
Ir prepareIr(std::vector<std::vector<float>> channels, double fileRate, const IrOptions& o, const std::string& where);

// Band-limited resampling by `ratio` (output rate / input rate): linear-phase Kaiser-windowed sinc (48 zero
// crossings per side, beta 10), cutoff at 0.96 x the lower Nyquist, amplitude preserving. The output keeps
// the kernel's whole support: input time t is output sample t * ratio + resampleDelay(ratio) (about
// 1 ms at 48 kHz), so an IR that starts at full level keeps its exact spectrum. prepareIr then trims that
// head where it carries less than -70 dB of the IR's energy (zero latency: the file's timing is kept).
std::vector<float> resample(const std::vector<float>& x, double ratio);
int resampleDelay(double ratio);

// An 'ir' path as the engine resolves it: relative to the assets folder, or absolute as is.
std::string resolveIrPath(const std::string& assetDir, const std::string& path);

}  // namespace as::conv
