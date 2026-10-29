# Kingsway After Rain - sound

- **Sax**: `sampled/alto_sax` through `hero(sax, family='sax', genre='pop', sections=riffs+outro, bed=[strings, pad])`
  = hero/sax v2, the user's 70s record chain (Weresax dynamic mic, 4:1, tube drive, tape, the 10 Hz autopan flutter,
  hero_plate_70s, echo throws). Range C#3-G#5: the riff peaks on G#5.
- **Rhodes** (verses / choruses): `epiano('rhodes')` (jRhodes3d), hp 180, -5 dB 380 Hz, +2 dB 7 kHz shelf, chorus I,
  plate -14 / hall -18 - the cover's instrument-version voicing with warmer low mids.
- **Hero guitar**: power_ballad's lead through `hero(family='guitar', genre='rock')`, -8 dB (the cover's lesson);
  every note kept <= D6 (the FSBS DI's top: the first build had 17 silent notes on E6 / D#6 / F6).
- **Bed**: VPO strings (no extra width - the section's own correlation is ~0) and the Juno pad (hp 220, width 1.15);
  master width 1.3 with mono below 120 Hz (the cover's 1.25 + 1.75 drove its intro to -0.32 correlation).
- **Acoustics**: sampled acoustic (L -0.7) + steel string (R +0.7), chorus I, -2.5 dB at 350 Hz.
- **Kit / bass**: Big Rusty (low shelf -1.5 dB at 70 Hz, -2.5 dB at 125 Hz: the bass owns ~110 Hz); Growlybass +2 dB
  at 115 Hz, its kick ducker 10 dB.
- **The stop** (riff3): a `utility` named `stop` on piano / strings / pad / bass / acoustics (-60 dB) and the hall
  (-9 dB) for the two bars, so releases and the band's room do not smear the silence; the sax keeps its plate.
