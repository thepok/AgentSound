# Chrome Leviathan

- **Style:** Darksynth (Perturbator / Carpenter Brut)
- **Tempo:** 124 BPM, with a ritardando and a fermata on the last chord
- **Key:** C# minor with the Phrygian flat II (D). The key change of v1 is gone: the song stays in C# minor and
  the last chorus gets bigger through its layers.
- **Length:** 4:02 (120 bars, 3:55 of music plus the hall tail)
- **Reference:** Perturbator "Future Club" (*Dangerous Days*, 12:59-17:47)

## About the song

Something huge made of metal wakes up under the city.

- **Intro:** a robot voice says "chrome leviathan" over a dark chord. A filtered lead whispers the song's
  signature, the C#-D-C# neighbour cell.
- **Verse:** the growling 16th bass rolls between the kicks and the verse teases the cell an octave down.
- **Build:** A-B-D-G#, from the Neapolitan to the dominant. The bass loses its low end and the kick drops out for
  the whole last bar. Then one beat of silence.
- **Chorus:** the hook is built from the cell in a 3+3+2 rhythm. It climbs to D6 (the flat 2 over the D chord),
  snarls D against G# (a tritone), then falls B#-A-G# onto the dominant. On its second pass it rises into C#
  instead. Distorted brass stabs answer in the gaps.
- **Breakdown:** the drums leave. A keytar plays a new B theme over a real choir, and the robot says "beneath the
  city ... it wakes".
- **Solo:** a distorted lead guitar solo with bends and vibrato, ending on a delay throw.
- **Final chorus:** the harmony, the choir, a supersaw an octave below the lead, then in its second half the guitar
  takes over the octave below; crashes every 4 bars, tight off-beat hats under the ride.
- **Outro:** strips down in stages. The robot says the title once more, the lead falls D to C#, the tempo slows
  into the last chord, and the hall rings out.

## What changed from v1 (following CRITIQUE_v1.md)

1. **Phrygian hook.** It is now built on the C#-D-C# cell, with busy bars alternating with held ones. The tease,
   the call in verse 2, the whisper in the intro and the outro all come from the same cell.
