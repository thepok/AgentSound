# Patio de Naranjos - A&R

**Verdict: ship.**

Checked against the brief and HUMAN_FEEDBACK:

- The wish: a fingerpicked nylon guitar piece, the guitar alone, the tune on top of its own p-i-m-a / Travis / 16th
  patterns (thumb on the beat, fingers lighter, pinches), a few hammer-ons / pull-offs in the tune (~1 per 6 bars),
  fret noises from the samples. Form with a key change (E minor -> E major middle), a contrasting b, a climax in
  a2, a real ending (Picardy E major, rolled chord, harmonics).
- Report: 0 errors, 0 warnings, 0 info (classical profile); clicks 0; silent_notes 0 (873 notes); flat_dynamics no
  (note dynamics 11.7 dB, per-section spreads 5-12 dB); -19.1 LUFS-I, TP -1.30; width >150 Hz 18 %; reverb -11.9 LU.
- Images: overview / loudness (the arc rises a1 -> a2, no dead spots except the deliberate breath bars), bands
  (balance within +-3.5 dB of the classical reference, no sub - a guitar), spectrogram zooms (a1: the tune on top,
  the bass on the beat; coda: the rolled chord and harmonics ringing out), cover.
- Learned ears (CPU, instrument "classical guitar"): realism 83.9, PQ 8.54, CE 7.92, CU 8.29, P(real) 0.69;
  per section 75-88 (intro 88, coda 84.5; the sections with the tune 75-79).

Open (not blocking):
1. P(real) is lower where the tune plays (0.56-0.62) than in the accompaniment-only intro / coda (0.73-0.76); a
   softer tune (-6 velocity) did not change it. Worth a listen by the user; if the tune reads "placed", the next
   lever is the rest-stroke timbre (a melody layer brighter / rounder than the pattern), not the level.
2. The hammer-ons are emulated (a softer re-pluck): the pack has no slur samples.
3. No nylon-guitar reference recording to `compare` against.
