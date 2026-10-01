#pragma once

// Shared sample-playback core of the 'sf2' and 'sampler' instruments: band-limited interpolation,
// loop handling, per-voice filter and the output tilt.
//
// Interpolation: 32-tap Kaiser-windowed sinc (cutoff 0.47 of the source rate, ~70 dB image rejection),
// polyphase table with 512 phases and linear interpolation between phases (interpolation error ~-95 dB),
// SSE dot products in a fixed summation order (deterministic). When a sample is played
// faster than one source frame per output frame (transposed up and/or recorded at a higher rate), the
// kernel is stretched so its cutoff tracks the output Nyquist frequency: precomputed polyphase tables on
// a semitone grid of stretches (the next step at or above the pitch ratio, 128 phases), so transposed-up
// voices cost the same per tap as native ones: no aliasing up to 8x (3 octaves above native speed);
// beyond that the kernel stays at 8x.
//
// Loops: a Region holds the sample data twice when it loops: segment A (the plain data, zero guards
// on both sides) and segment B (the real data before loopStart, then the loop repeated periodically
// from loopStart on, ping-pong loops unrolled into a forward period of 2 L - 2). A voice reads A until
// its kernel window would cross the loop end, then B, which is exact for the first pass (real pre-loop
// data in the window) and wraps by one period only once a window no longer reaches back before
// loopStart, so every window is seamless, also for loops shorter than the kernel (single-cycle
// waveforms). "Loop until release" leaves B for the same point of the pass in A as soon as the window
// lies inside the loop and plays the rest of the pass and the tail of the sample from A.
//
// Storage: segment A is shared (every region of one sample file uses the same A, whatever its loop), and
// a segment holds either floats or 16-bit integers read with a 1/32768 scale (half the memory, for 16-bit
// sources; the integer kernel sums the same products in the same order, so playback is bit-identical to
// the float storage of the same data).

#include "dsp/Dsp.h"

#include <array>
#include <cmath>
#include <cstdint>
#include <memory>
#include <vector>

namespace as::smp {

inline constexpr int kTaps = 32;
inline constexpr int kHalf = kTaps / 2;
inline constexpr int kPhases = 512;
inline constexpr int kMaxStretch = 8;
inline constexpr int kMaxHalfWidth = kHalf * kMaxStretch + 1;   // widest kernel half-width (frames)
inline constexpr int kGuardA = kMaxHalfWidth + 12;              // zero guard around segment A (+ tap padding)
inline constexpr int kGuardB = 2 * kMaxHalfWidth + 12;          // periodic guard around segment B
inline constexpr int kControl = 16;                             // voice control rate (samples)
inline constexpr int kWideSteps = 12;                           // stretched kernels per octave (semitone grid)
inline constexpr int kWideTables = 3 * kWideSteps;              // stretches 2^(1/12) .. 8
inline constexpr int kWidePhases = 128;                         // phases of the stretched kernels

// Stretched kernel for playback faster than the source (see Kernel::wide).
struct WideKernel {
    double stretch{1.0};
    int half{kHalf};           // tap t of a window reads frame floor(pos) - (half - 1) + t
    int taps{kTaps};           // multiple of 8, <= 2 * kMaxHalfWidth
    std::vector<float> coef;   // (kWidePhases + 1) rows of `taps`
    std::vector<float> delta;  // kWidePhases rows: coef[p + 1] - coef[p]
};

class Kernel {
public:
    // Built on first use; call it in prepare() so no allocation happens while rendering.
    static const Kernel& get();
    const float* row(int phase) const noexcept { return coef_.data() + static_cast<std::size_t>(phase) * kTaps; }
    const float* delta(int phase) const noexcept { return delta_.data() + static_cast<std::size_t>(phase) * kTaps; }
    // Kernel for playing `stretch` (> 1) source frames per output frame: the prototype stretched by the
    // next grid step (semitones, up to kMaxStretch) at or above `stretch`, so the cutoff lands at most a
    // semitone below the output Nyquist frequency (no aliasing), polyphase with kWidePhases phases.
    const WideKernel& wide(double stretch) const noexcept;

private:
    Kernel();
    std::vector<float> coef_, delta_;
    std::vector<WideKernel> wide_;
};

enum class LoopMode { None, Forward, PingPong };

// Planar sample storage of 1 or 2 channels: floats, or (is16) 16-bit integers scaled by 1/32768.
struct Segment {
    bool is16{false};
    std::array<std::vector<float>, 2> f;
    std::array<std::vector<std::int16_t>, 2> s;
    std::size_t length() const noexcept { return is16 ? s[0].size() : f[0].size(); }
    std::size_t bytes() const noexcept {
        return (f[0].size() + f[1].size()) * sizeof(float) + (s[0].size() + s[1].size()) * sizeof(std::int16_t);
    }
};

// Immutable sample data prepared for playback (shared between voices and instances).
struct Region {
    int channels{1};
    double rate{44100.0};                     // sample rate of the data (Hz)
    std::int64_t frames{0};                   // real frames
    std::shared_ptr<const Segment> a;         // [ch]: kGuardA zeros + frames + kGuardA zeros (shared)
    bool loop{false};
    std::int64_t loopStart{0}, loopEnd{0};    // real loop [loopStart, loopEnd) in frames
    std::int64_t period{0};                   // virtual loop period (forward: L, ping-pong: 2 L - 2)
    std::int64_t bFirst{0};                   // frame index of b[ch][0] (loopStart - kGuardB)
    Segment b;                                // [ch]: frames [bFirst, loopStart + period + kGuardB): real data
                                              // before loopStart, periodic loop data from loopStart on
    std::size_t bytes() const noexcept { return b.bytes(); }  // own memory (A is shared)
};

// Builds a region from planar float data (1 or 2 channels, equal length). Loop points are validated
// by the caller (0 <= loopStart, loopEnd <= frames, loopEnd - loopStart >= 2 for ping-pong, >= 1 else).
// `reverse` flips the data (and mirrors the loop).
Region makeRegion(const std::vector<float>* channels, int channelCount, double rate, LoopMode loop,
                  std::int64_t loopStart, std::int64_t loopEnd, bool reverse = false);

// Builds a region on a shared, already guarded segment A (kGuardA zeros + frames + kGuardA zeros per channel;
// float or 16-bit). Loop points as above, in the frames of A (a reversed A carries mirrored loop points).
Region makeRegion(std::shared_ptr<const Segment> a, int channelCount, double rate, std::int64_t frames, LoopMode loop,
                  std::int64_t loopStart, std::int64_t loopEnd);

// Playback position in a region. Plain data, copyable (voices are moved between slots).
struct Reader {
    const Region* region{nullptr};
    double pos{0.0};          // frames
    double end{0.0};          // stop when reached while not looping
    bool looping{false};
    bool exitAtWrap{false};   // loop until release, released: finish the current pass, then play the tail
    bool inB{false};
    bool done{false};

