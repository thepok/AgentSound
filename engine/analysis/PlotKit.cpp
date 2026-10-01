#include "analysis/PlotKit.h"

#include "analysis/Fft.h"
#include "analysis/Loudness.h"
#include "analysis/MixImpl.h"

#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <cstdio>

namespace as::analysis {

// ------------------------------------------------------------------ text

std::string sfmt(const char* f, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, f);
    std::vsnprintf(buf, sizeof buf, f, ap);
    va_end(ap);
    return buf;
}

std::string mmss(double sec) {
    const int s = static_cast<int>(std::lround(std::max(0.0, sec)));
    return sfmt("%d:%02d", s / 60, s % 60);
}

std::string mmssMs(double sec) {
    const auto ms = static_cast<long long>(std::llround(std::max(0.0, sec) * 1000.0));
    return sfmt("%lld:%02lld.%03lld", ms / 60000, (ms / 1000) % 60, ms % 1000);
}

std::string fitText(const std::string& s, int maxPx, int scale) {
    if (Canvas::textWidth(s, scale) <= maxPx) return s;
    std::string t = s;
    while (!t.empty() && Canvas::textWidth(t + "~", scale) > maxPx) t.pop_back();
    return t.empty() ? t : t + "~";
}

std::vector<std::string> wrapText(const std::string& s, int maxPx, int scale, int maxLines) {
    std::vector<std::string> lines;
    std::string cur;
    std::size_t i = 0;
    while (i < s.size()) {
        const std::size_t sp = s.find(' ', i);
        const std::string word = s.substr(i, sp == std::string::npos ? std::string::npos : sp - i);
        i = sp == std::string::npos ? s.size() : sp + 1;
        const std::string cand = cur.empty() ? word : cur + " " + word;
        if (Canvas::textWidth(cand, scale) <= maxPx || cur.empty()) { cur = cand; continue; }
        lines.push_back(cur);
        cur = word;
        if (static_cast<int>(lines.size()) >= maxLines - 1) {  // last line takes the rest
            cur += i < s.size() ? " " + s.substr(i) : std::string();
            break;
        }
    }
    if (!cur.empty()) lines.push_back(cur);
    for (auto& l : lines) l = fitText(l, maxPx, scale);
    return lines;
}

void textBox(Canvas& c, int x, int y, const std::string& s, Rgb fg, int scale, double alpha) {
    const int w = Canvas::textWidth(s, scale);
    c.blendRect(x - 3, y - 2, x + w + 3, y + 9 * scale + 1, kBg, alpha);
    c.text(x, y, s, fg, scale);
}

double niceStep(double minStep, std::initializer_list<double> steps) {
    for (double s : steps)
        if (s >= minStep) return s;
    return *(steps.end() - 1);
}

// ------------------------------------------------------------------ time frame

int TimeMap::xi(double sec) const { return static_cast<int>(std::lround(x(sec))); }

namespace {
int barStep(const MixImpl& m, const TimeMap& tm, double minPx) {
    // average bar length in the view (bars differ with a tempo map or meter changes)
    const double b0 = m.barAt(m.beatAt(tm.t0)), b1 = m.barAt(m.beatAt(tm.t0 + tm.dur));
    const double barSec = (m.mapped || m.metered) && b1 > b0 ? tm.dur / (b1 - b0) : 240.0 / m.bpm;
    const double pxPerBar = barSec / tm.dur * tm.width();
    return static_cast<int>(niceStep(minPx / std::max(pxPerBar, 1e-9), {1, 2, 4, 8, 16, 32, 64, 128, 256, 512}));
}
}  // namespace

