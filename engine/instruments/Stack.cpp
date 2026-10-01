#include "instruments/Stack.h"

#include "dsp/Dsp.h"
#include "render/Registry.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

namespace as {

std::uint64_t stackLayerSeed(std::uint64_t seed, int layer) noexcept {
    std::uint64_t h = seed ^ (0xA0761D6478BD642Full * static_cast<std::uint64_t>(layer + 1));
    h ^= h >> 31;
    h *= 0xE7037ED1A0B428DBull;
    h ^= h >> 29;
    return h ? h : 0x9E3779B97F4A7C15ull;
}

namespace {

constexpr int kMaxNotes = 2048;   // notes the stack tracks at once (sounding or pedal-held)
constexpr int kMaxQueue = 4096;   // delayed note events pending
constexpr int kMaxHeld = 1024;    // note-offs a layer holds for the emulated sustain pedal
constexpr float kXfStepDb = 1.0f;     // crossfade gains are rounded to this grid, so notes of similar velocity share a voice
constexpr double kGainTau = 0.0015;  // two-pole smoothing of the layer gains / pans / mute (~5 ms 10-90 %)

// Performance params the stack forwards to the layers that follow them.
enum Fwd { kBend, kPedal, kExpr, kDyn, kWheel, kFwdCount };
constexpr std::array<const char*, kFwdCount> kFwdNames = {"pitchbend", "pedal", "expression", "dynamics", "modwheel"};
constexpr std::array<const char*, kFwdCount> kFollowNames = {"follow.bend", "follow.pedal", "follow.expression",
                                                             "follow.dynamics", "follow.modwheel"};

// Two cascaded one-poles: C1-continuous glides, so gain / pan / mute jumps never click.
class Smooth2 {
public:
    void prepare(double sampleRate, double tau, float value) noexcept {
        c_ = static_cast<float>(std::exp(-1.0 / (tau * sampleRate)));
        snap(value);
    }
    void snap(float v) noexcept { a_ = b_ = t_ = v; moving_ = false; }
    void setTarget(float t) noexcept {
        t_ = t;
        moving_ = a_ != t_ || b_ != t_;
    }
    float next() noexcept {
        if (moving_) {
            a_ = t_ + (a_ - t_) * c_;
            b_ = a_ + (b_ - a_) * c_;
            if (std::fabs(a_ - t_) + std::fabs(b_ - t_) <= 1e-7f * (1.0f + std::fabs(t_))) {
                a_ = b_ = t_;
                moving_ = false;
            }
        }
        return b_;
    }
    bool moving() const noexcept { return moving_; }
    float value() const noexcept { return b_; }

private:
    float c_{0.0f}, a_{0.0f}, b_{0.0f}, t_{0.0f};
    bool moving_{false};
};

std::vector<ParamSpec> stackSpecs() {
    return {
        num("level", -60, 24, 0, "dB", "Output level of the whole stack (after the layers are summed)."),
        num("pitchbend", -24, 24, 0, "st",
            "Pitch bend in (fractional) semitones for every layer that follows it ('follow.bend', default on), on top of "
            "each layer's 'fine'. Turn it off on layers that must not bend (a bell or a sub under a bending lead)."),
        num("pedal", 0, 1, 0, "",
            "Sustain pedal (>= 0.5 = down) for every layer that follows it: sampler / sf2 layers get their own pedal "
            "(release samples at pedal-up); va / dx7 / drums layers are held by the stack (their note-offs wait for "
            "pedal-up). A step: automate it with 'step' points at chord changes."),
        num("expression", 0, 1, 1, "",
            "Expression (CC11) for every layer that follows it: gain x expression^2 (0.5 = -12 dB), smoothed; sampler / "
            "sf2 layers use their own, the stack applies it to the others. Phrase swells over the whole stack."),
        num("dynamics", 0, 1, 1, "",
            "Played dynamics (0 = ppp .. 1 = fff) for the sampler layers that follow it: their live crossfades, "
            "'dyntone' and 'dynrange'. Only when a layer is a sampler."),
        num("modwheel", 0, 1, 0, "", "DX7 mod wheel (the patch LFO vibrato) for the dx7 layers that follow it."),
    };
}

std::vector<ParamSpec> layerSpecs() {
    std::vector<ParamSpec> s = {
        num("level", -60, 24, 0, "dB",
            "Layer level in dB (smoothed; automatable: fade a pad layer in under a lead). Shadows the child's own "
            "'level', which stays as configured in its params."),
        num("pan", -1, 1, 0, "",
            "Layer position -1 (left) .. 1 (right), balance law like a track pan (unity at centre): an octave layer "
            "a little off-centre widens a lead."),
        toggle("mute", false, "Silences the layer (smoothed; it keeps playing its notes, so unmuting mid-note works)."),
        num("transpose", -48, 48, 0, "st",
            "Whole semitones added to every note of the layer (12 = an octave up, -12 = an octave-down double). Notes "
            "moved outside 0..127 are not played on it.", false),
        num("fine", -100, 100, 0, "ct",
            "Fine tuning in cents (through the child's pitch bend): 3-8 ct against another layer of the same "
            "instrument = a chorused double; 0 keeps the layers phase-locked. Only for va, dx7, sf2 and sampler layers."),
        num("keylo", 0, 127, 0, "", "Lowest key (the note before 'transpose') the layer plays.", false),
        num("keyhi", 0, 127, 127, "", "Highest key (before 'transpose') the layer plays.", false),
        num("keyfade", 0, 127, 0, "st",
            "Key crossfade width in semitones inside the key range: the layer fades in (equal power) over keylo.."
            "keylo+keyfade when keylo > 0 and out over keyhi-keyfade..keyhi when keyhi < 127. Give the neighbouring "
            "layer the mirrored range for a seamless split (bass: keyhi 54, piano: keylo 48, both keyfade 6).", false),
        num("vello", 0, 127, 0, "", "Lowest note velocity (1..127) the layer plays.", false),
        num("velhi", 0, 127, 127, "", "Highest note velocity the layer plays.", false),
        num("velfade", 0, 127, 0, "",
            "Velocity crossfade width inside the velocity range: the layer fades in (equal power) over vello.."
            "vello+velfade when vello > 0 and out over velhi-velfade..velhi when velhi < 127. Soft e-piano velhi 90 + "
            "grand vello 60, both velfade 30: an equal-power crossfade from 60 to 90. Notes in a fade play on the "
            "layer's crossfade voices ('xfvoices').", false),
        num("velcurve", 0.2f, 5, 1, "",
            "Velocity curve of the notes the child receives: velocity^velcurve (> 1 = softer until played hard, < 1 = "
            "brighter sooner). The crossfades use the played velocity.", false),
        num("velscale", 0, 4, 1, "",
            "Scales the velocity the child receives after the curve (0.6 = a gentler layer, 1.2 = harder; capped at "
            "127). Timbre, not level: use 'level' for balance.", false),
        num("delay", 0, 2000, 0, "ms",
            "Every note of the layer starts (and ends) this much later, and its sustain pedal moves with them: 10-30 ms "
            "= a soft double / flam behind the attack, 40-120 ms = a pad that swells in under the lead's attack.", false),
        num("xfvoices", 1, 16, 4, "",
            "Extra child instances for notes inside a key / velocity crossfade (each plays at one crossfade gain, "
            "rounded to 1 dB steps so nearby velocities share one; a free one takes a new gain). Only used by layers "
            "with a crossfade; 4 covers most playing, raise it for dense pedalled chords in the fade zone.", false),
    };
    const char* const followHelp[kFwdCount] = {
        "The layer follows the stack's 'pitchbend' (off: a bell or sub that must not bend; its own is then "
        "'layers.<id>.pitchbend').",
        "The layer follows the stack's sustain 'pedal' (off: a pad that must stop at key-up).",
        "The layer follows the stack's 'expression'.",
        "The layer follows the stack's 'dynamics' (sampler layers).",
        "The layer follows the stack's 'modwheel' (dx7 layers).",
    };
    for (int f = 0; f < kFwdCount; ++f) {
        ParamSpec t = toggle(kFollowNames[static_cast<std::size_t>(f)], true, followHelp[f]);
        t.automatable = false;
        s.push_back(std::move(t));
    }
    return s;
}

// The reference listing of an unconfigured stack (`agentsound params stack`): the stack's own params and the
// per-layer ones under their address.
std::vector<ParamSpec> docSpecs() {
    std::vector<ParamSpec> out = stackSpecs();
    for (ParamSpec s : layerSpecs()) {
        s.name = "layers.<id>." + s.name;
        out.push_back(std::move(s));
    }
    out.push_back(num("layers.<id>.<param>", 0, 0, 0, "",
                      "Any param of the layer's instrument (e.g. layers.pad.cutoff, layers.bell.modwheel when the layer "
                      "does not follow the stack's); the layer's own params above shadow the child's of the same name."));
    out.push_back(num("layers.<id>.fx.<index>.<param>", 0, 0, 0, "", "A param of the layer's insert fx entry <index>."));
    return out;
}

bool digitsOnly(std::string_view s) {
    return !s.empty() && std::all_of(s.begin(), s.end(), [](char c) { return c >= '0' && c <= '9'; });
}

bool validId(std::string_view s) {
    return !s.empty() && s.size() <= 64 &&
           std::all_of(s.begin(), s.end(), [](char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_'; });
}

const ParamSpec* findSpec(const std::vector<ParamSpec>& specs, std::string_view name) {
    for (const auto& s : specs) if (s.name == name) return &s;
    return nullptr;
}

float edge(double x) {
    if (x >= 1.0) return 1.0f;
    if (x <= 0.0) return 0.0f;
    return static_cast<float>(std::sin(x * dsp::kPi * 0.5));
}

std::string fmtNum(double v) {
    std::string s = std::to_string(v);
    while (!s.empty() && s.back() == '0') s.pop_back();
    if (!s.empty() && s.back() == '.') s.pop_back();
    return s;
}

class Stack final : public Instrument {
public:
    Stack() : params_(stackSpecs()), docs_(docSpecs()) {}

    void configure(const json& given) override {
        const std::string where = "stack";
        if (!given.is_object()) throw ConfigError(where + ": params must be a JSON object");
        const json params = applyFlat(given);
        params_.configure(params, where, {"layers"});
        if (!params.contains("layers")) {
            throw ConfigError(where + ": needs \"layers\": [{\"instrument\": {\"type\": ..., \"params\": {...}}, ...}, ...] "
                                      "(1.." + std::to_string(kStackMaxLayers) + " layers)");
        }
        const json& ls = params.at("layers");
        if (!ls.is_array() || ls.empty() || ls.size() > static_cast<std::size_t>(kStackMaxLayers)) {
            throw ConfigError(where + ": 'layers' must be a list of 1.." + std::to_string(kStackMaxLayers) + " layer objects");
        }
        layers_.clear();
        layers_.reserve(ls.size());
        for (std::size_t i = 0; i < ls.size(); ++i) {
            layers_.emplace_back();
            configureLayer(layers_.back(), ls[i], static_cast<int>(i), params);
        }
        // stack-level performance params only make sense when some layer takes them
        for (int f = 0; f < kFwdCount; ++f) {
            if (f == kPedal || f == kExpr || !params.contains(kFwdNames[static_cast<std::size_t>(f)])) continue;
            if (!anyFollows(f)) {
                throw ConfigError(where + ": '" + kFwdNames[static_cast<std::size_t>(f)] + "' is set, but no layer follows it (" +
                                  (f == kBend ? "no layer instrument has a pitch bend, or every layer has follow.bend off"
                                   : f == kDyn ? "'dynamics' is a sampler param: no sampler layer follows it"
                                               : "'modwheel' is a dx7 param: no dx7 layer follows it") + ")");
            }
        }
        pedalDown_ = params_.get("pedal") >= 0.5f;
        buildSpecs();
        configured_ = true;
    }

    void setTempoMap(const TempoMap& map) override {
        for (auto& L : layers_) {
            for (auto& in : L.inst) in->setTempoMap(map);
            for (auto& f : L.fx) f->setTempoMap(map);
        }
    }

    void prepare(const RenderContext& ctx) override {
        if (!configured_) throw ConfigError("stack: configure() before prepare()");
        sr_ = ctx.sampleRate;
        const int maxBlock = std::max(1, ctx.maxBlock);
        for (std::size_t i = 0; i < layers_.size(); ++i) {
            Layer& L = layers_[i];
            RenderContext c = ctx;
            c.seed = stackLayerSeed(ctx.seed, static_cast<int>(i));
            for (std::size_t k = 0; k < L.inst.size(); ++k) {
                try {
                    L.inst[k]->prepare(c);
                } catch (const ConfigError& e) {
                    throw ConfigError(L.path + ".instrument: " + e.what());
                }
            }
            L.tailSamples = 0;
            for (std::size_t j = 0; j < L.fx.size(); ++j) {
                RenderContext cf = c;
                cf.seed = c.seed ^ (0xD1B54A32D192ED03ull * static_cast<std::uint64_t>(j + 1));
                try {
                    L.fx[j]->prepare(cf);
                } catch (const ConfigError& e) {
                    throw ConfigError(L.path + ".fx[" + std::to_string(j) + "]: " + e.what());
                }
                if (L.fx[j]->latencySamples() > 0) {
                    throw ConfigError(L.path + ".fx[" + std::to_string(j) + "]: effect '" + L.fxTypes[j] +
                                      "' adds latency and is only allowed on the master chain");
                }
                L.tailSamples = std::max(L.tailSamples, static_cast<std::int64_t>(std::ceil(L.fx[j]->tailSeconds() * sr_)) +
                                                            (L.fx[j]->tailSeconds() > 0.0 ? maxBlock : 0));
            }
            L.quiet = L.tailSamples;
            L.delay = static_cast<std::int64_t>(std::llround(L.params.get("delay") * sr_ / 1000.0));
            L.bufL.assign(static_cast<std::size_t>(maxBlock), 0.0f);
            L.bufR.assign(static_cast<std::size_t>(maxBlock), 0.0f);
            L.held.clear();
            L.held.reserve(kMaxHeld);
            L.pedalDown = pedalDown_;
            L.pedalSent = -1;
            L.gainL.prepare(sr_, kGainTau, 0.0f);
            L.gainR.prepare(sr_, kGainTau, 0.0f);
            float gl, gr;
            layerGains(L, gl, gr);
            L.gainL.snap(gl);
            L.gainR.snap(gr);
            std::fill(L.instNotes.begin(), L.instNotes.end(), 0);
        }
        tmpL_.assign(static_cast<std::size_t>(maxBlock), 0.0f);
        tmpR_.assign(static_cast<std::size_t>(maxBlock), 0.0f);
        queue_.clear();
        queue_.reserve(kMaxQueue);
        qHead_ = 0;
        notes_.clear();
        notes_.reserve(kMaxNotes);
        level_.prepare(sr_, kGainTau, dsp::dbToGain(params_.get("level")));
        now_ = 0;
    }

    bool setParam(std::string_view name, float value) override {
        if (!std::isfinite(value)) return false;
        if (name.substr(0, 7) == "layers.") {
            const std::string_view rest = name.substr(7);
            const auto dot = rest.find('.');
            if (dot == std::string_view::npos) return false;
            Layer* L = findLayer(rest.substr(0, dot));
            return L && setLayerParam(*L, rest.substr(dot + 1), value);
        }
        if (findSpec(specs_, name) == nullptr || !params_.set(name, value)) return false;
        const float v = params_.get(name);
        if (name == "level") {
            level_.setTarget(dsp::dbToGain(v));
            return true;
        }
        int f = 0;
        while (f < kFwdCount && name != kFwdNames[static_cast<std::size_t>(f)]) ++f;
        if (f == kFwdCount) return false;
        if (f == kPedal) pedalDown_ = v >= 0.5f;
        for (std::size_t i = 0; i < layers_.size(); ++i) {
            Layer& L = layers_[i];
            if (!L.follow[f]) continue;
            if (f == kBend) {
                if (L.has[kBend]) sendBend(L);
            } else if (f == kPedal) {
                // (only up / down steps: a ramped pedal lane must not flood the event queue of a delayed layer)
                const std::int8_t down = v >= 0.5f ? 1 : 0;
                if (down == L.pedalSent) continue;
                L.pedalSent = down;
                // a delayed layer's notes and note-offs arrive 'delay' late, so its pedal does too: else a pedal-up
                // at a chord change would come before the old chord's (delayed) note-offs and the re-pressed pedal
                // would hold them into the next chord. (At the render's first sample nothing has reached the layer
                // yet: its start value applies at once, so a preview starts with the pedal a full render has there.)
                if (L.delay > 0 && now_ > 0) enqueue({now_ + L.delay, 0, 0, static_cast<std::int8_t>(i), 0, Kind::Pedal, v});
                else applyPedal(L, v);
            } else if (L.has[f]) {
                for (auto& in : L.inst) in->setParam(kFwdNames[static_cast<std::size_t>(f)], v);
            } else if (f == kExpr) {
                updateGains(L);
            }
        }
        return true;
    }

    void noteOn(int noteId, int pitch, float velocity) override {
        if (notes_.size() >= static_cast<std::size_t>(kMaxNotes)) return;  // (no room to track it: not played)
        const int vel = std::clamp(static_cast<int>(std::lround(velocity * 127.0f)), 0, 127);
        const int key = std::clamp(pitch, 0, 127);
        NoteRec rec;
        rec.id = noteId;
        bool any = false;
        for (std::size_t i = 0; i < layers_.size(); ++i) {
            Layer& L = layers_[i];
            const float g = gainAt(L, key, vel);
            if (g <= 1e-4f) continue;
            const int p = pitch + L.transpose;
            if (p < 0 || p > 127) continue;
            float v = velocity;
            if (L.velcurve != 1.0f || L.velscale != 1.0f) {
                v = std::pow(std::max(velocity, 0.0f), L.velcurve) * L.velscale;
                v = std::clamp(v, 1.0f / 127.0f, 1.0f);
            }
            const int k = poolVoice(L, g);
            if (k < 0) continue;
            any = true;
            rec.inst[i] = static_cast<std::int8_t>(k);
            ++L.instNotes[static_cast<std::size_t>(k)];
            if (L.delay > 0) enqueue({now_ + L.delay, noteId, static_cast<std::int16_t>(p), static_cast<std::int8_t>(i),
                                      static_cast<std::int8_t>(k), Kind::On, v});
            else L.inst[static_cast<std::size_t>(k)]->noteOn(noteId, p, v);
        }
        if (any) notes_.push_back(rec);
    }

    void noteOff(int noteId) override {
        for (std::size_t n = 0; n < notes_.size(); ++n) {
            if (notes_[n].id != noteId) continue;
            const NoteRec rec = notes_[n];
            notes_[n] = notes_.back();
            notes_.pop_back();
            for (std::size_t i = 0; i < layers_.size(); ++i) {
                const int k = rec.inst[i];
                if (k < 0) continue;
                Layer& L = layers_[i];
                if (L.delay > 0) enqueue({now_ + L.delay, noteId, 0, static_cast<std::int8_t>(i), static_cast<std::int8_t>(k), Kind::Off, 0.0f});
                else offNow(L, k, noteId);
            }
            return;
        }
    }

    void process(float* left, float* right, int frames) override {
        if (frames <= 0) return;
        int pos = 0;
        while (pos < frames) {
            dispatchDue(now_ + pos);
            int end = frames;
            if (qHead_ < queue_.size()) end = static_cast<int>(std::min<std::int64_t>(frames, queue_[qHead_].at - now_));
            end = std::max(end, pos + 1);
            renderSegment(left + pos, right + pos, end - pos);
            pos = end;
        }
        now_ += frames;
        for (auto& L : layers_) {
            bool still = true;
            for (const auto& in : L.inst) if (!in->idle()) { still = false; break; }
            L.quiet = still ? std::min<std::int64_t>(L.quiet + frames, INT64_C(1) << 60) : 0;
        }
    }

    bool idle() const override {
        if (qHead_ < queue_.size()) return false;
        for (const auto& L : layers_) {
            if (L.quiet < L.tailSamples) return false;
            for (const auto& in : L.inst) if (!in->idle()) return false;
        }
        return true;
    }

    const std::vector<ParamSpec>& paramSpecs() const override { return configured_ ? specs_ : docs_; }

private:
    struct Layer {
        std::string id, type, path;
        Params params{layerSpecs()};
        std::vector<std::unique_ptr<Instrument>> inst;   // [0] main, [1..] crossfade voices
        std::vector<float> instGain;                      // output gain per instance (main: 1)
        std::vector<int> instNotes;                       // notes allocated to the instance and not yet released
        std::vector<std::unique_ptr<Effect>> fx;
        std::vector<std::string> fxTypes;
        std::vector<ParamSpec> childSpecs;
        int transpose{0}, keylo{0}, keyhi{127}, keyfade{0}, vello{0}, velhi{127}, velfade{0};
        float velcurve{1.0f}, velscale{1.0f};
        std::int64_t delay{0};
        bool follow[kFwdCount]{true, true, true, true, true};
        bool has[kFwdCount]{};
        float bend0{0.0f};    // the child's own configured pitch bend
        float ownBend{0.0f};  // the child's pitch bend when the layer does not follow the stack's
        std::vector<std::pair<int, int>> held;  // (instance, note id) held by the emulated pedal
        bool pedalDown{false};  // the pedal as this layer sees it (a delayed layer gets pedal moves 'delay' later)
        std::int8_t pedalSent{-1};  // up / down last forwarded (-1: nothing yet): only pedal steps are forwarded
        Smooth2 gainL, gainR;
        std::int64_t tailSamples{0}, quiet{0};
        std::vector<float> bufL, bufR;
    };

    struct NoteRec {
        int id{0};
        std::int8_t inst[kStackMaxLayers]{-1, -1, -1, -1, -1, -1, -1, -1};
    };

    enum class Kind : std::int8_t { On, Off, Pedal };

    struct Event {
        std::int64_t at;
        int id;
        std::int16_t pitch;
        std::int8_t layer, inst;
        Kind kind;
        float vel;  // note-on: the child's velocity; pedal: the pedal value
    };

    // ------------------------------------------------------------------------------------ configure

    // Flat overrides 'layers.<id>.<param>' (and 'layers.<id>.fx.<index>.<param>') next to "layers" are written into
    // the layer they name: a layer param, else the child's param (the same addresses as automation).
    static json applyFlat(const json& given) {
        std::vector<std::string> flat;
        for (auto it = given.begin(); it != given.end(); ++it) {
            if (it.key().rfind("layers.", 0) == 0) flat.push_back(it.key());
        }
        if (flat.empty()) return given;
        json out = given;
        if (!out.contains("layers") || !out.at("layers").is_array()) {
            throw ConfigError("stack: '" + flat.front() + "' needs a \"layers\" list to apply to");
        }
        json& ls = out["layers"];
        const Params layerNames(layerSpecs());
        for (const std::string& key : flat) {
            const std::string rest = key.substr(7);
            const auto dot = rest.find('.');
            if (dot == std::string::npos || dot + 1 >= rest.size()) {
                throw ConfigError("stack: '" + key + "' must be layers.<id>.<param>");
            }
            const std::string id = rest.substr(0, dot), param = rest.substr(dot + 1);
            std::size_t idx = ls.size();
            for (std::size_t i = 0; i < ls.size(); ++i) {
                if (!ls[i].is_object()) continue;
                const bool named = ls[i].contains("id") && ls[i].at("id").is_string();
                if ((named && ls[i].at("id").get<std::string>() == id) || (!named && std::to_string(i) == id)) idx = i;
            }
            if (idx == ls.size()) throw ConfigError("stack: '" + key + "': there is no layer '" + id + "'");
            json& L = ls[idx];
            const json& v = given.at(key);
            if (param.rfind("fx.", 0) == 0) {
                const auto d2 = param.find('.', 3);
                const std::string digits = d2 == std::string::npos ? "" : param.substr(3, d2 - 3);
                if (!digitsOnly(digits) || digits.size() > 3 || d2 + 1 >= param.size()) {
                    throw ConfigError("stack: '" + key + "' must be layers.<id>.fx.<index>.<param>");
                }
                const std::size_t j = static_cast<std::size_t>(std::stoi(digits));
                if (!L.contains("fx") || !L.at("fx").is_array() || j >= L.at("fx").size() || !L["fx"][j].is_object()) {
                    throw ConfigError("stack: '" + key + "': layer '" + id + "' has no fx " + digits);
                }
                if (!L["fx"][j].contains("params")) L["fx"][j]["params"] = json::object();
                L["fx"][j]["params"][param.substr(d2 + 1)] = v;
            } else if (layerNames.index(param) >= 0) {
                L[param] = v;
            } else {
                if (!L.contains("instrument") || !L.at("instrument").is_object()) {
                    throw ConfigError("stack: '" + key + "': layer '" + id + "' has no instrument");
                }
                if (!L["instrument"].contains("params")) L["instrument"]["params"] = json::object();
                L["instrument"]["params"][param] = v;
            }
            out.erase(key);
        }
        return out;
    }

    void configureLayer(Layer& L, const json& j, int index, const json& stackParams) {
        L.path = "layers[" + std::to_string(index) + "]";
        if (!j.is_object()) throw ConfigError(L.path + ": must be an object {\"instrument\": {...}, \"level\": ..., ...}");
        L.params.configure(j, L.path, {"id", "instrument", "fx"});
        L.id = std::to_string(index);
        if (j.contains("id")) {
            if (!j.at("id").is_string() || !validId(j.at("id").get<std::string>())) {
                throw ConfigError(L.path + ".id: must be a name of a-z 0-9 _");
            }
            L.id = j.at("id").get<std::string>();
            if (digitsOnly(L.id) && L.id != std::to_string(index)) {
                throw ConfigError(L.path + ".id: '" + L.id + "' is a number that is not this layer's index; use a name");
            }
        }
        for (const auto& other : layers_) {
            if (&other != &L && other.id == L.id) throw ConfigError(L.path + ".id: '" + L.id + "' is used by another layer");
        }
        if (!j.contains("instrument") || !j.at("instrument").is_object() || !j.at("instrument").contains("type") ||
            !j.at("instrument").at("type").is_string()) {
            throw ConfigError(L.path + ": needs \"instrument\": {\"type\": ..., \"params\": {...}}");
        }
        const json& ij = j.at("instrument");
        for (auto it = ij.begin(); it != ij.end(); ++it) {
            if (it.key() != "type" && it.key() != "params") throw ConfigError(L.path + ".instrument: unknown key '" + it.key() + "'");
        }
        L.type = ij.at("type").get<std::string>();
        if (L.type == "stack") throw ConfigError(L.path + ".instrument: a stack can't contain a stack (flatten the layers)");
        json child = ij.contains("params") ? ij.at("params") : json::object();
        if (!child.is_object()) throw ConfigError(L.path + ".instrument.params: must be an object");

        auto whole = [&](const char* name) {
            const float v = L.params.get(name);
            if (v != std::round(v)) throw ConfigError(L.path + ": '" + name + "' must be a whole number");
            return static_cast<int>(v);
        };
        L.transpose = whole("transpose");
        L.keylo = whole("keylo");
        L.keyhi = whole("keyhi");
        L.keyfade = whole("keyfade");
        L.vello = whole("vello");
        L.velhi = whole("velhi");
        L.velfade = whole("velfade");
        const int voices = whole("xfvoices");
        if (L.keylo > L.keyhi) throw ConfigError(L.path + ": keylo " + std::to_string(L.keylo) + " is above keyhi " + std::to_string(L.keyhi));
        if (L.vello > L.velhi) throw ConfigError(L.path + ": vello " + std::to_string(L.vello) + " is above velhi " + std::to_string(L.velhi));
        L.velcurve = L.params.get("velcurve");
        L.velscale = L.params.get("velscale");
        for (int f = 0; f < kFwdCount; ++f) L.follow[f] = L.params.get(kFollowNames[static_cast<std::size_t>(f)]) >= 0.5f;

        // the child (a probe instance tells which performance params it has)
        std::unique_ptr<Instrument> probe;
        try {
            probe = createInstrument(L.type);
        } catch (const ConfigError& e) {
            throw ConfigError(L.path + ".instrument: " + e.what());
        }
        {
            const auto& specs = probe->paramSpecs();
            for (int f = 0; f < kFwdCount; ++f) {
                const ParamSpec* s = findSpec(specs, kFwdNames[static_cast<std::size_t>(f)]);
                L.has[f] = s && s->automatable;
            }
        }
        const float fine = L.params.get("fine");
        if (fine != 0.0f && !L.has[kBend]) {
            throw ConfigError(L.path + ": 'fine' needs an instrument with a pitch bend (va, dx7, sf2, sampler), not '" + L.type + "'");
        }
        L.bend0 = 0.0f;
        if (child.contains("pitchbend") && child.at("pitchbend").is_number()) L.bend0 = child.at("pitchbend").get<float>();
        L.ownBend = L.bend0;
        // stack-level performance values given in the JSON start the children there (no glide at the start)
        for (int f = 0; f < kFwdCount; ++f) {
            const char* n = kFwdNames[static_cast<std::size_t>(f)];
            if (f == kBend || !L.follow[f] || !L.has[f] || !stackParams.contains(n)) continue;
            child[n] = params_.get(n);
        }
        if (L.has[kBend] && (fine != 0.0f || (L.follow[kBend] && params_.get("pitchbend") != 0.0f))) {
            const float b = childBend(L);
            if (b < -24.0f || b > 24.0f) {
                throw ConfigError(L.path + ": pitch bend + fine = " + fmtNum(b) + " st is outside -24..24");
            }
            child["pitchbend"] = b;
        }
        L.inst.clear();
        L.inst.push_back(std::move(probe));
        try {
            L.inst[0]->configure(child);
        } catch (const ConfigError& e) {
            throw ConfigError(L.path + ".instrument: " + e.what());
        }
        L.childSpecs = L.inst[0]->paramSpecs();
        // crossfade voices: only when some note gets a gain strictly between 0 and 1
        bool fades = false;
        for (int key = 0; key < 128 && !fades; ++key) {
            for (int vel = 1; vel < 128; ++vel) {
                const float g = gainAt(L, key, vel);
                if (g > 1e-4f && g < 0.9999f) { fades = true; break; }
            }
        }
        if (fades) {
            for (int k = 0; k < voices; ++k) {
                auto in = createInstrument(L.type);
                in->configure(child);
                L.inst.push_back(std::move(in));
            }
        }
        L.instGain.assign(L.inst.size(), 1.0f);
        for (std::size_t k = 1; k < L.instGain.size(); ++k) L.instGain[k] = 0.0f;
        L.instNotes.assign(L.inst.size(), 0);

        // fx chain
        L.fx.clear();
        L.fxTypes.clear();
        if (j.contains("fx")) {
            const json& fj = j.at("fx");
            if (!fj.is_array()) throw ConfigError(L.path + ".fx: must be a list of {\"type\": ..., \"params\": {...}}");
            for (std::size_t f = 0; f < fj.size(); ++f) {
                const std::string fp = L.path + ".fx[" + std::to_string(f) + "]";
                const json& e = fj[f];
                if (!e.is_object() || !e.contains("type") || !e.at("type").is_string()) {
                    throw ConfigError(fp + ": must be {\"type\": ..., \"params\": {...}}");
                }
                for (auto it = e.begin(); it != e.end(); ++it) {
                    if (it.key() == "sidechain") {
                        throw ConfigError(fp + ": a layer effect has no sidechain input (put a keyed effect on the track's fx chain)");
                    }
                    if (it.key() != "type" && it.key() != "params") throw ConfigError(fp + ": unknown key '" + it.key() + "'");
                }
                const std::string type = e.at("type").get<std::string>();
                if (effectRequiresSidechain(type)) {
                    throw ConfigError(fp + ": '" + type + "' needs a sidechain, which a layer effect does not have (use it on the track)");
                }
                try {
                    auto fx = createEffect(type);
                    fx->configure(e.contains("params") ? e.at("params") : json::object());
                    L.fx.push_back(std::move(fx));
                } catch (const ConfigError& err) {
                    throw ConfigError(fp + ": " + err.what());
                }
                L.fxTypes.push_back(type);
            }
        }
    }

    bool anyFollows(int f) const {
        for (const auto& L : layers_) if (L.follow[f] && L.has[f]) return true;
        return false;
    }

    void buildSpecs() {
        specs_.clear();
        for (const auto& s : params_.specs()) {
            int f = 0;
            while (f < kFwdCount && s.name != kFwdNames[static_cast<std::size_t>(f)]) ++f;
            // pedal and expression reach every layer (emulated where the child has none)
            if (f < kFwdCount && f != kPedal && f != kExpr && !anyFollows(f)) continue;
            specs_.push_back(s);
        }
        for (const auto& L : layers_) {
            const std::string pre = "layers." + L.id + ".";
            for (ParamSpec s : L.params.specs()) {
                if (s.name == "fine" && !L.has[kBend]) continue;
                s.name = pre + s.name;
                specs_.push_back(std::move(s));
            }
            for (std::size_t j = 0; j < L.fx.size(); ++j) {
                for (ParamSpec s : L.fx[j]->paramSpecs()) {
                    s.name = pre + "fx." + std::to_string(j) + "." + s.name;
                    specs_.push_back(std::move(s));
                }
            }
            for (ParamSpec s : L.childSpecs) {
                if (L.params.index(s.name) >= 0) continue;  // shadowed by the layer's own
                if (followed(L, s.name)) continue;          // driven by the stack's
                s.name = pre + s.name;
                specs_.push_back(std::move(s));
            }
        }
    }

    // A child param the stack drives (the layer follows the stack's performance param of that name).
    static bool followed(const Layer& L, std::string_view name) {
        for (int f = 0; f < kFwdCount; ++f) {
            if (name == kFwdNames[static_cast<std::size_t>(f)]) return L.follow[f] && L.has[f];
        }
        return false;
    }

    // --------------------------------------------------------------------------------------- runtime

    Layer* findLayer(std::string_view id) {
        for (auto& L : layers_) if (L.id == id) return &L;
        return nullptr;
    }

    float childBend(const Layer& L) const {
        const float base = L.follow[kBend] ? L.bend0 + params_.get("pitchbend") : L.ownBend;
        return base + L.params.get("fine") / 100.0f;
    }

    void sendBend(Layer& L) {
        const float b = std::clamp(childBend(L), -24.0f, 24.0f);
        for (auto& in : L.inst) in->setParam("pitchbend", b);
    }

    void layerGains(const Layer& L, float& gl, float& gr) const {
        float g = L.params.get("mute") >= 0.5f ? 0.0f : dsp::dbToGain(L.params.get("level"));
        if (L.follow[kExpr] && !L.has[kExpr]) {
            const float e = params_.get("expression");
            g *= e * e;
        }
        const float pan = L.params.get("pan");
        gl = g * (pan > 0.0f ? std::cos(pan * static_cast<float>(dsp::kPi) * 0.5f) : 1.0f);
        gr = g * (pan < 0.0f ? std::cos(-pan * static_cast<float>(dsp::kPi) * 0.5f) : 1.0f);
    }

    void updateGains(Layer& L) {
        float gl, gr;
        layerGains(L, gl, gr);
        L.gainL.setTarget(gl);
        L.gainR.setTarget(gr);
    }

    bool setLayerParam(Layer& L, std::string_view sub, float value) {
        if (sub.substr(0, 3) == "fx.") {
            const std::string_view r = sub.substr(3);
            const auto dot = r.find('.');
            if (dot == std::string_view::npos || !digitsOnly(r.substr(0, dot)) || dot > 3) return false;
            std::size_t j = 0;
            for (char c : r.substr(0, dot)) j = j * 10 + static_cast<std::size_t>(c - '0');
            return j < L.fx.size() && L.fx[j]->setParam(r.substr(dot + 1), value);
        }
        if (L.params.index(sub) >= 0) {
            if (sub == "fine" && !L.has[kBend]) return false;
            if (!L.params.set(sub, value)) return false;
            if (sub == "fine") sendBend(L);
            else updateGains(L);   // level, pan, mute
            return true;
        }
        if (followed(L, sub) || findSpec(L.childSpecs, sub) == nullptr) return false;
        if (sub == "pitchbend") {
            const ParamSpec* s = findSpec(L.childSpecs, sub);
            if (!s->automatable) return false;
            L.ownBend = std::clamp(value, s->min, s->max);
            sendBend(L);
            return true;
        }
        bool ok = true;
        for (auto& in : L.inst) ok = in->setParam(sub, value) && ok;
        return ok;
    }

    float gainAt(const Layer& L, int key, int vel) const {
        if (key < L.keylo || key > L.keyhi || vel < L.vello || vel > L.velhi) return 0.0f;
        double g = 1.0;
        if (L.keyfade > 0) {
            if (L.keylo > 0) g *= edge(static_cast<double>(key - L.keylo) / L.keyfade);
            if (L.keyhi < 127) g *= edge(static_cast<double>(L.keyhi - key) / L.keyfade);
        }
        if (L.velfade > 0) {
            if (L.vello > 0) g *= edge(static_cast<double>(vel - L.vello) / L.velfade);
            if (L.velhi < 127) g *= edge(static_cast<double>(L.velhi - vel) / L.velfade);
        }
        return static_cast<float>(g);
    }

    // A crossfade gain on the kXfStepDb grid (at most half a step off): notes of nearby velocities / keys then share
    // a crossfade voice instead of each taking one. Within half a step of unity: the main instance's gain 1.
    static float xfGain(float g) {
        const float db = std::round(20.0f * std::log10(g) / kXfStepDb) * kXfStepDb;
        return db >= 0.0f ? 1.0f : std::pow(10.0f, db / 20.0f);
    }

    // The instance for a note at fade gain g (0 < g <= 1): the main one at unity, else the crossfade voice already at
    // (the grid value of) g, else a free one (it takes the gain), else the instance with the nearest gain in dB.
    int poolVoice(Layer& L, float g) {
        const std::size_t n = L.inst.size();
        if (g >= 0.9999f || n <= 1) return 0;   // (n <= 1 cannot happen with g < 1: a layer with fades has voices)
        g = xfGain(g);
        if (g >= 1.0f) return 0;
        for (std::size_t k = 1; k < n; ++k) {
            if (L.instGain[k] == g && (L.instNotes[k] > 0 || !L.inst[k]->idle())) return static_cast<int>(k);
        }
        for (std::size_t k = 1; k < n; ++k) {
            if (L.instNotes[k] == 0 && L.inst[k]->idle()) {
                L.instGain[k] = g;
                return static_cast<int>(k);
            }
        }
        std::size_t best = 0;
        float bestDist = std::fabs(std::log(g));   // the main instance (gain 1)
        for (std::size_t k = 1; k < n; ++k) {
            const float d = std::fabs(std::log(g / L.instGain[k]));
            if (d < bestDist) {
                bestDist = d;
                best = k;
            }
        }
        return static_cast<int>(best);
    }

    void offNow(Layer& L, int k, int noteId) {
        if (L.follow[kPedal] && !L.has[kPedal] && L.pedalDown && L.held.size() < static_cast<std::size_t>(kMaxHeld)) {
            L.held.emplace_back(k, noteId);
            return;
        }
        L.inst[static_cast<std::size_t>(k)]->noteOff(noteId);
        --L.instNotes[static_cast<std::size_t>(k)];
    }

    void applyPedal(Layer& L, float v) {
        const bool down = v >= 0.5f;
        if (L.has[kPedal]) {
            for (auto& in : L.inst) in->setParam("pedal", v);
        } else if (L.pedalDown && !down) {
            releaseHeld(L);
        }
        L.pedalDown = down;
    }

    void releaseHeld(Layer& L) {
        for (const auto& [k, id] : L.held) {
            L.inst[static_cast<std::size_t>(k)]->noteOff(id);
            --L.instNotes[static_cast<std::size_t>(k)];
        }
        L.held.clear();
    }

    void enqueue(const Event& e) {
        if (qHead_ > 0 && (qHead_ == queue_.size() || queue_.size() >= static_cast<std::size_t>(kMaxQueue))) {
            queue_.erase(queue_.begin(), queue_.begin() + static_cast<std::ptrdiff_t>(qHead_));
            qHead_ = 0;
        }
        if (queue_.size() >= static_cast<std::size_t>(kMaxQueue)) {  // full: play it now rather than never
            deliver(e);
            return;
        }
        std::size_t at = queue_.size();
        while (at > qHead_ && queue_[at - 1].at > e.at) --at;   // stable: after events at the same time
        queue_.insert(queue_.begin() + static_cast<std::ptrdiff_t>(at), e);
    }

    void deliver(const Event& e) {
        Layer& L = layers_[static_cast<std::size_t>(e.layer)];
        if (e.kind == Kind::On) L.inst[static_cast<std::size_t>(e.inst)]->noteOn(e.id, e.pitch, e.vel);
        else if (e.kind == Kind::Off) offNow(L, e.inst, e.id);
        else applyPedal(L, e.vel);
    }

    void dispatchDue(std::int64_t t) {
        while (qHead_ < queue_.size() && queue_[qHead_].at <= t) deliver(queue_[qHead_++]);
        if (qHead_ == queue_.size()) {
            queue_.clear();
            qHead_ = 0;
        }
    }

    void renderSegment(float* out0, float* out1, int n) {
        std::fill_n(out0, n, 0.0f);
        std::fill_n(out1, n, 0.0f);
        for (auto& L : layers_) {
            float* bl = L.bufL.data();
            float* br = L.bufR.data();
            L.inst[0]->process(bl, br, n);
            for (std::size_t k = 1; k < L.inst.size(); ++k) {
                L.inst[k]->process(tmpL_.data(), tmpR_.data(), n);
                const float g = L.instGain[k];
                if (g == 0.0f) continue;
                for (int i = 0; i < n; ++i) {
                    bl[i] += tmpL_[static_cast<std::size_t>(i)] * g;
                    br[i] += tmpR_[static_cast<std::size_t>(i)] * g;
                }
            }
            for (auto& fx : L.fx) fx->process(bl, br, n, nullptr, nullptr);
            for (int i = 0; i < n; ++i) {
                out0[i] += bl[i] * L.gainL.next();
                out1[i] += br[i] * L.gainR.next();
            }
        }
        for (int i = 0; i < n; ++i) {
            const float g = level_.next();
            out0[i] *= g;
            out1[i] *= g;
        }
    }

    Params params_;
    std::vector<ParamSpec> docs_, specs_;
    std::vector<Layer> layers_;
    std::vector<NoteRec> notes_;
    std::vector<Event> queue_;
    std::size_t qHead_{0};
    std::vector<float> tmpL_, tmpR_;
    Smooth2 level_;
    double sr_{48000.0};
    std::int64_t now_{0};
    bool pedalDown_{false};
    bool configured_{false};
};

}  // namespace

std::unique_ptr<Instrument> makeStack() { return std::make_unique<Stack>(); }

}  // namespace as
