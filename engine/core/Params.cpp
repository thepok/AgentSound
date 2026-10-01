#include "core/Params.h"

#include <algorithm>
#include <cmath>
#include <sstream>

namespace as {

Params::Params(std::vector<ParamSpec> specs) : specs_(std::move(specs)) {
    values_.reserve(specs_.size());
    for (const auto& spec : specs_) {
        if (spec.min > spec.max || spec.def < spec.min || spec.def > spec.max) {
            throw std::logic_error("ParamSpec '" + spec.name + "' has an invalid range/default");
        }
        values_.push_back(spec.def);
    }
}

int Params::index(std::string_view name) const noexcept {
    for (std::size_t i = 0; i < specs_.size(); ++i) {
        if (specs_[i].name == name) return static_cast<int>(i);
    }
    return -1;
}

float Params::get(std::string_view name) const {
    const int i = index(name);
    if (i < 0) throw std::out_of_range("unknown parameter '" + std::string(name) + "'");
    return values_[static_cast<std::size_t>(i)];
}

bool Params::set(std::string_view name, float value) {
    const int i = index(name);
    if (i < 0 || !std::isfinite(value)) return false;
    const auto& spec = specs_[static_cast<std::size_t>(i)];
    if (!spec.automatable) return false;
    values_[static_cast<std::size_t>(i)] = std::clamp(value, spec.min, spec.max);
    ++version_;
    return true;
}

void Params::configure(const json& object, std::string_view context,
                       const std::vector<std::string>& extraKeys) {
    const std::string where(context);
    if (object.is_null()) return;
    if (!object.is_object()) throw ConfigError(where + ": params must be a JSON object");

    for (auto it = object.begin(); it != object.end(); ++it) {
        const std::string& key = it.key();
        if (std::find(extraKeys.begin(), extraKeys.end(), key) != extraKeys.end()) continue;
        const int i = index(key);
        if (i < 0) {
            std::ostringstream known;
            for (std::size_t k = 0; k < specs_.size(); ++k) known << (k ? ", " : "") << specs_[k].name;
            throw ConfigError(where + ": unknown parameter '" + key + "' (known: " + known.str() + ")");
        }
        const auto& spec = specs_[static_cast<std::size_t>(i)];
        const json& v = it.value();
        float value = 0.0f;
        if (!spec.choices.empty() && v.is_string()) {
            const auto s = v.get<std::string>();
            const auto found = std::find(spec.choices.begin(), spec.choices.end(), s);
            if (found == spec.choices.end()) {
                std::ostringstream opts;
                for (std::size_t k = 0; k < spec.choices.size(); ++k) opts << (k ? "|" : "") << spec.choices[k];
                throw ConfigError(where + ": '" + key + "' must be one of " + opts.str() + ", got '" + s + "'");
            }
            value = static_cast<float>(found - spec.choices.begin());
        } else if (v.is_boolean()) {
            value = v.get<bool>() ? 1.0f : 0.0f;
        } else if (v.is_number()) {
            const double d = v.get<double>();
            if (!std::isfinite(d)) throw ConfigError(where + ": '" + key + "' is not finite");
            value = static_cast<float>(d);
        } else {
            throw ConfigError(where + ": '" + key + "' has the wrong type");
        }
        if (value < spec.min || value > spec.max) {
            std::ostringstream msg;
            msg << where << ": '" << key << "' = " << value << " is outside " << spec.min << ".." << spec.max;
            throw ConfigError(msg.str());
        }
        values_[static_cast<std::size_t>(i)] = value;
    }
    ++version_;
}

ParamSpec num(std::string name, float min, float max, float def, std::string unit, std::string help,
              bool automatable) {
    ParamSpec s;
    s.name = std::move(name);
    s.min = min;
    s.max = max;
    s.def = def;
    s.unit = std::move(unit);
    s.help = std::move(help);
    s.automatable = automatable;
    return s;
}

ParamSpec choice(std::string name, std::vector<std::string> choices, int def, std::string help,
                 bool automatable) {
    ParamSpec s;
    s.name = std::move(name);
    s.min = 0.0f;
    s.max = static_cast<float>(choices.size() - 1);
    s.def = static_cast<float>(def);
    s.help = std::move(help);
    s.choices = std::move(choices);
    s.automatable = automatable;
    return s;
}

ParamSpec toggle(std::string name, bool def, std::string help) {
    ParamSpec s;
    s.name = std::move(name);
    s.min = 0.0f;
    s.max = 1.0f;
    s.def = def ? 1.0f : 0.0f;
    s.help = std::move(help);
    s.choices = {"off", "on"};
    s.automatable = true;
    return s;
}

}  // namespace as
