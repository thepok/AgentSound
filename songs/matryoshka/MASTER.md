# Matryoshka - master

Platform `auto` (the pop window -11..-8 LUFS); no reference (an invention), tone judged against the pop profile.
Tool: `python -m agentsound master songs/matryoshka --section chorus4` (the hook section) and `--check`.

## Decisions

- **Tone**: the plan asked +3.0 dB low shelf at 60 Hz and -1.8 dB at 1.25 kHz (sub -4.1 dB vs the profile, the only
  big deviation). 3 dB on the master is the limit - the sub is also a mix matter: +1.5 dB low shelf on the bass (60 Hz)
  in the song, +2.0 dB on the master; the mid bell -1.8 dB @ 1.25 kHz Q 0.7 taken as planned. After: sub -2.1 dB,
  lowmid +1.5, mid +1.4, presence 0.0 (no presence lift on a piano-led song: "es klingt hart").
- **Width**: x1 (width above 150 Hz 42 %, inside 35..100 %); the pop_band master's width 1.35 with mono bass at 120 Hz
  stays (low-end correlation 1.00).
- **Loudness**: the pop_band chain (glue 2:1 above -12 dB, 30 ips tape, limiter) with `mastering.apply(...,
  limiter={'ceiling': -1.2, 'release': 120}, loudness_change=+0.5)`: limiter gain 7.0 dB, ceiling -1.2 for
  <= -1 dBTP.
- **The energy arc** (the brief's arc, not a flat brick - the first render read LRA 2.1 LU): the limiter's drive per
  section on top of the base: intro 0, verse1 -1.5, build -0.6, chorus1 +0.6, turn -0.3, minor -1.3, verse2 -0.6,
  chorus2 +0.3, chorus3 +0.5, chorus4 +0.8, coda -1.2 for its first 8 bars (the revelation starts quiet) rising to
  +0.6 at its 16th bar, end +0.3 (smooth 1-beat ramps).

## Result (pass 6 build; `master --check`)

-10.7 LUFS-I, TP -1.20 dBTP, LRA 4.9 LU, PLR ~8, correlation 0.67 (mono ~0.8 dB quieter), low end mono; sections
intro -16.9, verse1 -12.2, chorus1 -10.5, minor -12.5, chorus2 -10.0, chorus3 -9.4, chorus4 -9.1, coda -10.4 LUFS.
Streaming turns it down 3.3 dB (Spotify) - fine: a pop master, not squashed.
Refused: more than +2 dB of master low shelf (the rest belongs to the bass / kick), any presence lift.
