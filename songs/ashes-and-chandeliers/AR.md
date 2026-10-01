# A&R - Ashes and Chandeliers

Judged: `song/epic` @ 9af81e9 (mix + master). I re-rendered it with `--stems` (`out/ar/full/`), and the mix is
bit-identical to the delivered `out/mix.wav`. Evidence comes from `report.json`, the images, `agentsound mix --lead
gtr1` (findings only), `master --check`, and K-weighted stem levels per section measured on the stems.

```
verdict: revise
```

**Summary:** A real four-part epic with a theme you remember. The ballad, the mock-opera, the waltz, the
accelerando into the band and the tam-tam fall all land as composed. But the moments that should make it
*epic* fall short:

- The major-key return of the theme in the finale drowns in a root-heavy tutti.
- The band comes in quieter than the opera fermata before it, and Part III stays flat and narrow.

## Issues (most severe first)

1. **[blocker] The finale's payoff is buried: the theme in C major does not lead the tutti.**
   - **Stems, K-weighted, finale / summit:**
     - All melody doublings together (violins1, violins2, flutes, gtr1-3, horns, choir, choir_f) sit 1.7 / 0.7 dB under the rest.
     - The core tune (violins, flutes, gtr1-3) sits 3.8 / 3.5 dB under the rest.
   - **The loudest single stem in the finale is the cellos playing whole-bar roots.** They are level with gtr1 and 6.8 dB over violins1, the octave-up melody that should crown a film tutti.
   - **The root and bass group** (cellos, basses, bass guitar, tuba, timpani) is only 1.2 dB under *all* the melody doublings combined.
   - **`mix --lead gtr1`:**
     - bed +5.5 dB (finale) and +7.0 dB (summit) vs the lead, where the target is -7..-1
     - low +2.5 dB
     - cellos +0.8 dB over the lead
   - MIX.md's own result is "chords -0.4 dB against the melody". HUMAN_FEEDBACK asks for >= 2-3 dB ("der Lead ist jetzt zu leise").
   - `report.json` finale / summit: lowmid +2.9 / +5.3, mid +3.6 / +6.4, presence +3.8 / +4.7 dB vs the film reference. The loudest 40 s of the song is a mid-heavy wall. The spectrogram shows no melodic line standing out of it.
   - **Owner:** arranger first, then mix-engineer.
   - **Fix:**
     - Thin the accompaniment. Trumpets pads, trombones pads, violas pads, organ, the piano 8ths, choir_m roots and the power chords all spell the same chord in the same octaves. Keep two of them.
     - Take the cellos off the root pedal: onto the tune an octave down, or onto a counter-line.
     - Give the theme the film-tutti voicing: violins1 + violins2 in octaves, horns + trumpets in unison, the choir's top voice on the melody. gtr1 on top.
     - Then carve 250-800 Hz from the pads, keyed by the melody, and re-measure. Target: the bed >= 3 dB under the tune and the lows >= 3 dB under it, in finale and summit.

2. **[major] The band's entry is an anticlimax, and Part III never climbs.**
   - **Timeline:**
     - Bar 74 (E major fermata): -10.1 LUFS.
     - Bar 75 (the riff, "the band kicks in"): -13.7.
     - The first anthem bars: -15.6 / -15.0.
   - **Short-term max:** ascent -10.0 vs riff -13.9.
   - **Width collapses** from 62-97 % (bars 67-74) to 14-25 % at the downbeat. After the fermata the listener hears the room get smaller and quieter, not the band arriving.
   - **Part III is one flat plateau for 62 s:** riff -14.1, anthem -14.7, anthem2 -13.1, solo -13.6, riff2 -13.3.
     - The brief promised 4 -> 4.5 -> 5 (solo).
     - The solo, the brief's energy 5, is quieter than anthem2.
     - The whole rock part sits below the opera climax.
   - **The climax order is flat too:** the summit's short-term max (-9.7) only just tops the ascent (-10.0).
   - **Owner:** arranger (entry and build), mix-engineer (rides).
   - **Fix:**
     - Let the fermata chord diminuendo into the drummer's pickup, so the riff has headroom to hit.
     - Make the first riff an arrival: low brass, timpani and low strings on the riff accents (as in riff2), a crash + taiko downbeat.
     - Build Part III by adding layers:
       - anthem2: strings pad / choir "ah"
       - solo: the orchestra's sustained bed + a ride of the band +1 dB
     - Ride Part III ~1.5-2 dB up against the opera. The riff's short-term level must reach the fermata's (>= -11).

