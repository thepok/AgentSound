// clicks/click_NN.png: sample-accurate zoom of one detected click (mix, plus the attributed
// track/bus from the snippet its detector kept).

#include "analysis/MixImpl.h"
#include "analysis/PlotKit.h"
#include "analysis/WaveZoom.h"

#include <algorithm>
#include <cmath>

namespace as::analysis {

void renderClickImage(const MixImpl& m, std::size_t i, const std::string& path) {
    const ClickInfo& k = m.clicks.at(i);
    const double sr = m.sampleRate;
    WaveZoomSpec spec;
    spec.sampleRate = sr;
    spec.halfMs = 15.0;
    spec.detailHalfMs = 1.5;
    // Mix around the click, with a margin for the spectrum strip's frames.
    const auto half = static_cast<std::int64_t>(std::lround((spec.halfMs + 5.0) * 0.001 * sr));
    const auto len = static_cast<std::int64_t>(m.mixL.size());
    WaveSource mix;
    mix.name = "mix";
    const std::int64_t a = std::max<std::int64_t>(0, k.sample - half), b = std::min(len, k.sample + half + 1);
    if (b > a) {
        mix.L.assign(m.mixL.begin() + a, m.mixL.begin() + b);
        mix.R.assign(m.mixR.begin() + a, m.mixR.begin() + b);
    }
    mix.centre = k.sample - a;
    spec.sources.push_back(std::move(mix));
    const std::string who = k.node >= 0 ? "'" + m.nodes[static_cast<std::size_t>(k.node)].id + "'" : std::string("master");
    if (k.node >= 0 && k.nodeEvent && !k.nodeEvent->snipL.empty()) {
        WaveSource node;
        node.name = who;
        node.L = k.nodeEvent->snipL;
        node.R = k.nodeEvent->snipR;
        node.centre = static_cast<std::int64_t>(node.L.size() / 2) + (k.sample - k.nodeEvent->sample);
        spec.sources.push_back(std::move(node));
    }
    static const char* kSev[] = {"HIGH", "MEDIUM", "LOW"};
    spec.title = sfmt("CLICK %d/%d [%s]  %s (%.4f s) | %s | %s | jump %.1f dBFS, %.0f dB above its surroundings | channel %s",
                      static_cast<int>(i) + 1, std::max(static_cast<int>(m.clicks.size()), m.clicksInMix + m.clicksMasked),  // total, not the capped list
                      kSev[std::clamp(k.severity, 0, 2)], mmssMs(k.sec).c_str(), k.sec, m.barBeat(k.sec).c_str(),
                      who.c_str(), k.jumpDb, k.contrastDb, k.channels == 1 ? "L" : k.channels == 2 ? "R" : "both");
    std::string sub = k.inMix ? "audible in the mix" : "masked in the mix: only detectable in " + who;
    if (k.node < 0) sub += "; found in no single track/bus: master chain or the sum of parts";
    if (k.nodes.size() > 1) {
        sub += "; same click in";
        for (int n : k.nodes) sub += " '" + m.nodes[static_cast<std::size_t>(n)].id + "'";
    }
    sub += " | red line = start of the discontinuity";
    spec.subtitle = sub;
    spec.markers.push_back({0.0, "click"});
    renderWaveZoom(spec, path);
}

}  // namespace as::analysis
