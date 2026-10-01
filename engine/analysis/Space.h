#pragma once

// Internal: the 'space' assessment of the report (Space.cpp) - is the mix dry, narrow, thin, lush or
// washy? It classifies every node (drums, bass, bed, lead, other, fx one-shot; buses as effect
// returns by kind or groups), then measures per section and over the full sections:
//   width      stereo width (side/mid %) of the mix, of its part above 150 Hz (the low end should be
//              mono, so the image above it is what sounds wide or narrow) and of the music parts
//              (non-drum, non-bass tracks); correlation.
//   wetness    reverb-return (and echo-return) level vs the pre-master sum of everything that feeds
//              the master (LU below the mix), per return and total; the returns' low-end share;
//              tail audibility at breaks: the returns' level 0.3-0.8 s after the music stops.
//   bed        sustained parts (pads/strings/choir: long notes or steady envelopes) vs the lead
//              while the lead plays (K-weighted dB).
// and turns it into a verdict (washy > dry > narrow > ok/lush), warnings (dry_mix, narrow_mix,
// thin_bed, washy, over_wide, reverb_inaudible) and suggestions phrased with the node ids, current send
// levels and render-format effects. Thresholds come from the analysis profile (Profiles.h, "space
// targets"); they were calibrated on the composed songs (dry / narrow / thin, flagged), a lush variant
// of one of them (wide pads, 100 % Juno chorus, hall ~8 LU under the mix: passes) and an over-wet one
// (flagged washy).

#include "core/Params.h"

#include <initializer_list>
#include <optional>
#include <string>
#include <vector>

namespace as::analysis {

struct MixImpl;

enum class Role { Unknown, Drums, Bass, Bed, Lead, Other, Fx, Return, Group };
enum class ReturnKind { None, Reverb, Delay, Gated, Width, Other };
const char* roleName(Role r) noexcept;
const char* returnKindName(ReturnKind k) noexcept;

// Space measures of one section (or of the full sections together: SpaceData::global).
struct SpaceSection {
    bool full{false};                  // within 4 LU of the loudest section, drums playing (the "full" arrangement)
    bool assessed{false};              // not silent
    bool quiet{false};                 // > 10 LU under the loudest section (fades, tails, breaks): measured, not judged
    double widthPct{0.0}, corr{1.0};   // whole mix
    double hiWidthPct{0.0}, hiCorr{1.0};  // mix above 150 Hz
    std::optional<double> musicWidthPct;  // music tracks (non-drum, non-bass)
    std::optional<double> wetLu;       // reverb returns vs the (pre-master) mix, LU (none: no reverb return)
    std::optional<double> echoLu;      // delay returns vs the mix
    double returnLowPct{0.0};          // share of the reverb returns' energy below 150 Hz
    std::optional<double> bedVsLeadDb; // bed level under the lead while it plays (dB, - = bed quieter)
    bool leadPlays{false}, bedPlays{false};
    int lead{-1};                      // node index of the lead measured
    std::vector<int> beds;             // bed nodes playing
    std::vector<std::pair<int, double>> returnsLu;  // (return node, LU vs the mix)
    std::string verdict{"ok"};         // washy | dry | narrow | ok | lush (| quiet | silent)
    std::vector<std::string> issues;   // dry, narrow, washy, thin_bed, no_reverb, low_wash, phasey
};

// Level of the effect returns just after the music stops (a break, a stop, the song end).
struct SpaceTail {
    double sec{0.0};       // where the music stops
    double tailDb{0.0};    // returns 0.3-0.8 s later vs the music before the stop (dB)
    double decaySec{0.0};  // how long the returns stay within 40 dB of the music before
    bool capped{false};    // the music came back (or the audio ended) before the tail fell 40 dB
};

struct SpaceData {
    bool assessed{false};
    bool routing{false};               // node routing was given (else ids / audio were used)
    bool preMasterRef{false};          // returns measured against the sum of the master's inputs
    std::vector<SpaceSection> sections;  // parallel to MixImpl::sections
    SpaceSection global;               // over the full sections
    std::vector<int> reverbReturns, delayReturns, refNodes;  // refNodes empty: the final mix is the reference
    std::vector<std::pair<int, double>> echoActiveLu;  // delay returns: LU vs the mix while they sound (full sections)
    std::vector<SpaceTail> tails;
    std::optional<double> tailDb;      // median over the tails
    std::vector<int> opportunities;    // centred music nodes that would widen the mix most
    std::vector<double> opportunityWidth;  // their width in the full sections (%)
};

// One warning of the assessment (severity 0 error, 1 warn, 2 info).
struct SpaceFinding {
    int severity{1};
    std::string code, message;
    std::vector<std::string> sections, nodes;
};

// Id matching of the role guesses: a token of the id ("hook-double" -> hook, double; "lead2" -> lead)
// starts with one of `prefix` or equals one of `exact`, or the lower-case id contains one of `anywhere`.
bool idNamed(const std::string& id, std::initializer_list<const char*> prefix, std::initializer_list<const char*> anywhere = {},
             std::initializer_list<const char*> exact = {});

// Fills MixImpl::nodes[].role/returnKind and MixImpl::space, returns report["space"]. Needs the
// finished streams, sections with lufs, nodes with dominantBand/rmsDb/peakDb (the report builder
// calls it after the nodes).
json assessSpace(MixImpl& m, std::vector<SpaceFinding>& findings, std::vector<std::string>& suggestions);

}  // namespace as::analysis
