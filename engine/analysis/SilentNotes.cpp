#include "analysis/SilentNotes.h"

#include "analysis/Loudness.h"
#include "analysis/MixImpl.h"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <map>
#include <set>
#include <string>
#include <utility>

namespace as::analysis {

namespace {

constexpr double kChordSec = 0.03;    // note starts closer than this are one event
constexpr double kTailSec = 0.25;     // after the note's end: its release, release-triggered samples
constexpr double kMaxSpanSec = 3.0;   // a slow attack speaks within this
constexpr double kMinSpanSec = 0.03;
constexpr double kEndGuardSec = 0.05; // notes starting this close to the end of the render are not judged
constexpr double kWinSec = 0.01;      // level windows
constexpr int kMaxTimes = 6;
constexpr double kNoAttackDb = 3.0;   // a silent note that rises less than this over the sound before it added nothing

std::string fmt(const char* f, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, f);
    std::vsnprintf(buf, sizeof buf, f, ap);
    va_end(ap);
    return buf;
}

double r1(double x) { return std::isfinite(x) ? std::round(x * 10.0) / 10.0 + 0.0 : kDbFloor; }

const char* gmName(int k) {
    static const char* names[] = {"kick2", "kick", "rim", "snare", "clap", "snare2", "tom_lo", "hat", "tom_floor_hi", "pedal_hat",
                                  "tom_mid", "open_hat", "tom_lowmid", "tom_hi", "crash", "tom_high", "ride", "china", "ride_bell",
                                  "tamb", "splash", "cowbell", "crash2", "vibraslap", "ride2", "bongo_hi", "bongo_lo", "conga_mute",
                                  "conga_hi", "conga_lo", "timbale_hi", "timbale_lo", "agogo_hi", "agogo_lo", "cabasa", "maracas",
                                  "whistle_short", "whistle_long", "guiro_short", "guiro_long", "claves", "block_hi", "block_lo",
                                  "cuica_mute", "cuica_open", "triangle_mute", "triangle", "shaker", "jingle", "belltree",
                                  "castanets", "surdo_mute", "surdo"};
    return k >= 35 && k <= 87 ? names[k - 35] : nullptr;
}

std::string noteName(int k) {
    static const char* pc[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    return std::string(pc[((k % 12) + 12) % 12]) + std::to_string(k / 12 - 1);
}

std::string keyLabel(int k, bool drum) {
    if (drum && gmName(k)) return fmt("%s (%d)", gmName(k), k);
    return fmt("%s (%d)", noteName(k).c_str(), k);
}

// A sampler whose zones are mostly unpitched one-shots (pitchKeytrack 0: inst.kit, SFZ drum kits).
bool drumZones(const json& params) {
    if (!params.is_object() || !params.contains("samples") || !params.at("samples").is_array()) return false;
    const json& z = params.at("samples");
    if (z.empty()) return false;
    std::size_t flat = 0;
    for (const json& e : z)
        if (e.is_object() && e.contains("pitchKeytrack") && e.at("pitchKeytrack").is_number() && e.at("pitchKeytrack").get<double>() == 0.0) ++flat;
    return 5 * flat >= 4 * z.size();
}

bool drumInstrument(const NodeRouting& r) {
    if (r.instrument == "drums") return true;
    if (r.instrument == "sampler") return drumZones(r.instrumentParams);
    if (r.instrument == "stack" && r.instrumentParams.is_object() && r.instrumentParams.contains("layers") &&
        r.instrumentParams.at("layers").is_array()) {
        for (const json& L : r.instrumentParams.at("layers")) {
            if (!L.is_object() || !L.contains("instrument") || !L.at("instrument").is_object()) continue;
            const json& in = L.at("instrument");
            const std::string t = in.contains("type") && in.at("type").is_string() ? in.at("type").get<std::string>() : "";
            if (t == "drums" || (t == "sampler" && in.contains("params") && drumZones(in.at("params")))) return true;
        }
    }
    return false;
}

double laneValue(const NodeRouting::Lane& lane, double beat) {
    const auto& p = lane.points;
    if (beat <= p.front().beat) return p.front().value;
    if (beat >= p.back().beat) return p.back().value;
    std::size_t i = 0;
    while (i + 2 < p.size() && p[i + 1].beat <= beat) ++i;
    const auto& a = p[i];
    const auto& b = p[i + 1];
    const double t = (beat - a.beat) / (b.beat - a.beat);
    switch (b.curve) {
        case 1: return a.value > 0.0 && b.value > 0.0 ? a.value * std::pow(b.value / a.value, t) : a.value + (b.value - a.value) * t;
        case 2: return a.value + (b.value - a.value) * (0.5 - 0.5 * std::cos(3.14159265358979323846 * t));
        case 3: return a.value;
        default: return a.value + (b.value - a.value) * t;
    }
}

bool contains(const std::string& s, const char* part) { return s.find(part) != std::string::npos; }
bool endsWith(const std::string& s, const char* tail) {
    const std::string t(tail);
    return s.size() >= t.size() && s.compare(s.size() - t.size(), t.size(), t) == 0;
}

// The lane that has closed the track's level at `beat` (see the header), else nullptr.
const NodeRouting::Lane* closedLane(const NodeRouting& r, double beat) {
    for (const auto& lane : r.lanes) {
        if (lane.points.size() < 2) continue;
        const std::string& t = lane.target;
        double lo = lane.points.front().value, hi = lo;
        for (const auto& p : lane.points) {
            lo = std::min(lo, p.value);
            hi = std::max(hi, p.value);
        }
        const double v = laneValue(lane, beat);
        bool closed = false;
        if (endsWith(t, "mute")) {
            closed = v >= 0.5;
        } else if (contains(t, "cutoff")) {
            closed = hi > 0.0 && v <= hi / 16.0 && v <= 300.0;
        } else if (t == "gainDb" || contains(t, "gain") || contains(t, "level") || contains(t, "output") || contains(t, "volume") ||
                   contains(t, "expression") || contains(t, "dynamics")) {
            if (lo < 0.0) closed = v <= hi - 30.0;             // a dB lane
            else closed = hi > 0.0 && v <= 0.1 * hi;           // an amplitude lane (0..1)
        }
        if (closed) return &lane;
    }
    return nullptr;
}

std::string barBeatShort(const MixImpl& m, double sec) {
    const double beat = std::round(m.beatAt(sec) * 10.0) / 10.0;
    const double bar = std::floor(m.meter.barAt(beat) + 1e-9);
    const double pos = beat - m.meter.barStart(bar) + 1.0;
    return fmt("%d:%g", static_cast<int>(bar) + 1, std::round(pos * 10.0) / 10.0);
}

std::string clock(double sec) {
    const int mnt = static_cast<int>(sec / 60.0);
    return fmt("%d:%04.1f", mnt, sec - 60.0 * mnt);
}

struct Event {
    double sec{0.0}, endSec{0.0}, beat{0.0};
    std::vector<std::size_t> notes;  // indices into routing.notes
    double levelDb{kDbFloor};
    double preDb{kDbFloor};  // just before it (10 ms ending 2 ms before the start)
    bool silent{false}, excused{false};
};

bool hasAttack(const Event& e) { return e.levelDb > -100.0 && e.levelDb - e.preDb >= kNoAttackDb; }

}  // namespace

double silentThresholdDb(double medianDb) noexcept {
    return std::max(medianDb - kSilentBelowMedianDb, std::min(kSilentAbsoluteDb, medianDb - kSilentQuietTrackDb));
}

double spanLevelDb(const OnsetEnvelope& env, double t0, double t1) {
    const auto& ms = env.meanSquare();
    const auto n = static_cast<std::ptrdiff_t>(ms.size());
    const double hop = env.hopSec();
    const auto win = std::max<std::ptrdiff_t>(1, static_cast<std::ptrdiff_t>(std::lround(kWinSec / hop)));
    const auto k0 = std::clamp(static_cast<std::ptrdiff_t>(std::floor(t0 / hop)), std::ptrdiff_t{0}, n);
    const auto k1 = std::clamp(static_cast<std::ptrdiff_t>(std::floor((t1 - kWinSec) / hop)), k0, n);
    if (k0 >= n) return kDbFloor;
    double sum = 0.0;  // running window sum
    std::ptrdiff_t e = std::min(n, k0 + win);
    for (std::ptrdiff_t k = k0; k < e; ++k) sum += ms[static_cast<std::size_t>(k)];
    double best = sum / static_cast<double>(e - k0);
    for (std::ptrdiff_t k = k0 + 1; k <= k1 && k < n; ++k) {
        sum -= ms[static_cast<std::size_t>(k - 1)];
        if (k + win - 1 < n) sum += ms[static_cast<std::size_t>(k + win - 1)];
        const double len = static_cast<double>(std::min(n, k + win) - k);
        best = std::max(best, sum / len);
    }
    return best > 0.0 ? dbFromPower(best) : kDbFloor;
}

std::vector<json> assessSilentNotes(MixImpl& m, std::vector<DynamicsFinding>& findings, std::vector<std::string>& suggestions) {
    std::vector<json> out(m.nodes.size());
    for (std::size_t i = 0; i < m.nodes.size(); ++i) {
        NodeData& n = m.nodes[i];
        if (n.isBus || !n.env || !n.hasRouting || n.routing.notes.empty()) continue;
        const NodeRouting& r = n.routing;
        const bool tones = r.tones.size() == r.notes.size();

        // 1. Events: the notes by start, chord notes (within 30 ms) as one.
        std::vector<std::pair<double, std::size_t>> order;
        for (std::size_t k = 0; k < r.notes.size(); ++k) {
            const double s = m.secAtBeat(r.notes[k].first);
            if (!(s >= 0.0) || s >= m.durationSec - kEndGuardSec || !(r.notes[k].second > 0.0)) continue;
            order.emplace_back(s, k);
        }
        std::stable_sort(order.begin(), order.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        std::vector<Event> ev;
        for (const auto& [s, k] : order) {
            const double e = m.secAtBeat(r.notes[k].first + r.notes[k].second);
            if (!ev.empty() && s - ev.back().sec < kChordSec) {
                ev.back().notes.push_back(k);
                ev.back().endSec = std::max(ev.back().endSec, e);
            } else {
                Event x;
                x.sec = s;
                x.endSec = std::max(e, s);
                x.beat = r.notes[k].first;
                x.notes.push_back(k);
                ev.push_back(std::move(x));
            }
        }
        if (ev.empty()) continue;

        // 2. Levels: the loudest 10 ms inside each event's own span.
        std::vector<double> levels;
        for (std::size_t e = 0; e < ev.size(); ++e) {
            double t1 = std::min(ev[e].endSec + kTailSec, ev[e].sec + kMaxSpanSec);
            if (e + 1 < ev.size()) t1 = std::min(t1, ev[e + 1].sec - 0.005);
            t1 = std::min(std::max(t1, ev[e].sec + kMinSpanSec), m.durationSec);
            ev[e].levelDb = spanLevelDb(*n.env, ev[e].sec, t1);
            if (ev[e].sec >= 0.012) ev[e].preDb = spanLevelDb(*n.env, ev[e].sec - 0.012, ev[e].sec - 0.002);
            levels.push_back(ev[e].levelDb);
        }
        std::vector<double> sorted = levels;
        std::sort(sorted.begin(), sorted.end());
        const double median = sorted[sorted.size() / 2];
        const double thr = silentThresholdDb(median);

        // 3. Silent events; excused while a level lane is closed, or on a keyed track (a vocoder carrier sounds only
        //    while its modulator speaks: a chord between the words is silent by design).
        bool keyed = false;
        for (const auto& f : r.fx) keyed = keyed || f.type == "vocoder";
        int silentNotes = 0, excusedNotes = 0;
        std::set<std::string> excusedBy;
        std::vector<std::size_t> silentEv;
        for (std::size_t e = 0; e < ev.size(); ++e) {
            // A note with an attack of its own (it rises over what sounded before) does sound: too quiet to be heard only
            // 40 dB under the track's median note. One that adds nothing: under the threshold.
            if (ev[e].levelDb >= (hasAttack(ev[e]) ? median - kSilentBelowMedianDb : thr)) continue;
            const double mid = m.beatAt(0.5 * (ev[e].sec + std::min(ev[e].endSec, ev[e].sec + kMaxSpanSec)));
            const NodeRouting::Lane* lane = closedLane(r, ev[e].beat);
            if (!lane) lane = closedLane(r, mid);
            if (lane || keyed) {
                ev[e].excused = true;
                excusedNotes += static_cast<int>(ev[e].notes.size());
                excusedBy.insert(lane ? lane->target : std::string("vocoder (its modulator was silent)"));
                continue;
            }
            ev[e].silent = true;
            silentNotes += static_cast<int>(ev[e].notes.size());
            silentEv.push_back(e);
        }

        // 4. What the compiler already explained (its pitches), and the rest.
        std::set<int> known;
        for (const auto& ks : r.knownSilent) known.insert(ks.pitches.begin(), ks.pitches.end());
        std::vector<std::size_t> unexplained;
        std::map<int, int> confirmed;  // pitch -> notes measured silent
        for (std::size_t e : silentEv) {
            bool all = tones;
            for (std::size_t k : ev[e].notes) all = all && known.count(r.tones[k].pitch);
            if (all) {
                for (std::size_t k : ev[e].notes) ++confirmed[r.tones[k].pitch];
            } else {
                unexplained.push_back(e);
            }
        }
        const bool drum = drumInstrument(r);
        for (const auto& ks : r.knownSilent) {
            int measured = 0;
            for (int p : ks.pitches) {
                const auto it = confirmed.find(p);
                if (it != confirmed.end()) measured += it->second;
            }
            std::string msg = ks.message;
            if (measured > 0)
                msg += ks.count == 1 ? std::string(" (the render measured it silent)")
                                     : fmt(" (the render measured %d of them silent%s)", measured,
                                           measured < ks.count ? "; the others sound together with other notes or are outside the render" : "");
            findings.push_back({1, "silent_notes", msg, {}, {n.id}});
        }

        json j;
        j["notes"] = static_cast<int>(order.size());
        j["events"] = static_cast<int>(ev.size());
        j["medianDb"] = r1(median);
        j["thresholdDb"] = r1(thr);
        j["silent"] = silentNotes;
        if (excusedNotes > 0) {
            j["excused"] = excusedNotes;
            j["excusedBy"] = json(std::vector<std::string>(excusedBy.begin(), excusedBy.end()));
        }
        if (!r.knownSilent.empty()) {
            int c = 0;
            for (const auto& ks : r.knownSilent) c += ks.count;
            j["compileSilent"] = c;
        }
        if (!silentEv.empty()) {
            json at = json::array();
            std::set<int> ps;
            for (std::size_t e : silentEv) {
                if (at.size() < 16) at.push_back(barBeatShort(m, ev[e].sec));
                if (tones)
                    for (std::size_t k : ev[e].notes) ps.insert(r.tones[k].pitch);
            }
            j["at"] = at;
            if (!ps.empty()) j["pitches"] = json(std::vector<int>(ps.begin(), ps.end()));
        }
        out[i] = j;

        // Two kinds: NOTHING (the note adds nothing to what was sounding just before it: no sample, a muted layer - warn)
        // and TOO QUIET (it has an attack of its own, far under the track's notes: info).
        for (int kind = 0; kind < 2; ++kind) {
            const bool nothing = kind == 0;
            std::vector<std::size_t> group;
            for (std::size_t e : unexplained)
                if (!hasAttack(ev[e]) == nothing) group.push_back(e);
            if (group.empty()) continue;
            int count = 0;
            std::map<int, int> byPitch;
            double loudest = kDbFloor;
            for (std::size_t e : group) {
                count += static_cast<int>(ev[e].notes.size());
                loudest = std::max(loudest, ev[e].levelDb);
                if (tones)
                    for (std::size_t k : ev[e].notes) ++byPitch[r.tones[k].pitch];
            }
            std::vector<std::pair<int, int>> pv(byPitch.begin(), byPitch.end());
            std::stable_sort(pv.begin(), pv.end(), [](const auto& a, const auto& b) { return a.second > b.second; });
            std::string what;
            if (pv.size() == 1) {
                what = fmt("%d note%s on %s", count, count == 1 ? "" : "s", keyLabel(pv[0].first, drum).c_str());
            } else {
                what = fmt("%d notes", count);
                if (!pv.empty()) {
                    what += " (";
                    for (std::size_t q = 0; q < pv.size() && q < 6; ++q)
                        what += fmt("%s%d on %s", q ? ", " : "", pv[q].second, keyLabel(pv[q].first, drum).c_str());
                    if (pv.size() > 6) what += fmt(" and %d more keys", static_cast<int>(pv.size() - 6));
                    what += ")";
                }
            }
            std::string times;
            for (std::size_t q = 0; q < group.size() && q < static_cast<std::size_t>(kMaxTimes); ++q)
                times += (q ? ", " : "") + barBeatShort(m, ev[group[q]].sec);
            if (group.size() > static_cast<std::size_t>(kMaxTimes)) times += fmt(" (+%d more)", static_cast<int>(group.size() - kMaxTimes));
            const std::string level =
                nothing ? fmt("nothing above what was already sounding: at most %.1f dBFS in the notes' own spans; the track's notes "
                              "median %.1f dBFS", loudest, median)
                        : fmt("at most %.1f dBFS in the notes' own spans, %.0f dB under the track's median note (%.1f dBFS; threshold "
                              "%.1f)", loudest, median - loudest, median, thr);
            const std::string check =
                nothing ? "Check what reaches them: the instrument's key / velocity range (sampler zones, SoundFont key ranges, "
                          "stack layer keylo / keyhi / vello / velhi, a muted layer), a gate or automation closing the track there."
                        : "Raise them (velocity, the piece's level in the kit: inst.kit(..., gains={...}), a softer velocity curve) or "
                          "leave them out; also check a velocity / expression that nearly silences the sound, a gate or ducking "
                          "there.";
            const char* verb = nothing ? "made no sound" : count == 1 ? "was too quiet to be heard" : "were too quiet to be heard";
            findings.push_back({nothing ? 1 : 2, "silent_notes",
                                fmt("'%s': %s %s in the render at %s (%s). %s", n.id.c_str(), what.c_str(), verb, times.c_str(),
                                    level.c_str(), check.c_str()),
                                {}, {n.id}});
            if (nothing)
                suggestions.push_back(fmt("'%s' has %d silent note%s (first at %s, %s): zoom in with python -m agentsound zoom "
                                          "songs/<slug> --at %s --stem %s, then move them into the instrument's range or fix what "
                                          "silences them.",
                                          n.id.c_str(), count, count == 1 ? "" : "s", barBeatShort(m, ev[group[0]].sec).c_str(),
                                          clock(ev[group[0]].sec).c_str(), clock(ev[group[0]].sec).c_str(), n.id.c_str()));
        }
    }
    return out;
}

}  // namespace as::analysis
