# Rock recipe: a band in a room, instrumental

Drums, bass, two rhythm guitars and a lead voice (lead guitar, organ, sax or synth) that plays the "vocal"
melody: a live band that locks into a groove, gets loud in the chorus, and sounds like it was played, not
programmed. Punchy kick and snare in the centre, a wall of double-tracked guitars left and right, the bass glued
to the kick, the mids forward and dense. References: Led Zeppelin, AC/DC, Foo Fighters, Queens of the Stone Age,
Arctic Monkeys, The Strokes, Muse, Royal Blood; instrumental: Joe Satriani, The Shadows, Explosions in the Sky,
Mogwai, Khruangbin. Analysis profile: `rock`.

## Band presets (start here)

One call sets up the whole band - sampled players, amps and cabinets, placement, eq, compression, the drum bus, the
returns, the master chain - balanced on a demo and tuned for the `rock` profile. Compose the parts, not the mix:

```python
from agentsound import *
from agentsound import articulation as art, bands

ANALYSIS = {'profile': 'rock'}                       # = b.analysis
b = bands.rock_band(s)                               # or bands.make('rock_band', s, keys='piano', gain='high')
from agentsound import guitarist as gtr
RIFF = 'E> - . E . . G> - - . A - G E - . | D> - . B - . A - . . E . G A# B> -'     # steps on a 16th grid
gtr.double(gtr.riff(RIFF, bpm=s.tempo, grid='1/16', section=verse), (b.gtr_l, b.gtr_r), verse)   # quiet: palm-muted
gtr.double(gtr.riff(RIFF, bpm=s.tempo, grid='1/16', section=chorus), (b.gtr_l, b.gtr_r), chorus) # open power + 8va
b.lead.play(art.legato(line).glide(110, where=art.leaps(3)), chorus)
art.vibrato(b.lead, line, chorus, depth=28, rate=5.6)
print(b.describe())                                  # roles, buses and how to play them (b.notes)
```

