#pragma once

// Internal state of MixAnalyzer, shared by the analysis (MixAnalyzer.cpp) and the images
// (MixPlots.cpp, SpectroPlots.cpp, ClickPlots.cpp).

#include "analysis/ClickDetector.h"
#include "analysis/Loudness.h"
#include "analysis/MixAnalyzer.h"
#include "analysis/NoteDynamics.h"
#include "analysis/Profiles.h"
#include "analysis/Space.h"
#include "analysis/StreamStats.h"

#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace as::analysis {

struct NodeData {
    std::string id;
    bool isBus{false};
    std::unique_ptr<StreamStats> stats;
    std::unique_ptr<ClickDetector> clicks;
    std::unique_ptr<OnsetEnvelope> env;  // tracks only: 2.5 ms envelope for the note dynamics
    // filled by finish()
    double rmsDb{kDbFloor};  // RMS while active
    double peakDb{kDbFloor};
    double lufs{kDbFloor};
    int dominantBand{-1};
    double corr{1.0}, width{0.0}, balanceDb{0.0}, lowCorr{1.0}, lowShare{0.0}, sharePct{0.0};
    std::vector<double> sectionRmsDb;  // [section], RMS over the whole section
    // routing (optional, MixAnalyzer::setNodeRouting / setRouting) and the space roles (assessSpace)
    NodeRouting routing;
    bool hasRouting{false};
    Role role{Role::Unknown};
    ReturnKind returnKind{ReturnKind::None};
    bool feedsMaster{false};           // output is the master (with routing)
    NoteDynamicsResult dynamics;       // note-level dynamics (assessDynamics)
};

struct SectionData {
    std::string name;
    double startSec{0}, endSec{0};
    bool implicit{false};  // whole-song pseudo-section when no markers were given
    // filled by finish()
    double lufs{kDbFloor}, stMax{kDbFloor}, peakDb{kDbFloor}, rmsDb{kDbFloor};
    double corr{1.0}, width{0.0}, lowCorr{1.0}, lowShare{0.0}, balanceDb{0.0};
    std::array<double, kNumBands> vsRef{};
};

// A zoomed spectrogram image: one per section (16-bar chunks when the song has no sections).
struct ZoomSpan {
    std::string name, file;
    double startSec{0}, endSec{0};
};

// One reported click: a discontinuity found in the mix (attributed to the node(s) that show it at
// the same time) or only in a single node (masked in the mix).
struct ClickInfo {
    std::int64_t sample{0};
    double sec{0.0}, jumpDb{kDbFloor}, contrastDb{0.0};
    int channels{3};           // bit 0 = L, bit 1 = R
    int node{-1};              // attributed node, -1 = none (master chain or the sum of several parts)
    std::vector<int> nodes;    // every node with a coincident click
    bool inMix{true};
    int severity{1};           // 0 high, 1 medium, 2 low
    std::string image;         // "clicks/click_NN.png" or empty
    const ClickEvent* nodeEvent{nullptr};  // the attributed node's event (its snippet), may be null
};

struct ImageInfo {
    std::string file, shows;
};

struct MixImpl {
    // configuration
    double sampleRate{48000.0}, bpm{120.0}, startBeat{0.0};
    // song time (MixAnalyzer::setTimeGrid): a changing tempo (`mapped`) and bars other than 4/4 (`metered`)
    TempoMap tempo;
    MeterMap meter;
    bool mapped{false}, metered{false};
    double startSample{0.0};                   // mapped: song sample of the first rendered sample
    const AnalysisProfile* profile{&defaultAnalysisProfile()};  // reference balance + thresholds
    double lufsMin{-12.0}, lufsMax{-9.0};      // the profile's target unless loudnessOverride
    bool loudnessOverride{false};              // setLoudnessTarget() was called
    std::vector<std::int64_t> boundaries;      // section edges in samples (exact segment boundaries)
    int tickLen{4800};
    bool prepared{false}, finished{false}, fed{false};
    std::unique_ptr<SpectralSetup> setup;
    std::vector<NodeData> nodes;
    std::vector<float> mixL, mixR;