void drawTimeHeader(Canvas& c, const MixImpl& m, const TimeMap& tm, int ySec, int yBar, bool beats) {
    const double tEnd = tm.t0 + tm.dur;
    c.fillRect(tm.x0, ySec, tm.x1, ySec + 22, kPanel);
    for (std::size_t i = 0; i < m.sections.size(); ++i) {
        const auto& s = m.sections[i];
        if (s.endSec <= tm.t0 || s.startSec >= tEnd) continue;
        const int xa = std::clamp(tm.xi(s.startSec), tm.x0, tm.x1);
        const int xb = std::clamp(tm.xi(s.endSec), tm.x0, tm.x1);
        if (xb <= xa) continue;
        c.fillRect(xa, ySec, xb, ySec + 22, i % 2 ? kHeaderB : kHeaderA);
        c.vline(xa, ySec, ySec + 21, kWhite, 0.7);
        const std::string lufs = s.lufs > -70.0 ? sfmt("%.1f", s.lufs) : std::string("silent");
        const int room = xb - xa - 6;
        const int x = c.text(xa + 4, ySec + 3, fitText(s.name, room, 2), kText, 2) + xa + 4;
        if (Canvas::textWidth(s.name, 2) + 8 + Canvas::textWidth(lufs, 2) <= room) c.text(x + 8, ySec + 3, lufs, kAmber, 2);
    }
    // Bars (song numbering), labels >= 44 px apart.
    const int step = barStep(m, tm, 44.0);
    c.text(tm.x0 - Canvas::textWidth("bar", 2) - 8, yBar, "bar", kDim, 2);
    const double firstBar = std::floor(m.barAt(m.beatAt(tm.t0)));
    const double lastBar = std::ceil(m.barAt(m.beatAt(tEnd)));
    for (double b = firstBar; b <= lastBar; b += 1.0) {
        const double sec = m.secAtBeat(m.barStartBeat(b));
        if (sec < tm.t0 - 1e-6 || sec > tEnd + 1e-6) continue;
        const int x = tm.xi(sec);
        const int bar = static_cast<int>(b) + 1;
        if (beats) {
            const double bb = m.barStartBeat(b), bpb = m.barStartBeat(b + 1.0) - bb;
            for (int k = 1; k < bpb - 1e-9; ++k) {
                const double bs = m.secAtBeat(bb + k);
                if (bs > tm.t0 && bs < tEnd) c.vline(tm.xi(bs), yBar + 18, yBar + 20, kDim);
            }
        }
        if ((bar - 1) % step) continue;
        c.vline(x, yBar + 16, yBar + 20, kDim);
        const std::string label = std::to_string(bar);
        if (x + Canvas::textWidth(label, 2) + 2 <= tm.x1 + 30) c.text(x + 2, yBar, label, kDim, 2);
    }
}

void drawTimeGrid(Canvas& c, const MixImpl& m, const TimeMap& tm, int yTop, int yBottom, bool beats) {
    const double tEnd = tm.t0 + tm.dur;
    const int step = barStep(m, tm, 44.0);
    for (double b = std::floor(m.barAt(m.beatAt(tm.t0))); b <= std::ceil(m.barAt(m.beatAt(tEnd))); b += 1.0) {
        if (beats) {
            const double bb = m.barStartBeat(b), bpb = m.barStartBeat(b + 1.0) - bb;
            for (int k = 1; k < bpb - 1e-9; ++k) {
                const double bs = m.secAtBeat(bb + k);
                if (bs > tm.t0 && bs < tEnd) c.dashedVline(tm.xi(bs), yTop, yBottom, kWhite, 1, 5, 0.07);
            }
        }
        if (static_cast<int>(b) % step) continue;
        const double sec = m.secAtBeat(m.barStartBeat(b));
        if (sec <= tm.t0 || sec >= tEnd) continue;
        c.dashedVline(tm.xi(sec), yTop, yBottom, kWhite, 1, 3, beats ? 0.16 : 0.10);
    }
    for (const auto& s : m.sections) {
        for (double t : {s.startSec, s.endSec}) {
            if (t <= tm.t0 || t >= tEnd) continue;
            c.dashedVline(tm.xi(t), yTop, yBottom, kWhite, 6, 3, 0.55);
        }
    }
}

