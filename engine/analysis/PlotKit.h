#pragma once

// Shared look of the analysis images: palette, text helpers, the common time frame (every
// timeline image maps time to the same x range, so images line up when compared), section/bar
// header, bar/section grid, mm:ss axis, click markers, and the spectral helpers.

#include "analysis/Canvas.h"
#include "analysis/StreamStats.h"

#include <cstdint>
#include <initializer_list>
#include <string>
#include <vector>

namespace as::analysis {

struct MixImpl;

// ------------------------------------------------------------------ palette

inline constexpr Rgb kBg = rgbHex(0x0e1016);
inline constexpr Rgb kPanel = rgbHex(0x161a22);
inline constexpr Rgb kLane = rgbHex(0x1b202a);
inline constexpr Rgb kGrid = rgbHex(0x3a4254);
inline constexpr Rgb kText = rgbHex(0xe4e8f0);
inline constexpr Rgb kDim = rgbHex(0x98a0b3);
inline constexpr Rgb kWhite = rgbHex(0xffffff);
inline constexpr Rgb kHeaderA = rgbHex(0x252b3b);
inline constexpr Rgb kHeaderB = rgbHex(0x1c2130);
inline constexpr Rgb kRed = rgbHex(0xff4d4d);
inline constexpr Rgb kAmber = rgbHex(0xffb020);
inline constexpr Rgb kCyan = rgbHex(0x55ccff);
inline constexpr Rgb kGreen = rgbHex(0x3ddc84);
inline constexpr Rgb kOrange = rgbHex(0xff8c42);
inline constexpr Rgb kBusText = rgbHex(0x7fd4ff);
inline constexpr Rgb kWavePeak = rgbHex(0x3563c9);
inline constexpr Rgb kWaveRms = rgbHex(0x9dbbff);
inline constexpr Rgb kBandColors[kNumBands] = {rgbHex(0x7b3fb0), rgbHex(0x2f6fdb), rgbHex(0x1fa3a3), rgbHex(0x49b04a),
                                               rgbHex(0xe0c02a), rgbHex(0xf08a24), rgbHex(0xe8505f)};

// Common frame of the timeline images.
inline constexpr int kImageW = 1600;
inline constexpr int kPlotX0 = 180;
inline constexpr int kPlotX1 = 1470;
inline constexpr int kTitleY = 8;
inline constexpr int kSectionY = 32;
inline constexpr int kBarY = 58;
inline constexpr int kPlotTop = 88;   // first row below the header (click markers sit at 78..86)
inline constexpr int kAxisH = 34;     // height of the time axis under the last panel
inline constexpr int kLine = 22;      // line pitch of scale-2 text

// ------------------------------------------------------------------ text

std::string sfmt(const char* f, ...) __attribute__((format(printf, 1, 2)));
std::string mmss(double sec);          // 1:05
std::string mmssMs(double sec);        // 1:05.250
std::string fitText(const std::string& s, int maxPx, int scale);
std::vector<std::string> wrapText(const std::string& s, int maxPx, int scale, int maxLines);
// Text on a translucent dark box (readable on top of heat maps).
void textBox(Canvas& c, int x, int y, const std::string& s, Rgb fg, int scale = 2, double alpha = 0.72);
double niceStep(double minStep, std::initializer_list<double> steps);

// ------------------------------------------------------------------ time frame

struct TimeMap {
    int x0{kPlotX0}, x1{kPlotX1};
    double t0{0.0}, dur{1.0};  // seconds shown: [t0, t0 + dur]
    int width() const { return x1 - x0; }
    double x(double sec) const { return x0 + (sec - t0) / dur * width(); }
    int xi(double sec) const;
    double secAt(double px) const { return t0 + (px - x0) / width() * dur; }
    double pxSec() const { return dur / width(); }
};

// Section strip (name + section LUFS) at ySec and bar numbers at yBar. beats: also beat ticks.
void drawTimeHeader(Canvas& c, const MixImpl& m, const TimeMap& tm, int ySec = kSectionY, int yBar = kBarY, bool beats = false);
// Bar grid (faint), section edges (dashed), optionally beat lines.
void drawTimeGrid(Canvas& c, const MixImpl& m, const TimeMap& tm, int yTop, int yBottom, bool beats = false);
// mm:ss (or m:ss.s for short spans) labels under y.
void drawTimeAxis(Canvas& c, const TimeMap& tm, int y);
// Red triangles for the detected clicks (node >= 0: only that node's clicks) in [y, y + 8].
void drawClickMarkers(Canvas& c, const MixImpl& m, const TimeMap& tm, int y, int node = -2);
// Title line; returns the x after it.
int drawTitle(Canvas& c, const std::string& head, const std::string& rest, Rgb headColor = kText);
// Horizontal colour-map legend: "<lo> [gradient] <hi> <unit>" starting at x; returns the end x.
int drawColorLegend(Canvas& c, int x, int y, int w, const std::string& lo, const std::string& hi, const std::string& unit,
                    Rgb (*map)(double), bool diverging = false);
void panelFrame(Canvas& c, int x0, int y0, int x1, int y1);  // outline around [x0,x1) x [y0,y1)
// Left-column caption lines: first line bright, the rest in their colours.
void caption(Canvas& c, int x, int y, std::initializer_list<std::pair<const char*, Rgb>> lines);

// Range of 100 ms ticks overlapping [t0, t1) seconds (at least one tick while any exist).
struct TickSpan {
    std::size_t i0{0}, i1{0};
};
TickSpan ticksFor(const StreamStats& s, double tickSec, double t0, double t1);

// ------------------------------------------------------------------ spectra

// Averaged power spectra ((|L|^2 + |R|^2)/2) of Hann-windowed frames for `cols` columns covering
// samples [start, start + cols * samplesPerCol) of L/R (zero outside [0, len)). Frames are spaced
// <= n/2 apart. Returns cols x (n/2+1) values, bins summing to the frame's mean square.
std::vector<float> columnSpectra(const float* L, const float* R, std::int64_t len, int n, int cols, double start,
                                 double samplesPerCol);
// Kaiser-windowed sinc decimation by `factor` (flat to ~0.08 of the new rate).
std::vector<float> decimate(const std::vector<float>& x, int factor);
// Energy of one spectrum in [f0, f1).
double rowEnergy(const float* p, int half, double df, double f0, double f1);

// One layer of a multi-resolution spectrogram: an FFT size on a (decimated) signal, used for the
// rows between fLo and fHi (crossfaded over half an octave at interior edges).
struct SpecLayer {
    const float* L;
    const float* R;
    std::int64_t len;
    double rate;   // sample rate of L/R
    int n;         // FFT size
    double fLo, fHi;
};
// dB grid rows x cols (row 0 = fMax) of [t0Sec, t0Sec + cols * secPerCol).
std::vector<float> spectrogramDb(const std::vector<SpecLayer>& layers, int cols, int rows, double t0Sec, double secPerCol,
                                 double fMin, double fMax);

}  // namespace as::analysis
