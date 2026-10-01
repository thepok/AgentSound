#pragma once

// Silent notes, render-time ear: notes of a track that made no audible sound. Every analysed track with notes (any
// instrument: va, dx7, drums, sf2, sampler, stack) is measured on its own post-fader signal (the 2.5 ms envelope of
// NoteDynamics' OnsetEnvelope). Notes starting within 30 ms are one event (a chord, a kick under a crash). An event's
// level is the loudest 10 ms window between its start and min(its end + 0.25 s, its start + 3 s, the next event - 5 ms)
// (at least 30 ms): a slow attack, a release-triggered sample or a note delayed inside a stack still counts, and a
// note that rings under its own sustain, a legato / tied note or a grace note inside another note's tail reads the
// sound that is there - only a note with nothing audible anywhere in its own span can be silent.
// Two kinds, by whether the note has an attack of its own (its level rises 3+ dB over the 10 ms just before it, above
// -100 dBFS): a note that adds NOTHING to what was sounding is silent under max(median - 40 dB, min(-60 dBFS, median -
// 30 dB)), median = the median level of the track's events: 40 dB under its typical note, or under -60 dBFS when that
// is 30+ dB under it (a whole track that quiet is 'silent_node' / 'inaudible', not this); a note WITH an attack does
// sound and is 'too quiet to be heard' only 40 dB under the median. Excused (counted, never warned): a silent event
// while an automation lane of the track has closed the level - gainDb / a level / gain / output lane 30+ dB under its
// own maximum, an expression / volume / dynamics lane under 10 % of its maximum, a cutoff 4+ octaves under its maximum
// and below 300 Hz, a (layer) mute lane on -, and on a track with a vocoder insert (its carrier sounds only while the
// modulator speaks). Notes starting in the last 50 ms of the render are not judged.
// Findings: the compiler's own silent notes (render JSON analysis.silentNotes: notes that reach no sample zone, no
// drum piece, only muted stack layers - agentsound/silent_notes.py) are repeated as 'silent_notes' warnings with how
// many of them the render measured silent; silent events the compiler did not explain get their own 'silent_notes'
// warning (count, pitches - GM names on drum instruments -, bar:beat times, levels): 'made no sound' (warn) or
// 'too quiet to be heard' (info). The compiler's findings: warn.

#include "analysis/NoteDynamics.h"  // DynamicsFinding, OnsetEnvelope
#include "core/Params.h"           // json

#include <string>
#include <vector>

namespace as::analysis {

struct MixImpl;

// Thresholds (dB).
inline constexpr double kSilentBelowMedianDb = 40.0;
inline constexpr double kSilentAbsoluteDb = -60.0;
inline constexpr double kSilentQuietTrackDb = 30.0;

// The silence threshold of a track whose events have median level `medianDb`.
double silentThresholdDb(double medianDb) noexcept;

// Loudest 10 ms window level (dBFS RMS) of the envelope inside [t0, t1] seconds (at least one window from t0).
double spanLevelDb(const OnsetEnvelope& env, double t0, double t1);

// Fills nodes[].silentNotes (returned, parallel to MixImpl::nodes; null for nodes without notes) and the findings.
std::vector<json> assessSilentNotes(MixImpl& m, std::vector<DynamicsFinding>& findings, std::vector<std::string>& suggestions);

}  // namespace as::analysis
