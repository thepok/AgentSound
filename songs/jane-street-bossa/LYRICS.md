# Down on Jane Street - lyrics

**Theme (never named in the song):** a woman at a sidewalk table on Jane Street (West Village) late at night, waiting
for someone who does not come - and deciding, line by line, that she is fine without him. Shown through the rain,
the empty chair, the candle, the waiter, the taxis; said plainly only once ("I'm not the one who's late") and turned
into attitude at the very end ("now you can keep the wait").

**Hook line (on the melody's hook: the leap to the held note):** "Down on Jane Street, rain" - says the title, sits
on the pickup -> high D -> held A of every A section, comes back a fourth higher at the top of the C, ends the song.

**Quotable lines (the attitude):** "Ordered two, drank them both", "let the taxis pass", "I'm not the one who's late"
/ "now you can keep the wait".

**Final version (the calm round, the user's pick):** the A sections sing the SPARSE words - fewer syllables on longer
notes (quarters instead of eighths, 21 syllables per A instead of 26: song.py FEW_A), the song 20 % slower (100 BPM)
and a minor third lower (G major). The first A words are kept at the end ("First version").

Rhyme scheme per 8-bar part: X A X A (while / smile, way / stay, glass / pass, late / wait).
Notes per line (one note per syllable, the melody in `song.py`): `lyrics.check` clean for every part.

## Head (sung once through)

**A1**

    Down on Jane Street, rain                 (5)  the hook
    taps and sings a while.                   (5)  A
    Ordered two, drank them both,             (6)  X  - quotable
    tipped the band a smile.                  (5)  A

**B**

    Your chair is full of evening,            (7)  X
    the candle leans your way,                (6)  A  (a catch breath after 'way' at 100 BPM)
    the waiter wipes the table,               (7)  X
    I tell the evening: stay.                 (6)  A  - the evening of line 1 again

**A2**

    Down on Jane Street, rain                 (5)  the hook
    writes your name on glass.                (5)  A
    Let you be, let you go,                   (6)  X
    let the taxis pass.                       (5)  A  - quotable

**C**

    Let the bass walk me home,                (6)  X
    I'm not the one who's late,               (6)  A  - the one direct line
    down on Jane Street, rain -               (5)  the hook, a fourth higher: the top note (E5 on "Jane" in G)
    so I don't mind ... the wait.             (6)  A  (a breath after 'mind')

## Piano solo (32 bars, no voice)

## Out chorus (sung from the B)

**B, A2** as above, then **C** with its last line turned:

    Let the bass walk me home,
    I'm not the one who's late,
    down on Jane Street, rain -
    now you can keep the wait.

## Tag / ending

    Down on Jane Street, rain,
    down on Jane Street ...
    rain.                                     (held over the last chord)

## Notes

- Stresses on the strong beats: "JANE" on the long high note (beat 3), "WAI-ter" on beat 2 with "WIPES" on 4 (the
  first draft had "ter" on beat 3 - `lyrics.check` caught it, the rhythm was moved), "OR-dered" / "DRANK" / "LET" on
  beat 2 held, "TWO" / "BOTH" / "BE" / "GO" on beat 4 (the first draft put "dered" on beat 3: caught and moved).
- Open vowels on the long / high notes: "rain" (ey), "while" / "smile" (ay), "Jane" (ey), "home" (ow), "late" /
  "wait" / "stay" (ey). The first draft's "in style" put the closed "in" on a D5 - replaced by "a smile" (schwa).
- Breaths: every phrase ends on a rest of at least an 8th; at 100 BPM the longest sung phrase is 4.5 s ("I'm not
  the one who's late"; the held last "rain" 5.2 s) - the B breathes in its 8th rests (split_s 0.28 s), which kept
  "the candle leans your way, the waiter wipes the table" from becoming one 8 s breath.
- Diction (the singer's word-final consonants, singer.diction): the first render read 'drank' /k/, 'and' /d/,
  'writes' /t/ and 'on' /n/ too short in legato (35 ms) - the rhythm gave 'drank' / 'writes' a quarter, 'and' became
  'I' / 'so' / 'now', 'let it run' became 'let you be' (no stop before a consonant), 'keeps on asking' / 'keep on
  saying' became 'wipes the table' / 'tell the evening', and 'mind' got a breath after it. Final render: no coda warnings.
- Original lyrics; no line quotes or paraphrases an existing song.

## First version (126 BPM, Bb; FEW_A = False)

**A1**  Down on Jane Street, rain / taps the awning, sings a while. / I ordered two, I drank them both, / I tipped the
band a smile.

**A2**  Down on Jane Street, rain / writes your name across the glass. / I let you be, I let you go, / I let the taxis
pass.
