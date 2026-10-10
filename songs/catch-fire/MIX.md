# Catch Fire - mix

Profile `rock` (the band's balance; the brief first named `pop` - against the pop reference the guitar wall read
+4.7 dB low-mid / +4.6 dB mid "muddy / honky", against the rock reference +0.4 / +0.7: a pop-rock band record).

## MIX (song.py)

```python
MIX = {
    'trim': {'drums': 1.5, 'claps': 3.5, 'gtr_l': 2.5, 'gtr_r': 2.5, 'vocal': -1.0, 'choir': 5.0, 'bass': 1.0, 'sub': 1.0},
    'ride': {'vocal': {verse1/pre1/verse2/pre2/bridge: +1.0, build: +1.75, chorus1-3: +0.75},
             'drums': {chorus1-3: +1.5, post1-3: +1.0, build: -1.0}, 'gang' (+ its layers): {intro: -2.5 (-2.0)},
             'choir': {'bridge': 3.5, 'build': 4.0}},
    'eq': {'drums': 45 Hz -3, 'gtr_l' / 'gtr_r': 400 Hz -3.5, 'keys': 350 Hz -2, 'choir': 350 Hz -3},
    'duck': [sub under the kick: 10 dB, 1 ms, hold 40 ms, release 160 ms],
}
```

Plus, in the arrangement code (the producer's quiet-loud): `s.arc` (a master pre-limiter ride per section: intro -5
-> -3, verse1 -5, pre1 -4 -> -2.5, verse2 -4.5, pre2 -3.5 -> -2, bridge -7, build -4 -> -1.5, chorus3 / post3 / end
+0.5), taiko levels per section, guitar levels per section (verse -5/-6, chorus +1.5/+2), the drum room send -2,
guitar room sends -9.

## Before / after (full builds)

| | first build | final |
|---|---|---|
| LUFS-I / LRA | -9.2 / 2.4 LU (verse1 -10.7 vs chorus -8.7) | -9.9 / 4.8 LU (verse1 -13.2, pre1 -10.0, chorus -8.8, bridge -13.3) |
| width >150 Hz | 18 % (narrow) | 32 % (lush) |
| reverb vs mix | -15.9 LU | -14.9 LU |
| report warnings | 5 warn + 7 info (narrow, low-end masking x2, echo inaudible, tails) | 0 warn, 5 info |
| mixer, hooks: rhythm / low / bed vs lead | -9.6 / -5.2 / -13.3 dB | -5.3 / -2.9 / -8.9 dB (drums still 1.8 dB under the rock window: the vocal kept in front) |
| vocal presence share | 30 % song-wide | 35 % song-wide; 38 % over the chorus span (`--from-beat 126 --to-beat 158`) |
| clicks | 0 | 0 |

## Open / deliberate

- `drums_too_quiet` (mixer, hooks -5.3 vs -3.5): deliberate - the vocal is the lead of an anthem; pushing the drums
  further would cost the words (the presence share is already the tight constraint) and the drum peaks already
  reach +3 dBFS pre-master.
- `vocal_intelligibility` (singer.check): measured song-wide (35 %) while the lead is silent in the intro, the
  post-choruses and the end; in the chorus span it owns 38 %. The gang (10 %) sings "whoa / hey" - no words to lose.
  See TODO (the check should judge where the vocal sings).
- flat_dynamics INFO on gtr_l / gtr_r: a riff wall through a driven amp; see AR.md.

## A&R revision (AR.md round 1 -> 2)

The vocal stood on the band (hooks: rhythm -5 dB vs the lead; HUMAN_FEEDBACK "die Stimme im Vergleich zum Rest zu
laut"). Vocal trim -0.5 -> -1.0, claps +1, the kit ridden +1.5 in the choruses / +1 in the posts (a trim of +1.5
everywhere put the vocal under the drums in both verses), taikos intro +4 / verse1 +3 / posts +2, the intro gang
-2.5. Result: hooks rhythm -3.6 / -3.0 / -3.2, low -3.3 / -2.9 / -3.0, bed -8.5; intro rhythm -6.6 -> -3.8, low
-9.8 -> -6.1; `mix`: no moves, `drums_too_quiet` gone. Vocal presence share 35 -> 33 % (still the open info above).
