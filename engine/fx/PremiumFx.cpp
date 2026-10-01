#include "fx/PremiumFx.h"

#include "fx/PremiumUtil.h"

namespace as {

std::unique_ptr<Effect> createPremiumEffect(std::string_view type) {
    using namespace premium;
    if (type == "microshift") return makeMicroShift();
    if (type == "shimmer") return makeShimmer();
    if (type == "tape") return makeTape();
    if (type == "exciter") return makeExciter();
    if (type == "dimension") return makeDimension();
    return nullptr;
}

std::vector<std::string> premiumEffectTypes() { return {"microshift", "shimmer", "tape", "exciter", "dimension"}; }

}  // namespace as
