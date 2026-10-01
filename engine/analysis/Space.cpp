#include "analysis/Space.h"

#include "analysis/Aggregate.h"
#include "analysis/MixImpl.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <initializer_list>
#include <string>
#include <utility>

namespace as::analysis {

const char* roleName(Role r) noexcept {
    switch (r) {
        case Role::Drums: return "drums";
        case Role::Bass: return "bass";
        case Role::Bed: return "bed";
        case Role::Lead: return "lead";
        case Role::Other: return "other";
        case Role::Fx: return "fx";
        case Role::Return: return "return";
        case Role::Group: return "group";
        case Role::Unknown: break;
    }
    return "unknown";
}

const char* returnKindName(ReturnKind k) noexcept {
    switch (k) {
        case ReturnKind::Reverb: return "reverb";
        case ReturnKind::Delay: return "delay";
        case ReturnKind::Gated: return "gated";
        case ReturnKind::Width: return "width";
        case ReturnKind::Other: return "other";
        case ReturnKind::None: break;
    }
    return "none";
}

namespace {

constexpr double kFloorLu = -60.0;       // levels below this read as "nothing"
constexpr double kFullWithinLu = 4.0;    // full sections: within this of the loudest section
constexpr double kLeadActiveDb = 20.0;   // lead ticks within this of its loudest tick count as "playing"

std::string fmt(const char* f, ...) {
    char buf[2048];
    va_list ap;
    va_start(ap, f);
    std::vsnprintf(buf, sizeof buf, f, ap);
    va_end(ap);
    return buf;
}

double r1(double x) { return std::isfinite(x) ? std::round(x * 10.0) / 10.0 + 0.0 : kDbFloor; }
double r2(double x) { return std::isfinite(x) ? std::round(x * 100.0) / 100.0 + 0.0 : 0.0; }

double ratioDb(double num, double den) {
    if (!(den > 0.0)) return kFloorLu;
    return num > 0.0 ? std::max(kFloorLu, 10.0 * std::log10(num / den)) : kFloorLu;
}

std::string quoteList(const std::vector<std::string>& v, std::size_t maxItems = 6) {
    std::string s;
    for (std::size_t i = 0; i < v.size() && i < maxItems; ++i) s += (i ? ", '" : "'") + v[i] + "'";
    if (v.size() > maxItems) s += fmt(" and %d more", static_cast<int>(v.size() - maxItems));
    return s;
}

std::string signedDb(double v) { return fmt("%+.0f", std::round(v)); }

// ------------------------------------------------------------------ names

std::string lower(const std::string& s) {
    std::string o = s;
    for (char& c : o) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return o;
}

// Id tokens: split at non-letters ("hook-double" -> hook, double; "lead2" -> lead).
std::vector<std::string> tokens(const std::string& id) {
    std::vector<std::string> out;
    std::string cur;
    for (char c : lower(id)) {
        if (c >= 'a' && c <= 'z') {
            cur += c;
        } else if (!cur.empty()) {
            out.push_back(cur);
            cur.clear();
        }
    }
    if (!cur.empty()) out.push_back(cur);
    return out;
}

// A token of the id is one of `exact`, or starts with one of `prefix` ("hook-double" -> hook,
// "riser2" -> riser), or the id contains one of `anywhere` (compounds: "bigkick", "darkpad",
// "mainlead"). Only unambiguous words go into `anywhere`: a substring match on words like "beat",
// "rise", "sing" or "down" would read "heartbeat_pad" as drums, "sunrise_lead" as a riser,
// "crossing_keys" as a lead and "sundown_strings" as an fx.
bool named(const std::string& id, std::initializer_list<const char*> prefix, std::initializer_list<const char*> anywhere = {},
           std::initializer_list<const char*> exact = {}) {
    const std::string l = lower(id);
    const auto toks = tokens(id);
    for (const auto& t : toks) {
        for (const char* w : prefix)
            if (t.rfind(w, 0) == 0) return true;
        for (const char* w : exact)
            if (t == w) return true;
    }
    for (const char* w : anywhere)
        if (l.find(w) != std::string::npos) return true;
    return false;
}

bool drumName(const std::string& id) {
    return named(id,
                 {"kick", "snare", "drum", "kit", "hat", "hihat", "hh", "perc", "clap", "tom", "cymbal", "crash", "bd", "sd", "shaker",
                  "tamb", "rim", "conga", "bongo", "cowbell", "breakbeat"},
                 {"kick", "snare", "drum", "hihat", "clap", "cymbal", "shaker", "cowbell", "808", "909"},
                 {"ride", "break", "breaks", "beat", "beats", "groove", "loop", "loops"});
}
bool fxName(const std::string& id) {
    return named(id,
                 {"riser", "impact", "downlift", "uplift", "downer", "sweep", "whoosh", "noise", "sfx", "fx", "reverse", "boom", "swell",
                  "transition"},
                 {"riser", "impact", "downlift", "uplift", "whoosh", "sweep", "transition"},
                 {"rise", "down", "hit", "hits", "wind", "winds"});
}
bool bassName(const std::string& id) {
    return named(id, {"bass"}, {"bass"}, {"sub"});  // "sub", "sub_808" - not "subtle"
}
bool leadName(const std::string& id) {
    return named(id, {"lead", "hook", "melody", "melo", "solo", "topline", "vox", "vocal", "voice", "theme", "keytar", "soar", "singer"},
                 {"lead", "hook", "melody", "topline", "keytar", "vocal"}, {"sing"});
}
bool bedName(const std::string& id) {
    return named(id,
                 {"pad", "string", "choir", "drone", "atmos", "ambient", "bed", "wash", "organ", "texture", "cloud", "haze", "ensemble"},
                 {"pad", "string", "choir", "drone", "atmos", "ambient", "texture", "ensemble"});
}
bool arpName(const std::string& id) {
    return named(id,
                 {"arp", "seq", "pluck", "bell", "glass", "stab", "chord", "comp", "key", "piano", "rhodes", "epiano", "guitar", "gtr",
                  "perc", "marimba", "harp"},
                 {"arp", "pluck", "chord", "piano", "rhodes", "guitar", "marimba"});
}

ReturnKind kindFromName(const std::string& id) {
    if (named(id, {"hall", "plate", "verb", "reverb", "room", "chamber", "space", "amb", "cathedral", "shimmer", "bloom", "wash"},
              {"hall", "plate", "verb", "chamber", "cathedral", "shimmer"}))
        return ReturnKind::Reverb;
    if (named(id, {"echo", "delay", "dly", "tape"}, {"echo", "delay"})) return ReturnKind::Delay;
    if (named(id, {"gated", "gate"})) return ReturnKind::Gated;
    if (named(id, {"wide", "chorus", "ensemble", "width", "dimension", "juno", "doubler"}, {"chorus", "ensemble", "width", "doubler"}))
        return ReturnKind::Width;
    return ReturnKind::None;
}

ReturnKind kindFromFx(const std::vector<NodeRouting::Fx>& fx) {
    bool reverb = false, delay = false, gated = false, width = false;
    for (const auto& f : fx) {
        reverb = reverb || f.type == "reverb" || f.type == "convolver";  // (a convolver return is an IR reverb)
        delay = delay || f.type == "delay";
        gated = gated || f.type == "gatedreverb";
        width = width || f.type == "chorus" || f.type == "ensemble" || f.type == "flanger" || f.type == "phaser" || f.type == "width" ||
                f.type == "dimension" || f.type == "microshift";
        reverb = reverb || f.type == "shimmer";  // the octave-up shimmer is a reverb (bus/shimmer)
    }
    return reverb ? ReturnKind::Reverb : delay ? ReturnKind::Delay : gated ? ReturnKind::Gated : width ? ReturnKind::Width : ReturnKind::Other;
}

double paramNum(const json& params, const char* key, double fallback) {
    if (!params.is_object()) return fallback;
    const auto it = params.find(key);
    return it != params.end() && it->is_number() ? it->get<double>() : fallback;
}

// The insert effects / instrument settings that make a track stereo by themselves.
std::string widenerOf(const NodeData& n) {
    if (!n.hasRouting) return "";
    for (const auto& f : n.routing.fx) {
        if (f.type == "chorus" || f.type == "ensemble" || f.type == "flanger" || f.type == "phaser" || f.type == "dimension" ||
            f.type == "microshift")
            return f.type;
        if (f.type == "width" && paramNum(f.params, "width", 1.0) > 1.05) return "width";
    }
    const json& ip = n.routing.instrumentParams;
    if (n.routing.instrument == "va" && paramNum(ip, "unison", 1.0) >= 2.0 && paramNum(ip, "unison.spread", 0.7) >= 0.3)
        return "unison spread";
    if (n.routing.instrument == "dx7" && paramNum(ip, "detune", 0.0) > 0.0) return "dx7 detune";
    return "";
}

bool reverbInsert(const NodeData& n) {
    if (!n.hasRouting) return false;
    for (const auto& f : n.routing.fx)
        if ((f.type == "reverb" && paramNum(f.params, "mix", 0.3) >= 0.15) ||  // (a convolver at mix 1 is a cabinet)
            (f.type == "convolver" && paramNum(f.params, "mix", 1.0) >= 0.15 && paramNum(f.params, "mix", 1.0) < 0.95))
            return true;
    return false;
}

bool isMusic(Role r) { return r == Role::Bed || r == Role::Lead || r == Role::Other; }

// A reverb insert that makes the music wet without a return (on a music track or a group bus): not
// measurable, so "no reverb return" is not called dry and a low return level only informs.
bool wetInsert(const NodeData& n) { return ((!n.isBus && isMusic(n.role)) || n.role == Role::Group) && reverbInsert(n); }

// ------------------------------------------------------------------ notes

struct NoteStats {
    int count{0};
    double medianBeats{0.0};
    double polyShare{0.0};  // share of the sounding time with 2+ notes
};

NoteStats noteStats(const std::vector<std::pair<double, double>>& notes) {
    NoteStats s;
    std::vector<double> durs;
    std::vector<std::pair<double, int>> ev;
    for (const auto& [start, dur] : notes) {
        if (!(dur > 0.0) || !std::isfinite(start)) continue;
        durs.push_back(dur);
        ev.push_back({start, +1});
        ev.push_back({start + dur, -1});
    }
    s.count = static_cast<int>(durs.size());
    if (durs.empty()) return s;
    std::nth_element(durs.begin(), durs.begin() + static_cast<std::ptrdiff_t>(durs.size() / 2), durs.end());
    s.medianBeats = durs[durs.size() / 2];
    std::sort(ev.begin(), ev.end());  // ends (-1) before starts (+1) at the same beat
    double one = 0.0, two = 0.0, last = ev.front().first;
    int depth = 0;
    for (const auto& [t, d] : ev) {
        if (depth >= 1) one += t - last;
        if (depth >= 2) two += t - last;
        depth += d;
        last = t;
    }
    s.polyShare = one > 0.0 ? two / one : 0.0;
    return s;
}

// Audio-only "sustained" test (no notes known): a steady envelope (median change between consecutive
// active 100 ms ticks < 1.5 dB), modest crest, active a good part of the song, not a low-end part.
bool steadyEnvelope(const NodeData& n) {
    const StreamStats& st = *n.stats;
    const auto& t = st.ticks();
    std::vector<double> lv(t.size(), kDbFloor);
    double mx = kDbFloor;
    for (std::size_t i = 0; i < t.size(); ++i) {
        const double f = st.tickFrames(i);
        if (f > 0) lv[i] = dbFromPower(t[i].energy() / (2.0 * f));
        mx = std::max(mx, lv[i]);
    }
    const double thr = std::max(-50.0, mx - 30.0);
    std::vector<double> d;
    std::size_t active = 0;
    for (std::size_t i = 0; i < lv.size(); ++i) {
        if (lv[i] <= thr) continue;
        ++active;
        if (i > 0 && lv[i - 1] > thr) d.push_back(std::fabs(lv[i] - lv[i - 1]));
    }
    if (d.size() < 10 || active < t.size() * 3 / 10) return false;
    std::nth_element(d.begin(), d.begin() + static_cast<std::ptrdiff_t>(d.size() / 2), d.end());
    const double crest = n.peakDb - n.rmsDb;
    return d[d.size() / 2] < 1.5 && crest < 16.0 && n.dominantBand >= 2;
}

// ------------------------------------------------------------------ roles

void classify(MixImpl& m) {
    SpaceData& S = m.space;
    S.routing = false;
    for (const auto& n : m.nodes) S.routing = S.routing || n.hasRouting;
    const std::size_t nn = m.nodes.size();
    std::vector<NoteStats> ns(nn);
    for (std::size_t i = 0; i < nn; ++i)
        if (m.nodes[i].hasRouting) ns[i] = noteStats(m.nodes[i].routing.notes);

    for (std::size_t i = 0; i < nn; ++i) {
        NodeData& n = m.nodes[i];
        n.feedsMaster = n.routing.output == "master";  // default routing: straight to the master
        n.returnKind = ReturnKind::None;
        if (n.isBus) {
            // A return is fed by sends (and maybe by other buses' outputs: an echo return feeding the
            // hall); a group is fed by track outputs.
            int outputsIn = 0, busesIn = 0, sendsIn = 0;
            if (S.routing)
                for (const auto& o : m.nodes) {
                    if (&o == &n) continue;
                    if (o.routing.output == n.id) ++(o.isBus ? busesIn : outputsIn);
                    for (const auto& [bus, db] : o.routing.sends)
                        if (bus == n.id && db > -90.0) ++sendsIn;
                }
            bool isReturn = false;
            ReturnKind kind = ReturnKind::None;
            if (S.routing && (sendsIn > 0 || outputsIn > 0 || busesIn > 0)) {
                isReturn = sendsIn > 0 && outputsIn == 0;
                kind = kindFromFx(n.routing.fx);
            } else {
                kind = n.hasRouting && !n.routing.fx.empty() ? kindFromFx(n.routing.fx) : ReturnKind::None;
                const ReturnKind byName = kindFromName(n.id);
                if (kind == ReturnKind::None || kind == ReturnKind::Other) kind = byName;
                isReturn = kind != ReturnKind::None && kind != ReturnKind::Other && (byName != ReturnKind::None || n.hasRouting);
            }
            n.role = isReturn ? Role::Return : Role::Group;
            n.returnKind = isReturn ? (kind == ReturnKind::None ? ReturnKind::Other : kind) : ReturnKind::None;
            continue;
        }
        const NoteStats& s = ns[i];
        const bool notes = s.count > 0;
        const double beatSec = 60.0 / m.bpm;
        // Names first (the composer's intent), then the notes, then the audio.
        const bool lowPart = n.dominantBand >= 0 && n.dominantBand <= 1 && n.stats->centroidHz() < 300.0;
        // "sub_808" / "808bass" are basses; "bass_drum" / "kickbass" stay drums.
        const bool bassNamed = bassName(n.id) && !named(n.id, {"drum", "kick"}, {"drum", "kick"});
        if (n.routing.instrument == "drums" || (drumName(n.id) && !bassNamed))
            n.role = Role::Drums;
        else if (bassNamed)
            n.role = Role::Bass;
        else if (fxName(n.id))
            n.role = Role::Fx;
        else if (leadName(n.id) && !bedName(n.id))
            n.role = Role::Lead;
        else if (notes && s.count <= 6 && s.medianBeats >= 4.0 && !bedName(n.id))  // a few long notes: risers, swells, hits
            n.role = Role::Fx;
        else if (lowPart)
            n.role = Role::Bass;
        else if ((bedName(n.id) && (!notes || s.medianBeats >= 1.0)) ||
                 (notes && s.count >= 4 && s.medianBeats >= 1.5 && s.medianBeats * beatSec >= 0.75) ||
                 (notes && s.count >= 8 && s.polyShare >= 0.5 && s.medianBeats >= 1.0 && s.medianBeats * beatSec >= 0.6) ||
                 (!notes && steadyEnvelope(n)))
            n.role = Role::Bed;
        else
            n.role = Role::Other;
    }
    // No lead named: the loudest melodic, (nearly) monophonic line with normal note lengths.
    bool anyLead = false;
    for (const auto& n : m.nodes) anyLead = anyLead || n.role == Role::Lead;
    if (!anyLead) {
        int best = -1;
        for (std::size_t i = 0; i < nn; ++i) {
            const NodeData& n = m.nodes[i];
            const NoteStats& s = ns[i];
            if (n.role != Role::Other || s.count < 8 || s.polyShare >= 0.15 || s.medianBeats < 0.3 || s.medianBeats > 2.5 || arpName(n.id))
                continue;
            if (best < 0 || n.lufs > m.nodes[static_cast<std::size_t>(best)].lufs) best = static_cast<int>(i);
        }
        if (best >= 0) m.nodes[static_cast<std::size_t>(best)].role = Role::Lead;
    }
    S.reverbReturns.clear();
    S.delayReturns.clear();
    S.refNodes.clear();
    for (std::size_t i = 0; i < nn; ++i) {
        const NodeData& n = m.nodes[i];
        if (n.role == Role::Return && n.returnKind == ReturnKind::Reverb) S.reverbReturns.push_back(static_cast<int>(i));
        if (n.role == Role::Return && n.returnKind == ReturnKind::Delay) S.delayReturns.push_back(static_cast<int>(i));
        if (S.routing && n.feedsMaster) S.refNodes.push_back(static_cast<int>(i));
    }
}

// ------------------------------------------------------------------ measures

// Raw sums of one section (or several): everything the space measures are derived from.
struct Raw {
    Agg mix;
    double musLL{0}, musRR{0}, musLR{0};
    double refK{0}, revK{0}, echoK{0}, revLow{0}, revE{0};
    std::vector<double> retK;           // per node (returns only)
    double bedK{0}, leadK{0};
    int lead{-1};
    std::vector<int> beds;
    bool leadPlays{false};

