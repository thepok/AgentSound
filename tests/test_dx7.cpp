// Tests for the "dx7" instrument and the DX7 ROM bank loader.
// Run from the repo root (or pass the assets folder as argv[1]; "--spread" prints every voice's loudness).

#include "analysis/Loudness.h"
#include "core/Module.h"
#include "instruments/Dx7Banks.h"
#include "instruments/Dx7Synth.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <complex>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iterator>
#include <span>
#include <string>
#include <vector>

// MSFA (raw DX7 reference renders) last: synth.h defines the macro N and global min/max templates.
#include "msfa/synth.h"
#include "msfa/controllers.h"
#include "msfa/dx7note.h"
#include "msfa/lfo.h"
#undef snprintf  // controllers.h maps it to _snprintf on Windows

using namespace as;

namespace {

int gFailures = 0;
int gChecks = 0;

void check(bool ok, const std::string& what) {
    ++gChecks;
    std::printf("[%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
    if (!ok) ++gFailures;
}

std::string gAssets;

struct Audio {
    std::vector<float> l, r;
};

struct Event {
    int at;       // sample
    bool on;
    int id, pitch;
    float vel;
};

std::unique_ptr<Instrument> make(const json& params, double sr = 48000.0, std::uint64_t seed = 1) {
    auto synth = makeDx7Synth();
    synth->configure(params);
    RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.seed = seed;
    ctx.assetDir = gAssets;
    synth->prepare(ctx);
    return synth;
}

// Renders `frames` samples, splitting blocks at events; blockSize <= 0 uses pseudo-random block sizes.
Audio render(Instrument& synth, std::vector<Event> events, int frames, int blockSize = 256) {
    std::sort(events.begin(), events.end(), [](const Event& a, const Event& b) { return a.at < b.at; });
    Audio a;
    a.l.assign(static_cast<std::size_t>(frames), 0.0f);
    a.r.assign(static_cast<std::size_t>(frames), 0.0f);
    std::size_t next = 0;
    unsigned lcg = 12345;
    for (int pos = 0; pos < frames;) {
        while (next < events.size() && events[next].at <= pos) {
            const auto& e = events[next++];
            if (e.on) synth.noteOn(e.id, e.pitch, e.vel);
            else synth.noteOff(e.id);
        }
        int n = blockSize;
        if (n <= 0) {
            lcg = lcg * 1103515245u + 12345u;
            n = 1 + static_cast<int>((lcg >> 16) % kMaxBlock);
        }
        n = std::min({n, kMaxBlock, frames - pos});
        if (next < events.size()) n = std::min(n, events[next].at - pos);
        synth.process(a.l.data() + pos, a.r.data() + pos, n);
        pos += n;
    }
    return a;
}

double rms(const std::vector<float>& x, int from, int to) {
    double s = 0.0;
    for (int i = from; i < to; ++i) s += static_cast<double>(x[static_cast<std::size_t>(i)]) * x[static_cast<std::size_t>(i)];
    return std::sqrt(s / std::max(1, to - from));
}

bool allFinite(const Audio& a) {
    auto ok = [](const std::vector<float>& v) { return std::all_of(v.begin(), v.end(), [](float x) { return std::isfinite(x); }); };
    return ok(a.l) && ok(a.r);
}

// Frequency of the partial near `guess` (Hz): phase advance of a Hann-windowed DFT evaluated at
// `guess` over successive frames (unambiguous for errors below sr / (2 * hop)).
double measureFrequency(const std::vector<float>& x, double sr, double guess, int start, int frames) {
    const int win = 4096, hop = 2400;
    double sumDelta = 0.0;
    int count = 0;
    double prevPhase = 0.0;
    for (int f = 0; f < frames; ++f) {
        const int t0 = start + f * hop;
        std::complex<double> acc = 0.0;
        for (int n = 0; n < win; ++n) {
            const double w = 0.5 - 0.5 * std::cos(2.0 * 3.14159265358979323846 * n / (win - 1));
            const double t = static_cast<double>(t0 + n);
            acc += w * static_cast<double>(x[static_cast<std::size_t>(t0 + n)]) *
                   std::polar(1.0, -2.0 * 3.14159265358979323846 * guess * t / sr);
        }
        const double phase = std::arg(acc);
        if (f > 0) {
            double d = phase - prevPhase;
            while (d > 3.14159265358979323846) d -= 2.0 * 3.14159265358979323846;
            while (d < -3.14159265358979323846) d += 2.0 * 3.14159265358979323846;
            sumDelta += d;
            ++count;
        }
        prevPhase = phase;
    }
    return guess + (sumDelta / count) / (2.0 * 3.14159265358979323846 * hop / sr);
}

double cents(double f, double ref) { return 1200.0 * std::log2(f / ref); }

// Energy (dB) at the fold-back frequencies of harmonics of f0 above Nyquist, relative to the energy at
// the harmonics themselves (Hann-windowed 16384-point FFT from `start`).
double aliasDb(const std::vector<float>& x, double sr, double f0, int start) {
    const int n = 16384;
    const double pi = 3.14159265358979323846;
    std::vector<std::complex<double>> a(static_cast<std::size_t>(n));
    for (int i = 0; i < n; ++i) a[static_cast<std::size_t>(i)] = x[static_cast<std::size_t>(start + i)] * (0.5 - 0.5 * std::cos(2.0 * pi * i / (n - 1)));
    for (int i = 1, j = 0; i < n; ++i) {  // iterative radix-2 FFT
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[static_cast<std::size_t>(i)], a[static_cast<std::size_t>(j)]);
    }
    for (int len = 2; len <= n; len <<= 1) {
        const std::complex<double> wl = std::polar(1.0, -2.0 * pi / len);
        for (int i = 0; i < n; i += len) {
            std::complex<double> w = 1.0;
            for (int j = 0; j < len / 2; ++j) {
                const auto u = a[static_cast<std::size_t>(i + j)], t = a[static_cast<std::size_t>(i + j + len / 2)] * w;
                a[static_cast<std::size_t>(i + j)] = u + t;
                a[static_cast<std::size_t>(i + j + len / 2)] = u - t;
                w *= wl;
            }
        }
    }
    std::vector<char> used(static_cast<std::size_t>(n / 2), 0);
    auto band = [&](double f, double& acc) {
        const int c = static_cast<int>(std::lround(f * n / sr));
        for (int k = std::max(1, c - 4); k <= std::min(n / 2 - 1, c + 4); ++k) {
            if (!used[static_cast<std::size_t>(k)]) {
                used[static_cast<std::size_t>(k)] = 1;
                acc += std::norm(a[static_cast<std::size_t>(k)]);
            }
        }
    };
    double harm = 0.0, alias = 0.0;
    for (int k = 1; k * f0 < 0.48 * sr; ++k) band(k * f0, harm);
    for (int k = 1; k * f0 < 8.0 * sr; ++k) {
        if (k * f0 < 0.5 * sr) continue;
        double fa = std::fmod(k * f0, sr);
        if (fa > 0.5 * sr) fa = sr - fa;
        const bool nearHarmonic = std::fabs(fa / f0 - std::round(fa / f0)) * f0 < 40.0;
        if (!nearHarmonic && fa < 0.48 * sr) band(fa, alias);
    }
    return 10.0 * std::log10(alias / harm + 1e-30);
}

bool throwsConfig(const std::function<void()>& fn, std::string* message = nullptr) {
    try {
        fn();
    } catch (const ConfigError& e) {
        if (message) *message = e.what();
        return true;
    } catch (...) {
        return false;
    }
    return false;
}

void testBanks() {
    const auto banks = dx7::loadBanks(gAssets);
    check(banks.size() == 8, "8 ROM banks load (checksums verified): got " + std::to_string(banks.size()));
    const auto list = listDx7Voices(gAssets);
    check(list.size() == 256, "256 voices listed: got " + std::to_string(list.size()));

    std::printf("---- DX7 voice list (bank:index name; index is 0-based) ----\n");
    for (std::size_t i = 0; i < list.size(); ++i) {
        std::printf("%s:%-2d %-10s%s", list[i].bank.c_str(), list[i].index, list[i].name.c_str(), (i % 4 == 3) ? "\n" : " | ");
    }
    std::printf("-------------------------------------------------------------\n");

    auto nameAt = [&](const std::string& bank, int index) {
        for (const auto& v : list) {
            if (v.bank == bank && v.index == index) return v.name;
        }
        return std::string("<missing>");
    };
    check(nameAt("rom1a", 0) == "BRASS 1", "rom1a:0 is BRASS 1");
    check(nameAt("rom1a", 10) == "E.PIANO 1", "rom1a:10 is E.PIANO 1");
    check(nameAt("rom1a", 14) == "BASS 1", "rom1a:14 is BASS 1");
    check(nameAt("rom1a", 3) == "STRINGS 1", "rom1a:3 is STRINGS 1");
    check(nameAt("rom1a", 21) == "MARIMBA", "rom1a:21 is MARIMBA");
    check(nameAt("rom1a", 25) == "TUB BELLS", "rom1a:25 is TUB BELLS");
    check(nameAt("rom2b", 0) == "SYN-LEAD 2", "rom2b:0 is SYN-LEAD 2");
    check(nameAt("rom4b", 31) == "EXPLOSION", "rom4b:31 is EXPLOSION");

    // Resolution forms.
    auto resolved = [&](const std::string& spec) {
        const auto v = dx7::resolveVoice(banks, spec);
        return v.bank + ":" + std::to_string(v.index) + " " + v.name;
    };
    check(resolved("rom1a:10") == "rom1a:10 E.PIANO 1", "\"rom1a:10\" -> rom1a:10 E.PIANO 1");
    check(resolved("  e.piano 1 ") == "rom1a:10 E.PIANO 1", "bare name, case/whitespace-insensitive, first bank wins");
    check(resolved("rom3a:E.PIANO 1") == "rom3a:7 E.PIANO 1", "\"rom3a:E.PIANO 1\" -> rom3a:7");
    check(resolved("brass   1") == "rom1a:0 BRASS 1", "internal whitespace collapsed");
    check(resolved("brass1") == "rom1a:0 BRASS 1", "whitespace-free fallback");
    check(resolved("ROM1A:Tub Bells") == "rom1a:25 TUB BELLS", "bank name is case-insensitive");

    // Every voice recommended in kDx7VoiceParamHelp must resolve.
    bool allFound = true;
    for (const char* name : {"E.PIANO 1", "BASS 1", "SYN-BASS 1", "BRASS 1", "SYNBRASS 1", "STRINGS 1", "MARIMBA",
                             "TUB BELLS", "VIBE 1", "HARP 1", "CLAV 1", "FLUTE 1", "SYN-LEAD 1", "E.ORGAN 1"}) {
        try {
            dx7::resolveVoice(banks, name);
        } catch (const ConfigError&) {
            allFound = false;
            std::printf("      missing recommended voice %s\n", name);
        }
    }
    check(allFound && std::string(kDx7VoiceParamHelp).find("E.PIANO 1") != std::string::npos,
          "all voices recommended in kDx7VoiceParamHelp exist");

    // Framing / checksum errors.
    std::ifstream in(std::filesystem::path(gAssets) / "dx7" / "rom1a.syx", std::ios::binary);
    std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    check(bytes.size() == dx7::kBankSysexBytes, "rom1a.syx is 4104 bytes");
    check(dx7::checksum(std::span<const std::uint8_t>(bytes).subspan(6, 4096)) == bytes[4102], "checksum() matches file");
    auto corrupt = bytes;
    corrupt[100] ^= 0x01;
    check(throwsConfig([&] { dx7::parseBank(corrupt, "x", "corrupt"); }), "corrupted data -> checksum ConfigError");
    auto truncated = bytes;
    truncated.pop_back();
    check(throwsConfig([&] { dx7::parseBank(truncated, "x", "short"); }), "wrong size -> ConfigError");
}

void testConfigErrors() {
    std::string msg;
    const bool badName = throwsConfig([] { make({{"voice", "E.PAINO 1"}}); }, &msg);
    check(badName && msg.find("E.PIANO 1") != std::string::npos,
          "unknown voice \"E.PAINO 1\" -> ConfigError suggesting E.PIANO 1: " + msg);
    const bool badBank = throwsConfig([] { make({{"voice", "rom9z:3"}}); }, &msg);
    check(badBank && msg.find("rom9z") != std::string::npos && msg.find("rom4b") != std::string::npos,
          "unknown bank -> ConfigError listing banks: " + msg);
    check(throwsConfig([] { makeDx7Synth()->configure({{"voice", "rom1a:32"}}); }), "index 32 rejected by configure()");
    check(throwsConfig([] { makeDx7Synth()->configure({{"voice", 10}}); }), "non-string voice rejected");
    check(throwsConfig([] { makeDx7Synth()->configure({{"voice", "  "}}); }), "empty voice rejected");
    check(throwsConfig([] { makeDx7Synth()->configure({{"cutoff", 1000}}); }), "unknown param rejected");
    check(throwsConfig([] { makeDx7Synth()->configure({{"polyphony", 2.5}}); }), "fractional polyphony rejected");
    check(throwsConfig([] { makeDx7Synth()->configure({{"detune", 31}}); }), "out-of-range detune rejected");
    check(throwsConfig([] { makeDx7Synth()->configure({{"oversample", "8x"}}); }), "bad oversample choice rejected");

    auto synth = make({{"voice", "E.PIANO 1"}});
    check(synth->setParam("pitchbend", 2.0f) && synth->setParam("modwheel", 0.5f) && synth->setParam("brightness", -0.5f) &&
              synth->setParam("level", -3.0f) && synth->setParam("width", 0.2f),
          "continuous params accept automation");
    check(!synth->setParam("detune", 5.0f) && !synth->setParam("polyphony", 4.0f) && !synth->setParam("nope", 1.0f),
          "static/unknown params refuse automation");
    std::printf("params:");
    for (const auto& s : synth->paramSpecs()) std::printf(" %s", s.name.c_str());
    std::printf("\n");
}

void testEpiano() {
    const int sr = 48000;
    auto synth = make({{"voice", "E.PIANO 1"}});
    check(synth->idle(), "idle before any note");
    const auto a = render(*synth, {{0, true, 1, 60, 100 / 127.0f}}, 2 * sr);
    check(allFinite(a), "E.PIANO 1 middle C: all samples finite");
    const double early = rms(a.l, 0, sr / 4), late = rms(a.l, 7 * sr / 4, 2 * sr);
    check(early > 0.01, "E.PIANO 1 is non-silent (first 250 ms RMS " + std::to_string(early) + ")");
    check(late < early * 0.5, "E.PIANO 1 decays while held (RMS " + std::to_string(early) + " -> " + std::to_string(late) + ")");
    float peak = 0.0f;
    for (float x : a.l) peak = std::max(peak, std::fabs(x));
    double mom = 0.0;
    for (int i = 0; i + 2400 <= sr; i += 240) mom = std::max(mom, rms(a.l, i, i + 2400));
    const double momDb = 20.0 * std::log10(mom);
    check(momDb > -26.0 && momDb < -21.0 && peak < 0.5f,
          "autolevel: one E.PIANO 1 note ~-23.5 dBFS short-term RMS (" + std::to_string(momDb) + " dB), peak " + std::to_string(peak));
    check(a.l == a.r, "detune 0 at centre pan: L == R (mono)");
    check(!synth->idle(), "not idle while the key is held");

    synth->noteOff(1);
    int renderedAfterOff = 0;
    std::vector<float> l(256), r(256);
    while (!synth->idle() && renderedAfterOff < 10 * sr) {
        synth->process(l.data(), r.data(), 256);
        renderedAfterOff += 256;
    }
    check(synth->idle(), "noteOff leads to idle() after " + std::to_string(renderedAfterOff / double(sr)) + " s");
}

void testPitch() {
    for (const double sr : {48000.0, 44100.0, 96000.0}) {
        for (const char* os : {"2x", "1x", "4x"}) {
            const int frames = static_cast<int>(sr * 1.2);
            const auto a = render(*make({{"voice", "SYN-LEAD 2"}, {"oversample", os}}, sr), {{0, true, 1, 69, 0.8f}}, frames);
            const double f = measureFrequency(a.l, sr, 440.0, static_cast<int>(sr * 0.5), 6);
            const double c = cents(f, 440.0);
            char what[160];
            std::snprintf(what, sizeof what, "SYN-LEAD 2 A4 at %.0f Hz / %s: %.3f Hz (%+.2f ct), within +-3 ct", sr, os, f, c);
            check(std::fabs(c) < 3.0 && allFinite(a), what);
        }
    }
    const double sr = 48000.0;
    const double c4 = 440.0 * std::pow(2.0, -9.0 / 12.0);
    {
        const auto a = render(*make({{"voice", "SYN-LEAD 2"}}), {{0, true, 1, 60, 0.8f}}, 72000);
        const double f = measureFrequency(a.l, sr, c4, 24000, 6);
        char what[160];
        std::snprintf(what, sizeof what, "SYN-LEAD 2 middle C: %.3f Hz (%+.2f ct vs 261.626)", f, cents(f, c4));
        check(std::fabs(cents(f, c4)) < 3.0, what);
    }
    {
        const auto a = render(*make({{"voice", "SYN-LEAD 2"}, {"transpose", -12}, {"pitchbend", 2.0}}), {{0, true, 1, 81, 0.8f}}, 72000);
        const double expect = 440.0 * std::pow(2.0, 2.0 / 12.0);
        const double f = measureFrequency(a.l, sr, expect, 24000, 6);
        char what[160];
        std::snprintf(what, sizeof what, "transpose -12 + pitchbend +2 st on A5: %.3f Hz (%+.2f ct vs %.3f)", f, cents(f, expect), expect);
        check(std::fabs(cents(f, expect)) < 3.0, what);
    }
    {
        // Automated bend: start at 0, jump the target to -1 st at 0.3 s; measure after the smoother settles.
        auto synth = make({{"voice", "SYN-LEAD 2"}});
        std::vector<float> l(72000), r(72000);
        synth->noteOn(1, 69, 0.8f);
        for (int pos = 0; pos < 72000; pos += 32) {
            if (pos == 14400) check(synth->setParam("pitchbend", -1.0f), "setParam pitchbend -1");
            synth->process(l.data() + pos, r.data() + pos, 32);
        }
        const double expect = 440.0 * std::pow(2.0, -1.0 / 12.0);
        const double f = measureFrequency(l, sr, expect, 36000, 6);
        char what[160];
        std::snprintf(what, sizeof what, "automated pitchbend -1 st: %.3f Hz (%+.2f ct vs %.3f)", f, cents(f, expect), expect);
        check(std::fabs(cents(f, expect)) < 3.0 && allFinite({l, r}), what);
    }
    {
        const auto a = render(*make({{"voice", "SYN-LEAD 2"}, {"detune", 10}, {"width", 1.0}}), {{0, true, 1, 69, 0.8f}}, 72000);
        const double fl = measureFrequency(a.l, sr, 440.0, 24000, 6), fr = measureFrequency(a.r, sr, 440.0, 24000, 6);
        char what[160];
        std::snprintf(what, sizeof what, "detune 10 ct, width 1: L %+.2f ct, R %+.2f ct (expect -5 / +5)", cents(fl, 440.0), cents(fr, 440.0));
        check(std::fabs(cents(fl, 440.0) + 5.0) < 1.5 && std::fabs(cents(fr, 440.0) - 5.0) < 1.5, what);
    }
}

void testStereoAndDeterminism() {
    const int sr = 48000;
    const std::vector<Event> chord = {{0, true, 1, 60, 0.8f}, {0, true, 2, 64, 0.7f}, {100, true, 3, 67, 0.9f},
                                      {30000, false, 1, 0, 0}, {30000, false, 2, 0, 0}, {40000, false, 3, 0, 0},
                                      {50000, true, 4, 72, 1.0f}, {80000, false, 4, 0, 0}};
    const json p = {{"voice", "E.PIANO 1"}, {"detune", 8}, {"width", 0.8}, {"modwheel", 0.2}};
    const auto a = render(*make(p), chord, 2 * sr);
    const auto b = render(*make(p), chord, 2 * sr);
    check(a.l == b.l && a.r == b.r, "determinism: two renders are bit-identical");
    const auto c = render(*make(p), chord, 2 * sr, 0);
    check(a.l == c.l && a.r == c.r, "block-size invariance: random block sizes give bit-identical output");
    double diff = 0.0;
    for (std::size_t i = 0; i < a.l.size(); ++i) diff += std::fabs(a.l[i] - a.r[i]);
    check(diff / static_cast<double>(a.l.size()) > 1e-4 && allFinite(a),
          "detune > 0 creates an L/R difference (mean |L-R| " + std::to_string(diff / a.l.size()) + ")");
    const auto d = render(*make(p, 48000.0, 7), chord, 2 * sr);
    check(d.l != a.l, "a different seed changes the doubled voice's free-running phases");

    // Sample-accurate starts: the same note 1000 samples later is the same signal shifted.
    const json lead = {{"voice", "SYN-LEAD 2"}};
    const auto e0 = render(*make(lead), {{0, true, 1, 57, 0.8f}}, 20000);
    const auto e1 = render(*make(lead), {{1000, true, 1, 57, 0.8f}}, 21000);
    bool shifted = true;
    for (int i = 0; i < 20000; ++i) shifted = shifted && e0.l[static_cast<std::size_t>(i)] == e1.l[static_cast<std::size_t>(i + 1000)];
    check(shifted, "note starts are sample-accurate (1000-sample offset reproduces the signal exactly)");

    // 2x oversampling must not delay the signal noticeably (IIR half-band decimator, ~2 samples).
    const auto o1 = render(*make({{"voice", "SYN-LEAD 2"}, {"oversample", "1x"}}), {{0, true, 1, 57, 0.8f}}, 24000);
    const auto o2 = render(*make({{"voice", "SYN-LEAD 2"}, {"oversample", "2x"}}), {{0, true, 1, 57, 0.8f}}, 24000);
    int bestLag = 0;
    double bestCorr = -1.0;
    for (int lag = -30; lag <= 30; ++lag) {
        double xy = 0.0, xx = 0.0, yy = 0.0;
        for (int i = 2000; i < 20000; ++i) {
            const double x = o1.l[static_cast<std::size_t>(i)], y = o2.l[static_cast<std::size_t>(i + lag)];
            xy += x * y;
            xx += x * x;
            yy += y * y;
        }
        const double corr = xy / std::sqrt(xx * yy);
        if (corr > bestCorr) {
            bestCorr = corr;
            bestLag = lag;
        }
    }
    check(std::abs(bestLag) <= 3 && bestCorr > 0.9,
          "2x oversampling stays time-aligned with 1x (lag " + std::to_string(bestLag) + " samples, corr " +
              std::to_string(bestCorr) + ")");

    // Oversampling removes FM aliasing: E.PIANO 1 at C7, full velocity.
    const double c7 = 440.0 * std::pow(2.0, 27.0 / 12.0);
    double aliasByOs[3] = {};
    const char* osNames[3] = {"1x", "2x", "4x"};
    for (int i = 0; i < 3; ++i) {
        const auto x = render(*make({{"voice", "E.PIANO 1"}, {"oversample", osNames[i]}}), {{0, true, 1, 96, 1.0f}}, 24000);
        aliasByOs[i] = aliasDb(x.l, sr, c7, 4800);
    }
    char aliasWhat[200];
    std::snprintf(aliasWhat, sizeof aliasWhat, "oversampling suppresses aliasing (E.PIANO 1 C7 alias energy: 1x %.1f dB, 2x %.1f dB, 4x %.1f dB)",
                  aliasByOs[0], aliasByOs[1], aliasByOs[2]);
    check(aliasByOs[1] < aliasByOs[0] - 30.0 && aliasByOs[2] < -80.0, aliasWhat);

    // Two instances at different internal rates interleaved must not disturb each other (MSFA globals).
    auto x1 = make({{"voice", "BRASS 1"}, {"oversample", "2x"}});
    auto y1 = make({{"voice", "TUB BELLS"}, {"oversample", "1x"}}, 44100.0);
    auto x2 = make({{"voice", "BRASS 1"}, {"oversample", "2x"}});
    std::vector<float> xl(sr), xr(sr), yl(sr), yr(sr), zl(sr), zr(sr);
    x1->noteOn(1, 60, 0.8f);
    y1->noteOn(1, 72, 0.8f);
    x2->noteOn(1, 60, 0.8f);
    for (int pos = 0; pos < sr; pos += 128) {
        x1->process(xl.data() + pos, xr.data() + pos, 128);
        y1->process(yl.data() + pos, yr.data() + pos, 128);
    }
    for (int pos = 0; pos < sr; pos += 128) x2->process(zl.data() + pos, zr.data() + pos, 128);
    check(xl == zl && xr == zr, "instances with different internal rates are independent (shared MSFA tables guarded)");
}

void testVoicesAndControls() {
    const int sr = 48000;
    // Voice stealing with polyphony 2: 5 overlapping notes, all finite, ends idle.
    auto synth = make({{"voice", "STRINGS 1"}, {"polyphony", 2}});
    std::vector<Event> ev;
    for (int i = 0; i < 5; ++i) {
        ev.push_back({i * 4000, true, i, 60 + i * 3, 0.8f});
        ev.push_back({30000 + i * 1000, false, i, 0, 0});
    }
    const auto a = render(*synth, ev, 3 * sr);
    check(allFinite(a) && synth->idle(), "polyphony 2 with 5 overlapping notes: finite and idle at the end");
    // Notes 2..4 steal a sounding voice: the largest sample step around each steal must not exceed the
    // signal's own recent steps by much (a hard cut would jump by the victim's full amplitude).
    auto maxStep = [&](int from, int to) {
        float m = 0.0f;
        for (int i = from; i < to; ++i) m = std::max(m, std::fabs(a.l[static_cast<std::size_t>(i)] - a.l[static_cast<std::size_t>(i - 1)]));
        return m;
    };
    bool smooth = true;
    std::string steps;
    for (const int t : {8000, 12000, 16000}) {
        const float around = maxStep(t, t + 400), before = maxStep(t - 2400, t);
        smooth = smooth && around <= 1.5f * before + 0.005f;
        steps += " " + std::to_string(around) + "/" + std::to_string(before);
    }
    check(smooth, "voice stealing fades the victim (max step at steal / before:" + steps + ")");

    // velsens 0: every velocity sounds like 100.
    const auto soft = render(*make({{"voice", "E.PIANO 1"}, {"velsens", 0.0}}), {{0, true, 1, 60, 20 / 127.0f}}, sr / 2);
    const auto hard = render(*make({{"voice", "E.PIANO 1"}, {"velsens", 0.0}}), {{0, true, 1, 60, 1.0f}}, sr / 2);
    const auto softAuth = render(*make({{"voice", "E.PIANO 1"}}), {{0, true, 1, 60, 20 / 127.0f}}, sr / 2);
    const auto hardAuth = render(*make({{"voice", "E.PIANO 1"}}), {{0, true, 1, 60, 1.0f}}, sr / 2);
    check(soft.l == hard.l, "velsens 0 makes all velocities identical");

    // Brightness -1 removes high-frequency energy (first-difference energy as an HF proxy).
    auto hf = [](const std::vector<float>& x) {
        double s = 0.0;
        for (std::size_t i = 1; i < x.size(); ++i) s += (x[i] - x[i - 1]) * (x[i] - x[i - 1]);
        return s;
    };
    check(rms(softAuth.l, 0, sr / 2) < 0.7 * rms(hardAuth.l, 0, sr / 2) && hf(softAuth.l) < 0.2 * hf(hardAuth.l),
          "velsens 1 keeps the DX7 velocity response (velocity 20 vs 127: quieter and much less bright)");
    const auto bright = render(*make({{"voice", "E.PIANO 1"}}), {{0, true, 1, 72, 1.0f}}, sr / 2);
    const auto dark = render(*make({{"voice", "E.PIANO 1"}, {"brightness", -1.0}}), {{0, true, 1, 72, 1.0f}}, sr / 2);
    check(hf(dark.l) < 0.5 * hf(bright.l) && allFinite(dark),
          "brightness -1 tames the top end (HF energy ratio " + std::to_string(hf(dark.l) / hf(bright.l)) + ")");

    // Mod wheel brings in the LFO vibrato (E.PIANO 1 has PMS 3).
    const auto still = render(*make({{"voice", "E.PIANO 1"}}), {{0, true, 1, 60, 0.8f}}, sr);
    const auto vib = render(*make({{"voice", "E.PIANO 1"}, {"modwheel", 0.5}}), {{0, true, 1, 60, 0.8f}}, sr);
    check(still.l != vib.l && allFinite(vib), "modwheel changes the sound (LFO pitch/amp mod via controllers)");

    // Pan hard left silences the right channel; level -6 dB halves amplitude.
    const auto left = render(*make({{"voice", "E.PIANO 1"}, {"pan", -1.0}}), {{0, true, 1, 60, 0.8f}}, sr / 4);
    check(rms(left.r, 0, sr / 4) < 1e-6 && rms(left.l, 0, sr / 4) > 0.01, "pan -1 is hard left");
    const auto quiet = render(*make({{"voice", "E.PIANO 1"}, {"level", -6.0206}}), {{0, true, 1, 60, 0.8f}}, sr / 4);
    const auto loud = render(*make({{"voice", "E.PIANO 1"}}), {{0, true, 1, 60, 0.8f}}, sr / 4);
    check(std::fabs(rms(quiet.l, 0, sr / 4) / rms(loud.l, 0, sr / 4) - 0.5) < 0.01, "level -6 dB halves the amplitude");

    // A chord change that steals every voice at once (polyphony 8, 8-note chords of a long-release pad)
    // must fade all 8 victims: each needs its own spare fade slot.
    {
        std::vector<Event> pad;
        for (int c = 0; c < 4; ++c) {
            for (int k = 0; k < 8; ++k) {
                pad.push_back({c * sr / 2, true, c * 8 + k, 48 + k * 3 + c, 0.8f});
                pad.push_back({c * sr / 2 + sr / 2 - 1, false, c * 8 + k, 0, 0});
            }
        }
        const auto p8 = render(*make({{"voice", "STRINGS 1"}, {"polyphony", 8}, {"oversample", "1x"}}), pad, 2 * sr);
        auto maxD2 = [&](int from, int to) {  // second difference: highlights discontinuities
            double m = 0.0;
            for (int i = from; i < to; ++i) {
                const auto u = static_cast<std::size_t>(i);
                m = std::max(m, static_cast<double>(std::fabs(p8.l[u] - 2.0f * p8.l[u - 1] + p8.l[u - 2])));
            }
            return m;
        };
        bool ok = true;
        std::string d2s;
        for (int c = 1; c < 4; ++c) {
            const int t = c * sr / 2;
            const double around = maxD2(t - 5, t + 400), before = maxD2(t - 3000, t - 600);
            ok = ok && around <= 1.5 * before + 0.005;
            d2s += " " + std::to_string(around) + "/" + std::to_string(before);
        }
        check(ok && allFinite(p8), "stealing all 8 voices at once is click-free (2nd diff at change / before:" + d2s + ")");
    }

    // DC: FM feedback stacks leave large offsets (SYNBRASS 1 raw DC ~ 90 % of its AC RMS). The output is
    // AC-coupled like the DX7's analog stage, so a held note (and an 8-note chord of them) has ~no DC.
    {
        std::vector<Event> chord8;
        for (int k = 0; k < 8; ++k) chord8.push_back({0, true, k, 48 + 3 * k, 0.8f});
        for (const char* v : {"SYNBRASS 1", "PRC SYNTH1", "PERC BRASS"}) {
            const auto x = render(*make({{"voice", v}}), chord8, 2 * sr);
            double mean = 0.0;
            for (int i = sr; i < 2 * sr; ++i) mean += x.l[static_cast<std::size_t>(i)];
            mean /= sr;
            const double ac = rms(x.l, sr, 2 * sr);
            char what[160];
            std::snprintf(what, sizeof what, "%s 8-note chord has no DC offset (mean %.5f, RMS %.4f)", v, mean, ac);
            check(std::fabs(mean) < 0.02 * ac, what);  // raw MSFA output: mean ~ 0.9 x RMS for SYNBRASS 1
        }
    }

    // Autolevel also caps the single-note peak (high-crest percussive patches), and the idle flag waits for
    // the DC blocker's tail so the host never truncates audible output.
    {
        for (const char* v : {"CLAV 2", "HARPSICH 3", "E.PIANO 1"}) {
            const auto x = render(*make({{"voice", v}}), {{0, true, 1, 60, 100 / 127.0f}}, sr);
            float peak = 0.0f;
            for (float s : x.l) peak = std::max(peak, std::fabs(s));
            check(20.0 * std::log10(peak) < -11.0, std::string("autolevel: ") + v + " single-note peak " +
                                                        std::to_string(20.0 * std::log10(peak)) + " dBFS <= ~-12");
        }
        auto s = make({{"voice", "SYNBRASS 1"}});
        std::vector<float> l(256), r(256);
        s->noteOn(1, 60, 0.8f);
        for (int i = 0; i < 100; ++i) s->process(l.data(), r.data(), 256);
        s->noteOff(1);
        int n = 0;
        while (!s->idle() && n < 20 * sr) {
            s->process(l.data(), r.data(), 256);
            n += 256;
        }
        float after = 0.0f;
        for (int i = 0; i < 40; ++i) {
            s->process(l.data(), r.data(), 256);
            for (int k = 0; k < 256; ++k) after = std::max({after, std::fabs(l[static_cast<std::size_t>(k)]), std::fabs(r[static_cast<std::size_t>(k)])});
        }
        check(s->idle() && after < 1e-5f, "after idle() the output stays silent (max " + std::to_string(after) + ")");
    }

    // Release safety limit: ST.HELENS has a non-zero release level and never decays; after 30 s it must be
    // faded out (not cut) and the instrument must go idle.
    {
        const int sr2 = 44100;
        auto s = make({{"voice", "rom2b:30"}, {"oversample", "1x"}}, sr2);
        const auto x = render(*s, {{0, true, 1, 60, 0.8f}, {sr2 / 2, false, 1, 0, 0}}, 32 * sr2);
        double level = 0.0, step = 0.0;
        for (int i = 29 * sr2; i < 30 * sr2; ++i) level = std::max(level, static_cast<double>(std::fabs(x.l[static_cast<std::size_t>(i)])));
        for (int i = 30 * sr2; i < 31 * sr2; ++i) {
            const auto u = static_cast<std::size_t>(i);
            step = std::max(step, static_cast<double>(std::fabs(x.l[u] - 2.0f * x.l[u - 1] + x.l[u - 2])));
        }
        const double end = rms(x.l, 31 * sr2, 32 * sr2);
        check(level > 0.01 && end < 1e-5 && step < 0.1 * level && s->idle(),
              "non-decaying release is faded out at the 30 s safety limit (level " + std::to_string(level) +
                  ", max 2nd diff " + std::to_string(step) + ", then " + std::to_string(end) + ")");
    }

    // Every ROM voice renders finite, bounded audio (1x and 2x).
    int bad = 0;
    float worst = 0.0f;
    for (const auto& v : listDx7Voices(gAssets)) {
        auto s = make({{"voice", v.bank + ":" + std::to_string(v.index)}, {"oversample", std::array<const char*, 3>{"1x", "2x", "4x"}[static_cast<std::size_t>(v.index % 3)]}});
        const auto out = render(*s, {{0, true, 1, 48, 1.0f}, {0, true, 2, 72, 0.6f}, {9000, false, 1, 0, 0}, {9000, false, 2, 0, 0}}, 12000);
        for (float x : out.l) worst = std::max(worst, std::fabs(x));
        if (!allFinite(out)) ++bad;
    }
    check(bad == 0 && worst < 4.0f, "all 256 ROM voices render finite audio at 1x/2x/4x (max |x| " + std::to_string(worst) + ")");
}


// ---------------------------------------------------------------------------------------------
// Per-voice DC removal, envelope time scaling, loudness matching

constexpr double kPi = 3.14159265358979323846;

std::string fmt2(double x) {
    char b[32];
    std::snprintf(b, sizeof b, "%.2f", x);
    return b;
}

std::vector<float> mono(const Audio& a) {
    std::vector<float> m(a.l.size());
    for (std::size_t i = 0; i < m.size(); ++i) m[i] = 0.5f * (a.l[i] + a.r[i]);
    return m;
}

// Magnitude of the Hann-windowed DFT of x[from, from + n) at `hz`.
double toneMagnitude(const std::vector<float>& x, double sr, double hz, int from, int n) {
    std::complex<double> acc = 0.0;
    for (int i = 0; i < n; ++i) {
        const double w = 0.5 - 0.5 * std::cos(2.0 * kPi * i / (n - 1));
        acc += w * static_cast<double>(x[static_cast<std::size_t>(from + i)]) * std::polar(1.0, -2.0 * kPi * hz * i / sr);
    }
    return std::abs(acc);
}

// In-place iterative radix-2 FFT (forward, unnormalised).
void fftInPlace(std::vector<std::complex<double>>& a) {
    const int n = static_cast<int>(a.size());
    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[static_cast<std::size_t>(i)], a[static_cast<std::size_t>(j)]);
    }
    for (int len = 2; len <= n; len <<= 1) {
        const std::complex<double> wl = std::polar(1.0, -2.0 * kPi / len);
        for (int i = 0; i < n; i += len) {
            std::complex<double> w = 1.0;
            for (int j = 0; j < len / 2; ++j) {
                const auto u = a[static_cast<std::size_t>(i + j)], t = a[static_cast<std::size_t>(i + j + len / 2)] * w;
                a[static_cast<std::size_t>(i + j)] = u + t;
                a[static_cast<std::size_t>(i + j + len / 2)] = u - t;
                w *= wl;
            }
        }
    }
}

