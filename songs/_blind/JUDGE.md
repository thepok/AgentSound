# Blind judging: composed or generated?

You are a judge in a blind test of solo jazz-piano pieces. Each piece is either **composed** (written note by note
by a human-level composer/arranger) or **generated** (made by a rule-based music generator). The split between the two
is not disclosed. You cannot hear the music; each piece comes as a text packet with its notation and an analysis of
the rendered audio. All pieces were performed and rendered by the same piano player model, the same sound and the same
mix chain, so judge the **music**: the writing, the harmony, the melody, the form and how the performance shapes it.

## What you may read

Only this file and the eight packets in `songs/_blind/packets/` (`<ID>.txt`, the ID is a random four-letter code).
Do **not** open any other file in the repository, do not search it, and do not use git history: other files reveal
the answers, and reading them voids your verdict.

## What a packet holds

- **Header**: key, meter, tempo, feel (straight or swung 8ths), form, length, section layout in bars.
- **Chord chart**: one cell per bar per part (`%` = the chord continues, two symbols = a split bar). Sections use one
  naming scheme for every piece: intro, head (A1 A2 B A3 / A1 B A2 C / blues choruses), solo (choruses), head-out,
  tag, ending.
- **Notation**, bar by bar (bars numbered from 1 over the whole piece):
  - `RH` the right hand's top line: `position:note duration velocity [+n]`. Position is the beat in the bar
    (1 = downbeat, 2.5 = the "and" of 2; swung 8ths land near .58), duration in beats, velocity 1-127, `+n` = n more
    right-hand notes struck with it (a harmonized or chorded melody note). Positions and durations are rounded to
    1/12 beat; small offsets (1.08, 3.17) are the player's timing.
  - `LH` the left hand per chord: its first voicing low to high, the velocity, `(xN)` = N attacks on that chord.
- **Analysis** of the rendered audio: the loudness range, loudness per section relative to the whole piece, the
  dynamic spread of each hand, density per section, the highest and lowest notes and where they fall.

## Your task

Read all eight packets before you decide anything (compare them with each other). Then, for **each** packet:

1. **Verdict**: `generated` or `composed`.
2. **Confidence**: 0-100 (50 = a coin toss, 100 = certain).
3. **The three most telling reasons**, each citing bars (e.g. "bars 41-48: the bridge melody only sequences the A's
   motif a step up, no new idea"). Name what you see in the notes and chords, not a general impression.

Then, in a final section, **advice**: what would make the generated pieces indistinguishable from the composed ones -
concrete, ranked by impact, phrased as changes to the writing (melody, harmony, form, development, voicing, rhythm,
dynamics, the solo), with the bars that show each problem.

## Answer format

```
## <ID>
verdict: generated | composed
confidence: <0-100>
reasons:
1. bars ...: ...
2. bars ...: ...
3. bars ...: ...

... (all eight, in alphabetical ID order)

## Advice
1. ...
```