    void add(const Raw& o) {
        mix.append(o.mix);
        musLL += o.musLL; musRR += o.musRR; musLR += o.musLR;
        refK += o.refK; revK += o.revK; echoK += o.echoK; revLow += o.revLow; revE += o.revE;
        if (retK.size() < o.retK.size()) retK.resize(o.retK.size(), 0.0);
        for (std::size_t i = 0; i < o.retK.size(); ++i) retK[i] += o.retK[i];
        bedK += o.bedK;
        leadK += o.leadK;
        leadPlays = leadPlays || o.leadPlays;
        for (int b : o.beds)
            if (std::find(beds.begin(), beds.end(), b) == beds.end()) beds.push_back(b);
    }
};

class Assessor {
public:
    Assessor(MixImpl& m, std::vector<SpaceFinding>& f, std::vector<std::string>& s) : m_(m), P_(*m.profile), findings_(f), sugg_(s) {}
    json run();

private:
    Raw measureSection(std::size_t s);
    SpaceSection finish(const Raw& r) const;
    void judge(SpaceSection& s) const;
    void tails();
    void echoActivity();
    void opportunities();
    void warnDry();
    void warnInaudible();
    void warnWashy();
    void warnNarrow();
    void warnBed();
    void warnOverWide();
    json sectionJson(const SpaceSection& s) const;
    std::vector<std::string> fullNames(const char* issue) const;
    std::string sendPlan(const std::vector<int>& returns, double deltaDb, std::size_t maxTracks) const;

