#include "analysis/Realism.h"

#include "analysis/Fft.h"
#include "analysis/NoteDynamics.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <limits>
#include <numeric>

namespace as::analysis {
namespace {

constexpr double kAttackSec = 0.08;      // repeatSim / layerStep window
constexpr double kRepeatGapSec = 1.0;    // a repeat: the same key again within 1 s
constexpr int kRepeatVel = 6;            // ... at a velocity within +-6
constexpr std::size_t kMaxPairs = 160;   // waveform captures are kept for at most this many repeat pairs
constexpr double kHeldSec = 0.8;         // sustainFlux: notes held this long (no other onset meanwhile)
constexpr double kSustainSkipSec = 0.15; // ... measured from 150 ms after the onset
constexpr double kSustainMaxSec = 6.0;
constexpr std::size_t kMaxHeld = 48;
constexpr double kTailSec = 2.6;         // tailDecay: no new onset for 2.6 s
constexpr std::size_t kMaxTransitions = 96;
constexpr double kTransBefore = 0.06, kTransAfter = 0.3;

double dbPow(double p) { return 10.0 * std::log10(std::max(p, 1e-20)); }

double median(std::vector<double> v) {
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    const std::size_t n = v.size();
    return n % 2 ? v[n / 2] : 0.5 * (v[n / 2 - 1] + v[n / 2]);
}

double r3(double x) { return std::round(x * 1000.0) / 1000.0; }
double r2(double x) { return std::round(x * 100.0) / 100.0; }

double pearson(const std::vector<float>& a, const std::vector<float>& b) {
    const std::size_t n = std::min(a.size(), b.size());
    if (n < 2) return 0.0;
    double ma = 0, mb = 0;
    for (std::size_t i = 0; i < n; ++i) { ma += a[i]; mb += b[i]; }
    ma /= static_cast<double>(n);
    mb /= static_cast<double>(n);
    double sab = 0, saa = 0, sbb = 0;
    for (std::size_t i = 0; i < n; ++i) {
        const double x = a[i] - ma, y = b[i] - mb;
        sab += x * y;
        saa += x * x;
        sbb += y * y;
    }
    if (saa <= 1e-20 || sbb <= 1e-20) return saa <= 1e-20 && sbb <= 1e-20 ? 1.0 : 0.0;
    return sab / std::sqrt(saa * sbb);
}

// Best normalised cross-correlation of two waveforms over lags within +-maxLag samples.
double waveSim(const std::vector<float>& a, const std::vector<float>& b, int maxLag) {
    const int n = static_cast<int>(std::min(a.size(), b.size()));
    double best = -1.0;
    for (int lag = -maxLag; lag <= maxLag; ++lag) {
        const int i0 = std::max(0, -lag), i1 = std::min(n, n - lag);
        double sab = 0, saa = 0, sbb = 0;
        for (int i = i0; i < i1; ++i) {
            const double x = a[static_cast<std::size_t>(i)], y = b[static_cast<std::size_t>(i + lag)];
            sab += x * y;
            saa += x * x;
            sbb += y * y;
        }
        if (saa > 1e-20 && sbb > 1e-20) best = std::max(best, sab / std::sqrt(saa * sbb));
    }
    return best < -0.5 ? 0.0 : best;
}

// Least-squares slope (dB per second) of the envelope's level over [a, b) seconds; false when too short / silent.
bool slopeDb(const OnsetEnvelope& env, double a, double b, double& slope, double& level) {
    const auto& ms = env.meanSquare();
    const double h = env.hopSec();
    const auto i0 = static_cast<std::size_t>(std::max(0.0, std::floor(a / h)));
    const auto i1 = std::min(ms.size(), static_cast<std::size_t>(std::max(0.0, std::floor(b / h))));
    if (i1 <= i0 + 8) return false;
    double st = 0, sy = 0, stt = 0, sty = 0;
    const double n = static_cast<double>(i1 - i0);
    double pw = 0;
    for (std::size_t i = i0; i < i1; ++i) {
        const double t = static_cast<double>(i) * h, y = dbPow(ms[i]);
        st += t;
        sy += y;
        stt += t * t;
        sty += t * y;
        pw += ms[i];
    }
    const double d = n * stt - st * st;
    if (d <= 0) return false;
    slope = (n * sty - st * sy) / d;
    level = dbPow(pw / n);
    return true;
}

}  // namespace

struct RealismProbe::Impl {
    enum Kind { Attack, Held, Transition };
    struct Request {
        std::int64_t start{0};
        int length{0};
        Kind kind{Attack};
        int index{0};          // onset / held note / transition index
        std::vector<float> buf;
        int filled{0};
        bool done{false};
    };

