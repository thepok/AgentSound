# Classical recipe: orchestra, chamber music and film-score writing

Real players in a real hall: a string section that breathes, winds that phrase like singers, brass that
blooms from pp to ff, timpani that crown the climax, and a concert hall around all of it. The listener must
believe in the room and the people, so everything below serves that illusion: idiomatic ranges, voicing by
the harmonic series, dynamics that shape every phrase, seating in the stereo field and one coherent hall.
References: Beethoven 7 (Allegretto), Dvořák 9, Brahms 4, Tchaikovsky 5/6, Ravel *Daphnis*, Barber *Adagio for
Strings*, Elgar *Nimrod*; film: John Williams, James Horner, Thomas Newman, Howard Shore, Hans Zimmer (*Interstellar*,
*Dune*), Alexandre Desplat. Analysis profile: `classical` (`film` for orchestral hybrid cues, below; `piano` for
solo piano - the classical targets with a piano's spectrum: under `classical` a concert piano recording reads
lowmid / mid +11..+13 dB).

## Sub-styles (pick one per piece, write it in song.py)

| style | tempo | ensemble | signature |
|---|---|---|---|
| Baroque (concerto grosso, chorale) | 60–120, steady pulse | strings + continuo (harpsichord, cello, bass), oboes, trumpets | sequences, walking continuo bass, terraced dynamics (f / p blocks), 4-3 suspensions, little vibrato |
| Classical era (Haydn, Mozart) | 60–160 | strings, 2 fl, 2 ob, 2 bn, 2 hn, (2 tp, timp) | periodic 4+4 phrases, Alberti / repeated-note accompaniment, clear cadences, winds double and colour |
| Romantic symphonic | 50–140, rubato | full orchestra, 4 horns, 3 trb, tuba, harp | long melodies in violins / cellos / horns, chromatic harmony, big crescendos, climaxes on the dominant |
| Impressionist (Debussy, Ravel) | free, 40–100 | colour orchestra, harp, celesta, muted brass | parallel chords (planing), whole-tone / pentatonic / modal colour, 9ths and 11ths, flute and harp arabesques |
| String orchestra / Adagio | 40–70 | strings 5 parts, often divisi | suspensions, long crescendo to one climax, sustain + portamento feel, hush at the end |
| String quartet / chamber | 50–140 | 2 vln, vla, vc (+ piano, clarinet ...) | four real voices, dialogue, imitation, close miking, smaller room |
| Solo piano (Chopin, Satie, Debussy) | 40–120, rubato | grand piano | pedal as colour, left-hand patterns, melody sings in the top voice |
| Minimalist (Glass, Reich, Pärt) | 60–140 | strings, winds, piano, marimba | repeated cells shifting by one note, additive rhythm, tintinnabuli triads, slow harmonic change |
| Film score, lyrical (Williams, Horner, Newman) | 60–100 | full orchestra (+ piano, choir) | leitmotif, horn / string themes, chromatic mediants, lydian wonder, swelling transitions |
| Film score, hybrid / epic (Zimmer) | 60–130 | strings ostinati, low brass, taikos, choir, synth sub | ostinato + pedal, i–VI–III–VII in minor, braams, huge low end: use the `film` profile |

## Form and dramaturgy

- **Phrases**: 4+4 (antecedent ends on a half cadence, consequent on the tonic) or the 8-bar *sentence*
  (idea, repeat, fragmentation, cadence). Mark cadences clearly: they are the punctuation the ear follows.
- **Forms**: ternary A–B–A' (the return varied and re-orchestrated), rondo A–B–A–C–A, theme and variations
  (each variation a new texture / register / mode), sonata form (exposition: theme 1 in the tonic, transition,
  theme 2 in the dominant / relative; development: fragments, modulations, climax; recapitulation both themes
  in the tonic; coda), arch form (A–B–C–B–A). A 3–4 minute piece: ternary or a film-style through-composed cue.
- **One climax** per piece, around 60–70 % of the length (the "golden section"), prepared by a long crescendo
  in texture, register and harmony; after it a sudden drop (subito p) or a long glowing descent.
- **Dynamics map**: write it first, bar by bar (pp intro → mp theme → mf/f development → ff climax → p coda).
  Contrast is the drama: an orchestral piece has 15–20 LU between its softest and loudest passages.
- **Film cues**: through-composed around hit points (a moment every 4–16 bars), a leitmotif that returns
  transformed (minor / major, slow / fast, solo / tutti), transitions that swell into the next scene.

## Harmony and voice leading

- **Functional core**: I–IV–V–I, I–vi–ii6–V7–I, ii6/5 or IV before V, cadential 6/4 (I6/4–V–I) at big cadences,
  deceptive cadence V–vi to extend a phrase, half cadence (…–V) to end an antecedent.
- **Colour chords**: secondary dominants (V7/V, V7/ii, V7/vi), diminished sevenths as passing / pivot chords,
  Neapolitan bII6 before V in minor, augmented sixths (It+6, Fr+6, Ger+6) resolving to V, the minor iv in major
  (nostalgia), the Picardy third (major I at the end of a minor piece).
- **Suspensions** (4–3, 7–6, 9–8, 2–1): the sound of the Baroque and of every Adagio: prepare the note in the
  previous chord, hold it over the change (dissonance on the strong beat), resolve down by step.
- **Pedal points**: tonic pedal under changing harmonies (openings, endings), dominant pedal to build tension
  before a return; in the basses / timpani / horns.
- **Modulation**: to the dominant or relative in classical forms; by common chord or chromatic pivot; up a step
  or by a third for a final statement.
- **Film idioms**: chromatic mediants (C major → Ab major / E major: wonder, flight), I–bVI–bVII–I (heroic),
  lydian #4 (magic, flying), minor i–bVI–bIII–bVII (Zimmer epic), i–iv with a major IV (bittersweet), sus2/sus4
  and quartal chords (open landscapes), low tritone / clusters (menace), a pedal tone under moving triads.
- **Voice leading** (makes an orchestra sound like one instrument): keep common tones, move the other voices by
  step, contrary motion between melody and bass, no parallel fifths / octaves between outer voices, leading tone
  up to the tonic, chord sevenths down by step. Use `voice_lead(chords, register=..., voices=...)` for the
  inner parts and write the melody and bass lines by hand.
- **Spacing follows the harmonic series**: wide intervals in the bass (octaves, fifths), closer toward the top.
  Thirds below ~C3 sound muddy. Double the root (or the fifth), never the leading tone; keep the third in the
  middle.

## Orchestration

### Ranges and sweet spots (sounding pitch, C4 = middle C)

