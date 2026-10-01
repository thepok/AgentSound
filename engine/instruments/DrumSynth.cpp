#include "instruments/DrumSynth.h"

// Every piece is a small analog-style model:
//   kick     sine with an exponential pitch sweep (in semitones), shaped amp envelope, tanh drive,
//            phase-coherent clean sub tail, band-passed noise + blip click, DC blocker.
//   snare    up to 3 membrane partials with a short pitch drop (+ soft drive, 909 style) and HP/LP
//            filtered noise with a fast "crack" + tail envelope, lightly modulated by the body (wires).
//   clap     808 style: sawtooth noise bursts + tail, enveloped *before* a band-pass (smooth onsets).
//   hats     six PolyBLEP squares at inharmonic TR-808 (or denser 909-style) frequencies + noise,
//            band-pass -> VCA -> high-pass -> gentle low-pass. One physical hi-hat: every hat hit
//            chokes the ringing ones with a short fade.
//   toms     swept sine + inharmonic second mode + band-passed stick noise.
//   crash    twelve squares + noise in a mid band and a slowly swelling high band with separate
//            envelopes plus a broadband transient; ride = band-passed ping/wash + additive bell.
//   rim      two or three driven resonator partials + click; cowbell = 808 two-square design;
//            tambourine = jingle partials re-excited by short bursts, crossfaded to a shaker.
// Voices are pooled per piece; steals and chokes fade the old voice out over a few ms. Clap, crash and
// ride have a mono-compatible stereo width (decorrelated side signal); kits are loudness-matched.

