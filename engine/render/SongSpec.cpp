#include "render/SongSpec.h"

#include "analysis/Profiles.h"

#include <algorithm>
#include <cmath>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>

namespace as {
namespace {

[[noreturn]] void fail(const std::string& path, const std::string& message) {
    throw ConfigError(path + ": " + message);
}

void allowOnly(const json& object, const std::string& path, std::initializer_list<const char*> keys) {
    if (!object.is_object()) fail(path, "must be an object");
    for (auto it = object.begin(); it != object.end(); ++it) {
        bool known = false;
        for (const char* k : keys) known = known || it.key() == k;
        if (!known) {
            std::ostringstream list;
            bool first = true;
            for (const char* k : keys) { list << (first ? "" : ", ") << k; first = false; }
            fail(path, "unknown key '" + it.key() + "' (allowed: " + list.str() + ")");
        }
    }
}

double number(const json& object, const char* key, const std::string& path, double lo, double hi,
              std::optional<double> fallback = std::nullopt) {
    if (!object.contains(key)) {
        if (fallback) return *fallback;
        fail(path, std::string("missing required '") + key + "'");
    }
    const json& v = object.at(key);
    if (!v.is_number()) fail(path + "." + key, "must be a number");
    const double d = v.get<double>();
    if (!std::isfinite(d) || d < lo || d > hi) {
        std::ostringstream msg;
        msg << "must be in " << lo << ".." << hi << ", got " << d;
        fail(path + "." + key, msg.str());
    }
    return d;
}

std::string string(const json& object, const char* key, const std::string& path,
                   std::optional<std::string> fallback = std::nullopt) {
    if (!object.contains(key)) {
        if (fallback) return *fallback;
        fail(path, std::string("missing required '") + key + "'");
    }
    if (!object.at(key).is_string()) fail(path + "." + key, "must be a string");
    return object.at(key).get<std::string>();
}

bool validId(const std::string& id) {
    if (id.empty() || id.size() > 48) return false;
    return std::all_of(id.begin(), id.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
    });
}

Curve parseCurve(const json& v, const std::string& path) {
    if (!v.is_string()) fail(path, "curve must be a string");
    const auto s = v.get<std::string>();
    if (s == "linear") return Curve::Linear;
    if (s == "exp") return Curve::Exp;
    if (s == "smooth") return Curve::Smooth;
    if (s == "step") return Curve::Step;
    fail(path, "curve must be linear|exp|smooth|step, got '" + s + "'");
}

std::vector<FxSpec> parseFx(const json& node, const std::string& path) {
    std::vector<FxSpec> chain;
    if (!node.contains("fx")) return chain;
    const json& fx = node.at("fx");
    if (!fx.is_array()) fail(path + ".fx", "must be an array");
    for (std::size_t i = 0; i < fx.size(); ++i) {
        const std::string p = path + ".fx[" + std::to_string(i) + "]";
        allowOnly(fx[i], p, {"type", "params", "sidechain"});
        FxSpec spec;
        spec.path = p;
        spec.type = string(fx[i], "type", p);
        if (fx[i].contains("params")) {
            if (!fx[i].at("params").is_object()) fail(p + ".params", "must be an object");
            spec.params = fx[i].at("params");
        }
        if (fx[i].contains("sidechain")) spec.sidechain = string(fx[i], "sidechain", p);
        chain.push_back(std::move(spec));
    }
    return chain;
}

std::vector<AutomationLane> parseAutomation(const json& node, const std::string& path) {
    std::vector<AutomationLane> lanes;
    if (!node.contains("automation")) return lanes;
    const json& a = node.at("automation");
    if (!a.is_array()) fail(path + ".automation", "must be an array");
    for (std::size_t i = 0; i < a.size(); ++i) {
        const std::string p = path + ".automation[" + std::to_string(i) + "]";
        allowOnly(a[i], p, {"target", "points"});
        AutomationLane lane;
        lane.path = p;
        lane.target = string(a[i], "target", p);
        if (!a[i].contains("points") || !a[i].at("points").is_array() || a[i].at("points").empty()) {
            fail(p + ".points", "must be a non-empty array");
        }
        const json& pts = a[i].at("points");
        for (std::size_t k = 0; k < pts.size(); ++k) {
            const std::string pp = p + ".points[" + std::to_string(k) + "]";
            const json& pt = pts[k];
            if (!pt.is_array() || pt.size() < 2 || pt.size() > 3 || !pt[0].is_number() || !pt[1].is_number()) {
                fail(pp, "must be [beat, value] or [beat, value, curve]");
            }
            AutomationPoint point;
            point.beat = pt[0].get<double>();
            point.value = pt[1].get<double>();
            if (!std::isfinite(point.beat) || !std::isfinite(point.value) || point.beat < 0) {
                fail(pp, "beat must be >= 0 and values finite");
            }
            if (pt.size() == 3) point.curve = parseCurve(pt[2], pp);
            if (!lane.points.empty() && point.beat <= lane.points.back().beat) {
                fail(pp, "beats must be strictly increasing");
            }
            if (point.curve == Curve::Exp && !lane.points.empty() &&
                (point.value <= 0 || lane.points.back().value <= 0)) {
                fail(pp, "'exp' curve needs strictly positive values on both ends");
            }
            lane.points.push_back(point);
        }
        lanes.push_back(std::move(lane));
    }
    return lanes;
}

// ---- modulators

constexpr double kBig = 1e9;          // sanity bound of free-valued mapping numbers
constexpr double kMinRateBeats = 1.0 / 1024.0, kMaxRateBeats = 1024.0;
constexpr double kMinRateHz = 0.001, kMaxRateHz = 50.0;  // updated every 32 samples: no audio-rate modulation
constexpr double kMaxEnvBeats = 1024.0, kMaxFollowMs = 10000.0, kMaxFollowGainDb = 48.0;
constexpr double kMaxExpDepthOct = 10.0, kMinPositive = 1e-6;
constexpr std::size_t kMaxModulators = 64, kMaxSteps = 1024;

LfoShape parseShape(const std::string& s, const std::string& path) {
    if (s == "sine") return LfoShape::Sine;
    if (s == "triangle") return LfoShape::Triangle;
    if (s == "saw") return LfoShape::Saw;
    if (s == "ramp") return LfoShape::Ramp;
    if (s == "square") return LfoShape::Square;
    if (s == "random") return LfoShape::Random;
    if (s == "smoothrandom") return LfoShape::SmoothRandom;
    fail(path, "must be sine|triangle|saw|ramp|square|random|smoothrandom, got '" + s + "'");
}

void parseSource(const json& src, const std::string& sp, ModulatorSpec& m) {
    if (!src.is_object()) fail(sp, "must be an object {\"type\": \"lfo|steps|follow|envelope|random\", ...}");
    const std::string type = string(src, "type", sp);
    if (type == "lfo") {
        allowOnly(src, sp, {"type", "shape", "rateBeats", "rateHz", "phase", "retrigger"});
        m.source = ModSource::Lfo;
        m.shape = parseShape(string(src, "shape", sp), sp + ".shape");
        const bool beats = src.contains("rateBeats"), hz = src.contains("rateHz");
        if (beats == hz) fail(sp, "needs exactly one of 'rateBeats' (cycle length in beats, on the song grid) or 'rateHz'");
        if (beats) m.rateBeats = number(src, "rateBeats", sp, kMinRateBeats, kMaxRateBeats);
        else m.rateHz = number(src, "rateHz", sp, kMinRateHz, kMaxRateHz);
        m.phase = number(src, "phase", sp, 0.0, 1.0, 0.0);
        const std::string re = string(src, "retrigger", sp, std::string("none"));
        if (re != "none" && re != "note") fail(sp + ".retrigger", "must be none|note, got '" + re + "'");
        m.retrigger = re == "note";
    } else if (type == "steps") {
        allowOnly(src, sp, {"type", "values", "stepBeats", "glide", "loop"});
        m.source = ModSource::Steps;
        if (!src.contains("values") || !src.at("values").is_array() || src.at("values").empty()) {
            fail(sp + ".values", "must be a non-empty array of numbers");
        }
        const json& v = src.at("values");
        if (v.size() > kMaxSteps) fail(sp + ".values", "at most 1024 steps");
        for (std::size_t k = 0; k < v.size(); ++k) {
            if (!v[k].is_number() || !std::isfinite(v[k].get<double>())) {
                fail(sp + ".values[" + std::to_string(k) + "]", "must be a finite number");
            }
            m.values.push_back(v[k].get<double>());
        }
        m.stepBeats = number(src, "stepBeats", sp, kMinRateBeats, kMaxRateBeats);
        m.glide = number(src, "glide", sp, 0.0, 1.0, 0.0);
        if (src.contains("loop")) {
            if (!src.at("loop").is_boolean()) fail(sp + ".loop", "must be a boolean");
            m.loop = src.at("loop").get<bool>();
        }
    } else if (type == "follow") {
        allowOnly(src, sp, {"type", "node", "attackMs", "releaseMs", "gainDb"});
        m.source = ModSource::Follow;
        m.followNode = string(src, "node", sp);
        m.attackMs = number(src, "attackMs", sp, 0.0, kMaxFollowMs, 5.0);
        m.releaseMs = number(src, "releaseMs", sp, 0.0, kMaxFollowMs, 120.0);
        m.gainDb = number(src, "gainDb", sp, -kMaxFollowGainDb, kMaxFollowGainDb, 0.0);
    } else if (type == "envelope") {
        allowOnly(src, sp, {"type", "attackBeats", "decayBeats", "sustain", "releaseBeats", "trigger"});
        m.source = ModSource::Envelope;
        m.attackBeats = number(src, "attackBeats", sp, 0.0, kMaxEnvBeats, 0.0);
        m.decayBeats = number(src, "decayBeats", sp, 0.0, kMaxEnvBeats, 0.5);
        m.sustain = number(src, "sustain", sp, 0.0, 1.0, 0.0);
        m.releaseBeats = number(src, "releaseBeats", sp, 0.0, kMaxEnvBeats, 0.25);
        const std::string trig = string(src, "trigger", sp, std::string("note"));
        m.trigger = trig == "note" ? std::string() : trig;
    } else if (type == "random") {
        allowOnly(src, sp, {"type", "rateBeats", "smooth"});
        m.source = ModSource::Random;
        m.rateBeats = number(src, "rateBeats", sp, kMinRateBeats, kMaxRateBeats);
        m.smooth = number(src, "smooth", sp, 0.0, 1.0, 0.0);
    } else {
        fail(sp + ".type", "must be lfo|steps|follow|envelope|random, got '" + type + "'");
    }
}

// Reads the numeric mapping field `key` with the range modFieldRange() gives for it.
double mappingField(const json& object, const char* key, const std::string& path, const ModulatorSpec& m, ModField f) {
    double lo = 0.0, hi = 0.0;
    modFieldRange(m, f, lo, hi);
    return number(object, key, path, lo, hi);
}

std::vector<ModulatorSpec> parseModulators(const json& node, const std::string& path) {
    std::vector<ModulatorSpec> mods;
    if (!node.contains("modulators")) return mods;
    const json& a = node.at("modulators");
    if (!a.is_array()) fail(path + ".modulators", "must be an array");
    if (a.size() > kMaxModulators) fail(path + ".modulators", "at most 64 modulators per node");
    for (std::size_t i = 0; i < a.size(); ++i) {
        const std::string p = path + ".modulators[" + std::to_string(i) + "]";
        const json& j = a[i];
        allowOnly(j, p, {"target", "source", "mode", "min", "max", "depth", "base", "curve", "startBeat", "endBeat"});
        ModulatorSpec m;
        m.path = p;
        m.target = string(j, "target", p);
        if (m.target.rfind("mod.", 0) == 0) {
            fail(p + ".target", "a modulator cannot target another modulator; automate 'mod.<index>.<field>' instead");
        }
        const std::string mode = string(j, "mode", p);
        if (mode != "absolute" && mode != "offset") fail(p + ".mode", "must be absolute|offset, got '" + mode + "'");
        m.offset = mode == "offset";
        const std::string curve = string(j, "curve", p, std::string("linear"));
        if (curve != "linear" && curve != "exp") fail(p + ".curve", "must be linear|exp, got '" + curve + "'");
        m.expCurve = curve == "exp";
        if (!j.contains("source")) fail(p, "missing required 'source'");
        parseSource(j.at("source"), p + ".source", m);

        if (!m.offset) {
            if (j.contains("depth")) fail(p + ".depth", "is only for mode 'offset' (absolute mode maps the source onto min..max)");
            if (m.source == ModSource::Steps) {
                if (j.contains("min") || j.contains("max")) {
                    fail(p, "steps in mode 'absolute' take their 'values' in target units; remove 'min'/'max'");
                }
                for (std::size_t k = 0; k < m.values.size(); ++k) {
                    if (m.expCurve && m.values[k] <= 0) {
                        fail(p + ".source.values[" + std::to_string(k) + "]", "curve 'exp' needs values > 0");
                    }
                }
            } else {
                m.min = mappingField(j, "min", p, m, ModField::Min);
                m.max = mappingField(j, "max", p, m, ModField::Max);
            }
        } else {
            if (j.contains("min") || j.contains("max")) {
                fail(p, "'min'/'max' are for mode 'absolute'; mode 'offset' adds source * 'depth'");
            }
            m.depth = mappingField(j, "depth", p, m, ModField::Depth);
            if (m.source == ModSource::Steps) {
                for (std::size_t k = 0; k < m.values.size(); ++k) {
                    if (m.values[k] < -1.0 || m.values[k] > 1.0) {
                        fail(p + ".source.values[" + std::to_string(k) + "]",
                             "offset-mode steps must be in -1..1 (they are scaled by 'depth')");
                    }
                }
            }
        }
        if (j.contains("base")) {
            m.base = 0.0;  // present: makes the field apply for modFieldRange
            m.base = mappingField(j, "base", p, m, ModField::Base);
        }
        if (j.contains("startBeat")) m.startBeat = number(j, "startBeat", p, 0.0, 100000.0);
        if (j.contains("endBeat")) m.endBeat = number(j, "endBeat", p, 0.0, 100000.0);
        if (m.startBeat && m.endBeat && *m.endBeat <= *m.startBeat) fail(p + ".endBeat", "must be > startBeat");
        mods.push_back(std::move(m));
    }
    return mods;
}

void parseMix(const json& node, const std::string& path, NodeSpec& spec) {
    spec.gainDb = static_cast<float>(number(node, "gainDb", path, -120.0, 24.0, 0.0));
    spec.pan = static_cast<float>(number(node, "pan", path, -1.0, 1.0, 0.0));
    if (node.contains("mute")) {
        if (!node.at("mute").is_boolean()) fail(path + ".mute", "must be a boolean");
        spec.mute = node.at("mute").get<bool>();
    }
    if (node.contains("sends")) {
        const json& s = node.at("sends");
        if (!s.is_object()) fail(path + ".sends", "must be an object {busId: dB}");
        for (auto it = s.begin(); it != s.end(); ++it) {
            if (!it.value().is_number()) fail(path + ".sends." + it.key(), "must be a number (dB)");
            const double db = it.value().get<double>();
            if (!std::isfinite(db) || db < -120 || db > 24) fail(path + ".sends." + it.key(), "must be in -120..24 dB");
            spec.sends.emplace_back(it.key(), static_cast<float>(db));
        }
    }
}

// "tempoMap": [[beat, bpm], [beat, bpm, "linear"|"smooth"|"step"], ...] (docs/RENDER_FORMAT.md "Tempo map").
constexpr double kMinMapBpm = 1.0, kMaxMapBpm = 1000.0;
constexpr std::size_t kMaxTempoPoints = 100000, kMaxMeterPoints = 10000;

std::vector<TempoPoint> parseTempoMap(const json& a, const std::string& path) {
    if (!a.is_array() || a.empty()) fail(path, "must be a non-empty array of [beat, bpm] / [beat, bpm, curve] points");
    if (a.size() > kMaxTempoPoints) fail(path, "at most 100000 points");
    std::vector<TempoPoint> points;
    for (std::size_t k = 0; k < a.size(); ++k) {
        const std::string pp = path + "[" + std::to_string(k) + "]";
        const json& pt = a[k];
        if (!pt.is_array() || pt.size() < 2 || pt.size() > 3 || !pt[0].is_number() || !pt[1].is_number()) {
            fail(pp, "must be [beat, bpm] or [beat, bpm, curve]");
        }
        TempoPoint p;
        p.beat = pt[0].get<double>();
        p.bpm = pt[1].get<double>();
        if (!std::isfinite(p.beat) || p.beat < 0 || p.beat > 100000) fail(pp, "beat must be in 0..100000");
        if (!std::isfinite(p.bpm) || p.bpm < kMinMapBpm || p.bpm > kMaxMapBpm) {
            std::ostringstream msg;
            msg << "bpm must be in 1..1000, got " << p.bpm;
            fail(pp, msg.str());
        }
        if (pt.size() == 3) {
            if (!pt[2].is_string()) fail(pp, "curve must be a string");
            const auto c = pt[2].get<std::string>();
            if (c == "linear") p.curve = TempoCurve::Linear;
            else if (c == "smooth") p.curve = TempoCurve::Smooth;
            else if (c == "step") p.curve = TempoCurve::Step;
            else fail(pp, "tempo curve must be linear|smooth|step, got '" + c + "'");
        }
        if (k == 0 && p.beat != 0.0) fail(pp, "the first point must be at beat 0 (the tempo the song starts with)");
        if (k > 0 && p.beat <= points.back().beat) fail(pp, "beats must be strictly increasing");
        points.push_back(p);
    }
    return points;  // (points after lengthBeats are allowed: they shape the tail)
}

// "meter": [[beat, numerator, denominator], ...]: bars for the report (bar numbers, per-bar timeline).
std::vector<MeterPoint> parseMeter(const json& a, const std::string& path) {
    if (!a.is_array() || a.empty()) fail(path, "must be a non-empty array of [beat, numerator, denominator]");
    if (a.size() > kMaxMeterPoints) fail(path, "at most 10000 entries");
    std::vector<MeterPoint> points;
    for (std::size_t k = 0; k < a.size(); ++k) {
        const std::string pp = path + "[" + std::to_string(k) + "]";
        const json& pt = a[k];
        if (!pt.is_array() || pt.size() != 3 || !pt[0].is_number() || !pt[1].is_number() || !pt[2].is_number()) {
            fail(pp, "must be [beat, numerator, denominator], e.g. [32, 3, 4] for 3/4 from beat 32");
        }
        const double beat = pt[0].get<double>(), n = pt[1].get<double>(), d = pt[2].get<double>();
        if (!std::isfinite(beat) || beat < 0 || beat > 100000) fail(pp, "beat must be in 0..100000");
        if (n != std::floor(n) || n < 1 || n > 64) fail(pp, "numerator must be an integer 1..64");
        if (d != 1 && d != 2 && d != 4 && d != 8 && d != 16 && d != 32) fail(pp, "denominator must be 1, 2, 4, 8, 16 or 32");
        points.push_back({beat, static_cast<int>(n), static_cast<int>(d)});
    }
    try {
        MeterMap check(points);
    } catch (const std::invalid_argument& e) {
        std::string msg = e.what();
        if (msg.rfind("meter: ", 0) == 0) msg = msg.substr(7);
        fail(path, msg);
    }
    return points;
}

// "analysis": {"profile": "synthwave", "loudness": [-12, -9]}, both optional.
AnalysisSpec parseAnalysis(const json& a, const std::string& path) {
    allowOnly(a, path, {"profile", "loudness", "silentNotes"});
    AnalysisSpec spec;
    if (a.contains("profile")) {
        spec.profile = string(a, "profile", path);
        if (!analysis::findAnalysisProfile(spec.profile)) {
            fail(path + ".profile",
                 "unknown analysis profile '" + spec.profile + "' (profiles: " + analysis::analysisProfileNames() + ")");
        }
    }
    if (a.contains("loudness")) {
        const json& l = a.at("loudness");
        const std::string lp = path + ".loudness";
        if (!l.is_array() || l.size() != 2 || !l[0].is_number() || !l[1].is_number()) {
            fail(lp, "must be [minLufs, maxLufs], e.g. [-12, -9]");
        }
        const double lo = l[0].get<double>(), hi = l[1].get<double>();
        if (!std::isfinite(lo) || !std::isfinite(hi) || lo < -60.0 || hi > 0.0) fail(lp, "LUFS values must be in -60..0");
        if (!(lo < hi)) fail(lp, "min must be < max");
        spec.loudness = std::make_pair(lo, hi);
    }
    if (a.contains("silentNotes")) {
        // [{"track", "kind", "pitches", "count", "beats", "message"}]: written by the compiler (agentsound/silent_notes.py)
        const json& list = a.at("silentNotes");
        const std::string lp = path + ".silentNotes";
        if (!list.is_array()) fail(lp, "must be an array of {track, kind, pitches, count, beats, message}");
        for (std::size_t i = 0; i < list.size(); ++i) {
            const json& e = list[i];
            const std::string ep = lp + "[" + std::to_string(i) + "]";
            allowOnly(e, ep, {"track", "kind", "pitches", "count", "beats", "message"});
            SilentNoteHint h;
            h.track = string(e, "track", ep);
            h.kind = string(e, "kind", ep);
            if (h.kind != "no_sound" && h.kind != "muted_layers") fail(ep + ".kind", "must be 'no_sound' or 'muted_layers'");
            h.message = string(e, "message", ep);
            h.count = static_cast<int>(number(e, "count", ep, 1, 1e9));
            if (!e.contains("pitches") || !e.at("pitches").is_array() || e.at("pitches").empty())
                fail(ep + ".pitches", "must be a non-empty array of MIDI notes");
            for (const json& p : e.at("pitches")) {
                if (!p.is_number_integer() || p.get<int>() < 0 || p.get<int>() > 127) fail(ep + ".pitches", "must hold MIDI notes 0..127");
                h.pitches.push_back(p.get<int>());
            }
            if (e.contains("beats")) {
                if (!e.at("beats").is_array()) fail(ep + ".beats", "must be an array of beats");
                for (const json& b : e.at("beats")) {
                    if (!b.is_number() || !std::isfinite(b.get<double>()) || b.get<double>() < 0.0) fail(ep + ".beats", "must hold beats >= 0");
                    h.beats.push_back(b.get<double>());
                }
            }
            spec.silentNotes.push_back(std::move(h));
        }
    }
    return spec;
}

}  // namespace

