#pragma once

// Small float raster toolkit for the cover art (engine/art/Cover.cpp): an RGB canvas in sRGB space
// (like a design tool: gradients are designed in it), coverage masks, anti-aliased shapes (polygons
// with exact horizontal coverage on 16 sub-scanlines, analytic circles, distance-field strokes),
// Gaussian-like blur, deterministic value noise and the dithered conversion to 8-bit RGB (so smooth
// sky gradients do not band). Everything is deterministic: the same calls give the same bytes.

#include "analysis/Png.h"  // analysis::Image

#include <algorithm>
#include <cstdint>
#include <utility>
#include <vector>

namespace as::art {

struct Vec2 {
    double x{0.0}, y{0.0};
};

struct Color {
    float r{0.0f}, g{0.0f}, b{0.0f};
};

constexpr Color hex(std::uint32_t v) noexcept {
    return {static_cast<float>((v >> 16) & 0xff) / 255.0f, static_cast<float>((v >> 8) & 0xff) / 255.0f,
            static_cast<float>(v & 0xff) / 255.0f};
}
Color lerp(Color a, Color b, double t) noexcept;          // t clamped to 0..1
Color scale(Color c, double k) noexcept;
Color addc(Color a, Color b) noexcept;
double luma(Color c) noexcept;
Color saturate(Color c, double amount) noexcept;           // 1 = unchanged, 0 = grey, > 1 = more saturated

// Piecewise-linear colour ramp over 0..1 (stops sorted by position).
struct Gradient {
    std::vector<std::pair<double, Color>> stops;
    Color at(double t) const noexcept;
};

enum class Blend { Normal, Add, Screen, Multiply, Overlay, SoftLight };

class Raster {
public:
    Raster(int width, int height, Color fill = {});
    int width() const noexcept { return w_; }
    int height() const noexcept { return h_; }
    Color& at(int x, int y) noexcept { return px_[static_cast<std::size_t>(y) * static_cast<std::size_t>(w_) + static_cast<std::size_t>(x)]; }
    const Color& at(int x, int y) const noexcept { return px_[static_cast<std::size_t>(y) * static_cast<std::size_t>(w_) + static_cast<std::size_t>(x)]; }
    bool inside(int x, int y) const noexcept { return x >= 0 && y >= 0 && x < w_ && y < h_; }
    // Composites colour c with opacity a (0..1) onto pixel (x, y); out-of-range pixels are ignored.
    void put(int x, int y, Color c, double a, Blend mode = Blend::Normal) noexcept;
    std::vector<Color>& pixels() noexcept { return px_; }
    const std::vector<Color>& pixels() const noexcept { return px_; }

private:
    int w_, h_;
    std::vector<Color> px_;
};

// Coverage / alpha mask, 0..1 per pixel.
class Mask {
public:
    Mask(int width, int height) : w_(width), h_(height), a_(static_cast<std::size_t>(width) * static_cast<std::size_t>(height), 0.0f) {}
    int width() const noexcept { return w_; }
    int height() const noexcept { return h_; }
    float& at(int x, int y) noexcept { return a_[static_cast<std::size_t>(y) * static_cast<std::size_t>(w_) + static_cast<std::size_t>(x)]; }
    float at(int x, int y) const noexcept { return a_[static_cast<std::size_t>(y) * static_cast<std::size_t>(w_) + static_cast<std::size_t>(x)]; }
    float sample(int x, int y) const noexcept { return (x < 0 || y < 0 || x >= w_ || y >= h_) ? 0.0f : at(x, y); }
    std::vector<float>& data() noexcept { return a_; }
    const std::vector<float>& data() const noexcept { return a_; }
    void clear() noexcept;
    void maxWith(const Mask& o) noexcept;    // union
    void multiply(const Mask& o) noexcept;   // intersection
    void invert() noexcept;
    void scaleBy(float k) noexcept;

private:
    int w_, h_;
    std::vector<float> a_;
};

// Paints every covered pixel of `m` with shade(x, y) at opacity coverage * alpha.
template <class Shader>
void paint(Raster& r, const Mask& m, Shader&& shade, double alpha = 1.0, Blend mode = Blend::Normal) {
    const int w = std::min(r.width(), m.width()), h = std::min(r.height(), m.height());
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x) {
            const float a = m.at(x, y);
            if (a > 0.0f) r.put(x, y, shade(x, y), a * alpha, mode);
        }
}
// Paints a solid colour through a mask.
void paintSolid(Raster& r, const Mask& m, Color c, double alpha = 1.0, Blend mode = Blend::Normal);

// ------------------------------------------------------------------ shapes (into masks, max-combined)

// Polygon with any number of contours (nonzero winding), anti-aliased: 16 sub-scanlines per pixel
// with exact horizontal span coverage.
void fillPolygon(Mask& m, const std::vector<std::vector<Vec2>>& contours);
void fillPolygon(Mask& m, const std::vector<Vec2>& contour);
// Circle / ellipse with analytic edge coverage; feather > 0 softens the edge over that many pixels.
void fillEllipse(Mask& m, double cx, double cy, double rx, double ry, double feather = 0.0);
// Polyline of the given width (round caps and joins), coverage from the distance to the segments.
void strokePolyline(Mask& m, const std::vector<Vec2>& pts, double width, bool closed = false);
void strokeLine(Mask& m, Vec2 a, Vec2 b, double width);

// ------------------------------------------------------------------ filters

void blur(Mask& m, double sigma);     // ~Gaussian (three box passes per axis)
void blur(Raster& r, double sigma);

// ------------------------------------------------------------------ noise (deterministic)

std::uint32_t hash32(std::uint32_t x) noexcept;
double hashUnit(int x, int y, std::uint32_t seed) noexcept;              // white noise 0..1
double valueNoise(double x, double y, std::uint32_t seed) noexcept;      // smooth 0..1 (lattice 1)
double fbm(double x, double y, int octaves, std::uint32_t seed) noexcept;  // 0..1, octaves of valueNoise

// Small deterministic RNG for layout decisions (stars, positions).
class Random {
public:
    explicit Random(std::uint64_t seed) noexcept;
    std::uint64_t next() noexcept;
    double uniform() noexcept;                  // [0, 1)
    double range(double lo, double hi) noexcept;
    int below(int n) noexcept;                  // [0, n)

private:
    std::uint64_t s_;
};

// 8-bit RGB with +-0.5 LSB hashed dither (no banding in smooth gradients).
analysis::Image toImage(const Raster& r, std::uint32_t seed);

}  // namespace as::art
