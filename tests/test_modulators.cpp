// Modulator tests: every source (lfo, steps, follow, envelope, random), both mappings, windows,
// 'mod.<i>.<field>' automation, clamping, preview start alignment, determinism and strict errors.
// Values are observed through RenderOptions::trace (the value written per 32-sample block).
//
// Grid used throughout: 120 BPM at 48 kHz = 24000 samples per beat = exactly 750 blocks per beat.

#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using as::json;

namespace {

int failures = 0;
constexpr double kBlocksPerBeat = 750.0;
constexpr double kPi = 3.14159265358979323846;

void check(bool ok, const std::string& what) {
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << "\n";
    if (!ok) ++failures;
}

std::string num(double v) {
    std::ostringstream s;
    s << v;
    return s.str();
}

bool near(double a, double b, double tol = 1e-9) { return std::fabs(a - b) <= tol; }

double frac(double x) { return x - std::floor(x + 1e-9) < 0 ? 0.0 : x - std::floor(x + 1e-9); }

json song(double lengthBeats = 8.0) {
    json doc = json::parse(R"({"format": "agentsound.render", "version": 1, "title": "mod test",
                               "tempo": 120, "lengthBeats": 8, "tailSeconds": 0, "seed": 3, "tracks": []})");
    doc["lengthBeats"] = lengthBeats;
    return doc;
}

json track(const std::string& id, json notes = json::array(), json params = json::object()) {
    return {{"id", id}, {"instrument", {{"type", "va"}, {"params", params}}}, {"notes", notes}};
}

json lfo(const std::string& shape, double rateBeats) {
    return {{"type", "lfo"}, {"shape", shape}, {"rateBeats", rateBeats}};
}

json absolute(const std::string& target, json source, double lo, double hi, const std::string& curve = "linear") {
    return {{"target", target}, {"source", source}, {"mode", "absolute"}, {"min", lo}, {"max", hi}, {"curve", curve}};
}

json offsetMod(const std::string& target, json source, double depth) {
    return {{"target", target}, {"source", source}, {"mode", "offset"}, {"depth", depth}};
}

struct Traced {
    std::vector<double> values;
    double firstBeat{0.0};
    double blockBeats{0.0};
    double at(double beat) const {  // value of the block starting at `beat` (must be on the block grid)
        const auto k = static_cast<long>(std::llround((beat - firstBeat) / blockBeats));
        return k >= 0 && k < static_cast<long>(values.size()) ? values[static_cast<std::size_t>(k)] : std::nan("");
    }
};

Traced trace(const json& doc, const std::string& node, const std::string& target,
             std::optional<double> from = std::nullopt, std::optional<double> to = std::nullopt) {
    as::ControlTrace tr;
    tr.node = node;
    tr.target = target;
    as::RenderOptions o;
    o.assetDir = "assets";
    o.outDir = (fs::path(".scratch") / "modulators" / "trace").string();
    o.quiet = true;
    o.analysis = false;
    o.pngs = false;
    o.fromBeat = from;
    o.toBeat = to;
    o.trace = &tr;
    as::renderSong(as::parseSong(doc), o);
    return {tr.values, tr.firstBeat, tr.blockBeats};
}

bool throwsConfig(const json& doc, const std::string& expect) {
    try {
        as::validateSong(as::parseSong(doc), "assets");
    } catch (const as::ConfigError& e) {
        const bool matched = std::string(e.what()).find(expect) != std::string::npos;
        if (!matched) std::cout << "       (message was: " << e.what() << ")\n";
        return matched;
    }
    std::cout << "       (no error thrown)\n";
    return false;
}

std::vector<char> readFile(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), {}};
}

// ------------------------------------------------------------------------------------------ lfo

