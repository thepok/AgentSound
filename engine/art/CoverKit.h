#pragma once

// Shared building blocks of the cover styles (engine/art/Cover*.cpp): palettes, title fitting, text
// effects (chrome, neon, flat, shadow, distressed), backgrounds and finishing passes. Internal.

#include "art/Raster.h"
#include "art/StrokeFont.h"

#include <string>
#include <vector>

namespace as::art::kit {

// A named palette: role colours in a style-specific order (see each style's comment).
struct Palette {
    const char* name;
    std::vector<Color> c;
};

// The palette colours for `spec`: "" = the first (default) palette; a palette name; or a list of
// 1-3 hex colours "#rrggbb,#rrggbb" that replace the first roles of the default palette (the style's
// main accents). Throws ConfigError on an unknown name or a malformed list.
std::vector<Color> resolvePalette(const std::string& style, const std::vector<Palette>& palettes, const std::string& spec);

// Title broken into at most maxLines lines (word breaks balanced) at the largest cap height <= maxCap
// that keeps every line within maxWidth.
struct TitleFit {
    std::vector<std::string> lines;
    double cap{0.0};
};
TitleFit fitTitle(const std::string& text, const FontStyle& st, double maxWidth, double maxCap, int maxLines = 2);
// Upper-case (ASCII + German umlauts / common accents).
std::string upper(const std::string& utf8);
std::string lower(const std::string& utf8);

// Lays out `line` centred on centreX with its baseline at baselineY.
TextLayout centred(const std::string& line, const FontStyle& st, double cap, double centreX, double baselineY);

// ------------------------------------------------------------------ text effects

struct ChromeLook {
    Gradient face;             // over the cap height, top (0) to baseline (1)
    Color outline{};           // dark rim
    double outlineWidth{3.0};  // px
    Color glow{};              // outer glow (added)
    double glowSigma{12.0}, glowStrength{0.8};
    Color highlight{1.0f, 1.0f, 1.0f};  // bevel light (top-left edges)
    double bevel{4.0};         // px
    double shadowAlpha{0.0};   // soft drop shadow under everything
};
void drawChrome(Raster& r, const TextLayout& lay, const ChromeLook& look);

struct NeonLook {
    Color glow{};
    double glowSigma{10.0}, glowStrength{1.0};
    double coreWhite{0.65};    // how white-hot the tube's centre is
    double flicker{0.0};       // 0..1: a few letters dimmer (seeded)
    std::uint32_t seed{1};
};
void drawNeon(Raster& r, const TextLayout& lay, const NeonLook& look);

void drawFlat(Raster& r, const TextLayout& lay, Color fill, double alpha = 1.0, Blend mode = Blend::Normal);
void drawShadow(Raster& r, const TextLayout& lay, Color c, Vec2 offset, double sigma, double alpha, double grow = 0.0);
// Text with an eroded, inked look (rock): the fill multiplied by a noise threshold.
void drawDistressed(Raster& r, const TextLayout& lay, Color fill, double wear, std::uint32_t seed);
// Paints the text with a colour function of the pixel (gradients through the letters).
template <class Shader>
void drawShaded(Raster& r, const TextLayout& lay, Shader&& shade, double alpha = 1.0) {
    const DistanceField f = textDistance(lay, r.width(), r.height(), 3.0);
    paint(r, textMask(f), shade, alpha);
}

// ------------------------------------------------------------------ backgrounds and finishing

void verticalGradient(Raster& r, const Gradient& g, double y0, double y1);  // t = (y - y0) / (y1 - y0), clamped
// Soft round light: exp(-(d/radius)^2) falloff.
void radialGlow(Raster& r, Vec2 c, double radius, Color color, double strength, Blend mode = Blend::Add);
void grain(Raster& r, double amount, std::uint32_t seed);                    // film grain (luma noise)
void vignette(Raster& r, double strength, double inner = 0.55);            // darkens the corners
void scanlines(Raster& r, double period, double strength);
void bloom(Raster& r, double threshold, double sigma, double strength);    // glow of the bright parts
void halftone(Raster& r, const Mask& area, double cell, double angleDeg, Color ink, double gamma = 1.0);

// Mask of everything above a ridge line y(x) (mountains etc. use the complement).
Mask ridgeMask(int w, int h, const std::vector<Vec2>& ridge, bool below);

}  // namespace as::art::kit
