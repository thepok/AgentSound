# Render format v1 (`agentsound.render`)

The single contract between the Python compose layer (`agentsound/`) and the C++ engine (`agentsound.exe`).
It is flat and explicit: every note, parameter, route and automation point is spelled out; the engine
knows nothing about chords, scales or genres. The engine is **strict**: unknown keys, wrong types,
out-of-range values, dangling references and routing cycles are errors (exit code 2, message names the
JSON path). Nothing is silently defaulted except keys documented as optional below.

All times are in **beats** (quarter notes); the song tempo (`"tempo"`, or a `"tempoMap"` when it moves) turns
them into time.

```jsonc
{
  "format": "agentsound.render",
  "version": 1,
  "title": "Chrome Horizon II",                 // optional, metadata only
  "sampleRate": 48000,                          // optional, 44100 | 48000 | 96000, default 48000
  "tempo": 104.0,                               // BPM, 30..300; or "tempoMap" instead (see "Tempo map")
  "meter": [[0, 4, 4], [64, 3, 4]],             // optional, report bars only (see "Meter"); default 4/4
  "lengthBeats": 320.0,                         // end of the arrangement
  "tailSeconds": 4.0,                           // optional, default 4, max 30; render continues this long after lengthBeats (effect tails) and stops early once everything is silent
  "seed": 1,                                    // optional, default 1; every random process derives from it

  "sections": [                                 // optional; analysis/report markers only
    { "name": "intro", "startBeat": 0, "endBeat": 32 }
  ],

  "tracks": [
    {
      "id": "lead",                             // unique among tracks+buses, [a-z0-9_-]+
      "instrument": { "type": "va", "params": { "cutoff": 2400, "unison": 7 } },
      "fx": [                                   // optional insert chain, in order
        { "type": "chorus", "params": { "mix": 0.3 } },
        { "type": "compressor", "sidechain": "kick", "params": { "threshold": -24 } }
      ],
      "gainDb": -6.0,                           // optional, default 0, -120..+24
      "pan": 0.0,                               // optional, default 0, -1..1 (balance: unity at centre)
      "mute": false,                            // optional
      "output": "music",                        // optional, bus id or "master" (default)
      "sends": { "hall": -12.0, "echo": -18.0 },// optional, bus id -> send level dB (post-fader)
      "notes": [                                // [startBeat, durationBeats, pitch 0..127, velocity 1..127]
        [0.0, 1.5, 76, 110],
        [1.5, 0.5, 74, 96]
      ],
      "automation": [                           // optional
        {
          "target": "instrument.cutoff",       // see "Automation targets"
          "points": [[0, 400], [32, 6000, "exp"], [64, 800, "smooth"]]
        },
        { "target": "mod.0.depth", "points": [[64, 0], [96, 0.2]] }   // a modulator field (see "Modulators")
      ],
      "modulators": [                           // optional; see "Modulators"
        {
          "target": "fx.0.mix",
          "source": { "type": "lfo", "shape": "sine", "rateBeats": 2 },
          "mode": "offset", "depth": 0, "base": 0.3
        }
      ]
    }
  ],

  "buses": [                                    // optional; groups and effect returns
    { "id": "music", "fx": [], "gainDb": 0, "pan": 0, "output": "master", "sends": {}, "automation": [], "modulators": [] },
    { "id": "hall", "fx": [{ "type": "reverb", "params": { "mix": 1.0, "size": 0.8 } }] }
  ],

  "master": {                                   // optional
    "fx": [{ "type": "limiter", "params": { "ceiling": -1.0 } }],
    "gainDb": 0,
    "automation": [],
    "modulators": []
  },

  "export": {                                   // optional
    "stems": false,                             // also write one WAV per track and bus
    "bitDepth": 24                              // 16 | 24 | 32 (32 = float)
  },

  "analysis": {                                 // optional; report settings only, never changes the audio
    "profile": "synthwave",                     // optional, default "default"; see "Analysis profiles"
    "loudness": [-12, -9],                      // optional [minLufs, maxLufs] integrated target, overrides the profile's
    "silentNotes": [                            // optional, written by the compiler: notes it found no sound for
      {"track": "drums", "kind": "no_sound", "pitches": [49], "count": 17, "beats": [32, 96],
       "message": "'drums': 17 notes on crash (49) reach no sample in this kit ..."}
    ]
  }
}
```

## Semantics