// Energy of x between `lo` and `hi` Hz relative to its total energy, dB: averaged power spectrum of
// Hann-windowed 16384-point frames (half overlap). Hann side lobes fall fast, so strong partials a few
// octaves up do not leak into a low band (a 4th-order low-pass would read their skirts instead).
double bandDb(const std::vector<float>& x, double sr, double lo, double hi) {
    const int n = 16384;
    std::vector<double> power(static_cast<std::size_t>(n / 2), 0.0);
    std::vector<std::complex<double>> a(static_cast<std::size_t>(n));
    for (std::size_t start = 0; start + n <= x.size(); start += n / 2) {
        for (int i = 0; i < n; ++i) a[static_cast<std::size_t>(i)] = x[start + static_cast<std::size_t>(i)] * (0.5 - 0.5 * std::cos(2.0 * kPi * i / (n - 1)));
        fftInPlace(a);
        for (int k = 0; k < n / 2; ++k) power[static_cast<std::size_t>(k)] += std::norm(a[static_cast<std::size_t>(k)]);
    }
    double band = 0.0, all = 0.0;
    for (int k = 1; k < n / 2; ++k) {
        const double f = k * sr / n;
        all += power[static_cast<std::size_t>(k)];
        if (f >= lo && f < hi) band += power[static_cast<std::size_t>(k)];
    }
    return 10.0 * std::log10(band / (all + 1e-30) + 1e-30);
}

