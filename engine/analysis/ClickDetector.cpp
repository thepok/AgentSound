#include "analysis/ClickDetector.h"

#include <algorithm>
#include <cmath>

namespace as::analysis {

namespace {
std::int64_t nextPow2(std::int64_t v) {
    std::int64_t p = 1;
    while (p < v) p <<= 1;
    return p;
}
}  // namespace

double ClickEvent::jumpDb() const noexcept { return jump > 0.0f ? 20.0 * std::log10(static_cast<double>(jump)) : -120.0; }

double ClickEvent::contrastDb() const noexcept {
    if (context <= 0.0f) return 60.0;
    return std::min(60.0, 20.0 * std::log10(static_cast<double>(spike) / context));
}

ClickDetector::ClickDetector(double sampleRate) : ClickDetector(sampleRate, Settings{}) {}

bool ClickDetector::onsetNear(std::int64_t sample, std::int64_t tolerance) const noexcept {
    const auto it = std::lower_bound(onsets_.begin(), onsets_.end(), sample - tolerance);
    return it != onsets_.end() && *it <= sample + tolerance;
}

ClickDetector::ClickDetector(double sampleRate, const Settings& settings) : set_(settings), sr_(sampleRate) {
    // ~0.67 ms blocks (32 samples at 48 kHz).
    blockLen_ = std::max(8, static_cast<int>(std::lround(sampleRate / 1500.0)));
    const double blockSec = blockLen_ / sampleRate;
    ctxBlocks_ = std::max(4, static_cast<int>(std::ceil(set_.contextMs * 0.001 / blockSec)));
    onsetBlocks_ = std::max(2, static_cast<int>(std::ceil(0.008 / blockSec)));  // 8 ms of "body"
    contrastLin_ = static_cast<float>(std::pow(10.0, set_.minContrastDb / 20.0));
    onsetLin_ = static_cast<float>(std::pow(10.0, set_.onsetRiseDb / 10.0));
    onsetHfLin_ = static_cast<float>(std::pow(10.0, set_.onsetHfRiseDb / 10.0));
    mergeSamples_ = std::max<std::int64_t>(1, std::llround(set_.mergeMs * 0.001 * sampleRate));
    spreadHalf_ = std::max<std::int64_t>(4, std::llround(0.001 * sampleRate));
    blocks_.resize(static_cast<std::size_t>(nextPow2(2 * ctxBlocks_ + 8)));
    blockMask_ = static_cast<std::int64_t>(blocks_.size()) - 1;
    // Snippets end at most ctxBlocks-1 blocks after the event (they are cut when captured).
    snippetHalf_ = std::clamp(set_.snippetHalf, 0, (ctxBlocks_ - 1) * blockLen_);
    // Raw history needed at evaluation time (ctxBlocks+1 blocks after the event): the snippet, the
    // compactness window and the difference taps before the event.
    const std::int64_t rawNeed = static_cast<std::int64_t>(ctxBlocks_ + 3) * blockLen_ + std::max<std::int64_t>(snippetHalf_, spreadHalf_ + 4) + 16;
    ringL_.assign(static_cast<std::size_t>(nextPow2(rawNeed)), 0.0f);
    ringR_.assign(ringL_.size(), 0.0f);
    rawMask_ = static_cast<std::int64_t>(ringL_.size()) - 1;
}

void ClickDetector::feed(const float* L, const float* R, int frames) {
    if (finished_) return;
    int i = 0;
    while (i < frames) {
        const int n = std::min(frames - i, blockLen_ - fill_);
        float hfL = cur_.hfL, hfR = cur_.hfR, hf = cur_.hf;
        std::int64_t hfPos = cur_.hfPos;
        double energy = cur_.energy, hfEnergy = cur_.hfEnergy;
        float l1 = l1_, l2 = l2_, l3 = l3_, r1 = r1_, r2 = r2_, r3 = r3_;
        for (int k = 0; k < n; ++k) {
            float l = L[i + k], r = R[i + k];
            if (!(std::fabs(l) < 1e30f)) l = 0.0f;
            if (!(std::fabs(r) < 1e30f)) r = 0.0f;
            const float dl = std::fabs(l - 3.0f * l1 + 3.0f * l2 - l3);
            const float dr = std::fabs(r - 3.0f * r1 + 3.0f * r2 - r3);
            hfEnergy += static_cast<double>(dl) * dl + static_cast<double>(dr) * dr;
            l3 = l2; l2 = l1; l1 = l;
            r3 = r2; r2 = r1; r1 = r;
            hfL = std::max(hfL, dl);
            hfR = std::max(hfR, dr);
            const float d = std::max(dl, dr);
            if (d > hf) { hf = d; hfPos = pos_ + k; }
            energy += static_cast<double>(l) * l + static_cast<double>(r) * r;
            const auto idx = static_cast<std::size_t>((pos_ + k) & rawMask_);
            ringL_[idx] = l;
            ringR_[idx] = r;
        }
        l1_ = l1; l2_ = l2; l3_ = l3; r1_ = r1; r2_ = r2; r3_ = r3;
        cur_.hfL = hfL; cur_.hfR = hfR; cur_.hf = hf; cur_.hfPos = hfPos; cur_.energy = energy; cur_.hfEnergy = hfEnergy;
        pos_ += n;
        fill_ += n;
        i += n;
        if (fill_ == blockLen_) {
            pushBlock();
            const std::int64_t c = blocksDone_ - 1 - ctxBlocks_;
            if (c >= 0) evaluate(c, blocksDone_ - 1);
        }
    }
}

void ClickDetector::pushBlock() {
    blocks_[static_cast<std::size_t>(blocksDone_ & blockMask_)] = cur_;
    ++blocksDone_;
    cur_ = Block{};
    fill_ = 0;
}

void ClickDetector::finish() {
    if (finished_) return;
    if (fill_ > 0) pushBlock();
    for (std::int64_t c = std::max<std::int64_t>(0, blocksDone_ - ctxBlocks_); c < blocksDone_; ++c) evaluate(c, blocksDone_ - 1);
    finished_ = true;
}

void ClickDetector::evaluate(std::int64_t c, std::int64_t last) {
    const Block& b = blocks_[static_cast<std::size_t>(c & blockMask_)];
    const float spike = b.hf;
    if (!(spike >= static_cast<float>(set_.minJump))) return;
    auto blk = [&](std::int64_t j) -> const Block& { return blocks_[static_cast<std::size_t>(j & blockMask_)]; };
    // Mean (third-difference) energy per sample of blocks [a, b]. Summed directly: differences of
    // running totals lose the quiet passages late in a long song to rounding.
    auto meanOf = [&](std::int64_t a, std::int64_t b, double Block::*field) {
        if (b < a) return 0.0;
        double sum = 0.0;
        for (std::int64_t j = a; j <= b; ++j) sum += blk(j).*field;
        return sum / (static_cast<double>(b - a + 1) * blockLen_);
    };
    // A musical onset (the energy after the spike rises well above the energy before it: a drum
    // hit, a note starting from silence) is not a click; it is remembered to explain mix spikes.
    const std::int64_t preA = std::max<std::int64_t>(0, c - ctxBlocks_), preB = c - 2;
    const std::int64_t postA = c + 2, postB = std::min(last, c + 1 + onsetBlocks_);
    const double pre = meanOf(preA, preB, &Block::energy);
    const double post = meanOf(postA, postB, &Block::energy);
    constexpr double kEps = 1e-12;
    if (post + kEps > onsetLin_ * (pre + kEps) && post > 1e-8) {
        constexpr std::size_t kMaxOnsets = 1u << 20;
        if (onsets_.size() < kMaxOnsets && (onsets_.empty() || b.hfPos - 1 - onsets_.back() > mergeSamples_)) onsets_.push_back(b.hfPos - 1);
        return;
    }
    // Isolation: nothing within +-context (outside the neighbouring blocks) comes close. Nearest first.
    const float limit = spike / contrastLin_;
    float context = 0.0f;
    for (std::int64_t d = 2; d <= ctxBlocks_; ++d) {
        if (c + d <= last) context = std::max(context, blk(c + d).hf);
        if (c - d >= 0) context = std::max(context, blk(c - d).hf);
        if (context > limit) return;
    }
    const float riseDb = static_cast<float>(10.0 * std::log10((post + kEps) / (pre + kEps)));

    // High-frequency body: the attack of a new sound on top of others (a DX7 bass or clav note over its
    // own previous notes, the broadband energy barely rises) keeps adding high-frequency energy after
    // its first edge; a discontinuity is over after 3-4 samples (and a hard cut removes energy).
    const double hfPre = meanOf(preA, preB, &Block::hfEnergy);
    const double hfPost = meanOf(postA, postB, &Block::hfEnergy);
    constexpr double kHfEps = 1e-14;
    const float hfRiseDb = static_cast<float>(10.0 * std::log10((hfPost + kHfEps) / (hfPre + kHfEps)));
    if (hfPost + kHfEps > onsetHfLin_ * (hfPre + kHfEps) && post > 1e-8) {
        constexpr std::size_t kMaxOnsets = 1u << 20;
        if (onsets_.size() < kMaxOnsets && (onsets_.empty() || b.hfPos - 1 - onsets_.back() > mergeSamples_)) onsets_.push_back(b.hfPos - 1);
        return;
    }

    // Compactness: third-difference energy within +-1 ms relative to the peak.
    const std::int64_t p = b.hfPos;
    double spreadE = 0.0;
    for (std::int64_t s = p - spreadHalf_; s <= p + spreadHalf_; ++s) {
        const double dl = rawL(s) - 3.0 * rawL(s - 1) + 3.0 * rawL(s - 2) - rawL(s - 3);
        const double dr = rawR(s) - 3.0 * rawR(s - 1) + 3.0 * rawR(s - 2) - rawR(s - 3);
        spreadE += std::max(dl * dl, dr * dr);
    }
    const double spread = spreadE / (static_cast<double>(spike) * spike);
    if (spread > set_.maxSpread) {  // a short noise burst: the attack of a percussive sound
        constexpr std::size_t kMaxOnsets = 1u << 20;
        if (onsets_.size() < kMaxOnsets && (onsets_.empty() || p - 1 - onsets_.back() > mergeSamples_)) onsets_.push_back(p - 1);
        return;
    }

    // Size of the discontinuity: largest deviation from linear prediction around the spike.
    float jump = 0.0f;
    for (std::int64_t s = p - 2; s <= p + 1; ++s) {
        jump = std::max(jump, std::fabs(rawL(s) - 2.0f * rawL(s - 1) + rawL(s - 2)));
        jump = std::max(jump, std::fabs(rawR(s) - 2.0f * rawR(s - 1) + rawR(s - 2)));
    }
    if (!(jump >= static_cast<float>(set_.minJump))) return;

    ClickEvent ev;
    ev.sample = std::max<std::int64_t>(0, p - 1);
    ev.jump = jump;
    ev.spike = spike;
    ev.context = context;
    ev.riseDb = riseDb;
    ev.hfRiseDb = hfRiseDb;
    ev.spread = static_cast<float>(spread);
    ev.channels = static_cast<std::uint8_t>((b.hfL >= 0.5f * spike ? 1 : 0) | (b.hfR >= 0.5f * spike ? 2 : 0));

    ClickEvent* slot = nullptr;
    if (!events_.empty() && ev.sample - events_.back().sample <= mergeSamples_) {
        if (ev.jump <= events_.back().jump) return;  // same event, the earlier estimate was bigger
        slot = &events_.back();
        slot->snipL.clear();
        slot->snipR.clear();
    } else if (events_.size() >= set_.maxEvents) {
        ++overflow_;
        return;
    } else {
        events_.push_back(ClickEvent{});
        slot = &events_.back();
    }
    *slot = std::move(ev);

    if (snippetHalf_ > 0) {
        // Keep snippets for the strongest events only.
        std::size_t withSnip = 0;
        ClickEvent* weakest = nullptr;
        for (auto& e : events_) {
            if (&e == slot || e.snipL.empty()) continue;
            ++withSnip;
            if (!weakest || e.jump < weakest->jump) weakest = &e;
        }
        bool take = withSnip < set_.maxSnippets;
        if (!take && weakest && weakest->jump < slot->jump) {
            std::vector<float>().swap(weakest->snipL);
            std::vector<float>().swap(weakest->snipR);
            take = true;
        }
        if (take) {
            const auto n = static_cast<std::size_t>(2 * snippetHalf_ + 1);
            slot->snipL.resize(n);
            slot->snipR.resize(n);
            for (std::size_t k = 0; k < n; ++k) {
                const std::int64_t s = slot->sample - snippetHalf_ + static_cast<std::int64_t>(k);
                const bool ok = s >= pos_ - static_cast<std::int64_t>(ringL_.size());
                slot->snipL[k] = ok ? rawL(s) : 0.0f;
                slot->snipR[k] = ok ? rawR(s) : 0.0f;
            }
        }
    }
}

}  // namespace as::analysis
