# Round 3 (the calm version: 100 BPM, G major, the dry voice)

- width x1.2 -> x1.6: the dry, centred voice (no hall / room on it any more) left the sung sections 9.5-14 % wide above 150 Hz ('narrow', target 15-80 %); at x1.6 head 16.8 %, head_out 18.2 %, tag 24 % (lush), correlation 0.66 (the mono sum 0.8 dB quieter). The intro / solo read 88 / 93 % ('ok').
- the 250 Hz bell +0.7 -> -0.5 dB: a minor third lower the low mids read +3.3 dB over the jazz profile.
- result: -15.6 LUFS-I, true peak -1.20 dBTP, LRA 5.9 LU, PLR 14.6, 0 clicks; `master --check` all ok.

# Round 2

# Down on Jane Street - master

Platform `dynamic` (jazz: dynamics first), profile `jazz` (-16..-13 LUFS, LRA 5-14, PLR >= 9), no reference (none
for jazz in `assets/refrences/`: the profile's reference spectrum).

## Plan (`python -m agentsound master songs/jane-street-bossa --platform dynamic --render`)

- Tone: -2.3 dB bell at 1 kHz (Q 1), +0.7 dB at 250 Hz, +1.0 dB low shelf 60 Hz (mid +2.5 dB over the profile: the
  voice and the piano's middle register; fit rms 0.35 dB). Width x1 (19 % above 150 Hz, inside 15..80). Limiter
  ceiling -1.2 dBFS, release 250 ms.
- The post-pass drove the limiter +1.3 dB to the platform's -14.5 LUFS: -15.2 -> -14.6 LUFS, but the LRA fell 5.0 ->
  4.8 LU (a new `lra_small` warn). **Refused**: the song keeps its dynamics - in `song.py` only the EQ and the make-up
  for its loss (`loudness_change=0.6`), so the master lands where the mix was.

## In the song (`mastering.apply(...)` at the end of `build()`)

```python
mastering.apply(s, eq={'low.freq': 60, 'low.gain': 0.0, 'low.q': 0.7071, 'peak1.freq': 250, 'peak1.gain': 0.7,
                       'peak1.q': 1.0, 'peak2.freq': 1000, 'peak2.gain': -2.3, 'peak2.q': 1.0},
                width=1.2, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=0.6)
```

## Result (`master --check --platform dynamic` on the rebuilt `out/mix.wav`)

| | value |
|---|---|
| LUFS-I | -15.1 (inside -16..-13) |
| true peak | -1.20 dBTP |
| LRA | 5.7 LU (inside 5..14) |
| PLR | ~14 dB |
| width > 150 Hz | 27 % (sung sections 18-20 %, solo 51 %), correlation 0.71 (mono -0.7 dB) |
| tone vs profile | mid +1.6, sub +1.1, brilliance -3.1, air -2.5 (a warm club sound; the piano is voiced warm on purpose) |

Revise round 1 (A&R): the +1 dB low shelf at 60 Hz dropped (sub read +3 dB, 63 Hz +6 over the profile; the bass got a
-2 dB bell at 63 Hz in the MIX), width x1.2 above the mono bass (the sung sections read 10-13 % wide).

Delivered file: the rebuilt `out/mix.mp3` (the song chain carries the master).
