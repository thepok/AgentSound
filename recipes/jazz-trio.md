# Jazz trio recipe: New York bar jazz (piano, upright bass, brushes)

Late night in a small Manhattan club: a grand piano, an upright bass and a drummer on brushes, playing
standards-style tunes for a room of fifty people. Warm, intimate, swinging, never loud. References: Bill Evans
Trio at the Village Vanguard (1961), Red Garland, Wynton Kelly, Tommy Flanagan, Ahmad Jamal, Hank Jones;
modern: Brad Mehldau, Bill Charlap. For pianist-level detail (voice leading, enclosures, articulation, pedal)
read `recipes/jazz-piano.md` too.

The music is a *performance*: three players listening to each other. Everything below serves that illusion.

## Tempo, feel and styles (pick one per tune, write it in song.py)

| style | tempo | feel | bass | drums |
|---|---|---|---|---|
| Ballad | 56–76 | very laid back, rubato intro | two-feel, long notes | brush sweeps, almost no kick |
| Medium swing (the bar standard) | 120–160 | relaxed swing, 2 and 4 | walking quarters | brush sweep + taps on 2/4 |
| Up-tempo | 180–240 | tight, driving | fast walking | brush "stirring", fewer accents |
| Jazz waltz | 140–180 (3/4) | lilting | dotted-half + walking | sweep in 3 |
| Bossa / latin | 120–140 | straight 8ths | root-fifth dotted rhythm | cross-stick + brush |

**Swing is not one number.** Swing ratio falls with tempo: ballads ~0.64–0.67 (triplet), medium ~0.60–0.62,
up-tempo ~0.55. Timing layers: bass on (or a hair ahead of) the beat, brushes on the beat, piano right hand
10–25 ms behind ("laid back"), comping left hand less behind. Accents on 2 and 4 in drums (hi-hat foot) and a
slightly heavier 2 and 4 in the walking bass. Humanize velocities; keep timing jitter small (2–6 ms): the feel
comes from the *systematic* offsets and the swing ratio, not from randomness.

**Toolkit** (`from agentsound import jazz`, reference: docs/COMPOSE_API.md "Jazz", example: `songs/_demo_jazz`):
write every part on the straight grid and let the feel swing it. `jazz.band(s, sax=True)` sets each track's
groove from `jazz.Feel(s.tempo)`: `swing_ratio(bpm)` (0.66 ballad, 0.61 at 140, 0.555 at 220) and
`layback_ms(part, bpm)` (piano right hand +22..+10 ms, comping +10..+5, bass -2..-5, brushes 0, sax +35..+12,
ballad..up tempo); `jazz_groove(part, bpm)` does it for any track, `feel.apply(clip, part)` bakes it into a clip.
`phrase_dynamics(clip)` shapes a line phrase by phrase, `backbeat(clip)` accents 2 and 4.

## Form of a performance (≈ 3–5 min)

Tunes are 32-bar AABA or ABAC forms (8-bar phrases), or a 12-bar blues. One pass = one *chorus*.

1. **Intro** (4–8 bars): piano alone or with bass: a turnaround (iii–VI–ii–V), the last 8 bars of the tune, or a
   pedal-point vamp. Ballads: rubato piano intro.
2. **Head** (1 chorus): the melody in the right hand (C4–C6), sparse comping, bass in two-feel for the first A
   sections, walking from the bridge or the second chorus; brushes sweep.
3. **Piano solo** (2–3 choruses): develop a motif, longer lines, build intensity chorus by chorus (register,
   density, left hand more active); bass walks; brushes add taps and fills at phrase ends.
