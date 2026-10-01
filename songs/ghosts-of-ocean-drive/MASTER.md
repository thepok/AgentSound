# Ghosts of Ocean Drive - master

Mastering engineer pass after the mix (MIX.md). Platform `auto` (synthwave window -12..-9 LUFS, PLR >= 6, LRA 3-15),
reference The Midnight "Sunset" 4:00-4:30 against chorus2 (chorus vs chorus; analysed from the git-ignored
assets/refrences, never copied), and the synthwave profile.

## The plan and what was taken

`python -m agentsound master songs/ghosts-of-ocean-drive --ref <Sunset> --ref-start 4:00 --ref-end 4:30 --section chorus2`:

| plan | decision | why |
|---|---|---|
| eq: +1.5 dB bell 4 kHz Q 1 (the profile guard capped the wanted presence at +1.2) | **refused**; instead -1.0 dB bell 1.25 kHz Q 0.7 | the hook is a Salamander-based synth piano: no presence lift on a piano-led song ("es klingt hart"); the synthwave profile already reads presence +2.6 dB and flags `harsh` at 2-5 kHz, only Sunset reads it short. The one move both agree on is the mids (Sunset chorus2 +1.6 dB, profile +2.5..+3.4 dB): a broad, small dip |
| width x1 | kept (none) | width >150 Hz 56 % vs Sunset 59 % (within 1.5 dB); the song's width 1.25 + monobass 150 Hz stay |
| limiter: ceiling -1.2, release 120 ms | taken (release was 80 ms) | -1 dBTP after the mp3 encoder; a slower release pumps less on the gated drums |
| loudness: -11.7 -> -9.5 LUFS (+2 dB drive estimated) | **+2.0 dB** into every section's limiter drive (`MASTER_DRIVE`) | the post-pass (`plan.render()`, out/master/) calibrated +2 dB -> -10.8 LUFS, +3 dB (its max-drive cap) only -10.4 with LRA 6.2 -> 4.4: the song's limiter already works 3.5-4.5 dB in the choruses, so past +2 dB each dB bought 0.4 LU. Stopped there - the energy arc and the kick matter more than the last 0.4 LU |

In song.py (reproducible without out/): `mastering.apply(s, eq={'peak1.freq': 1250, 'peak1.gain': -1.0, 'peak1.q':
0.7}, limiter={'ceiling': -1.2, 'release': 120})` - the eq first in the master chain as `master_eq`, before the
retrowave eq / glue / tape / exciter / width / limiter - and `MASTER_DRIVE = 2.0` added to the per-section limiter
drive automation (the song automates `fx.limiter.gain`, so `loudness_change` on the static gain would do nothing).
The delivered file is the rebuilt `out/mix.mp3`; `out/master/mastered.*` is the +3 dB post-pass reference (not
delivered).

## Before / after (full song, `master --check` + report)

| measure | before | after |
|---|---|---|
| LUFS-I | -11.6 | -10.9 (window -12..-9) |
| true peak | -1.11 dBTP | -1.12 dBTP |
| LRA | 6.0 LU | 4.7 LU (3..15) |
| width >150 Hz / correlation | 53 % / 0.62 | 52 % / 0.64 |
| verse1 / chorus1 / chorus2 / breakdown / solo / chorus3 | -14.5 / -10.5 / -10.2 / -15.0 / -10.3 / -9.7 | -13.1 / -10.0 / -9.7 / -13.6 / -9.6 / -9.4 |
| bands vs synthwave profile (sub / bass / lowmid / mid / presence / air) | -3.5 / -1.0 / +0.5 / +2.4 / +2.0 / -2.0 | -2.5 / 0.0 / +1.1 / +2.5 / +2.6 / -2.2 |
| chorus2 vs Sunset: crest / kick punch / mid / presence | 12.4 / 13.0 / +1.6 / -3.7 dB | 11.8 / 12.7 / +1.0 / -3.6 dB |
| chorus3 vs Sunset: crest / kick punch / mid / presence | 12.2 / 14.4 / +1.5 / -3.4 dB | 11.8 / 13.6 / +1.0 / -3.1 dB |

The arc survives (verse1 -> chorus3 4.8 dB before, 3.7 dB after; the breakdown still the valley, chorus3 the peak).
`master --check`: true_peak / loudness / lra / mono_compat ok, no warnings; info only: streaming normalisation turns
it down 3.1 dB (Spotify -14), and the profile would like +2 dB of low shelf at 60 Hz.

## Refused / left

- The profile's +2 dB low shelf at 60 Hz: Sunset reads our sub +2.3 dB (chorus2) - the references disagree; not
  a master move.
- The presence lift (see above) and Sunset's loudness (-7.4 LUFS): both would cost the hook's warmth and the kick's
  punch, which is already 5-6 dB under Sunset (MIX.md, open issues).
- Streaming (-14 LUFS) was not asked for; the file is for listening / the phone.

## Revision (A&R issue 1)

- **Change:** `MASTER_DRIVE` is set per section: chorus1 +0.5, chorus2 +1.0, chorus3 +1.3, solo -1.3, other +0.5
  (was +2 everywhere).
- **Why:** the old drive pressed chorus 3 into a brick: 6.5 dB of limiting and LRA 0.7.
- **Result:**

| measure | before | after |
|---|---|---|
| chorus 3 drive | 6.5 dB | 5.8 dB |
| chorus 3 LRA | 0.7 LU | 1.1 LU |
| LUFS-I | -10.9 | -11.9 |
| LRA | 4.7 LU | 6.8 LU |
| true peak | | -1.13 dBTP |

- **Arc:** chorus 3 - chorus 1 is +1.2 LU, chorus 3 - solo +1.5, and verse 2 -> chorus 2 3.6.
- **`master --check`:** ok.
- **Refused:** the check's tone info, "-2 dB bell at 2 kHz". It would take back the hook's top, which the A&R asked
  for.
