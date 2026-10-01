# Down on Jane Street - lyrics

**Theme (never named in the song):** a woman at a sidewalk table on Jane Street (West Village) late at night, waiting
for someone who does not come - and deciding, line by line, that she is fine without him. Shown through the rain,
the empty chair, the candle, the waiter, the taxis; said plainly only once ("I'm not the one who's late") and turned
into attitude at the very end ("now you can keep the wait").

**Hook line (on the melody's hook: the leap to the held note):** "Down on Jane Street, rain" - says the title, sits
on the pickup -> high D -> held A of every A section, comes back a fourth higher at the top of the C, ends the song.

**Quotable lines (the attitude):** "I ordered two, I drank them both", "I let the taxis pass", "I'm not the one
who's late" / "now you can keep the wait".

Rhyme scheme per 8-bar part: X A X A (while / smile, way / stay, glass / pass, late / wait).
Notes per line (one note per syllable, the melody in `song.py`): `lyrics.check` clean for every part.

## Head (sung once through)

**A1**

    Down on Jane Street, rain                 (5)  the hook
    taps the awning, sings a while.           (7)  A
    I ordered two, I drank them both,         (8)  X  - quotable
    I tipped the band a smile.                (6)  A

**B**

    Your chair is full of evening,            (7)  X
    the candle leans your way,                (6)  A
    the waiter wipes the table,               (7)  X
    I tell the evening: stay.                 (6)  A  - the evening of line 1 again

**A2**

    Down on Jane Street, rain                 (5)  the hook
    writes your name across the glass.        (7)  A
    I let you be, I let you go,               (8)  X
    I let the taxis pass.                     (6)  A  - quotable

**C**

    Let the bass walk me home,                (6)  X
    I'm not the one who's late,               (6)  A  - the one direct line
    down on Jane Street, rain -               (5)  the hook, a fourth higher: the top note (G5 on "Jane")
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
- Breaths: every phrase ends on a rest of at least an 8th; the longest phrase ("Let the bass walk me home, I'm not
  the one who's late") is ~7.5 s.
- Diction (the singer's word-final consonants, singer.diction): the first render read 'drank' /k/, 'and' /d/,
  'writes' /t/ and 'on' /n/ too short in legato (35 ms) - the rhythm gave 'drank' / 'writes' a quarter, 'and' became
  'I' / 'so' / 'now', 'let it run' became 'let you be' (no stop before a consonant), 'keeps on asking' / 'keep on
  saying' became 'wipes the table' / 'tell the evening', and 'mind' got a breath after it. Final render: no coda warnings.
- Original lyrics; no line quotes or paraphrases an existing song.
