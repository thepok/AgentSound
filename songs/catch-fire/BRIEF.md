# Catch Fire - brief

## The wish

> "mache nun einen Song im Stile der Imagine Dragons"

An ORIGINAL arena pop-rock anthem in the spirit of Imagine Dragons (the Radioactive / Believer / Thunder / Demons
era) with SUNG vocals. No melody, lyric, riff or hook taken from any of their songs (or anyone's): only the idiom.

## The idiom we take (and how)

| idiom | here |
|---|---|
| huge stomp-and-clap percussion, taiko-like floor hits | a taiko ensemble track (MuseScore General taikos) + the Big Rusty kit's floor tom + Gimme-a-Hand hand claps on their own tracks; the intro and verse 1 are stomp + clap only |
| half-time chorus drop with a massive kick / sub | `drummer.arrange` style `halftime` in the choruses (snare + clap on 3), a sine sub under the chorus kicks, taikos on 1 and the & of 2 |
| sparse verses | verse 1: stomp + clap, sub bass, a filtered synth pulse, the palm-muted riff only in its second half |
| pre-chorus tension | `drummer` builds, the riff at pre energy (power chords), rising vocal line, riser + reverse swell, a one-beat BREATH before every drop (`s.transitions(...).into(chorus, breath=1)`) |
| explosive chantable chorus | the hook "Strike me down, I catch fire" peaking on A4; lead + two sung doubles + a sung harmony a third below; gang "hey!" shouts |
| gang vocals / chants | an original "whoa-oh" chant (post-chorus and intro): TIGER x3 takes (centre, L, R) + a TIGER harmony + Hanami an octave up mixed low; the NBO choir "oh" as a low pad under the choruses |
| a little electronic edge | a filtered synth pulse (cutoff automation), riser / impact / downlifter hits, the bass rig's growl |
| bridge strips down then rebuilds | bridge: piano + choir pad + voice only, then the pre melody returns over a tom build with the whole gang |
| final double chorus | 16 bars, the last line turns "I'll" into "we'll" |
| quiet-loud contrast is the point | verses 4-6 LU under the choruses, the bridge the quietest moment after the intro |

## Frame

- Genre: arena pop-rock. Analysis profile first `pop`, changed to **`rock`** in the mix (see MIX.md: the guitar wall
  read muddy / honky only against the pop reference); the band and the vocal hero use the rock settings.
- Tempo **124 BPM**, **D minor**, 4/4, straight 8ths; the choruses and post-choruses feel half-time (62).
- Form (110 bars, 3:33):
  `intro 8 | verse1 16 | pre1 8 | chorus1 8 | post1 4 | verse2 8 | pre2 8 | chorus2 8 | post2 4 | bridge 8 |
   build 8 | final 16 | post3 4 | end 2`
- Energy arc: intro 2-3 -> verse1 2 -> pre 3-4 -> chorus 5 -> post 4.5 -> verse2 2.5 -> pre 4 -> chorus 5 ->
  post 4.5 -> bridge 1.5 -> build 3-5 -> final 5+ -> post 5 -> end (one hit).

## The hook

"Strike me down, I catch fire" - the vocal hook on TIGER (male pop / rock voicebank), a stomped three-syllable call
(F4 E4 D4) and a leap to a held A4 on "fire" (an open 'ai'), doubled and harmonized in every chorus, the gang shouts
around it. The post-chorus chant ("whoa-oh") is the second hook and opens the song. No synth lead at all (HUMAN_FEEDBACK:
no beepy synth hooks): the voice carries every melody.

## Vocal

- Voice: **TIGER** (`python -m agentsound voicebanks`: male pop / rock, A2-C#5, modes fresh / disco / electric).
  Licence: CC-BY-NC-ND-4.0 + Commons Clause - **non-commercial, private listening only** (keep the credits warning).
  Hanami (Lotte V, vocoder CC-BY-NC-SA) only as the high gang layer, mixed low.
- Range used: verses C3-C4 (low, close), pre A3-D4, chorus D4-A4 (the peak), bridge A3-F4.
- Style `rock` (outgoing: scoops, vibrato on held peaks, falls), the chorus leaning on the power mode; the dry vocal
  chain (`hero(..., family='vocal', genre='rock')`, plate ~15 LU under, echo throws only on section ends).
  Grit: `'light'` is allowed by the user for rock - judged by ear-numbers in SOUND.md, off unless it helps.
- Theme for the lyricist: someone the world kept trying to put out (a kid from a burned-out town, written in pencil,
  pushed under) who turns every blow into fuel - the match image: being struck = catching fire. Circle it with
  concrete images (gravel, pencil, matches, a fire hose, doors nailed shut, an ember under a coat); a few direct lines
  allowed on the hook.

## References

None in the repo for this style (no downloads allowed). Judged against the `pop` profile targets and the recipes;
`compare` against Sweet Child O' Mine (chorus) only as a rock-production sanity check if needed.

## HUMAN_FEEDBACK checklist (the A&R ticks it)

- [x] A real song: form, a hook that returns and grows, variation between repeats, fills, transitions.
- [x] No beepy synth lead; the voice is the lead.
- [x] Lead in front: the vocal >= 2-3 dB over the bed in every section it sings (report `bed vs lead`).
- [x] Real dynamics: `flat_dynamics` 0 (the vocal measured from its audio onsets; every played part through a player).
- [x] Played, not keyboard-like: drummer / bassist / guitarist / pianist players, human timing.
- [x] Sung vocals dry and close (no wash); grit off by default.
- [x] Diction: no `coda_short` / `coda_buried`; word-final consonants audible.
- [x] Lyrics: circled theme, 2-3 quotable lines, hook on the peak, stresses on strong beats, open vowels on long/high notes.
- [x] Not "rushed": vowels on the beat, room to breathe between phrases.
- [x] Produced, not Gameboy: rooms, width, a full low end (sub on the drops).
- [x] `clicks` = 0, true peak <= -1 dBTP, no silent notes.

## Targets

- `pop` profile: -11..-8 LUFS (aim ~ -9), true peak <= -1 dBTP, PLR >= 6, LRA 4-8 (verse 3-5 LU under the chorus),
  width above 150 Hz 40-70 %.
- Mix profile `rock` for the balance (rhythm -3.5..0 dB vs the lead in the hooks, bed -10..-4).
- Master: platform `auto`.

## Credits to carry

TIGER (non-commercial), Hanami (Lotte V, vocoder NC), the band preset's packs (Big Rusty CC0, FSBS CC0, Emily CC0,
Growlybass CC0, Salamander CC-BY), MuseScore General (taikos), Gimme-a-Hand (GPL, music free), NBO choir (CC-BY-SA 4.0),
the build's credits.txt has the full list.

## Log

- producer: brief written (124 BPM D minor, 116 bars, TIGER lead, the stomp/clap + half-time drop idiom).
- arranger: ARRANGEMENT.md; drummer / bassist / guitarist (riff + double) / taiko + clap plans / pianist pedal; the
  doubles' takes made explicit (singer.double gave L and R the same take when the tracks already existed).
- lyricist: LYRICS.md, lyrics.check clean; pre rewritten after the diction check ("soaked all the way to the marrow,
  so go on, try me").
- sound-designer: SOUND.md - gain 'crunch', taiko hp 75 / room, carve of the wall under the voice (5 dB @ 3 kHz),
  'words' eq, sub only on the drops, grit off.
- mix-engineer: MIX.md - quiet-loud arc (LRA 2.4 -> 4.8), width 18 -> 32 %, 0 report warnings; open: drums 1.8 dB
  under the rock window (deliberate), vocal presence 35 % song-wide / 38 % in the chorus span.
- mastering-engineer: MASTER.md - rock, auto: -9.9 LUFS, -1.2 dBTP, PLR 8.7, width x1.25, +1.4 dB air shelf.
- a-and-r: AR.md - round 1 `revise` (vocal on top of the band, a thin stomp, a loud intro chant), mix-engineer +
  mastering-engineer revision (hook-only drum rides, taikos up, vocal -0.5, drive +3.7), round 2 `ship`.
- producer: delivered - out/mix.mp3, out/lyrics.txt, cover (subtitle 'ARENA': the artist line ran under the disc).