#include "dsp/Dsp.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace as {
namespace {

using BT = dsp::Biquad::Type;
constexpr double kTwoPi = dsp::kTwoPi;
constexpr float kLn1000 = 6.90775528f;       // exp(-kLn1000) = -60 dB
constexpr float kLn2Over12 = 0.0577622650f;  // semitones -> natural-log frequency ratio
constexpr int kChunk = 256;

// ------------------------------------------------------------------------------------------
// Parameters

enum Kit : int { Kit808, Kit909, KitLinn, KitSynthwave, KitModern, KitCount };
constexpr int kDefaultKit = KitSynthwave;

enum Piece : int { Kick, Snare, Clap, Hat, Tom, Crash, Ride, Rim, Cowbell, Tamb, PieceCount };

enum Id : int {
    PKit, PLevel, PVelocity, PHumanize,
    KickLevel, KickPan, KickTune, KickDecay, KickPitchEnv, KickPitchDecay, KickClick, KickDrive, KickSub,
    KickTone, KickPunch,
    SnareLevel, SnarePan, SnareTune, SnareDecay, SnareTone, SnareSnappy, SnareNoiseDecay, SnareBodyDecay,
    SnareHpf, SnareLpf,
    ClapLevel, ClapPan, ClapTune, ClapDecay, ClapSpread, ClapTone, ClapBursts, ClapWidth,
    HatLevel, HatPan, HatTune, HatDecay, HatOpenDecay, HatTone, HatNoise, HatModel,
    TomLevel, TomPan, TomTune, TomDecay, TomDrop, TomSpread,
    CrashLevel, CrashPan, CrashTune, CrashDecay, CrashTone, CrashWidth,
    RideLevel, RidePan, RideTune, RideDecay, RideTone, RideBell, RideWidth,
    RimLevel, RimPan, RimTune, RimDecay,
    CowLevel, CowPan, CowTune, CowDecay,
    TambLevel, TambPan, TambTune, TambDecay, TambJingle,
    IdCount
};

constexpr Id kLevelId[PieceCount] = {KickLevel, SnareLevel, ClapLevel, HatLevel, TomLevel,
                                     CrashLevel, RideLevel, RimLevel, CowLevel, TambLevel};
constexpr Id kPanId[PieceCount] = {KickPan, SnarePan, ClapPan, HatPan, TomPan,
                                   CrashPan, RidePan, RimPan, CowPan, TambPan};
// Pieces with a stereo width control (IdCount = none).
constexpr Id kWidthId[PieceCount] = {IdCount, IdCount, ClapWidth, IdCount, IdCount,
                                     CrashWidth, RideWidth, IdCount, IdCount, IdCount};

struct KitRow {
    Id id;
    float v[KitCount];
};

// Per-kit defaults. Parameters not listed keep their spec default in every kit.
//                                    808       909      linn    synthwave  modern
constexpr KitRow kKitTable[] = {
    {KickTune,        {   48.0f,    53.0f,    62.0f,    50.0f,    46.0f}},
    {KickDecay,       {   1.20f,    0.55f,    0.35f,    0.70f,    0.60f}},
    {KickPitchEnv,    {    7.0f,    28.0f,    14.0f,    24.0f,    34.0f}},
    {KickPitchDecay,  {  0.060f,   0.045f,   0.030f,   0.050f,   0.035f}},
    {KickClick,       {   0.00f,    0.45f,    0.60f,    0.25f,    0.35f}},
    {KickDrive,       {   0.05f,    0.30f,    0.10f,    0.25f,    0.40f}},
    {KickSub,         {   0.00f,    0.15f,    0.00f,    0.35f,    0.50f}},
    {KickTone,        {   0.35f,    0.55f,    0.60f,    0.50f,    0.55f}},
    {KickPunch,       {   0.00f,    0.60f,    0.50f,    0.50f,    0.70f}},
    {SnareTune,       {  238.0f,   185.0f,   200.0f,   190.0f,   210.0f}},
    {SnareDecay,      {   0.25f,    0.30f,    0.35f,    0.40f,    0.28f}},
    {SnareTone,       {   0.60f,    0.55f,    0.60f,    0.60f,    0.50f}},
    {SnareSnappy,     {   0.55f,    0.70f,    0.65f,    0.70f,    0.75f}},
    {SnareBodyDecay,  {   0.55f,    0.45f,    0.50f,    0.50f,    0.40f}},
    {SnareHpf,        { 1500.0f,   800.0f,   350.0f,   600.0f,   900.0f}},
    {SnareLpf,        { 9000.0f, 12000.0f,  9000.0f, 11000.0f, 14000.0f}},
    {ClapDecay,       {   0.25f,    0.30f,    0.35f,    0.40f,    0.30f}},
    {ClapSpread,      {   10.0f,     8.0f,    12.0f,    11.0f,     7.0f}},
    {ClapTone,        {   0.35f,    0.55f,    0.45f,    0.50f,    0.60f}},
    {ClapBursts,      {    4.0f,     4.0f,     5.0f,     4.0f,     3.0f}},
    {ClapWidth,       {   0.20f,    0.25f,    0.30f,    0.40f,    0.45f}},
    {HatPan,          {  -0.15f,   -0.15f,   -0.25f,   -0.20f,   -0.15f}},
    {HatDecay,        {  0.060f,   0.070f,   0.080f,   0.070f,   0.050f}},
    {HatOpenDecay,    {   0.45f,    0.50f,    0.60f,    0.55f,    0.40f}},
    {HatTone,         {   0.45f,    0.60f,    0.50f,    0.55f,    0.65f}},
    {HatNoise,        {   0.05f,    0.70f,    0.90f,    0.40f,    0.60f}},
    {HatModel,        {    0.0f,     1.0f,     1.0f,     0.0f,     1.0f}},
    {TomDecay,        {   0.60f,    0.45f,    0.50f,    0.70f,    0.50f}},
    {TomDrop,         {    2.0f,     5.0f,     2.5f,     9.0f,     4.0f}},
    {TomSpread,       {   0.30f,    0.30f,    0.50f,    0.50f,    0.40f}},
    {CrashPan,        {  -0.25f,   -0.25f,   -0.30f,   -0.25f,   -0.25f}},
    {CrashDecay,      {   1.80f,    2.20f,    2.00f,    3.00f,    2.20f}},
    {CrashTone,       {   0.50f,    0.60f,    0.55f,    0.65f,    0.60f}},
    {CrashWidth,      {   0.45f,    0.50f,    0.50f,    0.60f,    0.65f}},
    {RidePan,         {   0.30f,    0.30f,    0.35f,    0.30f,    0.30f}},
    {RideDecay,       {   2.00f,    2.50f,    2.20f,    3.00f,    2.50f}},
    {RideTone,        {   0.50f,    0.55f,    0.50f,    0.55f,    0.60f}},
    {RideBell,        {   0.20f,    0.35f,    0.40f,    0.35f,    0.30f}},
    {RideWidth,       {   0.35f,    0.40f,    0.40f,    0.45f,    0.50f}},
    {RimDecay,        {  0.050f,   0.060f,   0.080f,   0.070f,   0.050f}},
    {CowPan,          {   0.20f,    0.20f,    0.20f,    0.20f,    0.20f}},
    {CowDecay,        {   0.35f,    0.30f,    0.40f,    0.40f,    0.30f}},
    {TambPan,         {   0.25f,    0.25f,    0.30f,    0.25f,    0.25f}},
    {TambDecay,       {   0.12f,    0.20f,    0.25f,    0.22f,    0.18f}},
    {TambJingle,      {   0.00f,    0.60f,    0.90f,    0.70f,    0.30f}},
};

float kitDefault(Id id, float fallback) {
    for (const auto& row : kKitTable)
        if (row.id == id) return row.v[kDefaultKit];
    return fallback;
}

std::vector<ParamSpec> buildSpecs() {
    std::vector<ParamSpec> s(IdCount);
    auto add = [&](Id id, std::string name, float lo, float hi, float fallback, std::string unit, std::string help) {
        s[id] = num(std::move(name), lo, hi, kitDefault(id, fallback), std::move(unit), std::move(help));
    };

    s[PKit] = choice("kit", {"808", "909", "linn", "synthwave", "modern"}, kDefaultKit,
                     "Drum machine character: 808 (boomy, clean, clangy metals), 909 (punchy kick, bright snare), "
                     "linn (LinnDrum-like acoustic punch), synthwave (big 80s hybrid), modern (tight, deep sub). "
                     "Sets every per-piece default (the defaults listed here are the synthwave kit's); per-piece "
                     "values you give override it, e.g. {\"kit\": \"909\", \"snare.decay\": 0.3}.");
    add(PLevel, "level", -60, 12, 0, "dB", "Master level of the whole kit.");
    add(PVelocity, "velocity", 0, 1, 0.6f, "",
        "Velocity sensitivity: 0 = every hit at full level; 1 = strong dynamics (velocity 64 is about -12 dB) "
        "and softer hits are also darker.");
    add(PHumanize, "humanize", 0, 1, 0.2f, "",
        "Seeded per-hit variation so repeats are not machine-gun identical; at 1: +/-25 cents pitch, +/-12% decay, "
        "+/-2 dB level, +/-0.1 octave brightness. 0 = exact repeats (noise still varies like real hardware).");

    const char* label[PieceCount] = {"kick (35/36)", "snare (38/40)", "clap (39)",     "hi-hats (42/44/46)",
                                     "toms (41-50)", "crash (49/57)", "ride (51/59)",  "rim/side-stick (37)",
                                     "cowbell (56)", "tambourine/shaker (54)"};
    const char* prefix[PieceCount] = {"kick", "snare", "clap", "hat", "tom", "crash", "ride", "rim", "cowbell", "tamb"};
    for (int pc = 0; pc < PieceCount; ++pc) {
        const std::string p = prefix[pc];
        add(kLevelId[pc], p + ".level", -60, 12, 0, "dB", std::string("Level of the ") + label[pc] + ", relative to the kit.");
        add(kPanId[pc], p + ".pan", -1, 1, 0, "",
            std::string("Stereo position of the ") + label[pc] + ": -1 left, 0 centre, 1 right.");
    }

    add(KickTune, "kick.tune", 25, 150, 50, "Hz",
        "Pitch the kick settles to; tune it to the song key (41.2 = E1, 43.7 = F1, 49 = G1, 55 = A1).");
    add(KickDecay, "kick.decay", 0.05f, 4, 0.7f, "s", "Kick length: time for the body to fall by 60 dB.");
    add(KickPitchEnv, "kick.pitchenv", 0, 60, 24, "st",
        "How far above 'tune' the pitch sweep starts; more = harder, zappier punch (808 ~7, 909 ~28).");
    add(KickPitchDecay, "kick.pitchdecay", 0.002f, 0.5f, 0.05f, "s",
        "Duration of the pitch sweep (reaches ~95% of the drop); short = tight thump, long = laser 'pew'.");
    add(KickClick, "kick.click", 0, 1, 0.25f, "", "Beater/click transient level (filtered noise + blip); 0 = clean body only.");
    add(KickDrive, "kick.drive", 0, 1, 0.25f, "",
        "Saturation of the body: harmonics, loudness and sustain for small speakers (the sub tail stays clean).");
    add(KickSub, "kick.sub", 0, 1, 0.35f, "",
        "Clean sine tail that holds the fundamental as the body decays (808 boom); keep low with long decays.");
    add(KickTone, "kick.tone", 0, 1, 0.5f, "",
        "Brightness of click and drive harmonics (low-pass from 200 Hz at 0 up to fully open at 1).");
    add(KickPunch, "kick.punch", 0, 1, 0.5f, "",
        "Amp envelope shape: 0 = pure exponential (boomy 808), 1 = body held longer then dropping fast (punchy 909).");

    add(SnareTune, "snare.tune", 80, 500, 190, "Hz", "Pitch of the drum body (lowest mode); 808 ~238, 909 ~185.");
    add(SnareDecay, "snare.decay", 0.03f, 2, 0.4f, "s",
        "Overall snare length; noise and body decays are fractions of it (noisedecay, bodydecay).");
    add(SnareTone, "snare.tone", 0, 1, 0.6f, "", "Level of the tuned drum body (the 'tone' knob).");
    add(SnareSnappy, "snare.snappy", 0, 1, 0.7f, "", "Level of the snare-wire noise (the 'snappy' knob).");
    add(SnareNoiseDecay, "snare.noisedecay", 0.05f, 2, 1.0f, "x", "Noise (wires) decay as a fraction of snare.decay.");
    add(SnareBodyDecay, "snare.bodydecay", 0.05f, 2, 0.5f, "x", "Body decay as a fraction of snare.decay.");
    add(SnareHpf, "snare.hpf", 20, 8000, 600, "Hz", "High-pass cutoff of the wire noise; higher = thinner, crisper.");
    add(SnareLpf, "snare.lpf", 1000, 20000, 11000, "Hz", "Low-pass cutoff of the wire noise; lower = darker, softer.");

    add(ClapTune, "clap.tune", -24, 24, 0, "st", "Shifts the clap's band-pass filter in semitones.");
    add(ClapDecay, "clap.decay", 0.03f, 3, 0.4f, "s", "Length of the reverb-like tail after the last burst.");
    add(ClapSpread, "clap.spread", 2, 40, 11, "ms",
        "Spacing of the hand-clap bursts: small = tight single clap, large = loose group of clappers.");
    add(ClapTone, "clap.tone", 0, 1, 0.5f, "", "Brightness of the clap (filter centre and air).");
    add(ClapBursts, "clap.bursts", 1, 8, 4, "", "Number of quick noise bursts before the tail (808 = 4); rounded.");
    add(ClapWidth, "clap.width", 0, 1, 0.4f, "",
        "Stereo width of the clap (mono-compatible decorrelated side signal): 0 = mono point, 1 = wide.");

    add(HatTune, "hat.tune", -24, 24, 0, "st", "Pitch of the metallic oscillator bank in semitones (all hats).");
    add(HatDecay, "hat.decay", 0.01f, 1, 0.07f, "s", "Closed hat (42) length; the pedal hat (44) uses 75% of it.");
    add(HatOpenDecay, "hat.opendecay", 0.05f, 4, 0.55f, "s", "Open hat (46) length; any following hat hit chokes it.");
    add(HatTone, "hat.tone", 0, 1, 0.55f, "", "Brightness: moves the hat filters up (crisp, airy) or down (dark).");
    add(HatNoise, "hat.noise", 0, 1, 0.4f, "",
        "Noise share of the hat (equal loudness at any setting): 0 = pure metallic square bank (808), "
        "1 = pure filtered noise (sampled-hat character).");
    s[HatModel] = choice("hat.model", {"808", "909"}, static_cast<int>(kitDefault(HatModel, 0.0f)),
                         "Metallic bank: 808 = six squares at the TR-808 frequencies (clangy); 909 = higher, "
                         "denser set (smoother sizzle).");

    add(TomTune, "tom.tune", -24, 24, 0, "st",
        "Pitch offset of all toms; low/mid/high keep their intervals, 43/47/50 sit 2 st above 41/45/48.");
    add(TomDecay, "tom.decay", 0.05f, 4, 0.7f, "s", "Tom length.");
    add(TomDrop, "tom.drop", 0, 36, 9, "st",
        "Pitch drop during each hit: ~2 acoustic, ~5 909, 9+ Simmons/syndrum 'pew'.");
    add(TomSpread, "tom.spread", 0, 1, 0.5f, "", "Stereo spread of the toms around tom.pan (high toms left, floor right).");

    add(CrashTune, "crash.tune", -24, 24, 0, "st", "Pitch of the crash's metallic partials in semitones.");
    add(CrashDecay, "crash.decay", 0.2f, 10, 3, "s", "Crash length.");
    add(CrashTone, "crash.tone", 0, 1, 0.65f, "", "Crash brightness (filters and high sizzle).");
    add(CrashWidth, "crash.width", 0, 1, 0.6f, "",
        "Stereo width of the crash (mono-compatible decorrelated side signal): 0 = mono point, 1 = wide overheads.");

    add(RideTune, "ride.tune", -24, 24, 0, "st", "Pitch of the ride's metallic partials and bell in semitones.");
    add(RideDecay, "ride.decay", 0.2f, 10, 3, "s", "Ride wash length.");
    add(RideTone, "ride.tone", 0, 1, 0.55f, "", "Ride brightness.");
    add(RideBell, "ride.bell", 0, 1, 0.35f, "", "Level of the bell partials (pitch 59 plays with extra bell).");
    add(RideWidth, "ride.width", 0, 1, 0.45f, "",
        "Stereo width of the ride (mono-compatible decorrelated side signal): 0 = mono point, 1 = wide.");

    add(RimTune, "rim.tune", -24, 24, 0, "st", "Pitch of the rim/side-stick resonators in semitones.");
    add(RimDecay, "rim.decay", 0.01f, 1, 0.07f, "s", "Rim/side-stick length.");

    add(CowTune, "cowbell.tune", -24, 24, 0, "st", "Pitch of the two square oscillators (808: 540 + 800 Hz), semitones.");
    add(CowDecay, "cowbell.decay", 0.02f, 2, 0.4f, "s", "Cowbell tail length.");

    add(TambTune, "tamb.tune", -24, 24, 0, "st", "Pitch of the tambourine jingles / shaker band in semitones.");
    add(TambDecay, "tamb.decay", 0.02f, 2, 0.22f, "s", "Tambourine/shaker length.");
    add(TambJingle, "tamb.jingle", 0, 1, 0.7f, "", "0 = shaker/maracas (soft filtered noise), 1 = tambourine (metallic jingles).");

    for (const auto& spec : s)
        if (spec.name.empty()) throw std::logic_error("DrumSynth: incomplete ParamSpec table");
    for (const auto& row : kKitTable)
        for (float v : row.v)
            if (v < s[row.id].min || v > s[row.id].max)
                throw std::logic_error("DrumSynth: kit default out of range for " + s[row.id].name);
    return s;
}

const std::vector<ParamSpec>& specs() {
    static const std::vector<ParamSpec> table = buildSpecs();
    return table;
}

// ------------------------------------------------------------------------------------------
// Kit voicing: fixed per-kit constants that are not exposed as parameters.

struct Voicing {
    float kickClickHz, kickClickTau;       // click band centre, click noise time constant (s)
    std::array<float, 3> snRatio, snAmp;   // snare body modes (ratio to tune, relative level)
    float snDrop, snDrive, snFast, snWire, snCrackDb;  // body pitch drop (st), body drive, fast-noise weight,
                                                        // wire modulation, +dB presence peak at 4.5 kHz
    float clapHz, clapQ;
    float hatBpHz, hatBpQ, hatHpRatio;     // hat band-pass centre at tone 0.5, its Q, high-pass / band-pass ratio
    std::array<float, 3> tomHz;            // low/mid/high tom at tune 0
    float tomRatio2, tomAmp2, tomNoise;    // second mode ratio/level, stick noise level
    float crashNoise, rideNoise;           // noise share of the cymbal sources
    float cymSmear;                        // noise AM that spreads each metallic partial into a band
    std::array<float, 3> rimHz, rimAmp, rimDecay;
    float rimNoise, rimDrive;
    float cowHz1, cowHz2;
};

constexpr Voicing kVoicing[KitCount] = {
    {.kickClickHz = 3000, .kickClickTau = 0.0010f,
     .snRatio = {1.0f, 2.0f, 0.0f}, .snAmp = {1.0f, 0.55f, 0.0f},
     .snDrop = 0.6f, .snDrive = 0.0f, .snFast = 0.25f, .snWire = 0.0f, .snCrackDb = 0.0f,
     .clapHz = 1000, .clapQ = 1.4f,
     .hatBpHz = 7800, .hatBpQ = 1.2f, .hatHpRatio = 0.85f,
     .tomHz = {86.0f, 116.0f, 158.0f}, .tomRatio2 = 1.50f, .tomAmp2 = 0.05f, .tomNoise = 0.10f,
     .crashNoise = 0.15f, .rideNoise = 0.10f, .cymSmear = 0.2f,
     .rimHz = {455.0f, 1667.0f, 0.0f}, .rimAmp = {0.55f, 1.0f, 0.0f}, .rimDecay = {1.0f, 0.6f, 0.0f},
     .rimNoise = 0.10f, .rimDrive = 2.5f,
     .cowHz1 = 540, .cowHz2 = 800},
    {.kickClickHz = 4000, .kickClickTau = 0.0012f,
     .snRatio = {1.0f, 1.77f, 0.0f}, .snAmp = {1.0f, 0.70f, 0.0f},
     .snDrop = 3.0f, .snDrive = 0.35f, .snFast = 0.55f, .snWire = 0.05f, .snCrackDb = 2.0f,
     .clapHz = 1150, .clapQ = 1.2f,
     .hatBpHz = 9000, .hatBpQ = 0.8f, .hatHpRatio = 0.75f,
     .tomHz = {98.0f, 131.0f, 175.0f}, .tomRatio2 = 1.50f, .tomAmp2 = 0.12f, .tomNoise = 0.30f,
     .crashNoise = 0.55f, .rideNoise = 0.35f, .cymSmear = 0.8f,
     .rimHz = {500.0f, 1720.0f, 3200.0f}, .rimAmp = {0.5f, 1.0f, 0.25f}, .rimDecay = {1.0f, 0.6f, 0.35f},
     .rimNoise = 0.20f, .rimDrive = 2.2f,
     .cowHz1 = 540, .cowHz2 = 800},
    {.kickClickHz = 2800, .kickClickTau = 0.0025f,
     .snRatio = {1.0f, 1.59f, 2.14f}, .snAmp = {1.0f, 0.50f, 0.30f},
     .snDrop = 1.5f, .snDrive = 0.1f, .snFast = 0.45f, .snWire = 0.35f, .snCrackDb = 0.0f,
     .clapHz = 1050, .clapQ = 1.0f,
     .hatBpHz = 8500, .hatBpQ = 0.7f, .hatHpRatio = 0.7f,
     .tomHz = {92.0f, 124.0f, 165.0f}, .tomRatio2 = 1.59f, .tomAmp2 = 0.35f, .tomNoise = 0.30f,
     .crashNoise = 0.65f, .rideNoise = 0.40f, .cymSmear = 0.9f,
     .rimHz = {420.0f, 1180.0f, 2650.0f}, .rimAmp = {0.7f, 1.0f, 0.45f}, .rimDecay = {1.0f, 0.7f, 0.4f},
     .rimNoise = 0.35f, .rimDrive = 1.5f,
     .cowHz1 = 560, .cowHz2 = 845},
    {.kickClickHz = 3500, .kickClickTau = 0.0012f,
     .snRatio = {1.0f, 1.72f, 2.40f}, .snAmp = {1.0f, 0.55f, 0.15f},
     .snDrop = 4.0f, .snDrive = 0.25f, .snFast = 0.5f, .snWire = 0.15f, .snCrackDb = 1.5f,
     .clapHz = 1100, .clapQ = 1.3f,
     .hatBpHz = 8000, .hatBpQ = 1.0f, .hatHpRatio = 0.8f,
     .tomHz = {90.0f, 122.0f, 164.0f}, .tomRatio2 = 1.50f, .tomAmp2 = 0.15f, .tomNoise = 0.35f,
     .crashNoise = 0.50f, .rideNoise = 0.30f, .cymSmear = 0.8f,
     .rimHz = {455.0f, 1667.0f, 0.0f}, .rimAmp = {0.55f, 1.0f, 0.0f}, .rimDecay = {1.0f, 0.6f, 0.0f},
     .rimNoise = 0.15f, .rimDrive = 2.5f,
     .cowHz1 = 540, .cowHz2 = 800},
    {.kickClickHz = 4500, .kickClickTau = 0.0008f,
     .snRatio = {1.0f, 1.65f, 2.30f}, .snAmp = {1.0f, 0.50f, 0.20f},
     .snDrop = 5.0f, .snDrive = 0.35f, .snFast = 0.6f, .snWire = 0.1f, .snCrackDb = 2.5f,
     .clapHz = 1250, .clapQ = 1.1f,
     .hatBpHz = 9500, .hatBpQ = 0.8f, .hatHpRatio = 0.7f,
     .tomHz = {95.0f, 128.0f, 170.0f}, .tomRatio2 = 1.55f, .tomAmp2 = 0.20f, .tomNoise = 0.25f,
     .crashNoise = 0.60f, .rideNoise = 0.40f, .cymSmear = 0.9f,
     .rimHz = {520.0f, 1850.0f, 3400.0f}, .rimAmp = {0.5f, 1.0f, 0.2f}, .rimDecay = {1.0f, 0.6f, 0.35f},
     .rimNoise = 0.20f, .rimDrive = 2.2f,
     .cowHz1 = 545, .cowHz2 = 810},
};

// Metallic square banks (Hz). 808: the six TR-808 cymbal/hat oscillators.
constexpr std::array<double, 6> kMetal808 = {205.3, 304.4, 369.6, 522.7, 540.0, 800.0};
constexpr std::array<double, 6> kMetal909 = {317.0, 447.0, 571.0, 689.0, 811.0, 1016.0};
constexpr std::array<double, 6> kJingleHz = {5310.0, 6470.0, 7730.0, 8920.0, 10300.0, 11800.0};

// Output gains that balance the synthwave kit's pieces (see kKitTrimDb for the targets). Single hits at
// velocity 127 peak around -12 dBFS (kick) .. -4 dBFS (snare); a full groove sits near -20 dBFS RMS with
// peaks around -1.5 dBFS.
constexpr float kKickGain = 0.48f;
constexpr float kSnareGain = 1.03f;
constexpr float kClapGain = 2.39f;
constexpr float kHatGain = 2.36f;
constexpr float kTomGain = 0.374f;
constexpr float kCrashGain = 1.21f;
constexpr float kRideGain = 1.165f;
constexpr float kRimGain = 0.41f;
constexpr float kCowGain = 0.381f;
constexpr float kTambGain = 0.415f;
constexpr float kOutputTrim = 0.794f;  // -2 dB: headroom for kick + snare + clap stacks

// Per-kit loudness trims (dB): kits differ in character, not in level, so switching kits keeps the mix.
// Calibrated so that single full-velocity hits have the same K-weighted 400 ms loudness in every kit
// (relative to the kick: snare -2, clap -4, rim -9, closed hat -15, toms -3, crash -5, ride -9,
// cowbell -10, tambourine -12 LU).
//                                            kick  snare  clap   hat    tom  crash   ride    rim    cow   tamb
constexpr float kKitTrimDb[KitCount][PieceCount] = {
    /* 808       */ {2.0f, 3.7f,  3.0f,  0.5f, 0.4f,  3.9f,  0.2f, 1.5f,  0.2f, -0.4f},
    /* 909       */ {0.6f, 1.3f,  0.5f,  0.6f, 1.8f,  0.4f,  0.1f, 2.0f,  0.5f, -0.1f},
    /* linn      */ {2.5f, 1.9f, -0.8f, -0.5f, 3.1f, -0.2f, -0.2f, 4.4f, -0.3f,  0.1f},
    /* synthwave */ {0.0f, 0.0f,  0.0f,  0.0f, 0.0f,  0.0f,  0.0f, 0.0f,  0.0f,  0.0f},
    /* modern    */ {0.6f, 1.5f, -0.2f,  1.9f, 2.0f,  0.1f,  0.0f, 2.5f,  0.5f, -1.1f},
};

// ------------------------------------------------------------------------------------------
// DSP helpers

inline float semis(float st) noexcept { return std::exp2(st * (1.0f / 12.0f)); }
// Per-sample multiplier of an exponential that falls 60 dB in `seconds`.
inline float t60Mul(double seconds, double sr) noexcept {
    return static_cast<float>(std::exp(-kLn1000 / (std::max(seconds, 1e-4) * sr)));
}
// Per-sample multiplier of an exponential with time constant `seconds`.
inline float tauMul(double seconds, double sr) noexcept {
    return static_cast<float>(std::exp(-1.0 / (std::max(seconds, 1e-5) * sr)));
}
inline int samplesFor(double seconds, double sr) noexcept { return static_cast<int>(std::ceil(seconds * sr)) + 1; }
inline double safeHz(double f, double sr) noexcept { return std::clamp(f, 10.0, 0.45 * sr); }
inline void decay(float& env, float mul) noexcept { env = dsp::flush(env * mul); }
// Gentle peak saturation: unity slope, about -1.7 dB at 1.1 x knee, ceiling 1.0 x knee.
inline float saturate(float x, float knee) noexcept { return knee * dsp::softClip(x / knee); }
inline float sine(double phase) noexcept { return static_cast<float>(std::sin(kTwoPi * phase)); }
inline void wrap(double& phase) noexcept {
    if (phase >= 1.0) phase -= 1.0;
}

// Automation smoother: two cascaded one-poles per sample (C1-continuous, so level/pan/width jumps
// are click-free even on a ringing 808 kick, yet fast: 10-90 % = 3.36 x tau). Lands on the target.
constexpr double kGainTau = 0.0015;  // ~5 ms
class Smooth2 {
public:
    void prepare(double sr, double tau, float v) noexcept {
        c_ = static_cast<float>(1.0 - std::exp(-1.0 / (tau * sr)));
        snap(v);
    }
    void setTarget(float t) noexcept { t_ = t; }
    void snap(float v) noexcept { a_ = b_ = t_ = v; }
    float next() noexcept {
        if (b_ != t_ || a_ != t_) {
            a_ += (t_ - a_) * c_;
            b_ += (a_ - b_) * c_;
            if (std::fabs(t_ - a_) + std::fabs(t_ - b_) <= 1e-7f * (1.0f + std::fabs(t_))) a_ = b_ = t_;
        }
        return b_;
    }
    float target() const noexcept { return t_; }

private:
    float c_{1.0f}, a_{0.0f}, b_{0.0f}, t_{0.0f};
};

// Band-limited square (PolyBLEP), phase in cycles.
inline float blepSquare(double& phase, double inc) noexcept {
    const float t = static_cast<float>(phase), dt = static_cast<float>(inc);
    float y = t < 0.5f ? 1.0f : -1.0f;
    y += dsp::polyBlep(t, dt);
    float t2 = t + 0.5f;
    if (t2 >= 1.0f) t2 -= 1.0f;
    y -= dsp::polyBlep(t2, dt);
    phase += inc;
    wrap(phase);
    return y;
}

// Fixed-frequency sine by complex rotation (double precision: no drift over a 10 s tail).
struct SineOsc {
    double re{1.0}, im{0.0}, cr{1.0}, ci{0.0};
    void set(double hz, double sr) noexcept {
        const double w = kTwoPi * hz / sr;
        cr = std::cos(w);
        ci = std::sin(w);
        re = 1.0;
        im = 0.0;
    }
    float next() noexcept {
        const double r = re * cr - im * ci;
        im = re * ci + im * cr;
        re = r;
        return static_cast<float>(im);
    }
};

// Mono-compatible stereo width: a cascade of Schroeder all-passes turns the piece's mono sum into a
// decorrelated copy with the same spectrum, added to the left and subtracted from the right (a side
// signal), so L + R is untouched. Short, prime-ish delays keep the diffusion tight (< 20 ms).
struct Decorrelator {
    static constexpr int kStages = 4;
    static constexpr int kMaxDelay = 1024;  // 6.1 ms at 96 kHz = 586 samples
    std::array<std::array<float, kMaxDelay>, kStages> buf{};
    std::array<int, kStages> len{}, pos{};
    int hold{0}, holdLen{0};  // keeps running this many samples after the last input

