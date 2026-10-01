# Pop recipe: modern radio pop, instrumental

A hit without a singer: the lead instrument (synth, electric guitar, sax, piano, whistle-like lead) *is* the
voice, and everything else is built around it the way a pop production is built around a vocal. Big clean low
end, a hook in the first 10 seconds, a chorus that lifts, every section a little different, polished, wide and
bright but never harsh. References: The Weeknd *Blinding Lights*, Dua Lipa *Levitating* / *Don't Start Now*,
Harry Styles *As It Was*, Taylor Swift *1989*, Bruno Mars *24K Magic*, Coldplay, Robyn, Daft Punk *Get Lucky*,
K-pop production; instrumental pop: Kenny G / Dave Koz (sax), Jean-Michel Jarre, lo-fi covers.
Analysis profile: `pop`.

## Band presets (start here)

One call sets up a produced pop or funk band - sampled players, synths, percussion, sidechains, returns, a loud glued
master - balanced on a demo and tuned for the `pop` profile. Compose the parts, not the mix:

```python
from agentsound import *
from agentsound import bands

ANALYSIS = {'profile': 'pop'}                       # = b.analysis
b = bands.pop_band(s, keys='rhodes', lead='sax')    # bands.make('pop_band', s, without=('pluck',), ...)
b.drums.loop(drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'}), chorus)
b.perc.loop(drums({'clap': '....x.......x...', 'tamb': 'x.x.x.x.x.x.x.x.'}), chorus)
b.bass.loop(prog.bass('octave', rate='1/8', low='E1').articulate('staccato'), chorus)
print(b.describe())                                 # roles, buses and how to play them (b.notes)
```

| preset | roles | sounds | demo |
|---|---|---|---|
| `pop_band` (options `keys='rhodes'\|'wurli'\|'piano'`, `bass='electric'\|'synth'`, `lead='synth'\|'soft'\|'sax'\|'tenor'\|'guitar'\|'piano'`, `sub=True\|note\|False`) | drums, perc, bass, keys, pad, pluck, lead | SampleRadar Chart Kit with a sine sub thump under the kick tuned to the song's tonic (E1..D#2); Gimme-a-Hand claps (39), snaps (40), tambourine (54), maracas (70) on a wide perc track; a real electric bass (Growlybass, keyswitched `staccato` / `mute`) or `synthwave/moog_bass`; jRhodes3d / Wurlitzer EP200 / Salamander with tremolo + chorus; `synthwave/warm_pad` (sidechained 6 dB), `synthwave/arp_pluck` into the dotted-8th echo; the lead voice with plate + echo + bright 224XL hall | `songs/_bands/pop_band` (114 BPM F major: -10.6 LUFS, verse -10.1 / chorus -9.5, LRA 7.4, width 38 %, 0 warnings) |
| `funk_band` (`keys='clav'\|'wurli'\|'rhodes'`, `bass='finger'\|'round'\|'slap'`, `lead='tenor'\|'sax'\|'synth'\|'guitar'`) | drums, bass, keys, gtr, horns, lead | Orange Tree Jazz Funk kit (dry, 224XL ambience); Growlybass / Fashionbass (keyswitched) or the MF Precision slap bass (velocity >= 104 slaps); a clavinet through an envelope-driven band-pass (auto-wah: every note opens it) or Wurlitzer / Rhodes; the chicken-scratch FSBS single-coil DI (clean 1x12, compressed; `dead note` = real muted-string scratches); VPO trumpet + trombone sections spread L/R with `stab` / `accent` / `long` keyswitches; MTG tenor sax (legato) with a microshift | `songs/_bands/funk_band` (104 BPM E dorian: -10.8 LUFS, LRA 6.4, 0 warnings) |

- **Levels** sit in each role's last effect (`fx.trim.gain`): `gain_db` / `gainDb` automation start at 0 dB. Dry
  track levels on the demos: pop drums -19.5, perc -24, bass -20, keys -26.5, pad -27.5, pluck -27, lead -19; funk
  drums -21.5, bass -20, keys -24.5, gtr -25.5, horns -24, lead -20.5 LUFS. The pop_band master glues only above
  -12 dB, so a lighter verse stays lighter (the demo pulls bass -4 / keys -2 dB in the verse with `gainDb`).