void testLfoGrid() {
    std::cout << "lfo on the beat grid\n";
    json doc = song();
    json t = track("t");
    t["modulators"] = json::array({absolute("pan", lfo("ramp", 1.0), -1, 1),
                                   absolute("gainDb", lfo("sine", 2.0), -30, -6)});
    doc["tracks"].push_back(t);

    const Traced ramp = trace(doc, "t", "pan");
    check(ramp.values.size() == 6000, "one value per 32-sample block (" + std::to_string(ramp.values.size()) + ")");
    double err = 0.0;
    for (std::size_t k = 0; k < ramp.values.size(); ++k) {
        const double beat = static_cast<double>(k) / kBlocksPerBeat;
        err = std::max(err, std::fabs(ramp.values[k] - (-1.0 + 2.0 * frac(beat))));
    }
    check(err < 1e-9, "ramp rateBeats 1: value = -1 + 2*frac(beat) at every block (max err " + num(err) + ")");
    check(near(ramp.at(0.0), -1.0) && near(ramp.at(3.0), -1.0) && near(ramp.at(3.5), 0.0),
          "ramp restarts exactly on every beat");

    const Traced sine = trace(doc, "t", "gainDb");
    err = 0.0;
    for (std::size_t k = 0; k < sine.values.size(); ++k) {
        const double beat = static_cast<double>(k) / kBlocksPerBeat;
        const double u = 0.5 - 0.5 * std::cos(2.0 * kPi * beat / 2.0);
        err = std::max(err, std::fabs(sine.values[k] - (-30.0 + 24.0 * u)));
    }
    check(err < 1e-9, "sine rateBeats 2: starts at min, peaks mid-cycle (max err " + num(err) + ")");
    check(near(sine.at(1.0), -6.0) && near(sine.at(2.0), -30.0), "sine max at beat 1, min at beat 2");

    // Preview renders start mid-cycle; the renderer snaps the start down onto the song block grid.
    const Traced preview = trace(doc, "t", "pan", 1.2345, 4.0);
    err = 0.0;
    for (std::size_t k = 0; k < preview.values.size(); ++k) {
        const double beat = preview.firstBeat + static_cast<double>(k) * preview.blockBeats;
        err = std::max(err, std::fabs(preview.values[k] - (-1.0 + 2.0 * frac(beat))));
    }
    check(near(preview.firstBeat, 29600.0 / 24000.0), "preview starts on the song block grid at or before the requested beat (sample 29600 for 29628)");
    check(!preview.values.empty() && err < 1e-9, "preview (fromBeat 1.2345) stays locked to song beats (max err " + num(err) + ")");

    // rateHz: 1 Hz at 120 BPM = one cycle per 2 beats; phase shifts the cycle.
    json hz = song();
    json h = track("t");
    json src = {{"type", "lfo"}, {"shape", "ramp"}, {"rateHz", 1.0}, {"phase", 0.25}};
    h["modulators"] = json::array({absolute("pan", src, -1, 1)});
    hz["tracks"].push_back(h);
    const Traced th = trace(hz, "t", "pan");
    err = 0.0;
    for (std::size_t k = 0; k < th.values.size(); ++k) {
        const double beat = static_cast<double>(k) / kBlocksPerBeat;
        err = std::max(err, std::fabs(th.values[k] - (-1.0 + 2.0 * frac(0.25 + beat / 2.0))));
    }
    check(err < 1e-9, "rateHz 1 with phase 0.25 (max err " + num(err) + ")");

    // Shapes at quarter points, exp mapping between min and max.
    json shapes = song();
    json s = track("t");
    s["modulators"] = json::array({absolute("instrument.cutoff", lfo("triangle", 1.0), 250, 4000, "exp"),
                                   absolute("pan", lfo("saw", 1.0), -1, 1),
                                   absolute("gainDb", lfo("square", 1.0), -12, 0)});
    shapes["tracks"].push_back(s);
    const Traced tri = trace(shapes, "t", "instrument.cutoff");
    // (Checks use beats on the block grid: 1/750 beat. A quarter beat is 187.5 blocks.)
    check(near(tri.at(0.0), 250, 1e-6) && near(tri.at(0.5), 4000, 1e-6) && near(tri.at(0.2), 250 * std::pow(16.0, 0.4), 1e-6),
          "triangle + exp curve: 250 at the cycle start, 4000 mid-cycle, geometric in between");
    const Traced saw = trace(shapes, "t", "pan");
    check(near(saw.at(1.0), 1.0) && near(saw.at(1.2), 0.6) && near(saw.at(1.8), -0.6), "saw falls from +1 each cycle");
    const Traced sq = trace(shapes, "t", "gainDb");
    check(near(sq.at(2.0), 0.0) && near(sq.at(2.25), 0.0) && near(sq.at(2.5), -12.0) && near(sq.at(2.9), -12.0),
          "square is high for the first half of the cycle");
}

// ---------------------------------------------------------------------------------------- steps

void testSteps() {
    std::cout << "steps\n";
    json doc = song();
    json t = track("t");
    json seq = {{"type", "steps"}, {"values", {100, 200, 400, 800}}, {"stepBeats", 0.25}, {"glide", 0.5}};
    t["modulators"] = json::array({{{"target", "instrument.cutoff"}, {"source", seq}, {"mode", "absolute"}}});
    doc["tracks"].push_back(t);
    const Traced v = trace(doc, "t", "instrument.cutoff");
    check(near(v.at(0.0), 100) && near(v.at(0.1), 100), "first step holds its value (no glide into step 0)");
    // Beats on the block grid (1/750): 0.28 is 12 % into step 1 = 24 % through its glide.
    check(near(v.at(0.28), 124) && near(v.at(0.3), 140) && near(v.at(0.4), 200) && near(v.at(0.48), 200),
          "glide 0.5: first half of a step moves linearly into its value, then holds");
    check(near(v.at(0.96), 800) && near(v.at(1.04), 576) && near(v.at(1.2), 100), "loop: step 0 glides from the last value");

    json once = doc;
    once["tracks"][0]["modulators"][0]["source"]["loop"] = false;
    once["tracks"][0]["modulators"][0]["source"]["glide"] = 0.0;
    const Traced o = trace(once, "t", "instrument.cutoff");
    check(near(o.at(0.75), 800) && near(o.at(1.5), 800) && near(o.at(7.0), 800), "loop false: the last value holds");

    json expd = song();
    json e = track("t");
    json seq2 = {{"type", "steps"}, {"values", {100, 400}}, {"stepBeats", 0.25}, {"glide", 1.0}};
    e["modulators"] = json::array({{{"target", "instrument.cutoff"}, {"source", seq2}, {"mode", "absolute"}, {"curve", "exp"}}});
    expd["tracks"].push_back(e);
    const Traced x = trace(expd, "t", "instrument.cutoff");
    check(near(x.at(0.3), 100 * std::pow(4.0, 0.2), 1e-6) && near(x.at(0.4), 100 * std::pow(4.0, 0.6), 1e-6),
          "curve exp: geometric glide (100 -> 400)");

    json off = song();
    json f = track("t");
    json seq3 = {{"type", "steps"}, {"values", {-1, 1, 0.5}}, {"stepBeats", 0.5}};
    json m = offsetMod("pan", seq3, 0.4);
    m["base"] = 0.1;
    f["modulators"] = json::array({m});
    off["tracks"].push_back(f);
    const Traced y = trace(off, "t", "pan");
    check(near(y.at(0.0), -0.3) && near(y.at(0.5), 0.5) && near(y.at(1.0), 0.3) && near(y.at(1.5), -0.3),
          "offset steps: base + value * depth");

    // Steps count from the window start (outside it the base applies).
    json win = off;
    win["tracks"][0]["modulators"][0]["startBeat"] = 2.0;
    const Traced w = trace(win, "t", "pan");
    check(near(w.at(1.8), 0.1) && near(w.at(2.0), -0.3) && near(w.at(2.5), 0.5), "steps start at the window start");
}

