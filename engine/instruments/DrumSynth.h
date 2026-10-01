#pragma once

// "drums": fully synthesized drum machine (no samples) with TR-808, TR-909, LinnDrum-style,
// synthwave and modern kits. GM-style note map:
//   35/36 kick      37 rim/sidestick   38 snare, 40 brighter snare   39 clap
//   42 closed hat   44 pedal hat       46 open hat (choked by 42/44)
//   41/43 low tom   45/47 mid tom      48/50 high tom (43/47/50 sit 2 semitones above 41/45/48)
//   49/57 crash (57 = smaller, higher)  51/59 ride (59 = more bell)  54 tambourine/shaker  56 cowbell
// Other pitches are ignored. Hits are one-shots (noteOff is ignored). Timbre parameters are latched
// per hit; level, pan and width are smoothed and act on ringing hits too. Clap, crash and ride have a
// mono-compatible stereo width; the kits are loudness-matched (switching kit keeps the balance).
//
// The "kit" choice sets every per-piece default; explicit per-piece values override it, e.g.
// {"kit": "909", "snare.decay": 0.3}.

#include "core/Module.h"

#include <memory>
#include <string_view>

namespace as {

std::unique_ptr<Instrument> makeDrumSynth();

// Current value of a drums parameter (after configure/setParam), e.g. to check the resolved kit
// defaults. NaN if `drums` was not made by makeDrumSynth() or `name` is unknown.
float drumSynthParam(const Instrument& drums, std::string_view name);

}  // namespace as
