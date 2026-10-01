#include "analysis/Canvas.h"

#include "analysis/Font.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace as::analysis {

namespace {

Rgb lerpTable(const std::uint32_t* table, int n, double t) noexcept {
    if (!(t > 0.0)) return rgbHex(table[0]);
    if (t >= 1.0) return rgbHex(table[n - 1]);
    const double pos = t * (n - 1);
    const int i = static_cast<int>(pos);
    return mixRgb(rgbHex(table[i]), rgbHex(table[i + 1]), pos - i);
}

}  // namespace

Rgb mixRgb(Rgb a, Rgb b, double t) noexcept {
    t = std::clamp(t, 0.0, 1.0);
    auto m = [t](std::uint8_t x, std::uint8_t y) {
        return static_cast<std::uint8_t>(std::lround(x + (static_cast<double>(y) - x) * t));
    };
    return {m(a.r, b.r), m(a.g, b.g), m(a.b, b.b)};
}

Rgb inferno(double t) noexcept {
    static constexpr std::uint32_t kInferno[] = {0x000004, 0x160b39, 0x420a68, 0x6a176e, 0x932667, 0xbc3754,
                                                 0xdd513a, 0xf37819, 0xfca50a, 0xf6d746, 0xfcffa4};
    return lerpTable(kInferno, 11, t);
}

Rgb viridis(double t) noexcept {
    static constexpr std::uint32_t kViridis[] = {0x440154, 0x482475, 0x414487, 0x355f8d, 0x2a788e, 0x21918c,
                                                 0x22a884, 0x44bf70, 0x7ad151, 0xbddf26, 0xfde725};
    return lerpTable(kViridis, 11, t);
}

Rgb divergingDark(double t) noexcept {
    static constexpr std::uint32_t kDiv[] = {0x5aa9ff, 0x2f6fd6, 0x24407a, 0x2a2d36, 0x7a2a2a, 0xd63b2f, 0xff8a5a};
    return lerpTable(kDiv, 7, (std::clamp(t, -1.0, 1.0) + 1.0) * 0.5);
}

Canvas::Canvas(int width, int height, Rgb bg) {
    img_.width = std::max(1, width);
    img_.height = std::max(1, height);
    img_.rgb.resize(static_cast<std::size_t>(img_.width) * static_cast<std::size_t>(img_.height) * 3);
    for (std::size_t i = 0; i < img_.rgb.size(); i += 3) {
        img_.rgb[i] = bg.r;
        img_.rgb[i + 1] = bg.g;
        img_.rgb[i + 2] = bg.b;
    }
}

void Canvas::set(int x, int y, Rgb c) noexcept {
    if (x < 0 || y < 0 || x >= img_.width || y >= img_.height) return;
    std::uint8_t* p = &img_.rgb[(static_cast<std::size_t>(y) * static_cast<std::size_t>(img_.width) + static_cast<std::size_t>(x)) * 3];
    p[0] = c.r;
    p[1] = c.g;
    p[2] = c.b;
}

void Canvas::blend(int x, int y, Rgb c, double alpha) noexcept {
    if (x < 0 || y < 0 || x >= img_.width || y >= img_.height) return;
    std::uint8_t* p = &img_.rgb[(static_cast<std::size_t>(y) * static_cast<std::size_t>(img_.width) + static_cast<std::size_t>(x)) * 3];
    const Rgb m = mixRgb({p[0], p[1], p[2]}, c, alpha);
    p[0] = m.r;
    p[1] = m.g;
    p[2] = m.b;
}

void Canvas::fillRect(int x0, int y0, int x1, int y1, Rgb c) noexcept {
    x0 = std::max(x0, 0); y0 = std::max(y0, 0);
    x1 = std::min(x1, img_.width); y1 = std::min(y1, img_.height);
    for (int y = y0; y < y1; ++y)
        for (int x = x0; x < x1; ++x) set(x, y, c);
}

