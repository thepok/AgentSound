# MASTER - Toccata Tenebrae

`mastering.apply(s, eq={'high.freq': 8000, 'high.gain': 2.0}, limiter={'ceiling': -1.2})` on the preset's master.

- The pipes through the church IR sit 15-19 dB under the classical balance above 6 kHz ('dull' info); a +2 dB air
  shelf at 8 kHz (above the mixture's 2-5 kHz band, which the mix dipped) - brilliance -9.5 -> -7.7, air -18.7 ->
  -15.2 dB. The `master --check` proposal (+3 dB from 4 kHz) would push the mixture again: not taken.
- Loudness stays where the registrations put it: -19.9 LUFS-I (window -23..-16), LRA 10.7, TP -4.4 dBTP (the
  check: ok / ok). Streaming normalisation raises it up to 5.9 dB; fine for a concert work.
