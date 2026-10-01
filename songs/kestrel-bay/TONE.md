# Kestrel Bay - the lead guitar tone

The user, about the first guitar-solo showcase: "die Technik ist bestimmt toll, aber die Gitarre klingt einfach lahm"
(the technique is surely great, but the guitar just sounds lame). Every fretwork move was in and the mids matched Baker
Street within 2 dB. This file is the tone pass on `layered/hero_guitar_heavy` (system level: the engine got a tube amp,
the patch went to v2), measured on kestrel-bay only.

How it was measured (scratch scripts, not in the repo): the lead stem of `build --section solo2 --stems` (same notes,
same automation); a held-note test (G4 B4 D5 E5 A5 C6, 3 s each at velocity 100, the patch alone, dry); the harmonics of
each held note 0.3 s in (h1..h10 in dB re the fundamental); band shares of the active audio; the report's note dynamics.
References for a recorded lead tone: the SampleRadar heavy-metal lead phrases and the "Lead Multi" notes (real amped
lead guitars, recorded dry) and Guns N' Roses "Sweet Child O' Mine" (video edit, in `assets/refrences/`, analysis only):
Slash's solo 4:06-4:36 and the first solo 2:05-2:34 (found on the spectrogram: long held bends with vibrato at 1-2 kHz,
no vocal), `compare` loudness-matched against the solo2 section.

## Diagnosis (v1, what made it lame)

