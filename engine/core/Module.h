#pragma once

// The two plug-in shapes of the engine. Rendering is offline, single-threaded
// and deterministic: the same render JSON and seed must give bit-identical PCM.
//
// Call order guaranteed by the host (engine/Renderer):
//   construct -> configure(params JSON) -> [setTempoMap(map)] -> prepare(ctx) -> { setParam / noteOn / noteOff / process }*
// Events (noteOn/noteOff/setParam) arrive between process() calls; the host
// splits blocks at note boundaries so notes are sample accurate, and applies
// automation every kAutomationStep samples. process() is never called with
// more than ctx.maxBlock frames.

#include "core/Params.h"

#include <cstdint>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace as {

class TempoMap;  // core/TempoMap.h

inline constexpr int kMaxBlock = 256;
inline constexpr int kAutomationStep = 32;

struct RenderContext {
    double sampleRate{48000.0};
    double bpm{120.0};           // the song tempo; with a tempo map (setTempoMap) the tempo at beat 0
    std::uint64_t seed{1};       // modules derive their own RNG streams from this + their id
    int maxBlock{kMaxBlock};
    std::string assetDir;        // absolute path of the repo's assets/ folder (DX7 banks etc.)
    double startBeat{0.0};       // song beat of the first rendered sample (non-zero for preview renders);
                                 // tempo-grid modules (synced LFOs, tempo ducker, ...) must align to
                                 // song beats, i.e. their beat position at sample n is startBeat + n*bpm/(60*sr)
                                 // (with a tempo map: TempoMap::beatAtSample(songStartSample(...) + n))
};

class Instrument {
public:
    virtual ~Instrument() = default;

    // Strict: throws ConfigError on anything invalid. Called once, before prepare().
    virtual void configure(const json& params) = 0;
    // Tempo map (docs/RENDER_FORMAT.md "Tempo map"): called once, after configure() and before prepare(),
    // only for songs whose tempo changes (a constant tempo never calls it). The map outlives the module.
    // Tempo-synced modules follow it (beat grids, synced rates and delay times) and take the song position
    // of RenderContext::startBeat from songStartSample(); the default ignores it.
    virtual void setTempoMap(const TempoMap& map) { (void)map; }
    virtual void prepare(const RenderContext& ctx) = 0;

    // Automation. Returns false if the name is unknown / not automatable.
    virtual bool setParam(std::string_view name, float value) = 0;

    // noteId is unique per note for the whole render. velocity is 0..1 (MIDI vel / 127).
    virtual void noteOn(int noteId, int pitch, float velocity) = 0;
    virtual void noteOff(int noteId) = 0;

    // OVERWRITES left/right[0..frames). Must stay finite; no allocation after prepare().
    virtual void process(float* left, float* right, int frames) = 0;

    // True when no voice can produce sound any more (lets the host stop early at the tail).
    virtual bool idle() const = 0;

    virtual const std::vector<ParamSpec>& paramSpecs() const = 0;
};

class Effect {
public:
    virtual ~Effect() = default;

    virtual void configure(const json& params) = 0;
    virtual void setTempoMap(const TempoMap& map) { (void)map; }  // as Instrument::setTempoMap
    virtual void prepare(const RenderContext& ctx) = 0;
    virtual bool setParam(std::string_view name, float value) = 0;

    // In place. scLeft/scRight are the sidechain key signal for this block when the
    // effect was given a "sidechain" source in the render JSON, else nullptr.
    virtual void process(float* left, float* right, int frames,
                         const float* scLeft, const float* scRight) = 0;

    // Seconds the effect keeps ringing after silent input (reverb/delay tails).
    virtual double tailSeconds() const { return 0.0; }
    // Fixed processing delay in samples (only the master limiter should use this;
    // the host compensates latency on the master chain only).
    virtual int latencySamples() const { return 0; }

    virtual const std::vector<ParamSpec>& paramSpecs() const = 0;
};

}  // namespace as
