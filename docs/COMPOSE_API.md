# AgentSound compose API

Songs are Python files (stdlib only) that build a `Song`; `song.compile()` turns it into the flat,
validated render JSON of [RENDER_FORMAT.md](RENDER_FORMAT.md) and the engine renders it.

```
python -m agentsound new neon-arcade                  # songs/neon-arcade/song.py from songs/_template
python -m agentsound check songs/neon-arcade          # compile + validate (the engine's strict check too, if built), no render
python -m agentsound build songs/neon-arcade          # render -> out/mix.wav, mix.mp3, report.json, pngs
python -m agentsound build songs/neon-arcade --section chorus     # just one section (out/sections/chorus/)
python -m agentsound build ... --from-beat 64 --to-beat 96 --stems --no-mp3
python -m agentsound patches [prefix] [-v]            # sound library
python -m agentsound audition synthwave/lead [--notes chord|phrase|bass|drums|arp]
python -m agentsound params [va|dx7|drums|reverb|...] # every engine parameter: range, default, unit, help
python -m agentsound dx7 [search]                     # DX7 ROM voice names
python -m agentsound sf2 [search] [--samples]         # SoundFont presets (bank:program) / raw samples
python -m agentsound voices                           # Windows text-to-speech voices (for the vocoder)
python -m agentsound speak "neon lights" --out x.wav [--voice zira] [--rate -2] [--ssml]
python -m agentsound master songs/neon-arcade [--ref ref.opus] [--platform streaming] [--render] [--check]   # mastering
```

`song.py` defines `build() -> Song` (or a module-level `song`). Engine: `--engine PATH`, else
`$AGENTSOUND_ENGINE`, else `build/agentsound.exe`. Exit codes: 0 ok, 1 song error, 2 engine rejected the
JSON, 3 engine missing, 4 engine failure. After a render the CLI prints the report digest: loudness
(target -14..-9 LUFS-I, true peak <= -1 dBTP), per-section and per-track levels, warnings, suggestions.

## Conventions

* **Time is in beats** (quarter notes), as floats. Note values are accepted wherever a length is:
  `'1/16'` = 0.25, `'1/8t'` = triplet, `'1/8.'` = dotted. A bare number is always beats (`'4'` = 4 beats).
* **Progression chord lengths are in bars** (the only exception). A bar is the meter's: 4/4 = 4 beats, 3/4 = 3,
  6/8 = 3 (beats stay quarter notes; see Tempo and meter).
* **Positions** are beats or Sections (= their start). `sec.bar(n)` is 0-based (`bar(0)` = first bar,
  `bar(-1)` = last bar, `bar(sec.bars)` = the end), `sec.beat(-2)` = 2 beats before the section end.
* **Pitches**: MIDI ints or names, `C4` = 60, `'C#4'` = 61, `'Bb2'` = 46; drum names (`'kick'`) where drums fit.
* **Scale degrees are 1-based** (1 = tonic, 8 = octave up, -1 = the scale note below the tonic); they count the
  key's own scale, so in a pentatonic key degree 6 is the octave.
* **Velocity** 1..127 (100 = normal). Every random process is seeded (song seed, or explicit `seed=`).
* Everything is immutable-by-copy (clips, motifs, patches); tracks/buses/songs are the mutable builders
  and their methods return `self` for chaining. Mistakes raise `ComposeError` with the reason, the
  fix, and for note placement the song line that placed the note.

## Complete example

```python
from agentsound import *


def build() -> Song:
    s = Song('Neon Arcade', tempo=108, key='F# minor', seed=4)
    intro = s.section('intro', bars=8)
    verse = s.section('verse', bars=16)
    lift = s.section('build', bars=4)
    chorus = s.section('chorus', bars=16)
    outro = s.section('outro', bars=8)

    prog = s.prog('i VI III VII')                               # F#m D A E, one bar each
    climb = s.prog('iv:2 V7sus4 V7')                            # 4 bars of tension into the chorus
    hook = s.motif('1:1/4 3:1/4 5:1/4 8:1/4 | 7:1/2 5:1/2 | 6:1/4 5:1/4 3:1/4 2:1/4 | 1:4')
    beat = drums({'kick': 'x...x...x...x...', 'snare': '....X.......X...',
                  'hat': 'x.x.x.x.x.x.x.xo', 'ohh': '..............x.'})

    hall, gate, echo = s.hall(decay=3.5), s.gated(), s.echo(time=0.75, feedback=0.35)
    kit = s.track('drums', inst.drums(kit='synthwave'), sends={gate: -12}).groove('laidback')
    bass = s.track('bass', inst.va(osc1__wave='saw', sub__level=0.6, cutoff=600, amp__release=0.06))
    pad = s.track('pad', inst.va(unison=6, cutoff=1800, amp__attack=0.7, amp__release=2.0),
                  fx=[fx.chorus(mix=0.4)], gain_db=-7, sends={hall: -6})
    arps = s.track('arp', inst.va(osc1__wave='square', amp__sustain=0, amp__decay=0.2),
                   gain_db=-8, pan=-0.3, sends={echo: -9})
    lead = s.track('lead', inst.va(unison=3, mode='legato', glide=0.04,
                                   mods=[vamod.lfo('sine', hz=5.5, delay=0.3, fade=0.3) >> ('pitch', 15)]),
                   gain_db=-4, sends={hall: -10, echo: -14}).humanize(timing_ms=3, vel=6)

    pad.loop(prog.block(register=('F3', 'F5')), intro, verse, chorus, outro)
    pad.play(climb.block(register=('F3', 'F5')), lift)
    kit.loop(beat, verse, chorus).play(snare_roll(4, build=True), lift.bar(-1)).play(crash(), chorus)
    bass.loop(prog.bass('octave', rate='1/8'), verse).play(climb.bass('pulse'), lift)
    bass.loop(prog.bass('octave', rate='1/16'), chorus)
    riff = prog.arp('updown', rate='1/16', octaves=2, register=('F#3', 'F#4'))
    arps.loop(riff, verse.bar(8), bars=8).loop(riff, chorus).play(climb.arp('up', octaves=2), lift)
    lead.loop(hook.clip(octave=5), chorus).play(hook.sequence(0, -2).clip(octave=4, vel=80), outro)

    s.sidechain(pad, bass, arps, key=kit, pitches='kick', depth=10, release=200)
    pad.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 400, 1800),
                 riser(chorus.start, lift.length, 1800, 6000), exp_ramp(outro.start, outro.end, 6000, 300))
    s.master.add(fx.limiter(gain=6))
    return s
```

With a sound library installed, replace raw instruments by patches: `s.track('lead', 'synthwave/supersaw_lead')`
or `patches.get('synthwave/supersaw_lead').but(cutoff=2500)`.

## Song

