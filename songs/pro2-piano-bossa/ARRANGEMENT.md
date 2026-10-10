# Veranda Light - arrangement

**Frame:** E-flat major, 118 BPM, 4/4 straight 8ths, 90 bars, 3:12. Right hand `piano`; left hand `comp` (bossa
comping + root-fifth bass, as the endless bossa feel).

## The material
- **The sigh** (A bar 1, Ebmaj9): `r/8 C6/8 Bb5/8 G5/8~ G5/2` - 13, 5, 3, the 3rd syncopated and held.
- Moved down chromatically onto Ab7#11 (`B5 Bb5 Gb5`: a passing Cb, the 9th, the b7 held), then over Gm9
  (`Bb5 A5 F5`, b3 9 b7) with the Eb tied into the diminished chord: the guide line G Gb F Eb.
- Phrase 2 inverts it (C Eb G over Fm9, F Ab C over Bb13), D6 -> Db6 (the b9 of C7 anticipated) -> C6 by step.

## Form
| section | bars | harmony | energy | what happens |
|---|---|---|---|---|
| intro | 4 | Ebmaj9 Bmaj7#11 Ebmaj9 Bmaj7#11 Bb7sus4 | 1 | the sigh twice, each landing on a common tone of the B chord (Bb = maj7, Eb = 3rd); rubato, LH tenths |
| head A1 | 8 | Ebmaj9 Ab7#11 Gm9 Gbo7 Fm9 Bb13 Gm7 C7b9 Fm9 Bb7sus4 | 2 | the theme (touch 42-82) |
| head B | 8 | Cm9 Cm7/Bb Am7b5 D7b9 Gm9 C13 Fm9 Bb7b9 | 2 | lower and on the beat (G4-G5, 38-74): falls (G Eb D, F Eb C, F# Eb C, D Bb A) answered by walks up (C D Eb, G A Bb, Ab Bb C Eb, D F Ab) |
| head A2 | 8 | ... Bbm9 Eb7b9 | 2 | restated to bar 6; the peak bent D -> Db over Bbm9, Bb G over Eb7b9 into the C |
| head C | 8 | Abmaj9 Abm9 Db13 Gm9 Gb7#11 Fm9 E7#11 Ebmaj9 Fm9 Bb7sus4 | 3 | Bb C F6 (the head's peak), Eb6 Cb (the minor iv), the A's Gm9 sigh, half steps down (Fb Eb, B Bb), the hook bent onto the 9th (C Bb F) |
| solo A1 | 8 | A1 | 2 | the sigh late; a rising line to D6 (#11 of Ab7); D C Bb A F; a diminished turn; Ab G (a sigh); an 8th line in Bb13; the alt line to Bb4 / G4; a breath |
| solo B | 8 | B | 3 | calls (G Eb F G Bb D) answered by the sigh (C Bb G Eb); the call a step down, the answer through D7b9's b9; longer lines over Gm9 / C13; Eb6 C6 Ab5; Cb (b9) into the A2 |
| solo A2 | 8 | A2 | 4 -> 5 | denser; a turn and an 8th-triplet (D C Bb); the line climbs D6 F6 G6 over Bb13 to THE peak Ab6 (Bbm9); an enclosure Db-B -> C into the C |
| solo C | 8 | C | 4 -> 2 | C6 Eb6 G6 F6, the minor iv's Cb, the head's own sigh over Gm9, a line through Gb7#11 into Fm9, the E7#11 line (G# A# B C#), G5 held (3rd), F (9th) -> Eb (sus4): the end |
| out A2 | 8 | A2 | 2 | paraphrased by hand: a later entrance, an added 13th (F) over Ab7#11, a pickup D Eb F through the diminished chord |
| out C | 8 | C | 2 | as written, softer (40-82, ballad voicings), the last bar a held Eb |
| tag | 4 | Ebmaj9 Bmaj7#11 Abm9 Db13 | 1 | the vamp; its second half the backdoor: the sigh over Abm9 (Eb Db Cb), Cb Bb F over Db13; ritardando; no tenths (the bossa left hand alone: no doubled roots) |
| end | 2 | Eb6/9 | 1 | rolled (LH 80 ms, RH 90 ms after 0.3 beat), F on top; then the hook (C6 Bb5 G5) softly above it, dying away |

## Players
- `jazz.chorus` per section (`pianist.arrange` per part, one `pianist.Memory(once=True)`), style `straight`, the
  genre's ornament weights.
- Head: the A's from the same dice (seed 101), `anticipate=0.05`, `delay=0`, fill 0.2, embellish 0.25; touch per part
  A1 42-82, B 38-74, A2 46-88, C 50-100.
- Solo: `anticipate=0`, `delay=0`, `fill=0.12`; devices by part single+guide -> + thirds / sixths -> guide / drop2 /
  octave / sixths at the peak (`doubles=0.78`, no `climax=True`) -> guide / sixths; touch 42-80, 48-92, 56-116,
  46-86.
- Bossa left hand: the endless `bossa_left` (rootless bossa comping vel 42 x level, rolled 10-22 ms, the `R__f`
  line), levels head 0.75 / 0.7 / 0.8 / 0.9, solo 0.8 / 0.9 / 1.05 / 0.85, out 0.75 / 0.65, tag 0.65; the bass
  line's `bass_touch` range widened to 0.7 x lo .. 1.08 x hi (the endless range read flat_dynamics on this tune).
- Section sweeps only where a whole bar would be empty.

## Needs from sound design
The endless jazz-piano sound (locked): RH G3-Ab6, LH C2-F4.

## Revisions (A&R rounds 1-2)
- Head: phrase 2 one 4-bar arc (the inversion runs into D6 over the bar line); the bridge's second half new (D F A |
  A Bb A G | Ab G F | D F Ab Cb -> C6); the head-out C varied (a late F6, the E7#11 bar through its 13th); the sigh
  lightened towards its landing; written 8th anticipations moved onto the beat where the melody check flagged them.
- Solo: arpeggio legs replaced by scale / chromatic lines (one diminished arpeggio left: the bridge's D7b9 call),
  phrases over the bar lines, then breaths of 1.5-2.5 beats so it sings (A1 -> B, B bars 5-6, before the A2's climb,
  C bars 2 / 5); the A2 touched so only D6 F6 G6 -> Ab6 go above v100 (Ab6 the loudest note), doubles 0.6, embellish
  0 in the solo C and head-out A2.
- A hand-voiced ending: the last sigh C6 Bb5 as the top voice, the Eb6/9 (Eb Bb G | F Bb C G) struck under its G5.
- `check_melody()` (composer.melody_issues) runs in build(): clean.
