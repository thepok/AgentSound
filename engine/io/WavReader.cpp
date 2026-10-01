#include "io/WavReader.h"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <memory>
#include <stdexcept>

namespace as {

namespace {

struct FileCloser {
    void operator()(std::FILE* f) const noexcept { if (f) std::fclose(f); }
};
using File = std::unique_ptr<std::FILE, FileCloser>;

// 64-bit file positions (long is 32-bit on Windows).
int seek64(std::FILE* f, std::int64_t off, int whence) {
#ifdef _WIN32
    return _fseeki64(f, off, whence);
#else
    return fseeko(f, static_cast<off_t>(off), whence);
#endif
}
std::int64_t tell64(std::FILE* f) {
#ifdef _WIN32
    return _ftelli64(f);
#else
    return static_cast<std::int64_t>(ftello(f));
#endif
}

std::uint16_t u16(const unsigned char* p) { return static_cast<std::uint16_t>(p[0] | (p[1] << 8)); }
std::uint32_t u32(const unsigned char* p) {
    return static_cast<std::uint32_t>(p[0]) | (static_cast<std::uint32_t>(p[1]) << 8) | (static_cast<std::uint32_t>(p[2]) << 16) |
           (static_cast<std::uint32_t>(p[3]) << 24);
}

struct Layout {
    WavData info;
    std::int64_t dataOffset{0};
    int blockAlign{0};
};

Layout parseHeader(std::FILE* f, const std::string& path) {
    auto fail = [&](const std::string& why) { return std::runtime_error("'" + path + "': " + why); };
    unsigned char riff[12];
    if (std::fread(riff, 1, 12, f) != 12) throw fail("too short for a WAV file");
    if (std::memcmp(riff, "RIFF", 4) != 0 && std::memcmp(riff, "RF64", 4) != 0) throw fail("not a RIFF file");
    if (std::memcmp(riff + 8, "WAVE", 4) != 0) throw fail("not a WAVE file");
    Layout lay;
    bool haveFmt = false;
    int format = 0;
    std::int64_t offset = 12;
    while (true) {
        unsigned char hdr[8];
        if (std::fread(hdr, 1, 8, f) != 8) break;
        const std::uint32_t size = u32(hdr + 4);
        offset += 8;
        if (std::memcmp(hdr, "fmt ", 4) == 0) {
            if (size < 16 || size > 1024) throw fail("bad fmt chunk size");
            unsigned char fmt[1024];
            if (std::fread(fmt, 1, size, f) != size) throw fail("truncated fmt chunk");
            format = u16(fmt);
            lay.info.channels = u16(fmt + 2);
            lay.info.sampleRate = static_cast<int>(u32(fmt + 4));
            lay.blockAlign = u16(fmt + 12);
            lay.info.bitsPerSample = u16(fmt + 14);
            if (format == 0xFFFE) {  // WAVE_FORMAT_EXTENSIBLE: the sub-format GUID starts with the format code
                if (size < 40) throw fail("bad WAVE_FORMAT_EXTENSIBLE fmt chunk");
                format = u16(fmt + 24);
            }
            haveFmt = true;
            if (size & 1u) seek64(f, 1, SEEK_CUR);
            offset += size + (size & 1u);
        } else if (std::memcmp(hdr, "data", 4) == 0) {
            if (!haveFmt) throw fail("data chunk before fmt chunk");
            lay.dataOffset = offset;
            std::int64_t bytes = size;
            // Streaming writers may leave the size at 0 / 0xFFFFFFFF: take the rest of the file.
            seek64(f, 0, SEEK_END);
            const std::int64_t fileEnd = tell64(f);
            if (bytes == 0 || size == 0xFFFFFFFFu || offset + bytes > fileEnd) bytes = std::max<std::int64_t>(0, fileEnd - offset);
            lay.info.totalFrames = lay.blockAlign > 0 ? bytes / lay.blockAlign : 0;
            break;
        } else {
            const std::int64_t skip = static_cast<std::int64_t>(size) + (size & 1u);
            if (seek64(f, skip, SEEK_CUR) != 0) throw fail("truncated chunk");
            offset += skip;
        }
    }
    if (!haveFmt) throw fail("no fmt chunk");
    if (lay.dataOffset == 0) throw fail("no data chunk");
    const int bits = lay.info.bitsPerSample;
    if (format == 1) {
        if (bits != 8 && bits != 16 && bits != 24 && bits != 32) throw fail("unsupported PCM bit depth " + std::to_string(bits));
    } else if (format == 3) {
        if (bits != 32 && bits != 64) throw fail("unsupported float bit depth " + std::to_string(bits));
        lay.info.isFloat = true;
    } else {
        throw fail("unsupported WAV format code " + std::to_string(format) + " (PCM or IEEE float only)");
    }
    if (lay.info.channels < 1 || lay.info.channels > 64) throw fail("bad channel count");
    if (lay.info.sampleRate < 1000 || lay.info.sampleRate > 1000000) throw fail("bad sample rate");
    if (lay.blockAlign != lay.info.channels * bits / 8) throw fail("inconsistent block alignment");
    return lay;
}

float decode(const unsigned char* p, int bits, bool isFloat) {
    if (isFloat) {
        if (bits == 32) {
            float v;
            std::uint32_t u = u32(p);
            std::memcpy(&v, &u, 4);
            return v;
        }
        std::uint64_t u = static_cast<std::uint64_t>(u32(p)) | (static_cast<std::uint64_t>(u32(p + 4)) << 32);
        double v;
        std::memcpy(&v, &u, 8);
        return static_cast<float>(v);
    }
    switch (bits) {
        case 8: return (static_cast<int>(p[0]) - 128) / 128.0f;
        case 16: return static_cast<float>(static_cast<std::int16_t>(u16(p))) / 32768.0f;
        case 24: {
            std::int32_t v = static_cast<std::int32_t>(p[0] | (p[1] << 8) | (p[2] << 16));
            if (v & 0x800000) v -= 0x1000000;
            return static_cast<float>(v) / 8388608.0f;
        }
        default: return static_cast<float>(static_cast<double>(static_cast<std::int32_t>(u32(p))) / 2147483648.0);
    }
}

}  // namespace

WavData readWavInfo(const std::string& path) {
    File f(std::fopen(path.c_str(), "rb"));
    if (!f) throw std::runtime_error("cannot open '" + path + "'");
    return parseHeader(f.get(), path).info;
}

WavChannels readWavChannels(const std::string& path) {
    File f(std::fopen(path.c_str(), "rb"));
    if (!f) throw std::runtime_error("cannot open '" + path + "'");
    const Layout lay = parseHeader(f.get(), path);
    WavChannels out;
    out.sampleRate = lay.info.sampleRate;
    out.bitsPerSample = lay.info.bitsPerSample;
    out.isFloat = lay.info.isFloat;
    const int channels = lay.info.channels;
    const auto n = static_cast<std::size_t>(lay.info.totalFrames);
    out.channels.assign(static_cast<std::size_t>(channels), std::vector<float>(n));
    if (n == 0) return out;
    if (seek64(f.get(), lay.dataOffset, SEEK_SET) != 0) throw std::runtime_error("'" + path + "': seek failed");
    const int bytesPer = lay.info.bitsPerSample / 8;
    std::vector<unsigned char> buf(static_cast<std::size_t>(lay.blockAlign) * 4096);
    std::size_t done = 0;
    while (done < n) {
        const std::size_t want = std::min<std::size_t>(4096, n - done);
        const std::size_t got = std::fread(buf.data(), static_cast<std::size_t>(lay.blockAlign), want, f.get());
        for (std::size_t k = 0; k < got; ++k) {
            const unsigned char* fr = buf.data() + k * static_cast<std::size_t>(lay.blockAlign);
            for (int c = 0; c < channels; ++c)
                out.channels[static_cast<std::size_t>(c)][done + k] = decode(fr + c * bytesPer, lay.info.bitsPerSample, lay.info.isFloat);
        }
        done += got;
        if (got < want) {  // truncated file: keep what was read
            for (auto& ch : out.channels) ch.resize(done);
            break;
        }
    }
    return out;
}

WavData readWav(const std::string& path, std::int64_t startFrame, std::int64_t frameCount) {
    File f(std::fopen(path.c_str(), "rb"));
    if (!f) throw std::runtime_error("cannot open '" + path + "'");
    Layout lay = parseHeader(f.get(), path);
    WavData out = lay.info;
    const std::int64_t first = std::clamp<std::int64_t>(startFrame, 0, out.totalFrames);
    const std::int64_t last = frameCount < 0 ? out.totalFrames : std::clamp<std::int64_t>(startFrame + frameCount, first, out.totalFrames);
    out.startFrame = first;
    const auto n = static_cast<std::size_t>(last - first);
    out.left.resize(n);
    out.right.resize(n);
    if (n == 0) return out;
    if (seek64(f.get(), lay.dataOffset + first * lay.blockAlign, SEEK_SET) != 0)
        throw std::runtime_error("'" + path + "': seek failed");
    const int bytesPer = lay.info.bitsPerSample / 8;
    const bool stereo = out.channels >= 2;
    std::vector<unsigned char> buf(static_cast<std::size_t>(lay.blockAlign) * 4096);
    std::size_t done = 0;
    while (done < n) {
        const std::size_t want = std::min<std::size_t>(4096, n - done);
        const std::size_t got = std::fread(buf.data(), static_cast<std::size_t>(lay.blockAlign), want, f.get());
        for (std::size_t k = 0; k < got; ++k) {
            const unsigned char* fr = buf.data() + k * static_cast<std::size_t>(lay.blockAlign);
            const float l = decode(fr, lay.info.bitsPerSample, lay.info.isFloat);
            out.left[done + k] = l;
            out.right[done + k] = stereo ? decode(fr + bytesPer, lay.info.bitsPerSample, lay.info.isFloat) : l;
        }
        done += got;
        if (got < want) {  // truncated file: keep what was read
            out.left.resize(done);
            out.right.resize(done);
            break;
        }
    }
    return out;
}

}  // namespace as
