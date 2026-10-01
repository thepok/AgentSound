**Verdict:** this is a well-built demo, but it isn't ready for a synthwave label yet. The bones are right: the pre-chorus drops out for one beat before choruses 1 and 2, the key change is prepared, the ending lands on an F# major chord, and the stylistic choices fit the genre. But the chorus melody uses the same rhythm in nearly every bar. The key change happens 8 bars before the final chorus, so the final chorus doesn't feel like a new key arriving. And the final chorus isn't audibly bigger than chorus 1.

## What the score actually contains (from `out/song.render.json`)

**Chorus hook** (lead and dxlead, one chord per bar, chords `C D G Em ×3 | C D Bsus4 B`). Each bar is written as its notes, with the rhythm in beats:

| Bar | Chord | Notes | Rhythm (beats) |
|---|---|---|---|
| 1 | C | E5 D5 E5 G5 | 1.5, .5, .5, 1.5 |
| 2 | D | D5 C5 D5 F#5 | 1.5, .5, .5, 1.5 |
| 3 | G | F#5 E5 D5 B4 | 1.5, .5, .5, 1.5 |
| 4 | Em | E5, rest, then pickup B4 D5 | 2, 1, .5, .5 |
| 5 | C | E D E G (same as bar 1) | 1.5, .5, .5, 1.5 |
| 6 | D | F#5 E5 F#5 A5 | 1.5, .5, .5, 1.5 |
| 7 | G | B5 A5 G5 F#5 | 1.5, .5, .5, 1.5 |
| 8 | Em | E5, then pickup | — |
| 9–12 | | repeat of bars 1–4 | |
| 13–14 | C, D | same as bars 5–6 | |
| 15 | Bsus4 | B5 A5 F#5 | 2, 1, 1 |
| 16 | B | E5 → D#5 | 2, 2 |

- The long-short-short-long rhythm (1.5, .5, .5, 1.5) is used in 12 of the 16 bars.
- The lead never rests except in bars 4, 8, 12 and 16.
- The peak note B5 lasts only 1.5 beats.
- The melody is identical in all three choruses.

**Harmony by section:**

| Section | Chords |
|---|---|
| Intro | C D G Em |
| Verse | Em Cmaj7 Am7 Bm7 (the bass holds E for the first 8 bars) |
| Pre-chorus | Am Em/B C D Am Em/B C B |
| Chorus | C D G Em ×3, then C D Bsus4 B |
| Breakdown | Cmaj7 Dadd9 Bm7 Em9, 2 bars each |
| Lift | the pre-chorus a whole step up, already in F# minor from its first bar |
| Final chorus | the chorus up a whole step |
| Outro | D E A F#m D E F# (ends on F# major) |

**Bass:**
- Verse 1: octave 8ths on E1–E2.
- Verse 2: a galloping pattern (E1 E1 E2).
- Chorus: the `R.ro` 16th pattern on C2 D2 G1 E1.
- The bass is ducked 12 dB by the kick.

**Drums:**
- Kick on every beat, 8th hats in the verses and 16th hats in the choruses.
- Snare, plus clap in the choruses, on beats 2 and 4. The gated-reverb send is -6 dB.
- Tom fills at bars 3, 7, 11 and 15 of the final chorus. Because they are played with `replace=True`, the kick drops out under them.

## 1. Hook: 6/10

- **What works:** the E-D-E-G cell is singable. Stepping it down and then up is logical. The B5 peak in bar 7 is well placed, and the E5 → D#5 suspension over B makes a good half cadence.
- **Rhythm:** the same rhythm in 12 of the 16 bars makes it sound like an exercise.
- **No space:** the lead never rests, so the brass stabs land on the same beat as the lead instead of answering it. The notes say the brass "answers in the gaps", but the gaps only exist in bars 4, 8, 12 and 16.
- **Stalls:** F#5 is held at the end of bar 2 and repeated on the downbeat of bar 3, which stops the momentum.
- **The peak is too short:** B5 lasts 1.5 beats, the same as every other long note.
- **No pushes:** no note arrives early across a barline, and those anticipations are central to The Midnight and Gunship.

**Proposed hook** (same degree syntax; `_` extends the previous note as in `outro_m`):

