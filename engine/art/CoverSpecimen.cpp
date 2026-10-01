// The font sheet: every glyph of the stroke font in the variants the covers use (agentsound cover
// --style specimen), for checking letterforms, spacing and effects.

#include "art/CoverStyles.h"

namespace as::art::styles {

void specimen(Raster& r, Ctx& c) {
    const double S = c.S, k = S / 1400.0;
    kit::verticalGradient(r, Gradient{{{0.0, hex(0x15171f)}, {1.0, hex(0x0d0e14)}}}, 0, S);
    struct Row {
        std::string text;
        FontStyle st;
        double cap;
        int effect;  // 0 flat, 1 neon, 2 chrome, 3 serif flat
    };
    FontStyle regular;
    regular.weight = 0.11;
    FontStyle sharp;
    sharp.weight = 0.2;
    sharp.squareCaps = true;
    sharp.slant = 0.2;
    FontStyle light;
    light.weight = 0.06;
    light.tracking = 0.08;
    FontStyle serif;
    serif.weight = 0.14;
    serif.contrast = 1.0;
    serif.serifs = true;
    serif.squareCaps = true;
    serif.tracking = 0.04;
    FontStyle neon;
    neon.weight = 0.08;
    neon.slant = 0.15;
    FontStyle condensed;
    condensed.weight = 0.26;
    condensed.widthScale = 0.74;
    condensed.squareCaps = true;
    condensed.tracking = -0.02;
    const std::vector<Row> rows = {
        {"ABCDEFGHIJKLMNOPQRSTUVWXYZ", regular, 44, 0},
        {"abcdefghijklmnopqrstuvwxyz 0123456789", regular, 44, 0},
        {".,:;!?'\"-()[]{}/\\|+=<>*#%&$@^~_", regular, 40, 0},
        {"\xC3\x84\xC3\x96\xC3\x9C\xC3\xA4\xC3\xB6\xC3\xBC\xC3\x9F \xC3\x89\xC3\x88\xC3\x8A\xC3\x81\xC3\x80\xC3\x87\xC3\x91 "
         "\xC3\xA9\xC3\xA8\xC3\xAA\xC3\xA1\xC3\xA0\xC3\xA2\xC3\xAD\xC3\xB3\xC3\xB4\xC3\xBA\xC3\xA7\xC3\xB1 \xE2\x80\xA6\xE2\x80\x94"
         "\xE2\x80\x9E\xE2\x80\x9C\xC2\xB0\xC3\x97",
         regular, 40, 0},
        {"NEON AFTERGLOW 1986", sharp, 70, 2},
        {"Midnight Interstate", light, 56, 0},
        {"Sonata in D minor, Op. 12", serif, 58, 3},
        {"Chrome Leviathan", neon, 64, 1},
        {"blue train at dawn", condensed, 74, 0},
    };
    double y = 40 * k;
    for (const auto& row : rows) {
        const double cap = row.cap * k;
        y += cap * 1.55;
        const TextLayout lay = layoutText(row.text, row.st, cap, {40 * k, y});
        for (int x = static_cast<int>(40 * k); x < static_cast<int>(S - 40 * k); ++x) {
            r.put(x, static_cast<int>(y), hex(0x3a4254), 0.8);
            r.put(x, static_cast<int>(y - cap), hex(0x2a3040), 0.8);
        }
        switch (row.effect) {
            case 1: {
                kit::NeonLook look;
                look.glow = hex(0xff3fd2);
                look.glowSigma = 6 * k;
                kit::drawNeon(r, lay, look);
                break;
            }
            case 2: {
                kit::ChromeLook look;
                look.face = Gradient{{{0.0, hex(0x0a1740)}, {0.34, hex(0x5fa8ff)}, {0.49, hex(0xf7fdff)}, {0.505, hex(0x3b1d0e)},
                                      {0.7, hex(0xb0521a)}, {1.0, hex(0xffd38a)}}};
                look.outline = hex(0x080312);
                look.outlineWidth = 3 * k;
                look.glow = hex(0xff38d1);
                look.glowSigma = 10 * k;
                look.bevel = 3 * k;
                kit::drawChrome(r, lay, look);
                break;
            }
            default:
                kit::drawFlat(r, lay, row.effect == 3 ? hex(0xf1e9d6) : hex(0xe8ecf4));
        }
        y += cap * 0.35;
    }
}

}  // namespace as::art::styles