// ------------------------------------------------------------------------------------- follower

void testFollower() {
    std::cout << "follow\n";
    json doc = song();
    json follower = track("b");  // listed BEFORE its key: the engine must still process the key first
    json src = {{"type", "follow"}, {"node", "a"}, {"attackMs", 0}, {"releaseMs", 50}};
    follower["modulators"] = json::array({absolute("pan", src, 0, 1)});
    doc["tracks"].push_back(follower);
    doc["tracks"].push_back(track("a", json::array({json::array({1.0, 1.0, 45, 127})}),
                                  {{"amp.attack", 0.001}, {"osc.retrig", "on"}}));
    const Traced v = trace(doc, "b", "pan");
    check(v.at(0.0) == 0.0 && v.values[749] == 0.0, "silent key: follower at 0");
    check(v.at(1.0) > 0.01, "follower sees the key's CURRENT block (note starts on block 750: " + num(v.at(1.0)) + ")");
    double peak = 0.0;
    for (double x : v.values) peak = std::max(peak, x);
    check(peak > 0.1 && peak <= 1.0, "follower level within 0..1 (peak " + num(peak) + ")");
    check(v.at(2.0) > 0.01 && v.at(3.0) < 1e-3, "follower releases after the key stops (" + num(v.at(3.0)) + ")");

    json gained = doc;
    gained["tracks"][0]["modulators"][0]["source"]["gainDb"] = 12;
    const Traced g = trace(gained, "b", "pan");
    check(g.at(1.5) > v.at(1.5) * 3.5 || g.at(1.5) >= 0.999, "gainDb drives the follower harder");

    json cycle = doc;
    json back = {{"type", "follow"}, {"node", "b"}};
    cycle["tracks"][1]["modulators"] = json::array({absolute("pan", back, 0, 1)});
    check(throwsConfig(cycle, "routing cycle"), "follower cycle a <-> b rejected");

    json viaBus = song();
    json bt = track("t");
    bt["output"] = "grp";
    json followBus = {{"type", "follow"}, {"node", "grp"}};
    bt["modulators"] = json::array({absolute("pan", followBus, 0, 1)});
    viaBus["tracks"].push_back(bt);
    viaBus["buses"] = json::array({{{"id", "grp"}}});
    check(throwsConfig(viaBus, "routing cycle"), "following the bus you feed is a cycle");

    json self = doc;
    self["tracks"][0]["modulators"][0]["source"]["node"] = "b";
    check(throwsConfig(self, "cannot follow its own output"), "self-follow rejected");
    json master = doc;
    master["tracks"][0]["modulators"][0]["source"]["node"] = "master";
    check(throwsConfig(master, "'master' cannot be followed"), "following master rejected");
    json missing = doc;
    missing["tracks"][0]["modulators"][0]["source"]["node"] = "nope";
    check(throwsConfig(missing, "not a track or bus id"), "unknown follow node rejected");
}

// ------------------------------------------------------------------------------------- envelope

void testEnvelope() {
    std::cout << "envelope and retrigger\n";
    json doc = song();
    json notes = json::array({json::array({0.0, 0.9, 60, 100}), json::array({1.0, 0.4, 62, 100}),
                              json::array({1.5, 0.4, 64, 100})});
    json t = track("t", notes);
    json env = {{"type", "envelope"}, {"attackBeats", 0}, {"decayBeats", 0.5}, {"sustain", 0}, {"releaseBeats", 0}};
    t["modulators"] = json::array({absolute("pan", env, 0, 1)});
    doc["tracks"].push_back(t);
    const Traced v = trace(doc, "t", "pan");
    check(near(v.values[0], 1.0) && near(v.values[150], 0.6) && near(v.values[374], 1.0 / 375.0) && near(v.values[400], 0.0),
          "attack 0 / decay 0.5 beats: 1 at the note, linear to 0 over 375 blocks");
    check(near(v.at(1.0), 1.0) && near(v.values[750 + 150], 0.6), "retriggered by the next note-on");
    check(near(v.at(1.5), 1.0), "retriggered again at beat 1.5");

    json adsr = song();
    json a = track("t", json::array({json::array({0.0, 1.0, 60, 100})}));
    json env2 = {{"type", "envelope"}, {"attackBeats", 0.1}, {"decayBeats", 0.2}, {"sustain", 0.5}, {"releaseBeats", 0.5}};
    a["modulators"] = json::array({absolute("pan", env2, 0, 1)});
    adsr["tracks"].push_back(a);
    const Traced e = trace(adsr, "t", "pan");
    check(near(e.values[0], 0.0) && near(e.values[30], 0.4) && near(e.values[75], 1.0), "attack rises linearly over attackBeats");
    check(near(e.values[135], 0.8) && near(e.values[300], 0.5), "decay to sustain over decayBeats, then holds");
    check(near(e.values[750], 0.5) && near(e.values[825], 0.4) && near(e.values[1200], 0.0), "release after note-off over releaseBeats");

    // Envelope triggered by another track (per-note pumping from a kick track).
    json other = song();
    json kick = track("kick", json::array({json::array({0.0, 0.1, 36, 120}), json::array({1.0, 0.1, 36, 120}),
                                           json::array({2.0, 0.1, 36, 120})}));
    json pad = track("pad");
    json env3 = {{"type", "envelope"}, {"attackBeats", 0}, {"decayBeats", 0.5}, {"sustain", 0}, {"releaseBeats", 0.5}, {"trigger", "kick"}};
    json duck = {{"target", "gainDb"}, {"source", env3}, {"mode", "offset"}, {"depth", -12}, {"base", -3}};
    pad["modulators"] = json::array({duck});
    other["tracks"].push_back(pad);
    other["tracks"].push_back(kick);
    const Traced d = trace(other, "pad", "gainDb");
    check(near(d.at(0.0), -15.0) && near(d.at(1.0), -15.0) && near(d.at(2.0), -15.0) && near(d.at(0.9), -3.0),
          "trigger '<track>': ducks -12 dB on every kick note, back to base between");

    // LFO retrigger: the phase restarts on every note-on of the track.
    json re = song();
    json r = track("t", json::array({json::array({0.5, 1.0, 60, 100}), json::array({2.25, 1.0, 60, 100})}));
    json rl = {{"type", "lfo"}, {"shape", "ramp"}, {"rateBeats", 1.0}, {"retrigger", "note"}};
    r["modulators"] = json::array({absolute("pan", rl, -1, 1)});
    re["tracks"].push_back(r);
    const Traced l = trace(re, "t", "pan");
    check(near(l.at(0.2), -0.6), "before the first note it runs free on the song grid");
    check(near(l.at(0.5), -1.0) && near(l.at(0.7), -0.6) && near(l.at(1.0), 0.0), "note at 0.5 restarts the cycle");
    check(near(l.values[1687], -1.0), "note at 2.25 (inside block 1687) restarts it in that block");
}