double mean(const std::vector<float>& x, int from, int to) {
    double s = 0.0;
    for (int i = from; i < to; ++i) s += x[static_cast<std::size_t>(i)];
    return s / std::max(1, to - from);
}

// One note of `voice` rendered directly with MSFA: no voice high-pass, no output DC blocker, no oversampling,
// raw patch level. Uses the MSFA tables as the last instrument left them (render a 1x, 48 kHz one first).
std::vector<float> rawNote(const std::string& voice, int pitch, int velocity, int frames, int offAt = -1) {
    const auto patch = dx7::unpackVoice(dx7::resolveVoice(dx7::loadBanks(gAssets), voice).data);
    FmCore core;
    Controllers ctrl;
    ctrl.core = &core;
    std::fill(std::begin(ctrl.values_), std::end(ctrl.values_), 0);
    ctrl.values_[kControllerPitch] = 0x2000;
    ctrl.values_[kControllerPitchRange] = 2;
    ctrl.masterTune = ctrl.modwheel_cc = ctrl.foot_cc = ctrl.breath_cc = ctrl.aftertouch_cc = 0;
    ctrl.refresh();
    Lfo lfo;
    lfo.reset(patch.data() + 137);
    Dx7Note note;
    note.init(patch.data(), std::clamp(pitch + static_cast<int>(patch[144]) - 24, 0, 127), velocity);
    if (patch[136] != 0) note.oscSync();
    else note.oscFreeRun(0);
    lfo.keydown();
    std::vector<float> out(static_cast<std::size_t>(frames));
    for (int pos = 0; pos < frames; pos += N) {
        if (pos == offAt) note.keyup();
        std::int32_t buf[N] = {};
        const std::int32_t value = lfo.getsample();
        note.compute(buf, value, lfo.getdelay(), &ctrl);
        for (int j = 0; j < N && pos + j < frames; ++j)
            out[static_cast<std::size_t>(pos + j)] = static_cast<float>(std::clamp(buf[j] >> 4, -(1 << 24), (1 << 24) - 1)) / 16777216.0f;
    }
    return out;
}

