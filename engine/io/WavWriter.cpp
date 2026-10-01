#include "io/WavWriter.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>

namespace as {
namespace {

void put16(std::string& b, std::uint16_t v) { b.push_back(char(v & 0xff)); b.push_back(char(v >> 8)); }
void put32(std::string& b, std::uint32_t v) { for (int i = 0; i < 4; ++i) b.push_back(char((v >> (8 * i)) & 0xff)); }

}  // namespace

WavWriter::~WavWriter() { close(); }

void WavWriter::open(const std::string& path, int sampleRate, int bitDepth, std::uint64_t ditherSeed) {
    close();
    file_ = std::fopen(path.c_str(), "wb");
    if (!file_) throw std::runtime_error("cannot create '" + path + "'");
    bitDepth_ = bitDepth;
    frames_ = 0;
    rng_.reseed(ditherSeed ^ 0xD17E5ull);

    const std::uint16_t format = bitDepth == 32 ? 3 : 1;  // IEEE float : PCM
    const std::uint16_t channels = 2;
    const std::uint16_t blockAlign = static_cast<std::uint16_t>(channels * bitDepth / 8);
    std::string h;
    h += "RIFF"; put32(h, 0); h += "WAVE";
    h += "fmt "; put32(h, 16); put16(h, format); put16(h, channels);
    put32(h, static_cast<std::uint32_t>(sampleRate));
    put32(h, static_cast<std::uint32_t>(sampleRate) * blockAlign);
    put16(h, blockAlign); put16(h, static_cast<std::uint16_t>(bitDepth));
    h += "data"; put32(h, 0);
    std::fwrite(h.data(), 1, h.size(), file_);
}

void WavWriter::write(const float* left, const float* right, int frames) {
    if (!file_) return;
    buffer_.clear();
    const float* ch[2] = {left, right};
    for (int i = 0; i < frames; ++i) {
        for (int c = 0; c < 2; ++c) {
            float x = ch[c][i];
            if (!std::isfinite(x)) x = 0.0f;
            if (bitDepth_ == 32) {
                std::uint32_t bits;
                std::memcpy(&bits, &x, 4);
                put32(buffer_, bits);
                continue;
            }
            const double full = bitDepth_ == 16 ? 32767.0 : 8388607.0;
            const double dither = static_cast<double>(rng_.uniform()) - static_cast<double>(rng_.uniform());  // TPDF, +-1 LSB
            const double scaled = std::clamp(std::round(static_cast<double>(x) * full + dither), -full - 1.0, full);
            const auto v = static_cast<std::int32_t>(scaled);
            if (bitDepth_ == 16) put16(buffer_, static_cast<std::uint16_t>(v & 0xffff));
            else { buffer_.push_back(char(v & 0xff)); buffer_.push_back(char((v >> 8) & 0xff)); buffer_.push_back(char((v >> 16) & 0xff)); }
        }
    }
    std::fwrite(buffer_.data(), 1, buffer_.size(), file_);
    frames_ += static_cast<std::uint64_t>(frames);
}

void WavWriter::close() {
    if (!file_) return;
    const std::uint64_t dataBytes = frames_ * 2ull * static_cast<std::uint64_t>(bitDepth_ / 8);
    std::string s;
    put32(s, static_cast<std::uint32_t>(std::min<std::uint64_t>(dataBytes + 36, 0xffffffffull)));
    std::fseek(file_, 4, SEEK_SET);
    std::fwrite(s.data(), 1, 4, file_);
    s.clear();
    put32(s, static_cast<std::uint32_t>(std::min<std::uint64_t>(dataBytes, 0xffffffffull)));
    std::fseek(file_, 40, SEEK_SET);
    std::fwrite(s.data(), 1, 4, file_);
    std::fclose(file_);
    file_ = nullptr;
}

}  // namespace as
