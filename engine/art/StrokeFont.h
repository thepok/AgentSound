#pragma once

// "AgentSound Geo": a geometric skeleton (single-line) vector font drawn for this project and dedicated
// to the public domain (CC0). Glyphs are centre-line paths (lines, circle/ellipse arcs, Béziers) on a
// 100-unit cap height (x-height 70, descender -30); the renderer strokes them with a pen, so one
// skeleton gives every weight from hairline to black, round (neon tube / rounded) or square (crisp
// geometric) stroke ends, italic shear, condensed/extended widths, and a high-contrast "modern" serif
// variant (thin horizontals, thick verticals, hairline serifs) for classical covers.
//
// Coverage: printable ASCII, German umlauts and eszett, common Western accents (a e i o u c n with
// acute / grave / circumflex / diaeresis / tilde / cedilla / ring), en/em dash, curly quotes,
// ellipsis, degree, multiplication sign. Other characters render as '?'.
//
// Text is laid out on a baseline and rendered as a signed distance field (distance in pixels to the
// stroked outline, negative inside), from which covers derive fills, outlines, bevels and glows.

#include "art/Raster.h"

#include <string>
#include <vector>

namespace as::art {

struct FontStyle {
    double weight{0.14};       // pen width / cap height: 0.04 hairline, 0.10 light, 0.14 regular, 0.22 bold, 0.30 black
    double contrast{0.0};      // 0 monoline .. 1: horizontal strokes shrink to 20 % of the pen (vertical stress, Didone-like)
    double slant{0.0};         // italic shear, tan(angle) (0.2 ~ 11 degrees)
    double widthScale{1.0};    // letterform width: 0.72 condensed .. 1.25 extended
    double tracking{0.0};      // extra letter spacing / cap height
    bool squareCaps{false};    // square stroke ends, cut flat at the baseline / cap height (crisp) instead of round (neon)
    bool serifs{false};        // hairline serifs on the ends of vertical stems
};

// A line of text laid out in pixel coordinates (y down). Build with layoutText().
struct TextLayout {
    struct Seg {
        Vec2 a, b;
        float halfWidth;           // pen half width (px)
        bool squareA, squareB;     // square end at a / b (terminal + squareCaps)
    };
    struct GlyphShape {
        std::vector<Seg> segs;
        double clipTop, clipBottom;  // y range the glyph may cover (square caps cut here); +-inf when unclipped
        double x0, y0, x1, y1;       // bounding box of the outline (px)
    };
    std::vector<GlyphShape> glyphs;
    double x0{0}, y0{0}, x1{0}, y1{0};  // bounding box of the whole line (px)
    double advance{0};                  // pen advance (px), start of the line to the end of the last glyph
    double capHeight{0};                // px
    Vec2 origin{};                      // start of the baseline (px)
    double penHalfWidth{0};             // half the pen width of vertical stems (px)
};

// UTF-8 text on a baseline starting at `origin` (px, y down) with the given cap height in px.
TextLayout layoutText(const std::string& utf8, const FontStyle& style, double capHeightPx, Vec2 origin);
// Width (advance) of the text in px without laying it out at a position.
double measureText(const std::string& utf8, const FontStyle& style, double capHeightPx);
// Cap height that makes the text exactly `widthPx` wide (advance).
double capHeightForWidth(const std::string& utf8, const FontStyle& style, double widthPx);

// Signed distance (px) to the stroked text outline for every pixel of a w x h canvas: < 0 inside.
// Only pixels within `reach` px of the outline get exact values; farther ones hold +reach.
struct DistanceField {
    int width{0}, height{0};
    float reach{0};
    std::vector<float> d;
    float at(int x, int y) const noexcept {
        return (x < 0 || y < 0 || x >= width || y >= height) ? reach : d[static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + static_cast<std::size_t>(x)];
    }
};
DistanceField textDistance(const TextLayout& layout, int width, int height, double reach);
// Coverage mask of the text grown by `grow` px (0 = the outline itself, > 0 = an outline ring's outer edge).
Mask textMask(const DistanceField& field, double grow = 0.0);

// Characters of the font (for tests): every code point that has its own glyph.
std::vector<char32_t> fontCodePoints();
// Decodes UTF-8 (invalid bytes become U+FFFD).
std::u32string decodeUtf8(const std::string& s);

}  // namespace as::art
