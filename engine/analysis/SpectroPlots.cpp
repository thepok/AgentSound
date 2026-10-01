// spectrogram.png (whole song) and spectrogram_NN_<section>.png (one zoom per section, higher
// time resolution, beat grid and a waveform strip).

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

constexpr double kDbMax = -20.0, kDbMin = -100.0;  // fixed colour scale: renders stay comparable
constexpr double kFMin = 25.0;

struct Decimated {
    int factor{1};
    double rate{48000.0};
    std::vector<float> L, R;
};

Decimated decimateMix(const MixImpl& m) {
    Decimated d;
    d.factor = std::max(1, static_cast<int>(std::lround(m.sampleRate / 6000.0)));
    d.rate = m.sampleRate / d.factor;
    d.L = decimate(m.mixL, d.factor);
    d.R = decimate(m.mixR, d.factor);
    return d;
}

int scaledN(int n48k, double sr) {
    int n = n48k;
    while (sr > 1.5 * 48000.0 * n / n48k && n < 65536) n *= 2;
    return n;
}

// Frequency axis (left: band names and Hz labels), colour bar (right, dB).
void drawFrequencyFrame(Canvas& c, int y0, int y1, double fMax, bool hzLabelBelow) {
    if (hzLabelBelow) c.text(8, y1 + 8, "Hz", kDim, 2);
    const int rows = y1 - y0;
    auto yOf = [&](double f) { return y0 + std::log(fMax / f) / std::log(fMax / kFMin) * rows; };
    for (double f : {50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0, 10000.0, 20000.0}) {
        if (f > fMax) continue;
        const int y = static_cast<int>(std::lround(yOf(f)));
        if (f < fMax) c.dashedHline(kPlotX0, kPlotX1 - 1, y, kWhite, 2, 4, 0.22);
        const std::string label = f >= 1000.0 ? sfmt("%gk", f / 1000.0) : sfmt("%g", f);
        c.text(kPlotX0 - 8 - Canvas::textWidth(label, 2), std::clamp(y - 7, y0, y1 - 14), label, kText, 2);
        c.hline(kPlotX0 - 5, kPlotX0 - 1, y, kText);
    }
    for (int b = 0; b <= kNumBands; ++b) {
        const double f = kBandEdgesHz[b];
        if (f > fMax + 1.0) continue;
        const int y = static_cast<int>(std::lround(yOf(std::max(f, kFMin))));
        c.hline(4, 132, y, kGrid);
        if (b < kNumBands) {
            const int y2 = static_cast<int>(std::lround(yOf(std::min(kBandEdgesHz[b + 1], fMax))));
            c.text(8, std::clamp((y + y2) / 2 - 8, y2 + 1, y1 - 16), kBandNames[b], kBandColors[b], 2);
        }
    }
    const int cbX = kPlotX1 + 12, cbW = 18;
    for (int y = y0; y < y1; ++y) c.fillRect(cbX, y, cbX + cbW, y + 1, inferno(1.0 - static_cast<double>(y - y0) / (rows - 1)));
    c.rectOutline(cbX - 1, y0 - 1, cbX + cbW, y1, kGrid);
    for (double db = kDbMin; db <= kDbMax + 1e-9; db += 20.0) {
        const int y = static_cast<int>(std::lround(y1 - 1 - (db - kDbMin) / (kDbMax - kDbMin) * (rows - 1)));
        c.hline(cbX + cbW, cbX + cbW + 3, y, kText);
        c.text(cbX + cbW + 6, std::clamp(y - 7, y0, y1 - 14), sfmt(db >= kDbMax - 1e-9 ? "%.0fdB" : "%.0f", db), kText, 2);
    }
}

void paint(Canvas& c, const std::vector<float>& db, int cols, int rows, int y0) {
    for (int r = 0; r < rows; ++r)
        for (int col = 0; col < cols; ++col)
            c.set(kPlotX0 + col, y0 + r, inferno((db[static_cast<std::size_t>(r) * cols + col] - kDbMin) / (kDbMax - kDbMin)));
}

