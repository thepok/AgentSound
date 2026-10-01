#include "render/Renderer.h"

#include "analysis/MixAnalyzer.h"
#include "dsp/Dsp.h"
#include "io/WavWriter.h"
#include "render/Registry.h"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>

namespace as {
namespace {

constexpr int kBlock = kAutomationStep;  // automation, modulation and routing granularity (samples)
constexpr float kSilence = 1e-5f;        // -100 dBFS
constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
constexpr double kGridEps = 1e-9;        // a block starting (numerically) on a grid line belongs to the new step
constexpr double kFaderSmoothSeconds = 0.01;      // gain / pan / send smoothing (automation, static)
constexpr double kModFaderSmoothSeconds = 0.002;  // ... when a modulator drives them (gates stay crisp, no clicks)

struct NoteEvent {
    std::int64_t sample;
    bool on;
    int id;
    int pitch;
    float velocity;
    bool resumed{false};  // note-on moved to a preview's first sample (the note began earlier; modulators
                          // saw its real note-on in their preroll and ignore this one)
};

// Sample-accurate note events of a track's notes (song beats -> song samples through the tempo map),
// offs before ons at the same sample.
// Render mode (`history` false): the notes overlapping [from, to); notes that began before `from`
// restart at `from` (flagged `resumed`). History mode (modulator preroll): every event before `to`.
void collectNoteEvents(const NodeSpec& spec, const TempoMap& tempo, std::int64_t from, std::int64_t to,
                       bool history, int& noteId, std::vector<NoteEvent>& out) {
    auto toSample = [&](double beat) { return static_cast<std::int64_t>(std::llround(tempo.sampleAt(beat))); };
    for (const auto& n : spec.notes) {
        std::int64_t on = toSample(n.startBeat);
        const std::int64_t off = std::max(on + 1, toSample(n.startBeat + n.durationBeats));
        const float velocity = static_cast<float>(n.velocity) / 127.0f;
        if (history) {
            if (on >= to) continue;
            const int id = noteId++;
            out.push_back({on, true, id, n.pitch, velocity});
            if (off < to) out.push_back({off, false, id, n.pitch, 0.0f});
            continue;
        }
        if (off <= from || on >= to) continue;
        const bool resumed = on < from;
        if (resumed) on = from;
        const int id = noteId++;
        out.push_back({on, true, id, n.pitch, velocity, resumed});
        out.push_back({off, false, id, n.pitch, 0.0f});
    }
    std::stable_sort(out.begin(), out.end(), [](const NoteEvent& a, const NoteEvent& b) {
        if (a.sample != b.sample) return a.sample < b.sample;
        // Note-ons before note-offs at the same sample: back-to-back notes then overlap by zero
        // samples, which mono/legato voices treat as legato (glide, no retrigger) like a player would.
        return a.on && !b.on;
    });
}

// One control the renderer drives: a module parameter or the node's fader / pan / a send level.
// It is fed by at most one automation lane and any number of modulators, applied in declaration
// order on top of the lane value (absolute modulators replace it, offset modulators add to it).
struct Target {
    enum class Kind { Instrument, Fx, Gain, Pan, Send } kind{};
    int fxIndex{-1};
    int sendIndex{-1};
    std::string param;
    std::string name;           // target string as written (messages)
    double lo{0.0}, hi{0.0};    // the control's range; every value written is clamped to it
    double fallback{kNaN};      // value while neither lane nor modulator drives it (NaN: keep the configured value)
    int baseMod{-1};            // first modulator with a 'base': its (possibly automated) base replaces `fallback`
    int lane{-1};               // index into Node::lanes, -1 if not automated
    std::vector<int> mods;      // indices into Node::mods
    double laneValue{kNaN};
    double last{kNaN};          // last value written

    bool sameControl(const Target& o) const {
        return kind == o.kind && fxIndex == o.fxIndex && sendIndex == o.sendIndex && param == o.param;
    }
};

struct Lane {
    const AutomationLane* spec{};
    std::size_t cursor{0};
    int target{-1};             // index into Node::targets, or -1 for a modulator field lane ('mod.<i>.<field>')
    int mod{-1};
    ModField field{ModField::Depth};
    double lo{0.0}, hi{0.0};    // modulator field range
};

struct Mod {
    const ModulatorSpec* spec{};
    int target{-1};
    std::array<double, kModFieldCount> f{};  // live field values: the JSON value, or its 'mod.<i>.<field>' lane
    double origin{0.0};         // song beat the modulator's tempo grid counts from (startBeat or 0)
    bool accumulate{false};     // lfo/random phase integrated block by block (automated rate, note retrigger)
    double cycles{0.0};         // cycles since origin (or since the last retrigger) when accumulating
    std::uint64_t triggers{0};  // retrigger count (reseeds random shapes per note)
    std::uint64_t seed{0};
    int trigNode{-1};           // node whose note-ons (re)trigger it
    std::size_t trigCursor{0};
    int held{0};                // notes currently held on trigNode (envelope gate)
    int followNode{-1};
    double follow{0.0};         // follower level (linear amplitude)
    std::array<double, 2> coefMs{-1.0, -1.0};
    std::array<double, 2> coef{1.0, 1.0};   // follower attack / release one-pole coefficients
    enum class Stage { Idle, Attack, Decay, Sustain, Release } stage{Stage::Idle};
    double level{0.0};          // envelope level 0..1
    double releaseSlope{0.0};   // envelope level per beat while releasing (< 0: instant)
    double value{0.0};          // source output of the current block: -1..1 bipolar, 0..1 for follow/envelope,
                                // target units for absolute-mode steps

