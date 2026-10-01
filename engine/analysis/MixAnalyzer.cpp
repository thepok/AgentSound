#include "analysis/MixAnalyzer.h"

#include "analysis/Aggregate.h"
#include "analysis/Loudness.h"
#include "analysis/MixImpl.h"
#include "analysis/SilentNotes.h"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <filesystem>
#include <optional>
#include <set>
#include <stdexcept>
#include <tuple>

namespace as {

namespace analysis {

std::string MixImpl::barBeat(double sec) const {
    return meter.label(beatAt(sec));  // "bar 16 beat 1.00" (the beat rounded as displayed first); 4/4 by default
}

// Typical long-term spectrum of modern pop / synthwave masters, in dB per Hz: -4.5 dB/oct between
// 100 Hz and 8 kHz (the slope analyser "tilt" presets use to make commercial mixes look flat),
// flat 40-100 Hz (kick and bass fundamentals), rolling off below 40 Hz and steeper above 8 kHz.
double referencePsdDb(double f) noexcept {
    const double at100 = 4.5 * std::log2(10.0);
    if (f >= 8000.0) return -4.5 * 3.0 - 7.5 * std::log2(f / 8000.0);
    if (f >= 100.0) return -4.5 * std::log2(f / 1000.0);
    if (f >= 40.0) return at100;
    return at100 - 12.0 * std::log2(40.0 / std::max(f, 1.0));
}

std::array<double, kNumBands> referenceBandShares() { return defaultAnalysisProfile().bandShares(); }

bool balanceVsReference(const double* e, const std::array<double, kNumBands>& ref, double* out) noexcept {
    double total = 0.0;
    for (int b = 0; b < kNumBands; ++b) total += std::max(0.0, e[b]);
    std::array<double, kNumBands> dev{};
    for (int b = 0; b < kNumBands; ++b) {
        const double share = total > 0.0 ? std::max(0.0, e[b]) / total : 0.0;
        dev[static_cast<std::size_t>(b)] = share > 1e-9 ? 10.0 * std::log10(share / ref[static_cast<std::size_t>(b)]) : -90.0;
    }
    std::array<double, kNumBands> sorted = dev;
    std::nth_element(sorted.begin(), sorted.begin() + kNumBands / 2, sorted.end());
    const double median = sorted[kNumBands / 2];
    for (int b = 0; b < kNumBands; ++b)
        out[b] = total > 0.0 ? std::clamp(dev[static_cast<std::size_t>(b)] - median, -60.0, 60.0) : 0.0;
    return total > 0.0;
}

}  // namespace analysis

namespace {

using namespace analysis;

constexpr std::int64_t kEndOfStream = INT64_MAX / 4;

// ------------------------------------------------------------------ small helpers

// Rounding for the report (+ 0.0 turns -0.0 into 0.0).
double r1(double x) { return std::isfinite(x) ? std::round(x * 10.0) / 10.0 + 0.0 : kDbFloor; }
double r2(double x) { return std::isfinite(x) ? std::round(x * 100.0) / 100.0 + 0.0 : 0.0; }
double r3(double x) { return std::isfinite(x) ? std::round(x * 1000.0) / 1000.0 + 0.0 : 0.0; }
int ri(double x) { return std::isfinite(x) ? static_cast<int>(std::lround(x)) : static_cast<int>(kDbFloor); }

std::string fmt(const char* f, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, f);
    std::vsnprintf(buf, sizeof buf, f, ap);
    va_end(ap);
    return buf;
}

std::string fmtTime(double sec) {
    if (!(sec > 0.0)) sec = 0.0;
    const int m = static_cast<int>(sec / 60.0);
    return fmt("%d:%04.1f", m, sec - 60.0 * m);
}

std::string fmtTimeMs(double sec) {
    const auto ms = static_cast<long long>(std::llround(std::max(0.0, sec) * 1000.0));
    return fmt("%lld:%02lld.%03lld", ms / 60000, (ms / 1000) % 60, ms % 1000);
}

std::string quoteList(const std::vector<std::string>& v) {
    std::string s;
    for (std::size_t i = 0; i < v.size(); ++i) s += (i ? ", '" : "'") + v[i] + "'";
    return s;
}

// BS.1770 gated loudness over the full ticks inside [t0, t1) from per-tick K energies.
double gatedLufs(const std::vector<double>& kTick, double tickLen, std::int64_t frames, double sr, double t0, double t1,
                 double fallback) {
    const std::int64_t fullTicks = frames / static_cast<std::int64_t>(tickLen);
    const auto i0 = static_cast<std::int64_t>(std::ceil(t0 * sr / tickLen - 1e-9));
    const auto i1 = std::min<std::int64_t>({fullTicks, static_cast<std::int64_t>(std::floor(t1 * sr / tickLen + 1e-9)),
                                            static_cast<std::int64_t>(kTick.size())});
    if (i1 - i0 < 4) return fallback;
    std::vector<double> blocks;
    blocks.reserve(static_cast<std::size_t>(i1 - i0));
    for (std::int64_t j = i0; j + 4 <= i1; ++j) {
        const auto u = static_cast<std::size_t>(j);
        blocks.push_back((kTick[u] + kTick[u + 1] + kTick[u + 2] + kTick[u + 3]) / (4.0 * tickLen));
    }
    return integratedLoudness(blocks);
}

// How much two nodes' energy in one band coincides in time (1 = identical envelopes, ~0 = they alternate).
double coincidence(const StreamStats& a, const StreamStats& b, int band, double sr, double t0, double t1) {
    const double T = a.tickLen();
    const auto i0 = static_cast<std::size_t>(std::max(0.0, t0 * sr / T));
    const auto i1 = std::min({a.ticks().size(), b.ticks().size(), static_cast<std::size_t>(std::ceil(t1 * sr / T))});
    double num = 0.0, sa = 0.0, sb = 0.0;
    for (std::size_t i = i0; i < i1; ++i) {
        const double ea = a.ticks()[i].band[band], eb = b.ticks()[i].band[band];
        num += std::sqrt(ea * eb);
        sa += ea;
        sb += eb;
    }
    return (sa > 0 && sb > 0) ? num / std::sqrt(sa * sb) : 0.0;
}

// How strongly two parts' low-end (< 150 Hz) energy avoids each other, in dB: ~0 = independent or hitting together
// (a kick over an unducked sustained bass, a bass that plays only with the kick), 3-10 = one ducks while the other hits
// (a working sidechain), < 0 = the sustained one is louder on the hits than between them.
// How far the sustained part steps aside while the transient one hits (dB, 10 ms low-band envelopes of the two
// nodes' own outputs): the hits = the frames where the more transient node (higher p90 / median of its envelope: the
// kick) is in its top 10 %; the other node's mean energy there vs between the hits (where the kick sits below its
// median). A bass ducked 9 dB under each kick reads ~+9 dB, a bass that sounds only with the kick (no duck) ~0 or
// below, a bass in the kick's gaps strongly positive. (The earlier measure, the envelopes' normalised product, could
// not exceed ~1.5 dB for a sustained bass however deep its duck - the kick's own tail and ring dominate it - so the
// warning came and went with small bass edits.)
double lowSeparationDb(const StreamStats& a, const StreamStats& b, double sr, double t0, double t1) {
    const auto& ea0 = a.lowEnvelope();
    const auto& eb0 = b.lowEnvelope();
    const double F = a.envFrames();
    const auto i0 = static_cast<std::size_t>(std::max(0.0, std::ceil(t0 * sr / F)));
    const auto i1 = std::min({ea0.size(), eb0.size(), static_cast<std::size_t>(std::max(0.0, std::floor(t1 * sr / F)))});
    if (i1 <= i0 + 20) return 0.0;
    auto pct = [&](const std::vector<float>& e, double q) {
        std::vector<float> v(e.begin() + static_cast<std::ptrdiff_t>(i0), e.begin() + static_cast<std::ptrdiff_t>(i1));
        const std::size_t k = std::min(v.size() - 1, static_cast<std::size_t>(q * static_cast<double>(v.size())));
        std::nth_element(v.begin(), v.begin() + static_cast<std::ptrdiff_t>(k), v.end());
        return static_cast<double>(v[k]);
    };
    const double a50 = pct(ea0, 0.5), a90 = pct(ea0, 0.9), b50 = pct(eb0, 0.5), b90 = pct(eb0, 0.9);
    const bool aHits = a90 / std::max(a50, 1e-20) >= b90 / std::max(b50, 1e-20);
    const auto& ek = aHits ? ea0 : eb0;    // the transient one (the kick)
    const auto& es = aHits ? eb0 : ea0;    // the sustained one (the bass)
    const double k50 = aHits ? a50 : b50, k90 = aHits ? a90 : b90;
    if (!(k90 > 0.0)) return 0.0;
    double sHit = 0.0, sGap = 0.0;
    std::size_t nHit = 0, nGap = 0;
    for (std::size_t i = i0; i < i1; ++i) {
        if (ek[i] >= k90) {
            sHit += es[i];
            ++nHit;
        } else if (ek[i] < k50) {
            sGap += es[i];
            ++nGap;
        }
    }
    if (nHit == 0 || nGap == 0 || !(sGap > 0.0)) return 0.0;
    const double hit = sHit / static_cast<double>(nHit), gap = sGap / static_cast<double>(nGap);
    return std::clamp(10.0 * std::log10(std::max(gap, 1e-30) / std::max(hit, 1e-30)), -30.0, 30.0);
}

json bandObject(const double* values) {
    json o = json::object();
    for (int b = 0; b < kNumBands; ++b) o[kBandNames[b]] = r1(values[b]);
    return o;
}

bool looksLikeKick(const std::string& id) {
    for (const char* k : {"kick", "bd", "808", "drum"})
        if (id.find(k) != std::string::npos) return true;
    return false;
}

// Order of warnings with the same severity: what an agent should fix first.
int warningRank(const std::string& code) {
    static const char* kOrder[] = {"no_audio", "non_finite", "clipping", "clicks", "silent_notes", "true_peak", "loudness", "phase", "low_end_not_mono",
                                   "dry_mix", "washy", "narrow_mix", "over_wide", "thin_bed", "masking", "flat_dynamics", "reverb_inaudible", "balance_",
                                   "subsonic", "inaudible", "silent_section", "section_out_of_range", "lr_balance", "dc_offset", "dull",
                                   "tilt", "squashed", "mono", "very_wide", "lra_", "level_jump", "silent_node", "node_hot"};
    for (std::size_t i = 0; i < std::size(kOrder); ++i)
        if (code.rfind(kOrder[i], 0) == 0) return static_cast<int>(i);
    return static_cast<int>(std::size(kOrder));
}

// ------------------------------------------------------------------ clicks

constexpr std::size_t kMaxClicksReported = 40;
constexpr std::size_t kMaxClickImages = 8;

std::string channelName(int bits) { return bits == 1 ? "L" : bits == 2 ? "R" : "both"; }

// Runs the mix detector over the stored mix, then attributes every mix click to the node(s) whose
// own detector fired within +-1.5 ms (tracks before buses, then the biggest jump). Node clicks
// without a mix counterpart are kept as "masked" (audible in the part, hidden in the mix).
void analyseClicks(MixImpl& m) {
    const double sr = m.sampleRate;
    m.mixClicks = std::make_unique<ClickDetector>(sr);
    constexpr std::size_t kChunk = 8192;
    for (std::size_t i = 0; i < m.mixL.size(); i += kChunk) {
        const int n = static_cast<int>(std::min(kChunk, m.mixL.size() - i));
        m.mixClicks->feed(m.mixL.data() + i, m.mixR.data() + i, n);
    }
    m.mixClicks->finish();
    for (auto& n : m.nodes) n.clicks->finish();

    const std::int64_t tol = std::max<std::int64_t>(2, std::llround(0.0015 * sr));
    std::vector<std::vector<char>> used(m.nodes.size());
    for (std::size_t n = 0; n < m.nodes.size(); ++n) used[n].assign(m.nodes[n].clicks->events().size(), 0);
    auto gather = [&](std::int64_t s, ClickInfo& ci) {
        for (std::size_t n = 0; n < m.nodes.size(); ++n) {
            const auto& ev = m.nodes[n].clicks->events();
            auto it = std::lower_bound(ev.begin(), ev.end(), s - tol, [](const ClickEvent& e, std::int64_t v) { return e.sample < v; });
            for (; it != ev.end() && it->sample <= s + tol; ++it) {
                const auto k = static_cast<std::size_t>(it - ev.begin());
                if (used[n][k]) continue;
                used[n][k] = 1;
                const int ni = static_cast<int>(n);
                if (std::find(ci.nodes.begin(), ci.nodes.end(), ni) == ci.nodes.end()) ci.nodes.push_back(ni);
                const bool better = ci.node < 0 || (!m.nodes[n].isBus && m.nodes[static_cast<std::size_t>(ci.node)].isBus) ||
                                    (m.nodes[n].isBus == m.nodes[static_cast<std::size_t>(ci.node)].isBus && it->jump > ci.nodeEvent->jump);
                if (better) {
                    ci.node = ni;
                    ci.nodeEvent = &*it;
                }
            }
        }
    };
    std::vector<ClickInfo> list;
    for (const auto& e : m.mixClicks->events()) {
        ClickInfo ci;
        ci.sample = e.sample;
        ci.jumpDb = e.jumpDb();
        ci.contrastDb = e.contrastDb();
        ci.channels = e.channels;
        gather(e.sample, ci);
        if (ci.nodes.empty()) {
            // In no single part a click, but in one of them the attack of a sound (e.g. a kick's click
            // transient whose body barely rises above a dense mix): a musical transient, not a defect.
            bool onset = false;
            for (const auto& n : m.nodes) onset = onset || n.clicks->onsetNear(e.sample, tol);
            if (onset) continue;
        }
        list.push_back(std::move(ci));
    }
    for (std::size_t n = 0; n < m.nodes.size(); ++n) {
        const auto& ev = m.nodes[n].clicks->events();
        for (std::size_t k = 0; k < ev.size(); ++k) {
            if (used[n][k]) continue;
            ClickInfo ci;
            ci.inMix = false;
            gather(ev[k].sample, ci);  // groups the coincident events of other nodes (e.g. a bus fed by this track)
            ci.sample = ci.nodeEvent->sample;
            ci.jumpDb = ci.nodeEvent->jumpDb();
            ci.contrastDb = ci.nodeEvent->contrastDb();
            ci.channels = ci.nodeEvent->channels;
            list.push_back(std::move(ci));
        }
    }
    for (auto& ci : list) {
        ci.sec = static_cast<double>(ci.sample) / sr;
        ci.severity = !ci.inMix ? 2 : ci.jumpDb >= -30.0 ? 0 : 1;
    }
    std::stable_sort(list.begin(), list.end(), [](const ClickInfo& a, const ClickInfo& b) {
        if (a.severity != b.severity) return a.severity < b.severity;
        if (a.jumpDb != b.jumpDb) return a.jumpDb > b.jumpDb;
        return a.sample < b.sample;
    });
    m.clicksInMix = m.clicksMasked = 0;
    for (const auto& ci : list) (ci.inMix ? m.clicksInMix : m.clicksMasked)++;
    if (list.size() > kMaxClicksReported) list.resize(kMaxClicksReported);
    for (std::size_t i = 0; i < list.size() && i < kMaxClickImages; ++i) list[i].image = fmt("clicks/click_%02d.png", static_cast<int>(i) + 1);
    m.clicks = std::move(list);
}

// ------------------------------------------------------------------ image plan

std::string fileSafe(const std::string& s) {
    std::string out;
    for (char ch : s) {
        const bool ok = (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '-' || ch == '_';
        if (ok) out += ch;
        else if (!out.empty() && out.back() != '_') out += '_';
    }
    while (!out.empty() && out.back() == '_') out.pop_back();
    if (out.size() > 40) out.resize(40);
    return out.empty() ? std::string("section") : out;
}

void planImages(MixImpl& m) {
    m.zooms.clear();
    m.images.clear();
    const bool implicitOnly = m.sections.size() == 1 && m.sections[0].implicit;
    if (implicitOnly) {  // no sections: 16-bar chunks
        const double firstBar = std::floor(m.barAt(m.startBeat) + 1e-9);
        const double lastBar = std::max(firstBar + 1.0, std::ceil(m.barAt(m.beatAt(m.durationSec)) - 1e-9));
        for (double b = firstBar, e = firstBar; b < lastBar; b = e) {
            e = std::min(lastBar, b + 16.0);
            if (lastBar - e < 4.0) e = lastBar;  // a short remainder (often just the tail) joins this chunk
            ZoomSpan z;
            z.name = e - b <= 1.0 ? fmt("bar %d", static_cast<int>(b) + 1) : fmt("bars %d-%d", static_cast<int>(b) + 1, static_cast<int>(e));
            z.startSec = std::max(0.0, m.secAtBeat(m.barStartBeat(b)));
            z.endSec = std::min(m.durationSec, m.secAtBeat(m.barStartBeat(e)));
            if (z.endSec - z.startSec > 0.05) m.zooms.push_back(z);
        }
    } else {
        for (const auto& s : m.sections) {
            const double a = std::max(0.0, s.startSec), b = std::min(m.durationSec, s.endSec);
            if (b - a > 0.05) m.zooms.push_back({s.name, "", a, b});
        }
    }
    for (std::size_t i = 0; i < m.zooms.size(); ++i)
        m.zooms[i].file = fmt("spectrogram_%02d_%s.png", static_cast<int>(i) + 1, fileSafe(m.zooms[i].name).c_str());

    m.images.push_back({"overview.png", "dashboard + index: loudness, SPACE verdict per section (dry/narrow/ok/lush/washy), level of every "
                                        "track/bus, clicks, top issues, list of images"});
    m.images.push_back({"loudness.png", "waveform L/R (peak, RMS, clipping) + momentary/short-term LUFS vs target, section table"});
    m.images.push_back({"tracks.png", "one lane per track/bus: level over time, dominant band, section RMS (dBFS) written in"});
    m.images.push_back({"bands.png", "7-band share over time vs the reference split + band balance vs reference per section"});
    m.images.push_back({"stereo.png", "correlation, width (whole mix / above 150 Hz vs target), wetness (reverb + echo returns vs the "
                                      "mix, tails), SPACE strip, low-end mono check, L/R balance over time + stereo field with roles"});
    m.images.push_back({"spectrogram.png", "whole song, 25 Hz-20 kHz, fixed -100..-20 dB colour scale (comparable between renders)"});
    for (const auto& z : m.zooms) {
        const double b0 = 1.0 + m.barAt(m.beatAt(z.startSec)), b1 = 1.0 + m.barAt(m.beatAt(z.endSec));
        const std::string what = implicitOnly ? z.name
                                              : fmt("'%s' (bars %.0f-%.0f)", z.name.c_str(), std::floor(b0 + 1e-6),
                                                    std::max(std::floor(b0 + 1e-6), std::ceil(b1 - 1e-6) - 1.0));
        m.images.push_back({z.file, fmt("zoom of %s: ~20 ms spectrogram, beat grid, level strip: hats, transients, tails, pumping",
                                        what.c_str())});
    }
    for (std::size_t i = 0; i < m.clicks.size(); ++i) {
        const ClickInfo& k = m.clicks[i];
        if (k.image.empty()) continue;
        const std::string who = k.node >= 0 ? "'" + m.nodes[static_cast<std::size_t>(k.node)].id + "'" : std::string("master");
        const bool snip = k.nodeEvent && !k.nodeEvent->snipL.empty();
        m.images.push_back({k.image, fmt("click #%d at %s (%s) in %s%s: +-15 ms of the mix%s, every sample, spectrum strip",
                                         static_cast<int>(i) + 1, fmtTimeMs(k.sec).c_str(), m.barBeat(k.sec).c_str(), who.c_str(),
                                         k.inMix ? "" : " (masked in the mix)", snip ? (" and of " + who).c_str() : "")});
    }
}

// ------------------------------------------------------------------ report builder

class ReportBuilder {
public:
    explicit ReportBuilder(MixImpl& m) : m_(m), sr_(m.sampleRate) {}
    json build();

private:
    struct Warning {
        int severity;  // 0 error, 1 warn, 2 info
        std::string code, message;
        std::vector<std::string> sections, nodes;
    };

    void warn(int sev, std::string code, std::string msg, std::vector<std::string> sections = {},
              std::vector<std::string> nodes = {}) {
        warnings_.push_back({sev, std::move(code), std::move(msg), std::move(sections), std::move(nodes)});
    }
    void suggest(const std::string& s) {
        if (seenSuggestions_.insert(s).second) suggestions_.push_back(s);
    }
    std::int64_t secSample(double sec) const { return std::llround(sec * sr_); }
    std::int64_t barSample(double bar) const { return m_.barGrid().barStartSample(bar); }
    double firstBar() const { return std::floor(m_.barAt(m_.startBeat) + 1e-9); }
    double endBar() const { return std::ceil(m_.barAt(m_.beatAt(m_.durationSec)) - 1e-9); }
    // Tempo range over the beats [b0, b1) (the map's extremes lie on its points or the ends).
    std::pair<double, double> bpmRange(double b0, double b1) const {
        const double a = m_.tempo.bpmAt(b0), b = m_.tempo.bpmAt(std::max(b0, b1 - 1e-9));  // (a step at b1 is the next span's)
        double lo = std::min(a, b), hi = std::max(a, b);
        for (const TempoPoint& p : m_.tempo.points()) {
            if (p.beat <= b0 || p.beat >= b1) continue;
            for (double v : {p.bpm, m_.tempo.bpmAt(p.beat - 1e-9)}) {
                lo = std::min(lo, v);
                hi = std::max(hi, v);
            }
        }
        return {lo, hi};
    }

    void measureMix();
    json globalJson();
    void buildSections();
    json sectionsJson();
    json nodesJson();
    void checkMasking();
    void checkBalance();
    void checkSectionsAndStereo();
    json timelineJson();
    json clicksJson();
    void checkClicks();
    std::string topContributors(int band, std::size_t count) const;

    MixImpl& m_;
    double sr_;
    std::vector<Warning> warnings_;
    std::vector<std::string> suggestions_;
    std::set<std::string> seenSuggestions_;

    // intermediate results
    Agg mixAgg_;
    double stMax_{kDbFloor}, mMax_{kDbFloor}, dcL_{0}, dcR_{0}, firstClipSec_{-1};
    std::int64_t clipped_{0}, nonFinite_{0};
    std::array<double, kNumBands> vsRef_{};
    double tilt_{0}, refTilt_{0};
    std::vector<double> thirdHz_, thirdVsRef_;
    std::vector<double> segK_;                   // exact K-weighted energy per mix segment
    std::vector<Agg> mixSec_;                    // [section]
    std::vector<std::vector<Agg>> nodeSec_;      // [node][section]
    std::vector<std::array<double, kNumBands>> trackBandSum_;  // [section]: summed track band energy
    std::array<double, kNumBands> trackBandTotal_{};           // whole song
    std::vector<Agg> nodeAll_;                   // [node] whole song
};

void ReportBuilder::measureMix() {
    const auto n = m_.mixL.size();
    const auto T = static_cast<std::size_t>(m_.tickLen);
    const std::size_t numTicks = m_.mix->ticks().size();
    const auto& segs = m_.mix->segments();

    // Exact BS.1770 K-weighted energy per tick and per segment (time domain, double precision).
    m_.kTick.assign(numTicks, 0.0);
    segK_.assign(segs.size(), 0.0);
    KWeighting kl(sr_), kr(sr_);
    std::size_t seg = 0;
    for (std::size_t t = 0; t < numTicks; ++t) {
        double acc = 0.0;
        const std::size_t end = std::min(n, (t + 1) * T);
        for (std::size_t i = t * T; i < end; ++i) {
            const double yl = kl.process(m_.mixL[i]), yr = kr.process(m_.mixR[i]);
            const double e = yl * yl + yr * yr;
            acc += e;
            while (seg + 1 < segs.size() && static_cast<std::int64_t>(i) >= segs[seg + 1].start) ++seg;
            segK_[seg] += e;
        }
        m_.kTick[t] = acc;
    }
    const double Td = static_cast<double>(T);
    m_.momentary.assign(numTicks, static_cast<float>(kDbFloor));
    m_.shortTerm.assign(numTicks, static_cast<float>(kDbFloor));
    const std::size_t fullTicks = n / T;
    std::vector<double> blocks, shortBlocks;
    for (std::size_t t = 0; t < numTicks; ++t) {
        double s4 = 0.0, s30 = 0.0;
        for (std::size_t j = 0; j < 30 && j <= t; ++j) {
            if (j < 4) s4 += m_.kTick[t - j];
            s30 += m_.kTick[t - j];
        }
        m_.momentary[t] = static_cast<float>(lufsFromMeanSquare(s4 / (4.0 * Td)));
        m_.shortTerm[t] = static_cast<float>(lufsFromMeanSquare(s30 / (30.0 * Td)));
        if (t >= 3 && t < fullTicks) blocks.push_back(s4 / (4.0 * Td));
        if (t >= 29 && t < fullTicks) shortBlocks.push_back(s30 / (30.0 * Td));
        if (t >= std::min<std::size_t>(3, numTicks - 1)) mMax_ = std::max(mMax_, static_cast<double>(m_.momentary[t]));
        if (t >= std::min<std::size_t>(29, numTicks - 1)) stMax_ = std::max(stMax_, static_cast<double>(m_.shortTerm[t]));
    }
    if (!blocks.empty()) {
        m_.lufsI = integratedLoudness(blocks);
    } else if (n > 0) {  // shorter than one 400 ms block: ungated
        double sum = 0.0;
        for (double k : m_.kTick) sum += k;
        m_.lufsI = lufsFromMeanSquare(sum / static_cast<double>(n));
    }
    m_.lra = loudnessRange(shortBlocks);

    // Peaks, clipping, DC.
    double peak = 0.0, sumL = 0.0, sumR = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        const float l = m_.mixL[i], r = m_.mixR[i];
        const float a = std::max(std::fabs(l), std::fabs(r));
        if (a >= 1.0f) {
            clipped_ += (std::fabs(l) >= 1.0f) + (std::fabs(r) >= 1.0f);
            if (firstClipSec_ < 0) firstClipSec_ = static_cast<double>(i) / sr_;
        }
        peak = std::max(peak, static_cast<double>(a));
        sumL += l;
        sumR += r;
    }
    if (n) { dcL_ = sumL / static_cast<double>(n); dcR_ = sumR / static_cast<double>(n); }
    m_.samplePeakDb = dbFromAmplitude(peak);
    const TruePeak tp;
    m_.truePeakDb = dbFromAmplitude(std::max(tp.measure(m_.mixL.data(), n), tp.measure(m_.mixR.data(), n)));

    mixAgg_ = aggregate(*m_.mix, 0, kEndOfStream);

    // Band balance against the reference.
    balanceVsReference(mixAgg_.band, m_.refShare, vsRef_.data());

    // Third-octave long-term spectrum vs reference, and the spectral tilt (dB/oct of the PSD).
    const auto& spec = m_.mix->spectrum();
    const double df = sr_ / m_.setup->n;
    auto energyIn = [&](double f0, double f1) {
        double e = 0.0;
        const int k0 = std::max(0, static_cast<int>(std::floor(f0 / df + 0.5)));
        const int k1 = std::min(static_cast<int>(spec.size()) - 1, static_cast<int>(std::floor(f1 / df + 0.5)));
        for (int k = k0; k <= k1; ++k) {
            const double lo = (k - 0.5) * df, hi = (k + 0.5) * df;
            const double ov = std::min(hi, f1) - std::max(lo, f0);
            if (ov > 0) e += spec[static_cast<std::size_t>(k)] * ov / df;
        }
        return e;
    };
    static constexpr double kNominal[] = {25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
                                          800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000,
                                          10000, 12500, 16000, 20000};
    std::vector<double> dev, psd, refPsd, lx;
    for (int i = 0; i < 30; ++i) {
        const double fc = 1000.0 * std::exp2((i - 16) / 3.0);
        const double f0 = fc * std::exp2(-1.0 / 6.0), f1 = std::min(fc * std::exp2(1.0 / 6.0), sr_ * 0.5);
        if (f1 <= f0) break;
        const double e = energyIn(f0, f1), re = m_.profile->energy(f0, f1);
        thirdHz_.push_back(kNominal[i]);
        dev.push_back(e > 0 ? 10.0 * std::log10(e / re) : -99.0);
        if (fc >= 100.0 && fc <= 10000.0) {
            lx.push_back(std::log2(fc));
            psd.push_back(e > 0 ? 10.0 * std::log10(e / (f1 - f0)) : -200.0);
            refPsd.push_back(10.0 * std::log10(re / (f1 - f0)));
        }
    }
    double meanDev = 0.0;
    int cnt = 0;
    for (std::size_t i = 0; i < dev.size(); ++i)
        if (thirdHz_[i] >= 40 && thirdHz_[i] <= 16000 && dev[i] > -99.0) { meanDev += dev[i]; ++cnt; }
    meanDev = cnt ? meanDev / cnt : 0.0;
    for (double d : dev) thirdVsRef_.push_back(d > -99.0 ? d - meanDev : -99.0);
    auto slope = [&](const std::vector<double>& y) {
        const double nn = static_cast<double>(lx.size());
        if (nn < 2) return 0.0;
        double sx = 0, sy = 0, sxx = 0, sxy = 0;
        for (std::size_t i = 0; i < lx.size(); ++i) { sx += lx[i]; sy += y[i]; sxx += lx[i] * lx[i]; sxy += lx[i] * y[i]; }
        const double den = nn * sxx - sx * sx;
        return den != 0 ? (nn * sxy - sx * sy) / den : 0.0;
    };
    tilt_ = mixAgg_.bandSum() > 0 ? slope(psd) : 0.0;
    refTilt_ = slope(refPsd);
}

json ReportBuilder::globalJson() {
    json g;
    g["durationSec"] = r2(m_.durationSec);
    g["sampleRate"] = static_cast<int>(std::lround(sr_));
    g["bpm"] = m_.bpm;
    if (m_.mapped || m_.metered) {
        g["bars"] = r2(m_.barAt(m_.beatAt(m_.durationSec)) - m_.barAt(m_.startBeat));
    } else {
        g["bars"] = r2(m_.durationSec * m_.bpm / 240.0);
    }
    if (m_.mapped) {  // the tempo changes: its range over the rendered beats
        const auto [lo, hi] = bpmRange(m_.startBeat, m_.beatAt(m_.durationSec));
        g["bpmRange"] = {r1(lo), r1(hi)};
    }
    if (m_.metered) {  // meters in play: [first bar (1-based), "3/4"]
        json meters = json::array();
        const double end = std::max(m_.beatAt(m_.durationSec), m_.startBeat + 1e-9);
        const auto& pts = m_.meter.points();
        for (std::size_t i = 0; i < pts.size(); ++i) {
            const double next = i + 1 < pts.size() ? pts[i + 1].beat : end + 1.0;
            if (next <= m_.startBeat || pts[i].beat >= end) continue;
            const double from = std::max(pts[i].beat, m_.startBeat);
            meters.push_back({static_cast<int>(std::floor(m_.barAt(from) + 1e-9)) + 1,
                              std::to_string(pts[i].numerator) + "/" + std::to_string(pts[i].denominator)});
        }
        g["meter"] = meters;
    }
    g["lufsIntegrated"] = r1(m_.lufsI);
    g["loudnessRange"] = r1(m_.lra);
    g["shortTermMax"] = r1(stMax_);
    g["momentaryMax"] = r1(mMax_);
    g["truePeakDbtp"] = r2(m_.truePeakDb);
    g["samplePeakDb"] = r1(m_.samplePeakDb);
    g["plr"] = r1(m_.truePeakDb - m_.lufsI);
    const double rms = mixAgg_.rmsDb();
    g["rmsDb"] = r1(rms);
    g["crestDb"] = r1(m_.samplePeakDb - rms);
    g["clippedSamples"] = clipped_;
    if (firstClipSec_ >= 0) g["firstClipSec"] = r2(firstClipSec_);
    g["dcOffset"] = {std::round(dcL_ * 1e6) / 1e6 + 0.0, std::round(dcR_ * 1e6) / 1e6 + 0.0};
    g["stereoCorrelation"] = r2(mixAgg_.corr());
    g["widthPct"] = r1(mixAgg_.width());
    g["balanceLrDb"] = r1(lrBalanceDb(mixAgg_.ll, mixAgg_.rr));
    g["lowEndCorrelation"] = r2(mixAgg_.lowCorr());
    g["clicks"] = m_.clicksInMix;          // totals; report.clicks lists at most kMaxClicksReported
    g["clicksMasked"] = m_.clicksMasked;
    m_.stMax = stMax_;
    m_.rmsDb = rms;
    m_.corr = mixAgg_.corr();
    m_.width = mixAgg_.width();
    m_.lowCorr = mixAgg_.lowCorr();
    m_.balanceDb = lrBalanceDb(mixAgg_.ll, mixAgg_.rr);
    m_.clippedSamples = clipped_;
    m_.vsRef = vsRef_;
    double pct[kNumBands], db[kNumBands];
    for (int b = 0; b < kNumBands; ++b) {
        pct[b] = mixAgg_.bandPct(b);
        db[b] = pct[b] > 0 ? 10.0 * std::log10(pct[b] / 100.0) : -99.0;
    }
    g["bandsPct"] = bandObject(pct);
    g["bandsDb"] = bandObject(db);
    g["bandsVsRefDb"] = bandObject(vsRef_.data());
    const double all = mixAgg_.energy();
    g["subsonicPct"] = r2(all > 0 ? 100.0 * mixAgg_.band[kInfraSlot] / all : 0.0);
    g["spectralTiltDbPerOct"] = r2(tilt_);
    g["referenceTiltDbPerOct"] = r2(refTilt_);
    g["centroidHz"] = ri(m_.mix->centroidHz());
    json third;
    third["hz"] = thirdHz_;
    std::vector<double> dv;
    for (double d : thirdVsRef_) dv.push_back(r1(d));
    third["vsRefDb"] = dv;
    g["thirdOctave"] = third;
    return g;
}

void ReportBuilder::buildSections() {
    const std::size_t ns = m_.sections.size(), nn = m_.nodes.size();
    mixSec_.clear();
    nodeSec_.assign(nn, {});
    nodeAll_.clear();
    trackBandSum_.assign(ns, {});
    for (auto& s : m_.sections) {
        const Agg a = aggregate(*m_.mix, secSample(s.startSec), secSample(s.endSec));
        s.lufs = a.frames > 0 ? gatedLufs(m_.kTick, m_.tickLen, m_.mix->frames(), sr_, s.startSec, s.endSec, a.lufs()) : kDbFloor;
        mixSec_.push_back(a);
    }
    for (std::size_t n = 0; n < nn; ++n) {
        const auto& st = *m_.nodes[n].stats;
        nodeAll_.push_back(aggregate(st, 0, kEndOfStream));
        for (std::size_t s = 0; s < ns; ++s) {
            nodeSec_[n].push_back(aggregate(st, secSample(m_.sections[s].startSec), secSample(m_.sections[s].endSec)));
            if (!m_.nodes[n].isBus)
                for (int b = 0; b < kNumBands; ++b) trackBandSum_[s][static_cast<std::size_t>(b)] += nodeSec_[n][s].band[b];
        }
        if (!m_.nodes[n].isBus)
            for (int b = 0; b < kNumBands; ++b) trackBandTotal_[static_cast<std::size_t>(b)] += nodeAll_[n].band[b];
    }
}

json ReportBuilder::sectionsJson() {
    json arr = json::array();
    for (std::size_t s = 0; s < m_.sections.size(); ++s) {
        const auto& sec = m_.sections[s];
        const Agg& a = mixSec_[s];
        json j;
        j["name"] = sec.name;
        if (sec.implicit) j["implicit"] = true;
        j["startSec"] = r2(sec.startSec);
        j["endSec"] = r2(sec.endSec);
        const double beat0 = m_.beatAt(sec.startSec), beat1 = m_.beatAt(sec.endSec);
        j["startBar"] = r2(1.0 + m_.barAt(beat0));
        j["endBar"] = r2(1.0 + m_.barAt(beat1));
        if (m_.metered) {
            const MeterPoint& mp = m_.meter.meterAt(beat0 + 1e-9);
            j["meter"] = std::to_string(mp.numerator) + "/" + std::to_string(mp.denominator);
        }
        if (m_.mapped && sec.endSec > sec.startSec) {  // average tempo, and where it starts / ends when it moves
            j["bpm"] = r1((beat1 - beat0) * 60.0 / (sec.endSec - sec.startSec));
            const auto [lo, hi] = bpmRange(beat0, beat1);
            if (hi - lo > 0.05) {
                j["bpmStart"] = r1(m_.tempo.bpmAt(beat0));
                j["bpmEnd"] = r1(m_.tempo.bpmAt(std::max(beat0, beat1 - 1e-9)));
                j["bpmRange"] = {r1(lo), r1(hi)};
            }
        }
        j["lufs"] = r1(sec.lufs);
        // Short-term (3 s) windows that lie inside the section, so a loud previous section cannot leak
        // into e.g. a quiet outro; sections shorter than 3 s use the windows ending inside them.
        double stMax = kDbFloor;
        const auto first = static_cast<std::size_t>(std::max(0.0, std::ceil(sec.startSec / m_.tickSec() - 1e-9)));
        auto inside = [&](std::size_t t) { return t < m_.shortTerm.size() && (static_cast<double>(t) + 1.0) * m_.tickSec() <= sec.endSec + 1e-9; };
        const std::size_t t0 = inside(first + 29) ? first + 29 : first;
        for (std::size_t t = t0; inside(t); ++t) stMax = std::max(stMax, static_cast<double>(m_.shortTerm[t]));
        j["shortTermMax"] = r1(stMax);
        j["peakDb"] = r1(dbFromAmplitude(a.peak));
        j["rmsDb"] = r1(a.rmsDb());
        j["correlation"] = r2(a.corr());
        j["widthPct"] = r1(a.width());
        j["lowEndCorrelation"] = r2(a.lowCorr());
        double pct[kNumBands], vs[kNumBands];
        for (int b = 0; b < kNumBands; ++b) pct[b] = a.bandPct(b);
        balanceVsReference(a.band, m_.refShare, vs);
        SectionData& sd = m_.sections[s];
        sd.stMax = stMax;
        sd.peakDb = dbFromAmplitude(a.peak);
        sd.rmsDb = a.rmsDb();
        sd.corr = a.corr();
        sd.width = a.width();
        sd.lowCorr = a.lowCorr();
        sd.lowShare = a.lowShare();
        sd.balanceDb = lrBalanceDb(a.ll, a.rr);
        for (int b = 0; b < kNumBands; ++b) sd.vsRef[static_cast<std::size_t>(b)] = a.bandSum() > 0 ? vs[b] : 0.0;
        j["bandsPct"] = bandObject(pct);
        j["bandsVsRefDb"] = bandObject(vs);
        double trackTotal = 0.0;
        for (double v : trackBandSum_[s]) trackTotal += v;
        std::vector<std::pair<double, json>> active;
        for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
            const Agg& na = nodeSec_[n][s];
            const double rms = na.rmsDb();
            if (rms <= -50.0) continue;
            json e;
            e["id"] = m_.nodes[n].id;
            if (m_.nodes[n].isBus) e["bus"] = true;
            e["rmsDb"] = r1(rms);
            e["sharePct"] = r1(trackTotal > 0 ? 100.0 * na.bandSum() / trackTotal : 0.0);
            active.push_back({rms, e});
        }
        std::stable_sort(active.begin(), active.end(), [](const auto& x, const auto& y) { return x.first > y.first; });
        json act = json::array();
        for (auto& [lvl, e] : active) act.push_back(e);
        j["active"] = act;
        arr.push_back(j);
    }
    return arr;
}

