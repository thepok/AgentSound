# Nowhere to Be - A&R (roles/a-and-r.md)

# Round 2

Judged on build10 (scratch/build10.log, the new out/ report + images, re-measured scratch/measure_wet.json), `mix`
(findings: 1 info, "moves: none") and `master --check --platform dynamic` (all ok: -15.1 LUFS-I, TP -1.20 dBTP,
LRA 5.0, corr 0.71). 0 clicks, 0 clipped samples, 0 silent notes.

```
verdict: ship
summary: The same hushed, laid-back late-night ballad, now with a little more shape - verse 2 climbs where verse 1
fell, the last chorus stays open on "you", and the tenor opens the song at her pitch instead of mumbling under the
Rhodes. Still calm, unhurried and dry; the solo is gentler and the last chorus is (nearly) the warmest moment.
```

## Issue status (round 1 numbering)

1. Solo louder than the last chorus - **improved, still minor**. Solo short-term max -11.6 -> -12.1 LUFS (integrated
   -14.5 -> -15.0), chorus3 -12.4: the solo's climax still tops it by 0.3 LU (was 0.7) - below what the user notices.
   With the tenor 1 dB quieter the solo's band reads hotter around it (`mix`: rhythm -13.4 [-16..-13], low -2.9
   [-6.5..-3], both at the window's edge). Owner: mix-engineer. Optional: ride drums / Rhodes -0.5 dB in the solo.
2. Low mids / Rhodes-upright overlap - **open, minor** (not changed). Masking warn now lists the intro too (the Rhodes
   alone in bars 1-2: 65 % of 60-250 Hz). Mix lowmid +2.7 (was +2.9). The intro's tenor-vs-Rhodes masking is **fixed**:
   the hook at G4-C5 (spectrogram_01_intro.png: the sax clearly above the comping), `mix` intro low -2.3 -> -4.5 dB
   (inside the window), intro space ok (was lush).
3. Sung sections narrow - **open, minor** (not changed): verse1 / chorus1 / verse2 / chorus2 still `narrow*`.
4. Verse 2 repeats verse 1 - **fixed**: line 3 now Ab4 Bb4 C5 Bb4 ("sun-rise can wait" climbs); chorus3's last line
   lifts to G4 over the deceptive Cm9. Still 0 leaps of a 4th+, so the new contour costs no calm.
5. "clock" /k/, "let" /t/ legato codas -30 / -29 / -32 dB - **unchanged, watch only**; build10 `vocals` lines: no
   `coda_short` / `coda_buried` (shortest 'for' /r/ 35 ms). Diction passes.
6. Pad 'hall' send dropped, band plate inaudible (36.8 LU) - **open, minor housekeeping**.
7. NEW [minor] The intro tenor phrase is the one flat phrase: `flat_dynamics` info "1 of its 4 phrases stay under
   4.0 dB (in 'intro')" (sax note dynamics 5.4 -> 4.7 dB overall, from velocity 2.2 dB) despite the wider vel=(50, 90).
   Info level, not the warn that the checklist forbids; the opening statement may sound a little even. Owner:
   arranger. Fix: a clearer arc in SAX_INTRO (soft pickup, the C5 the peak, the F4 tail tapering), or `peaks=` on it.

No blocker, no major: ship stands.

## Calm / laid back / dry - round 2 numbers

| question | build10 | round 1 | verdict |
|---|---|---|---|
| (1) calm vs agitated | 0.9 % at/above D5, 0 notes >= G5, 0 leaps of a 4th+ (91 intervals, mean 1.84 st); soft mode 100 %, power 0 %; scooped onsets 3 % (2 of 63); vibrato median 8.0 ct at 5.2 Hz; 0 falls / doits; note levels p10-p90 3.5 dB | 0.9 %, 0 leaps, mean 1.88 st, 3 %, 8.6 ct | **calm** |
| (2) rushed vs laid back | vowels +61 ms median (p10 +59, p90 +80), 0 % early; phrase starts +80 ms; P-centre +1.8 ms (on the beat; jane-street rushed: ~20 ms ahead); 0.8 syllables/s, median step 417 ms, 0 % <= 260 ms; 1.67 s rests; 72 BPM | +61 ms, P-centre +2.1 ms | **laid back** |
| (3) wet vs dry | returns 20.5 LU under the dry voice (her own plate only), no echo, no throws; 30 dB down 0.1 s after a phrase end (wet -38.3 dB at 250 ms, -54.6 at 500 ms) | 20.5 LU, 0.1 s | **dry** |