    double& at(ModField field) { return f[static_cast<std::size_t>(field)]; }
    double get(ModField field) const { return f[static_cast<std::size_t>(field)]; }
};

struct Send {
    int target{};
    float db{};
    dsp::Smoother gain;
};

struct Node {
    const NodeSpec* spec{};
    std::unique_ptr<Instrument> instrument;
    std::vector<std::unique_ptr<Effect>> fx;
    std::vector<int> fxKey;          // node index of each fx's sidechain key, -1 if none
    int output{-1};                  // node index, -1 for master
    std::vector<Send> sends;
    std::vector<Target> targets;
    std::vector<Lane> lanes;
    std::vector<Mod> mods;
    float gainDb{0.0f};
    float pan{0.0f};
    dsp::Smoother gainL, gainR;
    std::vector<float> inL, inR;     // summing inputs (buses, master)
    std::vector<float> outL, outR;   // post-fader, pre-mute (sidechain key / follower signal)
    std::vector<NoteEvent> events;
    std::size_t nextEvent{0};
    int analyzerIndex{-1};
    std::unique_ptr<WavWriter> stem;
};

// Balance-style pan: unity at centre, the opposite side attenuated with a cosine law.
void panToGains(float pan, float& l, float& r) {
    pan = std::clamp(pan, -1.0f, 1.0f);
    l = pan > 0.0f ? std::cos(pan * static_cast<float>(dsp::kPi) * 0.5f) : 1.0f;
    r = pan < 0.0f ? std::cos(-pan * static_cast<float>(dsp::kPi) * 0.5f) : 1.0f;
}

double evaluate(const AutomationLane& lane, std::size_t& cursor, double beat) {
    const auto& p = lane.points;
    if (beat <= p.front().beat) { cursor = 0; return p.front().value; }
    if (beat >= p.back().beat) { cursor = p.size() - 1; return p.back().value; }
    if (cursor >= p.size() || p[cursor].beat > beat) cursor = 0;
    while (cursor + 1 < p.size() && p[cursor + 1].beat <= beat) ++cursor;
    const auto& a = p[cursor];
    const auto& b = p[cursor + 1];
    const double t = (beat - a.beat) / (b.beat - a.beat);
    switch (b.curve) {
        case Curve::Linear: return a.value + (b.value - a.value) * t;
        case Curve::Exp: return a.value * std::pow(b.value / a.value, t);
        case Curve::Smooth: return a.value + (b.value - a.value) * (0.5 - 0.5 * std::cos(dsp::kPi * t));
        case Curve::Step: return a.value;
    }
    return a.value;
}

const ParamSpec* automatableSpec(const std::vector<ParamSpec>& specs, const std::string& name) {
    for (const auto& s : specs) if (s.name == name && s.automatable) return &s;
    return nullptr;
}

std::uint64_t moduleSeed(std::uint64_t songSeed, const std::string& nodeId, int slot) {
    return songSeed * 0x9E3779B97F4A7C15ull ^ dsp::hashString(nodeId.c_str()) ^
           (static_cast<std::uint64_t>(slot + 2) * 0xBF58476D1CE4E5B9ull);
}

std::string fmt(double v) {
    std::ostringstream s;
    s << v;
    return s.str();
}

[[noreturn]] void badTarget(const std::string& where, const std::string& target, const std::string& why) {
    throw ConfigError(where + ": '" + target + "' " + why);
}

// ---- modulator sources

std::uint64_t mix64(std::uint64_t x) {  // splitmix64 finaliser
    x += 0x9E3779B97F4A7C15ull;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ull;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBull;
    return x ^ (x >> 31);
}

// Random value in [-1, 1) for grid step k: a pure function of (seed, step, retrigger count), so a
// preview render sees exactly the values of the full render.
double randomAt(const Mod& m, double k) {
    const auto step = static_cast<std::uint64_t>(static_cast<std::int64_t>(k));
    const std::uint64_t x = mix64(m.seed ^ mix64(step ^ (m.triggers * 0xD1B54A32D192ED03ull)));
    return static_cast<double>(x >> 11) * (2.0 / 9007199254740992.0) - 1.0;
}

double ease(double t) { return 0.5 - 0.5 * std::cos(dsp::kPi * t); }

// Bipolar LFO shapes; phase 0 is the start of a musical cycle: sine/triangle start at their minimum,
// saw falls from +1, ramp rises from -1, square is high for the first half.
double lfoShape(const Mod& m, double frac, double k) {
    switch (m.spec->shape) {
        case LfoShape::Sine: return -std::cos(dsp::kTwoPi * frac);
        case LfoShape::Triangle: return 1.0 - 4.0 * std::fabs(frac - 0.5);
        case LfoShape::Saw: return 1.0 - 2.0 * frac;
        case LfoShape::Ramp: return 2.0 * frac - 1.0;
        case LfoShape::Square: return frac < 0.5 ? 1.0 : -1.0;
        case LfoShape::Random: return randomAt(m, k);
        case LfoShape::SmoothRandom: {
            const double a = randomAt(m, k), b = randomAt(m, k + 1.0);
            return a + (b - a) * ease(frac);
        }
    }
    return 0.0;
}

bool activeAt(const ModulatorSpec& s, double beat) {
    return (!s.startBeat || beat >= *s.startBeat - kGridEps) && (!s.endBeat || beat < *s.endBeat - kGridEps);
}

// Maps the source value of `m` onto the target, given the value below it (lane / earlier modulators).
double applyMod(const Mod& m, double current) {
    const ModulatorSpec& s = *m.spec;
    if (!s.offset) {
        if (s.source == ModSource::Steps) return m.value;
        const double u = s.unipolar() ? m.value : 0.5 * (m.value + 1.0);
        const double lo = m.get(ModField::Min), hi = m.get(ModField::Max);
        return s.expCurve ? lo * std::pow(hi / lo, u) : lo + (hi - lo) * u;
    }
    const double base = std::isnan(current) ? m.get(ModField::Base) : current;
    const double amount = m.get(ModField::Depth) * m.value;
    return s.expCurve ? std::max(base, 1e-9) * std::exp2(amount) : base + amount;
}

ModField rateField(const ModulatorSpec& s) {
    return s.source == ModSource::Lfo && s.rateHz > 0 ? ModField::RateHz : ModField::RateBeats;
}

class Graph {
public:
    Graph(const SongSpec& song, const TempoMap& tempo, const std::string& assetDir, double startBeat = 0.0)
        : song_(song), tempo_(tempo), constant_(tempo.constant()), samplesPerBeat_(song.sampleRate * 60.0 / song.tempo) {
        const int n = static_cast<int>(song.nodes.size());
        nodes_.resize(static_cast<std::size_t>(n));

        for (int i = 0; i < n; ++i) {
            const NodeSpec& spec = song.nodes[static_cast<std::size_t>(i)];
            Node& node = nodes_[static_cast<std::size_t>(i)];
            node.spec = &spec;
            node.gainDb = spec.gainDb;
            node.pan = spec.pan;
            node.output = spec.kind == NodeSpec::Kind::Master ? -1 : indexOf(spec.output);
            if (spec.kind != NodeSpec::Kind::Master && spec.output == "master") node.output = n - 1;

            RenderContext ctx;
            ctx.sampleRate = song.sampleRate;
            ctx.bpm = song.tempo;
            ctx.maxBlock = kBlock;
            ctx.assetDir = assetDir;
            ctx.startBeat = startBeat;

            if (spec.kind == NodeSpec::Kind::Track) {
                try {
                    node.instrument = createInstrument(spec.instrumentType);
                    node.instrument->configure(spec.instrumentParams);
                    if (!constant_) node.instrument->setTempoMap(tempo_);
                    ctx.seed = moduleSeed(song.seed, spec.id, -1);
                    node.instrument->prepare(ctx);
                } catch (const ConfigError& e) {
                    throw ConfigError(spec.path + ".instrument: " + e.what());
                }
            }
            for (std::size_t f = 0; f < spec.fx.size(); ++f) {
                const FxSpec& fs = spec.fx[f];
                try {
                    auto fx = createEffect(fs.type);
                    fx->configure(fs.params);
                    if (!constant_) fx->setTempoMap(tempo_);
                    ctx.seed = moduleSeed(song.seed, spec.id, static_cast<int>(f));
                    fx->prepare(ctx);
                    if (!fs.sidechain.empty() && !effectAcceptsSidechain(fs.type)) {
                        throw ConfigError("effect '" + fs.type + "' does not accept a sidechain");
                    }
                    if (fs.sidechain.empty() && effectRequiresSidechain(fs.type)) {
                        throw ConfigError("effect '" + fs.type + "' needs a \"sidechain\": the modulator it listens to (e.g. a "
                                          "muted speech track; this node's own signal is the carrier)");
                    }
                    if (fx->latencySamples() > 0 && spec.kind != NodeSpec::Kind::Master) {
                        throw ConfigError("effect '" + fs.type + "' adds latency and is only allowed on the master chain");
                    }
                    node.fx.push_back(std::move(fx));
                } catch (const ConfigError& e) {
                    throw ConfigError(fs.path + ": " + e.what());
                }
                node.fxKey.push_back(fs.sidechain.empty() ? -1 : indexOf(fs.sidechain));
            }
            for (const auto& [busId, db] : spec.sends) {
                Send s;
                s.target = indexOf(busId);
                s.db = db;
                s.gain.prepare(song.sampleRate, kFaderSmoothSeconds, dsp::dbToGain(db));
                node.sends.push_back(std::move(s));
            }
            float gl, gr;
            panToGains(node.pan, gl, gr);
            const float g = dsp::dbToGain(node.gainDb);
            node.gainL.prepare(song.sampleRate, kFaderSmoothSeconds, g * gl);
            node.gainR.prepare(song.sampleRate, kFaderSmoothSeconds, g * gr);
            node.inL.assign(kBlock, 0.0f);
            node.inR.assign(kBlock, 0.0f);
            node.outL.assign(kBlock, 0.0f);
            node.outR.assign(kBlock, 0.0f);
            bindControls(node, i);
            // Modulated faders / pans / sends follow their modulators closely (a trance gate needs crisp
            // edges); automation-only ones keep the gentler smoothing.
            for (const Target& t : node.targets) {
                if (t.mods.empty()) continue;
                if (t.kind == Target::Kind::Gain || t.kind == Target::Kind::Pan) {
                    node.gainL.prepare(song.sampleRate, kModFaderSmoothSeconds, node.gainL.value());
                    node.gainR.prepare(song.sampleRate, kModFaderSmoothSeconds, node.gainR.value());
                } else if (t.kind == Target::Kind::Send) {
                    dsp::Smoother& g = node.sends[static_cast<std::size_t>(t.sendIndex)].gain;
                    g.prepare(song.sampleRate, kModFaderSmoothSeconds, g.value());
                }
            }
            preroll(node, startBeat);  // after bindControls: needs the modulator lanes
        }
        order_ = topologicalOrder();
    }

