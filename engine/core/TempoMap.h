#pragma once

// Song time: the tempo map (beat <-> song time <-> song sample) and the meter (bar <-> beat).
// docs/RENDER_FORMAT.md "Tempo map" and "Meter".
//
// A tempo map is a list of points [beat, bpm, curve]; the curve says how the tempo moves from the
// previous point to this one, like automation: "linear" (bpm linear in beats), "smooth" (cosine ease)
// or "step" (the previous tempo holds, the new one starts at the point). After the last point its tempo
// holds forever; before beat 0 the first tempo holds. Every conversion is analytic (no numeric
// integration): a linear segment lasts 60*(b1-b0)/(bpm1-bpm0)*ln(bpm1/bpm0) s, a smooth one
// 60*(b1-b0)/sqrt(bpm0*bpm1) s, so notes land on exact samples wherever they are. A constant map uses
// exactly the arithmetic of a plain "tempo" (sample = beat * sampleRate * 60 / bpm): bit-identical renders.
//
// Modules see the map through Instrument/Effect::setTempoMap (core/Module.h), only for songs whose
// tempo changes. It is immutable after construction; all queries are const, allocation-free and cheap
// (a binary search over the segments plus one log/exp or tan/atan).

#include <cstdint>
#include <string>
#include <vector>

namespace as {

enum class TempoCurve { Linear, Smooth, Step };

struct TempoPoint {
    double beat{0.0};
    double bpm{120.0};
    TempoCurve curve{TempoCurve::Linear};  // how the tempo moves from the previous point to this one
};

class TempoMap {
public:
    TempoMap();                                  // 120 BPM at 48 kHz
    TempoMap(double bpm, double sampleRate);     // constant tempo
    // First point at beat 0, beats strictly increasing, bpm > 0 and finite (the render-JSON parser
    // validates with good messages; this throws std::invalid_argument).
    TempoMap(const std::vector<TempoPoint>& points, double sampleRate);

    bool constant() const noexcept { return segs_.size() == 1; }
    double sampleRate() const noexcept { return sr_; }
    double initialBpm() const noexcept { return segs_.front().p0; }
    double minBpm() const noexcept { return minBpm_; }
    double maxBpm() const noexcept { return maxBpm_; }
    const std::vector<TempoPoint>& points() const noexcept { return points_; }

    // Tempo at a beat (from a "step" point's beat on: its new tempo).
    double bpmAt(double beat) const noexcept;
    // Song sample (fractional, from song beat 0 = sample 0) at which `beat` falls, and back.
    double sampleAt(double beat) const noexcept;
    double beatAtSample(double sample) const noexcept;
    double bpmAtSample(double sample) const noexcept { return bpmAt(beatAtSample(sample)); }
    // The same in seconds.
    double secondsAt(double beat) const noexcept;
    double beatAtSeconds(double seconds) const noexcept;
    // Seconds from beat b0 to beat b1 (negative when b1 < b0).
    double secondsBetween(double b0, double b1) const noexcept { return secondsAt(b1) - secondsAt(b0); }
    // The beat of the last tempo jump (a "step" point whose tempo differs from the one arriving there) in
    // (b0, b1], or NaN when there is none. Tempo-synced times (delay, predelay) restart their grid there.
    double lastJumpIn(double b0, double b1) const noexcept;
    bool hasJumps() const noexcept { return !jumps_.empty(); }

private:
    enum class Kind { Const, Linear, Smooth };
    struct Seg {
        Kind kind{Kind::Const};
        double b0{0.0}, b1{0.0};   // beats (b1 = +inf for the last segment)
        double p0{120.0}, p1{120.0};  // tempo at b0 / arriving at b1
        double s0{0.0}, s1{0.0};   // song samples at b0 / b1
        double spb{24000.0};       // const: samples per beat
        double k{0.0};             // linear: bpm per beat
        double g{0.0}, r{0.0};     // smooth: sqrt(p0 p1), sqrt(p1 / p0)
    };
    void build(const std::vector<TempoPoint>& points);
    const Seg& segAtBeat(double beat) const noexcept;
    const Seg& segAtSample(double sample) const noexcept;
    double segSample(const Seg& s, double beat) const noexcept;
    double segBeat(const Seg& s, double sample) const noexcept;
    static double segBpm(const Seg& s, double beat) noexcept;

