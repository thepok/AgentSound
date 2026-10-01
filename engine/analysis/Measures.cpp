#include "analysis/Measures.h"

#include "analysis/Aggregate.h"
#include "analysis/Fft.h"
#include "analysis/Loudness.h"
#include "analysis/StreamStats.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <vector>

namespace as::analysis {

namespace {

constexpr double kPi = 3.14159265358979323846;

double r1(double x) { return std::isfinite(x) ? std::round(x * 10.0) / 10.0 + 0.0 : 0.0; }
double r2(double x) { return std::isfinite(x) ? std::round(x * 100.0) / 100.0 + 0.0 : 0.0; }
double r3(double x) { return std::isfinite(x) ? std::round(x * 1000.0) / 1000.0 + 0.0 : 0.0; }

// RBJ cookbook high-pass (the low-pass lives in Loudness.h).
Biquad64 highPass(double sr, double f, double q) {
    const double w0 = 2.0 * kPi * std::clamp(f, 1.0, sr * 0.49) / sr;
    const double cw = std::cos(w0), alpha = std::sin(w0) / (2.0 * q);
    const double a0 = 1.0 + alpha;
    Biquad64 b;
    b.b0 = (1.0 + cw) / 2.0 / a0;
    b.b1 = -(1.0 + cw) / a0;
    b.b2 = b.b0;
    b.a1 = -2.0 * cw / a0;
    b.a2 = (1.0 - alpha) / a0;
    return b;
}

// Linear-interpolated percentile of a sorted vector (p in 0..1).
double pct(const std::vector<double>& sorted, double p) {
    if (sorted.empty()) return 0.0;
    const double pos = std::clamp(p, 0.0, 1.0) * static_cast<double>(sorted.size() - 1);
    const auto i = static_cast<std::size_t>(pos);
    if (i + 1 >= sorted.size()) return sorted.back();
    return sorted[i] + (sorted[i + 1] - sorted[i]) * (pos - static_cast<double>(i));
}

std::vector<double> sortedCopy(std::vector<double> v) {
    std::sort(v.begin(), v.end());
    return v;
}

int nextPow2(double x) {
    int n = 8;
    while (n < x && n < (1 << 20)) n <<= 1;
    return n;
}

// ------------------------------------------------------------------ long-term spectrum + stereo

struct Spectrum {
    int n{0};
    double df{1.0};
    std::vector<double> pl, pr, x;  // one-sided mean-square per bin (L, R, Re(L conj R)), averaged over the frames used
    int framesUsed{0}, framesTotal{0};
};

// Welch average (Hann, 50 % overlap, ~3 Hz bins) over the active frames: frames whose mean square is
// more than 20 dB under the mean frame (or below -70 dBFS) are skipped, like the gated loudness.
Spectrum longTermSpectrum(const float* L, const float* R, std::size_t len, double sr) {
    Spectrum s;
    s.n = nextPow2(sr / 3.0);
    const int n = s.n, half = n / 2, hop = n / 2;
    s.df = sr / n;
    s.pl.assign(static_cast<std::size_t>(half + 1), 0.0);
    s.pr = s.pl;
    s.x = s.pl;
    if (len == 0) return s;
    const std::size_t frames = len <= static_cast<std::size_t>(n) ? 1 : (len - static_cast<std::size_t>(n)) / hop + 1;
    // Frame levels for the gate.
    std::vector<double> ms(frames, 0.0);
    double mean = 0.0;
    for (std::size_t f = 0; f < frames; ++f) {
        const std::size_t s0 = f * hop, s1 = std::min(len, s0 + static_cast<std::size_t>(n));
        double e = 0.0;
        for (std::size_t i = s0; i < s1; ++i) e += static_cast<double>(L[i]) * L[i] + static_cast<double>(R[i]) * R[i];
        ms[f] = e / (2.0 * n);
        mean += ms[f];
    }
    mean /= static_cast<double>(frames);
    const double gate = std::max(1e-7, 0.01 * mean);
    const Fft fft(n);
    const auto win = hannWindow(n);
    double w2 = 0.0;
    for (float w : win) w2 += static_cast<double>(w) * w;
    std::vector<float> re(static_cast<std::size_t>(n)), im(static_cast<std::size_t>(n));
    const double norm = 1.0 / (static_cast<double>(n) * w2);
    s.framesTotal = static_cast<int>(frames);
    for (std::size_t f = 0; f < frames; ++f) {
        if (ms[f] < gate) continue;
        const std::size_t s0 = f * hop;
        for (int i = 0; i < n; ++i) {
            const std::size_t k = s0 + static_cast<std::size_t>(i);
            const bool in = k < len;
            re[static_cast<std::size_t>(i)] = in ? L[k] * win[static_cast<std::size_t>(i)] : 0.0f;
            im[static_cast<std::size_t>(i)] = in ? R[k] * win[static_cast<std::size_t>(i)] : 0.0f;
        }
        fft.forward(re.data(), im.data());
        for (int k = 0; k <= half; ++k) {
            const StereoBin b = splitStereo(re.data(), im.data(), n, k);
            const double c = (k == 0 || k == half) ? norm : 2.0 * norm;
            s.pl[static_cast<std::size_t>(k)] += b.pl * c;
            s.pr[static_cast<std::size_t>(k)] += b.pr * c;
            s.x[static_cast<std::size_t>(k)] += b.cross * c;
        }
        ++s.framesUsed;
    }
    if (s.framesUsed > 0) {
        const double inv = 1.0 / s.framesUsed;
        for (int k = 0; k <= half; ++k) {
            s.pl[static_cast<std::size_t>(k)] *= inv;
            s.pr[static_cast<std::size_t>(k)] *= inv;
            s.x[static_cast<std::size_t>(k)] *= inv;
        }
    }
    return s;
}

struct BandSums {
    double ll{0}, rr{0}, lr{0};
    double ms() const { return 0.5 * (ll + rr); }
};

// Sums of the per-bin values over [f0, f1), bins weighted by their overlap with the band.
BandSums bandSums(const Spectrum& s, double f0, double f1) {
    BandSums b;
    const int half = s.n / 2;
    const int k0 = std::max(0, static_cast<int>(std::floor(f0 / s.df + 0.5)));
    const int k1 = std::min(half, static_cast<int>(std::floor(f1 / s.df + 0.5)));
    for (int k = k0; k <= k1; ++k) {
        const double ov = std::min((k + 0.5) * s.df, f1) - std::max((k - 0.5) * s.df, f0);
        if (ov <= 0) continue;
        const double w = ov / s.df;
        b.ll += w * s.pl[static_cast<std::size_t>(k)];
        b.rr += w * s.pr[static_cast<std::size_t>(k)];
        b.lr += w * s.x[static_cast<std::size_t>(k)];
    }
    return b;
}

json spectrumJson(const Spectrum& s, double sr) {
    static constexpr double kNominal[] = {25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
                                          800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000,
                                          10000, 12500, 16000, 20000};
    json hz = json::array(), db = json::array();
    for (int i = 0; i < 30; ++i) {
        const double fc = 1000.0 * std::exp2((i - 16) / 3.0);
        const double f0 = fc * std::exp2(-1.0 / 6.0), f1 = std::min(fc * std::exp2(1.0 / 6.0), sr * 0.5);
        if (f1 <= f0) break;
        hz.push_back(kNominal[i]);
        db.push_back(r1(dbFromPower(bandSums(s, f0, f1).ms())));
    }
    json j;
    j["hz"] = hz;
    j["db"] = db;
    j["framesUsed"] = s.framesUsed;
    j["framesTotal"] = s.framesTotal;
    j["binHz"] = r2(s.df);
    return j;
}

json stereoJson(const Spectrum& s, double sr) {
    json j;
    json oct = json::array(), w = json::array(), c = json::array();
    static constexpr double kOct[] = {31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000};
    for (double fc : kOct) {
        const double f0 = fc / std::sqrt(2.0), f1 = std::min(fc * std::sqrt(2.0), sr * 0.5);
        if (f1 <= f0) break;
        const BandSums b = bandSums(s, f0, f1);
        oct.push_back(fc);
        w.push_back(r1(widthPct(b.ll, b.rr, b.lr)));
        c.push_back(r2(correlation(b.ll, b.rr, b.lr)));
    }
    j["octaveHz"] = oct;
    j["widthPct"] = w;
    j["correlation"] = c;
    json bands = json::object();
    for (int b = 0; b < kNumBands; ++b) {
        const BandSums v = bandSums(s, kBandEdgesHz[b], std::min(kBandEdgesHz[b + 1], sr * 0.5));
        bands[kBandNames[b]] = {{"widthPct", r1(widthPct(v.ll, v.rr, v.lr))}, {"correlation", r2(correlation(v.ll, v.rr, v.lr))}};
    }
    j["bands"] = bands;
    const BandSums low = bandSums(s, 20.0, 120.0);
    j["below120Hz"] = {{"widthPct", r1(widthPct(low.ll, low.rr, low.lr))}, {"correlation", r2(correlation(low.ll, low.rr, low.lr))}};
    const BandSums hi = bandSums(s, 150.0, sr * 0.5);
    j["above150Hz"] = {{"widthPct", r1(widthPct(hi.ll, hi.rr, hi.lr))}, {"correlation", r2(correlation(hi.ll, hi.rr, hi.lr))}};
    const BandSums all = bandSums(s, 20.0, sr * 0.5);
    j["whole"] = {{"widthPct", r1(widthPct(all.ll, all.rr, all.lr))}, {"correlation", r2(correlation(all.ll, all.rr, all.lr))}};
    return j;
}

// ------------------------------------------------------------------ loudness distribution

json loudnessJson(const float* L, const float* R, std::size_t len, double sr) {
    const auto tick = static_cast<std::size_t>(std::max(1L, std::lround(sr / 10.0)));
    const std::size_t ticks = len / tick;
    std::vector<double> k(ticks, 0.0), peak(ticks, 0.0);
    KWeighting kl(sr), kr(sr);
    for (std::size_t t = 0; t < ticks; ++t) {
        double e = 0.0, p = 0.0;
        for (std::size_t i = t * tick; i < (t + 1) * tick; ++i) {
            const double yl = kl.process(L[i]), yr = kr.process(R[i]);
            e += yl * yl + yr * yr;
            p = std::max(p, static_cast<double>(std::max(std::fabs(L[i]), std::fabs(R[i]))));
        }
        k[t] = e;
        peak[t] = p;
    }
    json j;
    const double T = static_cast<double>(tick);
    std::vector<double> blocks, shortMs, shortPeak;
    double mMax = kDbFloor;
    for (std::size_t t = 3; t < ticks; ++t) {
        const double ms = (k[t] + k[t - 1] + k[t - 2] + k[t - 3]) / (4.0 * T);
        blocks.push_back(ms);
        mMax = std::max(mMax, lufsFromMeanSquare(ms));
    }
    for (std::size_t t = 29; t < ticks; ++t) {
        double s = 0.0, p = 0.0;
        for (std::size_t q = t - 29; q <= t; ++q) { s += k[q]; p = std::max(p, peak[q]); }
        shortMs.push_back(s / (30.0 * T));
        shortPeak.push_back(p);
    }
    const double I = blocks.empty() ? kDbFloor : integratedLoudness(blocks);
    j["integratedLufs"] = r1(I);
    j["loudnessRange"] = r1(loudnessRange(shortMs));
    j["momentaryMaxLu"] = r1(I > kDbFloor ? mMax - I : 0.0);
    // EBU R128 gating of the short-term values (as for LRA): absolute -70 LUFS, relative -20 LU.
    double sum = 0.0;
    std::size_t count = 0;
    for (double ms : shortMs)
        if (lufsFromMeanSquare(ms) > -70.0) { sum += ms; ++count; }
    std::vector<double> rel, psr;
    double stMax = kDbFloor;
    if (count > 0 && I > kDbFloor) {
        const double gate = lufsFromMeanSquare(sum / static_cast<double>(count)) - 20.0;
        for (std::size_t i = 0; i < shortMs.size(); ++i) {
            const double l = lufsFromMeanSquare(shortMs[i]);
            if (l <= -70.0 || l <= gate) continue;
            rel.push_back(l - I);
            stMax = std::max(stMax, l);
            psr.push_back(dbFromAmplitude(shortPeak[i]) - l);
        }
    }
    j["shortTermValues"] = static_cast<int>(rel.size());
    if (rel.empty()) return j;
    j["shortTermMaxLu"] = r1(stMax - I);
    const auto s = sortedCopy(rel);
    json p = json::object();
    for (const auto& [name, q] : {std::pair{"p5", 0.05}, {"p10", 0.10}, {"p25", 0.25}, {"p50", 0.50}, {"p75", 0.75}, {"p90", 0.90},
                                  {"p95", 0.95}})
        p[name] = r1(pct(s, q));
    j["shortTermLu"] = p;
    // 1 LU histogram of the short-term loudness relative to the integrated, -30..+10 LU (clamped).
    constexpr int kBins = 40;
    std::vector<double> hist(kBins, 0.0);
    for (double v : rel) hist[static_cast<std::size_t>(std::clamp(static_cast<int>(std::floor(v + 30.0)), 0, kBins - 1))] += 1.0;
    json hp = json::array();
    for (double h : hist) hp.push_back(r1(100.0 * h / static_cast<double>(rel.size())));
    j["histogram"] = {{"fromLu", -30}, {"stepLu", 1}, {"pct", hp}};
    // Time within 2 LU of the loudest 3 s: how much of the track sits at full loudness.
    std::size_t near = 0;
    for (double v : rel) near += (v >= stMax - I - 2.0) ? 1 : 0;
    j["nearMaxPct"] = r1(100.0 * static_cast<double>(near) / static_cast<double>(rel.size()));
    j["psrDb"] = r1(pct(sortedCopy(psr), 0.5));
    return j;
}

// ------------------------------------------------------------------ envelopes, transients, decay

// Envelope in dB: mean square per hop, smoothed by a centred moving average of `smooth` hops.
std::vector<float> envelopeDb(const std::vector<float>& x, std::size_t hop, int smooth) {
    const std::size_t nh = x.size() / std::max<std::size_t>(1, hop);
    std::vector<double> ms(nh, 0.0);
    for (std::size_t j = 0; j < nh; ++j) {
        double e = 0.0;
        for (std::size_t i = j * hop; i < (j + 1) * hop; ++i) e += static_cast<double>(x[i]) * x[i];
        ms[j] = e / static_cast<double>(hop);
    }
    std::vector<float> db(nh, static_cast<float>(kDbFloor));
    const int h = std::max(0, smooth / 2);
    double acc = 0.0;
    int cnt = 0;
    std::size_t lo = 0, hi = 0;  // window [lo, hi)
    for (std::size_t j = 0; j < nh; ++j) {
        const std::size_t want0 = j >= static_cast<std::size_t>(h) ? j - static_cast<std::size_t>(h) : 0;
        const std::size_t want1 = std::min(nh, j + static_cast<std::size_t>(h) + 1);
        while (hi < want1) { acc += ms[hi++]; ++cnt; }
        while (lo < want0) { acc -= ms[lo++]; --cnt; }
        db[j] = static_cast<float>(dbFromPower(cnt > 0 ? std::max(0.0, acc) / cnt : 0.0));
    }
    return db;
}

struct Onsets {
    std::vector<std::size_t> hops;   // envelope index of each onset
    std::vector<double> attackDb;    // rise above the level before (pre window)
    std::vector<double> hitDb;       // per active second: the biggest rise (the main hit of that second)
    double activeSec{0.0};
};

// Onsets of a 1 ms envelope: local maxima (+-10 ms) of the rise over the lowest level in the pre
// window [t - preTo, t - preFrom] that reach minRise dB, at most one per `gap`, above the floor
// (45 dB under the loud level).
Onsets detectOnsets(const std::vector<float>& db, double hopSec, double minRise, double preFrom, double preTo, double gapSec) {
    Onsets o;
    const std::size_t n = db.size();
    if (n < 64) return o;
    std::vector<double> lv(db.begin(), db.end());
    std::sort(lv.begin(), lv.end());
    const double loud = pct(lv, 0.95);
    const double floor = std::max(loud - 45.0, -70.0);
    std::size_t active = 0;
    for (float v : db) active += v > loud - 30.0 ? 1 : 0;
    o.activeSec = static_cast<double>(active) * hopSec;
    const auto a0 = static_cast<std::size_t>(std::lround(preFrom / hopSec)), a1 = static_cast<std::size_t>(std::lround(preTo / hopSec));
    std::vector<float> rise(n, 0.0f);
    std::deque<std::size_t> dq;  // sliding minimum of db over [j - a1, j - a0]
    for (std::size_t j = 0; j < n; ++j) {
        if (j >= a0) {
            const std::size_t add = j - a0;
            while (!dq.empty() && db[dq.back()] >= db[add]) dq.pop_back();
            dq.push_back(add);
        }
        while (!dq.empty() && j >= a1 && dq.front() < j - a1) dq.pop_front();
        if (j >= a1 && !dq.empty()) rise[j] = std::max(0.0f, db[j] - db[dq.front()]);
    }
    // The main hit of every active second: its biggest rise (independent of the onset threshold).
    const auto sec = static_cast<std::size_t>(std::lround(1.0 / hopSec));
    for (std::size_t w0 = a1; w0 + sec <= n; w0 += sec) {
        float best = 0.0f, top = -1e9f;
        for (std::size_t j = w0; j < w0 + sec; ++j) {
            best = std::max(best, rise[j]);
            top = std::max(top, db[j]);
        }
        if (top > loud - 30.0) o.hitDb.push_back(best);
    }
    const auto win = static_cast<std::size_t>(std::lround(0.010 / hopSec));
    const auto gap = static_cast<std::size_t>(std::lround(gapSec / hopSec));
    std::size_t last = 0;
    bool any = false;
    for (std::size_t j = a1; j < n; ++j) {
        if (rise[j] < minRise || db[j] < floor) continue;
        bool isMax = true;
        for (std::size_t q = (j >= win ? j - win : 0); q <= std::min(n - 1, j + win) && isMax; ++q)
            if (rise[q] > rise[j] || (rise[q] == rise[j] && q < j)) isMax = false;
        if (!isMax || (any && j - last < gap)) continue;
        o.hops.push_back(j);
        o.attackDb.push_back(rise[j]);
        last = j;
        any = true;
    }
    return o;
}

json onsetJson(const Onsets& o) {
    json j;
    j["onsets"] = static_cast<int>(o.hops.size());
    j["perSec"] = r2(o.activeSec >= 1.0 ? static_cast<double>(o.hops.size()) / o.activeSec : 0.0);
    if (!o.attackDb.empty()) {
        const auto s = sortedCopy(o.attackDb);
        j["attackDb"] = r1(pct(s, 0.5));
        j["attackP90Db"] = r1(pct(s, 0.9));
    }
    if (!o.hitDb.empty()) j["hitDb"] = r1(pct(sortedCopy(o.hitDb), 0.5));
    return j;
}

double crestDb(const std::vector<float>& x) {
    double peak = 0.0, e = 0.0;
    for (float v : x) { peak = std::max(peak, static_cast<double>(std::fabs(v))); e += static_cast<double>(v) * v; }
    if (x.empty() || e <= 0.0) return 0.0;
    return dbFromAmplitude(peak) - dbFromPower(e / static_cast<double>(x.size()));
}

std::vector<float> filtered(const std::vector<float>& x, std::initializer_list<Biquad64> stages) {
    std::vector<float> y(x);
    for (Biquad64 b : stages) {
        b.reset();
        for (float& v : y) v = static_cast<float>(b.process(v));
    }
    return y;
}

// Free decays of a 10 ms envelope: from a local maximum, the envelope falls (0.5 dB tolerance) for
// >= 150 ms and >= 12 dB; a line fitted between -3 and -30 dB (>= 8 points, >= 10 dB, r^2 >= 0.85)
// gives T60 = 60 / slope.
json decayJson(const std::vector<float>& db, double hopSec) {
    json j;
    std::vector<double> t60;
    const std::size_t n = db.size();
    std::vector<double> lv(db.begin(), db.end());
    std::sort(lv.begin(), lv.end());
    const double loud = lv.empty() ? kDbFloor : pct(lv, 0.95);
    std::size_t p = 3;
    while (p + 3 < n) {
        bool peak = db[p] > loud - 25.0;
        for (std::size_t q = p - 3; q <= p + 3 && peak; ++q) peak = q == p || db[q] <= db[p];
        if (!peak) { ++p; continue; }
        std::size_t q = p + 1;
        float lowest = db[p];
        while (q < n && db[q] <= db[q - 1] + 0.5f && db[q] >= db[p] - 45.0f) { lowest = std::min(lowest, db[q]); ++q; }
        const std::size_t end = q;  // exclusive
        const double drop = db[p] - lowest;
        if (static_cast<double>(end - p) * hopSec >= 0.15 && drop >= 12.0) {
            double sx = 0, sy = 0, sxx = 0, sxy = 0, syy = 0;
            int m = 0;
            double hiLv = -1e9, loLv = 1e9;
            for (std::size_t k = p; k < end; ++k) {
                const double rel = db[k] - db[p];
                if (rel > -3.0 || rel < -30.0) continue;
                const double x = static_cast<double>(k - p) * hopSec, y = db[k];
                sx += x; sy += y; sxx += x * x; sxy += x * y; syy += y * y;
                hiLv = std::max(hiLv, y);
                loLv = std::min(loLv, y);
                ++m;
            }
            if (m >= 8 && hiLv - loLv >= 10.0) {
                const double den = m * sxx - sx * sx;
                const double slope = den > 0 ? (m * sxy - sx * sy) / den : 0.0;
                const double vy = m * syy - sy * sy;
                const double r2v = (den > 0 && vy > 0) ? (m * sxy - sx * sy) * (m * sxy - sx * sy) / (den * vy) : 0.0;
                if (slope < 0.0 && r2v >= 0.85) {
                    const double t = -60.0 / slope;
                    if (t >= 0.05 && t <= 12.0) t60.push_back(t);
                }
            }
        }
        p = std::max(end, p + 1);
    }
    j["decays"] = static_cast<int>(t60.size());
    if (t60.empty()) {
        j["robust"] = false;
        j["note"] = "no free decays (dense material without stops): no tail estimate";
        return j;
    }
    const auto s = sortedCopy(t60);
    const double med = pct(s, 0.5), tail = pct(s, 0.75), p90 = pct(s, 0.9);
    j["t60Sec"] = r2(med);
    j["tailT60Sec"] = r2(tail);
    const bool consistent = tail > 0 && (p90 - med) / tail < 0.8;
    const bool robust = t60.size() >= 8 && consistent;
    j["robust"] = robust;
    j["note"] = robust ? "T60 of free decays (400 Hz-4 kHz); tailT60Sec = the slower quarter (reverb tails ring longest)"
                       : "too few or too scattered free decays: not a reliable tail estimate";
    return j;
}

// Energy 80-300 ms after strong, isolated hits vs the first 50 ms (mid band, 1 ms envelope).
json sustainJson(const Onsets& hits, const std::vector<float>& midDb, double hopSec) {
    json j;
    std::vector<double> ratio;
    const auto h = [&](double sec) { return static_cast<std::size_t>(std::lround(sec / hopSec)); };
    for (std::size_t i = 0; i < hits.hops.size(); ++i) {
        if (hits.attackDb[i] < 9.0) continue;
        const std::size_t t = hits.hops[i];
        if (i + 1 < hits.hops.size() && hits.hops[i + 1] < t + h(0.32)) continue;  // the next hit would land in the window
        if (t + h(0.30) >= midDb.size()) break;
        double early = 0.0, late = 0.0;
        for (std::size_t k = t; k < t + h(0.05); ++k) early += std::pow(10.0, midDb[k] / 10.0);
        for (std::size_t k = t + h(0.08); k < t + h(0.30); ++k) late += std::pow(10.0, midDb[k] / 10.0);
        early /= static_cast<double>(h(0.05));
        late /= static_cast<double>(h(0.30) - h(0.08));
        if (early > 0.0 && late > 0.0) ratio.push_back(10.0 * std::log10(late / early));
    }
    j["hits"] = static_cast<int>(ratio.size());
    if (ratio.empty()) {
        j["robust"] = false;
        return j;
    }
    const auto s = sortedCopy(ratio);
    j["lateEarlyDb"] = r1(pct(s, 0.5));
    const double iqr = pct(s, 0.75) - pct(s, 0.25);
    j["iqrDb"] = r1(iqr);
    j["robust"] = ratio.size() >= 12 && iqr <= 8.0;
    return j;
}

}  // namespace

// ------------------------------------------------------------------ tempo

TempoEstimate estimateTempo(const float* L, const float* R, std::size_t len, double sr) {
    TempoEstimate est;
    const int n = nextPow2(sr / 23.4);  // 2048 at 48 kHz
    const auto hop = static_cast<std::size_t>(std::lround(sr / 100.0));  // 10 ms
    if (len < static_cast<std::size_t>(n) + hop * 400) return est;  // < ~4 s
    const std::size_t frames = (len - static_cast<std::size_t>(n)) / hop + 1;
    const Fft fft(n);
    const auto win = hannWindow(n);
    double w2 = 0.0, msAll = 0.0;
    for (float w : win) w2 += static_cast<double>(w) * w;
    for (std::size_t i = 0; i < len; ++i) msAll += 0.5 * (static_cast<double>(L[i]) * L[i] + static_cast<double>(R[i]) * R[i]);
    msAll /= static_cast<double>(len);
    if (!(msAll > 1e-12)) return est;
    const double scale = 1.0 / std::sqrt(static_cast<double>(n) * w2 * msAll);
    const int k0 = std::max(1, static_cast<int>(30.0 / (sr / n))), k1 = std::min(n / 2, static_cast<int>(8000.0 / (sr / n)));
    std::vector<float> re(static_cast<std::size_t>(n)), im(static_cast<std::size_t>(n)), prev(static_cast<std::size_t>(n / 2 + 1), 0.0f);
    std::vector<double> nov(frames, 0.0);
    for (std::size_t f = 0; f < frames; ++f) {
        const std::size_t s0 = f * hop;
        for (int i = 0; i < n; ++i) {
            const auto k = s0 + static_cast<std::size_t>(i);
            re[static_cast<std::size_t>(i)] = 0.5f * (L[k] + R[k]) * win[static_cast<std::size_t>(i)];
            im[static_cast<std::size_t>(i)] = 0.0f;
        }
        fft.forward(re.data(), im.data());
        double flux = 0.0;
        for (int k = k0; k <= k1; ++k) {
            const double mag = std::sqrt(static_cast<double>(re[static_cast<std::size_t>(k)]) * re[static_cast<std::size_t>(k)] +
                                         static_cast<double>(im[static_cast<std::size_t>(k)]) * im[static_cast<std::size_t>(k)]) * scale;
            const auto c = static_cast<float>(std::log1p(100.0 * mag));
            if (f > 0) flux += std::max(0.0f, c - prev[static_cast<std::size_t>(k)]);
            prev[static_cast<std::size_t>(k)] = c;
        }
        nov[f] = flux;
    }
    // Remove the slow trend (0.5 s moving mean) and keep the rises.
    std::vector<double> x(frames, 0.0);
    {
        const std::size_t h = 25;
        double acc = 0.0;
        std::size_t lo = 0, hi = 0;
        for (std::size_t f = 0; f < frames; ++f) {
            const std::size_t w0 = f >= h ? f - h : 0, w1 = std::min(frames, f + h + 1);
            while (hi < w1) acc += nov[hi++];
            while (lo < w0) acc -= nov[lo++];
            x[f] = std::max(0.0, nov[f] - acc / static_cast<double>(hi - lo));
        }
        double mean = 0.0;
        for (double v : x) mean += v;
        mean /= static_cast<double>(frames);
        for (double& v : x) v -= mean;
    }
    const std::size_t maxLag = std::min<std::size_t>(frames / 2, 800);  // up to 8 s (for the comb)
    std::vector<double> ac(maxLag + 1, 0.0);
    for (std::size_t lag = 0; lag <= maxLag; ++lag) {
        double s = 0.0;
        for (std::size_t f = lag; f < frames; ++f) s += x[f] * x[f - lag];
        ac[lag] = s / static_cast<double>(frames - lag);
    }
    if (!(ac[0] > 0.0)) return est;
    auto acAt = [&](double lag) {
        if (lag < 0.0 || lag >= static_cast<double>(maxLag)) return 0.0;
        const auto i = static_cast<std::size_t>(lag);
        const double t = lag - static_cast<double>(i);
        return ac[i] * (1.0 - t) + ac[std::min(maxLag, i + 1)] * t;
    };
    // Comb score: the beat period and its multiples, weighted towards ~120 BPM (log-Gaussian, 1 octave).
    auto score = [&](double bpm) {
        const double lag = 6000.0 / bpm;  // in 10 ms frames
        double s = 0.0, wsum = 0.0;
        for (int m = 1; m <= 4; ++m) {
            if (lag * m >= static_cast<double>(maxLag)) break;
            s += acAt(lag * m) / m;
            wsum += 1.0 / m;
        }
        const double oct = std::log2(bpm / 120.0);
        return wsum > 0 ? s / wsum * std::exp(-0.5 * oct * oct) : 0.0;
    };
    double best = 0.0, bestBpm = 0.0;
    for (double bpm = 60.0; bpm <= 200.0 + 1e-9; bpm += 0.5) {
        const double s = score(bpm);
        if (s > best) { best = s; bestBpm = bpm; }
    }
    if (bestBpm <= 0.0) return est;
    for (double bpm = bestBpm - 0.5; bpm <= bestBpm + 0.5 + 1e-9; bpm += 0.02) {
        const double s = score(bpm);
        if (s > best) { best = s; bestBpm = bpm; }
    }
    est.bpm = std::round(bestBpm * 10.0) / 10.0;
    est.confidence = std::clamp(acAt(6000.0 / bestBpm) / ac[0], 0.0, 1.0);
    return est;
}

// ------------------------------------------------------------------ everything

json measureSignal(const float* L, const float* R, std::size_t len, double sr) {
    json j;
    j["seconds"] = r2(static_cast<double>(len) / sr);
    const Spectrum spec = longTermSpectrum(L, R, len, sr);
    j["spectrum"] = spectrumJson(spec, sr);
    j["stereo"] = stereoJson(spec, sr);
    j["loudness"] = loudnessJson(L, R, len, sr);

    std::vector<float> mono(len);
    for (std::size_t i = 0; i < len; ++i) mono[i] = 0.5f * (L[i] + R[i]);
    const auto hop1 = static_cast<std::size_t>(std::max(1L, std::lround(sr / 1000.0)));  // 1 ms
    const double hopSec = static_cast<double>(hop1) / sr;
    const Biquad64 lp150 = Biquad64::lowPass(sr, 150.0, 0.7071), hp150 = highPass(sr, 150.0, 0.7071);
    const Biquad64 lp4k = Biquad64::lowPass(sr, 4000.0, 0.7071), hp2k = highPass(sr, 2000.0, 0.7071);
    // One filtered band at a time (a 10-minute reference is ~29 M samples per band).
    Onsets lowOn, midOn, highOn;
    std::vector<float> midEnv;
    double lowCrest = 0.0, midCrest = 0.0;
    {
        const std::vector<float> low = filtered(mono, {lp150, lp150});
        lowCrest = crestDb(low);
        // The low band needs a longer envelope (a 40 Hz fundamental ripples the 1 ms energy at 80 Hz).
        lowOn = detectOnsets(envelopeDb(low, hop1, 21), hopSec, 6.0, 0.030, 0.070, 0.080);
    }
    {
        const std::vector<float> mid = filtered(mono, {hp150, hp150, lp4k, lp4k});
        midCrest = crestDb(mid);
        midEnv = envelopeDb(mid, hop1, 5);
        midOn = detectOnsets(midEnv, hopSec, 6.0, 0.005, 0.025, 0.040);
    }
    highOn = detectOnsets(envelopeDb(filtered(mono, {hp2k, hp2k}), hop1, 5), hopSec, 6.0, 0.005, 0.025, 0.040);
    json tr;
    tr["low"] = onsetJson(lowOn);
    tr["mid"] = onsetJson(midOn);
    tr["high"] = onsetJson(highOn);
    tr["crestDb"] = r1(crestDb(mono));
    tr["lowCrestDb"] = r1(lowCrest);
    tr["midCrestDb"] = r1(midCrest);
    tr["note"] = "bands low < 150 Hz (kick/bass), mid 150 Hz-4 kHz (snare, keys, voice), high > 2 kHz (hats, attacks). "
                 "hitDb = median over the active seconds of the biggest rise of the envelope over its lowest level just "
                 "before (5-25 ms; low band 30-70 ms): how far the main hits stick out, bigger = punchier, less compressed; "
                 "attackDb / attackP90Db = the same rise over all onsets (>= 6 dB); perSec = onsets per second of active signal";
    j["transients"] = tr;
    const auto hop10 = static_cast<std::size_t>(std::max(1L, std::lround(sr / 100.0)));
    const std::vector<float> dmid = filtered(mono, {highPass(sr, 400.0, 0.7071), highPass(sr, 400.0, 0.7071), lp4k, lp4k});
    j["decay"] = decayJson(envelopeDb(dmid, hop10, 3), static_cast<double>(hop10) / sr);
    j["sustain"] = sustainJson(midOn, midEnv, hopSec);
    const TempoEstimate t = estimateTempo(L, R, len, sr);
    j["tempo"] = {{"bpm", t.bpm}, {"confidence", r3(t.confidence)}};
    return j;
}

}  // namespace as::analysis
