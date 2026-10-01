#include "analysis/ComparePlot.h"

#include "analysis/PlotKit.h"

#include <algorithm>
#include <cmath>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace as::analysis {

namespace {

constexpr Rgb kMixCol = rgbHex(0x55ccff);
constexpr Rgb kRefCol = rgbHex(0xffb020);
constexpr Rgb kUp = rgbHex(0xff6a5a);    // mix louder / more
constexpr Rgb kDown = rgbHex(0x5aa9ff);  // mix quieter / less
constexpr int W = kImageW;
constexpr int X0 = kPlotX0, X1 = kPlotX1;

// ------------------------------------------------------------------ json access (strict)

[[noreturn]] void bad(const std::string& what) { throw ConfigError("compare.json: " + what); }

const json& need(const json& j, const char* key) {
    if (!j.is_object() || !j.contains(key)) bad(std::string("missing '") + key + "'");
    return j.at(key);
}

std::optional<double> optNum(const json& j) {
    if (j.is_number()) return j.get<double>();
    return std::nullopt;
}

std::optional<double> optNum(const json& j, const char* key) {
    if (!j.is_object() || !j.contains(key)) return std::nullopt;
    return optNum(j.at(key));
}

std::vector<std::optional<double>> numList(const json& j, const char* key, bool required = true) {
    std::vector<std::optional<double>> v;
    if (!j.is_object() || !j.contains(key)) {
        if (required) bad(std::string("missing '") + key + "'");
        return v;
    }
    const json& a = j.at(key);
    if (!a.is_array()) bad(std::string("'") + key + "' must be an array");
    for (const auto& e : a) v.push_back(optNum(e));
    return v;
}

std::string str(const json& j, const char* key, const std::string& def = "") {
    if (j.is_object() && j.contains(key) && j.at(key).is_string()) return j.at(key).get<std::string>();
    return def;
}

// ------------------------------------------------------------------ anti-aliased strokes

// Polyline with round joins, coverage max-combined in a local buffer and blended once.
void stroke(Canvas& c, const std::vector<std::pair<double, double>>& pts, Rgb col, double width, double alpha = 1.0,
            int clipY0 = 0, int clipY1 = 1 << 30) {
    if (pts.size() < 2) return;
    double minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
    for (const auto& [x, y] : pts) {
        minX = std::min(minX, x); maxX = std::max(maxX, x);
        minY = std::min(minY, y); maxY = std::max(maxY, y);
    }
    const double r = width * 0.5 + 1.0;
    const int bx0 = std::max(0, static_cast<int>(std::floor(minX - r))), bx1 = std::min(c.width() - 1, static_cast<int>(std::ceil(maxX + r)));
    const int by0 = std::max({0, clipY0, static_cast<int>(std::floor(minY - r))});
    const int by1 = std::min({c.height() - 1, clipY1, static_cast<int>(std::ceil(maxY + r))});
    if (bx1 < bx0 || by1 < by0) return;
    const int bw = bx1 - bx0 + 1, bh = by1 - by0 + 1;
    std::vector<float> cov(static_cast<std::size_t>(bw) * static_cast<std::size_t>(bh), 0.0f);
    for (std::size_t s = 0; s + 1 < pts.size(); ++s) {
        const double ax = pts[s].first, ay = pts[s].second, qx = pts[s + 1].first, qy = pts[s + 1].second;
        const double dx = qx - ax, dy = qy - ay, len2 = dx * dx + dy * dy;
        const int sx0 = std::max(bx0, static_cast<int>(std::floor(std::min(ax, qx) - r)));
        const int sx1 = std::min(bx1, static_cast<int>(std::ceil(std::max(ax, qx) + r)));
        const int sy0 = std::max(by0, static_cast<int>(std::floor(std::min(ay, qy) - r)));
        const int sy1 = std::min(by1, static_cast<int>(std::ceil(std::max(ay, qy) + r)));
        for (int y = sy0; y <= sy1; ++y) {
            for (int x = sx0; x <= sx1; ++x) {
                const double px = x + 0.5 - ax, py = y + 0.5 - ay;
                const double t = len2 > 0 ? std::clamp((px * dx + py * dy) / len2, 0.0, 1.0) : 0.0;
                const double ex = px - t * dx, ey = py - t * dy;
                const double d = std::sqrt(ex * ex + ey * ey);
                const auto v = static_cast<float>(std::clamp(width * 0.5 + 0.5 - d, 0.0, 1.0));
                float& cell = cov[static_cast<std::size_t>(y - by0) * static_cast<std::size_t>(bw) + static_cast<std::size_t>(x - bx0)];
                cell = std::max(cell, v);
            }
        }
    }
    for (int y = 0; y < bh; ++y)
        for (int x = 0; x < bw; ++x) {
            const float v = cov[static_cast<std::size_t>(y) * static_cast<std::size_t>(bw) + static_cast<std::size_t>(x)];
            if (v > 0.0f) c.blend(bx0 + x, by0 + y, col, v * alpha);
        }
}

void disc(Canvas& c, double cx, double cy, double rad, Rgb col, double alpha = 1.0) {
    const int x0 = static_cast<int>(std::floor(cx - rad - 1)), x1 = static_cast<int>(std::ceil(cx + rad + 1));
    const int y0 = static_cast<int>(std::floor(cy - rad - 1)), y1 = static_cast<int>(std::ceil(cy + rad + 1));
    for (int y = y0; y <= y1; ++y)
        for (int x = x0; x <= x1; ++x) {
            const double d = std::hypot(x + 0.5 - cx, y + 0.5 - cy);
            const double v = std::clamp(rad + 0.5 - d, 0.0, 1.0);
            if (v > 0) c.blend(x, y, col, v * alpha);
        }
}

// Catmull-Rom through (x, y) points, sampled every ~2 px.
std::vector<std::pair<double, double>> smoothCurve(const std::vector<std::pair<double, double>>& p) {
    if (p.size() < 3) return p;
    std::vector<std::pair<double, double>> out;
    for (std::size_t i = 0; i + 1 < p.size(); ++i) {
        const auto& p0 = p[i ? i - 1 : 0];
        const auto& p1 = p[i];
        const auto& p2 = p[i + 1];
        const auto& p3 = p[std::min(p.size() - 1, i + 2)];
        const int steps = std::max(2, static_cast<int>((p2.first - p1.first) / 2.0));
        for (int s = 0; s < steps; ++s) {
            const double t = static_cast<double>(s) / steps, t2 = t * t, t3 = t2 * t;
            auto cr = [&](double a, double b, double cc, double d) {
                return 0.5 * (2 * b + (-a + cc) * t + (2 * a - 5 * b + 4 * cc - d) * t2 + (-a + 3 * b - 3 * cc + d) * t3);
            };
            out.push_back({cr(p0.first, p1.first, p2.first, p3.first), cr(p0.second, p1.second, p2.second, p3.second)});
        }
    }
    out.push_back(p.back());
    return out;
}

// ------------------------------------------------------------------ frequency axis

double fx(double hz) { return X0 + std::log(std::max(hz, 20.0) / 20.0) / std::log(1000.0) * (X1 - X0); }

void freqAxis(Canvas& c, int y) {
    static constexpr std::pair<double, const char*> kTicks[] = {{31.5, "31"}, {63, "63"}, {125, "125"}, {250, "250"}, {500, "500"},
                                                                {1000, "1k"}, {2000, "2k"}, {4000, "4k"}, {8000, "8k"}, {16000, "16k"}};
    for (const auto& [f, label] : kTicks) {
        const int x = static_cast<int>(std::lround(fx(f)));
        c.vline(x, y, y + 4, kDim);
        c.text(x - Canvas::textWidth(label, 2) / 2, y + 7, label, kDim, 2);
    }
    c.text(X1 + 8, y + 7, "Hz", kDim, 2);
}

void freqGrid(Canvas& c, int y0, int y1) {
    for (double f : {31.5, 63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0})
        c.dashedVline(static_cast<int>(std::lround(fx(f))), y0, y1, kWhite, 1, 3, 0.10);
}

// Report bands as alternating background columns with their names on top.
void bandColumns(Canvas& c, int y0, int y1, bool names) {
    static constexpr double kEdges[] = {20, 60, 250, 800, 2500, 6000, 12000, 20000};
    for (int b = 0; b < kNumBands; ++b) {
        const int xa = static_cast<int>(std::lround(fx(kEdges[b]))), xb = static_cast<int>(std::lround(fx(kEdges[b + 1])));
        c.fillRect(xa, y0, xb, y1, b % 2 ? kPanel : kLane);
        if (names) {
            const std::string n = kBandNames[b];
            if (Canvas::textWidth(n, 2) + 6 < xb - xa) c.text(xa + 4, y0 + 3, n, kBandColors[b], 2);
        }
    }
}

// ------------------------------------------------------------------ panels

struct Spectrum {
    std::vector<double> hz;
    std::vector<std::optional<double>> mix, ref, diff, smooth;
    std::vector<bool> valid;
};

Spectrum readSpectrum(const json& cmp) {
    const json& s = need(cmp, "spectrum");
    Spectrum sp;
    for (const auto& v : numList(s, "hz")) {
        if (!v) bad("spectrum.hz must be numbers");
        sp.hz.push_back(*v);
    }
    sp.mix = numList(s, "mixDb");
    sp.ref = numList(s, "refDb");
    sp.diff = numList(s, "diffDb");
    sp.smooth = numList(s, "smoothDiffDb", false);
    const std::size_t n = sp.hz.size();
    if (sp.mix.size() != n || sp.ref.size() != n || sp.diff.size() != n) bad("spectrum arrays differ in length");
    if (sp.smooth.size() != n) sp.smooth.assign(n, std::nullopt);
    sp.valid.assign(n, true);
    if (s.contains("valid") && s.at("valid").is_array() && s.at("valid").size() == n)
        for (std::size_t i = 0; i < n; ++i) sp.valid[i] = s.at("valid")[i].is_boolean() ? s.at("valid")[i].get<bool>() : true;
    return sp;
}

void spectrumPanel(Canvas& c, const Spectrum& sp, int y0, int h) {
    const int y1 = y0 + h;
    double hi = -1e9, lo = 1e9;
    for (std::size_t i = 0; i < sp.hz.size(); ++i) {
        for (const auto& v : {sp.mix[i], sp.ref[i]}) {
            if (!v || !sp.valid[i]) continue;
            hi = std::max(hi, *v);
            lo = std::min(lo, *v);
        }
    }
    if (hi < -1e8) { hi = 0.0; lo = -40.0; }
    const double top = std::ceil((hi + 4.0) / 5.0) * 5.0;
    const double bottom = std::clamp(std::floor((lo - 4.0) / 5.0) * 5.0, top - 60.0, top - 30.0);
    auto yv = [&](double db) { return y0 + (top - std::clamp(db, bottom, top)) / (top - bottom) * h; };
    bandColumns(c, y0, y1, true);
    const double gridStep = top - bottom > 40.0 ? 10.0 : 5.0;
    for (double g = top - gridStep; g > bottom; g -= gridStep) {
        const int y = static_cast<int>(std::lround(yv(g)));
        c.dashedHline(X0, X1, y, kWhite, 2, 4, 0.12);
        c.text(X1 + 8, y - 9, sfmt("%.0f", g), kDim, 2);
    }
    freqGrid(c, y0, y1);
    auto curve = [&](const std::vector<std::optional<double>>& v, bool onlyValid) {
        std::vector<std::pair<double, double>> pts;
        for (std::size_t i = 0; i < sp.hz.size(); ++i)
            if (v[i] && (!onlyValid || sp.valid[i])) pts.push_back({fx(sp.hz[i]), yv(*v[i])});
        return pts;
    };
    // The reference: filled under its curve, then both lines; bands without data (band-limited
    // reference) dimmed.
    const auto refAll = smoothCurve(curve(sp.ref, false));
    for (std::size_t i = 0; i + 1 < refAll.size(); ++i) {
        const int xa = static_cast<int>(std::lround(refAll[i].first)), xb = static_cast<int>(std::lround(refAll[i + 1].first));
        for (int x = xa; x < xb; ++x) {
            const double t = xb > xa ? static_cast<double>(x - xa) / (xb - xa) : 0.0;
            const int y = static_cast<int>(std::lround(refAll[i].second + t * (refAll[i + 1].second - refAll[i].second)));
            for (int yy = std::max(y, y0); yy < y1; ++yy) c.blend(x, yy, kRefCol, 0.10 * (1.0 - 0.6 * (yy - y) / std::max(1, y1 - y)));
        }
    }
    stroke(c, refAll, kRefCol, 1.5, 0.35, y0, y1);
    stroke(c, smoothCurve(curve(sp.ref, true)), kRefCol, 3.0, 1.0, y0, y1);
    stroke(c, smoothCurve(curve(sp.mix, false)), kMixCol, 1.5, 0.35, y0, y1);
    stroke(c, smoothCurve(curve(sp.mix, true)), kMixCol, 3.0, 1.0, y0, y1);
    for (std::size_t i = 0; i < sp.hz.size(); ++i) {
        if (!sp.valid[i]) {
            const double xa = fx(sp.hz[i] * std::exp2(-1.0 / 6.0)), xb = fx(sp.hz[i] * std::exp2(1.0 / 6.0));
            c.blendRect(static_cast<int>(xa), y0 + 24, static_cast<int>(xb), y1, kBg, 0.45);
            continue;
        }
        if (sp.ref[i]) disc(c, fx(sp.hz[i]), yv(*sp.ref[i]), 3.2, kRefCol);
        if (sp.mix[i]) disc(c, fx(sp.hz[i]), yv(*sp.mix[i]), 3.2, kMixCol);
    }
    panelFrame(c, X0, y0, X1, y1);
}

void diffPanel(Canvas& c, const Spectrum& sp, const json& regions, double tol, int y0, int h) {
    const int y1 = y0 + h;
    double m = 6.0;
    for (std::size_t i = 0; i < sp.hz.size(); ++i)
        if (sp.diff[i] && sp.valid[i]) m = std::max(m, std::fabs(*sp.diff[i]) + 1.0);
    const double range = std::min(18.0, std::ceil(m / 3.0) * 3.0);
    auto yv = [&](double db) { return y0 + (range - std::clamp(db, -range, range)) / (2.0 * range) * h; };
    c.fillRect(X0, y0, X1, y1, kLane);
    const int yz = static_cast<int>(std::lround(yv(0.0)));
    c.blendRect(X0, static_cast<int>(std::lround(yv(tol))), X1, static_cast<int>(std::lround(yv(-tol))) + 1, kGreen, 0.10);
    const double step = range > 9.0 ? 6.0 : 3.0;
    for (double g = step; g < range + 1e-9; g += step)
        for (double s : {g, -g}) {
            const int y = static_cast<int>(std::lround(yv(s)));
            c.dashedHline(X0, X1, y, kWhite, 2, 4, 0.10);
            c.text(X1 + 8, y - 9, sfmt("%+.0f", s), kDim, 2);
        }
    freqGrid(c, y0, y1);
    c.hline(X0, X1, yz, kText, 0.6);
    c.text(X1 + 8, yz - 9, "0", kText, 2);
    const double third = (X1 - X0) / (3.0 * std::log2(1000.0));
    for (std::size_t i = 0; i < sp.hz.size(); ++i) {
        if (!sp.diff[i]) continue;
        const double d = *sp.diff[i];
        const int xc = static_cast<int>(std::lround(fx(sp.hz[i])));
        const int hw = std::max(3, static_cast<int>(third * 0.32));
        const int ya = static_cast<int>(std::lround(yv(d)));
        const Rgb col = d >= 0 ? kUp : kDown;
        const double a = sp.valid[i] ? std::clamp(0.35 + std::fabs(d) / 8.0, 0.35, 0.9) : 0.18;
        c.blendRect(xc - hw, std::min(ya, yz), xc + hw + 1, std::max(ya, yz) + 1, col, a);
    }
    std::vector<std::pair<double, double>> pts;
    for (std::size_t i = 0; i < sp.hz.size(); ++i)
        if (sp.smooth[i] && sp.valid[i]) pts.push_back({fx(sp.hz[i]), yv(*sp.smooth[i])});
    stroke(c, smoothCurve(pts), kWhite, 2.5, 0.95, y0, y1);
    // Regions (what the suggestions are about): a bracket at the panel edge + label.
    if (regions.is_array()) {
        int n = 0;
        for (const auto& r : regions) {
            const auto f0 = optNum(r, "fromHz"), f1 = optNum(r, "toHz"), avg = optNum(r, "avgDb");
            if (!f0 || !f1 || !avg) continue;
            const int xa = static_cast<int>(std::lround(fx(*f0))), xb = static_cast<int>(std::lround(fx(*f1)));
            const bool up = *avg > 0;
            const int yb = up ? y0 + 26 : y1 - 8;
            const Rgb col = up ? kUp : kDown;
            c.fillRect(xa, yb, xb, yb + 3, col);
            c.fillRect(xa, up ? yb : yb - 6, xa + 2, up ? yb + 9 : yb + 3, col);
            c.fillRect(xb - 2, up ? yb : yb - 6, xb, up ? yb + 9 : yb + 3, col);
            const std::string label = sfmt("%+.1f dB", *avg);
            const int lw = Canvas::textWidth(label, 2);
            const int lx = std::clamp((xa + xb) / 2 - lw / 2, X0 + 2, X1 - lw - 2);
            textBox(c, lx, up ? yb - 22 : yb - 26, label, col, 2, 0.8);
            ++n;
        }
    }
    panelFrame(c, X0, y0, X1, y1);
}

void stereoPanel(Canvas& c, const json& st, int x0, int x1, int y0, int h) {
    const int y1 = y0 + h;
    const auto hz = numList(st, "octaveHz", false);
    const auto wm = numList(st, "mixWidthPct", false), wr = numList(st, "refWidthPct", false);
    const auto cm = numList(st, "mixCorrelation", false), cr = numList(st, "refCorrelation", false);
    c.fillRect(x0, y0, x1, y1, kLane);
    constexpr double kTop = 150.0;
    auto yv = [&](double pct) { return y0 + (kTop - std::clamp(pct, 0.0, kTop)) / kTop * h; };
    for (double g : {25.0, 50.0, 100.0, 150.0}) {
        const int y = static_cast<int>(std::lround(yv(g)));
        c.dashedHline(x0, x1, y, kWhite, 2, 4, g == 100.0 ? 0.25 : 0.10);
        c.text(x1 + 6, y - 9, sfmt("%.0f%%", g), kDim, 2);
    }
    const std::size_t n = hz.size();
    if (n == 0) {
        c.text(x0 + 8, y0 + 8, "no stereo data", kDim, 2);
        panelFrame(c, x0, y0, x1, y1);
        return;
    }
    const double gw = static_cast<double>(x1 - x0) / static_cast<double>(n);
    for (std::size_t i = 0; i < n; ++i) {
        const int gx = x0 + static_cast<int>(std::lround(gw * static_cast<double>(i)));
        const int bw = std::max(4, static_cast<int>(gw * 0.3));
        auto bar = [&](const std::optional<double>& v, int bx, Rgb col, int row) {
            if (!v) return;
            const int yt = static_cast<int>(std::lround(yv(*v)));
            c.blendRect(bx, yt, bx + bw, y1, col, 0.75);
            if (*v > kTop) textBox(c, gx + 4, y0 + 4 + row * 22, sfmt("%.0f", *v), col, 2, 0.85);
        };
        bar(i < wr.size() ? wr[i] : std::nullopt, gx + static_cast<int>(gw * 0.18), kRefCol, 1);
        bar(i < wm.size() ? wm[i] : std::nullopt, gx + static_cast<int>(gw * 0.18) + bw + 2, kMixCol, 0);
        const double f = hz[i].value_or(0.0);
        const std::string label = f >= 1000 ? sfmt("%.0fk", f / 1000.0) : sfmt("%.0f", f);
        c.text(gx + static_cast<int>(gw / 2) - Canvas::textWidth(label, 2) / 2, y1 + 6, label, kDim, 2);
        auto corr = [&](const std::optional<double>& v, int y, Rgb col) {
            if (!v) return;
            std::string s = *v >= 0.995 ? std::string("1.0") : sfmt("%.2f", *v);
            if (s.rfind("0.", 0) == 0) s.erase(0, 1);          // .58
            else if (s.rfind("-0.", 0) == 0) s.erase(1, 1);    // -.62
            c.text(gx + static_cast<int>(gw / 2) - Canvas::textWidth(s, 2) / 2, y, s, *v < 0.0 ? kRed : col, 2);
        };
        corr(i < cm.size() ? cm[i] : std::nullopt, y1 + 30, kMixCol);
        corr(i < cr.size() ? cr[i] : std::nullopt, y1 + 52, kRefCol);
    }
    c.text(8, y1 + 30, "corr mix", kMixCol, 2);
    c.text(8, y1 + 52, "corr ref", kRefCol, 2);
    panelFrame(c, x0, y0, x1, y1);
}

void dynamicsPanel(Canvas& c, const json& dyn, int x0, int x1, int y0, int h) {
    const int y1 = y0 + h;
    c.fillRect(x0, y0, x1, y1, kLane);
    const json& hist = need(dyn, "histogram");
    const double from = optNum(hist, "fromLu").value_or(-30.0), step = optNum(hist, "stepLu").value_or(1.0);
    const auto hm = numList(hist, "mixPct", false), hr = numList(hist, "refPct", false);
    // Range: the occupied bins of both (at least -8..+4 LU, at most -24..+8).
    double occLo = 0.0, occHi = 0.0;
    for (const auto* v : {&hm, &hr})
        for (std::size_t i = 0; i < v->size(); ++i)
            if ((*v)[i].value_or(0.0) >= 0.2) {
                occLo = std::min(occLo, from + step * static_cast<double>(i));
                occHi = std::max(occHi, from + step * static_cast<double>(i + 1));
            }
    const double kLo = std::clamp(std::floor((occLo - 2.0) / 4.0) * 4.0, -24.0, -8.0);
    const double kHi = std::clamp(std::ceil((occHi + 1.0) / 2.0) * 2.0, 4.0, 8.0);
    auto xv = [&](double lu) { return x0 + (std::clamp(lu, kLo, kHi) - kLo) / (kHi - kLo) * (x1 - x0); };
    double top = 5.0;
    for (const auto& v : hm) top = std::max(top, v.value_or(0.0));
    for (const auto& v : hr) top = std::max(top, v.value_or(0.0));
    top *= 1.12;
    auto yv = [&](double pct) { return y1 - std::clamp(pct / top, 0.0, 1.0) * (h - 4); };
    const double tick = kHi - kLo > 20.0 ? 4.0 : 2.0;
    for (double lu = std::ceil(kLo / tick) * tick; lu <= kHi + 1e-9; lu += tick) {
        const int x = static_cast<int>(std::lround(xv(lu)));
        c.dashedVline(x, y0, y1, kWhite, 1, 3, std::fabs(lu) < 1e-9 ? 0.35 : 0.10);
        const std::string s = std::fabs(lu) < 1e-9 ? std::string("0") : sfmt("%+.0f", lu);
        c.text(x - Canvas::textWidth(s, 2) / 2, y1 + 6, s, kDim, 2);
    }
    auto hist1 = [&](const std::vector<std::optional<double>>& v, Rgb col, double fillA) {
        std::vector<std::pair<double, double>> outline;
        for (std::size_t i = 0; i < v.size(); ++i) {
            const double a = from + step * static_cast<double>(i), b = a + step;
            if (b <= kLo || a >= kHi) continue;
            const double xa = xv(a), xb = xv(b), y = yv(v[i].value_or(0.0));
            c.blendRect(static_cast<int>(std::lround(xa)), static_cast<int>(std::lround(y)), static_cast<int>(std::lround(xb)), y1, col, fillA);
            outline.push_back({xa, y});
            outline.push_back({xb, y});
        }
        stroke(c, outline, col, 2.0, 0.95, y0, y1);
    };
    hist1(hr, kRefCol, 0.22);
    hist1(hm, kMixCol, 0.22);
    // p10..p95 of each as a bracket on top (the body of the distribution), numbers under the axis.
    auto span = [&](const json& p, Rgb col, int row, const char* who) {
        const auto a = optNum(p, "p10"), b = optNum(p, "p95");
        if (!a || !b) return;
        const int xa = static_cast<int>(std::lround(xv(*a))), xb = static_cast<int>(std::lround(xv(*b)));
        const int y = y0 + 8 + row * 12;
        c.fillRect(xa, y, std::max(xa + 2, xb), y + 3, col);
        c.fillRect(xa, y - 3, xa + 2, y + 6, col);
        c.fillRect(std::max(xa + 2, xb) - 2, y - 3, std::max(xa + 2, xb), y + 6, col);
        c.text(x0, y1 + 30 + row * 22, sfmt("%s: 85%% of the time in %+.1f..%+.1f LU", who, *a, *b), col, 2);
    };
    if (dyn.contains("mix")) span(dyn.at("mix"), kMixCol, 0, "mix");
    if (dyn.contains("ref")) span(dyn.at("ref"), kRefCol, 1, "ref");
    c.text(x1 + 6, y1 - 20, "LU", kDim, 2);
    panelFrame(c, x0, y0, x1, y1);
}

}  // namespace

