#pragma once

// SoundFont 2 (2.01 / 2.04) files: strict RIFF parsing of an sfbk file into presets, instruments,
// zones (generators + modulators) and sample headers, plus the 16-bit sample pool (and the 24-bit
// sm24 extension when present). Parsed files are cached for the whole process: every 'sf2' track
// and 'sampler' zone that uses the same file shares one copy, and each (sample, loop) region is
// converted to float once.
//
// Structural problems (bad RIFF framing, wrong record sizes, indices out of range, samples outside
// the sample pool) are ConfigErrors naming the file. Spec-sanctioned leniencies: unknown generators
// are ignored, a zone other than the first without an instrument / sample generator is ignored,
// generators after the instrument / sampleID generator are ignored.

#include "instruments/SamplerCore.h"

#include <array>
#include <cstdint>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <tuple>
#include <vector>

namespace as::sf2 {

inline constexpr int kGenCount = 61;

enum Gen : int {
    StartAddrsOffset = 0, EndAddrsOffset = 1, StartloopAddrsOffset = 2, EndloopAddrsOffset = 3,
    StartAddrsCoarseOffset = 4, ModLfoToPitch = 5, VibLfoToPitch = 6, ModEnvToPitch = 7,
    InitialFilterFc = 8, InitialFilterQ = 9, ModLfoToFilterFc = 10, ModEnvToFilterFc = 11,
    EndAddrsCoarseOffset = 12, ModLfoToVolume = 13, ChorusEffectsSend = 15, ReverbEffectsSend = 16,
    Pan = 17, DelayModLfo = 21, FreqModLfo = 22, DelayVibLfo = 23, FreqVibLfo = 24, DelayModEnv = 25,
    AttackModEnv = 26, HoldModEnv = 27, DecayModEnv = 28, SustainModEnv = 29, ReleaseModEnv = 30,
    KeynumToModEnvHold = 31, KeynumToModEnvDecay = 32, DelayVolEnv = 33, AttackVolEnv = 34,
    HoldVolEnv = 35, DecayVolEnv = 36, SustainVolEnv = 37, ReleaseVolEnv = 38, KeynumToVolEnvHold = 39,
    KeynumToVolEnvDecay = 40, InstrumentGen = 41, KeyRange = 43, VelRange = 44,
    StartloopAddrsCoarseOffset = 45, Keynum = 46, Velocity = 47, InitialAttenuation = 48,
    EndloopAddrsCoarseOffset = 50, CoarseTune = 51, FineTune = 52, SampleID = 53, SampleModes = 54,
    ScaleTuning = 56, ExclusiveClass = 57, OverridingRootKey = 58
};

struct Modulator {
    std::uint16_t src{0}, dest{0};
    std::int16_t amount{0};
    std::uint16_t amtSrc{0}, trans{0};
    // SF2 identity: same sources, destination and transform (the amount may differ).
    bool sameAs(const Modulator& o) const noexcept {
        return src == o.src && dest == o.dest && amtSrc == o.amtSrc && trans == o.trans;
    }
};

struct Zone {
    std::uint8_t keyLo{0}, keyHi{127}, velLo{0}, velHi{127};
    int target{-1};                             // instrument (preset zone) or sample (instrument zone)
    std::array<std::int16_t, kGenCount> gen{};  // raw generator amounts
    std::uint64_t set{0};                       // bit g: generator g is given in this zone
    std::vector<Modulator> mods;
    bool has(int g) const noexcept { return ((set >> g) & 1u) != 0; }
};

struct Preset {
    std::string name;
    int bank{0}, program{0};
    Zone global;               // empty when the preset has no global zone
    std::vector<Zone> zones;
};

struct Instrument {
    std::string name;
    Zone global;
    std::vector<Zone> zones;
};

struct Sample {
    std::string name;
    std::uint32_t start{0}, end{0}, loopStart{0}, loopEnd{0}, rate{0};  // absolute sample-pool indices
    std::uint8_t pitch{60};    // original MIDI key (255 = unpitched)
    std::int8_t correction{0}; // cents
    std::uint16_t link{0}, type{1};
    bool rom() const noexcept { return (type & 0x8000u) != 0; }
    std::uint32_t frames() const noexcept { return end - start; }
};

class File {
public:
    std::string path;       // as loaded (canonical)
    std::string name;       // INAM
    int versionMajor{2}, versionMinor{1};
    std::vector<Preset> presets;  // file order
    std::vector<Instrument> instruments;
    std::vector<Sample> samples;
    std::vector<std::int16_t> smpl;
    std::vector<std::uint8_t> sm24;  // empty unless a valid sm24 chunk is present

    // Presets sorted by bank, then program (the listing order).
    std::vector<const Preset*> sortedPresets() const;
    const Preset* find(int bank, int program) const noexcept;
    // Name (case-insensitive, whitespace-trimmed; ties: lowest bank) or "bank:program". Throws
    // ConfigError with close matches.
    const Preset& resolvePreset(const std::string& spec) const;
    const Preset& resolvePreset(int bank, int program) const;
    // Sample by name (same matching rules). Throws ConfigError with close matches.
    int resolveSample(const std::string& spec) const;

    // Float data of a sample (24-bit precision with sm24).
    std::vector<float> sampleData(int index) const;
    // Shared playback region of a sample. Loop points are relative to the sample start and must be
    // valid for `mode`. Built on first use, cached.
    std::shared_ptr<const smp::Region> region(int index, smp::LoopMode mode, std::int64_t loopStart,
                                              std::int64_t loopEnd, bool reverse = false) const;

private:
    using Key = std::tuple<int, int, std::int64_t, std::int64_t, bool>;
    mutable std::mutex mu_;
    mutable std::map<Key, std::shared_ptr<const smp::Region>> regions_;
};

// assetDir/soundfonts/<file>, or `file` itself when it is an absolute path.
std::string resolvePath(const std::string& assetDir, const std::string& file);

// Parses the file on first use; later calls with the same path return the cached File. Throws
// ConfigError (missing file, malformed data).
std::shared_ptr<const File> load(const std::string& path);

// Number of SoundFont files parsed by this process (lets tests verify the cache).
int loadCount() noexcept;

// Helpers shared with the sampler: lower-case, trimmed, internal whitespace collapsed.
std::string normalizeName(const std::string& s);

}  // namespace as::sf2
