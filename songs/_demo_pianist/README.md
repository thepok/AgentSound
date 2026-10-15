# Pianist A/B: the same notes, before and after the performance rules

Three pieces played by the romantic pianist (`romantic.Score.perform` + the body), each rendered twice:

| folder | piece |
|---|---|
| `newage/` | endless new-age-piano, seed 5 ("Glass Postcards", E major, 73 BPM, flowing) |
| `lantern/` | `songs/pro-newage-lantern`, a hand-written new-age rondo |
| `classical/` | endless classical-piano, seed 3 ("Reverie in E-flat major", 59 BPM, nocturne) |

- `out/ab_new.mp3` is `python -m agentsound build songs/_demo_pianist/<piece>` (the current pianist).
- `out/ab_old.mp3` is the same song.py rendered with the `agentsound` package from before the rules (the master
  the rules were merged onto, exported with `git archive` and run from that folder).

- Round 2: `out/ab2_new.mp3` is the current pianist again and `out/ab2_old.mp3` the round-1 rules (the branch
  state before round 2, run the same way). Round 2 changed the phrase tempo (each phrase draws its own arch, the
  beat lilt drawn per phrase), the left hand's dynamics (ACCOMPANIMENT) and its chord rolls (together / bottom-up,
  an arpeggiated cadence chord now and then).

The composition is deterministic, so both play the same notes. Only the expression differs: the melody lead and
chord spread, pedal timing and half changes, charge, articulation, bass voicing and the lilt's correlated jitter.
The rules, their sources and the measured numbers are in docs/PIANIST_RULES.md.
