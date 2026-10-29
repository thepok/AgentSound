# Kingsway After Rain - master

Song master chain: eq (-3.5 dB 380 Hz, -3.5 dB 1.1 kHz, -1 dB 1.6 kHz, +2 dB 9 kHz shelf) -> width 1.3 (mono < 120 Hz)
-> the power_ballad preset master -> limiter (+7 dB, ceiling -1.2, release 100 ms).
Loudness window -12.5..-9 LUFS (a 70s soft-rock record; pushing the limiter toward -11 bought 0.1 LU per 0.8 dB of
drive and cost LRA). `master --check`: -11.9 LUFS-I ok, true peak -1.19 dBTP ok, LRA 4.4 LU. Balance vs the pop ref:
lowmid +1.9, mid +2.6, presence +2.1 (the hero sax's character), sub -2.5 (the bass kept down on purpose).
