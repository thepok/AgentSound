# Blind judging: two evenings' programmes (orchestra)

You are a judge in a blind listening panel. You receive **two programmes**, **set X** and **set Y**. Each is an
evening's concert of **eight orchestral pieces by one composer**, played in the order given (piece 1 opens the
evening, piece 8 closes it). The two programmes are by two different composers. The orchestra is a full symphony
orchestra (strings, woodwinds, horns, trumpets, trombones, tuba, timpani, percussion, harp; some pieces use a smaller
chamber orchestra). The pieces are symphonic movements of different types (an allegro, a 6/8 vivace, a scherzo, a
river journey, an andante; major, minor and modal keys).

You cannot hear the music: each piece comes as a text packet with its orchestration, its notation as played and an
analysis of the rendered audio. All pieces were played by the same performance model, on the same sampled orchestra,
in the same hall, through the same mix chain - so judge the **music** and its **orchestration**.

Your task is about the **programme as a whole**, not the single piece: imagine sitting through each evening in order.
Which composer would you keep listening to after piece 8 - which programme keeps surprising you, and which one
starts to sound like the same piece again?

## What you may read

Only this file and the packets in `set_X/` and `set_Y/` (`01.txt` ... `08.txt`, in programme order). Do **not**
open any other file, do not search outside this folder.

## What a packet holds

- **Header**: key, meter, tempo, length, the section layout in bars (sections are numbered S1, S2, ... in order), the
  roles (instrument sections) the piece uses.
- **Orchestration** per section: which roles sound and their dynamics (marks pp .. ff).
- **Notation**, bar by bar, per role, AS PLAYED: `position:note(+note...)/duration` - position is the beat in the
  bar (1 = downbeat), notes struck together are joined with `+`, the duration (beats) of the top note. `%` = the role
  plays its previous bar again. In 6/8 a bar holds three quarter beats (two dotted-quarter pulses, on 1 and 2.5).
  There is no chord chart: read the harmony from the notes.
- **Analysis** of the rendered audio: the loudness per section, the number of roles sounding per section, the
  highest note and where it falls.

## Your task

Read the programme your prompt names first, all eight pieces in order, then the other one, all eight in order. Read
each programme as a listener would meet it: piece by piece, noting what you have heard before. Then compare.

1. **The choice** (forced): which programme would you keep listening to after piece 8 - `X` or `Y` (no tie) - and
   how strongly: **strength** 1-5 (1 = a coin toss, 3 = a clear preference, 5 = no contest).
2. Per programme:
   - **variety** 1-10: how different the eight pieces are from each other in the things a listener notices - form
     and its proportions, the kinds of opening, the textures of the sections (who plays what over what), the builds,
     the climaxes and their place, the endings, the themes' rhythms, meters, keys and colours (10 = every piece its
     own world, 1 = one piece eight times).
   - **coherence** 1-10: whether the eight pieces sound like one composer with a voice of their own - a recognisable
     identity and quality that carries the evening (10 = a strong, consistent musical personality; 1 = anonymous or
     random).
   - **same_again**: the piece number (2-8) at which this programme started to feel like the same piece again, and
     why (cite the pieces and bars that repeat what you heard earlier), or `never`.
   - **tells**: the repetitions across the programme - plans, section textures, gestures, builds, climaxes, endings,
     figures - that two or more of its pieces share (cite pieces and bars). List as many as you find, most audible
     first.
   - **best** / **weakest**: the piece number you would most / least want to hear again.
3. **Advice**: what would most improve the weaker programme as a programme (variety across the evening, not one
   piece), ranked by impact, with pieces and bars.

## Answer format

```
## Choice
keep: X | Y
strength: <1-5>
why: <two or three sentences: what decided it, citing pieces>

## Set X
variety: <1-10>
coherence: <1-10>
same_again: <2-8> | never
same_why: <what repeated, citing pieces and bars>
tells:
- pieces <a, b, ...>: <the shared plan / texture / gesture, with bars>
- ...
best: <1-8>
weakest: <1-8>

## Set Y
variety: <1-10>
coherence: <1-10>
same_again: <2-8> | never
same_why: <...>
tells:
- pieces <...>: <...>
best: <1-8>
weakest: <1-8>

## Advice
1. ...
```
