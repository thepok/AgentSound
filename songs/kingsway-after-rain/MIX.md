# Kingsway After Rain - mix

From the start (the cover's feedback): bass -5 dB, drums not hot, the bed (strings / pad) up and present, everything
ducking under the sax (`s.sidechain(all, key=sax, depth=4, attack=15, release=250)`) and the bed + comping 3 dB under
the Rhodes melody. Then three `mix` passes:

```
'trim': bass -5, strings +5.5, pad +4.5, acoustic_l -1.5, acoustic_r -4, sax -1.5, guitar -1.5
'ride': drums chorus1 +2.5 / chorus2 +2.5 / gsolo +2; strings + pad verse1 +5.5, verse2 +5, chorus1 -1, chorus2 -1.5
'duck': bass under the kick 6 dB;  'eq': sax -1.5 dB 3.3 kHz, -1 dB 1.2 kHz; rhodes -1.5 dB 1 kHz
```

Final (dB vs the section lead; pop windows): riffs rhythm -6.9..-7.2, low -6.1..-6.4, bed -6.8..-8.4 (the sax
deliberately on top: the user's "duck under the sax"); verses (Rhodes) bed -9.8 / -10.0; choruses rhythm -3.3 / -4.9,
low -1.6 / -2.8, bed -4.3 / -5.8; gsolo rhythm -6.2. Mixer: no moves, one info (drums in chorus2 -4.9 vs -4).
Space lush, bed -7.5 dB vs lead, correlation 0.54 (intro 0.13, no phase warning), lows corr 0.98, width >150 Hz 44 %.
