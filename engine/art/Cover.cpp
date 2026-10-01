#include "art/Cover.h"

#include "art/CoverStyles.h"
#include "core/Params.h"  // ConfigError

#include <algorithm>

namespace as::art {

namespace {

using Renderer = void (*)(Raster&, styles::Ctx&);

struct StyleEntry {
    const char* name;
    Renderer render;
    bool retro;
};

constexpr StyleEntry kStyles[] = {
    {"synthwave", styles::synthwave, true}, {"outrun", styles::outrun, true},   {"dreamwave", styles::dreamwave, true},
    {"darksynth", styles::darksynth, true}, {"jazz", styles::jazz, false},      {"classical", styles::classical, false},
    {"rock", styles::rock, false},          {"pop", styles::pop, false},
};

std::vector<kit::Palette> palettesOf(const StyleEntry& s) {
    return s.retro ? styles::retroPalettes(s.name) : styles::classicPalettes(s.name);
}

}  // namespace

std::vector<std::string> coverStyles() {
    std::vector<std::string> v;
    for (const auto& s : kStyles) v.push_back(s.name);
    return v;
}

std::vector<std::string> coverPalettes(const std::string& style) {
    std::vector<std::string> v;
    for (const auto& s : kStyles)
        if (style == s.name)
            for (const auto& p : palettesOf(s)) v.push_back(p.name);
    return v;
}

analysis::Image renderCover(const CoverSpec& spec) {
    if (spec.size < 256 || spec.size > 4000) throw ConfigError("cover size must be 256..4000 px");
    const auto seed = static_cast<std::uint32_t>(spec.seed ^ (spec.seed >> 32));
    if (spec.style == "specimen") {
        Raster r(spec.size, spec.size);
        styles::Ctx c{spec, spec.size, {}, Random(spec.seed), seed};
        styles::specimen(r, c);
        return toImage(r, seed);
    }
    const StyleEntry* entry = nullptr;
    std::string names;
    for (const auto& s : kStyles) {
        if (spec.style == s.name) entry = &s;
        names += (names.empty() ? "" : ", ") + std::string(s.name);
    }
    if (!entry) throw ConfigError("unknown cover style '" + spec.style + "' (styles: " + names + ")");
    std::vector<Color> pal = kit::resolvePalette(spec.style, palettesOf(*entry), spec.palette);
    Raster r(spec.size, spec.size);
    styles::Ctx c{spec, spec.size, std::move(pal), Random(spec.seed * 7919u + 17u), seed};
    entry->render(r, c);
    return toImage(r, seed);
}

}  // namespace as::art