void testVoiceHighPass() {
    const int sr = 48000;
    // (a) Transparent at the note's partials, while the voice's own DC is gone: instrument at 1x without autolevel
    // (centre pan = 0.7071 x) against the same note rendered raw by MSFA. BASS 1 / SYNBRASS 1 / MARIMBA play from
    // 0.5-ratio carriers, an octave below the key (the lowest partials a voice can have).
    struct Case {
        const char* voice;
        int pitch;
        double f0;
        int harmonics;
    };
    for (const Case c : {Case{"BASS 1", 40, 41.2034, 5}, Case{"SYNBRASS 1", 48, 65.4064, 5}, Case{"E.PIANO 1", 60, 261.6256, 6},
                         Case{"MARIMBA", 72, 261.6256, 4}}) {
        auto inst = make({{"voice", c.voice}, {"oversample", "1x"}, {"autolevel", "off"}});
        const auto out = render(*inst, {{0, true, 1, c.pitch, 100 / 127.0f}}, 2 * sr);
        const auto raw = rawNote(c.voice, c.pitch, 100, 2 * sr);
        double worst = 0.0;
        for (int k = 1; k <= c.harmonics; ++k) {
            const double a = toneMagnitude(out.l, sr, k * c.f0, sr / 4, sr), b = 0.70710678 * toneMagnitude(raw, sr, k * c.f0, sr / 4, sr);
            worst = std::max(worst, std::fabs(20.0 * std::log10(a / b)));
        }
        const double dcRaw = std::fabs(mean(raw, sr / 4, 5 * sr / 4)) / rms(raw, sr / 4, 5 * sr / 4);
        const double dcOut = std::fabs(mean(out.l, sr / 4, 5 * sr / 4)) / rms(out.l, sr / 4, 5 * sr / 4);
        char what[240];
        std::snprintf(what, sizeof what, "%s (%.1f Hz): partials 1-%d match raw MSFA within %.3f dB (<= 0.3), DC/RMS %.3f -> %.4f",
                      c.voice, c.f0, c.harmonics, worst, dcRaw, dcOut);
        check(worst <= 0.3 && dcOut < 0.02 && allFinite(out), what);
    }

    // (b) Note-on/off thumps. Every note start and end steps the voice's DC; before the per-voice high-pass that
    // passed the 10 Hz output blocker as a low thump. Energy 5-40 Hz of 1/8 comping before -> after: E.PIANO 1
    // -24.9 -> -78.5 dB, E.ORGAN 1 -27.2 -> -50.8, VOICE 1 -32.3 -> -70.9, SYNBRASS 1 -18.0 -> -57.8, TUB BELLS
    // -52.9 -> -75.7; MARIMBA 1/16 arp 5-60 Hz -34.2 -> -74.1 dB. A held chord of the same notes is the reference
    // for what is part of the sound (A3-A4 chord; E.ORGAN 1 and SYNBRASS 1 sound a real sub-octave partial at
    // 110 Hz, whose instant key-on/off still splatters a little below it: the organ's key click).
    const int chord[4] = {57, 60, 64, 69};
    std::vector<Event> comp, held;
    int id = 0;
    for (int k = 0; k < 24; ++k) {
        for (const int p : chord) {
            comp.push_back({k * sr * 3 / 10, true, id, p, 0.75f});
            comp.push_back({k * sr * 3 / 10 + sr / 4, false, id, 0, 0});
            ++id;
        }
    }
    for (int n = 0; n < 4; ++n) {
        held.push_back({0, true, 100 + n, chord[n], 0.75f});
        held.push_back({36 * sr / 5, false, 100 + n, 0, 0});
    }
    for (const char* v : {"E.PIANO 1", "E.ORGAN 1", "VOICE 1", "SYNBRASS 1", "TUB BELLS"}) {
        const auto seq = mono(render(*make({{"voice", v}}), comp, 8 * sr)), ref = mono(render(*make({{"voice", v}}), held, 8 * sr));
        const double seq40 = bandDb(seq, sr, 5.0, 40.0), ref40 = bandDb(ref, sr, 5.0, 40.0);
        char what[200];
        const std::string name = v;
        const double limit = name == "E.PIANO 1" ? -70.0 : name == "E.ORGAN 1" ? -45.0 : name == "SYNBRASS 1" ? -50.0 : -60.0;
        std::snprintf(what, sizeof what, "%s 1/8 comping: energy 5-40 Hz %.1f dB re total (<= %.0f; held chord %.1f dB)", v, seq40,
                      limit, ref40);
        check(seq40 <= limit, what);
    }
    std::vector<Event> arp;
    const int pattern[8] = {60, 64, 67, 72, 76, 72, 67, 64};
    for (int k = 0; k < 64; ++k) {
        arp.push_back({k * sr * 15 / 100, true, k, pattern[k % 8], 0.72f});
        arp.push_back({k * sr * 15 / 100 + sr / 10, false, k, 0, 0});
    }
    const auto marimba = mono(render(*make({{"voice", "MARIMBA"}, {"detune", 4}, {"width", 0.6}, {"transpose", 12}}), arp, 10 * sr));
    const double below60 = bandDb(marimba, sr, 5.0, 60.0);
    check(below60 <= -60.0, "MARIMBA 1/16 arp (C4-C5 sounding): energy 5-60 Hz " + fmt2(below60) + " dB re total (<= -60)");

    // (c) A downward bend takes the voice high-passes along: a C4 bent down two octaves keeps its fundamental.
    {
        auto bent = make({{"voice", "SYN-BASS 1"}, {"oversample", "1x"}, {"pitchbend", -24.0}});
        auto plain = make({{"voice", "SYN-BASS 1"}, {"oversample", "1x"}});
        const auto a = render(*bent, {{0, true, 1, 60, 0.8f}}, 2 * sr), b = render(*plain, {{0, true, 1, 36, 0.8f}}, 2 * sr);
        const double f0 = 65.4064;  // C2
        auto db = [&](const Audio& x, double hz) { return 20.0 * std::log10(toneMagnitude(x.l, sr, hz, sr / 2, sr)); };
        const double loss = (db(a, f0) - db(a, 2 * f0)) - (db(b, f0) - db(b, 2 * f0));
        check(std::fabs(loss) < 1.0, "C4 bent -24 st keeps its fundamental like a played C2 (fundamental re 2nd harmonic differs by " +
                                         std::to_string(loss) + " dB)");
    }
}