    void prepare(double sr, const std::array<double, kStages>& ms) {
        holdLen = 0;
        for (std::size_t k = 0; k < kStages; ++k) {
            len[k] = std::clamp(static_cast<int>(std::lround(ms[k] * 0.001 * sr)), 1, kMaxDelay);
            holdLen += 10 * len[k];  // g = 0.5: 10 round trips per stage are far below -60 dB
        }
        reset();
    }
    void reset() noexcept {
        for (auto& b : buf) b.fill(0.0f);
        pos.fill(0);
        hold = 0;
    }
    float process(float x) noexcept {
        constexpr float g = 0.5f;
        for (std::size_t k = 0; k < kStages; ++k) {
            auto& b = buf[k];
            const auto i = static_cast<std::size_t>(pos[k]);
            const float d = b[i];
            const float w = x + g * d;  // H(z) = (z^-N - g) / (1 - g z^-N)
            x = d - g * w;
            b[i] = dsp::flush(w);
            if (++pos[k] >= len[k]) pos[k] = 0;
        }
        return x;
    }
};

// ------------------------------------------------------------------------------------------
// Voices

struct Hit {
    double sr{48000.0};
    int variant{0};
    float dark{0.0f};   // velocity darkening 0..1 (0 = full velocity or no sensitivity)
    float pitch{1.0f};  // humanize frequency ratio
    float decay{1.0f};  // humanize decay factor
    float tone{0.0f};   // humanize brightness offset (octaves)
    float human{0.0f};  // humanize amount 0..1
    float trim{1.0f};   // kit loudness trim (linear)
    std::uint64_t seed{1};
};

struct VoiceBase {
    bool active{false};
    bool fading{false};
    int variant{0};
    std::uint32_t order{0};
    int age{0};     // samples since trigger
    int length{0};  // total samples (everything is below -90 dB after this)
    float gain{0.0f};
    float panOffset{0.0f};
    float gl{0.0f}, gr{0.0f}, tgl{0.0f}, tgr{0.0f};
    float gl1{0.0f}, gr1{0.0f};  // first stage of the (two-pole) level/pan smoothing
    float fade{1.0f}, fadeStep{0.0f};
    float noiseScale{1.0f};  // keeps white-noise spectral density independent of the sample rate
    dsp::Rng rng;