void drawTimeAxis(Canvas& c, const TimeMap& tm, int y) {
    const double step = niceStep(90.0 / tm.width() * tm.dur, {0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 20, 30, 60, 120, 300, 600});
    const double first = std::ceil(tm.t0 / step - 1e-9) * step;
    for (double t = first; t <= tm.t0 + tm.dur + 1e-9; t += step) {
        const int x = tm.xi(t);
        c.vline(x, y, y + 4, kDim);
        std::string label;
        if (step < 1.0) {
            const int mm = static_cast<int>(t / 60.0 + 1e-9);
            label = sfmt(step < 0.5 ? "%d:%04.1f" : "%d:%04.1f", mm, t - 60.0 * mm);
        } else {
            label = mmss(t);
        }
        const int w = Canvas::textWidth(label, 2);
        c.text(std::clamp(x - w / 2, tm.x0 - 20, tm.x1 + 40 - w), y + 7, label, kDim, 2);
    }
}

void drawClickMarkers(Canvas& c, const MixImpl& m, const TimeMap& tm, int y, int node) {
    for (const auto& k : m.clicks) {
        if (node >= -1 && k.node != node) continue;
        if (k.sec < tm.t0 || k.sec > tm.t0 + tm.dur) continue;
        const int x = tm.xi(k.sec);
        const Rgb col = k.inMix ? kRed : kAmber;
        for (int r = 0; r < 7; ++r) c.hline(x - (6 - r) / 1, x + (6 - r) / 1, y + r, col);
    }
}

int drawTitle(Canvas& c, const std::string& head, const std::string& rest, Rgb headColor) {
    int x = 8 + c.text(8, kTitleY, head, headColor, 2);
    if (!rest.empty()) x += 12 + c.text(x + 12, kTitleY, rest, kText, 2);
    return x;
}

int drawColorLegend(Canvas& c, int x, int y, int w, const std::string& lo, const std::string& hi, const std::string& unit,
                    Rgb (*map)(double), bool diverging) {
    x += c.text(x, y, lo, kDim, 2) + 6;
    for (int i = 0; i < w; ++i) {
        const double t = i / static_cast<double>(std::max(1, w - 1));
        c.fillRect(x + i, y + 1, x + i + 1, y + 16, map(diverging ? 2.0 * t - 1.0 : t));
    }
    x += w + 6;
    x += c.text(x, y, hi, kDim, 2);
    if (!unit.empty()) x += 8 + c.text(x + 8, y, unit, kDim, 2);
    return x;
}

void panelFrame(Canvas& c, int x0, int y0, int x1, int y1) { c.rectOutline(x0 - 1, y0 - 1, x1, y1, kGrid); }

void caption(Canvas& c, int x, int y, std::initializer_list<std::pair<const char*, Rgb>> lines) {
    for (const auto& [s, col] : lines) {
        c.text(x, y, s, col, 2);
        y += kLine;
    }
}

TickSpan ticksFor(const StreamStats& s, double tickSec, double t0, double t1) {
    const auto n = s.ticks().size();
    auto i0 = static_cast<std::size_t>(std::max(0.0, std::floor(t0 / tickSec)));
    auto i1 = static_cast<std::size_t>(std::max(0.0, std::ceil(t1 / tickSec)));
    i0 = std::min(i0, n);
    i1 = std::clamp(i1, std::min(i0 + 1, n), n);
    return {i0, i1};
}

// ------------------------------------------------------------------ spectra