    std::vector<Node>& nodes() { return nodes_; }
    const std::vector<int>& order() const { return order_; }
    Node& master() { return nodes_.back(); }

    // Song beat of song sample `pos` (a constant tempo keeps its classic arithmetic: bit-identical renders).
    double beatAt(std::int64_t pos) const {
        return constant_ ? static_cast<double>(pos) / samplesPerBeat_ : tempo_.beatAtSample(static_cast<double>(pos));
    }
    // Beats spanned by the n samples from `pos` (whose beat is `beat`).
    double beatsIn(std::int64_t pos, int n, double beat) const {
        return constant_ ? n / samplesPerBeat_ : tempo_.beatAtSample(static_cast<double>(pos + n)) - beat;
    }

    // Records the value written to `trace.target` of node `trace.node` in every block.
    void setProbe(ControlTrace* trace) {
        const int index = indexOf(trace->node);
        if (index < 0) throw ConfigError("trace: '" + trace->node + "' is not a node id");
        Node& node = nodes_[static_cast<std::size_t>(index)];
        const Target wanted = resolveTarget(node, trace->target, "trace");
        for (std::size_t t = 0; t < node.targets.size(); ++t) {
            if (!node.targets[t].sameControl(wanted)) continue;
            probe_ = trace;
            probeNode_ = &node;
            probeTarget_ = static_cast<int>(t);
            return;
        }
        throw ConfigError("trace: '" + trace->target + "' of '" + trace->node + "' is not driven by automation or modulators");
    }

    // Once per block, right before `node` is processed (its follower keys are already processed):
    // automation lanes, modulator sources, then every control target; finally the fader smoothers.
    void updateControls(Node& node, std::int64_t pos, int n) {
        const double beat = beatAt(pos);
        const double blockBeats = beatsIn(pos, n, beat);
        for (auto& lane : node.lanes) {
            const double v = evaluate(*lane.spec, lane.cursor, beat);
            if (lane.target >= 0) node.targets[static_cast<std::size_t>(lane.target)].laneValue = v;
            else node.mods[static_cast<std::size_t>(lane.mod)].at(lane.field) = std::clamp(v, lane.lo, lane.hi);
        }
        for (auto& m : node.mods) runSource(m, nullptr, pos, n, beat, blockBeats);
        for (std::size_t ti = 0; ti < node.targets.size(); ++ti) {
            Target& t = node.targets[ti];
            double v = t.lane >= 0 ? t.laneValue : kNaN;
            for (int mi : t.mods) {
                const Mod& m = node.mods[static_cast<std::size_t>(mi)];
                if (activeAt(*m.spec, beat)) v = applyMod(m, v);
            }
            if (std::isnan(v)) v = t.baseMod >= 0 ? node.mods[static_cast<std::size_t>(t.baseMod)].get(ModField::Base) : t.fallback;
            if (!std::isnan(v)) v = std::clamp(v, t.lo, t.hi);
            if (probe_ && probeNode_ == &node && probeTarget_ == static_cast<int>(ti)) {
                probe_->values.push_back(v);
                probe_->beats.push_back(beat);
            }
            if (std::isnan(v) || v == t.last) continue;
            t.last = v;
            const auto fv = static_cast<float>(v);
            switch (t.kind) {
                case Target::Kind::Instrument: node.instrument->setParam(t.param, fv); break;
                case Target::Kind::Fx: node.fx[static_cast<std::size_t>(t.fxIndex)]->setParam(t.param, fv); break;
                case Target::Kind::Gain: node.gainDb = fv; break;
                case Target::Kind::Pan: node.pan = fv; break;
                case Target::Kind::Send: node.sends[static_cast<std::size_t>(t.sendIndex)].db = fv; break;
            }
        }
        float gl, gr;
        panToGains(node.pan, gl, gr);
        const float g = node.gainDb <= -119.9f ? 0.0f : dsp::dbToGain(node.gainDb);
        node.gainL.setTarget(g * gl);
        node.gainR.setTarget(g * gr);
        for (auto& s : node.sends) s.gain.setTarget(s.db <= -119.9f ? 0.0f : dsp::dbToGain(s.db));
    }

private:
    int indexOf(const std::string& id) const {
        for (std::size_t i = 0; i < song_.nodes.size(); ++i) if (song_.nodes[i].id == id) return static_cast<int>(i);
        return -1;
    }