- **Kick and bass**: the pop kit's short sine sub (0.3 s) gives the 40-60 Hz weight a sampled kick lacks (`sub=False`
  for the plain kit, `sub='G1'` for another pitch); the bass is high-passed at 45 Hz and owns 60-150 Hz (the kick
  gives way at 115 Hz); bass (6 dB), pad (6 dB) and keys (2 dB) duck under the kick; the funk bass ducks 10 dB (hold
  30 ms) - write the bass in the kick's gaps after "the one" and it breathes. Staccato bass thins the low end: keep
  the chorus bass sustained.
- **Articulations**: basses `staccato` / `mute`, the funk guitar `dead note` (real muted scratches) and `palm mute`, horns `stab`
  (default) / `accent` / `long` (`clip.articulate('long', ...)` for swells and pads). Horn voicings F#3-F5 (both
  sections sound there), 2-4 notes.
- **Sends**: pop `plate` (lead, perc, keys), `hall` (pad, keys, pluck), `echo` (pluck, lead: automate `send.echo`
  throws); funk `room` (short ambience), `plate`, `echo` (quarter note). Master: low-mid dip, 2:1 glue, 30 ips tape,
  width 1.35 (pop) / 1.15 (funk) with the lows mono below 120 Hz, limiter at -1.2 dBTP - only when the song has no
  master chain yet (a second preset keeps the first).
- **Sounds**: `sounds={role: ...}` keeps the role chain, `without=` drops roles, `ids=` renames tracks. Every pop_band
  sound falls back to the engine / GeneralUser when a pack is missing; funk_band needs `freepats-fsbs-direct` (or
  Emilyguitar) for its guitar. Licences to check before publishing: jRhodes3d CC-BY-NC, Lithalean clavinet unstated,
  SampleRadar / Orange Tree no redistribution of the samples (music is fine).

## Sub-styles (pick one per song, write it in song.py)

| style | tempo | groove | signature |
|---|---|---|---|
| Dance-pop / nu-disco | 112–124 | four-on-the-floor, offbeat open hats, 16th shaker | octave-disco bass, funky guitar 16ths, string stabs, sidechain pump |
| Synth-pop (80s revival) | 100–130 (or 170 as double-time) | straight 8ths, gated snare | Juno pads, arpeggios, big snare, bright lead (overlaps synthwave) |
| Electropop | 120–128 | electronic kit, claps | plucks, vocal-chop-style synth hooks, drops |
| Pop ballad | 60–80 | half-time, sparse kit from the 2nd verse | piano or guitar start, strings / pads grow, key change for the last chorus |
| Trap-pop / pop R&B | 70–85 half-time (140–170 hats) | 808 kick + sliding 808 bass, triplet hats, snare on 3 | minimal chords, dark pads, glides |
| Tropical / house-pop | 100–112 | syncopated kick, marimba / pluck hooks | dembow or house groove, airy pads |
| Funk-pop | 105–118 | tight 16ths, ghost notes | slap / finger bass, clavinet, horns stabs, rhythm guitar |
| Pop-rock | 120–150 | live kit, 8ths | double-tracked guitars, driving bass (see recipes/rock.md) |
| Indie / bedroom pop | 80–120 | soft kit, lo-fi | wobbly tape, warm keys, gentle lead |

## Song form (≈ 3:00–3:30)

| section | bars | job |
|---|---|---|
| intro | 4–8 | the hook or its fragment, filtered or on one instrument |
| verse 1 | 8–16 | groove + bass + one harmony instrument; the lead tells the story in the middle register |
| pre-chorus | 4–8 | lift: rising line, subdominant chords, build (snare roll, riser, filter opening, kick drops out) |
| chorus | 8–16 | the hook: highest energy, widest image, lead up an octave or doubled, every layer in |
| post-chorus | 4–8 | instrumental hook / "drop" (the synth hook in dance-pop), keeps the energy |
| verse 2 | 8–16 | same chords, new texture (added counter-line, busier drums) |
| pre-chorus + chorus 2 | | shorter build, bigger chorus (extra layer, harmony line) |
| bridge | 8 | contrast: new chords (IV–V–vi, a borrowed bVI), half-time, breakdown to one instrument |
| final chorus | 8–16 | the biggest: key change up 1–2 semitones, or a drop to near silence then full, ad-lib lead |
| outro | 4–8 | hook tag, fade or button ending |