    double sr;
    std::vector<ProbeNote> notes;   // sorted by onset
    // onsets (distinct sample positions) and their attack features
    std::vector<std::int64_t> onsets;
    struct OnsetFeat {
        bool ok{false};
        std::vector<float> env;     // spectro-temporal envelope (dB)
        std::vector<float> wave;    // the raw window (only onsets of a kept repeat pair)
        double levelDb{-200.0}, brightDb{-200.0};
    };
    std::vector<OnsetFeat> feat;
    std::vector<bool> keepWave;
    std::vector<std::pair<int, int>> pairs;      // repeat pairs (onset indices)
    std::vector<int> layerNotes;                 // the sweep key's notes (indices into notes), sorted by velocity
    int layerKey{-1};
    struct HeldNote {
        bool ok{false};
        double rmsSd{0}, centSd{0}, periodicity{0}, periodMs{0};
    };
    std::vector<HeldNote> held;
    struct Trans {
        int from{60}, to{60};
        bool ok{false};
        double dipDb{0}, pitchMs{-1};
    };
    std::vector<Trans> trans;
    std::vector<std::size_t> tailNotes;          // notes ringing 2.6 s+ alone
    std::vector<Request> req;                    // sorted by start
    std::size_t next{0};
    std::vector<std::size_t> active;
    std::int64_t pos{0};
    int frameLen{1024}, attackHop{480}, attackLen{0};
    std::unique_ptr<Fft> fft;
    std::vector<float> window, re, im;
    std::vector<std::pair<int, int>> bands;      // 1/3-octave bands: [lo bin, hi bin)
    int brightBin{0};

    Impl(double sampleRate, std::vector<ProbeNote> ns) : sr(sampleRate), notes(std::move(ns)) {
        std::stable_sort(notes.begin(), notes.end(), [](const ProbeNote& a, const ProbeNote& b) { return a.on < b.on; });
        frameLen = 1;
        while (frameLen < static_cast<int>(0.02 * sr)) frameLen <<= 1;   // >= 20 ms
        attackHop = static_cast<int>(std::lround(0.01 * sr));
        attackLen = static_cast<int>(std::lround(kAttackSec * sr));
        fft = std::make_unique<Fft>(frameLen);
        window = hannWindow(frameLen);
        re.assign(static_cast<std::size_t>(frameLen), 0.0f);
        im.assign(static_cast<std::size_t>(frameLen), 0.0f);
        for (double f = 50.0; f < std::min(16000.0, 0.45 * sr); f *= std::pow(2.0, 1.0 / 3.0)) {
            const int lo = static_cast<int>(std::floor(f * frameLen / sr)), hi = static_cast<int>(std::floor(f * std::pow(2.0, 1.0 / 3.0) * frameLen / sr));
            if (hi > lo) bands.push_back({std::max(1, lo), std::min(frameLen / 2, hi)});
        }
        brightBin = static_cast<int>(std::lround(2500.0 * frameLen / sr));
        plan();
    }

