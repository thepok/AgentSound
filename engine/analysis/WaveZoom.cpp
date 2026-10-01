#include "analysis/WaveZoom.h"

#include "analysis/Loudness.h"
#include "analysis/PlotKit.h"

#include <algorithm>
#include <cmath>

namespace as::analysis {

namespace {

constexpr int kW = kImageW;
constexpr int kX0 = 150, kX1 = 1490;
constexpr Rgb kColL = rgbHex(0x55ccff);
constexpr Rgb kColR = rgbHex(0xff9a4d);
constexpr Rgb kColMono = rgbHex(0xd8e0f0);

struct View {
    double s0, s1;  // sample offsets relative to the centre shown at kX0 / kX1
    double x(double s) const { return kX0 + (s - s0) / (s1 - s0) * (kX1 - kX0); }
    double pxPerSample() const { return (kX1 - kX0) / (s1 - s0); }
};

float sampleAt(const std::vector<float>& v, std::int64_t centre, std::int64_t rel, bool& ok) {
    const std::int64_t i = centre + rel;
    ok = i >= 0 && i < static_cast<std::int64_t>(v.size());
    return ok ? v[static_cast<std::size_t>(i)] : 0.0f;
}

double peakIn(const WaveSource& src, const View& v, bool useL, bool useR) {
    double pk = 0.0;
    bool ok = false;
    for (auto s = static_cast<std::int64_t>(std::floor(v.s0)); s <= static_cast<std::int64_t>(std::ceil(v.s1)); ++s) {
        if (useL) pk = std::max(pk, static_cast<double>(std::fabs(sampleAt(src.L, src.centre, s, ok))));
        if (useR) pk = std::max(pk, static_cast<double>(std::fabs(sampleAt(src.R, src.centre, s, ok))));
    }
    return pk;
}

// Nice full-scale for a lane: the peak rounded up to 1/2/5 steps.
double laneScale(double peak) {
    if (!(peak > 1e-9)) return 1e-3;
    const double e = std::pow(10.0, std::floor(std::log10(peak)));
    for (double m : {1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0})
        if (m * e >= peak * 1.04) return m * e;
    return 10.0 * e;
}

std::string ampLabel(double a) {
    if (a >= 0.1) return sfmt("%.2f", a);
    if (a >= 0.01) return sfmt("%.3f", a);
    if (a >= 0.001) return sfmt("%.4f", a);
    return sfmt("%.1e", a);
}

void drawLaneFrame(Canvas& c, int y0, int h, double scale, const std::string& label, Rgb labelColor, const std::string& sub) {
    c.fillRect(kX0, y0, kX1, y0 + h, kPanel);
    const int yMid = y0 + h / 2;
    c.hline(kX0, kX1 - 1, yMid, kGrid);
    c.dashedHline(kX0, kX1 - 1, y0 + 3, kWhite, 2, 4, 0.12);
    c.dashedHline(kX0, kX1 - 1, y0 + h - 4, kWhite, 2, 4, 0.12);
    c.rectOutline(kX0 - 1, y0 - 1, kX1, y0 + h, kGrid);
    c.text(8, y0 + 4, fitText(label, kX0 - 16, 2), labelColor, 2);
    if (!sub.empty() && h >= 50) c.text(8, y0 + 4 + kLine, fitText(sub, kX0 - 16, 2), kDim, 2);
    c.text(kX1 + 6, y0 + 2, "+" + ampLabel(scale), kDim, 2);
    c.text(kX1 + 6, yMid - 8, "0", kDim, 2);
    c.text(kX1 + 6, y0 + h - 18, "-" + ampLabel(scale), kDim, 2);
    if (h >= 124) c.text(kX1 + 6, y0 + 2 + kLine, sfmt("%.0fdB", 20.0 * std::log10(std::max(scale, 1e-9))), kDim, 2);
}

// Waveform of one channel: min/max per pixel when samples are dense, else lines between the
// samples (dots from 3 px per sample on).
void drawTrace(Canvas& c, const View& v, int y0, int h, const std::vector<float>& x, std::int64_t centre, double scale, Rgb col,
               bool dots) {
    const double yMid = y0 + h / 2.0, amp = h / 2.0 - 4.0;
    auto yOf = [&](double val) { return std::clamp(yMid - val / scale * amp, static_cast<double>(y0), static_cast<double>(y0 + h - 1)); };
    const double pps = v.pxPerSample();
    bool ok = false;
    if (pps < 1.5) {
        double prevHi = 0.0, prevLo = 0.0;
        bool have = false;
        for (int px = kX0; px < kX1; ++px) {
            const double sa = v.s0 + (px - kX0) / pps, sb = v.s0 + (px + 1 - kX0) / pps;
            float lo = 0.0f, hi = 0.0f;
            bool any = false;
            for (auto s = static_cast<std::int64_t>(std::ceil(sa)); s < static_cast<std::int64_t>(std::ceil(sb)); ++s) {
                const float val = sampleAt(x, centre, s, ok);
                if (!ok) continue;
                lo = any ? std::min(lo, val) : val;
                hi = any ? std::max(hi, val) : val;
                any = true;
            }
            if (!any) { have = false; continue; }
            double top = yOf(hi), bot = yOf(lo);
            if (have) { top = std::min(top, prevLo); bot = std::max(bot, prevHi); }  // connect to the previous column
            c.vline(px, static_cast<int>(std::lround(top)), static_cast<int>(std::lround(bot)), col);
            prevHi = yOf(hi);
            prevLo = yOf(lo);
            have = true;
        }
        return;
    }
    const auto s0 = static_cast<std::int64_t>(std::floor(v.s0)), s1 = static_cast<std::int64_t>(std::ceil(v.s1));
    bool prevOk = false;
    double px0 = 0.0, py0 = 0.0;
    for (std::int64_t s = s0; s <= s1; ++s) {
        const float val = sampleAt(x, centre, s, ok);
        const double px = v.x(static_cast<double>(s)), py = yOf(val);
        if (ok && prevOk) {
            const double ax = std::max(px0, static_cast<double>(kX0)), bx = std::min(px, static_cast<double>(kX1 - 1));
            if (bx > ax) {
                const double t0 = (ax - px0) / (px - px0), t1 = (bx - px0) / (px - px0);
                c.line(ax, py0 + (py - py0) * t0, bx, py0 + (py - py0) * t1, col, pps >= 6.0 ? 2 : 1);
            }
        }
        if (ok && dots && px >= kX0 && px < kX1) {
            const int ix = static_cast<int>(std::lround(px)), iy = static_cast<int>(std::lround(py));
            c.fillRect(ix - 2, iy - 2, ix + 3, iy + 3, col);
            c.fillRect(ix - 1, iy - 1, ix + 2, iy + 2, kBg);
        }
        prevOk = ok;
        px0 = px;
        py0 = py;
    }
}

void drawMarkers(Canvas& c, const WaveZoomSpec& spec, const View& v, int y0, int y1, bool labels) {
    const double spms = spec.sampleRate / 1000.0;
    for (const auto& [ms, label] : spec.markers) {
        const double s = ms * spms;
        if (s < v.s0 || s > v.s1) continue;
        const int x = static_cast<int>(std::lround(v.x(s)));
        c.dashedVline(x, y0, y1, kRed, 5, 3, 0.85);
        if (labels && !label.empty()) textBox(c, std::min(x + 4, kX1 - Canvas::textWidth(label, 2) - 4), y0 + 3, label, kRed);
    }
}

void drawMsAxis(Canvas& c, const View& v, double sampleRate, int y, bool sampleTicks) {
    const double spms = sampleRate / 1000.0;
    const double ms0 = v.s0 / spms, ms1 = v.s1 / spms;
    const double step = niceStep((ms1 - ms0) / 14.0, {0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 500});
    if (sampleTicks && v.pxPerSample() >= 4.0)
        for (auto s = static_cast<std::int64_t>(std::ceil(v.s0)); s <= static_cast<std::int64_t>(std::floor(v.s1)); ++s)
            c.vline(static_cast<int>(std::lround(v.x(static_cast<double>(s)))), y, y + 2, kGrid);
    // Enough decimals for the step itself (a 2.5 ms step must not print -12.5 as "-12").
    int decimals = 0;
    while (decimals < 3 && std::fabs(step * std::pow(10.0, decimals) - std::round(step * std::pow(10.0, decimals))) > 1e-6) ++decimals;
    for (auto k = static_cast<std::int64_t>(std::ceil(ms0 / step - 1e-9)); k * step <= ms1 + 1e-9; ++k) {
        const double t = static_cast<double>(k) * step;  // no accumulated error
        const int x = static_cast<int>(std::lround(v.x(t * spms)));
        c.vline(x, y, y + 5, kDim);
        const double tt = k == 0 ? 0.0 : t;
        const std::string label = sfmt("%+.*f", decimals, tt);
        const std::string l = tt == 0.0 ? std::string("0") : label;
        const int w = Canvas::textWidth(l, 2);
        c.text(std::clamp(x - w / 2, kX0 - 30, kX1 - w), y + 8, l, tt == 0.0 ? kText : kDim, 2);
    }
    c.text(kX1 + 6, y + 8, "ms", kDim, 2);
}

}  // namespace

void renderWaveZoom(const WaveZoomSpec& spec, const std::string& path) {
    const double sr = spec.sampleRate > 0 ? spec.sampleRate : 48000.0;
    const double spms = sr / 1000.0;
    const double half = std::max(0.05, spec.halfMs), detail = std::clamp(spec.detailHalfMs, 0.02, half);
    const View va{-half * spms, half * spms}, vb{-detail * spms, detail * spms};
    const bool showL = spec.showL || !spec.showR, showR = spec.showR;
    const int chans = (showL ? 1 : 0) + (showR ? 1 : 0);
    const int nSrc = std::max<int>(1, static_cast<int>(spec.sources.size()));
    const int nA = nSrc * chans;
    const int laneA = std::clamp(360 / nA, 64, 150), laneB = std::clamp(270 / nSrc, 100, 180);
    const int stripH = spec.spectrogramStrip ? 72 : 0;

    const int yCapA = 58, yA = yCapA + 26;
    const int yStrip = yA + nA * (laneA + 6) + 4;
    const int yAxisA = yStrip + (stripH ? stripH + 4 : 0);
    const int yCapB = yAxisA + 40, yB = yCapB + 26;
    const int yAxisB = yB + nSrc * (laneB + 6);
    const int H = yAxisB + 34;
    Canvas c(kW, H, kBg);

    c.text(8, 8, fitText(spec.title, kW - 16, 2), kText, 2);
    if (!spec.subtitle.empty()) c.text(8, 32, fitText(spec.subtitle, kW - 16, 2), kDim, 2);

    // Main view: one lane per source and channel.
    c.text(8, yCapA, sfmt("WAVEFORM  %+.1f..%+.1f ms (%d samples at %.0f Hz)", -half, half,
                          static_cast<int>(std::lround(2 * half * spms)) + 1, sr), kText, 2);
    int y = yA;
    for (int si = 0; si < static_cast<int>(spec.sources.size()); ++si) {
        const WaveSource& src = spec.sources[static_cast<std::size_t>(si)];
        const double scale = laneScale(peakIn(src, va, showL, showR));  // same scale for L and R of a source
        for (int ch = 0; ch < 2; ++ch) {
            if ((ch == 0 && !showL) || (ch == 1 && !showR)) continue;
            drawLaneFrame(c, y, laneA, scale, src.name + (ch ? " R" : " L"), ch ? kColR : kColL,
                          sfmt("pk %.1f dB", 20.0 * std::log10(std::max(peakIn(src, va, ch == 0, ch == 1), 1e-9))));
            drawTrace(c, va, y, laneA, ch ? src.R : src.L, src.centre, scale, ch ? kColR : kColL, va.pxPerSample() >= 3.0);
            drawMarkers(c, spec, va, y, y + laneA - 1, y == yA);
            y += laneA + 6;
        }
    }
    // Detail window outline on the main view.
    c.dashedVline(static_cast<int>(std::lround(va.x(vb.s0))), yA - 4, yStrip - 6, kGreen, 3, 3, 0.8);
    c.dashedVline(static_cast<int>(std::lround(va.x(vb.s1))), yA - 4, yStrip - 6, kGreen, 3, 3, 0.8);

    // Spectrogram strip of the first source.
    if (stripH && !spec.sources.empty()) {
        const WaveSource& src = spec.sources[0];
        const int n = sr > 50000.0 ? 256 : 128;
        const int cols = kX1 - kX0;
        const double fMin = 200.0, fMax = std::min(20000.0, sr * 0.5);
        std::vector<SpecLayer> layers{{src.L.data(), src.R.data(), static_cast<std::int64_t>(src.L.size()), sr, n, 0.0, 1e9}};
        const double t0 = (static_cast<double>(src.centre) + va.s0) / sr;
        const auto db = spectrogramDb(layers, cols, stripH, t0, (va.s1 - va.s0) / cols / sr, fMin, fMax);
        float top = -200.0f;
        for (float d : db) top = std::max(top, d);
        const double hi = std::max(-110.0, static_cast<double>(top)), lo = hi - 70.0;
        for (int r = 0; r < stripH; ++r)
            for (int col = 0; col < cols; ++col)
                c.set(kX0 + col, yStrip + r, inferno((db[static_cast<std::size_t>(r) * cols + col] - lo) / (hi - lo)));
        c.rectOutline(kX0 - 1, yStrip - 1, kX1, yStrip + stripH, kGrid);
        c.text(8, yStrip + 4, "SPECTRUM", kText, 2);
        c.text(8, yStrip + 4 + kLine, fitText(src.name, kX0 - 16, 2), kDim, 2);
        c.text(8, yStrip + 4 + 2 * kLine, "70 dB range", kDim, 2);
        auto yOfF = [&](double f) { return yStrip + static_cast<int>(std::lround(std::log(fMax / f) / std::log(fMax / fMin) * (stripH - 1))); };
        for (double f : {500.0, 2000.0, 10000.0}) {
            if (f >= fMax) continue;
            c.dashedHline(kX0, kX1 - 1, yOfF(f), kWhite, 2, 5, 0.25);
            c.text(kX1 + 6, yOfF(f) - 8, f >= 1000 ? sfmt("%gk", f / 1000) : sfmt("%g", f), kDim, 2);
        }
        drawMarkers(c, spec, va, yStrip, yStrip + stripH - 1, false);
    }
    drawMsAxis(c, va, sr, yAxisA, false);

    // Detail view: L and R overlaid, every sample a dot.
    c.text(8, yCapB, sfmt("DETAIL  %+.2f..%+.2f ms (%d samples): dots = samples,", -detail, detail,
                          static_cast<int>(std::lround(2 * detail * spms)) + 1), kGreen, 2);
    int lx = 8 + Canvas::textWidth(sfmt("DETAIL  %+.2f..%+.2f ms (%d samples): dots = samples, ", -detail, detail,
                                        static_cast<int>(std::lround(2 * detail * spms)) + 1), 2);
    if (showL) lx += 12 + c.text(lx, yCapB, "L", kColL, 2);
    if (showR) lx += 12 + c.text(lx, yCapB, "R", kColR, 2);
    if (showL && showR) c.text(lx, yCapB, "(same = mono)", kDim, 2);
    y = yB;
    for (const WaveSource& src : spec.sources) {
        const double scale = laneScale(peakIn(src, vb, showL, showR));
        bool mono = showL && showR;
        bool ok = false;
        for (auto s = static_cast<std::int64_t>(std::floor(vb.s0)); mono && s <= static_cast<std::int64_t>(std::ceil(vb.s1)); ++s)
            mono = sampleAt(src.L, src.centre, s, ok) == sampleAt(src.R, src.centre, s, ok);
        drawLaneFrame(c, y, laneB, scale, src.name, kText, mono ? "L = R" : std::string(showL && showR ? "L + R" : showL ? "L" : "R"));
        if (mono) {
            drawTrace(c, vb, y, laneB, src.L, src.centre, scale, kColMono, true);
        } else {
            if (showL) drawTrace(c, vb, y, laneB, src.L, src.centre, scale, kColL, true);
            if (showR) drawTrace(c, vb, y, laneB, src.R, src.centre, scale, kColR, true);
        }
        drawMarkers(c, spec, vb, y, y + laneB - 1, false);
        y += laneB + 6;
    }
    drawMsAxis(c, vb, sr, yAxisB, true);
    writePng(path, c.image());
}

}  // namespace as::analysis
