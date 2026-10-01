#pragma once

// "va": virtual-analog polysynth (Jupiter/Juno pads and brass, JP-8000 supersaw,
// Prophet poly leads, Moog/SH-101 basses, plucks, arps, FM bells).
//
// Signal path per voice (2x oversampled below 88.2 kHz; 4-point BLEP/BLAMP oscillators):
//   unison x (osc1 [sine: phase-modulated by osc2, "fm"] + osc2 [hard sync]) + sub + noise [stereo]
//     -> anti-aliased (ADAA) drive stage
//     -> filter (ZDF transistor ladder 24 dB | TPT SVF 12 dB lp/bp/hp/notch)
//     -> amp envelope -> pan
// then halfband decimation, a global 12 dB high-pass ("hpf", Juno-style), output level and a
// safety soft clip that only acts above 0 dBFS.
//
// Modulation: the amp and filter envelopes are fixed paths; everything else is a free modulation
// matrix: the structured param "mods" is a list of routings {source, target, amount, id}, each with
// its own source (lfo per voice or global / env / velocity / key / random / macro1..8) and a
// target (pitch, osc levels and pulse widths, cutoff, resonance, drive, amp, pan, detune, fm, hpf).
// Every routing's amount is the automatable param 'mod.<id|index>.amount'.
// Every parameter (range, default, unit, help) is listed by paramSpecs().

#include "core/Module.h"

#include <memory>

namespace as {

std::unique_ptr<Instrument> makeVaSynth();

}  // namespace as
