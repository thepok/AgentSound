// Tests for the "drums" instrument (engine/instruments/DrumSynth.*). Deterministic; returns nonzero
// on failure and prints every check plus a per-kit/per-piece level table.

#include "instruments/DrumSynth.h"
#include "dsp/Dsp.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

using namespace as;

namespace {

int g_failures = 0;
int g_checks = 0;

void check(bool ok, const std::string& what) {
    ++g_checks;
    if (!ok) {
        ++g_failures;
        std::printf("  FAIL: %s\n", what.c_str());
    }
}

std::string fmt(const char* f, double a, double b = 0.0, double c = 0.0) {
    char buf[256];
    std::snprintf(buf, sizeof buf, f, a, b, c);
    return buf;
}

const char* kKits[] = {"808", "909", "linn", "synthwave", "modern"};

struct Ev {
    double t;
    int pitch;
    float vel;
};

struct Stereo {
    std::vector<float> l, r;
    std::size_t size() const { return l.size(); }
};

std::unique_ptr<Instrument> make(const json& params, double sr = 48000.0, std::uint64_t seed = 1) {
    auto d = makeDrumSynth();
    d->configure(params);
    RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.seed = seed;
    d->prepare(ctx);
    return d;
}

// Sample-accurate render: blocks are split at event times, like the host does.
Stereo render(Instrument& d, std::vector<Ev> evs, double seconds, double sr = 48000.0, int block = 256) {
    std::sort(evs.begin(), evs.end(), [](const Ev& a, const Ev& b) { return a.t < b.t; });
    const auto total = static_cast<std::size_t>(seconds * sr);
    Stereo out;
    out.l.assign(total, 0.0f);
    out.r.assign(total, 0.0f);
    std::size_t pos = 0, next = 0;
    int noteId = 0;
    while (pos < total) {
        while (next < evs.size() && static_cast<std::size_t>(std::llround(evs[next].t * sr)) <= pos) {
            d.noteOn(noteId++, evs[next].pitch, evs[next].vel);
            ++next;
        }
        std::size_t end = std::min(total, pos + static_cast<std::size_t>(block));
        if (next < evs.size()) end = std::min(end, static_cast<std::size_t>(std::llround(evs[next].t * sr)));
        d.process(out.l.data() + pos, out.r.data() + pos, static_cast<int>(end - pos));
        pos = end;
    }
    return out;
}

double peakAbs(const Stereo& s, std::size_t a = 0, std::size_t b = SIZE_MAX) {
    double p = 0.0;
    for (std::size_t i = a; i < std::min(b, s.size()); ++i) p = std::max({p, (double)std::fabs(s.l[i]), (double)std::fabs(s.r[i])});
    return p;
}

double energy(const Stereo& s, std::size_t a, std::size_t b) {
    double e = 0.0;
    for (std::size_t i = a; i < std::min(b, s.size()); ++i) e += (double)s.l[i] * s.l[i] + (double)s.r[i] * s.r[i];
    return e;
}

double rmsDb(const Stereo& s, std::size_t a, std::size_t b) {
    b = std::min(b, s.size());
    if (b <= a) return -200.0;
    return 10.0 * std::log10(std::max(energy(s, a, b) / (2.0 * (double)(b - a)), 1e-30));
}

bool allFinite(const Stereo& s) {
    for (std::size_t i = 0; i < s.size(); ++i)
        if (!std::isfinite(s.l[i]) || !std::isfinite(s.r[i])) return false;
    return true;
}

double maxStep(const Stereo& s, std::size_t a, std::size_t b) {
    double m = 0.0;
    for (std::size_t i = std::max<std::size_t>(a, 1); i < std::min(b, s.size()); ++i)
        m = std::max({m, (double)std::fabs(s.l[i] - s.l[i - 1]), (double)std::fabs(s.r[i] - s.r[i - 1])});
    return m;
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
        const double ang = -2.0 * 3.14159265358979323846 / (double)len;
        const std::complex<double> wl(std::cos(ang), std::sin(ang));
        for (std::size_t i = 0; i < n; i += len) {
            std::complex<double> w(1.0);
            for (std::size_t k = 0; k < len / 2; ++k) {
                const auto u = a[i + k], v = a[i + k + len / 2] * w;
                a[i + k] = u + v;
                a[i + k + len / 2] = u - v;
                w *= wl;
            }
        }
    }
}

// Power-weighted spectral centroid of the mono sum over the first 2^16 samples.
double centroid(const Stereo& s, double sr) {
    std::size_t n = 1;
    while (n < s.size() && n < (1u << 16)) n <<= 1;
    std::vector<std::complex<double>> a(n);
    for (std::size_t i = 0; i < std::min(n, s.size()); ++i) a[i] = 0.5 * ((double)s.l[i] + s.r[i]);
    fft(a);
    double num = 0.0, den = 0.0;
    for (std::size_t k = 1; k < n / 2; ++k) {
        const double p = std::norm(a[k]);
        num += p * (double)k * sr / (double)n;
        den += p;
    }
    return den > 0.0 ? num / den : 0.0;
}

