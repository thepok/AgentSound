# Critique: "Last Exit Before Dawn" (songs/midnight-interstate)

**Verdict:** It is technically clean, but it is not ready for a label yet. The palette is right for the genre and the structure is sound. The low end, the level of the lead and the stereo image sound like a demo, and the hook is well built but generic.

## Transcribed score (from out/song.render.json)

**Hook** (supersaw at octave 5, with the pulse double an octave below). Positions are beats within the bar.
- Bar 1, F#m: C#5 at 0, F#5 at 0.5, rest, F#5 at 1.5, G#5 at 2, A5 at 2.5 (held one beat), G#5 at 3.5
- Bar 2, D: F#5 (1.5 beats), D5, D5, C#5
- Bar 3, A: the head again, climbing A5 then B5
- Bar 4, E: C#6 (1.5 beats), B5, G#5 (held)
- Bars 5 to 12: the same 4-bar phrase twice more. Only the endings change (b2 turns up, b4 falls to E5).
- Bar 13, D: F#5, A5, A5, C#6, D6, C#6. This is the climax.
- Bar 14, E: B5, C#6, B5, G#5
- Bar 15, F#m: G#5 then F#5 (held)
- Bar 16: the head again as a pickup

The head (C#-F#, rest, F#-G#-A) is heard 6 times in 16 bars. The range is C#5 to D6.

**Harmony**

| Section | Chords |
|---|---|
| Intro | F#m, Dmaj7, A, E (x2), the same as the chorus |
| Verse | F#m, E, D, E. Bars 1-8 over an F# pedal, bars 9-16 on the roots |
| Build 1 | Bm (2 bars), D (2), E (2), C#sus4, C# |
| Build 2 | Bm, D, E, C# (1 bar each) |
| Chorus | F#m, D, A, E (x3), then D, E, F#m, F#m |
| Bridge | Dmaj7 (2 bars), E (2), then F#m, B, D, E, F#m, B, E, F# |
| Final chorus | The chorus up a whole step to G# minor |

Pad voicings: F#3-F#4-A4-C#5, then F#3-F#4-A4-D5, A3-E4-A4-C#5, G#3-E4-G#4-B4.

**Bass:** 8th-note octaves, with the low root on the beat and the upper octave on the off-beat (for example F#1, F#2, F#1, F#2). It switches to 16ths in the second half of chorus 2 and the final chorus. Verse 2 uses the pattern "rorororf". It is sidechained 10 dB with a 180 ms release from the kick, and every low root lands on a kick.

**Drums:** kick on every beat, tuned to F#1 (46 Hz) with 0.4 decay. Snare on 2 and 4, plus a clap in the choruses, sent to the gated reverb bus at -6 dB.
- Verse hats: 8ths, then 16ths from bar 9.
- Chorus hats: 16ths with an open hat on the last 16th.
- Bridge: no drums in bars 1-4, half-time in bars 5-8, then a roll into the final chorus.

## Scores (0-10)

| Area | Score |
|---|---|
| Hook | 6 |
| Harmony | 6 |
| Arrangement and energy arc | 6 |
| Sound design and genre fit | 6 |
| Mix | 5.5 |
| Overall | about 6 |

## 1. Hook (6)

**What works:**
- The head is singable and has a clear signature: the leap up a fourth (C#-F#), the rest on beat 2, and A pushed ahead of beat 4.
- The call-and-response form (A B A C) is clear.
- The climax on D6 comes late, and the ending (G# to F#, then the head as a pickup) is good craft.

**What doesn't:**
- The contour circles F#-G#-A-G#, a neighbour-tone figure heard in countless tracks.
- The head is heard 6 times. The rhythm is almost all 8th notes, and the only held notes are the 1.5-beat F#5 and C#6. There is no long "anthem" note to sing along with.
- The climax D6 sits on the root of the D chord, which is the least tense choice.
- The verse melody uses the same "rest, then four 8ths" cell, so the song leans too hard on one rhythm.

**Suggested rewrite** (same scale-degree syntax, over the new chorus chords in change 2):
- `a1` (D): `5:1/8 8:1/8 r:1/8 10:1/8 12:1/4.! 10:1/8`, giving C#, F#, rest, A, C#6 held, A. The held C#6 is the major 7th of D.
- `a2` (E): `11:1/4. 10:1/8 9:1/2`, giving B held, A, G# held.
- `a3` (F#m): `5:1/8 8:1/8 r:1/8 10:1/8 12:1/8 13:1/4! 12:1/8`. The D is a b6 leaning onto C#.
- `a4` (A): `14:1/2 12:1/4 10:1/4`, giving E6 held (a new peak), C#6, A5.
- `c1` (D): `10:1/8 12:1/8 r:1/8 12:1/8 14:1/8 15:1/4! 14:1/8`, climbing to F#6, the 3rd of D.
- `c2`: `14:1/4. 13:1/8 11:1/2`
- `c3`: `12:1/4 10:1/8 9:1/8 8:1/2`

## 2. Harmony (6)

**Strong points:**
- The harmonic-minor C#sus4 to C# at the end of build 1.
- The dorian B major (with a D#) in the bridge.
- The move to G# minor through E and F# is well prepared.

**Weak points:**
- The same few chords appear in every section: i, VI and VII in the intro, verse, chorus and outro. The intro even uses the exact chorus progression.
- The chorus lands on F#m, the chord verse 1 has just held over the F# pedal for 8 bars. After the strong C# (V) in the build, landing on the tonic flattens the lift.
- Chorus 2 has harmony clashes. The thirds harmony puts A5 over the E chord (bars 4 and 12, held 1.5 beats, against the pad's G#4, a suspended 4th against the major 3rd). It also puts D5 against the pad's C#5 over F#m (bars 1, 3, 5 and so on, a minor 2nd).

## 3. Arrangement and energy arc (6)

**Energy by section (LUFS):**

| Intro | Verse 1 | Build 1 | Chorus 1 | Verse 2 | Build 2 | Chorus 2 | Bridge | Final | Outro |
|---|---|---|---|---|---|---|---|---|---|
| -15.1 | -12.9 | -11.6 | -10.3 | -12.2 | -11.2 | -10.0 | -12.0 | -9.7 | -12.4 |

- **Contrast is mostly volume, not parts.** Verse and chorus play the same kit and bass pattern; the verse gets a -4.5 dB `gainDb` dip. The within-section curves are nearly flat (LRA 4.4 LU).
- **Verse 1 drags.** It runs 16 bars of kick, bass and pulse lead, and the melody repeats one rhythm 8 times. The pad (-32 dB) and arp (-33 dB) barely register. The first chorus arrives at 1:09.
- **The breakdown is too short.** The report says the bridge "dips to -17 LUFS", but only the first 4 bars do. From bar 81 the drums and bass are back, and the section averages -12.0, the same as a verse. The keytar (-25 dB) is quieter than the bass (-24 dB) there. The final chorus therefore has no real valley to rise out of. It is only 0.3 LU louder than chorus 2, so the key change carries all of the lift.
- **What works:** the one-beat drops, impacts, risers, fills every 4 bars in the final chorus, the glass hook in the intro and the keytar reprise in the outro.

## 4. Sound design and genre fit (6)

**Right choices:**
- 7-voice supersaw hook doubled by a pulse lead.
- Legato saw keytar with glide and delayed vibrato.
- DX7 celeste bells and E.PIANO 1, and Jupiter-style strings.
- Simmons toms and a gated reverb bus.

**What's off:**
- **Kick:** a long 46 Hz kick that is 66% sub reads as a modern 808, not an outrun or Linn-style kick.
- **Gated snare:** the gated bus sits at -30 dB against the dry snare at -24 dB in the choruses, so the bloom that defines the sound is hidden. The snare track is 58.6% in the 60-250 Hz band: boom, not crack.
- **Arp:** the 16th arp sits in A3-F#5 with a 700-1600 Hz cutoff. It is 63% low-mid, 3% of the chorus mix and 5% wide, so the genre's heartbeat is nearly inaudible.
- **Other layers:** strings (-31 dB) and choir (-32 dB) are barely audible.
- **Ear candy is thin:** no delay throws, reversed cymbals or other movement effects.

## 5. Mix (5.5)

**Clean:** 0 clicks, true peak -1.14 dBTP, PLR 10.1 and -11.2 LUFS are all fine.

**Problems:**
- **Low end:** the sub is +4 to +5.8 dB above the reference in every section, while the 60-250 Hz bass band is -1.5 to -2.1. The bass's on-beat F#1 roots are ducked 10 dB by a kick tuned to the same note, so the octave drive becomes an off-beat F#2 pulse.
- **Midrange:** the third-octave curve peaks at +3.9 dB at 800 Hz and +3.0 at 1 kHz, and dips -3 to -4 dB from 125 to 315 Hz. Mid is +3 to +3.9 in the choruses, while presence is -0.5 to -2.4 dB. The hook EQ even cuts 3.4 kHz by 2 dB.
- **Balance:** the hook (-22.7 dB) is only the third-loudest part in the chorus, behind the kit (-20.0) and the bass (-21.7). The drum bus makes up about 50% of the chorus mix.
- **Stereo:** width is 13% overall, and it collapses from 30% in the intro to 7% in verse 1. The echo bus leans 8.3 dB to the left.

## Prioritised changes (most impactful first)

**1. Low end** (the `KICK_LO/KICK_HI` constants, the `kit` patch and `s.sidechain(bass, ...)`)
- **How:**
  - Retune the kick to A1 (55 Hz) and B1 (61.7 Hz) after the key change; both are the minor 3rd of the tonic.
  - Set `kick__decay=0.25`, `kick__sub=0.05` and `kick__click` to about 0.45.
  - Set the bass sidechain to `depth=5, release=90`.
  - Add EQ on the bass: +2 dB at 110 Hz and a high-pass at 35 Hz. Raise `gain_db` from -1 to 0.
- **Why:** sub is +4 to +5.8 dB and the bass band is -2 dB. The octave bass should drive the song, not pump.

**2. Reharmonise the chorus to start on VI** (`P_chorus`, `P_bridge`)
- **How:**
  - `P_chorus = s.prog('VI VII i III') + s.prog('VI VII i VII') + s.prog('VI VII i III') + s.prog('VI VII i i')`. The current hook already fits: C# is the major 7th of D and G# is the major 7th of A.
  - The build's C# (V) then goes to D: a deceptive cadence, the classic outrun lift.
  - End the bridge on the V chord of G# minor instead of `VII I`: `... + s.prog('VI Vsus4:0.5 V:0.5').transpose(UP)` (E, D#sus4, D#). The final chorus then also lands deceptively.

**3. Move the hook forward and brighten it** (the `hook` track, its EQ, the `music` bus)
- **How:**
  - Hook `gain_db` from -1 to +1.
  - Replace the hook EQ's 3.4 kHz -2 dB cut with +1.5 dB at 3 kHz and -2 dB at 900 Hz (Q 1).
  - Hook echo send from -15 to -10.
  - Pull the kit back 1.5 dB in the choruses (`E['chorus1'/'chorus2'/'final'] = -1.5` for the kit only).
- **Why:** the hook is behind the drums and bass, and the mix has an 800 Hz-1 kHz bump with a presence dip.

**4. Make the bridge a real breakdown** (drums, bass and the `E['bridge']` energy setting)
- **How:**
  - Drop the half-time kit and snare in `bridge.bar(4)`. Keep drums out for bars 0-7 (hats only from bar 4 if needed), then run `g_verse_b` for bars 8-9, kick only at bar 10 and the roll.
  - Start the bridge bass at `bridge.bar(8)`, or play whole notes with the cutoff closed until then.
  - Keytar gets +2 dB and `cutoff` 2400 in the bridge.
- **Why:** aim for about -15 LUFS over 8 bars, so the key change lands.

**5. Make the 16th arp audible** (`AR`, `AR_UP`, arp gain and cutoff automation)
- **How:**
  - Registers: `AR=('F#4','F#5')` and `AR_UP=('G#4','G#5')`.
  - Arp `gain_db` from -6 to -3.
  - Multiply the cutoff automation values by about 1.8 (verse about 1300, chorus about 2600).
  - Add an echo send at -8 and slow pan automation (±0.4).
- **Why:** it is 63% low-mid and 3% of the mix, and it fights the pad register.

**6. Replace volume-only contrast with arrangement** (`E` and the verse 1 drums)
- **How:**
  - Cut the verse kit dip from -4.5 to -2.
  - Verse 1 bars 0-7: kick and 8th hats, no snare, bass cutoff automated down to about 450 Hz.
  - Bring in the snare backbeat and open the bass filter at bar 8.
  - Move the e-piano stabs into verse 1 bars 8-15, so the verse grows on its own.

**7. Fix the width** (pad `energy`, sends, echo bus)
- **How:**
  - Don't dip the pad in the verses (`energy(pad, verse1=-1.5, verse2=-1.5)`).
  - Send the hook double to `wide` at -10.
  - Pan the glass to -0.5 and the keys to +0.4.
  - Fix the echo bus's 8.3 dB left bias (try `width` 1.0, or offset the ping-pong start).
- **Target:** verse width 15% or more, chorus 22-25%.

**8. Bring out the gated snare** (the `snares` sends, the gated bus EQ)
- **How:**
  - Gated send from -6 to 0 dB, and raise the `energy(snares, 0.35)` scale to 0.5.
  - Snare track: +3 dB at 2.8 kHz and -3 dB at 180 Hz.
  - Soften the gated bus's 3.8 kHz -9 dB cut to -3.
- **Why:** the bloom should be about as loud as the dry snare.

**9. Fix the chorus 2 harmony clashes** (`harmony_m`)
- **How:** use diatonic 6ths below instead of 3rds, so the harmony follows chord tones: `hook_m.transpose(-5).clip(octave=4, vel=80)`. Or hand-fix bars 4 and 12 (A to G#) and the D5s over F#m (D to A).
- **Why:** this removes the suspended-4th-against-3rd clash over E and the minor 2nds against the pad's C#5.

**10. Adopt the hook rewrite from section 1** (`H` dict: `a1-a4`, `c1-c3`)
- **Why:** it adds long notes (the major 7th over D, an E6 peak) and a higher climax (F#6), while keeping the C#-F# signature and the call and response.

**11. Break up the verse melody's rhythm** (`verse_m`, `verse_var`)
- **How:** keep bars 1-2, then:
  - Start bars 3 and 7 on the downbeat with a held note.
  - Push the phrase ends ahead of the bar (an 8th early into the next bar).
  - Let the lead rest in bars 5-6 while the glass answers.
- **Why:** 8 identical "rest, then four 8ths" cells in 16 bars is too many.

**12. Final-chorus payoff and ear candy**
- **How:**
  - Add 3-5-note keytar answer licks in the hook's held notes of the final chorus (bars 2, 4, 8, 12 and 15-16), echoing the solo.
  - Automate the hook's echo send to +8 dB on beats 3-4 of bars 4, 8 and 12 (delay throws).
  - Add a reversed crash or open hat for the last 2 beats before each chorus.
  - Sweep the bass filter (400 to 1800 Hz) through the builds.

The files I used are `songs\midnight-interstate\song.py`, `songs\midnight-interstate\out\report.json`, `songs\midnight-interstate\out\song.render.json` and the images in `songs\midnight-interstate\out\`. No files were edited.