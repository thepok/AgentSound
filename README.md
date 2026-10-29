# AgentSound

**An agent-first, offline DAW: songs are Python code, a C++20 engine renders them, and an analysis report plus a set
of images - the "ears" - let an AI agent judge what it made and iterate, the way a producer listens back.** You tell
a coding agent (Claude Code, or any agent that can run a shell and look at images) the instrumental song you want;
it composes `songs/<slug>/song.py`, renders it, reads the loudness arc, spectrum, stereo image, click zooms and note
dynamics, fixes what it hears and hands over a tagged mp3 / wav with cover art and credits. Parts are *played*, not
triggered: virtual players (pianist, drummer, bassist, guitarist, hornist, jazz comping, articulation for sampled
solo instruments, a singer that sings lyrics with a licensed DiffSinger voicebank) with real moves, budgets and limits; calibrated "hero" sounds carry the leads; production roles
(producer -> arranger -> sound designer -> mix -> mastering -> A&R) give the agent a studio workflow; and every
finished song can get a generated making-of film. Everything renders offline and deterministically (same code +
seed = the same bits).

## Getting started

**Requirements**

- Windows 10 / 11 (the engine uses a few Win32 calls; it is developed and tested there - ports welcome).
- Python 3.11+ (the compose layer is stdlib only: no `pip install`).
- CMake >= 3.24, Ninja and a C++20 compiler, e.g. MinGW-w64 GCC 14.
- ffmpeg on `PATH` (mp3 encoding, decoding reference tracks).
- Optional, for making-of films: Node >= 22, Chrome or Edge, ffmpeg; narration with Breeze TTS 2 in WSL
  (research / non-commercial licence) or the built-in Windows voices.
- Optional, for the learned ears (`python -m agentsound ears`): a separate Python 3.12 venv with PyTorch (CUDA) +
  `audiobox_aesthetics` + `fadtk` (brings `laion_clap`), ~7 GB with the model weights - see section 6 "The learned
  ears". The main Python never needs torch.
- Optional, for sung vocals (`agentsound.singer`): WSL with a Python venv holding onnxruntime(-gpu) + numpy + pyyaml
  (`~/services/singing`) and a licensed DiffSinger voicebank in `assets/voices/<id>/` (Hanami, TIGER; not bundled) -
  see docs/COMPOSE_API.md "Vocals".

**Build and test**

```bash
# put your compiler on PATH first if it is not, e.g. export PATH=/c/mingw64/bin:$PATH
cmake --preset release && cmake --build --preset release && ctest --preset release
python tests/run.py
```

**Make a song**

```bash
python -m agentsound new my-song              # songs/my-song/song.py from songs/_template
python -m agentsound build songs/my-song      # -> songs/my-song/out/mix.mp3, mix.wav, report.json, images, cover, credits
python -m agentsound catalog                  # everything usable: instruments, effects, patches, presets, packs ...
```

Then open the repository in your agent and describe a song; [CLAUDE.md](CLAUDE.md) and [roles/](roles/) are its
working rules.