    void finding(int sev, const char* code, std::string msg, std::vector<std::string> sections = {}, std::vector<std::string> nodes = {}) {
        findings_.push_back({sev, code, std::move(msg), std::move(sections), std::move(nodes)});
    }
    void suggest(std::string s) {
        if (std::find(sugg_.begin(), sugg_.end(), s) == sugg_.end()) sugg_.push_back(std::move(s));
    }
    const std::string& id(int n) const { return m_.nodes[static_cast<std::size_t>(n)].id; }
    std::int64_t secSample(double sec) const { return std::llround(sec * m_.sampleRate); }

    MixImpl& m_;
    const AnalysisProfile& P_;
    std::vector<SpaceFinding>& findings_;
    std::vector<std::string>& sugg_;
    std::vector<std::vector<Agg>> A_;   // [node][section]
    std::vector<Raw> raw_;              // [section]
    bool reverbInserts_{false};
    bool implicit_{false};
};

Raw Assessor::measureSection(std::size_t s) {
    const std::size_t nn = m_.nodes.size();
    const SectionData& sec = m_.sections[s];
    const std::int64_t s0 = secSample(sec.startSec), s1 = secSample(sec.endSec);
    Raw r;
    r.mix = aggregate(*m_.mix, s0, s1);
    r.retK.assign(nn, 0.0);
    for (std::size_t n = 0; n < nn; ++n) {
        const NodeData& nd = m_.nodes[n];
        const Agg& a = A_[n][s];
        if (!nd.isBus && isMusic(nd.role)) { r.musLL += a.ll; r.musRR += a.rr; r.musLR += a.lr; }
        if (nd.role == Role::Return) r.retK[n] = a.k;
        if (nd.role == Role::Return && nd.returnKind == ReturnKind::Reverb) {
            r.revK += a.k;
            r.revLow += a.lowLL + a.lowRR;
            r.revE += a.energy();
        }
        if (nd.role == Role::Return && nd.returnKind == ReturnKind::Delay) r.echoK += a.k;
    }
    if (!m_.space.refNodes.empty())
        for (int n : m_.space.refNodes) r.refK += A_[static_cast<std::size_t>(n)][s].k;
    if (!(r.refK > 0.0)) r.refK = r.mix.k;

    // Bed under the lead: K-weighted, on the 100 ms ticks where the (loudest) lead plays.
    const double T = m_.tickLen;
    const auto t0 = static_cast<std::size_t>(std::max(0.0, std::ceil(static_cast<double>(s0) / T - 1e-9)));
    const auto t1 = static_cast<std::size_t>(std::max(0.0, std::floor(static_cast<double>(s1) / T + 1e-9)));
    for (std::size_t n = 0; n < nn; ++n)
        if (m_.nodes[n].role == Role::Bed && A_[n][s].rmsDb() > -50.0) r.beds.push_back(static_cast<int>(n));
    if (t1 <= t0) return r;
    double bestK = 0.0;
    std::vector<std::size_t> bestTicks;
    for (std::size_t n = 0; n < nn; ++n) {
        if (m_.nodes[n].role != Role::Lead) continue;
        const StreamStats& st = *m_.nodes[n].stats;
        const auto& tk = st.ticks();
        double mx = 0.0;
        for (std::size_t i = t0; i < t1 && i < tk.size(); ++i) mx = std::max(mx, tk[i].k / std::max(1.0, st.tickFrames(i)));
        if (mx <= 0.0) continue;
        const double thr = std::max(mx * std::pow(10.0, -kLeadActiveDb / 10.0), 2.0 * std::pow(10.0, -55.0 / 10.0));
        std::vector<std::size_t> act;
        double k = 0.0;
        for (std::size_t i = t0; i < t1 && i < tk.size(); ++i)
            if (tk[i].k / std::max(1.0, st.tickFrames(i)) > thr) { act.push_back(i); k += tk[i].k; }
        if (act.size() < std::max<std::size_t>(3, (t1 - t0) * 15 / 100)) continue;  // plays at least 15 % of the section
        if (k > bestK) { bestK = k; r.lead = static_cast<int>(n); bestTicks = std::move(act); }
    }
    if (r.lead < 0) return r;
    r.leadPlays = true;
    r.leadK = bestK;
    for (int b : r.beds) {
        const auto& tk = m_.nodes[static_cast<std::size_t>(b)].stats->ticks();
        for (std::size_t i : bestTicks)
            if (i < tk.size()) r.bedK += tk[i].k;
    }
    return r;
}

SpaceSection Assessor::finish(const Raw& r) const {
    SpaceSection o;
    o.assessed = r.mix.frames > 0 && r.mix.rmsDb() > -60.0;
    if (!o.assessed) {
        o.verdict = "silent";
        return o;
    }
    o.widthPct = r.mix.width();
    o.corr = r.mix.corr();
    o.hiWidthPct = r.mix.hiWidth();
    o.hiCorr = r.mix.hiCorr();
    if (r.musLL + r.musRR > 1e-4 * r.mix.energy()) o.musicWidthPct = widthPct(r.musLL, r.musRR, r.musLR);
    if (!m_.space.reverbReturns.empty()) o.wetLu = ratioDb(r.revK, r.refK);
    if (!m_.space.delayReturns.empty()) o.echoLu = ratioDb(r.echoK, r.refK);
    o.returnLowPct = r.revE > 0.0 ? 100.0 * r.revLow / r.revE : 0.0;
    for (std::size_t n = 0; n < r.retK.size(); ++n)
        if (m_.nodes[n].role == Role::Return) o.returnsLu.push_back({static_cast<int>(n), ratioDb(r.retK[n], r.refK)});
    o.leadPlays = r.leadPlays;
    o.lead = r.lead;
    o.beds = r.beds;
    o.bedPlays = r.bedK > 1e-6 * r.leadK && r.bedK > 0.0;
    if (r.leadPlays && o.bedPlays) o.bedVsLeadDb = ratioDb(r.bedK, r.leadK);
    return o;
}

void Assessor::judge(SpaceSection& s) const {
    s.issues.clear();
    if (!s.assessed) return;
    if (s.quiet) {  // a fade, a tail or a near-empty break: a ringing reverb there is wanted, not a wash
        s.verdict = "quiet";
        return;
    }
    auto add = [&](const char* i) { s.issues.push_back(i); };
    const bool wetKnown = s.wetLu.has_value();
    // Breaks and intros may be wetter by design: outside the full sections only a clearly washed-out one
    // (3 LU past the limit) is washy - the same rule as the 'washy' warning.
    if (wetKnown && *s.wetLu > P_.washyLu + (s.full ? 0.0 : 3.0)) add("washy");
    if (wetKnown && *s.wetLu > P_.wetMinLu - 3.0 && s.returnLowPct > P_.returnLowMaxPct) add("low_wash");
    if (s.corr < 0.0) add("phasey");
    if (wetKnown && *s.wetLu < P_.wetMinLu) add("dry");
    if (!wetKnown && !reverbInserts_ && !m_.nodes.empty()) { add("dry"); add("no_reverb"); }
    if (s.hiWidthPct < P_.widthMinPct) add("narrow");
    if (P_.bedBelowLeadMaxDb && s.leadPlays && (!s.bedPlays || (s.bedVsLeadDb && *s.bedVsLeadDb < -*P_.bedBelowLeadMaxDb)))
        add("thin_bed");
    auto has = [&](const char* i) { return std::find(s.issues.begin(), s.issues.end(), i) != s.issues.end(); };
    if (has("washy") || has("low_wash") || has("phasey"))
        s.verdict = "washy";
    else if (has("dry"))
        s.verdict = "dry";
    else if (has("narrow"))
        s.verdict = "narrow";
    else if (s.issues.empty() && wetKnown && *s.wetLu <= P_.wetMaxLu && s.hiWidthPct <= P_.widthMaxPct)
        s.verdict = "lush";
    else
        s.verdict = "ok";
}

std::vector<std::string> Assessor::fullNames(const char* issue) const {
    std::vector<std::string> v;
    for (std::size_t s = 0; s < m_.sections.size(); ++s) {
        const SpaceSection& sp = m_.space.sections[s];
        if (!sp.full || !sp.assessed) continue;
        if (issue && std::find(sp.issues.begin(), sp.issues.end(), issue) == sp.issues.end()) continue;
        v.push_back(m_.sections[s].name);
    }
    return v;
}

// ------------------------------------------------------------------ tails

// Delay returns vs the mix on the 100 ms ticks of the full sections where they sound (within 20 dB of
// their loudest tick there): an echo thrown on the last note of a phrase (automated send) is judged by
// how loud it is when it happens, not averaged over the silence between the throws.
void Assessor::echoActivity() {
    SpaceData& S = m_.space;
    S.echoActiveLu.clear();
    if (S.delayReturns.empty() || !m_.mix) return;
    const double T = m_.tickLen;
    std::vector<std::pair<std::size_t, std::size_t>> ranges;
    for (std::size_t s = 0; s < m_.sections.size(); ++s) {
        if (!S.sections[s].full) continue;
        const double s0 = static_cast<double>(secSample(m_.sections[s].startSec)), s1 = static_cast<double>(secSample(m_.sections[s].endSec));
        const auto t0 = static_cast<std::size_t>(std::max(0.0, std::ceil(s0 / T - 1e-9)));
        const auto t1 = static_cast<std::size_t>(std::max(0.0, std::floor(s1 / T + 1e-9)));
        if (t1 > t0) ranges.push_back({t0, t1});
    }
    auto refAt = [&](std::size_t i) {
        double k = 0.0;
        if (S.refNodes.empty()) {
            const auto& tk = m_.mix->ticks();
            return i < tk.size() ? static_cast<double>(tk[i].k) : 0.0;
        }
        for (int n : S.refNodes) {
            const auto& tk = m_.nodes[static_cast<std::size_t>(n)].stats->ticks();
            if (i < tk.size()) k += tk[i].k;
        }
        return k;
    };
    for (int r : S.delayReturns) {
        const StreamStats& st = *m_.nodes[static_cast<std::size_t>(r)].stats;
        const auto& tk = st.ticks();
        auto perFrame = [&](std::size_t i) { return tk[i].k / std::max(1.0, st.tickFrames(i)); };
        double mx = 0.0;
        for (const auto& [t0, t1] : ranges)
            for (std::size_t i = t0; i < t1 && i < tk.size(); ++i) mx = std::max(mx, perFrame(i));
        if (!(mx > 0.0)) continue;
        double e = 0.0, ref = 0.0;
        for (const auto& [t0, t1] : ranges)
            for (std::size_t i = t0; i < t1 && i < tk.size(); ++i)
                if (perFrame(i) > mx * 1e-2) { e += tk[i].k; ref += refAt(i); }
        if (e > 0.0 && ref > 0.0) S.echoActiveLu.push_back({r, ratioDb(e, ref)});
    }
}

void Assessor::tails() {
    SpaceData& S = m_.space;
    S.tails.clear();
    S.tailDb.reset();
    std::vector<int> rets = S.reverbReturns;
    rets.insert(rets.end(), S.delayReturns.begin(), S.delayReturns.end());
    if (rets.empty() || !m_.mix) return;
    const std::size_t N = m_.mix->ticks().size();
    std::vector<double> dry(N, 0.0), ret(N, 0.0), fr(N, 0.0);
    for (std::size_t i = 0; i < N; ++i) fr[i] = m_.mix->tickFrames(i);
    for (const auto& n : m_.nodes) {
        if (n.isBus) continue;
        const auto& tk = n.stats->ticks();
        for (std::size_t i = 0; i < N && i < tk.size(); ++i) dry[i] += tk[i].k;
    }
    for (int r : rets) {
        const auto& tk = m_.nodes[static_cast<std::size_t>(r)].stats->ticks();
        for (std::size_t i = 0; i < N && i < tk.size(); ++i) ret[i] += tk[i].k;
    }
    for (std::size_t i = 0; i < N; ++i) {
        const double f = std::max(1.0, fr[i]);
        dry[i] /= f;
        ret[i] /= f;
    }
    const double absMin = 2.0 * std::pow(10.0, -50.0 / 10.0);  // music before the stop above ~-50 dBFS
    const double drop12 = std::pow(10.0, -1.2), drop15 = std::pow(10.0, -1.5);
    std::vector<double> dbs;
    for (std::size_t i = 5; i + 1 < N; ++i) {
        double before = 0.0, retBefore = 0.0;
        for (std::size_t j = i - 5; j < i; ++j) { before += dry[j]; retBefore += ret[j]; }
        before /= 5.0;
        retBefore /= 5.0;
        if (before < absMin || dry[i] > before * drop12) continue;
        double after = 0.0;
        const std::size_t aEnd = std::min(N, i + 6);
        for (std::size_t j = i + 1; j < aEnd; ++j) after = std::max(after, dry[j]);
        if (after > before * drop15 || aEnd - i < 4) continue;
        // Only stops of music that was sent to the returns (else a dry part simply ended: no tail to judge).
        if (retBefore < before * 1e-4) continue;
        // Returns 0.3-0.8 s after the stop, and how long they stay within 40 dB of the music.
        double sum = 0.0;
        int cnt = 0;
        for (std::size_t j = i + 3; j < std::min(N, i + 9); ++j) { sum += ret[j]; ++cnt; }
        SpaceTail t;
        t.sec = static_cast<double>(i) * m_.tickSec();
        t.tailDb = cnt ? std::max(-90.0, 10.0 * std::log10(std::max(sum / cnt, 1e-30) / before)) : -90.0;
        std::size_t j = i;
        while (j < N && ret[j] > before * 1e-4 && dry[j] < before * drop15) ++j;
        t.capped = j >= N || dry[j] >= before * drop15;
        t.decaySec = static_cast<double>(j - i) * m_.tickSec();
        S.tails.push_back(t);
        dbs.push_back(t.tailDb);
        i += 20;  // one event per 2 s
    }
    if (!dbs.empty()) {
        std::sort(dbs.begin(), dbs.end());
        S.tailDb = dbs.size() % 2 ? dbs[dbs.size() / 2] : 0.5 * (dbs[dbs.size() / 2 - 1] + dbs[dbs.size() / 2]);
    }
}

// ------------------------------------------------------------------ opportunities (narrow)

void Assessor::opportunities() {
    SpaceData& S = m_.space;
    S.opportunities.clear();
    S.opportunityWidth.clear();
    // Only asked for when the mix is narrow (then they are named in narrow_mix and marked in stereo.png).
    const auto& gi = S.global.issues;
    if (std::find(gi.begin(), gi.end(), "narrow") == gi.end()) return;
    std::vector<std::size_t> full;
    for (std::size_t s = 0; s < m_.sections.size(); ++s)
        if (S.sections[s].full) full.push_back(s);
    if (full.empty()) return;
    double musE = 0.0;
    std::vector<Agg> sum(m_.nodes.size());
    for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
        if (m_.nodes[n].isBus || !isMusic(m_.nodes[n].role)) continue;
        for (std::size_t s : full) sum[n].append(A_[n][s]);
        musE += sum[n].energy();
    }
    if (!(musE > 0.0)) return;
    // Centred parts (< 12 % wide) first; when every part already has some width, the big ones under 40 %.
    std::vector<std::pair<double, int>> cand;
    for (const double limit : {12.0, 40.0}) {
        for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
            const NodeData& nd = m_.nodes[n];
            if (nd.isBus || !isMusic(nd.role)) continue;
            const double share = sum[n].energy() / musE, w = sum[n].width();
            if (share < 0.04 || w >= limit) continue;
            bool stereoSend = false;
            for (const auto& [bus, db] : nd.routing.sends)
                for (const auto& o : m_.nodes)
                    if (o.id == bus && o.role == Role::Return && db > -24.0 &&
                        (o.returnKind == ReturnKind::Reverb || o.returnKind == ReturnKind::Delay || o.returnKind == ReturnKind::Width))
                        stereoSend = true;
            const double roleW = nd.role == Role::Bed ? 1.5 : nd.role == Role::Lead ? 0.4 : 1.0;
            const double score = share * (1.0 - w / limit) * roleW * (widenerOf(nd).empty() ? 1.0 : 0.6) * (stereoSend ? 0.8 : 1.0);
            cand.push_back({score, static_cast<int>(n)});
        }
        if (!cand.empty()) break;
    }
    std::stable_sort(cand.begin(), cand.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
    for (std::size_t i = 0; i < cand.size() && i < 3; ++i) {
        S.opportunities.push_back(cand[i].second);
        S.opportunityWidth.push_back(sum[static_cast<std::size_t>(cand[i].second)].width());
    }
}

// ------------------------------------------------------------------ warnings

// "'pad' -10 -> -4 dB, 'strings' -10 -> -4" for the biggest senders into `returns` (+ deltaDb each).
std::string Assessor::sendPlan(const std::vector<int>& returns, double deltaDb, std::size_t maxTracks) const {
    struct Sender { double contrib; std::string id, bus; double db; };
    std::vector<Sender> v;
    std::vector<std::size_t> full;
    for (std::size_t s = 0; s < m_.sections.size(); ++s)
        if (m_.space.sections[s].full) full.push_back(s);
    for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
        const NodeData& nd = m_.nodes[n];
        double e = 0.0;
        for (std::size_t s : full) e += A_[n][s].k;
        for (const auto& [bus, db] : nd.routing.sends)
            for (int r : returns)
                if (id(r) == bus) v.push_back({e * std::pow(10.0, db / 10.0), nd.id, bus, db});
    }
    std::stable_sort(v.begin(), v.end(), [](const Sender& a, const Sender& b) { return a.contrib > b.contrib; });
    std::string s;
    bool clamped = false;
    for (std::size_t i = 0; i < v.size() && i < maxTracks; ++i) {
        const double to = std::min(0.0, v[i].db + deltaDb);
        clamped = clamped || v[i].db + deltaDb > 0.0;
        s += fmt("%s'%s' -> '%s' %s -> %s dB", i ? ", " : "", v[i].id.c_str(), v[i].bus.c_str(), signedDb(v[i].db).c_str(),
                 signedDb(to).c_str());
    }
    if (clamped) s += " (keep sends at or below 0 dB: raise the return's gainDb for the rest)";
    return s;
}

