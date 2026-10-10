# Hollis Street Shuffle Club - arrangement

**Frame:** Eb major, 112 BPM, 4/4, swing 0.58, 94 bars, 3:31. Solo piano (right hand `piano`, left hand `comp`).
Written with `recipes/jazz-composition.md`; every line is notation in song.py (`MEL`, `OUT2`, `SOLO`, `INTRO_MEL`,
`TAG_MEL`). The notation and the names below are in F; the piece sounds a whole step lower (`SHIFT = -2`).

## Charts
| chart | bars 1-6 | bars 7-12 | used by |
|---|---|---|---|
| C1 plain | F13 Bb13 F13 Cm9-F13 Bb13 Bdim7 | F13 D7b9 Gm9 C13 F13-D7b9 Gm9-C7b9 | head 1, solo 1, out 1 |
| C2 walk-down | (same) | Am7 Abm7-Db9 Gm9 Gb7#11 F13-Ab13 Db9-Gb7#11 | head 2, solo 2 |
| C3 backdoor | (same) | F13 D7b9 Bbm9 Eb9 F13-D7b9 Gm9-C7b9 | solo 3, out 2 |

## Form
| section | bars | chart | energy | what happens |
|---|---|---|---|---|
| intro | 4 | C9sus4 C7b9 C9sus4 Gb7#11 | 1 | a dominant pedal (not the v1's riff-alone intro): the riff's blue figure F Ab A, a C7b9 line, the riff's head ending on Bb, Gb7#11 into the head (its #11 C) |
| head 1 | 12 | C1 | 2 | the riff (F Ab A, C6, A) and its answer Ab F D (Bb13's 7-5-3 = the Bdim7 of bar 6, literally), AAB: riff / riff / riff re-fitted to Bb (Bb Db D F) and D7b9 (C A F# Eb); the punchline climbs Gm9 by scale from the Eb's resolution D, falls down C13 through its b9, a turnaround onto E |
| head 2 | 12 | C2 | 2 | bars 1-6 restated, bar 8 re-fitted to Abm7 (Cb Ab Gb) / Db9 (F); a new punchline: the scale climb to D6, the head's top E6 = Gb7#11's 7th, its #11 C6, down the tritone turnaround onto Gb's #11 |
| solo 1 | 12 | C1 | 2 | the riff's blue figure displaced to beat 3&, short calls and answers in the middle register, a triplet, chromatic C B C under F13, an enclosure-like G F# around D7's 3rd, the dorian climb with A over Gm9, Db-B enclosing C6 |
| solo 2 | 12 | C2 | 3 | longer 8th lines across the bar lines: Db-C over Bb13, a D-F-Ab triplet, the walk-down's own scales (Abm7: Gb F Eb Cb), the lydian-dominant climb over Gb7#11 to E6, chromatic D Db C into Ab13 |
| solo 3 | 12 | C3 | 5 | the riff figure an octave up into a line, Db-D blue notes, chromatic A B C, the riff's head at F6, a chromatic run A Bb B C into Bbm9, F Gb -> the PEAK G6 (Eb9's 3rd, octaves / locked hands), a scale descent home onto C |
| out 1 | 12 | C1 | 3 | the head near its level |
| out 2 | 12 | C3 | 2 | bars 1-8 restated, the punchline sinks over Bbm9 / Eb9, the riff's head alone in bar 11, a pickup into the tag |
| tag | 4 | F13 Bb13 F13 Bbm6 | 1 | the riff, its answer, the riff an octave down, the minor plagal Bbm6 (Db C Bb G) - not a bII7 approach |
| end | 2 | F13 | 1 | the endless `_ending` in its 'cadenza' style (a short run down into the chord; the v1 blues: rolled) |

## The craft moves (jazz-composition.md)
- A riff head: one 2-bar riff stated three times (re-fitted to IV and to VI7), answered by a punchline; chorus 2 restates
  bars 1-6 and rewrites bars 7-12 by phrase function (a new chart, a new top note) - not a fixed slot.
- Three written charts; the backdoor variant shared by the last solo chorus and the head out.
- Solo: the riff's figure as the motif (displaced, extended, an octave up at the peak), phrases crossing bar lines,
  guide-tone targets, chromatic passing notes on 21-24 % of the off-beat 8ths per chorus, no pure arpeggio bar,
  triplets and quarter / dotted landings (duration entropy 1.70), the peak written as a line arching to G6.
- Velocities from `jazz.touch` per phrase; the left hand breathes per 2 bars (`_lh_breath`).

## Players
- `jazz.chorus` = `pianist.arrange` per part; one `pianist.Memory`; style `straight`, LH `shell`, blues crushes.
- Head: `fill=0.3` (the riff's rests answered by the left hand more than by right-hand fills).
- Solo devices per chorus: single + guide -> guide / 3rds / 6ths -> octave / locked / drop 2 (`climax=True`); touch
  44-84 -> 48-90 -> 56-110; fills only answer / approach / enclosure / stabs.

## Needs from sound design
None (the endless sound, locked); the key choice Eb keeps the riff off the mid band.
