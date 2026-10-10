# Carousel on Morton Street - brief

**Wish (the session's brief):** "Distill [the five blind-test rounds] into recipes/jazz-composition.md ... compose TWO
new reference pieces with that guide, better than the current songs/pro-piano-* (which the judges criticised for
arpeggio solos): songs/pro2-piano-waltz (jazz waltz, AABA or ABAC, 3/4) ... Hand-write head AND solo ... Same sound
and setup as the endless generator ... similar length (~3-4 min) and section layout class."

- Genre / profile: solo jazz piano, `ANALYSIS = {'profile': 'piano'}` (the endless genre's).
- Frame: Eb major, 150 BPM, 3/4, straight 8ths (the endless 'waltz' feel played straight like the v1 waltz; the
  user's ears prefer straight jazz 8ths), 178 bars, 3:42.
- Form (the endless shape class): `intro 8 | head AABA 64 (16-bar parts) | solo AABA 64 | out B,A3 32 | tag 8 | end 2`.
- Energy arc: rubato intro vamp -> head (the bridge opens to F6) -> a written solo chorus that builds in four stages
  -> ONE peak (solo A3 bar 10: G6 over Bb13, 73 % into the piece) -> head out from the bridge near head level ->
  soft tag -> spread Eb6/9.
- Hook: the sampled grand's right hand (the endless sound, no synth); the motif Bb C D | G.
- Band: `agentsound.endless.perform.band` (the genre's solo_piano preset), unchanged.
- Craft guide: `recipes/jazz-composition.md` (written for this brief from `songs/_blind/ROUNDS.md`).
- Reference: songs/pro-piano-waltz (v1) - its solo came from the shared soloist; this one is written note by note.

## Checklist (HUMAN_FEEDBACK + jazz-composition.md)
- [x] A song, not a loop: AABA with restated A's and three different cadences, a contrasting bridge, a written solo
  with a story, an own intro vamp and a tag that reprises it.
- [x] Piano never a bare line: every part through `pianist.arrange` (jazz.chorus).
- [x] Straight 8ths (no swing).
- [x] Real dynamics: touch() per phrase, the left hand breathing per 4 bars; flat_dynamics 0.
- [x] Melody first (Beegie Adair): a singable motif, clear phrase ends, rolled chords, a real ending.
- [x] No arpeggio-per-bar solo; guide-tone targets, enclosures, chromatic passing notes.
- [x] clicks 0, silent_notes 0.

## Log
- producer: brief; sound and master locked to the endless genre.
- arranger: lead sheet + written solo (ARRANGEMENT.md); a scratch lint of every written bar (degrees, strong-beat
  clashes, arpeggio bars) and `composer.melody_issues` clean; `composer.tells` on the performance: clashes 0, wraps 0,
  repeats 0, head 5-gram 0.26 (the restated A's played from the A1's dice), cell_max 0.24, quarter runs 2, solo
  duration entropy 1.78, solo density x1.30 over the head, the loudest 4 bars and the top note at 0.73.
- sound designer: nothing changed by design (SOUND.md); the left hand's phrase arc in song.py (`_lh_breath`): its
  chords measured flat (4.5 dB, a flat_dynamics info) -> 6.0 dB.
- mix: findings recorded, not applied (MIX.md, parity).
- master: `master --check` -16.2 LUFS-I, TP -1.20 dBTP, LRA 5.9 LU: all ok (MASTER.md).
- A&R: ship (AR.md).