    void begin(const Hit& h) noexcept {
        active = true;
        fading = false;
        variant = h.variant;
        age = 0;
        fade = 1.0f;
        fadeStep = 0.0f;
        panOffset = 0.0f;
        noiseScale = static_cast<float>(std::sqrt(h.sr / 48000.0));
        rng.reseed(h.seed);
    }
    void startFade(double sr, double seconds) noexcept {
        if (fading) return;
        fading = true;
        fadeStep = fade / static_cast<float>(std::max(1.0, seconds * sr));
    }
    float white() noexcept { return noiseScale * rng.bipolar(); }
    // Samples to render in a block of n; zero-fills the rest of `out`.
    int live(float* out, int n) const noexcept {
        const int k = std::clamp(length - age, 0, n);
        std::fill(out + k, out + n, 0.0f);
        return k;
    }
};

struct KickVoice : VoiceBase {
    double phase{0.0}, invSr{0.0}, maxHz{0.0};
    float f0{50.0f}, sweep{0.0f}, pe{0.0f}, peMul{0.0f};
    float x{0.0f}, dx{0.0f}, curve{1.0f};
    float sub{0.0f}, subEnv{0.0f}, subMul{0.0f};
    float driveG{1.0f}, driveNorm{1.0f};
    float click{0.0f}, clickEnv{0.0f}, clickMul{0.0f}, blipEnv{0.0f}, blipMul{0.0f};
    double blipPhase{0.0}, blipInc{0.0};
    dsp::Biquad clickBp, toneLp;
    bool useLp{false};
    float dcX{0.0f}, dcY{0.0f}, dcR{0.0f};

    void start(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        invSr = 1.0 / sr;
        maxHz = 0.45 * sr;
        phase = 0.0;  // sine starts at zero: no step, the sweep itself is the punch
        f0 = p.get(KickTune) * h.pitch;
        // f(t) = f0 * 2^(pitchenv * e^(-t/tau) / 12), tau = pitchdecay / 3
        sweep = p.get(KickPitchEnv) * (1.0f - 0.3f * h.dark) * kLn2Over12;
        pe = 1.0f;
        peMul = tauMul(p.get(KickPitchDecay) / 3.0, sr);
        const double dec = p.get(KickDecay) * h.decay;
        // body(t) = exp(-ln1000 * (t/decay)^curve): curve 1 = exponential, 2 = held then falling
        x = 0.0f;
        dx = static_cast<float>(1.0 / (dec * sr));
        curve = 1.0f + p.get(KickPunch);
        sub = p.get(KickSub);
        subEnv = 1.0f;
        subMul = t60Mul(1.3 * dec, sr);
        // tanh(g x) / sqrt(g tanh g): peaks drop and the tail rises by the same dB (up to 6 dB each)
        driveG = 1.0f + 3.0f * p.get(KickDrive);
        driveNorm = 1.0f / std::sqrt(driveG * std::tanh(driveG));
        const float tone = std::clamp(p.get(KickTone) + h.tone, 0.0f, 1.0f);
        click = p.get(KickClick) * (1.0f - 0.5f * h.dark);
        clickEnv = blipEnv = 1.0f;
        clickMul = tauMul(vc.kickClickTau, sr);
        blipMul = tauMul(0.0009, sr);
        blipPhase = 0.0;
        blipInc = safeHz(0.45 * vc.kickClickHz, sr) * invSr;
        clickBp.reset();
        clickBp.set(BT::BandPass, sr, safeHz(vc.kickClickHz * std::exp2((tone - 0.5) * 1.5), sr), 0.9);
        const double lp = 200.0 * std::exp2(tone * 6.5);
        useLp = lp < 0.4 * sr;
        toneLp.reset();
        if (useLp) toneLp.set(BT::LowPass, sr, lp, 0.707);
        dcX = dcY = 0.0f;
        dcR = static_cast<float>(1.0 - kTwoPi * 8.0 / sr);
        gain = kKickGain;
        length = samplesFor(dec * (sub > 0.0f ? 1.95 : 1.5), sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            const double f = std::min(static_cast<double>(f0 * std::exp(sweep * pe)), maxHz);
            decay(pe, peMul);
            const float s = sine(phase);
            phase += f * invSr;
            wrap(phase);
            const float body = x > 0.0f ? std::exp(-kLn1000 * std::pow(x, curve)) : 1.0f;
            x += dx;
            float y = s * body;
            if (driveG > 1.0f) y = std::tanh(driveG * y) * driveNorm;
            if (sub > 0.0f) {
                y += s * sub * subEnv * (1.0f - body);  // fills in as the body decays, same phase
                decay(subEnv, subMul);
            }
            if (useLp) y = toneLp.process(y);
            if (click > 0.0f && clickEnv > 1e-5f) {  // after the tone filter: its band-pass tracks 'tone'
                const float nz = clickBp.process(white());
                const float blip = sine(blipPhase);
                blipPhase += blipInc;
                wrap(blipPhase);
                y += click * (2.5f * nz * clickEnv + 0.6f * blip * blipEnv);
                decay(clickEnv, clickMul);
                decay(blipEnv, blipMul);
            }
            const float d = y - dcX + dcR * dcY;  // 8 Hz DC blocker
            dcX = y;
            dcY = dsp::flush(d);
            out[i] = gain * d;
        }
        age += k;
    }
};

struct SnareVoice : VoiceBase {
    std::array<double, 3> ph{}, inc{};
    std::array<float, 3> amp{}, env{}, mul{};
    float sweep{0.0f}, pe{0.0f}, peMul{0.0f};
    float driveG{1.0f}, driveNorm{1.0f};
    float body{0.0f}, noise{0.0f}, wire{0.0f}, pre{1.0f};
    float fastW{0.0f}, fast{0.0f}, fastMul{0.0f}, tail{0.0f}, tailMul{0.0f};
    float atk{0.0f}, atkStep{0.0f};
    dsp::Biquad hp, lp, crack;
    bool useCrack{false};

