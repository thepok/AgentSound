# Production roles

A song is produced by six roles, each described by a plain Markdown brief in `roles/<role>.md` (a seventh, the
film director, makes the song's making-of film after delivery). The files are
tool-agnostic: a single agent can work through them in order, several agents can each be given one file as their
brief, or a person can follow them. Each file starts with the same header block (Role, When to use, Inputs,
Deliverable), then the mission, the method with this repo's commands, a checklist distilled from
`recipes/HUMAN_FEEDBACK.md`, and what the role must not do.

## Who does what

| role | file | owns | writes (in `songs/<slug>/`) |
|---|---|---|---|
| producer | `roles/producer.md` | the song from wish to delivery; runs the other roles; the brief and the log | `BRIEF.md` (+ `METADATA` / `COVER`, delivery) |
| arranger | `roles/arranger.md` | form, harmony, hook, transitions; the parts, performed by the players (pianist, drummer, bassist, guitarist, horn lines) | `ARRANGEMENT.md`, sections + parts in `song.py` |
| sound-designer | `roles/sound-designer.md` | every sound, layer and hero sound; each part's own chain, rooms and sends | sounds / chains in `song.py`, `SOUND.md` |
| mix-engineer | `roles/mix-engineer.md` | the balance vs the lead, carving (ducks, dips), rides per section (`agentsound.mixer`) | module-level `MIX` in `song.py`, `MIX.md` |
| mastering-engineer | `roles/mastering-engineer.md` | tone balance, loudness for the platform, peaks, width, mono (`agentsound.mastering`) | master chain in `song.py`, `out/master/`, `MASTER.md` |
| a-and-r | `roles/a-and-r.md` | the critic: verdict `ship` / `revise` with ranked issues, each with its owner | `AR.md` |
| film-director | `roles/film-director.md` | after delivery: the song's making-of film, made to measure from its logs (`python -m agentsound makingof`) | `film.py`, `out/making-of.mp4` |

## The pipeline and the hand-offs

```
wish ─> producer: BRIEF.md
          └─> arranger: ARRANGEMENT.md + sections        (2 Arrangement)
               └─> arranger: parts via the players       (3 Composition / players)
                    └─> sound-designer: SOUND.md         (4 Sound design, overlaps 3)
                         └─> mix-engineer: MIX + MIX.md  (5 Mix)
                              └─> mastering-engineer: master chain + MASTER.md   (6 Master)
                                   └─> a-and-r: AR.md    (7 A&R)
                                        ├─ revise: each issue back to its owner role, then A&R again
                                        └─ ship: producer delivers
```

- Every role appends one line to the `## Log` of `BRIEF.md` when it hands over (who, what, result, open issues).
- A problem goes to the role that owns its cause: flat or robotic playing -> arranger; beepy, harsh, thin sounds and
  clicks -> sound-designer; a buried lead, loud drums, mud / masking -> mix-engineer; loudness, peaks, broad tone,
  mono -> mastering-engineer. A later stage never covers an earlier stage's problem (no fader over a composition
  problem, no master EQ over a mix problem).
- Only one role edits `song.py` at a time. The mix lives in its own `MIX` dict and the master in the master chain, so
  the stages stay separable and re-runnable.
- The A&R never fixes anything and never softens a verdict; the producer delivers only after `ship`.

## Running it

- **One agent**: read `roles/producer.md`, then switch hats stage by stage, re-reading each role file.
- **Several agents**: the producer gives each agent its role file + the song folder and waits for the deliverable;
  stages run in order (the A&R ideally in a fresh agent that did not write the song).
- **Tools per role**: `python -m agentsound catalog` / `find` / `bands` / `patches` / `audition` (sound-designer,
  arranger), the players `agentsound.pianist` / `drummer` / `bassist` / `guitarist` / `jazz` (arranger),
  `build` / `zoom` / `compare` (everyone), `mix [--auto]` (mix-engineer), `master [--render | --check]`
  (mastering-engineer), the report + images (A&R). The APIs are in `docs/COMPOSE_API.md`.

## Rules for every role

- Read `recipes/HUMAN_FEEDBACK.md` first; append new user reactions there (date, song, words, rule).
- Work only on the assigned song; system fixes are validated on one reference song in a scratch copy, never by
  re-running all songs.
- Never copy reference audio or sample packs into the repo.
- Roles never send notifications or messages; delivery to the user is the calling session's decision.
