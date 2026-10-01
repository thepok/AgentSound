#pragma once

// Zero-latency partitioned convolution: the engine of the 'convolver' effect (engine/fx/Convolver.cpp).
//
// Stereo in -> stereo out through up to four IR channels ("routes": L->L, R->R for a stereo IR, the
// same IR on both sides for a mono IR, LL/LR/RL/RR for a true-stereo IR).
//
//   IR [0, head)                 direct form (time domain), so the output needs no future input:
//                                output sample n depends on input samples <= n (zero latency)
//   IR [S, S*(P+1)) per level    FFT partitions of block size S (uniform within a level, a frequency-
//                                domain delay line of P input spectra); levels grow by 'growth' up to
//                                'maxBlock' (non-uniform, Gardner-style): head, 4 x head, 16 x head, ...
//
// A level of block size S starts at IR offset S, so the input block that has just been completed
// (at a multiple of S) only affects output from that moment on: every block is transformed as soon as it
// is complete, the product of all partitions is inverted once and overlap-added into an output
// accumulator. Block boundaries lie on an ABSOLUTE sample grid (the song position), so the output never
// depends on how the host splits blocks or where a (preview) render starts: a render that starts at song
// sample s0 with silence before it is bit-identical to a full render with silence up to s0.
//
// Two real channels share one complex FFT (L in the real part, R in the imaginary part; the spectra are
// separated with X[k] and conj X[N-k]); spectra stay in the FFT's bit-reversed order (dsp::Fft), so there
// is no reordering pass. Summation order is fixed (deterministic). No allocation in process().

#include "dsp/Fft.h"

#include <cstdint>
#include <map>
#include <memory>
#include <vector>

namespace as::conv {

// One IR channel between an input and an output channel (0 = left, 1 = right).
struct Route {
    int in{0};
    int out{0};
    int ir{0};
};

// Default: 64 direct taps, then levels of 64 / 256 / 1024 / 4096 (3 partitions each) and 16384-sample
// blocks for the rest (a 5 s IR at 48 kHz: 14 of them); measured fastest offline for 1-8 s IRs.
struct Partitioning {
    int head{64};         // direct-form taps = the smallest FFT block (power of two)
    int growth{4};        // block-size ratio between consecutive levels (power of two >= 2)
    int maxBlock{16384};  // largest FFT block (FFT size twice that)
};

class Engine {
public:
    // irs: the IR channels (equal lengths >= 1); routes: which IR channel connects which input to which
    // output (every route's output gets the sum of its routes). `position` is the absolute sample index of
    // the first input sample (the song sample: the partition grid is absolute). Allocates everything and
    // starts silent. Throws std::invalid_argument on inconsistent arguments.
    void prepare(const std::vector<std::vector<float>>& irs, const std::vector<Route>& routes, std::uint64_t position,
                 const Partitioning& p = {});

    // n input frames -> n output frames; the outputs may alias the inputs. Any n >= 0.
    void process(const float* inL, const float* inR, float* outL, float* outR, int n) noexcept;

    int irLength() const noexcept { return length_; }

    struct LevelInfo {
        int block;           // S
        int firstPartition;  // the level covers IR samples [firstPartition * S, (firstPartition + partitions) * S)
        int partitions;
    };
    std::vector<LevelInfo> plan() const;

private:
    struct Level {
        int S{0}, N{0};
        int q0{1}, P{0};
        int ring{1};                     // input spectra kept (frequency-domain delay line)
        const dsp::Fft* fft{nullptr};
        std::vector<float> xr, xi;       // [slot][input channel][bin 0..S]
        std::vector<float> hr, hi;       // [partition][IR channel][bin 0..S], scaled by 0.5 / N
        std::vector<int> pk, pnk;        // bit-reversed positions of bins k and N - k
    };

    void runHead(int m) noexcept;
    void runLevel(Level& L) noexcept;

    int head_{64};
    int headTaps_{0};                    // min(head, IR length)
    int length_{0};
    int nIr_{0};
    std::vector<Route> routes_;
    std::vector<std::vector<float>> headIr_;   // [IR channel][tap]
    std::vector<float> hist_[2];               // [head - 1 previous samples | current chunk]
    std::vector<float> y_[2];                  // direct-form output of the chunk
    std::vector<float> inRing_[2], acc_[2];    // input history / output accumulator (absolute positions)
    std::uint64_t inMask_{0}, accMask_{0};
    std::vector<Level> levels_;
    std::map<int, std::unique_ptr<dsp::Fft>> ffts_;
    std::vector<float> fr_, fi_;               // FFT work buffers (largest N)
    std::vector<float> yr_[2], yi_[2];         // per-output spectra of one level (largest S + 1)
    std::uint64_t pos_{0};
};

}  // namespace as::conv