json ReportBuilder::nodesJson() {
    json arr = json::array();
    double trackTotal = 0.0;
    for (double v : trackBandTotal_) trackTotal += v;
    for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
        NodeData& node = m_.nodes[n];
        const StreamStats& st = *node.stats;
        const Agg& all = nodeAll_[n];
        json j;
        j["id"] = node.id;
        j["bus"] = node.isBus;
        // RMS while active (ticks above -60 dBFS), activity share, loudness.
        double actE = 0.0, actF = 0.0, total = 0.0, active50 = 0.0;
        std::vector<double> kt(st.ticks().size());
        for (std::size_t t = 0; t < st.ticks().size(); ++t) {
            const Tick& tk = st.ticks()[t];
            const double f = st.tickFrames(t);
            kt[t] = tk.k;
            total += f;
            if (f <= 0) continue;
            const double db = dbFromPower(tk.energy() / (2.0 * f));
            if (db > -60.0) { actE += tk.energy(); actF += f; }
            if (db > -50.0) active50 += f;
        }
        node.rmsDb = actF > 0 ? dbFromPower(actE / (2.0 * actF)) : kDbFloor;
        node.peakDb = dbFromAmplitude(all.peak);
        j["peakDb"] = r1(node.peakDb);
        j["rmsDb"] = r1(node.rmsDb);
        node.lufs = gatedLufs(kt, m_.tickLen, st.frames(), sr_, 0.0, static_cast<double>(st.frames()) / sr_ + 1.0, all.lufs());
        j["lufs"] = r1(node.lufs);
        j["crestDb"] = r1(node.rmsDb > kDbFloor ? node.peakDb - node.rmsDb : 0.0);
        j["activePct"] = r1(total > 0 ? 100.0 * active50 / total : 0.0);
        double pct[kNumBands], share[kNumBands];
        int dom = 0;
        for (int b = 0; b < kNumBands; ++b) {
            pct[b] = all.bandPct(b);
            if (all.band[b] > all.band[dom]) dom = b;
            const double tb = trackBandTotal_[static_cast<std::size_t>(b)];
            share[b] = tb > 0 ? 100.0 * all.band[b] / tb : 0.0;
        }
        node.dominantBand = all.bandSum() > 0 ? dom : -1;
        j["dominantBand"] = all.bandSum() > 0 ? kBandNames[dom] : "none";
        j["centroidHz"] = ri(st.centroidHz());
        j["bandsPct"] = bandObject(pct);
        json ms = bandObject(share);
        ms["total"] = r1(trackTotal > 0 ? 100.0 * all.bandSum() / trackTotal : 0.0);
        j["mixSharePct"] = ms;
        j["correlation"] = r2(all.corr());
        j["widthPct"] = r1(all.width());
        j["balanceLrDb"] = r1(lrBalanceDb(all.ll, all.rr));
        if (all.lowShare() > 0.01) j["lowEndCorrelation"] = r2(all.lowCorr());
        node.corr = all.corr();
        node.width = all.width();
        node.balanceDb = lrBalanceDb(all.ll, all.rr);
        node.lowCorr = all.lowCorr();
        node.lowShare = all.lowShare();
        node.sharePct = trackTotal > 0 ? 100.0 * all.bandSum() / trackTotal : 0.0;
        node.sectionRmsDb.clear();
        json secs = json::array();
        for (std::size_t s = 0; s < m_.sections.size(); ++s) {
            const Agg& a = nodeSec_[n][s];
            node.sectionRmsDb.push_back(a.rmsDb());
            double tt = 0.0;
            for (double v : trackBandSum_[s]) tt += v;
            secs.push_back({{"section", m_.sections[s].name}, {"rmsDb", r1(a.rmsDb())},
                            {"sharePct", r1(tt > 0 ? 100.0 * a.bandSum() / tt : 0.0)}});
        }
        j["sections"] = secs;
        std::vector<int> bars;
        for (double b = firstBar(); b < endBar(); b += 1.0) bars.push_back(ri(aggregate(st, barSample(b), barSample(b + 1.0)).rmsDb()));
        j["barsRmsDb"] = bars;
        if (st.nonFiniteSamples() > 0) {
            nonFinite_ += st.nonFiniteSamples();
            warn(0, "non_finite", fmt("'%s' produced %lld non-finite samples (NaN/Inf), treated as silence: a module is unstable.",
                                      node.id.c_str(), static_cast<long long>(st.nonFiniteSamples())), {}, {node.id});
        }
        if (node.peakDb > 0.0)
            warn(2, "node_hot", fmt("'%s' peaks at %+.1f dBFS before the master (float, so not clipped yet): lower its gainDb "
                                    "by ~%.0f dB to keep headroom for the master chain.", node.id.c_str(), node.peakDb,
                                    std::ceil(node.peakDb + 3.0)), {}, {node.id});
        arr.push_back(j);
    }
    return arr;
}

