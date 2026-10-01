**Verdict on "Chrome Leviathan":** a competent demo with the right palette and structure, but not ready for a darksynth label yet. The hook and chorus harmony are too bright and "pop synthwave" for the brief. The last half of the song leans on one 8-bar melody. The low end and mids are crowded, so the chorus doesn't hit as hard as the numbers suggest.

## What the score actually contains (read from song.render.json)

**Hook** (sync lead, 8 bars, played twice per chorus). Each cell is 3+3+2 sixteenths = dotted 8th, dotted 8th, 8th.

| Bar | Chord | Notes |
|---|---|---|
| 1 | C#m | C#5 E5 G#5, then A5! G#5 in quarters |
| 2 | A | E5 F#5 E5, then C#5 half note |
| 3 | E | E5 G#5 B5, then C#6! B5 |
| 4 | B | G#5 A5 G#5, then F#5 D#5 |
| 5–6 | C#m, A | = bars 1–2, bar 6 ends C#5 E5 |
| 7 | D | A5 F#5 A5, then D6! half note |
| 8 | G# | C6(B#)! B5 A5, then G#5 half note |

- All 8 bars use the same rhythm: one 3+3+2 cell plus two quarters or a half.
- Range is C#5 to D6. The phrase ends open on the V chord.
- The flat 2 (D) only appears as D6 over the D chord, where it is just the chord root. So the melody itself never sounds phrygian.

**Other melodic parts**
- **Verse tease:** C#4 E4 G#4 … G#4 A4 G#4 / D4 F#4 A4 … A4 G#4 F#4, in bars 9–16 of the verse only.
- **Verse 2:** the call only.
- **Breakdown and rise:** the hook at half speed on the solo lead.
- **Final chorus:** the hook a half step up, with lead2 harmony (mostly a 3rd below) and an octave-lower double.

**Harmony**

