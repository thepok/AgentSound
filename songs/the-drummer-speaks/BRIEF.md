# The Drummer Speaks - brief

**The wish** (user): "Create masterful drum solos, and the techniques needed for them, like we did for the
saxophone." This song is the showcase of the drummer's solo layer (`drummer.perform`, rudiments, the hands'
physics, the gated tom break, chokes, the live hi-hat, re-strike damping): a band frames a long drum solo that has
to sound like a human master drummer, not a drum machine.

- **Genre / profile**: classic hard rock with an organ (Zeppelin / Deep Purple era drum-feature tradition), analysis
  profile `rock`. Instrumental.
- **Tempo / key / meter / feel**: 116 BPM, E minor, 4/4, straight 8ths (the user prefers straight, tight feels).
- **Length**: ~3:10 (92 bars).
- **The hook**: a two-bar unison riff (bass + two rhythm guitars, E minor pentatonic with a chromatic turn) whose
  rhythm (3 + 3 + 4 + 2 16ths: `x..x..x...x.x...`) is ALSO the drum solo's motif - the solo grows out of the riff and
  hands it back. Melody: a singing head on the hero lead guitar (`layered/hero_guitar`, E4-B5: body, not beepy).
- **Form**: `intro 4 (cymbal swell, the drummer alone on the toms, then the riff) | A 16 (head x2 over the riff and
  C D Em B7) | B 8 (the chorus: C D Em Em C D B7 B7, crash-ride, open chords) | riff 4 (unison riff, band hits, a
  stop) | SOLO 40 (drums alone) | B2 8 (the band explodes back) | A3 8 (head, an octave up at the end) | end 4 (riff,
  a run, the final hit choked)`.
- **Energy arc**: intro 2 -> A 3 -> B 4 -> riff 4 -> solo 2 rising to 5 (soft time-keeping dissolving, a quiet motif,
  development around the toms, rudiments, polyrhythms, half / double time, a dramatic silence, the gated tom break,
  double bass, a speed burst, a press roll from a whisper, the big finish) -> B2 5 -> A3 4-5 -> end 5 + silence.
- **Band**: `bands.rock_band` (Big Rusty kit replaced by the `sampled/big_rusty_kit` patch: chokes 88-90, the live
  hi-hat on CC4 -> `dynamics`, `restrike=6`; drum bus with parallel compression and the Voxengo drum room; picked
  Growlybass; two DI guitars through amps L / R; the rock organ with its Leslie tremolo) + the hero guitar for the
  head + a mallet track (`sampled/big_rusty_mallets`) for the opening cymbal swell + a gated reverb return for the
  80s tom break.
- **Reference**: none (no drum-solo reference in `assets/refrences/`); the genre's `rock` profile targets.
- **Platform**: `auto`.

## HUMAN_FEEDBACK checklist (the A&R ticks it)

- [ ] A song, not a loop: form, a hook (the riff) that returns and grows, variation, fills, a real ending.
- [ ] The solo sounds played by a person: stickings with a weaker hand, ghost notes at ghost level, flams, rolls,
      dynamics that breathe (never one level), no machine-gun repeats, no impossible limb combinations.
- [ ] No beepy lead: the head on the hero guitar (body below 1 kHz).
- [ ] Lead in front in the head sections (bed >= 2-3 dB under it).
- [ ] Real dynamics: `flat_dynamics` = 0; the solo's arc audible (soft start, build, climax).
- [ ] Realism: sampled kit with velocity layers and round robins, played by the drummer (no grids).
- [ ] Produced: drum room, parallel-compressed drum bus, plate / echo on the lead, gated reverb on the tom break.
- [ ] `clicks` = 0, no clipping, true peak <= -1 dBTP, silent notes 0.
- [ ] Length 2:30-3:30, straight feel.

## Log

- producer: brief written (this file).
- arranger: form 4 / 16 / 8 / 4 / 40 / 8 / 8 / 4 bars (3:14); the riff (bass + two guitars) and its rhythm as the
  drum motif; head + chorus on the hero guitar (touch() arcs); the drummer through arrange (band sections, one
  Memory, kick locked to the bass, `hands='master'`), pattern (riff unisons), perform (the intro tom figure, the
  solo's frame, the end) and soloist.solo + drummer.vocabulary (the solo's body, classic arc, seed 11). First
  version: 22 solo moves ordered by hand; switched to the soloist when it was merged (ARRANGEMENT.md).
- sound designer: `sampled/big_rusty_kit` (chokes, live hi-hat) `.but(level=1.0, restrike=6)` in the rock_band drum
  chain (parallel-compressed bus, drum room) + a peak catcher on the bus; the gated return for the tom break; the
  mallet kit for the opening swell; the hero guitar; the organ's swell pedal and Leslie per section (SOUND.md).
- mix engineer: MIX trims drums +2 / bass +1.5, drums +2.5 in the solo, bass ducked 4 dB more under the kick, 42 Hz
  and 3.3 kHz cuts; the balance inside the rock targets in every hook (MIX.md).
- mastering engineer: rock window, auto; master eq (+2 dB at 400 Hz, -0.8 dB below 60 Hz), drive +3 dB; more drive
  refused (the limiter already holds the drum peaks; the solo's arc matters more than the last 0.1 LU) (MASTER.md).
- a-and-r: **ship** (AR.md) - minors: loudness 0.2 LU under the rock floor (the quieter solo; kept), the master
  narrows the solo's arc to ~4-5 LU, the bass + kick unison masking (deliberate), the rhythm guitars' / organ's flat
  info (amp / swell pedal). Delivered: out/mix.mp3, mix.wav, cover.png.