const char* modFieldName(ModField field) {
    switch (field) {
        case ModField::Depth: return "depth";
        case ModField::Min: return "min";
        case ModField::Max: return "max";
        case ModField::Base: return "base";
        case ModField::RateBeats: return "rateBeats";
        case ModField::RateHz: return "rateHz";
        case ModField::Phase: return "phase";
        case ModField::Glide: return "glide";
        case ModField::Smooth: return "smooth";
        case ModField::AttackMs: return "attackMs";
        case ModField::ReleaseMs: return "releaseMs";
        case ModField::GainDb: return "gainDb";
        case ModField::AttackBeats: return "attackBeats";
        case ModField::DecayBeats: return "decayBeats";
        case ModField::Sustain: return "sustain";
        case ModField::ReleaseBeats: return "releaseBeats";
    }
    return "?";
}

bool modFieldRange(const ModulatorSpec& m, ModField field, double& lo, double& hi) {
    auto set = [&](double a, double b) { lo = a; hi = b; return true; };
    switch (field) {
        case ModField::Depth:
            if (!m.offset) return false;
            return m.expCurve ? set(-kMaxExpDepthOct, kMaxExpDepthOct) : set(-kBig, kBig);
        case ModField::Min:
        case ModField::Max:
            if (m.offset || m.source == ModSource::Steps) return false;
            return m.expCurve ? set(kMinPositive, kBig) : set(-kBig, kBig);
        case ModField::Base:
            if (!m.base) return false;
            return (m.offset && m.expCurve) ? set(kMinPositive, kBig) : set(-kBig, kBig);
        case ModField::RateBeats:
            if (!(m.source == ModSource::Random || (m.source == ModSource::Lfo && m.rateBeats > 0))) return false;
            return set(kMinRateBeats, kMaxRateBeats);
        case ModField::RateHz:
            if (!(m.source == ModSource::Lfo && m.rateHz > 0)) return false;
            return set(kMinRateHz, kMaxRateHz);
        case ModField::Phase: return m.source == ModSource::Lfo && set(0.0, 1.0);
        case ModField::Glide: return m.source == ModSource::Steps && set(0.0, 1.0);
        case ModField::Smooth: return m.source == ModSource::Random && set(0.0, 1.0);
        case ModField::AttackMs:
        case ModField::ReleaseMs: return m.source == ModSource::Follow && set(0.0, kMaxFollowMs);
        case ModField::GainDb: return m.source == ModSource::Follow && set(-kMaxFollowGainDb, kMaxFollowGainDb);
        case ModField::AttackBeats:
        case ModField::DecayBeats:
        case ModField::ReleaseBeats: return m.source == ModSource::Envelope && set(0.0, kMaxEnvBeats);
        case ModField::Sustain: return m.source == ModSource::Envelope && set(0.0, 1.0);
    }
    return false;
}

