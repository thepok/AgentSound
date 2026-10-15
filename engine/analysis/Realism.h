#pragma once

// Realism probes of a played part (docs/SAMPLE_REALISM_PLAN.md section 1): does a sampled instrument sound played or
// triggered? Measured per track from its notes (the render JSON) on its own audio, while it renders: short windows
// around the notes are captured (only what a probe needs), turned into features when complete and dropped.
//
//   repeatSim      same key repeated (velocity within +-6, the earlier note at most 1 s before): how alike the first
//                  80 ms of the two notes are. sim = correlation of their spectro-temporal envelopes (1/3-octave bands
//                  x 10 ms frames, dB, 60 dB floor under the loudest cell); wave = the waveforms' correlation (best lag
//                  within +-1 ms). 1.0 = a machine gun (the same recording again); a real round-robin pack reads lower.
//   layerStep      a key played at 8+ different velocities (the audition 'sweep' probe): neighbouring velocities' steps
//                  in level (dB) and brightness (energy share above 2.5 kHz, dB) - the largest vs the median: velocity
//                  layer boundaries show as single big steps.
//   sustainFlux    notes held 0.8 s+ with no other onset in the track: from 150 ms after the onset, 10 ms frames, a
//                  300 ms moving average removed: the standard deviation of the level (dB) and of the spectral centroid
//                  (cents), and the strongest autocorrelation peak of the two (lag 50 ms .. 1 s): a looped sustain repeats
//                  (periodicity near 1 at the loop period), a live one does not.
//   tailDecay      notes ringing 2.6 s+ without a new onset in the track: the decay slope 0.1-0.6 s after the onset vs
//                  0.6-2.6 s (dB/s; a piano's two-stage decay: fast, then slow).
//   transitionDip  monophonic legato transitions (a note starting while the previous one sounds): the deepest level dip
//                  around the new onset (-10 .. +150 ms vs the 40 ms before, dB) and how long until the new pitch
//                  dominates (normalised autocorrelation at the new vs the old period, ms; octave steps skipped).
// Capture caps keep the memory small on long songs (pairs, held notes, transitions are sampled evenly).

#include "core/Params.h"  // json

#include <cstdint>
#include <memory>
#include <vector>

namespace as::analysis {

class OnsetEnvelope;

struct ProbeNote {
    std::int64_t on{0}, off{0};   // samples from the first fed sample
    int pitch{60}, velocity{100};
};

class RealismProbe {
public:
    RealismProbe(double sampleRate, std::vector<ProbeNote> notes);
    ~RealismProbe();
    void feed(const float* left, const float* right, int frames);   // the node's output, in order
    void finish();                                                   // completes captures cut by the end
    // The probes that measured something ({} when none). env: the node's 2.5 ms envelope (tailDecay).
    json report(const OnsetEnvelope* env) const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace as::analysis
