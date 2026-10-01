# Down on Jane Street - arrangement

## Frame

126 BPM, Bb major, 4/4, straight 8ths (the bossa preset's Feel: ratio 0.5, piano +8 ms, bass / kit on the beat;
the voice ~10 ms behind). 102 bars + a fermata, ~3:23. (The first draft was an instrumental in F major with a bass
solo; the user asked for a sung version - Bb puts the tune in Hanami's best range, A3-G5.)

## Changes (32-bar ABAC, one chord per bar unless split)

| part | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| A1 | Bbmaj9 | Eb9#11 | Cm9 | F13 | Dm7 | G7b9 | Cm9 F7b9 | Fm9 Bb13 |
| B | Ebmaj9 | Ab9#11 | Dm7 | G7b9 | Cm9 | Ebm6 | Dm7 G7#9 | Cm9 F7b9 |
| A2 | Bbmaj9 | Eb9#11 | Cm9 | F13 | Dm7 | G7b9 | Cm9 F7b9 | Dm7b5 G7b9 |
| C | Cm9 | Ebm6 | Dm7 | Dbdim7 | Cm9 | F7alt | Bbmaj9 Gm9 | Cm9 F13 |
| intro | Cm9 | F13 | Cm9 | F13 | Dm7 | G13 | Cm9 | F7b9 |
| tag | Dm7 G7b9 | Cm9 F13 | Ebm6 Ab9 | Cm9 B7#11 | | | | |
| end | Bbmaj9 (2 bars + fermata) | | | | | | | |

Tension / release: the held A of "rain" turns from maj7 (Bbmaj9) into #11 (Eb9#11); the B moves to the IV and its
lydian-dominant neighbour, the minor iv (Ebm6) is the bittersweet turn under "the waiter wipes the table"; the C
climbs (Cm9 Ebm6 Dm7 Dbdim7) to the top G5 over Cm9 and F7alt, then cadences. The tag ends with the tritone sub B7#11
-> Bbmaj9.

## Form

| section | bars | energy | who | what happens |
|---|---|---|---|---|
| intro (iv, ih) | 4 + 4 | 2 | bass, cross-stick, shaker; piano bossa comping; brushes from bar 5 | the groove first; bars 5-8 the hook on the piano (harmonized), an answer, a fill into the voice |
| head A1 B A2 C | 32 | 3 -> 4 | voice + trio; bossa in A / B / A, a straight "push" four in the C | the sung tune; the piano comps the bossa cells all through (rootless, under the voice) and answers in the voice's rests (voiced 3rds / 6ths) |
| piano_solo A1 B A2 C | 32 | 3 -> 5 | trio: bossa in A1 / B, push in A2, drive + ride in C | soloist arc in 4-bar phrases (statement -> answer -> develop -> burst -> climax -> resolve) with the hook as motif, the piano vocabulary; the trill saved for the climax (C) |
| head_out B A2 C | 24 | 4 -> 5 | voice + trio | sung freer (the lines paraphrased: anticipated / laid back), denser comping; a soft third below the voice on the climax line; the last line turned ("now you can keep the wait") |
| tag | 4 | 3 -> 2 | voice + trio, bossa, ritardando from bar 3 | the hook line twice, the piano's tritone fill |
| end | 2 | 1 | the voice's last "rain" (let go first), rolled Bbmaj9 (6/9), bass Bb1, last stirs | `s.ending`: rolled, fermata, the room opens |

The conductor's arc (`s.arc`) shapes the sections against each other: the first A soft, each part a little more, the
C's lift; the solo from its statement to the climax; the out chorus warmest in its C; tag and end soft.

## The hook

Voice: `r/4 F4/8 G4 D5/4. C5/8 | A4/2. r/4` - "Down on Jane Street, rain": a pickup leaping a sixth to a held D on
"JANE", sighing to C, the A of "rain" held over Bbmaj9 -> Eb9#11. It opens every A (head, out chorus), returns a
fourth higher at the C's top (G5 on "JANE" - the song's highest note), ends the tag and the song. The piano states it
in the intro and it is the motif of the piano solo (stated, fragmented, varied, sequenced, lifted).

## Transitions

- intro -> head: a pianist fill (section_end) in the last bar + a brush swell; the voice enters on the pickup.
- head C -> solo: the voice holds "wait" to the bar line; the solo's statement starts with the hook on the piano.
- solo A1/B bossa -> A2 push -> C drive + ride (climax), a soft crash on the C; brush swell into the out chorus.
- out chorus C -> tag: bossa again, ritardando from the tag's bar 3 into the rolled last chord.

## Players

- One `pianist.Memory()` for the whole song (the ornament budget song-wide), one `singer.Memory()` for the voice.
- Voice: `singer.sing(..., voice='hanami', style='ballad', late_ms=10, soft=0.75, power=0.35, fall=0.12, fewer
  scoops)`; the out chorus through `jazz.paraphrase(..., embellish=0)` (same notes, freer rhythm); one harmony line.
- Piano under the voice: `jazz.comp(style='bossa', voicing='rootless', register=('A2', 'E4'))` per part (continuous;
  the A&R found the `answer=` comping dropping out under every sung note); its answers in the voice's rests via
  `jazz.chorus` (pianist.arrange, style straight, voiced: thirds / sixths / guide / drop 2, no fills of its own).
- Piano solo: `soloist.solo(s, b.piano, pianist.vocabulary('straight', lh_track=b.piano, memory=mem,
  phrase_bars=4), at=solo, prog=solo.prog, motif=HOOK, budget=soloist.Budget(...).save(climax))`,
  `b.piano.feature(solo)`.
- Bass: bossa root-fifth (`prog.bass(pattern='R__f')` + `jazz.bass_touch`) in the bossa parts,
  `walking_bass(straight=True, feel='push' | 'drive')` in the four parts.
- Kit: `jazzband.bossa_groove` per block, `brushes(straight=True)` through `jazz.chorus` in the four parts,
  `jazz.brush_fill('swell')`, `jazz.last_stir` at the end.

## Needs from sound design

- Voice: clean, close, a little room (no echo throws, a low plate); the piano dipped where the words live.
- Piano: the warm Salamander, both hands on one track; melody / solo C4-D6, comping A2-E4 under the voice.
- Bass: Meatbass pizz Bb1-D3, velocity = level. Kit: brushes, cross-stick, shaker - all soft.
