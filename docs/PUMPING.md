# Endless orchestra: pumping diagnosis, 2026-10-25

## Finding and scope

The strongest repeatable contributor in the inspected exposed-wind passages is the **extra automatic phrase
arc**, layered on top of the written dynamics and symphony's motif/phrase offsets. This is excessive generated
performance contrast, not evidence of a hidden master-volume automation bug. The clarinet's velocity-derived
live dynamics amplify the contour and make it dominate the mix, then disappear again. Reducing that extra arc
improves three matched seeds. It does not eliminate all fast swings or establish a subjective listening preference.

Input: `D:/tmp/orch1h`, **17 pieces, 61.24 minutes**, not 25. Baseline code: `ddc8bbe` (only the user's feedback
after `f1ced2e`). All tunes were reconstructed with `endless.run.load_scored`, using the saved `compose` seed,
mood, swing and set plan; no fresh best-of-N selection. The first replay's momentary loudness differs from the
original MP3 by only 0.0013 dB on average. No audio was played.

## Measurements and attribution

The initial whole-corpus scan used BS.1770 K-weighting at 24 kHz, 400 ms windows at 100 ms hops. Final A/B reports
use the same coefficients at 48 kHz (`engine/analysis/Loudness.cpp`). A candidate is a local peak with a rise AND
fall of at least 3 dB, each flank 0.5–2 seconds away; silence/quiet tails and one-way fades are excluded.
There are **664 candidates**; each piece's 95th-percentile absolute one-second change is **5.36–6.88 dB**.
These numbers measure fast fluctuation, not necessarily bad playing. The candidate ranking is in
`D:/tmp/pumping/baseline.json`; all 17 loudness traces are alongside it.

Selected worst moments (smaller of the two flank-to-peak differences):

| Seed / piece | Peak time | Swing | Evidence / classification |
|---|---:|---:|---|
| 4292 / Mountains of the North | 0:08.5 | 10.89 dB | Exposed guitar attack/decay; do not classify as global gain riding |
| 4264 / Overture: Wild Wings | 1:21.2 | 9.53 dB | Clarinet dominates; bass/cello remain nearly steady |
| 4242 / Wings of the Sea | 0:34.7 | 9.48 dB | Clarinet dominates; phrase arc is the strongest isolated contributor |
| 4242 / Wings of the Sea | 1:35.1 | 9.48 dB | Violins I motif/entry; not removed by disabling long-note swells |
| 4255 / Mountains of the Valley | 2:32.7 | 9.46 dB | Ranked for further inspection; no stem-based attribution claimed |
| 4253 / Northern Fires of the Dawn | 2:03.2 | 8.07 dB | Clarinet phrase, following a similar surge at 2:00.2 |
| 4242 / Wings of the Sea | 0:46.3 | 7.66 dB | Written simultaneous string/brass sforzando; retain the accent |

Stems and compiled lanes establish that the selected clarinet surges are upstream of the master:

* **4242, 33.6 / 34.7 / 35.8 s:** clarinet dry 400 ms RMS is **−32.21 / −15.50 / −26.25 dBFS**.
  The score map rises gently **59.39 → 62.05 → 64.72** velocity units. The played clarinet notes instead rise
  **66 → 80 → 92 → 101**, then fall; their `instrument.dynamics` lane reaches **0.79528**.
* **4253, 121.8 / 123.2 / 124.3 s:** clarinet **−42.19 / −21.70 / −89.42 dBFS** (the last value is its rest),
  while the score map is **62.96 → 63.71 → 64.29**. Played velocities rise **47 → 47 → 61 → 80**.
* **4264, 79.4 / 81.2 / 82.0 s:** clarinet **−44.93 / −17.87 / −58.75 dBFS**; cello
  **−28.71 / −27.74 / −28.59 dBFS**, bass **−35.53 / −34.63 / −34.90 dBFS**. A master-only gain change cannot
  produce that separation. Score map **64.20 → 65.29 → 65.78**, played clarinet **54 → 75 → 79 → 79 → 90**.