// Energy of the mono sum between lo and hi Hz (first 2^16 samples).
double bandEnergy(const Stereo& s, double sr, double lo, double hi) {
    std::size_t n = 1;
    while (n < s.size() && n < (1u << 16)) n <<= 1;
    std::vector<std::complex<double>> a(n);
    for (std::size_t i = 0; i < std::min(n, s.size()); ++i) a[i] = 0.5 * ((double)s.l[i] + s.r[i]);
    fft(a);
    double e = 0.0;
    for (std::size_t k = 1; k < n / 2; ++k) {
        const double f = (double)k * sr / (double)n;
        if (f >= lo && f < hi) e += std::norm(a[k]);
    }
    return e;
}

struct PieceInfo {
    int pitch;
    const char* name;
};
const PieceInfo kPieces[] = {{35, "kick35"}, {36, "kick"},     {37, "rim"},     {38, "snare"},  {40, "snare40"},
                             {39, "clap"},   {42, "hat.cl"},   {44, "hat.ped"}, {46, "hat.op"}, {41, "tom41"},
                             {43, "tom43"},  {45, "tom45"},    {47, "tom47"},   {48, "tom48"},  {50, "tom50"},
                             {49, "crash"},  {57, "crash57"}, {51, "ride"},    {59, "ride59"}, {54, "tamb"},
                             {56, "cowbell"}};

// The window in which a piece should have decayed (from the resolved params).
double decayWindow(const Instrument& d, int pitch) {
    auto p = [&](const char* n) { return (double)drumSynthParam(d, n); };
    switch (pitch) {
        case 35: case 36: return p("kick.decay");
        case 37: return p("rim.decay");
        case 38: case 40: return p("snare.decay") * std::max(p("snare.noisedecay"), p("snare.bodydecay"));
        case 39: return p("clap.decay") + p("clap.bursts") * p("clap.spread") * 0.0015;
        case 42: return p("hat.decay");
        case 44: return 0.75 * p("hat.decay");
        case 46: return p("hat.opendecay");
        case 41: case 43: case 45: case 47: case 48: case 50: return p("tom.decay");
        case 49: return p("crash.decay");
        case 57: return 0.8 * p("crash.decay");
        case 51: case 59: return p("ride.decay");
        case 54: return p("tamb.decay");
        case 56: return p("cowbell.decay");
        default: return 1.0;
    }
}

// ------------------------------------------------------------------------------------------

void testSpecs() {
    std::printf("[specs] names unique, defaults = default kit, every kit configures\n");
    auto d = makeDrumSynth();
    const auto& specs = d->paramSpecs();
    check(specs.size() > 60, "expected >60 parameters");
    for (std::size_t i = 0; i < specs.size(); ++i) {
        check(!specs[i].help.empty(), "help for " + specs[i].name);
        check(specs[i].def >= specs[i].min && specs[i].def <= specs[i].max, "default in range: " + specs[i].name);
        for (std::size_t j = i + 1; j < specs.size(); ++j) check(specs[i].name != specs[j].name, "duplicate " + specs[i].name);
    }
    d->configure(json::object());
    for (const auto& s : specs) check(drumSynthParam(*d, s.name) == s.def, "spec default matches configured default: " + s.name);
    check(drumSynthParam(*d, "kit") == 3.0f, "default kit is synthwave");
    for (const char* kit : kKits) {
        bool ok = true;
        try {
            auto k = makeDrumSynth();
            k->configure(json{{"kit", kit}});
        } catch (const std::exception& e) {
            ok = false;
            std::printf("  kit %s: %s\n", kit, e.what());
        }
        check(ok, std::string("kit configures: ") + kit);
    }
    check(std::isnan(drumSynthParam(*d, "nope")), "unknown name -> NaN");
    std::printf("  %zu parameters\n", specs.size());
}

void testConfigStrict() {
    std::printf("[config] strict validation\n");
    auto throws = [](const json& j) {
        try {
            makeDrumSynth()->configure(j);
        } catch (const ConfigError&) {
            return true;
        }
        return false;
    };
    check(throws(json{{"kit", "707"}}), "unknown kit throws");
    check(throws(json{{"snare.decay", 5.0}}), "out of range throws");
    check(throws(json{{"snare.decy", 0.2}}), "unknown key throws");
    check(throws(json{{"kick.tune", "low"}}), "wrong type throws");
    check(throws(json::array({1, 2})), "non-object throws");
    check(throws(json{{"kit", 9}}), "kit index out of range throws");
    check(throws(json{{"kit", true}}), "kit as bool throws");
    check(throws(json{{"kit", 1.5}}), "fractional kit index throws");
    check(throws(json{{"hat.model", 0.5}}), "fractional hat.model throws");
    check(throws(json{{"crash.width", 1.5}}), "crash.width out of range throws");
    check(!throws(json{{"kit", 2.0}}), "integral kit index accepted");
    check(!throws(json{{"kit", 2}}), "kit by index accepted");
    check(!throws(json(nullptr)), "null params accepted");
}

