# Blind judging: composed or generated? (new-age solo piano)

You are a judge in a blind test of solo piano pieces in the new-age / pop-classical style (the gentle, song-like solo
piano of the 2000s: a singable right-hand tune over flowing broken chords - think Yiruma or Einaudi's song-like
pieces). Each piece is either **composed** (written note by note by a human-level composer) or **generated** (made by
a rule-based music generator). The split between the two is not disclosed. You cannot hear the music; each piece comes
as a text packet with its notation and an analysis of the rendered audio. All pieces were performed and rendered by
the same piano player model (touch, rubato, pedal, the broken-chord left hand's realization), the same sound and the
same mix chain, so judge the **music**: the writing, the melody, the harmony, the form, the left hand's choices and
how the performance shapes it.

## What you may read

Only this file and the packets in `packets/` (`<ID>.txt`, the ID is a random four-letter code). Do **not** open any
other file, do not search outside this folder.

## What a packet holds

- **Header**: key, meter, tempo, length, section layout in bars (sections named intro, A1 A2 ... = the theme's
  statements, B1 B2 = the chorus / contrast, inter = interlude, build, climax, coda - one naming scheme for every
  piece).
- **Chord chart**: one cell per bar per section (`%` = the chord continues, two symbols = a split bar).
- **Notation**, bar by bar (bars numbered from 1 over the whole piece):
  - `RH` the right hand's top line: `position:note duration velocity [+n]`. Position is the beat in the bar
    (1 = downbeat, 2.5 = the "and" of 2), duration in beats, velocity 1-127, `+n` = n more right-hand notes struck
    with it (a harmonized melody note, a chord). Positions and durations are rounded to 1/12 beat; small offsets
    (1.08, 3.17) are the player's timing. `position:(a b c) note duration velocity` = an ornament (a turn, a
    mordent): the quick notes a b c, then the note they decorate.
  - `LH` every left-hand attack in the bar: `position:note` (`a+b` struck together), then the bar's velocity range.
- **Analysis** of the rendered audio: the loudness range, loudness per section relative to the whole piece, the
  dynamic spread of each hand, density per section, the tempo per section as performed, the highest and lowest
  notes and where they fall.

## Your task

Read all packets before you decide anything (compare them with each other). Then, for **each** packet:

1. **Verdict**: `generated` or `composed`.
2. **Confidence**: 0-100 (50 = a coin toss, 100 = certain).
3. **The three most telling reasons**, each citing bars (e.g. "bars 21-28: the chorus melody only sequences the
   theme's cell a step up, no new idea"). Name what you see in the notes and chords, not a general impression.

Then, in a section **Count**, the total: how many of the packets you think are generated (any number from 0 to all
of them - it need not match your per-packet verdicts if you hedged, but say so).

Then, in a final section, **advice**: what would make the generated pieces indistinguishable from the composed ones -
concrete, ranked by impact, phrased as changes to the writing (melody, harmony, form, development, left hand,
rhythm, dynamics, texture), with the bars that show each problem.

## Answer format

```
## <ID>
verdict: generated | composed
confidence: <0-100>
reasons:
1. bars ...: ...
2. bars ...: ...
3. bars ...: ...

... (every packet, in alphabetical ID order)

## Count
generated: <number> of <number of packets>

## Advice
1. ...
```
