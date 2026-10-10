# Kites over Bank Street - arrangement

**Frame:** F major, 150 BPM, 3/4, straight 8ths; 180 bars, ~3:46 (with the ritardando and the ring-out).

## Form

| section | bars | harmony | energy | what happens |
|---|---|---|---|---|
| intro | 8 | Bbmaj7#11 (2) Am7 D7b9 Gm9 Bbm6 Gm9 C13 | 1 | rubato, ballad touch, LH tenths: the hook's IV-colour bars and its b9 answer, the minor iv (Bbm6) as a first shadow; the hook's pickup (A Bb) into the head |
| head A1 | 16 | Fmaj9 (2) Bbmaj7#11 (2) Am7 D7b9 Gm9 C13 Am7 Abdim7 Gm9 C7b9 Am7 D7b9 Gm9 C13 | 2 | the hook stated plainly, soft |
| head A2 | 16 | as A1, then Fmaj9 (2) Cm9 F13 | 2+ | same opening; lands home on F, the ii-V into IV, an F-A-C pickup up to the bridge's D6 |
| head B | 16 | Bbmaj9 (2) Ebm9 Ab13 Dbmaj9 (2) Gm7b5 C7b9 Am7 D7b9 Gm9 Bbm6 Am7 Ab13 Gm9 C7b9 | 3 | contrast: long high notes falling, a ii-V into Db (bVI, the surprise key), back through iii-VI, the minor iv, the tritone sub Ab13 |
| head A3 | 16 | as A1, then Dbmaj7#11 C7sus4 Fmaj9 (2) | 2+ | the deceptive cadence: the bridge's Db returns under the hook rhythm (F G C: the #11 again) |
| solo | 64 | AABA | 2 -> 4 | `soloist.solo(arc='build', energy=0.85)` from the hook's two bars: statement, development, burst, climax; the fast figure saved for its last A |
| out B | 16 | bridge | **5** | THE climax: bars 9-12 climb to Eb6 (b9 of D7 on top) -> D6 over Gm9 -> Db6 over Bbm6; `climax=True` (octaves / locked hands), touch +10/+18 |
| out A3 | 16 | last A | 3 -> 2 | the hook paraphrased, settling |
| tag | 8 | Dbmaj7#11 C7sus4 Bbmaj7#11 (2) Gm9 C13 Fmaj9 (2) | 1 | ballad, ritardando: the Db hook, the hook's head on IV with its #11 held, the last ii-V, the hook's first bar on the tonic |
| end | 4 | F69 | 1 | rolled from the left hand up, the 9th (G) on top, fermata, the room rings |

## The hook
`C5 1.5 | D5 .5 | F5 1 | E5 2.5` - a dotted lilt to a held major 7th. Growth: (1) sequenced onto the IV, the same E
reheard as #11; (2) its rhythm a third higher in bar 9 (E G C -> B over Abdim7: the #11 again, now as tension);
(3) low in bar 13 of A1 (C D E); (4) in the bridge's bar 13 (C E G); (5) over the Db in A3 / the tag (F G C, the
#11 of Db); (6) the soloist's motif; (7) the tag ends on its first bar, the end chord's 9th answers its E.

## Harmony with surprises
- maj7 -> #11 common tone (bars 2-4), Abdim7 passing chord (bar 10), b9 / altered dominants for colour.
- the bridge's ii-V into **Db** (bVI) instead of the expected IV-only bridge.
- the A3's **deceptive cadence** Dbmaj7#11 - C7sus4 - F (the bridge's key returns at the end of the tune).
- minor iv (Bbm6) in the bridge and the intro: the shadow before the light.

## Transitions
Pickups written into the melody (A Bb -> C; F A C -> D6; E A Bb -> C); `lead_in=True` lets the pianist fill the gap
before each part; arpeggio sweeps (from perform.py) where the right hand left a bar empty before the solo / out;
rubato intro; ritardando from the tag's middle into the fermata.

## Players
One `pianist.Memory` for the whole tune. `jazz.chorus` with the endless defaults (style straight, LH shell, lh_vel 54,
the genre's ornament weights); intro / tag style ballad, LH tenths. Head touch per part (-4, 0, +6, +2 on the
feel's 50-96 frame), density 0.5-0.63. Solo: `pianist.vocabulary('straight')`, phrase 4 bars, vel 54-104, budget
spice 2 / fast 16 / same 32 bars, the fast figure saved for the last A. Out: paraphrased (B lightly: 0.15 / 0.05 /
0.1), B `climax=True`.

## Needs from sound design
Nothing new: the endless jazz-piano sound, register C3-E6.
