#include "art/StrokeFont.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <limits>
#include <map>
#include <sstream>

namespace as::art {

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr double kCap = 100.0, kXh = 70.0, kDesc = -30.0;

// ------------------------------------------------------------------ glyph table
//
// Skeleton paths on the 100-unit cap height (y up). Commands (space separated):
//   M x y                  start a stroke          L x y          line to
//   A cx cy r a0 a1        circle arc from angle a0 to a1 (degrees, counter-clockwise when a1 > a0)
//   E cx cy rx ry a0 a1    ellipse arc             C x1 y1 x2 y2 x y   cubic Bezier
//   D x y                  a dot (a stroke of zero length)
// An arc continues the current stroke (a line joins it when the stroke ends elsewhere).
// adv = skeleton width; lsb / rsb adjust the side spacing (negative = tighter: round or open sides).

struct GlyphDef {
    char32_t cp;
    double adv, lsb, rsb;
    const char* path;
};

// clang-format off
constexpr GlyphDef kGlyphs[] = {
    {U' ', 34, 0, 0, ""},
    // capitals
    {U'A', 90, -5, -5, "M 0 0 L 45 100 L 90 0 M 15.3 34 L 74.7 34"},
    {U'B', 64, 0, -2, "M 0 52 L 38 52 M 0 0 L 0 100 L 36 100 A 36 76 24 90 -90 L 38 52 A 38 26 26 90 -90 L 0 0"},
    {U'C', 85.4, -3, -2, "A 50 50 50 45 315"},
    {U'D', 88, 0, -3, "M 0 0 L 0 100 L 38 100 A 38 50 50 90 -90 L 0 0"},
    {U'E', 60, 0, -1, "M 60 100 L 0 100 L 0 0 L 60 0 M 0 52 L 52 52"},
    {U'F', 58, 0, -2, "M 58 100 L 0 100 L 0 0 M 0 52 L 50 52"},
    {U'G', 100, -3, 0, "A 50 50 50 40 360 L 56 50"},
    {U'H', 78, 0, 0, "M 0 0 L 0 100 M 78 0 L 78 100 M 0 52 L 78 52"},
    {U'I', 0, 0, 0, "M 0 0 L 0 100"},
    {U'J', 52, -2, 0, "M 52 100 L 52 30 A 26 30 26 0 -180"},
    {U'K', 68, 0, -4, "M 0 0 L 0 100 M 64 100 L 0 36 M 24.3 60.3 L 68 0"},
    {U'L', 56, 0, -5, "M 0 100 L 0 0 L 56 0"},
    {U'M', 96, 0, 0, "M 0 0 L 0 100 L 48 2 L 96 100 L 96 0"},
    {U'N', 80, 0, 0, "M 0 0 L 0 100 L 80 0 L 80 100"},
    {U'O', 100, -3, -3, "A 50 50 50 90 450"},
    {U'P', 62, 0, -3, "M 0 0 L 0 100 L 36 100 A 36 74 26 90 -90 L 0 48"},
    {U'Q', 100, -3, -3, "A 50 50 50 90 450 M 60 30 L 98 -6"},
    {U'R', 66, 0, -3, "M 0 0 L 0 100 L 36 100 A 36 74 26 90 -90 L 0 48 M 32 48 L 66 0"},
    {U'S', 58, -2, -2, "A 29 75.5 24.5 35 270 A 29 25.5 25.5 90 -145"},
    {U'T', 72, -4, -4, "M 0 100 L 72 100 M 36 100 L 36 0"},
    {U'U', 78, 0, 0, "M 0 100 L 0 39 A 39 39 39 180 360 L 78 100"},
    {U'V', 88, -5, -5, "M 0 100 L 44 0 L 88 100"},
    {U'W', 128, -5, -5, "M 0 100 L 29 0 L 64 100 L 99 0 L 128 100"},
    {U'X', 82, -4, -4, "M 0 100 L 82 0 M 0 0 L 82 100"},
    {U'Y', 86, -5, -5, "M 0 100 L 43 50 L 86 100 M 43 50 L 43 0"},
    {U'Z', 72, -2, -2, "M 4 100 L 72 100 L 0 0 L 72 0"},
    // lower case
    {U'a', 70, -2, 0, "A 35 35 35 0 360 M 70 70 L 70 0"},
    {U'b', 70, 0, -2, "M 0 100 L 0 0 M 0 35 A 35 35 35 180 540"},
    {U'c', 59.7, -2, -2, "A 35 35 35 45 315"},
    {U'd', 70, -2, 0, "A 35 35 35 0 360 M 70 100 L 70 0"},
    {U'e', 70, -2, -2, "M 0 35 L 70 35 A 35 35 35 0 315"},
    {U'f', 52, -2, -5, "M 14 0 L 14 76 A 36 76 22 180 45 M 0 70 L 38 70"},
    {U'g', 70, -2, 0, "A 35 35 35 0 360 M 70 70 L 70 5 A 35 5 35 0 -150"},
    {U'h', 70, 0, 0, "M 0 100 L 0 0 M 0 35 A 35 35 35 180 0 L 70 0"},
    {U'i', 0, 0, 0, "M 0 0 L 0 70 D 0 92"},
    {U'j', 20, -4, 0, "M 20 70 L 20 -10 A 2 -10 18 0 -135 D 20 92"},
    {U'k', 58, 0, -4, "M 0 100 L 0 0 M 56 70 L 0 24 M 21 41 L 58 0"},
    {U'l', 0, 0, 0, "M 0 100 L 0 0"},
    {U'm', 104, 0, 0, "M 0 0 L 0 70 M 0 44 A 26 44 26 180 0 L 52 0 M 52 44 A 78 44 26 180 0 L 104 0"},
    {U'n', 70, 0, 0, "M 0 0 L 0 70 M 0 35 A 35 35 35 180 0 L 70 0"},
    {U'o', 70, -2, -2, "A 35 35 35 90 450"},
    {U'p', 70, 0, -2, "M 0 70 L 0 -30 M 0 35 A 35 35 35 180 540"},
    {U'q', 70, -2, 0, "A 35 35 35 0 360 M 70 70 L 70 -30"},
    {U'r', 38, 0, -4, "M 0 0 L 0 70 M 0 42 A 28 42 28 180 70"},
    {U's', 36, -2, -2, "A 18 53 17 40 270 A 18 18 18 90 -145"},
    {U't', 40, -2, -3, "M 14 96 L 14 16 A 30 16 16 180 290 M 0 70 L 34 70"},
    {U'u', 70, 0, 0, "M 0 70 L 0 35 A 35 35 35 180 360 M 70 70 L 70 0"},
    {U'v', 66, -4, -4, "M 0 70 L 33 0 L 66 70"},
    {U'w', 98, -4, -4, "M 0 70 L 24.5 0 L 49 70 L 73.5 0 L 98 70"},
    {U'x', 64, -3, -3, "M 0 70 L 64 0 M 0 0 L 64 70"},
    {U'y', 68, -4, -4, "M 0 70 L 34 0 M 68 70 L 19 -30"},
    {U'z', 62, -2, -2, "M 2 70 L 62 70 L 0 0 L 62 0"},
    // figures
    {U'0', 72, -2, -2, "E 36 50 36 50 90 450"},
    {U'1', 30, 2, 0, "M 0 84 L 30 100 L 30 0"},
    {U'2', 70, -2, -2, "A 35 67 33 160 -38 L 0 0 L 70 0"},
    {U'3', 64, -2, -2, "M 6 100 L 62 100 L 30 60 A 32 30 30 94 -150"},
    {U'4', 72, -3, -2, "M 52 0 L 52 100 L 0 28 L 72 28"},
    {U'5', 66, -2, -2, "M 62 100 L 12 100 L 9 52.5 A 33 31 32 138 -150"},
    {U'6', 70, -2, -2, "A 35 35 35 0 360 M 58 100 L 8 54"},
    {U'7', 66, -3, -3, "M 0 100 L 66 100 L 18 0"},
    {U'8', 54, -2, -2, "A 27 77 23 270 630 A 27 27 27 90 450"},
    {U'9', 70, -2, -2, "A 35 65 35 0 360 M 62 46 L 12 0"},
    // punctuation and symbols
    {U'.', 0, 0, 0, "D 0 0"},
    {U',', 8, 0, 0, "M 8 4 L 0 -16"},
    {U':', 0, 0, 0, "D 0 0 D 0 56"},
    {U';', 8, 0, 0, "M 8 4 L 0 -16 D 6 56"},
    {U'!', 0, 0, 0, "M 0 100 L 0 28 D 0 0"},
    {U'?', 56, -2, -2, "A 28 72 28 160 -60 L 28 30 D 28 0"},
    {U'\'', 0, 0, 0, "M 0 100 L 0 72"},
    {U'"', 18, 0, 0, "M 0 100 L 0 72 M 18 100 L 18 72"},
    {U'`', 12, 0, 0, "M 0 104 L 12 88"},
    {U'-', 36, 0, 0, "M 0 38 L 36 38"},
    {U'_', 70, -4, -4, "M 0 -14 L 70 -14"},
    {U'(', 24, 0, -2, "A 62 50 62 128 232"},
    {U')', 24, -2, 0, "A -38 50 62 52 -52"},
    {U'[', 22, 0, -2, "M 22 108 L 0 108 L 0 -8 L 22 -8"},
    {U']', 22, -2, 0, "M 0 108 L 22 108 L 22 -8 L 0 -8"},
    {U'{', 26, 0, -2, "M 26 108 L 14 104 L 12 60 L 0 50 L 12 40 L 14 -4 L 26 -8"},
    {U'}', 26, -2, 0, "M 0 108 L 12 104 L 14 60 L 26 50 L 14 40 L 12 -4 L 0 -8"},
    {U'/', 50, -4, -4, "M 0 -8 L 50 108"},
    {U'\\', 50, -4, -4, "M 0 108 L 50 -8"},
    {U'|', 0, 0, 0, "M 0 -20 L 0 112"},
    {U'+', 60, 0, 0, "M 0 50 L 60 50 M 30 20 L 30 80"},
    {U'=', 56, 0, 0, "M 0 36 L 56 36 M 0 64 L 56 64"},
    {U'<', 56, 0, 0, "M 56 80 L 0 50 L 56 20"},
    {U'>', 56, 0, 0, "M 0 80 L 56 50 L 0 20"},
    {U'*', 50, 0, 0, "M 25 100 L 25 60 M 6 90 L 44 70 M 6 70 L 44 90"},
    {U'#', 70, -2, -2, "M 20 0 L 30 100 M 50 0 L 60 100 M 4 34 L 70 34 M 0 66 L 66 66"},
    {U'%', 80, -2, -2, "A 16 84 14 90 450 A 64 16 14 90 450 M 76 100 L 4 0"},
    {U'&', 80, -2, -2, "M 80 0 L 24 64 A 38 80 20 225 -40 L 12 34 A 34 26 26 164 360 L 64 50"},
    {U'$', 58, -2, -2, "A 29 75.5 24.5 35 270 A 29 25.5 25.5 90 -145 M 29 114 L 29 -14"},
    {U'@', 100, -2, -2, "A 64 50 16 0 360 M 80 66 L 80 40 A 90 40 10 180 360 A 50 50 50 0 300"},
    {U'^', 52, 0, 0, "M 0 70 L 26 100 L 52 70"},
    {U'~', 72, 0, 0, "M 0 44 C 14 64 26 60 36 50 C 46 40 58 36 72 56"},
    {0x2013, 56, 0, 0, "M 0 38 L 56 38"},                   // en dash
    {0x2014, 96, 0, 0, "M 0 38 L 96 38"},                   // em dash
    {0x2018, 8, 0, 0, "M 8 100 L 0 80"},                    // left single quote
    {0x2019, 8, 0, 0, "M 8 100 L 0 80"},                    // right single quote / apostrophe
    {0x201C, 26, 0, 0, "M 8 100 L 0 80 M 26 100 L 18 80"},  // left double quote
    {0x201D, 26, 0, 0, "M 8 100 L 0 80 M 26 100 L 18 80"},  // right double quote
    {0x201E, 26, 0, 0, "M 8 4 L 0 -16 M 26 4 L 18 -16"},    // low double quote
    {0x2026, 64, 0, 0, "D 0 0 D 32 0 D 64 0"},             // ellipsis
    {0x00B0, 24, 0, 0, "A 12 88 12 90 450"},                // degree
    {0x00D7, 48, 0, 0, "M 0 26 L 48 74 M 0 74 L 48 26"},    // multiplication sign
    {0x00B7, 0, 0, 0, "D 0 50"},                            // middle dot
    {0x00DF, 58, 0, -2, "M 0 0 L 0 76 A 25 76 25 180 -38 L 30 54 A 30 26 28 80 -150"},  // sharp s
    {0xFFFD, 56, -2, -2, "A 28 72 28 160 -60 L 28 30 D 28 0"},
};
// clang-format on

// Accented letters: base + mark (drawn centred over the base, above the cap or x-height).
enum class Mark { Diaeresis, Acute, Grave, Circumflex, Tilde, Ring, Cedilla };
struct Composite {
    char32_t cp, base;
    Mark mark;
};
constexpr Composite kComposites[] = {
    {0xC4, U'A', Mark::Diaeresis}, {0xD6, U'O', Mark::Diaeresis}, {0xDC, U'U', Mark::Diaeresis},
    {0xE4, U'a', Mark::Diaeresis}, {0xF6, U'o', Mark::Diaeresis}, {0xFC, U'u', Mark::Diaeresis},
    {0xCB, U'E', Mark::Diaeresis}, {0xEB, U'e', Mark::Diaeresis}, {0xCF, U'I', Mark::Diaeresis}, {0xEF, U'i', Mark::Diaeresis},
    {0xC1, U'A', Mark::Acute}, {0xC9, U'E', Mark::Acute}, {0xCD, U'I', Mark::Acute}, {0xD3, U'O', Mark::Acute}, {0xDA, U'U', Mark::Acute},
    {0xE1, U'a', Mark::Acute}, {0xE9, U'e', Mark::Acute}, {0xED, U'i', Mark::Acute}, {0xF3, U'o', Mark::Acute}, {0xFA, U'u', Mark::Acute},
    {0xC0, U'A', Mark::Grave}, {0xC8, U'E', Mark::Grave}, {0xCC, U'I', Mark::Grave}, {0xD2, U'O', Mark::Grave}, {0xD9, U'U', Mark::Grave},
    {0xE0, U'a', Mark::Grave}, {0xE8, U'e', Mark::Grave}, {0xEC, U'i', Mark::Grave}, {0xF2, U'o', Mark::Grave}, {0xF9, U'u', Mark::Grave},
    {0xC2, U'A', Mark::Circumflex}, {0xCA, U'E', Mark::Circumflex}, {0xCE, U'I', Mark::Circumflex}, {0xD4, U'O', Mark::Circumflex},
    {0xDB, U'U', Mark::Circumflex}, {0xE2, U'a', Mark::Circumflex}, {0xEA, U'e', Mark::Circumflex}, {0xEE, U'i', Mark::Circumflex},
    {0xF4, U'o', Mark::Circumflex}, {0xFB, U'u', Mark::Circumflex},
    {0xD1, U'N', Mark::Tilde}, {0xF1, U'n', Mark::Tilde}, {0xC3, U'A', Mark::Tilde}, {0xE3, U'a', Mark::Tilde},
    {0xD5, U'O', Mark::Tilde}, {0xF5, U'o', Mark::Tilde},
    {0xC5, U'A', Mark::Ring}, {0xE5, U'a', Mark::Ring},
    {0xC7, U'C', Mark::Cedilla}, {0xE7, U'c', Mark::Cedilla},
};

// Kerning (design units, added to the advance between the pair).
struct KernPair {
    char32_t a, b;
    double k;
};
constexpr KernPair kKern[] = {
    {U'A', U'V', -9}, {U'A', U'W', -7}, {U'A', U'Y', -9}, {U'A', U'T', -7}, {U'A', U'v', -5}, {U'A', U'w', -4}, {U'A', U'y', -5},
    {U'V', U'A', -9}, {U'W', U'A', -7}, {U'Y', U'A', -9}, {U'T', U'A', -7}, {U'L', U'T', -10}, {U'L', U'V', -9}, {U'L', U'W', -7},
    {U'L', U'Y', -10}, {U'T', U'o', -10}, {U'T', U'a', -9}, {U'T', U'e', -9}, {U'T', U'r', -6}, {U'T', U'u', -6}, {U'T', U'y', -6},
    {U'T', U'.', -8}, {U'T', U',', -8}, {U'V', U'o', -7}, {U'V', U'a', -7}, {U'V', U'e', -7}, {U'W', U'o', -5}, {U'W', U'a', -5},
    {U'W', U'e', -5}, {U'Y', U'o', -9}, {U'Y', U'a', -9}, {U'Y', U'e', -9}, {U'P', U'A', -6}, {U'P', U'.', -9}, {U'F', U'A', -5},
    {U'F', U'.', -8}, {U'r', U'.', -7}, {U'r', U',', -7}, {U'v', U'.', -5}, {U'y', U'.', -5}, {U'L', U'\'', -8}, {U'L', 0x2019, -8},
};

// ------------------------------------------------------------------ parsed skeletons

struct DStroke {
    std::vector<Vec2> pts;       // design units, y up
    std::vector<char> curved;    // per segment
    bool dot{false};
    bool closed{false};
};

struct DGlyph {
    double adv{0}, lsb{0}, rsb{0};
    std::vector<DStroke> strokes;
    double ymin{0}, ymax{0};
};

void addArc(DStroke& s, double cx, double cy, double rx, double ry, double a0, double a1) {
    const double sweep = a1 - a0;
    const int steps = std::max(2, static_cast<int>(std::ceil(std::fabs(sweep) / 5.0)));
    for (int i = 0; i <= steps; ++i) {
        const double a = (a0 + sweep * i / steps) * kPi / 180.0;
        const Vec2 p{cx + rx * std::cos(a), cy + ry * std::sin(a)};
        if (i == 0) {
            if (s.pts.empty()) {
                s.pts.push_back(p);
            } else if (std::hypot(s.pts.back().x - p.x, s.pts.back().y - p.y) > 0.05) {
                s.pts.push_back(p);
                s.curved.push_back(0);
            }
            continue;
        }
        s.pts.push_back(p);
        s.curved.push_back(1);
    }
}

DGlyph parseGlyph(const GlyphDef& g) {
    DGlyph out;
    out.adv = g.adv;
    out.lsb = g.lsb;
    out.rsb = g.rsb;
    std::istringstream in(g.path);
    std::string cmd;
    DStroke cur;
    auto flush = [&]() {
        if (!cur.pts.empty()) {
            const Vec2 a = cur.pts.front(), b = cur.pts.back();
            cur.closed = !cur.dot && cur.pts.size() > 2 && std::hypot(a.x - b.x, a.y - b.y) < 0.05;
            out.strokes.push_back(cur);
        }
        cur = DStroke{};
    };
    auto num = [&]() {
        double v = 0.0;
        in >> v;
        return v;
    };
    while (in >> cmd) {
        if (cmd == "M") {
            flush();
            const double x = num(), y = num();
            cur.pts.push_back({x, y});
        } else if (cmd == "L") {
            const double x = num(), y = num();
            cur.pts.push_back({x, y});
            cur.curved.push_back(0);
        } else if (cmd == "A") {
            const double cx = num(), cy = num(), r = num(), a0 = num(), a1 = num();
            addArc(cur, cx, cy, r, r, a0, a1);
        } else if (cmd == "E") {
            const double cx = num(), cy = num(), rx = num(), ry = num(), a0 = num(), a1 = num();
            addArc(cur, cx, cy, rx, ry, a0, a1);
        } else if (cmd == "C") {
            const double x1 = num(), y1 = num(), x2 = num(), y2 = num(), x = num(), y = num();
            const Vec2 p0 = cur.pts.empty() ? Vec2{x1, y1} : cur.pts.back();
            if (cur.pts.empty()) cur.pts.push_back(p0);
            for (int i = 1; i <= 24; ++i) {
                const double t = i / 24.0, u = 1.0 - t;
                cur.pts.push_back({u * u * u * p0.x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x,
                                   u * u * u * p0.y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y});
                cur.curved.push_back(1);
            }
        } else if (cmd == "D") {
            flush();
            const double x = num(), y = num();
            cur.pts.push_back({x, y});
            cur.dot = true;
            flush();
        }
    }
    flush();
    out.ymin = 1e9;
    out.ymax = -1e9;
    for (const auto& s : out.strokes)
        for (const auto& p : s.pts) {
            out.ymin = std::min(out.ymin, p.y);
            out.ymax = std::max(out.ymax, p.y);
        }
    if (out.strokes.empty()) out.ymin = out.ymax = 0.0;
    return out;
}

void addMark(DGlyph& g, Mark mark, bool capital) {
    const double cx = g.adv / 2.0;
    const double base = capital ? 118.0 : 90.0;
    DGlyph m;
    GlyphDef def{0, 0, 0, 0, ""};
    std::string path;
    char buf[160];
    switch (mark) {
        case Mark::Diaeresis:
            std::snprintf(buf, sizeof buf, "D %.2f %.2f D %.2f %.2f", cx - 17, base, cx + 17, base);
            break;
        case Mark::Acute:
            std::snprintf(buf, sizeof buf, "M %.2f %.2f L %.2f %.2f", cx - 7, base - 8, cx + 9, base + 10);
            break;
        case Mark::Grave:
            std::snprintf(buf, sizeof buf, "M %.2f %.2f L %.2f %.2f", cx + 7, base - 8, cx - 9, base + 10);
            break;
        case Mark::Circumflex:
            std::snprintf(buf, sizeof buf, "M %.2f %.2f L %.2f %.2f L %.2f %.2f", cx - 16, base - 8, cx, base + 8, cx + 16, base - 8);
            break;
        case Mark::Tilde:
            std::snprintf(buf, sizeof buf, "M %.2f %.2f C %.2f %.2f %.2f %.2f %.2f %.2f C %.2f %.2f %.2f %.2f %.2f %.2f", cx - 20, base - 4,
                          cx - 14, base + 8, cx - 6, base + 6, cx, base, cx + 6, base - 6, cx + 14, base - 8, cx + 20, base + 4);
            break;
        case Mark::Ring:
            std::snprintf(buf, sizeof buf, "A %.2f %.2f 10 90 450", cx, base + 2);
            break;
        case Mark::Cedilla:
            std::snprintf(buf, sizeof buf, "M %.2f 0 L %.2f -10 L %.2f -16 L %.2f -28", cx + 2, cx + 2, cx + 10, cx - 2);
            break;
    }
    path = buf;
    def.path = path.c_str();
    m = parseGlyph(def);
    for (auto& s : m.strokes) g.strokes.push_back(s);
    g.ymin = std::min(g.ymin, m.ymin);
    g.ymax = std::max(g.ymax, m.ymax);
}

const std::map<char32_t, DGlyph>& glyphs() {
    static const std::map<char32_t, DGlyph> table = [] {
        std::map<char32_t, DGlyph> t;
        for (const auto& g : kGlyphs) t[g.cp] = parseGlyph(g);
        for (const auto& c : kComposites) {
            DGlyph g = t.at(c.base);
            const bool capital = c.base >= U'A' && c.base <= U'Z';
            if (!capital && (c.base == U'i') && c.mark != Mark::Cedilla) {
                // dotless: drop the i's dot before adding the mark
                g.strokes.erase(std::remove_if(g.strokes.begin(), g.strokes.end(), [](const DStroke& s) { return s.dot; }), g.strokes.end());
            }
            addMark(g, c.mark, capital);
            t[c.cp] = g;
        }
        return t;
    }();
    return table;
}

const DGlyph& glyphFor(char32_t cp) {
    const auto& t = glyphs();
    const auto it = t.find(cp);
    return it != t.end() ? it->second : t.at(0xFFFD);
}

double kern(char32_t a, char32_t b) {
    for (const auto& k : kKern)
        if (k.a == a && k.b == b) return k.k;
    return 0.0;
}

// ------------------------------------------------------------------ metrics shared by layout and measure

struct Pens {
    double thick, thin, horiz, scale;  // design units; scale = skeleton scale
};

Pens pens(const FontStyle& st) {
    Pens p;
    p.thick = std::clamp(st.weight, 0.01, 0.45) * kCap;
    p.thin = p.thick * (1.0 - 0.8 * std::clamp(st.contrast, 0.0, 1.0));
    p.horiz = st.contrast > 0.0 ? p.thin : p.thick;
    p.scale = (kCap - p.horiz) / kCap;
    return p;
}

constexpr double kSpacing = 15.0;  // side spacing between glyph outlines (design units)

double glyphAdvance(const DGlyph& g, const FontStyle& st, const Pens& p) {
    return g.adv * p.scale * st.widthScale + p.thick + kSpacing + g.lsb + g.rsb + st.tracking * kCap;
}

// Pen width of a segment (design units): contrast makes horizontal strokes thin; straight "/"
// diagonals are thin too (Didone convention: A has a thin left leg, V a thin right one).
double segWidth(Vec2 a, Vec2 b, bool curved, const Pens& p, const FontStyle& st) {
    if (st.contrast <= 0.0) return p.thick;
    const double dx = b.x - a.x, dy = b.y - a.y, len = std::hypot(dx, dy);
    if (len < 1e-9) return p.thick;
    const double s = std::pow(std::fabs(dy) / len, 1.4);
    double k = s;
    if (!curved && dx * dy > 0 && std::fabs(dx) > 0.12 * len) k *= 0.30;
    return p.thin + (p.thick - p.thin) * k;
}

}  // namespace