    // Resolves an automation / modulator target string of `node` (its range and static value).
    static Target resolveTarget(const Node& node, const std::string& t, const std::string& where) {
        const NodeSpec& spec = *node.spec;
        Target target;
        target.name = t;
        if (t == "gainDb") {
            target.kind = Target::Kind::Gain;
            target.lo = -120.0;
            target.hi = 24.0;
            target.fallback = spec.gainDb;
        } else if (t == "pan") {
            target.kind = Target::Kind::Pan;
            target.lo = -1.0;
            target.hi = 1.0;
            target.fallback = spec.pan;
        } else if (t.rfind("instrument.", 0) == 0) {
            if (!node.instrument) badTarget(where, t, "- only tracks have an instrument");
            target.kind = Target::Kind::Instrument;
            target.param = t.substr(11);
            const ParamSpec* p = automatableSpec(node.instrument->paramSpecs(), target.param);
            if (!p) badTarget(where, t, "is not an automatable instrument parameter");
            target.lo = p->min;
            target.hi = p->max;
        } else if (t.rfind("fx.", 0) == 0) {
            const auto dot = t.find('.', 3);
            if (dot == std::string::npos) badTarget(where, t, "must be fx.<index>.<param>");
            const std::string digits = t.substr(3, dot - 3);
            if (digits.empty() || digits.size() > 3 || !std::all_of(digits.begin(), digits.end(), [](char c) { return c >= '0' && c <= '9'; })) {
                badTarget(where, t, "has a bad fx index");
            }
            const int index = std::stoi(digits);
            if (index < 0 || index >= static_cast<int>(node.fx.size())) badTarget(where, t, "refers to a missing fx slot");
            target.kind = Target::Kind::Fx;
            target.fxIndex = index;
            target.param = t.substr(dot + 1);
            const ParamSpec* p = automatableSpec(node.fx[static_cast<std::size_t>(index)]->paramSpecs(), target.param);
            if (!p) badTarget(where, t, "is not an automatable parameter of that effect");
            target.lo = p->min;
            target.hi = p->max;
        } else if (t.rfind("send.", 0) == 0) {
            const std::string bus = t.substr(5);
            for (std::size_t s = 0; s < spec.sends.size(); ++s) {
                if (spec.sends[s].first == bus) target.sendIndex = static_cast<int>(s);
            }
            if (target.sendIndex < 0) badTarget(where, t, "needs a matching entry in 'sends'");
            target.kind = Target::Kind::Send;
            target.lo = -120.0;
            target.hi = 24.0;
            target.fallback = spec.sends[static_cast<std::size_t>(target.sendIndex)].second;
        } else {
            badTarget(where, t, "is not a valid target (instrument.<p>, fx.<i>.<p>, gainDb, pan, send.<bus>)");
        }
        return target;
    }

    static int targetSlot(Node& node, Target target) {
        for (std::size_t i = 0; i < node.targets.size(); ++i) {
            if (node.targets[i].sameControl(target)) return static_cast<int>(i);
        }
        node.targets.push_back(std::move(target));
        return static_cast<int>(node.targets.size()) - 1;
    }

    void bindControls(Node& node, int self) {
        const NodeSpec& spec = *node.spec;
        // Modulators first: 'mod.<i>.<field>' lanes refer to them.
        for (std::size_t i = 0; i < spec.modulators.size(); ++i) {
            const ModulatorSpec& ms = spec.modulators[i];
            Mod m;
            m.spec = &ms;
            for (int f = 0; f < kModFieldCount; ++f) m.f[static_cast<std::size_t>(f)] = modFieldValue(ms, static_cast<ModField>(f));
            m.origin = ms.startBeat.value_or(0.0);
            m.accumulate = ms.retrigger;
            m.seed = moduleSeed(song_.seed, spec.id, 1000 + static_cast<int>(i));
            if (ms.source == ModSource::Follow) m.followNode = indexOf(ms.followNode);
            if (ms.retrigger || ms.source == ModSource::Envelope) m.trigNode = ms.trigger.empty() ? self : indexOf(ms.trigger);
            m.target = targetSlot(node, resolveTarget(node, ms.target, ms.path + ".target"));
            node.targets[static_cast<std::size_t>(m.target)].mods.push_back(static_cast<int>(i));
            node.mods.push_back(m);
        }
        for (const auto& a : spec.automation) {
            Lane lane;
            lane.spec = &a;
            if (a.target.rfind("mod.", 0) == 0) {
                bindModulatorLane(node, lane);
            } else {
                Target t = resolveTarget(node, a.target, a.path + ".target");
                if (t.kind == Target::Kind::Pan) {
                    for (const auto& p : a.points) {
                        if (p.value < -1 || p.value > 1) badTarget(a.path + ".target", a.target, "pan values must be in -1..1");
                    }
                }
                const int slot = targetSlot(node, std::move(t));
                if (node.targets[static_cast<std::size_t>(slot)].lane >= 0) {
                    badTarget(a.path + ".target", a.target, "is automated twice; merge the points into one lane");
                }
                node.targets[static_cast<std::size_t>(slot)].lane = static_cast<int>(node.lanes.size());
                lane.target = slot;
            }
            node.lanes.push_back(lane);
        }
        for (auto& t : node.targets) checkTarget(node, t);
    }