void Assessor::warnDry() {
    const SpaceSection& g = m_.space.global;
    if (std::find(g.issues.begin(), g.issues.end(), "dry") == g.issues.end()) return;
    const auto secs = fullNames("dry");
    const std::string where = implicit_ ? std::string() : " in the full sections " + quoteList(fullNames(nullptr));
    if (!g.wetLu) {
        finding(1, "dry_mix", fmt("The mix is dry: there is no reverb return (a bus with a reverb fed by sends) and no reverb on the "
                                  "music tracks, so nothing gives it depth or space (the '%s' profile wants the reverb %.0f..%.0f LU "
                                  "below the mix)%s.", P_.name.c_str(), -P_.wetMaxLu, -P_.wetMinLu,
                                  m_.space.routing ? "" : "; without the routing only bus ids like 'hall', 'plate', 'verb' are recognised"),
                implicit_ ? std::vector<std::string>{} : secs);
        suggest("Add a reverb return: a bus {\"id\": \"hall\", \"fx\": [{\"type\": \"reverb\", \"params\": {\"type\": \"hall\", \"mix\": 1.0, "
                "\"decay\": 3.2, \"predelay\": 30, \"lowcut\": 250, \"width\": 1.3}}]} and send pads/strings at -6..-3 dB, the lead at "
                "-12..-8 dB and keys/arps at -10 dB (\"sends\": {\"hall\": -6}); a \"plate\" return for the snare and lead adds sheen.");
        return;
    }
    std::vector<std::string> ids;
    for (int r : m_.space.reverbReturns) ids.push_back(id(r));
    const double target = 0.5 * (P_.wetMinLu + P_.wetMaxLu);
    const double delta = std::round(target - *g.wetLu);
    std::string msg = fmt("The mix is dry: the reverb return%s %s sit%s %.1f LU below the mix%s (the '%s' profile expects %.0f..%.0f "
                          "LU below: deep and lush but defined)", ids.size() > 1 ? "s" : "", quoteList(ids).c_str(),
                          ids.size() > 1 ? "" : "s", -*g.wetLu, where.c_str(), P_.name.c_str(), -P_.wetMaxLu, -P_.wetMinLu);
    if (m_.space.tailDb) msg += fmt("; when the music stops the tails are %.0f dB under it", *m_.space.tailDb);
    // Reverb inserts on the music are not measured: say so, and only inform.
    std::vector<std::string> inserts;
    for (const auto& n : m_.nodes)
        if (wetInsert(n)) inserts.push_back(n.id);
    if (!inserts.empty()) msg += fmt(" (not counted: the reverb inserts on %s, which may make up for it)", quoteList(inserts).c_str());
    msg += ".";
    finding(inserts.empty() ? 1 : 2, "dry_mix", msg, implicit_ ? std::vector<std::string>{} : secs, ids);
    std::string fix = fmt("More reverb, about %+.0f dB on the returns (to ~%.0f LU below the mix)", delta, -target);
    const std::string plan = m_.space.routing ? sendPlan(m_.space.reverbReturns, delta, 5) : std::string();
    if (!plan.empty())
        fix += ": raise the sends " + plan + fmt(", or the return's gainDb by %+.0f dB", delta);
    else
        fix += fmt(": raise the gainDb of %s by %+.0f dB or the sends into it", quoteList(ids).c_str(), delta);
    // Beds and leads without any reverb.
    std::vector<std::string> unsent;
    for (const auto& n : m_.nodes) {
        if (n.isBus || (n.role != Role::Bed && n.role != Role::Lead) || reverbInsert(n)) continue;
        bool sent = false;
        for (const auto& [bus, db] : n.routing.sends)
            for (int r : m_.space.reverbReturns) sent = sent || (id(r) == bus && db > -40.0);
        if (!sent) unsent.push_back(n.id);
    }
    if (!unsent.empty() && m_.space.routing)
        fix += fmt("; %s send%s nothing to a reverb: add \"sends\": {\"%s\": %s} (beds -6..-3 dB, leads -12..-8 dB)",
                   quoteList(unsent).c_str(), unsent.size() > 1 ? "" : "s", id(m_.space.reverbReturns.front()).c_str(), "-6");
    fix += ". Longer tails (reverb \"decay\" 3-4 s, \"predelay\" 20-40 ms) sound bigger without washing out the attacks.";
    suggest(fix);
}

