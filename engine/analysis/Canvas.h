#pragma once

// Minimal RGB raster canvas for the analysis plots: rectangles, lines, alpha blending,
// bitmap text and perceptual colour maps.

#include "analysis/Png.h"

#include <cstdint>
#include <string_view>

namespace as::analysis {

struct Rgb {
    std::uint8_t r{0}, g{0}, b{0};
};
constexpr Rgb rgbHex(std::uint32_t hex) noexcept {
    return {static_cast<std::uint8_t>(hex >> 16), static_cast<std::uint8_t>(hex >> 8), static_cast<std::uint8_t>(hex)};
}
Rgb mixRgb(Rgb a, Rgb b, double t) noexcept;  // a*(1-t) + b*t

Rgb inferno(double t) noexcept;       // t in [0,1], perceptually uniform (matplotlib "inferno")
Rgb viridis(double t) noexcept;       // t in [0,1] (matplotlib "viridis")
Rgb divergingDark(double t) noexcept; // t in [-1,1]: blue .. dark grey .. red

class Canvas {
public:
    Canvas(int width, int height, Rgb background);
    int width() const noexcept { return img_.width; }
    int height() const noexcept { return img_.height; }

    void set(int x, int y, Rgb c) noexcept;
    void blend(int x, int y, Rgb c, double alpha) noexcept;
    void fillRect(int x0, int y0, int x1, int y1, Rgb c) noexcept;  // half-open [x0,x1) x [y0,y1)
    void blendRect(int x0, int y0, int x1, int y1, Rgb c, double alpha) noexcept;
    void rectOutline(int x0, int y0, int x1, int y1, Rgb c) noexcept;  // inclusive corners
    void hline(int x0, int x1, int y, Rgb c, double alpha = 1.0) noexcept;  // inclusive
    void vline(int x, int y0, int y1, Rgb c, double alpha = 1.0) noexcept;  // inclusive
    void dashedHline(int x0, int x1, int y, Rgb c, int on, int off, double alpha = 1.0) noexcept;
    void dashedVline(int x, int y0, int y1, Rgb c, int on, int off, double alpha = 1.0) noexcept;
    void line(double x0, double y0, double x1, double y1, Rgb c, int thickness = 1, double alpha = 1.0) noexcept;

    // Bitmap text; (x, y) = top-left of the glyph cell. Returns the drawn width in pixels.
    int text(int x, int y, std::string_view s, Rgb c, int scale = 2) noexcept;
    static int textWidth(std::string_view s, int scale = 2) noexcept;  // glyphs are 9*scale px tall

    const Image& image() const noexcept { return img_; }

private:
    Image img_;
};

}  // namespace as::analysis
