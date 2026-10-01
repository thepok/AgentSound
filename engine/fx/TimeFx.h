#pragma once

// Time-based and modulation effects:
//   chorus (Juno-60 BBD modes + custom), flanger, phaser, delay (tape-style, tempo-synced),
//   reverb (16-line modulated FDN: plate|hall|room|chamber|cathedral), gatedreverb (80s gated snare),
//   tremolo (incl. autopan), ensemble (3-phase string-machine chorus: Solina / RS style),
//   vowel (formant filter: a|e|i|o|u, continuous morph, size shift).

#include "core/Module.h"

#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace as {

// Returns a new, unconfigured effect of the given type, or nullptr if the type is not one of ours.
std::unique_ptr<Effect> createTimeEffect(std::string_view type);

// The type names createTimeEffect understands.
std::vector<std::string> timeEffectTypes();

// True for the types that use a sidechain key: 'delay' (key drives 'duck') and 'gatedreverb'
// (key opens the gate). The others ignore a key.
bool timeEffectAcceptsSidechain(std::string_view type);

}  // namespace as