    void plan() {
        const std::size_t nn = notes.size();
        // onsets
        std::vector<int> onsetOf(nn, 0);
        for (std::size_t k = 0; k < nn; ++k) {
            if (onsets.empty() || notes[k].on != onsets.back()) onsets.push_back(notes[k].on);
            onsetOf[k] = static_cast<int>(onsets.size()) - 1;
        }
        feat.assign(onsets.size(), {});
        keepWave.assign(onsets.size(), false);
        // repeat pairs: per note, the previous note of the same key
        std::map<int, std::size_t> last;
        std::vector<std::pair<int, int>> all;
        for (std::size_t k = 0; k < nn; ++k) {
            const auto it = last.find(notes[k].pitch);
            if (it != last.end()) {
                const ProbeNote& p = notes[it->second];
                if (notes[k].on - p.on <= static_cast<std::int64_t>(kRepeatGapSec * sr) && notes[k].on > p.on &&
                    std::abs(notes[k].velocity - p.velocity) <= kRepeatVel) {
                    const std::pair<int, int> pr{onsetOf[it->second], onsetOf[k]};
                    if (all.empty() || all.back() != pr) all.push_back(pr);
                }
            }
            last[notes[k].pitch] = k;
        }
        std::sort(all.begin(), all.end());
        all.erase(std::unique(all.begin(), all.end()), all.end());
        for (std::size_t i = 0; i < all.size(); ++i) {
            if (all.size() > kMaxPairs && (i * kMaxPairs) / all.size() == ((i + 1) * kMaxPairs) / all.size()) continue;
            pairs.push_back(all[i]);
            keepWave[static_cast<std::size_t>(all[i].first)] = keepWave[static_cast<std::size_t>(all[i].second)] = true;
        }
        for (std::size_t o = 0; o < onsets.size(); ++o) add(onsets[o], attackLen, Attack, static_cast<int>(o));
        // the sweep key: the key with the most distinct velocities (8+)
        std::map<int, std::map<int, int>> velsByKey;   // key -> velocity -> note index (the first)
        for (std::size_t k = 0; k < nn; ++k) velsByKey[notes[k].pitch].emplace(notes[k].velocity, static_cast<int>(k));
        std::size_t best = 0;
        for (const auto& [key, vels] : velsByKey) {
            if (vels.size() >= 8 && vels.size() > best) {
                best = vels.size();
                layerKey = key;
                layerNotes.clear();
                for (const auto& [v, k] : vels) layerNotes.push_back(k);
            }
        }
        // held notes, tails and transitions: by the next onset in the track
        std::vector<std::int64_t> nextOn(nn, std::numeric_limits<std::int64_t>::max());
        for (std::size_t k = 0; k < nn; ++k) {
            const auto it = std::upper_bound(onsets.begin(), onsets.end(), notes[k].on);
            if (it != onsets.end()) nextOn[k] = *it;
        }
        std::vector<std::size_t> heldIdx, transIdx;
        for (std::size_t k = 0; k < nn; ++k) {
            const ProbeNote& n = notes[k];
            const bool alone = (k == 0 || notes[k - 1].on != n.on) && (k + 1 == nn || notes[k + 1].on != n.on);
            // held notes and tails: one per onset (a chord counts once, its longest note for the hold)
            const bool firstOfOnset = k == 0 || notes[k - 1].on != n.on;
            if (firstOfOnset) {
                std::int64_t off = n.off;
                for (std::size_t j = k + 1; j < nn && notes[j].on == n.on; ++j) off = std::max(off, notes[j].off);
                if (std::min(off, nextOn[k]) - n.on >= static_cast<std::int64_t>(kHeldSec * sr)) heldIdx.push_back(k);
                if (nextOn[k] - n.on >= static_cast<std::int64_t>(kTailSec * sr)) tailNotes.push_back(k);
            }
            // a legato transition into note k: the previous onset's single note still sounds, no chord at k
            if (alone && k > 0 && (k < 2 || notes[k - 2].on != notes[k - 1].on)) {
                const ProbeNote& p = notes[k - 1];
                if (p.off > n.on + static_cast<std::int64_t>(0.001 * sr) && n.on - p.on >= static_cast<std::int64_t>(0.05 * sr) &&
                    p.pitch != n.pitch && std::abs(p.pitch - n.pitch) % 12 != 0 && n.on >= static_cast<std::int64_t>(kTransBefore * sr))
                    transIdx.push_back(k);
            }
        }
        auto thin = [](std::vector<std::size_t>& v, std::size_t cap) {
            if (v.size() <= cap) return;
            std::vector<std::size_t> out;
            for (std::size_t i = 0; i < cap; ++i) out.push_back(v[i * v.size() / cap]);
            v = out;
        };
        thin(heldIdx, kMaxHeld);
        thin(transIdx, kMaxTransitions);
        for (std::size_t k : heldIdx) {
            const ProbeNote& n = notes[k];
            std::int64_t off = n.off;
            for (std::size_t j = k + 1; j < nn && notes[j].on == n.on; ++j) off = std::max(off, notes[j].off);
            const std::int64_t a = n.on + static_cast<std::int64_t>(kSustainSkipSec * sr);
            const std::int64_t b = std::min({off, nextOn[k], n.on + static_cast<std::int64_t>(kSustainMaxSec * sr)});
            held.push_back({});
            add(a, static_cast<int>(b - a), Held, static_cast<int>(held.size()) - 1);
        }
        for (std::size_t k : transIdx) {
            trans.push_back({notes[k - 1].pitch, notes[k].pitch});
            const std::int64_t a = notes[k].on - static_cast<std::int64_t>(kTransBefore * sr);
            add(a, static_cast<int>(std::lround((kTransBefore + kTransAfter) * sr)), Transition, static_cast<int>(trans.size()) - 1);
        }
        std::stable_sort(req.begin(), req.end(), [](const Request& a, const Request& b) { return a.start < b.start; });
    }

