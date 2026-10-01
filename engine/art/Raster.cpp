#include "art/Raster.h"

#include <algorithm>
#include <cmath>

namespace as::art {

// ------------------------------------------------------------------ colour

Color lerp(Color a, Color b, double t) noexcept {
    const auto k = static_cast<float>(std::clamp(t, 0.0, 1.0));
    return {a.r + (b.r - a.r) * k, a.g + (b.g - a.g) * k, a.b + (b.b - a.b) * k};
}

Color scale(Color c, double k) noexcept {
    const auto f = static_cast<float>(k);
    return {c.r * f, c.g * f, c.b * f};
}

Color addc(Color a, Color b) noexcept { return {a.r + b.r, a.g + b.g, a.b + b.b}; }

double luma(Color c) noexcept { return 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b; }

Color saturate(Color c, double amount) noexcept {
    const auto l = static_cast<float>(luma(c));
    const auto k = static_cast<float>(amount);
    return {l + (c.r - l) * k, l + (c.g - l) * k, l + (c.b - l) * k};
}

Color Gradient::at(double t) const noexcept {
    if (stops.empty()) return {};
    if (t <= stops.front().first) return stops.front().second;
    for (std::size_t i = 1; i < stops.size(); ++i) {
        if (t <= stops[i].first) {
            const double span = stops[i].first - stops[i - 1].first;
            return lerp(stops[i - 1].second, stops[i].second, span > 0 ? (t - stops[i - 1].first) / span : 1.0);
        }
    }
    return stops.back().second;
}

// ------------------------------------------------------------------ raster

Raster::Raster(int width, int height, Color fill)
    : w_(std::max(1, width)), h_(std::max(1, height)), px_(static_cast<std::size_t>(w_) * static_cast<std::size_t>(h_), fill) {}

namespace {
inline float blendChannel(float d, float s, Blend mode) noexcept {
    switch (mode) {
        case Blend::Normal: return s;
        case Blend::Add: return d + s;
        case Blend::Screen: return 1.0f - (1.0f - std::clamp(d, 0.0f, 1.0f)) * (1.0f - std::clamp(s, 0.0f, 1.0f));
        case Blend::Multiply: return d * s;
        case Blend::Overlay: return d < 0.5f ? 2.0f * d * s : 1.0f - 2.0f * (1.0f - d) * (1.0f - s);
        case Blend::SoftLight: return (1.0f - 2.0f * s) * d * d + 2.0f * s * d;
    }
    return s;
}
}  // namespace

void Raster::put(int x, int y, Color c, double a, Blend mode) noexcept {
    if (!inside(x, y) || !(a > 0.0)) return;
    Color& d = at(x, y);
    const auto k = static_cast<float>(std::min(a, 1.0));
    if (mode == Blend::Add) {
        d.r += c.r * k;
        d.g += c.g * k;
        d.b += c.b * k;
        return;
    }
    const Color t{blendChannel(d.r, c.r, mode), blendChannel(d.g, c.g, mode), blendChannel(d.b, c.b, mode)};
    d.r += (t.r - d.r) * k;
    d.g += (t.g - d.g) * k;
    d.b += (t.b - d.b) * k;
}

void paintSolid(Raster& r, const Mask& m, Color c, double alpha, Blend mode) {
    paint(r, m, [c](int, int) { return c; }, alpha, mode);
}

// ------------------------------------------------------------------ mask

void Mask::clear() noexcept { std::fill(a_.begin(), a_.end(), 0.0f); }

void Mask::maxWith(const Mask& o) noexcept {
    const std::size_t n = std::min(a_.size(), o.a_.size());
    for (std::size_t i = 0; i < n; ++i) a_[i] = std::max(a_[i], o.a_[i]);
}

void Mask::multiply(const Mask& o) noexcept {
    const std::size_t n = std::min(a_.size(), o.a_.size());
    for (std::size_t i = 0; i < n; ++i) a_[i] *= o.a_[i];
}

void Mask::invert() noexcept {
    for (float& v : a_) v = 1.0f - std::clamp(v, 0.0f, 1.0f);
}

void Mask::scaleBy(float k) noexcept {
    for (float& v : a_) v *= k;
}

// ------------------------------------------------------------------ shapes

void fillPolygon(Mask& m, const std::vector<std::vector<Vec2>>& contours) {
    struct Edge {
        double x0, y0, x1, y1;
        int dir;
    };
    std::vector<Edge> edges;
    double ymin = 1e300, ymax = -1e300, xmin = 1e300, xmax = -1e300;
    for (const auto& c : contours) {
        const std::size_t n = c.size();
        if (n < 3) continue;
        for (std::size_t i = 0; i < n; ++i) {
            Vec2 a = c[i], b = c[(i + 1) % n];
            xmin = std::min({xmin, a.x, b.x});
            xmax = std::max({xmax, a.x, b.x});
            if (a.y == b.y) continue;
            int dir = 1;
            if (a.y > b.y) {
                std::swap(a, b);
                dir = -1;
            }
            edges.push_back({a.x, a.y, b.x, b.y, dir});
            ymin = std::min(ymin, a.y);
            ymax = std::max(ymax, b.y);
        }
    }
    if (edges.empty()) return;
    std::sort(edges.begin(), edges.end(), [](const Edge& p, const Edge& q) { return p.y0 < q.y0; });
    // Only the polygon's columns [bx0, bx1) are touched.
    const int bx0 = std::clamp(static_cast<int>(std::floor(xmin)), 0, m.width());
    const int bx1 = std::clamp(static_cast<int>(std::ceil(xmax)) + 1, 0, m.width());
    if (bx1 <= bx0) return;
    const int W = bx1 - bx0;
    const int y0 = std::max(0, static_cast<int>(std::floor(ymin))), y1 = std::min(m.height() - 1, static_cast<int>(std::ceil(ymax)));
    constexpr int S = 16;
    constexpr float kSub = 1.0f / S;
    std::vector<float> row(static_cast<std::size_t>(W) + 1, 0.0f);
    std::vector<std::pair<double, int>> xs;
    auto span = [&](double a, double b) {
        a = std::clamp(a - bx0, 0.0, static_cast<double>(W));
        b = std::clamp(b - bx0, 0.0, static_cast<double>(W));
        if (b <= a) return;
        const int ia = static_cast<int>(a), ib = static_cast<int>(b);
        if (ia == ib) {
            row[static_cast<std::size_t>(ia)] += static_cast<float>(b - a) * kSub;
            return;
        }
        row[static_cast<std::size_t>(ia)] += static_cast<float>(ia + 1 - a) * kSub;
        for (int i = ia + 1; i < ib; ++i) row[static_cast<std::size_t>(i)] += kSub;
        if (ib < W) row[static_cast<std::size_t>(ib)] += static_cast<float>(b - ib) * kSub;
    };
    std::size_t first = 0;
    for (int py = y0; py <= y1; ++py) {
        std::fill(row.begin(), row.end(), 0.0f);
        while (first < edges.size() && edges[first].y1 < py) {
            // edges are sorted by y0 only; skip the leading ones that ended (cheap heuristic)
            if (edges[first].y1 < py) ++first;
            else break;
        }
        for (int k = 0; k < S; ++k) {
            const double ys = py + (k + 0.5) / S;
            xs.clear();
            for (std::size_t i = first; i < edges.size(); ++i) {
                const Edge& e = edges[i];
                if (e.y0 > ys) break;
                if (ys >= e.y1) continue;
                xs.push_back({e.x0 + (ys - e.y0) * (e.x1 - e.x0) / (e.y1 - e.y0), e.dir});
            }
            if (xs.size() < 2) continue;
            std::sort(xs.begin(), xs.end());
            int wind = 0;
            double start = 0.0;
            for (const auto& [x, dir] : xs) {
                const int prev = wind;
                wind += dir;
                if (prev == 0 && wind != 0) start = x;
                else if (prev != 0 && wind == 0) span(start, x);
            }
        }
        for (int x = 0; x < W; ++x) {
            const float v = std::min(1.0f, row[static_cast<std::size_t>(x)]);
            if (v > 0.0f) m.at(bx0 + x, py) = std::max(m.at(bx0 + x, py), v);
        }
    }
}

void fillPolygon(Mask& m, const std::vector<Vec2>& contour) { fillPolygon(m, std::vector<std::vector<Vec2>>{contour}); }

void fillEllipse(Mask& m, double cx, double cy, double rx, double ry, double feather) {
    if (!(rx > 0.0 && ry > 0.0)) return;
    const double f = std::max(1.0, feather);
    const int x0 = std::max(0, static_cast<int>(std::floor(cx - rx - f - 1))), x1 = std::min(m.width() - 1, static_cast<int>(std::ceil(cx + rx + f + 1)));
    const int y0 = std::max(0, static_cast<int>(std::floor(cy - ry - f - 1))), y1 = std::min(m.height() - 1, static_cast<int>(std::ceil(cy + ry + f + 1)));
    for (int y = y0; y <= y1; ++y) {
        for (int x = x0; x <= x1; ++x) {
            const double dx = x + 0.5 - cx, dy = y + 0.5 - cy;
            const double k = std::sqrt((dx / rx) * (dx / rx) + (dy / ry) * (dy / ry));
            double d;  // signed distance, + inside
            if (k < 1e-9) {
                d = std::min(rx, ry);
            } else {
                const double gx = dx / (rx * rx), gy = dy / (ry * ry);
                const double g = std::sqrt(gx * gx + gy * gy) / k;
                d = (1.0 - k) / std::max(g, 1e-12);
            }
            const double v = std::clamp(d / f + 0.5, 0.0, 1.0);
            if (v > 0.0) m.at(x, y) = std::max(m.at(x, y), static_cast<float>(v));
        }
    }
}

void strokePolyline(Mask& m, const std::vector<Vec2>& pts, double width, bool closed) {
    const std::size_t n = pts.size();
    if (n == 0) return;
    const double hw = width * 0.5, r = hw + 1.0;
    const std::size_t segs = closed ? n : (n > 1 ? n - 1 : 1);
    for (std::size_t s = 0; s < segs; ++s) {
        const Vec2 a = pts[s], b = pts[(s + 1) % n];
        const double dx = b.x - a.x, dy = b.y - a.y, len2 = dx * dx + dy * dy;
        const int x0 = std::max(0, static_cast<int>(std::floor(std::min(a.x, b.x) - r)));
        const int x1 = std::min(m.width() - 1, static_cast<int>(std::ceil(std::max(a.x, b.x) + r)));
        const int y0 = std::max(0, static_cast<int>(std::floor(std::min(a.y, b.y) - r)));
        const int y1 = std::min(m.height() - 1, static_cast<int>(std::ceil(std::max(a.y, b.y) + r)));
        for (int y = y0; y <= y1; ++y) {
            for (int x = x0; x <= x1; ++x) {
                const double px = x + 0.5 - a.x, py = y + 0.5 - a.y;
                const double t = len2 > 0 ? std::clamp((px * dx + py * dy) / len2, 0.0, 1.0) : 0.0;
                const double ex = px - t * dx, ey = py - t * dy;
                const double v = std::clamp(hw + 0.5 - std::sqrt(ex * ex + ey * ey), 0.0, 1.0);
                if (v > 0.0) m.at(x, y) = std::max(m.at(x, y), static_cast<float>(v));
            }
        }
    }
}

void strokeLine(Mask& m, Vec2 a, Vec2 b, double width) { strokePolyline(m, {a, b}, width, false); }

// ------------------------------------------------------------------ blur

namespace {

std::vector<int> boxesForGauss(double sigma, int n) {
    const double wIdeal = std::sqrt(12.0 * sigma * sigma / n + 1.0);
    int wl = static_cast<int>(std::floor(wIdeal));
    if (wl % 2 == 0) --wl;
    wl = std::max(1, wl);
    const int wu = wl + 2;
    const double mIdeal = (12.0 * sigma * sigma - n * wl * wl - 4.0 * n * wl - 3.0 * n) / (-4.0 * wl - 4.0);
    const int mm = static_cast<int>(std::lround(mIdeal));
    std::vector<int> sizes;
    for (int i = 0; i < n; ++i) sizes.push_back(i < mm ? wl : wu);
    return sizes;
}

// One box pass (radius r) over `len` samples with stride, clamped edges.
void boxPass(float* data, int len, std::size_t stride, int r, std::vector<float>& tmp) {
    if (r <= 0 || len <= 1) return;
    tmp.resize(static_cast<std::size_t>(len));
    for (int i = 0; i < len; ++i) tmp[static_cast<std::size_t>(i)] = data[static_cast<std::size_t>(i) * stride];
    const float inv = 1.0f / static_cast<float>(2 * r + 1);
    auto v = [&](int i) { return tmp[static_cast<std::size_t>(std::clamp(i, 0, len - 1))]; };
    double acc = 0.0;
    for (int i = -r; i <= r; ++i) acc += v(i);
    for (int i = 0; i < len; ++i) {
        data[static_cast<std::size_t>(i) * stride] = static_cast<float>(acc) * inv;
        acc += v(i + r + 1) - v(i - r);
    }
}

void blurPlane(float* data, int w, int h, std::size_t pixelStride, double sigma) {
    if (!(sigma > 0.3)) return;
    const auto boxes = boxesForGauss(sigma, 3);
    std::vector<float> tmp;
    for (int b : boxes) {
        const int r = (b - 1) / 2;
        for (int y = 0; y < h; ++y) boxPass(data + static_cast<std::size_t>(y) * static_cast<std::size_t>(w) * pixelStride, w, pixelStride, r, tmp);
        for (int x = 0; x < w; ++x) boxPass(data + static_cast<std::size_t>(x) * pixelStride, h, static_cast<std::size_t>(w) * pixelStride, r, tmp);
    }
}

}  // namespace

void blur(Mask& m, double sigma) { blurPlane(m.data().data(), m.width(), m.height(), 1, sigma); }

void blur(Raster& r, double sigma) {
    float* base = &r.pixels().data()->r;
    for (int c = 0; c < 3; ++c) blurPlane(base + c, r.width(), r.height(), 3, sigma);
}

// ------------------------------------------------------------------ noise

std::uint32_t hash32(std::uint32_t x) noexcept {
    x ^= x >> 16;
    x *= 0x7feb352dU;
    x ^= x >> 15;
    x *= 0x846ca68bU;
    x ^= x >> 16;
    return x;
}

double hashUnit(int x, int y, std::uint32_t seed) noexcept {
    const std::uint32_t h = hash32(static_cast<std::uint32_t>(x) * 0x9E3779B1U ^ hash32(static_cast<std::uint32_t>(y) + 0x85EBCA6BU) ^ seed);
    return (h >> 8) * (1.0 / 16777216.0);
}

double valueNoise(double x, double y, std::uint32_t seed) noexcept {
    const double fx = std::floor(x), fy = std::floor(y);
    const int ix = static_cast<int>(fx), iy = static_cast<int>(fy);
    const double tx = x - fx, ty = y - fy;
    const double sx = tx * tx * (3.0 - 2.0 * tx), sy = ty * ty * (3.0 - 2.0 * ty);
    const double a = hashUnit(ix, iy, seed), b = hashUnit(ix + 1, iy, seed);
    const double c = hashUnit(ix, iy + 1, seed), d = hashUnit(ix + 1, iy + 1, seed);
    return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy;
}

double fbm(double x, double y, int octaves, std::uint32_t seed) noexcept {
    double sum = 0.0, amp = 0.5, norm = 0.0, f = 1.0;
    for (int o = 0; o < octaves; ++o) {
        sum += amp * valueNoise(x * f, y * f, seed + static_cast<std::uint32_t>(o) * 1013U);
        norm += amp;
        amp *= 0.5;
        f *= 2.03;
    }
    return norm > 0 ? sum / norm : 0.0;
}

Random::Random(std::uint64_t seed) noexcept : s_(seed * 0x9E3779B97F4A7C15ULL + 0x632BE59BD9B4E019ULL) {
    if (s_ == 0) s_ = 0x2545F4914F6CDD1DULL;
    next();
}

std::uint64_t Random::next() noexcept {
    s_ ^= s_ >> 12;
    s_ ^= s_ << 25;
    s_ ^= s_ >> 27;
    return s_ * 0x2545F4914F6CDD1DULL;
}

double Random::uniform() noexcept { return static_cast<double>(next() >> 11) * (1.0 / 9007199254740992.0); }
double Random::range(double lo, double hi) noexcept { return lo + (hi - lo) * uniform(); }
int Random::below(int n) noexcept { return n > 0 ? static_cast<int>(next() % static_cast<std::uint64_t>(n)) : 0; }

// ------------------------------------------------------------------ output

analysis::Image toImage(const Raster& r, std::uint32_t seed) {
    analysis::Image img;
    img.width = r.width();
    img.height = r.height();
    img.rgb.resize(static_cast<std::size_t>(img.width) * static_cast<std::size_t>(img.height) * 3);
    std::size_t k = 0;
    for (int y = 0; y < img.height; ++y) {
        for (int x = 0; x < img.width; ++x) {
            const Color c = r.at(x, y);
            const double d = hashUnit(x, y, seed) + hashUnit(x + 7919, y + 104729, seed) - 1.0;  // triangular, +-1 LSB
            for (float v : {c.r, c.g, c.b}) {
                const double q = std::floor(std::clamp(static_cast<double>(v), 0.0, 1.0) * 255.0 + 0.5 + 0.5 * d);
                img.rgb[k++] = static_cast<std::uint8_t>(std::clamp(q, 0.0, 255.0));
            }
        }
    }
    return img;
}

}  // namespace as::art
