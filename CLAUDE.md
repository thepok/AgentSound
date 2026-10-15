# AgentSound

Agent-first offline DAW: songs are Python code, rendered by a C++ engine, judged through an analysis
report and images. The user gives instrumental song wishes in chat; the agent composes, renders,
inspects and iterates, then hands over the mp3/wav.

README.md is the central overview — update it in the same commit whenever you add or change a user-facing feature
(test_readme enforces the basics).

## Layout

README.md section 9 has the repo layout and where to add things; section 2 the engine. The rules for the assets:

- `assets/dx7/` — the 8 DX7 ROM cartridges are not in git: install them per `assets/dx7/README.md` (DX7 voices are
  unavailable without them).
- `assets/samples/` — downloaded sample packs, gitignored (only `manifest.json` is versioned):
  `python -m agentsound samples fetch ID` installs one (SOURCE.json with the license / attribution, INDEX.json).
  Credit CC-BY packs.
- `songs/<slug>/song.py` — one song each; renders go to `songs/<slug>/out/` (gitignored).
- `covers/<slug>/song.py` — private comparison renders of copyrighted music (e.g. a famous line on our sax to
  compare with the record): gitignored, never committed, synced or published.

Open findings live in `TODO.md` - check it before system work, add new findings there, remove an entry when fixed.

## Build & test

```bash
export PATH=/d/compiler/mingw64/bin:$PATH   # e.g.: wherever your MinGW-w64 GCC lives, if it is not on PATH
cmake --preset release && cmake --build --preset release && ctest --preset release
python tests/run.py   # Python tests in parallel (serial: python -m unittest discover -s tests/python)
```

While working, run only the test modules of what you touched (`python tests/run.py endless soloist`, seconds to a
minute); the full `python tests/run.py` runs once before a merge, `--full` (test_notation over every song, ~30 min)
only before a public sync.

## Song workflow (for every user wish)

Songs are produced through the roles in `roles/` (overview: `docs/ROLES.md`): start with `roles/producer.md`, which
runs Brief -> Arrangement -> Composition/players -> Sound design (`roles/arranger.md`, `roles/sound-designer.md`)
-> Mix (`roles/mix-engineer.md`, `python -m agentsound mix`) -> Master (`roles/mastering-engineer.md`,
`python -m agentsound master`) -> A&R (`roles/a-and-r.md`: deliver only after its `ship`). One agent can wear every
hat in order, or each role file is one agent's brief. The steps below are the mechanics every role uses.

1. Read `recipes/HUMAN_FEEDBACK.md` (what the user disliked in earlier songs: never repeat it; append new feedback
   there whenever the user reacts to a song), the matching `recipes/<genre>.md` and `docs/COMPOSE_API.md`. Run `python -m agentsound catalog` once for the
   overview of everything usable (instruments, effects, patches, DX7 voices, SoundFont presets, sample packs with a
   structural index, recipes, analysis profiles, helper functions) and `python -m agentsound find WORD ...` to search
   it (e.g. `find brush`, `find kick 808`, `find reverb dark`) instead of walking `assets/` or the source.
2. Write `songs/<slug>/song.py` (start from `songs/_template/song.py`). Compose deliberately: form,
   harmony with tension/release, memorable hook, variation between repeats, fills and transitions.
3. `python -m agentsound build songs/<slug>` (`--section NAME` for fast iteration on one part).
4. Judge it: read the printed summary + `report.json` (`warnings`, `suggestions`, `clicks`), then LOOK at the images
   (Read tool) — `overview.png` is the index; open only what the question needs (README.md section 6 lists the report
   and the images; `python -m agentsound zoom songs/<slug> --at 1:23.4 [--stem <id>]` for any moment). Check the
   loudness arc per section, masking, low end, harshness, stereo, clicks, whether every part is audible and the note
   dynamics. `flat_dynamics` (a lead whose notes are all equally loud: robotic) must be 0; `silent_notes` (notes that
   reach no sample / piece / layer, or made no audible sound) must be 0 too. When the ears venv is installed,
   `python -m agentsound ears songs/<slug> [--section]` adds learned realism (Audiobox PQ/CE, CLAP P(real); README
   section 6 says which signals are trusted) - a second opinion, not a gate.
5. Compare with a reference when the user names one (or one of the genre is in `assets/refrences/` / `references/`,
   gitignored): `python -m agentsound compare songs/<slug> --ref <audio> [--ref-start --ref-end] [--section]`, LOOK at
   `out/compare/<ref>/compare.png`. Compare like with like (chorus vs chorus). Never copy reference audio into the repo.
6. Iterate on song.py until the mix targets of the recipe are met and there are no serious warnings
   (`python -m agentsound mix songs/<slug>` for the balance, `master songs/<slug> --check` for the delivery).
7. Deliver (README.md section 8: what the build writes - tagged mp3, cover, credits): set `METADATA` / `COVER` in
   song.py, LOOK at cover.png, read the credits warnings (NC / no-redistribution / unclear packs: private listening
   only until checked; CC-BY packs need the printed attribution). Hand over the absolute path of `out/mix.mp3` (and
   wav, cover) with a short description of the song and the credits that matter.

## Engine rules

- Strict everywhere: unknown params/keys are errors, never silently ignored.
- Deterministic: same render JSON + seed ⇒ bit-identical audio. All randomness via `dsp::Rng`.
- No allocation, I/O or exceptions in `process()`. Outputs finite. Only the master chain may add latency.
- New modules: every parameter a `ParamSpec` with a helpful `help` text; the steps are README.md section 9 ("to add").