void testKitPrecedence() {
    std::printf("[kit] kit defaults, then per-piece overrides\n");
    auto d = makeDrumSynth();
    d->configure(json{{"kit", "909"}});
    check(drumSynthParam(*d, "kit") == 1.0f, "kit=909 index");
    check(std::fabs(drumSynthParam(*d, "snare.decay") - 0.30f) < 1e-6f, "909 snare.decay default 0.30");
    check(std::fabs(drumSynthParam(*d, "kick.tune") - 53.0f) < 1e-6f, "909 kick.tune default 53");
    check(drumSynthParam(*d, "hat.model") == 1.0f, "909 hat.model = 909");
    d->configure(json{{"kit", "909"}, {"snare.decay", 0.6}});
    check(std::fabs(drumSynthParam(*d, "snare.decay") - 0.6f) < 1e-6f, "override snare.decay wins over kit");
    check(std::fabs(drumSynthParam(*d, "kick.tune") - 53.0f) < 1e-6f, "other 909 defaults kept");
    // a key that sorts before "kit" still overrides the kit
    d->configure(json{{"hat.decay", 0.2}, {"kit", "808"}});
    check(std::fabs(drumSynthParam(*d, "hat.decay") - 0.2f) < 1e-6f, "hat.decay override (sorts before kit)");
    check(std::fabs(drumSynthParam(*d, "hat.opendecay") - 0.45f) < 1e-6f, "808 hat.opendecay default");
    check(drumSynthParam(*d, "hat.model") == 0.0f, "808 hat.model = 808");
    // reconfigure resets: no leftovers from the previous configure
    d->configure(json{{"kit", "808"}});
    check(std::fabs(drumSynthParam(*d, "hat.decay") - 0.06f) < 1e-6f, "reconfigure starts from fresh defaults");

    // audible: longer override = more late energy
    auto a = make(json{{"kit", "909"}, {"humanize", 0}});
    auto b = make(json{{"kit", "909"}, {"humanize", 0}, {"snare.decay", 0.9}});
    const Stereo sa = render(*a, {{0.0, 38, 1.0f}}, 1.0), sb = render(*b, {{0.0, 38, 1.0f}}, 1.0);
    const double la = energy(sa, 14400, 48000), lb = energy(sb, 14400, 48000);
    check(lb > 20.0 * la, fmt("snare.decay 0.9 rings longer than 909 default (late energy x%.1f)", lb / std::max(la, 1e-30)));
    // kits really sound different
    auto k8 = make(json{{"kit", "808"}, {"humanize", 0}}), k9 = make(json{{"kit", "909"}, {"humanize", 0}});
    const Stereo s8 = render(*k8, {{0.0, 36, 1.0f}}, 2.0), s9 = render(*k9, {{0.0, 36, 1.0f}}, 2.0);
    check(energy(s8, 24000, 96000) > 10.0 * energy(s9, 24000, 96000), "808 kick booms much longer than 909 kick");
}

void testPieces(double sr, bool table) {
    std::printf("[pieces @ %.0f Hz] every mapped pitch, every kit: finite, audible, decays, idles, peak < -1 dBFS\n", sr);
    if (table)
        std::printf("  %-10s %-8s %8s %8s %8s %9s %8s %8s\n", "kit", "piece", "peakdB", "rms100", "rmsWin", "centroid",
                    "window", "tail/hd");
    for (const char* kit : kKits) {
        for (const auto& pc : kPieces) {
            auto d = make(json{{"kit", kit}, {"humanize", 0}}, sr);
            const double win = decayWindow(*d, pc.pitch);
            const double secs = 2.0 * win + 0.25;
            const Stereo s = render(*d, {{0.0, pc.pitch, 1.0f}}, secs, sr);
            const std::string tag = std::string(kit) + "/" + pc.name;
            const double pk = peakAbs(s);
            const auto w = static_cast<std::size_t>(win * sr);
            const double head = energy(s, 0, w / 10), tail = energy(s, w - w / 10, w);
            const double ratioDb = 10.0 * std::log10(std::max(tail, 1e-30) / std::max(head, 1e-30));
            check(allFinite(s), tag + " finite");
            check(pk > 0.02, tag + fmt(" audible (peak %.4f)", pk));
            check(pk < 0.891, tag + fmt(" peak below -1 dBFS (%.2f dB)", 20.0 * std::log10(pk)));
            check(ratioDb < -30.0, tag + fmt(" decays: last 10%% of window %.1f dB below first 10%%", ratioDb));
            check(d->idle(), tag + " idle after 2 x window");
            if (table)
                std::printf("  %-10s %-8s %8.1f %8.1f %8.1f %9.0f %8.3f %8.1f\n", kit, pc.name, 20.0 * std::log10(pk),
                            rmsDb(s, 0, static_cast<std::size_t>(0.1 * sr)), rmsDb(s, 0, std::max<std::size_t>(w, 1)),
                            centroid(s, sr), win, ratioDb);
        }
    }
}

void testCentroids(double sr) {
    std::printf("[spectrum @ %.0f Hz] centroid kick < snare < closed hat, every kit\n", sr);
    for (const char* kit : kKits) {
        auto c = [&](int pitch) {
            auto d = make(json{{"kit", kit}, {"humanize", 0}}, sr);
            return centroid(render(*d, {{0.0, pitch, 1.0f}}, 1.0, sr), sr);
        };
        const double k = c(36), s = c(38), h = c(42);
        std::printf("  %-10s kick %6.0f Hz  snare %6.0f Hz  hat %6.0f Hz\n", kit, k, s, h);
        check(k * 3.0 < s, std::string(kit) + " kick centroid well below snare");
        check(s * 1.5 < h, std::string(kit) + " snare centroid well below hat");
        check(k < 400.0, std::string(kit) + " kick centroid < 400 Hz");
    }
}

