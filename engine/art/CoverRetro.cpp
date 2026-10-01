// Retro-futurist covers: synthwave, outrun, dreamwave, darksynth.

#include "art/CoverStyles.h"

#include <algorithm>
#include <cmath>

namespace as::art::styles {

namespace {

constexpr double kPi = 3.14159265358979323846;

// Palette roles of the retro styles:
//   0 sun top / warm accent   1 grid + glow accent   2 horizon colour   3 sky top   4 sky middle
//   5 floor                   6 title glow           7 subtitle neon
Color role(const Ctx& c, int i) { return c.pal[static_cast<std::size_t>(i)]; }

void stars(Raster& r, Ctx& c, double yMax, int count, Color tint) {
    const double k = c.k();
    Mask sparkles(c.S, c.S);
    bool any = false;
    for (int i = 0; i < count; ++i) {
        const double x = c.rng.range(0, c.S), y = c.rng.range(0, yMax);
        const double b = std::pow(c.rng.uniform(), 2.2);
        const double rad = (0.5 + 1.3 * b) * k;
        kit::radialGlow(r, {x, y}, rad, lerp(tint, {1, 1, 1}, 0.6), 0.35 + 0.9 * b, Blend::Add);
        if (b > 0.93) {  // a few sparkles
            const double len = (10 + 18 * b) * k;
            strokeLine(sparkles, {x - len, y}, {x + len, y}, 0.9 * k);
            strokeLine(sparkles, {x, y - len}, {x, y + len}, 0.9 * k);
            any = true;
        }
    }
    if (any) {
        blur(sparkles, 1.2 * k);
        paintSolid(r, sparkles, lerp(tint, {1, 1, 1}, 0.7), 0.8, Blend::Add);
    }
}

// Horizontal stripes cut out of the lower part of a sun disc (the classic retro sun): they start
// `from` (fraction of the radius, - = above the centre) and get thicker towards the bottom.
void cutStripes(Mask& sun, double cy, double rad, double k, int count, double from = -0.18, double step = 0.115) {
    for (int i = 0; i < count; ++i) {
        const double y = cy + rad * (from + step * i);
        const double th = (2.5 + 3.4 * i) * k;
        Mask band(sun.width(), sun.height());
        fillPolygon(band, std::vector<Vec2>{{0, y}, {static_cast<double>(sun.width()), y},
                                             {static_cast<double>(sun.width()), y + th}, {0, y + th}});
        for (std::size_t p = 0; p < sun.data().size(); ++p) sun.data()[p] *= 1.0f - band.data()[p];
    }
}

// Perspective grid on the floor below `horizon`, vanishing point (vpx, horizon).
Mask floorGrid(const Ctx& c, double horizon, double vpx, double spacing, double lineW, double phase, bool vertical = true) {
    const double S = c.S;
    Mask m(c.S, c.S);
    // Horizontal lines: equal steps in depth, projected (y - horizon ~ 1 / z).
    for (int i = 0; i < 80; ++i) {
        const double z = 0.82 + (i + phase) * 0.33;
        const double y = horizon + (S - horizon) * (1.0 / z);
        if (y > S + 20) continue;
        if (y - horizon < 1.2) break;
        const double depth = (y - horizon) / (S - horizon);
        strokeLine(m, {-10, y}, {S + 10, y}, std::max(0.7, lineW * (0.35 + 0.9 * depth)));
    }
    if (vertical) {
        for (int i = -30; i <= 30; ++i) {
            const double xb = vpx + i * spacing;  // where the line crosses the bottom edge
            std::vector<Vec2> pts;
            for (int s = 0; s <= 6; ++s) {
                const double t = s / 6.0;
                pts.push_back({vpx + (xb - vpx) * t, horizon + (S - horizon) * t});
            }
            for (std::size_t s = 0; s + 1 < pts.size(); ++s)
                strokeLine(m, pts[s], pts[s + 1], std::max(0.6, lineW * (0.3 + 0.8 * (s + 0.5) / 6.0)));
        }
    }
    // Fade into the distance.
    for (int y = 0; y < c.S; ++y) {
        const double depth = std::clamp((y - horizon) / (S - horizon), 0.0, 1.0);
        const auto f = static_cast<float>(std::pow(depth, 0.45));
        for (int x = 0; x < c.S; ++x) m.at(x, y) *= f;
    }
    return m;
}

void glowLines(Raster& r, const Mask& m, Color glow, Color core, double k, double strength = 1.0) {
    Mask g1 = m;
    blur(g1, 4.0 * k);
    paintSolid(r, g1, glow, 1.3 * strength, Blend::Add);
    Mask g2 = m;
    blur(g2, 16.0 * k);
    paintSolid(r, g2, glow, 0.55 * strength, Blend::Add);
    paintSolid(r, m, core, 0.95);
}

kit::ChromeLook chromeLook(const Ctx& c, Color glow) {
    kit::ChromeLook look;
    look.face = Gradient{{{0.0, hex(0x0a1740)}, {0.30, hex(0x4e8fe8)}, {0.47, hex(0xeaf7ff)}, {0.50, hex(0xffffff)}, {0.515, hex(0x2e1508)},
                          {0.70, hex(0x9a4516)}, {0.88, hex(0xf0a04b)}, {1.0, hex(0xffe3a8)}}};
    look.outline = hex(0x07020f);
    look.outlineWidth = 4.0 * c.k();
    look.glow = glow;
    look.glowSigma = 14.0 * c.k();
    look.glowStrength = 0.9;
    look.bevel = 5.0 * c.k();
    look.shadowAlpha = 0.5;
    return look;
}

// Big chrome title (1-2 lines) centred at the top; returns the y below it.
double chromeTitle(Raster& r, Ctx& c, const std::string& title, double top, double maxCap, Color glow) {
    if (title.empty()) return top;
    FontStyle st;
    st.weight = 0.2;
    st.slant = 0.2;
    st.squareCaps = true;
    st.tracking = 0.03;
    const kit::TitleFit fit = kit::fitTitle(kit::upper(title), st, c.S * 0.80, maxCap, 2);
    double y = top;
    for (const auto& line : fit.lines) {
        y += fit.cap;
        kit::drawChrome(r, kit::centred(line, st, fit.cap, c.S * 0.5, y), chromeLook(c, glow));
        y += fit.cap * 0.32;
    }
    return y;
}

double neonSubtitle(Raster& r, Ctx& c, const std::string& text, double baseline, double cap, Color glow, double slant = 0.16) {
    if (text.empty()) return baseline;
    FontStyle st;
    st.weight = 0.085;
    st.slant = slant;
    st.tracking = 0.06;
    const kit::TitleFit fit = kit::fitTitle(text, st, c.S * 0.7, cap, 1);
    kit::NeonLook look;
    look.glow = glow;
    look.glowSigma = 5.0 * c.k();
    look.glowStrength = 1.1;
    const auto lay = kit::centred(fit.lines.empty() ? text : fit.lines[0], st, fit.cap, c.S * 0.5, baseline);
    // A soft dark halo first: the thin tube stays readable over the bright sun or palm fronds.
    kit::drawShadow(r, lay, hex(0x06020c), {0.0, 1.5 * c.k()}, 5.0 * c.k(), 0.55, 3.0 * c.k());
    kit::drawNeon(r, lay, look);
    return baseline + fit.cap;
}

}  // namespace

std::vector<kit::Palette> retroPalettes(const std::string& style) {
    if (style == "synthwave")
        return {{"sunset", {hex(0xffd319), hex(0xff2cd6), hex(0xff3d7f), hex(0x0b0725), hex(0x2c0f5e), hex(0x12001f), hex(0xff38d1), hex(0x39e7ff)}},
                {"miami", {hex(0xfff275), hex(0x21e6ff), hex(0xff5fa2), hex(0x06122e), hex(0x173a73), hex(0x02101f), hex(0x21e6ff), hex(0xff5fd2)}},
                {"midnight", {hex(0xff9de2), hex(0x7b5cff), hex(0x8a3cff), hex(0x02030d), hex(0x160d3d), hex(0x06041a), hex(0x8a6bff), hex(0x5ce1ff)}}};
    if (style == "outrun")
        return {{"sunset", {hex(0xffe14d), hex(0xff2e97), hex(0xff6a3d), hex(0x1a0633), hex(0x5e1a66), hex(0x14021f), hex(0xff3fae), hex(0x3ef2ff)}},
                {"turbo", {hex(0xfff06a), hex(0x00e0ff), hex(0xff7b2e), hex(0x071433), hex(0x3a2270), hex(0x05081a), hex(0x00c8ff), hex(0xff4fd8)}},
                {"crimson", {hex(0xffc04d), hex(0xff3355), hex(0xff5a36), hex(0x14030d), hex(0x4a0a2a), hex(0x0e0208), hex(0xff3355), hex(0xffd166)}}};
    if (style == "dreamwave")
        return {{"pastel", {hex(0xfff1d8), hex(0xf8c8ff), hex(0xffa6cf), hex(0x4a4d9c), hex(0x9d86dc), hex(0x6a58b4), hex(0xff86c6), hex(0xffffff)}},
                {"lagoon", {hex(0xfff8e0), hex(0xb8f3ff), hex(0xffb3d1), hex(0x2f5aa8), hex(0x6fa2e0), hex(0x3f6fb5), hex(0x7fe0ff), hex(0xffffff)}},
                {"peach", {hex(0xfff0db), hex(0xffd1e8), hex(0xffb08f), hex(0x5b4a9e), hex(0xc78ad6), hex(0x8a5fb0), hex(0xff9c7a), hex(0xffffff)}}};
    if (style == "darksynth")
        return {{"blood", {hex(0xff1f3d), hex(0xff2238), hex(0x5a0010), hex(0x000000), hex(0x14020a), hex(0x050003), hex(0xff1a36), hex(0xff4d5e)}},
                {"toxic", {hex(0x9dff2e), hex(0x6dff3c), hex(0x0f3a12), hex(0x000000), hex(0x051206), hex(0x010401), hex(0x8aff3c), hex(0xd4ff4d)}},
                {"violet", {hex(0xb04dff), hex(0xa23bff), hex(0x2a0052), hex(0x000000), hex(0x0d0218), hex(0x030006), hex(0xb04dff), hex(0xff4de1)}}};
    return {};
}

// ------------------------------------------------------------------ synthwave

void synthwave(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const double horizon = S * 0.62;
    const Color skyTop = role(c, 3), skyMid = role(c, 4), hor = role(c, 2), grid = role(c, 1), sunTop = role(c, 0);
    kit::verticalGradient(r, Gradient{{{0.0, skyTop}, {0.42, skyMid}, {0.78, lerp(skyMid, hor, 0.55)}, {1.0, hor}}}, 0, horizon);
    stars(r, c, horizon * 0.75, 170, lerp(grid, {1, 1, 1}, 0.5));

    // Sun: striped disc sitting on the horizon, warm top to hot bottom, with glow.
    const double rad = S * 0.25, cx = S * 0.5, cy = horizon - rad * 0.42;
    Mask sun(c.S, c.S);
    fillEllipse(sun, cx, cy, rad, rad);
    Mask glow = sun;
    cutStripes(sun, cy, rad, k, 6, -0.12, 0.105);
    for (int y = static_cast<int>(horizon); y < c.S; ++y)
        for (int x = 0; x < c.S; ++x) sun.at(x, y) = 0.0f;
    blur(glow, 30.0 * k);
    paintSolid(r, glow, lerp(hor, grid, 0.3), 0.75, Blend::Add);
    Mask glow2 = sun;
    blur(glow2, 110.0 * k);
    paintSolid(r, glow2, grid, 0.45, Blend::Add);
    const Gradient sunGrad{{{0.0, sunTop}, {0.45, lerp(sunTop, hor, 0.55)}, {1.0, lerp(hor, grid, 0.45)}}};
    paint(r, sun, [&](int, int y) { return sunGrad.at((y - (cy - rad)) / (2.0 * rad * 0.88)); });

    // Floor.
    const Gradient floorGrad{{{0.0, lerp(role(c, 5), hor, 0.25)}, {0.25, role(c, 5)}, {1.0, scale(role(c, 5), 0.55)}}};
    for (int y = static_cast<int>(horizon); y < c.S; ++y) {
        const Color col = floorGrad.at((y - horizon) / (S - horizon));
        for (int x = 0; x < c.S; ++x) r.at(x, y) = col;
    }
    // The sun's light on the floor, horizon haze and line.
    kit::radialGlow(r, {cx, horizon + S * 0.03}, S * 0.2, hor, 0.3, Blend::Add);
    for (int y = 0; y < c.S; ++y) {
        const double d = (y - horizon) / (S * 0.035);
        const double w = std::exp(-d * d) * 0.55;
        if (w > 1e-3)
            for (int x = 0; x < c.S; ++x) r.put(x, y, lerp(hor, grid, 0.5), w, Blend::Screen);
    }
    Mask line(c.S, c.S);
    strokeLine(line, {-10, horizon}, {S + 10, horizon}, 2.2 * k);
    glowLines(r, line, grid, lerp(grid, {1, 1, 1}, 0.75), k, 1.2);

    // Grid.
    const double phase = (c.seed % 1000) / 1000.0;
    const Mask g = floorGrid(c, horizon, S * 0.5, S * 0.105, 3.2 * k, phase);
    glowLines(r, g, grid, lerp(grid, {1, 1, 1}, 0.35), k);

    // Title and subtitle.
    const double below = chromeTitle(r, c, c.spec.title, S * 0.07, S * 0.155, role(c, 6));
    neonSubtitle(r, c, c.spec.subtitle, below + S * 0.035, S * 0.05, role(c, 7));

    kit::scanlines(r, 3.0 * k, 0.05);
    kit::grain(r, 0.035, c.seed);
    kit::vignette(r, 0.45);
}

// ------------------------------------------------------------------ outrun

namespace {

// Palm silhouette into `m`: a tapered, slightly curved trunk and drooping, serrated fronds.
void palm(Mask& m, Random& rng, Vec2 base, double height, double lean) {
    const Vec2 top{base.x + lean * height, base.y - height};
    const Vec2 ctrl{base.x + lean * height * 0.15 + height * 0.06 * (lean >= 0 ? -1 : 1), base.y - height * 0.55};
    auto trunkAt = [&](double t) {
        const double u = 1.0 - t;
        return Vec2{u * u * base.x + 2 * u * t * ctrl.x + t * t * top.x, u * u * base.y + 2 * u * t * ctrl.y + t * t * top.y};
    };
    std::vector<Vec2> left, right;
    constexpr int kSteps = 40;
    for (int i = 0; i <= kSteps; ++i) {
        const double t = static_cast<double>(i) / kSteps;
        const Vec2 p = trunkAt(t), q = trunkAt(std::min(1.0, t + 0.01)), o = trunkAt(std::max(0.0, t - 0.01));
        double tx = q.x - o.x, ty = q.y - o.y;
        const double tl = std::hypot(tx, ty);
        tx /= tl;
        ty /= tl;
        // Ringed trunk: the width wobbles a little every few steps.
        const double w = height * (0.034 - 0.016 * t) * (1.0 + 0.08 * ((i % 3) == 0));
        left.push_back({p.x - ty * w, p.y + tx * w});
        right.push_back({p.x + ty * w, p.y - tx * w});
    }
    std::vector<Vec2> trunk = left;
    for (auto it = right.rbegin(); it != right.rend(); ++it) trunk.push_back(*it);
    fillPolygon(m, trunk);
    // Fronds: a curved rachis with leaflets that point forward and hang down.
    auto ccw = [](std::vector<Vec2> poly) {
        double area = 0.0;
        for (std::size_t i = 0; i < poly.size(); ++i) {
            const Vec2 a = poly[i], b = poly[(i + 1) % poly.size()];
            area += a.x * b.y - b.x * a.y;
        }
        if (area < 0.0) std::reverse(poly.begin(), poly.end());
        return poly;
    };
    const int n = 9;
    for (int f = 0; f < n; ++f) {
        const double baseAng = -180.0 + 180.0 * f / (n - 1) + rng.range(-9, 9);  // spread over the upper half (y down)
        const double ang = baseAng * kPi / 180.0;
        const double len = height * rng.range(0.38, 0.52) * (std::fabs(std::sin(ang)) > 0.8 ? 0.8 : 1.0);
        const double droop = rng.range(0.6, 0.95) * (1.0 - 0.5 * std::fabs(std::sin(ang)));
        const double dx = std::cos(ang), dy = std::sin(ang);
        auto mid = [&](double t) { return Vec2{top.x + dx * len * t, top.y + dy * len * t + droop * len * t * t}; };
        std::vector<std::vector<Vec2>> parts;
        // Rachis: a thin tapered band.
        {
            std::vector<Vec2> a, b;
            for (int i = 0; i <= 24; ++i) {
                const double t = i / 24.0;
                const Vec2 p = mid(t), q = mid(std::min(1.0, t + 0.02)), o = mid(std::max(0.0, t - 0.02));
                double tx = q.x - o.x, ty = q.y - o.y;
                const double tl = std::max(1e-9, std::hypot(tx, ty));
                tx /= tl;
                ty /= tl;
                const double w = len * 0.014 * (1.0 - 0.8 * t) + 0.6;
                a.push_back({p.x - ty * w, p.y + tx * w});
                b.push_back({p.x + ty * w, p.y - tx * w});
            }
            std::vector<Vec2> band = a;
            for (auto it = b.rbegin(); it != b.rend(); ++it) band.push_back(*it);
            parts.push_back(ccw(band));
        }
        for (double t = 0.06; t < 0.98; t += 0.032) {
            const Vec2 p = mid(t), q = mid(std::min(1.0, t + 0.02)), o = mid(std::max(0.0, t - 0.02));
            double tx = q.x - o.x, ty = q.y - o.y;
            const double tl = std::max(1e-9, std::hypot(tx, ty));
            tx /= tl;
            ty /= tl;
            const double ll = len * 0.3 * std::pow(std::sin(kPi * std::min(1.0, t * 1.08)), 0.75) * (1.0 - 0.3 * t) * rng.range(0.85, 1.1);
            for (int side : {-1, 1}) {
                double lx = tx * 0.45 - ty * side * 0.8, ly = ty * 0.45 + tx * side * 0.8 + 0.55;  // forward, sideways, down
                const double l = std::hypot(lx, ly);
                lx /= l;
                ly /= l;
                const double w = std::max(1.2, ll * 0.09);
                const Vec2 tip{p.x + lx * ll, p.y + ly * ll + ll * 0.12};
                const Vec2 midp{p.x + lx * ll * 0.5 - ly * w * 0.25, p.y + ly * ll * 0.5 + lx * w * 0.25 + ll * 0.03};
                parts.push_back(ccw({{p.x - ly * w * 0.5, p.y + lx * w * 0.5}, {midp.x - ly * w * 0.4, midp.y + lx * w * 0.4}, tip,
                                     {midp.x + ly * w * 0.4, midp.y - lx * w * 0.4}, {p.x + ly * w * 0.5, p.y - lx * w * 0.5}}));
            }
        }
        fillPolygon(m, parts);
    }
}

// Mountain ridge across the canvas: fbm peaks (ridged = sharp crests), raised towards the sides by `edgeLift`.
std::vector<Vec2> ridge(const Ctx& c, double horizon, double height, double edgeLift, double freq, std::uint32_t seed, bool sharp = false) {
    std::vector<Vec2> pts;
    const int n = 240;
    for (int i = 0; i <= n; ++i) {
        const double x = c.S * i / static_cast<double>(n);
        const double u = x / c.S;
        const double side = std::pow(std::fabs(u - 0.5) * 2.0, 1.6);
        double h;
        if (sharp) {
            double sum = 0.0, amp = 0.6, f = freq;
            for (int o = 0; o < 4; ++o) {
                sum += amp * (1.0 - std::fabs(2.0 * valueNoise(u * f, 0.37 + o, seed + static_cast<std::uint32_t>(o)) - 1.0));
                amp *= 0.45;
                f *= 2.1;
            }
            h = std::pow(std::clamp(sum / 1.0, 0.0, 1.2), 2.0);
        } else {
            h = std::pow(std::clamp(fbm(u * freq, 0.37, 5, seed), 0.0, 1.0), 1.5);
        }
        const double y = horizon - height * (0.25 + h) * (1.0 - edgeLift + edgeLift * side);
        pts.push_back({x, std::min(y, horizon)});
    }
    return pts;
}

}  // namespace

void outrun(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const double horizon = S * 0.60;
    const Color warm = role(c, 0), neon = role(c, 1), hor = role(c, 2), skyTop = role(c, 3), skyMid = role(c, 4), floorC = role(c, 5);
    kit::verticalGradient(r, Gradient{{{0.0, skyTop}, {0.40, skyMid}, {0.75, lerp(skyMid, hor, 0.6)}, {1.0, lerp(hor, warm, 0.25)}}}, 0, horizon);
    stars(r, c, horizon * 0.45, 90, lerp(neon, {1, 1, 1}, 0.5));

    // Sun behind the mountains.
    const double rad = S * 0.29, cx = S * 0.5, cy = horizon - rad * 0.36;
    Mask sun(c.S, c.S);
    fillEllipse(sun, cx, cy, rad, rad);
    Mask glow = sun;
    cutStripes(sun, cy, rad, k, 7, -0.05, 0.1);
    blur(glow, 40.0 * k);
    paintSolid(r, glow, lerp(hor, neon, 0.35), 0.8, Blend::Add);
    const Gradient sunGrad{{{0.0, warm}, {0.5, lerp(warm, hor, 0.8)}, {1.0, lerp(hor, neon, 0.7)}}};
    paint(r, sun, [&](int, int y) { return sunGrad.at((y - (cy - rad)) / (1.6 * rad)); });

    // Mountains: a hazy far range and a dark near one with a rim light.
    Mask far = kit::ridgeMask(c.S, c.S, ridge(c, horizon + 2, S * 0.09, 0.3, 3.2, c.seed + 11u), true);
    paintSolid(r, far, lerp(skyMid, hor, 0.35), 0.92);
    const auto nearRidge = ridge(c, horizon + 2, S * 0.075, 0.75, 5.0, c.seed + 23u);
    Mask nearM = kit::ridgeMask(c.S, c.S, nearRidge, true);
    paintSolid(r, nearM, scale(floorC, 1.2));
    Mask rim(c.S, c.S);
    strokePolyline(rim, nearRidge, 2.0 * k);
    glowLines(r, rim, neon, lerp(neon, {1, 1, 1}, 0.4), k, 0.7);

    // Floor with a side grid, the road and its lane marks.
    for (int y = static_cast<int>(horizon); y < c.S; ++y) {
        const double t = (y - horizon) / (S - horizon);
        const Color col = lerp(lerp(floorC, hor, 0.25), scale(floorC, 0.6), std::pow(t, 0.5));
        for (int x = 0; x < c.S; ++x) r.at(x, y) = col;
    }
    kit::radialGlow(r, {cx, horizon + S * 0.02}, S * 0.25, hor, 0.28, Blend::Add);
    const double roadHalf = S * 0.43;
    Mask road(c.S, c.S);
    fillPolygon(road, std::vector<Vec2>{{cx - 1.0, horizon}, {cx + 1.0, horizon}, {cx + roadHalf, S + 2}, {cx - roadHalf, S + 2}});
    Mask grid = floorGrid(c, horizon, cx, S * 0.12, 3.0 * k, (c.seed % 997) / 997.0);
    Mask roadWide(c.S, c.S);
    fillPolygon(roadWide, std::vector<Vec2>{{cx - 3.0, horizon}, {cx + 3.0, horizon}, {cx + roadHalf * 1.1, S + 2}, {cx - roadHalf * 1.1, S + 2}});
    for (std::size_t i = 0; i < grid.data().size(); ++i) grid.data()[i] *= 1.0f - roadWide.data()[i];
    glowLines(r, grid, neon, lerp(neon, {1, 1, 1}, 0.3), k, 0.9);
    paint(r, road, [&](int, int y) {
        const double t = std::clamp((y - horizon) / (S - horizon), 0.0, 1.0);
        return lerp(lerp(floorC, hor, 0.35), hex(0x07040d), std::pow(t, 0.35));
    });
    Mask edges(c.S, c.S), dashes(c.S, c.S);
    for (int side : {-1, 1}) {
        for (int s = 0; s < 8; ++s) {
            const double t0 = s / 8.0, t1 = (s + 1) / 8.0;
            const Vec2 a{cx + side * roadHalf * t0 * 0.97, horizon + (S - horizon) * t0};
            const Vec2 b{cx + side * roadHalf * t1 * 0.97, horizon + (S - horizon) * t1};
            strokeLine(edges, a, b, std::max(0.8, 5.5 * k * (t0 + t1) * 0.5));
        }
    }
    for (int i = 0; i < 40; ++i) {  // centre dashes, equally spaced in depth
        const double z0 = 0.9 + i * 0.55 + ((c.seed % 13) / 13.0) * 0.55, z1 = z0 + 0.25;
        const double y0 = horizon + (S - horizon) / z1, y1 = horizon + (S - horizon) / z0;
        if (y0 - horizon < 1.0) break;
        const double w0 = 7.0 * k * (y0 - horizon) / (S - horizon) + 0.3, w1 = 7.0 * k * (y1 - horizon) / (S - horizon) + 0.3;
        fillPolygon(dashes, std::vector<Vec2>{{cx - w0, y0}, {cx + w0, y0}, {cx + w1, std::min(y1, S + 2.0)}, {cx - w1, std::min(y1, S + 2.0)}});
    }
    glowLines(r, edges, role(c, 7), lerp(role(c, 7), {1, 1, 1}, 0.5), k, 1.0);
    paintSolid(r, dashes, lerp(warm, {1, 1, 1}, 0.3), 0.95);
    Mask dglow = dashes;
    blur(dglow, 6.0 * k);
    paintSolid(r, dglow, warm, 0.6, Blend::Add);
    // Horizon line.
    Mask line(c.S, c.S);
    strokeLine(line, {-10, horizon}, {S + 10, horizon}, 1.6 * k);
    glowLines(r, line, neon, lerp(neon, {1, 1, 1}, 0.7), k, 0.8);

    // Palms (silhouettes against the sunset), two on the left, one on the right.
    Mask palms(c.S, c.S);
    Random prng(c.seed * 31ull + 5ull);
    const bool flip = (c.seed & 1u) != 0;
    const double sL = flip ? -1.0 : 1.0;
    palm(palms, prng, {S * (flip ? 0.9 : 0.1), S * 1.02}, S * 0.62, 0.10 * sL);
    palm(palms, prng, {S * (flip ? 0.99 : 0.01), S * 0.98}, S * 0.50, 0.20 * sL);
    palm(palms, prng, {S * (flip ? 0.12 : 0.88), S * 1.03}, S * 0.52, -0.12 * sL);
    Mask pglow = palms;
    blur(pglow, 10.0 * k);
    paintSolid(r, pglow, neon, 0.25, Blend::Add);
    paintSolid(r, palms, hex(0x07020c));

    const double below = chromeTitle(r, c, c.spec.title, S * 0.06, S * 0.15, role(c, 6));
    neonSubtitle(r, c, c.spec.subtitle, below + S * 0.035, S * 0.048, role(c, 7));
    kit::scanlines(r, 3.0 * k, 0.05);
    kit::grain(r, 0.035, c.seed);
    kit::vignette(r, 0.45);
}

// ------------------------------------------------------------------ dreamwave

void dreamwave(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const double horizon = S * 0.66;
    const Color sunC = role(c, 0), accent = role(c, 1), hor = role(c, 2), skyTop = role(c, 3), skyMid = role(c, 4), hills = role(c, 5);
    kit::verticalGradient(r, Gradient{{{0.0, skyTop}, {0.38, skyMid}, {0.80, lerp(skyMid, hor, 0.75)}, {1.0, lerp(hor, sunC, 0.35)}}}, 0,
                          horizon);
    stars(r, c, horizon * 0.35, 60, {1.0f, 1.0f, 1.0f});
    // Soft striped sun with a halo.
    const double rad = S * 0.17, cx = S * 0.5, cy = horizon - S * 0.085;
    kit::radialGlow(r, {cx, cy}, rad * 1.8, lerp(sunC, hor, 0.6), 0.22, Blend::Add);
    Mask sun(c.S, c.S);
    fillEllipse(sun, cx, cy, rad, rad, 2.5 * k);
    cutStripes(sun, cy, rad, k, 5, 0.05, 0.16);
    for (int y = static_cast<int>(horizon); y < c.S; ++y)
        for (int x = 0; x < c.S; ++x) sun.at(x, y) = 0.0f;
    const Gradient sunGrad{{{0.0, lerp(sunC, {1, 1, 1}, 0.2)}, {0.5, lerp(sunC, hor, 0.35)}, {1.0, lerp(hor, accent, 0.3)}}};
    paint(r, sun, [&](int, int y) { return sunGrad.at((y - (cy - rad)) / (2 * rad)); }, 0.96);
    // Cloud banks: soft horizontal fbm streaks drifting across the sun.
    Mask clouds(c.S, c.S);
    for (int y = 0; y < static_cast<int>(horizon); ++y) {
        const double band = std::exp(-std::pow((y - horizon * 0.84) / (S * 0.06), 2.0)) +
                            0.8 * std::exp(-std::pow((y - horizon * 0.60) / (S * 0.05), 2.0));
        if (band < 0.02) continue;
        for (int x = 0; x < c.S; ++x) {
            const double n = fbm(x / (S * 0.30), y / (S * 0.03), 5, c.seed + 101u);
            clouds.at(x, y) = static_cast<float>(std::clamp((n - 0.45) * 3.0, 0.0, 1.0) * band);
        }
    }
    blur(clouds, 4.0 * k);
    paint(r, clouds, [&](int, int y) { return lerp(lerp(skyMid, {1, 1, 1}, 0.5), hor, 0.2 + 0.5 * y / horizon); }, 0.7);
    // Hills and a soft floor with a faint grid.
    Mask hillM = kit::ridgeMask(c.S, c.S, ridge(c, horizon + 1, S * 0.05, 0.4, 2.2, c.seed + 7u), true);
    paintSolid(r, hillM, lerp(hills, hor, 0.3), 0.95);
    for (int y = static_cast<int>(horizon); y < c.S; ++y) {
        const double t = (y - horizon) / (S - horizon);
        const Color col = lerp(lerp(hills, hor, 0.45), scale(hills, 0.8), std::pow(t, 0.6));
        for (int x = 0; x < c.S; ++x) r.at(x, y) = col;
    }
    Mask grid = floorGrid(c, horizon, cx, S * 0.13, 2.4 * k, (c.seed % 991) / 991.0);
    Mask g1 = grid;
    blur(g1, 6.0 * k);
    paintSolid(r, g1, accent, 0.55, Blend::Add);
    paintSolid(r, grid, lerp(accent, {1, 1, 1}, 0.5), 0.6);
    for (int y = 0; y < c.S; ++y) {  // haze over the horizon
        const double d = (y - horizon) / (S * 0.04);
        const double w = std::exp(-d * d) * 0.45;
        if (w > 1e-3)
            for (int x = 0; x < c.S; ++x) r.put(x, y, lerp(hor, {1, 1, 1}, 0.35), w);
    }
    kit::bloom(r, 0.86, 20.0 * k, 0.25);

    // Thin, widely spaced title with a soft glow; the subtitle small at the bottom.
    FontStyle st;
    st.weight = 0.075;
    st.tracking = 0.16;
    const kit::TitleFit fit = kit::fitTitle(kit::upper(c.spec.title), st, S * 0.78, S * 0.10, 2);
    double y = S * 0.12;
    for (const auto& lineText : fit.lines) {
        y += fit.cap;
        const TextLayout lay = kit::centred(lineText, st, fit.cap, cx, y);
        kit::NeonLook look;
        look.glow = role(c, 6);
        look.glowSigma = 9.0 * k;
        look.glowStrength = 0.75;
        look.coreWhite = 0.95;
        kit::drawNeon(r, lay, look);
        y += fit.cap * 0.45;
    }
    if (!c.spec.subtitle.empty()) {
        FontStyle sub;
        sub.weight = 0.08;
        sub.tracking = 0.45;
        const kit::TitleFit sf = kit::fitTitle(kit::upper(c.spec.subtitle), sub, S * 0.6, S * 0.03, 1);
        const TextLayout lay = kit::centred(sf.lines.empty() ? "" : sf.lines[0], sub, sf.cap, cx, S * 0.93);
        kit::drawShadow(r, lay, scale(role(c, 5), 0.5), {0, 0}, 5.0 * k, 0.55, 3.0 * k);
        kit::drawFlat(r, lay, {1.0f, 1.0f, 1.0f}, 0.95);
    }
    kit::grain(r, 0.025, c.seed);
    kit::vignette(r, 0.18, 0.7);
}

// ------------------------------------------------------------------ darksynth

void darksynth(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const double horizon = S * 0.66;
    const Color red = role(c, 0), neon = role(c, 1), deep = role(c, 2), skyMid = role(c, 4), floorC = role(c, 5);
    kit::verticalGradient(r, Gradient{{{0.0, hex(0x000000)}, {0.55, skyMid}, {0.9, deep}, {1.0, lerp(deep, red, 0.35)}}}, 0, horizon);
    // Inverted neon triangle with an inner echo, sinking behind the mountains.
    const double tcx = S * 0.5, ttop = S * 0.405, tw = S * 0.26;
    const std::vector<Vec2> tri{{tcx - tw, ttop}, {tcx + tw, ttop}, {tcx, ttop + tw * 1.55}};
    const std::vector<Vec2> tri2{{tcx - tw * 0.72, ttop + tw * 0.16}, {tcx + tw * 0.72, ttop + tw * 0.16}, {tcx, ttop + tw * 1.27}};
    Mask triFill(c.S, c.S);
    fillPolygon(triFill, tri);
    paintSolid(r, triFill, hex(0x000000), 0.55);
    Mask triM(c.S, c.S);
    strokePolyline(triM, tri, 7.0 * k, true);
    strokePolyline(triM, tri2, 2.2 * k, true);
    glowLines(r, triM, neon, lerp(neon, {1, 1, 1}, 0.45), k, 1.4);
    kit::radialGlow(r, {tcx, horizon}, S * 0.35, red, 0.35, Blend::Add);
    // Jagged black mountains with a red rim.
    const auto rid = ridge(c, horizon + 2, S * 0.12, 0.55, 5.5, c.seed + 41u, true);
    Mask mount = kit::ridgeMask(c.S, c.S, rid, true);
    paintSolid(r, mount, hex(0x030003));
    Mask rim(c.S, c.S);
    strokePolyline(rim, rid, 1.8 * k);
    glowLines(r, rim, neon, lerp(neon, {1, 1, 1}, 0.2), k, 0.8);
    // Floor + harsh grid.
    for (int y = static_cast<int>(horizon); y < c.S; ++y) {
        const double t = (y - horizon) / (S - horizon);
        const Color col = lerp(lerp(floorC, deep, 0.5), hex(0x000000), std::pow(t, 0.4));
        for (int x = 0; x < c.S; ++x) r.at(x, y) = col;
    }
    const Mask grid = floorGrid(c, horizon, S * 0.5, S * 0.095, 3.6 * k, (c.seed % 983) / 983.0);
    glowLines(r, grid, neon, lerp(neon, {1, 1, 1}, 0.15), k, 1.1);
    Mask line(c.S, c.S);
    strokeLine(line, {-10, horizon}, {S + 10, horizon}, 2.4 * k);
    glowLines(r, line, neon, lerp(neon, {1, 1, 1}, 0.6), k, 1.2);

    // Title: dark steel face with a red glow; subtitle: spaced red capitals.
    FontStyle st;
    st.weight = 0.22;
    st.squareCaps = true;
    st.tracking = 0.05;
    st.widthScale = 1.08;
    const kit::TitleFit fit = kit::fitTitle(kit::upper(c.spec.title), st, S * 0.84, S * 0.14, 2);
    double y = S * 0.05;
    kit::ChromeLook look;
    look.face = Gradient{{{0.0, hex(0xf2f2f2)}, {0.42, hex(0x8c8c8c)}, {0.5, hex(0x1a1a1a)}, {0.56, hex(0x3a0006)}, {1.0, lerp(red, hex(0x000000), 0.35)}}};
    look.outline = hex(0x000000);
    look.outlineWidth = 4.0 * k;
    look.glow = neon;
    look.glowSigma = 16.0 * k;
    look.glowStrength = 1.0;
    look.bevel = 4.0 * k;
    look.highlight = {1.0f, 0.9f, 0.9f};
    for (const auto& lineText : fit.lines) {
        y += fit.cap;
        kit::drawChrome(r, kit::centred(lineText, st, fit.cap, S * 0.5, y), look);
        y += fit.cap * 0.3;
    }
    if (!c.spec.subtitle.empty()) {
        FontStyle sub;
        sub.weight = 0.11;
        sub.squareCaps = true;
        sub.tracking = 0.5;
        const kit::TitleFit sf = kit::fitTitle(kit::upper(c.spec.subtitle), sub, S * 0.7, S * 0.032, 1);
        kit::NeonLook nl;
        nl.glow = role(c, 7);
        nl.glowSigma = 4.0 * k;
        nl.coreWhite = 0.35;
        kit::drawNeon(r, kit::centred(sf.lines.empty() ? "" : sf.lines[0], sub, sf.cap, S * 0.5, y + S * 0.04 + sf.cap), nl);
    }

    // Glitch: a few horizontal slices shifted sideways with a red/cyan split.
    Raster copy = r;
    Random g(c.seed * 131ull + 7ull);
    for (int i = 0; i < 7; ++i) {
        const int y0 = static_cast<int>(g.range(0.15, 0.95) * S), h = static_cast<int>(g.range(2.0, 14.0) * k) + 1;
        const int dx = static_cast<int>(g.range(-28.0, 28.0) * k);
        for (int yy = y0; yy < std::min(c.S, y0 + h); ++yy)
            for (int x = 0; x < c.S; ++x) {
                const int sx = std::clamp(x - dx, 0, c.S - 1), sr = std::clamp(x - dx - static_cast<int>(4 * k), 0, c.S - 1);
                Color p = copy.at(sx, yy);
                p.r = copy.at(sr, yy).r;
                r.at(x, yy) = p;
            }
    }
    kit::scanlines(r, 3.0 * k, 0.12);
    kit::grain(r, 0.06, c.seed);
    kit::vignette(r, 0.6, 0.45);
}

}  // namespace as::art::styles
