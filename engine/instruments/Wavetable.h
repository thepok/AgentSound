#pragma once

// Wavetables for the "wavetable" instrument (engine/instruments/VaSynth.cpp, wavetable mode): loading,
// built-in procedural tables and the band-limited mipmaps the oscillator reads. Everything here runs at
// configure / prepare time (allocation, file I/O, FFTs); the oscillator only reads the finished tables.
//
// A table is 1..kMaxFrames single-cycle frames. Every frame is resampled (spectrally) to kFrameSize
// samples = up to 1024 harmonics, its DC removed, and stored as kLevels mip levels: level k keeps the
// first kFrameSize/2 >> k harmonics (one table per octave) at 16 samples per highest harmonic (8 for the
// two lowest levels, whose top partials are faint; at least 1024 samples), read with 4-point Hermite
// interpolation: the oscillator's images stay ~70-90 dB down. ~100 KB per frame (a 256-frame table: 26 MB,
// shared by every voice and track through the cache). The whole table is normalised to peak 1 (level 0).
//
// File formats (all WAV-based files are single-cycle frames concatenated, the first channel is used):
//   - Serum: a 'clm ' chunk "<!>2048 ..." gives the frame size;
//   - Surge: .wt files ('vawt' header: frame size, frame count, float32 or int16) and WAVs with a
//     'srge' / 'srgo' chunk (version, frame size);
//   - plain WAV (Ableton Wavetable, Vital exports, Bitwig ...): the frame size param, else 2048 when the
//     length divides, else (longer than 4096) the first of 4096 / 1024 / 512 / 256 that divides;
//   - single-cycle WAVs (AKWF 600-sample cycles: any length <= 4096 that 2048 does not divide): one frame.
// File lookup (resolvePath): an absolute path; else $AGENTSOUND_WAVETABLES/<name>, then
// assets/wavetables/<name>.

#include <cstddef>
#include <memory>
#include <string>
#include <vector>

namespace as::wt {

inline constexpr int kFrameSize = 2048;        // samples per frame after resampling
inline constexpr int kHarmonics = kFrameSize / 2;
inline constexpr int kLevels = 11;             // level k: kHarmonics >> k harmonics (1024 .. 1)
inline constexpr int kMaxFrames = 512;
inline constexpr int kOversample = 16;         // stored samples per highest harmonic (levels 0-1: half)
inline constexpr int kMinLevelSize = 1024;

inline constexpr int kGuard = 3;              // stored per frame: x[n-1], x[0..n-1], x[0], x[1]

// 4-point, 3rd-order Hermite interpolation between a[0] and a[1] (reads a[-1] .. a[2]), t in [0,1]
// (O. Niemitalo's form). At >= 8 samples per highest harmonic its images stay > 80 dB down.
inline float hermite4(const float* a, float t) noexcept {
    const float c = 0.5f * (a[1] - a[-1]);
    const float v = a[0] - a[1];
    const float w = c + v;
    const float aa = w + v + 0.5f * (a[2] - a[0]);
    const float bneg = w + aa;
    return ((aa * t - bneg) * t + c) * t + a[0];
}

struct Table {
    std::string name;     // builtin name or file path
    std::string format;   // how it was read: builtin, serum, surge-wt, surge-wav, wav, single-cycle
    int frames = 0;       // >= 1
    int sourceFrameSize = 0;
    int levelSize[kLevels] = {};            // samples per frame at each level (power of two)
    std::size_t levelOffset[kLevels] = {};  // start of level k; frame f at levelOffset[k] + f * stride(k) + 1
    std::vector<float> data;                // each frame with its wrap-around guards (kGuard)

    std::size_t stride(int level) const noexcept { return static_cast<std::size_t>(levelSize[level] + kGuard); }
    const float* frame(int level, int f) const noexcept {
        return data.data() + levelOffset[level] + static_cast<std::size_t>(f) * stride(level) + 1;
    }
    // Mip level for a phase increment in cycles per sample at the oscillator's rate (times a warp's
    // multiplier): the smallest k with (kHarmonics >> k) * inc <= 0.5, so no partial passes that rate's
    // Nyquist. (The oscillator runs 2x oversampled: a level change only moves partials above a quarter of
    // that rate, which the decimation filter removes anyway - the switch is inaudible.)
    static int levelFor(double inc) noexcept {
        const double h = 0.5 / (inc > 1e-12 ? inc : 1e-12);
        int k = 0;
        int cap = kHarmonics;
        while (k < kLevels - 1 && cap > h) { cap >>= 1; ++k; }
        return k;
    }
    // Hermite interpolation in the phase (0..1), linear crossfade between the frames around pos (0..frames-1).
    float read(int level, float pos, double phase) const noexcept {
        const int n = levelSize[level];
        const double x = phase * n;
        int i = static_cast<int>(x);
        if (i >= n) i = n - 1;
        if (i < 0) i = 0;
        const float t = static_cast<float>(x - i);
        int f0 = static_cast<int>(pos);
        if (f0 >= frames - 1) return hermite4(frame(level, frames - 1) + i, t);
        if (f0 < 0) f0 = 0;
        const float fr = pos - static_cast<float>(f0);
        const float* a = frame(level, f0) + i;
        const float va = hermite4(a, t);
        if (fr <= 0.0f) return va;
        const float vb = hermite4(a + stride(level), t);
        return va + fr * (vb - va);
    }
};

// Frames given as harmonic spectra: spectra[f][h] = (cos, sin) amplitude of harmonic h+1, i.e. the frame
// is sum_h c_h cos(2 pi (h+1) t) + s_h sin(2 pi (h+1) t). At most kHarmonics per frame.
struct Spectrum {
    std::vector<float> c, s;
};
std::shared_ptr<const Table> fromSpectra(const std::vector<Spectrum>& spectra, std::string name, std::string format,
                                         int sourceFrameSize);
// Frames given as samples: `frames` single cycles of `frameSize` samples each (any size >= 4).
std::shared_ptr<const Table> fromSamples(const std::vector<float>& samples, int frameSize, int frames, std::string name,
                                         std::string format);

// Built-in procedural tables (no files needed).
const std::vector<std::string>& builtinNames();
std::string builtinHelp();                 // one line per table
bool isBuiltin(const std::string& name);
std::shared_ptr<const Table> builtin(const std::string& name);  // cached; throws ConfigError if unknown

// A raw table read from a file, before resampling.
struct RawTable {
    std::vector<float> samples;
    int frameSize = 0, frames = 0;
    std::string format;
};
// frameSize > 0 forces the frame size (the length must be a multiple). Throws ConfigError.
RawTable readFile(const std::string& path, int frameSize = 0);
// readFile + fromSamples, cached by (canonical path, frameSize). Throws ConfigError.
std::shared_ptr<const Table> load(const std::string& path, int frameSize = 0);
// Resolves a table file name (see the header comment); returns the first existing candidate or throws
// ConfigError listing the places looked at.
std::string resolvePath(const std::string& assetDir, const std::string& file);
// True for names that look like table files (.wav / .wt).
bool looksLikeFile(const std::string& name);

}  // namespace as::wt
