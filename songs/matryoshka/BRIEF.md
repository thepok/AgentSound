# Matryoshka - brief

## The wish

> "Erfinde etwas Neues, deine eigene Claude-Opus-Erfindung, noch nie gehört und trotzdem potenziell gefällig."
> (Invent something new, your own invention, never heard before and yet potentially pleasing.)

The invention (decided by the main agent, developed here): **Matryoshka pop - a self-similar song.** One four-note
hook is the whole song, at three time scales at once, like nested dolls. The listener should, at the end, feel
"oh - it was all the same four notes".

## The invention: one hook, three (four) clocks

The hook: **C - A - F - G**, rhythm **dotted quarter, 8th, quarter, quarter** (1.5 + 0.5 + 1 + 1 beats = one bar).
Chosen because the same four notes are, in C major, the roots of the most familiar pop progression I - vi - IV - V,
and as key centres they make a natural journey through the closest related keys: home (C major) -> its shadow (A
minor, the relative) -> warmth (F major, the subdominant) -> lift (G major, the dominant, a truck-driver whole step up
from F) -> home again. The key journey is itself a I - vi - IV - V - I cadence, so the whole song is one enormous
chord progression that resolves in the coda.

| scale | factor | what the four notes are | what the rhythm (1.5 : 0.5 : 1 : 1) is |
|---|---|---|---|
| 1. melody | x1 (1 bar) | the hook on the hero piano: C6 A5 F5 G5 | the melody's rhythm |
| 2. harmony | x4 (4 bars) | the chord roots of every 4-bar phrase: C / Am / F / G (in each key its own 1-6-4-5) | the harmonic rhythm: 6 + 2 + 4 + 4 beats; the kick's accents (1, &2, 3) |
| 3. form | x64 (64 bars) | the key centres of the four main sections: C major, A minor, F major, G major | the section lengths: 24 + 8 + 16 + 16 bars |
| coda | x1 + x4 + x16 | the hook in the melody, as a sustained bass / cello line (x4) and as a choir line (x16: C 6 bars, A 2, F 4, G 4) at the same time, all converging on G and resolving to one C chord | all three rhythms at once |

