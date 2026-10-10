# One More Round - mix

Profile `edm` (mixer + analysis). `python -m agentsound mix songs/one-more-round` findings, applied as the module-level
`MIX` in song.py:

- trims: pad +6 (bed vs lead -16 dB in the verse / breakdowns), chords +4, pluck +3 (the drops' width and bed),
  bass -1 (edm/reese's compressor moved into its mid layer: chain order), drums -1, lead -3 (the piano's transients peaked -0.5 dBFS pre-master and drove the limiter), riser -5
  (the builds were louder than the drops), vocal -1.5 (peaked +0.2 dBFS pre-master), chops -1 (-1.0 dB vs the lead
  in drop 1: an "other" part over the lead).
- rides: bass +2.5 drop / +7 drop 2, drums -1 drop / +1 drop 2 / -1.5 in the builds, pad +2.5 verse / -6 talk box
  (it masked the talk box at 250-800 Hz), vocal +1.5 verse / +0.5 drop 2.
- eq: chops -2 dB at 1.4 kHz (the piano's band in drop 1), chords -2.5 @ 350, pad -2 @ 400, lead -2 @ 450 (low mids
  +3.0 vs the edm reference -> +2.3).
- song code: the hero vocal ducks / carves pad + chords and dips pluck / piano / drums at 3 kHz; the drums carve 3 dB
  at 3.5 kHz under the chops; the master width 1.45 (mono < 150 Hz): the music above 150 Hz 30 % -> 41 % wide.

Result: 0 warnings, 6 info (moderate masking that alternates: kick / bass ducking 5.7 dB, the riser vs the hats in
the builds, the downlifter vs the hats), clicks 0, silent notes 0, flat_dynamics 0 (chords 5.2, piano 3.1, chops
4.4, talk box 6.5 dB per phrase; vocal 15.6 dB).

**Decision (drop 2)**: the mixer (K-weighted) wanted the kick and bass up against the sung chorus (bass -11.4 dB vs
the lead), singer.check (unweighted RMS) wanted the vocal over the bass. Went with the mixer and HUMAN_FEEDBACK
2026-10-02 ("die Stimme im Vergleich zum Rest zu laut": a sung lead sits IN the band): bass +7, drums +1, vocal +0.5.
The vocal still owns the presence band ("intelligible" in the build's vocals line); the remaining
`vocal_buried` line (vocal -22.0 vs bass -16.8 dB RMS) is the RMS check reading the sub - a TODO finding.
Open: `low_end_wide` in the breakdowns (no bass or kick there; residue at a very low level) - TODO finding.