| preset | roles | sounds | demo |
|---|---|---|---|
| `rock_band` (options `keys='organ'\|'piano'`, `gain='crunch'\|'high'`, `kit='big_rusty'\|'unruly'\|'red_zeppelin'`) | drums, bass, gtr_l, gtr_r, lead, keys | Karoryfer Big Rusty kit (close + OH mics, 14 layers x 4 RR, velocity-calibrated) with a slow-attack punch compressor into a drum bus with New York parallel compression + tape and the Voxengo drum room (crushed); picked Growlybass into an SVT-style DI + tube amp rig; **gtr_l** FreePats FSBS DI -> the tube amp as a cranked Plexi -> Marshall 4x12 Greenback IR (hard left), **gtr_r** Emily SG DI -> two-stage crunch -> 2x12 V30 (hard right), `gain='high'`: metal 4x12 + a hotter crunch; lead FSBS DI -> driven Marshall, mono legato, dotted-8th echo + 224XL plate; setBfree rock organ with a Leslie-style tremolo (or the Salamander grand) | `songs/_bands/rock_band` (126 BPM E minor; after the rock pass: -9.6 LUFS, LRA 4.5, width 26 %; warns of the intro riff's kick + bass unison and flat dynamics of its narrow-velocity gtr_r / band lead) |
| `indie_band` (`keys='wurli'\|'organ'`, `kit='big_rusty'\|'unruly'\|...`) | drums, bass, gtr_l, gtr_r, lead, keys | Big Rusty kit (or `kit='unruly'`: the small dry garage kit, thin below 60 Hz) in the 224XL room; Fashionbass; **gtr_l** clean jangle (FSBS single-coil -> clean 1x12, compressor, chorus), **gtr_r** crunch (Emily SG -> 1x12 H30 edge of breakup); Shinyguitar archtop lead (pickup) through a blues amp with a 110 ms slapback; Greg Sullivan Wurlitzer through a small amp with tremolo | `songs/_bands/indie_band` (152 BPM D major: -9.6 LUFS, LRA 3.9, width 30 %, 0 warnings) |
| `power_ballad` (`kit=...`) | piano, strings, pad, drums, bass, lead | Salamander grand, VPO string section, Juno pad, Big Rusty kit in the big 224XL room + rich plate, fingered Growlybass, a singing FSBS lead (Marshall, quarter-note echo, 224XL hall) | `songs/_bands/power_ballad` (76 BPM A major: -10.0 LUFS, LRA 4.4, 0 warnings) |

What the presets do for you, and what you still decide:

- **Guitars are DI samples through ONE amp** (`rock.amp(kind)` = `patches.sampled_guitars.amp`: the engine's tube
  `amp` - cascaded triode preamp stages, the Marshall / Fender tone stack, a sagging push-pull power amp - into the
  `cab/*` cabinet IR and a mic roll-off; kinds `clean blues crunch rock metal lead` (`space_ir.AMPS`), any knob:
  `amp('crunch', gain=6.5, mid=7)`). Measured against the old one-saturator amp on the same riff: the low mids are
  back (+3 dB at 315-630 Hz, the Sweet Child chorus wants them), odd-harmonic crunch instead of the hollow fuzz. The DI
  sets are level-matched into the amp (`rock.DI_LEVEL`: Emily / Shiny are recorded ~13 dB quieter than FSBS). Every
  rhythm guitar is keyswitched (`rock.di_guitar`): `open` (default), **`palm mute`** and **`dead note`** (real
  muted-string scratches from Emilyguitar, 5 sets x 5 round robins spread over the neck; borrowed for FSBS) -
  `clip.articulate('palm', span=(a, b))`, `.articulate('dead', where=lambda n: n.dur < 0.15)`. No installed pack has DI
  palm-mute samples, so the palm mute is an emulation measured against the real amped chugs of
  `sampleradar-heavy-metal-guitar` (`sampled_guitars.PALM`: as loud as the open chord, the 80-315 Hz thump kept, a pick
  envelope, -22 dB at 200 ms through the amp, as bright as the open chord: the tight chug).
- **Riffs: the riff player** (`guitarist.riff(spec, bpm=, section=)`, docs/COMPOSE_API.md "Riffs and the wall"): write
  the riff once as steps (`'E> - . E . . G> -'`: note, `-` hold, `.` rest, `x` dead scratch; `>` accent, `!` let ring,
  `p` palm, `^` a choked hit) and let the section's energy play it - verse: palm-muted single notes; pre-chorus: power
  chords, the short notes chugged, accents open; chorus: power chords + octave ringing. `end='choke' | 'slide' |
  'build'` (or `into=` a bigger section) for the fill; `gtr.pedal([...])` an open-string pedal riff; `gtr.hits(cell,
  'E', bpm)` the stops in unison with the drums; `gtr.build_up('E', 4, bpm)` the pre-chorus chug build; `part.cell()`
  the riff's rhythm for the drummer (`DrumMotif.make(cell=...)`) and the bassist (`kick=`).
- **The wall: `guitarist.double(part, (b.gtr_l, b.gtr_r), at)`** - two PERFORMANCES, not a copy: other takes (`take(k)`:
  new timing / velocity noise), each take's timing drifting +-7 ms around the beat on a smooth curve (rushing and
  dragging), a slow tuning drift per take (+-4 ct on 'instrument.pitchbend', a different offset per take), other round
  robins (the tracks' sampler seeds) and two different guitars into two different amps / cabs (gtr_l FSBS -> Plexi 4x12,
  gtr_r Emily -> crunch 2x12). Width per octave on the-drummer-speaks: 45-54 % at 250-500 Hz in the choruses.
- **Basses** are keyswitched too (`rock.BASS_ARTICULATIONS`): `sustain`, **`staccato`** (the fretting hand lifting),
  `mute`. Write them where they sound (E1 = the low string): Growlybass samples sound an octave under their keys and
  the preset transposes them back.
