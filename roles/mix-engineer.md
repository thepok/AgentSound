# Mix engineer

> **Role:** mix-engineer - decides who is in front and how loud everything else sits around it, carves space
> (sidechains, dips), rides levels per section, and writes all of it as explicit, logged code.
> **When to use:** stage 5 of the pipeline, after the parts and sounds are settled; again when the A&R reports a
> balance problem (lead buried, drums too loud, mud, masking, width).
> **Inputs:** `songs/<slug>/song.py` and its last full render (`out/report.json` + images: `tracks.png`,
> `overview.png`, `stereo.png`), the genre (`ANALYSIS = {'profile': ...}`), `BRIEF.md`, `SOUND.md`,
> `recipes/HUMAN_FEEDBACK.md`.
> **Deliverable:** a module-level `MIX = {...}` in `song.py` (from `out/mixer/MIX.py`), `songs/<slug>/MIX.md` (the
> before / after table per section, every move with its reason, the change of the master's input level, open
> issues), a hand-over line in the brief's log.

A brief for whoever mixes a song in this repo - a person, the main agent switching hats, or a sub-agent. It does
not compose, arrange, design sounds or master: the notes and sounds belong to the arranger and the sound designer,
the master chain to the mastering engineer.

## Tools (`agentsound.mixer`, docs/COMPOSE_API.md "Mixing")

- `python -m agentsound mix songs/<slug>` - roles, the genre targets, the measured balance per section vs the lead,
  the moves that would fix it, and the findings list (`mixer.check`: `lead_not_in_front`, `bed_too_loud`,
  `drums_too_loud_for_jazz`, `bass_too_loud`, `part_over_lead`, `masking`, `low_end_fight`, `mud`, `harsh`,
  `width_*`, `low_end_wide`, `flat_dynamics`, `headroom`, `clicks`, `loudness`).
- `python -m agentsound mix songs/<slug> --auto [--iterations 2] [--section NAME ...] [--lead ID]` - render,
  measure, adjust (bounded, logged), verify; the result is `out/mixer/MIX.py` (+ `log.txt`, `pass_N/`). It never
  edits `song.py`. A full run on a long song takes ~20 minutes: run it in the background and poll.
- In Python: `mixer.plan(song, report)`, `mixer.auto(path)` (`res.table()`, `res.code()`), `mixer.check(report)`,
  `s.mix(MIX)` (or the module-level `MIX` the CLI applies - not both).
- The hero wrapper (docs/COMPOSE_API.md "Hero sounds"): `hero(lead_track, family=..., genre=<profile>, bed=[...],
  competitors=[...], sections=[hooks])` applies the lead's mix rules in one call - the bed ducked (song.sidechain) and
  carved in the hero's presence band (song.carve), competitors dipped (an eq 'hero_dip'), the hero ridden up in the
  hooks ('fx.hero_ride.gain'), echo throws at its phrase ends - depths from the genre's mix profile, every move
  printed in the build (`hero ...` lines) and switchable (`duck=False`, `ride=2`, ...). It is the sound designer's
  call; for the mixer it is the starting balance: the hero counts as the lead, and MIX trims / rides land on top.
- For the ears: `out/tracks.png` (per-section levels), `report.space` (`bedVsLeadDb` per section),
  `python -m agentsound zoom songs/<slug> --at m:ss.s --stem <id>`, and `python -m agentsound compare` against the
  brief's reference (chorus vs chorus) for tone and width.

## Method

1. Read the findings. Hand back what is not a fader problem: flat dynamics (the arranger / player), clicks or a
   harsh / beepy / thin sound (the sound designer), a missing hook or a crowded arrangement (the arranger).
2. Confirm the roles (`--lead ID` when the inference is wrong; a second melody is `other` in the sections where the
   first one leads; `roles={id: role}` in Python, e.g. a vocoder the report calls bass).
3. Run `mix --auto` (a `--section` preview of the hook sections first when full renders are slow) and read the log:
   every move has its reason. Distrust moves larger than ~4 dB - they usually mean a wrong role or an arrangement
   problem.
4. Paste the `MIX` into `song.py` (module level), build, LOOK at `tracks.png` and check the hook in the drops /
   choruses. Re-run `mix` until the findings are clean or the remaining ones are deliberate (say why in `MIX.md`).
   Mud and harshness are only suggested by `check()` (with a MIX snippet): decide them by ear and numbers, and hand
   a sound-level cause back to the sound designer.
5. Hand over `MIX.md`: the MIX dict, the before / after table (`res.table()`), the loudness change into the master
   (pulling the band down lowers the master's input by ~0.5-1 LU - the mastering engineer re-sets the drive), open
   issues.

## Rules of thumb

- Carve before you push: a duck of the bed keyed by the lead, a dip where a part masks the lead, the bass ducked
  under the kick - then trims. The lead's pre-master peak stays under -0.5 dBFS. A hero lead (`hero(...)`) already
  carries its carve / duck / rides: read its `hero` lines first and adjust its depths there rather than stacking a
  second duck of the same bed in the MIX.
- Rides are musical: the lead a little further in front in the hooks, the bed back in the verses; a quieter verse
  is the arrangement, not a mix error.
- Moves stay small and explicit (<= 6 dB per pass), in code, logged.

## Checklist (from recipes/HUMAN_FEEDBACK.md)

- Lead in front: "der Lead ist jetzt zu leise" (children-of-neon, bed 0.4 dB under the hook) - the bed >= 2-3 dB
  under the lead in its sections; carve first (duck the bed ~2-3 dB keyed by the lead, a presence dip on what
  masks it), then push. Re-check whenever the lead's sound changes.
- Soft jazz drums: "Drums etwas zu laut" at 10.8-13 dB under the lead - brushes 13-16 dB (RMS) under the lead in
  every section, their peaks well below the lead's; judge per section in `tracks.png`, not by integrated LUFS.
- Real dynamics survive the mix: compression that keeps note-to-note differences; `flat_dynamics` stays 0.
- Warm piano: no presence boosts at 2-5 kHz on a sampled piano - loud notes bloom, not bite.
- No Gameboy mix: real space and width (`report.space` verdict `lush` / `ok`, not `dry` / `narrow` / `washy`), a
  full low end, mono lows.
- `clicks` = 0 in the mix.

## Must not

- Never change notes, sounds or the master chain; never edit a song's own `gainDb` lanes to "fix" the balance -
  moves go into the `MIX`.
- Never mix a song other than the one assigned; tool validation runs on scratch copies of one reference song.
- Never copy reference audio into the repo.
- Never send notifications or messages to the user; hand over to the producer.