// ------------------------------------------------------------------------- offset + automation

void testOffsetAndFieldAutomation() {
    std::cout << "offset mode, mod.<i>.<field> automation, clamping, windows\n";
    json doc = song();
    json t = track("t");
    t["automation"] = json::array({{{"target", "pan"}, {"points", {{0, -0.5}, {4, 0.5}}}},
                                   {{"target", "instrument.cutoff"}, {"points", {{0, 1000}}}}});
    t["modulators"] = json::array({offsetMod("pan", lfo("square", 1.0), 0.25),
                                   {{"target", "instrument.cutoff"}, {"source", lfo("square", 1.0)}, {"mode", "offset"},
                                    {"depth", 1}, {"curve", "exp"}}});
    doc["tracks"].push_back(t);
    const Traced p = trace(doc, "t", "pan");
    double err = 0.0;
    for (std::size_t k = 0; k < 3000; ++k) {
        const double beat = static_cast<double>(k) / kBlocksPerBeat;
        const double lane = -0.5 + beat / 4.0;
        err = std::max(err, std::fabs(p.values[k] - (lane + (frac(beat) < 0.5 ? 0.25 : -0.25))));
    }
    check(err < 1e-9, "offset adds source * depth to the automation lane (max err " + num(err) + ")");
    const Traced c = trace(doc, "t", "instrument.cutoff");
    check(near(c.at(0.0), 2000, 1e-6) && near(c.at(0.5), 500, 1e-6), "curve exp offset: lane * 2^(source * depth octaves)");

    // mod.0.depth automation: a wobble that grows.
    json grow = song();
    json g = track("t");
    json m = offsetMod("pan", lfo("square", 1.0), 0.0);
    m["base"] = 0.0;
    g["modulators"] = json::array({m});
    g["automation"] = json::array({{{"target", "mod.0.depth"}, {"points", {{0, 0}, {4, 1}}}}});
    grow["tracks"].push_back(g);
    const Traced gr = trace(grow, "t", "pan");
    check(near(gr.at(0.0), 0.0) && near(gr.at(1.0), 0.25) && near(gr.at(2.5), -0.625) && near(gr.at(5.0), 1.0),
          "depth automated 0 -> 1 over 4 beats");

    // rateBeats automation keeps the phase continuous; previews integrate it up to their start.
    json rate = song();
    json rt = track("t");
    rt["modulators"] = json::array({absolute("pan", lfo("ramp", 1.0), -1, 1)});
    rt["automation"] = json::array({{{"target", "mod.0.rateBeats"}, {"points", {{0, 0.5}}}}});
    rate["tracks"].push_back(rt);
    const Traced fast = trace(rate, "t", "pan");
    err = 0.0;
    for (std::size_t k = 0; k < 3000; ++k) {
        const double beat = static_cast<double>(k) / kBlocksPerBeat;
        err = std::max(err, std::fabs(fast.values[k] - (-1.0 + 2.0 * frac(2.0 * beat))));
    }
    check(err < 1e-6, "rateBeats automated to 0.5: two cycles per beat (max err " + num(err) + ")");
    json sweep = rate;
    sweep["tracks"][0]["automation"][0]["points"] = {{0, 1.0}, {4, 0.25, "exp"}};
    const Traced full = trace(sweep, "t", "pan");
    const Traced part = trace(sweep, "t", "pan", 3.0, 5.0);
    double worst = 0.0;
    for (std::size_t k = 0; k < 1000; ++k) {
        const double beat = part.firstBeat + static_cast<double>(k) * part.blockBeats;
        const double d = std::fabs(part.values[k] - full.at(beat));
        worst = std::max(worst, std::min(d, 2.0 - d));  // a ramp wrap is not a difference
    }
    check(worst < 1e-6, "rate sweep: preview phase matches the full render (max diff " + num(worst) + ")");

    // Clamping to the target range.
    json clamp = song();
    json cl = track("t");
    json cm = offsetMod("pan", lfo("square", 1.0), 0.5);
    cm["base"] = 0.8;
    cl["modulators"] = json::array({cm});
    clamp["tracks"].push_back(cl);
    const Traced cv = trace(clamp, "t", "pan");
    double hi = -9.0, lo = 9.0;
    for (double x : cv.values) { hi = std::max(hi, x); lo = std::min(lo, x); }
    check(hi == 1.0 && near(lo, 0.3), "clamped to the pan range (max " + num(hi) + ", min " + num(lo) + ")");
    json deep = song();
    json dp = track("t");
    json dm = {{"target", "instrument.cutoff"}, {"source", lfo("square", 1.0)}, {"mode", "offset"}, {"depth", 8},
               {"curve", "exp"}, {"base", 5000}};
    dp["modulators"] = json::array({dm});
    deep["tracks"].push_back(dp);
    const Traced dv = trace(deep, "t", "instrument.cutoff");
    check(dv.at(0.0) == 20000.0 && dv.at(0.5) == 20.0, "cutoff clamped to 20..20000 (5000 * 2^+-8)");

    // Windows: outside, the lane / static value applies.
    json win = song();
    json w = track("t");
    w["gainDb"] = -6;
    json wm = absolute("gainDb", lfo("square", 1.0), -20, 0);
    wm["startBeat"] = 2;
    wm["endBeat"] = 4;
    w["modulators"] = json::array({wm});
    win["tracks"].push_back(w);
    const Traced wv = trace(win, "t", "gainDb");
    check(near(wv.at(1.9), -6) && near(wv.at(2.0), 0) && near(wv.at(2.5), -20) && near(wv.at(3.75), -20) && near(wv.at(4.0), -6),
          "window [2, 4): static fader value outside, modulated inside");
    json mw = song();
    json mt = track("t");
    json mm = absolute("instrument.cutoff", lfo("sine", 1.0), 400, 4000, "exp");
    mm["startBeat"] = 4;
    mm["base"] = 1200;
    mt["modulators"] = json::array({mm});
    mw["tracks"].push_back(mt);
    const Traced mv = trace(mw, "t", "instrument.cutoff");
    check(near(mv.at(0.0), 1200) && near(mv.at(3.9), 1200) && near(mv.at(4.0), 400, 1e-6) && near(mv.at(4.5), 4000, 1e-6),
          "module param: 'base' outside the window, cycle counts from the window start");
    json lw = song();
    json lt = track("t");
    lt["automation"] = json::array({{{"target", "instrument.cutoff"}, {"points", {{0, 300}, {8, 3000}}}}});
    json lm = absolute("instrument.cutoff", lfo("square", 1.0), 5000, 6000);
    lm["startBeat"] = 2;
    lm["endBeat"] = 3;
    lt["modulators"] = json::array({lm});
    lw["tracks"].push_back(lt);
    const Traced lv = trace(lw, "t", "instrument.cutoff");
    check(near(lv.at(1.0), 300 + 2700.0 / 8.0) && near(lv.at(2.0), 6000) && near(lv.at(2.5), 5000) && near(lv.at(3.0), 300 + 2700.0 * 3 / 8),
          "absolute modulator replaces the lane inside its window only");
}

