# Halo Orbit

*(folder: `songs/orbital-station`)*

- **Style:** sci-fi / soundtrack synthwave (S U R V I V E, Stranger Things, Vangelis' Blade Runner)
- **Tempo:** 84 BPM, 4/4, about 4:11 incl. the tail; ritardando to 66 BPM into the last chord
- **Key:** E minor with maj7 / min9 colours; the final section lifts a whole step to F# minor
- **Sound:** band preset `bands.scifi` (reference-calibrated) plus a Fairlight CMI choir, a sampled tenor sax,
  CS-80-style brass, Jupiter + sampled orchestral strings, a glassy FM counter-arp, a sonar ping, a vocoder
  station voice and real (reversed) cymbals
- **Delivery:** `METADATA` (Halo Orbit / AgentSound / Neon Archive / Synthwave), `COVER` synthwave style,
  midnight palette

## The song

A station drifts in a halo orbit and picks up a signal. The robot voice of the station says
"signal detected" over the first Em9 while a muffled Stranger-Things arpeggio (1-3-5-7-9) fades in with
bell pings and a sonar ping. Over four minutes the arpeggio's filter opens, so the music comes into focus. In the
verse the bells play the "signal" (the chorus hook in miniature, sequenced down the scale); the second pass
brings the pulse sequence, a soft TR-808 heartbeat and a Phrygian Fmaj7. The build sits on a B pedal with the
Fairlight choir swelling, a snare roll, a riser and a reversed cymbal that sucks into a one-beat dry silence
with a single sonar ping echoing into it. The chorus hook (B-E-G, F#-E-D, then an answer with an octave leap to the leading
tone D#) sits over VI-VII-i with a deceptive V->VI loop; the second pass adds the choir, a string line in 6ths
and 3rds under the hook, the bells an octave up, claps and a pulsing bass. The breakdown drops the drums: a
tenor sax sings the hook augmented (legato, delayed vibrato, swells, a delay throw on its long B) over the
choir and a floating arp, with glassy sparkles above. A four-bar climb pivots through Dmaj7 / C#7 into
F# minor; after another dry beat the final section lands with the full backbeat, CS-80 brass on the hook,
orchestral + Jupiter strings, the glass counter-arp and the choir, the sax answering the brass in the
second pass. In the outro the bells play the signal one last time, the robot says "signal lost", the tempo
slows into a held F#m9 (plagal Bm9 -> F#m9) and the mix narrows and fades into the hall tail.

## Form

| section | bars | what happens |
|---|---|---|
| intro | 8 | impact, filtered arp + sweep pad fade in, sonar pings, bass + choir hint, "signal detected" |
| drift (verse) | 16 | bells play the signal; pass 2: arp pattern B, dotted bass, bII, pulse sequence, 808 heartbeat + fill |
| approach (build) | 8 | B pedal (8th bass crescendo), choir swell, 16th sequence, hats/kick, snare roll, riser, reversed cymbal, dry drop + laser |
| orbit (chorus) | 16 | half-time 808; hook on soft lead + bells; pass 2 choir, string line, bells 8va, claps, 8th bass; tom fills |
| weightless (breakdown) | 8 | no drums; tenor sax sings the hook augmented, choir, sparse arp 8va, glass sparkles, shimmer bloom |
| ascent (build) | 4 | 16th arp runs, 16th bass, kick on every beat, snare roll, tom fill, riser, reversed cymbal, dry drop |
| horizon (final) | 16 | F# minor, backbeat + claps, brass hook, orch + Jupiter strings, glass arp, choir; pass 2 choir opens up, bells 8va, strings + sax harmony, tambourine |
| outro | 8 | the signal on bells, "signal lost", ritardando into F#m9, reversed cymbal + soft impact, fade into the tail |

## Production notes

- Everything starts from `bands.scifi(s)`: sampled TR-808, stranger_arp, seq_pulse, sweep pad, moog bass,
  DX bells, soft lead, dark 224XL hall (narrowed), tape echo, shimmer, the kick pump and master/dreamwave.
- Extra voices get a presence/top trim (`tame()`); the Fairlight choir gets Juno chorus + dimension (the CMI
  sample is nearly mono). The bells are 2 dB down with a 2.8 kHz dip; the pad dips 1.6 kHz and, only while
  the bells sing the verse, 1.4 kHz a further 5 dB (named eq `room`). Bass +2.5 dB shelf at 40 Hz.
- Master: the preset's chain with an extra broad dip (-2.5 dB at 1.6 kHz, -1.5 dB at 4 kHz), limiter +0.8 dB,
  master width 1.65 (1.15 while the pad is alone in the intro, 1.1 into the tail: mono-safe), master fade
  -9 dB over the last chord.
- Added a 224XL plate (`bus/ir_plate` +7 dB) for the sax and the brass; shimmer return narrowed to 0.75.
- Arc: bass lighter in intro/verse (-3 dB), breakdown and outro (-4 dB); sax +3 dB in the breakdown; choir
  steps back 3 dB under the sax and 1.5 dB in the final section; the returns are cut for both dry drops.
- The station voice is Windows TTS (Zira, rate -3) through `synthwave/vocoder_choir`; cached WAVs in
  `samples/speech/` (committed) so it re-renders without Windows.

## Final review (A&R pass, branch song/orbital-station-final)

What a listener would have heard on the first re-production, and what changed:

- **The final chorus buried its hook.** The CS-80 brass sat at -24 dB RMS under pad, choir and orchestra (each
  -22..-23): the climax was a wall without a tune. Now the brass is +4.5 dB (with a dimension halo), the soft
  lead doubles it 2 dB under, the pad (-1 dB), choir (-2.5 dB) and orchestra (-2 dB) step back, and a
  section-only master dip (-3 dB at 1.3 kHz, Q 0.5, `fx.final`) keeps the stack from getting honky. The brass
  alone is now level with the whole bed (+0.3 dB bed, was ~+6), brass + doubling lead sit ~2 dB on top. The
  tracks are named `brass_lead` / `sax_lead` so the report measures them as the leads they are.
- **The chorus-1 lead** got +1.5 dB and a -2 dB bell at 2.2 kHz: over the bed (-0.5 dB) without the edge.
- **"Pew" laser zaps -> a sonar ping.** The synced-saw laser was exactly the video-game sound the user dislikes
  (and it was the only sound in both dry drops). It is now an FM sine ping with a metallic strike, thrown into the
  tape echo and the hall (the station's sonar: fits the "signal" story); the final's triple shots became single
  pings.
- **The intro was inaudible on a phone.** The arp started at a 220 Hz cutoff behind the preset's 300 Hz high-pass
  (-31 dB RMS, nothing a phone speaker plays); it now opens from 420 Hz (560 at the verse, 850 at the build) and
  closes to 380 Hz at the end. The choir hint in the intro was -45 dB: now audible (-41).
- **The breakdown was no breakdown** (only 1.7 LU under the chorus). The bass now sits out the sax's first
  phrase and enters under the second (with a 180 Hz dip on the pad while it plays): weightless -13.8 LUFS, 3 LU
  under both choruses, so the final lands.
- **Verse pace:** a soft 808 hat "clock" (crescendo) in bars 5-8 of the verse, so the pulse arrives 12 s earlier
  and leads into the heartbeat.
- **Low end:** the preset's 36 Hz bass high-pass lowered to 29 Hz, the extra 40 Hz shelf down from +2.5 to +0.5
  dB: the 22-35 Hz hole is gone without the 36-56 Hz region swelling.
- **Master:** a -1.5 dB bell at 700 Hz added to the broad dip; limiter gain 2.3 -> 2.9 dB.

## Final numbers (dreamwave profile)

- **-12.3 LUFS-I**, LRA 5.0 LU, true peak -1.20 dBTP, PLR 11.1 dB, crest 12.8 dB, 0 clicks, 0 errors,
  **0 warnings**, 2 info (top end -7.4 dB and tilt -7.0 dB/oct vs the profile: the reference record is just as dark)
- Sections: intro -16.2, drift -14.0, approach -12.9, orbit -10.7, weightless -13.8, ascent -11.8,
  horizon -10.8, outro -14.1 LUFS
- Space: lush in every section; width above 150 Hz 85 % (full sections 79-88 %), correlation 0.57 (sections
  0.48-0.64), low end mono (0.98), reverb -9.7 LU, echo -20.0 LU; bed vs lead: orbit -0.5 dB (lead on top),
  weightless +0.2 (sax level with the bed), horizon +0.3 (brass alone; with the doubling lead ~2 dB on top)
- Compare vs Timecop1983 "Deckard's Dream" (loudness-matched):
  - whole song: every 1/3-octave region within +-2 dB (largest: sub 36-56 Hz +1.7); crest 13.5 vs 14.2 dB,
    punch snare 11.9 vs 11.9, hats 11.5 vs 12.9, kick 9.6 vs 12.2 (the drumless intro/verse/breakdown), width
    85 vs 158 %
  - orbit: -10.7 vs -11.3 LUFS, within +-2.5 dB (brilliance 8.9-14 kHz -3.1: the reference's hats/air), kick
    punch 13.3 vs 12.2
  - horizon: -10.8 vs -11.3 LUFS, within +-2.8 dB (561-898 Hz +2.7, 223-354 Hz -2.0, 1.8-2.8 kHz +1.9; was
    +3.3 dB over 0.45-2.8 kHz with the louder hook before the section dip), width 92 %, kick punch 15.6 vs 12.2
    (the backbeat final; the kick itself is small, the 808 snare and clap bursts carry low end)

## Remaining weaknesses

- Width stops at ~85 % above 150 Hz vs the reference's phasey 158 % (kept mono-safe on purpose).
- The final chorus reads 3.4 dB punchier in the low band than the reference (backbeat vs a steady wall); a
  shallower bass pump there made it worse, so the preset's pump stays.
- The sax is dry-mono in the centre with hall/plate/echo around it: realistic, but less "wide" than the synths.
- Licences: the Fairlight choir, the dark hall IR and the 808/cymbal packs are fine for private listening but need a
  check before publishing; the tenor sax (MTG / kinwie) needs the CC-BY credit printed in `out/credits.txt`.
