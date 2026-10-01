// Tests for the "sampler" instrument: WAV zones and folder mapping (note names, GM drum names), pitch and
// resampling, one-shot / gated playback, loops (forward, ping-pong), reverse, start offset, stereo files,
// hi-hat choke, raw SoundFont samples, strict configuration, determinism and idle, voice stealing / mono, speed;
// the shared playback core (stretched anti-aliasing kernels; forward / ping-pong loops of any length and loop
// until release, sample-exact against the unrolled signal); and the SFZ zone model on synthetic files: round
// robin, random layers (preview-stable), first / legato and release triggers, rt_decay, sustain pedal, note
// polyphony, groups / off_by / off modes, generators, offset / end, key tracking, velocity curves and
// crossfades, zone envelopes, filters, EQ, per-note randomness, start delay, vibrato / tremolo, zone width,
// 16-bit storage (bit-identical), smpl chunk loops and root keys, shared files, parallel loading, expression;
// channel mixes of multichannel files (zone "channels") and lossless WavPack files (CRC-checked, smpl loops from the
// embedded RIFF header; real GrandOrgue pipes when $AGENTSOUND_SAMPLES has the lars-palo-burea-church pack).
// played, not triggered: live dynamics (crossfades, gain curves, cutoff, layer stacks, tone, range), legato
// (scripted: past the attack, level-matched, click-free; library legato zones; portamento; release zones), the
// instrument vibrato, preview parity, keyswitches (swLast / swDown / swDefault) and silent-layer skipping; guitar
// techniques: per-note bends (bendfollow) and the string's harmonic (pinch harmonics, feedback).
// Run from the repo root (or pass the assets folder as argv[1]).

#include "analysis/ClickDetector.h"
#include "core/Module.h"
#include "instruments/Sampler.h"
#include "instruments/SamplerCore.h"
#include "instruments/SamplerFiles.h"
#include "instruments/SamplerWavPack.h"
#include "io/WavWriter.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <string>
#include <vector>

#include "data/wavpack_fixtures.h"

using namespace as;
namespace fs = std::filesystem;

