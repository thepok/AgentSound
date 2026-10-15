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
//
// "wavetable": the same voice engine (voices, glide, drift, unison, drive + filter, envelopes, the mods
// matrix, the global hpf) with two wavetable oscillators instead of the analog ones:
//   unison x (osc1 [table A at osc1.position, warp] + osc2 [table B, warp]) + sub [sine|tri|square|saw] + noise
// Tables (instruments/Wavetable.h): built-ins (basic pwm sync formant harmonics organ sine) or files (Serum /
// Surge / plain WAV frames, Surge .wt, single cycles), FFT-resampled to 2048-sample frames and band-limited
// per octave (mip levels: no partial above the internal Nyquist); the position crossfades neighbouring
// frames, smoothed per sample. Warps: sync, bend, mirror, fm (from the other oscillator). Extra mods targets:
// osc1.position, osc2.position, osc1.warp, osc2.warp. Tables load in prepare(); process() only reads them.

#include "core/Module.h"

#include <memory>

namespace as {

std::unique_ptr<Instrument> makeVaSynth();
std::unique_ptr<Instrument> makeWavetableSynth();

}  // namespace as
