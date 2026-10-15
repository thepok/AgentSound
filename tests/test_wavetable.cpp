// Tests for the "wavetable" instrument (VaSynth.cpp in wavetable mode + instruments/Wavetable.*): the spec
// list and its strictness, every file loader (Serum 'clm ', Surge .wt float / int16 and 'srge' WAVs, plain
// WAV frame-size detection and override, single cycles, errors) on tiny synthetic files written here, the
// built-in tables, aliasing at high notes, morph continuity (no clicks when the position jumps or sweeps),
// warps, determinism, finite output and speed.

#include "instruments/VaSynth.h"
#include "instruments/Wavetable.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
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
namespace fs = std::filesystem;

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
Ev on(double sec, int id, int pitch, double sr, float vel = 0.8f) { return {static_cast<long>(sec * sr), 0, id, pitch, vel, "", 0}; }
Ev off(double sec, int id, double sr) { return {static_cast<long>(sec * sr), 1, id, 0, 0, "", 0}; }
Ev prm(double sec, const std::string& n, float v, double sr) { return {static_cast<long>(sec * sr), 2, 0, 0, 0, n, v}; }

struct Out {
    std::vector<float> L, R;
};

std::unique_ptr<as::Instrument> make(const json& params, double sr = 48000, std::uint64_t seed = 1) {
    auto inst = as::makeWavetableSynth();
    inst->configure(params);
    as::RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.seed = seed;
    ctx.assetDir = "assets";
    inst->prepare(ctx);
    return inst;
}

