# The Drummer Speaks - mix

Profile `rock` (lead = the hero guitar in A / B / B2 / A3; rhythm = drums; low = bass; other = guitars, organ,
mallets). Starting balance: the rock_band preset's levels + the hero wrapper (no bed duck in rock; the organ carved
-2.5 dB at 2 kHz while the lead plays; -2 dB presence dips on both rhythm guitars; the lead ridden +1 dB in its
sections; echo throws at its phrase ends).

```python
MIX = {
    'trim': {'drums': 2.0, 'bass': 1.5},
    'ride': {'lead': {'B2': -1.5}, 'drums': {'solo': 3.5}},
    'duck': [{'targets': ['bass'], 'key': 'drums', 'pitches': 'kick', 'depth': 4, 'attack': 2, 'release': 110}],
    'eq': {'drums': [{'freq': 42, 'gain': -2.5, 'q': 0.8}], 'lead': [{'freq': 3300, 'gain': -2.0, 'q': 1.0}]},
}
```

| move | why |
|---|---|
| drums +2.0 dB | `mix`: rhythm -5.1 / -5.6 dB under the lead in B / B2 (rock window -3.5..0): the groove has to carry |
| bass +1.5 dB | low -6.5 / -5.8 in B2 / A3 (window -5..-1.5) |
| drums +3.5 dB in the solo | the drums ARE the band in the solo; without it the solo's climax sat 6 LU under the band (solo -13.7 vs B2 -7.7 LUFS) - with it (the soloist's version, more space in the statement) -11.8 vs -8.5 (the soft start stays soft, the climax comes near the band's level, the band's return is still an event: +3.3 LU) |
| bass ducked 4 dB more under the kick | the riff is a bass + kick unison (the kick locks to the bass): masking warned in A / A3 |
| drums -2.5 dB at 42 Hz | sub +4.9 dB over the rock reference, 99 % from the 24" kick and 22" floor tom: now +3.2 |
| lead -2 dB at 3.3 kHz | harsh: 2-5 kHz +2.9 dB over the reference, 52 % of it the lead; now presence +0.7 |
| lead -> echo bus -12 dB | the band's dotted ping-pong echo was unused (warning); the lead's phrase ends now repeat in stereo |

Before -> after (dB vs the section lead, `python -m agentsound mix`): A rhythm -4.1 -> -2.2, low -5.0 -> -2.8;
B -3.4 / -2.7 (was -5.1 / -5.3); B2 -2.5 / -2.7 (was -5.6 / -6.5); A3 -1.6 / -3.5 (was -3.6 / -5.8). Moves: none
left - the balance is inside the targets.

Production moves written in song.py (arrangement-side, not balance): the kit's gated-reverb send opens to -4 dB only
for the `gated_toms` bars; the kit's plate send rises to -5 dB on the last beat before the solo's silence (the
strokes ring into it) and to -6 dB on the final hit; the guitars' room send rises on the final hit; the organ's swell
pedal (expression) and Leslie speed per section.

Deliberate / open:
- `masking` drums vs bass in A / A3 stays a warning: the riff IS the bass and the kick together (locked); the duck
  (5 + 4 dB) and the kit's 150 Hz cut keep it defined.
- `flat_dynamics` (info) on the rhythm guitars and the organ: the guitars' accents are articulation (palm mute vs
  open) through a crunch amp that levels the notes (~2.4 dB per phrase, 7.3 dB over the song); the organ has no
  touch - its dynamics are the swell pedal (written: "dynamics automated").
- `node_hot` (info): the drums peak +3.5 dBFS before the master in the solo (float; the master limiter catches
  them).
- The master's input: +0.3 LU from these moves (the master check: -10.4 LUFS-I).
