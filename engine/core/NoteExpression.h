#pragma once

// Per-note expression: the optional fifth field of a render-JSON note ({"string": 2, ...}), validated at parse time
// against the instrument's note ParamSpecs (Instrument::noteParamSpecs) and dispatched with the note-on
// (Instrument::noteOn(id, pitch, velocity, expression)). Owned, fixed-size data: names are copied at parse time, so
// no JSON, no pointers into a parser and no allocation on dispatch. Missing slots inherit the instrument's controls.
// Salvaged from the physical-guitar branch (cx-physguitar); docs/SAMPLE_REALISM_PLAN.md levers 5 and 6 use it.

#include "core/Params.h"

#include <algorithm>
#include <array>
#include <string_view>
#include <vector>

namespace as {

struct NoteExpression {
    struct Slot {
        std::array<char, 32> name{};
        float value{};
    };
    std::array<Slot, 16> slots{};
    unsigned count{};

    bool has(std::string_view name) const noexcept {
        for (unsigned i = 0; i < count; ++i)
            if (name == slots[i].name.data()) return true;
        return false;
    }
    float get(std::string_view name, float fallback) const noexcept {
        for (unsigned i = 0; i < count; ++i)
            if (name == slots[i].name.data()) return slots[i].value;
        return fallback;
    }
};

// Strict: unknown keys, wrong types and out-of-range values are ConfigErrors (Params::configure); an instrument
// without note specs accepts only an empty object.
inline NoteExpression parseNoteExpression(const json& value, const std::vector<ParamSpec>& specs) {
    if (!value.is_object()) throw ConfigError("note params must be an object of {name: value}");
    if (specs.empty() && !value.empty()) throw ConfigError("this instrument takes no note params");
    Params params(specs);
    params.configure(value, "note params");
    NoteExpression result;
    if (value.size() > result.slots.size()) throw ConfigError("too many note params (maximum 16)");
    for (auto it = value.begin(); it != value.end(); ++it) {
        auto& slot = result.slots[result.count++];
        if (it.key().size() >= slot.name.size()) throw ConfigError("note param name exceeds 31 characters");
        std::copy(it.key().begin(), it.key().end(), slot.name.begin());
        slot.value = params.get(it.key());
    }
    return result;
}

}  // namespace as