void renderWhole(const MixImpl& m, const Decimated& d, const std::string& path) {
    constexpr int kSpecH = 600;
    const int Y0 = kPlotTop, Y1 = Y0 + kSpecH;
    const int H = Y1 + kAxisH + 8;
    Canvas c(kImageW, H, kBg);
    const TimeMap tm{kPlotX0, kPlotX1, 0.0, std::max(m.durationSec, 1e-3)};
    const int cols = tm.width();
    const double fMax = std::min(20000.0, m.sampleRate * 0.5);
    c.fillRect(kPlotX0, Y0, kPlotX1, Y1, rgbHex(0x000004));
    if (!m.mixL.empty()) {
        const auto len = static_cast<std::int64_t>(m.mixL.size());
        std::vector<SpecLayer> layers{
            {d.L.data(), d.R.data(), static_cast<std::int64_t>(d.L.size()), d.rate, 2048, 0.0, 212.0},  // ~3 Hz bins, ~340 ms
            {m.mixL.data(), m.mixR.data(), len, m.sampleRate, scaledN(4096, m.sampleRate), 212.0, 1e9}};  // ~12 Hz, ~85 ms
        paint(c, spectrogramDb(layers, cols, kSpecH, 0.0, tm.pxSec(), kFMin, fMax), cols, kSpecH, Y0);
    }
    drawFrequencyFrame(c, Y0, Y1, fMax, true);
    drawTitle(c, "SPECTROGRAM", sfmt("%s | %.1f LUFS-I | whole song, L+R energy per 1/%d-octave row, fixed scale | zooms: "
                                     "spectrogram_NN_*.png", mmss(m.durationSec).c_str(), m.lufsI,
                                     static_cast<int>(std::lround(kSpecH / std::log2(fMax / kFMin)))));
    drawTimeHeader(c, m, tm);
    drawClickMarkers(c, m, tm, 78);
    drawTimeGrid(c, m, tm, Y0, Y1 - 1);
    c.rectOutline(kPlotX0 - 1, Y0 - 1, kPlotX1, Y1, kGrid);
    drawTimeAxis(c, tm, Y1 + 2);
    writePng(path, c.image());
}

