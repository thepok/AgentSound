#include "instruments/Sf2File.h"

#include "core/Params.h"

#include <algorithm>
#include <bit>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <sstream>

namespace as::sf2 {
namespace {

static_assert(std::endian::native == std::endian::little, "the SoundFont loader assumes a little-endian host");

namespace fs = std::filesystem;

struct FileCloser {
    void operator()(std::FILE* f) const noexcept { if (f) std::fclose(f); }
};
using FilePtr = std::unique_ptr<std::FILE, FileCloser>;

int seek64(std::FILE* f, std::int64_t off) {
#ifdef _WIN32
    return _fseeki64(f, off, SEEK_SET);
#else
    return fseeko(f, static_cast<off_t>(off), SEEK_SET);
#endif
}

std::int64_t fileSize64(std::FILE* f) {
#ifdef _WIN32
    if (_fseeki64(f, 0, SEEK_END) != 0) return -1;
    return _ftelli64(f);
#else
    if (fseeko(f, 0, SEEK_END) != 0) return -1;
    return static_cast<std::int64_t>(ftello(f));
#endif
}

std::uint16_t u16(const unsigned char* p) { return static_cast<std::uint16_t>(p[0] | (p[1] << 8)); }
std::uint32_t u32(const unsigned char* p) {
    return static_cast<std::uint32_t>(p[0]) | (static_cast<std::uint32_t>(p[1]) << 8) |
           (static_cast<std::uint32_t>(p[2]) << 16) | (static_cast<std::uint32_t>(p[3]) << 24);
}

std::string fixedString(const unsigned char* p, std::size_t n) {
    std::size_t len = 0;
    while (len < n && p[len] != 0) ++len;
    std::string s(reinterpret_cast<const char*>(p), len);
    while (!s.empty() && std::isspace(static_cast<unsigned char>(s.back()))) s.pop_back();
    for (auto& c : s) {
        if (static_cast<unsigned char>(c) < 32) c = ' ';
    }
    return s;
}

struct Chunk {
    std::string id;
    std::int64_t data{0};  // offset of the chunk data
    std::uint32_t size{0};
};

struct RawGen {
    std::uint16_t oper, amount;
};
struct RawBag {
    std::uint16_t gen, mod;
};

class Parser {
public:
    explicit Parser(std::string path) : path_(std::move(path)) {}

    std::shared_ptr<File> parse() {
        file_.reset(std::fopen(path_.c_str(), "rb"));
        if (!file_) fail("cannot open the file");
        size_ = fileSize64(file_.get());
        if (size_ < 12) fail("too short for a SoundFont (RIFF sfbk) file");
        unsigned char head[12];
        read(0, head, 12);
        if (std::memcmp(head, "RIFF", 4) != 0) fail("not a RIFF file");
        if (std::memcmp(head + 8, "sfbk", 4) != 0) fail("not a SoundFont: RIFF form type is not 'sfbk'");
        const std::int64_t end = 8 + static_cast<std::int64_t>(u32(head + 4));
        if (end > size_) fail("truncated: the RIFF header announces " + std::to_string(end) + " bytes, the file has " + std::to_string(size_));

        auto out = std::make_shared<File>();
        out->path = path_;
        const Chunk* info = nullptr;
        const Chunk* sdta = nullptr;
        const Chunk* pdta = nullptr;
        std::vector<Chunk> lists;
        for (const Chunk& c : chunks(12, end, "the RIFF body")) {
            if (c.id != "LIST") continue;  // unknown top-level chunks are allowed and skipped
            if (c.size < 4) fail("LIST chunk too short");
            unsigned char type[4];
            read(c.data, type, 4);
            Chunk l = c;
            l.id = std::string(reinterpret_cast<const char*>(type), 4);
            lists.push_back(l);
        }
        for (const Chunk& l : lists) {
            if (l.id == "INFO") info = &l;
            else if (l.id == "sdta") sdta = &l;
            else if (l.id == "pdta") pdta = &l;
        }
        if (!sdta) fail("no 'sdta' (sample data) LIST chunk");
        if (!pdta) fail("no 'pdta' (preset data) LIST chunk");
        if (info) parseInfo(*info, *out);
        parseSdta(*sdta, *out);
        parsePdta(*pdta, *out);
        return out;
    }

private:
    [[noreturn]] void fail(const std::string& why) const { throw ConfigError("soundfont '" + path_ + "': " + why); }