std::string ReportBuilder::topContributors(int band, std::size_t count) const {
    std::vector<std::pair<double, std::string>> v;
    const double tb = trackBandTotal_[static_cast<std::size_t>(band)];
    if (tb <= 0) return "";
    for (std::size_t n = 0; n < m_.nodes.size(); ++n)
        if (!m_.nodes[n].isBus) v.push_back({nodeAll_[n].band[band] / tb, m_.nodes[n].id});
    std::stable_sort(v.begin(), v.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
    std::string s;
    for (std::size_t i = 0; i < v.size() && i < count; ++i) {
        if (v[i].first < 0.05) break;
        s += fmt("%s'%s' %.0f%%", i ? ", " : "", v[i].second.c_str(), 100.0 * v[i].first);
    }
    return s;
}

void ReportBuilder::checkMasking() {
    struct Hit { std::string section; double shareA, shareB, coinc, sep; };
    struct Key {
        std::size_t a, b;
        int band;
        bool operator==(const Key& o) const { return std::tie(a, b, band) == std::tie(o.a, o.b, o.band); }
    };
    std::vector<std::pair<Key, std::vector<Hit>>> hits;
    auto listFor = [&](const Key& k) -> std::vector<Hit>& {
        for (auto& [key, v] : hits)
            if (key == k) return v;
        hits.push_back({k, {}});
        return hits.back().second;
    };
    for (std::size_t s = 0; s < m_.sections.size(); ++s) {
        double total = 0.0;
        for (double v : trackBandSum_[s]) total += v;
        if (total <= 0) continue;
        const double frames = mixSec_[s].frames;
        for (int b = 0; b < kNumBands; ++b) {
            const double bandE = trackBandSum_[s][static_cast<std::size_t>(b)];
            // Only bands that matter in this section (relative to how much that band usually carries).
            if (bandE / total < std::max(0.25 * m_.refShare[static_cast<std::size_t>(b)], 0.005)) continue;
            if (frames <= 0 || dbFromPower(bandE / (2.0 * frames)) < -60.0) continue;
            // the two biggest carriers of the band. Mids and highs: both over 35 %. The low end (sub / bass: kick vs
            // bass) is judged on the separation of their envelopes, not on the shares: there both need only 25 %
            // and 70 % together - a pair near 35 % no longer drops in and out of the check with a 1 dB level edit.
            std::vector<std::pair<double, std::size_t>> shares;
            for (std::size_t n = 0; n < m_.nodes.size(); ++n)
                if (!m_.nodes[n].isBus) shares.push_back({nodeSec_[n][s].band[b] / bandE, n});
            std::stable_sort(shares.begin(), shares.end(), [](const auto& x, const auto& y) { return x.first > y.first; });
            if (shares.size() < 2) continue;
            const bool low = b <= 1;
            const double s0 = shares[0].first, s1 = shares[1].first;
            if (low ? !(s1 > 0.25 && s0 + s1 > 0.7) : !(s1 > 0.35)) continue;
            const std::size_t a = std::min(shares[0].second, shares[1].second), c = std::max(shares[0].second, shares[1].second);
            const double co = coincidence(*m_.nodes[a].stats, *m_.nodes[c].stats, b, sr_, m_.sections[s].startSec, m_.sections[s].endSec);
            if (co < 0.3) continue;  // one of them is (almost) only a tail or they strictly alternate
            const double sep = b <= 1 ? lowSeparationDb(*m_.nodes[a].stats, *m_.nodes[c].stats, sr_, m_.sections[s].startSec,
                                                        m_.sections[s].endSec)
                                      : 0.0;
            listFor({a, c, b}).push_back({m_.sections[s].name, nodeSec_[a][s].band[b] / bandE, nodeSec_[c][s].band[b] / bandE, co, sep});
        }
    }
    const bool implicitOnly = m_.sections.size() == 1 && m_.sections[0].implicit;
    for (auto& [key, list] : hits) {
        const std::string& A = m_.nodes[key.a].id;
        const std::string& B = m_.nodes[key.b].id;
        std::vector<std::string> secNames;
        double maxCo = 0.0, sa = 0.0, sb = 0.0, minSep = 1e9;
        std::string sepList;   // the low-end separation per section (the worst decides)
        for (auto& h : list) {
            secNames.push_back(h.section);
            maxCo = std::max(maxCo, h.coinc);
            minSep = std::min(minSep, h.sep);
            sepList += (sepList.empty() ? "" : ", ") + h.section + fmt(" %.1f", h.sep);
            sa = std::max(sa, h.shareA);
            sb = std::max(sb, h.shareB);
        }
        const std::string where = implicitOnly ? std::string("across the song") : "in " + quoteList(secNames);
        const int band = key.band;
        // Low end: judged on 10 ms envelopes, so working sidechain ducking (kick vs bass) is recognised.
        // Sharing the top octaves (hats + shaker, cymbal layers) is normal and rarely masks: info only.
        const bool lowBand = band <= 1, topBand = band >= 5;
        const bool ducked = lowBand && minSep >= 3.0;
        const int sev = topBand ? 2 : lowBand ? (ducked ? 2 : 1) : (maxCo >= 0.6 ? 1 : 2);
        std::string msg = fmt("'%s' and '%s' both carry %s of the %s band (%s) %s (up to %.0f%% / %.0f%%, ", A.c_str(), B.c_str(),
                              lowBand ? "the bulk (>25% each, >70% together)" : ">35%", kBandNames[band], kBandRanges[band],
                              where.c_str(), 100 * sa, 100 * sb);
        msg += lowBand ? fmt("low-end ducking between them %.1f dB", minSep) + (list.size() > 1 ? " (" + sepList + ")" : "")
                           + ", 3+ = they alternate)" : fmt("temporal overlap %.2f)", maxCo);
        msg += lowBand ? (ducked ? ": they alternate (ducking/sidechain works), so masking is moderate."
                          : minSep >= 1.5 ? ": they overlap in time; the ducking between them is weak."
                                          : ": they overlap in time (little or no ducking between them).")
                       : maxCo < 0.6 ? ": they partly alternate in time, so masking is moderate."
                       : topBand ? ": usually fine for hats/cymbals, but check that both stay distinct." : ": they mask each other.";
        warn(sev, "masking", msg, implicitOnly ? std::vector<std::string>{} : secNames, {A, B});

        const int domA = m_.nodes[key.a].dominantBand, domB = m_.nodes[key.b].dominantBand;
        if (band <= 1) {
            const bool kickA = looksLikeKick(A), kickB = looksLikeKick(B);
            if (kickA != kickB) {
                const std::string& kick = kickA ? A : B;
                const std::string& other = kickA ? B : A;
                const int domOther = kickA ? domB : domA;
                if (ducked)
                    suggest(fmt("'%s' already ducks under '%s' by ~%.0f dB; if the low end still sounds crowded, deepen the duck "
                                "(ducker \"depth\") or carve EQ so the kick owns ~50-60 Hz and the bass owns ~80-120 Hz.",
                                other.c_str(), kick.c_str(), minSep));
                else if (domOther >= 0 && domOther <= 1)
                    suggest(fmt("'%s' and '%s' fight in the low end (ducking between them only %.1f dB): duck '%s' under the kick "
                                "by 8-14 dB ({\"type\": \"ducker\", \"sidechain\": \"%s\", \"params\": {\"depth\": 10, \"release\": "
                                "150}}; if it already has one, raise its depth or hold), move its loudest low notes off the kick, "
                                "and/or carve EQ so the kick owns ~50-60 Hz and the bass owns ~80-120 Hz.",
                                kick.c_str(), other.c_str(), minSep, other.c_str(), kick.c_str()));
                else
                    suggest(fmt("'%s' adds low end under '%s': high-pass '%s' ({\"type\": \"eq\", \"params\": {\"hp.freq\": 150}}; "
                                "its body is higher up) or duck it from the kick ({\"type\": \"ducker\", \"sidechain\": \"%s\"}).",
                                other.c_str(), kick.c_str(), other.c_str(), kick.c_str()));
            } else if (domA >= 0 && domA <= 1 && domB >= 0 && domB <= 1) {
                suggest(fmt("'%s' and '%s' are both low-end parts: let one own the sub (< 80 Hz) and high-pass the other "
                            "({\"type\": \"eq\", \"params\": {\"hp.freq\": 90}}), move one an octave up, or duck one from the other "
                            "with a \"ducker\" keyed (\"sidechain\") by it.", A.c_str(), B.c_str()));
            } else {
                suggest(fmt("'%s' and '%s' overlap in %s (%s): high-pass the less important one at 120-200 Hz "
                            "({\"type\": \"eq\", \"params\": {\"hp.freq\": 150}}).", A.c_str(), B.c_str(), kBandNames[band],
                            kBandRanges[band]));
            }
        } else if (band == 2) {
            suggest(fmt("'%s' and '%s' build mud in 250-800 Hz: cut 2-4 dB around 300-500 Hz on the less important one "
                        "({\"type\": \"eq\", \"params\": {\"peak1.freq\": 400, \"peak1.gain\": -3}}), high-pass it higher, or voice "
                        "one of them an octave up.", A.c_str(), B.c_str()));
        } else {
            suggest(fmt("'%s' and '%s' compete in %s (%s): carve complementary EQ (cut one where the other peaks), pan them "
                        "apart, or let them alternate (call and response).", A.c_str(), B.c_str(), kBandNames[band], kBandRanges[band]));
        }
    }

    // Nearly inaudible and silent tracks.
    for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
        if (m_.nodes[n].isBus) continue;
        bool plays = false;
        double maxShare = 0.0;
        std::string loudestSec;
        for (std::size_t s = 0; s < m_.sections.size(); ++s) {
            const Agg& a = nodeSec_[n][s];
            if (a.rmsDb() <= -50.0) continue;
            plays = true;
            double total = 0.0;
            for (double v : trackBandSum_[s]) total += v;
            double best = total > 0 ? a.bandSum() / total : 0.0;
            for (int b = 0; b < kNumBands; ++b) {
                const double bandE = trackBandSum_[s][static_cast<std::size_t>(b)];
                if (total > 0 && bandE / total >= 0.005) best = std::max(best, a.band[b] / bandE);
            }
            if (best > maxShare) { maxShare = best; loudestSec = m_.sections[s].name; }
        }
        const std::string& id = m_.nodes[n].id;
        if (!plays) {
            warn(2, "silent_node", fmt("'%s' never rises above -50 dBFS RMS in any section (muted, empty or far too quiet).", id.c_str()),
                 {}, {id});
        } else if (maxShare < 0.01) {
            warn(1, "inaudible", fmt("'%s' is nearly inaudible: it never contributes more than %.1f%% of the energy of any band in "
                                     "the sections where it plays (max in '%s'). Raise its gainDb by 6-12 dB or remove it.",
                                     id.c_str(), 100.0 * maxShare, loudestSec.c_str()), {}, {id});
        }
    }
}