3. **[major] No wall of guitars: the rock sections are narrow and bass-and-kit heavy.**
   - Both rhythm guitars summed sit 4.0 dB (anthem2) and 2.3 dB (solo) under the kit, and under the bass guitar in anthem, anthem2 and solo. The rock recipe says the guitar pair should sit level with the drums.
   - The bass guitar is the second-loudest stem in anthem, solo and finale, even K-weighted.
   - **Width above 150 Hz:** anthem 23 %, anthem2 28 % (stereo.png), against the rock recipe's 30-60 % (25 is the floor). Full-band width is 14-18 % in all of Part III, the narrowest stretch of the song.
   - Also reported as info: `node_hot` kit +2.7 dBFS, drum_bus +1.4, bass +0.4 before the master.
   - HUMAN_FEEDBACK "Produced, not Gameboy: width" is not met for the most energetic part.
   - **Owner:** mix-engineer (levels), sound-designer (pans / doubles).
   - **Fix:**
     - gtr_l / gtr_r +2.5-3 dB in anthem, anthem2 and solo.
     - Bass guitar -2 dB (duck it under the kick).
     - gtr2 / gtr3 from ±0.38 to about ±0.65.
     - Kit and bass trimmed for headroom.
     - Re-check width >150 Hz >= 30 % in anthem and anthem2.

4. **[major] The choir lines in Part II sound like pads, not singers.**
   - The calls and answers are melodic lines on slow-onset "aah" sustain samples.
   - **choir_m stem at 2:07:** 250-300 ms from onset to within 3 dB of the note level. The 8th-note pickup of the call lasts 268 ms at 112 BPM, so it is swallowed.
   - Inside the phrase the level stays within ~4 dB with no articulation between the pitches.
   - **choir_f answers:** ~350 ms to speak, and so does the waltz's staccato "ah" (2:41). The producer flagged the "ah" as soft.
   - The curtain motif's defining upbeat is lost exactly where the choir is meant to declaim it (ff/pp drama).
   - HUMAN_FEEDBACK: "möglichst realistische, nicht keyboard-artige Instrumente".
   - **Owner:** sound-designer (articulation), arranger (writing).
   - **Fix:**
     - Use a faster-speaking choir layer for the calls: a staccato / marcato articulation, a short consonant or attack layer, or start the notes earlier than the 70 ms now.
     - Double the pickups and call onsets with brass or timpani so the rhythm reads.
     - Write the choir calls in longer values (pickup as a quarter).
     - Replace the staccato-"ah" waltz off-beats with pizzicato + a light choir "ah" pad, or with a real short-articulation choir.

5. **[minor] The pp extremes read as dropouts.**
   - The calls' female answers dip to about -36 / -38 LUFS short-term / momentary at ~2:12 and ~2:20, about 20 LU under the section.
   - The fall (bar 126, ~5:07) sits at -34.2 LUFS for ~4 s.
   - With the volume set for the finale (-10), these are near-silence on a phone.
   - **Owner:** mix-engineer.
   - **Fix:** the pp answers +4-6 dB (still pp in character), the fall's strings / "oh" choir +3 dB under the tam-tam ring.

6. **[minor] The ballad piano is veiled.**
   - For two minutes the piano opens the piece alone. Its loud frames sit at a centroid of 309 Hz (intro) / 547 Hz (theme) / 684 Hz (middle), with a 2-5 kHz share of 0.3-1.8 %.
   - Against the film reference, the intro / theme are brilliance -19.6 / -12.1 and air -25.8 / -19.7 dB.
   - In the intro the piano's energy below 350 Hz equals the energy above it: the left hand is as loud as the melody.
   - Warm is right (HUMAN_FEEDBACK "es klingt hart"; no presence push), but "smooth is not flat and not dull".
   - **Owner:** sound-designer.
   - **Fix:** a little air (a shelf above 8-10 kHz, not 2-5 kHz), the broken-chord left hand 2-3 dB softer under the melody (arranger: lh_vel), and a check that the melody's top notes speak over it.

