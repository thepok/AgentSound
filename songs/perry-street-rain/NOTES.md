# Perry Street Rain - production notes

Original straight-8th piano-trio tune, Ab major, 96 BPM (rubato intro, ritardando + fermata at the end), ~4:30 +
room tail. The user's wish: "New York Bar Jazz, aber ohne Swing" - late-night bar trio (piano, soft brushes,
upright bass), but even 8ths (after "lanterns-on-carmine": the lazy medium swing was not their taste,
recipes/HUMAN_FEEDBACK.md). Band: `bands.make('jazz_trio', feel=jazz.Feel(96, ratio=0.5, layback={'piano': 9,
'comp': 5, 'bass': -2, 'drums': 0}))` - Salamander Grand (right hand + comping), Meatbass pizz, Swirly Drums brushes,
salon IR room. Analysis profile `jazz`. Checked in the render JSON: off-beat 8ths sit at .51 beat (straight + lay-back).

## Form (106 bars, AABA 32)

| section | bars | what happens |
|---|---|---|
| intro | 4 | piano alone, rubato, pedalled: rolled Dbmaj9 Cm9 Bbm9 Eb7sus4-Eb7b9 (LH root-5th, RH 3-4-note grips), a trill on the Cm9's 9th (D-Eb, pedal lifted), a turn on the high C of bar 3, an Eb7b9 arpeggio sweep down into the head; a brush swell |
| head | 32 | the melody played by the pianist (`pianist.arrange`, see below): harmonized phrase by phrase, ornaments on the long notes, fills in the gaps; the left hand (guide-tone shells in A1/A2, rootless voicings from the bridge) replaces the separate comping; bass in a straight two, then dotted-quarter "push" motion from the bridge; brushes: stirs per beat + taps 2/4, from A2 ghost taps on the &s and a feathered even-8th kick (1, &2) |
| piano_solo | 32 | A1 the motif (sparse: guide tones, answers, a pentatonic run, turns) over LH shells, A2 a `jazz.solo_line` (the hook as motif) with a chromatic run and a scale run in its gaps, a trill, crushes, B two-handed (locked hands / drop 2 / octaves, rolled, tremolos, turns, re-struck voicings; LH rootless), A3 = the climax: the hook an octave up (octaves + inner tone, locked hands), trill, slip notes, tremolo, repeated notes, the block-chord shake on the last long note, alternating-hands and octave-run fills (ride in even 8ths + digs, crash, bass in 8th-note "drive") |
| bass_solo | 16 | the Meatbass quotes the hook two octaves down and sings over the A changes (four pitch-bend slides), piano whispers rolled shells, brushes only stir; swell into the head out |
| head_out | 16 | a glissando-like Ab13 sweep at the end of the bass solo into the head out; the bridge lush (drop 2, close, upper structures, arpeggio sweeps, rolls, turns), the last A quietly (guide tones, single notes, turns, a trill) |
| tag | 4 | backdoor tag Bbm9 Eb13 / Cm7 F7alt / Bbm9 Eb7sus4 / Dbm6 Gb13 as a ballad (drop 2 / quartal, rolled 15-25 ms, LH rootless), ritardando |
| end | 2 | Abmaj9#11 rolled from the left hand up to Eb6, bass Ab1, fermata, soft crash + dying stirs, the room send opens |

## Harmony

