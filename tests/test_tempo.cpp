// Tempo map + meter tests (docs/RENDER_FORMAT.md "Tempo map", "Meter"): exact analytic beat <-> time
// conversions (linear, smooth, step) against numeric integration; a constant map renders bit-identically to
// "tempo" (full render and preview); note onsets on the analytic times; tempo-synced effects on the moving
// grid (delay echoes, tremolo, ducker tempo mode, VA synced LFOs, track modulators); preview parity inside a
// ramp; meters in the report (bars, sections, timeline); strict parsing.

#include "core/TempoMap.h"
#include "instruments/Dx7Banks.h"
#include "io/WavReader.h"
#include "render/Registry.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
using as::json;
using as::TempoCurve;

namespace {

// A DX7 e-piano; the ROM banks are not distributed (assets/dx7/README.md), so without them a plain va plays the keys.
json keysInstrument() {
    if (as::dx7BanksInstalled("assets")) return {{"type", "dx7"}, {"params", {{"voice", "E.PIANO 1"}}}};
    static bool told = false;
    if (!told) std::printf("SKIP: dx7 keys replaced by va (%s)\n", as::kDx7NoBanksHint);
    told = true;
    return {{"type", "va"}, {"params", json::object()}};
}

int failures = 0;
constexpr double kSr = 48000.0;
constexpr double kPi = 3.14159265358979323846;

void check(bool ok, const std::string& what) {
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << "\n";
    if (!ok) ++failures;
}

std::string fmt(const char* f, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, f);
    std::vsnprintf(buf, sizeof buf, f, ap);
    va_end(ap);
    return buf;
}

std::vector<char> readFile(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), {}};
}

json readJsonFile(const fs::path& p) {
    std::ifstream in(p);
    return json::parse(in);
}

// Seconds from beat 0 to `beat` for a tempo function, by composite Simpson integration of 60 / bpm on each
// piece between the breakpoints (where the tempo curve has a kink).
double integrateSeconds(const std::function<double(double)>& bpm, double beat, std::vector<double> breaks = {}, int steps = 4000) {
    breaks.push_back(beat);
    double total = 0.0, a = 0.0;
    for (double b : breaks) {
        b = std::min(b, beat);
        if (b <= a) continue;
        const double h = (b - a) / steps;
        double s = 60.0 / bpm(a) + 60.0 / bpm(b);
        for (int i = 1; i < steps; ++i) s += (i % 2 ? 4.0 : 2.0) * 60.0 / bpm(a + i * h);
        total += s * h / 3.0;
        a = b;
    }
    return total;
}

