# Orchestra player A/B

This folder holds the same notes played twice: before and after the orchestra's performance rules
([docs/ORCHESTRA_RULES.md](../../docs/ORCHESTRA_RULES.md)).

| piece | what | build |
|---|---|---|
| `unbowed/` | songs/unbowed: a symphony first movement in C minor on `symphony_orchestra`, through `orch.Score` | `python -m agentsound build songs/_demo_orchestra_player/unbowed` |
| `film/` | songs/_bands/film_orchestra: the `film_orchestra` preset demo, every part through `orch.perform` | `python -m agentsound build songs/_demo_orchestra_player/film` |

`out/ab_old.mp3` and `out/ab_new.mp3` are both loudness-matched to -20 LUFS integrated (gain only). `out/` is
git-ignored.

- **old:** master at 3e763eb (`git archive` of `agentsound/` and the songs), built with the same song files.
- **new:** this branch. A build here makes the new version (`out/mix.mp3`).

Things to listen for:

- the sections a little apart, most clearly in the slow introduction and the film cue;
- legato lines that connect instead of a fixed 75 ms gap before every note;
- breaths in the winds and brass at phrase points, with held chords staggered;
- one dynamics curve per phrase instead of a 9 dB swell on every long note;
- the melody over the accompaniment;
- in unbowed's Allegro, the sustained notes on the beat with the shorts (they were 56-75 ms late).