void ReportBuilder::checkBalance() {
    if (mixAgg_.bandSum() <= 0) return;
    const AnalysisProfile& P = *m_.profile;
    auto d = [&](int b) { return vsRef_[static_cast<std::size_t>(b)]; };
    struct Rule { int band; bool high; int sev; const char* what; const char* fix; };
    // Limits come from the analysis profile (bandHighDb / bandLowDb; a direction without a limit is
    // not checked). Fixes are phrased with the engine's own effects (eq bands hp/low/peak1-3/high/lp,
    // width, ducker).
    static const Rule rules[] = {
        {0, true, 1, "too much sub: boomy and eats headroom on big systems",
         "lower the sub on the main contributors ({\"type\": \"eq\", \"params\": {\"low.freq\": 60, \"low.gain\": -3}}) or shorten "
         "long 808/kick tails; high-pass everything that is not kick or bass ({\"type\": \"eq\", \"params\": {\"hp.freq\": 35}})"},
        {0, false, 2, "very little sub: the low end will feel thin",
         "add sub to the bass (sub oscillator or an octave lower) or use a longer, deeper kick"},
        {1, true, 1, "boomy low end",
         "cut 2-4 dB around 100-200 Hz on the main contributors ({\"type\": \"eq\", \"params\": {\"peak1.freq\": 150, \"peak1.gain\": -3}}) "
         "or lower their gainDb"},
        {1, false, 2, "light on bass (60-250 Hz): the mix may sound thin",
         "raise the bass gainDb or give the kick more body around 80-120 Hz"},
        {2, true, 1, "muddy low mids",
         "cut 2-4 dB at 250-500 Hz on pads, keys and reverb returns ({\"type\": \"eq\", \"params\": {\"peak1.freq\": 350, "
         "\"peak1.gain\": -3}}) and high-pass reverb buses at 200-300 Hz ({\"hp.freq\": 250})"},
        {2, false, 2, "thin low mids: little body and warmth",
         "raise pads/keys gainDb, lower their high-pass, or add ~2 dB at 300-400 Hz on the pad ({\"type\": \"eq\", \"params\": "
         "{\"peak1.freq\": 350, \"peak1.gain\": 2}})"},
        {3, true, 1, "honky/boxy mids",
         "cut 2-3 dB around 1 kHz on the main contributors ({\"type\": \"eq\", \"params\": {\"peak2.freq\": 1000, \"peak2.gain\": -3}})"},
        {3, false, 2, "scooped mids: leads and keys may sound hollow or distant",
         "raise the lead/keys gainDb or boost 1-2 kHz on the lead ({\"type\": \"eq\", \"params\": {\"peak2.freq\": 1500, \"peak2.gain\": 2}})"},
        {4, true, 1, "harsh presence (2.5-6 kHz): fatiguing",
         "tame 2.5-5 kHz on leads/snare ({\"type\": \"eq\", \"params\": {\"peak3.freq\": 3500, \"peak3.gain\": -3}}) or lower synth cutoffs"},
        {4, false, 2, "recessed presence: leads and snare may lack definition",
         "boost 2-4 kHz on the lead ({\"type\": \"eq\", \"params\": {\"peak3.freq\": 3000, \"peak3.gain\": 3}}) or raise its gainDb"},
        {5, true, 1, "sizzly/brittle top (6-12 kHz)",
         "lower hats/cymbals gainDb or cut the top ({\"type\": \"eq\", \"params\": {\"high.freq\": 8000, \"high.gain\": -3}})"},
        {5, false, 2, "little brilliance (6-12 kHz): hats and synth edges may sound dull",
         "raise the hats, open synth filter cutoffs or add a high shelf ({\"type\": \"eq\", \"params\": {\"high.freq\": 8000, "
         "\"high.gain\": 2}})"},
        {6, true, 2, "a lot of air (12-20 kHz)",
         "check hats, noise and bright synths ({\"type\": \"eq\", \"params\": {\"lp.freq\": 14000}} on the brightest source)"},
        {6, false, 2, "little air (12-20 kHz)",
         "a gentle air shelf on the master ({\"type\": \"eq\", \"params\": {\"high.freq\": 12000, \"high.gain\": 1.5}}) or brighter "
         "hats / reverb returns"},
    };
    bool subHigh = false;
    for (const Rule& r : rules) {
        const std::size_t b = static_cast<std::size_t>(r.band);
        const std::optional<double> limit = r.high ? P.bandHighDb[b] : P.bandLowDb[b];
        if (!limit) continue;
        const double v = d(r.band);
        if (r.high ? v <= *limit : v >= *limit) continue;
        subHigh = subHigh || (r.band == 0 && r.high);
        warn(r.sev, std::string("balance_") + kBandNames[r.band] + (r.high ? "_high" : "_low"),
             fmt("%s %s is %+.1f dB vs the '%s' reference balance (relative to the rest of the spectrum; limit %+.0f): %s.",
                 kBandNames[r.band], kBandRanges[r.band], v, P.name.c_str(), *limit, r.what));
        // Naming the biggest contributors only helps when the band is too loud.
        const std::string who = r.high ? topContributors(r.band, 3) : std::string();
        const std::string from = who.empty() ? std::string() : " (mostly " + who + ")";
        suggest(fmt("%s %+.1f dB vs reference%s: %s.", kBandNames[r.band], v, from.c_str(), r.fix));
    }
    if (subHigh && P.name == defaultAnalysisProfile().name)
        suggest("The generic 'default' reference expects pop-like lows (flat only down to ~100 Hz). A four-on-the-floor "
                "synthwave / electronic mix is meant to carry a strong 40-60 Hz kick and bass: judge it against its genre with "
                "the render JSON \"analysis\": {\"profile\": \"synthwave\"} (profiles: " + analysisProfileNames() + ").");
    const double top = 10.0 * std::log10((std::pow(10.0, d(5) / 10.0) * m_.refShare[5] + std::pow(10.0, d(6) / 10.0) * m_.refShare[6]) /
                                         (m_.refShare[5] + m_.refShare[6]));
    if (top < P.dullDb) {
        warn(2, "dull", fmt("The top end (6-20 kHz) is %.1f dB below the '%s' reference balance (limit %.0f): the mix may sound "
                            "dull/dark.", top, P.name.c_str(), P.dullDb));
        suggest("Brighten the top: open filter cutoffs on pads/leads, add hats/shakers, or a gentle high shelf on the master "
                "({\"type\": \"eq\", \"params\": {\"high.freq\": 9000, \"high.gain\": 2}}).");
    }
    if (std::fabs(tilt_ - refTilt_) > P.tiltToleranceDbPerOct)
        warn(2, "tilt", fmt("Overall spectral tilt is %.1f dB/oct vs %.1f for the '%s' reference (tolerance +-%.1f): the mix is %s "
                            "overall.", tilt_, refTilt_, P.name.c_str(), P.tiltToleranceDbPerOct,
                            tilt_ < refTilt_ ? "darker/bass-heavier" : "brighter/thinner"));
    const double all = mixAgg_.energy();
    if (all > 0 && mixAgg_.band[kInfraSlot] / all > 0.01) {
        warn(1, "subsonic", fmt("%.1f%% of the energy is below 20 Hz (rumble/DC): wasted headroom.", 100.0 * mixAgg_.band[kInfraSlot] / all));
        suggest("High-pass the master or the offending tracks at 20-30 Hz to remove subsonic energy "
                "({\"type\": \"eq\", \"params\": {\"hp.freq\": 25}}).");
    }
}

