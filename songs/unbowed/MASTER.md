# Unbowed - master

Platform `dynamic` (a concert work: dynamics first), profile `classical`, no reference (no Beethoven recording in
`assets/refrences/`).

`python -m agentsound master songs/unbowed --platform dynamic` on the mixed build (-16.1 LUFS-I, the safety limiter
catching every ff peak at -1.0 dBTP):

- tone: +3.0 dB low shelf 100 Hz, -2.8 dB bell 1.6 kHz (Q 0.7), +1.2 dB high shelf 8 kHz (fit rms 0.27 dB) - broad
  only: the SSO sections are boxy around 1.6 kHz and light in the lows;
- width x1 (35 % above 150 Hz is inside 15..110 %), mono lows kept by the sections' own narrow low strings;
- loudness -16.1 -> -19.5 LUFS-I (the middle of the classical window): limiter gain -2.4 dB, ceiling -1.2,
  release 250 ms - the limiter now only catches the loudest hammer blows.

In song.py: `mastering.apply(s, eq={...}, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=-1.4)` (revision 1: -1.4 after the conductor's arc on the master input; -2.4 before).

## Result (`master songs/unbowed --check` on the rebuilt mix)

| measure | value | target |
|---|---|---|
| loudness | -19.8 LUFS-I (revision 1) | -23..-16 (orchestra -20..-18) |
| true peak | -1.20 dBTP | <= -1 |
| LRA | 17.3 LU (revision 1; 20.9 before) | 4..22 (8..20) |
| PLR | ~18 dB | >= 12 |
| width > 150 Hz | 31 % | 15..110 % |
| mono compatibility | corr 0.58 (mono ~1 dB quieter) | |
| tone vs classical | sub -3.7, lowmid +3.1, mid +3.6, presence +2.9, brilliance -0.5, air -2.0 dB | presence <= +3, mids <= +5 |

Refused: the check's further +3 dB low shelf at 80 Hz (the sub gap is the hall's 110 Hz low cut and the section
samples; a second shelf would make the basses boom) - left as it is.