Pivots (smooth, common-tone / leading-tone, the hook's root kept in the bass where possible):
C -> Am: `G  E7/G#` (the bass climbs G - G# - A); Am -> F: `E  C7/E` (the E stays in the bass and rises to F);
F -> G: `C  D` (Bb - C - D - G, the epic climb); G -> C: `Dm7  G7` (the D root kept, ii - V - I home).

Transformations used as variation (all of the same four notes): the diatonic inversion (C E G F, a rising
"question") is the verse tune and later the violins' counter-melody; the hook in each key's own degrees; an
upward-leap form (C5 -> A5: the 6th leap) for the big choruses; compressed harmony in the build (the cycle at x2,
then x1: the whole band hits the hook's rhythm with the hook's own chords under each note).

## Frame

- Genre: warm cinematic instrumental pop, analysis profile `pop` (`ANALYSIS = {'profile': 'pop'}`).
- 100 BPM, 4/4, straight 8ths. Keys C major -> A minor -> F major -> G major -> C major.
- Form (86 bars, ~3:27 + tail): `intro 4 | verse1 8 | build 4 | chorus1 8 | turn 4 (= section I, C, 24) |
  minor 8 (= II, Am) | verse2 8 | chorus2 8 (= III, F, 16) | chorus3 8 | chorus4 8 (= IV, G, 16) | coda 16 | end 2`.
- Energy arc: intro 1 -> verse1 2 -> build 3 -> chorus1 4 -> turn 3 -> minor 1.5 -> verse2 2.5 -> chorus2 3.5 ->
  chorus3 4.5 -> chorus4 5 -> coda 2 rising to 4.5 -> end (one ringing chord).

## The hook's sound

- The hero piano (`hero(s.track('piano', 'hero/piano_pop'), genre='pop', ...)`): the bright high sampled Salamander,
  the hook C5-C7, played by the pianist (`pianist.arrange`: octaves / sixths / thirds under the melody, restrikes,
  budgeted ornaments, touch() arcs). No synth lead anywhere; a DX glass layer an octave up joins the piano only for
  the final statements (chorus4, coda) - the `layered/piano_glass_lead` idea, faded in.
- Bed: VPO string section, a soft Juno pad, the VPO mixed choir "ah" (x16 line + chorus4), the solo cello (the hook
  in A minor, the x4 line in the coda, played by the wind/bow player `hornist`, family strings), violins (the
  inversion as counter-melody).
- Rhythm: pop_band preset (Chart Kit + tonic sub, perc, Growlybass finger bass, plate / bright hall / echo, master)
  without its keys / pluck / lead; drums by the drummer (pop), the bass by the bassist (pop, locked to the
  hook-rhythm kick `x.....x.x.......`).

## References

none (an invention); genre sanity against the pop profile. Spirit: Coldplay piano pop ("Clocks", "Fix You" lifts),
Hans Zimmer's layered-scale endings - for mood only, no reference audio.

## HUMAN_FEEDBACK checklist (the A&R ticks these)

- [ ] A song, not a loop: form, tension/release, the hook returns and grows, variation between repeats, fills.
      (Special risk here: one hook everywhere - it must never feel like a loop: keys, orchestration, register, forms.)
- [ ] No beepy lead: the hook on the bright high sampled hero piano, octave-doubled / voiced.
- [ ] Lead in front: bed >= 2-3 dB under the piano in its sections (report `bedVsLeadDb`).
- [ ] Real dynamics: `flat_dynamics` = 0; phrase arcs; first statement soft, last strongest.
- [ ] Played, not keyboard-like: pianist, drummer, bassist, hornist (cello); rolled chords, pedal.
- [ ] Piano: harmonized, decorated, fast two-key figures budgeted; warm, not hard.
- [ ] Hero sound on the hook: present, not just loud.
- [ ] Produced, not Gameboy: rooms, echoes, width, full low end.
- [ ] `clicks` = 0, `silent_notes` = 0, true peak <= -1 dBTP.
- [ ] The brief's own targets: the three scales audible in the coda; 3:00-3:45; warm, lifting.

## Targets

- pop profile: -11..-8 LUFS-I (a cinematic piano song may sit at the soft end: aim ~-10), TP <= -1 dBTP, LRA 4-8 LU
  (the minor section and the coda start may dip), chorus 2-4 LU over the verse, width above 150 Hz 40-70 %, reverb
  7-16 LU under the mix.
- Mixer profile `pop`; master platform `auto`.

## Log

- producer: brief written (the invention, the scales table, pivots, frame, form, sound plan, checklist).
- arranger: 12 sections / 86 bars (ARRANGEMENT.md): pianist (sparse / ballad / straight, LH tenths / shell in the
  quiet parts, octaves / 6ths / 3rds in the hooks, climax in chorus4 and the coda's last 8 bars), drummer pop (kick
  locked to the bass on the hook's onsets), bassist pop (kick grid x.....x.x.......), bow player for the cello and
  the violins; the build zooms the harmony x4 -> x2 -> x1. Open: none.
- sound-designer (SOUND.md): hero/piano_pop + glass layer, VPO strings / violins / mixed choir, SSO solo cello,
  pop_band rhythm section; pass 1: bass -5 dB + 1 kHz dip, cello -7 dB + hp, piano -2 dB + 300 Hz dip, violins bowed.
- mix-engineer (MIX.md): trims from mix (drums / perc -2.5, bed -0.5), rides for the concept (cello in minor / coda,
  choir in the coda), violins ducked under the piano, pad / strings / cello dips. 0 report warnings.
- mastering-engineer (MASTER.md): +2 dB low shelf, -1.8 dB @ 1.25 kHz, limiter ceiling -1.2, a drive arc per section.
  -10.7 LUFS-I, TP -1.20 dBTP, LRA 5.5 LU.
- a-and-r (AR.md): round 1 revise (hook under the cello in minor bars 33-36, narrow choruses 9-15 %, faint choir
  line) -> fixed (a gainDb dip on the counter-line, piano melody layer width 0.7, strings width 1.5 + rides, choir
  dynamics from 0.45) -> round 2 ship. Width above 150 Hz 42 -> 63 %.
- producer: delivered. METADATA / COVER (pop: two spheres, one the other's scale) set and looked at. Credits: CC-BY
  Salamander Grand (Alexander Holm), SSO (CC Sampling Plus), VPO (Paul Battersby); SampleRadar / Gimme-a-Hand / 224XL
  licences to check before publishing. System findings added to TODO.md.
