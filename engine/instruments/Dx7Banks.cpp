#include "instruments/Dx7Banks.h"

#include "core/Params.h"

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>

namespace as {
namespace dx7 {
namespace {

namespace fs = std::filesystem;

std::string lower(std::string s) {
    for (auto& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

std::string trim(const std::string& s) {
    const auto first = s.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = s.find_last_not_of(" \t\r\n");
    return s.substr(first, last - first + 1);
}

// Upper case, trimmed, internal whitespace runs collapsed to one space.
std::string normalizeName(const std::string& s) {
    std::string out;
    bool pendingSpace = false;
    for (const char ch : s) {
        const auto c = static_cast<unsigned char>(ch);
        if (std::isspace(c)) {
            pendingSpace = !out.empty();
            continue;
        }
        if (pendingSpace) out.push_back(' ');
        pendingSpace = false;
        out.push_back(static_cast<char>(std::toupper(c)));
    }
    return out;
}

std::string stripSpaces(const std::string& normalized) {
    std::string out;
    for (const char c : normalized) {
        if (c != ' ') out.push_back(c);
    }
    return out;
}

bool isAllDigits(const std::string& s) {
    return !s.empty() && std::all_of(s.begin(), s.end(), [](char c) { return c >= '0' && c <= '9'; });
}

std::size_t editDistance(const std::string& a, const std::string& b) {
    std::vector<std::size_t> prev(b.size() + 1), cur(b.size() + 1);
    for (std::size_t j = 0; j <= b.size(); ++j) prev[j] = j;
    for (std::size_t i = 1; i <= a.size(); ++i) {
        cur[0] = i;
        for (std::size_t j = 1; j <= b.size(); ++j) {
            const std::size_t sub = prev[j - 1] + (a[i - 1] == b[j - 1] ? 0 : 1);
            cur[j] = std::min({prev[j] + 1, cur[j - 1] + 1, sub});
        }
        std::swap(prev, cur);
    }
    return prev[b.size()];
}

std::string ref(const Bank& bank, int index) {
    return bank.name + ":" + std::to_string(index) + " " +
           voiceName(bank.voices[static_cast<std::size_t>(index)]);
}

// Up to `count` voices whose names are closest to `query` (substring hits first, then edit distance).
std::string suggestions(const std::vector<const Bank*>& banks, const std::string& query, std::size_t count) {
    struct Candidate {
        std::size_t score;
        std::string text;
    };
    const std::string q = stripSpaces(normalizeName(query));
    std::vector<Candidate> candidates;
    for (const Bank* bank : banks) {
        for (int i = 0; i < static_cast<int>(kVoicesPerBank); ++i) {
            const std::string name = stripSpaces(normalizeName(voiceName(bank->voices[static_cast<std::size_t>(i)])));
            std::size_t score = editDistance(q, name);
            if (!q.empty() && (name.find(q) != std::string::npos || q.find(name) != std::string::npos)) score = 0;
            candidates.push_back({score, ref(*bank, i)});
        }
    }
    std::stable_sort(candidates.begin(), candidates.end(),
                     [](const Candidate& a, const Candidate& b) { return a.score < b.score; });
    std::ostringstream out;
    for (std::size_t i = 0; i < std::min(count, candidates.size()); ++i) {
        out << (i ? ", " : "") << '"' << candidates[i].text << '"';
    }
    return out.str();
}

std::string bankList(const std::vector<Bank>& banks) {
    std::ostringstream out;
    for (std::size_t i = 0; i < banks.size(); ++i) out << (i ? ", " : "") << banks[i].name;
    return out.str();
}

const Bank* findBank(const std::vector<Bank>& banks, const std::string& name) {
    const std::string key = lower(trim(name));
    for (const auto& bank : banks) {
        if (bank.name == key) return &bank;
    }
    return nullptr;
}

// Index of the voice in `bank` named `name` (normalized compare, then whitespace-free compare), or -1.
int findName(const Bank& bank, const std::string& name, bool ignoreSpaces) {
    const std::string key = ignoreSpaces ? stripSpaces(normalizeName(name)) : normalizeName(name);
    for (int i = 0; i < static_cast<int>(kVoicesPerBank); ++i) {
        std::string candidate = normalizeName(voiceName(bank.voices[static_cast<std::size_t>(i)]));
        if (ignoreSpaces) candidate = stripSpaces(candidate);
        if (candidate == key) return i;
    }
    return -1;
}

ResolvedVoice make(const Bank& bank, int index) {
    ResolvedVoice v;
    v.bank = bank.name;
    v.index = index;
    v.data = bank.voices[static_cast<std::size_t>(index)];
    v.name = voiceName(v.data);
    return v;
}

}  // namespace

std::uint8_t checksum(std::span<const std::uint8_t> data) noexcept {
    std::uint32_t sum = 0;
    for (const auto b : data) sum += b;
    return static_cast<std::uint8_t>((128u - (sum & 0x7fu)) & 0x7fu);
}

Bank parseBank(std::span<const std::uint8_t> bytes, const std::string& bankName, const std::string& what) {
    auto fail = [&](const std::string& why) { throw ConfigError("dx7 bank '" + what + "': " + why); };
    if (bytes.size() != kBankSysexBytes) {
        fail("expected a 4104-byte DX7 32-voice bulk dump, got " + std::to_string(bytes.size()) + " bytes");
    }
    if (bytes[0] != 0xf0 || bytes[1] != 0x43) fail("not a Yamaha SysEx message (F0 43 ...)");
    if ((bytes[2] & 0xf0) != 0) fail("bad sub-status byte (expected 0n)");
    if (bytes[3] != 0x09) fail("not a 32-voice bulk dump (format byte must be 09)");
    if (bytes[4] != 0x20 || bytes[5] != 0x00) fail("byte count is not 4096 (expected 20 00)");
    if (bytes[kBankSysexBytes - 1] != 0xf7) fail("missing SysEx terminator F7");
    const auto payload = bytes.subspan(6, kBankDataBytes);
    if (std::any_of(payload.begin(), payload.end(), [](std::uint8_t b) { return b > 0x7f; })) {
        fail("voice data contains non-7-bit bytes");
    }
    if (checksum(payload) != bytes[kBankSysexBytes - 2]) fail("checksum mismatch");
    Bank bank;
    bank.name = bankName;
    for (std::size_t v = 0; v < kVoicesPerBank; ++v) {
        std::copy_n(payload.begin() + static_cast<std::ptrdiff_t>(v * kPackedVoiceBytes), kPackedVoiceBytes,
                    bank.voices[v].begin());
    }
    return bank;
}

std::vector<Bank> loadBanks(const std::string& assetDir) {
    const fs::path dir = fs::path(assetDir) / "dx7";
    std::error_code ec;
    if (!fs::is_directory(dir, ec)) {
        throw ConfigError("dx7: bank folder '" + dir.string() + "' does not exist (RenderContext::assetDir='" +
                          assetDir + "'); " + kDx7NoBanksHint);
    }
    std::vector<fs::path> files;
    for (const auto& entry : fs::directory_iterator(dir, ec)) {
        if (entry.is_regular_file() && lower(entry.path().extension().string()) == ".syx") {
            files.push_back(entry.path());
        }
    }
    if (ec) throw ConfigError("dx7: cannot list '" + dir.string() + "': " + ec.message());
    std::sort(files.begin(), files.end(),
              [](const fs::path& a, const fs::path& b) { return a.filename().string() < b.filename().string(); });

    std::vector<Bank> banks;
    for (const auto& file : files) {
        std::ifstream in(file, std::ios::binary);
        if (!in) throw ConfigError("dx7: cannot open bank '" + file.string() + "'");
        const std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        banks.push_back(parseBank(bytes, lower(file.stem().string()), file.string()));
    }
    if (banks.empty()) {
        throw ConfigError("dx7: no *.syx banks found in '" + dir.string() + "': " + kDx7NoBanksHint +
                          " (the 8 Yamaha DX7 ROM cartridges rom1a..rom4b.syx are not part of the repository)");
    }
    return banks;
}

UnpackedVoice unpackVoice(const PackedVoice& packed) {
    auto lim = [](int v, int maximum) { return static_cast<std::uint8_t>(std::min(v, maximum)); };
    UnpackedVoice r{};
    for (int op = 0; op < 6; ++op) {
        const int s = op * 17, d = op * 21;
        for (int i = 0; i < 11; ++i) r[d + i] = lim(packed[s + i] & 0x7f, 99);  // EG, break point, depths
        const int curves = packed[s + 11] & 0x7f;
        r[d + 11] = curves & 0x03;
        r[d + 12] = (curves >> 2) & 0x03;
        const int detuneRs = packed[s + 12] & 0x7f;
        r[d + 13] = detuneRs & 0x07;
        const int velAms = packed[s + 13] & 0x7f;
        r[d + 14] = velAms & 0x03;
        r[d + 15] = (velAms >> 2) & 0x07;
        r[d + 16] = lim(packed[s + 14] & 0x7f, 99);
        const int modeCoarse = packed[s + 15] & 0x7f;
        r[d + 17] = modeCoarse & 0x01;
        r[d + 18] = (modeCoarse >> 1) & 0x1f;
        r[d + 19] = lim(packed[s + 16] & 0x7f, 99);
        r[d + 20] = lim((detuneRs >> 3) & 0x0f, 14);
    }
    for (int i = 0; i < 8; ++i) r[126 + i] = lim(packed[102 + i] & 0x7f, 99);  // pitch EG
    r[134] = lim(packed[110] & 0x7f, 31);                                     // algorithm
    const int syncFb = packed[111] & 0x7f;
    r[135] = syncFb & 0x07;                                                   // feedback
    r[136] = (syncFb >> 3) & 0x01;                                            // osc key sync
    for (int i = 0; i < 4; ++i) r[137 + i] = lim(packed[112 + i] & 0x7f, 99); // LFO rate/delay/PMD/AMD
    const int lfo = packed[116] & 0x7f;
    r[141] = lfo & 0x01;                                                      // LFO key sync
    r[142] = lim((lfo >> 1) & 0x07, 5);                                       // LFO wave
    r[143] = (lfo >> 4) & 0x07;                                               // pitch mod sens
    r[144] = lim(packed[117] & 0x7f, 48);                                     // transpose (24 = none)
    for (int i = 0; i < 10; ++i) r[145 + i] = packed[118 + i] & 0x7f;         // name
    r[155] = 0x3f;                                                            // all operators on
    return r;
}

std::string voiceName(const PackedVoice& voice) {
    std::string raw;
    for (std::size_t i = 118; i < 128; ++i) {
        const auto c = voice[i] & 0x7f;
        raw.push_back(c >= 32 && c <= 126 ? static_cast<char>(c) : ' ');
    }
    // Collapse whitespace but keep the original case (ROM names are upper case anyway).
    std::string out;
    bool pendingSpace = false;
    for (const char c : raw) {
        if (c == ' ') {
            pendingSpace = !out.empty();
            continue;
        }
        if (pendingSpace) out.push_back(' ');
        pendingSpace = false;
        out.push_back(c);
    }
    return out;
}

void checkVoiceSpec(const std::string& spec) {
    const std::string s = trim(spec);
    if (s.empty()) throw ConfigError("dx7: 'voice' must not be empty (e.g. \"E.PIANO 1\" or \"rom1a:10\")");
    const auto colon = s.find(':');
    if (colon == std::string::npos) return;
    const std::string bank = trim(s.substr(0, colon));
    const std::string rest = trim(s.substr(colon + 1));
    if (bank.empty() || rest.empty()) {
        throw ConfigError("dx7: 'voice' = \"" + spec + "\" must look like \"bank:index\", \"bank:name\" or \"name\"");
    }
    if (isAllDigits(rest)) {
        if (rest.size() > 2 || std::stoi(rest) >= static_cast<int>(kVoicesPerBank)) {
            throw ConfigError("dx7: 'voice' = \"" + spec + "\": index must be 0..31 (0-based)");
        }
    }
}

ResolvedVoice resolveVoice(const std::vector<Bank>& banks, const std::string& spec) {
    checkVoiceSpec(spec);
    const std::string s = trim(spec);
    std::vector<const Bank*> all;
    for (const auto& b : banks) all.push_back(&b);

    const auto colon = s.find(':');
    if (colon != std::string::npos) {
        const std::string bankPart = trim(s.substr(0, colon));
        const std::string rest = trim(s.substr(colon + 1));
        if (const Bank* bank = findBank(banks, bankPart)) {
            if (isAllDigits(rest)) return make(*bank, std::stoi(rest));
            for (const bool loose : {false, true}) {
                const int i = findName(*bank, rest, loose);
                if (i >= 0) return make(*bank, i);
            }
            throw ConfigError("dx7: voice \"" + rest + "\" not found in bank '" + bank->name +
                              "'; closest: " + suggestions({bank}, rest, 6));
        }
        // Not a bank prefix: the colon may be part of a voice name; fall through to the name search.
        bool nameHit = false;
        for (const auto& b : banks) nameHit = nameHit || findName(b, s, true) >= 0;
        if (!nameHit) {
            throw ConfigError("dx7: unknown bank '" + bankPart + "' in voice \"" + spec +
                              "\" (banks: " + bankList(banks) + ")");
        }
    }
    for (const bool loose : {false, true}) {
        for (const auto& bank : banks) {
            const int i = findName(bank, s, loose);
            if (i >= 0) return make(bank, i);
        }
    }
    throw ConfigError("dx7: voice \"" + s + "\" not found; closest: " + suggestions(all, s, 8) +
                      " (use a name, \"bank:name\" or \"bank:index\" with 0-based index)");
}

}  // namespace dx7

bool dx7BanksInstalled(const std::string& assetDir) {
    std::error_code ec;
    const std::filesystem::path dir = std::filesystem::path(assetDir) / "dx7";
    if (!std::filesystem::is_directory(dir, ec)) return false;
    for (const auto& entry : std::filesystem::directory_iterator(dir, ec)) {
        if (entry.is_regular_file() && dx7::lower(entry.path().extension().string()) == ".syx") return true;
    }
    return false;
}

std::vector<Dx7VoiceInfo> listDx7Voices(const std::string& assetDir) {
    if (!dx7BanksInstalled(assetDir)) return {};
    std::vector<Dx7VoiceInfo> out;
    for (const auto& bank : dx7::loadBanks(assetDir)) {
        for (int i = 0; i < static_cast<int>(dx7::kVoicesPerBank); ++i) {
            out.push_back({bank.name, i, dx7::voiceName(bank.voices[static_cast<std::size_t>(i)])});
        }
    }
    return out;
}

}  // namespace as