| instrument | range | sweet spot / character |
|---|---|---|
| Violin | G3–A7 (orchestral to ~E7) | G3–E6; G string dark and warm, E string brilliant above A5 |
| Viola | C3–E6 | C3–C5; dark, veiled, the "inner voice" |
| Cello | C2–A5 | C2–A4; D4–A4 is the singing tenor register (themes!) |
| Double bass | E1–G3 (sounds an octave below written; C1 with extension) | E1–D3; doubles the cellos an octave lower |
| Harp | B0–G#7 | C2–C6; arpeggios, glissandi, harmonics; muted by nothing: let it ring |
| Piccolo | D5–C8 | top octave of tutti, festive; tiring above C7 |
| Flute | C4–D7 | G4–G6; low octave soft and breathy (only in quiet textures), bright top |
| Oboe | Bb3–A6 | D4–D6; plaintive solo voice, penetrating, poor pp at the bottom |
| English horn (cor anglais) | E3–C6 | G3–G5; melancholic solo (Dvořák 9 Largo) |
| Clarinet (Bb) | D3–Bb6 | chalumeau D3–E4 dark and rich, clarion A4–Bb5 bright; best pp of all winds |
| Bass clarinet | Bb1–F5 | Bb1–C4; soft velvet bass, doubles cellos / bassoons |
| Bassoon | Bb1–E5 | Bb1–G4; bass of the winds, D3–D4 lyrical tenor solos, staccato wit |
| Contrabassoon | Bb0–F3 | the organ-pedal of the orchestra, doubles the basses |
| French horn (F) | B1–F5 | C3–C5; the glue of the orchestra (pads, sustained harmony), heroic unison themes |
| Trumpet (Bb / C) | E3–C6 (D6) | C4–G5; fanfares, climaxes, muted colour |
| Trombone | E2–F5 | F2–F4; chorales, weight, ff power |
| Bass trombone | Bb1–Bb4 | F1–F3 with the tuba |
| Tuba | D1–F4 | F1–F3; foundation of the brass, sparing in soft music |
| Timpani | D2–A3 (4 drums: D2–A2, F2–C3, Bb2–F3, D3–A3) | tonic and dominant, rolls for swells, hits on downbeats |
| Glockenspiel | G5–C8 (2 octaves above written) | doubles a melody in the top, sparkle |
| Xylophone | F4–C8 (octave above written) | dry, bright staccato doubling |
| Celesta | C4–C8 (octave above written) | magic, music-box doubling of flutes / violins |
| Vibraphone / marimba | F3–F6 / C2–C7 | film and minimalist colour |
| Tubular bells | C4–F5 | bells at climaxes, weddings, funerals |
| Choir S / A / T / B | C4–A5 / G3–E5 / C3–A4 / E2–E4 | "aah" pads above the strings, "ooh" soft |

Keep every part in its range (a sample played outside its range is pitched and sounds fake); keep melodies
in the sweet spot; a note above the sweet spot is an effort (use it for intensity, briefly).

### Voicing, doubling and balance

- **Four layers**: melody (on top, one colour or a doubled colour), bass line (cellos + basses in octaves, +
  bassoon, + tuba in tutti), harmony filler (violas, 2nd violins, horns, clarinets), rhythm / colour (pizzicato,
  harp, timpani, percussion). Each layer must be audible: if two layers share a register, move one.
- **Classic doublings**: violins I + II in octaves (melody ff); flute an octave above the violins; oboe in unison
  with the violins (edge); clarinet with the violas; bassoon with the cellos; basses an octave below the cellos;
  horns double the melody in unison for a heroic climax, otherwise sustain the harmony.
- **Weights** (at the same dynamic): 1 trumpet ≈ 2 horns ≈ 1 trombone > whole woodwind section > 4 violin desks.
  In a tutti, the strings need doubling or the brass must play one dynamic lower (write *f* for brass under *ff*
  strings).
- **Strings divisi**: split a section (div. a2 / a3) for pads and close chords: 1st violins 2 notes, 2nd violins
  2 notes, violas 2 notes = 6-part string pad. Divisi makes each line thinner and softer: good for pp and
  shimmer, bad for a powerful melody (then unison).
- **Textures**: sustained pads (sustain / legato), pulses (repeated 8ths / 16ths spiccato or staccato),
  tremolo (tension, excitement), pizzicato (lightness, bass lines), col legno (clicks), harmonics (ghostly).
- **Winds as colour**: a flute solo over a string pad, an oboe answering the violins, clarinet arpeggios in the
  chalumeau; woodwind chords (2 fl, 2 ob, 2 cl, 2 bn interlocked) for a pastoral choral.

### Dynamics and articulation with samples

- **Velocity = dynamics** in most sampled instruments (the SSO "Notation" set: velocity sets volume, attack and
  brightness): pp 25–40, p 40–55, mp 55–70, mf 70–85, f 85–105, ff 105–127. Never play a whole part at one velocity.
- **Phrasing**: every long note is a swell (messa di voce: crescendo into the middle, taper off), every phrase
  has a shape (up to its high point, down to the cadence), the last note of a phrase is shorter and softer.
  Automate `gainDb` (and the hall send) for swells on sustained notes: `strings.automate('gainDb', swell(...))`.
- **Articulations as separate tracks**: `vln1_sus`, `vln1_stac`, `vln1_pizz` (one SFZ each) sharing the same pan
  and hall send, so switching articulation is just writing notes on another track.
- **Legato**: monophonic legato programs (SSO "Legato", NBO `_legmode`, Karoryfer `*_legato_map`) connect
  overlapping notes: write lines with a small overlap (`clip.legato(0.05)`), one voice per track.
- **Sample speed**: section samples have slow attacks (strings 50–200 ms, low brass up to 150 ms). Start sustained
  notes 30–80 ms early (`clip.shift(-0.06)` at 100 BPM ≈ −36 ms; not before beat 0) so they *sound* on the beat;
  keep shorts on it. Check with `python -m agentsound zoom songs/<slug> --at <time> --stem <id>`.
- **Played, not triggered** (docs/COMPOSE_API.md "Realistic performance"): `sampled/solo_violin`,
  `sampled/solo_cello` and `sampled/violin_section` .. `sampled/bass_section` hold every articulation in one track
  (`clip.articulate('spiccato', span=...)` inserts the keyswitches) and play **live dynamics**: automate
  `instrument.dynamics` (0..1) instead of velocity-only dynamics, so a held chord swells from p to f through the
  recorded layers and the tone opens (`s.track('vc', 'sampled/cello_section').automate('instrument.dynamics',
  [(a, 0.1), (a + 8, 1, 'smooth'), (a + 15, 0.1, 'smooth')])`). Solo lines: `art.perform(track, line, section)`
  ties the phrases into legato transitions (mono='legato'), picks staccato / marcato / sustain by note length and
  accent, shapes every note (swell, cresc, dim, fp, sfz) and adds a delayed vibrato; portamento into a leap:
  `line.glide(150, where=art.leaps(7))`. Any .sfz: `inst.sfz(..)` keeps CC1 crossfades live, `inst.sfz_multi({..})`
  merges per-articulation programs, `layers='dynamics'` crossfades plain velocity layers.
