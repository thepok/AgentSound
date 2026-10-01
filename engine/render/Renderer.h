#pragma once

#include "render/SongSpec.h"

#include <optional>
#include <string>
#include <vector>

namespace as {

// Inspection hook (tests, debugging): records the value the renderer applies to one control target
// (automation grammar: "instrument.cutoff", "fx.0.mix", "gainDb", "pan", "send.<bus>") of one node,
// once per kAutomationStep block, after automation, modulators and range clamping. NaN = the target
// was not driven in that block. values[k] belongs to the block starting at song beat beats[k] (= firstBeat +
// k * blockBeats at a constant tempo; with a tempo map the blocks span a changing number of beats).
struct ControlTrace {
    std::string node;
    std::string target;
    double firstBeat{0.0};
    double blockBeats{0.0};      // beats of the first block
    std::vector<double> values;
    std::vector<double> beats;   // song beat of each block's first sample
};

struct RenderOptions {
    std::string outDir;                 // created if missing
    std::string assetDir;               // repo assets/ (DX7 banks)
    std::optional<double> fromBeat;     // preview window (notes sustaining into it start at fromBeat)
    std::optional<double> toBeat;
    bool analysis{true};
    bool pngs{true};
    bool quiet{false};                  // no progress on stderr
    ControlTrace* trace{nullptr};       // optional: filled during the render (see ControlTrace)
};

struct RenderResult {
    double seconds{};        // length of the written mix
    double renderSeconds{};  // wall-clock time
    std::string mixPath;
    std::string reportPath;
};

// Builds every module (strict configure + prepare) and renders. Throws ConfigError for
// invalid songs (unknown types/params, routing cycles, bad automation or modulator targets).
RenderResult renderSong(const SongSpec& song, const RenderOptions& options);

// Constructs, configures and prepares all modules without rendering audio.
void validateSong(const SongSpec& song, const std::string& assetDir);

}  // namespace as
