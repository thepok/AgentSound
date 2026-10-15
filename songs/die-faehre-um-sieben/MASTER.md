# Die Fähre um sieben - master

Chain: glue compressor + limiter, then `mastering.apply` (eq +1.3 dB at 160 Hz, -2.2 dB at 630 Hz towards the jazz
profile's tilt, width 1.25, limiter ceiling -1.2 dBTP, loudness +1.2).

`master --check`: -14.6 LUFS-I (jazz target -16..-13), true peak -1.20 dBTP, LRA 6.2 LU, tilt -4.6 dB/oct (ref -5.0).
Normalisation: Spotify / YouTube +0.6 dB, Apple Music -1.4 dB. The check's tone hint (+0.9 @160 / -1.1 @630) left as
is: the remaining low-mid is the guitar body that carries the record.
