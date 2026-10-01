# MIX - Ashes and Chandeliers

Mix engineer's hand-over. The input was the producer's build 5 (c4af1f7). The moves are in the module-level `MIX` in
`song.py`, and the CLI applies them at build time. I made 3 mix renders (renders 1-3) and one final build with the
master chain (render 4). Mix profile `film`.

## Roles: judged by hand, part by part

`python -m agentsound mix` inferred the oboes as the lead. It judged only the masque and suggested "trim flutes
-4 dB". That suggestion is wrong: the flutes carry the waltz tune, and the oboes only double it. With explicit roles
(`mixer.plan/check(..., roles=...)`), the single-lead model still does not fit this piece, because the tune
changes hands:

- Part I: piano
- calls: the male choir calls, and the female choir answers
- masque: flutes and oboes
- ascent: the choirs
- riff: the rhythm guitars
- anthem and solo: gtr1
- finale and summit: a doubled melody on gtr1, violins 1 and 2, flutes, horns and choir

With gtr1 as the only lead in the finale, `check` flagged `bed_too_loud` +4.3 / +5.6 and proposed -6.5 dB trims on
the violins, horns and choir. Those instruments are the tune itself, so I did not apply those trims. I measured the
balance with the tune's carriers named per section instead (a scratch script over `mixer.View`: K-weighted bar levels, the same
maths as `mixer.measure`).

## Before / after (dB vs the tune per section, pre-master; section LUFS after the master)

| section | LUFS before -> after | tune | bed | rhythm | low | loudest other part |
|---|---|---|---|---|---|---|
| theme2 | -21.9 -> -21.8 | piano | -8.7 | - | -9.0 | cellos -10.3 |
| middle | -21.4 -> -21.4 | piano | -4.5 | - | -9.3 | violins1 -8.3 -> -8.6 |
| return | -20.7 -> -20.6 | piano | -3.5 -> -3.8 | -8.1 | -6.5 | violins -8.1 -> -8.3 |
| calls | -16.1 -> -16.0 | male + female choir -17.8 -> -17.1 | +2.5 -> +1.5 | -3.8 -> -4.6 | -5.4 -> -6.1 | timpani -3.8 -> -4.6 |
| masque | -20.7 -> -21.4 | flutes + oboes | -6.8 | -20.3 | -7.7 | clarinets -8.3 |
| ascent | -13.0 -> -13.2 | the choirs | +0.7 | -7.5 -> -7.3 | -15.0 -> -14.7 | horns -4.3 -> -4.1 |
| **riff** | **-14.9 -> -14.1** | riff guitars -18.1 -> -15.9 | -4.7 -> -7.2 | **-0.8 -> -2.9** | **-1.1 -> -3.7** | kit -0.8 -> -2.9 |
| anthem | -14.7 -> -14.7 | gtr1 -17.6 -> -17.6 | +0.3 -> 0.0 | -3.9 -> -3.8 | -3.0 -> -3.4 | bass -3.0 -> -3.4 |
| anthem2 | -13.1 -> -13.1 | gtr1 -16.9 -> -16.2 | +2.2 -> +1.0 | -1.7 -> -2.4 | -1.4 -> -2.4 | kit -1.7 -> -2.4 |
| solo | -13.7 -> -13.6 | gtr1 -16.0 -> -15.7 | -1.2 -> -1.7 | -2.3 -> -2.7 | -3.8 -> -4.4 | kit -2.3 -> -2.7 |
| **riff2** | **-13.8 -> -13.3** | riff guitars -18.1 -> -15.9 | +1.4 -> -0.9 | -0.6 -> -2.7 | -0.5 -> -3.2 | trombones **+0.3 -> -1.9** |
| finale | -11.3 -> -11.7 | the doubled melody -12.0 -> -12.3 | **+0.2 -> -0.4** | -8.5 -> -8.2 | -0.5 -> -0.7 | cellos -4.9 -> -4.7 |
| summit | -10.1 -> -10.5 | the doubled melody | +2.3 | -9.3 -> -8.7 | -1.9 -> -1.4 | horns -4.5 -> cellos -4.8 |
| coda | -27.1 -> -26.9 | piano | -5.8 | - | -9.2 | violins2 -8.1 |

