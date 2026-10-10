# Veranda Light - brief

**Wish (the session's brief):** compose two new reference pieces "that a master jazz pianist-composer would write,
clearly better than songs/pro-piano-latenight and songs/pro-piano-bossa", from the craft knowledge of the five blind
rounds (`songs/_blind/ROUNDS.md`): 2. songs/pro2-piano-bossa - a tender bossa, AABA or ABAC. Same sound and setup as
the endless generator (`agentsound.endless.perform.band`), similar length and section layout. Original melodies only.

- Genre / profile: solo jazz piano, `ANALYSIS = {'profile': 'piano'}`.
- Frame: E-flat major, 118 BPM, 4/4, straight 8ths (the endless 'bossa' feel: pianist style `straight`, the bossa
  left hand = rootless bossa comping + the root-fifth line `R__f` on the comp track, the piano laid back 8 ms).
- Length: 90 bars, 3:12: `intro 4 | head ABAC 32 | solo ABAC 32 | out A2,C 16 | tag 4 | end 2`.
- Energy arc: a quiet vamp -> a soft, singing A -> the bridge lower and quieter -> the C climbs to the head's peak
  (F6 over Abmaj9) -> the solo builds to ONE peak (Ab6 over Bbm9, solo A2 bar 7, 64 % into the piece) and winds
  down through the C -> the head out at head level, its C softer -> the tag into the backdoor -> Eb6/9, the hook
  above it.
- Band: the endless band (`perform.band`, the `solo_piano` preset + the genre's master gain + the bossa feel's
  -1.5 dB), untouched; the bossa left hand as the endless `bossa_left`, its bass line touched wider (below).

## What the blind rounds asked for, and where it is (the v1 criticism in brackets)
- A motif-based head: the sigh (C Bb G, falling onto a syncopated long note) moved chromatically onto Ab7#11
  (B Bb Gb), echoed over Gm9, inverted in phrase 2 (C Eb G, then a 4th higher F Ab C). [v1: a leap-and-sigh cell
  in nearly every bar]
- A guide-tone line under the sigh: G - Gb - F - Eb (3 of Eb, b7 of Ab7, b7 of Gm9, the diminished chord's Eb), then
  G - C - D/Db - C (A bar 7: the b9 of C7 resolving by step).
- A contour plan: the A Eb5-D6 (peak D6, bar 7); the bridge lower (G4-G5) with its own rhythm (on the beat,
  quarters and halves, falls answered by walks up); the C to the head's peak F6 (bar 25, 75 %).
- Restatement with varied cadences: A2 bends the peak D -> Db over Bbm9 (mode mixture) and turns to the subdominant
  (Bbm9 Eb7b9 -> Abmaj9); the C's half-step descent (Gm9 Gb7#11 Fm9 E7#11) and the hook bent onto the 9th.
- Intro / tag of their own: Ebmaj9 - Bmaj7#11 (the bVI a third away), the sigh landing on the common tones (Bb =
  the maj7 of B, Eb = its 3rd); the tag turns the vamp's second half into the minor iv (Abm9 Db13, the backdoor) and
  the last chord rings while the hook's three notes come back softly above it. [v1: the frame figure = the hook's
  shape, the last chord rolled like every endless tune]
- A hand-written solo (SOLO in song.py): the sigh displaced and answered, a rising line to the lydian #11, call
  and response in the bridge (falling sighs answered by climbs; enclosures), a denser A2 that builds to ONE peak
  written as a line (D6 F6 G6 -> Ab6), the C winding down with the head's own sigh and landing on the 9th / the
  sus4. [v1: arpeggio-per-bar 8th lines, the climax in octaves / locked hands on every beat]

## Checklist (HUMAN_FEEDBACK)
- [x] Straight 8ths (a bossa), melody first, tender.
- [x] A song, not a loop: the hook returns and grows (intro / A / solo / C's last bar / the end), surprises (the
  chromatic sigh on Ab7#11, the Db over Bbm9, the E7#11 tritone sub, the backdoor tag).
- [x] Piano harmonized and decorated, fast figures at most once each (`pianist.Memory(once=True)`).
- [x] Real dynamics: flat_dynamics 0 (lead 7.1 dB per phrase, vel 34-122; the bossa left hand 6.1 dB).
- [x] clicks 0, silent_notes 0.

## Log
- producer: brief; sound / mix / master locked to the endless genre.
- arranger: lead sheet, head-out A2 paraphrase and solo written by hand (ARRANGEMENT.md); chord-fit script: 0
  clashes (the one flagged Eb is the tied anticipation of the diminished chord).
- sound designer: unchanged by design (SOUND.md).
- mix: findings only (MIX.md): the left hand -2.6..-4.8 dB under the lead, the end-chord masking is the endless
  ending's voicing.
- master: `--check` all ok (MASTER.md).
- A&R: see AR.md.
