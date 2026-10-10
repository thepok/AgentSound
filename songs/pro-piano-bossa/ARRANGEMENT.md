# Folded Letter Bossa - arrangement

**Frame:** F major, 116 BPM, 4/4 straight 8ths, 90 bars, 3:16. Right hand `piano`; left hand `comp` (bossa comping +
root-fifth bass, as the endless bossa feel).

## Form
| section | bars | harmony | energy | what happens |
|---|---|---|---|---|
| intro | 4 | Bbmaj9 Bbm6 Gm9 C7b9 | 1 | the FRAME: the hook's shape (pickup leaping up to a held note) over IV, iv, ii; rubato, LH tenths |
| head A1 | 8 | Fmaj9 (2) G13 (2) Gm9 C13 Am7 D7b9 Gm9 C9 | 2 | the hook: up a sixth to the held A, sighing to E (maj7); its sequence onto G13's B natural |
| head B | 8 | Cm9 F13 Bbmaj9 Bbm6 Am9 D7b9 Gm9 C7sus4 C7b9 | 2-3 | the same rhythm, falling contour; the Db6 sigh of the minor iv; iii-VI-ii-V home |
| head A2 | 8 | ... Gm9 Gb7#11 Fmaj9 D7b9 Gm9 C7b9 | 2 | the surprise: Gb7#11 where A1 had C13 (Ab E C over it), a G-F# suspension over D7b9 |
| head C | 8 | Bbmaj9 Eb7#11 Am9 Abdim7 Gm9 C7sus4 C7b9 F69 (2) | 3 | climbs F5 -> Db6 -> E6 -> F6 (the head's peak on Abdim7), falls, quotes the hook's opening over the tonic, ends on D (6th) |
| solo A1 | 8 | A1 | 2 | sparse statement in the middle register, single notes + guide tones |
| solo B | 8 | B | 3 | 8th lines rising, 3rds / 6ths |
| solo A2 | 8 | A2 | 4 | the hook and its sequence an octave higher, a Gb7#11 line, drop 2 / quartal |
| solo C | 8 | C | 5 | CLIMAX in octaves / locked hands: D6 F6, Eb6 Db6, C6 E6 G6 (summit over Am9), a diminished cascade, then the hook's Gm9 figure and a long D5; a bar of space |
| out A2 | 8 | A2 | 2 | lightly paraphrased (jazz.paraphrase: anticipations, delays) |
| out C | 8 | C | 2-3 | as written, softer (50-96) |
| tag | 4 | Bbmaj9 Bbm6 Gm9 Gb7#11 | 1 | the intro's frame again; the last bar on Gb7#11 (A2's surprise) with Ab on top, ritardando |
| end | 2 | F69 | 1 | rolled, the RH top G5 (Ab -> G resolution), fermata |

## Players
- `jazz.chorus` per section (`pianist.arrange` per part, one `pianist.Memory`), style `straight`, the genre's
  ornament weights; head density 0.5 / 0.6 / 0.55 / 0.65, touch 50-90 / 54-98 / 52-94 / 56-104.
- Solo devices per part: single+guide -> guide/3rds/6ths -> drop2/quartal/6ths -> octave/locked/drop2 (`climax=True`,
  `doubles=0.8`); touch 50-84 -> 54-92 -> 60-102 -> 70-114.
- Bossa left hand: the endless `bossa_left` (rootless bossa comping vel 42 x section level, rolled 10-22 ms, the
  `R__f` line with `bass_touch`), levels head 0.9, solo 1.0, out 0.9, tag 0.75.
- Section sweeps per perform.build where a whole bar would be empty.

## Needs from sound design
The endless jazz-piano sound (locked): RH F#4-G6, LH C2-F4.