// Largest level change (dB) the voice high-pass applies to any significant partial of a held note: the
// instrument (1x, autolevel off, centre: x 0.7071) against the raw MSFA note through the same 10 Hz output DC
// blocker (2nd-order Butterworth, which predates the voice high-pass). Hann-windowed spectrum of 43..725 ms;
// partials = spectral peaks within 30 dB of the strongest, at or above 0.1 x key and 30 Hz. (On partials
// that decay fast the filters' group delay moves some energy into the window: a few tenths of a dB.)
double worstPartialChange(const std::string& voice, int pitch, double& atHz) {
    const int n = 32768, skip = 2048, frames = skip + n;
    auto inst = make({{"voice", voice}, {"oversample", "1x"}, {"autolevel", "off"}});
    const auto out = render(*inst, {{0, true, 1, pitch, 100 / 127.0f}}, frames);
    auto raw = rawNote(voice, pitch, 100, frames);
    {
        const double w = 2.0 * kPi * 10.0 / 48000.0, alpha = std::sin(w) / (2.0 * 0.70710678118654752), cw = std::cos(w), a0 = 1.0 + alpha;
        analysis::Biquad64 dc;
        dc.b0 = dc.b2 = (1.0 + cw) * 0.5 / a0;
        dc.b1 = -(1.0 + cw) / a0;
        dc.a1 = -2.0 * cw / a0;
        dc.a2 = (1.0 - alpha) / a0;
        for (auto& v : raw) v = static_cast<float>(dc.process(v));
    }
    auto spectrum = [&](const std::vector<float>& x) {
        std::vector<std::complex<double>> a(static_cast<std::size_t>(n));
        for (int i = 0; i < n; ++i) a[static_cast<std::size_t>(i)] = x[static_cast<std::size_t>(skip + i)] * (0.5 - 0.5 * std::cos(2.0 * kPi * i / (n - 1)));
        fftInPlace(a);
        std::vector<double> p(static_cast<std::size_t>(n / 2));
        for (int k = 0; k < n / 2; ++k) p[static_cast<std::size_t>(k)] = std::norm(a[static_cast<std::size_t>(k)]);
        return p;
    };
    const auto pr = spectrum(raw), po = spectrum(out.l);
    const auto patch = dx7::unpackVoice(dx7::resolveVoice(dx7::loadBanks(gAssets), voice).data);
    const double keyHz = 440.0 * std::pow(2.0, (std::clamp(pitch + static_cast<int>(patch[144]) - 24, 0, 127) - 69) / 12.0);
    const double binHz = 48000.0 / n;
    const int first = std::max(2, static_cast<int>(std::ceil(std::max(30.0, 0.1 * keyHz) / binHz)));
    const int last = static_cast<int>(20000.0 / binHz);
    double strongest = 0.0;
    for (int k = first; k <= last; ++k) strongest = std::max(strongest, pr[static_cast<std::size_t>(k)]);
    double worst = 0.0;
    atHz = 0.0;
    for (int k = first; k <= last; ++k) {
        const auto u = static_cast<std::size_t>(k);
        if (pr[u] < strongest * 1e-3 || pr[u] < pr[u - 1] || pr[u] < pr[u + 1]) continue;
        const double change = std::fabs(10.0 * std::log10(po[u] / (0.5 * pr[u]) + 1e-30));
        if (change > worst) {
            worst = change;
            atHz = k * binHz;
        }
    }
    return worst;
}