bool throwsInvalid(const std::function<void()>& f, const std::string& expect = "") {
    try {
        f();
    } catch (const std::invalid_argument& e) {
        if (!expect.empty() && std::string(e.what()).find(expect) == std::string::npos) {
            std::cout << "       (message was: " << e.what() << ")\n";
            return false;
        }
        return true;
    }
    return false;
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

// Renders a render-JSON document; returns the mix.
as::WavData renderDoc(const json& doc, const std::string& dir, std::optional<double> from = std::nullopt,
                      bool analysis = false, as::ControlTrace* trace = nullptr) {
    as::RenderOptions o;
    o.assetDir = "assets";
    o.outDir = (fs::path(".scratch") / "tempo" / dir).string();
    o.quiet = true;
    o.analysis = analysis;
    o.pngs = false;
    o.fromBeat = from;
    o.trace = trace;
    as::renderSong(as::parseSong(doc), o);
    return as::readWav((fs::path(o.outDir) / "mix.wav").string());
}

json baseDoc(double lengthBeats, int bitDepth = 32) {
    json d = {{"format", "agentsound.render"}, {"version", 1}, {"title", "tempo test"}, {"lengthBeats", lengthBeats},
              {"tailSeconds", 0.5}, {"seed", 5}, {"tracks", json::array()}, {"export", {{"bitDepth", bitDepth}}}};
    return d;
}

json tempoPoints(const std::vector<as::TempoPoint>& pts) {
    json a = json::array();
    for (const auto& p : pts) {
        json pt = json::array({p.beat, p.bpm});
        if (p.curve == TempoCurve::Step) pt.push_back("step");
        if (p.curve == TempoCurve::Smooth) pt.push_back("smooth");
        a.push_back(pt);
    }
    return a;
}

// A short, identical click per note: retriggered square, no drift, open filter.
json clickInstrument(double levelDb = -12.0) {
    return {{"type", "va"}, {"params", {{"osc1.wave", "square"}, {"osc.retrig", "on"}, {"drift.pitch", 0}, {"drift.cutoff", 0},
                                        {"amp.attack", 0.001}, {"amp.decay", 0.02}, {"amp.sustain", 0}, {"amp.release", 0.005},
                                        {"cutoff", 20000}, {"filter.env", 0}, {"filter.drive", 0}, {"level", levelDb}}}};
}

// Where |x| rises above `frac` of the local peak (the peak within `win` samples after the rise), with
// linear interpolation, for every event separated by at least `gap` quiet samples. extrapolate: the start of
// the rise instead, from the crossings of frac and 3 * frac (unbiased for a click played slower or faster,
// like the echoes of a tape-style delay while the tempo moves).
std::vector<double> onsets(const std::vector<float>& x, double floorThr, double frac, int win, int gap, bool extrapolate = false) {
    std::vector<double> out;
    std::size_t i = 0;
    int quiet = gap;
    while (i < x.size()) {
        if (std::fabs(x[i]) < floorThr) {
            ++quiet;
            ++i;
            continue;
        }
        if (quiet < gap) {
            quiet = 0;
            ++i;
            continue;
        }
        // event starts near i: find its peak, then the crossing of frac * peak
        const std::size_t start = i > 64 ? i - 64 : 0;
        float pk = 0.0f;
        for (std::size_t k = start; k < std::min(x.size(), i + static_cast<std::size_t>(win)); ++k) pk = std::max(pk, std::fabs(x[k]));
        auto crossing = [&](double thr) {
            std::size_t k = start;
            while (k + 1 < x.size() && std::fabs(x[k + 1]) < thr) ++k;
            const double a = std::fabs(x[k]), b = std::fabs(x[k + 1]);
            return static_cast<double>(k) + (b > a ? (thr - a) / (b - a) : 0.0);
        };
        const double c1 = crossing(frac * pk);
        const std::size_t k = static_cast<std::size_t>(c1);
        out.push_back(extrapolate ? c1 - (crossing(3.0 * frac * pk) - c1) * 0.5 : c1);
        // skip the event
        i = k + 1;
        quiet = 0;
        while (i < x.size() && quiet < gap) {
            quiet = std::fabs(x[i]) < floorThr ? quiet + 1 : 0;
            ++i;
        }
    }
    return out;
}

// Runs a module over constant input 1.0 (gain curves), in 32-sample blocks from song sample `startSample`.
std::vector<float> gainCurve(as::Effect& fx, std::size_t frames) {
    std::vector<float> l(frames, 1.0f), r(frames, 1.0f);
    for (std::size_t i = 0; i < frames; i += 32) {
        const int n = static_cast<int>(std::min<std::size_t>(32, frames - i));
        fx.process(l.data() + i, r.data() + i, n, nullptr, nullptr);
    }
    return l;
}

// Level crossings of `level` (rising or falling), interpolated.
std::vector<double> crossings(const std::vector<float>& x, double level, bool rising) {
    std::vector<double> out;
    for (std::size_t i = 1; i < x.size(); ++i) {
        const double a = x[i - 1], b = x[i];
        if (rising ? (a < level && b >= level) : (a > level && b <= level)) out.push_back(static_cast<double>(i - 1) + (level - a) / (b - a));
    }
    return out;
}

// ------------------------------------------------------------------------------------------ math

void testTempoMath() {
    std::cout << "tempo map: exact conversions\n";
    {
        const as::TempoMap m(97.3, kSr);
        const double spb = kSr * 60.0 / 97.3;
        bool same = m.constant();
        for (double b : {0.0, 0.37, 1.0, 13.25, 999.123, 54321.5}) {
            same = same && m.sampleAt(b) == b * spb && m.beatAtSample(b * spb) == (b * spb) / spb && m.secondsAt(b) == b * 60.0 / 97.3;
        }
        check(same, "constant map: sampleAt = beat * sr * 60 / bpm (and back, and seconds), bit for bit");
        const as::TempoMap merged({{0, 97.3}, {16, 97.3}, {24, 97.3, TempoCurve::Step}, {30, 97.3, TempoCurve::Smooth}}, kSr);
        bool m2 = merged.constant();
        for (double b : {0.0, 3.3, 17.1, 25.0, 40.0}) m2 = m2 && merged.sampleAt(b) == m.sampleAt(b);
        check(m2, "points that keep the tempo merge into one constant segment (bit-identical conversions)");
    }
    {
        const as::TempoMap m({{0, 120}, {4, 120}, {12, 60}}, kSr);
        const double analytic = 60.0 * 8.0 / (60.0 - 120.0) * std::log(60.0 / 120.0);
        const double got = m.secondsAt(12.0) - m.secondsAt(4.0);
        check(std::fabs(got - analytic) < 1e-12,
              fmt("linear ramp 120 -> 60 over 8 beats lasts 60*8/(60-120)*ln(60/120) = %.12f s (map %.12f)", analytic, got));
        auto bpm = [](double b) { return b < 4 ? 120.0 : b < 12 ? 120.0 - 7.5 * (b - 4.0) : 60.0; };
        double err = 0.0, round = 0.0, bpmErr = 0.0;
        for (double b = 0.0; b <= 16.0; b += 0.37) {
            err = std::max(err, std::fabs(m.secondsAt(b) - integrateSeconds(bpm, b, {4.0, 12.0})));
            round = std::max(round, std::fabs(m.beatAtSample(m.sampleAt(b)) - b));
            bpmErr = std::max(bpmErr, std::fabs(m.bpmAt(b) - bpm(b)));
        }
        check(err < 1e-9 && round < 1e-9 && bpmErr < 1e-9,
              fmt("linear: time = numeric integral of 60/bpm (max err %.1e s), beat -> sample -> beat (%.1e), bpm (%.1e)", err, round, bpmErr));
    }
    {
        const as::TempoMap m({{0, 100}, {6, 150, TempoCurve::Smooth}}, kSr);
        const double analytic = 60.0 * 6.0 / std::sqrt(100.0 * 150.0);
        check(std::fabs(m.secondsAt(6.0) - analytic) < 1e-12,
              fmt("smooth ramp 100 -> 150 over 6 beats lasts 60*6/sqrt(100*150) = %.12f s (map %.12f)", analytic, m.secondsAt(6.0)));
        auto bpm = [](double b) { return b < 6 ? 100.0 + 50.0 * (0.5 - 0.5 * std::cos(kPi * b / 6.0)) : 150.0; };
        double err = 0.0, round = 0.0, bpmErr = 0.0;
        for (double b = 0.0; b <= 9.0; b += 0.123) {
            err = std::max(err, std::fabs(m.secondsAt(b) - integrateSeconds(bpm, b, {6.0})));
            round = std::max(round, std::fabs(m.beatAtSample(m.sampleAt(b)) - b));
            bpmErr = std::max(bpmErr, std::fabs(m.bpmAt(b) - bpm(b)));
        }
        check(err < 1e-9 && round < 1e-9 && bpmErr < 1e-9,
              fmt("smooth: time = numeric integral (max err %.1e s), round trip (%.1e), cosine-eased bpm (%.1e)", err, round, bpmErr));
    }
    {
        const as::TempoMap m({{0, 120}, {4, 90, TempoCurve::Step}}, kSr);
        check(m.bpmAt(3.999999) == 120.0 && m.bpmAt(4.0) == 90.0 && m.sampleAt(4.0) == 96000.0 && std::fabs(m.sampleAt(5.0) - 128000.0) < 1e-9 &&
                  std::fabs(m.beatAtSample(128000.0) - 5.0) < 1e-12,
              "step: 120 BPM up to beat 4, then 90 (beat 4 at 2 s, beat 5 at 2.667 s)");
    }
    {
        const as::TempoMap m({{0, 120}, {8, 60}}, kSr);
        check(std::fabs(m.sampleAt(-1.0) + 24000.0) < 1e-9 && m.bpmAt(-3.0) == 120.0 && m.bpmAt(100.0) == 60.0 &&
                  std::fabs(m.sampleAt(20.0) - m.sampleAt(19.0) - 48000.0) < 1e-6 && m.minBpm() == 60.0 && m.maxBpm() == 120.0,
              "before beat 0 the first tempo holds, after the last point the last one; min/max bpm");
    }
    check(throwsInvalid([] { as::TempoMap({{1, 120}}, kSr); }, "beat 0") &&
              throwsInvalid([] { as::TempoMap({{0, 120}, {0, 100}}, kSr); }, "strictly increasing") &&
              throwsInvalid([] { as::TempoMap({{0, -5}}, kSr); }, "bpm > 0"),
          "invalid maps rejected (first point not at 0, beats not increasing, bpm <= 0)");
    {
        const as::TempoMap m({{0, 120}, {4, 120}, {12, 60, TempoCurve::Smooth}, {13, 90, TempoCurve::Step}}, kSr);
        as::BeatClock clock;
        clock.attach(&m);
        double err = 0.0;
        bool grid = true;
        for (std::int64_t s = 0; s < 12 * 48000; s += 7) err = std::max(err, std::fabs(clock.beatAt(s) - m.beatAtSample(static_cast<double>(s))));
        for (std::int64_t s = 0; s < 12 * 48000; s += 32 * 97) grid = grid && clock.beatAt(s) == m.beatAtSample(static_cast<double>(s));
        check(err < 1e-8 && grid, fmt("BeatClock: exact on the 32-sample grid, linear between, exact at a tempo step (max err %.1e beats)", err));
    }
}

void testMeterMath() {
    std::cout << "meter: bars across meter changes\n";
    const as::MeterMap mm({{0, 4, 4}, {16, 3, 4}, {25, 6, 8}, {31, 4, 4}});
    check(mm.barAt(16) == 4.0 && mm.barAt(19) == 5.0 && mm.barAt(25) == 7.0 && mm.barAt(28) == 8.0 && mm.barAt(31) == 9.0 &&
              mm.barAt(33) == 9.5,
          "bars: 4 of 4/4, 3 of 3/4 from beat 16, 2 of 6/8 (3 beats) from 25, 4/4 from 31");
    check(mm.barStart(4) == 16.0 && mm.barStart(6) == 22.0 && mm.barStart(7) == 25.0 && mm.barStart(9) == 31.0 && mm.barStart(10) == 35.0,
          "bar starts: bar 4 = beat 16, 6 = 22, 7 = 25, 9 = 31, 10 = 35");
    check(mm.label(29.5) == "bar 9 beat 2.50" && mm.label(16.0) == "bar 5 beat 1.00" && as::MeterMap().label(59.998) == "bar 16 beat 1.00",
          "labels: beat 29.5 = 'bar 9 beat 2.50' (6/8), beat 16 = 'bar 5 beat 1.00'; 4/4 default as before");
    check(mm.beatsPerBarAt(26) == 3.0 && mm.meterAt(17).numerator == 3 && as::MeterMap().plain() && !mm.plain(), "meter lookups");
    check(throwsInvalid([] { as::MeterMap({{0, 4, 4}, {6, 3, 4}}); }, "not on a bar line") &&
              throwsInvalid([] { as::MeterMap({{0, 4, 3}}); }, "denominator"),
          "a meter change inside a bar and a bad denominator are rejected");
}

// ------------------------------------------------------------------------------------------ parsing

void testParse() {
    std::cout << "render JSON: tempoMap / meter strictness\n";
    json doc = baseDoc(8);
    doc["tracks"].push_back({{"id", "a"}, {"instrument", clickInstrument()}, {"notes", {{0, 1, 69, 100}}}});
    json d = doc;
    d["tempo"] = 120;
    check(as::parseSong(d).tempoMap.empty(), "\"tempo\" alone: a constant tempo");
    d = doc;
    d["tempoMap"] = {{0, 120}, {4, 90, "smooth"}, {6, 80, "step"}};
    const auto s = as::parseSong(d);
    check(s.tempoMap.size() == 3 && s.tempo == 120.0 && s.tempoMap[1].curve == TempoCurve::Smooth && s.tempoMap[2].curve == TempoCurve::Step,
          "\"tempoMap\" parsed (curves, tempo = the first bpm)");
    d["tempo"] = 120;
    check(throwsConfig(d, "not both"), "\"tempo\" and \"tempoMap\" together rejected");
    d = doc;
    check(throwsConfig(d, "missing required 'tempo'"), "neither rejected");
    const auto rejects = [&](json map, const std::string& expect) {
        json x = doc;
        x["tempoMap"] = map;
        return throwsConfig(x, expect);
    };
    check(rejects({{1, 120}}, "first point must be at beat 0"), "first point not at beat 0 rejected");
    check(rejects({{0, 120}, {4, 100}, {4, 90}}, "strictly increasing"), "repeated beat rejected");
    check(rejects({{0, 120}, {4, 100, "exp"}}, "tempo curve must be linear|smooth|step"), "curve 'exp' rejected");
    check(rejects({{0, 120}, {4, 0.5}}, "bpm must be in 1..1000"), "bpm out of range rejected");
    check(rejects({{0, 120, "linear", 3}}, "[beat, bpm]"), "point with 4 entries rejected");
    check(rejects(json::array(), "non-empty"), "empty map rejected");
    const auto rejectsMeter = [&](json meter, const std::string& expect) {
        json x = doc;
        x["tempo"] = 120;
        x["meter"] = meter;
        return throwsConfig(x, expect);
    };
    check(rejectsMeter({{0, 4, 4}, {6, 3, 4}}, "not on a bar line"), "meter change inside a bar rejected");
    check(rejectsMeter({{0, 7, 3}}, "denominator"), "denominator 3 rejected");
    check(rejectsMeter({{0, 2.5, 4}}, "numerator"), "fractional numerator rejected");
    check(rejectsMeter({{4, 3, 4}}, "beat 0"), "meter not starting at beat 0 rejected");
    d = doc;
    d["tempo"] = 120;
    d["meter"] = {{0, 4, 4}, {4, 6, 8}};
    check(as::parseSong(d).meter.size() == 2, "\"meter\" parsed");
    const as::SongTiming t = as::parseTiming(json{{"render", 1}, {"tempo", 99}, {"tempoMap", {{0, 99}, {8, 60}}}, {"sampleRate", 44100}});
    check(t.tempoMap.size() == 2 && t.sampleRate == 44100 && t.tempo == 99.0, "parseTiming reads a report's render block (tempoMap wins)");
}

// ------------------------------------------------------------------------------------------ renders

json busySong() {
    json doc = baseDoc(12, 24);
    json pad = {{"id", "pad"},
                {"instrument", {{"type", "va"},
                                {"params", {{"unison", 3},
                                            {"mods", {{{"source", {{"type", "lfo"}, {"shape", "triangle"}, {"rateBeats", 0.75}, {"mode", "global"}}},
                                                       {"target", "cutoff"}, {"amount", 1.5}},
                                                      {{"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateBeats", 0.5}}}, {"target", "pan"}, {"amount", 0.3}}}}}}}},
                {"fx", {{{"type", "tremolo"}, {"params", {{"sync", "on"}, {"beats", 0.5}, {"depth", 0.4}}}},
                        {{"type", "phaser"}, {"params", {{"sync", "on"}, {"beats", 2}}}},
                        {{"type", "delay"}, {"params", {{"time", 0.75}, {"feedback", 0.4}, {"mix", 0.3}}}},
                        {{"type", "ducker"}, {"params", {{"mode", "tempo"}, {"depth", 6}}}}}},
                {"sends", {{"hall", -8}}},
                {"notes", {{0, 4, 57, 90}, {0, 4, 64, 90}, {4, 4, 55, 90}, {4, 4, 62, 90}, {8, 4, 53, 90}}},
                {"modulators", {{{"target", "gainDb"}, {"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateHz", 1.7}}}, {"mode", "offset"}, {"depth", 3}, {"base", -4}},
                                {{"target", "pan"}, {"source", {{"type", "steps"}, {"values", {-0.5, 0.5, 0}}, {"stepBeats", 0.5}}}, {"mode", "absolute"}},
                                {{"target", "fx.0.depth"}, {"source", {{"type", "envelope"}, {"decayBeats", 0.5}}}, {"mode", "absolute"}, {"min", 0.1}, {"max", 0.6}}}}};
    json keys = {{"id", "keys"}, {"instrument", keysInstrument()}, {"gainDb", -6},
                 {"notes", {{1, 1, 72, 100}, {3.5, 1, 76, 100}, {6, 2, 79, 100}, {9.25, 1, 74, 90}}}};
    json kit = {{"id", "kit"}, {"instrument", {{"type", "drums"}, {"params", json::object()}}},
                {"notes", {{0, 0.25, 36, 120}, {1, 0.25, 38, 110}, {2, 0.25, 36, 120}, {3, 0.25, 38, 110}, {5.5, 0.25, 42, 90}, {10, 0.25, 36, 120}}}};
    doc["tracks"] = {pad, keys, kit};
    doc["buses"] = {{{"id", "hall"}, {"fx", {{{"type", "reverb"}, {"params", {{"mix", 1}, {"predelaybeats", 0.25}}}}}}}};
    doc["master"] = {{"fx", {{{"type", "limiter"}, {"params", json::object()}}}}};
    return doc;
}