std::vector<float> columnSpectra(const float* L, const float* R, std::int64_t len, int n, int cols, double start,
                                 double samplesPerCol) {
    const Fft fft(n);
    const auto win = hannWindow(n);
    double w2 = 0.0;
    for (float w : win) w2 += static_cast<double>(w) * w;
    const int half = n / 2;
    std::vector<float> out(static_cast<std::size_t>(cols) * static_cast<std::size_t>(half + 1), 0.0f);
    std::vector<float> re(static_cast<std::size_t>(n)), im(static_cast<std::size_t>(n)), q(static_cast<std::size_t>(n));
    const int* rev = fft.bitReversed().data();
    const int perCol = std::max(1, static_cast<int>(std::ceil(2.0 * samplesPerCol / n - 1e-9)));
    // |XL|^2 + |XR|^2 = (|Z[k]|^2 + |Z[N-k]|^2) / 2; x2 one-sided, /2 channel average.
    const auto norm = static_cast<float>(1.0 / (static_cast<double>(n) * w2 * perCol) * 0.5);
    for (int c = 0; c < cols; ++c) {
        float* dst = &out[static_cast<std::size_t>(c) * static_cast<std::size_t>(half + 1)];
        for (int f = 0; f < perCol; ++f) {
            const auto centre = static_cast<std::int64_t>(std::floor(start + (c + (f + 0.5) / perCol) * samplesPerCol));
            const std::int64_t s0 = centre - n / 2;
            if (s0 + n <= 0 || s0 >= len) continue;
            if (s0 >= 0 && s0 + n <= len) {
                const float* pl = L + s0;
                const float* pr = R + s0;
                for (int i = 0; i < n; ++i) {
                    re[static_cast<std::size_t>(i)] = pl[i] * win[static_cast<std::size_t>(i)];
                    im[static_cast<std::size_t>(i)] = pr[i] * win[static_cast<std::size_t>(i)];
                }
            } else {
                for (int i = 0; i < n; ++i) {
                    const std::int64_t k = s0 + i;
                    const bool in = k >= 0 && k < len;
                    re[static_cast<std::size_t>(i)] = in ? L[k] * win[static_cast<std::size_t>(i)] : 0.0f;
                    im[static_cast<std::size_t>(i)] = in ? R[k] * win[static_cast<std::size_t>(i)] : 0.0f;
                }
            }
            fft.forwardDif(re.data(), im.data());
            for (int j = 0; j < n; ++j)
                q[static_cast<std::size_t>(j)] = re[static_cast<std::size_t>(j)] * re[static_cast<std::size_t>(j)] +
                                                 im[static_cast<std::size_t>(j)] * im[static_cast<std::size_t>(j)];
            dst[0] += q[static_cast<std::size_t>(rev[0])] * norm;
            dst[half] += q[static_cast<std::size_t>(rev[half])] * norm;
            for (int k = 1; k < half; ++k) dst[k] += (q[static_cast<std::size_t>(rev[k])] + q[static_cast<std::size_t>(rev[n - k])]) * norm;
        }
    }
    return out;
}

std::vector<float> decimate(const std::vector<float>& x, int factor) {
    if (factor <= 1) return x;
    const int taps = 8 * factor + 1, mid = taps / 2;
    const double fc = 0.4 / factor;  // cycles per input sample
    std::vector<float> h(static_cast<std::size_t>(taps));
    double sum = 0.0;
    auto i0 = [](double v) { double s = 1.0, t = 1.0; for (int k = 1; k < 40; ++k) { t *= (v / (2 * k)) * (v / (2 * k)); s += t; } return s; };
    for (int j = 0; j < taps; ++j) {
        const double t = j - mid, u = t / (mid + 1);
        const double sinc = t == 0 ? 2 * fc : std::sin(2 * 3.14159265358979323846 * fc * t) / (3.14159265358979323846 * t);
        h[static_cast<std::size_t>(j)] = static_cast<float>(sinc * i0(8.0 * std::sqrt(1.0 - u * u)) / i0(8.0));
        sum += h[static_cast<std::size_t>(j)];
    }
    for (float& v : h) v = static_cast<float>(v / sum);
    const auto n = static_cast<std::int64_t>(x.size());
    std::vector<float> out(static_cast<std::size_t>(n / factor));
    for (std::size_t m = 0; m < out.size(); ++m) {
        const std::int64_t base = static_cast<std::int64_t>(m) * factor - mid;
        float acc[4] = {0.0f, 0.0f, 0.0f, 0.0f};
        if (base >= 0 && base + taps <= n) {
            const float* px = x.data() + base;
            int j = 0;
            for (; j + 4 <= taps; j += 4) {
                acc[0] += h[static_cast<std::size_t>(j)] * px[j];
                acc[1] += h[static_cast<std::size_t>(j + 1)] * px[j + 1];
                acc[2] += h[static_cast<std::size_t>(j + 2)] * px[j + 2];
                acc[3] += h[static_cast<std::size_t>(j + 3)] * px[j + 3];
            }
            for (; j < taps; ++j) acc[0] += h[static_cast<std::size_t>(j)] * px[j];
        } else {
            for (int j = 0; j < taps; ++j) {
                const std::int64_t k = base + j;
                if (k >= 0 && k < n) acc[0] += h[static_cast<std::size_t>(j)] * x[static_cast<std::size_t>(k)];
            }
        }
        out[m] = acc[0] + acc[1] + acc[2] + acc[3];
    }
    return out;
}

