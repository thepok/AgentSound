# Gymnopédie No. 1 – étude notes

A benchmark étude (recipes/classical.md "Études"): Erik Satie's Gymnopédie No. 1 (1888, public domain) written note
for note as data (`satie_score.py`), performed by the system like a sensitive concert pianist, and measured against a
reference recording (`assets/refrences/Erik Satie - Gymnopédie No.1 [...].opus`, 3:37, git-ignored, **analysis only** -
nothing of it is copied, sampled or rendered). Goal: find the system's weaknesses, fix the library-sized ones, list
the rest.

Deliverable: `out/mix.mp3` / `out/mix.wav` / `out/cover.png` (3:36, -22.4 LUFS, TP -2.0 dBTP, LRA 12.1, 0 clicks,
0 warnings under the `piano` profile). Credit: Headroom Piano by Bengt Nilsson (CC-BY 4.0).

## 1. The score, verified by analysis

Written from memory of the score, then checked bar by bar against the recording (scripts in the git-ignored
`.scratch/gym/`):

- onsets (semitone spectrogram, 4096/8192-point FFTs, spectral-flux peaks) and a **template transcription** per onset:
  NNLS of the rise spectrum against Salamander piano-note templates (octave errors of plain peak picking vanish);
- **what sounds** 0.15-0.45 s after each chord (NNLS of the sustained spectrum), to tell held melody notes from
  re-struck chord tones;
