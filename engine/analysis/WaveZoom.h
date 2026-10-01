#pragma once

// Sample-accurate waveform zoom PNG (1600 px wide): used for the click images of the report and by
// `agentsound zoom <wav>`.
//
//   main view    centre +- halfMs, one lane per source and channel (auto-scaled, amplitude labels)
//   detail view  centre +- detailHalfMs, one lane per source with L and R overlaid, every sample a dot
//   strip        tiny spectrogram of the first source over the main view (a click is a vertical line)
// Time axes are in ms relative to the centre; markers (e.g. detected clicks) are red dashed lines.

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace as::analysis {

struct WaveSource {
    std::string name;        // lane label, e.g. "mix" or "'bass'"
    std::vector<float> L, R; // samples around the centre
    std::int64_t centre{0};  // index of the centre sample in L/R
};

struct WaveZoomSpec {
    double sampleRate{48000.0};
    double halfMs{15.0};
    double detailHalfMs{1.5};
    bool showL{true}, showR{true};
    std::vector<WaveSource> sources;  // sources[0] also feeds the spectrogram strip
    std::string title, subtitle;
    std::vector<std::pair<double, std::string>> markers;  // (ms relative to the centre, label)
    bool spectrogramStrip{true};
};

void renderWaveZoom(const WaveZoomSpec& spec, const std::string& path);  // throws std::runtime_error on I/O failure

}  // namespace as::analysis