- A1: `Fm9 | Dbmaj7#11 | Bbm9 | Eb7sus4 Eb7b9 | Abmaj9 | Dm7b5 G7b9 | Cm9 F7b9 | Bbm7 Eb7sus4`
- A2/A3: bars 6-8 `Cm7 F7b9 | Bbm9 Eb13 | Abmaj9 Ab13` (cycle of 5ths home, Ab13 = V of the bridge's Db); A3 turns
  around with C7alt (into the solo) or F7alt (into the tag)
- B: `Dbmaj9 | Gb13#11 (backdoor bVII) | Cm9 | F7alt | Bbm9 | Dbm6 (borrowed iv) | Emaj7#11 (chromatic) | Eb7sus4 Eb7b9`
- Melody: the hook rises through Fm9 to a held 9th (C Eb G), sighs back (F Eb C), is sequenced a third lower over
  Bbm9; resolutions by guide tone (Ab-G over G7b9, Gb-F over F7b9, E-Eb over Eb7b9 -> Abmaj9). Strong-beat notes
  checked against the chords (only 9ths / #11s / 13ths as deliberate tensions).

## The pianist (user feedback 2026-09-30)

"es ist, als würde ein Kind Taste für Taste drücken beim Lead - zu simpel" and "es gibt doch da so schöne Moves, z. B.
wo zwei Tasten sehr schnell abgewechselt werden". The melody had been a bare single-note line (touch() dynamics on
top). New library module `agentsound/pianist.py` (also `jazz.pianist`): named moves + an arranger; every piano part
of the song now goes through it (`hands()` in song.py: `pianist.arrange(touched melody, P[part], bpm, key, style,
density, lh, seed)` -> right hand on `piano`, left hand on `comp`, the piano pedal with the harmony, lifted for runs
and trills; `ARRANGED` keeps each Arrangement for inspection).

| part | style / density | what the arranger chose (seeded) | harmonized |
|---|---|---|---|
| head A1 | straight 0.45, LH guide | close, 6ths, quartal; a blues crush (E into F over Dbmaj7#11), a Bbm pentatonic run into bar 3, a turn, a crush, a re-struck voicing | 89 % |
| head A2 | straight 0.6 | drop 2, close, quartal, 6ths, guide; 2 tremolos, a trill, 2 turns, a restrike; a run and an arpeggio sweep in the gaps | 92 % |
| head B | straight 0.85, LH rootless | octaves, quartal, drop 2, 6ths; 2 tremolos, a restrike; a run, cascading 4ths | 95 % |
| head A3 | lush 0.6 | close, drop 2, ust, octaves, quartal; rolls, a restrike; 4ths cascades | 83 % |
| solo A1 | sparse 0.55 | guide / single; turns, a crush, a pentatonic run | 37 % |
| solo A2 | straight 0.6 (solo_line) | single / guide / 3rds; trill, mordent, crushes; chromatic run + scale run | 56 % |
| solo B | lush 0.85, LH rootless | locked, drop 2, octaves; tremolos, turns, restrike | 96 % |
| solo A3 | bar 0.9 climax | octaves, drop 2, locked; trill, slip notes, crushes, tremolo, repeated notes, the shake; hands / octave-run / chromatic fills | 91 % |
| head out B | lush 0.85 | drop 2, close, ust; turns, rolls, restrike; arpeggio sweeps | 95 % |
| last A | sparse 0.45 | guide / single; turns, a trill; a pentatonic run | 49 % |
| tag | ballad 0.55 (moves timed for the ritardando) | drop 2, quartal | 91 % |

Concrete bars: head A1 bar 1 C5 over Eb4 F4 Ab4 (close Fm), then Eb5 over Ab4 and G5 over Ab4 Eb5 (6ths) - the hook
now sounds in chords, the left hand Eb3 Ab3 under it; bar 2 ends with the blues crush E5 into F5 over Dbmaj7#11 and
a pentatonic run F5 Eb5 Db5 Bb4 Ab4 F4 into bar 3. Solo A3 bar 7: Db6 trilled against Eb6 over Db5 Ab5, ending with
the turn C6 Db6; bar 8: the Ab5 shaken against the minor 3rd above over F4 C5 Eb5, an octave run up Ab4 .. E5 into
the crushed Gb5 of the C7alt turnaround.

## Performance / technique

- Piano (before the pianist pass; still true for the intro, bass solo and ending): every comping chord rolled (8-22 ms, 25-45 in the tag, 60-80 ms intro / final chord); crushed grace notes
  before long melody notes (head A2/A3, solo, tag); locked hands (solo bridge), drop-2 block chords (head-out
  bridge) and octaves (solo A3) as the climaxes; pedal changing with the harmony in intro / head / head out / tag,
  held into the last chord; a paraphrased last A.
- Bass (`even_bass` in song.py): straight-8th jazz lines - root on 1, fifth / tenth / octave inside the bar, an
  8th-note chromatic or fifth approach (sometimes an anticipation tied over) on the & of 4; 'two' -> 'push' ->
  'drive' as the tune builds; a written solo with slides.
- Brushes (`even_brushes`): the preset's stirs one per beat + taps and hat foot on 2 and 4, plus even-8th colour
  (ghost taps on the &s, feathered kick 1 / &2, brush 8ths on the closed hat in the solo, the ride in even 8ths with
  digs on 2 and 4 for the climax), 8th-note fills every 8 bars. Drums sit 15-16 dB (RMS) under the piano per section.

## Mix / analysis (final render)

-15.6 LUFS-I, TP -1.2 dBTP, LRA 5.4 LU, width >150 Hz 42 %, reverb -17.0 LU, 0 clicks, 0 warnings, 0 info (before the
dynamics pass below).
Sections (LUFS-I): intro -20.0, head -16.1, piano solo -14.3 (climax), bass solo -18.6, head out -15.4, tag -16.9,
end -20.7. Tracks: piano -19.7 LUFS, comping -28.4, bass -23.8, brushes -35.2.

Iterations: (1) LRA 4.5 and the top end -7 dB vs the jazz reference -> head A1/A2 softer (piano velocity, brushes),
the solo's block chords and octaves louder, comping intensity up; high shelves on the piano (+2.5 dB at 4.2 kHz),
the comping (+1.5) and the master (+2.5 dB at 8 kHz, before the preset's chain: the salon IR is dark); the bass solo
lift -2 -> -3 dB; the final chord's left hand thinned to Ab2 Eb3 G3 and the right hand moved up (piano / comping
lowmid masking on the last chord). -> 0 warnings.

Dynamics pass (user feedback 2026-09-30: "the lead notes all sound equally loud"). Measured on the piano stem (476
note onsets from the render JSON, 97 % confirmed by a spectral-flux detector; peak of a 5 ms RMS envelope per onset):
the onset levels already spread 5-7 dB per 4-bar phrase, but that spread was register / sample layer / pedal wash,
not touch - per phrase r(velocity, onset dB) 0.12 in the head, 0.07 in the solo, velocity-explained range 0.7 dB
(head) / 0.4 dB (solo). The written velocities changed between sections (39-104 overall) but not inside a phrase (head
A1 63-71, B 83-89: ph() wrote one level per chorus, no accents). The piano path has no compressor (the ratio-2.5 one
is the bass's); the master limiter (preset drive 5.5 dB) shaved the solo climax (onset spread 6.8 dB into the
master, 4.9 dB out). Fix: `jazz.touch()` (new, humanize.py) writes the melody velocities from the line - each
phrase rises to its top note and relaxes, syncopations lean, passing / pickup / grace notes stay light, octaves and
block chords voiced to the top; head A1 46-94 < A2 50-100 < B 56-110 > A3 52-106, solo 56-104 / 60-110 / block
chords 72-114 / octaves 74-114, head-out bridge 70-114, last A 50-92, tag 46-86; intro inner voices ~50 under a
64-88 top line, the final roll 60 (LH) / 72-100 (RH, Eb6 on top), bass-solo comping vel 44-46. Piano trimmed 2.5 dB
(touch plays ~3 dB louder on average), master drive 5.7. After: per phrase r 0.76 (head) / 0.65 (solo),
velocity-explained range 7.0 / 6.6 dB, onset spread per phrase median 8.2 dB head (6.4-13.5), 9.0 dB solo (4.6-13.1;
the locked-hands chorus is the narrow one), tag 11.6 dB; in the mix 7-10 dB in head and solo A1/A2, 2.5-3.5 dB in
the dense climax (ride, bass drive, busier comping fill the gaps - the master takes ~1.5 dB more there). Drums RMS
13.2 / 15.4 / 16.7 dB under the piano (head / solo / head out). Final: -15.7 LUFS-I, TP -1.2, LRA 5.6 LU, 0 clicks, 0
warnings (info: the piano track peaks +2.1 dBFS before the master, float), no audible pumping in the level strips.

Pianist pass (2026-09-30): the harmonized right hand + held left-hand shells made the head 1.3 dB louder (-14.8
LUFS, the arc to the solo only 0.5 dB) and put the brushes 17 dB under the piano -> head touch lowered (A1 46-88,
A2 48-94, B 54-104, A3 50-98; inner voices x0.76), head-out bridge 66-108, last A 48-88. Final: -15.4 LUFS-I, TP -1.2,
LRA 5.8 LU, 0 clicks, 0 warnings (info: the piano track peaks +0.2 dBFS before the master, was +2.1). Sections: intro
-19.9, head -15.3, piano solo -14.3, bass solo -18.5, head out -15.4, tag -16.1, end -17.7. Track RMS per section
(piano / comp / bass / drums): head -24.3 / -32.6 / -25.3 / -39.6, solo -21.9 / -31.3 / -24.7 / -37.5, head out
-24.0 / -32.7 / -25.7 / -40.3 -> brushes 15.3 / 15.6 / 16.3 dB under the piano. Low-mid: the right hand stays above
C4 (floor 60) whenever the left hand plays, the left hand in C3..C4 (guide shells / rootless), the comping track now
carries only that left hand (-32.8 dBFS RMS, was -32.0 with jazz.comp); balance vs the profile lowmid +0.7 dB, mid
+1.1 (were +0.1 / +0.4 with the single-note line) - no masking warning, the runs and sweeps read clearly in
spectrogram_03 (bars 47-49).

## v4: fewer fast alternations, a warmer piano (user feedback on v3, 2026-09-30)

"nice nice ... etwas zu viele von diesen schnellen Zwei-Tasten-Wechseln ... sonst cool", then "man könnte es etwas
smoother machen, es klingt hart" - "eine Sound-Design-Frage, nicht so sehr Structure".

- **Ornament budget** (`pianist.arrange`, system level): the fast two-key alternations (trill, tremolo, shake, repeated
  notes, alternating hands) at most ~1 per 16 bars, never in neighbouring phrases, never two of a kind within 32
  bars, only at structural moments; the other ornaments at least 1.5-3 bars apart. One `pianist.Memory()` for the
  whole song (`hands()` passes `memory=, at=`), the intro trill booked on it (`played`), the fast budget saved for
  the climax (`save(solo.bar(31))`); the last A (sparse, no fast figures by default) gets `fast_every=16` for its
  final trill. Same seeds, everything else as v3 (devices, fills, runs, sweeps, gliss, left hand, dynamics: the
  substitutes come from a side random stream).
  Arrangement log: v3 **14** fast figures (4 trills, 7 tremolos, 1 shake, 1 repeated-note figure, 1
  alternating-hands break) + the intro trill -> v4 **3** + the intro trill: the tremolo on the tonic at the end of
  head A2 (bar 8, into the bridge), the shake on the climax's last long note (solo A3 bar 8; the A3 bar 7 trill and
  the bar 5 tremolo gave way: same 16 bars), a trill on the last note of the head out (A3o bar 8). Dropped ones
  became re-struck voicings, turns, crushes, rolls or a chromatic run. Other ornaments 26 -> 22 (turns 11 -> 9,
  crushes 7 -> 4), restrikes 6 -> 9.
- **Light ornaments**: figure notes 25-40 velocity under their principal (median drop per ornament 13-18 -> 22-32:
  trill 13.5 -> 25, tremolo 15 -> 25.5, shake 13 -> 32, turn 18 -> 22), swelling in and fading, legato, the pedal
  down, a soft landing; runs one gesture (lighter in the middle).
- **Piano sound** (the jazz presets, library level): `sampled/jazz_grand` (the Salamander with softened hammers,
  `inst.sfz(..., hammers=0.75)`: per velocity layer -5 dB at 3 kHz / -7 dB at 7.5 kHz on the top layer, a little
  clearer soft layers, the loud layers' level kept), the 3 kHz boost of the preset chain reduced to a broad +1 dB,
  air at 11 kHz, 1 dB more low-mid cut on the right hand, a fast soft-knee compressor on the loudest attacks (1.6:1
  over -12 dBFS, 70 ms), a touch of tape, the piano 1.5 dB further into the salon room; the song's piano shelf moved
  from +2.5 dB at 4.2 kHz to +2 dB at 5.5 kHz, PIANO_TRIM -2.5 -> -2.2. Piano stem, v3 -> v4: loudest 60 hits
  spectral centroid 1172 -> 1042 Hz, their 2-5 kHz share -14.2 -> -16.8 dB, their onset crest 11.8 -> 11.1 dB;
  whole stem 2-5 kHz share -13.5 -> -15.1 dB, centroid 878 -> 824 Hz, 150-500 Hz share -7.9 -> -7.6 dB (no mud).
  The solo spectrogram shows the vertical 2-10 kHz attack streaks of the climax clearly darker. Piano note dynamics
  8.3 -> 7.8 dB (audio 8.8 -> 8.3, from velocity 8.5 -> 8.9 dB).
- Final: -15.5 LUFS-I, TP -1.2, LRA 5.4 LU, 0 clicks, 0 warnings (1 info: the bass's flat dynamics, as before).
  Sections v3 -> v4: intro -19.9 -> -20.3, head -15.3 -> -15.4, solo -14.3 -> -14.6, bass solo -18.5 -> -18.4,
  head out -15.4 -> -15.2, tag -16.1 -> -15.9, end -17.7 -> -18.1. Balance vs the jazz profile: presence -3.9 ->
  -5.2 dB (the glass is gone; brilliance -5.9 and air -2.9 as before). The other jazz presets' demos
  (songs/_bands: trio, quartet, ballad, bossa) render within 0.2 LU of before with the same report findings.
Bass dynamics pass (2026-09-30, library fix): the dynamics ear read the bass flat - 3.8 dB note spread per phrase,
0.0 dB explained by the velocities (57-103). Causes: the Meatbass file ramps each velocity layer to full level at its
top (velocity 96 played ~3 dB louder than 103; 57..103 spanned ~4 dB) and the preset's compressor (-22 dB, 2.5:1,
automakeup) sat ~10 dB into every note. Now: the layers evened to one (v/127)^2 response (sampled/upright_bass v2),
a peak catcher + fixed makeup instead of the compressor, every bass line through jazz.bass_touch (4-bar arcs, root
on 1 leading, lighter pickups / approaches, lo 0.84 / hi 1.22 x vel), the bass solo through jazz.touch(68, 96), the
section velocities re-set for the same levels (head 81-92, solo 86-96, head out 93 / 81, tag 82, last note 92), the
left hand following the right hand's level. After: bass 6.8 dB per phrase (velocity response 2.1 dB per 10 steps),
comp 3.7 dB (was 2.0), piano unchanged 8.3 dB; bass RMS per section within +-0.2 dB of before, bass 3.8 dB under the
piano (integrated); -15.4 LUFS-I, 0 clicks, 0 warnings (info: node_hot piano, as before).

No jazz reference audio exists in assets/refrences, so no reference comparison was run.

## Credits

Salamander Grand Piano V3 by Alexander Holm, CC-BY 3.0 (attribution required when publishing); Karoryfer Meatbass
and Swirly Drums (CC0); Voxengo IM Reverbs (royalty-free IR).
