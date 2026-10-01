#include "fx/TimeFx.h"

#include "fx/TimeFxUtil.h"

namespace as {

std::unique_ptr<Effect> createTimeEffect(std::string_view type) {
    using namespace timefx;
    if (type == "chorus") return makeChorus();
    if (type == "flanger") return makeFlanger();
    if (type == "phaser") return makePhaser();
    if (type == "delay") return makeDelay();
    if (type == "reverb") return makeReverb();
    if (type == "gatedreverb") return makeGatedReverb();
    if (type == "tremolo") return makeTremolo();
    if (type == "ensemble") return makeEnsemble();
    if (type == "vowel") return makeVowel();
    if (type == "wah") return makeWah();
    if (type == "amp") return makeAmp();
    return nullptr;
}

std::vector<std::string> timeEffectTypes() {
    return {"chorus", "flanger", "phaser", "delay", "reverb", "gatedreverb", "tremolo", "ensemble", "vowel", "wah", "amp"};
}

bool timeEffectAcceptsSidechain(std::string_view type) { return type == "delay" || type == "gatedreverb"; }

}  // namespace as
