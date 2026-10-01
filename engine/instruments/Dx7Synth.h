#pragma once

// "dx7": Yamaha DX7 six-operator FM synthesizer playing the original ROM cartridge voices.
// DSP core: vendored MSFA (third_party/msfa, Apache-2.0, from Dexed, fidelity-patched by Msound2).
//
// The voice is chosen with the string-valued key "voice" (not a ParamSpec because ParamSpecs are
// numeric); see kDx7VoiceParamHelp and Dx7Banks.h. Banks are loaded in prepare() from
// RenderContext::assetDir + "/dx7/*.syx"; an unknown voice throws ConfigError from prepare().

#include "core/Module.h"

#include <memory>

namespace as {

std::unique_ptr<Instrument> makeDx7Synth();

inline constexpr const char* kDx7VoiceParamHelp =
    "voice (string, default \"E.PIANO 1\"): DX7 ROM voice by name (\"E.PIANO 1\", \"bass 1\"; case and "
    "extra spaces ignored, first match across rom1a..rom4b), \"bank:name\" (\"rom3a:E.PIANO 1\") or "
    "\"bank:index\" with a 0-based index 0..31 (\"rom1a:10\" = E.PIANO 1). Famous synthwave picks: "
    "E.PIANO 1, BASS 1, SYN-BASS 1, BRASS 1, SYNBRASS 1, STRINGS 1, MARIMBA, TUB BELLS, VIBE 1, "
    "HARP 1, CLAV 1, FLUTE 1, SYN-LEAD 1, E.ORGAN 1.";

}  // namespace as
