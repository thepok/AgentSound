// Cover art (agentsound cover): every style renders deterministically, seeds and palettes change
// the picture, the title is really drawn, strict errors; the stroke font covers its characters and
// lays out consistently; the raster primitives are anti-aliased and exact.

#include "analysis/Png.h"
#include "art/Cover.h"
#include "art/Raster.h"
#include "art/StrokeFont.h"
#include "core/Params.h"

#include <cmath>
#include <iostream>
#include <string>
#include <vector>

using namespace as::art;

namespace {

int failures = 0;

void check(bool ok, const std::string& what) {
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << "\n";
    if (!ok) ++failures;
}

double diff(const as::analysis::Image& a, const as::analysis::Image& b) {
    if (a.rgb.size() != b.rgb.size()) return 1e9;
    double d = 0.0;
    for (std::size_t i = 0; i < a.rgb.size(); ++i) d += std::abs(static_cast<int>(a.rgb[i]) - static_cast<int>(b.rgb[i]));
    return d / static_cast<double>(a.rgb.size());
}

double stddev(const as::analysis::Image& a) {
    double s = 0.0, s2 = 0.0;
    for (auto v : a.rgb) { s += v; s2 += static_cast<double>(v) * v; }
    const double n = static_cast<double>(a.rgb.size());
    return std::sqrt(std::max(0.0, s2 / n - (s / n) * (s / n)));
}

bool throwsConfig(const CoverSpec& s) {
    try {
        renderCover(s);
    } catch (const as::ConfigError&) {
        return true;
    } catch (...) {
        return false;
    }
    return false;
}

}  // namespace

int main() {
    std::cout << "styles\n";
    check(coverStyles().size() == 8, "8 styles");
    for (const auto& style : coverStyles()) {
        CoverSpec s;
        s.style = style;
        s.title = "Night Drive \xC3\x9C";
        s.subtitle = "AgentSound";
        s.size = 320;
        s.seed = 5;
        const auto a = renderCover(s);
        const auto b = renderCover(s);
        check(a.width == 320 && a.height == 320 && a.rgb == b.rgb, style + ": 320 px, deterministic");
        check(stddev(a) > 12.0, style + ": not flat (stddev " + std::to_string(stddev(a)) + ")");
        CoverSpec other = s;
        other.seed = 6;
        check(diff(a, renderCover(other)) > 0.2, style + ": the seed changes it");
        CoverSpec notitle = s;
        notitle.title = "";
        check(diff(a, renderCover(notitle)) > 0.5, style + ": the title is drawn");
        const auto pals = coverPalettes(style);
        check(pals.size() >= 2, style + ": palettes");
        if (pals.size() >= 2) {
            CoverSpec p = s;
            p.palette = pals[1];
            check(diff(a, renderCover(p)) > 1.0, style + ": palette '" + pals[1] + "' changes it");
        }
        CoverSpec custom = s;
        custom.palette = "#00ff00,#0000ff";
        check(diff(a, renderCover(custom)) > 0.5, style + ": custom colours change it");
    }
    std::cout << "errors\n";
    CoverSpec bad;
    bad.title = "x";
    bad.size = 300;
    bad.style = "baroque";
    check(throwsConfig(bad), "unknown style");
    bad.style = "jazz";
    bad.palette = "nonexistent";
    check(throwsConfig(bad), "unknown palette");
    bad.palette = "#12345";
    check(throwsConfig(bad), "malformed colour");
    bad.palette = "#111111,#222222,#333333,#444444";
    check(throwsConfig(bad), "too many colours");
    bad.palette = "";
    bad.size = 100;
    check(throwsConfig(bad), "size below 256");
    bad.size = 4001;
    check(throwsConfig(bad), "size above 4000");

    std::cout << "font\n";
    const auto cps = fontCodePoints();
    check(cps.size() > 140, "glyph count " + std::to_string(cps.size()));
    FontStyle st;
    bool allDrawn = true;
    for (char32_t cp = 33; cp < 127; ++cp) {
        std::string s(1, static_cast<char>(cp));
        const TextLayout lay = layoutText(s, st, 40.0, {10.0, 60.0});
        if (lay.glyphs.empty()) { allDrawn = false; std::cout << "    no glyph for '" << s << "'\n"; }
    }
    check(allDrawn, "every printable ASCII character has strokes");
    const double w1 = measureText("HELLO", st, 50.0), w2 = measureText("HELLO", st, 100.0);
    check(std::fabs(w2 - 2.0 * w1) < 1e-6, "advance scales with the cap height");
    const TextLayout lay = layoutText("HELLO", st, 50.0, {0.0, 100.0});
    check(std::fabs(lay.advance - w1) < 1e-6, "layout advance = measure");
    check(lay.y0 < 50.0 + 1.0 && lay.y0 > 40.0 && lay.y1 < 104.0, "caps sit between baseline and cap height");
    FontStyle tr = st;
    tr.tracking = 0.2;
    check(measureText("HELLO", tr, 50.0) > w1 + 30.0, "tracking widens");
    check(std::fabs(capHeightForWidth("HELLO", st, 300.0) * w1 / 50.0 - 300.0) < 1e-6, "cap height for a width");
    check(decodeUtf8("\xC3\xA4\xE2\x82\xAC") == std::u32string({0xE4, 0x20AC}), "UTF-8 decoding");
    check(decodeUtf8("\xFF")[0] == 0xFFFD, "invalid UTF-8 -> U+FFFD");
    // A glyph's distance field: inside a stem negative, far away positive.
    const TextLayout il = layoutText("I", st, 100.0, {20.0, 120.0});
    const DistanceField f = textDistance(il, 80, 140, 6.0);
    const double stemX = 0.5 * (il.glyphs[0].segs[0].a.x + il.glyphs[0].segs[0].b.x);
    check(f.at(static_cast<int>(stemX), 70) < -3.0 && f.at(70, 70) > 5.0, "distance field inside / outside");

    std::cout << "raster\n";
    Mask m(100, 100);
    fillPolygon(m, std::vector<Vec2>{{10, 10}, {60, 10}, {60, 40}, {10, 40}});
    double area = 0.0;
    for (float v : m.data()) area += v;
    check(std::fabs(area - 1500.0) < 1.0, "rectangle area exact (" + std::to_string(area) + ")");
    Mask half(10, 10);
    fillPolygon(half, std::vector<Vec2>{{2.5, 2.0}, {7.0, 2.0}, {7.0, 3.0}, {2.5, 3.0}});
    check(std::fabs(half.at(2, 2) - 0.5f) < 0.02f && std::fabs(half.at(3, 2) - 1.0f) < 0.02f, "partial pixel coverage");
    Mask circle(200, 200);
    fillEllipse(circle, 100, 100, 50, 50);
    area = 0.0;
    for (float v : circle.data()) area += v;
    check(std::fabs(area - 3.14159265 * 2500.0) < 20.0, "circle area");
    Mask bl = m;
    blur(bl, 4.0);
    double area2 = 0.0;
    for (float v : bl.data()) area2 += v;
    check(std::fabs(area2 - 1500.0) < 5.0, "blur keeps the energy");
    std::cout << (failures ? "FAILED: " + std::to_string(failures) : std::string("all passed")) << "\n";
    return failures ? 1 : 0;
}
