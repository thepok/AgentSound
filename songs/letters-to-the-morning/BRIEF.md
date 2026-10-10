# Letters to the Morning - brief

**Wish:** a song "like 'River Flows in You'" (Yiruma): a solo piano, new-age / pop-classical piece. An ORIGINAL
piece in that style - no melody, chord-and-rhythm signature or recognisable figure of the model; the genre only.

- Genre / profile: new-age / pop-classical solo piano, `ANALYSIS = {'profile': 'piano'}`.
- Frame: A-flat major (not the model's key), 4/4, 75 BPM (the return 70, the coda 66), rubato, straight 8ths,
  69 bars, ~3:55 of music + the final chord's ring (4:04 file).
- Hook: the right hand of the grand, Ab4-F6 - three rising 8ths into a held note, then a falling sigh of four 8ths
  into a held note (vi-IV-I-V). Never beepy: a sampled grand voiced warm (`solo_piano`: hammers fully softened, a
  dynamic presence cut on the loud notes, no 2-5 kHz lift).
- Band: `bands.make('solo_piano', s)` - right hand = `piano`, left hand = `comp`, salon room + plate, gentle master.
- Form: `intro 4 | A1 8 | A2 8 | B1 8 | inter 4 | A3 8 | build 8 | climax 8 | A4 8 | coda 5`.
- Energy arc: left hand alone, the hook's head high and soft -> theme p (mid register) -> theme with a higher
  answer -> hook mf -> the bed thins to air -> theme with sixths under it -> F-minor build, the melody an octave up,
  the left hand widening -> ONE climax (bar 53, ff, F6 over Fm) with a ritardando into a held Eb7 -> theme plain and
  soft -> the hook's head over Dbmaj7 - Dbm6 and a rolled Ab chord.
- References: none in the repo (the model is named for style only; no reference audio, no compare run).
- Targets: the piano profile (-23..-16 LUFS-I, TP <= -1 dBTP, LRA 4-22), clicks 0, silent_notes 0,
  flat_dynamics 0; the left hand 6-9 dB under the melody; loud frames' 2-5 kHz well under the body (the solo_piano
  fix measured 9.4-11.7 dB).

## Checklist (HUMAN_FEEDBACK)
- [x] A song, not a loop: ten sections, the theme in four colours (plain / higher answer / with sixths / plain and
  soft), the hook stated, sequenced, raised in the climax and echoed in the coda.
- [x] Music BREATHES (2026-10-09 "endless monotone line of notes"): a rest of a quarter to a full bar at every
  phrase end, ritardandi into the cadences, the interlude with whole bars of silence in the melody, the left hand
  thinning ('half' / 'open' / quarter figures) at phrase ends, in the interlude and the return; density rises and
  falls (LH 8ths -> quarters -> bass octaves + two-octave figures in the climax).
- [x] Register and dynamic contrast between phrases: A in Ab4-F5, B to C6, build to Db6, climax to F6, pp-ff marks.
- [x] Warm, not hard ("es klingt hart", "schrill und hart"): solo_piano voicing, master air above 9 kHz only.
- [x] Real dynamics: romantic touch per phrase, lean on long notes; flat_dynamics 0.
- [x] Played, not keyboard-like: melody rubato, phrase rubato, pedal changes per harmony, rolled final chords.
- [x] No fast two-key figures (none written).
- [x] clicks 0, TP <= -1 dBTP.

## Log
- producer: brief (this file); key, form and arc fixed; solo_piano preset as the sound.
- arranger / composer: the right hand written bar by bar in notation (romantic.score), the left hand as per-bar
  chord + broken-chord figure (ARRANGEMENT.md). Fixes after the first renders: bass register Db2-C3 (it boomed at
  C2-B2), the left hand capped at G4 (stays under the melody), a missing colour tone in bar 26, fermatas moved
  behind the rolled chords (they had stretched the rolls).
- sound designer: solo_piano unchanged; the left hand's low shelf -4 dB @ 220 Hz and -2 dB @ 1.4 kHz (SOUND.md).
- mix: left hand 6-9 dB under the melody; a -2 dB 400 Hz dip on the left hand (MIX.md). One masking warning left in
  the coda (both hands of one piano on the final chord; judged benign).
- master: drive 6.5 dB, -2 dB @ 100 Hz, +2.5 dB shelf @ 9 kHz: -19.7 LUFS-I, TP -1.20 dBTP, LRA 15.2 LU (MASTER.md).
- a-and-r: revise (AR.md) - 2 major: the left hand's unbroken, even 8th grid (8 attacks in 56/69 bars, no gap > 1 beat in bars 37-56, comp flat in 9/10 phrases: the music does not breathe), the melody a bare undecorated line in A1/A2/B1/A4 (chordPct 9.2 %); minors: pedalled bass +8.7..+9.5 dB at 80-100 Hz, vi-IV-I-V loop in B1/climax, coda masking (benign). Keep the arc, the interlude, the theme/hook, the warm sound.
- arranger (A&R round 1 fixes): left-hand figures varied inside every section (flow / rock / lilt - a quarter then
  8ths - / ring / colorhalf), the hand holds under the melody's rests (bars 8, 12, 16, 20, 24, 28, 36, 44, 48, 60,
  64: 13 gaps of 2-3.8 beats; attacks per bar now 3-16), each figure crests on its top note and every phrase swells
  +-8 % (comp phrase dynamics 9.6 dB), the bass carries less (x1.02 instead of x1.12); the climax denser (16th
  sweeps at its peaks, bars 51 / 53); the melody harmonized - sixths / thirds under A2's answer, octaves under B1's
  held notes, sixths in A3, chords in the climax - and one turn per theme statement (bars 11, 19, 59); A4's answer
  bent (Eb5-F5 and a sixth); the hook's loop broken: B1's second half IV - I6 - ii - iv - V, the climax opens
  Dbmaj7 - Eb/Db - Ab/C - Eb/Bb (a falling bass) into the vi peak; s.lilt (beat 3 +0.03, jitter 0.03).
- sound designer: the left hand -2.5 dB at 100 Hz (bass vs profile +0.9 dB, was +3.3); the right hand's velocity
  cap 106 (110) and the master -1 dB at 3.2 kHz after the denser climax: the loudest frames' 2-5 kHz 10.1 dB under
  the body (9.3 without them).
- mix / master re-checked: bed -4.5..-9.7 dB under the lead, no moves; -19.6 LUFS-I, TP -1.20, LRA 16.5, all ok.
- a-and-r round 2: ship (AR.md) - both majors fixed: LH varied and resting (8-attack bars 56 -> ~35/69, half-bar gaps in every A/B section, comp flat phrases 9 -> 3, climax sweeps 16/bar), melody harmonized + turns (chordPct 9.2 -> 13.1 %, A4 varied), bass +3.3 -> +0.9 dB, vi-IV-I-V loop broken; minors only (bars 37-56 drive without a half-bar rest, dark air -10 dB by design, bass-led intro/interlude, benign coda masking).