- The first chorus lands by ~0:50; the hook is heard in the intro; the song ends before the listener wants it to.
- **Contrast by section**: verse lead in the low-middle register with short phrases, chorus high and long notes;
  verse rhythm syncopated, chorus on the beat (or the reverse). Energy (loudness) verse → chorus +2…+4 LU.
- **Every repeat changes something**: drum pattern, an added counter-melody, a filter state, an octave, the
  harmony line, a percussion layer, a stop.
- **Transitions**: fills + crash, riser into the chorus, reverse cymbal, a one-beat (or one-bar) silence before
  the chorus downbeat, downlifter after it, snare roll in the pre.

## Harmony

- **Four-chord loops** carry most pop: I–V–vi–IV (axis), vi–IV–I–V (sad axis), I–vi–IV–V (50s), IV–V–iii–vi
  (royal road, J/K-pop), i–VI–III–VII (minor anthem), i–iv–VI–V, I–IV–vi–V.
- **Lifts**: the pre-chorus on IV or ii (away from the tonic), the chorus arriving on I or vi; a borrowed iv
  (minor subdominant) before the last chorus; bVII–I (mixolydian) for a rock-pop lift; the truck-driver key change
  (+1/+2 semitones) for the final chorus.
- **Colour**: add9, sus2/sus4, maj7 on IV and I (bittersweet), m7/m9 in funk-pop and R&B, pedal bass under
  changing chords in the pre-chorus.
- **Voicing**: pads and keys in the C3–C5 area (open voicings, `voice_lead`), no thirds below C3; the bass plays
  roots (slash chords for walking bass-lines: I–V/7–vi).
- **Chord rhythm**: push chords a 16th or 8th before the bar (anticipation) in upbeat pop; hold whole-bar chords
  in ballads.

## Melody and the lead instrument ("the vocal")

- **The hook**: 2–4 bars, simple rhythm, a memorable interval leap, repeated 2–4 times in the chorus with a
  varied ending (question / answer: `m + m.resolve()`); the title-line rhythm pattern.
- **Phrasing like a singer**: phrases of 1–2 bars with breaths (rests) between them, pickups into the downbeat,
  syncopation (start phrases on the "and"), repeated notes with rhythmic variation, long notes at phrase ends
  with vibrato (a delayed pitch LFO) and a small fall or scoop.
- **Range**: verse C4–A4, chorus up to C5–E5 (instrument-dependent: sax Bb3–F5, guitar G3–E5, synth anywhere but
  stay in the "vocal" range for melody); double the chorus hook an octave up or in thirds
  (`hook_clip.harmonize('3rd', key=s.key)`).
- **Leads that work**: synth lead (`synthwave/pulse_lead`, `synthwave/soft_lead`, `synthwave/supersaw_lead`, a
  `va` saw with glide + vibrato), electric guitar (`karoryfer-emilyguitar` with slides and vibrato, GM `'Clean
  Guitar'`), alto / tenor sax (`karoryfer-weresax`, `mtg-solo-sax`), piano melody (octaves), whistle / flute-like
  lead (`inst.sf2('Whistle')`, `'Pan Flute'`).
- **The hero sax** (late-70s / 80s sax pop: "Baker Street", Sanborn, Kenny G, Dave Koz; recipes/HUMAN_FEEDBACK.md
  2026-09-30): `hero(s.track('sax', 'layered/hero_sax'), bed=[strings, pad, piano, keys], genre='pop')` - the hero
  wrapper (docs/COMPOSE_API.md "Hero sounds") does all of the following in one logged call; by hand:
  `layered/hero_sax` (close-miked compressed gritty alto, double-tracked, `agentsound/patches/hero.py`) with its own `s.bus('hero_plate', 'bus/hero_plate')`, `articulation.throws(sax, line, at, bus=echo)` on the phrase
  ends, `s.carve(strings, pad, piano, keys, key=sax, depth=4)` so the bed's 1-4 kHz steps aside, the sax ridden 1-2 dB
  over the whole band in the hook sections (bed 6-8 dB under it). Worked example: `songs/lamplight-avenue`. The sax's
  within-note breath (swells, short pushes on held notes) goes on the hero's `air` stage (`heroes.air`), after its
  heavy compression.
