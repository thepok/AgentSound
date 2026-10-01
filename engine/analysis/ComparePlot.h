#pragma once

// compare.png: the picture of a reference comparison (compare.json of `python -m agentsound compare`,
// agentsound/compare.py). Same look as the other analysis images (1600 px wide, dark, bitmap text):
//   title + loudness match (both files' integrated loudness, the offset used)
//   SPECTRUM     loudness-matched 1/3-octave spectra (dB re each file's integrated loudness), mix vs reference
//   DIFFERENCE   mix - reference per 1/3 octave (bars), smoothed (line), the +-tolerance zone, and the
//                regions the suggestions are about, labelled with their size and range
//   STEREO       width (side/mid %) per octave, mix vs reference, with the L/R correlation per octave
//   DYNAMICS     short-term loudness distributions (relative to the integrated loudness), p10 / p95
//   METRICS      the table of compare.json 'metrics' (mix | reference | difference)
//   SUGGESTIONS  the prioritised suggestions
// Engine CLI: agentsound compare-png <compare.json> --out <png>.

#include "core/Params.h"  // as::json

#include <string>

namespace as::analysis {

// Throws ConfigError when a required field is missing or malformed, std::runtime_error on I/O failure.
void renderComparePng(const json& compare, const std::string& path);

}  // namespace as::analysis