    // 'mod.<index>.<field>' automation of a modulator field (depth, min, max, rateBeats, ...).
    void bindModulatorLane(Node& node, Lane& lane) {
        const AutomationLane& a = *lane.spec;
        const std::string& t = a.target;
        const std::string where = a.path + ".target";
        const auto dot = t.find('.', 4);
        if (dot == std::string::npos || dot == 4) badTarget(where, t, "must be mod.<index>.<field>");
        const std::string idx = t.substr(4, dot - 4);
        if (!std::all_of(idx.begin(), idx.end(), [](char c) { return c >= '0' && c <= '9'; }) || idx.size() > 3) {
            badTarget(where, t, "has a bad modulator index");
        }
        const int index = std::stoi(idx);
        if (index >= static_cast<int>(node.mods.size())) {
            badTarget(where, t, "refers to a missing modulator (this node has " + std::to_string(node.mods.size()) + ")");
        }
        const std::string name = t.substr(dot + 1);
        int found = -1;
        std::string all;
        for (int f = 0; f < kModFieldCount; ++f) {
            const char* fname = modFieldName(static_cast<ModField>(f));
            all += (f ? " " : "") + std::string(fname);
            if (name == fname) found = f;
        }
        if (found < 0) badTarget(where, t, "has an unknown field (fields: " + all + ")");
        Mod& m = node.mods[static_cast<std::size_t>(index)];
        const ModField field = static_cast<ModField>(found);
        double lo = 0.0, hi = 0.0;
        if (!modFieldRange(*m.spec, field, lo, hi)) {
            badTarget(where, t, "- '" + name + "' is not a field of that modulator (" +
                                    (field == ModField::Base ? "give it a static 'base' first" : "wrong source type or mode") + ")");
        }
        const Target& target = node.targets[static_cast<std::size_t>(m.target)];
        const bool targetUnits = field == ModField::Min || field == ModField::Max || field == ModField::Base;
        for (const auto& p : a.points) {
            if (p.value < lo || p.value > hi) {
                badTarget(where, t, "value " + fmt(p.value) + " at beat " + fmt(p.beat) + " is outside " + fmt(lo) + ".." + fmt(hi));
            }
            if (targetUnits && (p.value < target.lo || p.value > target.hi)) {
                badTarget(where, t, "value " + fmt(p.value) + " at beat " + fmt(p.beat) + " is outside the range " +
                                        fmt(target.lo) + ".." + fmt(target.hi) + " of '" + target.name + "'");
            }
        }
        for (const auto& other : node.lanes) {
            if (other.target < 0 && other.mod == index && other.field == field) badTarget(where, t, "is automated twice; merge the points into one lane");
        }
        lane.mod = index;
        lane.field = field;
        lane.lo = lo;
        lane.hi = hi;
        if (field == rateField(*m.spec) && (field == ModField::RateBeats || field == ModField::RateHz)) {
            m.accumulate = true;  // a moving rate must integrate its phase to stay continuous
        }
    }

    // Per-target rules: mapping values inside the control's range, 'base' vs. automation lane, and a
    // defined value outside every modulator window.
    void checkTarget(const Node& node, Target& t) const {
        const bool moduleParam = t.kind == Target::Kind::Instrument || t.kind == Target::Kind::Fx;
        bool allWindowed = !t.mods.empty();
        double firstBase = kNaN;
        auto inRange = [&](const ModulatorSpec& s, double v, const std::string& what) {
            if (v < t.lo || v > t.hi) {
                throw ConfigError(s.path + what + ": " + fmt(v) + " is outside the range " + fmt(t.lo) + ".." + fmt(t.hi) +
                                  " of '" + t.name + "'");
            }
        };
        for (int mi : t.mods) {
            const ModulatorSpec& s = *node.mods[static_cast<std::size_t>(mi)].spec;
            if (!s.offset) {
                if (s.source == ModSource::Steps) {
                    for (std::size_t k = 0; k < s.values.size(); ++k) inRange(s, s.values[k], ".source.values[" + std::to_string(k) + "]");
                } else {
                    inRange(s, s.min, ".min");
                    inRange(s, s.max, ".max");
                }
            }
            if (s.base) {
                if (t.lane >= 0) {
                    throw ConfigError(s.path + ".base: '" + t.name + "' has an automation lane, which is the base value; remove 'base'");
                }
                inRange(s, *s.base, ".base");
                if (std::isnan(firstBase)) { firstBase = *s.base; t.baseMod = mi; }
            }
            if (s.offset && t.lane < 0 && !s.base) {
                throw ConfigError(s.path + ": mode 'offset' adds to the automation lane of '" + t.name +
                                  "', which has none; give \"base\" (the centre value) or automate the target");
            }
            if (s.offset && s.expCurve && t.lane >= 0) {
                for (const auto& p : node.lanes[static_cast<std::size_t>(t.lane)].spec->points) {
                    if (p.value <= 0) {
                        throw ConfigError(s.path + ": curve 'exp' scales the automation of '" + t.name +
                                          "' by 2^(source*depth), which needs values > 0 (got " + fmt(p.value) + " at beat " + fmt(p.beat) + ")");
                    }
                }
            }
            if (!s.windowed()) allWindowed = false;
        }
        if (!std::isnan(firstBase)) t.fallback = firstBase;
        if (t.lane < 0 && moduleParam && allWindowed && std::isnan(t.fallback)) {
            const ModulatorSpec& s = *node.mods[static_cast<std::size_t>(t.mods.front())].spec;
            throw ConfigError(s.path + ": '" + t.name + "' has no automation lane, so outside the modulator window it needs "
                                       "\"base\" (the parameter value there) - modules do not report their configured values");
        }
    }

    // A preview render (startBeat > 0) starts every stateful modulator where the full render would be at
    // its first sample: accumulated lfo/random phases (automated rate, note retrigger) and envelopes are
    // run block by block from beat 0 on the full render's block grid, with the trigger track's real note
    // history and the modulator's field lanes. (Followers need audio and start at rest.)
    void preroll(Node& node, double startBeat) {
        const auto startSample = static_cast<std::int64_t>(std::llround(tempo_.sampleAt(startBeat)));
        if (startSample <= 0) return;
        std::vector<NoteEvent> history;
        for (std::size_t i = 0; i < node.mods.size(); ++i) {
            Mod& m = node.mods[i];
            if (!m.accumulate && m.spec->source != ModSource::Envelope) continue;
            history.clear();
            int ids = 0;
            if (m.trigNode >= 0) {
                collectNoteEvents(song_.nodes[static_cast<std::size_t>(m.trigNode)], tempo_, 0, startSample, true, ids, history);
            }
            std::vector<Lane> lanes;
            for (const Lane& lane : node.lanes) {
                if (lane.target < 0 && lane.mod == static_cast<int>(i)) lanes.push_back(lane);
            }
            m.trigCursor = 0;
            for (std::int64_t pos = 0; pos < startSample; pos += kBlock) {
                const int n = static_cast<int>(std::min<std::int64_t>(kBlock, startSample - pos));
                const double beat = beatAt(pos);
                for (Lane& lane : lanes) m.at(lane.field) = std::clamp(evaluate(*lane.spec, lane.cursor, beat), lane.lo, lane.hi);
                runSource(m, &history, pos, n, beat, beatsIn(pos, n, beat));
            }
            m.trigCursor = 0;  // the render's own event list starts now
        }
    }

