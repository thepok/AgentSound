# Blind judging: rate the pieces (orchestra)

You are a judge in a blind listening panel of orchestral pieces for a full symphony orchestra (strings, woodwinds,
horns, trumpets, trombones, tuba, timpani, percussion, harp; some pieces use a choir pad, some a smaller chamber
orchestra). The pieces are symphonic movements of different types (an allegro, a 6/8 vivace, a scherzo, a river
journey, an andante; major, minor and modal keys). You cannot hear the music;
each piece comes as a text packet with its orchestration, its notation as played and an analysis of the rendered
audio. All pieces were played by the same performance model (dynamics, phrasing, timing), on the same sampled
orchestra, in the same hall, through the same mix chain - so judge the **music** and its **orchestration**.

Your main task is to RATE THE QUALITY of every piece - as music someone would want to listen to, in its own idiom
(a nocturne is not worse for being slow, an allegro is not better for being loud). Some of the pieces may be
machine-generated and some written by human composers; the split is not disclosed and it is only a side question.

The panel has seven judges, each reading with a different lens (stated in your prompt); rate from your own and use
the whole scale - the panel's ratings are compared within each judge, so your own scale is what counts.

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
  beat; small offsets are the players' timing (0.92 = just before the downbeat). In 6/8 a bar holds three quarter
  beats (two dotted-quarter pulses, on 1 and 2.5). There is no chord chart: read the harmony from the notes. A bar
  without attacks shows the roles still holding notes from before or `(rest)`. Percussion notes are named by
  instrument (crash, cymbal_roll, bass_drum, ...); timpani notes are the drum's pitch.
- **Analysis** of the rendered audio: the loudness range, loudness per section relative to the whole piece, the
  number of roles sounding per section, the highest note and where it falls.

## Your task

Read all packets before you rate anything (compare them with each other: use the whole 1-10 scale across the set).
Then, for **each** packet, rate 1-10 (10 = outstanding, 5 = competent but forgettable, 1 = broken):

1. **melody** - the themes: memorable, a real hook or motto, shapes that breathe.
2. **harmony** - tension and release, colour, modulation that is earned; voice-leading.
3. **form** - form and drama: contrast between sections, the build to a real climax, the proportions, the ending.
4. **development** - is the material transformed between its statements (sequenced, fragmented, inverted,
   recoloured, combined, passed between instruments) rather than repeated or replaced.
5. **orchestration** - who carries what, the parts lying well on their instruments, spacing and doublings, colour
   changes and their timing, textures that change inside sections, balance (would the line be heard?).
6. **life** - energy and motion: does something happen, does the music move forward (rhythmic drive, running
   figures, dialogue between the choirs, dynamic contrast) - or does it stand still.
7. **overall** - would I listen to this again.

Then **fix**: the single most important change that would make this piece better, with the bars it concerns.

Then **the memorable moment**: the one moment of this piece you would remember - in the notes, with its bars -
and how memorable it is:

- **moment**: `bars <a-b>: <what happens, in the notes>`, or `none`.
- **memorable** 0-3:
  - 0 none - nothing stands out;
  - 1 a pleasant texture or a loud peak, nothing you would recognise again;
  - 2 a distinct gesture you would recognise if the piece came back to it;
  - 3 a gesture planted early, brought back changed, paying off at the high point or the end.
- **recurs**: the bars where the same gesture appears before or after (changed or not), or `none`.
- **shared**: the IDs of other packets with the same gesture (the same kind of moment, not merely the same style),
  or `none`.

Then **template**: the IDs of other packets that follow the SAME PLAN as this one - the same recipe of sections and
textures in the same order (e.g. the same kind of opening, the same development textures, the same build into the
same kind of climax, the same ending), so that the two would sound like one piece-making formula - or `none`. Name
a packet only when the plan itself is shared, not for a common style or instrument.

Then **the masterpiece question** - an ABSOLUTE bar, not relative to the other packets: how close is this piece to a
true masterpiece of the concert repertoire?

- **masterpiece** 1-10: 10 = canon repertoire (a movement the world keeps playing), 7 = a solid professional concert
  work, 5 = competent but anonymous, 3 = a student exercise. Use the absolute scale even if every packet lands low.
- **missing**: one located sentence - what is missing for this piece to be a true masterpiece (`bars <a-b>: ...`).

At the end, a section **Count** (a side question): how many of the packets you think are machine-generated (any
number from 0 to all of them), and a section **Advice**: the changes that would most improve the weaker pieces as a
group, ranked by impact, with bars.

## Answer format

```
## <ID>
melody: <1-10>
harmony: <1-10>
form: <1-10>
development: <1-10>
orchestration: <1-10>
life: <1-10>
overall: <1-10>
fix: bars ...: ...
moment: bars <a-b>: <what happens> | none
memorable: <0-3>
recurs: bars <...> | none
shared: <IDs> | none
template: <IDs> | none
masterpiece: <1-10>
missing: bars ...: ...
why: <one or two sentences: what decided the overall rating, citing bars>

... (every packet, in alphabetical ID order)

## Count
generated: <number> of <number of packets>

## Advice
1. ...
```
