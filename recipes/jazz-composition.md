# Jazz composition: writing a tune and a solo like a master

Craft for writing (not playing) a jazz piece: the head melody, its chart, the intro and tag, and a written-out solo.
Distilled from five rounds of a blind test (`songs/_blind/ROUNDS.md`, "rN.k" = round N, tell k) in which three
judges read the notation of composed and generated solo-piano pieces and named what gave each away. The tells were
caught in BOTH sources - the rule-based generator and agent-composed "pro" pieces - so treat every anti-pattern
below as a trap for your own pen too. Sound, voicing and touch are the players' job (`recipes/jazz-trio.md`,
`agentsound.pianist`); this file is about the notes they are given. Reference pieces written with it:
`songs/pro2-piano-waltz`, `songs/pro2-piano-blues`.

## 1. Plan before you write

Write the plan as a table in ARRANGEMENT.md first, then the notes:

- **Form**: AABA / ABAC (8- or 16-bar parts; 16 in a waltz), or a 12-bar blues with an AAB head.
- **A period plan per part**: every 4-bar phrase gets its own register band and its own landing note (never the
  last phrase's); the part's highest note sits in its peak phrase, ~60-75 % through the period (r4.1: generated
  heads "circled C5 in an A4-F5 range for 12 bars"; composed heads had a goal per phrase).
- **One climax for the piece**, at ~60-75 % of its length, usually the solo's last chorus or the first part of the
  head out - not both, and not as a fixed formula (r2.4, r3.2, r4.3). Everything else is placed relative to it.

## 2. The head melody

- **One motif, developed.** A 1-2 bar idea with a recognisable rhythm + interval shape, then answered: sequence
  (the same shape on the next chord, re-fitted to it), inversion, augmentation, a changed ending.
  Antecedent / consequent (question on V, answer on I), or AAB inside a blues chorus (r2.5).
- **Guide-tone skeleton.** Sketch the strong-beat / long notes first as a 3rd / 7th line moving by step through the
  changes (the 7th of ii falls to the 3rd of V); then decorate between them. A melody that is a rhythm template
  "filled with chord tones re-pitched per chord" is the generator's signature (r2.5, r4.1).
- **Rhythm**: no bar rhythm more than ~2x per 8 bars, no runs of four on-beat quarters, phrases that start off the
  beat and cross bar lines, rests of half a bar between phrases (r2.5, r1.8). A waltz head is especially prone to
  one dotted cell in every bar (r5).
- **No pitch circling**: no pitch on more than ~30 % of a phrase's attacks.
- **Tensions resolved by step**: a 9th / #11 / 13th / b9 on a strong beat, a chromatic appoggiatura into a chord
  tone - and its resolution in the next note (r4.1: ~90 % of fresh phrases). Every strong / long note must belong
  to its chord: no natural 11 over a dominant or maj7, no major 3rd over m7b5, no major 7th over a dominant, nothing
  held into a chord it clashes with (r3.4). Re-check after moving a motif to a new chord (r1.5).
- **Restate, don't re-roll.** A2 / A3 repeat A1 note for note up to the cadence bars, which change (a new ending, a
  turnaround into the bridge, the final cadence). A head with zero recurrence reads generated (r2.3); a blues head
  repeats bars 1-8 and rewrites 9-12 in its second chorus.
