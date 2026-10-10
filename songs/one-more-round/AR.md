# One More Round - A&R

## Round 1 (the first full build after the mix pass)

```
verdict: revise
summary: A real club song with a sung hook that turns into its own chops - but the drops ran out of hook halfway
         and the builds were as loud as the drops they lead into.
issues (most severe first):
1. [major] the drops had 4 bars of hook in 16 (tracks.png: chops bars 41-44, then nothing until the piano at 49; the
   sung chorus in drop 2 only bars 81-84): a loop with gaps, not a drop.      owner: arranger
   fix: a second (climbing) chops statement, the lower chops answering the piano, the chorus sung twice.
2. [major] the builds peaked over the drops (build -8.3 vs drop -8.9 LUFS, short-term max -6.8 vs -8.4): the drop
   cannot hit after a louder build.                    owner: mix / mastering   fix: riser down, the roll's
   velocities 30-100, the limiter lane in the builds -8 -> -4.5.
3. [major] the drop-2 vocal sat over the kick and bass (mixer: bass -11.4 dB, drums -6.6 dB vs the lead) -
   HUMAN_FEEDBACK 2026-10-02 "die Stimme im Vergleich zum Rest zu laut".       owner: mix-engineer
4. [minor] the talk box had no played dynamics (flat_dynamics 0.0 dB per phrase).   owner: sound designer
keep: the hook idea (sung -> chopped -> doubled by the piano), the hard-tuned dry vocal, the prism in breakdown 2,
      the talk-box answer after drop 1, the breath + impact into each drop, 0 clicks.
```

## Round 2 (final build)

Revision: drops filled (chops x2 per half, DROP_HOOK_B climbing to C6, chorus x2), builds: riser -5, roll
velocities 30-100/104, limiter lane -8 -> -4.5; drop 2: bass +7, drums +1, vocal +0.5; the talk box's accent lane
(6.5 dB per phrase). Evidence: build summary (3:17, -9.9 LUFS-I, TP -1.18 dBTP, LRA 5.2, 0 warnings, 6 info, clicks 0,
silent notes 0), overview.png / tracks.png / spectrogram_05_drop.png / spectrogram_06_talkbox.png, `mix` + `master
--check`.

```
verdict: ship
summary: The hook is everywhere it should be - sung in the builds, chopped and pitched up in the drops, doubled by
         a bright piano - over a pumping, clean club low end; a real arc from a filtered intro to the sung drop 2.
issues:
1. [minor] the end of each build still reads louder in 3-s loudness than the drop (short-term max -7.6 vs -8.4
   LUFS): riser + roll + the hook's Eb5. The drops are louder integrated (-8.8 vs -9.3) and hit after the breath with the impact and the full low end; genre-typical.
2. [minor] singer.check 'vocal_buried' in drop 2 (vocal -22.0 vs bass -16.8 dB RMS): an unweighted-RMS reading of the
   sub; the K-weighted mixer and HUMAN_FEEDBACK want the voice IN the band, the words own the presence band. TODO.
3. [minor] low_end_wide (mixer) in the breakdowns, where nothing plays below 150 Hz but reverb residue. TODO.
4. [minor] -9.9 LUFS-I sits at the bottom of the window; the drops are -8.8 / -8.9 (limiter saturation, TODO).
checklist: song not loop [x] (8/16-bar form, two different drops, breakdowns, talk-box interlude) | no beepy lead
[x] (voice, chops, sampled piano; supersaw only as chords) | lead in front [x] (bed -15.4 dB vs lead) | dynamics [x]
(flat_dynamics 0: chords 5.2, piano 3.1, chops 4.4, talk box 6.5, vocal 15.6 dB) | played [x] (pianist.arrange,
drums machine-tight by genre) | hero / epic [x] | produced [x] (lush: width 41 %, reverb -16 LU) | clicks 0, TP <=
-1 [x] | brief targets [x] (3:17, 124 BPM, hard-tuned Hanami hook + chops + prism, talk box 8 bars)
```
