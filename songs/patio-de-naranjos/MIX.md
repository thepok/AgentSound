# Patio de Naranjos - mix

One track: the balance is the player's (the tune 8-15 velocity over the pattern; a split render measured the tune
~3 LU over the accompaniment integrated, incl. its rests). `python -m agentsound mix`:

- `MIX['lead']`: the guitar is the lead in every section with the tune (it plays its own accompaniment).
- `MIX['eq']`: -2.5 dB at 300 Hz (q 1) on the guitar - mud 200-400 Hz +4.8 -> +2.8 dB over the classical reference.
- No glue, no rides: the arc is played (a1 -21.6, b -20.0, c -18.5, bridge -19.1, a2 -17.4, coda -21.6 LUFS);
  `s.arc` only eases c (-0.5) and lifts the coda (+2).
- Remaining mixer finding: `no_lead` from the report's roles (a solo guitar is not classed as a melodic lead) -
  structural, the MIX names it.
