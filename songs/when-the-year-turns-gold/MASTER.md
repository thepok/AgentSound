# When the Year Turns Gold - master (roles/mastering-engineer.md)

Platform `dynamic`, profile `jazz` (-16..-13 LUFS, LRA 5-14), no reference (none for this idiom in
`assets/refrences/`): the profile's spectrum.

- Plan (`python -m agentsound master --platform dynamic` on the first build: brilliance -6.4, air -9.0, mid +1.8 vs
  the profile): +2.7 dB high shelf 6.3 kHz, -2.2 dB bell 800 Hz, +0.5 / +0.7 dB at 60 / 160 Hz.
- Applied: the shelf +2.5 dB at 6.3 kHz and the bell -1.8 dB at 800 Hz; the low lifts refused (the sub already reads
  +1.7 over the profile). A soft-hammer grand, bowed strings and a soft-mode voice are dark by nature - a songbook
  ballad may stay warmer than the genre average (now brilliance -4.0, air -4.7).
- Width x1.15 (x1.3 made the solo piano intro 74 % wide at correlation 0.15), the low end mono.
- Limiter: ceiling -1.2 dBFS, release 250 ms, drive 3 dB (the preset's 5.5 landed -12.3 LUFS) + 1 dB make-up.

In the song: `mastering.apply(s, eq={...}, width=MASTER_WIDTH, limiter={'ceiling': -1.2, 'release': 250.0},
loudness_change=MASTER_MAKEUP)`.