// ------------------------------------------------------------------------------- random + determinism

void testRandomAndDeterminism() {
    std::cout << "random sources and determinism\n";
    json doc = song();
    json t = track("t", json::array({json::array({0.0, 8.0, 57, 100})}));
    json sh = {{"type", "random"}, {"rateBeats", 0.25}};
    json smooth = {{"type", "random"}, {"rateBeats", 0.5}, {"smooth", 1.0}};
    t["modulators"] = json::array({absolute("pan", sh, -1, 1), absolute("instrument.cutoff", lfo("smoothrandom", 1.0), 300, 3000, "exp"),
                                   absolute("gainDb", smooth, -12, 0)});
    doc["tracks"].push_back(t);
    const Traced a = trace(doc, "t", "pan");
    const Traced b = trace(doc, "t", "pan");
    check(a.values == b.values, "random: identical across renders");
    bool held = true, varies = false;
    auto step = [](std::size_t k) { return std::floor(static_cast<double>(k) * 4.0 / kBlocksPerBeat + 1e-9); };
    for (std::size_t k = 0; k + 1 < a.values.size(); ++k) {
        const bool boundary = step(k) != step(k + 1);  // 0.25 beats = 187.5 blocks
        if (!boundary && a.values[k] != a.values[k + 1]) held = false;
        if (a.values[k] != a.values[k + 1]) varies = true;
    }
    check(held && varies, "sample & hold: constant within a step, new value per step");
    double lo = 9, hi = -9;
    for (double x : a.values) { lo = std::min(lo, x); hi = std::max(hi, x); }
    check(lo >= -1.0 && hi <= 1.0 && hi - lo > 1.0, "values spread over min..max (" + num(lo) + ".." + num(hi) + ")");
    const Traced part = trace(doc, "t", "pan", 2.5, 4.0);
    bool same = true;
    for (std::size_t k = 0; k < 1000; ++k) same = same && part.values[k] == a.at(part.firstBeat + static_cast<double>(k) * part.blockBeats);
    check(same, "preview sees exactly the random values of the full render");
    const Traced c = trace(doc, "t", "instrument.cutoff");
    double jump = 0.0;
    for (std::size_t k = 1; k < c.values.size(); ++k) jump = std::max(jump, std::fabs(std::log2(c.values[k] / c.values[k - 1])));
    check(jump < 0.02, "smoothrandom lfo moves without jumps (max step " + num(jump) + " oct/block)");
    const Traced s = trace(doc, "t", "gainDb");
    double sjump = 0.0;
    for (std::size_t k = 1; k < s.values.size(); ++k) sjump = std::max(sjump, std::fabs(s.values[k] - s.values[k - 1]));
    check(sjump < 0.2, "random with smooth 1 glides (max step " + num(sjump) + " dB/block)");

    json other = doc;
    other["seed"] = 4;
    check(trace(other, "t", "pan").values != a.values, "another song seed gives other random values");

    // Whole mix bit-identical with every source type active.
    json full = song();
    json lead = track("lead", json::array({json::array({0.0, 2.0, 69, 110}), json::array({2.0, 2.0, 72, 100}),
                                           json::array({4.0, 4.0, 76, 90})}));
    lead["modulators"] = json::array({absolute("instrument.cutoff", lfo("sine", 0.5), 400, 5000, "exp"),
                                      absolute("pan", {{"type", "random"}, {"rateBeats", 0.25}, {"smooth", 0.3}}, -0.5, 0.5)});
    json pad = track("pad", json::array({json::array({0.0, 8.0, 57, 90}), json::array({0.0, 8.0, 60, 90})}));
    json gate = {{"target", "gainDb"}, {"source", {{"type", "steps"}, {"values", {0, -1, 0, 0, -1, 0, -1, -1}}, {"stepBeats", 0.25}}},
                 {"mode", "offset"}, {"depth", 18}, {"base", -6}};
    json fol = absolute("instrument.cutoff", {{"type", "follow"}, {"node", "lead"}, {"attackMs", 5}, {"releaseMs", 200}}, 800, 4000, "exp");
    pad["modulators"] = json::array({gate, fol});
    full["tracks"] = json::array({pad, lead});
    as::RenderOptions o;
    o.assetDir = "assets";
    o.quiet = true;
    o.analysis = false;
    o.pngs = false;
    const auto spec = as::parseSong(full);
    o.outDir = (fs::path(".scratch") / "modulators" / "a").string();
    as::renderSong(spec, o);
    o.outDir = (fs::path(".scratch") / "modulators" / "b").string();
    as::renderSong(spec, o);
    const auto wa = readFile(fs::path(".scratch") / "modulators" / "a" / "mix.wav");
    const auto wb = readFile(fs::path(".scratch") / "modulators" / "b" / "mix.wav");
    check(wa.size() > 1000 && wa == wb, "mix with lfo/random/steps/follow modulators is bit-identical across renders");
}

