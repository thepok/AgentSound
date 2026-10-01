#include "analysis/Profiles.h"

#include "analysis/MixImpl.h"  // referencePsdDb (the default curve)

#include <algorithm>
#include <cmath>

namespace as::analysis {

// How the genre references were derived
// -------------------------------------
// 1. Measurements. Four reference-style songs built only from the sound library (calibrated
//    -18 LUFS patches, kick-keyed sidechain on bass/pads/arps, master/synthwave chain): outrun
//    (drums_outrun kick at 55 Hz, octave_bass 8ths, warm_pad, arp_pluck, supersaw hook, 110 BPM),
//    retrowave pop (drums_909 at 46 Hz, pluck_bass + sub_bass, juno_pad, poly_stab, pulse_lead,
//    118 BPM), dreamwave (drums_808 half-time, moog_bass whole notes, dream_pad, epiano, soft_lead,
//    88 BPM) and darksynth (drums_dark at 41 Hz, dark_bass 16ths, dark_pad, seq_pulse, sync_lead,
//    124 BPM). Against the default reference their 1/3-octave spectra (mean-aligned) read, as the
//    average of the three driving songs: 31.5-50 Hz +5..+9 dB, 63-80 Hz +2..+3, 100-250 Hz -1..-3,
//    315-630 Hz ~0, 0.8-1.25 kHz +1.5..+3, 2.5-5 kHz -2.5..-3.5, 8-10 kHz +0.5..+1.5, 16 kHz -5;
//    band balance sub +6..+10 dB (sub share 35-53 % vs 11 %), presence -1.4..-4.9. The dreamwave
//    song: sub +6.5, low mids +3.3, presence -5, brilliance -4.7, air -14.
// 2. Published genre knowledge. Club / four-on-the-floor masters (the EDM and hip-hop targets of
//    tonal-balance tools, long-term average spectra of dance masters) peak at the kick fundamental
//    (45-60 Hz) and are close to equal energy per octave from ~35 Hz to ~150 Hz, i.e. several dB more
//    sub than rock/pop, whose long-term spectrum is flat only down to ~100 Hz; above that all modern
//    masters fall at roughly -4.5 dB/oct (per Hz). Synthwave production practice (recipes/synthwave.md):
//    kick + bass own 40-120 Hz, controlled 3-5 kHz (no harsh supersaw build-up), sparkly 8-12 kHz from
//    hats, reverbs and air shelves. Dreamwave / chillsynth: softer, warmer, rounded leads, rolled-off
//    top, quieter masters (-14..-10 LUFS). Darksynth: distorted bass and pads fill 150-700 Hz, sub
//    from low-tuned kicks (41-46 Hz), loud masters (-10..-7 LUFS).
// The offsets below take the measured shape where it agrees with (2) (sub/bass region, 2.5-5 kHz),
// smoothed into one broad 31-80 Hz bump (kicks are tuned anywhere from 41 to 55 Hz) and somewhat
// smaller than measured (library mixes are not ground truth), and (2) alone where the library is
// idiosyncratic (the dark 16 kHz roll-off of the library patches and the 1 kHz lead bumps are not
// written into the references). Result (band shares; default: sub 11 %, bass 45 %):
// synthwave sub 31 % / bass 37 %, i.e. sub and bass carry equal energy per octave. With it the
// driving test songs read sub 0..+4.6 dB (no 'sub high'), while a mix with a genuinely boomy sub
// (> +5 dB on top of the genre's own sub) is still flagged.
// Cross-check (review): the composed song songs/midnight-interstate (112 BPM outrun, not used for the
// derivation) reads sub +4.0 / -1.9 dB and no balance warning under default / synthwave; the four
// reference songs read sub 0 (outrun), +4.0 (retrowave pop), +1.2 (dreamwave) and +4.6 (darksynth,
// +3.9 under its own profile) under synthwave, so the +5 limit keeps ~1 dB of headroom for heavy
// but normal 41-46 Hz kicks.
//
// How the space targets were set (Space.h; values measured over the full sections)
// -----------------------------------------------------------------------------------
// The first composed songs sounded "pale, thin, narrow, not like big reverbs". Re-analysed with the
// routing (returns vs the pre-master sum, width above 150 Hz): midnight-interstate 29.5 % / -16.5 LU /
// bed -7.6 dB in chorus1, chrome-leviathan (darksynth) 21.6 % / -17.2 LU, children-of-neon 30.9 % /
// -10.7 LU, orbital-station 32.9 % / -11.1 LU, skyline-heartbeat 39.9 % / -13.6 LU / bed -8.8 dB in the
// verses, polaroid-summer (dreamwave) 31.9 % / -12.0 LU. The whole-mix width of all of them is 12-24 %:
// the mono kick and bass dominate that number, so it is reported but not judged. A deliberately lush
// variant of midnight-interstate (pads/strings/choir: Juno chorus mix 1.0 + width 1.2, +3 dB; keys/arps
// panned with chorus; hall sends +8 dB, hall width 1.3) reads 84.5 % / -6.8 LU / bed -0.9 dB (verdict
// lush, no warning - but its fully wet chorus + width leaves pads/strings/choir at correlation -0.17..-0.20,
// so since the review it is flagged over_wide (verdict ok); the same variant with the classic Juno balance,
// chorus mix 0.5 + width 1.4 and hall width 1.15, reads 64.3 % / -7.3 LU / -0.8 dB, pads at +0.2: lush, no
// warning); the already reworked afterglow-express 52.5 % / -8.0 LU / +1.3 dB (lush); an over-wet
// variant (hall sends +16 dB, hall +4 dB, full-range hall) -2.1 LU (washy). Hence synthwave: width 40..100 %
// above 150 Hz (100 % = side as loud as mid), reverb -14..-6 LU (washy above -4), bed within 6 dB of the
// lead; dreamwave wetter and wider, darksynth drier and narrower, default looser. Note: comparing a
// return's nodes[].lufs with the final lufsIntegrated reads 4-8 LU drier than this, because the master
// limiter's gain lifts only the mix (these songs used +3.4..+8 dB).
//
// How the jazz / classical / pop / rock / film references were derived
// --------------------------------------------------------------------
// 1. Published measurements of commercial recordings.
//    - Pestana, Ma, Reiss, Barbosa, Black (2013), "Spectral characteristics of popular commercial recordings
//      1950-2010", AES 135th Convention, paper 8960 (772 records): a ~5 dB/oct decay (per Hz) from 100 Hz to
//      4 kHz in every genre; hip-hop, rock, pop and electronic music are louder below 150 Hz and above 5 kHz
//      than jazz and folk, which are relatively louder in the mids; jazz has the lowest bass of all genres
//      and a decaying top; 50 Hz is the spectral maximum of most genres, only hip-hop has much at 30 Hz.
//    - Elowsson, Friberg (2017), "Long-term average spectrum in popular music and its relation to the level
//      of the percussion", AES 142nd Convention, paper 9762 (12,345 tracks): the per-Hz slope steepens from
//      -2.4 dB/oct at 200 Hz to -8.9 at 6.4 kHz; the genre differences are mainly a side effect of how loud
//      the percussion is: more drums = relatively more below ~100 Hz and above ~2-4.5 kHz, while the slope
//      from 89 Hz to 4.5 kHz stays 4.5 dB/oct whatever the percussion (so genre offsets live in the low end
//      and the top, the mids only move relatively); songs without a bass instrument sit up to ~10 dB under
//      the mean below 100 Hz (so a missing sub is rarely a fault outside pop / club music).
//    - Tonal-balance targets of mastering tools (iZotope's 'Orchestral' vs 'Modern' vs 'Bass Heavy' curves,
//      built from thousands of commercial masters): orchestral masters carry markedly less sub and less
//      top than modern pop/rock; bass-heavy (EDM / hip-hop) more sub.
//    - Loudness practice (EBU R 128 / Tech 3343 LRA; streaming normalisation -14 (Spotify) / -16 LUFS (Apple)):
//      pop and rock masters have LRA ~5-7 LU (EDM ~4), jazz more and classical the most (often 15-20+ LU);
//      jazz / classical releases sit at -18..-14 LUFS and quieter (orchestral -20 and below, purist -23),
//      modern pop -11..-7, rock -10..-6 (loud rock/metal even louder), soundtrack albums -16..-10.
// 2. Instruments and arrangement (recipes/jazz-trio.md, classical.md, pop.md, rock.md): the upright bass
//    radiates little below ~60 Hz and walks mostly A1-D3, the jazz kick is feathered and brushes / ride carry
//    the top softly; an orchestra's energy sits at 200 Hz-2 kHz (strings, horns, winds), basses and timpani
//    below, and distance darkens the hall top (air absorption, ISO 9613-1 at 20 C / 50 % RH: about 0.1 dB/m
//    at 8 kHz and several times that at 16 kHz, i.e. a few dB over 15 m of direct path and far more in the
//    reverberant field); pop puts an 808 / four-on-the-floor kick and a sub bass at 40-60 Hz, keeps 250-500 Hz
//    clean and adds air shelves; rock kicks are tuned to 60-100 Hz (bass guitar high-passed ~35 Hz),
//    double-tracked guitars fill 200 Hz-5 kHz and cymbals the top; film scores add low hits / braams / synth
//    sub under an orchestra in a big hall.
// 3. Calibration renders (engine; not ground truth): a medium-swing quartet (GeneralUser GS piano, acoustic
//    bass, brush kit, tenor sax; room 1.2 s, sends -10..-22 dB) reads reverb -11.9 LU, tails -34 dB, width 12 %
//    above 150 Hz; an orchestral mockup from the Sonatina Symphonic Orchestra SF2 set (15 sections panned by
//    seating, hall 2.1 s, sends -6..-1 dB, pp -> ff; recipes/classical.md) reads LRA 13.6 LU, reverb -6.6 LU,
//    tails -22 dB, width 55 % above 150 Hz, low end correlation 0.81 once cellos / basses / tuba are narrowed
//    (sample width 0.3-0.4) and the hall is high-passed at 110 Hz (0.27 with full-width stereo sections and an
//    80 Hz low cut: low_end_not_mono); a GM orchestral mockup LRA 15.6, reverb -6 LU, tails -18 dB; a rock
//    mockup (drum room -10, plate, hard-panned guitars) reverb -16 LU. Their spectra are far darker above 4 kHz
//    than real records (SSO / GM samples: 6-20 kHz 7-11 dB under even this darker classical reference), so
//    they set the space targets and the tolerances, never the reference curves.
// The offsets below (vs the default curve) read, median-aligned per band (default = 0): jazz sub -3.0 / bass
// +1.3 / lowmid +2.6 / mid +1.8 / brilliance -1.4 / air -3.7 (sub share 4 %, tilt -5.0 dB/oct vs -4.5);
// classical sub -3.6, bass +1.1, lowmid +2.9, mid +2.6, brilliance -4.2, air -8.4 (sub 3.6 %, tilt -5.3); pop
// sub +2.0, lowmid -1.3, brilliance +1.0, air +1.2 (sub 18 %, tilt -4.2); rock sub -2.0, lowmid +1.1, mid +1.3,
// air -1.7 (sub 6.5 %); film sub +2.1, bass +1.0, brilliance -1.8, air -3.0 (sub 15 %, tilt -4.9).
// Cross-check: a synthwave-shaped mix reads sub +9.6 under jazz, +10 under classical, +7.3 under rock
// (flagged); a pop-shaped one sub +4.4 under rock (flagged at +4), brilliance +5.2 / air +9.5 under classical
// (sizzly for an orchestra) and sub -2.0 under default. The limits are ~4 dB around the genre's own balance
// where a deviation is a mix fault in that genre (harsh strings: classical presence +3; mud: pop lowmid +3),
// looser where the style varies (organ pedals or bass drum: classical sub +7; solo piano's dark top:
// classical dull -8), unchecked where the style does not need the band (no sub demand in jazz / classical).
// The analyser's band split lets some 60-80 Hz leak into the sub band (a sub cut by 12 dB reads about -8), so
// the 'sub low' limits of pop (-5), film (-6) and rock (-8) mean a true deficit of roughly 7, 9 and 14 dB.
// Space targets: jazz is a close, small room (reverb 10-20 LU under the mix; a 0.8-1.4 s room 12-18 LU under
// leaves tails of -38..-51 dB at a stop; width from the stereo piano and drums: 15 % and up); classical and
// film live in a hall (reverb 4-14 / 3-13 LU under the mix, washy only when the reverb is ~2 dB louder than
// the direct sound, the low end in the hall is part of the warmth: 50 % / 45 % below 150 Hz allowed, tails
// above -30 dB = a hall that rings); pop is wide and polished (35 % and up, reverb 7-16 LU under), rock drier
// and a little narrower (reverb 9-20 LU under, drum-room tails). The thin-bed check stays off for all five
// (pads are not a genre requirement there).
// Verification (tests/test_analysis.cpp, testGenreProfiles): a genre-shaped mix per profile (a multisine with
// the reference spectrum, bass part mono, ensemble stereo, sections at genre-typical levels, a reverb return,
// a soft-clipped master for the loud genres) reads every band within 1.5 dB and raises no profile warning
// under its own profile (jazz -14.5 LUFS / LRA 7 / PLR 11; classical -19.5 / 17 / 14; pop -10 / 6 / 8; rock
// -8.5 / 5 / 7; film -13 / 12 / 11), while clearly wrong mixes (a synthwave low end in jazz or rock, jazz
// mastered like pop, a flattened -11 LUFS classical master, steely strings, a dry hall, pop without lows and
// top, scooped rock mids, a washed-out film score, ...) are flagged.

namespace {

std::vector<AnalysisProfile> makeProfiles() {
    std::vector<AnalysisProfile> v;
    using Lim = std::optional<double>;
    const Lim none;

    AnalysisProfile d;
    d.name = "default";
    d.description = "generic modern pop / synthwave master: flat 40-100 Hz, -4.5 dB/oct above, -12..-9 LUFS";
    d.lufsMin = -12.0;
    d.lufsMax = -9.0;
    d.bandHighDb = {Lim(5.0), Lim(4.0), Lim(4.0), Lim(4.0), Lim(4.0), Lim(5.0), Lim(7.0)};
    d.bandLowDb = {Lim(-9.0), Lim(-6.0), none, none, Lim(-7.0), none, none};
    v.push_back(d);

    AnalysisProfile s = d;
    s.name = "synthwave";
    s.description = "outrun / retrowave: four-on-the-floor kick at 41-55 Hz + bass own the sub (equal energy per octave "
                    "35-150 Hz), controlled 2.5-5 kHz, bright 8-12 kHz, -12..-9 LUFS";
    s.psdOffsetDb = {{25, -2.0},   {31.5, 4.0},  {40, 6.0},    {50, 7.0},   {63, 4.5},   {80, 1.5},
                     {100, 0.0},   {125, -1.0},  {200, -1.0},  {250, -1.0}, {315, 0.0},  {630, 0.0},
                     {1000, 1.0},  {1600, 0.0},  {2000, -1.0}, {2500, -2.0}, {5000, -2.0}, {6300, -0.5},
                     {8000, 1.0},  {10000, 1.5}, {12500, 0.5}, {16000, 0.0}};
    s.bandLowDb[0] = -6.0;  // a synthwave mix 6 dB under the genre's sub lacks its kick/bass foundation
    s.widthMinPct = 40.0;
    s.widthMaxPct = 100.0;
    s.wetMinLu = -14.0;
    s.wetMaxLu = -6.0;
    s.washyLu = -4.0;
    s.echoMinLu = -24.0;
    s.tailMinDb = -30.0;
    s.bedBelowLeadMaxDb = 6.0;
    v.push_back(s);

    AnalysisProfile w = d;
    w.name = "dreamwave";
    w.description = "dreamwave / chillsynth: round 808 sub, warm low mids, soft presence, rolled-off top, -14..-10 LUFS";
    w.psdOffsetDb = {{25, -2.0},   {31.5, 3.0},  {40, 5.0},    {50, 6.0},    {63, 4.0},    {80, 1.5},
                     {100, 0.5},   {160, 0.5},   {250, 1.0},   {400, 1.5},   {630, 1.5},   {1000, 1.0},
                     {1600, 0.0},  {2000, -1.5}, {2500, -3.0}, {5000, -3.5}, {6300, -3.0}, {8000, -2.5},
                     {12500, -4.0}, {16000, -6.0}};
    w.lufsMin = -14.0;
    w.lufsMax = -10.0;
    w.bandHighDb[4] = 3.0;   // presence peaks stick out more in a soft mix
    w.bandHighDb[5] = 4.0;
    w.bandHighDb[6] = 6.0;
    w.bandLowDb[0] = -8.0;
    w.bandLowDb[4] = -9.0;   // recessed presence is the style
    w.dullDb = -7.0;
    w.plrMinDb = 7.0;        // softer masters keep their transients
    w.lraMaxLu = 16.0;
    w.widthMinPct = 45.0;
    w.widthMaxPct = 110.0;
    w.wetMinLu = -11.0;
    w.wetMaxLu = -5.0;
    w.washyLu = -3.0;
    w.echoMinLu = -24.0;
    w.tailMinDb = -28.0;
    w.bedBelowLeadMaxDb = 5.0;
    v.push_back(w);

    AnalysisProfile k = d;
    k.name = "darksynth";
    k.description = "darksynth: low-tuned distorted kick, dense driven low mids (150-700 Hz), hard top, -10..-7 LUFS";
    k.psdOffsetDb = {{25, -1.0},   {31.5, 5.0},  {40, 7.0},    {50, 7.5},    {63, 5.0},    {80, 2.5},
                     {100, 1.5},   {160, 1.0},   {250, 1.5},   {400, 2.5},   {630, 2.0},   {1000, 1.0},
                     {1600, 0.0},  {2000, -1.0}, {2500, -2.5}, {5000, -2.5}, {6300, -1.0}, {8000, 0.0},
                     {10000, 0.5}, {12500, -0.5}, {16000, -2.0}};
    k.lufsMin = -10.0;
    k.lufsMax = -7.0;
    k.bandHighDb[2] = 5.0;   // dense low mids are the style
    k.bandLowDb[0] = -6.0;
    k.plrMinDb = 5.0;        // loud masters: PLR 6-8 dB is normal at -8 LUFS / -1 dBTP
    k.lraMinLu = 2.5;
    k.lraMaxLu = 14.0;
    k.widthMinPct = 30.0;
    k.widthMaxPct = 90.0;
    k.wetMinLu = -16.0;
    k.wetMaxLu = -8.0;
    k.washyLu = -5.0;
    k.echoMinLu = -26.0;
    k.tailMinDb = -32.0;
    v.push_back(k);

    AnalysisProfile j = d;
    j.name = "jazz";
    j.description = "small-group acoustic jazz (piano trio / quartet in a club room): upright bass without a sub kick, warm "
                    "mids, soft cymbal top, -16..-13 LUFS, LRA 5-14";
    j.psdOffsetDb = {{25, -12.0},  {31.5, -10.0}, {40, -6.0},   {50, -3.0},   {63, -1.5},   {80, -0.5},
                     {100, 0.0},   {160, 0.5},    {250, 1.0},   {315, 1.5},   {630, 1.5},   {1000, 1.0},
                     {1600, 0.5},  {2000, 0.0},   {2500, -0.5}, {3150, -1.0}, {5000, -1.5}, {6300, -2.0},
                     {8000, -2.5}, {10000, -3.0}, {12500, -4.0}, {16000, -5.5}};
    j.lufsMin = -16.0;
    j.lufsMax = -13.0;
    j.bandHighDb[5] = 4.0;   // a sizzling ride / brush top sticks out in a warm mix
    j.bandHighDb[6] = 6.0;
    j.bandLowDb = {none, Lim(-7.0), none, Lim(-6.0), Lim(-8.0), none, none};  // no sub demand; the walking bass must be heard
    j.dullDb = -7.0;
    j.plrMinDb = 9.0;        // light limiting only (-14 LUFS at -1 dBTP = PLR 13)
    j.lraMinLu = 5.0;
    j.lraMaxLu = 14.0;
    j.widthMinPct = 15.0;    // stereo piano + drum overheads around a centred bass
    j.widthMaxPct = 80.0;
    j.wetMinLu = -20.0;      // one short room 12-18 LU under the mix
    j.wetMaxLu = -10.0;
    j.washyLu = -6.0;
    j.echoMinLu = -28.0;
    j.tailMinDb = -52.0;     // a 0.8-1.4 s room 12-18 LU under the mix dies fast: -38..-51 dB is normal
    j.noteSpreadMinDb = 4.0; // a played piano / horn line breathes more than a synth lead: accents, ghosted passing notes
    j.judgeBassDynamics = true;  // the walking bass is played: accents, ghost notes
    v.push_back(j);

    AnalysisProfile c = d;
    c.name = "classical";
    c.description = "orchestral / chamber music in a concert hall: little sub, full mids, dark natural top, very dynamic "
                    "(-23..-16 LUFS, LRA 4-22), unlimited peaks (PLR >= 12)";
    c.psdOffsetDb = {{25, -12.0},  {31.5, -9.0},  {40, -6.5},   {50, -4.5},   {63, -3.0},   {80, -1.5},
                     {100, -1.0},  {125, -0.5},   {160, 0.0},   {250, 0.5},   {315, 1.0},   {630, 1.5},
                     {1000, 1.5},  {1250, 1.0},   {1600, 0.5},  {2000, 0.0},  {2500, -0.5}, {3150, -1.0},
                     {4000, -2.0}, {5000, -3.0},  {6300, -4.5}, {8000, -6.0}, {10000, -7.5}, {12500, -9.0},
                     {16000, -11.0}};
    c.lufsMin = -23.0;
    c.lufsMax = -16.0;
    // Organ pedals and the bass drum may add sub, full mids are the music; steely / harsh strings are the
    // classic fault (presence +3). No sub demand; the mids and the bass line must be there.
    c.bandHighDb = {Lim(7.0), Lim(4.0), Lim(5.0), Lim(5.0), Lim(3.0), Lim(4.0), Lim(5.0)};
    c.bandLowDb = {none, Lim(-8.0), none, Lim(-6.0), Lim(-9.0), none, none};
    c.dullDb = -8.0;         // a solo piano or a distant hall is darker still
    c.tiltToleranceDbPerOct = 2.0;  // string quartet vs organ vs full orchestra
    c.plrMinDb = 12.0;       // no limiter-ish crest: -20 LUFS at -1..-3 dBTP = PLR 17-19
    c.lraMinLu = 4.0;
    c.lraMaxLu = 22.0;
    c.widthMinPct = 15.0;    // seating panning + hall; solo / chamber recordings are narrower
    c.widthMaxPct = 110.0;
    c.wetMinLu = -14.0;      // the hall is part of the sound
    c.wetMaxLu = -4.0;
    c.washyLu = -2.0;        // reverb ~2 dB louder than the direct sound: distant, blurred
    c.echoMinLu = -28.0;
    c.tailMinDb = -30.0;     // a 1.8-2.5 s hall rings audibly after a cut-off (-19..-29 dB)
    c.returnLowMaxPct = 50.0;  // cellos, basses and timpani in the hall are its warmth
    c.noteSpreadMinDb = 4.5;   // phrasing is the music: hairpins, accents, soft upbeats
    c.judgeBassDynamics = true;  // cellos / basses phrase like every other section
    v.push_back(c);

    // Solo piano (the classical profile's thresholds, the piano's own balance). Derived from two commercial solo
    // piano recordings measured by the analyser under 'classical' (songs/gymnopedie-etude/NOTES.md): Satie,
    // Gymnopedie No. 1 (bands vs the classical reference: bass +7.5, low mids +14.4, mid +5.1, presence -6.7,
    // brilliance -18) and Chopin, Nocturne op. 9 no. 2 (bass 0, low mids +12.8, mid +11.2, presence +1.2,
    // brilliance -15.5): both raised three balance warnings under 'classical', which is an orchestra's curve. A
    // piano alone has no double basses, no timpani, no cymbals: its long-term spectrum is the middle register's
    // fundamentals (a broad hump of +15..+18 dB at 315-800 Hz against the default curve), a thin bottom octave
    // and a top that falls fast above 2.5 kHz (hammer noise and the partials of the upper octaves only). The curve
    // below is the mean of the two, smoothed over 1/3 octaves, the 5-16 kHz roll-off eased by 3-7 dB (both
    // references were lossy web encodes that cut the top). Under this curve the two recordings read bass +8.3 / -1.0,
    // sub +9.7 (room rumble) / -11.3, low mids +4.6 / +1.1, presence -0.7 / +5.5 dB: a close, bright nocturne and a
    // warm, distant hall recording are both solo piano, so the high limits sit ~1 dB outside them (bass +9.5, sub +11,
    // presence +6.5) and still catch a boomy (+10 dB) or glassy (+8 dB presence) piano. The top is not demanded (dull
    // at -10).
    AnalysisProfile pn = c;
    pn.name = "piano";
    pn.description = "solo piano (recital, nocturne, ballad or film piano alone): the middle register's hump at 250 Hz-2 kHz, "
                     "a thin bottom and a falling top, in a hall; classical loudness and dynamics (-23..-16 LUFS, LRA 4-22)";
    pn.psdOffsetDb = {{25, -12.0},  {40, -12.0},  {63, -8.0},   {80, -4.0},   {100, -3.0},   {125, -1.0},
                      {160, 4.0},   {200, 7.5},   {250, 9.5},   {315, 13.0},  {400, 16.0},   {500, 17.5},
                      {630, 17.5},  {800, 15.5},  {1000, 12.5}, {1250, 10.5}, {1600, 8.5},   {2000, 6.0},
                      {2500, 2.0},  {3150, -2.0}, {4000, -6.5}, {5000, -11.5}, {6300, -16.0}, {8000, -19.5},
                      {10000, -22.0}, {12500, -24.0}, {16000, -27.0}};
    pn.bandHighDb = {Lim(11.0), Lim(9.5), Lim(6.0), Lim(6.0), Lim(6.5), Lim(7.0), Lim(9.0)};
    pn.bandLowDb = {none, Lim(-8.0), Lim(-6.0), Lim(-6.0), Lim(-9.0), none, none};
    pn.dullDb = -10.0;
    pn.tiltToleranceDbPerOct = 2.5;  // a close studio grand vs a distant hall recording
    pn.widthMinPct = 12.0;           // a piano recorded from the hall reads 19-36 % above 150 Hz
    v.push_back(pn);

    AnalysisProfile p = d;
    p.name = "pop";
    p.description = "modern pop / dance-pop: strong 40-60 Hz kick and bass, clean low mids, bright controlled top, wide, "
                    "-11..-8 LUFS";
    p.psdOffsetDb = {{25, -1.0},   {31.5, 1.5},  {40, 2.5},    {50, 3.0},    {63, 2.5},    {80, 1.0},
                     {100, 0.0},   {125, -0.5},  {200, -1.0},  {400, -1.0},  {630, -0.5},  {800, 0.0},
                     {2000, 0.0},  {2500, 0.5},  {5000, 0.5},  {6300, 1.0},  {8000, 1.5},  {10000, 2.0},
                     {12500, 2.0}, {16000, 1.5}};
    p.lufsMin = -11.0;
    p.lufsMax = -8.0;
    p.bandHighDb = {Lim(4.0), Lim(4.0), Lim(3.0), Lim(4.0), Lim(3.0), Lim(4.0), Lim(6.0)};  // mud and harshness early
    p.bandLowDb = {Lim(-5.0), Lim(-6.0), none, none, Lim(-6.0), none, none};  // the low end and the lead's edge are the style
    p.dullDb = -4.5;
    p.plrMinDb = 6.0;
    p.lraMinLu = 3.0;
    p.lraMaxLu = 12.0;
    p.widthMinPct = 35.0;
    p.widthMaxPct = 100.0;
    p.wetMinLu = -16.0;
    p.wetMaxLu = -7.0;
    p.washyLu = -4.0;
    p.echoMinLu = -26.0;
    p.tailMinDb = -36.0;     // plates and rooms of 1.2-2 s
    v.push_back(p);

    AnalysisProfile r = d;
    r.name = "rock";
    r.description = "rock band: kick and bass punch at 60-100 Hz with less sub than pop, guitars and snare forward in the "
                    "mids, dense, -10..-7 LUFS";
    r.psdOffsetDb = {{25, -4.0},   {31.5, -3.5}, {40, -2.5},   {50, -1.5},   {63, -0.5},   {80, 0.0},
                     {160, 0.0},   {200, 0.5},   {250, 1.0},   {400, 1.0},   {500, 1.5},   {1600, 1.5},
                     {2000, 1.0},  {3150, 1.0},  {4000, 0.5},  {5000, 0.5},  {6300, 0.0},  {10000, 0.0},
                     {12500, -1.0}, {16000, -2.0}};
    r.lufsMin = -10.0;
    r.lufsMax = -7.0;
    r.bandHighDb[0] = 4.0;   // a subby 808-style low end is not rock
    r.bandLowDb = {Lim(-8.0), Lim(-6.0), none, Lim(-5.0), Lim(-6.0), none, none};  // scooped mids / no bite = weak guitars
    r.plrMinDb = 5.0;        // loud masters: -8 LUFS at -1 dBTP = PLR 7
    r.lraMinLu = 2.5;
    r.lraMaxLu = 12.0;
    r.widthMinPct = 25.0;    // double-tracked guitars left / right
    r.widthMaxPct = 100.0;
    r.wetMinLu = -20.0;      // drum room, snare plate, lead delay: drier than pop
    r.wetMaxLu = -9.0;
    r.washyLu = -5.0;
    r.echoMinLu = -26.0;
    r.tailMinDb = -40.0;     // drum rooms and short plates
    v.push_back(r);

    AnalysisProfile f = d;
    f.name = "film";
    f.description = "orchestral hybrid film score: orchestra plus low hits / synth sub in a big hall, darker top, dynamic "
                    "(-16..-10 LUFS, LRA 5-20)";
    f.psdOffsetDb = {{25, -2.0},   {31.5, 1.0},  {40, 2.0},    {50, 2.5},    {63, 2.0},    {80, 1.5},
                     {100, 1.0},   {125, 0.5},   {250, 0.5},   {630, 0.5},   {800, 0.0},   {1600, 0.0},
                     {2000, -0.5}, {2500, -0.5}, {3150, -1.0}, {5000, -1.0}, {6300, -1.5}, {8000, -2.0},
                     {10000, -2.0}, {12500, -2.5}, {16000, -3.5}};
    f.lufsMin = -16.0;
    f.lufsMax = -10.0;
    f.bandHighDb = {Lim(6.0), Lim(4.0), Lim(4.0), Lim(4.0), Lim(3.0), Lim(4.0), Lim(6.0)};
    f.bandLowDb = {Lim(-6.0), Lim(-6.0), none, none, Lim(-8.0), none, none};  // the low hits are part of the style
    f.dullDb = -7.0;
    f.tiltToleranceDbPerOct = 2.0;
    f.plrMinDb = 8.0;
    f.lraMinLu = 5.0;
    f.lraMaxLu = 20.0;
    f.widthMinPct = 30.0;
    f.widthMaxPct = 120.0;
    f.wetMinLu = -13.0;
    f.wetMaxLu = -3.0;
    f.washyLu = -2.0;
    f.echoMinLu = -26.0;
    f.tailMinDb = -30.0;
    f.returnLowMaxPct = 45.0;
    v.push_back(f);

    return v;
}

double offsetDb(const std::vector<std::pair<double, double>>& pts, double f) noexcept {
    if (pts.empty()) return 0.0;
    if (f <= pts.front().first) return pts.front().second;
    if (f >= pts.back().first) return pts.back().second;
    const auto it = std::upper_bound(pts.begin(), pts.end(), f, [](double x, const auto& p) { return x < p.first; });
    const auto& [f1, d1] = *it;
    const auto& [f0, d0] = *(it - 1);
    const double t = std::log2(f / f0) / std::log2(f1 / f0);
    return d0 + t * (d1 - d0);
}

}  // namespace

double AnalysisProfile::psdDb(double hz) const noexcept { return referencePsdDb(hz) + offsetDb(psdOffsetDb, hz); }

double AnalysisProfile::energy(double f0, double f1) const noexcept {
    constexpr int kSteps = 256;
    if (!(f1 > f0) || !(f0 > 0.0)) return 0.0;
    const double r = std::log(f1 / f0) / kSteps;
    double sum = 0.0;
    for (int i = 0; i < kSteps; ++i) {
        const double fa = f0 * std::exp(r * i), fb = f0 * std::exp(r * (i + 1));
        sum += std::pow(10.0, psdDb(std::sqrt(fa * fb)) / 10.0) * (fb - fa);
    }
    return sum;
}

std::array<double, kNumBands> AnalysisProfile::bandShares() const {
    std::array<double, kNumBands> s{};
    double total = 0.0;
    for (int b = 0; b < kNumBands; ++b) {
        s[static_cast<std::size_t>(b)] = energy(kBandEdgesHz[b], kBandEdgesHz[b + 1]);
        total += s[static_cast<std::size_t>(b)];
    }
    for (double& x : s) x /= total;
    return s;
}

const std::vector<AnalysisProfile>& analysisProfiles() {
    static const std::vector<AnalysisProfile> profiles = makeProfiles();
    return profiles;
}

const AnalysisProfile* findAnalysisProfile(const std::string& name) {
    for (const auto& p : analysisProfiles())
        if (p.name == name) return &p;
    return nullptr;
}

const AnalysisProfile& defaultAnalysisProfile() { return analysisProfiles().front(); }

std::string analysisProfileNames() {
    std::string s;
    for (const auto& p : analysisProfiles()) s += (s.empty() ? "" : ", ") + p.name;
    return s;
}

}  // namespace as::analysis