7. **[minor] Leftovers.**
   - 5 masked clicks in `basses` (1:38.4, 4:29.1, 4:41.7, 4:51.3, 4:54.3). Owner: sound-designer.
   - Info-level flat phrases on violins2 (theme2, middle) and horns (middle). Owner: arranger.
   - The pre-master headroom above (item 3). Owner: mix-engineer.

## Originality (not a Queen copy?)

The material is original: the curtain motif (G4 - Eb5 - D5 - C5), the C minor / Eb ballad harmony, the E minor
calls, the waltz, the A minor riff and the C major finale are not taken from Queen's records.

The *macro-form*, though, follows "Bohemian Rhapsody" section by section:

- a piano ballad
- a sudden mock-opera with male / female call and response
- hard rock with a harmonized guitar orchestra
- a slowing break
- a gong
- a soft piano ending

The brief allowed this as "the spirit". The orchestral Part IV and the 3/4 masque are what make it its own. No action
is required. Just know that a listener may say "Rhapsody homage" rather than "original epic". Making the finale the
unmistakable summit (issue 1) is also what tips the balance towards its own identity.

## Checklist (HUMAN_FEEDBACK)

- [x] A song, not a loop: 19 sections, 4 parts with their own keys, tempi and meters. The theme returns 9 times,
      transformed. Transitions are composed: fermatas, accelerando, drum pickup, break, tam-tam.
- [x] No beepy lead: hero piano, choirs, flutes, hero guitars, violins. No synth lead.
- [ ] Lead in front: fails in finale / summit (issue 1). The choir calls sit only 1.2 dB under the rest (issue 4). OK in the
      ballad (the piano is 14.2 -> 2.8 dB over the rest), the masque (flutes +4.2) and anthem / anthem2 / solo (gtr1 is 2.9 / 1.1 / 2.0 dB over the kit; the bed sits 8-11 dB under it).
- [x] Real dynamics: `flat_dynamics` 0 warnings, info-level only (violins2, horns pads). Piano envelope movement is
      8.8-15.1 dB per section. The choirs' dynamics lanes sweep 11-19 dB.
- [ ] Played, not keyboard-like: piano, drums, bass, rhythm and lead guitars and the orchestra are performed by the players.
      The choir lines are not (issue 4).
- [x] Piano: `pianist.arrange` ballad on every melody, one Memory with the big figure saved for the coda, rolled chords
      and pedal steps. Warm, not hard (no presence push), but veiled (issue 6).
- [n/a] Jazz rules.
- [x] Hero sounds on the hooks and the solo: hero_piano, hero_guitar_heavy + 2 x hero_guitar. The solo is in front (+2.0 dB over
      the kit) with its dotted-8th echo.
- [ ] Produced, not "Gameboy": halls, plate and echo are right. Part III width and the missing guitar wall are not
      (issue 3).
- [x] `clicks` 0 in the mix (5 masked), TP -1.19 dBTP, 0 clipped samples.
- [ ] The brief's own targets:
  - Met: length 5:52, film loudness -15.6 LUFS-I, LRA 14.8, PLR 14.4, ballad / coda levels, the finale the loudest.
  - Not met: the Part III arc 4 -> 4.5 -> 5 and "the band kicking in" (issue 2).

## Keep (must survive the revision)

- The form and the tempo map: rubato ballad, 56 BPM ritardando into the Ab fermata, the E minor subito stab, the 3/4
  masque, the accelerando 112 -> 138, the E major fermata, the break's ritardando, the tam-tam fall, the coda's
  fermata on the rolled C major add9.
- The curtain motif and its 9 transformations. It is memorable. Keep its upbeat audible everywhere.
- The ballad: pianist-performed, warm, cellos / basses / strings entering by degrees, the Ab swell.
- The masque's flute tune in front (+4.2 dB), and the pizzicato oom-pah-pah.
- The hero guitar orchestra in thirds and the guitarist's solo (bends, slides, echo). The mix engineer's riff-guitar
  lift (+2.5 dB).