    void read(std::int64_t off, void* dst, std::size_t n) {
        if (off < 0 || off + static_cast<std::int64_t>(n) > size_) fail("truncated file (read past the end at offset " + std::to_string(off) + ")");
        if (seek64(file_.get(), off) != 0 || std::fread(dst, 1, n, file_.get()) != n) fail("read error at offset " + std::to_string(off));
    }

    std::vector<Chunk> chunks(std::int64_t begin, std::int64_t end, const std::string& where) {
        std::vector<Chunk> out;
        std::int64_t off = begin;
        while (off + 8 <= end) {
            unsigned char h[8];
            read(off, h, 8);
            Chunk c;
            c.id = std::string(reinterpret_cast<const char*>(h), 4);
            c.size = u32(h + 4);
            c.data = off + 8;
            if (c.data + static_cast<std::int64_t>(c.size) > end) {
                fail("chunk '" + c.id + "' in " + where + " (offset " + std::to_string(off) + ", " + std::to_string(c.size) +
                     " bytes) extends past its container");
            }
            out.push_back(c);
            off = c.data + c.size + (c.size & 1u);
        }
        return out;
    }

    void parseInfo(const Chunk& list, File& out) {
        for (const Chunk& c : chunks(list.data + 4, list.data + list.size, "INFO")) {
            if (c.id == "ifil") {
                if (c.size != 4) fail("'ifil' chunk must be 4 bytes");
                unsigned char v[4];
                read(c.data, v, 4);
                out.versionMajor = u16(v);
                out.versionMinor = u16(v + 2);
                if (out.versionMajor != 2) {
                    fail("unsupported SoundFont version " + std::to_string(out.versionMajor) + "." + std::to_string(out.versionMinor) + " (2.x only)");
                }
            } else if (c.id == "INAM" && c.size > 0 && c.size < 4096) {
                std::vector<unsigned char> s(c.size);
                read(c.data, s.data(), c.size);
                out.name = fixedString(s.data(), s.size());
            }
        }
    }

    void parseSdta(const Chunk& list, File& out) {
        const Chunk* smpl = nullptr;
        const Chunk* sm24 = nullptr;
        const auto subs = chunks(list.data + 4, list.data + list.size, "sdta");
        for (const Chunk& c : subs) {
            if (c.id == "smpl") smpl = &c;
            else if (c.id == "sm24") sm24 = &c;
        }
        if (!smpl) fail("no 'smpl' chunk (16-bit sample data)");
        out.smpl.resize(smpl->size / 2);
        if (!out.smpl.empty()) read(smpl->data, out.smpl.data(), out.smpl.size() * 2);
        // sm24 (SoundFont 2.04): the low bytes of 24-bit samples; ignored when inconsistent, as the spec says.
        const bool v204 = out.versionMajor > 2 || (out.versionMajor == 2 && out.versionMinor >= 4);
        if (sm24 && v204 && sm24->size >= out.smpl.size() && sm24->size <= out.smpl.size() + 1) {
            out.sm24.resize(out.smpl.size());
            if (!out.sm24.empty()) read(sm24->data, out.sm24.data(), out.sm24.size());
        }
    }

    template <typename T, typename Fn>
    std::vector<T> records(const std::map<std::string, Chunk>& subs, const char* id, std::size_t size, std::size_t minCount, Fn decode) {
        const auto it = subs.find(id);
        if (it == subs.end()) fail(std::string("no '") + id + "' chunk in 'pdta'");
        const Chunk& c = it->second;
        if (c.size % size != 0) fail(std::string("'") + id + "' chunk size " + std::to_string(c.size) + " is not a multiple of " + std::to_string(size));
        const std::size_t count = c.size / size;
        if (count < minCount) fail(std::string("'") + id + "' chunk has " + std::to_string(count) + " records (at least " + std::to_string(minCount) + " expected)");
        std::vector<unsigned char> bytes(c.size);
        if (c.size) read(c.data, bytes.data(), c.size);
        std::vector<T> out;
        out.reserve(count);
        for (std::size_t i = 0; i < count; ++i) out.push_back(decode(bytes.data() + i * size));
        return out;
    }