    void add(std::int64_t start, int length, Kind kind, int index) {
        if (length <= 0 || start < 0) return;
        Request r;
        r.start = start;
        r.length = length;
        r.kind = kind;
        r.index = index;
        req.push_back(std::move(r));
    }

    void feed(const float* L, const float* R, int frames) {
        const std::int64_t end = pos + frames;
        while (next < req.size() && req[next].start < end) {
            req[next].buf.assign(static_cast<std::size_t>(req[next].length), 0.0f);
            active.push_back(next++);
        }
        for (std::size_t ai = 0; ai < active.size();) {
            Request& r = req[active[ai]];
            const std::int64_t a = std::max(pos, r.start), b = std::min(end, r.start + r.length);
            for (std::int64_t t = a; t < b; ++t) {
                const auto i = static_cast<std::size_t>(t - pos);
                const float v = 0.5f * (L[i] + R[i]);
                r.buf[static_cast<std::size_t>(t - r.start)] = std::isfinite(v) ? v : 0.0f;
            }
            if (end >= r.start + r.length) {
                complete(r);
                active[ai] = active.back();
                active.pop_back();
            } else {
                ++ai;
            }
        }
        pos = end;
    }

    void finish() {
        for (std::size_t i : active) complete(req[i]);   // cut by the end: zeros after it
        active.clear();
    }

    // Power spectrum of buf[at, at + frameLen) (zero beyond the end), Hann-windowed, into re (bins 0..N/2).
    void spectrum(const std::vector<float>& buf, std::size_t at) {
        for (int i = 0; i < frameLen; ++i) {
            const std::size_t j = at + static_cast<std::size_t>(i);
            re[static_cast<std::size_t>(i)] = j < buf.size() ? buf[j] * window[static_cast<std::size_t>(i)] : 0.0f;
            im[static_cast<std::size_t>(i)] = 0.0f;
        }
        fft->forward(re.data(), im.data());
        for (int k = 0; k <= frameLen / 2; ++k) {
            const float a = re[static_cast<std::size_t>(k)], b = im[static_cast<std::size_t>(k)];
            re[static_cast<std::size_t>(k)] = a * a + b * b;
        }
    }