- The big arc: -25 LUFS intro -> -10 summit -> -27 coda. LRA 14.8, TP -1.19, 0 clicks, the master chain (no louder).
- The metadata, the classical / noir cover, the credits.

## Revision

Revised on `song/epic` by the owning roles in order (arranger -> sound designer -> mix engineer; the master chain is
unchanged), 7 full renders. The numbers come from the final build's `report.json` (K-weighted bar levels per part,
the maths of `agentsound.mixer`), `mix --lead gtr1`, `master --check`, and a `--section calls --stems` render for the
choirs. "Before" is the judged build (bca8f26), measured the same way.

1. **[blocker] Finale buries its theme -> fixed.** Owners: arranger, mix engineer.
   - Finale / summit re-voiced as a film tutti. The theme runs in three octaves: violins1 + flutes 8va; violins2 +
     trumpets + gtr1 + the women's choir at pitch; cellos + horns + the men's choir 8vb. The large chorus' top voice
     sings it too.
   - The harmony is left to violas + the rhythm guitars (+ trombones in the summit) and the harmony guitars. Removed:
     tuba (except the last chord), organ, piano 8ths, trumpet / horn pads, the men's root fifths. The cellos are off
     the root pedal.
   - The old finale "weight" rides are gone (bass / basses / tuba up, gtr1 / choir / violins1 down). Violas +
     trombones are carved at 450 Hz keyed by gtr1 (3 dB). The tune carriers are ridden +1..+1.5 dB in the finale; the
     bass guitar and basses come back up, still 3 dB+ under the tune.
   - All doublings vs the rest: -1.7 / -0.7 -> **+5.6 / +4.4 dB** (finale / summit). The non-tune lows sit **7.9 / 8.5
     dB under** the tune.
   - The loudest single part was the cellos' roots (+0.8 over gtr1); now it is **gtr1**. The cellos, now on the tune,
     sit 1.3 / 1.0 dB under it.
   - `mix --lead gtr1`: bed +5.5 / +7.0 -> +3.8 / +4.0 dB (that "bed" is now the tune's own doublings), low +2.5 ->
     **-0.7 / -1.2 dB**.
2. **[major] Band entry and Part III build -> fixed.** Owners: arranger, mix engineer.
   - The E major fermata now dies away into the drum pickup: 'dim' shapes on the chord, choir lanes 1.0 -> 0.3, the
     struck chord / stab / crash 8-12 velocity lower, piano / choirs / horns ridden back in the ascent.
   - The riff is an arrival: brass marcato + cellos / basses + timpani on the riff accents, crash + concert bass drum
     on the downbeat, kit +1.5, riff guitars +3.5.
   - Part III adds layers: organ + violas / cellos pad under anthem; chorus 'ah' + horns under anthem2; the orchestra's
     sustained bed, the chorus and a timpani roll + crash into the solo's peak; tremolo violins over riff2.
   - Bar 74 (fermata) -10.1 -> **-12.7**, bar 75 (riff) -13.7 -> **-12.6** LUFS. Short-term max ascent / riff:
     -10.0 / -13.9 -> -11.7 / -12.3.
   - Part III riff / anthem / anthem2 / solo / riff2: -14.1 / -14.7 / -13.1 / -13.6 / -13.3 -> **-12.6 / -14.2 / -12.9
     / -12.7 / -12.3**, all above the opera (calls -15.4, ascent -14.8). Finale / summit -11.8 / -10.9 stay the peak.
3. **[major] Wall of guitars -> fixed.** Owners: mix engineer, sound designer.
   - Rhythm pair ridden +2.5 (anthem) / +3 (anthem2) / +3.5 (solo, riff) dB; bass guitar -2 (-1.5 in the solo) in
     Part III; kit trim -1.5; gtr2 / gtr3 panned +-0.38 -> **+-0.65**. The wall's fizz is dipped (3.3 kHz on the pair,
     3.8 kHz on gtr2 / 3, 3.5 kHz on the drum bus).
   - Width > 150 Hz anthem / anthem2: 23 / 28 % -> **31.7 / 40.3 %** (riff 37.8, solo 50.8).
   - Rhythm pair vs kit in anthem / anthem2 / solo: +1.8 / -1.0 / +0.1 -> **+5.4 / +2.8 / +3.4 dB**, and 5-7 dB over the
     bass guitar. Kit pre-master peak +2.7 -> +1.2 dBFS (info).