Smooth: unchanged - Rhodes velocities 26-87 (no bark), the tenor without tube / exciter, no fills, brushes
-14.1..-16.6 dB under the lead (rhythm per section in `mix`), presence 0.0 / brilliance -2.6 / air -2.5 vs the profile.

---

# Round 1

Judged on the final build (scratch/build7.log, out/report.json, the images, scratch/measure_wet.json), plus
`python -m agentsound mix` (findings: 0, "moves: none") and `master --check --platform dynamic` (all ok). No reference
for smooth jazz exists: `compare` skipped.

```
verdict: ship
summary: A slow, hushed late-night ballad - she sings low and unhurried right in front of a warm Rhodes, a soft
upright and brushes, and the tenor answers her and takes a gentle solo. Nothing pushes, nothing is bright or wet;
if anything it is a little thick in the low mids and very even from start to finish.
```

## Issues (most severe first)

No blocker, no major.

1. [minor] The tenor solo is the loudest moment of the song, not the last chorus: short-term max -11.6 LUFS in the solo
   (~2:57, the `long_tone` climax) vs -12.3 in chorus3 (loudness.png, the "max" marker). A smooth ballad should peak
   on the voice's last chorus.
   owner: mix-engineer   fix: `sax.feature(solo, db=1.0)` instead of 2.0, or ride the sax -1 dB over solo bars 51-54;
   re-check that chorus3 holds the ST max.
2. [minor] Low mids are thick and the Rhodes and the upright share the bass band: report `masking` warn (piano/bass
   both >25 % of 60-250 Hz in verse1, inter, verse2, tag), Rhodes 59 % bass / 41 % lowmid share, centroid 243 Hz;
   bands.png lowmid +2.9 dB overall (+7.8 intro, +5.3 tag), brilliance -2.6, air -2.5. Smooth, but on the dark,
   slightly woolly side. In the intro the tenor's low hook (G3-C4) sits inside the Rhodes' comping register (D3-G4):
   `mix` reads the low group only -2.3 dB under the tenor there (window -6.5..-3).
   owner: arranger (register) / mix-engineer   fix: comp the Rhodes from F3 up in the sparse sections (or HP it at
   ~110 Hz), and keep the intro Rhodes above the low tenor (or play the intro hook at pitch, as in the inter);
   optionally a +0.5 dB 10 kHz shelf on the master as the tone_profile info suggests.
3. [minor] The sung sections read `narrow` (space verdict, stereo.png: width >150 Hz 11 / 13 / 15 / 14 % in
   verse1 / chorus1 / verse2 / chorus2, target 15..80; correlation 0.80-0.84). The dry centred voice is right; the band
   around her is what is narrow.
   owner: mix-engineer   fix: widen the bed, not the voice - the pad's spread wider, the Rhodes' stereo vibrato a
   little wider, the room return wider; the voice stays dry and centred.
4. [minor] The tune is built from two rhythm cells for every line, and verse2 sings exactly verse1's notes (song.py:
   `VOX('verse')` twice, chorus x3 identical until chorus3's harmony and last line). Over 4:30 at 72 BPM it is calm but
   very even - LRA 5.1, sections -16.7..-13.2 LUFS.
   owner: arranger   fix (next song, or a light touch here): vary one verse2 line (a different contour on the
   3rd line, a held note displaced by a beat) and let chorus3's hook rise one step on its last line.
5. [minor] Two legato word-final stops are nearly silent in the 2-8 kHz band: "clock" /k/ -30.4 dB, "let" /t/ -29.2
   and -32.5 dB vs their vowels (measure_wet.json codas). Both run legato into the next consonant ("clock to", "let
   the"), which is natural English elision, and the engine's diction check passes (no `coda_short` / `coda_buried` in
   build7.log; the codas before rests - "cold", "wait", "stayed", "but" - are clearly there). Watch item only.
   owner: producer   fix: none required; if the user hears "clo' to the wall", give "clock" a 40 ms gap.