void ReportBuilder::checkSectionsAndStereo() {
    // Global loudness / peaks.
    if (mixAgg_.energy() <= 0.0 || m_.lufsI <= -70.0)
        warn(0, "no_audio", m_.mixL.empty() ? "No mix audio was fed to the analyser." : "The mix is silent (integrated loudness below -70 LUFS).");
    if (m_.mix->nonFiniteSamples() > 0)
        warn(0, "non_finite", fmt("The mix contains %lld non-finite samples (NaN/Inf).", static_cast<long long>(m_.mix->nonFiniteSamples())));
    if (clipped_ > 0) {
        warn(0, "clipping", fmt("%lld samples clip (|x| >= 1.0), first at %s: they will distort in every player.",
                                static_cast<long long>(clipped_), fmtTime(firstClipSec_).c_str()));
        suggest("Put {\"type\": \"limiter\", \"params\": {\"ceiling\": -1.0}} last in the master fx, or lower master gainDb "
                "until clippedSamples is 0.");
    }
    if (m_.truePeakDb > -1.0 && mixAgg_.energy() > 0) {
        // Within 0.1 dB of the limit is limiter/meter tolerance (a -1.0 ceiling can read -0.97 here): info only.
        const bool marginal = m_.truePeakDb <= -0.9;
        const double ceiling = std::min(-1.0, -1.2 - (m_.truePeakDb + 1.0));
        warn(m_.truePeakDb > 0.0 ? 0 : marginal ? 2 : 1, "true_peak",
             marginal ? fmt("True peak %+.2f dBTP is marginally above -1.0 dBTP (within limiter tolerance).", m_.truePeakDb)
                      : fmt("True peak %+.2f dBTP is above -1.0 dBTP: inter-sample overs will distort after MP3/AAC encoding.",
                            m_.truePeakDb));
        suggest(fmt("Set the master limiter's \"ceiling\" to %.1f (it is true-peak aware) so truePeakDbtp stays <= -1.0.", ceiling));
    }
    const AnalysisProfile& P = *m_.profile;
    if (mixAgg_.energy() > 0 && m_.lufsI > -70.0) {
        const double mid = 0.5 * (m_.lufsMin + m_.lufsMax);
        const std::string whose = m_.loudnessOverride ? std::string("render JSON analysis.loudness")
                                                      : "'" + P.name + "' profile";
        if (m_.lufsI < m_.lufsMin) {
            warn(1, "loudness_low", fmt("Integrated loudness %.1f LUFS is %.1f LU below the target %.0f..%.0f LUFS (%s; sample peak "
                                        "%.1f dBFS).", m_.lufsI, m_.lufsMin - m_.lufsI, m_.lufsMin, m_.lufsMax, whose.c_str(),
                                        m_.samplePeakDb));
            suggest(fmt("Raise the master limiter's input \"gain\" by about %.1f dB to land near %.0f LUFS (add {\"type\": \"limiter\", "
                        "\"params\": {\"ceiling\": -1.0}} last in the master fx if there is none).", mid - m_.lufsI, mid));
        } else if (m_.lufsI > m_.lufsMax) {
            warn(1, "loudness_high", fmt("Integrated loudness %.1f LUFS is %.1f LU above the target %.0f..%.0f LUFS (%s): streaming "
                                         "services will turn it down and the limiting costs punch (PLR %.1f dB).",
                                         m_.lufsI, m_.lufsI - m_.lufsMax, m_.lufsMin, m_.lufsMax, whose.c_str(), m_.truePeakDb - m_.lufsI));
            suggest(fmt("Lower the master limiter's input \"gain\" by about %.1f dB to land near %.0f LUFS.", m_.lufsI - mid, mid));
        }
    }
    if (m_.durationSec > 30.0 && mixAgg_.energy() > 0) {
        if (m_.lra < P.lraMinLu)
            warn(2, "lra_low", fmt("Loudness range is only %.1f LU (the '%s' profile expects %.1f..%.0f): sections barely differ in "
                                   "level (flat arrangement or heavy compression). Quieter verses/breakdowns make choruses hit harder.",
                                   m_.lra, P.name.c_str(), P.lraMinLu, P.lraMaxLu));
        else if (m_.lra > P.lraMaxLu)
            warn(2, "lra_high", fmt("Loudness range is %.1f LU (the '%s' profile expects %.1f..%.0f): very dynamic; quiet parts may "
                                    "get lost on small speakers.", m_.lra, P.name.c_str(), P.lraMinLu, P.lraMaxLu));
    }
    if (std::fabs(dcL_) > 0.001 || std::fabs(dcR_) > 0.001) {
        warn(1, "dc_offset", fmt("DC offset L %.4f / R %.4f: wastes headroom and causes clicks at edits.", dcL_, dcR_));
        suggest("High-pass the master at 20 Hz to remove the DC offset ({\"type\": \"eq\", \"params\": {\"hp.freq\": 20}}).");
    }
    if (mixAgg_.energy() > 0 && m_.lufsI > -70.0 && m_.truePeakDb - m_.lufsI < P.plrMinDb)
        warn(2, "squashed", fmt("Peak-to-loudness ratio is only %.1f dB (the '%s' profile expects >= %.0f dB): heavily limited, "
                                "transients and punch are flattened.", m_.truePeakDb - m_.lufsI, P.name.c_str(), P.plrMinDb));
    if (mixAgg_.ll > 0 && mixAgg_.rr > 0) {
        const double bal = 10.0 * std::log10(mixAgg_.ll / mixAgg_.rr);
        if (std::fabs(bal) > 1.5) {
            warn(1, "lr_balance", fmt("The mix leans %s: the left channel is %+.1f dB vs the right. Check pans and one-sided "
                                      "effects (nodes[].balanceLrDb).", bal > 0 ? "left" : "right", bal));
            suggest("Re-centre the image: balance the pans of the loudest off-centre parts (see nodes[].balanceLrDb) or pan a "
                    "counterpart to the other side.");
        }
    }

    // Stereo image.
    const bool lowSmeared = mixAgg_.lowShare() > 0.05 && mixAgg_.lowCorr() < 0.75;
    if (mixAgg_.energy() > 0) {
        const double c = mixAgg_.corr(), w = mixAgg_.width();
        if (c < -0.2) {
            warn(0, "phase", fmt("Stereo correlation is %.2f: L and R are largely out of phase; the mix collapses in mono.", c));
            suggest("Find the phasey source (nodes[].correlation < 0): reduce its stereo width ({\"type\": \"width\", \"params\": "
                    "{\"width\": 0.7}}), Haas delays or chorus width.");
        } else if (c < 0.0) {
            warn(1, "phase", fmt("Stereo correlation is %.2f (< 0): very wide and partly out of phase; check mono compatibility.", c));
        } else if (c < 0.2) {
            warn(2, "very_wide", fmt("Stereo correlation is %.2f: a very wide, loosely correlated image; check mono compatibility.", c));
        } else if (c > 0.97 && w < 2.0 &&  // narrow_mix (space) says it with the fixes
                   std::find(m_.space.global.issues.begin(), m_.space.global.issues.end(), "narrow") == m_.space.global.issues.end()) {
            warn(2, "mono", fmt("The mix is essentially mono (correlation %.2f, width %.1f%%).", c, w));
            suggest("Add stereo interest: pan secondary parts (arps, hats, pads) left/right, chorus or {\"type\": \"width\", "
                    "\"params\": {\"width\": 1.4}} on pads, sends to a stereo reverb bus.");
        }
        if (lowSmeared) {
            warn(1, "low_end_not_mono", fmt("The low end (< 150 Hz) has correlation %.2f: bass energy is spread in stereo and will "
                                            "partially cancel in mono / on club systems.", mixAgg_.lowCorr()));
            suggest("Keep the low end mono: add {\"type\": \"width\", \"params\": {\"monobass\": 120}} on the master (or the bass "
                    "bus), pan kick/bass centre, avoid stereo chorus/unison spread on the bass.");
        }
    }

    // Per-section checks.
    if (m_.sections.size() == 1 && m_.sections[0].implicit) return;
    for (std::size_t s = 0; s < m_.sections.size(); ++s) {
        const auto& sec = m_.sections[s];
        const Agg& a = mixSec_[s];
        if (sec.startSec >= m_.durationSec - 1e-6) {
            warn(1, "section_out_of_range", fmt("Section '%s' starts at %s, after the audio ends (%s).", sec.name.c_str(),
                                                fmtTime(sec.startSec).c_str(), fmtTime(m_.durationSec).c_str()), {sec.name});
            continue;
        }
        if (a.frames <= 0) continue;
        if (a.rmsDb() < -60.0) {
            warn(1, "silent_section", fmt("Section '%s' is (nearly) silent: RMS %.1f dBFS.", sec.name.c_str(), a.rmsDb()), {sec.name});
            continue;
        }
        if (a.corr() < -0.2)
            warn(1, "phase", fmt("Section '%s' has stereo correlation %.2f: phasey, collapses in mono.", sec.name.c_str(), a.corr()), {sec.name});
        else if (a.corr() < 0.0)
            warn(2, "very_wide", fmt("Section '%s' has stereo correlation %.2f: very wide/uncorrelated, borderline phasey; check mono "
                                     "compatibility.", sec.name.c_str(), a.corr()), {sec.name});
        if (a.lowShare() > 0.05 && a.lowCorr() < 0.75 && !lowSmeared)
            warn(1, "low_end_not_mono", fmt("Section '%s': low end (< 150 Hz) correlation %.2f; keep the bass mono.", sec.name.c_str(), a.lowCorr()), {sec.name});
    }
    // Level jumps between consecutive sections.
    for (std::size_t s = 1; s < m_.sections.size(); ++s) {
        const auto& p = m_.sections[s - 1];
        const auto& c = m_.sections[s];
        if (p.lufs <= -70.0 || c.lufs <= -70.0) continue;
        const double jump = c.lufs - p.lufs;
        if (std::fabs(jump) > 6.0)
            warn(2, "level_jump", fmt("'%s' -> '%s': loudness jumps %+.1f LU (%.1f -> %.1f LUFS); fine for a deliberate drop or "
                                      "breakdown, otherwise rebalance or automate gainDb.", p.name.c_str(), c.name.c_str(), jump,
                                      p.lufs, c.lufs), {p.name, c.name});
    }
}