void Assessor::warnInaudible() {
    const SpaceSection& g = m_.space.global;
    if (!g.assessed) return;
    const bool dry = std::find(g.issues.begin(), g.issues.end(), "dry") != g.issues.end();
    for (const auto& [n, avgLu] : g.returnsLu) {
        const NodeData& nd = m_.nodes[static_cast<std::size_t>(n)];
        // Echoes are judged while they sound (throws are sparse by design), reverbs on average.
        double lu = avgLu;
        for (const auto& [k, active] : m_.space.echoActiveLu)
            if (k == n) lu = active;
        if (nd.returnKind == ReturnKind::Delay && lu < P_.echoMinLu) {
            const double delta = std::round(P_.echoMinLu + 6.0 - lu);
            finding(1, "reverb_inaudible", fmt("The echo return '%s' is %.1f LU below the mix while it sounds (%.1f LU on average; the '%s' "
                                               "profile: audible above -%.0f LU): its repeats are lost under the music.",
                                               nd.id.c_str(), -lu, -avgLu, P_.name.c_str(), -P_.echoMinLu),
                    {}, {nd.id});
            const std::string plan = m_.space.routing ? sendPlan({n}, delta, 4) : std::string();
            suggest(fmt("Make the echo '%s' audible (about %+.0f dB): %s; echoes bloom best in the gaps (delay \"duck\": 0.3-0.5) and "
                        "as throws on the last note of a phrase (automate \"send.%s\").", nd.id.c_str(), delta,
                        plan.empty() ? fmt("raise its gainDb by %+.0f dB", delta).c_str() : ("raise the sends " + plan).c_str(),
                        nd.id.c_str()));
        } else if (nd.returnKind == ReturnKind::Reverb && lu < P_.wetMinLu - 10.0 && m_.space.reverbReturns.size() > 1) {
            double loudest = lu;  // a return automated up in some sections (a shimmer blooming in the breaks) is heard there
            for (const auto& sec : m_.space.sections)
                for (const auto& [k, secLu] : sec.returnsLu)
                    if (k == n) loudest = std::max(loudest, secLu);
            if (loudest >= P_.wetMinLu - 10.0) continue;
            finding(2, "reverb_inaudible", fmt("The reverb return '%s' is %.1f LU below the mix: it is effectively inaudible (raise its "
                                               "sends by 8-12 dB or remove it).", nd.id.c_str(), -lu), {}, {nd.id});
        }
    }
    if (m_.space.tailDb && *m_.space.tailDb < P_.tailMinDb) {
        std::vector<std::string> at;
        double decay = 0.0;
        for (const auto& t : m_.space.tails) {
            if (at.size() < 4) at.push_back(fmt("%d:%04.1f", static_cast<int>(t.sec / 60.0), t.sec - 60.0 * std::floor(t.sec / 60.0)));
            decay = std::max(decay, t.decaySec);
        }
        std::vector<std::string> ids;
        for (int r : m_.space.reverbReturns) ids.push_back(id(r));
        for (int r : m_.space.delayReturns) ids.push_back(id(r));
        finding(dry ? 2 : 1, "reverb_inaudible",
                fmt("Reverb/echo tails are inaudible when the music stops (%s): 0.3-0.8 s later the returns are %.0f dB under the music "
                    "before (the '%s' profile: above %.0f dB); the longest tail stays within 40 dB for %.1f s.",
                    quoteList(at).c_str(), *m_.space.tailDb, P_.name.c_str(), P_.tailMinDb, decay),
                {}, ids);
        suggest("Let the space ring into breaks and endings: longer reverb \"decay\" (hall 3-5 s), more send on the last chords before "
                "a break (automate \"send.<reverb bus>\" up over the last bar), or a delay throw on the last note (automate "
                "\"send.<echo bus>\" to 0 dB).");
    }
}

