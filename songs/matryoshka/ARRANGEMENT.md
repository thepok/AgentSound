# Matryoshka - arrangement

## Frame

100 BPM, 4/4, straight 8ths. 86 bars, 3:27.6 + a 7 s tail; a ritardando (to 86 BPM) over the last two coda bars
into the final chord. Keys: C major (bars 1-28 incl. intro) -> A minor (8) -> F major (16) -> G major (16) -> C major
(coda + end, 18).

## The hook and its scales

`HOOK = '8:1/4. 6:1/8 4:1/4 5:1/4'` in each key's degrees (C: C A F G; Am: A F D E; F: F D Bb C; G: G E C D).

- x1: the piano melody (every chorus bar 1 / 5, the build's bar 3, every coda bar).
- x4: the chord cycle `cyc(I, vi, IV, V)` = 1.5 + 0.5 + 1 + 1 bars; the bassist's kick grid `x.....x.x.......`
  = the hook's onsets (1, &2, 3; its 4th note is the backbeat), the drummer's kick locked to the bass.
- x2 / x1 in the build: the harmony zooms in (`cyc(..., scale=2)`, then `scale=1`: chords C Am F G under each note
  of the hook, the band hitting its rhythm), then Gsus4 G and a one-beat breath.
- x16 in the coda: the choir line C (6 bars) A (2) F (4) G (4) in octaves (sopranos C5, basses C3; sung in 2-bar
  breaths), the x4 line on bass (C2 A1 F1 G1) and the solo cello (C4 A3 F3 G3), the hook x1 on the piano (C5, then
  C6, then in octaves) - five octaves of the same notes, all on G in the last bar -> C.
- x64 = the form: section I 24 bars (verse1 + build + chorus1 + turn), II 8, III 16, IV 16.

Derived material (the same four notes): the diatonic inversion (steps +2 +2 -1: G B D C, C E G F) = the verse
tune (`VERSE`) and the violin descant of chorus 4 (G5 B5 D6 C6 at x4); the hook from the 6th degree (A F D E: the
minor key's hook heard in every chorus bar 3); the upward-leap form (1 -> 6 up a sixth: F5 D6 Bb5 C6 / G5 E6 C6 D6)
for choruses 2-4; the hook x4 as a violin descant on top of verse 2 (F5 D5 Bb4 C5).

## Form

| section | bars | key / harmony (roots = the hook) | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 4 | C: Cadd9 Am7 Fmaj7 Gsus4 | 1 | piano (sparse, tenths LH), pad filtering open | the chorus melody an octave down: the hook in the first second |
| verse1 | 8 | C: C Am7 Fmaj7 G / Cadd9 Am F Gsus4 | 2 | piano (verse tune = inversion, shell LH), pad, bass (pop, verse), drums half-time | the rising "question" |
| build | 4 | C at x2, then x1, Gsus4 G | 3 | piano octaves (the hook x2, then x1), band hits, drummer build | the zoom: the harmony compresses to the melody's scale; a one-beat breath |
| chorus1 | 8 | C: C Am F G / C Am7 Fmaj7 G | 4 | piano hook C6 (octaves / 6ths / 3rds), strings from bar 5, drums full | the hook, answer, the hook from A, lift; ends on a held G |
| turn | 4 | C Am F G E7/G# | 3 | piano (sparse), strings, pad, drums post | the hook, the answer, the minor key's hook low, B -> G#: into A minor |
| minor | 8 | Am: Am F Dm E / Am Fmaj7 Dm E C7/E | 1.5 | solo cello (the hook A4 F4 D4 E4), piano tenths, strings; drums from bar 5 half-time | cycle 2: the piano takes the hook high, the cello counters; G# melts to G over C7/E |
| verse2 | 8 | F: F Dm7 Bbmaj7 C / Fadd9 Dm Bb Csus4 | 2.5 | piano verse tune in F, violin descant (the hook x4 on top), shaker, strings | the verse again, new key, new colour |
| chorus2 | 8 | F: F Dm Bb C / F Dm Bb C D | 3.5 | piano upward-leap hook, strings, tamb + claps | last bar C -> D: the climb into G |
| chorus3 | 8 | G: G Em C D x2 | 4.5 | everything, piano octaves higher | the climax |
| chorus4 | 8 | G: G Em C D / G Em7 Cadd9 Dm7 G7 | 5 | + choir chords, violins (the inversion x4), glass layer on the piano, pianist climax | Dm7 G7: home |
| coda | 16 | C: 4 x4-cycles (C Am F Gsus4 / C Am F Gadd9 / F/C Dm/A F G7 / C Am7 Fadd9 G) | 2 -> 4.5 | bars 1-8 no drums: piano hook low (x1), bass + cello x4, choir x16; strings from bar 5; drums, tamb and the glass layer from bar 9; pianist climax from bar 9 | the revelation; ritardando in the last 2 bars |
| end | 2 | C | - | rolled piano chord, bass, cello, choir, strings, pad; drummer's final hit | one chord |

## Transitions

- intro -> verse1: the pad's filter opens; the verse's first note answers the intro's held G.
- build: drummer 'pre' role (snare build), a one-beat breath (bass, pad, strings, perc cleared) before chorus 1.
- chorus1 -> turn: a held G5 (half cadence), drummer fill.
- turn -> minor: G -> E7/G# (bass G G# A), the melody B4 -> G#4 -> the cello's A4.
- minor -> verse2: E -> C7/E (the E held in the bass, rising to F), melody G#5 -> G5 -> F.
- chorus2 -> chorus3: Bb | C D -> G (melody C6 A5 F#5 -> G5), drummer fill + crash.
- chorus4 -> coda: Dm7 G7 -> C (melody B5 D6 -> C6), the drums drop out for 8 bars.

## Players

- pianist (`pianist.arrange`, one `Memory`): intro / verses / turn / coda start `style='sparse'` with guide / thirds /
  single devices and a left hand (tenths / shell); choruses `ballad` with the hook devices (octave, sixths, thirds,
  close, drop2) and doubles at 78 % under the top note; the build `straight` with octaves; the minor section `ballad`
  with tenths; chorus 4 and the coda's last 8 bars `climax=True`. Ornaments restricted to restrike, roll, turn, crush,
  mordent, rare trill (fast figures budgeted by the style). Pedal from `arr.pedal`, the final chord rolled 45 ms.
- drummer (`drummer.arrange`, style pop, density 0.5, ending hit, `lock=bass`): plan per section (verse1 half time,
  build = pre, turn = post, minor = bridge half, coda = outro half); cleared in the intro, the first half of the minor
  section and the first half of the coda.
- bassist (`bassist.arrange`, style pop, `kick='x.....x.x.......'`, one `Memory`): verse / pre / chorus / break parts
  per section and key; the coda's x4 line written out (sustained roots in the hook rhythm).
- bow player (`hornist.arrange`, family strings, style ballad): the solo cello's hook in A minor + counter-line, and
  its x4 line in the coda (air, vibrato on held notes, lean-ins on the cycle starts).
- strings / pad / choir: block chords with 4-bar arches (`arc`) and crescendos; the choir's x16 line hand-written
  with a `dynamics` swell.

## Needs from sound design

- Hook: bright, high, present piano from C4 to C7 (hero piano_pop), velocity response kept (the chain costs ~1 dB of
  contrast: accents 20-30 velocity apart - touch() ranges 68-120 in the choruses).
- Choir: mixed "ah" with live `dynamics`; the x16 line sits at C5 (sopranos) + C3 (basses) - must stay audible
  under the band in coda bars 9-16.
- Cello: legato, live dynamics (the x4 line in the coda must read as a melody, not a pad).
- Glass layer: only in chorus 4 and the coda's last 8 bars.