void testConstantIdentical() {
    std::cout << "a constant tempo map renders bit-identically to \"tempo\"\n";
    json a = busySong();
    a["tempo"] = 104;
    json b = busySong();
    b["tempoMap"] = {{0, 104}};
    json c = busySong();
    c["tempoMap"] = {{0, 104}, {3, 104}, {6.5, 104, "step"}, {9, 104, "smooth"}};
    const auto wav = [](const char* dir) { return readFile(fs::path(".scratch") / "tempo" / dir / "mix.wav"); };
    renderDoc(a, "const_tempo");
    renderDoc(b, "const_map");
    renderDoc(c, "const_map3");
    check(!wav("const_tempo").empty() && wav("const_tempo") == wav("const_map") && wav("const_tempo") == wav("const_map3"),
          "full render: \"tempo\": 104, [[0, 104]] and a 4-point constant map give the same bytes");
    renderDoc(a, "const_tempo_p", 5.3);
    renderDoc(b, "const_map_p", 5.3);
    renderDoc(c, "const_map3_p", 5.3);
    check(!wav("const_tempo_p").empty() && wav("const_tempo_p") == wav("const_map_p") && wav("const_tempo_p") == wav("const_map3_p"),
          "preview from beat 5.3: the same bytes too");
    json d = busySong();
    d["tempoMap"] = {{0, 104}, {6, 90}};
    renderDoc(d, "ramp_map");
    check(wav("ramp_map") != wav("const_tempo"), "(a real ramp does change the render)");
}

