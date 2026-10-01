#include "instruments/SamplerWavPack.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <stdexcept>

// A clean-room lossless WavPack decoder following the published format (WavPack 4 / 5 block layout, the
// entropy coder with its three adaptive medians and zero runs, decorrelation passes with terms 1..8, 17, 18
// and the cross-channel terms -1..-3). Checked per block against the stream's own CRC.

namespace as::smp {
namespace {

constexpr std::uint32_t kBytesStored = 3, kMonoFlag = 4, kHybridFlag = 8, kJointStereo = 0x10, kFloatData = 0x80,
                        kInt32Data = 0x100, kInitialBlock = 0x800, kFinalBlock = 0x1000, kShiftLsb = 13,
                        kShiftMask = 0x1fu << 13, kSrateLsb = 23, kSrateMask = 0xfu << 23, kFalseStereo = 0x40000000u,
                        kDsdFlag = 0x80000000u;
constexpr std::uint32_t kMonoData = kMonoFlag | kFalseStereo;
constexpr int kMaxTerm = 8, kMaxTerms = 16, kLimitOnes = 16;

enum : int {
    kIdDecorrTerms = 0x2, kIdDecorrWeights = 0x3, kIdDecorrSamples = 0x4, kIdEntropyVars = 0x5, kIdInt32Info = 0x9,
    kIdWvBitstream = 0xa, kIdRiffHeader = 0x21, kIdRiffTrailer = 0x22, kIdSampleRate = 0x27,
};

const std::array<unsigned char, 256>& exp2Table() {
    static const std::array<unsigned char, 256> t = [] {
        std::array<unsigned char, 256> a{};
        for (int i = 0; i < 256; ++i) a[static_cast<std::size_t>(i)] = static_cast<unsigned char>(std::lround(256.0 * std::exp2(i / 256.0)) - 256);
        return a;
    }();
    return t;
}

std::int32_t exp2s(int log) {
    if (log < 0) return -exp2s(-log);
    const std::uint32_t value = exp2Table()[static_cast<std::size_t>(log & 0xff)] | 0x100u;
    log >>= 8;
    if (log <= 9) return static_cast<std::int32_t>(value >> (9 - log));
    if (log - 9 >= 32) return 0;
    return static_cast<std::int32_t>(value << (log - 9));
}

int restoreWeight(signed char weight) {
    int result = static_cast<int>(weight) * 8;
    if (result > 0) result += (result + 64) >> 7;
    return result;
}

std::uint16_t le16(const unsigned char* p) { return static_cast<std::uint16_t>(p[0] | (p[1] << 8)); }
std::uint32_t le32(const unsigned char* p) {
    return static_cast<std::uint32_t>(p[0]) | (static_cast<std::uint32_t>(p[1]) << 8) | (static_cast<std::uint32_t>(p[2]) << 16) |
           (static_cast<std::uint32_t>(p[3]) << 24);
}

// Integer ops with the stream's wrap-around semantics (no signed overflow in C++).
inline std::int32_t wrap(std::int64_t x) noexcept { return static_cast<std::int32_t>(static_cast<std::uint32_t>(x)); }

inline std::int32_t applyWeight(std::int32_t weight, std::int32_t sample) noexcept {
    if (sample == static_cast<std::int16_t>(sample)) return wrap((static_cast<std::int64_t>(weight) * sample + 512) >> 10);
    const std::int64_t lo = (static_cast<std::int64_t>(sample & 0xffff) * weight) >> 9;
    const std::int64_t hi = static_cast<std::int64_t>((sample & ~0xffff) >> 9) * weight;
    return wrap((static_cast<std::int64_t>(wrap(lo)) + wrap(hi) + 1) >> 1);
}

inline void updateWeight(std::int32_t& weight, int delta, std::int32_t source, std::int32_t result) noexcept {
    if (source && result) weight += ((source ^ result) < 0) ? -delta : delta;
}

inline void updateWeightClip(std::int32_t& weight, int delta, std::int32_t source, std::int32_t result) noexcept {
    if (source && result) {
        const std::int32_t s = (source ^ result) >> 31;
        weight = (weight ^ s) + (delta - s);
        if (weight > 1024) weight = 1024;
        weight = (weight ^ s) - s;
    }
}

struct Pass {
    int term{0}, delta{0};
    std::int32_t weightA{0}, weightB{0};
    std::array<std::int32_t, kMaxTerm> a{}, b{};
};

struct Bits {
    const unsigned char* p{nullptr};
    const unsigned char* end{nullptr};
    std::uint64_t sr{0};
    int bc{0};
    int overrun{0};  // bytes read past the end (zeros)
    void fill(int n) {
        while (bc < n) {
            std::uint64_t byte = 0;
            if (p < end) byte = *p++;
            else ++overrun;
            sr |= byte << bc;
            bc += 8;
        }
    }
    std::uint32_t bit() {
        fill(1);
        const auto r = static_cast<std::uint32_t>(sr & 1u);
        sr >>= 1;
        --bc;
        return r;
    }
    std::uint32_t bits(int n) {  // n <= 32
        if (n <= 0) return 0;
        fill(n);
        const auto r = static_cast<std::uint32_t>(sr & ((n >= 32) ? 0xffffffffull : ((1ull << n) - 1)));
        sr >>= n;
        bc -= n;
        return r;
    }
};

int countBits(std::uint32_t v) {
    int n = 0;
    while (v) { ++n; v >>= 1; }
    return n;
}

std::uint32_t readCode(Bits& bs, std::uint32_t maxcode) {
    if (maxcode < 2) return maxcode ? bs.bit() : 0u;
    const int bitcount = countBits(maxcode);
    const std::uint32_t extras = static_cast<std::uint32_t>((1ull << bitcount) - maxcode - 1);
    std::uint32_t code = bs.bits(bitcount - 1);
    if (code >= extras) code = (code << 1) - extras + bs.bit();
    return code;
}

struct Entropy {
    std::array<std::uint32_t, 3> median{};
};

// Reads a count coded as: n ones..., then (for n >= 2) n-1 more bits (LSB first) with an implied top bit.
bool readEscape(Bits& bs, std::uint32_t& out) {
    int cbits = 0;
    while (cbits < 33 && bs.bit()) ++cbits;
    if (cbits == 33) return false;
    if (cbits < 2) {
        out = static_cast<std::uint32_t>(cbits);
        return true;
    }
    std::uint32_t mask = 1, value = 0;
    while (--cbits) {
        if (bs.bit()) value |= mask;
        mask <<= 1;
    }
    out = value | mask;
    return true;
}

// The residuals of one block (lossless entropy decoder). Returns false on a corrupt stream.
bool getWords(Bits& bs, bool mono, std::array<Entropy, 2>& c, std::int32_t* out, std::int64_t count) {
    std::uint32_t zerosAcc = 0;
    bool holdingOne = false, holdingZero = false;
    for (std::int64_t i = 0; i < count; ++i) {
        Entropy& e = c[mono ? 0 : static_cast<std::size_t>(i & 1)];
        if (c[0].median[0] < 2 && !holdingZero && !holdingOne && c[1].median[0] < 2) {
            if (zerosAcc) {
                if (--zerosAcc) {
                    out[i] = 0;
                    continue;
                }
            } else {
                if (!readEscape(bs, zerosAcc)) return false;
                if (zerosAcc) {
                    c[0].median = {0, 0, 0};
                    c[1].median = {0, 0, 0};
                    out[i] = 0;
                    continue;
                }
            }
        }
        std::uint32_t ones = 0;
        if (holdingZero) {
            holdingZero = false;
        } else {
            while (ones < static_cast<std::uint32_t>(kLimitOnes + 1) && bs.bit()) ++ones;
            if (ones >= static_cast<std::uint32_t>(kLimitOnes)) {
                if (ones == static_cast<std::uint32_t>(kLimitOnes + 1)) return false;
                std::uint32_t extra = 0;
                if (!readEscape(bs, extra)) return false;
                ones = extra + kLimitOnes;
            }
            if (holdingOne) {
                holdingOne = ones & 1u;
                ones = (ones >> 1) + 1;
            } else {
                holdingOne = ones & 1u;
                ones >>= 1;
            }
            holdingZero = !holdingOne;
        }
        auto med = [&](int k) { return (e.median[static_cast<std::size_t>(k)] >> 4) + 1; };
        auto inc = [&](int k, std::uint32_t div) { e.median[static_cast<std::size_t>(k)] += ((e.median[static_cast<std::size_t>(k)] + div) / div) * 5; };
        auto dec = [&](int k, std::uint32_t div) { e.median[static_cast<std::size_t>(k)] -= ((e.median[static_cast<std::size_t>(k)] + (div - 2)) / div) * 2; };
        std::uint32_t low, high;
        if (ones == 0) {
            low = 0;
            high = med(0) - 1;
            dec(0, 128);
        } else {
            low = med(0);
            inc(0, 128);
            if (ones == 1) {
                high = low + med(1) - 1;
                dec(1, 64);
            } else {
                low += med(1);
                inc(1, 64);
                if (ones == 2) {
                    high = low + med(2) - 1;
                    dec(2, 32);
                } else {
                    low += (ones - 2) * med(2);
                    high = low + med(2) - 1;
                    inc(2, 32);
                }
            }
        }
        const std::uint32_t value = low + readCode(bs, high - low);
        out[i] = bs.bit() ? static_cast<std::int32_t>(~value) : static_cast<std::int32_t>(value);
        if (bs.overrun > 8) return false;
    }
    return true;
}

void monoPass(Pass& d, std::int32_t* buf, std::int64_t n) {
    std::int32_t* const end = buf + n;
    if (d.term == 17 || d.term == 18) {
        for (std::int32_t* p = buf; p < end; ++p) {
            const std::int32_t sam = d.term == 17 ? wrap(2ll * d.a[0] - d.a[1]) : wrap((3ll * d.a[0] - d.a[1]) >> 1);
            d.a[1] = d.a[0];
            d.a[0] = wrap(static_cast<std::int64_t>(applyWeight(d.weightA, sam)) + *p);
            updateWeight(d.weightA, d.delta, sam, *p);
            *p = d.a[0];
        }
        return;
    }
    int m = 0, k = d.term & (kMaxTerm - 1);
    for (std::int32_t* p = buf; p < end; ++p) {
        const std::int32_t sam = d.a[static_cast<std::size_t>(m)];
        d.a[static_cast<std::size_t>(k)] = wrap(static_cast<std::int64_t>(applyWeight(d.weightA, sam)) + *p);
        updateWeight(d.weightA, d.delta, sam, *p);
        *p = d.a[static_cast<std::size_t>(k)];
        m = (m + 1) & (kMaxTerm - 1);
        k = (k + 1) & (kMaxTerm - 1);
    }
}

void stereoPass(Pass& d, std::int32_t* buf, std::int64_t frames) {
    std::int32_t* const end = buf + 2 * frames;
    auto add = [](std::int32_t w, std::int32_t s, std::int32_t r) { return wrap(static_cast<std::int64_t>(applyWeight(w, s)) + r); };
    switch (d.term) {
        case 17:
        case 18:
            for (std::int32_t* p = buf; p < end; p += 2) {
                std::int32_t sam = d.term == 17 ? wrap(2ll * d.a[0] - d.a[1]) : wrap((3ll * d.a[0] - d.a[1]) >> 1);
                d.a[1] = d.a[0];
                d.a[0] = add(d.weightA, sam, p[0]);
                updateWeight(d.weightA, d.delta, sam, p[0]);
                p[0] = d.a[0];
                sam = d.term == 17 ? wrap(2ll * d.b[0] - d.b[1]) : wrap((3ll * d.b[0] - d.b[1]) >> 1);
                d.b[1] = d.b[0];
                d.b[0] = add(d.weightB, sam, p[1]);
                updateWeight(d.weightB, d.delta, sam, p[1]);
                p[1] = d.b[0];
            }
            break;
        case -1:
            for (std::int32_t* p = buf; p < end; p += 2) {
                const std::int32_t samA = add(d.weightA, d.a[0], p[0]);
                updateWeightClip(d.weightA, d.delta, d.a[0], p[0]);
                p[0] = samA;
                d.a[0] = add(d.weightB, samA, p[1]);
                updateWeightClip(d.weightB, d.delta, samA, p[1]);
                p[1] = d.a[0];
            }
            break;
        case -2:
            for (std::int32_t* p = buf; p < end; p += 2) {
                const std::int32_t samB = add(d.weightB, d.b[0], p[1]);
                updateWeightClip(d.weightB, d.delta, d.b[0], p[1]);
                p[1] = samB;
                d.b[0] = add(d.weightA, samB, p[0]);
                updateWeightClip(d.weightA, d.delta, samB, p[0]);
                p[0] = d.b[0];
            }
            break;
        case -3:
            for (std::int32_t* p = buf; p < end; p += 2) {
                const std::int32_t samA = add(d.weightA, d.a[0], p[0]);
                updateWeightClip(d.weightA, d.delta, d.a[0], p[0]);
                const std::int32_t samB = add(d.weightB, d.b[0], p[1]);
                updateWeightClip(d.weightB, d.delta, d.b[0], p[1]);
                p[0] = d.b[0] = samA;
                p[1] = d.a[0] = samB;
            }
            break;
        default: {
            int m = 0, k = d.term & (kMaxTerm - 1);
            for (std::int32_t* p = buf; p < end; p += 2) {
                std::int32_t sam = d.a[static_cast<std::size_t>(m)];
                d.a[static_cast<std::size_t>(k)] = add(d.weightA, sam, p[0]);
                updateWeight(d.weightA, d.delta, sam, p[0]);
                p[0] = d.a[static_cast<std::size_t>(k)];
                sam = d.b[static_cast<std::size_t>(m)];
                d.b[static_cast<std::size_t>(k)] = add(d.weightB, sam, p[1]);
                updateWeight(d.weightB, d.delta, sam, p[1]);
                p[1] = d.b[static_cast<std::size_t>(k)];
                m = (m + 1) & (kMaxTerm - 1);
                k = (k + 1) & (kMaxTerm - 1);
            }
        }
    }
}

struct Block {
    std::uint32_t flags{0}, crc{0};
    std::int64_t index{0}, samples{0};
    const unsigned char* meta{nullptr};
    std::size_t metaSize{0};
};

struct Sub {
    int id;  // without the size flags
    const unsigned char* data;
    std::size_t size;
};

std::vector<Sub> subBlocks(const Block& b) {
    std::vector<Sub> out;
    std::size_t off = 0;
    while (off + 2 <= b.metaSize) {
        const unsigned char* h = b.meta + off;
        const int id = h[0];
        std::size_t words = h[1];
        off += 2;
        if (id & 0x80) {
            if (off + 2 > b.metaSize) throw std::runtime_error("WavPack: truncated metadata");
            words += (static_cast<std::size_t>(b.meta[off]) << 8) + (static_cast<std::size_t>(b.meta[off + 1]) << 16);
            off += 2;
        }
        const std::size_t bytes = words * 2;
        if (off + bytes > b.metaSize) throw std::runtime_error("WavPack: truncated metadata");
        const std::size_t size = (id & 0x40) && bytes ? bytes - 1 : bytes;
        out.push_back({id & 0x3f, b.meta + off, size});
        off += bytes;
    }
    return out;
}

// Chunks of an embedded RIFF header / trailer, without 'RIFF....WAVE' and without the 'data' chunk.
void appendChunks(const unsigned char* p, std::size_t n, std::vector<unsigned char>& out) {
    std::size_t off = 0;
    if (n >= 12 && (std::memcmp(p, "RIFF", 4) == 0 || std::memcmp(p, "RF64", 4) == 0)) off = 12;
    while (off + 8 <= n) {
        const std::uint32_t size = le32(p + off + 4);
        if (std::memcmp(p + off, "data", 4) == 0) {
            off += 8;  // the header ends with the data chunk's header: its body is the audio
            continue;
        }
        const std::size_t total = 8 + static_cast<std::size_t>(size) + (size & 1u);
        if (off + 8 + size > n) break;
        out.insert(out.end(), p + off, p + off + std::min(total, n - off));
        if (total > n - off) out.push_back(0);
        off += total;
    }
}

}  // namespace

bool isWavPack(const unsigned char* bytes, std::size_t size) noexcept { return size >= 32 && std::memcmp(bytes, "wvpk", 4) == 0; }

WavPackAudio decodeWavPack(const unsigned char* bytes, std::size_t size) {
    static const int kRates[15] = {6000, 8000, 9600, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 64000, 88200, 96000, 192000};
    std::vector<Block> blocks;
    std::size_t off = 0;
    while (off + 32 <= size) {
        const unsigned char* h = bytes + off;
        if (std::memcmp(h, "wvpk", 4) != 0) {
            // skip junk between blocks (ID3/APE tags at the end)
            const void* next = std::memchr(h + 1, 'w', size - off - 1);
            if (!next) break;
            off = static_cast<std::size_t>(static_cast<const unsigned char*>(next) - bytes);
            continue;
        }
        const std::uint32_t ck = le32(h + 4);
        const std::uint16_t version = le16(h + 8);
        if (ck < 24 || off + 8 + ck > size) throw std::runtime_error("WavPack: truncated block");
        if (version < 0x402 || version > 0x410) throw std::runtime_error("WavPack: unsupported stream version " + std::to_string(version));
        Block b;
        b.index = static_cast<std::int64_t>(le32(h + 16)) + (static_cast<std::int64_t>(h[10]) << 32);
        b.samples = le32(h + 20);
        b.flags = le32(h + 24);
        b.crc = le32(h + 28);
        b.meta = h + 32;
        b.metaSize = ck - 24;
        blocks.push_back(b);
        off += 8 + ck;
    }
    if (blocks.empty()) throw std::runtime_error("WavPack: no blocks");

    WavPackAudio out;
    // channel layout from the first group of blocks (INITIAL .. FINAL)
    int channels = 0;
    for (const Block& b : blocks) {
        if (b.samples == 0) continue;
        channels += (b.flags & kMonoFlag) && !(b.flags & kFalseStereo) ? 1 : 2;
        if (b.flags & kFinalBlock) break;
    }
    for (const Block& b : blocks) {
        if (b.flags & (kHybridFlag)) throw std::runtime_error("WavPack: hybrid (lossy) streams are not supported");
        if (b.flags & kFloatData) throw std::runtime_error("WavPack: float data is not supported (integer PCM only)");
        if (b.flags & kDsdFlag) throw std::runtime_error("WavPack: DSD audio is not supported");
    }
    std::int64_t frames = 0;
    for (const Block& b : blocks) frames = std::max(frames, b.index + b.samples);
    if (channels < 1 || channels > 64) throw std::runtime_error("WavPack: bad channel count");
    if (frames < 1) throw std::runtime_error("WavPack: no audio frames");
    if (frames * channels > (std::int64_t{1} << 31)) throw std::runtime_error("WavPack: file too long");
    out.channels = channels;
    out.frames = frames;
    out.samples.assign(static_cast<std::size_t>(frames * channels), 0);

    std::vector<std::int32_t> buf;
    int chan = 0;  // first output channel of the current block
    bool sawRate = false;
    for (const Block& b : blocks) {
        const auto subs = subBlocks(b);
        for (const Sub& s : subs) {
            if (s.id == (kIdRiffHeader & 0x3f) || s.id == (kIdRiffTrailer & 0x3f)) appendChunks(s.data, s.size, out.riff);
            if (s.id == (kIdSampleRate & 0x3f) && s.size >= 3) {
                out.rate = static_cast<double>(s.data[0] | (s.data[1] << 8) | (s.data[2] << 16));
                sawRate = true;
            }
        }
        if (b.samples == 0) continue;
        if (b.flags & kInitialBlock) chan = 0;
        const bool mono = (b.flags & kMonoData) != 0;
        const int blockChannels = (b.flags & kMonoFlag) && !(b.flags & kFalseStereo) ? 1 : 2;
        if (chan + blockChannels > channels) throw std::runtime_error("WavPack: inconsistent channel layout");
        const int bytesPer = static_cast<int>(b.flags & kBytesStored) + 1;
        out.bits = bytesPer * 8;
        const std::uint32_t srIndex = (b.flags & kSrateMask) >> kSrateLsb;
        if (!sawRate && srIndex < 15) out.rate = kRates[srIndex];

        Pass passes[kMaxTerms];
        int numTerms = 0;
        std::array<Entropy, 2> ent{};
        int sentBits = 0, zeros = 0, ones = 0, dups = 0;
        const Sub* stream = nullptr;
        for (const Sub& s : subs) {
            switch (s.id) {
                case kIdDecorrTerms: {
                    if (s.size > static_cast<std::size_t>(kMaxTerms)) throw std::runtime_error("WavPack: too many decorrelation terms");
                    numTerms = static_cast<int>(s.size);
                    for (int i = 0; i < numTerms; ++i) {
                        Pass& d = passes[numTerms - 1 - i];
                        d = Pass{};
                        d.term = static_cast<int>(s.data[i] & 0x1f) - 5;
                        d.delta = (s.data[i] >> 5) & 7;
                        if (d.term == 0 || d.term < -3 || (d.term > kMaxTerm && d.term < 17) || d.term > 18 || (mono && d.term < 0)) {
                            throw std::runtime_error("WavPack: bad decorrelation term");
                        }
                    }
                    break;
                }
                case kIdDecorrWeights: {
                    std::size_t count = mono ? s.size : s.size / 2;
                    if (count > static_cast<std::size_t>(numTerms)) throw std::runtime_error("WavPack: bad decorrelation weights");
                    const auto* p = reinterpret_cast<const signed char*>(s.data);
                    for (int i = numTerms - 1; i >= 0 && count; --i, --count) {
                        passes[i].weightA = restoreWeight(*p++);
                        if (!mono) passes[i].weightB = restoreWeight(*p++);
                    }
                    break;
                }
                case kIdDecorrSamples: {
                    const unsigned char* p = s.data;
                    const unsigned char* const e = s.data + s.size;
                    auto next = [&]() {
                        if (p + 2 > e) throw std::runtime_error("WavPack: bad decorrelation samples");
                        const std::int32_t v = exp2s(static_cast<std::int16_t>(le16(p)));
                        p += 2;
                        return v;
                    };
                    for (int i = numTerms - 1; i >= 0 && p < e; --i) {
                        Pass& d = passes[i];
                        if (d.term > kMaxTerm) {
                            d.a[0] = next();
                            d.a[1] = next();
                            if (!mono) {
                                d.b[0] = next();
                                d.b[1] = next();
                            }
                        } else if (d.term < 0) {
                            d.a[0] = next();
                            d.b[0] = next();
                        } else {
                            for (int m = 0; m < d.term; ++m) {
                                d.a[static_cast<std::size_t>(m)] = next();
                                if (!mono) d.b[static_cast<std::size_t>(m)] = next();
                            }
                        }
                    }
                    break;
                }
                case kIdEntropyVars: {
                    if (s.size != (mono ? 6u : 12u)) throw std::runtime_error("WavPack: bad entropy variables");
                    for (int c = 0; c < (mono ? 1 : 2); ++c) {
                        for (int k = 0; k < 3; ++k) {
                            ent[static_cast<std::size_t>(c)].median[static_cast<std::size_t>(k)] =
                                static_cast<std::uint32_t>(exp2s(le16(s.data + 6 * c + 2 * k)));
                        }
                    }
                    break;
                }
                case kIdInt32Info:
                    if (s.size >= 4) {
                        sentBits = s.data[0];
                        zeros = s.data[1];
                        ones = s.data[2];
                        dups = s.data[3];
                    }
                    break;
                case kIdWvBitstream:
                    stream = &s;
                    break;
                default:
                    break;
            }
        }
        if (!stream) throw std::runtime_error("WavPack: a block has no audio bitstream");
        if ((b.flags & kInt32Data) && sentBits) throw std::runtime_error("WavPack: 'int32 sent bits' streams are not supported");
        if (zeros > 31 || ones > 31 || dups > 31) throw std::runtime_error("WavPack: bad int32 info");
        const std::int64_t n = b.samples;
        const int perFrame = mono ? 1 : 2;
        buf.assign(static_cast<std::size_t>(n * perFrame), 0);
        Bits bs{stream->data, stream->data + stream->size};
        if (!getWords(bs, mono, ent, buf.data(), n * perFrame)) throw std::runtime_error("WavPack: corrupt bitstream");
        std::uint32_t crc = 0xffffffffu;
        if (mono) {
            for (int t = 0; t < numTerms; ++t) monoPass(passes[t], buf.data(), n);
            for (const std::int32_t v : buf) crc = crc * 3u + static_cast<std::uint32_t>(v);
        } else {
            for (int t = 0; t < numTerms; ++t) stereoPass(passes[t], buf.data(), n);
            if (b.flags & kJointStereo) {
                for (std::int64_t i = 0; i < n; ++i) {
                    std::int32_t& l = buf[static_cast<std::size_t>(2 * i)];
                    std::int32_t& r = buf[static_cast<std::size_t>(2 * i + 1)];
                    r = wrap(static_cast<std::int64_t>(r) - (l >> 1));
                    l = wrap(static_cast<std::int64_t>(l) + r);
                }
            }
            for (std::int64_t i = 0; i < n; ++i) {
                crc = crc * 3u + static_cast<std::uint32_t>(buf[static_cast<std::size_t>(2 * i)]);
                crc = crc * 3u + static_cast<std::uint32_t>(buf[static_cast<std::size_t>(2 * i + 1)]);
            }
        }
        if (crc != b.crc) throw std::runtime_error("WavPack: CRC mismatch in the block at sample " + std::to_string(b.index));
        // int32 info (lossless: zeros / ones / duplicates) and the block's shift
        int shift = static_cast<int>((b.flags & kShiftMask) >> kShiftLsb);
        for (auto& v : buf) {
            if (b.flags & kInt32Data) {
                if (zeros) v = wrap(static_cast<std::int64_t>(static_cast<std::uint32_t>(v) << zeros));
                else if (ones) v = wrap((static_cast<std::int64_t>(v) + 1) * (std::int64_t{1} << ones) - 1);
                else if (dups) v = wrap((static_cast<std::int64_t>(v) + (v & 1)) * (std::int64_t{1} << dups) - (v & 1));
            }
            if (shift) v = wrap(static_cast<std::int64_t>(static_cast<std::uint32_t>(v) << shift));
        }
        // into the interleaved output
        for (std::int64_t i = 0; i < n; ++i) {
            const std::int64_t f = b.index + i;
            if (f >= frames) break;
            std::int32_t* dst = out.samples.data() + f * channels + chan;
            if (mono) {
                dst[0] = buf[static_cast<std::size_t>(i)];
                if (blockChannels == 2) dst[1] = buf[static_cast<std::size_t>(i)];  // false stereo
            } else {
                dst[0] = buf[static_cast<std::size_t>(2 * i)];
                dst[1] = buf[static_cast<std::size_t>(2 * i + 1)];
            }
        }
        chan += blockChannels;
    }
    if (out.rate <= 0.0) throw std::runtime_error("WavPack: unknown sample rate");
    return out;
}

}  // namespace as::smp
