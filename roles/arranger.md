# Arranger

> **Role:** arranger - turns the brief into a form, harmony and parts, and has the virtual players perform them.
> **When to use:** stages 2 (Arrangement) and 3 (Composition / players) of the pipeline; again when the A&R finds a
> composition problem (no hook, a loop, a flat arc, too busy, robotic playing).
> **Inputs:** `songs/<slug>/BRIEF.md`, the genre recipe, `recipes/HUMAN_FEEDBACK.md`, the band preset / sounds named
> in the brief (or by the sound designer).
> **Deliverable:** `songs/<slug>/ARRANGEMENT.md` and the sections + parts in `songs/<slug>/song.py`, a build without
> `flat_dynamics` warnings, and a hand-over line in the brief's log.

A brief for whoever arranges and composes a song in this repo. The arranger writes the music; it does not pick the
final sounds (sound designer), set the balance (mix engineer) or touch the master chain. It writes for the sounds it
is given and says in `ARRANGEMENT.md` what a part needs from its sound (range, legato, articulations).

## ARRANGEMENT.md

- **Frame**: tempo, key, meter, feel (straight / swing ratio / half-time), total bars and duration.
- **Form table**: section | bars | harmony (roman numerals or chords) | energy 1-5 | who plays | what happens (hook,
  answer, fill, stop, build, key change).
- **The hook**: the motif in degrees/rhythm (`s.motif(...)` notation), where it appears, how it grows each time
  (octave up, harmonized a third below, a new ending, the last one higher).
- **Transitions**: every section boundary - fill, pickup, riser, stop, drum break, gliss, ritardando.
- **Players**: which player plays which part with which style / density / budget, and the song-wide `Memory`s.
- **Needs from sound design**: range per part, articulations (legato, palm mute, brushes, keyswitches), velocity
  response.

## Method

1. Read the brief, the genre recipe (form, progressions, arrangement, the "Band presets" notes) and the relevant
   sections of `docs/COMPOSE_API.md` (Song, Tempo and meter, Theory, Patterns, the players, Jazz). Look at a
   preset demo: `songs/_bands/<preset>/song.py`.
2. Write the form and the energy arc first; then the harmony per section (tension -> release, a turnaround or a
   pickup into every new section; `theory` helpers, `jazz.JAZZ_PROGRESSIONS`, `s.prog('ii V I')`); then the hook.
3. Write the skeleton in `song.py`: `s.section(name, bars=...)` in order, tempo moves (`s.set_tempo`,
   `s.ritardando`, `s.fermata`, `s.rubato`) and meter changes, the band (`b = bands.make('<preset>', s)` or tracks
   the sound designer names), `ANALYSIS = b.analysis`.
4. Perform every part through its player - a looped grid or a bare line is not a part:
   - piano: `pianist.arrange(melody, prog, bpm=s.tempo, key=s.key, style=..., density=..., lh=..., memory=mem,
     at=sec.bar(n))` for every piano melody and solo; its `.lh` replaces a separate comping part; set pieces with the
     named moves (`pianist.trill`, `.roll`, `.gliss`, ...) booked in the memory (`mem.played(at, 'trill')`), the big
     figure saved for the climax (`mem.save(at)`); `.pedal(prog, at)` for the sustain pedal;
   - drums: `drummer.arrange(s, style=..., density=..., kit=b.drums, plan={...}, ending=...)` then `part.play(track)`
     (fills budgeted by `fill_every` / `flashy_every`);
   - bass: `bassist.arrange(prog, bpm=s.tempo, key=s.key, style=..., part=..., kick=beat, memory=mem, at=sec)` then
     `.place(track, sec)`;
   - guitars: `guitarist.arrange(...)` for rhythm (a second `.take(2)` for double tracking), `guitarist.lead(...)`
     for solos (bends, vibrato);
   - winds (sax, trumpet, trombone, flute, clarinet; bowed strings for bow pressure): `hornist.arrange(melody,
     s.tempo, family=..., style=..., section=..., peaks=<the hook's held peaks>, vel=(lo, hi), memory=mem, at=sec)`
     then `.place(track, sec)` - the air inside the held notes (pushes, pulses, swells, tapers), vibrato on the held
     peaks, the bell moving against the mic; never a held wind note at one level ("pustet mal kurz mehr, mal kurz
     weniger"); jazz horns: `jazz.horn_line(...)` with the brief's feel; everything else with `humanize` /
     `jazz.touch()` velocity arcs.
5. Build (`python -m agentsound build songs/<slug> --section NAME` while working, then the whole song). Read the
   "note dynamics" block and each player's `.summary()` / `.budget` / `.moves`; LOOK at `out/tracks.png` (who plays
   when) and `out/loudness.png` (the arc). Listen-by-numbers: does every section have a reason to exist?
6. Hand over: `ARRANGEMENT.md` updated to what was built, a log line in `BRIEF.md` (sections, hook placements,
   moves used, what the sound designer must know).

## Checklist (from recipes/HUMAN_FEEDBACK.md)

- A song, not a loop: "it sounds rather simplistic" - form, tension/release, variation between repeats, fills,
  counter-lines. The hook that worked on lamplight-avenue: one motif that opens the song, returns between sections,
  is harmonized a third below in the choruses and climbs higher in the last one.
- Real dynamics: "sind alle Lead-Noten gleich laut?" - velocity arcs over each phrase in 55-118, accents on phrase
  peaks and strong beats, softer passing / repeated notes, octave doubles softer; a section arc (first statement
  soft, the climax strongest). `flat_dynamics` must be 0.
- A piano lead is never a bare single-note line: "als würde ein Kind Taste für Taste drücken". Harmonize (83-95 %
  of melody notes voiced was the "WOW!!!" benchmark), decorate long notes, fill the gaps.
- Budget the flashy moves: "etwas zu viele von diesen schnellen Zwei-Tasten-Wechseln" - about one fast figure per
  16 bars, never in neighbouring phrases, only at structural moments; ornaments light and legato (a soft landing).
- Jazz: piano-led, **straight 8ths** ("New York Bar Jazz, aber ohne Swing") unless the user asks for swing - then
  light (ratio 0.55-0.58). Clear phrase shapes with rhythmic drive, not meandering bebop lines ("leiernd"); rolled
  chords, grace notes, a real ending ("bei Jazz ist auch die Technik wichtig, gerollte Akkorde usw."). Melody first,
  polish over virtuosity (Beegie Adair). Drum bombs and ride choruses soft (velocity 45-60).
- Realism: write idiomatic lines - ranges, breathing gaps for winds, bowing phrases for strings, strums and bends.
- Held wind notes breathe: "da spielt er eine Note und pustet mal kurz mehr, mal kurz weniger" - every sax / brass /
  woodwind lead goes through `hornist.arrange` (air moves inside the note, vibrato on the held peaks, mic moves).

## Must not

- Never choose the final sounds or effect chains, set mix levels to hide a composition problem, or touch the master.
- Never quantize a played part back to a grid or flatten its velocities to "clean it up".
- Never edit other songs; copy ideas from them, not files. Never copy a reference song's melody or audio.
- Never send notifications or messages to the user; hand over to the producer.