double modFieldValue(const ModulatorSpec& m, ModField field) {
    switch (field) {
        case ModField::Depth: return m.depth;
        case ModField::Min: return m.min;
        case ModField::Max: return m.max;
        case ModField::Base: return m.base.value_or(0.0);
        case ModField::RateBeats: return m.rateBeats;
        case ModField::RateHz: return m.rateHz;
        case ModField::Phase: return m.phase;
        case ModField::Glide: return m.glide;
        case ModField::Smooth: return m.smooth;
        case ModField::AttackMs: return m.attackMs;
        case ModField::ReleaseMs: return m.releaseMs;
        case ModField::GainDb: return m.gainDb;
        case ModField::AttackBeats: return m.attackBeats;
        case ModField::DecayBeats: return m.decayBeats;
        case ModField::Sustain: return m.sustain;
        case ModField::ReleaseBeats: return m.releaseBeats;
    }
    return 0.0;
}

TempoMap SongSpec::makeTempoMap() const {
    if (tempoMap.empty()) return TempoMap(tempo, static_cast<double>(sampleRate));
    try {
        return TempoMap(tempoMap, static_cast<double>(sampleRate));
    } catch (const std::invalid_argument& e) {  // a hand-built SongSpec (parseSong validates)
        throw ConfigError(std::string("$.tempoMap: ") + e.what());
    }
}

