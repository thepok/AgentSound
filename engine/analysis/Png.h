#pragma once

// Self-contained PNG writer/reader (8-bit RGB). Deflate with LZ77 (hash chains, lazy matching)
// and per-block choice of dynamic Huffman, fixed Huffman or stored blocks; adaptive PNG row
// filters. The decoder (full inflate) exists so tests can verify the files byte-exactly.

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace as::analysis {

struct Image {
    int width{0}, height{0};
    std::vector<std::uint8_t> rgb;  // row-major, 3 bytes per pixel
};

std::uint32_t crc32(const std::uint8_t* data, std::size_t n, std::uint32_t crc = 0) noexcept;
std::uint32_t adler32(const std::uint8_t* data, std::size_t n, std::uint32_t adler = 1) noexcept;

std::vector<std::uint8_t> deflateCompress(const std::uint8_t* data, std::size_t n);
std::vector<std::uint8_t> inflateDecompress(const std::uint8_t* data, std::size_t n);  // throws std::runtime_error
std::vector<std::uint8_t> zlibCompress(const std::uint8_t* data, std::size_t n);
std::vector<std::uint8_t> zlibDecompress(const std::uint8_t* data, std::size_t n);     // checks Adler-32, throws

std::vector<std::uint8_t> encodePng(const Image& image);
// Decodes 8-bit RGB / RGBA (alpha dropped), non-interlaced PNGs; verifies every chunk CRC and the
// zlib checksum. Throws std::runtime_error on anything malformed.
Image decodePng(const std::vector<std::uint8_t>& png);

void writePng(const std::string& path, const Image& image);  // throws std::runtime_error on I/O failure
std::vector<std::uint8_t> readFileBytes(const std::string& path);  // throws std::runtime_error

}  // namespace as::analysis
