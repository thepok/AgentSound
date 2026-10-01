#pragma once

// Note-level dynamics ("are all the lead notes equally loud?"): every analysed track keeps a 2.5 ms
// mean-square envelope while it renders (OnsetEnvelope, fed with the node audio); the report finds the
// note onsets (from the render JSON's notes when the routing is known - chord notes within 30 ms are
// one event -, else from the audio: 10 ms level rises of 6+ dB), measures each onset's level (mean
// square over the first 30-100 ms of the note, up to the next onset) and reports the 10-90 percentile
// spread of those levels overall, per section and per phrase (~8-bar chunks of the sections).
// The audio spread alone over-reads: a chorus / microshift wobble, the register or the samples scatter
// note levels by several dB although every note is played the same. So when the velocities are known,
// the level's response to velocity is measured too (regression inside the phrases on what each note adds
// over the sound before it, register removed, minus one standard error, clamped to what a velocity curve
// can do) and the played dynamics of a phrase are
// min(audio spread, response x the phrase's 10-90 % velocity range); with expression / dynamics
// automation (dynamics without velocity) only the audio counts. A melodic lead whose median played
// dynamics stay under the profile's noteSpreadMinDb (default 3 dB, jazz 4, classical 4.5) with 8+ notes
// per phrase is 'flat_dynamics' (warn; other melodic parts, and bass lines under jazz / classical: info).
// Drums, fx, pads/beds, arps/sequences and pulse parts (8ths/16ths on a fixed grid) are never flagged:
// even velocities are their idiom.

#include "core/Params.h"  // json

#include <string>
#include <vector>

namespace as::analysis {

struct MixImpl;

// Streaming 2.5 ms mean-square envelope of a stereo signal (mean of L^2 and R^2 per hop).
class OnsetEnvelope {
public:
    explicit OnsetEnvelope(double sampleRate, double secondsHint = 0.0);
    void feed(const float* left, const float* right, int frames);  // non-finite samples count as silence
    void finalize();                                              // flushes a partial last hop
    const std::vector<float>& meanSquare() const noexcept { return ms_; }
    double hopSec() const noexcept { return hopSec_; }
    int hop() const noexcept { return hop_; }

private:
    int hop_{120};
    double hopSec_{0.0025};
    double acc_{0.0};
    int n_{0};
    std::vector<float> ms_;
};

// Level (dBFS RMS, full-scale sine = -3) of the note starting at `sec`: the mean square over
// [sec, sec + window], window = clamp(nextSec - sec - 5 ms, 30 ms, 100 ms). nextSec <= sec: no next onset.
// attackDb (optional): the energy the note adds over what was sounding just before it (mean square of the
// window minus that of [sec - 12 ms, sec - 2 ms]), dBFS; kDbFloor when it adds less than a quarter of the
// window's energy (a legato note without a new attack, a note buried under ringing ones).
double onsetLevelDb(const OnsetEnvelope& env, double sec, double nextSec, double* attackDb = nullptr);

// Onsets found in the audio alone (seconds): 10 ms level rises of >= 6 dB that reach within 45 dB of
// the loudest level (and above -70 dBFS), at least 50 ms apart.
std::vector<double> detectOnsets(const OnsetEnvelope& env);

// 10-90 percentile spread of `levels` (dB); 0 for fewer than 2 values. p10/p90 are optional outputs.
double percentileSpread(std::vector<double> levels, double* p10 = nullptr, double* p90 = nullptr);

// Result per track, kept for the images.
struct NoteDynamicsResult {
    bool measured{false};
    std::string kind;          // lead, melodic, bass, bed, even, drums, fx
    int events{0};
    double spreadDb{0.0};       // audio, whole song, 10-90 %
    double dynamicsDb{0.0};     // the judged number: played dynamics, median over the phrases
    int severity{-1};           // -1 fine / not judged, 1 warn, 2 info
    std::string mark;           // short label for tracks.png ("FLAT 0.4 dB", "2/6 phrases flat"), empty = none
};

// One warning of the assessment (severity 1 warn, 2 info).
struct DynamicsFinding {
    int severity{1};
    std::string code, message;
    std::vector<std::string> sections, nodes;
};

// Fills MixImpl::nodes[].dynamics and returns the per-node json (nodes[].dynamics, parallel to
// MixImpl::nodes; null for nodes without a measure). Needs the roles (assessSpace) and the node
// section levels (sectionRmsDb): the report builder calls it after both.
std::vector<json> assessDynamics(MixImpl& m, std::vector<DynamicsFinding>& findings, std::vector<std::string>& suggestions);

}  // namespace as::analysis