- **Other heroes** (the same wrapper): a trumpet solo `hero(s.track('lead', 'sampled/solo_trumpet'), family='brass',
  genre='pop', bed=[pad], competitors=[keys, pluck])` (validated on the pop_band demo: the lead's pre-master peak
  +1.0 -> -4.4 dBFS, rhythm -4.0 -> -2.9 dB under it in the chorus, reverb -12.3 -> -10.2 LU, echo -26 -> -21 LU via
  the throws, note dynamics 12 dB, no new mixer finding), `family='woodwind'` (flute), `'voice'` (an "aah" topline),
  `'organ'`, `'strings'` (a violin).
- **Counter-melodies and ear candy**: a second line answering the lead in its gaps (bells, glockenspiel, plucks,
  guitar licks), "vocal chop" style plucks (short syncopated synth notes on chord tones).

### Hero sounds: the piano

When the piano *is* the song (the pop / power ballad that opens on piano - Elton John, Billy Joel, Adele "Someone
Like You" - or a driving piano hook like Coldplay "Clocks"), make it a hero: `hero(s.track('piano',
'sampled/hero_piano'), bed=[strings, pad], genre='pop')` (or `family='piano_pop'` / `'piano_strings'`; the mix rules
below in one call, docs/COMPOSE_API.md "Hero sounds"). The patches (`agentsound/patches/hero_piano.py`): `sampled/hero_piano` (ballad: softened hammers, bright but not glassy, even,
a lush plate), `sampled/hero_piano_pop` (brighter, tighter, high-passed for the bassist: 8th-note ostinatos and
pop hooks), `layered/hero_piano_strings` (the ballad hero with a string section swelling in for the last chorus).
All three are key-split stacks of the Salamander: below C4 the recorded wide stereo, from C4 up a narrowed,
re-centred melody layer - a big image with a solid centre (a melody correlation ~0.55 instead of the plain grand's
phasey -0.3). Both hands go on the hero track (`pianist.arrange(..., style='ballad')` with pop devices for the right
hand, broken chords / 8th pulses for the left). Mix rules: the bed 3-5 dB under the hero in its sections -
`hero_piano.carve(s, hero, strings, pad, ...)` ducks the bed 2.5 dB under the piano and dips it 2 dB at 2.5 kHz;
the hero fader then sits around -4 dB (power_ballad) / -2 dB (pop_band); echo throws (`send.echo`) on phrase ends;
the left hand above E2 when a bassist plays. The chain costs ~1 dB of note-to-note contrast: accents 20-30
velocity apart. Measured in power_ballad with the piano as the lead: the bed 4.6 dB under it in the chorus (the
preset piano 1.6), 36 % of the chorus's 1-5 kHz band (18 %), crest 16.6 dB (19.0), no masking warning.

## Rhythm and drums

- **Four-on-the-floor**: kick on every beat, clap/snare on 2 and 4, open hat on the offbeat 8ths, closed hat or
  shaker 16ths; kick tuned to the key (41–55 Hz fundamentals), 8 bars without the kick in the pre-chorus.
- **Half-time / trap-pop**: kick on 1 and the "and" of 2, snare on 3, hats in 16ths with 32nd/triplet rolls, an
  808 bass that glides (`glide`, legato notes) and doubles the kick.
- **Pop-rock / ballad**: live kit, snare on 2 and 4, hats 8ths, crash on section downbeats, tom fills.
- **Groove**: tight grid for electronic pop (`groove('tight')`), 8th/16th swing 0.52–0.56 for funk-pop and R&B,
  hats velocity-shaped (`vel_pattern`), ghost notes on the snare in funk-pop.
- **Percussion layers**: shaker 16ths, tambourine on 2 and 4 in the chorus, claps layered with the snare, a
  conga / bongo pattern in tropical pop.

## Instruments and roles

- **Bass**: sub + mid. Synth pop: a sine/triangle sub layer (`synthwave/sub_bass`) plus a filtered saw or pluck
  for definition (`synthwave/pluck_bass`, `synthwave/moog_bass`); dance-pop: octave disco lines; funk-pop: finger /
  slap bass (`karoryfer-growlybass`, `karoryfer-swagbass`, `fiedler-precision-e-bass`); ballad: long roots. Mono,
  sidechained to the kick in dance-pop.
- **Keys**: grand piano (`gm/grand_piano`, `salamander-grand`), e-pianos (`greg-sullivan-epianos` Wurlitzer
  EP200 / CP80, `jrhodes3d`, DX7 `synthwave/epiano`), organ stabs, clavinet in funk-pop.
- **Guitars**: clean 16th-note funk chords (`karoryfer-emilyguitar`, `karoryfer-shinyguitar` electric, FSBS clean
  when installed), acoustic strums (`freepats-fss-steel-guitar`, strummed with `clip.strum`), muted plucks.
- **Pads and strings**: `synthwave/juno_pad`, `synthwave/warm_pad`, `gm/strings`, SSO strings (see
  recipes/classical.md) for ballads; string stabs in disco.
- **Brass**: `gm/brass_section` stabs, synth brass (`inst.sf2('Synth Brass 1')`, DX7 `BRASS 1`).
- **FX**: risers (`synthwave/noise_riser`), impacts (`synthwave/impact`), downlifters (`synthwave/downlifter`),
  reverse swells, one-shots from `sampleradar-stabs`.

## Arrangement density

| section | drums | bass | harmony | lead | extras |
|---|---|---|---|---|---|
| intro | none / filtered | none | 1 instrument (filtered) | hook fragment | riser |
| verse | kick + hats, snare light | yes | 1–2 instruments | low register | 1 counter-line |
| pre-chorus | building, snare roll | pedal / pulse | + pad, filter opening | rising | riser, kick drop |
| chorus | full + crash + claps + tambourine | full, sidechained | all layers, wide | high, doubled | ear candy |
| bridge | half-time / off | long notes | new chords, sparse | new melody or solo | |

Frequency slots: kick 45–60 Hz and 3–5 kHz click, bass 50–150 Hz, keys/guitars 200 Hz–3 kHz (thinned with a
high-pass at 150–250 Hz), lead 1–4 kHz presence, hats and air 8–16 kHz. Two parts in the same slot at the same
time: move one (octave, register, rhythm) before reaching for EQ.

## Sound table (packs in `assets/samples/`, see `python -m agentsound samples`)

SFZ packs load with the planned `inst.sfz('samples/<id>/<file>.sfz', articulation=...)`, SoundFonts with
`inst.sf2(preset, file=<absolute path>)` (e.g. `library.SAMPLES.joinpath('freepats-fingerbass-yr-sf2',
'FingerBassYR 20190930.sf2').as_posix()`), one-shot folders with `inst.sampler(zones=[...], oneshot='on')`
(names that are not GM drum names or notes need explicit zones):

```python
KIT = 'samples/sampleradar-80s-pop-drums/Drum Kits/Kit A'       # 80PD_KitA-Kick01.wav, -Snare01, -Clap, -ClHat, -OpHat ...
kit = s.track('drums', inst.sampler(zones=[
    {'file': f'{KIT}/80PD_KitA-Kick01.wav', 'root': 36, 'lo': 36, 'hi': 36},
    {'file': f'{KIT}/80PD_KitA-Snare01.wav', 'root': 38, 'lo': 38, 'hi': 38},
    {'file': f'{KIT}/80PD_KitA-Clap.wav', 'root': 39, 'lo': 39, 'hi': 39},
    {'file': f'{KIT}/80PD_KitA-ClHat.wav', 'root': 42, 'lo': 42, 'hi': 42, 'choke': 1},
    {'file': f'{KIT}/80PD_KitA-OpHat.wav', 'root': 46, 'lo': 46, 'hi': 46, 'choke': 1}], oneshot='on'))
