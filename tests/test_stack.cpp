// The 'stack' instrument (layered children): a stack sums its layers exactly like separate tracks, velocity and
// key crossfades are equal-power (and play in-fade notes at their own gain on the crossfade voices), transpose /
// key ranges / note delay / level / pan / mute / velocity curves do what they say, the emulated sustain pedal holds
// va / dx7 layers, renders are deterministic, strict validation, and the renderer addresses layer params
// ('instrument.layers.<id>.<param>').

#include "dsp/Dsp.h"
#include "instruments/Dx7Banks.h"
#include "instruments/Stack.h"
#include "render/Registry.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

using namespace as;
namespace fs = std::filesystem;

namespace {

int gFail = 0, gChecks = 0;

void check(bool ok, const std::string& what) {
    ++gChecks;
    if (!ok) ++gFail;
    std::printf("  [%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
}

template <typename... A>
std::string fmt(const char* f, A... a) {
    char buf[1024];
    std::snprintf(buf, sizeof buf, f, a...);
    return buf;
}

constexpr double kSr = 48000.0;
constexpr int kBlock = 32;
constexpr std::uint64_t kSeed = 7;

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
};

struct Note {
    long on, off;
    int pitch;
    float vel;
};

struct Set {
    long at;
    std::string name;
    float value;
};

RenderContext context(std::uint64_t seed = kSeed, double startBeat = 0.0) {
    RenderContext ctx;
    ctx.sampleRate = kSr;
    ctx.bpm = 120.0;
    ctx.seed = seed;
    ctx.assetDir = "assets";
    ctx.maxBlock = kBlock;
    ctx.startBeat = startBeat;
    return ctx;
}

// Renders an instrument with sample-accurate notes (blocks split at events) and parameter sets at 32-sample block
// starts, like the renderer.
Stereo render(const std::string& type, const json& config, const std::vector<Note>& notes, long length,
              std::uint64_t seed = kSeed, std::vector<Set> sets = {}) {
    auto inst = createInstrument(type);
    inst->configure(config);
    inst->prepare(context(seed));
    struct Ev { long at; bool on; int id; int pitch; float vel; };
    std::vector<Ev> evs;
    for (std::size_t i = 0; i < notes.size(); ++i) {
        evs.push_back({notes[i].on, true, static_cast<int>(i), notes[i].pitch, notes[i].vel});
        evs.push_back({notes[i].off, false, static_cast<int>(i), notes[i].pitch, 0.0f});
    }
    std::stable_sort(evs.begin(), evs.end(), [](const Ev& a, const Ev& b) {
        if (a.at != b.at) return a.at < b.at;
        return a.on && !b.on;
    });
    std::stable_sort(sets.begin(), sets.end(), [](const Set& a, const Set& b) { return a.at < b.at; });
    Stereo out(static_cast<std::size_t>(length));
    std::size_t ei = 0, si = 0;
    for (long pos = 0; pos < length;) {
        long end = std::min(length, (pos / kBlock + 1) * kBlock);
        if (pos % kBlock == 0) {
            for (; si < sets.size() && sets[si].at <= pos; ++si) {
                if (!inst->setParam(sets[si].name, sets[si].value)) check(false, "setParam(" + sets[si].name + ") refused");
            }
        }
        for (; ei < evs.size() && evs[ei].at <= pos; ++ei) {
            if (evs[ei].on) inst->noteOn(evs[ei].id, evs[ei].pitch, evs[ei].vel);
            else inst->noteOff(evs[ei].id);
        }
        if (ei < evs.size()) end = std::min(end, evs[ei].at);
        inst->process(out.l.data() + pos, out.r.data() + pos, static_cast<int>(end - pos));
        pos = end;
    }
    return out;
}

double maxDiff(const Stereo& a, const Stereo& b, long shift = 0) {
    double d = 0.0;
    for (std::size_t i = 0; i + static_cast<std::size_t>(shift) < a.l.size(); ++i) {
        const std::size_t j = i + static_cast<std::size_t>(shift);
        if (j >= b.l.size()) break;
        d = std::max({d, double(std::fabs(a.l[j] - b.l[i])), double(std::fabs(a.r[j] - b.r[i]))});
    }
    return d;
}

double peak(const Stereo& a, long from = 0, long to = -1) {
    double p = 0.0;
    const long n = to < 0 ? static_cast<long>(a.l.size()) : to;
    for (long i = from; i < n; ++i) p = std::max({p, double(std::fabs(a.l[static_cast<std::size_t>(i)])),
                                                  double(std::fabs(a.r[static_cast<std::size_t>(i)]))});
    return p;
}

double rms(const Stereo& a, long from, long to) {
    double e = 0.0;
    for (long i = from; i < to; ++i) {
        const auto k = static_cast<std::size_t>(i);
        e += double(a.l[k]) * a.l[k] + double(a.r[k]) * a.r[k];
    }
    return std::sqrt(e / std::max(1L, 2 * (to - from)));
}

// Least-squares gain of `part` in `mix`.
double projection(const Stereo& mix, const Stereo& part) {
    double num = 0.0, den = 0.0;
    for (std::size_t i = 0; i < mix.l.size(); ++i) {
        num += double(mix.l[i]) * part.l[i] + double(mix.r[i]) * part.r[i];
        den += double(part.l[i]) * part.l[i] + double(part.r[i]) * part.r[i];
    }
    return den > 0.0 ? num / den : 0.0;
}

// Joint least-squares gains of two parts in `mix`.
void projection2(const Stereo& mix, const Stereo& a, const Stereo& b, double& ga, double& gb) {
    double aa = 0, bb = 0, ab = 0, am = 0, bm = 0;
    auto acc = [&](const std::vector<float>& m, const std::vector<float>& x, const std::vector<float>& y) {
        for (std::size_t i = 0; i < m.size(); ++i) {
            aa += double(x[i]) * x[i];
            bb += double(y[i]) * y[i];
            ab += double(x[i]) * y[i];
            am += double(x[i]) * m[i];
            bm += double(y[i]) * m[i];
        }
    };
    acc(mix.l, a.l, b.l);
    acc(mix.r, a.r, b.r);
    const double det = aa * bb - ab * ab;
    ga = det != 0.0 ? (am * bb - bm * ab) / det : 0.0;
    gb = det != 0.0 ? (bm * aa - am * ab) / det : 0.0;
}

double projection1(const std::vector<float>& mix, const std::vector<float>& part) {
    double num = 0.0, den = 0.0;
    for (std::size_t i = 0; i < mix.size(); ++i) {
        num += double(mix[i]) * part[i];
        den += double(part[i]) * part[i];
    }
    return den > 0.0 ? num / den : 0.0;
}

// A clean looped sine on the sampler (no randomness, flat velocity response not needed: references use the same
// velocity), plain envelope.
json sine(double release = 0.05) {
    return {{"samples", {{"file", "*sine"}, {"loop", "forward"}}}, {"release", release}, {"attack", 0.002}};
}

// The engine's crossfade gain grid: 1 dB steps, within half a step of unity = 1.
double xfq(double g) {
    if (g <= 0.0 || g >= 0.9999) return g <= 0.0 ? 0.0 : 1.0;
    const double db = std::round(20.0 * std::log10(g));
    return db >= 0.0 ? 1.0 : std::pow(10.0, db / 20.0);
}

json layer(const std::string& id, const std::string& type, const json& params, const json& extra = json::object()) {
    json l = {{"id", id}, {"instrument", {{"type", type}, {"params", params}}}};
    for (auto it = extra.begin(); it != extra.end(); ++it) l[it.key()] = it.value();
    return l;
}

json stackRaw(const json& layers, const json& extra = json::object()) {
    json s = json::object();
    s["layers"] = layers;
    for (auto it = extra.begin(); it != extra.end(); ++it) s[it.key()] = it.value();
    return s;
}

// (a vector: brace lists of one layer would otherwise collapse into the layer object itself)
json stack(const std::vector<json>& layers, const json& extra = json::object()) {
    return stackRaw(json(layers), extra);
}

bool configError(const json& config, const std::string& expect) {
    try {
        auto s = createInstrument("stack");
        s->configure(config);
        s->prepare(context());
    } catch (const ConfigError& e) {
        const bool ok = std::string(e.what()).find(expect) != std::string::npos;
        if (!ok) std::printf("       (message was: %s)\n", e.what());
        return ok;
    }
    return false;
}

// ---------------------------------------------------------------------------------------------

void testSum() {
    std::printf("layer sum = separate renders\n");
    const json va = {{"cutoff", 2400}, {"unison", 3}, {"osc2.level", 0.5}, {"osc2.fine", 7}};
    const json dx = {{"voice", "E.PIANO 1"}, {"detune", 6}};
    const std::vector<Note> notes = {{0, 30000, 60, 0.8f}, {4800, 40000, 64, 0.6f}, {12000, 20000, 67, 1.0f}, {50000, 70000, 72, 0.4f}};
    const long len = 96000;
    const Stereo s = render("stack", stack({layer("pad", "va", va), layer("keys", "dx7", dx)}), notes, len);
    const Stereo a = render("va", va, notes, len, stackLayerSeed(kSeed, 0));
    const Stereo b = render("dx7", dx, notes, len, stackLayerSeed(kSeed, 1));
    Stereo sum(static_cast<std::size_t>(len));
    for (long i = 0; i < len; ++i) {
        const auto k = static_cast<std::size_t>(i);
        sum.l[k] = a.l[k] + b.l[k];
        sum.r[k] = a.r[k] + b.r[k];
    }
    const double d = maxDiff(s, sum);
    check(peak(s) > 0.05 && d <= 1e-6, fmt("va + dx7 stack = va render + dx7 render (max diff %.2g, peak %.2f)", d, peak(s)));
    const Stereo one = render("stack", stack({layer("keys", "dx7", dx)}), notes, len);
    const Stereo alone = render("dx7", dx, notes, len, stackLayerSeed(kSeed, 0));
    check(maxDiff(one, alone) == 0.0, "a one-layer stack is bit-identical to its child");

    // level + pan: -6 dB and pan +0.5 (balance: left x cos(pi/4), right unity)
    const Stereo lp = render("stack", stack({layer("keys", "dx7", dx, {{"level", -6}, {"pan", 0.5}})}), notes, len);
    const double gl = projection1(lp.l, alone.l), gr = projection1(lp.r, alone.r);
    const double eg = std::pow(10.0, -6.0 / 20.0);
    check(std::fabs(gl - eg * std::cos(dsp::kPi / 4)) < 1e-4 && std::fabs(gr - eg) < 1e-4,
          fmt("level -6 dB + pan 0.5: left x%.4f right x%.4f (expected %.4f / %.4f)", gl, gr, eg * std::cos(dsp::kPi / 4), eg));
    // stack level
    const Stereo sl = render("stack", stack({layer("keys", "dx7", dx)}, {{"level", -12}}), notes, len);
    check(std::fabs(projection(sl, alone) - std::pow(10.0, -0.6)) < 1e-4, "stack 'level' -12 dB scales the sum");
    // determinism
    const Stereo s2 = render("stack", stack({layer("pad", "va", va), layer("keys", "dx7", dx)}), notes, len);
    check(maxDiff(s, s2) == 0.0, "deterministic: the same config + seed renders bit-identically");
}

void testTransposeKeysDelay() {
    std::printf("transpose, key ranges, note delay, velocity curve\n");
    const json sn = sine();
    const long len = 24000;
    const Stereo up = render("stack", stack({layer("s", "sampler", sn, {{"transpose", 12}})}), {{0, 12000, 60, 0.8f}}, len);
    const Stereo ref = render("sampler", sn, {{0, 12000, 72, 0.8f}}, len, stackLayerSeed(kSeed, 0));
    check(maxDiff(up, ref) == 0.0 && peak(up) > 0.05, "transpose 12: note 60 plays the child's note 72");
    const Stereo oct = render("stack", stack({layer("s", "sampler", sn, {{"transpose", -48}})}), {{0, 12000, 40, 0.8f}}, len);
    check(peak(oct) == 0.0, "notes transposed below 0 are not played on the layer");

    const json ranged = stack({layer("lo", "sampler", sn, {{"keyhi", 59}}), layer("hi", "sampler", sn, {{"keylo", 60}, {"transpose", 7}})});
    const Stereo k59 = render("stack", ranged, {{0, 12000, 59, 0.8f}}, len);
    const Stereo k60 = render("stack", ranged, {{0, 12000, 60, 0.8f}}, len);
    const Stereo r59 = render("sampler", sn, {{0, 12000, 59, 0.8f}}, len, stackLayerSeed(kSeed, 0));
    const Stereo r67 = render("sampler", sn, {{0, 12000, 67, 0.8f}}, len, stackLayerSeed(kSeed, 1));
    check(maxDiff(k59, r59) == 0.0 && maxDiff(k60, r67) == 0.0, "key split: 59 plays only the low layer, 60 only the high one");

    const Stereo del = render("stack", stack({layer("s", "sampler", sn, {{"delay", 10}})}), {{0, 12000, 60, 0.8f}}, len);
    const Stereo nod = render("sampler", sn, {{0, 12000, 60, 0.8f}}, len, stackLayerSeed(kSeed, 0));
    check(peak(del, 0, 480) == 0.0 && maxDiff(del, nod, 480) == 0.0,
          "delay 10 ms: the layer is the child's render 480 samples later (note-off delayed too)");

    const Stereo curved = render("stack", stack({layer("s", "sampler", sn, {{"velcurve", 2}, {"velscale", 1.5}})}), {{0, 12000, 60, 0.6f}}, len);
    const Stereo vref = render("sampler", sn, {{0, 12000, 60, 0.6f * 0.6f * 1.5f}}, len, stackLayerSeed(kSeed, 0));
    check(maxDiff(curved, vref) < 1e-6, "velcurve 2 + velscale 1.5: the child gets 0.6^2 x 1.5");
}

void testCrossfade() {
    std::printf("velocity crossfade (equal power) and crossfade voices\n");
    // soft layer (sine at the note) fades out over 60..90, hard layer (a fifth up) fades in over 60..90
    const json sn = sine();
    const json cfg = stack({layer("soft", "sampler", sn, {{"velhi", 90}, {"velfade", 30}}),
                            layer("hard", "sampler", sn, {{"vello", 60}, {"velfade", 30}, {"transpose", 7}})});
    const long len = 16000;
    bool power = true, monotone = true, ends = true;
    double prevHard = -1.0, worst = 0.0;
    for (int v = 40; v <= 110; v += 5) {
        const float vel = static_cast<float>(v) / 127.0f;
        const Stereo s = render("stack", cfg, {{0, 12000, 60, vel}}, len);
        const Stereo a = render("sampler", sn, {{0, 12000, 60, vel}}, len, stackLayerSeed(kSeed, 0));
        const Stereo b = render("sampler", sn, {{0, 12000, 67, vel}}, len, stackLayerSeed(kSeed, 1));
        double ga = 0.0, gb = 0.0;
        projection2(s, a, b, ga, gb);
        const double pw = ga * ga + gb * gb;   // equal power up to the 1 dB gain grid (each gain within 0.5 dB)
        worst = std::max(worst, std::fabs(10.0 * std::log10(pw)));
        if (std::fabs(10.0 * std::log10(pw)) > 0.5 + 1e-3) power = false;
        if (gb < prevHard - 1e-6) monotone = false;
        prevHard = gb;
        if (v <= 60 && (std::fabs(ga - 1.0) > 1e-4 || std::fabs(gb) > 1e-4)) ends = false;
        if (v >= 90 && (std::fabs(gb - 1.0) > 1e-4 || std::fabs(ga) > 1e-4)) ends = false;
        if (v == 75 && (std::fabs(ga - std::sqrt(0.5)) > 2e-3 || std::fabs(gb - std::sqrt(0.5)) > 2e-3)) ends = false;
    }
    check(power, fmt("equal power over the fade: soft^2 + hard^2 = 1 within the 1 dB gain grid (worst %.2f dB)", worst));
    check(monotone, "the hard layer rises monotonically with velocity");
    check(ends, "outside the fade one layer alone at unity; at 75 both at -3 dB");

    // a chord with notes at different fade gains: each note at its own gain (crossfade voices), exactly the
    // gain-weighted sum of single-note renders
    const std::vector<Note> chord = {{0, 12000, 60, 64 / 127.0f}, {400, 12000, 64, 75 / 127.0f}, {800, 12000, 67, 86 / 127.0f},
                                     {1200, 12000, 71, 110 / 127.0f}, {1600, 12000, 48, 45 / 127.0f}};
    const Stereo s = render("stack", cfg, chord, len);
    Stereo expect(static_cast<std::size_t>(len));
    for (const Note& n : chord) {
        const int v = static_cast<int>(std::lround(n.vel * 127.0f));
        const double x = (v - 60) / 30.0;
        const double gs = v <= 60 ? 1.0 : v >= 90 ? 0.0 : xfq(std::sin((1.0 - x) * dsp::kPi / 2));
        const double gh = v <= 60 ? 0.0 : v >= 90 ? 1.0 : xfq(std::sin(x * dsp::kPi / 2));
        const Stereo a = render("sampler", sn, {{n.on, n.off, n.pitch, n.vel}}, len, stackLayerSeed(kSeed, 0));
        const Stereo b = render("sampler", sn, {{n.on, n.off, n.pitch + 7, n.vel}}, len, stackLayerSeed(kSeed, 1));
        for (long i = 0; i < len; ++i) {
            const auto k = static_cast<std::size_t>(i);
            expect.l[k] += static_cast<float>(gs * a.l[k] + gh * b.l[k]);
            expect.r[k] += static_cast<float>(gs * a.r[k] + gh * b.r[k]);
        }
    }
    const double d = maxDiff(s, expect);
    check(d < 2e-5 * std::max(1.0, peak(expect)), fmt("5-note chord across the fade = sum of its notes at their own gains (max diff %.2g)", d));

    // notes whose fade gains land on the same 1 dB grid value share a crossfade voice: with xfvoices 1 a pair of
    // such velocities still plays exactly at its gains
    int va = -1;
    for (int v = 61; v < 89 && va < 0; ++v) {
        auto gains = [](int w) {
            const double x = (w - 60) / 30.0;
            return std::make_pair(xfq(std::sin((1.0 - x) * dsp::kPi / 2)), xfq(std::sin(x * dsp::kPi / 2)));
        };
        const auto g1 = gains(v), g2 = gains(v + 1);
        if (g1 == g2 && g1.first < 1.0 && g1.second < 1.0) va = v;
    }
    check(va > 0, fmt("two neighbouring velocities share both grid gains (%d / %d)", va, va + 1));
    if (va > 0) {
        json one = cfg;
        one["layers"][0]["xfvoices"] = 1;
        one["layers"][1]["xfvoices"] = 1;
        const std::vector<Note> pair = {{0, 12000, 60, va / 127.0f}, {300, 12000, 64, (va + 1) / 127.0f}};
        const Stereo sp = render("stack", one, pair, len);
        Stereo ep(static_cast<std::size_t>(len));
        for (const Note& n : pair) {
            const int v = static_cast<int>(std::lround(n.vel * 127.0f));
            const double x = (v - 60) / 30.0;
            const double gs = xfq(std::sin((1.0 - x) * dsp::kPi / 2)), gh = xfq(std::sin(x * dsp::kPi / 2));
            const Stereo a = render("sampler", sn, {{n.on, n.off, n.pitch, n.vel}}, len, stackLayerSeed(kSeed, 0));
            const Stereo b = render("sampler", sn, {{n.on, n.off, n.pitch + 7, n.vel}}, len, stackLayerSeed(kSeed, 1));
            for (long i = 0; i < len; ++i) {
                const auto k = static_cast<std::size_t>(i);
                ep.l[k] += static_cast<float>(gs * a.l[k] + gh * b.l[k]);
                ep.r[k] += static_cast<float>(gs * a.r[k] + gh * b.r[k]);
            }
        }
        const double dp = maxDiff(sp, ep);
        check(dp < 2e-5 * std::max(1.0, peak(ep)), fmt("velocities %d + %d share one crossfade voice at their exact grid gains (max diff %.2g)",
                                                       va, va + 1, dp));
    }

    // more fade gains at once than crossfade voices: still finite and audible (the nearest voice's gain)
    std::vector<Note> many;
    for (int i = 0; i < 12; ++i) many.push_back({i * 100L, 12000, 55 + i, (61 + 2 * i) / 127.0f});
    const Stereo m = render("stack", cfg, many, len);
    bool finite = true;
    for (float x : m.l) finite = finite && std::isfinite(x);
    check(finite && peak(m) > 0.05, "12 notes at 12 fade gains on 4 crossfade voices: finite, audible");

    // key crossfade: the same mechanics over the keyboard
    const json kcfg = stack({layer("lo", "sampler", sn, {{"keyhi", 66}, {"keyfade", 6}}),
                             layer("hi", "sampler", sn, {{"keylo", 60}, {"keyfade", 6}, {"transpose", 12}})});
    const Stereo km = render("stack", kcfg, {{0, 12000, 63, 0.8f}}, len);
    const Stereo ka = render("sampler", sn, {{0, 12000, 63, 0.8f}}, len, stackLayerSeed(kSeed, 0));
    const Stereo kb = render("sampler", sn, {{0, 12000, 75, 0.8f}}, len, stackLayerSeed(kSeed, 1));
    double kga = 0.0, kgb = 0.0;
    projection2(km, ka, kb, kga, kgb);
    check(std::fabs(kga - std::sqrt(0.5)) < 1e-3 && std::fabs(kgb - std::sqrt(0.5)) < 1e-3,
          fmt("key crossfade 60..66: key 63 plays both layers at -3 dB (%.3f / %.3f)", kga, kgb));
}

void testPedalMuteParams() {
    std::printf("pedal, mute, follow flags, parameter addressing\n");
    const json dx = {{"voice", "E.PIANO 1"}};
    const long len = 48000;
    const std::vector<Note> n = {{0, 4800, 60, 0.8f}};
    // pedal down from the start: the dx7 layer (no pedal of its own) is held by the stack until pedal-up at 36000
    const Stereo held = render("stack", stack({layer("ep", "dx7", dx)}, {{"pedal", 1}}), n, len, kSeed, {{36000, "pedal", 0}});
    const Stereo dry = render("stack", stack({layer("ep", "dx7", dx)}), n, len);
    const double hr = rms(held, 24000, 30000), dr = rms(dry, 24000, 30000);
    const double hl = rms(held, 44000, 48000);
    check(hr > 4.0 * dr, fmt("emulated pedal holds a dx7 layer after its note-off (%.1f dB louder 0.5 s later)", 20 * std::log10(hr / std::max(dr, 1e-12))));
    check(hl < 0.3 * hr, "pedal-up releases the held note");
    const Stereo nf = render("stack", stack({layer("ep", "dx7", dx, {{"follow.pedal", false}})}, {{"pedal", 1}}), n, len);
    check(maxDiff(nf, dry) == 0.0, "follow.pedal off: the layer ignores the pedal");

    // mute (smoothed) and layer level automation
    const Stereo mu = render("stack", stack({layer("ep", "dx7", dx)}), n, len, kSeed, {{9600, "layers.ep.mute", 1}});
    check(peak(mu, 10560, len) < 1e-4 * peak(mu, 0, 9600) && peak(mu, 12000, len) == 0.0 && peak(mu, 0, 9600) > 0.01,
          "mute automation: -80 dB within 20 ms, exact silence after 50 ms");

    // params addressed through the layer: the child's (dx7 modwheel when not following), fine, the layer fx
    auto s = createInstrument("stack");
    s->configure(stack({layer("ep", "dx7", dx, {{"follow.modwheel", false}, {"fx", json::array({{{"type", "chorus"}, {"params", json::object()}}})}}),
                        layer("pad", "va", json::object())}));
    auto has = [&](const std::string& name) {
        for (const auto& p : s->paramSpecs()) if (p.name == name) return p.automatable;
        return false;
    };
    check(has("layers.ep.modwheel") && has("layers.ep.fx.0.mix") && has("layers.pad.cutoff") && has("layers.pad.fine") &&
              has("layers.ep.level") && has("pitchbend") && has("pedal") && has("expression"),
          "specs: layers.<id>.<child param>, layers.<id>.fx.<i>.<param>, layer params, stack params");
    check(!has("modwheel") && !has("dynamics") && !has("layers.pad.pitchbend") && !has("layers.ep.transpose"),
          "specs: no stack 'modwheel' / 'dynamics' without a following layer, no child pitchbend when it follows the stack");
    s->prepare(context());
    check(s->setParam("layers.pad.cutoff", 900) && s->setParam("layers.ep.fx.0.mix", 0.2f) && s->setParam("layers.ep.modwheel", 0.5f) &&
              s->setParam("layers.pad.fine", 5) && s->setParam("pitchbend", 2) && !s->setParam("layers.zz.cutoff", 1) &&
              !s->setParam("layers.pad.nothing", 1) && !s->setParam("layers.ep.fx.3.mix", 1) && !s->setParam("modwheel", 1),
          "setParam routes layer / child / fx / stack params and refuses unknown ones");
    // fine = pitch bend in cents: +100 ct on a layer = the child a semitone up
    const Stereo fine = render("stack", stack({layer("s", "sampler", sine(), {{"fine", 100}})}), {{0, 12000, 60, 0.8f}}, 16000);
    const Stereo semi = render("sampler", sine(), {{0, 12000, 61, 0.8f}}, 16000, stackLayerSeed(kSeed, 0));
    check(maxDiff(fine, semi) < 2e-3, fmt("fine +100 ct = a semitone up (max diff %.2g)", maxDiff(fine, semi)));
    // follow.bend off: the stack's pitchbend leaves the layer alone
    const Stereo bent = render("stack", stack({layer("s", "sampler", sine(), {{"follow.bend", false}}),
                                                     layer("t", "sampler", sine(), {{"keylo", 100}})}, {{"pitchbend", 12}}),
                               {{0, 12000, 60, 0.8f}}, 16000);
    const Stereo flat = render("sampler", sine(), {{0, 12000, 60, 0.8f}}, 16000, stackLayerSeed(kSeed, 0));
    check(maxDiff(bent, flat) == 0.0, "follow.bend off: the layer does not bend with the stack");
    // expression emulated on a layer without its own (dx7): 0.5 -> -12 dB
    const Stereo ex = render("stack", stack({layer("ep", "dx7", dx)}, {{"expression", 0.5}}), n, len);
    check(std::fabs(projection(ex, dry) - 0.25) < 1e-3, "expression 0.5 on a dx7 layer = x0.25 (-12 dB)");
}

void testDelayedPedal() {
    std::printf("pedal on delayed layers, sampler pedal, flat overrides\n");
    // A typical pedal change: the chord's note-off and pedal-up at 9600, the pedal re-pressed 320 samples later.
    // A layer delayed 50 ms gets its note-off at 12000: the pedal must reach it delayed too, or the re-pressed pedal
    // holds the old chord into the next one.
    const long len = 36000;
    const std::vector<Note> n = {{0, 9600, 60, 0.8f}};
    const std::vector<Set> pedal = {{9600, "pedal", 0}, {9920, "pedal", 1}};
    const json va = {{"amp.release", 0.05}, {"cutoff", 2000}};
    const json sn = sine(0.05);
    for (const auto& [type, cfg] : {std::pair<std::string, json>{"va", va}, std::pair<std::string, json>{"sampler", sn}}) {
        const Stereo now = render("stack", stack({layer("x", type, cfg)}, {{"pedal", 1}}), n, len, kSeed, pedal);
        const Stereo late = render("stack", stack({layer("x", type, cfg, {{"delay", 50}})}, {{"pedal", 1}}), n, len, kSeed, pedal);
        const double held = rms(late, 24000, 36000), ref = rms(late, 4000, 8000);
        check(ref > 0.01 && held < 1e-4 * ref,
              fmt(("delay 50 ms + pedal change (" + type + "): the old note is released 50 ms late, not held by the re-pressed "
                   "pedal (%.1f dB under the note)").c_str(),
                  20 * std::log10(std::max(held, 1e-12) / ref)));
        const double d = maxDiff(late, now, 2400);
        check(d < 1e-4 * peak(now) && peak(late, 0, 2400) == 0.0,
              fmt(("delay 50 ms (" + type + "): notes and pedal together = the undelayed render 2400 samples later (max diff %.2g)").c_str(), d));
    }
    // a ramped pedal lane (a value every 32 samples) on two layers delayed 2 s = only its up / down step: the
    // layers' event queues are not flooded (4000 moves per layer would overflow them)
    {
        const json two = stack({layer("a", "va", va, {{"delay", 2000}}), layer("b", "va", va, {{"delay", 2000}, {"transpose", 7}})},
                               {{"pedal", 1}});
        std::vector<Set> ramp;
        for (int i = 1; i <= 4000; ++i) ramp.push_back({32L * i, "pedal", 1.0f - static_cast<float>(i) / 4000.0f});
        const long rlen = 200000;
        const std::vector<Note> rn = {{0, 4800, 60, 0.8f}, {80000, 90000, 64, 0.8f}};  // the 2nd while the ramp runs
        const Stereo rr = render("stack", two, rn, rlen, kSeed, ramp);
        const Stereo rs = render("stack", two, rn, rlen, kSeed, {{32L * 2001, "pedal", 0}});
        check(peak(rr) > 0.01 && maxDiff(rr, rs) == 0.0 && peak(rr, 0, 96000) == 0.0 && peak(rr, 100000, 176000) > 0.01 &&
                  peak(rr, 170000, 176000) < peak(rr, 176000, 180000),
              "a ramped pedal lane on delayed layers = its up / down step (no queue flood: the notes stay 2 s late)");
    }
    // the sampler's own pedal holds its note across the note-off until pedal-up
    const Stereo sh = render("stack", stack({layer("x", "sampler", sn)}, {{"pedal", 1}}), {{0, 4800, 60, 0.8f}}, len, kSeed, {{24000, "pedal", 0}});
    check(rms(sh, 12000, 20000) > 0.1 * rms(sh, 1000, 4000) && rms(sh, 30000, 36000) < 1e-4 * rms(sh, 1000, 4000),
          "sampler layer: its own pedal holds the note until pedal-up, then it releases");

    // flat overrides next to "layers" = the same values written into the layer
    const json dx = {{"voice", "E.PIANO 1"}};
    const json nested = stack({layer("ep", "dx7", dx, {{"level", -4}, {"fx", json::array({{{"type", "chorus"}, {"params", {{"mix", 0.3}}}}})}}),
                               layer("pad", "va", {{"cutoff", 900}}, {{"transpose", -12}})});
    json flat = stack({layer("ep", "dx7", dx, {{"fx", json::array({{{"type", "chorus"}, {"params", json::object()}}})}}),
                       layer("pad", "va", json::object())});
    flat["layers.ep.level"] = -4;
    flat["layers.ep.fx.0.mix"] = 0.3;
    flat["layers.pad.cutoff"] = 900;
    flat["layers.pad.transpose"] = -12;
    const std::vector<Note> nn = {{0, 20000, 60, 0.8f}, {2000, 20000, 67, 0.7f}};
    const Stereo fa = render("stack", nested, nn, 24000), fb = render("stack", flat, nn, 24000);
    check(peak(fa) > 0.01 && maxDiff(fa, fb) == 0.0, "flat layers.<id>.<param> overrides (layer / fx / child params) = nested values");
    json badFlat = flat;
    badFlat["layers.nope.cutoff"] = 1;
    check(configError(badFlat, "there is no layer 'nope'"), "a flat override for an unknown layer is an error");
    badFlat = flat;
    badFlat["layers.ep.fx.2.mix"] = 1;
    check(configError(badFlat, "has no fx 2"), "a flat override for a missing layer fx is an error");
    badFlat = flat;
    badFlat["layers.pad.nothing"] = 1;
    check(configError(badFlat, "layers[1].instrument"), "a flat override for an unknown child param is the child's error");
}

void testErrors() {
    std::printf("strict validation\n");
    const json dx = {{"voice", "E.PIANO 1"}};
    check(configError(json::object(), "needs \"layers\""), "no layers");
    check(configError(stackRaw(json::array()), "1..8"), "empty layer list");
    json nine = json::array();
    for (int i = 0; i < 9; ++i) nine.push_back(layer("l" + std::to_string(i), "dx7", dx));
    check(configError(stackRaw(nine), "1..8"), "more than 8 layers");
    check(configError(stack({layer("a", "dx7", dx, {{"bogus", 1}})}), "unknown parameter 'bogus'"), "unknown layer key");
    check(configError(stack({layer("a", "dx7", {{"bogus", 1}})}), "layers[0].instrument"), "unknown child param names the layer");
    check(configError(stack({layer("a", "dx7", dx), layer("a", "va", json::object())}), "used by another layer"), "duplicate ids");
    check(configError(stack({layer("A b", "dx7", dx)}), "a-z 0-9"), "bad id");
    check(configError(stack({layer("3", "dx7", dx)}), "not this layer's index"), "a numeric id that is not the index");
    check(configError(stack({layer("a", "stack", stack({layer("b", "dx7", dx)}))}), "can't contain a stack"), "no nesting");
    check(configError(stack({layer("a", "drums", json::object(), {{"fine", 5}})}), "'fine' needs"), "fine on drums");
    check(configError(stack({layer("a", "dx7", dx, {{"keylo", 70}, {"keyhi", 60}})}), "above keyhi"), "keylo > keyhi");
    check(configError(stack({layer("a", "dx7", dx, {{"transpose", 1.5}})}), "whole number"), "fractional transpose");
    check(configError(stack({layer("a", "dx7", dx)}, {{"dynamics", 0.5}}), "no layer follows"), "stack dynamics without a sampler layer");
    check(configError(stack({layer("a", "dx7", dx, {{"fx", json::array({{{"type", "compressor"}, {"sidechain", "kick"}}})}})}), "no sidechain"),
          "sidechain on a layer fx");
    check(configError(stack({layer("a", "dx7", dx, {{"fx", json::array({{{"type", "limiter"}}})}})}), "latency"), "latency fx in a layer");
    check(configError(stack({layer("a", "nope", json::object())}), "unknown instrument type"), "unknown child type");
    check(configError(stack({layer("a", "dx7", dx, {{"pan", 2}})}), "outside"), "out-of-range layer param");
}

void testRenderer() {
    std::printf("renderer: automation of layer params, strict targets, preview\n");
    const json song = json::parse(R"({
      "format": "agentsound.render", "version": 1, "tempo": 120, "lengthBeats": 8, "tailSeconds": 1, "seed": 3,
      "tracks": [{"id": "lead", "instrument": {"type": "stack", "params": {"layers": [
          {"id": "keys", "instrument": {"type": "dx7", "params": {"voice": "E.PIANO 1"}}},
          {"id": "saw", "instrument": {"type": "va", "params": {"cutoff": 1500}}, "transpose": -12, "level": -8,
           "fx": [{"type": "chorus", "params": {"mix": 0.3}}]}]}},
        "notes": [[0,1,60,100],[1,1,64,90],[2,2,67,110],[4,4,72,80]],
        "automation": [{"target": "instrument.layers.saw.cutoff", "points": [[0, 400], [8, 6000, "exp"]]},
                       {"target": "instrument.layers.saw.level", "points": [[0, -20], [4, -6]]},
                       {"target": "instrument.layers.saw.fx.0.mix", "points": [[0, 0], [8, 0.5]]}],
        "modulators": [{"target": "instrument.layers.keys.fine", "source": {"type": "lfo", "shape": "sine", "rateHz": 5},
                        "mode": "offset", "depth": 8, "base": 0}]}]
    })");
    const fs::path dir = fs::temp_directory_path() / "agentsound_test_stack";
    fs::remove_all(dir);
    RenderOptions o;
    o.assetDir = "assets";
    o.analysis = false;
    o.pngs = false;
    o.quiet = true;
    bool ok = true;
    std::string msg;
    try {
        o.outDir = (dir / "a").string();
        renderSong(parseSong(song), o);
        o.outDir = (dir / "b").string();
        renderSong(parseSong(song), o);
    } catch (const std::exception& e) {
        ok = false;
        msg = e.what();
    }
    auto read = [](const fs::path& p) {
        std::ifstream in(p, std::ios::binary);
        return std::vector<char>{std::istreambuf_iterator<char>(in), {}};
    };
    const auto a = read(dir / "a" / "mix.wav"), b = read(dir / "b" / "mix.wav");
    check(ok && !a.empty() && a == b, "a song automating layer / child / layer-fx params renders deterministically" + (msg.empty() ? "" : " (" + msg + ")"));