void Assessor::warnWashy() {
    const SpaceData& S = m_.space;
    std::vector<std::string> wet, low, phasey;
    double worst = -99.0, worstLow = 0.0;
    for (std::size_t s = 0; s < m_.sections.size(); ++s) {
        const SpaceSection& sp = S.sections[s];
        if (!sp.assessed || sp.quiet) continue;
        // Breaks may be wetter by design: outside the full sections only a clearly washed-out section counts.
        if (sp.wetLu && *sp.wetLu > P_.washyLu + (sp.full ? 0.0 : 3.0)) { wet.push_back(m_.sections[s].name); worst = std::max(worst, *sp.wetLu); }
        if (sp.full && std::find(sp.issues.begin(), sp.issues.end(), "low_wash") != sp.issues.end()) {
            low.push_back(m_.sections[s].name);
            worstLow = std::max(worstLow, sp.returnLowPct);
        }
        if (sp.corr < 0.0) phasey.push_back(m_.sections[s].name);
    }
    const SpaceSection& g = S.global;
    if (g.wetLu && *g.wetLu > P_.washyLu && wet.empty()) { wet.push_back("song"); worst = *g.wetLu; }
    std::vector<std::string> ids;
    for (int r : S.reverbReturns) ids.push_back(id(r));
    if (!wet.empty()) {
        const double target = 0.5 * (P_.wetMinLu + P_.wetMaxLu);
        const double delta = std::round(worst - target);
        finding(1, "washy", fmt("The mix is washy: the reverb returns are only %.1f LU below the mix in %s (the '%s' profile: at least "
                                "%.0f LU below, lush at %.0f..%.0f): the groove, the attacks and the lead lose definition.",
                                -worst, implicit_ ? "the song" : quoteList(wet).c_str(), P_.name.c_str(), -P_.washyLu, -P_.wetMaxLu,
                                -P_.wetMinLu),
                implicit_ ? std::vector<std::string>{} : wet, ids);
        const std::string plan = S.routing ? sendPlan(S.reverbReturns, -delta, 4) : std::string();
        suggest(fmt("Less reverb, about %+.0f dB (to ~%.0f LU below the mix): %s; a longer \"predelay\" (30-60 ms) and a shorter "
                    "\"decay\" keep it big but clear.", -delta, -target,
                    plan.empty() ? fmt("lower the gainDb of %s", quoteList(ids).c_str()).c_str() : ("lower the sends " + plan).c_str()));
    }
    if (!low.empty()) {
        finding(1, "washy", fmt("Low-end reverb: the reverb returns carry %.0f%% of their energy below 150 Hz in %s (limit %.0f%%): "
                                "the tails muddy the kick and bass.", worstLow, implicit_ ? "the song" : quoteList(low).c_str(),
                                P_.returnLowMaxPct),
                implicit_ ? std::vector<std::string>{} : low, ids);
        suggest(fmt("High-pass the reverb returns %s at 200-300 Hz: reverb \"lowcut\": 250, or {\"type\": \"eq\", \"params\": "
                    "{\"hp.freq\": 250}} after the reverb; keep bass and kick out of the reverb sends.", quoteList(ids).c_str()));
    }
    if (!phasey.empty() && (!wet.empty() || !low.empty()))
        suggest(fmt("%s: correlation below 0 (phasey): narrow the widest returns (reverb \"width\": 1.0) and wideners before adding "
                    "more.", quoteList(phasey).c_str()));
}

void Assessor::warnNarrow() {
    const SpaceSection& g = m_.space.global;
    if (std::find(g.issues.begin(), g.issues.end(), "narrow") == g.issues.end()) return;
    const std::string where = implicit_ ? std::string() : " in the full sections " + quoteList(fullNames(nullptr));
    std::string msg = fmt("The mix is narrow: above 150 Hz it is only %.1f%% wide (side/mid; correlation %.2f)%s (the '%s' profile expects "
                          "%.0f..%.0f%%; whole mix %.0f%%, correlation %.2f, with the low end mono as it should be)",
                          g.hiWidthPct, g.hiCorr, where.c_str(), P_.name.c_str(), P_.widthMinPct, P_.widthMaxPct, g.widthPct, g.corr);
    if (g.musicWidthPct) msg += fmt("; the music parts (non-drum, non-bass tracks) are %.0f%% wide", *g.musicWidthPct);
    std::vector<std::string> ids;
    if (!m_.space.opportunities.empty()) {
        msg += ". Widest opportunities: ";
        for (std::size_t i = 0; i < m_.space.opportunities.size(); ++i) {
            const NodeData& n = m_.nodes[static_cast<std::size_t>(m_.space.opportunities[i])];
            const std::string w = widenerOf(n);
            const double width = m_.space.opportunityWidth[i];
            const std::string how = width < 12.0 ? (w.empty() ? (n.hasRouting ? std::string("centred, no chorus/width") : std::string("centred"))
                                                              : "has " + w + " but stays centred")
                                                 : (w.empty() ? std::string("no chorus/width") : "only moderately widened by its " + w);
            msg += fmt("%s'%s' (%s, %.0f%% wide, %s)", i ? ", " : "", n.id.c_str(), roleName(n.role), width, how.c_str());
            ids.push_back(n.id);
        }
    }
    msg += ".";
    finding(1, "narrow_mix", msg, implicit_ ? std::vector<std::string>{} : fullNames("narrow"), ids);
    for (std::size_t i = 0; i < m_.space.opportunities.size(); ++i) {
        const NodeData& n = m_.nodes[static_cast<std::size_t>(m_.space.opportunities[i])];
        const double width = m_.space.opportunityWidth[i];
        const std::string w = widenerOf(n);
        if (n.role == Role::Lead)
            suggest(fmt("'%s' (lead) stays centred, but give it stereo around it: a pingpong echo send ({\"type\": \"delay\", \"params\": "
                        "{\"mode\": \"pingpong\", \"mix\": 1.0}} on a return, send -12 dB) and a plate send.", n.id.c_str()));
        else if (n.role == Role::Bed && w.empty())
            suggest(fmt("Widen '%s' (bed, %.0f%% wide): Juno chorus + width in its fx, {\"type\": \"chorus\", \"params\": {\"mode\": \"II\", "
                        "\"mix\": 0.5}}, {\"type\": \"width\", \"params\": {\"width\": 1.4}}; with va also \"unison\": 3-5, "
                        "\"unison.spread\": 0.9 (keep the chorus mix at 0.5: fully wet plus a width boost goes out of phase).",
                        n.id.c_str(), width));
        else if (n.role == Role::Bed)
            suggest(fmt("Widen '%s' (bed, %.0f%% wide although it has %s): Juno chorus \"mode\": \"II\" at \"mix\": 0.5 then "
                        "{\"type\": \"width\", \"params\": {\"width\": 1.4}}; or split it into two layers panned -0.5 / +0.5.",
                        n.id.c_str(), width, w.c_str()));
        else
            suggest(fmt("Move '%s' (%.0f%% wide) off the centre: pan it -0.3..-0.6 with a counterpart on the other side, or add "
                        "{\"type\": \"chorus\", \"params\": {\"mode\": \"I\", \"mix\": 0.4}} / a pingpong echo send.", n.id.c_str(), width));
    }
    suggest("Returns widen too: reverb \"width\": 1.2-1.5 on the hall; a gentle master {\"type\": \"width\", \"params\": {\"width\": 1.15, "
            "\"monobass\": 120}} widens everything above 120 Hz and keeps the low end mono.");
}

