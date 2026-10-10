# Window on Barrow - arrangement

**Frame:** C minor, 100 BPM, 4/4, swing 0.6, 90 bars, 3:46. Solo piano (right hand `piano`, left hand `comp`).

## Form
| section | bars | harmony | energy | what happens |
|---|---|---|---|---|
| intro | 4 | Abmaj7#11 G7b9 Abmaj7#11 G7b9 | 1 | the hook's head an octave up, rubato ('lean'), ballad touch, LH tenths; falls through G7b9's diminished upper structure into the head |
| head A1 | 8 | Cm9 Ab7#11 Fm9 Bb13 / Ebmaj9 Abmaj7 Dm7b5 G7alt | 2 | the hook stated softly (48-88) |
| head A2 | 8 | same, ending ii-V-i then C7b9 into the bridge | 2 | new phrase end climbing E5 G5 Bb5 into the bridge |
| head B | 8 | Fm9 Bb13 Ebmaj9 Ebmaj9 / Ebm9 Ab13 Dbmaj7#11 G7alt | 3 | long notes high; the HOOK IN Eb MAJOR (bar 4); darkens to Ebm9 (Gb), climbs to the Neapolitan Dbmaj7#11 (Eb6 - C6 - G5: the lydian sound), tritone fall to G7alt |
| head A3 | 8 | ... Dm7b5 Db7#11 CmMaj9 | 2 | tritone-sub cadence onto the minor-major chord |
| solo A1 | 8 | A changes | 2 | statement: the hook displaced by 2.5 beats, single notes + guide tones, lots of space |
| solo A2 | 8 | A2 changes | 3 | call and response sequenced up a step (C D Eb G Bb -> Eb F Ab C Bb), a triplet, 3rds / 6ths |
| solo B | 8 | bridge | 4 | rising 8th lines, a run over Ab13 to F6, drop 2 / quartal |
| solo A3 | 8 | A3 changes | 5 | CLIMAX: the hook in octaves / locked hands an octave up, the summit G6 (13th of Bb13) held, the shake; then down in steps to a long C5 |
| out B | 8 | bridge | 3 | the bridge again (54-100) |
| out A3 | 8 | A3 changes | 2 | the hook thinned: its D left ringing a whole bar, ballad style, softer (46-86) |
| tag | 4 | Abmaj7#11 G7b9 Abmaj7#11 Dm7b5 Db7#11 | 1 | the hook twice - the second an octave up (lamplight-avenue's "climbs higher in the last one"), ritardando |
| end | 2 | CmMaj9 | 1 | s.ending: rolled from the LH up, the RH's top note D6 = the hook's leaning note, fermata, room |

## The hook
`r/4 G4/8 C5/8 Eb5/4. D5/8~ | D5/2 C5/8 Bb4/8 C5/4` - a rising minor arpeggio that leans on D (the 9th of Cm, held as
the #11 of Ab7#11 across the bar line), answered in bar 3 by the same rhythm widened (Ab C Eb G F over Fm9). It
returns: intro (8va), A1/A2/A3, the bridge (in Eb major), solo A1 (displaced), solo A3 (octaves, the climax), out A3
(thinned), tag (twice, 8va the second time), the final chord's top note.

## Players
- `jazz.chorus` per section = `pianist.arrange` per part; one `pianist.Memory` song-wide (ornament budget).
- Head: style `straight`, LH `shell` (lh_vel 54), the genre's ornament weights; density 0.5 / 0.55 / 0.7 / 0.6.
- Solo: written out; devices per part: single+guide -> guide/3rds/6ths -> drop2/quartal -> octave/locked/drop2
  (`climax=True`, `doubles=0.8`); touch frames 50-84 -> 54-92 -> 60-102 -> 70-116.
- Section sweeps (perform.build's rule) only where a full bar would be empty.
- Moves used (arranger summaries): devices guide / thirds / sixths / quartal / drop2 / close / octave / locked;
  ornaments roll, turn, mordent, restrike, crush, 2 trills + 1 shake (fast budget); fills chromatic, gliss,
  pentatonic, arpeggio.

## Needs from sound design
None beyond the endless jazz-piano sound (locked for the comparison): RH C4-G6, LH C2-F4.
