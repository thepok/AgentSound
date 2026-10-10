# Catch Fire - lyrics

**Theme (one sentence):** someone the world kept trying to put out - written in pencil, pushed under, hosed down -
turns every blow into fuel: being struck is how a match catches fire.

**Image system:** matches, gravel, ashes, a name in pencil, fists, doors nailed shut, a fire hose, rain, an ember under
a coat, daylight. The feeling is never named; the hook says it in the match's own terms.

**Hook line:** "Strike me down, I catch fire" - the chorus's first and third line, on the melody's peak (a held A4 on
the open 'ai' of "fire"); unchanged every time. The last chorus turns "I'll burn on into daylight" into "we'll".

**Quotable lines (attitude):** "Kept my matches dry" / "All the doors you nailed together make a fine old blaze" /
"Strike me down, I catch fire - every bruise is kindling".

## The words (one token per note in song.py; `lyrics.check` clean on every line)

```
[Intro - gang chant]
Whoa, oh, oh, oh, oh, oh.
Whoa, oh, oh, oh, oh - hey!

[Verse 1]                                   syllables  rhyme
Gravel in my pockets,                        6          x
ashes on my shoes,                           5          A
they wrote my name in pencil                 7          x
like I'd be gone by June.                    6          A
Kept my head below the window,               8          x
kept my matches dry,                         5          B
every fist that came to find me              8          x
struck another light.                        5          B

[Pre-chorus]
Bring the rain, bring the water,             7          C (slant: water / marrow)
bring the hoses and the hail,                7          x
soaked all the way to the marrow,            8          C
so go on, try me -                           5          (the breath: one beat of silence)

[Chorus]
Strike me down, I catch fire,   (hey!)       7          H
every bruise is kindling,                    6          x
strike me down, I catch fire,                7          H
I'll burn on into daylight.                  7          x

[Post-chorus - gang chant]
Whoa, oh, oh, oh, oh, oh.
Whoa, oh, oh, oh, oh - hey!

[Verse 2]
Twenty winters in a cellar,                  8          x
now I own the flame,                         5          D (slant: flame / blaze)
all the doors you nailed together            8          x
make a fine old blaze.                       5          D

[Pre-chorus] (as above)
[Chorus] (as above)
[Post-chorus] (as above)

[Bridge - stripped]
They poured the ocean on me,                 7          x
I was breathing smoke,                       5          E
still I kept one ember                       6          x
underneath my coat.                          5          E

[Build - the pre-chorus with the whole gang]
Bring the rain, bring the water,
bring the hoses and the hail,
soaked all the way to the marrow,
so go on, try me -

[Final chorus x2]
Strike me down, I catch fire,
every bruise is kindling,
strike me down, I catch fire,
I'll burn on into daylight.
Strike me down, I catch fire,
every bruise is kindling,
strike me down, I catch fire,
we'll burn on into daylight.

[Post-chorus / end]
Whoa, oh, oh, oh, oh, oh.
Whoa, oh, oh, oh, oh - hey!
```

## Notes per line

- Verses sit low (C3-C4) and leave a bar of air after every line (sparse, never crammed: "sie klingt gerusht" was a
  jazz finding, but the rule holds - at 124 BPM the shortest syllables are 16ths only as pickups inside a dotted
  figure, most are 8ths and longer).
- Stresses: every two-syllable word has its stressed syllable on the stronger beat (GRAV-el, POCK-ets, PEN-cil,
  be-LOW, WIN-dow, MATCH-es, an-OTH-er, to-GETH-er, MAR-row, O-cean, BREATH-ing, EM-ber, un-der-NEATH, KIN-dling,
  DAY-light) - `lyrics.check` reports none.
- Open vowels on the long and high notes: "shoes" / "June" (oo), "dry" / "light" / "fire" / "try" (ai), "hail" /
  "flame" / "blaze" (ay), "gone" / "smoke" / "coat" / "whoa" (oh / aw), "me" (ee). "river" was first planned in the
  pre (a closed 'ih' on its top note: `lyrics.check` flagged it) -> "water".
- The first draft of the pre sang "I've been soaked down to the marrow, so go on and try me": the build's diction
  check found the word-final /n/ of "been" / "down" and the /d/ of "and" squeezed to 35 ms in legato clusters (8th
  and 16th notes before a consonant onset) - rewritten as "soaked all the way to the marrow, so go on, try me"
  (the /t/ of "soaked" links onto "all", "on" gets a whole beat); "breathing" got a 16th of air before "smoke".
- "every" is sung in two syllables (`every{eh1 v r iy0}`: the dictionary's first entry has three).
- "fire" takes two notes (fi- on the held A4, -re a short G4 fall) - how the word is sung in rock.
- Word-final consonants before rests (pockets, shoes, June, dry, light, flame, blaze, hail, marrow, coat, smoke) sit
  at the end of their notes with a beat or more of rest after them: room for the singer's diction rule.