void testOnsets() {
    std::cout << "note onsets land on the analytic times of the tempo map\n";
    const std::vector<as::TempoPoint> pts = {{0, 120}, {4, 120}, {12, 70}, {16, 70}, {20, 140, TempoCurve::Smooth}, {22, 100, TempoCurve::Step}};
    const as::TempoMap map(pts, kSr);
    json doc = baseDoc(26);
    doc["tempoMap"] = tempoPoints(pts);
    json notes = json::array();
    std::vector<double> beats;
    for (double b = 0.0; b < 26.0; b += 1.0) {
        notes.push_back({b, 0.1, 69, 100});
        beats.push_back(b);
    }
    for (double b : {4.5, 13.25, 20.75, 21.9}) {  // off-beat notes inside the ramps
        notes.push_back({b, 0.1, 69, 100});
        beats.push_back(b);
    }
    std::sort(beats.begin(), beats.end());
    std::sort(notes.begin(), notes.end(), [](const json& x, const json& y) { return x[0].get<double>() < y[0].get<double>(); });
    doc["tracks"].push_back({{"id", "click"}, {"instrument", clickInstrument()}, {"notes", notes}});
    const as::WavData w = renderDoc(doc, "onsets");
    const auto on = onsets(w.left, 0.003, 0.3, 400, 1200);
    bool countOk = on.size() == beats.size();
    double worst = 0.0, naive = 0.0;
    const double lat = countOk ? on[0] - std::llround(map.sampleAt(beats[0])) : 0.0;
    for (std::size_t k = 0; countOk && k < beats.size(); ++k) {
        const double expected = static_cast<double>(std::llround(map.sampleAt(beats[k]))) + lat;
        worst = std::max(worst, std::fabs(on[k] - expected));
        naive = std::max(naive, std::fabs(on[k] - (beats[k] * kSr * 60.0 / 120.0 + lat)));
    }
    check(countOk && worst <= 1.0,
          fmt("%d onsets at llround(sampleAt(beat)) +- %.2f samples (constant 120 BPM would be off by %.0f ms)",
              static_cast<int>(on.size()), worst, naive / kSr * 1000.0));
}

void testDelayGrid() {
    std::cout << "tempo-synced delay: echoes on the moving grid\n";
    // ritardando 120 -> 60 over beats 2..10: a click at beat 3, echoes 1 beat apart on the song's beats
    const std::vector<as::TempoPoint> pts = {{0, 120}, {2, 120}, {10, 60}};
    const as::TempoMap map(pts, kSr);
    for (const char* mode : {"stereo", "pingpong"}) {
        json doc = baseDoc(14);
        doc["tempoMap"] = tempoPoints(pts);
        doc["tailSeconds"] = 0.0;
        doc["tracks"].push_back({{"id", "dry"}, {"instrument", clickInstrument()}, {"pan", -1}, {"notes", {{3, 0.05, 69, 100}}}});
        doc["tracks"].push_back({{"id", "wet"}, {"instrument", clickInstrument()}, {"pan", 1}, {"notes", {{3, 0.05, 69, 100}}},
                                 {"fx", {{{"type", "delay"}, {"params", {{"mode", mode}, {"time", 1}, {"feedback", 0.6}, {"mix", 1}, {"highcut", 20000},
                                                                        {"lowcut", 20}, {"width", 0}}}}}}});
        const as::WavData w = renderDoc(doc, std::string("delay_") + mode);
        // where each click's rise starts: while the tempo moves the echoes are resampled (tape-style), so a
        // threshold crossing would read their slightly stretched attack as lateness
        const auto dry = onsets(w.left, 1e-4, 0.05, 400, 2000, true);
        const auto wet = onsets(w.right, 1e-4, 0.05, 400, 2000, true);
        const bool ok = dry.size() == 1 && wet.size() >= 5;
        double worst = 0.0, naive = 0.0;
        std::string list, errs;
        for (std::size_t k = 0; ok && k < 5; ++k) {
            const double expected = map.sampleAt(4.0 + static_cast<double>(k)) - map.sampleAt(3.0);
            const double got = wet[k] - dry[0];
            worst = std::max(worst, std::fabs(got - expected));
            errs += fmt("%s%+.2f", k ? ", " : "", got - expected);
            // what a delay time from the tempo at the echo (instead of the last beat's duration) would give
            naive = std::max(naive, std::fabs(got - (k + 1) * 60.0 / map.bpmAt(4.0 + static_cast<double>(k)) * kSr));
            list += fmt("%s%.1f", k ? ", " : "", got / kSr * 1000.0);
        }
        // (the clicks' onsets are read within ~2 samples: every pass resamples the echo a little, tape-style)
        check(ok && worst < 2.5,
              fmt("%s: echoes 1..5 on the beats after the note (%s ms), errors %s samples (a delay from the current tempo: %.0f ms off)",
                  mode, list.c_str(), errs.c_str(), naive / kSr * 1000.0));
    }
    // Exact, at the module: an impulse between two beats; each echo's centre (first moment of the interpolated
    // impulse) lands where the song is `time` beats later, every repeat too, through a ramp; at the tempo step
    // (beat 8.25) the grid restarts: an echo whose `time` beats span the step counts the beats before it at the
    // new tempo (the delay time changes at once there instead of replaying the window at the speed ratio).
    const std::vector<as::TempoPoint> pts2 = {{0, 120}, {2, 120}, {7, 70, TempoCurve::Smooth}, {8.25, 100, TempoCurve::Step}};
    const as::TempoMap map2(pts2, kSr);
    for (double time : {1.0, 0.75}) {
        auto fx = as::createEffect("delay");
        fx->configure({{"mode", "stereo"}, {"time", time}, {"feedback", 0.5}, {"mix", 1}, {"highcut", 20000}, {"lowcut", 20}});
        fx->setTempoMap(map2);
        as::RenderContext ctx;
        ctx.sampleRate = kSr;
        ctx.bpm = map2.initialBpm();
        fx->prepare(ctx);
        const auto n0 = static_cast<std::size_t>(std::llround(map2.sampleAt(2.5))) + 7;
        const double beat0 = map2.beatAtSample(static_cast<double>(n0));
        const auto frames = static_cast<std::size_t>(map2.sampleAt(beat0 + 6.0 * time)) + 2000;
        std::vector<float> l(frames, 0.0f), r(frames, 0.0f);
        l[n0] = r[n0] = 1.0f;
        for (std::size_t i = 0; i < frames; i += 32) fx->process(l.data() + i, r.data() + i, static_cast<int>(std::min<std::size_t>(32, frames - i)), nullptr, nullptr);
        // delay time at song sample x (the restart rule, written independently) and the echo of a sample
        auto delayAt = [&](double x) {
            const double b = map2.beatAtSample(x), b0 = b - time;
            if (b0 < 8.25 && b >= 8.25) return x - map2.sampleAt(8.25) + (8.25 - b0) * 60.0 * kSr / 100.0;
            return x - map2.sampleAt(b0);
        };
        auto echoOf = [&](double src) {  // the first x with x - delayAt(x) >= src (bisection)
            double lo = src, hi = src + 10.0 * kSr;
            for (int it = 0; it < 200; ++it) {
                const double mid = 0.5 * (lo + hi);
                (mid - delayAt(mid) >= src ? hi : lo) = mid;
            }
            return hi;
        };
        double worst = 0.0, src = static_cast<double>(n0);
        std::string errs;
        for (int k = 1; k <= 6; ++k) {
            const double expected = echoOf(src);
            src = expected;
            double m0 = 0.0, m1 = 0.0;
            for (auto i = static_cast<std::size_t>(expected) - 60; i < static_cast<std::size_t>(expected) + 60; ++i) {
                m0 += l[i];
                m1 += static_cast<double>(i) * l[i];
            }
            const double centre = m1 / m0;
            worst = std::max(worst, std::fabs(centre - expected));
            errs += fmt("%s%+.3f", k > 1 ? ", " : "", centre - expected);
        }
        check(worst < 0.05, fmt("impulse through a %.2f-beat delay: echo centres 1..6 vs the song's beats: %s samples", time, errs.c_str()));
    }
}

