# Down on Jane Street - A&R (round 3: the calm version)

Judged build: `out/mix.mp3` / `report.json` of the calm version (fix/dry-vocals: 100 BPM - 20 % slower than 126 -,
G major, the sparse A words, sung soft + laid back, the dry vocal space), `mix` and `master --check` re-run on it,
the singer's diction ears, the phrase lengths (song seconds), overview.png. No jazz reference: `compare` skipped.
Same hat as the producer this round (the coordinator asked for a short pass) - weigh it accordingly.

```
verdict: ship
summary: A slow, calm bossa ballad now: the voice sits dry and close, lower and behind the beat, with room to
         breathe between the lines; the band still grooves under it and the piano solo still climbs to the peak.
```

## Checks of the slowdown (126 -> 100 BPM)

- Groove: the bossa kit at 100 BPM got soft 16th ghost taps between the brush 8ths (35 %, velocity 14-22: GHOSTS),
  so the swirl does not thin out; the drums sit -16.1 / -15.8 dB under the voice in the head / head_out (window
  -16..-13), the bass -6.5 / -6.6 (window -6.5..-3) - on the edges, inside. The shaker read "nearly inaudible" at the
  slower tempo (fewer shakes): +2 dB more; 0 warnings after.
- The piano solo keeps its arc: section -16.7 LUFS, its climax the song's loudest short-term moment (-11.9 LUFS).
- Timing: the lay-back is in ms (vowels ~35 ms behind, phrase starts ~50): at 100 BPM that is 6 % / 8 % of a beat
  (7 % / 10 % at 126) - still on / just behind the beat, no drag.
- Breath: the longest sung phrase grew to 8.1 s ("the candle leans your way, the waiter wipes the table" - an 8th rest
  after 'way' was too short to split the take): the B now breathes at rests >= 0.28 s (split_s), the longest phrase is
  4.5 s, the held last "rain" 5.2 s.
- Diction: no coda warning (the shortest word-final consonant 46 ms; at 126 BPM three legato codas read 35 ms).
- Dynamics: voice 17.0 dB, piano 10.1, bass 6.1 per phrase; flat_dynamics 0. 0 clicks, true peak -1.20 dBTP.

## Issues (most severe first)

1. [minor] Low end heavier in G: sub +3.8, low-mid +3.4 dB over the jazz profile (Bb: +1.1 / +2.6). The master check
   calls it a tone note (its suggestion even adds 0.7 dB at 60 Hz), HUMAN_FEEDBACK: 1-3 dB polish is not heard.
   owner: mix-engineer   fix: optional, -1.5 dB more on the bass bell (53 Hz) or a 120 Hz high-pass on the comping.
2. [minor] The tag's band sits low under the voice (rhythm -17.5, bass -7.9 vs the windows' -16 / -6.5): a soft
   tag by design, the mixer moves nothing.  owner: arranger   fix: optional, tag kit vel 0.6 -> 0.7.
3. [minor] Width x1.6 on the master (the dry voice is centred): the intro / solo read 88 / 93 % wide above 150 Hz
   ('ok', the window tops at 80). owner: mastering-engineer   fix: optional, x1.45 if the solo sounds too spread.
4. [minor, from round 2] the final chord's ring is short.

## HUMAN_FEEDBACK checklist (the new entries)

- [x] Dry, close vocal: its returns ~20 LU under the dry voice, no echo, no band room.
- [x] Calm, not "aufgeregt": sung soft (Nectar alone), few small scoops, slow narrow late vibrato, no falls, the
      line mostly stepwise and a minor third lower (4 % of the sung time at / above D5).
- [x] Not "gerusht": laid back (the syllables land on the beat), fewer words on longer notes in the A's, 20 % slower.
- [x] Everything of round 2's list still holds (song not loop, voice in front, real dynamics, warm piano, jazz drums
      behind, produced space, 0 clicks).

## Keep

The hook (now E5 on "Jane"), "Ordered two, drank them both", "let the taxis pass", "I'm not the one who's late" /
"now you can keep the wait"; the bossa comping under the voice; the solo's arc; the single harmony line.

---

# Round 2 (126 BPM, Bb)

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