void testKickClean() {
    std::printf("[kick] clean sub: no DC, no click unless asked\n");
    for (const char* kit : kKits) {
        auto d = make(json{{"kit", kit}, {"humanize", 0}, {"kick.click", 0.0}});
        const Stereo s = render(*d, {{0.0, 36, 1.0f}}, 3.0);
        double sum = 0.0;
        for (float v : s.l) sum += v;
        const double mean = sum / (double)s.size(), pk = peakAbs(s);
        check(std::fabs(mean) < 1e-4 * pk, std::string(kit) + fmt(" kick DC mean %.2e", mean));
        // first samples rise from zero (no step without click)
        check(std::fabs(s.l[0]) < 1e-3 && maxStep(s, 0, 48) < 0.05, std::string(kit) + fmt(" kick onset has no step (%.4f)", maxStep(s, 0, 48)));
        // the tail is a clean low sine: very little energy above 1 kHz after 150 ms
        Stereo tail;
        tail.l.assign(s.l.begin() + 7200, s.l.begin() + 7200 + 16384);
        tail.r.assign(s.r.begin() + 7200, s.r.begin() + 7200 + 16384);
        const double ct = centroid(tail, 48000.0);
        check(ct < 200.0, std::string(kit) + fmt(" kick tail centroid %.0f Hz (clean sub)", ct));
    }
    auto withClick = make(json{{"kit", "909"}, {"humanize", 0}, {"kick.click", 1.0}});
    auto noClick = make(json{{"kit", "909"}, {"humanize", 0}, {"kick.click", 0.0}});
    const Stereo a = render(*withClick, {{0.0, 36, 1.0f}}, 0.05), b = render(*noClick, {{0.0, 36, 1.0f}}, 0.05);
    const double ha = bandEnergy(a, 48000.0, 1500.0, 20000.0), hb = bandEnergy(b, 48000.0, 1500.0, 20000.0);
    check(ha > 10.0 * hb, fmt("kick.click adds a high-frequency transient (+%.1f dB above 1.5 kHz)", 10.0 * std::log10(ha / hb)));
}

void testChoke() {
    std::printf("[hats] open hat choked by closed and pedal hat\n");
    for (int chokePitch : {42, 44}) {
        auto a = make(json{{"humanize", 0}}), b = make(json{{"humanize", 0}});
        const Stereo open = render(*a, {{0.0, 46, 1.0f}}, 0.8);
        const Stereo choked = render(*b, {{0.0, 46, 1.0f}, {0.1, chokePitch, 1.0f}}, 0.8);
        const double eo = energy(open, 9600, 38400), ec = energy(choked, 9600, 38400);
        check(ec < 0.02 * eo, fmt("pitch %.0f chokes open hat (energy 0.2-0.8 s: %.1f dB)", chokePitch, 10.0 * std::log10(ec / eo)));
        auto c = make(json{{"humanize", 0}});
        const Stereo closedOnly = render(*c, {{0.1, chokePitch, 1.0f}}, 0.2);
        const double natural = std::max(maxStep(open, 4700, 5300), maxStep(closedOnly, 4700, 5300));
        check(maxStep(choked, 4700, 5300) < 1.5 * natural,
              fmt("choke is a fade, max step %.3f vs natural %.3f", maxStep(choked, 4700, 5300), natural));
    }
    // other pieces do not choke the open hat
    auto a = make(json{{"humanize", 0}}), b = make(json{{"humanize", 0}});
    const Stereo open = render(*a, {{0.0, 46, 1.0f}}, 0.4);
    const Stereo withSnare = render(*b, {{0.0, 46, 1.0f}, {0.1, 38, 1.0f}}, 0.4);
    check(energy(withSnare, 14400, 19200) > energy(open, 14400, 19200), "snare does not choke the open hat");
}

void testRetrigger() {
    std::printf("[retrigger] same-piece retrigger crossfades (no discontinuity)\n");
    struct Case {
        int pitch;
        const char* name;
    };
    for (const char* kit : kKits) {
        for (const Case c : {Case{36, "kick"}, Case{45, "tom"}, Case{56, "cowbell"}}) {
            auto d1 = make(json{{"kit", kit}, {"humanize", 0}, {"kick.click", 0.0}});
            const Stereo single = render(*d1, {{0.0, c.pitch, 1.0f}}, 0.2);
            const double natural = maxStep(single, 0, single.size());
            for (double t : {0.0503, 0.1371, 0.2219}) {
                auto d = make(json{{"kit", kit}, {"humanize", 0}, {"kick.click", 0.0}});
                const Stereo s = render(*d, {{0.0, c.pitch, 1.0f}, {t, c.pitch, 1.0f}}, t + 0.1);
                const auto at = static_cast<std::size_t>(std::llround(t * 48000.0));
                const double step = maxStep(s, at - 240, at + 2400);
                check(step <= 2.0 * natural + 1e-4,
                      std::string(kit) + "/" + c.name + fmt(" retrigger at %.4f s: max step %.4f vs natural %.4f", t, step, natural));
            }
        }
    }
    // mono kick: after the fade the output equals a fresh single kick
    auto a = make(json{{"humanize", 0}, {"kick.click", 0.0}}), b = make(json{{"humanize", 0}, {"kick.click", 0.0}});
    const Stereo two = render(*a, {{0.0, 36, 1.0f}, {0.25, 36, 1.0f}}, 0.6);
    const Stereo one = render(*b, {{0.25, 36, 1.0f}}, 0.6);
    double diff = 0.0;
    for (std::size_t i = 12000 + 960; i < two.size(); ++i) diff = std::max(diff, (double)std::fabs(two.l[i] - one.l[i]));
    check(diff < 1e-6, fmt("retriggered kick fully replaced after 20 ms (max diff %.2e)", diff));
    // polyphonic snare: 16 rapid hits never exceed the pool and never produce steps > a single hit
    auto sn = make(json{{"humanize", 0}});
    std::vector<Ev> roll;
    for (int i = 0; i < 16; ++i) roll.push_back({0.02 * i, 38, 1.0f});
    const Stereo r = render(*sn, roll, 1.2);
    check(allFinite(r) && peakAbs(r) < 1.0, fmt("snare roll stays finite and below 0 dBFS (peak %.3f)", peakAbs(r)));
}