- In the finale, the piano's 8th chords went from -0.7 to -3.2 dB under gtr1.
- In the summit, choir_m went from +1.0 over gtr1 (it had been flagged `part_over_lead`) to -0.5.
- In the finale and summit, the doubled melody's own lead voices (violins 1 and 2, flutes, horns, choir) are counted
  as the tune, and the "bed" is the harmony under it. So a bed around 0 dB there means a real orchestral tutti, not
  a buried lead.
- In the rock sections, the lead gtr1 stays 2.4-3.4 dB above the loudest other part: the kit or the bass.
- The ballad bed (the string pad 8.7 dB under the piano in theme2, 3.8 dB in the return) is the arrangement's
  candlelight arc. It is outside the loudness window the mixer judges (sections more than 12 LU under the loudest are
  not judged), so I left it alone.

**Whole song:**

| | before | after |
|---|---|---|
| LUFS-I | -15.4 | -15.6 |
| true peak (dBTP) | -1.19 | -1.19 |
| LRA (LU) | 15.5 | 14.8 |
| PLR (dB) | 14.2 | 14.4 |
| balance vs film: mid | **+4.3 (warn)** | **+3.0** |
| balance vs film: presence | **+3.5 (warn)** | **+2.7** |
| balance vs film: lowmid | +3.0 | +2.6 |
| balance vs film: sub | -1.9 | -0.9 |
| warnings | 2 | 0 |
| clicks in the mix | 0 | 0 |
| lows correlation | 0.96 | 0.96 |
| width above 150 Hz | 40 % | 39 % |

**By render, mix only:**

| | render 1 | render 2 | render 3 |
|---|---|---|---|
| mid / presence | +3.8 / +3.1 (warn) | +3.8 / +2.9 | +3.9 / +2.9 |

The master's broad eq then took the mid / presence to +3.0 / +2.7.

## The moves (MIX in song.py) and why

1. **The riff hits** (the producer's weakness 3: the riff came in about 2 LU under the ascent's fermata). The riff
   guitars were 1-3 dB under the kit and bass, and in riff2 under the doubling trombones.
   - Move: gtr_l / gtr_r ride +2.5 dB in riff and riff2.
   - Result: riff -14.9 -> -14.1 LUFS, riff2 -13.8 -> -13.3. The guitars are now 2.9 dB over the kit and 1.9 dB
     over the trombones.
   - I also tried +1 dB in the anthems / solo (render 1). It added presence (gtr_r to 9.7 % of the presence band) and
     took the lead's margin, but gained only +1.6 % of width, so I dropped it.
