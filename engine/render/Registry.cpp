#include "render/Registry.h"

#include "fx/Convolver.h"
#include "fx/DynamicsFx.h"
#include "fx/PremiumFx.h"
#include "fx/TimeFx.h"
#include "fx/Vocoder.h"
#include "instruments/DrumSynth.h"
#include "instruments/Dx7Synth.h"
#include "instruments/Sampler.h"
#include "instruments/Sf2Synth.h"
#include "instruments/Stack.h"
#include "instruments/VaSynth.h"

#include <sstream>

namespace as {
namespace {

std::string joined(const std::vector<std::string>& items) {
    std::ostringstream out;
    for (std::size_t i = 0; i < items.size(); ++i) out << (i ? ", " : "") << items[i];
    return out.str();
}

}  // namespace

std::vector<std::string> instrumentTypes() { return {"va", "dx7", "drums", "sf2", "sampler", "stack"}; }

std::vector<std::string> effectTypes() {
    auto types = dynamicsEffectTypes();
    for (auto& t : timeEffectTypes()) types.push_back(t);
    for (auto& t : premiumEffectTypes()) types.push_back(t);
    types.push_back("vocoder");
    types.push_back("convolver");
    return types;
}

std::unique_ptr<Instrument> createInstrument(std::string_view type) {
    if (type == "va") return makeVaSynth();
    if (type == "dx7") return makeDx7Synth();
    if (type == "drums") return makeDrumSynth();
    if (type == "sf2") return makeSf2Synth();
    if (type == "sampler") return makeSampler();
    if (type == "stack") return makeStack();
    throw ConfigError("unknown instrument type '" + std::string(type) + "' (known: " + joined(instrumentTypes()) + ")");
}

std::unique_ptr<Effect> createEffect(std::string_view type) {
    if (auto fx = createDynamicsEffect(type)) return fx;
    if (auto fx = createTimeEffect(type)) return fx;
    if (auto fx = createPremiumEffect(type)) return fx;
    if (type == "vocoder") return makeVocoder();
    if (type == "convolver") return makeConvolver();
    throw ConfigError("unknown effect type '" + std::string(type) + "' (known: " + joined(effectTypes()) + ")");
}

bool effectAcceptsSidechain(std::string_view type) {
    return dynamicsEffectAcceptsSidechain(type) || timeEffectAcceptsSidechain(type) || effectRequiresSidechain(type);
}

// The vocoder's sidechain is its modulator (the voice): without one it has nothing to say.
bool effectRequiresSidechain(std::string_view type) { return type == "vocoder"; }

}  // namespace as
