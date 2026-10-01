# The Drummer Speaks - master

- **Platform**: `auto` (the `rock` window -10..-7 LUFS-I, PLR >= 5, -1 dBTP). No reference (none for a drum
  feature in `assets/refrences/`): tone against the rock profile.
- **Chain** (the rock_band master, set by `mastering.apply` in song.py): `master_eq` (-0.8 dB low shelf 60 Hz, +2.0 dB
  bell 400 Hz Q 1: the profile wanted +1.4, then +0.6 more on the re-check - lowmid -2.9 -> -0.9 dB vs the reference)
  -> the preset's eq (25 Hz high-pass, -1 dB at 300 Hz, +2.5 dB air shelf) -> glue 2:1 at -12 dB (RMS, 100 Hz key
  high-pass) -> tape 15 ips -> width 1.12 (mono below 150 Hz) -> limiter ceiling -1.2 dBFS, release 120 ms, drive
  7 -> 10.5 dB (`loudness_change=+3.5`).
- **The drum peaks**: with the drums alone in the solo, their hardest hits (+2 dBFS on the drum bus before the
  master) drove the limiter: +1.5 dB of drive bought only +0.3 LU and cost 0.7 LU of LRA. The sound designer's peak
  catcher at the end of the drum bus (8:1 above -9 dBFS, 0.3 ms attack: only the tallest transients) let the same
  drive reach the window.
- **Result** (`master --check` on the final build): -10.2 LUFS-I (0.2 LU under the window's floor: warn, kept - the
  quieter solo pulls the integrated level down; the band sections sit at -8.5..-9.3), true peak -1.20 dBTP, LRA 4.9
  LU, PLR ~9, mono correlation 0.67, no clipping, 0 clicks.
- **Refused**: more drive. +0.6 dB more bought nothing (the limiter holds the drum peaks); the post-pass (`master
  --render`, +3 dB more limiting) reached -9.5 LUFS but cost 0.5 LU of LRA and 1 dB of crest - the solo's arc (soft
  motif -> climax) is the point of this song. Streaming services turn it down 3.8 dB anyway.
- **Kept as is**: the sub +0.7 dB over the reference (a 24" kick and a 22" floor tom in a drum feature; the mix
  already took 2.5 dB at 42 Hz).
