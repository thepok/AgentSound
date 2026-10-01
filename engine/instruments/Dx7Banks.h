#pragma once

// DX7 32-voice bank (cartridge) loading and voice lookup.
//
// Banks are standard 4104-byte bulk dumps (F0 43 0n 09 20 00 <4096 data> <checksum> F7)
// found in <assetDir>/dx7/*.syx; the bank name is the lower-case file stem ("rom1a").
// Voice references accepted by resolveVoice():
//   "rom1a:10"        bank + 0-based index (0..31 = DX7 front-panel number - 1)
//   "rom1a:E.PIANO 1" bank + name
//   "E.PIANO 1"       bare name, searched across all banks in file-name order (first match wins)
// Names match case-insensitively with leading/trailing whitespace trimmed and internal runs of
// whitespace collapsed ("brass 1" finds "BRASS   1"); as a fallback, all whitespace is ignored.

#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace as {

struct Dx7VoiceInfo {
    std::string bank;  // lower-case file stem, e.g. "rom1a"
    int index;         // 0..31 within the bank
    std::string name;  // display name: trimmed, internal spaces collapsed ("BRASS 1")
};

// Scans assetDir/dx7/*.syx sorted by file name. Returns an empty list when the folder does not
// exist or holds no banks (the Yamaha ROM cartridges are not distributed with the project, see
// assets/dx7/README.md); throws ConfigError on unreadable or malformed bank files.
std::vector<Dx7VoiceInfo> listDx7Voices(const std::string& assetDir);

// True when assetDir/dx7 holds at least one *.syx bank (DX7 voices are unavailable otherwise).
bool dx7BanksInstalled(const std::string& assetDir);

// The hint printed when no banks are installed.
inline constexpr const char* kDx7NoBanksHint = "no DX7 banks installed - see assets/dx7/README.md";

namespace dx7 {

inline constexpr std::size_t kPackedVoiceBytes = 128;
inline constexpr std::size_t kVoicesPerBank = 32;
inline constexpr std::size_t kBankDataBytes = kPackedVoiceBytes * kVoicesPerBank;  // 4096
inline constexpr std::size_t kBankSysexBytes = kBankDataBytes + 8;                // 4104

using PackedVoice = std::array<std::uint8_t, kPackedVoiceBytes>;
inline constexpr std::size_t kUnpackedVoiceBytes = 156;
using UnpackedVoice = std::array<std::uint8_t, kUnpackedVoiceBytes>;  // "VCED" layout, operator 6 first

struct Bank {
    std::string name;  // lower-case file stem
    std::array<PackedVoice, kVoicesPerBank> voices{};
};

struct ResolvedVoice {
    std::string bank;
    int index{0};
    std::string name;
    PackedVoice data{};
};

// DX7 bulk checksum: two's complement of the 7-bit sum of the data bytes.
std::uint8_t checksum(std::span<const std::uint8_t> data) noexcept;

// Parses one 4104-byte bulk dump and verifies framing and checksum. Throws ConfigError
// mentioning `what` (usually the file path) on any error.
Bank parseBank(std::span<const std::uint8_t> bytes, const std::string& bankName, const std::string& what);

// Loads every assetDir/dx7/*.syx (sorted by file name). Throws ConfigError if the folder is
// missing, contains no banks (the message names assets/dx7/README.md), or a bank is malformed.
std::vector<Bank> loadBanks(const std::string& assetDir);

// Packed 128-byte bulk voice -> 156-byte "VCED" layout expected by MSFA's Dx7Note (ported from Msound2
// Dx7EngineAdapter; every field range-limited like the DX7 does; all six operators switched on).
UnpackedVoice unpackVoice(const PackedVoice& packed);

// Display name of a packed voice (bytes 118..127), trimmed with internal spaces collapsed.
std::string voiceName(const PackedVoice& voice);

// Syntax check without file access (used by configure()). Throws ConfigError.
void checkVoiceSpec(const std::string& spec);

// Resolves a voice reference (see top of file). Throws ConfigError listing close matches.
ResolvedVoice resolveVoice(const std::vector<Bank>& banks, const std::string& spec);

}  // namespace dx7
}  // namespace as