void renderZoom(const MixImpl& m, const Decimated& d, std::size_t index, const std::string& path) {
    const ZoomSpan& z = m.zooms[index];
    constexpr int kSpecH = 520, kWaveH = 96;
    const int Y0 = kPlotTop, Y1 = Y0 + kSpecH, yWave = Y1 + 8, yEnd = yWave + kWaveH;
    const int H = yEnd + kAxisH + 8;
    Canvas c(kImageW, H, kBg);
    const TimeMap tm{kPlotX0, kPlotX1, z.startSec, std::max(z.endSec - z.startSec, 1e-3)};
    const int cols = tm.width();
    const double fMax = std::min(20000.0, m.sampleRate * 0.5), sr = m.sampleRate;
    const auto len = static_cast<std::int64_t>(m.mixL.size());
    c.fillRect(kPlotX0, Y0, kPlotX1, Y1, rgbHex(0x000004));
    // Resolution per register: long frames where pitch matters, short ones for the highs (hats, clicks).
    std::vector<SpecLayer> layers{
        {d.L.data(), d.R.data(), static_cast<std::int64_t>(d.L.size()), d.rate, 1024, 0.0, 150.0},       // ~6 Hz, ~170 ms
        {m.mixL.data(), m.mixR.data(), len, sr, scaledN(4096, sr), 150.0, 600.0},                        // ~12 Hz, ~85 ms
        {m.mixL.data(), m.mixR.data(), len, sr, scaledN(2048, sr), 600.0, 2000.0},                       // ~23 Hz, ~43 ms
        {m.mixL.data(), m.mixR.data(), len, sr, scaledN(1024, sr), 2000.0, 1e9}};                        // ~47 Hz, ~21 ms
    if (!m.mixL.empty()) paint(c, spectrogramDb(layers, cols, kSpecH, tm.t0, tm.pxSec(), kFMin, fMax), cols, kSpecH, Y0);
    drawFrequencyFrame(c, Y0, Y1, fMax, false);

    // Level strip in dBFS: RMS per column (filled) and sample peak (line) of the whole mix, so
    // transients, sidechain pumping and decays stay visible even in a limited master.
    c.fillRect(kPlotX0, yWave, kPlotX1, yWave + kWaveH, kPanel);
    {
        constexpr double kTop = 0.0, kBottom = -42.0;
        auto yOf = [&](double db) {
            return yWave + static_cast<int>(std::lround((kTop - std::clamp(db, kBottom, kTop)) / (kTop - kBottom) * (kWaveH - 1)));
        };
        for (double db : {-6.0, -12.0, -18.0, -24.0, -30.0, -36.0}) c.dashedHline(kPlotX0, kPlotX1 - 1, yOf(db), kWhite, 2, 5, 0.12);
        const double spc = tm.pxSec() * sr;
        int prevPk = -1;
        for (int col = 0; col < cols; ++col) {
            const auto s0 = std::max<std::int64_t>(0, static_cast<std::int64_t>(tm.t0 * sr + col * spc));
            const auto s1 = std::min(len, std::max(s0 + 1, static_cast<std::int64_t>(tm.t0 * sr + (col + 1) * spc)));
            float pk = 0.0f;
            double sq = 0.0;
            for (std::int64_t i = s0; i < s1; ++i) {
                const float l = m.mixL[static_cast<std::size_t>(i)], r = m.mixR[static_cast<std::size_t>(i)];
                pk = std::max(pk, std::max(std::fabs(l), std::fabs(r)));
                sq += 0.5 * (static_cast<double>(l) * l + static_cast<double>(r) * r);
            }
            if (s1 <= s0) continue;
            const double rmsDb = dbFromPower(sq / static_cast<double>(s1 - s0)), pkDb = dbFromAmplitude(pk);
            const int X = kPlotX0 + col;
            if (rmsDb > kBottom) c.vline(X, yOf(rmsDb), yWave + kWaveH - 1, kWaveRms, 0.8);
            const int yp = yOf(pkDb);
            if (pkDb > kBottom) c.vline(X, prevPk >= 0 ? std::min(prevPk, yp) : yp, prevPk >= 0 ? std::max(prevPk, yp) : yp, kWavePeak);
            prevPk = pkDb > kBottom ? yp : -1;
        }
        c.text(8, yWave + 4, "LEVEL dBFS", kText, 2);
        c.text(8, yWave + 4 + kLine, "line = peak", rgbHex(0x5b86e6), 2);
        c.text(8, yWave + 4 + 2 * kLine, "fill = RMS", kWaveRms, 2);
        c.text(kPlotX1 + 8, yWave + 2, "0", kDim, 2);
        c.text(kPlotX1 + 8, yOf(-24.0) - 8, "-24", kDim, 2);
        c.text(kPlotX1 + 8, yWave + kWaveH - 18, "-42", kDim, 2);
    }

    const double b0 = 1.0 + m.barAt(m.beatAt(z.startSec)), b1 = m.barAt(m.beatAt(z.endSec));
    double lufs = kDbFloor;
    for (const auto& s : m.sections)
        if (s.name == z.name && std::fabs(s.startSec - z.startSec) < 0.05) lufs = s.lufs;
    const double colMs = tm.pxSec() * 1000.0;
    drawTitle(c, sfmt("SPECTROGRAM %d/%d", static_cast<int>(index) + 1, static_cast<int>(m.zooms.size())),
              sfmt("'%s' bars %.0f-%.0f | %s-%s |%s %.0f ms/px, frames 21 ms (highs)..170 ms (sub) | beat grid",
                   z.name.c_str(), std::floor(b0 + 1e-6), std::ceil(b1 - 1e-6), mmss(z.startSec).c_str(), mmss(z.endSec).c_str(),
                   lufs > -70.0 ? sfmt(" %.1f LUFS |", lufs).c_str() : "", colMs),
              kCyan);
    drawTimeHeader(c, m, tm, kSectionY, kBarY, true);
    drawClickMarkers(c, m, tm, 78);
    drawTimeGrid(c, m, tm, Y0, yEnd - 1, true);
    c.rectOutline(kPlotX0 - 1, Y0 - 1, kPlotX1, Y1, kGrid);
    panelFrame(c, kPlotX0, yWave, kPlotX1, yWave + kWaveH);
    drawTimeAxis(c, tm, yEnd + 2);
    writePng(path, c.image());
}

}  // namespace

void renderSpectrogram(const MixImpl& m, const std::string& path) { renderWhole(m, decimateMix(m), path); }

void renderSpectrograms(const MixImpl& m, const std::string& dir, bool whole, bool sectionZooms) {
    const Decimated d = decimateMix(m);
    if (whole) renderWhole(m, d, dir + "/spectrogram.png");
    if (sectionZooms)
        for (std::size_t i = 0; i < m.zooms.size(); ++i) renderZoom(m, d, i, dir + "/" + m.zooms[i].file);
}

}  // namespace as::analysis