**Sample packs** (pianos, orchestra, drum kits, guitars, impulse responses) are not in the repository:
`python -m agentsound samples` lists the 261 packs of `assets/samples/manifest.json` with their licences,
`python -m agentsound samples fetch ID` downloads one from its original source (`--all --genre jazz` a genre's set).
Without any pack you still have the synths, the drum synth and the full General MIDI set of the bundled GeneralUser
GS SoundFont (`gm/` patches); band presets name the packs they need. Every build writes `out/credits.txt` with the attributions and
licence warnings (CC-BY needs credit; NC / no-redistribution packs are for private listening).

**DX7 voices**: the `dx7` instrument needs the 8 Yamaha DX7 factory ROM cartridges, which are not distributed here -
see [assets/dx7/README.md](assets/dx7/README.md). Without them DX7 voices (and the DX7-based `synthwave/` patches,
including the template's e-piano) are unavailable and the tests skip their DX7 checks; everything else works.

**Voicebanks** (sung vocals): `python -m agentsound voicebanks` lists the licensed DiffSinger voices of
`assets/voices/manifest.json` (url, licence, range, modes) and whether they are installed; the voices are downloaded
from their official sources by hand (their licences forbid redistribution), never committed. No cloning of real
singers: only licensed voicebanks, synthetic voices or the user's own voice.

**License**: MIT ([LICENSE](LICENSE)). Bundled third-party components (nlohmann/json, the MSFA DX7 core, GeneralUser
GS, CMUdict) and what is used but not shipped are listed in [THIRD_PARTY.md](THIRD_PARTY.md).

## Overview

This file is the central overview. Details live in the references:

| reference | what |
|---|---|
| [docs/COMPOSE_API.md](docs/COMPOSE_API.md) | the Python song API: Song, sounds, samples, heroes, players, automation, mixer, mastering, delivery |
| [docs/RENDER_FORMAT.md](docs/RENDER_FORMAT.md) | the JSON contract Python -> engine, analysis profiles, report fields (space, note dynamics, realism probes) |
| [docs/PARAMS.md](docs/PARAMS.md) | every engine parameter (range, default, unit, help), generated by `build/agentsound.exe params --markdown` |
| [docs/SAMPLE_REALISM_PLAN.md](docs/SAMPLE_REALISM_PLAN.md) | plan (not built): sampled instruments that sound played - round robins, continuous dynamics, player noises, resonance, transitions, a living sustain |
| [docs/ROLES.md](docs/ROLES.md) + [roles/](roles/) | the production roles (producer -> ... -> A&R) and their briefs |
| [recipes/](recipes/) | genre guides; [recipes/HUMAN_FEEDBACK.md](recipes/HUMAN_FEEDBACK.md) = what the user disliked before |
| [CLAUDE.md](CLAUDE.md) | the short working rules for agents in this repo |

## 1. The loop and quick start

```
song.py ──compile──> render JSON ──engine──> mix.wav / mix.mp3 + report.json + PNGs
   ^                                                  │
   └──── judge (report, images, zoom, compare) <──────┘      deliver: mp3 (tagged, cover), wav, credits.txt
```

```bash
cmake --preset release && cmake --build --preset release && ctest --preset release   # engine + C++ tests
python tests/run.py [-j N] [word ...]                           # Python tests in parallel (one process per module)
python tests/run.py --full                                     # + test_notation over EVERY song (~30 min; default: a sample)

python -m agentsound catalog                  # everything usable, one page (engine, patches, bands, DX7, SF2, packs ...)
python -m agentsound find brush               # search it all (all words must match)
python -m agentsound new my-song              # songs/my-song/song.py from songs/_template
python -m agentsound build songs/my-song      # -> out/mix.wav, mix.mp3, report.json, images, cover.png, credits.txt
python -m agentsound build songs/my-song --section chorus       # fast iteration on one section
```

Engine lookup: `--engine PATH`, else `$AGENTSOUND_ENGINE`, else `build/agentsound.exe`. Sample packs: `$AGENTSOUND_SAMPLES`,
else `assets/samples/` (a git worktree has none: point `AGENTSOUND_SAMPLES` at the main checkout's). A band preset whose
preferred pack is missing never falls back silently: compile fails naming the packs, the substitutes and
`samples fetch ID`; `AGENTSOUND_PACK_FALLBACK=1` renders the substitutes anyway, with an error-level `pack_fallback`
report warning. ffmpeg encodes the mp3 and decodes references.

**Notes as text** (`notation`, docs/COMPOSE_API.md "Notation"): `notes('vel=92 C5/8 Eb5 G5/4. F5/8 | Eb5/2 C5/4 r')`
writes a line compactly and fully - sticky note values, relative octaves or scale degrees (`5/8 8 r 10 12/4.!` with
`key=`), rests, ties and holds across checked bar lines (`meter=`, `pickup=`), chords with per-note lengths, tuplets and
free figures, slurs, grace notes, accents / exact velocities / dynamics and hairpins, articulation and glide marks,
ornaments (`^tr`, `^turn`, `^mord`, `^roll`, `^fig`) and pitch gestures (`^scoop`, `^fall`, `^vib`), voices, repeats,
`@beat` positions. `phrases(a1=..., a2=...)('a1 a2 | a1+2d a2')` composes named phrases (transposed per reference,
variants by bar); `hold('F#2 C#3 A3 E4', 8, 70)` is one held chord; `notation.format(clip_or_track)` writes any part back
as text that parses to the same notes (every track of every song round-trips). With it: `s.at(sec, beats)` and
`(section, beats)` positions everywhere, `automate(..., at=)`, `track.cut` / `clear(cut=True)` / `s.breath(before=[...])`
for real stops, `track.fx['compressor'].set(...)`, `Clip.window / vel_add / arch / roll`, `harmonize(keep=False,
fit=prog, fold=)`.

**Form, choruses, endings** (the jazz package, docs/COMPOSE_API.md "Song" / "Jazz"): `s.form('intro:4 head:AABA
solo:AABA out:B,A3o tag:4 end:2', parts=CHANGES)` makes the sections with their changes attached (`.prog`, `.parts`);
`jazz.chorus(band, head, melody, piano=..., comp=..., bass=..., drums=...)` plays a trio / quartet chorus part by part
through the existing players (pianist.arrange + `Arrangement.place`, jazz.comp, walking_bass, brushes) - every option
shared or per part (`jazz.each(...)`, `'A2': {...}`, `None` rests), song-wide `defaults=`; straight-8th and 3/4 lines
(`walking_bass(straight=True, feel='two' | 'push' | 'drive' | 'one' | 'walk')`, `brushes(straight=True, ghosts=,
kick='even', hat8=, ride=)`); `s.ending(end, chords=..., bass=..., drums=..., rit=..., hold=..., room=...)` is the
rolled last chord with ritardando, fermata and room ramp; `track.feature(solo, db=2)`, `jazz.slides(...)`,
`jazz.bombs`, `jazz.last_stir`, `pianist.crushes`. Written classical scores: `romantic.score(rh={bar: notation},
lh=..., dyn=..., meter='12/8', pickup='1/8').perform(s, rh_track, lh_track)` - the nocturne etude's pipeline (touch,
ornaments in real time, singing line, melody rubato, pedal) on top of `notes(expand=False)`; `Score.rubato` / `touch`
are the phrase loops of a slow piece.

**Section plans** (the pop / synthwave package, `sections`, docs/COMPOSE_API.md "Section plans"): sections carry
their harmony (`s.section('chorus', 16, prog=CHORUS)`) and the parts are written per section, every option a
default with per-section overrides (`{chorus: 86, '*': 80}`): `pad.chords(...)`, `arp.arp(mode, ...)`,
`bass.bassline(style, ...)` (`bars=` windows, `then=`, `crescendo=`, `transpose=`, `scale=`, `prog=`, `cut=`);
`kit.plan({sec: [groove, (8, groove_b)]}, fills=..., crashes=..., keep=('kick',))` (fills per section, at positions or
as song-wide rules spaced by the players' fill budget); section lanes `track.levels({...})` / `node.lane(target,
{...} | marks, glide=, default=, drops=, hold=, end=)`; `track.rise(chorus, 16)` and
`s.transitions(riser=, reverse=, impact=, down=).into(chorus, ..., breath=1)`; the robot voice in one call
(`speech.voice(s, words)` + `vox.robot(carrier, say=..., chords=...)`), a talk box (`speech.talkbox(guitar,
singer.mouth(s, line, words))`); `art.perform(preset='sax')`,
`art.throws(spans=)`, `pianist.Player` / `top_leads` / `arrange(doubles=)`, `bassist.Player`, `s.beat_at(seconds,
before=)`, `s.breath(cut=False)`.

**CLI** (`python -m agentsound <command>`):

| command | does |
|---|---|
| `build` | compile, render, encode + tag the mp3, cover, credits, print the report digest (`--section`, `--from-beat/--to-beat`, `--stems`, `--profile`, `--no-mp3`; `--set TRACK.instrument.PARAM=V`: an A/B variant of the same song code in `out/ab/<label>/`) |
| `check` | compile + validate (compose layer, then the engine's strict check), no render |
| `new` | a new song folder from the template |
| `audition` | render a short test phrase with a patch (`--notes` chord / phrase / bass / drums / arp; realism probes repeat / sweep / legato / sustain / pedal); `--set PARAM=V`, `--ab PARAM=V`: A and B loudness-matched plus a blind pair with its key |
| `patches` / `bands` / `params` | list patches, band presets, engine parameters |
| `catalog` / `find` | the overview of everything / one search across it |
| `dx7` / `sf2` / `sfz` / `kit` | DX7 ROM voices, SoundFont presets, what an .sfz holds (`--check`, `--pitch`), what a kit / organ / multisample folder maps to |
| `samples` | list / `fetch` the sample packs of `assets/samples/manifest.json` |
| `zoom` | sample-accurate waveform zoom of the mix or a stem at a moment |
| `compare` | the mix vs a reference track, loudness-matched |
| `mix` | the mix engineer: findings + plan; `--auto` renders, measures, writes `out/mixer/MIX.py` |
| `master` | the mastering engineer: match / `--render` the post-pass / `--check` delivery targets |
| `voices` / `speak` | Windows text-to-speech voices / speak a line to WAV (for the vocoder) |
| `voicebanks` | the singing voicebanks (`assets/voices/manifest.json`): installed?, licence, range, modes; `--check` loads them in the WSL backend |
| `lyrics` | how lyrics are sung: words -> syllables (phonemes, stress) -> notes (`--voice` adds a voicebank's dictionary) |
| `makingof` | the making-of film of a built song: `out/making-of.mp4` from its `film.py` (`--draft` writes a first one, `--script`, `--stills`, `--preview`, `--tts breeze\|sapi\|none`) - see "The making-of film" |

The engine executable has its own commands too: `render`, `validate`, `params`, `dx7`, `sf2`, `zoom`, `clicks`,
`analyze` (report + images of any WAV), `compare-png`, `cover`.

## 2. The engine (`engine/`)

C++20, one executable. `core/` (Module interface, ParamSpecs, tempo map: the frozen contract), `dsp/Dsp.h` (shared
DSP), `instruments/`, `fx/`, `render/` (song parser, routing graph, `Registry.cpp`), `analysis/` (report, images,
file analysis, comparison), `art/` (covers + a public-domain stroke font), `io/` (WAV read / write).

**Instruments**

| type | what |
|---|---|
| `va` | virtual-analog polysynth: 2 osc + sub + noise, supersaw unison, ladder / SVF filter, envelopes, drift, poly / mono / legato, a per-voice mod matrix (`mods`, built with `vamod`) |
| `wavetable` | wavetable synth on the va's voice engine (unison, drift, glide, filter, envelopes, `mods`): 2 wavetable oscillators + sub (sine / tri / square / saw) + noise; smooth morphing `osc<N>.position` (automate it or route env / lfo / velocity to it), warps sync / bend / mirror / fm; band-limited mip levels (one per octave, Hermite-read: no aliasing up to the top note); built-in tables `basic pwm sync formant harmonics organ sine` or table files: Serum (`clm `) / Surge (`.wt`, `srge`) / Vital / Ableton / plain WAV frames, AKWF single cycles (`$AGENTSOUND_WAVETABLES`, `assets/wavetables/`, `./x.wav` next to the song) - `inst.wavetable(...)`, patches `wavetable/` |
| `dx7` | DX7 FM (msfa core) playing the 256 original ROM voices by name (`assets/dx7/`, not bundled: see its README) |
| `drums` | synthesized drum machine on the GM key map, kits 808 909 linn synthwave modern, every piece tweakable |
| `sf2` | SoundFont 2 player (GeneralUser GS by default: full GM/GS set + drum kits; any .sf2 via `file=`) |
| `sampler` | the sampled-instrument core: WAV folders / files / zones with an SFZ-grade zone model - velocity layers, round robin, random layers, release triggers, groups / off_by, crossfades, per-zone envelopes, filters, EQ, LFOs, loops; keyswitch articulations, `mono='legato'` transitions + portamento, live `dynamics` (layer crossfades while a note sounds), `expression`, sustain `pedal`, `vibrato`, `flutter` (living sustain: band-limited random shimmer / jitter per note), `restrike` (re-strike damping: a drum or string struck again damps its own ringing voices, so rolls do not pile up), synthetic round robins `rr*` (per-note tuning / brightness / level / transient, `rrborrow` the neighbouring sample on quick repeats) and `layers='blend'` / `veltone` (velocity layers crossfaded onset-aligned, brightness inside a layer; per-family values in `patches/realism.py`), WavPack decoding (organs), 32-tap sinc interpolation |
| `stack` | 1-8 child instruments on one track (layers): level, pan, transpose, detune, key / velocity ranges with crossfades, velocity curve, note delay, own fx chain; pedal / bend / expression / dynamics forwarded |

**Effects** (by family)

| family | types |
|---|---|
| dynamics | `compressor` (sidechain; `band` > 0 = a keyed dynamic EQ - what `song.carve` uses), `ducker` (keyed or tempo pump), `limiter` (true-peak lookahead; master only), `saturator`, `bitcrush`, `deesser` (sung vocals: split-band or wide sibilance reduction above `freq`, listen mode) |
| tone / utility | `eq` (7 bands), `filter` (lp / bp / hp / ladder), `utility` (gain, pan, polarity, mono; the hero `air` stage and mixer rides are utilities), `width` (M/S + monobass) |
| modulation | `chorus` (Juno I / II), `ensemble` (string machine), `dimension` (Dimension-D), `microshift` (pitch doubler), `flanger`, `phaser`, `tremolo` (+ a slow sine / smooth-random LFO on its rate and depth), `vowel` (formant filter), `wah` (pedal / auto-wah) |
| time / space | `delay` (tempo-synced, ping-pong, ducking), `reverb` (plate hall room chamber cathedral), `gatedreverb` (keyable 80s gate), `shimmer`, `convolver` (impulse-response WAV: halls, rooms, plates, churches, guitar cabinets; `crossfeed` gives a 2-channel IR a true-stereo-like answer to panned sources) |
| colour | `tape` (cassette .. 30 ips: saturation, head bump, wow / flutter, hiss), `exciter`, `amp` (tube guitar amp head: 1-4 cascaded preamp stages, Tube Screamer boost, Marshall / Fender tone stack, presence / resonance, a sagging push-pull power amp, `mix`: the time-aligned DI blended under it (a bass rig); 4x oversampled + ADAA; a cab IR `convolver` after it - the one amp of every DI guitar and the rock bass: `sampled_guitars.amp(kind)`, `bass_rig()`) |
| voice | `vocoder` (channel vocoder 8-40 bands or LPC talkbox; the sidechain is the speech modulator, required) |

**Mixer / routing**: tracks -> insert chain -> gain -> pan -> post-fader sends -> output (a bus or the master); buses
group or return; sidechains key compressor / ducker / delay / gatedreverb / vocoder from any node's post-fader signal;
**taps** move a send, a sidechain key or a follower earlier - `prefader` (parallel compression / grit buses that keep
their blend when the fader rides), `prefx` (the dry instrument) or `pre:<fx>` (before an insert: a hero's bed duck
listens before its echo and ride) - `sends={crush: (-6, 'prefader')}`, `s.sidechain(..., tap='pre:echo')`;
muted tracks still run (vocoder modulators, ghost key tracks); cycles are errors; only the master may add latency.
**Chain order** is checked at compile: a compressor / saturator / amp / bitcrush / driven tape after a delay, reverb,
chorus or doubler in one chain is a warning (drive first: `s.track(..., pre=[...])`), so is anything but a utility after
the master limiter.

**Automation and modulation**: point lanes (`linear exp smooth step`) on `instrument.<p>`, `fx.<i|type|name>.<p>`,
`gainDb`, `pan`, `send.<bus>`, layer params (`instrument.layers.<id>.<p>`); track modulators (`lfo`, `steps`, `gate`,
`follow`, `envelope`, `sample_hold`) evaluated every 32 samples on the beat grid, windowed, stackable, with
automatable depth; the va's per-voice matrix. **Tempo map**: set / ramp / ritardando / accelerando / fermata / rubato,
meter changes; every tempo-synced effect, modulator, humanize ms and the report follow it.

**Rules** (enforced): strict everywhere - unknown params / keys / types / ranges are errors (exit code 2), nothing is
silently ignored; deterministic - the same render JSON + seed gives bit-identical audio, all randomness through
`dsp::Rng`; no allocation, I/O or exceptions in `process()`, finite output.

## 3. The sound library

Patches are named sounds (`s.track('lead', 'synthwave/supersaw_lead')`, `patches.get(name).but(...)`), each levelled
to -18 LUFS on its audition phrase and carrying its sends. `python -m agentsound patches [prefix] [-v]`,
`audition <patch>`. 339 patches:

| prefix | count | what |
|---|---|---|
| `sampled/` | 195 | real instruments from sample packs (lazy: a missing pack errors only when rendered) - drums & percussion 56 (acoustic kits, brushes, ~16 classic drum machines, percussion, timpani), pianos & keys 19, guitars 21 (the acoustic: `sampled/acoustic_guitar`, Shinyguitar mics with its recorded chucks and fret noises), basses 12, strings 23 (the symphonic sections one per track: `sampled/violins_1` `sampled/violins_2` `sampled/violas` `sampled/celli` `sampled/double_basses`, seated, keyswitched), brass 15 (muted a3 sections `sampled/horns_muted` `sampled/trumpets_muted`), woodwinds & saxes 19 (the a2 / a3 sections `sampled/flutes` `sampled/oboes` `sampled/clarinets` `sampled/bassoons`), organs 8, choir 4, tuned percussion 5, vintage samplers / synths 12 (Fairlight, Mellotron, Solina, poly) |
| `synthwave/` | 46 | va / dx7 / drums synth sounds: pads, leads, basses, arps, drums, FX, vocoder choir / lead, talkbox |
| `layered/` | 18 | `stack` patches (piano + glass lead, e-piano -> grand split, octave strings, sub bass ...) |
| `hero/` | 20 | the hero presets (below) + three legacy names |
| `bus/` | 39 | return / group chains: hall, plate, echo, gated, shimmer, tape echo, `hero_plate`, `hero_plate_70s`, 22 convolution spaces `bus/ir_*` |
| `gm/` | 12 | calibrated GeneralUser GS presets |
| `cab/` | 5 | guitar amp / cabinet chains for DI guitars: the engine's tube `amp` (clean blues crunch rock metal voicings) + the cabinet IR |
| `wavetable/` | 5 | wavetable synth sounds (built-in tables, no files): warm pad, evolving pad (vowels wandering, a harmonic bloom), pluck (a harmonic strike falling back), bass (a position "bite"), a lead WITH an octave-down body, glide and vibrato |
| `edm/` | 7 | EDM sounds (recipes/edm.md): the club bass (clean sine sub + driven mid), reese, supersaw chords, future-bass chords (formant, wobble), the pluck, the supersaw lead WITH an octave-down body (never a thin beep), the vocal-chop chain |
| `master/` | 5 | master chains (synthwave, dreamwave, darksynth, edm: the loud club master, audition) |

**Other sources**: `inst.dx7('NAME')` (256 ROM voices, `dx7 [search]`), `inst.sf2('Preset')` (GeneralUser GS 2.0.3,
287 presets; `sf2 [search]`), `inst.sfz(path, articulation=, cc=, mics=, hammers=, velcurve=)` / `inst.sfz_multi`
(SFZ importer: inheritance, includes, keyswitches live, dynamics controller live, mic mixes; unsupported opcodes are
reported), `inst.kit(dir)` (any drum one-shots, Hydrogen, DrumGizmo -> GM keys with layers / round robins),
`inst.organ(dir, stops=[...])` (GrandOrgue pipe organs), `inst.multisample(dir)` (note-named samples),
`inst.sampler(...)`, `inst.stack(layer(...), ...)`.

**Hero sounds** (`hero()`, `agentsound.heroes`): THE way to put a hook or solo in front. `hero(track, family=...)`
replaces the sound by the family's build (source + optional takes / octave layers + a shared chain `heroes.ORDER`:
tone -> catch -> comp -> deess -> amp -> drive -> tape -> presence -> exciter -> chorus / double / width / dimension -> `air`
-> echo) and applies logged, switchable
mix rules: plate / echo space, bed duck, `carve` (keyed dynamic EQ on the bed), presence dips on competitors, rides in
the hook sections, echo throws on phrase ends. Presets (`heroes.presets()`): `sax` (THE hero sax in every genre, v2:
the late-70s record sax the user picked by ear - Weresax dynamic mic with a breath trace, 4:1, tube + tape grit,
near-mono, a 10 Hz smooth-random autopan, a bright 3.6 s plate; play it with `hornist.arrange(..., style='hero70s')`;
opt-out `sax_clean` = the v1 double-tracked hero `layered/hero_sax`), `piano`, `piano_pop`,
`piano_strings`, `piano_synth`, `guitar`, `guitar_clean`, `guitar_heavy`, `synth`, `darksynth`, `strings`, `brass`,
`woodwind`, `voice`, `vocal` (a sung lead vocal of `singer`: vocal compressor, presence, a de-esser after the boosts;
DRY and close by default - its own short pre-delayed `bus/vocal_plate` 15-20 LU under the voice by genre, no constant
echo, throws only on section ends for pop / rock and none for jazz / ballad, no inherited band hall / room), `organ`,
`generic`. `heroes.air(track, points)` writes breath after the compressor;
`hero.play(track, clip, at)` plays with the family's player. **Vocal grit** (the guitar amp on a sung voice):
`hero(vox.track, family='vocal', grit='light' | 'crunch' | 'megaphone')` - light / crunch a parallel tube-amp bus
(300 Hz-5 kHz in, a speaker roll-off out) blended -9 / -5 dB under the untouched clean vocal (the consonants stay),
megaphone the whole voice band-limited and driven; level-matched (`heroes.grit_trim`), tweakable
(`grit={'amount': 'crunch', 'blend': -7, 'gain': 7}`); A/B: `python songs/_demo_vocal/grit_ab.py`.

**Sample packs**: `assets/samples/manifest.json` lists 261 packs (url, license, attribution, category, genres; 67 of
them impulse responses); the packs themselves are git-ignored. `python -m agentsound samples [--genre G --category
C]`, `samples fetch ID` downloads, unpacks, converts FLAC -> WAV and writes `SOURCE.json` (license / attribution) and
`INDEX.json` (structure, SFZ summaries). Licenses range from CC0 / CC-BY to non-commercial and no-redistribution:
fine for private listening, check before publishing. The build writes `out/credits.txt` from the files a song
actually uses and prints the CC-BY attributions and license warnings.

## 4. The players

Every part is played, not triggered: named MOVES usable alone, an arranger that picks them by context and seed,
BUDGETS that keep flashy moves rare (a `Memory()` counts them song-wide), touch dynamics, per-hand timing,
playability checks, and a log (`.moves`, `.budget`, `.summary()`).

| player | entry points | plays |
|---|---|---|
| `pianist` | `pianist.arrange(melody, prog, bpm=, style=)` (`.place(piano, comp)`), `Memory`, moves (trill, tremolo, turn, crush, gliss, runs ...), `crushes`, `pianist.vocabulary(style, lh_track=)` (the solo vocabulary) | voicing devices under the melody, ornaments and fills (the fast ones - trills, tremolos, runs, sweeps - budgeted per `fast_every`, never in loud bars), left-hand styles in any meter (the shell hand: shells, bass + rootless chord, rootless voicings, comping pushes), pedal; a piano SOLO through `soloist.solo` (every phrase harmonized, runs / 4ths / blues crushes as spice, the trill or tremolo saved for the climax, the left hand comping under it) |
| `romantic` | `score` (+ `Score.perform` / `rubato` / `touch`), `fioritura`, `trill`, `turn`, `grace`, `accompany`, `lean_on_long`, `cantabile`, `dynamics`, `melody_rubato`, `pedal_changes`, `figure_stats` | the classical / romantic pianist for written scores (Chopin, the nocturne etude): fioriture as shaped gestures in real time, trills with a start and a Nachschlag, the 12/8 bass-chord-chord left hand, the singing line (long notes lean, the next note plays into the decay), hairpins, melody-only rubato over a steady left hand, pedal per harmony with flutter in chromatic runs; the performance RULES from the research (melody lead + chord spread as the hammers' velocity artifact, syncopated / half pedalling, melodic + harmonic charge, articulation, every phrase's own tempo arch, the left hand's dynamics and chord rolls: [docs/PIANIST_RULES.md](docs/PIANIST_RULES.md), A/B in `songs/_demo_pianist`) |
| `expressive` | `KTH`, `CHARGE`, `melodic_charge`, `harmonic_charge` (per-change keys, `tension`), `punctuation`, `correlated`, `HIGH_LOUD` | the performance rules every player shares (KTH Director Musices: melodic / harmonic charge, punctuation, high-loud; AR(1) correlated timing): the pianist (`romantic`) and the orchestra (`bandlib.ensemble`: `orch.perform`, `orch.Score`) each turn them into their own vocabulary - velocity and pedal, or the dynamics lane and a bow lift ([docs/ORCHESTRA_RULES.md](docs/ORCHESTRA_RULES.md)) |
| `organist` | `organist.perform(song, band, [organist.Voice(notes, role, name, kind=, touch=, ornaments=, accel=, breathe=)], phrases=, seed=)`, `TOUCH`, `ORNAMENTS`, `HAND`, `articulate`, `ring_gaps`, `parallel_motion` | the PIPE ORGAN, which has no touch dynamics: articulation per voice (legato / cantabile / ordinary / detache / staccato drawn by note values and tempo; a repeated note always re-struck; one pipe per key - a key struck again inside a held one re-strikes it), one body gesture (`humanize` body 'organ') that every voice follows, an agogic late downbeat, breaths before phrases and big chords (the accompaniment may keep its pickups: `breathe=False`), the registrant's gap at a registration seam, per-hand timing and chord spread, upper-note trills with a turn / mordents / turns at the organ's rates, rushing runs (`accel`); two registrations of one manual never at once; records `song.organ_voices` (recipes/organ.md) |
| `organ_vocab` | `harmonize`, `satb`, `flow`, `counterline`, `bass_line`, `toccata` (`TOCCATA_FIGURES`), `fugue`, `planing`, `ornament_targets`, `slots_from_chart` | the organ's textures from a tune + a chart: a chorale harmonization (a dynamic program over the key's chords, cadences at the phrase ends, a cadential 6/4), SATB voice-leading (a beam search: no parallel 5ths / octaves - also from a passing note -, leading tone and 7ths resolved, root-position cadences), passing 8ths and 4-3 suspensions, ONE-motif counter-lines (a Bach chorale prelude's figure), a walking pedal free of parallels with the tune, toccata figuration (Widor's oscillation, broken chords, the turn cell, the rocking figure, scale runs; voice-led off-beat chords), a fugal exposition (tonal answer, countersubject), Vierne / Messiaen planing |
| `drummer` | `drummer.arrange(song, style=, kit=)`, `Memory`, `Kit.of(...)`, moves (tom_run, build, stop ...); solo: `perform(steps)`, `vocabulary()` (for `soloist.solo`), `rudiment`, `pattern`, `Hands`, `DrumMotif`, `SOLO_MOVES`, `feet`, `choke`, `hat_lane` | a whole form: grooves per style and section role, budgeted fills, crashes, builds, stops, endings (a hit grabbed by a choke); four limbs with speed limits; kick locked to the bass. A drum SOLO: a stroke language (stickings, accents, ghosts, flams, drags, buzz, kit voices), the hands' physics (a weaker hand, stick heights, rebounds, up-strokes, reach, sticking-aware speed limits), the PAS rudiments orchestrated around the kit, feet ostinatos and double bass, the live hi-hat openness lane, cymbal chokes, per-hand samples, and solo moves (motif and its development, tom melodies, call and response, 3 over 4, fives, quintuplets, half / double time, linear, hand-hand-foot triplets, speed bursts, press rolls, the gated tom break, silences, the big finish) played in order by `perform()` or by `soloist.solo()` |
| `bassist` | `bassist.arrange(prog, bpm=, style=, kick=)`, `Memory`, `touch`, moves (slide, approach, octave_pop ...) | styles rock pop country funk motown disco ballad reggae tumbao synth walking; kick lock / interlock; fingering and tempo limits |
| `guitarist` | `guitarist.arrange(...)` (rhythm), `guitarist.lead(...)` (`gestures=True`: fretwork bends / vibrato), `guitarist.vocabulary(style)` (the solo vocabulary), `Fretboard`, `shapes`, `Memory`, `HANDS` / `HandFeel` (`hand=`) | real chord shapes, strum / pick patterns per style and section, palm mutes / dead notes, double-tracked takes; lead bends, vibrato, slides, hammer-ons; the HAND FEEL ('acoustic', 'fingerstyle'; styles `songwriter`, `fingerstyle`): drawn tempo / force-dependent strum spread, lighter late up-strokes on 2-5 top strings, partial strums, drifting time and loudness, drawn lifts at changes, thumb vs fingers, pinch lag; on `sampled/acoustic_guitar` the recorded chucks and budgeted fret / shift noises (`songs/_demo_acoustic`: strum, fingerpicked ballad, A/B on `sampled/steel_guitar`); CHORD MELODY `arrange(..., melody=clip, slur=)`: the tune fretted on top of the picked pattern on the highest string the grip reaches, the pattern kept under it, close steps now and then hammered on / pulled off (`songs/patio-de-naranjos`: solo nylon guitar on `sampled/concert_guitar`) |
| `guitar_riff` | `guitarist.riff(spec, bpm=, section=)`, `pedal`, `hits`, `build_up`, `double(part, (gtr_l, gtr_r), at)`, `cell` | the rock riff player: riffs written as steps ('E> - . E . . G> -'), played by the section's energy (verse palm-muted single notes, pre-chorus chugged power chords, chorus open power chords + octave), stops in unison with the drums, the pre-chorus chug build; the double-tracked wall: two real takes (drifting timing, tuning drift, other round robins, two guitars / amps) |
| `fretwork` | `fretwork.bend`, `prebend`, `ghost_bend`, `unison_bend`, `oblique_bend`, `vibrato` (`VIBRATOS`), `hammer_on`, `trill`, `legato_run`, `slide`, `slide_in` / `slide_out`, `picked_run`, `tremolo_pick`, `sweep`, `rake`, `pinch`, `palm_mute`, `whammy_dive` / `whammy_scoop` / `whammy_vibrato`, `feedback`, `wah` / `wah_talk`, `pick_scrape`, `squeak`; `render(track, parts, at)` | the lead guitarist's hands inside and between notes (a guitar hero's micro-performance, like the hornist's breath): bends that rise fast, overshoot and settle, pre-bends, unison bends (the held string on a twin track / the sampler's per-note `bendfollow`), finger vibrato that only goes UP (down from a bent pitch), legato without the pick, alternate picking with accents, sweeps, pinch harmonics and controlled feedback (the sampler's `harmonic`), palm mutes, whammy, wah, pick scrapes |
| `soloist` | `soloist.solo(song, track, vocab, at=, arc=, motif=, budget=, prog=)`, `Move`, `Vocabulary`, `Ctx`, `Part`, `Budget`, `ARCS`, `develop` / `vary` / `transform`, material lines (`target_line`, `answer_line`, `run_line`, ...) | the instrument-agnostic SOLO: a dramatic arc (statement -> call / response -> varied repetition -> speed burst -> climax -> resolution; `jazz`: one peak two thirds in) over any player's vocabulary (`guitarist.vocabulary`, `hornist.vocabulary`, `pianist.vocabulary`), motivic development of the song's hook (quoted literally at most twice; a 3-5 note cell of it developed call by call - sequenced, inverted, displaced, truncated, augmented: `motif_line`), free phrasing across the bar lines, target-first lines, the chord's own scale (chromatic notes only as approaches into the beat), no octave wraps / verbatim bar repeats, one ornament budget, dynamics never flat (`songs/_demo_soloist`: the same arc on the sax and the guitar) |
| `hornist` | `hornist.arrange(melody, bpm, family=, style=, section=)`, `hornist.vocabulary(family, style=)` (the solo vocabulary), `Memory`, `.place(track, at)`, moves (push, pulse, swell, bloom, taper, vibrato, scoop, fall, shake, lean_in, turn_away, bell_swing ...) | the wind player (sax, trumpet, trombone, flute, clarinet, bowed strings): breath INSIDE held notes (air pushes / swells on the post-compressor `air` stage or live `dynamics`), air-coupled vibrato, budgeted pitch spice, mic technique (bell toward / away from the mic via a `mic` EQ + reverb sends), and the continuous body sway relative to the mic (`sway=1` in hero / pop / ballad / jazz, 0 in classical, `gesture.sway`: distance / axis / room / a little pan drift at 0.1-1 Hz, the bell lifting toward the peaks and sinking at phrase ends) |
| `jazz` | `jazz.band`, `chorus`, `comp`, `walking_bass` (straight / 3/4 too), `brushes`, `brush_colour`, `ride_pattern`, `bombs`, `last_stir`, `slides`, `horn_line`, `solo_line`, `paraphrase`, `block_chords`, `Feel` | the jazz vocabulary: rootless / shell / quartal voicings, comping cells, walking lines, brush kits, horn phrasing (scoops, falls, swells, vibrato) |
| `articulation` | `perform`, `legato`, `expression`, `vibrato`, `throws`, `auto_articulate` | sampled solo instruments played: live dynamics, legato, portamento, keyswitches, echo throws |
| `singer` | `singer.sing(song_or_track, line, lyrics, at=, voice=, style='pop'\|'rock'\|'jazz'\|'ballad', seed=, moves=, pitch='hybrid', mic_pull=, back_phrase=, ornament=, messa_di_voce=, emphasis=)`, `double`, `harmony`, `prism`, `mouth`, `chops`, `tune_curve`, `Memory`, `check`, `diction`, `voice`; `lyrics` (`align`, `check`, `g2p`, `syllabify`, `spell`: German lyrics by hand phonemes, `songs/die-faehre-um-sieben`), `voicebank` (`voices`, `get`, `check_prompt`) | a SUNG lead vocal with lyrics from the score, rendered by a licensed DiffSinger voicebank (Hanami, TIGER) in WSL and played back as takes: consonants before the beat, vowels held, word-final consonants sung and audible (at the end of the word's last note, minimum lengths, a final stop released, never under the phrase-end release), glides, scoops, late growing vibrato, falls (budgeted), audible breaths, voice colour (soft / power modes) following the dynamics, timing feel; the calm `jazz` / `ballad` styles (sung soft - the soft mode alone, the level by make-up gain -, laid back behind the beat, few small scoops, a slow late narrow vibrato, no falls; the mic technique on long held words - she slowly pulls back from the mic, the note fades a few dB with less proximity bass and a touch more room, leaning back in for the consonant: `mic_pull`, on for jazz / ballad, written after the vocal compressor); the expression - back-phrasing (a phrase laid back against the band, caught up by its landing note; never early in the calm styles), ornaments on a melody's repeats (grace notes, a turn, a small run on an open vowel, a blue note - budgeted, the syllables stay), messa di voce on held peaks (voice mode + the level after the compressor), and the lyrics' markup `*word*` (emphasis) / `(( line ))` (intimate, near-whispered); doubles and harmonies are sung again (not copied / shifted); processed-voice effects: pitch correction on the sung curve (`sing(tune='hard'|'soft', retune_ms=, key=, scale=)`: the Cher / T-Pain step with flips on every note change, or a soft 40 ms correction), the harmoniser / Prismizer `prism(vox, harmony, preset='choir-of-one'|'prismizer')` (the line RE-SUNG by 3-6 takes on the chord tones around it, voice-led, level-matched, own timing / formant / pan, optionally hard-tuned), the talk box's `mouth` (the words mouthed on one low pitch for `speech.talkbox`: the vocoder in LPC mode after a guitar's amp; its level follows the line's velocities) - `songs/_demo_vocal_fx` (A/B set: `make_ab.py`); VOCAL CHOPS `chops(vox, line, at=, slices=, unit='syllable'|'word'|'phrase')` (slices of the part's own rendered takes on a sampler track, retriggered in the rhythm of a line and pitched to its notes - the EDM / future-bass chop; `songs/one-more-round`); the robotic baseline `moves=False` for A/B; the vocal checks (intelligibility 2.5-6 kHz, buried, harsh, diction: word-final consonants too short / buried, the wetness in LU vs the dry voice). Consent rule: no cloning of real singers (`songs/_demo_vocal`) |

Shared feel (`humanize`): `touch(clip, lo, hi)` writes phrase-shaped melody velocities, `bass_touch` the same for bass
lines, grooves, swing, `jazz_groove` / lay-back per part, and the player's BODY (`track.humanize(body='calm' |
'lyrical' | 'swing' | 'waltz', lead=)`, on the jazz presets' piano hands by default, the endless piano feels' own): one gesture per phrase moves timing and
dynamics together instead of random jitter - the phrase arc (faster and louder into its peak), a ritardando into phrase
and section ends on the decelerating-motion curve, a leap's landing late, a breath before a phrase, the weight in the
bar; the left hand moves with the right (`body_stats(song)` measures the coupling). Shared performance layers: `gesture` (the moves INSIDE a note
as additive shapes on abstract lanes - pitch bend, vibrato, air, mic, harmonic, wah, palm mute, echo -, sampled
click-free; the hornist and fretwork are built on it) and `budget` (one ornament budget for every player: the
pianist's, bassist's, drummer's, guitarist's, hornist's and soloist's tricks; zero spacing disables a Budget class by
default, while `zero='unlimited'` removes its spacing; `guitar_vocab` and `horn_vocab` hold the solo vocabularies). Rules from the user's feedback: flat velocities read as
robotic (the report's `flat_dynamics`), ornaments and fills are spice, not habit, and a player breathes - silence
between phrases, phrases at different levels (an endless line of notes reads as monotone).

Voicing (`voicing`): `voicing.chorale(table, voices=voicing.STRINGS, key='C minor')` / `voicing.voice(steps, ...)`
voices chords into real parts around the lines written by hand - any voice set (`SATB`, `STRINGS`, `WINDS`, `WINDS8`
the interlocked wind pairs, `HORNS`, `BRASS`, `TUTTI`): chord tones in range, no crossing, complete chords, no doubled
leading tone or seventh, no parallel fifths / octaves, the smallest motion, no semitone rub against the written lines.
`voicing.check(parts, harmony, voices=...)` reads written parts back (parallels between EVERY voice pair, semitone
clashes, strong-beat non-chord tones, ranges, crossings); `arpeggiate` / `passing_eighths` give a fugue's free voices
motion without parallels or rubs (songs/lux-perpetua, songs/unbowed). ONE harmony object: `s.prog(...)` /
`s.harmony(table, at)` return a `voicing.Harmony` (a Progression from a progression string or a voicing table) that
voices itself - `.chorale(voices)`, `.under(melody, STRINGS)` (the parts under a written line) or `.under(line, 3)`
(block harmony), `.voice(register, voices, vel)` (a section's divisi), `.tutti()`, `.figure('oompah' / 'broken' ...)`.
`voicing.fugue(entries, ...)` writes a fugue / fugato (entries as written, free voices voiced, their counterpoint,
who leads when), `voicing.imitation(cell, entries)` imitative entries; `figures` holds the textures (`'pulse8'`
string drive, `'offbeats'`, `'syncope'`, `'beats'`, `'tremolo'`, oom-pah, Alberti, broken chords, ostinatos).

The orchestrator's desk (`bandlib.scoring`, as `orch.*`): `orch.Score(s, band, DYNAMICS)` holds a whole piece's
parts with ONE dynamics map (marks, hairpins, subito, bar accents, phrase arcs) and performs them at the end - held
notes follow a written crescendo (`follow=True`); `sc.double` / `colla_parte` (doublings with per-section offsets),
`sc.hits` (tutti chords), `sc.brass` (natural trumpets + horns + timpani on the chord tones), `sc.unison`,
`sc.winds`, `sc.stabs`, `sc.fermata`, `orch.bed` (a section's held harmony in one call); `orch.Choir` makes a sampled
choir speak on time (speaking velocity, the written dynamics on a lane, syllable gating, swells); `s.arc(rides)` is
the conductor's section arc on the master input (songs/unbowed, songs/lux-perpetua, songs/ashes-and-chandeliers).

Every sustaining part goes through `orch.perform`, which PLAYS it by the orchestra's performance rules
(`bandlib.ensemble`, from the performance research, each a distribution or a budget in a table with its source and
range: [docs/ORCHESTRA_RULES.md](docs/ORCHESTRA_RULES.md)): sections a little apart (Rasch's asynchrony: a seat
offset, the leader's drift the others follow, each section's own correlated deviation - strings looser than winds,
slow music looser), one dynamics curve per phrase (messa di voce on long notes, accents only where a note stands
out, an ff accent heard as its fall), legato overlaps by family with bow changes / tongued repeats and a lift at a
melodic group's end, down-bow / up-bow weight, wind and brass breaths by an airflow budget at the best phrase point
(staggered in chords, a quick catch breath after a held note), tongued brass entries and blooming horns, staggered
releases with a taper, solo vibrato that starts late and deepens with the dynamics. `orch.Score(..., style=)` picks
`'baroque'` (terraces), `'classical'`, `'romantic'` or `'film'`; it keeps every accompaniment phrase under the melody
(BALANCE) and adds the melodic / harmonic charge the pianist uses too (`expressive`). `rules={'breath': {...}}` on
`orch.perform` / `orch.Score` changes single values (unknown keys are errors). Same-notes A/B:
`songs/_demo_orchestra_player`.

## 5. Band presets, genres, recipes

`b = bands.make('name', s)` (or `bands.<name>(s)`) sets up a complete, mixed ensemble - roles -> tracks, rooms,
sends, sidechains, master chain, analysis profile - tuned against a reference or a demo song (`songs/_bands/<name>`).
`python -m agentsound bands [genre]`, `print(b.describe())`. Presets live in `agentsound/bandlib/<genre>.py`; `bands.Builder` owns track construction and explicit bus reuse /
new-bus policies. Pop and EDM keep each lead sound, pack fallback, chain and trim together in `LEADS` records.

| genre | presets |
|---|---|
| synthwave | `outrun`, `retrowave`, `dreamwave`, `darksynth`, `scifi` |
| jazz | `jazz_trio` (`voicing='smooth'`: solo_piano's softened grand, a wetter club with a plate on the piano - the endless jazz-trio sound), `jazz_quartet`, `jazz_ballad`, `bossa`, `soul_ballad` (Rhodes, two-feel upright, stirs), `solo_piano` (one grand voiced warm and smooth: the endless jazz-piano sound), `lofi_piano` (the felt Osiris piano dull and warm, a dusty kit ducking it, a vinyl surface-noise bed - `lofi_crackle()` -, a wobbly hissing cassette master: the endless lofi-piano sound); `lead='vocal'` seats a sung lead inside the band (faders, drive, the voice -3 dB) |
| pop | `pop_band`, `funk_band` |
| edm | `house`, `techno`, `big_room`, `future_bass`, `melodic_house` (909 / 808 / main-room kits + sine sub, the kick pumping bass / chords / pad, `edm/*` sounds, `master/edm`; grooves per section kind in `band.info['grooves']`) |
| rock | `rock_band`, `indie_band`, `power_ballad` |
| orchestra | `string_quartet`, `chamber_orchestra`, `symphony_orchestra`, `film_orchestra`, `church_organ` (a Lars Palo GrandOrgue organ in its church, `organ='burea' | 'pitea'`: registrations as roles - soft / principal / full / pedal / pedal_full + `registers=` flute, positiv, cornet, reed, trumpet, oboe, strings, swell_full, pedal_soft, pedal_cantus on their manuals; `tremulant=` True or per role; the swell box `orch.swell(band, points)` on the Swell's roles) |

**Recipes** (read before composing): [synthwave](recipes/synthwave.md), [jazz trio](recipes/jazz-trio.md), [jazz composition](recipes/jazz-composition.md) (writing heads and solos),
[pop](recipes/pop.md), [rock](recipes/rock.md), [classical](recipes/classical.md), [EDM](recipes/edm.md), [organ](recipes/organ.md) (registration, idioms, the church), [SimCity](recipes/simcity.md) (the SimCity 3000 city-building jazz: research, sounds, form) - sound palette, progressions,
arrangement, mix targets, hero sounds; plus [HUMAN_FEEDBACK](recipes/HUMAN_FEEDBACK.md).

**Analysis profiles** (`ANALYSIS = {'profile': ..., 'loudness': [lo, hi]}` in song.py or `build --profile`): `default`,
`synthwave`, `dreamwave`, `darksynth`, `jazz`, `classical`, `piano` (solo piano: classical thresholds, a piano spectrum), `organ` (pipe organ in a church: the 16' foundation, a top that follows the registration; an organ's tracks - `analysis.registration`, every `inst.organ` track - are judged by their registration / swell across the sections, not by touch dynamics), `pop`, `edm` (club: kick + sub, loud -10..-6 LUFS), `rock`, `film` - each a reference spectrum,
loudness window, LRA / PLR limits, space targets and note-dynamics threshold ([RENDER_FORMAT.md "Analysis
profiles"](docs/RENDER_FORMAT.md)).

### Endless generators (`agentsound/endless`, `python -m agentsound endless GENRE`)

Music on demand WITHOUT an LLM: a seeded, rule-based tune composer writes an original lead sheet (form AABA /
ABAC / 12-bar blues, key, tempo, feel, jazz changes from ii-V-I / turnaround / backdoor / tritone / bridge blocks, a
singable motif-based melody checked against the chords) and the library's players perform it (`pianist.arrange`
heads, a `soloist.solo` chorus with `pianist.vocabulary`, the head out paraphrased, `s.ending`), then a quality gate
reads the report (0 clicks, no flat lead, 0 silent notes, loudness in range; a failed seed is rerolled).
Genres are DATA (`endless.genres`: forms, moods -> feels / keys / tempo / chord colours, the band preset, the
arrangement plan): `jazz-piano` (solo piano on the `solo_piano` preset, the default) and `jazz-trio` (+ bass and brushes, `jazz_trio` with `voicing='smooth'`). Swing is an option
(off by default: `--swing` or `--swing 0.58`); the feel suits the form (a blues swings or is a straight-8th shuffle
with a stride left hand, a bossa wants a song form).
It plans top-down before any note (`genres.ARCS`, one mechanism on every level: an arc curve + targets): a stream
of tunes follows a **set arc** (a medium opener, contrast in feel / tempo / key, a ballad after an up-tempo tune, the
highlight past the middle, a quiet closer; printed at the start of every set), every tune a **tension arc** per form
(AABA: calm A1, A2 alike with another cadence, the bridge climbing, THE climax - the tune's single highest note - drawn
in the form's last section (the last A restates its first phrase and climbs to it) or at the bridge) that sets each
phrase's register, line density, chord colour and the pianist's touch; every A spans an octave or more; the
phrases are gestures, then notes fill them - each 4-bar phrase with its own register and landing goal, the part's
peak 60-75 % through it, the chord changes met by guide tones, a strong-beat tension resolved by step in most
phrases, a rhythm cell at most twice per 8 bars (the hook's rhythm developed in its later phrases: displaced,
truncated, augmented), phrase endings drawn (downbeat, anticipation, pickup, a breath for the left hand; the bridge's
line runs into its turnaround). Identity: one hook and a theme
RESTATED note for note in every A (only the cadence bars are new; a blues chorus is AAB, its second chorus varies
where it is drawn - its answer, its second statement, or calmer - over its own second ending), a bridge in its own
register with long notes against the moving lines,
an intro of its own (a weighted vamp from `genres.INTROS` - bVImaj7#11-V7b9, IV-iv-ii-V, iii-VI-ii-V, a pedal, the
riff alone an octave low ... - with a drawn line over it: a fragment of the hook augmented, sequenced or answered,
never the head's bars copied) and a tag that develops the hook's head with a twist (an approach
drawn: the tritone sub, the backdoor, the minor plagal, a deceptive cadence, a cold stop - into a 6/9 / mMaj9 end
chord, its roll / spread / plink / cadenza / fade and its grip drawn too).
`composer.shape(tune[, song])` measures it (climax place, hook recurrences, register / touch following the arc, the
solo's build); the runner rerolls a tune that breaks it. The solo plays the tune's chart (three quarters of the tunes
one cadence of a head-out part played another way - tritone, backdoor, pedal, minor plagal, a ii-V -, in the last solo
chorus and the head out alike, the melody singing the substitute's colour) in a SHAPE drawn per tune (a rise, a slow
build, an answer-and-develop arch, less is more, a block-chord chorus - each climbing to its climax in the last
stretch and resolving -, rarely trading 4s with the left hand; double time only in ~30 % of the tunes, before the
climax), built from a cell of the hook developed call by call in lines of every length (a fragment to an 8-bar line,
breaths of a beat or two), ending on a tone of the head out's first chord, every lick at most once per piece and
rarely in the next tune of a set; the whole piece's dynamic plan is drawn per tune (`plan['dynamics']`: the peak - the
piece's highest note, `perform.CLIMAX` - in the solo's last 8-16 bars, 60-75 % in, a 3rd-6th over the head's top,
v110+; a 2-bar block-chord shout at the head out's top note in ~13 %), the head out at the head's level, the tag
coming down only in its last bars, the final chord a few LU under the piece with nothing after it. The head sits
high (around A5) with its hook a 1-bar cell sequenced along the root motion in half the tunes. `composer.tells(song, tune)` measures the blind test's tells (`songs/_blind/ROUNDS.md`:
silent solo bars, octave wraps, verbatim repeats, the solo's density / velocity against the head, repeated fill
shapes, harmonized fast notes, literal hook quotes; round 2: the intro / tag copied, isolated reharms, the head's
5-note shape recurrence, the solo's duration entropy, a loudness range, where the peak sits, silent left-hand bars;
round 3: on / off-beat velocity and zig-zag in lines, repeated notes, chord clashes per rule, empty solo bars, the
solo / head-out loudness, fast figures per chorus, the left hand's rootless voicings and anticipations, the vamp /
line / reharm slot drawn; round 4: phrase goals and pitch circling, rhythm cells per 8 bars, strong-beat tensions,
the bridge's register / rhythm, phrase endings, the solo's line shapes, chord tones on the beat, double time, licks
recurring in a solo and across tunes, chart variants, tag approaches, final chords, feel / form; round 5: chord-
arpeggio bars and motif-derived phrases in the solo, onset-pattern reuse, guide tones at the head's chord changes,
chromatic notes by resolution, the solo's loudness from its second chorus, intro / tag bars copied from the head,
the bridge's line into its turnaround, where the head's peak sits, the A's range, the solo's last note; round 6: the
solo's density over the head, silent solo bars per chorus and at cadences, phrase lengths / line shape, the form's
level and ending, the climax ladder, the head's register / touch / climb, colour tones on the reharm, the left hand's
bare roots and rests, the frame's held notes).
The playing BREATHES (user on the r6 tunes: "sounds like an endless monotone line of notes") - in balance (blind
round 6): the head breathes at its phrase ends; the solo plays heavy-tailed lines (`soloist.PHRASES`) with a breath
of a beat or two after each (`soloist.BREATH`; a bar at most once a chorus, the last note rings into it, no pickup
filling it), a calmer phrase after a long one (`soloist.CONTRAST`: register and touch), the head's phrases at
their own levels (`perform.phrase_levels` -> `humanize.touch(levels=)`), melody notes voiced at their arrivals rather
than under every note, fills / ornaments rare; `composer.breath(song)` measures it (attacks per bar and their spread,
the time without a new right-hand / any onset for a beat+, rests of half a bar / a bar, phrase lengths, held notes,
left-hand attacks, ornament notes, phrase-to-phrase register / velocity / density contrast;
recipes/jazz-composition.md "Breathing").

**Endless PIANO in general** (`python -m agentsound endless piano --style jazz | new-age | classical | lofi | mix`): the same
composer and plan drive every style - a genre owns its chord VOCABULARY (`Genre.harmony`: blocks with inversions
`V@3` = Eb/G, colours, intro vamps, end chords, tag approaches), its melody (cells, step sizes, phrase plans -
singable periods with a breath at every phrase end, phrase-end kinds), its titles and its ARRANGEMENT:
`new-age-piano` (letters-to-the-morning: pop progressions with tender add9 / maj7 / borrowed-iv colour, the form
`verse` = theme / theme / chorus hook / build in the relative minor, played as intro (left hand alone, then the hook's
head) - A - A' - the hook - an interlude of echoes - the theme with 3rds / 6ths - the build - ONE climax (the hook in
chords, its top note lifted over everything before, a fermata) - the theme soft - a coda, 58-104 BPM, four feels
(gentle / flowing / bright 4/4 and a 3/4 waltz that plays the form doubled, its chords moving bar by bar); a SET
draws per slot, never the slot before's (`plan['set']`, `composer.set_draws`, pinned for the slot's best-of-N): the
layout (song as above / chorus: the hook right after the first theme / return: climax, interlude, the theme's
return), the climax (the theme 8va, the chorus climbing, the lifted hook, a step up) and a register shift of -3..+3
semitones (the climax pitch), the climax part (build or chorus) drawn per tune; each section
draws its arrangement - `perform.ARRANGE_KEYS`: shortened / 9-bar sections, the climax as the lifted hook, the theme an
octave up or a step up with a pivot, a deceptive last return, a walking bass, filled holes, the climax REHARMONIZED
under its melody (harmony `reharm`: substitutes per degree) - so no two pieces share one grid; a hairpin per phrase
(`plan['swell']`) and a drawn touch window per tune (`plan['touch_span']`); best-of-8 replaces seeds the arc check
rejects (`plan['candidate_tries']`); one BLOOM per piece (`plan['bloom']`, HUMAN_FEEDBACK 2026-10-15: the build, the
chorus or the climax pushes the tempo 4-10 % forward and the climax keeps part of it, the left hand opens into 16ths /
triplets over two and a half octaves up to the melody, the right hand weaves the chord under its held notes, and the
hand-to-hand figure - the left hand climbs, the right carries it on into the next melody note, Für Elise's A section -
appears there and now and then elsewhere; `composer.bloom_tells` scores it: tempo_push, climax_tempo, rh_peak_den,
flow32, hand_meet - docs/PIANIST_RULES.md "The bloom"); the new-age blind rounds in `songs/_blind/ROUNDS.md` "New-age", the packets / measures in
`songs/_blind/make_packets_newage.py` / `measure_newage.py`) and
`classical-piano` (a nocturne or a salon waltz: ternary a a' b b' a'' with Neapolitan / diminished / borrowed-iv colour,
the b' the climax with a cadenza flourish into the return; the waltz plays its strains twice, ~3 minutes; chords spelled
by the key - Cb in Gb, the Neapolitan of Eb Fb/Ab) are played by the ROMANTIC pianist (`perform.build_piano`:
`romantic.Score` from the composed notes - touch per phrase, lean on long notes, cantabile, melody rubato -, the inner
notes of its chords softer, a broken-chord LEFT HAND from `pianist.FIGURES` per section (flowing 8ths over a 10th,
rocking, walking 10ths, the nocturne arpeggio, eight 3/4 figures from the oom-pah-pah to an arpeggio over the bar;
held still where the melody breathes), written dynamics per section, phrase rubato, ritardandi, an inhale before the
peak, and the feel's BODY on both hands - new-age lyrical / calm, the nocturne lyrical, the waltz a light sway). The jazz specs moved the same
way (user: "the jazz should be more like that too"): stepwise heads with a rest at every phrase end, a left-hand
figure per section (`lh_plan`: shells -> tenths -> rootless -> walking 10ths / stride, broken chords in a ballad's
intro / tag) and
written section dynamics (`plan['dyn']`, the ballads deepest: loudness range 7.6 -> 11.4 LU over 4 tunes). `--style mix` plays a
set that alternates the styles (`composer.mix_plan`); the gate also checks the BREATH before rendering
(`band['breath']`: the share of time without a new right-hand onset, the density's variation) and tune.json carries
`composer.piano_tells` (hook statements, phrase rests, left-hand figure variety, climax place). Output:
`songs/_endless_piano/out/<style>/NNN-<title>/`.
`lofi-piano` is the same machinery as data: jazzy 7th / 9th loops (ii-V-I, IVmaj7-iii7-vi7, borrowed iv / bVI-bVII,
never a plain triad), 8-bar A / B parts that come back as loops, a sparse hum of a melody (the `lofi` cells: two to
four notes, then space), a lazy swing (the 'lazy' feel's own `groove` 0.57 when `--swing` is not given) or straight
8ths at 68-90 BPM, the left hand's 7th chords held or pushed onto the & of 2 (`pianist.FIGURES` `lofi_*`), on the
`lofi_piano` band; per MOOD the drums (`moods[m]['drums']`: study / late-night / sunday with the drummer's `lofi`
boom-bap loop - in after the intro, out in the bridge and the coda (plan section `drums: False`) -, rain the piano
alone with a little rubato); a mood with drums plays only `steady` feels (no phrase rubato / lilt / inhale: the kit
keeps the grid).
`new-age-epiano` (`python -m agentsound endless new-age-epiano`) is new-age-piano on the 80s DX7 e-piano (ROM1
"E.PIANO 1", `synthwave/epiano` - needs the DX7 banks, `assets/dx7/README.md`): the same composer, plan and score,
the sound swapped through `solo_piano`'s `sounds=` - a stack, so the sustain pedal holds the FM voices; its level
follows the played velocity (velocity fade-in layers) while the timbre stays in the round zone (the tine barks only at
the climax) -, the left hand from G2 (`plan['lh']`: pianist.figure's register), clean pedal lifts (`plan['pedal']`),
no bass-octave climax figures, the 224XL chamber + a plate.

**Endless ORGAN** (`python -m agentsound endless organ`, `endless.organ`): the same composer writes the tune (CELLS
`hymn` quarters and halves, `march` dotted trumpet-tune cells, the singing `song` / `aria` cells; triadic cadential
`ORGAN_HARMONY` with a Picardy third and a plagal Amen) and `endless.organ` sets it per section of the feel's
arrangement (`plan['arrangements']`) in an organ TEXTURE on a REGISTRATION drawn once per verse (`organ.REGISTRATIONS`):
moods `chorale` (a chorale and two variations - principals, a chorale-prelude verse with the cantus on a solo stop,
the full organ re-harmonized with a descant - or a chorale prelude: the ornamented cantus over one motif's
counterpoint), `trio` (three lines on two manuals and the pedal, twice on new stops), `toccata` (16ths in three
figures over the harmony, off-beat or beat chords, the tune in the pedal or a bass line, scale runs into cadences, the
band climbing to a held final chord, the bridge a crescendo in the swell box), `meditation` (a soft solo with
tremulant over held voices, the swell breathing per phrase, planing in the middle, the reprise an octave up) and
`festive` (a trumpet tune over three-note chords and a walking pedal, an echo, the hymn on the full organ with a
descant). Repeats are re-harmonized, a dominant pedal point leads into a return, the coda ends V7 - I. The organist plays it; fermatas at the chorale's phrase ends, the church's ring and
the registrant's pause before a verse on new stops (none where the hand just moves to another manual), the church
blooming into the silences. Best-of-8 by the ORGAN score (`genres.SCORES['organ']` over `organ.organ_metrics`:
parallels, voice-leading leaps, cadence variety, pedal idleness, registration monotony and changes, the ring,
articulation, timing, ornaments, silence) measured on the four songs/pro-organ-* references; the gate's
profile is `organ`. Blind rounds: songs/_blind/ROUNDS.md "Organ".

**Endless ORCHESTRA** (`python -m agentsound endless orchestra-film`, `endless.orchestra`, `bandlib/orchestration.py`;
design and roadmap: docs/ORCHESTRA_ENDLESS.md): the new-age composer writes the tune and the new-age section plan,
then the piece becomes a SCORE of lines with musical functions (`orch.OrchScore` blocks of `orch.Line`s: melody,
counter, harmony, inner, bass, ostinato, colour, pedal, voice, doubling - instrument-independent, the one
representation later composers write into), an ORCHESTRATOR draws a texture per section (`orch.TEXTURES`: string
pad, solo over strings, harp solo, singing violins, cello theme, woodwind chorale, horns over a string ostinato, the
theme with a counter-melody, the tutti / lyrical tutti climax) under `orch.RULES` (ranges and sweet spots by whole
octaves, doublings by register from the placed line, one tutti at the peak, a light coda, colour changes, brass
under a line softer) on the instrument table `orch.ROLE_TRAITS` + `orch.role_table`, and `orch.Score` plays it on the
`film_orchestra` band (one track per section; `endless.orchestra.band`: the `master/film-lyrical` master, a gain and
trims). Moods hopeful / longing / epic / pastoral / night, sizes chamber / full; the decisions are Arrangement
records (kind 'orchestra': size, texture, lead, counter - learn tokens `ASize` `ATex` `ALead` `ACtr`). Best-of-6 by
the ORCHESTRA score (the new-age melodic metrics on a reduction + `orch.orchestration_metrics`, ranges from the four
songs/pro-orch-* references written on the same band); the gate's profile is `classical`. Renders ~0.2-0.5 min
per minute of music. Blind rounds: songs/_blind/ROUNDS.md "Orchestra".

**The quality score and best-of-N**: `composer.score(song, tune)` turns the checkers we have (the blind test's tells,
breath, the body, the lead sheet's melody checks, the arc) into ONE number 0-100 from the notes - no audio, ~1 s - with
its per-metric parts and worst offenders; the rule is a data table per style (`genres.SCORES`: {metric: target range,
weight, hard}; jazz from the pro2 references, new-age from letters-to-the-morning + the three songs/pro-newage-* pieces and its blind rounds' tells - a second set of eight hand-written pieces of other moods / meters / forms measures the ranges, `songs/_blind/measure_newage.py --set2` - classical / lofi provisional), a
broken hard rule (an octave wrap, a verbatim repeat over another chord, a silent cadence bar ...) caps it. The runner
composes and performs `--candidates N` tunes per set slot (default 8; the same mood / feel / key / tempo, other
composition seeds), scores them and renders only the best (the next on a failed audio gate); tune.json carries the
score. Metrics share an immutable note view and leave the song unchanged (see [API](docs/COMPOSE_API.md)).
`python -m agentsound score songs/<slug>` (or an endless tune folder) prints it for any piano piece. It sees
closeness to our references, not the sound or taste: the ears and the blind judges stay the final check (stage 2 of
the roadmap learns the weights from their verdicts - TODO.md).

```bash
python -m agentsound endless piano --style new-age --count 3          # new-age solo piano (letters-to-the-morning)
python -m agentsound endless piano --style classical                  # a nocturne / a salon waltz
python -m agentsound endless piano --style lofi --mood study          # lo-fi: study | late-night | sunday (drums), rain
python -m agentsound endless piano --count 6                          # --style mix: a set alternating the styles
python -m agentsound endless jazz-piano --count 4                     # a set of 4 along the set arc
python -m agentsound endless jazz-piano --count 3 --mood late-night   # late-night | bright | blue | tender
python -m agentsound endless jazz-piano --play                        # endless: plays back-to-back, renders ahead
python -m agentsound endless jazz-piano --hours 1 --join              # an hour + one long mp3 with gaps
python -m agentsound endless organ --count 5                          # church organ: chorale | trio | toccata | meditation | festive
python -m agentsound endless organ --hours 0.5 --join                 # half an hour of organ music + one long mp3
python -m agentsound endless --list                                   # genres, moods, feels, forms
python -m agentsound endless jazz-piano --candidates 1                # no best-of-N: one seed at a time
python -m agentsound score songs/pro2-piano-waltz                     # the quality score + worst offenders
```

Each tune lands in `songs/_endless_<genre>/out/NNN-<title>/` (mix.mp3 tagged with a cover, tune.json with key /
tempo / form / changes / melody / seed / the plan and its measured shape / timing, tune.txt the lead sheet); `songs/_endless_jazz_piano/song.py`
rebuilds any seed with the full image set. In code: `endless.compose(endless.genre('jazz-piano'), seed)` ->
`Tune`, `endless.song(tune)` -> `Song`. Modules: `endless.genres`, `endless.composer`, `endless.perform`,
`endless.arrangement` (the players' per-piece decisions as one record), `endless.run`, `endless.organ`;
docs/COMPOSE_API.md "Endless generators".

### Learned generator (`agentsound/learn`, `python -m agentsound learn`)

A ~32M-parameter decoder-only transformer (plain PyTorch, own tokenizer, no human music data, no pretrained weights)
trained on what the endless generators compose, then improved against `composer.score` - the experiment and every
result are in [docs/LEARNED_GENERATOR.md](docs/LEARNED_GENERATOR.md). It writes at the COMPOSITION level: a token
sequence is an endless `Tune` (header, plan, harmony per part with roman-numeral chords, then the melodies bar by bar)
and `learn.tokens.decode` turns it back into a `Tune` that the existing players perform and the engine renders
(tune -> tokens -> tune is note-identical; `tests/python/test_learn.py`). Token schema 2 adds the players'
arrangement as an `Arr` block: the form (layout), which sections play, the climax treatment, bars / tail / cadence, the left hand per
section, hairpins and the solo's plan. That is the `endless.arrangement` record, which `endless.perform.arrange(tune)`
draws and `perform.build(tune, arrangement=)` plays, bit-identical to the drawn default. Old checkpoints keep
sampling with schema 1. Genre conditioning is a learned embedding
that can be blended (`--genre new-age-piano=0.7,jazz-piano=0.3`). A set is judged as a set: `sample` / `eval` print
its `variety`, which is the spread of mood, feel, form, mode, key, tempo, climax and ending, from 0 (all alike) to 1
(`learn.evaluate.variety`). `--spread` forces each piece's mood, feel, form, meter, key, mode and tempo so that the
set covers the player genre evenly, using only combinations the composer itself draws. With a schema-2 checkpoint
(`runs/top30_2`) it also spreads the arrangement's layout and climax kind, and `variety` counts both. `--header-temp T`
sets a separate temperature for the header and plan tokens. `eval --data FULL TOK` measures against another teacher
export. The schema-2 student reproduces the teacher's arrangement; in blind round 2 both were caught 40 of 40 times
(notebook section 12). `train --init CKPT` warm-starts from an older checkpoint: tokens the data adds get rows from
their related tokens' mean, and a larger `--ctx` (default 1152, 1280 for the widened new-age teacher) copies the last
trained position. In blind round 3 (section 13) the warm-started student fooled the judges 6 of 40 times, the teacher
4 of 40. Only the parent process holds the model on the GPU; the scoring / export worker pools run with
`CUDA_VISIBLE_DEVICES=-1`, and train / eval log the peak reserved GPU memory.
The `D:/...` paths below are the author's machine (a data drive): any folder works. The learn tools' data root is
`$AGENTSOUND_LEARN` (default `D:/agentsound-learn`), and `learn render` finds the main checkout via `$AGENTSOUND_MAIN`.

```bash
python -m agentsound learn export --tokens-only --per-genre 20000 --seed0 4000 --out D:/agentsound-learn/data/tok
python -m agentsound learn export --per-genre 4000 --out D:/agentsound-learn/data/full     # + performed, scored
python -m agentsound learn train --run D:/agentsound-learn/runs/base --data D:/agentsound-learn/data/tok --epochs 5
python -m agentsound learn train --run RUN3 --data TOK3 --init RUN2/ckpt.pt --ctx 1280 --epochs 2 --lr 2e-4  # warm start
python -m agentsound learn eval --run D:/agentsound-learn/runs/base --n 128 --top-p 0.95 --retry 8 --tag p95-retry8
python -m agentsound learn finetune --run RUN --out RUN2        # expert iteration (generate -> score -> keep -> train)
python -m agentsound learn rl --run RUN --out RUN3              # GRPO, reward composer.score, KL to the supervised model
python -m agentsound learn sample --run RUN --genre new-age-piano=0.7,jazz-piano=0.3 --n 16 --out rows.jsonl
python -m agentsound learn sample --run RUN --genre new-age-piano --n 6 --spread --grammar --best-of 8 --out set.jsonl
python -m agentsound learn render --rows rows.jsonl --best 2 --out DIR        # perform + render (the endless gate)
python -m agentsound learn blind --student DIR --teacher DIR --out JUDGES     # anonymized packets for a blind round
```

Torch is imported only by `train` / `sample` / `eval` / `finetune` / `rl` (run them with a CUDA venv's Python); the
tokenizer, the grammar (`learn.grammar`: grammar-constrained decoding), export and the measures are stdlib. Data and
checkpoints stay outside git. Modules: `learn.tokens`, `learn.grammar`, `learn.export`, `learn.data`, `learn.model`,
`learn.train`, `learn.sample`, `learn.evaluate`, `learn.improve`, `learn.rl`, `learn.disc`, `learn.render`.

## 6. The ears: report, images, zoom, compare

`out/report.json` (judged against the profile) + the build's printed digest:

The engine emits `findings[]` with `code`, `metric`, `value`, `limit`, `node`, `section`, `severity` and a
message. Mix, master and endless consume these verdicts; delivery overrides use the same engine evaluator.
Low-end mono requires >5% low-band energy and correlation <0.75; true peak up to 0.1 dB over the ceiling is
info, DC must exceed 0.001, low PLR is info, and profile loudness allows 0.05 LU at either edge.
Streaming retains its +/-1 LU target policy; endless retains exact inclusive genre bounds.
See [audio verdict policies](docs/COMPOSE_API.md#audio-verdict-policies) for boundaries and the engine API.

- **Loudness**: integrated / short-term / per section and per track (LUFS), true peak, LRA, PLR; per-bar levels.
- **Spectrum**: 7 bands and 1/3 octaves vs the profile's reference, tilt, dull / harsh / mud.
- **Stereo and space** (`space`): width above 150 Hz, low-end mono, correlation, reverb / echo returns vs the mix,
  tails at stops, bed vs lead - verdict dry / narrow / lush / washy per section.
- **Masking** between tracks per band, kick / bass alternation, levels and roles per node (`nodes[].role`).
- **Note dynamics** (`nodes[].dynamics`): per-phrase spread of each melodic track's note levels vs its velocities;
  `flat_dynamics` = robotic lead.
- **Realism probes** (`nodes[].realism`, docs/SAMPLE_REALISM_PLAN.md): played vs triggered per pitched track -
  `repeatSim` (same-key repeats: 1.0 = the same recording again, a machine gun; FreePats nylon 1.0, the 7-round-robin
  concert guitar 0.84), `layerStep` (velocity-layer seams on the audition `sweep`), `sustainFlux` (a looped sustain is
  periodic), `tailDecay`, `transitionDip`. Measure on the audition probes (`--notes repeat|sweep|legato|sustain|pedal`)
  and A/B a param with `audition --ab` / `build --set`.
- **Silent notes** (`silent_notes` warnings, `nodes[].silentNotes`): before rendering, `agentsound.silent_notes`
  lists every note that reaches no sample zone (kit without cymbals, a key outside a multisample's or SoundFont preset's range, a velocity
  or keyswitch articulation without zones), no drum-machine piece or only muted stack layers - with GM names / note
  names, bar:beat times and a fix (the same pack's kits that have the piece); after rendering, every track's notes
  that made no audible sound in their own span (40 dB under the track's median note, or a note that adds nothing
  under -60 dBFS; notes under their own sustain, legato lines, vocoder carriers and notes under a closed automation
  lane are not). The `drummer` warns when the kit
  lacks a piece it plays and names the fallback.
- **Pack fallbacks** (`pack_fallback` errors, only with `AGENTSOUND_PACK_FALLBACK=1`; else compile fails): a band
  played a substitute for a missing sample pack (the pack, what played instead, the install command).
- **Clicks**: detected discontinuities with time, bar and the node they come from.
- `warnings` (ranked: what to fix first) and `suggestions` with render-format fixes.

Images (look at them): `overview.png` (index), `loudness.png`, `tracks.png`, `bands.png`, `stereo.png`,
`spectrogram.png` + `spectrogram_NN_<section>.png`, `clicks/click_NN.png`. `zoom songs/<slug> --at 1:23.4 [--stem id]`
inspects any moment. `compare songs/<slug> --ref <audio> [--ref-start --ref-end] [--section]` writes
`out/compare/<ref>/compare.json` + `compare.png`: loudness-matched spectrum difference, width per octave, loudness
distribution, punch, tails, prioritised fixes naming the tracks. References stay outside git (`assets/refrences/`,
`references/`): analysis only, never copied.

### The learned ears (`agentsound.ears`, `python -m agentsound ears`, optional)

```bash
python -m agentsound ears songs/<slug> [--section] [--ref <audio or dir> ...] [--instrument piano]
python -m agentsound ears a.wav some/folder/ --ref refs/ --out result.json   # any audio, a set -> FAD
```

Pretrained audio models as a second opinion, per file (10 s windows spread over it, averaged): Meta **Audiobox
Aesthetics** axes `PQ` production quality, `PC` production complexity, `CE` content enjoyment, `CU` content
usefulness (1..10); **LAION-CLAP music** zero-shot `pReal` = P("a real recording of a <instrument> ...") against
P("a MIDI <instrument> ...") over four prompt pairs (instrument from the song's sampled tracks / their packs, or
`--instrument`); with `--ref`: `refCos` (CLAP embedding cosine to the references) and `fad` (Frechet distance of all
files' CLAP windows vs the references'). `realism` (0..100) = 0.4 PQ + 0.2 CU + 0.4 pReal, each mapped linearly
over its calibrated range (`ears.REALISM`: PQ 6.0..8.5, CU 6.5..8.5, pReal 0.3..0.9). A song writes `out/ears.json`
and an `ears` block into `out/report.json`; `--section` adds one row per section.

**What it can and cannot hear** (calibration, docs/COMPOSE_API.md "The learned ears"): `realism`, `PQ`, `CU` and
`pReal` ranked every degraded copy of a good render lower (one velocity for all notes, 16th grid + one velocity,
bitcrush, telephone band; 8 of 8 on two songs) - it catches damage and mechanical playing. It does NOT tell real recordings
from our renders (our mixes score higher than 6 of 8 paired commercial references), did not prefer the new
Shinyguitar strum over the old FSS one, and does not separate the composed pro piano pieces from the endless new-age
pieces. `refCos` / `fad` measure closeness in style, not quality. Use it to compare versions of the same song (a
drop of ~10 points = something got mechanical or damaged), never as a gate or across genres; `pReal` depends on the
instrument noun (the same piano render: 0.77 as "piano", 0.60 as "music"), so compare runs with the same one; `CE` /
`PC` are reported but not in the score (content and density, not realism).

**Install** (once; everything on a drive with ~8 GB free - nothing here touches the main Python):
`D:/venvs/...` is the author's data drive - put the venv anywhere and point `$AGENTSOUND_EARS_PYTHON` at its python
(the default looks in `D:/venvs/agentsound-ears`).

```bash
py -3.12 -m venv D:/venvs/agentsound-ears
mkdir -p D:/venvs/cache                    # the worker puts HF_HOME / TORCH_HOME / TMP under <venv parent>/cache
export PIP_CACHE_DIR=D:/venvs/cache/pip TMP=D:/venvs/cache/tmp TEMP=D:/venvs/cache/tmp
D:/venvs/agentsound-ears/Scripts/python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126
D:/venvs/agentsound-ears/Scripts/python -m pip install audiobox_aesthetics fadtk --extra-index-url https://download.pytorch.org/whl/cu126
```

The first run downloads the weights from Hugging Face: `facebook/audiobox-aesthetics` (CC-BY-4.0, 0.4 GB) and
`lukewys/laion_clap` `music_audioset_epoch_15_esc_90.14.pt` (CC0-1.0, 2.2 GB; the LAION-AI/CLAP release - the
transformers port `laion/larger_clap_music` returns near-equal zero-shot scores and is not used), plus the
`roberta-base` / `bert-base-uncased` / `bart-base` tokenizers `laion_clap` loads. Weights stay in the cache, never in
the repo. Another location: set `AGENTSOUND_EARS_PYTHON` to the venv's python (and `AGENTSOUND_EARS_CACHE` for the
caches). Without the venv the command prints these steps and exits 3; nothing else depends on it. ~30 s per song on
a 16 GB GPU after the models are cached (CPU works, slower).

## 7. Production tools and the roles

- **Mixer** (`agentsound.mixer`, `python -m agentsound mix`): roles (lead, bed, rhythm, low, other), genre targets
  vs the lead per profile, `plan()` / `check()` (findings with MIX snippets) / `auto()` (render -> measure -> adjust,
  bounded and logged). The result is a module-level `MIX = {'trim', 'ride', 'duck', 'eq', 'lead', 'arc', 'ramp'}` in song.py
  (`lead`: who carries the tune per section).
- **Mastering** (`agentsound.mastering`, `python -m agentsound master`): `match()` a reference or the profile (tonal
  eq within a profile guard, loudness, width, limiter), platforms `auto` / `streaming` / `loud` / `dynamic`,
  `--render` post-pass with do-no-harm back-off, `check()` delivery targets (true peak, loudness, LRA, mono, tone),
  `apply()` / `plan.snippet()` into the song's master chain.
- **Roles** ([docs/ROLES.md](docs/ROLES.md)): tool-agnostic briefs, one agent can wear every hat or each is one
  agent's brief. Pipeline and what each writes in `songs/<slug>/`:

| role | brief | writes |
|---|---|---|
| producer | [roles/producer.md](roles/producer.md) | `BRIEF.md` (brief + log), METADATA / COVER, delivery |
| arranger | [roles/arranger.md](roles/arranger.md) | `ARRANGEMENT.md`, sections + parts via the players |
| lyricist | [roles/lyricist.md](roles/lyricist.md) | a sung vocal's words: `LYRICS.md`, the `lyrics=` of `singer.sing` |
| sound designer | [roles/sound-designer.md](roles/sound-designer.md) | sounds, layers, heroes, chains, `SOUND.md` |
| mix engineer | [roles/mix-engineer.md](roles/mix-engineer.md) | `MIX` in song.py, `MIX.md` |
| mastering engineer | [roles/mastering-engineer.md](roles/mastering-engineer.md) | master chain, `out/master/`, `MASTER.md` |
| A&R | [roles/a-and-r.md](roles/a-and-r.md) | `AR.md`: `ship` or `revise` with ranked issues per owner |
| film director | [roles/film-director.md](roles/film-director.md) | `film.py` + `out/making-of.mp4`: the song's making-of, made to measure |

### The making-of film (`agentsound/makingof`, `python -m agentsound makingof songs/<slug>`)

A documentary of how a song was made, generated from its own files and logs, then the song itself visualized
(1920x1080, 30 fps, H.264 + AAC, `songs/<slug>/out/making-of.mp4`). Songs are not all the same, so the film is
**code per song**: `songs/<slug>/film.py` composes reusable chapters for THAT song's story (`--draft` writes a first
draft from the facts; the brief is [roles/film-director.md](roles/film-director.md)). Every text and number comes
from the song's files: the wish and the log (`BRIEF.md`), the form, keys, tempi and the hook with every place it
returns (the render JSON), the sounds and why (`SOUND.md`), the players' moves on their exact beats (their move logs,
recorded while `song.py` builds), the A&R issues and the revision's before -> after numbers (`AR.md`), the mix and
master (`MIX.md`, `MASTER.md`, `report.json`) and the credits.

- **Chapters** (`from agentsound.makingof.film import Film, N, AR, Item, Excerpt, Episode`): `cold_open` (the wish
  typed as chat bubbles, the title card), `team`, `blueprint` (form, tempo, energy per bar, the hook drawn as notes),
  `act` (a part of the song under its own scene), `tracks` (each part soloed from its stem - rendered once with
  `build --stems` - then the band back in), `performance` (track lanes, the players' moves popping on their frames),
  `crisis` (the A&R stamp and ranked issues), `tried` (before / after: the judged build from git, re-rendered once
  with today's engine, against today, the same bars, loudness-matched, the measured change), `song` (the whole
  song), `credits` (CC-BY attributions, the narration's licence).
- **Looks**: audio-reactive WebGL scenes per section (`Film.look`): `nebula`, `ink` (smoke and a candle), `ring`
  (a spectrum ring round the cover), `grid` (synthwave horizon), `mandala`, `scope` (vectorscope ribbons) and the 3D
  note highway (`+hw`), crossfaded on section boundaries; bloom, chromatic aberration, grain, the palette from the
  cover, the colour temperature following the energy arc. Features per frame (log bands, loudness, onsets, width,
  L/R samples) are analysed once and cached.
- **Narration** (English, captions always): Breeze TTS 2 (local, WSL + GPU; research / non-commercial licence, named
  in the credits) with a frozen voice per role (narrator, A&R) and a delivery direction per line, raw chunks cached,
  one loudness gain per speaker (median to -18 LUFS, peak ceiling -1.5 dBFS), ducking the music under it; `--tts sapi`
  uses the Windows voices, `none` captions only. Breeze location: `$AGENTSOUND_BREEZE_DIR` (WSL path,
  default `~/services/breeze-tts` in the WSL user's home).
- **Renderer**: headless Chrome (WebGL2 + Canvas 2D, `agentsound/makingof/web/`) draws each frame as a pure
  function of its index, N tabs in parallel, piped into ffmpeg (NVENC when available, else libx264); the soundtrack
  (song segments, stems, before / after clips, narration) is mixed by ffmpeg. Requirements: Node >= 22, Chrome or
  Edge (`$AGENTSOUND_CHROME`), ffmpeg; `--gpu high` asks for the discrete GPU. Stills for review: `--stills 12,40,95`.

### Études (benchmarks that find the system's weaknesses)

A public-domain score played note-for-note (e.g. `songs/gymnopedie-etude`: Satie, Gymnopédie No. 1), checked bar by bar
against a user-provided reference recording by analysis only, then measured with `compare` (tempo curve, rubato,
note dynamics, decay, brightness) - every gap becomes a library fix or a written open gap (method: `recipes/classical.md`,
"Études"). The Gymnopédie added `Song.lilt()` (beat-level timing in the tempo map), the rubato shape `'breath'`, the
`piano` analysis profile (solo piano), sampler `sympathetic` string resonance and half pedal, and `sampled/recital_grand`.

## 8. Feedback, system work, delivery

- **Human feedback**: [recipes/HUMAN_FEEDBACK.md](recipes/HUMAN_FEEDBACK.md) collects what the user said after
  listening and the rule it implies (newest first). Read it before every song; append every new reaction (date,
  song, words, rule).
- **System work** (patches, presets, players, analysis) is validated on ONE reference song in a scratch copy, never by
  re-running all songs; roles never touch other songs.
- **Delivery**: `build` writes `out/mix.mp3` tagged (title, artist, album, genre, year, BPM, key, credits, embedded
  cover), `out/cover.png` (engine cover styles synthwave outrun dreamwave darksynth jazz classical rock pop, or your
  own picture), `out/credits.txt` and, for a sung song, `out/lyrics.txt` (the words by section). Set `METADATA = {...}`
  / `COVER = {...}` in song.py. Hand over absolute paths of mp3 / wav / cover (+ the lyrics) with a short description
  and the credits that matter.

Also user-facing: `delivery` (mp3 tags, cover, credits.txt, the CC-BY / BY-SA / BY-NC attribution check) and `library`
(the sample-pack manager behind `python -m agentsound samples`: manifest, fetch, SOURCE.json / INDEX.json).

## 9. Repo layout and where to add things

The players share `patterns.weighted_choice` for seeded table choices ([API](docs/COMPOSE_API.md#patterns-all-return-a-clip)).

```
agentsound/            Python compose layer (stdlib only)
  song.py theory.py voicing.py figures.py patterns.py midifx.py humanize.py automation.py modulation.py vamod.py tempo.py
  articulation.py pianist.py romantic.py drummer.py bassist.py guitarist.py jazz.py heroes.py
  gesture.py budget.py fretwork.py soloist.py guitar_vocab.py guitar_riff.py horn_vocab.py   lanes, budgets, solos, riffs
  makingof/            the making-of film (facts, players' logs, narration, timeline, web/ renderer)
  endless/ learn/      the endless rule generators; the learned generator (torch only for its train / sample commands)
  sfz.py kits.py organ.py speech.py            sample importers, TTS
  singer.py lyrics.py voicebank.py voicebank_runner/   the sung vocal (the runner runs in WSL: onnxruntime)
  patches/             the sound library (one module per family, registered lazily)
  bands.py bandlib/    band presets (one file per genre family)
  mixer.py mastering.py compare.py delivery.py library.py catalog.py cli.py
engine/                C++ engine (see section 2)
web/                   Endless browser app, workers, license notices and pinned runtime manifest (web/README.md)
tools/wasm/            portable WASM build, browser adapter, runtime restore and site staging tools
docs/ roles/ recipes/  references, role briefs, genre guides
songs/<slug>/song.py   one song each (_template, _demo_*, _bands/<preset> are system songs); out/ is git-ignored
assets/                dx7/ (ROM cartridges: not bundled, see its README), soundfonts/ (GeneralUser GS), samples/manifest.json,
                       voices/manifest.json (the singing voicebanks: not bundled)
tests/                 C++ tests (test_*.cpp, ctest) and tests/python (unittest)
```

Python helper modules (`catalog.HELPER_MODULES`, listed with every public function by `catalog helpers`): `theory`,
`patterns`, `humanize`, `automation`, `modulation`, `midifx`, `vamod`, `jazz`, `pianist`, `romantic`, `drummer`, `bassist`,
`guitarist`, `sfz`, `kits`, `organ`, `articulation`, `speech`, `tempo`, `song`, `sections`, `mixer`, `mastering`, `heroes`,
`gesture`, `fretwork`, `soloist`, `guitar_vocab`, `guitar_riff`, `horn_vocab`, `budget`, `voicing`, `notation`, `figures`,
`bandlib.scoring` (the orchestrator's desk, used as `orch.Score` / `orch.Choir` ...), `bandlib.ensemble` (the
orchestra's performance rules), `expressive` (the KTH rules every player shares), `singer`, `lyrics`, `voicebank`.

| to add | do |
|---|---|
| an engine instrument / effect | implement `Instrument` / `Effect` (`engine/core/Module.h`), a `ParamSpec` with `help` per param, register in `engine/render/Registry.cpp`, `tests/test_<name>.cpp`, a line in `catalog.MODULES`, regenerate `docs/PARAMS.md`, list it in this README |
| a patch | a module in `agentsound/patches/` (registered on import), levelled to -18 LUFS on its audition phrase (sampled sets: per-zone evening via `patches/_levelling.py`); tests in `tests/python/test_patches.py` / `test_sampled_*.py` |
| a sample pack | an entry in `assets/samples/manifest.json` (url, license, attribution, category, genres) |
| a band preset | a builder in `agentsound/bandlib/<genre>.py`, a demo in `songs/_bands/<name>`, tuned against a reference |
| a player / move | a module like `pianist.py` (moves + arrange + budgets + Memory), add it to `catalog.HELPER_MODULES`, document it in COMPOSE_API and here |
| a hero preset | `heroes.define(...)` in `agentsound/patches/hero_*.py`, calibrated (level, velocity response), `tests/python/test_hero*.py` |
| a role | `roles/<role>.md` with the header block (Role, When to use, Inputs, Deliverable), a row in `docs/ROLES.md` and here |
| an analysis profile | `engine/analysis/Profiles.cpp`, `cli.ANALYSIS_PROFILES`, a mixer profile, RENDER_FORMAT tables, here |

**Keep this file current**: update it in the same commit as any user-facing change. `tests/python/test_readme.py`
fails when an engine module, helper module, band preset, role, analysis profile, CLI command, recipe, patch family
or hero preset is not mentioned here.

Browser/WASM: `python tools/wasm/runtime.py` restores the checksum-pinned runtime assets into `web/` (ignored binaries); `python -m http.server 8778 --directory web` serves the app. See [web/README.md](web/README.md) and [tools/wasm/README.md](tools/wasm/README.md). The existing p11 browser release is preserved independently of current native generator development.

Sampler playback repairs isolated sample glitches and broken loop seams at load time. `Song.lead_hint` identifies melody tracks per section for note-dynamics analysis; see `docs/RENDER_FORMAT.md`.