    auto rejects = [&](const std::string& target, const std::string& expect) {
        json bad = song;
        bad["tracks"][0]["automation"] = json::array({{{"target", target}, {"points", json::array({json::array({0, 1})})}}});
        bad["tracks"][0].erase("modulators");
        try {
            validateSong(parseSong(bad), "assets");
        } catch (const ConfigError& e) {
            return std::string(e.what()).find(expect) != std::string::npos;
        }
        return false;
    };
    check(rejects("instrument.layers.nope.cutoff", "not an automatable instrument parameter"), "an unknown layer id is an error");
    check(rejects("instrument.layers.saw.transpose", "not an automatable instrument parameter"), "a static layer param is not automatable");
    check(rejects("instrument.layers.keys.pitchbend", "not an automatable instrument parameter"),
          "the child's pitchbend is the stack's while the layer follows it");
    fs::remove_all(dir);
}

}  // namespace

int main() {
    std::printf("test_stack\n");
    // Most cases layer a DX7 e-piano; the ROM banks are not distributed (assets/dx7/README.md).
    const bool dx7 = dx7BanksInstalled("assets");
    if (!dx7) std::printf("SKIP: the dx7-layer cases (%s)\n", kDx7NoBanksHint);
    if (dx7) testSum();
    testTransposeKeysDelay();
    testCrossfade();
    if (dx7) {
        testPedalMuteParams();
        testDelayedPedal();
        testErrors();
        testRenderer();
    }
    if (gFail) std::printf("FAILED: %d of %d check(s)\n", gFail, gChecks);
    else std::printf("all %d checks passed\n", gChecks);
    return gFail ? 1 : 0;
}