MeterMap SongSpec::makeMeterMap() const {
    if (meter.empty()) return MeterMap();
    try {
        return MeterMap(meter);
    } catch (const std::invalid_argument& e) {
        throw ConfigError(std::string("$.meter: ") + e.what());
    }
}

SongTiming parseTiming(const json& doc) {
    const std::string root = "$";
    if (!doc.is_object()) fail(root, "must be an object");
    SongTiming t;
    const double sr = number(doc, "sampleRate", root, 8000, 384000, 48000.0);
    t.sampleRate = static_cast<int>(sr);
    if (doc.contains("tempoMap")) {
        t.tempoMap = parseTempoMap(doc.at("tempoMap"), root + ".tempoMap");
        t.tempo = t.tempoMap.front().bpm;
    } else {
        t.tempo = number(doc, "tempo", root, 1, 1000);
    }
    if (doc.contains("meter")) t.meter = parseMeter(doc.at("meter"), root + ".meter");
    return t;
}

double SongSpec::beatToSeconds(double beat) const {
    return tempoMap.empty() ? beat * 60.0 / tempo : makeTempoMap().secondsAt(beat);
}

SongSpec parseSong(const json& doc) {
    const std::string root = "$";
    allowOnly(doc, root, {"format", "version", "title", "sampleRate", "tempo", "tempoMap", "meter", "lengthBeats",
                          "tailSeconds", "seed", "sections", "tracks", "buses", "master", "export", "analysis"});
    if (string(doc, "format", root) != "agentsound.render") fail(root + ".format", "must be 'agentsound.render'");
    if (number(doc, "version", root, 1, 1) != 1) fail(root + ".version", "must be 1");

    SongSpec song;
    song.title = string(doc, "title", root, std::string("Untitled"));
    const double sr = number(doc, "sampleRate", root, 44100, 96000, 48000.0);
    if (sr != 44100 && sr != 48000 && sr != 96000) fail(root + ".sampleRate", "must be 44100, 48000 or 96000");
    song.sampleRate = static_cast<int>(sr);
    song.lengthBeats = number(doc, "lengthBeats", root, 0.25, 100000);
    if (doc.contains("tempo") == doc.contains("tempoMap")) {
        fail(root, doc.contains("tempo") ? "give either 'tempo' (constant BPM) or 'tempoMap' (changing tempo), not both"
                                         : "missing required 'tempo' (BPM) or 'tempoMap' ([[beat, bpm], ...])");
    }
    if (doc.contains("tempo")) {
        song.tempo = number(doc, "tempo", root, 30, 300);
    } else {
        song.tempoMap = parseTempoMap(doc.at("tempoMap"), root + ".tempoMap");
        song.tempo = song.tempoMap.front().bpm;
    }
    if (doc.contains("meter")) song.meter = parseMeter(doc.at("meter"), root + ".meter");
    song.tailSeconds = number(doc, "tailSeconds", root, 0, 30, 4.0);
    song.seed = static_cast<std::uint64_t>(number(doc, "seed", root, 0, 4294967295.0, 1.0));

    if (doc.contains("sections")) {
        const json& secs = doc.at("sections");
        if (!secs.is_array()) fail(root + ".sections", "must be an array");
        for (std::size_t i = 0; i < secs.size(); ++i) {
            const std::string p = root + ".sections[" + std::to_string(i) + "]";
            allowOnly(secs[i], p, {"name", "startBeat", "endBeat"});
            SectionSpec s;
            s.name = string(secs[i], "name", p);
            s.startBeat = number(secs[i], "startBeat", p, 0, 100000);
            s.endBeat = number(secs[i], "endBeat", p, 0, 100000);
            if (s.endBeat <= s.startBeat) fail(p, "endBeat must be > startBeat");
            song.sections.push_back(s);
        }
    }

    std::set<std::string> ids;
    auto claimId = [&](const std::string& id, const std::string& p) {
        if (!validId(id)) fail(p + ".id", "must match [a-z0-9_-]{1,48}, got '" + id + "'");
        if (id == "master") fail(p + ".id", "'master' is reserved");
        if (!ids.insert(id).second) fail(p + ".id", "duplicate id '" + id + "'");
    };

    if (!doc.contains("tracks") || !doc.at("tracks").is_array() || doc.at("tracks").empty()) {
        fail(root + ".tracks", "must be a non-empty array");
    }
    const json& tracks = doc.at("tracks");
    for (std::size_t i = 0; i < tracks.size(); ++i) {
        const std::string p = root + ".tracks[" + std::to_string(i) + "]";
        const json& t = tracks[i];
        allowOnly(t, p, {"id", "instrument", "fx", "gainDb", "pan", "mute", "output", "sends", "notes", "automation",
                         "modulators"});
        NodeSpec n;
        n.kind = NodeSpec::Kind::Track;
        n.path = p;
        n.id = string(t, "id", p);
        claimId(n.id, p);
        if (!t.contains("instrument")) fail(p, "missing required 'instrument'");
        allowOnly(t.at("instrument"), p + ".instrument", {"type", "params"});
        n.instrumentType = string(t.at("instrument"), "type", p + ".instrument");
        if (t.at("instrument").contains("params")) {
            if (!t.at("instrument").at("params").is_object()) fail(p + ".instrument.params", "must be an object");
            n.instrumentParams = t.at("instrument").at("params");
        }
        n.fx = parseFx(t, p);
        parseMix(t, p, n);
        n.output = string(t, "output", p, std::string("master"));
        if (t.contains("notes")) {
            const json& notes = t.at("notes");
            if (!notes.is_array()) fail(p + ".notes", "must be an array");
            n.notes.reserve(notes.size());
            for (std::size_t k = 0; k < notes.size(); ++k) {
                const json& nt = notes[k];
                const std::string np = p + ".notes[" + std::to_string(k) + "]";
                if (!nt.is_array() || nt.size() != 4) fail(np, "must be [startBeat, durationBeats, pitch, velocity]");
                for (int f = 0; f < 4; ++f) if (!nt[f].is_number()) fail(np, "all four fields must be numbers");
                NoteSpec note{nt[0].get<double>(), nt[1].get<double>(), 0, 0};
                const double pitch = nt[2].get<double>(), vel = nt[3].get<double>();
                if (!std::isfinite(note.startBeat) || note.startBeat < 0 || note.startBeat >= song.lengthBeats) {
                    fail(np, "startBeat must be in [0, lengthBeats)");
                }
                if (!std::isfinite(note.durationBeats) || note.durationBeats <= 0) fail(np, "durationBeats must be > 0");
                if (pitch != std::floor(pitch) || pitch < 0 || pitch > 127) fail(np, "pitch must be an integer 0..127");
                if (vel != std::floor(vel) || vel < 1 || vel > 127) fail(np, "velocity must be an integer 1..127");
                note.pitch = static_cast<int>(pitch);
                note.velocity = static_cast<int>(vel);
                n.notes.push_back(note);
            }
        }
        n.automation = parseAutomation(t, p);
        n.modulators = parseModulators(t, p);
        song.nodes.push_back(std::move(n));
    }

    if (doc.contains("buses")) {
        const json& buses = doc.at("buses");
        if (!buses.is_array()) fail(root + ".buses", "must be an array");
        for (std::size_t i = 0; i < buses.size(); ++i) {
            const std::string p = root + ".buses[" + std::to_string(i) + "]";
            const json& b = buses[i];
            allowOnly(b, p, {"id", "fx", "gainDb", "pan", "mute", "output", "sends", "automation", "modulators"});
            NodeSpec n;
            n.kind = NodeSpec::Kind::Bus;
            n.path = p;
            n.id = string(b, "id", p);
            claimId(n.id, p);
            n.fx = parseFx(b, p);
            parseMix(b, p, n);
            n.output = string(b, "output", p, std::string("master"));
            n.automation = parseAutomation(b, p);
            n.modulators = parseModulators(b, p);
            song.nodes.push_back(std::move(n));
        }
    }

    NodeSpec master;
    master.kind = NodeSpec::Kind::Master;
    master.id = "master";
    master.path = root + ".master";
    master.output.clear();
    if (doc.contains("master")) {
        const json& m = doc.at("master");
        allowOnly(m, master.path, {"fx", "gainDb", "automation", "modulators"});
        master.fx = parseFx(m, master.path);
        master.gainDb = static_cast<float>(number(m, "gainDb", master.path, -120.0, 24.0, 0.0));
        master.automation = parseAutomation(m, master.path);
        master.modulators = parseModulators(m, master.path);
    }
    song.nodes.push_back(std::move(master));

    if (doc.contains("export")) {
        const json& e = doc.at("export");
        allowOnly(e, root + ".export", {"stems", "bitDepth"});
        if (e.contains("stems")) {
            if (!e.at("stems").is_boolean()) fail(root + ".export.stems", "must be a boolean");
            song.exportStems = e.at("stems").get<bool>();
        }
        const double bits = number(e, "bitDepth", root + ".export", 16, 32, 24.0);
        if (bits != 16 && bits != 24 && bits != 32) fail(root + ".export.bitDepth", "must be 16, 24 or 32");
        song.bitDepth = static_cast<int>(bits);
    }

    if (doc.contains("analysis")) song.analysis = parseAnalysis(doc.at("analysis"), root + ".analysis");

    // Reference checks: outputs, sends, sidechains, modulator sources.
    auto isBus = [&](const std::string& id) {
        return std::any_of(song.nodes.begin(), song.nodes.end(),
                           [&](const NodeSpec& n) { return n.kind == NodeSpec::Kind::Bus && n.id == id; });
    };
    auto isTrack = [&](const std::string& id) {
        return std::any_of(song.nodes.begin(), song.nodes.end(),
                           [&](const NodeSpec& n) { return n.kind == NodeSpec::Kind::Track && n.id == id; });
    };
    for (std::size_t i = 0; i < song.analysis.silentNotes.size(); ++i) {
        const std::string& t = song.analysis.silentNotes[i].track;
        if (!isTrack(t)) fail(root + ".analysis.silentNotes[" + std::to_string(i) + "].track", "'" + t + "' is not a track id");
    }
    for (const auto& n : song.nodes) {
        if (n.kind != NodeSpec::Kind::Master && n.output != "master" && !isBus(n.output)) {
            fail(n.path + ".output", "'" + n.output + "' is not a bus id or 'master'");
        }
        if (n.output == n.id) fail(n.path + ".output", "a bus cannot output to itself");
        for (const auto& [bus, db] : n.sends) {
            if (!isBus(bus)) fail(n.path + ".sends." + bus, "'" + bus + "' is not a bus id");
            if (bus == n.id) fail(n.path + ".sends." + bus, "a bus cannot send to itself");
        }
        for (const auto& fx : n.fx) {
            if (fx.sidechain.empty()) continue;
            if (!ids.count(fx.sidechain)) fail(fx.path + ".sidechain", "'" + fx.sidechain + "' is not a track or bus id");
            if (fx.sidechain == n.id) fail(fx.path + ".sidechain", "a node cannot key its own effect");
        }
        const bool track = n.kind == NodeSpec::Kind::Track;
        const std::string noNotes = n.kind == NodeSpec::Kind::Bus ? "a bus has no notes" : "the master has no notes";
        for (const auto& m : n.modulators) {
            const std::string sp = m.path + ".source";
            if (m.source == ModSource::Follow) {
                if (m.followNode == "master") fail(sp + ".node", "'master' cannot be followed (every node feeds it)");
                if (!ids.count(m.followNode)) fail(sp + ".node", "'" + m.followNode + "' is not a track or bus id");
                if (m.followNode == n.id) fail(sp + ".node", "a node cannot follow its own output");
            }
            if (m.source == ModSource::Envelope) {
                if (m.trigger.empty() && !track) {
                    fail(sp + ".trigger", "'note' needs a track (" + noNotes + "); name the track whose notes trigger it");
                }
                if (!m.trigger.empty() && !isTrack(m.trigger)) {
                    fail(sp + ".trigger", "'" + m.trigger + "' is not a track id (or 'note' for this track's notes)");
                }
            }
            if (m.retrigger && !track) fail(sp + ".retrigger", "'note' needs a track (" + noNotes + ")");
        }
    }
    return song;
}

}  // namespace as
