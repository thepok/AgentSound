# Catch Fire - master

`python -m agentsound master songs/catch-fire` (profile rock, platform auto, no reference), applied in song.py:

```python
s.master.fx['tape'].set(drive=4.0)        # the rock_band master's tape rounds the drum peaks: a denser chorus
mastering.apply(s, eq={'high.freq': 6300, 'high.gain': 1.4, 'peak1.freq': 160, 'peak1.gain': 0.5, ...},
                width=1.25, limiter={'ceiling': -1.2, 'release': 120.0}, loudness_change=+3.7)
```

(the song's own limiter gain was first lowered 7 -> 5 dB so the drop jumps out of the pre-chorus; then +2.8.)

| | mix (before) | master |
|---|---|---|
| LUFS-I | -10.2 | -9.9 (rock window -10..-7) |
| true peak | -1.2 dBTP | -1.2 dBTP |
| LRA | 7.1 | 4.8 LU (rock 2.5..12) |
| PLR | - | 8.7 dB |
| width >150 Hz | 21 % | 32 % |
| tone vs rock ref | brilliance -3.7, air -4.7 | brilliance -3.6, air -3.4 (+1.4 dB shelf at 6.3 kHz) |

- The choruses sit at -8.8 LUFS whatever the drive (the limiter holds them): more drive only lifted the verses and
  shrank the quiet-loud contrast, so the drive stops at +2.8 (integrated -9.9).
- `master --check`: true peak ok, LRA ok, mono compatibility ok (correlation 0.63, mono sum ~0.8 dB quieter);
  streaming turns it down ~4 dB (normalisation info).

After the A&R revision (louder kit, quieter intro) the integrated level fell to -10.03: drive +2.8 -> +3.7 ->
-9.9 LUFS-I, -1.20 dBTP, LRA 4.2 LU, PLR 8.7 dB; `master --check` all ok.