    void complete(Request& r) {
        if (r.done) return;
        r.done = true;
        if (r.kind == Attack) attack(r);
        else if (r.kind == Held) heldNote(r);
        else transition(r);
        std::vector<float>().swap(r.buf);
    }

    void attack(Request& r) {
        OnsetFeat& f = feat[static_cast<std::size_t>(r.index)];
        const auto& x = r.buf;
        double total = 0, high = 0, pw = 0;
        for (float v : x) pw += static_cast<double>(v) * v;
        f.levelDb = dbPow(pw / std::max<std::size_t>(1, x.size()));
        const int frames = std::max(1, (r.length - frameLen / 2) / attackHop);
        std::vector<float> cells;
        for (int fr = 0; fr < frames && fr < 8; ++fr) {
            spectrum(x, static_cast<std::size_t>(fr * attackHop));
            for (const auto& [lo, hi] : bands) {
                double e = 0;
                for (int k = lo; k < hi; ++k) e += re[static_cast<std::size_t>(k)];
                cells.push_back(static_cast<float>(dbPow(e)));
            }
            for (int k = 1; k < frameLen / 2; ++k) {
                total += re[static_cast<std::size_t>(k)];
                if (k >= brightBin) high += re[static_cast<std::size_t>(k)];
            }
        }
        if (cells.empty() || total <= 1e-18) return;
        const float top = *std::max_element(cells.begin(), cells.end());
        for (float& c : cells) c = std::max(c, top - 60.0f);
        f.env = std::move(cells);
        f.brightDb = dbPow(high / total);
        f.ok = f.levelDb > -90.0;
        if (keepWave[static_cast<std::size_t>(r.index)]) f.wave = x;
    }

    void heldNote(Request& r) {
        HeldNote& h = held[static_cast<std::size_t>(r.index)];
        const auto& x = r.buf;
        const int hop = static_cast<int>(std::lround(0.01 * sr));
        const int nf = static_cast<int>(x.size()) / hop - frameLen / hop;
        if (nf < 40) return;   // under ~0.4 s of frames
        std::vector<double> lv, ce;
        for (int i = 0; i < nf; ++i) {
            const std::size_t a = static_cast<std::size_t>(i * hop);
            double p = 0;
            for (int j = 0; j < hop; ++j) p += static_cast<double>(x[a + j]) * x[a + j];
            lv.push_back(dbPow(p / hop));
            spectrum(x, a);
            double e = 0, ef = 0;
            for (int k = 1; k < frameLen / 2; ++k) {
                e += re[static_cast<std::size_t>(k)];
                ef += re[static_cast<std::size_t>(k)] * k;
            }
            ce.push_back(e > 1e-18 ? 1200.0 * std::log2(std::max(1e-9, ef / e * sr / frameLen) / 440.0) : 0.0);
        }
        if (median(lv) < -90.0) return;
        auto detrend = [](std::vector<double> v) {   // minus a centred 300 ms (30 frame) moving average
            std::vector<double> out(v.size());
            const int w = 15;
            for (std::size_t i = 0; i < v.size(); ++i) {
                const std::size_t a = i >= static_cast<std::size_t>(w) ? i - w : 0, b = std::min(v.size(), i + w + 1);
                double s = 0;
                for (std::size_t j = a; j < b; ++j) s += v[j];
                out[i] = v[i] - s / static_cast<double>(b - a);
            }
            return out;
        };
        auto sd = [](const std::vector<double>& v) {
            double s = 0, ss = 0;
            for (double x : v) { s += x; ss += x * x; }
            const double n = static_cast<double>(v.size());
            return std::sqrt(std::max(0.0, ss / n - (s / n) * (s / n)));
        };
        const auto dl = detrend(lv), dc = detrend(ce);
        h.rmsSd = sd(dl);
        h.centSd = sd(dc);
        auto peak = [&](const std::vector<double>& v, int& lagOut) {
            double e0 = 0;
            for (double x : v) e0 += x * x;
            if (e0 <= 1e-12) return 0.0;
            double best = 0;
            const int maxLag = std::min<int>(100, static_cast<int>(v.size()) / 2);
            for (int lag = 5; lag <= maxLag; ++lag) {
                double s = 0, a = 0, b = 0;
                for (std::size_t i = 0; i + static_cast<std::size_t>(lag) < v.size(); ++i) {
                    s += v[i] * v[i + lag];
                    a += v[i] * v[i];
                    b += v[i + lag] * v[i + lag];
                }
                const double c = a > 0 && b > 0 ? s / std::sqrt(a * b) : 0.0;
                if (c > best) { best = c; lagOut = lag; }
            }
            return best;
        };
        int la = 0, lc = 0;
        const double pa = peak(dl, la), pc = peak(dc, lc);
        h.periodicity = std::max(pa, pc);
        h.periodMs = 10.0 * (pa >= pc ? la : lc);
        h.ok = true;
    }