void Assessor::warnBed() {
    if (!P_.bedBelowLeadMaxDb) return;
    std::vector<std::string> thin, missing, beds;
    double worst = 0.0;
    int worstLead = -1, missingLead = -1;
    for (std::size_t s = 0; s < m_.sections.size(); ++s) {
        const SpaceSection& sp = m_.space.sections[s];
        if (!sp.full || std::find(sp.issues.begin(), sp.issues.end(), "thin_bed") == sp.issues.end()) continue;
        if (!sp.bedPlays || !sp.bedVsLeadDb) {
            missing.push_back(m_.sections[s].name);
            if (missingLead < 0) missingLead = sp.lead;
            continue;
        }
        thin.push_back(m_.sections[s].name);
        if (worstLead < 0 || *sp.bedVsLeadDb < worst) { worst = *sp.bedVsLeadDb; worstLead = sp.lead; }
        for (int b : sp.beds)
            if (std::find(beds.begin(), beds.end(), id(b)) == beds.end()) beds.push_back(id(b));
    }
    const double maxDb = *P_.bedBelowLeadMaxDb;
    if (!thin.empty()) {
        const std::string leadId = worstLead >= 0 ? id(worstLead) : std::string("the lead");
        const std::string where = implicit_ ? std::string() : " in " + quoteList(thin);
        std::vector<std::string> nodes = beds;
        nodes.push_back(leadId);
        const double delta = std::ceil(-worst - (maxDb - 2.0));
        finding(1, "thin_bed", fmt("The bed is thin: the sustained parts %s sit up to %.1f dB under the lead '%s'%s (K-weighted while the "
                                   "lead plays; the '%s' profile expects the bed within %.0f dB): the mix sounds pale and empty around "
                                   "the lead.", quoteList(beds).c_str(), -worst, leadId.c_str(), where.c_str(), P_.name.c_str(), maxDb),
                implicit_ ? std::vector<std::string>{} : thin, nodes);
        suggest(fmt("Fill the bed: raise %s gainDb by ~%.0f dB (to ~%.0f dB under '%s'), or layer a second pad an octave up (wide chorus, "
                    "hall send); if the bed is ducked by the kick, a shallower duck (\"depth\" 4-6 dB) keeps it present.",
                    quoteList(beds).c_str(), std::max(1.0, delta), maxDb - 2.0, leadId.c_str()));
    }
    if (!missing.empty()) {
        const std::string leadId = missingLead >= 0 ? id(missingLead) : std::string("the lead");
        const std::string where = implicit_ ? std::string() : " in " + quoteList(missing);
        finding(1, "thin_bed", fmt("The bed is missing: no sustained part (pad, strings, choir) plays under '%s'%s; the '%s' profile wants "
                                   "a bed within %.0f dB of the lead, otherwise the lead floats alone over the drums.",
                                   leadId.c_str(), where.c_str(), P_.name.c_str(), maxDb),
                implicit_ ? std::vector<std::string>{} : missing, {leadId});
        suggest(fmt("Add a sustained bed under '%s'%s: a wide pad/strings layer holding the chords (whole notes, chorus + width, hall "
                    "send -4 dB) about 3-5 dB under the lead.", leadId.c_str(), where.c_str()));
    }
}

// Parts widened into anti-phase (the overshoot of a width fix): they go hollow and lose level in mono.
// Music parts are a warning (and cost the 'lush' verdict); an extra-wide effect return only informs
// (in mono the mix just gets a little drier).
void Assessor::warnOverWide() {
    // A music part with more side than mid over the whole song (correlation below -0.1, > ~120 % wide)
    // has no phantom centre left: a fully wet chorus (mix 1.0) plus a width boost reads -0.2 here, the
    // classic Juno balance (mix 0.5) with width 1.4 reads +0.2 and sounds just as wide. Returns are
    // diffuse by design: only a clearly anti-phase one (-0.25: mono sum -4.3 dB vs -3 dB) is mentioned.
    constexpr double kPartAntiPhase = -0.1, kReturnAntiPhase = -0.25;
    struct Hit { std::string id, text; };
    std::vector<Hit> parts, returns;
    std::vector<std::string> fixes;
    for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
        const NodeData& nd = m_.nodes[n];
        const bool music = !nd.isBus && isMusic(nd.role);
        const bool ret = nd.role == Role::Return &&
                         (nd.returnKind == ReturnKind::Reverb || nd.returnKind == ReturnKind::Width || nd.returnKind == ReturnKind::Delay);
        if ((!music && !ret) || nd.corr >= (music ? kPartAntiPhase : kReturnAntiPhase) || nd.rmsDb < -45.0) continue;
        (music ? parts : returns)
            .push_back({nd.id, fmt("'%s' (correlation %.2f, %.0f%% wide, %.0f dB in mono)", nd.id.c_str(), nd.corr,
                                   std::min(nd.width, 999.0), 10.0 * std::log10(std::max(1e-3, 0.5 * (1.0 + nd.corr))))});
        for (const auto& f : nd.routing.fx) {
            if (f.type == "width" && paramNum(f.params, "width", 1.0) > 1.25)
                fixes.push_back(fmt("'%s' width %.2g -> 1.2", nd.id.c_str(), paramNum(f.params, "width", 1.0)));
            if (f.type == "chorus" && paramNum(f.params, "mix", 0.5) > 0.6)
                fixes.push_back(fmt("'%s' chorus mix %.2g -> 0.5", nd.id.c_str(), paramNum(f.params, "mix", 0.5)));
            if ((f.type == "reverb" || f.type == "delay") && paramNum(f.params, "width", 1.0) > 1.2)
                fixes.push_back(fmt("'%s' %s width %.2g -> 1.0", nd.id.c_str(), f.type.c_str(), paramNum(f.params, "width", 1.0)));
        }
    }
    if (parts.empty() && returns.empty()) return;
    auto list = [](const std::vector<Hit>& v, std::vector<std::string>& ids) {
        std::string s;
        for (std::size_t i = 0; i < v.size(); ++i) {
            if (i < 5) s += (i ? ", " : "") + v[i].text;
            ids.push_back(v[i].id);
        }
        return s;
    };
    if (!parts.empty()) {
        SpaceSection& g = m_.space.global;
        g.issues.push_back("over_wide");
        if (g.verdict == "lush") g.verdict = "ok";
        std::vector<std::string> ids;
        const std::string what = list(parts, ids);
        finding(1, "over_wide", "Over-widened: " + what + (parts.size() > 1 ? " are" : " is") +
                                    " partly out of phase: hollow and quieter in mono (phones, clubs, mono speakers).",
                {}, ids);
    }
    if (!returns.empty()) {
        std::vector<std::string> ids;
        const std::string what = list(returns, ids);
        finding(2, "over_wide", "Extra-wide effect return" + std::string(returns.size() > 1 ? "s " : " ") + what +
                                    ": partly out of phase, so the space shrinks in mono.",
                {}, ids);
    }
    std::string fix = "Back off the widening until the parts' correlation is >= 0 (nodes[].correlation): ";
    if (fixes.empty()) fix += "less \"width\" (1.1-1.3), chorus \"mix\" 0.5, reverb \"width\" <= 1.2";
    for (std::size_t i = 0; i < fixes.size() && i < 6; ++i) fix += (i ? ", " : "") + fixes[i];
    fix += "; width is best built from decorrelated layers (two voices panned apart, unison spread) rather than side boost.";
    suggest(fix);
}

// ------------------------------------------------------------------ json

// Optional numbers are left out when unknown (the report never contains null).
void putOpt(json& j, const char* key, const std::optional<double>& v) {
    if (v) j[key] = r1(*v);
}

json Assessor::sectionJson(const SpaceSection& s) const {
    json j;
    j["verdict"] = s.verdict;
    j["issues"] = s.issues;
    if (!s.assessed) return j;
    j["widthPct"] = r1(s.widthPct);
    j["correlation"] = r2(s.corr);
    j["widthAbove150HzPct"] = r1(s.hiWidthPct);
    j["correlationAbove150Hz"] = r2(s.hiCorr);
    putOpt(j, "musicWidthPct", s.musicWidthPct);
    putOpt(j, "wetnessLu", s.wetLu);
    putOpt(j, "echoLu", s.echoLu);
    putOpt(j, "bedVsLeadDb", s.bedVsLeadDb);
    if (s.lead >= 0) j["lead"] = id(s.lead);
    json beds = json::array();
    for (int b : s.beds) beds.push_back(id(b));
    j["beds"] = beds;
    return j;
}

