# MASTER - Ashes and Chandeliers

Mastering engineer's hand-over. The input was the mix of MIX.md, render 3: -15.6 LUFS-I, TP -1.19 dBTP, LRA 15.1 LU,
mid +3.9 / presence +2.9 against the film balance, 0 warnings.

## Platform and target

- **Profile `film`, platform `auto`.** The profile's window is -16..-10 LUFS, LRA 5-20, PLR >= 8.
- **A symphonic master, not a loud one.** The piece lives on a range of about 17 LU, from the candlelit ballad
  (-25..-21 LUFS) and the coda (-27) up to the finale / summit (-12..-10). The mix sat inside the window, so `auto`
  kept its level: target -15.5, the nearest edge plus 0.5 LU.
- **Streaming.** I did not push to -14. Streaming normalisation raises this master about 1.6 dB when the true peak
  allows, and Apple Music turns it down 0.4 dB. A louder master would have cost the loud tutti LRA for no gain after
  normalisation.
- **No reference.** `assets/refrences/` has nothing symphonic or rock-opera (only synthwave, Baker Street, Chopin and
  Satie). I matched against the film profile's reference spectrum instead (dead band 1.5 dB, strength 0.75).

## Decisions (`python -m agentsound master songs/ashes-and-chandeliers`, then `--render`)

- **Check first.** Before the mix pass, `master --check` returned `tone_band` warnings for mid +4.3 and presence
  +3.5. Both were too big for the master, so they went to the mix (MIX.md). After the mix, `check` had no tone
  warnings.
- **EQ** (`master_eq`, first in the chain, before the film chain's own dips / air / glue):
  - +1.9 dB low shelf at 60 Hz. The sub sat 1.9 dB under the film balance, and a tutti with taikos, timpani and
    basses wants the floor.
  - -1.4 dB broad bell at 1.25 kHz, Q 0.5. This is the centre of the remaining mid surplus. It is broad and gentle,
    and it does not dull the lead.
  - The fit's rms error was 0.19 dB. Every move stays well inside +-3 dB.
- **Width:** x1. The width above 150 Hz is 45 % in the post-pass measurement, inside the profile's 30-120 %. The
  song's mono-bass stage at 120 Hz (low-end correlation 0.96) stays before the limiter.
- **Limiter:**
  - Ceiling -1.2 dBFS, so the true peak stays <= -1 dBTP.
  - Drive +0.6 dB (the plan's estimate; the post-pass needed 1 pass).
  - Release 200 ms. I kept the film chain's slower release instead of the plan's 120 ms (`auto`'s pop default), so
    the orchestral tutti does not pump. The post-pass with 120 ms landed within 0.1 LU of the in-song result below.

In song.py (end of `build()`):

```python
mastering.apply(s, eq={"low.freq": 60, "low.gain": 1.9, "low.q": 0.7071, "peak1.freq": 1250, "peak1.gain": -1.4,
                       "peak1.q": 0.5}, limiter={"ceiling": -1.2, "release": 200.0}, loudness_change=+0.6)
```

The final master chain is:
1. `master_eq`
2. The film eq: -2.5 dB at 400 Hz, -3.5 dB at 1.1 kHz, +4 dB air above 7.5 kHz
3. Glue compressor: 1.6:1, 1-2 dB
4. Width, mono bass at 120 Hz
5. Limiter: -1.2 ceiling, 200 ms release, +0.6 dB

## Results

| | mix (render 3) | post-pass `mastered.wav` | delivered rebuild `out/mix.mp3` |
|---|---|---|---|
| LUFS-I | -15.6 | -15.7 | **-15.6** |
| true peak (dBTP) | -1.19 | -1.20 | **-1.19** |
| LRA (LU) | 15.1 | 14.7 | **14.8** |
| PLR (dB) | 14.4 | 14.5 | **14.4** |
| width above 150 Hz | 45 % | 45 % | 39 % (report, pre-master sum) |
| correlation | 0.54 | 0.57 | 0.57 |
| mid / presence vs film | +3.9 / +2.9 | +2.8 / +2.5 | **+3.0 / +2.7** |
| sub / bass vs film | -1.9 / -0.7 | -0.9 / -0.4 | **-0.9 / -0.4** |
| warnings | 0 | 0 (new none) | **0**, 0 clicks |

**Energy arc after the master (section LUFS):**

| section | LUFS |
|---|---|
| intro | -25.3 |
| theme | -23.4 |
| theme2 | -21.8 |
| middle | -21.4 |
| return | -20.6 |
| stab | -17.7 |
| calls | -16.0 |
| masque | -21.4 |
| ascent | -13.2 |
| riff | -14.1 |
| anthem | -14.7 |
| anthem2 | -13.1 |
| solo | -13.6 |
| riff2 | -13.3 |
| break | -17.0 |
| finale | -11.7 |
| summit | **-10.5** (the peak; short-term max -9.7) |
| fall | -22.8 |
| coda | -26.9 |

## `master --check` on the delivered build

- **ok:** true_peak -1.19 dBTP, loudness -15.6 inside -16..-10, LRA 14.8 inside 5..20, mono_compat (correlation
  0.57, the mono sum about 1.1 dB quieter).
- **info:** normalisation (+1.6 dB on Spotify / YouTube, -0.4 dB on Apple Music).

## Refused

- **A louder master** (`loud` / `streaming`): it would squash the tutti for nothing after normalisation. The dynamic
  range is the point of this piece.
- **Any width boost:** the width is already inside the profile. The narrow anthems are a panning issue in the mix
  and the sound design (MIX.md), not a master issue.
