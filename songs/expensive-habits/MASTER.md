# Expensive Habits - master (roles/mastering-engineer.md)

Platform `auto`, profile `pop` (window -11..-8 LUFS), no reference.

- Tone: no master eq (`master`: wanted correction <= 0.9 dB, inside the dead band; bands vs the pop profile within
  +-1 dB, air -2).
- Width: x1 (43 % above 150 Hz, inside 35..100), mono lows (lows correlation 0.99).
- Loudness: `mastering.apply(s, limiter={'ceiling': -1.2, 'release': 120}, loudness_change=+2.8)`.
  -12.1 -> -10.8 LUFS-I. The plan's -10.5 was not reached on purpose: +2.1 dB of drive bought 1.0 LU and cost
  1.4 LU of LRA (5.8 -> 4.4); at +2.8 the LRA is 4.1 LU - more drive would only squash the verse / chorus contrast.
- Result: -10.8 LUFS-I, true peak -1.07 dBTP, LRA 4.1 LU, PLR 9.7 dB, correlation 0.69, 0 clipped samples.
- `master --check`: true peak ok, loudness ok, LRA ok, mono ok (mono sum 0.7 dB quieter).

Round 2 (same chain): -10.9 LUFS-I, true peak -1.12 dBTP, LRA 4.1 LU, correlation 0.68; `master --check` all ok.
Sections: verses -13.4 / -12.3, pres -11.2 / -11.0, choruses -9.7 / -9.7 / -9.4 / -9.4, bridge -12.2, outro -10.4 LUFS.
Final build: -10.9 LUFS-I, -1.10 dBTP, LRA 4.1 LU, bridge -12.7 LUFS, outro -10.6 LUFS; `master --check` all ok.