    void start(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        const bool alt = h.variant == 1;  // pitch 40: brighter, snappier
        const double f1 = p.get(SnareTune) * h.pitch * (alt ? 1.05 : 1.0);
        const double dec = p.get(SnareDecay) * h.decay;
        const double bodyT = dec * p.get(SnareBodyDecay), noiseT = dec * p.get(SnareNoiseDecay);
        const float sum = vc.snAmp[0] + vc.snAmp[1] + vc.snAmp[2];
        for (std::size_t k = 0; k < 3; ++k) {
            ph[k] = 0.0;
            inc[k] = std::min(f1 * vc.snRatio[k], 0.4 * sr) / sr;
            amp[k] = vc.snAmp[k] / sum;
            env[k] = 1.0f;
            mul[k] = t60Mul(bodyT / (1.0 + 0.7 * static_cast<double>(k)), sr);  // higher modes die faster
        }
        sweep = vc.snDrop * (1.0f - 0.3f * h.dark) * kLn2Over12;
        pe = 1.0f;
        peMul = tauMul(0.012, sr);
        driveG = 1.0f + 2.0f * vc.snDrive;
        driveNorm = 1.0f / std::tanh(driveG);
        body = p.get(SnareTone) * (alt ? 0.85f : 1.0f);
        noise = p.get(SnareSnappy) * (alt ? 1.15f : 1.0f);
        wire = vc.snWire;
        pre = h.trim;  // the kit trim drives the peak saturator: louder kits get denser, not higher peaks
        fastW = vc.snFast;
        fast = tail = 1.0f;
        fastMul = tauMul(0.006, sr);
        tailMul = t60Mul(noiseT, sr);
        atk = 0.0f;
        atkStep = static_cast<float>(1.0 / (0.0004 * sr));
        const double bright = h.tone - 1.2 * h.dark;
        hp.reset();
        hp.set(BT::HighPass, sr, safeHz(p.get(SnareHpf) * (alt ? 1.35 : 1.0), sr), 0.707);
        lp.reset();
        lp.set(BT::LowPass, sr, safeHz(p.get(SnareLpf) * (alt ? 1.25 : 1.0) * std::exp2(bright), sr), 0.707);
        useCrack = vc.snCrackDb > 0.0f;
        crack.reset();
        if (useCrack) crack.set(BT::Peak, sr, safeHz(4500.0, sr), 0.9, vc.snCrackDb);
        gain = -kSnareGain;  // top-mic polarity (stick pushes the head away): kick and snare do not stack
        length = samplesFor(1.5 * std::max(bodyT, noiseT) + 0.005, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            const double ratio = std::exp(sweep * pe);
            decay(pe, peMul);
            float b = 0.0f;
            for (std::size_t m = 0; m < 3; ++m) {
                if (amp[m] <= 0.0f) continue;
                b += amp[m] * env[m] * sine(ph[m]);
                ph[m] += inc[m] * ratio;
                wrap(ph[m]);
                decay(env[m], mul[m]);
            }
            if (driveG > 1.0f) b = std::tanh(driveG * b) * driveNorm;
            float nz = lp.process(hp.process(white()));
            if (useCrack) nz = crack.process(nz);
            const float ne = atk * (fastW * fast + (1.0f - fastW) * tail);
            atk = std::min(1.0f, atk + atkStep);
            decay(fast, fastMul);
            decay(tail, tailMul);
            out[i] = gain * saturate(pre * (body * b + noise * ne * nz * (1.0f + wire * b)), 1.2f);
        }
        age += k;
    }
};

struct ClapVoice : VoiceBase {
    std::array<int, 8> at{};
    std::array<float, 8> amp{};
    int bursts{0}, next{0}, tailAt{0};
    float burst{0.0f}, burstMul{0.0f}, tail{0.0f}, tailMul{0.0f}, air{0.0f};
    dsp::Biquad bp, hpLow, hpAir;

    void start(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        bursts = std::clamp(static_cast<int>(std::lround(p.get(ClapBursts))), 1, 8);
        const double spread = p.get(ClapSpread) * 0.001;
        const double jitter = 0.08 + 0.3 * h.human;
        double t = 0.0;
        for (int k = 0; k < bursts; ++k) {
            at[static_cast<std::size_t>(k)] = static_cast<int>(std::lround(t * sr));
            amp[static_cast<std::size_t>(k)] = (k == bursts - 1 && k > 0 ? 0.75f : 1.0f) * (0.85f + 0.15f * rng.uniform());
            t += spread * (1.0 + jitter * rng.bipolar());
        }
        next = 0;
        tailAt = at[static_cast<std::size_t>(bursts - 1)];
        burst = 0.0f;
        burstMul = tauMul(std::clamp(spread * 0.3, 0.0012, 0.008), sr);
        const double dec = p.get(ClapDecay) * h.decay;
        tail = 1.0f;
        tailMul = t60Mul(dec, sr);
        const float tone = p.get(ClapTone);
        const double fc = vc.clapHz * semis(p.get(ClapTune)) * h.pitch *
                          std::exp2((tone - 0.5) * 1.4 + h.tone - 0.8 * h.dark);
        bp.reset();
        bp.set(BT::BandPass, sr, safeHz(fc, sr), vc.clapQ);
        hpLow.reset();
        hpLow.set(BT::HighPass, sr, 250.0, 0.707);
        hpAir.reset();
        hpAir.set(BT::HighPass, sr, safeHz(fc * 2.5, sr), 0.707);
        air = 0.03f + 0.09f * tone;
        gain = kClapGain;
        length = tailAt + samplesFor(1.5 * dec, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            if (next < bursts && age + i >= at[static_cast<std::size_t>(next)]) burst = amp[static_cast<std::size_t>(next++)];
            float e = burst;  // sawtooth bursts; the band-pass after the envelope rounds the onsets
            decay(burst, burstMul);
            if (age + i >= tailAt) {
                e += 0.6f * tail;
                decay(tail, tailMul);
            }
            const float x = white() * e;
            out[i] = gain * hpLow.process(bp.process(x) + air * hpAir.process(x));
        }
        age += k;
    }
};

struct HatVoice : VoiceBase {
    std::array<double, 6> ph{}, inc{};
    float metal{0.0f}, noise{0.0f};
    float fastW{0.0f}, fast{0.0f}, fastMul{0.0f}, tail{0.0f}, tailMul{0.0f};
    float atk{0.0f}, atkStep{0.0f};
    dsp::Biquad bp, hp, lp;

    // variant: 0 closed (42), 1 pedal (44), 2 open (46)
    void start(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        const bool pedal = h.variant == 1, open = h.variant == 2;
        const auto& bank = p.get(HatModel) > 0.5f ? kMetal909 : kMetal808;
        const double r = semis(p.get(HatTune)) * h.pitch;
        double sumHz = 0.0;
        for (std::size_t k = 0; k < 6; ++k) {
            ph[k] = rng.uniform();  // the 808 bank free-runs: every hit catches it at another phase
            inc[k] = std::min(bank[k] * r, 0.25 * sr) / sr;
            sumHz += inc[k] * sr;
        }
        const double tone = p.get(HatTone) + h.tone - 0.7 * h.dark - (pedal ? 0.2 : 0.0);
        const double bpHz = safeHz(vc.hatBpHz * std::exp2((tone - 0.5) * 1.2), sr);
        // Equal-loudness metal/noise crossfade. A unit square at f has odd harmonics 4/(pi k), i.e. a power
        // density of about 4 f / (pi^2 F^2) per Hz near F; our white noise has 2 / (3 * 48000) per Hz. Match
        // both at the band-pass centre, then normalise the band's power (proportional to F / Q) so neither
        // hat.noise nor hat.tone nor the kit's filter Q changes the level much.
        const double metalDensity = 4.0 * sumHz / (dsp::kPi * dsp::kPi * bpHz * bpHz);
        const double noiseDensity = 2.0 / (3.0 * 48000.0);
        const double bandNorm = 0.3 * std::sqrt(vc.hatBpQ * 8000.0 / bpHz);
        const double nz = p.get(HatNoise);
        metal = static_cast<float>(bandNorm * std::sqrt((1.0 - nz) * noiseDensity / metalDensity));
        noise = static_cast<float>(bandNorm * std::sqrt(nz));
        const double dec = (open ? p.get(HatOpenDecay) : p.get(HatDecay) * (pedal ? 0.75 : 1.0)) * h.decay;
        fastW = open ? 0.35f : pedal ? 0.1f : 0.3f;
        fast = tail = 1.0f;
        fastMul = tauMul(open ? 0.008 : 0.004, sr);
        tailMul = t60Mul(dec, sr);
        atk = 0.0f;
        atkStep = static_cast<float>(1.0 / ((pedal ? 0.0015 : open ? 0.0004 : 0.0002) * sr));
        bp.reset();
        bp.set(BT::BandPass, sr, bpHz, vc.hatBpQ);
        hp.reset();
        hp.set(BT::HighPass, sr, safeHz(bpHz * vc.hatHpRatio, sr), 0.707);
        lp.reset();
        lp.set(BT::LowPass, sr, safeHz(13000.0 * std::exp2((tone - 0.5) * 0.8), sr), 0.707);
        gain = kHatGain * (pedal ? 0.7f : open ? 0.9f : 1.0f);
        length = samplesFor(1.5 * dec + 0.002, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            float m = 0.0f;
            for (std::size_t o = 0; o < 6; ++o) m += blepSquare(ph[o], inc[o]);
            const float src = bp.process(metal * m + noise * white());
            const float e = atk * (fastW * fast + (1.0f - fastW) * tail);
            atk = std::min(1.0f, atk + atkStep);
            decay(fast, fastMul);
            decay(tail, tailMul);
            out[i] = gain * lp.process(hp.process(src * e));
        }
        age += k;
    }
};

struct TomVoice : VoiceBase {
    double ph1{0.0}, ph2{0.0}, invSr{0.0};
    float f0{0.0f}, ratio2{0.0f}, amp2{0.0f}, env2{0.0f}, mul2{0.0f};
    float sweep{0.0f}, pe{0.0f}, peMul{0.0f};
    float x{0.0f}, dx{0.0f};
    float nAmt{0.0f}, nFast{0.0f}, nFastMul{0.0f};
    dsp::Biquad nbp;