    // Starts at `start` (frames). loop: the region's loop is active.
    void start(const Region& r, double startFrame, double endFrame, bool loop) noexcept;
    // Renders n frames (n <= kControl) at `inc` source frames per output frame into out0 (and out1 for
    // stereo regions). Frames after the end of the sample are zero (done is set).
    void read(float* out0, float* out1, int n, double inc) noexcept;
    // Advances exactly like read() without computing samples (a silent layer that keeps its place, so it
    // is phase-aligned with its note when it fades in).
    void skip(int n, double inc) noexcept;

private:
    template <bool kOut>
    void run(float* out0, float* out1, int n, double inc) noexcept;
    // exitAtWrap while reading B: switches to A when that is exact, else returns the B position to wait for.
    double leaveLoop(double ls, double le, double per, int half, double inc) noexcept;
};

// Real frame of the sample that a reader position plays (loops unrolled: positions past the loop end map
// back into the loop, ping-pong loops mirrored).
double loopedFrame(const Region& r, double pos) noexcept;

// Short-time level of a sample: RMS (both channels) in 10 ms windows every 5 ms, and where its attack has
// settled (the scripted-legato entry point: the first frame after the onset whose level stays near the
// sustain level; after an attack overshoot, the first frame back near it). Computed once per sample data
// and shared (cached for the whole process); computing it allocates: call it outside process().
struct LevelTrack {
    double hop{240.0};          // frames per entry
    std::vector<float> rms;     // entry i: the window centred on frame i * hop
    double attackEnd{0.0};      // frames
    float at(double frame) const noexcept;
    // RMS over [a, b) (frames; power average of the entries)
    float mean(double a, double b) const noexcept;
};
std::shared_ptr<const LevelTrack> levelTrack(const Region& r);

// Per-voice 2-pole lowpass (Simper TPT state-variable filter): smooth under fast coefficient changes.
struct Lowpass {
    float ic1{0.0f}, ic2{0.0f};
    void reset() noexcept { ic1 = ic2 = 0.0f; }
    void flush() noexcept { ic1 = dsp::flush(ic1); ic2 = dsp::flush(ic2); }
};

struct LowpassCoefs {
    float a1{1.0f}, a2{0.0f}, a3{0.0f};
    float open{1.0f};   // 0 = filtered .. 1 = bypassed (fully open cutoff): blended, so crossing it is smooth
    void set(double sampleRate, double hz, double q) noexcept;
    float process(Lowpass& s, float x) const noexcept {
        const float v3 = x - s.ic2;
        const float v1 = a1 * s.ic1 + a2 * v3;
        const float v2 = s.ic2 + a2 * s.ic1 + a3 * v3;
        s.ic1 = 2.0f * v1 - s.ic1;
        s.ic2 = 2.0f * v2 - s.ic2;
        return v2 + open * (x - v2);
    }
};

// Gentle output tilt EQ (brightness -1..1): high shelf at 2.5 kHz (+6 .. -10 dB) and an opposite low
// shelf at 250 Hz (-/+ 2 dB). The shelf gains live only in the output mix, so automation is click-free;
// brightness 0 is bit-transparent.
class Tilt {
public:
    void prepare(double sampleRate, float brightness) noexcept;
    // In place on a stereo block; ramps from the current to `brightness` over the block.
    void process(float* l, float* r, int n, float brightness) noexcept;
    bool settled() const noexcept;

private:
    struct Svf {
        float a1{1.0f}, a2{0.0f}, a3{0.0f}, ic1{0.0f}, ic2{0.0f};
        void tune(double sampleRate, double hz, double k) noexcept;
        void tick(float v0, float& band, float& low) noexcept;
    };
    static void mix(float bright, std::array<float, 5>& m) noexcept;
    std::array<Svf, 2> high_, low_;
    std::array<float, 5> m_{1.0f, 0.0f, 0.0f, 0.0f, 0.0f};
};

// Two cascaded one-poles advanced by one block (C1-continuous parameter glide; lands on the target).
inline void glide(float& a, float& b, float target, float e) noexcept {
    a = target + (a - target) * e;
    b = a + (b - a) * e;
    if (std::fabs(a - target) + std::fabs(b - target) <= 1e-7f * (1.0f + std::fabs(target))) a = b = target;
}

// Absolute cents (SF2 convention, 0 = 8.176 Hz) -> Hz.
inline double centsToHz(double cents) noexcept { return 8.17579891564 * std::exp2(cents / 1200.0); }

}  // namespace as::smp