- **Kits** are GM-mapped (36 kick, 38 snare, 37 side stick, 40 rimshot, 42 / 44 / 46 hats, 49 / 57 crash, 51 / 59 ride,
  53 bell, toms 50 48 45 43 41 - `rock.remap_keys` copies the Karoryfer toms onto 48 / 50). Velocity picks one of up to
  14 layers: ghosts 30-50, backbeat 100-127. Big Rusty is velocity-calibrated (`kits.velocity_map`,
  `sampled_drums.BIG_RUSTY_VELOCITY`): the snare rises smoothly from ghost to rimshot and the toms sit 1-2.5 dB over it
  at every velocity (before: snare layers 2-4 at one level, toms 5-8 dB over the snare). `tom_fill()`, `snare_roll()`,
  `crash()` work as written. The kit's chain: eq -> **`punch`** (a 25 ms-attack 3:1 compressor: the stick passes, the
  ring is held) -> the drum bus (**`crush`**: New York parallel compression 6:1 mixed in at 35 %, **`tape`**
  saturation, eq) + the room (the Voxengo drum room IR + **`room_crush`**: the room compressed 6:1 at 50 %, the big
  rock room between the hits).
- **Levels**: each role's balance sits in its last effect (`fx.trim.gain`), so `gain_db` and `gainDb` automation
  (loud-quiet dynamics: `t.automate('gainDb', per_section({verse: -4, chorus: 0}))`) start from 0 dB. Dry track levels
  on the demos: drums -20.5, bass -22, each rhythm guitar -23.5, lead -19.5, organ -26 LUFS. The rock_band master glues
  only above -12 dB, so a lighter verse stays lighter (demo: verse -9.7, chorus -8.5 LUFS).
- **Sends** (set, automate them): `room` (drums -5, guitars -13), `plate`, `echo` (the lead: `send.echo` throws),
  `drum_bus`. The bass is an SVT-style rig (`sampled_guitars.bass_rig`: the tube amp growls in the mids, the
  time-aligned DI carries the lows and the pick) and ducks 5 dB under the kick (a short duck; the kick eq leaves 150 Hz
  to the bass). Master: eq,
  2:1 glue, tape, width 1.12 with the lows mono below 150 Hz, limiter at -1.2 dBTP - set only when the song has no
  master chain yet (`rock.master_chain`: a second preset on the same song, or your own `s.master`, keeps the first;
  `b.info['master']` says 'set' / 'kept').
- **Sounds**: `sounds={'lead': ...}` swaps one (it keeps the role's chain - for a guitar role that chain is the amp,
  so pass a DI or clean source), `without=('keys',)` drops one, `ids={'gtr_l': 'rhythm_l'}` renames tracks. Missing
  optional packs fall back (kits: Big Rusty -> Unruly -> Red Zeppelin -> Forzee -> GeneralUser; organ, piano, basses
  likewise); the guitars need `freepats-fsbs-direct` / `karoryfer-emilyguitar` (ComposeError with the fetch command).
- Still yours: the riff, loud-quiet dynamics per section, fills, the solo's shape, the ending, the reverb throws.

## Hero sounds (the featured lead guitar)

For a solo that stands in front like on a record (Gilmour, Slash "November Rain", Gary Moore, Knopfler, the Baker
Street solo) use the hero guitars of `agentsound/patches/hero_guitar.py` instead of the band's `lead` role:
`layered/hero_guitar` (the singing overdriven lead: FSBS Strat DI -> sustainer -> Plexi lead channel -> Greenback
4x12, tape, microshift double, its own dotted-8th / quarter stereo echo, hall + plate), `layered/hero_guitar_heavy`
(hotter amp + a real amped lead multisample doubled under it: long held peaks keep singing) and
`sampled/hero_guitar_clean` (the Knopfler / clean Strat, polyphonic: double stops). The two driven ones are stacks of
velocity zones - harder picking = more gain, a brighter amp input and ~3 dB louder per zone, ~2 dB per 10 velocity
steps after the amp (the band lead: 0.2, the dynamics ear flagged it flat) - so play them through the module, which
writes the glides / vibrato onto every zone and keeps slurs inside one zone. The mix rules below come in one call
with the hero wrapper (docs/COMPOSE_API.md "Hero sounds"): `hero(s.track('lead', 'layered/hero_guitar'),
bed=[b.strings, b.pad], competitors=[b.piano], genre='rock')` (rock: no bed duck - carve and dips; throws on its own
echo) - instead of the hand-written sidechain / dip lines of the example:

