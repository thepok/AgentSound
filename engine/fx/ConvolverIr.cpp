#include "fx/ConvolverIr.h"

#include "core/Params.h"
#include "io/WavReader.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <limits>
#include <map>
#include <memory>
#include <mutex>
#include <sstream>

namespace as::conv {

namespace {

namespace fs = std::filesystem;

constexpr double kPi = 3.14159265358979323846;
constexpr int kZeros = 48;       // sinc zero crossings per side
constexpr int kTable = 512;      // kernel table points per zero crossing (linear interpolation: < -140 dB)
constexpr double kBeta = 10.0;   // Kaiser window (side lobes ~ -100 dB)
constexpr double kCut = 0.96;    // cutoff re the lower of the two Nyquist frequencies
constexpr double kSilent = 1e-6; // trailing samples below this x peak (-120 dB) are dropped

std::string fmtNum(double v) {
    std::ostringstream s;
    s << v;
    return s.str();
}

double besselI0(double x) {
    double sum = 1.0, term = 1.0;
    for (int k = 1; k < 200; ++k) {
        const double h = x / (2.0 * k);
        term *= h * h;
        sum += term;
        if (term < 1e-17 * sum) break;
    }
    return sum;
}

// sinc(u) * kaiser(u / kZeros) at u = j / kTable zero crossings.
const std::vector<double>& kernel() {
    static const std::vector<double> t = [] {
        std::vector<double> v(static_cast<std::size_t>(kZeros * kTable + 2), 0.0);
        const double i0 = besselI0(kBeta);
        for (std::size_t j = 0; j < v.size(); ++j) {
            const double u = static_cast<double>(j) / kTable;
            if (u >= kZeros) break;
            const double s = u == 0.0 ? 1.0 : std::sin(kPi * u) / (kPi * u);
            const double r = u / kZeros;
            v[j] = s * besselI0(kBeta * std::sqrt(std::max(0.0, 1.0 - r * r))) / i0;
        }
        return v;
    }();
    return t;
}

// The raw files, read once per process (a song may use one IR on several buses; tests build hundreds).
std::shared_ptr<const WavChannels> readCached(const std::string& path) {
    static std::mutex mu;
    static std::map<std::string, std::shared_ptr<const WavChannels>> cache;
    std::error_code ec;
    std::string key = fs::weakly_canonical(fs::path(path), ec).string();
    if (ec || key.empty()) key = path;
    const std::string file = key;
    // a file rewritten in the meantime (same path, new content) is read again
    std::error_code se, te;
    const auto size = fs::file_size(fs::path(file), se);
    const auto time = fs::last_write_time(fs::path(file), te);
    key += '|' + std::to_string(se ? 0 : size) + '|' + std::to_string(te ? 0 : time.time_since_epoch().count());
    std::lock_guard<std::mutex> lock(mu);
    if (const auto it = cache.find(key); it != cache.end()) return it->second;
    auto wav = std::make_shared<const WavChannels>(readWavChannels(file));
    cache.emplace(key, wav);
    return wav;
}

// "samples/<pack>/..." (relative, or inside an absolute path): the pack id when that pack is not installed
// (no <pack>/SOURCE.json next to the path), else "".
std::string missingPack(const std::string& resolved) {
    const std::string p = fs::path(resolved).generic_string();
    std::size_t at = std::string::npos;
    for (std::size_t i = p.find("samples/"); i != std::string::npos; i = p.find("samples/", i + 1))
        if (i == 0 || p[i - 1] == '/') at = i;
    if (at == std::string::npos) return "";
    const std::size_t idStart = at + 8, idEnd = p.find('/', idStart);
    if (idEnd == std::string::npos || idEnd == idStart) return "";
    std::error_code ec;
    if (fs::is_regular_file(fs::path(p.substr(0, idEnd)) / "SOURCE.json", ec)) return "";
    return p.substr(idStart, idEnd - idStart);
}

// Where the IR (its first `frames` samples) has faded for good: its level in 10 ms blocks stays more than 80 dB
// under the loudest block from there on (noise floors and slow residues of the recording: many IR files keep
// seconds of them; a reverb has long become inaudible 60 dB down). Returns 20 ms after the last louder block,
// or `frames` (also for IRs under 0.5 s, kept as they are).
std::int64_t noiseFloorEnd(const std::vector<std::vector<float>>& ch, std::int64_t frames, double rate) {
    const auto B = std::max<std::int64_t>(1, std::llround(0.01 * rate));
    const std::int64_t nb = frames / B;
    if (nb < 50) return frames;
    std::vector<double> level(static_cast<std::size_t>(nb), 0.0);  // mean square
    for (std::int64_t b = 0; b < nb; ++b) {
        double e = 0.0;
        for (const auto& c : ch)
            for (std::int64_t i = b * B; i < (b + 1) * B; ++i) e += static_cast<double>(c[static_cast<std::size_t>(i)]) * c[static_cast<std::size_t>(i)];
        level[static_cast<std::size_t>(b)] = e;
    }
    const double floor = *std::max_element(level.begin(), level.end()) * 1e-8;  // -80 dB
    std::int64_t last = nb - 1;
    while (last > 0 && level[static_cast<std::size_t>(last)] <= floor) --last;
    return std::min(frames, (last + 1) * B + std::llround(0.02 * rate));
}

}  // namespace

std::string resolveIrPath(const std::string& assetDir, const std::string& path) {
    const fs::path p(path);
    return p.is_absolute() ? p.string() : (fs::path(assetDir) / p).string();
}

int resampleDelay(double ratio) {
    const double half = kZeros / (kCut * std::min(1.0, ratio));  // kernel half width in input samples
    return static_cast<int>(std::ceil(half * ratio - 1e-9));
}

std::vector<float> resample(const std::vector<float>& x, double ratio) {
    const auto& table = kernel();
    const auto n = static_cast<std::int64_t>(x.size());
    const double fc = kCut * std::min(1.0, ratio);  // cutoff in units of the input Nyquist
    const double half = kZeros / fc;                // kernel half width in input samples
    const int delay = resampleDelay(ratio);
    // output sample m sits at input time (m - delay) / ratio: the kernel's whole support, pre-ringing included
    const auto outN = static_cast<std::int64_t>(std::ceil((static_cast<double>(n - 1) + half) * ratio - 1e-9)) + delay + 1;
    std::vector<float> y(static_cast<std::size_t>(outN), 0.0f);

    // A rational step 1 / ratio = q / p with few phases (44.1 -> 48 kHz: 147 / 160, 96 -> 48 kHz: 2 / 1): the
    // kernel values repeat every p outputs, so they are computed exactly once per phase (polyphase FIR).
    int p = 0;
    std::int64_t q = 0;
    for (int pp = 1; pp <= 4096 && p == 0; ++pp) {
        const double qq = pp / ratio;
        if (std::fabs(qq - std::round(qq)) < 1e-9 * qq) {
            p = pp;
            q = std::llround(qq);
        }
    }
    if (p > 0) {
        const auto K = static_cast<std::int64_t>(std::ceil(half)) + 1;  // taps j in [-K, K]: input n0 - j
        const auto width = static_cast<std::size_t>(2 * K + 1);
        const double i0 = besselI0(kBeta);
        std::vector<double> w(static_cast<std::size_t>(p) * width, 0.0);
        for (int r = 0; r < p; ++r)
            for (std::int64_t j = -K; j <= K; ++j) {
                const double off = static_cast<double>(r) / p + static_cast<double>(j);  // t - input index
                const double u = std::fabs(off) * fc;                                    // zero crossings
                if (u >= kZeros) continue;
                const double s = u == 0.0 ? 1.0 : std::sin(kPi * u) / (kPi * u);
                const double z = u / kZeros;
                w[static_cast<std::size_t>(r) * width + static_cast<std::size_t>(j + K)] =
                    fc * s * besselI0(kBeta * std::sqrt(std::max(0.0, 1.0 - z * z))) / i0;
            }
        for (std::int64_t m = 0; m < outN; ++m) {
            const std::int64_t num = (m - delay) * q;  // input time t = num / p = n0 + r / p
            std::int64_t n0 = num / p;
            if (num % p != 0 && num < 0) --n0;
            const auto r = static_cast<std::size_t>(num - n0 * p);
            const double* wr = w.data() + r * width;
            double acc = 0.0;
            const std::int64_t jlo = std::max<std::int64_t>(-K, n0 - (n - 1)), jhi = std::min<std::int64_t>(K, n0);
            for (std::int64_t j = jlo; j <= jhi; ++j)
                acc += static_cast<double>(x[static_cast<std::size_t>(n0 - j)]) * wr[j + K];
            y[static_cast<std::size_t>(m)] = static_cast<float>(acc);
        }
        return y;
    }

    // Any other ratio (a free 'stretch'): the kernel from the table, linearly interpolated (< -140 dB).
    const double scale = fc * kTable;
    const auto last = static_cast<std::int64_t>(table.size()) - 2;
    for (std::int64_t m = 0; m < outN; ++m) {
        const double t = static_cast<double>(m - delay) / ratio;
        const std::int64_t lo = std::max<std::int64_t>(0, static_cast<std::int64_t>(std::ceil(t - half)));
        const std::int64_t hi = std::min<std::int64_t>(n - 1, static_cast<std::int64_t>(std::floor(t + half)));
        double acc = 0.0;
        for (std::int64_t i = lo; i <= hi; ++i) {
            const double u = std::fabs(t - static_cast<double>(i)) * scale;
            const auto j = static_cast<std::int64_t>(u);
            if (j > last) continue;
            const double f = u - static_cast<double>(j);
            const double g = table[static_cast<std::size_t>(j)] + f * (table[static_cast<std::size_t>(j + 1)] - table[static_cast<std::size_t>(j)]);
            acc += static_cast<double>(x[static_cast<std::size_t>(i)]) * g;
        }
        y[static_cast<std::size_t>(m)] = static_cast<float>(acc * fc);
    }
    return y;
}

Ir prepareIr(std::vector<std::vector<float>> ch, double fileRate, const IrOptions& o, const std::string& where) {
    auto fail = [&](const std::string& what) { return ConfigError(where + " " + what); };
    const int nch = static_cast<int>(ch.size());
    if (nch != 1 && nch != 2 && nch != 4) {
        throw fail("has " + std::to_string(nch) + " channels; use mono (1), stereo (2: L->L, R->R) or true stereo "
                   "(4: LL, LR, RL, RR = left in -> left out, left -> right, right -> left, right -> right)");
    }
    auto frames = static_cast<std::int64_t>(ch[0].size());
    if (frames < 1) throw fail("has no audio frames");
    if (!(fileRate >= 1000.0)) throw fail("has an unusable sample rate");
    const double fileMs = 1000.0 * static_cast<double>(frames) / fileRate;

    // start: skip the head of the file
    const auto s0 = static_cast<std::int64_t>(std::llround(o.startMs * fileRate / 1000.0));
    if (s0 >= frames)
        throw fail("is " + fmtNum(std::round(fileMs * 10.0) / 10.0) + " ms long: 'start' = " + fmtNum(o.startMs) + " ms skips all of it");
    if (s0 > 0)
        for (auto& c : ch) c.erase(c.begin(), c.begin() + s0);
    frames -= s0;

    // trailing silence (digital zeros, dither below -120 dB re the peak) carries nothing
    float peak = 0.0f;
    for (const auto& c : ch)
        for (const float v : c) {
            if (!std::isfinite(v)) throw fail("contains NaN or infinite samples (a broken float WAV)");
            peak = std::max(peak, std::fabs(v));
        }
    if (!(peak > 0.0f)) throw fail(s0 > 0 ? "is silent after 'start'" : "is silent");
    std::int64_t end = 1;
    for (const auto& c : ch)
        for (std::int64_t i = frames - 1; i >= end; --i)
            if (std::fabs(c[static_cast<std::size_t>(i)]) > kSilent * peak) {
                end = i + 1;
                break;
            }
    frames = end;

    // neither does the tail once the IR has fallen 80 dB under its loudest 10 ms (noise floors and slow
    // residues of the recording: many IR files keep seconds of them)
    if (const std::int64_t cut = noiseFloorEnd(ch, frames, fileRate); cut < frames) {
        const auto fade = std::min<std::int64_t>(cut / 2, std::llround(0.02 * fileRate));
        frames = cut;
        for (auto& c : ch)
            for (std::int64_t i = 0; i < fade; ++i)
                c[static_cast<std::size_t>(frames - fade + i)] *=
                    static_cast<float>(0.5 * (1.0 + std::cos(kPi * static_cast<double>(i + 1) / static_cast<double>(fade))));
    }

    // length: truncate with a raised-cosine fade over the last quarter (at most 0.5 s)
    if (o.lengthSec > 0.0) {
        const auto keep = std::max<std::int64_t>(1, std::llround(o.lengthSec * fileRate));
        if (keep < frames) {
            frames = keep;
            const auto fade = std::max<std::int64_t>(1, std::min<std::int64_t>(keep / 4, std::llround(0.5 * fileRate)));
            for (auto& c : ch)
                for (std::int64_t i = 0; i < fade; ++i)
                    c[static_cast<std::size_t>(frames - fade + i)] *=
                        static_cast<float>(0.5 * (1.0 + std::cos(kPi * static_cast<double>(i + 1) / static_cast<double>(fade))));
        }
    }
    for (auto& c : ch) c.resize(static_cast<std::size_t>(frames));

    if (o.reverse)
        for (auto& c : ch) std::reverse(c.begin(), c.end());

    const double ratio = o.sampleRate / fileRate * o.stretch;
    const double outSeconds = static_cast<double>(frames) * ratio / o.sampleRate;
    if (outSeconds > kMaxIrSeconds) {
        throw fail("lasts " + fmtNum(std::round(outSeconds * 10.0) / 10.0) + " s (after 'stretch'); the convolver takes up to " +
                   fmtNum(kMaxIrSeconds) + " s: shorten it with 'length'");
    }
    if (std::fabs(ratio - 1.0) > 1e-12) {
        for (auto& c : ch) c = resample(c, ratio);
        // The resampler delays by its kernel half width (~1 ms) to keep the pre-ringing; drop as much of that
        // head as carries less than -70 dB of the IR's energy (all channels alike), so the IR keeps the file's
        // timing - exactly when the file has any silence before the direct sound, within ~0.5 ms for a hard
        // onset at its first sample (zero latency: the dry path and other tracks stay aligned).
        double total = 0.0;
        for (const auto& c : ch)
            for (const float v : c) total += static_cast<double>(v) * v;
        const std::size_t delay = static_cast<std::size_t>(resampleDelay(ratio));
        std::size_t drop = 0;
        for (double head = 0.0; drop < delay && drop + 1 < ch[0].size(); ++drop) {
            for (const auto& c : ch) head += static_cast<double>(c[drop]) * c[drop];
            if (head > 1e-7 * total) break;
        }
        if (drop > 0)
            for (auto& c : ch) c.erase(c.begin(), c.begin() + static_cast<std::ptrdiff_t>(drop));
    }

    Ir ir;
    ir.fileChannels = nch;
    ir.fileRate = fileRate;
    if (nch == 1) ir.routes = {{0, 0, 0}, {1, 1, 0}};
    else if (nch == 2) ir.routes = {{0, 0, 0}, {1, 1, 1}};
    else ir.routes = {{0, 0, 0}, {0, 1, 1}, {1, 0, 2}, {1, 1, 3}};
    if (o.normalize) {
        // unit energy per output channel: white noise (uncorrelated L / R) comes out at its input level
        double e = 0.0;
        for (const Route& r : ir.routes)
            for (const float v : ch[static_cast<std::size_t>(r.ir)]) e += static_cast<double>(v) * v;
        e *= 0.5;
        if (!(e > 0.0)) throw fail("is silent at this sample rate");
        ir.gain = 1.0 / std::sqrt(e);
    } else {
        // the same filter at the render rate (resampling keeps amplitudes, so the gain follows the rate);
        // 'stretch' keeps the energy
        ir.gain = (fileRate / o.sampleRate) / std::sqrt(o.stretch);
    }
    if (ir.gain != 1.0)
        for (auto& c : ch)
            for (float& v : c) v = static_cast<float>(v * ir.gain);
    // Samples more than 200 dB under the peak become exact zeros: float IR files often keep denormal or
    // near-denormal 'silence' (before the direct sound, in fades), and every product with such a tap is a
    // denormal - several times slower on x86 in the direct-form head and the FFT partitions.
    float outPeak = 0.0f;
    for (const auto& c : ch)
        for (const float v : c) outPeak = std::max(outPeak, std::fabs(v));
    const float tiny = std::max(outPeak * 1e-10f, std::numeric_limits<float>::min());
    for (auto& c : ch)
        for (float& v : c)
            if (std::fabs(v) < tiny) v = 0.0f;
    ir.channels = std::move(ch);
    return ir;
}

Ir loadIr(const std::vector<std::string>& paths, const std::vector<std::string>& shown, const IrOptions& o) {
    std::vector<std::shared_ptr<const WavChannels>> wavs;
    std::string where;
    for (std::size_t f = 0; f < paths.size(); ++f) {
        const std::string& path = paths[f];
        const std::string& name = shown[f];
        const std::string one = "IR '" + name + "'" + (path != name ? " (" + path + ")" : "");
        where += (f ? " + '" : "IR '") + name + "'";
        std::error_code ec;
        if (!fs::is_regular_file(fs::path(path), ec)) {
            std::string msg = "IR file '" + name + "' not found" + (path != name ? " (resolved to '" + path + "')" : "");
            if (const std::string pack = missingPack(path); !pack.empty()) {
                msg += ": the sample pack '" + pack + "' is not installed (python -m agentsound samples; fetch it with "
                       "python -m agentsound samples fetch " + pack + ")";
            }
            throw ConfigError(msg);
        }
        std::string ext = fs::path(path).extension().string();
        for (auto& c : ext) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        if (ext != ".wav") throw ConfigError(one + " is not a .wav file (the sample library converts FLAC / AIFF / OGG packs to WAV)");
        try {
            wavs.push_back(readCached(path));
        } catch (const std::exception& e) {
            throw ConfigError(one + ": cannot load it: " + e.what());
        }
        const WavChannels& w = *wavs.back();
        if (w.frames() > static_cast<std::int64_t>(600.0 * w.sampleRate)) throw ConfigError(one + " is longer than 10 minutes: not an impulse response");
        if (f > 0 && w.sampleRate != wavs[0]->sampleRate) {
            throw ConfigError(one + " is at " + std::to_string(w.sampleRate) + " Hz but '" + shown[0] + "' at " +
                              std::to_string(wavs[0]->sampleRate) + " Hz: the files of one IR need the same sample rate");
        }
        if (f > 0 && w.channels.size() != wavs[0]->channels.size())
            throw ConfigError(where + ": the files of one IR need the same channel count (" + std::to_string(wavs[0]->channels.size()) +
                              " and " + std::to_string(w.channels.size()) + ")");
    }
    // Several files: their channels in order (2 mono = L, R; 2 stereo = the left input's L, R outputs then the
    // right input's; 4 mono = LL, LR, RL, RR).
    const std::size_t per = wavs[0]->channels.size();
    if (wavs.size() > 1 && !((wavs.size() == 2 && per <= 2) || (wavs.size() == 4 && per == 1))) {
        throw ConfigError(where + ": " + std::to_string(wavs.size()) + " files of " + std::to_string(per) + " channel(s); several files "
                          "make one IR: 2 mono files (left, right), 2 stereo files (the response to the left input, then to "
                          "the right input: true stereo) or 4 mono files (LL, LR, RL, RR)");
    }
    std::vector<std::vector<float>> ch;
    std::size_t frames = 0;
    for (const auto& w : wavs)
        for (const auto& c : w->channels) {
            ch.push_back(c);
            frames = std::max(frames, c.size());
        }
    for (auto& c : ch) c.resize(frames, 0.0f);
    return prepareIr(std::move(ch), static_cast<double>(wavs[0]->sampleRate), o, where);
}

}  // namespace as::conv
