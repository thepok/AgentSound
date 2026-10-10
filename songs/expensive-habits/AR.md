# Expensive Habits - A&R, round 2 (roles/a-and-r.md)

Judged from the round-2 build (`.tmp_s/build11.log`, 17:13; `out/report.json`, `out/song.render.json`, the images),
`song.py` (diff `cf22eca~1..HEAD`), `python -m agentsound mix` (0 findings) and `master --check` (all ok). The vocal
was also measured on its own stem (`out/wetness/stems/vocal.wav`, written by the producer's round-2 wetness run; its
render JSON has the same vocal track as the final build - only the bridge's pad / choir trim came later). The band
stems there are muted, so band levels are the report's per-bar / per-section RMS. No reference track (compare
skipped). The A&R cannot hear: every statement is a number, an image or a line of `song.py`.

```
verdict: ship
summary: Still a real 80s synth-pop song - a cool, dry, half-spoken voice inside a sequenced octave bass, machine
  drums, orchestra hits and a key change - and it now ends at home on D minor and breathes after "sky" and "Sunday".
  What is left is polish: the verse line ends fade far under the band, the last chord is switched off rather than
  rung out, the four choruses are still equally loud and their top is still dull.
issues (most severe first):
1. [minor] NEW (the merge): the mic pull-back takes the verse line ends well under the band. 16 pulls on the lead
   (build log: -4.3..-5.7 dB, every held line end in verses / pres / bridge / outro). On the stem the held words fall
   from onset to end by: "four" -4.2, "more" -5.2, "wrong" -7.1, "belong" -7.6, "know" -7.6 dB (pull + taper); the
   last half second of "wrong" / "belong" sits at -29..-36 dBFS against a band at -20 dB RMS in those bars (10-16 dB
   under; the voice starts those words only ~3 dB under the band). Verse 2's rhyme stops come after the fade:
   /t/ of "flat" -32, "cat" -35, /d/ of "bed" -33 dBFS (20 ms frames) against a band at -18..-19 - 14-17 dB under it.
   The library's diction check passes (no `coda_short` / `coda_buried`: it compares the coda with its own vowel, not
   with the band) and the pull keeps 25 % on the coda only, so this is not a proven loss - but it is exactly where
   "out verliert sein t" would be said again, and a slow fade on every line end is a ballad singer's gesture, not the
   deadpan this brief asks for (the producer switched the other jazz phrasing off for that reason). Word onsets and
   the voice's share of the presence band (40 %, was 39 %) are unharmed.
   owner: sound-designer   fix: `mic_pull=2.5` (or `False`) in VERSE_VOICE, or keep it only on the two outro tags;
   then re-read the line ends of verse 2 on the stem (the /t/ of "flat" / "cat" no more than ~10 dB under the band).
2. [minor] the ending resolves but is switched off, not rung out. Fixed in the render: bar 116 is D minor (pad D3 A3
   D4 F4, bass D2 whole note, orchestra hit D4 + D5, kick + snare + crash on the downbeat, the riff E5 F5 A5 -> D6;
   song.render.json outro beats 28-32; bar 115 is a break - no bass, a snare fill). But the D6 only arrives on beat 3
   and everything is released together on the bar line: the mix holds -11 dBFS RMS to 3:55.9, is at -25 dB 100 ms
   later, -36 at 0.3 s, -52 at 1 s (report tails: `decaySec 0.0`, tail -27 dB; spectrogram_14_outro.png: bar 116 is
   one flat block to the edge, the bass at -19 dB as loud as in a chorus). A cold stop on the tonic is a legitimate
   80s ending, so not a cut-off - but the last note gets one second and the 5 s tail is nearly empty.
   owner: arranger   fix: let it ring - D6 on the downbeat (or one more bar: `tempo.fermata` / a 2-bar hold), the
   riff's pedal down for the last chord, the bass note shorter or fading (vel 96 -> ~80, a release), pad release long.
3. [minor] the pres are fixed, the choruses still do not grow: pre1 -11.2 -> chorus1 -9.7 (+1.5 LU, was +0.7), pre2
   -11.0 -> chorus2 -9.7 (+1.3, was +0.8) - good. But chorus1-4 are -9.7 / -9.7 / -9.4 / -9.4 LUFS (0.3 LU from
   first to last, was 0.4), lift -9.9 -> chorus3 only +0.5, LRA 4.1 LU unchanged on the floor of the brief's 4-8, and
   the integrated level is -10.9 LUFS - 0.1 LU inside the pop window (-11..-8; the brief aims at ~-10). The limiter
   drive (+2.8 dB) was not touched; the key change, Hanami and the marimba carry the climax, the level does not
   (loudness.png).
   owner: mastering-engineer   fix: chorus1 / chorus2 a step down in `s.arc` (0.0 / 0.5 -> -0.6 / -0.2) and
   +0.3..0.5 dB overall drive, or 0.5 dB less drive with the arc's chorus3 / 4 at +1.5 / +1.8; watch the -11 floor.
4. [minor] the dull top was not fixed in the render: hats -14 -> -12 moved air (12-20 kHz) vs the pop profile from
   -3.1 / -3.6 / -3.9 / -2.9 to -2.9 / -3.4 / -3.7 / -2.7 dB in chorus 1-4 and from -2.3 to -2.2 dB over the song
   (bands.png) - 0.2 dB. The verses are fine (0.0 / -1.8); it is the full choruses that close up.
   owner: mix-engineer   fix: a +1.5..2 dB shelf at 12 kHz on the kit or on the master in the choruses (or the
   crash / open hat / tambourine up 3 dB there); hats alone do not reach it.
5. [minor] narrow sections kept on purpose (verse1 30.1 %, bridge 30.0 % above 150 Hz, pre1 34.5 %; pre2 now 35.9 %
   = ok; stereo.png: 3 of 14 `narrow`, was 4). The dry centred verse against the wide chorus is an acceptable
   reading of the idiom and the choruses clear the target (35.4-37.9 %), so accepted - but the part of the note that
   was not about the idiom is still open: the pad alone reads phasey (correlation -0.05, width 111 %, red in the
   stereo field), strings 0.00 / 100 %. Mono sum 0.7 dB quieter: harmless.
   owner: sound-designer   fix: pad width 1.25 -> ~1.1 (correlation back above 0); nothing else.
6. [minor] the low end where the voice is softest: bass -1 dB in the pres took their sub from +2.6 / +2.2 to +2.1 /
   +1.8 dB vs the profile and puts the bass 0.6 dB under the voice (mix: low -0.6, was over it) - fixed enough. The
   bridge went the other way: with pad and choir 1.5 dB down its sub is +3.2 dB (was +2.7) and the bass (-20.8 dB
   RMS) sits 2 dB over the voice (-22.8) under the intimate aside; band sum 4-5 dB over the voice in bars 85-88.
   The two `masking` warnings (kick / octave bass, up to 48 % / 74 % of the sub) stay: idiomatic, song total sub
   -0.2 dB.
   owner: mix-engineer   fix: bass in the bridge -1.0 -> -2.5 dB (bars 87-88 at least).
7. [minor] the markup is uneven: `*time*` works (+2.7 / +2.7 / +3.7 dB over the chorus's median word, `*run-*`
   +3.6 in chorus 4: the loudest 400 ms of every chorus, -17.6..-16.3 dBFS, still at or under the band sum of
   -16..-17.6 - leaned, not shouted), `*dance*` +1.9 dB; `*cheap*` does nothing measurable (-0.6 / -0.2 / -0.6 /
   0.0 dB vs the median word) and its /p/ is unreleased into "view" (a 100 ms hole, no burst - round 1's weakest coda
   too). The breath after "Sunday" was paid for in the aside: bar 87 now carries 6 syllables in 3.5 beats (3.4 / s,
   "switched off and the" as four straight 8ths; the bridge was 3.0 / s) - the near-spoken line is the densest of the
   bridge. Verse 1's talky first bar (8 syllables, 3.9 / s) kept on purpose: accepted.
   owner: lyricist / arranger   fix: move the lean from `*cheap*` to `*sky*` or drop it; aside: "the phone turned
   off, the radio low" (one syllable less, "off" back on a quarter).
8. [minor] notes: ARRANGEMENT.md line 40 says "the drummer's choke ending" (song.py: `ending='hit'`, the kit has no
   choked crash); MASTER.md round 2 quotes the bridge at -12.2 LUFS (the build: -12.4, measured before the bed trim).
   2 masked clicks remain in the bass stem (0:59.240, 1:12.463; 0 in the mix). Round 1's three note errors are fixed.
   owner: producer   fix: correct the notes; nothing to render.
checklist:
  [x] A song, not a loop - 14 sections, sung title x4 + the outro tag x2, riff x4 growing (vel 84 -> 98 + brass -> 102
      -> 104 -> outro +2 with its own last answer RIFF_END), verse 2 new melody + e-piano + marimba, Hanami from
      chorus 2, +2 key change, the turned last line; riser / impact / downlifter / the one-beat breath; a break bar
      and a tonic ending (issue 2 is its polish).
  [x] No beepy lead - the melody is the voice; the riff is `layered/piano_glass_lead` octave-doubled with brass an
      octave under it (intro lowmid +5.1 dB vs profile).
  [x] Vocal CALM / cool, not "aufgeregt" - back_phrase / ornament / messa_di_voce off in both voices (build: no such
      moves on 'vocal'); per take 1-5 scoops, 1-7 vibratos, 0 falls / doits; emphasis = 2 lane moves per chorus (3 in
      the last), the leaned word 2.7-3.7 dB over the median word and never over the band; voice level spread per
      section (400 ms, p10-p90) 5.0-10.1 dB (the wide ones are the verses / outro with their faded line ends). SOUND.md's 75 % soft / 1.5 % power mode (was 78 % / 0.6 %) not re-measured
      here.
  [x] Vocal LAID BACK, not "gerusht" - every line its own breath now: chorus 25 notes in 4 phrases (was 3), 0.5 s of
      silence after "sky" in all four choruses (stem -45..-52 dB for two 8ths), bridge 34 notes in 4 phrases, 0.5 s
      after "Sunday" (-44 / -48 dB); verse lines 2-2.5 bars + 1.25-2 bars of rest; late_ms 24 / 18. Issue 7's bar.
  [x] Vocal DRY - sends unchanged: `vocal_plate` -21 dB, echo -60 dB with 11 throws to -15; on the stems the returns
      sit 15.7 dB RMS under the dry voice over the song (plate 16.9-19.2 dB under per section, echo 17.9-22.2 dB under
      where it throws, -59 dB in the pres; outro 14.6 dB under: the two title throws); no hall on the voice.
  [x] Vocal IN the band - mix: rhythm -1.7..-3.7, low -0.4..-3.2, bed -4.0..-6.0 dB vs the voice, 0 findings; per bar
      the band sum is 3-6 dB over the voice in verses, choruses and bridge. The `vocals` warnings (voice 2.0-2.7 dB
      section-RMS under the bass in verses / pres / bridge, 4.8 in the outro; 40 % of the presence band, kit 29 %)
      are the price of that and right for the idiom - do not turn him up. But see issue 1: the line ENDS go too far.
  [x] Diction - no `coda_short` / `coda_buried` in build11.log; 143 word-final consonants over 10 takes, the shortest
      35 ms (/r/ "your", "we're"; /l/ "I'll"), /v/ "of" / "expensive" 46-58 ms; lyrics.txt in the song folder and in
      out/ (identical). Issue 1 is the caveat.
  [x] Real dynamics - flat_dynamics 0: riff 6.4 dB, brass 7.1, keys 3.8 (2 of 6 phrases flat, not flagged), orch
      3.7, vocal automated (18.5 dB over audio onsets).
  [x] Produced, not "Gameboy" - 224XL hall + plate, gated snare bus, echo; space `lush` (reverb -11.6 LU, width
      > 150 Hz 44 %); balance vs pop within +-1 dB from sub to brilliance (air -2.2: issue 4); lows correlation 0.99.
  [x] No grit on the voice - `hero(..., drive=False)`; chain tone -> comp -> presence -> de-ess -> air.
  [x] 0 clicks in the mix (2 masked in the bass stem), 0 clipped samples, true peak -1.12 dBTP, silent notes 0 on all
      15 tracks; the merge broke none of it.
  [x] Feels like classic synth-pop - unchanged: octave bass in 8ths, machine kit + Linn claps + gated snare, Juno pad
      + string machine, orchestra hits, DX marimba 16ths, Fairlight choir + Hanami's ahs, half-time bridge -> hit
      build -> one-beat breath -> +2; C minor verse into an Eb major chorus.
  [x] Lyrics - circled with images, two deliberate direct lines; "we smile / pose for the cameras then we do what
      we're told" now parses (sung twice); nothing recognisable from an existing song.
  [x] The brief's targets - 4:00.3 with the tail (3:56 of music), 118 BPM, the form as briefed, -10.9 LUFS-I (window
      -11..-8: inside by 0.1), LRA 4.1 (4-8: on the floor), TP <= -1; cover readable (title, "AgentSound - Night
      Economy"); credits list TIGER / Hanami as non-commercial.
  [-] Piano / jazz / hero-horn items: not applicable.
keep: the verses as sung (low, centred, soft mode, two bars of talk and two of rest) and the voice's level and
  dryness - do not raise it for the `vocals` warnings; the jazz phrasing OFF; the breaths after "sky" and "Sunday";
  `*time*` / `*running*` leaned and the bridge's aside at line level (-22.8 vs -22.4 dB); the D minor landing with
  the break bar before it; the pres 1.3-1.5 LU under their choruses; "then we do what we're told"; the title on the
  pickup leap, alone in the one-beat breath before the key change; the riff on the glass piano with the brass under.
```