json Assessor::run() {
    SpaceData& S = m_.space;
    S = SpaceData{};
    classify(m_);
    const std::size_t ns = m_.sections.size(), nn = m_.nodes.size();
    implicit_ = ns == 1 && m_.sections[0].implicit;
    A_.assign(nn, std::vector<Agg>(ns));
    for (std::size_t n = 0; n < nn; ++n)
        for (std::size_t s = 0; s < ns; ++s)
            A_[n][s] = aggregate(*m_.nodes[n].stats, secSample(m_.sections[s].startSec), secSample(m_.sections[s].endSec));
    S.preMasterRef = !S.refNodes.empty();
    reverbInserts_ = false;
    for (const auto& n : m_.nodes)
        if (wetInsert(n)) reverbInserts_ = true;

    // Full sections: within kFullWithinLu of the loudest and, when the song has drums, with the drums
    // playing (within 10 dB of their loudest section: breakdowns and intros with a lone hat may be wetter
    // or narrower by design); the whole song without sections.
    double loudest = kDbFloor;
    for (const auto& sec : m_.sections)
        if (sec.lufs > -70.0 && sec.endSec - sec.startSec >= 2.0) loudest = std::max(loudest, sec.lufs);
    std::vector<double> drumsMs(ns, 0.0);
    double drumsMax = 0.0;
    for (std::size_t n = 0; n < nn; ++n) {
        if (m_.nodes[n].isBus || m_.nodes[n].role != Role::Drums) continue;
        for (std::size_t s = 0; s < ns; ++s) drumsMs[s] += A_[n][s].ms();
    }
    for (double d : drumsMs) drumsMax = std::max(drumsMax, d);
    auto loudEnough = [&](std::size_t s) {
        const SectionData& sec = m_.sections[s];
        return sec.lufs > -70.0 && sec.lufs >= loudest - kFullWithinLu && sec.endSec - sec.startSec >= 2.0;
    };
    bool drumGate = drumsMax > 0.0;
    if (drumGate) {  // no loud section with drums at all (odd): judge by loudness only
        bool any = false;
        for (std::size_t s = 0; s < ns; ++s) any = any || (loudEnough(s) && drumsMs[s] >= drumsMax * 0.1);
        drumGate = any;
    }
    raw_.clear();
    Raw global;
    global.retK.assign(nn, 0.0);
    bool anyFull = false;
    for (std::size_t s = 0; s < ns; ++s) {
        raw_.push_back(measureSection(s));
        SpaceSection sp = finish(raw_.back());
        sp.full = sp.assessed && (implicit_ || (loudEnough(s) && (!drumGate || drumsMs[s] >= drumsMax * 0.1)));
        sp.quiet = sp.assessed && !sp.full && !implicit_ && m_.sections[s].lufs < loudest - 10.0;
        judge(sp);
        if (sp.full) {
            global.add(raw_.back());
            if (global.lead < 0 || (raw_.back().lead >= 0 && raw_.back().leadK > 0.0 &&
                                    m_.nodes[static_cast<std::size_t>(raw_.back().lead)].lufs >
                                        m_.nodes[static_cast<std::size_t>(global.lead)].lufs))
                global.lead = raw_.back().lead;
            anyFull = true;
        }
        S.sections.push_back(std::move(sp));
    }
    if (anyFull) {
        S.global = finish(global);
        S.global.full = true;
        judge(S.global);
    } else {
        S.global.verdict = "silent";
    }
    S.assessed = true;
    tails();
    echoActivity();
    opportunities();
    warnDry();
    warnInaudible();
    warnWashy();
    warnNarrow();
    warnBed();
    warnOverWide();

    // report["space"]
    json j = sectionJson(S.global);
    std::vector<std::string> over;
    for (std::size_t s = 0; s < ns; ++s)
        if (S.sections[s].full) over.push_back(m_.sections[s].name);
    j["measuredOver"] = over;
    j["reference"] = S.preMasterRef ? "pre-master sum of the master's inputs (routing known)"
                                    : "the final mix (no routing given: returns are compared with the mastered mix)";
    j["returnLowPct"] = r1(S.global.returnLowPct);
    json rets = json::array();
    for (std::size_t n = 0; n < nn; ++n) {
        const NodeData& nd = m_.nodes[n];
        if (nd.role != Role::Return) continue;
        json r;
        r["id"] = nd.id;
        r["kind"] = returnKindName(nd.returnKind);
        for (const auto& [k, lu] : S.global.returnsLu)
            if (k == static_cast<int>(n)) r["lu"] = r1(lu);
        for (const auto& [k, lu] : S.echoActiveLu)
            if (k == static_cast<int>(n)) r["activeLu"] = r1(lu);
        double low = 0.0, e = 0.0;
        for (std::size_t s = 0; s < ns; ++s)
            if (S.sections[s].full) { low += A_[n][s].lowLL + A_[n][s].lowRR; e += A_[n][s].energy(); }
        r["lowPct"] = r1(e > 0.0 ? 100.0 * low / e : 0.0);
        r["widthPct"] = r1(nd.width);
        json per = json::array();  // LU vs the mix per section (parallel to space.sections; floor -60)
        for (std::size_t s = 0; s < ns; ++s) {
            double v = kFloorLu;
            for (const auto& [k, lu] : S.sections[s].returnsLu)
                if (k == static_cast<int>(n)) v = lu;
            per.push_back(r1(v));
        }
        r["sectionsLu"] = per;
        rets.push_back(r);
    }
    j["returns"] = rets;
    json tl;
    putOpt(tl, "tailDb", S.tailDb);
    json evs = json::array();
    for (std::size_t i = 0; i < S.tails.size() && i < 8; ++i) {
        const SpaceTail& t = S.tails[i];
        evs.push_back({{"time", fmt("%d:%04.1f", static_cast<int>(t.sec / 60.0), t.sec - 60.0 * std::floor(t.sec / 60.0))},
                       {"bar", static_cast<int>(std::floor(m_.barAt(m_.beatAt(t.sec)) + 1e-9)) + 1},
                       {"tailDb", r1(t.tailDb)},
                       {"decaySec", r1(t.decaySec)},
                       {"musicReturned", t.capped}});
    }
    tl["events"] = evs;
    tl["count"] = static_cast<int>(S.tails.size());
    j["tails"] = tl;
    json opp = json::array();
    for (std::size_t i = 0; i < S.opportunities.size(); ++i) {
        const NodeData& n = m_.nodes[static_cast<std::size_t>(S.opportunities[i])];
        const std::string w = widenerOf(n);
        opp.push_back({{"id", n.id}, {"role", roleName(n.role)}, {"widthPct", r1(S.opportunityWidth[i])}, {"widener", w.empty() ? "none" : w}});
    }
    j["opportunities"] = opp;
    json secs = json::array();
    for (std::size_t s = 0; s < ns; ++s) {
        json e = sectionJson(S.sections[s]);
        e["section"] = m_.sections[s].name;
        e["full"] = S.sections[s].full;
        secs.push_back(e);
    }
    j["sections"] = secs;
    json tg;
    tg["profile"] = P_.name;
    tg["widthAbove150HzPct"] = {P_.widthMinPct, P_.widthMaxPct};
    tg["wetnessLu"] = {P_.wetMinLu, P_.wetMaxLu};
    tg["washyLu"] = P_.washyLu;
    tg["echoMinLu"] = P_.echoMinLu;
    tg["tailMinDb"] = P_.tailMinDb;
    tg["returnLowMaxPct"] = P_.returnLowMaxPct;
    if (P_.bedBelowLeadMaxDb) tg["bedBelowLeadMaxDb"] = *P_.bedBelowLeadMaxDb;
    j["targets"] = tg;
    json roles = json::object();
    for (const auto& n : m_.nodes) roles[n.id] = n.role == Role::Return ? std::string("return:") + returnKindName(n.returnKind) : roleName(n.role);
    j["roles"] = roles;
    return j;
}

}  // namespace

bool idNamed(const std::string& id, std::initializer_list<const char*> prefix, std::initializer_list<const char*> anywhere,
             std::initializer_list<const char*> exact) {
    return named(id, prefix, anywhere, exact);
}

json assessSpace(MixImpl& m, std::vector<SpaceFinding>& findings, std::vector<std::string>& suggestions) {
    Assessor a(m, findings, suggestions);
    return a.run();
}

}  // namespace as::analysis