2. **Darker chorus harmony:** i bVI iv bVII | i bVI bII V (C#m A F#m B | C#m A D G#). The E major chorus of v1 is
   gone.
3. **No 48 bars of one melody.**
   - The breakdown has a new B theme on the keytar, and the guitar solo is a new section.
   - The second half of every chorus changes: chorus 1 gets answers and a ride, chorus 2 a harmony a sixth below,
     the final chorus the guitar in unison.
   - The hook's last bar differs on its second pass.
4. **The drop hits.**
   - The bass high-pass rises to 180 Hz through each build.
   - The kick leaves for the whole last bar of build 1, and the last beat before each drop is silent.
5. **Chorus bass with character:** a riff per chord, like the verse riff, with ghost roots on the kick steps
   instead of bare root 16ths.
6. **Mid congestion:** the preset voicings (pad A3-A4, stabs C#4-C#5), stabs only in the second half of each bar,
   and cuts at 1.9 kHz and 3 kHz on the lead.
7. **Bigger snare:** a gated 80s snare (`sampled/80s_gated_kit`) under the 909 snare, and the synth wall ducks
   3 dB on every snare and clap hit.
8. **Kick:** the preset's sampled TR-909 kick (no fixed pitch, so there is no tritone against a new key).
9. **Lead ear candy:** a 2-semitone scoop into every held D6, a -12 semitone dive on the last hook note, and delay
   throws on the last hook note and at the end of the guitar solo.
10. **Width:** the preset (chorus / microshift on the synths, a wide master), with the hall and gated returns
    narrowed so they stay mono-safe.
11. **Intro and outro identity:** the robot voice, the whisper, a staged strip-down, a ritardando and a fermata.
12. **Stabs answer the hook** in its gaps (16th positions 8, 11 and 14) instead of doubling its rhythm.

## Sound

- **Band:** `bands.make('darksynth', s)`. The preset supplies the distorted TR-909 (Rob Roy samples), the growl bass,
  the dark pad, the 16th seq, the distorted brass stabs, the sync lead, the 224XL dark hall, the IR plate, the echo,
  the keyed gated snare, the kick pump and `master/darksynth`.
- **Extra tracks:**
  - `gm/choir_aahs` (a real choir) in chorus 2, the breakdown, the solo, the final chorus and the outro.
  - The guitar: FSBS DI into the `amp('lead')` Marshall chain from `bandlib.rock`, with microshift. It is played
    mono-legato with `art.legato`, glides into leaps, `art.vibrato` and pitch-bend bends.
  - `synthwave/solo_lead` as the keytar.
  - `lead2` (a second sync lead) for the answers and the harmony, and `dbl` (a supersaw an octave down).
  - A gated snare layer, and a vocoder robot: `synthwave/vocoder_choir` keyed by Windows TTS, the German voice
    "Stefan" speaking English with `shift=-4`. The speech is cached in `samples/speech/`, which is committed.
  - Lasers, a noise riser, impacts and downlifters.
- **Mix changes on top of the preset:**
  - **Bass:** +3 dB low shelf at 45 Hz, +4 dB at 170 Hz, and a fast compressor. Its saw peaks were driving the
    master limiter and flattening every section. Fader -2 dB.
  - **Lead:** -2.5 dB at 1.9 kHz and -3 dB at 3 kHz.
  - **Kit:** -4 dB high shelf from 6 kHz.
  - **Returns:** the hall is narrowed to 0.8 and the gated reverb to 0.7.
  - **Master compressor:** threshold -20 raised to -15, so the sections keep their contrast.
  - **Master EQ:** the +4 dB presence lift at 4 kHz is replaced by -0.5 dB at 2.6 kHz, and the air shelf is halved
    to +1.5 dB.
  - **Limiter:** drive 9.4 dB.
  - **Level rides** in every section: thinner verses and a quieter breakdown, so the choruses hit.

## A&R final pass (song/chrome-leviathan-final)

Judged against the render, the stems, the space report and "Future Club" (chorus 2 and the final chorus). What a
listener would have heard, and the fixes:

1. **The hook did not sit on top.** The bed was level with or louder than the lead in chorus 2 (+0.5 dB), the final
   (+0.7) and the breakdown's keytar (+1.3); the guitar solo sat 2 dB under the pad. Rides: lead +1.5 / +2.5 / +2.5 dB
   in the three choruses (-2.5 in verse 1, -1 in verse 2, where the teases sat 7 dB over the bed), keytar +1.5 in the
   breakdown, guitar +3 in the solo. Now bed vs lead -1.6 dB in every chorus, the guitar leads the solo (-24 vs pad -26
   dBFS RMS).
2. **The bass had no pump.** The added bass compressor (2 ms attack, auto make-up) sat after the preset's kick ducker
   and pulled the ducking straight back up: a flat wall under the kick. The shelf + compressor now go before the
   ducker, the ducker is 6 dB deep, and a 3 dB snare-keyed duck clears the backbeat. Bass trim -2 -> -1 dB and the 45 Hz
   shelf +3 -> +4.5 dB, so the low end did not lose weight (sub -1.0, bass 0.0 dB vs the profile).
3. **Transients.** Kit compressor attack 5 -> 15 ms, master tape drive 9 -> 6.5 (less soft-clipping of the snare), the
   gated snare layer +2 dB in the choruses with a 220 Hz body bump and its fizz cut (-6 dB shelf from 5.6 kHz: it held
   58 % of the brilliance band). The final groove swaps the open hats for tight accented off-beat hats under the ride.
   Kick punch 9.8 -> 9.7..9.9, hats 12.8 -> 14.1 dB (chorus 2), 10.6 -> 11.5 dB (final).
4. **The final chorus was crowded** (lead + guitar in unison + supersaw an octave down + harmony + choir: mids +1.8 dB
   at 1.4-2.8 kHz). The supersaw double plays only the first half; in the second half the guitar takes over the octave
   below (hook2 an octave down, +1.5 dB), so the second half changes colour instead of piling up. Choir -2.5 dB in the
   final, lead2 -2.5 dB at 1.8 kHz, lead -1.5 dB at 1.1 kHz (Q 2), master -1.5 dB at 2.6 kHz. Both compared sections
   now show no tone suggestions.
5. **Arc.** Verse 1 thinner (kit -7/-5, bass -8/-6, seq -2.5, pad -6.5), breakdown bed deeper (pad -8.5, choir -6.5):
   verse -11.2, build -9.8, chorus -8.9 LUFS; LRA 3.2 -> 3.7 LU.
6. **Width and mono.** Master width 1.15 -> 1.25 (lusher wall above 150 Hz: 38 -> 42 %), with the hall narrowed
   0.8 -> 0.7 and the shimmer to 0.8, so the pad-only intro (correlation 0.29) and the hall tail (width 99 -> 63 %)
   stay safe on a mono phone speaker. Limiter drive 9.4 -> 9.8 dB.

## Final numbers (profile darksynth, after the A&R pass)

- **Loudness:** -9.7 LUFS-I, true peak -1.14 dBTP, LRA 3.7 LU. 0 clicks, 0 warnings (3 info masking notes).
- **Sections (LUFS):**

  | intro | verse | build | chorus | verse2 | build2 | chorus2 | breakdown | solo | final | outro |
  |---|---|---|---|---|---|---|---|---|---|---|
  | -13.1 | -11.2 | -9.8 | -8.9 | -10.1 | -9.8 | -8.9 | -10.9 | -8.5 | -8.8 | -10.4 |

- **Balance vs the darksynth reference (dB):** sub -1.0, bass 0.0, low mids -0.2, mids +0.7, presence +1.8,
  brilliance +0.8, air -3.2 (tilt -4.9 dB/oct, reference -5.2).
- **Stereo:** width 16 % (41 % above 150 Hz; 42-44 % in the choruses), correlation 0.73, low end mono (1.00); every
  section's correlation >= 0.29.
- **Space:** reverb -12.4 LU, echo -18.4 LU, bed -1.7 dB vs lead (-1.6 in every chorus), every section "lush".
- **Compare vs "Future Club"** (loudness-matched):

  | measure | chorus2 | final | reference |
  |---|---|---|---|
  | tone | within tolerance (no tone suggestions) | within tolerance (no tone suggestions) | |
  | crest | 10.0 dB | 10.1 dB | 10.0 dB |
  | kick punch | 9.7 dB | 9.9 dB | 11.4 dB |
  | snare punch | 9.3 dB | 8.8 dB | 14.0 dB |
  | hat punch | 14.1 dB | 11.5 dB | 16.8 dB |
  | width above 150 Hz | 45 % | 43 % | 27 % |
  | correlation | 0.73 | 0.73 | 0.73 |

## Remaining weaknesses

- Snare punch stays ~5 dB under the reference: the gated layer is flat-topped by nature, and the dense 16th bass
  and the wall fill the 150 Hz-4 kHz band right before each hit. Closing it would need a transient shaper (the engine
  has none) or a much lighter master; the preset notes accept 2-5 dB.
- The section contrast is modest (LRA 3.7; the reference has 3.1). The master is still a loud darksynth master.
- The mix is wider than the reference (about 44 % vs 27 % above 150 Hz). This is deliberate, because the listener
  asked for lush. It stays mono-safe.
- Everything was judged by analysis, not by ear. The vocoder's intelligibility, the guitar's bends and the
  mid-band density of the final chorus (lead + harmony + guitar an octave below) deserve a listening check.
