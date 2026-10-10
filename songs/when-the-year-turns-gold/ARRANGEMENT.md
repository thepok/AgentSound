# When the Year Turns Gold - arrangement (roles/arranger.md)

62 BPM (verse 56, rubato), Db major, 4/4, straight (no swing anywhere), 72 bars, ~4:59.

| section | bars | time | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 2 | rubato | 1 | piano | a hint of the hook over Gbmaj9, a fermata on F7 (the dominant of Bb minor) |
| verse | 8 | rubato, 56 | 1.5 | voice, piano | "Summer took the early train": Bb minor, the left hand's roots, rolled chords in her gaps, a fermata on Ab7sus |
| A1 | 8 | a tempo 62 | 2 | + bass (two-feel), brush stirs | the hook "When the year turns gold"; the piano answers after "gold", "said", "five"; the backdoor Gbm6 - Cb9 |
| A2 | 8 | | 2.5 | + strings pp | a pad under her, violins I a halo that moves in her gaps; Bm7 - E7b9 into the bridge |
| B | 8 | | 3.5 | strings swell | A major (bVI): "Leaves come down like letters"; back by Gm7 C7 - Fm9 - Bb13 - Ebm9 - Ab7 |
| A3 | 8 | | 3 | piano fills return | the hook, home on Dbmaj9 |
| Ai | 8 | | 3 | instrumental | violins I + II sing the first half of the A in octaves, the piano the second half (harmonized), no doublers |
| B2 | 8 | | 4.5 | full strings, harp gliss in | the climax: violins in octaves on the bridge line, a cello counter-line in half notes, "stay" lifted to Db5; a ritardando in the last 2 bars |
| A4 | 8 | | 3.5 | | the last A turned: "and the gold turns gray" climbs to Db5; the deceptive Fm7 - E°7 |
| tag | 4 | rit | 2.5 | | the hook twice, slowing |
| end | 2 | fermata | 1 | | "gold" held on C5 (the maj7) over Dbmaj9(#11), the harp rolls the chord, the brushes' last stir |

## Changes

- A: `Dbmaj9 | Dbmaj9 Bb7b9 | Ebm9 | Ab13 Ab7b9 | Fm7 E°7 |` + the turnaround of each A (A1 `Ebm9 Db9 | Gbmaj9 |
  Gbm6 Cb9`, A2 `Ebm9 Bb7b9 | Ebm9 Ab13 | Dbmaj9 Bm7 E7b9`, A3 `... | Dbmaj9 Ebm9 Ab13`, A4 `... | Fm7 E°7`).
- B: `Amaj9 | F#m9 B13 | Bm9 E13 | Amaj9 Gm7 C7b9 | Fm9 | Bb13 Bb7b9 | Ebm9 | Ab7sus4 Ab7b9` (B2: Bb7#9).
- Verse: `Bbm9 | Gbmaj9 | Ebm9 | F7sus4 F7b9 | Bbm9 | Gm7b5 C7b9 | Fm9 | Ebm9 Ab7sus4`. Tag: `Ebm9 Ab13 | Fm7 E°7 |
  Ebm9 | Ab7sus4 Ab7b9`, end `Dbmaj9#11`.
- Original: the form (verse + AABA + half chorus from the bridge) and the devices (ii-V chains, a passing diminished,
  a backdoor cadence, a bridge in bVI) are the idiom; no standard's melody, changes or words are used.

## The voice's line

Db4-C5, the top Db5 twice (B2 "stay", A4 "gray"); 1 leap of a 4th+ in 142 intervals (mean 1.77 st), nothing at or
above D5; 5-7 syllables per 2-bar line, a rest after every line. Every A opens with the same rising hook
(F-Gb-Ab-Bb-C), the endings differ (A1 falls to F through the backdoor, A2 / A3 hold F over the turnaround, A4 climbs).

## Players

`singer.sing` (style ballad, takes 0-3, one Memory), `jazz.comp(style='ballad', answer=<her line>)` rolled 16-34 ms
with the pedal, `pianist.arrange(style='ballad')` for the intro, the fills and the half chorus, `jazz.walking_bass`
two-feel straight, `jazzband.brushes(style='ballad', kick=None, fills=False)`, the strings in one `orch.Score` with a
dynamics map per section (pp in A2 to mf in B2), `s.ending` with the rit, the rolled last chord and `last_stir`.
