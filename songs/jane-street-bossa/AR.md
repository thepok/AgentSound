# Down on Jane Street - A&R (round 2)

Judged build: `out/mix.mp3` / `mix.wav` / `report.json` of 2026-10-01 19:54 (commit eb671bf; `check` recompiles to a
byte-identical `song.render.json`, so the render is current), `mix` and `master --check --platform dynamic` re-run on
it, `check` (compile only: no diction / coda warnings), the pianist / soloist summaries read from `build()`, zooms at
3:14.95 and 3:15.5. No jazz reference available: `compare` skipped. Round 1 (revise) is in the BRIEF log.

```
verdict: ship
summary: A warm, catchy bossa-flavoured jazz song: a hook you hum after one listen, lyrics with a wink, and now a
         piano that keeps the groove going under her and answers her lines. The solo builds to a real peak and the
         out chorus sounds freer than the first time through.
```

## Round-1 issues - status

- [major] piano laid out under the voice -> **fixed**. Every head / head_out bar now has piano (`barsRmsDb` -22..-31
  dB in the sung sections, no empty bar; round 1: 15 bars at -52..-57); `tracks.png` shows a continuous piano lane.
  The answers are voiced (`thirds` / `sixths` / `guide` / `drop2` in every part, no `single` left). Sung sections are
  now `lush`: width >150 Hz 18.4 % / 19.5 % (target 15-80; round 1 9.8 / 10.1). The piano still sits 4.0-4.8 dB
  under the voice.
- out chorus a repeat -> fixed: paraphrased rhythm (anticipations / lay-backs) plus one soft harmony a third below
  on "down on Jane Street, rain" (`vocal_harm`, about 7 dB under the lead peak).
- ending stops short -> improved, see minor 1.
- boomy sub -> fixed: sub +3.0 -> +1.1 dB vs the jazz profile.
- shaker vs voice -> fixed: the masking info is gone (0 warnings, 0 info).
- solo hook x3 -> fixed: 13 four-bar phrases, the hook stated once and then answered.
- scoops -> reduced: 1-5 per part (was 2-7).
- stale docs -> fixed (ARRANGEMENT.md rewritten, docstring).

## Issues (most severe first)

1. **[minor] The final chord's ring is short.** The voice lets go cleanly at 3:14.95 (a ~60 ms release, no click).
   But by then the Bb6/9 chord, rolled 4 s earlier, has already decayed: the mix steps down about 12 dB there, and
   the chord is close to silence by ~3:15.8. The report's tail is 1.4 s at -21.4 dB. Better than round 1, but the
   "room rings" moment is under a second.
   owner: arranger   fix: softly re-strike or re-roll the top of the chord (or just the 6/9 colour tones) as the
   voice releases, or end the voice a beat earlier so the fresher chord carries; keep the pedal down to the end.
2. **[minor] Boxy mids, a 63 Hz bump.** Third-octaves vs the jazz profile: 630 Hz +4.9, 800 Hz +4.1, 1 kHz +3.5 dB
   (mid +1.6 overall), and 63 Hz still +4.2 (sub +1.1 overall). The master check suggests -1.7 dB at 800 Hz.
   HUMAN_FEEDBACK says the user does not hear 1-3 dB polish, so this is not worth an A/B round.
   owner: mastering-engineer   fix: optional, -1.5 dB bell at ~700 Hz (Q 1) in the song's master eq.
3. **[minor] The solo opens low and leans on the motif.** After the sung head ends near -13 LUFS short-term, the
   solo's first ~30 s sit at -17..-19 (section -15.9 vs head -14.6). It builds to the song's peak (-11.2 at ~1:59),
   so the arc works. Still, 6 of its 13 phrases are `motif`, and the climax is one `trill` phrase (round 1 had
   octaves + trill).
   owner: arranger   fix: optional, start the solo ~1 dB hotter (arc) and make one develop phrase non-motif.
4. **[minor / watch] Vocal onset bends.** The `head_out` spectrogram still shows curved onsets on many notes; this is
   DiffSinger's own transitions plus the remaining scoops. Not judged by ear. owner: producer   fix: listen once to
   the out chorus before delivery; nothing to change unless it sounds "leiernd".

## HUMAN_FEEDBACK checklist

- [x] A song, not a loop: intro / sung ABAC / piano solo ABAC / out chorus from the B (paraphrased, one harmony) /
      tag / end. The hook opens every A, returns a fourth higher in the C and ends the song.
- [x] No beepy lead: the hook is sung (Hanami, clean vocal hero).
- [x] Lead in front: piano -4.8 / -4.0 / -3.9 dB under the voice (head / head_out / tag), bass -5.6..-6.1.
- [x] Real dynamics: `flat_dynamics` 0; voice 15.6 dB, piano 10.1 dB, bass 6.0 dB per phrase.
- [x] Played, not keyboard-like: bossa comping rolled 10-22 ms, rolled final chord, singer moves, bass touch.
- [x] Piano harmonized, never a bare line: the answers are voiced in every part, the solo goes through soloist +
      pianist vocabulary, the intro hook is drop-2 / guide. One fast figure in the song (the trill at the solo's
      climax). Warm, not hard: brilliance -3.1 / air -2.5 dB, presence 0.0.
- [x] Jazz: straight 8ths (Feel 0.5), drums -14.4..-15.3 dB under the lead per section, melody first.
- [x] Hero sound on the hook: the voice present and clean (no tube: matches "no amp grit on vocals").
- [x] Produced, not "Gameboy": `lush` in intro / head / solo / head_out / tag (width >150 Hz 18-51 %), reverb
      -12.7 LU, correlation 0.71 (the mono sum only 0.7 dB quieter).
- [x] 0 clicks, 0 clipped samples, true peak -1.20 dBTP, 0 silent notes on every track.
- [x] The brief's targets: 3:23, -15.1 LUFS-I (jazz -16..-13), LRA 5.7, PLR 13.9, platform dynamic; `mix` 0 findings,
      `master --check` all ok.
- [x] Vocals: no coda / diction warnings, lyrics circled with one direct line and quotable lines, `out/lyrics.txt`
      written. Credits: Hanami's vocoder is CC-BY-NC-SA, so private listening only.

## Keep

- The hook and the lyrics, unchanged: the sixth leap to "JANE", the A held into Eb9#11, the fourth-higher return in
  the C; "I ordered two, I drank them both", "I let the taxis pass", "so I don't mind / now you can keep the wait".
- The bossa comping under the voice, soft and below it, with voiced answers in her rests.
- The solo's arc to the song's loudest moment and the band opening from bossa into the straight four.
- The freer out chorus with its single harmony line. One harmony is enough; do not stack more.
- The balance (voice clean and in front, brushes ~15 dB back, warm piano) and the master that kept the dynamics.
