// vocoder: band energy follows the modulator (classic + lpc), silence in -> silence out, hold, formant shift,
// level calibration, determinism, preview parity, finite output at extreme settings, strictness (a vocoder
// without a sidechain is a ConfigError) and the muted-modulator routing through the renderer.

#include "dsp/Dsp.h"
#include "render/Registry.h"
#include "render/Renderer.h"
#include "render/SongSpec.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <functional>
#include <memory>
#include <string>
#include <vector>

using namespace as;

namespace {

int gFail = 0, gChecks = 0;

void check(bool ok, const std::string& what) {
    ++gChecks;
    if (!ok) ++gFail;
    std::printf("  [%s] %s\n", ok ? " ok " : "FAIL", what.c_str());
}

template <typename... A>
std::string fmt(const char* f, A... a) {
    char buf[512];
    std::snprintf(buf, sizeof buf, f, a...);
    return buf;
}

constexpr double kSr = 48000.0;
constexpr double kBpm = 120.0;
constexpr int kBlock = kAutomationStep;

struct Stereo {
    std::vector<float> l, r;
    explicit Stereo(std::size_t n = 0) : l(n, 0.0f), r(n, 0.0f) {}
    std::size_t size() const { return l.size(); }
};

// Carrier: an A minor chord of band-limited saws (harmonics to 12 kHz), slightly different per side.
Stereo sawChord(std::size_t n, double gain = 0.12) {
    Stereo x(n);
    const double f0[5] = {110.0, 164.81, 220.0, 261.63, 329.63};
    for (int v = 0; v < 5; ++v) {
        const int harmonics = static_cast<int>(12000.0 / f0[v]);
        for (int h = 1; h <= harmonics; ++h) {
            const double a = gain / h, w = dsp::kTwoPi * f0[v] * h / kSr;
            double phL = 0.37 * h * (v + 1), phR = phL + 0.3 * h;
            for (std::size_t i = 0; i < n; ++i) {
                x.l[i] += static_cast<float>(a * std::sin(phL + w * static_cast<double>(i)));
                x.r[i] += static_cast<float>(a * std::sin(phR + w * static_cast<double>(i)));
            }
        }
    }
    return x;
}

// Band-limited noise (4th-order band-pass around fc, one octave wide), unit-ish RMS * gain.
std::vector<float> bandNoise(std::size_t n, double fc, double gain, std::uint64_t seed) {
    dsp::Rng rng(seed);
    dsp::Biquad bp[2];
    for (auto& b : bp) b.set(dsp::Biquad::Type::BandPass, kSr, fc, 1.4);
    std::vector<float> y(n);
    for (std::size_t i = 0; i < n; ++i) y[i] = static_cast<float>(gain * 4.0) * bp[1].process(bp[0].process(rng.bipolar()));
    return y;
}

// Modulator: bursts of band noise at 400 Hz, 1.2 kHz, 3.2 kHz (250 ms each, 10 ms fades), 150 ms of silence between.
constexpr double kBurstHz[3] = {400.0, 1200.0, 3200.0};
constexpr long kBurstLen = 12000, kGap = 7200, kFirst = 4800;
long burstStart(int k, int cycle = 0) { return kFirst + (cycle * 3 + k) * (kBurstLen + kGap); }

std::vector<float> burstModulator(std::size_t n) {
    std::vector<float> m(n, 0.0f);
    std::vector<std::vector<float>> src;
    for (int k = 0; k < 3; ++k) src.push_back(bandNoise(n, kBurstHz[k], 0.25, 100 + k));
    for (int cycle = 0; burstStart(0, cycle) < static_cast<long>(n); ++cycle)
        for (int k = 0; k < 3; ++k) {
            const long a = burstStart(k, cycle);
            for (long i = 0; i < kBurstLen && a + i < static_cast<long>(n); ++i) {
                const double f = std::min({1.0, i / 480.0, (kBurstLen - i) / 480.0});
                m[static_cast<std::size_t>(a + i)] = static_cast<float>(f) * src[static_cast<std::size_t>(k)][static_cast<std::size_t>(a + i)];
            }
        }
    return m;
}

std::unique_ptr<Effect> vocoder(const json& params, double startBeat = 0.0, std::uint64_t seed = 7) {
    auto fx = createEffect("vocoder");
    fx->configure(params);
    RenderContext ctx;
    ctx.sampleRate = kSr;
    ctx.bpm = kBpm;
    ctx.seed = seed;
    ctx.maxBlock = kBlock;
    ctx.startBeat = startBeat;
    fx->prepare(ctx);
    return fx;
}

// Runs the vocoder over carrier[offset..offset+len) keyed by mod (mono, same offset) in 32-sample blocks
// (or `block` samples: the host may use other sizes).
Stereo run(Effect& fx, const Stereo& carrier, const std::vector<float>& mod, long offset, long len, int block = kBlock) {
    Stereo out(static_cast<std::size_t>(len));
    for (long i = 0; i < len; ++i) {
        out.l[static_cast<std::size_t>(i)] = carrier.l[static_cast<std::size_t>(offset + i)];
        out.r[static_cast<std::size_t>(i)] = carrier.r[static_cast<std::size_t>(offset + i)];
    }
    for (long pos = 0; pos < len; pos += block) {
        const int n = static_cast<int>(std::min<long>(block, len - pos));
        const float* key = mod.data() + offset + pos;
        fx.process(out.l.data() + pos, out.r.data() + pos, n, key, key);
    }
    return out;
}

// Energy of x (mono sum) band-passed around fc (4th order, ~1/2 octave) over [a, b).
double bandEnergy(const Stereo& s, double fc, long a, long b) {
    dsp::Biquad bp[2];
    for (auto& f : bp) f.set(dsp::Biquad::Type::BandPass, kSr, fc, 2.9);
    double e = 0.0;
    for (long i = 0; i < b; ++i) {
        const float y = bp[1].process(bp[0].process(0.5f * (s.l[static_cast<std::size_t>(i)] + s.r[static_cast<std::size_t>(i)])));
        if (i >= a) e += static_cast<double>(y) * y;
    }
    return e / static_cast<double>(std::max<long>(1, b - a));
}

double rms(const Stereo& s, long a, long b) {
    double e = 0.0;
    for (long i = a; i < b; ++i) e += 0.5 * (double(s.l[static_cast<std::size_t>(i)]) * s.l[static_cast<std::size_t>(i)] +
                                             double(s.r[static_cast<std::size_t>(i)]) * s.r[static_cast<std::size_t>(i)]);
    return std::sqrt(e / static_cast<double>(std::max<long>(1, b - a)));
}

double db(double x) { return 10.0 * std::log10(std::max(x, 1e-30)); }

bool finite(const Stereo& s) {
    for (std::size_t i = 0; i < s.size(); ++i)
        if (!std::isfinite(s.l[i]) || !std::isfinite(s.r[i])) return false;
    return true;
}

// Correlation of log band envelopes (16 third-octave bands 250 Hz - 8 kHz, 10 ms frames) between the modulator
// and the output: how well the output's spectrum over time follows the modulator's (intelligibility).
double envelopeCorrelation(const std::vector<float>& mod, const Stereo& out, long a, long b) {
    double sum = 0.0;
    int bands = 0;
    for (int k = 0; k < 16; ++k) {
        const double fc = 250.0 * std::pow(2.0, k / 3.0);
        dsp::Biquad bm[2], bo[2];
        for (int s = 0; s < 2; ++s) {
            bm[s].set(dsp::Biquad::Type::BandPass, kSr, fc, 4.3);
            bo[s].set(dsp::Biquad::Type::BandPass, kSr, fc, 4.3);
        }
        std::vector<double> em, eo;
        double am = 0.0, ao = 0.0;
        for (long i = 0; i < b; ++i) {
            const float ym = bm[1].process(bm[0].process(mod[static_cast<std::size_t>(i)]));
            const float yo = bo[1].process(bo[0].process(0.5f * (out.l[static_cast<std::size_t>(i)] + out.r[static_cast<std::size_t>(i)])));
            if (i < a) continue;
            am += double(ym) * ym;
            ao += double(yo) * yo;
            if ((i - a) % 480 == 479) {
                em.push_back(db(am + 1e-12));
                eo.push_back(db(ao + 1e-12));
                am = ao = 0.0;
            }
        }
        // floor 40 dB under each band's loudest frame (decay tails into silence are not the point)
        const double fm = *std::max_element(em.begin(), em.end()) - 40.0, fo = *std::max_element(eo.begin(), eo.end()) - 40.0;
        for (auto& v : em) v = std::max(v, fm);
        for (auto& v : eo) v = std::max(v, fo);
        double mm = 0, mo = 0;
        for (std::size_t i = 0; i < em.size(); ++i) { mm += em[i]; mo += eo[i]; }
        mm /= em.size();
        mo /= eo.size();
        double smo = 0, smm = 0, soo = 0;
        for (std::size_t i = 0; i < em.size(); ++i) {
            smo += (em[i] - mm) * (eo[i] - mo);
            smm += (em[i] - mm) * (em[i] - mm);
            soo += (eo[i] - mo) * (eo[i] - mo);
        }
        if (smm > 0 && soo > 0) {
            sum += smo / std::sqrt(smm * soo);
            ++bands;
        }
    }
    return bands ? sum / bands : 0.0;
}

// ---------------------------------------------------------------------------------------------------------------

void testFollowsModulator(const char* mode) {
    std::printf("%s: band energy follows the modulator\n", mode);
    const std::size_t n = static_cast<std::size_t>(burstStart(0, 1) + kBurstLen);
    const Stereo car = sawChord(n);
    const std::vector<float> mod = burstModulator(n);
    // flatten 0 and emphasis 0: the output is carrier x modulator envelope, so it can be compared with the carrier
    auto fx = vocoder({{"mode", mode}, {"flatten", 0}, {"emphasis", 0}, {"unvoiced", 0}, {"sibilance", 0}});
    const Stereo out = run(*fx, car, mod, 0, static_cast<long>(n));
    check(finite(out), "output finite");
    // E[burst][band] relative to the carrier's own energy in that band
    double rel[3][3];
    for (int k = 0; k < 3; ++k) {
        const long a = burstStart(k) + 2400, b = burstStart(k) + kBurstLen - 1200;
        for (int j = 0; j < 3; ++j) rel[k][j] = db(bandEnergy(out, kBurstHz[j], a, b)) - db(bandEnergy(car, kBurstHz[j], a, b));
    }
    for (int k = 0; k < 3; ++k) {
        double margin = 1e9;
        for (int j = 0; j < 3; ++j)
            if (j != k) margin = std::min(margin, rel[k][k] - rel[k][j]);
        check(margin > 15.0, fmt("burst at %.0f Hz opens its band: %+.1f dB vs %+.1f / %+.1f (margin %.1f dB > 15)", kBurstHz[k],
                                 rel[k][k], rel[k][(k + 1) % 3], rel[k][(k + 2) % 3], margin));
    }
    // between bursts (modulator silent) the output dies away: 30 ms and 75 ms into the 150 ms gap
    const double burst = rms(out, burstStart(0), burstStart(0) + kBurstLen);
    const long gap = burstStart(1) - kGap;
    const double early = 20 * std::log10(std::max(1e-12, rms(out, gap + 1440, gap + 1920) / burst));
    const double late = 20 * std::log10(std::max(1e-12, rms(out, gap + 3600, burstStart(1) - 200) / burst));
    check(early < -12.0 && late < -45.0, fmt("gap after a burst: output %.1f dB after 30 ms, %.1f dB after 75 ms", early, late));
    const double corr = envelopeCorrelation(mod, out, burstStart(0) - 2400, burstStart(0, 1) - 100);
    check(corr > 0.8, fmt("band-envelope correlation modulator vs output %.2f (> 0.8)", corr));
    const double base = envelopeCorrelation(mod, car, burstStart(0) - 2400, burstStart(0, 1) - 100);
    check(base < 0.3, fmt("(the carrier alone: %.2f)", base));
}

void testSilence(const char* mode) {
    std::printf("%s: silence\n", mode);
    const std::size_t n = 48000;
    const Stereo car = sawChord(n);
    const std::vector<float> none(n, 0.0f);
    auto fx = vocoder({{"mode", mode}});
    const Stereo out = run(*fx, car, none, 0, static_cast<long>(n));
    double peak = 0.0;
    for (std::size_t i = 0; i < n; ++i) peak = std::max({peak, double(std::fabs(out.l[i])), double(std::fabs(out.r[i]))});
    check(peak == 0.0, fmt("silent modulator -> silent output (peak %.3g)", peak));
    const Stereo quiet(n);
    auto fx2 = vocoder({{"mode", mode}});
    const std::vector<float> mod = burstModulator(n);
    const Stereo out2 = run(*fx2, quiet, mod, 0, static_cast<long>(n));
    double peak2 = 0.0;
    for (std::size_t i = 0; i < n; ++i) peak2 = std::max({peak2, double(std::fabs(out2.l[i])), double(std::fabs(out2.r[i]))});
    check(peak2 == 0.0, fmt("silent carrier -> silent output (peak %.3g)", peak2));
}

void testHold(const char* mode) {
    std::printf("%s: hold freezes the spectrum\n", mode);
    const std::size_t n = static_cast<std::size_t>(burstStart(2) + 2 * kBurstLen);
    const Stereo car = sawChord(n);
    std::vector<float> mod = burstModulator(n);
    for (std::size_t i = static_cast<std::size_t>(burstStart(1)); i < n; ++i) mod[i] = 0.0f;  // only the 400 Hz burst
    auto fx = vocoder({{"mode", mode}, {"flatten", 0}, {"emphasis", 0}});
    Stereo out(n);
    out.l = car.l;
    out.r = car.r;
    const long holdAt = burstStart(0) + kBurstLen / 2;
    for (long pos = 0; pos < static_cast<long>(n); pos += kBlock) {
        if (pos == holdAt / kBlock * kBlock) fx->setParam("hold", 1.0f);
        fx->process(out.l.data() + pos, out.r.data() + pos, kBlock, mod.data() + pos, mod.data() + pos);
    }
    const double before = rms(out, holdAt - 960, holdAt);            // the 20 ms before the freeze
    const double after = rms(out, burstStart(1), burstStart(2));  // modulator silent, spectrum held
    check(after > 0.5 * before && after < 2.0 * before,
          fmt("held output keeps sounding after the modulator stops (%.1f dB re the 20 ms before the hold)",
              20 * std::log10(after / before)));
    const double low = bandEnergy(out, 400.0, burstStart(1), burstStart(2)), high = bandEnergy(out, 3200.0, burstStart(1), burstStart(2));
    const double lowC = bandEnergy(car, 400.0, burstStart(1), burstStart(2)), highC = bandEnergy(car, 3200.0, burstStart(1), burstStart(2));
    check(db(low) - db(lowC) > db(high) - db(highC) + 15.0, "... with the held 400 Hz spectrum");
}

// Releasing 'hold' while the modulator is silent: the held sound fades with the release time instead of being cut
// within one control period (a click on a held chord - the demo's "drive" freeze ends in a pause).
void testHoldRelease(const char* mode) {
    std::printf("%s: releasing hold into silence fades out\n", mode);
    const std::size_t n = static_cast<std::size_t>(burstStart(2) + kBurstLen);
    const Stereo car = sawChord(n);
    std::vector<float> mod = burstModulator(n);
    for (std::size_t i = static_cast<std::size_t>(burstStart(1)); i < n; ++i) mod[i] = 0.0f;
    auto fx = vocoder({{"mode", mode}});  // release 15 ms (default)
    Stereo out(n);
    out.l = car.l;
    out.r = car.r;
    const long holdAt = (burstStart(0) + kBurstLen / 2) / kBlock * kBlock;
    const long freeAt = (burstStart(1) + 4800) / kBlock * kBlock;  // 100 ms into the silence
    for (long pos = 0; pos < static_cast<long>(n); pos += kBlock) {
        if (pos == holdAt) fx->setParam("hold", 1.0f);
        if (pos == freeAt) fx->setParam("hold", 0.0f);
        fx->process(out.l.data() + pos, out.r.data() + pos, kBlock, mod.data() + pos, mod.data() + pos);
    }
    const double before = rms(out, freeAt - 960, freeAt);
    auto rel = [&](double ms0, double ms1) {
        return 20.0 * std::log10(std::max(1e-12, rms(out, freeAt + std::lround(ms0 * 48), freeAt + std::lround(ms1 * 48)) / before));
    };
    const double at2 = rel(2, 3), at100 = rel(100, 120);
    check(at2 > -8.0 && at100 < -40.0,
          fmt("output 2-3 ms after the release %.1f dB (> -8: no cut), 100 ms after %.1f dB (< -40: it does close)", at2, at100));
}

void testShift() {
    std::printf("formant shift moves the bands (both modes)\n");
    const std::size_t n = static_cast<std::size_t>(burstStart(2));
    const Stereo car = sawChord(n);
    const std::vector<float> mod = burstModulator(n);
    const long a = burstStart(1) + 2400, b = burstStart(1) + kBurstLen - 1200;  // the 1.2 kHz burst
    for (const char* mode : {"classic", "lpc"}) {
        double peakHz[3];
        const double shifts[3] = {-12.0, 0.0, 12.0};
        for (int s = 0; s < 3; ++s) {
            auto fx = vocoder({{"mode", mode}, {"flatten", 1}, {"emphasis", 0}, {"shift", shifts[s]}, {"unvoiced", 0}, {"sibilance", 0}});
            const Stereo out = run(*fx, car, mod, 0, static_cast<long>(n));
            double best = -1e9;
            for (double f = 300.0; f < 6000.0; f *= std::pow(2.0, 1.0 / 12.0)) {
                const double e = bandEnergy(out, f, a, b);
                if (e > best) { best = e; peakHz[s] = f; }
            }
        }
        check(peakHz[0] < 0.75 * peakHz[1] && peakHz[2] > 1.4 * peakHz[1],
              fmt("%s: the 1.2 kHz burst peaks at %.0f / %.0f / %.0f Hz with shift -12 / 0 / +12", mode, peakHz[0], peakHz[1], peakHz[2]));
    }
}

void testLevel() {
    std::printf("level: a white modulator at the reference level reproduces the carrier\n");
    const std::size_t n = 96000;
    const Stereo car = sawChord(n);
    dsp::Rng rng(5);
    std::vector<float> white(n);
    for (auto& v : white) v = static_cast<float>(0.46 * 1.7320508) * rng.bipolar();  // RMS 0.46 (kRef)
    for (const char* mode : {"classic", "lpc"}) {
        auto fx = vocoder({{"mode", mode}, {"flatten", 0}, {"emphasis", 0}, {"unvoiced", 0}, {"sibilance", 0}});
        const Stereo out = run(*fx, car, white, 0, static_cast<long>(n));
        const double d = 20.0 * std::log10(rms(out, 24000, static_cast<long>(n)) / rms(car, 24000, static_cast<long>(n)));
        check(std::fabs(d) < 3.0, fmt("%s: output %+.1f dB re the carrier (within 3 dB)", mode, d));
    }
}

void testDeterminismAndBlocks() {
    std::printf("determinism, block-size independence\n");
    const std::size_t n = 60000;
    const Stereo car = sawChord(n);
    std::vector<float> mod = burstModulator(n);
    const std::vector<float> hiss = bandNoise(n, 5000.0, 0.02, 99);
    for (std::size_t i = 0; i < n; ++i) mod[i] += hiss[i];  // (some unvoiced bits for the noise paths)
    for (const char* mode : {"classic", "lpc"}) {
        const json p = {{"mode", mode}, {"shift", -3}, {"width", 1}};
        auto a = vocoder(p), b = vocoder(p), c = vocoder(p);
        const Stereo x = run(*a, car, mod, 0, static_cast<long>(n));
        const Stereo y = run(*b, car, mod, 0, static_cast<long>(n));
        const Stereo z = run(*c, car, mod, 0, static_cast<long>(n), 7);  // odd host blocks
        check(x.l == y.l && x.r == y.r, fmt("%s: bit-identical renders", mode));
        double diff = 0.0;
        for (std::size_t i = 0; i < n; ++i) diff = std::max({diff, double(std::fabs(x.l[i] - z.l[i])), double(std::fabs(x.r[i] - z.r[i]))});
        check(diff < 1e-6, fmt("%s: 7-sample host blocks give the same output (max diff %.2g)", mode, diff));
    }
}

void testPreview() {
    std::printf("preview parity (a render starting mid-song matches the full render after the envelopes settle)\n");
    const double startBeat = 13.5 + 5.0 / 24000.0;  // off the 32-sample grid
    const long start = std::llround(startBeat * kSr * 60.0 / kBpm), span = 48000;
    const std::size_t n = static_cast<std::size_t>(start + span);
    const Stereo car = sawChord(n);
    std::vector<float> mod(n, 0.0f);
    const long cycle = 3 * (kBurstLen + kGap);
    const std::vector<float> bursts = burstModulator(static_cast<std::size_t>(kFirst + cycle));
    for (long i = 0; i < static_cast<long>(n); ++i)  // bursts all the time, also across the preview start
        mod[static_cast<std::size_t>(i)] = bursts[static_cast<std::size_t>(kFirst + i % cycle)];
    for (const char* mode : {"classic", "lpc"}) {
        const json p = {{"mode", mode}, {"unvoiced", 1}, {"width", 0.7}};
        auto full = vocoder(p), prev = vocoder(p, startBeat);
        const Stereo f = run(*full, car, mod, 0, static_cast<long>(n));
        const Stereo q = run(*prev, car, mod, start, span);
        double diff = 0.0, peak = 0.0;
        for (long i = 24000; i < span; ++i) {
            const auto k = static_cast<std::size_t>(i), g = static_cast<std::size_t>(start + i);
            diff = std::max({diff, double(std::fabs(q.l[k] - f.l[g])), double(std::fabs(q.r[k] - f.r[g]))});
            peak = std::max({peak, double(std::fabs(f.l[g])), double(std::fabs(f.r[g]))});
        }
        check(peak > 0.01 && diff < 1e-4 * std::max(1.0, peak / 0.3),
              fmt("%s: preview vs full render max diff %.2g after 0.5 s (peak %.2f)", mode, diff, peak));
    }
}

void testExtremes() {
    std::printf("extreme settings stay finite\n");
    const std::size_t n = 30000;
    const Stereo car = sawChord(n, 0.6);  // hot carrier
    std::vector<float> mod = burstModulator(n);
    for (auto& v : mod) v *= 8.0f;  // clipping-level modulator
    const std::vector<json> cases = {
        {{"bands", 8}, {"lo", 1000}, {"hi", 2000}, {"bandwidth", 2}, {"attack", 0.5}, {"release", 5}, {"shift", 12}, {"emphasis", 12}, {"flatten", 1}, {"unvoiced", 1}, {"sibilance", 1}, {"width", 1}, {"output", 24}},
        {{"bands", 40}, {"lo", 50}, {"hi", 16000}, {"bandwidth", 0.5}, {"attack", 100}, {"release", 1000}, {"shift", -12}, {"emphasis", 0}, {"gate", -20}},
        {{"mode", "lpc"}, {"order", 40}, {"shift", 12}, {"emphasis", 12}, {"flatten", 1}, {"unvoiced", 1}, {"sibilance", 1}, {"attack", 0.5}, {"release", 5}, {"output", 24}},
        {{"mode", "lpc"}, {"order", 8}, {"shift", -12}, {"emphasis", 0}, {"flatten", 0}, {"release", 1000}},
    };
    for (const json& c : cases) {
        auto fx = vocoder(c);
        const Stereo out = run(*fx, car, mod, 0, static_cast<long>(n));
        double peak = 0.0;
        for (std::size_t i = 0; i < n; ++i) peak = std::max({peak, double(std::fabs(out.l[i])), double(std::fabs(out.r[i]))});
        check(finite(out) && peak < 1e5, fmt("%s: finite (peak %.2f)", c.dump().substr(0, 70).c_str(), peak));
    }
}

void testSampleRates() {
    std::printf("other sample rates (44.1 / 96 kHz): level and finiteness\n");
    const std::size_t n = 48000;
    const Stereo car = sawChord(n);
    dsp::Rng rng(9);
    std::vector<float> white(n);
    for (auto& v : white) v = static_cast<float>(0.46 * 1.7320508) * rng.bipolar();
    for (double fs : {44100.0, 96000.0}) {
        for (const json& p : {json{{"mode", "classic"}, {"flatten", 0}, {"emphasis", 0}, {"unvoiced", 0}, {"sibilance", 0}},
                              json{{"mode", "lpc"}, {"flatten", 0}, {"emphasis", 0}, {"unvoiced", 0}, {"sibilance", 0}},
                              json{{"hi", 16000}, {"shift", 12}, {"bands", 40}, {"unvoiced", 1}, {"sibilance", 1}},
                              json{{"mode", "lpc"}, {"shift", -12}, {"order", 40}, {"unvoiced", 1}}}) {
            auto fx = createEffect("vocoder");
            fx->configure(p);
            RenderContext ctx;
            ctx.sampleRate = fs;
            ctx.bpm = kBpm;
            ctx.seed = 3;
            fx->prepare(ctx);
            const Stereo out = run(*fx, car, white, 0, static_cast<long>(n));
            const double d = 20.0 * std::log10(std::max(1e-12, rms(out, 12000, static_cast<long>(n)) / rms(car, 12000, static_cast<long>(n))));
            // neutral settings reproduce the carrier; with emphasis, flatten and the noise paths a white (very bright,
            // 'unvoiced') modulator comes out much louder than speech would - only sanity-checked here
            const bool neutral = p.value("flatten", 0.7) == 0.0;
            check(finite(out) && d > -12.0 && d < (neutral ? 4.0 : 30.0),
                  fmt("%.0f Hz %s: finite, output %+.1f dB re the carrier", fs, p.dump().substr(0, 60).c_str(), d));
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------

bool configError(const std::function<void()>& f, const std::string& expect) {
    try {
        f();
    } catch (const ConfigError& e) {
        const bool ok = std::string(e.what()).find(expect) != std::string::npos;
        if (!ok) std::printf("       (message was: %s)\n", e.what());
        return ok;
    }
    return false;
}

json song(bool keyed) {
    json fx = {{"type", "vocoder"}, {"params", {{"bands", 16}}}};
    if (keyed) fx["sidechain"] = "voice";
    return {
        {"format", "agentsound.render"}, {"version", 1}, {"title", "vocoder routing"}, {"tempo", 120},
        {"lengthBeats", 8}, {"tailSeconds", 1}, {"seed", 3},
        {"tracks", json::array({
            {{"id", "voice"}, {"mute", true},
             {"instrument", {{"type", "va"}, {"params", {{"osc1.wave", "saw"}, {"noise.level", 0.3}}}}},
             {"fx", json::array({{{"type", "vowel"}, {"params", {{"vowel", "a"}}}}})},
             {"modulators", json::array({{{"target", "fx.0.morph"}, {"source", {{"type", "lfo"}, {"shape", "triangle"}, {"rateBeats", 2}}},
                                          {"mode", "absolute"}, {"min", 0}, {"max", 4}}})},
             {"notes", json::array({json::array({0, 3, 48, 100}), json::array({4, 3, 48, 100})})}},
            {{"id", "choir"}, {"instrument", {{"type", "va"}, {"params", {{"osc1.wave", "saw"}, {"unison", 3}}}}},
             {"fx", json::array({fx})},
             {"notes", json::array({json::array({0, 8, 57, 100}), json::array({0, 8, 60, 100}), json::array({0, 8, 64, 100})})}},
        })},
        {"master", {{"fx", json::array({{{"type", "limiter"}, {"params", json::object()}}})}}},
    };
}

void testStrictAndRouting() {
    std::printf("strictness and routing\n");
    check(effectAcceptsSidechain("vocoder") && effectRequiresSidechain("vocoder") && !effectRequiresSidechain("compressor"),
          "registry: the vocoder requires a sidechain");
    check(configError([] { validateSong(parseSong(song(false)), "assets"); }, "needs a \"sidechain\""),
          "a vocoder without a sidechain is a ConfigError");
    check(configError([] { vocoder({{"bands", 20.5}}); }, "whole number"), "bands must be a whole number");
    check(configError([] { vocoder({{"order", 12.5}, {"mode", "lpc"}}); }, "whole number"), "order must be a whole number");
    check(!configError([] { vocoder({{"lo", 1000}, {"hi", 2000}}); }, "") && configError([] { vocoder({{"lo", 1100}}); }, "outside 50..1000"),
          "lo / hi ranges (hi is always at least an octave above lo)");
    check(configError([] { vocoder({{"mode", "talkbox"}}); }, "classic|lpc"), "unknown mode");
    check(configError([] { vocoder({{"carrier", 1}}); }, "unknown parameter"), "unknown parameter");
    bool ok = true;
    try {
        validateSong(parseSong(song(true)), "assets");
    } catch (const std::exception& e) {
        ok = false;
        std::printf("       (%s)\n", e.what());
    }
    check(ok, "a keyed vocoder validates");

    // Muted modulator: rendered and heard only through the vocoder; not in the mix, not analysed.
    namespace fs = std::filesystem;
    const fs::path dir = fs::path(".scratch") / "vocoder";
    RenderOptions o;
    o.outDir = dir.string();
    o.assetDir = "assets";
    o.quiet = true;
    o.pngs = false;
    renderSong(parseSong(song(true)), o);
    std::ifstream in(dir / "report.json");
    const json report = json::parse(in);
    bool voiceAnalysed = false, choirAnalysed = false;
    for (const auto& node : report.at("nodes")) {
        voiceAnalysed = voiceAnalysed || node.at("id") == "voice";
        choirAnalysed = choirAnalysed || node.at("id") == "choir";
    }
    check(choirAnalysed && !voiceAnalysed, "the muted modulator track is not analysed (the carrier track is)");
    const double lufs = report.at("global").at("lufsIntegrated").get<double>();
    check(lufs > -30.0 && lufs < -3.0, fmt("the vocoded mix is audible (%.1f LUFS)", lufs));
    // the second half (beats 4-8) talks again after a gap (beats 3-4): the gap is silent
    json quiet = song(true);
    quiet["tracks"][0]["notes"] = json::array();
    const fs::path dir2 = fs::path(".scratch") / "vocoder_silent";
    o.outDir = dir2.string();
    o.pngs = false;
    renderSong(parseSong(quiet), o);
    std::ifstream in2(dir2 / "report.json");
    const json r2 = json::parse(in2);
    const double silentLufs = r2.at("global").at("lufsIntegrated").get<double>();
    check(silentLufs < -69.0, fmt("without modulator notes the vocoded track is silent (%.1f LUFS)", silentLufs));
}

}  // namespace

int main() {
    std::printf("test_vocoder\n");
    for (const char* mode : {"classic", "lpc"}) {
        testFollowsModulator(mode);
        testSilence(mode);
        testHold(mode);
        testHoldRelease(mode);
    }
    testShift();
    testLevel();
    testDeterminismAndBlocks();
    testPreview();
    testExtremes();
    testSampleRates();
    testStrictAndRouting();
    if (gFail) std::printf("FAILED: %d of %d check(s)\n", gFail, gChecks);
    else std::printf("all %d checks passed\n", gChecks);
    return gFail ? 1 : 0;
}
