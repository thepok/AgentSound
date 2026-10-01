#pragma once

// Streaming click / pop detector: finds sample discontinuities (steps, single-sample spikes, hard
// cuts) in a stereo stream.
//
// Detection signal: the third difference x[n] - 3x[n-1] + 3x[n-2] - x[n-3] (+18 dB/oct, a 440 Hz
// tone is attenuated by ~74 dB relative to a step), max over L/R, summarised per ~0.67 ms block.
// A block is a click candidate when its spike is
//   * isolated: >= minContrastDb above the largest spike within +-contextMs (excluding the adjacent
//     blocks), so the periodic edges of saws/squares, hats, snares and noise never qualify (their
//     neighbourhood is just as spiky: a click is an HF spike of near-zero duration), and
//   * not a musical onset: the broadband energy after the spike (skipping 1.3 ms) must not rise by
//     more than onsetRiseDb over the energy before it. A kick drum starting mid-cycle has a sharp
//     edge too, but its body follows; a click inside a sustained sound, a hard-cut note or a pop in
//     silence has no body, and
//   * not the attack of a sound on top of others: the third-difference energy after the spike must
//     not rise by more than onsetHfRiseDb either (a DX7 bass note over its own previous note barely
//     raises the broadband energy but keeps adding high-frequency content; a click is over after
//     3-4 samples), and
//   * compact: a discontinuity is a 3-4 sample pattern in the third difference (step 1,-2,1; pop
//     1,-3,3,-1), so the third-difference energy within +-1 ms stays below maxSpread x peak^2
//     (step 1.5, pop 2.2). The click layer of a kick or a rimshot is a short noise burst instead:
//     many similar spikes, spread 5+.
// The size of the event ("jump") is the largest deviation from linear prediction,
// |x[n] - 2x[n-1] + x[n-2]|, around the spike: the step height for a step, twice the height for a
// one-sample spike. Events smaller than minJump are ignored.
//
// Cost: ~15 flops per sample; feed() never allocates except when storing a (rare) event.

#include <cstdint>
#include <vector>

namespace as::analysis {

struct ClickEvent {
    std::int64_t sample{0};    // first sample of the discontinuity (stream position)
    float jump{0.0f};          // unexplained jump (linear full scale), see above
    float spike{0.0f};         // |third difference| peak
    float context{0.0f};       // largest |third difference| within +-context outside the spike
    float riseDb{0.0f};        // broadband energy after vs before the spike (dB)
    float hfRiseDb{0.0f};      // third-difference (high-frequency) energy after vs before the spike (dB)
    float spread{0.0f};        // third-difference energy within +-1 ms / peak^2 (1.5 for a clean step)
    std::uint8_t channels{0};  // bit 0 = left, bit 1 = right
    // Samples [sample - snippetHalf, sample + snippetHalf] of both channels when the detector keeps
    // snippets (only for the strongest events, see Settings::maxSnippets).
    std::vector<float> snipL, snipR;

    double jumpDb() const noexcept;      // 20*log10(jump)
    double contrastDb() const noexcept;  // spike vs context, capped at 60 dB
};

class ClickDetector {
public:
    struct Settings {
        double minJump = 0.003;       // -50 dBFS: smaller discontinuities are inaudible in a mix
        double minContrastDb = 12.0;  // spike vs its +-context neighbourhood
        double onsetRiseDb = 4.5;     // energy rise that marks a musical onset (not a click)
        double onsetHfRiseDb = 4.0;   // rise of the high-frequency energy that lasts after the spike: the attack
                                      // of a new sound on top of others (a click has no high-frequency body)
        double maxSpread = 3.5;       // more third-difference energy around the peak = a noise burst, not a click
                                      // (a click on a busy background at the contrast limit reads ~2.9; kick click layers 4-15)
        double contextMs = 30.0;      // neighbourhood on each side (>= one period of a 33 Hz saw)
        double mergeMs = 2.0;         // events closer than this are one event (the bigger one wins)
        int snippetHalf = 0;          // samples kept on each side of an event (0 = none)
        std::size_t maxSnippets = 16; // snippets kept for the strongest events only
        std::size_t maxEvents = 400;  // further events are counted in overflow() and dropped
    };

    explicit ClickDetector(double sampleRate);
    ClickDetector(double sampleRate, const Settings& settings);

    void feed(const float* left, const float* right, int frames);  // non-finite samples count as 0
    void finish();  // evaluates the last blocks (with the context that exists); call once

    const std::vector<ClickEvent>& events() const noexcept { return events_; }  // in time order
    // Positions of isolated spikes that were rejected as musical onsets (a drum hit's attack), in
    // time order: a spike in a mix at the same moment is explained by that part's transient.
    const std::vector<std::int64_t>& onsets() const noexcept { return onsets_; }
    bool onsetNear(std::int64_t sample, std::int64_t tolerance) const noexcept;
    std::int64_t frames() const noexcept { return pos_; }
    std::int64_t overflow() const noexcept { return overflow_; }
    const Settings& settings() const noexcept { return set_; }
    int snippetHalf() const noexcept { return snippetHalf_; }
    double sampleRate() const noexcept { return sr_; }

private:
    struct Block {
        float hf{0.0f}, hfL{0.0f}, hfR{0.0f};
        std::int64_t hfPos{0};
        double energy{0.0}, hfEnergy{0.0};  // sum of squares of the samples / of the third difference (both channels)
    };
    void pushBlock();
    void evaluate(std::int64_t c, std::int64_t lastBlock);
    // Raw samples of the recent past; silence before the start and after the last fed sample.
    float rawL(std::int64_t s) const noexcept { return s < 0 || s >= pos_ ? 0.0f : ringL_[static_cast<std::size_t>(s & rawMask_)]; }
    float rawR(std::int64_t s) const noexcept { return s < 0 || s >= pos_ ? 0.0f : ringR_[static_cast<std::size_t>(s & rawMask_)]; }

    Settings set_;
    double sr_;
    int blockLen_, ctxBlocks_, onsetBlocks_, snippetHalf_;
    float contrastLin_, onsetLin_, onsetHfLin_;
    std::int64_t mergeSamples_, spreadHalf_;
    std::vector<Block> blocks_;
    std::int64_t blockMask_;
    std::vector<float> ringL_, ringR_;
    std::int64_t rawMask_;
    Block cur_;
    int fill_{0};
    std::int64_t pos_{0}, blocksDone_{0}, overflow_{0};
    float l1_{0}, l2_{0}, l3_{0}, r1_{0}, r2_{0}, r3_{0};
    std::vector<ClickEvent> events_;
    std::vector<std::int64_t> onsets_;
    bool finished_{false};
};

}  // namespace as::analysis
