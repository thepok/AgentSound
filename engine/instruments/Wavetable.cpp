#include "instruments/Wavetable.h"

#include "core/Params.h"
#include "dsp/Fft.h"
#include "io/WavReader.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <map>
#include <mutex>

namespace as::wt {
namespace {

namespace fs = std::filesystem;
constexpr double kPi = 3.14159265358979323846;

int levelHarmonics(int k) { return kHarmonics >> k; }
int levelSizeFor(int k) { return std::max(kMinLevelSize, (k < 2 ? kOversample / 2 : kOversample) * levelHarmonics(k)); }

const dsp::Fft& fftOf(int n) {
    static std::mutex m;
    static std::map<int, std::unique_ptr<dsp::Fft>> cache;
    std::lock_guard<std::mutex> lock(m);
    auto& p = cache[n];
    if (!p) p = std::make_unique<dsp::Fft>(n);
    return *p;
}

bool isPow2(int n) { return n >= 4 && (n & (n - 1)) == 0; }

// Harmonics 1..H of one frame of M samples: x = sum c_h cos(2 pi h t) + s_h sin(2 pi h t).
Spectrum analyse(const float* x, int m) {
    const int h = std::min(kHarmonics, m / 2);
    Spectrum sp;
    sp.c.assign(static_cast<std::size_t>(h), 0.0f);
    sp.s.assign(static_cast<std::size_t>(h), 0.0f);
    if (isPow2(m)) {
        const dsp::Fft& f = fftOf(m);
        std::vector<float> re(x, x + m), im(static_cast<std::size_t>(m), 0.0f);
        f.forwardDif(re.data(), im.data());  // X[k] at bitReversed()[k]
        const int* rev = f.bitReversed();
        for (int k = 1; k <= h; ++k) {
            const auto j = static_cast<std::size_t>(rev[k]);
            const float scale = (2 * k == m ? 1.0f : 2.0f) / static_cast<float>(m);
            sp.c[static_cast<std::size_t>(k - 1)] = re[j] * scale;
            sp.s[static_cast<std::size_t>(k - 1)] = -im[j] * scale;
        }
        return sp;
    }
    // Any other length (AKWF 600, 1000 ...): a direct DFT over a cosine table.
    std::vector<double> cs(static_cast<std::size_t>(m)), sn(static_cast<std::size_t>(m));
    for (int n = 0; n < m; ++n) {
        cs[static_cast<std::size_t>(n)] = std::cos(2.0 * kPi * n / m);
        sn[static_cast<std::size_t>(n)] = std::sin(2.0 * kPi * n / m);
    }
    for (int k = 1; k <= h; ++k) {
        double a = 0.0, b = 0.0;
        std::int64_t idx = 0;
        for (int n = 0; n < m; ++n) {
            a += x[n] * cs[static_cast<std::size_t>(idx)];
            b += x[n] * sn[static_cast<std::size_t>(idx)];
            idx += k;
            if (idx >= m) idx -= m;
        }
        const double scale = (2 * k == m ? 1.0 : 2.0) / m;
        sp.c[static_cast<std::size_t>(k - 1)] = static_cast<float>(a * scale);
        sp.s[static_cast<std::size_t>(k - 1)] = static_cast<float>(b * scale);
    }
    return sp;
}

std::string lower(std::string s) {
    for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

// ---------------------------------------------------------------------------------------------
// Built-in procedural tables (spectra, so they are band-limited by construction)

constexpr int kBuiltinFrames = 64;

// Harmonic h with amplitude a at a Schroeder phase (pi h^2 / n): many partials of similar level do not all
// peak together, so every frame has a similar crest factor and the table's peak normalisation keeps the
// frames at similar loudness.
void setPartial(Spectrum& s, int h, double a, int n) {
    const double ph = kPi * static_cast<double>(h) * static_cast<double>(h) / n;
    s.c[static_cast<std::size_t>(h - 1)] = static_cast<float>(a * std::sin(ph));
    s.s[static_cast<std::size_t>(h - 1)] = static_cast<float>(a * std::cos(ph));
}

Spectrum empty(int h) {
    Spectrum s;
    s.c.assign(static_cast<std::size_t>(h), 0.0f);
    s.s.assign(static_cast<std::size_t>(h), 0.0f);
    return s;
}

// sine -> triangle -> saw -> square (all in sine phase, so neighbouring shapes add up instead of cancelling)
std::vector<Spectrum> basicShapes() {
    auto shape = [](int which) {
        Spectrum s = empty(kHarmonics);
        for (int h = 1; h <= kHarmonics; ++h) {
            double a = 0.0;
            switch (which) {
                case 0: a = h == 1 ? 1.0 : 0.0; break;
                case 1: a = (h % 2) ? 8.0 / (kPi * kPi) / (h * h) * (((h - 1) / 2) % 2 ? -1.0 : 1.0) : 0.0; break;
                case 2: a = 2.0 / kPi / h; break;  // falling saw 1 - 2t
                default: a = (h % 2) ? 4.0 / kPi / h : 0.0; break;
            }
            s.s[static_cast<std::size_t>(h - 1)] = static_cast<float>(a);
        }
        return s;
    };
    const Spectrum keys[4] = {shape(0), shape(1), shape(2), shape(3)};
    std::vector<Spectrum> out;
    for (int f = 0; f < kBuiltinFrames; ++f) {
        const double x = 3.0 * f / (kBuiltinFrames - 1);
        const int seg = std::min(2, static_cast<int>(x));
        const float t = static_cast<float>(x - seg);
        Spectrum s = empty(kHarmonics);
        for (std::size_t h = 0; h < s.s.size(); ++h) s.s[h] = keys[seg].s[h] + t * (keys[seg + 1].s[h] - keys[seg].s[h]);
        out.push_back(std::move(s));
    }
    return out;
}

// Pulse width 50 % -> 4 % (the PWM sweep; narrower pulses are thinner and quieter, as on an analog synth)
std::vector<Spectrum> pwmShapes() {
    std::vector<Spectrum> out;
    for (int f = 0; f < kBuiltinFrames; ++f) {
        const double d = 0.5 - 0.46 * f / (kBuiltinFrames - 1);
        Spectrum s = empty(kHarmonics);
        for (int h = 1; h <= kHarmonics; ++h)
            s.c[static_cast<std::size_t>(h - 1)] = static_cast<float>(2.0 / (kPi * h) * std::sin(kPi * h * d));
        out.push_back(std::move(s));
    }
    return out;
}

// Hard-synced saw, slave ratio 1 -> 8 (the classic sync sweep), from 16x oversampled time-domain frames.
std::vector<Spectrum> syncShapes() {
    constexpr int m = 16 * kFrameSize;
    std::vector<float> x(static_cast<std::size_t>(m));
    std::vector<Spectrum> out;
    for (int f = 0; f < kBuiltinFrames; ++f) {
        const double r = 1.0 + 7.0 * f / (kBuiltinFrames - 1);
        for (int n = 0; n < m; ++n) {
            const double ph = r * (n + 0.5) / m;
            x[static_cast<std::size_t>(n)] = static_cast<float>(1.0 - 2.0 * (ph - std::floor(ph)));
        }
        out.push_back(analyse(x.data(), m));
    }
    return out;
}

// Vowels a -> e -> i -> o -> u: a saw source through three formant resonances (at a C3-A3 fundamental the
// formants sit where a voice has them; higher notes shift them up like any wavetable).
std::vector<Spectrum> formantShapes() {
    static const double F[5][3] = {{800, 1150, 2900}, {530, 1840, 2480}, {300, 2250, 3000}, {500, 850, 2800}, {330, 750, 2500}};
    static const double G[3] = {1.0, 0.6, 0.25};
    static const double B[3] = {110, 140, 220};
    constexpr double fRef = 196.0;  // G3
    constexpr int hMax = 160;
    std::vector<Spectrum> out;
    for (int f = 0; f < kBuiltinFrames; ++f) {
        const double x = 4.0 * f / (kBuiltinFrames - 1);
        const int seg = std::min(3, static_cast<int>(x));
        const double t = x - seg;
        Spectrum s = empty(hMax);
        for (int h = 1; h <= hMax; ++h) {
            const double fh = h * fRef;
            double a = 0.04;
            for (int k = 0; k < 3; ++k) {
                const double fk = F[seg][k] + t * (F[seg + 1][k] - F[seg][k]);
                const double u = (fh - fk) / B[k];
                a += G[k] / (1.0 + u * u);
            }
            setPartial(s, h, a / std::sqrt(static_cast<double>(h)), hMax);
        }
        out.push_back(std::move(s));
    }
    return out;
}

// A band of harmonics sweeping up from the fundamental to the 64th (over a constant fundamental): bright
// additive sweeps, glassy evolving pads.
std::vector<Spectrum> harmonicShapes() {
    constexpr int hMax = 256;
    std::vector<Spectrum> out;
    for (int f = 0; f < kBuiltinFrames; ++f) {
        const double c = 6.0 * f / (kBuiltinFrames - 1);
        Spectrum s = empty(hMax);
        for (int h = 1; h <= hMax; ++h) {
            const double u = (std::log2(static_cast<double>(h)) - c) / 0.55;
            double a = std::exp(-0.5 * u * u) / std::sqrt(static_cast<double>(h));
            if (h == 1) a += 0.6;
            setPartial(s, h, a, hMax);
        }
        out.push_back(std::move(s));
    }
    return out;
}

// Drawbar organ: 8' flute -> full registration (8' 4' 2 2/3' 2' 1 3/5' 1 1/3' 1').
std::vector<Spectrum> organShapes() {
    static const int H[7] = {1, 2, 3, 4, 5, 6, 8};
    static const double A[7] = {1.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0};
    static const double Z[7] = {1.0, 0.9, 0.7, 0.75, 0.5, 0.45, 0.55};
    std::vector<Spectrum> out;
    for (int f = 0; f < kBuiltinFrames; ++f) {
        const double t = static_cast<double>(f) / (kBuiltinFrames - 1);
        Spectrum s = empty(8);
        for (int k = 0; k < 7; ++k) s.s[static_cast<std::size_t>(H[k] - 1)] = static_cast<float>(A[k] + t * (Z[k] - A[k]));
        out.push_back(std::move(s));
    }
    return out;
}

struct BuiltinDef {
    const char* name;
    const char* help;
    std::vector<Spectrum> (*make)();
};
std::vector<Spectrum> sineShape() {
    Spectrum s = empty(1);
    s.s[0] = 1.0f;
    return {s};
}
const BuiltinDef kBuiltins[] = {
    {"basic", "sine -> triangle -> saw -> square (position 0, 0.33, 0.67, 1), smooth morphs between", basicShapes},
    {"pwm", "pulse 50 % (square) -> 4 % (thin, nasal): modulate the position for PWM", pwmShapes},
    {"sync", "hard-synced saw, slave ratio 1 -> 8: the sync-lead sweep", syncShapes},
    {"formant", "vowels a -> e -> i -> o -> u on a saw (formants placed for a ~G3 fundamental): talking pads, vocal leads",
     formantShapes},
    {"harmonics", "a band of harmonics sweeping from the fundamental up to the 64th: glassy, evolving additive pads",
     harmonicShapes},
    {"organ", "drawbar organ: 8' flute -> full registration", organShapes},
    {"sine", "one sine frame (sub layers, pure tones, FM modulator)", sineShape},
};

std::mutex gCacheMutex;
std::map<std::string, std::shared_ptr<const Table>>& cache() {
    static std::map<std::string, std::shared_ptr<const Table>> c;
    return c;
}

std::uint32_t u32(const unsigned char* p) { return p[0] | (p[1] << 8) | (p[2] << 16) | (static_cast<std::uint32_t>(p[3]) << 24); }
std::uint16_t u16(const unsigned char* p) { return static_cast<std::uint16_t>(p[0] | (p[1] << 8)); }

std::vector<unsigned char> readBytes(const std::string& path) {
    std::FILE* f = std::fopen(path.c_str(), "rb");
    if (!f) throw ConfigError("wavetable: cannot open '" + path + "'");
    std::vector<unsigned char> b;
    unsigned char buf[65536];
    std::size_t got;
    while ((got = std::fread(buf, 1, sizeof buf, f)) > 0) b.insert(b.end(), buf, buf + got);
    std::fclose(f);
    return b;
}

RawTable readSurgeWt(const std::vector<unsigned char>& b, const std::string& path) {
    if (b.size() < 12) throw ConfigError("wavetable '" + path + "': truncated .wt header");
    const std::uint32_t n = u32(b.data() + 4);
    const std::uint16_t count = u16(b.data() + 8), flags = u16(b.data() + 10);
    if (n < 4 || n > 65536 || count < 1) {
        throw ConfigError("wavetable '" + path + "': bad .wt header (frame size " + std::to_string(n) + ", " +
                          std::to_string(count) + " frames)");
    }
    const bool int16 = (flags & 0x4) != 0;
    const std::size_t total = static_cast<std::size_t>(n) * count, bytes = total * (int16 ? 2 : 4);
    if (b.size() < 12 + bytes) throw ConfigError("wavetable '" + path + "': .wt data is truncated");
    RawTable r;
    r.samples.resize(total);
    const unsigned char* p = b.data() + 12;
    for (std::size_t i = 0; i < total; ++i) {
        if (int16) {
            r.samples[i] = static_cast<float>(static_cast<std::int16_t>(u16(p + 2 * i))) / 32768.0f;
        } else {
            const std::uint32_t u = u32(p + 4 * i);
            float v;
            std::memcpy(&v, &u, 4);
            r.samples[i] = std::isfinite(v) ? v : 0.0f;
        }
    }
    r.frameSize = static_cast<int>(n);
    r.frames = count;
    r.format = "surge-wt";
    return r;
}

// Frame-size hints in a WAV's chunks: Serum 'clm ' ("<!>2048 ..."), Surge 'srge' / 'srgo' (version, size).
int wavHint(const std::vector<unsigned char>& b, std::string& format) {
    if (b.size() < 12 || std::memcmp(b.data(), "RIFF", 4) != 0 || std::memcmp(b.data() + 8, "WAVE", 4) != 0) return -1;
    std::size_t off = 12;
    while (off + 8 <= b.size()) {
        const unsigned char* h = b.data() + off;
        const std::uint32_t size = u32(h + 4);
        const std::size_t body = off + 8, avail = b.size() - body;
        const std::size_t len = std::min<std::size_t>(size, avail);
        if (std::memcmp(h, "clm ", 4) == 0) {
            const std::string s(reinterpret_cast<const char*>(b.data() + body), len);
            const auto at = s.find("<!>");
            if (at != std::string::npos) {
                const int v = std::atoi(s.c_str() + at + 3);
                if (v > 0) { format = "serum"; return v; }
            }
        } else if ((std::memcmp(h, "srge", 4) == 0 || std::memcmp(h, "srgo", 4) == 0) && len >= 8) {
            const int v = static_cast<int>(u32(b.data() + body + 4));
            if (v > 0) { format = "surge-wav"; return v; }
        }
        if (size > b.size()) break;
        off = body + size + (size & 1u);
    }
    return 0;
}

}  // namespace

// ---------------------------------------------------------------------------------------------

std::shared_ptr<const Table> fromSpectra(const std::vector<Spectrum>& spectra, std::string name, std::string format,
                                         int sourceFrameSize) {
    if (spectra.empty()) throw ConfigError("wavetable '" + name + "': no frames");
    if (static_cast<int>(spectra.size()) > kMaxFrames) {
        throw ConfigError("wavetable '" + name + "': " + std::to_string(spectra.size()) + " frames (at most " +
                          std::to_string(kMaxFrames) + "; a wrong frame size? set osc<N>.framesize)");
    }
    auto t = std::make_shared<Table>();
    t->name = std::move(name);
    t->format = std::move(format);
    t->frames = static_cast<int>(spectra.size());
    t->sourceFrameSize = sourceFrameSize;
    std::size_t total = 0;
    for (int k = 0; k < kLevels; ++k) {
        t->levelSize[k] = levelSizeFor(k);
        t->levelOffset[k] = total;
        total += static_cast<std::size_t>(t->frames) * t->stride(k);
    }
    t->data.assign(total, 0.0f);
    for (int k = 0; k < kLevels; ++k) {
        const int n = t->levelSize[k], hk = levelHarmonics(k);
        const dsp::Fft& f = fftOf(n);
        const int* rev = f.bitReversed();
        std::vector<float> re(static_cast<std::size_t>(n)), im(static_cast<std::size_t>(n));
        for (int fr = 0; fr < t->frames; ++fr) {
            const Spectrum& sp = spectra[static_cast<std::size_t>(fr)];
            std::fill(re.begin(), re.end(), 0.0f);
            std::fill(im.begin(), im.end(), 0.0f);
            const int h = std::min<int>(hk, static_cast<int>(sp.c.size()));
            // x[n] = Re(sum_h (c_h + i s_h) e^{-2 pi i h n / N}) via the forward transform (bit-reversed in)
            for (int j = 1; j <= h; ++j) {
                re[static_cast<std::size_t>(rev[j])] = sp.c[static_cast<std::size_t>(j - 1)];
                im[static_cast<std::size_t>(rev[j])] = sp.s[static_cast<std::size_t>(j - 1)];
            }
            f.forwardDit(re.data(), im.data());
            float* dst = t->data.data() + t->levelOffset[k] + static_cast<std::size_t>(fr) * t->stride(k);
            dst[0] = re[static_cast<std::size_t>(n - 1)];
            std::copy(re.begin(), re.end(), dst + 1);
            dst[n + 1] = re[0];
            dst[n + 2] = re[1];
        }
    }
    // Normalise the whole table (all levels) by the peak of level 0.
    float peak = 0.0f;
    const std::size_t l0 = static_cast<std::size_t>(t->frames) * t->stride(0);
    for (std::size_t i = 0; i < l0; ++i) peak = std::max(peak, std::fabs(t->data[i]));
    if (!(peak > 1e-6f) || !std::isfinite(peak))
        throw ConfigError("wavetable '" + t->name + "': the table is silent (or only DC)");
    const float g = 1.0f / peak;
    for (float& x : t->data) x *= g;
    return t;
}

std::shared_ptr<const Table> fromSamples(const std::vector<float>& samples, int frameSize, int frames, std::string name,
                                         std::string format) {
    if (frameSize < 4) throw ConfigError("wavetable '" + name + "': frame size " + std::to_string(frameSize) + " is too small");
    if (static_cast<std::size_t>(frameSize) * static_cast<std::size_t>(frames) > samples.size())
        throw ConfigError("wavetable '" + name + "': fewer samples than frames x frame size");
    if (frames > kMaxFrames) {
        throw ConfigError("wavetable '" + name + "': " + std::to_string(frames) + " frames of " + std::to_string(frameSize) +
                          " samples (at most " + std::to_string(kMaxFrames) + " frames; set osc<N>.framesize if the frame "
                          "size was guessed wrong)");
    }
    std::vector<Spectrum> sp;
    sp.reserve(static_cast<std::size_t>(frames));
    for (int f = 0; f < frames; ++f)
        sp.push_back(analyse(samples.data() + static_cast<std::size_t>(f) * static_cast<std::size_t>(frameSize), frameSize));
    return fromSpectra(sp, std::move(name), std::move(format), frameSize);
}

const std::vector<std::string>& builtinNames() {
    static const std::vector<std::string> names = [] {
        std::vector<std::string> v;
        for (const auto& b : kBuiltins) v.emplace_back(b.name);
        return v;
    }();
    return names;
}

std::string builtinHelp() {
    std::string s;
    for (const auto& b : kBuiltins) s += std::string(s.empty() ? "" : "; ") + b.name + " (" + b.help + ")";
    return s;
}

bool isBuiltin(const std::string& name) {
    for (const auto& b : kBuiltins)
        if (name == b.name) return true;
    return false;
}

std::shared_ptr<const Table> builtin(const std::string& name) {
    const BuiltinDef* def = nullptr;
    for (const auto& b : kBuiltins)
        if (name == b.name) def = &b;
    if (!def) {
        std::string all;
        for (const auto& b : kBuiltins) all += std::string(all.empty() ? "" : ", ") + b.name;
        throw ConfigError("wavetable: unknown built-in table '" + name + "' (built-ins: " + all + "; or a .wav / .wt file)");
    }
    const std::string key = "builtin:" + name;
    {
        std::lock_guard<std::mutex> lock(gCacheMutex);
        const auto it = cache().find(key);
        if (it != cache().end()) return it->second;
    }
    auto t = fromSpectra(def->make(), name, "builtin", kFrameSize);
    std::lock_guard<std::mutex> lock(gCacheMutex);
    return cache().emplace(key, t).first->second;
}

bool looksLikeFile(const std::string& name) {
    const std::string l = lower(name);
    auto ends = [&](const char* e) {
        const std::size_t n = std::strlen(e);
        return l.size() > n && l.compare(l.size() - n, n, e) == 0;
    };
    return ends(".wav") || ends(".wt");
}

RawTable readFile(const std::string& path, int frameSize) {
    const std::vector<unsigned char> b = readBytes(path);
    if (b.size() >= 4 && std::memcmp(b.data(), "vawt", 4) == 0) {
        RawTable r = readSurgeWt(b, path);
        if (frameSize > 0 && frameSize != r.frameSize) {
            throw ConfigError("wavetable '" + path + "': the .wt header says " + std::to_string(r.frameSize) +
                              " samples per frame, the framesize param " + std::to_string(frameSize));
        }
        return r;
    }
    std::string hintFormat = "wav";
    const int hint = wavHint(b, hintFormat);
    if (hint < 0) throw ConfigError("wavetable '" + path + "': not a WAV (RIFF/WAVE) or Surge .wt ('vawt') file");
    WavChannels w;
    try {
        w = readWavChannels(path);
    } catch (const std::exception& e) {
        throw ConfigError("wavetable '" + path + "': " + e.what());
    }
    if (w.channels.empty() || w.channels[0].empty()) throw ConfigError("wavetable '" + path + "': no samples");
    RawTable r;
    r.samples = std::move(w.channels[0]);
    const int len = static_cast<int>(std::min<std::size_t>(r.samples.size(), 1u << 30));
    int fsz = frameSize;
    r.format = "wav";
    if (fsz <= 0 && hint > 0) {
        fsz = hint;
        r.format = hintFormat;
    }
    if (fsz <= 0) {
        if (len % 2048 == 0) fsz = 2048;
        else if (len <= 4096) { fsz = len; r.format = "single-cycle"; }
        else {
            for (int c : {4096, 1024, 512, 256})
                if (len % c == 0) { fsz = c; break; }
        }
        if (fsz <= 0) {
            throw ConfigError("wavetable '" + path + "': " + std::to_string(len) + " samples and no frame-size chunk: "
                              "cannot tell the frame size (set osc<N>.framesize, e.g. 2048)");
        }
    }
    if (fsz < 4 || fsz > 65536) throw ConfigError("wavetable '" + path + "': frame size " + std::to_string(fsz) + " is out of range 4..65536");
    if (len % fsz != 0) {
        throw ConfigError("wavetable '" + path + "': " + std::to_string(len) + " samples is not a whole number of " +
                          std::to_string(fsz) + "-sample frames");
    }
    r.frameSize = fsz;
    r.frames = len / fsz;
    return r;
}

std::shared_ptr<const Table> load(const std::string& path, int frameSize) {
    std::error_code ec;
    std::string canon = fs::weakly_canonical(fs::path(path), ec).string();
    if (ec || canon.empty()) canon = path;
    const std::string key = canon + "|" + std::to_string(frameSize);
    {
        std::lock_guard<std::mutex> lock(gCacheMutex);
        const auto it = cache().find(key);
        if (it != cache().end()) return it->second;
    }
    RawTable r = readFile(canon, frameSize);
    auto t = fromSamples(r.samples, r.frameSize, r.frames, path, r.format);
    std::lock_guard<std::mutex> lock(gCacheMutex);
    return cache().emplace(key, t).first->second;
}

std::string resolvePath(const std::string& assetDir, const std::string& file) {
    const fs::path p(file);
    std::error_code ec;
    std::vector<fs::path> tried;
    if (p.is_absolute()) {
        tried.push_back(p);
    } else {
        if (const char* env = std::getenv("AGENTSOUND_WAVETABLES"); env && *env) tried.push_back(fs::path(env) / p);
        tried.push_back(fs::path(assetDir) / "wavetables" / p);
    }
    for (const auto& c : tried)
        if (fs::is_regular_file(c, ec)) return c.string();
    std::string where;
    for (const auto& c : tried) where += (where.empty() ? "" : ", ") + c.string();
    throw ConfigError("wavetable file '" + file + "' not found (looked at: " + where + "; tables live in "
                      "$AGENTSOUND_WAVETABLES or assets/wavetables/, or give an absolute path)");
}

}  // namespace as::wt