// ------------------------------------------------------------------------- previews and retrigger timing

double lastOnBefore(const std::vector<double>& ons, double beat) {
    double last = -1.0;
    for (double on : ons) if (on <= beat + 1e-12) last = on;
    return last;
}

void testPreviewParity() {
    std::cout << "note-triggered sources: exact timing and preview parity\n";
    const double blockBeats = 1.0 / kBlocksPerBeat;

    // LFO retrigger: after the block of a note-on the phase is (beat - note-on) exactly, whatever the block
    // grid; a preview starts with the phase the full render has there (note history before the preview).
    const std::vector<double> ons = {0.5, 2.3, 3.1, 5.2};
    json doc = song();
    json t = track("t", json::array({json::array({0.5, 1.0, 60, 100}), json::array({2.3, 0.3, 62, 100}),
                                     json::array({3.1, 1.5, 64, 100}), json::array({5.2, 0.5, 65, 100})}));
    json rl = {{"type", "lfo"}, {"shape", "ramp"}, {"rateBeats", 1.0}, {"retrigger", "note"}};
    t["modulators"] = json::array({absolute("pan", rl, -1, 1)});
    doc["tracks"].push_back(t);
    auto expected = [&](double b) {
        for (double on : ons) if (on >= b - 1e-12 && on < b + blockBeats - 1e-12) return -1.0;  // the note's block
        const double last = lastOnBefore(ons, b);
        return -1.0 + 2.0 * frac(last < 0 ? b : b - last);
    };
    auto worstError = [&](const Traced& tr, std::size_t count) {
        double worst = 0.0;
        for (std::size_t k = 0; k < count && k < tr.values.size(); ++k) {
            const double b = tr.firstBeat + static_cast<double>(k) * tr.blockBeats;
            const double d = std::fabs(tr.values[k] - expected(b));
            worst = std::max(worst, std::min(d, 2.0 - d));  // a ramp wrap is not a difference
        }
        return worst;
    };
    const Traced full = trace(doc, "t", "pan");
    check(worstError(full, full.values.size()) < 1e-6, "full render: retriggered phase exact from the note-on sample (max err " +
                                                           num(worstError(full, full.values.size())) + ")");
    for (double from : {2.8, 2.45, 3.7, 4.123}) {  // between notes, inside a held note, off the block grid
        const Traced part = trace(doc, "t", "pan", from, 6.0);
        check(worstError(part, part.values.size()) < 1e-6, "preview from beat " + num(from) + " continues the full render's phase (max err " +
                                                               num(worstError(part, part.values.size())) + ")");
    }

    // Envelope: a preview starting inside a held note / a release continues the envelope instead of
    // restarting it (the resumed note-on is not a new trigger).
    json env = song();
    json e = track("t", json::array({json::array({0.0, 1.5, 60, 100}), json::array({2.0, 0.5, 62, 100})}));
    json adsr = {{"type", "envelope"}, {"attackBeats", 0}, {"decayBeats", 1.0}, {"sustain", 0.25}, {"releaseBeats", 0.5}};
    e["modulators"] = json::array({absolute("pan", adsr, 0, 1)});
    env["tracks"].push_back(e);
    const Traced ef = trace(env, "t", "pan");
    for (double from : {0.5, 1.0, 1.76, 2.2}) {
        const Traced part = trace(env, "t", "pan", from, 4.0);
        double worst = 0.0;
        for (std::size_t k = 0; k < part.values.size(); ++k) worst = std::max(worst, std::fabs(part.values[k] - ef.at(part.firstBeat + static_cast<double>(k) * part.blockBeats)));
        check(worst < 1e-9, "envelope preview from beat " + num(from) + " = full render (first " + num(part.values[0]) + " vs " +
                                num(ef.at(from)) + ", max diff " + num(worst) + ")");
    }
    check(near(ef.at(0.5), 0.625) && near(ef.at(1.76), 0.12), "decay / release levels on the beat grid");

    // Envelope level is exact relative to a note-on inside a block.
    json mid = song();
    json mt = track("t", json::array({json::array({1.0 + 16.0 / 24000.0, 2.0, 60, 100})}));  // 16 samples into block 750
    json dec = {{"type", "envelope"}, {"attackBeats", 0}, {"decayBeats", 1.0}, {"sustain", 0}, {"releaseBeats", 0}};
    mt["modulators"] = json::array({absolute("pan", dec, 0, 1)});
    mid["tracks"].push_back(mt);
    const Traced mv = trace(mid, "t", "pan");
    check(near(mv.values[750], 1.0) && near(mv.values[751], 1.0 - 16.0 / 24000.0) && near(mv.values[900], 1.0 - (150.0 * 32 - 16) / 24000.0),
          "decay measured from the note-on sample (" + num(mv.values[751]) + ")");

    // A 'mod.<i>.base' lane also sets the value outside the modulator's window.
    json bw = song();
    json bt = track("t");
    json bm = offsetMod("pan", lfo("square", 1.0), 0.2);
    bm["base"] = 0.0;
    bm["startBeat"] = 2;
    bm["endBeat"] = 4;
    bt["modulators"] = json::array({bm});
    bt["automation"] = json::array({{{"target", "mod.0.base"}, {"points", {{0, 0}, {8, 0.5}}}}});
    bw["tracks"].push_back(bt);
    const Traced bv = trace(bw, "t", "pan");
    check(near(bv.at(1.0), 0.0625) && near(bv.at(2.0), 0.325) && near(bv.at(5.0), 0.3125),
          "automated base applies inside and outside the window (" + num(bv.at(5.0)) + ")");
}

