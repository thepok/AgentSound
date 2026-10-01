#include "analysis/Png.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <functional>
#include <iterator>
#include <queue>
#include <stdexcept>
#include <utility>

namespace as::analysis {

namespace {

// ---------------------------------------------------------------- checksums

const std::array<std::uint32_t, 256>& crcTable() {
    static const std::array<std::uint32_t, 256> table = [] {
        std::array<std::uint32_t, 256> t{};
        for (std::uint32_t n = 0; n < 256; ++n) {
            std::uint32_t c = n;
            for (int k = 0; k < 8; ++k) c = (c & 1u) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            t[n] = c;
        }
        return t;
    }();
    return table;
}

// ---------------------------------------------------------------- deflate tables (RFC 1951)

constexpr int kLenBase[29] = {3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31,
                              35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258};
constexpr int kLenExtra[29] = {0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2,
                               3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0};
constexpr int kDistBase[30] = {1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385,
                               513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577};
constexpr int kDistExtra[30] = {0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7,
                                8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13};
constexpr int kClOrder[19] = {16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15};

int lengthIndex(int len) noexcept {
    return static_cast<int>(std::upper_bound(std::begin(kLenBase), std::end(kLenBase), len) - std::begin(kLenBase)) - 1;
}
int distIndex(int dist) noexcept {
    return static_cast<int>(std::upper_bound(std::begin(kDistBase), std::end(kDistBase), dist) - std::begin(kDistBase)) - 1;
}

std::vector<std::uint8_t> fixedLitLengths() {
    std::vector<std::uint8_t> l(288);
    for (int i = 0; i < 288; ++i) l[static_cast<std::size_t>(i)] = i < 144 ? 8 : i < 256 ? 9 : i < 280 ? 7 : 8;
    return l;
}

// ---------------------------------------------------------------- encoder

struct BitWriter {
    std::vector<std::uint8_t>& out;
    std::uint64_t acc{0};
    int count{0};
    void put(std::uint32_t value, int bits) {
        acc |= static_cast<std::uint64_t>(value) << count;
        count += bits;
        while (count >= 8) { out.push_back(static_cast<std::uint8_t>(acc)); acc >>= 8; count -= 8; }
    }
    void align() {
        if (count > 0) out.push_back(static_cast<std::uint8_t>(acc));
        acc = 0;
        count = 0;
    }
};

std::uint32_t reverseBits(std::uint32_t code, int len) noexcept {
    std::uint32_t r = 0;
    for (int i = 0; i < len; ++i) { r = (r << 1) | (code & 1u); code >>= 1; }
    return r;
}

// Canonical Huffman codes, bit-reversed for LSB-first output.
std::vector<std::uint32_t> canonicalCodes(const std::vector<std::uint8_t>& lens) {
    int blCount[16] = {};
    for (auto l : lens) if (l) ++blCount[l];
    std::uint32_t next[16] = {};
    std::uint32_t code = 0;
    for (int b = 1; b < 16; ++b) { code = (code + static_cast<std::uint32_t>(blCount[b - 1])) << 1; next[b] = code; }
    std::vector<std::uint32_t> codes(lens.size(), 0);
    for (std::size_t i = 0; i < lens.size(); ++i)
        if (lens[i]) codes[i] = reverseBits(next[lens[i]]++, lens[i]);
    return codes;
}

// Huffman code lengths limited to maxLen (frequencies are flattened until the tree fits).
std::vector<std::uint8_t> huffmanLengths(std::vector<std::uint32_t> freq, int maxLen) {
    std::vector<std::uint8_t> lens(freq.size(), 0);
    for (;;) {
        std::vector<int> syms;
        for (std::size_t i = 0; i < freq.size(); ++i) if (freq[i]) syms.push_back(static_cast<int>(i));
        if (syms.empty()) return lens;
        if (syms.size() == 1) { lens[static_cast<std::size_t>(syms[0])] = 1; return lens; }
        std::vector<std::uint64_t> weight;
        std::vector<int> parent;
        using Item = std::pair<std::uint64_t, int>;
        std::priority_queue<Item, std::vector<Item>, std::greater<Item>> pq;
        for (int s : syms) {
            pq.push({freq[static_cast<std::size_t>(s)], static_cast<int>(weight.size())});
            weight.push_back(freq[static_cast<std::size_t>(s)]);
            parent.push_back(-1);
        }
        while (pq.size() > 1) {
            const Item a = pq.top(); pq.pop();
            const Item b = pq.top(); pq.pop();
            const int id = static_cast<int>(weight.size());
            weight.push_back(a.first + b.first);
            parent.push_back(-1);
            parent[static_cast<std::size_t>(a.second)] = id;
            parent[static_cast<std::size_t>(b.second)] = id;
            pq.push({weight.back(), id});
        }
        int maxDepth = 0;
        std::vector<int> depth(syms.size());
        for (std::size_t k = 0; k < syms.size(); ++k) {
            int d = 0;
            for (int p = static_cast<int>(k); parent[static_cast<std::size_t>(p)] >= 0; p = parent[static_cast<std::size_t>(p)]) ++d;
            depth[k] = d;
            maxDepth = std::max(maxDepth, d);
        }
        if (maxDepth <= maxLen) {
            for (std::size_t k = 0; k < syms.size(); ++k) lens[static_cast<std::size_t>(syms[k])] = static_cast<std::uint8_t>(depth[k]);
            return lens;
        }
        for (auto& f : freq) if (f) f = (f >> 1) | 1u;
    }
}

struct Sym {
    std::uint16_t value;  // literal byte, or match length when dist != 0
    std::uint16_t dist;
};

void writeBlock(BitWriter& bw, const std::vector<Sym>& syms, const std::uint8_t* raw, std::size_t begin,
                std::size_t end, bool final) {
    std::vector<std::uint32_t> litFreq(286, 0), distFreq(30, 0);
    std::uint64_t extraBits = 0;
    for (const Sym& s : syms) {
        if (!s.dist) { ++litFreq[s.value]; continue; }
        const int li = lengthIndex(s.value), di = distIndex(s.dist);
        ++litFreq[static_cast<std::size_t>(257 + li)];
        ++distFreq[static_cast<std::size_t>(di)];
        extraBits += static_cast<std::uint64_t>(kLenExtra[li] + kDistExtra[di]);
    }
    litFreq[256] = 1;

    // Dynamic Huffman candidate.
    auto dFreq = distFreq;
    {
        int used = 0;
        for (auto f : dFreq) used += f ? 1 : 0;
        if (used < 2) { if (!dFreq[0]) dFreq[0] = 1; else dFreq[1] = 1; }  // keep >= 2 codes for picky decoders
    }
    const auto litLens = huffmanLengths(litFreq, 15);
    const auto distLens = huffmanLengths(dFreq, 15);
    int hlit = 286, hdist = 30;
    while (hlit > 257 && !litLens[static_cast<std::size_t>(hlit - 1)]) --hlit;
    while (hdist > 1 && !distLens[static_cast<std::size_t>(hdist - 1)]) --hdist;
    std::vector<std::uint8_t> all(litLens.begin(), litLens.begin() + hlit);
    all.insert(all.end(), distLens.begin(), distLens.begin() + hdist);
    std::vector<std::pair<int, int>> rle;  // (symbol 0..18, extra value)
    for (std::size_t i = 0; i < all.size();) {
        const int l = all[i];
        std::size_t run = 1;
        while (i + run < all.size() && all[i + run] == l) ++run;
        if (l == 0) {
            std::size_t left = run;
            while (left >= 11) { const std::size_t r = std::min<std::size_t>(left, 138); rle.push_back({18, static_cast<int>(r - 11)}); left -= r; }
            if (left >= 3) { rle.push_back({17, static_cast<int>(left - 3)}); left = 0; }
            while (left--) rle.push_back({0, 0});
        } else {
            rle.push_back({l, 0});
            std::size_t left = run - 1;
            while (left >= 3) { const std::size_t r = std::min<std::size_t>(left, 6); rle.push_back({16, static_cast<int>(r - 3)}); left -= r; }
            while (left--) rle.push_back({l, 0});
        }
        i += run;
    }
    std::vector<std::uint32_t> clFreq(19, 0);
    for (auto& [sym, extra] : rle) ++clFreq[static_cast<std::size_t>(sym)];
    const auto clLens = huffmanLengths(clFreq, 7);
    int hclen = 19;
    while (hclen > 4 && !clLens[static_cast<std::size_t>(kClOrder[hclen - 1])]) --hclen;

    std::uint64_t dynBits = 3 + 5 + 5 + 4 + 3ull * static_cast<std::uint64_t>(hclen) + extraBits;
    for (auto& [sym, extra] : rle) dynBits += clLens[static_cast<std::size_t>(sym)] + (sym == 16 ? 2 : sym == 17 ? 3 : sym == 18 ? 7 : 0);
    for (std::size_t i = 0; i < litFreq.size(); ++i) dynBits += static_cast<std::uint64_t>(litFreq[i]) * litLens[i];
    for (std::size_t i = 0; i < distFreq.size(); ++i) dynBits += static_cast<std::uint64_t>(distFreq[i]) * distLens[i];

    static const auto fixedLit = fixedLitLengths();
    std::uint64_t fixedBits = 3 + extraBits;
    for (std::size_t i = 0; i < litFreq.size(); ++i) fixedBits += static_cast<std::uint64_t>(litFreq[i]) * fixedLit[i];
    for (auto f : distFreq) fixedBits += 5ull * f;

    const std::size_t rawLen = end - begin;
    const std::uint64_t storedBits = (rawLen / 65535 + 1) * 40ull + 8ull * rawLen;

    if (storedBits < dynBits && storedBits < fixedBits) {
        std::size_t pos = begin;
        do {
            const std::size_t len = std::min<std::size_t>(65535, end - pos);
            const bool last = final && pos + len == end;
            bw.put(last ? 1u : 0u, 1);
            bw.put(0, 2);
            bw.align();
            bw.put(static_cast<std::uint32_t>(len), 16);
            bw.put(static_cast<std::uint32_t>(~len & 0xFFFFu), 16);
            bw.out.insert(bw.out.end(), raw + pos, raw + pos + len);
            pos += len;
        } while (pos < end);
        return;
    }

    const bool useDynamic = dynBits < fixedBits;
    std::vector<std::uint8_t> ll, dl;
    if (useDynamic) {
        ll = litLens;
        dl = distLens;
        bw.put(final ? 1u : 0u, 1);
        bw.put(2, 2);
        bw.put(static_cast<std::uint32_t>(hlit - 257), 5);
        bw.put(static_cast<std::uint32_t>(hdist - 1), 5);
        bw.put(static_cast<std::uint32_t>(hclen - 4), 4);
        for (int i = 0; i < hclen; ++i) bw.put(clLens[static_cast<std::size_t>(kClOrder[i])], 3);
        const auto clCodes = canonicalCodes(clLens);
        for (auto& [sym, extra] : rle) {
            bw.put(clCodes[static_cast<std::size_t>(sym)], clLens[static_cast<std::size_t>(sym)]);
            if (sym == 16) bw.put(static_cast<std::uint32_t>(extra), 2);
            else if (sym == 17) bw.put(static_cast<std::uint32_t>(extra), 3);
            else if (sym == 18) bw.put(static_cast<std::uint32_t>(extra), 7);
        }
    } else {
        ll = fixedLit;
        dl.assign(30, 5);
        bw.put(final ? 1u : 0u, 1);
        bw.put(1, 2);
    }
    const auto litCodes = canonicalCodes(ll);
    const auto distCodes = canonicalCodes(dl);
    for (const Sym& s : syms) {
        if (!s.dist) { bw.put(litCodes[s.value], ll[s.value]); continue; }
        const int li = lengthIndex(s.value), di = distIndex(s.dist);
        const auto lsym = static_cast<std::size_t>(257 + li);
        bw.put(litCodes[lsym], ll[lsym]);
        if (kLenExtra[li]) bw.put(static_cast<std::uint32_t>(s.value - kLenBase[li]), kLenExtra[li]);
        bw.put(distCodes[static_cast<std::size_t>(di)], dl[static_cast<std::size_t>(di)]);
        if (kDistExtra[di]) bw.put(static_cast<std::uint32_t>(s.dist - kDistBase[di]), kDistExtra[di]);
    }
    bw.put(litCodes[256], ll[256]);
}

// ---------------------------------------------------------------- decoder

struct BitReader {
    const std::uint8_t* data;
    std::size_t size;
    std::size_t pos{0};
    std::uint32_t buf{0};
    int count{0};
    std::uint32_t bits(int need) {
        while (count < need) {
            if (pos >= size) throw std::runtime_error("inflate: unexpected end of data");
            buf |= static_cast<std::uint32_t>(data[pos++]) << count;
            count += 8;
        }
        const std::uint32_t v = need ? buf & ((1u << need) - 1u) : 0u;
        buf >>= need;
        count -= need;
        return v;
    }
    void align() { buf = 0; count = 0; }
};

struct Huffman {
    std::array<int, 16> count{};
    std::vector<int> symbol;
    void build(const std::uint8_t* lens, int n) {
        count.fill(0);
        for (int i = 0; i < n; ++i) ++count[lens[i]];
        count[0] = 0;
        int left = 1;
        for (int len = 1; len < 16; ++len) {
            left = (left << 1) - count[static_cast<std::size_t>(len)];
            if (left < 0) throw std::runtime_error("inflate: over-subscribed Huffman code");
        }
        std::array<int, 16> offs{};
        for (int len = 1; len < 15; ++len) offs[static_cast<std::size_t>(len + 1)] = offs[static_cast<std::size_t>(len)] + count[static_cast<std::size_t>(len)];
        symbol.assign(static_cast<std::size_t>(n), 0);
        for (int i = 0; i < n; ++i)
            if (lens[i]) symbol[static_cast<std::size_t>(offs[lens[i]]++)] = i;
    }
    int decode(BitReader& br) const {
        int code = 0, first = 0, index = 0;
        for (int len = 1; len < 16; ++len) {
            code |= static_cast<int>(br.bits(1));
            const int c = count[static_cast<std::size_t>(len)];
            if (code - c < first) return symbol[static_cast<std::size_t>(index + (code - first))];
            index += c;
            first += c;
            first <<= 1;
            code <<= 1;
        }
        throw std::runtime_error("inflate: invalid Huffman code");
    }
};

std::size_t inflateImpl(const std::uint8_t* data, std::size_t n, std::vector<std::uint8_t>& out) {
    BitReader br{data, n};
    static const auto fixed = [] {
        std::pair<Huffman, Huffman> h;
        const auto lit = fixedLitLengths();
        h.first.build(lit.data(), 288);
        std::uint8_t d[30];
        std::fill(std::begin(d), std::end(d), static_cast<std::uint8_t>(5));
        h.second.build(d, 30);
        return h;
    }();
    bool final = false;
    do {
        final = br.bits(1) != 0;
        const std::uint32_t type = br.bits(2);
        if (type == 0) {
            br.align();
            const std::uint32_t len = br.bits(16), nlen = br.bits(16);
            if ((len ^ 0xFFFFu) != nlen) throw std::runtime_error("inflate: stored block length mismatch");
            if (br.pos + len > n) throw std::runtime_error("inflate: stored block overruns input");
            out.insert(out.end(), data + br.pos, data + br.pos + len);
            br.pos += len;
            continue;
        }
        if (type == 3) throw std::runtime_error("inflate: invalid block type");
        Huffman dynLit, dynDist;
        const Huffman* lit = &fixed.first;
        const Huffman* dist = &fixed.second;
        if (type == 2) {
            const int hlit = static_cast<int>(br.bits(5)) + 257, hdist = static_cast<int>(br.bits(5)) + 1;
            const int hclen = static_cast<int>(br.bits(4)) + 4;
            std::uint8_t cl[19] = {};
            for (int i = 0; i < hclen; ++i) cl[kClOrder[i]] = static_cast<std::uint8_t>(br.bits(3));
            Huffman clh;
            clh.build(cl, 19);
            std::vector<std::uint8_t> lens;
            while (static_cast<int>(lens.size()) < hlit + hdist) {
                const int sym = clh.decode(br);
                if (sym < 16) { lens.push_back(static_cast<std::uint8_t>(sym)); continue; }
                std::uint8_t val = 0;
                int rep = 0;
                if (sym == 16) {
                    if (lens.empty()) throw std::runtime_error("inflate: repeat with no previous length");
                    val = lens.back();
                    rep = 3 + static_cast<int>(br.bits(2));
                } else if (sym == 17) {
                    rep = 3 + static_cast<int>(br.bits(3));
                } else {
                    rep = 11 + static_cast<int>(br.bits(7));
                }
                if (static_cast<int>(lens.size()) + rep > hlit + hdist) throw std::runtime_error("inflate: too many code lengths");
                lens.insert(lens.end(), static_cast<std::size_t>(rep), val);
            }
            dynLit.build(lens.data(), hlit);
            dynDist.build(lens.data() + hlit, hdist);
            lit = &dynLit;
            dist = &dynDist;
        }
        for (;;) {
            const int sym = lit->decode(br);
            if (sym < 256) { out.push_back(static_cast<std::uint8_t>(sym)); continue; }
            if (sym == 256) break;
            const int li = sym - 257;
            if (li >= 29) throw std::runtime_error("inflate: invalid length symbol");
            const int len = kLenBase[li] + static_cast<int>(br.bits(kLenExtra[li]));
            const int ds = dist->decode(br);
            if (ds >= 30) throw std::runtime_error("inflate: invalid distance symbol");
            const std::size_t d = static_cast<std::size_t>(kDistBase[ds]) + br.bits(kDistExtra[ds]);
            if (d > out.size()) throw std::runtime_error("inflate: distance too far back");
            const std::size_t from = out.size() - d;
            for (int k = 0; k < len; ++k) out.push_back(out[from + static_cast<std::size_t>(k)]);
        }
    } while (!final);
    return br.pos;  // bytes consumed (the final partial byte counts as consumed)
}

void putBE32(std::vector<std::uint8_t>& v, std::uint32_t x) {
    v.push_back(static_cast<std::uint8_t>(x >> 24));
    v.push_back(static_cast<std::uint8_t>(x >> 16));
    v.push_back(static_cast<std::uint8_t>(x >> 8));
    v.push_back(static_cast<std::uint8_t>(x));
}
std::uint32_t getBE32(const std::uint8_t* p) {
    return (static_cast<std::uint32_t>(p[0]) << 24) | (static_cast<std::uint32_t>(p[1]) << 16) |
           (static_cast<std::uint32_t>(p[2]) << 8) | static_cast<std::uint32_t>(p[3]);
}

void putChunk(std::vector<std::uint8_t>& png, const char* type, const std::vector<std::uint8_t>& data) {
    putBE32(png, static_cast<std::uint32_t>(data.size()));
    const std::size_t start = png.size();
    png.insert(png.end(), type, type + 4);
    png.insert(png.end(), data.begin(), data.end());
    putBE32(png, crc32(png.data() + start, png.size() - start));
}

constexpr std::uint8_t kSignature[8] = {137, 80, 78, 71, 13, 10, 26, 10};

int paeth(int a, int b, int c) noexcept {
    const int p = a + b - c;
    const int pa = std::abs(p - a), pb = std::abs(p - b), pc = std::abs(p - c);
    if (pa <= pb && pa <= pc) return a;
    return pb <= pc ? b : c;
}

}  // namespace

std::uint32_t crc32(const std::uint8_t* data, std::size_t n, std::uint32_t crc) noexcept {
    const auto& t = crcTable();
    crc = ~crc;
    for (std::size_t i = 0; i < n; ++i) crc = t[(crc ^ data[i]) & 0xFFu] ^ (crc >> 8);
    return ~crc;
}

std::uint32_t adler32(const std::uint8_t* data, std::size_t n, std::uint32_t adler) noexcept {
    std::uint32_t a = adler & 0xFFFFu, b = adler >> 16;
    while (n > 0) {
        const std::size_t chunk = std::min<std::size_t>(n, 5552);
        for (std::size_t i = 0; i < chunk; ++i) { a += data[i]; b += a; }
        a %= 65521u;
        b %= 65521u;
        data += chunk;
        n -= chunk;
    }
    return (b << 16) | a;
}

std::vector<std::uint8_t> deflateCompress(const std::uint8_t* d, std::size_t n) {
    std::vector<std::uint8_t> out;
    BitWriter bw{out};
    if (n == 0) {  // single final fixed block holding only end-of-block
        bw.put(1, 1);
        bw.put(1, 2);
        bw.put(0, 7);
        bw.align();
        return out;
    }
    constexpr int kHashBits = 16, kWindow = 32768, kMaxChain = 32, kNiceLen = 96, kLazyMax = 32, kBlockSyms = 1 << 16;
    constexpr std::size_t kWinMask = kWindow - 1;
    std::vector<std::int32_t> head(std::size_t{1} << kHashBits, -1), prev(kWindow, -1);
    auto hashAt = [&](std::size_t i) -> std::uint32_t {
        const std::uint32_t v = (static_cast<std::uint32_t>(d[i]) << 16) | (static_cast<std::uint32_t>(d[i + 1]) << 8) | d[i + 2];
        return (v * 2654435761u) >> (32 - kHashBits);
    };
    auto insert = [&](std::size_t i) {
        if (i + 2 >= n) return;
        const std::uint32_t h = hashAt(i);
        prev[i & kWinMask] = head[h];
        head[h] = static_cast<std::int32_t>(i);
    };
    auto findMatch = [&](std::size_t i, int& bestLen, int& bestDist) {
        bestLen = 0;
        bestDist = 0;
        const std::size_t maxLen = std::min<std::size_t>(258, n - i);
        if (maxLen < 3) return;
        std::size_t best = 2;
        std::int32_t j = head[hashAt(i)];
        int chain = kMaxChain;
        while (j >= 0 && chain-- > 0) {
            const std::size_t dist = i - static_cast<std::size_t>(j);
            if (dist > static_cast<std::size_t>(kWindow)) break;
            const std::uint8_t* a = d + j;
            const std::uint8_t* b = d + i;
            if (a[best] == b[best] && a[0] == b[0] && a[1] == b[1]) {
                std::size_t l = 2;
                while (l < maxLen && a[l] == b[l]) ++l;
                if (l > best) {
                    best = l;
                    bestDist = static_cast<int>(dist);
                    if (l >= maxLen || l >= static_cast<std::size_t>(kNiceLen)) break;
                }
            }
            j = prev[static_cast<std::size_t>(j) & kWinMask];
        }
        if (best >= 3) bestLen = static_cast<int>(best);
    };

    std::vector<Sym> syms;
    syms.reserve(kBlockSyms + 4);
    std::size_t blockStart = 0;
    std::size_t i = 0;
    bool havePrev = false;
    int prevLen = 0, prevDist = 0;
    while (i < n) {
        if (!havePrev && syms.size() >= static_cast<std::size_t>(kBlockSyms)) {
            writeBlock(bw, syms, d, blockStart, i, false);
            syms.clear();
            blockStart = i;
        }
        int len = 0, dist = 0;
        if (i + 2 < n) findMatch(i, len, dist);
        insert(i);
        if (havePrev && prevLen >= len) {  // the match found one byte earlier wins
            syms.push_back({static_cast<std::uint16_t>(prevLen), static_cast<std::uint16_t>(prevDist)});
            const std::size_t end = i - 1 + static_cast<std::size_t>(prevLen);
            for (std::size_t k = i + 1; k < end; ++k) insert(k);
            i = end;
            havePrev = false;
            continue;
        }
        if (havePrev) syms.push_back({d[i - 1], 0});
        if (len >= kLazyMax) {  // long enough: take it without looking one byte ahead
            syms.push_back({static_cast<std::uint16_t>(len), static_cast<std::uint16_t>(dist)});
            const std::size_t end = i + static_cast<std::size_t>(len);
            for (std::size_t k = i + 1; k < end; ++k) insert(k);
            i = end;
            havePrev = false;
            continue;
        }
        if (len >= 3) {
            havePrev = true;
            prevLen = len;
            prevDist = dist;
        } else {
            syms.push_back({d[i], 0});
            havePrev = false;
        }
        ++i;
    }
    if (havePrev) syms.push_back({d[n - 1], 0});  // unreachable in practice (a match needs 3 bytes)
    writeBlock(bw, syms, d, blockStart, n, true);
    bw.align();
    return out;
}

std::vector<std::uint8_t> inflateDecompress(const std::uint8_t* data, std::size_t n) {
    std::vector<std::uint8_t> out;
    inflateImpl(data, n, out);
    return out;
}

std::vector<std::uint8_t> zlibCompress(const std::uint8_t* data, std::size_t n) {
    std::vector<std::uint8_t> out = {0x78, 0xDA};
    const auto body = deflateCompress(data, n);
    out.insert(out.end(), body.begin(), body.end());
    putBE32(out, adler32(data, n));
    return out;
}

std::vector<std::uint8_t> zlibDecompress(const std::uint8_t* data, std::size_t n) {
    if (n < 6) throw std::runtime_error("zlib: stream too short");
    if ((data[0] & 0x0F) != 8 || ((data[0] << 8) | data[1]) % 31 != 0 || (data[1] & 0x20))
        throw std::runtime_error("zlib: bad header");
    std::vector<std::uint8_t> out;
    const std::size_t used = inflateImpl(data + 2, n - 2, out);
    if (2 + used + 4 > n) throw std::runtime_error("zlib: missing Adler-32");
    if (getBE32(data + 2 + used) != adler32(out.data(), out.size())) throw std::runtime_error("zlib: Adler-32 mismatch");
    return out;
}

std::vector<std::uint8_t> encodePng(const Image& img) {
    if (img.width <= 0 || img.height <= 0 ||
        img.rgb.size() != static_cast<std::size_t>(img.width) * static_cast<std::size_t>(img.height) * 3)
        throw std::runtime_error("encodePng: invalid image");
    const std::size_t stride = static_cast<std::size_t>(img.width) * 3;
    std::vector<std::uint8_t> raw;
    raw.reserve((stride + 1) * static_cast<std::size_t>(img.height));
    std::vector<std::uint8_t> zeros(stride, 0), cand[5];
    for (auto& c : cand) c.resize(stride);
    for (int y = 0; y < img.height; ++y) {
        const std::uint8_t* cur = img.rgb.data() + static_cast<std::size_t>(y) * stride;
        const std::uint8_t* up = y ? cur - stride : zeros.data();
        // Candidate rows for the five PNG filters (none, sub, up, average, Paeth).
        for (std::size_t i = 0; i < stride; ++i) {
            const int a = i >= 3 ? cur[i - 3] : 0, b = up[i], c = i >= 3 ? up[i - 3] : 0;
            cand[0][i] = cur[i];
            cand[1][i] = static_cast<std::uint8_t>(cur[i] - a);
            cand[2][i] = static_cast<std::uint8_t>(cur[i] - b);
            cand[3][i] = static_cast<std::uint8_t>(cur[i] - ((a + b) >> 1));
            cand[4][i] = static_cast<std::uint8_t>(cur[i] - paeth(a, b, c));
        }
        // Pick the filter with the smallest sum of |signed bytes| (the usual heuristic).
        std::uint64_t bestScore = ~0ull;
        int best = 0;
        for (int f = 0; f < 5; ++f) {
            std::uint64_t score = 0;
            for (std::size_t i = 0; i < stride; ++i) {
                const std::uint8_t v = cand[f][i];
                score += v < 128 ? v : 256u - v;
            }
            if (score < bestScore) { bestScore = score; best = f; }
        }
        raw.push_back(static_cast<std::uint8_t>(best));
        raw.insert(raw.end(), cand[best].begin(), cand[best].end());
    }
    std::vector<std::uint8_t> png(std::begin(kSignature), std::end(kSignature));
    std::vector<std::uint8_t> ihdr;
    putBE32(ihdr, static_cast<std::uint32_t>(img.width));
    putBE32(ihdr, static_cast<std::uint32_t>(img.height));
    ihdr.insert(ihdr.end(), {8, 2, 0, 0, 0});  // 8-bit, RGB, deflate, adaptive filtering, no interlace
    putChunk(png, "IHDR", ihdr);
    putChunk(png, "IDAT", zlibCompress(raw.data(), raw.size()));
    putChunk(png, "IEND", {});
    return png;
}

Image decodePng(const std::vector<std::uint8_t>& png) {
    if (png.size() < 8 || !std::equal(std::begin(kSignature), std::end(kSignature), png.begin()))
        throw std::runtime_error("png: bad signature");
    std::size_t pos = 8;
    int width = 0, height = 0, channels = 0;
    bool sawHeader = false, sawEnd = false;
    std::vector<std::uint8_t> idat;
    while (pos + 12 <= png.size()) {
        const std::uint32_t len = getBE32(png.data() + pos);
        if (pos + 12 + len > png.size()) throw std::runtime_error("png: chunk overruns file");
        const std::uint8_t* type = png.data() + pos + 4;
        const std::uint8_t* body = type + 4;
        if (getBE32(body + len) != crc32(type, len + 4)) throw std::runtime_error("png: chunk CRC mismatch");
        const std::string t(reinterpret_cast<const char*>(type), 4);
        if (t == "IHDR") {
            if (len != 13) throw std::runtime_error("png: bad IHDR");
            width = static_cast<int>(getBE32(body));
            height = static_cast<int>(getBE32(body + 4));
            if (body[8] != 8 || (body[9] != 2 && body[9] != 6) || body[10] || body[11] || body[12])
                throw std::runtime_error("png: only 8-bit non-interlaced RGB/RGBA is supported");
            channels = body[9] == 2 ? 3 : 4;
            sawHeader = true;
        } else if (t == "IDAT") {
            idat.insert(idat.end(), body, body + len);
        } else if (t == "IEND") {
            sawEnd = true;
            break;
        }
        pos += 12 + len;
    }
    if (!sawHeader || !sawEnd || width <= 0 || height <= 0) throw std::runtime_error("png: missing IHDR/IEND");
    const auto raw = zlibDecompress(idat.data(), idat.size());
    const std::size_t stride = static_cast<std::size_t>(width) * static_cast<std::size_t>(channels);
    if (raw.size() != (stride + 1) * static_cast<std::size_t>(height)) throw std::runtime_error("png: wrong data size");
    std::vector<std::uint8_t> cur(stride), prevRow(stride, 0);
    Image img;
    img.width = width;
    img.height = height;
    img.rgb.resize(static_cast<std::size_t>(width) * static_cast<std::size_t>(height) * 3);
    const std::size_t bpp = static_cast<std::size_t>(channels);
    for (int y = 0; y < height; ++y) {
        const std::uint8_t* row = raw.data() + static_cast<std::size_t>(y) * (stride + 1);
        const int f = row[0];
        if (f > 4) throw std::runtime_error("png: bad filter type");
        for (std::size_t i = 0; i < stride; ++i) {
            const int a = i >= bpp ? cur[i - bpp] : 0, b = prevRow[i], c = i >= bpp ? prevRow[i - bpp] : 0;
            int pred = 0;
            switch (f) {
                case 1: pred = a; break;
                case 2: pred = b; break;
                case 3: pred = (a + b) >> 1; break;
                case 4: pred = paeth(a, b, c); break;
                default: break;
            }
            cur[i] = static_cast<std::uint8_t>(row[1 + i] + pred);
        }
        for (int x = 0; x < width; ++x)
            for (int ch = 0; ch < 3; ++ch)
                img.rgb[(static_cast<std::size_t>(y) * static_cast<std::size_t>(width) + static_cast<std::size_t>(x)) * 3 + static_cast<std::size_t>(ch)] =
                    cur[static_cast<std::size_t>(x) * bpp + static_cast<std::size_t>(ch)];
        std::swap(cur, prevRow);
    }
    return img;
}

void writePng(const std::string& path, const Image& image) {
    const auto bytes = encodePng(image);
    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    if (!f) throw std::runtime_error("cannot open '" + path + "' for writing");
    f.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    if (!f) throw std::runtime_error("failed writing '" + path + "'");
}

std::vector<std::uint8_t> readFileBytes(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open '" + path + "'");
    return std::vector<std::uint8_t>(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
}

}  // namespace as::analysis