    // Builds one zone. Generators after the terminal one (instrument / sampleID) are ignored; unknown
    // generators and generators that do not belong to this level are ignored (SF2.04 7.5 / 7.9).
    Zone zone(const std::vector<RawGen>& gens, std::size_t g0, std::size_t g1, const std::vector<Modulator>& mods,
              std::size_t m0, std::size_t m1, bool presetLevel, std::size_t targetCount, const std::string& where) {
        Zone z;
        const int terminal = presetLevel ? InstrumentGen : SampleID;
        const int other = presetLevel ? SampleID : InstrumentGen;
        for (std::size_t k = g0; k < g1; ++k) {
            const RawGen& g = gens[k];
            if (g.oper == KeyRange || g.oper == VelRange) {
                const auto lo = static_cast<std::uint8_t>(g.amount & 0xFFu), hi = static_cast<std::uint8_t>(g.amount >> 8);
                if (g.oper == KeyRange) { z.keyLo = lo; z.keyHi = hi; }
                else { z.velLo = lo; z.velHi = hi; }
                z.set |= std::uint64_t{1} << g.oper;
                continue;
            }
            if (g.oper >= kGenCount || g.oper == other) continue;
            if (g.oper == terminal) {
                if (g.amount >= targetCount) {
                    fail(where + ": " + (presetLevel ? "instrument" : "sample") + " index " + std::to_string(g.amount) +
                         " out of range (" + std::to_string(targetCount) + " defined)");
                }
                z.target = g.amount;
                break;
            }
            z.gen[g.oper] = static_cast<std::int16_t>(g.amount);
            z.set |= std::uint64_t{1} << g.oper;
        }
        z.mods.assign(mods.begin() + static_cast<std::ptrdiff_t>(m0), mods.begin() + static_cast<std::ptrdiff_t>(m1));
        return z;
    }

    // Splits a bag range into the global zone (first zone without a target) and the local zones.
    void zones(const std::vector<RawBag>& bags, std::size_t b0, std::size_t b1, const std::vector<RawGen>& gens,
               const std::vector<Modulator>& mods, bool presetLevel, std::size_t targetCount, const std::string& where,
               Zone& global, std::vector<Zone>& local) {
        for (std::size_t b = b0; b < b1; ++b) {
            const std::size_t g0 = bags[b].gen, g1 = bags[b + 1].gen, m0 = bags[b].mod, m1 = bags[b + 1].mod;
            if (g0 > g1 || m0 > m1) fail(where + ": zone generator/modulator indices are not ascending");
            if (g1 > gens.size() - 1 || m1 > mods.size() - 1) fail(where + ": zone indices past the generator/modulator lists");
            Zone z = zone(gens, g0, g1, mods, m0, m1, presetLevel, targetCount, where);
            if (z.target >= 0) local.push_back(std::move(z));
            else if (b == b0) global = std::move(z);
            // other zones without an instrument / sample are ignored (SF2.04 7.3 / 7.7)
        }
    }