    // Advances modulator `m` over the block [pos, pos + n) and sets m.value for it. `events` are the
    // trigger track's note events (nullptr: the render's list of m.trigNode).
    void runSource(Mod& m, const std::vector<NoteEvent>* events, std::int64_t pos, int n, double beat, double blockBeats) {
        const ModulatorSpec& s = *m.spec;
        bool noteOn = false;
        double onBeats = 0.0;  // position of the block's last note-on, in beats from the block start
        if (m.trigNode >= 0) {
            const auto& ev = events ? *events : nodes_[static_cast<std::size_t>(m.trigNode)].events;
            while (m.trigCursor < ev.size() && ev[m.trigCursor].sample < pos + n) {
                const NoteEvent& e = ev[m.trigCursor++];
                if (e.on && e.resumed) continue;  // held across a preview start: the preroll saw its real note-on
                if (e.on) {
                    ++m.held;
                    noteOn = true;
                    onBeats = constant_ ? static_cast<double>(std::max<std::int64_t>(0, e.sample - pos)) / samplesPerBeat_
                                        : beatAt(std::max(pos, e.sample)) - beat;
                } else if (m.held > 0) {
                    --m.held;
                }
            }
        }
        // Time this block advances a (re)triggered source: from the note-on, so the phase / level of later
        // blocks is exact relative to the note whatever the block grid (full render or preview).
        const double advance = noteOn ? blockBeats - onBeats : blockBeats;
        switch (s.source) {
            case ModSource::Lfo:
            case ModSource::Random: {
                const ModField rf = rateField(s);
                const double rate = m.get(rf);
                const double perBeat = rf == ModField::RateHz ? rate * 60.0 / song_.tempo : 1.0 / rate;
                // A free-running (Hz) lfo counts song time: with a changing tempo, the seconds between the beats.
                const bool seconds = rf == ModField::RateHz && !constant_;
                auto span = [&](double b0, double b1) { return seconds ? tempo_.secondsBetween(b0, b1) * rate : (b1 - b0) * perBeat; };
                double cycles;
                if (m.accumulate) {
                    const double end = std::max(beat + blockBeats, m.origin);
                    double from = std::max(beat, m.origin);
                    if (noteOn && s.retrigger) {
                        m.cycles = 0.0;
                        ++m.triggers;
                        from = std::min(end, std::max(beat + onBeats, m.origin));
                    }
                    cycles = m.cycles;
                    m.cycles += span(from, end);
                } else {
                    cycles = span(m.origin, beat);  // exact on the song grid, also for previews
                }
                if (s.source == ModSource::Lfo) {
                    const double p = m.get(ModField::Phase) + cycles;
                    const double k = std::floor(p + kGridEps);
                    m.value = lfoShape(m, std::max(0.0, p - k), k);
                } else {
                    const double k = std::floor(cycles + kGridEps);
                    const double frac = std::max(0.0, cycles - k);
                    const double smooth = m.get(ModField::Smooth);
                    const double b = randomAt(m, k);
                    if (smooth > 0.0 && frac < smooth) {
                        const double a = randomAt(m, k - 1.0);
                        m.value = a + (b - a) * ease(frac / smooth);
                    } else {
                        m.value = b;
                    }
                }
                break;
            }
            case ModSource::Steps: {
                const double x = std::max(0.0, (beat - m.origin) / s.stepBeats);
                const double k = std::floor(x + kGridEps);
                const double frac = std::max(0.0, x - k);
                const std::size_t count = s.values.size();
                double cur, prev;
                if (!s.loop && k >= static_cast<double>(count)) {
                    cur = prev = s.values.back();
                } else {
                    const auto idx = static_cast<std::size_t>(std::fmod(k, static_cast<double>(count)));
                    cur = s.values[idx];
                    prev = k < 1.0 ? cur : s.values[(idx + count - 1) % count];
                }
                const double glide = m.get(ModField::Glide);
                if (glide > 0.0 && frac < glide && prev != cur) {
                    const double t = frac / glide;
                    m.value = (!s.offset && s.expCurve) ? prev * std::pow(cur / prev, t) : prev + (cur - prev) * t;
                } else {
                    m.value = cur;
                }
                break;
            }
            case ModSource::Follow: {
                for (std::size_t c = 0; c < 2; ++c) {
                    const double ms = m.get(c == 0 ? ModField::AttackMs : ModField::ReleaseMs);
                    if (ms == m.coefMs[c]) continue;
                    m.coefMs[c] = ms;
                    m.coef[c] = ms <= 0.0 ? 1.0 : 1.0 - std::exp(-1.0 / (ms * 0.001 * song_.sampleRate));
                }
                const Node& key = nodes_[static_cast<std::size_t>(m.followNode)];
                const double g = std::pow(10.0, m.get(ModField::GainDb) / 20.0);
                double env = m.follow;
                for (int i = 0; i < n; ++i) {
                    const auto si = static_cast<std::size_t>(i);
                    const double x = std::max(std::fabs(key.outL[si]), std::fabs(key.outR[si])) * g;
                    env += (x > env ? m.coef[0] : m.coef[1]) * (x - env);
                }
                m.follow = env < 1e-12 ? 0.0 : env;
                m.value = std::min(m.follow, 1.0);
                break;
            }
            case ModSource::Envelope: {
                using Stage = Mod::Stage;
                if (noteOn) {  // retrigger from the current level (no jump down)
                    if (m.get(ModField::AttackBeats) <= 0.0) { m.level = 1.0; m.stage = Stage::Decay; }
                    else m.stage = Stage::Attack;
                }
                if (m.held == 0 && (m.stage == Stage::Attack || m.stage == Stage::Decay || m.stage == Stage::Sustain)) {
                    const double r = m.get(ModField::ReleaseBeats);
                    m.stage = Stage::Release;
                    m.releaseSlope = r > 0.0 ? m.level / r : -1.0;
                }
                m.value = m.level;
                const double sustain = m.get(ModField::Sustain);
                switch (m.stage) {  // advance to the start of the next block
                    case Stage::Idle: m.level = 0.0; break;
                    case Stage::Attack: {
                        const double a = m.get(ModField::AttackBeats);
                        m.level = a > 0.0 ? m.level + advance / a : 1.0;
                        if (m.level >= 1.0 - kGridEps) { m.level = 1.0; m.stage = Stage::Decay; }
                        break;
                    }
                    case Stage::Decay: {
                        const double d = m.get(ModField::DecayBeats);
                        m.level = d > 0.0 ? m.level - advance * (1.0 - sustain) / d : sustain;
                        if (m.level <= sustain + kGridEps) { m.level = sustain; m.stage = Stage::Sustain; }
                        break;
                    }
                    case Stage::Sustain: m.level = sustain; break;
                    case Stage::Release:
                        m.level = m.releaseSlope < 0.0 ? 0.0 : m.level - advance * m.releaseSlope;
                        if (m.level <= kGridEps) { m.level = 0.0; m.stage = Stage::Idle; }
                        break;
                }
                break;
            }
        }
    }

