# SOUND - Ashes and Chandeliers

One hall for everything that is "the orchestra" (the film orchestra preset's Musikverein IR x1.5, ~2.3 s, id `hall`),
the rock band's own rooms for the band (drum room IR, 224XL plate, echo), and the heroes' own spaces (the hero
piano's plate, the hero guitars' echo + plate). Master: the film orchestra chain (1.1 kHz / 400 Hz dips, +4 dB air
above 7.5 kHz, 1-2 dB slow glue, -1.2 dBTP limiter); the rock band preset kept it (`info['master'] = 'kept'`).

| role | sound | range | chain + sends | why | checks |
|---|---|---|---|---|---|
| piano (hook, Part I / coda; staccato in II; 8ths in IV) | `sampled/hero_piano` (Salamander, key split, hammers 0.5), gain -3 | LH C1-E4, RH G4-C6 | the patch chain (eq, catch + glue comp, tape, width, Dimension-D); plate -7, hall -16; echo throws in the coda | "lieber eine hohe Piano-Taste": the ballad hero, warm (no 2-5 kHz push: "es klingt hart" was sound design) | note dynamics per phrase (report), bed vs lead in Part I |
| violins1 / violins2 / violas / cellos / basses | film orchestra (SSO 4.0 Performance sections, VPO re-looped sustains), live dynamics lane | preset ranges | preset eq / width / seating; hall -6..-5.5; violins2 + violas carved under the piano (2 dB duck, -1.5 dB at 2.5 kHz) | real sections with keyswitched staccato / pizzicato / tremolo / marcato | clicks, `low_end_not_mono` |
| winds (flutes, oboes, clarinets, bassoons), harp | film orchestra | sweet spots | preset | masque colour, the finale's flute octave | |
| brass (horns, trumpets, trombones, low_brass, tuba) | film orchestra (SSO) | sweet spots | preset, hall -3..-3.5 | stabs (marcato), the ascent swell, finale chords, riff2 doubling | |
| timpani / percussion / taiko | film orchestra (VSCO timpani hit / roll, VSCO GM-style percussion, MuseScore taiko) | D2-C3 / keys 36-81 | preset | rolls into the fermatas, the tam-tam (46), cymbal rolls (48), crash + bass drum at arrivals | |
| choir (large chorus) | film orchestra SSO large chorus 'aah' | C3-A5 | preset, hall -3 | tutti harmony in calls, ascent, finale, summit | loop-seam clicks |
| choir_m | `sampled/choir_male` (VPO), pan -0.3, gain -2, -2.5 dB at 1 kHz | G2-F#4 | eq; hall -6 | the calls (f / ff), the low entries of the ascent, the finale's open fifths | dynamics lane |
| choir_f | `sampled/choir` (VPO female 'ah'), pan +0.3, gain -5, -3 dB at 1 kHz | F3-A5 | eq; hall -8 | the answers (p / pp), the waltz 'ah' on 2 and 3, high entries | |
| choir_oh | `sampled/choir_oh` (NBO 'oh', clean loops), gain -8 | C3-C6 | eq; hall -6; carved under the piano | the soft pads under the middle, the fall and the coda (exposed pp: clean loops) | |
| kit | rock_band Big Rusty (close + OH), id `kit` | GM | preset drum bus (parallel comp, tape), room -5, plate -20 | the band | |
| bass | rock_band picked Growlybass, tube drive | E1-E3 | preset; ducks 5 dB under the kick | | |
| gtr_l / gtr_r | rock_band `gain='high'`: FSBS DI -> metal 4x12 (L), Emily SG -> hot crunch 2x12 (R) | E2-E4 power chords | preset amps; + a -2 dB dip at 1.9 kHz and a 2.5 dB duck keyed by gtr1 | "heavy and driving": the wall under the guitar orchestra | |
| organ | rock_band Leslie organ, id `organ` | A3-E5 | preset; tremolo (Leslie) rate automated 1 -> 6.2 Hz in anthem2 / solo; dip + duck as the guitars | | |
| gtr1 (guitar orchestra top / solo) | `layered/hero_guitar_heavy`, centre, gain +2.5 (-2 dB ride in the finale), -3 dB at 3.4 kHz, -2 dB at 1.1 kHz | E4-E6 | the hero chain (velocity zones, sustainer, Plexi lead, 4x12, tape, microshift, own echo); hall -13, plate -18; echo throws | held peaks keep singing (the double) | lead dynamics (velocity 70-124, touch) |
| gtr2 / gtr3 (harmony) | `layered/hero_guitar`, pan -0.38 / +0.38, gain +1.5 / +0.5, -2 dB at 1.1 and 3.4 kHz | C4-G5 | the hero chain; hall -12, plate -18 | a guitar orchestra in thirds: different sides, a bit lower than the top voice | |

Licenses (credits.txt): Salamander CC-BY 3.0 (credit Alexander Holm), SSO Sampling Plus 1.0 (credit), VPO royalty-free,
VSCO 2 CE CC0, NBO 2 CC-BY-SA 4.0 (credit), Big Rusty / Growlybass / Emily CC0, FSBS CC0, MuseScore General MIT,
Voxengo IM Reverbs (no redistribution), 224XL IRs (license unclear), Jester IRs; SampleRadar lead multisample (heavy
hero double: royalty-free for music, no redistribution).

## Production moves and why (measured over 5 renders)

- Render 1: rock sections (-15.6 LUFS) were quieter than the operatic calls (-15.0) and the ascent (-12.3); the
  masque sank to -24.9; the female choir peaked the mids (23 % of 0.8-2.5 kHz); low end not mono in break / summit;
  the band's echo bus idle.
- Moves: band faders up (kit +0.5, bass +2, rhythm guitars +1.5, organ +3), the guitar orchestra up (+3.5 / +5.5 /
  +5.5: the harmony voices were 6-7 dB under the top voice), female choir -3 dB and its finale dynamics 0.4-0.65,
  mid cuts (1 kHz) on choirs and harmony guitars, presence cuts (3.2-3.4 kHz) on gtr1, violins1, violins2, trumpets
  and the rhythm guitars; the masque's faders +4..+10 dB inside it (flutes, pizzicato strings, bassoons, harp, the
  choir's staccato 'ah'); the finale's weight: bass guitar +3, basses +3, tuba +4, cellos +1.5, gtr1 / choir -2,
  violins1 -1.5; the taikos' lows centred (width monobass 150), and one master width stage (monobass 120 Hz) before
  the limiter (hard-panned power chords: lows correlation 0.85 -> 0.96); gtr1 feeds the band's dotted-8th echo
  (-14 dB in the anthems, -6 dB in the solo; the echo return +9 dB): Brian-May-style repeats.
- Result (render 4): rock -14.9..-12.9 LUFS above the opera (calls -15.8), finale -11.2 / summit -10.0 the peak,
  echo audible, lows mono, 0 clicks; mid / presence still a little over the film reference (+4.6 / +3.6 dB, limits
  +4 / +3): render 5 cuts 1 kHz on the male choir and the harmony guitars and 3.2 kHz on violins2 and trumpets.

## Revision (A&R round 1)

- **Choirs that speak** (A&R #4): measured the cause - the VPO SFZ's amp envelope has `ampeg_attack=0.625` with
  `ampeg_vel2attack=-0.625` (0.4 s at velocity 40), and the recordings themselves take 50-180 ms to reach -3 dB.
  choir_m / choir_f are now `patches.get(...).but(start=100)` (100 ms into the sample) and their lines are played at
  velocity 120 (~40 ms attack) with the written dynamics on `instrument.expression` (e = vel / 120, moved over the
  80 ms before each onset). The ascent's entries keep the slow swell (expression back to 1 before the ascent).
  Result (calls stems): 40 ms after an upbeat onset the calls are at -7..-9 dB of full level (was -26..-31), the
  answers -9..-14 (was -39 / -40).
- **Guitar orchestra wider** (A&R #3): gtr2 / gtr3 pan +-0.38 -> +-0.65 (width >150 Hz anthem 23 -> 31.7 %, anthem2
  28 -> 40.3 %).
- **Ballad piano air** (A&R #6): `eq` 'air' high shelf +5 dB at 7.5 kHz after the hero chain (no 2-5 kHz push): intro
  air -36.1 -> -31.2 dB vs film; only partial, the softened-hammer grand has little above 7 kHz.
- **Removed**: the finale's 'weight' gainDb lanes (bass / basses / tuba up, gtr1 / choir / violins1 down) - they
  buried the tune. Added: `s.carve(violas, trombones, key=gtr1, freq=450, depth=3)`; the riff's taiko hit (it masked
  the kit's sub) is not used - the concert bass drum marks the downbeat.
- Masked clicks: choir_f adds 2 low-level loop seams in the finale's held notes (-41 dBFS, masked); 0 in the mix.
