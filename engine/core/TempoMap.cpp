#include "core/TempoMap.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <limits>
#include <stdexcept>

namespace as {
namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kInf = std::numeric_limits<double>::infinity();

std::string num(double v) {
    char buf[40];
    std::snprintf(buf, sizeof buf, "%g", v);
    return buf;
}

}  // namespace

// ---------------------------------------------------------------------------------------------- TempoMap

TempoMap::TempoMap() : TempoMap(120.0, 48000.0) {}

TempoMap::TempoMap(double bpm, double sampleRate) : TempoMap(std::vector<TempoPoint>{{0.0, bpm, TempoCurve::Linear}}, sampleRate) {}

TempoMap::TempoMap(const std::vector<TempoPoint>& points, double sampleRate) : sr_(sampleRate) {
    if (!(std::isfinite(sampleRate) && sampleRate > 0.0)) throw std::invalid_argument("tempo map: sample rate must be > 0");
    build(points);
}

void TempoMap::build(const std::vector<TempoPoint>& points) {
    if (points.empty()) throw std::invalid_argument("tempo map: needs at least one point");
    if (points.front().beat != 0.0) throw std::invalid_argument("tempo map: the first point must be at beat 0");
    for (std::size_t i = 0; i < points.size(); ++i) {
        const TempoPoint& p = points[i];
        if (!(std::isfinite(p.beat) && std::isfinite(p.bpm) && p.bpm > 0.0)) {
            throw std::invalid_argument("tempo map: point " + std::to_string(i) + " needs a finite beat and bpm > 0");
        }
        if (i > 0 && !(p.beat > points[i - 1].beat)) {
            throw std::invalid_argument("tempo map: beats must be strictly increasing (point " + std::to_string(i) + " at beat " +
                                        num(p.beat) + ")");
        }
    }
    points_ = points;
    minBpm_ = maxBpm_ = points.front().bpm;
    for (const TempoPoint& p : points) {
        minBpm_ = std::min(minBpm_, p.bpm);
        maxBpm_ = std::max(maxBpm_, p.bpm);
    }

    // Segments: point i-1 -> point i shaped by point i's curve, then the last tempo forever. Constant
    // stretches of equal tempo merge, so a constant map is one segment starting at beat 0 / sample 0.
    std::vector<Seg> segs;
    auto push = [&](Seg s) {
        if (s.kind == Kind::Const && !segs.empty() && segs.back().kind == Kind::Const && segs.back().p0 == s.p0) {
            segs.back().b1 = s.b1;
            return;
        }
        segs.push_back(s);
    };
    for (std::size_t i = 1; i < points.size(); ++i) {
        const TempoPoint& a = points[i - 1];
        const TempoPoint& b = points[i];
        Seg s;
        s.b0 = a.beat;
        s.b1 = b.beat;
        s.p0 = a.bpm;
        if (b.curve == TempoCurve::Step || a.bpm == b.bpm) {
            s.kind = Kind::Const;
            s.p1 = a.bpm;
        } else {
            s.kind = b.curve == TempoCurve::Linear ? Kind::Linear : Kind::Smooth;
            s.p1 = b.bpm;
        }
        push(s);
    }
    Seg last;
    last.b0 = points.back().beat;
    last.b1 = kInf;
    last.p0 = last.p1 = points.back().bpm;
    push(last);

    double s0 = 0.0;
    for (Seg& s : segs) {
        s.s0 = s0;
        switch (s.kind) {
            case Kind::Const: s.spb = sr_ * 60.0 / s.p0; break;
            case Kind::Linear: s.k = (s.p1 - s.p0) / (s.b1 - s.b0); break;
            case Kind::Smooth:
                s.g = std::sqrt(s.p0 * s.p1);
                s.r = std::sqrt(s.p1 / s.p0);
                break;
        }
        s.s1 = std::isfinite(s.b1) ? (s.kind == Kind::Smooth ? s.s0 + 60.0 * sr_ * (s.b1 - s.b0) / s.g : segSample(s, s.b1)) : kInf;
        s0 = s.s1;
    }
    jumps_.clear();
    for (std::size_t i = 1; i < segs.size(); ++i) {
        if (segs[i].p0 != segs[i - 1].p1) jumps_.push_back(segs[i].b0);
    }
    segs_ = std::move(segs);
}

double TempoMap::lastJumpIn(double b0, double b1) const noexcept {
    if (jumps_.empty() || !(b1 > b0)) return std::numeric_limits<double>::quiet_NaN();
    const auto it = std::upper_bound(jumps_.begin(), jumps_.end(), b1);  // first jump > b1
    if (it == jumps_.begin() || !(*(it - 1) > b0)) return std::numeric_limits<double>::quiet_NaN();
    return *(it - 1);
}