void testDeterminism() {
    std::printf("[determinism] same seed = identical, humanize seeded, block-size independent\n");
    std::vector<Ev> pat;
    for (int i = 0; i < 16; ++i) {
        pat.push_back({0.125 * i, 42, 0.8f});
        if (i % 4 == 0) pat.push_back({0.125 * i, 36, 1.0f});
        if (i % 8 == 4) pat.push_back({0.125 * i, 38, 0.9f});
    }
    pat.push_back({0.0, 49, 1.0f});
    pat.push_back({1.5, 39, 1.0f});
    pat.push_back({1.75, 46, 1.0f});
    pat.push_back({1.9, 54, 0.7f});
    auto a = make(json{{"humanize", 1.0}}, 48000, 7), b = make(json{{"humanize", 1.0}}, 48000, 7);
    auto c = make(json{{"humanize", 1.0}}, 48000, 8);
    auto e = make(json{{"humanize", 1.0}}, 48000, 7);
    const Stereo sa = render(*a, pat, 2.5), sb = render(*b, pat, 2.5), sc = render(*c, pat, 2.5);
    const Stereo se = render(*e, pat, 2.5, 48000.0, 37);
    check(sa.l == sb.l && sa.r == sb.r, "same seed + humanize -> bit-identical");
    check(sa.l != sc.l, "different seed -> different render");
    check(sa.l == se.l && sa.r == se.r, "block size 37 vs 256 -> bit-identical");
    // widened pieces that stop and restart (decorrelator hold expiring mid-block) stay block-size independent
    const std::vector<Ev> wide = {{0.0, 39, 1.0f}, {1.0, 39, 0.9f}, {1.0, 51, 0.7f}, {2.3131, 39, 1.0f}};
    for (int blk : {1, 37, 100}) {
        auto x = make(json{{"humanize", 0.5}}, 48000, 5), y = make(json{{"humanize", 0.5}}, 48000, 5);
        const Stereo sx = render(*x, wide, 6.0, 48000.0, 256), sy = render(*y, wide, 6.0, 48000.0, blk);
        check(sx.l == sy.l && sx.r == sy.r, fmt("width/decorrelator: block size %.0f vs 256 -> bit-identical", blk));
    }

    // humanize 0: a noise-free kick repeats exactly; humanize 1: it does not
    auto h0 = make(json{{"humanize", 0.0}, {"kick.click", 0.0}});
    auto h1 = make(json{{"humanize", 1.0}, {"kick.click", 0.0}});
    const Stereo r0 = render(*h0, {{0.0, 36, 1.0f}, {2.0, 36, 1.0f}}, 4.0);
    const Stereo r1 = render(*h1, {{0.0, 36, 1.0f}, {2.0, 36, 1.0f}}, 4.0);
    auto sameHalves = [](const Stereo& s) {
        for (std::size_t i = 0; i < 96000; ++i)
            if (s.l[i] != s.l[i + 96000]) return false;
        return true;
    };
    check(sameHalves(r0), "humanize 0: repeated kick identical");
    check(!sameHalves(r1), "humanize 1: repeated kick varies");
    double d = 0.0, ref = 0.0;
    for (std::size_t i = 0; i < 96000; ++i) {
        d += std::pow(r1.l[i] - r1.l[i + 96000], 2);
        ref += std::pow(r1.l[i], 2);
    }
    check(d < 0.5 * ref, fmt("humanize variation stays subtle (diff/ref energy %.3f)", d / ref));
}