| Section | Progression |
|---|---|
| Verse | i i bII bVII (C#m C#m D B) |
| Build | A B D G#, 2 bars each |
| Chorus | C#m A E B \| C#m A D G# |
| Breakdown | C#m Amaj7 E B, 2 bars each |
| Rise | C#m(2) A(2) D(2) A A7, then Dm |
| Final chorus | the chorus progression a half step up (Dm B♭ F C \| Dm B♭ E♭ A) |
| Outro | C#m C#m D C#m |

- The pad uses smooth close voicings (for example G#3 C#4 E4 G#4 → A3 C#4 E4 A4).
- The seq keeps a C# major 7th over the D chord.

**Bass**
- **Verse riff:** `. C#2 C#2 C#2! . C#2 C#2 C#3 …`, with fills (B2 G#2, then E2 D2 C#2 as a phrygian push) and a B# pickup. This is good writing.
- **Chorus:** bare root 16ths in a `.rRr.rRo` pattern (C#2, A1, E2, B1, C#2, A1, D2, G#1). It has less character than the verse bass.
- **Build:** off-beat 8ths on A1 and B1, then 16ths.

**Drums**
- Four-on-the-floor kick. Hats `x..ox..o`, open hat on the off-beat 8ths.
- Snare plus clap on 2 and 4, sent to the gated reverb.
- The breakdown has a heartbeat kick. The rise is half-time (kick on beat 1 and the "and" of 3, snare on 3).

**Numbers from the report and images**

| Measure | Value |
|---|---|
| Sub vs reference | +3.7 dB overall; build +7.0, build 2 +6.5, chorus +4.6 |
| Third-octave bands | 50–63 Hz +4.4; 100–125 Hz −5.3 / −3.6 (a hole); 630 Hz–1.6 kHz +2 to +3; mid band +2.9 to +3.5 in choruses |
| Presence | −2.3 overall, −5.8 in verse 1, −6.8 in the outro |
| Width | 12% overall, 7–8% in verses and builds |
| Mono sources | seq and hats (correlation 1.00) |
| Phase | gated bus −0.21 correlation at 153% width, wide bus −0.05 |
| Snare | only about 5% of the chorus energy |
| Chorus vs build | +2.1 LU |
| Loudness arc | very flat apart from the breakdown |
| Clicks | 0 |

## Prioritised changes

1. **Put the phrygian menace into the hook itself** (`hook =` in `song.py`, then re-derive `harm`, `tease` and `call_only`). The current tune is aeolian arpeggios in one rhythm repeated 8 times. It sounds like FM-84, not Perturbator. Build it on a flat-2 neighbour cell and alternate busy bars with held bars:
   `hook = mel('C#5!:1/8. D5:1/8. C#5:1/8 G#5!:1/8. A5:1/8. G#5:1/8 | E5!:1/8. F#5:1/8. E5:1/8 C#5:1/2 | G#5!:1/8. A5:1/8. G#5:1/8 B5!:1/8. C#6:1/8. B5:1/8 | A5!:1/8. G#5:1/8. F#5:1/8 D#5:1/2 | C#5!:1/8. D5:1/8. C#5:1/8 G#5!:1/8. A5:1/8. G#5:1/8 | E5!:1/8. F#5:1/8. E5:1/8 C#5:1/4 A5:1/4 | D6!:1/8. C#6:1/8. A5:1/8 D6!:1/2 | D6!:1/8. C6:1/8. A5:1/8 G#5:1/2', vel=104)`
   - The C#–D–C# cell becomes the song's signature, and it teases well in the verse an octave down.
   - The D6 over G# in the last bar is a tritone snarl, and the phrase still falls B#–A–G# onto the V chord.

2. **Darken the chorus harmony** (`chorus_prog`). i–bVI–bIII–bVII is the most common synthwave progression, and the E major makes the chorus brighter than the verse. Use `'i bVI iv bVII i bVI bII V'` (C#m A F#m B | C#m A D G#). Add an `F#m = ('F#2', 3, 10)` cell to `ost_chorus`. The new bar-3 hook notes work over F#m.

3. **Stop running the same melody for 48 bars in a row** (bars 65–112: chorus 2, then the half-speed hook, then the final chorus).
   - In the breakdown, replace `solo.play(slow_hook…)` with a new B theme, for example `mel('G#4:1 A4:1 G#4:1/2 E4:1/2 D4:2 | C#4:4 | E4:1 F#4:1 E4:1/2 C#4:1/2 D4:2 | D#4:4', vel=100)` stretched over the 8 bars. Keep only the quote in the rise.
   - Make the second 8 bars of each chorus differ from the first. Fill the half-note gaps (bars 2, 4 and 6) with lead2 or laser answers, and change bar 8 on the second pass.

4. **Make the chorus drop hit.** Right now the build has more sub (+7 dB) than the chorus, and the chorus is only +2.1 LU louder.
   - Automate `bass 'instrument.hpf'` from 20 to about 180 Hz across `build1`, `build2` and `rise`, snapping back at the downbeat.
   - Clear the kick for the whole last bar, not just the last beat: `kit.clear(build1.bar(7), build1.end)`, and the same in build 2. Let the snare roll and riser carry that bar.

5. **Give the chorus bass the verse riff's character, and relax the ducking.**
   - Replace the chorus `bassline(...)` with a `line()` riff per chord in the same style as `riff`: octave jumps, b7 and 5 fills, and a D2–C#2 push into bars 1 and 5.
   - Set `s.sidechain(bass, …)` to depth 12→5 and release 230→110. The bass already avoids the kick, so the ducker mostly kills the 16th after each kick and leaves the 100–125 Hz hole.
   - Add a synced `lfo` on the bass cutoff at a 1/8 rate for real growl, instead of the current 2-bar sine.

6. **Clear the mid congestion.** The mid band is +3 to +3.5 in choruses and 630 Hz–1.6 kHz is +2 to +3. The pad (C#3–C#5) and stabs (G#3–E5) play the same chords in the same register, with the choir at G#3–G#4 and lead2 on top.
   - Pad: `ride(pad, {… 'chorus': -5, 'chorus2': -5, 'final': -4})` or register `('C#3','G#4')` in choruses.
   - Choir: `choir_reg = ('G#4','G#5')`.
   - Stabs: add an EQ with a 250 Hz high-pass and a −3 dB cut around 1 kHz.

7. **Make the snare huge and bring back presence.** The snare is only about 5% of chorus energy.
   - Snare gain_db +2.5, gated send −6→−3.
   - Set the gated reverb `width` 1.2→0.9 to fix its −0.21 correlation.
   - On the lead, remove the patch's 3.2 kHz −2.5 dB cut (`peak3.gain` 0) so it actually screams. Presence is −1.2 to −1.7 in choruses.

8. **Fix the kick.**
   - `kick__decay` 0.42→0.28. At 124 BPM the tail blurs into the rolling bass, which causes the +4.4 dB bump at 50–63 Hz.
   - The kick is tuned to G#1, which is a tritone against D in the final chorus. Either use a second kit track for `final` with `kick__tune=55` (A1), or drop the modulation. It is a pop key-change move that is rare in this genre, so staying in C#m and adding layers is also a valid choice.

9. **Add lead ear candy.** Currently the lead has fixed pitches, only a light vibrato, and no sync movement.
   - `lead.automate('instrument.pitchbend', …)`: a −2 st to 0 scoop into each D6, and a −12 st dive on the final G#5 of the last chorus pass.
   - `lead.automate('instrument.osc2.semi', …)`: a sync sweep 7→19 across held notes.

10. **Widen the stereo image.** It is 12% overall, 7–8% in verses and builds, and the seq and hats are mono.
    - Move hats and open hats to a separate kit track panned about ±0.2, or give them stereo width.
    - Add `fx.chorus`/`width` to the seq and raise its echo send (−14→−9).
    - Aim for about 20% width in choruses, with the low end still mono.

11. **Give the intro and outro identity.**
    - Intro: play the C#–D–C# cell on a filtered seq or lead in bars 5–8.
    - Verse 1, bars 1–8 (presence −5.8): add sparse lasers or a filtered pulse answer.
    - Outro: it sits at −11.1 LUFS until a cliff at the end. Strip it down in stages (kit out at bar 4, ride the bass and seq −4 dB), or use a deliberate hard stop at `outro.bar(6)` with the impact and the D–C# fall in reverb.

12. **Let the stabs answer the hook instead of doubling it.** `gate_pat` is 3+3+2 twice per bar, the same as the hook cell. Gate only the second half of each bar (for example `'........x_.x_.x.'`) or use off-beat 16ths, so the stabs fill the gaps.

## Scores

| Area | Score | Why |
|---|---|---|
| Hook | 5.5/10 | Clear A-B-A-C form, climax in the right place, but one rhythm throughout and no menace |
| Harmony | 6/10 | Strong phrygian verse and a good A7 pivot, but a cliché, too-bright chorus |
| Arrangement and energy | 6/10 | Solid template and clean drop beats, but weak build-to-chorus contrast and the same melody for 48 bars |
| Sound design and genre fit | 6/10 | Right patch palette, but a thin gated snare, no lead gestures, limited growl and little ear candy |
| Mix | 6.5/10 | Loudness, peak and click targets met, but sub-heavy builds, the 100–125 Hz hole, crowded mids, narrow image and weak presence |

Overall about 6/10: a strong demo, and items 1–5 are what stand between it and a release.

Files:
- songs\chrome-leviathan\song.py
- songs\chrome-leviathan\out\report.json
- songs\chrome-leviathan\out\song.render.json