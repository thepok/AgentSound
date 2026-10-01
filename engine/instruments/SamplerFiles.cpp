#include "instruments/SamplerFiles.h"

#include "instruments/SamplerWavPack.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <utility>

namespace as::smp {
namespace {

namespace fs = std::filesystem;

struct FileCloser {
    void operator()(std::FILE* f) const noexcept { if (f) std::fclose(f); }
};
using FilePtr = std::unique_ptr<std::FILE, FileCloser>;

std::uint16_t u16(const unsigned char* p) { return static_cast<std::uint16_t>(p[0] | (p[1] << 8)); }
std::uint32_t u32(const unsigned char* p) {
    return static_cast<std::uint32_t>(p[0]) | (static_cast<std::uint32_t>(p[1]) << 8) | (static_cast<std::uint32_t>(p[2]) << 16) |
           (static_cast<std::uint32_t>(p[3]) << 24);
}
std::uint64_t u64(const unsigned char* p) { return static_cast<std::uint64_t>(u32(p)) | (static_cast<std::uint64_t>(u32(p + 4)) << 32); }

std::vector<unsigned char> readAll(const std::string& path) {
    FilePtr f(std::fopen(path.c_str(), "rb"));
    if (!f) throw std::runtime_error("cannot open '" + path + "'");
#ifdef _WIN32
    if (_fseeki64(f.get(), 0, SEEK_END) != 0) throw std::runtime_error("'" + path + "': seek failed");
    const std::int64_t size = _ftelli64(f.get());
    _fseeki64(f.get(), 0, SEEK_SET);
#else
    if (fseeko(f.get(), 0, SEEK_END) != 0) throw std::runtime_error("'" + path + "': seek failed");
    const std::int64_t size = static_cast<std::int64_t>(ftello(f.get()));
    fseeko(f.get(), 0, SEEK_SET);
#endif
    if (size < 0) throw std::runtime_error("'" + path + "': cannot determine the file size");
    std::vector<unsigned char> bytes(static_cast<std::size_t>(size));
    if (size > 0 && std::fread(bytes.data(), 1, bytes.size(), f.get()) != bytes.size()) {
        throw std::runtime_error("'" + path + "': read error");
    }
    return bytes;
}

// The 'smpl' chunk: MIDI unity note (+ pitch fraction) and the first loop.
void readSmpl(const unsigned char* body, std::uint64_t size, std::optional<FileLoop>& loop, std::optional<double>& unity) {
    if (size < 36) return;
    const std::uint32_t note = u32(body + 12), fraction = u32(body + 16), loops = u32(body + 28);
    if (note <= 127) unity = static_cast<double>(note) + static_cast<double>(fraction) / 4294967296.0;
    if (loops >= 1 && size >= 60) {
        const std::uint32_t type = u32(body + 36 + 4), start = u32(body + 36 + 8), end = u32(body + 36 + 12);
        if (end >= start) loop = FileLoop{static_cast<std::int64_t>(start), static_cast<std::int64_t>(end) + 1, type == 1};
    }
}

// PCM frames of a decoded file in one of three layouts: WAV bytes (PCM / float), or WavPack integers.
struct Pcm {
    const unsigned char* data{nullptr};   // WAV: interleaved frames of blockAlign bytes
    const std::int32_t* ints{nullptr};    // WavPack: interleaved sign-extended integers of `bits` bits
    int format{1};                        // WAV: 1 = PCM, 3 = float
    int channels{1}, bits{16}, blockAlign{2};
    std::int64_t frames{0};