void testVelocityAndAutomation() {
    std::printf("[velocity/automation]\n");
    auto loud = make(json{{"humanize", 0}}), soft = make(json{{"humanize", 0}});
    const double pl = peakAbs(render(*loud, {{0.0, 38, 1.0f}}, 0.5));
    const double ps = peakAbs(render(*soft, {{0.0, 38, 0.5f}}, 0.5));
    const double dropDb = 20.0 * std::log10(ps / pl);
    check(dropDb < -4.0 && dropDb > -14.0, fmt("velocity 0.5 is %.1f dB below 1.0 (sensitivity 0.6)", dropDb));
    auto flat = make(json{{"humanize", 0}, {"velocity", 0.0}, {"kick.click", 0.0}});
    const double f1 = peakAbs(render(*flat, {{0.0, 36, 1.0f}}, 0.3));
    auto flat2 = make(json{{"humanize", 0}, {"velocity", 0.0}, {"kick.click", 0.0}});
    const double f2 = peakAbs(render(*flat2, {{0.0, 36, 0.3f}}, 0.3));
    check(std::fabs(f1 - f2) < 1e-6, "velocity sensitivity 0: level independent of velocity");

    auto d = make(json{{"humanize", 0}});
    check(!d->setParam("kit", 1.0f), "kit not automatable");
    check(!d->setParam("hat.model", 1.0f), "hat.model not automatable");
    check(!d->setParam("nope", 1.0f), "unknown param rejected");
    check(d->setParam("kick.decay", 0.3f), "kick.decay automatable");
    // level automation on a ringing open hat: smooth, and it takes effect
    auto h = make(json{{"humanize", 0}, {"hat.opendecay", 2.0}});
    Stereo s;
    s.l.assign(48000, 0.0f);
    s.r.assign(48000, 0.0f);
    h->noteOn(0, 46, 1.0f);
    h->process(s.l.data(), s.r.data(), 12000);
    h->setParam("hat.level", -40.0f);
    h->setParam("hat.pan", 1.0f);
    for (int off = 12000; off < 48000; off += 256) h->process(s.l.data() + off, s.r.data() + off, std::min(256, 48000 - off));
    check(energy(s, 24000, 36000) < 1e-3 * energy(s, 0, 12000), "hat.level automation reaches ringing voice");
    check(maxStep(s, 11990, 12100) < 2.0 * maxStep(s, 11000, 11990) + 1e-4, "level/pan automation is click-free");
    double le = 0.0, re = 0.0;
    for (std::size_t i = 20000; i < 24000; ++i) le += s.l[i] * s.l[i], re += s.r[i] * s.r[i];
    check(le < 1e-3 * re, "pan automation to 1 moves the ringing hat right");
    // master level
    auto m = make(json{{"humanize", 0}, {"level", -12.0}}), m0 = make(json{{"humanize", 0}});
    const double pm = peakAbs(render(*m, {{0.0, 36, 1.0f}}, 0.3)), p0 = peakAbs(render(*m0, {{0.0, 36, 1.0f}}, 0.3));
    check(std::fabs(20.0 * std::log10(pm / p0) + 12.0) < 0.2, "level -12 dB");
}

void testMisc() {
    std::printf("[misc] unmapped pitches, noteOff, idle, extreme settings\n");
    auto d = make(json::object());
    check(d->idle(), "idle after prepare");
    const Stereo s = render(*d, {{0.0, 60, 1.0f}, {0.01, 34, 1.0f}, {0.02, 52, 1.0f}}, 0.2);
    check(peakAbs(s) == 0.0 && d->idle(), "unmapped pitches are silent");
    d->noteOn(1, 46, 1.0f);
    d->noteOff(1);
    check(!d->idle(), "noteOff ignored (one-shot)");

    // extreme settings stay finite and below 0 dBFS at level 0 dB
    json hot = {{"humanize", 1.0},    {"kick.drive", 1.0},  {"kick.sub", 1.0},       {"kick.click", 1.0},
                {"kick.punch", 1.0},  {"kick.pitchenv", 60}, {"kick.tune", 150},     {"snare.tone", 1.0},
                {"snare.snappy", 1.0}, {"clap.bursts", 8},   {"clap.spread", 2},     {"hat.noise", 1.0},
                {"hat.tone", 1.0},    {"hat.tune", 24},     {"crash.tone", 1.0},    {"crash.tune", 24},
                {"ride.bell", 1.0},   {"ride.tune", 24},    {"tamb.tune", 24},      {"rim.tune", 24},
                {"cowbell.tune", 24}, {"tom.drop", 36},     {"tom.tune", 24}};
    for (double sr : {44100.0, 96000.0}) {
        for (const auto& pc : kPieces) {
            auto x = make(hot, sr);
            const Stereo o = render(*x, {{0.0, pc.pitch, 1.0f}}, 0.6, sr);
            check(allFinite(o) && peakAbs(o) < 1.0,
                  std::string("extreme ") + pc.name + fmt(" @%.0f finite, peak %.3f", sr, peakAbs(o)));
        }
    }
    json low = {{"kick.tune", 25}, {"kick.decay", 4.0}, {"tom.tune", -24}, {"hat.tune", -24}, {"crash.decay", 10}, {"hat.decay", 0.01}};
    for (const auto& pc : kPieces) {
        auto x = make(low);
        const Stereo o = render(*x, {{0.0, pc.pitch, 0.05f}}, 0.3);
        check(allFinite(o), std::string("low settings ") + pc.name + " finite");
    }
}

