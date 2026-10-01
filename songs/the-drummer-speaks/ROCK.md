# The Drummer Speaks - the rock pass (the band sound)

The user liked the new lead guitar tone (the `amp` effect, `layered/hero_guitar_heavy` v2) and the drum solo, and asked
"what's still missing for good rock?". This is a SYSTEM pass on the band - rhythm guitars, riffs, bass, kit, the rock
mix - validated on this one song against the full-band sections of Guns N' Roses "Sweet Child O' Mine" (the video edit
in `assets/refrences/`, analysis only): the intro riff with the band (0:16-0:32), a chorus (1:04-1:20), the heavy
"where do we go" climax (4:05-4:35), against this song's A (riff + head), B (chorus) and B2 (the band's return after
the drum solo). Numbers: `python -m agentsound compare ... --section A|B|B2`, loudness-matched (the record is a -17.6
LUFS rip, ours -8.5); scratch measurements in the worktree's `.scratch/` (not in the repo).

## What was missing (measured)

1. **The rhythm guitars ran on the old amp**: one tube waveshaper per cab (`cab/*`, `sampled_guitars._amp`, the band
   presets' `rock.amp`, `layered/hero_guitar`, `sampled/hero_guitar_clean`) with a bright shelf before and a scooped tone
   stack after it. The same FSBS riff through it: 315-630 Hz at -13.7 dB of the energy (-10.8 through the tube amp), the
   low mids scooped; against the record the whole mix lacked low mids: **-3.5 dB (178-707 Hz) in the riff, -3.2 dB
   (178-561 Hz) in the chorus**.
2. **No palm mute samples, and the emulation lost the chug.** No installed guitar pack has DI palm mutes (FSBS direct,
   Emily, Black and Green, Shiny: none; SampleRadar's heavy-metal chugs are real but amped). The v1 emulation (a 1.6
   kHz low-pass, 0.55 s decay) through a driven amp: the low thump 3.7 / 2.8 dB under the open chord (80-160 / 160-315
   Hz) and ~250 ms flat into the amp; the real amped chugs keep their 80-315 Hz and fall -4..-16 dB at 100 ms, -21..-35
   dB at 200 ms, peaking as loud as the open chord.
3. **No riff player.** The riff was a hand-made clip (`chordify('power').articulate('palm', short)`) played the same in
   every section; the "double" was the same notes on two tracks with different humanize seeds (per-note jitter only, no
   drift, no tuning difference).
4. **The bass had no amp.** The rock_band bass "tube drive" was a saturator at mix 0.55: centroid 383 Hz vs the DI's 371
   - nearly clean.
5. **Big Rusty's velocity response** (TODO): the snare's layers 2-4 (velocity 14-51) within 4 dB (-43 .. -38.8 dB) while
   the kick moves 8 dB there, then +3 dB jumps at 52 and 65; the toms 5-8 dB over the snare at the same mid velocity.
6. **Drum punch vs the record**: kick 11.6 dB over its surroundings in the chorus (record 21.4), 13.8 in the climax
   (22.0); the hats too spiky (11.1 / 11.5 vs 9.6 / 7.2); in the riff the kick stuck out (24.1 vs 11.0).
7. **The kick/bass check was touchy**: its separation (the envelopes' normalised product) cannot exceed ~1.5 dB for a
   sustained bass however deep its duck (the kick's own tail dominates), so it warned about ducked basses (even the
   engine test's synthetic bass, ducked 10 dB) and came and went with the 35 % share gate.

## What changed

- **Engine `amp`: `mix`** - the time-aligned DI blended under the amp (the dry path through the same half-band
  filters: 4 samples of delay, exact at mix 0 / 0.5 / 1; `tests/test_amp.cpp`).
- **One amp for the library** (`patches.sampled_guitars.amp(kind, cab=, mic=, **knobs)`): the `cab/*` patches are now
  `amp -> cabinet IR -> mic` with voicings in `space_ir.AMPS` (clean: one-stage Fender; blues: edge of breakup; crunch:
  two stages, gain 5; rock: a cranked Plexi, gain 6 / master 7; metal: TS boost + four stages, scooped; lead), each
  levelled to the DI; `amp()` lands where the v1 chain did (`AMP_TRIM`), so every calibrated level holds. `rock.amp`,
  the amped `sampled/*_guitar` patches (v2), `layered/hero_guitar` (v2: the Plexi lead channel on the tube amp, a
  rolled-back pickup), `sampled/hero_guitar_clean` and fretwork's pick scrape use it; `layered/hero_guitar_heavy` is
  bit-identical (its pinned digest unchanged).
- **Palm mute** (`sampled_guitars.PALM`, shared by the band presets): a resonant 900 Hz low-pass (70 % key tracking), a
  3600 ct pick envelope, decay 0.2 s, no sustain. Through the rock amp: peak -1.3 dB vs the open chord, -4.2 / -22 dB at
  100 / 200 ms, 80-160 / 160-315 Hz -1.8 / -1.5 dB vs the open chord, the centroid x1.02 (real chugs: equal peak, the
  thump kept, -4..-16 / -21..-35 dB, centroid x1.1-1.9; a 700 Hz version kept the thump within 0.2 dB but went dull,
  x0.78).
- **The riff player** (`agentsound/guitar_riff.py`, `guitarist.riff / pedal / hits / build_up / double / cell`): this
  song's riff is one line - `'E> - . E . . G> - - . A - G E - . | D> - . B - . A - . . E . G A# B> -'` - played at
  each span's energy: under the head (0.45) palm-muted single notes, intro / A3 (0.62) chugged power chords with open
  accents, the riff section and the ending (0.9) power chords + octave ringing; the turns and choruses on the same
  grid. `double()` makes the wall: two takes (other timing / velocity noise), a timing drift of +-7 ms on a smooth curve
  per take, +-4 ct tuning drift per take on the pitch bend, other round robins, two guitars into two amps.
- **The bass rig** (`sampled_guitars.bass_rig`: the tube amp at gain 4, tight 180 Hz, the DI blended at 65 %, a speaker
  roll-off): centroid 371 -> 553 Hz, +2.4 / +3.8 dB at 0.6-1.2 / 1.2-2.5 kHz with the DI's lows; rock_band's bass and
  `sampled/rock_bass` (v2).
- **Big Rusty calibrated** (`kits.velocity_map`, `sampled_drums.BIG_RUSTY_VELOCITY`): snare 14 / 25 / 38 / 51 / 64 / 65:
  -43.7 / -41.7 / -38.7 / -36.4 / -34.1 / -32.5 dB (smooth, the kick's curve), toms at velocity 50 -34..-35 (+1.5..2 dB
  over the snare; were +5..8).
- **The rock_band drum production**: the kit's `punch` (3:1, 25 ms attack), the drum bus `crush` (New York parallel 6:1,
  10 ms, 35 %) + `tape`, the room return's `room_crush` (6:1 at 50 %); the rhythm guitars keep their body (+1 dB at
  300 Hz instead of -1.5 at 250; the cab mic eq without its 350 Hz dip). Guitar / bass trims re-levelled to the old
  balance.
- **The kick/bass check** (engine analysis): the separation is now the sustained part's low-end energy on the transient
  part's hits vs between them - a ducked sustained bass reads its duck (the synthetic test: 0.1 -> 7.9 dB for the
  ducked one), a bass that only sounds with the kick reads ~0 (they hit together); low-band pairs gated by > 25 % each /
  > 70 % together; the message gives every section's value. Stable: this song's A..B with the bass +1.5 dB louder gives
  the same separations (intro -0.1, A -0.3, B 3.3 dB).