json ReportBuilder::timelineJson() {
    json tl;
    if (m_.mapped || m_.metered) {  // bars differ in length: the first one's, each row has its start in sec
        const double b = firstBar();
        tl["barSec"] = r3(m_.secAtBeat(m_.barStartBeat(b + 1.0)) - m_.secAtBeat(m_.barStartBeat(b)));
    } else {
        tl["barSec"] = r3(240.0 / m_.bpm);
    }
    tl["columns"] = {"bar", "sec", "lufs", "peakDb", "widthPct", "sub", "bass", "lowmid", "mid", "presence", "brilliance", "air"};
    tl["note"] = m_.metered || m_.mapped
                     ? "one row per song bar (the song's meter and tempo map; sec = the bar's start): lufs = loudness of the bar "
                       "(ungated), band columns = band level in dBFS"
                     : "one row per 4/4 bar (song numbering): lufs = loudness of the bar (ungated), band columns = band level in dBFS";
    json rows = json::array();
    for (double b = firstBar(); b < endBar(); b += 1.0) {
        const std::int64_t s0 = barSample(b), s1 = barSample(b + 1.0);
        const Agg a = aggregate(*m_.mix, s0, s1);
        double k = a.k;
        std::size_t g0 = 0, g1 = 0;
        if (m_.mix->segmentRange(s0, s1, g0, g1)) {  // exact K-weighted energy of the bar
            k = 0.0;
            for (std::size_t g = g0; g < g1 && g < segK_.size(); ++g) k += segK_[g];
        }
        json row = {static_cast<int>(b) + 1, r2(std::max(0.0, static_cast<double>(s0) / sr_)),
                    r1(a.frames > 0 ? lufsFromMeanSquare(k / a.frames) : kDbFloor), r1(dbFromAmplitude(a.peak)), ri(a.width())};
        for (int band = 0; band < kNumBands; ++band) row.push_back(ri(a.bandDbFs(band)));
        rows.push_back(row);
    }
    tl["rows"] = rows;
    return tl;
}

json ReportBuilder::clicksJson() {
    json arr = json::array();
    static const char* kSev[] = {"high", "medium", "low"};
    for (const ClickInfo& k : m_.clicks) {
        const double beat = std::round(m_.beatAt(k.sec) * 100.0) / 100.0;
        const double bar = std::floor(m_.barAt(beat) + 1e-9);
        json j;
        j["time"] = fmtTimeMs(k.sec);
        j["sec"] = std::round(k.sec * 10000.0) / 10000.0 + 0.0;
        j["bar"] = static_cast<int>(bar) + 1;
        j["beat"] = r2(beat - m_.barStartBeat(bar) + 1.0);
        j["node"] = k.node >= 0 ? m_.nodes[static_cast<std::size_t>(k.node)].id : std::string("master");
        if (k.nodes.size() > 1) {
            json ids = json::array();
            for (int n : k.nodes) ids.push_back(m_.nodes[static_cast<std::size_t>(n)].id);
            j["nodes"] = ids;
        }
        j["severity"] = kSev[k.severity];
        j["inMix"] = k.inMix;
        j["jumpDb"] = r1(k.jumpDb);
        j["contrastDb"] = r1(k.contrastDb);
        j["channel"] = channelName(k.channels);
        if (!k.image.empty()) j["image"] = k.image;
        arr.push_back(j);
    }
    return arr;
}

void ReportBuilder::checkClicks() {
    if (m_.clicks.empty()) return;
    const ClickInfo& w = m_.clicks.front();
    std::vector<std::string> ids;
    bool anyBus = false, anyMaster = false;
    for (const ClickInfo& k : m_.clicks) {
        if (k.node < 0) { anyMaster = anyMaster || k.inMix; continue; }
        const auto& n = m_.nodes[static_cast<std::size_t>(k.node)];
        if (std::find(ids.begin(), ids.end(), n.id) == ids.end()) ids.push_back(n.id);
        anyBus = anyBus || n.isBus;
    }
    const std::string who = w.node >= 0 ? fmt("in '%s'", m_.nodes[static_cast<std::size_t>(w.node)].id.c_str())
                                        : std::string("in no single track (master chain or the sum)");
    const std::string worst = fmt("%s (%s) %s: a %.0f dBFS jump, %.0f dB above its surroundings", fmtTimeMs(w.sec).c_str(),
                                  m_.barBeat(w.sec).c_str(), who.c_str(), w.jumpDb, w.contrastDb);
    const int sev = w.severity == 0 ? 0 : w.inMix ? 1 : 2;
    std::string msg;
    if (m_.clicksInMix > 0) {
        msg = fmt("%d click%s/pop%s in the mix (worst %s)", m_.clicksInMix, m_.clicksInMix > 1 ? "s" : "", m_.clicksInMix > 1 ? "s" : "",
                  worst.c_str());
        if (m_.clicksMasked > 0) msg += fmt("; %d more only audible in single tracks", m_.clicksMasked);
    } else {
        msg = fmt("%d click%s in single tracks, masked in the mix (worst %s)", m_.clicksMasked, m_.clicksMasked > 1 ? "s" : "", worst.c_str());
    }
    msg += ": sample discontinuities, see report.clicks and clicks/click_01.png.";
    warn(sev, "clicks", msg, {}, ids);
    std::string fix = "Clicks are sound that starts or stops abruptly. ";
    if (!ids.empty()) fix += "In " + quoteList(ids) + ": ";
    fix += "give the instrument a short attack and release (va: \"amp.attack\" and \"amp.release\" >= 0.003 s; with \"osc.retrig\": "
           "\"on\" never attack 0), leave a small gap between touching notes of mono/legato voices or use \"glide\", shorten notes "
           "that are cut by voice stealing (fewer overlapping notes or higher \"polyphony\"), and ramp automation instead of jumping.";
    if (anyBus) fix += " A click on a bus usually comes from a track sent to it (look for the same click in that track).";
    if (anyMaster) fix += " Clicks found in no single track come from the master chain or the sum: check master fx settings.";
    fix += fmt(" Zoom in on any moment: python -m agentsound zoom songs/<slug> --at %s [--stem <id>].", fmtTimeMs(w.sec).c_str());
    suggest(fix);
}