    // variant: 0..5 = notes 41, 43, 45, 47, 48, 50
    void start(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        invSr = 1.0 / sr;
        const int drum = h.variant / 2;  // 0 low, 1 mid, 2 high
        const bool up = (h.variant % 2) == 1;
        f0 = vc.tomHz[static_cast<std::size_t>(drum)] * semis(p.get(TomTune) + (up ? 2.0f : 0.0f)) * h.pitch;
        const double dec = p.get(TomDecay) * h.decay;
        sweep = p.get(TomDrop) * (1.0f - 0.3f * h.dark) * kLn2Over12;
        pe = 1.0f;
        peMul = tauMul(std::max(0.012, 0.22 * dec), sr);
        ph1 = ph2 = 0.0;
        x = 0.0f;
        dx = static_cast<float>(1.0 / (dec * sr));
        ratio2 = vc.tomRatio2;
        amp2 = vc.tomAmp2;
        env2 = 1.0f;
        mul2 = t60Mul(0.45 * dec, sr);
        nAmt = vc.tomNoise;
        nFast = 1.0f;
        nFastMul = tauMul(0.012, sr);
        nbp.reset();
        nbp.set(BT::BandPass, sr, safeHz(std::clamp(f0 * 9.0, 600.0, 5000.0) * std::exp2(h.tone - 0.5 * h.dark), sr), 0.8);
        panOffset = p.get(TomSpread) * 0.6f * static_cast<float>(1 - drum);
        gain = -kTomGain / (1.0f + amp2);  // top-mic polarity, like the snare
        length = samplesFor(1.5 * dec, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            const double f = std::min(static_cast<double>(f0 * std::exp(sweep * pe)), 4000.0);
            decay(pe, peMul);
            const float env = x > 0.0f ? std::exp(-kLn1000 * std::pow(x, 1.15f)) : 1.0f;
            x += dx;
            const float y = env * (sine(ph1) + amp2 * env2 * sine(ph2));
            ph1 += f * invSr;
            wrap(ph1);
            ph2 += f * ratio2 * invSr;
            wrap(ph2);
            decay(env2, mul2);
            const float nz = nbp.process(white()) * nAmt * (nFast + 0.3f * env);
            decay(nFast, nFastMul);
            out[i] = gain * (y + 2.0f * nz);
        }
        age += k;
    }
};

struct CymbalVoice : VoiceBase {
    bool ride{false};
    int oscs{6};
    std::array<double, 12> ph{}, inc{};
    float metal{0.0f}, noise{0.0f};
    float eA{0.0f}, mA{0.0f}, eB{0.0f}, mB{0.0f}, eF{0.0f}, mF{0.0f}, swell{0.0f}, swellMul{0.0f};
    float atk{0.0f}, atkStep{0.0f};
    float smear{0.0f}, jit{0.0f}, jitA{0.0f}, jitNorm{0.0f};
    dsp::Biquad hp, bandA, bandB, lp;
    std::array<SineOsc, 4> bell{};
    std::array<float, 4> bAmp{}, bEnv{}, bMul{};
    float bellAmt{0.0f};

    void setBank(double ratio, int count, double sr, float smearAmount) {
        oscs = count;
        // Amplitude-modulating the bank with ~250 Hz noise turns every static partial into a narrow
        // noise band: dense, shimmering cymbal instead of a clangy chord. jitNorm makes the noise unit RMS.
        smear = smearAmount;
        jit = 0.0f;
        jitA = static_cast<float>(std::exp(-kTwoPi * 250.0 / sr));
        jitNorm = std::sqrt(3.0f * (1.0f + jitA) / (1.0f - jitA));
        for (std::size_t k = 0; k < 12; ++k) {
            const double spread = k < 6 ? 1.0 : 1.4142;  // second bank: denser, non-harmonic offset
            ph[k] = rng.uniform();
            inc[k] = std::min(kMetal808[k % 6] * ratio * spread, 0.25 * sr) / sr;
        }
    }

    // Crash: variant 1 (57) is a smaller, higher, shorter crash.
    void startCrash(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        ride = false;
        setBank(semis(p.get(CrashTune) + (h.variant == 1 ? 2.0f : 0.0f)) * h.pitch, 12, sr, vc.cymSmear);
        metal = (1.0f - vc.crashNoise) / 12.0f;
        noise = vc.crashNoise * 0.5f;
        const double dec = p.get(CrashDecay) * h.decay * (h.variant == 1 ? 0.8 : 1.0);
        const double tone = p.get(CrashTone) + h.tone - 0.6 * h.dark;
        const double ts = std::exp2((tone - 0.5) * 1.2);
        hp.reset();
        hp.set(BT::HighPass, sr, safeHz(600.0 * ts, sr), 0.707);
        bandA.reset();
        bandA.set(BT::BandPass, sr, safeHz(3800.0 * ts, sr), 0.6);
        bandB.reset();
        bandB.set(BT::HighPass, sr, safeHz(7500.0 * ts, sr), 0.707);
        lp.reset();
        lp.set(BT::LowPass, sr, safeHz(12000.0 * std::exp2((tone - 0.5) * 1.0), sr), 0.707);
        eA = eB = eF = swell = 1.0f;
        mA = t60Mul(0.6 * dec, sr);  // mids die first, the sizzle rings on
        mB = t60Mul(dec, sr);
        mF = tauMul(0.02, sr);
        swellMul = tauMul(0.015, sr);
        atk = 0.0f;
        atkStep = static_cast<float>(1.0 / (0.0015 * sr));
        bellAmt = 0.0f;
        gain = kCrashGain;
        length = samplesFor(1.5 * dec, sr);
    }

    // Ride: variant 1 (59) has extra bell.
    void startRide(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        ride = true;
        const double r = semis(p.get(RideTune) + (h.variant == 1 ? 1.0f : 0.0f)) * h.pitch;
        setBank(r * 1.35, 6, sr, 0.4f * vc.cymSmear);
        metal = (1.0f - vc.rideNoise) / 6.0f;
        noise = vc.rideNoise * 0.5f;
        const double dec = p.get(RideDecay) * h.decay;
        const double tone = p.get(RideTone) + h.tone - 0.6 * h.dark;
        const double ts = std::exp2((tone - 0.5) * 1.2);
        bandA.reset();
        bandA.set(BT::BandPass, sr, safeHz(5500.0 * ts, sr), 1.0);
        hp.reset();
        hp.set(BT::HighPass, sr, safeHz(1500.0 * ts, sr), 0.707);
        lp.reset();
        lp.set(BT::LowPass, sr, safeHz(16000.0 * std::exp2((tone - 0.5) * 0.8), sr), 0.707);
        eF = eA = 1.0f;
        mF = tauMul(0.035, sr);  // stick "ping"
        mA = t60Mul(dec, sr);    // wash
        atk = 0.0f;
        atkStep = static_cast<float>(1.0 / (0.0005 * sr));
        static constexpr double kBellRatio[4] = {1.0, 1.52, 2.07, 2.76};
        static constexpr float kBellAmp[4] = {1.0f, 0.7f, 0.5f, 0.35f};
        static constexpr double kBellDecay[4] = {0.6, 0.45, 0.35, 0.25};
        for (std::size_t k = 0; k < 4; ++k) {
            const double f = 820.0 * r * kBellRatio[k];
            bell[k].set(f, sr);
            bAmp[k] = f < 0.45 * sr ? kBellAmp[k] / 2.55f : 0.0f;
            bEnv[k] = 1.0f;
            bMul[k] = t60Mul(dec * kBellDecay[k], sr);
        }
        bellAmt = std::min(1.5f, p.get(RideBell) * (h.variant == 1 ? 2.0f : 1.0f) + (h.variant == 1 ? 0.25f : 0.0f));
        gain = kRideGain;
        length = samplesFor(1.5 * dec, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            float m = 0.0f;
            for (std::size_t o = 0; o < static_cast<std::size_t>(oscs); ++o) m += blepSquare(ph[o], inc[o]);
            if (smear > 0.0f) {
                jit = dsp::flush(jitA * jit + (1.0f - jitA) * rng.bipolar());
                m *= (1.0f - smear) + smear * jitNorm * jit;
            }
            const float src = metal * m + noise * white();
            float y;
            if (!ride) {
                const float lo = hp.process(src);
                const float a = bandA.process(lo), b = bandB.process(lo);
                y = atk * (0.8f * a * eA + 0.5f * b * eB * (1.0f - 0.7f * swell) + 0.45f * lo * eF);
                decay(eA, mA);
                decay(eB, mB);
                decay(eF, mF);
                decay(swell, swellMul);
                y = lp.process(y);
            } else {
                const float s = hp.process(bandA.process(src));
                y = lp.process(s * atk * (0.6f * eF + 0.4f * eA));
                decay(eF, mF);
                decay(eA, mA);
                if (bellAmt > 0.0f) {
                    float b = 0.0f;
                    for (std::size_t o = 0; o < 4; ++o) {
                        b += bAmp[o] * bEnv[o] * bell[o].next();
                        decay(bEnv[o], bMul[o]);
                    }
                    y += 0.25f * bellAmt * b;
                }
            }
            atk = std::min(1.0f, atk + atkStep);
            out[i] = gain * y;
        }
        age += k;
    }
};

struct RimVoice : VoiceBase {
    std::array<SineOsc, 3> osc{};
    std::array<float, 3> amp{}, env{}, mul{};
    float drive{1.0f}, driveNorm{1.0f}, clickAmt{0.0f}, clickEnv{0.0f}, clickMul{0.0f};
    dsp::Biquad hp, clickHp;

    void start(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        const double r = semis(p.get(RimTune)) * h.pitch;
        const double dec = p.get(RimDecay) * h.decay;
        float sum = 0.0f, longest = 0.0f;
        for (std::size_t k = 0; k < 3; ++k) {
            const double f = vc.rimHz[k] * r;
            osc[k].set(f, sr);
            amp[k] = (vc.rimAmp[k] > 0.0f && f < 0.45 * sr) ? vc.rimAmp[k] : 0.0f;
            env[k] = 1.0f;
            mul[k] = t60Mul(dec * std::max(vc.rimDecay[k], 0.05f), sr);
            sum += amp[k];
            longest = std::max(longest, vc.rimDecay[k]);
        }
        for (auto& a : amp) a /= std::max(sum, 1e-3f);
        drive = vc.rimDrive;
        driveNorm = 1.0f / dsp::softClip(std::min(drive, 1.5f));
        clickAmt = vc.rimNoise * (1.0f - 0.5f * h.dark);
        clickEnv = 1.0f;
        clickMul = tauMul(0.0008, sr);
        hp.reset();
        hp.set(BT::HighPass, sr, 250.0, 0.707);
        clickHp.reset();
        clickHp.set(BT::HighPass, sr, safeHz(2000.0 * std::exp2(h.tone), sr), 0.707);
        gain = kRimGain;
        length = samplesFor(1.5 * dec * longest + 0.003, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            float s = 0.0f;
            for (std::size_t o = 0; o < 3; ++o) {
                if (amp[o] <= 0.0f) continue;
                s += amp[o] * env[o] * osc[o].next();
                decay(env[o], mul[o]);
            }
            float y = dsp::softClip(drive * s) * driveNorm;
            if (clickEnv > 1e-5f) {
                y += clickAmt * clickEnv * clickHp.process(white());
                decay(clickEnv, clickMul);
            }
            out[i] = gain * hp.process(y);
        }
        age += k;
    }
};

struct CowbellVoice : VoiceBase {
    std::array<double, 2> ph{}, inc{};
    float fast{0.0f}, fastMul{0.0f}, tail{0.0f}, tailMul{0.0f}, atk{0.0f}, atkStep{0.0f};
    dsp::Biquad bp, lp;