    void transition(Request& r) {
        Trans& t = trans[static_cast<std::size_t>(r.index)];
        const auto& x = r.buf;
        const int on = static_cast<int>(std::lround(kTransBefore * sr));
        auto rmsDb = [&](int a, int b) {
            double p = 0;
            a = std::max(a, 0);
            b = std::min(b, static_cast<int>(x.size()));
            for (int i = a; i < b; ++i) p += static_cast<double>(x[static_cast<std::size_t>(i)]) * x[static_cast<std::size_t>(i)];
            return dbPow(p / std::max(1, b - a));
        };
        const int ms = static_cast<int>(std::lround(0.001 * sr));
        const double before = rmsDb(on - 50 * ms, on - 10 * ms);
        if (before < -80.0) return;
        double lowest = 1e9;
        for (int a = on - 10 * ms; a + 5 * ms <= on + 150 * ms; a += 5 * ms / 2) lowest = std::min(lowest, rmsDb(a, a + 5 * ms));
        t.dipDb = lowest - before;
        // the new pitch: normalised autocorrelation at the new and the old period
        const double fOld = 440.0 * std::exp2((t.from - 69) / 12.0), fNew = 440.0 * std::exp2((t.to - 69) / 12.0);
        const int pOld = static_cast<int>(std::lround(sr / fOld)), pNew = static_cast<int>(std::lround(sr / fNew));
        const int win = std::max(20 * ms, static_cast<int>(2.5 * std::max(pOld, pNew)));
        auto nacf = [&](int a, int lag) {
            double s = 0, e1 = 0, e2 = 0;
            for (int i = a; i < a + win && i + lag < static_cast<int>(x.size()); ++i) {
                const double u = x[static_cast<std::size_t>(i)], v = x[static_cast<std::size_t>(i + lag)];
                s += u * v;
                e1 += u * u;
                e2 += v * v;
            }
            return e1 > 1e-18 && e2 > 1e-18 ? s / std::sqrt(e1 * e2) : 0.0;
        };
        t.pitchMs = -1.0;
        for (int a = on; a + win + std::max(pOld, pNew) < static_cast<int>(x.size()); a += 5 * ms) {
            const double cNew = nacf(a, pNew), cOld = nacf(a, pOld);
            if (cNew > 0.5 && cNew > cOld + 0.05) {
                t.pitchMs = (a - on) / (0.001 * sr);
                break;
            }
        }
        t.ok = true;
    }