4. **Bass solo** (1 chorus, optional): piano comps very sparsely, drums almost only hi-hat on 2/4.
5. **Trading fours** (optional, 1 chorus): 4 bars piano, 4 bars brush solo.
6. **Head out** (1 chorus), then **ending**: tag the last 4 bars 2–3 times (iii–VI–ii–V vamp), a ritardando,
   and a final chord with colour (maj9, 6/9, maj7#11) left ringing — bass on the root, a soft cymbal/brush swell.

Every chorus must differ: dynamics, register, density, bass feel (two → four), drum texture.

## Harmony

- **ii–V–I** is the grammar. Major: `ii7 V7 Imaj7` (Dm9 G13 Cmaj9). Minor: `iiø7 V7b9 i6/im(maj7)`
  (Bø7 E7b9 Am6). Chain them through keys (tonicize: every chord can be preceded by its own ii–V).
- **Turnarounds**: `I vi ii V`, `iii VI7 ii V` (Em7 A7 Dm7 G7), with tritone subs `I bIII7 bVI7 bII7`,
  `I #Idim7 ii #IIdim7 iii` (diminished passing chords), backdoor `iv7 bVII7 I`.
- **Blues** (12 bars, jazz version): `I7 | IV7 | I7 | v7 I7 | IV7 | #IVdim7 | I7 | VI7 | ii7 | V7 | I7 VI7 | ii7 V7`.
- **Extensions by function**: tonic major `maj7, 6, 6/9, maj9, maj7#11`; minor tonic `m6, m(maj7), m9`;
  ii `m9, m11`; dominant `9, 13, 7sus4` (natural) or `7b9, 7#9, 7b13, 7alt` (altered, especially resolving to
  minor); half-diminished `m7b5 (ø)`, `ø9`.
- **Reharmonise the head's second A** (tritone sub, a secondary dominant, a sus chord) so repeats are fresh.
- Always check the actual pitches of a voicing against its label (see jazz-piano.md).

## Piano voicings and comping

- **With a bassist the piano omits roots.** Left hand (C3–C5 zone, centre around middle C):
  - *Rootless A/B voicings* (Bill Evans): A = 3-5-7-9, B = 7-9-3-5 (with 13 instead of 5 on dominants).
    Alternate A/B through ii–V–I so voices move by step (guide tones 3 → 7 → 3 descend by half steps).
  - *Shells* (3+7, or 7+3) for fast tempos and behind a busy right hand.
  - *Quartal* (stacked 4ths, "So What" voicing) for modal colour.
- Right hand melody or solo line in C4–C6; for block-chord moments harmonise the melody in *drop-2* or
  "locked hands" (melody doubled an octave below with a 4-note chord between).
- **Never a bare single-note piano lead** (HUMAN_FEEDBACK 2026-09-30: "als würde ein Kind Taste für Taste
  drücken"). Play every head and solo through the pianist: `arr = pianist.arrange(touched_melody, prog, bpm=s.tempo,
  key=s.key, style='straight' | 'ballad' | 'bar' | 'lush' | 'sparse', density=0.4-0.9, lh='guide' | 'rootless' |
  'shell' | 'tenths' | 'stride' | 'pedal', seed=...)` (= `jazz.pianist`) -> `b.piano.play(arr.rh, sec)`,
  `b.comp.play(arr.lh, sec)` (the left hand IS the comping: drop the separate `jazz.comp` there),
  `b.piano.automate('instrument.pedal', arr.pedal(prog, sec))`. It harmonizes phrase by phrase, ornaments long notes,
  fills the gaps and prints what it did (`arr.summary()`, `arr.moves`). Set pieces by name: `pianist.trill`,
  `tremolo`, `mordent`, `inverted_mordent`, `turn`, `crush`, `blues_crush`, `slip_note`, `repeated`, `roll`, `sweep`,
  `gliss`, `run`, `chromatic_run`, `pentatonic_run`, `octave_run`, `fourths`, `shake`, `alternating_hands` (intro
  flourishes, a gliss into the head out, the final shake). Example: songs/perry-street-rain.
- **Comping rhythm**: short, conversational, not on every beat. Classic cells: Charleston (1 and the "and" of 2),
  anticipation on the "and" of 4 into the next bar, a held chord on beat 1 of a new section, silence for a bar.
  Comp lighter when the right hand is busy; answer the melody's rests.
- **Solo lines**: 8th-note lines swung, starting off the downbeat; target chord tones on strong beats and
  approach them chromatically or with enclosures (upper neighbour, lower neighbour, target); bebop scales
  (dominant with added major 7th) keep chord tones on the beat; mix long lines with short motifs and space;
  develop one idea per 8 bars; blue notes (b3, b5) over blues; octave doubling for the climax chorus.
  `jazz.solo_line(prog, key=s.key, density=, intensity=, motif=head_opening, seed=chorus)` writes such a line
  (phrases off the beat, chord tones on the beats, enclosures, triplet turns, space) as a starting point: build
  2-3 choruses with rising density / intensity / register, keep what works, hand-edit the rest.
- **Pedal**: ballads use sustain pedal to connect chords, cleared at each chord change; medium swing uses
  little pedal. Keep comping chords genuinely short.
- **Toolkit**: `jazz.jazz_voicings(chords, 'rootless')` voice-leads A/B forms (guide tones by step, b9/b13 on a
  dominant resolving to minor) - or `rootless(ch, 'A')`, `shell(ch, '37')`, `quartal(ch)`, `so_what(ch)`,
  `upper_structure('G7alt')`, `block(ch, melody, 'locked')`; `check_voicing(ch, pitches)` lists what doesn't
  match the label, `mud(pitches)` the low-interval mud. `jazz.comp(prog, style='charleston' | 'swing' | 'garland'
  | 'ballad' | 'sparse' | 'bossa' | 'waltz', density=, intensity=, answer=melody)` comps per bar with varied cells,
  anticipations and answers in the melody's rests; `jazz.block_chords(melody, prog, 'locked')` for a shout chorus;
  `jazz.paraphrase(melody, seed=chorus)` loosens a head.

## Bass (upright, E1–G3, solos up to C4)

- **Two-feel**: half notes, root and fifth (or approach), for heads and ballads.
- **Walking**: quarter notes; root on beat 1 of a chord, chord or scale tones on 2–3, a chromatic or scale
  approach to the next root on 4; occasional skip notes (a swung triplet ghost before a beat), repeated notes,
  octave jumps. Contour like a melody, not a zigzag.
- Pedal point (a held root or dominant) under intros and endings; the bass solo is melodic, upper register, sparse.
- Articulation: notes slightly shorter than full value except in ballads; accents on 2 and 4 are subtle.
- **Toolkit**: `jazz.walking_bass(prog, key=s.key, feel='four' | 'two', approach='mixed', skip=0.1, octave=0.05,
  repeat=0.05, pedal=[(0, 16, 'F2')], seed=...)` - roots on 1, chord tones on 3, approaches on 4, skip notes
  (`skip_grid='triplet'` for skip-note triplets), E1..G3; a new seed per chorus.
- **Dynamics** (the dynamics ear judges the bass under the jazz profile: 4 dB per phrase): a real bassist's notes
  are never equally loud - 4-bar arcs, the root on 1 (two-feel) or 2 / 4 (walking) leaning, lighter pickups and
  approach notes, ghosted skips, pushed anticipations accented. `walking_bass(touch=1.0)` does it by default; a
  hand-written or pattern line goes through `jazz.bass_touch(line, lo, hi, accent='1-3' | '2-4')`. The upright
  (`sampled/upright_bass`) now follows velocity ((v/127)^2 across its evened layers, ~10 dB from 57 to 103) and the
  presets' bass chain is a peak catcher, not a leveller (the old 2.5:1 compressor left 0 dB of velocity response):
  the velocity IS the level - 80-95 for a walking line, ~80 for a soft pedal intro; 60-70 is really soft.
  Comping and the pianist's left hand also vary per hit (`comp(touch=1.0)`, `left_hand` follows the right hand).

## Brushes (the "seichte" drums)

- **Sweep**: a continuous circular swish on the snare (a sustained, filtered noise texture), accented on 2 and 4
  by the second brush (a soft tap / slap). This *is* the groove at medium and ballad tempos.
- **Hi-hat foot** on 2 and 4 (pedal hat, soft, short).
- **Kick**: "feathered" — very soft on all four beats, or omitted; a louder kick only as a punctuation.
- **Ride with brushes** (or soft sticks for the solo chorus): the "spang-a-lang" pattern
  (1, 2 and-a, 3, 4 and-a swung), light, for the hottest chorus.
- **Fills**: brush taps on triplets or 8ths at phrase ends (bar 8 of each A), a soft cymbal swell before a new chorus.
- Dynamics follow the piano; the drums never exceed the piano.
- **Toolkit**: `jazz.brushes(bars, style='medium' | 'ballad' | 'up' | 'two', kit=jazz.GM_BRUSH, fills=True,
  phrase=8, ride=False, vel=...)` (sweep per half bar / bar, taps + hat foot on 2 and 4, feathered kick, a fill every
  `phrase` bars; `ride=True` for the hot chorus), `jazz.ride_pattern(bars, 'spang')`, `jazz.brush_fill('swell', 2)`
  before a new chorus. Kit maps are dicts: `GM_BRUSH` (GeneralUser 'Brush': 40 = held swirl), `SWIRLY_BRUSH`
  (Karoryfer Swirly Drums keymap: 60 / 64 one-shot stirs - `sweep=jazz.swirly_sweep(s.tempo)`: one stir about
  every second, half bars at medium swing, beats at ballad tempos).

## Optional: saxophone (quartet)

A tenor sax (Coltrane's *Ballads*, Dexter Gordon, Stan Getz, Hank Mobley) turns the trio into a quartet.
The sax takes the heads and the first solo; the piano then comps and takes the second solo.

- **Roles**: sax = melody and lead voice (tenor ~A2–E5 sounding, sweet spot Bb2–Bb4; alto a fourth/fifth
  higher, brighter, more bebop). The piano comps *more sparsely* under the sax (shells, fewer notes in the
  sax's register, no melody doubling), and fills the sax's breaths with short answers.
- **Phrasing makes or breaks it** (a sampled sax played like a keyboard sounds fake):
  - breathe: phrases of 2–4 bars with real rests; no note-wall.
  - lay back further than the piano (20–40 ms), especially on ballads.
  - articulation: legato lines (slight overlap), accents on off-beat 8ths in swing lines, ghosted notes (low
    velocity) in fast runs, short "doo-dat" endings.
  - expression: long notes swell and fade (automate/modulate level over the note), delayed vibrato on held notes
    (starts after ~0.3–0.5 s, 4.5–5.5 Hz, grows), small scoops into important notes (pitch bend from −50…−100 cents),
    occasional falls at phrase ends.
  - melody paraphrase: when stating the head, displace rhythms, anticipate, embellish — never play it rigidly on the grid.
- **Solo**: the same melodic rules as the piano solo (motif development, targets, enclosures, bebop lines, space),
  but in the horn's range and with breaths; build over 2 choruses; trade fours with the drums before the head out.
- **Sound**: `inst.sf2('Tenor Sax', mono='on')` (GM 67) or `'Alto Sax'` (GM 66); plate/room send a bit higher than
  the piano's; eq: cut 300–400 Hz boxiness, gentle presence at 2–3 kHz; a little `tape` for breathiness;
  centre-left pan with the piano centre-right if both are prominent.
- **Mix**: sax as loud as the piano's melody (it leads when it plays); piano comping 3–5 dB under it.
- **Toolkit**: `line = jazz.horn_line(head, s.tempo, param='level', seed=...)` then `line.place(sax, section)`:
  swing + lay-back baked into the notes, legato phrases, breaths (before rests, and inside phrases longer than 2
  bars), phrase dynamics, and expression lanes - scoops into phrase starts / leaps, falls at phrase ends, swells and
  a delayed, growing vibrato on long notes (`vibrato=False` for GeneralUser's 'Tenor Sax': it has its own delayed
  vibrato, about +-19 ct at 5 Hz from 0.4 s; the FreePats tenor is straight and needs ours). `param='expression'`
  once the sampler update brings the expression control (the default), `'level'` or `'gainDb'` until then. Comp under it with
  `jazz.comp(..., answer=head, register=('A2', 'G4'))`.
- **Sampled sax, played**: `sampled/tenor_sax` / `sampled/alto_sax` are legato players (mono='legato'): horn_line's
  legato phrases become real legato transitions (no re-attack, level-matched), its vibrato runs on the sampler's own
  `vibrato` (continuous through the transitions), `param='dynamics'` puts the swells on the played dynamics, and
  `glide=0.3` adds portamento into leaps. Ballad phrase by hand: `art.perform(sax, line, section, glide_leaps=7)`
  (docs/COMPOSE_API.md "Realistic performance").

## Band presets (start here)

One call sets up a finished, balanced trio / quartet / ballad band / bossa group on the best installed sampled
instruments: sounds, stage placement, eq, dynamics, IR room + plate returns, sends, a sidechain, the master chain and
the analysis profile (`agentsound/bandlib/jazz.py`; demos with every number below: `songs/_bands/<preset>/song.py`).

```python
from agentsound import bands, jazz
from agentsound.bandlib import jazz as jazzband      # brushes(), pedal(), bossa_groove()
b = bands.make('jazz_quartet', s)                    # or 'jazz_trio', 'jazz_ballad' (bass='arco'), 'bossa'
ANALYSIS = {'profile': 'jazz'}                       # = b.analysis
b.comp.play(jazz.comp(prog, answer=head, register=('A2', 'G4'), seed=1), a1)
b.bass.play(jazz.walking_bass(prog, key=s.key, seed=2), a1)
b.drums.play(jazzband.brushes(b, 8, style='medium', seed=3), a1)
jazz.horn_line(head, s.tempo, seed=4, **b.info['horn']).place(b.sax, a1)
# 'gainDb' lanes are dB on the track's gain_db (here the preset's level for the bass)

b.bass.automate('gainDb', [(0, 0), (bass_solo.start, 1.5, 'smooth'), (head_out.start, 0, 'smooth')])
```

| preset | roles | sounds (fallback: GeneralUser GS) | space |
|---|---|---|---|
| `jazz_trio` | piano, comp, bass, drums | Salamander Grand SFZ (release samples), Meatbass pizz, Swirly brush kit | salon IR (0.8 s), master -14.5 LUFS |
| `jazz_quartet` | + sax | + MTG tenor (legato player, live dynamics, own vibrato); comping ducks 1.5 dB under it | salon + 224XL plate |
| `jazz_ballad` | piano, comp, bass, drums, sax | pedalled Salamander, Swirly stirs per beat, `bass='pizz'` or `'arco'` (Meatbass arco, legato) | 224XL chamber + rich plate |
| `bossa` | guitar, piano, bass, drums, rim, shaker, sax | FreePats nylon guitar, Blonde Bop cross-stick, FreePats egg shaker, airy tenor; straight 8ths | salon + 224XL plate |

- **Placement (audience view)**: piano left (its own pan -0.5, comping -0.3: a track pan only attenuates one side
  and hardly moves the Salamander, whose melody register sits right of centre), bass centre, drums right (+0.35),
  sax in front (centre), bossa guitar left, cross-stick and shaker right with the drums (the Blonde Bop side stick
  plays at width 0: its own drummer-view pan would pull it back to the centre). The report reads it as piano
  +1.6..+2.9 dB left, drums -4 dB right, every full-band section of the demos within 1 dB of centre (with the sax at
  +0.2 the quartet had leaned 1-1.8 dB right; an intro of piano or guitar alone leans ~2 dB left).
- **Balance measured on the demos** (dry tracks): lead -18.5..-20.5 LUFS, comping 5-6 dB under, bass 3.5-5.7 dB,
  brushes 13-15 dB, cross-stick 15.5, shaker 15 dB under (the drums 3 dB softer than first calibrated,
  `DRUM_TRIM`: the user found them "etwas zu laut" at 10-12 dB); the mixes -14.1..-14.9 LUFS, LRA 5.2-7.0 LU, 0 clicks, 0
  report warnings under the `jazz` profile. `b.info['sounds']` / `['credits']` say what played (credit the Salamander,
  CC-BY 3.0 Alexander Holm, the MTG saxophones, CC-BY 4.0, and the Blonde Bop kit, CC-BY-SA 3.0).
- **Brushes**: the Swirly stir is ~19 dB under a tap at the same velocity - with `jazz.brushes()` straight onto the
  kit the sweep is inaudible. `jazzband.brushes(b, bars, ...)` plays jazz.brushes keyed for the kit it got and
  levels it (stirs x1.9, taps x0.8). A Swirly stir is a swell (~0.6 s in, an exponential tail) that the next one
  crossfades (the `sampled/brush_kit` patch sets its stir tail and release to the maximum): one stir about every
  second keeps it continuous (~9 dB swell per gesture), one per bar at 144 BPM or per half bar at 66 BPM left
  25-30 dB of silence between them. `b.info['sweep']` = `jazz.swirly_sweep(tempo)`: half bars at medium swing,
  beats below ~109 BPM, bars above ~218 BPM.
- **Sax**: always `horn_line(..., **b.info['horn'])` - on the MTG tenor `param='dynamics'` (the swells move its
  live dynamics), its own delayed vibrato, legato transitions, `glide=0.2`. Soft layer up to velocity 100, the
  loud (brighter) one 101-127: keep heads at 70-95 and let a solo climax reach 105-115.
- **Space**: the IR salon (a modelled 18th-century wooden room) against the algorithmic room on the trio demo:
  17 vs 15 LU under the mix, tails -37 vs -35 dB - the IR has real early reflections and no modulation shimmer;
  `space='room'` keeps the algorithmic one, `'club'` the 224XL room, `'chamber'` the ballad chamber.
- **Mix fixes the presets carry** (each measured): the Meatbass read +10 dB sub against the jazz profile (low
  shelf -5 dB at 90 Hz, high-pass 42 Hz); the feathered kick masked the bass (brushes high-passed at 80 Hz); the
  Salamander and the tenor piled +4..+6 dB into 250 Hz-2 kHz (cuts on both + a broad master dip at 450 Hz / 1.3
  kHz); the close tenor alone is 1 % wide (microshift + plate + a master width of 1.15 above 150 Hz keep the mix
  above the profile's 15 %); the demos read 2-3 dB dull at 2.5-6 kHz against the profile (master +1.5 dB at
  3.8 kHz).
- **A warm piano, not a hard one** (HUMAN_FEEDBACK 2026-09-30, perry-street-rain: "es klingt hart"): the presets play
  `sampled/jazz_grand` (the Salamander with softened hammers: its loud layers get far brighter than louder), no
  presence boost on the piano (air at 11 kHz), the loud attacks rounded on the piano tracks (`SOFT_PIANO`: a fast
  soft-knee compressor on the loudest hits + a touch of tape), the piano a little further back in the room. Don't
  undo it in a song with a 3-5 kHz shelf on the piano: if a soft passage reads dull, lift the air (8-12 kHz) or
  play it a little louder.
- **Ballad**: `jazzband.pedal([b.piano, b.comp], prog, section)` changes the pedal with the harmony; `s.rubato`
  on the intro, `s.ritardando` into the last chord, `Song(tail=6)` for the chamber.
- **Bossa**: `jazzband.bossa_groove(bars, b)` -> the drums / rim / shaker clips (brush 8ths, kick 1 &2 3 &4, hat
  foot 2 and 4, the 2-bar cross-stick 1 &2 4 | &1 3, shaker 8ths); guitar = `jazz.comp(style='bossa',
  voicing='drop2', register=('E3', 'E5')).strum(ms=12)`, bass `prog.bass(pattern='R__f', rate='1/8')`.

## Sounds in AgentSound

`jazz.band(s, sax=True)` (the toolkit set-up without IR rooms or master; the presets above are the finished
version) plays each role from its installed SFZ pack (`sampled_sounds='auto'`, `jazz.SFZ_SOUNDS`: Salamander Grand,
Meatbass, Swirly Drums, the MTG tenor) and from GeneralUser GS where a pack is missing, levelled to the GeneralUser
balance; `b.kit` / `b.sweep` / `b.horn` / `b.sounds` say what it got (brushes: `jazzband.brushes(b, ...)`,
the sax: `horn_line(..., **b.horn)`). `sampled_sounds=False` keeps GeneralUser only (songs/_demo_jazz), `True` wants
every pack, `'sf2'` the SoundFont packs below. Pass `piano=`, `bass=`, `drums=`, `horn=` to swap a sound (then
re-level that track).

| role | sampled (SFZ, `python -m agentsound samples`) | GeneralUser GS (the fallback) |
|---|---|---|
| piano | **Salamander Grand** (`salamander-grand`: Yamaha C5, 16 velocity layers, release samples, CC-BY 3.0 Alexander Holm - credit it) | `inst.sf2('Grand Piano')`: stereo, 8 layers; comping velocities 50–100, lines 70–115 |
| upright bass | **Meatbass** (`meatbass`: 1958 upright, pizz 4 velocities x 5 takes, CC0 Karoryfer; `sampled/upright_bass`: layers evened to one (v/127)^2 response; arco `Programs/01_arco_modwheel.sfz`) | `inst.sf2('Acoustic Bass')` (0:32): mono centre; eq −2.5 dB at 170 Hz, +2 dB at 850 Hz for finger attack; a peak catcher (−9 dB, 3:1, fast), never a levelling compressor: it erases the line's dynamics |
| brushes | **Swirly Drums** (`swirly-drums`: stirs, taps, digs, ride, hats, CC0 Karoryfer; `sampled/brush_kit`, keymap `jazz.SWIRLY_BRUSH`, `sweep=jazz.swirly_sweep(tempo)`) | `inst.sf2(bank=128, program=40)` ('Brush'): 38 tap, 39 slap, 40 held swirl (`jazz.GM_BRUSH`); quiet by design - level +12, gain −3 in `band()` |
| tenor sax | **MTG tenor** (`mtg-solo-sax`, `sampled/tenor_sax`: legato player, CC-BY 4.0); FreePats tenor (`freepats-tenor-sax`, CC0) | `inst.sf2('Tenor Sax', mono='on')` (0:66) |
| alternative keys | | `synthwave/epiano` (DX7 E.PIANO 1): 70s/80s fusion flavour, not for the NYC bar sound |

Two packs also come as SoundFonts: `jazz.band(s, sax=True, sampled_sounds='sf2')` takes the Salamander Grand
(`salamander-grand-v3-sf2`) and the FreePats tenor (`freepats-tenor-sax-sf2`) from there (one sound:
`jazz.sampled('piano')`). Measured on the whole demo: the Salamander is a spaced-pair recording whose L/R samples
are barely correlated (some notes negative), so it plays at sf2 width 0.7 with no extra widener (the GeneralUser
piano's width 2.0 + widener 1.7 made it 360 % wide, correlation -0.65, -8 dB in mono); both sampled sounds are
warmer (more 250-800 Hz) than the GeneralUser presets, and the Salamander's pianissimo layers make right-hand lines
at velocity 40-55 about 6 dB softer than on the GeneralUser piano - voice them at 60-90. Credit the Salamander
(CC-BY 3.0, Alexander Holm). Presets: `python -m agentsound sf2 [search] [--file F]`; packs: `python -m agentsound samples`.

## Mix: a small room, close and warm

- **Room**: one short room reverb (type `room` or `chamber`, 0.8–1.4 s, pre-delay 8–15 ms) shared by all three,
  return 12–18 LU under the mix; a touch of plate on the piano for ballads. No chorus, no big halls.
- **Placement** (audience view): piano wide stereo but anchored centre, bass centre, drums spread gently
  (hi-hat left, ride right), kick/bass mono.
- **Balance**: piano leads (−0..−2 dB relative), bass 3–6 dB under the piano but always audible (walking
  lines must be followable), brushes 13–15 dB under the piano (clearly behind it, like a club trio record).
- **Tone**: warm, not bright: `tape` on the master (15 ips, subtle), gentle compression on the bass (3:1, slow),
  no exciter; a slight high roll-off above 12 kHz is period-correct.
- **Loudness**: jazz is dynamic: −16…−13 LUFS integrated, loudness range 6–12 LU, true peak ≤ −1 dBTP; light
  limiting only (a few dB at most). Use the analysis profile `jazz` (`ANALYSIS = {'profile': 'jazz'}`). The GM
  acoustic bass reads +5…+7 dB sub under it: high-pass or shelve it below ~50 Hz (the sampled Meatbass does not).
- **What `jazz.band()` sets up** (measured dry track levels on medium-swing material): piano melody / sax about
  −19.5 LUFS, comping −23.5, bass −22.5, brushes −29; pans piano +0.15 (its low comping register sits left of
  the treble: one wide piano), sax −0.25, bass and drums centre; a subtle M/S widening on the piano and a Haas
  microshift on the brushes and the sax; room 1.2 s (all) + plate 1.9 s (sax, piano right hand). The demo masters
  with `fx.tape(speed='15', drive=1.5)`, +1.5 dB air at 10 kHz and `fx.limiter(gain=3, ceiling=-1.2)`: about −14
  LUFS. Shape the arc per section with velocities (`vel=` on comp / walking_bass / brushes, `clip.velocity()` on
  the head): intro and ending softer, bridge and last A fuller.

## Checklist per tune

- Form written out (AABA/blues), choruses counted, every chorus with a different intensity plan.
- Chords with correct extensions per function; piano voicings rootless and voice-led; guide tones move by step
  (`jazz.jazz_voicings` + `jazz.check_voicing` for hand-written voicings).
- Melody/solo lines target chord tones; phrases start off the beat; space between phrases.
- The piano lead harmonized, decorated and filled (`pianist.arrange`), not a single-note line; the right hand above
  C4 while the left hand plays; a move per phrase or so, not everywhere.
- Bass walks with approach notes; two-feel where the tune breathes.
- Brushes sweep continuously; 2 and 4 audible but soft.
- Swing ratio set for the tempo; piano laid back relative to the bass.
- Ending with a tag and a coloured final chord that rings out.
