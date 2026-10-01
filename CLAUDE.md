# AgentSound

Agent-first offline DAW: songs are Python code, rendered by a C++ engine, judged through an analysis
report and images. The user gives instrumental song wishes in chat; the agent composes, renders,
inspects and iterates, then hands over the mp3/wav.

README.md is the central overview — update it in the same commit whenever you add or change a user-facing feature
(test_readme enforces the basics).

## Layout

- `agentsound/` — Python compose layer (stdlib only): theory, patterns, humanize, Song builder, patches, CLI.
- `engine/` — C++20 renderer. `core/` interfaces + params (frozen contract), `dsp/Dsp.h` shared DSP,
  `instruments/` (va, dx7, drums, sf2, sampler, stack = layered children), `fx/` (dynamics, time, premium effects), `analysis/` (report + PNGs,
  file analysis + reference comparison), `art/` (cover art + the project's public-domain stroke font),
  `render/` (song parser, routing graph, registry), `io/` (WAV), `main.cpp` (CLI).
- `docs/RENDER_FORMAT.md` — the JSON contract between Python and the engine. `docs/COMPOSE_API.md` — the song API.
  `docs/PARAMS.md` — generated parameter reference (`build/agentsound.exe params --markdown`).
- `recipes/` — genre guides (sound palette, progressions, arrangement, mix targets). Read before composing.
- `roles/` — tool-agnostic production role briefs (producer, arranger, sound-designer, mix-engineer,
  mastering-engineer, a-and-r); `docs/ROLES.md` is the overview.
- `songs/<slug>/song.py` — one song each; renders go to `songs/<slug>/out/` (gitignored).
- `assets/dx7/` — the 8 original DX7 ROM cartridges (256 voices), not in git: install them per
  `assets/dx7/README.md` (DX7 voices are unavailable without them). `build/agentsound.exe dx7 [search]` lists them.
- `assets/soundfonts/` — GeneralUser GS (full GM/GS set). `python -m agentsound sf2 [search]` lists presets.
- `assets/samples/` — downloaded sample packs (gitignored; only `manifest.json` is versioned: url, license, genres).
  `python -m agentsound samples` lists them, `samples fetch ID` installs one (unpacks, FLAC→WAV, writes
  SOURCE.json with the license/attribution and INDEX.json with the folder structure). Credit CC-BY packs.

Open findings live in `TODO.md` - check it before system work, add new findings there, remove an entry when fixed.

## Build & test

```bash
export PATH=/d/compiler/mingw64/bin:$PATH   # e.g.: wherever your MinGW-w64 GCC lives, if it is not on PATH
cmake --preset release && cmake --build --preset release && ctest --preset release
python -m unittest discover -s tests/python
```

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
3. `python -m agentsound build songs/<slug>` — renders `out/mix.wav`, `out/mix.mp3`, `out/report.json` and the
   image set. Use `--section NAME` for fast iteration on one part.
4. Judge it: read the printed summary + `report.json` (`warnings`, `suggestions`, `clicks`), then LOOK at the images
   (Read tool) — `overview.png` is the index; open only what the question needs: `loudness.png` (energy arc),
   `tracks.png` (who plays when, per-section levels), `bands.png` (spectral balance vs reference), `stereo.png`,
   `spectrogram.png` + `spectrogram_NN_<section>.png` (zoomed detail), `clicks/click_NN.png` (sample-level zooms of
   detected clicks). Inspect any moment: `python -m agentsound zoom songs/<slug> --at 1:23.4 [--stem <id>]`.
   Check loudness arc per section, masking, low end, harshness, stereo, clicks, whether every part is audible,
   and note dynamics: the summary's "note dynamics" lines / `nodes[].dynamics` (10-90 % spread of each melodic
   track's note levels per phrase next to the velocities it was given); `flat_dynamics` (a lead whose notes are all
   equally loud: robotic) must be 0. `silent_notes` (notes that reach no sample / drum piece / unmuted layer - the
   build prints them before rendering - or made no audible sound in the render: `nodes[].silentNotes`) must be 0 too.
5. Compare with a reference: when the user names a reference track (or one of the genre is available, e.g. in
   `assets/refrences/` or `references/`, gitignored), run `python -m agentsound compare songs/<slug> --ref <audio> [--ref-start 1:02
   --ref-end 1:32] [--section chorus]` and LOOK at `out/compare/<ref>/compare.png`: loudness-matched spectrum and
   difference, width per octave, loudness distribution, punch, prioritised suggestions with render-format fixes
   (compare.json). Compare like with like (chorus vs chorus). Never copy reference audio into the repo.
6. Iterate on song.py until the mix targets of the recipe are met and there are no serious warnings
   (`python -m agentsound mix songs/<slug>` for the balance, `master songs/<slug> --check` for the delivery).
7. Deliver: the build already wrote `out/credits.txt`, `out/cover.png` and tagged `out/mix.mp3` (title, artist, album,
   genre, year, BPM, key, credits in the comment, the cover embedded). Set `METADATA = {...}` / `COVER = {'style':
   ...}` in song.py (docs/COMPOSE_API.md "Delivery"), LOOK at cover.png, and read the credits warnings: NC /
   no-redistribution / unclear packs are fine for private listening but must be checked before publishing; CC-BY
   packs need the printed attribution. Deliver the absolute path of `out/mix.mp3` (and wav, cover) with a short
   description of the song and the credits that matter.

## Engine rules

- Strict everywhere: unknown params/keys are errors, never silently ignored.
- Deterministic: same render JSON + seed ⇒ bit-identical audio. All randomness via `dsp::Rng`.
- No allocation, I/O or exceptions in `process()`. Outputs finite. Only the master chain may add latency.
- New modules: implement `Instrument`/`Effect` from `engine/core/Module.h`, declare every parameter as a
  `ParamSpec` with a helpful `help` text, register in `engine/render/Registry.cpp`, add `tests/test_<name>.cpp`.
