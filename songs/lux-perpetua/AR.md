# A&R - Lux Perpetua (Requiem in D minor)

Judged build: `ee83ed5` (song/requiem), rebuilt independently with `--stems`. The numbers are identical to the
mix / master hand-over: -19.6 LUFS-I, TP -2.47 dBTP, LRA 16.0, PLR 17.1, 0 warnings, 3 info, 0 clicks in the mix.

Evidence:
- the report and the images (`overview`, `loudness`, `tracks`, `bands`, `stereo`, the section spectrograms);
- zooms (`zoom_2m13.9s_choir_s.png`, `zoom_2m13.9s_mix.png`);
- `mix` findings and `master --check --platform dynamic`;
- my own measurements on the dry stems, with scratch scripts that are not committed: per-section RMS, band-limited
  level of one part against all the others (FFT, 250 Hz-4 kHz), level at each fugue entry, the re-attack depth of
  each written note, parallels and clashes in the sung parts (read from `song.DEBUG`).

Nobody has listened. There is no K. 626 recording in `assets/refrences/`, so there is no `compare`.

```
verdict: revise
summary: A Requiem in miniature with the right Mozart vocabulary and real drama (a 16 LU range, a subito-pp Quantus
  tremor, a Kyrie that grows entry by entry to a bare fifth, a Picardy Amen) - but it sounds like choir and organ pads
  over low strings: the violins' Introitus pulse, the Lacrimosa sighs, the storm's 16ths and the natural trumpets are
  written and not heard, and the choir sings legato vowels where Mozart hammers syllables.
```

## Issues (most severe first)

1. **[blocker] Mozart's orchestral signatures are in the score but not in the sound (a failed brief).**
   The brief's idiom list is "the syncopated string pulse of an Introitus", "a Dies irae storm (tremolo, running
   16ths, dotted brass and timpani)" and "a 12/8 Lacrimosa of sighing violins". Measured on the dry stems, band-limited
   in the part's own register, against the sum of all the other parts:

   | passage | part | 500-1000 Hz | 1-2 kHz | 2-4 kHz | section RMS |
   |---|---|---|---|---|---|
   | Introitus pulse (intro, 0:00-0:26) | violins I | -15.7 dB | -7.7 | -9.3 | -47.2 dBFS vs cellos -38.1, basset horns -38.8 |
   | Introitus pulse (requiem, 0:26-1:13) | violins I | -20.9 dB | -19.2 | -12.9 | -45.8 (1 %) vs choir -34, cellos -35.1 |
   | Lacrimosa bars 1-2, orchestra alone (3:22-3:32) | violins I sighs | -8.7 dB | -7.9 | +1.4 | -49.4 vs organ -40.4, basset horns -41.0 |
   | Lacrimosa with the choir (3:32-3:47) | violins I sighs | -15.6 dB | -19.8 | -4.6 | |
   | Dies irae storm (2:13-2:26) | violins I 16ths | -13.4 dB | -10.8 | -6.7 | -31.0 vs basset horns -28.6 |
   | Dies irae storm | trumpets | -18.1 dB | -13.5 | -13.7 | -38.5 (1 %), 21 dB under the mix |

   - In `tracks.png` the violins read -47 / -50 dBFS (intro) and -46 / -48 (requiem). Violins II are missing from
     the intro's active list.
   - What is left is choir + organ + cellos / basses + basset horns: sustained chords. That is the "keyboard
     strings" impression the user has already rejected. The Mozart texture is gone.
   - Causes in the code:
     - the figures ride the chord dynamics: pulse `off=+4/0` on a map of 50-60, the sighs `off=-2/-6`, the 16ths
       `-6`, the trumpets `-10` at 55 % length;
     - the mix trimmed violins I / II / violas by -1.5 dB song-wide.

   **owner:** arranger (the parts) + mix-engineer (the balance)

   **fix:**
   - Arranger: write the figures a dynamic level above the chords they decorate (the pulse mp-mf staccato, the sighs
     mp with a small swell on the appoggiatura, the 16ths f). Give the trumpets the brief's dotted figures on D / A in
     the Dies irae and at the ira (not 55 %-length hits).
   - Mix: take the -1.5 dB off the violins where they carry a figure and ride them up per passage: intro / requiem
     violins I + II, Lacrimosa violins, Dies irae violins I, trumpets in dies / ira.
   - Target: each figure within about -6 dB of the rest in its own octave band (500-2000 Hz) during its passage.
     Re-check with a band-limited stem measure, not only the section RMS.