- **The bridge contrasts**: its own register (2-3 semitones higher on average), its own rhythm (long notes against
  the A's moving lines), often its own key area; it climbs to the head's peak and hands back to A (r4.1).
- **Blues = riff head.** A 1-2 bar riff stated on I, repeated (re-fitted or literally) over IV, answered by a
  punchline in bars 9-12; the second chorus varies by phrase function, not at a fixed slot (r4.2).

## 3. The chart

- **Chart variants**: the second chorus / second ending of a blues gets its own turnaround (tritone, backdoor
  iv-bVII, a pedal, minor plagal); the solo choruses play the tune's chart or its written variants - never one
  chart copied into every chorus (r4.5), never one isolated reharm in one solo chorus (r2.2).
- **Reharms are tied to melody notes**: a substitution earns its place when the melody note becomes a colour of the
  new chord (the tonic's 5th as the #11 of the Neapolitan, the 9th as the #11 of the IV). Put a reharm where the
  head out and the last solo chorus can share it.
- **Chromatic notes come from the chord**: borrowed chords (bVI, iv, bII) get their own scale - a chromatic note
  that clashes with the borrowed chord is a tell (r5).

## 4. Intro, tag, ending

- **The intro is its own material** (r2.1): a vamp (bVImaj7#11 - V7b9, I - bII, a dominant pedal, IV - iv - ii -
  V), the riff alone an octave low, a developed fragment of the hook over new chords. Never the form's last bars
  copied. Vary the vamp between pieces (r3.6: one stock vamp in every tune read as a formula).
- **The tag reprises the intro with a twist** and approaches the last chord in a way chosen for this piece (tritone,
  backdoor, plagal, deceptive, a cold stop); the end chord carries a colour that answers the tune (6/9, maj7#11,
  mMaj9, the hook's signature note on top). Vary the final gesture too: rolled, spread, a plink, a short cadenza
  (r4.5: "a bII7#11 into the last chord in 7 of 8 tags; the same rolled final chord everywhere").

## 5. The solo (write it as lines, not as chords)

The two worst habits of written solos in this repo: **an arpeggio per bar** (the agent-composed references "lean on
chord arpeggios", r5) and **sparseness by rule** (held notes alternating with empty bars, r3.5). A solo is lines.

- **Motif development from the head**: open with a fragment of the hook (displaced, re-rhythmed), answer it, sequence
  it to the next chord, then let it go and come back to it at the peak or the end. Quote, don't paste (r1.5:
  verbatim repeats over different chords).
- **Phrases of every length, crossing bar lines**: a 1-bar fragment, a 2-bar idea, and in every chorus at least one
  8-12-bar line of 8ths (r6.1: the references' phrases average 12-46 beats); start on an "and" or beat 2 as often as
  on 1; a breath of a beat or two between phrases, at most one silent bar per chorus (never in the turnaround), a
  developed answer after it (r3.5, r6.1, section 7). Roughly: 2-bar idea - a beat - 2-bar answer - a beat - an 8-bar
  line - a bar's breath.
- **Target-note chains**: aim each chord change at its 3rd or 7th (or a resolving tension), and reach it by step:
  scale steps, a chromatic passing tone, an **enclosure** (the step above + the half step below, or below-above-
  target), a chromatic approach from a half step. Off-beat chromatic notes ~15-30 % of a line's 8ths (r5: the
  generated lines had more of them than the composed references, and won).
- **Arpeggios are rare**: at most one pure arpeggio figure per 8 bars, and then of an upper structure (3-5-7-9,
  a triad from the 9th) leading into a scale line - never root-position chord tones in one direction bar after
  bar (r3.3, r4.3). Turn the line around every 5-7 notes.
- **Rhythmic variety, low entropy**: mostly 8th lines with quarter / dotted landings, a triplet now and then, 16ths
  only as a peak gesture (duration entropy of the top line ~1.7-2.2 bits, r2.6). No repeated notes inside 8th
  lines (r3.3). No stock fill at every phrase end (r1.7). Every lick at most once per piece (r4.4).
- **An arc that builds**: chorus 1 sparse-ish and middle register, chorus 2 longer lines and a wider range, the last
  chorus the peak - denser (+40-70 % attacks over the head), higher, at about head velocity plus phrase shaping,
  harmonized more (3rds / 6ths -> drop 2 / octaves at the top, r1.4). Vary the shape between pieces (r4.3).
- **Call and response**: a phrase in the upper register answered lower (or by the left hand), a question on the
  dominant answered on the tonic.
- **The planned peak is a line**: write the climax as a melodic line arching to the top note (one turn on the way
  up), maybe 2 bars in block chords / octaves at the peak - not a sweep or a scale climb, not block chords on every
  beat (r4.3).
- **Land on a target**: end the solo on a chord tone or resolved tension of the last chord, and hand over to the
  head out with a pickup that leads into its first note.

## 6. Dynamics (velocities in the notation)

- **Shape each phrase**: velocity follows the contour (up with the line, the top leaned on, a phrase's end
  released), never the beat (r3.1: on/off-beat alternation of 20-45 read as a machine).
- **One climax** at ~60-75 % of the piece; the solo at or a little above the head's level, the head out near the head,
  intro and tag softer (r2.4, r3.2). A shout lasts at most 2 bars around a melodic peak.

## 7. Breathing (the ear's verdict, not the judges')

After five blind rounds at chance level the user listened to an endless tune and heard "an endless monotone line of
notes" (HUMAN_FEEDBACK 2026-10-09). The notation judges could not catch it: the agent-written references had the same
density (8-9 attacks a bar for both hands, onsets ~0.1 beat apart in the median). Earlier rules had made it worse -
"never a silent bar", "an empty bar gets a pickup", a fill or ornament in every gap, the left hand re-striking in
every right-hand rest. A pianist breathes:

- **Silence belongs to a phrase end, not mid-phrase.** After a phrase, half a bar to two bars without a new note
  (the last note or the pedal rings into it); after a long line a long breath; in a build the breaths get shorter.
  Whole silent bars in a solo are fine when they follow a phrase (one in ~8 bars), not as "held note + empty bar" by
  rule (r3.5).
- **Density rises and falls.** Sparse statements, dense moments only at the builds; a quiet phrase after a busy one -
  lower, softer, fewer notes. Not every phrase at 8th-note density.
- **Long notes are held, not filled.** A landing note sounds its length; a fill at most every third phrase end, an
  ornament now and then on a held note - decoration is the exception.
- **The head is a melody with light comp.** Voice the arrivals (beat 1 / 3, held notes, the phrase's goal), let the
  passing notes go single; the left hand strikes the changes and often just lets the chord ring.
- **Phrases differ in level and register.** The plan's arc between the parts, and inside a part each phrase its own
  level (one loud, the next a few dB down) - not one velocity window phrase after phrase.

**The balance (blind round 6).** The breath fix overshot where it was applied by rule everywhere: half a bar to two
bars after every 5-9-beat solo phrase gave 4-10 silent bars per solo chorus, a solo SPARSER than the head (2.5
attacks a bar against the references' 4.3-6.2), and section dynamics that faded the form (the head out 2 LU under the
head, the ending 6-12 LU under the piece). Four judges caught all eight pieces. What breathes where:

- **The head breathes at phrase ends** - keep it: the landing held, a beat or more of silence at most 4-bar phrase ends
  (the user's "b sounds better"; ~75 % of them in the generated heads, the references 50-88 %).
- **The solo breathes between LINES, briefly.** Heavy-tailed phrase lengths - a 1-bar fragment, a 2-bar idea, then an
  8-12-bar line of 8ths (at least one line of 16+ beats per chorus; the references' phrases average 12-46 beats) -
  and a breath of a beat or two after each; at most one silent bar per chorus, after a long line, at the start of a
  phrase (after a cadence), never in the turnaround. The solo is denser than the head (1.3x+), its phrases start off
  the beat as often as on it. Contrast between phrases is register and touch, not fewer notes.
- **A slot is filled by a line, not a held note.** A motif / riff / resolution that ends early goes on as a line; a
  resolution comes down to its target and holds it a bar at most - a note held over two bars reads as an empty bar.
- **Lines run in directed runs.** 4-8 notes one way (scale, chromatic, an enclosure), a leap to restart and a stepwise
  fill the other way: ~0.3-0.4 direction changes per step, under ~15 % leaps of a 4th+, no repeated pitches.
- **The form keeps its level.** The head stated firmly (not timid: its touch ~v65-75, its register around G5-A5), the
  head out at the head's level, the tag coming down only in its last bars, the final chord 2-5 LU under the piece at
  v35+, nothing after it. Loudness range for jazz ~7-10 LU (the references 5.6-7.5; letters-to-the-morning's 16 LU
  belongs to new-age / classical, whose wider range stays). The one peak: the solo's last 8-16 bars, a 3rd-6th over
  the head's top, v110+, climbed into and left by a descent.

The players do this by default (`soloist.PHRASES` / `BREATH` / `CONTRAST`, `pianist.STYLES`' low fill / embellish rates,
`pianist.arrange(written=True)` for a written line, `humanize.touch(levels=)`, `endless.perform.phrase_levels`). Check
a performance with `composer.breath(song)`: the share of time with no new right-hand onset for a beat or more
(`quiet1`, per section; `quiet1_both` for both hands), rests of half a bar / a bar, attacks per bar and their spread,
phrase lengths, held notes, left-hand attacks, ornament notes per 32 bars, the phrase-to-phrase register / velocity /
density change. Endless jazz-piano, 24 tunes, before -> after the breath fix: see songs/_blind/ROUNDS.md "After the
r6 listening"; the balance after round 6: "After round 6".

### Body / gesture

After the breath A/B the user said version b was better and that, listening, they picture a player gently moving their
body - easier the better the music (HUMAN_FEEDBACK 2026-10-09). Random jitter per note moves no body. The piano
hands of the jazz presets play with a BODY (`track.humanize(body=...)`, `humanize.BODIES`): one gesture per phrase
drives timing and dynamics together.

- **The phrase arc** (Todd 1992): the line moves on and grows into the phrase's peak (its loudest written note) and
  broadens and softens away from it - one curve for both, the phrase keeps its length, onsets within +-40 ms.
- **Phrase ends slow down like a body coming to rest** (Friberg & Sundberg 1999): v(x) = (1 + (w^q - 1) x)^(1/q),
  q 2.5-3; deeper into a section end; never eating more than half the breath after it.
- **The hand travels**: a leap's landing note a few ms late (more for a bigger leap); a **breath** before a phrase that
  follows a rest (a little late, a softer first note, settling back within a beat); a little **weight** on the
  downbeat.
- **One body, two hands**: the left hand follows the right's gesture (`lead='piano'`), struck together = moved
  together.
- **The tempo lanes win**: under `s.rubato` / ritardandi / fermatas the body does not add its own tempo, its dynamics
  follow the lanes' tempo instead (letters-to-the-morning).
- Profiles: `swing` for swung tunes (steady time: arcs +-10 ms, a section end laid back <= 45 ms), `lyrical` for
  straight 8ths, `calm` for ballads (<= 70 BPM); `jazz.Feel.body` picks it.

Check it with `humanize.body_stats(song)`: the per-phrase correlation of local tempo and velocity (`coupling`), the
ritardando into the section ends (`late_ms`, fitted `w` / `q`), a leap's delay against a step's. Before -> after
(jitter -> body): r6 003 (seed 106, swing 0.6) coupling 0.06 -> 0.32 (heard with the tempo map 0.04 -> 0.21), into
the section end -4 -> +43 ms late, leap vs step -0.4 / +0.3 -> +2.8 / -2.0 ms, the piano's note dynamics 6.2 -> 7.4
dB; pro2-piano-latenight 0.18 -> 0.38 (heard 0.03 -> 0.18), leap 0 -> +6 ms; letters-to-the-morning (its tempo lanes
own the time) heard 0.13 -> 0.20, breath 0 -> +7 ms, note dynamics 5.8 -> 6.9 dB. A/B: `songs/_endless_jazz_piano/
out/body/{before,after}`, `songs/letters-to-the-morning/out/body_{before,after}.mp3`. The fitted q is only telling for
a deep ritardando (w < 0.92; a synthetic lyrical end gives back q 2.5): the swing profile's laid-back section ends are
too shallow for it.

## 8. Anti-patterns (caught in BOTH generated and agent-composed pieces)

| tell | where it showed | write instead |
|---|---|---|
| an arpeggio per bar in the solo | the v1 pro solos (r5) | scale lines with enclosures; one upper-structure arpeggio per 8 bars at most |
| one rhythm cell in most bars | waltz heads (r4.1, r5), generated A sections (r2.5) | each phrase its own rhythm; the motif's rhythm returns, not every bar's |
| chord-blind strong / long notes | moved motifs (r1.5, r3.4), borrowed chords (r5) | check every strong note against its chord (`theory.clash`, `composer.melody_issues`) |
| fixed slots | variation at chorus 2 bar 9, a 16th chorus at a fixed index, one tag approach (r4.2-4.5) | decide each piece's moments from its own material |
| copied intro / tag | r2.1 | a vamp or a fragment developed over new chords |
| sparseness by rule | empty solo bars (r3.5) | half-bar breaths and answers |
| an endless line | every gap filled, one density and level (user, r6) | the head breathes at its phrase ends; contrast of register and level between phrases |
| breath by rule | silent bars every 3-4 solo bars, the solo sparser than the head, a faded form (blind r6) | solo lines with 1-2-beat breaths, the form at its level, the peak in the solo's last bars |
| the same rolled final chord | r4.5, r5 | choose the ending per piece |

## 9. Check it

- `composer.melody_issues(notes, Harm(changes, key_pcs), lo, hi, meter=)` on every written part (clashes, leaps,
  register) - the pro2 songs run it in `build()`.
- `composer.tells(song, tune)` measures the blind-test tells on the performance: the solo's density over the head,
  duration entropy, head 5-gram recurrence, cell_max, wraps, repeats, the dynamic range and where the peak sits;
  `composer.breath(song)` whether it breathes (section 7).
- LISTEN (or look at loudness.png): a head whose short-term loudness is one flat line for a minute is a monotone
  line, whatever the notation says.
- Read the solo bar by bar as a judge would: does any bar spell its chord root-up? Does a phrase end on a target?
  Where is the one peak?
