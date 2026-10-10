# Cellar Hours - arrangement

**Frame:** F minor, 108 BPM, 4/4, swing 0.58, 90 bars, 3:30. Solo piano (right hand `piano`, left hand `comp`).

## The material
- **a** (A bar 1, Fm9): `G5/4. F5/8 Eb5/8 C5/8~ C5/4` - the 9th resolving to the root, the 7th, a skip to the 5th
  held across beat 4.
- **b** (A bar 2, Bb13): `r/4 D5/8 G5/8~ G5/2` - a breath, a 4th up to the held 13th.
- Phrase 1 = a b a' b': a' a step down over Ebm9 | Ab13 with its third note re-fitted (C, the 3rd of Ab13), b'
  widened to a 5th, its G now the #11 of Dbmaj7. Phrase 2: Bb C Db (Gm7b5) climbing to the A's peak Eb6 (the #9 of
  C7alt), the alt line Db Ab E, E -> F (the leading tone) and the landing on Ab.

## Form
| section | bars | harmony | energy | what happens |
|---|---|---|---|---|
| intro | 4 | Bbm9/F Fm9 Gbmaj7#11 C7sus4 C7b9 | 1 | b developed over the vamp (F-C, Eb-Ab, F-C), rubato, LH tenths |
| head A1 | 8 | Fm9 Bb13 Ebm9 Ab13 Dbmaj7#11 Gm7b5 C7alt Fm9 Db7#11 C7b9 | 2 | the theme, soft (touch 42-80) |
| head A2 | 8 | ... Fm9, Cm7b5 F7#9 | 2 | restated to bar 6; the cadence rises to C6 and turns through F7#9 (Gb Ab) into the bridge |
| head B | 8 | Bbm9 Eb13 Abmaj9 Dbmaj9 Dm7b5 G7alt Gm7b5 C7alt | 2 -> 4 | low and slow (half notes + quarter-note triplets, Bb4-G5, 40-72); then Ab C F6 tied over the bar into G7alt: the head's peak; a chromatic fall home (B -> Bb, E F -> G) |
| head A3 | 8 | ... Dbmaj7#11, Gm7b5 Gb7#11 | 3 | the deceptive cadence (F G over Dbmaj7#11), the tritone sub, C6 (#11) left hanging |
| solo A1 | 8 | A1 | 2 | a quoted 2.5 beats late; target notes D (3 of Bb13), Gb (b3 of Ebm9), the F held over the change into Dbmaj7, an enclosure F-Eb -> E, the alt line to Db -> C; single notes + guide tones |
| solo A2 | 8 | A2 | 3 | a in quarter-note triplets (call), an 8th answer turning at Ab; the call a step down, a long rising answer; a dense line from Db6 to the cadence; A Ab (3, #9) over F7#9 into the bridge |
| solo B | 8 | B | 4 | a target-note chain Db -> G -> C -> F (enclosures Ab-F#, Db-B, G-E), the bridge's quarter-note triplets quoted (Ab C Eb), a long line from F6 down and up to F6 again over Gm7b5 |
| solo A3 | 8 | A3 | 5 -> 3 | THE peak: a from Ab6 (v123), b an octave up (G6), then a descending line (touched in pieces: 64-124, 60-112, 50-100) to the cadence; ends Bb5 -> Db5 over Gb7#11 = the first note of the head-out's bridge |
| out B | 8 | B | 3 | the bridge again (44-76, then 52-98) |
| out A3 | 8 | A3 | 2 | thinned by hand: a held longer, the peak given up (Db6), the last bar open; ballad voicings (38-80) |
| tag | 4 | Bbm9/F Fm9 Gbmaj7#11 (2) | 1 | the intro's vamp, but it stays on the Neapolitan: Db Bb F falling into the tonic, ritardando |
| end | 2 | Fm6/9 | 1 | spread (LH 130 ms, RH 120 ms, after half a beat), G on top; then G6 F6 softly (a's first two notes) into the room |

## Players
- `jazz.chorus` per section = `pianist.arrange` per part; one `pianist.Memory(once=True)` for the piece (every fast
  figure at most once: one trill in the head-out bridge).
- Head: style `straight`, LH `shell`; the A's from the same dice (a theme restated: seed 101), `anticipate=0.05`,
  `delay=0` (the written syncopations stay where they are), fills 0.3, embellish 0.25.
- Solo: `anticipate=0`, `delay=0`, `fill=0.12` (the line is the solo), devices by part: single+guide -> +thirds /
  sixths -> guide / drop2 / quartal on the bridge's long targets -> octave / drop2 / guide at the peak, `doubles=0.78`
  (no `climax=True`: no block chords on every note).
- Section sweeps (perform.build's rule) only where a whole bar would be empty (none fired).

## Needs from sound design
None beyond the endless jazz-piano sound (locked for the comparison): RH Ab3-Ab6, LH F2-F4.

## Revisions (A&R rounds 1-2)
- Each A's bars 6-8 have their own rhythm (A1 half note + quarter-triplet answer and a bVI7 turnaround; A2 a rise to
  Eb6 and a quarter-triplet fall A Ab Eb into the bridge's Db; A3 a long F over the deceptive chord, a G pickup).
- Solo: each ii-V its own territory (A1 low from below, A2 a turning line from Bb4, A3 the peak's descent); the bridge
  phrased 2 + 2 + 4 under a rising ceiling (Eb6, F6 only in bars 57 / 59), one enclosure (C-Bb -> B), a half-empty
  last bar and a leaned-on Eb6 pickup into the Ab6; the solo's last bar Cm7b5 F7#9 (part A3S) into the head-out
  bridge; bar 44 rises through Db7.
- No fast ornaments in the intro or the head-out bridge; a hand-voiced Fm6/9 (F C Ab | Ab C D G) instead of the
  endless end chord; `check_melody()` (composer.melody_issues) runs in build(): clean.
