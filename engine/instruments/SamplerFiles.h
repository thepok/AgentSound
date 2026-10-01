#pragma once

// Sample files of the 'sampler': WAV loading straight into the playback core's guarded segment A, a
// process-wide cache shared by every zone, instrument instance and track that plays the same file, and a
// parallel preloader for libraries with thousands of files.
//
// WAV: PCM 8/16/24/32-bit integer or IEEE float 32/64, plain, WAVE_FORMAT_EXTENSIBLE or RF64; any channel
// count (the first two channels are played, or a channel mix: see ChannelGain). Lossless WavPack streams are
// decoded too, whatever their extension (GrandOrgue sample sets store their pipes as WavPack '.wav' files). Storage: 8- and 16-bit files, and 24-bit files whose low byte
// is zero everywhere (16-bit material converted to 24 bit, e.g. FLAC -> WAV), are kept as 16-bit integers
// (lossless, half the memory of floats); true 24-bit, 32-bit and float files as floats. The 'smpl' chunk
// provides the MIDI unity note (+ pitch fraction) and the first loop (start, inclusive end, type).
// Deterministic: the decoded data does not depend on the loading order or the number of threads.

#include "instruments/SamplerCore.h"

#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace as::smp {

struct FileLoop {
    std::int64_t start{0}, end{0};   // [start, end) in frames of the file (end = the smpl end + 1)
    bool pingpong{false};            // smpl loop type 1 (alternating)
};

struct SampleFile {
    std::string path;                        // cache key (normalized absolute path)
    int channels{1};                         // played channels (1 or 2; 2 with a channel mix)
    int fileChannels{1}, bits{16};
    bool isFloat{false};
    double rate{44100.0};
    std::int64_t frames{0};
    bool reversed{false};
    std::shared_ptr<const Segment> a;        // guarded data for Region (kGuardA zeros on both sides)
    std::optional<FileLoop> loop;            // first smpl loop, mirrored when reversed; only when it lies in the file
    std::optional<double> unityNote;         // smpl MIDI unity note + pitch fraction (semitones)
};

// A channel of a multichannel file mixed into the stereo pair at load time (zone field "channels": one mic mix of
// a multi-mic drum kit, without derived files): left += gainL x channel, right += gainR x channel.
struct ChannelGain {
    int channel{0};         // 0-based channel of the file
    float left{1.0f}, right{1.0f};
};

// Normalized path used as the cache key (lexically normalized, forward slashes); with a channel mix, the mix is
// part of the key (each mix of a file is decoded and cached once).
std::string fileKey(const std::string& path);
std::string fileKey(const std::string& path, const std::vector<ChannelGain>& mix);

// The decoded file (cached for the whole process). Throws std::runtime_error naming the file when it cannot
// be read or is not a supported WAV. With a (non-empty) channel mix the file is stereo (float) and holds the mix.
std::shared_ptr<const SampleFile> loadSampleFile(const std::string& path, bool reverse, const std::vector<ChannelGain>& mix = {});

struct FileRequest {
    std::string path;
    std::vector<ChannelGain> mix;
};

struct LoadStats {
    int requested{0};      // distinct files asked for
    int loaded{0};         // decoded by this call
    int cached{0};         // already in memory (shared with earlier instruments / tracks)
    std::uint64_t bytes{0};       // memory of the files loaded by this call
    std::uint64_t fileBytes{0};   // bytes read from disk by this call
    double seconds{0.0};
};

// Loads every file of `paths` that is not cached yet, on up to 8 threads. Returns the errors by path
// (empty when everything loaded); `stats` (optional) receives the counts.
// Errors are keyed by fileKey(path, mix).
std::map<std::string, std::string> preloadSampleFiles(const std::vector<std::string>& paths, bool reverse,
                                                      LoadStats* stats = nullptr);
std::map<std::string, std::string> preloadSampleFiles(const std::vector<FileRequest>& requests, bool reverse,
                                                      LoadStats* stats = nullptr);

// Memory of every cached sample file (bytes) and their number: tests and load summaries.
std::uint64_t cachedSampleBytes() noexcept;
int cachedSampleFiles() noexcept;

// Built-in generators (SFZ '*sine', '*noise'): a looped single-cycle sine (root C4 = 60 at its rate) and one
// second of seeded white noise (uniform, full scale). Shared, immutable.
std::shared_ptr<const Region> sineRegion();
std::shared_ptr<const Region> noiseRegion();

}  // namespace as::smp
