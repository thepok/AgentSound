#include "art/CoverKit.h"

#include "core/Params.h"  // ConfigError

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>
#include <functional>

namespace as::art::kit {

// ------------------------------------------------------------------ palettes

namespace {

bool parseHex(const std::string& s, Color& out) {
    std::string h = s;
    while (!h.empty() && std::isspace(static_cast<unsigned char>(h.front()))) h.erase(h.begin());
    while (!h.empty() && std::isspace(static_cast<unsigned char>(h.back()))) h.pop_back();
    if (!h.empty() && h[0] == '#') h.erase(h.begin());
    if (h.size() != 6) return false;
    std::uint32_t v = 0;
    for (char ch : h) {
        v <<= 4;
        if (ch >= '0' && ch <= '9') v |= static_cast<std::uint32_t>(ch - '0');
        else if (ch >= 'a' && ch <= 'f') v |= static_cast<std::uint32_t>(ch - 'a' + 10);
        else if (ch >= 'A' && ch <= 'F') v |= static_cast<std::uint32_t>(ch - 'A' + 10);
        else return false;
    }
    out = hex(v);
    return true;
}

}  // namespace

std::vector<Color> resolvePalette(const std::string& style, const std::vector<Palette>& palettes, const std::string& spec) {
    if (palettes.empty()) return {};
    if (spec.empty()) return palettes.front().c;
    if (spec.find('#') != std::string::npos || spec.find(',') != std::string::npos) {
        std::vector<Color> c = palettes.front().c;
        std::size_t start = 0, i = 0;
        while (start <= spec.size()) {
            const std::size_t comma = spec.find(',', start);
            const std::string part = spec.substr(start, comma == std::string::npos ? std::string::npos : comma - start);
            Color col;
            if (!parseHex(part, col)) throw ConfigError("cover palette: '" + part + "' is not a #rrggbb colour");
            if (i >= 3 || i >= c.size()) throw ConfigError("cover palette: at most 3 colours (the style's main accents)");
            c[i++] = col;
            if (comma == std::string::npos) break;
            start = comma + 1;
        }
        return c;
    }
    std::string names;
    for (const auto& p : palettes) {
        if (spec == p.name) return p.c;
        names += (names.empty() ? "" : ", ") + std::string(p.name);
    }
    throw ConfigError("cover style '" + style + "' has no palette '" + spec + "' (palettes: " + names + ", or \"#rrggbb,#rrggbb\")");
}

// ------------------------------------------------------------------ text helpers

namespace {

std::string encodeUtf8(const std::u32string& s) {
    std::string out;
    for (char32_t c : s) {
        if (c < 0x80) out += static_cast<char>(c);
        else if (c < 0x800) {
            out += static_cast<char>(0xC0 | (c >> 6));
            out += static_cast<char>(0x80 | (c & 0x3F));
        } else if (c < 0x10000) {
            out += static_cast<char>(0xE0 | (c >> 12));
            out += static_cast<char>(0x80 | ((c >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (c & 0x3F));
        } else {
            out += static_cast<char>(0xF0 | (c >> 18));
            out += static_cast<char>(0x80 | ((c >> 12) & 0x3F));
            out += static_cast<char>(0x80 | ((c >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (c & 0x3F));
        }
    }
    return out;
}

}  // namespace

std::string upper(const std::string& utf8) {
    std::u32string out;
    for (char32_t c : decodeUtf8(utf8)) {
        if (c >= U'a' && c <= U'z') out.push_back(c - 32);
        else if (c == 0xDF) out += U"SS";
        else if (c >= 0xE0 && c <= 0xFE && c != 0xF7) out.push_back(c - 0x20);
        else out.push_back(c);
    }
    return encodeUtf8(out);
}

std::string lower(const std::string& utf8) {
    std::u32string out;
    for (char32_t c : decodeUtf8(utf8)) {
        if (c >= U'A' && c <= U'Z') out.push_back(c + 32);
        else if (c >= 0xC0 && c <= 0xDE && c != 0xD7) out.push_back(c + 0x20);
        else out.push_back(c);
    }
    return encodeUtf8(out);
}

TitleFit fitTitle(const std::string& text, const FontStyle& st, double maxWidth, double maxCap, int maxLines) {
    std::vector<std::string> words;
    {
        std::string cur;
        for (char ch : text) {
            if (ch == ' ' || ch == '\t' || ch == '\n') {
                if (!cur.empty()) words.push_back(cur);
                cur.clear();
            } else {
                cur += ch;
            }
        }
        if (!cur.empty()) words.push_back(cur);
    }
    TitleFit best;
    if (words.empty()) return best;
    const int n = static_cast<int>(words.size());
    double bestScore = -1.0;
    for (int k = 1; k <= std::min(maxLines, n); ++k) {
        // Every composition of the words into k consecutive lines (n is small for titles).
        std::vector<int> cut(static_cast<std::size_t>(k - 1));
        std::function<void(int, int)> rec;
        rec = [&](int idx, int from) {
            if (idx == k - 1) {
                std::vector<std::string> lines;
                int start = 0;
                for (int c = 0; c <= k - 1; ++c) {
                    const int end = c < k - 1 ? cut[static_cast<std::size_t>(c)] : n;
                    std::string line;
                    for (int w = start; w < end; ++w) line += (w > start ? " " : "") + words[static_cast<std::size_t>(w)];
                    lines.push_back(line);
                    start = end;
                }
                double widest = 0.0, narrowest = 1e300;
                for (const auto& l : lines) {
                    const double w = measureText(l, st, 100.0) / 100.0;
                    widest = std::max(widest, w);
                    narrowest = std::min(narrowest, w);
                }
                const double cap = widest > 0 ? std::min(maxCap, maxWidth / widest) : maxCap;
                // Bigger type wins; each extra line costs 12 %; balanced lines are preferred.
                const double score = cap * std::pow(0.88, k - 1) * (0.9 + 0.1 * narrowest / std::max(widest, 1e-9));
                if (score > bestScore) {
                    bestScore = score;
                    best.lines = lines;
                    best.cap = cap;
                }
                return;
            }
            for (int c = from; c <= n - (k - 1 - idx); ++c) {
                cut[static_cast<std::size_t>(idx)] = c;
                rec(idx + 1, c + 1);
            }
        };
        rec(0, 1);
    }
    return best;
}

TextLayout centred(const std::string& line, const FontStyle& st, double cap, double centreX, double baselineY) {
    const TextLayout probe = layoutText(line, st, cap, {0.0, baselineY});
    const double dx = centreX - 0.5 * (probe.x0 + probe.x1);
    return layoutText(line, st, cap, {dx, baselineY});
}

// ------------------------------------------------------------------ text effects

namespace {

Mask shifted(const Mask& m, Vec2 off) {
    Mask out(m.width(), m.height());
    const int ox = static_cast<int>(std::lround(off.x)), oy = static_cast<int>(std::lround(off.y));
    for (int y = 0; y < m.height(); ++y)
        for (int x = 0; x < m.width(); ++x) out.at(x, y) = m.sample(x - ox, y - oy);
    return out;
}

}  // namespace

void drawChrome(Raster& r, const TextLayout& lay, const ChromeLook& look) {
    const double reach = look.outlineWidth + std::max(look.bevel, 2.0) + 4.0;
    const DistanceField f = textDistance(lay, r.width(), r.height(), reach);
    const Mask rim = textMask(f, look.outlineWidth);
    if (look.shadowAlpha > 0.0) {
        Mask sh = shifted(rim, {0.0, lay.capHeight * 0.05});
        blur(sh, std::max(2.0, look.glowSigma * 0.5));
        paintSolid(r, sh, {0.0f, 0.0f, 0.0f}, look.shadowAlpha);
    }
    if (look.glowStrength > 0.0) {
        Mask g = rim;
        blur(g, look.glowSigma);
        paintSolid(r, g, look.glow, look.glowStrength, Blend::Add);
        Mask g2 = rim;
        blur(g2, look.glowSigma * 3.0);
        paintSolid(r, g2, look.glow, look.glowStrength * 0.45, Blend::Add);
    }
    paintSolid(r, rim, look.outline);
    const double top = lay.origin.y - lay.capHeight;
    const double lx = -0.42, ly = -0.91;  // towards the light (up, slightly left)
    const int x0 = std::max(0, static_cast<int>(lay.x0) - 2), x1 = std::min(r.width() - 1, static_cast<int>(lay.x1) + 2);
    const int y0 = std::max(0, static_cast<int>(lay.y0) - 2), y1 = std::min(r.height() - 1, static_cast<int>(lay.y1) + 2);
    for (int y = y0; y <= y1; ++y) {
        for (int x = x0; x <= x1; ++x) {
            const double d = f.at(x, y);
            const double cov = std::clamp(0.5 - d, 0.0, 1.0);
            if (cov <= 0.0) continue;
            Color c = look.face.at((y + 0.5 - top) / lay.capHeight);
            if (look.bevel > 0.0) {
                double gx = f.at(x + 1, y) - f.at(x - 1, y), gy = f.at(x, y + 1) - f.at(x, y - 1);
                const double gl = std::hypot(gx, gy);
                if (gl > 1e-6) {
                    gx /= gl;
                    gy /= gl;
                    const double edge = std::clamp(1.0 + d / look.bevel, 0.0, 1.0);
                    const double lit = gx * lx + gy * ly;
                    c = lerp(c, look.highlight, edge * std::max(0.0, lit) * 0.9);
                    c = scale(c, 1.0 - 0.5 * edge * std::max(0.0, -lit));
                }
            }
            r.put(x, y, c, cov);
        }
    }
}

void drawNeon(Raster& r, const TextLayout& lay, const NeonLook& look) {
    const DistanceField f = textDistance(lay, r.width(), r.height(), 4.0);
    const Mask core = textMask(f, 0.0);
    Mask g1 = textMask(f, lay.penHalfWidth * 0.5);
    blur(g1, look.glowSigma);
    paintSolid(r, g1, look.glow, look.glowStrength, Blend::Add);
    Mask g2 = core;
    blur(g2, look.glowSigma * 3.2);
    paintSolid(r, g2, look.glow, look.glowStrength * 0.55, Blend::Add);
    const double hw = std::max(0.8, lay.penHalfWidth);
    const Color hot = saturate(scale(look.glow, 1.25), 0.85);
    const int x0 = std::max(0, static_cast<int>(lay.x0) - 2), x1 = std::min(r.width() - 1, static_cast<int>(lay.x1) + 2);
    const int y0 = std::max(0, static_cast<int>(lay.y0) - 2), y1 = std::min(r.height() - 1, static_cast<int>(lay.y1) + 2);
    for (int y = y0; y <= y1; ++y) {
        for (int x = x0; x <= x1; ++x) {
            const double d = f.at(x, y);
            const double cov = std::clamp(0.5 - d, 0.0, 1.0);
            if (cov <= 0.0) continue;
            const double inner = std::pow(std::clamp(-d / hw, 0.0, 1.0), 0.7);
            r.put(x, y, lerp(hot, {1.0f, 1.0f, 1.0f}, look.coreWhite * inner), cov);
        }
    }
}

void drawFlat(Raster& r, const TextLayout& lay, Color fill, double alpha, Blend mode) {
    const DistanceField f = textDistance(lay, r.width(), r.height(), 2.0);
    paintSolid(r, textMask(f), fill, alpha, mode);
}

void drawShadow(Raster& r, const TextLayout& lay, Color c, Vec2 offset, double sigma, double alpha, double grow) {
    const DistanceField f = textDistance(lay, r.width(), r.height(), grow + 2.0);
    Mask m = shifted(textMask(f, grow), offset);
    blur(m, sigma);
    paintSolid(r, m, c, alpha);
}

void drawDistressed(Raster& r, const TextLayout& lay, Color fill, double wear, std::uint32_t seed) {
    const DistanceField f = textDistance(lay, r.width(), r.height(), 2.0);
    Mask m = textMask(f);
    const double s = std::max(4.0, lay.capHeight / 9.0);
    for (int y = 0; y < m.height(); ++y) {
        for (int x = 0; x < m.width(); ++x) {
            float& a = m.at(x, y);
            if (a <= 0.0f) continue;
            const double n = 0.65 * fbm(x / s, y / s, 4, seed) + 0.35 * hashUnit(x / 2, y / 2, seed + 7u);
            const double keep = std::clamp((n - wear) * 8.0 + 0.5, 0.0, 1.0);
            a *= static_cast<float>(keep);
        }
    }
    paintSolid(r, m, fill);
}

// ------------------------------------------------------------------ backgrounds and finishing

void verticalGradient(Raster& r, const Gradient& g, double y0, double y1) {
    for (int y = 0; y < r.height(); ++y) {
        const Color c = g.at((y + 0.5 - y0) / std::max(1e-9, y1 - y0));
        for (int x = 0; x < r.width(); ++x) r.at(x, y) = c;
    }
}

void radialGlow(Raster& r, Vec2 c, double radius, Color color, double strength, Blend mode) {
    const double reach = radius * 3.0;
    const int x0 = std::max(0, static_cast<int>(c.x - reach)), x1 = std::min(r.width() - 1, static_cast<int>(c.x + reach));
    const int y0 = std::max(0, static_cast<int>(c.y - reach)), y1 = std::min(r.height() - 1, static_cast<int>(c.y + reach));
    for (int y = y0; y <= y1; ++y)
        for (int x = x0; x <= x1; ++x) {
            const double d = std::hypot(x + 0.5 - c.x, y + 0.5 - c.y) / radius;
            const double w = std::exp(-d * d) * strength;
            if (w > 1e-4) r.put(x, y, color, w, mode);
        }
}

void grain(Raster& r, double amount, std::uint32_t seed) {
    for (int y = 0; y < r.height(); ++y)
        for (int x = 0; x < r.width(); ++x) {
            const double n = (hashUnit(x, y, seed) + hashUnit(x >> 1, y >> 1, seed + 3u) - 1.0) * amount;
            Color& p = r.at(x, y);
            const auto k = static_cast<float>(n);
            p.r += k;
            p.g += k;
            p.b += k;
        }
}

void vignette(Raster& r, double strength, double inner) {
    const double cx = r.width() * 0.5, cy = r.height() * 0.5, rmax = std::hypot(cx, cy);
    for (int y = 0; y < r.height(); ++y)
        for (int x = 0; x < r.width(); ++x) {
            const double d = std::hypot(x + 0.5 - cx, y + 0.5 - cy) / rmax;
            const double t = std::clamp((d - inner) / (1.0 - inner), 0.0, 1.0);
            const double k = 1.0 - strength * t * t * (3.0 - 2.0 * t);
            r.at(x, y) = scale(r.at(x, y), k);
        }
}

void scanlines(Raster& r, double period, double strength) {
    for (int y = 0; y < r.height(); ++y) {
        const double ph = std::fmod(y + 0.5, period) / period;
        const double k = 1.0 - strength * (0.5 + 0.5 * std::cos(2.0 * 3.14159265358979 * ph));
        for (int x = 0; x < r.width(); ++x) r.at(x, y) = scale(r.at(x, y), k);
    }
}

void bloom(Raster& r, double threshold, double sigma, double strength) {
    Raster bright(r.width(), r.height());
    for (std::size_t i = 0; i < r.pixels().size(); ++i) {
        const Color c = r.pixels()[i];
        const double l = luma(c);
        const double k = l > threshold ? (l - threshold) / std::max(1e-6, 1.0 - threshold) : 0.0;
        bright.pixels()[i] = scale(c, std::min(1.5, k));
    }
    blur(bright, sigma);
    for (std::size_t i = 0; i < r.pixels().size(); ++i) {
        Color& p = r.pixels()[i];
        const Color b = bright.pixels()[i];
        p.r += b.r * static_cast<float>(strength);
        p.g += b.g * static_cast<float>(strength);
        p.b += b.b * static_cast<float>(strength);
    }
}

void halftone(Raster& r, const Mask& area, double cell, double angleDeg, Color ink, double gamma) {
    const double a = angleDeg * 3.14159265358979 / 180.0, ca = std::cos(a), sa = std::sin(a);
    for (int y = 0; y < r.height(); ++y) {
        for (int x = 0; x < r.width(); ++x) {
            const double px = x + 0.5, py = y + 0.5;
            const double u = (px * ca + py * sa) / cell, v = (-px * sa + py * ca) / cell;
            const double cu = std::floor(u) + 0.5, cv = std::floor(v) + 0.5;
            // Tone at the cell centre (back-rotated).
            const double cx = (cu * ca - cv * sa) * cell, cy = (cu * sa + cv * ca) * cell;
            const double tone = std::pow(std::clamp(static_cast<double>(area.sample(static_cast<int>(cx), static_cast<int>(cy))), 0.0, 1.0), gamma);
            if (tone <= 0.0) continue;
            const double rad = 0.5 * std::sqrt(tone) * 1.35;  // in cells; > 0.5 merges into a solid
            const double d = std::hypot(u - cu, v - cv);
            const double cov = std::clamp((rad - d) * cell + 0.5, 0.0, 1.0);
            if (cov > 0.0) r.put(x, y, ink, cov);
        }
    }
}

Mask ridgeMask(int w, int h, const std::vector<Vec2>& ridge, bool below) {
    Mask m(w, h);
    if (ridge.size() < 2) return m;
    std::vector<Vec2> poly = ridge;
    if (below) {
        poly.push_back({ridge.back().x, static_cast<double>(h) + 2});
        poly.push_back({ridge.front().x, static_cast<double>(h) + 2});
    } else {
        poly.push_back({ridge.back().x, -2.0});
        poly.push_back({ridge.front().x, -2.0});
    }
    fillPolygon(m, poly);
    return m;
}

}  // namespace as::art::kit