void testAllVoicesKeepPartials() {
    // The voice high-pass must not touch any voice's sound: every ROM voice, C3 and C5.
    int bad = 0;
    double worst = 0.0;
    std::string where;
    for (const auto& v : listDx7Voices(gAssets)) {
        const std::string spec = v.bank + ":" + std::to_string(v.index);
        for (const int pitch : {48, 72}) {
            double hz = 0.0;
            const double change = worstPartialChange(spec, pitch, hz);
            if (change > 1.0) {
                ++bad;
                std::printf("      %s %s note %d: partial at %.1f Hz changed by %.2f dB\n", spec.c_str(), v.name.c_str(), pitch, hz, change);
            }
            if (change > worst) {
                worst = change;
                where = spec + " " + v.name + " note " + std::to_string(pitch) + " at " + fmt2(hz) + " Hz";
            }
        }
    }
    check(bad == 0, "all 256 voices keep every partial within 30 dB of their strongest within 1 dB (C3, C5; vs raw MSFA): "
                    "worst " + fmt2(worst) +
                        " dB (" + where + ")");
}

// 10 ms RMS envelope of one note (velocity 0.8) held for `hold` s; `releaseAtOff` > 0 sets 'release' just before
// the note-off.
std::vector<double> noteEnvelope(const json& p, int pitch, double hold, double seconds, float releaseAtOff = 0.0f,
                                 std::vector<float>* audio = nullptr) {
    auto s = make(p);
    const int sr = 48000, holdAt = static_cast<int>(hold * sr), total = static_cast<int>(seconds * sr);
    std::vector<float> l(static_cast<std::size_t>(total)), r(static_cast<std::size_t>(total));
    s->noteOn(1, pitch, 0.8f);
    for (int pos = 0; pos < total; pos += 32) {
        if (pos == holdAt) {
            if (releaseAtOff > 0.0f) s->setParam("release", releaseAtOff);
            s->noteOff(1);
        }
        s->process(l.data() + pos, r.data() + pos, std::min(32, total - pos));
    }
    std::vector<double> env;
    for (int i = 0; i + 480 <= total; i += 480) env.push_back(rms(l, i, i + 480));
    if (audio) *audio = l;
    return env;
}

