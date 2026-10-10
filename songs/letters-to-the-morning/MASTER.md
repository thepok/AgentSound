# Letters to the Morning - master

The solo_piano preset's master (eq, glue 1.3:1 rms, tape 15 ips without wow / flutter, a slow limiter at -1.2 dBTP)
with song-level changes (`MASTER` in song.py):

- limiter drive 6.5 dB (preset 5.0): the intro / interlude / coda sat at -27..-29 LUFS - very quiet on a phone; the
  extra 1.5 dB only reaches the climax peaks (PLR 18+ dB kept).
- eq: -2 dB bell at 100 Hz (the pedalled bass), -1 dB at 3.2 kHz (q 0.8: the climax's loud chords), +2.5 dB high
  shelf at 9 kHz (air above the presence band; `master --check` proposed +3 dB at 8 kHz and -1.8..-2.9 dB at 100 Hz).

`python -m agentsound master songs/letters-to-the-morning --check`: -19.6 LUFS-I (target -23..-16), true peak
-1.20 dBTP, LRA 16.5 LU, correlation 0.44 - all ok. Streaming raises it ~5.6 dB (to -14) where the peak allows.