void renderComparePng(const json& cmp, const std::string& path) {
    if (!cmp.is_object() || str(cmp, "format") != "agentsound.compare") bad("not an agentsound.compare document");
    const Spectrum sp = readSpectrum(cmp);
    const json& mixInfo = need(cmp, "mix");
    const json& refInfo = need(cmp, "reference");
    const json& lm = need(cmp, "loudnessMatch");
    const json& metrics = need(cmp, "metrics");
    const json& sugg = need(cmp, "suggestions");
    if (!metrics.is_array() || !sugg.is_array()) bad("'metrics' and 'suggestions' must be arrays");
    const double tol = optNum(need(cmp, "spectrum"), "toleranceDb").value_or(1.5);

    // Suggestions (wrapped) decide the height.
    constexpr int kIndent = 8 + 12 * 12;
    std::vector<std::pair<std::string, std::vector<std::string>>> sugLines;
    int nSugLines = 0;
    for (const auto& s : sugg) {
        if (sugLines.size() >= 9) break;
        auto lines = wrapText(str(s, "text"), W - 8 - kIndent, 2, 3);
        nSugLines += static_cast<int>(lines.size());
        sugLines.push_back({str(s, "area", "?"), std::move(lines)});
    }
    std::vector<std::string> notes;
    if (cmp.contains("notes") && cmp.at("notes").is_array()) {
        for (const auto& n : cmp.at("notes"))
            if (n.is_string()) notes.push_back(n.get<std::string>());
    } else if (!str(cmp, "excerptNote").empty()) {
        notes.push_back(str(cmp, "excerptNote"));
    }
    std::vector<std::string> noteLines;
    for (const auto& n : notes)
        for (auto& l : wrapText("NOTE: " + n, W - 16, 2, 2)) noteLines.push_back(std::move(l));
    // The summary wraps onto a second line rather than losing its tail (crest, width).
    const std::vector<std::string> summaryLines = wrapText(str(cmp, "summary"), W - 16, 2, 2);
    const int extraSummary = std::max(0, static_cast<int>(summaryLines.size()) - 1);
    const int ySpec = 96 + (static_cast<int>(noteLines.size()) + extraSummary) * kLine, hSpec = 300;
    const int yDiff = ySpec + hSpec + 44, hDiff = 210;
    const int yStereo = yDiff + hDiff + 76, hStereo = 200;
    const int yMetrics = yStereo + hStereo + 82;
    const int metricRows = static_cast<int>((metrics.size() + 1) / 2);
    const int ySug = yMetrics + 30 + metricRows * kLine + 16;
    const int H = ySug + 30 + (sugLines.empty() ? kLine : nSugLines * kLine + static_cast<int>(sugLines.size()) * 6) + 12;
    Canvas c(W, H, kBg);

    // Title, loudness match, summary, notes.
    const std::string mixLabel = str(mixInfo, "label", "mix"), refLabel = str(refInfo, "label", "reference");
    int x = 8 + c.text(8, kTitleY, "COMPARE", kText, 2) + 16;
    x += c.text(x, kTitleY, fitText(mixLabel, 620, 2), kMixCol, 2) + 12;
    x += c.text(x, kTitleY, "vs", kDim, 2) + 12;
    c.text(x, kTitleY, fitText(refLabel, W - x - 8, 2), kRefCol, 2);
    const auto ml = optNum(lm, "mixLufs"), rl = optNum(lm, "refLufs"), off = optNum(lm, "offsetDb");
    std::string match = "LOUDNESS-MATCHED";
    if (ml && rl && off)
        match += sfmt(": mix %.1f LUFS, reference %.1f LUFS -> spectra relative to each file's loudness (mix %+.1f dB)", *ml, *rl, *off);
    c.text(8, kTitleY + kLine + 2, fitText(match, W - 16, 2), kText, 2);
    for (std::size_t i = 0; i < summaryLines.size(); ++i)
        c.text(8, kTitleY + (2 + static_cast<int>(i)) * kLine + 4, summaryLines[i], kDim, 2);
    for (std::size_t i = 0; i < noteLines.size(); ++i)
        c.text(8, kTitleY + (3 + extraSummary + static_cast<int>(i)) * kLine + 6, noteLines[i], kAmber, 2);

    // SPECTRUM.
    caption(c, 8, ySpec + 4, {{"SPECTRUM", kText}, {"1/3 octave", kDim}, {"dB re LUFS-I", kDim}});
    c.text(8, ySpec + 4 + 4 * kLine, "mix", kMixCol, 2);
    c.text(8, ySpec + 4 + 5 * kLine, "reference", kRefCol, 2);
    spectrumPanel(c, sp, ySpec, hSpec);
    freqAxis(c, ySpec + hSpec + 2);

    // DIFFERENCE.
    caption(c, 8, yDiff + 4, {{"DIFFERENCE", kText}, {"mix - ref, dB", kDim}, {"red: mix more", kUp}, {"blue: mix less", kDown},
                              {"bars 1/3 oct", kDim}, {"line ~1 oct", kDim}});
    c.text(8, yDiff + 4 + 6 * kLine, sfmt("tol +-%.1f dB", tol), kGreen, 2);
    const json& spj = need(cmp, "spectrum");
    diffPanel(c, sp, spj.contains("regions") ? spj.at("regions") : json::array(), tol, yDiff, hDiff);
    freqAxis(c, yDiff + hDiff + 2);

    // STEREO (left) and DYNAMICS (right).
    const int sx1 = 780, dx0 = 1010;
    caption(c, 8, yStereo + 4, {{"STEREO WIDTH", kText}, {"side/mid %", kDim}, {"per octave", kDim}});
    c.text(8, yStereo + 4 + 4 * kLine, "mix", kMixCol, 2);
    c.text(8, yStereo + 4 + 5 * kLine, "reference", kRefCol, 2);
    if (cmp.contains("stereo")) stereoPanel(c, cmp.at("stereo"), X0, sx1, yStereo, hStereo);
    c.text(850, yStereo + 4, "DYNAMICS", kText, 2);
    c.text(850, yStereo + 4 + kLine, "short-term", kDim, 2);
    c.text(850, yStereo + 4 + 2 * kLine, "loudness", kDim, 2);
    c.text(850, yStereo + 4 + 3 * kLine, "re LUFS-I", kDim, 2);
    c.text(850, yStereo + 4 + 4 * kLine, "% of time", kDim, 2);
    if (cmp.contains("dynamics")) dynamicsPanel(c, cmp.at("dynamics"), dx0, X1, yStereo, hStereo);

    // METRICS: two columns.
    c.hline(8, W - 8, yMetrics - 8, kGrid);
    c.text(8, yMetrics, "METRICS", kText, 2);
    const int colW = (W - 16) / 2;
    auto header = [&](int cx) {
        c.text(cx + 372, yMetrics, "mix", kMixCol, 2);
        c.text(cx + 480, yMetrics, "ref", kRefCol, 2);
        c.text(cx + 588, yMetrics, "diff", kDim, 2);
    };
    header(8);
    header(8 + colW);
    for (std::size_t i = 0; i < metrics.size(); ++i) {
        const json& m = metrics[i];
        const int cx = 8 + (i < static_cast<std::size_t>(metricRows) ? 0 : colW);
        const int y = yMetrics + 30 + static_cast<int>(i % static_cast<std::size_t>(metricRows)) * kLine;
        const auto mv = optNum(m, "mix"), rv = optNum(m, "ref"), dv = optNum(m, "diff");
        std::string fmt = str(m, "fmt", "{:.1f}");
        const bool two = fmt.find(".2f") != std::string::npos, zero = fmt.find(".0f") != std::string::npos;
        auto num = [&](const std::optional<double>& v, bool sign) {
            if (!v) return std::string("n/a");
            return sfmt(sign ? (two ? "%+.2f" : zero ? "%+.0f" : "%+.1f") : (two ? "%.2f" : zero ? "%.0f" : "%.1f"), *v);
        };
        const std::string unit = str(m, "unit");
        const std::string note = str(m, "note");
        c.text(cx, y, fitText(str(m, "label") + (unit.empty() ? "" : " (" + unit + ")"), 360, 2), note.empty() ? kText : kDim, 2);
        c.text(cx + 372, y, num(mv, false), note.empty() ? kMixCol : kDim, 2);
        c.text(cx + 480, y, num(rv, false), note.empty() ? kRefCol : kDim, 2);
        const bool flag = m.contains("flag") && m.at("flag").is_boolean() && m.at("flag").get<bool>();
        if (!note.empty()) c.text(cx + 588, y, fitText(note, colW - 600, 2), kDim, 2);
        else c.text(cx + 588, y, dv ? num(dv, true) : std::string(""), flag ? kAmber : kText, 2);
    }

    // SUGGESTIONS.
    c.hline(8, W - 8, ySug - 8, kGrid);
    c.text(8, ySug, sfmt("SUGGESTIONS (%d, most important first; compare.json has the render-format fixes)", static_cast<int>(sugg.size())),
           kText, 2);
    int y = ySug + 30;
    if (sugLines.empty()) c.text(8, y, "none: the mix matches the reference within the tolerances", kGreen, 2);
    for (std::size_t i = 0; i < sugLines.size(); ++i) {
        const auto& [area, lines] = sugLines[i];
        const Rgb col = area == "tone" ? kCyan : area == "loudness" ? kGreen : area == "stereo" ? rgbHex(0xc792ea)
                        : area == "space" ? rgbHex(0x7fdbca) : kAmber;
        c.text(8, y, sfmt("%d.", static_cast<int>(i) + 1), kText, 2);
        c.text(8 + 36, y, fitText(area, 100, 2), col, 2);
        for (const auto& line : lines) {
            c.text(kIndent, y, line, kText, 2);
            y += kLine;
        }
        y += 6;
    }
    writePng(path, c.image());
}

}  // namespace as::analysis
