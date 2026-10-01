# The Drummer Speaks - A&R

Judged: the full build of song.py with the solo from `soloist.solo` + `drummer.vocabulary` (3:14, `out/mix.mp3`),
`out/report.json`, the images, `mix` and `master --check`.

```
verdict: ship
summary: A tight, straight hard-rock frame (a riff you remember after one pass, a singing guitar head, an organ that
breathes) that drops out for a 40-bar drum solo which grows out of the riff's own rhythm - soft snare talk, answers on
the toms and the hi-hat, rudiments around the kit, a gated 80s tom break, double bass, a press roll from a whisper -
and hands the riff back to the band with unison hits; the band explodes back in, the final hit is grabbed.
```

## Issues (most severe first)

1. [minor] Loudness 0.2 LU under the rock window's floor (-10.2 LUFS-I; `master --check` warn). The limiter already
   holds the drum peaks (+1.5 dB drive bought +0.3 LU); the shortfall is the solo itself (-11.8 LUFS: quieter by
   design). Inaudible after normalisation (streaming turns it down 3.8 dB). owner: mastering-engineer - kept, see
   MASTER.md.
2. [minor] The master narrows the solo's arc: soft statement -> climax is ~10 dB of RMS before the master chain, ~4-5
   LU of short-term loudness after it (`loudness.png`: -14 at the first statement, -9.2 at the burst). The arc is
   still heard (density, velocity layers, the open space in the statement), but a gentler glue in the solo would let
   it breathe more. owner: mastering-engineer (an automated glue threshold in the solo) - next revision if the user
   wants a more dynamic solo.
3. [minor] `masking` drums / bass in A and A3: the riff is a bass + kick unison (the kick locked to the bass), ducked
   5 + 4 dB. Deliberate (MIX.md). owner: mix-engineer.
4. [minor] `flat_dynamics` info on the rhythm guitars (2.4 dB per phrase through a crunch amp: their accents are
   palm mute vs open) and the organ (no touch on an organ: the swell pedal is automated). Not the lead (7.0 dB per
   phrase, `flat_dynamics` 0 on the lead). owner: arranger - acceptable.
5. [minor] No reference track (none for a drum feature in `assets/refrences/`): tone judged against the rock
   profile only (balance within +-1.5 dB except presence +1.4 / sub +0.7).

## Evidence on the solo (the brief's core)

- Played by the hands' physics (`HANDS['master']`), measured on the render JSON's 640 solo strokes: off the grid by
  a median 2.6 ms (p90 11.6 ms with the graces and bounces) - never the grid; 97 same-drum strokes closer than 35 ms
  (flams 15-30 ms ahead: 50, drags, the press roll's bounces closing in and dying away); velocities 7-127, SD 15-45
  per 2 bars; only 32 of 640 strokes repeat the previous velocity on the same drum (and the kit's 4 round robins
  rotate on top): no machine gun. The weak hand a hair late and looser, ghosts 15-35, rebounds of doubles under the
  first stroke, accents losing height at speed (the unit tests in `tests/python/test_drumsolo.py`).
- Re-strike damping (`restrike=6`): the fast tom passages and the double bass do not pile up boom (the sampler test:
  a 16th run +5.3 dB of ring without it, +0.4 dB with 9 dB of damping).
- The arc (`spectrogram_05_solo.png`, `loudness.png`): the time-keeping dissolving under the band's dying chord, the
  motif three times soft with space kept by the hat foot, answers (tom melody, call and response, the hi-hat dance
  on the live CC4 lane), development (flams down the toms, paradiddles around the kit), the burst (the gated break
  on its own return, hand-hand-foot triplets, double bass), the climax (the press roll), a quiet resolution with
  cymbal swells, then the finish on the riff's accents -> B2 +3.3 LU.
- Limbs: `drummer.check()` [] on every drummer part; the soloist's warnings []; 0 silent notes; 0 clicks.

## Checklist (BRIEF.md)

- [x] A song, not a loop: intro (swell, the drummer alone, the riff) -> head x2 -> chorus -> riff unison -> solo ->
      chorus -> head -> riff + choked hit; the riff returns 6 times and is the solo's motif.
- [x] The solo sounds played: stickings with a weaker hand, ghosts at ghost level, flams / drags / buzz, never one
      level, no machine-gun repeats (velocity layers + round robins + height variation), no impossible limbs.
- [x] No beepy lead: the hero guitar (body below 1 kHz, vibrato, echo throws).
- [x] Lead in front in the head sections: rhythm -1.4..-3.2 dB, low -2.7..-3.5 dB, the others <= -4.5 dB under the
      lead (`mix`: inside the rock targets, no moves left).
- [x] Real dynamics: `flat_dynamics` 0 on the lead (7.0 dB per phrase); the solo's arc audible.
- [x] Realism: Big Rusty (14 layers x 4 round robins, close + OH), played by the drummer (no grids anywhere).
- [x] Produced: drum room, parallel-compressed drum bus + peak catcher, plate / echo / hall on the lead, gated
      reverb on the tom break, plate throws into the solo's longest rest and the final hit (space `lush`).
- [x] `clicks` 0, no clipping, true peak -1.2 dBTP, silent notes 0.
- [x] Length 3:14, straight feel.

## Keep

The riff-as-motif idea (the solo grows out of the band's riff and gives it back as the cue), the hat foot keeping the
pulse in the solo's space, the gated break on its own return, the finish's unison hits, the choked final hit with the
band cutting together, the organ's swell pedal and Leslie moves, the hero guitar's head.

## Re-check after the rock pass (the band sound, ROCK.md)

Judged: the full build of song.py on the rock pass (guitarist.riff + double, the tube-amp guitars, the bass rig, the
calibrated kit and drum bus), `out/report.json`, `mix`, `master --check`, `compare` against Sweet Child O' Mine's
band sections (riff / chorus / climax) and the A/B clips in `out/rock_ab/`.

```
verdict: ship
summary: The same song with a real rock band under it: the riff now breathes with the form (palm-muted single notes
under the head, chugged power chords in the intro, an open ringing wall with the octave in the riff section and the
choruses), the bass growls, the kit rises evenly from ghost note to backbeat, and the kick finally punches in the
choruses.
```

1. [minor] Snare punch in the choruses 7.6 dB over its surroundings vs 12.4 in the record (was 8.7): the open power
   chords + octave ring under every backbeat. owner: mix-engineer / sound-designer (TODO: a snare path of its own).
2. [minor] The wall is far wider than the record at 250-500 Hz (45-54 % vs 9-20 %); the brief asked for a wide wall and
   the mono sum is 0.9 dB quieter (mono_compat ok) - judge by ear. owner: producer.
3. [minor] `masking` drums / bass in A (-0.9 dB: the riff's kick + bass unison, they hit together) - deliberate as
   before; the chorus's duck is now measured (no longer listed). owner: mix-engineer.
4. [minor] `flat_dynamics` info on gtr_l (the rhythm guitars' dynamics are the articulations: through the driven amps
   velocity moves the level ~0 dB). owner: sound-designer (TODO).
5. [minor] Numbers only - the A/B (`out/rock_ab/`) is for the user's ears.

Numbers: -10.0 LUFS-I (inside -10..-7; was -10.2: loudness_low gone), LRA 5.1 LU, true peak -1.20 dBTP, width >150 Hz 33 %,
clicks 0, 1 warning (the riff unison), lead note dynamics 7.3 dB, `mix` no moves, `master --check` all ok. Kept: everything
in Keep above (the solo and its arc were not touched).