```python
from agentsound.patches import hero_guitar as hero
b = bands.power_ballad(s, without=('lead',))                 # not sounds={'lead': ...}: that adds the band's amp
lead = s.track('lead', 'layered/hero_guitar')
hero.lead(lead, solo_line, prog, style='rock', section=solo, memory=gtr.Memory(), climax=True)   # guitarist.lead
hero.play(lead, art.legato(line).glide(140, where=art.leaps(3)), verse, vib={'depth': 26}, throws=True)
s.sidechain(b.strings, b.pad, b.piano, key=lead, depth=2.5, attack=10, hold=120, release=220)     # carve the bed
b.piano.add_fx(fx.eq({'peak2.freq': 1900, 'peak2.gain': -2.0}))                                   # presence dip
```

Mix rules: in the hero's sections the bed sits 3-5 dB under it (report `bed ... vs lead` per section), carved by the
sidechain and presence dips rather than by pushing the lead; velocities 55-120 with phrase arcs (touch() / the
guitarist). Validated on the power_ballad demo with an 8-bar solo over the chorus changes, against the Baker Street
guitar solo (3:29-4:03 of the official video, loudness-matched): old band lead vs hero - lead dynamics 0.0 dB
(flat_dynamics warn) -> 4.4 dB (1.9 dB per 10 velocity), bed vs lead in the solo -2.0 -> -3.9 dB, the lead's share of
the solo 14 -> 20 %, lead width 0 -> 12 %, the mix vs the reference at 0.7-1.4 kHz -2.0 -> -1.2 dB (mid-forward like
the record), the lead no longer the main source of the mix's surplus above 2.8 kHz (that is the cymbals and the
master's air shelf), 0 clicks.

## Sub-styles (pick one per song, write it in song.py)

| style | tempo | feel | signature |
|---|---|---|---|
| Classic / hard rock (70s) | 100–140 | straight 8ths, big room drums | blues-pentatonic riffs, I–bVII–IV, Hammond organ, guitar solo |
| Arena rock (80s) | 110–140 | 8ths, gated snare, big chorus | power chords, anthemic lead, keys pads |
| Alternative / grunge (90s) | 90–130 | loud–quiet–loud | clean arpeggios in verses, fuzz walls in choruses, drop D |
| Indie / garage rock | 120–170 | driving 8ths, open hats | jangly clean guitars, octave leads, tight small room |
| Punk / pop-punk | 160–200 | fast 8th downstrokes, double-time drums | power chords, short songs, no solos |
| Blues rock | 70–130 (shuffle) | swung 8ths | 12-bar form, call and response, bends |
| Surf / instrumental guitar rock | 140–180 | driving, tom-heavy | spring-reverb twang lead, tremolo picking, melody on the low strings |
| Post-rock | 70–140 | slow build | tremolo-picked melodies, delays, crescendo form, no vocals needed |
| Stoner / heavy | 60–110 | half-time, heavy | fuzz, drop tunings (C, D), sub-heavy riffs |
| Math / prog | varies | odd meters (7/8, 5/4) | tapping, clean tones, unison hits |

## Form

- **Verse / chorus** with a riff intro: intro riff (4–8 bars) – verse – (pre) – chorus – verse – chorus – solo /
  bridge – chorus – chorus – ending. Instrumental rock states the "vocal" melody on the lead in verse and chorus,
  and keeps the riff as the song's signature.
- **Loud–quiet–loud**: clean, sparse verses (arpeggios, bass and hats), a pre-chorus that swells, choruses with the
  full distorted wall. Dynamics are the drama (the chorus 3–5 LU louder).
- **Riff-based / blues**: the riff *is* the song: repeat it, move it to IV and V, answer it with the lead.
- **Post-rock crescendo form**: one theme repeated with growing layers over 3–6 minutes to one explosive climax.
- **The solo**: after the second chorus, 8–16 bars over the verse or chorus changes, building from a motif to its
  peak (higher register, faster notes, bends) and handing back to the chorus.