    // results of finish()
    json report;
    std::unique_ptr<StreamStats> mix;
    std::unique_ptr<ClickDetector> mixClicks;
    std::vector<double> kTick;                 // exact K-weighted energy per tick (both channels)
    std::vector<float> momentary, shortTerm;   // LUFS of the 400 ms / 3 s window ending at each tick
    double durationSec{0.0}, lufsI{kDbFloor}, lra{0.0}, truePeakDb{kDbFloor}, samplePeakDb{kDbFloor};
    double stMax{kDbFloor}, rmsDb{kDbFloor}, corr{1.0}, width{0.0}, lowCorr{1.0}, balanceDb{0.0};
    std::int64_t clippedSamples{0};
    std::array<double, kNumBands> vsRef{};
    std::vector<SectionData> sections;         // sorted by start; a whole-song "song" section if none were given
    std::array<double, kNumBands> refShare{};  // the profile's reference energy share per band (sums to 1)
    int errors{0}, warnings{0}, infos{0};
    std::vector<std::pair<int, std::string>> notes;  // (severity 0 error / 1 warn / 2 info, message), sorted
    std::vector<ClickInfo> clicks;             // most severe first (capped, see the counts)
    int clicksInMix{0}, clicksMasked{0};       // totals before capping
    std::vector<ZoomSpan> zooms;               // per-section spectrogram images
    std::vector<ImageInfo> images;             // what writeImages() writes, in reading order
    SpaceData space;                           // the 'space' assessment (Space.h)

    double tickSec() const noexcept { return tickLen / sampleRate; }
    // Song beat at `sec` seconds from the first rendered sample, and back (through the tempo map).
    double beatAt(double sec) const noexcept {
        return mapped ? tempo.beatAtSample(startSample + sec * sampleRate) : startBeat + sec * bpm / 60.0;
    }
    double secAtBeat(double beat) const noexcept {
        return mapped ? (tempo.sampleAt(beat) - startSample) / sampleRate : (beat - startBeat) * 60.0 / bpm;
    }
    // Fractional 0-based song bar of a beat, and the beat where 0-based bar `bar` starts (the meter; 4/4 default).
    double barAt(double beat) const noexcept { return metered ? meter.barAt(beat) : beat / 4.0; }
    double barStartBeat(double bar) const noexcept { return metered ? meter.barStart(bar) : 4.0 * bar; }
    double beatsPerBarAt(double beat) const noexcept { return metered ? meter.beatsPerBarAt(beat) : 4.0; }
    BarGrid barGrid() const noexcept {
        BarGrid g;
        g.startBeat = startBeat;
        g.bpm = bpm;
        g.sampleRate = sampleRate;
        g.tempo = mapped ? &tempo : nullptr;
        g.meter = metered ? &meter : nullptr;
        g.startSample = startSample;
        return g;
    }
    // "bar 12 beat 3.25" style position (1-based song bars of the meter, quarter-note beats).
    std::string barBeat(double sec) const;
};

// Reference long-term spectrum of a typical modern pop / synthwave master, dB per Hz (arbitrary offset):
// the "default" analysis profile; the other profiles add their offsets to it (Profiles.h).
double referencePsdDb(double hz) noexcept;
std::array<double, kNumBands> referenceBandShares();  // the default profile's band shares
// Band level vs the reference balance in dB, aligned so that the median band reads 0: + = louder
// than the reference relative to the rest of the spectrum. (Plain share ratios saturate for big
// bands: +6 dB of level in the 45 % bass band would only read +2.3 dB.) Returns false (all 0) for
// silence. bandEnergy has kNumBands entries on any common scale.
bool balanceVsReference(const double* bandEnergy, const std::array<double, kNumBands>& ref, double* outDb) noexcept;

// Images (each throws std::runtime_error on I/O failure).
void renderOverview(const MixImpl& m, const std::string& path);
void renderLoudness(const MixImpl& m, const std::string& path);
void renderTracks(const MixImpl& m, const std::string& path);
void renderBands(const MixImpl& m, const std::string& path);
void renderStereo(const MixImpl& m, const std::string& path);
void renderSpectrogram(const MixImpl& m, const std::string& path);
// spectrogram.png plus the zoomed spectrograms (MixImpl::zooms) into dir.
void renderSpectrograms(const MixImpl& m, const std::string& dir, bool whole, bool sectionZooms);
// clicks[i].image (must be set) under dir.
void renderClickImage(const MixImpl& m, std::size_t i, const std::string& path);

}  // namespace as::analysis