Exact notes, beats (including fermatas), lanes and stem readings: `D:/tmp/pumping/evidence.json` and
`score_maps.json`. Raw RMS readings here are deliberately distinguished from the K-weighted mix measurements.
The oscillations largely *do* follow the generated note dynamics. Their excessive automatic shaping, rather
than an unexplained mismatch with those velocities, is what the fix addresses.

## Controlled ablations

Seed 4242, same saved composition, at **34.7 s**:

| Intervention | Swing |
|---|---:|
| Baseline | 9.48 dB |
| Automatic long-note swells off | 9.48 dB |
| TECH off | 9.48 dB |
| Score-follow ramps off | 9.57 dB |
| Master compressor removed | 9.25 dB |
| Symphony SHAPE offsets zeroed | 8.39 dB |
| Extra `Score._shape` arc removed | 3.21 dB |
| SOLO off (different players) | 1.41 dB |
| Proposed fix: extra arc at 30% | 5.30 dB |

The first six ablations isolate mechanisms; SOLO off also replaces instruments, so it is evidence about the
exposed-player interaction, not a reason to remove solos. The diagnostic monkeypatches live only in
`D:/tmp/pumping/render_probe.py`; production code uses the explicit flag below.

Seed 4264, whole-piece p95 one-second change / candidates per minute (24 kHz diagnostic):

| Variant | p95 dB | Candidates/min |
|---|---:|---:|
| Baseline | 6.15 | 10.66 |
| SOLO off | 6.06 | 10.04 |
| CHOIR off | 6.27 | 10.98 |
| COLOUR off | 6.56 | 11.56 |
| TECH2 off | 6.34 | 11.60 |
| Sample repair off | 6.15 | 10.66 |
| SHAPE3 off | 5.58 | 11.30 |
| Extra arc at 30% | 5.76 | 9.41 |

COLOUR off changes duration (191.59 → 187.08 s); SHAPE3 off changes the form (255.15 s), so their absolute
timestamps are not aligned comparisons. These are feature screens, not isolated gain tests. CHOIR/COLOUR/SOLO/
TECH/TECH2/SHAPE3 switches use `genres` APIs. No bus compressor or sidechain exists in the inspected baseline;
the hall has a convolver and EQ only. Its send automation is confined to the final ring. Loudness normalisation
is not an active time-varying stage. The master is EQ → RMS compressor (120 ms / 2.5 s) → limiter: compressor
bypass does not remove the diagnosed sparse-phrase surge. No evidence implicates seam repair at these moments;
this does not exonerate every loop or release sample throughout the library.

## Fix, regression and reproduction

`Score._shape` (`bandlib/scoring.py`) adds `k * (touch(40,80) - 60)` to each part. Romantic phrasing raises k
by 1.2; `endless/symphony.py` also supplies the SHAPE offsets and line-phrasing floor. The solo clarinet uses live
sample layers, `dynrange=20` and `velsens=0.35`, so the contour is strongly audible. The fix scales only the
extra touch arc (including that floor) by **0.3**, at its symphonic call site. It keeps a smaller contour gesture
and leaves the common player, original notes, score map, technique palette, long-note swells and master intact.
No C++ DSP or sample files change.

**Default off**: `genres.symphony_pumping(True)` enables it; `False` restores the original render.
`shared_plan.py --flag pumping` / `--flag nopumping` expose the same switch. It changes no random draws or set
planning. `tests/python/test_endless_pumping.py` checks deterministic replay, off round-trip, unchanged composed
score/orchestration/master, plus detection of a synthetic repeating 8 dB envelope and rejection of silence,
constant level and monotonic fades. The final three off renders are also checked against the pre-fix compiled
JSON and PCM, not just against a same-version round trip.

