# Kites over Bank Street - brief

**Wish:** "Compose TWO solo jazz piano pieces as a professional jazz pianist-composer would ... the 'pro' reference
set for a blind comparison against the rule-based endless generator ... 1. songs/pro-piano-waltz: a jazz waltz in
3/4, bright, AABA." Same sound as the endless jazz-piano genre, similar length (3-4 min), same shape class (intro,
head, one solo chorus, head out, tag/ending); only composition and performance may differ.

- **Genre / profile:** solo jazz piano, `ANALYSIS = {'profile': 'piano'}` (the endless genre's).
- **Frame:** F major, 150 BPM, 3/4, straight 8ths (HUMAN_FEEDBACK "aber ohne Swing"; the endless default), ~3:46.
- **Sound (fixed, not mine to change):** the endless jazz-piano band - `jazz_trio` without bass / drums, the
  Salamander grand on both hands (piano = RH, comp = LH), trims piano -2 / comp +3 dB, pans -0.4 / -0.1, sends
  room +6 / plate +8 dB, the 3.5 kHz -3.5 dB EQ, master gain 6.5 dB. Copied line for line from
  `agentsound/endless/perform.py` into `make_band()`.
- **Hook:** a dotted waltz lilt up to a held major 7th (C D F | E), sequenced onto the IV where the same E becomes the
  #11 - the tune's signature colour. On the grand's melody register (C5-D6), harmonized by `pianist.arrange`.
- **Form:** `intro 8 | head A1 A2 B A3 (4 x 16) | solo AABA (64) | out B A3 (32) | tag 8 | end 4` = 180 bars.
- **Energy arc:** soft rubato intro -> head (A1 soft, bridge lifts) -> solo builds from a sparse statement ->
  THE climax = the head-out bridge (Eb6, octaves / locked hands) -> last A settles -> soft tag, rolled F6/9.
- **Reference:** the endless jazz-piano waltz tunes (e.g. `_endless_jazz_piano/out/001-...-waltz`) - shape class only.
- **Blind comparison:** tags / cover as an endless tune (album "Endless Sessions"), `out/leadsheet.txt` +
  `out/tune.json` in the endless runner's format.

## Checklist (HUMAN_FEEDBACK)
- [ ] a song, not a loop: hook returns and grows, bridge contrast, variation between repeats, transitions
- [ ] straight 8ths, melody first, polish over virtuosity (Beegie Adair)
- [ ] piano harmonized / decorated by `pianist.arrange`, fast figures budgeted (one `pianist.Memory`)
- [ ] real dynamics: `flat_dynamics` 0, a section arc with one summit
- [ ] clicks 0, silent notes 0, loudness inside the endless gate (-18.5..-12 LUFS)

## Log
- producer: brief written; the sound is frozen to the endless genre spec (no sound-design / mix / master freedom).
- arranger: lead sheet composed (ARRANGEMENT.md), checked with the endless composer's own `melody_issues` (only the
  intended E6 of the climax flagged as out of the normal register). Build 1: arc flat (head -15.4, solo -14.5, out
  -14.6). Build 2: A1 softer, solo energy 0.85 / vel 54-104, out bridge +10/+18 touch -> head -15.6, solo -15.2,
  out -14.5 (summit at 2:47-2:55, ST max -11.4), tag -17.7.
- sound designer / mix / master: no changes by design (SOUND.md, MIX.md, MASTER.md).
- A&R: ship (AR.md).
