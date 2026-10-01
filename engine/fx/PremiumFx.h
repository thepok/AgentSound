#pragma once

// Premium colour and space effects (the "expensive 80s production" toolbox):
//   microshift (H910 / H3000 / MicroShift-style micro-pitch stereo widener), shimmer (reverb with an
//   octave-up (+ fifth) pitch-shifted feedback loop), tape (saturation, head bump, HF roll-off,
//   wow & flutter, hiss), exciter (Aphex-style alias-free harmonic exciter), dimension (Roland
//   SDD-320 style mono-compatible spatial chorus).

#include "core/Module.h"

#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace as {

// Returns a new, unconfigured effect of the given type, or nullptr if the type is not one of ours.
std::unique_ptr<Effect> createPremiumEffect(std::string_view type);

// The type names createPremiumEffect understands (none of them uses a sidechain key).
std::vector<std::string> premiumEffectTypes();

}  // namespace as