// Goertzel power of `f` Hz in x[a, b).
double tonePower(const std::vector<float>& x, std::size_t a, std::size_t b, double f) {
    const double w = 2.0 * kPi * f / kSr, c = 2.0 * std::cos(w);
    double s1 = 0.0, s2 = 0.0;
    for (std::size_t i = a; i < b && i < x.size(); ++i) {
        const double s0 = x[i] + c * s1 - s2;
        s2 = s1;
        s1 = s0;
    }
    return (s1 * s1 + s2 * s2 - c * s1 * s2) / static_cast<double>(b - a);
}

// A fermata-like tempo jump (140 -> 35 BPM, back to 140) under a steady 1 kHz tone: the synced delay and the
// synced reverb predelay change their time at once at each jump (crossfaded) and keep playing the tone at its
// pitch - no replay of the window at a quarter (two octaves down) or four times the speed.
void testTempoJumps() {
    std::cout << "tempo jumps: synced delay / predelay restart their grid (no pitch warp)\n";
    const std::vector<as::TempoPoint> pts = {{0, 140}, {8, 35, TempoCurve::Step}, {10, 140, TempoCurve::Step}};
    const as::TempoMap map(pts, kSr);
    check(map.lastJumpIn(7.0, 8.0) == 8.0 && std::isnan(map.lastJumpIn(8.0, 9.0)) && map.lastJumpIn(8.0, 12.0) == 10.0 &&
              std::isnan(as::TempoMap({{0, 120}, {4, 60}}, kSr).lastJumpIn(0, 10)),
          "lastJumpIn: the jumps in (b0, b1], none for ramps");
    const auto frames = static_cast<std::size_t>(map.sampleAt(13.0));
    struct Case { const char* type; json params; };
    const std::vector<Case> cases = {
        {"delay", {{"time", 0.75}, {"feedback", 0}, {"mix", 1}, {"highcut", 20000}, {"lowcut", 20}}},
        {"delay", {{"mode", "pingpong"}, {"time", 0.5}, {"offset", 50}, {"feedback", 0.4}, {"mix", 1}, {"highcut", 20000}, {"lowcut", 20}}},
        {"reverb", {{"predelaybeats", 0.5}, {"mix", 1}, {"decay", 0.4}, {"moddepth", 0}}},
    };
    for (const Case& c : cases) {
        auto fx = as::createEffect(c.type);
        fx->configure(c.params);
        fx->setTempoMap(map);
        as::RenderContext ctx;
        ctx.sampleRate = kSr;
        ctx.bpm = map.initialBpm();
        fx->prepare(ctx);
        std::vector<float> l(frames), r(frames);
        for (std::size_t i = 0; i < frames; ++i) l[i] = r[i] = static_cast<float>(0.3 * std::sin(2.0 * kPi * 1000.0 * static_cast<double>(i) / kSr));
        for (std::size_t i = 0; i < frames; i += 32) fx->process(l.data() + i, r.data() + i, static_cast<int>(std::min<std::size_t>(32, frames - i)), nullptr, nullptr);
        // windows after each jump (skipping the 30 ms crossfade): the tone vs its two-octave shadows
        double worst = -300.0, bad = 0.0;
        for (double jb : {8.0, 10.0}) {
            const auto a = static_cast<std::size_t>(map.sampleAt(jb) + 0.05 * kSr);
            const auto b = static_cast<std::size_t>(std::min(map.sampleAt(jb + 0.75), map.sampleAt(jb) + 1.0 * kSr));
            for (auto* ch : {&l, &r}) {
                const double tone = tonePower(*ch, a, b, 1000.0);
                const double shadow = std::max(tonePower(*ch, a, b, 250.0), tonePower(*ch, a, b, 4000.0));
                worst = std::max(worst, 10.0 * std::log10(shadow / tone));                bad = std::max(bad, tone > 1e-6 ? 0.0 : 1.0);
            }
        }
        double jumpMax = 0.0;  // largest sample-to-sample step of the output (a sine of 0.3 steps <= 0.04)
        for (std::size_t i = 1; i < frames; ++i) jumpMax = std::max(jumpMax, static_cast<double>(std::fabs(l[i] - l[i - 1])));
        check(bad == 0.0 && worst < -40.0 && jumpMax < 0.08,
              fmt("%s %s: the tone keeps its pitch after the jumps (250 Hz / 4 kHz shadows at %+.0f dB vs the 1 kHz tone), largest step %.3f",
                  c.type, c.params.dump().c_str(), worst, jumpMax));
    }
}

void testModulatorsFollow() {
    std::cout << "track modulators follow the tempo map\n";
    const std::vector<as::TempoPoint> pts = {{0, 120}, {2, 120}, {6, 75, TempoCurve::Smooth}, {9, 140, TempoCurve::Step}};
    const as::TempoMap map(pts, kSr);
    json doc = baseDoc(12);
    doc["tempoMap"] = tempoPoints(pts);
    json t = {{"id", "t"}, {"instrument", clickInstrument()}, {"notes", {{0, 1, 69, 100}}}};
    t["modulators"] = {{{"target", "pan"}, {"source", {{"type", "lfo"}, {"shape", "ramp"}, {"rateBeats", 1}}}, {"mode", "absolute"}, {"min", -1}, {"max", 1}},
                       {{"target", "gainDb"}, {"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateHz", 2.5}}}, {"mode", "absolute"}, {"min", -30}, {"max", -6}}};
    doc["tracks"].push_back(t);
    as::ControlTrace pan, gain;
    pan.node = gain.node = "t";
    pan.target = "pan";
    gain.target = "gainDb";
    renderDoc(doc, "mods_pan", std::nullopt, false, &pan);
    renderDoc(doc, "mods_gain", std::nullopt, false, &gain);
    double errPan = 0.0, errBeat = 0.0, errGain = 0.0;
    for (std::size_t k = 0; k < pan.values.size(); ++k) {
        const double beat = pan.beats[k];
        errBeat = std::max(errBeat, std::fabs(beat - map.beatAtSample(static_cast<double>(k) * 32.0)));
        const double f = beat - std::floor(beat + 1e-9);
        errPan = std::max(errPan, std::fabs(pan.values[k] - (-1.0 + 2.0 * std::max(0.0, f))));
    }
    for (std::size_t k = 0; k < gain.values.size(); ++k) {
        const double sec = map.secondsAt(gain.beats[k]);
        const double ph = sec * 2.5 - std::floor(sec * 2.5);
        errGain = std::max(errGain, std::fabs(gain.values[k] - (-30.0 + 24.0 * 0.5 * (1.0 - std::cos(2.0 * kPi * ph)))));
    }
    check(pan.values.size() > 1000 && errBeat < 1e-9 && errPan < 1e-9,
          fmt("rateBeats lfo: value = the song beat's phase at every block (%d blocks, max err %.1e; block beats %.1e)",
              static_cast<int>(pan.values.size()), errPan, errBeat));
    check(gain.values.size() > 1000 && errGain < 1e-6, fmt("rateHz lfo: phase = song seconds x rate through the ramp (max err %.1e dB)", errGain));
}

