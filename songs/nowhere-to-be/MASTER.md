# Nowhere to Be - master (roles/mastering-engineer.md)

Platform `dynamic` (jazz: dynamics first), profile `jazz` (-16..-13 LUFS, LRA 5-14, PLR >= 9), no reference (none for
smooth jazz in `assets/refrences/`: the profile's reference spectrum).

## Plan (`python -m agentsound master songs/nowhere-to-be --platform dynamic`)

- Tone: +1.0 dB low shelf 60 Hz, -2.2 dB bell 630 Hz (Q 1) (fit rms 0.32 dB). Width x1.25 (the plan's cap; 8 % above
  150 Hz < 15). Loudness -15.6 -> -14.5 LUFS (limiter +1.5 dB; it would fall short rather than squash).

## Decisions

- The bell at 630 Hz -2.2 dB: kept (the low mids / mids of her low register and the tenor).
- The low shelf +1 dB: refused - the sub already reads +1.6..+2 dB over the profile; smooth, not boomy.
- Width x1.6 instead of x1.25: the dry centred voice leaves the mix ~8 % wide above 150 Hz; at x1.6 23 % ('lush'
  overall, the sung sections 9-15 %), correlation 0.71 (mono sum ~0.7 dB quieter), the low end mono (corr 0.99).
- Limiter: ceiling -1.2 dBFS, release 250 ms, `loudness_change=+1.0` (the eq's loss made up and a little more); the
  preset's drive 6 -> 3 dB (MASTER_DRIVE) - the voice-led ballad reads ~3 LU louder into it.

In the song: `mastering.apply(s, eq={'low.freq': 60, 'low.gain': 0.0, 'low.q': 0.7071, 'peak1.freq': 630,
'peak1.gain': -2.2, 'peak1.q': 1.0}, width=1.6, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=1.0)`.

## Result (`master --check --platform dynamic`)

-15.1 LUFS-I (inside -16..-13), true peak -1.20 dBTP, LRA 5.0 LU, PLR ~13.8 dB, correlation 0.71, 0 clicks, 0 clipped
samples; all checks ok (info: tone_profile would add +1.1 dB at 60 Hz / -1.1 at 630 - within the dead band).