2. **[major] The choir is a legato vowel pad in the declaimed movements (unticked: "nicht keyboard-artig").**
   - Dies irae / Quantus tremor at q=144: 44 of the 80 Dies notes and 64 of the 92 tremor notes last 0.19-0.45 s.
     They are sung on sustained "ah" samples, joined with no silence between syllables.
     `zoom_2m13.9s_choir_s.png` shows 2.5 s (six beats, four note changes) as one continuous waveform.
   - The re-attack depth per written note is 8.0 dB (dies), 5.9 dB (tremor) and 8.0 dB (ira), against 24-28 dB for
     the timpani. Even the legato Requiem reaches 10.7 dB.
   - Mozart's Dies irae is syllabic chordal hammering with rests between the words. Here it reads as a keyboard
     "choir aahs" patch retriggered in chords.

   **owner:** arranger + sound-designer

   **fix:**
   - Arranger: declaim the chords détaché. Note lengths 55-65 % with real rests at the word ends ("Di-es i-rae |
     rest"), fewer repeated quarters (the tremolo strings carry the agitation), and a rest after each phrase, as in
     K. 626.
   - Sound designer: a short release on the SATB tracks for short notes, and a 30-60 ms dip of the dynamics lane
     before each syllable (a consonant gap). Check the packs for a choir staccato / marcato articulation.
   - TODO.md already lists the slow choir attack.
   - Target: re-attack depth of 12 dB or more on the syllables of dies and tremor.

3. **[major] The organ plays the whole choir as a pad from 0:26 to the end.**
   - `organ_notes` collects all four voices of every chorale and harmony step: song.py L304, L357-359, L420, L431,
     L505. The organ then holds them as chords.
   - It is the loudest track in the Lacrimosa (-35.5 dBFS, 14 %) and in the Lacrimosa's two orchestral bars (-40.4,
     9 dB over the violins' sighs).
   - It is louder than the soprano at her Kyrie entry: organ -33.6 against S -35.3 over the entry's first two beats.
   - At -30.6 in the Dies irae it is level with the cellos. `tracks.png` shows it continuous from the requiem to the
     end.
   - Mozart's organ is a continuo: a figured bass line with light chords, tasto solo under entries, and hardly
     noticed in forte tutti. A sustained organ doubling every voice turns the orchestra into a pad and blurs the
     counterpoint.

   **owner:** arranger (the part) + mix-engineer (the level)

   **fix:**
   - The organ plays the bass line. Add a light 2-3 voice right hand only in the soft chorale passages (Introitus
     p, Tuba, Amen). Bass only (tasto solo) under the fugue entries and in the Dies irae storm.
   - Lower it about 6 dB.
   - Check it stays at least 6 dB under the choir and under the violin figures of issue 1.

4. **[major] The first 26 seconds are quiet, near-mono and muddy.**
   - intro: -29.3 LUFS (short-term max -27.0), width 11.3 % (the classical profile accepts 15 %, targets 25-80 %),
     correlation 0.80.
   - Bands vs the reference: lowmid +10.4, bass +9.1, air -10.6 dB (`bands.png`).
   - Active tracks: cellos 29 %, basset horns 25 %, bassoons 14 %, basses 13 %, violins I 4 %.
   - In `stereo.png` the bassoons are a mono point (width 0 %).
   - This is the listener's first impression: a dark mono murmur before the choir arrives.

   **owner:** mix-engineer (+ arranger for the violins, issue 1)

   **fix:**
   - Give the winds a seat with some width (bassoons / basset horns 0.4-0.6).
   - Dip 2-3 dB at 250-400 Hz on cellos and bassoons in the intro.
   - The violins' pulse from issue 1.
   - Consider +2 dB for the whole intro. The +6.8 LU jump into the choir's entry stays dramatic.
   - Target: intro width 20 % or more, lowmid no more than +6.

5. **[major] The tone of a sample mockup: boxy mids, a dull top.**
   - Third-octave vs the classical reference: +4.4..+6.3 dB from 500 Hz to 1.25 kHz (630 Hz +6.3), +4.5 / +5.1 dB at
     2.5 / 3.15 kHz, then -3.2..-9.4 dB from 5 to 20 kHz. Spectral centroid 425 Hz.
   - Brilliance -5.7 and air -10.3 dB, even after the master's +2.7 dB high shelf.
   - `master --check` still proposes another +3 dB low shelf and +3 dB high shelf.
   - `mix` finds mud at 200-400 Hz +3.3 dB, with choir_s the biggest contributor (15 %).
   - Mids up and air down is the signature of sections and a choir that sound sampled rather than heard in a hall.

   **owner:** sound-designer, then mastering-engineer

   **fix:**
   - Cut the choir's box at the source (a further 2-3 dB at 550-650 Hz, q ~1, on choir_mixed and choir_oh) instead of
     the master's broad 800 Hz dip.
   - Let the violins' dynamics lane reach the brighter layers in the f passages.
   - Give the hall return the air: check its highcut / damping and add a +2-3 dB shelf at 8 kHz on the return.
   - Then re-plan the master.
   - Target: no third-octave above +4 dB in 500 Hz-3 kHz, air -7 dB or better.

6. **[major] The fugue reads as chords.**

   Dry-stem RMS over the first two beats of each entry:

   | entry | the entering voice | the other parts |
   |---|---|---|
   | T (answer) | -38.7 | B -37.1 (countersubject), organ -37.4 |
   | A (subject) | -36.3 | B -36.4, T -36.8, organ -35.2 |
   | S (answer) | -35.3 | B -34.1, cellos -33.8, organ -33.6 |
   | T (middle entry, F major) | -30.1 | A -29.7, cellos -29.7 |

   - The entering subject is never on top.
   - The cellos are the loudest track of the Kyrie (-30.4, 15 %), because of the mix's +1.5 / +2 dB bass trims.
   - The free voices mostly hold half notes (the producer says so).
   - The organ doubles the harmony (issue 3).
   - The answer is real (A-E-F), not the tonal answer (A-D) that a subject opening tonic-to-dominant gets in
     Classical practice.

   **owner:** arranger (+ mix-engineer for the cellos / basses)

   **fix:**
   - Give the free voices real counterpoint: the countersubject in every pair, and 8ths against the subject's
     quarters.
   - Make the answer tonal.
   - Each entering voice sings a level above the others for its first two bars while they drop back.
   - Mix: pull cellos / basses back about 2 dB in the Kyrie.

7. **[minor] The climax is a plateau.**
   - Short-term max: Kyrie -13.7, dies -13.6, tremor -13.8, ira -13.6 LUFS (`loudness.png`). The dynamics map tops
     out at 112-120 in all four.
   - The "climax" (ira) adds no layer or level that the Dies irae did not already have.

   **owner:** arranger

   **fix:**
   - Hold something back: the Kyrie's close f rather than ff, the dies at f without the trumpets in its first
     phrase.
   - The ira ff with trumpet fanfares, violins in octaves and a timpani roll into the cadence.
   - Target: the ira 1.5-2 LU over the dies.

8. **[minor] Voice-leading and counterpoint slips.**
   - Nine parallel octaves / fifths in the sung parts. The outer voices were written by hand and bypass `satb()`'s
     check, which only covers the free voices:
     - Requiem bar 2: S and B in octaves D5/D3 - C#5/C#3 - D5/D3, the leading tone doubled in the outer voices. It is
       fixed in the table, score.py L217.
     - Requiem beat 34: S-B octaves Bb-A.
     - Kyrie beat 72: T-B octaves A-D at the final cadence.
     - Kyrie beat 60: A-B fifths E/A - D/G.
     - Kyrie beats 31, 42, 55: octaves.
     - Lacrimosa beat 37.5: S-A fifths E/A - D/G.
   - 29 of the 128 Lacrimosa violin notes sit a semitone or minor ninth from a note the choir sings at that moment
     (e.g. Bb5 over the choir's A4 at beat 36.5, F5 against E5 at beat 40). Appoggiaturas against their own
     resolution in another voice are harsh, not Mozartian.

   **owner:** arranger

   **fix:**
   - Run the fixed outer voices through the same parallel / doubling check (a check-only pass of `satb()`).
   - Re-voice those rows.
   - Keep the violins' appoggiaturas off pitches the choir is sounding at that moment.

9. **[minor] The Requiem's choral entry is a rolled chord, not an imitative entry, and the subito p is a
   diminuendo.**
   - song.py L283-285 delays T and A by 0.5 / 1.0 beat on the same held chord.
   - The map goes 104 -> 84 -> 58 over three beats.
   - `loudness.png`: -21 to -25 LUFS over about 4 s at 0:26-0:30.

   **owner:** arranger

   **fix:** a short "Requiem" motif in imitation, B then T then A then S (the brief promises "voice by voice"), then
   a real step to p.

10. **[minor] The Lacrimosa lament and the Amen are nearly flat, and nothing judges them.**
    - choir_oh: 4.3 dB of note dynamics per phrase in the Lacrimosa and 2.1 dB in the Amen. The report's flat
      threshold is 4.5 dB, but the part is classed `bed`, so it is not judged. Velocities 113-118.
    - The lament carries the section (MIX.md names choir_oh the lead of the Lacrimosa and Amen).

    **owner:** arranger

    **fix:**
    - A swell on each "Lacrimosa" phrase in the oh lane (p < mp > p, 6-8 dB).
    - Shape each Amen chord: lean into the plagal chord, bloom the Picardy chord.

11. **[minor] Tempo breathing is shallow.**
    - Rubato depth 0.03: intro 54-57.2 BPM, Lacrimosa 69.3-74.7 (about +-3 %).
    - Phrase ends broaden only before the fermatas.

    **owner:** arranger

    **fix:**
    - Rubato depth 0.05-0.06 with 'breath' at the phrase ends of the Introitus, Tuba and Lacrimosa.
    - A small tenuto on each Neapolitan chord.

12. **[minor] Range and seams.**
    - choir_oh sings 7 notes (12.2 s) below its sampled range of C3: G2 / A2 / Bb2 in the Lacrimosa bass, the Amen
      and the Tuba's men. Those are stretched samples.
    - 11 loop seams are masked in single tracks in the Kyrie's fermata chord. There are 0 in the mix, which is
      acceptable, and TODO.md already lists them.

    **owner:** sound-designer

    **fix:** put those bass notes on choir_mixed's bass (sampled down to E2) or up an octave.

13. **[minor] Brief honesty and a missing reference.**
    - The Lacrimosa's chromatic soprano climb (A4-Bb4-B4-C5-C#5-D5-E5 to F5 over a falling bass, 12/8, D minor)
      follows the gesture of K. 626's "qua resurget".
    - The Tuba's rising Bb-major trombone arpeggio follows K. 626's Tuba mirum, in the same key.
    - That is fine for the user's wish, and the music is public domain. But the brief says "no ... progression
      lifted".
    - No orchestral reference is available to check the sound against.

    **owner:** producer

    **fix:**
    - Call these two gestures homages in the delivery text.
    - Put a K. 626 recording in `assets/refrences/` (analysis only) and run `compare` like for like (Lacrimosa vs
      Lacrimosa, Dies irae vs Dies irae) on the next round.

## Checklist (recipes/HUMAN_FEEDBACK.md)

- [x] A song, not a loop: five attacca movements, a fugue, composed transitions (fermatas, the timpani roll into the
      choir, the G.P., the hush on low D, the A7 fermata).
- [x] No beepy lead: no synths at all. The leads are the choir, the strings and the solo trombone.
- [x] Lead in front: the choir is +0.5..+3.5 dB over the instruments in its register and -0.4..-1.1 dB against the
      whole orchestra in the tuttis (MIX.md's stem measure). The Tuba solo is 7.2 dB over its bed (`mix`). But the figures under the choir
      are too far back (issue 1).
- [x] Real dynamics: flat_dynamics 0, LRA 16 LU. Violins 8-11 dB, trombone solo 16.6 dB.
      The unjudged choir_oh lament is borderline (issue 10).
- [ ] Played, not keyboard-like: issue 1 (the figures are inaudible), issue 2 (a legato vowel pad in the
      declamation), issue 3 (the organ pad).
- [n/a] Piano rules / jazz rules.
- [x] Hero sound on the solo: the Tuba trombone, played by `hornist` (14 vibratos, blooms, a taper), 16.6 dB of
      dynamics, in front.
- [ ] Produced, not "Gameboy": the hall is lush (reverb -10.4 LU, lows corr 0.97), but the intro is 11 % wide and
      muddy (issue 4) and the top is dull (issue 5).
- [x] clicks 0 in the mix, no clipping, TP -2.47 dBTP.
- [ ] The brief's own targets: loudness / LRA / PLR / TP / width are met. The idiom pillars (the Introitus pulse, the
      storm's 16ths and dotted brass, the Lacrimosa sighs) are not audible (issue 1).

## Keep (what works - must survive the revision)

- **The form and the drama.**
  - Five movements, attacca.
  - The Kyrie grows entry by entry from -30 to -13.7 LUFS short-term.
  - The subito pp of the Quantus tremor: the mix falls from -22.9 to -36.2 dB RMS within a second at 2:25-2:26, then
    climbs back to -16.5 over the rising chromatic bass.
  - The ira -> tuba drop (-11.9 LU).
  - The Lacrimosa climb to its forte (short-term -17.5).
  - LRA 16 LU, PLR 17.1.
- **The vocabulary is right:**
  - the chromatic lament bass;
  - Neapolitan sixths, cadential 6/4s, the deceptive Bb;
  - the Kyrie's Adagio close on a bare fifth;
  - natural-trumpet notes only (D4 / A4 / D5 / F#5) and timpani on D / A;
  - trombones colla parte with A T B;
  - the Lacrimosa's 12/8 with the violins' rest-plus-slurred-pair sigh (the figure is right, it only needs to be
    heard);
  - the plagal Amen with a Picardy third.
- **The solo trombone** (hornist) and the low voices' answer in parallel sixths above it.
- **The seating:**
  - antiphonal violins;
  - trumpets and timpani back left, trombones back right;
  - the choir S A T B read left to right (+4.2 / +0.5 / -2.3 / -3.4 dB).
- **The mix's choir-as-lead balance**, the "dynamic" master (-19.6 LUFS-I, TP -2.5, no glue) and the hall blooms on
  the fermatas.
- **Technically clean:** 0 clicks in the mix, lows correlation 0.97, the cover.

## Evidence index

- `out/overview.png`, `loudness.png`, `tracks.png`, `bands.png`, `stereo.png`, `spectrogram_04_dies.png`,
  `spectrogram_08_lacrimosa.png`.
- `out/zooms/zoom_2m13.9s_choir_s.png`, `zoom_2m13.9s_mix.png`.
- `python -m agentsound mix songs/lux-perpetua`: roles, 1 mud finding.
- `python -m agentsound master songs/lux-perpetua --check --platform dynamic`: ok; tone_profile +3 / +3 shelves.
- Scratch measures (git-ignored `.scratch/`):
  - `vl.py`: parallels, clashes, note lengths, ranges;
  - `stems.py`: RMS per section and envelope curves;
  - `band.py`: band-limited level against all the other stems;
  - `onsets.py`: re-attack depth per written note.

## Revision

The owning roles (arranger, sound designer, mix engineer, mastering engineer, producer) worked the issues in order.
Numbers from the rebuilt song with `--stems`, measured the A&R's way (the scratch scripts re-run: band-limited level
against the sum of all other stems, dry-stem RMS per entry, re-attack depth per written note, parallels between
every pair of sung voices). Still nobody has listened, and there is still no K. 626 recording for `compare`.

Result: -19.5 LUFS-I, TP -1.20 dBTP, LRA 15.1 LU, PLR 18.3, 0 warnings, 0 clicks in the mix (13 masked single-track
loop seams, all low, 12 in the Kyrie's fermata chord), `mix`: no moves (1 info: mud +2.9), `master --check
--platform dynamic`: ok (2 info). No flat_dynamics.

1. **[blocker] The figures are heard.** Arranger: each figure is written a dynamic level above the chords it
   decorates - the Introitus pulse +20-24 velocity steps (mp-mf staccato), the Lacrimosa sighs +10-14 with the
   appoggiatura +5 over its resolution, the storm's 16ths f (+6, beats +10), violins II in measured 16ths on the alto
   in the Dies irae and an octave under violins I in the ira; the trumpets play dotted figures (dotted 8th, 16th,
   quarter) on D / A from the Dies irae's second phrase, fanfares in the ira. Mix: the violins' -1.5 dB trim is gone,
   rides per passage (MIX.md). Band-limited vs all other stems (500-1000 / 1000-2000 / 2000-4000 Hz), before -> after:
   - intro pulse, violins I: -15.7 / -7.7 / -9.3 -> -8.6 / -0.6 / -3.8;
   - requiem pulse, violins I: -20.9 / -19.2 / -12.9 -> -9.8 / -9.7 / -5.9;
   - Lacrimosa bars 1-2, sighs: -8.7 / -7.9 / +1.4 -> +1.4 / -0.3 / +5.1; with the choir: -15.6 / -19.8 / -4.6 ->
     -6.8 / -10.7 / +2.4;
   - Dies irae 16ths: -13.4 / -10.8 / -6.7 -> -9.5 / -7.2 / -4.2;
   - trumpets: -18.1 / -13.5 / -13.7 -> -10.5 / -6.8 / -5.9 (Dies irae, 2nd phrase), -8.5 / -3.9 / -4.0 (ira);
     21 -> 12.7 dB under the mix.
   - Not fully at the -6 dB target where the choir sings in the same octave (requiem, storm): pushing further would
     put the violins over the voices. The choir's sum stays 3-5 dB over the loudest orchestral section in every sung
     section; vs the whole orchestra it went +1.2..-0.4 -> +0.7..-1.9 dB (the orchestra now plays its figures).
2. **[major] Declamation.** Arranger: the Dies irae / tremor / ira chords are sung detached (55-85 % of their value,
   1-beat notes 60 %). Sound: the samples' 1.25 s zone release cannot be shortened per track, so each voice's
   `expression` lane parts the syllables (falls to 0.4 within 50 ms after each note, opens on the next attack).
   Re-attack depth per written soprano note (median): dies 8.0 -> 22.3 dB, tremor 5.9 -> 24.3, ira 8.0 -> 25.1 (the
   timpani read 24-28). The 2.5 s zoom at 2:13.9 now shows separate syllables with gaps.
3. **[major] The organ is a continuo.** It plays the bass line throughout (tasto solo in the Kyrie and the storm) and
   a light right hand (alto + tenor) only in the Requiem's p passages, the Tuba and the Amen; MIX trim -6 dB. Kyrie
   soprano entry: organ -33.6 vs S -35.3 -> organ -45.1 vs S -34.1 dBFS; Lacrimosa: the loudest track (-35.5) -> the
   quietest (-46.3); -42..-48 dBFS in every section, 9-11 dB under the soprano and the violin figures.
4. **[major] The intro.** -29.3 -> -28.1 LUFS (the whole map +6 velocity steps; the +6.9 LU jump into the choir
   stays), width 11.3 -> 25.7 % (the violins' antiphonal pulse now heard; a short stereo early-reflection insert on
   the mono bassoons / basset horns), bass +9.1 -> +2.2, lowmid +10.4 -> +7.5 dB (a 4 dB dip at 300 Hz on cellos,
   violas, bassoons and basset horns in the intro only). Lowmid misses the +6 target by 1.5 dB: 35 % of it is the
   basset horns' sighs (the intro's lead) and 38 % the violins' own pulse around F4-G4.
5. **[major] Tone.** The choir's box cut at the source (-2.5 dB at 600 Hz on every choir track, 5.5 dB with the mix),
   the hall return opened to 20 kHz with a +2.5 dB shelf at 9 kHz, violins' and T / B presence boosts moved or
   removed, a new master plan on the new mix (+3 low shelf, -3 dB at 800 Hz, +3 high shelf 5 kHz). Balance vs the
   classical reference: brilliance -5.7 -> -3.9, air -10.3 -> -6.9 dB (target -7 or better: met); third octaves
   630 Hz +6.3 -> +5.2, 2.5 / 3.15 kHz +4.5 / +5.1 -> +4.3 / +4.7, 5-12.5 kHz -3.2..-9.4 -> -2.4..-4.4. Not met: no
   third octave above +4 in 500 Hz-3 kHz (630 Hz +5.2, 1.25 kHz +4.4, 3.15 kHz +4.7) - the sampled choir and
   sections; the master is at its +-3 dB limit (`master --check` still suggests +3 dB shelves, now only -0.9 dB at
   630 Hz).
6. **[major] The fugue.** The answer is tonal (A-D answers D-A: A3 D4 F4 E4 ..., over Am - Dm7); the free voices move
   in quarters and passing 8ths (43 notes added by `arpeggiate()` / `passing_eighths()`, each checked for parallels
   and semitone rubs); the episode has a walking bass in quarters; each entering voice sings a level above the
   others for two bars (+8 velocity steps and full expression, the others -6 / 0.8) with its colla-parte doubling;
   cellos / basses -2 dB in the Kyrie, the organ tasto solo. Entering voice vs the loudest other part (voices,
   organ, cellos), first two beats: T +2.2, A +4.4, S +1.5, T (F major) +8.5, B +3.3, A +3.6 dB (before: never on
   top).
7. **[minor] The climax.** The Kyrie closes f (map to 108, not 116), the Dies irae is f (110-114) with no trumpets
   in its first phrase, the tremor's crescendo stops at 110, the ira alone is ff (122-124) with fanfares, violins in
   octaves and a timpani roll into the cadence. Short-term max: kyrie -15.3, dies -13.5, tremor -14.6, ira -11.8
   LUFS: the ira 1.7 LU over the Dies irae (integrated +1.8: -14.4 -> -12.6).
8. **[minor] Voice leading.** A check of every pair of sung voices (similar-motion parallels): 9 -> 0. Fixed: the
   Requiem's bar 2 (A7/E: V4/3 under the soprano's C#5, no doubled leading tone), its bar 9 (the lament bass under a
   held D5, 4-3 onto the half cadence), the Kyrie (harmony steps split so the voicer sees the leading tone of the
   subject's last beats, the walking bass, the alto's G4 before its last entry, a bare fifth A3 in the tenor at the
   end), the Lacrimosa (A/E instead of A/C# under the soprano's C#5, Bb instead of Gm/Bb twice, a fixed alto D5 over
   Em7b5/G). Lacrimosa violin notes a semitone / minor ninth from a sung pitch: 29 of 128 -> 0 of 105 (the sighs
   pick a chord tone whose appoggiatura and resolution rub nothing, else a plain note).
9. **[minor] The choir's entry.** B T A S enter a beat apart, each on 'Re-qui-em' (a note, its upper neighbour,
   back; the soprano's pickup lands on the leading tone), f; a real subito p at bar 3 (a step 100 -> 56).
10. **[minor] The lament and the Amen breathe.** A swell on each Lacrimosa bar on the expression lane (0.64 -> 1 ->
    0.64, peaking on the soprano's highest note), the Amen leans into each plagal chord and blooms into the Picardy
    D major; the Tuba's men swell per phrase. Note dynamics: choir_oh Lacrimosa 4.3 -> 9.4 dB, Amen 2.1 -> 5.7 dB;
    the soprano's lament (now 'ah', issue 12) 14.3 dB.
11. **[minor] Tempo.** Rubato depth 0.03 -> 0.05-0.055 ('breath' at the phrase ends of the Introitus, Tuba and
    Lacrimosa), a small tenuto on the Neapolitans (intro, Requiem, Amen: +0.35-0.4 beat).
12. **[minor] Range.** The 'oh' set has samples D2-C#5 (the patch note said C3-C6; corrected): its low G2 / A2 / Bb2
    are recorded samples within a semitone and stay. The real stretch was the lament's soprano D5-F5 (1-4 semitones
    over the top sample): it now sings on the 'ah' soprano (samples to C6). The Kyrie fermata's loop seams stay masked
    (TODO.md).
13. **[minor] Brief honesty.** The Lacrimosa's chromatic climb and the Tuba's rising Bb-major arpeggio are named as
    homages to K. 626 in song.py, ARRANGEMENT.md and the delivery text. Still no K. 626 recording in
    `assets/refrences/` for `compare`.

New findings in TODO.md: a sampler zone's release wins over the track's `release` (no short choir without the
expression gate), the NBO 'oh' range (and `film_orchestra(choir='oh')`'s sweet range), and the voicer / checker
helpers that grew in score.py.

Back to the A&R for a verdict.
