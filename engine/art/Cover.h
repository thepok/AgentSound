#pragma once

// Album covers for the delivered mp3 (`agentsound cover`, python -m agentsound build -> out/cover.png).
// Deterministic (same spec -> same bytes), square, anti-aliased, one renderer per genre style:
//   synthwave   night sky gradient, stars, striped sun with glow, magenta perspective grid, chrome title
//   outrun      sunset, sun behind mountains, perspective road with lane marks, palm silhouettes, chrome title
//   dreamwave   pastel haze: soft sun, clouds, faint grid, bloom, thin wide-spaced white title
//   darksynth   black and red, harsh: neon triangle, jagged mountains, red grid, glitch slices, grain
//   jazz        mid-century record sleeve: flat colour, colour blocks, duotone halftone "photo",
//               big bold condensed lower-case type
//   classical   elegant minimal: paper, fine rules, thin gold circle, high-contrast serif capitals
//   rock        gritty high contrast: black, distressed white capitals, red accents, scratches, halftone
//   pop         bold gradients: colour blobs, a glossy sphere, heavy rounded type with a soft shadow
// Text uses the project's stroke font (art/StrokeFont.h); titles wrap onto two lines when long.
// "specimen" renders the font sheet (all glyphs, weights and variants) for checking the font.

#include "analysis/Png.h"  // analysis::Image

#include <cstdint>
#include <string>
#include <vector>

namespace as::art {

struct CoverSpec {
    std::string style{"synthwave"};
    std::string title;
    std::string subtitle;
    std::string palette;       // "" = the style's default; a palette name of the style or "#rrggbb,#rrggbb[,#rrggbb]"
    std::uint64_t seed{1};
    int size{1400};            // 256..4000 px
};

std::vector<std::string> coverStyles();                        // the styles above (without "specimen")
std::vector<std::string> coverPalettes(const std::string& style);  // palette names of a style, default first

// Throws ConfigError for an unknown style / palette, a malformed colour list or a size outside 256..4000.
analysis::Image renderCover(const CoverSpec& spec);

}  // namespace as::art