    void parsePdta(const Chunk& list, File& out) {
        std::map<std::string, Chunk> subs;
        for (const Chunk& c : chunks(list.data + 4, list.data + list.size, "pdta")) subs[c.id] = c;

        struct RawPreset { std::string name; std::uint16_t program, bank, bag; };
        struct RawInst { std::string name; std::uint16_t bag; };
        const auto phdr = records<RawPreset>(subs, "phdr", 38, 2, [&](const unsigned char* p) {
            return RawPreset{fixedString(p, 20), u16(p + 20), u16(p + 22), u16(p + 24)};
        });
        const auto bagDecode = [](const unsigned char* p) { return RawBag{u16(p), u16(p + 2)}; };
        const auto genDecode = [](const unsigned char* p) { return RawGen{u16(p), u16(p + 2)}; };
        const auto modDecode = [](const unsigned char* p) {
            Modulator m;
            m.src = u16(p);
            m.dest = u16(p + 2);
            m.amount = static_cast<std::int16_t>(u16(p + 4));
            m.amtSrc = u16(p + 6);
            m.trans = u16(p + 8);
            return m;
        };
        const auto pbag = records<RawBag>(subs, "pbag", 4, 1, bagDecode);
        const auto pmod = records<Modulator>(subs, "pmod", 10, 1, modDecode);
        const auto pgen = records<RawGen>(subs, "pgen", 4, 1, genDecode);
        const auto inst = records<RawInst>(subs, "inst", 22, 2, [&](const unsigned char* p) {
            return RawInst{fixedString(p, 20), u16(p + 20)};
        });
        const auto ibag = records<RawBag>(subs, "ibag", 4, 1, bagDecode);
        const auto imod = records<Modulator>(subs, "imod", 10, 1, modDecode);
        const auto igen = records<RawGen>(subs, "igen", 4, 1, genDecode);
        const auto shdrIt = subs.find("shdr");
        if (shdrIt == subs.end()) fail("no 'shdr' chunk in 'pdta'");

        // samples
        const Chunk& sc = shdrIt->second;
        if (sc.size % 46 != 0 || sc.size / 46 < 2) fail("'shdr' chunk has a bad size (46-byte records, terminal 'EOS' included)");
        {
            std::vector<unsigned char> bytes(sc.size);
            read(sc.data, bytes.data(), sc.size);
            const std::size_t count = sc.size / 46 - 1;  // without the terminal record
            out.samples.reserve(count);
            for (std::size_t i = 0; i < count; ++i) {
                const unsigned char* p = bytes.data() + i * 46;
                Sample s;
                s.name = fixedString(p, 20);
                s.start = u32(p + 20);
                s.end = u32(p + 24);
                s.loopStart = u32(p + 28);
                s.loopEnd = u32(p + 32);
                s.rate = u32(p + 36);
                s.pitch = p[40];
                s.correction = static_cast<std::int8_t>(p[41]);
                s.link = u16(p + 42);
                s.type = u16(p + 44);
                if (!s.rom()) {
                    if (s.end < s.start || s.end > out.smpl.size()) {
                        fail("sample #" + std::to_string(i) + " '" + s.name + "': data [" + std::to_string(s.start) + ", " +
                             std::to_string(s.end) + ") lies outside the sample pool (" + std::to_string(out.smpl.size()) + " samples)");
                    }
                }
                out.samples.push_back(std::move(s));
            }
        }

        // instruments
        if (inst.back().bag > ibag.size() - 1) fail("'inst' terminal record points past 'ibag'");
        out.instruments.reserve(inst.size() - 1);
        for (std::size_t i = 0; i + 1 < inst.size(); ++i) {
            if (inst[i].bag > inst[i + 1].bag) fail("instrument #" + std::to_string(i) + " '" + inst[i].name + "': bag indices are not ascending");
            Instrument in;
            in.name = inst[i].name;
            zones(ibag, inst[i].bag, inst[i + 1].bag, igen, imod, false, out.samples.size(),
                  "instrument #" + std::to_string(i) + " '" + in.name + "'", in.global, in.zones);
            out.instruments.push_back(std::move(in));
        }

        // presets
        if (phdr.back().bag > pbag.size() - 1) fail("'phdr' terminal record points past 'pbag'");
        out.presets.reserve(phdr.size() - 1);
        for (std::size_t i = 0; i + 1 < phdr.size(); ++i) {
            if (phdr[i].bag > phdr[i + 1].bag) fail("preset #" + std::to_string(i) + " '" + phdr[i].name + "': bag indices are not ascending");
            Preset pr;
            pr.name = phdr[i].name;
            pr.bank = phdr[i].bank;
            pr.program = phdr[i].program;
            zones(pbag, phdr[i].bag, phdr[i + 1].bag, pgen, pmod, true, out.instruments.size(),
                  "preset '" + pr.name + "' (" + std::to_string(pr.bank) + ":" + std::to_string(pr.program) + ")", pr.global, pr.zones);
            out.presets.push_back(std::move(pr));
        }
        if (out.presets.empty()) fail("the file contains no presets");
    }

    std::string path_;
    FilePtr file_;
    std::int64_t size_{0};
};

// ------------------------------------------------------------------------------------ name lookup

std::string compact(const std::string& s) {
    std::string out;
    for (const char ch : s) {
        const auto c = static_cast<unsigned char>(ch);
        if (std::isalnum(c)) out.push_back(static_cast<char>(std::tolower(c)));
    }
    return out;
}

std::size_t editDistance(const std::string& a, const std::string& b) {
    std::vector<std::size_t> prev(b.size() + 1), cur(b.size() + 1);
    for (std::size_t j = 0; j <= b.size(); ++j) prev[j] = j;
    for (std::size_t i = 1; i <= a.size(); ++i) {
        cur[0] = i;
        for (std::size_t j = 1; j <= b.size(); ++j) {
            cur[j] = std::min({prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] == b[j - 1] ? 0 : 1)});
        }
        std::swap(prev, cur);
    }
    return prev[b.size()];
}