Round 1 recap (ship, 8 minors): fixed in the render - 1 the ending lands on D minor (now: rings too briefly, issue
2), 3a / 3b the breaths after "sky" and "Sunday", 7 "then we do what we're told", 8 the three note errors, 2 / 6 the
pres under the choruses and the bass out of the voice's way there. Not fixed although attempted - 5 the air (hats +2
dB = 0.2 dB). Half fixed - 2 the chorus-to-chorus growth and LRA (untouched). Kept on purpose and accepted - 3c verse
1's first bar, 4 the narrow verses (the phasey pad is still open), 6 the kick / bass overlap. New since the merge -
the mic pull on every verse line end (issue 1), the uneven markup (issue 7).

Hand-over line for BRIEF.md's log (the producer adds it): `a-and-r round 2: AR.md - ship; 8 minors (the mic pull
fades the verse line ends 10-16 dB under the band, the last chord is switched off after one bar, choruses still
equally loud / LRA 4.1 / -10.9 LUFS on the window's edge, air still -3 dB in the choruses, the phasey pad, the
bridge's bass over the aside, *cheap* does nothing, two stale notes).`

Publishing: private listening only - TIGER (CC BY-NC-ND + Commons Clause) and Hanami's vocoder (CC BY-NC-SA) are
non-commercial, SampleRadar forbids redistribution, the Fairlight / LinnDrum / 224XL sources are unclear.