// Seconds from `from` until the 10 ms envelope is `db` below its level just before `from`.
double fallTime(const std::vector<double>& e, double from, double db) {
    const auto i0 = static_cast<std::size_t>(std::lround(from / 0.01));
    const double ref = e[i0 - 1];
    for (std::size_t i = i0; i < e.size(); ++i)
        if (20.0 * std::log10(e[i] / ref + 1e-30) < db) return static_cast<double>(i - i0) * 0.01;
    return -1.0;
}

// Seconds until the envelope first comes within `db` of its maximum.
double riseTime(const std::vector<double>& e, double db) {
    const double top = *std::max_element(e.begin(), e.end());
    for (std::size_t i = 0; i < e.size(); ++i)
        if (20.0 * std::log10(e[i] / top + 1e-30) > db) return static_cast<double>(i) * 0.01;
    return -1.0;
}

void testEnvelopeScaling() {
    // Release: the -30 dB release time scales with the multiplier (STRINGS 1: ~0.7 s at 1x).
    {
        const double base = fallTime(noteEnvelope({{"voice", "STRINGS 1"}}, 60, 1.5, 9.0), 1.5, -30.0);
        bool ok = base > 0.3;
        std::string times = "1x " + fmt2(base) + " s";
        for (const float m : {0.25f, 0.5f, 2.0f, 4.0f, 8.0f}) {
            const double t = fallTime(noteEnvelope({{"voice", "STRINGS 1"}, {"release", m}}, 60, 1.5, 9.0), 1.5, -30.0);
            ok = ok && t > 0.0 && std::fabs(t / base / m - 1.0) < 0.15;
            times += ", " + fmt2(m) + "x " + fmt2(t) + " s";
        }
        check(ok, "release multiplier scales STRINGS 1's release time (-30 dB: " + times + ")");
    }
    // Attack (R1) and decay (R2/R3).
    {
        const double a1 = riseTime(noteEnvelope({{"voice", "STRINGS 1"}}, 60, 4.0, 4.0), -3.0);
        const double a4 = riseTime(noteEnvelope({{"voice", "STRINGS 1"}, {"attack", 4.0}}, 60, 4.0, 4.0), -3.0);
        check(a1 > 0.05 && std::fabs(a4 / a1 / 4.0 - 1.0) < 0.2,
              "attack 4x slows STRINGS 1's bow (to -3 dB) from " + fmt2(a1) + " s to " + fmt2(a4) + " s");
        auto decay = [](float m) {
            const auto e = noteEnvelope({{"voice", "MARIMBA"}, {"decay", m}}, 60, 3.0, 3.0);
            const auto peak = static_cast<std::size_t>(std::max_element(e.begin(), e.end()) - e.begin());
            return fallTime(e, 0.01 * static_cast<double>(peak + 1), -20.0);
        };
        const double d1 = decay(1.0f), d2 = decay(2.0f), dh = decay(0.5f);
        check(d1 > 0.1 && std::fabs(d2 / d1 / 2.0 - 1.0) < 0.15 && std::fabs(dh / d1 / 0.5 - 1.0) < 0.15,
              "decay multiplier scales MARIMBA's ring (-20 dB: 0.5x " + fmt2(dh) + " s, 1x " + fmt2(d1) + " s, 2x " + fmt2(d2) + " s)");
    }
    // 'release' applies at note-off: set just before the note-off it gives the same audio as configured from the
    // start; multipliers within half an EG rate step of 1 leave the patch untouched.
    {
        std::vector<float> late, early, unity, nearUnity;
        noteEnvelope({{"voice", "STRINGS 1"}}, 60, 1.0, 4.0, 4.0f, &late);
        noteEnvelope({{"voice", "STRINGS 1"}, {"release", 4.0}}, 60, 1.0, 4.0, 0.0f, &early);
        noteEnvelope({{"voice", "E.PIANO 1"}}, 60, 1.0, 2.0, 0.0f, &unity);
        noteEnvelope({{"voice", "E.PIANO 1"}, {"attack", 1.05}, {"decay", 0.95}, {"release", 1.08}}, 60, 1.0, 2.0, 0.0f, &nearUnity);
        check(late == early, "release set just before the note-off == release configured from the start (bit-identical)");
        check(unity == nearUnity, "attack/decay/release within half an EG rate step of 1 are bit-identical to the patch");
    }
    // The 30 s release safety limit (for patches that never decay) stretches with 'release': VOICE 1 at 16x is
    // still at about -37 dB after 30 s and must keep decaying instead of being faded out there.
    {
        std::vector<float> tail;
        noteEnvelope({{"voice", "VOICE 1"}, {"oversample", "1x"}, {"release", 16.0}}, 60, 1.0, 32.5, 0.0f, &tail);
        const int sr = 48000;
        const double before = rms(tail, 30 * sr, 30 * sr + sr / 5), after = rms(tail, 31 * sr + 3 * sr / 10, 31 * sr + sr / 2);
        const double drop = 20.0 * std::log10(after / (before + 1e-30) + 1e-30);
        check(before > 1e-4 && drop > -6.0, "release 16x: VOICE 1's tail keeps decaying past the 30 s safety limit (29.0-29.2 s -> "
                                            "30.3-30.5 s after the note-off: " + fmt2(drop) + " dB, level " +
                                            fmt2(20.0 * std::log10(before + 1e-30)) + " dBFS)");
    }
    // Pads: a released chord keeps sounding under the next one for as long as 'release' says. Old chord alone,
    // released after 1 s: time to fall 20 dB (the crossfade under the next chord).
    for (const char* voice : {"STRINGS 1", "BRASS 1"}) {
        const int sr = 48000;
        auto tail = [&](float release) {
            std::vector<Event> ev;
            for (const int p : {57, 60, 64}) {
                ev.push_back({0, true, p, p, 0.8f});
                ev.push_back({sr, false, p, 0, 0});
            }
            const auto x = render(*make({{"voice", voice}, {"release", release}}), ev, 12 * sr);
            const double before = rms(x.l, sr - sr / 20, sr);  // 10 ms windows, 1 ms hop, after the note-off
            for (int t = sr; t + sr / 100 <= 12 * sr; t += sr / 1000)
                if (rms(x.l, t, t + sr / 100) < 0.1 * before) return static_cast<double>(t - sr) / sr + 0.005;
            return -1.0;
        };
        const double t1 = tail(1.0f), t2 = tail(2.0f), t4 = tail(4.0f), t16 = tail(16.0f);
        check(t1 > 0.0 && std::fabs(t2 / t1 / 2.0 - 1.0) < 0.25 && std::fabs(t4 / t1 / 4.0 - 1.0) < 0.25 && t16 > 10.0 * t1,
              std::string(voice) + " chord tail after the change (-20 dB): release 1 " + fmt2(t1) + " s, 2 " + fmt2(t2) + " s, 4 " +
                  fmt2(t4) + " s, 16 " + fmt2(t16) + " s");
    }
}

// Integrated loudness (BS.1770, gated) of a stereo render.
double lufs(const Audio& a) {
    analysis::KWeighting kl(48000.0), kr(48000.0);
    std::vector<double> sums(1, 0.0);
    for (std::size_t i = 0; i < a.l.size(); ++i) {
        const double x = kl.process(a.l[i]), y = kr.process(a.r[i]);
        sums.push_back(sums.back() + x * x + y * y);
    }
    const std::size_t block = 19200, hop = 4800;
    std::vector<double> blocks;
    for (std::size_t s = 0; s + block <= a.l.size(); s += hop) blocks.push_back((sums[s + block] - sums[s]) / block);
    return analysis::integratedLoudness(blocks);
}