- **Song**: the guitars through `guitarist.riff` + `guitarist.double`; MIX bass trim +1.5 -> +1.0 (the rig's growl
  reads louder); `mix`: no moves, `master --check`: all ok.

## Before / after

Against Sweet Child O' Mine (mix - record, loudness-matched; old = the delivered build, new = this pass):

| | riff (A / 0:16-0:32) | chorus (B / 1:04-1:20) | climax (B2 / 4:05-4:35) |
|---|---|---|---|
| low mids (band) | -3.5 -> **-3.0** dB | -3.2 -> **-1.7** dB | -0.4 -> +1.1 dB |
| bass band | -0.1 -> -0.8 | -0.2 -> -1.7 | +1.6 -> **+0.4** |
| kick punch (record) | 24.1 -> 22.8 (11.0) | 11.6 -> **14.4** (21.4) | 13.8 -> **17.0** (22.0) |
| snare punch (record) | 10.9 -> 8.3 (8.4) | 8.7 -> 7.6 (12.4) | 8.6 -> 7.1 (9.9) |
| hats punch (record) | 12.9 -> **8.1** (8.9) | 11.1 -> **7.2** (9.6) | 11.5 -> **8.6** (7.2) |
| width > 150 Hz (record) | 23 -> 23 % (14) | 28 -> 32 % (19) | 30 -> 33 % (17) |
| width 250 / 500 Hz | 18 / 25 -> 28 / 27 % | 28 / 35 -> 45 / 54 % | 31 / 38 -> 52 / 54 % |
| crest (record) | 12.2 -> 11.9 (14.9) | 11.8 -> 11.9 (14.1) | 11.6 -> 11.7 (11.7) |

Whole song: -10.2 -> -10.0 LUFS-I, LRA 4.9 -> 5.1 LU, true peak -1.20 dBTP, width > 150 Hz 30 -> 33 %, clicks 0;
warnings 2 -> 1 (loudness_low gone; the masking warning is the riff's kick + bass unison in A: -0.9 dB, they hit
together - deliberate, MIX.md; B is now recognised as ducked); lead note dynamics 7.0 -> 7.3 dB (the plain hero on the
tube amp keeps its picking: 3.5 dB from velocity).

## A/B (old vs new, the same 18 s, the new level-matched to the old by integrated LUFS)

`out/rock_ab/`: `riff_intro_A_*` (0:04.1-0:22.1: the intro riff - chugged -, the riff under the head - palm-muted single
notes -, into the turn; new -0.4 dB), `chorus_B_*` (0:41.4-0:59.4: the chorus wall - open power chords + octave -, into
the riff section; new -0.2 dB), `reentry_after_solo_*` (2:24.8-2:42.8: the drum solo's unison hits and the band's
return in B2; new 0.0 dB). `a_old` = the delivered build, `b_new` = this pass.

## Open (TODO.md)

Verify by ear (numbers only); the snare's punch in the dense choruses (7-8 dB vs 10-12), the low-mid width of the wall
(much wider than the record), the rhythm guitars' velocity dynamics through the driven amps, the mixer tagging gtr_r
'low', the other rock songs not re-rendered, no bass cabinet IR.
