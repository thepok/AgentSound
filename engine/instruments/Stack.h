#pragma once

// "stack" instrument: layered instruments. One track plays 1-8 child instruments of any type (va, dx7, drums, sf2,
// sampler) at once - a piano with a DX bell an octave up and a pad swelling in under it, a velocity-switched
// e-piano -> grand, a string section doubled an octave down - each layer with its own level, pan, transpose,
// fine tuning, key range, velocity range with equal-power crossfades, velocity curve, note delay, mute and an
// optional insert fx chain. Notes go to every layer whose key / velocity range they fall in; the stack-level
// performance params (pitchbend, pedal, expression, dynamics, modwheel) go to every layer that follows them.
//
//   {"type": "stack", "params": {
//      "layers": [
//        {"id": "piano", "instrument": {"type": "sampler", "params": {...}}, "level": 0},
//        {"id": "bell", "instrument": {"type": "dx7", "params": {"voice": "E.PIANO 1"}}, "transpose": 12,
//         "level": -9, "follow.bend": false, "fx": [{"type": "chorus", "params": {"mix": 0.3}}]},
//        {"id": "pad", "instrument": {"type": "va", "params": {...}}, "level": -14, "delay": 40}
//      ],
//      "pedal": 0, "level": 0}}
//
// Params of the layers and of their children are addressed as 'layers.<id>.<param>' (a layer without "id" is
// named by its index: 'layers.0.cutoff'); a layer's fx as 'layers.<id>.fx.<index>.<param>'. The layer's own params
// (level, pan, transpose, ...) shadow the child's params of the same name. docs/RENDER_FORMAT.md "Stack".
//
// Velocity / key crossfades need a per-note gain, which a child instrument cannot apply to one of its voices: a
// layer with a crossfade runs a small pool of extra child instances ('xfvoices'), each with a fixed output gain; a
// note in a fade zone plays on the instance that has its gain (or a free one, which takes it). Everything else
// plays on the layer's main instance, so a stack without crossfades costs exactly its children.

#include "core/Module.h"

#include <cstdint>
#include <memory>

namespace as {

std::unique_ptr<Instrument> makeStack();

// The RNG seed of layer `layer`'s child instrument(s) (and, xor-ed with the fx index, its effects).
std::uint64_t stackLayerSeed(std::uint64_t seed, int layer) noexcept;

inline constexpr int kStackMaxLayers = 8;

}  // namespace as