void Canvas::blendRect(int x0, int y0, int x1, int y1, Rgb c, double alpha) noexcept {
    x0 = std::max(x0, 0); y0 = std::max(y0, 0);
    x1 = std::min(x1, img_.width); y1 = std::min(y1, img_.height);
    for (int y = y0; y < y1; ++y)
        for (int x = x0; x < x1; ++x) blend(x, y, c, alpha);
}

void Canvas::rectOutline(int x0, int y0, int x1, int y1, Rgb c) noexcept {
    hline(x0, x1, y0, c);
    hline(x0, x1, y1, c);
    vline(x0, y0, y1, c);
    vline(x1, y0, y1, c);
}

void Canvas::hline(int x0, int x1, int y, Rgb c, double alpha) noexcept {
    if (x0 > x1) std::swap(x0, x1);
    for (int x = x0; x <= x1; ++x) alpha >= 1.0 ? set(x, y, c) : blend(x, y, c, alpha);
}

void Canvas::vline(int x, int y0, int y1, Rgb c, double alpha) noexcept {
    if (y0 > y1) std::swap(y0, y1);
    for (int y = y0; y <= y1; ++y) alpha >= 1.0 ? set(x, y, c) : blend(x, y, c, alpha);
}

void Canvas::dashedHline(int x0, int x1, int y, Rgb c, int on, int off, double alpha) noexcept {
    if (x0 > x1) std::swap(x0, x1);
    const int period = std::max(1, on + off);
    for (int x = x0; x <= x1; ++x)
        if ((x - x0) % period < on) alpha >= 1.0 ? set(x, y, c) : blend(x, y, c, alpha);
}

void Canvas::dashedVline(int x, int y0, int y1, Rgb c, int on, int off, double alpha) noexcept {
    if (y0 > y1) std::swap(y0, y1);
    const int period = std::max(1, on + off);
    for (int y = y0; y <= y1; ++y)
        if ((y - y0) % period < on) alpha >= 1.0 ? set(x, y, c) : blend(x, y, c, alpha);
}

void Canvas::line(double x0, double y0, double x1, double y1, Rgb c, int thickness, double alpha) noexcept {
    const double dx = x1 - x0, dy = y1 - y0;
    const int steps = std::max(1, static_cast<int>(std::ceil(std::max(std::fabs(dx), std::fabs(dy)))));
    const int lo = -(thickness - 1) / 2, hi = thickness / 2;
    int lastX = std::numeric_limits<int>::min(), lastY = lastX;
    for (int s = 0; s <= steps; ++s) {
        const int x = static_cast<int>(std::lround(x0 + dx * s / steps));
        const int y = static_cast<int>(std::lround(y0 + dy * s / steps));
        if (x == lastX && y == lastY) continue;
        lastX = x;
        lastY = y;
        for (int oy = lo; oy <= hi; ++oy)
            for (int ox = lo; ox <= hi; ++ox) alpha >= 1.0 ? set(x + ox, y + oy, c) : blend(x + ox, y + oy, c, alpha);
    }
}

int Canvas::textWidth(std::string_view s, int scale) noexcept {
    return s.empty() ? 0 : (static_cast<int>(s.size()) * kGlyphAdvance - 1) * scale;
}

int Canvas::text(int x, int y, std::string_view s, Rgb c, int scale) noexcept {
    int cx = x;
    for (char ch : s) {
        int idx = static_cast<unsigned char>(ch) - 32;
        if (idx < 0 || idx >= 95) idx = '?' - 32;
        const std::uint8_t* g = kFont5x9[idx];
        for (int row = 0; row < kGlyphH; ++row)
            for (int col = 0; col < kGlyphW; ++col)
                if (g[row] & (0x10 >> col))
                    for (int sy = 0; sy < scale; ++sy)
                        for (int sx = 0; sx < scale; ++sx) set(cx + col * scale + sx, y + row * scale + sy, c);
        cx += kGlyphAdvance * scale;
    }
    return textWidth(s, scale);
}

}  // namespace as::analysis