- **The ending**: a big final chord held with cymbal washes and drum fills ("rock ending"), or a cold stop on
  beat 1, or the riff alone.

## Harmony and riffs

- **Power chords** (root + fifth + octave: `chordify('power')`) in E, A, D, G (open-string keys); drop D for heavy
  riffs (D power chords on the low string).
- **Progressions**: I–IV–V, I–bVII–IV (mixolydian: "Sweet Child", "Hey Jude" coda), i–bVI–bVII (aeolian epic),
  i–bIII–bVII–IV, vi–IV–I–V (pop-rock), I–V–vi–IV, the 12-bar blues (I7 IV7 I7 I7 | IV7 IV7 I7 I7 | V7 IV7 I7 V7).
- **Riffs**: minor-pentatonic / blues-scale figures on the low strings, a pedal (open low E / D) alternating with
  moving notes, chromatic approach notes, rhythmic hits with the drums (stabs on the "and" of 4).
- **Colour**: sus2 / sus4 and add9 open voicings for alt / indie, major chords with a moving inner voice, octaves
  for lead melodies, fifths and fourths for heavier harmony (no thirds under distortion: they get muddy).

## Drums

- **Rock beat**: kick on 1 and 3 (plus the "and" of 3), snare on 2 and 4 (strong, rimshot in choruses), hats in
  8ths (open-ish in choruses, or ride), crash on section downbeats.
- **Variations**: half-time (snare on 3) for heavy bridges, four-on-the-floor for disco-rock, double-time punk
  (snare on every "and"), shuffle (swung 8ths, 0.62–0.66) for blues rock, floor-tom grooves for surf / tribal.
- **Fills**: 1 beat or 1 bar before a new section, 16ths around the toms high → low, ending on a crash + kick.
- **Feel**: humanize 4–8 ms and ±8 velocity, snare backbeat a few ms late in laid-back grooves, ghost notes on the
  snare in funk-rock, hat accents on the beats. Real drummers vary: change the pattern every 4–8 bars.

## Bass

- Locks with the kick: roots in 8ths (the rock bass), octaves in disco-rock, doubling the guitar riff an octave
  lower, walking passing tones into chord changes, sustained roots in the quiet verses.
- Register E1–E3 (4-string), picked for attack and definition, fingered for warmth; a touch of drive (saturator
  `tube`, drive 6–12) so it speaks on small speakers.
- Let the bassist play it: `bassist.arrange(prog, bpm=s.tempo, key=s.key, style='rock', part='verse', kick=beat,
  into=<next section's chord>, memory=mem, at=sec).place(b.bass, sec)` - roots locked to the kick (the verse doubles
  its rhythm, staccato), driving sustained 8ths in the chorus, approaches, a budgeted slide or fill into the next
  section (docs/COMPOSE_API.md "The bassist"; styles pop / funk / motown / disco / ballad for the other feels).

## Guitars

- **Rhythm wall**: two rhythm guitars playing the same riff, panned hard left / right (+-0.8...1.0), as two
  *performances*: `guitarist.double(part, (gtr_l, gtr_r), at)` (drifting timing, tuning drift, other takes and round
  robins) on two different guitars / amps (the band presets). An identical copy panned left and right is mono.