    json report(const OnsetEnvelope* env) const {
        json out = json::object();
        // repeatSim
        std::vector<double> sims, waves;
        for (const auto& [a, b] : pairs) {
            const OnsetFeat& fa = feat[static_cast<std::size_t>(a)];
            const OnsetFeat& fb = feat[static_cast<std::size_t>(b)];
            if (!fa.ok || !fb.ok) continue;
            sims.push_back(pearson(fa.env, fb.env));
            if (!fa.wave.empty() && !fb.wave.empty()) waves.push_back(waveSim(fa.wave, fb.wave, static_cast<int>(std::lround(0.001 * sr))));
        }
        if (!sims.empty()) {
            json j = {{"pairs", sims.size()}, {"sim", r3(median(sims))}};
            if (!waves.empty()) j["wave"] = r3(median(waves));
            out["repeatSim"] = j;
        }
        // layerStep
        if (layerKey >= 0) {
            std::vector<double> lsteps, bsteps;
            const OnsetFeat* prev = nullptr;
            for (int k : layerNotes) {
                const auto it = std::lower_bound(onsets.begin(), onsets.end(), notes[static_cast<std::size_t>(k)].on);
                const OnsetFeat& f = feat[static_cast<std::size_t>(it - onsets.begin())];
                if (!f.ok) continue;
                if (prev) {
                    lsteps.push_back(std::fabs(f.levelDb - prev->levelDb));
                    bsteps.push_back(std::fabs(f.brightDb - prev->brightDb));
                }
                prev = &f;
            }
            if (lsteps.size() >= 6) {
                out["layerStep"] = {{"key", layerKey}, {"notes", lsteps.size() + 1},
                                    {"maxLevelDb", r2(*std::max_element(lsteps.begin(), lsteps.end()))}, {"medianLevelDb", r2(median(lsteps))},
                                    {"maxBrightDb", r2(*std::max_element(bsteps.begin(), bsteps.end()))}, {"medianBrightDb", r2(median(bsteps))}};
            }
        }
        // sustainFlux
        std::vector<double> rs, cs, ps, pm;
        for (const HeldNote& h : held) {
            if (!h.ok) continue;
            rs.push_back(h.rmsSd);
            cs.push_back(h.centSd);
            ps.push_back(h.periodicity);
            pm.push_back(h.periodMs);
        }
        if (!rs.empty()) {
            out["sustainFlux"] = {{"notes", rs.size()}, {"rmsSdDb", r3(median(rs))}, {"centroidSdCents", r2(median(cs))},
                                  {"periodicity", r3(median(ps))}, {"periodMs", r2(median(pm))}};
        }
        // tailDecay
        if (env) {
            std::vector<double> s1, s2;
            for (std::size_t k : tailNotes) {
                const double t0 = static_cast<double>(notes[k].on) / sr + 0.1;
                double a = 0, b = 0, la = 0, lb = 0;
                if (!slopeDb(*env, t0, t0 + 0.5, a, la) || !slopeDb(*env, t0 + 0.5, t0 + 2.5, b, lb)) continue;
                if (la < -70.0 || lb < -110.0) continue;
                s1.push_back(-a);
                s2.push_back(-b);
            }
            if (!s1.empty()) out["tailDecay"] = {{"notes", s1.size()}, {"firstDbPerSec", r2(median(s1))}, {"laterDbPerSec", r2(median(s2))}};
        }
        // transitionDip
        std::vector<double> dips, pms;
        for (const Trans& t : trans) {
            if (!t.ok) continue;
            dips.push_back(t.dipDb);
            if (t.pitchMs >= 0) pms.push_back(t.pitchMs);
        }
        if (!dips.empty()) {
            json j = {{"transitions", dips.size()}, {"dipDb", r2(median(dips))}};
            if (!pms.empty()) j["pitchMs"] = r2(median(pms));
            out["transitionDip"] = j;
        }
        return out;
    }
};

RealismProbe::RealismProbe(double sampleRate, std::vector<ProbeNote> notes)
    : impl_(std::make_unique<Impl>(sampleRate, std::move(notes))) {}
RealismProbe::~RealismProbe() = default;
void RealismProbe::feed(const float* left, const float* right, int frames) { impl_->feed(left, right, frames); }
void RealismProbe::finish() { impl_->finish(); }
json RealismProbe::report(const OnsetEnvelope* env) const { return impl_->report(env); }

}  // namespace as::analysis
