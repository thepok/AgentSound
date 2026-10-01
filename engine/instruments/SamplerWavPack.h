#pragma once

// Lossless WavPack decoding for the sampler: GrandOrgue sample sets (and some other libraries) store their pipes
// as WavPack streams, often with a '.wav' extension. Supported: lossless integer PCM of 8..32 bits, mono / stereo /
// multichannel (one or two channels per block), joint stereo, every decorrelation term, the int32 shift info and the
// RIFF header / trailer the encoder keeps (the 'smpl' loops and 'cue ' markers live there). Not supported (a clear
// error): hybrid / lossy streams, float data, DSD. Every block is checked against its CRC, so a decode is either
// bit-exact or an error.

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace as::smp {

struct WavPackAudio {
    int channels{0};
    int bits{16};                          // bits per sample of the source (8, 16, 24, 32)
    double rate{0.0};
    std::int64_t frames{0};
    std::vector<std::int32_t> samples;     // interleaved, sign-extended integers of `bits` bits
    std::vector<unsigned char> riff;       // the embedded RIFF header + trailer (chunks, 'RIFF....WAVE' stripped)
};

// True when the bytes start with a WavPack block ("wvpk").
bool isWavPack(const unsigned char* bytes, std::size_t size) noexcept;

// Decodes a whole WavPack file held in memory. Throws std::runtime_error with the reason (without the file name).
WavPackAudio decodeWavPack(const unsigned char* bytes, std::size_t size);

}  // namespace as::smp