// Up to `count` of `names` closest to `query` (substring hits first, then edit distance).
std::vector<std::size_t> closest(const std::vector<std::string>& names, const std::string& query, std::size_t count) {
    const std::string q = compact(query);
    std::vector<std::pair<std::size_t, std::size_t>> scored;
    for (std::size_t i = 0; i < names.size(); ++i) {
        const std::string n = compact(names[i]);
        std::size_t score = editDistance(q, n);
        if (!q.empty() && (n.find(q) != std::string::npos || q.find(n) != std::string::npos)) score = 0;
        scored.push_back({score, i});
    }
    std::stable_sort(scored.begin(), scored.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
    std::vector<std::size_t> out;
    for (std::size_t i = 0; i < std::min(count, scored.size()); ++i) out.push_back(scored[i].second);
    return out;
}

std::string presetId(const Preset& p) { return std::to_string(p.bank) + ":" + std::to_string(p.program); }

bool parseBankProgram(const std::string& s, int& bank, int& program) {
    const auto colon = s.find(':');
    if (colon == std::string::npos || colon == 0 || colon + 1 >= s.size()) return false;
    const std::string a = s.substr(0, colon), b = s.substr(colon + 1);
    auto digits = [](const std::string& x) { return !x.empty() && x.size() <= 5 && std::all_of(x.begin(), x.end(), [](char c) { return c >= '0' && c <= '9'; }); };
    if (!digits(a) || !digits(b)) return false;
    bank = std::stoi(a);
    program = std::stoi(b);
    return true;
}

std::mutex gCacheMutex;
std::map<std::string, std::shared_ptr<const File>>& cache() {
    static std::map<std::string, std::shared_ptr<const File>> c;
    return c;
}
int gLoads = 0;

}  // namespace

std::string normalizeName(const std::string& s) {
    std::string out;
    bool space = false;
    for (const char ch : s) {
        const auto c = static_cast<unsigned char>(ch);
        if (std::isspace(c)) {
            space = !out.empty();
            continue;
        }
        if (space) out.push_back(' ');
        space = false;
        out.push_back(static_cast<char>(std::tolower(c)));
    }
    return out;
}

std::vector<const Preset*> File::sortedPresets() const {
    std::vector<const Preset*> out;
    for (const auto& p : presets) out.push_back(&p);
    std::stable_sort(out.begin(), out.end(), [](const Preset* a, const Preset* b) {
        return a->bank != b->bank ? a->bank < b->bank : a->program < b->program;
    });
    return out;
}

const Preset* File::find(int bank, int program) const noexcept {
    for (const auto& p : presets) {
        if (p.bank == bank && p.program == program) return &p;
    }
    return nullptr;
}

const Preset& File::resolvePreset(int bank, int program) const {
    if (const Preset* p = find(bank, program)) return *p;
    std::ostringstream msg;
    msg << "no preset at bank " << bank << " program " << program << " in '" << path << "'";
    std::vector<std::string> inBank;
    std::vector<int> banks;
    for (const Preset* p : sortedPresets()) {
        if (p->bank == bank) inBank.push_back(presetId(*p) + " " + p->name);
        if (std::find(banks.begin(), banks.end(), p->bank) == banks.end()) banks.push_back(p->bank);
    }
    if (!inBank.empty()) {
        msg << "; bank " << bank << " has: ";
        for (std::size_t i = 0; i < std::min<std::size_t>(inBank.size(), 16); ++i) msg << (i ? ", " : "") << inBank[i];
        if (inBank.size() > 16) msg << ", ...";
    } else {
        msg << "; banks in the file: ";
        for (std::size_t i = 0; i < banks.size(); ++i) msg << (i ? ", " : "") << banks[i];
    }
    msg << " (list them with `agentsound sf2 [search]`)";
    throw ConfigError(msg.str());
}

const Preset& File::resolvePreset(const std::string& spec) const {
    int bank = 0, program = 0;
    const std::string trimmed = normalizeName(spec);
    if (parseBankProgram(trimmed, bank, program)) return resolvePreset(bank, program);
    const auto sorted = sortedPresets();
    for (const Preset* p : sorted) {  // exact (case-insensitive) name; ties go to the lowest bank
        if (normalizeName(p->name) == trimmed) return *p;
    }
    const std::string c = compact(spec);
    for (const Preset* p : sorted) {
        if (!c.empty() && compact(p->name) == c) return *p;
    }
    std::vector<std::string> names;
    for (const Preset* p : sorted) names.push_back(p->name);
    std::ostringstream msg;
    msg << "unknown preset '" << spec << "' in '" << path << "'; did you mean ";
    const auto best = closest(names, spec, 6);
    for (std::size_t i = 0; i < best.size(); ++i) msg << (i ? ", " : "") << '"' << sorted[best[i]]->name << "\" (" << presetId(*sorted[best[i]]) << ")";
    msg << "? (a name, or \"bank:program\"; list them with `agentsound sf2 [search]`)";
    throw ConfigError(msg.str());
}

