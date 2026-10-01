# Summer, Overexposed

*(folder: `songs/polaroid-summer/`, v2: the re-production on the dreamwave band preset)*

- **Style:** Dreamwave / chillsynth (FM-84, Timecop1983 territory)
- **Tempo:** 88 BPM, 4/4, 96 bars, 4:25 plus a 10 s tail. The last two bars slow down to 69 BPM (ritardando), and the final chord is held longer (fermata).
- **Key:** D major, with a borrowed minor iv (Gm6) and lydian colour (Gmaj7 with a #11 in the melody, maj7 and add9 tonics). The last chorus and the outro move up to **E major**.
- **Reference:** Timecop1983 - Deckard's Dream (loudness-matched `compare`)

## The song

A warm summer evening you only remember from an old, sun-bleached photograph. The identity of v1 stays the same. A DX7 E.piano plays alone, and a dream pad develops behind it the way a picture develops. The whole song grows from one small cell: *a note, a sigh one step down, back up, then a lift*. Every four bars the harmony turns from Gmaj7 to Gm6, a B-Bb-A line that fades like the colours of the photo. There is a one-beat silence before each chorus, and the last lift goes up a whole step to E major.

What is new in v2:

- **A real instrument carries the second half.** An alto sax (Weresax, sampled) is played with the realism engine: legato transitions, live dynamics shapes, delayed vibrato, portamento into leaps, scoops into phrase entries, and delay throws on phrase ends. It introduces itself with answers in verse 2, plays an 8-bar solo over the chorus changes (a new section), and takes the hook in the E-major final chorus. The soft lead doubles it an octave up, and a harmony line joins in the second half. In the outro the sax plays the signature sigh (here C-B) an octave under the E.piano's displaced hook.
- **A new section: the solo** (8 bars after the breakdown, chorus changes ending on A7sus4). The arc is now breakdown (low) -> solo (medium) -> lift (build) -> final (peak).
- **The vocoder says the title.** Windows TTS (Zira) through `synthwave/vocoder_choir`: "summer" over Dmaj7 and "overexposed" over Gm6 in the breakdown, and "summer" again, as a memory, in the outro. The speech cache is committed in `samples/speech/`.
- **A sampled choir** (VPO female "ah") under the second half of the breakdown and through the whole final chorus.
- **Percussion:** LinnDrum cabasa and congas in the solo groove, 16th hats in the choruses, and tom fills, crashes and a snare pickup at every section change.
- **A real ending.** The music fades by 4-14 dB through the last two bars (a decrescendo per track), the tempo slows into the rolled Emaj9, the E.piano's hall send blooms, and the chord rings into a 10 s tail. v1 ended at full level.
- The verse 2 answers and the outro sax lines were checked against the E.piano melody so they no longer clash (they had minor-second rubs).

## Form

| section | bars | what happens |
|---|---|---|
| intro | 8 | E.piano chords alone (high), a low pad develops in (filter 500 -> 1600 Hz, shimmer), the E.piano plays the hook, glass arp, soft riser |
| verse 1 | 16 | half-time LinnDrum, tied moog-bass roots, soft-lead verse melody; second half adds E.piano answers, glass arp, ghost snares, tambourine, a quiet string bed |
| pre | 4 | ii-iii-IV, then bVI-bVII; climbing sequence, snare roll, riser, **1-beat drop** |
| chorus 1 | 16 | backbeat doubles (snare and clap on 2 and 4, 16th hats), crash and impact, the hook on the soft lead; strings brighten in the second half, where the hook varies |
| verse 2 | 8 | the E.piano sings the verse, and the **sax** answers in its gaps; rim ghosts, 16th hats, a new arp pattern, a high thin string bed |
| breakdown | 8 | drums out, downlifter; the E.piano alone over bVI-bVII; pad, bass, choir and a kick heartbeat return; **vocoder "summer ... overexposed"** |
| solo | 8 | **alto sax solo** over the chorus changes (-> A7sus4); cabasa and congas, glass sparkle, strings |
| lift | 4 | the pre-chorus again, ending on C-D (bVI-bVII of E), snare roll, riser, 1-beat drop |
| final | 16 | **E major**: sax on the hook, soft lead an octave up, harmony line in the second half, choir, strings, busier kick |
| outro | 8 | the groove thins to hats, the hook echoes a beat late on the E.piano, the sax sighs, the vocoder "summer", ritardando + fermata on a rolled Emaj9, fade into the tail |

## Sound

- **Band preset `bands.dreamwave`** (analysis profile `dreamwave`): soft LinnDrum (kick +3 dB, hats -2 dB compared with the preset, kit compressor attack 3 -> 18 ms for punch), moog bass (tied roots from G1, 8 dB kick ducking), dream pad + Juno strings, DX7 E.PIANO 1, soft lead (octave shine), Lexicon 224XL dark hall (IR), 224XL plate, tape echo, shimmer, keyed gated snare, and the master/dreamwave chain.
- **Extras:** alto sax (EQ, compressor, microshift; sends hall, plate, echo), second soft lead (harmony), CELESTE glass arp, VPO choir, vocoder choir + TTS voice (muted modulator), noise riser, downlifter, impact.
- **Mix moves:** EQ on lead, E.piano, pad and strings against the reference's midrange; a master "tone" EQ in front of the preset chain (650 Hz -4.5, 1.9 kHz -4.5, going to -6.5 in the final chorus only, a -1.5 dB shelf above 5 kHz); pad width 0.75 -> 1.0 where the drums play, E.piano width 1.15 in full sections, lows below 140 Hz kept mono on both; shimmer and hall sends bloom in the intro, breakdown and outro; echo throws on the lead and sax phrase ends; per-section fader rides for the energy arc.

## Final numbers (last render)

- **-11.7 LUFS-I**, true peak **-1.20 dBTP**, LRA **6.1 LU**, **0 clicks** in the mix (2 low-level clicks in the choir track alone, masked in the mix, info only), **0 warnings** (2 info) under the `dreamwave` profile.
- Stereo: correlation **0.57**, width 27 % (whole mix), **63 %** above 150 Hz (full sections 55-76 %), lows correlation 1.00, space "lush" (reverb -8.9 LU, echo -17..-21 LU in the full sections).
- Sections (LUFS): intro -16.7, verse1 -12.8, pre -11.2, chorus1 -10.3, verse2 -11.7, breakdown -14.8, solo -11.3, lift -10.5, final -10.4, outro -12.3 (fading to about -22 LUFS short-term before the tail).
- **Compared with Timecop1983 - Deckard's Dream** (whole song, loudness-matched): -11.7 vs -11.3 LUFS; every 1/3-octave region is within about +-2.3 dB (smoothed) from 30 Hz to 14 kHz (bands: sub +1.7, bass -0.1, low mids -1.1, mids +1.8, presence +1.1, brilliance +1.7 dB). Crest 13.4 vs 14.2 dB, PSR 10.0 vs 10.0 dB, width above 150 Hz 67 % vs 158 %, correlation 0.57 vs 0.25, lows correlation 1.00 vs 0.97. Punch: kick 7.7 vs 12.2 dB, snare 10.6 vs 11.9 dB, hats 13.8 vs 12.9 dB. Transients 12.5 vs 13.7 per second.
- Final chorus alone against the reference: -10.4 LUFS; regions within about +-2.7 dB (1.6-2.5 kHz and 100 Hz run highest); crest 11.7 vs 14.2 dB (the densest section).
- v1 against the same reference, for comparison: +7.5 dB too bright at 0.5-14 kHz, -9 dB sub, width 54 %, kick punch 28 dB.

## Remaining weaknesses

- **Kick punch** is still 4.5 dB under the reference (7.7 vs 12.2 dB). The preset's calibration also stopped at 7 dB. The sustained moog bass and pad fill the gaps between the hits.
- **Width** is 63-67 % above 150 Hz, against the reference's 158 %. The reference is phasey in the low mids (negative correlation at 250 Hz-1 kHz). We stay mono-safe on purpose.
- **Chorus vs final:** the final chorus (-10.4) is no louder than chorus 1 (-10.3) because the limiter flattens them. Its lift comes from the key change, density, choir, sax and harmony, not from level.
- **Vocoder intelligibility** has not been judged by ear. It is short, sits under the hall, and is only a flavour.
- The **choir** track has two tiny sample discontinuities at chord changes (bar 84 / 87). They are masked in the mix and flagged as info only.

## v3: the A&R pass (branch `song/polaroid-summer-final`)

A hard listen of v2 (analysis + stems) found five things a listener would hear, and fixed them in `song.py`:

- **The 1-beat drops were not drops.** `clear()` only removes notes that *start* in the gap; the tied moog roots and
  held chords rang straight through, so the "silence" before chorus 1 and the final sat at -13 dB RMS. A `cut()` helper
  now ends every note sounding into the gap: the mix falls to -24..-26 dB RMS for the beat (pad release + reverb
  breathing), then the impact lands.
- **The breakdown opened in a hole.** The E.piano played alone for two bars (-25..-30 dB RMS, 13 LU under the song,
  negative correlation = thin in mono) and then the vocoder hit 6 dB over everything. Now a low dark pad plays from
  the first bar (with a 1.2 kHz carve on the pad in intro/breakdown against the E.piano), the E.piano's hall blooms
  (-14 -> -8), the E.piano is narrowed to 0.85 where it is alone (intro, breakdown), and the vocoder is 3 dB lower
  (it floats in the hall instead of shouting).
- **The final chorus was not the peak.** The limiter now drives 0.8 dB less in chorus 1 and 0.5 dB more in the final
  (automated `fx.limiter.gain`): chorus 1 -10.9, final -10.0 LUFS. The lead sits 1 dB higher in chorus 1 (the E.piano
  comp 1.5 dB lower: bed vs lead 0.4 dB), the sax 1.5 dB higher in the final.
- **The ending released too early.** Fermata 2 -> 4 beats, the pad fades 16 dB (was 6) through the last two bars so
  its release is no step, and the last Emaj9 gets a shimmer send that rings into the tail.
- **Kick, width, tone.** Kick sample +3 dB (5 vs 2), kit glue ratio 3 -> 2.5 with a 25 ms attack, bass ducking 8 dB
  (release 170 ms), hats -4 dB; master width automated 1.6-1.7 where the drums play (1.3-1.4 in intro, breakdown,
  outro); EQ from the compare: bass -2.5 dB at 105 Hz, keys -1.5 dB at 720 Hz, lead / sax dips moved to 2.1-2.4 kHz,
  master tone 700 Hz -5.5 / 2 kHz -5 / 2.25 kHz -1.5 (Q 2).

### Final numbers (v3)

- **-11.7 LUFS-I**, TP **-1.20 dBTP**, LRA 6.3 LU, **0 clicks** in the mix, **0 warnings** (2 info: the choir's two
  masked micro-clicks, moderate drums/pad presence overlap in the pre-chorus).
- Sections (LUFS): intro -16.8, verse1 -12.9, pre -11.5, chorus1 -10.9, verse2 -11.7, breakdown -15.3, solo -11.4,
  lift -10.6, **final -10.0**, outro -12.8.
- Space: lush; width above 150 Hz 81 % (full sections 67-100 %), correlation 0.50, lows 1.00, reverb -9.0 LU.
- vs Timecop1983 "Deckard's Dream", loudness-matched: bands sub +1.7, bass -0.3, low mids -0.7, mids +1.1, presence
  +0.6, brilliance +1.8 dB (smoothed curve within +-1.5 dB 30 Hz-12 kHz); crest 13.7 vs 14.2 dB; kick punch **9.4**
  vs 12.2 (v2 7.7), snare 11.3 vs 11.9, hats 15.7 vs 12.9; width 81 vs 158 % (the reference is phasey in the mids;
  ours stays mono-safe).
- Left as is: the reference's 158 % width (it runs below 0 correlation from 250 Hz to 1 kHz: bad on a phone
  speaker), the hat-punch metric (+2.8 dB; lowering the hats 4 dB did not move it), the macro-dynamics note (intro
  and breakdown are quiet on purpose).