json ReportBuilder::build() {
    m_.durationSec = static_cast<double>(m_.mixL.size()) / sr_;
    m_.refShare = m_.profile->bandShares();
    measureMix();
    buildSections();

    json report;
    report["format"] = "agentsound.report";
    report["version"] = 1;
    report["global"] = globalJson();
    report["sections"] = sectionsJson();
    report["nodes"] = nodesJson();  // also fills NodeData::dominantBand used below
    report["timeline"] = timelineJson();
    report["clicks"] = clicksJson();
    // Space (width / wetness / bed): needs the sections and the node stats above; its warnings and
    // suggestions go after the level, click and balance ones.
    std::vector<SpaceFinding> spaceFindings;
    std::vector<std::string> spaceSuggestions;
    report["space"] = assessSpace(m_, spaceFindings, spaceSuggestions);
    for (std::size_t n = 0; n < m_.nodes.size(); ++n) {
        const NodeData& nd = m_.nodes[n];
        report["nodes"][n]["role"] = roleName(nd.role);
        if (nd.role == Role::Return) report["nodes"][n]["returnKind"] = returnKindName(nd.returnKind);
    }
    // Note-level dynamics: needs the roles and the node section levels.
    std::vector<DynamicsFinding> dynFindings;
    std::vector<std::string> dynSuggestions;
    const std::vector<json> dyn = assessDynamics(m_, dynFindings, dynSuggestions);
    for (std::size_t n = 0; n < m_.nodes.size() && n < dyn.size(); ++n)
        if (!dyn[n].is_null()) report["nodes"][n]["dynamics"] = dyn[n];
    // Silent notes: notes of a track with no audible sound (and the compiler's analysis.silentNotes).
    std::vector<DynamicsFinding> silentFindings;
    std::vector<std::string> silentSuggestions;
    const std::vector<json> sil = assessSilentNotes(m_, silentFindings, silentSuggestions);
    for (std::size_t n = 0; n < m_.nodes.size() && n < sil.size(); ++n)
        if (!sil[n].is_null()) report["nodes"][n]["silentNotes"] = sil[n];
    json images = json::array();
    for (const auto& im : m_.images) images.push_back({{"file", im.file}, {"shows", im.shows}});
    report["images"] = images;
    checkSectionsAndStereo();
    checkClicks();
    checkBalance();
    checkMasking();
    for (auto& f : spaceFindings) warn(f.severity, std::move(f.code), std::move(f.message), std::move(f.sections), std::move(f.nodes));
    for (const auto& sgg : spaceSuggestions) suggest(sgg);
    for (auto& f : dynFindings) warn(f.severity, std::move(f.code), std::move(f.message), std::move(f.sections), std::move(f.nodes));
    for (const auto& sgg : dynSuggestions) suggest(sgg);
    for (auto& f : silentFindings) warn(f.severity, std::move(f.code), std::move(f.message), std::move(f.sections), std::move(f.nodes));
    for (const auto& sgg : silentSuggestions) suggest(sgg);

    const AnalysisProfile& P = *m_.profile;
    json ref;
    ref["profile"] = P.name;
    ref["name"] = P.description;
    json names = json::array();
    for (const auto& ap : analysisProfiles()) names.push_back(ap.name);
    ref["profiles"] = names;
    double refPct[kNumBands];
    for (int b = 0; b < kNumBands; ++b) refPct[b] = 100.0 * m_.refShare[static_cast<std::size_t>(b)];
    ref["bandsPct"] = bandObject(refPct);
    ref["tiltDbPerOct"] = r2(refTilt_);
    ref["lufsTarget"] = {m_.lufsMin, m_.lufsMax};
    ref["lufsTargetFrom"] = m_.loudnessOverride ? "override" : "profile";
    if (m_.loudnessOverride) ref["profileLufsTarget"] = {P.lufsMin, P.lufsMax};
    ref["truePeakMaxDbtp"] = -1.0;
    json limits = json::object();
    for (int b = 0; b < kNumBands; ++b) {
        json l = json::object();
        if (P.bandLowDb[static_cast<std::size_t>(b)]) l["low"] = *P.bandLowDb[static_cast<std::size_t>(b)];
        if (P.bandHighDb[static_cast<std::size_t>(b)]) l["high"] = *P.bandHighDb[static_cast<std::size_t>(b)];
        limits[kBandNames[b]] = l;
    }
    ref["bandLimitsDb"] = limits;
    ref["dullDb"] = P.dullDb;
    ref["tiltToleranceDbPerOct"] = P.tiltToleranceDbPerOct;
    ref["plrMinDb"] = P.plrMinDb;
    ref["lraRangeLu"] = {P.lraMinLu, P.lraMaxLu};
    ref["noteSpreadMinDb"] = P.noteSpreadMinDb;
    ref["judgeBassDynamics"] = P.judgeBassDynamics;
    report["reference"] = ref;

    std::stable_sort(warnings_.begin(), warnings_.end(), [](const Warning& a, const Warning& b) {
        return std::make_pair(a.severity, warningRank(a.code)) < std::make_pair(b.severity, warningRank(b.code));
    });
    json warns = json::array();
    static const char* kSev[] = {"error", "warn", "info"};
    m_.errors = m_.warnings = m_.infos = 0;
    m_.notes.clear();
    for (const auto& w : warnings_) {
        json j;
        j["severity"] = kSev[w.severity];
        j["code"] = w.code;
        j["message"] = w.message;
        if (!w.sections.empty()) j["sections"] = w.sections;
        if (!w.nodes.empty()) j["nodes"] = w.nodes;
        warns.push_back(j);
        m_.notes.push_back({w.severity, w.message});
        (w.severity == 0 ? m_.errors : w.severity == 1 ? m_.warnings : m_.infos)++;
    }
    report["warnings"] = warns;
    report["suggestions"] = suggestions_;

    // One-line digest for a quick read.
    std::string bal;
    for (int b = 0; b < kNumBands; ++b) bal += fmt("%s%s %+.1f", b ? ", " : "", kBandNames[b], vsRef_[static_cast<std::size_t>(b)]);
    const bool inTarget = m_.lufsI >= m_.lufsMin && m_.lufsI <= m_.lufsMax;
    const SpaceSection& sg = m_.space.global;
    std::string space = "space " + sg.verdict;
    if (sg.assessed) {
        space += fmt(" (width >150 Hz %.0f%%", sg.hiWidthPct);
        space += sg.wetLu ? fmt(", reverb %.1f LU", *sg.wetLu) : std::string(", no reverb return");
        if (sg.bedVsLeadDb) space += fmt(", bed %+.1f dB vs lead", *sg.bedVsLeadDb);
        space += ")";
    }
    std::string head = fmtTime(m_.durationSec);
    if (m_.mapped) {  // the song time when it is not one constant 4/4 tempo
        const auto [lo, hi] = bpmRange(m_.startBeat, m_.beatAt(m_.durationSec));
        head += fmt(" | tempo map %.0f..%.0f BPM", lo, hi);
    }
    if (m_.metered) {
        std::string meters;
        for (const MeterPoint& p : m_.meter.points()) {
            const std::string ms = std::to_string(p.numerator) + "/" + std::to_string(p.denominator);
            if (meters.find(ms) == std::string::npos) meters += (meters.empty() ? "" : " ") + ms;
        }
        head += " | meter " + meters;
    }
    report["summary"] = fmt("%s | profile %s | %.1f LUFS-I (target %.0f..%.0f: %s) | TP %.2f dBTP | LRA %.1f LU | corr %.2f, "
                            "width %.0f%%, lows corr %.2f | %s | tilt %.1f dB/oct (ref %.1f) | balance vs ref dB: %s | clicks %d | "
                            "%d errors, %d warnings, %d info",
                            head.c_str(), P.name.c_str(), m_.lufsI, m_.lufsMin, m_.lufsMax,
                            inTarget ? "ok" : (m_.lufsI < m_.lufsMin ? "too quiet" : "too loud"), m_.truePeakDb, m_.lra,
                            mixAgg_.corr(), mixAgg_.width(), mixAgg_.lowCorr(), space.c_str(), tilt_, refTilt_, bal.c_str(),
                            m_.clicksInMix, m_.errors, m_.warnings, m_.infos);
    report["glossary"] = {
        {"lufs", "ITU-R BS.1770-4 loudness (K-weighted); integrated, section and node values are gated"},
        {"rmsDb", "plain RMS over both channels, full-scale sine = -3.0 dBFS; for nodes: RMS while active (> -60 dBFS)"},
        {"bands", "sub 20-60, bass 60-250, lowmid 250-800, mid 800-2.5k, presence 2.5k-6k, brilliance 6k-12k, air 12k-20k Hz"},
        {"bandsPct", "share of the 20 Hz-20 kHz energy per band"},
        {"bandsVsRefDb", "band level vs the reference balance of the analysis profile (reference.profile), dB, aligned so the "
                         "median band reads 0 (+ = louder than the reference relative to the rest of the spectrum); flagged "
                         "outside reference.bandLimitsDb"},
        {"profile", "the analysis profile (render JSON \"analysis\": {\"profile\": ...}): reference balance, loudness target and "
                    "the style-dependent thresholds; reference.profiles lists them"},
        {"balanceLrDb", "left vs right energy in dB (+ = louder left); nodes: where a part sits in the stereo field"},
        {"plr", "peak-to-loudness ratio, truePeakDbtp - lufsIntegrated (8-12 typical, below reference.plrMinDb squashed)"},
        {"shortTermMax", "loudest 3 s window (LUFS); for sections only windows inside the section"},
        {"masking", "two tracks each carrying > 35 % of a band in a section (sub / bass: > 25 % each and > 70 % together); "
                    "for sub/bass the message gives the ducking between them per section: the sustained part's 10 ms "
                    "low-end energy on the transient part's hits vs between them (3+ dB = they alternate, e.g. a working "
                    "sidechain; ~0 = they hit together)"},
        {"mixSharePct", "node energy per band relative to the summed energy of all tracks (buses: relative to that same track sum)"},
        {"sharePct", "node energy relative to the summed energy of all tracks in that section"},
        {"widthPct", "side/mid energy ratio in % (0 = mono, 100 = as much side as mid)"},
        {"correlation", "L/R correlation: +1 mono, 0 wide/uncorrelated, < 0 phasey"},
        {"lowEndCorrelation", "L/R correlation below 150 Hz, should stay > 0.8"},
        {"thirdOctave", "long-term 1/3-octave spectrum minus the profile's reference curve, mean-aligned (+ = bump, - = dip)"},
        {"barsRmsDb", "node RMS per bar, same bars as timeline.rows"},
        {"bpm", "global.bpm = the tempo at the song start; with a tempo map global.bpmRange = [slowest, fastest] in the render, "
                "sections[].bpm = the section's average tempo (+ bpmStart / bpmEnd / bpmRange when it moves inside); bars follow "
                "the song's meter (global.meter, sections[].meter; 6/8 = 3 quarter-note beats per bar)"},
        {"clicks", "sample discontinuities (steps, spikes, hard cuts) that stick out of their +-30 ms neighbourhood and are not "
                   "the onset of a sound, most severe first. jumpDb = size of the jump (dBFS), contrastDb = how far its "
                   "high-frequency spike rises above the surroundings, node = the track/bus that has the same click (master = "
                   "none), inMix false = only detectable in that track (masked in the mix), bar/beat 1-based; at most 40 "
                   "are listed, global.clicks / global.clicksMasked count all"},
        {"images", "the PNGs written next to report.json and what each shows; look at them with an image viewer / the Read tool"},
        {"space", "is the mix dry / narrow / thin / lush / washy (verdict, issues): top-level values are measured over the full "
                  "sections (measuredOver: within 4 LU of the loudest, drums playing), sections[] per section; targets = the "
                  "profile's limits; warnings dry_mix, narrow_mix, washy, over_wide, thin_bed, reverb_inaudible"},
        {"widthAbove150HzPct", "side/mid energy % of the mix above 150 Hz: the stereo image that should be wide while kick and bass "
                               "stay mono (the whole-mix widthPct is dominated by the mono low end)"},
        {"musicWidthPct", "width of the music tracks together (roles bed, lead, other: no drums, bass, fx one-shots or buses)"},
        {"wetnessLu", "reverb returns vs the mix in LU (-12 = the reverb sits 12 LU below the mix); measured against the pre-master "
                      "sum of the master's inputs when the routing is known; echoLu the same for delay returns"},
        {"bedVsLeadDb", "sustained parts (role bed: long notes / steady envelopes) vs the lead, K-weighted, on the ticks where the "
                        "lead plays (-8 = the bed sits 8 dB under the lead)"},
        {"tails", "the effect returns 0.3-0.8 s after the music stops (breaks, stops, the end) vs the music before, dB; decaySec = how "
                  "long they stay within 40 dB of it"},
        {"role", "what the space assessment treats a node as: drums, bass, bed, lead, other, fx (one-shots), return (bus fed by "
                 "sends; returnKind reverb/delay/gated/width/other), group (bus fed by outputs)"},
        {"dynamics", "nodes[].dynamics: note-level dynamics of a track - every note onset (render JSON notes, chord notes within "
                     "30 ms as one; without notes: level rises in the audio) measured as its mean level over the first 30-100 ms; "
                     "spreadDb = 10-90 % spread of those levels over the song, levelDb = [p10, p90], sections[] per section; per "
                     "phrase (sections cut into ~8-bar chunks, 8+ notes): phraseSpreadDb = median audio spread, velocityPhraseDb = "
                     "the part the velocities explain (velocityDbPer10 = measured level response per 10 velocity steps, conservative: "
                     "minus one standard error, x the phrase's velocity range), dynamicsDb = the played dynamics judged: median of min(audio, velocity part) (audio only "
                     "with automatedDynamics: expression / dynamics automation, or an automated insert gain stage fx.<i>.output / gain "
                     "- e.g. hornist's breath after the compressor); flatPhrases = phrases under thresholdDb "
                     "(reference.noteSpreadMinDb); velocity = what the notes were given; kind = lead / melodic (judged; bass too "
                     "when reference.judgeBassDynamics) or bass / bed / even (arps, 8th/16th pulses: never flagged), why = how the "
                     "kind was decided; warning flat_dynamics (lead: warn, other judged parts: info)"},
        {"silentNotes", "nodes[].silentNotes: notes of a track that made no audible sound (analysis/SilentNotes.h) - notes = the "
                        "judged notes, events = the same with chord notes (within 30 ms) as one; each event's level = the loudest 10 ms "
                        "in its own span (start .. min(end + 0.25 s, start + 3 s, the next event)); medianDb = the track's median event "
                        "level, thresholdDb = max(median - 40, min(-60, median - 30)) for notes that add nothing to what sounded before them "
                        "(notes with an attack of their own: median - 40); silent = notes of the events under it (at = their "
                        "bar:beat, pitches), excused = silent ones while an automation lane had closed the level or on a vocoder "
                        "carrier (excusedBy), "
                        "compileSilent = notes the compiler found no sample / layer for (render JSON analysis.silentNotes); warning "
                        "silent_notes"},
        {"-120", "floor value meaning silence"}};
    return report;
}

}  // namespace

// ------------------------------------------------------------------ MixAnalyzer

MixAnalyzer::MixAnalyzer() : impl_(std::make_unique<analysis::MixImpl>()) {}
MixAnalyzer::~MixAnalyzer() = default;
MixAnalyzer::MixAnalyzer(MixAnalyzer&&) noexcept = default;
MixAnalyzer& MixAnalyzer::operator=(MixAnalyzer&&) noexcept = default;