int File::resolveSample(const std::string& spec) const {
    const std::string trimmed = normalizeName(spec);
    for (std::size_t i = 0; i < samples.size(); ++i) {
        if (normalizeName(samples[i].name) == trimmed) return static_cast<int>(i);
    }
    const std::string c = compact(spec);
    for (std::size_t i = 0; i < samples.size(); ++i) {
        if (!c.empty() && compact(samples[i].name) == c) return static_cast<int>(i);
    }
    std::vector<std::string> names;
    for (const auto& s : samples) names.push_back(s.name);
    std::ostringstream msg;
    msg << "unknown sample '" << spec << "' in '" << path << "'; did you mean ";
    const auto best = closest(names, spec, 6);
    for (std::size_t i = 0; i < best.size(); ++i) msg << (i ? ", " : "") << '"' << names[best[i]] << '"';
    msg << "? (list them with `agentsound sf2 --samples [search]`)";
    throw ConfigError(msg.str());
}

std::vector<float> File::sampleData(int index) const {
    const Sample& s = samples.at(static_cast<std::size_t>(index));
    std::vector<float> out(s.frames());
    if (!sm24.empty()) {
        for (std::uint32_t i = 0; i < s.frames(); ++i) {
            const std::int32_t v = static_cast<std::int32_t>(smpl[s.start + i]) * 256 + sm24[s.start + i];
            out[i] = static_cast<float>(v) * (1.0f / 8388608.0f);
        }
    } else {
        for (std::uint32_t i = 0; i < s.frames(); ++i) out[i] = static_cast<float>(smpl[s.start + i]) * (1.0f / 32768.0f);
    }
    return out;
}

std::shared_ptr<const smp::Region> File::region(int index, smp::LoopMode mode, std::int64_t loopStart, std::int64_t loopEnd,
                                                bool reverse) const {
    if (mode == smp::LoopMode::None) loopStart = loopEnd = 0;
    const Key key{index, static_cast<int>(mode), loopStart, loopEnd, reverse};
    std::lock_guard<std::mutex> lock(mu_);
    const auto it = regions_.find(key);
    if (it != regions_.end()) return it->second;
    const Sample& s = samples.at(static_cast<std::size_t>(index));
    if (s.rom()) throw ConfigError("soundfont '" + path + "': sample '" + s.name + "' lives in a sound ROM (not contained in the file)");
    if (s.rate == 0) throw ConfigError("soundfont '" + path + "': sample '" + s.name + "' has sample rate 0");
    const std::vector<float> data = sampleData(index);
    auto region = std::make_shared<const smp::Region>(smp::makeRegion(&data, 1, static_cast<double>(s.rate), mode, loopStart, loopEnd, reverse));
    regions_.emplace(key, region);
    return region;
}

std::string resolvePath(const std::string& assetDir, const std::string& file) {
    const fs::path p(file);
    if (p.is_absolute()) return p.string();
    return (fs::path(assetDir) / "soundfonts" / p).string();
}

std::shared_ptr<const File> load(const std::string& path) {
    std::error_code ec;
    std::string key = fs::weakly_canonical(fs::path(path), ec).string();
    if (ec || key.empty()) key = path;
    std::lock_guard<std::mutex> lock(gCacheMutex);
    auto& c = cache();
    const auto it = c.find(key);
    if (it != c.end()) return it->second;
    if (!fs::is_regular_file(fs::path(key), ec)) {
        throw ConfigError("soundfont file '" + path + "' not found (SoundFonts live in assets/soundfonts/; give 'file' as a name "
                          "there, e.g. \"GeneralUser-GS.sf2\", or an absolute path)");
    }
    std::shared_ptr<const File> f = Parser(key).parse();
    ++gLoads;
    c.emplace(key, f);
    return f;
}

int loadCount() noexcept {
    std::lock_guard<std::mutex> lock(gCacheMutex);
    return gLoads;
}

}  // namespace as::sf2
