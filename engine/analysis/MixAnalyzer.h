#pragma once

// The composing agent's "ears": measures the rendered mix and every track/bus while the song
// renders and turns it into report.json plus a set of focused PNGs (writeImages).
//
// Usage (engine/render/Renderer):
//   prepare(sr, bpm, sections, hint) [-> setTimeGrid / setStartBeat / setProfile / setLoudnessTarget] -> addNode(...)*
//   [-> setRouting(song) / setNodeRouting(...)] -> { feedNode(...)* feedMix(...) }* -> finish() -> writeImages(dir)
// The full stereo mix is kept in memory (float). Nodes are summarised on a 100 ms grid plus exact
// sums between bar/section boundaries, and run a streaming click detector that keeps +-15 ms of
// audio around its strongest events; no other node audio is stored. Node feeds must line up
// sample-exactly with the mix (the master latency is removed from the mix only).
//
// Images (1600 px wide, same time axis, section strip and bar numbers on every timeline image):
//   overview.png                dashboard + index: loudness, SPACE verdict per section, per-track levels, clicks, top issues
//   loudness.png                waveform L/R + momentary/short-term LUFS, section table
//   tracks.png                  per-track/bus level lanes with section values and dominant band
//   bands.png                   7-band share over time + balance vs reference per section
//   stereo.png                  correlation, width (whole / above 150 Hz vs target), wetness (reverb + echo returns vs
//                               the mix), SPACE strip, low-end mono, balance over time + stereo field with roles
//   spectrogram.png             whole song
//   spectrogram_NN_<name>.png   one zoom per section (16-bar chunks without sections): ~20 ms
//                               spectrogram, beat grid, level strip
//   clicks/click_NN.png         the worst 8 clicks: sample-accurate +-15 ms waveform zoom
// report["images"] lists them with what each shows (as planned by finish(); the renderer writes
// them unless --no-png). Stale spectrogram_NN_* / clicks/click_NN images in dir are removed.
//
// Report (json; write it with formatReport(), which also puts the keys in reading order):
//   summary        one-line digest (length, analysis profile, LUFS vs target, true peak, LRA, stereo, space verdict,
//                  tilt, band balance)
//   space          dry / narrow / thin / lush / washy (analysis/Space.h): verdict + issues, width (whole, above
//                  150 Hz, music parts), reverb/echo returns vs the (pre-master) mix, bed vs lead, tails at stops,
//                  per section, over the full sections, returns[], roles, opportunities, targets
//   global         durationSec, lufsIntegrated, loudnessRange, shortTermMax, momentaryMax, truePeakDbtp,
//                  samplePeakDb, plr, rmsDb, crestDb, clippedSamples, dcOffset[L,R], stereoCorrelation,
//                  widthPct, balanceLrDb, lowEndCorrelation, bandsPct/bandsDb/bandsVsRefDb (sub bass lowmid mid presence
//                  brilliance air), subsonicPct, spectralTiltDbPerOct vs referenceTiltDbPerOct, centroidHz,
//                  thirdOctave {hz[], vsRefDb[]}
//   sections[]     name, start/end (sec and bar), lufs (gated), shortTermMax, peakDb, rmsDb, correlation,
//                  widthPct, lowEndCorrelation, bandsPct, bandsVsRefDb, active[] {id, rmsDb, sharePct}
//   nodes[]        id, bus, role (+ returnKind), peakDb, rmsDb (while active), lufs, crestDb, activePct, dominantBand, centroidHz,
//                  bandsPct, mixSharePct {per band + total}, correlation, widthPct, balanceLrDb, lowEndCorrelation,
//                  sections[] {section, rmsDb, sharePct}, barsRmsDb[] (one value per timeline row),
//                  dynamics (tracks with notes / onsets: note-level dynamics, analysis/NoteDynamics.h)
//   timeline       {barSec, columns[], rows[][]}: per song bar (4/4 unless the song has a meter) lufs, peakDb, widthPct
//                  and 7 band levels
//   clicks[]       detected clicks/pops, most severe first: severity high|medium|low, time (m:ss.mmm), sec,
//                  bar, beat, node (track/bus showing it, "master" = none), nodes[] (all), inMix, jumpDb,
//                  contrastDb, channel, image; global.clicks / global.clicksMasked
//                  count all of them (in the mix / only in single parts; the list keeps the worst 40)
//   images[]       {file, shows}: the PNGs of writeImages()
//   warnings[]     {severity error|warn|info, code, message, sections?, nodes?}, most important first
//   suggestions[]  concrete fixes phrased in render-format terms
//   reference      the analysis profile used (name, description) and its targets: band shares, tilt,
//                  loudness window (lufsTarget, lufsTargetFrom profile|override), band balance limits
//                  and the other thresholds; glossary explains every field.
// Clicks: see analysis/ClickDetector.h. The mix and every node run the detector; a mix click is
// attributed to the node(s) with a click within +-1.5 ms, dropped if a node has a musical onset
// there instead (a drum's attack), and node clicks without a mix click are reported as masked.
// bandsVsRefDb is each band's level vs the profile's reference balance, aligned so the median band
// reads 0 (a share ratio would saturate for the big bass band). Every spectral / loudness / dynamics
// threshold (balance_*, dull, tilt, loudness_*, squashed, lra_*, the masking band relevance) is taken
// from the profile, so e.g. the strong 41-55 Hz sub of a four-on-the-floor synthwave mix is 'sub
// high' under "default" but normal under "synthwave".

#include "core/Params.h"  // as::json
#include "core/TempoMap.h"

#include <memory>
#include <string>
#include <utility>
#include <vector>

