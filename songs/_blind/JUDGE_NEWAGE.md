# Blind judging: rate the pieces (new-age solo piano)

You are a judge in a blind listening panel of solo piano pieces in the new-age / pop-classical style (the gentle,
song-like solo piano of the 2000s: a singable right-hand tune over flowing broken chords - think Yiruma or Einaudi's
song-like pieces). You cannot hear the music; each piece comes as a text packet with its notation and an analysis of
the rendered audio. All pieces were performed and rendered by the same piano player model (touch, rubato, pedal, the
broken-chord left hand's realization), the same sound and the same mix chain.

Your main task is to RATE THE QUALITY of every piece - as music someone would want to listen to. Some of the pieces
may be machine-generated and some written by human composers; the split is not disclosed and it is only a side
question here.

(The earlier rounds' brief, a composed / generated verdict per packet: JUDGE_NEWAGE_g1g2.md - for the record only.)

The panel has seven judges, each reading with a different lens (stated in your prompt); rate from your own and use
the whole scale - the panel's ratings are compared within each judge, so your own scale is what counts.

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
  tempo per section as performed, per section the right hand's level over the left hand's (dB of note energy;
  negative = the left hand leads) and the share of right-hand notes at or above C6, the dynamic spread of each hand,
  density per section, the highest and lowest notes and where they fall.

## Your task

Read all packets before you rate anything (compare them with each other: use the whole 1-10 scale across the set).
Then, for **each** packet, rate 1-10 (10 = outstanding, 5 = competent but forgettable, 1 = broken):

1. **melody** - memorable, singable, a real hook; shapes that breathe.
2. **harmony** - tension and release, colour, surprise that is earned; voice-leading.
3. **form** - form and drama: does it build to a real climax, do the proportions and section contrasts work, does it
   end well.
4. **development** - is the theme transformed between its statements (varied, reharmonised, extended, fragmented)
   rather than repeated or replaced.
5. **performance** - as written for and played by the hands: the balance between the hands, the register, touch
   and dynamics, pedal-like holds, rubato, whether the right hand sings and the texture flows.
6. **overall** - would I listen to this again.

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
performance: <1-10>
overall: <1-10>
fix: bars ...: ...
moment: bars <a-b>: <what happens> | none
memorable: <0-3>
recurs: bars <...> | none
shared: <IDs> | none
why: <one or two sentences: what decided the overall rating, citing bars>

... (every packet, in alphabetical ID order)

## Count
generated: <number> of <number of packets>

## Advice
1. ...
```
