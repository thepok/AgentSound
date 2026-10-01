# Ghosts of Ocean Drive - arrangement

## Frame

104 BPM, B minor (last chorus C# minor), 4/4, straight 8ths. 124 bars, ~4:46 + an 8 s tail. Verse 1 half-time,
choruses four on the floor (the drummer's synthpop machine style).

## Form

| section | bars | harmony | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 8 | Gmaj7:2 A6:2 Bm9:2 Asus4 A | 1 | pad (filter opening), glass arp (lp opening), hero piano (bars 4-6), hats from bar 5 | the hook cell teased far away, soft (vel 46-70); shimmer bloom |
| verse1 | 16 | Bm G D A Bm G Em A (x2) | 2 | drums half-time, bass (bassist synth, verse), pad, e-piano comp, hero piano | the verse tune (lower, sparse: single notes / guide tones), a half cadence on E, then up to A |
| pre1 | 8 | Em:2 G:2 A:2 F#7sus4 F#7 | 3 | + strings swelling, e-piano 8ths crescendo, drum build, riser (bars 5-8) | the ladder melody in 3rds / 6ths for 7 bars, then the hook voice rests for a bar (the chorus arrives from a hole); a one-beat breath before the chorus |
| chorus1 | 16 | G A Bm D G A Em F# + G A Bm D G A Bm:2 | 4 | four on the floor + claps, crash, bass drive, pad, e-piano, 8th arp, impact | THE hook: octaves / sixths under it (doubles at 75 %), first statement vel 70-108 |
| interlude | 4 | G A Bm D | 3.5 | groove on, e-piano | the hook cell once more (returns between sections) |
| verse2 | 8 | Bm G D A Bm G Em A | 2.5 | drums (energy 0.42), bass, pad, e-piano on two chords a bar | the verse tune again, a little louder, a new ending up to A (revision: thinner, the arp waits) |
| pre2 | 8 | as pre1 | 3.5 | + the 16th arp from bar 5 (crescendo), brass stabs in the last 2 bars, riser | the ladder in drop2 voicings for 6 bars; the brass hits take the last 2 while the hook voice rests |
| chorus2 | 16 | as chorus1 | 4.5 | + choir (2nd half), strings, brass off-beat stabs, glass arp (2nd half), 16th arp | the hook harmonized, more octaves (74 % voiced), vel 74-112 |
| breakdown | 8 | Gmaj7:2 E:2 D:2 Asus4 A | 2 | drums stop (band hit, then time), bass roots, pad, strings, choir, glass arp, shimmer up | the hook at half speed, G -> G# over the Dorian major IV (E major): hope; both hands (tenths) |
| solo | 8 | G A Bm D G A Em G#7 | 3.5 | drums half-time (energy 0.45), bass, pad, soft strings swelling in bars 5-8, e-piano long chords, riser (bars 5-8) | the hero sax solo in front of a lighter band, climbing to F#5, landing on G#7 = V of C# minor |
| chorus3 | 16 | A B C#m E A B F#m G# + A B C#m E A B C#m A | 5 | everything, crash, impact | the hook a whole step up, the pianist's climax (octaves / locked hands), vel 78-118; the last bar turns to A (the pivot home) |
| outro | 8 | G A Bm D Gmaj7:2 Bm9:2 | 1.5 | drums 4 bars then out, bass rings, pad / strings / glass fade | the sax sings the cell as a farewell, the piano answers it (bar 4), a rolled Bm(add9) chord rings out |

## The hook

Degrees of B minor (8 = B5): `5 6 8 8 7 6 | 6 7 9 9 8 7 | 8. 7 8~ | . 5 6 5 3 | 5 6 8 8 7 6 | 6 7 9 10 9 8 | 8. 7 6 5 |
#7~ . 3 4` then `... | 6 7 9 10 11 12 | 12. 10 8~ | 8~`. Rhythm cell: 8th 8th quarter 8th 8th quarter.
Growth: intro tease (3 bars, soft) -> chorus1 (sixths / drop2 / octaves, 82 % voiced) -> interlude (cell) -> chorus2 (74 %,
more thirds / octaves) -> breakdown (half speed, G#) -> chorus3 (+2 st, climax=True: octaves / locked hands, 86 %) ->
outro (sax).

## Transitions

- intro -> verse1: the drummer's fill; hats already in from intro bar 5.
- verse -> pre: fills (drummer), the melody climbs to A.
- pre -> chorus: drum build (8ths -> 16ths), riser over the last 4 bars, strings crescendo, one beat of silence before
  chorus1/2 (only the hero's tail / pickup), impact + crash on the downbeat.
- chorus1 -> interlude -> verse2: drummer fills; the interlude keeps the groove.
- chorus2 -> breakdown: downlifter, the drummer's stop (band hit), shimmer blooms.
- breakdown -> solo: drummer fill into the solo, pad filter reopens.
- solo -> chorus3: riser, the sax lands on G#7 (V of C# minor) = the key change.
- chorus3 -> outro: chorus 3's last bar on A (VI of C#m = VII of Bm), downlifter, the outro's G a step below it, drums
  strip after 4 bars, a ritardando-free fade with the last chord rolled.

## Players

- pianist (`pianist.arrange`, one `Memory` for the song): verses style sparse (density 0.35-0.45), pre / choruses
  straight with hook devices {octave 3, sixths 1.5, thirds 1.5, drop2 0.8, guide 0.8, single 0.4} and ornaments limited
  to {restrike 3, roll 1.5, crush 0.6, turn 0.4, trill 0.3} (a synthwave hook is sung, not decorated); breakdown ballad
  + tenths left hand; chorus3 climax=True. Velocities from `touch()` per section (the section arc).
- drummer (`drummer.arrange(s, style='synthpop', density=0.55)`): plan intro time-only, verse1 half, interlude post,
  breakdown break, verse2 energy 0.42, solo half (energy 0.45), ending hit. The kit gets a crash key (49, played by
  the cymbals track) so the 18 section crashes sound; hats, crashes and the kick layer are split onto their own tracks
  (SOUND.md).
- bassist (`bassist.arrange(style='synth')`, one `Memory`): part per section, kicks HALF / FOUR, outro ending ring.
- hornist (`hornist.arrange(family='sax', style='hero')`): solo (peaks on the held D, E, F#, D#, climax=True) and the
  outro farewell.

## Needs from sound design

- Hook: a hero sound that reads in front over pads + strings + choir, E2-F#6 (the breakdown left hand goes low),
  velocity -> level + brightness, sustain on long notes (the saw layer of piano_synth), pedal with the harmony.
- Sax: D4-F#5 (alto), breath on the air stage.