    std::vector<int> topologicalOrder() {
        const int n = static_cast<int>(nodes_.size());
        std::vector<std::vector<int>> after(static_cast<std::size_t>(n));  // edge u -> v: u before v
        std::vector<int> indegree(static_cast<std::size_t>(n), 0);
        auto edge = [&](int u, int v) { after[static_cast<std::size_t>(u)].push_back(v); ++indegree[static_cast<std::size_t>(v)]; };
        for (int i = 0; i < n; ++i) {
            const Node& node = nodes_[static_cast<std::size_t>(i)];
            if (node.output >= 0) edge(i, node.output);
            for (const auto& s : node.sends) edge(i, s.target);
            for (int key : node.fxKey) if (key >= 0) edge(key, i);
            for (const auto& m : node.mods) if (m.followNode >= 0) edge(m.followNode, i);
        }
        std::vector<int> order, ready;
        for (int i = 0; i < n; ++i) if (indegree[static_cast<std::size_t>(i)] == 0) ready.push_back(i);
        while (!ready.empty()) {
            std::sort(ready.begin(), ready.end(), std::greater<int>());  // stable: lowest index first
            const int u = ready.back();
            ready.pop_back();
            order.push_back(u);
            for (int v : after[static_cast<std::size_t>(u)]) {
                if (--indegree[static_cast<std::size_t>(v)] == 0) ready.push_back(v);
            }
        }
        if (static_cast<int>(order.size()) != n) {
            std::string stuck;
            for (int i = 0; i < n; ++i) {
                if (indegree[static_cast<std::size_t>(i)] > 0) stuck += (stuck.empty() ? "" : ", ") + nodes_[static_cast<std::size_t>(i)].spec->id;
            }
            throw ConfigError("routing cycle (outputs/sends/sidechains/followers) involving: " + stuck);
        }
        return order;
    }