namespace {

int gFailures = 0;
int gChecks = 0;
std::string gAssets;
fs::path gTmp;

void check(bool ok, const std::string& what) {
    ++gChecks;
    std::printf("[%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
    if (!ok) ++gFailures;
}

template <typename... A>
std::string fmt(const char* f, A... a) {
    char buf[1024];
    std::snprintf(buf, sizeof buf, f, a...);
    return buf;
}

constexpr double kSr = 48000.0;
constexpr double kPi = 3.14159265358979;
long sec(double s) { return static_cast<long>(std::lround(s * kSr)); }
double db(double x) { return 20.0 * std::log10(std::max(x, 1e-12)); }

// Mono 16-bit PCM WAV.
std::string writeMono(const fs::path& path, const std::vector<float>& x, int rate) {
    std::vector<unsigned char> b;
    auto u16 = [&](unsigned v) { b.push_back(v & 0xFF); b.push_back((v >> 8) & 0xFF); };
    auto u32 = [&](unsigned v) { u16(v & 0xFFFF); u16(v >> 16); };
    const unsigned data = static_cast<unsigned>(x.size() * 2);
    b.insert(b.end(), {'R', 'I', 'F', 'F'});
    u32(36 + data);
    b.insert(b.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
    u32(16);
    u16(1);
    u16(1);
    u32(static_cast<unsigned>(rate));
    u32(static_cast<unsigned>(rate) * 2);
    u16(2);
    u16(16);
    b.insert(b.end(), {'d', 'a', 't', 'a'});
    u32(data);
    for (float v : x) u16(static_cast<unsigned>(static_cast<std::int16_t>(std::lround(std::clamp(v, -1.0f, 1.0f) * 32767.0f))) & 0xFFFF);
    fs::create_directories(path.parent_path());
    std::ofstream(path, std::ios::binary).write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
    return path.string();
}

std::string writeStereo(const fs::path& path, const std::vector<float>& l, const std::vector<float>& r, int rate) {
    fs::create_directories(path.parent_path());
    WavWriter w;
    w.open(path.string(), rate, 32, 1);
    w.write(l.data(), r.data(), static_cast<int>(l.size()));
    w.close();
    return path.string();
}

// WAV with any sample format (bits 16 / 24 PCM, 32 float), optional 'smpl' chunk (unity note, one loop:
// start + inclusive end, type 0 forward / 1 ping-pong) placed after the data like most editors do.
struct SmplInfo {
    int unity{60};
    std::uint32_t fraction{0};
    long loopStart{-1}, loopEnd{-1};
    int type{0};
};
std::string writeWav(const fs::path& path, const std::vector<float>& x, int rate, int bits, const SmplInfo* smpl = nullptr,
                     bool zeroLowByte = false) {
    std::vector<unsigned char> b, data;
    auto put16 = [](std::vector<unsigned char>& v, unsigned x) { v.push_back(x & 0xFF); v.push_back((x >> 8) & 0xFF); };
    auto put32 = [&](std::vector<unsigned char>& v, unsigned x) { put16(v, x & 0xFFFF); put16(v, x >> 16); };
    for (const float s : x) {
        if (bits == 16) {
            put16(data, static_cast<unsigned>(static_cast<std::int16_t>(std::lround(std::clamp(s, -1.0f, 1.0f) * 32767.0f))) & 0xFFFF);
        } else if (bits == 24) {
            std::int32_t v = static_cast<std::int32_t>(std::lround(std::clamp(s, -1.0f, 1.0f) * 8388607.0f));
            if (zeroLowByte) v &= ~0xFF;
            data.push_back(static_cast<unsigned char>(v & 0xFF));
            data.push_back(static_cast<unsigned char>((v >> 8) & 0xFF));
            data.push_back(static_cast<unsigned char>((v >> 16) & 0xFF));
        } else {
            unsigned u;
            std::memcpy(&u, &s, 4);
            put32(data, u);
        }
    }
    std::vector<unsigned char> sm;
    if (smpl) {
        for (unsigned v : {0u, 0u, static_cast<unsigned>(1e9 / rate), static_cast<unsigned>(smpl->unity), smpl->fraction, 0u, 0u,
                           smpl->loopStart >= 0 ? 1u : 0u, 0u})
            put32(sm, v);
        if (smpl->loopStart >= 0) {
            for (unsigned v : {0u, static_cast<unsigned>(smpl->type), static_cast<unsigned>(smpl->loopStart), static_cast<unsigned>(smpl->loopEnd), 0u, 0u})
                put32(sm, v);
        }
    }
    const unsigned fmt = bits == 32 ? 3 : 1, align = static_cast<unsigned>(bits / 8);
    b.insert(b.end(), {'R', 'I', 'F', 'F'});
    put32(b, static_cast<unsigned>(4 + 24 + 8 + data.size() + (sm.empty() ? 0 : 8 + sm.size())));
    b.insert(b.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
    put32(b, 16);
    put16(b, fmt);
    put16(b, 1);
    put32(b, static_cast<unsigned>(rate));
    put32(b, static_cast<unsigned>(rate) * align);
    put16(b, align);
    put16(b, static_cast<unsigned>(bits));
    b.insert(b.end(), {'d', 'a', 't', 'a'});
    put32(b, static_cast<unsigned>(data.size()));
    b.insert(b.end(), data.begin(), data.end());
    if (!sm.empty()) {
        b.insert(b.end(), {'s', 'm', 'p', 'l'});
        put32(b, static_cast<unsigned>(sm.size()));
        b.insert(b.end(), sm.begin(), sm.end());
    }
    fs::create_directories(path.parent_path());
    std::ofstream(path, std::ios::binary).write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
    return path.string();
}

std::vector<float> sine(double hz, int rate, double seconds, double amp = 0.5) {
    std::vector<float> v(static_cast<std::size_t>(std::lround(seconds * rate)));
    for (std::size_t i = 0; i < v.size(); ++i) v[i] = static_cast<float>(amp * std::sin(2.0 * kPi * hz * static_cast<double>(i) / rate));
    return v;
}

struct Audio {
    std::vector<float> l, r;
    std::vector<float> mono() const {
        std::vector<float> m(l.size());
        for (std::size_t i = 0; i < l.size(); ++i) m[i] = 0.5f * (l[i] + r[i]);
        return m;
    }
};

struct Event {
    long at;
    bool on;
    int id, pitch;
    float vel;
    const char* param = nullptr;  // set: setParam(param, value) at `at` (on / id / pitch ignored)
    float value = 0.0f;
};

Event setAt(long at, const char* param, float value) { return Event{at, false, 0, 0, 0.0f, param, value}; }

std::unique_ptr<Instrument> make(const json& params, double sr = kSr, double startBeat = 0.0) {
    auto s = makeSampler();
    s->configure(params);
    RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.assetDir = gAssets;
    ctx.startBeat = startBeat;
    ctx.bpm = 120.0;
    ctx.seed = 11;
    s->prepare(ctx);
    return s;
}

Audio render(Instrument& synth, std::vector<Event> events, long frames, int blockSize = 256) {
    std::stable_sort(events.begin(), events.end(), [](const Event& a, const Event& b) { return a.at < b.at; });
    Audio a;
    a.l.assign(static_cast<std::size_t>(frames), 0.0f);
    a.r.assign(static_cast<std::size_t>(frames), 0.0f);
    std::size_t next = 0;
    unsigned lcg = 777;
    for (long pos = 0; pos < frames;) {
        while (next < events.size() && events[next].at <= pos) {
            const auto& e = events[next++];
            if (e.param) synth.setParam(e.param, e.value);
            else if (e.on) synth.noteOn(e.id, e.pitch, e.vel);
            else synth.noteOff(e.id);
        }
        long n = blockSize;
        if (n <= 0) {
            lcg = lcg * 1103515245u + 12345u;
            n = 1 + static_cast<long>((lcg >> 16) % kMaxBlock);
        }
        n = std::min({n, static_cast<long>(kMaxBlock), frames - pos});
        if (next < events.size()) n = std::min(n, events[next].at - pos);
        synth.process(a.l.data() + pos, a.r.data() + pos, static_cast<int>(n));
        pos += n;
    }
    return a;
}

double rms(const std::vector<float>& x, long from, long to) {
    double s = 0.0;
    from = std::max(0L, from);
    to = std::min(static_cast<long>(x.size()), to);
    for (long i = from; i < to; ++i) s += static_cast<double>(x[static_cast<std::size_t>(i)]) * x[static_cast<std::size_t>(i)];
    return std::sqrt(s / std::max(1L, to - from));
}

int clicks(const Audio& a) {
    analysis::ClickDetector det(kSr);
    det.feed(a.l.data(), a.r.data(), static_cast<int>(a.l.size()));
    det.finish();
    for (const auto& e : det.events()) {
        std::printf("      click at %.4f s: jump %.1f dB, contrast %.1f dB, rise %.1f dB, hf rise %.1f dB\n",
                    static_cast<double>(e.sample) / kSr, e.jumpDb(), e.contrastDb(), e.riseDb, e.hfRiseDb);
    }
    return static_cast<int>(det.events().size());
}

// Frequency from upward zero crossings over [from, to).
double zeroCrossHz(const std::vector<float>& x, long from, long to) {
    double first = -1.0, last = 0.0;
    int n = 0;
    for (long i = from + 1; i < to; ++i) {
        const float a = x[static_cast<std::size_t>(i - 1)], b = x[static_cast<std::size_t>(i)];
        if (a < 0.0f && b >= 0.0f) {
            const double t = static_cast<double>(i - 1) + a / (a - b);
            if (first < 0.0) first = t;
            last = t;
            ++n;
        }
    }
    return n > 1 ? kSr * (n - 1) / (last - first) : 0.0;
}
double cents(double hz, double ref) { return 1200.0 * std::log2(std::max(hz, 1e-9) / ref); }

bool rejects(const json& p, const std::string& needle) {
    try {
        make(p);
    } catch (const ConfigError& e) {
        const bool ok = std::string(e.what()).find(needle) != std::string::npos;
        if (!ok) std::printf("      message: %s\n", e.what());
        return ok;
    }
    return false;
}

// ----------------------------------------------------------------------------------------- tests

void testNoteFolder() {
    std::printf("folder of note-named samples\n");
    const fs::path dir = gTmp / "keys";
    writeMono(dir / "C4.wav", sine(261.6256, 44100, 1.0), 44100);
    writeMono(dir / "c5.wav", sine(523.2511, 44100, 1.0), 44100);
    writeMono(dir / "F#5.wav", sine(739.9888, 44100, 1.0), 44100);
    auto s = make({{"samples", {{"dir", dir.string()}}}});
    for (const auto& [key, expect] : std::vector<std::pair<int, double>>{
             {60, 261.6256}, {64, 329.6276}, {48, 130.8128}, {70, 466.1638}, {72, 523.2511}, {78, 739.9888}, {84, 1046.502}}) {
        auto one = make({{"samples", {{"dir", dir.string()}}}});
        const auto m = render(*one, {{0, true, 1, key, 1.0f}}, sec(0.5)).mono();
        const double f = zeroCrossHz(m, sec(0.05), sec(0.45));
        check(std::fabs(cents(f, expect)) < 0.5, fmt("key %d: %.2f Hz (expected %.2f; nearest sample transposed, 44.1 -> 48 kHz)", key, f, expect));
    }
    // level: a full-velocity note plays the file at its level (mono: -3 dB per side at centre)
    const Audio a = render(*s, {{0, true, 1, 60, 1.0f}}, sec(0.5));
    check(std::fabs(db(rms(a.l, sec(0.1), sec(0.4)) / (0.5 / std::sqrt(2.0))) + 3.01) < 0.05,
          fmt("unity level: %.2f dB re the file (expected -3.01, equal-power centre)", db(rms(a.l, sec(0.1), sec(0.4)) / (0.5 / std::sqrt(2.0)))));
    auto soft = make({{"samples", {{"dir", dir.string()}}}});
    const Audio b = render(*soft, {{0, true, 1, 60, 64.0f / 127.0f}}, sec(0.5));
    check(std::fabs(db(rms(b.l, sec(0.1), sec(0.4)) / rms(a.l, sec(0.1), sec(0.4))) - 40.0 * std::log10(64.0 / 127.0)) < 0.05,
          "velocity 64: (64/127)^2 = -11.9 dB");
    for (const auto& [param, value, expect] : std::vector<std::tuple<std::string, double, double>>{
             {"transpose", 12, 523.2511}, {"tune", -100, 246.9417}, {"pitchbend", 7, 391.9954}}) {
        auto t = make({{"samples", {{"dir", dir.string()}}}, {param, value}});
        const auto m = render(*t, {{0, true, 1, 60, 1.0f}}, sec(0.5)).mono();
        const double f = zeroCrossHz(m, sec(0.05), sec(0.45));
        check(std::fabs(cents(f, expect)) < 0.5, fmt("%s %g: %.2f Hz (expected %.2f)", param.c_str(), value, f, expect));
    }
}

void testDrumFolder() {
    std::printf("folder of GM drum names, one-shot, choke\n");
    const fs::path dir = gTmp / "kit";
    std::vector<float> kick(24000), hat(4800), ohh(48000);
    for (std::size_t i = 0; i < kick.size(); ++i) kick[i] = static_cast<float>(0.8 * std::exp(-static_cast<double>(i) / 6000.0) * std::sin(2.0 * kPi * 55.0 * i / 48000.0));
    std::uint32_t rng = 1;
    auto noise = [&] { rng = rng * 1664525u + 1013904223u; return static_cast<float>((rng >> 8) * (1.0 / 8388608.0) - 1.0); };
    for (std::size_t i = 0; i < hat.size(); ++i) hat[i] = 0.3f * static_cast<float>(std::exp(-static_cast<double>(i) / 800.0)) * noise();
    for (std::size_t i = 0; i < ohh.size(); ++i) ohh[i] = 0.3f * static_cast<float>(std::exp(-static_cast<double>(i) / 20000.0)) * noise();
    writeMono(dir / "kick.wav", kick, 48000);
    writeMono(dir / "Closed Hat.wav", hat, 48000);
    writeMono(dir / "ohh.wav", ohh, 48000);
    const json cfg = {{"samples", {{"dir", dir.string()}}}, {"oneshot", "on"}};
    auto s = make(cfg);
    const Audio a = render(*s, {{0, true, 1, 36, 1.0f}, {sec(0.01), false, 1, 36, 0.0f}}, sec(0.5));
    check(rms(a.l, sec(0.2), sec(0.3)) > 0.05, "kick.wav plays on key 36 and one-shot ignores the 10 ms note-off");
    double worst = 0.0;
    for (long i = sec(0.005); i < sec(0.4); ++i) worst = std::max(worst, std::fabs(a.l[static_cast<std::size_t>(i)] / 0.70710678 - kick[static_cast<std::size_t>(i)]));
    check(worst < 2e-3, fmt("drum samples play untransposed at 48 kHz: matches the file after the 1 ms attack (max error %.1e)", worst));
    auto gated = make({{"samples", {{"dir", dir.string()}}}});
    const Audio g = render(*gated, {{0, true, 1, 36, 1.0f}, {sec(0.01), false, 1, 36, 0.0f}}, sec(0.5));
    check(rms(g.l, sec(0.2), sec(0.3)) < 1e-4, "gated (oneshot off): the note-off releases the kick (release 0.1 s)");
    auto miss = make(cfg);
    const Audio m = render(*miss, {{0, true, 1, 38, 1.0f}}, sec(0.2));
    check(rms(m.l, 0, sec(0.2)) == 0.0, "no file for the snare: key 38 is silent");
    // 'Closed Hat.wav' maps to key 42 (case and spaces ignored); it chokes the open hat
    auto open = make(cfg);
    const Audio o = render(*open, {{0, true, 1, 46, 1.0f}}, sec(0.8));
    auto choked = make(cfg);
    const Audio c = render(*choked, {{0, true, 1, 46, 1.0f}, {sec(0.3), true, 2, 42, 1.0f}}, sec(0.8));
    const double before = rms(o.l, sec(0.5), sec(0.8)), after = rms(c.l, sec(0.5), sec(0.8));
    check(db(before / after) > 30.0 && clicks(c) == 0,
          fmt("closed hat (42) chokes the open hat (46): tail %.1f -> %.1f dBFS, %d clicks", db(before), db(after), clicks(c)));
}

void testZonesAndLoops() {
    std::printf("zones, velocity layers, loops, reverse, start offset\n");
    const fs::path dir = gTmp / "zones";
    const std::string soft = writeMono(dir / "soft.wav", sine(440.0, 48000, 0.5), 48000);
    const std::string loud = writeMono(dir / "loud.wav", sine(660.0, 48000, 0.5), 48000);
    const json layers = {{"samples", json::array({{{"file", soft}, {"root", 69}, {"velhi", 80}}, {{"file", loud}, {"root", 69}, {"vello", 81}}})}};
    auto a = make(layers);
    const double fs1 = zeroCrossHz(render(*a, {{0, true, 1, 69, 60.0f / 127.0f}}, sec(0.3)).mono(), sec(0.05), sec(0.25));
    auto b = make(layers);
    const double fs2 = zeroCrossHz(render(*b, {{0, true, 1, 69, 120.0f / 127.0f}}, sec(0.3)).mono(), sec(0.05), sec(0.25));
    check(std::fabs(fs1 - 440.0) < 0.5 && std::fabs(fs2 - 660.0) < 0.5, fmt("velocity layers: vel 60 -> %.1f Hz, vel 120 -> %.1f Hz", fs1, fs2));

    // forward loop of a short file (100 cycles of 441 Hz at 44.1 kHz): a held note sustains, click-free
    const std::string cyc = writeMono(dir / "cyc.wav", sine(441.0, 44100, 10000.0 / 44100.0), 44100);
    auto l = make({{"samples", {{"file", cyc}, {"root", 69}, {"loop", "forward"}}}});
    const Audio la = render(*l, {{0, true, 1, 69, 1.0f}, {sec(2.0), false, 1, 69, 0.0f}}, sec(2.5));
    check(rms(la.l, sec(1.8), sec(2.0)) > 0.2 && clicks(la) == 0 && std::fabs(zeroCrossHz(la.mono(), sec(1.0), sec(1.9)) - 441.0) < 0.05,
          fmt("forward loop sustains a 0.23 s file for 2 s at 441 Hz, %d clicks", clicks(la)));
    // ping-pong on a rising ramp: the loop plays up and down (a triangle), no jumps
    std::vector<float> ramp(4800);
    for (std::size_t i = 0; i < ramp.size(); ++i) ramp[i] = -0.5f + static_cast<float>(i) / 4800.0f;
    const std::string rp = writeMono(dir / "ramp.wav", ramp, 48000);
    auto pp = make({{"samples", {{"file", rp}, {"root", 60}, {"loop", "pingpong"}}}});
    const Audio pa = render(*pp, {{0, true, 1, 60, 1.0f}}, sec(1.0));
    float lo = 1.0f, hi = -1.0f, step = 0.0f;
    for (long i = sec(0.2); i < sec(1.0); ++i) {
        const float x = pa.l[static_cast<std::size_t>(i)] / 0.70710678f;
        lo = std::min(lo, x);
        hi = std::max(hi, x);
        step = std::max(step, std::fabs(x - pa.l[static_cast<std::size_t>(i - 1)] / 0.70710678f));
    }
    check(lo < -0.49f && hi > 0.49f && step < 0.002f && clicks(pa) == 0,
          fmt("ping-pong loop: a triangle between %.3f and %.3f, largest step %.4f (ramp slope 0.0002)", lo, hi, step));

    // reverse: a decaying burst plays backwards (swells up)
    std::vector<float> burst(24000);
    for (std::size_t i = 0; i < burst.size(); ++i) burst[i] = static_cast<float>(0.8 * std::exp(-static_cast<double>(i) / 3000.0) * std::sin(2.0 * kPi * 440.0 * i / 48000.0));
    const std::string bp = writeMono(dir / "burst.wav", burst, 48000);
    auto fwd = make({{"samples", {{"file", bp}}}, {"oneshot", "on"}});
    auto rev = make({{"samples", {{"file", bp}}}, {"oneshot", "on"}, {"reverse", "on"}});
    const Audio fa = render(*fwd, {{0, true, 1, 60, 1.0f}}, sec(0.5)), ra = render(*rev, {{0, true, 1, 60, 1.0f}}, sec(0.5));
    check(rms(fa.l, 0, sec(0.05)) > 10.0 * rms(fa.l, sec(0.4), sec(0.5)) && rms(ra.l, sec(0.4), sec(0.5)) > 10.0 * rms(ra.l, 0, sec(0.05)),
          "reverse: the decaying burst swells up instead");
    // start offset: [0.2 s silence][tone] starts with the tone at start = 200 ms
    std::vector<float> late(9600, 0.0f);
    const auto tone = sine(440.0, 48000, 0.3);
    late.insert(late.end(), tone.begin(), tone.end());
    const std::string lp = writeMono(dir / "late.wav", late, 48000);
    auto st0 = make({{"samples", {{"file", lp}}}});
    auto st1 = make({{"samples", {{"file", lp}}}, {"start", 200}});
    const Audio s0 = render(*st0, {{0, true, 1, 60, 1.0f}}, sec(0.15)), s1 = render(*st1, {{0, true, 1, 60, 1.0f}}, sec(0.15));
    check(rms(s0.l, sec(0.01), sec(0.15)) < 1e-4 && rms(s1.l, sec(0.01), sec(0.15)) > 0.2, "start 200 ms skips the silent head");
    // resonant lowpass
    auto open = make({{"samples", {{"file", soft}, {"root", 69}}}});
    auto closed = make({{"samples", {{"file", soft}, {"root", 69}}}, {"cutoff", 110}});
    const double ro = rms(render(*open, {{0, true, 1, 69, 1.0f}}, sec(0.4)).l, sec(0.1), sec(0.4));
    const double rc = rms(render(*closed, {{0, true, 1, 69, 1.0f}}, sec(0.4)).l, sec(0.1), sec(0.4));
    check(db(rc / ro) < -20.0 && db(rc / ro) > -28.0, fmt("cutoff 110 Hz on a 440 Hz tone: %.1f dB (12 dB/oct: ~-24)", db(rc / ro)));
}

void testStereoAndSf2() {
    std::printf("stereo files, raw SoundFont samples\n");
    const fs::path dir = gTmp / "stereo";
    const auto left = sine(441.0, 44100, 0.5, 0.5);
    const std::vector<float> right(left.size(), 0.0f);
    const std::string st = writeStereo(dir / "left_only.wav", left, right, 44100);
    auto s = make({{"samples", {{"file", st}, {"root", 69}}}});
    const Audio a = render(*s, {{0, true, 1, 69, 1.0f}}, sec(0.4));
    check(rms(a.l, sec(0.1), sec(0.4)) > 0.3 && rms(a.r, sec(0.1), sec(0.4)) < 1e-6, "stereo file: channels stay separate at width 1, full level");
    auto m = make({{"samples", {{"file", st}, {"root", 69}}}, {"width", 0}});
    const Audio b = render(*m, {{0, true, 1, 69, 1.0f}}, sec(0.4));
    double d = 0.0;
    for (std::size_t i = 0; i < b.l.size(); ++i) d = std::max(d, static_cast<double>(std::fabs(b.l[i] - b.r[i])));
    check(d < 1e-6, "width 0 folds a stereo file to mono");

    auto sf = make({{"samples", {{"file", "soundfonts/GeneralUser-GS.sf2"}, {"sample", "Sine-750Hz"}, {"loop", "forward"}}}});
    const Audio c = render(*sf, {{0, true, 1, 69, 1.0f}}, sec(1.0));
    const double f = zeroCrossHz(c.mono(), sec(0.1), sec(0.9));
    check(std::fabs(cents(f, 440.0)) < 0.5 && rms(c.l, sec(0.8), sec(1.0)) > 0.05,
          fmt("SoundFont sample 'Sine-750Hz' (root 78, -23 ct, loop from the header): A4 = %.2f Hz, sustained", f));
}

void testConfig() {
    std::printf("config errors\n");
    check(rejects(json::object(), "'samples' is required"), "missing samples");
    check(rejects({{"samples", 5}}, "must be {\"dir\""), "samples of the wrong type");
    check(rejects({{"samples", {{"dir", "samples/x"}, {"root", 3}}}}, "unknown key 'root'"), "unknown key next to dir");
    check(rejects({{"samples", {{"file", "a.wav"}, {"rot", 60}}}}, "unknown key 'rot'"), "unknown zone key");
    check(rejects({{"samples", {{"file", "a.wav"}, {"loop", "circle"}}}}, "\"none\", \"oneshot\", \"forward\", \"pingpong\", \"sustain\", \"auto\""),
          "bad loop mode");
    check(rejects({{"samples", {{"file", "a.wav"}, {"lo", 70}, {"hi", 60}}}}, "lo > hi"), "lo > hi");
    check(rejects({{"samples", {{"file", "a.wav"}, {"root", 60.5}, {"lo", 1.5}}}}, "whole number"), "fractional key");
    check(rejects({{"samples", {{"file", "a.wav"}, {"sample", "x"}}}}, "only for SoundFont files"), "sample on a WAV");
    check(rejects({{"samples", {{"file", "soundfonts/GeneralUser-GS.sf2"}}}}, "name the sample"), "SoundFont without sample");
    check(rejects({{"samples", {{"file", "soundfonts/GeneralUser-GS.sf2"}, {"sample", "Sine-750"}}}}, "did you mean \"Sine-750Hz\""),
          "unknown SoundFont sample with suggestions");
    check(rejects({{"samples", {{"file", "samples/none.wav"}}}}, "not found"), "missing file");
    check(rejects({{"samples", {{"dir", (gTmp / "nothing_here").string()}}}}, "not a folder"), "missing folder");
    const fs::path bad = gTmp / "badnames";
    writeMono(bad / "C4.wav", sine(261.6, 48000, 0.1), 48000);
    writeMono(bad / "melody.wav", sine(261.6, 48000, 0.1), 48000);
    check(rejects({{"samples", {{"dir", bad.string()}}}}, "cannot map 'melody.wav'"), "unmappable file name in a folder");
    const fs::path dup = gTmp / "dups";
    writeMono(dup / "kick.wav", sine(60, 48000, 0.1), 48000);
    writeMono(dup / "bd.wav", sine(60, 48000, 0.1), 48000);
    check(rejects({{"samples", {{"dir", dup.string()}}}}, "both map to key 36"), "two files on one key");
    const std::string shortWav = writeMono(gTmp / "short.wav", sine(441, 48000, 0.01), 48000);
    check(rejects({{"samples", {{"file", shortWav}, {"loop", "forward"}, {"loopEnd", 100000}}}}, "must lie inside the sample"),
          "loop outside the file");
    check(rejects({{"samples", {{"file", shortWav}}}, {"cutoff", 5}}, "outside 20..20000"), "param out of range");
}

void testDeterminismIdle() {
    std::printf("determinism, block independence, idle\n");
    const fs::path dir = gTmp / "keys";
    const std::vector<Event> ev = {{0, true, 1, 60, 0.9f}, {500, true, 2, 67, 0.6f}, {sec(0.3), false, 1, 60, 0}, {sec(0.4), true, 3, 72, 1.0f},
                                   {sec(0.6), false, 2, 67, 0}, {sec(0.7), false, 3, 72, 0}};
    const json cfg = {{"samples", {{"dir", dir.string()}}}, {"cutoff", 3000}, {"resonance", 0.4}, {"release", 0.2}};
    auto a = make(cfg);
    auto b = make(cfg);
    auto c = make(cfg);
    const Audio x = render(*a, ev, sec(1.2)), y = render(*b, ev, sec(1.2)), z = render(*c, ev, sec(1.2), 0);
    check(x.l == y.l && x.r == y.r, "same input -> bit-identical output");
    check(x.l == z.l && x.r == z.r, "random block sizes -> bit-identical output");
    auto d = make(cfg);
    d->noteOn(1, 60, 1.0f);
    std::vector<float> l(256), r(256);
    long pos = 0;
    for (; pos < sec(0.2); pos += 256) d->process(l.data(), r.data(), 256);
    d->noteOff(1);
    long idleAt = -1;
    for (; pos < sec(3.0); pos += 256) {
        d->process(l.data(), r.data(), 256);
        if (d->idle()) { idleAt = pos; break; }
    }
    check(idleAt > 0 && idleAt < sec(1.5), fmt("idle %.2f s after the note-off (release 0.2 s)", (idleAt - sec(0.2)) / kSr));
}

// Amplitude of the component at `hz` (4-term Blackman-Harris window, -92 dB side lobes).
double tone(const std::vector<float>& x, long start, int n, double hz) {
    std::complex<double> acc = 0.0;
    double wsum = 0.0;
    for (int i = 0; i < n; ++i) {
        const double t = 2.0 * kPi * i / (n - 1);
        const double w = 0.35875 - 0.48829 * std::cos(t) + 0.14128 * std::cos(2 * t) - 0.01168 * std::cos(3 * t);
        acc += w * static_cast<double>(x[static_cast<std::size_t>(start + i)]) * std::polar(1.0, -2.0 * kPi * hz * i / kSr);
        wsum += w;
    }
    return 2.0 * std::abs(acc) / wsum;
}

// Reads `frames` output frames from a reader at a fixed rate (control blocks of kControl frames).
std::vector<float> readAll(smp::Reader& rd, long frames, double inc) {
    std::vector<float> out(static_cast<std::size_t>(frames), 0.0f);
    for (long k = 0; k < frames; k += smp::kControl) {
        const int n = static_cast<int>(std::min<long>(smp::kControl, frames - k));
        rd.read(out.data() + k, nullptr, n, inc);
    }
    return out;
}

void testCore() {
    std::printf("playback core: stretched kernels, loop until release\n");
    const smp::Kernel& K = smp::Kernel::get();
    check(K.wide(1.0001).stretch >= 1.0001 && K.wide(1.0001).stretch < 1.06 && K.wide(2.0).stretch == 2.0 &&
              K.wide(2.001).stretch > 2.0 && K.wide(100.0).stretch == 8.0 && K.wide(100.0).half == 128,
          "stretched kernels: the next semitone step at or above the pitch ratio, capped at 8x");

    // band-limited saw at 48 kHz: 300 Hz, harmonics up to 23.7 kHz
    std::vector<float> saw(48000);
    for (std::size_t i = 0; i < saw.size(); ++i) {
        double v = 0.0;
        for (int k = 1; k <= 79; ++k) v += std::sin(2.0 * kPi * k * static_cast<double>(i % 160) / 160.0) / k;
        saw[i] = static_cast<float>(0.25 * v);
    }
    const smp::Region sawRegion = smp::makeRegion(&saw, 1, 48000.0, smp::LoopMode::Forward, 0, 48000);
    for (const double inc : {1.03, 1.3, 2.83, 5.3}) {  // off the semitone grid of the stretched kernels
        smp::Reader rd;
        rd.start(sawRegion, 0.0, 48000.0, true);
        const auto m = readAll(rd, sec(0.4), inc);
        const double f0 = 300.0 * inc, fund = tone(m, sec(0.1), 8192, f0);
        double alias = 0.0;
        for (int k = 1; k <= 79; ++k) {
            const double f = k * f0;
            if (f < kSr / 2) continue;
            const double folded = kSr - std::fmod(f, kSr) < kSr / 2 ? kSr - std::fmod(f, kSr) : std::fmod(f, kSr);
            if (folded > 20000.0) continue;  // folds into the transition band above 20 kHz: inaudible
            const double v = tone(m, sec(0.1), 8192, folded);
            alias += v * v;
        }
        check(db(std::sqrt(alias) / fund) < -70.0, fmt("saw read %.2fx faster: aliasing below 20 kHz %.1f dB under the fundamental (limit -70)", inc,
                                                         db(std::sqrt(alias) / fund)));
    }

    // level continuity where the 32-tap kernel hands over to the stretched ones
    const std::vector<float> s5k = sine(5000.0, 48000, 1.0);
    const smp::Region sineRegion = smp::makeRegion(&s5k, 1, 48000.0, smp::LoopMode::None, 0, 0);
    auto level = [&](double inc) {
        smp::Reader rd;
        rd.start(sineRegion, 0.0, 48000.0, false);
        const auto m = readAll(rd, sec(0.5), inc);
        return rms(m, sec(0.1), sec(0.4));
    };
    check(std::fabs(db(level(1.0001) / level(0.9999))) < 0.05, fmt("5 kHz: %.3f dB step between the plain and the stretched kernel",
                                                                   db(level(1.0001) / level(0.9999))));

    // loop until release, released before the loop is reached: plays straight through like an unlooped sample
    std::vector<float> ramp(20000);
    for (std::size_t i = 0; i < ramp.size(); ++i) ramp[i] = static_cast<float>(std::sin(0.01 * static_cast<double>(i)) * (1.0 - i / 20000.0));
    const smp::Region looped = smp::makeRegion(&ramp, 1, 44100.0, smp::LoopMode::Forward, 12000, 12500);
    const smp::Region plain = smp::makeRegion(&ramp, 1, 44100.0, smp::LoopMode::None, 0, 0);
    for (const double inc : {0.9187, 1.7}) {
        smp::Reader a, b;
        a.start(looped, 0.0, 20000.0, true);
        b.start(plain, 0.0, 20000.0, false);
        const auto early = readAll(a, 160, inc);
        a.exitAtWrap = true;  // the note-off, long before the loop at frame 12000
        const auto restA = readAll(a, 24000, inc);  // past the end of the sample at both rates
        const auto allB = readAll(b, 24160, inc);
        bool same = std::equal(early.begin(), early.end(), allB.begin()) && std::equal(restA.begin(), restA.end(), allB.begin() + 160);
        check(same && a.done, fmt("loop until release, released before the loop (%.2fx): plays straight through (identical to no loop)", inc));
    }

    // Loops against the unrolled signal (loop repeated, then the tail) read without a loop through the same
    // kernel: exact while sustaining (also loops shorter than the kernel: the first pass must see the real
    // attack data before loopStart) and, released in pass 5 (loop until release), for the rest of the pass
    // and the tail (as long as the loop is longer than the kernel).
    for (const long len : {7L, 40L, 300L}) {
        for (const double inc : {0.7, 1.0, 2.5, 6.0}) {
            const long pre = 500;
            std::vector<float> data;
            unsigned lcg = 1;
            for (long i = 0; i < pre; ++i) {
                lcg = lcg * 1103515245u + 12345u;
                data.push_back(0.6f * (static_cast<float>((lcg >> 9) & 0xFFFF) / 32768.0f - 1.0f));
            }
            for (long i = 0; i < len; ++i) data.push_back(static_cast<float>(0.5 * std::sin(2.0 * kPi * static_cast<double>(i) / len)));
            for (long i = 0; i < 400; ++i) data.push_back(static_cast<float>(0.3 * std::cos(0.05 * static_cast<double>(i))));
            auto unrolled = [&](long passes) {
                std::vector<float> u(data.begin(), data.begin() + pre + len);
                for (long p = 1; p < passes; ++p) u.insert(u.end(), data.begin() + pre, data.begin() + pre + len);
                u.insert(u.end(), data.begin() + pre + len, data.end());
                return u;
            };
            const smp::Region loop = smp::makeRegion(&data, 1, 48000.0, smp::LoopMode::Forward, pre, pre + len);
            const std::vector<float> longRef = unrolled(400);
            const smp::Region refRegion = smp::makeRegion(&longRef, 1, 48000.0, smp::LoopMode::None, 0, 0);
            smp::Reader a, b;
            a.start(loop, 0.0, static_cast<double>(data.size()), true);
            b.start(refRegion, 0.0, static_cast<double>(longRef.size()), false);
            const long n = static_cast<long>(static_cast<double>(pre + 390 * len) / inc) / 16 * 16;
            const auto x = readAll(a, n, inc), y = readAll(b, n, inc);
            double err = 0.0;
            for (long i = 0; i < n; ++i) err = std::max(err, static_cast<double>(std::fabs(x[static_cast<std::size_t>(i)] - y[static_cast<std::size_t>(i)])));
            check(err < 1e-5, fmt("loop of %ld frames at %.1fx: sustain identical to the unrolled loop (max error %.1e)", len, inc, err));
            {  // ping-pong: forward, then backward without repeating the end points
                std::vector<float> pp(data.begin(), data.begin() + pre + len);
                for (int pass = 0; pass < 200; ++pass) {
                    for (long i = pre + len - 2; i > pre; --i) pp.push_back(data[static_cast<std::size_t>(i)]);
                    pp.insert(pp.end(), data.begin() + pre, data.begin() + pre + len);
                }
                const smp::Region ping = smp::makeRegion(&data, 1, 48000.0, smp::LoopMode::PingPong, pre, pre + len);
                const smp::Region ppRef = smp::makeRegion(&pp, 1, 48000.0, smp::LoopMode::None, 0, 0);
                smp::Reader e, f;
                e.start(ping, 0.0, static_cast<double>(data.size()), true);
                f.start(ppRef, 0.0, static_cast<double>(pp.size()), false);
                const long m = static_cast<long>(static_cast<double>(pre + 190 * (2 * len - 2)) / inc) / 16 * 16;
                const auto xp = readAll(e, m, inc), yp = readAll(f, m, inc);
                double perr = 0.0;
                for (long i = 0; i < m; ++i) perr = std::max(perr, static_cast<double>(std::fabs(xp[static_cast<std::size_t>(i)] - yp[static_cast<std::size_t>(i)])));
                check(perr < 1e-5, fmt("ping-pong loop of %ld frames at %.1fx: identical to the unrolled loop (max error %.1e)", len, inc, perr));
            }

            // released in pass 5 (in its middle / at its very end): that pass is finished, unless the window of
            // the last frame rendered before the release already reached past its loop end; then the next one
            const int half = inc > 1.0 ? smp::Kernel::get().wide(inc).half : smp::kHalf;
            for (const double when : {4.5, 4.98}) {
                const long rel = static_cast<long>(static_cast<double>(pre + when * len) / inc) / 16 * 16;
                const double relPos = static_cast<double>(rel) * inc - pre;
                long passes = static_cast<long>(std::floor(relPos / len)) + 1;
                if (relPos - (passes - 1) * len >= len - half + inc) ++passes;
                smp::Reader c, d;
                c.start(loop, 0.0, static_cast<double>(data.size()), true);
                const std::vector<float> ref5 = unrolled(passes);
                const smp::Region ref5Region = smp::makeRegion(&ref5, 1, 48000.0, smp::LoopMode::None, 0, 0);
                d.start(ref5Region, 0.0, static_cast<double>(ref5.size()), false);
                const long total = rel + static_cast<long>(static_cast<double>(2 * len + 800) / inc) / 16 * 16;
                const auto held = readAll(c, rel, inc);
                c.exitAtWrap = true;
                const auto released = readAll(c, total - rel, inc);
                const auto want = readAll(d, total, inc);
                double relErr = 0.0;
                for (long i = 0; i < total; ++i) {
                    const float got = i < rel ? held[static_cast<std::size_t>(i)] : released[static_cast<std::size_t>(i - rel)];
                    relErr = std::max(relErr, static_cast<double>(std::fabs(got - want[static_cast<std::size_t>(i)])));
                }
                if (len > 2 * half) {
                    check(relErr < 1e-5 && c.done, fmt("loop of %ld frames at %.1fx, released at pass %.2f: rest of pass %ld + tail exact (max error %.1e)",
                                                       len, inc, when + 1.0, passes, relErr));
                }
            }
        }
    }
}

void testStealingAndSpeed() {
    std::printf("voice stealing, mono, speed\n");
    const json sine = {{"file", "soundfonts/GeneralUser-GS.sf2"}, {"sample", "Sine-750Hz"}, {"loop", "forward"}};
    std::vector<Event> chords;
    int id = 0;
    for (int k = 0; k < 8; ++k) {
        for (const int p : {48, 52, 55, 59, 62, 64, 67, 71}) {
            chords.push_back({sec(0.25 * k), true, ++id, p + k % 3, 0.8f});
            chords.push_back({sec(0.25 * k + 0.6), false, id, 0, 0.0f});
        }
    }
    // attack 4 ms: the corner at the end of the default 1 ms linear attack of a pure sine that starts on top of
    // equally loud sines reads as a click to the detector (no energy rise); what is tested here is the 4 ms steal fade
    auto poly = make({{"samples", sine}, {"polyphony", 2}, {"release", 0.3}, {"attack", 0.004}});
    const Audio a = render(*poly, chords, sec(3.0));
    check(clicks(a) == 0 && rms(a.l, sec(0.5), sec(1.5)) > 0.05, "polyphony 2 with 8-note chords: stolen voices fade out click-free");
    std::vector<Event> line;
    for (int k = 0; k < 16; ++k) {
        line.push_back({sec(0.2 * k), true, 100 + k, 48 + (k * 5) % 12, 0.8f});
        line.push_back({sec(0.2 * k + 0.3), false, 100 + k, 0, 0.0f});  // overlapping: legato
    }
    auto mono = make({{"samples", sine}, {"mono", "on"}, {"release", 0.3}, {"attack", 0.004}});
    const Audio m = render(*mono, line, sec(4.0));
    check(clicks(m) == 0 && rms(m.l, sec(0.5), sec(3.0)) > 0.05, "mono: each new note replaces the previous one click-free");

    // 16 voices of a 48 kHz sample played 7..22 semitones above its root (stretched kernels on every voice)
    std::vector<float> saw(96000);
    for (std::size_t i = 0; i < saw.size(); ++i) saw[i] = static_cast<float>(0.2 * (2.0 * static_cast<double>(i % 183) / 183.0 - 1.0));
    const std::string path = writeMono(gTmp / "speed" / "saw.wav", saw, 48000);
    auto s = make({{"samples", {{"file", path}, {"root", 60}, {"loop", "forward"}, {"loopStart", 183 * 100}, {"loopEnd", 183 * 500}}}});
    std::vector<Event> held;
    for (int k = 0; k < 16; ++k) held.push_back({0, true, k + 1, 67 + k, 0.8f});
    const auto t0 = std::chrono::steady_clock::now();
    const Audio h = render(*s, held, sec(10.0));
    const double wall = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    check(rms(h.l, sec(9.0), sec(10.0)) > 0.01 && 10.0 / wall >= 10.0,
          fmt("16 voices transposed up 7-22 semitones: %.0fx realtime (limit 10x)", 10.0 / wall));
}

// ------------------------------------------------------------------------ SFZ zone model (synthetic)

void testSequencesAndTriggers() {
    std::printf("round robin, random layers (preview-stable), first / legato\n");
    const fs::path dir = gTmp / "rr";
    const std::string a = writeWav(dir / "a.wav", sine(440.0, 48000, 0.4), 48000, 16);
    const std::string b = writeWav(dir / "b.wav", sine(550.0, 48000, 0.4), 48000, 16);
    const std::string c = writeWav(dir / "c.wav", sine(660.0, 48000, 0.4), 48000, 16);
    const json rr = {{"samples", json::array({{{"file", a}, {"root", 69}, {"seqLength", 3}, {"seqPosition", 1}},
                                             {{"file", b}, {"root", 69}, {"seqLength", 3}, {"seqPosition", 2}},
                                             {{"file", c}, {"root", 69}, {"seqLength", 3}, {"seqPosition", 3}}})}};
    std::vector<Event> ev;
    for (int k = 0; k < 7; ++k) {
        ev.push_back({sec(0.5 * k), true, k + 1, 69, 1.0f});
        ev.push_back({sec(0.5 * k + 0.3), false, k + 1, 69, 0.0f});
    }
    auto s = make(rr);
    const auto m = render(*s, ev, sec(3.6)).mono();
    std::string got;
    bool ok = true;
    const double want[3] = {440.0, 550.0, 660.0};
    for (int k = 0; k < 7; ++k) {
        const double f = zeroCrossHz(m, sec(0.5 * k + 0.05), sec(0.5 * k + 0.25));
        got += fmt("%.0f ", f);
        ok = ok && std::fabs(f - want[k % 3]) < 1.0;
    }
    check(ok, "seqLength 3: successive notes cycle through the 3 zones: " + got);
    // velocity outside a zone's range does not advance its counter
    const json layered = {{"samples", json::array({{{"file", a}, {"root", 69}, {"seqLength", 2}, {"seqPosition", 1}, {"velhi", 63}},
                                                  {{"file", b}, {"root", 69}, {"seqLength", 2}, {"seqPosition", 2}, {"velhi", 63}},
                                                  {{"file", c}, {"root", 69}, {"vello", 64}}})}};
    auto l = make(layered);
    const auto lm = render(*l, {{0, true, 1, 69, 0.3f}, {sec(0.3), false, 1, 69, 0}, {sec(0.5), true, 2, 69, 0.9f}, {sec(0.8), false, 2, 69, 0},
                                {sec(1.0), true, 3, 69, 0.3f}, {sec(1.3), false, 3, 69, 0}}, sec(1.5)).mono();
    const double f1 = zeroCrossHz(lm, sec(0.05), sec(0.25)), f2 = zeroCrossHz(lm, sec(0.55), sec(0.75)), f3 = zeroCrossHz(lm, sec(1.05), sec(1.25));
    check(std::fabs(f1 - 440) < 1 && std::fabs(f2 - 660) < 1 && std::fabs(f3 - 550) < 1,
          fmt("counters advance only when the zone matches: soft %.0f, loud %.0f, soft %.0f Hz (440 660 550)", f1, f2, f3));

    // random layers: exactly one of two zones per note, both used, deterministic, identical in a preview render
    const json rnd = {{"samples", json::array({{{"file", a}, {"root", 69}, {"hirand", 0.5}, {"release", 0.005}},
                                              {{"file", b}, {"root", 69}, {"lorand", 0.5}, {"release", 0.005}}})}};
    std::vector<Event> notes;
    for (int k = 0; k < 40; ++k) {
        notes.push_back({sec(0.1 * k), true, k + 1, 69, 1.0f});
        notes.push_back({sec(0.1 * k + 0.08), false, k + 1, 69, 0.0f});
    }
    auto r1 = make(rnd), r2 = make(rnd);
    const Audio x = render(*r1, notes, sec(4.2)), y = render(*r2, notes, sec(4.2), 0);
    const auto xm = x.mono();
    int lowCount = 0, highCount = 0, bad = 0;
    for (int k = 0; k < 40; ++k) {
        const double p440 = tone(xm, sec(0.1 * k + 0.01), 2048, 440.0), p550 = tone(xm, sec(0.1 * k + 0.01), 2048, 550.0);
        if (p440 > 0.2 && p550 < 0.02) ++lowCount;
        else if (p550 > 0.2 && p440 < 0.02) ++highCount;
        else ++bad;
    }
    check(bad == 0 && lowCount >= 10 && highCount >= 10 && x.l == y.l,
          fmt("lorand/hirand: one layer per note (%d low, %d high, %d mixed), deterministic", lowCount, highCount, bad));
    // preview: an instance starting at song beat 2 (1 s at 120 bpm) draws the same layers for the same notes
    auto pv = make(rnd, kSr, 2.0);
    std::vector<Event> later;
    for (const auto& e : notes) {
        if (e.at >= sec(1.0)) later.push_back({e.at - sec(1.0), e.on, e.id, e.pitch, e.vel});
    }
    const Audio p = render(*pv, later, sec(3.2));
    bool same = true;
    for (long i = 0; i < sec(3.2); ++i) same = same && p.l[static_cast<std::size_t>(i)] == x.l[static_cast<std::size_t>(i + sec(1.0))];
    check(same, "a preview render (startBeat 2) picks the same random layer for every note as the full render");

    // first / legato: a note while another key is held plays the legato zone
    const json fl = {{"samples", json::array({{{"file", a}, {"root", 69}, {"trigger", "first"}}, {{"file", c}, {"root", 69}, {"trigger", "legato"}}})}};
    auto t = make(fl);
    const auto tm = render(*t, {{0, true, 1, 69, 1.0f}, {sec(0.3), true, 2, 69, 1.0f}, {sec(0.35), false, 1, 69, 0}, {sec(0.6), false, 2, 69, 0},
                                {sec(1.0), true, 3, 69, 1.0f}, {sec(1.3), false, 3, 69, 0}}, sec(1.6)).mono();
    const double g1 = zeroCrossHz(tm, sec(0.05), sec(0.25)), g3 = zeroCrossHz(tm, sec(1.05), sec(1.25));
    const double legatoPart = tone(tm, sec(0.4), 4096, 660.0), firstPart = tone(tm, sec(0.4), 4096, 440.0);
    check(std::fabs(g1 - 440) < 1 && std::fabs(g3 - 440) < 1 && legatoPart > 0.1 && firstPart < 0.01,
          fmt("first / legato: alone %.0f Hz, overlapping -> legato zone (660 Hz %.2f, 440 Hz %.3f), alone again %.0f Hz", g1,
              legatoPart, firstPart, g3));
}

void testReleaseAndPedal() {
    std::printf("release triggers, rt_decay, sustain pedal, note polyphony\n");
    const fs::path dir = gTmp / "rel";
    const std::string tone440 = writeWav(dir / "tone.wav", sine(440.0, 48000, 3.0), 48000, 16);
    auto relTone = sine(1320.0, 48000, 0.3, 0.4);
    for (std::size_t i = 0; i < 2400; ++i) relTone[relTone.size() - 1 - i] *= static_cast<float>(i / 2400.0);  // 50 ms fade-out
    const std::string rel = writeWav(dir / "rel.wav", relTone, 48000, 16);
    const json cfg = {{"samples", json::array({{{"file", tone440}, {"root", 69}, {"release", 0.02}},
                                              {{"file", rel}, {"root", 69}, {"pitchKeytrack", 0}, {"trigger", "release"}, {"rtDecay", 20}}})}};
    auto shortNote = make(cfg), longNote = make(cfg);
    const auto s = render(*shortNote, {{0, true, 1, 69, 1.0f}, {sec(0.25), false, 1, 69, 0}}, sec(0.8)).mono();
    const auto l = render(*longNote, {{0, true, 1, 69, 1.0f}, {sec(0.75), false, 1, 69, 0}}, sec(1.3)).mono();
    const double before = tone(s, sec(0.05), 4096, 1320.0), rs = tone(s, sec(0.3), 4096, 1320.0), rl = tone(l, sec(0.8), 4096, 1320.0);
    check(before < 1e-3 && rs > 0.05 && std::fabs(db(rs / rl) - 10.0) < 0.3,
          fmt("release zone plays at note-off; rtDecay 20 dB/s: held 0.25 s vs 0.75 s = %.2f dB apart (10)", db(rs / rl)));

    // sustain pedal: the note rings on after its note-off, the release zone fires at pedal-up
    auto ped = make(cfg);
    const auto p = render(*ped, {setAt(0, "pedal", 1.0f), {sec(0.05), true, 1, 69, 1.0f}, {sec(0.25), false, 1, 69, 0},
                                 setAt(sec(1.0), "pedal", 0.0f)}, sec(1.6)).mono();
    const double ringing = tone(p, sec(0.6), 4096, 440.0), after = tone(p, sec(1.2), 4096, 440.0);
    const double relEarly = tone(p, sec(0.3), 4096, 1320.0), relAtUp = tone(p, sec(1.02), 4096, 1320.0);
    check(ringing > 0.2 && after < 1e-3 && relEarly < 1e-3 && relAtUp > 0.01 && clicks(Audio{p, p}) == 0,
          fmt("pedal down: rings after the note-off (%.2f), released at pedal-up (%.1e after), release sample at pedal-up (%.3f) "
              "not at the note-off (%.1e)", ringing, after, relAtUp, relEarly));
    // re-striking a held key: the old voice rings on and a new one starts (two voices)
    auto re = make({{"samples", {{"file", tone440}, {"root", 69}, {"release", 0.02}}}});
    const auto r = render(*re, {setAt(0, "pedal", 1.0f), {0, true, 1, 69, 1.0f}, {sec(0.2), false, 1, 69, 0}, {sec(0.5), true, 2, 69, 1.0f},
                                {sec(0.6), false, 2, 69, 0}}, sec(1.0)).mono();
    const double one = rms(r, sec(0.3), sec(0.45)), two = rms(r, sec(0.7), sec(0.9));
    check(two > 1.2 * one, fmt("re-struck under the pedal: the old note rings on under the new one (rms %.3f -> %.3f)", one, two));
    // note polyphony 1 turns the re-struck key's old voice off; pedal=false zones ignore the pedal
    auto np = make({{"samples", {{"file", tone440}, {"root", 69}, {"release", 0.02}, {"notePolyphony", 1}}}});
    const auto q = render(*np, {setAt(0, "pedal", 1.0f), {0, true, 1, 69, 1.0f}, {sec(0.2), false, 1, 69, 0}, {sec(0.5), true, 2, 69, 1.0f},
                                {sec(0.6), false, 2, 69, 0}}, sec(1.0)).mono();
    const double q1 = rms(q, sec(0.3), sec(0.45)), q2 = rms(q, sec(0.7), sec(0.9));
    auto deaf = make({{"samples", {{"file", tone440}, {"root", 69}, {"release", 0.02}, {"pedal", false}}}});
    const auto d = render(*deaf, {setAt(0, "pedal", 1.0f), {0, true, 1, 69, 1.0f}, {sec(0.2), false, 1, 69, 0}}, sec(0.6)).mono();
    check(std::fabs(db(q2 / q1)) < 1.5 && rms(d, sec(0.4), sec(0.6)) < 1e-4,
          fmt("notePolyphony 1: the re-strike replaces the old voice (%.2f dB); pedal=false zones ignore the pedal", db(q2 / q1)));
}

void testSympatheticAndHalfPedal() {
    std::printf("sympathetic string resonance, half pedal\n");
    // a piano-like note: six harmonics of C4, decaying (the sample spreads over the keyboard)
    const double f4 = 261.6256;
    std::vector<float> note(static_cast<std::size_t>(48000 * 4));
    for (std::size_t i = 0; i < note.size(); ++i) {
        const double t = static_cast<double>(i) / 48000.0;
        double v = 0.0;
        for (int h = 1; h <= 6; ++h) v += std::sin(2.0 * kPi * f4 * h * t) / h;
        note[i] = static_cast<float>(0.25 * v * std::exp(-t / 1.6) * std::min(1.0, t / 0.002));
    }
    const fs::path dir = gTmp / "symp";
    const std::string file = writeWav(dir / "c4.wav", note, 48000, 24);
    auto cfg = [&](double symp) {
        return json{{"samples", {{"file", file}, {"root", 60}, {"release", 0.03}, {"vello", 2}}}, {"sympathetic", symp},
                    {"polyphony", 16}};
    };
    auto diff = [](const Audio& a, const Audio& b) {
        std::vector<float> d(a.l.size());
        for (std::size_t i = 0; i < d.size(); ++i) d[i] = 0.5f * ((a.l[i] + a.r[i]) - (b.l[i] + b.r[i]));
        return d;
    };
    // pedal down, C4 struck and released: the strings of its harmonics' keys ring (C3 through its 2nd harmonic, C5, G5 ...)
    const std::vector<Event> ev = {setAt(0, "pedal", 1.0f), {sec(0.05), true, 1, 60, 0.8f}, {sec(0.3), false, 1, 60, 0},
                                   setAt(sec(1.6), "pedal", 0.0f)};
    auto dry = make(cfg(0.0)), wet = make(cfg(0.6)), wet2 = make(cfg(0.6)), plain = make(cfg(0.0));
    const Audio d0 = render(*dry, ev, sec(2.2)), d1 = render(*wet, ev, sec(2.2), 0), d2 = render(*wet2, ev, sec(2.2));
    auto plainCfg = cfg(0.0);
    plainCfg.erase("sympathetic");
    auto pl = make(plainCfg);
    const Audio d3 = render(*pl, ev, sec(2.2));
    check(d0.l == d3.l && d0.r == d3.r, "sympathetic 0 is the plain sampler (bit-identical)");
    check(d1.l == d2.l && d1.r == d2.r, "sympathetic resonance is deterministic and block-size independent");
    const auto res = diff(d1, d0);
    const auto dm = d0.mono();
    const double dryLate = rms(dm, sec(1.2), sec(1.5)), resLate = rms(res, sec(1.2), sec(1.5));
    const double resUp = rms(res, sec(1.75), sec(1.95));
    check(resLate > dryLate * 0.03 && resLate < dryLate * 1.5 && resUp < resLate * 0.02,
          fmt("pedal down: the halo rings %.1f dB re the note after 1.2 s; pedal up damps it (%.1f dB in 0.15 s)",
              db(resLate / dryLate), db(resUp / resLate)));
    check(clicks(d1) == 0, "no clicks from the strings (pedal down / up)");
    // pedal up, C3 held down silently (velocity 1 plays no zone): struck C4 staccato makes its string ring on
    const std::vector<Event> held = {{0, true, 9, 48, 1.0f / 127.0f}, {sec(0.1), true, 1, 60, 0.8f}, {sec(0.3), false, 1, 60, 0}};
    const std::vector<Event> none = {{sec(0.1), true, 1, 60, 0.8f}, {sec(0.3), false, 1, 60, 0}};
    auto h1 = make(cfg(0.6)), h0 = make(cfg(0.6));
    const auto hm = render(*h1, held, sec(1.4)).mono(), nm = render(*h0, none, sec(1.4)).mono();
    const double ringHeld = rms(hm, sec(0.5), sec(0.9)), ringNone = rms(nm, sec(0.5), sec(0.9));
    // the held C3 string answers C4 in its 2nd mode: in tune (C4 = its 2nd harmonic), not 30 cents beside it
    const double on = tone(hm, sec(0.45), 32768, f4);
    const double off = std::max(tone(hm, sec(0.45), 32768, f4 * std::exp2(60 / 1200.0)),
                                tone(hm, sec(0.45), 32768, f4 * std::exp2(-60 / 1200.0)));
    check(ringHeld > 20.0 * std::max(ringNone, 1e-7) && on > 4.0 * off,
          fmt("a silently held key's string rings after the staccato (%.1e vs %.1e without it), in tune (%.1e vs %.1e 60 ct "
              "off)", ringHeld, ringNone, on, off));

    // half pedal: pedal-held notes decay faster, the bass less than the treble
    auto hp = [&](float pedal, int key) {
        auto s = make(cfg(0.0));
        const auto a = render(*s, {setAt(0, "pedal", pedal), {sec(0.05), true, 1, key, 0.8f}, {sec(0.2), false, 1, key, 0}}, sec(1.4)).mono();
        return rms(a, sec(1.1), sec(1.3)) / rms(a, sec(0.1), sec(0.2));
    };
    const double fullC6 = hp(1.0f, 72), halfC6 = hp(0.75f, 72), fullC2 = hp(1.0f, 36), halfC2 = hp(0.75f, 36);
    const double lossC6 = db(fullC6 / halfC6), lossC2 = db(fullC2 / halfC2);
    check(lossC6 > 4.0 && lossC6 < 12.0 && lossC2 > 1.5 && lossC2 < lossC6 * 0.75,
          fmt("half pedal 0.75: pedal-held notes lose %.1f dB (C5) / %.1f dB (C2) more after 1.1 s than with the full pedal",
              lossC6, lossC2));
}

void testRestrike() {
    std::printf("re-strike damping (restrike)\n");
    // a drum-like hit: decaying noise (a ringing head: hits add in power, not in phase), one-shot
    std::vector<float> hit(static_cast<std::size_t>(48000 * 2.5));
    unsigned seed = 12345u;
    for (std::size_t i = 0; i < hit.size(); ++i) {
        const double t = static_cast<double>(i) / 48000.0;
        seed = seed * 1664525u + 1013904223u;
        const double n = static_cast<double>(seed >> 8) / 8388608.0 - 1.0;
        hit[i] = static_cast<float>(0.3 * n * std::exp(-t / 0.8) * std::min(1.0, t / 0.001));
    }
    const std::string file = writeWav(gTmp / "restrike" / "tom.wav", hit, 48000, 24);
    auto cfg = [&](double rs) {
        return json{{"samples", {{"file", file}, {"root", 45}, {"loop", "oneshot"}}}, {"restrike", rs}, {"polyphony", 32}};
    };
    // a 16th-note run on one drum (8 strokes, 125 ms apart), then silence
    std::vector<Event> run;
    for (int k = 0; k < 8; ++k) run.push_back({sec(0.125 * k), true, k + 1, 45, 0.8f});
    std::vector<Event> one = {{sec(0.875), true, 1, 45, 0.8f}};
    auto plain = make(cfg(0.0)), damped = make(cfg(9.0)), damped2 = make(cfg(9.0)), single = make(cfg(9.0));
    auto bareCfg = cfg(0.0);
    bareCfg.erase("restrike");
    auto bare = make(bareCfg);
    const Audio p = render(*plain, run, sec(1.6)), d = render(*damped, run, sec(1.6)), d2 = render(*damped2, run, sec(1.6), 0);
    const Audio b = render(*bare, run, sec(1.6));
    const Audio o = render(*single, one, sec(1.6));
    check(p.l == b.l && p.r == b.r, "restrike 0 is the plain sampler (bit-identical)");
    check(d.l == d2.l && d.r == d2.r, "restrike is deterministic and block-size independent");
    const auto pm = p.mono(), dm = d.mono(), om = o.mono();
    // after the last stroke: the plain run rings with every earlier hit on top; damped it is close to one hit
    const double pl = rms(pm, sec(0.95), sec(1.3)), dl = rms(dm, sec(0.95), sec(1.3)), ol = rms(om, sec(0.95), sec(1.3));
    check(db(pl / ol) > 4.0 && db(dl / ol) < 2.0 && db(dl / ol) > 0.0,
          fmt("a run's ring: plain %+.1f dB over one hit, restrike 9 dB %+.1f dB", db(pl / ol), db(dl / ol)));
    // the new stroke's attack is not damped (the first 10 ms after the last strike)
    const double pa = rms(om, sec(0.876), sec(0.886)), da = rms(dm, sec(0.876), sec(0.886));
    check(da > pa * 0.95, fmt("the new stroke keeps its attack (%.3f vs a single hit %.3f)", da, pa));
    check(clicks(d) == 0, "no clicks from the damping glide");
    check(rejects(cfg(30.0), "restrike"), "restrike above 24 dB is rejected");
}

void testGroupsAndGenerators() {
    std::printf("groups (off_by), off modes, *silence / *sine / *noise\n");
    const fs::path dir = gTmp / "groups";
    std::vector<float> noise(96000);
    std::uint32_t rng = 7;
    for (auto& v : noise) {
        rng = rng * 1664525u + 1013904223u;
        v = 0.2f * static_cast<float>((rng >> 8) * (1.0 / 8388608.0) - 1.0);
    }
    const std::string open = writeWav(dir / "open.wav", noise, 48000, 16);
    const std::string closed = writeWav(dir / "closed.wav", std::vector<float>(noise.begin(), noise.begin() + 4800), 48000, 16);
    auto kit = [&](const char* mode) {
        return json{{"samples", json::array({{{"file", open}, {"lo", 46}, {"hi", 46}, {"pitchKeytrack", 0}, {"group", 2}, {"offBy", 1},
                                              {"offMode", mode}, {"release", 0.2}, {"loop", "oneshot"}},
                                             {{"file", closed}, {"lo", 42}, {"hi", 42}, {"pitchKeytrack", 0}, {"group", 1}, {"loop", "oneshot"}},
                                             {{"file", "*silence"}, {"lo", 40}, {"hi", 40}, {"group", 1}}})}};
    };
    auto ring = make(kit("fast"));
    const auto o = render(*ring, {{0, true, 1, 46, 1.0f}}, sec(1.0)).mono();
    auto cut = make(kit("fast"));
    const auto c = render(*cut, {{0, true, 1, 46, 1.0f}, {sec(0.4), true, 2, 42, 1.0f}}, sec(1.0)).mono();
    auto slow = make(kit("normal"));
    const auto n = render(*slow, {{0, true, 1, 46, 1.0f}, {sec(0.4), true, 2, 42, 1.0f}}, sec(1.0)).mono();
    auto mute = make(kit("fast"));
    const auto m = render(*mute, {{0, true, 1, 46, 1.0f}, {sec(0.4), true, 2, 40, 1.0f}}, sec(1.0)).mono();
    const double ref = rms(o, sec(0.5), sec(0.9));
    check(ref > 0.05 && rms(c, sec(0.51), sec(0.9)) < 1e-4 && clicks(Audio{c, c}) == 0,
          fmt("off_by: the closed hat (group 1) fades the open hat (offBy 1) in 5 ms: tail after the closed hat %.1f dB, no clicks",
              db(rms(c, sec(0.51), sec(0.9)) / ref)));
    check(rms(n, sec(0.45), sec(0.5)) > 0.2 * ref && rms(n, sec(0.75), sec(0.9)) < 0.01 * ref,
          "offMode normal: the turned-off voice fades with its own release (0.2 s)");
    check(rms(m, sec(0.41), sec(0.9)) < 1e-4, "a *silence zone of group 1 turns the open hat off (mute groups)");
    // generators: *sine plays A4 at key 69; *noise is broadband
    auto sn = make({{"samples", {{"file", "*sine"}}}});
    const auto sm = render(*sn, {{0, true, 1, 69, 1.0f}}, sec(0.5)).mono();
    auto nz = make({{"samples", {{"file", "*noise"}}}});
    const auto nm = render(*nz, {{0, true, 1, 60, 1.0f}}, sec(0.5)).mono();
    check(std::fabs(cents(zeroCrossHz(sm, sec(0.1), sec(0.45)), 440.0)) < 1.0 && rms(nm, sec(0.1), sec(0.4)) > 0.2,
          fmt("*sine at key 69: %.2f Hz; *noise rms %.2f", zeroCrossHz(sm, sec(0.1), sec(0.45)), rms(nm, sec(0.1), sec(0.4))));
}

void testZoneShaping() {
    std::printf("offset / end, key tracking, velocity curves, crossfades, envelopes, filters, EQ\n");
    const fs::path dir = gTmp / "shape";
    std::vector<float> late(9600, 0.0f);
    const auto t440 = sine(440.0, 48000, 1.0);
    late.insert(late.end(), t440.begin(), t440.end());
    const std::string lp = writeWav(dir / "late.wav", late, 48000, 16);
    const std::string a = writeWav(dir / "a.wav", sine(440.0, 48000, 1.0), 48000, 16);
    const std::string b = writeWav(dir / "b.wav", sine(660.0, 48000, 1.0), 48000, 16);
    const std::string k1 = writeWav(dir / "k1.wav", sine(1000.0, 48000, 1.0, 0.25), 48000, 16);
    auto one = [&](const json& zone, int key, float vel, long len = sec(0.6), long off = -1) {
        auto s = make({{"samples", zone}});
        std::vector<Event> ev{{0, true, 1, key, vel}};
        if (off >= 0) ev.push_back({off, false, 1, key, 0});
        return render(*s, ev, len).mono();
    };
    const auto o = one({{"file", lp}, {"root", 69}, {"offset", 9600}}, 69, 1.0f, sec(0.2));
    const auto e = one({{"file", a}, {"root", 69}, {"end", 24000}}, 69, 1.0f, sec(0.8));
    check(rms(o, sec(0.01), sec(0.15)) > 0.2 && rms(e, sec(0.1), sec(0.45)) > 0.2 && rms(e, sec(0.52), sec(0.8)) < 1e-4,
          "offset 9600 skips the silent head; end 24000 stops the sample at 0.5 s");
    const auto kt = one({{"file", a}, {"root", 69}, {"pitchKeytrack", 0}}, 81, 1.0f);
    const auto half = one({{"file", a}, {"root", 69}, {"pitchKeytrack", 50}}, 81, 1.0f);
    check(std::fabs(zeroCrossHz(kt, sec(0.1), sec(0.5)) - 440.0) < 0.5 && std::fabs(cents(zeroCrossHz(half, sec(0.1), sec(0.5)), 440.0) - 600.0) < 1.0,
          "pitchKeytrack 0: every key at the root pitch; 50 ct/key: an octave up is a tritone");
    // velocity: ampVeltrack 0 = flat, a velcurve point [64, 1] = full level from velocity 64 (linear below)
    const double flat30 = rms(one({{"file", a}, {"root", 69}, {"ampVeltrack", 0}}, 69, 30.0f / 127.0f), sec(0.1), sec(0.5));
    const double flat127 = rms(one({{"file", a}, {"root", 69}, {"ampVeltrack", 0}}, 69, 1.0f), sec(0.1), sec(0.5));
    const double c64 = rms(one({{"file", a}, {"root", 69}, {"velcurve", {{64, 1}}}}, 69, 64.0f / 127.0f), sec(0.1), sec(0.5));
    const double c32 = rms(one({{"file", a}, {"root", 69}, {"velcurve", {{64, 1}}}}, 69, 32.0f / 127.0f), sec(0.1), sec(0.5));
    const double half64 = rms(one({{"file", a}, {"root", 69}, {"ampVeltrack", 0.5}}, 69, 64.0f / 127.0f), sec(0.1), sec(0.5));
    check(std::fabs(db(flat30 / flat127)) < 0.01 && std::fabs(db(c64 / flat127)) < 0.05 && std::fabs(db(c32 / c64) + 6.02) < 0.1 &&
              std::fabs(half64 / flat127 - (1.0 - 0.5 * (1.0 - std::pow(64.0 / 127.0, 2.0)))) < 0.01,
          fmt("ampVeltrack 0 flat; velcurve [64, 1]: vel 64 full, vel 32 %.2f dB; ampVeltrack 0.5 at vel 64: %.3f", db(c32 / c64), half64 / flat127));
    // velocity crossfade (equal power): 440 Hz fades out, 660 Hz fades in over velocity 40..80
    const json xf = json::array({{{"file", a}, {"root", 69}, {"xfoutLo", 40}, {"xfoutHi", 80}}, {{"file", b}, {"root", 69}, {"xfinLo", 40}, {"xfinHi", 80}}});
    auto level = [&](int vel, double hz) {
        const auto mm = one(xf, 69, static_cast<float>(vel) / 127.0f);
        return tone(mm, sec(0.1), 8192, hz) / std::pow(static_cast<double>(vel) / 127.0, 2.0);
    };
    const double lo440 = level(30, 440), lo660 = level(30, 660), mid440 = level(60, 440), mid660 = level(60, 660), hi440 = level(100, 440);
    check(lo660 < 1e-3 && hi440 < 1e-3 && std::fabs(db(mid440 / lo440) + 3.01) < 0.05 && std::fabs(db(mid660 / lo440) + 3.01) < 0.05,
          fmt("velocity crossfade: vel 30 only 440, vel 100 only 660, midway both %.2f / %.2f dB (equal power -3.01)", db(mid440 / lo440),
              db(mid660 / lo440)));
    // per-zone envelope: attack 0.1, hold 0.1, decay 0.1 to sustain 0.5, release 0.2 (60 dB)
    const auto env = one({{"file", a}, {"root", 69}, {"attack", 0.1}, {"hold", 0.1}, {"decay", 0.1}, {"sustain", 0.5}, {"release", 0.2}}, 69, 1.0f,
                         sec(1.0), sec(0.6));
    const double full = 0.25;  // sine 0.5 peak: rms 0.354, -3 dB centre pan
    const double at50 = rms(env, sec(0.045), sec(0.055)) / full, holdL = rms(env, sec(0.12), sec(0.19)) / full;
    const double sus = rms(env, sec(0.45), sec(0.55)) / full, rel = rms(env, sec(0.8), sec(0.9)) / full;
    check(std::fabs(at50 - 0.5) < 0.06 && std::fabs(holdL - 1.0) < 0.02 && std::fabs(sus - 0.5) < 0.02 && rel < 0.01,
          fmt("zone envelope: attack half-way %.2f, hold %.2f, sustain %.2f, released %.4f", at50, holdL, sus, rel));
    // zone filters and EQ on a 1 kHz tone
    auto tone1k = [&](const json& extra) {
        json z = {{"file", k1}, {"root", 60}, {"pitchKeytrack", 0}};
        for (auto it = extra.begin(); it != extra.end(); ++it) z[it.key()] = it.value();
        return tone(one(z, 60, 1.0f), sec(0.2), 8192, 1000.0);
    };
    const double dry = tone1k(json::object());
    const double lp2 = db(tone1k({{"cutoff", 200}}) / dry), hp2 = db(tone1k({{"filter", "hpf_2p"}, {"cutoff", 5000}}) / dry);
    const double lp1 = db(tone1k({{"filter", "lpf_1p"}, {"cutoff", 200}}) / dry), eq = db(tone1k({{"eq", {{1000, 1, 12}}}}) / dry);
    const double kt2 = db(tone1k({{"cutoff", 200}, {"filKeytrack", 100}, {"filKeycenter", 36}}) / dry);
    check(lp2 < -25 && lp2 > -31 && hp2 < -25 && hp2 > -31 && lp1 < -12 && lp1 > -16 && std::fabs(eq - 12.0) < 0.2 && kt2 > -3,
          fmt("zone filter at 1 kHz: lpf_2p 200 Hz %.1f dB, hpf_2p 5 kHz %.1f, lpf_1p 200 Hz %.1f, eq +12 dB -> %.2f, key tracked "
              "2 octaves up %.1f", lp2, hp2, lp1, eq, kt2));
    // filter envelope: +4 octaves (200 Hz -> 3.2 kHz) for 0.3 s, then a 0.1 s decay down to the filter's own cutoff
    auto fe = make({{"samples", {{"file", k1}, {"root", 60}, {"pitchKeytrack", 0}, {"cutoff", 200},
                                 {"filterEnv", {4800, 0, 0, 0.3, 0.1, 0, 0.1}}}}});
    const auto fm = render(*fe, {{0, true, 1, 60, 1.0f}}, sec(1.0)).mono();
    auto plainLp = make({{"samples", {{"file", k1}, {"root", 60}, {"pitchKeytrack", 0}}}});
    const auto pm = render(*plainLp, {{0, true, 1, 60, 1.0f}}, sec(1.0)).mono();
    const double open = db(tone(fm, sec(0.05), 8192, 1000.0) / tone(pm, sec(0.05), 8192, 1000.0));
    const double shut = db(tone(fm, sec(0.7), 8192, 1000.0) / tone(pm, sec(0.7), 8192, 1000.0));
    check(open > -1.0 && shut < -25.0 && clicks(Audio{fm, fm}) == 0,
          fmt("filter envelope: open while it holds (%.1f dB at 1 kHz), back at the zone cutoff after its decay (%.1f dB)", open, shut));
}

void testRandomDelayLfo() {
    std::printf("per-note randomness, start delay, vibrato / tremolo, zone width\n");
    const fs::path dir = gTmp / "rnd";
    const std::string a = writeWav(dir / "a.wav", sine(440.0, 48000, 1.5), 48000, 16);
    std::vector<Event> ev;
    for (int k = 0; k < 12; ++k) {
        ev.push_back({sec(0.25 * k), true, k + 1, 69, 1.0f});
        ev.push_back({sec(0.25 * k + 0.2), false, k + 1, 69, 0.0f});
    }
    const json pr = {{"samples", {{"file", a}, {"root", 69}, {"pitchRandom", 50}, {"ampRandom", 6}, {"release", 0.01}}}};
    auto r1 = make(pr), r2 = make(pr);
    const auto x = render(*r1, ev, sec(3.1)).mono(), y = render(*r2, ev, sec(3.1)).mono();
    double lo = 1e9, hi = -1e9, glo = 1e9, ghi = -1e9;
    for (int k = 0; k < 12; ++k) {
        const double c = cents(zeroCrossHz(x, sec(0.25 * k + 0.02), sec(0.25 * k + 0.18)), 440.0);
        const double g = db(rms(x, sec(0.25 * k + 0.02), sec(0.25 * k + 0.18)) / 0.25);
        lo = std::min(lo, c);
        hi = std::max(hi, c);
        glo = std::min(glo, g);
        ghi = std::max(ghi, g);
    }
    check(x == y && lo >= -50.5 && hi <= 50.5 && hi - lo > 30 && glo >= -0.1 && ghi <= 6.1 && ghi - glo > 1.5,
          fmt("pitchRandom 50: %.0f..%+.0f ct; ampRandom 6: %+.1f..%+.1f dB; deterministic", lo, hi, glo, ghi));
    auto dl = make({{"samples", {{"file", a}, {"root", 69}, {"delay", 0.1}}}});
    const auto d = render(*dl, {{0, true, 1, 69, 1.0f}}, sec(0.3)).mono();
    check(rms(d, 0, sec(0.099)) == 0.0 && rms(d, sec(0.11), sec(0.3)) > 0.2, "delay 0.1 s: the zone starts 100 ms after the note-on");
    auto vib = make({{"samples", {{"file", a}, {"root", 69}, {"vibrato", {50, 5, 0, 0}}}}});
    const auto v = render(*vib, {{0, true, 1, 69, 1.0f}}, sec(1.2)).mono();
    double vlo = 1e9, vhi = -1e9;
    for (long t = sec(0.1); t + sec(0.02) < sec(1.1); t += sec(0.01)) {
        const double c = cents(zeroCrossHz(v, t, t + sec(0.02)), 440.0);
        vlo = std::min(vlo, c);
        vhi = std::max(vhi, c);
    }
    auto trem = make({{"samples", {{"file", a}, {"root", 69}, {"tremolo", {6, 4, 0.2, 0}}}}});
    const auto tr = render(*trem, {{0, true, 1, 69, 1.0f}}, sec(1.2)).mono();
    double tlo = 1e9, thi = -1e9;
    for (long t = sec(0.3); t + sec(0.01) < sec(1.1); t += sec(0.005)) {
        const double g = db(rms(tr, t, t + sec(0.01)) / 0.25);
        tlo = std::min(tlo, g);
        thi = std::max(thi, g);
    }
    const double still = db(rms(tr, sec(0.05), sec(0.19)) / 0.25);
    check(vlo > -60 && vlo < -40 && vhi > 40 && vhi < 60 && tlo < -5 && thi > 5 && std::fabs(still) < 0.1 && clicks(Audio{v, v}) == 0,
          fmt("vibrato 50 ct 5 Hz: %.0f..%+.0f ct; tremolo 6 dB after 0.2 s: %.1f..%+.1f dB (before: %+.2f)", vlo, vhi, tlo, thi, still));
    const std::string st = writeStereo(dir / "st.wav", sine(441.0, 44100, 0.5, 0.5), std::vector<float>(22050, 0.0f), 44100);
    auto narrow = make({{"samples", {{"file", st}, {"root", 69}, {"width", 0}}}});
    const Audio w = render(*narrow, {{0, true, 1, 69, 1.0f}}, sec(0.4));
    double diff = 0.0;
    for (std::size_t i = 0; i < w.l.size(); ++i) diff = std::max(diff, static_cast<double>(std::fabs(w.l[i] - w.r[i])));
    check(diff < 1e-6 && rms(w.l, sec(0.1), sec(0.3)) > 0.1, "zone width 0 folds its stereo file to mono");
}

void testStorageAndFiles() {
    std::printf("16-bit storage, smpl chunk loops and root, shared files, parallel loading\n");
    const fs::path dir = gTmp / "store";
    // the same integers as 16-bit PCM and as float (k / 32768): bit-identical playback, half the memory
    std::vector<float> ints(48000), exact(48000);
    for (std::size_t i = 0; i < ints.size(); ++i) {
        const auto k = static_cast<int>(std::lround(12000.0 * std::sin(2.0 * kPi * 523.25 * static_cast<double>(i) / 48000.0) +
                                                    3000.0 * std::sin(2.0 * kPi * 3100.0 * static_cast<double>(i) / 48000.0)));
        ints[i] = static_cast<float>(k) / 32767.0f;
        exact[i] = static_cast<float>(k) / 32768.0f;
    }
    const std::string p16 = writeWav(dir / "i16.wav", ints, 48000, 16), p32 = writeWav(dir / "f32.wav", exact, 48000, 32);
    const std::uint64_t m0 = smp::cachedSampleBytes();
    auto s16 = make({{"samples", {{"file", p16}, {"root", 60}}}});
    const std::uint64_t m1 = smp::cachedSampleBytes();
    auto s32 = make({{"samples", {{"file", p32}, {"root", 60}}}});
    const std::uint64_t m2 = smp::cachedSampleBytes();
    const std::vector<Event> ev{{0, true, 1, 67, 0.9f}, {sec(0.3), false, 1, 67, 0}};
    const Audio a = render(*s16, ev, sec(0.6)), b = render(*s32, ev, sec(0.6));
    check(a.l == b.l && a.r == b.r && (m1 - m0) * 10 < (m2 - m1) * 6,
          fmt("16-bit file: bit-identical to its float copy (7 st up), %.0f vs %.0f KB in memory", static_cast<double>(m1 - m0) / 1024.0,
              static_cast<double>(m2 - m1) / 1024.0));
    const std::string z24 = writeWav(dir / "z24.wav", ints, 48000, 24, nullptr, true), t24 = writeWav(dir / "t24.wav", ints, 48000, 24);
    const std::uint64_t n0 = smp::cachedSampleBytes();
    make({{"samples", {{"file", z24}}}});
    const std::uint64_t n1 = smp::cachedSampleBytes();
    make({{"samples", {{"file", t24}}}});
    const std::uint64_t n2 = smp::cachedSampleBytes();
    check((n1 - n0) * 10 < (n2 - n1) * 6, "24-bit files with a zero low byte (converted 16-bit material) are stored as 16-bit, true 24-bit as float");
    // smpl chunk: loop [2400, 2400 + 100 cycles of 480 Hz) and unity note 71 + 50 ct: loop 'auto' + root 'sample'
    SmplInfo info;
    info.unity = 71;
    info.fraction = 0x80000000u;
    info.loopStart = 2400;
    info.loopEnd = 2400 + 10000 - 1;
    const std::string sp = writeWav(dir / "smpl.wav", sine(480.0, 48000, 0.3), 48000, 16, &info);
    auto sl = make({{"samples", {{"file", sp}, {"root", "sample"}, {"loop", "auto"}}}});
    const auto sm = render(*sl, {{0, true, 1, 71, 1.0f}}, sec(1.5)).mono();
    const double f = zeroCrossHz(sm, sec(0.5), sec(1.4));
    check(rms(sm, sec(1.2), sec(1.4)) > 0.2 && std::fabs(cents(f, 480.0) + 50.0) < 0.5 && clicks(Audio{sm, sm}) == 0,
          fmt("smpl chunk: loop 'auto' sustains the 0.3 s file; root 'sample' = 71.5: key 71 plays %.2f Hz (480 Hz - 50 ct)", f));
    auto plain = make({{"samples", {{"file", sp}, {"loop", "none"}}}});
    const auto pm = render(*plain, {{0, true, 1, 60, 1.0f}}, sec(0.6)).mono();
    auto fwd = make({{"samples", {{"file", sp}, {"root", 71.5}, {"loop", "forward"}}}});
    const auto fm = render(*fwd, {{0, true, 1, 71, 1.0f}}, sec(1.5)).mono();
    check(rms(pm, sec(0.35), sec(0.6)) < 1e-4 && rms(fm, sec(1.2), sec(1.4)) > 0.2 && clicks(Audio{fm, fm}) == 0,
          "loop 'none' ignores the file's loop; 'forward' without points uses the file's loop points");
    // sharing and parallel loading: 240 files, then a second instrument on the same files loads nothing
    json zones = json::array();
    for (int i = 0; i < 240; ++i) {
        const std::string pth = writeWav(dir / "many" / (std::to_string(i) + ".wav"), sine(100.0 + i, 48000, 0.05), 48000, i % 2 ? 16 : 24);
        zones.push_back({{"file", pth}, {"lo", i % 128}, {"hi", i % 128}});
    }
    const int f0 = smp::cachedSampleFiles();
    const auto t0 = std::chrono::steady_clock::now();
    auto big = make({{"samples", zones}});
    const double load = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    const int f1 = smp::cachedSampleFiles();
    auto again = make({{"samples", zones}});
    const int f2 = smp::cachedSampleFiles();
    const Audio g1 = render(*big, {{0, true, 1, 5, 1.0f}, {0, true, 2, 100, 1.0f}}, sec(0.1));
    const Audio g2 = render(*again, {{0, true, 1, 5, 1.0f}, {0, true, 2, 100, 1.0f}}, sec(0.1));
    check(f1 - f0 == 240 && f2 == f1 && g1.l == g2.l && rms(g1.l, 0, sec(0.05)) > 0.05,
          fmt("240 files loaded in parallel in %.0f ms, shared by a second instrument (%d new files), identical output", load * 1000.0, f2 - f1));
}

// Interleaved 16-bit PCM WAV with any number of channels: chans[c][frame].
std::string writeMulti(const fs::path& path, const std::vector<std::vector<float>>& chans, int rate) {
    std::vector<unsigned char> b;
    auto u16 = [&](unsigned v) { b.push_back(v & 0xFF); b.push_back((v >> 8) & 0xFF); };
    auto u32 = [&](unsigned v) { u16(v & 0xFFFF); u16(v >> 16); };
    const auto nc = static_cast<unsigned>(chans.size());
    const auto frames = static_cast<unsigned>(chans[0].size());
    const unsigned data = frames * nc * 2;
    b.insert(b.end(), {'R', 'I', 'F', 'F'});
    u32(36 + data);
    b.insert(b.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
    u32(16);
    u16(1);
    u16(nc);
    u32(static_cast<unsigned>(rate));
    u32(static_cast<unsigned>(rate) * 2 * nc);
    u16(2 * nc);
    u16(16);
    b.insert(b.end(), {'d', 'a', 't', 'a'});
    u32(data);
    for (unsigned f = 0; f < frames; ++f) {
        for (unsigned c = 0; c < nc; ++c) {
            u16(static_cast<unsigned>(static_cast<std::int16_t>(std::lround(std::clamp(chans[c][f], -1.0f, 1.0f) * 32767.0f))) & 0xFFFF);
        }
    }
    fs::create_directories(path.parent_path());
    std::ofstream(path, std::ios::binary).write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
    return path.string();
}

// Amplitude of the `hz` component of x[from, to) (single-bin DFT).
double toneAmp(const std::vector<float>& x, double hz, long from, long to) {
    double re = 0.0, im = 0.0;
    for (long i = from; i < to; ++i) {
        const double w = 2.0 * kPi * hz * static_cast<double>(i) / kSr;
        re += x[static_cast<std::size_t>(i)] * std::cos(w);
        im += x[static_cast<std::size_t>(i)] * std::sin(w);
    }
    return 2.0 * std::sqrt(re * re + im * im) / static_cast<double>(to - from);
}

void testChannelMix() {
    std::printf("channel mix of multichannel files (zone 'channels')\n");
    // 4 channels, one tone each (like 4 microphones of one drum hit)
    const double hz[4] = {300.0, 750.0, 1200.0, 2100.0};
    std::vector<std::vector<float>> ch;
    for (double h : hz) ch.push_back(sine(h, 48000, 0.5, 0.2));
    const std::string p = writeMulti(gTmp / "multi" / "hit.wav", ch, 48000);
    const json mix = {{0, 1.0, 0.0}, {2, 0.0, 1.0}, {3, 0.5, 0.5}};
    auto s = make({{"samples", {{"file", p}, {"pitchKeytrack", 0}, {"channels", mix}}}});
    const Audio a = render(*s, {{0, true, 1, 60, 1.0f}}, sec(0.4));
    const long f0 = sec(0.05), f1 = sec(0.35);
    const double l300 = toneAmp(a.l, 300.0, f0, f1), l1200 = toneAmp(a.l, 1200.0, f0, f1), r300 = toneAmp(a.r, 300.0, f0, f1);
    const double r1200 = toneAmp(a.r, 1200.0, f0, f1), l750 = toneAmp(a.l, 750.0, f0, f1) + toneAmp(a.r, 750.0, f0, f1);
    const double l2100 = toneAmp(a.l, 2100.0, f0, f1), r2100 = toneAmp(a.r, 2100.0, f0, f1);
    check(l300 > 0.05 && r300 < 1e-3 && r1200 > 0.05 && l1200 < 1e-3 && l750 < 1e-3 && std::fabs(l2100 - r2100) < 1e-4 &&
              std::fabs(l2100 / l300 - 0.5) < 0.02,
          fmt("[[0,1,0],[2,0,1],[3,.5,.5]]: ch0 left only (%.3f / %.4f), ch2 right only (%.3f / %.4f), ch3 centred at half gain, ch1 unused",
              l300, r300, r1200, l1200));
    // one channel picked into both sides
    auto pick = make({{"samples", {{"file", p}, {"pitchKeytrack", 0}, {"channels", {{1, 0.7071, 0.7071}}}}}});
    const Audio b = render(*pick, {{0, true, 1, 60, 1.0f}}, sec(0.4));
    check(toneAmp(b.l, 750.0, f0, f1) > 0.04 && toneAmp(b.l, 300.0, f0, f1) < 1e-3 && b.l == b.r, "one channel picked into both sides");
    // polarity flip: a channel against itself inverted cancels
    auto null = make({{"samples", {{"file", p}, {"channels", {{2, 1.0, 1.0}, {2, -1.0, -1.0}}}}}});
    const Audio c = render(*null, {{0, true, 1, 60, 1.0f}}, sec(0.3));
    check(rms(c.l, 0, sec(0.3)) < 1e-6, "negative gains flip the polarity (a channel minus itself is silent)");
    // mixes are cached per (file, mix): the same mix shares, another decodes once more
    const int n0 = smp::cachedSampleFiles();
    auto s2 = make({{"samples", {{"file", p}, {"pitchKeytrack", 0}, {"channels", mix}}}});
    const int n1 = smp::cachedSampleFiles();
    make({{"samples", {{"file", p}, {"channels", {{0, 0.5, 0.0}}}}}});
    const int n2 = smp::cachedSampleFiles();
    check(n1 == n0 && n2 == n0 + 1, "a mix is decoded once per process and shared; a different mix is another cache entry");
    const Audio a2 = render(*s2, {{0, true, 1, 60, 1.0f}}, sec(0.4));
    check(a2.l == a.l && a2.r == a.r, "channel mix: identical output on a second instrument");
    // a pure pick / polarity flip of a 16-bit file stays 16-bit (organ sets with one inverted microphone)
    const std::string st = writeMulti(gTmp / "multi" / "pair.wav", {ch[0], ch[1]}, 48000);
    auto plain = make({{"samples", {{"file", st}, {"pitchKeytrack", 0}}}});
    const std::uint64_t b0 = smp::cachedSampleBytes();
    auto flip = make({{"samples", {{"file", st}, {"pitchKeytrack", 0}, {"channels", {{0, 1, 0}, {1, 0, -1}}}}}});
    const std::uint64_t b1 = smp::cachedSampleBytes();
    const Audio pa = render(*plain, {{0, true, 1, 60, 1.0f}}, sec(0.2)), fa = render(*flip, {{0, true, 1, 60, 1.0f}}, sec(0.2));
    bool negated = pa.l == fa.l;
    for (std::size_t i = 0; i < pa.r.size() && negated; ++i) negated = pa.r[i] == -fa.r[i];
    const auto* file = smp::loadSampleFile(st, false, {{0, 1.0f, 0.0f}, {1, 0.0f, -1.0f}}).get();
    check(negated && file->a->is16 && b1 - b0 < 48000 * 2 * 2 + 4096,
          fmt("[[0,1,0],[1,0,-1]]: right channel inverted exactly, still 16-bit (%.0f KB)", static_cast<double>(b1 - b0) / 1024.0));
    // strict errors
    check(rejects({{"samples", {{"file", p}, {"channels", {{4, 1.0, 1.0}}}}}}, "channel mix uses channel 4 but the file has 4 channel"),
          "a channel beyond the file's channels: error naming the channel count");
    check(rejects({{"samples", {{"file", p}, {"channels", {{0, 1.0}}}}}}, "[channel 0..63, gain left, gain right]"), "bad entry shape: error");
    check(rejects({{"samples", {{"file", p}, {"channels", json::array()}}}}, "channels"), "empty channel list: error");
    check(rejects({{"samples", {{"file", p}, {"channels", {{0.5, 1.0, 1.0}}}}}}, "whole channel number"), "fractional channel: error");
    check(rejects({{"samples", {{"file", p}, {"channels", {{0, 20.0, 1.0}}}}}}, "outside -16..16"), "gain out of range: error");
    check(rejects({{"samples", {{"file", "*sine"}, {"channels", {{0, 1.0, 1.0}}}}}}, "only for WAV zones"), "channels on a generator: error");
}

std::uint64_t fnv32(const smp::WavPackAudio& a) {
    std::uint64_t h = 0xcbf29ce484222325ull;
    for (const std::int32_t v : a.samples) {
        const auto u = static_cast<std::uint32_t>(static_cast<std::uint64_t>(static_cast<std::uint32_t>(v)) << (32 - a.bits));
        h = (h ^ u) * 0x100000001b3ull;
    }
    return h;
}

// Inserts an ID_RIFF_HEADER metadata block (a WAV header with a 'smpl' loop, root 64) into the first WavPack block.
std::vector<unsigned char> withRiffHeader(const unsigned char* wv, std::size_t n, std::uint32_t loopStart, std::uint32_t loopEnd) {
    std::vector<unsigned char> riff;
    auto p16 = [&](unsigned v) { riff.push_back(v & 0xFF); riff.push_back((v >> 8) & 0xFF); };
    auto p32 = [&](unsigned v) { p16(v & 0xFFFF); p16(v >> 16); };
    riff.insert(riff.end(), {'R', 'I', 'F', 'F'});
    p32(0);
    riff.insert(riff.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
    p32(16);
    for (unsigned v : {1u, 2u}) p16(v);
    p32(44100);
    p32(44100 * 4);
    p16(4);
    p16(16);
    riff.insert(riff.end(), {'s', 'm', 'p', 'l'});
    p32(60);
    for (unsigned v : {0u, 0u, 22675u, 64u, 0u, 0u, 0u, 1u, 0u}) p32(v);
    for (unsigned v : {0u, 0u, loopStart, loopEnd, 0u, 0u}) p32(v);
    riff.insert(riff.end(), {'d', 'a', 't', 'a'});
    p32(700 * 4);
    std::vector<unsigned char> sub{0x21, static_cast<unsigned char>(riff.size() / 2)};
    sub.insert(sub.end(), riff.begin(), riff.end());
    std::vector<unsigned char> out(wv, wv + 32);
    out.insert(out.end(), sub.begin(), sub.end());
    out.insert(out.end(), wv + 32, wv + n);
    const std::uint32_t ck = (out[4] | (out[5] << 8) | (out[6] << 16) | (static_cast<std::uint32_t>(out[7]) << 24)) + static_cast<std::uint32_t>(sub.size());
    for (int i = 0; i < 4; ++i) out[static_cast<std::size_t>(4 + i)] = static_cast<unsigned char>((ck >> (8 * i)) & 0xFF);
    return out;
}

void testWavPack() {
    std::printf("lossless WavPack files\n");
    struct Fx {
        const char* name;
        const unsigned char* data;
        std::size_t size;
        std::uint64_t hash;
        int channels, frames;
    };
    const Fx fixtures[] = {{"16-bit stereo", k_wv_s16_stereo, sizeof k_wv_s16_stereo, k_wv_s16_stereo_hash, 2, 700},
                           {"24-bit mono", k_wv_s24_mono, sizeof k_wv_s24_mono, k_wv_s24_mono_hash, 1, 500},
                           {"16-bit 4 channels", k_wv_s16_quad, sizeof k_wv_s16_quad, k_wv_s16_quad_hash, 4, 300}};
    for (const auto& f : fixtures) {
        bool ok = false;
        std::string why;
        try {
            const auto a = smp::decodeWavPack(f.data, f.size);
            ok = a.channels == f.channels && a.frames == f.frames && a.rate == 44100.0 && fnv32(a) == f.hash;
            why = fmt("%d ch, %lld frames, %d bits", a.channels, static_cast<long long>(a.frames), a.bits);
        } catch (const std::exception& e) {
            why = e.what();
        }
        check(ok, fmt("%s: bit-exact decode (%s)", f.name, why.c_str()));
    }
    // corruption is caught by the per-block CRC
    std::vector<unsigned char> bad(k_wv_s16_stereo, k_wv_s16_stereo + sizeof k_wv_s16_stereo);
    bad[300] ^= 0x5A;  // inside the first block's bitstream
    bool caught = false;
    try {
        smp::decodeWavPack(bad.data(), bad.size());
    } catch (const std::runtime_error& e) {
        caught = std::string(e.what()).find("WavPack") != std::string::npos;
    }
    check(caught, "a corrupted stream is an error (CRC / bitstream check), never wrong audio");
    // a WavPack file with a '.wav' name plays in the sampler like the PCM file; its RIFF header's smpl loop is used
    const fs::path dir = gTmp / "wavpack";
    fs::create_directories(dir);
    const auto withLoop = withRiffHeader(k_wv_s16_stereo, sizeof k_wv_s16_stereo, 100, 599);
    std::ofstream(dir / "pipe.wav", std::ios::binary).write(reinterpret_cast<const char*>(withLoop.data()), static_cast<std::streamsize>(withLoop.size()));
    const auto ref = smp::decodeWavPack(k_wv_s16_stereo, sizeof k_wv_s16_stereo);
    std::vector<float> l(700), r(700);
    for (int i = 0; i < 700; ++i) {
        l[static_cast<std::size_t>(i)] = static_cast<float>(ref.samples[static_cast<std::size_t>(2 * i)]) / 32768.0f;
        r[static_cast<std::size_t>(i)] = static_cast<float>(ref.samples[static_cast<std::size_t>(2 * i + 1)]) / 32768.0f;
    }
    const std::string pcm = writeStereo(dir / "pcm.wav", l, r, 44100);
    auto wv = make({{"samples", {{"file", (dir / "pipe.wav").string()}, {"root", 60}}}});
    auto pc = make({{"samples", {{"file", pcm}, {"root", 60}}}});
    const std::vector<Event> ev{{0, true, 1, 62, 0.8f}, {sec(0.01), false, 1, 62, 0}};
    const Audio a = render(*wv, ev, sec(0.05)), b = render(*pc, ev, sec(0.05));
    check(a.l == b.l && a.r == b.r && rms(a.l, 0, sec(0.01)) > 0.05, "WavPack '.wav' plays bit-identical to its PCM copy");
    const auto file = smp::loadSampleFile((dir / "pipe.wav").string(), false);
    check(file->loop && file->loop->start == 100 && file->loop->end == 600 && file->unityNote && *file->unityNote == 64.0 && file->a->is16,
          "the embedded RIFF header's smpl chunk gives the loop [100, 600) and root 64; 16-bit data stays 16-bit");
    auto looped = make({{"samples", {{"file", (dir / "pipe.wav").string()}, {"root", "sample"}, {"loop", "auto"}}}});
    const Audio lp = render(*looped, {{0, true, 1, 64, 1.0f}}, sec(0.5));
    check(rms(lp.l, sec(0.4), sec(0.5)) > 0.05, "loop 'auto' sustains the 700-frame WavPack file from its smpl loop");
    std::ofstream(dir / "broken.wav", std::ios::binary).write(reinterpret_cast<const char*>(bad.data()), static_cast<std::streamsize>(bad.size()));
    check(rejects({{"samples", {{"file", (dir / "broken.wav").string()}}}}, "WavPack"), "a corrupted WavPack zone: config error naming WavPack");
    // real GrandOrgue pipes (skipped without the pack)
    const char* lib = std::getenv("AGENTSOUND_SAMPLES");
    const fs::path pipe = fs::path(lib ? lib : "assets/samples") / "lars-palo-burea-church" / "HVPrincipal8" / "060-C.wav";
    if (!fs::is_regular_file(pipe)) {
        std::printf("[skip] GrandOrgue pipe (pack lars-palo-burea-church not installed)\n");
        return;
    }
    const auto org = smp::loadSampleFile(pipe.string(), false);
    check(org->channels == 2 && org->frames == 340025 && org->loop && org->loop->start == 97124 && org->loop->end == 163244,
          fmt("Burea Principal 8' C4 (WavPack): %lld frames, smpl loop [%lld, %lld)", static_cast<long long>(org->frames),
              static_cast<long long>(org->loop ? org->loop->start : -1), static_cast<long long>(org->loop ? org->loop->end : -1)));
}

void testZoneConfig() {
    std::printf("zone config errors\n");
    const std::string a = (gTmp / "rr" / "a.wav").string();
    auto zone = [&](const json& extra) {
        json z = {{"file", a}};
        for (auto it = extra.begin(); it != extra.end(); ++it) z[it.key()] = it.value();
        return json{{"samples", z}};
    };
    check(rejects(zone({{"seqPosition", 3}, {"seqLength", 2}}), "seqPosition 3 > seqLength 2"), "seqPosition beyond seqLength");
    check(rejects(zone({{"lorand", 0.5}, {"hirand", 0.5}}), "lorand >= hirand"), "empty random range");
    check(rejects(zone({{"trigger", "later"}}), "\"attack\", \"release\", \"release_key\", \"first\", \"legato\""), "bad trigger");
    check(rejects(zone({{"offMode", "slow"}}), "\"fast\", \"normal\", \"time\""), "bad off mode");
    check(rejects(zone({{"offset", 100}, {"end", 50}}), "end <= offset"), "end before offset");
    check(rejects(zone({{"velcurve", {{64, 1}, {32, 0.5}}}}), "strictly increasing"), "velcurve order");
    check(rejects(zone({{"xfinLo", 80}, {"xfinHi", 40}}), "xfinLo > xfinHi"), "crossfade range order");
    check(rejects(zone({{"resonance", 3}}), "needs a zone filter"), "resonance without cutoff");
    check(rejects(zone({{"filter", "lpf_2p"}}), "no \"cutoff\""), "filter without cutoff");
    check(rejects(zone({{"eq", {{1000, 1}}}}), "[freq Hz, bandwidth octaves, gain dB]"), "eq band shape");
    check(rejects(zone({{"vibrato", {10, 5}}}), "[depth cents, rate Hz, delay s, fade s]"), "vibrato shape");
    check(rejects(zone({{"filterEnv", {1200, 0, 0, 0, 1, 0, 1}}}), "needs a zone filter"), "filter envelope without a filter");
    check(rejects(zone({{"cutoff", 500}, {"filterEnv", {1200, 0, 0}}}), "[depth cents, delay s, attack s"), "filter envelope shape");
    check(rejects(zone({{"pedal", 1}}), "true or false"), "pedal flag type");
    check(rejects(zone({{"root", "file"}}), "\"sample\""), "root keyword");
    check(rejects({{"samples", {{"file", "*saw"}}}}, "is not a generator"), "unknown generator");
    check(rejects({{"samples", {{"file", "*sine"}, {"offset", 10}}}}, "does not apply to a generator"), "offset on a generator");
    check(rejects(zone({{"loop", "forward"}, {"loopStart", 10}, {"loopEnd", 30}, {"end", 20}}), "lies beyond the played end"),
          "loop beyond the end");
    check(rejects(zone({{"offset", 1000000}}), "beyond the end of the sample"), "offset beyond the sample");
}

void testExpression() {
    std::printf("expression\n");
    const std::string a = (gTmp / "rr" / "a.wav").string();
    auto full = make({{"samples", {{"file", a}, {"root", 69}}}});
    auto halfE = make({{"samples", {{"file", a}, {"root", 69}}}, {"expression", 0.5}});
    const double r1 = rms(render(*full, {{0, true, 1, 69, 1.0f}}, sec(0.3)).l, sec(0.1), sec(0.3));
    const double r2 = rms(render(*halfE, {{0, true, 1, 69, 1.0f}}, sec(0.3)).l, sec(0.1), sec(0.3));
    check(std::fabs(db(r2 / r1) + 12.04) < 0.05, fmt("expression 0.5: %.2f dB (expression^2: -12.04)", db(r2 / r1)));
}

}  // namespace

void testReviewFixes() {
    std::printf("group polyphony, one damper per key at pedal-up, long pedal holds\n");
    const fs::path dir = gTmp / "review";
    const std::string tone440 = writeWav(dir / "tone.wav", sine(440.0, 48000, 3.0), 48000, 16);
    auto relTone = sine(1320.0, 48000, 0.3, 0.4);
    for (std::size_t i = 0; i < 2400; ++i) relTone[relTone.size() - 1 - i] *= static_cast<float>(i / 2400.0);
    const std::string rel = writeWav(dir / "rel.wav", relTone, 48000, 16);

    // groupPolyphony 2 in group 5: the third and fourth note fade the oldest two out (5 ms), other groups are untouched
    const json gp = {{"samples", json::array({{{"file", tone440}, {"root", 69}, {"lo", 60}, {"hi", 80}, {"group", 5},
                                               {"groupPolyphony", 2}, {"loop", "oneshot"}, {"attack", 0.02}},
                                              {{"file", tone440}, {"root", 69}, {"lo", 40}, {"hi", 50}, {"loop", "oneshot"},
                                               {"attack", 0.02}}})}};
    auto g = make(gp);
    const auto gm = render(*g, {{0, true, 1, 45, 0.8f}, {sec(0.1), true, 2, 60, 0.8f}, {sec(0.2), true, 3, 64, 0.8f},
                                {sec(0.3), true, 4, 67, 0.8f}, {sec(0.4), true, 5, 71, 0.8f}}, sec(0.8)).mono();
    const auto hz = [](int key) { return 440.0 * std::pow(2.0, (key - 69) / 12.0); };
    const long at = sec(0.55);
    const double k45 = tone(gm, at, 8192, hz(45)), k60 = tone(gm, at, 8192, hz(60)), k64 = tone(gm, at, 8192, hz(64));
    const double k67 = tone(gm, at, 8192, hz(67)), k71 = tone(gm, at, 8192, hz(71));
    check(k60 < 1e-3 && k64 < 1e-3 && k67 > 0.05 && k71 > 0.05 && k45 > 0.05 && clicks(Audio{gm, gm}) == 0,
          fmt("groupPolyphony 2: keys 60 / 64 turned off (%.1e / %.1e), 67 / 71 sound (%.2f / %.2f), group 0 untouched (%.2f)",
              k60, k64, k67, k71, k45));
    json bad = gp;
    bad["samples"][0]["groupPolyphony"] = 0;
    check(rejects(bad, "groupPolyphony"), "groupPolyphony 0 is rejected");

    // velsens scales a zone's own ampVeltrack (SFZ amp_veltrack): patches of sampled instruments get flatter dynamics
    auto velLevel = [&](float velsens, float vel) {
        auto v = make({{"samples", {{"file", tone440}, {"root", 69}, {"ampVeltrack", 0.8}}}, {"velsens", velsens}});
        const auto m = render(*v, {{0, true, 1, 69, vel}}, sec(0.3)).mono();
        return rms(m, sec(0.1), sec(0.3));
    };
    const double full = velLevel(1.0f, 1.0f), soft1 = velLevel(1.0f, 64.0f / 127.0f), soft05 = velLevel(0.5f, 64.0f / 127.0f);
    const double c64 = (64.0 / 127.0) * (64.0 / 127.0);
    const double want1 = db(1.0 - 0.8 * (1.0 - c64)), want05 = db(1.0 - 0.4 * (1.0 - c64));
    check(std::fabs(db(soft1 / full) - want1) < 0.1 && std::fabs(db(soft05 / full) - want05) < 0.1 &&
              std::fabs(db(velLevel(0.0f, 20.0f / 127.0f) / full)) < 0.05,
          fmt("ampVeltrack 0.8 x velsens: velocity 64 at %.2f dB (velsens 1, want %.2f), %.2f dB (velsens 0.5, want %.2f), "
              "velsens 0 flat", db(soft1 / full), want1, db(soft05 / full), want05));

    // per-zone randomness does not depend on the zone's list position: dropping other zones (compile-time pruning)
    // leaves a note's amp / pitch / offset randomness unchanged
    const json rz = {{"file", tone440}, {"root", 69}, {"lo", 60}, {"hi", 80}, {"ampRandom", 6}, {"pitchRandom", 30},
                     {"offsetRandom", 2000}};
    const json other = {{"file", tone440}, {"root", 69}, {"lo", 20}, {"hi", 30}};
    auto pruned = make({{"samples", json::array({rz})}});
    auto whole = make({{"samples", json::array({other, other, rz})}});
    const std::vector<Event> notes = {{0, true, 1, 69, 0.8f}, {sec(0.2), true, 2, 72, 0.8f}, {sec(0.4), false, 1, 69, 0},
                                      {sec(0.4), false, 2, 72, 0}};
    const auto pa = render(*pruned, notes, sec(0.5)), pb = render(*whole, notes, sec(0.5));
    check(pa.l == pb.l && pa.r == pb.r, "zone randomness keyed by the zone's content: identical after other zones are dropped");

    // a key struck three times under the pedal: one release sample at pedal-up (one damper), as loud as a single strike's
    const json cfg = {{"samples", json::array({{{"file", tone440}, {"root", 69}, {"release", 0.02}},
                                              {{"file", rel}, {"root", 69}, {"pitchKeytrack", 0}, {"trigger", "release"}}})}};
    auto once = make(cfg), thrice = make(cfg);
    const auto o = render(*once, {setAt(0, "pedal", 1.0f), {sec(0.1), true, 1, 69, 1.0f}, {sec(0.2), false, 1, 69, 0},
                                  setAt(sec(0.8), "pedal", 0.0f)}, sec(1.2)).mono();
    const auto t = render(*thrice, {setAt(0, "pedal", 1.0f), {sec(0.1), true, 1, 69, 1.0f}, {sec(0.2), false, 1, 69, 0},
                                    {sec(0.3), true, 2, 69, 1.0f}, {sec(0.4), false, 2, 69, 0}, {sec(0.5), true, 3, 69, 1.0f},
                                    {sec(0.6), false, 3, 69, 0}, setAt(sec(0.8), "pedal", 0.0f)}, sec(1.2)).mono();
    const double r1 = tone(o, sec(0.82), 4096, 1320.0), r3 = tone(t, sec(0.82), 4096, 1320.0);
    check(r1 > 0.05 && std::fabs(db(r3 / r1)) < 0.5,
          fmt("three strikes under the pedal: one release sample at pedal-up (%.2f dB vs one strike)", db(r3 / r1)));
    // struck again and still held at pedal-up: no release then, it fires at that note's note-off
    auto held = make(cfg);
    const auto h = render(*held, {setAt(0, "pedal", 1.0f), {sec(0.1), true, 1, 69, 1.0f}, {sec(0.2), false, 1, 69, 0},
                                  {sec(0.3), true, 2, 69, 1.0f}, setAt(sec(0.5), "pedal", 0.0f), {sec(0.9), false, 2, 69, 0}},
                          sec(1.4)).mono();
    const double atUp = tone(h, sec(0.52), 4096, 1320.0), atOff = tone(h, sec(0.92), 4096, 1320.0);
    check(atUp < 1e-3 && atOff > 0.05,
          fmt("key held again at pedal-up: no release sample then (%.1e), one at its note-off (%.2f)", atUp, atOff));

    // a pedal held down for more notes than the note table holds (release zones wait for pedal-up): later notes are
    // still tracked (legato triggers work)
    const json leg = {{"samples", json::array({{{"file", tone440}, {"root", 69}, {"release", 0.01}, {"trigger", "first"}},
                                              {{"file", rel}, {"root", 69}, {"pitchKeytrack", 0}, {"trigger", "legato"},
                                               {"loop", "oneshot"}},
                                              {{"file", "*silence"}, {"trigger", "release"}}})}};
    auto lp = make(leg);
    std::vector<Event> ev = {setAt(0, "pedal", 1.0f)};
    for (int k = 0; k < 600; ++k) {
        ev.push_back({k * 64L + 1, true, 10 + k, 60 + k % 12, 0.7f});
        ev.push_back({k * 64L + 33, false, 10 + k, 60 + k % 12, 0.0f});
    }
    const long t0 = 600L * 64 + sec(0.5);
    ev.push_back({t0, true, 5000, 69, 1.0f});                // first note: 'first' zone
    ev.push_back({t0 + sec(0.2), true, 5001, 69, 1.0f});     // overlapping: 'legato' zone
    ev.push_back({t0 + sec(0.4), false, 5000, 69, 0.0f});
    ev.push_back({t0 + sec(0.4), false, 5001, 69, 0.0f});
    const auto l = render(*lp, ev, t0 + sec(0.6)).mono();
    check(tone(l, t0 + sec(0.21), 4096, 1320.0) > 0.05,
          "after 600 pedalled notes an overlapping note still plays its legato zone (notes stay tracked)");
}

// ------------------------------------------------------------------------------------ realism: played, not triggered

namespace {

json merged(json a, const json& b) {
    for (auto it = b.begin(); it != b.end(); ++it) a[it.key()] = it.value();
    return a;
}

// dynamics automation: `from` -> `to` in 32-sample steps over [t0, t1)
void dynRamp(std::vector<Event>& ev, long t0, long t1, float from, float to, const char* param = "dynamics") {
    for (long t = t0; t < t1; t += 32) ev.push_back(setAt(t, param, from + (to - from) * static_cast<float>(t - t0) / static_cast<float>(t1 - t0)));
    ev.push_back(setAt(t1, param, to));
}

// RMS envelope in dB (30 ms windows - several periods of the test tones, short against a note - every 5 ms,
// centred) of x over [from, to)
std::vector<double> envelopeDb(const std::vector<float>& x, long from, long to) {
    std::vector<double> e;
    for (long t = from; t <= to; t += sec(0.005)) e.push_back(db(rms(x, t - sec(0.015), t + sec(0.015))));
    return e;
}

void testDynamics() {
    std::printf("live dynamics: CC-style crossfades, gain curves, cutoff, note-on conditions, tone, range\n");
    const fs::path dir = gTmp / "dyn";
    const std::string s440 = writeWav(dir / "s440.wav", sine(440.0, 48000, 3.0), 48000, 16);
    const std::string s550 = writeWav(dir / "s550.wav", sine(550.0, 48000, 3.0), 48000, 16);
    const std::string s660 = writeWav(dir / "s660.wav", sine(660.0, 48000, 3.0), 48000, 16);

    // two layers crossfaded by 'dynamics' (xfout on the soft one, xfin on the loud one): swept 0 -> 1 while the note sounds
    const json xf = {{"velsens", 0}, {"dynamics", 0}, {"dyntone", 0},
                     {"samples", json::array({{{"file", s440}, {"root", 69}, {"xfoutLoDyn", 0}, {"xfoutHiDyn", 127}},
                                              {{"file", s660}, {"root", 69}, {"xfinLoDyn", 0}, {"xfinHiDyn", 127}}})}};
    std::vector<Event> ev = {{0, true, 1, 69, 0.8f}};
    dynRamp(ev, sec(0.5), sec(1.5), 0.0f, 1.0f);
    auto a = make(xf);
    const Audio sweep = render(*a, ev, sec(2.2));
    const auto m = sweep.mono();
    const double lo440 = tone(m, sec(0.2), 8192, 440.0), lo660 = tone(m, sec(0.2), 8192, 660.0);
    const double hi440 = tone(m, sec(1.8), 8192, 440.0), hi660 = tone(m, sec(1.8), 8192, 660.0);
    const double mid440 = tone(m, sec(1.0) - 1024, 2048, 440.0), mid660 = tone(m, sec(1.0) - 1024, 2048, 660.0);
    const double powerDb = db(std::sqrt(mid440 * mid440 + mid660 * mid660) / lo440);
    check(lo660 < 1e-4 && hi440 < 1e-4 && std::fabs(db(hi660 / lo440)) < 0.1 && std::fabs(powerDb) < 0.4 && clicks(sweep) == 0,
          fmt("dynamics 0 -> 1 crossfades the layers while the note sounds: 440 %.3f -> %.5f, 660 %.5f -> %.3f, equal power "
              "halfway (%+.2f dB), click-free", lo440, hi440, lo660, hi660, powerDb));
    // the loud layer started with the note (silent, skipped) and is sample-aligned with one audible from the start
    auto b = make(merged(xf, {{"dynamics", 1}}));
    const Audio held = render(*b, {{0, true, 1, 69, 0.8f}}, sec(2.2));
    double diff = 0.0;
    for (long i = sec(1.6); i < sec(2.2); ++i) diff = std::max(diff, static_cast<double>(std::fabs(held.l[static_cast<std::size_t>(i)] - sweep.l[static_cast<std::size_t>(i)])));
    check(diff < 1e-6, fmt("a layer faded in by dynamics is phase-aligned with its note (max diff %.1e vs a render at dynamics 1)", diff));

    // gain curve and note-on condition
    const json gc = {{"velsens", 0}, {"dyntone", 0}, {"samples", {{"file", s440}, {"root", 69}, {"dynGain", {{0, 0.25}, {127, 1.0}}}}}};
    auto g0 = make(merged(gc, {{"dynamics", 0}})), g1 = make(gc);
    const double r0 = rms(render(*g0, {{0, true, 1, 69, 0.8f}}, sec(0.4)).l, sec(0.1), sec(0.4));
    const double r1 = rms(render(*g1, {{0, true, 1, 69, 0.8f}}, sec(0.4)).l, sec(0.1), sec(0.4));
    check(std::fabs(db(r0 / r1) + 12.04) < 0.05, fmt("dynGain [[0, 0.25], [127, 1]]: dynamics 0 is %.2f dB (-12.04)", db(r0 / r1)));
    const json cond = {{"dyntone", 0}, {"samples", json::array({{{"file", s440}, {"root", 69}, {"dynHi", 63}}, {{"file", s660}, {"root", 69}, {"dynLo", 64}}})}};
    auto c = make(cond);
    const auto cm = render(*c, {setAt(0, "dynamics", 0.2f), {0, true, 1, 69, 0.8f}, {sec(0.3), false, 1, 69, 0}, setAt(sec(0.4), "dynamics", 0.9f),
                                {sec(0.4), true, 2, 69, 0.8f}, {sec(0.7), false, 2, 69, 0}}, sec(0.8)).mono();
    const double f1 = zeroCrossHz(cm, sec(0.05), sec(0.25)), f2 = zeroCrossHz(cm, sec(0.45), sec(0.65));
    check(std::fabs(f1 - 440) < 1 && std::fabs(f2 - 660) < 1, fmt("dynLo / dynHi pick the zone at the note-on: %.0f, %.0f Hz", f1, f2));

    // dynCutoff: the zone filter opens with dynamics
    const std::string s2k = writeWav(dir / "s2k.wav", sine(2000.0, 48000, 1.0), 48000, 16);
    const json dc = {{"velsens", 0}, {"samples", {{"file", s2k}, {"root", 69}, {"cutoff", 500}, {"dynCutoff", 4800}}}};
    auto d0 = make(merged(dc, {{"dynamics", 0}})), d1 = make(dc);
    const double c0 = tone(render(*d0, {{0, true, 1, 69, 0.8f}}, sec(0.5)).mono(), sec(0.2), 8192, 2000.0);
    const double c1 = tone(render(*d1, {{0, true, 1, 69, 0.8f}}, sec(0.5)).mono(), sec(0.2), 8192, 2000.0);
    check(db(c1 / c0) > 18.0, fmt("dynCutoff 4800: 2 kHz through a 500 Hz lowpass at dynamics 0, 8 kHz at 1: +%.1f dB", db(c1 / c0)));

    // dyntone (brightness with dynamics; exactly transparent at dynamics 1) and dynrange (level)
    std::vector<float> two = sine(200.0, 48000, 1.0, 0.3);
    const auto hi = sine(6000.0, 48000, 1.0, 0.3);
    for (std::size_t i = 0; i < two.size(); ++i) two[i] += hi[i];
    const std::string st = writeWav(dir / "two.wav", two, 48000, 16);
    const json tj = {{"velsens", 0}, {"samples", {{"file", st}, {"root", 69}}}};
    auto t1 = make(tj), tOff = make(merged(tj, {{"dyntone", 0}})), t0 = make(merged(tj, {{"dynamics", 0}}));
    const Audio A1 = render(*t1, {{0, true, 1, 69, 0.8f}}, sec(0.5)), AOff = render(*tOff, {{0, true, 1, 69, 0.8f}}, sec(0.5));
    const auto m0 = render(*t0, {{0, true, 1, 69, 0.8f}}, sec(0.5)).mono(), m1 = A1.mono();
    const double hiDb = db(tone(m0, sec(0.2), 8192, 6000.0) / tone(m1, sec(0.2), 8192, 6000.0));
    const double loDb = db(tone(m0, sec(0.2), 8192, 200.0) / tone(m1, sec(0.2), 8192, 200.0));
    check(A1.l == AOff.l && hiDb < -4.0 && hiDb > -6.0 && loDb > 0.0 && loDb < 1.5,
          fmt("dyntone 0.5: dynamics 0 is darker (6 kHz %+.1f dB, 200 Hz %+.2f dB); dynamics 1 is bit-identical to dyntone 0", hiDb, loDb));
    auto rg = make(merged(tj, {{"dynamics", 0}, {"dynrange", 18}, {"dyntone", 0}}));
    const double rr = rms(render(*rg, {{0, true, 1, 69, 0.8f}}, sec(0.5)).l, sec(0.2), sec(0.5)) / rms(AOff.l, sec(0.2), sec(0.5));
    check(std::fabs(db(rr) + 18.0) < 0.05, fmt("dynrange 18: dynamics 0 is %.2f dB", db(rr)));

    // layers='dynamics': three velocity layers become a dynamics stack
    const json lay = {{"velsens", 0}, {"layers", "dynamics"}, {"dyntone", 0},
                      {"samples", json::array({{{"file", s440}, {"root", 69}, {"velhi", 42}},
                                               {{"file", s550}, {"root", 69}, {"vello", 43}, {"velhi", 84}},
                                               {{"file", s660}, {"root", 69}, {"vello", 85}}})}};
    std::vector<Event> lev = {setAt(0, "dynamics", 0.0f), {0, true, 1, 20, 0.8f}, {0, true, 2, 69, 0.2f}};
    dynRamp(lev, sec(0.5), sec(2.5), 0.0f, 1.0f);
    auto l = make(lay);
    const Audio la = render(*l, lev, sec(3.0));
    const auto lm = la.mono();
    auto amps = [&](long at) {
        return std::array<double, 3>{tone(lm, at, 4096, 440.0), tone(lm, at, 4096, 550.0), tone(lm, at, 4096, 660.0)};
    };
    const auto p0 = amps(sec(0.2)), pm = amps(sec(1.5) - 2048), p1 = amps(sec(2.7));
    const double full = p0[0];
    check(p0[1] < 1e-4 && p0[2] < 1e-4 && pm[0] < 0.02 * full && pm[2] < 0.02 * full && std::fabs(db(pm[1] / full)) < 0.2 &&
              p1[0] < 1e-4 && p1[1] < 1e-4 && std::fabs(db(p1[2] / full)) < 0.1 && clicks(la) == 0,
          fmt("layers='dynamics': a velocity-20 note swells through its layers: 440 at dynamics 0, 550 at 0.5 (%.2f dB), 660 at "
              "1 (%.2f dB), click-free", db(pm[1] / full), db(p1[2] / full)));
    auto sp0 = make(merged(lay, {{"xfspread", 0}}));
    const auto s0 = render(*sp0, lev, sec(3.0)).mono();
    check(tone(s0, sec(2.7) - 2048, 4096, 550.0) > 0.9 * full && tone(s0, sec(2.7) - 2048, 4096, 660.0) < 1e-4,
          "xfspread 0: a note started at dynamics 0 reaches only the next layer (550 holds at dynamics 1)");
    check(rejects(merged(lay, {{"xfspread", 1.5}}), "whole number"), "xfspread must be a whole number");
}

// A horn-like sample: a 40 ms noisy attack, a rise, then a steady harmonic tone decaying 2 dB over 2 s.
std::vector<float> hornSample(double hz, double seconds) {
    std::vector<float> x(static_cast<std::size_t>(std::lround(seconds * 48000)));
    unsigned rng = 12345u;
    for (std::size_t i = 0; i < x.size(); ++i) {
        const double t = static_cast<double>(i) / 48000.0;
        const double rise = std::min(1.0, t / 0.06), decay = std::pow(10.0, -2.0 * t / seconds / 20.0);
        double v = 0.0;
        for (int h = 1; h <= 4; ++h) v += 0.3 / h * std::sin(2.0 * kPi * hz * h * t);
        rng = rng * 1664525u + 1013904223u;
        const double noise = (static_cast<double>(rng >> 8) / 16777216.0 * 2.0 - 1.0) * 0.5 * std::max(0.0, 1.0 - t / 0.04);
        x[i] = static_cast<float>(v * rise * decay + noise);
    }
    return x;
}

// Largest deviation (dB) of the RMS envelope around a transition at `t` from the straight line (in dB) between the
// level before (t - 60 ms) and after (t + 300 ms).
double transitionDeviation(const std::vector<float>& x, long t) {
    const auto e = envelopeDb(x, t - sec(0.06), t + sec(0.31));
    const double a = e.front(), b = e.back();
    double dev = 0.0;
    for (std::size_t i = 0; i < e.size(); ++i) {
        const double line = a + (b - a) * static_cast<double>(i) / static_cast<double>(e.size() - 1);
        dev = std::max(dev, std::fabs(e[i] - line));
    }
    return dev;
}

// Energy of the first difference (the noisy attack) in [t, t + 40 ms] relative to the steady tone before `t`.
double attackNoiseDb(const std::vector<float>& x, long t) {
    auto hf = [&](long a, long b) {
        double s = 0.0;
        for (long i = a; i < b; ++i) {
            const double d = x[static_cast<std::size_t>(i)] - x[static_cast<std::size_t>(i - 1)];
            s += d * d;
        }
        return s / static_cast<double>(b - a);
    };
    return 10.0 * std::log10(hf(t, t + sec(0.04)) / hf(t - sec(0.1), t - sec(0.02)));
}

void testLegato() {
    std::printf("legato: scripted and library transitions, level match, portamento, vibrato\n");
    const fs::path dir = gTmp / "legato";
    const std::string horn = writeWav(dir / "horn.wav", hornSample(261.6256, 2.5), 48000, 16);
    const json base = {{"velsens", 0}, {"release", 0.08}, {"samples", {{"file", horn}, {"root", 60}}}};
    // a phrase of four overlapping equal-velocity notes
    std::vector<Event> phrase;
    const int keys[4] = {60, 62, 64, 62};
    for (int k = 0; k < 4; ++k) {
        phrase.push_back({sec(0.6 * k), true, k + 1, keys[k], 0.8f});
        phrase.push_back({sec(0.6 * k + 0.62), false, k + 1, keys[k], 0.0f});
    }
    auto lg = make(merged(base, {{"mono", "legato"}}));
    auto re = make(merged(base, {{"mono", "on"}}));
    const Audio L = render(*lg, phrase, sec(3.0)), R = render(*re, phrase, sec(3.0));
    const auto lm = L.mono(), rm = R.mono();
    double devL = 0.0, devR = 0.0, noiseL = -99.0, noiseR = -99.0;
    for (int k = 1; k < 4; ++k) {
        devL = std::max(devL, transitionDeviation(lm, sec(0.6 * k)));
        devR = std::max(devR, transitionDeviation(rm, sec(0.6 * k)));
        noiseL = std::max(noiseL, attackNoiseDb(lm, sec(0.6 * k)));
        noiseR = std::max(noiseR, attackNoiseDb(rm, sec(0.6 * k)));
    }
    const double first = attackNoiseDb(lm, sec(0.12)) , firstAttack = attackNoiseDb(rm, sec(0.6));
    check(devL < 1.5 && devR > 3.0, fmt("legato transitions keep the level: RMS envelope within %.2f dB (re-attacked mono notes: %.1f dB)",
                                        devL, devR));
    check(noiseL < 3.0 && noiseR > 10.0, fmt("legato notes enter past their attack: attack noise %+.1f dB at transitions (re-attacked: %+.1f dB)",
                                            noiseL, noiseR));
    (void)first;
    (void)firstAttack;
    check(clicks(L) == 0, "legato phrase is click-free");
    const double d4 = tone(lm, sec(0.8), 8192, 293.6648), c4 = tone(lm, sec(0.8), 8192, 261.6256);
    check(d4 > 0.1 && c4 < 1e-3, fmt("the second note sounds at its pitch (D4 %.3f, the old C4 gone: %.1e)", d4, c4));
    auto lg2 = make(merged(base, {{"mono", "legato"}}));
    check(render(*lg2, phrase, sec(3.0)).l == L.l, "legato is deterministic");

    // a note after a rest attacks normally (the noisy attack is there)
    auto lg3 = make(merged(base, {{"mono", "legato"}}));
    const auto sep = render(*lg3, {{0, true, 1, 60, 0.8f}, {sec(0.4), false, 1, 60, 0}, {sec(0.6), true, 2, 62, 0.8f}, {sec(1.0), false, 2, 62, 0}},
                            sec(1.2)).mono();
    check(attackNoiseDb(sep, sec(0.6)) > 10.0, fmt("a note after a rest attacks (noise %+.1f dB)", attackNoiseDb(sep, sec(0.6))));

    // velocity of a legato note sets its level smoothly
    auto lv = make(merged(base, {{"mono", "legato"}, {"velsens", 1}}));
    const auto vm = render(*lv, {{0, true, 1, 60, 0.5f}, {sec(0.6), true, 2, 62, 1.0f}, {sec(0.62), false, 1, 60, 0}, {sec(1.4), false, 2, 62, 0}},
                           sec(1.5)).mono();
    const auto ve = envelopeDb(vm, sec(0.55), sec(1.2));
    double worstStep = 0.0;
    for (std::size_t i = 1; i < ve.size(); ++i) worstStep = std::max(worstStep, std::fabs(ve[i] - ve[i - 1]));
    const double rise = ve.back() - ve.front();
    check(rise > 4.0 && worstStep < 1.0, fmt("a louder legato note (velocity 64 -> 127) rises %.1f dB smoothly (largest 5 ms step %.2f dB)",
                                             rise, worstStep));

    // library legato transitions (trigger 'legato' zones) play when present; the old note crossfades out
    const std::string s440 = (gTmp / "dyn" / "s440.wav").string(), s660 = (gTmp / "dyn" / "s660.wav").string();
    const json lib = {{"mono", "legato"}, {"velsens", 0}, {"legatotime", 50},
                      {"samples", json::array({{{"file", s440}, {"root", 69}, {"trigger", "first"}},
                                               {{"file", s660}, {"root", 69}, {"trigger", "legato"}}})}};
    auto lb = make(lib);
    const Audio LB = render(*lb, {{0, true, 1, 69, 0.8f}, {sec(0.5), true, 2, 69, 0.8f}, {sec(0.52), false, 1, 69, 0}, {sec(1.2), false, 2, 69, 0}},
                           sec(1.4));
    const auto lbm = LB.mono();
    check(tone(lbm, sec(0.7), 8192, 660.0) > 0.2 && tone(lbm, sec(0.7), 8192, 440.0) < 1e-3 && clicks(LB) == 0,
          "library legato zone plays the transition, the old note crossfades out (click-free)");

    // portamento: the pitch bends from the old note to the new one
    const std::string sn = writeWav(dir / "sine.wav", sine(440.0, 48000, 3.0), 48000, 16);
    const json port = {{"mono", "legato"}, {"velsens", 0}, {"glide", 200}, {"glideshape", "linear"},
                       {"samples", {{"file", sn}, {"root", 69}, {"loop", "none"}}}};
    auto pt = make(port);
    const Audio P = render(*pt, {{0, true, 1, 69, 0.8f}, {sec(0.5), true, 2, 72, 0.8f}, {sec(0.52), false, 1, 69, 0}, {sec(1.3), false, 2, 72, 0}},
                           sec(1.4));
    const auto pm = P.mono();
    const double fMid = zeroCrossHz(pm, sec(0.5) + sec(0.09), sec(0.5) + sec(0.11)), fEnd = zeroCrossHz(pm, sec(0.8), sec(1.0));
    check(std::fabs(cents(fMid, 440.0) - 150.0) < 15.0 && std::fabs(cents(fEnd, 440.0) - 300.0) < 2.0 && clicks(P) == 0,
          fmt("glide 200 ms: halfway %.0f ct above the old note (150), then %.1f ct (300); click-free", cents(fMid, 440.0), cents(fEnd, 440.0)));

    // key-up noises (release zones) fire at the end of the phrase, not between legato notes
    const std::string rel = writeWav(dir / "rel.wav", sine(1320.0, 48000, 0.3, 0.4), 48000, 16);
    const json rz = {{"mono", "legato"}, {"velsens", 0},
                     {"samples", json::array({{{"file", sn}, {"root", 69}}, {{"file", rel}, {"root", 69}, {"pitchKeytrack", 0}, {"trigger", "release"}}})}};
    auto rzi = make(rz);
    const auto rzm = render(*rzi, {{0, true, 1, 69, 0.8f}, {sec(0.5), true, 2, 71, 0.8f}, {sec(0.52), false, 1, 69, 0}, {sec(1.0), false, 2, 71, 0}},
                            sec(1.4)).mono();
    check(tone(rzm, sec(0.55), 8192, 1320.0) < 1e-3 && tone(rzm, sec(1.0), 8192, 1320.0) > 0.05,
          "release zones fire at the phrase end only (a legato note carries the sound on)");

    // instrument vibrato: +- depth in cents at the rate
    const json vib = {{"velsens", 0}, {"vibrato", 50}, {"vibratorate", 5}, {"samples", {{"file", sn}, {"root", 69}}}};
    auto vi = make(vib);
    const auto vim = render(*vi, {{0, true, 1, 69, 0.8f}}, sec(1.2)).mono();
    double lo = 1e9, hi2 = -1e9;
    for (long t = sec(0.2); t + sec(0.02) < sec(1.2); t += sec(0.005)) {
        const double c = cents(zeroCrossHz(vim, t, t + sec(0.02)), 440.0);
        lo = std::min(lo, c);
        hi2 = std::max(hi2, c);
    }
    check(hi2 > 40.0 && hi2 < 55.0 && lo < -40.0 && lo > -55.0, fmt("vibrato 50 ct: pitch swings %+.0f .. %+.0f ct", lo, hi2));
    // preview parity: a render starting at song beat 2 (1 s) plays notes after the start exactly like the full render
    std::vector<Event> pev = {setAt(0, "dynamics", 0.6f), {sec(1.25), true, 1, 69, 0.8f}, {sec(1.8), true, 2, 71, 0.8f}, {sec(1.82), false, 1, 69, 0},
                              {sec(2.4), false, 2, 71, 0}};
    dynRamp(pev, sec(1.5), sec(2.0), 0.6f, 0.9f);
    const json pj = merged(vib, {{"mono", "legato"}, {"glide", 80}, {"dynrange", 12}});
    auto pf = make(pj), pp = make(pj, kSr, 2.0);
    const Audio F = render(*pf, pev, sec(2.6));
    std::vector<Event> later;
    for (const auto& e : pev) {
        if (e.at >= sec(1.0)) later.push_back({e.at - sec(1.0), e.on, e.id, e.pitch, e.vel, e.param, e.value});
    }
    later.insert(later.begin(), setAt(0, "dynamics", 0.6f));
    const Audio Pv = render(*pp, later, sec(1.6));
    double pdiff = 0.0;
    for (long i = 0; i < sec(1.6); ++i) pdiff = std::max(pdiff, static_cast<double>(std::fabs(Pv.l[static_cast<std::size_t>(i)] - F.l[static_cast<std::size_t>(i + sec(1.0))])));
    check(pdiff < 1e-6, fmt("preview (startBeat 2) = full render for legato / glide / vibrato / dynamics (max diff %.1e)", pdiff));
}

// Reader::skip keeps exactly the place read() would (forward / ping-pong loops, loop until release, the end).
void testSkip() {
    std::printf("reader skip (silent layers) = read without samples\n");
    std::vector<float> data(30000);
    for (std::size_t i = 0; i < data.size(); ++i) data[i] = static_cast<float>(std::sin(0.01 * static_cast<double>(i)) * 0.5);
    bool ok = true;
    const std::pair<smp::LoopMode, bool> modes[] = {{smp::LoopMode::Forward, false}, {smp::LoopMode::PingPong, false},
                                                    {smp::LoopMode::Forward, true}, {smp::LoopMode::None, false}};
    for (const auto& [mode, untilRelease] : modes) {
        const smp::Region r = smp::makeRegion(&data, 1, 44100.0, mode, 9000, 9400);
        for (const double inc : {0.37, 1.0, 1.91, 5.3}) {
            smp::Reader a, b;
            a.start(r, 100.0, 30000.0, mode != smp::LoopMode::None);
            b.start(r, 100.0, 30000.0, mode != smp::LoopMode::None);
            float o0[smp::kControl], o1[smp::kControl];
            for (int k = 0; k < 3000; ++k) {
                if (untilRelease && k == 900) a.exitAtWrap = b.exitAtWrap = true;
                const int n = 1 + k % smp::kControl;
                if (k % 7 < 4) {
                    a.read(o0, nullptr, n, inc);
                    b.skip(n, inc);
                } else {  // both read: the same samples after any number of skipped blocks
                    a.read(o0, nullptr, n, inc);
                    b.read(o1, nullptr, n, inc);
                    for (int i = 0; i < n; ++i) ok = ok && o0[i] == o1[i];
                }
                ok = ok && a.pos == b.pos && a.inB == b.inB && a.done == b.done && a.looping == b.looping;
            }
        }
    }
    check(ok, "after skipped blocks a reader is bit-identical to one that read them (loops, ping-pong, release, end)");
}

void testKeyswitches() {
    std::printf("keyswitches: articulations switched live by notes that never sound\n");
    const std::string s440 = (gTmp / "dyn" / "s440.wav").string(), s550 = (gTmp / "dyn" / "s550.wav").string(),
                      s660 = (gTmp / "dyn" / "s660.wav").string();
    const std::string s880 = writeWav(gTmp / "ks" / "s880.wav", sine(880.0, 48000, 1.0), 48000, 16);
    const json ks = {{"velsens", 0},
                     {"samples", json::array({{{"file", s440}, {"root", 69}, {"swLast", 24}, {"swLo", 24}, {"swHi", 27}, {"swDefault", 24}},
                                              {{"file", s660}, {"root", 69}, {"swLast", 25}, {"swDefault", 24}},
                                              {{"file", s880}, {"root", 69}, {"swLast", json::array({26, 27})}, {"swDefault", 24}},
                                              {{"file", s550}, {"root", 69}, {"swDown", 30}}})}};
    auto k = make(ks);
    const auto km = render(*k, {{0, true, 1, 69, 0.8f}, {sec(0.3), false, 1, 69, 0},
                                {sec(0.4), true, 2, 25, 0.8f}, {sec(0.41), false, 2, 25, 0}, {sec(0.45), true, 3, 69, 0.8f}, {sec(0.75), false, 3, 69, 0},
                                {sec(0.8), true, 4, 27, 0.8f}, {sec(0.8), true, 5, 69, 0.8f}, {sec(1.1), false, 5, 69, 0}, {sec(1.1), false, 4, 27, 0},
                                {sec(1.2), true, 6, 30, 0.8f}, {sec(1.2), true, 7, 69, 0.8f}, {sec(1.5), false, 7, 69, 0}, {sec(1.5), false, 6, 30, 0},
                                {sec(1.6), true, 8, 69, 0.8f}, {sec(1.9), false, 8, 69, 0}},
                           sec(2.0)).mono();
    const double f1 = zeroCrossHz(km, sec(0.05), sec(0.25)), f2 = zeroCrossHz(km, sec(0.5), sec(0.7)), f3 = zeroCrossHz(km, sec(0.85), sec(1.05));
    const double f5 = zeroCrossHz(km, sec(1.65), sec(1.85));
    const double down550 = tone(km, sec(1.22), 8192, 550.0), up550 = tone(km, sec(1.62), 8192, 550.0);
    check(std::fabs(f1 - 440) < 1 && std::fabs(f2 - 660) < 1 && std::fabs(f3 - 880) < 1 && std::fabs(f5 - 880) < 1,
          fmt("swDefault 24 -> 440 Hz; keyswitch 25 -> %.0f; keyswitch 27 (swLast [26, 27]) at the same sample -> %.0f; it stays: %.0f Hz",
              f2, f3, f5));
    check(down550 > 0.1 && up550 < 1e-3, "swDown 30: that zone plays only while its key is held");
    auto k2 = make(ks);
    const Audio only = render(*k2, {{0, true, 1, 25, 1.0f}, {sec(0.2), false, 1, 25, 0}, {sec(0.3), true, 2, 30, 1.0f}, {sec(0.5), false, 2, 30, 0}}, sec(0.6));
    check(std::all_of(only.l.begin(), only.l.end(), [](float x) { return x == 0.0f; }) && k2->idle(), "keyswitch notes never sound");
    const json one = {{"samples", {{"file", s440}, {"root", 69}}}};
    check(rejects(merged(one, {{"samples", {{"file", s440}, {"swLo", 24}}}}), "swLo and swHi"), "swLo without swHi is rejected");
    check(rejects({{"samples", json::array({{{"file", s440}, {"swLast", 24}, {"swDefault", 24}}, {{"file", s660}, {"swLast", 25}, {"swDefault", 25}}})}},
                  "one default articulation"), "conflicting swDefault values are rejected");
    check(rejects({{"samples", {{"file", s440}, {"dynCutoff", 1200}}}}, "needs a zone filter"), "dynCutoff needs a zone filter");
    check(rejects({{"samples", {{"file", s440}, {"dynGain", {{64, 1}, {32, 0.5}}}}}}, "strictly increasing"), "dynGain points must increase");
    check(rejects({{"samples", {{"file", s440}, {"xfinLoDyn", 90}, {"xfinHiDyn", 30}}}}, "xfinLoDyn > xfinHiDyn"), "xfinLoDyn > xfinHiDyn is rejected");
}

// Review of the realism engine: velocity crossfades in a dynamics stack, fast legato runs, returning to a held key.
void testRealismReview() {
    std::printf("realism review: dynamics stacks of velocity-crossfaded layers, fast legato runs, return to a held key\n");
    const std::string s440 = (gTmp / "dyn" / "s440.wav").string(), s660 = (gTmp / "dyn" / "s660.wav").string();
    // layers='dynamics' on layers that crossfade by velocity (xfin / xfout vel): a soft note's velocity must not mute
    // the loud layer the stack fades in
    const json vx = {{"velsens", 0}, {"layers", "dynamics"}, {"dyntone", 0},
                     {"samples", json::array({{{"file", s440}, {"root", 69}, {"velhi", 80}, {"xfoutLo", 60}, {"xfoutHi", 80}},
                                              {{"file", s660}, {"root", 69}, {"vello", 60}, {"xfinLo", 60}, {"xfinHi", 80}}})}};
    std::vector<Event> ve = {setAt(0, "dynamics", 0.0f), {0, true, 1, 69, 0.15f}};
    dynRamp(ve, sec(0.3), sec(0.8), 0.0f, 1.0f);
    auto va = make(vx);
    const auto vm = render(*va, ve, sec(1.2)).mono();
    const double soft = tone(vm, sec(0.05), 8192, 440.0), loud = tone(vm, sec(0.9), 8192, 660.0);
    check(soft > 0.1 && std::fabs(db(loud / soft)) < 0.2 && tone(vm, sec(0.9), 8192, 440.0) < 1e-4,
          fmt("layers='dynamics' ignores velocity crossfades: a velocity-19 note swells into the loud layer (%.3f -> %.3f)", soft, loud));

    // a fast legato run (notes 40 ms apart, crossfades of 60 ms overlap): the line keeps its level
    const std::string horn = (gTmp / "legato" / "horn.wav").string();
    const json base = {{"velsens", 0}, {"release", 0.08}, {"mono", "legato"}, {"legatotime", 60}, {"samples", {{"file", horn}, {"root", 60}}}};
    std::vector<Event> run = {{0, true, 1, 60, 0.8f}, {sec(0.505), false, 1, 60, 0.0f}};
    for (int k = 0; k < 16; ++k) {
        run.push_back({sec(0.5 + 0.04 * k), true, k + 2, 61 + k, 0.8f});
        run.push_back({sec(0.5 + 0.04 * k + 0.045), false, k + 2, 0, 0.0f});
    }
    run.push_back({sec(1.14), true, 99, 62, 0.8f});
    run.push_back({sec(1.6), false, 99, 62, 0.0f});
    auto fr = make(base);
    const Audio FR = render(*fr, run, sec(1.7));
    const auto fm = FR.mono();
    const double before = db(rms(fm, sec(0.3), sec(0.48))), during = db(rms(fm, sec(0.6), sec(1.1)));
    const double after = db(rms(fm, sec(1.3), sec(1.58)));
    check(std::fabs(during - before) < 1.5 && std::fabs(after - before) < 1.5 && clicks(FR) == 0,
          fmt("a fast legato run keeps the line's level: %.1f dB before, %.1f during, %.1f after (click-free)", before, during, after));

    // a note released over a held key: the line goes back to that key (legato), not silence
    const std::string rel = (gTmp / "legato" / "rel.wav").string();
    const json withRel = merged(base, {{"samples", json::array({{{"file", horn}, {"root", 60}},
                                                               {{"file", rel}, {"root", 69}, {"pitchKeytrack", 0}, {"trigger", "release"}}})}});
    const std::vector<Event> trill = {{0, true, 1, 60, 0.8f}, {sec(0.5), true, 2, 62, 0.8f}, {sec(0.8), false, 2, 62, 0}, {sec(1.5), false, 1, 60, 0}};
    auto tr = make(withRel);
    const Audio TR = render(*tr, trill, sec(1.8));
    const auto tm = TR.mono();
    const double c4 = tone(tm, sec(1.0), 8192, 261.6256), d4 = tone(tm, sec(1.0), 8192, 293.6648);
    check(c4 > 0.05 && d4 < 1e-3 && std::fabs(db(rms(tm, sec(1.0), sec(1.4)) / rms(tm, sec(0.3), sec(0.48)))) < 1.5 && clicks(TR) == 0,
          fmt("releasing a note over a held key returns to it (C4 %.3f, D4 %.1e, level kept, click-free)", c4, d4));
    check(tone(tm, sec(0.81), 4096, 1320.0) < 1e-3 && tone(tm, sec(1.51), 4096, 1320.0) > 0.05,
          fmt("the note left fires no release zone (%.1e); the key returned to fires its own at its note-off (%.3f)",
              tone(tm, sec(0.81), 4096, 1320.0), tone(tm, sec(1.51), 4096, 1320.0)));
    auto tr2 = make(withRel);
    check(render(*tr2, trill, sec(1.8)).l == TR.l, "returning to a held key is deterministic");
}

// A plucked string: partials 1..10 at 1/k, the upper ones dying faster.
std::vector<float> stringSample(double hz, double seconds, double tau = 1.2) {
    std::vector<float> v(static_cast<std::size_t>(std::lround(seconds * 48000)));
    for (std::size_t i = 0; i < v.size(); ++i) {
        const double t = static_cast<double>(i) / 48000.0;
        double s = 0.0;
        for (int k = 1; k <= 10; ++k) s += std::sin(2.0 * kPi * k * hz * t) / k * std::exp(-t * k / (tau * 2.0));
        v[i] = static_cast<float>(0.3 * s * std::exp(-t / tau));
    }
    return v;
}

void testGuitarTechniques() {
    std::printf("guitar techniques: per-note bends (bendfollow), the string's harmonic (pinch / feedback)\n");
    const fs::path dir = gTmp / "guitar";
    const std::string str = writeWav(dir / "string.wav", stringSample(440.0, 3.0), 48000, 16);
    const json base = {{"velsens", 0}, {"release", 0.08}, {"samples", {{"file", str}, {"root", 69}}}};

    // an oblique bend: the held B4 (latched bendfollow 0) stays, the G4 under it rises a whole step to A4
    auto ob = make(base);
    const auto obm = render(*ob, {setAt(0, "bendfollow", 0.0f), {sec(0.01), true, 1, 71, 0.8f}, setAt(sec(0.02), "bendfollow", 1.0f),
                                  {sec(0.03), true, 2, 67, 0.8f}, setAt(sec(0.3), "pitchbend", 2.0f),
                                  {sec(1.2), false, 1, 71, 0}, {sec(1.2), false, 2, 67, 0}},
                              sec(1.3)).mono();
    const double held = tone(obm, sec(0.6), 16384, 493.8833), bent = tone(obm, sec(0.6), 16384, 440.0),
                 gone = tone(obm, sec(0.6), 16384, 391.995);
    check(held > 0.02 && bent > 0.02 && gone < 0.05 * bent,
          fmt("oblique bend: the held B4 stays (%.3f), the G4 under it rises to A4 (%.3f, G4 left %.4f)", held, bent, gone));
    check(rejects(merged(base, {{"bendfollow", 2}}), "bendfollow"), "bendfollow out of range is an error");

    // the harmonic: 0 = the plain note, bit-transparent
    auto plain = make(base), zero = make(merged(base, {{"harmonic", 0.0}, {"harmonicnum", 4}}));
    const std::vector<Event> one = {{0, true, 1, 69, 0.8f}, {sec(2.5), false, 1, 69, 0}};
    const Audio P = render(*plain, one, sec(2.7));
    check(render(*zero, one, sec(2.7)).l == P.l, "harmonic 0 is bit-transparent");
    // harmonic 1, partial 3: the octave + fifth only, at the note's level
    auto h3 = make(merged(base, {{"harmonic", 1.0}, {"harmonicnum", 3}}));
    const Audio H = render(*h3, one, sec(2.7));
    const auto pm = P.mono(), hm = H.mono();
    const double p1 = tone(pm, sec(0.3), 8192, 440.0), p3 = tone(pm, sec(0.3), 8192, 1320.0);
    const double q1 = tone(hm, sec(0.3), 8192, 440.0), q3 = tone(hm, sec(0.3), 8192, 1320.0);
    check(p3 < 0.5 * p1 && q3 > 20.0 * q1, fmt("harmonic 1: partial 3 / fundamental %.2f -> %.1f", p3 / p1, q3 / std::max(q1, 1e-9)));
    const double lp = db(rms(pm, sec(0.05), sec(0.2))), lh = db(rms(hm, sec(0.05), sec(0.2)));
    check(std::fabs(lh - lp) < 3.0, fmt("the partial is level-matched to the note (%.1f vs %.1f dB)", lh, lp));
    // it sustains: the note dies, the 'feedback' holds near its peak level
    const double dp = db(rms(pm, sec(2.0), sec(2.3))) - db(rms(pm, sec(0.1), sec(0.3)));
    const double dh = db(rms(hm, sec(2.0), sec(2.3))) - db(rms(hm, sec(0.1), sec(0.3)));
    check(dh > dp + 8.0, fmt("harmonic 1 sustains like feedback: %.1f dB after 2 s (the plain note %.1f dB)", dh, dp));
    // it tracks the bend: a whole-step bend moves the partial with the note
    auto hb = make(merged(base, {{"harmonic", 1.0}, {"harmonicnum", 2}}));
    const auto hbm = render(*hb, {{0, true, 1, 69, 0.8f}, setAt(sec(0.4), "pitchbend", 2.0f), {sec(1.5), false, 1, 69, 0}}, sec(1.6)).mono();
    const double up = tone(hbm, sec(0.8), 8192, 880.0 * std::pow(2.0, 2.0 / 12.0)), stay = tone(hbm, sec(0.8), 8192, 880.0);
    check(up > 10.0 * stay, fmt("the harmonic follows a bend (B5 %.3f, A5 %.4f)", up, stay));
    // a feedback bloom: harmonic ramped 0 -> 0.9 over a held note, click-free, finite, deterministic
    std::vector<Event> bl = {{0, true, 1, 64, 0.9f}, {sec(2.6), false, 1, 64, 0}};
    for (int k = 0; k <= 40; ++k) bl.push_back(setAt(sec(0.8 + 0.03 * k), "harmonic", 0.9f * k / 40.0f));
    auto fb1 = make(merged(base, {{"harmonicnum", 2}})), fb2 = make(merged(base, {{"harmonicnum", 2}}));
    const Audio F1 = render(*fb1, bl, sec(2.8)), F2 = render(*fb2, bl, sec(2.8));
    bool finite = true;
    for (float x : F1.l) finite = finite && std::isfinite(x);
    check(finite && F1.l == F2.l, "a feedback bloom is finite and deterministic");
    check(clicks(F1) == 0, "a feedback bloom is click-free");
    // a pinch harmonic: stepped up just before the pick (partial 5), back down after the note
    auto pin = make(merged(base, {{"harmonicnum", 5}}));
    const Audio PH = render(*pin, {setAt(0, "harmonic", 0.8f), {sec(0.005), true, 1, 64, 0.9f}, {sec(1.0), false, 1, 64, 0},
                                   setAt(sec(1.2), "harmonic", 0.0f), {sec(1.3), true, 2, 64, 0.9f}, {sec(2.0), false, 2, 64, 0}},
                             sec(2.2));
    const auto phm = PH.mono();
    const double e5 = 329.6276 * 5.0;
    check(tone(phm, sec(0.2), 8192, e5) > 3.0 * tone(phm, sec(0.2), 8192, 329.6276) &&
              tone(phm, sec(1.5), 8192, e5) < tone(phm, sec(1.5), 8192, 329.6276),
          "a pinch harmonic squeals (partial 5 over the note), the next note is plain again");
    check(clicks(PH) == 0, "pinch harmonics are click-free");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 1) {
        gAssets = argv[1];
    } else {
        for (const char* candidate : {"assets", "../assets", "../../assets"}) {
            if (fs::is_regular_file(fs::path(candidate) / "soundfonts" / "GeneralUser-GS.sf2")) {
                gAssets = fs::absolute(candidate).string();
                break;
            }
        }
    }
    if (gAssets.empty()) {
        std::printf("FAIL: cannot find assets/soundfonts (run from the repo root or pass the assets dir)\n");
        return 1;
    }
    gTmp = fs::temp_directory_path() / "agentsound_test_sampler";
    std::error_code ec;
    fs::remove_all(gTmp, ec);
    fs::create_directories(gTmp);
    try {
        testNoteFolder();
        testDrumFolder();
        testZonesAndLoops();
        testStereoAndSf2();
        testConfig();
        testDeterminismIdle();
        testCore();
        testStealingAndSpeed();
        testSequencesAndTriggers();
        testReleaseAndPedal();
        testSympatheticAndHalfPedal();
        testRestrike();
        testGroupsAndGenerators();
        testZoneShaping();
        testRandomDelayLfo();
        testStorageAndFiles();
        testZoneConfig();
        testChannelMix();
        testWavPack();
        testExpression();
        testReviewFixes();
        testDynamics();
        testLegato();
        testKeyswitches();
        testSkip();
        testRealismReview();
        testGuitarTechniques();
    } catch (const std::exception& e) {
        std::printf("FAIL: unexpected exception: %s\n", e.what());
        return 1;
    }
    std::printf("%d/%d checks passed\n", gChecks - gFailures, gChecks);
    return gFailures == 0 ? 0 : 1;
}
