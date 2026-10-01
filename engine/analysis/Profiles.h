#pragma once

// Analysis profiles: the genre-specific targets the report measures a mix against. A profile sets
// the reference long-term spectrum (band balance, 1/3-octave curve, tilt), the integrated loudness
// window and every style-dependent warning threshold (band balance limits, dull top, tilt tolerance,
// peak-to-loudness ratio, loudness range) and the space targets. Selected by the render JSON key "analysis":
// {"profile": "synthwave"} (docs/RENDER_FORMAT.md); "default" is the generic pop/synthwave master reference
// the report always used. Genres: synthwave, dreamwave, darksynth, jazz, classical, piano (solo piano), pop,
// rock, film (how each was derived: Profiles.cpp).
//
// The reference spectrum of every profile is the default curve (referencePsdDb in MixImpl.h) plus a
// per-profile offset curve in dB, given as (Hz, dB) breakpoints interpolated linearly over log2(f)
// and held beyond the first/last point. Warnings compare the mix's band levels vs that reference
// (median-aligned, see balanceVsReference) with the profile's per-band limits.

#include "analysis/StreamStats.h"  // kNumBands

#include <array>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace as::analysis {

struct AnalysisProfile {
    std::string name;
    std::string description;  // one line: the style and what its reference expects
    std::vector<std::pair<double, double>> psdOffsetDb;  // (Hz, dB) added to the default curve
    double lufsMin{-12.0}, lufsMax{-9.0};                 // integrated loudness target
    // Band balance limits (dB vs the reference, median-aligned): a band above bandHighDb / below
    // bandLowDb is flagged (balance_<band>_high / _low); nullopt = that direction is not checked.
    std::array<std::optional<double>, kNumBands> bandHighDb{};
    std::array<std::optional<double>, kNumBands> bandLowDb{};
    double dullDb{-6.0};                 // top end (6-20 kHz) below the reference by more -> "dull"
    double tiltToleranceDbPerOct{1.5};   // |tilt - reference tilt| above this -> "tilt"
    double plrMinDb{6.0};                // true peak - LUFS-I below this -> "squashed"
    double lraMinLu{3.0}, lraMaxLu{15.0};  // loudness range outside -> "lra_low" / "lra_high" (songs > 30 s)

    // Space targets (report "space", Space.h), judged in the full sections (within 4 LU of the loudest).
    double widthMinPct{30.0}, widthMaxPct{100.0};  // mix width above 150 Hz (side/mid %): below min -> "narrow_mix", above max not "lush"
    double wetMinLu{-18.0}, wetMaxLu{-7.0};       // reverb returns vs the mix (LU): below min -> "dry_mix"; min..max = lush
    double washyLu{-4.0};                         // reverb returns louder than this vs the mix -> "washy"
    double echoMinLu{-28.0};                      // a delay (echo) return quieter than this -> "reverb_inaudible"
    double tailMinDb{-34.0};                      // returns 0.3-0.8 s after the music stops, vs the music: below -> tails inaudible
    double returnLowMaxPct{30.0};                 // reverb-return energy below 150 Hz above this share -> low-end wash ("washy")
    std::optional<double> bedBelowLeadMaxDb;      // bed more than this under the lead -> "thin_bed" (nullopt: not checked)

    // Note dynamics (NoteDynamics.h): a melodic lead whose note levels (10-90 % spread per 8-bar phrase, median over
    // the phrases with 8+ notes) stay under this -> "flat_dynamics" (warn; other melodic parts: info).
    double noteSpreadMinDb{3.0};
    bool judgeBassDynamics{false};  // bass lines judged too (info): a walking / continuo bass is played, a synth bass pulse is not

    // Reference long-term spectrum in dB per Hz (arbitrary common offset).
    double psdDb(double hz) const noexcept;
    // Reference energy between f0 and f1 (same arbitrary scale for every band of this profile).
    double energy(double f0, double f1) const noexcept;
    // Reference energy share per band (sums to 1).
    std::array<double, kNumBands> bandShares() const;
};

// Every profile, "default" first.
const std::vector<AnalysisProfile>& analysisProfiles();
// nullptr for an unknown name.
const AnalysisProfile* findAnalysisProfile(const std::string& name);
const AnalysisProfile& defaultAnalysisProfile();
// "default, synthwave, dreamwave, darksynth, jazz, classical, piano, pop, rock, film" (for error messages).
std::string analysisProfileNames();

}  // namespace as::analysis
