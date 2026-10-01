# The Drummer Speaks - sound design

| track | sound | why |
|---|---|---|
| drums | `sampled/big_rusty_kit` (Karoryfer Big Rusty, CC0) `.but(level=1.0, restrike=6)` in the rock_band drum chain | the best solo kit installed: 14 velocity layers x 4 round robins on snare / toms / kick (10 on the snare centre), close + overhead mics (snare bottom -4, OH -2), FOUR toms (14" 15" 18" 22": a tom melody has four notes), snare centre / edge (39) / rimshot (40) / side stick, chokes on 88 / 89 / 90 (crash / ride / china: the final hit is grabbed), a variable hi-hat on 46 whose opening is the live `dynamics` param (the SFZ's CC4 imported live: the drummer's hat lane opens and closes it stroke by stroke) and a foot splash (56). `restrike=6`: the sampler's re-strike damping - a drum struck again damps its own ringing voices, so the 16th-triplet tom runs, the double-bass and the press roll do not pile up boom (sampled, every hit layers fully: ~+5-7 dB of ring on a fast run). level 1.0 = the band's own Big Rusty level (the patch's 8.0 is its -18 LUFS calibration alone). Other candidates: Virtuosity (36 layers, but two toms), Crocell / Muldjord (up to 24 / 13 round robins, but no live hat and no chokes on the GM map), MF Natural (per-hand samples via `Kit.hand_keys`, but two toms and an NC licence). |
| drum chain | rock_band: eq (+1.5 dB at 70 Hz, -2.5 at 150, -2 at 420, +1 at 4.5 kHz) -> trim, output `drum_bus` (4:1 at -22 dB, 12 ms attack, **mix 0.45 = parallel compression**, tape saturation, eq), sends `room` -5 (Voxengo drum room IR: the room mics), `plate` -20 | a kit in a room, its transients intact (the parallel bus lifts the body and the ghost notes without flattening the accents) |
| gated (bus) | `bus/gated` (AMS-style gated burst: 280 ms hold, cut in 25 ms) | the 80s tom break: the kit's send opens to -4 dB only for the `gated_toms` move's two bars (the window from `part.moves`), else -60 |
| mallets | `sampled/big_rusty_mallets` (the same kit, soft mallets: CC 25 / 26 / 28 = 110), into the drum bus, room -8 | the opening cymbal swell: mallet rolls on the crash from a whisper |
| bass | rock_band picked Growlybass (tube drive, compressor), ducked 5 dB under the kick | the riff's weight |
| gtr_l / gtr_r | rock_band DI guitars: FSBS -> Marshall 4x12 (L), Emily SG -> 2x12 crunch (R) | the riff as two takes, palm mutes on the short notes |
| keys | rock_band setBfree organ, tube drive, Leslie-style tremolo (rate automated: slow under the riff, fast in the choruses, slowing as the solo starts) | pads and pushes, the Em chord that rings away under the solo's first bars |
| lead | `layered/hero_guitar` via `hero()` (rock: no bed duck; carve on the organ, dips on the rhythm guitars; ride +1 dB in the head / chorus sections), `hero_guitar.play` (vibrato on the long notes, echo throws) | the head: a singing driven Strat with body (no beepy lead) |
| hall | `s.hall()` | the lead patch's and the mallets' hall send |

Credits: Big Rusty Drums, Growlybass, Emilyguitar (Karoryfer, CC0); FreePats FSBS guitar, setBfree organ (CC0);
Voxengo IM Reverbs; Lexicon 224XL plate (Little Devil); the guitar cabinet IRs (see `out/credits.txt`).
