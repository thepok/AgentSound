// Tests for the "va" virtual-analog instrument: pitch, filters, envelopes, unison, voice
// management, glide, stability, determinism, aliasing, the modulation matrix ("mods": sources,
// targets, strictness, amount automation, preview parity), FM, stereo noise and speed.

#include "instruments/VaSynth.h"
#include "dsp/Dsp.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <set>
#include <string>
#include <vector>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <time.h>
#endif

using as::json;

namespace {

int failures = 0;

void check(bool ok, const std::string& what) {
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << "\n";
    if (!ok) ++failures;
}

constexpr double kPi = 3.14159265358979323846;

template <typename... A>
std::string fmt(const char* f, A... a) {
    char buf[512];
    std::snprintf(buf, sizeof buf, f, a...);
    return buf;
}

struct Ev {
    long t;
    int type;  // 0 on, 1 off, 2 param
    int id = 0, pitch = 0;
    float vel = 0.8f;
    std::string name;
    float value = 0.0f;
};
Ev on(double sec, int id, int pitch, float vel, double sr) { return {static_cast<long>(sec * sr), 0, id, pitch, vel, "", 0}; }
Ev off(double sec, int id, double sr) { return {static_cast<long>(sec * sr), 1, id, 0, 0, "", 0}; }
Ev prm(double sec, const std::string& n, float v, double sr) { return {static_cast<long>(sec * sr), 2, 0, 0, 0, n, v}; }

struct Out {
    std::vector<float> L, R;
    double sr;
};

std::unique_ptr<as::Instrument> make(const json& params, double sr = 48000, std::uint64_t seed = 1, double bpm = 120,
                                     double startBeat = 0.0) {
    auto inst = as::makeVaSynth();
    inst->configure(params);
    as::RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.seed = seed;
    ctx.bpm = bpm;
    ctx.startBeat = startBeat;
    inst->prepare(ctx);
    return inst;
}

// Minimal host: splits blocks at events (sample accurate), max 256 frames per block.
Out render(as::Instrument& inst, std::vector<Ev> evs, double seconds, double sr) {
    std::stable_sort(evs.begin(), evs.end(), [](const Ev& a, const Ev& b) { return a.t < b.t; });
    const long total = static_cast<long>(seconds * sr);
    Out o{std::vector<float>(static_cast<std::size_t>(total)), std::vector<float>(static_cast<std::size_t>(total)), sr};
    long pos = 0;
    std::size_t ei = 0;
    while (pos < total) {
        while (ei < evs.size() && evs[ei].t <= pos) {
            const Ev& e = evs[ei++];
            if (e.type == 0) inst.noteOn(e.id, e.pitch, e.vel);
            else if (e.type == 1) inst.noteOff(e.id);
            else inst.setParam(e.name, e.value);
        }
        long next = std::min(total, pos + 256);
        if (ei < evs.size()) next = std::min(next, std::max(pos + 1, evs[ei].t));
        inst.process(&o.L[static_cast<std::size_t>(pos)], &o.R[static_cast<std::size_t>(pos)], static_cast<int>(next - pos));
        pos = next;
    }
    return o;
}

Out renderPatch(const json& params, const std::vector<Ev>& evs, double seconds, double sr = 48000, std::uint64_t seed = 1) {
    auto inst = make(params, sr, seed);
    return render(*inst, evs, seconds, sr);
}

bool allFinite(const Out& o) {
    for (std::size_t i = 0; i < o.L.size(); ++i)
        if (!std::isfinite(o.L[i]) || !std::isfinite(o.R[i])) return false;
    return true;
}
float peak(const Out& o) {
    float p = 0;
    for (std::size_t i = 0; i < o.L.size(); ++i) p = std::max({p, std::fabs(o.L[i]), std::fabs(o.R[i])});
    return p;
}
double rms(const std::vector<float>& x, double sr, double a, double b) {
    const std::size_t i0 = static_cast<std::size_t>(a * sr), i1 = std::min(x.size(), static_cast<std::size_t>(b * sr));
    double s = 0;
    for (std::size_t i = i0; i < i1; ++i) s += double(x[i]) * x[i];
    return std::sqrt(s / double(std::max<std::size_t>(1, i1 - i0)));
}
double db(double x) { return 20.0 * std::log10(std::max(x, 1e-12)); }
float maxDiff(const Out& a, const Out& b) {
    float d = 0;
    for (std::size_t i = 0; i < a.L.size() && i < b.L.size(); ++i)
        d = std::max({d, std::fabs(a.L[i] - b.L[i]), std::fabs(a.R[i] - b.R[i])});
    return d;
}

// Mean frequency from upward zero crossings (linear interpolation) in [a,b] seconds.
double measureHz(const std::vector<float>& x, double sr, double a, double b) {
    const std::size_t i0 = static_cast<std::size_t>(a * sr), i1 = std::min(x.size(), static_cast<std::size_t>(b * sr));
    double first = -1, last = -1;
    int count = 0;
    for (std::size_t i = i0 + 1; i < i1; ++i) {
        if (x[i - 1] < 0.0f && x[i] >= 0.0f) {
            const double t = double(i - 1) + x[i - 1] / (x[i - 1] - x[i]);
            if (first < 0) first = t;
            last = t;
            ++count;
        }
    }
    if (count < 2) return 0.0;
    return (count - 1) / ((last - first) / sr);
}

// Hann-windowed Goertzel amplitude at frequency f in [a,b] seconds.
double tone(const std::vector<float>& x, double sr, double f, double a, double b) {
    const std::size_t i0 = static_cast<std::size_t>(a * sr), i1 = std::min(x.size(), static_cast<std::size_t>(b * sr));
    const std::size_t n = i1 - i0;
    std::complex<double> acc = 0;
    double wsum = 0;
    for (std::size_t i = 0; i < n; ++i) {
        const double w = 0.5 - 0.5 * std::cos(2 * kPi * double(i) / double(n - 1));
        acc += w * double(x[i0 + i]) * std::polar(1.0, -2 * kPi * f * double(i) / sr);
        wsum += w;
    }
    return 2.0 * std::abs(acc) / wsum;
}

void fft(std::vector<std::complex<double>>& a) {
    const std::size_t n = a.size();
    for (std::size_t i = 1, j = 0; i < n; ++i) {
        std::size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    for (std::size_t len = 2; len <= n; len <<= 1) {
        const std::complex<double> wl = std::polar(1.0, -2 * kPi / double(len));
        for (std::size_t i = 0; i < n; i += len) {
            std::complex<double> w = 1;
            for (std::size_t k = 0; k < len / 2; ++k) {
                const auto u = a[i + k], v = a[i + k + len / 2] * w;
                a[i + k] = u + v;
                a[i + k + len / 2] = u - v;
                w *= wl;
            }
        }
    }
}

// Energy of everything that is not a harmonic of f0 (below 20 kHz) relative to the harmonic energy.
double inharmonicDb(const std::vector<float>& x, double sr, double f0, double start) {
    const std::size_t n = 32768, i0 = static_cast<std::size_t>(start * sr);
    std::vector<std::complex<double>> a(n);
    for (std::size_t i = 0; i < n; ++i) {  // 4-term Blackman-Harris
        const double t = 2 * kPi * double(i) / double(n - 1);
        const double w = 0.35875 - 0.48829 * std::cos(t) + 0.14128 * std::cos(2 * t) - 0.01168 * std::cos(3 * t);
        a[i] = w * double(x[i0 + i]);
    }
    fft(a);
    double harm = 0, other = 0;
    const double binHz = sr / double(n);
    for (std::size_t k = 1; k < n / 2; ++k) {
        const double f = double(k) * binHz;
        if (f > 20000.0) break;
        const double e = std::norm(a[k]);
        const double h = f / f0;
        const double distBins = std::fabs(h - std::round(h)) * f0 / binHz;
        if (std::round(h) >= 1 && distBins <= 6.0) harm += e;
        else other += e;
    }
    return 10.0 * std::log10(std::max(other, 1e-30) / std::max(harm, 1e-30));
}

// Times (s) where the energy envelope (2 ms moving average of x^2) rises through `level` (linear
// amplitude), in [a, b].
std::vector<double> risingEdges(const std::vector<float>& x, double sr, double level, double a, double b) {
    const long w = static_cast<long>(0.002 * sr);
    const long i0 = static_cast<long>(a * sr), i1 = std::min(static_cast<long>(x.size()) - w, static_cast<long>(b * sr));
    const double thr = 0.5 * level * level;  // mean of a sine's square
    std::vector<double> t;
    double e = 0;
    for (long i = i0 - w / 2; i < i0 + w / 2; ++i) e += double(x[static_cast<std::size_t>(i)]) * x[static_cast<std::size_t>(i)];
    double prev = e / w;
    for (long i = i0 + 1; i < i1; ++i) {
        const double in = x[static_cast<std::size_t>(i + w / 2 - 1)], outv = x[static_cast<std::size_t>(i - w / 2 - 1)];
        e += in * in - outv * outv;
        const double cur = e / w;
        if (prev < thr && cur >= thr) t.push_back((double(i - 1) + (thr - prev) / (cur - prev)) / sr);
        prev = cur;
    }
    return t;
}

json clean(json extra = json::object()) {  // deterministic, open filter, no analog drift
    json j = {{"drift.pitch", 0}, {"drift.cutoff", 0}, {"cutoff", 20000}, {"resonance", 0}, {"filter.env", 0},
              {"filter.keytrack", 0}, {"filter.velocity", 0}, {"filter.drive", 0}, {"amp.velocity", 0},
              {"amp.attack", 0.002}, {"amp.sustain", 1.0}};
    for (auto it = extra.begin(); it != extra.end(); ++it) j[it.key()] = it.value();
    return j;
}
json merged(json a, const json& b) {
    for (auto it = b.begin(); it != b.end(); ++it) a[it.key()] = it.value();
    return a;
}

// Modulation-matrix builders.
json lfoHz(const char* shape, double hz, json extra = json::object()) {
    return merged({{"type", "lfo"}, {"shape", shape}, {"rateHz", hz}}, extra);
}
json lfoBeats(const char* shape, double beats, json extra = json::object()) {
    return merged({{"type", "lfo"}, {"shape", shape}, {"rateBeats", beats}}, extra);
}
json envSrc(double a, double d, double s, double r, const char* curve = "exp") {
    return {{"type", "env"}, {"attack", a}, {"decay", d}, {"sustain", s}, {"release", r}, {"curve", curve}};
}
json macroSrc(int i) { return {{"type", "macro"}, {"index", i}}; }
json route(const json& src, const char* target, double amount, const std::string& id = "") {
    json r = {{"source", src}, {"target", target}, {"amount", amount}};
    if (!id.empty()) r["id"] = id;
    return r;
}
json withMods(json params, json mods) {  // (a one-element braced list {route(...)} is the route itself)
    params["mods"] = mods.is_object() ? json::array({mods}) : std::move(mods);
    return params;
}
bool throwsConfig(const json& j, std::string* msg = nullptr) {
    try {
        make(j);
    } catch (const as::ConfigError& e) {
        if (msg) *msg = e.what();
        return true;
    }
    return false;
}

// ---------------------------------------------------------------------------------------------

void testSpecs() {
    std::cout << "specs & configuration\n";
    auto inst = as::makeVaSynth();
    const auto& specs = inst->paramSpecs();
    std::set<std::string> names;
    bool okRanges = true, okHelp = true;
    for (const auto& s : specs) {
        names.insert(s.name);
        okRanges &= s.min <= s.def && s.def <= s.max;
        okHelp &= s.help.size() > 10;
    }
    check(names.size() == specs.size(), "parameter names are unique (" + std::to_string(specs.size()) + " params)");
    check(okRanges && okHelp, "defaults inside ranges, every parameter has help text");
    bool haveAll = true;
    for (const char* n : {"osc1.wave", "osc1.level", "osc1.pw", "osc2.semi", "osc2.fine", "osc2.level", "osc2.sync",
                          "osc2.phase", "fm", "sub.level", "sub.octave", "noise.level", "noise.color", "noise.stereo",
                          "unison", "unison.detune", "unison.spread", "drift.pitch", "drift.cutoff", "filter.type",
                          "cutoff", "resonance", "filter.drive", "filter.keytrack", "filter.env", "filter.velocity",
                          "amp.attack", "amp.decay", "amp.sustain", "amp.release", "amp.velocity", "fenv.attack",
                          "fenv.decay", "fenv.sustain", "fenv.release", "macro1", "macro8", "mods", "mode",
                          "polyphony", "glide", "pitchbend", "level", "pan"})
        haveAll &= names.count(n) == 1;
    check(haveAll, "all required parameters are declared");
    bool noLegacy = true;  // the fixed LFOs / pitch envelope are gone (current format only)
    for (const auto& s : specs)
        noLegacy &= s.name.rfind("lfo1.", 0) != 0 && s.name.rfind("lfo2.", 0) != 0 && s.name != "fenv.pitch" &&
                    s.name != "fenv.osc2";
    check(noLegacy, "no lfo1.* / lfo2.* / fenv.pitch / fenv.osc2 parameters any more");
    check(throwsConfig({{"lfo1.pitch", 10}}) && throwsConfig({{"fenv.pitch", 12}}), "old fixed-modulation params are rejected");

    check(throwsConfig({{"cutof", 100}}), "unknown key is rejected");
    check(throwsConfig({{"cutoff", 5}}), "out-of-range value is rejected");
    check(throwsConfig({{"unison", 2.5}}), "fractional unison is rejected");
    check(throwsConfig({{"filter.type", "lp24"}}), "unknown enum choice is rejected");
    check(throwsConfig({{"cutoff", "high"}}), "wrong type is rejected");
    check(!throwsConfig({{"filter.type", "notch"}, {"osc2.sync", true}, {"mode", "legato"}, {"unison", 9}}),
          "valid enum strings / booleans are accepted");
    check(!inst->setParam("nope", 1.0f) && !inst->setParam("unison", 3.0f) && inst->setParam("cutoff", 500.0f) &&
              !inst->setParam("mods", 1.0f) && inst->setParam("macro3", 0.5f),
          "setParam: unknown / structural params and 'mods' refused, cutoff and macros accepted");
}

void testModConfig() {
    std::cout << "modulation matrix: configuration (strict)\n";
    const json vib = route(lfoHz("sine", 5.5, {{"delay", 0.3}}), "pitch", 15, "vib");
    // accepted: parameters appear per routing, named by id or index
    auto inst = make(withMods(json::object(), {vib, route(envSrc(0, 0.2, 0, 0.2), "cutoff", 2),
                                               route(macroSrc(2), "hpf", 1.5, "hp")}));
    const auto& specs = inst->paramSpecs();
    const as::ParamSpec* a = nullptr;
    const as::ParamSpec* b = nullptr;
    const as::ParamSpec* c = nullptr;
    for (const auto& s : specs) {
        if (s.name == "mod.vib.amount") a = &s;
        if (s.name == "mod.1.amount") b = &s;
        if (s.name == "mod.hp.amount") c = &s;
    }
    check(a && b && c && a->automatable && a->def == 15.0f && a->min == -4800.0f && a->unit == "ct" && b->unit == "oct" &&
              c->def == 1.5f && a->help.find("lfo sine") != std::string::npos,
          "each routing adds an automatable 'mod.<id|index>.amount' (range / unit of its target, default = amount)");
    check(inst->setParam("mod.vib.amount", 30.0f) && inst->setParam("mod.1.amount", -1.0f) && !inst->setParam("mod.2.amount", 1.0f),
          "setParam accepts the amounts by id / index (an id'd routing has no index name)");
    auto over = make(withMods({{"mod.vib.amount", 40}}, {vib}));
    float ov = 0;
    for (const auto& s : over->paramSpecs())
        if (s.name == "mod.vib.amount") ov = s.def;
    check(ov == 15.0f, "a flat 'mod.<id>.amount' key is accepted (overrides the entry's amount)");

    struct Bad { json params; const char* what; };
    const json okSrc = lfoHz("sine", 5);
    std::vector<json> many;
    for (int i = 0; i < 65; ++i) many.push_back(route(okSrc, "cutoff", 0.1));
    const std::vector<Bad> bad = {
        {{{"mods", json::array({json{{"target", "cutoff"}, {"amount", 1}}})}}, "a routing without source"},
        {{{"mods", json::object()}}, "mods not a list"},
        {{{"mods", json::array({1})}}, "a routing that is not an object"},
        {withMods({}, {merged(route(okSrc, "cutoff", 1), {{"depth", 1}})}), "unknown routing key"},
        {withMods({}, {route(okSrc, "filter.cutoff", 1)}), "unknown target"},
        {withMods({}, {route({{"type", "wobble"}}, "cutoff", 1)}), "unknown source type"},
        {withMods({}, {route(merged(okSrc, {{"rate", 2}}), "cutoff", 1)}), "unknown lfo key"},
        {withMods({}, {route({{"type", "lfo"}, {"shape", "sine"}}, "cutoff", 1)}), "lfo without a rate"},
        {withMods({}, {route(merged(okSrc, {{"rateBeats", 1}}), "cutoff", 1)}), "lfo with rateHz and rateBeats"},
        {withMods({}, {route(lfoHz("sine", 0), "cutoff", 1)}), "rateHz 0"},
        {withMods({}, {route(lfoHz("wiggle", 1), "cutoff", 1)}), "unknown lfo shape"},
        {withMods({}, {route(lfoHz("sine", 1, {{"phase", 1.5}}), "cutoff", 1)}), "phase 1.5"},
        {withMods({}, {route(lfoHz("sine", 1, {{"mode", "poly"}}), "cutoff", 1)}), "unknown lfo mode"},
        {withMods({}, {route(lfoHz("sine", 1, {{"unipolar", 1}}), "cutoff", 1)}), "unipolar not a bool"},
        {withMods({}, {route(envSrc(0, 0.1, 2, 0.1), "cutoff", 1)}), "env sustain 2"},
        {withMods({}, {route(envSrc(0, 0.1, 0, 0.1, "log"), "cutoff", 1)}), "unknown env curve"},
        {withMods({}, {route(okSrc, "cutoff", 11)}), "cutoff amount 11 oct"},
        {withMods({}, {route(okSrc, "amp", 30)}), "amp amount +30 dB"},
        {withMods({}, {route(okSrc, "cutoff", 1, "a"), route(okSrc, "pan", 1, "a")}), "duplicate id"},
        {withMods({}, {route(okSrc, "cutoff", 1, "Vib")}), "id with capitals"},
        {withMods({}, {route(okSrc, "cutoff", 1, "3x")}), "id starting with a digit"},
        {withMods({}, {{{"source", okSrc}, {"target", "cutoff"}, {"amount", "1"}}}), "amount as a string"},
        {withMods({}, {route(okSrc, "hpf", 1)}), "per-voice lfo -> global hpf"},
        {withMods({}, {route(envSrc(0, 0.1, 0, 0.1), "hpf", 1)}), "env -> global hpf"},
        {withMods({}, {route(lfoHz("sine", 1, {{"mode", "global"}, {"delay", 0.5}}), "hpf", 1)}), "global lfo with delay -> hpf"},
        {withMods({}, {route(macroSrc(9), "cutoff", 1)}), "macro index 9"},
        {withMods({}, {route(macroSrc(0), "cutoff", 1)}), "macro index 0"},
        {withMods({}, {route({{"type", "macro"}, {"index", 1.5}}, "cutoff", 1)}), "fractional macro index"},
        {withMods({}, {route({{"type", "macro"}}, "cutoff", 1)}), "macro without index"},
        {withMods({}, {route({{"type", "key"}, {"low", 40}}, "cutoff", 1)}), "key with low only"},
        {withMods({}, {route({{"type", "key"}, {"low", 60}, {"high", 40}}, "cutoff", 1)}), "key high below low"},
        {withMods({}, {route({{"type", "random"}, {"seed", -1}}, "cutoff", 1)}), "random seed -1"},
        {withMods({}, {route({{"type", "velocity"}, {"curve", "exp"}}, "cutoff", 1)}), "velocity with a field"},
        {withMods({}, many), "65 routings"},
        {withMods({{"mod.nope.amount", 1}}, {vib}), "flat amount of a routing that does not exist"},
        {withMods({{"mod.vib.amount", 5000}}, {vib}), "flat amount outside the target range"},
        {{{"fm", 2}}, "fm with a saw osc1"},
        {withMods({}, {route(envSrc(0, 0.2, 0, 0.2), "fm", 3)}), "an fm routing with a saw osc1"},
    };
    int rejected = 0;
    std::string firstMissed;
    for (const auto& b2 : bad) {
        if (throwsConfig(b2.params)) ++rejected;
        else if (firstMissed.empty()) firstMissed = b2.what;
    }
    check(rejected == static_cast<int>(bad.size()),
          fmt("%d of %zu invalid matrices rejected with a ConfigError", rejected, bad.size()) +
              (firstMissed.empty() ? "" : " (accepted: " + firstMissed + ")"));
    std::string msg;
    throwsConfig(withMods({}, {route(okSrc, "cutof", 1)}), &msg);
    check(msg.find("mods[0]") != std::string::npos && msg.find("cutoff") != std::string::npos,
          "errors name the routing and list the valid targets: " + msg.substr(0, 90) + "...");
    std::vector<json> sixtyFour(many.begin(), many.begin() + 64);
    check(!throwsConfig(withMods({}, sixtyFour)), "64 routings are accepted");
    check(!throwsConfig(withMods({{"osc1.wave", "sine"}, {"fm", 1}}, {route(envSrc(0, 0.2, 0, 0.2), "fm", 3)})),
          "fm with a sine osc1 is accepted");
}

void testPitch() {
    std::cout << "pitch accuracy\n";
    for (double sr : {44100.0, 48000.0, 96000.0}) {
        auto o = renderPatch(clean({{"osc1.wave", "sine"}}), {on(0, 1, 69, 0.8f, sr)}, 1.2, sr);
        const double f = measureHz(o.L, sr, 0.2, 1.2);
        check(std::fabs(f - 440.0) < 0.5, fmt("sine A4 at %.0f Hz sample rate = %.4f Hz", sr, f));
    }
    const double sr = 48000;
    auto o2 = renderPatch(clean({{"osc1.level", 0}, {"osc2.level", 1}, {"osc2.wave", "sine"}, {"osc2.semi", 7}}),
                          {on(0, 1, 69, 0.8f, sr)}, 1.2, sr);
    const double f2 = measureHz(o2.L, sr, 0.2, 1.2), want2 = 440.0 * std::pow(2.0, 7.0 / 12.0);
    check(std::fabs(f2 - want2) < 0.5, fmt("osc2 +7 st = %.3f Hz (want %.3f)", f2, want2));
    auto o3 = renderPatch(clean({{"osc1.level", 0}, {"osc2.level", 1}, {"osc2.wave", "sine"}, {"osc2.semi", -12},
                                 {"osc2.fine", 50}}),
                          {on(0, 1, 69, 0.8f, sr)}, 1.2, sr);
    const double f3 = measureHz(o3.L, sr, 0.2, 1.2), want3 = 440.0 * std::pow(2.0, -11.5 / 12.0);
    check(std::fabs(f3 - want3) < 0.5, fmt("osc2 -12 st +50 ct = %.3f Hz (want %.3f)", f3, want3));
    for (int oct : {-1, -2}) {
        auto o = renderPatch(clean({{"osc1.level", 0}, {"sub.level", 1}, {"sub.octave", oct}}),
                             {on(0, 1, 69, 0.8f, sr)}, 1.2, sr);
        const double f = measureHz(o.L, sr, 0.2, 1.2), want = 440.0 * std::pow(2.0, oct);
        check(std::fabs(f - want) < 0.5, fmt("sub octave %d = %.3f Hz", oct, f));
    }
    auto ob = renderPatch(clean({{"osc1.wave", "sine"}}), {on(0, 1, 57, 0.8f, sr), prm(0.1, "pitchbend", 12, sr)}, 1.2, sr);
    const double fb = measureHz(ob.L, sr, 0.4, 1.2);
    check(std::fabs(fb - 440.0) < 0.5, fmt("pitchbend +12 on A3 = %.3f Hz", fb));
}

void testFilter() {
    std::cout << "filters\n";
    const double sr = 48000;
    auto hiEnergy = [&](const Out& o) {  // energy above ~2 kHz (4th-order high-pass)
        as::dsp::Biquad a, b;
        a.set(as::dsp::Biquad::Type::HighPass, sr, 2000, 0.7071);
        b.set(as::dsp::Biquad::Type::HighPass, sr, 2000, 0.7071);
        std::vector<float> y(o.L.size());
        for (std::size_t i = 0; i < y.size(); ++i) y[i] = b.process(a.process(o.L[i]));
        return rms(y, sr, 0.3, 1.0);
    };
    for (const char* type : {"ladder", "lp12"}) {
        auto lo = renderPatch(clean({{"filter.type", type}, {"cutoff", 200}}), {on(0, 1, 45, 0.8f, sr)}, 1.0, sr);
        auto hi = renderPatch(clean({{"filter.type", type}, {"cutoff", 8000}}), {on(0, 1, 45, 0.8f, sr)}, 1.0, sr);
        const double d = db(hiEnergy(hi)) - db(hiEnergy(lo));
        check(d > 30.0, fmt("%s: partials above 2 kHz are %.1f dB weaker at cutoff 200 than at 8000", type, d));
    }
    auto lowBand = [&](const Out& o) { return tone(o.L, sr, 110.0, 0.3, 1.0); };
    auto hp = renderPatch(clean({{"filter.type", "hp12"}, {"cutoff", 2000}}), {on(0, 1, 45, 0.8f, sr)}, 1.0, sr);
    auto lp = renderPatch(clean({{"filter.type", "lp12"}, {"cutoff", 2000}}), {on(0, 1, 45, 0.8f, sr)}, 1.0, sr);
    check(db(lowBand(lp)) - db(lowBand(hp)) > 30.0, fmt("hp12 removes the 110 Hz fundamental (%.1f dB)", db(lowBand(lp)) - db(lowBand(hp))));
    // Envelope sweep: filter.env opens the filter at the start of a pluck.
    auto pl = renderPatch(clean({{"cutoff", 300}, {"filter.env", 5}, {"fenv.decay", 0.3}, {"fenv.sustain", 0}}),
                          {on(0, 1, 45, 0.8f, sr)}, 1.0, sr);
    const double early = tone(pl.L, sr, 110 * 12, 0.01, 0.06), late = tone(pl.L, sr, 110 * 12, 0.7, 0.95);
    check(db(early) - db(late) > 20, fmt("filter envelope: 12th harmonic %.1f dB louder at the attack", db(early) - db(late)));
    // the filter envelope sustains (filter.env uses fenv.sustain)
    auto f = renderPatch(clean({{"cutoff", 200}, {"filter.env", 5}, {"fenv.decay", 0.1}, {"fenv.sustain", 1.0}}),
                         {on(0, 1, 45, 0.8f, sr)}, 1.0, sr);
    auto g = renderPatch(clean({{"cutoff", 200}, {"filter.env", 5}, {"fenv.decay", 0.1}, {"fenv.sustain", 0.0}}),
                         {on(0, 1, 45, 0.8f, sr)}, 1.0, sr);
    const double d = db(tone(f.L, sr, 110 * 12, 0.6, 0.95)) - db(tone(g.L, sr, 110 * 12, 0.6, 0.95));
    check(d > 20, fmt("filter envelope sustain holds the filter open (%.1f dB brighter at sustain 1)", d));
}

void testRelease() {
    std::cout << "envelopes\n";
    const double sr = 48000;
    auto inst = make({{"amp.release", 0.25}});
    auto o = render(*inst, {on(0, 1, 60, 0.8f, sr), off(0.5, 1, sr)}, 0.9, sr);
    check(inst->idle(), "idle() is true after the release (0.25 s) has finished");
    check(rms(o.L, sr, 0.2, 0.45) > 0.01, fmt("sustain is audible (%.1f dBFS RMS)", db(rms(o.L, sr, 0.2, 0.45))));
    check(rms(o.L, sr, 0.8, 0.9) < 1e-5, fmt("output is silent after the release (%.1f dBFS)", db(rms(o.L, sr, 0.8, 0.9))));
    auto inst2 = make({{"amp.release", 0.25}});
    render(*inst2, {on(0, 1, 60, 0.8f, sr), off(0.5, 1, sr)}, 0.6, sr);
    check(!inst2->idle(), "idle() is false during the release tail");
    // Attack click check: the first milliseconds rise smoothly (no sample-to-sample jump > 0.05).
    auto a = renderPatch({{"amp.attack", 0.001}, {"osc.retrig", true}}, {on(0, 1, 40, 1.0f, sr)}, 0.05, sr);
    float jump = 0;
    for (std::size_t i = 1; i < 96; ++i) jump = std::max(jump, std::fabs(a.L[i] - a.L[i - 1]));
    check(jump < 0.05f, fmt("1 ms attack has no click (max step %.4f)", jump));
    // Pluck with sustain 0 frees its voice while the key is still held.
    auto inst3 = make({{"amp.sustain", 0}, {"amp.decay", 0.2}});
    render(*inst3, {on(0, 1, 60, 0.8f, sr)}, 0.6, sr);
    check(inst3->idle(), "sustain-0 pluck becomes idle once it has decayed (key still held)");
}

void testDeterminism() {
    std::cout << "determinism\n";
    const double sr = 48000;
    json p = withMods({{"unison", 5}, {"noise.level", 0.3}, {"noise.color", "pink"}, {"noise.stereo", 0.7}, {"drift.pitch", 8},
                       {"osc2.level", 0.7}, {"osc2.sync", true}, {"osc2.semi", 7}},
                      {route(lfoHz("samplehold", 7), "cutoff", 1), route(lfoHz("smoothrandom", 3, {{"mode", "global"}}), "osc2.pitch", 300),
                       route({{"type", "random"}}, "pan", 0.5), route(envSrc(0.01, 0.2, 0.3, 0.2, "linear"), "cutoff", 2)});
    std::vector<Ev> evs = {on(0, 1, 48, 0.9f, sr), on(0.1, 2, 55, 0.7f, sr), off(0.6, 1, sr), prm(0.3, "cutoff", 900, sr),
                           on(0.7, 3, 60, 0.5f, sr), off(1.0, 2, sr), off(1.1, 3, sr)};
    auto a = renderPatch(p, evs, 1.5, sr, 7), b = renderPatch(p, evs, 1.5, sr, 7), c = renderPatch(p, evs, 1.5, sr, 8);
    check(a.L == b.L && a.R == b.R, "two identical renders are bit-identical (random / S&H / smooth-random mods, stereo noise)");
    check(a.L != c.L, "a different seed gives a different render");
}

void testUnison() {
    std::cout << "unison\n";
    const double sr = 48000;
    auto u = renderPatch({{"unison", 7}, {"unison.detune", 0.6}, {"unison.spread", 1}}, {on(0, 1, 57, 0.8f, sr)}, 1.0, sr);
    std::vector<float> diff(u.L.size());
    for (std::size_t i = 0; i < diff.size(); ++i) diff[i] = u.L[i] - u.R[i];
    const double rel = rms(diff, sr, 0.2, 1.0) / rms(u.L, sr, 0.2, 1.0);
    check(rel > 0.3, fmt("unison 7 spread 1: L-R difference is %.2f of L", rel));
    auto m = renderPatch({{"unison", 1}}, {on(0, 1, 57, 0.8f, sr)}, 0.5, sr);
    check(m.L == m.R, "unison 1 at centre pan: L == R exactly");
    auto one = renderPatch({{"unison", 1}}, {on(0, 1, 57, 0.8f, sr)}, 1.0, sr);
    const double d1 = db(rms(one.L, sr, 0.2, 1.0)), d9 = db(rms(renderPatch({{"unison", 9}, {"unison.detune", 0.5}},
                                                                             {on(0, 1, 57, 0.8f, sr)}, 1.0, sr).L, sr, 0.2, 1.0));
    check(std::fabs(d9 - d1) < 4.0, fmt("unison 9 vs 1 loudness: %.1f vs %.1f dBFS", d9, d1));
}

void testChord() {
    std::cout << "levels & 32-note chord\n";
    const double sr = 48000;
    auto single = renderPatch(json::object(), {on(0, 1, 57, 100 / 127.0f, sr)}, 1.0, sr);
    const double s1 = db(rms(single.L, sr, 0.3, 1.0));
    check(s1 > -26 && s1 < -10, fmt("default patch, one note (vel 100): %.1f dBFS RMS", s1));
    std::vector<Ev> chord4 = {on(0, 1, 57, 0.8f, sr), on(0, 2, 60, 0.8f, sr), on(0, 3, 64, 0.8f, sr), on(0, 4, 67, 0.8f, sr)};
    auto c4 = renderPatch(json::object(), chord4, 1.0, sr);
    check(peak(c4) < 1.0f, fmt("default patch, 4-note chord: %.1f dBFS RMS, peak %.1f dBFS", db(rms(c4.L, sr, 0.3, 1.0)),
                                db(peak(c4))));
    for (const json& p : {json::object(), json{{"unison", 9}, {"unison.detune", 0.7}, {"osc2.level", 1}, {"sub.level", 1},
                                               {"resonance", 1}, {"filter.drive", 1}, {"cutoff", 20000}}}) {
        std::vector<Ev> evs;
        for (int i = 0; i < 32; ++i) evs.push_back(on(0, i + 1, 36 + i, 1.0f, sr));
        for (int i = 0; i < 32; ++i) evs.push_back(off(1.5, i + 1, sr));
        auto o = renderPatch(p, evs, 2.5, sr);
        check(allFinite(o) && peak(o) < 2.0f, fmt("32-note chord finite, peak %.1f dBFS (< +6), RMS %.1f dBFS", db(peak(o)),
                                                   db(rms(o.L, sr, 0.2, 1.4))) + (p.empty() ? " [default]" : " [unison 9, all osc, res 1, drive 1]"));
    }
}

void testStealing() {
    std::cout << "voice allocation\n";
    const double sr = 48000;
    const json p = clean({{"osc1.wave", "sine"}, {"polyphony", 4}, {"amp.release", 3}});
    const int notes[6] = {57, 60, 64, 67, 71, 74};
    std::vector<Ev> evs;
    for (int i = 0; i < 4; ++i) evs.push_back(on(0, i + 1, notes[i], 0.8f, sr));
    evs.push_back(on(0.5, 5, notes[4], 0.8f, sr));
    evs.push_back(on(0.5, 6, notes[5], 0.8f, sr));
    auto o = render(*make(p), evs, 1.0, sr);
    auto amp = [&](int n) { return tone(o.L, sr, 440.0 * std::pow(2.0, (n - 69) / 12.0), 0.55, 1.0); };
    const double ref = amp(notes[2]);
    bool ok = db(amp(notes[0])) - db(ref) < -40 && db(amp(notes[1])) - db(ref) < -40;
    for (int i = 2; i < 6; ++i) ok &= std::fabs(db(amp(notes[i])) - db(ref)) < 3;
    check(ok, fmt("polyphony 4 + 2 notes: the 2 oldest are stolen (%.0f / %.0f dB), the 4 newest play", db(amp(notes[0])) - db(ref),
                  db(amp(notes[1])) - db(ref)));

    // A released (still ringing) voice is stolen before the oldest held one.
    std::vector<Ev> e2 = {on(0, 1, 57, 0.8f, sr), on(0.05, 2, 60, 0.8f, sr), on(0.1, 3, 64, 0.8f, sr), off(0.3, 2, sr),
                          on(0.5, 4, 67, 0.8f, sr)};
    auto o2 = render(*make(clean({{"osc1.wave", "sine"}, {"polyphony", 3}, {"amp.release", 3}})), e2, 1.0, sr);
    auto amp2 = [&](int n) { return db(tone(o2.L, sr, 440.0 * std::pow(2.0, (n - 69) / 12.0), 0.55, 1.0)); };
    const double r2 = amp2(64);
    check(amp2(60) - r2 < -40 && std::fabs(amp2(57) - r2) < 3 && std::fabs(amp2(67) - r2) < 3,
          fmt("released note is stolen first (released %.0f dB, oldest held %.0f dB)", amp2(60) - r2, amp2(57) - r2));

    // The steal fade is click-free: the second difference (a click detector) around the steal stays
    // at the level of the steady tones.
    auto curv = [&](double a, double b) {
        double m = 0;
        for (std::size_t i = static_cast<std::size_t>(a * sr); i < static_cast<std::size_t>(b * sr); ++i)
            m = std::max(m, std::fabs(double(o.L[i]) - 2.0 * o.L[i - 1] + o.L[i - 2]));
        return m;
    };
    const double around = curv(0.499, 0.52), steady = curv(0.6, 0.9);  // steady = the 4 notes left after the steal
    check(around < 2.0 * steady, fmt("stealing is click-free (2nd difference %.5f vs %.5f steady)", around, steady));

    // Mono and legato modes only ever sound one note.
    for (const char* mode : {"mono", "legato"}) {
        auto m = render(*make(clean({{"osc1.wave", "sine"}, {"mode", mode}, {"amp.release", 0.5}})),
                        {on(0, 1, 57, 0.8f, sr), on(0.4, 2, 64, 0.8f, sr), off(0.8, 2, sr), off(1.2, 1, sr)}, 1.3, sr);
        const double a57 = db(tone(m.L, sr, 220.0, 0.45, 0.78)), a64 = db(tone(m.L, sr, 329.63, 0.45, 0.78));
        const double back = measureHz(m.L, sr, 0.85, 1.15);
        check(a57 - a64 < -40 && std::fabs(back - 220.0) < 1.0,
              fmt("mode %s: one voice (old note %.0f dB) and returns to the held note (%.2f Hz)", mode, a57 - a64, back));
    }
}

void testGlide() {
    std::cout << "glide\n";
    const double sr = 48000;
    for (const char* mode : {"mono", "legato", "poly"}) {
        auto o = render(*make(clean({{"osc1.wave", "sine"}, {"mode", mode}, {"glide", 0.3}, {"polyphony", 1}})),
                        {on(0, 1, 45, 0.8f, sr), on(0.5, 2, 57, 0.8f, sr), off(0.52, 1, sr), off(1.5, 2, sr)}, 1.5, sr);
        const double mid = measureHz(o.L, sr, 0.54, 0.62), end = measureHz(o.L, sr, 1.1, 1.45);
        check(mid > 120 && mid < 205 && std::fabs(end - 220) < 1.0,
              fmt("glide A2->A3: %.1f Hz mid-slide, %.2f Hz at the end", mid, end) + " [" + mode + "]");
    }
    auto nog = render(*make(clean({{"osc1.wave", "sine"}, {"mode", "legato"}, {"glide", 0.3}})),
                      {on(0, 1, 45, 0.8f, sr), off(0.4, 1, sr), on(0.5, 2, 57, 0.8f, sr)}, 1.0, sr);
    const double f = measureHz(nog.L, sr, 0.52, 0.6);
    check(std::fabs(f - 220) < 2.0, fmt("legato: detached notes do not glide (%.1f Hz right after the note)", f));
}

void testLadderStability() {
    std::cout << "stability\n";
    const double sr = 48000;
    auto self = renderPatch(clean({{"osc1.level", 0}, {"noise.level", 0.001}, {"resonance", 1}, {"cutoff", 1000}}),
                            {on(0, 1, 60, 0.8f, sr)}, 2.0, sr);
    const double f = measureHz(self.L, sr, 1.0, 2.0);
    check(allFinite(self) && peak(self) < 2.0f && rms(self.L, sr, 1.0, 2.0) > 0.01,
          fmt("ladder self-oscillates at resonance 1 (%.0f Hz, %.1f dBFS RMS) and stays bounded (peak %.1f dBFS)", f,
              db(rms(self.L, sr, 1.0, 2.0)), db(peak(self))));
    bool ok = true;
    float worst = 0;
    for (const char* type : {"ladder", "lp12", "bp12", "hp12", "notch"}) {
        for (double cut : {20.0, 400.0, 5000.0, 20000.0}) {
            auto o = renderPatch({{"filter.type", type}, {"resonance", 1}, {"filter.drive", 1}, {"cutoff", cut},
                                  {"osc2.level", 1}, {"sub.level", 1}, {"noise.level", 1}, {"unison", 3},
                                  {"filter.env", 8}, {"filter.keytrack", 1}},
                                 {on(0, 1, 24, 1.0f, sr), on(0, 2, 60, 1.0f, sr), on(0, 3, 108, 1.0f, sr)}, 0.5, sr);
            ok &= allFinite(o);
            worst = std::max(worst, peak(o));
        }
    }
    check(ok && worst < 8.0f, fmt("all filter types at resonance 1 + drive 1, cutoff 20..20k: finite, peak %.1f dBFS", db(worst)));
    // Fast automation of everything (plus matrix amounts driving every target to its extremes) stays finite.
    std::vector<Ev> evs = {on(0, 1, 48, 1.0f, sr), on(0, 2, 60, 1.0f, sr)};
    const char* names[] = {"cutoff", "resonance", "filter.drive", "osc1.pw", "unison.detune", "pitchbend", "pan", "level",
                           "osc2.level", "mod.vib.amount", "hpf", "mod.res.amount", "mod.amp.amount", "macro1"};
    for (int k = 0; k < 400; ++k) {
        const std::string n = names[k % 14];
        const float v = (k % 2) ? 1e9f : -1e9f;  // clamped by Params
        evs.push_back(prm(0.002 * k, n, v, sr));
    }
    auto o = renderPatch(withMods({{"osc2.level", 1}, {"osc2.sync", true}},
                                  {route(lfoHz("sine", 6), "pitch", 20, "vib"), route(macroSrc(1), "resonance", 1, "res"),
                                   route(lfoHz("square", 13), "amp", -20, "amp"), route(macroSrc(1), "hpf", 5, "hp")}),
                         evs, 1.0, sr);
    check(allFinite(o), "extreme automation jumps (params and routing amounts) stay finite");
}

void testAliasing() {
    std::cout << "anti-aliasing\n";
    for (double sr : {44100.0, 48000.0}) {
        for (const char* wave : {"saw", "square"}) {
            const int note = 96;  // C7, 2093 Hz
            auto o = renderPatch(clean({{"osc1.wave", wave}}), {on(0, 1, note, 0.8f, sr)}, 1.0, sr);
            const double r = inharmonicDb(o.L, sr, 440.0 * std::pow(2.0, (note - 69) / 12.0), 0.1);
            check(r < -60.0, fmt("%s C7 at %.0f Hz: inharmonic (alias) energy %.1f dB below harmonics", wave, sr, r));
        }
    }
    const double sr = 48000;
    auto s = renderPatch(clean({{"osc2.level", 1}, {"osc1.level", 0}, {"osc2.sync", true}, {"osc2.semi", 9.3}}),
                         {on(0, 1, 84, 0.8f, sr)}, 1.0, sr);
    const double r = inharmonicDb(s.L, sr, 440.0 * std::pow(2.0, (84 - 69) / 12.0), 0.1);
    check(r < -50.0, fmt("hard sync C6 (+9.3 st slave): inharmonic energy %.1f dB below harmonics", r));
    // Regression: a pulse whose low part is shorter than one internal sample (PWM pushed to 0.98 at
    // a high note) lost its falling edge whenever edge and wrap fell into the same sample.
    for (int note : {100, 108}) {
        auto p = renderPatch(withMods(clean({{"osc1.wave", "square"}, {"osc1.pw", 0.95}}),
                                      {route(lfoHz("square", 0.01), "osc1.pw", 0.45)}),
                             {on(0, 1, note, 0.8f, sr)}, 1.0, sr);
        const double rp = inharmonicDb(p.L, sr, 440.0 * std::pow(2.0, (note - 69) / 12.0), 0.1);
        check(rp < -45.0, fmt("pulse width 0.98 (via PWM) at note %d: inharmonic energy %.1f dB", note, rp));
    }
    // FM stays clean enough at a moderate index (sine carrier + sine modulator, 2x oversampled).
    auto fmo = renderPatch(clean({{"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"fm", 3}}), {on(0, 1, 81, 0.8f, sr)}, 1.0, sr);
    const double rf = inharmonicDb(fmo.L, sr, 880.0, 0.1);
    check(rf < -60.0, fmt("fm index 3 at A5 (ratio 1): inharmonic energy %.1f dB below the harmonics", rf));
}

// ---------------------------------------------------------------------------------------------
// Modulation matrix

void testModLfo() {
    std::cout << "modulation matrix: LFOs\n";
    const double sr = 48000;
    const json gate = clean({{"osc1.wave", "sine"}, {"amp.attack", 0.001}});
    auto edges = [&](const Out& o, double a, double b) { return risingEdges(o.L, sr, 0.03, a, b); };
    // Free rate: the gate period equals 1 / rateHz (voice LFO, restarted at the note).
    for (double hz : {4.0, 3.7}) {
        auto o = renderPatch(withMods(gate, {route(lfoHz("square", hz, {{"unipolar", true}}), "amp", -40)}),
                             {on(0, 1, 90, 0.8f, sr)}, 6.0, sr);
        const auto e = edges(o, 0.3, 5.8);
        const double period = e.size() > 2 ? (e.back() - e.front()) / double(e.size() - 1) : 0.0;
        check(e.size() > 15 && std::fabs(period - 1.0 / hz) < 2e-5,
              fmt("voice lfo square %.1f Hz: %zu gate edges, period %.6f s (want %.6f)", hz, e.size(), period, 1.0 / hz));
    }
    // Tempo sync, global: rising edges (square low half -> loud) on the song grid: k * 0.25 s + 0.125 s at
    // 120 BPM / 1/8 note, whenever the note starts; at 100 BPM 1 beat = 0.6 s.
    for (double bpm : {120.0, 100.0}) {
        const double beats = bpm == 120.0 ? 0.5 : 1.0, period = beats * 60.0 / bpm;
        auto inst = make(withMods(gate, {route(lfoBeats("square", beats, {{"mode", "global"}, {"unipolar", true}}), "amp", -40)}),
                         sr, 1, bpm);
        auto o = render(*inst, {on(0.337, 1, 90, 0.8f, sr)}, 4.0, sr);
        const auto e = edges(o, 0.4, 3.9);
        double worst = 0.0;
        for (double t : e) {
            const double ph = std::fmod(t - 0.5 * period, period);
            const double off = ph > 0.5 * period ? ph - period : ph;
            worst = std::max(worst, std::fabs(off - 0.0015));
        }
        check(e.size() >= 5 && worst < 0.0015,
              fmt("global lfo rateBeats %.1f at %.0f BPM: %zu edges, all on the song grid (+1.5 ms de-click) within %.2f ms",
                  beats, bpm, e.size(), worst * 1000));
    }
    // Tempo sync, per voice: the cycle restarts at the note (edge 0.125 s after the note start).
    {
        auto o = renderPatch(withMods(gate, {route(lfoBeats("square", 0.5, {{"unipolar", true}}), "amp", -40)}),
                             {on(0.337, 1, 90, 0.8f, sr)}, 2.0, sr);
        const auto e = edges(o, 0.4, 1.9);
        const double first = e.empty() ? 0.0 : e.front() - 0.337;
        check(!e.empty() && std::fabs(first - 0.125 - 0.0015) < 0.0015,
              fmt("voice lfo rateBeats 0.5: the first gate opens %.2f ms after the note (want 125 + de-click)", first * 1000));
    }
    // Phase: square with phase 0.5 starts low (open) at the note.
    {
        auto o = renderPatch(withMods(gate, {route(lfoHz("square", 2, {{"unipolar", true}, {"phase", 0.5}}), "amp", -40)}),
                             {on(0, 1, 90, 0.8f, sr)}, 1.0, sr);
        check(db(rms(o.L, sr, 0.05, 0.2)) - db(rms(o.L, sr, 0.3, 0.45)) > 30, "phase 0.5: the square starts in its low half");
    }
    // Delayed vibrato with fade-in: none before the delay, clearly present after.
    auto v = renderPatch(withMods(clean({{"osc1.wave", "sine"}}), {route(lfoHz("sine", 5, {{"delay", 0.5}, {"fade", 0.2}}), "pitch", 100)}),
                         {on(0, 1, 69, 0.8f, sr)}, 1.5, sr);
    double lo = 1e9, hi = 0;
    for (double t = 0.8; t < 1.4; t += 0.02) {
        const double f = measureHz(v.L, sr, t, t + 0.02);
        lo = std::min(lo, f);
        hi = std::max(hi, f);
    }
    const double early = measureHz(v.L, sr, 0.1, 0.45);
    check(std::fabs(early - 440) < 0.5 && hi > 460 && lo < 420,
          fmt("delayed vibrato: %.2f Hz before the delay, %.0f..%.0f Hz after", early, lo, hi));
    // Shapes: saw falls, ramp rises (pitch at 1/4 of the cycle).
    for (const char* shape : {"saw", "ramp", "triangle", "sine"}) {
        auto o = renderPatch(withMods(clean({{"osc1.wave", "sine"}}), {route(lfoHz(shape, 0.5), "osc1.pitch", 1200)}),
                             {on(0, 1, 69, 0.8f, sr)}, 1.0, sr);
        const double f = measureHz(o.L, sr, 0.494, 0.506);  // phase 0.25: saw 0.5, ramp -0.5, triangle 1, sine 1
        const double want = std::string(shape) == "saw" ? 622.25 : std::string(shape) == "ramp" ? 311.13 : 880.0;
        check(std::fabs(f / want - 1.0) < 0.01, fmt("lfo %s at a quarter cycle: %.1f Hz (want %.1f)", shape, f, want));
    }
    // S&H: steps per cycle, different between cycles, within the amount.
    {
        auto o = renderPatch(withMods(clean({{"osc1.wave", "sine"}}), {route(lfoHz("samplehold", 4), "osc1.pitch", 100)}),
                             {on(0, 1, 81, 0.8f, sr)}, 2.2, sr);
        std::set<long> steps;
        bool inRange = true;
        for (int k = 1; k < 8; ++k) {
            const double f = measureHz(o.L, sr, 0.25 * k + 0.05, 0.25 * k + 0.2);
            const double ct = 1200.0 * std::log2(f / 880.0);
            inRange &= std::fabs(ct) <= 100.5;
            steps.insert(std::lround(ct));
        }
        check(inRange && steps.size() >= 5, fmt("samplehold: %zu distinct steps in 7 cycles, all within +-100 ct", steps.size()));
    }
    // Auto-pan (global LFO) moves the image.
    auto p = renderPatch(withMods({}, {route(lfoHz("sine", 2, {{"mode", "global"}}), "pan", 1)}), {on(0, 1, 57, 0.8f, sr)}, 1.0, sr);
    const double l1 = rms(p.L, sr, 0.1, 0.2), r1 = rms(p.R, sr, 0.1, 0.2);
    check(std::fabs(db(l1) - db(r1)) > 6, fmt("lfo -> pan sweeps the stereo image (%.1f dB L/R)", db(l1) - db(r1)));
    // Voice vs global: two notes started 0.1 s apart share a global LFO's phase, voice LFOs restart per note.
    auto phaseDiff = [&](const char* mode) {
        auto o = renderPatch(withMods(clean({{"osc1.wave", "sine"}}), {route(lfoHz("square", 1, {{"mode", mode}}), "pan", 1)}),
                             {on(0, 1, 69, 0.8f, sr), on(0.1, 2, 81, 0.8f, sr)}, 1.0, sr);
        return db(tone(o.L, sr, 880, 0.52, 0.58)) - db(tone(o.R, sr, 880, 0.52, 0.58));  // note 2 at 0.52..0.58 s
    };
    const double gd = phaseDiff("global"), vd = phaseDiff("voice");
    check(gd > 30 && vd < -30, fmt("mode global: note 2 follows the shared LFO (L-R %.0f dB at 0.55 s); mode voice: its own cycle (%.0f dB)", gd, vd));

    // Fast LFOs keep their depth: only jumps are de-clicked, not the LFO (AM sidebands of a sine LFO -> osc1.level
    // are rate independent up to 200 Hz, voice and global).
    for (const char* mode : {"voice", "global"}) {
        const double fc = 440.0 * std::pow(2.0, (95 - 69) / 12.0);
        auto amIndex = [&](double r) {
            json p = withMods(clean({{"osc1.wave", "sine"}, {"osc1.level", 0.5}}),
                              {route(lfoHz("sine", r, {{"mode", mode}}), "osc1.level", 0.5)});
            auto o = renderPatch(p, {on(0, 1, 95, 1.0f, sr)}, 1.5, sr);
            return (tone(o.L, sr, fc + r, 0.3, 1.4) + tone(o.L, sr, fc - r, 0.3, 1.4)) / tone(o.L, sr, fc, 0.3, 1.4);
        };
        const double slow = amIndex(5), fast = amIndex(200);
        check(std::fabs(db(fast / slow)) < 0.2,
              fmt("%s sine lfo at 200 Hz keeps its depth: AM index %.3f vs %.3f at 5 Hz (%.2f dB)", mode, fast, slow, db(fast / slow)));
    }
    // ... and saw / ramp keep their slope (only the reset is smoothed): a 0.5 Hz ramp -> osc1.pitch 1200 at 30 %
    // of its cycle is exactly where the wave is, no lag.
    {
        auto o = renderPatch(withMods(clean({{"osc1.wave", "sine"}}), {route(lfoHz("ramp", 0.5, {{"phase", 0.0}}), "osc1.pitch", 1200)}),
                             {on(0, 1, 69, 0.8f, sr)}, 1.0, sr);
        const double f = measureHz(o.L, sr, 0.59, 0.61), want = 440.0 * std::pow(2.0, 2.0 * 0.3 - 1.0);
        check(std::fabs(1200 * std::log2(f / want)) < 3, fmt("ramp lfo has no lag: %.2f Hz at 0.6 s (want %.2f)", f, want));
    }
    // Jumps glide out click-free: a mono retrigger restarting a sine LFO at another phase, a delay ending without
    // fade, saw resets and square edges (-> amp / pan, big depth). Measure: the largest second difference around
    // the jump vs that of the loudest 220 Hz sine of the note (a step would be ~100x it; a ~2 ms glide ~2x).
    {
        const json sine = clean({{"osc1.wave", "sine"}, {"mode", "mono"}});
        auto maxStep = [&](const Out& o, double a, double b) {
            float m = 0;
            for (std::size_t i = static_cast<std::size_t>(a * sr); i < static_cast<std::size_t>(b * sr); ++i)
                m = std::max({m, std::fabs(o.L[i] - 2 * o.L[i - 1] + o.L[i - 2]), std::fabs(o.R[i] - 2 * o.R[i - 1] + o.R[i - 2])});
            return m;
        };
        struct Case { json mod; std::vector<Ev> evs; double at; const char* what; };
        const std::vector<Case> cases = {
            {route(lfoHz("sine", 3, {{"unipolar", true}}), "osc1.level", -0.9), {on(0, 1, 57, 0.8f, sr), on(0.41, 2, 57, 0.8f, sr)},
             0.41, "mono retrigger restarts a sine lfo -> osc1.level -0.9"},
            {route(lfoHz("square", 2, {{"phase", 0.5}}), "pan", 0.5), {on(0, 1, 57, 0.8f, sr), on(0.3, 2, 57, 0.8f, sr)}, 0.3,
             "mono retrigger restarts a square lfo -> pan 0.5"},
            {route(lfoHz("sine", 3, {{"delay", 0.3}, {"phase", 0.25}}), "amp", -30), {on(0, 1, 57, 0.8f, sr)}, 0.3,
             "a delay ending without fade (lfo at its peak) -> amp -30 dB"},
            {route(lfoHz("saw", 4, {{"unipolar", true}}), "osc1.level", -0.9), {on(0, 1, 57, 0.8f, sr)}, 0.5,
             "saw lfo reset -> osc1.level -0.9"},
            {route(lfoHz("square", 4, {{"mode", "global"}, {"unipolar", true}}), "osc1.level", -0.9), {on(0, 1, 57, 0.8f, sr)}, 0.5,
             "global square lfo edge -> osc1.level -0.9"},
        };
        for (const Case& c : cases) {
            auto o = renderPatch(withMods(sine, {c.mod}), c.evs, 1.0, sr);
            const float jump = maxStep(o, c.at - 0.003, c.at + 0.01);
            const double w = 2 * kPi * 220 / sr;
            const float sine2 = static_cast<float>(peak(o) * w * w);
            check(allFinite(o) && jump <= 4.0f * sine2,
                  fmt("%s: max 2nd difference %.5f around the jump (%.1fx the loudest sine's)", c.what, jump, jump / sine2));
        }
    }
}

void testModEnv() {
    std::cout << "modulation matrix: envelopes\n";
    const double sr = 48000;
    const json sine = clean({{"osc1.wave", "sine"}, {"amp.release", 1.0}});
    // linear: attack 0.2 s -> half way at 0.1 s; sustain 0.5 -> +600 ct held; release 0.2 s after note-off.
    auto o = renderPatch(withMods(sine, {route(envSrc(0.2, 0.3, 0.5, 0.2, "linear"), "osc1.pitch", 1200)}),
                         {on(0, 1, 69, 0.8f, sr), off(1.5, 1, sr)}, 2.0, sr);
    const double half = measureHz(o.L, sr, 0.095, 0.105), held = measureHz(o.L, sr, 1.0, 1.45);
    const double rel = measureHz(o.L, sr, 1.595, 1.605), after = measureHz(o.L, sr, 1.75, 1.95);
    check(std::fabs(half / 622.25 - 1) < 0.01 && std::fabs(held - 622.25) < 0.5 && std::fabs(rel / 523.25 - 1) < 0.015 &&
              std::fabs(after - 440) < 0.5,
          fmt("linear env -> osc1.pitch 1200: %.1f Hz half-way up the attack, sustain 0.5 = %.2f Hz, %.1f Hz half-way "
              "through the release, %.2f Hz after it", half, held, rel, after));
    // exp (analog) pitch envelope: the classic zap returns to the played pitch.
    auto z = renderPatch(withMods(sine, {route(envSrc(0, 0.15, 0, 0.2), "pitch", 1200)}), {on(0, 1, 69, 0.8f, sr)}, 1.5, sr);
    const double early = measureHz(z.L, sr, 0.0005, 0.004), back = measureHz(z.L, sr, 0.8, 1.4);
    check(early > 780 && std::fabs(back - 440) < 0.5,
          fmt("env (attack 0) -> pitch +1200: starts an octave up (%.0f Hz), settles on the note (%.2f Hz)", early, back));
    // osc2 sweep returns to osc2.semi (a sync sweep).
    auto s2 = renderPatch(withMods(clean({{"osc1.level", 0}, {"osc2.level", 1}, {"osc2.wave", "sine"}, {"osc2.semi", 7}}),
                                   {route(envSrc(0, 0.15, 0, 0.2), "osc2.pitch", -1200)}),
                          {on(0, 1, 69, 0.8f, sr)}, 1.5, sr);
    const double want = 440.0 * std::pow(2.0, 7.0 / 12.0), held2 = measureHz(s2.L, sr, 0.8, 1.4);
    check(std::fabs(held2 - want) < 0.5 && measureHz(s2.L, sr, 0.001, 0.012) < 0.7 * want,
          fmt("env -> osc2.pitch -1200: starts low, held osc2 returns to osc2.semi +7 (%.2f Hz, want %.2f)", held2, want));
    // exp env with sustain: holds its level (+600 ct at sustain 0.5).
    auto es = renderPatch(withMods(sine, {route(envSrc(0.01, 0.1, 0.5, 0.2), "osc1.pitch", 1200)}), {on(0, 1, 69, 0.8f, sr)}, 1.0, sr);
    check(std::fabs(measureHz(es.L, sr, 0.6, 0.95) - 622.25) < 0.5, "exp env sustain 0.5 -> +600 ct held");
    // mono retrigger restarts the envelope from its level; legato does not retrigger.
    for (const char* mode : {"mono", "legato"}) {
        auto m = renderPatch(withMods(merged(sine, {{"mode", mode}}), {route(envSrc(0, 0.1, 0, 0.1), "osc1.pitch", 1200)}),
                             {on(0, 1, 57, 0.8f, sr), on(0.5, 2, 69, 0.8f, sr)}, 1.0, sr);
        const double f = measureHz(m.L, sr, 0.501, 0.512);
        const bool retrig = f > 600;
        check(retrig == (std::string(mode) == "mono"), fmt("mode %s: the env %s at the second note (%.0f Hz right after it)", mode,
                                                              retrig ? "restarts" : "does not restart", f));
    }
}

void testModSources() {
    std::cout << "modulation matrix: velocity, key, random, macros\n";
    const double sr = 48000;
    const json sine = clean({{"osc1.wave", "sine"}});
    auto hzOf = [&](const json& mods, int note, float vel, double a = 0.3, double b = 0.9) {
        auto o = renderPatch(withMods(sine, mods), {on(0, 1, note, vel, sr)}, b + 0.05, sr);
        return measureHz(o.L, sr, a, b);
    };
    const json velo = {route({{"type", "velocity"}}, "osc1.pitch", 1200)};
    const double v5 = hzOf(velo, 69, 0.5f), v1 = hzOf(velo, 69, 1.0f);
    check(std::fabs(v5 - 622.25) < 0.5 && std::fabs(v1 - 880) < 0.5,
          fmt("velocity (0..1) -> +1200 ct: vel 0.5 = %.2f Hz, vel 1 = %.2f Hz", v5, v1));
    const json key = {route({{"type", "key"}}, "osc1.pitch", 1200)};
    const double k75 = hzOf(key, 75, 0.8f), k63 = hzOf(key, 63, 0.8f);
    check(std::fabs(k75 - 880) < 0.6 && std::fabs(k63 - 220) < 0.3,
          fmt("key (octaves from A4) -> +1200 ct: D#5 = %.2f Hz (want 880), D#4 = %.2f Hz (want 220)", k75, k63));
    const json keyR = {route({{"type", "key"}, {"low", 57}, {"high", 81}}, "osc1.pitch", 1200)};
    const double r69 = hzOf(keyR, 69, 0.8f), r90 = hzOf(keyR, 90, 0.8f);
    check(std::fabs(r69 - 622.25) < 0.5 && std::fabs(r90 / (2 * 440 * std::pow(2.0, 21 / 12.0)) - 1) < 0.001,
          fmt("key low 57 high 81 (0..1) -> +1200 ct: A4 = %.2f Hz (0.5), F#6 clamps at 1 (%.1f Hz)", r69, r90));
    // random: a per-note value in -1..1, different per note, reproducible, independent per routing unless
    // the routings share a seed.
    auto cents = [&](const json& mods, std::uint64_t seed) {
        std::vector<Ev> evs;
        for (int i = 0; i < 8; ++i) {
            evs.push_back(on(0.25 * i, i + 1, 69 + (i % 2) * 12, 0.8f, sr));
            evs.push_back(off(0.25 * i + 0.2, i + 1, sr));
        }
        auto o = renderPatch(withMods(merged(sine, {{"amp.release", 0.01}}), mods), evs, 2.1, sr, seed);
        std::vector<double> c;
        for (int i = 0; i < 8; ++i) {
            const double f = measureHz(o.L, sr, 0.25 * i + 0.03, 0.25 * i + 0.19);
            c.push_back(1200.0 * std::log2(f / (440.0 * ((i % 2) ? 2.0 : 1.0))));
        }
        return c;
    };
    const json rnd = route({{"type", "random"}, {"seed", 5}}, "osc1.pitch", 100);
    const auto c1 = cents(rnd, 1), c1b = cents(rnd, 1), c2 = cents(rnd, 2);
    const auto cTwice = cents({rnd, rnd}, 1);
    const json unseeded = route({{"type", "random"}}, "osc1.pitch", 100);
    const auto cSingle = cents({unseeded}, 1), cIndep = cents({unseeded, unseeded}, 1);
    const auto cUni = cents({route({{"type", "random"}, {"unipolar", true}}, "osc1.pitch", 100)}, 1);
    bool range = true, same = true, doubled = true, uni = true, notDoubled = false;
    double spread = 0;
    std::set<long> distinct;
    for (std::size_t i = 0; i < 8; ++i) {
        range &= std::fabs(c1[i]) <= 100.5;
        same &= std::fabs(c1[i] - c1b[i]) < 1e-6;
        doubled &= std::fabs(cTwice[i] - 2 * c1[i]) < 1.0;
        notDoubled |= std::fabs(cIndep[i] - 2 * cSingle[i]) > 5;
        uni &= cUni[i] > -0.5;
        spread = std::max(spread, std::fabs(c1[i] - c2[i]));
        distinct.insert(std::lround(c1[i]));
    }
    check(range && distinct.size() >= 6 && same && spread > 10,
          fmt("random -> +-100 ct: %zu distinct values over 8 notes, within range, reproducible, another seed differs", distinct.size()));
    check(doubled, "two routings with the same random seed share the value (their sum = 2x)");
    check(notDoubled, "random sources without a seed are independent per routing");
    check(uni, "random unipolar: 0..1 (never below the note)");
    // macros: static value and automation (smoothed)
    auto m = renderPatch(withMods(merged(sine, {{"macro3", 0.5}}), {route(macroSrc(3), "osc1.pitch", 1200)}),
                         {on(0, 1, 69, 0.8f, sr), prm(0.5, "macro3", 1.0f, sr)}, 1.0, sr);
    const double m1 = measureHz(m.L, sr, 0.2, 0.45), m2 = measureHz(m.L, sr, 0.6, 0.95);
    check(std::fabs(m1 - 622.25) < 0.5 && std::fabs(m2 - 880) < 0.5,
          fmt("macro3 -> +1200 ct: 0.5 = %.2f Hz, automated to 1 = %.2f Hz", m1, m2));
}

// Every target with a static counterpart: a routing from a macro at 1 equals setting the param (units).
void testModTargets() {
    std::cout << "modulation matrix: targets (a routing at full source == the static param)\n";
    const double sr = 48000;
    struct Case { const char* target; double amount; json base, stat; const char* what; };
    const std::vector<Case> cases = {
        {"osc1.pw", 0.3, {{"osc1.wave", "square"}, {"osc1.pw", 0.4}}, {{"osc1.pw", 0.7}}, "pulse width"},
        {"osc2.pw", -0.25, {{"osc2.wave", "square"}, {"osc2.level", 1}, {"osc2.pw", 0.5}}, {{"osc2.pw", 0.25}}, "pulse width"},
        {"osc1.level", -0.5, {{"osc1.level", 1}}, {{"osc1.level", 0.5}}, "level"},
        {"osc2.level", 0.75, {{"osc2.level", 0}}, {{"osc2.level", 0.75}}, "level"},
        {"sub.level", 0.5, {{"sub.level", 0}}, {{"sub.level", 0.5}}, "level"},
        {"noise.level", 0.25, {{"noise.level", 0}}, {{"noise.level", 0.25}}, "level"},
        {"cutoff", -2, {{"cutoff", 2000}}, {{"cutoff", 500}}, "octaves"},
        {"resonance", 0.5, {{"resonance", 0}, {"cutoff", 1200}}, {{"resonance", 0.5}}, "level"},
        {"filter.drive", 0.75, {{"filter.drive", 0}}, {{"filter.drive", 0.75}}, "level"},
        {"pan", -0.5, {{"pan", 0}}, {{"pan", -0.5}}, "position"},
        {"unison.detune", 0.5, {{"unison", 5}, {"unison.detune", 0}}, {{"unison.detune", 0.5}}, "detune"},
        {"amp", -6, {{"level", 0}}, {{"level", -6}}, "dB"},
        {"hpf", 2, {{"hpf", 100}}, {{"hpf", 400}}, "octaves (global)"},
        {"fm", 1.5, {{"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"osc2.semi", 12}, {"fm", 0.5}}, {{"fm", 2}}, "index"},
    };
    const std::vector<Ev> evs = {on(0, 1, 45, 0.8f, sr), on(0, 2, 57, 0.6f, sr), on(0, 3, 64, 0.9f, sr)};
    for (const Case& c : cases) {
        const json base = merged(clean({{"cutoff", 3000}, {"macro1", 1}}), c.base);
        const Out stat = renderPatch(merged(base, c.stat), evs, 0.6, sr);
        const Out mod = renderPatch(withMods(base, {route(macroSrc(1), c.target, c.amount)}), evs, 0.6, sr);
        const Out none = renderPatch(base, evs, 0.6, sr);
        const float d = maxDiff(stat, mod), effect = maxDiff(stat, none), pk = peak(stat);
        check(d <= 2e-4f * std::max(pk, 0.05f) && effect > 0.02f * pk,
              fmt("%-13s %+g (%s): matches the static param (max diff %.1e, peak %.2f; the routing's effect %.2f)", c.target,
                  c.amount, c.what, d, pk, effect));
    }
    // pitch targets (cents): measured.
    const json sine = clean({{"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"macro1", 1}});
    auto f1 = renderPatch(withMods(sine, {route(macroSrc(1), "osc1.pitch", 1200)}), {on(0, 1, 69, 0.8f, sr)}, 0.8, sr);
    auto fp = renderPatch(withMods(merged(sine, {{"sub.level", 1}, {"osc1.level", 0}}), {route(macroSrc(1), "pitch", 700)}),
                          {on(0, 1, 69, 0.8f, sr)}, 0.8, sr);
    auto f2 = renderPatch(withMods(merged(sine, {{"osc1.level", 0}, {"osc2.level", 1}}), {route(macroSrc(1), "osc2.pitch", -1200)}),
                          {on(0, 1, 69, 0.8f, sr)}, 0.8, sr);
    const double h1 = measureHz(f1.L, sr, 0.2, 0.8), hp = measureHz(fp.L, sr, 0.2, 0.8), h2 = measureHz(f2.L, sr, 0.2, 0.8);
    check(std::fabs(h1 - 880) < 0.5 && std::fabs(hp - 220 * std::pow(2.0, 7 / 12.0)) < 0.3 && std::fabs(h2 - 220) < 0.3,
          fmt("osc1.pitch +1200 ct doubles the frequency (%.2f Hz); pitch +700 moves the sub too (%.2f Hz); osc2.pitch -1200 "
              "halves osc2 (%.2f Hz)", h1, hp, h2));
    // amp in dB: -12 dB is 12 dB quieter.
    auto a0 = renderPatch(clean({{"macro1", 1}}), {on(0, 1, 57, 0.8f, sr)}, 0.8, sr);
    auto a1 = renderPatch(withMods(clean({{"macro1", 1}}), {route(macroSrc(1), "amp", -12)}), {on(0, 1, 57, 0.8f, sr)}, 0.8, sr);
    const double da = db(rms(a1.L, sr, 0.2, 0.8)) - db(rms(a0.L, sr, 0.2, 0.8));
    check(std::fabs(da + 12.0) < 0.05, fmt("amp -12 dB: %.2f dB", da));
    // amount ranges clamp the targets: osc1.level -1 silences osc1, pan +2 is hard right.
    auto s = renderPatch(withMods(clean({{"macro1", 1}}), {route(macroSrc(1), "osc1.level", -1), route(macroSrc(1), "pan", 2)}),
                         {on(0, 1, 57, 0.8f, sr)}, 0.5, sr);
    check(peak(s) < 1e-6f, "osc1.level -1: silent (levels stay in 0..1)");
    auto r = renderPatch(withMods(clean({{"macro1", 1}}), {route(macroSrc(1), "pan", 2)}), {on(0, 1, 57, 0.8f, sr)}, 0.5, sr);
    check(rms(r.L, sr, 0.1, 0.5) < 1e-6 && rms(r.R, sr, 0.1, 0.5) > 0.01, "pan +2: hard right (pan stays in -1..1)");
}

void testFm() {
    std::cout << "fm (osc2 -> osc1 phase modulation)\n";
    const double sr = 48000;
    // osc.retrig: both oscillators start at phase 0, so the ratio-1 spectrum is the textbook one
    const json base = clean({{"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"osc.retrig", true}});
    auto pure = renderPatch(base, {on(0, 1, 69, 0.8f, sr)}, 1.0, sr);
    auto fm = renderPatch(merged(base, {{"fm", 2}}), {on(0, 1, 69, 0.8f, sr)}, 1.0, sr);
    const double h1 = db(tone(fm.L, sr, 440, 0.2, 1.0)), h2 = db(tone(fm.L, sr, 880, 0.2, 1.0)), h4 = db(tone(fm.L, sr, 1760, 0.2, 1.0));
    const double p2 = db(tone(pure.L, sr, 880, 0.2, 1.0)) - db(tone(pure.L, sr, 440, 0.2, 1.0));
    // sin(wt + 2 sin wt): harmonic amplitudes |J0-J2|, J1+J3, J2-J4 ... -> clearly present
    check(p2 < -60 && h2 - h1 > 6 && h4 - h1 > -6,
          fmt("fm 2 at ratio 1 adds harmonics (2nd %.1f dB, 4th %.1f dB re the 1st; without fm %.0f dB)", h2 - h1, h4 - h1, p2));
    const double inh = inharmonicDb(fm.L, sr, 440.0, 0.1);
    auto bell = renderPatch(merged(base, {{"osc2.semi", 21}, {"osc2.fine", 69}, {"fm", 4}}), {on(0, 1, 69, 0.8f, sr)}, 1.0, sr);
    check(inh < -60 && allFinite(bell) && peak(bell) < 1.0f,
          fmt("the carrier pitch stays exact (all energy on 440 Hz harmonics: rest %.0f dB); a ratio-3.5 bell at index 4 is "
              "finite", inh));
    // an env -> fm routing: bright attack, pure sustain
    auto env = renderPatch(withMods(base, {route(envSrc(0, 0.2, 0, 0.2), "fm", 5)}), {on(0, 1, 69, 0.8f, sr)}, 1.5, sr);
    const double early = db(tone(env.L, sr, 1760, 0.0, 0.02)) - db(tone(env.L, sr, 440, 0.0, 0.02));
    const double late = db(tone(env.L, sr, 1760, 1.0, 1.5)) - db(tone(env.L, sr, 440, 1.0, 1.5));
    check(early > -15 && late < -60, fmt("env -> fm 5: 4th harmonic %.0f dB at the attack, %.0f dB in the sustain", early, late));
    // fm with hard sync and unison stays finite
    auto wild = renderPatch(withMods(merged(base, {{"osc2.sync", true}, {"osc2.semi", 7}, {"unison", 3}, {"osc2.level", 0.5}}),
                                     {route(lfoHz("sine", 3), "fm", 8)}),
                            {on(0, 1, 60, 1.0f, sr), on(0, 2, 96, 1.0f, sr)}, 1.0, sr);
    check(allFinite(wild) && peak(wild) < 2.0f, "fm + sync + unison + lfo -> fm: finite and bounded");
    // strict: fm only acts on a sine osc1, so without one it is not automatable (a lane would be ignored)
    auto fmAutomatable = [](const json& p) {
        auto inst = make(p);
        for (const auto& s : inst->paramSpecs())
            if (s.name == "fm") return s.automatable && inst->setParam("fm", 1.0f);
        return false;
    };
    check(fmAutomatable(base) && !fmAutomatable(clean()) && !fmAutomatable(clean({{"osc1.wave", "square"}})),
          "'fm' is automatable with a sine osc1 only");
}

void testNoiseStereoAndPhase() {
    std::cout << "stereo noise, osc2.phase\n";
    const double sr = 48000;
    auto corr = [&](const Out& o) {
        double lr = 0, ll = 0, rr = 0;
        for (std::size_t i = static_cast<std::size_t>(0.1 * sr); i < o.L.size(); ++i) {
            lr += double(o.L[i]) * o.R[i];
            ll += double(o.L[i]) * o.L[i];
            rr += double(o.R[i]) * o.R[i];
        }
        return lr / std::sqrt(ll * rr + 1e-30);
    };
    for (const char* color : {"white", "pink"}) {
        const json n = clean({{"osc1.level", 0}, {"noise.level", 1}, {"noise.color", color}, {"cutoff", 20000}});
        auto a = renderPatch(n, {on(0, 1, 60, 0.8f, sr)}, 1.0, sr);
        auto h = renderPatch(merged(n, {{"noise.stereo", 0.5}}), {on(0, 1, 60, 0.8f, sr)}, 1.0, sr);
        auto w = renderPatch(merged(n, {{"noise.stereo", 1}}), {on(0, 1, 60, 0.8f, sr)}, 1.0, sr);
        const double lv = db(rms(w.L, sr, 0.1, 1.0)) - db(rms(a.L, sr, 0.1, 1.0)), rv = db(rms(w.R, sr, 0.1, 1.0)) - db(rms(a.L, sr, 0.1, 1.0));
        check(a.L == a.R && std::fabs(corr(w)) < 0.05 && std::fabs(corr(h) - 0.707) < 0.05 && std::fabs(lv) < 0.5 && std::fabs(rv) < 0.5,
              fmt("%s noise: stereo 0 is centred (L == R), 0.5 correlation %.2f, 1 correlation %.3f, level L %+.2f R %+.2f dB",
                  color, corr(h), corr(w), lv, rv));
    }
    // automating noise.stereo on a sounding note is click-free (the voice switches to its stereo path)
    auto j = renderPatch(clean({{"osc1.level", 0}, {"noise.level", 1}, {"cutoff", 3000}}),
                         {on(0, 1, 60, 0.8f, sr), prm(0.5, "noise.stereo", 1.0f, sr)}, 1.0, sr);
    check(allFinite(j) && std::fabs(corr(j)) < 0.9, "noise.stereo automated 0 -> 1 on a held note widens it");
    // osc2.phase with osc.retrig: same-pitch sines cancel at 0.5, add up at 0.
    const json two = clean({{"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"osc2.level", 1}, {"osc.retrig", true}});
    auto sum = renderPatch(two, {on(0, 1, 69, 0.8f, sr)}, 0.5, sr);
    auto cancel = renderPatch(merged(two, {{"osc2.phase", 0.5}}), {on(0, 1, 69, 0.8f, sr)}, 0.5, sr);
    const double d = db(rms(cancel.L, sr, 0.05, 0.5)) - db(rms(sum.L, sr, 0.05, 0.5));
    check(d < -60, fmt("osc2.phase 0.5 with osc.retrig: same-pitch sine layers cancel (%.0f dB vs phase 0)", d));
}

void testModAutomation() {
    std::cout << "modulation matrix: amount automation is smoothed\n";
    const double sr = 48000;
    struct Jump { const char* target; float from, to; };
    for (const Jump& j : {Jump{"cutoff", 4, -3.5f}, Jump{"amp", -60, 0}, Jump{"pan", -1, 1}, Jump{"osc1.level", -1, 0},
                          Jump{"resonance", 0, 1}, Jump{"osc1.pitch", 0, 1200}}) {
        const json p = withMods(clean({{"osc1.wave", "sine"}, {"cutoff", 1500}, {"macro1", 1}}), {route(macroSrc(1), j.target, j.from, "x")});
        auto o = renderPatch(p, {on(0, 1, 57, 0.8f, sr), prm(0.5, "mod.x.amount", j.to, sr)}, 0.9, sr);
        auto maxStep = [&](const std::vector<float>& x, double a, double b) {
            float m = 0;
            for (std::size_t i = static_cast<std::size_t>(a * sr); i < static_cast<std::size_t>(b * sr); ++i)
                m = std::max(m, std::fabs(x[i] - x[i - 1]));
            return m;
        };
        float jump = 0, steady = 0;
        for (const auto* x : {&o.L, &o.R}) {
            jump = std::max(jump, maxStep(*x, 0.499, 0.56));
            steady = std::max({steady, maxStep(*x, 0.3, 0.49), maxStep(*x, 0.7, 0.9)});
        }
        check(allFinite(o) && jump <= 1.25f * steady + 1e-5f,
              fmt("'mod.x.amount' (-> %s) %g -> %g in one step is smoothed (max step %.5f vs steady %.5f)", j.target, j.from,
                  j.to, jump, steady));
    }
}

// A preview render starting at a song position equals the same span of a full render: global LFOs on the
// song grid / song clock, per-note sources from the note and its song position.
void testModPreview() {
    std::cout << "modulation matrix: preview renders match full renders\n";
    const double sr = 48000, bpm = 120;
    const json voiceMods = {route(lfoBeats("smoothrandom", 1.25, {{"mode", "global"}}), "cutoff", 2),
                            route(lfoBeats("square", 0.75, {{"mode", "global"}, {"phase", 0.3}}), "amp", -6),
                            route(lfoHz("samplehold", 7.3), "osc2.pitch", 50), route(lfoHz("sine", 3.3, {{"mode", "global"}}), "pan", 0.5),
                            route({{"type", "random"}}, "osc1.pitch", 30), route(envSrc(0.05, 0.3, 0.2, 0.3), "cutoff", 3),
                            route(lfoBeats("triangle", 3, {{"delay", 0.1}, {"fade", 0.2}}), "osc1.pw", 0.3)};
    json withHpf = voiceMods;
    withHpf.push_back(route(lfoHz("triangle", 0.37, {{"mode", "global"}}), "hpf", 1.5));
    const json base = {{"unison", 3}, {"noise.level", 0.2}, {"noise.stereo", 1}, {"osc1.wave", "square"}};
    struct Case { json params; double skip; const char* what; };
    const std::vector<Case> cases = {{withMods(base, voiceMods), 0.0, "every sample"},
                                     {withMods(base, withHpf), 0.02, "after the hpf glide (20 ms)"}};
    for (const Case& c : cases) {
        for (double startBeat : {13.5, 13.5 + 5.0 / 24000.0, 7.0 + 1.0 / 3.0}) {
            const double t0 = startBeat * 60.0 / bpm;
            const long s0 = std::lround(t0 * sr);
            auto full = make(c.params, sr, 3, bpm, 0.0);
            std::vector<Ev> fe = {{s0, 0, 1, 57, 0.8f, "", 0}, {s0 + 24000, 0, 2, 64, 0.7f, "", 0}, {s0 + 48000, 1, 1, 0, 0, "", 0}};
            const Out fo = render(*full, fe, t0 + 1.6, sr);
            auto prev = make(c.params, sr, 3, bpm, startBeat);
            std::vector<Ev> pe = {{0, 0, 1, 57, 0.8f, "", 0}, {24000, 0, 2, 64, 0.7f, "", 0}, {48000, 1, 1, 0, 0, "", 0}};
            const Out po = render(*prev, pe, 1.5, sr);
            auto naive = make(c.params, sr, 3, bpm, 0.0);  // the same notes without the song position: differs
            const Out no = render(*naive, pe, 1.5, sr);
            double d = 0, dn = 0, pk = 0;
            for (std::size_t i = static_cast<std::size_t>(c.skip * sr); i < po.L.size(); ++i) {
                const std::size_t f = static_cast<std::size_t>(s0) + i;
                d = std::max({d, double(std::fabs(po.L[i] - fo.L[f])), double(std::fabs(po.R[i] - fo.R[f]))});
                dn = std::max({dn, double(std::fabs(no.L[i] - fo.L[f]))});
                pk = std::max(pk, double(std::fabs(fo.L[f])));
            }
            check(pk > 1e-3 && d < (c.skip > 0 ? 1e-5 : 1e-6) && dn > 0.05 * pk,
                  fmt("preview at beat %.5f matches the full render %s: max diff %.1e (peak %.2f); ignoring the song "
                      "position: %.2f", startBeat, c.what, d, pk, dn) + (c.skip > 0 ? " [with an hpf routing]" : ""));
        }
    }
}

void testModMany() {
    std::cout << "modulation matrix: many routings\n";
    const double sr = 48000;
    const char* targets[] = {"pitch", "osc1.pitch", "osc2.pitch", "osc1.pw", "osc2.pw", "osc1.level", "osc2.level", "sub.level",
                             "noise.level", "cutoff", "resonance", "filter.drive", "amp", "pan", "unison.detune"};
    const double amounts[] = {50, 30, 700, 0.3, 0.3, -0.3, 0.5, 0.4, 0.2, 2, 0.5, 0.5, -6, 0.6, 0.4};
    const json sources[] = {lfoHz("sine", 5.5), lfoHz("square", 3, {{"mode", "global"}}), lfoBeats("samplehold", 0.25),
                            lfoBeats("smoothrandom", 2, {{"mode", "global"}}), envSrc(0.01, 0.3, 0.2, 0.4), envSrc(0.2, 1, 0.5, 1, "linear"),
                            {{"type", "velocity"}}, {{"type", "key"}}, {{"type", "random"}}, macroSrc(2),
                            lfoHz("triangle", 0.7, {{"delay", 0.2}, {"fade", 0.3}}), lfoHz("saw", 11, {{"unipolar", true}})};
    json mods = json::array();
    for (int i = 0; i < 32; ++i)
        mods.push_back(route(sources[i % 12], targets[i % 15], amounts[i % 15] * (i % 3 == 0 ? -1 : 1)));
    std::vector<Ev> evs;
    for (int i = 0; i < 8; ++i) evs.push_back(on(0.05 * i, i + 1, 40 + 5 * i, 0.5f + 0.06f * i, sr));
    for (int i = 0; i < 8; ++i) evs.push_back(off(1.5 + 0.05 * i, i + 1, sr));
    const json p = withMods({{"unison", 3}, {"osc2.level", 0.6}, {"osc1.wave", "square"}, {"macro2", 0.7}}, mods);
    auto inst = make(p, sr);
    const auto t0 = std::chrono::steady_clock::now();
    const Out o = render(*inst, evs, 3.0, sr);
    const double s = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    check(allFinite(o) && peak(o) < 2.0f && rms(o.L, sr, 0.5, 1.4) > 1e-3,
          fmt("32 routings (every source type and voice target), 8 notes x unison 3: finite, peak %.1f dBFS, 3 s in %.3f s",
              db(peak(o)), s));
    std::vector<Ev> evs2 = evs;
    for (int k = 0; k < 64; ++k) evs2.push_back(prm(0.02 * k, "mod." + std::to_string(k % 32) + ".amount", (k % 2) ? 1e9f : -1e9f, sr));
    auto o2 = renderPatch(p, evs2, 2.0, sr);
    check(allFinite(o2), "every amount jumping between its extremes stays finite");
}

// CPU time of the calling thread (seconds): the speed checks stay meaningful on a busy machine, where
// wall-clock time also counts other processes.
double threadCpuSeconds() {
#ifdef _WIN32
    FILETIME created, exited, kernel, user;
    if (!GetThreadTimes(GetCurrentThread(), &created, &exited, &kernel, &user)) return 0.0;
    auto sec = [](const FILETIME& f) {
        return static_cast<double>((static_cast<std::uint64_t>(f.dwHighDateTime) << 32) | f.dwLowDateTime) * 1e-7;
    };
    return sec(kernel) + sec(user);
#else
    timespec ts{};
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
    return static_cast<double>(ts.tv_sec) + 1e-9 * static_cast<double>(ts.tv_nsec);
#endif
}

void testSpeed() {
    std::cout << "speed (thread CPU time, best of 3)\n";
    const double sr = 48000;
    auto run = [&](const json& p, int voices, const char* label) {
        std::vector<Ev> evs;
        for (int i = 0; i < voices; ++i) evs.push_back(on(0, i + 1, 48 + 3 * i, 0.8f, sr));
        double best = 1e9;
        for (int k = 0; k < 3; ++k) {
            auto inst = make(p, sr);
            const double t0 = threadCpuSeconds();
            render(*inst, evs, 3.0, sr);
            best = std::min(best, threadCpuSeconds() - t0);
        }
        best = std::max(best, 1e-6);
        std::cout << "  info " << label << ": 3 s rendered in " << best << " s (" << 3.0 / best << "x realtime)\n";
        return best;
    };
    run({{"unison", 1}}, 1, "1 voice, 1 osc");
    run({{"unison", 1}, {"osc2.level", 1}}, 8, "8 voices, 2 osc");
    const double heavy = run({{"unison", 7}, {"osc2.level", 1}}, 8, "8 voices, unison 7, 2 osc, stereo (worst case)");
    check(heavy < 30.0, "worst-case patch renders in bounded time (generous limit, also holds for -O0 builds)");
    const json mods = {route(lfoHz("sine", 5.5, {{"delay", 0.2}}), "pitch", 15), route(lfoHz("triangle", 0.3, {{"mode", "global"}}), "osc2.pw", 0.3),
                       route(envSrc(0, 0.08, 0, 0.1), "cutoff", 2), route({{"type", "velocity"}}, "amp", 6),
                       route({{"type", "random"}}, "pan", 0.3), route(macroSrc(1), "resonance", 0.3),
                       route({{"type", "key"}}, "cutoff", 0.5), route(lfoBeats("samplehold", 0.25), "filter.drive", 0.3)};
    const double modded = run(withMods({{"unison", 7}, {"osc2.level", 1}, {"macro1", 0.5}}, mods), 8,
                              "8 routings, 8 voices, unison 7, 2 osc, stereo");
#ifdef NDEBUG
    // 5x realtime (on a machine so busy that even the plain patch misses it: the routings cost < 20 %)
    check(modded < 0.6 || modded < 1.2 * heavy,
          fmt("8 routings, 8 voices x unison 7: faster than 5x realtime (%.1fx; without routings %.1fx)", 3.0 / modded,
              3.0 / heavy));
#else
    check(modded < 30.0, "8 routings, 8 voices x unison 7: bounded time (debug build)");
#endif
    run(withMods({{"unison", 1}, {"osc1.wave", "sine"}, {"osc2.wave", "sine"}, {"osc2.semi", 19}},
                 {route(envSrc(0, 0.5, 0.1, 0.5), "fm", 4)}),
        8, "8 voices, fm with an env");
}

}  // namespace

int main() {
    std::cout << "test_va\n";
    testSpecs();
    testModConfig();
    testPitch();
    testFilter();
    testRelease();
    testDeterminism();
    testUnison();
    testChord();
    testStealing();
    testGlide();
    testLadderStability();
    testAliasing();
    testModLfo();
    testModEnv();
    testModSources();
    testModTargets();
    testFm();
    testNoiseStereoAndPhase();
    testModAutomation();
    testModPreview();
    testModMany();
    testSpeed();
    std::cout << (failures ? "FAILED: " + std::to_string(failures) + " check(s)\n" : "all va tests passed\n");
    return failures ? 1 : 0;
}
