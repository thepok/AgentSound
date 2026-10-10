# EDM recipe: house, techno, big room, future bass, melodic house

Club music built in 8- and 16-bar blocks: a kick that owns the floor, a sub that owns the low end, everything else
pumping around the kick, tension built by builds and released by drops. Analysis profile `edm`
(`ANALYSIS = {'profile': 'edm'}`), mixer profile `edm` (`python -m agentsound mix`), band presets `house`, `techno`,
`big_room`, `future_bass`, `melodic_house` (`agentsound/bandlib/edm.py`), sounds `edm/*` (`agentsound/patches/edm.py`).

Read `recipes/HUMAN_FEEDBACK.md` first. The rule that matters most here: **no beepy synth hook** ("etwas
Piepsiges", "bissel lahm"). EDM is the genre where that mistake is easiest - a thin saw or sine line in A4-A6 is
exactly what the user rejected. The hook goes on a sung / chopped vocal, the bright high house piano, or `edm/lead`
(a supersaw with a saw body an octave below) - never a bare oscillator.

## Band presets (start here)

```python
from agentsound import bands
b = bands.make('melodic_house', s)               # drums bass chords pad pluck lead + plate / hall / echo, master/edm
g = b.info['grooves']                            # one bar per section kind: 'intro' 'groove' 'build' 'drop' 'break'
b.drums.plan({intro: g['intro'], build: g['build'], drop: g['drop'], brk: g['break']},
             fills={build: (8, snare_roll(4, build=True))}, crashes={drop: 118})
ANALYSIS = b.analysis
```

| preset | tempo | kit | bass | chords | hook | pump |
|---|---|---|---|---|---|---|
| `house` | 120-126 | TR-909 + sine sub | `edm/bass` offbeat 8ths | piano house chords (Salamander) | bright piano | 8 dB |
| `techno` | 125-135 | modular kit, rims | `edm/reese` rolling 16ths | `edm/pluck` stabs into the echo | pluck / supersaw | 6 dB |
| `big_room` | 126-130 | main-room kit (layered kick, big clap) | `edm/bass` | `edm/supersaw` | `edm/lead` | 10 dB |
| `future_bass` | 140-160 (half-time feel) | TR-808, trap hats | `edm/bass` held roots | `edm/future_chords` (wobble, formant) | piano / vocal chops | 12 dB, long release |
| `melodic_house` | 120-124 | TR-909 + shaker | `edm/reese` held | soft `edm/supersaw` | bright piano / vocal | 8 dB |

Options: `lead='supersaw' | 'piano' | 'pluck'`, `kit='909' | '808' | 'main_room' | 'modular'`, `sub=` (the sine
thump under the kick: True = the song's tonic), `without=`, `sounds=`, `ids=` (agentsound/bands.py). Every preset
sets the kick pump (`song.sidechain(..., pitches='kick')` on bass / chords / pad / pluck), the drum bus (parallel 4:1
+ tape) and `master/edm` with the style's limiter drive. `songs/_bands/house/song.py` is the 24-bar demo (STYLE =
any of the five).

The drummer knows the club groove too: `drummer.arrange(s, style='house', kit=b.drums)` - four on the floor in every
section, closed 8ths in intros and breakdowns, 16ths in builds, the open hat on every & in the drops, a clap layer,
snare rolls (no tom runs), machine-tight. Use it when you want the section energies and fills decided for you; use
the preset's grooves when you want to write each bar.

## Sub-styles

- **House / deep house** (120-126): 909 four on the floor, offbeat open hats, a shaker in 16ths, clap on 2 and 4,
  offbeat bass between the kicks, piano or organ chords (the classic house piano stab: `x..x..x.` in 8ths), a
  warm pad. Swing the hats a touch (0.54). Hooks: piano riff, sung / chopped vocal.
- **Techno** (125-135): hypnotic, minimal harmony (one chord or a two-chord vamp, phrygian / minor), a rolling reese
  or 16th bass, rims and metallic percussion, the pluck as a stab into the echo, long filter moves instead of chord
  changes. Breakdowns are textural (pad + echo), builds are filter + snare roll.
- **Big room / festival** (126-130): a huge layered kick, supersaw chords, a short catchy lead hook (3-6 notes),
  long builds (16 bars, snare roll 8ths -> 16ths -> 32nds, riser, a pitch-up), a one-beat silence, the drop with a
  crash and an impact. The hook on `edm/lead` doubled by the vocal chops.
- **Future bass** (140-160, half-time): 808 kick in a syncopated half-time pattern, trap hats (16ths with 32nd
  rolls), the snare / clap on beat 3; wide detuned chords (`edm/future_chords`) that BREATHE with a 12 dB pump and a
  long release, pitched vocal chops as the lead, pitch-bends into chords. Rich chords: maj7, add9, min9, sus2.
- **Melodic house / progressive** (120-124): emotional minor progressions, a reese or held sub, the pluck arpeggio
  into a dotted-8th echo (half the sound is the echo), soft supersaw chords, a bright piano or a sung hook, long
  breakdowns with the pad and the vocal.

## Form (8- and 16-bar blocks; every boundary is a phrase of 8)

```
intro 16 | groove A 16 | breakdown 16 | build 8 | DROP 1 16 | groove B 8 | breakdown 2 16 | build 8 | DROP 2 16 | outro 8-16
```

~3:00 at 124 BPM is ~92 bars: shorten the intro and outro to 8 for a radio / listening edit. Rules:

- **Intro**: drums first (kick + hats, or the filtered groove), elements enter every 4-8 bars. A DJ intro is
  16-32 bars of drums; for listening keep it 8.
- **Breakdown**: the kick drops out, the pad / piano / vocal carry the hook quietly (the first time the melody is
  heard plainly). The limiter rides down 3-5 dB (`s.master.lane('fx.limiter.gain', ...)`).
- **Build** (8 or 16 bars): a snare roll accelerating (`snare_roll(8, build=True)`: 8ths -> 16ths -> 32nds), a
  noise riser (`s.transitions(riser=True).into(drop, riser=16)`), the chords' filter opening (`lane('instrument.cutoff',
  {build: (600, 8000, 'exp')})`), the pump deepening, the bass dropping out in the last 1-2 bars, a pitch rise.
- **The drop**: preceded by a breath (`breath=1`: one beat of silence, or a vocal tag alone), lands on a crash + an
  impact (`impact=('A1', 120)`), everything in at once. The hook plays, the bass and kick at full weight.
- **Drop 2** must change something: a counter-melody, the chops answering the lead, a key lift (rare), a new bass
  rhythm, the vocal on top. Never an identical copy.
- **Outro**: the groove strips back in reverse order; the last bar has a downlifter and a reverb tail.

## Harmony

- Minor keys dominate: `i VI III VII` (Am F C G), `vi IV I V`, `i iv VI V`, `i VII VI VII`. Four chords, one per
  bar (house, big room) or one per 2 bars (melodic, progressive). Techno: one chord, movement by filter.
- Future bass / melodic: rich voicings - add9, maj7, min9, sus2, spread wide (C3-E5); a pedal note under changing
  chords; slash chords (`IV/I`).
- Breakdowns can re-harmonise the hook (fewer chords, longer), builds sit on V or IV (or the i with a rising pedal).

## Rhythm and drums (`patterns.drums` grids, 16ths)

- Kick: four on the floor (`x...x...x...x...`), machine-tight - no humanize on the kick; a sine sub thump under it
  on the song's tonic (the presets' `sub=True`, `bandlib.pop.kick_sub`).
- Clap / snare on 2 and 4 (half-time: on 3). Open hat on every & (`..x...x...x...x.`), closed 16ths with machine
  accents, a shaker (key 82) in 16ths. Shape the hat velocities (on-beats 100 %, & 80 %, 16ths 55-60 %).
- Variation every 4 / 8 bars: a kick drop-out on bar 8, an open-hat lift, a clap roll, a crash on each phrase's
  downbeat. A drop's 16 bars are two 8-bar phrases: the second adds a part.
- Future bass: half-time kick `X.....x...x..x..`, clap on 3, hats with 32nd rolls (`patterns.drums` with step
  '1/32' for the roll bar).

## Bass: sub + mid

- Two layers (`edm/bass`, `edm/reese`): a clean mono sine sub (< 90 Hz) and a mid layer (saws / square, high-passed
  at 100 Hz) for the notes a phone can play. Roots E1-E2.
- House: offbeat 8ths between the kicks (`bassline('offbeat', ...)`); techno: rolling 16ths (`x.xx`); melodic /
  future: held roots and slides (legato overlaps glide).
- The kick pumps the bass 8-12 dB with a fast attack (2 ms) and a release ~55-60 % of a beat - the kick and the sub
  never sound together. Check the report's masking line: "low-end ducking between them 6+ dB".

## Chords, pads, plucks, leads - NOT beepy

- **Chords**: `edm/supersaw` (big room, melodic), `edm/future_chords` (future bass), piano (house). Pumped 6-12 dB.
  Their filter is the build's main instrument.
- **Pad**: `synthwave/warm_pad` in breakdowns and under the drops, hall -6.
- **Pluck**: `edm/pluck` 16th / 8th chord-tone patterns C4-C6 INTO the dotted-8th echo (sends echo -9).
- **The hook** (HUMAN_FEEDBACK "Melody / lead sound"): a sung vocal (Hanami, hard-tuned), vocal chops, the bright
  high piano (`sampled/piano_lead`, C5-C7, octave-doubled), or `edm/lead` (supersaw + an octave-down saw body; A4-C6
  with phrase arcs, vibrato on held notes). Never a sine / triangle / single saw line. Velocity arcs 60-118
  (`humanize.touch`): `flat_dynamics` must be 0.

## Vocals in EDM

- **The sung hook**: `singer.sing(s, line, lyrics, voice='hanami', style='pop', tune='hard')` - the hard-tuned,
  stepped pop-EDM vocal (retune 0 ms: every note change a flip). Short lines, open vowels on the long notes, a
  title hook of 3-6 words repeated. Lyrics per `roles/lyricist.md` (original, circle the theme).
- **Vocal chops**: `ch = singer.chops(vox, line, at=drop, slices=['oh', 'night', 2], unit='syllable')` - slices of
  the singer's OWN takes (one per syllable / word / phrase) retriggered in the rhythm of `line` and pitched to its
  notes (resampled: up = smaller and brighter - the classic chop). A new sampler track `chops` with the chain
  `edm/vocal_chop` (high-pass 220 Hz, presence, compressor, tape, chorus); `sends={'echo': -10}`. The chops answer
  the sung hook or replace a lead in the drop. Give them velocity arcs (`humanize.touch`) - the sampler passes them
  (velsens 0.85). `ch.describe()` lists the slices; the build prints a `chops` line.
- **Prism / harmoniser**: `singer.prism(vox, harmony, preset='prismizer')` - the hook re-sung on the chord tones,
  tight and wide (the Francis-and-the-Lights wall) for a drop's vocal moment.
- **Talk box**: `singer.mouth(...)` + `speech.talkbox(guitar_or_synth, mouth)` - a short talk-box answer in a
  breakdown or after a drop (the user's favourite vocal effect: keep it as a special moment, 2-4 bars).
- The vocal is the lead in its sections: bed (chords / pad) 3-6 dB under it, the chords carved / ducked by it
  (`hero(vox.track, family='vocal', genre='pop', bed=[...])`), the chops and pluck out of its 2.5-6 kHz while it sings.

## Transitions

- `fxh = s.transitions(riser=True, reverse=True, impact=True, down=True)`;
  `fxh.into(drop, riser=16, reverse=2, impact=('A1', 120), breath=1)`; `fxh.into(breakdown, down=('A3', 8, 100))`.
- Snare rolls (`snare_roll(8, build=True)`), a crash on every drop downbeat, a reverse cymbal into breakdowns, a
  filter sweep (`lane('instrument.cutoff', ...)`) on the chords / pad, a high-pass on the master group or the
  music in the last bar of a build (the "lift").

## Mix and master (profile `edm`, mixer profile `edm`)

| target | value |
|---|---|
| loudness | integrated -10..-6 LUFS, the drops -9..-6 (master/edm limiter gain ~10-12 dB: past that the 30 ms release, not the drive, sets the loudness); true peak <= -1 dBTP |
| PLR | >= 5 dB |
| LRA | 2-10 LU (breakdowns are the quiet part: limiter ridden 3-5 dB down) |
| sub (20-60 Hz) | the kick + sub own it: more than pop, less than synthwave |
| low mids (250-500 Hz) | carved: -1.5 dB on the master, -2..-3 dB on chords / pad |
| width | 35-110 % above 150 Hz (supersaw / future chords wide), everything < 120 Hz mono |
| reverb | the drops fairly dry (-18..-12 LU), breakdowns wet (hall + echo) |
| levels | lead / vocal -18, drums -18, bass -19, chords -23..-25, pad -26 LUFS (pre-master) |
| pump | bass 8-12 dB, chords / pad 6-12 dB, pluck 3 dB from the kick |

Checks: `clicks` 0, `silent_notes` 0, `flat_dynamics` 0; the masking line kick / bass "they alternate"; the vocal
owns the presence band in its sections (the build's `vocals` lines).

## Checklist

- [ ] 8/16-bar blocks; builds, breaths and drops; drop 2 differs from drop 1.
- [ ] The hook is sung, chopped, a bright piano or `edm/lead` - never a beepy oscillator.
- [ ] Kick + sub own the low end, everything else pumps (sidechain on bass, chords, pad).
- [ ] Every melodic part has velocity arcs; the chops too.
- [ ] Breakdowns softer (limiter lane), drops loud (-9..-6 LUFS; the song -10..-6 integrated).
- [ ] Credits: the kits (909: hyperreal licence unclear; SampleRadar: no redistribution), Hanami (attribution,
      non-commercial vocoder) - private listening unless checked.