```
# In PowerShell, for this machine's existing scientific Python:
$env:TMP = 'D:/tmp/pumping'; $env:TEMP = $env:TMP
$env:AGENTSOUND_SAMPLES = 'D:/Repos/AgentSound/assets/samples'
$env:AGENTSOUND_ENGINE = 'D:/Repos/AgentSound/build/agentsound.exe'
py -3.12 tools/pumping_ab.py D:/tmp/orch1h/001-wings-of-the-sea --out D:/tmp/pumping/ab/4242
py -3.12 tools/pumping.py D:/tmp/pumping/ab/4242/after/mix.wav --out D:/tmp/pumping/after.json
py -3.12 tests/run.py endless orchestra analysis
```

The diagnostic can add `pumping` to an existing report with `--report`; it deliberately adds no automatic
`gain_riding` verdict, because the corpus's guitar attack and written accents demonstrate the false positives.
The A/B runner writes `before.mp3` / `after.mp3` per seed, full float WAVs, stems, compiled render JSON and reports
under `D:/tmp/pumping/ab/{4242,4253,4264}/`. Both versions use the unchanged master, with no loudness matching.
`D:/tmp/pumping/results.json` contains the final 48 kHz numbers and PCM hashes; `comparison.png` plots the passages.

## Final A/B results (48 kHz, complete pieces)

| Seed | Fixed-window swing before → after | p95 1 s change before → after | Candidate count | Integrated LUFS |
|---|---:|---:|---:|---:|
| 4242, 34.7 s | 9.48 → 5.30 dB | 6.09 → 5.68 dB | 42 → 36 | −15.8 → −16.1 |
| 4253, 123.2 s | 8.07 → 4.06 dB | 5.94 → 5.32 dB | 44 → 38 | −16.1 → −16.4 |
| 4264, 81.2 s | 9.52 → 4.00 dB | 6.15 → 5.74 dB | 34 → 30 | −15.9 → −16.2 |

All six WAVs have their full decoded length, finite samples and zero reported clicks, and pass the existing
endless delivery gate. All six MP3s decode to the expected full duration. All three flag-off
compiled JSONs and PCM arrays are identical to the pre-fix replay. Candidate count falls **120 → 104 (13.3%)**.
Long-term loudness range is retained (11.7 → 12.1, 10.1 → 10.4, 9.5 → 9.8 LU), rather than compressed away.
The final fix preserves separately-created choir/guest phrasing; the initial monkeypatch screen was global,
so its 4264 p95 of 5.76 is slightly different from the production fix's 5.74.

Limitations: some individual attacks still have large swings, and some become larger. At 4242 the violin solo
gets an informational low-spread note for one of two phrases; its overall phrase spread is still 5.5 dB against
a 4.5 dB threshold (`flat: false`). Leave the switch off by default pending listening review.

Validation: `py -3.12 tests/run.py -j 4 endless orchestra analysis` ran **335 tests in 14 modules**. Eleven modules
passed; three modules had five environmental errors when Python `TemporaryDirectory` directories denied writes
inside this Windows sandbox (`test_endless`: 1, `test_endless_score`: 1, `test_sampled_orchestra`: 3). A minimal
`tempfile.mkdtemp()` followed by `Path.write_text()` reproduces the denial with both Python 3.12 and 3.14.
No assertion failures occurred in this final run. The **four new regression tests pass**, as do the **11 README
tests**, the shared-plan flag round-trip and `git diff --check`. Logs: `D:/tmp/pumping/tests-retry.log` and
`tests-readme-final.log`. These environmental errors are reported, not suppressed by modifying the tests.

Operational note: redundant full-length ablation stems exhausted the remaining D: space. They were removed;
affected final renders and tests were rerun. The engine can report success on a disk-truncated WAV, so delivery
checks include decoded duration and finite samples, and the A/B runner checks free space before rendering.
The original repository's `.git` is read-only in this session; a Git bundle clone at
`D:/tmp/pumping/pumping-fix` holds the `pumping-fix` branch. The original master checkout is untouched.
