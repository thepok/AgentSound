# Producer

> **Role:** producer - owns one song from the user's wish to the delivered file and runs the other roles.
> **When to use:** every new song wish, and every change request on a song ("the lead is too quiet", "less swing").
> **Inputs:** the user's wish in their words (genre, mood, references, length, instruments, "wie X aber ohne Y"),
> `recipes/HUMAN_FEEDBACK.md`, the matching `recipes/<genre>.md`.
> **Deliverable:** `songs/<slug>/BRIEF.md` (the brief + the production log), a song that passed the A&R, and the
> hand-over: absolute paths of the mp3 / wav / cover, a short description, the credits that matter.

A brief for whoever produces a song in this repo - the main agent, a sub-agent or a person. The producer does not
have to play every part; it decides what the song is, gives each role its brief, checks what comes back against the
brief and the user's ears, and says "done" only after the A&R says "ship".

## The pipeline

| # | stage | role file | writes |
|---|---|---|---|
| 1 | Brief | `roles/producer.md` | `songs/<slug>/BRIEF.md` |
| 2 | Arrangement | `roles/arranger.md` | `songs/<slug>/ARRANGEMENT.md`, the section skeleton of `song.py` |
| 3 | Composition / players | `roles/arranger.md` (players part) | the parts in `song.py` (pianist, drummer, bassist, guitarist, ...) |
| 4 | Sound design | `roles/sound-designer.md` | the sounds + chains in `song.py`, `songs/<slug>/SOUND.md` |
| 5 | Mix | `roles/mix-engineer.md` | module-level `MIX` in `song.py`, `songs/<slug>/MIX.md` |
| 6 | Master | `roles/mastering-engineer.md` | the master chain in `song.py`, `songs/<slug>/MASTER.md` |
| 7 | A&R | `roles/a-and-r.md` | `songs/<slug>/AR.md` (verdict + ranked issues) |

Stages 3 and 4 overlap (a player writes for the sound it plays), and the A&R can send the song back to any stage.
A fix goes to the stage that owns the cause: a flat melody is the player's, a harsh piano the sound designer's, a
buried hook the mixer's, a squashed master the mastering engineer's - never a fader over a composition problem.

**How it runs** - either way works, the files are the same:

- **One agent, all hats**: work through the role files in order, re-read each file when switching hats, write each
  stage's file before starting the next. This is the default for a single song wish.
- **Several agents, one role each**: give each agent its role file as its brief plus the song folder; it returns its
  deliverable and a short hand-over (what it did, open issues). The producer runs them in order (arranger -> sound
  designer -> mix -> master -> A&R), reads each hand-over, and re-runs a stage when the A&R sends it back. Only one
  agent edits `songs/<slug>/song.py` at a time.

## Method

1. **Read** `recipes/HUMAN_FEEDBACK.md` completely (the user's ears: never repeat a mistake listed there), the
   genre recipe, `docs/COMPOSE_API.md`. Run `python -m agentsound catalog` once and `python -m agentsound find WORD`
   to see what exists; `python -m agentsound bands [genre]` for the band presets.
2. **Write `songs/<slug>/BRIEF.md`** (`python -m agentsound new <slug>` creates the song folder from the template):
   - the wish, quoted; the genre + analysis profile (`ANALYSIS = {'profile': ...}`); tempo, key, meter, feel
     (straight or swung - and how much), length;
   - the hook: what carries it (instrument + register) and why it is not beepy; the band preset if one fits;
   - the form in one line (e.g. `intro 4 | A 16 | B 8 | A' 16 | solo 16 | A'' 16 | tag 6`) and the energy arc;
   - references: at most one named track + the excerpt to compare with (chorus vs chorus); `none` is fine;
   - the HUMAN_FEEDBACK rules that apply to this song, as a checklist the A&R will tick;
   - the targets: the recipe's mix targets, the mixer profile, the platform for the master (`auto` unless asked);
   - a `## Log` section: one line per stage (who, what, result, open issues). Append, never rewrite.
3. **Hand out the stages** (above) and read each hand-over against the brief. Build between stages:
   `python -m agentsound build songs/<slug>` (`--section NAME` while iterating), read the summary, look at
   `out/overview.png`.
4. **A&R**: run the A&R role on the final build. `revise` -> send the ranked issues to their owners, rebuild, A&R
   again. `ship` -> deliver.
5. **Deliver**: `METADATA` / `COVER` set (docs/COMPOSE_API.md "Delivery"), LOOK at `out/cover.png`, read the
   credits warnings (NC / no-redistribution / unclear packs: private listening only; CC-BY: print the attribution).
   Hand over the absolute paths of `out/mix.mp3` (or `out/master/mastered.mp3` when the master is a post-pass),
   `out/mix.wav`, `out/cover.png`, a 2-3 sentence description and the credits. Whether and how the file reaches the
   user (chat, phone) is decided by the session that talks to the user, not by this role.
6. **Feedback**: when the user reacts to the song, append it to `recipes/HUMAN_FEEDBACK.md` (date, song, the user's
   words, the rule) and fix it at the system level (patch, preset, player, analysis) when it applies to more than
   this song.

## Checklist (from recipes/HUMAN_FEEDBACK.md)

- A real song, not a loop: form, tension and release, one memorable hook that returns and grows, variation between
  repeats, fills and transitions, counter-lines ("it sounds rather simplistic" was the first verdict ever).
- No beepy lead: "die Lieder scheinen oft als Melodie-Main-Synth etwas Piepsiges zu haben" - the hook sits on a
  real, bright, high sampled piano, a hero sound or a lead with body below 1 kHz.
- The lead is in front: "der Lead ist jetzt zu leise" - bed >= 2-3 dB under the lead in its sections.
- Real dynamics: "sind alle Lead-Noten gleich laut?" - `flat_dynamics` = 0.
- Realism: "möglichst realistische, nicht keyboard-artige Instrumente" - sampled, played, articulated.
- Jazz = piano-led New York bar jazz, "aber ohne Swing": straight 8ths unless the user asks for swing (then light,
  ratio <= 0.58); soft drums (brushes 13-16 dB under the lead: "Drums etwas zu laut"); a warm piano ("es klingt
  hart" was a sound-design fault); pianist moves budgeted ("etwas zu viele von diesen schnellen
  Zwei-Tasten-Wechseln"); the model is Beegie Adair: melody first, polish over virtuosity.
- Hero sounds for hooks and solos: present and "epic", not just loud (lamplight-avenue's sax lacked it).
- No bare oscillators, no Gameboy: every part has its production (the 224XL rooms, echoes, width, a full low end).
- `clicks` = 0 in the mix before delivery.

## Must not

- Never send notifications or messages (no `notify` CLI, no phone delivery) from inside a role run - the session
  that talks to the user decides that.
- Never touch other songs. System work (patches, presets, players, analysis) is validated on ONE reference song in
  a scratch copy (children-of-neon, the song the user chose as the test bed; for jazz perry-street-rain, the "WOW"
  benchmark) - never re-run all songs through a fix.
- Never copy reference audio into the repo (`references/`, `assets/refrences/` are git-ignored; analysis only).
- Never skip the A&R or overrule a `revise` by editing the verdict; fix the issues or tell the user what stays open.
- Never put role files, briefs or song notes in a tool-specific folder (`.claude/`): they live in `roles/` and the
  song folder so any agent or person can use them.