- **Rubato and ritardando**: the engine has one tempo, so write them: stretch the last beats of a phrase
  (longer notes, later onsets), a final ritardando over 2–4 bars, a fermata (a held chord plus 1–2 beats of
  silence into the hall tail).

### Orchestrating a climax

1. Start with one colour (strings p, or a solo wind).
2. Add a layer every 2–4 bars: horns sustaining, woodwinds doubling, trumpets and trombones entering on the
   last phrase, timpani roll (crescendo) in the final bar before the peak.
3. Expand the register outward: basses go down (octave lower), the melody goes up (violins into the E string,
   flute / piccolo an octave above).
4. Harmonic tension: dominant pedal or a chromatic rising bass line, then the arrival on the tonic (or a
   deceptive bVI for an even bigger lift).
5. The arrival: full tutti on beat 1, timpani + bass drum + cymbal crash, brass in chords, strings in octaves.
6. After the peak: subito p (strings alone) or a long diminuendo: let the hall ring into the silence.

### Film-score toolbox

- **Ostinato**: strings spiccato / staccato 8ths or 16ths on one or two notes (celli + violas), accents shifting
  the groove (3+3+2), a pedal in the basses; low brass holds under it.
- **Braams and hits**: low brass (tuba, bass trombone, horns in low register) fortissimo cluster or open fifth,
  plus a taiko / bass drum hit and a sub sine (a short va `sine` at 30–45 Hz) on the downbeat.
- **Themes**: horns in unison (heroic), strings in octaves (emotional), solo piano or solo woodwind (intimate),
  choir "aah" doubling strings an octave up (epic). A SOLO theme in front of the orchestra (a film violin, a
  trumpet call, a flute melody) is a hero: `hero(s.track('violin', 'sampled/solo_violin'), family='strings',
  genre='film', bed=[strings, choir], competitors=[piano])` (docs/COMPOSE_API.md "Hero sounds": the strings hero
  chain, its own plate, echo throws, the bed ducked 1.5 dB and carved 3 dB at 2.8 kHz while it plays, +1 dB in the
  hooks; the violin stays a plain sampler, its articulations and `dynamics` swells keep working). Validated on a
  20-bar film cue (strings bed, choir, piano arpeggios, cellos, timpani): the bed +0.2 / +1.2 dB OVER the plain solo
  violin in verse / chorus (mixer: bed_too_loud, masking strings vs violin) -> -2.1 / -0.8 dB under the hero (both
  findings gone), low mids +10.0 -> +7.4 and mids +10.6 -> +8.2 dB vs the film reference, note dynamics 9.6 dB.
  `family='brass'` / `'woodwind'` for the trumpet / flute. In a classical (concert) mix: `genre='classical'` (no
  bed duck, no ride - the hall and the players balance).
- **Risers and transitions**: string crescendo on a tremolo chord, cymbal roll (suspended cymbal), harp or
  woodwind glissando up, reverse cymbal into the downbeat.
- **Pads under dialogue** (quiet cues): strings divisi pp sustain, one colour change per 4 bars.

## Seating and panning (audience view, pan −1 = left)

| section | pan | depth (hall send / high shelf) |
|---|---|---|
| 1st violins | −0.6 … −0.45 | front: send −6 … −5 dB |
| 2nd violins | −0.3 … −0.15 (or +0.5 antiphonal: 2nd violins opposite the 1st) | front |
| Violas | +0.15 … +0.3 | front-middle |
| Cellos | +0.35 … +0.5 | front |
| Double basses | +0.5 … +0.65 (behind the cellos) | send −6, high shelf −1 dB |
| Harp / piano / celesta | −0.45 … −0.35 | middle |
| Flutes / oboes (front row of winds) | −0.15 / +0.1 | middle: send −5 … −4, high shelf −1 |
| Clarinets / bassoons (back row) | −0.1 / +0.15 | middle |
| Horns | −0.35 … −0.2 (bells face backwards: indirect, round) | back: send −3, high shelf −2 dB |
| Trumpets | +0.1 … +0.2 | back: send −4 … −3 |
| Trombones / tuba | +0.3 … +0.45 | back: send −3, high shelf −1.5 |
| Timpani | −0.1 … +0.1 | back: send −3 … 0 |
| Percussion | ±0.3 … 0.5 | back |
| Choir | wide (two tracks ±0.3, or width 1.3) | behind the orchestra: send −3 |

Depth comes from three moves at once: less direct level, more reverb send, a softer top (eq high shelf
−1…−3 dB at 6 kHz). Sections are recorded with their own stereo spread: keep the sample `width` around 0.6–1.0
for violins, violas and winds, 0.3–0.5 for cellos, basses, tuba and timpani (centred lows, see the hall), and
1.0–1.3 for a full-string pad program.

## The hall

- **One hall for everything** (a single return makes one room): `hall = s.hall(decay=2.1, predelay=22,
  lowcut=110, highcut=9000, damping=6000, width=1.2, size=0.85)`. Concert halls: RT60 1.8–2.3 s (Musikverein
  2.0, Concertgebouw 2.2), chamber halls 1.3–1.7 s, churches 3–6 s. The synthwave hall's 250 Hz low cut would
  drain the warmth; a 100–120 Hz low cut keeps it and keeps the lows centred.
- **Centred lows**: stereo section samples plus a full-range hall decorrelate the low end (the report's
  `low_end_not_mono` warns below a correlation of 0.75 under 150 Hz; an SSO mockup with full-width sections and an
  80 Hz hall low cut read 0.27). Give cellos, basses, tuba and timpani a sample `width` of 0.3–0.5 (they stay in
  their seat) and the hall a 100–120 Hz low cut: the same mockup then reads 0.81 and is still 55 % wide.
- **Early reflections for proximity**: a short `chamber` or `room` return (0.8–1.2 s, predelay 5–10 ms) at −6…−10 dB
  on the close instruments glues sampled sections recorded in different rooms.
- **Sends**: strings −6…−4 dB, woodwinds −5…−3, brass and percussion −4…0 (further back), solo instruments
  −8…−6 (more direct). Target: the reverb return 4–14 LU under the mix (profile `classical`), tails at a
  stop above −30 dB. The sample sets carry different amounts of their own room (SSO only a little, Philharmonia
  very little): send everything to the one hall so they share a space.
