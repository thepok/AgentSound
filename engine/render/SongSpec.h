#pragma once

// Parsed, validated form of a render JSON document (docs/RENDER_FORMAT.md).

#include "core/Params.h"
#include "core/TempoMap.h"

#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace as {

enum class Curve { Linear, Exp, Smooth, Step };

struct NoteSpec {
    double startBeat{};
    double durationBeats{};
    int pitch{};
    int velocity{};
};

struct AutomationPoint {
    double beat{};
    double value{};
    Curve curve{Curve::Linear};  // shape of the segment arriving at this point
};

struct AutomationLane {
    std::string target;  // "instrument.x", "fx.N.x", "gainDb", "pan", "send.<bus>"
    std::vector<AutomationPoint> points;
    std::string path;    // JSON path for error messages
};

// ---- taps: where a send, a sidechain key or a follower picks up a node's signal ("tap" in the render JSON,
// docs/RENDER_FORMAT.md "Taps")
//   kTapPost (-1)      "post"      after the inserts, the fader (gainDb) and the pan: the default
//   kTapPreFader (-2)  "prefader"  after the inserts, before the fader and the pan
//   0..N               "prefx" (= 0) / "pre:<i>": the signal entering insert i of the tapped node (0: the dry
//                      instrument output / the summed bus input); "pre:<fx count>" is the "prefader" point
inline constexpr int kTapPost = -1;
inline constexpr int kTapPreFader = -2;
std::string tapName(int tap);

// ---- modulators ("parameters are instruments too", see docs/RENDER_FORMAT.md "Modulators")

enum class ModSource { Lfo, Steps, Follow, Envelope, Random };
enum class LfoShape { Sine, Triangle, Saw, Ramp, Square, Random, SmoothRandom };

// Fields of a modulator that 'mod.<index>.<field>' automation lanes can drive.
enum class ModField {
    Depth, Min, Max, Base, RateBeats, RateHz, Phase, Glide, Smooth,
    AttackMs, ReleaseMs, GainDb, AttackBeats, DecayBeats, Sustain, ReleaseBeats
};
inline constexpr int kModFieldCount = 16;

struct ModulatorSpec {
    std::string target;              // same grammar as automation targets (no 'mod.' targets)
    ModSource source{ModSource::Lfo};
    // lfo (shape, rate, phase, retrigger) / random (rateBeats, smooth)
    LfoShape shape{LfoShape::Sine};
    double rateBeats{0.0};           // cycle (lfo) or hold (random) length in beats; 0 when rateHz is used
    double rateHz{0.0};              // lfo only; 0 when rateBeats is used
    double phase{0.0};               // 0..1 cycles
    bool retrigger{false};           // lfo: restart on every note-on of this track
    double smooth{0.0};              // random: fraction of a step used to glide to the new value
    // steps
    std::vector<double> values;
    double stepBeats{0.0};
    double glide{0.0};               // fraction of a step used to glide into its value
    bool loop{true};
    // follow
    std::string followNode;          // track or bus id (post-fader output by default, like a sidechain key)
    int followTap{kTapPost};         // where on that node the follower listens ("tap")
    double attackMs{5.0};
    double releaseMs{120.0};
    double gainDb{0.0};
    // envelope
    double attackBeats{0.0};
    double decayBeats{0.5};
    double sustain{0.0};
    double releaseBeats{0.25};
    std::string trigger;             // empty = this track's notes, else a track id
    // mapping
    bool offset{false};              // mode: false = absolute (min..max), true = offset (+ source * depth)
    bool expCurve{false};            // absolute: geometric min..max; offset: depth in octaves (x 2^(s*depth))
    double min{0.0};
    double max{1.0};
    double depth{0.0};
    std::optional<double> base;      // value under the modulator when the target has no automation lane
    // active window (song beats); outside it the modulator contributes nothing
    std::optional<double> startBeat;
    std::optional<double> endBeat;
    std::string path;                // JSON path for error messages

    bool unipolar() const { return source == ModSource::Follow || source == ModSource::Envelope; }
    bool windowed() const { return startBeat.has_value() || endBeat.has_value(); }
};

