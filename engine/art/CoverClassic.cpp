// Classic-sleeve covers: jazz, classical, rock, pop.

#include "art/CoverStyles.h"

#include <algorithm>
#include <cmath>

namespace as::art::styles {

namespace {

constexpr double kPi = 3.14159265358979323846;

Color role(const Ctx& c, int i) { return c.pal[static_cast<std::size_t>(i)]; }

double smooth01(double t) {
    t = std::clamp(t, 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

// Paper: a flat colour with low-contrast fibres and speckles.
void paper(Raster& r, Color base, double amount, std::uint32_t seed, double k) {
    for (int y = 0; y < r.height(); ++y)
        for (int x = 0; x < r.width(); ++x) {
            const double n = fbm(x / (90.0 * k), y / (90.0 * k), 4, seed) - 0.5;
            const double f = fbm(x / (3.0 * k), y / (14.0 * k), 2, seed + 9u) - 0.5;
            r.at(x, y) = scale(base, 1.0 + amount * (0.9 * n + 0.35 * f));
        }
}

// Left-aligned block of lines (title fitted to maxWidth), returns the baseline of the last line.
double leftBlock(Raster& r, const std::vector<std::string>& lines, const FontStyle& st, double cap, double x, double firstBaseline,
                 double lineGap, const std::vector<Color>& colors) {
    double y = firstBaseline;
    for (std::size_t i = 0; i < lines.size(); ++i) {
        const TextLayout lay = layoutText(lines[i], st, cap, {x, y});
        kit::drawFlat(r, lay, colors[std::min(i, colors.size() - 1)]);
        if (i + 1 < lines.size()) y += cap * lineGap;
    }
    return y;
}

}  // namespace

// Palette roles:
//   jazz       0 duotone tint   1 accent (block, second title line)   2 background   3 light type
//   classical  0 gold / accent  1 type                                 2 paper        3 secondary type
//   rock       0 accent red     1 white type                           2 black        3 grey
//   pop        0 blob 1         1 blob 2                               2 blob 3       3 blob 4 (base)
std::vector<kit::Palette> classicPalettes(const std::string& style) {
    if (style == "jazz")
        return {{"midnight", {hex(0x2f6fd8), hex(0xf2a900), hex(0x0e1726), hex(0xf1ece0)}},
                {"ember", {hex(0xd9531e), hex(0x2fb5a8), hex(0x16110e), hex(0xf3ead8)}},
                {"sea", {hex(0x2a9d8f), hex(0xe9c46a), hex(0x0f1c1f), hex(0xf1ede2)}}};
    if (style == "classical")
        return {{"ivory", {hex(0xa8854f), hex(0x262422), hex(0xf3eee3), hex(0x6b6255)}},
                {"noir", {hex(0xc9a45c), hex(0xefe6d2), hex(0x121212), hex(0x9c927f)}},
                {"sage", {hex(0x7d8f5a), hex(0x26302a), hex(0xe4e6dc), hex(0x5d6a5f)}}};
    if (style == "rock")
        return {{"black", {hex(0xe0201c), hex(0xf2f0ea), hex(0x0b0b0b), hex(0x6f6f6f)}},
                {"acid", {hex(0xc6ff1a), hex(0xf5f5f0), hex(0x0c0c0c), hex(0x707070)}},
                {"cream", {hex(0xd62828), hex(0x111111), hex(0xece6d6), hex(0x8a8375)}}};
    if (style == "pop")
        return {{"candy", {hex(0xff3d8b), hex(0xffb13d), hex(0x7b3dff), hex(0x3dd9ff)}},
                {"citrus", {hex(0xffd23d), hex(0xff6b3d), hex(0x3dffb0), hex(0x3d8bff)}},
                {"berry", {hex(0xff2e63), hex(0xa12eff), hex(0xff9ad5), hex(0x2e2bff)}}};
    return {};
}

// ------------------------------------------------------------------ jazz

void jazz(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const Color tint = role(c, 0), accent = role(c, 1), bg = role(c, 2), light = role(c, 3);
    for (auto& p : r.pixels()) p = bg;

    // The "photo": a record under a spotlight in smoke, as a two-colour halftone print.
    const double photoH = S * 0.58;
    Mask tone(c.S, c.S);  // ink amount 0..1 (darkness)
    const double rcx = S * (0.60 + 0.08 * ((c.seed % 5) / 4.0)), rcy = photoH * 0.52, R = S * 0.36;
    const double sheenAng = (c.seed % 360) * kPi / 180.0;
    for (int y = 0; y < static_cast<int>(photoH); ++y) {
        for (int x = 0; x < c.S; ++x) {
            const double dxs = (x - S * 0.30) / (S * 0.55), dys = (y - photoH * 0.15) / (S * 0.5);
            double light1 = 0.25 + 0.75 * std::exp(-(dxs * dxs + dys * dys) * 1.6);          // spotlight
            light1 *= 0.75 + 0.5 * (fbm(x / (160.0 * k), y / (110.0 * k), 5, c.seed) - 0.5);  // smoke
            double ink = 1.0 - std::clamp(light1, 0.0, 1.0);
            const double dx = x - rcx, dy = y - rcy, rr = std::hypot(dx, dy);
            if (rr < R) {
                const double th = std::atan2(dy, dx);
                const double groove = 0.5 + 0.5 * std::sin(rr / (2.2 * k));
                const double sheen = std::pow(std::max(0.0, std::cos(2.0 * (th - sheenAng))), 10.0);
                double rec = 0.88 - 0.06 * groove - 0.55 * sheen * smooth01((rr - R * 0.36) / (R * 0.2));
                // The label is painted over it: keep the ink dark underneath, else the halftone cells that
                // straddle the label's edge leave light 'teeth' outside the painted disc.
                if (rr < R * 0.34) rec = 0.9;
                const double edge = std::clamp((R - rr) / (1.5 * k), 0.0, 1.0);
                ink = ink + (rec - ink) * edge;
            }
            tone.at(x, y) = static_cast<float>(std::clamp(ink, 0.0, 1.0));
        }
    }
    Mask area(c.S, c.S);
    fillPolygon(area, std::vector<Vec2>{{0, 0}, {S, 0}, {S, photoH}, {0, photoH}});
    paintSolid(r, area, lerp(tint, light, 0.18));
    kit::halftone(r, tone, 7.0 * k, 45.0, lerp(bg, hex(0x000000), 0.4), 1.15);
    // Record label in the accent colour, with its hole.
    Mask label(c.S, c.S);
    fillEllipse(label, rcx, rcy, R * 0.34, R * 0.34);
    for (int y = static_cast<int>(photoH); y < c.S; ++y)
        for (int x = 0; x < c.S; ++x) label.at(x, y) = 0.0f;
    paintSolid(r, label, accent);
    Mask ring(c.S, c.S);
    strokePolyline(ring, [&] {
        std::vector<Vec2> v;
        for (int i = 0; i <= 120; ++i) v.push_back({rcx + R * 0.26 * std::cos(i * 2 * kPi / 120), rcy + R * 0.26 * std::sin(i * 2 * kPi / 120)});
        return v;
    }(), 1.6 * k);
    paintSolid(r, ring, lerp(accent, bg, 0.35));
    Mask hole(c.S, c.S);
    fillEllipse(hole, rcx, rcy, R * 0.025, R * 0.025);
    paintSolid(r, hole, bg);
    // Film grain on the photo only.
    for (int y = 0; y < static_cast<int>(photoH); ++y)
        for (int x = 0; x < c.S; ++x) {
            const auto n = static_cast<float>((hashUnit(x, y, c.seed + 5u) - 0.5) * 0.06);
            Color& p = r.at(x, y);
            p.r += n;
            p.g += n;
            p.b += n;
        }

    // Colour block + type: artist in spaced capitals on the block, the title huge and bold below.
    const double margin = S * 0.065;
    const double blockH = S * 0.075;
    Mask block(c.S, c.S);
    fillPolygon(block, std::vector<Vec2>{{0, photoH}, {S * 0.62, photoH}, {S * 0.62, photoH + blockH}, {0, photoH + blockH}});
    paintSolid(r, block, accent);
    FontStyle cap;
    cap.weight = 0.13;
    cap.squareCaps = true;
    cap.tracking = 0.22;
    const std::string artist = c.spec.subtitle.empty() ? std::string("AGENTSOUND") : kit::upper(c.spec.subtitle);
    const kit::TitleFit af = kit::fitTitle(artist, cap, S * 0.62 - 2 * margin, blockH * 0.4, 1);
    if (!af.lines.empty())
        kit::drawFlat(r, layoutText(af.lines[0], cap, af.cap, {margin, photoH + blockH * 0.5 + af.cap * 0.5}), bg);
    FontStyle big;
    big.weight = 0.2;
    big.widthScale = 0.8;
    big.squareCaps = true;
    big.tracking = -0.01;
    const std::string title = kit::lower(c.spec.title);
    const double avail = S - photoH - blockH - S * 0.075;
    kit::TitleFit tf = kit::fitTitle(title, big, S - 2 * margin, avail * 0.52, 2);
    if (tf.lines.size() == 1) tf = kit::fitTitle(title, big, S - 2 * margin, avail * 0.62, 1);
    const double lineGap = 1.12;
    const double blockTextH = tf.cap * (1.0 + lineGap * (static_cast<double>(tf.lines.size()) - 1.0));
    const double first = photoH + blockH + (S - photoH - blockH - blockTextH) * 0.5 + tf.cap * 0.92;
    leftBlock(r, tf.lines, big, tf.cap, margin - tf.cap * 0.02, first, lineGap, {light, accent});
    // Catalogue number and a small mark in the corner.
    FontStyle tiny;
    tiny.weight = 0.12;
    tiny.squareCaps = true;
    tiny.tracking = 0.2;
    char cat[32];
    std::snprintf(cat, sizeof cat, "AS %04u", static_cast<unsigned>(4000 + (c.seed % 1000)));
    const double tcap = S * 0.017;
    const double tw = measureText(cat, tiny, tcap);
    kit::drawFlat(r, layoutText(cat, tiny, tcap, {S - margin - tw, photoH + blockH * 0.5 + tcap * 0.5}), lerp(light, bg, 0.2));
    kit::vignette(r, 0.15, 0.7);
    kit::grain(r, 0.02, c.seed + 1u);
}

// ------------------------------------------------------------------ classical

void classical(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const Color gold = role(c, 0), ink = role(c, 1), pap = role(c, 2), soft = role(c, 3);
    paper(r, pap, 0.05, c.seed, k);
    // Double frame.
    const double m1 = S * 0.045, m2 = S * 0.058;
    Mask frame(c.S, c.S);
    strokePolyline(frame, {{m1, m1}, {S - m1, m1}, {S - m1, S - m1}, {m1, S - m1}}, 2.2 * k, true);
    strokePolyline(frame, {{m2, m2}, {S - m2, m2}, {S - m2, S - m2}, {m2, S - m2}}, 0.9 * k, true);
    paintSolid(r, frame, gold, 0.9);
    // A thin gold circle around a soft watercolour wash: the image of the sleeve.
    const double cx = S * 0.5, cy = S * 0.335, R = S * 0.19;
    Mask wash(c.S, c.S);
    for (int y = static_cast<int>(cy - R * 1.3); y < static_cast<int>(cy + R * 1.3); ++y) {
        if (y < 0 || y >= c.S) continue;
        for (int x = static_cast<int>(cx - R * 1.3); x < static_cast<int>(cx + R * 1.3); ++x) {
            if (x < 0 || x >= c.S) continue;
            const double d = std::hypot(x - cx - R * 0.10, y - cy + R * 0.12) / (R * 0.92);
            const double n = fbm(x / (150.0 * k), y / (150.0 * k), 4, c.seed + 3u);
            const double v = std::clamp(1.0 - d, 0.0, 1.0);
            wash.at(x, y) = static_cast<float>(std::pow(v, 0.8) * (0.55 + 0.9 * (n - 0.5)) * 0.5);
        }
    }
    blur(wash, 3.0 * k);
    paintSolid(r, wash, lerp(gold, pap, 0.25), 0.9, Blend::Multiply);
    Mask circle(c.S, c.S);
    std::vector<Vec2> pts;
    for (int i = 0; i <= 360; ++i) pts.push_back({cx + R * std::cos(i * kPi / 180.0), cy + R * std::sin(i * kPi / 180.0)});
    strokePolyline(circle, pts, 1.6 * k, true);
    std::vector<Vec2> arc;
    for (int i = 200; i <= 340; ++i) arc.push_back({cx + R * 1.07 * std::cos(i * kPi / 180.0), cy + R * 1.07 * std::sin(i * kPi / 180.0)});
    strokePolyline(circle, arc, 0.8 * k);
    paintSolid(r, circle, gold);

    // Title in high-contrast serif capitals, centred; ornament; subtitle in spaced small capitals.
    FontStyle serif;
    serif.weight = 0.13;
    serif.contrast = 1.0;
    serif.serifs = true;
    serif.squareCaps = true;
    serif.tracking = 0.10;
    const kit::TitleFit tf = kit::fitTitle(kit::upper(c.spec.title), serif, S * 0.76, S * 0.068, 2);
    double y = S * 0.70;
    if (tf.lines.size() > 1) y -= tf.cap * 0.5;
    for (const auto& line : tf.lines) {
        kit::drawFlat(r, kit::centred(line, serif, tf.cap, cx, y), ink);
        y += tf.cap * 1.55;
    }
    y -= tf.cap * 1.55;
    const double oy = y + S * 0.045;
    Mask orn(c.S, c.S);
    strokeLine(orn, {cx - S * 0.12, oy}, {cx - S * 0.018, oy}, 1.0 * k);
    strokeLine(orn, {cx + S * 0.018, oy}, {cx + S * 0.12, oy}, 1.0 * k);
    fillPolygon(orn, std::vector<Vec2>{{cx, oy - 6 * k}, {cx + 6 * k, oy}, {cx, oy + 6 * k}, {cx - 6 * k, oy}});
    paintSolid(r, orn, gold);
    if (!c.spec.subtitle.empty()) {
        FontStyle small;
        small.weight = 0.09;
        small.tracking = 0.34;
        const kit::TitleFit sf = kit::fitTitle(kit::upper(c.spec.subtitle), small, S * 0.72, S * 0.024, 1);
        if (!sf.lines.empty()) kit::drawFlat(r, kit::centred(sf.lines[0], small, sf.cap, cx, oy + S * 0.075), soft);
    }
    kit::vignette(r, 0.12, 0.6);
}

// ------------------------------------------------------------------ rock

void rock(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const Color red = role(c, 0), white = role(c, 1), black = role(c, 2), grey = role(c, 3);
    // Grimy ground: stains and dust.
    for (int y = 0; y < c.S; ++y)
        for (int x = 0; x < c.S; ++x) {
            const double n = fbm(x / (220.0 * k), y / (220.0 * k), 5, c.seed);
            r.at(x, y) = lerp(black, grey, std::clamp((n - 0.5) * 0.5 + 0.06, 0.0, 0.3));
        }
    // A big distressed disc (red), cut by black diagonal bars.
    const double cx = S * 0.64, cy = S * 0.34, R = S * 0.33;
    Mask disc(c.S, c.S);
    fillEllipse(disc, cx, cy, R, R);
    Mask bars(c.S, c.S);
    for (int i = -2; i <= 2; ++i) {
        const double off = i * S * 0.14 + (static_cast<int>(c.seed % 7u) - 3) * S * 0.01;
        const double w = S * 0.022;
        fillPolygon(bars, std::vector<Vec2>{{cx - R * 1.3 + off, cy + R * 1.3}, {cx - R * 1.3 + off + w, cy + R * 1.3},
                                             {cx + R * 1.3 + off + w, cy - R * 1.3}, {cx + R * 1.3 + off, cy - R * 1.3}});
    }
    for (std::size_t i = 0; i < disc.data().size(); ++i) disc.data()[i] *= 1.0f - bars.data()[i];
    for (int y = 0; y < c.S; ++y)
        for (int x = 0; x < c.S; ++x) {
            float& a = disc.at(x, y);
            if (a <= 0.0f) continue;
            const double n = 0.7 * fbm(x / (26.0 * k), y / (26.0 * k), 4, c.seed + 11u) + 0.3 * hashUnit(x, y, c.seed + 12u);
            a *= static_cast<float>(std::clamp((n - 0.28) * 6.0, 0.0, 1.0));
        }
    paintSolid(r, disc, red);
    // Halftone shading over the disc's lower right.
    Mask shade(c.S, c.S);
    for (int y = 0; y < c.S; ++y)
        for (int x = 0; x < c.S; ++x) {
            const double d = ((x - cx) * 0.6 + (y - cy) * 0.8) / R;
            shade.at(x, y) = static_cast<float>(disc.at(x, y) * std::clamp(d * 0.9, 0.0, 0.8));
        }
    kit::halftone(r, shade, 9.0 * k, 30.0, black, 1.0);
    // Scratches.
    Mask scr(c.S, c.S);
    Random g(c.seed * 97ull + 3ull);
    for (int i = 0; i < 28; ++i) {
        const double x0 = g.range(0, S), y0 = g.range(0, S), len = g.range(0.05, 0.4) * S, a = g.range(-0.3, 0.3) + (g.uniform() < 0.5 ? 0.0 : kPi / 2);
        strokeLine(scr, {x0, y0}, {x0 + std::cos(a) * len, y0 + std::sin(a) * len}, g.range(0.4, 1.2) * k);
    }
    paintSolid(r, scr, white, 0.18);

    // Title: huge distressed condensed capitals at the bottom left; red kicker above.
    const double margin = S * 0.06;
    FontStyle big;
    big.weight = 0.25;
    big.widthScale = 0.78;
    big.squareCaps = true;
    big.tracking = 0.0;
    const kit::TitleFit tf = kit::fitTitle(kit::upper(c.spec.title), big, S - 2 * margin, S * 0.2, 2);
    double y = S - margin - tf.cap * 1.12 * (static_cast<double>(tf.lines.size()) - 1.0);
    const double titleTop = y - tf.cap;
    for (const auto& line : tf.lines) {
        const TextLayout lay = layoutText(line, big, tf.cap, {margin - tf.cap * 0.04, y});
        kit::drawShadow(r, lay, hex(0x000000), {6 * k, 6 * k}, 3.0 * k, 0.7);
        kit::drawDistressed(r, lay, white, 0.33, c.seed + 21u);
        y += tf.cap * 1.12;
    }
    if (!c.spec.subtitle.empty()) {
        FontStyle kick;
        kick.weight = 0.16;
        kick.squareCaps = true;
        kick.tracking = 0.28;
        const kit::TitleFit sf = kit::fitTitle(kit::upper(c.spec.subtitle), kick, S * 0.7, S * 0.034, 1);
        if (!sf.lines.empty()) {
            const TextLayout lay = layoutText(sf.lines[0], kick, sf.cap, {margin, titleTop - S * 0.035});
            Mask bar(c.S, c.S);
            fillPolygon(bar, std::vector<Vec2>{{margin, titleTop - S * 0.03 + 4 * k}, {margin + lay.advance, titleTop - S * 0.03 + 4 * k},
                                               {margin + lay.advance, titleTop - S * 0.03 + 9 * k}, {margin, titleTop - S * 0.03 + 9 * k}});
            paintSolid(r, bar, red);
            kit::drawDistressed(r, lay, red, 0.25, c.seed + 22u);
        }
    }
    kit::grain(r, 0.09, c.seed);
    kit::vignette(r, 0.55, 0.4);
}

// ------------------------------------------------------------------ pop

void pop(Raster& r, Ctx& c) {
    const double S = c.S, k = c.k();
    const Color b1 = role(c, 0), b2 = role(c, 1), b3 = role(c, 2), base = role(c, 3);
    // Mesh-like gradient: a base diagonal ramp and big soft colour blobs.
    for (int y = 0; y < c.S; ++y)
        for (int x = 0; x < c.S; ++x) r.at(x, y) = lerp(base, b3, (x + y) / (2.0 * S));
    Random g(c.seed * 13ull + 1ull);
    const Vec2 p1{S * g.range(0.1, 0.35), S * g.range(0.1, 0.35)}, p2{S * g.range(0.65, 0.9), S * g.range(0.2, 0.45)},
        p3{S * g.range(0.3, 0.7), S * g.range(0.65, 0.9)};
    kit::radialGlow(r, p1, S * 0.42, b1, 0.95, Blend::Normal);
    kit::radialGlow(r, p2, S * 0.38, b2, 0.9, Blend::Normal);
    kit::radialGlow(r, p3, S * 0.40, b3, 0.8, Blend::Normal);
    // A glossy sphere with its shadow, and a small one.
    auto sphere = [&](double cx, double cy, double R, Color col) {
        Mask sh(c.S, c.S);
        fillEllipse(sh, cx + R * 0.18, cy + R * 0.95, R * 0.95, R * 0.22);
        blur(sh, R * 0.12);
        paintSolid(r, sh, hex(0x000000), 0.28);
        Mask m(c.S, c.S);
        fillEllipse(m, cx, cy, R, R);
        paint(r, m, [&](int x, int y) {
            const double nx = (x - cx) / R, ny = (y - cy) / R;
            const double nz = std::sqrt(std::max(0.0, 1.0 - nx * nx - ny * ny));
            const double lambert = std::clamp(-0.45 * nx - 0.55 * ny + 0.7 * nz, 0.0, 1.0);
            const double rim = std::pow(1.0 - nz, 3.0);
            const double spec = std::pow(std::max(0.0, -0.4 * nx - 0.5 * ny + 0.77 * nz), 40.0);
            Color out = lerp(scale(col, 0.45), col, lambert);
            out = lerp(out, b2, rim * 0.5);
            return lerp(out, {1, 1, 1}, spec * 0.9);
        });
    };
    sphere(S * 0.66, S * 0.36, S * 0.2, lerp(b1, b3, 0.3));
    sphere(S * 0.27, S * 0.2, S * 0.07, lerp(b2, b1, 0.2));
    // Title: heavy rounded type with a soft shadow, lower left; subtitle above it.
    const double margin = S * 0.07;
    FontStyle big;
    big.weight = 0.22;
    big.tracking = 0.0;
    const kit::TitleFit tf = kit::fitTitle(kit::lower(c.spec.title), big, S - 2 * margin, S * 0.17, 2);
    // Heavy lower case: a first line with descenders (g, j, p, q, y) needs more room above the second.
    const bool descends = tf.lines.size() > 1 && tf.lines[0].find_first_of("gjpqy") != std::string::npos;
    const double lead = tf.cap * (descends ? 1.38 : 1.24);
    double y = S - margin - lead * (static_cast<double>(tf.lines.size()) - 1.0) - tf.cap * 0.25;
    const double top = y - tf.cap;
    for (const auto& line : tf.lines) {
        const TextLayout lay = layoutText(line, big, tf.cap, {margin, y});
        kit::drawShadow(r, lay, scale(b3, 0.35), {0, 10 * k}, 14.0 * k, 0.55);
        kit::drawFlat(r, lay, {1.0f, 1.0f, 1.0f});
        y += lead;
    }
    if (!c.spec.subtitle.empty()) {
        FontStyle sub;
        sub.weight = 0.14;
        sub.tracking = 0.12;
        const kit::TitleFit sf = kit::fitTitle(kit::upper(c.spec.subtitle), sub, S * 0.7, S * 0.03, 1);
        if (!sf.lines.empty()) {
            const TextLayout lay = layoutText(sf.lines[0], sub, sf.cap, {margin, top - S * 0.04});
            kit::drawShadow(r, lay, scale(b3, 0.35), {0, 4 * k}, 6.0 * k, 0.4);
            kit::drawFlat(r, lay, {1.0f, 1.0f, 1.0f}, 0.95);
        }
    }
    kit::grain(r, 0.025, c.seed);
}

}  // namespace as::art::styles
