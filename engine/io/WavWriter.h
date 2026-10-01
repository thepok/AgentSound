#pragma once

// Streaming stereo WAV writer (PCM 16/24 with TPDF dither, or 32-bit float).

#include "dsp/Dsp.h"

#include <cstdint>
#include <cstdio>
#include <string>

namespace as {

class WavWriter {
public:
    WavWriter() = default;
    ~WavWriter();
    WavWriter(const WavWriter&) = delete;
    WavWriter& operator=(const WavWriter&) = delete;

    // Throws std::runtime_error if the file cannot be created.
    void open(const std::string& path, int sampleRate, int bitDepth, std::uint64_t ditherSeed);
    void write(const float* left, const float* right, int frames);
    void close();  // patches the RIFF sizes; idempotent

    std::uint64_t frames() const noexcept { return frames_; }

private:
    std::FILE* file_{nullptr};
    int bitDepth_{24};
    std::uint64_t frames_{0};
    dsp::Rng rng_;
    std::string buffer_;
};

}  // namespace as