    const SongSpec& song_;
    const TempoMap& tempo_;
    bool constant_;
    double samplesPerBeat_;           // constant tempo only
    std::vector<Node> nodes_;
    std::vector<int> order_;
    ControlTrace* probe_{nullptr};
    const Node* probeNode_{nullptr};
    int probeTarget_{-1};
};

}  // namespace

void validateSong(const SongSpec& song, const std::string& assetDir) {
    const TempoMap tempo = song.makeTempoMap();
    (void)song.makeMeterMap();  // validates a hand-built meter
    Graph graph(song, tempo, assetDir);
}

RenderResult renderSong(const SongSpec& song, const RenderOptions& options) {
    const auto wallStart = std::chrono::steady_clock::now();
    namespace fs = std::filesystem;
    fs::create_directories(options.outDir);

    const double requestedFrom = std::clamp(options.fromBeat.value_or(0.0), 0.0, song.lengthBeats);
    const double sr = song.sampleRate;
    // Song time: beats -> song samples through the tempo map (a constant tempo is one segment whose
    // arithmetic is the classic beat * sr * 60 / bpm), bars through the meter (report only).
    const TempoMap tempo = song.makeTempoMap();
    const MeterMap meter = song.makeMeterMap();
    auto toSample = [&](double beat) { return static_cast<std::int64_t>(std::llround(tempo.sampleAt(beat))); };
    // Blocks stay on the song's 32-sample grid (a preview starts up to 31 samples early) so automation
    // and modulator updates land on exactly the same samples as in the full render; every module and
    // the analyzer are told the exact song beat of the first rendered sample.
    const std::int64_t startSample = toSample(requestedFrom) / kBlock * kBlock;
    const double fromBeat = tempo.beatAtSample(static_cast<double>(startSample));
    Graph graph(song, tempo, options.assetDir, fromBeat);
    auto& nodes = graph.nodes();

    const double toBeat = std::clamp(options.toBeat.value_or(song.lengthBeats), requestedFrom, song.lengthBeats);
    if (toBeat <= requestedFrom) throw ConfigError("render window is empty (fromBeat >= toBeat)");
    const std::int64_t endSample = toSample(toBeat);
    const std::int64_t tailSamples = static_cast<std::int64_t>(song.tailSeconds * sr);

    if (options.trace) {
        graph.setProbe(options.trace);
        options.trace->firstBeat = fromBeat;
        options.trace->blockBeats = graph.beatsIn(startSample, kBlock, fromBeat);
        options.trace->values.clear();
        options.trace->beats.clear();
    }

    // Note events, sample accurate; offs before ons at the same sample.
    int noteId = 0;
    for (auto& node : nodes) {
        if (node.instrument) collectNoteEvents(*node.spec, tempo, startSample, endSample, false, noteId, node.events);
    }

    // Master-chain latency is removed from the output.
    int latency = 0;
    for (const auto& fx : graph.master().fx) latency += fx->latencySamples();

    MixAnalyzer analyzer;
    if (options.analysis) {
        // seconds from the first rendered sample
        auto secFrom = [&](double beat) {
            return tempo.constant() ? (beat - fromBeat) * 60.0 / song.tempo : (tempo.sampleAt(beat) - static_cast<double>(startSample)) / sr;
        };
        std::vector<SectionMarker> markers;
        for (const auto& s : song.sections) {
            const double a = std::max(s.startBeat, fromBeat), b = std::min(s.endBeat, toBeat);
            if (b > a) markers.push_back({s.name, secFrom(a), secFrom(b)});
        }
        analyzer.prepare(sr, song.tempo, markers, static_cast<double>(endSample - startSample + tailSamples) / sr);
        analyzer.setTimeGrid(tempo, meter);
        analyzer.setStartBeat(fromBeat);
        try {  // validated by parseSong; a hand-built SongSpec with bad settings is still a config error
            analyzer.setProfile(song.analysis.profile);
            if (song.analysis.loudness) analyzer.setLoudnessTarget(song.analysis.loudness->first, song.analysis.loudness->second);
        } catch (const std::invalid_argument& e) {
            throw ConfigError(std::string("$.analysis: ") + e.what());
        }
        for (auto& node : nodes) {
            // Muted nodes (incl. sidechain key "ghost" tracks) are silent by definition: not analysed.
            if (node.spec->kind != NodeSpec::Kind::Master && !node.spec->mute) {
                node.analyzerIndex = analyzer.addNode(node.spec->id, node.spec->kind == NodeSpec::Kind::Bus);
            }
        }
        analyzer.setRouting(song);  // routing + notes for the report's 'space' assessment (returns, beds, sends)
    }

    const std::string mixPath = (fs::path(options.outDir) / "mix.wav").string();
    WavWriter mix;
    mix.open(mixPath, song.sampleRate, song.bitDepth, song.seed);
    if (song.exportStems) {
        fs::create_directories(fs::path(options.outDir) / "stems");
        for (auto& node : nodes) {
            if (node.spec->kind == NodeSpec::Kind::Master) continue;
            node.stem = std::make_unique<WavWriter>();
            node.stem->open((fs::path(options.outDir) / "stems" / (node.spec->id + ".wav")).string(),
                            song.sampleRate, song.bitDepth, song.seed ^ dsp::hashString(node.spec->id.c_str()));
        }
    }

    std::vector<float> mixL(kBlock), mixR(kBlock);
    std::int64_t pos = startSample;
    std::int64_t written = 0;          // mix frames written (after latency removal)
    std::int64_t latencyToSkip = latency;
    std::int64_t silentRun = 0;
    std::int64_t flushRemaining = -1;  // after the tail ends, render `latency` more samples
    const std::int64_t hardEnd = endSample + tailSamples;
    int lastProgress = -1;

    while (true) {
        const int n = kBlock;

        // Master-chain latency: the first `latency` master output samples are dropped, so the mix
        // lines up with the (undelayed) node outputs and stems.
        int offset = 0;
        if (latencyToSkip > 0) {
            offset = static_cast<int>(std::min<std::int64_t>(latencyToSkip, n));
            latencyToSkip -= offset;
        }

        // Process nodes in dependency order. Controls (automation + modulators, block rate; modules
        // smooth internally) are updated right before each node, so followers see their key's current block.
        for (int index : graph.order()) {
            Node& node = nodes[static_cast<std::size_t>(index)];
            graph.updateControls(node, pos, n);
            float* L = node.outL.data();
            float* R = node.outR.data();
            if (node.instrument) {
                int done = 0;
                while (done < n) {
                    int segEnd = n;
                    while (node.nextEvent < node.events.size()) {
                        const NoteEvent& ev = node.events[node.nextEvent];
                        const std::int64_t at = ev.sample - pos;
                        if (at > done) { segEnd = static_cast<int>(std::min<std::int64_t>(at, n)); break; }
                        if (ev.on) node.instrument->noteOn(ev.id, ev.pitch, ev.velocity);
                        else node.instrument->noteOff(ev.id);
                        ++node.nextEvent;
                    }
                    node.instrument->process(L + done, R + done, segEnd - done);
                    done = segEnd;
                }
            } else {
                std::copy(node.inL.begin(), node.inL.end(), L);
                std::copy(node.inR.begin(), node.inR.end(), R);
                std::fill(node.inL.begin(), node.inL.end(), 0.0f);
                std::fill(node.inR.begin(), node.inR.end(), 0.0f);
            }
            for (std::size_t f = 0; f < node.fx.size(); ++f) {
                const int key = node.fxKey[f];
                const float* kL = key >= 0 ? nodes[static_cast<std::size_t>(key)].outL.data() : nullptr;
                const float* kR = key >= 0 ? nodes[static_cast<std::size_t>(key)].outR.data() : nullptr;
                node.fx[f]->process(L, R, n, kL, kR);
            }
            for (int i = 0; i < n; ++i) {
                L[i] *= node.gainL.next();
                R[i] *= node.gainR.next();
            }
            if (node.spec->kind == NodeSpec::Kind::Master) break;  // master is always last

            const bool audible = !node.spec->mute;
            if (audible) {
                Node& out = nodes[static_cast<std::size_t>(node.output)];
                for (int i = 0; i < n; ++i) { out.inL[static_cast<std::size_t>(i)] += L[i]; out.inR[static_cast<std::size_t>(i)] += R[i]; }
                for (auto& s : node.sends) {
                    Node& bus = nodes[static_cast<std::size_t>(s.target)];
                    for (int i = 0; i < n; ++i) {
                        const float g = s.gain.next();
                        bus.inL[static_cast<std::size_t>(i)] += L[i] * g;
                        bus.inR[static_cast<std::size_t>(i)] += R[i] * g;
                    }
                }
            }
            static const std::vector<float> zeros(kBlock, 0.0f);
            const float* aL = audible ? L : zeros.data();
            const float* aR = audible ? R : zeros.data();
            // Node outputs are not delayed by the master chain: unlike the master output they already
            // line up with the latency-compensated mix, so they keep every sample.
            if (node.analyzerIndex >= 0) analyzer.feedNode(node.analyzerIndex, aL, aR, n);
            if (node.stem) node.stem->write(aL, aR, n);
        }

        // Master output.
        Node& m = graph.master();
        if (offset < n) {
            std::copy(m.outL.begin() + offset, m.outL.end(), mixL.begin());
            std::copy(m.outR.begin() + offset, m.outR.end(), mixR.begin());
            const int count = n - offset;
            mix.write(mixL.data(), mixR.data(), count);
            if (options.analysis) analyzer.feedMix(mixL.data(), mixR.data(), count);
            written += count;
        }

        pos += n;
        if (!options.quiet) {
            const int pct = static_cast<int>(100.0 * static_cast<double>(pos - startSample) / static_cast<double>(std::max<std::int64_t>(1, endSample - startSample)));
            if (pct / 10 != lastProgress / 10 && pct <= 100) { std::fprintf(stderr, "render %d%%\n", pct); lastProgress = pct; }
        }

        if (flushRemaining >= 0) {
            flushRemaining -= n;
            if (flushRemaining <= 0) break;
            continue;
        }
        if (pos >= endSample) {
            float peak = 0.0f;
            for (int i = 0; i < n; ++i) peak = std::max({peak, std::fabs(m.outL[static_cast<std::size_t>(i)]), std::fabs(m.outR[static_cast<std::size_t>(i)])});
            bool allIdle = true;
            for (auto& node : nodes) if (node.instrument && !node.instrument->idle()) allIdle = false;
            silentRun = (peak < kSilence && allIdle) ? silentRun + n : 0;
            if (silentRun >= static_cast<std::int64_t>(0.25 * sr) || pos >= hardEnd) {
                flushRemaining = latency;
                if (flushRemaining <= 0) break;
            }
        }
    }

    mix.close();
    for (auto& node : nodes) if (node.stem) node.stem->close();

    RenderResult result;
    result.mixPath = mixPath;
    result.seconds = static_cast<double>(written) / sr;
    if (options.analysis) {
        json report = analyzer.finish();
        report["render"] = {{"title", song.title}, {"tempo", song.tempo}, {"sampleRate", song.sampleRate},
                            {"fromBeat", fromBeat}, {"toBeat", toBeat}, {"fromSec", static_cast<double>(startSample) / sr},
                            {"latencySamples", latency}};
        if (!song.tempoMap.empty()) {  // the song time for zoom --beat / bar numbers outside the engine
            json points = json::array();
            for (const TempoPoint& p : song.tempoMap) {
                json pt = json::array({p.beat, p.bpm});
                if (p.curve != TempoCurve::Linear) pt.push_back(p.curve == TempoCurve::Step ? "step" : "smooth");
                points.push_back(pt);
            }
            report["render"]["tempoMap"] = points;
            report["render"]["bpmRange"] = json::array({tempo.minBpm(), tempo.maxBpm()});
        }
        if (!song.meter.empty()) {
            json m = json::array();
            for (const MeterPoint& p : song.meter) m.push_back(json::array({p.beat, p.numerator, p.denominator}));
            report["render"]["meter"] = m;
        }
        result.reportPath = (fs::path(options.outDir) / "report.json").string();
        std::ofstream(result.reportPath) << formatReport(report);
        if (options.pngs) analyzer.writeImages(options.outDir);
    }
    result.renderSeconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - wallStart).count();
    return result;
}

}  // namespace as
