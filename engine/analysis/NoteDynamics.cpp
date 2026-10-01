#include "analysis/NoteDynamics.h"

#include "analysis/Loudness.h"
#include "analysis/MixImpl.h"
#include "analysis/Profiles.h"
#include "analysis/Space.h"
#include "render/Registry.h"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <map>
#include <memory>
#include <string>
#include <utility>

namespace as::analysis {

// ------------------------------------------------------------------ envelope

OnsetEnvelope::OnsetEnvelope(double sampleRate, double secondsHint) {
    hop_ = std::max(1, static_cast<int>(std::lround(sampleRate * 0.0025)));
    hopSec_ = hop_ / sampleRate;
    if (secondsHint > 0.0) ms_.reserve(static_cast<std::size_t>(secondsHint / hopSec_) + 16);
}

void OnsetEnvelope::feed(const float* left, const float* right, int frames) {
    for (int i = 0; i < frames; ++i) {
        double l = left[i], r = right[i];
        if (!std::isfinite(l)) l = 0.0;
        if (!std::isfinite(r)) r = 0.0;
        acc_ += 0.5 * (l * l + r * r);
        if (++n_ == hop_) {
            ms_.push_back(static_cast<float>(acc_ / hop_));
            acc_ = 0.0;
            n_ = 0;
        }
    }
}

void OnsetEnvelope::finalize() {
    if (n_ > 0) ms_.push_back(static_cast<float>(acc_ / n_));
    acc_ = 0.0;
    n_ = 0;
}

namespace {

constexpr int kWinHops = 4;  // 10 ms level windows

// Mean square of the 10 ms window starting at hop k (shorter at the end), -1 past the end.
double windowMs(const std::vector<float>& ms, std::ptrdiff_t k) {
    const auto n = static_cast<std::ptrdiff_t>(ms.size());
    if (k < 0 || k >= n) return -1.0;
    const std::ptrdiff_t e = std::min(n, k + kWinHops);
    double s = 0.0;
    for (std::ptrdiff_t i = k; i < e; ++i) s += ms[static_cast<std::size_t>(i)];
    return s / static_cast<double>(e - k);
}

}  // namespace

double onsetLevelDb(const OnsetEnvelope& env, double sec, double nextSec, double* attackDb) {
    const double win = nextSec > sec ? std::clamp(nextSec - sec - 0.005, 0.03, 0.1) : 0.1;
    const auto& ms = env.meanSquare();
    const auto n = static_cast<std::ptrdiff_t>(ms.size());
    auto mean = [&](double t0, double t1) {
        const auto k0 = std::clamp(static_cast<std::ptrdiff_t>(std::floor(t0 / env.hopSec())), std::ptrdiff_t{0}, n);
        const auto k1 = std::clamp(static_cast<std::ptrdiff_t>(std::ceil(t1 / env.hopSec())), k0, n);
        double e = 0.0;
        for (std::ptrdiff_t k = k0; k < k1; ++k) e += ms[static_cast<std::size_t>(k)];
        return k1 > k0 ? e / static_cast<double>(k1 - k0) : 0.0;
    };
    const double e = mean(std::max(0.0, sec), sec + win);
    if (attackDb) {
        const double pre = sec >= 0.012 ? mean(sec - 0.012, sec - 0.002) : 0.0;
        *attackDb = e > 0.0 && e - pre >= 0.25 * e ? dbFromPower(e - pre) : kDbFloor;
    }
    return e > 0.0 ? dbFromPower(e) : kDbFloor;
}

std::vector<double> detectOnsets(const OnsetEnvelope& env) {
    const auto& ms = env.meanSquare();
    const auto n = static_cast<std::ptrdiff_t>(ms.size());
    std::vector<double> lv(ms.size(), kDbFloor);
    double mx = kDbFloor;
    for (std::ptrdiff_t k = 0; k < n; ++k) {
        const double w = windowMs(ms, k);
        lv[static_cast<std::size_t>(k)] = w > 0.0 ? dbFromPower(w) : kDbFloor;
        mx = std::max(mx, lv[static_cast<std::size_t>(k)]);
    }
    std::vector<double> out;
    if (mx <= -70.0) return out;
    const double thr = std::max(-70.0, mx - 45.0);
    auto rise = [&](std::ptrdiff_t k) {  // (before the first sample: silence, so a note at 0:00 counts)
        if (k < 0 || k >= n) return 0.0;
        return lv[static_cast<std::size_t>(k)] - (k >= kWinHops ? lv[static_cast<std::size_t>(k - kWinHops)] : kDbFloor);
    };
    const auto refractory = static_cast<std::ptrdiff_t>(std::ceil(0.05 / env.hopSec()));
    std::ptrdiff_t last = -refractory - 1;
    for (std::ptrdiff_t k = 0; k < n; ++k) {
        const double d = rise(k);
        if (d < 6.0 || lv[static_cast<std::size_t>(k)] < thr || k - last < refractory) continue;
        bool peak = true;
        for (std::ptrdiff_t j = 1; j <= kWinHops && peak; ++j) peak = d >= rise(k - j) && d > rise(k + j);
        if (!peak) continue;
        out.push_back(static_cast<double>(std::max<std::ptrdiff_t>(0, k - kWinHops / 2)) * env.hopSec());
        last = k;
    }
    return out;
}

double percentileSpread(std::vector<double> v, double* p10, double* p90) {
    if (v.empty()) {
        if (p10) *p10 = kDbFloor;
        if (p90) *p90 = kDbFloor;
        return 0.0;
    }
    std::sort(v.begin(), v.end());
    auto q = [&](double f) {
        const double x = f * static_cast<double>(v.size() - 1);
        const auto i = static_cast<std::size_t>(std::floor(x));
        const std::size_t j = std::min(v.size() - 1, i + 1);
        return v[i] + (v[j] - v[i]) * (x - static_cast<double>(i));
    };
    const double a = q(0.1), b = q(0.9);
    if (p10) *p10 = a;
    if (p90) *p90 = b;
    return b - a;
}

// ------------------------------------------------------------------ assessment

namespace {

constexpr int kMinNotes = 8;            // notes a phrase needs to be judged
constexpr double kPhraseBars = 8.0;     // phrase length the sections are cut into
constexpr double kChordSec = 0.03;      // note starts closer than this are one event (a chord, a flam)
constexpr double kSilentDb = -70.0;     // onsets quieter than this did not sound (muted, automated away)

std::string fmt(const char* f, ...) {
    char buf[2048];
    va_list ap;
    va_start(ap, f);
    std::vsnprintf(buf, sizeof buf, f, ap);
    va_end(ap);
    return buf;
}

double r1(double x) { return std::isfinite(x) ? std::round(x * 10.0) / 10.0 + 0.0 : kDbFloor; }

struct Event {
    double sec{0.0}, beat{0.0};
    int velocity{0};  // 0 = unknown (audio onsets)
    int pitch{-1};
    int notes{1};
    double durBeats{0.0};  // longest note of the event (0 = unknown: audio onsets)
    double levelDb{kDbFloor};
    double attackDb{kDbFloor};  // what the note adds over the sound before it (kDbFloor: no clear attack)
    int section{-1};
};

// Parts whose idiom is an even pulse: never judged, whatever their velocities.
bool evenName(const std::string& id) { return idNamed(id, {"arp", "seq", "ostinato"}, {"arpegg", "sequence"}); }
// Melody instruments the space roles do not name as leads.
bool melodyInstrumentName(const std::string& id) {
    return idNamed(id, {"sax", "trumpet", "trp", "flute", "violin", "clarinet", "oboe", "whistle", "harmonica", "trombone", "horn",
                        "cornet", "flugel", "recorder", "piccolo", "soprano", "alto", "tenor", "solo"},
                   {"sax", "trumpet", "flute", "violin", "clarinet"});
}
bool leadIntentName(const std::string& id) {
    return idNamed(id, {"lead", "hook", "melody", "melo", "solo", "topline", "theme", "vocal", "voice", "vox"},
                   {"lead", "hook", "melody", "topline"}) ||
           melodyInstrumentName(id);
}

// Notes on a fixed fast grid: 8ths / 16ths (also swung: the pairs are even), >= 70 % of the steps; or a fast
// figure of short notes (85 %+ of the steps 8ths or faster, median note <= 0.3 beats: an arpeggio with rests).
bool pulsePart(const std::vector<Event>& ev) {
    if (ev.size() < 16) return false;
    auto modeShare = [](const std::vector<double>& d, double maxStep) {
        std::map<long, int> hist;
        for (double x : d) ++hist[std::lround(x * 48.0)];
        long best = 0;
        int cnt = 0;
        for (const auto& [k, c] : hist)
            if (c > cnt) { best = k; cnt = c; }
        const double mode = best / 48.0;
        if (mode <= 0.0 || mode > maxStep + 1e-9) return 0.0;
        int near = 0;
        for (double x : d) near += std::fabs(x - mode) <= 0.04;
        return static_cast<double>(near) / static_cast<double>(d.size());
    };
    std::vector<double> ioi, pairs;
    for (std::size_t i = 1; i < ev.size(); ++i) ioi.push_back(ev[i].beat - ev[i - 1].beat);
    for (std::size_t i = 1; i < ioi.size(); i += 2) pairs.push_back(ioi[i] + ioi[i - 1]);
    if (modeShare(ioi, 0.5) >= 0.7 || (pairs.size() >= 8 && modeShare(pairs, 1.0) >= 0.7)) return true;
    std::vector<double> dur;
    for (const Event& e : ev)
        if (e.durBeats > 0.0) dur.push_back(e.durBeats);
    if (dur.size() != ev.size()) return false;
    std::nth_element(dur.begin(), dur.begin() + static_cast<std::ptrdiff_t>(dur.size() / 2), dur.end());
    int fast = 0;
    for (double x : ioi) fast += x <= 0.54;
    return 100 * fast >= 85 * static_cast<int>(ioi.size()) && dur[dur.size() / 2] <= 0.3;
}

// The instrument parameter that maps velocity to level, its value (as set or the default) and a value that
// lets played velocities through. Empty name for unknown instruments.
struct VelParam {
    std::string name;
    double value{0.0}, good{0.0};
};
VelParam velocityParam(const std::string& t, const json& ip) {
    VelParam p;
    if (t == "va") p = {"amp.velocity", 0.5, 0.7};
    else if (t == "dx7" || t == "sf2" || t == "sampler") p = {"velsens", 1.0, 0.8};
    else return p;
    try {  // the default from the instrument's own ParamSpec (the numbers above are the fallback)
        const auto inst = createInstrument(t);
        for (const ParamSpec& s : inst->paramSpecs())
            if (s.name == p.name) p.value = s.def;
    } catch (...) {
    }
    if (ip.is_object()) {
        const auto it = ip.find(p.name);
        if (it != ip.end() && it->is_number()) p.value = it->get<double>();
    }
    return p;
}
VelParam velocityParam(const NodeData& n) {
    const json& ip = n.routing.instrumentParams;
    if (n.routing.instrument != "stack") return velocityParam(n.routing.instrument, ip);
    // a layered stack: its first layer (the main sound by convention: the piano under the glass, the sax over the
    // synth) and its velocity param as addressed on the stack, 'layers.<id>.<param>' (a flat override wins)
    VelParam p;
    if (!ip.is_object() || !ip.contains("layers") || !ip.at("layers").is_array() || ip.at("layers").empty()) return p;
    const json& L = ip.at("layers")[0];
    if (!L.is_object() || !L.contains("instrument") || !L.at("instrument").is_object()) return p;
    const json& inst = L.at("instrument");
    const std::string type = inst.contains("type") && inst.at("type").is_string() ? inst.at("type").get<std::string>() : "";
    const std::string id = L.contains("id") && L.at("id").is_string() ? L.at("id").get<std::string>() : "0";
    p = velocityParam(type, inst.contains("params") ? inst.at("params") : json::object());
    if (p.name.empty()) return p;
    p.name = "layers." + id + "." + p.name;
    const auto it = ip.find(p.name);
    if (it != ip.end() && it->is_number()) p.value = it->get<double>();
    return p;
}

// Compressors / limiters in the track's insert chain ("compressor (ratio 4)").
std::string squashers(const NodeData& n) {
    std::string s;
    for (const auto& f : n.routing.fx) {
        if (f.type != "compressor" && f.type != "limiter") continue;
        std::string one = f.type;
        if (f.params.is_object()) {
            const auto it = f.params.find("ratio");
            if (it != f.params.end() && it->is_number()) one += fmt(" (ratio %g)", it->get<double>());
        }
        s += (s.empty() ? "" : ", ") + one;
    }
    return s;
}

}  // namespace

std::vector<json> assessDynamics(MixImpl& m, std::vector<DynamicsFinding>& findings, std::vector<std::string>& suggestions) {
    const std::size_t nn = m.nodes.size(), ns = m.sections.size();
    const double thr = m.profile->noteSpreadMinDb;
    std::vector<json> out(nn);
    std::vector<std::vector<Event>> evs(nn);
    std::vector<bool> fromNotes(nn, false);

    // 1. Onsets and their levels.
    for (std::size_t i = 0; i < nn; ++i) {
        NodeData& n = m.nodes[i];
        n.dynamics = {};
        if (n.isBus || !n.env || n.role == Role::Drums || n.role == Role::Fx) continue;
        std::vector<Event> ev;
        const auto& notes = n.routing.notes;
        if (n.hasRouting && !notes.empty()) {
            fromNotes[i] = true;
            const bool tones = n.routing.tones.size() == notes.size();
            std::vector<Event> raw;
            raw.reserve(notes.size());
            for (std::size_t k = 0; k < notes.size(); ++k) {
                Event e;
                e.beat = notes[k].first;
                e.durBeats = notes[k].second;
                e.sec = m.secAtBeat(e.beat);
                if (!(e.sec >= 0.0) || e.sec >= m.durationSec || !(notes[k].second > 0.0)) continue;
                if (tones) {
                    e.velocity = n.routing.tones[k].velocity;
                    e.pitch = n.routing.tones[k].pitch;
                }
                raw.push_back(e);
            }
            std::stable_sort(raw.begin(), raw.end(), [](const Event& a, const Event& b) { return a.sec < b.sec; });
            for (const Event& e : raw) {
                if (!ev.empty() && e.sec - ev.back().sec < kChordSec) {
                    Event& g = ev.back();
                    g.velocity = std::max(g.velocity, e.velocity);
                    g.pitch = std::max(g.pitch, e.pitch);
                    g.durBeats = std::max(g.durBeats, e.durBeats);
                    ++g.notes;
                } else {
                    ev.push_back(e);
                }
            }
        } else {
            for (double sec : detectOnsets(*n.env)) {
                Event e;
                e.sec = sec;
                e.beat = m.beatAt(sec);
                ev.push_back(e);
            }
        }
        std::vector<Event> kept;
        for (std::size_t k = 0; k < ev.size(); ++k) {
            ev[k].levelDb = onsetLevelDb(*n.env, ev[k].sec, k + 1 < ev.size() ? ev[k + 1].sec : -1.0, &ev[k].attackDb);
            if (ev[k].levelDb < kSilentDb) continue;
            for (std::size_t s = 0; s < ns; ++s)
                if (ev[k].sec >= m.sections[s].startSec && ev[k].sec < m.sections[s].endSec) ev[k].section = static_cast<int>(s);
            kept.push_back(ev[k]);
        }
        evs[i] = std::move(kept);
    }

    // 2. What each part is. Ids first (the composer's intent), then the rhythm, then the space roles.
    std::vector<std::string> kind(nn), reason(nn);
    std::vector<int> pitchMedian(nn, -1);
    for (std::size_t i = 0; i < nn; ++i) {
        const NodeData& n = m.nodes[i];
        if (evs[i].size() < 2) continue;
        std::vector<int> p;
        for (const Event& e : evs[i])
            if (e.pitch >= 0) p.push_back(e.pitch);
        if (!p.empty()) {
            std::nth_element(p.begin(), p.begin() + static_cast<std::ptrdiff_t>(p.size() / 2), p.end());
            pitchMedian[i] = p[p.size() / 2];
        }
        const bool leadNamed = leadIntentName(n.id);
        auto set = [&](const char* k, const char* why) {
            kind[i] = k;
            reason[i] = why;
        };
        if (evenName(n.id)) set("even", "arp / sequence id: even by design");
        else if (!leadNamed && pulsePart(evs[i])) set("even", "8th/16th pulse or arpeggio figure");
        else if (n.role == Role::Bass) set("bass", "role bass");
        else if (n.role == Role::Bed && !leadNamed) set("bed", "role bed (sustained notes)");
        else if (n.role == Role::Lead) set("lead", "role lead");
        else if (leadNamed) set("lead", "melody id");
        else set("melodic", "melodic part");
    }
    // Sections without a lead: the loudest melodic part there leads it. A melodic part (not a low line)
    // that leads at least half of the sections it plays in is judged as a lead.
    auto plays = [&](std::size_t i, std::size_t s) {
        int c = 0;
        for (const Event& e : evs[i]) c += e.section == static_cast<int>(s);
        return c >= 2 && s < m.nodes[i].sectionRmsDb.size() && m.nodes[i].sectionRmsDb[s] > -60.0;
    };
    std::vector<int> led(nn, 0), active(nn, 0);
    for (std::size_t s = 0; s < ns; ++s) {
        bool leadPlays = false;
        for (std::size_t i = 0; i < nn; ++i) leadPlays = leadPlays || (kind[i] == "lead" && plays(i, s));
        int best = -1;
        for (std::size_t i = 0; i < nn; ++i) {
            if (kind[i] != "melodic" || !plays(i, s)) continue;
            ++active[i];
            if (leadPlays) continue;
            if (best < 0 || m.nodes[i].sectionRmsDb[s] > m.nodes[static_cast<std::size_t>(best)].sectionRmsDb[s]) best = static_cast<int>(i);
        }
        if (best >= 0) ++led[static_cast<std::size_t>(best)];
    }
    for (std::size_t i = 0; i < nn; ++i)
        if (kind[i] == "melodic" && active[i] > 0 && 2 * led[i] >= active[i] && (pitchMedian[i] < 0 || pitchMedian[i] >= 52)) {
            kind[i] = "lead";
            reason[i] = fmt("leads %d of its %d sections in level", led[i], active[i]);
        }

    // 3. Per phrase (the sections cut into ~8-bar chunks, 6-12 bars): the spread of the note levels (audio) and
    //    the part of it the velocities explain; overall and per section; the verdict.
    for (std::size_t i = 0; i < nn; ++i) {
        NodeData& n = m.nodes[i];
        const auto& ev = evs[i];
        if (ev.size() < 2) continue;
        std::vector<double> lv;
        for (const Event& e : ev) lv.push_back(e.levelDb);
        double p10 = 0, p90 = 0;
        const double spread = percentileSpread(lv, &p10, &p90);

        json secs = json::array();
        struct Chunk {
            int section{-1};
            std::vector<std::size_t> idx;  // events
        };
        std::vector<Chunk> chunks;
        for (std::size_t s = 0; s < ns; ++s) {
            std::vector<double> sl;
            for (const Event& e : ev)
                if (e.section == static_cast<int>(s)) sl.push_back(e.levelDb);
            if (sl.size() >= 2) secs.push_back({{"section", m.sections[s].name}, {"notes", sl.size()}, {"spreadDb", r1(percentileSpread(sl))}});
            const double b0 = m.barAt(m.beatAt(m.sections[s].startSec)), b1 = m.barAt(m.beatAt(m.sections[s].endSec));
            if (!(b1 > b0)) continue;
            const int count = std::max(1, static_cast<int>(std::lround((b1 - b0) / kPhraseBars)));
            const double len = (b1 - b0) / count;
            for (int c = 0; c < count; ++c) {
                Chunk ch;
                ch.section = static_cast<int>(s);
                const double c0 = b0 + c * len, c1 = c + 1 == count ? b1 + 1e-6 : b0 + (c + 1) * len;
                for (std::size_t k = 0; k < ev.size(); ++k) {
                    if (ev[k].section != static_cast<int>(s)) continue;
                    const double bar = m.barAt(ev[k].beat);
                    if (bar >= c0 - 1e-6 && bar < c1) ch.idx.push_back(k);
                }
                if (ch.idx.size() >= 2) chunks.push_back(std::move(ch));
            }
        }

        // Velocity response of the sound: the slope of the note level over velocity inside the phrases (phrase means
        // removed, so section gain moves do not count; the register taken out with the pitch). The level is what each
        // note adds over the sound before it (attackDb: pedalled / ringing notes would flatten the slope) when enough
        // notes have a clear attack, else the plain note level. Conservative: the slope minus one standard error (a few
        // narrow velocities give no confident response), clamped to 0 .. 1.25 x the (v/127)^2 curve's slope at the
        // median velocity.
        std::vector<int> vel;
        int chords = 0;
        for (const Event& e : ev) {
            if (e.velocity > 0) vel.push_back(e.velocity);
            chords += e.notes > 1;
        }
        const bool velKnown = vel.size() == ev.size() && static_cast<int>(vel.size()) >= kMinNotes;
        bool automated = false;  // expression / dynamics moved by automation or a modulator: dynamics without velocity
        // ... or a gain stage in the insert chain moved by automation: a wind player's breath written after the
        // compressor (agentsound.hornist: the 'air' / 'mic' stage, 'fx.<i>.gain' / 'fx.<i>.output')
        auto gainStage = [](const std::string& t) {
            if (t.rfind("fx.", 0) != 0) return false;
            const auto dot = t.find('.', 3);
            if (dot == std::string::npos || dot == 3) return false;
            for (std::size_t c = 3; c < dot; ++c)
                if (t[c] < '0' || t[c] > '9') return false;
            const std::string p = t.substr(dot + 1);
            return p == "output" || p == "gain";
        };
        for (const std::string& t : n.routing.automated)
            automated = automated || gainStage(t) ||
                        (t.rfind("instrument.", 0) == 0 &&
                         (t.find("expression") != std::string::npos || t.find("dynamics") != std::string::npos));
        double slope = 0.0;  // dB per velocity step
        if (velKnown) {
            int attacks = 0;
            for (const Event& e : ev) attacks += e.attackDb > kDbFloor;
            const bool useAttack = attacks >= kMinNotes && 10 * attacks >= 3 * static_cast<int>(ev.size());
            auto level = [&](std::size_t k) { return useAttack ? ev[k].attackDb : ev[k].levelDb; };
            auto used = [&](std::size_t k) { return !useAttack || ev[k].attackDb > kDbFloor; };
            double svv = 0, svp = 0, spp = 0, slv = 0, slp = 0, sll = 0;
            int nUsed = 0, groups = 0;
            for (const Chunk& ch : chunks) {
                double mv = 0, mp = 0, ml = 0;
                int c = 0;
                for (std::size_t k : ch.idx) {
                    if (!used(k)) continue;
                    mv += ev[k].velocity;
                    mp += std::max(0, ev[k].pitch);
                    ml += level(k);
                    ++c;
                }
                if (c < 2) continue;
                mv /= c;
                mp /= c;
                ml /= c;
                nUsed += c;
                ++groups;
                for (std::size_t k : ch.idx) {
                    if (!used(k)) continue;
                    const double v = ev[k].velocity - mv, p = std::max(0, ev[k].pitch) - mp, l = level(k) - ml;
                    svv += v * v;
                    svp += v * p;
                    spp += p * p;
                    slv += l * v;
                    slp += l * p;
                    sll += l * l;
                }
            }
            const double det = svv * spp - svp * svp;
            const bool withPitch = det > 1e-6 * svv * std::max(spp, 1e-9);
            if (svv > 1e-9) {
                const double b = withPitch ? (slp * svv - slv * svp) / det : 0.0;
                slope = withPitch ? (slv * spp - slp * svp) / det : slv / svv;
                // residual variance -> standard error of the slope
                const double rss = std::max(0.0, sll - slope * slv - b * slp);
                const int dof = nUsed - groups - (withPitch ? 2 : 1);
                const double s2 = dof > 0 ? rss / dof : 0.0;
                const double se = std::sqrt(s2 * (withPitch ? spp / det : 1.0 / svv));
                slope -= se;
            }
            std::vector<int> vs = vel;
            std::nth_element(vs.begin(), vs.begin() + static_cast<std::ptrdiff_t>(vs.size() / 2), vs.end());
            const double vMed = std::max(20, vs[vs.size() / 2]);
            slope = std::clamp(slope, 0.0, 1.25 * 40.0 / (std::log(10.0) * vMed));
        }

        struct Phrase {
            int section;
            int notes;
            double audioDb, velDb, playedDb;
        };
        std::vector<Phrase> phrases;
        auto measure = [&](const std::vector<std::size_t>& idx, int section) {
            std::vector<double> pl, pv;
            for (std::size_t k : idx) {
                pl.push_back(ev[k].levelDb);
                pv.push_back(ev[k].velocity);
            }
            Phrase p{section, static_cast<int>(idx.size()), percentileSpread(pl), 0.0, 0.0};
            p.velDb = velKnown ? slope * percentileSpread(pv) : 0.0;
            p.playedDb = velKnown && !automated ? std::min(p.audioDb, p.velDb) : p.audioDb;
            return p;
        };
        for (const Chunk& ch : chunks)
            if (static_cast<int>(ch.idx.size()) >= kMinNotes) phrases.push_back(measure(ch.idx, ch.section));
        if (phrases.empty() && static_cast<int>(ev.size()) >= kMinNotes) {  // sparse: the song as one phrase
            std::vector<std::size_t> all(ev.size());
            for (std::size_t k = 0; k < ev.size(); ++k) all[k] = k;
            phrases.push_back(measure(all, -1));
        }
        auto median = [](std::vector<double> v) {
            if (v.empty()) return 0.0;
            std::sort(v.begin(), v.end());
            const std::size_t h = v.size() / 2;
            return v.size() % 2 ? v[h] : 0.5 * (v[h - 1] + v[h]);
        };
        std::vector<double> pa, pv, pp;
        int flatCount = 0;
        std::vector<std::string> flatSecs;
        for (const Phrase& p : phrases) {
            pa.push_back(p.audioDb);
            pv.push_back(p.velDb);
            pp.push_back(p.playedDb);
            if (p.playedDb < thr) {
                ++flatCount;
                if (p.section >= 0) {
                    const std::string& nm = m.sections[static_cast<std::size_t>(p.section)].name;
                    if (std::find(flatSecs.begin(), flatSecs.end(), nm) == flatSecs.end()) flatSecs.push_back(nm);
                }
            }
        }
        const double audioDb = median(pa), velDb = median(pv), playedDb = median(pp);
        const bool judged = kind[i] == "lead" || kind[i] == "melodic" || (kind[i] == "bass" && m.profile->judgeBassDynamics);
        const bool flat = judged && !phrases.empty() && playedDb < thr;
        // The velocities limit the played dynamics while the audio alone would pass (a wobbling sound).
        const bool byVelocity = velKnown && !automated && velDb < audioDb && audioDb >= thr;

        json j;
        j["kind"] = kind[i];
        j["why"] = reason[i];
        j["onsets"] = fromNotes[i] ? "notes" : "audio";
        j["notes"] = ev.size();
        j["spreadDb"] = r1(spread);
        j["levelDb"] = {r1(p10), r1(p90)};
        if (!phrases.empty()) {
            j["dynamicsDb"] = r1(playedDb);
            j["phraseSpreadDb"] = r1(audioDb);
            j["phrases"] = static_cast<int>(phrases.size());
            j["flatPhrases"] = flatCount;
        }
        double v10 = 0, v90 = 0;
        if (!vel.empty()) {
            std::vector<double> vd(vel.begin(), vel.end());
            percentileSpread(vd, &v10, &v90);
            j["velocity"] = {{"min", *std::min_element(vel.begin(), vel.end())}, {"max", *std::max_element(vel.begin(), vel.end())},
                             {"p10", std::lround(v10)}, {"p90", std::lround(v90)}};
        }
        if (velKnown) {
            j["velocityDbPer10"] = r1(10.0 * slope);
            if (!phrases.empty()) j["velocityPhraseDb"] = r1(velDb);
        }
        if (automated) j["automatedDynamics"] = true;
        if (fromNotes[i]) j["chordPct"] = r1(100.0 * chords / static_cast<double>(ev.size()));
        j["thresholdDb"] = thr;
        j["judged"] = judged;
        j["flat"] = flat;
        j["sections"] = secs;
        out[i] = j;

        NoteDynamicsResult& R = n.dynamics;
        R.measured = true;
        R.kind = kind[i];
        R.events = static_cast<int>(ev.size());
        R.spreadDb = spread;
        R.dynamicsDb = phrases.empty() ? spread : playedDb;

        // Findings.
        if (!judged || phrases.empty()) continue;
        const bool lead = kind[i] == "lead";
        const std::string label = lead ? "lead" : kind[i] == "bass" ? "bass line" : "melodic part";
        std::string velText;
        std::vector<std::string> causes;
        const VelParam vp = velocityParam(n);
        const std::string comp = squashers(n);
        if (!vel.empty()) {
            const int vmin = *std::min_element(vel.begin(), vel.end()), vmax = *std::max_element(vel.begin(), vel.end());
            velText = fmt("velocities %d-%d (10-90 %%: %ld-%ld)", vmin, vmax, std::lround(v10), std::lround(v90));
            if (v90 - v10 < 25.0) causes.push_back("the velocities barely move");
        }
        if (!vp.name.empty() && vp.value < vp.good) causes.push_back(fmt("%s %.2f shrinks what they do", vp.name.c_str(), vp.value));
        if (!comp.empty()) causes.push_back(comp + " on the track squeezes the notes together");
        if (causes.empty())
            causes.push_back(vel.empty() ? "the part is played / sampled at one level"
                                         : "the velocities move but the sound levels them (velocity layers without level, legato "
                                           "notes without a new attack, a bus compressor)");
        std::string cause;
        for (const auto& c : causes) cause += (cause.empty() ? "" : "; ") + c;
        std::string fix = "velocity arcs over each phrase (55-118: accents on the phrase peaks and strong beats, softer passing "
                          "and repeated notes, octave doubles softer than the line)";
        if (!vp.name.empty() && vp.value < vp.good)
            fix += fmt(", %s %.2f -> %.1f+ so the velocities reach the level", vp.name.c_str(), vp.value, vp.good);
        else if (!vp.name.empty())
            fix += fmt(" (%s %.2f passes them)", vp.name.c_str(), vp.value);
        if (!comp.empty()) fix += ", a gentler " + comp + " (lower ratio, slower attack) or none before the level differences";
        const int np = static_cast<int>(phrases.size());
        if (flat) {
            std::string what;
            if (byVelocity)
                what = fmt("has no played dynamics: its velocities move the note level only ~%.1f dB per phrase (median of %d, %d under "
                           "%.1f dB; measured response %.1f dB per 10 velocity steps; %zu notes, %s) - the %.1f dB the note levels do "
                           "vary comes from the sound itself (modulation, chorus, register, samples), not from accents",
                           velDb, np, flatCount, thr, 10.0 * slope, ev.size(), velText.c_str(), audioDb);
            else
                what = fmt("plays every note at nearly the same level: the note levels move only %.1f dB per phrase (10-90 %%, median "
                           "of %d, %d under %.1f dB; %zu notes, whole song %.1f dB%s%s%s)",
                           audioDb, np, flatCount, thr, ev.size(), spread, velText.empty() ? "" : ", ", velText.c_str(),
                           velKnown ? fmt("; the velocities account for ~%.1f dB", velDb).c_str() : "");
            findings.push_back({lead ? 1 : 2, "flat_dynamics",
                                fmt("'%s' (%s: %s) %s. Cause: %s. Robotic - fix: %s.", n.id.c_str(), label.c_str(), reason[i].c_str(),
                                    what.c_str(), cause.c_str(), fix.c_str()),
                                flatSecs, {n.id}});
            R.severity = lead ? 1 : 2;
            R.mark = fmt("FLAT %.1f dB", playedDb);
            if (lead)
                suggestions.push_back(fmt("'%s' is a lead with flat note dynamics (%.1f dB per phrase, want >= %.1f): %s.", n.id.c_str(),
                                          playedDb, thr, fix.c_str()));
        } else if (lead && flatCount > 0 && 4 * flatCount >= np) {
            std::string list;
            for (const auto& s : flatSecs) list += (list.empty() ? "'" : ", '") + s + "'";
            findings.push_back({2, "flat_dynamics",
                                fmt("'%s' (lead) is dynamic overall (%.1f dB per phrase) but %d of its %d phrases stay under %.1f dB "
                                    "(in %s): give those phrases velocity arcs and accents too.",
                                    n.id.c_str(), playedDb, flatCount, np, thr, list.c_str()),
                                flatSecs, {n.id}});
            R.severity = 2;
            R.mark = fmt("%d/%d phrases flat", flatCount, np);
        }
    }
    return out;
}

}  // namespace as::analysis
