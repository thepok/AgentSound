# Kestrel Bay - mix

`python -m agentsound mix songs/kestrel-bay` (profile rock), three passes:

1. first build: the hero 7 dB over the drums and 10-17 dB over the bed (the mixer: drums_too_quiet, bed_too_quiet);
   every section at -8.2..-9.2 LUFS (LRA 1.9 LU): no arc at all.
2. `trim lead -3.5, drums +2, bed +3` overshot: bass / rhythm / bed above their windows (lead_not_in_front in outro).
3. final `MIX` (song.py): trim lead / lead_twin -1.5, drums +2, pad / strings +1.5, bass -1.5, clean -1.5, gtr_l -1.5,
   gtr_r -1; ride strings +3 in the verse; eq gtr_r -2 dB at 3.3 kHz, lead -1.5 dB at 3.3 kHz (harsh presence) and
   +1.5 dB at 900 Hz (mid-forward, the Baker Street comparison).

Measured (dB vs the section lead; windows rock): verse rhythm -3.7 / low -2.4 / bed -10.8; chorus (hook) rhythm -2.5
/ low -3.4 / bed -5.9; solo -3.1 / -4.5 / -6.4; solo2 -3.5 / -3.0 / -6.8; chorus2 (hook) -3.6 / -3.6 / -4.7; outro2
-1.3 / -2.2 / -4.0. Whole song: bed -6.8 dB vs lead, lead -17.5 LUFS, drums -20.5, bass -23.8.

**The arc** (`ARC`, a utility first in the master chain ridden per section, 2-beat glides): intro -8, verse -7,
chorus -1.5, bridge -4, solo -6, solo2 0, break -9, chorus2 +0.5, outro -6, outro2 +0.5, end 0 then -14 over the
ring-out. The quiet sections stay under the glue and the limiter, the big ones hit them: the drama of a power ballad
(recipe: the chorus 3-5 LU over the verse) instead of one wall.

Open / accepted: the drums peak +4 dBFS into the drum bus (float, before the master: info); 'drums' and 'bass' share
60-250 Hz in the first solo (the bass ducks under the kick); the echo return is quiet (clean / piano sends only: the
hero has its own echo).

**Tone pass (2026-10-01, the v2 heavy hero, TONE.md):** the solos are the guitar hero's feature, so it sits in front
there: the hero wrapper rides it +1 dB in chorus / chorus2 / solo / solo2 / outro / outro2 (`sections=`), MIX rides
lead / lead_twin +2 dB more in the four solo sections, `s.carve(gtr_l, gtr_r, piano, key=lead, freq=1400, depth=3)`,
and the old +1.5 dB at 900 Hz on the lead is gone (the tube amp is mid-forward itself; -1.5 dB at 3.3 kHz stays).
Solo2, K-weighted, per 2 bars, pre-master: the lead vs the whole band -0.9 / -2.0 / +1.5 / -3.3 dB before ->
+2.1 / +1.4 / +4.3 / -1.0 dB after (median -2.0 -> +1.4 dB). `mix`: "moves: none - the balance is inside the targets"; the solos read
`balance_mid_high` ~+4 dB against the generic rock curve while the same span is within +-1.5 dB of Slash's solo at
0.8-6 kHz (TODO).
