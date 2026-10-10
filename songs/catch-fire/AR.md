# Catch Fire - A&R

## Round 1 (build 16, commit e7ce4a5)

```
verdict: revise
summary: A real anthem with a hook that returns and grows, but the singer stands in front of the band instead of in
         it - the stomp that should shake the room is small, and the song opens on a loud choir over a thin drum.
issues (most severe first):
1. [major] the vocal sits ON the band in the hooks: rhythm -5.2 / -4.6 / -5.0 dB vs the lead in chorus1-3 (rock
   window -3.5..0, mixer `drums_too_quiet`); tracks.png: vocal -18, drums -21, each guitar -24. HUMAN_FEEDBACK
   2026-10-02 "die Stimme im Vergleich zum Rest zu laut" - a sung lead sits IN the band, err quieter. An arena
   chorus is carried by the kit.            owner: mix-engineer   fix: vocal -0.5 dB, drums / claps up in the hooks
2. [major] the intro is not a stomp: the gang chant leads by 6.6 dB over the rhythm and 9.8 dB over the lows
   (taiko -32 dBFS RMS vs gang -18), and at -9.4 LUFS it is as loud as a pre-chorus (brief: energy 2-3).
                                            owner: mix-engineer   fix: taikos up, the intro gang down
3. [minor] verse 1's stomp is thin (taiko -37 dBFS under a vocal at -23).   owner: mix-engineer   fix: taiko +3
4. [minor] cover: the artist line "AGENTSOUND" runs under the disc (last letters hidden).   owner: producer
5. [minor] flat_dynamics INFO on gtr_l / gtr_r (2.2 / 1.8 dB per phrase): a driven amp flattens the pick dynamics;
   the lead's `flat_dynamics` is 0 (vocal 20.9 dB). Known system finding (TODO), not fixable in the song.
keep: the form and the quiet-loud arc (verse 4 LU under the chorus, bridge the floor), the breath before every
      drop, the dry vocal (plate -15.7 LU, echo only as throws, tails -22 dB), the punchy lead (fewer scoops),
      the doubled / harmonized hook, 0 clicks.
```

## Round 2 (after the revision: build 21)

Revision: MIX trim vocal -0.5 -> -1.0, claps 2.5 -> 3.5; drum ride +1.5 in the choruses / +1.0 in the posts, -1.0
in the build (the vocal fell under the toms there: vocal ride build 1.0 -> 1.75); taikos intro +4, verse1 +3,
posts +2; the gang -2.5 dB (its layers -2) in the intro; master drive +2.8 -> +3.7; cover subtitle 'ARENA'.
(A first try with drums +1.5 everywhere put the vocal under the drums in both verses: reverted to hook-only rides.)

```
verdict: ship
summary: The chorus now lands like a band hit with a voice in the middle of it, not a singer over a backing track;
         the stomp opens the song and the chant sits on top of it.
issues:
1. [minor] vocal presence share 33 % song-wide (singer.check wants 40 %): measured over the whole song including
   intro / posts / end where the lead is silent, and against a guitar wall + crash wash that belongs to the genre.
   The words are carried by the carve (5 dB @ 3 kHz), the 'words' eq and the diction (no coda_short / coda_buried).
   If the user cannot follow the words: vocal ride +0.5 in the choruses first.
2. [minor] flat_dynamics INFO on the rhythm guitars (see round 1, system finding).
3. [minor] brilliance -3.2 / air -2.8 dB vs the rock reference: a slightly dark master; kept (TIGER's sibilants and
   the crash wash get harsh above that).
evidence: mix: "moves: none - the balance is inside the targets" (hooks: rhythm -3.6 / -3.0 / -3.2, low -3.3 /
  -2.9 / -3.0, bed -8.7 / -8.5 / -8.4; intro rhythm -3.8, low -6.1); master --check all ok (-9.9 LUFS-I, -1.20 dBTP,
  LRA 4.2, PLR 8.7, corr 0.63); report: 0 errors, 0 warnings, 6 info, clicks 0, silent notes 0; loudness.png:
  intro -10.1 -> verse1 -12.7 -> pre -10.0 -> chorus -8.8 -> verse2 -11.9 -> bridge -12.6 -> build -9.6 -> final -8.9.
vocal: dry (vocal plate -15.7 LU under the voice, no constant echo, phrase tails -22 dB); in the band (see above);
  not rushed (verses: one sung bar, one bar of air; chorus lines end on held notes with half a bar of rest; a
  one-beat breath before every drop; 50 % scooped onsets cut to the punchy setting); diction passes (shortest
  codas 35-58 ms, none flagged).
arena anthem? yes: stomp + clap + chant intro, sparse verse, climbing pre with riser and breath, half-time drop
  with sub, a three-syllable shoutable hook with gang "hey!" answers, a whoa-oh post-chorus, a stripped bridge, a
  tom build and a double final chorus that turns "I'll" into "we'll".
checklist: [x] a song, not a loop  [x] no beepy lead  [x] lead in front but in the band  [x] real dynamics (lead
  flat_dynamics 0)  [x] played (drummer / bassist / guitarist / pianist)  [x] vocal dry and close, grit off
  [x] diction  [x] lyrics (circled theme, hook on the peak)  [x] not rushed  [x] produced (rooms, width 34 %, sub on
  the drops)  [x] clicks 0, TP -1.2 dBTP, no silent notes  [x] the brief's targets (form, 3:37, LRA 4.2)
keep: everything above.
```
