#pragma once

// Strict, self-describing parameter sets shared by every instrument and effect.
//
// A module declares its parameters once as ParamSpecs. The same list drives
// JSON validation (unknown keys, wrong types and out-of-range values are
// errors, never silently clamped), automation lookup and the generated
// parameter reference (`agentsound params`).

#include <nlohmann/json.hpp>

#include <cstddef>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace as {

using json = nlohmann::json;

struct ParamSpec {
    std::string name;          // dotted lowercase, e.g. "cutoff", "osc1.wave", "kick.decay"
    float min{0.0f};
    float max{1.0f};
    float def{0.0f};
    std::string unit;          // "Hz", "dB", "s", "ms", "st", "ct", "%", "beats", "" ...
    std::string help;          // one line, written for the composing agent
    std::vector<std::string> choices;  // non-empty => enum; value is the choice index
    bool automatable{true};
};

class ConfigError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class Params {
public:
    Params() = default;
    explicit Params(std::vector<ParamSpec> specs);

    // Applies a JSON object of overrides on top of the defaults.
    // Numbers set numeric params, strings select enum choices (by name).
    // Keys listed in `extraKeys` are skipped (the module handles them itself).
    // Throws ConfigError naming `context` on any unknown key, wrong type,
    // non-finite or out-of-range value.
    void configure(const json& object, std::string_view context,
                   const std::vector<std::string>& extraKeys = {});

    // Automation entry point: returns false for unknown or non-automatable names.
    // Values are clamped to the declared range (automation curves may overshoot slightly).
    bool set(std::string_view name, float value);

    int index(std::string_view name) const noexcept;  // -1 if unknown
    float get(int index) const noexcept { return values_[static_cast<std::size_t>(index)]; }
    float get(std::string_view name) const;           // throws std::out_of_range
    int choice(std::string_view name) const { return static_cast<int>(get(name) + 0.5f); }

    const std::vector<ParamSpec>& specs() const noexcept { return specs_; }

    // Monotonic counter bumped on every successful set/configure; lets a module
    // cheaply detect "something changed since last block".
    unsigned version() const noexcept { return version_; }

private:
    std::vector<ParamSpec> specs_;
    std::vector<float> values_;
    unsigned version_{0};
};

// Convenience constructors for spec tables.
ParamSpec num(std::string name, float min, float max, float def, std::string unit, std::string help,
              bool automatable = true);
ParamSpec choice(std::string name, std::vector<std::string> choices, int def, std::string help,
                 bool automatable = false);
ParamSpec toggle(std::string name, bool def, std::string help);

}  // namespace as