```
a1='8:1/4. 7:1/8 8:1/8 10:1/4 9:1/8'       # E5 . D E G F#> (F# pushed into the D bar)
b ='_:1/2 r:1/2'                           # F# held, 2 beats of space -> brass answers
c ='r:1/8 7:1/8 8:1/8 9:1/8 10:1/4 5:1/4'  # 8th run D E F# G, drop to B4
d ='8:1/2 r:1/4 5:1/8 7:1/8'               # (as now)
a2='8:1/4. 7:1/8 8:1/8 10:1/4 11:1/8'      # ... G A> (A pushed)
f ='_:1/4 9:1/8 11:1/8 12:1/2'             # A, F# A, B5 arrives early on beat 3 over D
p ='_:1/2. 11:1/8 10:1/8'                  # B5 held about 5.5 beats over G: the long peak note, then A G
d2='9:1/4 8:1/4. r:1/8 5:1/8 7:1/8'
g2='_:1/2 11:1/4 9:1/4'                    # over Bsus4
hook = a1 b c d | a2 f p d2 | a1 b c d | a2 f g2 h
```

In the final chorus only, replace bar 15 with `'15:1/2. 12:1/8 11:1/8'`. That puts E6 (F#6 after the key change) over the Bsus4, the only time that note appears in the song.

## 2. Harmony: 7/10

- **What works:**
  - The pre-chorus bass climbs A-B-C-D to a major B.
  - The move from that B to C at the chorus is a good lift.
  - The breakdown's new chord colours work.
  - The D-E-F# major ending is textbook and emotional.
- **Clichés:** C D G Em is the genre's standard progression, and that is acceptable here.
- **The key change is misplaced:** the lift starts on Bm, which already belongs to E minor, and slides into F# minor quietly. So the final chorus downbeat sounds like "the chorus again, in a key we've been in for 8 bars", not a new key arriving.
- **Minor points:**
  - The chorus never resolves to the tonic chord at a phrase ending, which is fine.
  - The verse's first 8 bars on a held E are a little static.

## 3. Arrangement and energy arc: 6.5/10

- **Form:** intro 8, verse 1 16, pre-chorus 8, chorus 16, verse 2 8, pre-chorus 8, chorus 16, breakdown 8, lift 8, final chorus 16, outro 9. That is sensible, and the first chorus arrives at 1:05.
- **Repetition:**
  - Verse 1 repeats melody bars 1–2 four times.
  - The pre-chorus melody is heard 3 times, the last time on the solo lead in the lift.
  - The hook is played 3 × 16 bars with no melodic variation. There is no post-chorus riff and no new solo, although a sax or guitar-style solo is a hallmark of The Midnight.
- **The climax doesn't land:**
  - The final chorus is -9.6 LUFS against -9.9 for chorus 2 and -10.0 for chorus 1: only 0.3–0.4 LU louder.
  - The lead's share of the mix drops from 17% to 13.7% because five layers double the same line in the same register (dxlead, vlead an octave down, bells, harm, descant).
  - The four tom fills with `replace=True` knock out the kick in the climax.
- **Stronger moments:** the breakdown dip (-14.5 LUFS) and the ramp up through the lift work well.

## 4. Sound design and genre authenticity: 6/10

- **Patches:** the choices are right (LinnDrum kit, brass_stab plus dx_brass, supersaw plus DX lead, Jupiter strings).
- **Snare too quiet:** the snare is at -25 dB RMS against -18 for the kit (kick and hats). The gated reverb is only 1.5% of the mix.
- **No vibrato on the hook:** the supersaw lead has no vibrato, while the solo lead does. It also has a dull top end (cutoff 4200 Hz, ladder filter).
- **Ear candy:** there are no echo throws at phrase ends. The arp is effectively mono (6% width). Risers, impacts, downlifters and crashes are present and correct.

## 5. Mix: 6/10

- **Clean technically:** -11.1 LUFS, -1.16 dBTP, no clicks, low end mono.
- **Narrow:** width is 18% overall, 10–11% in the verses and 18–21% in the choruses. The genre wants 30% or more.
- **Honky mids:** the 1/3-octave bands at 630 Hz, 800 Hz and 1 kHz read +3.6, +4.4 and +2.2 dB. The final chorus mids are +2.7 dB.
- **Muddy low-mids** in the intro (+8.6) and breakdown (+6.9). Pad (G3–G4), strings (C4–G4), keys and brass are all stacked in the same octave.
- **Low end:** 63 Hz is +4.1 dB but 100–250 Hz is 2.4–4 dB short, so there is weight without punch.
- **Top end:** presence -1.3 dB and air -1.8 dB, even with the +2.5 dB shelf on the master.
- **Loudness arc:** the three choruses sit on the same plateau against the limiter.

## Prioritised changes

1. **Rewrite the hook rhythm** (the `H` dict and `hook =` line in `song.py`). Use the strings above: pushed notes, bars of space in bars 2 and 4, an 8th-note run in bar 3, a long held B5 peak, and the one-off E6 in the final chorus. This is the biggest gain in memorability and it opens room for the brass to answer.

2. **Put the key change on the final chorus downbeat.**
   - Keep the lift in E minor and push up from C to C# in its last bar: `P_lift = s.prog('Am Em/B C D Am Em/B C C#')`.
   - Solo lead: play `pre_m` bars 1–7 untransposed, then `pre_m.slice(28, 32)` at `lift.bar(7)` with `transpose=UP` (G#5 then E#5).
   - Brass and harm in the lift: `br_pre` untransposed, with only the final B stab moved to `lift.bar(7)` with `transpose=UP`.
   - Then C# → D on the final downbeat is the classic 80s key-change hit.

3. **Make the final chorus actually bigger.**
   - Replace the octave-down vlead double with an octave-up one (`transpose=UP+12`, about -8 dB).
   - Remove the bells doubling in the final chorus.
   - Add about +1.5 dB to the lead in the final chorus.
   - Hold chorus 1 back: `dxbrass` and tambourine only in its second half, and `arc(music ...)` chorus 1 at -0.5.
   - Goal: final chorus at least 1 LU above chorus 1.

4. **Tom fills in the final chorus.** Delete the fills at bars 3 and 11. Keep fills only into bars 8 and 16, and restore the kick under them (no `replace=True`, or re-add the `kick` hits). Right now the climax loses its kick every 4 bars.

5. **Bring the 80s snare forward.**
   - `snare` gain_db from -1 to about +2.5.
   - Gated send from -6 to about -1.
   - Kit high shelf from +3 to +1, and `hat.level` down about 2 dB.
   - This also fixes the kit/snare masking note and the kit's 49% share of verse 1.

6. **Make the brass answer the hook instead of doubling its attacks.**
   - With the new hook, put stabs in the gaps: D bar `'........X_..x_..'`, Em bar as now.
   - Keep the downbeat `ONE` stab only on bar 1 of each 4-bar phrase.
   - Pan `brass` -0.3 and `dxbrass` +0.3.

7. **Widen the choruses.**
   - Pan brass as above.
   - Raise the arp's echo send to about -6 with a ping-pong setting, or pair a second arp track panned -0.35.
   - Music bus width from 1.2 to about 1.35 (monobass stays at 150).
   - Pan hats +0.15 and the tambourine -0.2.
   - Target 30–40% width in choruses and about 20% in verses.

8. **Clear the mids and low-mids.**
   - `pad` EQ: high-pass about 150 Hz, cut about -3 dB at 800 Hz and about -2 dB at 350 Hz.
   - Strings in the choruses: `register=(64, 81)` so they sit above the pad.
   - Brass and arp: about -2 dB at 800 Hz.
   - This targets the 630 Hz–1 kHz honk and the intro/breakdown mud.

9. **Brighten and animate the lead.**
   - `lead` fx: add a peak around 3 kHz at +2 dB and a high shelf around 10 kHz at +1.5 dB, or raise cutoff to about 6500.
   - Add delayed vibrato (`lfo1.pitch` about 15, `lfo1.delay` about 0.35, rate about 5.5) so the long B5 sings.
   - Add echo throws: a short throw track or higher echo send on the held notes in bars 4, 8 and 16.

10. **Low-end body.** On `bass`, cut about -2 dB at 60 Hz and boost about +2.5 dB at 120 Hz. This fixes 63 Hz at +4.1 against 100–250 Hz at -2 to -4 and makes the kick-and-bass pulse punchier.

11. **Descant register.** The G5–C6 whole notes sit in the same octave as the hook's peak. Move them up an octave in the final chorus, or write contrary motion (descending C6-B5-A5-G5 while the hook climbs), so they soar above the hook instead of doubling it.

12. **Verse 1 variety.** In bars 9–16, vary the melody (an octave-up answer, or a new second half instead of reusing bars 1–2). Let the e-piano fill the lead's rests with short replies. Optionally trim the intro to 4 bars so the first chorus lands around 0:57.

## Scores

| Area | Score |
|---|---|
| Hook | 6/10 |
| Harmony | 7/10 |
| Arrangement and energy arc | 6.5/10 |
| Sound design and genre authenticity | 6/10 |
| Mix | 6/10 |
| **Overall** | **6.3/10** |

**Label-ready?** Not yet. Changes 1–5 would likely take it to about 7.5–8.

Files are in songs\skyline-heartbeat:
- song.py
- out\song.render.json
- out\report.json
- out\overview.png
- out\loudness.png
- out\tracks.png
- out\bands.png
- out\stereo.png
- out\spectrogram_04_chorus1.png
- out\spectrogram_10_final.png