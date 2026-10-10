# Cellar Hours - brief

**Wish (the session's brief):** compose two new reference pieces "that a master jazz pianist-composer would write,
clearly better than songs/pro-piano-latenight and songs/pro-piano-bossa", from the craft knowledge of the five blind
rounds (`songs/_blind/ROUNDS.md`): 1. songs/pro2-piano-latenight - a late-night minor AABA, medium swing, swing ratio
~0.58-0.6. Same sound and setup as the endless generator (`agentsound.endless.perform.band`), similar length and
section layout (intro, head, solo, head-out, tag, ending). Original melodies only.

- Genre / profile: solo jazz piano, `ANALYSIS = {'profile': 'piano'}` (the endless genre's).
- Frame: F minor, 108 BPM, 4/4, the endless 'straight' feel (pianist style `straight`, left hand `shell`), swing
  0.58 (the brief's range at its low end; HUMAN_FEEDBACK wants <= 0.58).
- Length: 90 bars, 3:30: `intro 4 | head AABA 32 | solo AABA 32 | out B,A3 16 | tag 4 | end 2`.
- Energy arc: a quiet vamp -> a soft first A -> the bridge low and quiet, then the head's peak (F6 over Dm7b5) ->
  the solo builds from a sparse quote to ONE peak (Ab6, solo A3 bar 1, 67 % into the piece) and comes down -> the
  head out at head level, its last A thinned -> a hushed tag -> Fm6/9 spread, the tune's first note G on top.
- Band: the endless band (`perform.band`, the `solo_piano` preset + the genre's master gain), untouched.

## What the blind rounds asked for, and where it is (the v1 criticism in brackets)
- A motif-based head: a (a 9th falling by step and skipping down) + b (a breath, a leap up to a held colour tone);
  a-b sequenced down a step and RE-FITTED to the new chords (Db -> C over Ab13); phrase 2 a stepwise climb, not
  the motif again. [v1: a 5-1-3 pickup arpeggio as the hook, repeated mechanically]
- A guide-tone skeleton: G-F (9-1) / D (3) / F-Eb (9-1) / C (7) / Db (b5) / Eb-Db (#9-b9) / F-Ab; the leading tone E
  of C7alt resolves to F in every A.
- A contour plan with one placed peak per period: phrase 1 Bb4-G5, phrase 2 to Eb6 (A bar 6), the bridge low
  (Bb4-G5, half notes and quarter-note triplets) then F6 (B bars 5-6, 65 % through the head); the solo's Ab6.
- Restatement with varied cadences: A2 turns through F7#9 into the bridge, A3 cadences deceptively (Dbmaj7#11)
  and through the tritone (Gb7#11).
- Intro / tag of their own: a plagal vamp over an F pedal into the Neapolitan Gbmaj7#11, b developed (5th, 4th,
  5th); the tag stays on the Neapolitan and falls straight to the tonic (no dominant), spread, then a soft G-F echo.
  [v1: the hook's head over bVI-V, the same hook twice in the tag]
- A hand-written solo (SOLO in song.py): a displaced quote of a, target-note chains with enclosures (F-Eb -> E,
  Ab-F# -> G, Db-B -> C, G-E -> F), a in quarter-note triplets answered by rising 8th lines, the bridge's triplets
  quoted, 1-3-bar phrases across bar lines, one peak written as a line (a expanded from Ab6, b an octave up), a
  descent ending on Db, the first note of the head-out's bridge. [v1: an arpeggio per bar, the climax as block
  chords / octaves on every beat (climax=True)]
- Phrase-shaped dynamics: `jazz.touch` per part, the bridge and the solo's last A touched in pieces (a soft low
  half, the climb; the peak, then the line coming down).

## Checklist (HUMAN_FEEDBACK)
- [x] A song, not a loop: a hook that returns and grows (intro / A / solo peak / tag echo), surprises (the
  deceptive A3, the Neapolitan tag ending).
- [x] Piano never a bare line: every part through `pianist.arrange` (devices, ornaments, a few fills, LH shells);
  fast figures once each (`pianist.Memory(once=True)`).
- [x] Real dynamics: flat_dynamics 0 (lead 7.1 dB per phrase, vel 29-125).
- [x] Light swing (0.58), melody first.
- [x] clicks 0, silent_notes 0.

## Log
- producer: brief written; sound / mix / master locked to the endless genre (parity for the blind test).
- arranger: lead sheet, head-out A3 and the solo written by hand (ARRANGEMENT.md); checked with a chord-fit script
  (every strong-beat / long note a chord tone or available tension, non-chord tones resolved by step): 0 clashes.
- sound designer: nothing changed by design (SOUND.md).
- mix: `python -m agentsound mix` - all inside the targets, no moves (MIX.md).
- master: `master --check` all ok (MASTER.md).
- A&R: see AR.md.
