#pragma once

// 'convolver': convolution with a recorded impulse response - real rooms, halls, plates, springs and
// guitar cabinets (engine/fx/Convolver.cpp; engine: ConvolverEngine, IR preparation: ConvolverIr).
// Zero latency, deterministic, preview-exact. The IR file is the string param 'ir' (see
// docs/RENDER_FORMAT.md, "convolver"); every other param is a ParamSpec.

#include "core/Module.h"

#include <memory>

namespace as {

std::unique_ptr<Effect> makeConvolver();

}  // namespace as