// ------------------------------------------------------------------------------------ strict errors

void testErrors() {
    std::cout << "strict validation\n";
    auto with = [](json mod, json trackPatch = json::object()) {
        json doc = song();
        json t = track("t", json::array({json::array({0.0, 1.0, 60, 100})}));
        t["modulators"] = json::array({mod});
        for (auto it = trackPatch.begin(); it != trackPatch.end(); ++it) t[it.key()] = it.value();
        doc["tracks"].push_back(t);
        doc["tracks"].push_back(track("u"));
        doc["buses"] = json::array({{{"id", "fx"}}});
        return doc;
    };
    const json good = absolute("instrument.cutoff", lfo("sine", 1.0), 400, 4000, "exp");
    json m = good;
    m["bogus"] = 1;
    check(throwsConfig(with(m), "unknown key 'bogus'"), "unknown modulator key");
    m = good;
    m["source"]["speed"] = 2;
    check(throwsConfig(with(m), "unknown key 'speed'"), "unknown source key");
    m = good;
    m["source"]["type"] = "chaos";
    check(throwsConfig(with(m), "must be lfo|steps|follow|envelope|random"), "unknown source type");
    m = good;
    m["source"]["shape"] = "wobble";
    check(throwsConfig(with(m), "sine|triangle|saw|ramp|square|random|smoothrandom"), "unknown lfo shape");
    m = good;
    m["source"]["rateHz"] = 3;
    check(throwsConfig(with(m), "exactly one of 'rateBeats'"), "rateBeats and rateHz together");
    m = good;
    m["source"]["rateBeats"] = 0;
    check(throwsConfig(with(m), "rateBeats"), "rate 0 rejected");
    m = good;
    m["target"] = "instrument.nonexistent";
    check(throwsConfig(with(m), "not an automatable instrument parameter"), "unknown instrument param target");
    m = good;
    m["target"] = "instrument.unison";
    check(throwsConfig(with(m), "not an automatable"), "static (non-automatable) param target");
    m = good;
    m["target"] = "fx.0.mix";
    check(throwsConfig(with(m), "missing fx slot"), "fx target without that slot");
    m = good;
    m["target"] = "send.fx";
    check(throwsConfig(with(m), "matching entry in 'sends'"), "send target without a send");
    m = good;
    m["target"] = "fx.0x.mix";
    check(throwsConfig(with(m), "bad fx index"), "fx index with trailing junk");
    m = good;
    m["target"] = "volume";
    check(throwsConfig(with(m), "not a valid target"), "unknown target");
    m = good;
    m["target"] = "mod.0.depth";
    check(throwsConfig(with(m), "cannot target another modulator"), "modulator targeting a modulator");
    m = good;
    m["mode"] = "multiply";
    check(throwsConfig(with(m), "absolute|offset"), "bad mode");
    m = good;
    m["min"] = 0;
    check(throwsConfig(with(m), "min"), "exp curve with min 0");
    m = absolute("instrument.cutoff", lfo("sine", 1.0), 5, 4000);
    check(throwsConfig(with(m), "outside the range 20..20000"), "min outside the parameter range");
    m = good;
    m["depth"] = 1;
    check(throwsConfig(with(m), "only for mode 'offset'"), "depth in absolute mode");
    m = offsetMod("pan", lfo("sine", 1.0), 0.5);
    m["min"] = 0;
    check(throwsConfig(with(m), "'min'/'max' are for mode 'absolute'"), "min in offset mode");
    m = offsetMod("instrument.cutoff", lfo("sine", 1.0), 0.5);
    check(throwsConfig(with(m), "give \"base\""), "offset without lane and without base");
    m = offsetMod("pan", lfo("sine", 1.0), 0.5);
    m["base"] = 0.0;
    check(throwsConfig(with(m, {{"automation", json::array({{{"target", "pan"}, {"points", {{0, 0.2}}}}})}}), "remove 'base'"),
          "base next to an automation lane");
    m = offsetMod("instrument.cutoff", lfo("sine", 1.0), 1.0);
    m["curve"] = "exp";
    m["base"] = 0;
    check(throwsConfig(with(m), "base"), "exp offset with base 0");
    m = good;
    m["startBeat"] = 4;
    check(throwsConfig(with(m), "outside the modulator window it needs \"base\""), "windowed module param without base or lane");
    m = good;
    m["startBeat"] = 4;
    m["endBeat"] = 2;
    check(throwsConfig(with(m), "must be > startBeat"), "empty window");
    json steps = {{"type", "steps"}, {"values", {0, 2}}, {"stepBeats", 0.25}};
    m = offsetMod("pan", steps, 0.5);
    m["base"] = 0;
    check(throwsConfig(with(m), "must be in -1..1"), "offset steps outside -1..1");
    m = {{"target", "pan"}, {"source", steps}, {"mode", "absolute"}, {"min", 0}, {"max", 1}};
    check(throwsConfig(with(m), "take their 'values' in target units"), "min/max on absolute steps");
    m = {{"target", "pan"}, {"source", steps}, {"mode", "absolute"}};
    check(throwsConfig(with(m), "outside the range -1..1"), "absolute steps outside the target range");
    m = {{"target", "pan"}, {"source", {{"type", "steps"}, {"values", json::array()}, {"stepBeats", 0.25}}}, {"mode", "absolute"}};
    check(throwsConfig(with(m), "non-empty array"), "empty steps");
    m = absolute("pan", {{"type", "envelope"}, {"trigger", "fx"}}, 0, 1);
    check(throwsConfig(with(m), "not a track id"), "envelope trigger on a bus id");
    json busDoc = song();
    busDoc["tracks"].push_back(track("t"));
    busDoc["buses"] = json::array({{{"id", "grp"}, {"modulators", json::array({absolute("pan", {{"type", "envelope"}}, 0, 1)})}}});
    check(throwsConfig(busDoc, "needs a track"), "note-triggered envelope on a bus");
    busDoc["buses"][0]["modulators"] = json::array({absolute("pan", {{"type", "lfo"}, {"shape", "sine"}, {"rateBeats", 1}, {"retrigger", "note"}}, 0, 1)});
    check(throwsConfig(busDoc, "needs a track"), "lfo retrigger on a bus");
    busDoc["buses"][0]["modulators"] = json::array({absolute("instrument.cutoff", lfo("sine", 1), 400, 800)});
    check(throwsConfig(busDoc, "only tracks have an instrument"), "instrument target on a bus");

    // mod.<i>.<field> lanes.
    auto lane = [&](const std::string& target, json points) {
        return with(good, {{"automation", json::array({{{"target", target}, {"points", points}}})}});
    };
    check(throwsConfig(lane("mod.3.min", {{0, 500}}), "missing modulator"), "mod index out of range");
    check(throwsConfig(lane("mod.0.speed", {{0, 1}}), "unknown field"), "unknown mod field");
    check(throwsConfig(lane("mod.0.depth", {{0, 1}}), "not a field of that modulator"), "depth on an absolute modulator");
    check(throwsConfig(lane("mod.0.rateBeats", {{0, 0}}), "outside"), "rateBeats automation of 0");
    check(throwsConfig(lane("mod.0.min", {{0, 10}}), "outside the range 20..20000"), "min automation outside the target range");
    check(throwsConfig(lane("mod.x.min", {{0, 500}}), "bad modulator index"), "non-numeric mod index");
    json dup = with(good, {{"automation", json::array({{{"target", "pan"}, {"points", {{0, 0}}}}, {{"target", "pan"}, {"points", {{0, 1}}}}})}});
    check(throwsConfig(dup, "automated twice"), "duplicate automation lane");

    json unknownKey = song();
    json tt = track("t");
    tt["modulators"] = json::object();
    unknownKey["tracks"].push_back(tt);
    check(throwsConfig(unknownKey, "modulators: must be an array"), "modulators must be an array");
    json masterDoc = song();
    masterDoc["tracks"].push_back(track("t"));
    masterDoc["master"] = {{"modulators", json::array({absolute("gainDb", lfo("sine", 4), -3, 0)})}};
    bool ok = true;
    try { as::validateSong(as::parseSong(masterDoc), "assets"); } catch (const as::ConfigError& e) { ok = false; std::cout << "       " << e.what() << "\n"; }
    check(ok, "master accepts modulators");
}

}  // namespace

int main() {
    fs::create_directories(fs::path(".scratch") / "modulators");
    std::cout << "test_modulators\n";
    testLfoGrid();
    testSteps();
    testFollower();
    testEnvelope();
    testOffsetAndFieldAutomation();
    testRandomAndDeterminism();
    testPreviewParity();
    testErrors();
    std::cout << (failures ? "FAILED" : "PASSED") << " (" << failures << " failures)\n";
    return failures ? 1 : 0;
}