double rowEnergy(const float* p, int half, double df, double f0, double f1) {
    if (f1 - f0 < 2.0 * df) {
        const double pos = 0.5 * (f0 + f1) / df;
        const int k = std::clamp(static_cast<int>(pos), 0, half - 1);
        const double t = std::clamp(pos - k, 0.0, 1.0);
        return (p[k] * (1.0 - t) + p[k + 1] * t) / df * (f1 - f0);
    }
    double e = 0.0;
    const int k0 = std::max(0, static_cast<int>(std::floor(f0 / df + 0.5)));
    const int k1 = std::min(half, static_cast<int>(std::floor(f1 / df + 0.5)));
    for (int k = k0; k <= k1; ++k) {
        const double ov = std::min((k + 0.5) * df, f1) - std::max((k - 0.5) * df, f0);
        if (ov > 0) e += p[k] * ov / df;
    }
    return e;
}

std::vector<float> spectrogramDb(const std::vector<SpecLayer>& layers, int cols, int rows, double t0Sec, double secPerCol,
                                 double fMin, double fMax) {
    std::vector<float> db(static_cast<std::size_t>(rows) * static_cast<std::size_t>(cols), static_cast<float>(kDbFloor));
    if (layers.empty() || cols <= 0 || rows <= 0) return db;
    std::vector<std::vector<float>> spec;
    for (const auto& ly : layers)
        spec.push_back(columnSpectra(ly.L, ly.R, ly.len, ly.n, cols, t0Sec * ly.rate, secPerCol * ly.rate));
    // Weight of each layer for a row centred at log2(f): smoothstep crossfades (half an octave)
    // at the interior layer edges.
    auto weight = [&](std::size_t li, double f) {
        const auto& ly = layers[li];
        auto ramp = [](double x) { x = std::clamp(x, 0.0, 1.0); return x * x * (3.0 - 2.0 * x); };
        const double lf = std::log2(f);
        double w = 1.0;
        if (li > 0) w *= ramp((lf - std::log2(ly.fLo)) / 0.5 + 0.5);
        if (li + 1 < layers.size()) w *= 1.0 - ramp((lf - std::log2(ly.fHi)) / 0.5 + 0.5);
        return w;
    };
    for (int r = 0; r < rows; ++r) {
        const double fTop = fMax * std::pow(fMin / fMax, static_cast<double>(r) / rows);
        const double fBot = fMax * std::pow(fMin / fMax, static_cast<double>(r + 1) / rows);
        const double fc = std::sqrt(fTop * fBot);
        double ws[8] = {};
        double wsum = 0.0;
        for (std::size_t li = 0; li < layers.size() && li < 8; ++li) wsum += ws[li] = weight(li, fc);
        for (int col = 0; col < cols; ++col) {
            double e = 0.0;
            for (std::size_t li = 0; li < layers.size() && li < 8; ++li) {
                if (ws[li] <= 0.0) continue;
                const auto& ly = layers[li];
                const int half = ly.n / 2;
                const double top = std::min(fTop, ly.rate * 0.5);
                if (fBot >= top) continue;
                e += ws[li] / wsum * rowEnergy(&spec[li][static_cast<std::size_t>(col) * static_cast<std::size_t>(half + 1)], half,
                                               ly.rate / ly.n, fBot, top);
            }
            db[static_cast<std::size_t>(r) * static_cast<std::size_t>(cols) + static_cast<std::size_t>(col)] = static_cast<float>(dbFromPower(e));
        }
    }
    return db;
}

}  // namespace as::analysis
