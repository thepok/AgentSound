#pragma once

// vocoder: the 80s robot voice (Kraftwerk, Daft Punk, The Midnight, Zapp's talkbox) without a singer.
//
// The effect's own input is the CARRIER (supersaw chords, a pad, a saw lead: it gives the pitch, the
// notes and the timbre); the "sidechain" is the MODULATOR (a speech track, a choir, drums: it gives the
// words / the rhythm). A vocoder without a sidechain is a config error (effectRequiresSidechain()).
//   mode classic  analog channel vocoder: 8-40 log-spaced analysis bands (complex gammatone filters,
//                 ripple-free envelopes) drive the same bands of the carrier (4th-order band-passes);
//                 formant shift, unvoiced noise + sibilance for consonants, band stereo spread, hold.
//   mode lpc      talkbox: the modulator's vocal-tract resonances (causal, frequency-warped running LPC,
//                 exact exponentially windowed autocorrelation) filter the carrier - smoother and clearly
//                 more intelligible; formant shift by re-warping the synthesis filter.
// Zero latency (causal filters only), deterministic (noise is a hash of the song sample position, so
// preview renders match full renders), allocation-free after prepare().

#include "core/Module.h"

#include <memory>

namespace as {

std::unique_ptr<Effect> makeVocoder();

}  // namespace as