    double sr_{48000.0};
    std::vector<Seg> segs_;
    std::vector<TempoPoint> points_;  // as given (normalised: redundant points kept)
    std::vector<double> jumps_;       // beats of the tempo jumps, increasing
    double minBpm_{120.0}, maxBpm_{120.0};
};

// Song sample of a render's first sample, i.e. of RenderContext::startBeat, rounded as the renderer
// does. With map == nullptr (constant tempo) this is exactly the classic
// llround(max(0, startBeat) * sampleRate * 60 / max(bpm, 1)); modules use it instead of deriving the
// song position themselves, so previews of tempo-mapped songs line up with full renders.
std::int64_t songStartSample(double startBeat, double sampleRate, double bpm, const TempoMap* map) noexcept;

// Song beat at song sample n for modules that walk the song sample by sample (tempo-synced LFO phases,
// beat grids): exact on every multiple of 32 song samples (the renderer's control grid), linear in
// between (error < 1e-8 beat), exact per sample in the blocks that hold a tempo step; three map
// evaluations per 32 samples, identical in previews and full renders. Not thread-safe (single-threaded
// render); the cache is mutable so const accessors can use it.
class BeatClock {
public:
    void attach(const TempoMap* map) noexcept { map_ = map; block_ = kNone; }
    const TempoMap* map() const noexcept { return map_; }
    double beatAt(std::int64_t sample) const noexcept;
    double bpmAt(std::int64_t sample) const noexcept;   // tempo at the start of the sample's 32-sample block

private:
    static constexpr std::int64_t kNone = INT64_MIN;
    void load(std::int64_t block) const noexcept;
    const TempoMap* map_{nullptr};
    mutable std::int64_t block_{kNone};
    mutable double beat0_{0.0}, beat1_{0.0}, bpm_{120.0};
    mutable bool exact_{false};
};

// ---- meter

struct MeterPoint {
    double beat{0.0};
    int numerator{4};
    int denominator{4};
    double beatsPerBar() const noexcept { return numerator * 4.0 / denominator; }
};

// Bars of the song: each point starts a new bar at its beat with numerator/denominator (beats stay
// quarter notes: 3/4 = 3 beats per bar, 6/8 = 3, 7/8 = 3.5). Bar numbers count from 0 at beat 0.
class MeterMap {
public:
    MeterMap();  // 4/4 throughout
    // First point at beat 0, beats strictly increasing, every change on a bar line of the meter before
    // it, numerator 1..64, denominator 1|2|4|8|16|32 (throws std::invalid_argument with the reason).
    explicit MeterMap(const std::vector<MeterPoint>& points);

    bool plain() const noexcept { return segs_.size() == 1 && segs_.front().bpb == 4.0; }  // 4/4 only
    const std::vector<MeterPoint>& points() const noexcept { return points_; }

    // Fractional 0-based bar number of a song beat (bar k spans [barStart(k), barStart(k + 1))).
    double barAt(double beat) const noexcept;
    // Song beat where 0-based bar `bar` (an integer) starts; fractional bars interpolate inside the bar.
    double barStart(double bar) const noexcept;
    double beatsPerBarAt(double beat) const noexcept;
    const MeterPoint& meterAt(double beat) const noexcept;
    // "bar 12 beat 3.25" (1-based, beats in quarter notes), the beat rounded to 1/100 first.
    std::string label(double beat) const;

private:
    struct Seg {
        double beat{0.0}, bpb{4.0}, bar0{0.0};  // start beat, beats per bar, bars before it
        std::size_t point{0};
    };
    std::vector<Seg> segs_;
    std::vector<MeterPoint> points_;
};

}  // namespace as
