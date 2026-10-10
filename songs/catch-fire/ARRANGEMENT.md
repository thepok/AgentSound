# Catch Fire - arrangement

## Frame

124 BPM, D minor, 4/4, straight 8ths; the choruses, post-choruses and the intro's second half feel half-time (the
snare + clap on 3). 110 bars = 3:33.

## Form

| section | bars | harmony (one chord per bar unless :n) | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 8 | Dm F C Bb x2 | 2 -> 3.5 | gang chant (TIGER alone, then the whole gang + Hanami 8va), taikos (stomp), claps on 3, the synth pulse filtered; from bar 4: drums half-time on the floor tom, guitars ringing, bass, sub, choir | the chant = the second hook, heard in the first second; a downlifter into the verse |
| verse1 | 16 | Dm:2 Bb:2 F:2 C:2 x2 | 2 | lead low (C3-C4), taiko stomp + claps, pulse, bass long notes (ballad); bar 8: the drummer on floor-tom half-time, the riff palm-muted single notes, bass on the kick | sparse: a bar of air after every line |
| pre1 | 8 | Bb C Dm Dm Bb C Gm A | 3 -> 4 | lead rising (F3-D4), the riff as power-chord chugs, piano 8ths crescendo, pulse filter opening, drummer build, taiko stomp from bar 4, riser + reverse swell | "so go on and try me" - then ONE BEAT OF SILENCE (breath) |
| chorus1 | 8 | Dm F C Bb Dm F C C | 5 | lead + 2 sung doubles + a harmony a third below, gang "hey!" on the half-time 3, half-time drums (ride), taiko drop pattern, claps, the guitar wall (ringing chord + push), bass driving 8ths, sub on the kick, choir "oh", piano sparkle D5-D6 | impact on the downbeat; the hook "Strike me down, I catch fire" peaking on A4 |
| post1 | 4 | Dm F C Bb | 4.5 | the gang chant (TIGER x3 + harmony + Hanami), tribal taikos + floor-tom half-time, wall, choir | the chant answers the chorus |
| verse2 | 8 | Dm:2 Bb:2 F:2 C:2 | 2.5 | lead, the kit on 8th hats, riff palm-muted, piano 8ths soft, pulse | a downlifter; the band stays in (no full drop) |
| pre2 | 8 | as pre1 | 3 -> 4 | as pre1, a little hotter | breath |
| chorus2 | 8 | as chorus1 | 5 | as chorus1 | impact |
| post2 | 4 | Dm F C Bb | 4.5 | as post1 | |
| bridge | 8 | Bb F Gm Dm Bb F Gm A | 1.5 | piano (8th arpeggio + low roots, pedal), choir soft, lead sung softer (soft mode), bass enters at bar 4 | strip-down: no drums, no guitars (only their level lane), a downlifter + soft impact |
| build | 8 | as pre | 3 -> 5 | lead + doubles (the gang sings the pre), drums on the floor tom building, taikos stomp -> tribe, riff 0.5 -> 0.72, choir crescendo, pulse filter wide open | breath, riser |
| chorus3 | 16 | chorus x2 | 5+ | everything; the last line "we'll burn on into daylight" | impact |
| post3 | 4 | Dm F C Bb | 5 | the gang chant at full size | ends on the chant's "hey!" |
| end | 2 | Dm | hit | drummer's final hit, guitars + bass ring, taiko, sub | the cut-off |

## The hooks

- **Chorus hook** (lead): `F4/8 E4 D4/4 r/8 D4/8 E4/8 A4/8~ | A4/4. G4/8` - "Strike me down, I catch fi-re": three
  stomped syllables falling F-E-D, a breath, then a climb to a held A4. Returns 2x per chorus, 8x in the song; the
  doubles widen it, the harmony (a third below, sung) thickens it, the last chorus is 16 bars and changes one word.
- **Chant hook** (gang): `A3/4. A3/8 C4/4 D4/4 | C4/2 A3/4 r/4 | G3/4. G3/8 A3/4 C4/4 | A3/2 r/4 D4/8` -
  "Whoa, oh oh oh, oh oh / whoa, oh oh oh, oh - hey!". Opens the song (bars 1-4 alone, 5-8 with the band), follows
  every chorus, grows from one voice to five.

## Transitions

- intro -> verse1: downlifter, the band drops out (stomp + clap stay).
- verse1 -> pre1: the drummer's fill, the riff wakes up (power chords).
- every pre -> chorus: the drummer's build, the riff's fill into the chorus (`into=`), a 15-beat noise riser peaking
  on the breath, a 2-beat reverse swell, one beat of silence for everyone but the voices (`s.transitions(...).into(
  chorus, breath=1)`), an impact on the downbeat.
- chorus -> post: continuous (the post is the chorus's tail: taikos go tribal, the drums move to the floor tom).
- post -> verse2: downlifter.
- post2 -> bridge: downlifter + a soft impact; everything but piano + choir stops.
- bridge -> build: the floor tom enters, the stomp returns.
- post3 -> end: the drummer's ending hit.

## Players

- drums: `drummer.arrange` (style rock, density 0.55, hands 'master', one `drummer.Memory`), three calls: intro
  (bars 4-7), verse1 bar 8 .. post2, build .. end (`ending='hit'`); per-section plan: verse1 floor-tom half-time
  (energy 0.38), pre builds (0.62 / 0.66), choruses `halftime` + ride (0.92 / 0.96 / 1.0), posts `halftime` + floor,
  verse2 hat 8ths (0.5), build floor (0.7).
- percussion: `taiko.plan` / `claps.plan` (stomp, drop, tribe cells; per-section loops; the track humanized).
- bass: `bassist.Player` (style rock, one Memory): verse1 ballad long notes, then rock locked to the half-time kick;
  pre / chorus / post parts; the bridge (ballad) from bar 4; the end rings.
- sub: one sine note per bar on the chord root (F1-E2) + the & of 2, under the choruses / posts / intro.
- guitars: `guitarist.riff` + `guitarist.double` (two performances, gtr_l FSBS -> high-gain amp, gtr_r Emily ->
  crunch): one cell (3+3+2+3+3+2) per chord root for verse / pre, a ringing chord + half-time push for chorus / post,
  the energy per section decides palm-muted single notes / chugged power chords / ringing power + octave; `into=` the
  chorus gives the fill.
- piano: 8th pulse (verse2, pres: close voicings A3-D5, crescendo, 2-bar arches), chorus sparkle (D5-D6 quarters),
  bridge (8th up-down arpeggio A3-F5 + root, pedal by `pianist.pedal`).
- choir "oh": spread voicings D3-A4 under the choruses, posts, bridge, build.
- synth pulse: 8th up-arpeggio D4-D5 with the cutoff lane opening intro -> pre.
- vocals: `singer.sing` (TIGER, style rock, one Memory for the lead, one for the gang), chorus parts with
  `base_power=1.0, power=0.6`, the bridge softer (`soft=0.6, base_soft=0.3`); `singer.double` L / R and
  `singer.harmony(steps=-2)` on every chorus and the build; the gang chant on its own tracks.

## Needs from sound design

- The vocal chain dry and close (the vocal hero, rock); the doubles and the gang the same chain, no rides / throws.
- A sub that is felt on the drops but stays out of the verses; the kick must not fight it (the sub sits on the kick's
  notes).
- Taikos and claps big but under the voice; the guitars may be loud only where the voice rests.
