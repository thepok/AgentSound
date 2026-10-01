# Nocturne op. 9 no. 2 - the etude

Chopin's Nocturne in E-flat major (1832, public domain) rendered note for note from the score, to find what the
virtual pianist cannot yet do. Reference: a concert recording (`assets/refrences/Chopin - Nocturne op.9 No.2
[9E6b3swbnWg].opus`, 4:29, Opus) - **analysis only**, never copied or committed.

Build: `python -m agentsound build songs/nocturne-etude` (the romantic pianist) and
`NOCTURNE_MODE=before python -m agentsound build songs/nocturne-etude` (the same score played with the tools that
existed before the etude). Measure: `python songs/nocturne-etude/measure.py` (numpy + ffmpeg; both files through the
same detectors: bar lines, melody vs bass onsets, figure timing, melody onset levels, chroma per bar).

## The score and how it was checked

12/8, Andante, E-flat major: an eighth pickup + 34 bars (A 1-4, A' 5-8, B 9-12, A'' 13-16, B 17-20, A''' 21-24,
coda 25-31, the senza-tempo bar 32 with the cadenza, 33-34 the end). The notes were written from the score and
then checked bar by bar against the recording: onset detection + top-voice pitch tracking (fundamental present,
octave / 12th ghosts rejected), precise peak frequencies (cents) for the fast figures, spectral peaks per eighth
for the bass and the chords, chroma per beat and per bar. The recording is the target where editions or the
pianist's ornaments differ.

What the analysis corrected (first draft -> recording):

- bar 1: G5 held five eighths, then F5 G5 F5 (quarter) Eb5 Bb4; beat 2 is a diminished seventh over the Eb pedal
  (B D Ab), beat 4 a D7 (b9) that goes to C7
- bars 2-3: the bar line falls before F5 (bar 3 starts F5 over Bb7), not before G5; bar 2 = G5, a chromatic turn on
  C5 (Db5 C5 B4 C5) over C7, C6 G5 Bb5 (beat 3: an E-diminished sonority over F - E dominates, not Db), Ab5 G5 over Fm
