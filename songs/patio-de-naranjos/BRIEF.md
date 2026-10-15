# Patio de Naranjos - brief

**Wish:** "hätte gerne so ein gezupfte nylon gitarre lied" - a fingerpicked nylon-string guitar piece; the guitar
is the star, intimate and warm, real fingerpicking (thumb bass on alternating strings, p-i-m-a arpeggios, the
melody on top inside the pattern, some hammer-ons), breathing timing, natural dynamics, 3-4 min, at most subtle
support.

- **Genre / profile:** lyrical Spanish-tinged classical guitar solo; `ANALYSIS = {'profile': 'classical'}`
  (-23..-16 LUFS, dynamics first). The `piano` profile was tried first: its dark grand reference called a nylon
  guitar "+13 dB brilliant"; against the classical and jazz references the balance is within +-3 dB.
- **Tempo / key / meter / feel:** 84 BPM, 4/4, straight 8ths (16ths in a2). E minor, the middle section (c) and
  the ending in E major (the parallel major - the guitar's open E), b in the relative G major, the bridge an
  Andalusian fall (Am G F B7) back to E minor.
- **Hook:** the tune itself on the treble strings (B / E strings, E4-G5): rest, B4-E5 up to a held G5, stepping
  down - opens every A phrase, returns in a2 and climbs to the climax. Not beepy: a real sampled nylon guitar with
  4 velocity layers and round robins.
- **Sound:** `sampled/concert_guitar` (Markus Fiedler's Natural Concert Guitar - the most alive nylon set installed:
  4 velocity layers x up to 7 round robins, release / fret noises), heard by a stereo pair (keypan), a small wooden
  room close, the warm Musikverein hall behind. No support instruments: the guitar alone (the wish; every extra
  part would cover it). No physical-model guitar.
- **Form:** `intro 4 | a1 16 | b 8 | c 16 (E major) | bridge 4 | a2 16 | coda 6` = 70 bars, 3:29 (+ tail).
  Energy arc: intro / a1 intimate (-21.6 LUFS) -> b rising -> c the light, dancing middle (Travis picking) ->
  bridge held on B7 (ritardando + fermata) -> a2 the top (16th arpeggios, the last phrase climbing to G5, -17.4)
  -> coda soft (Picardy E major, a rolled final chord, harmonics, the hall opening).
- **References:** none (no nylon-guitar recording in `assets/refrences/`); the classical profile's balance.
- **HUMAN_FEEDBACK checklist:**
  - [x] a real song, not a loop: form with a key change, variation between the A's, transitions (bass runs,
        ritardandi, fermata), a climax, an ending
  - [x] realism: sampled, played (guitarist + hand 'fingerstyle': thumb / finger weights, pinch lag, skipped /
        swapped inner voices, drifting time and loudness, fret noises from the samples) - never keyboard-like
  - [x] real dynamics: the tune `touch()`ed per phrase (velocities 45-125), the pattern 32-80; flat_dynamics 0
  - [x] the lead in front: the tune 8-15 velocity over the pattern (measured on a split render: the tune ~3 LU
        over the accompaniment, integrated incl. its rests)
  - [x] warm, not hard: the 3.5 kHz edge, the 7 kHz zing and the air rounded off; the ff layer only on the summit
  - [x] flashy moves budgeted: hammer-ons / pull-offs in the tune ~1 per 6 bars, chord ornaments by the
        guitarist's budget
  - [x] clicks 0, silent_notes 0
- **Targets:** classical profile (-23..-16 LUFS, TP <= -1 dBTP, width >150 Hz 15-110 %, reverb -14..-4 LU);
  platform auto.

## Log

- producer: brief (this file). Found: `sampled/concert_guitar` installed in the main checkout (worktree:
  `AGENTSOUND_SAMPLES` pointed there); the guitarist had no chord-melody mode (melody on top of a picked
  pattern) - added `guitarist.arrange(melody=, slur=)` (system work, tested in test_guitarist.test_chord_melody).
- arranger: ARRANGEMENT.md - the form, the tune per section, the player plan.
- sound designer: SOUND.md - stereo pair keypan, tone chain, rooms. Render 1: brilliance +12 vs piano, tune 1 LU
  under the pattern, 2 % wide -> tune +8..15 velocity / pattern -6, profile classical, keypan + width.
- mix: MIX.md - the guitar named the lead, a 300 Hz dip (mud +4.8 -> +2.8 dB). 0 warnings.
- master: MASTER.md - width 1.2 (mono < 120 Hz), limiter +6 dB, ceiling -1.3: -19.1 LUFS-I, TP -1.30.
- A&R: AR.md - ship.
