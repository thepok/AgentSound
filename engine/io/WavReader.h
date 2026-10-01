#pragma once

// WAV reader for the analysis tools (zoom command, tests): PCM 8/16/24/32-bit integer and IEEE
// float 32/64, plain or WAVE_FORMAT_EXTENSIBLE, any channel count (the first two channels are
// returned; mono is duplicated into both). Reads a frame range without loading the whole file.

#include <cstdint>
#include <string>
#include <vector>

namespace as {

struct WavData {
    int sampleRate{0};
    int channels{0};             // in the file
    int bitsPerSample{0};
    bool isFloat{false};
    std::int64_t totalFrames{0}; // in the file
    std::int64_t startFrame{0};  // first frame in left/right
    std::vector<float> left, right;  // full-scale = +-1.0
    double durationSec() const noexcept { return sampleRate > 0 ? static_cast<double>(totalFrames) / sampleRate : 0.0; }
};

// Header only (no samples). Throws std::runtime_error with a readable message on anything malformed
// or unsupported.
WavData readWavInfo(const std::string& path);

// Every channel of a whole file (impulse responses: mono, stereo, 4-channel true stereo ...), with the
// same format support and errors as readWav.
struct WavChannels {
    int sampleRate{0};
    int bitsPerSample{0};
    bool isFloat{false};
    std::vector<std::vector<float>> channels;  // channels[c][frame], full-scale = +-1.0
    std::int64_t frames() const noexcept { return channels.empty() ? 0 : static_cast<std::int64_t>(channels[0].size()); }
};
WavChannels readWavChannels(const std::string& path);

// Frames [startFrame, startFrame + frameCount) clipped to the file (frameCount < 0: to the end).
// Frames outside the file are not returned: check startFrame / left.size().
WavData readWav(const std::string& path, std::int64_t startFrame = 0, std::int64_t frameCount = -1);

}  // namespace as
