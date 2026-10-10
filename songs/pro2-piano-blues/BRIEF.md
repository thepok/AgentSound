# Hollis Street Shuffle Club - brief

**Wish (the session's brief):** "... compose TWO new reference pieces with that guide [recipes/jazz-composition.md],
better than the current songs/pro-piano-* (which the judges criticised for arpeggio solos): ...
songs/pro2-piano-blues (medium swing or shuffle blues with a riff head, several choruses). Hand-write head AND solo
... Same sound and setup as the endless generator ... similar length (~3-4 min) and section layout class."

- Genre / profile: solo jazz piano, `ANALYSIS = {'profile': 'piano'}` (the endless genre's).
- Frame: Eb major jazz blues, 112 BPM, 4/4, medium swing at ratio 0.58 (the endless 'straight' feel swung like
  `--swing 0.58`; HUMAN_FEEDBACK allows <= 0.58), 94 bars, 3:31. Notated in F, played a whole step down (song.py
  `SHIFT`): in F the riff sat on the 800 Hz-2.5 kHz band of the locked sound (mid +6.0..6.1 dB, a report warning).
- Form (the endless blues shape class): `intro 4 | head 2 x 12 | solo 3 x 12 | out 2 x 12 | tag 4 | end 2`.
- Energy arc: a soft dominant-pedal intro -> the riff head (chorus 2 a shade stronger, its top on the tritone sub)
  -> three written solo choruses that build -> ONE peak (solo chorus 3 bar 10, the top note over the backdoor Eb9 -
  0.65 of the piece) -> the riff head out near head level, its second chorus sinking -> tag -> a short cadenza into
  the last chord.
- Hook: the riff on the sampled grand's right hand (the endless sound).
- Band: `agentsound.endless.perform.band` (the genre's solo_piano preset), unchanged.
- Reference: songs/pro-piano-blues (v1: a minor riff blues whose solo came from the shared soloist).

## Checklist (HUMAN_FEEDBACK + jazz-composition.md)
- [x] A song, not a loop: a riff head AAB, three charts (plain / walk-down + tritone subs / backdoor), a written solo
  with a story, an own intro and tag.
- [x] Piano never a bare line: every part through `pianist.arrange` (jazz.chorus), blues crushes allowed.
- [x] Swing light (0.58), as the brief's "medium swing" within the user's limit.
- [x] Real dynamics: touch() per phrase, the left hand breathing per 2 bars; flat_dynamics 0.
- [x] No arpeggio-per-bar solo: guide tones, enclosures, chromatic passing notes, triplets and long landings.
- [x] clicks 0, silent_notes 0.

## Log
- producer: brief; sound and master locked to the endless genre.
- arranger: lead sheet + three written solo choruses (ARRANGEMENT.md); the scratch lint (degrees, strong-beat clashes,
  arpeggio bars) and `composer.melody_issues` clean; `composer.tells`: clashes 0, wraps 0, repeats 0, head 5-gram
  0.52 (a riff head), solo duration entropy 1.70, the solo x1.10 (peak x1.16) denser than the busy riff head at +7.8
  velocity, the loudest 4 bars at 0.65, the top note at 0.66.
- sound designer: nothing changed (SOUND.md); the key moved F -> Eb for the mid band (above); `_lh_breath` on the
  left hand.
- mix: 0 findings (MIX.md).
- master: `master --check` -16.9 LUFS-I, TP -1.20 dBTP, LRA 5.2 LU: all ok (MASTER.md).
- A&R: ship (AR.md).