void testGrooveAndSpeed() {
    std::printf("[groove] 120 BPM synthwave pattern: level and speed\n");
    std::vector<Ev> pat;
    const double beat = 0.5;
#ifdef NDEBUG
    const double bars = 90;  // 3 minutes
#else
    const double bars = 16;  // unoptimized builds: keep the test quick
#endif
    for (int b = 0; b < (int)bars; ++b) {
        const double t0 = b * 4 * beat;
        if (b % 8 == 0) pat.push_back({t0, 49, 1.0f});
        for (int q = 0; q < 4; ++q) pat.push_back({t0 + q * beat, 36, 1.0f});
        const bool fillBar = b % 4 == 3;  // the tom fill replaces the last backbeat
        pat.push_back({t0 + 1 * beat, 38, 1.0f});
        pat.push_back({t0 + 1 * beat, 39, 0.8f});
        if (!fillBar) {
            pat.push_back({t0 + 3 * beat, 38, 1.0f});
            pat.push_back({t0 + 3 * beat, 39, 0.8f});
        }
        for (int s = 0; s < 16; ++s) pat.push_back({t0 + s * beat / 4, s % 4 == 2 ? 46 : 42, s % 2 ? 0.6f : 0.85f});
        for (int e = 0; e < 8; ++e) pat.push_back({t0 + e * beat / 2, 51, 0.5f});
        pat.push_back({t0 + 3.5 * beat, 54, 0.7f});
        if (fillBar) {
            const int fill[6] = {50, 48, 47, 45, 43, 41};
            for (int s = 0; s < 6; ++s) pat.push_back({t0 + 2 * beat + s * beat / 3, fill[s], 0.9f});
        }
    }
    auto d = make(json::object(), 48000, 3);
    const auto t0 = std::chrono::steady_clock::now();
    const Stereo s = render(*d, pat, bars * 4 * beat + 1.0);
    const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    const double rms = rmsDb(s, 0, s.size()), pk = 20.0 * std::log10(peakAbs(s));
    std::printf("  full kit groove: RMS %.1f dBFS, peak %.1f dBFS; %.0f s rendered in %.2f s (%.0fx realtime)\n", rms,
                pk, bars * 4 * beat, secs, (bars * 4 * beat) / secs);
    check(allFinite(s), "groove finite");
    check(rms > -22.0 && rms < -8.0, fmt("groove RMS %.1f dBFS in -22..-8", rms));
    check(pk < -1.0, fmt("groove peak %.1f dBFS < -1", pk));
#ifdef NDEBUG
    check(secs < 20.0, "3-minute dense groove renders in < 20 s (release build)");
#endif
}

// Max K-weighted (BS.1770 shelf + RLB, 48 kHz) 400 ms loudness of a render, LUFS-like.
double momentary(const Stereo& s) {
    using BT = dsp::Biquad::Type;
    dsp::Biquad sl, hl, sr, hr;
    sl.set(BT::HighShelf, 48000.0, 1681.0, 0.707, 4.0);
    hl.set(BT::HighPass, 48000.0, 38.0, 0.5);
    sr = sl;
    hr = hl;
    std::vector<double> e(s.size());
    for (std::size_t i = 0; i < s.size(); ++i) {
        const double a = hl.process(sl.process(s.l[i])), b = hr.process(sr.process(s.r[i]));
        e[i] = a * a + b * b;
    }
    double best = 0.0, acc = 0.0;
    const std::size_t w = 19200;
    for (std::size_t i = 0; i < e.size(); ++i) {
        acc += e[i];
        if (i >= w) acc -= e[i - w];
        best = std::max(best, acc / (double)w);
    }
    return -0.691 + 10.0 * std::log10(best + 1e-30);
}

// Loudness of one full-velocity hit, averaged over a few seeds (noise pieces vary per hit).
double hitLoudness(const json& params, int pitch) {
    double e = 0.0;
    for (std::uint64_t seed = 1; seed <= 4; ++seed) {
        auto d = make(params, 48000.0, seed * 77);
        e += std::pow(10.0, momentary(render(*d, {{0.0, pitch, 1.0f}}, 1.5)) / 10.0);
    }
    return 10.0 * std::log10(e / 4.0);
}

void testBalance() {
    std::printf("[balance] pieces balanced against the kick, kits level-matched, hat.noise/tone keep the level\n");
    struct Target {
        int pitch;
        const char* name;
        double relKick;
    };
    const Target targets[] = {{38, "snare", -2}, {39, "clap", -4}, {42, "hat.cl", -15}, {45, "tom45", -3},
                              {49, "crash", -5}, {51, "ride", -9}, {37, "rim", -9},     {56, "cowbell", -10},
                              {54, "tamb", -12}};
    const double refKick = hitLoudness(json{{"humanize", 0}}, 36);
    for (const char* kit : kKits) {
        const json p = {{"kit", kit}, {"humanize", 0}};
        const double kick = hitLoudness(p, 36);
        check(std::fabs(kick - refKick) < 1.0, std::string(kit) + fmt(" kick loudness %.1f vs synthwave %.1f LU", kick, refKick));
        std::printf("  %-10s kick %6.1f LU |", kit, kick);
        for (const auto& t : targets) {
            const double rel = hitLoudness(p, t.pitch) - kick;
            std::printf(" %s %+.1f", t.name, rel);
            check(std::fabs(rel - t.relKick) < 1.5,
                  std::string(kit) + "/" + t.name + fmt(" is %.1f LU vs kick (target %.0f)", rel, t.relKick));
        }
        std::printf("\n");
    }
    // hat.noise is an equal-loudness crossfade, hat.tone changes colour more than level
    const double n0 = hitLoudness(json{{"humanize", 0}, {"hat.noise", 0.0}}, 42);
    const double n5 = hitLoudness(json{{"humanize", 0}, {"hat.noise", 0.5}}, 42);
    const double n1 = hitLoudness(json{{"humanize", 0}, {"hat.noise", 1.0}}, 42);
    check(std::max({n0, n5, n1}) - std::min({n0, n5, n1}) < 2.5,
          fmt("hat.noise 0/0.5/1 loudness %.1f/%.1f", n0, n5) + fmt("/%.1f LU (within 2.5)", n1));
    for (const char* model : {"808", "909"}) {
        const double t0 = hitLoudness(json{{"humanize", 0}, {"hat.model", model}, {"hat.tone", 0.0}}, 42);
        const double t1 = hitLoudness(json{{"humanize", 0}, {"hat.model", model}, {"hat.tone", 1.0}}, 42);
        check(std::fabs(t1 - t0) < 4.0, std::string(model) + fmt(" hat.tone 0 vs 1 loudness %.1f vs %.1f LU", t0, t1));
    }
}