| call | does |
|---|---|
| `Song(title, tempo=120, key='C major', seed=1, time_sig='4/4', sample_rate=48000, tail=4.0, meter=None)` | tempo 30..300 (the tempo the song starts with), sample rate 44100/48000/96000, tail = seconds rendered after the end; `meter=(3, 4)` = `time_sig`, the default meter |
| `s.section(name, bars, meter=None)` -> `Section` | appended after the previous section; names unique; sections are the report markers; `meter=(3, 4)` / `'6/8'` gives it its own meter |
| `s['verse']`, `s.sections`, `s.length` (beats), `s.bar(n)`, `s.seconds(beat)` | lookup / time helpers (bars across meter changes, seconds through the tempo map) |
| `s.set_tempo`, `s.tempo_ramp`, `s.ritardando`, `s.accelerando`, `s.fermata`, `s.rubato`, `s.lilt`, `s.tempo_at` | a moving tempo, see Tempo and meter |
| `s.track(id, sound, *, fx=(), gain_db=0, pan=None, output='master', sends=None, mute=False)` | ids match `[a-z0-9_-]+` |
| `s.bus(id, fx=(), *, gain_db=0, pan=None, output='master', sends=None)` | group or return bus; `fx` may be a chain patch |
| `s.hall(**p)`, `s.plate(**p)`, `s.echo(**p)`, `s.gated(**p)` | 100 % wet return buses (patches `bus/hall` etc. if the library has them); params go to the chain's reverb/delay/gatedreverb. A second call returns the same bus (with params it is an error) |
| `s.gated(..., key=kit, pitches='snare')` | keyed gate: only those notes of the key track open the gatedreverb (muted ghost key track `<key>-key`, as for `sidechain`); `key=` alone keys from the whole track/bus; a later `s.gated(key=...)` keys an existing bus. See the gated-snare recipe under Production moves |
| `s.sidechain(*targets, key, pitches=None, **ducker_params)` | pump targets from `key`; `pitches='kick'` keys only from those notes via a muted ghost track `<key>-key` (it shows as a silent node in the report) |
| `s.carve(*targets, key, freq=2500, q=0.7, depth=4, **compressor_params)` | carve room for a lead: a keyed dynamic EQ on every target (a band-mode `compressor`: `band`, `bandq`, `range`) dips its `freq` band by up to `depth` dB while the key (the lead) plays and gives it back in the lead's gaps - the bed keeps its level and body, only the lead's presence band steps aside (`node.carve(key, ...)` for one node). Hero leads: `s.carve(strings, pad, piano, keys, key=sax, depth=4)` |
| `s.master.add(fx...)`, `s.master.use('master/...')`, `s.master.gain_db`, `s.master.automate(...)` | master chain |
| `s.prog(spec, bars=1)`, `s.motif(spec, dur=0.5)` | progression / motif in the song key and meter |
| `s.export(stems=True, bit_depth=24)` | render options (CLI `--stems` also works) |
| `s.compile()` -> dict, `s.save(path)`, `s.describe()`, `s.warnings` | validation: unique ids, routing targets exist, no cycles (outputs, sends and sidechains), notes inside the song, automation targets resolvable and strictly increasing; **silent notes** (`agentsound.silent_notes`): every note of a sampler / kit / sfz / stack / drum-machine track that reaches no sample zone (a kit without that piece, a key outside the multisample's range, a velocity or keyswitch articulation without zones), no drum piece or only muted stack layers is a "silent notes: ..." warning (GM names / note names, bar:beat, the fix) and goes to the render JSON's `analysis.silentNotes` (the report's `silent_notes` warnings, next to what the render measured: docs/RENDER_FORMAT.md "Silent notes") |

`sound` for a track: a `Patch`, a patch name, `inst.va(...)`/`inst.dx7('E.PIANO 1')`/`inst.drums(kit='linn')`
or `{'type': ..., 'params': {...}}`. Patch fx come first, then `fx=`; `gain_db` adds to the patch level; `pan=None`
keeps the patch pan; sends merge (patch sends to buses that don't exist are dropped with a warning).

**Section**: `.name .start .end .length .bars .span .meter .beats_per_bar`, `.bar(n, beat=0)`, `.beat(b)`, `.bar_starts(every=1)`, `beat in sec`.

**Track** (all return the track):

| method | |
|---|---|
| `play(what, at=0, *, times=1, transpose=0, vel=1.0, replace=False)` | place a Clip / Progression (block chords) / Motif / Chord; `replace=True` first removes this track's notes in that span (fills) |
| `loop(what, *sections, bars=None, until=None, ...)` | repeat to fill each section, or from a position for `bars` / `until` a beat or section; cut at the end |
| `note(pitch, at, dur=1, vel=100)`, `clear(start, end=None, pitches=None)` | single note / remove notes |
| `groove(name_or_Groove)`, `humanize(timing_ms=4, vel=6, seed=None)` | applied at compile with the local song tempo (ms stay ms in a ritardando); drum tracks get per-drum offsets |
| `automate(target, *point_lists)`, `send(bus, db)`, `to(bus)`, `add_fx(*fx, first=False)`, `duck(key=None, pitches=None, **p)` | also on buses (and `automate`/`add_fx` on the master) |
| `modulate(target, *modulators, window=None)` | LFOs, step sequences, trance gates, followers, per-note envelopes, random steps driving a parameter (see Modulation); on tracks, buses and the master |
| `.notes`, `.clip(start, end)` | inspect / copy a placed part |

## Tempo and meter

Beats are always quarter notes. `Song(tempo=...)` is the tempo the song starts with; these calls make it move
(the render JSON then carries an exact `"tempoMap"`, docs/RENDER_FORMAT.md). Positions are beats or Sections,
spans a Section or `(start, end)`:

```python
s.rubato(verse, depth=0.04, phrase='arch')                      # the phrase breathes (ballads, classical)
s.lilt(verse, beats={2: 0.06}, jitter=0.03)                     # the pulse inside each bar breathes (beat 2 lingers)
s.ritardando((end.bar(-2), end.bar(-1)), to=0.7, a_tempo=False)  # slow into the last bar ...
s.fermata(end.bar(-1), hold=3)                                  # ... whose chord rings 3 beats longer
s.set_tempo(bridge, 84)                                         # a new tempo from the bridge on
s.accelerando(build, to=1.1)                                    # push into the chorus (keeps the new tempo)
```

| call | does |
|---|---|
| `s.set_tempo(at, bpm)` | the tempo is `bpm` from `at` on (until the next change); 10..600 BPM (`set_tempo(0, 20)` alone gives a one-point `"tempoMap"`, as `"tempo"` is 30..300) |
| `s.tempo_ramp(start, end, to_bpm, curve='linear')` | from the tempo at `start` to `to_bpm` at `end`, kept afterwards; `'smooth'` eases in and out |
| `s.ritardando(span, to=0.8, bpm=None, curve='smooth', a_tempo=True)` | slow down across the span to `to` x the tempo there (or to `bpm`); `a_tempo=True` returns to the old tempo at the span end (rit. ... a tempo) - after the held chord when a `fermata` sits on the span end, never when no note starts after the chord there (a final chord stays slow); a ramp starting right at the span end continues from the slowed tempo, a `set_tempo` there wins. `False` always stays slow |
| `s.accelerando(span, to=1.15, bpm=None, curve='smooth', a_tempo=False)` | speed up; keeps the new tempo unless `a_tempo=True` (then as for ritardando) |
| `s.fermata(at, hold=1.5, seconds=None, length=None)` | the chord at `at` rings `hold` extra beats (at the tempo there) or `seconds` longer, then the music goes on. The stretched span runs to the next note onset after the chord (notes within 1/4 beat of `at` - strums, rolls - belong to the chord), else to the end of the chord - but never into the next fermata while nothing after the chord is placed yet (a song that asks `tempo_at` while writing its parts); `length=` sets it exactly. Everything inside waits (arpeggios under a fermata slow down too: end them on the chord) |
| `s.rubato(span, depth=0.04, phrase='arch', seed=None)` | phrase-shaped breathing of +-depth around the tempo: `'arch'` moves forward into the phrase and broadens towards its end, `'wave'` breathes twice, `'lean'` holds back then moves on, `'breath'` moves on through the first 60 % and broadens into the last 40 % (a sung phrase: the reference recording of the Gymnopedie etude read phrase middles +2.5 %, last bars -3.5 %), `'free'` only wanders; plus a seeded smooth irregularity. The span keeps its length (time taken is given back) and joins the tempo around it without a jump |
| `s.lilt(span, beats={2: 0.06}, jitter=0.0, seed=None)` | beat-level agogics in every whole bar of the span: inner beat k arrives `beats[k]` beats late (negative: early), plus a seeded random `jitter` (standard deviation in beats) per beat; the downbeats stay on the tempo map (each bar gives its time back). The whole tempo moves - both hands, every track together - where `humanize` moves single notes apart. A slow 3/4 whose chord on 2 lingers: `{2: 0.06}` (a concert recording of Satie's Gymnopedie No. 1: +0.066 beats, +-0.08 / +-0.14 on beats 2 / 3); a Viennese waltz: `{2: -0.08}`; a pianist's unmetronomic pulse: `jitter=0.02-0.05`. Stacks with rubato, ramps and fermatas; delays within +-0.3 beats |
| `s.tempo_at(beat)`, `s.seconds(beat)`, `s.tempo_map()`, `s.tempo_points()` | the BPM at a beat, the song time of a beat (exactly as the engine renders it), the map, the render JSON points |

Ramps (tempo_ramp / ritardando / accelerando) may not overlap each other or contain a `set_tempo` (end one where
the next starts); fermatas, rubato spans and lilt spans may not overlap their own kind. A rubato or fermata may sit on a ramp (they scale
it). Everything follows the map: humanize / groove milliseconds (the local tempo), tempo-synced effects (delay
echoes stay on the moving beat grid through ramps and change their time at once, crossfaded, at a tempo jump -
`set_tempo`, a fermata, a tempo - so they never warp in pitch; reverb `predelaybeats` the same, tremolo / phaser `sync`, ducker `mode='tempo'`, va
`rateBeats` LFOs), track modulators (`rate='1/4'` stays a quarter note; `'5hz'` stays 5 Hz), the report (section
times, bars, `bpm` per section) and `zoom --beat`. Strums in a slow passage: `clip.strum(ms=30, bpm=s.tempo_at(beat))`.

**Meter**: `Song(..., meter=(3, 4))` (= `time_sig`) sets the default; `s.section(name, bars, meter=(6, 8))`
gives a section its own. Bars count in the section's meter: 3/4 = 3 beats, 6/8 = 3 (two dotted quarters), 7/8 =
3.5, 12/8 = 6. Every bar helper follows it: `sec.bar(n)`, `sec.bar_starts()`, `sec.length`, `s.bar(n)` (song bars
across meter changes), `s.bars_after(start, bars)`, `track.loop(..., bars=N)` (each bar in the meter where it
falls), `s.meter_at(beat)`, `s.meter_grid()`, `s.prog(spec, meter=sec.meter)` (chord lengths in that meter's
bars) and modulator rates in bars (`'1 bar'` = the meter at the window start). Drum grids: one bar per pattern -
12 sixteenths for 3/4 (`drums({'kick': 'x...........'}, step='1/16')`), 6 eighths for 6/8 (`step='1/8'`), or
`drums(..., bars=1, beats_per_bar=sec.beats_per_bar)`. The render JSON's `"meter"` comes from the sections (a
section that starts inside a bar of the meter before it gets a short bar first) and numbers the report's bars.

## Sounds: instruments, effects, patches

```python
inst.va(cutoff=1800, unison=5, osc1__wave='saw')   # '__' in a keyword becomes '.': osc1.wave
inst.dx7('E.PIANO 1')                               # DX7 ROM voice by name (install the ROMs: assets/dx7/README.md)
inst.drums(kit='synthwave')                         # GM map: 36 kick 38 snare 39 clap 42 hat 46 open hat ...
inst.sf2('Grand Piano')                             # SoundFont preset (GeneralUser GS: full GM/GS set), see Samples
inst.sampler(dir='samples/909', oneshot='on')       # WAV sampler (folders, zones, loops), see Samples
fx.reverb(type='plate', mix=0.25)                   # any engine fx type: eq filter compressor ducker saturator
fx.filter(name='sweep', cutoff=18000)               #   delay reverb gatedreverb tremolo vowel ensemble wah amp
fx.filter(name='sweep', cutoff=18000)               #   delay reverb gatedreverb tremolo vowel ensemble wah
fx.shimmer(mix=0.3, decay=8)                        #   premium: microshift shimmer tape exciter dimension
fx.vocoder(bands=20, sidechain='voice')             #   robot voice (needs its modulator), see Vocoder and speech
fx.convolver(ir='samples/<pack>/Hall.wav')          # impulse response (IR WAV): patches bus/ir_* (returns), cab/* (DI guitar)
fx('eq', {'low.gain': 2, 'high.gain': 1.5})         # dict form for any param name
```

The Python layer passes params through; the engine validates them strictly (`python -m agentsound params va`).
`sidechain` and `name` are the only reserved FX keywords (`name` labels an effect for automation).
The va's `mods` param is the one structured param: a list of modulation routes (see VA modulation matrix).

**Patch**(`name, instrument=None, fx=(), gain_db=0, pan=0, sends=None, notes=''`): a named sound. Copies:
`.but(**params)` (instrument params; on fx-only patches the first effect), `.but_fx(index|type|name, **params)` (one
insert effect: `patches.get('bus/hall').but_fx('reverb', decay=4)`), `.with_fx(*fx, first=False, replace=False)`,
`.with_mix(gain_db=, pan=, sends={'hall': None})`, `.named(name)`, `.with_mods(*routes, replace=False)` (va
modulation routes; a route with an existing id replaces it). Fx-only patches (`instrument=None`) are
bus/master chains (`bus/...`, `master/...`). Registry: `patches.register(p, replace=False)`, `patches.get(name)`
(a copy, with did-you-mean errors), `patches.has`, `patches.list(prefix)`, `patches.describe(name)`.
The library is every module in `agentsound/patches/`, imported lazily on first use.

### Layered instruments (`inst.stack`, `layer`, `Patch.layered`)

One track, several instruments playing the same notes: a hook piano with a DX glass layer an octave up and a pad
swelling in under long notes, a piano attack over a sustaining supersaw, a velocity-crossfaded e-piano -> grand, violins
doubled by cellos an octave down. Each layer does one job (attack, body, sparkle, swell); the engine's `stack`
instrument sums them exactly like separate tracks would (docs/RENDER_FORMAT.md "Stack").

```python
lead = s.track('lead', 'layered/piano_glass_lead')            # the library: python -m agentsound patches layered/
lead = s.track('lead', inst.stack(
    layer('sampled/piano_lead', 'piano'),                        # a patch: its instrument + its fx chain
    layer('synthwave/arp_glass', 'glass', transpose=12, level=-10, bend=False),
    layer(inst.va(cutoff=1500, unison=5), 'pad', level=-14, delay=60, pedal=False, fx=[fx.chorus(mix=0.4)])),
    sends={'hall': -14})
keys = s.track('keys', inst.stack(layer('sampled/rhodes', vel=(1, 95), velfade=35),        # soft: Rhodes
                                  layer('sampled/grand_piano', vel=(60, 127), velfade=35)))  # hard: grand
bass = s.track('bass', inst.stack(layer('synthwave/moog_bass', fx=[fx.eq({'hp.freq': 90})]),
                                  layer('synthwave/sub_bass', 'sub', cutoff=120, keys=('C0', 'C4'))))
```

**`layer(sound, id=None, *, fx=(), keys=None, vel=None, bend=, pedal=, expression=, dynamics=, modwheel=, **params)`**:
`sound` is a patch name, a Patch (its instrument; its fx chain becomes the layer's fx, then `fx=`; its `gain_db` adds to
the layer level, its pan is the layer pan; its sends are dropped - the track's sends serve the whole stack) or an
Instrument. `id` names the layer for addressing (default: the patch name's last part or the instrument type, made
unique). Layer params (`patches.LAYER_KEYS`; every other keyword is a param of the layer's instrument, e.g.
`cutoff=900`):

| param | meaning |
|---|---|
| `level` (dB), `pan`, `mute` | the layer's mix (automatable, smoothed); `pan` is a balance like the track pan |
| `transpose` (st), `fine` (ct) | `transpose=12` / `-12` octave layers; `fine` detunes through the child's pitch bend (automatable; 3-8 ct against another layer of the same instrument = a chorused double) |
| `keys=(lo, hi)`, `keyfade` | key range (note names or MIDI, before transpose); `keyfade` semitones of equal-power crossfade inside the range at a split |
| `vel=(lo, hi)`, `velfade` | velocity range; `velfade` = equal-power crossfade width inside it (soft layer `vel=(1, 95)`, hard layer `vel=(60, 127)`, both `velfade=35`: both at -3 dB at 78) |
| `velcurve`, `velscale` | the velocity the child gets: `vel ** velcurve * velscale` (crossfades use the played velocity) |
| `delay` (ms) | the layer's notes start and end later: 10-30 ms a soft double, 40-120 ms a pad swelling in behind the attack |
| `bend`, `pedal`, `expression`, `dynamics`, `modwheel` | `False`: the layer ignores the stack's param of that name (a bell that must not bend, a pad that must stop at key-up) |
| `xfvoices` | extra child instances for notes inside a crossfade (default 4; fade gains are rounded to 1 dB steps, so notes of nearby velocities share one) |

**`inst.stack(*layers, **params)`**: 1..8 layers (layer objects, patch names, Patches, Instruments). Stack params:
`level` (dB), and the performance params it forwards to every layer that follows them: `pitchbend` (+ each layer's
`fine`), `pedal` (sampler / sf2 layers use their own pedal with release samples; the stack holds the note-offs of va /
dx7 / drums layers until pedal-up), `expression` (the stack applies it to layers without their own), `dynamics`
(sampler layers), `modwheel` (dx7 layers). Automate them as usual: `track.automate('instrument.pedal', ...)`.

**Addressing a layer** - `.but()`, automation and modulators use `layers.<id or index>.<param>`: a layer param
(`layers.pad.level`), an effect of the layer's chain by index, name or type (`layers.pad.fx.chorus.mix`) or a param of
its instrument (`layers.pad.cutoff`). The compiler writes ids and fx indices (`instrument.layers.pad.fx.0.mix`).

```python
p = patches.get('layered/piano_glass_lead').layer('glass', level=-6)       # = .but(**{'layers.glass.level': -6})
p = p.but(**{'layers.pad.cutoff': 2400, 'layers.pad.fx.chorus.mix': 0.5, 'pedal': 1})
lead.automate('instrument.layers.pad.level', ramp(chorus.start, chorus.end, -20, -8))  # bring the pad in
lead.modulate('instrument.layers.glass.fine', lfo('sine', '1/2', depth=6))             # slow shimmer
lead.automate('instrument.pedal', steps({0: 1, 7.9: 0, 8: 1}))                         # pedal: piano + glass
```

**`Patch.layered(name, *layers, fx=(), gain_db=0, pan=0, sends=None, notes='', audition=None, **stack_params)`** makes
a patch of a stack (`fx` = the stack's own chain after the layers are summed); `patch.layer(id, **params)` changes one
layer. `inst.stack(...).layers` lists the Layer objects (`.id`, `.instrument`, `.fx`, `.params`).

Rules of thumb (measured on the layered/* library, `agentsound/patches/layered.py`): one layer leads and the others
sit 6-16 LU under the stack (a colour you feel more than hear); layers of *different* instruments are uncorrelated
(the stack's energy = the sum of its layers within 0.1 dB: no phasing); an octave-down layer under a lead is best a
square / triangle (odd harmonics only: none lands on the lead's partials); two sampled keyboards on one key inside a
velocity crossfade keep a fixed phase relation (single notes vary about +-1.5 dB there); split two bass layers with
filters (the growl high-passed, the sub low-passed) so their fundamentals do not fight; a pad layer that should not
smear chord changes gets `pedal=False` - so does any sustaining synth under a pedalled melody (a pedalled supersaw
under a piano hook piles every note of the chord into a held cluster; the pedal of a delayed layer arrives with its
notes, `delay` ms late) -, an octave glass / bell layer `bend=False`. Sampler layers load only the zones
their notes reach (the key / velocity range and transpose of the layer are applied before zone pruning).
Articulation marks (keyswitches, per-note glides) need a plain sampler track; on a stack, automate the sampler layer's
own params instead (`instrument.layers.strings.dynamics` when it does not follow the stack's `dynamics`).
`art.perform` / `art.vibrato` write the vibrato on every sampler layer of a stack themselves
(`instrument.layers.<id>.vibrato`), legato ties and `instrument.pitchbend` scoops / falls reach every layer that follows
the stack. Hero leads are built by the hero wrapper (next section): e.g. `layered/hero_sax` = the lead take + two
detuned, late, panned takes of a different sample set ~10 dB under it (uncorrelated: width without phasing) + an
optional muted octave layer (`instrument.layers.octave.mute` 0 in the big sections), through the shared hero chain.

## Hero sounds (`hero()`, `agentsound.heroes`)

THE way to make a hook or a solo stand in front like on a record (recipes/HUMAN_FEEDBACK.md: "epischer und
präsenter", "der Lead ist zu leise", "piepsig"): one wrapper for every instrument - the sound (the source + a shared
hero chain voiced per family) AND its mix rules (the bed carved around it, rides, echo throws), all logged.

```python
lead = hero(s.track('lead', 'sampled/solo_violin'), family='strings', genre='film',
            bed=[strings, pad], competitors=[piano], sections=[chorus1, chorus2])   # -> the track, now a hero
hero.play(lead, theme, verse)                   # = heroes.play: the family's player (touch() arcs, vibrato, ...)
heroes.air(lead, [(8, 0), (8.5, 3, 'smooth'), (9.5, 0, 'smooth')])   # breath on a held note, after the compressor
p = hero('sampled/trumpet', family='brass')     # -> a Patch: this sound through the brass hero
p = hero(family='sax')                          # -> the family's own hero (= hero/sax)
s.track('lead', 'hero/strings')                 # the presets are patches too: hero/<preset> (without mix rules)
print(lead.hero)                                # what it did (also printed by build / check: 'hero ...' lines)
```

**`hero(sound=None, family=None, *, genre=None, bed=(), competitors=(), sections=None, double=None, octave=None,
air=True, chain=True, space=True, plate=None, echo=None, duck=True, carve=True, dips=True, ride=True, throws=True,
**stages)`**. `sound`: a Track (the wrapper replaces its sound by the hero build of it - the song's own inserts after
the patch chain stay - and applies the mix rules; returns the track, `track.hero` = the log and options), or a patch
name / Patch / Instrument / None (returns a Patch; the mix rules need a track). `family`: a preset, family or alias
(below); None = inferred from the sound (`heroes.infer`: a hero patch -> its preset, the patch name's words -
violin, trumpet, flute, choir, organ, guitar, piano, sax ... -, a va / dx7 -> synth, else generic).

**The sound** (`heroes.build(preset, sound=None, double=, octave=, air=True, **stages)`): the preset's own source
(`sound=None` or its default) or yours. A single source stays a plain instrument - keyswitch articulations, legato
transitions, `dynamics` swells and per-note glides keep working; extra layers make a stack (`inst.stack`), never a
copy of the same samples (a detuned copy comb-filters): `double='takes'` (other takes of the instrument from a
different sample set, ~10 dB under, detuned, 17-27 ms late, panned apart - the preset's own; around another sound
they become `'shift'` unless forced), `double='shift'` (a micro-pitch double stage), `octave=True / 'muted'` (the
family's octave-down layer). The shared chain, in this order (`heroes.ORDER`; a preset may reorder):
`tone` (eq: high-pass, the family's mud / honk / box) -> `catch` (a fast peak compressor, pianos) -> `comp` (the
bloom: <= 3:1, 15-30 ms attack so attacks and accents pass) -> `amp` (family fx) -> `drive` (saturator) -> `tape` ->
`presence` (eq: bite 2.5-3.5 kHz, air shelf 8-10 kHz) -> `exciter` -> `chorus` / `double` (microshift) / `width` /
`dimension` -> `echo` (its own, guitars) -> **`air`** (last: a utility named `air`, 0 dB - the BREATH stage).
`**stages` override: `hero(t, family='brass', comp={'threshold': -20}, drive=False)`.

**The air stage** (`heroes.AIR_TARGET = 'fx.air.gain'`): within-note expression - a wind player's "mal kurz mehr,
mal kurz weniger" air on a held note, a swell, an fp-crescendo - written as dB on `fx.air.gain` (`heroes.air(track,
points)`) lands after all the compression and saturation: a 3 dB push on a held note through the sax chain (6-9 dB
of gain reduction) measures +3.0 dB at the output; the same push in front of the compressor (`instrument.expression`)
+0.9 dB. The timbre side of the breath stays in front of the chain (`instrument.dynamics` crossfades,
`articulation.expression`); the air stage gives the level move back on top. `air=False` leaves it out.

**The mix rules** (a Track given), each logged and each switchable (`False` = off, a number = the depth in dB):
`space` - the preset's plate bus (`bus/hero_plate`, created as bus `hero_plate` if missing; the patch's own `plate`
send moves there; `plate=` another bus / patch) and the echo send for the throws (the song's `echo` bus, any bus named
`*echo*` / `*delay*`, else a new `s.echo()`; `echo=` a bus, `False` = none); `duck` - the bed ducks under the hero
(`song.sidechain(*bed, key=hero, ...)`); `carve` - the bed's presence band dips while the hero plays (`song.carve`, a
keyed dynamic EQ at the family's frequency); `dips` - competitors get a static presence dip (`mixer.add_eq_dip`, an
eq named `hero_dip`); `ride` - the hero up in the hook sections (a utility `hero_ride` + an `fx.hero_ride.gain` lane,
the mixer's ride points; `sections=` or the sections named chorus / drop / hook / refrain / lift / climax / finale /
peak / head, plus the preset's own feature sections: the guitar heroes' `solo...` sections, mix key `feature`); `throws` - the echo send thrown up on every phrase end the track plays (`articulation.throws`; a guitar
hero throws its own echo's `fx.echo.mix`). Rides and throws are written when the song compiles
(`Song.add_compile_hook`), so every note placed after `hero()` counts; a lane the song writes itself on the same
target wins (logged). `genre=` (a mixer profile: pop, rock, film, synthwave, jazz, classical ...) sets the duck
(`bed_duck_db`), ride (`lead_ride_db`) and dip (`dip_db`) depths instead of the preset's (rock: no bed duck, jazz /
classical: no ride). The mixer treats a hero track as the lead (`mixer.infer_roles`: why 'hero()').

| preset (family) | default source | chain (key values) | space | mix: duck / carve / ride / dips | gain |
|---|---|---|---|---|---|
| `sax` | Weresax alto + 2 MTG alto takes (-10 / -10.5 dB, +9 / -8 ct, 17 / 26 ms) + muted MTG tenor -12 st | -2.5 dB 650 Hz, -4 dB 1.3 kHz; 3:1 -31 dB 25 ms; tube 9 dB; +2 dB 3 kHz, +3 dB 8 kHz; exciter | hero_plate -14, hall -16, echo -24 -> -5 | 2.5 / 4 @ 2.5 kHz / +2 / -2 | -2.6 |
| `piano` (`piano_pop`, `piano_strings`) | Salamander key split (hammers 0.5 / 0.15; + VPO strings -14 dB 70 ms) | -3 dB 280 Hz, +2.5 dB 2 kHz, +3 dB 10 kHz; catch 3:1 5 ms; glue rms 2:1 30 ms; tape; width 1.2; Dimension-D | plate -7, hall -16, echo -60 -> -3 | 2.5 / 2 @ 2.5 kHz / +1 / -2 | 2.2 (3.2, 2.6) |
| `guitar` (`guitar_clean`, `guitar_heavy`) | FSBS Strat DI in 5 velocity zones through Plexi / 4x12 (clean: one sampler + combo; heavy v2: a neck-pickup DI in 4 zones through the engine's tube `amp` (3 stages, TS push, mid 7, presence 8) + 4x12 IR, + amped lead double -7 dB; its eq only hp 80 / lp 7.5 kHz, tape without drive) | hp 150, -3.5 dB 3.8 kHz, lp 6.8 kHz; tape; microshift 7 ct; own dotted-8th echo | hall -12, plate -18; throws on fx.echo.mix | 2.5 / 2.5 @ 2 kHz / +1 / -2 | -1.0 (-6.9, -3.8) |
| `synth` (`darksynth`) | two-saw voice + square octave -9 dB (G#4 up) + supersaw halo -10 dB (dark: sync lead + driven saw octave) | -3 dB 420 Hz, -4.5 dB 3.6 kHz, +2.5 dB 9.5 kHz; rms 2:1 25 ms; tape; Juno I; microshift 9 ct (dark: tube 8 dB first) | plate -12, hall -14, echo -11 -> -4 | 2.5 / 2 @ 1.8 kHz / +1 / -2 | 1.9 (4.6) |
| `piano_synth` | piano_lead + poly saw voice -6 dB (velcurve 1.6) | -1.5 dB 3.3 kHz, +1.5 dB 9.5 kHz; tape; microshift 7 ct | plate -12, hall -14, echo -12 -> -4 | 2.5 / 2 @ 1.8 kHz / +1 / -2 | -1.5 |
| `strings` (violin) | sampled/solo_violin (VSCO 2); takes: VPO violins -12 dB; octave: SSO cello | -1.5 dB 500 Hz / 1.1 kHz / 3.8 kHz; 1.8:1 -21 dB 25 ms; tape; +1.5 dB 2.8 kHz, +2 dB 9 kHz | hero_plate -16, hall -9, echo -28 -> -12 | 1.5 / 3 @ 2.8 kHz / +1 / -1.5 | -1.1 |
| `brass` (trumpet) | sampled/solo_trumpet (VSCO 2); takes: VPO (Iowa) trumpet x2; octave: SSO trombone | -1.5 dB 420 Hz, -2 dB 1.2 kHz, -1.5 dB 4.8 kHz; 2:1 -23 dB 20 ms; tube 6 dB; +1.5 dB 2.8 kHz, +2 dB 8.5 kHz; exciter | hero_plate -14, hall -14, echo -24 -> -8 | 2 / 3 @ 2.2 kHz / +1.5 / -2 | -1.8 |
| `woodwind` (flute) | sampled/solo_flute (VSCO 2); takes: SSO flute; octave: clarinet | hp 200, -1.5 dB 450 Hz; 1.8:1 -21 dB 25 ms; tape; +1 dB 3 kHz, +2.5 dB 9 kHz | hero_plate -14, hall -10, echo -24 -> -9 | 2 / 3 @ 2.2 kHz / +1 / -1.5 | -0.7 |
| `voice` (choir) | sampled/choir (VPO "ah") | -2 dB 300 Hz; 2:1 -21 dB 15 ms; tube 5 dB; +2 dB 3.2 kHz, +3 dB 10 kHz; exciter; vocal doubler 9 ct | hero_plate -12, hall -14, echo -20 -> -6 | 2.5 / 3 @ 3 kHz / +1.5 / -2 | -2.5 |
| `organ` | sampled/tonewheel_organ (+ its Leslie) | -2 dB 250 Hz, +1 dB 800 Hz; 2:1 -21 dB; tube 8 dB; +1.5 dB 2.5 / 8 kHz | hall -14, echo -26 -> -10 (no plate) | 2 / 2.5 @ 1.5 kHz / +1 / -2 | -0.2 |
| `generic` | sampled/solo_cello (any other sound) | hp 60, -2 dB 300 Hz; 1.8:1 -21 dB 20 ms; tape; +1.5 dB 2.8 kHz, +2 dB 9 kHz | hero_plate -16, hall -12, echo -24 -> -8 | 2.5 / 3 @ 2.5 kHz / +1 / -2 | -1.6 |

Aliases: violin / fiddle -> strings, trumpet -> brass, flute -> woodwind, choir / vocal / vox -> voice, hammond / b3
-> organ, synth_lead -> synth, synth_piano -> piano_synth, darksynth_lead -> darksynth. `heroes.presets()`,
`heroes.get_preset(name)` (`.chain`, `.mix`, `.space`, `.play`, `.measured`), `heroes.PRESETS`. Generic vs
family-specific: the stage vocabulary and order, `heroes.MIX_DEFAULTS` / `SPACE_DEFAULTS`, the mix / ride / throw
logic are shared; frequencies, amounts, sources, sends and mix depths are per preset.

**Levels and dynamics**: every `hero/<preset>` lands at -18.0 LUFS on its audition phrase (like the library); around
another sound the gain is the preset's `user_gain_db` (measured on a typical other sound) - audition it. The chains
keep the dynamics ear quiet: <= 3:1 with 15-30 ms attacks; the new families measured on a velocity ladder (40 -> 127,
one note) 1.6-1.7 dB per 10 velocity steps (the raw samplers 2.2-2.5), the guitar hero 1.9, piano 2.4, synth 2.2; the
sax hero is squeezed hard on purpose (0.3 dB per 10 on isolated notes: its phrase dynamics are the velocity arcs'
timbre, the rides and the air stage). Play them with velocity arcs (`hero.play` = `humanize.touch` in the preset's
range + the family's player).

**The old names** stay registered and unchanged (their definitions are pinned by tests/python/test_hero.py; the
songs that use them render byte-identical JSON): `layered/hero_sax`, `sampled/hero_piano`, `sampled/hero_piano_pop`,
`layered/hero_piano_strings`, `layered/hero_guitar`, `sampled/hero_guitar_clean`, `layered/hero_guitar_heavy`,
`hero/synth_lead`, `hero/synth_piano`, `hero/darksynth_lead` - each is the preset's build without the air stage;
`hero/<preset>` is the same sound + `air` (sample-identical at 0 dB). Their helpers still work: `hero_piano.carve`,
`hero_guitar.play` / `.lead`, `hero_synth.perform`, `HERO_SAX`, `articulation.throws`.

## Samples (SoundFonts and WAV files)

Sampled instruments are first-class sounds: an `sf2` or `sampler` track is a track like any other, so insert fx,
sends, sidechains, automation and modulators all work on it (`instrument.cutoff` sweeps, `instrument.pitchbend`
dives, `gainDb` trance gates, ...). Both play through the same band-limited core: 32-tap windowed-sinc
interpolation whose cutoff follows the pitch when a sample is played faster than it was recorded (no aliasing up
to 3 octaves above native speed), seamless loops (also single-cycle loops), click-free voice stealing (4 ms fade).

**SoundFonts** (`inst.sf2`): `assets/soundfonts/GeneralUser-GS.sf2` (GeneralUser GS 2.0.3, 287 presets: GM bank 0,
variation banks 8-16, drum kits in bank 128 and 120) is the default font; other `.sf2` files in
`assets/soundfonts/` are used with `file='Name.sf2'`.

```python
inst.sf2('Grand Piano')                      # preset name: case-insensitive, spaces trimmed, did-you-mean errors
inst.sf2('0:48') / inst.sf2(bank=0, program=48)      # GM numbers; bank 128 = drum kits (36 kick, 38 snare, ...)
inst.sf2('Slow Strings', attack=3, release=2, width=1.4, cutoff=-12, level=-2)
kit = s.track('kit', inst.sf2('Standard 1'))          # GM kit: play it with drums({...}) grids
s.track('keys', 'gm/grand_piano')                     # calibrated library patches (below)
```

| sf2 param | |
|---|---|
| `preset` / `bank` + `program`, `file` | the preset (default: the font's first, GM 0:0 Grand Piano) and font |
| `level` (dB), `pan`, `width` (0..2, the font's own panning: stereo pianos spread by key, linked stereo samples) | output; at level 0 a GM piano plays 4-note chords at ~-18 LUFS and the font's own balance places every other preset around it |
| `cutoff` (st, automatable) | shifts every voice's resonant lowpass (the font's filter; voices without one get it below 0): -12 an octave darker, -36..-60 muffled, sweeps |
| `brightness` (-1..1, automatable) | tilt EQ (+6 / -10 dB above 2.5 kHz) |
| `pitchbend` (st, automatable), `transpose` (st, moves the key zones), `tune` (ct) | pitch |
| `attack`, `release` (x, 0.05..20) | scale the preset's envelope times: `attack=4` slow swells, `release=3` long tails |
| `velsens` (0..1), `polyphony` (voices, 64), `mono` (`'on'`: one note at a time) | playing |
| `pedal` (0..1 step, automatable), `expression` (0..1, automatable) | sustain pedal (>= 0.5 down: note-offs are held until pedal-up) and CC11-style volume (gain x expression^2) |

What the player implements (SoundFont 2.01/2.04): preset + instrument generator layering (preset generators add to
the instrument's, local zones override global zones), key and velocity ranges (velocity layers), root key / coarse /
fine / scale tuning and the sample's pitch correction, sample start/end/loop offsets (+ coarse), loop modes (none,
continuous, until release: the tail after the loop plays on release), DAHDSR volume envelope (attack linear in
amplitude, decay/release linear in dB, keynum-to-hold/decay), modulation envelope and both LFOs to pitch / filter /
volume, resonant 2-pole lowpass per voice (initialFilterFc/Q, resonance peak compensated by half its height),
pan, exclusive classes (a closed hi-hat chokes the open one, 100 ms), linked stereo samples (two phase-locked
voices, hard left/right unless the font pans them), 24-bit samples (sm24), and modulators whose sources are note-on
velocity / key number (the SF2 default velocity->attenuation (concave, 960 cB) and velocity->filter modulators;
instrument modulators with the same identity override them, preset modulators add). **initialAttenuation** is
applied x 0.4 (as the EMU hardware and FluidSynth do; GM fonts are balanced for it); modulator attenuation is
not scaled. Not implemented: MIDI controllers other than the sustain pedal and expression (the `pedal` and
`expression` params; CCs sit at their power-on values; the pitch wheel is the `pitchbend` param, no modwheel vibrato), per-voice chorus/reverb sends (use buses and `sends=`), modulator links,
modulated loop points.

**gm/ patches** (`agentsound/patches/gm_sf2.py`, each -18 LUFS on its audition material, with reverb sends and
extra width): `gm/grand_piano gm/piano_lead gm/strings gm/choir_aahs gm/orchestra_hit gm/warm_pad gm/fretless gm/nylon_guitar
gm/music_box gm/synth_strings gm/brass_section`. Any other preset: `inst.sf2('Name')`, e.g. 'Fast Strings',
'Tremolo Strings', 'Pizzicato Strings', 'Orchestral Harp', 'Timpani', 'French Horns', 'Trumpet', 'Flute', 'Oboe',
'Clarinet', 'Tine Electric Piano', 'Tonewheel Organ', 'Vibraphone', 'Marimba', 'Acoustic Bass', 'Finger Bass',
'Synth Bass 1', 'Halo Pad', 'Sweep Pad', 'Voice Oohs', 'Steel Drums', 'Kalimba', kits 'Standard 1', 'Room',
'Power', 'Electronic', '808/909', 'Jazz', 'Brush', 'Orchestral' (`python -m agentsound sf2 kit`).

**WAV sampler** (`inst.sampler`):

```python
inst.sampler(dir='samples/909', oneshot='on')        # folder: every .wav, mapped by its name (see below)
inst.sampler(dir='./samples/chops')                   # './' and '../' = relative to the song file (made absolute)
inst.sampler(file='samples/pad.wav', root='A3', loop='forward', attack=0.4, release=1.5)
inst.sampler(zones=[{'file': 'samples/p/C3.wav', 'root': 'C3', 'hi': 'F#3'},
                    {'file': 'samples/p/C4.wav', 'root': 'C4', 'lo': 'G3', 'vello': 90, 'gain': -2}])
inst.sampler(file='soundfonts/GeneralUser-GS.sf2', sample='Orchestra Hit-2', oneshot='on', reverse='on')
```

* Folder mapping: GM drum names play on their key without transposition (`kick bd rim rimshot snare sd clap cp
  tom_lo tom_mid tom_hi hat hh closed_hat ch pedal ohh open_hat crash ride tamb cowbell`; case, spaces and `-` are
  ignored: `Closed Hat.wav`), and the hi-hats (42/44/46) choke each other. Note names (`C4.wav`, `F#3.wav`,
  `Bb2.wav`, `60.wav`, C4 = 60) spread over the keyboard: each sample plays the keys nearest to it. Any other file
  name is an error. `{'dir': ..., 'loop': 'forward', 'gain': -3}` apply to every file.
* Zone keys: `file`, `sample` (a SoundFont sample by name, for `.sf2` files: `python -m agentsound sf2 --samples
  [search]`), `root` (default 60; SoundFont samples: their own root and pitch correction), `lo hi` (keys),
  `vello velhi` (velocity layers), `loop` (`none` `oneshot` `forward` `pingpong` `sustain` (loops while the key
  is held) `auto` (the WAV's own smpl loop, if any)), `loopStart loopEnd` (frames; default the file's smpl loop,
  else the whole file; SoundFont samples their own loop), `gain` (dB), `tune` (ct), `pan`, `choke` (group number: a
  new note fades the group's other notes in 50 ms). Overlapping zones layer. The full SFZ-grade zone model (round
  robin, random layers, release triggers, groups / off_by, crossfades, per-zone envelopes, filters, EQ, LFOs) is
  listed in docs/RENDER_FORMAT.md; `inst.sfz` (below) writes it for you.
* Params: `level` (0 dB = the file's level; mono files -3 dB per side at centre), `pan`, `width` (stereo files
  mid/side 0..2; mono zones scale their `pan`), `transpose`, `tune`, `pitchbend`, `cutoff` (Hz, 20000 = open),
  `resonance` (all automatable except transpose/tune), `attack decay sustain release` (s; linear attack,
  exponential decay/release), `velsens` (level ~ (velocity/127)^(2 velsens)), `start` (ms offset into the
  sample, applied per note: automate it to step through a phrase), `oneshot` (`'on'`: plays the whole sample,
  ignores note-offs and loops: drums, hits), `reverse` (`'on'`), `mono`, `polyphony` (32, up to 256), `pedal`
  (sustain pedal: automate with steps, 1 down / 0 up; release samples of held notes play at pedal-up; 0.5..1 is a
  half pedal: the held notes ring but die faster - treble +16 dB/s at 0.5, +8 at 0.75, the bass 40 % of that),
  `sympathetic` (0..1, default 0 = off: a piano's sympathetic string resonance - 88 tuned comb strings excited by
  what is played, ringing while the pedal (or their held key) lifts their dampers; 0.5-0.9 on a classical / ballad
  grand: the pedalled sound blooms and decays more slowly, silently held keys ring along),
  `expression` (0..1, gain x expression^2: swells and phrase dynamics).
* Paths: relative to `assets/` (put shared sample sets in `assets/samples/<name>/`), or absolute; the Python layer
  turns `./...` / `../...` into absolute paths next to the song (`songs/<slug>/samples/`). Files: PCM 8/16/24/32-bit
  or float WAV, any rate (resampled), mono or stereo (more channels: the first two).

### SFZ instruments (`inst.sfz`)

Most free multisample libraries (pianos, orchestras, drum kits with brushes and round robins) ship as `.sfz`
files. `inst.sfz` imports one onto the `sampler`, so it plays like a commercial sampler: velocity layers, round
robin, random layers, release samples, keyswitch articulations, multi-mic mixes, groups that cut each other off.

```python
piano = s.track('piano', inst.sfz('samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz'))
piano.automate('instrument.pedal', [[0, 1, 'step'], [15.9, 0, 'step'], [16, 1, 'step']])   # sustain pedal
strings = inst.sfz('samples/vpo-scripts-standard/Strings/1st-violin-SEC-KS-C2.sfz', articulation='staccato')
bass = inst.sfz('samples/meatbass/Programs/04_pizz.sfz', cc={107: 26}, level=2)    # controller-selected layers
kit = inst.sfz('samples/swirly-drums/Programs/Basic_kit.sfz', cc={4: 127, 14: 0}, mics={'wet': -6})
inst.sfz('./my_kit/kit.sfz')                                                         # next to the song
```

`inst.sfz(path, articulation=None, cc=None, mics=None, strict=False, dyn_cc='auto', keyswitches='live', hammers=None,
**params)`:

* `path`: `'samples/<pack>/...'` (the sample library: `$AGENTSOUND_SAMPLES`, else `assets/samples`), `./` / `../`
  next to the song, or absolute. A missing pack names the `samples fetch` command; missing sample files are a
  ComposeError listing them.
* `articulation`: a keyswitch articulation by label (case-insensitive substring) or key, chosen statically.
  Without it every articulation is imported and switched **live** per note (`keyswitches='live'`, the default:
  `clip.articulate('staccato')`, see "Realistic performance"; unmarked notes play the file's `sw_default`;
  `keyswitches='static'` imports only that one). `sfz.articulations(path)` lists them
  (`[{'key', 'name', 'label', 'regions', 'default'}]`).
* `dyn_cc`: the **dynamics controller** that stays live as the sampler's automatable `dynamics` param: `'auto'` (CC1
  when the file maps crossfades, volume / gain / amplitude, cutoff or `lo/hicc` layers to it, else CC11 when it does),
  a number, or `None` (static like every other CC). Its crossfades / gain / cutoff / layer conditions become the zone
  fields `xfinLoDyn`.., `dynGain`, `dynCutoff`, `dynLo`/`dynHi`; `dynamics` starts at the controller's value (so the
  default sound is the static one) and `dyntone` is set to 0 when the file's own layers or filter carry the timbre or
  when that value is below the top (the tilt is flat only at dynamics 1; pass `dyntone=` to have both).
* `cc`: fixed controller values `{number: 0..127}` for the whole song. The engine plays no MIDI controllers, so
  every CC is evaluated once at import: `locc`/`hicc` conditions pick layers, `*_oncc` modulations become static
  values, CC crossfades static gains. Defaults: the file's `set_ccN` / `set_hdccN`, else MIDI power-on (7 = 100,
  10 = 64, 11 = 127, others 0). CC-triggered regions (`on_locc`: pedal noises) are skipped. Automate
  `instrument.pedal` for CC64 and `instrument.expression` for CC11 instead.
* `mics`: `{name: dB or None}` level or mute per microphone / signal layer (detected from folder and file names
  and group labels: close, oh, room, wet, top, btm, ...); `sfz.mics(path)` lists them with region counts.
* `strict=True`: raise on opcodes the sampler cannot play. Default: one compile warning names them (with counts).
* `hammers`: 0..1 piano hammer voicing (`sfz.hammers`): every velocity layer gets two eq bands by its velocity - the
  loud layers darker (at 1: -7 dB at 3 kHz, -9 dB at 7.5 kHz on the top layer, 0 at velocity 80), the soft ones a
  little clearer - a gentler velocity -> brightness curve, like softened hammer felt: a close-miked sampled grand's
  loud notes bloom instead of turning glassy (user feedback 2026-09-30, perry-street-rain: "es klingt hart").
  0.5-0.8 = a warm jazz / ballad grand (`sampled/jazz_grand` = the Salamander at 0.75).
* `velcurve=[(velocity, gain), ...]`: one velocity -> amplitude curve for every velocity-layer zone (zones with
  lovel / hivel), replacing the file's `amp_velcurve_N` / `amp_veltrack`. Packs that ramp each layer to full level
  at its top (`amp_velcurve_96=1` ...) play louder at the top of a soft layer than at the bottom of the next one:
  `sfz.even_velcurve([(lovel, hivel, level_db), ...], power=2.0)` builds a smooth, monotonic curve from the layers'
  measured sample levels (the level follows 20 x power x log10(v/127) dB whatever layer plays). `sampled/upright_bass`
  (Meatbass) uses it: the file alone gave ~4 dB between velocity 57 and 103 and played 96 louder than 103.
* `**params`: sampler params (`level`, `pedal`, `expression`, `width`, `cutoff`, `velsens`, `transpose`, `tune`,
  `polyphony` (128 here), `attack decay sustain release` for zones without their own `ampeg_*`).

What is imported: `<control> <global> <master> <group> <region>` inheritance, `#define $VAR`, `#include`,
`default_path`, `note_offset` / `octave_offset`, note names (`c4` = 60), comments, paths with spaces or
backslashes (case-insensitive lookup; `.flac` / `.ogg` / `.aif` fall back to the converted `.wav` of the
downloader), `<curve>` and the predefined curves. Opcodes: key / velocity ranges, `pitch_keycenter`
(`sample` = the WAV's own), `transpose` / `tune` / `pitch_keytrack`, `volume` / `amplitude` / `pan` / `width`,
`amp_veltrack` / `amp_velcurve_N`, `xfin_*` / `xfout_*` (velocity, key, CC), `seq_length` / `seq_position`,
`lorand` / `hirand`, `trigger` (attack / release / release_key / first / legato), `rt_decay`, `offset` / `end` /
`offset_random`, `loop_mode` / `loop_start` / `loop_end` (and the WAV's `smpl` loop), `group` / `off_by` /
`off_mode` / `off_time`, `note_polyphony`, `polyphony` (voices per group), `ampeg_*` (+ `vel2*`), `fil_type` / `cutoff` / `resonance` /
`fil_keytrack` / `fil_veltrack`, `fileg_*` (filter envelope), `eqN_*`, `pitchlfo_*` / `amplfo_*` and `lfoN` to
pitch / volume (vibrato, tremolo), `amp_random` / `pitch_random` / `delay` / `delay_random`, `sustain_sw`,
`sw_lokey` / `sw_hikey` / `sw_last` / `sw_down` / `sw_up` / `sw_default` / `sw_label`, `lochan` / `hichan`,
`loprog` / `hiprog`. Counted, not played (`info['unsupported']`): `<effect>` / `<midi>` sections, `varN_*`,
second filters, LFO targets other than pitch / volume, envelope shapes (`*_shape`),
`effectN` sends. Controllers only per-note (velocity / key through CC 131-133) are linearized per region.

Inspect before composing: `python -m agentsound sfz FILE [--json] [--cc 64=127] [--articulation NAME] [--pitch]` prints keys,
velocity layers, round robin, random layers, release zones, articulations, microphones, labelled controllers with
their defaults and everything unsupported; `sfz --check [PACK ...]` imports every `.sfz` of the installed packs
(fragments that are `#include`d by another file are marked as such). `python -m agentsound find WORD` prints
ready-to-paste `inst.sfz(...)` lines (from the pack's INDEX.json: `catalog --reindex` after an update).
`--pitch` (`sfz.pitch_check(path)`) renders a few notes and compares the measured fundamental with the MIDI pitch: it
catches octave-shifted or mis-named sample sets (e.g. Karoryfer's Big Cat cello sounds an octave above its keys: play
it with `transpose=-12`). Programs whose sample paths only resolve in the pack's `Samples/` folder (a missing
`default_path`, an undefined `$sample_dir`) are found there (listed under `approximated`).

At compile, zones that none of the track's notes can reach (key after `transpose`, velocity) are dropped, so only
the samples a song plays are loaded (a warning says "K of N zones can sound with its notes"); 16-bit samples stay
16-bit in memory and one file is shared by every zone and track that plays it (`AGENTSOUND_VERBOSE=1` prints the
engine's load summary). Round-robin counters start at the render start: a `--section` preview may pick a different
round-robin sample than the full render at the same spot (random layers are preview-stable).

**`inst.sfz_multi({'sustain': 'x_sus.sfz', 'staccato': 'x_stac.sfz', 'pizz': {'path': 'x_pizz.sfz', 'gain': -2}},
keyswitch=0, default=None, cc=None, mics=None, dyn_cc='auto', **params)`**: one instrument from separate
per-articulation programs (VSCO 2, SSO and VPO ship them separately); articulation i gets keyswitch key
`keyswitch` + i (0 = C-1 upwards, below any played note), `default` (else the first) plays unmarked notes, groups /
`off_by` are renumbered per program; a program dict takes `path`, `articulation` (of a keyswitch program), `cc`,
`mics`, `gain`. `sfz.load_multi(...)` returns the zones and info.

**sampled/ patches** (`agentsound/patches/sampled.py`, each -18 LUFS on its audition material, lazy: the .sfz is
read when a song renders it, a missing pack is an error only then): keys `sampled/grand_piano` (Salamander, 16
layers + release samples) `sampled/jazz_grand` (the same grand voiced warm: softened hammers, `hammers=0.75` - the
jazz presets' piano) `sampled/piano_lead` (the same grand voiced as a bright, compressed, chorused
melody piano for hooks in C5-C7 over a dense mix; `lead='piano'` on the synthwave bands) `sampled/upright_piano` `sampled/rhodes` `sampled/wurlitzer` `sampled/vibraphone`
`sampled/celesta`; jazz `sampled/upright_bass` `sampled/brush_kit` (stirs and sweeps on 60-64)
`sampled/jazz_kit` `sampled/tenor_sax` `sampled/alto_sax` `sampled/nylon_guitar`; orchestra (Virtual Playing
Orchestra) `sampled/strings` `sampled/strings_staccato` `sampled/strings_pizz` `sampled/violins` `sampled/cellos`
`sampled/basses` `sampled/flute` `sampled/clarinet` `sampled/oboe` `sampled/french_horns` `sampled/trumpet`
`sampled/trombones` `sampled/harp` `sampled/timpani` `sampled/choir`; played (v2, "Realistic performance")
`sampled/solo_violin` `sampled/solo_cello` `sampled/violin_section` `sampled/viola_section` `sampled/cello_section`
`sampled/bass_section` (keyswitched sustain / spiccato / pizzicato / tremolo, live dynamics, legato soloists), and
`sampled/tenor_sax` / `sampled/alto_sax` are legato players since v2. Each patch's notes give the key map, range,
useful `cc=` tweaks and the license (rhodes and vibraphone are CC-BY-NC).

### Kits (`inst.kit`), organs (`inst.organ`) and multisamples (`inst.multisample`)

Packs that are not SFZ: drum one-shot collections with any file names, Hydrogen and DrumGizmo kits, GrandOrgue pipe
organs and note-named multisample folders. Each builder writes sampler zones (`agentsound/kits.py`,
`agentsound/organ.py`); `python -m agentsound kit DIR [--json]` prints what it makes of a folder (the drum map, an
organ's manuals and stops, or `--multisample` roots) before you use it.

```python
kit = s.track('drums', inst.kit('samples/hyperreal-linndrum'))                       # any names -> GM keys
kit = s.track('drums', inst.kit('samples/sampleradar-80s-pop-drums/Drum Kits/Kit A',
                                map={'snare2': 'samples/sampleradar-80s-pop-drums/Gated Snares/80PD_GatedSnare-05.wav',
                                     'clap': None}, gains={'hats': -6}))
kit = s.track('drums', inst.kit('samples/hydrogen-forzee-stereo'))                   # Hydrogen drumkit.xml
kit = s.track('drums', inst.kit('samples/drumgizmo-drskit', mics={'room': -6, 'overheads': -2, 'SnareBottom': None}))
org = s.track('organ', inst.organ('samples/lars-palo-burea-church', stops=['Principal 8', 'Oktava 4']))
ped = s.track('pedal', inst.organ('samples/lars-palo-burea-church', stops=['Subbas 16'], manual='pedal', stereo='left'))
vc = s.track('cello', inst.multisample('samples/philharmonia-all/cello', match=['_1_', 'arco-normal'], release=0.4))
```

**inst.kit(source, map=None, ...)** - `source`: a folder (searched recursively; folder names count as hints:
tidal-style `bd/ sd/ hh/ oh/ cp/ cr/ lt/ mt/ ht`), a Hydrogen kit (folder with `drumkit.xml`), a DrumGizmo kit (its
folder or kit `.xml`), or a list of WAV files.
* Names -> roles -> GM keys: kick / bd / bass drum 36 (variants 35, then spare keys), snare / sd 38 (40), rim / side
  stick 37 (with both: side stick 37, rimshot 40), clap 39, closed / pedal / open hat 42 / 44 / 46 (half-open: a spare
  key; the hats choke each other), toms 41 43 45 47 48 50 (ordered by floor / low / mid / high in the name, else by
  measured pitch; missing tom keys get the nearest tom retuned), crash 49 (57), ride 51 (59), ride bell 53, china 52,
  splash 55, tambourine 54, cowbell 56, bongos 60 / 61, congas 62-64, timbales 65 / 66, agogo 67 / 68, cabasa 69,
  maracas 70, claves 75, woodblock 76 / 77, triangle 80 / 81, shaker 82 ... Run-together machine names are read too
  (`CR8KBASS`, `KPRCLHH`, `DR110CHT`, `chhl`, `tomhh`); words every file of a folder shares (`80PD_KitA-`, `TR 808`)
  name the kit, not the drum. Unrecognized files go to spare keys 88+ and are listed (`info['unmapped']`), loops /
  beats / fills are skipped and listed (`info['skipped']`): nothing disappears silently. `extras=False` keeps only
  the GM keys.
* Velocity layers from the names (`v1..v16`, `vl1..vl16`, `vel`, `pp p mp mf f ff`, `soft medium hard`, `ghost
  accent`, Italian `pianissimo .. fortissimo`), round robins from `rr1`, `take2`, `hit3`. Numbered files of one name
  (`Kick-01..08`, or hit indices in front: `1-Snare .. 56-Snare`) are measured: hits at natural, rising levels (a wide
  loudness and peak spread) become velocity layers ordered by loudness with round robins among near-equal ones;
  4+ takes of an acoustic drum at uneven natural peaks are one drum when they sound alike (body pitch, decay,
  brightness), whatever their level and length; normalized collections (`TR 808 Kick 01 / 02 / 03`, most peaks at
  the same level) are different sounds (variants), unless two are near-identical takes (then they alternate).
  Override with `numbered='variants' | 'layers' | 'rr' | 'random'`. `snares on / off` in a name is the snare wires'
  state, not the drum (`rack tom - snares off` is a tom). Side stick / cross stick / rim click go on 37, a rimshot on
  40 (`Snare Rimshot`, `SnareRim`); plain `Stick(s)` (sticks clicked together) is percussion.
* Zones: one-shots (`loop 'oneshot'`, `pitchKeytrack 0`), `seqLength/seqPosition` round robins (or `lorand/hirand`
  with `numbered='random'`), `ampVeltrack 0.45` on multi-layer sounds (the samples carry the dynamics), a 0.8 dB /
  4 ct per-hit variation on multi-sample sounds (`humanize=True/False` to force), a 12 ms fade on files that stop
  mid-waveform (no end click), mono (and dual-mono) one-shots panned from the drummer's view (`spread=0..1`,
  default 0.5); real stereo files keep the placement they were recorded with.
* `map=` overrides / extends: keys by GM name (`kick kick2 rim snare snare2 clap hat pedal_hat open_hat tom_lo
  tom_floor_hi tom_mid tom_lowmid tom_hi tom_high crash crash2 ride ride2 ride_bell china splash tamb cowbell
  bongo_hi conga_hi ...`), MIDI number or note name; values: a file name, substring or glob in the folder, a path
  (`'samples/<pack>/...'`, `'./x.wav'`: any file), a list (layers / round robins of one sound), `None` (empty
  key), or `{'files': ..., 'gain': dB, 'tune': ct, 'pan': p, 'choke': n, 'layers': 'auto'|'velocity'|'rr'|'random'}`.
  `gains={'hats': -4, 'cymbals': -3, 'kick': 2}` (dB per role, family `hats` / `cymbals` / `toms`, GM key name,
  alias like `bd` / `ohh`, or MIDI key; an unknown name is an error).
  `fill=False` leaves missing keys empty. Other keywords are sampler params (`level`, `velsens`, `tune`, `width`...).
  The key names of a kit: `instrument.info['kit']['names']`.
* **Hydrogen** kits: every instrument's layers (min / max velocity, gain, pitch), volume, pan, mute groups (-> choke);
  layers with the same range alternate. **DrumGizmo** kits: each hit is one multichannel WAV (a channel per
  microphone) with a `power`; hits become velocity layers (power bands ~2.5 dB) with round robins, the kit's
  `Midimap*.xml` gives the keys, `group="hihat"` chokes. The microphones are mixed into stereo at load time by the
  zone field `channels` (no derived files): room and overhead pairs hard left / right, close mics panned where their
  drum sits; `mics={'room': -6, 'overheads': -2, 'close': 0, 'kick': 2, 'SnareBottom': None}` sets dB per group
  (`all close overheads room kick snare hihat toms ride cymbals`) or channel name (None = muted). `kit='basic'` picks
  one of several kit files (an error on other kinds). A pack that ships its own `.sfz` gets a note in
  `info['notes']` / the `kit` command: multi-microphone one-shot folders (a `kick/ sn/ oh/` folder per mic) map
  better through `inst.sfz`.

**inst.organ(source, stops=[...], manual=None, tremulant=False, release=True, stereo='asis', extend='octave')** - a
GrandOrgue sample set (the unpacked `.orgue`: a `.organ` definition + pipe WAVs, usually WavPack-compressed: the
engine decodes them). Each pipe: attack + sustain loop (the file's `smpl` loop) up to its release marker (cue), and
the recorded release as a `trigger 'release'` zone (the decay into the church; definitions with several releases
per pipe by key-press time - 'MultipleReleases' - play the one for held notes); ranks, borrowed (`REF:`) pipes,
per-stop / per-pipe levels and tunings are applied. Stops layer (a registration); names ignore case, accents and foot
marks (`'Rorflojt 4'` finds `Rörflöjt 4'`), `'pedal: Subbas 16'` or `manual=` picks the manual (a name on several
manuals: the first that is not the pedal). `tremulant=True` (or a depth factor) adds the wind tremulant (rate and
depth from the definition). `stereo`: `'asis'` (the recording), `'flip'` (right channel inverted), `'left'` /
`'right'` (one microphone on both sides: mono), or per stop `{'Subbas 16': 'left'}` (the others as recorded). The
Lars Palo sets use a spaced microphone pair: the phase between the channels changes from pipe to pipe (measured on
Burea: from +0.99 to -0.99 correlation within one stop), so some low pipes thin out in mono whatever the polarity -
keep manual stops `'asis'` and put pedal / bass stops on `'left'` (solid in mono; the report's low-end correlation
1.0). `extend`: notes
outside a stop's compass play the pipe an octave inside (`'octave'`), transposed (`'stretch'`) or not (`'none'`).
`expression` is the swell pedal. `python -m agentsound kit <organ folder>` lists manuals and stops.

**inst.multisample(source, octave=0, loop='auto', match=None, root=None, keys=None)** - note-named samples (`Pad
C3.wav`, `Str_F#2`, `bass_A1_forte`, `060-C`): each file on its root key, spread to the keys between its neighbours,
velocity layers / round robins from the names. `match` keeps one articulation / length of a folder that mixes
them; `octave=1` for packs that call middle C `C3`; `root='A3'` puts files without a note in the name on a key
(one sample over the keyboard: Fairlight voices); `loop='pingpong', loop_start=, loop_end=` (frames) sustain
samples without loops.

Library patches built this way (lazy: a missing pack fails at use with its fetch command): drum machines
`sampled/linndrum tr808 tr909 tr707 dmx drumtraks`, 80s `sampled/80s_pop_kit 80s_gated_kit`, acoustic
`sampled/studio_kit room_kit forzee_kit pacific_kit`, Fairlight CMI `sampled/fairlight_orch5 fairlight_choir
fairlight_aahs fairlight_strings fairlight_brass`, organ `sampled/church_organ church_organ_full church_organ_flutes
organ_pedal` (agentsound/patches/sampled_kits.py, sampled_synths.py).

## Vocoder and speech (robot voices, no singer)

The 80s robot voice (Kraftwerk, Daft Punk, The Midnight, Zapp's talkbox): the engine's `vocoder` effect shapes a
**carrier** - the track it sits on: chords, a pad, a saw lead - with the spectrum of a **modulator** - its
`sidechain`: a speech track. The vocoder *sings the carrier's notes* (chords on the carrier = a robot choir, a
melody = a robot lead singer) while the speech gives the *words*, their rhythm and consonants. The speech is
Windows text-to-speech through `agentsound.speech` (no downloads).

```python
from agentsound import speech
vox = speech.words(['neon lights', 'city nights', 'midnight', 'drive'], voice='zira', rate=-2)
voice = s.track('voice', vox.instrument())                  # one-shot sampler: word i on key C2 + i
voice.play(vox.clip({0: 'neon lights', 4: 'city nights', 8: 'midnight', 10: 'drive'}, length=16), verse)
choir = s.track('choir', 'synthwave/vocoder_choir')         # carrier: bright pad + vocoder (its fx.0)
choir.loop(prog.block(voicing='spread', register=('A2', 'E5')), verse)   # the notes the robot sings
speech.vocode(choir, voice)                                 # key the vocoder with the voice, mute the voice
b = verse.bar(2, 2) + 0.4                                   # 'drive' + 0.4 beats: inside its vowel
choir.automate('fx.vocoder.hold', [(b - 1, 0), (b, 1, 'step'), (b + 5, 0, 'step')])     # freeze the vowel
```

Complete example: `songs/_demo_vocoder/song.py` (choir + talkbox answering, 16 bars).

* **Routing**: the voice track is only the modulator. `speech.vocode(carrier, voice, mute=True, **params)` keys
  every `vocoder` in the carrier's chain with the voice (or appends `fx.vocoder(**params)`; params also update the
  existing vocoders, e.g. `shift=-4`, `mode='lpc'`) and mutes the voice: a muted track still renders and feeds
  sidechains, but is not in the mix and not analysed (RENDER_FORMAT "Mute"). One voice can key several carriers
  (a choir and a talkbox); a vocoder without a sidechain is an engine error.
* **Patches** (`agentsound/patches/vocoder.py`, -18 LUFS vocoded on their audition): `synthwave/vocoder_choir`
  (5-voice unison saw pad, 20-band classic vocoder, formants -2 st, bands spread in stereo, Juno chorus: chords),
  `synthwave/vocoder_lead` (detuned saw, mono legato + glide, 24 bands: one note per syllable, A3-A4),
  `synthwave/talkbox` (saw + pulse, LPC mode, tube drive, delayed vibrato: G3-G4 melodies with slides).
  `python -m agentsound audition synthwave/talkbox` speaks a line through it.
* **Words** `speech.words(items, voice=None, rate=0, volume=100, root='C2', cache_dir=None)` -> `Words`: every
  entry (a word or a phrase) spoken once, on its own key (`vox['drive']` -> MIDI key), one-shot; `vox.seconds[w]`,
  `vox.beats(w, tempo)` (plan melodies), `vox.zones()`, `vox.instrument(**sampler_params)`,
  `vox.clip({beat: word} | [(beat, word[, vel])], length=None, vel=127, tempo=None)` -> a Clip. A word starts
  10-30 ms after its note (silence trimmed); velocity 127 = the calibrated level (100 = -4 dB quieter robot).
  `speech.phrase(text, root='C4', ...)` -> one sampler zone (`inst.sampler(zones=[...], oneshot='on')`).
* **Timing**: a word is one sample, so the robot says it at its own speed (`rate=-10..10`; -2..-4 = clearer,
  more robotic). For a sung line put one carrier note per syllable (`vox.seconds` / the syllables' timing), or let
  a legato carrier (vocoder_lead, talkbox) glide under the word; for a choir hold the chord under the whole word.
  Separate words give the rhythm: fire them on beats like drum hits.
* **speak**(`text, path=None, voice=None, rate=0, volume=100, ssml=None, cache_dir=None`) -> Path: `ssml=True`
  (text is SSML: `<prosody>`, `<break time="200ms"/>`, `<emphasis>`) or an SSML string. `voice`: a name or a unique
  part of it (`'zira'`, `'onecore:Stefan'`, `'sapi:hedda'`; `speech.voices()` / `python -m agentsound voices`
  lists them: the SAPI desktop voices and, through PowerShell's WinRT bridge, the newer OneCore voices, which win
  when both engines have the name). Every result is trimmed, normalised to -18 dBFS active speech level (what the
  vocoder is calibrated for) and **cached by a hash** of text / SSML / voice / rate / volume in
  `<song folder>/samples/speech/<text>-<hash>.wav`: re-renders never call the synthesiser again and work without
  Windows - commit those WAVs with the song. Without Windows and without the cached file: `SpeechError` (a
  ComposeError). A German voice speaking English gives the Kraftwerk accent.
* **The vocoder** (`python -m agentsound params vocoder`): `mode` `classic` (analog channel vocoder: `bands`
  8-40 over `lo`..`hi` Hz, `bandwidth`) or `lpc` (talkbox: a running vocal-tract model filters the carrier -
  smoother, the most intelligible, `order`); both: `attack` / `release` (ms: 15-25 intelligible, 100+ smeared
  pads), `shift` (formants, st: -3..-6 bigger / deeper robot, +3..+6 small), `emphasis` (treble lift, dB/oct),
  `flatten` (evens out the carrier's own spectrum so any carrier speaks clearly; 0 = its own timbre), `unvoiced`
  (noise for 's' 'f' 't' while the voice is unvoiced: consonants on dark carriers), `sibilance` (the voice's own
  highs on those sounds), `gate` (dBFS), `hold` (automatable freeze: the robot 'aaah'), `width` (classic: bands
  alternate left/right), `mix`, `output`. The output follows both: silent while the voice pauses, silent without
  carrier notes, about the carrier's loudness while it talks. Zero latency.
* **Tips**: bright carriers (saws, open filters) speak best; chords with 3-5 notes in C3-C5 give a full robot choir;
  a single high note speaks worse than a low one (fewer harmonics to shape); keep the modulator free of reverb (put
  the reverb after the vocoder, on the carrier or a send); `shift` -2..-4 on a female voice makes a male robot.
  Any track can be the modulator: `speech.vocode(pad, kit, mute=False)` makes a pad talk in the drums' rhythm (keep
  the kit audible with `mute=False`; the unvoiced noise turns the hats into breathy ticks).
* **How intelligible** (measured while tuning the defaults, Windows TTS phrases): STOI-style intelligibility ~0.85
  on sustained saw chords / notes (the dry carrier alone scores 0.45, the voice itself 1.0), band envelopes following
  the voice with correlation > 0.9 (`tests/test_vocoder.cpp`), and the Windows speech recogniser picks the right one
  of 8 vocoded German phrases 8 of 8 times in both modes (LPC with the highest confidence); 12 bands or `flatten=0`
  on a dark pad drop to 0-2 of 8.

### Realistic performance (`agentsound.articulation`)

A sampled violin, sax or drummer sounds *triggered* when every note re-attacks from the velocity layer its velocity
picks, in one articulation, at a frozen dynamic. The sampler plays them *played* instead:

| what | how | engine |
|---|---|---|
| **live dynamics** | automate `instrument.dynamics` 0..1 (the mod wheel of sample libraries) | SFZ CC crossfades / gain / cutoff on the dynamics controller play live; `layers='dynamics'` turns plain velocity layers into a stack that crossfades while a note sounds (`xfspread` layers each side); `dyntone` opens the tone, `dynrange` the level |
| **legato** | `mono='legato'` + overlapping notes (`art.legato(clip)`, `jazz.horn_line`) | no new attack: library legato zones, else the new sample enters past its attack, crossfaded (`legatotime`) and level-matched to the old note; notes after a rest attack |
| **portamento** | `clip.glide(150, where=art.leaps(5))` (a mark: the compiler steps `instrument.glide` before the note) or automate `glide` | the old note bends to the new pitch, the new one in from the old (`glideshape` linear / ease / fast) |
| **articulations** | `clip.articulate('staccato', span=(8, 12))`, `track.note(.., art='pizz')`, `art.auto_articulate(clip, track)` | keyswitch notes inserted at the note start (never sounding), zones by `swLast`; unused articulations are not loaded |
| **expression** | `art.expression(track, clip, at, shapes)` - `SHAPES`: flat swell cresc dim fp sfz accent, or 'auto' | points on `instrument.dynamics` (a sampler whose dynamics move its level: `art.live_dynamics(track)` - layers='dynamics', `dynrange` > 0 or zones mapped to it) else `instrument.expression`; tied notes continue the line's level |
| **vibrato** | `art.vibrato(track, clip, at, depth=18, rate=5.2, delay=0.35, grow=0.6)` | `instrument.vibrato` (cents) / `vibratorate` (Hz): delayed per long note, runs on through legato; on a stack track (`layered/hero_sax`) every sampler layer gets it (`instrument.layers.<id>.vibrato`, `art.vibrato_prefixes(track)`) |
| **echo throws** | `art.throws(track, clip, at, bus=echo, throw=-8, min_rest=0.75, min_dur=0.5)` | `send.<bus>` rises from the track's static send to `throw` dB on the held last note of every phrase and falls back before the next phrase: the echo answers in the gaps instead of smearing the line |

```python
from agentsound import articulation as art
vln = s.track('violin', 'sampled/solo_violin')                 # sustain / spiccato / pizzicato / tremolo, legato
line = s.motif('1:1/2 3:1/4 5:1/4 | 6:3/4 5:1/4 | ...').clip(octave=5)
art.perform(vln, line, verse)                                  # all of the below in one call, returns the clip played

line = line.articulate('spiccato', span=(16, 24))              # mark first: legato() never ties detached notes
line = art.legato(line, overlap=0.04)                          # tie the phrases -> legato transitions
line = line.glide(160, where=art.leaps(7))                     # portamento into leaps of a 5th or more
line = art.humanize_starts(line, s.tempo, ms=7, late_ms=0)     # a player's timing, note ends kept (overlaps survive)
vln.play(line, verse)
art.expression(vln, line, verse, ['cresc', None, 'swell', ...])  # per-note shapes (None = flat)
art.vibrato(vln, line, verse, depth=22, rate=5.4)
cellos.automate('instrument.dynamics', [(a, 0.08), (a + 8, 1.0, 'smooth'), (a + 15, 0.1, 'smooth')])   # chord swell
```

Details:
* Marks (articulation, glide) live on the notes (a `Note` subclass): `shift`, `transpose`, `velocity`, `gate`,
  `legato`, `humanize`, `swing`, `slice`, `loop` and track grooves keep them; `Clip(...)` / `map` / MIDI effects that
  build new notes drop them. `art.plain(clip)` removes them, `art.articulation_of(n)` / `art.glide_of(n)` read them.
* Articulation names match the instrument's keyswitch labels case-insensitively (exact, then a word / prefix:
  'stac' -> 'Staccato'), or a key number / note name. `art.available(track)` lists them. Unmarked notes play the
  default articulation; notes starting together share one keyswitch (a warning if they ask for different ones).
* Touching notes (one ends where the next starts) are legato on a `mono='legato'` sampler; notes marked detached
  (staccato / spiccato / pizzicato / marcato: `art.detached`) are kept 6 ms apart by the compiler and never tied by
  `art.legato`. `art.bow_changes(clip, bpm, max_seconds=4)` re-attacks long tied lines (bow change / breath).
  Releasing the sounding note while an earlier key is still held (a trill or grace note over a held note) goes
  back to that key with a legato transition (last-note priority). A glide mark needs a note sounding into it (a
  compile warning names glides after a rest or a detached note: they have no effect).
* Keyswitch notes you write yourself (the instrument's keyswitch keys) switch too, and keep their articulation's
  zones from being pruned.
* `auto_articulate`: shorter than `short` beats (default an 8th) and not tied -> staccato / spiccato; velocity >=
  `accent_vel` -> marcato; the rest -> sustain - picked by `ARTICULATION_WORDS` from what the instrument has.
* `jazz.horn_line` on a sampler uses the sampler's vibrato (lanes instead of a pitch-bend LFO), `param='dynamics'`
  puts its swells on `dynamics`, `glide=0.3` marks portamento into leaps inside legato phrases.

## Theory

* `note('F#3')`, `note_name(61)`, `pc('Bb')`, `hz(69)`, `scale('dorian')`, `SCALES`.
* **Key**: `Key('A minor')`, `Key('Am')`, `Key('F# dorian')`, `Key('C', 'lydian')`; modes: major minor dorian
  phrygian lydian mixolydian locrian harmonic_minor melodic_minor phrygian_dominant hungarian_minor
  major_pentatonic minor_pentatonic blues major_blues whole_tone chromatic.
  `.degree(d, octave=4)`, `.step(s)`, `.contains(p)`, `.snap(p)`, `.transpose(p, steps)`, `.notes(lo, hi)`,
  `.chord('iv7')`, `.triad(degree, size=3|4|5)`, `.chords(seventh=False)`, `.prog(...)`, `.motif(...)`.
* **Chord symbols**: `chord('Fmaj7/A')`. Qualities: `'' m dim aug 5 6 m6 69 7 maj7 M7 Δ m7 -7 mMaj7 m7b5 ø dim7 °7
  9 maj9 m9 11 m11 13 maj13 m13 sus2 sus4 7sus4 9sus4 add9 madd9 add11 add2 add4 add6 2 (= sus2) 7alt dom7`,
  alterations `b5 #5 b9 #9 #11 b13`, `no3 no5`, parenthesised `7(b9,#11)`, slash bass `C/E`.
  `.notes(octave)`, `.pcs`, `.bass_note(low='E1')`, `.voice(style, ...)`, `.transpose(n)`, `.over('E')`.
* **Roman numerals** (`key.chord`, progressions): case = quality (`V` major, `v` minor), suffix `°`/`o`/`dim`,
  `ø`, `+`/`aug`, then any extension (`V7`, `iv7`, `bVIImaj7`, `IVadd9`, `Vsus4`); secondary `V7/V`, `vii°/ii`.
  Plain numerals use the key's own scale (A minor: `VI` = F, `VII` = G, `V` = E major), except that a
  diminished / half-diminished `vii` is the leading-tone chord (A minor: `vii°7` = G#dim7, `vii°/iv` = C#dim);
  an explicit `b`/`#` is relative to the major scale of the tonic (C major: `bVII` = Bb; A minor: `bVI` = F too).
* **Progression**: `s.prog('i VI III VII')`, `'i:2 iv:0.5 V7:1.5'` (`:n` bars), `'Am % F G'` (`%` holds the
  previous chord another bar), `r`/`NC` rest, `|` ignored; lists `[('Am', 2), 'F', chord('G7')]`. `+`, `* n`,
  `.transpose()`, `.at(beat)`, `.length` (beats), `.voiced(...)`, `.roots(low)`; generators `.block(**kw)`,
  `.arp(mode, **kw)`, `.bass(style, **kw)`. `PROGRESSIONS` holds common synthwave/pop numerals.
* **Voicing**: `voice(chord, style, octave=4, inversion=0, voices=None, register=None, bass=True)` with styles
  `close open drop2 drop3 spread`; `voice_lead(chords, register=(52, 76), voices=4, bass=False)` picks, chord by
  chord, the voicing with the least total movement (important tones first: root, 3rd, 7th, tensions, 5th last).
  Extra voices may double any chord tone (root preferred, then fifth, then third), so narrow registers work:
  `chords(s.prog('i VI'), register=(55, 76))` voices F as A3 F4 A4 C5 after A3 E4 A4 C5.
  The jazz styles (`rootless rootless_a rootless_b shell shell37 shell73 quartal sowhat ust`, see Jazz) work in
  `voice()`, `Progression.voiced()` and `chords(prog, voicing='rootless', register=('C3', 'C5'))` too.
* Jazz symbols: `Cø9` (= Cm9b5), bare tensions in parentheses `Cm7(11)`, `C7(13)`, `C7(b9,#11)`; roman numerals
  may repeat the minor sign: `iim7b5`, `ivm7`, `im(maj7)`. `C11` is read as C9sus4 by the jazz voicings.

### Voicing and voice leading (`agentsound.voicing`)

Real parts for chorales, choirs, string and wind choirs and orchestral tuttis, voiced around the lines written by
hand (`voice_lead` above voices a pad; this voices independent parts and checks them). Pitches are MIDI numbers,
times beats; parts are `{voice: [(start, dur, pitch)]}`.

```python
from agentsound import voicing as vc
table = [(2, 'Cm', 'G5', 'C3'), (2, 'Fm/Ab', None, 'Ab2'), (1, 'G7', 'F5', 'G2', {'violas': 'D4'}), (1, 'Cm', 'Eb5', 'C3')]
strings = vc.chorale(table, sec.start, voices=vc.STRINGS, key='C minor', tie=True)   # top / bass fixed, rest voiced
winds = vc.chorale(table, sec.start, voices=vc.WINDS8, key='C minor')                # 8 interlocked wind parts
steps = [{'chord': 'G7', 'fixed': {'S': 'F5'}, 'active': ('S', 'A', 'T'), 'avoid': [71], 'lt': 11}, ...]
vc.voice(steps, voices=vc.SATB, key='C minor', prev={...})                        # -> [{voice: pitch}] per step
issues = vc.check(strings, vc.timeline(table, sec.start), voices=vc.STRINGS)        # [Issue(kind, beat, voices, ...)]
print(vc.summary(issues))                                                          # 'clash 1, parallel_5th 2' / 'clean'
```

| call | does |
|---|---|
| `voice(steps, *, voices=SATB, lt=None, key=None, prev=None, center=None, spacing=12, bass_gap=19, leap=None, unison=False)` | per step (`chord`, `fixed` {voice: pitch}, `active` voices, `avoid` pitches, `lt`) the free voices: chord tones in range, strictly descending (no crossing / unison), adjacent upper voices <= `spacing` apart (the bass <= `bass_gap`), complete chords (3rd, 7th, root, 5th), the leading tone (`lt` pc or from `key`) and the 7th never doubled, big sets double the root first, the free bass on the chord's bass, the smallest motion (leaps > 5th / > 8ve cost), no parallel 5ths / 8ves between any moving voices, no free voice a semitone (or whole tone) from `avoid`. Sets with more than four free voices search `leap` (default 9) semitones around the previous pitches (wider when nothing fits); `unison=True` lets neighbouring voices share a pitch (orchestral doublings: WINDS8 and TUTTI in a narrow span need it), never crossing |
| `chorale(table, t0=0, *, voices=, key=, lt=, prev=, tie=False, active=None, center=None, spacing=, bass_gap=, leap=, unison=False)` | homophonic writing from `(dur, chord, top, bass[, {voice: pitch}])` rows (None = free; chord None = a rest) -> parts in the table's rhythm; `tie=True` holds repeated pitches |
| `satb(steps, ...)` | `voice()` with the SATB set (or `ranges=` with the same names) |
| `check(parts, harmony=None, *, voices=None, order=None, strong=1.0, t0=0, clashes=True, span=None)` | parallel 5ths / 8ves (also compound, also non-adjacent voices) between EVERY pair, semitone clashes (m2 / M7 / m9) at each onset, strong-beat non-chord tones vs a `[(start, dur, chord)]` timeline, notes out of range and crossings (with `voices`) -> `[Issue]`; advice: written suspensions show as non-chord tones on purpose |
| `arpeggiate(parts, free, harmony, t0, *, voices=, until=None)`, `passing_eighths(parts, free, t0, key_at, *, order=, until=None)` | counterpoint for a fugue's free voices (`free` = {(voice, round(start, 4))}): a chord-tone leap on the last beat of a long note, passing 8ths between notes a 3rd / 4th apart (`key_at` a key or a function beat -> (scale pcs, tonic, leading tone)) - only where no parallels or semitone rubs result; edit `parts` in place |
| `line('C5:1 r:.5 Eb5:.5 \| ...', t0, shift)`, `length(spec)`, `timeline(table, t0)`, `harmony_at(harm, t)`, `merge_ties(notes)`, `info(sym)` (`ChordInfo`: root, bass, third, fifth, seventh, major, dim7), `leading_tone(key)`, `parallel_or_rub(parts, v, seq)` | notation and chord helpers |

Voice sets (ordered top to bottom, `{name: (lo, hi[, centre])}`, any dict works): `SATB`, `STRINGS` (violins I / II,
violas, cellos; the basses double the cellos an octave down), `WINDS` (fl ob cl bn), `WINDS8` (fl1 fl2 ob1 ob2 cl1 cl2
bn1 bn2, the Classical wind choir interlocked), `HORNS` (4), `BRASS` (2 tp, 2 hn, tb), `TUTTI` (8 voices, C7 down to the
basses' E1).

## Patterns (all return a Clip)

**Clip** = immutable notes `(start, dur, pitch, vel)` + `length`. `Clip([(0, 1, 'A4', 100), ...], length=4)`,
`Clip.rest(4)`. Combine: `a + b` (sequence), `a | b` (layer), `a * 4` (repeat). Transforms: `shift transpose octave
transpose_scale(steps, key) slice(start, end) repeat loop(length) stretch reverse velocity(f) with_vel gate(f)
legato(overlap=0.02) only(*pitches) without filter map fit(prog, key)`, feel `humanize swing groove crescendo accent`
and the MIDI effects below. `lead | lead.transpose_scale(-2, key)` doubles a line in diatonic thirds;
`line.fit(prog, key)` moves strong-beat notes onto chord tones and snaps the rest to the key. `legato()` extends
every note to the next onset plus a 0.02-beat overlap so mono / `mode='legato'` synths glide (the engine plays
note-ons before note-offs at the same sample, so `legato(0)` - notes touching - is legato too).

**Drum grids**: one character per step (default `step='1/16'`): `X` accent (118), `x` hit (100), `o` ghost (62),
`1`-`9` level (14..126), `.`/`-` rest, `_` hold, spaces and `|` ignored; `vel=` scales every level. Voices: `kick snare clap rim hat pedal ohh tom_lo
tom_mid tom_hi crash ride tamb cowbell` (+ short aliases `bd sd cp hh oh ...`) or MIDI numbers. Shorter voices
repeat to the longest; `bars=` forces the length; `vel=` scales.

```python
drums({'kick': 'x...x...x...x...', 'clap': '....X.......X...', 'hat': '..x.'})
drums('''kick: x..x..x.x...x...
         snare: ....x.......x..o''', step='1/16')
grid('x.x_x...', 'A2')                 # pitched rhythm, '_' holds; pitch may be a list (stab)
euclid(5, 16) -> 'x..x..x..x..x...'    # Bjorklund; rotate=
```

**arp**(`chords, mode='up', rate='1/16', octaves=1, gate=0.6, vel=92, accent=1.15, register=(57, 76),
voices=None, pattern=None, seed=0, restart=True`): modes `up down updown downup converge diverge pinky thumb
random`; `pattern=[0, 2, 1, 3, None]` indexes the sorted chord tones (wraps by octaves, None = rest). Chord tones
are voice-led inside `register`. `chords` = Progression, chord symbol, Chord (with `length=`) or a pitch list.

**bassline**(`chords, style='octave', rate=None, low='E1', vel=100, gate=None, accent=1.1, pattern=None`):
styles `root pulse octave fifth offbeat gallop walk arp`; roots (slash bass if any) land in the octave above
`low`. `walk` = quarter-note walking line: root, stepwise chord/scale tones (the progression's key), chromatic
approach to the next root. `pattern='r.oR f_.l'` per step: `r`/`x` root, `o` octave up, `l` octave down, `f` fifth, `t` third,
`s` seventh, uppercase accent, `_` hold, `.` rest (restarts on every chord).

**chords**(`prog, voicing='smooth', register=(52, 76), voices=4, vel=84, gate=1.0, rhythm=None, step='1/8',
strum=0.0, bass=False`): pads (held) or stabs (`rhythm='x..x..x.'`).

**Motif** (degree melody, diatonic transforms): `s.motif('1:1/8 3:1/8 5:1/4 r:1/4 8:1/2')`; tokens
`item[:dur]` with item = degree, `#4`/`b7`, note name `E5` (read at octave=4, so it moves with `.clip(octave=)`),
`r`/`.` rest, `_` hold; suffix `!` accent, `?` ghost;
default `dur=`. Or `[(1, 0.5), ('b7', '1/4'), None]`. `.transpose(steps) .invert(axis) .retrograde() .stretch(f)
.rhythm(durs) .sequence(0, -1, -2) .resolve(degree=1) .vary(seed, amount)`, `+`, `*`, `.clip(octave=4, vel=96,
gate=0.92)`. Question/answer: `m + m.resolve()`.

**melody**(`prog, key, rhythm='x.x.x..x', step='1/8', register=('E4', 'E5'), contour='arch', seed=0`):
seeded chord-aware line (chord tones on beats 1/3 and long notes, stepwise motion, contour
`arch rise fall wave valley flat`) - a starting point to edit.

**Fills**: `snare_roll(length=2, step='1/16', vel=(40, 120), pitch='snare', build=False)`,
`tom_fill(length=1, toms=('tom_hi', 'tom_mid', 'tom_lo'))`, `crash()`. Place with
`kit.play(fill, sec.bar(-1), replace=True)` to replace the groove in that span. Levels: `drums(..., vel=80)` and
`grid(..., vel=)` scale the written levels in percent (100 = as written, 2..200; a 0..1 ratio is an error - the
ratio is `track.play / loop(clip, vel=0.8)`), `crash(vel=)` is a velocity 1..127.

## MIDI effects (transform any Clip)

Write a musical idea once, then transform it - like Ableton's MIDI effects or a hardware arpeggiator. Every
Clip has these methods (also functions `midifx.<name>(clip, ...)`); they are pure (return a new Clip, keep the
length) and chain. Randomness is seeded (`seed=`, default 0: same seed, same notes). "Onset" = the notes that
start together, within 1/32 beat (a chord counts once, humanized chords too).

```python
held = s.prog('i VI III VII').block(voices=3)                   # held chords (or any pad / chord clip)
arps.loop(held.arpeggiate('updown', rate='1/16', octaves=2), verse)            # arp over what is held
held.arpeggiate('up', pattern='x.xx x_x.', accent=1.2)         # rhythm: x hit X accent o ghost . rest _ tie
held.arpeggiate(pattern=[0, 2, 1, 3, None])                    # step order as indices into the held notes
held.arpeggiate('chord', rate='1/8', pattern='x..x..x.')       # rhythmic chord stabs from a pad
pad.loop(held.strum(ms=25, bpm=s.tempo, direction='alternate'), chorus)       # guitar strum, ends kept
hook.harmonize('3rd', key=s.key)                               # + diatonic thirds (A minor: A->C, E->G, G->B)
hook.echo(times=3, delay='1/8.', decay=0.6, transpose=2, key=s.key)           # MIDI delay climbing in thirds
bass.chordify('7th', key=s.key, voicing='spread')              # every note -> the diatonic 7th chord on it
beat.ratchet(3, where=lambda n: n.pitch == 42 and n.start >= 3.5)             # hat roll at the bar end
line.quantize('1/16', strength=0.8, swing=0.58).scale_quantize(s.key).fold('A3', 'A5')
beat.chance(0.9, seed=2).vel_pattern([1.15, 0.8, 1, 0.8], grid='1/16')       # sparse, accented variation
```

| method | does |
|---|---|
| `arpeggiate(mode='up', rate='1/16', octaves=1, gate=0.7, pattern=None, latch=False, vel=None, accent=None, retrigger=True, seed=0)` | a clock ticks every `rate`; each step plays the next of the notes **held** at that moment, so every chord region is arpeggiated for as long as it is held and chord changes are picked up on the next step. Modes `up down updown downup converge diverge pinky thumb random order` (as played) `chord` (all held notes per step) `pattern`. `pattern=[0, 2, None, -1]`: indices into the sorted, octave-extended held notes (wrap by octaves, `None` rest); `pattern='x.xX_'`: rhythm locked to the clock (rests don't advance the order, `_` ties: the note holds through the tied steps; a digits-only string is an error - indices go in a list). `retrigger=True` restarts the order when the held notes change or are struck again, `False` keeps counting. `latch=True` keeps playing the last chord through gaps. `vel=None` keeps each held note's velocity; `accent` = factor on the beat or a list of per-step factors |
| `strum(ms=30, direction='down', vel_decay=0.0, *, beats=None, bpm=120)` | offsets the notes of every chord (`down` = low string first, `up`, `alternate`) by `ms` each (at `bpm`; or `beats=0.03` / `'1/64'`), keeping their ends; `vel_decay` softens later strings |
| `ratchet(n=2, where=None, gate=0.9, vel_decay=0.0)` | splits notes into `n` repeats inside their length (rolls). `where`: predicate `lambda n: ...`, onset pattern `'...x'` (digits = repeat count: `'..3.4'`) or pitches (`'hat'`, `['snare', 'clap']`); `vel_decay < 0` = crescendo roll |
| `echo(times=3, delay='1/8.', decay=0.6, transpose=0, gate=None, key=None, wrap=False)` | MIDI delay: repeats `delay` apart, velocity × `decay` each (dropped below 1); `transpose` per repeat in semitones, or in scale steps with `key=`; `gate=None` keeps the length (≤ the delay), else `gate × delay`; `wrap=True` folds repeats past the end to the clip start (seamless loops); a repeat landing on the same pitch at the same time merges (the louder stays) |
| `harmonize('3rd', key=)`, `(['3rd', '5th'], key=)`, `('-6th', key=)`, `(steps=[2], key=)`, `(semitones=[12])`, `vel=0.8` | parallel voices, diatonic (names / steps follow the key; chromatic notes keep their alteration) or chromatic; names `2nd 3rd 4th 5th 6th 7th octave 9th 10th`, `-` prefix or `' below'` = below |
| `chordify(shape='triad', key=None, voicing='close', vel=1.0)` | every note becomes the chord rooted on it: `triad 7th 9th 6th` (diatonic, need `key=`), `add9 open` (diatonic with key, else chromatic), `sus2 sus4` (always a true sus chord: perfect fifth; with `key=` the other sus shape is used where the asked one leaves the key - F in A minor gives Fsus2), `power` (1-5-8), a chord quality for parallel chords (`'m7'`, `'maj9'`, `'7sus4'`) or semitones `(0, 3, 7)`. Voicing `close`, `open` (2nd/4th voice up an octave), `spread` (fifth first, wide) |
| `quantize(grid='1/16', strength=1.0, ends=False, swing=0.0)` | pulls starts (and ends) toward the grid; `strength=0.5` keeps half the feel; `swing` 0 or 0.5..0.8 as in `Clip.swing`. A note just before the clip end may snap onto the end (the next bar's downbeat) |
| `scale_quantize(key, direction='nearest')` | snaps pitches into the key (`nearest` ties go down, `up`, `down`) |
| `chance(p=0.8, seed=0)`, `thin(every=2, offset=0)` | keep each note with probability p / keep every n-th onset (chords stay whole) |
| `fold(low, high)`, `octave_double(12, vel=0.8)` | octave-fold into a register (≥ 11 semitones) / add octave copies (`-12` sub, `24`, `[12, -12]`) |
| `vel_random(amount=10, seed=0)`, `vel_pattern([1.2, 0.8, 1, 0.8], grid=None)` | uniform ±amount / cycled accents per onset (values > 4 are absolute velocities; `grid='1/16'` locks the pattern to grid positions) |
| `staccato(length='1/16')`, `legato(overlap=0.02)`, `gate(f)` | cap note lengths / tie to the next onset / scale lengths |
| `retrograde(rhythm=True)`, `invert(pivot=None, key=None)` | backwards (`rhythm=False`: same rhythm, pitch order reversed) / upside down around a pivot (default the first note), diatonic with `key=` |

`arp(prog, ...)` (Patterns) builds an arp from a progression with voice-led chord tones; `clip.arpeggiate(...)`
arpeggiates whatever a clip holds (your own voicings, a played part, a pad) and keeps its timing.

## Feel

`humanize(clip, timing_ms=4, vel=6, bpm, seed)` (`bpm` may be a function of the beat, e.g. `s.tempo_at`), `jitter`, `vel_jitter`, `swing(clip, 0.58, grid='1/16')`
(0.5 straight .. 0.67 triplet), `crescendo(clip, 0.5, 1.0, curve=1)`, `decrescendo`, `accent(clip, every=1,
amount=1.2)`, `groove(clip, name, bpm, drums=False)`. `GROOVES`: `straight tight laidback (= synthwave: snare/clap
+9 ms, 16th velocity shape, melodic parts +4 ms) push mpc shuffle swing8`; custom `Groove(name, swing, grid,
vel=(...), late_ms, drum_ms={'snare': 9})`. On tracks prefer `track.groove(...)` / `track.humanize(...)`.
Jazz feel (humanize.py, also in `agentsound.jazz`): `swing_ratio(bpm)`, `layback_ms(part, bpm)`, `lay_back(clip, ms,
bpm)`, `jazz_groove(part, bpm, ratio=None, late_ms=None, accent_24=None)`, `backbeat(clip, 1.08)`, `phrases(clip,
gap)`, `phrase_dynamics(clip, ...)`, `touch(clip, lo, hi, ...)` - see Jazz.

## The drummer (`agentsound.drummer`)

A virtual drummer, the pianist's shape for the kit: it plays a whole song FORM - grooves per style and section,
fills into sections, crashes, builds, stops, an ending - with two hands and two feet, a fill BUDGET, drum touch and
per-limb feel. Every drum part of a band song goes through it (or its moves); a looped grid is not a drummer.

```python
from agentsound import drummer
part = drummer.arrange(s, style='rock', density=0.6, seed=3, kit=b.drums)    # the Song: all sections, its tempo
part.play(b.drums)                  # b.drums.play(part.clip, part.start) + the track's own humanize off
print(part.summary(), part.plan, part.budget)                                  # what it played, and why
part = drummer.arrange([verse, chorus, post], bpm=s.tempo, style='pop', kit=b.drums, ending='hit',
                       plan={'verse': {'energy': 0.35, 'ghosts': 0.8}, 'bridge': 'half', 'chorus': 'ride'})
b.drums.play(drummer.tom_run(2, s.tempo, kit=b.drums), verse.bar(-1, 2), replace=True)       # one move
```

`arrange(form, *, bpm=None, style='rock', density=0.5, seed=0, kit=None, plan=None, fill_every=4, flashy_every=8,
same_every=16, crash_every=4, fills=None, feel=None, timing_ms=None, swing=None, ending=None, human=True,
phrase_fills=True, lock=None, lock_mode='with', memory=None, at=None, hands=None)` -> `Performance` (`.clip` from `.start`, `.hits` = every stroke with its
limb / tag / timing offset, `.moves` = [(start, end, 'groove' | 'fill' | 'build' | 'crash' | 'stop' | 'dropout' |
'ending' | 'dropped', name)], `.plan` per section, `.budget`, `.summary()`, `.fills`, `.crashes`, `.play(track,
humanize=False)`). `form`: a Song, a Section, consecutive Sections, or `(name, bars)` pairs (placed at `at=`).
- **Section roles** (`ROLES`, from the name or `plan={'x': {'role': ...}}`): intro 0.38, verse 0.42, pre 0.6,
  chorus 0.88 (+0.04 per repeat), post 0.7, bridge 0.58, solo 0.8, break 0.25, outro 0.72, end 0.85 = the energy:
  levels (verse backbeat ~100, chorus ~120), calm vs busy kick cells, ride / 16ths in the big parts, rimshots, open
  hats. A section's groove = a main cell + a variation in its 4th bar; a repeated section reuses it. The pre-chorus
  BUILDS into the chorus (snare 8ths -> 16ths -> 32nds, the kick on the beats); a break STOPS (the band hit, silence,
  time on the hat); the end section = a big hit and (2+ bars) a tom rumble into the final cut-off (`ending='hit' |
  'roll' | 'groove' | 'choke'` (the hit, the cymbals grabbed a beat later); on another last section 'hit' lands on
  its last bar; ballad / synthpop end on a cymbal swell). `hat_loose` time is a half-open hat (openness 0.45: the
  live-hat lane on Big Rusty / Unruly).
- **Fills** (`FILL_KINDS`: pickup, snare, toms, triplets, flams, linear, roll, build; eighths / slap = jazz brushes)
  into EVERY section (into a chorus a whole bar at density >= 0.45), and with a chance (density) into a new 4- or
  8-bar phrase. The BUDGET (user feedback: spice, not habit): phrase fills at least `fill_every` bars apart, the
  `FLASHY` ones (toms, triplets, flams, linear at 2+ beats; weighted by the energy they lead into) `flashy_every`
  bars apart and one kind `same_every` bars apart - a plainer fill (a snare run, or the groove going on into a
  pickup) takes the place (logged 'dropped'); neighbouring fills avoid each other's kind; now and then
  the bar before a chorus DROPS OUT instead (the hat alone, then a pickup). `Memory()` + `memory=` counts the budget
  over section-by-section calls. Crash with the kick on section downbeats and after fills in the big parts.
- **Styles** (`STYLES`): rock, halftime, shuffle (0.62), pop, funk (16th hats, ghosts, linear fills, 0.54), disco
  (four on the floor, open hats on the &), ballad (side stick verses, laid-back backbeat), motown, synthpop (the 80s
  / outrun machine: tight, 16th hats, clap layer, tom runs), bossa (cross-stick clave, straight), jazz (straight-8th
  ride, or `patterns.brushes` on a brush kit, soft: behind the piano), train. `plan` per section: `role energy time
  mode fill fill_len crash ghosts build stop dropout style side rimshot sweep lock` (strict: an unknown fill kind or
  a non-bool switch is an error), or a shorthand string (a role, a
  `TIMEKEEPERS` name - hat hat8 hat16 hat4 hat_barks hat_loose ride ride_bell bell floor crash snare16 pedal none -,
  `'hat8/half'`, 'half', 'four', a style, 'stop').
- **Limbs**: R (hat / ride / crash, toms), L (snare, ghosts), RF (kick), LF (hat foot). A limb never strikes closer
  than it can (groove 70 ms, rolls 40 ms, kick 80 ms, hat foot 100 ms; one-handed 16th hats only up to ~135 BPM),
  the foot never closes a hat being opened, a crash always has the kick, kick and snare trade places on the
  accented backbeat (no kick under 2 and 4 but in four on the floor; Motown's snare on every beat keeps the kick on 1
  and 3). The limb rules judge the swung strokes. `check(part)` lists violations ([] for what arrange plays).
- **Touch** (by energy): backbeat 80-122, kick 72-114, hat accents on the beats (the & x0.74, 16ths x0.55), ghosts 15-35, hat
  foot 40-64, fills crescendo; a 4-bar phrase arc, the first backbeat of a section leaning in, every stroke a
  little different. **Feel** (`human=True`): the style's push / pull per limb (`feel=` 'on' | 'laid_back' | 'push' |
  a style | {'R': ms, 'L': ms, 'RF': ms, 'LF': ms}: rock's backbeat +3 ms behind the hat), a spread of `timing_ms`
  (rock 6, synthpop 0.8), a slow drift per limb (not on the machine), the crash a hair after its kick, flam graces
  15-25 ms ahead; `swing=` 0.5..0.75 on the style's grid (8ths; funk 16ths) - the subdivisions swing with the
  off-beat (a 16th fill in a 0.62 shuffle: 0, .31, .62, .81), triplets stay. The presets humanize their drum
  track: `part.play(track)` switches that off; a track `groove` still applies on top (the jazz presets' band swing:
  then leave the drummer's `swing=` at 0.5, or the drums swing twice).
  Jazz on sticks stays soft (ride 44-56 before its accents, kick bombs <= 57).
- **Kit** (`Kit.of(track | instrument | 'gm' | 'big_rusty' | 'big_rusty_kit' | 'unruly' | 'unruly_kit' |
  'mf_natural' | 'swirly' | 'gm_brush' | {piece: key})`): pieces kick snare side rimshot edge clap hat hat_shank
  hat_pedal hat_open hat_half hat_splash ride bell ride_crash crash crash2 china splash tamb cowbell crash_choke
  ride_choke china_choke, toms tom1.. (high -> low) and floor (`kit.voices()`: snare + toms, high -> low). The
  `sampled/big_rusty_kit` / `unruly_kit` patches are recognised with their choke keys and their live hi-hat
  (`Kit.live_hat`), MF Natural with its per-hand samples (`Kit.hand_keys`). A sampled kit is read: only keys with
  samples count, tom copies merge (Big Rusty: 4 toms, Unruly: 3, the pop Chart kit: none - its fills stay on the
  snare), a key that only copies another piece's samples is no second piece (Big Rusty's 57 = its 49 crash: no
  doubled crash; the final hit takes the ride crash as its second cymbal), missing pieces fall back (no ride: a
  washy hat; no rimshot: the snare). Every fallback and every left-out piece is a warning (`part.warnings`: "the kit
  has no crash: 18 crash strokes play on hat_open (46) instead"); `part.play(track)` adds them to `s.advice` (repeated
  in `s.warnings` by every compile), plus - for a part arranged for another kit than the track plays (`kit=None`:
  General MIDI) - the strokes landing on keys without samples and the fallback `kit=<track>` would play.
- **Hands**: `hands=` a `Hands` / `HANDS` name (the solo layer's player, below): the fills' strokes get its physics -
  the weaker hand, rebounds, up-strokes, reach (the levels; the style's feel keeps the timing). One drummer through
  a song: the same `Hands` in `arrange()` and `perform()`.
- **Kick and bass**: `lock=b.bass` (the bass Track once it is placed, or a Clip from the part's start): the kick
  locks to the bass - each kick of the groove moves onto the bass note nearest it (within an 8th, never under the
  backbeat, 16th off-beats only in a 16th feel; no bass note near: it drops, beat 1 stays), so kick and bass hit
  together at the style's density - for syncopated funk / pop bass lines; `lock_mode='answer'`: the kick plays in
  the bass's gaps instead (beat 1 together, then they alternate - the low end stays clear).
Named MOVES (each a Clip from `at`, keyed for `kit=`, `energy=` 0..1, a few ms of seeded timing): `tom_run(length,
bpm)` (snare then the toms high -> low, crescendo, kick under it), `snare_run`, `triplet_fill`, `flam_fill` (flam
accents down the kit), `linear_fill` (R L K ...: no two limbs together), `pickup(bpm, length=1)`, `roll` (snare
roll crescendo), `build` (8ths -> 16ths -> 32nds), `stop(bpm, length=4)` (band hit + pickup), `dropout`, `swell`
(mallet cymbal roll), `crash_hit`, `open_hat` (open + the foot's chick), `count_in`, `beat(style, bars, bpm,
role=...)` (the groove alone), `brushes` / `ride` (patterns.brushes / ride_pattern on the kit's keys). Reused:
`patterns.snare_roll`, `tom_fill`, `brushes`, `brush_fill`, `ride_pattern`.

### The drum solo: hands, rudiments, feet, solo moves

What `hornist` is for a sax, this layer of `drummer` is for a drummer taking a SOLO: the strokes of two hands and two
feet played like a person plays them, so a sampled kit sounds played, not triggered (HUMAN_FEEDBACK "realism").

```python
from agentsound import drummer
kit = s.track('drums', 'sampled/big_rusty_kit')        # 14 layers x 4 round robins, chokes, a live hi-hat
c = drummer.rudiment('paradiddle', s.tempo, beats=8, kit=kit, orchestrate='split', shape='cresc')
c = drummer.pattern('f>R l l >R@tom1 l r >L@floor+K -', s.tempo, kit=kit, energy=0.8)    # any sticking
motif = drummer.DrumMotif.make(seed=3, cell='x..x..x...x.x...')    # the riff's rhythm as the solo's motif
part = drummer.perform([('time', 4, 0.55), ('motif', 2, 0.45), ('develop', 4, 0.6),
                        ('rudiment', 2, 0.65, {'rudiment': 'flam_accent', 'orchestrate': 'accents'}),
                        ('tom_melody', 2, 0.65), ('three_over_four', 2, 0.75), ('silence', 1),
                        ('gated_toms', 2, 0.9), ('speed_burst', 1, 0.95), ('finish', 2, 1.0)],
                       bpm=s.tempo, kit=kit, at=solo.start, motif=motif, seed=7)
part.play(kit)                       # the clip + the hi-hat openness lane (instrument.dynamics) on a live-hat kit
```

- **The stroke language** (`STROKE_HELP`, `strokes(pattern, grid=0.25, ...)` -> Hits, `pattern(pat, bpm, ...)` ->
  Clip): one token per grid step - `R L` taps, `r l` ghosts, `>R` accent, `^R` rimshot accent, `fR` flam, `dR` drag,
  `zR` buzz stroke, `RR` / `RLR` several strokes in one step (a diddle, a triplet), `K k` kick, `P p` hat foot
  (`P@kick`: the left foot on a double pedal), `@piece` / `@N` (the kit's voices: 0 snare, 1 tom1 ...), `A+B`
  together, `-` rest. `energy` (0..1) is the passage's top level (42 .. 126: a whisper .. fff), `shape` its dynamic ('cresc',
  'decresc', 'build', 'swell', 'wave', (lo, hi), a function), `orchestrate` spreads unmarked strokes over the kit
  (`ORCHESTRATIONS`: snare, toms / around, down / up (a group per drum), split (the lead hand on the floor tom, the
  other on the snare), accents (accents on the toms, taps on the snare), hands, a list, a dict, a function).
- **The hands' physics** (`Hands(lead='R', weak=0.3, tap=0.6, ghost=(18, 32), grace=0.36, height=0.035,
  timing_ms=4, single_ms=70, double_ms=38, foot_ms=85, heel_toe_ms=58, evenness=0.8, reach_ms=55)`, named
  `HANDS`: master, pro (default), rock, student; `perform_hits(hits, bpm)`): the weaker hand softer, later and
  looser; stick heights that wander a little (accents least); the rebound of a double stroke a little under the
  first; an accent right after its own hand's tap loses contrast at speed (the stick has to come up: the Moeller
  problem); a hand crossing the kit faster than its reach lands softer and later; ghosts stay 15-35; flams (the other
  hand 16-28 ms ahead, wider when soft), drags (two graces), buzz strokes (3-6 bounces closing in and dying away);
  micro-timing: each stroke ~0.6 x `timing_ms` (SD) around a slow wander of each limb (+-3 ms beat to beat), the weak
  hand a little late, ghosts looser, accents tighter; loud passages push a hair ahead. `sticking_problems(hits, bpm)` lists what two hands and two feet cannot play
  (a single stroke sooner than `single_ms` after its hand's last, a rebound sooner than `double_ms`, one foot faster
  than heel-toe, one limb on two drums at once); `rudiment()` / `pattern()` raise with the limit.
- **Rudiments** (`RUDIMENTS`: the PAS roll, diddle, flam and drag rudiments - single / double / triple stroke rolls,
  5- to 17-stroke rolls, buzz roll, single / double / triple / inverted paradiddle, paradiddle-diddle, flam, flam
  accent, flam tap, flamacue, flam paradiddle, flammed mill, pataflafla, Swiss army triplet, inverted flam tap, flam
  drag, drag, single / double drag tap, lesson 25, dragadiddle, single / double / triple ratamacue - plus accent grids
  on singles: accent_fours / threes / triplets, moeller_sixes, herta): `rudiment(name, bpm, beats=, grid=, kit=,
  energy=, orchestrate=, shape=, hands=, lead='L', accents=True)`.
- **Feet** (`FEET`, `feet(kind, bars, bpm)` / the ostinato under a solo move): chick (hat foot on 2 and 4), chick4,
  splash, four, clave (kick on the 3-2 son clave), samba, double (16th double bass: both feet on one kick),
  heel_toe, gallop, none; `double_bass(beats, bpm, accents=...)`.
- **Hi-hat openness, chokes**: a hat stroke's `open` (0 closed .. 1 open; pieces `hat`, `hat_half` 0.55,
  `hat_open` 1). On a kit whose variable hat opens by the live `dynamics` param (`Kit.live_hat`: Big Rusty and
  Unruly, their SFZ CC4 imported live) every stroke's openness is a step in `instrument.dynamics`
  (`hat_lane(hits, kit, bpm)`; `Performance.lanes`, written by `part.play(track)`), elsewhere the openness picks the
  closed / half / open sample. `hat_dance(beats, bpm)` plays the hat as a voice. Chokes: pieces `crash_choke`,
  `ride_choke`, `china_choke` (the kits' choke keys: `big_rusty_kit` 88 / 89 / 90, `unruly_kit` 88 / 89,
  `mf_natural` 58), `choke(bpm, piece='crash', after=1)` (a hit grabbed `after` beats later), `arrange(...,
  ending='choke')`. Per-hand samples: `Kit.hand_keys` ({key: {'R': key}}: MF Natural's snare / toms recorded per
  hand - each hand plays its own).
- **Re-strike damping** (the sampler's `restrike`, dB): a drum head or cymbal struck again is touched by the stick,
  so its old vibration does not stay on top of the new one. Sampled, every hit layers fully - a 16th-note run on one
  drum piles up ~5-7 dB of ring; `restrike=6` keeps it near one hit. Set it on a solo kit:
  `s.track('drums', patches.get('sampled/big_rusty_kit').but(restrike=6))` (drum kits 4-9; default 0 = off).
- **The solo moves** (`SOLO_MOVES`: name -> fn(SoloContext) -> Hits, its feet, `spice` (a showpiece), energy,
  density, natural length): time (the groove dissolving as the band drops out), hat_dance, motif (the `DrumMotif`
  stated, repeated with a touch), develop (the motif varied bar by bar: `MOTIF_VARIATIONS` orchestrate, answer,
  displace, flams, diminish, augment, fill, kick, fragment, rimshots, invert, sparse, climb), rudiment (orchestrated:
  paradiddles split, flam accents on the toms, six-stroke rolls down the kit ...), flam_toms, tom_melody (the toms as
  a melody: called on the snare, answered on the toms, its dynamics from `humanize.touch` with the toms as pitches),
  call_response (snare calls, toms answer), three_over_four (dotted-8th accents around the toms over 16th ghosts),
  fives (16ths in groups of five across the bar line), quintuplets, half_double (half-time into double-time), linear
  (R L K / R L L K / R L R K K figures), bonham (hand-hand-foot 16th triplets around the toms, original pattern),
  speed_burst (the fastest singles the hands can play at the tempo), buzz (a press roll pp -> ff), double_bass,
  gated_toms (an 80s tom break in that spirit, original figure: send the toms to `bus/gated` for its span - its
  window is in `part.moves`), silence (the drummer stops), swell (a cymbal roll; on `sampled/big_rusty_mallets`
  soft mallets), finish (unison hits, a gap, a run around the whole kit into the band's 1; `choke=True`), hit_choke.
  `perform(steps, bpm=, kit=, at=, hands=, seed=, motif=, feet=)` plays them in YOUR order (steps `(move, bars[,
  energy[, opts]])` or dicts with the move's opts) -> a Performance (`.moves` = (start, end, 'solo', name)); give the
  steps an arc (soft start, build, climax), never one level. `solo_move(name, beats, bpm, ...)` is one move as a
  Clip. The arc, the motif development and the budget across a solo belong to `soloist.solo()` (the instrument-
  agnostic solo wrapper), which plays the drummer's moves through `drummer.vocabulary()`.
- **With the soloist** (`drummer.vocabulary(kit, hands=None, moves=None, feet=None, opts=None, budget=None)` ->
  `soloist.Vocabulary`): one `soloist.Move` per solo move (`SOLO_ROLES`: where it fits in the arc - motif, answer,
  develop, burst, climax, resolve; spice / fast as above; the finish a rare cue), each slot played by the hands'
  physics on the kit, the hi-hat lane carried as the Part's steps; the motif is any Clip - the song's riff or hook:
  `DrumMotif.from_clip(clip, kit=)` takes its rhythm (16ths or triplets) and accents (the loudest notes), a drum clip
  keeps its drums - and `DrumMotif.to_clip(kit)` turns one back into notes; `vary` picks the stage's
  `MOTIF_VARIATIONS`; `place` writes the notes and the hat lane (the track's humanize off); `touch=False` (the
  drummer shapes its own dynamics). `soloist.solo(s, kit, drummer.vocabulary(kit, hands='master'), at=solo,
  motif=riff, arc='build', seed=7)`.

## Automation

`node.automate(target, *point_lists)`; targets: `instrument.<param>`, `fx.<index|type|name>.<param>`
(resolved at compile, so inserting effects later is safe; ambiguous types need an index or `name=`), `gainDb`,
`pan`, `send.<bus>`. **`gainDb` values are dB on the node's `gain_db`** (its level as set: yours, a patch's, a band
preset's for its role): `automate('gainDb', [(0, 0), (solo.start, 2, 'smooth')])` = "as set, +2 dB from the solo",
`fade(a, b, 0, -60)` fades out from wherever the fader is; the same for modulators on `gainDb` (base / min / max /
steps values; the base defaults to the fader). The compose layer adds `gain_db` at compile (the render format's
lanes are absolute); a lane holds its first value before it and its last after it. Points `(beat, value[, curve])`,
curve `linear exp smooth step` shaping the segment arriving at the point (`exp` needs positive values: use it for
Hz). Calls on one target merge; points on the same beat become an instant jump, to the `step` point (start of
`hold`/`steps`/`per_section`, `riser` reset) if there is one, else to the point listed later.

Generators (positions may be Sections): `ramp(a, b, v0, v1, curve)`, `exp_ramp`, `smooth_ramp`, `hold(a, b, v)`,
`steps({beat: v})`, `per_section({intro: 0.2, chorus: 0.6}, glide=2)`, `swell(a, b, lo, hi)`,
`riser(drop, length=8, lo=200, hi=12000, reset=None)`, `fade(a, b, -60, 0)` (for `gainDb`),
`lfo(a, b, lo, hi, period='1/4', shape='sine|tri|saw|saw_down|square', log=False)` (drawn as points; for
anything periodic prefer the `lfo('sine', ...)` *modulator* below: exact, cheaper, automatable depth).
`steps(...)` and `lfo(...)` are the same names as the modulator generators: a dict / positions make points,
a list / a shape name make a modulator.

## Modulation ("parameters are instruments too")

`node.modulate(target, *mods, window=None)` drives a target continuously during the render (the engine
evaluates it every 32 samples, locked to the song's beat grid, also in `--section` previews). Targets are the
automation targets (`instrument.<p>`, `fx.<index|type|name>.<p>`, `gainDb`, `pan`, `send.<bus>`).

```python
lead.modulate('instrument.cutoff', lfo('sine', rate='1/4', min=600, max=4000, curve='exp'))   # wobble
pad.modulate('gainDb', gate('x.x.xx.x.x.xx.x.', rate='1/16', depth=18), window=chorus)       # trance gate
bass.modulate('instrument.cutoff', follow(kit, pitches='kick', min=300, max=2500, curve='exp'))  # kick opens it
arp.modulate('instrument.cutoff', steps([400, 2400, 800, 3200], rate='1/16', glide=0.3, curve='exp'))
arp.modulate('instrument.cutoff', envelope(decay='1/8', min=600, max=6000, curve='exp'))      # per-note pluck
pad.modulate('gainDb', envelope(decay='1/4', trigger=kit, pitches='kick', depth=-10))         # kick pump
pad.modulate('pan', lfo('triangle', rate='2 bars', depth=0.6), window=(chorus.start, chorus.end))
lead.modulate('instrument.osc2.fine', sample_hold('1 bar', smooth=1, depth=4, base=7))        # analog drift
bass.modulate('instrument.cutoff', lfo('sine', rate='1/8', depth=ramp(drop.start, drop.end, 0, 2), curve='exp'))
```

**Mapping** (every generator takes one of the two):

| | |
|---|---|
| `min=, max=` | absolute: the source sweeps the target between min and max (`curve='exp'`: geometrically, for Hz; min > max inverts). `steps()` without min/max takes target values directly |
| `depth=` | offset: `source × depth` is added to the target's automation lane, or to `base=`. Sources are bipolar (−1..1: `lfo`, `steps`, `gate`, `sample_hold`) or unipolar (0..1: `follow`, `envelope`). With `curve='exp'` depth is in **octaves** (value × 2^(source × depth)) — the natural unit for cutoffs |
| `base=` | the centre value when the target is not automated. Filled in automatically for `gainDb` / `pan` / sends and for params set explicitly on the sound (`inst.va(cutoff=2200)`, fx params); otherwise give it (or automate the target). Not allowed next to an automation lane (the lane is the base) |

**Generators** (rates: `'1/16'`, `'1/8.'`, `'1/8t'`, `'1/4'`, `'1 bar'`, `'2 bars'`, `'1/2 bar'`, `'3 beats'`, a
number of beats, or for `lfo` only `'5hz'`):

| call | source |
|---|---|
| `lfo(shape='sine', rate='1/4', *, min/max \| depth, base, curve, phase=0, retrigger=False, name)` | shapes `sine` `triangle` (`tri`) `saw` (falls; `saw_down`) `ramp` (rises; `saw_up` - note the points-`lfo(a, b, ...)` calls the rising one `saw`: say `saw_up` / `saw_down` to be unambiguous) `square` `random` (S&H per cycle) `smoothrandom`. Phase 0 = cycle start: sine/triangle start at their minimum and peak mid-cycle; square is high first. `retrigger=True` restarts on each note of the track |
| `steps(values, rate='1/16', *, glide=0, loop=True, depth, base, curve, name)` | step sequencer from the window start (or beat 0); `glide` = fraction of each step spent gliding in |
| `gate(pattern, rate='1/16', *, depth=24, glide=0, base, curve, name)` | trance gate: `x` open, `.` closed (−depth), `0`-`9` partly open, `_` repeat, spaces/`\|` ignored. Any target: `gate('x..x', depth=2, curve='exp')` on a cutoff |
| `follow(node, *, attack=5, release=120, gain_db=0, pitches=None, min/max \| depth, ...)` | envelope follower of a track/bus (post-fader level, ms times; 0 silent .. 1 full scale). `pitches='kick'` follows only those notes (muted key track) |
| `envelope(attack=0, decay='1/8', sustain=0, release=None, *, trigger=None, pitches=None, ...)` | linear ADSR in beats/note values, restarted by each note of this track or of `trigger=` (with `pitches=`); `release=None` = decay |
| `sample_hold(rate='1/16', *, smooth=0, min/max \| depth, ...)` | seeded random steps (song seed: deterministic); `smooth=1` = continuous drift |

**Windows**: `window=chorus` (its span), `window=(start, end)` (beats or Sections = their start; `None` = open).
Tempo-grid sources count from the window start. Outside the window the lane / base / static value applies.

**Stacking and automating modulators**: several modulators on one target apply in order — absolute ones set the
value, offset ones add to it (e.g. `steps` for the notes of a filter line + a small `lfo` on top). Any of
`min`, `max`, `depth`, `base`, `rate`, `glide`, `smooth`, `phase` may be a point list instead of a number
(`depth=ramp(...)`, `depth=per_section({verse: 0.2, chorus: 1})`), or name the modulator (`name='wob'`) and
`node.automate('mod.wob.depth', ...)` (fields: depth min max base rate phase glide smooth attack decay sustain
release gain_db). The compose layer resolves names/fx targets, fills bases, creates ghost key tracks for
`pitches=`, and checks follower cycles; the engine re-validates everything strictly (ranges of params,
windows without a known base, ...).

## VA modulation matrix (`vamod`)

The `va` synth has two fixed envelopes — amp (`amp.*`) and filter (`fenv.*` + `filter.env`) — and a free
modulation matrix for everything else that moves inside a note: its `mods` param is a list of routes, as many
as needed (up to 64), each with its own source. The matrix runs per voice (vibrato, pitch envelopes, velocity
and key tracking, per-note randomness), at control rate with per-sample ramps; `from agentsound import *`
exports the builder module `vamod`.

```python
vm = vamod
lead = s.track('lead', inst.va(unison=3, mods=[
    vm.lfo('sine', hz=5.5, delay=0.3, fade=0.4, id='vib') >> ('pitch', 15),   # delayed vibrato, cents
    vm.env(a=0, d=0.08) >> ('pitch', 1200),                                   # pitch zap on every note
    vm.lfo('triangle', hz=0.3, mode='global') >> ('osc2.pw', 0.3),             # slow shared PWM
    vm.velocity() >> ('cutoff', 1.5),                                         # harder = brighter (octaves)
    vm.random() >> ('pan', 0.3),                                              # per-note stereo spread
    vm.macro(1) >> ('cutoff', 2),                                             # a knob for song automation
]))
lead.automate('instrument.mod.vib.amount', ramp(verse.start, chorus.start, 0, 25))   # every amount is a param
lead.modulate('instrument.macro1', lfo('sine', rate='2 bars', min=0, max=1))        # track modulators drive macros
gate = inst.va(mods=[vm.lfo('square', rate='1/16', mode='global', unipolar=True, phase=0.5)  # trance gate: open on
                     >> ('amp', -24)])                           # each 16th (the square is high first), shut after
bell = inst.va(osc1__wave='sine', osc2__wave='sine', osc2__semi=19, osc2__fine=2,          # FM bell (ratio ~3)
               mods=[vm.env(a=0, d=1.5) >> ('fm', 4)])
pad = patches.get('synthwave/warm_pad').with_mods(vm.lfo('sine', rate=8, mode='global') >> ('cutoff', 0.5))
```

A route is `source >> (target, amount)` or `(target, amount, id)` (or `id=` on the source, or `route.named(id)`);
plain dicts `{'source': {...}, 'target': ..., 'amount': ..., 'id': ...}` work too. The amount is what a source
value of 1 adds to the target, in the target's unit.

| source | value | |
|---|---|---|
| `lfo(shape, rate \| hz=, *, phase=0, delay=0, fade=0, mode='voice', unipolar=False)` | −1..1 (unipolar 0..1) | shapes `sine` `triangle` (`tri`) `saw` (falls; `saw_down`) `ramp` (rises; `saw_up`) `square` `samplehold` (`sh`) `smoothrandom` (`smooth`). Phase 0: sine / triangle at 0 rising, saw at +1, ramp at −1, square high first (so a unipolar square → `amp` gate needs `phase=0.5` to be open on the beat). Any rate up to 200 Hz keeps its full depth: only jumps (square / S&H / saw edges, restarts, a delay ending) glide out in ~2 ms. `rate`: note value / beats (`'1/8'`, `'1/4.'`, `'1/8t'`, `'3 beats'`, a number; tempo-synced — bars are not accepted, the synth doesn't know the meter) or `'5hz'`; `hz=` free. `mode='voice'`: every note restarts its own LFO; `'global'`: one free-running LFO shared by all notes, on the song grid when synced (identical in `--section` previews). `delay` / `fade` (s) hold it back after each note start, then fade it in (also for global LFOs) |
| `env(a=0, d=0.3, s=0, r=d, curve='exp')` | 0..1 | per note, times in **seconds** (track `envelope()` counts beats); `'exp'` = the analog RC shape of the amp / filter envelopes, or `'linear'`; mono mode retriggers from the current level, legato does not |
| `velocity()` | 0..1 | the note velocity |
| `key(low=None, high=None)` | octaves from A4 | `(note − 69) / 12` of the (gliding) pitch; with `low`/`high` (MIDI numbers or names) 0..1 across that range, clamped |
| `random(seed=None, unipolar=False)` | −1..1 per note | drawn from the song seed, the note's position and pitch (renders and previews agree); routes are independent unless they give the same `seed` |
| `macro(n)` | 0..1 | the instrument param `macroN` (n = 1..8, default 0, smoothed): automate / modulate `instrument.macroN` to move every route it feeds |

| target | amount unit | |
|---|---|---|
| `pitch`, `osc1.pitch`, `osc2.pitch` | cents | `pitch` = every oscillator + sub; `osc1.pitch` also moves the sub (and the hard-sync master); `osc2.pitch` the sync slave: the classic sync sweep |
| `osc1.pw`, `osc2.pw` | pulse width | added to `osc1.pw` / `osc2.pw`, kept in 0.02..0.98 (PWM: 0.1-0.25) |
| `osc1.level`, `osc2.level`, `sub.level`, `noise.level` | level | added, kept in 0..1 |
| `cutoff` | octaves | on top of `filter.env`, key tracking and `filter.velocity` |
| `resonance`, `filter.drive`, `unison.detune` | param units | added, kept in 0..1 |
| `amp` | dB | all amp routes add up (−96 = silent): tremolo ±3, gate −24 with a unipolar square |
| `pan` | position | added to `pan`, kept in −1..1 |
| `fm` | radians | osc2 → osc1 phase-modulation index added to the `fm` param (0..10); needs `osc1.wave='sine'` (osc2 may stay silent: `osc2.level` 0) |
| `hpf` | octaves | the global high-pass after the voices: only global sources (`lfo(..., mode='global')` without delay/fade, `macro`) |

* **Amounts are parameters**: route *i* is `instrument.mod.<id>.amount` when it has an id, else
  `instrument.mod.<i>.amount` (its position in the list); automate or modulate them like any param (smoothed ~5 ms;
  a track modulator with `depth=` on one needs `base=`). A flat param `'mod.<id>.amount'` on the sound overrides the
  route's amount: `patch.but(**{'mod.vib.amount': 25})`.
* **Editing a patch's matrix**: `.with_mods(*routes)` appends, and a route whose id is already in the matrix replaces
  it (`.with_mods(vm.lfo('sine', hz=6, delay=0.5, id='vib') >> ('pitch', 20))` re-times a patch's vibrato);
  `replace=True` drops the patch's own routes; `.but(mods=[...])` sets the whole list. `vamod.describe(mods)` lists
  the routes with their amount params; library patches name theirs in their notes (`vib`, `pwm`, `sweep`, ...).
* **Identical sources are shared**: routes with the same source definition read one source instance (one envelope
  driving `pitch` and `osc2.pitch` = the old `fenv.pitch` + `fenv.osc2`), so they move together; `random()` without
  a seed is the exception (each route draws its own).
* **Matrix or track modulator?** The matrix acts inside each voice (per-note phase, per-note envelopes, velocity,
  key); `track.modulate('instrument.<param>', ...)` sets one value for the whole track on the song grid (and can drive
  the macros, i.e. many routes at once).
* **Strict**: unknown sources / targets / keys, out-of-range amounts or fields, duplicate ids, voice sources on
  `hpf`, `fm` without a sine osc1 and more than 64 routes are errors (Python first, the engine again).
* Related va params: `noise.stereo` (0..1: independent left/right noise — wide risers and breath),
  `osc2.phase` (osc2's start phase when `osc.retrig` restarts the oscillators), `fm`, `macro1`..`macro8`.

## Production moves (synthwave)

* Pump: `s.sidechain(pad, bass, arp, key=kit, pitches='kick', depth=8..14, release=~70% of a beat in ms)`;
  keyless tempo pump: `track.duck(rate=1, depth=10)`.
* Space: `s.hall()` for pads/leads, `s.plate()` for keys, `s.echo(time=0.75)` (dotted 8th) for arps/leads,
  `s.gated()` for the 80s snare; set levels with `sends={bus: -12}`.
* 80s gated snare (keyed): send the kit to the gated reverb and let only the snare open the gate - the kick
  can't trigger bursts, and it works at any send level (an unkeyed gate opens on whatever crosses its
  threshold on the bus input):
  ```python
  kit = s.track('drums', 'synthwave/drums_outrun')                  # its patch already sends -6 dB to 'gated'
  s.gated(gain_db=-2, hold=250, key=kit, pitches='snare')           # add 'clap'/'tom_*' to gate those too
  ```
  With `inst.drums(...)` give the kit `sends={'gated': -6}`. Shape it with the gatedreverb params: `hold` =
  burst length (about an 8th note: 60000 / bpm / 2 ms), `release` 10..40 ms (the abrupt cut), `predelay` 0..20,
  `decay` long (flat burst) or short (decaying). The key is the raw drum instrument (no inserts) at the kit's
  fader, whose snare hits peak far above the gate threshold (-16 dBFS in `bus/gated`), so every snare note opens
  it, ghost notes included. Set the effect level with the return `gain_db` (-6 subtle .. +4 huge).
* Builds: `riser(...)` on filter cutoffs / a high-pass, `snare_roll(4, build=True)` into `crash()`,
  `per_section` for arrangement-level changes, `fade` on `gainDb` for outros.
* Movement (modulators): pluck filters on arps/basses `envelope(decay='1/8', min=500, max=5000, curve='exp')`;
  a pad breathing with the kick `envelope(decay='1/4', trigger=kit, pitches='kick', depth=-8)` on `gainDb` (or
  on the pad cutoff with `curve='exp'`, `depth=-1`); a chorus-only trance gate `gate('x.x.xx.x.x.xx.x.', depth=18)`;
  a bass that opens with the kick `follow(kit, pitches='kick', min=300, max=1800, curve='exp')`; slow stereo
  motion `lfo('triangle', rate='2 bars', depth=0.4)` on `pan`; subtle analog life `sample_hold('1 bar', smooth=1,
  depth=0.15, curve='exp')` on cutoffs. Let depth grow into the drop with `depth=ramp(...)`.
* Inside the va (per note, `mods`): delayed vibrato `vamod.lfo('sine', hz=5.5, delay=0.3, fade=0.4) >> ('pitch', 15)`
  on held lead notes; sync-lead bite `vamod.env(a=0, d=0.3) >> ('osc2.pitch', 1600)` with `osc2__sync='on'`; Juno
  shimmer `vamod.lfo('triangle', hz=0.6, mode='global') >> ('osc1.pw', 0.2)` on a square pad; velocity-to-cutoff and
  `vamod.random() >> ('pan', 0.2)` so repeated arp notes breathe; wide risers with `noise__stereo=1`.
* Levels: aim instrument tracks at roughly -24..-18 LUFS in the report, then `fx.limiter(gain=...)` on the
  master to land at -14..-9 LUFS-I with true peak <= -1 dBTP; read the report warnings and suggestions and iterate.

## Jazz (`agentsound.jazz`)

Everything for a New York bar trio / quartet (piano, upright bass, brushes, tenor sax) in one namespace:
`from agentsound import jazz` (it is not part of `from agentsound import *`). It re-exports the jazz voicings
(theory.py), comping / walking bass / brushes (patterns.py) and the jazz feel (humanize.py) and adds the band
set-up, the horn expression helpers and melody helpers. Recipe: `recipes/jazz-trio.md`; a complete example:
`songs/_demo_jazz/song.py`. All generators write **straight 8ths** (exact triplets where a triplet is meant):
the swing ratio and every part's lay-back come from the feel, so one part works at any tempo. Everything random
is seeded.

```python
s = Song('Blue Room', tempo=138, key='Bb major', seed=7)
head = s.section('head', bars=32)
b = jazz.band(s, sax=True)                          # comp / piano / bass / drums / sax tracks, room + plate buses,
                                                    # each track already grooved (swing by tempo + its lay-back)
prog = s.prog('Bbmaj7 Gm7 Cm7 F7 | ...')            # 32 bars
melody = Clip([...], length=128)                    # the written head, straight
b.comp.play(jazz.comp(prog, style='charleston', answer=melody, register=('A2', 'G4'), seed=1), head)
b.bass.play(jazz.walking_bass(prog, key=s.key, seed=2), head)
b.drums.play(jazz.brushes(32, seed=3), head)
jazz.horn_line(melody, s.tempo, param='level', seed=4).place(b.sax, head)   # phrasing + expression
```

**Voicings** (theory.py; lists of MIDI pitches; `register` default `LH_REGISTER` = C3..C5, clear of low-interval
mud):

| call | |
|---|---|
| `rootless(ch, form='A', voices=4, register, resolve_minor=False)` | Bill Evans: A = 3-5-7-9, B = 7-9-3-5; dominants take 13 for 5 (G13: B E F A / F A B E); written alterations win (7alt = 3 b13 b7 #9, 7b9, 7#9, 7#11, 7b13); m7b5 = b3 b5 b7 + root (9 / 11 when written); 6, 6/9, m6 put the 6th in the 7th's place; triads read as 6/9, m9, dim7, 7sus4; `C11` = C9sus4. `voices=3`: A = 3-7-9, B = 7-3-5 |
| `shell(ch, form='37', register, root=False, tension=False)` | guide tones only (m7b5 adds its b5); `tension=True` + the 9; `root=True` = Bud Powell shell for solo piano: root E2..D#3 with 7th and 10th (G2 F3 B3) |
| `quartal(ch, voices=4)` | stacked 4ths from the chord scale holding 3rd + 7th + written alterations, no avoid notes: Dm7 D G C F, G7 F B E A, Cmaj7 B E A D, G7alt B F Bb Eb |
| `so_what(ch)` | three 4ths + a major 3rd (Dm7: D G C F A; Cmaj7: E A D G B; dominants: a 5-note quartal stack) |
| `block(ch, melody, style='drop2')` | block chord under a melody note: `close` (4-way close), `drop2`, `drop24`, `locked` (locked hands: + the melody an octave below); 6th chords on major (maj7 set when the melody is the 7th), tensions replace the tone below them, a passing melody note gets the dim7 built down from it |
| `upper_structure(ch, triad='auto', register=(52, 84), top=None)` | altered dominants: 3 + b7 tritone and a triad on top (`UPPER_STRUCTURES`: II bIII bV bVI VI bIIm #IVm); auto: alt -> bVI, b9b13 -> bIIm, b9#11 -> bV, 7b9 -> VI, 7#9 -> bIII, #11 -> II |
| `jazz_voice(ch, style)`, `jazz_voicings(chords, style='rootless', register, voices=4, start=None)` | one chord / a voice-led sequence (dynamic programme over every form and octave: least motion, smooth top voice, centred in the register). Rootless A/B forms alternate where roots move by 4ths / 5ths, so the guide tones move by step (Dm7 G7 Cmaj7: F3 A3 C4 E4 / F3 A3 B3 E4 / E3 G3 B3 D4); a dominant resolving to minor gets b9 / b13 |
| `chord_kind(ch)`, `guide_tones(ch)`, `chord_scale(ch)`, `chord_scale_name(ch)`, `available_tensions(ch)` | analysis: family (`CHORD_KINDS`), (3rd, 7th) pcs, the chord scale (`CHORD_SCALES`: dorian, mixolydian, altered, half_whole, locrian, lydian_dominant ...), tensions without avoid notes |
| `mud(pitches)`, `check_voicing(ch, pitches)` | pairs below their low interval limit (`LOW_INTERVAL_LIMITS`: m2 E3, M2 Eb3, m3 C3, M3 Bb2, 4th A2, 5th Bb1 ...); every problem of a voicing against its symbol (foreign tones, missing 3rd / 7th, mud) |

**Comping** `comp(prog, style='swing', voicing='rootless', register=(48, 72), voices=4, density=0.5,
intensity=0.5, answer=None, phrase=8, vel=None, roll=None, seed=0, touch=1.0)`: one rhythm cell per bar from `COMP_CELLS`,
seeded and varied (no cell three times running; phrase starts favour a chord on 1, phrase ends a push). Styles
`swing` (the conversational mix), `charleston`, `garland` (short chords on the & of 2 and 4), `ballad` (held,
rolled), `sparse`, `bossa` (1 &2 4 | 2 &3 - play it straight), `waltz` (3/4). A hit on the 8th before a chord
change anticipates the new chord and ties over (the change is not struck again). `density` ~0.6..3 hits per bar,
`intensity` = velocity 50..88 + shorter stabs. `answer=melody` comps in the melody's rests (hits under melody notes
dropped except soft anchors on chord changes; every rest of a beat or more answered). Voicings: any jazz style or
a classic one; put it under a horn with `register=('A2', 'G4')`. `touch` 0..1: the pianist's touch per hit - the
comping breathes over each `phrase` (x0.87..1.13) and every 2 bars (+-8 %), anticipations lean in, short off-beat
stabs are lighter than the anchors on 1, +-7 % per hit, normalized in energy so `vel` / `intensity` keep the
loudness (~4-5 dB of hit-to-hit dynamics on the Salamander; `touch=0`: the old flat cell levels, which the dynamics
ear reads as flat_dynamics).

**Walking bass** `walking_bass(prog, key=None, feel='four', low='E1', high='G3', seed=0, vel=90, gate=0.9,
approach='mixed', skip=0.1, octave=0.05, repeat=0.05, pedal=None, accent=1.05, skip_grid='swing', touch=1.0)`: quarter notes,
the root on beat 1 of every chord (repeated chords merge and keep walking), chord tones on beat 3, chord / scale /
chromatic passing tones on 2, an approach on the last beat before each change (`approach`: chromatic | scale |
dominant | mixed: half step above / below, scale step, or the target's 5th, chosen by the line's direction),
planned like a melody (steps and 3rds, no A-B-A wobbles) inside `low`..`high`. Seeded colour: `skip` (ghosted skip
note before the next beat: on the & or, `skip_grid='triplet'`, on the last triplet), `octave` (octave leap),
`repeat` (beat 2 repeats beat 1). `feel='two'`: half notes, root then 5th / an approach, pickups with `skip`.
`pedal='F2'` or `[(start, end, 'F2')]` (beats inside the clip): pedal point, approaching the chord after it.
`touch` 0..1: a bassist's dynamics through `bass_touch` (4-bar arcs ~0.8..1.16 x vel, beats 2 / 4 feathered in
'four', 1 / 3 in 'two', ghosted skips, lighter approaches, pushed anticipations accented), normalized in energy so
`vel` keeps the loudness: ~6-8 dB of note-to-note dynamics per phrase on `sampled/upright_bass`; `touch=0` = the old
flat level (vel +-3 %: flat_dynamics). The line's notes are the same with any touch. With the evened Meatbass the
velocity is the level: 80-95 is the calibrated walking level of the jazz presets, a soft pedal intro ~80, 60-70 is
really soft (~4-5 dB under 90).

**Bass touch** (humanize.py, `jazz.bass_touch`) `bass_touch(clip, lo=62, hi=100, accent='1-3', phrase=16, peak=0.6,
offbeat=0.82, ghost=0.55, approach=0.84, anticipation=1.1, pitch=0.35, beats_per_bar=4, jitter=0.03, seed=0)`:
writes a bass line's velocities like `touch()` does for a melody - per `phrase` beats a cosine arc from lo up to hi
at `peak` and back; beat weights `BASS_ACCENTS[accent]` ('1-3' two-feel / straight 8ths, '2-4' a swinging walk,
'even'); off-beat 8ths x offbeat; ghosts (<= 1/3 beat) x ghost of the arc's soft end; a note stepping (1-2
semitones) into the next bar line x approach; an off-beat note tied over the bar line x anticipation; `pitch`
velocity per semitone off the phrase's mean; seeded jitter. Use it on any hand-written or pattern bass line (a
straight-8th head: lo 0.84 x vel / hi 1.22 x vel, see songs/perry-street-rain).

**Brushes / ride**: `brushes(bars=4, style='medium', kit=None, sweep=None, taps=True, kick='feather', hat=True,
ride=False, fills=True, phrase=8, fill=None, vel=1.0, seed=0, beats_per_bar=4)` - the continuous sweep (`kit['sweep']` held per
'half' bar (medium, two), 'bar' (ballad, up), '2bars', 'beat' or a beat count; `False` = none), taps on 2 and 4
with seeded ghost taps, feathered kick (`'feather'`, `'two'`, `None`), hi-hat foot on 2 and 4, `ride=True` swaps
the taps for the ride, a fill in the last bar of every `phrase` bars. Styles `medium ballad up two`.
`brush_fill(kind='triplets', length=2, kit=None, vel=(40, 90))`: `FILL_KINDS` triplets eighths slap toms swell.
`ride_pattern(bars=4, pattern='spang', kit=None, vel=72, accent=1.12, variation=0.15)`: `spang` (spang-a-lang),
`quarters`, `two`, `broken`. Kits are plain dicts role -> note (a list = round robin): `GM_BRUSH` (GeneralUser /
GS 'Brush' kit, `inst.sf2(bank=128, program=40)`: 38 tap, 39 slap, 40 held swirl, 44 hat foot, 51 ride, 36 kick),
`SWIRLY_BRUSH` (Karoryfer Swirly Drums: 38 tap, 40 edge, 39 dig, 60 / 64 slow / fast one-shot stirs - swells the
next one crossfades: use `sweep=jazz.swirly_sweep(s.tempo)`, one stir about every second - 62 stops them, 44 foot,
51 ride) or your own.

**Feel** (humanize.py): `swing_ratio(bpm)` 0.66 at ballad tempo (<= 70), 0.61 at 140, 0.555 at 220, 0.53 at 300.
`LAYBACK_MS` / `layback_ms(part, bpm)`: piano right hand 22..10 ms behind (ballad..up), comping 10..5, bass
-2..-5 (on top), brushes 0, ride -2..-4, sax 35..12. `jazz_groove(part, bpm, ratio=None, late_ms=None,
accent_24=None, beats_per_bar=4)` -> a `Groove` for `track.groove()` (8ths swung at the ratio, the lay-back, the
bass's backbeats x1.04). `jazz.Feel(bpm, ratio=None, layback={...}, beats_per_bar=4)`: `.ratio`, `.late_ms(part)`,
`.groove(part)`, `.swing(clip)`, `.apply(clip, part)` (baked into a clip). `backbeat(clip, 1.08, beats_per_bar=4)`
accents 2 and 4 (2 and 3 in 3/4); `phrases(clip, gap)`;
`phrase_dynamics(clip, gap='1/8', arch=0.12, peak=1.06, end=0.9, offbeat=1.0, ghost=None)` shapes each phrase
(arch, top note, soft short ends, bebop upbeat accents, ghosted low notes in runs) - a shading of a few percent
(about 1 dB) around the written level. For a melody lead use `touch(clip, lo=60, hi=108, gap='1/4', start=0.4,
end=0.3, pitch=0.8, sync=1.1, passing=0.84, grace=0.62, last=0.86, inner=0.86)`: it WRITES the velocities from the
line - each phrase rises from lo + start x (hi - lo) to its top note and relaxes to lo + end x (hi - lo), the clip's
summit gets hi (lower-peaking phrases 1 per semitone less), higher notes sing out (`pitch` per semitone),
syncopations lean (x sync), passing / grace / short last notes stay light, notes under the top (octaves, block
chords) x inner. A written melody at one velocity reads flat to the ear even when the sections differ (user feedback
2026-09-30): aim for 8-12 dB of onset contrast inside a phrase (lo 50-60 / hi 90-100 soft, lo 75-85 / hi 115-122 at
a climax; the Salamander's top layers start at 105 / 113 / 121). Apply it before `octave_double` / `block_chords`.

**Horn expression** - a sampled horn played like a keyboard sounds fake. `horn_line(melody, bpm, ratio=None,
late_ms=None, long='1/2', scoop=0.35, scoop_cents=(-90, -50), fall=0.5, fall_st=-3, vibrato=True, vib_hz=(4.6, 5.4),
vib_depth=0.18, vib_delay=0.35, vib_grow=0.6, swell=True, swell_db=(-5, 0, -7), param='expression', breath_ms=180,
max_phrase=8, legato=True, dynamics=True, seed=0)` -> `HornLine`: `.clip` = the notes as played (swung, laid back:
baked in, so don't groove the horn track; legato inside phrases - use `mono='on'`; breaths before rests and inside
phrases longer than `max_phrase` beats; phrase dynamics) and `.expr` (an `Expression`): scoops (pitch bend from
`scoop_cents`) into phrase starts and notes after a leap up, falls (`fall_st` semitones + a fade) on phrase-end
notes before a rest, swells (`swell_db` start / peak / end) and a delayed vibrato (after `vib_delay` s, growing over
`vib_grow` s to `vib_depth` semitones at a seeded rate in `vib_hz`, one lfo for the whole line) on notes of at
least `long`. GeneralUser's 'Tenor Sax' has its own delayed vibrato (about +-19 ct at 5 Hz from 0.4 s): give it
`vibrato=False`; the FreePats / sampled tenor plays a straight tone and needs ours. `line.place(track, at)` plays it
and applies the expression there (twice for head in / head out is fine). `param`: `EXPRESSION_PARAMS` - `'expression'` (default; the sampler / sf2 expression control 0..1, arriving
with the sampler update), `'level'` (instrument level, dB relative to the sound's own) or `'gainDb'` (the fader).
Building blocks: `scoop(at, cents=-80, length='1/16')`, `fall(end, semitones=-3, length='1/8', back=None)` (points
for `'instrument.pitchbend'`), `swell(start, end, lo_db, peak_db, end_db)` (dB offsets: `Expression.add_swell`),
`vibrato(start, end, bpm, depth, hz, delay, grow)` (depth / rate lanes), `breathe(clip, bpm, breath_ms, max_phrase)`,
`legato_phrases(clip, overlap=0.02, max_gap='1/16')`, `Expression()` (`.add`, `.add_swell`, `.add_vibrato`,
`.shifted`, `+`, `.apply(track)`).

**Melody**: `paraphrase(melody, seed=0, anticipate=0.3, delay=0.15, embellish=0.2, key=None)` loosens a head
(anticipations tied over, late phrase entrances, chromatic pickups / enclosures before long notes; pitches kept) -
paraphrase every chorus differently. `block_chords(melody, prog, style='drop2', min_dur=0, key=None, vel=0.85)`
harmonizes every melody note with `block()` (Shearing / Garland locked hands: `style='locked'`).
`solo_line(prog, key=None, register=('C4', 'C6'), density=0.6, intensity=0.5, seed=0, motif=None, motif_prob=0.3,
phrase_bars=(1, 3), rest_beats=(1.5, 4), chromatic=0.35, triplets=0.12, vel=88)`: a bebop-flavoured improvised line
(a seeded starting point, like `melody()`): phrases of 1-3 bars mostly starting off the beat with rests between,
running 8ths with quarter notes and 8th-note-triplet turns, chord tones on the beats (a dynamic programme per
phrase: chord-scale and chromatic passing tones between, steps over leaps, runs, an arc), enclosures into targets,
phrase endings on a long 3rd / 9th, bebop accents (upbeats, ghosted low notes); `motif=` opens phrases with a
motif fitted to the chords. Density lengthens phrases, intensity raises level and register. A new seed per chorus.
**The pianist** (`agentsound.pianist`, also `from agentsound import pianist`; `jazz.pianist(...)` = `pianist.arrange`)
- a piano lead is never a bare single-note line (HUMAN_FEEDBACK 2026-09-30). `arrange(melody, prog, *, bpm, key=None,
style='straight', density=0.5, seed=0, lh=None, floor=None, voices=None, roll=None, anticipate=None, delay=None,
fill=None, embellish=None, quick=None, devices=None, ornaments=None, fills=None, climax=False, lead_in=False,
section_end=True, inner=None, lh_vel=58, lh_register=('C3', 'C4'), ceiling='C7', fast_every=None, spice_every=None,
same_every=32, memory=None, at=None)` -> `Arrangement` (`.rh`, `.lh`, `.melody` as placed, `.moves` = [(start, end,
'device' | 'ornament' | 'fill' | 'dropped', name)], `.dry`, `.pedal(prog, at)`, `.summary()`, `.budget`,
`.harmonized` = the share of melody notes with voices under them). Per phrase (lines longer than ~6
beats change device after a long note or at a bar line) a voicing DEVICE under the melody (`DEVICES`: single,
guide, thirds, sixths, close, drop2, quartal, ust, octave, locked; `voicing(ch, melody, device, floor, voices)` for
one note: melody on top, voices >= floor, no minor 2nds / 9ths, no mud): strong / long chord tones get the device,
weak ones a guide tone or a 3rd, passing tones stay single; long notes (1.5+ beats) an ORNAMENT (`ORNAMENTS`: trill,
tremolo, restrike, turn, mordent, inverted_mordent, roll, crush, blues_crush, slip, repeated, shake - one per phrase),
shorter chord tones now and then a quick one (blues crush on a major 3rd, crush, slip, mordent, turn); gaps of a
beat or more a FILL (`FILL_KINDS`: run, chromatic, arpeggio, answer, stabs, fourths, pentatonic, hands, octave_run,
tremolo, repeated; gliss only into the clip end with section_end; the gap before the first note with lead_in=True).
Anticipations (the chord they belong to), delayed entrances, chords rolled into the melody (it keeps its time),
inner voices x `inner` (~10-15 velocity under: apply `jazz.touch()` first). `STYLES`: straight (guide / 3rds /
drop 2 / quartal, runs and answers), ballad (drop 2 / close / ust, arpeggios, rolls 15-25 ms, trills), bar (octaves,
blues crushes, slip notes, repeated notes, shakes, chromatic run-downs, alternating hands), lush (drop 2 / ust /
close, tremolos, sweeps), sparse (guide tones, single notes, answers); density 0..1 scales how much is harmonized,
decorated and filled; climax=True favours octaves / locked hands / octave runs. `lh=` `LH_STYLES` (guide = 3rd + 7th,
shell = 1-7 / 1-3, rootless A/B, tenths, stride, pedal) -> the right hand stays above C4; the left hand is struck on
the changes (anticipated with the right hand), held, rolled, and answers the right hand once on a chord of a bar or
more, in the meter's place (`LH_METERS`; `lh_answers=` the chance, default density x 0.8): 4/4 on 3 or the & of 2;
3/4 a light 'oom-pah-pah' answer on 2, the & of 2 or 3 (seeded, the held shell lifts before it; the hand stays out
where the right hand plays); 6/8 on the second dotted quarter, 5/4 on 4 (3+2), 12/8, 7/8, 7/4, 9/8, 2/4 likewise;
stride follows the meter's pulse too. The meter comes from the progression's beats per bar (3 = 3/4, 6 = 12/8):
pass `meter='6/8'` for compound time (`left_hand(prog, bpm, style=..., meter=None, answers=None)` on its own).
`pedal(prog, at, dry=[(start, end)])`: the harmony pedal lifted for runs and repeated notes (the arrangement's
`.dry`; ornaments keep it down: legato).
**Ornament budget** (HUMAN_FEEDBACK 2026-09-30, perry-street-rain v3: "etwas zu viele von diesen schnellen
Zwei-Tasten-Wechseln"): the `FAST` two-key alternations (trill, tremolo, shake, repeated notes, alternating hands -
as ornaments and as fills) are rare spice: at most one per `fast_every` bars (per style: straight / bar 16, lush 12,
ballad 10, sparse 0 = none), two of a kind at least `same_every` (32) bars apart, never in neighbouring phrases, only
at structural moments, the best-placed first (the clip's last long note, a phrase end, the top of the line, a
section-end fill, climax=True). The `SPICE` ornaments (turn, mordent, crush, blues crush, slip, roll) share a larger
budget: `spice_every` bars apart (1.5-3). A dropped move becomes another (not fast) ornament / fill of the style or
the plain voicing, from a side random stream (devices, fills and rolls stay as they were); `.moves` logs it as
`'dropped'`, `.budget` = {fast_every, spice_every, same_every, fast: [(beat, kind)], spice: n, dropped: [(beat,
kind, substitute)]}. Song-wide: `mem = pianist.Memory()`, pass `memory=mem, at=sec.bar(n)` to every arrange() call
(without `at` the calls follow each other); `mem.played(at, 'trill')` books a move placed by hand,
`mem.save(at)` keeps the fast budget free for the climax (earlier calls stay `fast_every` bars away from it).
Ornaments are played **light**: the principal note at its velocity, the figure `light` velocity under it (default
25-40, `light=` on the moves), swelling in and fading, legato, a soft landing; runs / sweeps / 4ths are one gesture
(lighter in the middle).
Named MOVES (each a Clip from `at`, timed in real time by `bpm`, velocities shaped, a few ms of seeded wobble):
`trill(pitch, dur, bpm, upper=None, chord=, key=, rate=14, start_rate=None, turn=True, light=None)` (12-16
notes/s, accelerating, light under the principal, ending with a turn), `tremolo(lower, upper, dur, bpm, rate=11,
swell='arch' | 'cresc' | 'dim', land=True)` (3rds, 6ths, octaves, a chord against its bass), `mordent(pitch, dur,
bpm, upper=False)` / `inverted_mordent`, `turn(pitch, dur, bpm, inverted=False, chromatic=True)`, `crush(pitch, dur,
bpm, grace=-1, together=False, under=())`, `blues_crush(third, dur, bpm)` (minor 3rd struck with the major 3rd),
`slip_note(pitches, dur, bpm, voice=-1, by=-2)` (Floyd Cramer), `repeated(pitches, dur, bpm, rate=9)` (hand
alternation), `roll(pitches, dur, bpm, ms=25, direction='up')`, `sweep(chord, dur, bpm, low, high, direction)`
(arpeggio across the keyboard), `gliss(target, length, bpm, direction='up', span=14, land=False)` (a fast scale
sweep INTO a downbeat), `run(start, end, dur, bpm, chord=, key=, scale=)`, `chromatic_run`, `pentatonic_run(start,
dur, bpm, notes=6)`, `octave_run`, `fourths(top, dur, bpm, voices=2, grid=0.25)` (cascading 4ths), `shake(pitches,
dur, bpm, interval=3)` (block-chord ending shake), `alternating_hands(chord, dur, bpm, top, pattern='RL')`
(`MOVES` = name -> function).
`JAZZ_PROGRESSIONS`: ii_v_i, minor_ii_v_i, turnaround, iii_vi_ii_v, tritone_turnaround, backdoor, rhythm_a, blues,
bridge_cycle (roman numerals: `s.prog(jazz.JAZZ_PROGRESSIONS['rhythm_a'])`).

**The romantic pianist** (`agentsound.romantic`, `from agentsound import romantic as rom`) - for WRITTEN scores
(Chopin, Schumann, Liszt, film piano): the jazz pianist arranges a lead sheet, this one plays the notes as written
but as a pianist would. Found and measured by the nocturne etude (songs/nocturne-etude, NOTES.md: before/after
against a concert recording). Times are beats; figures are timed in REAL time through `bpm` (a number or
`s.tempo_at`: place the left hand first so the tempo map knows its onsets).

| call | plays |
|---|---|
| `fioritura(pitches, dur, bpm, at=, shape='arch', ease=0.8, vel=(v0, v1), dip=6, sing=0.4, land=None, max_rate=24)` | the written notes of a fast figure (chromatic, scale, arpeggio, turns) as ONE gesture: `SHAPES` arch (out of the principal slowly, fastest in the middle, broadening into the landing; ends ~1.8x the middle at ease 0.8) / accel / rit / even / wave, lighter in the middle (`dip`), higher notes sing, finger legato; never thinned (too fast = error) |
| `trill(pitch, dur, bpm, key=, start='main'\|'upper'\|'lower', rate=12, start_rate, end_rate, grow=0.35, settle=0.3, lower=None, land=)` | a slow start speeding up to `rate` notes/s, settling into the Nachschlag (lower neighbour - `lower=-1` chromatic - and main) that leads into `land`; light under the principal |
| `turn(pitch, dur, bpm, where='after'\|'on', key=, upper=, lower=)`, `grace(pitches, target, dur, bpm, ms=65, on_beat=False)` | the gruppetto between two notes (after) or on the beat; appoggiature / small notes before (stealing time) or on the beat |
| `accompany(entries, bpm, pattern='bcc', vel=40, bass=1.2, second=0.9, top=1.05, roll_ms=12)` | the left hand from `(start, length, bass, chord[, chord2])` entries: bass + chord + chord in 12/8 (`bc`, `bccccc`, `B..` = a held rolled chord), the bass carrying, the chords soft and slightly rolled, a slow breath per phrase |
| `lean_on_long(clip, bpm, gain=10)`, `cantabile(clip, bpm, match=0.35, lift=5)`, `decay_db(pitch, s)` | the singing line: long notes get more tone; the note after a long one plays into the decayed level (the legato illusion); ornaments keep their level under their principal |
| `dynamics(clip, [(beat, 'p'), (beat, 'f'), (beat, 'pp', 'step')])`, `LEVELS` | marks and hairpins as velocity factors (pp 0.55 .. ff 1.3, smooth or subito) |
| `melody_rubato(rh, anchors, bpm, lean_ms=35, late_ms=6, sync_ms=32, agogic_ms=50, peak_ms=40)` | Chopin's rubato: only the melody moves - leaning ahead / behind inside each anchor span, the downbeat melody spread around the bass (+-sync_ms), held back after leaps and on local summits; order and legato kept; the left hand keeps the tempo map |
| `pedal_changes(changes, end=, lift_ms=90, bpm=, dry=, flutter=, flutter_ms=280, flutter_to=0)` | legato pedal per harmony (up with the new bass, down lift_ms later), cleared every flutter_ms in chromatic runs / cadenzas (`flutter_to=0.6`: to a half pedal, the bass rings on) |
| `figure_stats(clip, bpm)` | notes, notes/s, fastest / slowest IOI, ends vs middle, CV - to compare a figure with a recording |

```python
lh_t.play(rom.accompany(entries, s.tempo_at, vel=38), 0)                         # the timekeeper first
rh = rom.fioritura(['Db6', 'C6', 'B5', 'Bb5', 'A5', 'Ab5', 'F5', 'D5', 'B4', 'Bb4'], 1.25, s.tempo_at, at=b16 + 1)
rh = rom.cantabile(rom.lean_on_long(line, s.tempo_at), s.tempo_at)
rh = rom.melody_rubato(rom.dynamics(rh, marks), anchors=bar_and_half_bar_beats, bpm=s.tempo_at)
```

**Band presets** (finished productions: IR rooms, placement, master, balance measured on demo songs):
`bands.make('jazz_trio' | 'jazz_quartet' | 'jazz_ballad' | 'bossa', s)` - `agentsound/bandlib/jazz.py`, recipe
`recipes/jazz-trio.md` "Band presets", demos `songs/_bands/<preset>`; its helpers `agentsound.bandlib.jazz.brushes(band,
bars, ...)` (jazz.brushes keyed and levelled for the kit a band got: a Swirly stir is ~19 dB under a tap at the same
velocity), `pedal(tracks, prog, at)` (sustain pedal with the harmony) and `bossa_groove(bars, band)`.
Levels: a role's `gain_db` is the preset's level for it; `b.bass.gain_db -= 1` moves it, and
`b.bass.automate('gainDb', [(0, 0), (solo.start, 2, 'smooth'), (solo.end, 0, 'smooth')])` is dB on it (every
`gainDb` value is relative to the track's gain_db, see Automation).


**Band** `band(s, sax=False, piano=None, bass=None, drums=None, horn=None, room=True, plate=True,
sampled_sounds='auto', feel=None, ids=None, piano_width=None)` -> `Band` with `.comp .piano .bass .drums .sax .room
.plate .feel` and `.kit .sweep .stir .horn .sounds` (the brush keymap / sweep / stir levelling for the drums it got,
the horn_line options for its sax, role -> what plays it). `sampled_sounds='auto'` plays each role from its installed
SFZ pack (`SFZ_SOUNDS`: Salamander Grand, Meatbass pizz, Swirly Drums, the MTG legato tenor - levelled to the
GeneralUser balance) and from GeneralUser GS where the pack is missing; `False` GeneralUser only; `True` every pack
(else an error naming `samples fetch`); `'sf2'` the SoundFont packs (below). With the Swirly kit play the brushes with
`kit=b.kit, sweep=b.sweep` (or `bandlib.jazz.brushes(b, ...)`), the sax with `horn_line(..., **b.horn)`.
The GeneralUser sounds (Grand Piano width 2.0, Acoustic Bass, Brush kit, Tenor Sax mono) get eq, compression on the
bass, pans (piano +0.15, sax -0.25), subtle width (piano M/S widener `piano_width`: `PIANO_WIDTH` 1.7 on the narrow
GeneralUser piano, 1.0 on a sampled / passed-in piano - a stereo recording is wide already and widening it more
throws it out of phase; a Haas microshift on the brushes and the sax), a small
room (1.2 s) for all and a plate for sax and piano, and each track's groove from the feel (not the sax: horn_line
bakes it). Balance measured on medium-swing material: piano melody / sax about -19.5 LUFS, comping -23.5, bass
-22.5, brushes -29 - the recipe's mix. Swap any sound (`piano=inst.sf2(...)`, a sampled instrument, a patch) and
re-level it. `sampled_sounds='sf2'` (or `jazz.sampled('piano' | 'sax', **params)` for one sound) takes the piano and
the sax from installed sample packs that ship as SoundFonts (`SAMPLED_SOUNDS`: Salamander Grand V3 - CC-BY, credit
Alexander Holm - and the FreePats tenor), levelled and eq'd like the defaults; a missing pack is an error naming
the `samples fetch` command. The Salamander's spaced-pair samples are barely correlated (some notes negative): it
plays at sf2 `width=0.7` without the widener (piano track correlation ~0.4-0.7). Its 16 velocity layers are real
pianissimo below ~60: lines written for the GeneralUser piano at velocity 40-55 come out ~6 dB softer - play the
right hand at 60-90 (or raise its gain_db).
Master: `fx.tape(speed='15', drive=1.5)`, a gentle air shelf and `fx.limiter(gain=2..4)` land a trio around
-15..-13 LUFS with a real dynamic range (the analysis profile `jazz`, when available, judges that; with `default`
ignore the loudness / sub / width warnings that assume a synthwave master).

## The bassist (`agentsound.bassist`)

A virtual bass player, the counterpart of the pianist: a progression (+ the kick to lock with) in, a played bass
line out - roots struck on the downbeats and the changes, approach notes and passing tones into the next chord, space
in the verse and drive in the chorus, dead notes, octave pops, slides, hammer-ons, fills into the next section, human
touch and timing. `from agentsound import bassist`. Every move is a function of its own; `arrange()` chooses them bar
by bar (seeded, deterministic) and BUDGETS the flashy ones (user feedback: spice, not habit).

```python
mem = bassist.Memory()                                   # one per bassist and song: budgets count song-wide
beat = drums({'kick': 'x.....x.x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
line = bassist.arrange(s.prog('Em C G D') * 2, bpm=s.tempo, key=s.key, style='rock', part='verse', kick=beat,
                       into='A', seed=2, memory=mem, at=verse)
line.place(b.bass, verse)                                # articulations mapped to the patch, slides as glides / bends
bassist.arrange(cprog, bpm=s.tempo, key=s.key, style='rock', part='chorus', kick=big, memory=mem,
                at=chorus).place(b.bass, chorus)
bassist.arrange(s.prog('Em:2'), bpm=s.tempo, style='rock', part='end', ending='slide', section_end=False,
                memory=mem, at=end).place(b.bass, end)
print(line.summary(), line.budget, line.locked, line.problems)   # what it played; [] = playable
```

`arrange(prog, *, bpm, key=None, style='rock', part=None, energy=None, density=0.5, seed=0, kick=None, lock=None,
interlock=None, strings=4, low='E1', high=None, technique=None, cells=None, approach=None, fills=None, flash=None, fill_every=None,
flash_every=None, section_end=True, into=None, pedal=None, ending=None, late_ms=None, timing_ms=None, timing=True,
swing=None, memory=None, at=None, length=None)` -> `BassLine` (`.clip` relative to the clip start, `.place(track, at)`,
`.adapted(track)` -> (clip, pitch-bend points), `.moves` = [(start, end, kind, name)] with kind `groove` (the cell
per bar) | `approach` | `fill` | `move` (FLASH) | `ghost` | `space` | `pedal` | `ending`, `.summary()`, `.budget`
(fill_every / flash_every, the fills and flashy moves kept, the ones `dropped`), `.locked` (share of the kick onsets
the bass plays with), `.problems` (check()), `.swing` (the 16th swing played, None = straight)).

* **Styles** (`STYLES`; each a set of 16th-grid groove cells per 4/4 bar chosen by energy, a note-length gate,
  articulation, lay-back, approach / move / fill weights and budgets; `PATCHES` = the curated patch per style):
  `rock` (8th roots with the pick locked to the kick; the kick's rhythm doubled in a verse; `sampled/rock_bass`),
  `pop` (whole notes / 1-&2-3 anchors / 1-5-8 / 3-3-2 syncopation / octaves; `finger_bass`), `country` (two-beat
  root-5th, walk-ups; `picked_bass`), `funk` (16th grooves with dead notes and octave pops, interlocking with the
  kick: the one together, the gaps answered; `finger_bass`, `slap_bass` + `technique='slap'`), `motown` (melodic
  1-3-5-6 lines - the 6th, not a blue b7, over a major triad - chromatic approaches; `flatwound_bass`), `disco` (staccato octave 8ths), `ballad` (whole / half notes,
  passing tones, legato, slides; `hollow_bass`), `reggae` (one-drop: space on the one, laid back +14 ms;
  `flatwound_bass`), `tumbao` (latin: the 5th on the & of 2, the next chord anticipated on 4 and tied over the bar
  line, fills land on that 4 - never on the one; `electric_upright`), `synth` (synthwave octave pulse; `layered/synth_sub_bass`) and `walking` (wraps
  `patterns.walking_bass`: two-feel at low energy, four above; `upright_bass`). `cells={'eighths': 2, 'kick': 1}`
  overrides the cell weights (`'kick'` = the kick's rhythm doubled).
* **Form**: `part=` a `PARTS` name (intro .35, verse .45, pre .62, chorus .85, bridge .55, solo .7, outro .5, break
  .3, ...) or `energy=` 0..1 picks the cells (sparse and short in a verse, driving and sustained in a chorus), the
  level (the top velocity ~90 -> ~118), the note lengths (a rock verse chugs staccato, the chorus sustains).
  `density` 0..1 scales approaches, fills, moves and dead notes (and leaves space when low). A variation cell at the
  end of 4-bar phrases; a fill at the section end (`section_end=True`, into `into=` - the next section's first chord,
  default the progression's own first chord).
* **Kick lock**: `kick=` a drum Clip (its kick notes 35 / 36) or a 16th pattern `'x.....x.x.......'`, looped over
  the clip. A swung or humanized drum clip is read on its 16th grid (each kick snapped to the nearest 16th within
  0.07 beats) and the bassist plays the drummer's 16th swing (measured from the kicks on the e / a; `swing=` sets it,
  0.5 = straight, 0.5..0.8 or 50..80 %; applied as a time warp, so a slide's pluck and glide stay a pair). Notes
  near a kick snap onto it, missing kick hits are doubled (`lock` 0..1: 1 = every kick; style defaults rock / pop
  0.8), dead notes on a kick become real notes; `.locked` reports the share. Funk interlocks instead
  (`interlock=True`, its default): the one together with the kick, a note on a later kick moves a 16th off it (it
  stays with the kick where both neighbours are taken), dead notes leave the later kicks too - bass and kick
  alternate instead of masking each other.
* **Budgets**: FILL_KINDS fills at most one per `fill_every` bars (default 8, funk 4: the section end first, then
  8- / 4-bar phrase ends); `FLASH` moves (slide, slide_out, hammer_on, pull_off, octave_pop, rake, walk_up) at most one
  per `flash_every` bars (rock / pop / ballad 4, funk / motown / country 2, synth / tumbao 8), the same kind 2 x
  `flash_every` apart; the best-placed candidates win (a slide into the first note of a section, a slide-out before a
  rest / at the end, a walk-up into a change). One gesture at a time: a flashy move never shares a bar with a fill
  (the bar before it, the fill, the bar it lands in - song-wide with a Memory), and an `ending=` owns the last bar
  (no fill, no move there). `memory=bassist.Memory()` + `at=` counts them song-wide
  (`mem.played(at, 'slide')` books a hand-placed move). Approach notes, passing tones and a funk groove's dead notes
  are the language and not budgeted (`approach=` sets their chance); an approach always leads into the note that
  follows it (a step / a 4th-5th away; into a fill's first note where a fill replaced the change).
* **Touch** (`touch(clip, lo, hi, beats_per_bar=4, phrase=4, melodic=False, kick=(), changes=(), ghost=(22, 40))`, the
  model arrange uses): the one strongest, beat 3 ~0.85, 2 / 4 ~0.78, off 8ths ~0.66, 16ths ~0.56 of the way from lo to
  hi, the chord changes and the kick notes a little stronger, 4-bar arcs (+-3 %; walking +-10, ballad +-7), approaches
  lighter, fills crescendo, the second note of a hammer-on / pull-off softer, dead notes 20-40; melodic styles (motown, ballad, reggae, walking):
  higher notes sing out. `technique='slap'`: thumb roots 104-115, popped octaves 116-127 (the slap bass's layers).
* **Timing**: baked into the clip with `articulation.humanize_starts` (note ends kept, a slide's or hammer-on's pair
  moves together): the style's lay-back (`late_ms`: reggae +14, ballad +8, motown +4, pop +3, rock 0, funk -2, walking
  `layback_ms('bass')`: on top) + seeded jitter (`timing_ms` 2-6). Don't `track.humanize()` the bass again; on a
  track that already has a groove (the jazz bands) pass `late_ms=0`; `timing=False` leaves the grid.
* **Playability**: `strings=4` E1-G3, `5` B0-G3 (`RANGES`), roots from `low` (the octave nearest the previous root,
  pulled down), everything folded into the range, one note at a time (a slide's pluck and a hammer-on's pair overlap
  ~0.03 beats: a legato transition). `fingering(clip, bpm, strings=4)` plans the fretting hand (a 4-fret span, open
  strings free, a shift of d frets takes ~60 ms + 12 ms per fret); `check(clip, bpm, strings=4, low, high)` lists
  notes out of range, notes sounding over the next one, and jumps no hand makes in time (`.problems`). arrange()
  re-fingers a jump it can't make at a fast tempo (the chord span moves an octave, its approach note with it).
  Tempo limits of the plucking hand (`FAST`): cells with runs of 3+ 16th attacks (dead notes count) only up to 165
  bpm, 16th pairs (gallops, a popped octave a 16th after the root) up to 200 bpm; above, the 16th funk fill and the
  rake are left out and a last guard drops the weakest note of any such run (a dead note, an approach, an off-beat
  note - never a beat, a change or a move / fill note). `technique='synth'` has no limit.
* **Articulations and slides on a track** (`place` / `adapted`): the clip carries `'staccato'` (short notes in
  staccato styles / a verse) and `'mute'` (dead notes) marks and glide marks on slides. `place()` maps them to what
  the patch has (`'staccato'`, `'mute'` -> its mute / ghost / dead note; dropped where it has none, e.g. sf2), and
  plays slides as glides on a `mono='legato'` sampler, else merges each slide into its pluck + `'instrument.pitchbend'`
  points (samplers, sf2, dx7, stacks; instruments without a pitch bend lose the slide).

Named MOVES (each a Clip from `at`; `MOVES` = name -> function): `approach(target, bpm, kind='chromatic' | 'diatonic'
| 'fifth', above=False, notes=1, grid=0.5)` (the target lands at at + notes x grid), `walk_up(target, bpm, steps=3,
grid=1, direction='up')`, `passing(start, end, dur, bpm, chromatic=False)`, `octave_pop(pitch, bpm, dur=0.5,
grid=0.25, slap=False)`, `slide(pitch, dur, bpm, by=-2, ms=80)` (plucked `by` away, glides in), `slide_out(pitch, dur,
bpm, drop=-7, ms=220)`, `hammer_on(lower, upper, dur, bpm, grid=0.25)`, `pull_off(upper, lower, dur, bpm)`,
`ghost(pitch, bpm, dur=0.12, vel=32)`, `rake(target, dur, bpm, grid=0.25)` (dead notes into the one), `fill(kind,
target, dur, bpm, chord=, key=, grid=None, low='E1', high='G3')` (`FILL_KINDS`: run_up, run_down, chromatic, octave,
pentatonic, triplet, walk_up, rake, sixteenths, slide), `pedal(pitch, dur, bpm, grid=0.5, octave=0)`, `walk(prog,
bpm, key=, feel='four', ...)` (walking_bass + the bassist's touch, skip notes as dead notes). `arrange(pedal='E1' or
[(start, end, 'E1')])` keeps the groove's rhythm on a pedal note; `ending='ring'` (the last bar: the root held) or
`'slide'` (held, then a slide out).
## The guitarist (`agentsound.guitarist`)

A virtual guitar player, built like the pianist: named MOVES (each usable alone), two arrangers that choose them by
context and seed, BUDGETS that keep flashy moves rare, touch dynamics, human timing, playability, and a log of what
was played. Every guitar part - acoustic steel / nylon, clean, crunch, distorted, lead - goes through it
(HUMAN_FEEDBACK: realistic, never keyboard-like; flat velocities are robotic; flashy moves are spice, not habit).

```python
from agentsound import guitarist as gtr
mem = gtr.Memory()                                   # one per player and song: budgets + the last shape
for sec, pr in ((verse, 'Em C G D'), (chorus, 'C G D Em')):
    arr = gtr.arrange(s.prog(pr), bpm=s.tempo, key=s.key, style='rock', section=sec, sound=b.gtr_l, memory=mem,
                      seed=11, next_chord='C')
    arr.play(b.gtr_l, sec)                           # notes with palm-mute / dead-note marks
    arr.take(2).play(b.gtr_r, sec)                   # the double-tracked second take
ld = gtr.lead(line, s.prog('C G D Em'), bpm=s.tempo, key=s.key, style='rock', section='chorus', sound=b.lead,
              memory=lead_mem, at=chorus.bar(4), climax=True)
ld.play(b.lead, chorus.bar(4))                       # notes + pitchbend (bends) + vibrato automation
gtr.bend('A5', 6, s.tempo, rise_ms=260).play(b.lead, end)          # a move on its own (a Lick)
b.acoustic.play(gtr.hammer_chord('D', 2, s.tempo, sound=b.acoustic), verse.bar(3))
```

**Fretboard.** `Fretboard(tuning='standard' | TUNINGS name (drop_d, half_down, full_down, drop_c, dadgad, open_g,
open_d, open_e) | six pitches, capo=0, frets=20, stretch=4)`: `.positions(pitch)`, `.fingers(frets)` (a barre counts
once), `.playable(frets)` (<= 4 fingers, fretted notes within one hand's reach: 3 frets apart low on the neck, 4
above the 7th fret). `shapes(chord, kind='open', fretboard=, tuning=, capo=)` -> every playable `Shape` (frets low E
first, None = muted; `.pitches`, `.notes`, `.strings`, `.fingers`, `.span`, `.pos`, `.diagram()` 'x32010'), the most
idiomatic first; `shape(chord, kind, near=)` the best; `KINDS`: open (first-position chords: C x32010, G 320003, Am,
Em, D, F 133211 when no open shape fits), barre (E / A shapes, no open strings), full, power (root + 5th [+ octave] on
2-3 low strings), upper (3-4 note grips on the D-G-B-E / A-D-G-B sets, inversions: funk, reggae, pop verses), shell
(1-3-7 on the low strings, Freddie Green). `voice_lead(chords, kind, start=)` the smoothest path (a shape's own cost +
hand movement - position shifts, top-note leaps; common fingers are cheap); `best_capo(chords)` the capo that gives
the most open shapes (Bb Eb F Gm -> 3). Strummed shapes have no gaps between their strings and the chord's bass
lowest; a slash chord puts its bass there (C/E 032010).

**Rhythm hand: `arrange(prog, *, bpm, key=None, style='pop', section=None, energy=None, density=0.5, seed=0,
take=None, technique=None, pattern=None, kind=None, vel=None, fill=None, fills=None, ornaments=None,
section_end=True, next_chord=None, anticipate=None, open_change=None, swing=None, spice_every=None,
fill_every=None, tuning='standard', capo=0, fretboard=None, sound=None, articulations=None, memory=None, at=None,
length=None, into=None, strings=None)`** -> `Arrangement` (`.clip`, `.play(track, at)`, `.take(n)` - the same part played again with new
timing / velocity noise for a double-tracked guitar -, `.moves` [(start, end, kind, name)], `.shapes` [(beat,
Shape)], `.budget`, `.energy`, `.technique`, `.summary()`, `.count(kind, name)`). The SECTION decides (`section=` a
Section - name, length, start - or a name; `SECTION_ENERGY`: intro .35, verse .45, pre .62, chorus .85, post .75,
bridge .55, solo .8, break .4, outro .4; `energy=` overrides): the style's technique for it, the velocity range
(low energy ~61-94, chorus ~75-112), how many strings an up-stroke takes. `STYLES` (technique per section):

| style | intro / verse | pre | chorus | outro | fills | ornaments |
|---|---|---|---|---|---|---|
| pop | arpeggio / muted8 (palm-muted 8ths) | eighths | strum (D . d U . u D u) | ring | build, bass_run, choke | hammer_chord, sus4 |
| folk | travis / travis | strum | strum | let_ring | bass_run | hammer_chord, sus4 |
| rock | chug (palm-muted power 8ths) | drive (8th power downs) | power (ringing, pushes) | ring | choke, build, slide_chord | slide_chord |
| punk | downs | downs | downs | ring | choke, build | - |
| ballad | let_ring / arpeggio | arpeggio | ballad_strum | let_ring | bass_run | hammer_chord |
| funk | scratch (16th dead-note scratch, high grips) | = | = | = | choke, slide_chord | slide_chord |
| reggae | skank (short chops on 2 and 4) | = | = | = | choke | - |
| country | boom_chick (bass note + strum) | strum | strum | let_ring | bass_run | hammer_chord, sus4 |
| indie | arp16 (jangle) | eighths | eighths | ring | build, choke | hammer_chord |
| jazz | four (shells, four to the bar) | = | = | = | - | - |

`TECHNIQUES` (strum, strum16, eighths, downs, ballad_strum, arpeggio, arp16, travis, let_ring, muted8, chug, drive,
power, scratch, skank, four, boom_chick, ring): patterns with weights, the variant for the last bar of every 4-bar
phrase, the shape kind, the strum spread, up-stroke strings, gate (s) for chops / scratches. `PATTERNS`: (grid,
tokens) - `D` / `d` down strum (accent / normal), `U` / `u` up strum, `X` / `x` dead strum, `P` / `p` palm-muted
downstroke, `B` bass string, `A` alternate bass, `1`-`4` a string from the top, `+` together (`B+1` a pinch), `o` a
ghost up, `.` nothing (the strings ring); any token string works as `pattern=` (e.g. a composed riff rhythm 'P . p .
p p D .'). The picking hand: a downstroke low -> high, an upstroke high -> low on the top 3-4 strings, lighter; the
spread in ms for six strings (folk 16-30, rock 7-14, a let-ring 40-70), the stroke centred a little before the beat;
per-string velocities (a down digs into the middle strings, an up rings the top string); every string rings until
it is struck again, damped (a chuck) or the chord change takes it: a string that does not keep its fret stops
(fretted ones lift 10-18 ms early; an open string the new grip frets or leaves out is damped - no low E ringing on
under a D chord), a common tone on the same fret rings on. The hand has a speed limit (a strummed chord ~10.5
strokes / s, a chug ~13, a picked string ~14): a style's 16th pattern faster than that (16th strums above ~158 BPM)
is played on the 8th grid (logged as 'pattern ... (8ths: tempo)'; a build fill too). Dead strums,
palm mutes and hammer-ons use the guitar's own articulations (`sound=` a track / patch: its 'palm mute', 'dead note',
'hammer-on', 'muted' keyswitches; `articulations={'palm': ..., 'dead': ..., 'hammer': ...}` overrides), else short,
lighter notes emulate them. Accents (the one, the backbeat), a gentle arc over each 4-bar phrase, a crescendo into
a louder next section, human timing (3-7 ms, seeded; reggae / ballad laid back). The fretting hand: shapes of the
technique's kind, voice-led (`memory=` continues from the last shape), anticipations (a stroke an 8th before a change
takes the new chord: `anticipate`), the open-string stroke of a hand already travelling (folk / pop: `open_change`).
Ornaments on chord changes (`RHYTHM_ORNAMENTS`: hammer_chord - the 3rd hammered on from the 2nd, Dsus2 -> D; sus4 -
pulled off from the 4th; slide_chord - the grip slid in from two frets below; in a picked pattern the grace string
is picked where the pattern reaches it and the finger hammers half a step later) and a FILL into the next section
(`FILLS` in the last 1-2 beats with `section_end=True`: build - 16th strums, crescendo; bass_run - a bass-string walk
into `next_chord`; choke - a hit, then silence; slide_chord - the next chord slid into on the & of 4). `into=` the
next section (a Section or a name) makes it a transition: into a bigger section the fill is (nearly) certain and
leans to build / choke / slide, into a quieter one it is rarer and never a build; a picked part (arpeggio, Travis,
let ring) ends in a bass run or just rings on - a choke or a build only into a clearly bigger section (energy + more
than 0.1). `strings='top5'` (or 'top4'): the downstrokes leave the low strings to the bass (an acoustic in a full
band) - chord-change ornaments, palm mutes and the fill's strums keep to them too.

**Lead hand: `lead(melody, prog=None, *, bpm, key=None, style='rock', section=None, energy=None, density=0.5, seed=0,
touch=True, sound=None, mono=None, articulations=None, moves=None, flash_every=None, spice_every=None,
fast_every=None, same_every=32, fill=None, climax=False, vib=None, tuning='standard', capo=0, fretboard=None,
memory=None, at=None)`** -> `Arrangement` with `.auto` ({'instrument.pitchbend' / 'instrument.vibrato' /
'instrument.vibratorate': points}; `.play(track, at)` writes it, vibrato only on a sampler). The line is fingered
(a position that shifts as little as it can, the middle of the neck, fretted notes), given `touch()` phrase
dynamics (touch=True: the style's range, raised with the energy; (lo, hi); False keeps the written velocities) and
PICKED (a 14 ms gap before the next note: a new attack even on a mono='legato' sampler) except where the hand slurs:
a hammer-on / pull-off between close notes on one string, a slide into a leap on one string, a scoop into a phrase
(tied: a mono='legato' sampler plays no new attack - `mono=` is read from `sound=`; on a polyphonic guitar the
'hammer-on' articulation or soft passed frets); besides the budgeted moves the style's legato phrasing ties close
steps within a phrase now and then (rock 0.2, blues 0.25, pop 0.3, jazz 0.45, ballad 0.75 - a singing ballad lead
picks less; logged as 'phrasing'; only on one string within 4 frets, never out of a bent note). Long notes get a
finger vibrato (the style's depth / rate, delayed, growing); moves by context: a BEND into a long phrase-peak / phrase-end note (always proposed for the clip's last
long note; a whole step only on the D, G, B, E strings - the wound low strings bend a half step -, the fretted
note at the 2nd fret or higher, never a written double stop), a PRE-BEND released into the next note a step below
(the string is pushed up silently before the pick, so it needs a rest of 120 ms or more before the note - the pitch
wheel moves the whole track; with `memory=` the previous part's last note counts), a RAKE into an accented phrase
start (a rake or a scoop needs room before its note: not on the very first beat of a part), a DOUBLE STOP
on a long chord tone (polyphonic only), a TRILL / TREMOLO picking on a very long note (tremolo only with
`climax=True`), a LICK in a gap of 1.5+ beats. `LEAD_STYLES`: rock, blues, ballad, pop, country, jazz (move weights,
vibrato, budgets, lay-back, touch range); `moves=` overrides the weights.

**Budgets** (song-wide with `memory=` a `Memory()` shared by a player's calls, `at=` the part's position; the
best-placed candidates first - a phrase end, the top of the line, a long note - the rest logged as 'dropped'):
`FAST` (trill, tremolo_pick) at most one per `fast_every` bars (rock / blues / country 16; ballad / pop / jazz 0 =
never), two of a kind `same_every` (32) bars apart; `FLASH` (bend, prebend, rake, double_stop, lick, harmonic and the
rhythm hand's slide_chord / build / choke) one per `flash_every` bars (lead: rock 2, blues 1.5, ballad 3, pop 4,
country 2, jazz 8; rhythm: `fill_every`, 4-8); `SPICE` (slide, hammer_on, pull_off, scoop, hammer_chord, sus4,
bass_run) one per `spice_every` bars (lead 1-2, rhythm 2-8). `Memory.played(at, name)` books a move placed by hand.

**Moves** (`MOVES`; rhythm moves return a Clip, bend / prebend / vibrato a `Lick` = a Clip + `.auto`, `lick.play(track,
at)`): `strum(chord | Shape, dur, bpm, direction='down' | 'up', strings='all' | 'topN' | 'lowN' | 'mid' | [..],
spread_ms=24, vel=90)`, `chuck(chord, bpm, dead=)`, `strum_pattern(prog, bpm, pattern='pop', kind='open', vel=(62,
100), anticipate=0.25)`, `arpeggio(prog, bpm, pattern='arp_ballad')`, `travis(prog, bpm)`, `chug(prog, bpm,
pattern='chug')`, `skank(prog, bpm)`, `scratch(prog, bpm, pattern='funk')`, `let_ring(chord, dur, bpm, ms=70)`,
`hammer_chord(chord, dur, bpm, sus=2 | 4, delay=0.5)`, `slide_chord(chord, dur, bpm, frm=-2, ms=110)`, `bass_run(frm,
to, dur, bpm, key=, notes=3)`, `choke(chord, bpm, hold=0.5)`, `build(chord, dur, bpm, vel=(58, 108))`; lead:
`bend(pitch, dur, bpm, amount=2, rise_ms=110, release=None)` (fretted `amount` lower, pushed up; release= a share of
dur: bend and release), `prebend(pitch, dur, bpm, amount=2, release=0.5)`, `vibrato(pitch, dur, bpm, depth=28,
rate=5.6)`, `slide(frm, to, dur, bpm, legato=True)` (a glide mark on a mono legato sampler, else the frets passed
softly), `hammer_on(frm, to, dur, bpm)` / `pull_off`, `trill(pitch, dur, bpm, rate=11)` (hammer / pull, light),
`double_stop(top, dur, bpm, chord=)` (the diatonic 3rd / 4th / 6th below that is a chord tone), `rake(pitch, dur,
bpm, strings=3)` (dead strings, then the note), `harmonic(pitch, dur, bpm, art=)` (sampled/concert_guitar has real
flageolets on G#5-G7), `tremolo_pick(pitch, dur, bpm, rate=12)`, `lick(chord, dur, bpm, notes=5)` (pentatonic,
hammer / pull pairs, landing on a chord tone). Bends move every sounding note of a track: keep them on a
monophonic lead track (the rock_band / power_ballad / pop_band `lead` roles are mono='legato').

Reused: `humanize.touch` (lead dynamics), `articulation.vibrato_points` / `articulation._mark` / `available` (vibrato,
articulation and glide marks, the guitar's keyswitch names), `patterns` (Clip, Note, the progression loop), `theory`
(chords, chord scales). Tested in `tests/python/test_guitarist.py` (playability, budgets over 40 seeds, determinism,
shaped velocities, timing bounds).

## The lead guitarist's hands (`agentsound.fretwork`)

The guitar hero's micro-performance, built like the hornist's breath: a rock / blues / fusion lead is not a line of
picked notes. Every move returns a `soloist.Part` (the notes as a guitarist writes them - a bent note at its FRETTED
pitch - plus `gesture.Gesture`s on the shared lanes, latched per-note steps and aux notes); `fretwork.render(track,
parts, at)` writes them: the notes through `patches.hero_guitar.play` (glides and the velocity-zone lock on a hero
stack), then every lane ONCE (one automation lane per target, so moves from anywhere merge).

```python
from agentsound import fretwork as fw
parts = [fw.bend('A4', 3, s.tempo, amount=2),                        # G4 pushed up a whole step, vibrato below A4
         fw.prebend('C5', 2.5, s.tempo).shifted(4),                  # bent silently, picked, released
         fw.legato_run(['A4', 'C5', 'D5', 'E5', 'G5', 'A5'], 1.5, s.tempo).shifted(8),
         fw.pinch('E4', 2, s.tempo).shifted(10),                     # the squeal (partial 6), wide vibrato
         fw.feedback('A4', 6, s.tempo, partial=2).shifted(13),       # the held note blooms into its octave
         fw.wah(4, s.tempo, kind='wacka').merge(fw.picked_run(['E5', 'G5'] * 4, 4, s.tempo)).shifted(20)]
fw.render(lead, parts, at=solo)
```

**Pitch.** `bend(pitch, dur, bpm, amount=2, rise_ms=None, delay_ms=0, overshoot=None, settle_ms=120, release=None,
release_ms=200, vib='rock', back=None)` - amount 1 / 2 / 3 / 4 semitones (half / whole / 1.5 / 2 steps; the rise takes
95 / 140 / 190 / 240 ms), a fast rise that overshoots 4 + 3 x amount ct and settles, held with a vibrato that goes DOWN
from the bent pitch, release= a share of dur; `prebend(pitch, dur, bpm, amount=2, release=0.4, pre_ms=90)` (the lane
steps up in the silence before the pick); `ghost_bend` (a soft pick, the release heard, swelling); `unison_bend(pitch,
dur, bpm, amount=2, mono=True)` and `oblique_bend(top, dur, bpm, interval=5)` - the held string never bends: on a mono
lead (`mono=True`, the hero stacks) it plays on the `twin` aux track (`twin_track(song, lead)`: the same patch, its own
pitch), on a polyphonic guitar it is latched out (`bendfollow` 0 then 1: the sampler's per-note bend latch);
`vibrato(pitch, dur, bpm, style='rock')` - finger vibrato UP from the note (`VIBRATOS`: narrow 24 ct / 6.4 Hz, rock
45 / 5.7, wide 70 / 5.0 (Gilmour), blues 85 / 4.6 (Gary Moore), bb 60 / 6.8 (B.B. King), shred 110 / 7.0, subtle 14 /
5.6), delayed, widening on a long note, a little uneven; `whammy_vibrato` (centred: the bar goes both ways),
`whammy_dive(pitch, dur, bpm, semis=-12)`, `whammy_scoop`; `slide_in(pitch, dur, bpm, frm=-4)` / `slide_out(pitch,
dur, bpm, semis=-7)` (the bend lane), `slide(frm, to, dur, bpm)` (a shift slide: a glide mark, `squeak=True` a finger
noise).

**Legato and picking.** `hammer_on` / `pull_off` (tied: a mono='legato' sampler plays no new attack, softer),
`trill(pitch, dur, bpm, upper=2, rate=11)` (one pick, the rest tied; FAST), `legato_run(pitches, dur, bpm,
per_string=3)` (only the first note on each string picked), `picked_run(pitches, dur, bpm, group=4)` (every note
picked - a small gap before each pick -, downstrokes stronger, group starts accented, a crescendo, pick accents also
as 'air' after the compressor), `tremolo_pick(pitch, dur, bpm, rate=13)`, `sweep(pitches, dur, bpm,
direction='updown')` (one note per string, muted as the next sounds, a hammer / pull turn at the top), `rake(pitch,
dur, bpm, strings=3)` (choked scratches under a palm-mute plateau into the note), `accents(notes, bpm)`.

**Tone.** `pinch(pitch, dur, bpm, partial=None)` - the note's partial (`pinch_partial`: 3-6, the highest under ~2.6
kHz) brought out from the pick on (the sampler's `harmonic`, stepped up a few ms before the note) with a wide vibrato
on top; `feedback(pitch, dur, bpm, partial=2, start=0.3, bloom_s=1.4, amount=0.85)` - a held note blooming into its
octave / twelfth, held at the note's peak level (it sustains like feedback), a little louder, vibrato on top;
`palm_mute(pitches, dur, bpm, grid=0.25)` - short chugs under a `mute` plateau (the voices' low-pass closing to
~650 Hz: thud, not ring); `wah(dur, bpm, kind='swell' | 'close' | 'wacka' | 'cocked')` and `wah_talk(clip, bpm)` (the
foot opening on every pick) - the `wah` fx inserted AHEAD of the amp (`wah_stage(track)`: in every zone of a hero stack,
switched in by the `wahmix` lane); `pick_scrape(dur, bpm)` and `squeak(bpm)` on the `noise` aux track
(`noise_track(song, lead)`: band-passed noise through a crunch amp, its filter following a gliding note).

**Targets** (`targets(track)`): bend -> `instrument.pitchbend` (a stack forwards it); harm / mute / the steps -> every
sampler layer's `harmonic` / `cutoff` / `bendfollow` / `harmonicnum`; wah / wahmix -> the wah stage's `pedal` / `mix`;
air -> the breath stage `fx.air.gain` (hornist.air_stage: after the compressor); echo -> `fx.echo.mix` (the hero's own
echo: throws); vib -> each sampler's `vibrato`. Engine: the sampler's `bendfollow` (latched per note), `harmonic`,
`harmonicnum`, `harmonicfocus` and the `wah` effect (docs/PARAMS.md). `guitarist.lead(..., gestures=True)` plays a
written line with these bends and vibrato (`.gestures`, `.part()`, `.play(track)` via render). Tested in
`tests/python/test_fretwork.py`, `tests/test_sampler.cpp` (guitar techniques), `tests/test_wah.cpp`.

## The wind player (`agentsound.hornist`)

A sax / trumpet / trombone / flute / clarinet player (bowed strings reuse the air moves as bow pressure), the
pianist's shape for the breath: a held wind note is never one level. User feedback 2026-09-30 (lamplight-avenue, the
Baker Street homage): "da spielt er eine Note und pustet mal kurz mehr, mal kurz weniger" and "die bewegen das Sax
gezielt und gewollt relativ zum Mikrofon". The player moves the AIR inside the note (a short push on the beat,
pulses with the groove, a swell, an fp, a bloom, a taper at the phrase end), the PITCH with the air (vibrato that
deepens as the air grows, a tiny lift with a push, scoop / fall / doit, rarely a shake or a growl) and the BELL
relative to the MIC (leaning in on the big notes, turning away on the soft endings).

```python
from agentsound import hornist
mem = hornist.Memory()                                   # one per player: budgets count song-wide
perf = hornist.arrange(HOOK, s.tempo, family='sax', style='hero', section='riff', peaks=(1, 9, 17),
                       vel=(84, 118), seed=10, memory=mem, at=riff)
perf.place(sax, riff)                                    # the notes + every lane on this track's targets
perf.add(hornist.fall(31.4, s.tempo, semis=-4))          # a hand-placed move (before place): sampled with the rest
print(perf.summary(), perf.budget)                       # what it played, what the budget dropped
hornist.render(sax, [hornist.push(8, 2.5, s.tempo, db=3).shifted(riff.start)])   # moves on their own
```

**arrange(melody, bpm, family=, style=, section= | energy=, peaks=, vel=(lo, hi), seed=, climax=, memory=, at=,
depth=1, accent=0.12, legato=True, breath_ms=160, humanize_ms=4, late_ms=0, held=0.45, \*\*overrides)** ->
`Performance` (`.clip` as played, `.gestures`, `.moves` log `(start, end, kind, name)`, `.budget` {every bars,
'kept', 'dropped'}, `.lanes(at)` the sampled abstract lanes, `.place(track, at, room=, level=, vibrato=, accents=)`,
`.add(*gestures)`). Phrasing: `touch()` velocity arcs (vel=), legato inside the phrases (`articulation.legato`),
breaths (`jazz.breathe`), a player's timing. Per phrase the note-to-note dynamics as air (`accents`: (vel - the phrase
mean) x `accent` dB; placed only on a compressed chain, where the velocities alone are squeezed flat). Per HELD note
(>= 0.45 s and 3/4 beat): the hook peaks (`peaks=` beats in the clip) and each phrase's highest held note get the most
air - a swell or a bloom, often a push on a beat inside it, vibrato (the family's `peak_vib_ct`), `lean_in`
(section energy >= 0.85); long notes (>= 2.5 beats, 1.6 s) `pulse`, else a swell / push; a long phrase opener now and
then an `fp_cresc`; other held notes a `push` or a `bloom` or nothing (not every note breathes the same), gentle
vibrato on some; phrase ends `taper` + `breath_release`, `fade_away` on soft ones, a `fall` / `doit`; phrase openers
and leaps up a `scoop`; with `climax=True` / on the last hook peak a `shake` (sax, trumpet) or `growl` (sax,
trombone). All depths x (0.8 + 0.3 x section energy) x `depth` (`SECTION_ENERGY`: verse 0.55, pre 0.75, chorus / hook
/ riff 1.0, solo 0.9, climax 1.15, outro 0.85), varied +-15-25 % (seeded). `FAMILIES`: sax, trumpet, trombone, flute,
clarinet, strings (vibrato depth / rate / delay, push depth, the pitch lift, tone per dB of air, scoop / fall / doit
chances, shake / growl, vibrato-air coupling). `STYLES`: hero, pop, ballad, jazz, classical (chances per move and the
budgets). Any key of either as an override (`push=0.8`, `peak_vib_ct=30`, `mic_every=8`).

**Budgets** (song-wide with `memory=`; best-placed first, the rest in `.budget['dropped']` with their substitute):
`FAST` (shake, growl) one per `fast_every` bars (hero 24, pop / jazz 32, ballad / classical never), structural moments
only; `SPICE` (scoop, fall, doit) `spice_every` (1.5-4); mic moves `mic_every` (hero 4, pop 6, jazz 8, classical 16);
`pulse` / `fp_cresc` `pulse_every` (a dropped pulse becomes a push, a dropped fp a bloom). `Memory.played(at, name)`
books a hand-placed move, `Memory.save(at)` keeps the FAST budget for the climax.

**Moves** (`MOVES`, defined in the shared `agentsound.gesture` and re-exported; each returns a `Gesture` of additive
shapes on the abstract `LANES`: air, bright, bend, vib, mic, prox, shelf, room (+ harm, wah, wahmix, mute, echo for
the guitar); positions in beats, times in s / ms): air - `push(start, dur, bpm, at=, db=2.5, ms=160, rise=0.35,
lift=5, bright=0.35)` (on the first beat / syncopation after the attack by default), `pulse(start, dur, bpm, n=,
every=1, db=2, ms=140, fade=0.85)`, `swell(start, dur, bpm, lo=-3, peak=2, end=-2, peak_at=0.55, tied=, back=)`,
`messa_di_voce(...)` (-5 / +2.5 / -5), `fp_cresc(start, dur, bpm, dip=-6, dip_ms=180, bloom=2)`, `bloom(start, dur,
bpm, under=-3, ms=320)`, `taper(start, dur, bpm, db=-5, frac=0.45, back=)`, `breath_release(end, bpm, db=-9, ms=110,
drop=-12)`, `accents(notes, bpm, db_per_vel=0.12)`; pitch - `vibrato(start, dur, bpm, depth=22, hz=5.4, delay=0.28,
grow=0.5, rise=0.3)`, `scoop(start, bpm, cents=-70, ms=90)`, `fall(end, bpm, semis=-3, ms=200, back=, air=-6)`,
`doit(end, bpm, semis=3)`, `shake(start, dur, bpm, interval=3, hz=6.5)`, `growl(start, dur, bpm, db=1.6, cents=10,
hz=27)`; mic - `lean_in(start, dur, bpm, db=2, prox=2.5, bright=1.8, room=-3)` (closer: louder, the proximity lift at
300 Hz, brighter, drier), `turn_away` / `off_axis(start, dur, bpm, shelf=-4, db=-1, room=2.5)` (darker above
3.2 kHz, quieter, more room), `bell_swing(start, dur, bpm, seconds=1.2, shelf=-3, room=2)` (on -> off -> on axis
inside a long note), `fade_away(start, dur, bpm, shelf=-5, db=-4, room=3, frac=0.6)` (turning away while tapering).
Phrase-end shapes hold into the tail and return to rest before the next onset (`back=`). Every shape is cosine
keyframes with zero slope at each key, sampled every <= 20 ms: no zipper; steps only at a scoop or into a note after
a rest.

**Targets** (`targets(track)`; measured in `TARGET_MEASUREMENTS`: a +3 dB push on each target of a held note):

| sound | expression | dynamics +0.25 | after the chain | the air goes to |
|---|---|---|---|---|
| `layered/hero_sax` / `hero/sax` (3:1 compressor) | +1.35 dB | +0.5 dB | +3.0 dB | the breath stage `fx.air.gain` |
| `sampled/alto_sax`, `trumpet`, `flute` (plain) | +3.0 | +0.1..0.2 (tone only) | +3.0 | `fx.air.gain` (+ the tone on the mic shelf) |
| `sampled/tenor_sax`, `solo_trumpet`, `solo_flute`, `solo_clarinet`, `solo_trombone`, `trumpet_harmon`, `solo_violin`, `solo_horn` (live dynamics, no compressor) | +3.0 | +2.6..7.9 (with the louder layer's tone) | +3.0 | `instrument.dynamics` (`DYN_SENS` dB per unit; home lowered by `HEADROOM` 4 dB, made good on the mic stage) |

The breath stage is `agentsound.heroes`' convention: a utility named `air` at the end of the chain, after every
compressor and the saturation (every `hero/<preset>` has one; `air_stage(track)` inserts it when missing, so any
compressed lead works). `mic_stage(track)` appends an eq named `mic` after it, always last (peak1 at 300 Hz =
proximity, a gentle high shelf from 3.2 kHz = the axis, output = distance): the mic moves and the air's tone go there,
the room offsets to the track's reverb sends (plate / hall / room ...: not the echo, which `articulation.throws` owns),
bend to `instrument.pitchbend`, the vibrato to the sampler's `vibrato` / `vibratorate` (every sampler layer of a stack;
depth x (1 + couple x air dB)), else a pitch-bend lfo. A compressed chain gets the `accents` after the compressor (the
note-dynamics ear counts an automated insert gain stage as played dynamics): measured on the lamplight hook,
`layered/hero_sax` moves 1.2 dB per 10 velocity steps before its chain and 0.35 after it (the 3:1 compressor); the
accents' 0.12 dB per velocity step give the 1.2 back after the compressor (its takes sum to their power sum within
0.05 dB before the chain - measured through the compressor each variant is compressed on its own). Don't also write
`art.perform(shapes=...)` / `art.vibrato` on a track the hornist plays (one lane per target).

Measured (Baker Street, the sax riff's held notes in the record - analysis only: the harmonics of the tracked f0):
level inside a held note 3.7-7 dB (p5-p95, 90 ms smoothed; median ~4.5), 1-3 bumps of 2-4 dB lasting 100-170 ms,
vibrato +-20-30 ct at 5.4-5.5 Hz on the held peaks, brightness moving 4-12 dB within a note and only loosely with the
level (the bell / mic, not only the air). The defaults aim there. Tested in `tests/python/test_hornist.py`.

## The soloist (`agentsound.soloist`)

An instrument-agnostic SOLO builder: one wrapper that turns any player's vocabulary of moves into a solo with a
dramatic arc - a low motif, call and response, repetition with variation, a speed burst, the climax, the resolution
- with motivic development of the song's hook, breathing space (rests are part of the plan), an ornament budget
(tricks stay spice: HUMAN_FEEDBACK "zu viele von diesen schnellen Zwei-Tasten-Wechseln") and a dynamics arc that is
never flat. The instrument lives in its `Vocabulary` (the guitar's: `guitarist.vocabulary(...)`; the hornist's and
the drummer's plug in the same way); the soloist only plans.

```python
from agentsound import soloist, guitarist as gtr
vocab = gtr.vocabulary('rock')                                 # the guitar's moves, motif maker and variations
perf = soloist.solo(s, lead, vocab, at=solo, prog=PROG, motif=HOOK, arc='classic', seed=7)
print(perf.summary(), perf.stages, perf.warnings)              # what it played where, and why
perf = soloist.solo(s, lead, vocab, at=[solo1, solo2], budget=soloist.Budget(spice_every=1, fast_every=8))
perf = soloist.solo(s, lead, vocab, at=(64, 8))                # (start beat, bars)
```

**The interface** (stable: other players implement it):

- `Move(name, beats, energy, density, spice, play, *, fast=False, roles=(), weight=1.0)` - one thing a player can
  do. `beats` the length it wants (0 = it fills the slot it is given); `energy` 0..1 how intense it sounds and
  `density` 0..1 how busy it is (the arc picks moves whose energy / density match the stage, nearest first);
  `spice=True` a trick the ornament budget counts (`fast=True` the rarest kind: bursts, trills, rolls - `fast_every`);
  `roles` where it fits ('motif' 'answer' 'fill' 'develop' 'burst' 'climax' 'resolve'; () = anywhere);
  `play(ctx) -> Part | Clip | [notes]` (positions relative to `ctx.at`).
- `Vocabulary(moves, motif=None, vary=None, *, name='', place=None, register=(0.0, 1.0), vel=(56, 118),
  phrase_bars=2, touch=True, budget=None, range=(48, 84), rest=1.0)` - `motif(ctx) -> Clip` makes a motif when the
  solo gets none, `vary(motif, ctx) -> Clip` develops it (default `soloist.vary`: sequence, invert, fragment, rhythm
  displacement, octave, ornament - by stage), `place(track, perf)` writes the parts on the track (default: the notes
  + every gesture lane via `gesture.render`), `budget` its default `Budget`, `rest` (0..1) scales the space the
  stages plan at the phrase ends (1 for a horn that breathes; the drummer's vocabulary 0.4 - its feet keep the pulse
  through the space).
- `Ctx` (what `play` / `motif` / `vary` get): `song, track, vocab, at` (song beat), `beats` (the slot, the rest
  excluded), `bpm, bpb, key, prog, chord(t=None)` (the chord at a beat, None without `prog=`), `stage, role`
  ('call' | 'response' | 'fill' | 'lead'), `energy, density` (0..1 here), `register` (0..1: low statement .. top at
  the climax), `vel` ((lo, hi) of this phrase: the dynamics arc), `motif` (the current Clip), `phrase, phrases,
  progress` (0..1), `last` (the last note played, absolute), `rng` (seeded per slot), `budget` (for tricks inside a
  move: `ctx.budget.allows(name, at, fast=)` / `ctx.budget.book(...)`), `memory` (a dict the vocabulary keeps per
  solo).
- `Part(clip, gestures=(), log=(), tricks=())` - what a move played: the notes, `gesture.Gesture`s on abstract lanes
  (pitch bend, vibrato, air, harmonic, wah ...), a log `(start, end, kind, name)`, and the tricks inside it
  `(beat, name, fast)` booked in the budget.
- `solo(song, track, vocab, at=section | [sections] | (start, bars), arc='classic', motif=None, budget=None,
  seed=None, *, prog=None, key=None, energy=None, place=True)` -> `Performance` (`.parts` [(beat, stage, role, move,
  Part)], `.clip` (all notes, from `.start`), `.gestures`, `.moves` [(start, end, stage, name)], `.stages` [(stage,
  start, end, energy)], `.budget` {'kept', 'dropped', every}, `.warnings` (like the drummer's: added to `s.advice`
  on place), `.summary()`). `prog=`, `key=` (default `song.key`), `energy=` (scales the arc), `place=False` (plan
  only) are additions to the coordinator's signature.

**Players.** `guitarist.vocabulary(style='rock' | 'blues' | 'ballad' | 'fusion', register=('G3', 'D6'), vel=(62, 122),
weights=, moves=, budget=)` - motif, answer, bend_cry, prebend, ghost, slides, sequence, legato, chug, wah, pinch,
double_stop, shred / sweep / tremolo / trill (fast), scream (a run to the top into a unison / 1.5-step bend, an echo
throw), feedback, dive, resolve (`agentsound.guitar_vocab`: built on fretwork and `lead(gestures=True)`).
`hornist.vocabulary(family='sax', style='hero', register=None, vel=(64, 120))` - motif, answer, riff, long_tone,
scoop_call, fall_off, sequence, run (fast), shake / growl (fast, where the family has them), resolve
(`agentsound.horn_vocab`: lines breathed by `hornist.arrange`; the default place: the notes + `hornist.render`). The
same arc on both (`songs/_demo_soloist`, `tests/python/test_soloist.py`). A vocabulary's `range=(lo, hi)` is the
instrument's solo range (`ctx.range`).

**Material** (shared by every vocabulary; each takes a Ctx): `key_of`, `chord_tones(ctx, t)`, `pentatonic(ctx, t)` (minor
pentatonic on minor / dominant chords, major on major ones, inside the key), `scale`, `snap`, `step`, `fold` / `fit`
(into `ctx.range`), `center(ctx, shift)` (the arc's register), `seconds`, `grid(ctx, max_rate)`, `vel(ctx, x)`,
`merge(*parts)`, `trick(ctx, name, at, fast)` (a trick inside a move, booked in the budget), `motif_in_register`,
`answer_line` (falling to a chord tone), `sequence_line` (a cell sequenced up), `run_line`.

**Arcs** (`ARCS`; the solo is cut into phrases of `vocab.phrase_bars` bars - halved down to one bar while there are
fewer phrases than stages -, each phrase gets a stage by its position):
`classic` statement (low motif, sparse, ~35 % energy) -> answer (call and response: the motif, then a move that
answers it) -> develop (the motif varied / sequenced up) -> burst (the speed burst: the densest moves) -> climax
(the top of the range, the biggest move: a held bend, a scream) -> resolve (the motif's head low, a long last
note); `build` (no resolution: into a final chorus), `ballad` (no burst, more space), `trade` (call / response
throughout: trading 4s), `short` (statement -> climax -> resolve, for 4-8 bars). Every stage carries energy,
density, register, rest share (space at the phrase end: 25-45 %, the burst 10 %) and the velocity range.

**Budget** (`soloist.Budget(spice_every=1.5, fast_every=8, same_every=16, bpb=4)`, shared with
`agentsound.budget`: the guitarist's, hornist's and pianist's budgets are the same mechanism): spice moves at most
one per `spice_every` bars, fast moves one per `fast_every` bars and only in the burst / climax stages, one kind
`same_every` bars apart; `budget.save(beat)` keeps the fast budget for a moment (the climax). Pass one Budget to
several solo() calls to count song-wide. A move the budget refuses is replaced by the best plain move (logged in
`.budget['dropped']`).

## Mixing (`agentsound.mixer`)

The mix engineer's tools: who is the lead, where every other part belongs relative to it in this genre, and the
moves that get the mix there - measured from the report, bounded, logged, and written as explicit code (`MIX`),
never applied silently.

```
python -m agentsound mix songs/<slug>                      # roles, targets, measured balance per section, the moves,
                                                           # and a mix engineer's findings (from out/report.json)
python -m agentsound mix songs/<slug> --auto [--iterations 2] [--section drop1 --section drop2] [--lead ID]
                                                           # render -> measure -> adjust, then verify; writes
                                                           # out/mixer/MIX.py (+ log.txt, pass_N/ renders)
```

```python
from agentsound import mixer
p = mixer.plan(song, 'songs/x/out/report.json')            # MixPlan: .roles .balances .moves .glue, .describe(), .mix()
p = mixer.plan(song, profile='synthwave', hooks=['chorus'])  # no report: the genre's static carve / ride plan
res = mixer.auto('songs/x', iterations=2)                  # AutoResult: .mix .log .before .after .table() .code()
for f in mixer.check('songs/x'):                           # Finding: code, severity, message, fix, mix (a MIX snippet)
    print(f)

MIX = {                                                    # song.py, module level: the CLI applies it at build / check
    'trim': {'keys_lead': 1.5, 'pad': -2.0},               # dB, song-wide (tracks or buses)
    'ride': {'keys_lead': {'drop2': 1.0}, 'pad': {'verse': -1.0}},   # dB per section, on top of the trim
    'duck': [{'targets': ['pad', 'choir'], 'key': 'keys_lead', 'depth': 2.5, 'threshold': -34,
              'attack': 15, 'hold': 60, 'release': 260},  # = s.sidechain(...); 'pitches': 'kick' keys from notes
             {'targets': ['bass'], 'key': 'drums', 'pitches': 'kick', 'depth': 8, 'attack': 2, 'release': 120}],
    'eq': {'piano': [{'freq': 1400, 'gain': -2.0, 'q': 1.0}]},        # 1-3 bells (presence dips, mud cuts)
    'ramp': 1.0,                                           # beats a ride moves before the section start (default 1)
}
# or explicitly, once, at the end of build(): s.mix(MIX)   (not both: applying twice is an error)
```

**What a MIX writes** (all visible in the render JSON): trims and rides go to one `utility` insert named `mixer` at
the end of the node's chain (after its own inserts and duckers, before the fader: the sends follow it; the song's own
`gainDb` lanes stay untouched), a ride is its `fx.mixer.gain` lane (a linear move over `ramp` beats before each
section that changes); ducks are ordinary `ducker`s (`s.sidechain`), eq dips one `eq` insert named `mixer_eq`.
Strict: unknown keys, nodes (with did-you-mean), sections and values out of range are errors.

**Roles**: `lead` (the part in front; per section the loudest lead-role part that plays in half its bars), `bed`
(pads, strings, choir), `rhythm` (drums, percussion), `low` (bass), `other` (keys, arps, comping, counter-lines; a
second lead counts here), `fx` (risers, impacts: not balanced). Explicit arguments (`lead=`, `bed=`, `rhythm=`,
`low=`, `other=`, `roles={id: role}`) > a band's roles (`band=b`; jazz presets: piano and sax lead, comp other) >
the report's `nodes[].role` (a report without a lead: its melodic lead, `nodes[].dynamics.kind`) > the track id.

**Levels**: per bar from the report (`nodes[].barsRmsDb` + each node's K-weighting offset `lufs - rmsDb`), so the
numbers read like the LUFS balances of the recipes and presets; a group (all rhythm parts, all bass parts, all beds)
is summed and compared with the section's lead on the bars both play. The bed uses the report's own
`space.sections[].bedVsLeadDb` when it names the same lead. Sections too short (< 2 bars), quiet (> 12 LU under
the loudest) or without the lead in half their bars are not judged. **Hook sections**: names with chorus / drop /
hook / refrain / lift / climax / finale / peak / head, else the full sections within 1.5 LU of the loudest
(`hooks=` overrides).

**Targets** (dB vs the lead in the hook sections; outside the hooks the band may sit `lead ride` closer, the bed
stays; drums and bass are only judged for being too loud outside the hooks - a softer verse is the arrangement):

| profile | rhythm | low | bed | others at most | lead ride / bed ride | bed ducks under the lead | bass under the kick | dips |
|---|---|---|---|---|---|---|---|---|
| `synthwave` | -5..-2 | -5..-2 | -5.5..-2.5 | -3 | +1 / -1 | 2.5 dB | 8 dB | -2 |
| `dreamwave` | -6..-2 | -6..-2 | -4.5..-2 | -3 | +1 / -1 | 2 dB | 6 dB | -2 |
| `darksynth` | -3.5..+0.5 | -3.5..+0.5 | -6..-1.5 | -2 | +1 / -1 | 2 dB | 8 dB | -2 |
| `jazz` | -16..-13 | -6.5..-3 | -10..-4 | -4 | 0 / 0 | 1.5 dB | - | -1.5 |
| `classical` | -14..-4 | -9..-1 | -8..-1 | -1 | 0 / 0 | - | - | -1.5 |
| `film` | -10..-2 | -8..-1 | -7..-1 | -1.5 | +1 / -1 | 1.5 dB | 4 dB | -1.5 |
| `pop` | -4..-0.5 | -4..-0.5 | -10..-4 | -4 | +1.5 / -1 | 2 dB | 6 dB | -2 |
| `rock` | -3.5..0 | -5..-1.5 | -10..-4 | -2 | +1 / -1 | - | 5 dB | -2 |
| `default` | -5..-1 | -5..-1 | -7..-2.5 | -3 | +1 / -1 | 2 dB | 6 dB | -2 |

Where they come from: the user's feedback (synthwave: "der Lead ist jetzt zu leise" with the bed 0.4 dB under the
hook - the rule is >= 2-3 dB; jazz: "Drums etwas zu laut" at 10-12 dB under the lead, fixed at 13-16), the band
presets' measured balances (pop_band, rock_band, jazz_trio) and the recipes' mix targets. `mixer.PROFILES` holds
them (`MixProfile`); `plan(..., profile=MixProfile(...))` takes your own.

**How auto() moves** (per pass; `iterations` passes, then one more render to verify; stops early when nothing is
off): (1) per section, the part of the error that every group shares is the lead's - its trim is the median over the
hook sections, sections that differ get a ride; the lead rises only while its pre-master peak stays under -0.5 dBFS,
what it cannot rise the band comes down instead. (2) Each group gets the song-wide trim that puts the most sections
inside their window (hooks count double), landing 0.5 dB inside; a level within 0.5 dB outside needs no move. A bed
that crowds the lead is **carved first** (a duck keyed by the lead, `bed ducks` dB) and trimmed for the rest; the
sections the bed trim cannot fix get rides. (3) Other parts above the lead's limit are trimmed. (4) The report's
masking warnings: a part sharing the lead's low-mid / mid / presence band gets a dip there (450 / 1400 / 3300 Hz);
kick and bass overlapping in time get a duck of the bass under the kick (`pitches='kick'`). Every move is at most
`max_step` (6) dB per pass, trims add up to +-12 dB, rides to +-6 dB; everything is logged (`res.log`, `log.txt`,
and as comments over `MIX` in `MIX.py`). Deterministic: the same report gives the same moves. Previews:
`sections=[...]` / `span=(from_beat, to_beat)` render only that range (the moves are judged on what it contains).
Moving the band down lowers the pre-master sum: the master's limiter drive (mastering) sets the final loudness.

**Validated** on scratch copies: children-of-neon with the user's "der Lead ist zu leise" version (before the manual
fix): `check` reports `lead_not_in_front` and `bed_too_loud`; `auto` (2 passes) carved the bed with a 2.5 dB duck
keyed by the hook, trimmed bass -3 / bed -1.5 / drums -0.8 and rode the bed -1 dB in drop2 and the lift: bed vs lead
drop2 +1.0 -> -2.5, lift +0.8 -> -2.8 dB (the manual fix reached -0.7 / -1.0). perry-street-rain with the drums 3 dB
hot (DRUM_TRIM undone, the level the user found too loud): drums -11.0 -> -14.0 dB under the piano in the head
(trim -2.5; the real fix was -3); the song as delivered: drums already inside (-14.5..-16.1), bass trimmed 2 dB.

**check()** findings (most important first, each with a fix and usually a MIX snippet): `lead_not_in_front`,
`bed_too_loud` / `bed_too_quiet`, `drums_too_loud` (`drums_too_loud_for_jazz`) / `drums_too_quiet`, `bass_too_loud` /
`bass_too_quiet`, `part_over_lead`, `masking` (a dip on the part that is not the lead), `low_end_fight` (duck the
bass under the kick), `flat_dynamics` (the player's job, not the fader's), `mud` (200-400 Hz over the profile's
reference: dips at 300 Hz on the biggest low-mid contributors), `harsh` (2-5 kHz: dips at 3.3 kHz; on the lead a
presence dip lets its fader come up), `width_narrow` / `width_over_wide` / `width_phasey`, `low_end_wide`,
`headroom`, `clicks`, `loudness` (info: the master's business). `plan()` also lists **glue** suggestions per genre
(a drum bus compressor, the master glue - or none for jazz / classical).

## Delivery: METADATA, COVER, credits, reference comparison

`python -m agentsound build` also writes `out/credits.txt`, `out/cover.png` and tags `out/mix.mp3` (ID3v2.3: title,
artist, album, album artist, genre, year, BPM, key, comment with the credits, the cover as front-cover picture) so a
phone or Telegram shows title, performer and cover. Two optional module-level dicts in `song.py` (strict keys;
`python -m agentsound check` validates them):

```python
METADATA = {'title': 'Night Drive', 'artist': 'AgentSound', 'album': 'Neon Nights', 'genre': 'Synthwave',
            'year': 2026, 'comment': 'first take', 'track': 3, 'composer': '...', 'copyright': '...'}
COVER = {'style': 'outrun', 'palette': 'sunset', 'title': 'NIGHT DRIVE', 'subtitle': 'AgentSound', 'seed': 7}
COVER = {'style': 'jazz', 'palette': ['#2f6fd8', '#f2a900']}   # 1-3 colours replace the style's main accents
COVER = {'file': 'art/cover.jpg'}                               # your own picture (relative to the song folder)
COVER = False                                                   # no cover
```

| key | default |
|---|---|
| `METADATA['title']` | the `Song` title (also the cover title) |
| `METADATA['artist']` | `'AgentSound'` (also the cover subtitle) |
| `METADATA['album']` / `['genre']` / `['year']` | `'AgentSound'` / from the cover style (`film` profile: Soundtrack, `piano`: Classical) / this year |
| `COVER['style']` | the analysis profile if it is a style (`synthwave`, `dreamwave`, `darksynth`, `jazz`, `classical`, `pop`, `rock`; `film` / `piano` -> `classical`), else a style named in `METADATA['genre']`, else `synthwave` |
| `COVER['palette']` | the style's first palette; `agentsound cover --list` lists them |
| `COVER['seed']` / `['size']` | the song seed / 1400 px |

Cover styles (engine `agentsound cover --style S --title T [--subtitle S] [--seed N] [--palette P] --out cover.png`):
`synthwave` (sunset grid, striped sun, chrome title), `outrun` (road, palms, mountains), `dreamwave` (pastel haze,
thin glowing type), `darksynth` (red/black, neon triangle, glitch), `jazz` (duotone halftone record, colour block,
bold condensed lower case), `classical` (paper, gold circle and rules, high-contrast serif capitals), `rock` (grit,
distressed capitals, red disc), `pop` (colour blobs, glossy spheres, heavy rounded type). The type is the project's
own public-domain stroke font (engine/art/StrokeFont.cpp: A-Z, a-z, figures, punctuation, German umlauts, common
accents).

**Credits**: every sample pack (`samples/<id>/...` or an absolute path under `$AGENTSOUND_SAMPLES`), SoundFont (the
sf2 default GeneralUser GS included) and impulse response / other file param of the render JSON is listed with the
license and attribution of its `SOURCE.json`. The build summary warns about non-commercial, no-redistribution and
unclear licenses (fine for private listening; check before publishing) and prints the CC-BY attributions a
published song needs.

**Reference comparison**: `python -m agentsound compare songs/<slug> --ref <mp3|wav|flac|m4a> [--ref-start 1:02
--ref-end 1:32] [--section chorus]` compares the last full render (or one section of it) with a commercial
reference, loudness-matched: 1/3-octave spectrum and difference, stereo width and correlation per octave (low-end
mono), short-term loudness distribution, crest / PSR, punch (how far the kick / snare / hat hits stick out),
transient density, tails (only when robust). It writes `out/compare/<ref>/compare.json` (numbers + prioritised
suggestions with render-format fixes naming the tracks that carry the band) and `compare.png` (look at it). Compare
a section with an excerpt of similar character (chorus vs chorus) for dynamics. `agentsound analyze <wav> --out DIR`
gives the full report + images of any WAV.

## Mastering (`agentsound.mastering`)

The mastering engineer works on the finished mix (`out/mix.wav` of the last full build), after the mix itself is
right: it makes small, broad moves - never a fix for a mix problem - and every decision is logged with its reason.
Nothing in it is genre code: the genre comes in as data (the song's analysis profile: loudness window, LRA range,
PLR floor, width targets, band balance and its limits) and the platform preset; a reference track, when given,
becomes the tonal / width / loudness target.

```python
from agentsound import mastering
plan = mastering.match('songs/<slug>', ref='assets/refrences/x.opus', ref_start='1:02', ref_end='1:32',
                       section='chorus', platform='auto')      # -> out/master/master.json, plan.describe()
res = plan.render()            # post-pass: out/master/mastered.wav + .mp3, before/after numbers (master_result.json)
plan.apply(song)               # or the same settings into song.master (what plan.snippet() prints for song.py)
mastering.apply(s, eq={'high.freq': 6300, 'high.gain': 0.5}, width=1.1, monobass=120,
                limiter={'ceiling': -1.2, 'release': 120}, loudness_change=+2.0)
findings = mastering.check('songs/<slug>', platform='streaming')   # [{code, severity, message, fix?}, ...]
```

```
python -m agentsound master songs/<slug> [--ref X --ref-start 1:02 --ref-end 1:32] [--section chorus]
                                         [--platform auto|streaming|loud|dynamic] [--profile P]
                                         [--strength 0.75] [--max-db 3] [--render] [--no-mp3]
python -m agentsound master songs/<slug> --check [--platform streaming] [--compare out/compare/<ref>/compare.json]
python -m agentsound master path/to/any.wav --check --profile jazz
```

**`match(song_or_mix, ref=, ref_start=, ref_end=, section=, profile=, platform=, strength=0.75, max_db=3)`** analyses
the mix like `compare` does (the section, or the whole song) and decides:

- **Tone**: the loudness-matched 1/3-octave difference to the reference (the `compare` machinery), or without a
  reference the mix vs the profile's reference spectrum (`global.thirdOctave`). Smoothed over ~1 octave, re-centred
  on its median (the mids are the anchor; level is the limiter's job), a dead band (1 dB vs a reference, 1.5 dB vs a
  genre profile), `strength` of the rest, each band and the summed curve within +-`max_db`. Judged 31.5 Hz-12.5
  kHz only: YouTube / Opus references have nothing reliable at 16 kHz and above (and above the reference's own
  low-pass, `bandLimitedAboveHz`). **Profile guard**: the correction may not push any band past the profile's
  limits (`reference.bandLimitsDb`, 0.75 dB inside; brilliance / air not below `dullDb`); a band already outside is
  only allowed back - an old, dark or mono record (Baker Street 1978: -23 LUFS, mono, 20 dB less sub and air) must
  not make a modern mix thin or dull. Fitted with at most a low shelf, three broad bells (Q 0.5-1) and a high
  shelf (`fit_eq`, deterministic), plus a 20 Hz high-pass when the mix has DC or subsonic energy.
- **Loudness**: `platform` -
  | platform | target | limiting allowed | release |
  |---|---|---|---|
  | `auto` (default) | the reference's LUFS clamped into the profile's window (0.5 LU inside), else the nearest edge; a mix inside keeps its level | 3 dB | 120 ms |
  | `streaming` | -14 LUFS-I (Spotify / YouTube / Tidal / Amazon; Apple Music -16); the post-pass report judges -15..-13 | 4 dB | 150 ms |
  | `loud` (`club`) | the top of the profile's window - 0.5 (not louder than the reference) | 6 dB | 60 ms |
  | `dynamic` (`classical`, `jazz`) | the middle of the window (or the quieter reference): dynamics first | 1.5 dB | 250 ms |

  Never above the window's top (except streaming's fixed target) nor past the PLR floor (-1 dBTP - `plrMinDb`).
  "Limiting allowed" is the drive beyond the mix's headroom: the post-pass never drives the limiter harder and
  falls short of the target instead (`cappedByMaxDrive`) - an already limited mix loses ~0.8 LU of loudness range
  per dB of extra drive (children-of-neon: +3 dB took LRA 8.5 -> 6.1). **Density floor**: the master may be as loud
  as the reference, not denser - its crest factor stays >= the reference's - 1.5 dB (`loud`: - 3 dB; `dynamic`: the
  mix's own - 1 dB); the post-pass stops the drive there and says so (`cappedByDensity`): make the mix denser (bus
  glue) instead.
- **Width**: towards the reference's width above 150 Hz (or into the profile's range), x0.85-1.25, only when the
  difference is >= 1.5 dB, never widening a mix whose correlation is already < 0.3; `monobass` 120 Hz when the lows
  are not mono (correlation < 120 Hz under 0.9).
- **Limiter**: ceiling 0.2 dB under the true-peak target (-1 dBTP for every platform: lossy encoders add inter-sample
  overs), release by platform, the drive estimated from the loudness gap, the eq's and the width's loudness change.

`MasterPlan`: `.eq` / `.width` / `.limiter` (render-format params), `.targets`, `.measured`, `.estimate`,
`.curve` (diff, wanted and fitted eq per band), `.log`; `.chain()` (FX list: eq 'master_eq' > width > limiter),
`.patch()` (an fx-chain Patch for a song without a master chain), `.apply(song)`, `.snippet()`, `.render()`,
`.save()` / `MasterPlan.load(path)`.

**Into the song** (`mastering.apply(song, eq=, width=, monobass=, limiter=, loudness_change=)`, `plan.apply(song)`):
the eq goes FIRST in the master chain as `'master_eq'` (replaced, not stacked, when applied again: it was measured
on the finished mix, so it sits before the song's glue / tape / limiter), the song's width effect is multiplied (or
one is inserted before the limiter), the limiter's params are set and its gain moves by `loudness_change` (an
estimate: a limiter already working turns 1 dB of drive into less than 1 LU - re-build and check). Automation
targets by fx index follow the inserted effects. Paste `plan.snippet()` into song.py so the song stays
reproducible without out/.

**Post-pass** (`plan.render()` / `--render`): the engine renders mix.wav as one sampler note through the chain as
the master (`out/master/master.render.json`, 32-bit float `mastered.wav`), the limiter drive calibrated to the
target within 0.2 LU (secant steps, <= 4 renders), then `before/` and `after/` analyses (the song's tempo,
sections, profile; the platform's window) and their warnings. **Do no harm**: a warning the mix did not have
halves the eq / width moves, then drops them (`backoff`; loudness warnings are the limiter's and do not count), and
the plan is updated to what was applied (also `plan.snippet()`: the calibrated drive becomes `loudness_change`). With a
reference: `compare_before.json` / `compare_after.json` (+ png). `mastered.mp3` takes the tags and cover of
mix.mp3. Deterministic: the same plan renders bit-identical audio. The sampler's interpolation filter band-limits
the post-pass above ~19 kHz (transparent to -80 dB below 19 kHz at 48 kHz): inaudible, not bit-transparent.

**`check(report, platform=, compare=, render=)`** (a report dict / report.json / song folder): `true_peak` (over
the platform's -1 dBTP), `clipping`, `dc_offset`, `subsonic`, `loudness_window` (vs the profile's or platform's
window) / `loudness_platform` (vs -14), `normalisation` (what Spotify & co. at -14 and Apple Music at -16 do with
this level), `squashed` (PLR under the profile's floor), `lra_small` / `lra_large` (vs the profile's LRA range;
warn under `dynamic`), `tone_profile` (the broad master eq towards the genre average) / `tone_band` (a band past its
limit: fix it in the mix) / `tone_reference` (with a compare.json), `mono_low_end`, `mono_compat` (correlation,
mono-sum loss), `narrow` / `wide`, `no_limiter` (render JSON). Each with a render-format `fix` where one exists;
`warn` first, then `info`, then `ok`.

Validation (scratch copies, whole songs vs whole references, `platform='auto'` / `'streaming'`):
| | children-of-neon vs The Midnight "Sunset" (synthwave) | lamplight-avenue vs Baker Street 1978 (pop) |
|---|---|---|
| mix / reference | -11.7 / -9.7 LUFS, width >150 Hz 58 / 65 %, crest 14.4 / 14.8 dB | -10.6 / -23.0 LUFS, width 39 / 0.3 % (mono), sub +22, air +19 dB vs the record |
| tone | within the dead band after smoothing: +0.7 dB high shelf 8 kHz | the record asked for -3 dB lows / -2.2 dB top; the profile guard held sub >= -1.2, no low-mid boost, brilliance >= -2.0, air >= -1.1; the first pass raised `very_wide` (intro correlation) -> backed off x0.5: -1.4 dB bell 63 Hz, +0.6 dB 160 Hz, -1.1 dB shelf 4 kHz |
| `auto` | target -9.7 (the reference), density floor 12.4 dB stopped the drive at +1.9 dB: -10.7 LUFS, TP -1.19, LRA 8.5 -> 7.0, loudness gap -2.0 -> -1.0 LU, spectrum rms vs ref 1.99 -> 2.01 dB | -10.6 (target -10.5), spectrum rms vs ref 10.4 -> 10.0 dB (sub 22.3 -> 21.5, brilliance 9.4 -> 8.6, air 19.3 -> 18.5 dB) |
| `loud` / `dynamic` | -9.7 LUFS with +3.6 dB drive, LRA 5.8, crest 14.4 -> 12.3 | `dynamic`: -10.6, LRA 5.8 unchanged |
| `streaming` | -14.0 LUFS, TP -3.2, LRA 8.5 unchanged | -14.0 LUFS, TP -4.0, LRA 5.9 |
| warnings | no new ones in any run (streaming resolves `loudness_high` vs -15..-13) | no new ones after the back-off |

A master cannot move the tone much (by design): it matches loudness, peaks and width and nudges the balance; the
spectrum-vs-reference numbers barely move, and limiting itself shifts the loudness-matched spectrum a little (quiet
sections come up). Big tonal gaps are mix work - `compare` names the tracks.


## The making-of film (`film.py`, `agentsound.makingof`)

`python -m agentsound makingof songs/<slug>` renders `out/making-of.mp4` from `songs/<slug>/film.py` - the song's
making-of as code, like song.py (brief: `roles/film-director.md`). `--draft` writes a first film.py from the facts,
`--script` writes the narration to `making-of.md` (a review copy), `--stills T,T` PNG frames, `--preview` a quick
960x540 look, `--tts breeze|sapi|none`, `--song-length SECONDS`, `--chapters id,kind`.

```python
from agentsound.makingof.film import AR, Episode, Excerpt, Film, Item, N

def build(facts):                        # the song's facts: read-only, from its files and logs
    f = Film(facts)
    f.look(scenes={'intro': 'ink', 'finale': 'mandala', 'anthem': 'nebula+hw'})
    f.cold_open(N("It started with a wish in a chat.", 'Warm, intimate, unhurried.'))
    f.team(N("..."))
    f.blueprint(N("..."), show=('form', 'tempo', 'energy', 'hook'))
    f.act('I Candlelight', N("Act one ..."), scene='ink', at='theme', play=11)
    f.tracks(N("..."), items=[Item('Strings', ['violins1', 'cellos'], 295.93)])
    f.performance(excerpts=[Excerpt(229.35, 240.35, 'solo', [N("Into the solo ...")])])
    f.crisis(AR("Verdict: revise."))
    f.tried(N("..."), episodes=[Episode(1, before_lines=[AR("...")], after_lines=[N("...")])])
    f.song(N("And now, ..."))
    f.credits()
    return f
```

| call | shows | options |
|---|---|---|
| `N(text, direction='', pause=360)` / `AR(...)` | a narrated line (the narrator / the A&R's voice), always a caption | <= 260 characters; `direction`: 3-12 words of delivery |
| `look(scenes={section: scene}, highway=())` | the visual scene per section: `nebula` `ink` `ring` `grid` `mandala` `scope`, `+hw` the note highway | the rest follows the genre / energy plan |
| `cold_open(*lines)` | the wish typed as chat bubbles, the title card with the cover | `title=` |
| `team(*lines)` | a card per role and per player who played (log line / move counts) | |
| `blueprint(*lines, show=...)` | the form (parts, keys), tempo curve, energy per bar, the hook as notes + its returns | `show` any of form, tempo, energy, hook |
| `act(part, *lines, scene=, at=, play=)` | a part (a `parts` name or section names) under its own scene, its sections and words, `play` s of it | `at`: a section or seconds |
| `tracks(*lines, items=[Item(name, ids, at)])` | each item's stems solo from `at`, then the band back in, with its facts | default: `facts['items']` |
| `performance(*lines, excerpts=[Excerpt(start, end, label, lines)])` | track lanes; the players' moves pop on their frames | default: the densest moments |
| `crisis(*lines)` | the A&R stamp, the ranked issues, the revision's numbers | |
| `tried(*lines, episodes=[n or Episode(n, before_lines, after_lines)])` | before / after of AR.md revision item n: the judged build (git, re-rendered once) vs today, same bars, loudness-matched | positions from the issue's text (time, bar, section) |
| `song(*lines, start=0, length=None)` | the whole song with the audio-reactive scenes, section titles, the hook badge, moves | |
| `credits(*lines)` | Made with AgentSound, the roles, sample credits, the narration's licence | |

The `facts` dict (`agentsound.makingof.facts.collect`): `title`, `genre`, `duration`, `sections` (name, start, end,
bars, key, part, bpm, meter, lufs, level, what happens), `parts`, `energy` (LUFS per bar), `tempo`, `tracks` (notes
in seconds, family, colour, player), `moves` (the players' moves in seconds, `pop` = shown as a label), `hook`
(motif, names, `occurrences`, phrase), `items` (meet-the-tracks groups with their facts and moment), `wish`, `log`,
`soundRows`, `soundMeasured`, `verdict`, `issues`, `revision` (with before -> after `pairs`), `proposal`, `credits`.
