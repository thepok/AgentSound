# Low Ceiling Blues - brief

**Wish:** "Compose TWO solo jazz piano pieces as a professional jazz pianist-composer would ... the 'pro' reference
set for a blind comparison against the rule-based endless generator ... 2. songs/pro-piano-blues: a minor or major
blues with a strong, memorable riff head." Same sound as the endless jazz-piano genre, similar length (3-4 min),
same shape class as an endless blues (intro 4, head 2 x 12, solo choruses, head out 2 x 12, tag 4, end 2).

- **Genre / profile:** solo jazz piano, `ANALYSIS = {'profile': 'piano'}` (the endless genre's).
- **Frame:** C minor blues, 104 BPM, 4/4, straight 8ths (HUMAN_FEEDBACK "aber ohne Swing"), ~3:47.
- **Sound (fixed):** the endless jazz-piano band, copied line for line from `agentsound/endless/perform.py` into
  `make_band()` (see SOUND.md).
- **Hook:** a two-bar riff - repeated tonic, the minor third, the blue climb F-F#-G, answered by the fall G F Eb C -
  stated AAB over the 12 bars (I, a fourth up on IV, home, then the punchline). On the grand's middle register
  (C5-C6), harmonized by `pianist.arrange`.
- **Form:** `intro 4 | head A1 A2 (2 x 12) | solo S1 S2 S3 (3 x 12) | out A1 A2 (2 x 12) | tag 4 | end 2` = 94 bars.
- **Energy arc:** the riff alone (no left hand) -> head -> three solo choruses building -> THE climax = the head
  out's first chorus (octaves / locked hands, the punchline to Eb6) -> the Neapolitan chorus settles -> tag vamp
  -> rolled Cm6/9.
- **Reference:** the endless jazz-piano blues tunes (e.g. `_endless_jazz_piano/out/002-the-other-promise-blues`) -
  shape class only.
- **Blind comparison:** tags / cover as an endless tune (album "Endless Sessions"), `out/leadsheet.txt` +
  `out/tune.json` in the endless runner's format.

## Checklist (HUMAN_FEEDBACK)
- [ ] a song, not a loop: a riff that returns and grows, chorus-to-chorus variation, transitions
- [ ] straight 8ths, melody first, polish over virtuosity
- [ ] piano harmonized / decorated by `pianist.arrange`, fast figures budgeted (one `pianist.Memory`)
- [ ] real dynamics: `flat_dynamics` 0, a section arc with one summit
- [ ] clicks 0, silent notes 0, loudness inside the endless gate (-18.5..-12 LUFS)

## Log
- producer: brief written; the sound is frozen to the endless genre spec.
- arranger: lead sheet composed (ARRANGEMENT.md), `melody_issues` clean on A1 / A2 / the climax chorus. Build 1: the
  solo louder than the head out (-14.4 vs -15.1), intro as loud as the head. Build 2: intro softer, solo energy 0.8
  / vel 50-102, out A1 +12/+20 -> out the summit. Build 3: tag softer. Build 4: intro unaccompanied (riff alone).
  The left hand read borderline flat (4.3-4.5 dB, info `flat_dynamics` on comp) with seed 7316; performance seeds
  7317-7319 tried in scratch copies, 7319 kept (piano 6.6 dB, LH 5.2 dB, no flat_dynamics entry).
- sound designer / mix / master: no changes by design (SOUND.md, MIX.md, MASTER.md).
- A&R: ship (AR.md).