void MixAnalyzer::prepare(double sampleRate, double bpm, std::vector<SectionMarker> sections, double totalSecondsHint) {
    if (!(sampleRate >= 8000.0 && sampleRate <= 384000.0)) throw std::invalid_argument("MixAnalyzer: sample rate out of range");
    impl_ = std::make_unique<analysis::MixImpl>();
    auto& m = *impl_;
    m.sampleRate = sampleRate;
    m.bpm = (std::isfinite(bpm) && bpm > 0.0) ? bpm : 120.0;
    m.tickLen = std::max(1, static_cast<int>(std::lround(sampleRate / 10.0)));
    m.setup = std::make_unique<analysis::SpectralSetup>(sampleRate);
    // Effective sections (a whole-song pseudo-section when none are given), sorted by start.
    for (auto& s : sections) {
        if (!std::isfinite(s.startSec) || !std::isfinite(s.endSec) || s.endSec <= s.startSec) continue;
        analysis::SectionData d;
        d.name = s.name;
        d.startSec = std::max(0.0, s.startSec);
        d.endSec = s.endSec;
        m.sections.push_back(d);
        m.boundaries.push_back(std::llround(d.startSec * sampleRate));
        m.boundaries.push_back(std::llround(d.endSec * sampleRate));
    }
    std::stable_sort(m.sections.begin(), m.sections.end(), [](const auto& a, const auto& b) { return a.startSec < b.startSec; });
    const double hint = std::clamp(std::isfinite(totalSecondsHint) ? totalSecondsHint : 0.0, 0.0, 1800.0);
    const auto reserveFrames = static_cast<std::size_t>(hint * sampleRate) + 1024;
    m.mixL.reserve(reserveFrames);
    m.mixR.reserve(reserveFrames);
    m.prepared = true;
}

void MixAnalyzer::setProfile(const std::string& name) {
    auto& m = *impl_;
    if (m.finished) throw std::logic_error("MixAnalyzer::setProfile after finish");
    const analysis::AnalysisProfile* p = analysis::findAnalysisProfile(name);
    if (!p) throw std::invalid_argument("unknown analysis profile '" + name + "' (profiles: " + analysis::analysisProfileNames() + ")");
    m.profile = p;
    if (!m.loudnessOverride) {
        m.lufsMin = p->lufsMin;
        m.lufsMax = p->lufsMax;
    }
}

void MixAnalyzer::setLoudnessTarget(double minLufs, double maxLufs) {
    auto& m = *impl_;
    if (m.finished) throw std::logic_error("MixAnalyzer::setLoudnessTarget after finish");
    if (!(std::isfinite(minLufs) && std::isfinite(maxLufs) && minLufs < maxLufs))
        throw std::invalid_argument("MixAnalyzer: loudness target min must be < max");
    m.lufsMin = minLufs;
    m.lufsMax = maxLufs;
    m.loudnessOverride = true;
}

void MixAnalyzer::setStartBeat(double beat) {
    auto& m = *impl_;
    if (m.fed) throw std::logic_error("MixAnalyzer::setStartBeat after feeding started");
    m.startBeat = std::isfinite(beat) ? beat : 0.0;
    m.startSample = m.tempo.sampleAt(m.startBeat);
    for (auto& n : m.nodes) n.stats->setBoundaries(m.boundaries, m.barGrid());  // bar grid moved
}

void MixAnalyzer::setTimeGrid(const TempoMap& tempo, const MeterMap& meter) {
    auto& m = *impl_;
    if (m.fed) throw std::logic_error("MixAnalyzer::setTimeGrid after feeding started");
    m.tempo = tempo;
    m.meter = meter;
    m.mapped = !tempo.constant();
    m.metered = !meter.plain();
    m.startSample = m.tempo.sampleAt(m.startBeat);
    for (auto& n : m.nodes) n.stats->setBoundaries(m.boundaries, m.barGrid());
}

int MixAnalyzer::addNode(const std::string& id, bool isBus) {
    auto& m = *impl_;
    if (!m.prepared) throw std::logic_error("MixAnalyzer::addNode before prepare");
    if (m.fed) throw std::logic_error("MixAnalyzer::addNode after feeding started (node timelines would not line up)");
    analysis::NodeData node;
    node.id = id;
    node.isBus = isBus;
    const std::size_t reserveTicks = m.mixL.capacity() / static_cast<std::size_t>(m.tickLen) + 2;
    node.stats = std::make_unique<analysis::StreamStats>(*m.setup, m.tickLen, reserveTicks, false, true);
    node.stats->setBoundaries(m.boundaries, m.barGrid());
    analysis::ClickDetector::Settings cs;
    cs.snippetHalf = static_cast<int>(std::lround(0.015 * m.sampleRate));  // +-15 ms around each click for the images
    node.clicks = std::make_unique<analysis::ClickDetector>(m.sampleRate, cs);
    if (!isBus)
        node.env = std::make_unique<analysis::OnsetEnvelope>(m.sampleRate, static_cast<double>(m.mixL.capacity()) / m.sampleRate);
    m.nodes.push_back(std::move(node));
    return static_cast<int>(m.nodes.size()) - 1;
}

void MixAnalyzer::setNodeRouting(int node, NodeRouting routing) {
    auto& m = *impl_;
    if (node < 0 || node >= static_cast<int>(m.nodes.size())) throw std::out_of_range("MixAnalyzer::setNodeRouting: bad node index");
    if (m.finished) throw std::logic_error("MixAnalyzer::setNodeRouting after finish");
    auto& n = m.nodes[static_cast<std::size_t>(node)];
    n.routing = std::move(routing);
    n.hasRouting = true;
}

void MixAnalyzer::feedNode(int node, const float* left, const float* right, int frames) {
    auto& m = *impl_;
    if (node < 0 || node >= static_cast<int>(m.nodes.size())) throw std::out_of_range("MixAnalyzer::feedNode: bad node index");
    if (frames <= 0 || m.finished) return;
    m.fed = true;
    auto& n = m.nodes[static_cast<std::size_t>(node)];
    n.stats->feed(left, right, frames);
    n.clicks->feed(left, right, frames);
    if (n.env) n.env->feed(left, right, frames);
}

void MixAnalyzer::feedMix(const float* left, const float* right, int frames) {
    auto& m = *impl_;
    if (!m.prepared) throw std::logic_error("MixAnalyzer::feedMix before prepare");
    if (frames <= 0 || m.finished) return;
    m.fed = true;
    m.mixL.insert(m.mixL.end(), left, left + frames);
    m.mixR.insert(m.mixR.end(), right, right + frames);
}

json MixAnalyzer::finish() {
    auto& m = *impl_;
    if (!m.prepared) throw std::logic_error("MixAnalyzer::finish before prepare");
    if (m.finished) return m.report;
    for (auto& n : m.nodes) {
        n.stats->finalize();
        if (n.env) n.env->finalize();
    }
    // Sanitise the stored mix (NaN/Inf -> 0, counted by the stream below) so every measure stays finite.
    const std::size_t numTicks = (m.mixL.size() + static_cast<std::size_t>(m.tickLen) - 1) / static_cast<std::size_t>(m.tickLen);
    m.mix = std::make_unique<analysis::StreamStats>(*m.setup, m.tickLen, numTicks + 1, true);
    m.mix->setBoundaries(m.boundaries, m.barGrid());
    constexpr std::size_t kChunk = 8192;
    for (std::size_t i = 0; i < m.mixL.size(); i += kChunk) {
        const int n = static_cast<int>(std::min(kChunk, m.mixL.size() - i));
        m.mix->feed(m.mixL.data() + i, m.mixR.data() + i, n);
    }
    m.mix->finalize();
    for (std::size_t i = 0; i < m.mixL.size(); ++i) {
        if (!(std::fabs(m.mixL[i]) < 1e30f)) m.mixL[i] = 0.0f;
        if (!(std::fabs(m.mixR[i]) < 1e30f)) m.mixR[i] = 0.0f;
    }
    const double duration = static_cast<double>(m.mixL.size()) / m.sampleRate;
    if (m.sections.empty()) {
        analysis::SectionData d;
        d.name = "song";
        d.endSec = duration;
        d.implicit = true;
        m.sections.push_back(d);
    }
    m.durationSec = duration;
    analyseClicks(m);
    planImages(m);
    ReportBuilder builder(m);
    m.report = builder.build();
    m.finished = true;
    return m.report;
}

void MixAnalyzer::writeSpectrogramPng(const std::string& path) const {
    if (!impl_->finished) throw std::logic_error("MixAnalyzer::writeSpectrogramPng before finish");
    analysis::renderSpectrogram(*impl_, path);
}

void MixAnalyzer::writeOverviewPng(const std::string& path) const {
    if (!impl_->finished) throw std::logic_error("MixAnalyzer::writeOverviewPng before finish");
    analysis::renderOverview(*impl_, path);
}

// ------------------------------------------------------------------ report formatting

namespace {
bool allScalars(const json& j) {
    for (const auto& e : j)
        if (e.is_structured()) return false;
    return true;
}

// Keys in reading order: the digest and the problems first, identifiers first inside entries;
// everything else alphabetical.
int keyRank(const std::string& key, int depth) {
    static const char* kTop[] = {"format", "version", "summary", "render", "warnings", "suggestions", "space", "clicks", "images",
                                 "global", "sections", "nodes", "timeline", "reference", "glossary"};
    static const char* kInner[] = {"severity", "code", "message", "profile", "id", "name", "section", "verdict", "issues", "full",
                                   "time", "bar", "beat", "node", "file", "bus", "role", "implicit"};
    const auto find = [&](const auto& list) {
        for (std::size_t i = 0; i < std::size(list); ++i)
            if (key == list[i]) return static_cast<int>(i);
        return 1000;
    };
    return depth == 0 ? find(kTop) : find(kInner);
}

std::vector<json::const_iterator> orderedMembers(const json& j, int depth) {
    std::vector<json::const_iterator> v;
    for (auto it = j.cbegin(); it != j.cend(); ++it) v.push_back(it);
    std::stable_sort(v.begin(), v.end(), [depth](const auto& a, const auto& b) { return keyRank(a.key(), depth) < keyRank(b.key(), depth); });
    return v;
}

void emitCompact(std::string& out, const json& j, int depth) {
    if (j.is_object()) {
        out += '{';
        bool first = true;
        for (const auto& it : orderedMembers(j, depth)) {
            if (!first) out += ',';
            first = false;
            out += json(it.key()).dump() + ':';
            emitCompact(out, it.value(), depth + 1);
        }
        out += '}';
    } else if (j.is_array()) {
        out += '[';
        for (std::size_t i = 0; i < j.size(); ++i) {
            if (i) out += ',';
            emitCompact(out, j[i], depth + 1);
        }
        out += ']';
    } else {
        out += j.dump();
    }
}

// One line for: scalars, short values, arrays of scalars (timeline rows, per-bar values) and objects
// whose members are scalars or short scalar lists with at most one long text (warnings, per-section
// entries). Text maps such as the glossary get one line per entry.
bool printFlat(const json& j, std::size_t compactSize) {
    if (!j.is_structured() || compactSize <= 100) return true;
    int longTexts = 0;
    for (const auto& e : j) {
        if (e.is_structured() && (j.is_array() || !(e.is_array() && e.size() <= 8 && allScalars(e)))) return false;
        if (e.is_string() && e.get_ref<const std::string&>().size() > 40) ++longTexts;
    }
    return longTexts <= 1;  // lists of sentences (suggestions) and text maps (glossary): one per line
}

void emitJson(std::string& out, const json& j, int depth) {
    std::string compact;
    emitCompact(compact, j, depth);
    if (printFlat(j, compact.size())) { out += compact; return; }
    const std::string pad(static_cast<std::size_t>(depth) * 2 + 2, ' '), end(static_cast<std::size_t>(depth) * 2, ' ');
    std::size_t i = 0;
    if (j.is_array()) {
        out += "[\n";
        for (const auto& e : j) {
            out += pad;
            emitJson(out, e, depth + 1);
            out += ++i < j.size() ? ",\n" : "\n";
        }
        out += end + "]";
    } else {
        out += "{\n";
        for (const auto& it : orderedMembers(j, depth)) {
            out += pad + json(it.key()).dump() + ": ";
            emitJson(out, it.value(), depth + 1);
            out += ++i < j.size() ? ",\n" : "\n";
        }
        out += end + "}";
    }
}
}  // namespace

std::string formatReport(const json& report) {
    std::string out;
    emitJson(out, report, 0);
    out += "\n";
    return out;
}

void MixAnalyzer::writeImages(const std::string& dir) const {
    namespace fs = std::filesystem;
    const auto& m = *impl_;
    if (!m.finished) throw std::logic_error("MixAnalyzer::writeImages before finish");
    // Images of an earlier render with other sections / more clicks would be stale: remove them.
    std::error_code ec;
    auto starts = [](const std::string& s, const char* p) { return s.rfind(p, 0) == 0; };
    // Collected first, removed afterwards: removing entries while iterating a directory is unspecified.
    std::vector<fs::path> stale;
    for (const auto& e : fs::directory_iterator(dir, ec)) {
        const std::string name = e.path().filename().string();
        if (starts(name, "spectrogram_") && e.path().extension() == ".png") stale.push_back(e.path());
    }
    const fs::path clickDir = fs::path(dir) / "clicks";
    for (const auto& e : fs::directory_iterator(clickDir, ec)) {
        const std::string name = e.path().filename().string();
        if (starts(name, "click_") && e.path().extension() == ".png") stale.push_back(e.path());
    }
    for (const auto& p : stale) fs::remove(p, ec);
    analysis::renderOverview(m, dir + "/overview.png");
    analysis::renderLoudness(m, dir + "/loudness.png");
    analysis::renderTracks(m, dir + "/tracks.png");
    analysis::renderBands(m, dir + "/bands.png");
    analysis::renderStereo(m, dir + "/stereo.png");
    analysis::renderSpectrograms(m, dir, true, true);
    bool anyClickImage = false;
    for (const auto& k : m.clicks) anyClickImage = anyClickImage || !k.image.empty();
    if (anyClickImage) {
        fs::create_directories(clickDir);
        for (std::size_t i = 0; i < m.clicks.size(); ++i)
            if (!m.clicks[i].image.empty()) analysis::renderClickImage(m, i, dir + "/" + m.clicks[i].image);
    }
}

}  // namespace as