    float sample(std::int64_t f, int c) const noexcept {
        if (ints) {
            const std::int32_t v = ints[f * channels + c];
            return static_cast<float>(static_cast<double>(v) / static_cast<double>(std::int64_t{1} << (bits - 1)));
        }
        const unsigned char* q = data + f * blockAlign + c * (bits / 8);
        if (format == 3) {
            if (bits == 32) {
                float v;
                const std::uint32_t u = u32(q);
                std::memcpy(&v, &u, 4);
                return std::isfinite(v) ? v : 0.0f;
            }
            double d;
            const std::uint64_t u = u64(q);
            std::memcpy(&d, &u, 8);
            return std::isfinite(d) ? static_cast<float>(d) : 0.0f;
        }
        switch (bits) {
            case 8: return static_cast<float>(static_cast<int>(q[0]) - 128) / 128.0f;
            case 16: return static_cast<float>(static_cast<std::int16_t>(u16(q))) / 32768.0f;
            case 24: {
                std::int32_t x = static_cast<std::int32_t>(q[0] | (q[1] << 8) | (q[2] << 16));
                if (x & 0x800000) x -= 0x1000000;
                return static_cast<float>(x) / 8388608.0f;
            }
            default: return static_cast<float>(static_cast<double>(static_cast<std::int32_t>(u32(q))) / 2147483648.0);
        }
    }
    // Lossless 16-bit value (only when fits16() holds).
    std::int16_t sample16(std::int64_t f, int c) const noexcept {
        if (ints) {
            const std::int32_t v = ints[f * channels + c];
            return static_cast<std::int16_t>(bits <= 16 ? v * (1 << (16 - bits)) : v / (1 << (bits - 16)));
        }
        const unsigned char* q = data + f * blockAlign + c * (bits / 8);
        if (bits == 8) return static_cast<std::int16_t>((static_cast<int>(q[0]) - 128) * 256);
        if (bits == 16) return static_cast<std::int16_t>(u16(q));
        return static_cast<std::int16_t>(u16(q + 1));  // 24-bit with a zero low byte
    }
    // 16-bit storage is lossless: 8/16-bit data, and 24-bit data whose low byte is always zero.
    bool fits16(int played) const noexcept {
        if (format == 3 && !ints) return false;
        if (bits <= 16) return true;
        if (bits != 24) return false;
        for (std::int64_t f = 0; f < frames; ++f) {
            for (int c = 0; c < played; ++c) {
                if (ints ? (ints[f * channels + c] & 0xff) != 0 : data[f * blockAlign + c * 3] != 0) return false;
            }
        }
        return true;
    }
};

// Decodes a WAV (or WavPack) file held in memory into a guarded segment A. `mix` (optional) mixes the listed
// channels into stereo at load time.
std::shared_ptr<SampleFile> decodeWav(const std::string& path, const std::vector<unsigned char>& bytes, bool reverse,
                                      const std::vector<ChannelGain>& mix) {
    auto fail = [&](const std::string& why) { return std::runtime_error("'" + path + "': " + why); };
    const std::size_t n = bytes.size();
    const unsigned char* p = bytes.data();
    Pcm pcm;
    double rate = 0.0;
    std::optional<FileLoop> loop;
    std::optional<double> unity;
    WavPackAudio wv;
    if (isWavPack(p, n)) {
        try {
            wv = decodeWavPack(p, n);
        } catch (const std::exception& e) {
            throw fail(e.what());
        }
        pcm.ints = wv.samples.data();
        pcm.channels = wv.channels;
        pcm.bits = wv.bits;
        pcm.frames = wv.frames;
        rate = wv.rate;
        for (std::size_t off = 0; off + 8 <= wv.riff.size();) {  // the embedded RIFF chunks: 'smpl' loops
            const unsigned char* h = wv.riff.data() + off;
            const std::uint32_t size = u32(h + 4);
            if (off + 8 + size > wv.riff.size()) break;
            if (std::memcmp(h, "smpl", 4) == 0) readSmpl(h + 8, size, loop, unity);
            off += 8 + size + (size & 1u);
        }
    } else {
        if (n < 12) throw fail("too short for a WAV file");
        const bool rf64 = std::memcmp(p, "RF64", 4) == 0;
        if (std::memcmp(p, "RIFF", 4) != 0 && !rf64) throw fail("not a RIFF/RF64 WAV file");
        if (std::memcmp(p + 8, "WAVE", 4) != 0) throw fail("not a WAVE file");
        int format = 0, channels = 0, bits = 0, blockAlign = 0;
        std::size_t dataOff = 0;
        std::uint64_t dataSize = 0, ds64Data = 0;
        bool haveFmt = false, haveData = false;
        std::size_t off = 12;
        while (off + 8 <= n) {
            const unsigned char* h = p + off;
            std::uint64_t size = u32(h + 4);
            const std::size_t body = off + 8;
            if (std::memcmp(h, "ds64", 4) == 0 && size >= 16 && body + 16 <= n) {
                ds64Data = u64(p + body + 8);
            } else if (std::memcmp(h, "fmt ", 4) == 0) {
                if (size < 16 || body + size > n) throw fail("bad fmt chunk");
                format = u16(p + body);
                channels = u16(p + body + 2);
                rate = static_cast<double>(u32(p + body + 4));
                blockAlign = u16(p + body + 12);
                bits = u16(p + body + 14);
                if (format == 0xFFFE) {  // WAVE_FORMAT_EXTENSIBLE: the sub-format GUID starts with the format code
                    if (size < 40) throw fail("bad WAVE_FORMAT_EXTENSIBLE fmt chunk");
                    format = u16(p + body + 24);
                }
                haveFmt = true;
            } else if (std::memcmp(h, "data", 4) == 0) {
                haveData = true;
                dataOff = body;
                if (rf64 && size == 0xFFFFFFFFull) size = ds64Data;
                // Streaming writers may leave the size at 0 / 0xFFFFFFFF, and truncated files are common: take what is there.
                if (size == 0 || size == 0xFFFFFFFFull || body + size > n) size = n - body;
                dataSize = size;
            } else if (std::memcmp(h, "smpl", 4) == 0 && body + 36 <= n) {
                readSmpl(p + body, std::min<std::uint64_t>(size, n - body), loop, unity);
            }
            if (size > n) break;
            off = body + static_cast<std::size_t>(size) + (size & 1u);
        }
        if (!haveFmt) throw fail("no fmt chunk");
        if (!haveData) throw fail("no data chunk");
        if (format == 1) {
            if (bits != 8 && bits != 16 && bits != 24 && bits != 32) throw fail("unsupported PCM bit depth " + std::to_string(bits));
        } else if (format == 3) {
            if (bits != 32 && bits != 64) throw fail("unsupported float bit depth " + std::to_string(bits));
        } else {
            throw fail("unsupported WAV format code " + std::to_string(format) + " (PCM or IEEE float only)");
        }
        if (channels < 1 || channels > 64) throw fail("bad channel count " + std::to_string(channels));
        if (blockAlign != channels * bits / 8) throw fail("inconsistent block alignment");
        pcm.data = p + dataOff;
        pcm.format = format;
        pcm.channels = channels;
        pcm.bits = bits;
        pcm.blockAlign = blockAlign;
        pcm.frames = static_cast<std::int64_t>(dataSize / static_cast<std::uint64_t>(blockAlign));
    }
    if (rate < 1000.0 || rate > 1000000.0) throw fail("bad sample rate");
    const std::int64_t frames = pcm.frames;
    if (frames < 1) throw fail("has no audio frames");
    for (const auto& m : mix) {
        if (m.channel < 0 || m.channel >= pcm.channels) {
            throw fail("the channel mix uses channel " + std::to_string(m.channel) + " but the file has " + std::to_string(pcm.channels) +
                       " channel(s) (0.." + std::to_string(pcm.channels - 1) + ")");
        }
    }

    auto file = std::make_shared<SampleFile>();
    file->channels = !mix.empty() ? 2 : (pcm.channels >= 2 ? 2 : 1);
    file->fileChannels = pcm.channels;
    file->bits = pcm.bits;
    file->isFloat = pcm.format == 3 && !pcm.ints;
    file->rate = rate;
    file->frames = frames;
    file->reversed = reverse;
    file->unityNote = unity;
    // A mix that only picks / swaps / polarity-flips channels (gains 0 or +-1, one source per side) keeps 16-bit data.
    int pick[2] = {-1, -1};
    int sign[2] = {1, 1};
    bool simple = !mix.empty();
    for (const auto& m : mix) {
        const float g[2] = {m.left, m.right};
        for (int side = 0; side < 2; ++side) {
            if (g[side] == 0.0f) continue;
            if ((g[side] != 1.0f && g[side] != -1.0f) || pick[side] >= 0) simple = false;
            pick[side] = m.channel;
            sign[side] = g[side] < 0.0f ? -1 : 1;
        }
    }
    simple = simple && pick[0] >= 0 && pick[1] >= 0;
    const bool is16 = (mix.empty() || simple) && pcm.fits16(simple ? pcm.channels : file->channels);
    auto seg = std::make_shared<Segment>();
    seg->is16 = is16;
    const auto total = static_cast<std::size_t>(frames + 2 * kGuardA);
    for (int c = 0; c < file->channels; ++c) {
        if (is16) seg->s[static_cast<std::size_t>(c)].assign(total, 0);
        else seg->f[static_cast<std::size_t>(c)].assign(total, 0.0f);
    }
    for (std::int64_t f = 0; f < frames; ++f) {
        const auto dst = static_cast<std::size_t>((reverse ? frames - 1 - f : f) + kGuardA);
        if (!mix.empty() && is16) {
            for (int side = 0; side < 2; ++side) {
                const int v = sign[side] * pcm.sample16(f, pick[side]);
                seg->s[static_cast<std::size_t>(side)][dst] = static_cast<std::int16_t>(std::clamp(v, -32768, 32767));
            }
            continue;
        }
        if (!mix.empty()) {
            float l = 0.0f, r = 0.0f;
            for (const auto& m : mix) {
                const float x = pcm.sample(f, m.channel);
                l += m.left * x;
                r += m.right * x;
            }
            seg->f[0][dst] = l;
            seg->f[1][dst] = r;
            continue;
        }
        for (int c = 0; c < file->channels; ++c) {
            if (is16) seg->s[static_cast<std::size_t>(c)][dst] = pcm.sample16(f, c);
            else seg->f[static_cast<std::size_t>(c)][dst] = pcm.sample(f, c);
        }
    }
    if (loop && !(loop->start >= 0 && loop->end <= frames && loop->end - loop->start >= (loop->pingpong ? 2 : 1))) loop.reset();
    if (loop && reverse) *loop = FileLoop{frames - loop->end, frames - loop->start, loop->pingpong};
    file->loop = loop;
    file->a = std::move(seg);
    return file;
}

using Key = std::pair<std::string, bool>;
std::mutex gMutex;
std::map<Key, std::shared_ptr<const SampleFile>>& cache() {
    static std::map<Key, std::shared_ptr<const SampleFile>> c;
    return c;
}

std::shared_ptr<const SampleFile> lookup(const Key& key) {
    std::lock_guard<std::mutex> lock(gMutex);
    const auto it = cache().find(key);
    return it == cache().end() ? nullptr : it->second;
}

std::shared_ptr<const SampleFile> insert(const Key& key, std::shared_ptr<SampleFile> file) {
    file->path = key.first;
    std::lock_guard<std::mutex> lock(gMutex);
    const auto [it, fresh] = cache().emplace(key, std::move(file));
    return it->second;  // another thread may have been first: everyone shares that one
}

}  // namespace

std::string fileKey(const std::string& path) { return fs::path(path).lexically_normal().generic_string(); }

std::string fileKey(const std::string& path, const std::vector<ChannelGain>& mix) {
    std::string key = fileKey(path);
    if (mix.empty()) return key;
    std::ostringstream s;
    s.precision(9);
    s << key << "#mix";
    for (const auto& m : mix) s << ':' << m.channel << ',' << m.left << ',' << m.right;
    return s.str();
}

std::shared_ptr<const SampleFile> loadSampleFile(const std::string& path, bool reverse, const std::vector<ChannelGain>& mix) {
    const Key key{fileKey(path, mix), reverse};
    if (auto hit = lookup(key)) return hit;
    const std::string real = fileKey(path);
    return insert(key, decodeWav(real, readAll(real), reverse, mix));
}

std::map<std::string, std::string> preloadSampleFiles(const std::vector<std::string>& paths, bool reverse, LoadStats* stats) {
    std::vector<FileRequest> requests;
    requests.reserve(paths.size());
    for (const auto& p : paths) requests.push_back({p, {}});
    return preloadSampleFiles(requests, reverse, stats);
}

std::map<std::string, std::string> preloadSampleFiles(const std::vector<FileRequest>& requests, bool reverse, LoadStats* stats) {
    const auto t0 = std::chrono::steady_clock::now();
    struct Job {
        std::string key, path;
        const std::vector<ChannelGain>* mix;
    };
    std::vector<Job> jobs;
    for (const auto& r : requests) jobs.push_back({fileKey(r.path, r.mix), fileKey(r.path), &r.mix});
    std::sort(jobs.begin(), jobs.end(), [](const Job& a, const Job& b) { return a.key < b.key; });
    jobs.erase(std::unique(jobs.begin(), jobs.end(), [](const Job& a, const Job& b) { return a.key == b.key; }), jobs.end());
    std::vector<Job> todo;
    for (const auto& j : jobs) {
        if (!lookup({j.key, reverse})) todo.push_back(j);
    }
    std::map<std::string, std::string> errors;
    std::mutex errMutex;
    std::atomic<std::size_t> next{0};
    std::atomic<std::uint64_t> bytes{0}, fileBytes{0};
    auto work = [&] {
        while (true) {
            const std::size_t i = next.fetch_add(1);
            if (i >= todo.size()) return;
            try {
                const auto raw = readAll(todo[i].path);
                fileBytes += raw.size();
                auto file = decodeWav(todo[i].path, raw, reverse, *todo[i].mix);
                bytes += file->a->bytes();
                insert({todo[i].key, reverse}, std::move(file));
            } catch (const std::exception& e) {
                std::lock_guard<std::mutex> lock(errMutex);
                errors[todo[i].key] = e.what();
            }
        }
    };
    const unsigned hw = std::max(1u, std::thread::hardware_concurrency());
    const std::size_t threads = std::min<std::size_t>({8, hw, todo.size()});
    if (threads <= 1) {
        work();
    } else {
        std::vector<std::thread> pool;
        for (std::size_t t = 0; t < threads; ++t) pool.emplace_back(work);
        for (auto& t : pool) t.join();
    }
    if (stats) {
        stats->requested = static_cast<int>(jobs.size());
        stats->loaded = static_cast<int>(todo.size() - errors.size());
        stats->cached = static_cast<int>(jobs.size() - todo.size());
        stats->bytes = bytes.load();
        stats->fileBytes = fileBytes.load();
        stats->seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    }
    return errors;
}

std::uint64_t cachedSampleBytes() noexcept {
    std::lock_guard<std::mutex> lock(gMutex);
    std::uint64_t total = 0;
    for (const auto& [k, f] : cache()) total += f->a->bytes();
    return total;
}

int cachedSampleFiles() noexcept {
    std::lock_guard<std::mutex> lock(gMutex);
    return static_cast<int>(cache().size());
}

std::shared_ptr<const Region> sineRegion() {
    static const std::shared_ptr<const Region> r = [] {
        constexpr int kLen = 256;  // one cycle of C4 (MIDI 60): rate = 256 x 261.63 Hz
        std::vector<float> cycle(kLen);
        for (int i = 0; i < kLen; ++i) cycle[static_cast<std::size_t>(i)] = static_cast<float>(std::sin(dsp::kTwoPi * i / kLen));
        const double rate = kLen * dsp::midiToHz(60.0);
        return std::make_shared<const Region>(makeRegion(&cycle, 1, rate, LoopMode::Forward, 0, kLen));
    }();
    return r;
}

std::shared_ptr<const Region> noiseRegion() {
    static const std::shared_ptr<const Region> r = [] {
        std::vector<float> noise(48000);
        dsp::Rng rng(0x6E6F697365ull);
        for (auto& x : noise) x = rng.bipolar();
        return std::make_shared<const Region>(makeRegion(&noise, 1, 48000.0, LoopMode::Forward, 0, 48000));
    }();
    return r;
}

}  // namespace as::smp
