// Tests for the "sf2" instrument and the SoundFont 2 loader: parsing (GeneralUser GS and small SoundFonts
// built here), generator / modulator semantics, pitch accuracy, loops, velocity layers, exclusive classes,
// release and idle, determinism, preview parity, the shared file cache and render speed.
// Run from the repo root (or pass the assets folder as argv[1]).

#include "analysis/ClickDetector.h"
#include "core/Module.h"
#include "instruments/Sf2File.h"
#include "instruments/Sf2Synth.h"

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
};

std::unique_ptr<Instrument> make(const json& params, double startBeat = 0.0, double sr = kSr) {
    auto s = makeSf2Synth();
    s->configure(params);
    RenderContext ctx;
    ctx.sampleRate = sr;
    ctx.bpm = 120.0;
    ctx.assetDir = gAssets;
    ctx.startBeat = startBeat;
    s->prepare(ctx);
    return s;
}

// Renders `frames` samples, splitting blocks at events; blockSize <= 0: pseudo-random block sizes.
Audio render(Instrument& synth, std::vector<Event> events, long frames, int blockSize = 256,
             const std::function<void(long)>& atBlock = nullptr) {
    std::stable_sort(events.begin(), events.end(), [](const Event& a, const Event& b) { return a.at < b.at; });
    Audio a;
    a.l.assign(static_cast<std::size_t>(frames), 0.0f);
    a.r.assign(static_cast<std::size_t>(frames), 0.0f);
    std::size_t next = 0;
    unsigned lcg = 12345;
    for (long pos = 0; pos < frames;) {
        while (next < events.size() && events[next].at <= pos) {
            const auto& e = events[next++];
            if (e.on) synth.noteOn(e.id, e.pitch, e.vel);
            else synth.noteOff(e.id);
        }
        if (atBlock) atBlock(pos);
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
double db(double x) { return 20.0 * std::log10(std::max(x, 1e-12)); }
long sec(double s) { return static_cast<long>(std::lround(s * kSr)); }

bool finite(const Audio& a) {
    for (std::size_t i = 0; i < a.l.size(); ++i)
        if (!std::isfinite(a.l[i]) || !std::isfinite(a.r[i])) return false;
    return true;
}

int clicks(const Audio& a) {
    analysis::ClickDetector det(kSr);
    det.feed(a.l.data(), a.r.data(), static_cast<int>(a.l.size()));
    det.finish();
    return static_cast<int>(det.events().size());
}

// Fundamental by normalized autocorrelation around the expected period (parabolic peak interpolation).
double autocorrPitch(const std::vector<float>& x, long start, long len, double expectHz) {
    const double expect = kSr / expectHz;
    const int lo = static_cast<int>(expect * 0.8), hi = static_cast<int>(expect * 1.25) + 2;
    std::vector<double> r(static_cast<std::size_t>(hi + 2), 0.0);
    for (int tau = lo - 1; tau <= hi + 1; ++tau) {
        double s = 0.0, e0 = 0.0, e1 = 0.0;
        for (long i = start; i < start + len; ++i) {
            const double a = x[static_cast<std::size_t>(i)], b = x[static_cast<std::size_t>(i + tau)];
            s += a * b;
            e0 += a * a;
            e1 += b * b;
        }
        r[static_cast<std::size_t>(tau)] = s / std::sqrt(std::max(e0 * e1, 1e-30));
    }
    int best = lo;
    for (int tau = lo; tau <= hi; ++tau)
        if (r[static_cast<std::size_t>(tau)] > r[static_cast<std::size_t>(best)]) best = tau;
    const double a = r[static_cast<std::size_t>(best - 1)], b = r[static_cast<std::size_t>(best)], c = r[static_cast<std::size_t>(best + 1)];
    const double d = a - 2.0 * b + c;
    const double frac = std::fabs(d) > 1e-12 ? 0.5 * (a - c) / d : 0.0;
    return kSr / (best + frac);
}

double cents(double hz, double ref) { return 1200.0 * std::log2(hz / ref); }

// Amplitude of the component at `hz` (4-term Blackman-Harris window, -92 dB side lobes).
double tone(const std::vector<float>& x, long start, int n, double hz) {
    std::complex<double> acc = 0.0;
    double wsum = 0.0;
    for (int i = 0; i < n; ++i) {
        const double t = 2.0 * 3.14159265358979 * i / (n - 1);
        const double w = 0.35875 - 0.48829 * std::cos(t) + 0.14128 * std::cos(2 * t) - 0.01168 * std::cos(3 * t);
        acc += w * static_cast<double>(x[static_cast<std::size_t>(start + i)]) * std::polar(1.0, -2.0 * 3.14159265358979 * hz * i / kSr);
        wsum += w;
    }
    return 2.0 * std::abs(acc) / wsum;
}

// Spectral centroid (Hz) of a stretch, via a plain DFT on 2048 points.
double centroid(const std::vector<float>& x, long start) {
    const int n = 2048;
    double num = 0.0, den = 0.0;
    for (int k = 1; k < n / 2; ++k) {
        std::complex<double> acc = 0.0;
        for (int i = 0; i < n; ++i) {
            const double w = 0.5 - 0.5 * std::cos(2.0 * 3.14159265358979 * i / (n - 1));
            acc += w * static_cast<double>(x[static_cast<std::size_t>(start + i)]) * std::polar(1.0, -2.0 * 3.14159265358979 * k * i / n);
        }
        const double m = std::abs(acc);
        num += m * k * kSr / n;
        den += m;
    }
    return num / std::max(den, 1e-12);
}

// ------------------------------------------------------------------------------ SoundFont builder

struct Builder {
    struct Smp {
        std::string name;
        std::vector<std::int16_t> data;
        std::uint32_t loopStart, loopEnd, rate;
        std::uint8_t pitch;
        std::int8_t corr;
        std::uint16_t link, type;
    };
    struct Zone {
        std::vector<std::pair<std::uint16_t, std::int32_t>> gens;  // amount as signed or packed range
        std::vector<sf2::Modulator> mods;
    };
    struct Inst {
        std::string name;
        std::vector<Zone> zones;
    };
    struct Pre {
        std::string name;
        std::uint16_t bank, program;
        std::vector<Zone> zones;
    };
    std::vector<Smp> samples;
    std::vector<Inst> insts;
    std::vector<Pre> presets;

    static std::int32_t range(int lo, int hi) { return lo | (hi << 8); }

    std::vector<unsigned char> bytes() const {
        std::vector<unsigned char> out;
        auto put16 = [](std::vector<unsigned char>& v, std::uint32_t x) { v.push_back(x & 0xFF); v.push_back((x >> 8) & 0xFF); };
        auto put32 = [&](std::vector<unsigned char>& v, std::uint32_t x) { put16(v, x & 0xFFFF); put16(v, x >> 16); };
        auto name20 = [](std::vector<unsigned char>& v, const std::string& s) {
            for (int i = 0; i < 20; ++i) v.push_back(i < static_cast<int>(s.size()) ? static_cast<unsigned char>(s[static_cast<std::size_t>(i)]) : 0);
        };
        auto chunk = [&](const char* id, const std::vector<unsigned char>& body) {
            std::vector<unsigned char> c(id, id + 4);
            put32(c, static_cast<std::uint32_t>(body.size()));
            c.insert(c.end(), body.begin(), body.end());
            if (body.size() & 1) c.push_back(0);
            return c;
        };
        auto list = [&](const char* type, const std::vector<std::vector<unsigned char>>& subs) {
            std::vector<unsigned char> body(type, type + 4);
            for (const auto& s : subs) body.insert(body.end(), s.begin(), s.end());
            return chunk("LIST", body);
        };
        std::vector<unsigned char> ifil, inam(std::begin("Test Font"), std::end("Test Font"));
        put16(ifil, 2);
        put16(ifil, 1);
        std::vector<unsigned char> smpl, shdr;
        for (const auto& s : samples) {
            const std::uint32_t start = static_cast<std::uint32_t>(smpl.size() / 2);
            for (auto v : s.data) put16(smpl, static_cast<std::uint16_t>(v));
            for (int i = 0; i < 46; ++i) put16(smpl, 0);  // 46 zero points after each sample (SF2 spec)
            name20(shdr, s.name);
            put32(shdr, start);
            put32(shdr, start + static_cast<std::uint32_t>(s.data.size()));
            put32(shdr, start + s.loopStart);
            put32(shdr, start + s.loopEnd);
            put32(shdr, s.rate);
            shdr.push_back(s.pitch);
            shdr.push_back(static_cast<unsigned char>(s.corr));
            put16(shdr, s.link);
            put16(shdr, s.type);
        }
        name20(shdr, "EOS");
        for (int i = 0; i < 26; ++i) shdr.push_back(0);
        auto zones = [&](const std::vector<Zone>& zs, std::vector<unsigned char>& bag, std::vector<unsigned char>& gen,
                         std::vector<unsigned char>& mod, std::uint16_t& gi, std::uint16_t& mi) {
            for (const auto& z : zs) {
                put16(bag, gi);
                put16(bag, mi);
                for (const auto& [op, amount] : z.gens) {
                    put16(gen, op);
                    put16(gen, static_cast<std::uint16_t>(amount));
                    ++gi;
                }
                for (const auto& m : z.mods) {
                    put16(mod, m.src);
                    put16(mod, m.dest);
                    put16(mod, static_cast<std::uint16_t>(m.amount));
                    put16(mod, m.amtSrc);
                    put16(mod, m.trans);
                    ++mi;
                }
            }
        };
        std::vector<unsigned char> phdr, pbag, pmod, pgen, inst, ibag, imod, igen;
        std::uint16_t gi = 0, mi = 0, bi = 0;
        for (const auto& p : presets) {
            name20(phdr, p.name);
            put16(phdr, p.program);
            put16(phdr, p.bank);
            put16(phdr, bi);
            put32(phdr, 0);
            put32(phdr, 0);
            put32(phdr, 0);
            zones(p.zones, pbag, pgen, pmod, gi, mi);
            bi = static_cast<std::uint16_t>(bi + p.zones.size());
        }
        name20(phdr, "EOP");
        put16(phdr, 0);
        put16(phdr, 0);
        put16(phdr, bi);
        for (int i = 0; i < 3; ++i) put32(phdr, 0);
        put16(pbag, gi);
        put16(pbag, mi);
        for (int i = 0; i < 2; ++i) put16(pgen, 0);
        for (int i = 0; i < 5; ++i) put16(pmod, 0);
        gi = mi = bi = 0;
        for (const auto& in : insts) {
            name20(inst, in.name);
            put16(inst, bi);
            zones(in.zones, ibag, igen, imod, gi, mi);
            bi = static_cast<std::uint16_t>(bi + in.zones.size());
        }
        name20(inst, "EOI");
        put16(inst, bi);
        put16(ibag, gi);
        put16(ibag, mi);
        for (int i = 0; i < 2; ++i) put16(igen, 0);
        for (int i = 0; i < 5; ++i) put16(imod, 0);
        std::vector<unsigned char> body = {'s', 'f', 'b', 'k'};
        for (const auto& l : {list("INFO", {chunk("ifil", ifil), chunk("INAM", inam)}), list("sdta", {chunk("smpl", smpl)}),
                              list("pdta", {chunk("phdr", phdr), chunk("pbag", pbag), chunk("pmod", pmod), chunk("pgen", pgen),
                                            chunk("inst", inst), chunk("ibag", ibag), chunk("imod", imod), chunk("igen", igen),
                                            chunk("shdr", shdr)})}) {
            body.insert(body.end(), l.begin(), l.end());
        }
        return chunk("RIFF", body);
    }

    std::string write(const std::string& name) const {
        const auto b = bytes();
        const fs::path p = gTmp / name;
        std::ofstream(p, std::ios::binary).write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
        return p.string();
    }
};

std::vector<std::int16_t> sine(double hz, double rate, long n, double amp = 0.5) {
    std::vector<std::int16_t> v(static_cast<std::size_t>(n));
    for (long i = 0; i < n; ++i) v[static_cast<std::size_t>(i)] = static_cast<std::int16_t>(std::lround(32767.0 * amp * std::sin(2.0 * 3.14159265358979 * hz * i / rate)));
    return v;
}

// ----------------------------------------------------------------------------------------- tests

void testParsing() {
    std::printf("parsing GeneralUser GS\n");
    const int before = sf2::loadCount();
    const auto f = sf2::load(sf2::resolvePath(gAssets, "GeneralUser-GS.sf2"));
    check(f->presets.size() == 287 && f->instruments.size() == 324 && f->samples.size() == 920,
          fmt("287 presets, 324 instruments, 920 samples (got %zu, %zu, %zu)", f->presets.size(), f->instruments.size(), f->samples.size()));
    check(f->name.find("GeneralUser GS") != std::string::npos && f->versionMajor == 2, "INFO: name '" + f->name + "', version 2.x");
    check(f->smpl.size() == 32093662 / 2, fmt("16-bit sample pool: %zu samples", f->smpl.size()));
    const sf2::Preset* piano = f->find(0, 0);
    check(piano && piano->name == "Grand Piano", "bank 0 program 0 = 'Grand Piano'");
    check(f->find(128, 0) && f->find(128, 0)->name == "Standard 1" && f->find(8, 80) && f->find(8, 80)->name == "Sine Wave",
          "128:0 'Standard 1' (drum kit), 8:80 'Sine Wave'");
    check(&f->resolvePreset("  grand   PIANO ") == piano && &f->resolvePreset("0:0") == piano && f->resolvePreset("8:80").name == "Sine Wave",
          "preset lookup: case-insensitive, whitespace-trimmed name or bank:program");
    const auto sorted = f->sortedPresets();
    check(sorted.front() == piano && sorted.back()->bank == 128, "listing sorted by bank, program");
    // the zones of Grand Piano: a global preset zone and 6 key ranges x 8 velocity layers of 'Stereo Grand Mellow'
    check(piano->global.has(sf2::InitialFilterFc) && piano->global.gen[sf2::InitialFilterFc] == -884 && piano->global.mods.size() == 1 &&
              piano->global.mods[0].dest == sf2::InitialAttenuation && piano->global.mods[0].amount == 800,
          "Grand Piano global zone: filter offset -884 ct, velocity->attenuation modulator 800 cB");
    check(piano->zones.size() == 48, fmt("Grand Piano: 6 key ranges x 8 velocity layers = 48 local zones (got %zu)", piano->zones.size()));
    const sf2::Zone& z0 = piano->zones[0];
    check(z0.keyLo == 0 && z0.keyHi == 35 && z0.velLo == 0 && z0.velHi == 49 && z0.gen[sf2::InitialFilterFc] == 759 &&
              f->instruments[static_cast<std::size_t>(z0.target)].name == "Stereo Grand Mellow",
          "first zone: keys 0-35, velocity 0-49, fc offset 759, instrument 'Stereo Grand Mellow'");
    const sf2::Instrument& in = f->instruments[static_cast<std::size_t>(z0.target)];
    const sf2::Zone& iz = in.zones[0];
    const sf2::Sample& s = f->samples[static_cast<std::size_t>(iz.target)];
    check(in.global.gen[sf2::InitialFilterFc] == 8815 && in.global.gen[sf2::SampleModes] == 1 && iz.keyHi == 27 &&
              s.name == "Grand Piano-D1" && s.rate == 31000 && s.pitch == 26 && s.correction == -9,
          "instrument global zone (fc 8815, looped) and first zone: sample 'Grand Piano-D1' 31 kHz root 26 -9 ct");
    check(f->samples[static_cast<std::size_t>(f->resolveSample("sine-750hz"))].name == "Sine-750Hz", "sample lookup by name");

    auto throwsWith = [](const std::function<void()>& fn, const std::string& needle) {
        try {
            fn();
        } catch (const ConfigError& e) {
            return std::string(e.what()).find(needle) != std::string::npos;
        }
        return false;
    };
    check(throwsWith([&] { f->resolvePreset("Grand Pinao"); }, "did you mean \"Grand Piano\" (0:0)"),
          "unknown preset: did-you-mean suggestion");
    check(throwsWith([&] { f->resolvePreset(0, 200); }, "no preset at bank 0 program 200"), "unknown bank/program: clear error");
    check(throwsWith([&] { sf2::load(sf2::resolvePath(gAssets, "Missing.sf2")); }, "not found"), "missing file: clear error");
    const fs::path notRiff = gTmp / "not_riff.sf2";
    std::ofstream(notRiff, std::ios::binary) << "hello, this is not a soundfont at all";
    check(throwsWith([&] { sf2::load(notRiff.string()); }, "not a RIFF file"), "garbage file rejected");
    {  // truncated copy of the real file
        std::ifstream in(sf2::resolvePath(gAssets, "GeneralUser-GS.sf2"), std::ios::binary);
        std::vector<char> head(200000);
        in.read(head.data(), static_cast<std::streamsize>(head.size()));
        std::ofstream(gTmp / "truncated.sf2", std::ios::binary).write(head.data(), static_cast<std::streamsize>(head.size()));
        check(throwsWith([&] { sf2::load((gTmp / "truncated.sf2").string()); }, "truncated"), "truncated file rejected");
    }
    {  // a pdta record size error
        Builder b;
        b.samples.push_back({"s", sine(441, 44100, 1000), 0, 0, 44100, 60, 0, 0, 1});
        b.insts.push_back({"i", {{{{sf2::SampleID, 0}}, {}}}});
        b.presets.push_back({"p", 0, 0, {{{{sf2::InstrumentGen, 0}}, {}}}});
        auto bytes = b.bytes();
        const std::string needle = "pgen";
        auto it = std::search(bytes.begin(), bytes.end(), needle.begin(), needle.end());
        it[4] = 6;  // pgen size 8 -> 6: not a multiple of the 4-byte record (and the following chunks are misaligned)
        const fs::path p = gTmp / "bad_pbag.sf2";
        std::ofstream(p, std::ios::binary).write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
        bool threw = false;
        try {
            sf2::load(p.string());
        } catch (const ConfigError& e) {
            threw = std::string(e.what()).find("soundfont '") != std::string::npos;
        }
        check(threw, "malformed pdta rejected with a ConfigError naming the file");
    }
    (void)before;
}

void testCache() {
    std::printf("shared file cache\n");
    const auto a = sf2::load(sf2::resolvePath(gAssets, "GeneralUser-GS.sf2"));
    const int loads = sf2::loadCount();
    auto i1 = make({{"preset", "Grand Piano"}});
    auto i2 = make({{"preset", "Slow Strings"}});
    auto i3 = make(json::object());
    const auto b = sf2::load(sf2::resolvePath(gAssets, "GeneralUser-GS.sf2"));
    check(a.get() == b.get() && sf2::loadCount() == loads, fmt("three instances share one parsed file (loads stay at %d)", loads));
    const auto r1 = a->region(0, smp::LoopMode::None, 0, 0), r2 = a->region(0, smp::LoopMode::None, 0, 0);
    check(r1.get() == r2.get(), "sample regions are converted once and shared");
}

void testPitch() {
    std::printf("pitch\n");
    // the Sine Wave preset: A4 from the 750 Hz sample (root 78, -23 ct correction) = exactly 440 Hz
    auto sine = make({{"preset", "Sine Wave"}});
    const Audio a = render(*sine, {{0, true, 1, 69, 0.8f}, {sec(1.5), false, 1, 69, 0.0f}}, sec(1.5));
    const double f = autocorrPitch(a.mono(), sec(0.4), 8192, 440.0);
    check(std::fabs(cents(f, 440.0)) < 0.5, fmt("Sine Wave A4: %.3f Hz (%+.2f ct)", f, cents(f, 440.0)));
    for (const auto& [param, value, expect] : std::vector<std::tuple<std::string, double, double>>{
             {"transpose", 12, 880.0}, {"tune", 50, 440.0 * std::exp2(50.0 / 1200.0)}, {"pitchbend", 2, 440.0 * std::exp2(2.0 / 12.0)}}) {
        auto s = make({{"preset", "Sine Wave"}, {param, value}});
        const Audio b = render(*s, {{0, true, 1, 69, 0.8f}}, sec(1.0));
        const double g = autocorrPitch(b.mono(), sec(0.4), 8192, expect);
        check(std::fabs(cents(g, expect)) < 0.5, fmt("%s %g: %.2f Hz (expected %.2f)", param.c_str(), value, g, expect));
    }
    // a real piano sample (keys 65-69 play 'Grand Piano-F#4', root 67 -3 ct, 32 kHz)
    auto piano = make({{"preset", "Grand Piano"}});
    const Audio p = render(*piano, {{0, true, 1, 69, 0.8f}}, sec(1.5));
    const double fp = autocorrPitch(p.mono(), sec(0.3), 16384, 440.0);
    check(std::fabs(cents(fp, 440.0)) < 5.0, fmt("Grand Piano A4: %.2f Hz (%+.2f ct, limit 5)", fp, cents(fp, 440.0)));
    // other sample rates
    auto p44 = make({{"preset", "Sine Wave"}}, 0.0, 44100.0);
    Audio q;
    q.l.assign(44100, 0.0f);
    q.r.assign(44100, 0.0f);
    p44->noteOn(1, 69, 0.8f);
    for (int pos = 0; pos < 44100; pos += 256) p44->process(q.l.data() + pos, q.r.data() + pos, std::min(256, 44100 - pos));
    double zc = 0.0, first = -1.0, last = 0.0;
    for (int i = 4410; i < 44100; ++i) {
        if (q.l[static_cast<std::size_t>(i - 1)] < 0.0f && q.l[static_cast<std::size_t>(i)] >= 0.0f) {
            const double t = i - 1 + q.l[static_cast<std::size_t>(i - 1)] / (q.l[static_cast<std::size_t>(i - 1)] - q.l[static_cast<std::size_t>(i)]);
            if (first < 0) first = t;
            last = t;
            zc += 1.0;
        }
    }
    const double f44 = 44100.0 * (zc - 1.0) / (last - first);
    check(std::fabs(cents(f44, 440.0)) < 0.5, fmt("at 44.1 kHz: %.3f Hz", f44));
}

void testLoops() {
    std::printf("loops\n");
    // a looped string pad and organ held for 10 s keep sounding, click-free
    for (const char* preset : {"Slow Strings", "Tonewheel Organ", "Warm Pad"}) {
        auto s = make({{"preset", preset}});
        const Audio a = render(*s, {{0, true, 1, 60, 0.8f}, {0, true, 2, 64, 0.8f}, {0, true, 3, 67, 0.8f}, {sec(10.0), false, 1, 60, 0.0f},
                                    {sec(10.0), false, 2, 64, 0.0f}, {sec(10.0), false, 3, 67, 0.0f}},
                             sec(11.0));
        const double early = rms(a.l, sec(1.0), sec(2.0)), late = rms(a.l, sec(9.0), sec(10.0));
        check(finite(a) && late > 0.3 * early && late > 1e-3 && clicks(a) == 0,
              fmt("%-16s held 10 s: RMS %.1f dBFS at 1-2 s, %.1f dBFS at 9-10 s, %d clicks", preset, db(early), db(late), clicks(a)));
    }
    // single-cycle loops (32..128 samples, shorter than the kernel): the second difference of a pure sine
    // stays near its theoretical maximum A (2 pi f / sr)^2. A seam (a loop off by a fraction of a frame)
    // spikes it by ~1 / (2 pi f / sr) (> 3x even at 1760 Hz); the 16-bit source's own quantization noise
    // allows ~10 % at 220 Hz.
    for (int key : {57, 81, 93}) {
        auto one = make({{"preset", "Sine Wave"}});
        const Audio a = render(*one, {{0, true, 1, key, 0.8f}}, sec(3.0));
        const double hz = 440.0 * std::exp2((key - 69) / 12.0);
        double peak = 0.0, d2 = 0.0;
        for (long i = sec(0.5); i < sec(3.0); ++i) {
            peak = std::max(peak, static_cast<double>(std::fabs(a.l[static_cast<std::size_t>(i)])));
            d2 = std::max(d2, static_cast<double>(std::fabs(a.l[static_cast<std::size_t>(i)] - 2.0f * a.l[static_cast<std::size_t>(i - 1)] + a.l[static_cast<std::size_t>(i - 2)])));
        }
        const double w = 2.0 * 3.14159265358979 * hz / kSr;
        const double ratio = d2 / (peak * w * w);
        const double drift = db(rms(a.l, sec(2.5), sec(3.0)) / rms(a.l, sec(0.5), sec(1.0)));
        check(ratio < 1.25 && std::fabs(drift) < 0.05 && clicks(a) == 0,
              fmt("Sine Wave key %d (%.0f Hz): 2nd-difference peak %.3f x theory, level drift %+.3f dB, %d clicks", key, hz, ratio, drift, clicks(a)));
    }
}

void testVelocity() {
    std::printf("velocity layers\n");
    // Standard 1 kit, key 49: velocity 0-41 plays the ride cymbal sample, 42+ the crash
    auto kitAt = [](float vel) {
        auto k = make({{"preset", "Standard 1"}});
        return render(*k, {{0, true, 1, 49, vel}}, sec(0.6)).mono();
    };
    const auto soft = kitAt(30.0f / 127.0f), loud = kitAt(120.0f / 127.0f), loud2 = kitAt(110.0f / 127.0f);
    auto corr = [](const std::vector<float>& a, const std::vector<float>& b) {
        double s = 0, ea = 0, eb = 0;
        for (long i = 0; i < sec(0.3); ++i) {
            s += double(a[static_cast<std::size_t>(i)]) * b[static_cast<std::size_t>(i)];
            ea += double(a[static_cast<std::size_t>(i)]) * a[static_cast<std::size_t>(i)];
            eb += double(b[static_cast<std::size_t>(i)]) * b[static_cast<std::size_t>(i)];
        }
        return s / std::sqrt(std::max(ea * eb, 1e-30));
    };
    check(std::fabs(corr(soft, loud)) < 0.3 && corr(loud, loud2) > 0.5,
          fmt("crash key: velocity 30 plays a different sample than 120 (correlation %.2f; 110 vs 120: %.2f)", corr(soft, loud), corr(loud, loud2)));
    // piano: louder and brighter with velocity
    double lastRms = 0.0, lastCentroid = 0.0;
    bool rising = true;
    std::string text;
    for (int v : {30, 60, 90, 120}) {
        auto p = make({{"preset", "Grand Piano"}});
        const auto m = render(*p, {{0, true, 1, 60, v / 127.0f}}, sec(0.4)).mono();
        const double r = rms(m, 0, sec(0.4)), c = centroid(m, sec(0.05));
        rising = rising && r > lastRms && c > lastCentroid;
        lastRms = r;
        lastCentroid = c;
        text += fmt(" v%d %.1f dB %.0f Hz", v, db(r), c);
    }
    check(rising, "Grand Piano gets louder and brighter with velocity:" + text);
    auto flat = make({{"preset", "Grand Piano"}, {"velsens", 0}});
    const double r1 = rms(render(*flat, {{0, true, 1, 60, 30 / 127.0f}}, sec(0.4)).l, 0, sec(0.4));
    auto flat2 = make({{"preset", "Grand Piano"}, {"velsens", 0}});
    const double r2 = rms(render(*flat2, {{0, true, 1, 60, 120 / 127.0f}}, sec(0.4)).l, 0, sec(0.4));
    check(std::fabs(db(r1 / r2)) < 0.01, "velsens 0: every note plays as velocity 100");
}

void testExclusiveClass() {
    std::printf("exclusive class (hi-hat choke)\n");
    auto kit = [](bool closed) {
        auto k = make({{"preset", "Standard 1"}});
        std::vector<Event> ev = {{0, true, 1, 46, 0.8f}, {sec(0.1), false, 1, 46, 0.0f}};
        if (closed) {
            ev.push_back({sec(0.25), true, 2, 42, 0.8f});
            ev.push_back({sec(0.3), false, 2, 42, 0.0f});
        }
        return render(*k, ev, sec(1.0));
    };
    const Audio open = kit(false), choked = kit(true);
    const double tailOpen = rms(open.l, sec(0.55), sec(0.9)), tailChoked = rms(choked.l, sec(0.55), sec(0.9));
    check(db(tailOpen / tailChoked) > 25.0 && clicks(choked) == 0,
          fmt("a closed hat chokes the ringing open hat: tail %.1f dBFS -> %.1f dBFS, %d clicks", db(tailOpen), db(tailChoked), clicks(choked)));
    // the same class does not choke the voices of its own note (pairs / layers)
    auto k2 = make({{"preset", "Standard 1"}});
    const Audio twice = render(*k2, {{0, true, 1, 46, 0.8f}, {sec(0.1), false, 1, 46, 0.0f}}, sec(0.5));
    check(rms(twice.l, sec(0.3), sec(0.5)) > 1e-3, "an open hat alone rings on");
}

void testReleaseAndIdle() {
    std::printf("release, idle\n");
    auto p = make({{"preset", "Grand Piano"}});
    p->noteOn(1, 60, 0.8f);
    std::vector<float> l(256), r(256);
    long pos = 0;
    for (; pos < sec(0.5); pos += 256) p->process(l.data(), r.data(), 256);
    check(!p->idle(), "sounding: not idle");
    p->noteOff(1);
    double lastPeak = 1.0;
    long idleAt = -1;
    for (; pos < sec(8.0); pos += 256) {
        p->process(l.data(), r.data(), 256);
        float peak = 0.0f;
        for (int i = 0; i < 256; ++i) peak = std::max({peak, std::fabs(l[static_cast<std::size_t>(i)]), std::fabs(r[static_cast<std::size_t>(i)])});
        if (p->idle()) { idleAt = pos; break; }
        lastPeak = peak;
    }
    check(idleAt > 0 && idleAt < sec(4.0) && lastPeak < 1e-3, fmt("idle %.2f s after note-off, the last block peaks at %.1f dBFS", (idleAt - sec(0.5)) / kSr, db(lastPeak)));
    p->process(l.data(), r.data(), 256);
    check(std::all_of(l.begin(), l.end(), [](float x) { return x == 0.0f; }), "silent once idle");

    // the attack scale and release scale params
    auto slow = make({{"preset", "Grand Piano"}, {"release", 4}});
    const Audio a = render(*slow, {{0, true, 1, 60, 0.8f}, {sec(0.5), false, 1, 60, 0.0f}}, sec(2.0));
    auto normal = make({{"preset", "Grand Piano"}});
    const Audio b = render(*normal, {{0, true, 1, 60, 0.8f}, {sec(0.5), false, 1, 60, 0.0f}}, sec(2.0));
    check(rms(a.l, sec(1.0), sec(1.5)) > 3.0 * rms(b.l, sec(1.0), sec(1.5)), "release x4 keeps the tail longer");
    auto swell = make({{"preset", "Slow Strings"}, {"attack", 5}});
    const Audio c = render(*swell, {{0, true, 1, 60, 0.8f}}, sec(1.0));
    auto strings = make({{"preset", "Slow Strings"}});
    const Audio d = render(*strings, {{0, true, 1, 60, 0.8f}}, sec(1.0));
    check(rms(c.l, sec(0.1), sec(0.3)) < 0.6 * rms(d.l, sec(0.1), sec(0.3)), "attack x5 swells in slower");
}

void testPedalAndExpression() {
    std::printf("sustain pedal, expression\n");
    const std::vector<Event> ev = {{0, true, 1, 60, 0.8f}, {sec(0.3), false, 1, 60, 0.0f}};
    auto dry = make({{"preset", "Grand Piano"}});
    const Audio a = render(*dry, ev, sec(3.0));
    auto held = make({{"preset", "Grand Piano"}, {"pedal", 1}});
    const Audio b = render(*held, ev, sec(3.0));
    check(db(rms(b.l, sec(1.0), sec(1.3)) / rms(a.l, sec(1.0), sec(1.3))) > 20.0,
          fmt("pedal down: the note rings on after note-off (%.1f dB louder at 1 s)", db(rms(b.l, sec(1.0), sec(1.3)) / rms(a.l, sec(1.0), sec(1.3)))));
    auto lift = make({{"preset", "Grand Piano"}, {"pedal", 1}});
    bool lifted = false;
    const Audio c = render(*lift, ev, sec(3.0), 256, [&](long pos) {
        if (!lifted && pos >= sec(1.0)) lifted = lift->setParam("pedal", 0.0f);
    });
    check(rms(c.l, sec(0.8), sec(0.95)) > 0.5 * rms(b.l, sec(0.8), sec(0.95)) &&
              db(rms(c.l, sec(2.5), sec(3.0)) / rms(b.l, sec(2.5), sec(3.0))) < -20.0 && clicks(c) == 0,
          fmt("pedal-up releases the held notes (%.1f dB vs held, no clicks)", db(rms(c.l, sec(2.5), sec(3.0)) / rms(b.l, sec(2.5), sec(3.0)))));
    auto half = make({{"preset", "Grand Piano"}, {"expression", 0.5}});
    const Audio d = render(*half, ev, sec(0.3));
    auto full = make({{"preset", "Grand Piano"}});
    const Audio e = render(*full, ev, sec(0.3));
    const double ratio = db(rms(d.l, sec(0.05), sec(0.3)) / rms(e.l, sec(0.05), sec(0.3)));
    check(std::fabs(ratio + 12.04) < 0.05, fmt("expression 0.5: %.2f dB (expression^2: -12.04)", ratio));
}

void testDeterminismAndPreview() {
    std::printf("determinism, block independence, preview parity\n");
    const std::vector<Event> ev = {{0, true, 1, 48, 0.8f}, {100, true, 2, 64, 0.6f}, {sec(0.3), true, 3, 72, 1.0f}, {sec(0.6), false, 1, 48, 0},
                                   {sec(0.9), false, 2, 64, 0}, {sec(1.0), false, 3, 72, 0}, {sec(1.1), true, 4, 60, 0.9f}, {sec(1.5), false, 4, 60, 0}};
    auto a = make({{"preset", "Grand Piano"}});
    auto b = make({{"preset", "Grand Piano"}});
    auto c = make({{"preset", "Grand Piano"}});
    const Audio x = render(*a, ev, sec(2.0)), y = render(*b, ev, sec(2.0)), z = render(*c, ev, sec(2.0), 0);
    check(x.l == y.l && x.r == y.r, "same input -> bit-identical output");
    check(x.l == z.l && x.r == z.r, "random block sizes -> bit-identical output (voices run on their own control grid)");
    auto full = make({{"preset", "Slow Strings"}, {"width", 1.5}});
    auto prev = make({{"preset", "Slow Strings"}, {"width", 1.5}}, 13.5);
    const long start = sec(13.5 * 0.5);
    const Audio f = render(*full, {{start, true, 1, 57, 0.8f}}, start + sec(1.5));
    const Audio g = render(*prev, {{0, true, 1, 57, 0.8f}}, sec(1.5));
    double diff = 0.0;
    for (long i = 0; i < sec(1.5); ++i) diff = std::max(diff, static_cast<double>(std::fabs(g.l[static_cast<std::size_t>(i)] - f.l[static_cast<std::size_t>(start + i)])));
    check(diff == 0.0, fmt("preview render from beat 13.5 matches the full render (max diff %.1e)", diff));
}

void testSynthetic() {
    std::printf("generator semantics (SoundFonts built by the test)\n");
    const double rate = 44100.0;
    // sample 0: 441 Hz for 20000 frames (loop 10000..20000 = whole cycles), then an 882 Hz tail of 30000
    auto body = sine(441.0, rate, 20000);
    const auto tail = sine(882.0, rate, 30000);
    body.insert(body.end(), tail.begin(), tail.end());
    Builder b;
    b.samples.push_back({"body", body, 10000, 20000, 44100, 69, 0, 0, 1});
    b.samples.push_back({"left", sine(441.0, rate, 44100), 0, 44100, 44100, 69, 0, 2, 4});   // linked stereo pair
    b.samples.push_back({"right", sine(441.0, rate, 44100, 0.25), 0, 44100, 44100, 69, 0, 1, 2});
    using G = std::vector<std::pair<std::uint16_t, std::int32_t>>;
    // inst 0: loop until release, 2 s release; inst 1: continuous loop; inst 2: stereo pair
    b.insts.push_back({"until", {{G{{sf2::ReleaseVolEnv, 1200}, {sf2::SampleModes, 3}, {sf2::SampleID, 0}}, {}}}});
    b.insts.push_back({"cont", {{G{{sf2::ReleaseVolEnv, 1200}, {sf2::SampleModes, 1}, {sf2::SampleID, 0}}, {}}}});
    b.insts.push_back({"pair", {{G{{sf2::SampleModes, 1}, {sf2::SampleID, 1}}, {}}, {G{{sf2::SampleModes, 1}, {sf2::SampleID, 2}}, {}}}});
    // inst 3: attenuation 100 cB, velocity -> attenuation switched off (identical to the default: amount 0)
    b.insts.push_back({"att", {{G{{sf2::InitialAttenuation, 100}, {sf2::SampleModes, 1}, {sf2::SampleID, 0}}, {sf2::Modulator{0x0502, 48, 0, 0, 0}}}}});
    // inst 4: keys 0-59 play the (louder) left sample, 60-127 the right one
    b.insts.push_back({"split", {{G{{sf2::KeyRange, Builder::range(0, 59)}, {sf2::SampleModes, 1}, {sf2::SampleID, 1}}, {}},
                                 {G{{sf2::KeyRange, Builder::range(60, 127)}, {sf2::SampleModes, 1}, {sf2::SampleID, 2}}, {}}}});
    b.presets.push_back({"Until", 0, 0, {{G{{sf2::InstrumentGen, 0}}, {}}}});
    b.presets.push_back({"Cont", 0, 1, {{G{{sf2::InstrumentGen, 1}}, {}}}});
    b.presets.push_back({"Pair", 0, 2, {{G{{sf2::InstrumentGen, 2}}, {}}}});
    b.presets.push_back({"Att", 0, 3, {{G{{sf2::InstrumentGen, 3}}, {}}}});
    b.presets.push_back({"NoAtt", 0, 4, {{G{{sf2::InstrumentGen, 1}}, {}}}});
    // preset with a global zone adding +12 semitones and a local zone overriding it with +7 (and 60 cB)
    b.presets.push_back({"Offsets", 0, 5, {{G{{sf2::CoarseTune, 12}}, {}}, {G{{sf2::CoarseTune, 7}, {sf2::InitialAttenuation, 60}, {sf2::InstrumentGen, 1}}, {}}}});
    b.presets.push_back({"Split", 0, 6, {{G{{sf2::InstrumentGen, 4}}, {}}}});
    const std::string path = b.write("test.sf2");

    auto pitchAt = [](const Audio& a, double t, double expect) { return autocorrPitch(a.mono(), sec(t), 4096, expect); };
    {  // loop until release: while held 441 Hz; after the release the tail (882 Hz) plays
        auto s = make({{"file", path}, {"preset", "Until"}});
        const Audio a = render(*s, {{0, true, 1, 69, 1.0f}, {sec(1.0), false, 1, 69, 0.0f}}, sec(2.0));
        const double held = pitchAt(a, 0.8, 441.0), after = pitchAt(a, 1.4, 882.0);
        check(std::fabs(cents(held, 441.0)) < 1.0 && std::fabs(cents(after, 882.0)) < 1.0 && rms(a.l, sec(1.4), sec(1.5)) > 0.02,
              fmt("loop until release: %.1f Hz held, %.1f Hz (the sample's tail) after the release", held, after));
        auto c = make({{"file", path}, {"preset", "Cont"}});
        const Audio d = render(*c, {{0, true, 1, 69, 1.0f}, {sec(1.0), false, 1, 69, 0.0f}}, sec(2.0));
        const double cont = pitchAt(d, 1.4, 441.0);
        check(std::fabs(cents(cont, 441.0)) < 1.0 && clicks(d) == 0, fmt("continuous loop keeps looping in the release: %.1f Hz, no clicks", cont));
        check(clicks(a) == 0, "leaving the loop is click-free");
    }
    {  // linked stereo pair: left sample hard left, right sample hard right
        auto s = make({{"file", path}, {"preset", "Pair"}});
        const Audio a = render(*s, {{0, true, 1, 69, 1.0f}}, sec(0.5));
        const double l = rms(a.l, sec(0.2), sec(0.5)), r = rms(a.r, sec(0.2), sec(0.5));
        check(std::fabs(db(l / r) - 6.02) < 0.1, fmt("linked stereo: left / right samples on their sides (L/R %.2f dB, samples differ by 6.02 dB)", db(l / r)));
        auto m = make({{"file", path}, {"preset", "Pair"}, {"width", 0}});
        const Audio c = render(*m, {{0, true, 1, 69, 1.0f}}, sec(0.5));
        double d = 0.0;
        for (std::size_t i = 0; i < c.l.size(); ++i) d = std::max(d, static_cast<double>(std::fabs(c.l[i] - c.r[i])));
        check(d < 1e-6, "width 0 folds the pair to mono");
    }
    {  // attenuation x 0.4, the default velocity modulator and its override
        auto att = make({{"file", path}, {"preset", "Att"}});
        auto noatt = make({{"file", path}, {"preset", "NoAtt"}});
        const double a = rms(render(*att, {{0, true, 1, 69, 1.0f}}, sec(0.3)).l, sec(0.1), sec(0.3));
        const double n = rms(render(*noatt, {{0, true, 1, 69, 1.0f}}, sec(0.3)).l, sec(0.1), sec(0.3));
        check(std::fabs(db(n / a) - 4.0) < 0.05, fmt("initialAttenuation 100 cB x 0.4 = %.2f dB quieter (expected 4.00)", db(n / a)));
        auto soft = make({{"file", path}, {"preset", "NoAtt"}});
        const double v64 = rms(render(*soft, {{0, true, 1, 69, 64.0f / 127.0f}}, sec(0.3)).l, sec(0.1), sec(0.3));
        const double expect = 40.0 * std::log10(64.0 / 127.0);
        check(std::fabs(db(v64 / n) - expect) < 0.05, fmt("default velocity modulator: velocity 64 %.2f dB (expected %.2f)", db(v64 / n), expect));
        auto soft2 = make({{"file", path}, {"preset", "Att"}});
        const double w64 = rms(render(*soft2, {{0, true, 1, 69, 64.0f / 127.0f}}, sec(0.3)).l, sec(0.1), sec(0.3));
        check(std::fabs(db(w64 / a)) < 0.01, "an instrument modulator with the default's identity overrides it (amount 0: no velocity response)");
    }
    {  // preset generators add to the instrument's, the local zone overrides the global one
        auto s = make({{"file", path}, {"preset", "Offsets"}});
        const Audio a = render(*s, {{0, true, 1, 69, 1.0f}}, sec(0.5));
        const double f = pitchAt(a, 0.2, 441.0 * std::exp2(7.0 / 12.0));
        auto n = make({{"file", path}, {"preset", "NoAtt"}});
        const double ref = rms(render(*n, {{0, true, 1, 69, 1.0f}}, sec(0.5)).l, sec(0.2), sec(0.5));
        check(std::fabs(cents(f, 441.0 * std::exp2(7.0 / 12.0))) < 1.0 && std::fabs(db(ref / rms(a.l, sec(0.2), sec(0.5))) - 2.4) < 0.05,
              fmt("preset offsets: coarse +7 (local over global +12) -> %.1f Hz, attenuation 60 cB -> -2.4 dB", f));
    }
    {  // anti-aliasing: a band-limited saw (harmonics to 22 kHz at 44.1 kHz) played 2 octaves up (4.4 source frames
       // per output frame): the stretched kernel removes everything above the output Nyquist frequency
        Builder a;
        std::vector<std::int16_t> saw(168 * 100);
        for (std::size_t i = 0; i < saw.size(); ++i) {
            double v = 0.0;
            for (int k = 1; k <= 83; ++k) v += std::sin(2.0 * 3.14159265358979 * k * static_cast<double>(i % 168) / 168.0) / k;
            saw[i] = static_cast<std::int16_t>(std::lround(8000.0 * v));
        }
        a.samples.push_back({"saw", saw, 0, static_cast<std::uint32_t>(saw.size()), 44100, 60, 0, 0, 1});
        a.insts.push_back({"saw", {{G{{sf2::SampleModes, 1}, {sf2::SampleID, 0}}, {}}}});
        a.presets.push_back({"Saw", 0, 0, {{G{{sf2::InstrumentGen, 0}}, {}}}});
        auto s = make({{"file", a.write("saw.sf2")}});
        const auto m = render(*s, {{0, true, 1, 84, 1.0f}}, sec(0.5)).mono();
        const double f0 = 262.5 * 4.0, fund = tone(m, sec(0.2), 8192, f0);
        double alias = 0.0, worst = 0.0;
        for (int k = 25; k <= 83; ++k) {  // harmonics above 26 kHz fold back to 48 kHz - k f0 (none lands on a harmonic)
            double f = std::fmod(k * f0, kSr);
            if (f > kSr / 2) f = kSr - f;
            const double v = tone(m, sec(0.2), 8192, f);
            alias += v * v;
            worst = std::max(worst, v);
        }
        check(db(std::sqrt(alias) / fund) < -70.0,
              fmt("saw 2 octaves up: aliasing %.1f dB below the fundamental (worst component %.1f dB; limit -70)", db(std::sqrt(alias) / fund),
                  db(worst / fund)));
    }
    {  // key ranges pick the zone
        auto s = make({{"file", path}, {"preset", "Split"}});
        const double lo = rms(render(*s, {{0, true, 1, 59, 1.0f}}, sec(0.3)).mono(), sec(0.1), sec(0.3));
        auto t = make({{"file", path}, {"preset", "Split"}});
        const double hi = rms(render(*t, {{0, true, 1, 60, 1.0f}}, sec(0.3)).mono(), sec(0.1), sec(0.3));
        check(std::fabs(db(lo / hi) - 6.02) < 0.1, fmt("key 59 plays the loud sample, key 60 the quiet one (%.2f dB apart)", db(lo / hi)));
    }
}

void testConfigErrors() {
    std::printf("config errors\n");
    auto rejects = [](const json& p, const std::string& needle, bool atPrepare = false) {
        try {
            auto s = makeSf2Synth();
            s->configure(p);
            if (atPrepare) {
                RenderContext ctx;
                ctx.assetDir = gAssets;
                s->prepare(ctx);
            }
        } catch (const ConfigError& e) {
            const bool ok = std::string(e.what()).find(needle) != std::string::npos;
            if (!ok) std::printf("      message: %s\n", e.what());
            return ok;
        }
        return false;
    };
    check(rejects({{"cutof", 1}}, "unknown parameter 'cutof'"), "unknown parameter");
    check(rejects({{"preset", "Grand Piano"}, {"program", 3}}, "either 'preset' or 'bank'"), "preset and program together");
    check(rejects({{"bank", 8}}, "needs a 'program'"), "bank without program");
    check(rejects({{"polyphony", 3.5}}, "whole number"), "fractional polyphony");
    check(rejects({{"preset", 12}}, "'preset' must be a preset name"), "preset of the wrong type");
    check(rejects({{"preset", "Grand Pianoo"}}, "did you mean", true), "unknown preset (at prepare) with suggestions");
    check(rejects({{"bank", 3}, {"program", 0}}, "no preset at bank 3", true), "unknown bank/program");
    check(rejects({{"file", "Nope.sf2"}}, "not found", true), "missing file");
    auto s = make({{"bank", 0}, {"program", 48}, {"level", -6}, {"width", 0.5}});
    check(s != nullptr, "bank + program select a preset");
}

void testEveryPreset() {
    std::printf("every preset of GeneralUser GS renders finite audio\n");
    const auto f = sf2::load(sf2::resolvePath(gAssets, "GeneralUser-GS.sf2"));
    int bad = 0;
    float worst = 0.0f;
    std::string worstName;
    for (const sf2::Preset* p : f->sortedPresets()) {
        auto s = make({{"preset", std::to_string(p->bank) + ":" + std::to_string(p->program)}});
        const Audio a = render(*s, {{0, true, 1, 36, 1.0f}, {0, true, 2, 60, 0.7f}, {0, true, 3, 84, 0.4f}, {sec(0.2), false, 1, 36, 0},
                                    {sec(0.2), false, 2, 60, 0}, {sec(0.2), false, 3, 84, 0}},
                             sec(0.3));
        if (!finite(a)) ++bad;
        for (std::size_t i = 0; i < a.l.size(); ++i) {
            const float m = std::max(std::fabs(a.l[i]), std::fabs(a.r[i]));
            if (m > worst) { worst = m; worstName = p->name; }
        }
    }
    check(bad == 0 && worst < 2.0f, fmt("all 287 presets finite (loudest peak %.2f: %s)", worst, worstName.c_str()));
}

void testSpeed() {
    std::printf("speed\n");
    // 16-voice piano passage: 4 overlapping 4-note chords per bar (notes ring 1.5 bars), 30 s of audio
    auto p = make({{"preset", "Grand Piano"}});
    std::vector<Event> ev;
    const int chords[4][4] = {{45, 57, 60, 64}, {41, 53, 57, 60}, {36, 48, 55, 64}, {43, 55, 59, 62}};
    int id = 0;
    for (int bar = 0; bar < 15; ++bar) {
        for (int beat = 0; beat < 4; ++beat) {
            const long at = sec(bar * 2.0 + beat * 0.5);
            for (int k = 0; k < 4; ++k) {
                ev.push_back({at, true, ++id, chords[(bar + beat) % 4][k] + 12 * (beat % 2), 0.75f});
                ev.push_back({at + sec(2.0), false, id, 0, 0.0f});
            }
        }
    }
    // Best of 3 wall-clock runs: other processes (parallel builds, agents) must not fail a speed limit that the
    // code itself meets.
    double wall = 1e9;
    bool ok = true;
    for (int run = 0; run < 3 && 30.0 / wall < 20.0; ++run) {
        const auto t0 = std::chrono::steady_clock::now();
        const Audio a = render(*p, ev, sec(30.0));
        wall = std::min(wall, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
        ok = ok && finite(a);
    }
    check(ok && 30.0 / wall >= 20.0, fmt("16-voice piano: %.0fx realtime (limit 20x, best of 3)", 30.0 / wall));
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
        std::printf("FAIL: cannot find assets/soundfonts/GeneralUser-GS.sf2 (run from the repo root or pass the assets dir)\n");
        return 1;
    }
    gTmp = fs::temp_directory_path() / "agentsound_test_sf2";
    fs::create_directories(gTmp);
    try {
        testParsing();
        testCache();
        testConfigErrors();
        testPitch();
        testLoops();
        testVelocity();
        testExclusiveClass();
        testReleaseAndIdle();
        testPedalAndExpression();
        testDeterminismAndPreview();
        testSynthetic();
        testEveryPreset();
        testSpeed();
    } catch (const std::exception& e) {
        std::printf("FAIL: unexpected exception: %s\n", e.what());
        return 1;
    }
    std::printf("%d/%d checks passed\n", gChecks - gFailures, gChecks);
    return gFailures == 0 ? 0 : 1;
}