const TempoMap::Seg& TempoMap::segAtBeat(double beat) const noexcept {
    // last segment with b0 <= beat (the first one for beats before 0)
    const auto it = std::upper_bound(segs_.begin(), segs_.end(), beat, [](double b, const Seg& s) { return b < s.b0; });
    return it == segs_.begin() ? segs_.front() : *(it - 1);
}

const TempoMap::Seg& TempoMap::segAtSample(double sample) const noexcept {
    const auto it = std::upper_bound(segs_.begin(), segs_.end(), sample, [](double x, const Seg& s) { return x < s.s0; });
    return it == segs_.begin() ? segs_.front() : *(it - 1);
}

double TempoMap::segSample(const Seg& s, double beat) const noexcept {
    switch (s.kind) {
        case Kind::Const: return s.s0 + (beat - s.b0) * s.spb;
        case Kind::Linear: {
            // t = 60 / k * ln(bpm(beat) / p0), with bpm linear in beats
            const double x = beat - s.b0;
            return s.s0 + 60.0 * sr_ / s.k * std::log1p(s.k * x / s.p0);
        }
        case Kind::Smooth: {
            // bpm = p0 + (p1 - p0) (1 - cos(pi u)) / 2: t = 120 L / (pi g) * atan(r tan(pi u / 2))
            const double L = s.b1 - s.b0;
            const double u = (beat - s.b0) / L;
            if (u <= 0.0) return s.s0;
            if (u >= 1.0) return s.s1;
            return s.s0 + 120.0 * sr_ * L / (kPi * s.g) * std::atan(s.r * std::tan(0.5 * kPi * u));
        }
    }
    return s.s0;
}

double TempoMap::segBeat(const Seg& s, double sample) const noexcept {
    switch (s.kind) {
        case Kind::Const: return s.b0 + (sample - s.s0) / s.spb;
        case Kind::Linear: {
            const double t = (sample - s.s0) / sr_;
            return s.b0 + s.p0 / s.k * std::expm1(s.k * t / 60.0);
        }
        case Kind::Smooth: {
            const double L = s.b1 - s.b0;
            if (sample <= s.s0) return s.b0;
            if (sample >= s.s1) return s.b1;
            const double theta = (sample - s.s0) * kPi * s.g / (120.0 * sr_ * L);
            if (theta >= 0.5 * kPi) return s.b1;
            return s.b0 + L * (2.0 / kPi) * std::atan(std::tan(theta) / s.r);
        }
    }
    return s.b0;
}

double TempoMap::segBpm(const Seg& s, double beat) noexcept {
    switch (s.kind) {
        case Kind::Const: return s.p0;
        case Kind::Linear: return s.p0 + s.k * std::clamp(beat - s.b0, 0.0, s.b1 - s.b0);
        case Kind::Smooth: {
            const double u = std::clamp((beat - s.b0) / (s.b1 - s.b0), 0.0, 1.0);
            return s.p0 + (s.p1 - s.p0) * (0.5 - 0.5 * std::cos(kPi * u));
        }
    }
    return s.p0;
}

double TempoMap::bpmAt(double beat) const noexcept {
    if (beat < 0.0) return segs_.front().p0;
    return segBpm(segAtBeat(beat), beat);
}

double TempoMap::sampleAt(double beat) const noexcept {
    const Seg& first = segs_.front();
    if (beat < 0.0 && first.kind != Kind::Const) return beat * (sr_ * 60.0 / first.p0);  // the first tempo before beat 0
    return segSample(segAtBeat(beat), beat);
}

double TempoMap::beatAtSample(double sample) const noexcept {
    const Seg& first = segs_.front();
    if (sample < 0.0 && first.kind != Kind::Const) return sample / (sr_ * 60.0 / first.p0);
    return segBeat(segAtSample(sample), sample);
}

double TempoMap::secondsAt(double beat) const noexcept {
    if (constant()) return beat * 60.0 / segs_.front().p0;  // the classic beat -> seconds of a constant tempo
    return sampleAt(beat) / sr_;
}

double TempoMap::beatAtSeconds(double seconds) const noexcept {
    if (constant()) return seconds * segs_.front().p0 / 60.0;
    return beatAtSample(seconds * sr_);
}

std::int64_t songStartSample(double startBeat, double sampleRate, double bpm, const TempoMap* map) noexcept {
    if (!map) return std::llround(std::max(0.0, startBeat) * (sampleRate * 60.0 / std::max(bpm, 1.0)));
    return std::llround(map->sampleAt(std::max(0.0, startBeat)));
}

// --------------------------------------------------------------------------------------------- BeatClock

