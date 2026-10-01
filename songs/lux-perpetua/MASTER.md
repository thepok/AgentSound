# MASTER - Lux Perpetua

Mastering engineer's hand-over. The master chain lives in `song.py`: `mastering.apply(...)` at the end of
`build()`. The plan is in `out/master/master.json` (git-ignored).

## Platform and target

- **Platform `dynamic`.** This is a concert work (classical profile, the brief: "a safety limiter only, no glue
  compression"), so dynamics come first.
- **Target:** the middle of the classical window, -19.5 LUFS-I.
- **Limits:** true peak <= -1 dBTP; LRA inside 4-22 LU; PLR >= 12. The limiter may do at most 1.5 dB of peak
  limiting.
- **No reference:** there is no recording of K. 626 in `assets/refrences/`, so the tone is judged against the
  `classical` profile.

## Method

1. **The mix first.** I removed the producer's earlier master eq and rendered the finished mix (`MIX`) through
   only the limiter and mono bass, then ran `master --check`.
   - It read lowmid +6.5 / mid +6.6 dB vs the classical balance: two `tone_band` warnings ("too big for a master eq
     alone - fix it in the mix").
   - I sent it back to the mix. MIX.md has the carving and the stronger bass line.
   - The finished mix reads lowmid +4.6 / mid +4.8, inside the +5 limit, with 0 warnings.
2. **The plan.** `python -m agentsound master songs/lux-perpetua --platform dynamic` on that mix.
3. **The post-pass.** `--render`: 1 pass, drive +0.7 dB, no new warnings. It resolved the `dull` info.
4. **Into the song.** I pasted the plan into `song.py` (`mastering.apply`), rebuilt, and ran `master --check
   --platform dynamic` on the new build. It matches the post-pass (-19.6 LUFS-I, LRA 16.0, PLR 17.1).

## Settings

- **Eq `master_eq`**, first in the chain. It is broad and every band is within +-3 dB:
  - +2.8 dB low shelf at 100 Hz;
  - -0.5 dB at 400 Hz (Q 1);
  - -2.8 dB at 800 Hz (Q 0.7): the sampled sections and the choir read boxy there;
  - +0.5 dB at 8 kHz (Q 1);
  - +2.7 dB high shelf at 5 kHz: the sample sets are dark.
- **Width:** x1. Width above 150 Hz is 40 %, inside 15..110. Monobass stays at 120 Hz; the lows' correlation is
  0.97.
- **Limiter:** ceiling -1.2 dB, release 250 ms. Its gain went 1.2 -> 1.9 dB: the plan's +0.7 dB of drive on top of
  what the song had. It only catches the timpani / tutti peaks.

## Result (final build)

| measure | producer's master | this master | target |
|---|---|---|---|
| LUFS-I | -20.7 | -19.6 | -23..-16 (dynamic: -19.5) |
| true peak | -3.6 dBTP | -2.5 dBTP | <= -1 |
| LRA | 16.3 LU | 16.0 LU | 4..22 |
| PLR | 17.1 | 17.1 | >= 12 |
| width >150 Hz | 44 % | 41 % | 25..80 |
| correlation (all / lows) | 0.48 / 0.96 | 0.54 / 0.97 | |
| tone vs classical ref: sub | -12.0 | -9.8 | not checked low |
| tone: bass | 0.0 | 0.0 | |
| tone: lowmid | +3.8 | +2.3 | limit +5 |
| tone: mid | +3.5 | +2.3 | limit +5 |
| tone: presence | +0.2 | +0.9 | limit +3 |
| tone: brilliance | -7.3 | -5.7 | |
| tone: air | -11.5 | -10.3 | |
| warnings / info | 0 / 3 | 0 / 3 | 0 warnings |
| clicks in the mix | 0 | 0 | 0 |

`master --check` (platform dynamic) passes on true peak, loudness, LRA and mono compatibility; it shows only two
info lines:

- **normalisation:** Spotify would raise this by 5.6 dB, if the peak allows.
- **tone_profile:** "a further +3 dB low shelf and +3 dB high shelf would move it towards the genre average". I
  did not take it: it would stack past the +-3 dB a master may do. Brilliance and air are not warnings. What is
  left of the darkness is the samples' character (SSO / VPO sections and a sampled choir in a 1.9 s hall), not a
  master job.

## Refused, and why

- **More loudness.** `auto` / `streaming` would squeeze the 16 LU of drama (pp tremor to ff ira) that the piece is
  built on. -19.6 is the concert middle; a -14 LUFS version would need ~4 dB more limiting.
- **More width.** 41 % is inside the target. The choir's seat comes from the mix's seating, not a master widener.

## Revision (A&R round 1)

The mix changed under the master (figures up, organ down, the choir's box cut, the hall opened), so the plan was
redone the same way: a scratch copy of the song without the master eq, rendered through the limiter and mono bass,
then `python -m agentsound master <that mix> --platform dynamic`. Pre-master: -19.0 LUFS-I, lowmid +4.9, mid +4.9,
presence +1.7, brilliance -5.9, air -9.5 dB, 0 warnings (the first try read mid +5.7 / presence +3.2: two warnings,
handed back to the mix, MIX.md).

- **Eq `master_eq`:** +3.0 dB low shelf 100 Hz, -3.0 dB at 800 Hz (Q 0.7), +3.0 dB high shelf 5 kHz - the plan
  as it came, every band at the +-3 dB limit.
- **Limiter:** ceiling -1.2 dB, release 250 ms, gain 1.9 -> 2.8 dB (the plan's +0.9 dB of drive).

| measure | before (A&R) | after | target |
|---|---|---|---|
| LUFS-I | -19.6 | -19.5 | -23..-16 (dynamic: -19.5) |
| true peak | -2.47 dBTP | -1.20 dBTP | <= -1 |
| LRA | 16.0 LU | 15.1 LU | 4..22 |
| PLR | 17.1 | 18.3 | >= 12 |
| tone: lowmid / mid / presence | +2.3 / +2.3 / +0.9 | +2.6 / +2.4 / +1.4 | +5 / +5 / +3 |
| tone: brilliance / air | -5.7 / -10.3 | -3.9 / -6.9 | air -7 or better (A&R) |
| third octaves 500 Hz-3.15 kHz | up to +6.3 (630 Hz) | up to +5.2 (630 Hz); 1.25 k +4.4, 2.5 k +4.3, 3.15 k +4.7 | <= +4 (A&R) |
| third octaves 5-12.5 kHz | -3.2..-9.4 | -2.4..-4.4 | |
| warnings / clicks in the mix | 0 / 0 | 0 / 0 | 0 |

`master --check --platform dynamic`: true peak, loudness, LRA and mono compatibility ok; the tone_profile info still
asks for +3 dB shelves at both ends (and -0.9 dB at 630 Hz) - not taken, it would stack past the +-3 dB a master may
do. The mids that stay 4-5 dB over the genre average are the sampled choir and sections (four "ah" voices, the SSO
strings); the rest belongs to the parts, not the master.