- **Notes**: sample-accurate. A note starts at `startBeat` and is released at `startBeat + durationBeats`
  (release tail is the instrument's business). Overlapping notes of the same pitch are separate voices.
  Notes may start anywhere in `[0, lengthBeats)`; ending after `lengthBeats` is allowed (released in the tail).
- **Signal flow**: track instrument → track fx chain → gain → pan → (sends, post-fader) → output.
  Buses sum their inputs, then fx → gain → pan → sends → output. `master` sums everything routed to it,
  runs its fx chain and gain; output is the mix. Routing must be acyclic (a bus may not feed itself
  through any path). Buses are processed in dependency order.
- **Sidechain**: an fx entry may name `"sidechain": "<track or bus id>"`. The effect receives that
  node's **post-fader, pre-send** output of the *same block* as key signal. The key node must be computed
  before the effect's node (the engine orders processing accordingly; a cycle is an error).
  Only effects whose type supports a key accept `sidechain`: `compressor`, `ducker`, `delay` (ducking), `gatedreverb`
  (the gate) and `vocoder`, which **requires** one: its sidechain is the modulator (the voice whose spectrum it
  imposes on this node's signal, the carrier); a `vocoder` without `sidechain` is an error.
- **Mute**: a muted track/bus still runs (keeps state, feeds sidechains and followers) but contributes
  silence to its output and sends, and is not analysed (no node in the report; its stem is silent). This is how a
  vocoder's modulator is wired: a muted speech track, the carrier's `vocoder` keyed by it:
  `{"id": "voice", "mute": true, "instrument": {"type": "sampler", ...}}` +
  `{"id": "choir", "fx": [{"type": "vocoder", "sidechain": "voice", "params": {...}}], ...}` - only the robot is heard.
- **Latency**: only the master chain may contain latency (the limiter); the engine removes it from the
  output so the mix is time-aligned.

## Tempo map

`"tempoMap"` replaces `"tempo"` (exactly one of the two) when the tempo moves: ritardando, accelerando, fermata,
rubato, a new tempo for a section.

```jsonc
"tempoMap": [[0, 96], [60, 96], [63.9999, 70, "smooth"], [64, 35, "step"], [68, 96, "step"]]
//  rit. 96 -> 70 over beats 60..64, a fermata on beat 64 (its 4 beats at 35 BPM), a tempo from beat 68
//  (a jump right after a ramp: the ramp arrives a hair early, then "step" - how the compose layer writes it)
```

- **Points** `[beat, bpm]` or `[beat, bpm, curve]`: the first at beat 0, beats strictly increasing (0..100000),
  bpm 1..1000. `curve` shapes how the tempo moves from the previous point to this one, like automation:
  `"linear"` (default; bpm linear in beats), `"smooth"` (cosine ease in and out), `"step"` (the previous tempo
  holds up to the point, the new one starts there). After the last point its tempo holds (also in the tail);
  before beat 0 the first one does.
- **Exact**: times are the analytic integral of the map, not sampled - a linear segment lasts
  60·(b1−b0)/(bpm1−bpm0)·ln(bpm1/bpm0) s, a smooth one 60·(b1−b0)/√(bpm0·bpm1) s - so every note starts on its
  exact sample. A constant map (one point, or points that keep the tempo) renders **bit-identically** to `"tempo"`.
- **Everything that counts beats follows it**: notes; automation and modulators (evaluated on the song's beat
  grid: a `rateBeats` lfo cycles once per beat whatever the tempo, a `rateHz` one runs in seconds, envelopes in
  beats); tempo-synced effects - `delay` with `sync` (the delay is the duration of the last `time` beats, so the
  echo of a note - and every repeat - lands `time` beats later on the moving grid; while the tempo ramps the
  echoes are resampled like a tape echo, click-free; a tempo jump - a `"step"` point to another tempo - restarts
  the grid: the beats before the jump count at the new tempo, so the delay time changes at once there with a
  30 ms crossfade instead of replaying the window at the speed ratio - no pitch warp in a fermata), `reverb`
  `predelaybeats` (the same), `tremolo` / `phaser` `sync` (phase from the song beat), the `ducker` `tempo` mode (ducks on the song's
  beats), `va` `rateBeats` LFOs (voice and global); preview renders (`--from-beat`, `--section`) start at the
  map's song time and match the full render; `tailSeconds` stays seconds.
- **Report**: `render.tempoMap` (as given), `render.bpmRange`, `render.fromSec` (song time of the first sample),
  `global.bpmRange` (rendered span), `sections[].bpm` (average), with `bpmStart` / `bpmEnd` / `bpmRange` when it
  moves inside a section; section times, bar lines and bar/beat labels follow the map; the summary line says
  `tempo map A..B BPM`. `agentsound zoom <wav> --beat B --song song.render.json|report.json [--start-beat S]`
  converts through the map.
- **Modules** (engine/core/Module.h): `Instrument/Effect::setTempoMap(map)` is called once before `prepare()`,
  only when the tempo changes; `RenderContext::bpm` is then the tempo at beat 0 and `songStartSample()`
  (core/TempoMap.h) the song sample of `startBeat`. Modules that count beats or derive the song position from
  `startBeat` must use them; the others ignore the map.
- **Strict**: both or neither of `tempo` / `tempoMap`, a first point not at beat 0, beats not increasing, bpm
  outside 1..1000, a curve other than linear / smooth / step and malformed points are errors.

## Meter

```jsonc
"meter": [[0, 4, 4], [32, 3, 4], [44, 2, 4], [46, 6, 8]]   // [beat, numerator, denominator]; default 4/4
```

For the report only (the audio does not depend on it): bars start at every entry and follow its meter in
quarter-note beats (3/4 = 3, 6/8 = 3, 7/8 = 3.5, 12/8 = 6 beats per bar). Every change must fall on a bar line of
the meter before it (a pickup or leftover bar is an entry of its own, like `[44, 2, 4]`). Bar numbers everywhere -
`sections[].startBar/endBar`, `timeline.rows` (one row per song bar, `sec` = its start; `barSec` is the first
bar's length), `nodes[].barsRmsDb`, clicks and tails `bar`/`beat`, the image headers (bar numbers, beat ticks),
zoom titles - use it; `global.meter` lists `[first bar, "3/4"]`, `sections[].meter` the meter at the section
start, the summary line `meter 4/4 3/4`. Strict: the first entry at beat 0, beats strictly increasing, numerator
an integer 1..64, denominator 1, 2, 4, 8, 16 or 32, changes on bar lines.

## Assets (DX7 banks, SoundFonts, samples)

Instruments that load files resolve them against the engine's **assets folder**: `--assets DIR`, else
`$AGENTSOUND_ASSETS`, else the first `assets/` (containing `dx7/`) found walking up from the executable (the
repo's `assets/`), else `./assets`. Missing or malformed files are config errors (exit 2) naming the JSON path and
the resolved file. Files are loaded once per process and shared by every track that uses them.

| instrument | param | resolved as |
|---|---|---|
| `sf2` | `"file"` (string, default `"GeneralUser-GS.sf2"`) | `<assets>/soundfonts/<file>`; an absolute path is used as is |
| `sf2` | `"preset"` (string) | a preset name (case-insensitive, whitespace-trimmed) or `"bank:program"`; alternatively the numeric params `bank` + `program` |
| `sampler` | `"samples"` (object or array, see below) | every `file` / `dir` relative to `<assets>/` (e.g. `"samples/909"`, `"soundfonts/GeneralUser-GS.sf2"`), or absolute |

`samples` is the only structured (non-scalar) instrument param. Forms (strict: unknown keys are errors):

```jsonc
"samples": { "dir": "samples/909", "loop": "none", "gain": 0 }        // every *.wav in the folder, mapped by file name
"samples": { "file": "samples/pad.wav", "root": 57, "loop": "forward" } // one zone
"samples": [                                                             // zones (overlapping zones layer)
  { "file": "samples/p/C3.wav", "root": 48, "lo": 0, "hi": 54, "vello": 0, "velhi": 127,
    "loop": "pingpong", "loopStart": 1200, "loopEnd": 48000, "gain": -2.0, "tune": 0, "pan": 0.0, "choke": 0 },
  { "file": "soundfonts/GeneralUser-GS.sf2", "sample": "Orchestra Hit-2" }   // a raw SoundFont sample
]
```

Zone fields (every one optional except `file`; the SFZ importer `agentsound/sfz.py` writes them, see
docs/COMPOSE_API.md "SFZ instruments"):

| field | range | meaning |
|---|---|---|
| `file` | path | a WAV, an `.sf2` (needs `sample`), or a generator `"*silence"` (plays nothing: only turns voices off), `"*sine"`, `"*noise"` |
| `sample` | string | the SoundFont sample by name (`agentsound sf2 --samples [search]`) |
| `root` | 0..127 or `"sample"` | the key the file sounds at unshifted (default 60; SoundFont samples: their own + pitch correction); `"sample"` = the WAV's `smpl` chunk (unity note + fraction), else 60 |
| `lo` `hi` `vello` `velhi` | 0..127 | key and velocity range (overlapping zones layer) |
| `loop` | `none` `oneshot` `forward` `pingpong` `sustain` `auto` | `oneshot`: plays to the end, note-off ignored (drums). `forward` / `pingpong`: loops while the note sounds (release too). `sustain`: loops while the key is held, then plays on past the loop end. `auto`: the WAV's own `smpl` loop if it has one (forward or ping-pong), else no loop. `forward` / `pingpong` / `sustain` without `loopStart`/`loopEnd` use the file's `smpl` loop when it has one, else the whole file |
| `loopStart` `loopEnd` | frames | loop `[start, end)` inside the played part (a loop mode is required; `loopEnd` <= `end`) |
| `offset` `end` | frames | play from `offset` to `end` (exclusive; default whole file) |
| `gain` | -144..48 dB | zone level |
| `tune` | -9600..9600 ct | fine / coarse tuning |
| `pitchKeytrack` | -1200..1200 ct per key | 100 = normal, 0 = every key at the root pitch (drums, noises) |
| `pan` `width` | -1..1, 0..2 | zone position; stereo width of a stereo file (mid/side) |
| `choke` | 0..127 | a new note of the zone fades every other voice of the same choke number in 50 ms |
| `group` `offBy` | int32 | a new voice of group G turns off sounding voices whose zone has `offBy` = G (SFZ `group` / `off_by`: hi-hat families, mono instruments) |
| `offMode` `offTime` | `fast` (~5 ms) `normal` (the zone's release) `time`; 0..60 s | how an `offBy` voice stops |
| `notePolyphony` | 1..128 | at most n sounding voices of the same key in the zone's group (the oldest is turned off) |
| `groupPolyphony` | 1..256 | at most n voices of the zone's group (group 0: of this zone) at once; starting one more fades the oldest voice of another note out in ~5 ms (SFZ `polyphony`: hi-hat and cymbal groups) |
| `seqLength` `seqPosition` | 1..128 | round robin: the zone keeps a counter that advances on every note that matches its key / velocity / random range, and plays when `counter % seqLength == seqPosition - 1` |
| `lorand` `hirand` | 0..1 | random layers: one value per note-on (seeded by the note's absolute sample time and key: renders and previews agree), the zone plays when `lorand <= r < hirand` |
| `trigger` | `attack` `release` `release_key` `first` `legato` | `release`: plays at note-off, or at pedal-up while the sustain pedal holds the note (piano dampers: once per key, not while the key is struck again and still held); `release_key`: at note-off regardless of the pedal; `first`: only when no other key is down; `legato`: only when another key is down |
| `rtDecay` | 0..200 dB/s | release zones get quieter by this much per second the key was held |
| `ampVeltrack` | -1..1 | velocity to level for this zone (1 = the default curve at full depth, 0 = flat, negative = inverted), scaled by the instrument's `velsens` |
| `velcurve` | `[[vel, gain 0..4], ...]` | piecewise-linear velocity to gain (replaces the default curve; scaled by `ampVeltrack`/`velsens`) |
| `xfinLo` `xfinHi` `xfoutLo` `xfoutHi` | 0..127 | velocity crossfade in / out (SFZ `xfin_lovel` ...) |
| `xfinLoKey` `xfinHiKey` `xfoutLoKey` `xfoutHiKey` | 0..127 | key crossfade in / out |
| `xfVelCurve` `xfKeyCurve` | `power` (default) `gain` | equal-power or linear crossfades |
| `envDelay` `attack` `hold` `decay` `sustain` `release` | s (0..100), sustain 0..1 | the zone's amplitude envelope (DAHDSR); a zone without its own time uses the instrument's param |
| `velAttack` `velHold` `velDecay` `velRelease` / `velSustain` | ±100 s / ±1 | added x velocity/127 (SFZ `ampeg_vel2*`) |
| `filter` `cutoff` `resonance` | `lpf_1p` `lpf_2p` (default) `hpf_1p` `hpf_2p` `bpf_2p`; 1..40000 Hz; 0..40 dB | a per-voice filter (on top of the instrument's `cutoff`) |
| `filKeytrack` `filKeycenter` `filVeltrack` | ct per key, key, ct at velocity 127 | cutoff tracking |
| `filterEnv` | `[depth ct, delay, attack, hold, decay, sustain 0..1, release]` | an envelope moving the zone cutoff (SFZ `fileg_*`) |
| `eq` | 1..3 x `[freq Hz, bandwidth oct, gain dB]` | peaking EQ bands (SFZ `eqN_*`) |
| `vibrato` `tremolo` | `[depth ct / dB, rate Hz, delay s, fade s]` | per-voice sine LFOs to pitch / level |
| `ampRandom` `pitchRandom` `offsetRandom` | dB (0..+x), ct (±x), frames (0..x) | per-note randomness (seeded like `lorand`) |
| `delay` `delayRandom` | s | the voice starts later |
| `pedal` | bool (default true) | false: the sustain pedal does not hold this zone |
| `channels` | 1..64 x `[channel 0..63, gain L, gain R]` (linear gains -16..16) | mixes the listed channels of a multichannel WAV into the zone's stereo pair at load time: left = sum gainL x channel, right = sum gainR x channel (a microphone mix of a DrumGizmo multichannel hit, a polarity flip `[[0, 1, 0], [1, 0, -1]]`). A channel the file does not have is an error. Each (file, mix) is decoded and cached once; a mix that only picks / swaps / inverts channels of 16-bit data stays 16-bit. WAV zones only |
| `xfinLoDyn` `xfinHiDyn` `xfoutLoDyn` `xfoutHiDyn` | 0..127 | **live** crossfade in / out on the instrument's `dynamics` param x 127 (SFZ `xfin_loccN` ... of the dynamics controller): recomputed every 16 samples while the note sounds, so layers of one note crossfade during a crescendo |
| `xfDynCurve` | `power` (default) `gain` | equal-power or linear dynamics crossfade |
| `dynGain` | `[[dyn 0..127, gain 0..16], ...]` | **live** piecewise-linear gain over `dynamics` x 127 (SFZ `volume_onccN` / `amplitude_onccN` of the dynamics controller); end points extended flat |
| `dynCutoff` | -12000..12000 ct | **live** zone filter move: cutoff + dynCutoff x `dynamics` (needs a zone filter) |
| `dynLo` `dynHi` | 0..127 | the zone plays only when `dynamics` x 127 at the note-on lies in the range (SFZ `lo/hiccN` of the dynamics controller) |
| `legatoOffset` | 0..10000 ms | `mono` `legato`, scripted transitions: where this zone's sample starts when it enters legato (else the `legatooffset` param, else auto: the sample's settled level) |
| `swLast` | 0..127 or `[lo, hi]` | keyswitch articulation: the zone plays only while the last keyswitch pressed is this key (range: SFZ `sw_lolast`..`sw_hilast`) |
| `swDown` | 0..127 | the zone plays only while this keyswitch key is held |
| `swLo` `swHi` | 0..127 (both) | the keyswitch range: keys that select articulations (with every `swLast` / `swDown` key) and never sound |
| `swDefault` | 0..127 | the articulation selected before any keyswitch (one value per instrument: zones that disagree are an error) |

**Played, not triggered** (`sampler` params; docs/COMPOSE_API.md "Realistic performance"):
- `dynamics` (0..1, default 1, automatable, ~5 ms smoothing): drives the live zone fields above; `layers`
  `"dynamics"` turns velocity layers into a dynamics stack (a note starts the layers around `dynamics` x 127 at its
  note-on plus `xfspread` on each side, together and sample-aligned; neighbouring layer centres - the middle of each
  zone's `vello`..`velhi` - crossfade equal-power; velocity then only sets the level, and the zones' velocity
  crossfades `xfinLo`..`xfoutHi` do not apply); `dyntone` (a tilt EQ, darker
  below dynamics 1; exactly transparent at 1) and `dynrange` (dB quieter at dynamics 0) are static. Silent layers are
  not interpolated (they only keep their place in the sample).
- `mono` `"legato"`: a note that starts while another key is held (keyswitch notes do not count; touching notes -
  note-on and note-off on the same sample - count) and has a sustaining zone to go to is a **legato transition**:
  zones with `trigger` `legato` play when the library has them (the old voices fade out over max(`legatotime`, their
  attack)); otherwise the new zones enter past their attack (`legatoOffset` / `legatooffset` / auto) with no attack
  envelope, crossfading equal-power with the old voices over `legatotime`, level-matched to the old voices (the
  match relaxes to the note's own level over >= 0.5 s; `legatomatch` 0 turns it off). A transition that starts
  before the previous one ended fades every outgoing voice from its current gain together (the line keeps its power
  in fast runs). `glide` > 0 bends the old
  voices to the new pitch and the new ones in from the old pitch (`glideshape`), crossfading over max(`legatotime`,
  `glide`). The held notes behind a transition fire no release zones. Releasing the sounding note while an earlier
  key is still held goes back to that key with a legato transition (last-note priority; the released note fires no
  release zones). A note after a rest attacks (the tail of the
  previous one fades in 30 ms). `legatotime`, `legatooffset` and `glide` are latched at each transition.
- `vibrato` (cents) / `vibratorate` (Hz): an instrument vibrato on every voice; its phase restarts with a note after
  a rest and runs on through legato transitions (preview-stable from the next such note).
- Keyswitch notes (keys in the keyswitch set, raw pitch before `transpose`) only select the articulation and never
  sound; the Python compiler inserts them at the start of notes marked with an articulation, held until the next
  switch (so a `--section` preview starting inside it selects it too).

**Sustain pedal** (`pedal` param, a step 0..1, >= 0.5 = down; `sampler` and `sf2`): while down, note-offs are held
(the voices ring until pedal-up, a re-struck key starts a new voice); release-triggered zones of held notes fire at
pedal-up. **Expression** (`expression`, 0..1): output gain x expression^2. Both are ordinary automatable params.
**Round robin in previews**: counters start at the render's start, so a `--section` preview may pick a different
round-robin sample than the full render at the same spot (random layers are preview-stable).

Folder names: GM drum names (`kick`, `snare`, `clap`, `hat`, `ohh`, ... on their key; hats choke each other) or note
names (`C4`, `F#3`, `Bb2`, `60`; spread to the nearest keys); anything else is an error (for arbitrary names the
Python kit builder `inst.kit` writes zones). The Python layer passes song-relative paths (`./samples/...` in
`inst.sampler`) as absolute paths. WAV files are read once per process (in parallel, 16-bit and 8-bit material kept
as 16-bit in memory) and shared by every zone and track; with `AGENTSOUND_VERBOSE=1` the engine prints a load summary
per sampler to stderr (zones, files, MB, seconds). **WavPack**: a zone file that is a lossless WavPack stream (whatever
its extension: GrandOrgue organs store their pipes as WavPack `.wav` files) is decoded like a WAV - 8..32-bit integer
PCM, mono / stereo / multichannel, every block checked against its CRC (a corrupt file is an error, never wrong
audio); the `smpl` loop comes from the RIFF header the encoder kept. Hybrid (lossy), float and DSD WavPack are errors.

**`convolver` (effect) `"ir"`** - the impulse response, required: one WAV path (relative to `<assets>/` or
absolute), or a list of 2 or 4 WAVs that together form one IR, their channels taken in order:

```jsonc
"ir": "samples/<pack>/Hall.wav"                                  // 1 ch: same IR on L and R; 2 ch: L->L, R->R; 4 ch: LL, LR, RL, RR
"ir": ["samples/<pack>/Hall L.wav", "samples/<pack>/Hall R.wav"]   // 2 mono files: left, right
"ir": ["samples/<pack>/Plate.L.wav", "samples/<pack>/Plate.R.wav"] // 2 stereo files: left input's L/R, right input's L/R (true stereo)
"ir": ["...V1.1.L.wav", "...V1.1.R.wav", "...V1.2.L.wav", "...V1.2.R.wav"]  // 4 mono files: LL, LR, RL, RR (Lexicon 224XL sets)
```

The files of one IR need the same sample rate and channel count; any rate is resampled to the render rate
(linear-phase windowed sinc; the resampler's pre-ringing is trimmed where it is under -70 dB, so a resampled IR
keeps the file's timing: exactly when the file has any silence before the direct sound, within ~0.5 ms for a hard
onset at its first sample). PCM
8/16/24/32-bit or float WAV only (the sample library converts FLAC / AIFF / OGG packs to WAV). The file is read
at prepare: a missing, unreadable or unsupported file is a config error naming the JSON path and the file; a
path inside `samples/<pack>/` of a pack that is not installed says so and names the fetch command. The Python
layer (`fx.convolver(ir=...)`, patches) passes `samples/...` paths as absolute paths inside the sample library
(`$AGENTSOUND_SAMPLES`, else `assets/samples`) and `./`, `../` paths relative to the song file. Zero latency;
the effect's `tailSeconds` = IR length + predelay, but the render does not lengthen the song's `tailSeconds` for
it: a long IR (a church, a 5 s hall) needs a song tail that long. The prepared IR ends where it has fallen 80 dB
under its peak; samples more than 200 dB under the peak become exact zeros; NaN / infinite samples are a config
error. The other params (mix, gain, predelay, lowcut, highcut, width, start,
length, stretch, normalize, reverse) are in `docs/PARAMS.md`.

## Stack (layered instruments)

The `stack` instrument plays 1-8 child instruments of any other type on one track: every note goes to each layer whose
key and velocity range it falls in, and the layers are summed (a stack of A and B renders exactly like a track of A
plus a track of B, up to float rounding; a one-layer stack is bit-identical to its child).

```jsonc
"instrument": { "type": "stack", "params": {
  "layers": [                                        // 1..8, in order
    { "id": "piano",                                 // optional [a-z0-9_]+, unique; default: the layer index ("0", "1", ...)
      "instrument": { "type": "sampler", "params": { "samples": [...], "level": 8.2 } },   // any type but "stack"
      "fx": [{ "type": "eq", "params": { "hp.freq": 210 } }] },                          // optional insert chain
    { "id": "glass", "instrument": { "type": "dx7", "params": { "voice": "CELESTE" } },
      "transpose": 12, "level": -10, "follow.bend": false },
    { "id": "pad", "instrument": { "type": "va", "params": { "cutoff": 1500 } },
      "level": -14, "delay": 40, "follow.pedal": false, "fx": [{ "type": "chorus", "params": { "mix": 0.4 } }] }
  ],
  "level": 0, "pedal": 0,                            // the stack's own params (below)
  "layers.pad.cutoff": 1200                          // optional flat overrides: layers.<id>.<param> (as automation)
} }
```

Layer keys (all optional except `instrument`; `agentsound params stack` lists them with ranges):

| key | range | meaning |
|---|---|---|
| `level` `pan` `mute` | -60..24 dB, -1..1, bool | the layer's gain (balance pan, unity at centre), automatable, smoothed (two-pole, ~5 ms 10-90 %) |
| `transpose` | -48..48 st | added to every note of the layer; notes moved outside 0..127 do not play on it |
| `fine` | -100..100 ct | detune through the child's `pitchbend` (va, dx7, sf2, sampler; an error on drums), automatable |
| `keylo` `keyhi` `keyfade` | 0..127 | key range (the played note, before `transpose`); `keyfade` semitones of equal-power fade inside the range: in over keylo..keylo+keyfade when keylo > 0, out over keyhi-keyfade..keyhi when keyhi < 127 |
| `vello` `velhi` `velfade` | 0..127 | velocity range and its equal-power fade, the same way (soft layer velhi 95 + hard layer vello 60, both velfade 35: an equal-power crossfade 60..95) |
| `velcurve` `velscale` | 0.2..5, 0..4 | the velocity the child receives: `v^velcurve * velscale`, clamped to 1/127..1 (the fades use the played velocity) |
| `delay` | 0..2000 ms | the layer's note-ons, note-offs and sustain-pedal moves arrive this much later (flams, soft doubles, pads swelling in behind an attack; the other performance params are not delayed) |
| `xfvoices` | 1..16 (4) | crossfade voices, see below |
| `follow.bend` `follow.pedal` `follow.expression` `follow.dynamics` `follow.modwheel` | bool (on) | whether the layer takes the stack's param of that name |

Stack params: `level` (dB, the summed output), and the performance params forwarded to the layers that follow them:
`pitchbend` (st; the child's bend = its own configured bend + the stack's + `fine`/100), `pedal` (sampler / sf2
children get their own `pedal` - release samples at pedal-up; for va / dx7 / drums children the stack holds their
note-offs while the pedal is down and releases them at pedal-up), `expression` (children with their own get it; for the
others the stack applies gain x expression^2), `dynamics` (sampler children), `modwheel` (dx7 children). A stack param
given in the JSON starts the following children there. `pitchbend`, `dynamics` or `modwheel` set while no layer
follows it (or has it) is an error.

**Addressing** (automation, modulators, flat overrides): `instrument.layers.<id>.<param>` - a layer key (automatable:
`level`, `pan`, `mute`, `fine`), `layers.<id>.fx.<index>.<param>` (the layer's insert chain) or any automatable param of
the child (`layers.pad.cutoff`, `layers.glass.mod.vib.amount`). Layer keys shadow child params of the same name
(`level`, `pan`, `transpose`: the child keeps its configured value); a child's `pitchbend` / `pedal` / `expression` /
`dynamics` / `modwheel` is the stack's while the layer follows it (then only `layers.<id>.<param>` when it does not).

**Crossfade voices**: a velocity / key fade needs a per-note gain, which a child instrument cannot apply to one of its
voices. A layer whose fades give some note a gain strictly between 0 and 1 runs `xfvoices` extra instances of its
child (configured identically, same seed). Fade gains are rounded to 1 dB steps (at most 0.5 dB off the exact
equal-power curve; within 0.5 dB of unity = unity), so notes of nearby velocities / keys share an instance: a note at
gain 1 plays on the main instance, a note in a fade on the extra instance already at its gain, else on a free one (it
takes the gain), else on the instance (the main one included) with the nearest gain in dB. Layers
without fades cost exactly their child. Mono / legato children only glide between notes on the same instance, so keep
legato lines out of a fade zone.

**Layer fx**: effects that need a sidechain (`vocoder`) or add latency (`limiter`) and a `"sidechain"` key are
errors; the layer's fx tail keeps the stack from reporting idle. Tempo map, `startBeat` and preview renders reach the
children and layer effects as on a track (synced LFOs and effects are phase-identical in previews).

**Determinism**: child `i` (and its crossfade voices) is seeded from the track seed and `i`; its effect `j` from that
and `j`. `delay` in a preview render: a note that began before the preview start restarts at the start and its delay
counts from there. Strict: unknown layer keys, a missing `instrument`, duplicate or malformed ids, a numeric id other
than the layer's index, keylo > keyhi, vello > velhi, fractional `transpose` / key / velocity / `xfvoices`, a nested
stack, an unknown flat override target, and the child's own errors (named `layers[i].instrument`).

## Automation targets

| target | meaning |
|---|---|
| `instrument.<param>` | any automatable instrument param (a stack's layers: `instrument.layers.<id>.<param>`, see "Stack") |
| `fx.<index>.<param>` | param of the node's fx chain entry `<index>` (0-based) |
| `gainDb`, `pan` | node fader and pan |
| `send.<busId>` | send level in dB |
| `mod.<index>.<field>` | a field of the node's modulator `<index>` (0-based), see "Modulators" |

`points` are `[beat, value]` or `[beat, value, curve]`, strictly increasing in beat. `curve` describes
the shape of the segment **arriving** at that point: `"linear"` (default), `"exp"` (exponential,
only for strictly positive values — use for frequencies), `"smooth"` (cosine ease), `"step"` (jump at
the point). Before the first point the first value holds; after the last point the last value holds.
The engine evaluates automation every 32 samples; modules smooth internally. A target may have at most
one automation lane (merge the points; a second lane for the same target is an error).

## Modulators

"Parameters are instruments too": every track, bus and the master may carry `"modulators"` (at most 64),
continuous control sources evaluated every 32 samples like automation, on the song's beat grid. Modules
smooth their parameters internally (~ms) and the renderer smooths gain / pan / sends (10 ms; 2 ms when a
modulator drives them, so trance gates keep crisp, click-free edges), so 32-sample updates are effectively
continuous. Audio-rate modulation is not a goal (lfo rates stop at 50 Hz).

```jsonc
"modulators": [
  { "target": "instrument.cutoff",
    "source": { "type": "lfo", "shape": "sine", "rateBeats": 1 },
    "mode": "absolute", "min": 600, "max": 4000, "curve": "exp" },              // quarter-note filter wobble
  { "target": "gainDb",
    "source": { "type": "steps", "values": [0, -1, 0, -1, 0, 0, -1, 0], "stepBeats": 0.25 },
    "mode": "offset", "depth": 18, "base": -6, "startBeat": 64, "endBeat": 128 }  // trance gate, chorus only
]
```

| key | meaning |
|---|---|
| `target` | required; automation grammar: `instrument.<p>`, `fx.<i>.<p>`, `gainDb`, `pan`, `send.<bus>` (automatable params only; `mod.*` is not a modulator target) |
| `source` | required; one of the sources below |
| `mode` | required: `"absolute"` or `"offset"` |
| `min`, `max` | absolute mode, required (not for `steps`): the source's 0..1 is mapped onto min..max (min > max inverts); must lie inside the target's range |
| `depth` | offset mode, required: `source × depth` is added to the value below (see evaluation order) |
| `curve` | optional `"linear"` (default) or `"exp"`. Absolute: geometric min..max (both > 0; use for Hz). Offset: `depth` is in octaves (−10..10), the value below is multiplied by 2^(source × depth). Absolute steps: glides are geometric |
| `base` | optional: the target's value under the modulator when the target has **no** automation lane (an error if it has one; the lane is the base). Required in offset mode without a lane, and on an instrument/fx param without a lane whose modulators are all windowed (the value outside the windows; modules do not report their configured values). Must lie inside the target's range |
| `startBeat`, `endBeat` | optional active window `[startBeat, endBeat)` in song beats; outside it the modulator contributes nothing |

Sources (bipolar sources output −1..1, unipolar ones 0..1; absolute mode maps bipolar −1..1 onto min..max,
offset mode multiplies the raw output by `depth`):

| `type` | keys | output |
|---|---|---|
| `lfo` | `shape` (required): `sine` `triangle` `saw` `ramp` `square` `random` `smoothrandom`; exactly one of `rateBeats` (cycle length in beats, 1/1024..1024, on the song grid) or `rateHz` (0.001..50, free-running); `phase` 0..1 (default 0); `retrigger` `"none"` (default) or `"note"` (restart on every note-on of this track; tracks only) | bipolar |
| `steps` | `values` (1..1024 numbers, required), `stepBeats` (required), `glide` 0..1 (default 0), `loop` (default true) | absolute: the values are target values; offset: values in −1..1 |
| `follow` | `node` (track or bus id, required), `attackMs` (0..10000, default 5), `releaseMs` (default 120), `gainDb` (−48..48, default 0) | unipolar |
| `envelope` | `attackBeats` (default 0), `decayBeats` (0.5), `sustain` 0..1 (0), `releaseBeats` (0.25), `trigger`: `"note"` (default; this track's notes) or a track id | unipolar |
| `random` | `rateBeats` (required), `smooth` 0..1 (default 0) | bipolar |

- **Shapes** (phase 0 = start of a cycle): `sine` = −cos (minimum at 0, maximum at ½ — a quarter-note wobble
  opens between the beats), `triangle` (minimum at 0, maximum at ½), `saw` falls +1 → −1, `ramp` rises
  −1 → +1, `square` is +1 for the first half, `random` holds a new value per cycle (sample & hold),
  `smoothrandom` glides (cosine) between the per-cycle random values.
- **Tempo grid**: `lfo` with `rateBeats`, `steps` and `random` count from the modulator's `startBeat` (or beat
  0) in song beats: cycle / step k starts at `startBeat + k × rate`, exactly, also in preview renders
  (`--from-beat`, whose first sample is at a song beat that need not be on the block grid). With `rateHz` the
  phase is song time × rate. An automated `rateBeats` / `rateHz` integrates the phase block by block (no
  jumps); previews integrate it from beat 0 to their start, so they match the full render.
- **Note triggers** (`retrigger: "note"`, `envelope`): the retriggered phase / envelope level runs from the
  note-on's exact sample, whatever the block grid. A preview render replays the trigger track's notes before
  its start, so lfo phases and envelope stages continue where the full render is (a note held across the
  preview start is not a new trigger). Followers start at rest in previews (they need the audio before).
- **steps**: step k holds `values[k mod n]` (or, with `loop: false`, the last value once the list is
  exhausted). With `glide` g the first g of every step moves linearly from the previous step's value
  (the first step of the sequence does not glide).
- **follow**: peak envelope (one-pole attack / release) of `max(|L|, |R|) × gainDb` of the node's post-fader,
  pre-mute output — the signal a sidechain key gets — of the **current block**, clamped to 0..1 (linear
  amplitude: a node peaking at −6 dBFS gives 0.5). The followed node is processed first: it is a dependency
  edge like a sidechain, so cycles are errors; `master` and the node itself cannot be followed. A muted
  node can be followed (e.g. a sidechain "ghost" key track).
- **envelope**: linear ADSR with times in beats. Every note-on of the trigger track restarts the attack from
  the current level (attack 0 jumps to 1); decay runs to `sustain` in `decayBeats`; the gate is open while at
  least one trigger note is held, and when the last one ends the level falls to 0 in `releaseBeats`. Note-ons
  are seen in the 32-sample block they fall in (≤ 0.7 ms early), so a pluck's filter is open on its attack.
- **random**: step k's value is a hash of (song seed, node id, modulator index, k): deterministic and identical
  in preview renders. `smooth` s: the first s of each step glides (cosine) from the previous value.
- **Evaluation**, per block and target: start from the target's automation lane value (if any); then apply the
  target's modulators in array order where active — absolute ones replace the value, offset ones add
  `source × depth` (multiply by 2^(source × depth) with `exp`) to it, or to `base` when there is nothing below.
  When nothing is active the lane, else `base` (the first modulator's with one; a `mod.<i>.base` lane moves it
  there too), else the node's static `gainDb` / `pan` / send level applies
  (instrument / fx params keep their configured value). The result is clamped to the target's range (the
  param range from `agentsound params`; `gainDb` −120..24, `pan` −1..1, sends −120..24 dB).
- **Modulator fields as automation** (`mod.<index>.<field>`, index into this node's `modulators`): `depth`
  (offset mode), `min` `max` (absolute, not steps), `base` (only if given), `rateBeats` / `rateHz` (lfo — the
  one it uses; random: `rateBeats`), `phase` (lfo), `glide` (steps), `smooth` (random), `attackMs` `releaseMs`
  `gainDb` (follow), `attackBeats` `decayBeats` `sustain` `releaseBeats` (envelope). The lane replaces the
  field's JSON value (which must still be given); its points must lie in the field's range (`min` / `max` /
  `base` also in the target's range). `steps` step length cannot be automated.
- **Strict**: unknown keys, a missing or doubled rate, values out of range, bad targets, dangling `node` /
  `trigger` ids, a `trigger` that is not a track, `note` triggers / retrigger on buses or the master, and
  follower cycles are errors naming the JSON path.

## Analysis profiles

`"analysis"` chooses what the report (`report.json`, images) judges the mix against. It never changes the
audio. `profile` sets the reference long-term spectrum (band balance `bandsVsRefDb`, `thirdOctave`, tilt),
the integrated loudness target and every style-dependent warning threshold: the band balance limits
(`balance_<band>_high/_low`), `dull`, `tilt`, `loudness_low/_high`, `squashed` (peak-to-loudness ratio),
`lra_low/_high` and which bands count for `masking`. The report states the profile in `summary`,
`reference.profile` (with every threshold it used: `bandLimitsDb`, `dullDb`, `tiltToleranceDbPerOct`,
`plrMinDb`, `lraRangeLu`, `noteSpreadMinDb`, `lufsTarget` + `lufsTargetFrom`; `reference.profiles` lists every profile name), the
warning messages and the image titles.

| profile | for | reference balance (vs default) | loudness | other thresholds |
|---|---|---|---|---|
| `default` | anything; generic modern pop / synthwave master | flat 40–100 Hz, −4.5 dB/oct above, steeper above 8 kHz (sub 11 %, bass 45 % of the energy) | −12…−9 | sub +5/−9, bass +4/−6, lowmid/mid/presence +4, presence −7, brilliance +5, air +7 dB; dull −6; PLR ≥ 6; LRA 3–15 |
| `synthwave` | outrun / nightdrive / retrowave pop: four-on-the-floor kick at 41–55 Hz | +4…+7 dB at 31–63 Hz (kick + bass: equal energy per octave 35–150 Hz; sub 31 %, bass 37 %), −1 dB 125–250 Hz, −2 dB 2.5–5 kHz (controlled presence), +1…+1.5 dB 8–10 kHz (bright top) | −12…−9 | as default, sub low −6 |
| `dreamwave` | dreamwave / chillsynth: 808 half-time, lush pads, soft leads | +3…+6 dB 31–63 Hz, +1…+1.5 dB 250–630 Hz (warm), −3…−3.5 dB 2.5–6 kHz (less presence), −2.5…−6 dB above 8 kHz | −14…−10 | presence +3/−9, brilliance +4, air +6, sub low −8; dull −7; PLR ≥ 7; LRA 3–16 |
| `darksynth` | darksynth: low-tuned distorted kick, driven bass and pads | +5…+7.5 dB 31–63 Hz, +1.5…+2.5 dB 100–630 Hz (dense low mids), −2.5 dB 2.5–5 kHz, darker air | −10…−7 | lowmid +5, sub low −6; PLR ≥ 5; LRA 2.5–14 |
| `jazz` | small-group acoustic jazz (piano trio / quartet, club room): upright bass, feathered kick, brushes / ride | −6…−12 dB below 40 Hz, −3 dB at 50 Hz (no sub kick), +1…+1.5 dB 250–1000 Hz (warm mids), −1…−3 dB 3–10 kHz, −4…−5.5 dB 12–16 kHz (sub share 4 %) | −16…−13 | sub not checked low, bass low −7, mid low −6, presence −8, brilliance +4, air +6; dull −7; PLR ≥ 9; LRA 5–14 |
| `classical` | orchestral / chamber music in a concert hall | −6.5…−12 dB below 40 Hz, −3…−4.5 dB 50–63 Hz, +1…+1.5 dB 315–1250 Hz, −2…−3 dB 4–5 kHz, −4.5…−11 dB 6–16 kHz (no hats, distance, hall) | −23…−16 | sub +7 (organ pedals, bass drum) and not checked low, bass low −8, lowmid / mid +5, mid low −6, presence +3 (steely strings) / −9, brilliance +4, air +5; dull −8; tilt ±2; PLR ≥ 12 (no limiting); LRA 4–22 |
| `piano` | solo piano (recital, nocturne, ballad or film piano alone) in a hall | the middle register's hump: +4…+9.5 dB 160–250 Hz, +13…+17.5 dB 315–800 Hz, +6…+12.5 dB 1–2 kHz, −2…−11.5 dB 3–5 kHz, −16…−27 dB 6–16 kHz, −8…−12 dB below 63 Hz (the mean of two commercial solo piano recordings, which read lowmid +13…+14 dB under `classical`) | −23…−16 | as classical, but sub +11, bass +9.5 / −8, lowmid / mid +6 / −6, presence +6.5 / −9, brilliance +7, air +9 (a warm hall recording and a close, bright one both pass); dull −10; tilt ±2.5; width from 12 % |
| `pop` | modern pop / dance-pop: 808 or four-on-the-floor kick + sub bass, clean low mids, bright | +2.5…+3 dB 40–63 Hz, −1 dB 200–400 Hz, +0.5 dB 2.5–5 kHz, +1.5…+2 dB 8–16 kHz (sub share 18 %) | −11…−8 | sub +4 / −5, lowmid +3, presence +3 / −6, brilliance +4, air +6; dull −4.5; LRA 3–12 |
| `rock` | rock band: kick / bass punch at 60–100 Hz, guitars and snare forward | −2.5…−4 dB below 40 Hz, +1…+1.5 dB 250 Hz–3 kHz (guitars), −1…−2 dB 12–16 kHz (sub share 6.5 %) | −10…−7 | sub +4 / −8, mid low −5 (scooped guitars), presence −6; PLR ≥ 5; LRA 2.5–12 |
| `film` | orchestral hybrid film score: orchestra + low hits / braams / synth sub, big hall | +2…+2.5 dB 40–63 Hz, +0.5…+1 dB 100–630 Hz, −1 dB 3–5 kHz, −1.5…−3.5 dB 6–16 kHz | −16…−10 | sub +6 / −6, presence +3 / −8, brilliance +4, air +6; dull −7; tilt ±2; PLR ≥ 8; LRA 5–20 |

Limits are dB vs the profile's reference balance, aligned so the median band reads 0; a mix that matches
its genre reads ~0 everywhere. Example: an outrun mix whose 41–55 Hz kick and bass put ~45 % of the energy
below 60 Hz reads `sub +6..+10 dB` (`balance_sub_high`) under `default`, but `sub 0..+4` (fine) under
`synthwave`; a genuinely boomy one (> +5 dB on top of the genre's own sub) is still flagged. The same
synthwave low end in a jazz trio reads sub +10 under `jazz` (flagged); a jazz master at −14.5 LUFS is
`loudness_low` under `default` and fine under `jazz`; an orchestral mix at −19.5 LUFS with LRA 17 is fine under
`classical` and `loudness_low` + `lra_high` under `default`. Balance limits the table leaves out keep the
default's (sub +5 / −9, bass +4 / −6, lowmid / mid / presence +4, presence −7, brilliance +5, air +7). How the
references were derived (reference-style library renders, published genre spectra: Pestana et al. 2013,
Elowsson & Friberg 2017, loudness practice) is documented in `engine/analysis/Profiles.cpp`.

Space targets (the report's `space` assessment, see below; judged in the full sections):

| profile | width above 150 Hz (`narrow_mix` below) | reverb returns vs the mix (`dry_mix` below, lush zone) | `washy` above | echo audible above | tails at stops above | bed under the lead (`thin_bed`) |
|---|---|---|---|---|---|---|
| `default` | 30…100 % | −18…−7 LU | −4 LU | −28 LU | −34 dB | not checked |
| `synthwave` | 40…100 % | −14…−6 LU | −4 LU | −24 LU | −30 dB | within 6 dB |
| `dreamwave` | 45…110 % | −11…−5 LU | −3 LU | −24 LU | −28 dB | within 5 dB |
| `darksynth` | 30…90 % | −16…−8 LU | −5 LU | −26 LU | −32 dB | not checked |
| `jazz` | 15…80 % | −20…−10 LU (one short room) | −6 LU | −28 LU | −52 dB (a 0.8–1.4 s room dies fast) | not checked |
| `classical` | 15…110 % | −14…−4 LU (the hall is part of the sound) | −2 LU | −28 LU | −30 dB | not checked |
| `piano` | 12…110 % | −14…−4 LU | −2 LU | −28 LU | −30 dB | not checked |
| `pop` | 35…100 % | −16…−7 LU | −4 LU | −26 LU | −36 dB | not checked |
| `rock` | 25…100 % | −20…−9 LU (drum room, snare plate) | −5 LU | −26 LU | −40 dB | not checked |
| `film` | 30…120 % | −13…−3 LU | −2 LU | −26 LU | −30 dB | not checked |

Reverb returns carrying more than 30 % of their energy below 150 Hz are flagged `washy` (low-end reverb); `classical`
allows 50 % and `film` 45 % (cellos, basses and timpani in the hall are its warmth).

- `loudness`: `[min, max]` LUFS, both in −60..0, min < max; replaces the profile's window (the report says
  `lufsTargetFrom: "override"` and keeps the profile's in `profileLufsTarget`).
- `silentNotes`: the compile-time silent notes (agentsound/silent_notes.py, see "Silent notes" below): `track` (a
  track id), `kind` (`no_sound` | `muted_layers`), `pitches` (non-empty, MIDI 0..127), `count` (>= 1), `beats`
  (optional, the first ones), `message`. The report repeats each as a `silent_notes` warning.
- **Strict**: `analysis` must be an object with only `profile` / `loudness` / `silentNotes`; an unknown profile name
  is an error listing the profiles; `loudness` must be two numbers; a `silentNotes` entry with an unknown key, a
  track id that is no track, another kind or a pitch outside 0..127 is an error.
- Python: `python -m agentsound build songs/<slug> --profile synthwave`, or a module-level
  `ANALYSIS = {'profile': 'synthwave', 'loudness': [-12, -9]}` in song.py (the CLI writes it into the render
  JSON; `--profile` wins over the file).

## Outputs (`agentsound render song.render.json --out DIR`)

- `DIR/mix.wav` (and `DIR/stems/<id>.wav` if requested)
- `DIR/report.json` — the "ears", judged against the analysis profile (`reference.profile`): loudness, peaks,
  per-section and per-track analysis, `warnings`, `suggestions`,
  `clicks` (detected discontinuities with time, bar/beat and the node they come from) and `images` (every image
  written, with what it shows)
- images: `overview.png` (index/dashboard), `loudness.png`, `tracks.png`, `bands.png`, `stereo.png`,
  `spectrogram.png`, `spectrogram_NN_<section>.png`, `clicks/click_NN.png`
- `DIR/report.json` `space` — is the mix **dry / narrow / thin / lush / washy**? (see "Space assessment" below)
- `DIR/report.json` `nodes[].dynamics` — are the notes of a melodic line played with real dynamics, or all
  equally loud? (see "Note dynamics" below)
- `DIR/report.json` `nodes[].silentNotes` + `silent_notes` warnings — did every note make a sound? (see "Silent
  notes" below)
- `agentsound zoom <wav> --at m:ss.sss [--ms 40]` (or `--beat B --song song.render.json|report.json`: through the
  song's tempo map, bar/beat of the meter in the title) / `agentsound clicks <wav>` inspect any WAV (mix or stem)
- `agentsound analyze <wav> --out DIR [--profile P] [--tempo BPM] [--section NAME START END]... [--from T --to T]`:
  the same report + images for any WAV (reference tracks, bounces; with a render's tempo and sections it reproduces
  the render's numbers), plus `report.measures`: 1/3-octave levels (dBFS, active frames), width/correlation per
  octave and band (`below120Hz`, `above150Hz`), short-term loudness distribution relative to the integrated
  (percentiles, histogram, PSR), transients per band (`perSec`, `hitDb` = how far the main hits stick out, attack),
  crest factors, `decay` / `sustain` tail estimates with a `robust` flag, `tempo` estimate. Without `--tempo` the bar
  grid uses the estimated tempo (`render.tempoFrom`). `--section` times count from the first analysed sample (`--from`);
  `--title` is UTF-8.
- `agentsound compare-png compare.json --out compare.png` (the picture of `python -m agentsound compare`) and
  `agentsound cover --style S --title T ... --out cover.png` (album covers, `--size` 256..4000; `--list` shows styles and
  palettes)
- stdout: one JSON line `{"ok":true, "seconds":..., "renderSeconds":..., "out":"..."}`; errors: exit code 2
  (invalid input) or 1 (internal), message on stderr.

Instrument and effect types, and every parameter with range, default and unit, are listed by
`agentsound params` (markdown with `--markdown`, JSON with `--json`), generated from the ParamSpecs.

## Space assessment (`report.space`)

The report judges whether the mix has space: stereo width, reverb/echo level, sustained bed under the lead.
Everything is measured from the render itself; the routing of the render JSON (outputs, sends, fx, notes) tells
the analyser which buses are **effect returns** (fed by `sends`, kind from their fx: `reverb` (reverb, convolver), `delay`, `gated`
(gatedreverb), `width` (chorus/ensemble/width), `other`; a return may also take other buses' outputs, e.g. an
echo feeding the hall) and which are **groups** (fed by track `output`s); an automated send counts with its
loudest automated level (a throw-only send at a static -120 dB still feeds its return). It gives
every node a **role** (`nodes[].role`, `space.roles`): `drums`, `bass`, `bed` (long notes: median >= 1.5 beats
and >= 0.75 s, or polyphonic chords >= 1 beat; ids like pad/strings/choir), `lead` (ids like lead/hook/melody,
else the loudest monophonic line), `other` (arps, keys, plucks), `fx` (a few long notes: risers, impacts),
`return`, `group`. Ids decide first (whole words where a substring would mislead: `heartbeat_pad` is a bed,
`sunrise_lead` a lead, `sub_808` a bass, `bass_drum` drums), then notes, then the audio.

- **Full sections** (`space.measuredOver`, `sections[].full`): within 4 LU of the loudest section and, when the
  song has drums, with the drums playing (within 10 dB of their loudest section). The top-level values of
  `space` are measured over them together; warnings are about them. Sections > 10 LU under the loudest are
  `quiet` (measured, not judged).
- **Width**: `widthPct` / `correlation` (whole mix), `widthAbove150HzPct` / `correlationAbove150Hz` (the image
  above the mono low end: what is judged, `narrow_mix` below the profile's range), `musicWidthPct` (the
  bed/lead/other tracks together, dry). `opportunities` (when narrow): the music parts that would widen the mix
  most (centred < 12 % first) with their width and widener (`chorus`, `width`, `unison spread`, `dx7 detune`
  or `none`).
- **Wetness**: `wetnessLu` = all reverb returns vs the mix in LU (K-weighted; `-12` = the reverb sits 12 LU
  under the mix), `echoLu` the same for delay returns, `returns[]` {id, kind, lu, activeLu (delay returns: vs the
  mix on the ticks where the echo sounds, so sparse throws are judged by how loud they are when they happen),
  lowPct (energy below 150 Hz), widthPct, sectionsLu[] (per section, parallel to `space.sections`)}. With the routing known the
  reference is the **pre-master sum** of the master's inputs (`reference`), so the master limiter's gain does
  not change it (comparing a return's `nodes[].lufs` with the final `lufsIntegrated` does: it reads the returns
  4-8 LU too low behind a limiter with gain). `tails` {tailDb, count, events[] {time, bar, tailDb, decaySec,
  musicReturned}}: where the music stops (breaks, stops, the end) the returns' level 0.3-0.8 s later vs the
  music before, and how long they stay within 40 dB of it.
- **Bed**: `bedVsLeadDb` = the bed roles vs the loudest lead, K-weighted, on the 100 ms ticks where the lead
  plays (`-8` = the bed sits 8 dB under the lead); `lead`, `beds[]` name them.
- **Verdict** (`verdict`, per section and over the full sections): `washy` (reverb above the profile's
  `washyLu` - outside the full sections 3 LU past it -, low-end reverb, or correlation < 0) > `dry` (reverb under the lush zone, or no reverb return and
  no reverb insert on the music) > `narrow` > `lush` (width and reverb inside the targets, bed fine) > `ok`;
  `quiet` / `silent` sections are not judged. `issues[]` lists every finding: `dry`, `no_reverb`, `narrow`,
  `washy`, `low_wash`, `phasey`, `thin_bed`, `over_wide` (top level only).
- **Warnings**: `dry_mix` (with a send plan: the current sends into the reverb returns and the levels that
  reach the target, beds/leads without a reverb send), `narrow_mix` (with the opportunities and the effects to
  widen them), `thin_bed` (bed too far under the lead, or no bed at all; synthwave / dreamwave), `washy` (too
  much reverb, or low-end reverb: high-pass the returns), `over_wide` (a music part widened into anti-phase,
  whole-song correlation < -0.1 - e.g. a fully wet chorus plus a width boost; the classic Juno balance, chorus
  mix 0.5 + width 1.4, stays around +0.2 and sounds as wide - it goes hollow and quiet in mono and costs the
  `lush` verdict; an effect return below -0.25 is info; with the widening params to back off),
  `reverb_inaudible` (an echo return under the profile's `echoMinLu` while it sounds (`activeLu`), a second reverb return > 10 LU under the
  lush zone (info), or tails that die when the music stops). A `dry_mix` is only info when music tracks carry
  their own reverb inserts (not measurable).
- `space.targets` repeats the profile's limits; `overview.png` has a SPACE strip (verdict per section with
  `w` width above 150 Hz, `rev` reverb LU, `bed` dB) and a SPACE line; `stereo.png` shows the width above
  150 Hz against the target band, a WETNESS panel (reverb returns vs the mix over time with the lush zone and
  the washy limit, echo as a line, tail markers), the SPACE strip, and each node's role in the stereo field
  (amber: a centred part to widen).

## Note dynamics (`report.nodes[].dynamics`)

"Are all the lead notes equally loud?" Every track (not buses, drums or fx one-shots) is measured note by note from
its own rendered audio:

- **Onsets**: the notes of the render JSON (`onsets: "notes"`; note starts within 30 ms are one event, a chord or a
  flam, with its highest velocity and pitch), or - for a track without notes - level rises of 6+ dB within 10 ms in
  the audio (`onsets: "audio"`). Onsets quieter than -70 dBFS (muted / automated away) are skipped.
- **Level of a note**: the mean level over the first 30-100 ms of the note (up to the next onset), dBFS (full-scale
  sine = -3).
- `notes` (events), `spreadDb` = 10-90 percentile spread of the note levels over the song, `levelDb` = [p10, p90],
  `sections[]` {section, notes, spreadDb}, `velocity` {min, max, p10, p90} = what the notes were given, `chordPct` =
  events with 2+ notes, `thresholdDb` = the profile's `noteSpreadMinDb`.
- **Phrases**: each section cut into ~8-bar chunks (6-12 bars); those with 8+ notes are judged (`phrases`; a sparse part
  with 8+ notes but no such phrase is judged over the whole song). `phraseSpreadDb` = median audio spread per phrase.
  The audio spread over-reads the playing: a chorus / microshift wobble, the register or the samples scatter the note
  levels by several dB although every note is played alike. So with known velocities the analyser also measures the
  sound's **velocity response** (`velocityDbPer10`: dB per 10 velocity steps; regression of the note level on velocity
  inside the phrases with the register taken out; the level is what each note adds over the sound just before it
  when 30 %+ of the notes have a clear attack, so pedalled / ringing notes do not flatten it; conservative: the slope
  minus one standard error, so a few narrow velocities never pass as a response; clamped to 0..1.25 x the (v/127)^2
  curve) and the part of each phrase's level range it explains (`velocityPhraseDb` = response x the phrase's 10-90 %
  velocity range).
  **`dynamicsDb`** = the played dynamics that are judged: the median over the phrases of min(audio spread, velocity
  part); with expression / dynamics automation or modulation (`automatedDynamics`: dynamics that need no velocity)
  the audio spread alone. `flatPhrases` = phrases under the threshold. Wide velocities with a small velocity part =
  the sound flattens them (low `amp.velocity` / `velsens`, velocity layers without level, legato notes without a new
  attack); a small audio spread with a big velocity part = a compressor squeezes them; narrow velocities = the part
  was written flat.
- `kind` / `why`: `lead` (the space role lead - ids like lead/hook/melody/vox -, melody instruments by id - sax,
  trumpet, flute, violin, clarinet, solo... -, or a melodic part at or above E3 that is the loudest melodic part in
  at least half of the sections it plays in where no lead plays), `melodic` (other melodic parts: keys, counter-lines,
  comping), `bass`, `bed` (role bed: sustained pads / strings / choir) and `even` (ids arp / seq / ostinato, and
  unnamed parts whose notes sit on a fixed 8th/16th grid - also swung pairs - for 70 %+ of the steps, or fast figures
  of short notes: 85 %+ of the steps 8ths or faster, median note <= 0.3 beats). `judged` is
  true for lead / melodic, and for bass under profiles with `judgeBassDynamics` (`jazz`, `classical`: a walking /
  continuo bass is played; a synth bass pulse is not); `bed` and `even` parts are measured but never flagged (an even
  16th arp is its idiom).
- **Warning** `flat_dynamics`: a judged part whose `dynamicsDb` is under the profile's `noteSpreadMinDb`
  (`flat: true`) - severity `warn` for a lead, `info` for melodic / bass parts; also `info` for a lead that is dynamic
  overall but has a quarter or more of its phrases flat. The message gives the numbers, the velocities, the likely
  cause (velocities that barely move, the instrument's velocity parameter, a compressor / limiter on the track) and
  the fix: velocity arcs over each phrase (55-118: accents on the phrase peaks and strong beats, softer passing and
  repeated notes, octave doubles softer), `amp.velocity` (va) >= 0.7 / `velsens` (dx7, sf2, sampler) >= 0.8, a gentler
  track compressor. `sections` of the warning = the sections with flat phrases.
- Thresholds (`reference.noteSpreadMinDb`, `reference.judgeBassDynamics`): 3 dB, `jazz` 4 dB (a played piano / horn
  line breathes more: accents, ghosted passing notes), `classical` 4.5 dB (hairpins, accents, soft upbeats). Typical
  values: a synth lead at velocities 81-103 through `amp.velocity` 0.3 reads 0-1 dB (its chorus may still scatter
  the audio by 5-7 dB), velocity arcs 55-118 through a velocity-sensitive sound 6-12 dB.
- Calibration (the songs as they were when the user asked "sind alle Lead-Noten gleich laut?"): polaroid-summer
  `lead` (velocities 81-103, `amp.velocity` 0.3) audio 6.6 dB but 0.0 dB from velocity -> warn, `lead2` 0.0 -> warn,
  the `sax` with expression automation 5.4 dB (1 of 4 phrases flat: info); midnight-interstate `hook` 1.9 dB audio,
  `hook-double` 0.2, `verse-lead` 0.0 -> warn, `sax` 6.6 dB fine; perry-street-rain (jazz, 4 dB) `piano` 2.3 dB from
  velocity (its velocities span a median 15 steps per phrase at ~1.9 dB per 10 steps) -> warn, `comp` 1.7 and the
  compressed walking `bass` (audio 3.8 dB, 0 from velocity) -> info.
- `tracks.png` marks a flat part at the end of its lane (`FLAT X dB` = its `dynamicsDb`, red = lead / warn, amber =
  info; `n/m phrases flat` for a lead that is flat only in some phrases); the build summary prints a "note dynamics"
  block (per judged track: `dynamicsDb`, FLAT, notes, velocities, audio spread and velocity part, flat phrases; the
  others on one "not judged" line).

## Silent notes (`report.nodes[].silentNotes`, `silent_notes` warnings)

"Did every note make a sound?" Two ears, one warning code:

- **Compile time** (Python, before rendering: `agentsound/silent_notes.py`, run by `Song.compile()` on every unmuted
  track): a note is silent when no sample can play it - `sampler` (inst.sampler / inst.kit / inst.sfz / sampled
  patches): no zone covers its key (after the `transpose` param) and velocity (with `layers: "dynamics"` any velocity
  is covered; `*silence` zones do not count), or the keyswitch articulation active at its time has no zone there
  (keyswitch notes themselves never count); `drums`: its key is none of the machine's pieces (35-51, 54, 56, 57, 59);
  `stack`: no layer takes it (key / velocity range, key / velocity fades - a fade starts at gain 0 on `keylo` itself -,
  velocity curve, layer transpose) or every layer that takes it is silent for it, or (`kind: "muted_layers"`) only
  muted layers take it (a `layers.<id>.mute` lane is followed). va, dx7 and sf2 are left to the render-time ear.
  Round robins, random layers and trigger conditions count as covered when any zone of the key could play. The
  patches' prose `Range:` notes are playing advice, not limits: the zones are the machine-readable range. The findings
  go to `song.warnings` ("silent notes: ...": count, GM names on a kit / note names, bar:beat times, the cause - the
  kit has no sample there, "its samples cover G4-C6 (67-84) only", the velocity, the articulation - and a fix: map
  the piece, with the same pack's samples of that role when the pack is installed; transpose the part into the
  range) and to `analysis.silentNotes` of the render JSON. The drummer (`agentsound.drummer`) warns at arrange time
  when the kit lacks a piece it plays (`Performance.warnings`: "the kit has no crash: 18 crash strokes play on
  hat_open (46) instead") and, when the part was arranged for another kit than the track plays (kit=None: General
  MIDI), names the strokes that land on keys without samples and the fallback `kit=<track>` would play;
  `Performance.play(track)` puts both into `song.advice`, which every compile repeats in `song.warnings`.
- **Render time** (`engine/analysis/SilentNotes.h`): every analysed track with notes (any instrument), on its own
  post-fader signal. Notes starting within 30 ms are one event (a crash on the kick is heard as the kick: the
  compile-time ear covers that). An event's level = the loudest 10 ms window between its start and min(its end +
  0.25 s, its start + 3 s, the next event - 5 ms), at least 30 ms: a slow attack, a release-triggered sample, a
  delayed stack layer still count, and a note under its own sustain, a legato / tied note or a grace note inside
  another note's tail reads the sound that is there. Two kinds, by whether the note has an attack of its own (its
  level rises 3+ dB over the 10 ms just before it, above -100 dBFS): a note that adds **nothing** to what was
  sounding is silent under `thresholdDb` = `max(median - 40 dB, min(-60 dBFS, median - 30 dB))`, median = the
  track's median event level (`medianDb`): 40 dB under its typical note, or under -60 dBFS when that is 30+ dB under
  it (a whole track that quiet is `silent_node` / `inaudible`, not this); a note **with an attack** does sound and
  is flagged only 40 dB under the median ("too quiet to be heard"). **Excused** (`excused`, `excusedBy`, never
  warned): a silent event while an automation lane has closed the level - gainDb / level / gain / output lanes 30+ dB
  under their maximum, expression / volume / dynamics under 10 % of it, a cutoff 4+ octaves under its maximum and
  below 300 Hz, a mute lane on -, and every silent event of a track with a `vocoder` insert (the carrier sounds only
  while its modulator speaks). Notes in the last 50 ms of the render are not judged. `nodes[].silentNotes`: `notes`,
  `events`, `medianDb`, `thresholdDb`, `silent` (notes), `at` (bar:beat), `pitches`, `excused`, `excusedBy`,
  `compileSilent` (the compiler's count).
- **Warnings** `silent_notes` (ranked right after clicks): each compile-time finding once (`warn`), with "(the render
  measured N of them silent)" - the others sound together with other notes (masked) or lie outside a preview
  render -; silent events the compiler did not explain get their own warning: "made no sound" (`warn`, with a
  `zoom` suggestion) or "too quiet to be heard" (`info`), with count, pitches (GM names on a kit), bar:beat, the
  levels and what to check.
- Calibration (the songs as of this commit): the compile-time ear found the old `ghosts-of-ocean-drive`'s 17
  crashes on kit A (arranged with `kit=None`; the render measured 1 of them silent, the others start with a kick),
  and on the current songs: `ashes-and-chandeliers` `choir_f` 41 notes under G4 (the female choir's samples cover
  G4-C6 only; 6 measured silent), `choir_m` 4 on G4, `tuba` 1 on C1, `gtr3` 1 on E6; `polaroid-summer` `choir` 37
  notes under G4; `orbital-station` 14 tambourines on the TR-808 kit (no tambourine sample). Render time, nothing
  else on children-of-neon, perry-street-rain, minetta-lane-waltz, lamplight-avenue, ghosts-of-ocean-drive,
  ashes-and-chandeliers, polaroid-summer and the gymnopedie / nocturne études: the vocoder chords between the words
  (children-of-neon `robot` 4 notes, polaroid-summer `vox` 10) are excused; soft hats and brush strokes 20-39 dB under
  their kit (lamplight `perc`, perry / minetta brushes at -60 / -65 dBFS) have an attack and stay unflagged; only hats
  40 dB under the kit are 'too quiet' (info: orbital-station 4, the old ghosts 9 - the ones its A&R later called
  nearly inaudible).