void BeatClock::load(std::int64_t block) const noexcept {
    block_ = block;
    const double s0 = static_cast<double>(block) * 32.0;
    beat0_ = map_->beatAtSample(s0);
    beat1_ = map_->beatAtSample(s0 + 32.0);
    bpm_ = map_->bpmAt(beat0_);
    // A block with a kink (a "step" tempo change inside it) is not linear: evaluate it exactly per sample.
    exact_ = std::fabs(map_->beatAtSample(s0 + 16.0) - 0.5 * (beat0_ + beat1_)) > 1e-8;
}

double BeatClock::beatAt(std::int64_t sample) const noexcept {
    const std::int64_t block = sample >= 0 ? sample / 32 : -((-sample + 31) / 32);
    if (block != block_) load(block);
    if (exact_) return map_->beatAtSample(static_cast<double>(sample));
    return beat0_ + (beat1_ - beat0_) * (static_cast<double>(sample - block * 32) * (1.0 / 32.0));
}

double BeatClock::bpmAt(std::int64_t sample) const noexcept {
    const std::int64_t block = sample >= 0 ? sample / 32 : -((-sample + 31) / 32);
    if (block != block_) load(block);
    return bpm_;
}

// ---------------------------------------------------------------------------------------------- MeterMap

MeterMap::MeterMap() : MeterMap(std::vector<MeterPoint>{{0.0, 4, 4}}) {}

MeterMap::MeterMap(const std::vector<MeterPoint>& points) {
    if (points.empty()) throw std::invalid_argument("meter: needs at least one point");
    if (points.front().beat != 0.0) throw std::invalid_argument("meter: the first entry must be at beat 0");
    double bar0 = 0.0;
    for (std::size_t i = 0; i < points.size(); ++i) {
        const MeterPoint& p = points[i];
        const int d = p.denominator;
        if (p.numerator < 1 || p.numerator > 64) throw std::invalid_argument("meter: numerator must be 1..64, got " + std::to_string(p.numerator));
        if (d != 1 && d != 2 && d != 4 && d != 8 && d != 16 && d != 32) {
            throw std::invalid_argument("meter: denominator must be 1, 2, 4, 8, 16 or 32, got " + std::to_string(d));
        }
        if (!std::isfinite(p.beat)) throw std::invalid_argument("meter: beats must be finite");
        if (i > 0) {
            const Seg& prev = segs_.back();
            if (!(p.beat > prev.beat)) {
                throw std::invalid_argument("meter: beats must be strictly increasing (entry " + std::to_string(i) + " at beat " + num(p.beat) + ")");
            }
            const double bars = (p.beat - prev.beat) / prev.bpb;
            const double whole = std::round(bars);
            if (std::fabs(bars - whole) > 1e-6 * std::max(1.0, whole)) {
                const double lo = prev.beat + std::floor(bars) * prev.bpb;
                throw std::invalid_argument("meter: the change at beat " + num(p.beat) + " is not on a bar line of the " +
                                            std::to_string(points[i - 1].numerator) + "/" + std::to_string(points[i - 1].denominator) +
                                            " before it (bars start at beats " + num(lo) + " and " + num(lo + prev.bpb) + ")");
            }
            bar0 = prev.bar0 + whole;
        }
        segs_.push_back({p.beat, p.beatsPerBar(), bar0, i});
    }
    points_ = points;
}

double MeterMap::barAt(double beat) const noexcept {
    const auto it = std::upper_bound(segs_.begin(), segs_.end(), beat, [](double b, const Seg& s) { return b < s.beat; });
    const Seg& s = it == segs_.begin() ? segs_.front() : *(it - 1);
    return s.bar0 + (beat - s.beat) / s.bpb;
}

double MeterMap::barStart(double bar) const noexcept {
    const auto it = std::upper_bound(segs_.begin(), segs_.end(), bar, [](double b, const Seg& s) { return b < s.bar0; });
    const Seg& s = it == segs_.begin() ? segs_.front() : *(it - 1);
    return s.beat + (bar - s.bar0) * s.bpb;
}

double MeterMap::beatsPerBarAt(double beat) const noexcept { return meterAt(beat).beatsPerBar(); }

const MeterPoint& MeterMap::meterAt(double beat) const noexcept {
    const auto it = std::upper_bound(segs_.begin(), segs_.end(), beat, [](double b, const Seg& s) { return b < s.beat; });
    const Seg& s = it == segs_.begin() ? segs_.front() : *(it - 1);
    return points_[s.point];
}

std::string MeterMap::label(double beat) const {
    const double b = std::round(beat * 100.0) / 100.0;  // as displayed: 59.998 -> bar 16 beat 1.00
    const double bar = std::floor(barAt(b) + 1e-9);
    char buf[64];
    std::snprintf(buf, sizeof buf, "bar %d beat %.2f", static_cast<int>(bar) + 1, b - barStart(bar) + 1.0);
    return buf;
}

}  // namespace as
