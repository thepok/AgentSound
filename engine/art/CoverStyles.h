#pragma once

// Internal: the style renderers of art/Cover.h and their palettes.

#include "art/Cover.h"
#include "art/CoverKit.h"

namespace as::art::styles {

struct Ctx {
    const CoverSpec& spec;
    int S;                       // canvas size (px)
    std::vector<Color> pal;      // resolved palette roles (see each style's palette table)
    Random rng;
    std::uint32_t seed;
    double k() const { return S / 1400.0; }  // scale of pixel sizes designed at 1400 px
};

std::vector<kit::Palette> retroPalettes(const std::string& style);    // synthwave, outrun, dreamwave, darksynth
std::vector<kit::Palette> classicPalettes(const std::string& style);  // jazz, classical, rock, pop

void synthwave(Raster& r, Ctx& c);
void outrun(Raster& r, Ctx& c);
void dreamwave(Raster& r, Ctx& c);
void darksynth(Raster& r, Ctx& c);
void jazz(Raster& r, Ctx& c);
void classical(Raster& r, Ctx& c);
void rock(Raster& r, Ctx& c);
void pop(Raster& r, Ctx& c);
void specimen(Raster& r, Ctx& c);

}  // namespace as::art::styles