4. **[major] Choir lines speak like pads -> fixed for the calls.** Owners: sound designer, arranger.
   - The cause: the VPO choir SFZ's attack is 0.625 s x (1 - vel/127), so a p answer at velocity 40 took ~0.4 s.
   - The lines now sing at a speaking velocity (120, ~40 ms attack). The written dynamics move to an
     `instrument.expression` lane per onset, so every note keeps its written level and arc. The samples start 100 ms
     in, and long notes lead by 35 ms (was 70). The waltz 'ah' is treated the same.
   - Horns marcato double the men's upbeat + target note, pizzicato violins the women's.
   - Level 40 ms after the upbeat onset, vs full level: calls -26..-31 -> **-7..-9 dB**; answers -39 / -40 -> **-14 /
     -9 dB**. Onset to -3 dB of the phrase top: answers 725 / 595 -> **300 / 230 ms**.
5. **[minor] pp dropouts -> fixed.** Owners: mix engineer, arranger.
   - pp answers written +10-12 velocity, their dynamics lane 0.3 / 0.22 -> 0.4 / 0.32. The fall's strings and 'oh'
     choir are louder (a swell instead of a dim; choir 0.45 -> 0.3).
   - Answer bars 41 / 45: -31.4 / -33.5 -> **-26.7 / -27.2** LUFS. Fall bar 126: -34.2 -> **-30.5**.
6. **[minor] Veiled ballad piano -> partly fixed.** Owners: sound designer, arranger.
   - The left hand is 8 velocity softer (the intro's rolled chords 52 -> 46). An air shelf of +5 dB above 7.5 kHz sits
     on the piano (no 2-5 kHz push).
   - Theme bass vs film +8.9 -> +7.0 dB. Intro air / brilliance -36.1 / -28.6 -> -31.2 / -26.6 dB (theme -25.8 / -19.6
     -> -25.5 / -18.8). The softened-hammer grand has almost nothing above 7 kHz; warm stays warm.
7. **[minor] Leftovers -> unchanged.** 0 clicks in the mix. Masked clicks 5 -> 7: the 5 in basses, plus 2 in choir_f
   (loop seams of the finale's held notes, -41 dBFS). The info-level flat phrases on violins2 (theme2, middle) remain.

**Whole song:** -15.4 LUFS-I (was -15.6), TP -1.18 dBTP, LRA 15.3 LU, PLR 14.2, width > 150 Hz 41 %. Balance vs film:
mid +3.5, presence +2.6, lowmid +3.1. **0 warnings**, 7 info. `master --check`: true peak, loudness, LRA and mono all
ok. Its info suggests an optional +1.2 dB low shelf / -1.0 dB bell; not taken, the master stays as it was.

**Kept:** the form and tempo map, the theme and its 9 returns, the ballad, the waltz, the guitar orchestra and solo,
the -26.6 -> -10.9 -> -27.5 LUFS arc, the master, metadata and cover.

**Brief re-judgement** (by the revising agent, not a fresh A&R; a fresh pass should confirm):
- Issues 1, 2, 3 and 5 are fixed by the numbers. Issue 4 is fixed for the calls: the answers' first 80 ms still sit
  ~10 dB under full level, because this is a sustain-sample choir with no real consonant. Issue 6 is partial,
  issue 7 unchanged and masked.
- Still open: the finale / summit tone stays mid-forward (mid +4.2 / +7.6, presence +4.3 / +4.9 vs film), because the
  tune itself lives there; the song-wide balance is inside the limits. Anthem stays Part III's valley (-14.2, the
  "verse"), and the solo is only 0.2 LU over anthem2, because the limiter holds the rock sections at a similar
  density.
- Verdict proposal: **ship candidate**. The A&R makes the final call.
