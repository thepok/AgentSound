#pragma once

// Dynamics and tone effects:
//   eq (7-band SVF: hp, low shelf, 3 peaks, high shelf, lp), filter (resonant SVF / ladder sweeps),
//   compressor (feed-forward, stereo-linked, sidechain), ducker (sidechain or tempo-synced pump),
//   saturator (4x oversampled + ADAA: tape|tube|hard|fold), limiter (true-peak lookahead brickwall),
//   width (M/S + Linkwitz-Riley mono bass), bitcrush, utility, deesser (split-band sibilance control).

#include "core/Module.h"

#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace as {

// Returns a new, unconfigured effect of the given type, or nullptr if the type is not one of ours.
std::unique_ptr<Effect> createDynamicsEffect(std::string_view type);

// The type names createDynamicsEffect understands.
std::vector<std::string> dynamicsEffectTypes();

// True for the types that use a "sidechain" key signal (compressor, ducker).
bool dynamicsEffectAcceptsSidechain(std::string_view type);

}  // namespace as