2. **The lead guitar in front in the rock** sections.
   - Move: a -1.5 dB presence dip at 2.6 kHz (Q 0.8) on gtr1 (gtr1 was 22 % of the song's presence band), then its
     fader back up: trim +0.5, rides anthem +0.5, anthem2 +1.0, solo +1.0 dB.
   - Result: the kit went from 1.7 dB under the lead to 2.4 dB under it in anthem2, and from 2.3 to 2.7 in the solo.
     The pre-master peak of gtr1 is -5.5 dBFS before the rides.
3. **The finale tune on top.**
   - Moves: piano 8th chords -2.5 dB (finale), the drive bass -1.5 (finale and summit), choir_m -1.0 (finale) and
     -1.5 (summit), horns -1.0 and trombones -1.0 (summit, the brass pads over the climbing motif).
   - Why: the finale's low weight (basses, tuba, cellos) is the sound designer's and stays. The bass guitar was the
     low part with presence fizz (7.6 % of the presence band).
4. **The calls.**
   - Move: choir_m +1.0 dB in the calls.
   - Why: the call was 2.5 dB under the sum of the orchestral stabs and tremolos. It is now 1.5 dB under, and the
     stabs still land.
5. **Mid / presence surplus.** I carved it where it is not the tune:
   - hall return: -2.5 dB at 1.2 kHz (Q 0.6, the hall carried 14.7 % of the mid band) and -1.5 dB at 4 kHz
   - gtr2 / gtr3: -1.5 dB at 2.5 kHz
   - violins1: -1.5 dB at 4.5 kHz
   - choir: -1.5 dB at 1.3 kHz
   - gtr_l / gtr_r: -1.5 dB at 4.5 kHz (fizz)
   - bass: -2 dB at 3 kHz (the drive's fizz, not its growl)
6. **Space in Part III.** The rock sections measured "dry / narrow": reverb -15..-18 LU against the film space's
   -13 LU, and width above 150 Hz 22-29 % against 30 %.
   - Moves, per section (riff / anthem / anthem2 / solo / riff2 / break):

     | return | riff | anthem | anthem2 | solo | riff2 | break |
     |---|---|---|---|---|---|---|
     | plate | +4 | +6 | +6 | +6 | +4 | +4 |
     | hall | +3 | +5.5 | +4 | +6 | +3 | +3 |
     | room | +2 | +3 | +3 | +3 | +2 | +2 |

   - Result, wetness (LU):

     | | riff | anthem | anthem2 | solo | riff2 | break |
     |---|---|---|---|---|---|---|
     | before | -17.1 | -17.6 | -15.8 | -18.3 | -13.9 | -15.4 |
     | after | -12.4 | -13.1 | -11.9 | -13.5 | -10.3 | -12.9 |

     Riff, riff2 and break now read "lush" or "ok". The guitar orchestra blooms in the plate, and the solo's echo
     (-12.5 LU) is kept.

## Change of the master's input

The mix moves lowered the pre-master sum by about 0.2 LU: -15.4 -> -15.6 LUFS-I through the unchanged film chain
(render 3). The mastering engineer re-set the drive (MASTER.md).

## Open issues

- **anthem and solo** read "dry" by 0.1 / 0.5 LU (wetness -13.1 / -13.5 against -13). The Brian-May echo (-12.5 to
  -16.7 LU) gives these sections their space, and pushing the reverb further would wash the 138 BPM guitars.
- **anthem / anthem2 stay "narrow"** (width above 150 Hz 23 / 28 % against 30 %). The cause is the panning: the
  guitar orchestra's top voice is centred, and the second voice is at only -0.38. Riding the hard-panned rhythm
  guitars barely moves the width. This is for the sound designer: gtr2 / gtr3 at about +-0.6, or a wider double
  on gtr1.
- **For the sound designer:** 5 masked low-level clicks in `basses` (-34 dBFS, finale). They are inaudible in the mix.
- **For the arranger:** `flat_dynamics` at info level on 2 violins2 phrases and 1 horns phrase.
- **For the A&R to judge by ear:** the jump from the masque (-21.4) to the ascent (-13.2) is deliberate.

## Revision (after the A&R's "revise")

The MIX dict in `song.py` was reworked with the re-voiced finale (arranger) - every move is commented there:

- **Wall of guitars (A&R #3):** gtr_l / gtr_r +3.5 riff, +2.5 anthem, +3 anthem2, +3.5 solo, +3 riff2, -0.5 finale,
  -1.5 summit; bass guitar -2 dB in Part III (-1.5 in the solo); kit trim -1.5 (pre-master peak +2.7 -> +1.2 dBFS),
  kit +1.5 riff / +1 solo / +1 riff2; a second fizz dip at 3.3 kHz on the pair, 3.8 kHz on gtr2 / gtr3, 3.5 kHz on
  the drum bus. Result: the pair +5.4 / +2.8 / +3.4 dB over the kit in anthem / anthem2 / solo, width >150 Hz
  31.7 / 40.3 % in anthem / anthem2.
- **Band entry (A&R #2):** piano -4, choirs -1.5, horns -1.5, violins1 -1 in the ascent (the fermata no longer
  outshouts the riff); organ +3 anthem / +1.5 anthem2; gtr1 +1.5 anthem, +1.5 solo.
- **Finale (A&R #1):** the old "finale weight" gainDb lanes are gone (they raised the roots and lowered the tune);
  tune carriers +1..+1.5 (violins1 / violins2 / trumpets / horns / cellos), gtr1 +1 finale / summit, large chorus
  -1 / -2, bass guitar +1.5 / +3 and basses +2 / +2.5 (the thinned tutti lost its bottom: bass -2.8 vs film); a
  carve of violas + trombones at 450 Hz keyed by gtr1. The single-lead mixer still calls the finale bed +3.8 / +4.0 dB
  over gtr1 - that "bed" is the tune's own doublings (violins, choirs, horns); the non-tune parts sit 5.6 / 4.4 dB
  under the tune, the non-tune lows 7.9 / 8.5 dB.
- **Tone:** gtr1 +1 trim with dips at 1.1 and 4.2 kHz, violins1 2.8 kHz, violins2 3.5 kHz: presence +3.4 (warn) ->
  +2.6, mid +3.5, 0 warnings. The master's input moved +0.2 LU (-15.6 -> -15.4 LUFS-I through the unchanged chain).
- Still open: the flutes over the oboes in the masque (the flutes carry the tune, as before).
