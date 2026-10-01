# Matryoshka - A&R

## Round 1 (build pass 7)

```
verdict: revise
summary: A warm, lifting piano-pop instrumental whose one hook really does run through everything - the key journey
  C / Am / F / G and the coda's stacked scales are clearly built and the arc climbs; but in the minor section the hook
  is buried under the cello, and the band sits narrow in the middle of the stereo field in every chorus.
issues (most severe first):
1. [major] the hook is under the cello in the second half of the minor section (bars 33-36, where the piano takes the
   hook back): cello -25.0 vs piano -26.4 dBFS RMS, bass -23.9 (report nodes[].barsRmsDb); mixer bed_too_loud
   +1.9 dB in 'minor'. The cello's +5 dB ride was meant for its own solo cycle (bars 29-32) but covers the whole
   section, and its counter-line's softer velocities do not reach the level (its dynamics are the bow player's).
   owner: arranger / mix-engineer   fix: play the counter-line as its own performance at a lower level (hornist
   place(level=...)), keep the ride for the solo cycle only.
2. [major] narrow image in the hook sections: width 9-15 % in build / chorus1-3 / verse2 (loudness.png section table;
   space verdict 'narrow' in 5 sections; pop wants 40-70 % above 150 Hz). The hero piano's melody layer is narrowed
   to 0.4 and it, the drums and the bass carry the choruses from the centre; the strings / pad bed sits 6-8 dB under
   the lead and adds little side signal.
   owner: sound-designer / mix-engineer   fix: open the piano's melody layer (width 0.4 -> 0.7), strings wider and
   ridden up ~1.5 dB in the choruses (the bed still >= 4 dB under the lead).
3. [minor] the coda's x16 choir line is faint in its first 8 bars (-33.6 dBFS RMS, 8 dB under the piano): the first
   pitch change of the line (C -> A at coda bar 7) is where the listener has to notice it.
   owner: mix-engineer   fix: the choir's live dynamics start at ~0.45 instead of 0.3.
4. [minor] 7 low-level loop-seam clicks in the choir's long "ah" notes (masked in the mix, clicks 0).
   owner: sound-designer   fix: none needed for delivery; a TODO for the choir_mixed loops.
checklist: [x] a song, not a loop (4 keys, 3 textures of the hook, build zoom, coda)  [x] no beepy lead (hero piano)
  [ ] lead in front (minor section - issue 1)  [x] real dynamics (piano 6.8 dB, flat_dynamics 0)  [x] played (pianist,
  drummer, bassist, bowed cello / violins)  [x] piano harmonized 44-100 %, fast figures budgeted, warm (no presence
  lift)  [x] hero sound  [ ] produced, not Gameboy - rooms and low end yes, width no (issue 2)  [x] clicks 0, TP -1.20
  [x] the brief's targets: 3:28, keys C Am F G C, the coda's scales audible (the bass x4 steps are visible in
  spectrogram_11_coda.png), LRA 5.5 LU, verse1 -13.2 -> chorus1 -10.6 -> chorus4 -9.1 LUFS.
keep: the build's zoom (x2 -> x1 band hits -> breath), the pivots (G# melting to G into F, C D into G, Dm7 G7 home),
  the verse = the inversion, the coda's layering, the drive arc, the pop cover (two spheres, one inside the scale of
  the other).
```

## Round 2 (build pass 9, after the round-1 fixes)

```
verdict: ship
summary: A warm, cinematic piano-pop instrumental that climbs through four keys on one four-note hook and ends by
  stacking it in five octaves at three speeds before one resolving C chord - pleasant first, clever second.
issues (most severe first):
1. [minor] the mixer still reads 'bed too loud -0.5 dB' for the minor section as a whole: its first 4 bars are the
   cello's solo (the piano only plays its left hand), which the one-lead-per-section measure counts as bed. In the
   piano's own bars (33-36) the piano is 7 dB over the cello (-26.2 vs -33.0 dBFS RMS) and 8 dB over the strings -
   deliberate, logged in TODO.md (mixer: lead per section / inside a section).
   owner: - (system)   fix: none for this song.
2. [minor] the choir's x16 line in coda bars 1-8 is 8 dB under the piano (-32.5 dBFS RMS; bars 9-16 -28.8): heard as
   a soft sustained line that moves at bars 7 / 9 / 13, not as a second melody - acceptable for the slowest scale.
3. [minor] 10 low loop-seam clicks in the choir stem (masked, mix clicks 0) - TODO.md.
4. [minor] sub -2.5 dB vs the pop profile after the +2 dB master shelf (master --check suggests more); a cinematic
   piano song, not a club track - leave it.
checklist: [x] a song, not a loop  [x] no beepy lead (hero piano, glass layer only as sparkle)  [x] lead in front
  (hooks: bed -5.1..-7.7 dB, rhythm -1.9..-3.3, low -1.6..-2.9 under the piano; minor: see issue 1)  [x] real dynamics
  (piano 6.8 dB per phrase, flat_dynamics 0)  [x] played (pianist 44-100 % harmonized, drummer pop with 2 flashy
  fills + a build, bassist locked to the hook-rhythm kick, bowed cello / violins)  [x] piano warm (no presence lift),
  fast figures budgeted  [x] hero sound  [x] produced (width above 150 Hz 63 %, reverb -14.4 LU, space lush / ok in
  every section but the 4-bar build - 'dry' on purpose: the band hits and the breath - full low end mono)  [x] clicks 0, TP -1.20 dBTP, silent notes 0  [x] the brief: 3:28 (+ tail),
  C -> Am -> F -> G -> C, the scales stacked in the coda, LRA 5.5 LU, arc verse1 -13.0 / chorus1 -10.3 / minor -13.3 /
  chorus4 -9.1 / coda -10.3 LUFS, 0 report warnings.
keep: everything listed in round 1; the wider piano melody layer (0.7) and strings (1.5).
```