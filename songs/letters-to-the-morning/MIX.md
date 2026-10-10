# Letters to the Morning - mix

`python -m agentsound mix songs/letters-to-the-morning` (piano plan: the melody hand on top of the accompaniment,
3-12 dB; no glue - one instrument, the pianist balances the hands).

- Measured bed (left hand) vs lead (right hand) per section (round 2): intro -4.5, A1 -6.3, A2 -8.0, B1 -9.3, A3
  -6.9, build -9.7, climax -9.6, A4 -7.3, coda -5.9 dB (inter: quiet, not judged) - all inside -12..-2, no moves.
- MIX: `{'eq': {'comp': [{'freq': 400, 'gain': -2.0, 'q': 1.0}]}}` - a little more room for the melody's low notes.
- Open: one `masking` warning in the coda (both hands carry > 35 % of 250-800 Hz while the final chords ring:
  the 250-800 Hz band holds the melody's own C4-G5 fundamentals). Judged by ear-level reasoning as the natural
  sound of one piano's two hands on a held final chord; the right hand's final chord was raised to C5-Eb6 and the
  left hand dipped, which is as far as it should go without thinning the ending.
- Level jumps (B1 -> inter -7.7 LU, A3 -> build +6.1, climax -> A4 -8.6) are the written dynamics (info only).