void testFxFollow() {
    std::cout << "tempo-synced effects and VA LFOs follow the tempo map\n";
    const std::vector<as::TempoPoint> pts = {{0, 120}, {2, 120}, {10, 60}, {12, 60}, {14, 150, TempoCurve::Smooth}};
    const as::TempoMap map(pts, kSr);
    const auto frames = static_cast<std::size_t>(map.sampleAt(16.0));
    as::RenderContext ctx;
    ctx.sampleRate = kSr;
    ctx.bpm = map.initialBpm();
    // tremolo: sine, 1 beat, depth 1 -> gain 0.5 (1 + cos(2 pi beat)): 0.5 at beat k + 0.25 (falling) / k + 0.75 (rising)
    {
        auto fx = as::createEffect("tremolo");
        fx->configure({{"sync", "on"}, {"beats", 1}, {"depth", 1}, {"shape", "sine"}});
        fx->setTempoMap(map);
        fx->prepare(ctx);
        const auto g = gainCurve(*fx, frames);
        const auto down = crossings(g, 0.5, false), up = crossings(g, 0.5, true);
        const double c = std::exp(-1.0 / (0.0006 * kSr));
        const double lag = 2.0 * c / (1.0 - c);  // two one-pole gain smoothers (kEdgeTau 0.6 ms)
        bool ok = down.size() == 16 && up.size() == 16;
        double worst = 0.0;
        for (std::size_t k = 0; ok && k < 16; ++k) {
            worst = std::max(worst, std::fabs(down[k] - lag - map.sampleAt(k + 0.25)));
            worst = std::max(worst, std::fabs(up[k] - lag - map.sampleAt(k + 0.75)));
        }
        check(ok && worst < 3.0, fmt("tremolo sync: 16 cycles over 16 beats, gain 0.5 at beats k+0.25 / k+0.75 (max err %.2f samples)", worst));
    }
    // ducker tempo mode: every duck starts on the first sample of a beat
    {
        auto fx = as::createEffect("ducker");
        fx->configure({{"mode", "tempo"}, {"rate", 1}, {"depth", 24}, {"attack", 0.5}, {"hold", 0}, {"release", 150}});
        fx->setTempoMap(map);
        fx->prepare(ctx);
        const auto g = gainCurve(*fx, frames);
        std::vector<double> starts;
        for (std::size_t i = 0; i < g.size(); ++i)
            if (g[i] < 1.0f && (i == 0 || g[i - 1] == 1.0f)) starts.push_back(static_cast<double>(i));
        bool ok = starts.size() == 16;
        double worst = 0.0;
        for (std::size_t k = 0; ok && k < 16; ++k) worst = std::max(worst, std::fabs(starts[k] - std::ceil(map.sampleAt(static_cast<double>(k)) - 1e-6)));
        check(ok && worst <= 1.0, fmt("ducker tempo mode: %d ducks, each within %.0f sample of its beat", static_cast<int>(starts.size()), worst));
    }
    // VA: a global synced square gate (open on the beat) and a voice synced lfo on the cutoff
    {
        const json params = {{"osc1.wave", "sine"}, {"osc.retrig", "on"}, {"drift.pitch", 0}, {"drift.cutoff", 0}, {"amp.attack", 0.001},
                             {"amp.sustain", 1}, {"cutoff", 20000}, {"filter.env", 0},
                             {"mods", {{{"source", {{"type", "lfo"}, {"shape", "square"}, {"rateBeats", 1}, {"mode", "global"}, {"unipolar", true}, {"phase", 0.5}}},
                                        {"target", "amp"}, {"amount", -40}}}}};
        auto va = as::createInstrument("va");
        va->configure(params);
        va->setTempoMap(map);
        va->prepare(ctx);
        std::vector<float> l(frames), r(frames);
        va->noteOn(1, 93, 0.9f);
        for (std::size_t i = 0; i < frames; i += 32) va->process(l.data() + i, r.data() + i, static_cast<int>(std::min<std::size_t>(32, frames - i)));
        std::vector<float> env(frames, 0.0f);  // peak over the last 28 samples (> one 1760 Hz period)
        for (std::size_t i = 0; i < frames; ++i) {
            float pk = 0.0f;
            for (std::size_t k = i >= 27 ? i - 27 : 0; k <= i; ++k) pk = std::max(pk, std::fabs(l[k]));
            env[i] = pk;
        }
        float top = 0.0f;
        for (float v : env) top = std::max(top, v);
        const auto opens = crossings(env, 0.5 * top, true);
        bool ok = opens.size() >= 15;
        double lag0 = ok ? opens[1] - map.sampleAt(1.0) : 0.0, spread = 0.0;
        for (std::size_t k = 1; ok && k < 16 && k < opens.size(); ++k)
            spread = std::max(spread, std::fabs(opens[k] - map.sampleAt(static_cast<double>(k)) - lag0));
        check(ok && spread < 30.0 && std::fabs(lag0) < 0.006 * kSr,
              fmt("VA global synced gate opens on every beat of the map (%d openings, de-click lag %.1f ms, spread %.2f ms)",
                  static_cast<int>(opens.size()), lag0 / kSr * 1000.0, spread / kSr * 1000.0));
    }
}

