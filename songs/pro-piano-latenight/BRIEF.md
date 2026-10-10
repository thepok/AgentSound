# Window on Barrow - brief

**Wish (the session's brief):** "Compose TWO solo jazz piano pieces as a professional jazz pianist-composer would ...
They serve as the 'pro' reference set for a blind comparison against the rule-based endless generator ... Use the SAME
instrument, patch, room, mix settings and master as the endless jazz-piano genre spec ... 1. songs/pro-piano-latenight:
a late-night minor AABA ballad/medium tune with optional swing feel (use swing like the endless `--swing 0.6`)."

- Genre / profile: solo jazz piano, `ANALYSIS = {'profile': 'piano'}` (the endless genre's).
- Frame: C minor, 100 BPM, 4/4, medium (the endless 'straight' feel: pianist style `straight`, left hand `shell`),
  swing ratio 0.6 (= `endless jazz-piano --swing 0.6`; HUMAN_FEEDBACK prefers <= 0.58, the comparison brief wins here).
- Length: 90 bars, 3:46 (endless tunes of this feel: 3-4 min).
- Form (the endless shape class): `intro 4 | head AABA 32 | solo AABA 32 | out B,A3 16 | tag 4 | end 2`.
- Energy arc: soft statement -> bridge opens -> solo builds through four stages -> ONE climax (solo A3, the hook in
  octaves, G6 over Bb13) -> head out relaxes -> hushed tag -> rolled CmMaj9 with the hook's D on top.
- Hook: the sampled grand's right hand, C5-Eb6 (no synth anywhere), harmonized by `pianist.arrange`.
- Band: `jazz_trio` without bass and drums + the endless trims / pans / sends / eq / master gain, copied verbatim from
  `endless/genres.py` / `perform.py` (verified: the compiled tracks, buses and master equal an endless tune's).
- Reference: an endless jazz-piano tune of the same feel (`.tmp` render, seed 40, analysis only).

## Checklist (HUMAN_FEEDBACK)
- [x] A song, not a loop: real form, a hook that returns and grows (intro up an octave, bridge in major, solo climax
  in octaves, tag twice), tension / release, a surprise or two (bII Dbmaj7#11 in the bridge, tritone sub cadence,
  minor-major final chord).
- [x] Piano never a bare line: every part through `pianist.arrange` (devices, ornaments, fills, LH shells).
- [x] Fast two-key figures budgeted (one shared `pianist.Memory`: 3 in 90 bars - head A2 trill, the climax shake,
  out A3 trill).
- [x] Real dynamics: `touch()` arcs per phrase, section frames from 44-84 (intro) to 70-116 (climax); flat_dynamics 0.
- [x] Melody first (Beegie Adair): singable hook, clear phrase ends, rolled chords, a real ending.
- [x] Warm piano: the genre's jazz_grand + its -3.5 dB at 3.5 kHz, unchanged.
- [x] clicks 0, silent_notes 0.

## Log
- producer: brief written; sound and master locked to the endless genre for the blind comparison.
- arranger: lead sheet + written-out solo composed by hand (ARRANGEMENT.md); built: 3:46, 0 clicks, 0 silent, piano
  note dynamics 8.2 dB, no flat_dynamics. Solo A3 devices forced to octave / locked / drop2 for the climax.
- sound designer: nothing changed by design (SOUND.md).
- mix: `python -m agentsound mix` findings recorded, not applied (MIX.md: parity with the endless setup).
- master: `master --check` -15.9 LUFS (0.1 LU over the piano window, like the endless reference render at -15.8),
  TP -1.2 dBTP; kept (MASTER.md).
- A&R: ship (AR.md).
