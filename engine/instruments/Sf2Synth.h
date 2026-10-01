#pragma once

// "sf2" instrument: a SoundFont 2 player (presets of assets/soundfonts/*.sf2, default GeneralUser GS).
//
// Implements the SF2 synthesis model per voice: preset + instrument generator layering (preset
// generators add to the instrument's, local zones override global zones), key/velocity ranges,
// root key / coarse / fine / scale tuning with the sample's pitch correction, sample start/end/loop
// offsets (+ coarse), loop modes (none, continuous, until release), DAHDSR volume envelope in
// timecents (attack linear in amplitude, decay/release linear in dB, keynum-to-hold/decay), modulation
// envelope and both LFOs to pitch / filter / volume, a resonant 2-pole lowpass per voice
// (initialFilterFc/Q), initialAttenuation (x 0.4, see below), pan, exclusive classes (hi-hat choke),
// linked stereo samples (two phase-locked voices) and SF2 modulators whose sources are note-on
// velocity / key number (with the default velocity->attenuation and velocity->filter modulators;
// instrument modulators override, preset modulators add).
//
// Not implemented (documented in docs/COMPOSE_API.md): MIDI controller input (CCs sit at their
// power-on values, pitch wheel = the 'pitchbend' param), per-voice chorus/reverb sends (use buses),
// modulator links, modulated loop points.

#include "core/Module.h"

#include <memory>

namespace as {

std::unique_ptr<Instrument> makeSf2Synth();

}  // namespace as