// Module-level preview parity with a tempo map: a module prepared at a song position inside a ramp equals the
// same span of a module prepared at the song start (same input from that position).
void testModulePreview() {
    std::cout << "module previews inside a ramp match full renders\n";
    const std::vector<as::TempoPoint> pts = {{0, 120}, {2, 120}, {10, 70, TempoCurve::Smooth}, {12, 100, TempoCurve::Step}};
    const as::TempoMap map(pts, kSr);
    const double startBeat = map.beatAtSample(std::floor(map.sampleAt(6.3) / 32.0) * 32.0);  // as the renderer rounds
    const auto s0 = static_cast<std::size_t>(std::llround(map.sampleAt(startBeat)));
    const std::size_t frames = s0 + 96000;
    auto input = [&](std::size_t songSample) {  // a signal that starts at the preview's first sample
        if (songSample < s0) return 0.0f;
        const double t = static_cast<double>(songSample - s0) / kSr;
        return static_cast<float>(0.3 * std::sin(2.0 * kPi * 330.0 * t) * std::exp(-3.0 * t) + 0.2 * std::sin(2.0 * kPi * 87.0 * t));
    };
    struct Case { const char* type; json params; double startTol; };
    const std::vector<Case> cases = {
        {"delay", {{"time", 0.75}, {"feedback", 0.5}, {"mix", 0.5}, {"wow", 0.3}}, 1e-5},
        {"tremolo", {{"sync", "on"}, {"beats", 0.5}, {"depth", 0.8}, {"shape", "square"}}, 1e-5},
        {"phaser", {{"sync", "on"}, {"beats", 1.5}}, 1.0},  // (its sweep smoother starts settled in a preview, as at a constant tempo)
        {"ducker", {{"mode", "tempo"}, {"rate", 0.5}, {"depth", 12}}, 1e-5},
        {"reverb", {{"predelaybeats", 0.25}, {"mix", 0.5}}, 1e-5},
    };
    for (const Case& c : cases) {
        std::vector<float> full[2], prev[2];
        for (int pass = 0; pass < 2; ++pass) {
            auto fx = as::createEffect(c.type);
            fx->configure(c.params);
            fx->setTempoMap(map);
            as::RenderContext ctx;
            ctx.sampleRate = kSr;
            ctx.bpm = map.initialBpm();
            ctx.seed = 9;
            ctx.startBeat = pass == 0 ? 0.0 : startBeat;
            fx->prepare(ctx);
            const std::size_t first = pass == 0 ? 0 : s0;
            std::vector<float>* out = pass == 0 ? full : prev;
            out[0].assign(frames - first, 0.0f);
            out[1].assign(frames - first, 0.0f);
            for (std::size_t i = 0; i < frames - first; ++i) out[0][i] = out[1][i] = input(first + i);
            for (std::size_t i = 0; i < frames - first; i += 32) {
                const int n = static_cast<int>(std::min<std::size_t>(32, frames - first - i));
                fx->process(out[0].data() + i, out[1].data() + i, n, nullptr, nullptr);
            }
        }
        double d = 0.0, dStart = 0.0, pk = 0.0;
        for (std::size_t i = 0; i < prev[0].size(); ++i) {
            const double e = std::max(std::fabs(prev[0][i] - full[0][s0 + i]), std::fabs(prev[1][i] - full[1][s0 + i]));
            double& slot = i < static_cast<std::size_t>(0.05 * kSr) ? dStart : d;
            slot = std::max(slot, e);
            pk = std::max(pk, static_cast<double>(std::fabs(full[0][s0 + i])));
        }
        check(pk > 0.01 && d < 1e-5 && dStart < c.startTol,
              fmt("%s: preview from beat %.4f equals the full render (max diff %.1e in the first 50 ms, %.1e after; peak %.2f)", c.type,
                  startBeat, dStart, d, pk));
    }
    // VA: global and voice synced LFOs from the song position
    {
        const json params = {{"unison", 2}, {"osc1.wave", "square"},
                             {"mods", {{{"source", {{"type", "lfo"}, {"shape", "smoothrandom"}, {"rateBeats", 0.75}, {"mode", "global"}}}, {"target", "cutoff"}, {"amount", 2}},
                                       {{"source", {{"type", "lfo"}, {"shape", "triangle"}, {"rateBeats", 0.5}}}, {"target", "pan"}, {"amount", 0.6}},
                                       {{"source", {{"type", "lfo"}, {"shape", "square"}, {"rateBeats", 0.25}, {"mode", "global"}, {"phase", 0.3}}}, {"target", "amp"}, {"amount", -6}}}}};
        std::vector<float> full[2], prev[2];
        for (int pass = 0; pass < 2; ++pass) {
            auto va = as::createInstrument("va");
            va->configure(params);
            va->setTempoMap(map);
            as::RenderContext ctx;
            ctx.sampleRate = kSr;
            ctx.bpm = map.initialBpm();
            ctx.seed = 4;
            ctx.startBeat = pass == 0 ? 0.0 : startBeat;
            va->prepare(ctx);
            const std::size_t first = pass == 0 ? 0 : s0;
            std::vector<float>* out = pass == 0 ? full : prev;
            out[0].assign(frames - first, 0.0f);
            out[1].assign(frames - first, 0.0f);
            for (std::size_t i = 0; i < frames - first; i += 32) {
                if (first + i == s0) va->noteOn(1, 57, 0.8f);
                if (first + i == s0 + 48000) va->noteOn(2, 64, 0.7f);
                const int n = static_cast<int>(std::min<std::size_t>(32, frames - first - i));
                va->process(out[0].data() + i, out[1].data() + i, n);
            }
        }
        double d = 0.0, pk = 0.0;
        for (std::size_t i = 0; i < prev[0].size(); ++i) {
            d = std::max({d, static_cast<double>(std::fabs(prev[0][i] - full[0][s0 + i])), static_cast<double>(std::fabs(prev[1][i] - full[1][s0 + i]))});
            pk = std::max(pk, static_cast<double>(std::fabs(full[0][s0 + i])));
        }
        check(pk > 0.01 && d < 1e-6, fmt("va (global + voice synced lfos): preview equals the full render (max diff %.1e, peak %.2f)", d, pk));
    }
}

void testRenderPreview() {
    std::cout << "renderer: a preview inside a ramp matches the full render\n";
    const std::vector<as::TempoPoint> pts = {{0, 110}, {3, 110}, {11, 64, TempoCurve::Smooth}, {13, 64}, {15, 96}};
    json doc = baseDoc(18);
    doc["tempoMap"] = tempoPoints(pts);
    doc["tailSeconds"] = 0.0;
    const double from = 6.2;  // everything plays from here on (effects start from silence in both renders)
    json pad = {{"id", "pad"},
                {"instrument", {{"type", "va"},
                                {"params", {{"osc1.wave", "saw"}, {"unison", 2},
                                            {"mods", {{{"source", {{"type", "lfo"}, {"shape", "square"}, {"rateBeats", 0.5}, {"mode", "global"}, {"unipolar", true}}},
                                                       {"target", "amp"}, {"amount", -9}},
                                                      {{"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateBeats", 1}}}, {"target", "cutoff"}, {"amount", 1}}}}}}}},
                {"fx", {{{"type", "tremolo"}, {"params", {{"sync", "on"}, {"beats", 0.25}, {"depth", 0.3}}}},
                        {{"type", "delay"}, {"params", {{"time", 0.5}, {"feedback", 0.45}, {"mix", 0.35}}}},
                        {{"type", "ducker"}, {"params", {{"mode", "tempo"}, {"depth", 8}}}}}},
                {"notes", {{from, 3, 57, 90}, {from, 3, 64, 90}, {from + 3, 4, 60, 90}, {from + 7.5, 2, 62, 90}}}};
    json keys = {{"id", "keys"}, {"instrument", keysInstrument()}, {"gainDb", -8},
                 {"notes", {{from + 0.5, 1, 72, 100}, {from + 2.25, 1, 76, 100}, {from + 5, 2, 79, 100}}}};
    // Modulated faders / params start from their static value in any preview (their smoothers are not
    // pre-rolled, also at a constant tempo), so the modulators run on a muted track and are compared as values.
    json ctl = {{"id", "ctl"}, {"instrument", clickInstrument()}, {"mute", true}, {"notes", {{1.0, 0.5, 60, 100}, {from + 1, 0.5, 60, 100}}},
                {"fx", {{{"type", "tremolo"}, {"params", {{"depth", 0.3}}}}}},
                {"automation", {{{"target", "mod.1.rateHz"}, {"points", {{0, 2}, {12, 5}}}}}},
                {"modulators", {{{"target", "pan"}, {"source", {{"type", "lfo"}, {"shape", "triangle"}, {"rateBeats", 1.5}}}, {"mode", "offset"}, {"depth", 0.5}, {"base", 0}},
                                {{"target", "gainDb"}, {"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateHz", 3}}}, {"mode", "offset"}, {"depth", 2}, {"base", -3}},
                                {{"target", "fx.0.depth"}, {"source", {{"type", "envelope"}, {"decayBeats", 0.75}}}, {"mode", "absolute"}, {"min", 0.1}, {"max", 0.5}}}}};
    doc["tracks"] = {pad, keys, ctl};
    const as::WavData full = renderDoc(doc, "parity_full");
    const as::WavData prev = renderDoc(doc, "parity_prev", from);
    const as::TempoMap map(pts, kSr);
    const auto startSample = static_cast<std::size_t>(std::llround(map.sampleAt(from)) / 32 * 32);
    double d = 0.0, dStart = 0.0, pk = 0.0;
    std::size_t worstAt = 0;
    for (std::size_t i = 0; i < prev.left.size() && startSample + i < full.left.size(); ++i) {
        const double e = std::max(std::fabs(prev.left[i] - full.left[startSample + i]), std::fabs(prev.right[i] - full.right[startSample + i]));
        if (i < static_cast<std::size_t>(0.05 * kSr)) {
            dStart = std::max(dStart, e);
        } else if (e > d) {
            d = e;
            worstAt = i;
        }
        pk = std::max(pk, static_cast<double>(std::fabs(full.left[startSample + i])));
    }
    check(!prev.left.empty() && pk > 0.02 && d < 1e-5,
          fmt("preview from beat %.1f (inside a smooth ritardando): max diff %.1e vs the full render after 50 ms (at %.3f s; "
              "%.1e before; peak %.2f)", from, d, worstAt / kSr, dStart, pk));
    const std::size_t k0 = startSample / 32;
    for (const char* target : {"pan", "gainDb", "fx.0.depth"}) {
        as::ControlTrace tf, tp;
        tf.node = tp.node = "ctl";
        tf.target = tp.target = target;
        renderDoc(doc, "parity_full_trace", std::nullopt, false, &tf);
        renderDoc(doc, "parity_prev_trace", from, false, &tp);
        double dt = 0.0;
        bool beatsOk = !tp.values.empty() && std::fabs(tp.firstBeat - map.beatAtSample(static_cast<double>(startSample))) < 1e-12;
        for (std::size_t k = 0; k < tp.values.size() && k0 + k < tf.values.size(); ++k) {
            dt = std::max(dt, std::fabs(tp.values[k] - tf.values[k0 + k]));
            beatsOk = beatsOk && tp.beats[k] == tf.beats[k0 + k];
        }
        check(beatsOk && dt < 1e-9,
              fmt("preview '%s' modulator values and block beats equal the full render's (max diff %.1e)", target, dt));
    }
}