- **Automate the room**: raise the hall send 2–4 dB on the last chord before a general pause so the hall rings.
- **Convolution** (`python -m agentsound params convolver`, patches `bus/ir_*`): real halls from IRs:
  `samples/voxengo-im-reverbs/Musikvereinsaal.wav` (Vienna, `bus/ir_concert_hall`), `Scala Milan Opera Hall.wav`,
  `St Nicolaes Church.wav`, `French 18th Century Salon.wav` (chamber), the Little Devil 224XL halls and chambers,
  the Bricasti M7 (`samplicity-bricasti-m7`), the Lexicon 480L (`grant-nelson-lexicon-480l`) and EchoThief's real
  spaces (`echothief`).

## Sound table (packs in `assets/samples/`, see `python -m agentsound samples`)

Paths are given for the planned `inst.sfz('samples/<id>/<file>.sfz', articulation=...)` (one SFZ per
articulation needs no `articulation=`; it picks an articulation inside keyswitched `KS` files). SoundFonts load
with `inst.sf2(preset, file=<absolute path>)` (relative sf2 paths mean `assets/soundfonts/`); WAV folders with
custom names load with `inst.sampler(zones=[...])`:

```python
from agentsound import library
def pack(*parts):                     # absolute path into assets/samples (or $AGENTSOUND_SAMPLES in worktrees)
    return library.SAMPLES.joinpath(*parts).as_posix()
SSO = 'samples/sso/Sonatina Symphonic Orchestra'
vln1 = s.track('vln1', inst.sfz(f'{SSO}/Strings - Notation/1st Violins Sustain.sfz'), pan=-0.5, sends={hall: -5})
timp = s.track('timpani', inst.sf2('Timpani', file=pack('freepats-timpani-sf2', 'Timpani 20240809.sf2')), sends={hall: -2})
```