- a **plain render of the score** (constant 72 BPM, flat velocities) analysed the same way: where the analyser makes a
  systematic mistake it makes it on both, so only real differences remain (e.g. the Salamander's C#4 also shows a
  2nd partial 4 dB over its fundamental - the recording's "C#5" at bar 17 is the low C#4);
- per bar a **chroma similarity** (cosine of the 12-bin chroma of the whole bar): the final render reads **0.926 mean /
  0.931 median** against the recording; the same render shifted by one bar reads 0.656 (so the metric discriminates).
  The lowest bars (9 = 0.79, 41, 59) differ in voicing (the pianist brings out the D in the Gmaj7 chord), not in notes.

Where memory and analysis disagreed, the analysis won:

| bars | first draft | from the recording |
|---|---|---|
| 17-19 (56-58) | C#5, F#5, E5 over F#m, Bm, Em | the low answer **C#4, F#4, E4** inside the chords (the chords re-strike C#4 / F#4); Em chords G3 B3 G4 and B3 D4 G4 |
| 21 (60) | D major | **D minor** (F3 A3 D4 F4): the dorian middle part begins |
| 22 (61) | D2 bass | **A2** soft, A3 C4 E4 (A minor) |
| 25-26, 30-31 | A3-based chords | **C3 E3 A3 E4** / **C3 F#3 A3 D4** over the D pedal |
| 35-36 / 74-75 | melody C#5 A4 E5 | melody **C#5 D5 E5** (first half) / **E5 D5 C5** (second), A4 at the top of the LH chord |
| 37 / 76 | F#4 held | F#4 / F4, chord B2 A3 D4 on 2, **E minor (E3 G3 B3 + E4 G4) on beat 3** |
| 38 / 77 | chord on 2 | **Am7 on the downbeat** (A2 A3 C4 + E4 G4 C5) |
| 73 | B4 A4 B4 | **B4 C5 F5** over A3 C4 F4 |
| 39 / 78 | - | D major (D4 F#4 D5) / the final **D minor** (D4 F4 A4 over D2 A2 A3) |

## 2. Measurements: reference / before / after

*before* = the same performance with the tools as they were (`ETUDE_BEFORE=1`: rubato 'arch', no lilt,
`sampled/studio_piano`, profile `classical`); *after* = the fixes below. Same song decisions (tempo map shape,
velocities, pedal, room) in both. Bar downbeats: the recording's from its detected bass onsets, the renders' from the
tempo map, both snapped to detected onsets (the detector's latency cancels).

| measure | reference | before | after |
|---|---|---|---|
| tempo median (BPM) | 69.8 | 71.1 | 70.8 |
| bar-tempo CV (%) | 7.3 | 6.6 | 6.3 |
| local bar rubato (% vs ±2 bars) | 2.87 | 3.84 | **2.90** |
| phrase-end tempo / phrase median | 0.964 | 0.961 | 0.954 |
| correlation of bar tempi with the reference | 1 | 0.82 | 0.83 |
| beat 2 position in the bar (beats, mean ± sd) | 1.066 ± 0.084 | 1.011 ± 0.027 | **1.063 ± 0.051** |
| beat 3 position | 2.008 ± 0.136 | 2.015 ± 0.101 | 2.023 ± 0.106 |
| deviation from a per-phrase metronome (ms RMS, downbeats) | 101 | 90 | 79 |
| melody dynamics per phrase (dB, 10-90 %, band level) | 9.0 | 7.0 | 7.7 |
| melody dynamics per phrase, the report's ear (dB) | - | 4.8 (flat under 4.5; 4.5 = FLAT in an earlier take) | **6.3** |
| melody over the beat-2 chord (dB) | 8.2 | 5.2 | **8.2** |
| melody over the bass note (dB) | 3.7 | 3.2 | 4.6 |
| section arc: middle part / coda over the theme (dB) | +5.3 / +4.0 | +4.0 / +1.4 | +6.0 / +2.1 |
| within-bar decay ("valley": peak - last 0.2 s, dB) | 11.6 | 15.4 | 15.3 |
| held E4 over bars 19-21 (dB/s) | -3.4 | -4.3 | **-3.3** |
| final chord decay (dB/s) | -3.8 | -3.7 | -3.5 |
| attack centroid, first 60 ms of melody notes (Hz, < 7.5 kHz) | 543 | 432 | 470 |
| sustain centroid, 300-360 ms (Hz) | 395 | 388 | 400 |
| loudness range (LU) | 9.9 | 9.4 | 12.1 |
| width above 150 Hz (%) / L-R correlation | 36 / 0.52 | 49 / 0.38 | **35 / 0.50** |
| spectral tilt (dB/oct) | -10.0 | -9.7 | -9.2 |
| tonal balance vs the recording (compare, loudness-matched) | - | bass 56-90 Hz -4.1, presence +2.8 | bass -3.6, presence 1.8-7 kHz +3.7 |
| tail T60 (compare, s) | 1.66 | 3.48 | 3.24 |
| report warnings | the recording itself under `classical`: 3 balance warnings (+7.5 bass, +14.4 lowmid, +5.1 mid) | 3 (classical balance) | **0** (`piano`) |

## 3. Weaknesses found

### Fixed at library level (with tests)

1. **Tempo map rubato too mechanical at the beat level.** Rubato was phrase-level only; the recording's pulse inside
   the bar is not metronomic: beat 2 (the chord) arrives **+0.066 beats late** on average (sd 0.084). Before: 1.011 ±
   0.027. Fix: `Song.lilt(span, beats={2: 0.06}, jitter=0.05)` - beat-level agogics on the tempo map (both hands
   together, downbeats stay, each bar gives its time back; finely sampled 1/32-beat curve, drift < 0.1 ms/bar).
   After: **1.063 ± 0.051**, metronome deviation 90 -> 79 ms (the recording 101). tests/python/test_tempo.py.
2. **Phrase breathing shape.** 'arch' (symmetric push-pull) gave 3.8 % local bar rubato vs 2.9 % in the recording,
   whose phrases move on through the middle (+2.5 %) and broaden into the last bar (-3.5 %). Fix: rubato
   `phrase='breath'` (on through 60 %, broadening in the last 40 %, zero mean). After: **2.90 %**.
3. **The `classical` analysis profile flags every real solo piano.** Two commercial solo recordings (this one and a
   Chopin nocturne) read lowmid +13..+14 dB and 3 balance warnings each under `classical` (an orchestra's curve).
   Fix: analysis profile **`piano`** (engine/analysis/Profiles.cpp; the classical thresholds with the mean spectrum of
   both recordings, limits wide enough for a warm hall and a close, bright recording; tests: its reference mix passes,
   is flagged under classical, boomy / glassy pianos are flagged).
4. **No sympathetic resonance: the pedalled piano decays too fast.** A held note decayed **4.3 dB/s** vs 3.4 in the
   recording. Fix: sampler param **`sympathetic`** (0 = off, bit-identical): 88 tuned comb strings excited by what is
   played, ringing while the pedal or their held key lifts the dampers (struck keys excluded, lowest octave
   uncoupled, block-size independent, click-free; silently held keys ring along). After (0.9): **3.3 dB/s**.
   tests/test_sampler.cpp.
5. **No half pedal.** The pedal was binary. Fix: `pedal` 0.5..1 = half pedal (pedal-held notes die faster: treble 16
   dB/s at 0.5, bass 40 % of that). Tested (C5 loses 6 dB, C2 4 dB over 1.1 s at 0.75); not needed in the Gymnopédie
   itself (a full change every bar).
6. **The sound: no patch voiced for a classical solo grand.** concert_grand (the recipe's "for classical") reads
   **10 dB darker above 3 kHz** than the recording; the Salamander patches read **123 % wide** (the player's
   perspective); studio_piano's velsens 0.7 squeezed a p-mp melody (flat_dynamics, melody only 5.2 dB over the chords).
   Fix: **`sampled/recital_grand`** (Headroom C3, velsens 1.0, width 0.75, sympathetic 0.9, hall -11). After: melody
   over chords **8.2 dB** (recording 8.2), width **35 %** (36), tonal balance within ~4 dB in every band, 0 warnings.
7. **Docs**: recipes/classical.md "Solo piano" + "Études" (the method), COMPOSE_API (lilt, breath, sympathetic, half
   pedal), RENDER_FORMAT (piano profile), PARAMS.md.

The jazz benchmark songs/perry-street-rain renders **bit-identical** with the new engine (sha256 9E2FE44C...,
old and new engine). Engine ctest 20/20, Python 840 tests OK.

### Open gaps (engine-sized or not done)

- **Within-bar decay still too deep: 15.3 dB vs 11.6** (resonance fills it, the wider velocity range deepens it again).
  The pedal is a note-holding switch plus a comb halo, not a damper / soundboard model: no aftersound (two-stage string
  decay), no soundboard coupling between the notes of a chord, no "pedal before the note" bloom, no partial
  re-damping when the pedal is only half lifted at a change. The final-chord decay matches (-3.5 vs -3.8 dB/s).
- **Attack brightness of the soft layers: the attack is only 1.18x brighter than the sustain (470 / 400 Hz) vs 1.37x
  (543 / 395) in the recording.** The sampled pp-mp layers have no hammer "ping": a velocity-dependent attack
  transient (a short bright filter envelope per note, or hammer-noise samples) is missing in the sampler / patches.
- **Melody dynamics per phrase still 7.7 dB vs 9.0 dB** (the report's ear 6.3): `touch()` shapes one arc per phrase;
  a pianist also shapes single notes (the top of a leap, the dissonant note, the phrase's first note after a
  breath). A melody-aware `touch` (accent by harmonic tension / interval) is the next player-level step.
- **Rubato is not melody-aware**: 'breath' is a fixed shape per span; the recording lingers at phrase peaks and
  harmonic arrivals. A `rubato(..., peak=melody_clip)` shape (arch around the melody's goal note) is not built.
- **Two hands = two tracks** so the dynamics ear can judge the melody (a single piano track is classified as a bed);
  the two tracks then trigger a `masking` info (lowmid, b1 / b2) - a false positive for one instrument, and each
  hand's resonance bank only hears its own hand.
- **Tail T60 3.2 s vs 1.7 s** (compare): our last chord rings under the pedal into a 9 s tail; the recording's end
  may be cut or faded - not judged further.
- **LH-before-RH asynchrony** (25 ms in the performance) cannot be measured in the mono mixture with these tools
  (onsets are ~12 ms frames, bass and melody overlap spectrally); release / pedal noises not analysed.
- **References are lossy web encodes** (the top above ~12-16 kHz is cut): air / brilliance comparisons are
  unreliable, the `piano` profile does not demand a top.

## 4. Reproduce

```
python -m agentsound build songs/gymnopedie-etude                    # after
ETUDE_BEFORE=1 python -m agentsound build songs/gymnopedie-etude     # before (studio_piano, arch, no lilt, classical)
python -m agentsound compare songs/gymnopedie-etude --ref "assets/refrences/Erik Satie - Gymnopédie No.1 [S-Xm7s9eGxU].opus"
```
