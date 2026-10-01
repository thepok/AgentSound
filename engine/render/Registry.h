#pragma once

// Maps render-JSON type names to module factories.

#include "core/Module.h"

#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace as {

std::unique_ptr<Instrument> createInstrument(std::string_view type);  // throws ConfigError if unknown
std::unique_ptr<Effect> createEffect(std::string_view type);          // throws ConfigError if unknown
bool effectAcceptsSidechain(std::string_view type);
bool effectRequiresSidechain(std::string_view type);  // a "sidechain" is mandatory (vocoder: the modulator)
std::vector<std::string> instrumentTypes();
std::vector<std::string> effectTypes();

}  // namespace as