Out render(as::Instrument& inst, std::vector<Ev> evs, double seconds, double sr) {
    std::stable_sort(evs.begin(), evs.end(), [](const Ev& a, const Ev& b) { return a.t < b.t; });
    const long total = static_cast<long>(seconds * sr);
    Out o{std::vector<float>(static_cast<std::size_t>(total)), std::vector<float>(static_cast<std::size_t>(total))};
    long pos = 0;
    std::size_t ei = 0;
    while (pos < total) {
        while (ei < evs.size() && evs[ei].t <= pos) {
            const Ev& e = evs[ei++];
            if (e.type == 0) inst.noteOn(e.id, e.pitch, e.vel);
            else if (e.type == 1) inst.noteOff(e.id);
            else if (!inst.setParam(e.name, e.value)) std::cout << "  (setParam " << e.name << " refused)\n";
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

// Energy of everything that is not a harmonic of f0 (below 20 kHz) relative to the harmonic energy below 20 kHz
// (relToTotal: relative to the whole signal's energy): the aliases (partials folded back from above Nyquist)
// and interpolation images land between the harmonics.
double inharmonicDb(const std::vector<float>& x, double sr, double f0, double start, bool relToTotal = false) {
    const std::size_t n = 32768, i0 = static_cast<std::size_t>(start * sr);
    std::vector<std::complex<double>> a(n);
    for (std::size_t i = 0; i < n; ++i) {  // 4-term Blackman-Harris
        const double t = 2 * kPi * double(i) / double(n - 1);
        const double w = 0.35875 - 0.48829 * std::cos(t) + 0.14128 * std::cos(2 * t) - 0.01168 * std::cos(3 * t);
        a[i] = w * double(x[i0 + i]);
    }
    fft(a);
    double harm = 0, other = 0, total = 0;
    const double binHz = sr / double(n);
    for (std::size_t k = 1; k < n / 2; ++k) total += std::norm(a[k]);
    for (std::size_t k = 1; k < n / 2; ++k) {
        const double f = double(k) * binHz;
        if (f > 20000.0) break;
        const double e = std::norm(a[k]);
        const double h = f / f0;
        const double distBins = std::fabs(h - std::round(h)) * f0 / binHz;
        if (std::round(h) >= 1 && distBins <= 6.0) harm += e;
        else other += e;
    }
    return 10.0 * std::log10(std::max(other, 1e-30) / std::max(relToTotal ? total : harm, 1e-30));
}

// Largest second difference (a click is a spike of it) in [a, b] seconds.
double maxD2(const std::vector<float>& x, double sr, double a, double b) {
    const std::size_t i0 = std::max<std::size_t>(2, static_cast<std::size_t>(a * sr));
    const std::size_t i1 = std::min(x.size(), static_cast<std::size_t>(b * sr));
    double m = 0;
    for (std::size_t i = i0; i < i1; ++i) m = std::max(m, std::fabs(double(x[i]) - 2.0 * x[i - 1] + x[i - 2]));
    return m;
}

json clean(json extra = json::object()) {  // deterministic, open filter, no drift
    json j = {{"drift.pitch", 0}, {"drift.cutoff", 0}, {"cutoff", 20000}, {"resonance", 0}, {"filter.env", 0},
              {"filter.keytrack", 0}, {"filter.velocity", 0}, {"filter.drive", 0}, {"amp.velocity", 0},
              {"amp.attack", 0.002}, {"amp.sustain", 1.0}, {"filter.type", "lp12"}};
    for (auto it = extra.begin(); it != extra.end(); ++it) j[it.key()] = it.value();
    return j;
}

// params + one mods routing
json mods(json params, const json& src, const char* target, double amount, const std::string& id = "") {
    json r = json::object();
    r["source"] = src;
    r["target"] = target;
    r["amount"] = amount;
    if (!id.empty()) r["id"] = id;
    params["mods"] = json::array();
    params["mods"].push_back(r);
    return params;
}

bool throwsConfig(const json& j, std::string* msg = nullptr, bool va = false) {
    try {
        if (va) {
            auto i = as::makeVaSynth();
            i->configure(j);
        } else {
            make(j);
        }
    } catch (const as::ConfigError& e) {
        if (msg) *msg = e.what();
        return true;
    }
    return false;
}

// ---------------------------------------------------------------------------------------------
// Synthetic table files

void put32(std::vector<unsigned char>& b, std::uint32_t v) {
    for (int i = 0; i < 4; ++i) b.push_back(static_cast<unsigned char>(v >> (8 * i)));
}
void put16(std::vector<unsigned char>& b, std::uint16_t v) {
    b.push_back(static_cast<unsigned char>(v));
    b.push_back(static_cast<unsigned char>(v >> 8));
}
void putTag(std::vector<unsigned char>& b, const char* t) { b.insert(b.end(), t, t + 4); }

// WAV (mono) of float32 or PCM16 samples, with an optional extra chunk before 'data'.
void writeWav(const fs::path& p, const std::vector<float>& x, bool pcm16, const char* chunkTag = nullptr,
              const std::vector<unsigned char>& chunk = {}) {
    std::vector<unsigned char> body;
    putTag(body, "WAVE");
    putTag(body, "fmt ");
    put32(body, 16);
    put16(body, pcm16 ? 1 : 3);
    put16(body, 1);
    put32(body, 44100);
    const int bytes = pcm16 ? 2 : 4;
    put32(body, 44100u * static_cast<std::uint32_t>(bytes));
    put16(body, static_cast<std::uint16_t>(bytes));
    put16(body, static_cast<std::uint16_t>(8 * bytes));
    if (chunkTag) {
        putTag(body, chunkTag);
        put32(body, static_cast<std::uint32_t>(chunk.size()));
        body.insert(body.end(), chunk.begin(), chunk.end());
        if (chunk.size() & 1u) body.push_back(0);
    }
    putTag(body, "data");
    put32(body, static_cast<std::uint32_t>(x.size() * static_cast<std::size_t>(bytes)));
    for (float v : x) {
        if (pcm16) {
            put16(body, static_cast<std::uint16_t>(static_cast<std::int16_t>(std::lround(std::clamp(v, -1.0f, 1.0f) * 32767.0f))));
        } else {
            std::uint32_t u;
            std::memcpy(&u, &v, 4);
            put32(body, u);
        }
    }
    std::vector<unsigned char> file;
    putTag(file, "RIFF");
    put32(file, static_cast<std::uint32_t>(body.size()));
    file.insert(file.end(), body.begin(), body.end());
    std::FILE* f = std::fopen(p.string().c_str(), "wb");
    std::fwrite(file.data(), 1, file.size(), f);
    std::fclose(f);
}

void writeSurgeWt(const fs::path& p, const std::vector<float>& x, int frameSize, int frames, bool int16) {
    std::vector<unsigned char> b;
    putTag(b, "vawt");
    put32(b, static_cast<std::uint32_t>(frameSize));
    put16(b, static_cast<std::uint16_t>(frames));
    put16(b, int16 ? 0x4 : 0x0);
    for (float v : x) {
        if (int16) {
            put16(b, static_cast<std::uint16_t>(static_cast<std::int16_t>(std::lround(v * 16384.0f))));
        } else {
            std::uint32_t u;
            std::memcpy(&u, &v, 4);
            put32(b, u);
        }
    }
    std::FILE* f = std::fopen(p.string().c_str(), "wb");
    std::fwrite(b.data(), 1, b.size(), f);
    std::fclose(f);
}

// `frames` frames of `size` samples; frame f = sin(2 pi (f + 1) t): a table whose frames are told apart by
// their harmonic number.
std::vector<float> harmonicFrames(int size, int frames, double amp = 0.8) {
    std::vector<float> x;
    for (int f = 0; f < frames; ++f)
        for (int n = 0; n < size; ++n) x.push_back(static_cast<float>(amp * std::sin(2 * kPi * (f + 1) * n / size)));
    return x;
}

// Max deviation of a loaded table (level 0, every frame) from sin(2 pi (f + 1) t) (the table is
// normalised to peak 1).
double frameError(const as::wt::Table& t) {
    double e = 0;
    for (int f = 0; f < t.frames; ++f)
        for (int k = 0; k < 97; ++k) {
            const double ph = (k + 0.31) / 97.0;
            e = std::max(e, std::fabs(t.read(0, static_cast<float>(f), ph) - std::sin(2 * kPi * (f + 1) * ph)));
        }
    return e;
}

fs::path tmpDir() {
    const fs::path d = fs::temp_directory_path() / "agentsound_test_wavetable";
    fs::create_directories(d);
    return d;
}

void setEnv(const char* k, const std::string& v) {
#ifdef _WIN32
    _putenv_s(k, v.c_str());
#else
    setenv(k, v.c_str(), 1);
#endif
}

// ---------------------------------------------------------------------------------------------

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

void testSpecs() {
    std::cout << "specs and strictness\n";
    auto inst = as::makeWavetableSynth();
    const auto& sp = inst->paramSpecs();
    auto has = [&](const char* n) {
        for (const auto& s : sp)
            if (s.name == n) return true;
        return false;
    };
    bool helps = true;
    for (const auto& s : sp) helps = helps && s.help.size() > 10;
    check(helps, fmt("every one of the %d params has a help text", static_cast<int>(sp.size())));
    check(has("osc1.table") && has("osc1.position") && has("osc2.warp") && has("osc2.warp.amount") && has("sub.wave") &&
              has("unison") && has("cutoff") && has("mods") && has("amp.attack") && has("osc1.framesize"),
          "wavetable params present (tables, positions, warps, sub.wave + the shared va engine's)");
    check(!has("osc1.wave") && !has("osc1.pw") && !has("fm") && !has("osc2.sync"), "no analog waveform params");
    std::string msg;
    check(throwsConfig({{"osc1.wave", "saw"}}, &msg) && msg.find("osc1.wave") != std::string::npos, "unknown key 'osc1.wave' -> error");
    check(throwsConfig({{"osc1.table", "bogus"}}, &msg) && msg.find("basic") != std::string::npos,
          "unknown built-in table -> error listing the built-ins: " + msg);
    check(throwsConfig({{"osc1.table", 3}}), "a non-string table -> error");
    check(throwsConfig({{"osc1.table", "basic"}, {"osc1.framesize", 2048}}), "framesize with a built-in -> error");
    check(throwsConfig({{"osc1.framesize", 100.5}}), "fractional framesize -> error");
    check(throwsConfig({{"osc1.position", 1.5}}), "position out of range -> error");
    check(throwsConfig({{"osc1.warp", "fold"}}), "unknown warp -> error");
    check(throwsConfig({{"osc1.table", "missing_table.wav"}}, &msg) && msg.find("not found") != std::string::npos,
          "missing table file -> error at prepare: " + msg);
    const json lfo = {{"type", "lfo"}, {"shape", "sine"}, {"rateHz", 1}};
    check(throwsConfig(mods(json::object(), lfo, "osc1.pw", 0.2), &msg) &&
              msg.find("osc1.position") != std::string::npos,
          "mods target osc1.pw (va only) -> error listing the wavetable targets");
    check(!throwsConfig(mods(json::object(), lfo, "osc1.position", 0.5, "morph")),
          "mods target osc1.position accepted");
    check(throwsConfig(mods(json::object(), lfo, "osc1.position", 0.5), &msg, true),
          "the va rejects the wavetable target osc1.position");
    auto m = make(mods(json::object(), lfo, "osc2.warp", 0.5, "wm"));
    check(m->setParam("mod.wm.amount", 0.2f) && m->setParam("osc1.position", 0.5f) && m->setParam("osc2.warp.amount", 0.3f) &&
              !m->setParam("osc1.table", 1.0f) && !m->setParam("osc1.warp", 1.0f),
          "automatable: positions, warp amounts, routing amounts; not: tables, warp types");
}

void testLoaders() {
    std::cout << "file loaders (synthetic files)\n";
    const fs::path d = tmpDir();
    using as::wt::readFile;
    using as::wt::load;

    // Serum: 'clm ' chunk with "<!>256" -> 4 frames of 256 (float32)
    {
        const std::string clm = "<!>256 10000000 wavetable (www.xferrecords.com)";
        writeWav(d / "serum.wav", harmonicFrames(256, 4), false, "clm ", std::vector<unsigned char>(clm.begin(), clm.end()));
        const auto r = readFile((d / "serum.wav").string());
        check(r.frameSize == 256 && r.frames == 4 && r.format == "serum",
              fmt("Serum clm WAV: frame size %d, %d frames, format %s", r.frameSize, r.frames, r.format.c_str()));
        const auto t = load((d / "serum.wav").string());
        const double e = frameError(*t);
        check(t->frames == 4 && e < 2e-3, fmt("Serum table resampled 256 -> 2048: frames are harmonics 1..4 (max error %.1e)", e));
    }
    // Surge .wt float32 (512 x 3) and int16 (128 x 5)
    {
        writeSurgeWt(d / "surge_f.wt", harmonicFrames(512, 3), 512, 3, false);
        const auto r = readFile((d / "surge_f.wt").string());
        check(r.frameSize == 512 && r.frames == 3 && r.format == "surge-wt", fmt("Surge .wt float32: %d x %d", r.frameSize, r.frames));
        const double e = frameError(*load((d / "surge_f.wt").string()));
        check(e < 2e-3, fmt("Surge .wt float32 frames read back (max error %.1e)", e));
        writeSurgeWt(d / "surge_i.wt", harmonicFrames(128, 5, 0.9), 128, 5, true);
        const auto r2 = readFile((d / "surge_i.wt").string());
        const double e2 = frameError(*load((d / "surge_i.wt").string()));
        check(r2.frameSize == 128 && r2.frames == 5 && e2 < 2e-3,
              fmt("Surge .wt int16: %d x %d, frames read back (max error %.1e)", r2.frameSize, r2.frames, e2));
        check(throwsConfig({{"osc1.table", (d / "surge_f.wt").string()}, {"osc1.framesize", 256}}),
              "a framesize that contradicts the .wt header -> error");
    }
    // Surge WAV: 'srge' chunk (version 1, frame size 1024), PCM16
    {
        std::vector<unsigned char> c;
        put32(c, 1);
        put32(c, 1024);
        writeWav(d / "surge.wav", harmonicFrames(1024, 2), true, "srge", c);
        const auto r = readFile((d / "surge.wav").string());
        const double e = frameError(*load((d / "surge.wav").string()));
        check(r.frameSize == 1024 && r.frames == 2 && r.format == "surge-wav" && e < 2e-3,
              fmt("Surge srge WAV (PCM16): %d x %d, %s, max error %.1e", r.frameSize, r.frames, r.format.c_str(), e));
    }
    // Plain WAV (Ableton / Vital export): 3 x 2048 auto-detected; 5 x 1024 by length; forced frame size
    {
        writeWav(d / "plain2048.wav", harmonicFrames(2048, 3), false);
        const auto r = readFile((d / "plain2048.wav").string());
        check(r.frameSize == 2048 && r.frames == 3 && r.format == "wav", fmt("plain WAV 3 x 2048: detected %d x %d", r.frameSize, r.frames));
        writeWav(d / "plain1024.wav", harmonicFrames(1024, 5), false);
        const auto r2 = readFile((d / "plain1024.wav").string());
        check(r2.frameSize == 1024 && r2.frames == 5, fmt("plain WAV 5 x 1024 (no 2048 multiple): detected %d x %d", r2.frameSize, r2.frames));
        const auto r3 = readFile((d / "plain2048.wav").string(), 512);
        check(r3.frameSize == 512 && r3.frames == 12, fmt("framesize 512 forced: %d x %d", r3.frameSize, r3.frames));
        writeWav(d / "plain_bad.wav", std::vector<float>(5000, 0.1f), false);
        std::string msg;
        bool threw = false;
        try { readFile((d / "plain_bad.wav").string()); } catch (const as::ConfigError& e) { threw = true; msg = e.what(); }
        check(threw && msg.find("framesize") != std::string::npos, "5000 samples, no chunk -> error asking for the frame size");
    }
    // Single cycle (AKWF-style 600 samples, PCM16): one frame resampled to 2048
    {
        std::vector<float> x(600);
        for (int n = 0; n < 600; ++n) x[static_cast<std::size_t>(n)] = static_cast<float>(0.7 * std::sin(2 * kPi * n / 600.0));
        writeWav(d / "akwf_0001.wav", x, true);
        const auto r = readFile((d / "akwf_0001.wav").string());
        const auto t = load((d / "akwf_0001.wav").string());
        const double e = frameError(*t);
        check(r.frameSize == 600 && r.frames == 1 && r.format == "single-cycle" && e < 2e-3,
              fmt("single-cycle 600-sample WAV: 1 frame, resampled (max error %.1e)", e));
        // a 600-sample saw: band-limited and its harmonics kept (harmonic 3 at 1/3 of the fundamental)
        for (int n = 0; n < 600; ++n) x[static_cast<std::size_t>(n)] = static_cast<float>(1.0 - 2.0 * n / 600.0);
        writeWav(d / "akwf_saw.wav", x, false);
        auto o = renderPatch(clean({{"osc1.table", (d / "akwf_saw.wav").string()}}), {on(0, 1, 57, 48000)}, 0.6);
        const double h1 = tone(o.L, 48000, 220, 0.1, 0.6), h3 = tone(o.L, 48000, 660, 0.1, 0.6);
        check(std::fabs(db(h3 / h1) + 9.54) < 0.5, fmt("AKWF saw played at A3: harmonic 3 at %.2f dB (saw: -9.54)", db(h3 / h1)));
    }
    // Not a table file
    {
        std::FILE* f = std::fopen((d / "junk.wav").string().c_str(), "wb");
        std::fputs("this is not a wav", f);
        std::fclose(f);
        bool threw = false;
        try { readFile((d / "junk.wav").string()); } catch (const as::ConfigError&) { threw = true; }
        check(threw, "a non-WAV file -> ConfigError");
    }
    // The user dir ($AGENTSOUND_WAVETABLES) resolves relative names; the instrument plays a file table
    {
        setEnv("AGENTSOUND_WAVETABLES", d.string());
        const std::string resolved = as::wt::resolvePath("assets", "serum.wav");
        check(fs::equivalent(resolved, d / "serum.wav"), "relative name found in $AGENTSOUND_WAVETABLES");
        auto o = renderPatch(clean({{"osc1.table", "serum.wav"}, {"osc1.position", 1.0}}), {on(0, 1, 57, 48000)}, 0.5);
        const double h4 = tone(o.L, 48000, 880, 0.1, 0.5), h1 = tone(o.L, 48000, 220, 0.1, 0.5);
        check(allFinite(o) && h4 > 0.05 && h4 > 100 * h1, fmt("file table at position 1 plays frame 4 (harmonic 4 %.1f dB over the fundamental)", db(h4 / h1)));
        setEnv("AGENTSOUND_WAVETABLES", "");
    }
}

void testBuiltins() {
    std::cout << "built-in tables\n";
    for (const auto& n : as::wt::builtinNames()) {
        const auto t = as::wt::builtin(n);
        bool fin = true;
        float pk = 0;
        for (float v : t->data) { fin = fin && std::isfinite(v); pk = std::max(pk, std::fabs(v)); }
        double lo = 1e9, hi = 0;  // frame loudness (RMS of level 0) across the table
        for (int f = 0; f < t->frames; ++f) {
            const float* x = t->frame(0, f);
            double e = 0;
            for (int i = 0; i < t->levelSize[0]; ++i) e += double(x[i]) * x[i];
            const double r = std::sqrt(e / t->levelSize[0]);
            lo = std::min(lo, r);
            hi = std::max(hi, r);
        }
        const double spread = db(hi / lo), allowed = n == "pwm" ? 14.0 : 8.0;  // (pwm: thin pulses are quieter)
        check(fin && pk > 0.9f && pk < 1.2f && t->frames >= 1 && spread < allowed,
              fmt("built-in '%s': %d frames, finite, peak %.2f, frame RMS %.1f .. %.1f dB (spread %.1f dB)", n.c_str(),
                  t->frames, pk, db(lo), db(hi), spread));
    }
    const double sr = 48000;
    auto sine = renderPatch(clean({{"osc1.position", 0.0}}), {on(0, 1, 57, sr)}, 0.6);
    auto sq = renderPatch(clean({{"osc1.position", 1.0}}), {on(0, 1, 57, sr)}, 0.6);
    auto saw = renderPatch(clean({{"osc1.position", 2.0 / 3.0}}), {on(0, 1, 57, sr)}, 0.6);
    const double s1 = tone(sine.L, sr, 220, 0.1, 0.6), s2 = tone(sine.L, sr, 440, 0.1, 0.6);
    check(db(s2 / s1) < -70, fmt("basic at 0 is a sine (harmonic 2 at %.0f dB)", db(s2 / s1)));
    const double q1 = tone(sq.L, sr, 220, 0.1, 0.6), q2 = tone(sq.L, sr, 440, 0.1, 0.6), q3 = tone(sq.L, sr, 660, 0.1, 0.6);
    check(std::fabs(db(q3 / q1) + 9.54) < 0.5 && db(q2 / q1) < -50,
          fmt("basic at 1 is a square (h3 %.2f dB, h2 %.0f dB)", db(q3 / q1), db(q2 / q1)));
    const double w1 = tone(saw.L, sr, 220, 0.1, 0.6), w2 = tone(saw.L, sr, 440, 0.1, 0.6);
    check(std::fabs(db(w2 / w1) + 6.02) < 0.5, fmt("basic at 2/3 is a saw (h2 %.2f dB)", db(w2 / w1)));
}

// The oscillator alone: a table read at the internal rate (96 kHz) with the level the synth picks; the
// inharmonic energy below 20 kHz (images of the interpolation, folded partials) relative to the whole signal.
double tableInharmonicDb(const as::wt::Table& t, float pos, double f0, double fs = 96000.0) {
    const double inc = f0 / fs;
    const int level = as::wt::Table::levelFor(inc);
    std::vector<float> x(static_cast<std::size_t>(fs * 0.5));
    double ph = 0.123;
    for (auto& v : x) {
        ph += inc;
        if (ph >= 1.0) ph -= 1.0;
        v = t.read(level, pos, ph);
    }
    if (rms(x, fs, 0.05, 0.5) < 1e-3) return -300.0;  // nothing in band (e.g. 'sync' at ratio 8 above 6 kHz: all partials > Nyquist)
    return inharmonicDb(x, fs, f0, 0.05, true);
}

void testAliasing() {
    std::cout << "anti-aliasing (mip levels)\n";
    // The oscillator alone (mip levels + Hermite interpolation), every note 36..127 of every built-in table at
    // its first, middle, last and an in-between frame (96 kHz = the oscillator's rate at 48 kHz).
    for (const auto& name : as::wt::builtinNames()) {
        const auto t = as::wt::builtin(name);
        double worst = -300;
        int worstNote = 0;
        const float last = static_cast<float>(t->frames - 1);
        for (int note = 36; note <= 127; ++note) {
            for (float pos : {0.0f, std::floor(last * 0.5f), last, last * 0.66f + 0.37f}) {
                const double r = tableInharmonicDb(*t, std::min(pos, last), 440.0 * std::pow(2.0, (note - 69) / 12.0));
                if (r > worst) { worst = r; worstNote = note; }
            }
        }
        check(worst < -65.0, fmt("oscillator alone, '%s' (4 positions, notes 36..127): worst inharmonic energy %.1f dB "
                                 "(note %d)", name.c_str(), worst, worstNote));
    }
    // Through the voice (drive stage, filter, 2x decimation: the va's shared path, whose nonlinear stages fold a
    // little of the top partials back): the wavetable saw / square alias no more than the va's BLEP oscillators.
    for (double sr : {44100.0, 48000.0}) {
        for (int shape = 0; shape < 2; ++shape) {
            for (int note : {84, 96, 108, 120, 127}) {
                const double f0 = 440.0 * std::pow(2.0, (note - 69) / 12.0);
                auto o = renderPatch(clean({{"osc1.position", shape ? 1.0 : 2.0 / 3.0}}), {on(0, 1, note, sr)}, 1.0, sr);
                const double r = inharmonicDb(o.L, sr, f0, 0.1);
                auto va = as::makeVaSynth();
                json vp = clean({{"osc1.wave", shape ? "square" : "saw"}});
                va->configure(vp);
                as::RenderContext ctx;
                ctx.sampleRate = sr;
                va->prepare(ctx);
                const double rv = inharmonicDb(render(*va, {on(0, 1, note, sr)}, 1.0, sr).L, sr, f0, 0.1);
                check(r < -60.0 && r <= rv + 3.0, fmt("%s note %d at %.0f Hz: inharmonic energy %.1f dB (the va's %s: %.1f)",
                                                       shape ? "square" : "saw", note, sr, r, shape ? "square" : "saw", rv));
            }
        }
    }
    const double sr = 48000;
    for (const char* table : {"sync", "harmonics", "formant", "pwm"}) {
        for (int note : {84, 96}) {
            auto o = renderPatch(clean({{"osc1.table", table}, {"osc1.position", 0.9}}), {on(0, 1, note, sr)}, 1.0, sr);
            const double r = inharmonicDb(o.L, sr, 440.0 * std::pow(2.0, (note - 69) / 12.0), 0.1);
            check(r < -60.0, fmt("'%s' at position 0.9, note %d, through the voice: inharmonic energy %.1f dB", table, note, r));
        }
    }
    // warps add partials; the mip level follows the warp's multiplier, so they stay usable at high notes
    for (const char* warp : {"sync", "bend", "mirror"}) {
        auto o = renderPatch(clean({{"osc1.position", 2.0 / 3.0}, {"osc1.warp", warp}, {"osc1.warp.amount", 0.5}}),
                             {on(0, 1, 96, sr)}, 1.0, sr);
        const double r = inharmonicDb(o.L, sr, 440.0 * std::pow(2.0, (96 - 69) / 12.0), 0.1);
        check(r < -30.0, fmt("warp %s 0.5 on the saw at C7 (not band-limited: 2x oversampled only): inharmonic energy %.1f dB", warp, r));
    }
}

void testMorph() {
    std::cout << "morph continuity\n";
    const double sr = 48000;
    // a position jump sine -> triangle (both smooth: any step in the output would be a spike of the 2nd difference)
    auto j = renderPatch(clean(), {on(0, 1, 45, sr), prm(0.5, "osc1.position", 1.0f / 3.0f, sr)}, 1.0, sr);
    const double steadyA = maxD2(j.L, sr, 0.2, 0.5), during = maxD2(j.L, sr, 0.5, 0.55), steadyB = maxD2(j.L, sr, 0.7, 1.0);
    check(during <= 1.15 * std::max(steadyA, steadyB),
          fmt("position jump 0 -> 1/3 (sine -> triangle) at A2: 2nd difference %.2e during vs %.2e / %.2e steady", during,
              steadyA, steadyB));
    // a fast LFO sweep across the whole table (sine .. square) never exceeds the square's own edges
    const json lfo = {{"type", "lfo"}, {"shape", "triangle"}, {"rateHz", 3}, {"unipolar", true}};
    auto sw = renderPatch(mods(clean(), lfo, "osc1.position", 1.0),
                          {on(0, 1, 45, sr)}, 1.5, sr);
    auto sq = renderPatch(clean({{"osc1.position", 1.0}}), {on(0, 1, 45, sr)}, 1.0, sr);
    const double dSweep = maxD2(sw.L, sr, 0.1, 1.5), dSquare = maxD2(sq.L, sr, 0.1, 1.0);
    check(allFinite(sw) && dSweep <= 1.1 * dSquare,
          fmt("LFO sweep 3 Hz over the whole table: 2nd difference %.3f <= the square's %.3f", dSweep, dSquare));
    // per-sample interpolation: the position moves smoothly between control points (no 32-sample stairs)
    const json env = {{"type", "env"}, {"attack", 0.0}, {"decay", 0.3}, {"sustain", 0.0}, {"release", 0.1}};
    json ep = clean({{"osc1.table", "harmonics"}});
    auto e = renderPatch(mods(ep, env, "osc1.position", 1.0), {on(0, 1, 45, sr)}, 0.6, sr);
    auto h0 = renderPatch(clean({{"osc1.table", "harmonics"}, {"osc1.position", 1.0}}), {on(0, 1, 45, sr)}, 0.6, sr);
    const double dEnv = maxD2(e.L, sr, 0.0, 0.6), dTop = maxD2(h0.L, sr, 0.1, 0.6);
    check(dEnv <= 1.1 * dTop, fmt("env -> position (harmonics, falling from the brightest frame): 2nd diff %.3f <= %.3f", dEnv, dTop));
    const double early = tone(e.L, sr, 110.0 * 32, 0.0, 0.05), late = tone(e.L, sr, 110.0 * 32, 0.4, 0.6);
    check(early > 10 * late, fmt("env -> position: harmonic 32 fades with the envelope (%.1f dB)", db(early / late)));
}

void testWarpsAndSub() {
    std::cout << "warps, osc2, sub, noise\n";
    const double sr = 48000;
    const json base = clean({{"osc1.position", 0.0}});
    auto plain = renderPatch(base, {on(0, 1, 57, sr)}, 0.5, sr);
    const double p2 = tone(plain.L, sr, 440, 0.1, 0.5);
    for (const char* w : {"sync", "bend", "mirror", "fm"}) {
        json j = base;
        j["osc1.warp"] = w;
        j["osc1.warp.amount"] = 0.6;
        if (std::string(w) == "fm") { j["osc2.table"] = "sine"; j["osc2.semi"] = 12; }
        auto o = renderPatch(j, {on(0, 1, 57, sr)}, 0.5, sr);
        const double h2 = tone(o.L, sr, 440, 0.1, 0.5) + tone(o.L, sr, 660, 0.1, 0.5) + tone(o.L, sr, 1320, 0.1, 0.5);
        check(allFinite(o) && h2 > 30 * std::max(p2, 1e-6) && peak(o) < 1.5f,
              fmt("warp %s 0.6 on a sine adds harmonics (%.1f dB over the plain sine's), finite", w, db(h2 / std::max(p2, 1e-9))));
    }
    // osc2 an octave up from another table, the sub an octave down
    auto o = renderPatch(clean({{"osc1.level", 0.0}, {"osc2.level", 0.4}, {"osc2.table", "sine"}, {"osc2.semi", 12},
                                {"sub.level", 0.4}, {"sub.wave", "sine"}}),
                         {on(0, 1, 57, sr)}, 0.5, sr);
    const double a440 = tone(o.L, sr, 440, 0.1, 0.5), a110 = tone(o.L, sr, 110, 0.1, 0.5), a220 = tone(o.L, sr, 220, 0.1, 0.5);
    check(a440 > 0.02 && a110 > 0.02 && a220 < 0.03 * a440, fmt("osc2 (+12) and a sine sub (-12): %.3f / %.3f, osc1 off (%.4f)", a440, a110, a220));
    auto n = renderPatch(clean({{"osc1.level", 0.0}, {"noise.level", 1.0}}), {on(0, 1, 57, sr)}, 0.5, sr);
    check(rms(n.L, sr, 0.1, 0.5) > 0.02, "noise source works");
}

void testDeterminismAndFinite() {
    std::cout << "determinism, unison, finite output, speed\n";
    const double sr = 48000;
    const json p = {{"osc1.table", "formant"}, {"osc2.table", "harmonics"}, {"osc2.level", 0.6}, {"unison", 5},
                    {"unison.detune", 0.4}, {"osc1.position", 0.3}, {"drift.pitch", 4}};
    std::vector<Ev> evs = {on(0, 1, 48, sr), on(0.1, 2, 55, sr), on(0.2, 3, 64, sr), off(0.8, 1, sr), off(0.9, 2, sr), off(1.0, 3, sr)};
    auto a = renderPatch(p, evs, 1.5, sr, 7), b = renderPatch(p, evs, 1.5, sr, 7), c = renderPatch(p, evs, 1.5, sr, 8);
    check(a.L == b.L && a.R == b.R, "same seed -> bit-identical (unison phases from dsp::Rng)");
    check(a.L != c.L, "another seed -> other unison phases / drift");
    double side = 0;
    for (std::size_t i = 0; i < a.L.size(); ++i) side += std::fabs(a.L[i] - a.R[i]);
    check(side > 1.0, "unison spreads in stereo");
    // stress: every warp at full amount, resonance, drive, unison 9, extreme notes
    bool fin = true;
    float pk = 0;
    for (const char* w : {"none", "sync", "bend", "mirror", "fm"}) {
        json j = {{"osc1.table", "sync"}, {"osc2.table", "pwm"}, {"osc2.level", 1.0}, {"osc1.warp", w}, {"osc1.warp.amount", 1.0},
                  {"osc2.warp", w}, {"osc2.warp.amount", 1.0}, {"unison", 9}, {"unison.detune", 1.0}, {"resonance", 1.0},
                  {"filter.drive", 1.0}, {"sub.level", 1.0}, {"noise.level", 0.5}};
        auto o = renderPatch(j, {on(0, 1, 0, sr), on(0, 2, 127, sr), on(0.1, 3, 60, sr), off(0.6, 1, sr)}, 1.0, sr);
        fin = fin && allFinite(o);
        pk = std::max(pk, peak(o));
    }
    check(fin && pk < 2.5f, fmt("all warps at 1, resonance 1, drive 1, unison 9, notes 0..127: finite (peak %.2f)", pk));
    // speed: 8 notes x unison 7, two oscillators
    json s = {{"osc1.table", "basic"}, {"osc2.table", "harmonics"}, {"osc2.level", 0.7}, {"unison", 7}, {"osc1.position", 0.5}};
    std::vector<Ev> ch;
    for (int k = 0; k < 8; ++k) ch.push_back(on(0, k + 1, 48 + 3 * k, sr));
    double best = 1e9;
    for (int k = 0; k < 3; ++k) {  // thread CPU time, best of 3 (other processes do not count)
        auto inst = make(s, sr);
        const double t0 = threadCpuSeconds();
        auto o = render(*inst, ch, 4.0, sr);
        best = std::min(best, threadCpuSeconds() - t0);
        fin = fin && allFinite(o);
    }
    check(fin && best < 4.0 / 2.0, fmt("8 voices x unison 7 x 2 oscillators: %.1fx realtime (> 2x)", 4.0 / best));
}

}  // namespace

int main() {
    testSpecs();
    testLoaders();
    testBuiltins();
    testAliasing();
    testMorph();
    testWarpsAndSub();
    testDeterminismAndFinite();
    if (failures) {
        std::cout << failures << " wavetable test(s) FAILED\n";
        return 1;
    }
    std::cout << "all wavetable tests passed\n";
    return 0;
}
