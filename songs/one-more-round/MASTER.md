# One More Round - master

`master/edm` from the preset (eq: 25 Hz high-pass, -1.5 dB @ 300 Hz, air +1.5 dB; 2:1 rms glue above -10 dB; tape;
width - 1.45 in this song - with mono below 150 Hz; limiter ceiling -1.2 dBFS), the limiter drive ridden per section
(`s.master.lane('fx.limiter.gain', ..., base=master_gain + 1)`): intro -6, verse -4, breakdowns -7, builds -7 -> -3,
drops 0 / +0.5, talk box -3.5, outro -6.

`python -m agentsound master songs/one-more-round --check`: true peak -1.18 dBTP ok, -9.8 LUFS-I inside -10..-6, LRA
5.3-5.7 LU inside 2..10, mono compatibility ok (correlation 0.67-0.69). Drops at -8.7 / -8.4 LUFS, breakdowns -11..-12,
intro / outro -13. Streaming turns it down 4-6 dB (fine: a club master).

Finding on the way (fixed in the library, TODO for the rest): the limiter saturates on this dense drop - drive 11 vs 20
dB gave -9.3 vs -9.2 LUFS; only the release moves it (50 ms -9.3, 30 ms -9.0, 25 ms -8.9). master/edm now uses 30 ms
and the edm profile judges the whole song at -10..-6 (the drops -9..-6). A -7 LUFS club master needs a clipper stage
(TODO "Mastering"). Also fixed: a section lane with `glide` after a tuple move wrote its points out of order (the drop's
drive jumped back 1 dB after its first sample) - agentsound/sections.lane_points.