// The audition phrases (first two bars, 100 BPM): a melody in the A4-A5 register and whole-bar 4-note chords.
std::vector<Event> phraseEvents(bool chords) {
    struct PhraseNote {
        double beat, length;
        int pitch, velocity;
    };
    static const PhraseNote lead[] = {{0.0, 0.92, 76, 100}, {1.0, 0.92, 81, 100}, {2.0, 0.46, 79, 100}, {2.5, 0.46, 76, 100},
                                      {3.0, 0.92, 72, 100}, {4.0, 0.46, 74, 100}, {4.5, 0.46, 76, 100}, {5.0, 0.92, 72, 100},
                                      {6.0, 1.84, 71, 100}};
    static const PhraseNote chord[] = {{0.0, 3.8, 57, 84}, {0.0, 3.8, 60, 84}, {0.0, 3.8, 64, 84}, {0.0, 3.8, 69, 84},
                                       {4.0, 3.8, 53, 84}, {4.0, 3.8, 60, 84}, {4.0, 3.8, 65, 84}, {4.0, 3.8, 69, 84}};
    std::vector<Event> ev;
    int id = 0;
    auto add = [&](const PhraseNote& n) {
        ev.push_back({static_cast<int>(std::lround(n.beat * 28800.0)), true, id, n.pitch, static_cast<float>(n.velocity) / 127.0f});
        ev.push_back({static_cast<int>(std::lround((n.beat + n.length) * 28800.0)), false, id, 0, 0.0f});
        ++id;
    };
    if (chords) {
        for (const auto& n : chord) add(n);
    } else {
        for (const auto& n : lead) add(n);
    }
    return ev;
}

bool gPrintSpread = false;

void testLoudnessMatch() {
    // Every ROM voice at level 0 plays the melody and the chords (1x engine for speed; the calibration does not
    // depend on it). Per voice: the mean of the two (LUFS). Four-bar versions of both phrases at the default 2x
    // engine, before (loudest 50 ms of a held C4) -> after the phrase calibration: standard deviation 3.41 -> 2.00 LU,
    // voices within +-2 LU of the median 119 -> 225 of 256, p5..p95 9.4 -> 4.9 LU wide (melody alone: sd 3.75 ->
    // 2.75 LU, 126 -> 208 voices); LEAD BRASS -22.5 vs SYN-LEAD 1 -17.1 LUFS on the melody before. What stays
    // outside +-2 LU: percussion held down by the single-note peak cap (GLOKENSPL, COW BELL, XYLOPHONE, KOTO: -3..-6
    // LU), slow-attack pads that never open up on a melody of short notes (EVOLUTION, VOICES, STRINGS 5: loud on
    // chords, quiet on the melody) and effects (TAKE OFF, EXPLOSION).
    const int frames = 7 * 48000;
    const auto banks = dx7::loadBanks(gAssets);
    std::vector<std::pair<dx7::PackedVoice, std::array<double, 2>>> seen;  // ROM duplicates render once
    std::vector<double> value;
    for (const auto& bank : banks) {
        for (int index = 0; index < static_cast<int>(dx7::kVoicesPerBank); ++index) {
            const auto& data = bank.voices[static_cast<std::size_t>(index)];
            const std::string name = dx7::voiceName(data);
            std::array<double, 2> l{};
            const auto hit = std::find_if(seen.begin(), seen.end(), [&](const auto& s) { return s.first == data; });
            if (hit != seen.end()) {
                l = hit->second;
            } else {
                for (int k = 0; k < 2; ++k) {
                    auto synth = make({{"voice", bank.name + ":" + std::to_string(index)}, {"oversample", "1x"}});
                    l[static_cast<std::size_t>(k)] = lufs(render(*synth, phraseEvents(k == 1), frames));
                }
                seen.push_back({data, l});
            }
            value.push_back(0.5 * (l[0] + l[1]));
            if (gPrintSpread) std::printf("  %-6s %-2d %-10s melody %6.2f  chords %6.2f LUFS\n", bank.name.c_str(), index, name.c_str(), l[0], l[1]);
        }
    }
    auto sorted = value;
    std::sort(sorted.begin(), sorted.end());
    const double median = sorted[sorted.size() / 2];
    double avg = 0.0, var = 0.0;
    for (const double x : value) avg += x / static_cast<double>(value.size());
    for (const double x : value) var += (x - avg) * (x - avg) / static_cast<double>(value.size());
    const auto within = [&](double lu) {
        return static_cast<int>(std::count_if(value.begin(), value.end(), [&](double x) { return std::fabs(x - median) <= lu; }));
    };
    char what[300];
    std::snprintf(what, sizeof what, "autolevel: %zu voices on melody + chords: median %.1f LUFS, sd %.2f LU, p5..p95 %.1f..%.1f, "
                  "%d within +-2 LU (>= 210), %d within +-3 LU", value.size(), median, std::sqrt(var), sorted[sorted.size() * 5 / 100],
                  sorted[sorted.size() * 95 / 100], within(2.0), within(3.0));
    check(value.size() == 256 && within(2.0) >= 210 && std::sqrt(var) < 2.4, what);
    // The pair the sound designers measured: the full audition melody at the default 2x engine.
    std::vector<Event> melody;
    {
        const double beats[15][3] = {{0.0, 0.92, 76}, {1.0, 0.92, 81}, {2.0, 0.46, 79}, {2.5, 0.46, 76}, {3.0, 0.92, 72},
                                     {4.0, 0.46, 74}, {4.5, 0.46, 76}, {5.0, 0.92, 72}, {6.0, 1.84, 71}, {8.0, 0.92, 76},
                                     {9.0, 0.92, 81}, {10.0, 0.46, 83}, {10.5, 0.46, 81}, {11.0, 0.92, 79}, {12.0, 2.76, 81}};
        for (int i = 0; i < 15; ++i) {
            melody.push_back({static_cast<int>(std::lround(beats[i][0] * 28800.0)), true, i, static_cast<int>(beats[i][2]), 100 / 127.0f});
            melody.push_back({static_cast<int>(std::lround((beats[i][0] + beats[i][1]) * 28800.0)), false, i, 0, 0.0f});
        }
    }
    const double lb = lufs(render(*make({{"voice", "LEAD BRASS"}}), melody, 12 * 48000));
    const double sl = lufs(render(*make({{"voice", "rom1a:SYN-LEAD 1"}}), melody, 12 * 48000));
    check(std::fabs(lb - sl) < 1.5, "audition melody: LEAD BRASS " + fmt2(lb) + " vs SYN-LEAD 1 " + fmt2(sl) +
                                        " LUFS (within 1.5 LU; before: -22.5 vs -17.1)");
}

// Without the ROM banks (not distributed, see assets/dx7/README.md): what still must hold.
void testWithoutBanks() {
    check(listDx7Voices(gAssets).empty(), "no banks: the voice list is empty (no exception)");
    std::string msg;
    const bool threw = throwsConfig([] { dx7::loadBanks(gAssets); }, &msg);
    check(threw && msg.find("assets/dx7/README.md") != std::string::npos,
          "no banks: loadBanks() -> ConfigError naming assets/dx7/README.md: " + msg);
    check(throwsConfig([] { make({{"voice", "E.PIANO 1"}}); }), "no banks: prepare() of a dx7 voice -> ConfigError");
    check(throwsConfig([] { makeDx7Synth()->configure({{"voice", "rom1a:32"}}); }), "index 32 rejected by configure()");
    check(throwsConfig([] { makeDx7Synth()->configure({{"cutoff", 1000}}); }), "unknown param rejected");
    std::array<std::uint8_t, dx7::kBankSysexBytes> zero{};
    check(throwsConfig([&] { dx7::parseBank(zero, "x", "zeros"); }), "bad framing -> ConfigError");
}

}  // namespace

int main(int argc, char** argv) {
    namespace fs = std::filesystem;
    if (argc > 1 && std::string(argv[argc - 1]) == "--spread") {
        gPrintSpread = true;
        --argc;
    }
    if (argc > 1) {
        gAssets = argv[1];
    } else {
        for (const char* candidate : {"assets", "../assets", "../../assets"}) {
            if (fs::is_directory(fs::path(candidate) / "dx7") || fs::is_directory(fs::path(candidate) / "soundfonts")) {
                gAssets = fs::absolute(candidate).string();
                break;
            }
        }
    }
    if (gAssets.empty()) {
        std::printf("FAIL: cannot find the assets folder (run from the repo root or pass the assets dir)\n");
        return 1;
    }
    if (!dx7BanksInstalled(gAssets)) {
        std::printf("SKIP: %s - ROM-dependent DX7 checks skipped\n", kDx7NoBanksHint);
        try {
            testWithoutBanks();
        } catch (const std::exception& e) {
            std::printf("FAIL: unexpected exception: %s\n", e.what());
            return 1;
        }
        std::printf("%d/%d checks passed (ROM checks skipped)\n", gChecks - gFailures, gChecks);
        return gFailures == 0 ? 0 : 1;
    }
    try {
        testBanks();
        testConfigErrors();
        testEpiano();
        testPitch();
        testStereoAndDeterminism();
        testVoicesAndControls();
        testVoiceHighPass();
        testAllVoicesKeepPartials();
        testEnvelopeScaling();
        testLoudnessMatch();
    } catch (const std::exception& e) {
        std::printf("FAIL: unexpected exception: %s\n", e.what());
        return 1;
    }
    std::printf("%d/%d checks passed\n", gChecks - gFailures, gChecks);
    return gFailures == 0 ? 0 : 1;
}
