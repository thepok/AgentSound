# Die Fähre um sieben - brief

## The wish

An ORIGINAL song in the manner of early-1970s German Liedermacher folk-pop: a young woman (think of the feel of the
early Juliane Werding records, ~1972-74) telling a story to her own acoustic guitar. Intimate, guitar-centred, sparse,
warm, a little melancholic, close-miked. No melody, lyric, chord sequence or title taken from her songs; her voice is
NOT imitated or cloned (the vocal is the licensed generic voicebank Hanami).

## The idiom we take (and how)

| idiom | here |
|---|---|
| the guitar carries the record | `sampled/acoustic_guitar` with the guitarist's hands (HUMAN_FEEDBACK 2026-10-11: the acoustic demos "sounded nice"): Travis picking in the verses, songwriter strum with recorded chucks in the choruses, arpeggios in the bridge, chord-change fret noises, an intro and an instrumental break |
| storytelling in verses, a sung refrain | 2 verses (the man who never boards the ferry), a chorus with a proverb-like hook, a bridge that turns the story (she leaves) |
| minor verse, major chorus | A minor verses (descending bass line), C major chorus (F G C Am7) |
| sparse era arrangement | the upright bass from verse 2, brushes and a string pad only in the last chorus / tag, a plate reverb + a small room |
| close, unhurried voice | sung low and calm (A3-B4, C5 once), `style='ballad'`, the mic pull on held ends, a near-whispered last line |

## Frame

- Profile `jazz` (an acoustic small-room record, -16..-13 LUFS, dynamics first).
- 84 BPM, A minor / C major, 4/4, 3:14 with a ritardando into the last chord.
- Form: intro 4 | verse1 8 | chorus1 8 | verse2 8 | chorus2 8 | break 8 | bridge 8 | chorus3 8 | tag 4 | outro 2.

## Log

- German singing did not exist (the lyrics pipeline was English / ARPAbet only): added German by hand phonemes in
  Hanami's German symbols (`lyrics.spell` + a per-song `LEX`, docs/COMPOSE_API.md "German").
- Intelligibility proxy (a German Windows SAPI recognizer): spoken-style renders 4/4 correct in a closed choice of 10
  sentences, the sung stem 2/12 lines in a closed choice of 24 (dictation hears fragments: "Fahrschein Tag" etc.); the
  SAPI engine is poor on any singing, so it decides nothing - kept the vocal, sung low and calm, words on short notes.
- Bass: hollow_bass read flat (the layers level the velocities) -> sampled/upright_bass with a 4-bar velocity arc.
- Narrow mix (2-11 % width) -> guitar double, pans, dimension / width fx, room sends, master width: 17 % >150 Hz.
- Masking voice vs guitar -> the intro rhythm guitar only in bars 3-4, guitar rides / eq, a vocal-keyed carve 220 Hz.
