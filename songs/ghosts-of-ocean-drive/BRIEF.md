# Ghosts of Ocean Drive - brief

## The wish

> "starte auch einen neuen synthy song" - a NEW synthwave song: emotional, cinematic 80s night-drive / retrowave in
> the vein of The Midnight / FM-84 / Timecop1983 / Kavinsky (original composition), a great singable HOOK carried by
> a hero sound, maybe a sax or guitar solo, lush pads/strings as a bed, gated 80s machine drums, synth/octave bass,
> arps, layered keys; a clear form with an energy arc, risers/fills and variation between repeats.

## Frame

- Genre: retrowave pop (instrumental), analysis profile `synthwave` (`ANALYSIS = {'profile': 'synthwave'}`).
- Tempo 104 BPM, B minor, 4/4, straight 8ths; half-time feel in verse 1, four on the floor from the choruses on.
- Length: 124 bars, ~4:46 + the reverb tail.
- Different from the other synthwave songs: children-of-neon (122, F#m, dream trance), polaroid-summer (88, D major),
  midnight-interstate (112, F#m), skyline-heartbeat (118, Em), chrome-leviathan (124, C#m darksynth),
  orbital-station (84, Em sci-fi). New here: B minor, a Dorian major-IV breakdown, a sax solo, a key change up a
  whole step via G#7.

## The hook

- The chorus melody (16 bars): a cell of two 8ths, a leap to a quarter, two 8ths falling to a quarter (F# G B, B A G
  over G), sequenced a step higher over A, answered by a held B on the tonic; the second half climbs to F#6 and comes
  home to B. Teased in the intro, returns in the interlude, re-coloured (G -> G#) in the breakdown, up a step in the
  last chorus, sung once more by the sax in the outro.
- Carried by a hero sound (`hero()` wrapper, genre synthwave): candidates `hero/synth_piano` (piano_synth),
  `hero/synth_lead`, `hero/piano_pop`, `layered/piano_glass_lead` - chosen by measuring the chorus against the
  references (SOUND.md). Played by the pianist (octaves / sixths / thirds under the melody, restrikes and rolls,
  budgeted ornaments) with touch() velocity arcs - never a bare, beepy single line.
- Solo: the hero sax (`hero/sax`, Weresax alto) played by the wind player (`hornist`, style hero).

## Form and energy arc

`intro 8 | verse1 16 | pre1 8 | chorus1 16 | interlude 4 | verse2 8 | pre2 8 | chorus2 16 | breakdown 8 | solo 8 |
chorus3 16 (C#m) | outro 8`

Energy: 1 -> 2 -> 3 -> 4 -> 3.5 -> 2.5 -> 3.5 -> 4.5 -> 2 -> 4 -> 5 -> 1.5.

## References (analysis only, like with like)

- The Midnight "Sunset" (retrowave pop; the hook excerpt 4:00-4:30 vs our chorus2 / chorus3).
- Kavinsky "Nightcall" 1:15-1:45 (outrun low end, density).
- Timecop1983 "Deckard's Dream" (dreamwave width / darkness; whole track vs whole song).

## HUMAN_FEEDBACK checklist (the A&R ticks these)

- [ ] A song, not a loop: form, tension/release, hook returns and grows, variation between repeats, fills.
- [ ] No thin/beepy synth lead: the hook on a hero sound with body, played in octaves / voicings.
- [ ] The hook reads in front: bed >= 3 dB under the lead in the chorus sections (report `bedVsLeadDb`).
- [ ] Real dynamics: `flat_dynamics` = 0; touch() arcs, the section arc (first statement soft, last chorus hottest).
- [ ] Piano parts through `pianist.arrange`, flashy two-key figures budgeted (fast_every).
- [ ] Held sax notes breathe (hornist: air, vibrato on held peaks, mic moves).
- [ ] Hero sounds for hook and solo; no bare oscillators, no Gameboy (224XL rooms, echoes, width, full low end).
- [ ] Drums by the drummer, bass by the bassist (not looped grids).
- [ ] `clicks` = 0.

## Targets

- Recipe mix targets (synthwave.md): -12..-9 LUFS-I, TP <= -1 dBTP, chorus 2-4 LU over the verse, width above 150 Hz
  60-80 % in full sections, reverb 8-14 LU under the mix, echo ~-16..-22 LU while it sounds.
- Mixer profile `synthwave`; master platform `auto`.

## Log

- producer: brief written (wish, frame, hook plan, form, references, checklist).
- arranger: 12 sections / 124 bars built (ARRANGEMENT.md); pianist (hook devices octave / 6ths / 3rds, 74-89 % of the
  hook voiced, ornaments restricted to restrike / roll / rare crush), drummer synthpop (16 crashes, 6 tom fills, 2
  builds, a stop), bassist synth (verse 1 + outro interlocked with the kick), hornist solo + outro farewell. Keys /
  brass given 4-bar arcs + accents (were flat). Open: none.
- sound-designer: hook sound chosen by measurement (SOUND.md): hero piano_synth; sax hero for the solo; hats played
  lighter; bass ducker deeper (9 dB, threshold -48). Open: hats' punch and kick punch vs Sunset.
- mix (producer, with `agentsound mix`): MIX dict (drums +2, bass rides down in verses / pres, bed rides, lead +1.5 in
  verses, sax +1.5 in the solo, pad / keys / drums dips); master limiter drive automated per section (energy arc
  verse1 -14.5 -> chorus1 -10.5 -> chorus2 -10.2 -> chorus3 -9.7 LUFS). Result: 0 report warnings, 0 mixer findings
  (1 info), 0 clicks, master --check ok (TP -1.11, -11.6 LUFS, LRA 6.0).
- producer: delivered (METADATA / COVER outrun set, cover looked at). Checklist: all ticked; see known weaknesses in
  the hand-over (kick punch -4.5 dB and hats +5 dB vs Sunset, 111-224 Hz +3 dB vs Sunset, presence -2.4 dB).
- mix-engineer (MIX.md): drums ridden up in the choruses (+0.6 / +0.8 / +1.0) and back in the solo (-0.5), hats'
  air dipped (-2 dB @ 10 kHz), a fast 4 dB kick duck on the bass, the hook's 800 Hz honk dipped (-1.5 dB) with the
  lead +1 dB. Result: drums inside the window in every hook (chorus2 -5.8 -> -5.2), bed 3.9-5.8 dB under the lead, 0
  warnings, 1 info finding, 0 clicks. Open: kick punch / hat punch vs Sunset (sound, not faders).
- mastering-engineer (MASTER.md): -1 dB @ 1.25 kHz master_eq first (the plan's +1.5 dB presence lift refused: piano
  hook), limiter release 120 ms, +2 dB drive per section: -11.6 -> -10.9 LUFS-I, TP -1.12 dBTP, LRA 6.0 -> 4.7,
  master --check ok.
- a-and-r (AR.md): **revise** - 4 major: the arc plateaus from chorus 1 (chorus1 -> chorus3 +0.6 LU, chorus3 only +0.2 over the solo, 6.5 dB limiter drive in chorus3; arranger + mastering), a soft kick / ticky hats / 110-125 Hz boom vs Sunset (sound-designer), a hook with no top (0.9 % presence in the lead stem; sound-designer), the sax solo under the band (-2.3 dB, bed -3.9; arranger + mix-engineer); 3 minor (width 50-55 %, the C#m -> G outro jump, GOD_LEAD switch / credits).
- revision (arranger, sound-designer, mix-engineer, mastering-engineer, producer; AR.md "Revision"): the arc now climbs
  (chorus3 - chorus1 +0.6 -> +1.2 LU, chorus3 - solo +0.2 -> +1.5, verse2 -> chorus2 1.8 -> 3.6; LRA 4.7 -> 6.8). The
  hook rests before chorus 1 and 2. Verse 2 and the solo are thinned, and the master drive varies per section. The
  drummer's crashes sound again. The kick hits (Linn layer, split low end): punch 13.6 -> 18.7 dB (Sunset 18.9). The
  hook has a top (glass octave layer, air shelf, softer doubles): presence share 0.9 -> 2.7 %. The sax sits over the
  band (-2.9 -> +2.4 dB, bed 6.3 dB under it). Width 52 -> 58 %. Chorus 3 pivots on A into the outro. GOD_LEAD is
  removed. Result: 0 warnings, 0 clicks, TP -1.13 dBTP, -11.9 LUFS, master --check ok, mixer 1 info (harsh,
  deliberate). Open: the top-band punch is still +3.9 dB over Sunset (snare / clap crack).
