# Sample realism plan: sampled instruments that sound played

Status (2026-10-15): lever 1, batch 0 (tooling) and batch A (levers 2 + 3, engine + `patches/realism.py`; no patch
opted in yet, the blind A/B is with the user) are built; the rest is a plan. The open items are in TODO.md, section
"Sampled-instrument realism". This plan replaces full physical modelling. The physical guitar on `cx-physguitar` was "simple and empty"
(HUMAN_FEEDBACK 2026-10-11). Real recordings keep the body, room and attack. Small models and synthesized parts
supply what the recordings lack: variation, continuity, noises, resonance, transitions and a sustain that is alive.

## 0. Why, and the ground rules

**The complaints** (recipes/HUMAN_FEEDBACK.md):

- 2026-09 realism: "möglichst realistische, nicht keyboard-artige Instrumente" ("as realistic as possible, not
  keyboard-like"). A sampled note must sound played, not triggered.
- 2026-10-11 cx-physguitar: "simple and empty". The modelled guitar lost fullness, so samples stay the source.
- 2026-10-15 blueprint-boulevard: the sampled alto's looped sustain is too static. A fast 10-16 Hz / 25 % tremolo
  "sounds more real". A real reed has aperiodic shimmer, jitter and breath turbulence.
- 2026-09-30 lamplight-avenue: a held sax note moves 3.7-7 dB (the player moves relative to the mic). The hornist
  breath moves are the answer to that, and they stay.

**The levers, in the order the user agreed:**

1. Per-voice random micro-modulation and a random LFO on `fx.tremolo`. This is the shared foundation and **another
   agent is building it now**. This plan does not design it.
2. Synthetic round robins.
3. Continuous dynamics.
4. Performance-noise layer.
5. Hybrid resonance.
6. Synthesized transitions.
7. Resynthesized sustain.
8. A learned timbre model (outlook only).

**Rules for every lever** (CLAUDE.md, memory "KISS: tools over functions" and "shared wrappers, not parallel
techniques"):

- **One owning tool.** Sound-level behaviour lives in the engine `sampler`, as params with a `ParamSpec` and a helpful
  `help`. Per-instrument values live in the patches. Playing decisions (when a squeak happens, which string, which
  transition) live in the players: guitarist / fretwork, hornist, pianist / romantic, ensemble. There is no second
  sampler, no song-level hack and no Python audio post-processing.
- **Defaults are bit-transparent.** Every new param defaults to 0 / off. Every existing render stays bit-identical
  until a patch opts in. A patch that opts in goes on the TODO "Not re-rendered after a library change" list with
  the songs that use it.
- **Per-family values come from one data table.** A new `agentsound/patches/realism.py` holds
  `FAMILY = {'plucked': {...}, 'nylon': {...}, 'piano': {...}, 'reed': {...}, 'brass': {...}, 'bowed': {...}}`. It
  holds sampler param values only, and patches spread it (`_sfz(path, level=..., **realism.FAMILY['nylon'])`). This
  is one table, not a defaults mechanism per lever.
- **Determinism.** Every random draw comes from `dsp::Rng` or the sampler's existing hash `random01(seed_, a, b, c)`.
  Draws are keyed by what the note is (its onset, key and zone salt), never by voice slot, block size or note count
  across tracks. Each lever gets its own derived stream (for example `mix64(seed ^ 'rr')`), so turning one lever on
  never shifts another lever's draws. That matters most for lever 1's stream.
- **Real time.** No allocation, I/O or exceptions in `process()`. Analysis data (lever 7) and resonator buffers
  (lever 5) are built in `prepare()` or at load and cached per sample, like `smp::levelTrack`. Only the master chain
  may add latency, so no lever may add lookahead.
- **Judging.**
  - First, same-song A/B on one stem, loudness-matched and short (10-20 s solo, then 20-30 s in context).
  - Second, the analysis metrics (section 1).
  - Third, the ears venv as a same-song second opinion. It catches "got more mechanical" and nothing finer
    (README section 6). It runs on the user's machine, which has the GPU.
  - **The user's ear is the final judge.** HUMAN_FEEDBACK warns that the user "cannot grade effect quality from an
    A/B alone", so every A/B also goes out in song context.

### What lever 1 provides, and the boundary with it

Lever 1 (in progress, not designed here):

- **What it is.** Inside the sampler voice, a band-limited random amplitude and pitch micro-modulation, running
  continuously while the note sounds. Plus a random LFO on `fx.tremolo`'s rate and depth.
- **What it owns.** Everything that moves *during* a note: shimmer, jitter, slow drift. Its per-voice noise source,
  seeded at note-on, is the shared primitive.
- **What it owns: the SFZ noise LFO.** `sfz.py` still plays the SFZ noise LFO (`lfoN_wave=-1`) as a sine (the
  `approx` counter at sfz.py ~1376). Weresax uses exactly that LFO for its own humanize controls (cc117 rate,
  cc118 uneven pitch, cc119 unsteady vibrato, cc122 wind-noise level; `Programs/Sax.sfz`). Lever 1 should map that
  LFO to its noise source, which gives the pack's own humanize for free.
- **What it does NOT own (this plan does).**
  - Static per-note offsets drawn once at note-on (lever 2).
  - Layer blending (lever 3).
  - Extra events: noises (lever 4).
  - Coupled resonators (lever 5).
  - Transitions between notes (lever 6).
  - Replacing the loop (lever 7).
- **What we reuse.** Lever 2 reuses lever 1's per-voice seeding helper. Lever 7 drives its partials' modulation from
  lever 1's noise process, so there is no second random modulator in the voice.

## 1. Shared evaluation tooling (batch 0, small)

Every lever needs the same three things. Build them once, before or alongside lever 2.

**A. Instrument A/B without editing a song.**

- Extend `python -m agentsound audition <patch>` (cli.py `audition_song`) with `--set param=value` (repeatable)
  and `--ab param=value`. `--ab` renders A (as is) and B (with the override) and writes them loudness-matched as
  `a.wav` / `b.wav` plus a randomly labelled blind pair.
- Add probe materials to `AUDITION`:
  - `repeat`: the same note 8x at one velocity, then a repeated chord.
  - `sweep`: one key, velocity 20 -> 127 in steps of 4.
  - `legato`: an interval ladder in steps of 1, 2, 5, 7 and 12.
  - `sustain`: 4 s held notes at pp / mf / ff.
  - `pedal`: a pedalled chord change, then pedal up.

**B. Song A/B.** Add `build --set TRACK.instrument.PARAM=V` (repeatable; unknown targets are errors, strict). It
writes to `out/ab/<label>/`. With `--section` and `--stems` it gives the per-stem pair the user hears. No song code
changes, so the same song renders A and B.

**C. Realism probes in the report.** Extend `engine/analysis/NoteDynamics` (per melodic track, next to
`flat_dynamics`). Each probe runs on its own probe material and on song stems. If lever 1 adds a sustain metric,
`sustain_flux` reuses it instead.

| field | measures | lever |
|---|---|---|
| `repeat_sim` | Median spectral-envelope correlation of the first 80 ms of consecutive same-key, same-velocity (±6) notes. 1.0 = machine gun. | 2 |
| `layer_step` | On the `sweep` probe: the largest jump in level (dB) and brightness (share above 2.5 kHz, dB) between neighbouring velocities, vs the median step. | 3 |
| `sustain_flux` | On held notes > 0.8 s, after the attack (`LevelTrack::attackEnd`): the standard deviation of the 10 ms RMS (dB) and of the spectral centroid (cents) after a 300 ms detrend, plus the autocorrelation peak at the loop period (a loop's periodicity). | 1, 7 |
| `tail_decay` | For notes released or pedalled: the decay slope in the first 0.5 s vs the next 2 s (two-stage decay; TODO "Piano realism": 15.3 vs 11.6 dB within a bar). | 5 |
| `transition_dip` | At legato transitions: the deepest level dip and the time to the new pitch (the `_demo_realism` numbers already measure this by hand). | 6 |

Effort: about 1 day. Tests:

- `test_cli`: the `--set` / `--ab` parsing, and unknown targets fail.
- `test_analysis.cpp`: synthetic signals.
  - A repeated identical WAV gives `repeat_sim` ≈ 1, and jittered copies give less.
  - A looped sine gives a `sustain_flux` periodicity peak, and an AM-noise sine gives none.

## 2. Lever 2: synthetic round robins

**Problem.** Packs with one sample per note and one take play every repeated note identically. That is the
"keyboard" sound on repeated notes, arpeggios and strums. The worst packs are FreePats Spanish classical (the
`sampled/nylon_guitar` patch; INDEX `vel1 rr1`), FreePats tenor sax (`vel2 rr1`), the upright KW, jRhodes, Splendid
and Headroom (`rr1`), and Weresax (2 RR).

**Exists today:**

- SFZ round robins (`seqLength` / `seqPosition`, `lorand` / `hirand`).
- Per-zone `ampRandom`, `pitchRandom`, `offsetRandom` and `delayRandom`. These are imported from SFZ only, and a
  patch cannot set them instrument-wide.
- The hash `random01(seed_, now, key, ...)` and the per-zone `salt` (Sampler.cpp ~1389, ~1620).
- Timing humanize in Python (`humanize.jitter`, the players' hand feel).

**Design.** These are instrument-level sampler params, applied at note-on on top of whatever the zone does. They are
drawn once per note (zone salt, onset, key) from the `rr` stream.

| param | range | default | help (short) |
|---|---|---|---|
| `rrpitch` | 0-20 ct | 0 | Per-note random tuning offset (± ct, triangular): a string or reed never lands on exactly the same pitch. |
| `rrtone` | 0-6 dB | 0 | Per-note random brightness (± dB on the voice's tilt / lowpass): pick or finger angle, bow contact. |
| `rrattack` | 0-1 | 0 | Per-note random attack variation: scales the start offset into the attack (0-6 ms of the transient skipped or a 0-4 ms softer ramp), so the transients differ. |
| `rrstart` | 0-50 ms | 0 | Per-note random start offset *after* the attack (looped or sustained packs: a different phase of the vibration and the noise). |
| `rrlevel` | 0-3 dB | 0 | Per-note random level (± dB) under the velocity. |
| `rrborrow` | 0-1 | 0 | Chance that a note plays the neighbouring sample (±1 semitone, re-pitched) instead of its own, when the note is a repeat of the previous note on that key within 1 s. The classic synthetic round robin for one-sample-per-note packs. |

**Not in the engine:**

- Timing variation stays in the players and humanize (one owner of time).
- `rrrepeat` scales: the variation is larger for a fast repeat of the same key (the counter that SFZ
  `nextInSequence` already keeps per zone), because machine-gun repeats are where it is heard. Implement it as a
  fixed internal rule (×1.5 under 250 ms), not a param, unless the A/B says otherwise.

**Where.**

- `Sampler.cpp` note-on (zone pick and voice start): about 120 lines, on the same code path as `ampRandom` /
  `pitchRandom`.
- `rrtone` reuses the voice `Lowpass` / tilt. No new filter.
- `rrborrow` reuses zone selection with `key ± 1` and the voice's pitch ratio. Exclude zones whose `pitchKeytrack`
  is 0 (drums).
- Python: `inst.sfz(...)` passes the params, and `realism.FAMILY` holds the values.

**Per-family defaults** (a starting point for the A/B, not final):

| family | `rrpitch` | `rrtone` | `rrattack` | `rrstart` | `rrlevel` | `rrborrow` |
|---|---|---|---|---|---|---|
| nylon / plucked, 1 RR (`sampled/nylon_guitar`) | 4 | 1.5 | 0.4 | 0 | 0.8 | 0.5 |
| plucked with RR packs (Fiedler concert guitar 7 RR, Shinyguitar 5 random) | 2 | 1 | 0.2 | — | 0.5 | 0 |
| piano, 1 RR | 1.5 | 1 | 0.25 | — | 0.5 | 0.3 (sweep-gated: a borrowed note must not stick out) |
| reed / brass (Weresax, MTG has rr9) | 3 | 1 | 0.3 | 30 | — | 0 (the timbre changes too much across the break) |
| Rhodes / e-piano | 2 | 0.5 | 0.2 | — | — | 0.3 |
| drums | not this lever: real RR and re-strike damping exist | | | | | |

**Determinism and real time.** The draws use `random01` keyed on (onset sample, key, zone salt, a lever constant),
with no `Rng` state shared between notes. Nothing new is allocated, because `rrborrow` reads already-loaded zones.

**Risk: section renders.** `now` is the render-time sample. If `build --section` starts at sample 0, a section
render draws differently from the full render. Check what `lorand` does today. If needed, key the draws on the
note's song-time onset, which the compiler can pass via the NoteExpression of lever 5.

**Evaluation.**

- Probes `repeat` and `sweep` on `sampled/nylon_guitar`, `sampled/upright_piano` and `sampled/alto_sax`.
- `repeat_sim` should drop, toward what the 7-RR Fiedler pack measures (the target is "like a real RR pack", not 0).
  `flat_dynamics` stays unchanged. `rrborrow`'s timbre step on `sweep` stays under 1.5 dB brightness.
- **Reference song.** The nylon fingerstyle song in progress: arpeggios, repeated bass notes and a tremolo-picking
  passage, if it has one. Until it lands, use the fingerstyle section of `songs/_demo_acoustic` on
  `sampled/nylon_guitar`. Second reference: a comping passage with repeated chords (`songs/pro-piano-bossa`).

**Tests** (`tests/test_sampler.cpp`, a `*sine` generator zone so pitch is measurable):

- Default 0 gives a bit-identical hash of an existing test render.
- `rrpitch=10`: every note is within ±10 ct, and at least two of eight repeats differ.
- Same seed is identical, and a different seed differs.
- `rrborrow`: the borrowed note lands on the right pitch (±1 ct).
- `rrstart` never starts inside the attack (`attackEnd`).

**Risks.**

- Too much `rrpitch` reads as out of tune in chords. Cap it per family and test in context.
- `rrborrow` across a register break (sax, piano bass strings) is audible. Restrict it to zones of the same
  velocity layer and a similar `levelTrack` brightness.

**Effort:** S-M (1-2 agent days with the tests).

## 3. Lever 3: continuous dynamics

**Problem.** In `layers='velocity'` (the default) a velocity picks one layer. On packs with 2-5 layers (Splendid 5,
Weresax 2, FreePats sax 2, upright KW 2, Fiedler 4), a crescendo of struck notes jumps in timbre at the layer
boundaries, and inside a layer only the level moves. That is a keyboard tell. Salamander, with 16 layers, is fine.

**Exists today:**

- `layers='dynamics'` + `xfspread` + `dynamics`: a phase-aligned stack of layers, crossfaded live by one
  instrument-wide control. It suits sustained mono instruments, but its layer position is not per note.
- `dyntone` (the tilt follows `dynamics`) and `dynrange`.
- Zone `filVeltrack` and `velcurve`, and `sfz.even_velcurve` / `apply_velcurve` / `hammers()` in Python.
- `levelTrack` for level matching.

**Design.** A third layer mode plus a velocity tone control. These reuse the dynamics-stack machinery: a note starts
its layers together and phase-aligned, and `silent` layers cost nothing.

| param | range | default | help (short) |
|---|---|---|---|
| `layers` | + `'blend'` | `'velocity'` | blend: each note starts the two velocity layers its velocity lies between and mixes them at a fixed per-note ratio (equal power, by where the velocity sits between the layers' centres). The layer steps of a 2-5 layer pack disappear; a struck instrument (piano, guitar, mallets) gets the per-note version of what `dynamics` does live for winds. |
| `blendwidth` | 0-1 | 0.5 | `layers='blend'`: how much of each layer's velocity range crossfades (0 = hard switch as recorded, 1 = always a mix of two). A narrow width keeps most notes on one pure recording and only smooths the boundaries (less phasing). |
| `veltone` | 0-1 | 0 | Velocity-dependent brightness inside a layer: the voice tilt / lowpass follows where the velocity sits in its layer (darker at the bottom, as recorded at the top), so a layer no longer has one fixed colour for 30 velocity steps. Same curve as `dyntone`, per note. |

**Where.**

- The `Sampler.cpp` zone loop at note-on (the `layersDyn_` branch is the template) and the voice gain set-up.
- `veltone` reuses `smp::Tilt` / the voice lowpass, the same as `rrtone`. Implement `rrtone` and `veltone` as one
  tone offset per voice.
- Patches: piano / guitar / mallet patches with 2-5 layers get `layers='blend', blendwidth=0.4, veltone=0.5`.
  Salamander keeps `'velocity'` with `veltone` only.
- The hornist's live `dynamics` path is unchanged. Winds stay on `layers='dynamics'`.

**Phase risk.** Two different takes of the same note are not phase-coherent. Blending them comb-filters the sustain,
which matters most on piano. Mitigations, in order:

1. A narrow `blendwidth`.
2. Align the second layer's start to the first by onset (`levelTrack` attack detection; a sample-accurate offset
   computed once per zone pair at load, cached).
3. Let the blend converge to the dominant layer over 150-300 ms after the attack (a "timbre in the attack, one
   recording in the tail" crossfade).

Option 3 is a fixed internal envelope. Test it before adding a param.

**Determinism and real time.** No randomness. Twice the voices per note, so check the polyphony defaults: the piano
patches have 128-160, and blend needs up to 2x.

**Evaluation.**

- The `sweep` probe: `layer_step` on Splendid (`sampled/concert_grand`) and on the upright KW. Target: no step over
  2x the median.
- A tail comb check: the spectral flatness of a held blended note vs the pure layers (the comb shows as notches).
- **Reference songs.** `songs/nocturne-etude` (a melody of crescendo phrases; TODO "Piano realism": soft notes lack a
  bright attack, 1.18x vs 1.37x, which `veltone` speaks to directly). `songs/gymnopedie-etude` for the soft end.
  Guitar: the nylon song's dynamic arcs on `sampled/concert_guitar` (4 layers).

**Tests:**

- `blend` at a layer centre equals the single layer (within -90 dB).
- Between two layers, the level is monotone in velocity.
- `blendwidth=0` is bit-identical to `'velocity'`.
- `veltone=0` is bit-transparent.
- Polyphony steal order is unchanged for single-layer notes.

**Risks.** Phasing (above). CPU on dense piano with the pedal (2x voices). A pack whose layers differ in loudness
more than in timbre (Shinyguitar's layers are normalised) needs its velcurve first. `blend` does not replace
`even_velcurve`.

**Effort:** M (2-3 days, mostly the phase-alignment check and the A/B).

## 4. Lever 4: performance-noise layer

**Problem.** Real recordings carry the player: finger squeaks on wound strings when the hand shifts, the finger
leaving a string, breath before a phrase, sax key clicks, the piano's damper and pedal thumps. Clean multisamples
lack them.

**Exists today.** The model is the acoustic guitar:

- `sampled_guitars.NOISES['sampled/acoustic_guitar']` is a role -> key / articulation map: fret, muted, strings,
  chuck, brush, thump, knock.
- `guitarist._finger_noises()` places finger-off noises at chord changes and position shifts, budgeted by
  `budget.Budget` and logged as 'noise' moves.
- The sampler's `*noise` generator zones, with zone filter and filter envelope (`fenv`), plus release triggers.

Packs that ship noises:

| pack | noises |
|---|---|
| Fiedler concert guitar | `mf-nylon-guitar-fretnoise1..9` + 13 release zones |
| Salamander | `pedalD1/2`, `pedalU1/2`, `rel1..` (release zones in use) and `harmLA*` |
| Weresax | `alto_map_wind_noise.sfz`: a breath-noise layer under every note, its level on cc122 |
| Bear sax | `breath_osc_*`, `noise_breath` |
| War tuba | `breath_rr*` |

TODO "Kits / samples": "no real string-squeak recording" and "a sampled string-noise pack (pick scrape / squeak are
synthetic)".

**Design.** One shared primitive: a noise map per patch, plus the existing extra-note path, plus `Budget`. Then a
vocabulary per player.

1. **Move the noise map.** `sampled_guitars.NOISES` becomes `patches.NOISES` (the guitar entry is unchanged). Roles
   are added per family, and each value is a key, an articulation or a list of keys:

   | family | roles |
   |---|---|
   | guitar | `fret`, `shift` (the squeak), `release`, `chuck`, `knock`, `slide` |
   | reed / brass | `breath_in`, `key_click`, `wind` (the continuous layer, its level as a CC or param) |
   | piano | `pedal_down`, `pedal_up`, `damper`, `key_off` |
   | bowed | `bow_start`, `bow_change`, `string_release` |

   `guitarist._noises()` becomes `patches.noises_of(sound, given)`, and every player calls it.

2. **Supply the noises.** A patch supplies them in one of three ways:
   - Recorded zones of the pack. Fiedler fretnoise and Salamander pedals become zones on keys outside the playing
     range, as Shinyguitar's keys 12-27 are now.
   - The pack's own continuous layer. Weresax `wind` is already in `Sax.sfz` through cc122, so the hero sets
     `cc={122: n}`. That is a patch value, not code.
   - **Synthesized noise presets**: `*noise` zones with a filter, a filter envelope and an amp envelope. They are
     defined once as data in `patches/realism.py` as `NOISE_ZONES`:

     | preset | recipe |
     |---|---|
     | `squeak` | Band-passed noise 1.5-4 kHz, `fenv` sweeping up an octave in 80-150 ms, 120 ms envelope (wound strings only) |
     | `breath_in` | Band-pass 600 Hz-3 kHz, 150-300 ms swell |
     | `key_click` | 4 ms high-passed burst plus a 1.2 kHz resonance |
     | `pedal_thump` | Lowpass 300 Hz, 40 ms |
     | `scrape` | From physguitar's contact / scrape synthesis (section 5's salvage list), rendered as a zone recipe, not ported code |

     These presets are the fallback, used only where the pack has no recording.

3. **Players place them.** Every placement goes through `Budget` and is logged as a 'noise' move.
   - **guitarist / fretwork**: already places fret and shift noises. Add squeaks only on position shifts of wound
     strings (strings 0-2, shift ≥ 3 frets, `legato` / slide contexts), and slide noise on `fretwork` slides. Extend
     it to `sampled/concert_guitar` and `sampled/nylon_guitar` via the map.
   - **hornist**: a `breath_in` at the breath gaps `arrange()` already makes (`breath_ms`), its level following the
     coming phrase's energy. A `key_click` on fast runs only. The jazz styles keep it rare (budget).
   - **pianist / romantic**: `pedal_down` / `pedal_up` thumps at the points `pianist.pedal()` /
     `Pianist.pedal_points()` already compute. Damper noise is in the Salamander release zones today. Only a level
     check is needed.
   - **ensemble** (strings): `bow_change` at the direction changes it already plans. This is low priority: no pack
     has it recorded.

**Engine changes.** None are expected. If the synthesized squeak needs a pitch-tracking band-pass, the zone `fenv`
plus `filKeytrack` already do that.

**Params.** None new in the engine. In Python: the players' existing `noises=` argument (False = off), a
`noise_level` dB trim in the hand feel / hornist style, and `NOISE_ZONES` levels calibrated against the note level.
The guitar fret noise sits about 24 dB under strums (`ACOUSTIC_FRET_GAIN`). Use the same calibration method.

**Determinism.** The players' seeded `random.Random(f"{seed}:noise")` streams already exist and are separate from
the note stream, so a `take` changes only the noise.

**Evaluation.**

- Count and level per noise kind in the player's log.
- `silent_notes` must stay 0: noise notes must reach a zone. The compile check knows extra notes.
- In `zoom` on a stem, squeaks should sit 15-30 dB under the note peak and never land on a strong beat unless a
  shift happens there.
- **Reference songs.** The nylon fingerstyle song (squeaks and finger-off on `sampled/concert_guitar`);
  `songs/blueprint-boulevard` (alto breath before phrases, cc122 wind); `songs/gymnopedie-etude` (pedal thumps on
  `sampled/recital_grand`).

**Tests:**

- `test_guitarist`: a squeak appears only on wound-string shifts of 3 frets or more.
- `test_hornist`: one breath at most per breath gap, inside the gap and before the phrase.
- `test_pianist`: thumps align with the pedal points.
- `test_patches`: every `NOISES` role resolves to a zone of the patch, which catches pack updates.

**Risks.**

- Noise as habit. The rule "ornaments are spice, not habit" applies: budgets, and fewer noises in dense mixes.
- Synthesized squeaks can sound like a synth. If the A/B is not clearly better, keep only recorded noises and leave
  the synthesized one off.
- Pedal thumps get masked or annoy the listener. Default them low.

**Effort:** M (2-3 days: mostly Python, data and calibration).

## 5. Lever 5: hybrid resonance

**Problem.**

- Dry or close-miked samples lack what the instrument does *between* notes: open strings ringing in sympathy, the
  body's coupling, and the piano's two-stage decay with the pedal.
- The TODO "Piano realism" measured a decay of 15.3 dB inside a bar vs 11.6 in the reference: no damper or
  soundboard model.
- Guitar: a fingerstyle nylon chord on one-sample-per-note FreePats sounds like separate notes, not one box.

**Exists today.**

- **The sampler's `StringBank`** (Sampler.cpp ~900; `sympathetic`): 88 feedback-comb piano strings excited by the
  instrument's output, with dampers from the pedal and held keys and a half-pedal. Buffers are sized in
  `prepare()`, quiet strings are skipped, and the struck keys are excluded. It is the right primitive. Generalize it,
  do not duplicate it.
- **`cx-physguitar`** (unmerged; `git show cx-physguitar:<path>`). What is worth salvaging:
  - `engine/core/NoteExpression.h` plus the `Module.h` overload
    `noteOn(id, pitch, vel, const NoteExpression&)` / `noteParamSpecs()` / `parseExpression()` and its
    `SongSpec.cpp` parsing. This is generic per-note data: fixed size (16 slots), validated at parse time, with no
    allocation on dispatch. It lets a player tell the sampler which **string** a note is on, which lever 5 (open vs
    fretted strings), lever 6 (string legato) and lever 2 (song-time onset key) all need. **Salvage it first, as is
    plus tests.**
  - `engine/instruments/GuitarBody.h`: 48 body modes (Hz, bandwidth, gain), derived from CC0 Shinyguitar attacks by
    `tools/voice_physguitar.py`. This is the body bank for lever 5, and the tool is the method for violin / cello
    bodies.
  - The string `Loop` in PhysGuitar.cpp: a waveguide with a cubic Lagrange fractional delay, a stiffness all-pass
    and a one-pole loss fitted at the fundamental and the 4th partial (tuned including the phase). It is more exact
    than the StringBank comb (linear interpolation, fixed loop lowpass). Use it only if a guitar's six sympathetic
    strings audibly mistune or ring wrong with the comb. Otherwise keep the comb.
  - The contact / scrape / knock noise synthesis. It is a recipe source for lever 4's synthesized noises, not engine
    code to port.
  - **Not salvaged:** the plucked-string model itself, the two polarisations, the stereo mic and room model (the
    samples have a real mic and room), and the calibration JSON.

**Design.** A `Resonance` component: `StringBank` moved out of Sampler.cpp into `engine/instruments/Resonance.h/.cpp`
and generalized. It is used by the sampler now and by sf2 or a physical instrument later.

- **String sets**: `piano` (the current 88, bit-identical), `guitar` / `nylon` (6 open strings in a tuning, coupled
  through the bridge), `violin` / `viola` / `cello` (4), `harp` (later).
- **An optional body bank**: N biquad modes (GuitarBody.h for guitar and nylon; violin and cello sets measured the
  same way from CC0 VSCO / Bigcat attacks by the voice tool) between the excitation and the strings. It optionally
  goes to the output as a small "bloom".

**Sampler params:**

| param | range | default | help (short) |
|---|---|---|---|
| `sympathetic` | as now | 0 | Unchanged: the amount of sympathetic string resonance. |
| `strings` | piano / guitar / nylon / violin / viola / cello | piano | The resonating string set (tuning, decay times and coupling per set). piano = today's 88-string bank, bit-identical. |
| `tuning` | `[6 or 4 MIDI pitches]` (patch level) | standard | The open strings the set rings at (drop D, DADGAD, open G). |
| `body` | 0-1 | 0 | Body resonance: the instrument's modal body (strings' set) added to the output and feeding the strings. 0 = off, no cost. For dry / DI-like or one-take packs whose recording lacks the box; mic'd packs keep it low (the body is in the recording: no double colouring). |

**Damping.** Piano: the dampers follow the pedal and held keys, as now. Guitar: open strings are free by default, but:

- A string that is currently **fretted** (a NoteExpression `string` slot of a sounding note at a fret > 0) is
  damped as an open resonator.
- `muted` / palm / chuck articulations damp all strings for their duration (the articulation is known at note-on).
- The guitarist's `Shape` knows its frets, so it sends `string` per note. Without NoteExpression, all six strings
  stay free, which is the fallback.

**Where.**

- Engine: Resonance.h/.cpp (about 300 lines, mostly moved), Sampler params, a NoteExpression opt-in in the sampler
  (`noteParamSpecs`: `string` and later `transition`).
- Python: `guitarist` emits `string` per note (it has it: `Shape.frets`); patches set
  `strings='nylon', sympathetic=0.3, body=...`.
- Tool: `tools/voice_physguitar.py` from the branch becomes `tools/voice_body.py`, which measures the body modes of
  any pack.

**Per-instrument defaults:**

| patch | settings |
|---|---|
| `sampled/nylon_guitar` (FreePats, dry-ish) | `strings='nylon', sympathetic=0.35, body=0.3` |
| `sampled/concert_guitar` (Fiedler, mic'd) | `sympathetic=0.25, body=0` |
| `sampled/acoustic_guitar` (Shiny) | `strings='guitar', sympathetic=0.25, body=0` |
| `sampled/recital_grand` | stays 0.9 |
| `sampled/grand_piano` / `piano_lead` | `sympathetic` 0.5 after an A/B (the TODO piano decay gap) |
| `sampled/solo_violin` / `solo_cello` | `strings='violin'` / `'cello'`, `sympathetic=0.2`: open-string sympathy is what makes a D major scale on a violin ring |

**Real time.** Fixed buffers sized in `prepare()` for the largest set. A guitar costs 6 strings plus 48 biquads per
instrument, not per voice. The quiet-skip is kept. There is no feedback gain above 1: the comb gains are below 1,
and the body is passive (mode gains as derived), with a limiter-free `tanh` only on a bridge return if the waveguide
loop is ever used. Outputs are always finite: the existing test pattern.

**Evaluation.**

- `tail_decay` on the `pedal` probe and on song stems. The piano target is the TODO numbers (11.6 dB inside a bar on
  the Gymnopedie reference).
- Guitar: the ring-on of an open E after a fretted E chord (spectral line at 82 / 165 Hz in `zoom`), and the
  "togetherness" of a chord: the ears' PQ on the same song A/B.
- **The fullness check from the physguitar feedback:** judged by ear against the sampled guitar alone, never by the
  decay numbers alone.
- **Reference songs.** The nylon fingerstyle song (FreePats and Fiedler variants); `songs/gymnopedie-etude` and
  `songs/nocturne-etude` (piano pedal).

**Tests** (`test_sampler.cpp`):

- `strings='piano'` is bit-identical to today.
- An open-string resonance appears for a note at an open-string pitch and its 5th / octave, and not for a fretted
  string's tritone.
- A muted articulation damps within 60 ms.
- A fretted-string NoteExpression damps that open string.
- `body=0` costs nothing (no state change).
- Determinism.
- `test_guitarist`: `string` is emitted per note and matches the Shape.

**Risks.**

- Double colouring on mic'd packs (body default 0).
- Boom: the bass strings couple less, as in the piano bank today.
- Mud in dense mixes: tie `sympathetic` to the arrangement density in the patch notes, not in code.
- NoteExpression touches the render format. Update RENDER_FORMAT.md and PARAMS.md and keep instruments strict:
  unknown note params are errors.

**Effort:** M-L (3-5 days: NoteExpression salvage about 1, Resonance refactor plus sets about 2, body tool and
A/B about 1-2).

## 6. Lever 6: synthesized transitions

**Problem.** Without recorded legato (no free pack ships "true legato" per TODO "Orchestral gaps"), notes of a line
are separate attacks or a plain crossfade. Guitar slides and hammer-ons on a polyphonic sampler are a pitch bend of
the whole instrument (`bendfollow` latches per note, but one bend is shared).

**Exists today**, and most of the lever is here already:

- `mono='legato'`: the new note enters past its attack (`legatooffset` = auto from `levelTrack::attackEnd`), with an
  equal-power crossfade (`legatotime`) and a level match (`legatomatch`).
- Portamento (`glide`, `glideshape` linear / ease / fast), where the old voice bends to the new pitch while the new
  one bends in from the old. That *is* "pitch-shifting the previous note's tail plus a crossfade".
- The hornist's scoops / falls through `pitchbend`, `fretwork` bends via `pitchbend` + `bendfollow`, and `_demo_realism`
  with measured transition numbers.

**What is missing (the design):**

1. **String legato on polyphonic instruments.** `mono` gains a fourth choice, `'string'`. Voices are grouped by the
   NoteExpression `string` slot (lever 5's salvage). A new note on a string that still sounds is a legato transition
   on that string only: hammer-on, pull-off or slide. That means the same crossfade, glide and level-match code,
   with no re-attack. The other strings ring on. The fretwork / guitarist slide, hammer and pull moves send
   `transition` per note: `slide` (glide time from the move), `hammer` (no glide, `legatooffset` short, a small
   level step up) or `pull` (a step down plus a tiny pluck from the pack's attack: `legatooffset` 0 at -12 dB).
   Today these moves are approximated with the whole-instrument `pitchbend`.
2. **A transition shape per family.** These are params latched per transition, like `glide`:

   | param | range | default | help (short) |
   |---|---|---|---|
   | `legatodip` | 0-12 dB | 0 | Level dip at the crossover (a tongued or bow-change legato: the sound thins for 20-60 ms). |
   | `legatonoise` | 0-1 | 0 | Plays the patch's transition noise (lever 4 roles `slide` / `bow_change` / `key_click`) at the crossover, scaled by the interval. |
   | `glidemax` | 1-24 st | 24 | Largest interval the old voice bends through. Beyond it the old note fades early and the new one bends in only the last `glidemax` semitones, so a resampled tail never moves far enough to shift its formants audibly (the "chipmunk" risk of re-pitching samples). |

3. **Per-note transition data.** Each of `glide`, `legatotime` and `legatodip` can come per note from NoteExpression
   (`transition`, `glide_ms`) instead of a stepped automation. The compiler today steps `glide` "just before" a note,
   which works for mono; for `'string'` mode the stepped param would also hit the other strings.

**Where.**

- Sampler legato code: the `lgDir` / `glide*` voice fields are reused. `'string'` mode is about 150 lines: the
  per-string held-note lists generalize `Held`.
- Python:
  - `articulation.legato` and `.glide` emit NoteExpression when the track's instrument opts in.
  - `fretwork` slides, hammers and pulls use it.
  - The hornist gets `legatodip` per style (jazz tongued legato vs pop slurs).
  - `ensemble` gets `legatodip` for bow changes (it already plans bowing).

**Per-family defaults:**

| family | settings |
|---|---|
| reed | `legatodip` 1.5 dB, `glidemax` 7 |
| brass | dip 2.5 dB (lip slur), `legatonoise` 0 |
| bowed solo | dip 3 dB on bow changes only (ensemble decides), `glidemax` 5 |
| guitar | `mono='string'` on the nylon / acoustic / lead patches, slide noise via `legatonoise` 0.6 |

**Determinism.** No randomness beyond the existing draws. Latched per transition.

**Evaluation.**

- `transition_dip` and the "previous pitch 150-300 ms into the next note" measure from `_demo_realism`.
- The `legato` probe.
- **Reference songs.** `songs/blueprint-boulevard` (alto head and solo legato phrases); `songs/_demo_realism`
  (violin and sax pairs, the numbers in its docstring are the baseline); the nylon song's slides and hammer-ons.

**Tests:**

- `mono='string'`: a note on string 3 does not stop string 1, and a second note on string 3 makes a transition (no
  attack transient: peak within 1 dB of the crossfade level).
- `glidemax`: no voice bends more than its value.
- `legatodip=0` is bit-transparent.
- `test_fretwork`: the slide and hammer moves emit the right expression.

**Risks.**

- `'string'` mode and pedal / sustain interplay on guitar is a new state machine. Keep it separate from piano
  pedalling.
- Formant shift on long glides (`glidemax`).
- Library legato zones (`trigger='legato'`) must keep precedence.

**Effort:** M (2-4 days; `'string'` mode is most of it).

## 7. Lever 7: a sustain that is alive instead of a loop

**Problem.** A sustain loop repeats the same 50-500 ms forever. That is the "static sax" of 2026-10-15. Lever 1
modulates the result, but the periodic spectrum underneath stays. Packs: Weresax (looped), MTG (short takes, some
looped), the VPO / VSCO strings, choirs (with loop-seam clicks in TODO "Loop seams"), organs (fine: a real organ is
static).

This lever comes in two steps. 7a is cheap and sample-based. 7b is real resynthesis and happens only if 7a plus
lever 1 are not enough.

### 7a. Wandering sustain (multi-point loop): first

**Design.**

- **At load:** a `SustainMap` per region, computed once and cached like `levelTrack`. It holds candidate positions in
  the sustained part (after `attackEnd`, before the release or tail) that are pitch-synchronous (the fundamental
  period from the autocorrelation) and spectrally close (MFCC or band-energy distance under a threshold).
- **While a note is held:** instead of looping one region, the voice jumps between candidates. A second `smp::Reader`
  starts at the next candidate and the two crossfade equal-power over a drawn 80-250 ms. The next jump is after a
  drawn 0.3-1.2 s, so the sustain never repeats exactly.
- **When it applies:** long unlooped recordings (MTG, many orchestra samples) and looped ones whose recorded sustain
  before the loop is long enough. With fewer than 3 candidates the voice falls back to the normal loop, so a short
  sample is never worse.

| param | range | default | help (short) |
|---|---|---|---|
| `wander` | 0-1 | 0 | Alive sustain: while a note is held past its attack, playback wanders between pitch-synchronous points of the recorded sustain with slow crossfades instead of repeating one loop (0 = the loop as recorded). The amount sets how far back it may jump and how often. |
| `wanderxf` | 30-400 ms | 150 | Crossfade time of a wander jump. |

**Where.**

- `SamplerCore` gets the `SustainMap` (beside `LevelTrack`, cached per Segment A; computing it allocates, so it runs
  at load).
- The `Sampler` voice gets a second Reader (a `Reader` is plain data, so there is no allocation) and the wander
  state.
- Draws use the voice's `wander` stream (a separate derived seed).

**Defaults:**

| family | `wander` |
|---|---|
| reed / brass | 0.6 |
| bowed solo | 0.5 |
| sections | 0.4 |
| choir | 0.5 (also hides loop-seam clicks) |
| piano / plucked | 0 (they decay: nothing to sustain) |

**Evaluation.** `sustain_flux`:

- The periodicity peak at the loop period disappears.
- The RMS and centroid variation rise toward a real sustained reed. The reference value comes from an unlooped MTG
  take or a reference recording measured by `compare`.
- No clicks: the `clicks` report stays 0.
- **Reference song.** `songs/blueprint-boulevard`, the alto's long notes in the head and the outro. That is exactly
  the complaint. A/B it with lever 1 on in both A and B, so the A/B isolates lever 7.

**Tests:**

- `wander=0` is bit-identical.
- A synthetic sample (a sine with slow AM, 3 s) gives at least 3 candidates, and the jumps keep the phase (no
  discontinuity above -60 dB at crossfades).
- A short sample falls back to the loop.
- Determinism.
- Two readers never allocate.

**Risks.**

- A pitch drift inside the recording makes a jump audible as a pitch step. Exclude candidates over 3 ct off the
  median.
- Vibrato in the sample: candidates must match the vibrato phase too. Restrict to `novib` sets or a shorter
  `wanderxf`.
- CPU: two readers during crossfades only.

**Effort:** M (3 days).

### 7b. Sinusoidal + noise resynthesis: only if 7a is not enough

**Design.**

- **Offline analysis tool:** `python -m agentsound resynth <patch|pack>`, numpy only (installed, 2.5.x). It does a
  harmonic partial track of each sample's sustained part (f0 from the autocorrelation, 32-64 partials: frequency,
  amplitude and phase per 10 ms frame) and a residual noise envelope in 16 bands.
- **Output:** written to a gitignored cache next to the pack's INDEX (`<pack>/RESYNTH/<sample>.bin`), never into git.
- **In the engine:** at load (`prepare()`), the sampler reads the analysis if the patch asks for it. Past
  `attackEnd` a voice crossfades from the sample to an additive bank: recursive oscillators, no tables, about 40
  partials. The partials' amplitude and frequency get independent band-limited random modulation, driven by lever
  1's noise process, with per-family spectra:
  - shimmer 1-3 % on the upper partials,
  - jitter 2-5 ct,
  - breath noise that follows the level (the residual bands through the voice's `*noise` path).
- The sustain is regenerated for as long as the note is held: no loop, and the note's own spectrum evolves.

**Params:**

| param | range | default | help (short) |
|---|---|---|---|
| `resynth` | 0-1 | 0 | The share of the resynthesized sustain after the attack. |
| `resynthlife` | 0-1 | 0.5 | The depth of the per-partial modulation. |

**Real time.** 40 partials x voices: fine for mono leads, too costly for pads (patches decide). Analysis data is
loaded in `prepare()`, and the engine does no I/O while rendering.

**Risks.**

- This is the closest lever to "modelling", and it could sound synthetic, like the physguitar. Gate it hard: it ships
  only if blind A/Bs on blueprint-boulevard beat 7a plus lever 1.
- Analysis artifacts on breathy or multiphonic samples.
- A cache format to maintain.

**Effort:** L-XL (1-2 weeks).

## 8. Lever 8 (later): a learned timbre model

**Outlook only. It needs a GPU, so no work now.**

- **What it is.** The learned version of 7b, a DDSP-style model: f0 and loudness (plus a family or pack embedding)
  in, harmonic amplitudes and a noise filter per frame out.
- **Training data.** Our own installed CC0 / CC-BY sample packs, credited per SOURCE.json and kept off NC packs, plus
  the user's reactions in HUMAN_FEEDBACK.
- **Inference.** At render time from Python only (precomputed per note into a cache). It never runs in the engine's
  `process()`, which would mean no deterministic C++ inference otherwise.
- **How it fits.** It follows the learned-generator roadmap (`docs/LEARNED_GENERATOR.md`): rules become evaluators
  first. Here, the realism probes of section 1 and the ears are the scorer.
- **When.** Only once 7b's oscillator bank exists as the synthesis back end and blind rounds show 7b's limits.

## 9. Recommended batches and what the user hears

Each batch is one branch. It merges after the user's listening verdict, which goes into HUMAN_FEEDBACK.

| batch | content | why grouped | user listening set (10-20 s solo pair + 20-30 s in song, A/B labels hidden) |
|---|---|---|---|
| **0** (after lever 1 merges) | Section 1 tooling (`audition --ab`, `build --set`, the probes) + the NoteExpression salvage from `cx-physguitar` | Every lever uses them. NoteExpression unblocks levers 2, 5 and 6. | None: tooling. Report the probe baselines of the reference songs instead. |
| **A** | Lever 2 (round robins) + lever 3 (blend / `veltone`) | The same note-on code path (zone pick, voice tone offset). One engine touch, one re-render list. | (1) nylon arpeggio with repeated bass notes, FreePats nylon, A/B; (2) piano repeated chords (pro-piano-bossa comping) A/B; (3) a piano crescendo, 5-layer concert grand, `blend` A/B; (4) the same in nocturne-etude. |
| **B** | Lever 4 (noises: map move, recorded zones, players; synthesized presets off unless they win) | Mostly Python and data, no engine risk. | (1) the nylon song: squeaks and finger-off, A/B; (2) blueprint-boulevard alto with breath-in and cc122 wind, A/B; (3) gymnopedie pedal thumps A/B. |
| **C** | Lever 5 (Resonance refactor, guitar and violin sets, body bank) | One engine component. Needs NoteExpression `string`. | (1) nylon chords: sympathetic plus body vs plain; (2) gymnopedie or nocturne with `sympathetic` 0.5 on the default grand vs 0; (3) a solo violin scale in D. |
| **D** | Lever 6 (`mono='string'`, `legatodip`, `legatonoise`, `glidemax`) | Builds on C's per-string data. | (1) nylon slides and hammer-ons; (2) blueprint-boulevard alto legato phrase; (3) `_demo_realism` violin pair re-rendered. |
| **E** | Lever 7a (wander) | The direct answer to the static-sax complaint, *if* lever 1 leaves a gap. Pull it forward to right after A if the user still hears a static sustain after lever 1. | (1) a blueprint-boulevard held alto note, lever 1 on in both, wander A/B; (2) a held choir chord (lux-perpetua) A/B. |
| **F** (gated) | Lever 7b | Only if E plus lever 1 lose a blind A/B against reference recordings. | Head-to-head: 7a vs 7b on the same phrase. |
| later | Lever 8 | GPU, data | — |

**Sending to the user.** The A/B pairs go as short mp3s with hidden labels ("1 / 2"), then the in-song excerpt. That
is the user's delivery path (notify; memory "Song delivery via notify"). One question per pair: "which sounds more
played / real?" plus free comments. Every reaction is appended to HUMAN_FEEDBACK with the measured numbers, as earlier
entries were. A lever whose B loses or ties stays at default 0 in the patches and goes to TODO "Parked" with the
reason.

## 10. Effort overview

| lever | engine | Python / data | effort |
|---|---|---|---|
| tooling (0) | analysis probes | cli `--ab` / `--set`, audition probes | ~1 d |
| NoteExpression salvage | Module.h, SongSpec, sampler opt-in | compiler / notation pass-through | ~1 d |
| 2 round robins | sampler note-on | `realism.FAMILY` | 1-2 d |
| 3 continuous dynamics | sampler layer mode, tone | patch values | 2-3 d |
| 4 noises | none expected | `patches.NOISES`, players, `NOISE_ZONES` | 2-3 d |
| 5 resonance | Resonance.h/.cpp, sets, body | guitarist `string`, `tools/voice_body.py` | 3-5 d |
| 6 transitions | `mono='string'`, transition params | fretwork / hornist / ensemble | 2-4 d |
| 7a wander | SustainMap, 2nd reader | patch values | ~3 d |
| 7b resynthesis | additive voice | analysis tool and cache | 1-2 wk |
| 8 learned | — | outlook | — |
