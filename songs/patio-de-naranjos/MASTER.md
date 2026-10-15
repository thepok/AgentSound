# Patio de Naranjos - master

Platform auto, classical profile (-23..-16 LUFS). Chain: `fx.width(1.2, monobass=120)` -> `fx.limiter(gain=6,
release=250, ceiling=-1.3)`. Result: -19.1 LUFS-I, TP -1.30 dBTP, LRA 6.8 LU, PLR 15-20 dB per section (a solo
instrument keeps its transients). `master --check`: true peak ok, loudness ok; the tone note (+3 dB at 100 Hz towards
the orchestral average) is not taken - a guitar has no sub and the thumb's low E is already full.
Streaming normalisation raises it 5 dB (Spotify, TP allowing) - fine for a quiet acoustic record.
