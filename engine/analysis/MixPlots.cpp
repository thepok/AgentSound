// The report images that follow the song timeline: overview.png (dashboard + index),
// loudness.png, tracks.png, bands.png and stereo.png. All share PlotKit's frame (1600 px wide, the
// same x for the same time in every image), header (sections + bars) and time axis.

#include "analysis/Canvas.h"
#include "analysis/Loudness.h"
#include "analysis/MixImpl.h"
#include "analysis/PlotKit.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

namespace as::analysis {

namespace {

TimeMap songMap(const MixImpl& m) { return TimeMap{kPlotX0, kPlotX1, 0.0, std::max(m.durationSec, 1e-3)}; }

int yLin(double v, double top, double bottom, int y0, int h) {
    return y0 + static_cast<int>(std::lround((top - std::clamp(v, std::min(top, bottom), std::max(top, bottom))) / (top - bottom) * (h - 1)));
}

// RMS level (dBFS) of a stream per plot column.
std::vector<double> levelColumns(const MixImpl& m, const StreamStats& st, const TimeMap& tm) {
    std::vector<double> out(static_cast<std::size_t>(tm.width()), kDbFloor);
    for (int col = 0; col < tm.width(); ++col) {
        const TickSpan sp = ticksFor(st, m.tickSec(), tm.t0 + col * tm.pxSec(), tm.t0 + (col + 1) * tm.pxSec());
        double e = 0.0, f = 0.0;
        for (std::size_t i = sp.i0; i < sp.i1; ++i) { e += st.ticks()[i].energy(); f += st.tickFrames(i); }
        if (f > 0) out[static_cast<std::size_t>(col)] = dbFromPower(e / (2.0 * f));
    }
    return out;
}

// Momentary (max within the column) and short-term (at the column centre) loudness per column.
void loudnessColumns(const MixImpl& m, const TimeMap& tm, std::vector<double>& mo, std::vector<double>& st) {
    const auto cols = static_cast<std::size_t>(tm.width());
    mo.assign(cols, kDbFloor);
    st.assign(cols, kDbFloor);
    if (!m.mix || m.momentary.empty()) return;
    for (std::size_t col = 0; col < cols; ++col) {
        const double t0 = tm.t0 + static_cast<double>(col) * tm.pxSec(), t1 = t0 + tm.pxSec();
        const TickSpan sp = ticksFor(*m.mix, m.tickSec(), t0, t1);
        double mMax = kDbFloor;
        for (std::size_t i = sp.i0; i < sp.i1 && i < m.momentary.size(); ++i) mMax = std::max(mMax, static_cast<double>(m.momentary[i]));
        mo[col] = mMax;
        st[col] = m.shortTerm[std::min(m.shortTerm.size() - 1, static_cast<std::size_t>((t0 + t1) * 0.5 / m.tickSec()))];
    }
}

// Loudness panel: target band, grid, section averages, momentary (thin cyan), short-term (amber),
// integrated (dashed). Labels on the right every labelStep LU.
void drawLoudnessPanel(Canvas& c, const MixImpl& m, const TimeMap& tm, int y0, int h, double top, double bottom, double labelStep,
                       bool sectionLabels) {
    c.fillRect(tm.x0, y0, tm.x1, y0 + h, kPanel);
    auto yOf = [&](double l) { return yLin(l, top, bottom, y0, h); };
    c.blendRect(tm.x0, yOf(m.lufsMax), tm.x1, yOf(m.lufsMin) + 1, kGreen, 0.18);
    for (double l = std::ceil(bottom / 3.0) * 3.0; l < top; l += 3.0) {
        const int y = yOf(l);
        const bool major = std::fmod(-l + 1e-9, labelStep) < 1e-6;
        c.dashedHline(tm.x0, tm.x1 - 1, y, kWhite, 2, 4, major ? 0.16 : 0.07);
        if (major) c.text(tm.x1 + 8, y - 8, sfmt("%.0f", l), kDim, 2);
    }
    std::vector<double> mo, st;
    loudnessColumns(m, tm, mo, st);
    for (int col = 1; col < tm.width(); ++col) {
        const auto a = static_cast<std::size_t>(col - 1), b = static_cast<std::size_t>(col);
        if (mo[a] > bottom || mo[b] > bottom) c.line(tm.x0 + col - 1, yOf(mo[a]), tm.x0 + col, yOf(mo[b]), kCyan, 1, 0.7);
    }
    for (int col = 1; col < tm.width(); ++col) {
        const auto a = static_cast<std::size_t>(col - 1), b = static_cast<std::size_t>(col);
        if (st[a] > bottom || st[b] > bottom) c.line(tm.x0 + col - 1, yOf(st[a]), tm.x0 + col, yOf(st[b]), kAmber, 3);
    }
    if (m.lufsI > bottom) c.dashedHline(tm.x0, tm.x1 - 1, yOf(m.lufsI), kWhite, 8, 4, 0.9);
    for (const auto& sec : m.sections) {
        if (sec.lufs <= bottom || sec.implicit) continue;
        const int y = yOf(sec.lufs);
        const int xa = std::clamp(tm.xi(sec.startSec), tm.x0, tm.x1 - 1), xb = std::clamp(tm.xi(sec.endSec), tm.x0, tm.x1 - 1);
        c.hline(xa + 2, xb - 2, y, kWhite, 0.8);
        c.hline(xa + 2, xb - 2, y + 1, kWhite, 0.8);
        if (!sectionLabels) continue;
        const std::string l1 = sfmt("%.1f", sec.lufs), l2 = sfmt("max %.1f", sec.stMax);
        const int room = xb - xa - 10;
        const int ty = y - 24 >= y0 + 2 ? y - 24 : y + 6;
        if (Canvas::textWidth(l1 + "  " + l2, 2) <= room) {
            textBox(c, xa + 6, ty, l1, kText);
            textBox(c, xa + 6 + Canvas::textWidth(l1 + "  ", 2), ty, l2, kAmber);
        } else if (Canvas::textWidth(l1, 2) <= room) {
            textBox(c, xa + 6, ty, l1, kText);
        }
    }
}

// Waveform of one channel: min/max envelope (dark) with RMS (light), clipped columns red.
void drawWaveformLane(Canvas& c, const MixImpl& m, const TimeMap& tm, const std::vector<float>& x, int y0, int h, bool dbGrid) {
    c.fillRect(tm.x0, y0, tm.x1, y0 + h, kPanel);
    const int yc = y0 + h / 2;
    const double amp = h / 2.0 - 2.0;
    c.hline(tm.x0, tm.x1 - 1, yc, kGrid);
    if (dbGrid) {
        for (double db : {-6.0, -12.0}) {
            const double a = std::pow(10.0, db / 20.0);
            c.dashedHline(tm.x0, tm.x1 - 1, static_cast<int>(std::lround(yc - a * amp)), kWhite, 2, 5, 0.14);
            c.dashedHline(tm.x0, tm.x1 - 1, static_cast<int>(std::lround(yc + a * amp)), kWhite, 2, 5, 0.14);
        }
    }
    const auto n = static_cast<std::int64_t>(x.size());
    const double pxSec = tm.pxSec();
    for (int col = 0; col < tm.width(); ++col) {
        const auto s0 = static_cast<std::int64_t>((tm.t0 + col * pxSec) * m.sampleRate);
        const auto s1 = std::max(s0 + 1, static_cast<std::int64_t>((tm.t0 + (col + 1) * pxSec) * m.sampleRate));
        if (s0 >= n) break;
        float lo = 0.0f, hi = 0.0f;
        double sq = 0.0;
        bool clip = false;
        const std::int64_t e = std::min(s1, n);
        for (std::int64_t i = s0; i < e; ++i) {
            const float v = x[static_cast<std::size_t>(i)];
            lo = std::min(lo, v);
            hi = std::max(hi, v);
            sq += static_cast<double>(v) * v;
            clip = clip || std::fabs(v) >= 1.0f;
        }
        const double rms = std::sqrt(sq / static_cast<double>(std::max<std::int64_t>(1, e - s0)));
        const int X = tm.x0 + col;
        c.vline(X, static_cast<int>(std::lround(yc - std::min(1.0f, hi) * amp)), static_cast<int>(std::lround(yc - std::max(-1.0f, lo) * amp)),
                kWavePeak);
        c.vline(X, static_cast<int>(std::lround(yc - std::min(1.0, rms) * amp)), static_cast<int>(std::lround(yc + std::min(1.0, rms) * amp)),
                kWaveRms);
        if (clip) c.fillRect(X, y0 + 1, X + 1, y0 + h - 1, kRed);
    }
}

// Per-column band energies of the mix over a window (seconds) centred on each column.
void bandColumns(const MixImpl& m, const TimeMap& tm, double window, std::vector<std::array<double, kNumBands>>& out,
                 std::vector<double>& levelDb) {
    const auto cols = static_cast<std::size_t>(tm.width());
    out.assign(cols, {});
    levelDb.assign(cols, kDbFloor);
    if (!m.mix) return;
    for (std::size_t col = 0; col < cols; ++col) {
        const double tc = tm.t0 + (static_cast<double>(col) + 0.5) * tm.pxSec();
        const TickSpan sp = ticksFor(*m.mix, m.tickSec(), tc - window * 0.5, tc + window * 0.5);
        double frames = 0.0, total = 0.0;
        for (std::size_t i = sp.i0; i < sp.i1; ++i) {
            for (int b = 0; b < kNumBands; ++b) out[col][static_cast<std::size_t>(b)] += m.mix->ticks()[i].band[b];
            frames += m.mix->tickFrames(i);
        }
        for (double v : out[col]) total += v;
        if (frames > 0) levelDb[col] = dbFromPower(total / (2.0 * frames));
    }
}

Rgb corrColor(double c) { return c < 0.0 ? kRed : c < 0.2 ? kAmber : rgbHex(0x4fb3ff); }

// ------------------------------------------------------------------ space (Space.h)

constexpr Rgb kViolet = rgbHex(0xc77dff);

Rgb verdictColor(const std::string& v) {
    if (v == "lush") return kGreen;
    if (v == "ok") return rgbHex(0x7f9cc0);
    if (v == "dry") return kAmber;
    if (v == "narrow") return kCyan;
    if (v == "washy") return kViolet;
    return kGrid;
}

// "dry" / "narrow" / ... plus the numbers that decided it, in decreasing length (w = width above
// 150 Hz, rev = reverb returns vs the mix in LU, bed = bed vs lead in dB).
std::vector<std::string> spaceLabels(const SpaceSection& sp) {
    const std::string wet = sp.wetLu ? sfmt(" rev%.0f", *sp.wetLu) : std::string(" norev");
    const std::string bed = sp.bedVsLeadDb ? sfmt(" bed%+.0f", *sp.bedVsLeadDb) : std::string();
    const std::string w = sfmt(" w%.0f%%", sp.hiWidthPct);
    const std::string key = sp.verdict == "narrow" ? w : (sp.verdict == "dry" || sp.verdict == "washy") ? wet : std::string();
    return {sp.verdict + w + wet + bed, sp.verdict + w + wet, sp.verdict + key, sp.verdict, sp.verdict.substr(0, 1)};
}

// One cell per section, coloured by the space verdict (full sections stronger), with its numbers.
void drawSpaceStrip(Canvas& c, const MixImpl& m, const TimeMap& tm, int y0, int h) {
    c.fillRect(tm.x0, y0, tm.x1, y0 + h, kPanel);
    const SpaceData& S = m.space;
    for (std::size_t s = 0; s < m.sections.size() && s < S.sections.size(); ++s) {
        const SectionData& sec = m.sections[s];
        const SpaceSection& sp = S.sections[s];
        if (!sp.assessed) continue;
        const int xa = std::clamp(tm.xi(sec.startSec), tm.x0, tm.x1), xb = std::clamp(tm.xi(sec.endSec), tm.x0, tm.x1);
        if (xb - xa < 3) continue;
        c.blendRect(xa + 1, y0 + 2, xb - 1, y0 + h - 2, verdictColor(sp.verdict), sp.full ? 0.5 : 0.25);
        const int scale = h >= 20 ? 2 : 1;
        for (const auto& t : spaceLabels(sp)) {
            if (Canvas::textWidth(t, scale) > xb - xa - 8) continue;
            c.text(xa + 5, y0 + (h - 9 * scale) / 2, t, kText, scale);
            break;
        }
    }
}

// Reverb (and echo) returns vs the reference (pre-master sum, else the mix) over a window per column, LU.
void wetColumns(const MixImpl& m, const TimeMap& tm, double window, std::vector<double>& rev, std::vector<double>& echo) {
    const auto cols = static_cast<std::size_t>(tm.width());
    rev.assign(cols, kDbFloor);
    echo.assign(cols, kDbFloor);
    const SpaceData& S = m.space;
    if (!m.mix || (S.reverbReturns.empty() && S.delayReturns.empty())) return;
    auto sumK = [&](int node, std::size_t i0, std::size_t i1) {
        const auto& tk = m.nodes[static_cast<std::size_t>(node)].stats->ticks();
        double k = 0.0;
        for (std::size_t i = i0; i < i1 && i < tk.size(); ++i) k += tk[i].k;
        return k;
    };
    for (std::size_t col = 0; col < cols; ++col) {
        const double tc = tm.t0 + (static_cast<double>(col) + 0.5) * tm.pxSec();
        const TickSpan sp = ticksFor(*m.mix, m.tickSec(), tc - window * 0.5, tc + window * 0.5);
        double ref = 0.0;
        if (!S.refNodes.empty()) {
            for (int n : S.refNodes) ref += sumK(n, sp.i0, sp.i1);
        } else {
            for (std::size_t i = sp.i0; i < sp.i1; ++i) ref += m.mix->ticks()[i].k;
        }
        if (!(ref > 0.0)) continue;
        double r = 0.0, e = 0.0;
        for (int n : S.reverbReturns) r += sumK(n, sp.i0, sp.i1);
        for (int n : S.delayReturns) e += sumK(n, sp.i0, sp.i1);
        if (r > 0.0) rev[col] = 10.0 * std::log10(r / ref);
        if (e > 0.0) echo[col] = 10.0 * std::log10(e / ref);
    }
}

std::string spaceLine(const MixImpl& m) {
    const SpaceSection& g = m.space.global;
    const AnalysisProfile& P = *m.profile;
    if (!g.assessed) return "SPACE: not assessed (silent)";
    std::string s = sfmt("SPACE %s: width >150 Hz %.0f%% (%.0f..%.0f)", g.verdict.c_str(), g.hiWidthPct, P.widthMinPct, P.widthMaxPct);
    if (g.musicWidthPct) s += sfmt(", music %.0f%%", *g.musicWidthPct);
    s += g.wetLu ? sfmt(" | reverb %.1f LU (%.0f..%.0f)", *g.wetLu, P.wetMinLu, P.wetMaxLu) : std::string(" | no reverb return");
    if (g.echoLu) s += sfmt(" | echo %.0f LU", *g.echoLu);
    if (g.bedVsLeadDb) s += sfmt(" | bed %+.1f dB", *g.bedVsLeadDb);
    if (m.space.tailDb) s += sfmt(" | tails %.0f dB", *m.space.tailDb);
    return s;
}

}  // namespace

// ------------------------------------------------------------------ overview.png

void renderOverview(const MixImpl& m, const std::string& path) {
    const TimeMap tm = songMap(m);
    const int nNodes = static_cast<int>(m.nodes.size());
    const int laneH = nNodes ? std::clamp(260 / nNodes, 14, 26) : 24;  // compact: tracks.png has the big lanes
    const int loudH = 160, eventsH = 22, spaceH = 24;
    const int yLoud = kPlotTop, yEvents = yLoud + loudH + 8, ySpace = yEvents + eventsH + 6, yNodesCap = ySpace + spaceH + 10;
    const int yNodes = yNodesCap + 26;
    const int yEnd = yNodes + std::max(1, nNodes) * laneH;
    const int yNums = yEnd + kAxisH + 10;

    // Top issues (at most 8 lines, <= 2 per issue) and the image index below the plots.
    constexpr int kNoteX = 8 + 7 * 12, kMaxNoteLines = 8;
    std::vector<std::pair<int, std::vector<std::string>>> notes;
    int noteLines = 0;
    for (std::size_t i = 0; i < m.notes.size(); ++i) {
        auto lines = wrapText(m.notes[i].second, kImageW - 8 - kNoteX, 2, 2);
        if (noteLines + static_cast<int>(lines.size()) > kMaxNoteLines) break;
        noteLines += static_cast<int>(lines.size());
        notes.push_back({std::clamp(m.notes[i].first, 0, 2), std::move(lines)});
    }
    std::vector<std::pair<std::string, std::string>> index = {
        {"loudness.png", "waveform + loudness curves, section table"},
        {"tracks.png", "level of each track/bus, section values"},
        {"bands.png", "band balance over time vs reference"},
        {"stereo.png", "correlation, width, wetness, mono check, field"},
        {"spectrogram.png", "whole song, fixed colour scale"}};
    if (!m.zooms.empty()) {
        std::string names;
        for (const auto& z : m.zooms) names += (names.empty() ? "" : ", ") + z.name;
        index.push_back({m.zooms.size() == 1 ? m.zooms[0].file : sfmt("spectrogram_01..%02d_*.png", static_cast<int>(m.zooms.size())),
                         "zoom per section: " + names});
    }
    std::size_t clickImages = 0;
    for (const auto& k : m.clicks) clickImages += k.image.empty() ? 0 : 1;
    if (clickImages)
        index.push_back({clickImages == 1 ? std::string("clicks/click_01.png") : sfmt("clicks/click_01..%02d.png", static_cast<int>(clickImages)),
                         "sample-accurate zoom per click"});
    const int yNotes = yNums + 3 * kLine + 12;
    const int notesH = notes.empty() ? 0 : 28 + noteLines * kLine + static_cast<int>(notes.size() - 1) * 4;
    const int yIndex = yNotes + notesH + 10;
    const int indexRows = static_cast<int>((index.size() + 1) / 2);  // two columns
    const int H = yIndex + 28 + indexRows * kLine + 8;
    Canvas c(kImageW, H, kBg);

    const Rgb headCol = m.errors ? kRed : m.warnings ? kText : kGreen;
    drawTitle(c, "OVERVIEW", sfmt("%s | %.1f LUFS-I (%s target %.0f..%.0f) | TP %.2f dBTP | LRA %.1f LU | %d click%s | %d errors, "
                                  "%d warnings, %d info", mmss(m.durationSec).c_str(), m.lufsI,
                                  m.loudnessOverride ? "override" : m.profile->name.c_str(), m.lufsMin, m.lufsMax,
                                  m.truePeakDb, m.lra, m.clicksInMix,
                                  m.clicksInMix == 1 ? "" : "s", m.errors, m.warnings, m.infos), headCol);
    drawTimeHeader(c, m, tm);
    drawClickMarkers(c, m, tm, 78);

    // Loudness.
    drawLoudnessPanel(c, m, tm, yLoud, loudH, 0.0, -48.0, 12.0, false);
    caption(c, 8, yLoud + 4, {{"LOUDNESS LUFS", kText}, {"short-term 3s", kAmber}, {"momentary 0.4s", kCyan},
                              {"-- integrated", kText}, {"== section avg", kDim}});
    c.text(8, yLoud + 4 + 5 * kLine, sfmt("target %.0f..%.0f", m.lufsMin, m.lufsMax), kGreen, 2);
    c.text(8, yLoud + 4 + 6 * kLine, sfmt("(%s)", m.loudnessOverride ? "override" : m.profile->name.c_str()), kDim, 2);

    // Events: clicks and clipping.
    {
        c.fillRect(tm.x0, yEvents, tm.x1, yEvents + eventsH, kPanel);
        c.text(8, yEvents + 3, "EVENTS", kText, 2);
        const double pxSec = tm.pxSec();
        const auto n = static_cast<std::int64_t>(m.mixL.size());
        int clipCols = 0;
        for (int col = 0; col < tm.width(); ++col) {
            const auto s0 = static_cast<std::int64_t>(col * pxSec * m.sampleRate);
            const auto s1 = std::min(n, static_cast<std::int64_t>((col + 1) * pxSec * m.sampleRate));
            bool clip = false;
            for (std::int64_t i = s0; i < s1 && !clip; ++i)
                clip = std::fabs(m.mixL[static_cast<std::size_t>(i)]) >= 1.0f || std::fabs(m.mixR[static_cast<std::size_t>(i)]) >= 1.0f;
            if (clip) { c.fillRect(tm.x0 + col, yEvents + 2, tm.x0 + col + 1, yEvents + eventsH - 2, kRed); ++clipCols; }
        }
        const std::string what = m.clicks.empty() && clipCols == 0
                                     ? std::string("no clicks, no clipping")
                                     : sfmt("clicks: %d in the mix (red), %d masked in single parts (amber)%s", m.clicksInMix,
                                            m.clicksMasked, clipCols ? "; clipping = red bars" : "");
        for (const auto& k : m.clicks) {
            const int x = tm.xi(k.sec);
            c.fillRect(x - 1, yEvents + 1, x + 2, yEvents + eventsH - 1, k.inMix ? kRed : kAmber);
        }
        // The legend stays readable over dense markers (they are repeated under the bar numbers and in the lanes).
        textBox(c, tm.x0 + 8, yEvents + 3, what, kDim, 2, 0.8);
        c.text(tm.x1 + 8, yEvents + 3, sfmt("%d click%s", m.clicksInMix, m.clicksInMix == 1 ? "" : "s"), m.clicksInMix ? kRed : kDim, 2);
    }

    // Space: verdict per section (dry / narrow / ok / lush / washy) with width, reverb and bed numbers.
    {
        drawSpaceStrip(c, m, tm, ySpace, spaceH);
        c.text(8, ySpace + 3, "SPACE", kText, 2);
        c.text(tm.x1 + 8, ySpace + 3, fitText(m.space.global.verdict, kImageW - tm.x1 - 12, 2), verdictColor(m.space.global.verdict), 2);
    }

    // Tracks and buses: one lane per node, colour = RMS level; swatch = dominant band.
    {
        constexpr double kLo = -60.0, kHi = 0.0;
        const int scale = laneH >= 18 ? 2 : 1;
        c.text(8, yNodesCap + 4, "TRACKS", kText, 2);
        c.text(8 + Canvas::textWidth("TRACKS ", 2), yNodesCap + 4, "BUSES", kBusText, 2);
        const int lx = drawColorLegend(c, tm.x0 + 4, yNodesCap + 4, 180, "-60", "0", "dBFS RMS", viridis);
        c.text(lx + 24, yNodesCap + 4, "square = dominant band (see bands.png)", kDim, 2);
        c.text(tm.x1 + 8, yNodesCap + 4, "RMS", kDim, 2);
        for (int ni = 0; ni < nNodes; ++ni) {
            const auto& node = m.nodes[static_cast<std::size_t>(ni)];
            const int y0 = yNodes + ni * laneH, y1 = y0 + laneH - 1;
            c.fillRect(tm.x0, y0, tm.x1, y1, kLane);
            const auto lv = levelColumns(m, *node.stats, tm);
            for (int col = 0; col < tm.width(); ++col) {
                const double db = lv[static_cast<std::size_t>(col)];
                if (db > kLo) c.fillRect(tm.x0 + col, y0, tm.x0 + col + 1, y1, viridis((db - kLo) / (kHi - kLo)));
            }
            const int ty = y0 + (laneH - 1 - 9 * scale) / 2;
            const int sw = 5 * scale;
            if (node.dominantBand >= 0) c.fillRect(8, ty + scale, 8 + sw, ty + scale + sw, kBandColors[node.dominantBand]);
            c.text(8 + sw + 2 * scale + 2, ty, fitText(node.id, kPlotX0 - 30 - sw, scale), node.isBus ? kBusText : kText, scale);
            c.text(tm.x1 + 8, ty, node.rmsDb > kDbFloor ? sfmt("%.1f", node.rmsDb) : std::string("silent"), kDim, scale);
            for (const auto& k : m.clicks)
                if (k.node == ni) {
                    const int x = tm.xi(k.sec);
                    for (int r = 0; r < 5; ++r) c.hline(x - (4 - r), x + (4 - r), y0 + r, k.inMix ? kRed : kAmber);
                }
        }
        if (nNodes == 0) c.text(tm.x0 + 8, yNodes + 4, "no tracks/buses were analysed", kDim, 2);
    }

    drawTimeGrid(c, m, tm, yLoud, yEnd - 1);
    panelFrame(c, tm.x0, yLoud, tm.x1, yLoud + loudH);
    panelFrame(c, tm.x0, yEvents, tm.x1, yEvents + eventsH);
    panelFrame(c, tm.x0, ySpace, tm.x1, ySpace + spaceH);
    panelFrame(c, tm.x0, yNodes, tm.x1, yEnd);
    drawTimeAxis(c, tm, yEnd + 2);

    // Key numbers.
    {
        int x = 8;
        x += c.text(x, yNums, sfmt("BALANCE vs %s ref dB:", m.profile->name.c_str()), kDim, 2) + 12;
        for (int b = 0; b < kNumBands; ++b) {
            const double v = m.vsRef[static_cast<std::size_t>(b)];
            const auto& hi = m.profile->bandHighDb[static_cast<std::size_t>(b)];
            const auto& lo = m.profile->bandLowDb[static_cast<std::size_t>(b)];
            x += c.text(x, yNums, kBandNames[b], kBandColors[b], 2) + 6;
            x += c.text(x, yNums, sfmt("%+.1f", v), (hi && v > *hi) || (lo && v < *lo) ? kAmber : kText, 2) + 16;
        }
        c.text(8, yNums + kLine, sfmt("PLR %.1f dB | short-term max %.1f LUFS | corr %.2f | width %.0f%% | lows corr %.2f | L/R %+.1f dB | "
                                      "clipped samples %lld", m.truePeakDb - m.lufsI, m.stMax, m.corr, m.width, m.lowCorr, m.balanceDb,
                                      static_cast<long long>(m.clippedSamples)),
               kDim, 2);
        c.text(8, yNums + 2 * kLine, fitText(spaceLine(m), kImageW - 16, 2), verdictColor(m.space.global.verdict), 2);
    }
    if (!notes.empty()) {
        c.hline(8, kImageW - 8, yNotes, kGrid);
        c.text(8, yNotes + 6, sfmt("TOP ISSUES (%d in total, all of them in report.json)", static_cast<int>(m.notes.size())), kDim, 2);
        static constexpr const char* kTag[] = {"ERROR", "WARN", "INFO"};
        static constexpr Rgb kTagColor[] = {kRed, kAmber, kDim};
        int y = yNotes + 30;
        for (const auto& [sev, lines] : notes) {
            c.text(8, y, kTag[sev], kTagColor[sev], 2);
            for (const auto& line : lines) {
                c.text(kNoteX, y, line, kText, 2);
                y += kLine;
            }
            y += 4;
        }
    }
    c.hline(8, kImageW - 8, yIndex, kGrid);
    c.text(8, yIndex + 6, "MORE IMAGES (same folder, each one focused; report.json 'images' lists them all)", kDim, 2);
    for (std::size_t i = 0; i < index.size(); ++i) {
        const auto& [file, what] = index[i];
        const int x = i % 2 ? kImageW / 2 + 8 : 8, y = yIndex + 30 + static_cast<int>(i / 2) * kLine;
        const int w = c.text(x, y, file, kCyan, 2);
        c.text(x + w + 14, y, fitText(what, kImageW / 2 - 24 - w, 2), kText, 2);
    }
    writePng(path, c.image());
}

// ------------------------------------------------------------------ loudness.png

void renderLoudness(const MixImpl& m, const std::string& path) {
    const TimeMap tm = songMap(m);
    constexpr int kWaveH = 118, kLoudH = 300;
    const int yWL = kPlotTop, yWR = yWL + kWaveH + 6, yLoud = yWR + kWaveH + 10, yEnd = yLoud + kLoudH;
    const bool implicitOnly = m.sections.size() == 1 && m.sections[0].implicit;
    const int rows = implicitOnly ? 0 : std::min<int>(14, static_cast<int>(m.sections.size()));
    const int yTab = yEnd + kAxisH + 12;
    const int H = yTab + (rows ? 26 + rows * kLine : 0) + 10;
    Canvas c(kImageW, H, kBg);

    const bool inTarget = m.lufsI >= m.lufsMin && m.lufsI <= m.lufsMax;
    drawTitle(c, "LOUDNESS", sfmt("%s | %.1f LUFS-I (target %.0f..%.0f: %s) | LRA %.1f LU | short-term max %.1f | TP %.2f dBTP | "
                                  "peak %.1f dBFS | PLR %.1f dB", mmss(m.durationSec).c_str(), m.lufsI, m.lufsMin, m.lufsMax,
                                  inTarget ? "ok" : m.lufsI < m.lufsMin ? "too quiet" : "too loud", m.lra, m.stMax, m.truePeakDb,
                                  m.samplePeakDb, m.truePeakDb - m.lufsI),
              inTarget ? kGreen : kAmber);
    drawTimeHeader(c, m, tm);
    drawClickMarkers(c, m, tm, 78);

    drawWaveformLane(c, m, tm, m.mixL, yWL, kWaveH, true);
    drawWaveformLane(c, m, tm, m.mixR, yWR, kWaveH, true);
    caption(c, 8, yWL + 4, {{"WAVEFORM L", kText}, {"dark = peak", rgbHex(0x5b86e6)}, {"light = RMS", kWaveRms}, {"red = clip", kRed}});
    caption(c, 8, yWR + 4, {{"WAVEFORM R", kText}, {"- - -6/-12 dB", kDim}});
    for (int y0 : {yWL, yWR}) {
        c.text(kPlotX1 + 8, y0 + 2, "0 dB", kDim, 2);
        c.text(kPlotX1 + 8, y0 + kWaveH / 2 - 8, "-inf", kDim, 2);
    }
    c.text(kPlotX1 + 8, yWL + kWaveH / 2 + 16, sfmt("pk %.1f", m.samplePeakDb), kText, 2);
    c.text(kPlotX1 + 8, yWR + kWaveH / 2 + 16, sfmt("TP %.2f", m.truePeakDb), m.truePeakDb > -1.0 ? kAmber : kText, 2);

    drawLoudnessPanel(c, m, tm, yLoud, kLoudH, -3.0, -45.0, 6.0, true);
    caption(c, 8, yLoud + 4, {{"LOUDNESS LUFS", kText}, {"short-term 3s", kAmber}, {"momentary 0.4s", kCyan}, {"-- integrated", kText},
                              {"== section avg", kText}, {"max = ST max", kAmber}});
    c.text(8, yLoud + 4 + 6 * kLine, sfmt("target %.0f..%.0f", m.lufsMin, m.lufsMax), kGreen, 2);
    c.text(8, yLoud + 4 + 7 * kLine, sfmt("(%s)", m.loudnessOverride ? "override" : m.profile->name.c_str()), kDim, 2);
    c.text(8, yLoud + 4 + 8 * kLine, sfmt("integr. %.1f", m.lufsI), kText, 2);

    drawTimeGrid(c, m, tm, yWL, yEnd - 1);
    panelFrame(c, tm.x0, yWL, tm.x1, yWL + kWaveH);
    panelFrame(c, tm.x0, yWR, tm.x1, yWR + kWaveH);
    panelFrame(c, tm.x0, yLoud, tm.x1, yEnd);
    drawTimeAxis(c, tm, yEnd + 2);

    if (rows) {
        static constexpr int kCol[] = {8, 230, 400, 560, 680, 810, 940, 1080, 1200, 1330, 1450};
        static constexpr const char* kHead[] = {"SECTION", "bars", "time", "LUFS", "vs prev", "ST max", "peak dB", "PLR", "width",
                                                "corr", "clicks"};
        for (int i = 0; i < 11; ++i) c.text(kCol[i], yTab, kHead[i], kDim, 2);
        c.hline(8, kImageW - 8, yTab + 20, kGrid);
        for (int r = 0; r < rows; ++r) {
            const auto& s = m.sections[static_cast<std::size_t>(r)];
            const int y = yTab + 26 + r * kLine;
            int clicks = 0;
            for (const auto& k : m.clicks) clicks += k.inMix && k.sec >= s.startSec && k.sec < s.endSec ? 1 : 0;
            const double jump = r > 0 && m.sections[static_cast<std::size_t>(r - 1)].lufs > -70.0 && s.lufs > -70.0
                                    ? s.lufs - m.sections[static_cast<std::size_t>(r - 1)].lufs
                                    : 0.0;
            c.text(kCol[0], y, fitText(s.name, kCol[1] - kCol[0] - 12, 2), kText, 2);
            c.text(kCol[1], y, sfmt("%.0f-%.0f", std::floor(1.0 + m.barAt(m.beatAt(s.startSec)) + 1e-6), std::ceil(m.barAt(m.beatAt(s.endSec)) - 1e-6)),
                   kText, 2);
            c.text(kCol[2], y, mmss(s.startSec) + "-" + mmss(s.endSec), kText, 2);
            c.text(kCol[3], y, s.lufs > -70.0 ? sfmt("%.1f", s.lufs) : std::string("silent"), kAmber, 2);
            c.text(kCol[4], y, r > 0 ? sfmt("%+.1f", jump) : std::string("-"), std::fabs(jump) > 6.0 ? kRed : kText, 2);
            c.text(kCol[5], y, sfmt("%.1f", s.stMax), kText, 2);
            c.text(kCol[6], y, sfmt("%.1f", s.peakDb), s.peakDb > -1.0 ? kAmber : kText, 2);
            c.text(kCol[7], y, s.lufs > -70.0 ? sfmt("%.1f", s.peakDb - s.lufs) : std::string("-"), kText, 2);
            c.text(kCol[8], y, sfmt("%.0f%%", s.width), kText, 2);
            c.text(kCol[9], y, sfmt("%.2f", s.corr), corrColor(s.corr), 2);
            c.text(kCol[10], y, sfmt("%d", clicks), clicks ? kRed : kDim, 2);
        }
    }
    writePng(path, c.image());
}

// ------------------------------------------------------------------ tracks.png

void renderTracks(const MixImpl& m, const std::string& path) {
    const TimeMap tm = songMap(m);
    const int nNodes = static_cast<int>(m.nodes.size());
    const int laneH = nNodes ? std::clamp(700 / nNodes, 26, 64) : 40;
    const int yLanes = kPlotTop + 30, yEnd = yLanes + std::max(1, nNodes) * laneH;
    const int H = yEnd + kAxisH + 10;
    Canvas c(kImageW, H, kBg);
    constexpr double kLo = -60.0, kHi = 0.0;

    drawTitle(c, "TRACKS", sfmt("%s | level of every track/bus over time | numbers = section RMS dBFS | FLAT = played note "
                                "dynamics under %.1f dB per phrase", mmss(m.durationSec).c_str(), m.profile->noteSpreadMinDb));
    drawTimeHeader(c, m, tm);
    drawClickMarkers(c, m, tm, 78);
    int lx = drawColorLegend(c, kPlotX0, kPlotTop + 4, 200, "-60", "0", "dBFS RMS", viridis);
    lx += 30;
    lx += c.text(lx, kPlotTop + 4, "dominant band:", kDim, 2) + 10;
    for (int b = 0; b < kNumBands; ++b) {
        c.fillRect(lx, kPlotTop + 7, lx + 10, kPlotTop + 17, kBandColors[b]);
        lx += 14 + c.text(lx + 14, kPlotTop + 4, kBandNames[b], kBandColors[b], 2) + 10;
    }
    c.text(8, kPlotTop + 4, "TRACKS", kText, 2);
    c.text(8 + Canvas::textWidth("TRACKS ", 2), kPlotTop + 4, "BUSES", kBusText, 2);
    c.text(tm.x1 + 8, kPlotTop + 4, "active", kDim, 2);

    for (int ni = 0; ni < nNodes; ++ni) {
        const auto& node = m.nodes[static_cast<std::size_t>(ni)];
        const int y0 = yLanes + ni * laneH, y1 = y0 + laneH - 2;
        c.fillRect(tm.x0, y0, tm.x1, y1, kLane);
        const auto lv = levelColumns(m, *node.stats, tm);
        for (int col = 0; col < tm.width(); ++col) {
            const double db = lv[static_cast<std::size_t>(col)];
            if (db > kLo) c.fillRect(tm.x0 + col, y0, tm.x0 + col + 1, y1, viridis((db - kLo) / (kHi - kLo)));
        }
        // Level curve inside the lane (-60 at the bottom, 0 dBFS at the top).
        for (int col = 1; col < tm.width(); ++col) {
            const double a = lv[static_cast<std::size_t>(col - 1)], b = lv[static_cast<std::size_t>(col)];
            if (a <= kLo && b <= kLo) continue;
            c.line(tm.x0 + col - 1, yLin(a, kHi, kLo, y0 + 2, laneH - 5), tm.x0 + col, yLin(b, kHi, kLo, y0 + 2, laneH - 5), kWhite, 1, 0.45);
        }
        // Per-section level written in.
        for (std::size_t s = 0; s < m.sections.size() && s < node.sectionRmsDb.size(); ++s) {
            const auto& sec = m.sections[s];
            const double v = node.sectionRmsDb[s];
            if (v <= kLo) continue;
            const std::string t = sfmt("%.0f", v);
            const int xa = std::clamp(tm.xi(sec.startSec), tm.x0, tm.x1), xb = std::clamp(tm.xi(sec.endSec), tm.x0, tm.x1);
            const int w = Canvas::textWidth(t, 2);
            if (xb - xa < w + 10) continue;
            textBox(c, (xa + xb - w) / 2, y0 + (laneH - 2 - 18) / 2, t, kWhite, 2, 0.6);
        }
        // Flat note dynamics (flat_dynamics): red = a lead (warn), amber = another melodic part (info).
        if (node.dynamics.severity > 0 && !node.dynamics.mark.empty()) {
            const std::string& t = node.dynamics.mark;
            const int w = Canvas::textWidth(t, 2);
            textBox(c, tm.x1 - w - 8, y0 + (laneH - 2 - 18) / 2, t, node.dynamics.severity == 1 ? kRed : kAmber, 2, 0.8);
        }
        // Clicks in this node.
        for (const auto& k : m.clicks)
            if (std::find(k.nodes.begin(), k.nodes.end(), ni) != k.nodes.end()) {
                const int x = tm.xi(k.sec);
                for (int r = 0; r < 7; ++r) c.hline(x - (6 - r), x + (6 - r), y0 + r, k.inMix ? kRed : kAmber);
            }
        // Labels.
        const bool two = laneH >= 44;
        const int ty = two ? y0 + (laneH - 2 - 40) / 2 : y0 + (laneH - 2 - 18) / 2;
        const bool mark = node.dominantBand >= 0;
        // One-line lanes put the band square after the name: keep room for it so it never covers the name.
        const std::string name = fitText(node.id, kPlotX0 - 20 - (mark && !two ? 20 : 0), 2);
        c.text(8, ty, name, node.isBus ? kBusText : kText, 2);
        if (mark) {
            const int yb = two ? ty + kLine : ty;
            const int xb = two ? 8 : 8 + Canvas::textWidth(name, 2) + 8;
            c.fillRect(xb, yb + 3, xb + 10, yb + 13, kBandColors[node.dominantBand]);
            if (two) c.text(xb + 16, yb, fitText(kBandNames[node.dominantBand], kPlotX0 - 40, 2), kBandColors[node.dominantBand], 2);
        }
        c.text(tm.x1 + 8, ty, node.rmsDb > kDbFloor ? sfmt("%.1f", node.rmsDb) : std::string("silent"), kText, 2);
        if (two) c.text(tm.x1 + 8, ty + kLine, sfmt("pk %.0f", node.peakDb), kDim, 2);
    }
    if (nNodes == 0) c.text(tm.x0 + 8, yLanes + 8, "no tracks/buses were analysed", kDim, 2);
    drawTimeGrid(c, m, tm, yLanes, yEnd - 1);
    panelFrame(c, tm.x0, yLanes, tm.x1, yEnd);
    drawTimeAxis(c, tm, yEnd + 2);
    writePng(path, c.image());
}

// ------------------------------------------------------------------ bands.png

void renderBands(const MixImpl& m, const std::string& path) {
    const TimeMap tm = songMap(m);
    constexpr int kStackH = 270, kRowH = 40;
    const int yStack = kPlotTop + 26, yDev = yStack + kStackH + 34, yEnd = yDev + kNumBands * kRowH;
    const int H = yEnd + kAxisH + 40;
    Canvas c(kImageW, H, kBg);
    static constexpr const char* kShortRange[kNumBands] = {"20-60", "60-250", "250-800", "0.8-2.5k", "2.5-6k", "6-12k", "12-20k"};

    drawTitle(c, "BANDS", sfmt("%s | share of the energy per band over time, and each band vs the reference balance of profile "
                               "'%s'", mmss(m.durationSec).c_str(), m.profile->name.c_str()));
    drawTimeHeader(c, m, tm);
    drawClickMarkers(c, m, tm, 78);

    std::vector<std::array<double, kNumBands>> narrow, wide;
    std::vector<double> lvl, lvlWide;
    bandColumns(m, tm, std::max(tm.pxSec(), 0.5), narrow, lvl);
    bandColumns(m, tm, std::max(tm.pxSec(), 2.0), wide, lvlWide);
    std::vector<double> ref(kNumBands + 1, 0.0);
    for (int b = 0; b < kNumBands; ++b) ref[static_cast<std::size_t>(b + 1)] = ref[static_cast<std::size_t>(b)] + m.refShare[static_cast<std::size_t>(b)];

    // (1) Stacked share, sub at the bottom.
    c.text(8, kPlotTop + 4, "SHARE OF ENERGY PER BAND (stacked, - - = reference split)", kText, 2);
    c.fillRect(tm.x0, yStack, tm.x1, yStack + kStackH, kPanel);
    for (int col = 0; col < tm.width(); ++col) {
        const auto& e = narrow[static_cast<std::size_t>(col)];
        double total = 0.0;
        for (double v : e) total += v;
        if (total <= 0.0 || lvl[static_cast<std::size_t>(col)] < -70.0) continue;
        double acc = 0.0;
        for (int b = 0; b < kNumBands; ++b) {
            const double share = e[static_cast<std::size_t>(b)] / total;
            const int ya = static_cast<int>(std::lround(yStack + kStackH - (acc + share) * kStackH));
            const int yb = static_cast<int>(std::lround(yStack + kStackH - acc * kStackH));
            c.fillRect(tm.x0 + col, ya, tm.x0 + col + 1, yb, kBandColors[b]);
            acc += share;
        }
    }
    for (int b = 1; b < kNumBands; ++b)
        c.dashedHline(tm.x0, tm.x1 - 1, static_cast<int>(std::lround(yStack + kStackH - ref[static_cast<std::size_t>(b)] * kStackH)), kWhite, 6, 4, 0.7);
    for (int v : {0, 25, 50, 75, 100}) {
        const int y = static_cast<int>(std::lround(yStack + kStackH - v / 100.0 * kStackH));
        c.text(tm.x1 + 8, std::clamp(y - 8, yStack, yStack + kStackH - 16), sfmt("%d%%", v), kDim, 2);
    }
    {  // band legend in the left margin
        int y = yStack + 4;
        for (int b = kNumBands - 1; b >= 0; --b) {
            c.fillRect(8, y + 3, 20, y + 15, kBandColors[b]);
            c.text(26, y, kBandNames[b], kBandColors[b], 2);
            y += kLine;
        }
    }

    // (2) Deviation from the reference balance, one row per band, per-section numbers.
    c.text(8, yDev - 26, "BALANCE vs REFERENCE dB (~2 s window, section values written in)", kText, 2);
    const int legendW = Canvas::textWidth("-12", 2) + 6 + 120 + 6 + Canvas::textWidth("+12", 2);
    drawColorLegend(c, tm.x1 - legendW, yDev - 26, 120, "-12", "+12", "", divergingDark, true);
    c.text(tm.x1 + 8, yDev - 26, "song", kDim, 2);
    for (int col = 0; col < tm.width(); ++col) {
        if (lvlWide[static_cast<std::size_t>(col)] < -70.0) continue;
        double dev[kNumBands];
        if (!balanceVsReference(wide[static_cast<std::size_t>(col)].data(), m.refShare, dev)) continue;
        for (int b = 0; b < kNumBands; ++b) {
            const int row = kNumBands - 1 - b;
            c.fillRect(tm.x0 + col, yDev + row * kRowH, tm.x0 + col + 1, yDev + row * kRowH + kRowH - 1, divergingDark(dev[b] / 12.0));
        }
    }
    for (int b = 0; b < kNumBands; ++b) {
        const int row = kNumBands - 1 - b;
        const int y = yDev + row * kRowH;
        c.fillRect(8, y + 4, 20, y + 16, kBandColors[b]);
        c.text(26, y + 1, kBandNames[b], kText, 2);
        c.text(26, y + 20, kShortRange[b], kDim, 2);
        const double v = m.vsRef[static_cast<std::size_t>(b)];
        const auto& hi = m.profile->bandHighDb[static_cast<std::size_t>(b)];
        const auto& lo = m.profile->bandLowDb[static_cast<std::size_t>(b)];
        c.text(tm.x1 + 8, y + 11, sfmt("%+.1f", v), hi && v > *hi ? kOrange : lo && v < *lo ? kCyan : kText, 2);
        for (const auto& s : m.sections) {
            if (s.implicit || s.rmsDb < -60.0) continue;
            const int xa = std::clamp(tm.xi(s.startSec), tm.x0, tm.x1), xb = std::clamp(tm.xi(s.endSec), tm.x0, tm.x1);
            const std::string t = sfmt("%+.1f", s.vsRef[static_cast<std::size_t>(b)]);
            const int w = Canvas::textWidth(t, 2);
            if (xb - xa < w + 10) continue;
            textBox(c, (xa + xb - w) / 2, y + 11, t, kWhite, 2, 0.55);
        }
    }
    drawTimeGrid(c, m, tm, yStack, yEnd - 1);
    panelFrame(c, tm.x0, yStack, tm.x1, yStack + kStackH);
    panelFrame(c, tm.x0, yDev, tm.x1, yEnd);
    drawTimeAxis(c, tm, yEnd + 2);
    c.text(8, yEnd + kAxisH + 10, "red = more energy than the reference balance (relative to the rest of the spectrum), blue = less; "
                                  "0 = the median band", kDim, 2);
    writePng(path, c.image());
}

// ------------------------------------------------------------------ stereo.png

void renderStereo(const MixImpl& m, const std::string& path) {
    const TimeMap tm = songMap(m);
    constexpr int kCorrH = 150, kWidthH = 110, kWetH = 120, kSpaceH = 24, kLowH = 110, kBalH = 90, kGap = 10, kFieldRow = 24;
    const int yCorr = kPlotTop, yWidth = yCorr + kCorrH + kGap, yWet = yWidth + kWidthH + kGap, ySpace = yWet + kWetH + kGap;
    const int yLow = ySpace + kSpaceH + kGap, yBal = yLow + kLowH + kGap;
    const int yEnd = yBal + kBalH;
    const int nNodes = static_cast<int>(m.nodes.size());
    const int yField = yEnd + kAxisH + 16;
    const int H = yField + 28 + std::max(1, nNodes) * kFieldRow + 12;
    Canvas c(kImageW, H, kBg);

    const SpaceSection& sg = m.space.global;
    drawTitle(c, "STEREO", sfmt("%s | correlation %.2f | width %.0f%% (>150 Hz %.0f%% in full sections) | lows corr %.2f | L/R %+.1f dB "
                                "| space %s", mmss(m.durationSec).c_str(), m.corr, m.width, sg.hiWidthPct, m.lowCorr, m.balanceDb,
                                sg.verdict.c_str()),
              m.corr < 0.0 || m.lowCorr < 0.75 ? kAmber : kText);
    drawTimeHeader(c, m, tm);
    drawClickMarkers(c, m, tm, 78);

    // Per-column stereo terms over a ~0.5 s window.
    const auto cols = static_cast<std::size_t>(tm.width());
    std::vector<double> corr(cols, 1.0), width(cols, 0.0), low(cols, 1.0), bal(cols, 0.0), lowShare(cols, 0.0), lvl(cols, kDbFloor);
    std::vector<double> hiWidth(cols, 0.0);
    if (m.mix) {
        const double win = std::max(tm.pxSec(), 0.5);
        for (std::size_t col = 0; col < cols; ++col) {
            const double tc = (static_cast<double>(col) + 0.5) * tm.pxSec();
            const TickSpan sp = ticksFor(*m.mix, m.tickSec(), tc - win * 0.5, tc + win * 0.5);
            double ll = 0, rr = 0, lr = 0, a = 0, b = 0, ab = 0, f = 0;
            for (std::size_t i = sp.i0; i < sp.i1; ++i) {
                const Tick& t = m.mix->ticks()[i];
                ll += t.ll; rr += t.rr; lr += t.lr; a += t.lowLL; b += t.lowRR; ab += t.lowLR;
                f += m.mix->tickFrames(i);
            }
            lvl[col] = f > 0 ? dbFromPower((ll + rr) / (2.0 * f)) : kDbFloor;
            corr[col] = (ll > 0 && rr > 0) ? std::clamp(lr / std::sqrt(ll * rr), -1.0, 1.0) : 1.0;
            const double side = ll + rr - 2.0 * lr, mid = ll + rr + 2.0 * lr;
            width[col] = side <= 0 ? 0.0 : mid <= 0 ? 999.0 : 100.0 * side / mid;
            const double hl = std::max(0.0, ll - a), hr = std::max(0.0, rr - b), hlr = lr - ab;
            const double hSide = hl + hr - 2.0 * hlr, hMid = hl + hr + 2.0 * hlr;
            hiWidth[col] = hSide <= 0 ? 0.0 : hMid <= 0 ? 999.0 : 100.0 * hSide / hMid;
            low[col] = (a > 0 && b > 0) ? std::clamp(ab / std::sqrt(a * b), -1.0, 1.0) : 1.0;
            lowShare[col] = (ll + rr) > 0 ? (a + b) / (ll + rr) : 0.0;
            bal[col] = (ll > 0 || rr > 0) ? std::clamp(10.0 * std::log10(std::max(ll, 1e-30) / std::max(rr, 1e-30)), -40.0, 40.0) : 0.0;
        }
    }
    auto sectionValues = [&](int y, auto value, const char* f) {
        for (const auto& s : m.sections) {
            if (s.rmsDb < -60.0) continue;
            const int xa = std::clamp(tm.xi(s.startSec), tm.x0, tm.x1), xb = std::clamp(tm.xi(s.endSec), tm.x0, tm.x1);
            const std::string t = sfmt(f, value(s));
            const int w = Canvas::textWidth(t, 2);
            if (xb - xa >= w + 10) textBox(c, (xa + xb - w) / 2, y, t, kWhite, 2, 0.6);
        }
    };

    // (1) Correlation.
    c.fillRect(tm.x0, yCorr, tm.x1, yCorr + kCorrH, kPanel);
    {
        auto yOf = [&](double v) { return yLin(v, 1.0, -1.0, yCorr, kCorrH); };
        for (double v : {0.5, -0.5}) c.dashedHline(tm.x0, tm.x1 - 1, yOf(v), kWhite, 2, 4, 0.12);
        c.hline(tm.x0, tm.x1 - 1, yOf(0.0), kGrid);
        for (std::size_t col = 0; col < cols; ++col) {
            if (lvl[col] < -70.0) continue;
            const int x = tm.x0 + static_cast<int>(col);
            c.vline(x, yOf(0.0), yOf(corr[col]), corrColor(corr[col]), 0.85);
        }
        for (double v : {1.0, 0.5, 0.0, -0.5, -1.0}) c.text(tm.x1 + 8, std::clamp(yOf(v) - 8, yCorr, yCorr + kCorrH - 16), sfmt("%+.1f", v), kDim, 2);
        caption(c, 8, yCorr + 4, {{"CORRELATION", kText}, {"+1 = mono", kDim}, {"0 = wide", kDim}, {"< 0 = phasey", kRed}});
        sectionValues(yCorr + 6, [](const SectionData& s) { return s.corr; }, "%.2f");
    }
    // (2) Width: whole mix (bars) and above 150 Hz (line, what the space check judges) vs the profile's target.
    c.fillRect(tm.x0, yWidth, tm.x1, yWidth + kWidthH, kPanel);
    {
        const AnalysisProfile& P = *m.profile;
        auto yOf = [&](double v) { return yLin(v, 100.0, 0.0, yWidth, kWidthH); };
        c.blendRect(tm.x0, yOf(std::min(100.0, P.widthMaxPct)), tm.x1, yOf(P.widthMinPct) + 1, kGreen, 0.12);
        for (double v : {25.0, 50.0, 75.0}) c.dashedHline(tm.x0, tm.x1 - 1, yOf(v), kWhite, 2, 4, 0.12);
        for (std::size_t col = 0; col < cols; ++col) {
            if (lvl[col] < -70.0) continue;
            c.vline(tm.x0 + static_cast<int>(col), yOf(0.0), yOf(width[col]), width[col] > 100.0 ? kAmber : rgbHex(0x8a7dff), 0.85);
        }
        for (std::size_t col = 1; col < cols; ++col) {
            if (lvl[col] < -70.0 || lvl[col - 1] < -70.0) continue;
            c.line(tm.x0 + static_cast<double>(col) - 1.0, yOf(hiWidth[col - 1]), tm.x0 + static_cast<double>(col), yOf(hiWidth[col]),
                   kWhite, 2, 0.8);
        }
        for (double v : {100.0, 50.0, 0.0}) c.text(tm.x1 + 8, std::clamp(yOf(v) - 8, yWidth, yWidth + kWidthH - 16), sfmt("%.0f%%", v), kDim, 2);
        caption(c, 8, yWidth + 4, {{"WIDTH S/M %", kText}, {"bars: all", rgbHex(0x8a7dff)}, {"line: >150Hz", kWhite},
                                   {"green: target", kGreen}});
        for (std::size_t s = 0; s < m.sections.size() && s < m.space.sections.size(); ++s) {
            const SectionData& sec = m.sections[s];
            const SpaceSection& sp = m.space.sections[s];
            if (!sp.assessed) continue;
            const int xa = std::clamp(tm.xi(sec.startSec), tm.x0, tm.x1), xb = std::clamp(tm.xi(sec.endSec), tm.x0, tm.x1);
            const std::string t = sfmt("%.0f%%", sp.hiWidthPct);
            const int w = Canvas::textWidth(t, 2);
            if (xb - xa >= w + 10)
                textBox(c, (xa + xb - w) / 2, yWidth + 6, t, sp.hiWidthPct < P.widthMinPct ? kCyan : kWhite, 2, 0.6);
        }
    }
    // (3) Wetness: reverb returns (bars) and echo returns (line) vs the mix, LU, with the lush zone and the washy limit.
    c.fillRect(tm.x0, yWet, tm.x1, yWet + kWetH, kPanel);
    {
        const AnalysisProfile& P = *m.profile;
        constexpr double kTop = 0.0, kBottom = -36.0;
        auto yOf = [&](double v) { return yLin(v, kTop, kBottom, yWet, kWetH); };
        c.blendRect(tm.x0, yOf(P.wetMaxLu), tm.x1, yOf(P.wetMinLu) + 1, kGreen, 0.14);
        c.dashedHline(tm.x0, tm.x1 - 1, yOf(P.washyLu), kViolet, 6, 4, 0.8);
        for (double v : {-12.0, -24.0}) c.dashedHline(tm.x0, tm.x1 - 1, yOf(v), kWhite, 2, 4, 0.12);
        std::vector<double> rev, echo;
        wetColumns(m, tm, std::max(tm.pxSec(), 2.0), rev, echo);
        for (std::size_t col = 0; col < cols; ++col) {
            if (lvl[col] < -70.0 || rev[col] <= kBottom) continue;
            const Rgb colr = rev[col] > P.washyLu ? kViolet : rev[col] < P.wetMinLu ? kAmber : kGreen;
            c.vline(tm.x0 + static_cast<int>(col), yOf(kBottom), yOf(rev[col]), colr, 0.7);
        }
        for (std::size_t col = 1; col < cols; ++col) {
            if (echo[col] <= kBottom || echo[col - 1] <= kBottom) continue;
            c.line(tm.x0 + static_cast<double>(col) - 1.0, yOf(echo[col - 1]), tm.x0 + static_cast<double>(col), yOf(echo[col]), kCyan, 2, 0.9);
        }
        for (const SpaceTail& t : m.space.tails) {
            const int x = tm.xi(t.sec);
            for (int r = 0; r < 6; ++r) c.hline(x - (5 - r), x + (5 - r), yWet + 1 + r, t.tailDb < P.tailMinDb ? kAmber : kWhite);
            const std::string label = sfmt("tail %.0f dB", t.tailDb);
            const int lw = Canvas::textWidth(label, 2);
            textBox(c, x + 8 + lw <= tm.x1 - 4 ? x + 8 : x - 8 - lw, yWet + 2, label, t.tailDb < P.tailMinDb ? kAmber : kText, 2, 0.6);
        }
        for (double v : {0.0, -12.0, -24.0, -36.0}) c.text(tm.x1 + 8, std::clamp(yOf(v) - 8, yWet, yWet + kWetH - 16), sfmt("%.0f", v), kDim, 2);
        caption(c, 8, yWet + 4, {{"WETNESS LU", kText}, {"reverb vs mix", kGreen}, {"echo (line)", kCyan}, {"- - washy", kViolet}});
        if (m.space.reverbReturns.empty())
            textBox(c, tm.x0 + 12, yWet + kWetH / 2 - 8, "no reverb return (a bus with a reverb fed by sends): the mix has no measurable space",
                    kAmber, 2, 0.7);
        for (std::size_t s = 0; s < m.sections.size() && s < m.space.sections.size(); ++s) {
            const SectionData& sec = m.sections[s];
            const SpaceSection& sp = m.space.sections[s];
            if (!sp.assessed || !sp.wetLu) continue;
            const int xa = std::clamp(tm.xi(sec.startSec), tm.x0, tm.x1), xb = std::clamp(tm.xi(sec.endSec), tm.x0, tm.x1);
            const std::string t = sfmt("%.1f", *sp.wetLu);
            const int w = Canvas::textWidth(t, 2);
            if (xb - xa >= w + 10)
                textBox(c, (xa + xb - w) / 2, yWet + kWetH - 26, t,
                        *sp.wetLu < P.wetMinLu ? kAmber : *sp.wetLu > P.washyLu ? kViolet : kWhite, 2, 0.6);
        }
    }
    // (4) Space verdict per section.
    drawSpaceStrip(c, m, tm, ySpace, kSpaceH);
    c.text(8, ySpace + 3, "SPACE", kText, 2);
    c.text(tm.x1 + 8, ySpace + 3, fitText(m.space.global.verdict, kImageW - tm.x1 - 12, 2), verdictColor(m.space.global.verdict), 2);
    // (3) Low end mono check.
    c.fillRect(tm.x0, yLow, tm.x1, yLow + kLowH, kPanel);
    {
        auto yOf = [&](double v) { return yLin(v, 1.0, -1.0, yLow, kLowH); };
        c.blendRect(tm.x0, yOf(0.75), tm.x1, yOf(1.0) + 1, kGreen, 0.12);
        c.hline(tm.x0, tm.x1 - 1, yOf(0.0), kGrid);
        c.dashedHline(tm.x0, tm.x1 - 1, yOf(0.75), kGreen, 4, 4, 0.5);
        for (std::size_t col = 0; col < cols; ++col) {
            if (lvl[col] < -70.0) continue;
            const bool significant = lowShare[col] > 0.02 && lvl[col] > -60.0;
            const Rgb col2 = !significant ? kGrid : low[col] < 0.75 ? kRed : kGreen;
            c.vline(tm.x0 + static_cast<int>(col), yOf(0.0), yOf(low[col]), col2, 0.85);
        }
        for (double v : {1.0, 0.0, -1.0}) c.text(tm.x1 + 8, std::clamp(yOf(v) - 8, yLow, yLow + kLowH - 16), sfmt("%+.0f", v), kDim, 2);
        c.text(tm.x1 + 8, yOf(0.75) + 4, "0.75", kGreen, 2);
        caption(c, 8, yLow + 4, {{"LOW END MONO", kText}, {"corr < 150 Hz", kDim}, {"red < 0.75", kRed}, {"grey = no lows", kDim}});
        for (const auto& s : m.sections) {
            if (s.rmsDb < -60.0) continue;
            const int xa = std::clamp(tm.xi(s.startSec), tm.x0, tm.x1), xb = std::clamp(tm.xi(s.endSec), tm.x0, tm.x1);
            const bool lows = s.lowShare > 0.02;
            const std::string t = lows ? sfmt("%.2f", s.lowCorr) : std::string("few lows");
            const int w = Canvas::textWidth(t, 2);
            if (xb - xa >= w + 10) textBox(c, (xa + xb - w) / 2, yLow + kLowH - 26, t, lows && s.lowCorr < 0.75 ? kRed : kWhite, 2, 0.6);
        }
    }
    // (4) L/R balance.
    c.fillRect(tm.x0, yBal, tm.x1, yBal + kBalH, kPanel);
    {
        auto yOf = [&](double v) { return yLin(v, 6.0, -6.0, yBal, kBalH); };
        c.hline(tm.x0, tm.x1 - 1, yOf(0.0), kGrid);
        for (double v : {3.0, -3.0}) c.dashedHline(tm.x0, tm.x1 - 1, yOf(v), kWhite, 2, 4, 0.12);
        for (std::size_t col = 0; col < cols; ++col) {
            if (lvl[col] < -70.0) continue;
            c.vline(tm.x0 + static_cast<int>(col), yOf(0.0), yOf(bal[col]), std::fabs(bal[col]) > 1.5 ? kAmber : kCyan, 0.85);
        }
        for (double v : {6.0, 0.0, -6.0}) c.text(tm.x1 + 8, std::clamp(yOf(v) - 8, yBal, yBal + kBalH - 16), sfmt("%+.0f dB", v), kDim, 2);
        caption(c, 8, yBal + 4, {{"BALANCE L/R", kText}, {"+ = left", kDim}});
        sectionValues(yBal + 6, [](const SectionData& s) { return s.balanceDb; }, "%+.1f");
    }
    drawTimeGrid(c, m, tm, yCorr, yEnd - 1);
    for (auto [y, h] : {std::pair{yCorr, kCorrH}, {yWidth, kWidthH}, {yWet, kWetH}, {ySpace, kSpaceH}, {yLow, kLowH}, {yBal, kBalH}})
        panelFrame(c, tm.x0, y, tm.x1, y + h);
    drawTimeAxis(c, tm, yEnd + 2);

    // (5) Stereo field: where each track/bus sits (constant-power pan inverted from its L/R balance)
    // and how wide it is.
    c.hline(8, kImageW - 8, yField - 6, kGrid);
    c.text(8, yField, "STEREO FIELD  dot = position, bar = width, right: corr / width; role (amber: centred, widen it)", kText, 2);
    const int fx0 = tm.x0 + 60, fx1 = tm.x1 - 60, fmid = (fx0 + fx1) / 2;
    for (int ni = 0; ni < nNodes; ++ni) {
        const auto& node = m.nodes[static_cast<std::size_t>(ni)];
        const int y = yField + 28 + ni * kFieldRow, yc = y + kFieldRow / 2 - 1;
        c.fillRect(tm.x0, y, tm.x1, y + kFieldRow - 2, ni % 2 ? kPanel : kLane);
        c.text(8, y + 3, fitText(node.id, kPlotX0 - 16, 2), node.isBus ? kBusText : kText, 2);
        c.text(tm.x0 + 8, y + 3, "L", kDim, 2);
        {
            const bool opp = std::find(m.space.opportunities.begin(), m.space.opportunities.end(), ni) != m.space.opportunities.end();
            const std::string role = node.role == Role::Return ? std::string("return:") + returnKindName(node.returnKind) : roleName(node.role);
            c.text(tm.x0 + 30, y + 3, opp ? role + " - widen" : role, opp ? kAmber : kDim, 2);
        }
        c.text(tm.x1 - 20, y + 3, "R", kDim, 2);
        c.dashedVline(fmid, y, y + kFieldRow - 3, kWhite, 2, 2, 0.3);
        if (node.rmsDb <= -90.0) {
            c.text(fmid + 10, y + 3, "silent", kDim, 2);
            continue;
        }
        const double theta = std::atan(std::pow(10.0, -node.balanceDb / 20.0));
        const double p = std::clamp(4.0 * theta / 3.14159265358979323846 - 1.0, -1.0, 1.0);
        const int x = static_cast<int>(std::lround(fmid + p * (fx1 - fmid)));
        const int spread = static_cast<int>(std::lround(std::min(1.2, std::sqrt(std::max(0.0, node.width) / 100.0)) * 0.5 * (fx1 - fmid)));
        c.blendRect(x - spread, yc - 4, x + spread + 1, yc + 5, node.corr < 0.0 ? kRed : rgbHex(0x8a7dff), 0.55);
        c.fillRect(x - 5, yc - 6, x + 6, yc + 7, node.isBus ? kBusText : kText);
        c.text(tm.x1 + 4, y + 3, sfmt("%.2f/%.0f%%", node.corr, std::min(node.width, 999.0)), corrColor(node.corr), 2);
    }
    writePng(path, c.image());
}

}  // namespace as::analysis