6. [minor] Housekeeping: the pad patch's send to 'hall' is dropped (build warning: no such bus) and the band 'plate'
   return is 36.9 LU under the mix (report info: inaudible).
   owner: sound-designer   fix: drop the pad's hall send explicitly; remove the keys' plate send or leave it.

## Calm / laid back / dry - judged from the numbers

| question | this build | jane-street rushed | jane-street calm (the user's pick) | verdict |
|---|---|---|---|---|
| (1) calm vs agitated | 0.9 % of sung time at/above D5, 0 notes >= G5, 0 leaps of a 4th+ (91 intervals, mean 1.88 st); soft mode 100 % / power 0 %; scooped onsets 3 % (2 of 65), 6 planned scoops of ~26 ct; vibrato median 8.6 ct at 5.4 Hz (p90 21 ct), only on held notes; 0 falls, 0 doits; gain lane -1.6..+0.7 dB, note levels p10-p90 3.4 dB | 1/3 at/above D5, 11 leaps per chorus | 4 % at/above D5 | **calm** |
| (2) rushed vs laid back | vowels median +61 ms behind the beat (p10 +59, p90 +80), 0 % early; phrase starts +80 ms; P-centre +2 ms (the syllable lands on the beat, not ahead); 72 BPM; 0.8 syllables/s, median syllable step 417 ms (0 % of steps <= 260 ms), 1.67 s of rest between phrases | syllables ~20 ms AHEAD, 62 % 8th-note steps at 126 BPM (238 ms) | 100 BPM, vowels ~35 ms behind | **laid back** |
| (3) wet vs dry | returns 20.5 LU under the dry voice (one bus: her own short plate), no echo, no throws, not in the band room; 30 dB down 0.1 s after a phrase end (wet -39 dB at 250 ms, -55 dB at 500 ms) | plate -12 + constant echo -20 + throws | ~20 LU under | **dry** |

Notes: the P-centre of +2 ms is "on the beat" rather than behind it - correct, because at 72 BPM the consonants run
~119 ms ahead of each vowel and the 60 ms lay-back was set to land the syllable, not the vowel, on the beat; the
phrase-start vowels at +80 ms are the most laid back of the set and still well inside "relaxed". Syllable steps of
417 ms are 8ths musically at 72 BPM, but in time they are 1.75x slower than jane-street's rushed 8ths and 1.4x slower
than its calm version.

### Smooth - is anything bright, edgy, busy or hard?

- Rhodes bark: no. Velocities 26-87 (the bell layers, under the ~95 bark threshold), centroid 243 Hz, 0 % presence /
  brilliance share; rolled 14-30 ms, pedal with the harmony. If anything it is too dark (issue 2), never hard.
- Sax grit: no. Soft hero without tube and exciter, 0 dB at 3 kHz, gentle 2:1; tenor centroid 479 Hz, 80 % lowmid,
  1 % presence; no shakes / growls (weights 0), the budget kept one `scoop_call` and no fast figure in the solo.
  The tenor's plate is wetter than the voice (~9-11 LU under it in inter / solo, wetness strip -9.4 / -10.7) - fine for
  a ballad horn.
- Busy fills: no. `fills=False` on every brush part, comping density 0.3-0.55, a two-feel bass ('push' only under
  the solo), brush stirs one per beat, ghosts <= 0.15.
- Drum level: brushes 15.3-16.6 dB (RMS) under the lead per section (`mix`: rhythm -15.3 / -15.1 / -14.9 / -14.3 /
  -13.9 / -14.4 vs the voice, -14.2 vs the tenor in the solo; tracks.png drums -34..-37 vs vocal -19..-21); the
  cross-stick a click at RMS -49..-55 (30 dB under her). The kit's sample peak (-9.2 dBFS) is the feathered kick
  (57 % bass-band energy) - a low thump, not a crack in her range.
- Hard / harsh: no. Mix presence 0.0 dB vs the jazz profile, brilliance -2.6, air -2.5; vocal: "intelligible
  (presence band owned), not buried, no harshness"; sibilance median -14.9 dB.

## HUMAN_FEEDBACK checklist

- [x] CALM, not "aufgeregt": soft mode 100 %, Eb4-C5 + one D5 (0.9 %), stepwise (0 leaps of a 4th+), 3 % scooped
      onsets, no falls.
- [x] LAID BACK, not "gerusht": vowels +61 ms, P-centre +2 ms (0 % early), 0.8 syllables/s, 1.67 s rests, 72 BPM.
- [x] DRY and close: returns 20.5 LU under the voice, no echo, no throws, tails gone in 0.1 s.
- [x] Straight 8ths, no swing ratio anywhere (bossa preset Feel 0.5, `straight=True` on bass and brushes).
- [x] A song, not a loop: 11 sections, the hook in the intro (tenor low), chorus x3, inter (tenor at pitch), the solo's
      motif and the tag; a turn to bVI in the bridge, a deceptive Cm9 into the tag, chorus3's harmony and turned last
      line; tenor answers in her gaps. (Repetition of the verse melody: issue 4, minor.)
- [x] Lead in front: rhythm -13.9..-16.6 dB, low group -4.4..-7.5 dB, pad ~12 dB under her in the sung sections;
      `mix` findings 0.
- [x] Real dynamics: `flat_dynamics` 0; voice 19.2 dB (onsets) / vowel levels 7.3 dB p10-p90, bass 8.7, tenor 5.4,
      Rhodes 4.5 (3/11 phrases under 4 dB), pad 4.1.
- [x] Played, not keyboard-like: `singer.sing` (takes 0-3, breaths, releases, tapers), `hornist.arrange` +
      `soloist.solo`, `jazz.comp` rolled with pedal, `jazz.walking_bass` with touch, `jazzband.brushes` + hand-placed
      cross-stick with velocity jitter, `s.ending` with rit, rolled final chord and `last_stir`.
- [x] Warm, not hard: Rhodes velocities <= 87, no presence boost on keys or sax.
- [x] Jazz drums soft: 13-16 dB under the lead in every section (above).
- [x] Hero sax present in the solo but smooth (no tube, no exciter, no fast figure). (Slightly too present at its
      climax: issue 1, minor.)
- [x] No busy fills; ornaments budgeted (one kept spice in the solo, none dropped).
- [x] Diction passes: no `coda_short` / `coda_buried` in build7.log (shortest coda 'for' /r/ 35 ms, within its class);
      lyrics.txt in out/ to send along.
- [x] 0 clicks, 0 clipped samples, true peak -1.20 dBTP, 0 silent notes (every node `silent: 0`).
- [x] Brief targets: 72 BPM Eb, 78 bars + fermata = 4:30; -15.0 LUFS-I (jazz -16..-13), LRA 5.1 (>= 5), PLR 13.8,
      correlation 0.71, low end mono (0.99).
- [x] No beepy lead: the lead is a sung voice, the instrumental hook on the tenor.

## Keep

- The voice exactly as it is: Hanami `jazz`, soft mode only, `late_ms=60` / `late_first_ms=20` (the P-centre lands on
  the beat at 72 BPM), Eb4-C5, few syllables on long notes, a breath after every line, the dry hero with its own plate
  ~20 LU under her. This is the delivery the user asked for after jane-street - do not touch it while fixing the minors.
- The tenor as a soft hero (no tube / exciter, 2:1) answering only in her gaps (chorus2 / chorus3 beats 6 and 14).
- The form and the hook's journey (tenor low -> voice -> tenor at pitch -> solo motif -> harmony -> "nowhere but you"
  -> deceptive Cm9 -> tag -> the last "be" on Eb4 over the rolled Ebmaj9 with the fermata).
- The drum balance (15-16 dB under) and `fills=False`; the Rhodes' warm velocity range.
- The cover (jazz style, record + "nowhere to be") and the credits: Hanami (Lotte V; AI-dolGAN vocoder CC BY-NC-SA)
  and jRhodes3d (CC-BY-NC) are non-commercial, the SampleRadar pad no-redistribution, the 224XL plate unclear - fine
  for private listening, check before publishing.