namespace as {

struct SectionMarker {
    std::string name;
    double startSec{0.0};
    double endSec{0.0};
};

// Optional description of how a node is routed and what it plays (MixAnalyzer::setNodeRouting, or
// setRouting from the parsed song). The 'space' assessment uses it to tell effect returns (buses fed
// by sends) from groups (buses fed by outputs) and which effects they run, to measure the returns
// against the pre-master sum (so master gain does not skew "LU below the mix"), to find sustained
// beds and leads by their notes, and to phrase fixes with the actual send levels. Without it, buses
// and roles are guessed from ids and audio and returns are measured against the final mix.
struct NodeRouting {
    struct Fx {
        std::string type;               // effect type, e.g. "reverb", "delay", "chorus", "width"
        json params = json::object();   // its params as in the render JSON
    };
    std::string output{"master"};                        // bus id or "master"
    std::vector<std::pair<std::string, double>> sends;   // (bus id, send level dB: static, or the loudest automated level)
    std::vector<Fx> fx;                                  // insert chain in order
    std::string instrument;                              // track instrument type ("va", "dx7", "drums"...); "" for buses
    json instrumentParams = json::object();
    double gainDb{0.0}, pan{0.0};
    std::vector<std::pair<double, double>> notes;        // tracks: (startBeat, durationBeats) of every note
    struct Tone {
        int pitch{60};
        int velocity{100};  // 1..127
    };
    std::vector<Tone> tones;                             // optional, parallel to notes: pitch and velocity (empty = unknown)
    std::vector<std::string> automated;                  // targets moved by automation lanes (2+ points) or modulators,
                                                         // e.g. "instrument.expression", "gainDb" (note dynamics)
    struct Lane {                                        // automation lanes with 2+ points (silent notes: a note while a
        std::string target;                              // level lane is closed was silenced on purpose)
        struct Point {
            double beat{0.0}, value{0.0};
            int curve{0};  // arriving segment: 0 linear, 1 exp, 2 smooth, 3 step
        };
        std::vector<Point> points;
    };
    std::vector<Lane> lanes;
    struct KnownSilent {                                 // the compiler's silent notes of this track (analysis.silentNotes)
        std::string kind, message;
        std::vector<int> pitches;
        int count{0};
    };
    std::vector<KnownSilent> knownSilent;
};

struct SongSpec;

namespace analysis { struct MixImpl; }

class MixAnalyzer {
public:
    MixAnalyzer();
    ~MixAnalyzer();
    MixAnalyzer(MixAnalyzer&&) noexcept;
    MixAnalyzer& operator=(MixAnalyzer&&) noexcept;
    MixAnalyzer(const MixAnalyzer&) = delete;
    MixAnalyzer& operator=(const MixAnalyzer&) = delete;

    // sampleRate 8 kHz..384 kHz (throws std::invalid_argument otherwise), bpm > 0 (4/4 bars for the
    // timeline). Sections are report markers in seconds from the first rendered sample; empty or
    // inverted ones are ignored. The hint only pre-sizes buffers. Calling prepare() again resets.
    void prepare(double sampleRate, double bpm, std::vector<SectionMarker> sections, double totalSecondsHint);

    // Optional settings, after prepare() (which resets them) and before finish().
    // Analysis profile (analysis/Profiles.h): reference spectral balance, loudness target and every
    // style-dependent warning threshold. Default "default". Throws std::invalid_argument for an
    // unknown name (the message lists the profiles).
    void setProfile(const std::string& name);
    // Integrated loudness target; overrides the profile's window whatever the call order.
    // Throws std::invalid_argument unless min < max (both finite).
    void setLoudnessTarget(double minLufs, double maxLufs);
    void setStartBeat(double beat);  // song beat of the first rendered sample (preview renders) so bar numbers follow the song
    // Song time: a tempo map (bar lines, bar/beat labels and the report's tempo info follow it; a constant map
    // keeps `bpm`) and the meter (bars other than 4/4). Before feeding; copies both.
    void setTimeGrid(const TempoMap& tempo, const MeterMap& meter);

    int addNode(const std::string& id, bool isBus);  // tracks and buses, before feeding; returns the node index

    // Optional, any time before finish(): routing and material of an added node (see NodeRouting).
    // Throws std::out_of_range for a bad index.
    void setNodeRouting(int node, NodeRouting routing);
    // Optional convenience for the renderer, after the addNode() calls: fills the routing of every
    // added node from the parsed song, matched by id (nodes the song does not know are left alone).
    void setRouting(const SongSpec& song);

    // Post-fader node output, every block in timeline order. Non-finite samples are counted,
    // reported and treated as silence.
    void feedNode(int node, const float* left, const float* right, int frames);
    // Final master output (after limiter, latency-compensated).
    void feedMix(const float* left, const float* right, int frames);

    // Builds the report (call once after all audio was fed; later calls return the same report).
    json finish();

    // Require finish(). Throw std::runtime_error on I/O failure.
    void writeSpectrogramPng(const std::string& path) const;  // whole-song spectrogram only
    void writeOverviewPng(const std::string& path) const;     // dashboard only
    // Writes every image of report["images"] into `dir` (called by the renderer; dir must exist).
    void writeImages(const std::string& dir) const;

private:
    std::unique_ptr<analysis::MixImpl> impl_;
};

// Pretty-prints a report for reading: objects are indented, but short objects, warnings and all
// arrays of numbers/strings stay on one line (one bar per line in the timeline). Keys are in reading
// order (summary, warnings, suggestions, global, sections, nodes, timeline, ...; severity/code/message
// and id/name first inside entries). Prefer this over json::dump(indent), which puts every number of
// the timeline on its own line and sorts the summary and warnings to the bottom.
std::string formatReport(const json& report);

}  // namespace as
