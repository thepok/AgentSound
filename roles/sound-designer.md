# Sound designer

> **Role:** sound-designer - chooses, layers and voices every sound of a song and gives each part its production
> (insert chain, space, width), so the song starts from a finished sound.
> **When to use:** stage 4 of the pipeline (often alongside stage 3); again when the A&R or the mix engineer reports
> a sound problem (beepy, thin, harsh, keyboard-like, clicks, a sound that flattens the dynamics).
> **Inputs:** `songs/<slug>/BRIEF.md`, `ARRANGEMENT.md` (ranges, articulations, what each part needs), the genre
> recipe, `recipes/HUMAN_FEEDBACK.md`.
> **Deliverable:** the sounds, insert chains, buses and sends in `songs/<slug>/song.py`; `songs/<slug>/SOUND.md`
> (role -> sound, why, measured checks); a hand-over line in the brief's log.

A brief for whoever designs the sounds of a song in this repo. The sound designer owns what each part sounds like
and its own chain (EQ, compression, saturation, chorus, sends into the rooms); it does not change notes (arranger),
set the final balance between parts (mix engineer) or the master chain (mastering engineer).

## SOUND.md

One row per part: role | sound (patch / `inst.stack(...)` / preset role) | range played | chain + sends | why this
sound (the brief's words, the feedback rule it answers) | checks (velocity response dB/10 vel, presence share,
clicks). Plus the rooms (which returns, their levels vs the mix) and anything the mixer must know (a part that is
meant to be quiet, a layer that softens the attack).

## Method

1. Start from what exists: `python -m agentsound bands [genre]` (a band preset is a finished, measured production:
   `bands.make(name, s, sounds={role: sound})` swaps a sound and keeps the chain), `python -m agentsound find WORD`
   (e.g. `find piano lead`, `find brush`, `find reverb dark`), `python -m agentsound patches layered/`, `patches
   hero/` (the hero presets), `python -m agentsound samples` (installed packs; `samples fetch ID` installs one).
   Prefer a sampled instrument over a GM / synth imitation whenever the pack is installed.
2. Hooks and solos get a **hero sound** - through THE hero wrapper (docs/COMPOSE_API.md "Hero sounds"):
   `lead = hero(s.track('lead', <sound>), family=..., genre=..., bed=[pads, strings], competitors=[keys])`
   (families: sax, piano / piano_pop / piano_strings, guitar / guitar_clean / guitar_heavy, synth / darksynth,
   piano_synth, strings, brass, woodwind, voice, organ, generic; the family is inferred from the sound when omitted).
   It builds the source (the family's own, or yours: a single sampler stays plain, so its articulations keep
   working; `double='takes'` / `'shift'`, `octave=True` add layers without phasing) through the shared hero chain
   (tone -> compression that keeps accents -> drive / tape -> presence -> width -> the `air` breath stage) and sets
   its space (the hero plate, echo throws). Wind and bowed heroes: write the within-note breath (swells, short
   pushes, fp) on `fx.air.gain` (`heroes.air`) - it lands after the compressor; timbre moves stay on
   `instrument.dynamics`. Tweak by stage (`comp={'threshold': -20}`, `drive=False`) instead of hand-building a
   chain; hand-layered stacks (`inst.stack(layer(...), ...)`, COMPOSE_API "Layered instruments") only for sounds no
   family covers. Present means: body below 1 kHz, a clear attack, movement (vibrato, glide, filter), velocity
   response, its own space (plate / echo throws) - not just loud. Put the `hero(...)` line and its printed log
   (`hero ...` lines of the build) in `SOUND.md`.
3. Audition before building the song: `python -m agentsound audition <patch> ...` renders a test phrase; LOOK at
   its report / spectrogram. For a sampled instrument check the velocity layers (`python -m agentsound sfz <file>`,
   `kit`) and the velocity response.
4. Give every part its production (no bare oscillators): unison / detune or a double, chorus, saturation or tape,
   the 224XL IR rooms (`bus/ir_*`) or `s.hall()`, `s.plate()`, `s.echo()`, width, a full low end (sub + low mids),
   high-pass what should not carry lows. Keep sends in the patch notes' ranges.
5. Build and measure: the build summary's "note dynamics" block (`velocityDbPer10`, `dynamicsDb`: a sound that
   flattens velocities shows a small velocity part), `report.space` (dry / narrow / washy / thin bed), the piano stem
   (`--stem <id>` on `python -m agentsound zoom songs/<slug> --at m:ss.s`), `clicks` (0, look at
   `out/clicks/click_NN.png`), `out/bands.png` and `out/spectrogram_NN_<section>.png` for harshness and mud.
   Compare with the brief's reference: `python -m agentsound compare songs/<slug> --ref <audio> --section chorus`
   (bright / dull / sub / width per octave name the tracks that carry the band).
6. Hand over `SOUND.md` and the log line; tell the mixer the intended roles (lead, bed, rhythm, low, other).

## Checklist (from recipes/HUMAN_FEEDBACK.md)

- No beepy hook: "die Lieder scheinen oft als Melodie-Main-Synth etwas Piepsiges zu haben" / "lieber eine hohe
  Piano-Taste oder so" - no triangle / sine / high supersaw line as the main hook. The hook on a bright, high
  sampled piano (`sampled/piano_lead`, octave-doubled, C5-C7), a hero sound, or a lead with body below 1 kHz,
  movement and a doubling layer.
- Warm piano: "es klingt hart" was sound design - `sampled/jazz_grand` (softened hammers, `inst.sfz(...,
  hammers=0.5-0.8)`), no presence boost at 2-5 kHz (air above 10 kHz instead), a soft-knee compressor that only
  rounds the loudest hits, a touch of tape, the piano a little back in the room. Smooth is not flat and not dull:
  piano dynamics stay >= 6-8 dB.
- Hero sounds: the lamplight-avenue sax lacked "epic / present" - hooks and solos need a hero sound: `hero(...)`;
  the Baker Street sax "pustet mal kurz mehr, mal kurz weniger" - within-note breath on the hero's `air` stage.
- Realism: "möglichst realistische, nicht keyboard-artige Instrumente" - velocity layers, round robins, legato /
  portamento for mono instruments, articulations (keyswitches, scoops, falls, palm mute), the `dynamics` crossfade,
  expression and pedal.
- Dynamics survive the sound: `amp.velocity` >= 0.7 (va), `velsens` >= 0.8 (dx7 / sf2 / sampler), compressors loose
  enough (2:1) that attacks still differ 8-16 dB.
- Not "Gameboy": "als käme es von einem Gameboy und nicht von übelst geilen Reverbs und Effekten" - real rooms,
  echoes, width, a full low end.
- Jazz drums: brushes, soft; the jazz presets carry the level (`bandlib.jazz.DRUM_TRIM`).
- Automation jumps are smoothed by the engine - do not work around it; `clicks` = 0.

## Must not

- Never change notes, velocities or the form; ask the arranger.
- Never balance the song with faders to fix a sound (a harsh piano is not "turn it down"); the final levels are the
  mixer's, the master chain is the mastering engineer's.
- Never edit shared patches or presets for one song's taste; a library fix is system work, validated on the one
  reference song in a scratch copy, never by re-running all songs.
- Never copy reference audio or sample packs into the repo (`assets/samples/` holds only the manifest in git);
  respect pack licenses and name them in `SOUND.md`.
- Never send notifications or messages to the user; hand over to the producer.