    void start(const Hit& h, const Params& p, const Voicing& vc) {
        begin(h);
        const double sr = h.sr;
        const double r = semis(p.get(CowTune)) * h.pitch;
        ph = {rng.uniform(), rng.uniform()};
        inc = {std::min(vc.cowHz1 * r, 0.25 * sr) / sr, std::min(vc.cowHz2 * r, 0.25 * sr) / sr};
        const double dec = p.get(CowDecay) * h.decay;
        fast = tail = 1.0f;
        fastMul = tauMul(0.012, sr);  // 808: sharp initial drop, then a longer ring
        tailMul = t60Mul(dec, sr);
        atk = 0.0f;
        atkStep = static_cast<float>(1.0 / (0.0003 * sr));
        bp.reset();
        bp.set(BT::BandPass, sr, safeHz(1100.0 * r, sr), 1.0);
        lp.reset();
        lp.set(BT::LowPass, sr, safeHz(4500.0 * std::exp2(h.tone - 0.5 * h.dark), sr), 0.707);
        gain = kCowGain;
        length = samplesFor(1.5 * dec + 0.01, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            const float s = 0.5f * (blepSquare(ph[0], inc[0]) + blepSquare(ph[1], inc[1]));
            const float y = 0.9f * bp.process(s) + 0.35f * lp.process(s);
            const float e = atk * (0.6f * fast + 0.4f * tail);
            atk = std::min(1.0f, atk + atkStep);
            decay(fast, fastMul);
            decay(tail, tailMul);
            out[i] = gain * y * e;
        }
        age += k;
    }
};

struct TambVoice : VoiceBase {
    std::array<SineOsc, 6> osc{};
    std::array<float, 6> amp{}, env{}, mul{};
    std::array<int, 3> at{};
    int next{0};
    float burst{0.0f}, burstSm{0.0f}, burstMul{0.0f}, smK{0.0f};
    float shakeAtk{0.0f}, shakeStep{0.0f}, shakeTail{0.0f}, shakeMul{0.0f};
    float jingle{0.0f};
    dsp::Biquad bpShake, bpNoise, hp;

    void start(const Hit& h, const Params& p, const Voicing&) {
        begin(h);
        const double sr = h.sr;
        const double r = semis(p.get(TambTune)) * h.pitch;
        const double dec = p.get(TambDecay) * h.decay;
        jingle = p.get(TambJingle);
        float sum = 0.0f;
        for (std::size_t k = 0; k < 6; ++k) {
            const double f = kJingleHz[k] * r * (1.0 + 0.015 * rng.bipolar());
            osc[k].set(f, sr);
            const float a = 0.5f + 0.5f * rng.uniform();
            amp[k] = f < 0.45 * sr ? a : 0.0f;
            sum += amp[k];
            env[k] = 1.0f;
            mul[k] = t60Mul(dec * (1.0 - 0.08 * static_cast<double>(k)), sr);
        }
        for (auto& a : amp) a /= std::max(sum, 1e-3f);
        at = {0, static_cast<int>((0.005 + 0.004 * rng.uniform()) * sr), static_cast<int>((0.011 + 0.007 * rng.uniform()) * sr)};
        next = 0;
        burst = burstSm = 0.0f;
        burstMul = tauMul(0.004, sr);
        smK = static_cast<float>(1.0 - std::exp(-1.0 / (0.00015 * sr)));
        shakeAtk = 0.0f;
        shakeStep = static_cast<float>(1.0 / (0.006 * sr));
        shakeTail = 1.0f;
        shakeMul = t60Mul(dec, sr);
        const double bright = std::exp2(h.tone - 0.6 * h.dark);
        bpShake.reset();
        bpShake.set(BT::BandPass, sr, safeHz(7200.0 * r * bright, sr), 0.9);
        bpNoise.reset();
        bpNoise.set(BT::BandPass, sr, safeHz(9000.0 * r * bright, sr), 0.8);
        hp.reset();
        hp.set(BT::HighPass, sr, safeHz(3000.0 * r, sr), 0.707);
        gain = kTambGain;
        length = samplesFor(1.5 * dec + 0.02, sr);
    }

    void render(float* out, int n) noexcept {
        const int k = live(out, n);
        for (int i = 0; i < k; ++i) {
            if (next < 3 && age + i >= at[static_cast<std::size_t>(next)]) burst = 1.0f - 0.25f * static_cast<float>(next++);
            burstSm = dsp::flush(burstSm + (burst - burstSm) * smK);  // ~0.15 ms attack: click-free re-excitation
            decay(burst, burstMul);
            const float nz = white();
            float y = 0.0f;
            if (jingle < 1.0f) {
                y += (1.0f - jingle) * 1.4f * bpShake.process(nz) * shakeAtk * shakeTail;
                shakeAtk = std::min(1.0f, shakeAtk + shakeStep);
                decay(shakeTail, shakeMul);
            }
            if (jingle > 0.0f) {
                float jn = 0.0f;
                for (std::size_t o = 0; o < 6; ++o) {
                    jn += amp[o] * env[o] * osc[o].next();
                    decay(env[o], mul[o]);
                }
                y += jingle * (jn * (0.35f + 0.65f * burstSm) + 1.2f * bpNoise.process(nz) * burstSm);
            }
            out[i] = gain * hp.process(y);
        }
        age += k;
    }
};

// ------------------------------------------------------------------------------------------
// The instrument

struct Mapped {
    Piece piece;
    int variant;
};

bool mapPitch(int pitch, Mapped& m) noexcept {
    switch (pitch) {
        case 35: case 36: m = {Kick, 0}; return true;
        case 37: m = {Rim, 0}; return true;
        case 38: m = {Snare, 0}; return true;
        case 40: m = {Snare, 1}; return true;
        case 39: m = {Clap, 0}; return true;
        case 42: m = {Hat, 0}; return true;
        case 44: m = {Hat, 1}; return true;
        case 46: m = {Hat, 2}; return true;
        case 41: m = {Tom, 0}; return true;
        case 43: m = {Tom, 1}; return true;
        case 45: m = {Tom, 2}; return true;
        case 47: m = {Tom, 3}; return true;
        case 48: m = {Tom, 4}; return true;
        case 50: m = {Tom, 5}; return true;
        case 49: m = {Crash, 0}; return true;
        case 57: m = {Crash, 1}; return true;
        case 51: m = {Ride, 0}; return true;
        case 59: m = {Ride, 1}; return true;
        case 54: m = {Tamb, 0}; return true;
        case 56: m = {Cowbell, 0}; return true;
        default: return false;
    }
}

constexpr int kChokeNone = -1;
constexpr int kChokeAll = -2;

class DrumSynth final : public Instrument {
public:
    DrumSynth() : params_(specs()) {}

    void configure(const json& j) override {
        if (!j.is_null() && !j.is_object()) throw ConfigError("drums: params must be a JSON object");
        if (j.is_object()) {
            for (const char* key : {"kit", "hat.model"}) {  // Params accepts bools/fractions for choices
                if (!j.contains(key)) continue;
                const json& v = j.at(key);
                if (v.is_boolean() || (v.is_number_float() && v.get<double>() != std::floor(v.get<double>())))
                    throw ConfigError(std::string("drums: '") + key + "' must be a choice name (e.g. \"" +
                                      (key[0] == 'k' ? "909" : "808") + "\") or an integer index");
            }
        }
        Params p(specs());
        if (j.is_object() && j.contains("kit")) {
            json kitOnly = json::object();
            kitOnly["kit"] = j.at("kit");
            p.configure(kitOnly, "drums");
        }
        const int kit = static_cast<int>(p.get(PKit) + 0.5f);
        json kitDefaults = json::object();
        for (const auto& row : kKitTable) kitDefaults[specs()[static_cast<std::size_t>(row.id)].name] = row.v[kit];
        p.configure(kitDefaults, "drums (kit defaults)");
        p.configure(j, "drums");
        params_ = std::move(p);
        level_.snap(kOutputTrim * dsp::dbToGain(P(PLevel)));
    }

    void prepare(const RenderContext& ctx) override {
        sr_ = ctx.sampleRate;
        rng_.reseed(ctx.seed ^ 0xD12C5A7E3B9F4861ull ^ dsp::hashString("drums"));
        smoothK_ = static_cast<float>(1.0 - std::exp(-1.0 / (kGainTau * sr_)));
        level_.prepare(sr_, kGainTau, kOutputTrim * dsp::dbToGain(P(PLevel)));
        order_ = 0;
        const int kit = std::clamp(static_cast<int>(P(PKit) + 0.5f), 0, KitCount - 1);
        for (int pc = 0; pc < PieceCount; ++pc) {
            trim_[static_cast<std::size_t>(pc)] = dsp::dbToGain(kKitTrimDb[kit][pc]);
            if (kWidthId[pc] == IdCount) continue;
            auto& w = width_[static_cast<std::size_t>(pc)];
            w.prepare(sr_, kGainTau, P(kWidthId[pc]));
            decor_[static_cast<std::size_t>(pc)].prepare(
                sr_, pc == Clap ? std::array<double, 4>{1.3, 2.3, 3.7, 5.3} : std::array<double, 4>{1.7, 2.9, 4.3, 6.1});
        }
        forAll([](auto& pool) {
            for (auto& v : pool) v.active = false;
        });
    }

    bool setParam(std::string_view name, float value) override {
        if (!params_.set(name, value)) return false;
        const int id = params_.index(name);
        if (id == PLevel) {
            level_.setTarget(kOutputTrim * dsp::dbToGain(P(PLevel)));
            return true;
        }
        for (int pc = 0; pc < PieceCount; ++pc) {
            if (id != kLevelId[pc] && id != kPanId[pc] && id != kWidthId[pc]) continue;
            if (id == kWidthId[pc]) {
                auto& w = width_[static_cast<std::size_t>(pc)];
                if (decor_[static_cast<std::size_t>(pc)].hold > 0) w.setTarget(P(kWidthId[pc]));
                else w.snap(P(kWidthId[pc]));  // nothing ringing: the next hit starts at the new width
            }
            const Piece piece = static_cast<Piece>(pc);
            forPiece(piece, [&](auto& pool) {
                for (auto& v : pool)
                    if (v.active) setTargets(v, piece);
            });
            break;
        }
        return true;
    }