- **Palm-muted** riffs in verses (the riff player at verse energy: single notes, palm-muted), open ringing power chords
  + octave in choruses, accents with the snare, stops with the band (`guitarist.hits` on the drummer's cell).
- **Clean guitars**: arpeggiated chords (`arpeggiate('up', rate='1/8')`) in the quiet sections, chorus / delay /
  plate on them.
- **Lead**: the melody or solo in the middle of the stereo image, pentatonic / blues phrasing, bends (automate
  the instrument `pitchbend` by +2 semitones into a note), slides (`glide` on a mono / legato lead), vibrato (a
  pitch LFO at 5–6 Hz on long notes), double stops, octave melodies; a delay (1/4 or dotted 1/8) and a plate.
- **Tone in the engine**: DI guitars through `sampled_guitars.amp(kind)` (the tube amp + a cabinet IR, above);
  pre-amped sets (`freepats-fsbs-dist1` / `dist2`: sampled/dist_guitar, fuzz_guitar) need only EQ. Cabinet IRs (the
  `cab/*` patches; `amp(kind, cab=...)` mixes any voicing with any cab): `jester-emerald-ir-pack` (Marshall 1960AX
  Greenback 4x12), `jester-brutal-ir-pack` (V30 4x12), `kalthallen-cabs-free`, the `overdriven-*` 1x12 / 2x12 packs,
  `david-fau-casquel-guitar-irs`; FSBS direct (DI) guitars are made for this.

## Keys and lead instruments

- **Hammond organ**: `freepats-rock-organ`, `freepats-drawbar-organ`, GM `'Rock Organ'` / `'Tonewheel Organ'`; the
  Leslie is chorus (mode II) + a slow `tremolo`, sped up in the chorus; organ pads under guitars, stabs in
  classic rock, a distorted organ solo (saturator).
- **Piano**: 8th-note chords in pop-rock (`gm/grand_piano`, `salamander-grand`), honky-tonk for boogie
  (`freepats-old-piano-fb`).
- **Synths**: 80s arena pads and brass (`synthwave/juno_pad`, `synthwave/brass_stab`), a sync / saw lead for
  synth-rock.
- **Sax**: a tenor / baritone growl for bar-rock (`karoryfer-bear-sax`, `karoryfer-weresax`); the soft-rock / AOR
  hero sax solo ("Baker Street", Springsteen's Clarence Clemons) on `layered/hero_sax` - compressed, gritty,
  double-tracked, its own `bus/hero_plate`, echo throws (`articulation.throws`) and the band carved around it
  (`s.carve(..., key=sax)`): recipes/pop.md "The hero sax", `songs/lamplight-avenue`.

## Arrangement density and energy

| section | drums | bass | guitars | lead | loudness |
|---|---|---|---|---|---|
| intro | riff hits or none | riff | one guitar riff (or both) | – | mid |
| verse | kit, closed hats | roots 8ths | palm-muted or clean arpeggios | melody, low register | −3…−5 LU |
| pre-chorus | building, open hats | pedal | open chords, rising | rising line | −2 LU |
| chorus | full, crash, ride / open hats | driving 8ths | full wall L/R + octave line | melody high, doubled | loudest |
| solo | chorus groove | chorus | rhythm wall | solo builds | loud |
| bridge | half-time / breakdown | long notes | one guitar | sparse | −6 LU then build |

Frequency slots: kick 60–100 Hz body + 3–5 kHz beater, bass 50–250 Hz + 700 Hz–1 kHz growl, guitars 100 Hz–5 kHz
(the mids are theirs), snare 180–250 Hz body + 4–6 kHz crack, cymbals 6–16 kHz, lead 1–4 kHz in front.

## Sound table (packs in `assets/samples/`, see `python -m agentsound samples`)

SFZ packs load with the planned `inst.sfz('samples/<id>/<file>.sfz', articulation=...)`, SoundFonts with
`inst.sf2(preset, file=<absolute path>)` (build it from `agentsound.library.SAMPLES`), one-shot folders with
`inst.sampler(zones=[...], oneshot='on')`. The AVL kits and the SF2 kits use the GM drum map: play them with
`drums({'kick': ..., 'snare': ..., 'hat': ..., 'ride': ..., 'crash': ...})`.

| part | first choice | alternatives | license / notes |
|---|---|---|---|
| Drum kit | `avl-red-zeppelin/Red_Zeppelin_2023_repack.sfz` (Ludwig, 26" kick, big room: classic rock), `muldjordkit/MuldjordKit 20201018.sfz` (Tama, 2 kicks, 4 toms) | `avl-black-pearl/Black_Pearl_2023_repack.sfz` (Pearl rock kit), `big-rusty-drums/Programs/01-full.sfz` (80s kit, close + OH mics, CC0), `fiedler-mf-natural-drumset/mf-drumset-complete-ogg.sfz`, `karoryfer-gogodze-phu-vol-ii/Programs/Kit.sfz` (lo-fi to hi-fi mics), `hydrogen-forzee-stereo`, SF2 `muldjordkit-sf2`, `avl-red-zeppelin-sf2` ("Red_Zeppelin_4pc") | AVL: CC-BY-SA (credit Glen MacArthur); MuldjordKit: CC-BY (credit Lars Muldjord); Fiedler: CC-BY-NC-SA "music ok"; Forzee: GPL (music free); coming: `naked-drums`, `salamander-drumkit`, `karoryfer-unruly-drums`, DrumGizmo DRSKit |
| Snare / hats / cymbals | `karoryfer-frankensnare/Programs/01-frankensnare.sfz` (+ `07-14x65maple.sfz`, `09-14x8al.sfz` ...), `karoryfer-hat-with-the-phat/Programs/01-complete.sfz` | `sampleradar-drum-samples/Assorted Hits/Snares/`, `Kicks/`, `Cymbals/`, `sampleradar-hats-cymbals-gongs/Cymbals/Accoustic/`, `sampleradar-radio-ready-drums` (clean / crunch / wide / xtracomp kits) | SampleRadar: no redistribution |
| Bass | `karoryfer-growlybass/growlybass_dirty.sfz` or `_clean.sfz` (Squier Jazz, 5 RR, CC0) | `karoryfer-fashionbass/fashionbass.sfz` (palm mutes, muted strums), `karoryfer-pastabass/combo_platter.sfz` (Bass VI / baritone), `karoryfer-swagbass/swagbass.sfz`, `freepats-bass-yr-picked/PickedBassYR 20190930.sfz`, `fiedler-precision-e-bass`, GM `'Pick Bass'`; coming: `karoryfer-black-and-blue-basses` (picked solidbody) | all CC0 except Fiedler |
| Distorted guitar | `freepats-fsbs-dist2/EGuitarFSBS-dist2 bridge 20220911.sfz` (single notes: build power chords from 2–3 notes) | coming: `freepats-fsbs-dist1`, `freepats-fsbs-direct` (DI for amp + cab IR); `karoryfer-emilyguitar/emily_basic.sfz` + saturator; GM `'Distortion Guitar'`, `'Overdrive Guitar'` (sketches) | FreePats CC0 |
| Clean / crunch guitar | `karoryfer-emilyguitar/emily_clean.sfz` (Epiphone SG), `karoryfer-shinyguitar/Programs/electric_three.sfz` (archtop pickup) | `freepats-fsbs-jazz/EGuitarFSBS-jazz bridge 20260807.sfz`, coming `freepats-fsbs-clean`, `karoryfer-black-and-green-guitars` (DI hollowbodies); GM `'Clean Guitar'`, `'Jazz Guitar'` | |
| Acoustic guitar | `freepats-fss-steel-guitar/FSS-SteelStringGuitar-20200521.sfz`, `karoryfer-shinyguitar/Programs/acoustic_three.sfz` | GM `'Steel Guitar'`; nylon: `freepats-spanish-classical-guitar`, `fiedler-natural-concert-guitar` | FSS: GPL + FreePats exception (music free) |
| Organ | `freepats-rock-organ/RockOrganEmulation-20190715.sfz`, `freepats-drawbar-organ/DrawbarOrganEmulation-20190712.sfz` | `freepats-percussive-organ`, `karoryfer-caveman-cosmonaut/Programs/main.sfz` (70s/80s combo organ), GM `'Rock Organ'`, `'Tonewheel Organ'`, `synthwave/organ` | CC0 (setBfree renderings, not a real tonewheel) |
| Piano / keys | `salamander-grand/SalamanderGrandPianoV3.sfz` | `gm/grand_piano`, `upright-piano-kw`, `freepats-old-piano-fb`, `greg-sullivan-epianos/Wurlitzer EP200/Wurlitzer EP200.sfz` | Salamander / Greg Sullivan: CC-BY |
| Lead sax | `karoryfer-bear-sax/Programs/1-solo-mono.sfz` (baritone, growl), `karoryfer-weresax/Programs/Sax.sfz` (alto) | `mtg-solo-sax`, GM `'Tenor Sax'` | |
| Cab IRs (convolver) | `jester-emerald-ir-pack/Impulses/48kHz/` (6 Greenback IRs, e.g. `1_Nacho_Guacamole_48.wav`) | `jester-brutal-ir-pack/Impulses/48kHz/` (15 V30 IRs), `kalthallen-cabs-free/Kalthallen IRs/` (`001a-SM57-V30-4x12.wav` ...), `overdriven-uk-112-v30-tubepreamp2-v1-0/TubePreamp2/DYN-57/` ..., `david-fau-casquel-guitar-irs` | Jester Brutal CC0; Emerald free for commercial use; Kalthallen and Overdriven: free for music, no redistribution; David Fau Casquel: CC-BY |
| Rooms (convolver) | `voxengo-im-reverbs/Nice Drum Room.wav`, `Small Drum Room.wav` | `little-devil-224xl-04-room`, `-06-chamber`, `-12-cd-plate-b`, `-13-cd-plate-a` (true stereo .L/.R pairs; license unclear) | Voxengo: royalty-free, no resale / redistribution |

## Mix (profile `rock`; check report.json)

- **Drums**: kick 60–80 Hz body + 3–5 kHz click (`eq`), snare 200 Hz body + 5 kHz crack, compression 4:1 with a slow
  attack (15–30 ms) for punch, a drum bus (`bus/drums`) and parallel compression (`fx.compressor(mix=0.4)`) for
  weight; a short room (0.6–1.0 s, `type='room'`) at −10…−14 dB on the kit, a plate (1.2–1.6 s) on the snare.
- **Bass**: high-pass 35 Hz, compressor 4:1, a little drive, 700 Hz–1 kHz for definition; the kick owns 60 Hz,
  the bass 80–120 Hz (or the reverse: decide per song).
- **Guitars**: high-pass 80–100 Hz, low-pass 8–10 kHz, −2…−3 dB at 300–500 Hz if the low mids turn to mud, presence
  2–3 kHz; rhythm guitars hard left / right, 4–8 dB under the lead; clean guitars with chorus and a plate.
- **Lead**: centre, the loudest melodic element, plate + 1/4 or dotted-8th delay (−14…−10 dB), automate throws.
- **Master**: glue compressor 2:1 (slow attack, 1–3 dB), a touch of `tape`, limiter (ceiling −1) to −9…−7.5 LUFS.
  Rock is dense but must breathe: keep the PLR ≥ 6 dB (the `squashed` info fires under 5).

| measure | target (`rock`) |
|---|---|
| integrated loudness | −10…−7 LUFS (aim −8.5) |
| true peak / PLR | ≤ −1 dBTP / 6–8 dB (≥ 5) |
| loudness range | 3–8 LU (2.5–12 accepted): verses 3–5 LU under the choruses |
| balance | kick / bass punch at 60–100 Hz, less sub than pop (sub more than +4 is flagged), guitars and snare forward in the mids (scooped mids below −5 flagged), cymbal top without sizzle |
| width above 150 Hz | 30–60 % from the double-tracked guitars (25–100 accepted) |
| reverb / echo | drum room + snare plate + lead delay: reverb 9–20 LU under the mix, echo audible on the lead |

## Checklist

- Sub-style, tempo, key (guitar-friendly) and form chosen; the riff and the lead melody written first.
- Loud–quiet dynamics per section; fills and crashes into sections; a solo that builds; a real ending.
- Drums humanized with pattern variations; bass locked to the kick; rhythm guitars double-tracked left / right as
  two performances; clean parts in the quiet sections.
- Lead in the centre with plate and delay; organ / keys fill without masking the guitars.
- `ANALYSIS = {'profile': 'rock'}`; −10…−7 LUFS, true peak ≤ −1 dBTP, PLR ≥ 6; no balance / space warnings.
- Credits for CC-BY / BY-SA packs (AVL, MuldjordKit, Salamander, ...) in the song docstring and the delivery message.