const char* modFieldName(ModField field);
// Valid range of `field` for this modulator; false when the field does not apply to it
// (e.g. 'min' in offset mode, 'rateHz' on a tempo-synced lfo, 'base' when none is given).
bool modFieldRange(const ModulatorSpec& spec, ModField field, double& lo, double& hi);
// The field's value as given in the render JSON.
double modFieldValue(const ModulatorSpec& spec, ModField field);

struct FxSpec {
    std::string type;
    json params = json::object();
    std::string sidechain;       // node id or empty
    int sidechainTap{kTapPost};  // where on the key node the key is tapped ("tap")
    std::string path;
};

struct SendSpec {
    std::string bus;
    float db{};
    int tap{kTapPost};           // "post" (default) | "prefader" | "prefx" / "pre:<i>"
};

struct NodeSpec {
    std::string id;
    enum class Kind { Track, Bus, Master } kind{Kind::Track};
    std::string instrumentType;
    json instrumentParams = json::object();
    std::vector<FxSpec> fx;
    float gainDb{0.0f};
    float pan{0.0f};
    bool mute{false};
    std::string output{"master"};
    std::vector<SendSpec> sends;
    std::vector<NoteSpec> notes;
    std::vector<AutomationLane> automation;
    std::vector<ModulatorSpec> modulators;
    std::string path;
};

struct SectionSpec {
    std::string name;
    double startBeat{};
    double endBeat{};
};

// "analysis": report settings (docs/RENDER_FORMAT.md "Analysis profiles"); they never change the audio.
// "analysis.silentNotes": notes the compiler found no sound for (agentsound/silent_notes.py: no sample zone, no drum
// piece, only muted stack layers); the report repeats them as 'silent_notes' warnings next to what the render measured.
struct SilentNoteHint {
    std::string track;
    std::string kind;              // "no_sound" | "muted_layers"
    std::vector<int> pitches;
    int count{0};
    std::vector<double> beats;     // the first ones (song beats)
    std::string message;
};

struct AnalysisSpec {
    std::string profile{"default"};  // a name from analysis/Profiles.h (validated by parseSong)
    std::optional<std::pair<double, double>> loudness;  // integrated LUFS target override (min < max)
    std::vector<SilentNoteHint> silentNotes;
    // "analysis.audioOnsets": tracks whose notes trigger whole phrases (a singer's takes: one note per sung phrase,
    // the dynamics inside the audio) - their note dynamics are measured from the audio's own onsets
    std::vector<std::string> audioOnsets;
};

struct SongSpec {
    std::string title;
    int sampleRate{48000};
    double tempo{120.0};                 // "tempo" (BPM); with a "tempoMap": its tempo at beat 0
    std::vector<TempoPoint> tempoMap;    // "tempoMap" points; empty = the constant `tempo`
    std::vector<MeterPoint> meter;       // "meter" ([beat, numerator, denominator]); empty = 4/4
    double lengthBeats{0.0};
    double tailSeconds{4.0};
    std::uint64_t seed{1};
    std::vector<SectionSpec> sections;
    std::vector<NodeSpec> nodes;  // tracks, then buses, then the master (always last, id "master")
    bool exportStems{false};
    int bitDepth{24};
    AnalysisSpec analysis;

    // Song time: the tempo map (a constant one for "tempo") at the song's sample rate, and the bars.
    TempoMap makeTempoMap() const;
    MeterMap makeMeterMap() const;
    double beatToSeconds(double beat) const;
};

// Strict parse + structural validation (ids, references, ranges). Module-level
// parameter validation happens later when modules are configured.
// Throws ConfigError with a JSON path in the message.
SongSpec parseSong(const json& document);

// Just the song time of a render JSON, or of a report's "render" block (which repeats them): "sampleRate",
// "tempoMap" (else "tempo") and "meter", validated like parseSong; every other key is ignored.
struct SongTiming {
    int sampleRate{48000};
    double tempo{120.0};
    std::vector<TempoPoint> tempoMap;
    std::vector<MeterPoint> meter;
};
SongTiming parseTiming(const json& document);

}  // namespace as