double correlation(const Stereo& s, std::size_t a, std::size_t b) {
    double lr = 0.0, ll = 0.0, rr = 0.0;
    for (std::size_t i = a; i < std::min(b, s.size()); ++i) {
        lr += (double)s.l[i] * s.r[i];
        ll += (double)s.l[i] * s.l[i];
        rr += (double)s.r[i] * s.r[i];
    }
    return lr / std::sqrt(ll * rr + 1e-30);
}

void testWidth() {
    std::printf("[width] crash/ride/clap stereo width: decorrelated, mono-compatible, automatable\n");
    struct Case {
        int pitch;
        const char* param;
        const char* pan;
    };
    for (const Case c : {Case{49, "crash.width", "crash.pan"}, Case{51, "ride.width", "ride.pan"},
                         Case{39, "clap.width", "clap.pan"}}) {
        auto mono = make(json{{"humanize", 0}, {c.param, 0.0}, {c.pan, 0.0}});
        auto wide = make(json{{"humanize", 0}, {c.param, 0.8}, {c.pan, 0.0}});
        const Stereo m = render(*mono, {{0.0, c.pitch, 1.0f}}, 5.0), w = render(*wide, {{0.0, c.pitch, 1.0f}}, 5.0);
        check(m.l == m.r, std::string(c.param) + " = 0 at centre: L == R");
        const double corr = correlation(w, 0, 24000);
        check(corr < 0.6, std::string(c.param) + fmt(" = 0.8: L/R correlation %.2f < 0.6", corr));
        // L + R is exactly the mono signal scaled by 1/sqrt(1 + w^2): no comb filtering in mono
        const double a = 1.0 / std::sqrt(1.0 + 0.8 * 0.8);
        double err = 0.0, ref = 0.0;
        for (std::size_t i = 0; i < m.size(); ++i) {
            err = std::max(err, std::fabs((double)w.l[i] + w.r[i] - a * ((double)m.l[i] + m.r[i])));
            ref = std::max(ref, std::fabs((double)m.l[i] + m.r[i]));
        }
        check(err < 1e-4 * ref, std::string(c.param) + fmt(" mono sum unchanged (max err %.2e of peak)", err / ref));
        // constant power: stereo energy within 0.5 dB of the mono version
        const double de = 10.0 * std::log10(energy(w, 0, w.size()) / energy(m, 0, m.size()));
        check(std::fabs(de) < 0.5, std::string(c.param) + fmt(" keeps the energy (%.2f dB)", de));
        check(wide->idle(), std::string(c.param) + " idle after the tail");
    }
    // a hard-panned wide crash stays on its side
    auto hard = make(json{{"humanize", 0}, {"crash.width", 1.0}, {"crash.pan", -1.0}});
    const Stereo hp = render(*hard, {{0.0, 49, 1.0f}}, 1.0);
    check(peakAbs(Stereo{hp.r, hp.r}) < 1e-6 && peakAbs(hp) > 0.01, "crash.pan -1 with width 1: right channel silent");
    // automation: click-free, reaches the ringing crash
    auto d = make(json{{"humanize", 0}, {"crash.width", 0.0}, {"crash.pan", 0.0}});
    Stereo s;
    s.l.assign(48000, 0.0f);
    s.r.assign(48000, 0.0f);
    d->noteOn(0, 49, 1.0f);
    d->process(s.l.data(), s.r.data(), 12000);
    check(d->setParam("crash.width", 1.0f), "crash.width automatable");
    for (int off = 12000; off < 48000; off += 256) d->process(s.l.data() + off, s.r.data() + off, std::min(256, 48000 - off));
    check(correlation(s, 6000, 12000) > 0.999 && correlation(s, 24000, 36000) < 0.5,
          fmt("width automation 0 -> 1 on a ringing crash (corr %.2f)", correlation(s, 24000, 36000)));
    check(maxStep(s, 11990, 12200) < 1.5 * maxStep(s, 11000, 11990) + 1e-4, "width automation is click-free");
}

}  // namespace

int main(int argc, char** argv) {
    const bool table = argc > 1 && std::string(argv[1]) == "--table";
    testSpecs();
    testConfigStrict();
    testKitPrecedence();
    testPieces(48000.0, table);
    testPieces(44100.0, false);
    testPieces(96000.0, false);
    testCentroids(48000.0);
    testCentroids(96000.0);
    testKickClean();
    testChoke();
    testRetrigger();
    testDeterminism();
    testVelocityAndAutomation();
    testBalance();
    testWidth();
    testMisc();
    testGrooveAndSpeed();
    std::printf("%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