// ------------------------------------------------------------------ public API

std::u32string decodeUtf8(const std::string& s) {
    std::u32string out;
    for (std::size_t i = 0; i < s.size();) {
        const auto c = static_cast<unsigned char>(s[i]);
        int n = 0;
        char32_t cp = 0;
        if (c < 0x80) { cp = c; n = 1; }
        else if ((c & 0xE0) == 0xC0) { cp = c & 0x1F; n = 2; }
        else if ((c & 0xF0) == 0xE0) { cp = c & 0x0F; n = 3; }
        else if ((c & 0xF8) == 0xF0) { cp = c & 0x07; n = 4; }
        else { out.push_back(0xFFFD); ++i; continue; }
        if (i + static_cast<std::size_t>(n) > s.size()) { out.push_back(0xFFFD); break; }
        bool ok = true;
        for (int k = 1; k < n; ++k) {
            const auto cc = static_cast<unsigned char>(s[i + static_cast<std::size_t>(k)]);
            if ((cc & 0xC0) != 0x80) { ok = false; break; }
            cp = (cp << 6) | (cc & 0x3F);
        }
        if (!ok) { out.push_back(0xFFFD); ++i; continue; }
        out.push_back(cp);
        i += static_cast<std::size_t>(n);
    }
    return out;
}

