# Blind judging: composed or generated? (pipe organ)

You are a judge in a blind test of pipe-organ pieces in the church repertoire (chorale preludes, chorales and their
variations, trios, French-romantic toccatas, meditations / elevations, trumpet tunes and festive postludes). Each piece
is either **composed** (written note by note by a human-level composer-organist) or **generated** (made by a
rule-based music generator). The split between the two is not disclosed. You cannot hear the music; each piece comes
as a text packet with its registration, its notation as played and an analysis of the rendered audio. All pieces were
played by the same organist model (articulation, ornaments, breaths, timing), on the same sampled church organ, through
the same mix chain - so judge the **music**: the writing (melody, counterpoint and voice-leading, harmony and
cadences, form, texture), the registration plan and how the performance shapes it.

## What you may read

Only this file and the packets in `packets/` (`<ID>.txt`, the ID is a random four-letter code). Do **not** open any
other file, do not search outside this folder.

## What a packet holds

- **Header**: key, meter, tempo, length, the section layout in bars (sections are numbered S1, S2, ... in order).
- **Registration** per section: which stops (tracks) sound - a track is one registration on one manual (Great,
  Swell, Positive) or the pedal; the swell box's opening range where it moves (the swell pedal's crescendo /
  diminuendo). An organ has no touch dynamics: its loudness is the registration and the swell box.
- **Notation**, bar by bar, per registration track, AS PLAYED: `position:note(+note...)/duration` - position is the
  beat in the bar (1 = downbeat), notes struck together are joined with `+`, the duration (beats) of the top note
  shows the articulation (legato = touching the next attack, detached = shorter). Positions and durations are rounded
  to 1/12 beat; small offsets are the player's timing. There is no chord chart: read the harmony from the notes.
- **Analysis** of the rendered audio: the loudness range, loudness per section relative to the whole piece, attacks
  per bar per track and section, the highest manual note and where it falls, the pedal's range.

## Your task

Read all packets before you decide anything (compare them with each other). Then, for **each** packet:

1. **Verdict**: `generated` or `composed`.
2. **Confidence**: 0-100 (50 = a coin toss, 100 = certain).
3. **The three most telling reasons**, each citing bars (e.g. "bars 21-28: the pedal only repeats the chord roots
   in quarters, never a line"). Name what you see in the notes, not a general impression.

Then, in a final section, **advice**: what would make the generated pieces indistinguishable from the composed ones -
concrete, ranked by impact, phrased as changes to the writing (melody, counterpoint, harmony, cadences, form, texture,
registration, articulation, ornaments, timing), with the bars that show each problem.

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

## Advice
1. ...
```