    void noteOn(int, int pitch, float velocity) override {
        Mapped m{};
        if (!mapPitch(pitch, m)) return;
        const float vel = std::clamp(velocity, 0.0f, 1.0f);
        const float sens = P(PVelocity), hum = P(PHumanize);
        Hit h;
        h.sr = sr_;
        h.variant = m.variant;
        h.dark = sens * (1.0f - vel);
        h.human = hum;
        h.trim = trim_[static_cast<std::size_t>(m.piece)];
        // Always draw the same number of values so the hit sequence does not depend on humanize.
        const float rp = rng_.bipolar(), rd = rng_.bipolar(), rl = rng_.bipolar(), rt = rng_.bipolar();
        h.pitch = semis(0.25f * hum * rp);
        h.decay = 1.0f + 0.12f * hum * rd;
        h.tone = 0.1f * hum * rt;
        h.seed = rng_.next();
        const float hitGain = std::pow(vel, 2.0f * sens) * dsp::dbToGain(2.0f * hum * rl);
        const Voicing& vc = kVoicing[std::clamp(static_cast<int>(P(PKit) + 0.5f), 0, KitCount - 1)];

        switch (m.piece) {
            case Kick: {  // one kick "circuit": a new hit fades the ringing one (no sub phase smear)
                auto& v = claim(kick_, 4, kChokeAll, 0.010, 0.010);
                v.start(h, params_, vc);
                finish(v, Kick, hitGain);
                break;
            }
            case Snare: {
                auto& v = claim(snare_, 4, kChokeNone, 0.0, 0.008);
                v.start(h, params_, vc);
                finish(v, Snare, hitGain);
                break;
            }
            case Clap: {
                auto& v = claim(clap_, 4, kChokeNone, 0.0, 0.008);
                v.start(h, params_, vc);
                finish(v, Clap, hitGain);
                break;
            }
            case Hat: {  // one physical hi-hat: any hat hit chokes the ringing ones (open hat choke)
                auto& v = claim(hat_, 4, kChokeAll, 0.007, 0.007);
                v.start(h, params_, vc);
                finish(v, Hat, hitGain);
                break;
            }
            case Tom: {  // each tom rings independently; re-hitting the same tom restarts it
                auto& v = claim(tom_, 6, m.variant, 0.012, 0.012);
                v.start(h, params_, vc);
                finish(v, Tom, hitGain);
                break;
            }
            case Crash: {
                auto& v = claim(crash_, 4, kChokeNone, 0.0, 0.030);
                v.startCrash(h, params_, vc);
                finish(v, Crash, hitGain);
                break;
            }
            case Ride: {
                auto& v = claim(ride_, 4, kChokeNone, 0.0, 0.030);
                v.startRide(h, params_, vc);
                finish(v, Ride, hitGain);
                break;
            }
            case Rim: {
                auto& v = claim(rim_, 3, kChokeNone, 0.0, 0.005);
                v.start(h, params_, vc);
                finish(v, Rim, hitGain);
                break;
            }
            case Cowbell: {
                auto& v = claim(cow_, 4, kChokeAll, 0.006, 0.006);
                v.start(h, params_, vc);
                finish(v, Cowbell, hitGain);
                break;
            }
            case Tamb: {
                auto& v = claim(tamb_, 4, kChokeNone, 0.0, 0.010);
                v.start(h, params_, vc);
                finish(v, Tamb, hitGain);
                break;
            }
            case PieceCount: break;
        }
    }

    void noteOff(int) override {}  // one-shots

    void process(float* left, float* right, int frames) override {
        std::fill(left, left + frames, 0.0f);
        std::fill(right, right + frames, 0.0f);
        for (int off = 0; off < frames; off += kChunk) {
            const int n = std::min(kChunk, frames - off);
            for (int pc = 0; pc < PieceCount; ++pc) {
                const auto piece = static_cast<Piece>(pc);
                float* side = kWidthId[pc] == IdCount ? nullptr : side_.data();
                bool any = false;
                forPiece(piece, [&](auto& pool) { any = mix(pool, left + off, right + off, n, side); });
                if (side) addSide(piece, any, left + off, right + off, n);
            }
        }
        for (int i = 0; i < frames; ++i) {
            const float g = level_.next();
            left[i] = std::isfinite(left[i]) ? left[i] * g : 0.0f;
            right[i] = std::isfinite(right[i]) ? right[i] * g : 0.0f;
        }
    }

    bool idle() const override {
        bool any = false;
        for (const auto& d : decor_) any = any || d.hold > 0;
        forAll([&](const auto& pool) {
            for (const auto& v : pool) any = any || v.active;
        });
        return !any;
    }

    const std::vector<ParamSpec>& paramSpecs() const override { return specs(); }

    float value(std::string_view name) const {
        const int i = params_.index(name);
        return i < 0 ? std::numeric_limits<float>::quiet_NaN() : params_.get(i);
    }

private:
    float P(Id id) const { return params_.get(id); }

    template <class F>
    void forPiece(Piece piece, F&& f) {
        switch (piece) {
            case Kick: f(kick_); break;
            case Snare: f(snare_); break;
            case Clap: f(clap_); break;
            case Hat: f(hat_); break;
            case Tom: f(tom_); break;
            case Crash: f(crash_); break;
            case Ride: f(ride_); break;
            case Rim: f(rim_); break;
            case Cowbell: f(cow_); break;
            case Tamb: f(tamb_); break;
            case PieceCount: break;
        }
    }
    template <class F>
    void forAll(F&& f) {
        for (int pc = 0; pc < PieceCount; ++pc) forPiece(static_cast<Piece>(pc), f);
    }
    template <class F>
    void forAll(F&& f) const {
        f(kick_);
        f(snare_);
        f(clap_);
        f(hat_);
        f(tom_);
        f(crash_);
        f(ride_);
        f(rim_);
        f(cow_);
        f(tamb_);
    }

    // Finds a slot for a new hit. `choke`: kChokeNone, kChokeAll or a variant whose ringing voices
    // are faded out over chokeSec. Beyond `maxPoly` sounding voices the oldest is faded (stealSec).
    template <class V, std::size_t N>
    V& claim(std::array<V, N>& pool, int maxPoly, int choke, double chokeSec, double stealSec) {
        for (auto& v : pool)
            if (v.active && (choke == kChokeAll || (choke >= 0 && v.variant == choke))) v.startFade(sr_, chokeSec);
        for (;;) {
            int sounding = 0;
            V* oldest = nullptr;
            for (auto& v : pool) {
                if (!v.active || v.fading) continue;
                ++sounding;
                if (!oldest || v.order < oldest->order) oldest = &v;
            }
            if (sounding < maxPoly || !oldest) break;
            oldest->startFade(sr_, stealSec);
        }
        V* slot = nullptr;
        for (auto& v : pool)
            if (!v.active) return v;
        for (auto& v : pool)  // every slot busy fading: reuse the quietest one
            if (!slot || v.fade < slot->fade) slot = &v;
        return *slot;
    }

    void setTargets(VoiceBase& v, Piece piece) const {
        float lvl = dsp::dbToGain(P(kLevelId[piece]));
        if (kWidthId[piece] != IdCount) {  // constant power: mid scaled by 1/sqrt(1 + w^2), side by w/sqrt(1 + w^2)
            const float w = P(kWidthId[piece]);
            lvl /= std::sqrt(1.0f + w * w);
        }
        float gl = 0.0f, gr = 0.0f;
        dsp::panGains(P(kPanId[piece]) + v.panOffset, gl, gr);
        v.tgl = lvl * gl;
        v.tgr = lvl * gr;
    }

    void finish(VoiceBase& v, Piece piece, float hitGain) {
        v.gain *= hitGain * (piece == Snare ? 1.0f : trim_[static_cast<std::size_t>(piece)]);  // snare: inside
        v.order = order_++;
        setTargets(v, piece);
        v.gl = v.gl1 = v.tgl;
        v.gr = v.gr1 = v.tgr;
    }

    // Adds the pool's voices to left/right; with `side`, also writes their mono sum there (for the width).
    // Returns true if any voice was active.
    template <class V, std::size_t N>
    bool mix(std::array<V, N>& pool, float* left, float* right, int n, float* side) {
        bool any = false;
        if (side) std::fill(side, side + n, 0.0f);
        for (auto& v : pool) {
            if (!v.active) continue;
            any = true;
            v.render(tmp_.data(), n);
            for (int i = 0; i < n; ++i) {
                v.gl1 += (v.tgl - v.gl1) * smoothK_;
                v.gr1 += (v.tgr - v.gr1) * smoothK_;
                v.gl += (v.gl1 - v.gl) * smoothK_;
                v.gr += (v.gr1 - v.gr) * smoothK_;
                float s = tmp_[static_cast<std::size_t>(i)];
                if (v.fading) {
                    v.fade = std::max(0.0f, v.fade - v.fadeStep);
                    s *= v.fade;
                }
                left[i] += s * v.gl;
                right[i] += s * v.gr;
                if (side) side[i] += s * std::min(v.gl, v.gr);  // = mid at centre, fades out when hard-panned
            }
            if (v.age >= v.length || (v.fading && v.fade <= 0.0f)) v.active = false;
        }
        return any;
    }

    // Sample-accurate (independent of the block size): the decorrelator runs while its input is non-zero
    // and for holdLen samples after, then parks with the width smoother settled.
    void addSide(Piece piece, bool active, float* left, float* right, int n) {
        auto& d = decor_[static_cast<std::size_t>(piece)];
        auto& w = width_[static_cast<std::size_t>(piece)];
        if (!active && d.hold <= 0) return;
        for (int i = 0; i < n; ++i) {
            const float x = side_[static_cast<std::size_t>(i)];
            if (x != 0.0f) d.hold = d.holdLen;
            if (d.hold <= 0) continue;
            const float s = d.process(x) * w.next();  // x already carries 1/sqrt(1 + w^2)
            left[i] += s;
            right[i] -= s;
            if (--d.hold == 0) w.snap(w.target());
        }
    }

    Params params_;
    double sr_{48000.0};
    dsp::Rng rng_;
    std::uint32_t order_{0};
    float smoothK_{0.01f};
    Smooth2 level_;
    std::array<KickVoice, 6> kick_;
    std::array<SnareVoice, 8> snare_;
    std::array<ClapVoice, 6> clap_;
    std::array<HatVoice, 8> hat_;
    std::array<TomVoice, 10> tom_;
    std::array<CymbalVoice, 6> crash_;
    std::array<CymbalVoice, 6> ride_;
    std::array<RimVoice, 5> rim_;
    std::array<CowbellVoice, 5> cow_;
    std::array<TambVoice, 6> tamb_;
    std::array<float, kChunk> tmp_{}, side_{};
    std::array<float, PieceCount> trim_{};
    std::array<Smooth2, PieceCount> width_{};
    std::array<Decorrelator, PieceCount> decor_{};  // only the pieces with a width use theirs
};

}  // namespace

std::unique_ptr<Instrument> makeDrumSynth() { return std::make_unique<DrumSynth>(); }

float drumSynthParam(const Instrument& drums, std::string_view name) {
    const auto* d = dynamic_cast<const DrumSynth*>(&drums);
    return d ? d->value(name) : std::numeric_limits<float>::quiet_NaN();
}

}  // namespace as
