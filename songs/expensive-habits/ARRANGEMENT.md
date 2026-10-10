# Expensive Habits - arrangement

**Frame**: 118 BPM, 4/4, straight (machine-tight 16ths), C minor (verses) / Eb major (choruses) -> +2 (D minor / F major)
from chorus 3; 116 bars, ~3:56 + tail.

## Form

| section | bars | harmony | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 8 | Cm Ab Eb Bb x2 | 2 | riff (glass piano), orch hits; pad, brass, bass + drums from bar 5 | the riff alone with hits, then the band joins |
| verse1 | 16 | Cm7:2 Abmaj7:2 Fm7:2 Gsus4 G x2 | 2 | TIGER (soft, half-spoken), bass, pad, light kit, marimba from bar 5 | 4 lines, each followed by ~1.5 bars of rest |
| pre1 | 8 | Ab Bb Gm7 Cm Ab Bb Fm7 Gsus4 G | 3 | + strings from bar 5 (crescendo), snare build | climbs to D4 on "told", riser, lands on G |
| chorus1 | 8 | Eb Bb/D Cm7 Ab Eb Bb/D Abmaj7 Bb | 4 | full kit + claps, keys stabs, strings, choir, orch hit on 1 and 5, impact | the title on the pickup leap |
| post1 | 4 | Cm Ab Eb Bb | 3.5 | riff + brass | the instrumental hook |
| verse2 | 16 | verse | 2.5 | + e-piano offbeat stabs, marimba from bar 1 ('up') | new words |
| pre2 | 8 | pre | 3.5 | strings whole section | "nobody here is sorry" |
| chorus2 | 8 | chorus | 4.5 | + Hanami "ahs" | |
| post2 | 4 | riff | 4 | riff + brass, downlifter into the bridge | |
| bridge | 8 | Fm Db Ab Eb Fm Db Bb Bb | 2.5 | half-time kit, bass roots in halves, pad, strings, choir | the turn: "I'll trade it all for one slow Sunday" |
| lift | 4 | Gm7 Gm7/C C7sus4 C7 | 3.5 | orch hits p -> ff, strings crescendo, pre-style snare build, riser | the dominant of F; a 1-beat breath before the chorus |
| chorus3 | 8 | chorus +2 (F C/E Dm7 Bb ...) | 5 | everything, impact on D2, marimba back | the key change |
| chorus4 | 8 | chorus +2 | 5 | Hanami higher (Bb4-C5) | the last line turned: "and we're running out of time" |
| outro | 8 | Dm Bb F C Dm Bb F-C Dm | 3 | riff (+2) + brass, the vocal tag x2, bass to bar 6, the drummer's ending | the riff's last answer climbs to D6 over D minor, a last D hit in bar 8 |

## The hooks

- **Sung**: "Ex-pen-sive ha-bits" = pickup Bb3 -> Eb4 (dotted quarter) D4 C4 Bb3 (held over the bar). Four choruses
  + the outro tag; after the key change it sits a whole step higher (C4 -> F4).
- **Instrumental riff** (C minor, 4 bars): `C5 Eb5 G5. F5 Eb5 D5 C5 | . C5 Eb5 F5 Eb5 C5 | Bb4 Eb5 G5. F5 Eb5 D5 Eb5 |
  . D5 F5 G5 F5.` - on the bright glass piano octave-doubled (the lower octave at ~65-70 %), a 2-bar velocity arch,
  the brass stab an octave down under it. Intro (twice), post1, post2, outro (+2, twice).

## Transitions

- intro -> verse1: the riff's last bar, the drummer's fill.
- pre -> chorus: the drummer's build (the `pre` role), a 15-beat riser ending a beat early, the impact on the downbeat,
  the orchestra hit.
- post2 -> bridge: downlifter, the kit drops to half time.
- lift -> chorus3: the orchestra-hit build, the riser, a one-beat breath (silence) before the key change, impact on D2.
- chorus4 -> outro -> end: the riff in D minor, the drummer's ending hit, the last orchestra hit, the riff's last chord rung out on the pedal.

## Players

- Drums: `drummer.arrange(s, style='synthpop', density=0.55, plan={'bridge': 'half', 'lift': role pre})` - fills
  budgeted by the drummer, crashes on section downbeats; the first 4 intro bars cleared.
- Voice: `singer.sing` with one `singer.Memory` (the spice budget song-wide); every line its own take (split 0.45 s).
- Bass: the sequenced octave bass (`bassline('octave', rate='1/8')`) - a machine part by design (the idiom), roots in
  halves in the bridge.
- Riff: velocities 84-106, a 2-bar arch, octave double softer, strummed 6 ms.

## Needs from sound design

- TIGER dry and close, clean; competitors (e-piano, marimba, riff) dip in his presence band.
- The riff bright with body (not a beep): the glass piano layer stack.
- Strings / choir / pad as a bed that steps aside for the words.
