#pragma once

// "sampler" instrument: plays WAV files (and raw samples out of SoundFonts) through the same
// band-limited playback core as 'sf2', with key/velocity zones, loops (forward / ping-pong / sustain),
// one-shot mode for drums, ADSR, a resonant lowpass, pitch bend, reverse, a per-note start offset,
// sustain pedal and expression - and the zone model of SFZ multisample libraries (agentsound/sfz.py
// imports .sfz files into it): round robin (seqLength/seqPosition), random layers (lorand/hirand),
// release / first / legato triggers, groups turning each other off (group/offBy/offMode), velocity
// curves and crossfades, per-zone envelopes, filters, EQ, vibrato / tremolo and per-note randomness.
// Played, not triggered: live 'dynamics' (CC-style crossfades, gain curves and cutoff moves per zone, velocity
// layers as a crossfaded dynamics stack, a dynamics-linked tilt and level), monophonic legato (library legato zones,
// else scripted transitions entering past the attack, equal-power and level-matched, with portamento), keyswitch
// articulations switched live by notes that never sound (swLast / swDown / swLo..swHi / swDefault), and an
// instrument vibrato that runs on through legato transitions.
//
// 'samples' (structured, see docs/RENDER_FORMAT.md "Assets" for every zone field):
//   {"dir": "samples/909"}                      every *.wav in the folder, mapped by file name:
//                                               GM drum names (kick.wav -> 36, snare, clap, hat, ohh, ...)
//                                               play on their key; note names (C4.wav, F#3.wav, 60.wav)
//                                               spread over the keyboard
//   {"file": "samples/pad.wav", "root": 57}     one zone
//   [{"file": ..., "root", "lo", "hi", "vello", "velhi", "loop", "gain", "tune", "pan", "choke",
//     "seqLength", "lorand", "trigger", "group", "offBy", "attack", "cutoff", ...}, ...]
//   {"file": "soundfonts/GeneralUser-GS.sf2", "sample": "StrLoop - C3"}   a raw SoundFont sample
//   {"file": "*silence"} / "*sine" / "*noise"   built-in generators (a silent zone only turns voices off)
//   "channels": [[ch, gainL, gainR], ...]      mix channels of a multichannel file into stereo (mic mixes)
// Paths are relative to the assets/ folder, or absolute. WAV (and lossless WavPack) files are loaded once per process (in
// parallel) and shared by every zone and track that plays them; 16-bit material is kept as 16-bit.

#include "core/Module.h"

#include <memory>

namespace as {

std::unique_ptr<Instrument> makeSampler();

}  // namespace as