1. **Hollow, octave-heavy harmonics instead of a singing fundamental.** A real amped lead note: the fundamental leads,
   odd harmonics strong - Lead Multi B4-G#5: h2 -13..-26 dB, h3 -2..-8 dB, even minus odd median **-16.9 dB**. Ours:
   even minus odd median **+2.6 dB**, h2 *over* the fundamental on G4 (+7.5) and D5 (+15.5 dB). Two causes:
   - the FSBS DI is a **bridge pickup**: its raw 2nd harmonic is +2.1..+2.9 dB over the fundamental (G4-A#5);
   - the amp was **one asymmetric waveshaper** per zone (`saturator` 'tube', bias 0.2 + its own 0.18, drive 25-32 dB):
     a single curve at fuzz gain amplifies whatever dominates its input and adds even harmonics - a fuzz box, not a
     cascaded preamp. (Even with the new amp, the bridge DI still came out h2-heavy: the source had to change too.)
2. **A smothered, band-limited spectrum** (the cuts that tamed the fuzz): 150 Hz / 24 dB high-pass, -2 dB at 300 Hz,
   -1.5 dB at 350, a -3 dB scoop at 450, low-passes at 7.5 kHz (cab eq) and 6.8 kHz (tone), -4.5 dB at 4 kHz, the mix's
   -1.5 dB at 3.3 kHz. Lead stem (solo2) vs recorded lead phrases:

   | band share (dB of the energy) | 80-250 | 250-500 | 4-8 k | 8-16 k | 4-8 k vs 1-3 k |
   |---|---|---|---|---|---|
   | recorded leads (7 phrases) | -6..-19 | -5.5..-14 | -13.8..-19.9 (mostly -14..-15) | -45..-49 | -11.2..-14.4 |
   | v1 | **-21.6** | **-19.5** | **-18.7** | -47.0 | **-16.9** |

   ~10 dB less body and ~4-5 dB less bite: a 500 Hz-4 kHz "telephone" lead.
3. **Not in front.** K-weighted, per 2 bars, pre-master: the lead sat **0.9-3.3 dB under the whole band** in solo2
   (median -2.0 dB; every band part alone was 5.5-10.6 dB under it, the wall together outweighed it).
4. **Against the record** (solo2 vs Slash's solo, loudness-matched): presence 2.8-9 kHz **-3.0 dB**, 1.1-1.4 kHz
   **-3.4 dB** (the first solo: presence -3.0 dB at 3.6-9 kHz).

Checked and NOT the problem:
- **Sustain.** Held test notes lost 3-6 dB in the first second, then held (median -5.1 dB at 2.9 s); the recorded Lead
  Multi notes fall 1.9-2.6 dB/s. The DI itself dies fast (B4-C#6: -13..-22 dB after 1 s), but the sustainer + gain
  held it.
- **The DI samples.** Clean (noise floor -86..-115 dBFS), long (4.5-17.6 s, no loops), 2 picking strengths x 4 takes;
  bends move the sounding voice (no sample switching inside a bend).
- **The cab IR.** The Jester Emerald Greenback 4x12 (SM57) matches the other 4x12s installed (Kalthallen V30,
  Overdriven US 4x12 V30, Jester Brutal): +6..+11 dB at 125 Hz, flat 0.5-5 kHz, -8..-10 dB at 6.3 kHz.
- **Aliasing.** The old saturator was 4x + ADAA: inharmonic energy -40..-59 dB.

## What changed

**Engine: `amp`** (`engine/fx/AmpFx.cpp`, `tests/test_amp.cpp`): a tube guitar amp head. An optional Tube Screamer push
(`boost`: x + clip(drive * hp720(x)), 5 kHz low-pass) -> `stages` 1-4 cascaded triode stages (`gain` spread over them;
`tight` input high-pass, `bright` cap; per stage a coupling high-pass, a cathode-bypass shelf so the lows get less gain,
an asymmetric soft clip with first-order ADAA, the phase inversion of a common-cathode stage, a Miller low-pass closing
stage by stage) -> the Marshall / Fender TMB tone stack (`bass` `mid` `treble`, Yeh & Smith's analytic transfer
function - checked against a nodal solve of the circuit within 0.1 dB) -> a push-pull power stage (`master`, a small
bias mismatch, `sag`: the supply drops under load - compression and a bloom) with `presence` / `resonance` on its
output (in the feedback loop they survive the clipping). 4x oversampled (polyphase IIR half-bands, ~5.5 samples of
latency like the saturator), double precision, a mono input processed once. Tests: gain 8 THD 0.43 vs gain 1 0.03;
+20 dB in -> +0.1 dB out at gain 8; a sine at a lead setting: h3+h5 -8 dB vs h2+h4 -37 dB; off-harmonic (aliased)
energy of a 1175 Hz tone at gain 9 / 4 stages -74 dB (2960 Hz: -41 dB); tone stack, presence, sag, strict params,
determinism, gliding automation.

**Patch: `layered/hero_guitar_heavy` v2** (`agentsound/patches/hero_guitar.py`):
- the DI as a **neck pickup**: the zones' 12 dB/oct low-pass key-tracked 100 % at ~1.3x the note (420 Hz at E4), no
  velocity tracking - the fundamental leads (`NECK`);
- per zone: sustainer -> **`amp`** (`LEAD_AMP`: 3 stages, gain 5.6 / 6.3 / 7.0 / 7.6 by zone, boost 6, tight 110,
  bright +1..+4, bass 5 mid 7 treble 7, presence 8, resonance 6, master 4, sag 0.3) -> the same Greenback 4x12 IR ->
  a mic roll-off (70 Hz, 6 kHz) -> the post compressor; zone levels unchanged (-9.6 / -6.4 / -3.2 / 0 dB);
- the hero's tone stage is now only an 80 Hz high-pass and a 7.5 kHz low-pass (no scoop, no fizz cuts), the tape stage
  without drive (tape drive after the amp put 8-16 kHz fizz back: 8-16 kHz share -42 dB without, -37 with);
- re-levelled to -18.0 LUFS on the audition phrase (gain -1.1 -> -3.8 dB).
- Tried and dropped: a filter envelope that opens the neck filter at every pick (2400 or 1200 ct, ~100 ms): the
  attack got 1.6-1.8 dB brighter than the body, but every onset equally so - the velocity part of the note dynamics
  went 1.9 -> 0.0 dB (TODO: velocity-scaled filter envelope). A veltrack on the neck filter (300-2400 ct) did the same
  and brought D5's octave back.

**Hero wrapper:** the guitar presets ride their **solo sections** like hooks (preset mix key `feature`: 'solo').

**Song (mix):** `hero(..., sections=[chorus, chorus2, solo, solo2, outro, outro2])` (the outro pair is the second solo);
MIX ride lead / lead_twin +2 dB in the four solo sections; the old +1.5 dB at 900 Hz on the lead dropped (the amp is
mid-forward); `s.carve(gtr_l, gtr_r, piano, key=lead, freq=1400, depth=3)`.

## Before / after

Lead stem, solo2 (same notes and automation; v1 = the delivered build, v2 = this pass, in its final mix):

| | v1 | v2 | recorded leads / record |
|---|---|---|---|
| held-note test: even minus odd harmonics (median, G4-C6) | +2.6 dB | **-8.3 dB** | -16.9 dB (Lead Multi) |
| held-note test: h2 / h3 re the fundamental, B4 E5 A5 | -7 / +10, -10 / -3, -8 / -9 dB | -29 / -8, -23 / -11, -25 / -6 dB | B4 -13 / +8, D5 -15 / -3, F5 -23 / -4 dB |
| held-note test: level at 2 s / 2.9 s (median) | -4.6 / -5.1 dB | -5.2 / -5.6 dB | -1.9..-2.6 dB/s |
| held notes in the solo2 phrase (slope, median) | -2.0 dB/s | -1.1 dB/s (a 2.3 s G5: -1.1 dB/s, spread 3 dB) | |
| inharmonic energy (noise, aliasing) | -42.7 dB | -41.9 dB | -39.0 dB |
| band share 80-250 / 250-500 Hz | -21.6 / -19.5 dB | -18.4 / -15.5 dB | -6..-19 / -5.5..-14 dB |
| band share 4-8 kHz / 8-16 kHz | -18.7 / -47.0 dB | **-14.3 / -42.3 dB** | -13.8..-19.9 / -45..-49 dB |
| fizz (4-8 kHz vs 1-3 kHz) | -16.9 dB | -11.3 dB | -11.2..-14.4 dB |
| lead vs the whole band, K-weighted, per 2 bars | -0.9 / -2.0 / +1.5 / -3.3 dB | **+2.1 / +1.4 / +4.3 / -1.0 dB** | (the sax rule: 1-2 dB over) |
| note dynamics (report, solo2) | 6.1 dB, 2.0 from velocity | 4.5 dB, 1.6 from velocity | >= 3 dB |
| note dynamics (report, whole song, 301 notes) | 5.4 dB | 5.8 dB, 3.9 from velocity | |

Against the record (solo2 section vs Slash's solo 4:06-4:36 / the first solo 2:05-2:34, loudness-matched,
mix - record): presence 2.5-6 kHz **-1.7 -> -0.6 dB** / -0.6 -> +0.5 dB; mid 0.8-2.5 kHz -0.3 -> -0.0 / +0.7 -> +0.9 dB;
1/3 octaves 3.15 / 4 / 5 kHz -4.3 / -3.7 / -4.0 -> -2.4 / -0.7 / -1.8 dB (first solo: -3.3 / -1.8 / -2.9 -> -1.4 / +1.2 /
-0.7 dB). Left over, not the lead's: bass +1.4..+2.6 dB at 56-140 Hz, air +3..+4 dB above 11 kHz, brilliance -3..-4 dB
at 6-12 kHz (the band and the master); the 1.6 kHz / 2 kHz lines (-5.9 / +3.7 dB) are where the two solos' notes sit.

Whole song (v2): -9.9 LUFS-I, true peak -1.20 dBTP, LRA 5.4 LU, clicks 0, warnings: only the known quiet echo return
(`reverb_inaudible`, MIX.md); `master --check` all ok. A solo2-only render reads `balance_mid_high` +4.9 /
`balance_presence_high` +4.0 dB against the generic rock curve (limit +4) - a guitar hero in front IS the mids; against
the GnR solo the same span is within +-1 dB in those bands (TODO: the rock profile).

A/B (18 s each, same spans of the old and the new full mix; `a_old` / `b_new`): `out/tone_ab/solo2_*.mp3`,
`outro2_*.mp3`, `bridge_feedback_*.mp3` (the held G#5 blooming into feedback); the lead alone with its own space
`lead_alone_solo2_*.mp3` (`b_new_levelmatched`: -2.8 dB, the same loudness as the old one - the new one is also
ridden 2 dB up in the solos).

Not verified by ear (numbers only): whether the tube amp sounds like a cranked Marshall or like a well-measured
plug-in, and the neck filter's warmth on the low notes. Listen to the A/B first.
