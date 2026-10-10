# Letters to the Morning - A&R (round 2)

verdict: ship
summary: A warm, singing solo-piano piece with a clear arc: soft statements, a hook that climbs, a quiet interlude,
a build into one real climax and a hushed return. The left hand now rocks, rings and stops under the melody's
breaths instead of running, and the melody gains thirds, sixths, octaves and a turn as it returns.

Round 1 (revise) had two major issues: (1) the left hand was an unbroken, even 8th-note grid, 8 attacks in 56 of 69
bars, `comp` flat in 9 of 10 phrases, and the density did not rise into the climax; (2) the melody was a bare
single line in A1 / A2 / B1 / A4 (chordPct 9.2 %, no ornaments, A4 a copy of A1). The minors were the bass
(+8.7..+9.5 dB at 80-100 Hz), the vi-IV-I-V loop and the coda masking.

Round 2 was judged from scratch on the fresh render: report.json, loudness / tracks / spectrograms (B1, build,
climax), `mix` (findings), `master --check`, and the attack / gap / velocity / inter-onset numbers from
out/song.render.json. No reference audio exists, so no compare was run.

## What changed, measured
- **Breathing / density (round-1 issue 1): fixed enough.**
  - The left hand's figures now vary inside every section ('lilt', 'ring', 'colorhalf', 'half', 'quart').
  - The bars with exactly 8 attacks fell from 56 to ~35 of 69. A gap of half a bar or more now falls in A1 (bar 8),
    A2 (bars 16, 20), B1 (bar 24), A3 (bar 36), A4 (bars 60, 64), the interlude and the coda.
  - The climax is now a density lift: 16 attacks in bars 51 and 53 (the 16th sweeps under the peaks), against 8 in
    the build and 3-7 per bar in A4.
  - `comp` is flat in 3 of 10 phrases (was 9), with 5.2 dB of phrase dynamics (was 3.9) and velocities 18-55
    shaped by the crest. loudness.png shows deep short-term dips at the phrase ends of every A section.
- **The melody (round-1 issue 2): fixed.**
  - chordPct is 13.1 % (was 9.2). There are sixths / thirds under A2's answer, octaves under B1's held notes, sixths
    in A3 and chords in the climax.
  - One turn per theme statement (bars 11, 19, 59). These are ornaments, not fast two-key figures.
  - A4 is no longer a copy of A1: the answer is bent (Eb5-F5) and bar 62 has a sixth.
- **The bass**: +0.9 dB vs the profile (was +3.3). The third-octaves at 80 / 100 Hz are +5.5 / +6.2 (were +8.7 / +9.5).
- **Originality**: the vi-IV-I-V loop now runs only once as written (bars 21-24). B1's second half (Dbmaj7 -
  Ab/C - Bbm7 / Dbm6 - Eb) and the climax opening (Dbmaj7 - Eb/Db - Ab/C - Eb/Bb, a falling bass) leave it. The
  notation shares no figure with the model: the hook's degrees are 3-6-7-1 / 7-6-5-6-4, and the 16th neighbour-tone
  oscillation is absent.
- **The sound stays warm**: the climax spectrogram shows no 2-5 kHz glare. The producer's log measures the loudest
  frames' 2-5 kHz 10.1 dB under the body (inside the 9.4-11.7 dB the solo_piano fix reached).

## issues (most severe first)
1. [minor] **The drive from bar 37 to the fermata in bar 56 (~1:58-3:03) never stops for more than one beat.**
   The build and the climax keep the left hand moving in 8ths / 16ths, and the only real inhale is the quarter rest
   in bar 48. This reads as a deliberate long crescendo between two breathing halves, so it is not the "monotone
   line" again. If a later revision wants more air: let bar 44 ring ('C7:ring') or lift both hands for a half bar
   before the climax (bar 48 beat 3).
   owner: arranger
2. [minor] **The top is dark**: air -10.0 dB and brilliance -1.0 vs the piano profile. `master --check` proposes
   +2.9 dB at 8 kHz. This is a deliberate trade for warmth ("schrill und hart" rule) and well judged. Leave it, or at
   most +1 dB of shelf above 10 kHz on the room return.
   owner: mastering-engineer
3. [minor] **The quiet sections stay bass-led**: bass +6.9 in the intro and +5.7 in the interlude, the left hand
   alone. That is natural for those textures and inaudible on a phone.
   owner: sound-designer. No fix needed.
4. [minor] **Coda masking warning** (piano 56 % / comp 44 % of 250-800 Hz on the final chords). Benign: one piano's
   two hands on a held chord, and the melody's top notes (C6 / Eb6) stay clear.
   owner: mix-engineer. No fix needed.

## checklist
- [x] A song, not a loop: ten sections, the theme in four colours, the hook stated, re-harmonized, raised in the
  climax, echoed in the coda; a fermata climax and a rolled ending
- [x] No beepy lead: the warm Salamander grand, body in 250-800 Hz
- [x] Lead in front: the left hand is 4.5-9.7 dB under the melody in every judged section (`mix`, no moves)
- [x] Real dynamics: flat_dynamics 0; melody velocity 37-109, phrase spread 7.6 dB; the left hand is shaped
- [x] Played, not keyboard-like: melody rubato, phrase rubato, the lilt (8ths 338-419 ms around a 400 ms grid),
  pedal per harmony, rolled final chords
- [x] Piano harmonized / decorated, not a bare line; [x] fast two-key figures: none; [x] warm, not hard
- [x] Music BREATHES: rests at the phrase ends in both hands, density rising (climax 16 / bar) and falling (A4 3-7,
  interlude 2-5), register and dynamic contrast (pp-ff, Ab4-F6)
- [x] Produced: salon room + plate at -11.1 LU, width 38 %, full but no longer boomy low end
- [x] clicks 0, no clipping, true peak -1.20 dBTP
- [x] The brief's targets: -19.6 LUFS-I (-23..-16), LRA 16.5, PLR 18.4, form / key / length as written, an
  original piece in the style only

## keep
- The arc: intro -27.5 -> A2 -20.5 -> B1 -19.4 -> the interlude at -27.8 -> build -17.0 -> climax -15.7 -> A4 -24.2
  -> coda -26.0.
- The interlude's empty bars. The left hand stopping under the right hand's phrase-end rests. The 16th sweeps only
  at the two climax peaks.
- The theme, the hook and its new second half, the Fb -> Eb turn over Dbm6, the Gbmaj7 colour, the falling-bass
  climax opening, the deceptive cadence in A4.
- The solo_piano voicing with the 106 velocity cap and the -1 dB at 3.2 kHz. Do not add presence to "brighten" it.
- The ritardandi, the Eb7 fermata, A4 at 70 BPM, the coda at 66, and the final rolled Ab(add9) ringing out.