kit.loop(drums({'kick': 'x...x...x...x...', 'clap': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '..x...x...x...x.'}), chorus)
```

| part | first choice | alternatives | license / notes |
|---|---|---|---|
| Electronic drums | engine `inst.drums(kit='modern')`, `synthwave/drums_909`, `synthwave/drums_linn` | `sampleradar-essential-drumkit` (`Chart Kit/`, `Main Room Kit/`, `TR 909 Kit/`, `TR 808 Kit/`, `DX_DMX Kit/` one-shots), `sampleradar-80s-pop-drums/Drum Kits/Kit A–D` + `Gated Snares/`, Hyperreal machines (`hyperreal-tr909`, `-linndrum`, `-tr707` ...) | SampleRadar: royalty-free, no redistribution; Hyperreal: license unclear (music use at your own risk) |
| Live / pop-rock kit | `big-rusty-drums/Programs/01-full.sfz` (80s kit, sticks, CC0), `muldjordkit/MuldjordKit 20201018.sfz` (CC-BY: credit Lars Muldjord) | `avl-black-pearl/Black_Pearl_2023_repack.sfz`, `fiedler-mf-natural-drumset/mf-drumset-complete-ogg.sfz` (CC-BY-NC-SA "music ok": music may be sold, samples not), `muldjordkit-sf2`, `avl-black-pearl-sf2` | AVL: CC-BY-SA (credit Glen MacArthur) |
| Snares / hats / cymbals | `karoryfer-frankensnare/Programs/01-frankensnare.sfz` (+ single snares `06-14x5maple.sfz` ...), `karoryfer-hat-with-the-phat/Programs/02-basic.sfz` | `sampleradar-hats-cymbals-gongs/Hats/Accoustic/`, `Cymbals/Accoustic/`, `sampleradar-drum-samples/Assorted Hits/` | |
| Claps / percussion | `hydrogen-gimme-a-hand` (claps, GPL: music is not a derivative), `freepats-world-percussion/WorldPercussion 20200905.sfz` (shakers, tambourine, congas, cajon; CC0) | `avl-buskmans-holiday/Buskmans_Holiday.sfz`, `karoryfer-gogodze-phu-vol-i` (cajon), Ethan Winer `tambourine.sf2` | |
| Synth bass | `synthwave/sub_bass` + `synthwave/pluck_bass` / `moog_bass` / `octave_bass` | `inst.va(...)` sine / saw, DX7 `synthwave/dx_bass` | |
| Electric bass | `karoryfer-growlybass/growlybass_clean.sfz` (Jazz bass, CC0), `karoryfer-fashionbass/fashionbass_clean.sfz` | `karoryfer-swagbass/swagbass_clean.sfz` (slap / muted), `freepats-fingerbass-yr/FingerBassYR 20190930.sfz`, `fiedler-precision-e-bass/mf-precission-e-bass-fingered-pop-slap-slide-fretnoise.sfz`, GM `'Finger Bass'`, `'Slap Bass 1'` | |
| Piano | `gm/grand_piano` (opened-up GS grand), `salamander-grand/SalamanderGrandPianoV3.sfz` (CC-BY: Alexander Holm) | `upright-piano-kw/UprightPianoKW-20220221.sfz` (CC0, indie / lo-fi), `freepats-old-piano-fb/PianoFB 20200401.sfz` (honky-tonk), `splendid-grand-piano` | |
| E-pianos / keys | `greg-sullivan-epianos/Wurlitzer EP200/Wurlitzer EP200.sfz`, `CP80/CP80.sfz`, `Pianet T/Pianet T.sfz` (CC-BY: Greg Sullivan) | `jrhodes3d/jRhodes3d-st.sfz` (Rhodes Mk I, CC-BY-NC: music fine, samples not), DX7 `synthwave/epiano`, `lithalean-wurlitzer`, `lithalean-clavinet` (license unclear: avoid for releases), GM `'Tine Electric Piano'`, `'Clavinet'` | |
| Organ | `freepats-drawbar-organ/DrawbarOrganEmulation-20190712.sfz`, `freepats-percussive-organ/...` (CC0) | GM `'Tonewheel Organ'`, `synthwave/organ` | |
| Guitars | `karoryfer-emilyguitar/emily_clean.sfz` (SG, flatwounds; `emily_chords.sfz` for strums), `karoryfer-shinyguitar/Programs/electric_three.sfz` / `acoustic_three.sfz` | `freepats-fsbs-jazz` (clean jazz tone), FSBS clean (`freepats-fsbs-clean`, coming), `freepats-fss-steel-guitar/FSS-SteelStringGuitar-20200521.sfz` (acoustic), `freepats-spanish-classical-guitar`, `fiedler-natural-concert-guitar` (nylon), GM `'Clean Guitar'`, `'Muted Guitar'`, `gm/nylon_guitar` | FSS: GPL with FreePats exception (music free) |
| Pads / synths | `synthwave/juno_pad`, `warm_pad`, `dream_pad`, `arp_pluck`, `poly_stab`, `jupiter_strings` | GM `'Warm Pad'`, `'Polysynth'`, `'Halo Pad'`, `karoryfer-caveman-cosmonaut/Programs/main.sfz` (80s combo organ / strings) | |
| Strings / brass | `gm/strings`, `gm/brass_section`, SSO sections (recipes/classical.md) | `sampleradar-stabs/Misc Stabs/` (horn, string, orchestra hits), `fairlight-cmi-library-1-3` (ORCH5 hit etc., license unclear) | |
| Sax lead | `layered/hero_sax` (the hero alto, see "The hero sax"), `karoryfer-weresax/Programs/Sax.sfz` (alto, CC0) | `mtg-solo-sax/MTG Solo Saxophones/MTG Alto Sax.sfz`, `MTG Tenor Sax.sfz` (CC-BY: MTG / UPF), `freepats-tenor-sax/TenorSaxophone-20200717.sfz` (CC0), GM `'Alto Sax'` | |
| Vocal-like | `gm/choir_aahs`, GM `'Voice Oohs'`, `'Synth Voice'` | SSO `Chorus - Notation/Mixed Chorus.sfz` | |

## Mix (profile `pop`; check report.json)

- **Centre**: kick, snare/clap, bass and the lead, all mono-compatible; the lead the loudest element in the
  choruses (like a vocal: 3–6 dB over the backing, a compressor 3:1 for steady level, de-harsh 3–5 kHz if needed).
- **Low end**: kick and bass own 40–120 Hz: tune the kick to the key, sidechain the bass (and pads) to the kick
  in dance-pop (`s.sidechain(bass, pad, key=kit, pitches='kick', depth=8)`, 6–10 dB), high-pass everything else at
  100–200 Hz, `width` with `monobass` 120 on the master.
- **Clean low mids**: cut 2–3 dB at 250–450 Hz on pads, keys and guitars (the `pop` profile flags low mids above
  +3 dB); leave the warmth in the bass.
- **Brightness without harshness**: air shelves (+1…+2 dB at 10–12 kHz) or `exciter` on the lead / master; tame
  2.5–5 kHz (presence above +3 dB is flagged). Hats and shakers sit 12–18 dB under the lead.
- **Width**: pads / keys / double-tracked guitars left-right, chorus on pads, stereo delays on the lead, a hall on
  the pads; keep the width above 150 Hz 40–70 % (`narrow_mix` below 35 %).
- **Space**: a plate (1.2–1.8 s, predelay 20–30 ms) on the lead and snare, a hall (2–2.5 s) on pads / strings,
  a dotted-8th or 1/4 echo on the lead (throws on phrase ends); returns high-passed at 200–300 Hz. Reverb 7–16 LU
  under the mix.
- **Glue**: a drum bus (`bus/drums`), a music bus (`bus/music`), then the master: gentle EQ, glue compressor 2:1,
  `width` 1.05–1.1 with `monobass`, limiter (ceiling −1) driven to −10…−8.5 LUFS.

| measure | target (`pop`) |
|---|---|
| integrated loudness | −11…−8 LUFS (aim −9.5; streaming turns louder masters down) |
| true peak / PLR | ≤ −1 dBTP / 7–9 dB (≥ 6) |
| loudness range | 4–8 LU (3–12 accepted): verse 2–4 LU under the chorus |
| balance | sub strong (kick + bass), low mids clean, bright controlled top |
| width above 150 Hz | 40–70 % (35–100 accepted) |
| reverb / echo | reverb 7–16 LU under the mix, echo audible in the lead's gaps |

## Checklist

- Sub-style, tempo, key and form chosen; hook written first and placed in the intro and every chorus.
- Four-chord loop with a lifting pre-chorus and a contrasting bridge; last chorus bigger (key change or layers).
- Lead phrased like a singer (breaths, pickups, syncopation, vibrato on long notes), chorus higher than the verse.
- Groove per section, fills and transitions into every chorus, one-beat drop before a big chorus.
- Kick and bass tuned and separated; low mids clean; lead on top; wide pads; plate + hall + echo.
- `ANALYSIS = {'profile': 'pop'}`; −11…−8 LUFS, true peak ≤ −1 dBTP, LRA 4–8 LU; no balance / space warnings.
- Credits for CC-BY / BY-SA packs in the song docstring and the delivery message.