**Main library: Sonatina Symphonic Orchestra 4.0** (`sso`, CC Sampling Plus 1.0: credit "Sonatina Symphonic
Orchestra (Mattias Westlund, Peter Eastman)", no use in advertising). Full orchestra, stereo 44.1 kHz, sampled in
minor thirds, little baked-in room. Use the **`- Notation`** folders (velocity = volume); the `- Performance`
programs drive long notes with the mod wheel (CC1), which songs cannot send yet, and CC21 controls string
vibrato. SFZs use `#include`/`#define` and loop points in the SFZ (the `(looped)` variants hold any length).

| part | first choice (SSO, `Sonatina Symphonic Orchestra/...`) | alternatives | notes |
|---|---|---|---|
| 1st / 2nd violins | `Strings - Notation/1st Violins Sustain.sfz`, `2nd Violins Sustain.sfz`; also `Marcato`, `Staccato`, `Legato`, `Pizzicato`, `Tremolo`, `Col Legno`, `Harmonics` | VSCO `vsco2-ce/ViolinEnsSusVib.sfz` (+`-Quiet`), `ViolinEnsSpic.sfz`, `ViolinEnsPizz.sfz`, `ViolinEnsTrem.sfz`; NBO-2 (violin sections, CC-BY-SA) | VSCO file names are one octave low: always map from the SFZ, never by file name |
| Violas | `Strings - Notation/Violas Sustain.sfz` (+ articulations) | `vsco2-ce/ViolaEnsSusVib.sfz`, `ViolaEnsSpic.sfz`, `ViolaEnsPizz.sfz`, `ViolaEnsTrem.sfz` | |
| Cellos (section) | `Strings - Notation/Celli Sustain.sfz` (+ articulations) | `vsco2-ce/CelloEnsSusVib.sfz`, `CelloEnsSpic.sfz`, `CelloEnsPizz.sfz`, `CelloEnsTrem.sfz` | |
| Solo cello | `Strings - Notation/Cello Solo Sustain.sfz`, `Cello Solo Legato.sfz` | `karoryfer-bigcat-cello/Programs/01- Bowed (velocity layer).sfz`, `03- Plucked.sfz`, `vc_arco_sus_legato_map.sfz` (CC0, close, non-vibrato: add a vibrato LFO); `ethan-winer-cello-solo/cello_solo.sf2` ("Ethan's Cello") | Karoryfer: sampled in minor thirds, 4-dynamic staccato, pizzicato, harmonics, slides |
| Basses (section) | `Strings - Notation/Basses Sustain.sfz`, `Basses Pizzicato.sfz` | `vsco2-ce/ContrabassSusVB.sfz`, `ContrabassPizz.sfz`, `ContrabassSpic.sfz` (solo bass); `meatbass/Programs/03_arco_5vel.sfz`, `04_pizz.sfz` (1958 upright, CC0); `dsmolken-double-bass/d_smolken_rubner_bass_arco.sfz`, `..._pizz.sfz` (CC0) | layer a solo bass + section for definition |
| Solo violin / viola | `Strings - Notation/Violin Solo 2 Sustain.sfz` (vibrato and non-vibrato), `Viola Solo Sustain.sfz` | `vsco2-ce/SViolinVib.sfz`, `SViolinSpic.sfz`, `SViolinPizz.sfz`; Philharmonia `violin/`, `viola/` (zones) | |
| Flutes / piccolo | `Woodwinds - Notation/Flutes Sustain.sfz`, `Flute Solo 1 Sustain (looped, decay).sfz`, `Piccolo Solo ...` | `vsco2-ce/FluteSusVib.sfz`, `FluteExpVib.sfz`, `FluteStac.sfz`, `PiccoloSus.sfz` | |
| Oboes / cor anglais | `Woodwinds - Notation/Oboes Sustain.sfz`, `Oboe Solo ...`, `Cor Anglais Solo ...` | `vsco2-ce/OboeSusVib.sfz`, `OboeStac.sfz` | |
| Clarinets / bass clarinet | `Woodwinds - Notation/Clarinets Sustain.sfz`, `Clarinet Solo ...`, `Bass Clarinet Solo ...` | `vsco2-ce/ClarinetSus.sfz`, `ClarinetStac.sfz` | |
| Bassoons / contrabassoon | `Woodwinds - Notation/Bassoons Sustain.sfz`, `Bassoon Solo ...`, `Contrabassoon Solo ...` | `vsco2-ce/BassoonSus.sfz`, `BassoonVib.sfz`, `BassoonStac.sfz`; `ethan-winer-bassoon/bassoon.sf2` | |
| Horns | `Brass - Notation/Horns Sustain.sfz`, `Horns Marcato.sfz`, `Horns Staccato.sfz`, `Horn Solo ...` | `vsco2-ce/FHornSus.sfz`, `FHornStac.sfz`, `FHornMute.sfz` | the warmest pad in the orchestra |
| Trumpets | `Brass - Notation/Trumpets Sustain.sfz`, `Trumpets Marcato.sfz`, `Trumpet Solo ...` | `vsco2-ce/TrumpetSus.sfz`, `TrumpetSusVib.sfz`, `TrumpetStraightMuteSus.sfz`, `TrumpetHarmonMuteSus.sfz` | |
| Trombones / bass trombone | `Brass - Notation/Trombones Sustain.sfz`, `Tenor Trombone Solo ...`, `Bass Trombone Solo ...` | `vsco2-ce/TromboneSus.sfz`, `TromboneVib.sfz`, `TromboneStac.sfz` | |
| Tuba | `Brass - Notation/Tuba Sustain.sfz`, `Tuba Staccato.sfz` | `vsco2-ce/TubaSus.sfz`, `TubaStac.sfz`; `karoryfer-war-tuba/Programs/2-solo-poly.sfz` (folk-punk tone, CC0) | |
| Timpani | `Percussion/Timpani.sfz` (hits, rolls, crescendos) | `vsco2-ce/Timpani.sfz`, `TimpaniRolls.sfz`; `freepats-timpani-sf2/Timpani 20240809.sf2` ("Timpani", round robins) | |
| Percussion | `Percussion/Bass Drum & Snare.sfz`, `Cymbals & Tamtam.sfz`, `Triangle.sfz`, `All Unpitched Percussion.sfz` | `vsco2-ce/GM-StylePerc.sfz`; Ethan Winer SF2s `ethan-winer-triangle/triangle.sf2`, `...-sleigh-bells/sleigh_bells.sf2`, `...-tambourine/tambourine.sf2`; Philharmonia `percussion/*` (one-shots: clash cymbals, tam-tam, bass drum) | |
| Mallets / bells | `Percussion/Glockenspiel.sfz`, `Xylophone.sfz`, `Celeste.sfz`, `Chimes.sfz`, `Crotales.sfz`, `Vibraphone.sfz`, `Marimba Hits.sfz` | `vsco2-ce/Glockenspiel.sfz`, `Xylophone.sfz`, `Marimba.sfz`, `TubularBells.sfz`; `freepats-xylophone-sf2`, `freepats-tubular-bells-sf2`, `ethan-winer-glockenspiel`, `ethan-winer-tubular-bells` (SF2); `mslp-vibes/mslp_vibes.sfz` (CC-BY-NC: music OK, samples not) | |
| Harp | `Concert Harp.sfz` (in the SSO root) | `vsco2-ce/Harp.sfz`; `freepats-concert-harp-sf2/ConcertHarp-20200702.sf2` (preset "Instrument") | |
| Choir | `Chorus - Notation/Mixed Chorus.sfz`, `Large Chrous.sfz` (sic; `Chorus - Performance/Large Chorus.sfz`) | `nbo-2/Choir/choir.sfz` ("Oh"); GM `gm/choir_aahs`, `inst.sf2('Voice Oohs')` | |
| Organ | `Organ/Organ Combinations.sfz`, `Organ All Stops.sfz`, single stops (`Great - Open Diapason 8ft.sfz`, `Pedal - Bourdon 16ft.sfz`, ...) | `freepats-church-organ-emulation-sf2/ChurchOrganEmulation-20190924.sf2`; `vsco2-ce/OrganLoud.sfz`, `OrganQuiet.sfz` (+`Pedal`); Lars Palo sets (below) | organ pedals at 16' add real sub: judge with the classical `sub` limit (+7) in mind |
| Harpsichord | `Harpsichord/Harpsichord 8'.sfz`, `Harpsichord Full.sfz` | `nbo-2` harpsichord (note-named WAVs) | Baroque continuo |
| Grand piano | `salamander-grand/SalamanderGrandPianoV3.sfz` (Yamaha C5, 16 velocity layers, CC-BY: credit Alexander Holm) | `Grand Piano/Grand Piano.sfz` (SSO), `splendid-grand-piano/Splendid Grand Piano.sfz` (public domain), `headroom-piano/Headroom Piano.sfz` (C3, close + Decca, CC-BY), `osiris-piano/Programs/01-natural.sfz` (quiet C2, soft pedal, CC0), `ydp-grand-piano-sf2`, `salamander-grand-v3-sf2` | |

**Other orchestral packs**

- **VSCO 2 CE** (`vsco2-ce`, CC0, Versilian Studios): chamber-size sections and solos with vibrato / non-vibrato
  and quiet variants, 75 SFZs in the pack root (`ViolinEnsSusVib.sfz`, `CelloEns-KS.sfz`, `Contrabass-KS.sfz`,
  `Flute-KS.sfz`, `Tuba-KS.sfz` ...). **Sample file names are one octave low** (a file named `A2` plays A3): map
  from the SFZ key centres. Chamber-size sections: ideal for chamber music, intimate film cues and for layering
  with SSO (VSCO violins under SSO 1st violins thicken the section).
- **Virtual Playing Orchestra 3** (`vpo-scripts-standard` / `vpo-scripts-performance` + `vpo-wav`): a curated mix of
  SSO, NBO, VSCO, Iowa and Philharmonia samples with per-section scripts (`Strings/1st-violin-SEC-sustain.sfz`,
  `-staccato`, `-pizzicato`, `-tremolo`, `-accent`, `all-strings-SEC-*-panned.sfz`, `Brass/french-horn-SEC-*`,
  `Percussion/timpani-hit-n-roll.sfz` ...). The scripts reference `..\libs\...`, i.e. they expect the `libs` folder of
  `vpo-wav` next to their category folders: they only resolve if the sfz player maps them onto
  `samples/vpo-wav/libs` (otherwise use SSO / VSCO). Standard = velocity driven (use it); `-normal-mod-wheel` and
  the performance set need CC1. License: royalty-free for music, components CC0 / Sampling Plus / CC-BY-SA, no
  resale of the library.
- **No Budget Orchestra 2** (`nbo-2`, CC-BY-SA-4.0 for the SFZ and Jeff Glatt sets; some Freesound-derived sets
  carry other licenses, see each `license.txt`; the choir is music-use only): sections and solos with several legato
  modes (`Cello/CelloSect/cellos.sfz`, `cellos_legmode.sfz`, `cellos_pizzi.sfz`, `cellos_tremulo.sfz`, `FrenchHorn/
  HornSect/horns.sfz`, `Flute/SoloFlute/flute_vib.sfz`, `Choir/choir.sfz` ...). Heavily looped: best for long
  pads and the choir, blended under SSO. Credit Jeff Glatt and the per-instrument sources.
- **Philharmonia Orchestra samples** (`philharmonia-all`, free for music, **no redistribution**, MP3 converted to WAV:
  leading silence, use the sampler's `start` offset and check with `python -m agentsound zoom`): every solo
  instrument in many dynamics and articulations, one folder per instrument (`violin/`, `cello/`, `french horn/`,
  `percussion/tam-tam/` ...), files `<instr>_<note>_<length>_<dynamic>_<articulation>.wav` with sharps as `s`
  (`violin_As3_1_forte_arco-normal.wav`); lengths `025 05 1 15 long very-long phrase`, dynamics `pianissimo` …
  `fortissimo`, articulations `arco-normal`, `arco-legato`, `arco-staccato`, `arco-spiccato`, `arco-tremolo`,
  `pizz-normal`, `molto-vibrato`, `non-vibrato`, `natural-harmonic`, `arco-sul-ponticello` .... Build zones:

  ```python
  from agentsound import library, note
  def philharmonia(instr, length='1', art='arco-normal', layers=(('piano', 1, 70), ('forte', 71, 127))):
      folder = library.SAMPLES / 'philharmonia-all' / instr
      zones = []
      for dyn, lo, hi in layers:
          for f in sorted(folder.glob(f'*_{length}_{dyn}_{art}.wav')):
              pitch = f.stem.split('_')[1].replace('s', '#')         # 'As3' -> 'A#3'
              zones.append({'file': f.as_posix(), 'root': pitch, 'vello': lo, 'velhi': hi})
      return zones                                               # each root plays the keys nearest to it
  oboe = inst.sampler(zones=philharmonia('oboe', length='1', art='normal'), start=30, release=0.3)
  ```
  (Wind folders use `normal` / `staccato` instead of `arco-*`; list a folder before choosing.)
- **Solo bass specialists**: `iowa-doublebass-arco-1644` and `iowa-doublebass-pizz-1644` (Univ. of Iowa MIS,
  unrestricted) are **chromatic runs per string** (`Bass.arco.sulA.ff.A1B1.stereo.wav`): slice into notes before
  use (zones with `start` offsets), or prefer meatbass / D. Smolken.
- **Organs**: Lars Palo GrandOrgue sets (`lars-palo-burea-church`, `lars-palo-burea-choir-organ`, `lars-palo-pitea-mhs`;
  CC-BY-SA-2.5: credit "sample set by Lars Palo (familjenpalo.se)", share-alike applies to modified samples): one
  folder per stop, files `<midi>-<note>.wav` (`HVPrincipal8/036-C.wav` = C2) → zones with `root` from the number;
  mix stops by layering tracks (Principal 8' + Octave 4' + Mixture = plenum). Their sustain loops live in the WAV
  `smpl` chunk, which the engine does not read yet: notes stop at the sample end (SSO organ SFZs and the FreePats
  SF2 loop fine).
- **GM fallbacks**: GeneralUser GS (`inst.sf2('Slow Strings')`, `'Fast Strings'`, `'Tremolo Strings'`, `'Pizzicato
  Strings'`, `'French Horns'`, `'Trumpet'`, `'Trombone'`, `'Tuba'`, `'Flute'`, `'Oboe'`, `'Clarinet'`, `'Bassoon'`,
  `'Timpani'`, `'Orchestral Harp'`, `'Concert Choir'`, kit `'Orchestral'`), `musescore-general-sf2`, `fluidr3-gm2`,
  `sso-sf2` (older SSO 1.x as 57 SF2 files, e.g. `Strings - 1st Violins Sustain.sf2`). They are darker and more
  generic than the SFZ libraries; fine for sketches and layering.
- **Coming**: `vcsl` (Versilian Community Sample Library, CC0: harpsichords, organs, percussion, world instruments).

**License duties** (keep a `CREDITS` line in song.py's docstring and in the delivery message): CC-BY / CC-BY-SA /
Sampling Plus → name the library and author; SA only binds redistributed or modified *samples*, not the music;
NC packs (MSLP vibes, jRhodes) and "no redistribution" packs (Philharmonia, Kalthallen) → use in music only, never
ship the samples; CC0 packs need nothing (credit is still polite).

## Band presets (agentsound/bandlib/orchestra.py)

One call seats a complete, balanced ensemble in one hall - the sounds, articulations, seating, depth, eq, the
convolution hall, the master chain and the analysis profile - so a piece starts from a finished orchestra:

```python
from agentsound import bands
from agentsound.bandlib import orchestra as orch
o = bands.symphony_orchestra(s)                     # string_quartet, chamber_orchestra, film_orchestra, church_organ
ANALYSIS = o.analysis                               # {'profile': 'classical'} ('film' for film_orchestra)
orch.perform(o, 'violins1', theme, verse)           # articulations by length, velocities -> the dynamics lane, early
orch.perform(o, 'violas', chords.articulate('tremolo'), build, shapes='cresc')          #   long notes, timing
orch.dynamics(o, orch.STRINGS, [(0, 'p'), (16, 'ff', 'smooth')], at=build)             # one lane for many roles
o.percussion.note(orch.PERCUSSION_KEYS['cymbal_roll'], climax.start - 4.2, 6, 96)       # swell peaks 3.5 s in
orch.ring(o, coda.bar(-1), length=2, db=5)                                               # the hall blooms at the end
print(o.describe()); o.info['articulations']['cellos']; o.info['sweet']['horns']       # how to play each role
```

| preset | roles | sounds | hall / master |
|---|---|---|---|
| `string_quartet` | violin1 violin2 viola cello | solo legato players (mono='legato'): VSCO 2 solo violin, SSO solo violin 2 / viola / cello (+ VSCO desk tremolo) | Musikverein IR x1.1 (~1.6 s); safety limiter |
| `chamber_orchestra` | violins1 violins2 violas cellos basses flutes oboes clarinets bassoons horns timpani | VSCO 2 CE chamber sections and solo winds (each wind role = the pair), timpani hit / roll | Musikverein x1.1 |
| `symphony_orchestra` | + trumpets trombones tuba percussion harp celesta | SSO 4.0 'Performance' sections (live mod-wheel dynamics, 8 string articulations), VPO re-looped viola / cello / bass sustains, VSCO oboe sustain, timpani, GM-style percussion, harp | Musikverein x1.25 (~1.9 s) |
| `film_orchestra` | symphony - celesta + low_brass drums choir (+ sub pulse with `hybrid=True`) | + SSO bass trombone, MuseScore taikos, SSO chorus 'aah' (`choir='oh'`: NBO, clean loops) | Musikverein x1.5, seated wider; master: mid dip, air, 1-2 dB glue, limiter |
| `church_organ` | soft principal full pedal pedal_full | Lars Palo Burea (`organ='pitea'`), each role a registration | St Nicolaes church IR (~3.6 s) |

- **Dynamics are a lane, not a velocity**: every sustaining role plays live dynamics (`instrument.dynamics`: SSO
  mod-wheel level + filter, VSCO p/f layers crossfaded at their recorded levels). `orch.perform` writes the lane from
  the written velocities (40 p, 78 mf, 95 f, 115 ff; notes of 2.5 s and more swell) - or pass `shapes`
  (`'cresc'`, `'dim'`, a list per note) for crescendi INSIDE held notes; `orch.dynamics` writes one curve on several
  roles. Velocity itself only shapes the attack. Struck roles (timpani, percussion, harp, celesta, taikos) play
  velocity; organ registrations have no dynamics (the swell pedal is `instrument.expression` on 'soft').
- **Articulations** per role in `o.info['articulations']`, the same core names everywhere (sustain, staccato /
  spiccato, pizzicato, tremolo, marcato, legato, harmonics, col legno, non-vibrato, muted where the library has them),
  switched per note by keyswitch: `clip.articulate('pizzicato', span=(8, 16))`. Levels are calibrated on renders
  (a short's loudest 100 ms against the sustain's body, same notes, same dynamics): staccato / spiccato -1 dB,
  pizzicato -2, tremolo -1, marcato +2; harmonics, col legno and mutes stay as soft as recorded.
- **Timing**: long notes start `o.info['lead_ms'][role]` early (strings 90 ms in the SSO sections), so the slow
  attacks sound on the beat; perform() places the part in song time first, so even a downbeat moves early.
- **Even notes**: the sample sets are uneven (VSCO 2 CE notes jump up to 15 dB between recordings, round robins
  more; SSO a few dB). The presets measure the samples when they are built and put every key range on a straight
  line over the keyboard (and VSCO's velocity layers into a dynamics stack whose softest layer is at most 14 dB
  down), so a scale at one dynamic stays level: a VSCO horn line no longer jumps +13 dB above C5.
- **Balance**: role gains calibrated at mf on renders, one line per role over its sweet spot (LUFS): a string
  section line, the woodwind lines ~3 dB softer, the brass for the chords they usually play; pp -> ff spans ~20 dB
  (15-23) in every section. Missing optional packs fall back at the same level (VPO sustains -> SSO sustains,
  VSCO oboe / timpani / percussion / harp -> SSO).
- **Measured on the demos** (`songs/_bands/<preset>`, 0 warnings each under the preset's profile, 0 clicks in the
  mix): string quartet -21.6 LUFS / LRA 13.1, a held A5 grows +14 dB inside the note, a held F5 falls -11 dB, the
  tremolo swells ~9 dB (no longer out of silence); chamber -20.9 / LRA 15.0 (A -29.4, B -24.4, C -17.7); symphony
  -20.6 / LRA 17.0 (intro -32.7, climax -16.4, close -32.5 LUFS); film -15.3 / LRA 14.9; organ -17.4 / LRA 20.1
  (intro -32.6, chorale -22.6, toccata -15.1 LUFS per section).

## Performance and humanisation

- **Timing**: sections breathe together but not quantised: ±5–15 ms jitter on shorts, larger (±20 ms) on soft
  sustained entries; the basses slightly ahead of the beat in fast music, solos free (rubato).
- **Velocity**: shape every phrase (arches), accents on metric strong beats, round-robins or ±6 velocity jitter
  on repeated notes (`vel_jitter`), no identical repeated velocities.
- **Chords**: stagger the notes of a sustained section chord by 5–20 ms (`clip.strum(ms=12, bpm=s.tempo)`), softer
  for inner voices; in divisi, give each half a different velocity.
- **Bow changes and breaths**: re-articulate held notes every 2–4 bars (split the note, small velocity dip) in
  strings; leave winds and brass a breath (an 8th rest) every 2–4 bars.
- **Vibrato**: sustained solo strings and winds need it (samples without vibrato: a delayed pitch LFO on the
  track, 5–6 Hz, depth 10–20 cents, fading in after 0.3 s).

## Solo piano from a score (Chopin nocturne etude: songs/nocturne-etude, NOTES.md has the numbers)

- **Play it with `agentsound.romantic`** (docs/COMPOSE_API.md "The romantic pianist"), not with the jazz arranger:
  the notes are written; the pianist shapes them. Fioriture as one gesture (`fioritura`, arch: the ends ~1.5-2x
  slower than the middle, 7-10 notes/s, lighter in the middle - an even grid reads as a sequencer), trills with a
  slow start and a Nachschlag into the next note (`trill`, ~10 notes/s on average), turns between the notes.
- **The left hand keeps time, the melody sings over it**: `accompany` (bass + two soft chords per dotted quarter,
  the bass ~1.2x the chords, chords slightly rolled), placed FIRST; the right hand `lean_on_long` + `cantabile`
  (long notes carry, the next note plays into the decay), `dynamics` (the score's marks and hairpins), then
  `melody_rubato` (the recording: melody vs bass at the bar lines spread +-47 ms; a lock-step render 8 ms).
- **Voicing**: the melody's pitch class ~0.65-0.75 of the chroma energy at the bar lines (the recording 0.67; a flat
  left hand at the melody's level 0.56): left-hand chords around velocity 35-40 under a melody at 60-100.
- **Tempo**: phrase rubato deep enough to be heard (`s.rubato(..., depth=0.1)` per two bars, breaths into the
  cadences): the recording's bar lengths vary with CV 0.13; depth 0.045 gave 0.04.
- **Pedal** per harmony (`pedal_changes`), cleared in chromatic runs and cadenzas (`flutter=`, to a half pedal:
  `flutter_to=0.6`).
- **Sound** (see also "Solo piano" below): for a close, warm, dry nocturne recording the Salamander
  (`inst.sfz(..., hammers=0.45, width=0.4)`, the melody track panned ~-0.5 so the treble is not right-heavy, string
  resonance off) matched it better than `sampled/recital_grand` (36 % wide vs 19 %, +3.8 dB brilliance); a concert
  hall IR (`bus/ir_concert_hall` at width 1.0, sends -10), a safety limiter only; analysis profile **`piano`**.

## Mix targets (profile `classical`; check report.json)

| measure | target | too little | too much |
|---|---|---|---|
| integrated loudness | −23…−16 LUFS (orchestra −20…−18, chamber / solo −22…−19, film cue under `film` −16…−10) | quiet, lost on phones | limited, lifeless |
| true peak | ≤ −1 dBTP (a safety limiter only: `fx.limiter(ceiling=-1.0)` without gain) | | squashed |
| peak-to-loudness (PLR) | ≥ 12 dB (typ. 15–20; dense sustained pads with no timpani / brass attacks read ~10: add accents, contrast) | `squashed` | |
| loudness range | 8–20 LU (4–22 accepted) | flat, no drama | pp inaudible on small speakers |
| reverb returns | 4–14 LU under the mix; tails at a stop above −30 dB | dry studio, sampled | distant, washy (> −2 LU) |
| width above 150 Hz | 25–80 % (15–110 accepted) | a mono orchestra | phasey |
| balance | little sub, full mids, natural top (no hyped air) | thin (no basses) | steely strings (presence > +3), mud from many sections (low mids > +5) |

- Start with no master processing but a −1 dBTP safety limiter; set levels with track gains. No bus compression
  on classical music (at most 1–2 dB of slow glue on a film cue).
- EQ sparingly: high-pass everything except basses, cellos, timpani, bass drum and organ at 40–60 Hz; a gentle
  −2 dB at 250–400 Hz on dense mid sections if `balance_lowmid_high`; −1…−3 dB at 2.5–4 kHz on violins if the
  top is steely; a small high shelf on the distant sections for depth.
- The report's `masking` warnings between doubled sections (violins I/II, cellos/basses in octaves) describe
  intended orchestral doublings: judge them by ear (is the melody still clear?), not by the number.
- `level_jump` infos at pp/ff changes are the drama, not a fault. `dull` (6–20 kHz more than 8 dB under the
  reference) is common with GM and SSO samples (an SSO-SF2 mockup read −7…−11 dB): prefer VSCO 2 CE, Philharmonia
  and the SSO 4.0 SFZs at higher velocities in loud passages, let violins, triangle and cymbals speak, and add a
  gentle high shelf (+1…+2 dB at 8 kHz) on the hall return before brightening single parts.
- `low_end_not_mono`: narrow the low sections and high-pass the hall (see "The hall") instead of forcing the mix
  mono.

## Film (orchestral hybrid) with profile `film`

Same orchestra, plus: low hits (taiko `inst.sf2('Taiko Drum')`, orchestral bass drum, a short sub sine), synth
pulses and drones (va), braams (low brass fff), risers. Mix louder (−16…−10 LUFS, PLR ≥ 8, LRA 5–20), a big hall
3–13 LU under the mix (keep low hits and sub out of the hall: send them to a short room or nothing), strong low end
(sub share like pop), a darker top than pop. A trailer master (−9…−7 LUFS) needs `ANALYSIS = {'profile': 'film',
'loudness': [-9, -7]}`.

## Solo piano

- Sound: `sampled/recital_grand` (Headroom C3 voiced for the hall: velsens 1.0, width 0.75, sympathetic string
  resonance 0.9, hall -11) with `ANALYSIS = {'profile': 'piano'}` - the `classical` curve is an orchestra's and flags
  every real solo piano recording (lowmid +13..+14 dB). Two tracks of the same patch, 'melody' (right hand) and
  'accomp' (left hand), with the same pedal lane: the report then judges the melody's dynamics as the lead.
- Voicing: the melody ~8 dB over the chords and ~4 dB over the bass notes (measured on a concert recording of
  Satie's Gymnopedie No. 1), touch() arcs of 30-45 velocity per phrase, the middle part / climax ~6 dB over the
  first statement.
- Time: `s.rubato(phrase, phrase='breath')` per phrase, ritardandi at the big cadences, `s.lilt(span, beats={2:
  0.06}, jitter=0.05)` for the pulse inside the bar (a slow 3/4's chord on 2 lingers), the bass ~25 ms before the
  melody, cadence chords rolled 30-40 ms, a fermata on the last chord.
- Pedal: a change on every harmony (up just after the new bass, down ~0.25 beat later: `pedal` steps); a half pedal
  (`instrument.pedal` 0.6-0.8) clears the treble and keeps the bass ringing.

## Études: learning from the masters (public-domain score + analysis-only reference)

An étude is a benchmark piece that finds the system's weaknesses by playing something whose every note is known and
comparing the result with a real performance. Independent of user feedback, it is repeatable and measurable:

1. **A public-domain score** (the composer died more than 70 years ago: Satie, Chopin, Debussy, Bach ...) written
   note for note as data (`songs/<slug>/<composer>_score.py`), never taken from an edition's typesetting or a MIDI
   file of unknown origin.
2. **A reference recording for analysis only** (the user's file in `assets/refrences/`, git-ignored): it is never
   copied, sampled or rendered into the song. Verify the notes against it: onset detection + template (NNLS)
   transcription with piano-note templates, what sounds after each chord, a plain render of the score analysed the
   same way (the analyser's own mistakes then cancel), and a per-bar chroma similarity against a shifted-bar
   baseline (the Gymnopedie: 0.93 vs 0.66). Where memory and analysis disagree, the analysis wins.
3. **Performance measurements on both** (bar downbeats of the reference from its detected bass onsets, of the render
   from its tempo map): tempo per bar (CV, local rubato, phrase-end broadening, final ritardando), beat positions
   inside the bar (mean / spread), deviation from a metronome, melody dynamics per phrase, melody over chord / bass,
   within-bar decay (pedal and resonance), a held note's decay, attack / sustain brightness - plus `agentsound
   compare` (tonal balance, LRA, width, correlation, tails).
4. **Before / after**: render the same performance with the tools as they were and with the fixes (an environment
   switch in song.py), list every clear gap with numbers, fix what belongs in the library (players, tempo helpers,
   patches, the sampler, analysis profiles) with tests, and leave the engine-sized ones as a written list in the
   étude's NOTES.md. Keep the benchmark songs (the jazz trio) bit-identical or sensibly unchanged.

`songs/gymnopedie-etude/NOTES.md` is the worked example (it added `Song.lilt`, rubato 'breath', the `piano` profile,
the sampler's sympathetic resonance and half pedal, and `sampled/recital_grand`).

## Checklist

- Sub-style, form, dynamics map and the one climax written down before any notes.
- Every part in its range and sweet spot; melody in one clear colour (or a classic doubling); bass line in
  octaves; harmony voiced by the harmonic series; inner voices voice-led.
- Articulations chosen per passage (sustain / staccato / pizzicato / tremolo tracks); phrases shaped with velocity
  and `gainDb` swells; long notes re-articulated; breaths for winds and brass.
- Sections seated in the stereo field; depth via send, level and a softer top; one hall (+ early room).
- `ANALYSIS = {'profile': 'classical'}` (or `'film'`); loudness −23…−16 LUFS, PLR ≥ 12, no limiting.
- Credits for CC-BY / Sampling Plus / BY-SA packs in the song docstring and the delivery message.