std::vector<char32_t> fontCodePoints() {
    std::vector<char32_t> v;
    for (const auto& [cp, g] : glyphs())
        if (cp != 0xFFFD) v.push_back(cp);
    return v;
}

double measureText(const std::string& utf8, const FontStyle& st, double capHeightPx) {
    const Pens p = pens(st);
    const std::u32string text = decodeUtf8(utf8);
    double adv = 0.0;
    for (std::size_t i = 0; i < text.size(); ++i) {
        adv += glyphAdvance(glyphFor(text[i]), st, p);
        if (i + 1 < text.size()) adv += kern(text[i], text[i + 1]) * p.scale;
    }
    if (!text.empty()) adv -= kSpacing + st.tracking * kCap;  // no spacing after the last glyph
    return std::max(0.0, adv) * capHeightPx / kCap;
}

double capHeightForWidth(const std::string& utf8, const FontStyle& st, double widthPx) {
    const double w100 = measureText(utf8, st, 100.0);
    return w100 > 0.0 ? widthPx * 100.0 / w100 : 0.0;
}

TextLayout layoutText(const std::string& utf8, const FontStyle& st, double capHeightPx, Vec2 origin) {
    TextLayout lay;
    lay.capHeight = capHeightPx;
    lay.origin = origin;
    const Pens p = pens(st);
    const double u = capHeightPx / kCap;  // px per design unit
    lay.penHalfWidth = p.thick * u * 0.5;
    const std::u32string text = decodeUtf8(utf8);
    double pen = 0.0;  // design units
    lay.x0 = lay.y0 = 1e300;
    lay.x1 = lay.y1 = -1e300;
    // Guides a serif may sit on (design units).
    const double guides[] = {0.0, kXh, kCap, kDesc};
    for (std::size_t gi = 0; gi < text.size(); ++gi) {
        const DGlyph& g = glyphFor(text[gi]);
        const double left = pen + g.lsb;
        auto xf = [&](Vec2 d) {  // design -> px
            const double y = d.y * p.scale + p.horiz / 2.0;
            const double x = left + d.x * p.scale * st.widthScale + p.thick / 2.0 + y * st.slant;
            return Vec2{origin.x + x * u, origin.y - y * u};
        };
        TextLayout::GlyphShape shape;
        double ymaxDesign = g.ymax;
        auto addSeg = [&](Vec2 a, Vec2 b, double wDesign, bool sqA, bool sqB) {
            shape.segs.push_back({xf(a), xf(b), static_cast<float>(wDesign * u * 0.5), sqA, sqB});
        };
        for (const auto& s : g.strokes) {
            if (s.dot || s.pts.size() == 1) {
                const double w = p.thick * (st.contrast > 0 ? 0.9 : 1.0);
                Vec2 d = s.pts[0];
                // Dots above the x-height (i, j, umlauts) move up with the weight so they never touch the stem.
                if (d.y > kXh + 5.0) d.y += std::max(0.0, (p.thick - 12.0) * 0.75) / p.scale;
                ymaxDesign = std::max(ymaxDesign, d.y);
                addSeg(d, d, w, st.squareCaps, st.squareCaps);
                continue;
            }
            const std::size_t n = s.pts.size();
            for (std::size_t k = 0; k + 1 < n; ++k) {
                const bool first = k == 0, last = k + 2 == n;
                const bool sqA = st.squareCaps && first && !s.closed;
                const bool sqB = st.squareCaps && last && !s.closed;
                const bool curved = k < s.curved.size() && s.curved[k];
                addSeg(s.pts[k], s.pts[k + 1], segWidth(s.pts[k], s.pts[k + 1], curved, p, st), sqA || (st.serifs && first && !s.closed),
                       sqB || (st.serifs && last && !s.closed));
            }
            if (st.serifs && !s.closed) {
                // Hairline serifs on steep straight terminals that sit on a guide line.
                for (int end = 0; end < 2; ++end) {
                    const std::size_t i0 = end == 0 ? 0 : n - 1, i1 = end == 0 ? 1 : n - 2;
                    const bool curved = end == 0 ? (!s.curved.empty() && s.curved.front()) : (!s.curved.empty() && s.curved.back());
                    if (curved) continue;
                    const Vec2 t = s.pts[i0], o = s.pts[i1];
                    const double dx = o.x - t.x, dy = o.y - t.y;
                    if (std::fabs(dy) < 1e-9 || std::fabs(dx) / std::fabs(dy) > 0.9) continue;  // steeper than ~42 degrees
                    bool onGuide = false;
                    for (double gl : guides) onGuide = onGuide || std::fabs(t.y - gl) < 1.5;
                    if (!onGuide) continue;
                    const double half = std::max(0.55 * p.thick + 7.0, 11.0) / (p.scale * st.widthScale);
                    const double w = std::max(p.thin, 0.02 * kCap);
                    addSeg({t.x - half, t.y}, {t.x + half, t.y}, w, true, true);
                }
            }
        }
        // Clip range for square caps: the glyph's own vertical extent (flat cuts at baseline / cap height).
        if (st.squareCaps || st.serifs) {
            const double top = ymaxDesign * p.scale + p.horiz, bottom = g.ymin * p.scale;
            shape.clipTop = origin.y - top * u;
            shape.clipBottom = origin.y - bottom * u;
        } else {
            shape.clipTop = -std::numeric_limits<double>::infinity();
            shape.clipBottom = std::numeric_limits<double>::infinity();
        }
        shape.x0 = shape.y0 = 1e300;
        shape.x1 = shape.y1 = -1e300;
        for (const auto& sg : shape.segs) {
            for (const Vec2& q : {sg.a, sg.b}) {
                shape.x0 = std::min(shape.x0, q.x - sg.halfWidth * 1.5);
                shape.x1 = std::max(shape.x1, q.x + sg.halfWidth * 1.5);
                shape.y0 = std::min(shape.y0, q.y - sg.halfWidth * 1.5);
                shape.y1 = std::max(shape.y1, q.y + sg.halfWidth * 1.5);
            }
        }
        if (!shape.segs.empty()) {
            lay.x0 = std::min(lay.x0, shape.x0);
            lay.x1 = std::max(lay.x1, shape.x1);
            lay.y0 = std::min(lay.y0, shape.y0);
            lay.y1 = std::max(lay.y1, shape.y1);
            lay.glyphs.push_back(std::move(shape));
        }
        pen += glyphAdvance(g, st, p);
        if (gi + 1 < text.size()) pen += kern(text[gi], text[gi + 1]) * p.scale;
    }
    if (!text.empty()) pen -= kSpacing + st.tracking * kCap;
    lay.advance = std::max(0.0, pen) * u;
    if (lay.glyphs.empty()) lay.x0 = lay.x1 = origin.x, lay.y0 = lay.y1 = origin.y;
    return lay;
}

