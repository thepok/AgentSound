# Expensive Habits - mix (roles/mix-engineer.md)

Profile `pop` (hooks: rhythm -4..-0.5, low -4..-0.5, bed -10..-4 dB vs the lead). The lead is the voice; the brief
wants it IN the band (HUMAN_FEEDBACK: "die Stimme im Vergleich zum Rest zu laut"), so every move errs quieter for him.

## Moves

| move | why |
|---|---|
| trim vocal -2, drums +2, bass +1 | first build: the voice 7-8 dB over the kit and the bass in the choruses |
| trim pad -3, choir -3, strings -2.5 | the bed -2.4..-3.0 dB under him in choruses 2-4 (want <= -4) |
| trim riff -1.5; (song) riff -6.5 dB in the outro | the riff -1.2 dB under the outro tag (limit -4) |
| trim keys +1.5 | the stabs carry the chorus's width (right) |
| eq drums -2.5 dB at 3.3 kHz; (song) the kit carved up to 3 dB at 3.5 kHz keyed by the voice | the kit carried 47 % of 2.5-6 kHz against his 28 % -> 30 % / 39 %: the words, without turning him up |
| (song) the bed's width from placement and hall (strings left, choir right, keys right, ahs left, hall sends) instead of level | the choruses read `narrow` (31-33 % above 150 Hz) once the bed was under him -> lush (width 1.5 on the bed was over-wide: correlation -0.23) |
| (song) bass -3 / -2.5 dB in the verses, pad -2 / -1.5 | cooler verses |
| hero ride +0.5 dB (not 1.5) | in the band, not on top |

## After (`python -m agentsound mix`: 0 findings; dB vs the voice)

| section | rhythm | low | bed |
|---|---|---|---|
| verse1 | -2.7 | -1.7 | -5.8 |
| pre1 | -1.9 | +0.3 | -4.6 |
| chorus1 | -3.4 | -2.5 | -5.6 |
| verse2 | -2.8 | -1.1 | -5.6 |
| pre2 | -2.0 | +0.4 | -4.2 |
| chorus2 | -3.4 | -3.2 | -4.4 |
| bridge | -3.9 | -1.9 | -3.8 |
| chorus3 | -2.6 | -2.6 | -3.9 |
| chorus4 | -3.3 | -2.5 | -3.8 |
| outro | -2.1 | -0.6 | -6.7 |

Open / deliberate: `singer.check` warns that the voice sits 1-3 dB RMS under the bass in the verses / pres and owns
39 % (not 40 %) of the presence band - deliberate (the octave bass is the idiom, its energy is below 250 Hz; the voice
leads the kit and the bed everywhere). The report's kick / bass low-end masking warning stays: an 8th-note octave
bass under a four-on-the-floor kick always overlaps; the ducker (depth 9) is in.

## Round 2

- (song) bass -1 dB in pre1 / pre2 and the arc's pres -1.6 / -1.1 dB (were -1.0 / -0.5): the pre-chorus now sits
  1.3-1.5 LU under its chorus (was 0.7-0.8).
- (song) pad and choir -1.5 dB in the bridge: the bed -2.9 -> -4.1 dB under the intimate aside.
- `mix`: 0 findings. Balance vs the voice: rhythm -1.7..-3.7, low -0.4..-3.2, bed -4.0..-6.0 dB; the voice owns 40 %
  of the presence band (the kit 29 %).
- After A&R round 2: bass -2.5 dB in the bridge (it sat 2 dB over the intimate aside). Final `mix`: 0 findings;
  bridge rhythm -3.0 / low -2.5 / bed -4.5 dB vs the voice.
