# Blind judging: composed or generated? (orchestra)

You are a judge in a blind test of lyrical orchestral pieces in the film / new-age concert idiom (a hopeful theme, a
longing woodwind solo, an epic horn tune, a pastoral or night-time nocturne - the register of Horner, Portman,
Desplat, Hisaishi, Morricone's lyrical scores). Each piece is either **composed** (written note by note and
orchestrated by a human-level composer-orchestrator) or **generated** (made by a rule-based music generator and a
rule-based orchestrator). The split between the two is not disclosed. You cannot hear the music; each piece comes as
a text packet with its orchestration, its notation as played and an analysis of the rendered audio. All pieces were
played by the same performance model (dynamics, phrasing, timing), on the same sampled orchestra, in the same hall,
through the same mix chain - so judge the **music**: the writing (melody, harmony and cadences, counter-melodies,
form) and the **orchestration** (which instruments carry what, spacing and doublings, colour changes, the texture's
density over the piece, the climax, the dynamics plan).

## What you may read

Only this file and the packets in `packets/` (`<ID>.txt`, the ID is a random four-letter code). Do **not** open any
other file, do not search outside this folder.

## What a packet holds

- **Header**: key, meter, tempo, length, the section layout in bars (sections are numbered S1, S2, ... in order), the
  roles (instrument sections) the piece uses.
- **Orchestration** per section: which roles sound and their dynamics (the range of the dynamics lane - or, for harp,
  timpani and percussion, the velocities - as marks pp .. ff).
- **Notation**, bar by bar, per role, AS PLAYED: `position:note(+note...)/duration` - position is the beat in the
  bar (1 = downbeat), notes struck together are joined with `+` (a section playing divisi chords), the duration
  (beats) of the top note. `%` = the role plays its previous bar again. Positions and durations are rounded to 1/12
  beat; small offsets are the players' timing. There is no chord chart: read the harmony from the notes. A bar
  without attacks shows the roles still holding notes from before (`no attack - held: ...`) or `(rest)` (silence).
  Percussion notes are named by instrument (crash, cymbal_roll, bass_drum, ...); timpani notes are the drum's pitch.
- **Analysis** of the rendered audio: the loudness range, loudness per section relative to the whole piece, the
  number of roles sounding per section, the highest note and where it falls.

## Your task

Read all packets before you decide anything (compare them with each other). Then, for **each** packet:

1. **Verdict**: `generated` or `composed`.
2. **Confidence**: 0-100 (50 = a coin toss, 100 = certain).
3. **The three most telling reasons**, each citing bars (e.g. "bars 21-28: the violas and second violins hold the
   same whole-note chord tones under every melody, never a line"). Name what you see in the notes, not a general
   impression.

Then, in a final section, **advice**: what would make the generated pieces indistinguishable from the composed ones -
concrete, ranked by impact, phrased as changes to the writing and the orchestration (melody, harmony, counter-lines,
form, voicing and spacing, doublings, colour changes, texture density, dynamics, the climax), with the bars that show
each problem.

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