- bar 3 harmony Bb7 | G7/B | Cm | A-diminished (F# in the tenor), the bass Bb B C A Bb
- bar 4 cadence: Bb4 D6 C6 then the 16ths Bb5 Ab5 G5 Ab5 C5 D5 into Eb5 on beat 3
- bar 6: the grace turn B4 C5 Db5 C5 and the appoggiatura chain F-E, Ab-G, Db-C; bar 7: the trill on F5 ends in a
  chromatic Nachschlag E5 F5 into G5
- bars 13 / 21: the figure A4 Bb4 B4 Bb4 Db5 D5 G5 (not a turn); bar 16: Db6 C6 B5 Bb5 A5 Ab5 and a broken
  diminished chord F5 D5 B4 to Bb4 (the recording's inter-onset times rule out a full chromatic scale);
  bar 24: the chromatic descent Db6 .. Ab5 (slow, ~5/s) and the chromatic climb A4 .. D5 (~10/s) into G5 F5 Eb5
- B: a chromatic lament bass Bb A Ab (G) - Bb | F/A | Ab Ab7 Abm | Eb Fb7 C7-F7 Gm | Cm F7 Bb ... Bb7; the "E
  natural" seen over the A basses is the A's 3rd partial, not a note; the repeated E-flats in bars 10 / 18 (4 / 5
  strikes)
- coda: an Eb pedal alternating Eb and A-flat minor (Cb); bar 28 the descent G6 .. Eb5 over F7/A - Bb7; bar 31 the
  chromatic descent in octaves (C7/C6, B6/B5, A6/A5, Ab6, G6) over F7/A Bb7 G7/B Cm F7/A; the cadenza's figure is a
  four-note cycle Cb7 Bb6 C7 A6 (~15 cycles, ~11 notes/s by pitch tracking; the recording is tuned ~+15 ct)

Verification: chroma cosine per bar (1 = identical pitch-class energy) mean **0.82**; 29 of 34 bars >= 0.70, 22 >=
0.80; A sections 0.81, B 0.84, coda 0.82. The six bars under 0.70 (2, 6, 14, 22: the ornamented C7 bar; 28 the
con-forza run; 32 the cadenza bar) differ mostly in balance and timing (the recording's C6 / turn louder than its
G5, its bar-28 run soft) - the pitch classes are the same. Lower confidence: the inner left-hand voicings (the bass
notes' partials land exactly on the chord tones), the flourish before the cadenza in bar 32, bars 30-31.

## Before / after (same score, same tempo map, same sound; only the performance tools differ)

| measure | before (old tools) | after (`romantic`) | recording |
|---|---|---|---|
| melody vs bass at the bar lines, exact (note data) | -0.6 +- 2.2 ms (lock-step) | +10.4 +- 37.1 ms (60 % late, 17 % early) | - |
| same, detected in the audio (the detector reads ~+16 ms on a lock-step render) | 16.5 +- 9.3 ms | 19.2 +- 33.2 ms | 21.6 +- 46.6 ms |
| cadenza cycle (bar 32, 59 notes), exact | 95 ms every note, CV 0.00 | 54-131 ms, CV 0.23, ends 1.58x the middle | detected 8-12 notes/s, strongly uneven |
| fioritura bar 16, exact | CV 0.04, ends/middle 1.02 | CV 0.22, ends/middle 1.42 | detected CV 0.26, ends/middle 1.23 |
| fioritura bar 16, detected (both through the same detector) | CV 0.08, ends/middle 1.06 | CV 0.28, ends/middle 1.43 | CV 0.26, ends/middle 1.23 |
| fioritura bar 24, exact | CV 0.21 | CV 0.36 (slow descent, fast climb) | detected CV 0.65 |
| trill bar 7, exact | 22 notes, 12.7/s, turns back to the main note | 17 notes, 9.9/s, slow start, settles into E5 F5 -> G5 | detected 10.6/s |
| left hand vs melody (median velocity) | chords 49 / bass 50 / melody 67 | chords 31 / bass 39 / melody 70 | - |
| melody's pitch class share at the bar lines (voicing) | 0.51 | 0.64 | 0.67 |
| melody onset level spread per phrase (detected, dB) | 27.8 | 33.1 | 37.5 |
| report: rh note dynamics per phrase | 6.0 dB | 7.2 dB | - |
| bar loudness range / LRA | 7.1 dB / 8.4 LU | 8.6 dB / 11.1 LU | 9.9 dB / 12.1 LU |
| attack vs sustain centroid (loudest melody attacks) | 0.99 (dark attacks) | 1.03 | 1.02 |
| chroma cosine per bar | 0.80 | 0.83 | - |
| report warnings (profile `piano`) | 2 (the hands mask each other in the low mids and mids) | **0** | 0 |
| tempo: bar lengths CV / correlation with the recording | 0.075 / 0.59 | 0.075 / 0.59 | 0.13 |

The whole song vs the recording (`compare`, loudness-matched): -22.8 vs -22.8 LUFS, LRA 11.1 vs 12.1 LU, PLR 20.7
vs 21.6 dB, crest 23.6 vs 23.8 dB, width above 150 Hz 16 vs 19 %, correlation 0.74 vs 0.68, tilt -8.2 vs -7.4 dB/oct;
bass +13.6 dB (22-180 Hz) and air -5.1 dB, T60 2.5 vs 1.6 s (see open gaps). 0 clicks, true peak -2.1 dBTP (the
limiter never works).

## Weaknesses found (numbers) and what was fixed

Fixed in the library (`agentsound/romantic.py`, tests in `tests/python/test_romantic.py`; `tempo.py`; the `piano`
analysis profile):

1. **No fioritura.** The pianist's runs are scales / arpeggios / glisses; a written free figure (chromatic
   descent, broken diminished chord, the cadenza cycle) could only be put on an even grid: CV 0.00-0.04, every note
   equal. -> `fioritura()`: the written notes as one gesture (arch / accel / rit / wave), ends ~1.4-1.8x slower than
   the middle, lighter in the middle, finger legato, timed in real time, never thinned (bar 16 CV 0.04 -> 0.22, the
   cadenza 0.00 -> 0.23).
2. **Trills without a classical start and ending.** `pianist.trill` (jazz) runs 12.7 notes/s and turns back to a
   held main note. -> `trill()`: main / upper / lower start, a slow start (0.55x), `rate` in the middle, settling
   (0.7x) into the Nachschlag (diatonic or `lower=-1` chromatic) that lands on the next note: 9.9 notes/s (the
   recording ~10.6), ornament notes never louder than the principal.
3. **The melody locked to the bass.** Only the global tempo map could move: melody vs bass +-2 ms. -> `melody_rubato()`
   moves the right hand only: leaning inside half-bar spans, downbeats spread around the bass (+10 +- 37 ms exact;
   detected std 9 -> 33 ms, the recording 47), agogic delays after leaps and on local summits; order and legato kept.
4. **No nocturne left hand.** Bass + chord + chord in 12/8 had to be written by hand, every strike at one level: the
   accompaniment as loud as the tune (voicing share 0.51). -> `accompany()`: patterns (`bcc`, `bc`, `B..` held
   chords), the bass carrying, the chords soft, the second strike lighter, slightly rolled, breathing per phrase:
   voicing 0.51 -> 0.64 (recording 0.67).
5. **Long singing notes.** `touch()` shapes by pitch and position only: the opening G5 (3 s) got less than the short
   notes after it, and the note after a long note banged out of its decay. -> `lean_on_long()` (long notes gain up to
   10 velocity) + `cantabile()` (the next note plays into the decayed level, `decay_db()` model; ornaments keep their
   level under their principal): phrase note dynamics 6.0 -> 7.2 dB, detected spread 27.8 -> 33.1 dB (rec. 37.5).
6. **Hairpins.** Only `humanize.crescendo` spans. -> `dynamics()` with marks (pp .. ff, subito steps) and smooth
   hairpins (the same map in both runs; the arc correlates 0.85 with the recording's bar loudness).
7. **`s.tempo_at()` while a song is being written ignored every a-tempo return** (no notes placed yet -> each
   ritardando kept its slowed tempo for good): real-time figures got denser bar after bar - the same trill had 17
   notes in bar 7, ~35 in bar 15 and ~55 in bar 23. Fixed in `tempo.py` (no onsets = the music goes on); every other
   song compiles bit-identical.
8. **The classical profile misjudges solo piano.** The concert recording itself reads lowmid +12.8 / mid +11.2 dB
   (limits +5) under `classical` (an orchestral balance). Found here and, in parallel, by the Gymnopedie etude,
   whose analysis profile `piano` (already fitted to this same Chopin recording + the Satie one) is in master; the
   nocturne's own version of it was dropped in the merge. Under `piano`: the recording 0 warnings, this render 0;
   under `classical` this render gets the same two balance warnings as the recording (+13.2 / +12.7).
9. **Pedal smear.** A harmony pedal over chromatic runs piles every passing note into a cluster. -> `pedal_changes()`
   (legato pedal per harmony) with `flutter=` windows: cleared every ~300 ms in the chromatic fioriture and the
   cadenza, to a half pedal (`flutter_to=0.6`, the sampler's half pedal from master) so the bass keeps ringing
   (bar 16 detected CV 0.36 -> 0.28, the recording 0.26).

Open gaps (not fixed here):

- **Tempo breathing** is shallower than the pianist's: bar-length CV 0.075 vs 0.13 (correlation with the
  recording's bar lengths 0.59) with four-bar lean / arch rubato (depth 0.1) and cadence ritardandi; the recording
  takes 9.7 s for one bar and 5.3 s for another. The tempo map is shared by both runs (not a before / after item);
  a phrase-level "take time here" tool (bar-wise agogics beyond +-10 %) is still missing.
- **Ring / room**: the render rings longer than the recording (T60 2.5 vs 1.6 s, after-hit energy +0.6 dB): the
  pedal per harmony and the hall. Master's sympathetic string resonance makes it longer still (0.6: T60 3.0 s,
  after-hit -3.3 dB) - the recording is dry - so it stays off here; `sampled/recital_grand` (the Gymnopedie's
  Headroom C3) read T60 1.9 s but 36 % wide (the recording 19 %), brilliance +3.8 dB and 3.7 LU too quiet for this
  performance's velocities, so the warm Salamander stays (`NOCTURNE_PIANO=recital` renders the alternative).
- **Bass / air vs the recording**: +13.6 dB at 22-180 Hz and -5.1 dB of air - mostly the recording (an old,
  band-limited, bass-light YouTube transfer); not chased further than a -5 dB low shelf on the left hand.
- **Ornament detail**: the recording's trill is more uneven (detected CV 0.47, ends 1.74x) than `trill()` (0.19,
  1.28); the cadenza's shape is the pianist's free choice (accelerando / decelerando) - `fioritura(shape='arch')`
  approximates it.
- **Measurement limits**: onset / pitch detection in a pedalled polyphonic recording (the detector's +16 ms bias on
  melody vs bass, figure onsets merged under the pedal), the inner left-hand voicings, bars 30-32 of the coda.

## Performance and sound

Salamander Grand (`inst.sfz(..., hammers=0.45, width=0.4)`: warm, narrow enough to be one instrument), the right
hand panned -0.55 so the treble is not right-heavy, the Musikverein IR (`bus/ir_concert_hall` at width 1.0, sends -10
dB), a low shelf -5 dB at 180 Hz on the left hand, air +3.5 dB at 10 kHz, a safety limiter at -1 dBTP that never
works (string resonance off: the recording is dry). The left hand is placed first (the tempo map's timekeeper); the right hand: `touch` (a gentle arc) ->
ornaments (`fioritura`, `trill`, `turn`) -> `lean_on_long` -> `cantabile` -> `dynamics` (the score's hairpins, the
B section's crescendo to its forte bar, one coda climax at bars 30-31, the cadenza leggiero) -> `melody_rubato`;
pedal per harmony with flutter in the chromatic figures. Tempo 50 (quarter) with four-bar lean/arch rubato, breaths
into the cadences, bar 32 senza tempo (24, the figures in real time), the end dying away under a fermata.

Credits: Salamander Grand Piano V3 by Alexander Holm (CC-BY 3.0); Voxengo IM Reverbs (royalty-free).