// A held pad through every tempo-synced effect across steps, ramps and a fermata-like drop: the click
// detector of the report finds nothing (tempo-driven delay / predelay moves glide, grids stay continuous).
void testNoClicks() {
    std::cout << "tempo-synced effects stay click-free through tempo steps and ramps\n";
    json doc = baseDoc(20, 24);
    doc["tempoMap"] = {{0, 120}, {6, 70, "step"}, {8, 70}, {12, 140, "smooth"}, {14, 140}, {14.0001, 35, "step"}, {16, 140, "step"}};
    doc["tailSeconds"] = 1.0;
    json pad = {{"id", "pad"},
                {"instrument", {{"type", "va"},
                                {"params", {{"osc1.wave", "saw"}, {"osc2.level", 0.5}, {"osc2.fine", 7}, {"unison", 2}, {"amp.attack", 0.3},
                                            {"amp.release", 0.8}, {"cutoff", 3000},
                                            {"mods", {{{"source", {{"type", "lfo"}, {"shape", "triangle"}, {"rateBeats", 0.5}, {"mode", "global"}}},
                                                       {"target", "cutoff"}, {"amount", 0.5}}}}}}}},
                {"fx", {{{"type", "tremolo"}, {"params", {{"sync", "on"}, {"beats", 0.5}, {"depth", 0.3}}}},
                        {{"type", "phaser"}, {"params", {{"sync", "on"}, {"beats", 2}, {"mix", 0.4}}}},
                        {{"type", "delay"}, {"params", {{"time", 0.75}, {"feedback", 0.5}, {"mix", 0.4}, {"mode", "pingpong"}}}},
                        {{"type", "ducker"}, {"params", {{"mode", "tempo"}, {"depth", 6}, {"release", 180}}}}}},
                {"sends", {{"hall", -8}}},
                {"notes", {{0, 20, 57, 90}, {0, 20, 64, 90}, {0, 20, 69, 85}}},
                {"modulators", {{{"target", "pan"}, {"source", {{"type", "lfo"}, {"shape", "sine"}, {"rateBeats", 1}}}, {"mode", "offset"}, {"depth", 0.3}, {"base", 0}}}}};
    doc["tracks"].push_back(pad);
    doc["buses"] = {{{"id", "hall"}, {"fx", {{{"type", "reverb"}, {"params", {{"mix", 1}, {"predelaybeats", 0.5}}}}}}}};
    renderDoc(doc, "noclicks", std::nullopt, true);
    const json rep = readJsonFile(fs::path(".scratch") / "tempo" / "noclicks" / "report.json");
    check(rep["global"]["clicks"] == 0 && rep["global"]["clicksMasked"] == 0 && rep["clicks"].empty(),
          fmt("no clicks in the mix or any node (%d / %d masked)", rep["global"]["clicks"].get<int>(), rep["global"]["clicksMasked"].get<int>()));
}

void testMeterReport() {
    std::cout << "report: bars follow the meter and the tempo map\n";
    json doc = baseDoc(40, 24);
    doc["tempo"] = 120;
    doc["meter"] = {{0, 4, 4}, {16, 3, 4}, {28, 6, 8}};
    doc["sections"] = {{{"name", "four"}, {"startBeat", 0}, {"endBeat", 16}},
                       {{"name", "waltz"}, {"startBeat", 16}, {"endBeat", 28}},
                       {{"name", "jig"}, {"startBeat", 28}, {"endBeat", 40}}};
    json notes = json::array();
    for (int b = 0; b < 40; ++b) notes.push_back({b, 0.5, 60, 100});
    doc["tracks"].push_back({{"id", "keys"}, {"instrument", {{"type", "va"}, {"params", json::object()}}}, {"notes", notes}});
    renderDoc(doc, "meter", std::nullopt, true);
    const json rep = readJsonFile(fs::path(".scratch") / "tempo" / "meter" / "report.json");
    const json& secs = rep["sections"];
    check(secs.size() == 3 && secs[0]["startBar"] == 1.0 && secs[1]["startBar"] == 5.0 && secs[2]["startBar"] == 9.0 &&
              secs[2]["endBar"] == 13.0 && secs[1]["meter"] == "3/4" && secs[2]["meter"] == "6/8",
          "sections: 'waltz' starts at bar 5 (3/4), 'jig' at bar 9 and ends at bar 13 (6/8 = 3 beats)");
    const json& rows = rep["timeline"]["rows"];
    bool rowsOk = rows.size() >= 12;
    // bar starts (s): 4/4 bars every 2 s, then 3/4 bars every 1.5 s from 8 s, 6/8 bars every 1.5 s from 14 s
    const double expect[] = {0, 2, 4, 6, 8, 9.5, 11, 12.5, 14, 15.5, 17, 18.5};
    for (std::size_t i = 0; rowsOk && i < 12; ++i) rowsOk = rows[i][0] == static_cast<int>(i) + 1 && std::fabs(rows[i][1].get<double>() - expect[i]) < 0.006;
    check(rowsOk, "timeline: one row per song bar, bar starts 0, 2, 4, 6, 8, 9.5, ... s");
    check(rep["global"]["meter"].size() == 3 && rep["global"]["meter"][1][0] == 5 && rep["global"]["meter"][1][1] == "3/4" &&
              rep["render"]["meter"].size() == 3,
          "global.meter lists the meters with their first bar; render.meter repeats the JSON");

    // tempo info with a map
    json m = doc;
    m.erase("tempo");
    m["tempoMap"] = {{0, 120}, {16, 120}, {28, 60, "linear"}};
    renderDoc(m, "meter_map", std::nullopt, true);
    const json rm = readJsonFile(fs::path(".scratch") / "tempo" / "meter_map" / "report.json");
    const json& s2 = rm["sections"];
    const as::TempoMap map({{0, 120}, {16, 120}, {28, 60}}, kSr);
    const double waltzEnd = map.secondsAt(28.0);
    check(s2.size() == 3 && std::fabs(s2[1]["endSec"].get<double>() - waltzEnd) < 0.006 && s2[0]["bpm"] == 120.0 &&
              s2[1]["bpmStart"] == 120.0 && s2[1]["bpmEnd"] == 60.0 && rm["global"]["bpmRange"][0] == 60.0 &&
              rm["render"]["tempoMap"].size() == 3,
          fmt("sections in seconds through the map ('waltz' ends at %.2f s), section bpm / bpmStart / bpmEnd, bpmRange", waltzEnd));
}

}  // namespace

int main() {
    fs::create_directories(fs::path(".scratch") / "tempo");
    std::cout << "test_tempo\n";
    testTempoMath();
    testMeterMath();
    testParse();
    testConstantIdentical();
    testOnsets();
    testDelayGrid();
    testTempoJumps();
    testModulatorsFollow();
    testFxFollow();
    testModulePreview();
    testRenderPreview();
    testNoClicks();
    testMeterReport();
    std::cout << (failures ? "FAILED" : "PASSED") << " (" << failures << " failures)\n";
    return failures ? 1 : 0;
}