DistanceField textDistance(const TextLayout& lay, int width, int height, double reach) {
    DistanceField f;
    f.width = width;
    f.height = height;
    f.reach = static_cast<float>(reach);
    f.d.assign(static_cast<std::size_t>(width) * static_cast<std::size_t>(height), f.reach);
    std::vector<float> local;
    for (const auto& g : lay.glyphs) {
        const int gx0 = std::max(0, static_cast<int>(std::floor(g.x0 - reach - 2))), gx1 = std::min(width - 1, static_cast<int>(std::ceil(g.x1 + reach + 2)));
        const int gy0 = std::max(0, static_cast<int>(std::floor(g.y0 - reach - 2))), gy1 = std::min(height - 1, static_cast<int>(std::ceil(g.y1 + reach + 2)));
        if (gx1 < gx0 || gy1 < gy0) continue;
        const int lw = gx1 - gx0 + 1, lh = gy1 - gy0 + 1;
        local.assign(static_cast<std::size_t>(lw) * static_cast<std::size_t>(lh), f.reach);
        for (const auto& s : g.segs) {
            const double hw = s.halfWidth, r = hw * 1.5 + reach + 1.0;
            const int x0 = std::max(gx0, static_cast<int>(std::floor(std::min(s.a.x, s.b.x) - r)));
            const int x1 = std::min(gx1, static_cast<int>(std::ceil(std::max(s.a.x, s.b.x) + r)));
            const int y0 = std::max(gy0, static_cast<int>(std::floor(std::min(s.a.y, s.b.y) - r)));
            const int y1 = std::min(gy1, static_cast<int>(std::ceil(std::max(s.a.y, s.b.y) + r)));
            const double dx = s.b.x - s.a.x, dy = s.b.y - s.a.y, len = std::hypot(dx, dy);
            const double ux = len > 1e-9 ? dx / len : 1.0, uy = len > 1e-9 ? dy / len : 0.0;
            for (int y = y0; y <= y1; ++y) {
                for (int x = x0; x <= x1; ++x) {
                    const double px = x + 0.5 - s.a.x, py = y + 0.5 - s.a.y;
                    const double along = px * ux + py * uy, across = std::fabs(-px * uy + py * ux);
                    double d;
                    if (along < 0.0) d = s.squareA ? std::max(-along - hw, across - hw) : std::hypot(along, across) - hw;
                    else if (along > len) d = s.squareB ? std::max(along - len - hw, across - hw) : std::hypot(along - len, across) - hw;
                    else d = across - hw;
                    float& cell = local[static_cast<std::size_t>(y - gy0) * static_cast<std::size_t>(lw) + static_cast<std::size_t>(x - gx0)];
                    cell = std::min(cell, static_cast<float>(d));
                }
            }
        }
        for (int y = gy0; y <= gy1; ++y) {
            const double cy = y + 0.5;
            const double clip = std::max(g.clipTop - cy, cy - g.clipBottom);
            for (int x = gx0; x <= gx1; ++x) {
                float v = local[static_cast<std::size_t>(y - gy0) * static_cast<std::size_t>(lw) + static_cast<std::size_t>(x - gx0)];
                if (std::isfinite(clip)) v = std::max(v, static_cast<float>(clip));
                float& cell = f.d[static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + static_cast<std::size_t>(x)];
                cell = std::min(cell, std::min(v, f.reach));
            }
        }
    }
    return f;
}

Mask textMask(const DistanceField& field, double grow) {
    Mask m(field.width, field.height);
    for (int y = 0; y < field.height; ++y)
        for (int x = 0; x < field.width; ++x) {
            const double v = std::clamp(0.5 - (field.at(x, y) - grow), 0.0, 1.0);
            m.at(x, y) = static_cast<float>(v);
        }
    return m;
}

}  // namespace as::art
