# Blind test rounds (endless jazz-piano vs composed pieces)

Judges read only JUDGE.md + packets/ (a copy outside the repo). Target: accuracy near 50 %.

## Round 1 (2026-10-09, endless with the arc plan)

| Judge lens | Correct | Misses |
|---|---|---|
| composer | 6/8 | ASSM, GVJR (composed, called generated) |
| pianist | 6/8 | ASSM, GVJR |
| statistician | 6/8 | ASSM, GVJR |

All four generated tunes were caught (confidence 80-92). The two misses are the composed waltz and blues, whose solos
came from the shared soloist tool; the two composed pieces with hand-written solos were recognised. So most tells
live in the shared soloist / pianist vocabulary, a few in the endless head composer. Unanimous tells:
1. Solo opening grid: head motif on odd bars, empty or one-reply even bars (often a whole silent bar).
2. One fixed 16th-note run template (cell on 1-2.75, hole on 3, triplet pickup on 4, landing on 2 held 1.92 beats)
   at the same chorus position in four pieces; an 8th-note "a b c b c d" cell in the waltz bridges.
3. Register wrap: single notes folded an octave inside a line (D6 Eb5 D6).
4. Solo energy as a velocity plateau (+10..+22 over the head) with equal or lower density; composed solos get
   denser (+40-70 %) at about head velocity, peak once ~2/3 in, voiced as block chords.
5. Verbatim bar repeats over different chords; the motif not re-fitted to the chord.
6. Every fast note harmonized (+1); flat velocities inside runs.
7. The same beat-4 sextuplet fill at most phrase ends.
8. Heads built from one-bar cells + pickup-only bars; the chart copied unchanged into every chorus.

## Round 2 (2026-10-09, after the soloist/pianist fixes + solo_piano; IDs re-rolled)

| Judge lens | Correct | Confidence |
|---|---|---|
| composer | 8/8 | 66-78 (round 1: 75-92) |
| pianist | 8/8 | 58-78 |
| statistician | 8/8 | 62-75 |

The shared-soloist tells are gone: the composed waltz and blues (whose solos use the same soloist) are now read as
composed, and the judges list the soloist/ornament habits as "the shared player model, not evidence". What is left is
the endless COMPOSER (lower confidence, but a clean 4/4 split). Unanimous tells:
1. Intro and tag are a copy of the form's last 4/8 bars; composed pieces write a vamp (bVImaj7#11-V7b9, IV-iv-ii-V,
   the riff alone an octave low) and reprise it in the tag with a twist (tritone ending, mMaj9 / 6/9).
2. Exactly one isolated reharm (a tritone sub) in one solo chorus only (round-1 fix overshoot); composed pieces keep
   the solo on the tune's own chart / its written variants.
3. The head is re-rolled, never restated: 5-note shape recurrence in the head 0.00-0.02 vs 0.08-0.38 composed (round-1
   "no verbatim repeats" overshoot). Restate A note for note, vary only the cadence bars; a blues head repeats bars 1-8.
4. Macro dynamics: loudness range 4.0-5.9 LU vs 6.4-7.8; the peak at 43-56 % or in the solo, while composed pieces
   often put the shout in the head-out (v115-124, block chords) at 60-75 %.
5. Melody = a rhythm template filled with chord tones (3+3+2 cell in nearly every bar, quarter-note blocks); composed:
   one motif + sequence/answer (AAB, antecedent-consequent), a recognisable hook.
6. Solo rhythm too random (duration entropy 2.4-3.4 vs 1.7-2.2): longer 8th lines across bar lines, 16ths/triplets as
   rare peaks (round-1 overshoot).
7. Player details (both sources, lower priority): the waltz LH rests every second bar; bass anticipations clash with
   the bar's chord; a tremolo held across the bar line into a clashing chord; the swing groove splits rolled chords
   (lower voice straight, top swung); the solo's displaced head quote is a fixed offset.

## After round 2 (fix/endless-composer-r2; the r3 renders in `songs/_endless_jazz_piano/out/r3`)

What changed, measured by `composer.tells()` over 24 tunes (seeds 100-123, odd seeds swing 0.6) before -> after
(the 4 composed pieces in brackets):
1. Intro / tag are the tune's own: a vamp from `genres.INTROS` (bVImaj7#11-V7b9, IV-iv-ii-V, I-bII, a dominant pedal,
   the riff alone an octave low without the left hand) with the hook over it; the tag reprises it with the tritone
   sub into a 6/9 / maj7#11 / mMaj9 / m6/9 end chord. Copied from the form: 24/24 -> 0/24 (0).
2. The solo plays the chart; half the tunes reharmonize the last cadence once, in the last solo chorus AND the head
   out, with a new melody note there. Isolated reharms per tune 1.29 -> 0 (0).
3. The A is restated note for note up to its cadence (blues: bars 1-8 repeated, 9-12 rewritten); the A sections are
   played from the A1's dice with a plainer decoration. Head 5-note recurrence 0.04 -> 0.23 (0.20; written 0.5).
4. A blues chorus is AAB; no cell runs four on-beat quarters: quarter-note runs 5.1 -> 0.5 per head (2.0), the most
   common bar rhythm 0.28 -> 0.26 of the head (0.25).
5. Macro dynamics: the solo builds to its climax at its end; half the tunes shout the head out's first part (block
   chords, touch +14/+24, the melody's top lifted over the head's), the last part comes down, intro / tag softer.
   Loudness range from the notes 4.6 -> 5.3 (6.1); the r3 renders' LRA 5.8 / 7.5 / 7.8 / 5.8 (round 2: 4.4 / 5.9 /
   5.8 / 4.0; the composed pieces re-rendered: 6.0 / 7.7 / 7.4 / 5.1); the loudest 4 bars at 0.65 -> 0.73 of the
   piece (0.77), the top note 0.49 -> 0.68 (0.69). All four r3 tunes happen to be shout tunes (the seeds' dice; 11 of
   the 24).
6. Solo rhythm: 8th-note lines, 16ths / triplets rare (vocabulary weights, the soloist's rhythm table), landing
   lengths on the 8th grid: duration entropy 2.71 -> 2.16 bits (2.00).
7. Players: the waltz left hand keeps the pulse (silent LH bars ~72 -> ~5 per waltz tune), no clashing bass push, no
   ornament ringing into a clashing chord, rolled chords swung whole, a varied displacement of the solo's quote.
Round 1's measures stay: octave wraps 0, verbatim solo repeats 0, silent solo bars 2.2 -> 1.8, harmonized fast notes
0.15 -> 0.11.

## Round 3 (2026-10-09, after the composer fixes; IDs re-rolled)

| Judge lens | Correct | Confidence | Misses |
|---|---|---|---|
| composer | 6/8 | 55-70 | a generated blues read as composed, the composed bossa read as generated |
| pianist | 6/8 | 60-75 | the composed waltz and blues (shared soloist) read as generated |
| statistician | 6/8 | 70-80 | the same two |

Average 75 % (round 2: 100 %). The line between the groups is no longer "generator vs composer" but "the shared
player model vs hand-written solos": the two composed pieces whose solos come from the shared soloist are grouped with
the generated tunes. The remaining tells therefore sit mostly in the SHARED players (they improve every song):
1. Velocity in 8th/16th lines alternates on/off the beat by 20-45 (on-beat +7..+14 on average); composed lines shape
   velocity with the phrase (rises with the pitch, an arc over 2-4 bars), on/off difference about 1.
2. One fixed whole-piece dynamic plan: the shout head-out (v110-125) then a soft last A, the solo no louder than the
   head (round-2 overshoot: the shout in every tune of the sample). Composed: the peak in the solo's last chorus/A at
   60-75 %, the head-out near head level; the shout at most 2 bars at a melodic peak, the plan varied per piece.
3. Repeated notes in 8th lines (10-18 % vs 0-1 %); 4-note scale cells that reverse every beat; arpeggio sweeps.
4. Chord-blind strong-beat / long notes after a motif is moved: natural 11 over a dominant or maj7#11, major 3rd over
   m7b5 or minor, major 7th over a dominant; a note held into a clashing chord.
5. Solo opening: held single notes alternating with empty bars (up to 10 empty bars per 64) - sparseness by rule;
   composed: a 2-bar idea, a rest, a developed answer; half-bar breaths, not whole empty bars.
6. Stock intro IV-iv-ii-V with the head's first phrase refitted note by note, in all four generated tunes (round-2
   overshoot: one vamp dominates); one rhythmic cell repeated ~9 times; a fixed tritone-sub slot in the last chorus.
7. Trills/tremolos/runs in loud bars and in the intro; the LH: sparse root+7 shells (1.2-1.8 attacks/bar) - add
   rootless voicings and anticipations.

## After round 3 (fix/player-r3; the r4 renders in `songs/_endless_jazz_piano/out/r4`, packets seed `blind-jazz-piano-v4`)

The fixes sit in the shared players first (every song using them changes), each rule a distribution / budget.
`composer.tells()` round-3 measures over 24 tunes (seeds 100-123, odd seeds swing 0.6) before -> after; the 4 pro
songs (waltz / blues / latenight / bossa) before -> after in brackets:
1. Line velocity follows the contour and the phrase, never the beat (`humanize.touch`: passing notes / low
   neighbours lighter on or off the beat, syncopations, leap targets and contour tops leaned on, neighbour steps
   capped at 15, a seeded +-2; `soloist._lines`: the run ramp follows pitch, no weak-8th ghosting; grace figures
   ~10-22 under the principal; fills rise to within 12 of their target). On/off-beat difference in 8th / 16th lines
   11.6 -> 3.3 (15.9 / 9.0 / 4.6 / 2.9 -> 2.4 / 3.4 / 1.3 / 2.0), zig-zag rate 0.70 -> 0.49 (0.74 / 0.63 -> 0.49 /
   0.60), neighbour steps over 15: 29 % -> 6 %.
2. The whole-piece dynamic plan is drawn per tune (`plan['dynamics']`: solo 45 % / shout 25 % / late 15 % / calm
   15 %): the peak in the solo's last chorus (the loudest 4 bars at 0.60-0.76 of every tune, was 0.51-0.85), the
   solo at or above the head (+0.5 -> +1.6 dB, every tune >= +0.7), the head out near the head (+0.6 -> +0.3 dB,
   -0.4..+1.1), a shout only in shout tunes and only the 2 bars around the head out's lifted top note (block chords,
   the peak note v118). Loudness range from the notes 5.25 -> 5.86; the r4 renders' LRA 5.9 / 7.3 / 7.3 / 6.4 (r3
   5.8 / 7.5 / 7.8 / 5.8). None of the 4 blind tunes draws the shout now (solo, calm, solo, late).
3. Repeated notes inside lines 10.8 % -> 2.1 % (17.1 / 10.7 % -> 1.3 / 3.2 %; `soloist._lines` 'unisons'), reversing
   4-note cells 0.46 -> 0.59 per 32 solo bars (under one per chorus), pure arpeggio bars 0, the solo's chord changes
   struck on a 3rd / 7th 0.68 -> 0.73.
4. Clashes (theory.clash on beat 1 / 3 and notes > half a beat, anticipations against the chord they anticipate,
   notes held into a clashing chord) 1.46 -> 0.29 per tune (2 / 2 / 3 / 5 -> 1 / 0 / 3 / 5: the latenight / bossa
   solos are hand-written); `soloist._lines` 'chords'.
5. Empty solo bars 2.7 -> 0.15 per 64 (10 / 3.6 -> 1 / 0): a statement is the idea, a half-bar breath and a developed
   answer; a bar without an attack gets a pickup into the next phrase (the held note lifted).
6. Intro vamps re-weighted + three new ones (8 kinds in 24 tunes, none over 8), the intro's line drawn (`INTRO_LINES`:
   hook 11, answer 7, cell 3, voicings 3), the reharm slot drawn over the head-out parts (A2 5, A3 2, B 2, C 2; 11 of
   24 tunes), at most two bars of one rhythm in a row in the frame.
7. Fast figures (trills / tremolos / runs / sweeps; `pianist.FAST` now holds the runs too) 3.3 -> 1.3 per tune, the
   most in one chorus 1.6 -> 0.7, none in loud bars or the intro's last bar (0.25 -> 0.04); the left hand
   (`LH_SHELL`): rootless voicings 6 % -> 38 % of its chords, attacks per bar 1.55 -> 1.71, on the & of 2 / 4 10 % ->
   16 %, the waltz plays bass + chord.
Rounds 1-2 stay: octave wraps 0, verbatim solo repeats 0, silent solo bars 1.8 -> 0.1 per tune, harmonized fast notes
0.11 -> 0.09, solo duration entropy 2.16 -> 1.94 (composed 1.7-2.2), head 5-gram 0.23 -> 0.28, intro / tag copies 0,
isolated reharms 0, cell_max 0.26, quarter runs 0.5, silent LH bars 5.0 -> 5.1. Watch: the solo's mean top velocity
over the head +4.7 -> +9.0 (round 1's plateau was +10..+22 at equal density; now +60 % density), the highest note
at 0.68 -> 0.62 of the piece (some tunes keep the head's climax as the top note).

## Round 4 (2026-10-09, after the player fixes; IDs re-rolled)

| Judge lens | Correct | Confidence | Misses |
|---|---|---|---|
| composer | 8/8 | 55-70 | - |
| pianist | 6/8 | 55-75 | generated bossa-blues -> composed, composed bossa -> generated |
| statistician | 4/8 (chance) | 55-75 | composed latenight, waltz, bossa -> generated; generated AABA -> composed |

Average 75 % (18/24) with the lowest confidences so far; the statistician is at chance and says "most features may
come from the shared framework; only the head and chart writing separated them, weakly". The composer still separates
on the HEAD writing. Tells:
1. Head melodies without a goal: phrases circle one pitch (C5 in an A4-F5 range for 12 bars), one rhythm cell in
   nearly every bar (11-17 uses), chord tones re-pitched per chord; composed heads: each 4-bar phrase has its own
   target pitch / register, a peak ~60-75 % through the period, a bridge with its own register and rhythm.
2. A fixed variation slot: chorus 2 bar 9 jumps to the head's peak (both generated blues); phrase endings on a 4.5
   anticipation held into an empty RH bar.
3. The solo shape is the same everywhere (sparse -> 16th middle -> loud last section, peak at 64-80 %); the 16th
   double-time chorus at a fixed index; arpeggio sweeps / scale climbs into the peak; block-chord peaks on every beat.
4. Licks reused within and across pieces (a triplet + 0.08-beat stab, the G altered run, the up-sweep, trill shapes).
5. One chart for all choruses in the blues (no turnaround variants); a bII7#11 into the last chord in 7 of 8 tags; the
   same rolled final chord everywhere.
6. Feel/form pairing looks random (a blues with a bossa feel; a straight-8th jazz blues).


## After round 4 (fix/endless-r4; the r5 renders in `songs/_endless_jazz_piano/out/r5`, packets seed `blind-jazz-piano-v5`)

Every fix is a weighted distribution or a budget in the owning tool (the composer / genres data, the soloist, the
piano vocabulary, the pianist, perform). `composer.tells()` round-4 measures over 24 tunes (seeds 100-123, odd seeds
swing 0.6) before -> after, the 4 pro songs in brackets; plan-level shares over 100 tunes (seeds 100-199):
1. Heads with goals: a period plan first (`genres.CONTOURS`, drawn per part kind: every 4-bar phrase its register and
   a landing goal never the last phrase's, the part's top note in its peak phrase's second half, the bridge in its own
   register `BRIDGE_SHIFT` with long notes (`CELLS[..]['long']`, one rhythm per tune) against the moving lines), the
   strong notes a guide-tone line, a tension on a strong beat resolved by step in ~88 % of the fresh phrases
   (`_appoggiatura`), a rhythm cell (3+ notes) at most twice per 8 bars (a blues' riff repeat excepted) and no pitch on
   more than ~30 % of a phrase's attacks (`_style_issues`, weighed under the hard rules). Circling (most common pitch's
   share per phrase) 0.31 -> 0.27 (0.21-0.25), its max 0.41 -> 0.33; phrase top spread 2.2 -> 2.7 semitones (1.9-2.6),
   phrase register spread 1.5 -> 1.7 (1.5-2.3); a part's top note at 0.43 -> 0.54 of it (the A's 0.6; pro 0.34-0.57);
   one bar rhythm per 8 bars 2.35 -> 2.16 uses (1.5-3.1), max 2.96 -> 2.42; phrases with a resolved strong-beat
   tension 0.62 -> 0.89 (0.33-0.88); the bridge's register over the A +1.7 -> +2.5 (+2.3..+3.3), its long-note share
   -0.08 -> +0.08 against the A (-0.03..+0.12). The A2 / A3 still restate the A1 up to the cadence (head 5-gram
   0.28 -> 0.28).
2. No fixed variation slot: a blues head's second chorus varies by phrase function (`SECOND_CHORUS`: its answer 8, its
   second statement 7, calmer with the climax in the first chorus 6 of 21 blues) - the climax in chorus 2 bar 9, bar
   5 or chorus 1 bar 9; the first bar where the second A differs 7.6 -> 6.2. Phrase endings drawn (`PHRASE_ENDS`):
   downbeat 124 / other 95 / anticipation 6 / pickup 5 -> 63 / 90 / 14 / 29 (+ short landings that leave the bar to the
   left hand's answer).
3. The solo's shape drawn per tune (`plan['solo']['shapes']`, soloist arcs rise / slow / early / sparse / chords /
   trade4, each with the dynamic plans it allows): 24 tunes rise 6, chords 4, sparse 4, trade 4, early 3, slow 3 (100:
   23 / 13 / 17 / 15 / 19 / 13); double time once in 6 / 24 (29 / 100) at a drawn place (`perform.solo_arc`): 16th
   bars per tune 5.7 -> 1.25. Lines (`soloist.target_line`): a turn-back every 5-7 notes (one-way stretches 3.2 -> 2.9
   notes, the longest 7.6 -> 5.6; pro 5-9), chord tones in one direction 5+ 1.44 -> 0.38 per 32 bars, the beats on
   chord tones 0.94 -> 0.86 (0.79-0.93: `LEAN`, a non-chord tone resolving by step; a chord change keeps its 3rd / 7th);
   the climax a line arching to its top note (turning once on its way up), block chords on every note only in the
   block-chord chorus (longest block run 2.9 -> 3.1); a sweep / scale climb into the solo's top note 1 -> 2 of 24.
   Trading 4s: the right hand plays 4 bars, the left hand a line of its own in the next 4 with the right hand comping.
4. Licks: every FAST figure at most once per piece (`pianist.Memory(once=True)`), a soloist move's name once
   (`same_every` the whole piece), pickups drawn from `soloist.PICKUPS` (each rhythm once per solo, leading into
   wherever the next phrase starts); a set remembers the tune before (`perform.build(prev=)`, `Memory.after`: its
   fast figures a tenth as often, its moves counted). Fast cells of the solo recurring in it 4.5 -> 0.38 per tune (0);
   consecutive tunes sharing a fast cell 4.1 -> 0.35; sharing a cell or a lick kind 2.1 -> 1.3 with the set memory.
5. Charts: a blues head's second ending (a `CHART_VARIANTS` turnaround / cadence variant: tritone, backdoor, pedal,
   minor plagal, ii-V split) in 14 of 21 blues, the solo choruses play the first or the second chorus's chart; the
   reharm draws its kind too. Tag approaches (`TAG_APPROACH`) bII7#11 in 24 / 24 -> 5 / 24 (100: tritone 30, backdoor
   22, plagal 20, deceptive 14, cold stop 14); the final chord (`END_STYLES`) rolled in 24 / 24 -> roll 9, spread 6,
   plink 3, cadenza 3, fade 3.
6. Feel / form (`FEEL_FORMS`, the form drawn first): blues feels (100 tunes) straight-8th 15, swung 8, bossa 5, ballad
   6 -> swung 9, straight-8th shuffle 8 (the new 'shuffle' feel: bar style, stride left hand), ballad 3, straight 1;
   bossa with a song form 3 / 8 -> 13 / 13.
Rounds 1-3 (24 tunes): silent solo bars 0.08 -> 0.04, both hands silent 0, wraps 0, verbatim repeats 0, fast figures
10.2 -> 3.7 (their repeats 0.46 -> 0.13), harmonized fast notes 0.09 -> 0.09, the solo's density over the head 1.60 ->
1.08 (pro 1.11-1.61; its densest third 2.21 -> 1.35, pro 1.44-1.74), its velocity over the head +9.0 -> +4.5 (pro
+0.1..+6.7), head 5-gram 0.28 -> 0.28, solo duration entropy 1.94 -> 2.15 (1.74-2.14), the loudest 4 bars at 0.69 ->
0.69, the top note at 0.62 -> 0.63, intro / tag copies 0, isolated reharms 0, cell_max 0.26 -> 0.23, quarter runs 0.5
-> 0, on / off-beat velocity 3.3 -> 3.2, zig-zag 0.49 -> 0.52, repeated notes 2.1 % -> 2.6 %, reversing cells 0.59 ->
0.04, clashes 0.29 -> 0.29 (fills / long pickups re-fitted: `pianist._unclash`, `soloist.pickup(chord_at=)`), empty
solo bars 0.15 -> 0.08 per 64, fast figures per chorus 0.71 -> 0.83, none loud or in the intro's end.
Watch (moved by the new distribution, not by a rule): the solo over the head +1.6 -> +0.2 dB (pro -0.7..+1.0: a
slow build / less is more / trading tunes leave the peak to the head out, `out_peak`), the loudness range from the
notes 5.86 -> 5.18 (pro 4.6-6.5; the r5 renders' LRA 6.6 / 5.9 / 7.6 / 4.9, r4 5.9 / 7.3 / 7.3 / 6.4), velocity
steps over 15 in lines 6.3 % -> 9.7 % (the smooth 16th runs got rare; per 8th line as before: the head 10 %), chord
changes struck on a 3rd / 7th 0.73 -> 0.61 (pro 0.40-0.82), left-hand attacks per bar 1.7 -> 2.6 (the traded bars'
lines, the stride shuffle), rootless left-hand chords 0.38 -> 0.35.
The 4 r5 tunes keep the slots: seed 105 'bright' pinned to the waltz (plan {'mood', 'feel'}), seed 100 'blue' (now a
straight-8th shuffle blues, unpinned), seed 106 'late-night' swing 0.6 pinned to a straight AABA (plan {'mood',
'feel', 'form'}: item 6 would draw a ballad ABAC), seed 202 its r4 set-plan entry (a bossa, now ABAC). The pro waltz /
blues re-rendered (their solos use the shared soloist; LRA 6.0 / 7.2, clicks 0); latenight / bossa unchanged.

## Round 5 (2026-10-09, after the head-goal / solo-shape / lick fixes; IDs re-rolled)

| Judge lens | Correct | Confidence |
|---|---|---|
| composer | 6/8 | 55-70 ("every verdict close to a coin toss") |
| pianist | 2/8 | 52-68 |
| statistician | 2/8 | 52-72 |

10/24 = 42 %: at chance, and two judges systematically INVERTED - they read three of the four generated tunes as
composed and three of the four composed pieces as generated. The generated lines now have more chromatic approach
tones (15-30 % of off-beats) than the agent-written reference solos, which lean on chord arpeggios. Goal of the loop
reached for notation-level judging. Remaining notes for both sides (not tells any more): arpeggio-per-bar solo
passages (mostly in the reference pieces), rhythm-cell reuse in waltz heads, a quiet sparse solo in one generated
blues (solo below head loudness), clashing chromatic notes on borrowed chords, the same rolled final chord, doubled LH
roots in bossa tags. Next quality bar: the user's ears, and stronger references than agent-written pieces.

## After round 5 (fix/endless-r5; the r6 renders in `songs/_endless_jazz_piano/out/r6`, packets seed `blind-jazz-piano-v6`)

The composer judge (6/8, the lens that matters most) asked for development instead of re-pitched patterns. Every fix
is a weighted distribution or a budget in the owning tool (soloist, piano vocabulary, pianist, humanize.touch, the
endless composer / genres / perform). `composer.tells()` gains round 5's measures (`_tells_r5`); 24 tunes (seeds
100-123, odd seeds swing 0.6) before -> after, the pro songs in brackets (waltz / blues / latenight / bossa / pro2
waltz / pro2 blues):
1. Solos from a motif (`soloist.motif_cell` / `motif_line`, `MOTIVIC` 0.65, `CELL_MOVES`): a stage starts from the
   hook's fragment and every call develops the cell before it (sequenced, inverted, displaced, truncated, augmented;
   `transform` keeps the contour), the response continues it (answer / sequence / riff moves); phrases 3-12 beats.
   Solo phrases holding a development of a hook cell 0.16 -> 0.19 (pro 0.21 / 0.8 / 0.4 / 0.25 / 0 / 0.67), phrase
   length 5.2 -> 6.1 beats, crossing a bar line 0.84 -> 0.88; pure chord-arpeggio bars 0.03 -> 0.05 (pro up to 0.41),
   bars of 85 %+ chord tones 0.19 -> 0.34 (pro 0.2-0.82: rich chords count most notes as tones).
2. Onset-pattern reuse: the A's 'develop' / 'answer' phrase varies the hook's rhythm (`genres.DEVELOP_RHYTHM`), intro
   / tag develop a fragment: one bar pattern's most uses per 32 bars 4.4 -> 3.5 (pro 4-7).
3. Heads as guide-tone lines: a new chord met by its 3rd / 7th by step (weighted in `_choose`): 0.22 -> 0.30 of the
   changes (pro 0.24-0.42); head arpeggio bars 0.11 -> 0.10.
4. Chromatic notes from the chord: `soloist.scale(ctx, t)` is the chord's own scale over borrowed / chromatic chords,
   chromatic notes only as half-step approaches into a target on the beat (target_line, transform, the composer's
   `_fit`), the lean on a beat a chord-scale step, `pianist.arrange` never harmonizes a chromatic note, the
   appoggiatura no longer replaces an approach's target: chromatic top notes 8.7 -> 4.8 per 32 bars, unresolved /
   harmonized / held ones 4.8 -> 2.4 (pro 2.4-14.9 -> 2.4-13.7).
5. Solo intensity: the velocity window builds across every solo, slow / sparse / trading shapes no longer start soft,
   the traded left-hand line as loud as the right hand's, a double-time burst only in the solo's second half, the
   'early' shape peaks past the middle and builds again, the 'space' stage plays motivic 3-6-note calls: the solo from
   its 2nd chorus (a one-chorus solo: its 2nd half) +0.8 -> +1.5 dB over the head, its last chorus / half the loudest
   75 % -> 96 % of the tunes, longest run of single-note bars 1.0 -> 1.2 (no run over 2).
6. Intros / tags (`INTRO_LINES` / `TAG_LINES`: augment, fragment, answer, chords): intro / tag bars copying a head bar
   0.55 -> 0.19 (pro 0.25-0.88).
7. Destinations: the bridge's last phrase from `BRIDGE_ENDS` (its line into the turnaround): fewest sung attacks in
   a bridge's last 2 bars 4.1 -> 4.9; the climax in the form's last section (`PEAK_PART` 'last' 60 %: an AABA's last
   A restates its first phrase and climbs to the peak): head peak in the last section 0.48 -> 0.92 of the tunes.
8. A range: register G4-Bb5 (peak Db6), wider A contours, a soft "an A spans an octave" rule: the smallest A range
   8.6 -> 11.1 semitones (82 % of the tunes >= 12; mean A range 9.1 -> 12.5; pro 13-18).
9. The solo ends on a target (`perform._land_solo`: a bar left empty before the head out gets a landing note; the last
   note a common tone of the two chords or an anticipation of the head out's first chord; no sweep into the head out):
   0.58 -> 1.0.
Lower priority: the final chord's grip drawn (`perform.END_VOICINGS`, also for the pro songs: `_end_clips` seeds by
the symbol), the bossa tag's left hand is the bossa comping alone (no doubled roots); the blues LH and double-time
16ths unchanged.
Regressions checked (rounds 1-4, 24 tunes): wraps 0 -> 0.04 (one 14-semitone leap at a call/response seam), verbatim
repeats 0, silent / empty solo bars 0.04 / 0.08 -> 0 / 0, both hands silent 0, harmonized fast notes 0.09 -> 0.10,
fast figures 3.7 -> 3.5 (repeats 0.13 -> 0.04), licks recurring 0.38 -> 0.17, clashes 0.29 -> 0.29, repeated notes
2.6 % -> 2.7 %, on / off-beat velocity 3.2 -> 3.6 (`humanize.touch`: a phrase's pickup now leans into its note; the
head's lines measured alone 8.8 -> 6.8), zig-zag 0.52 -> 0.47, head 5-gram 0.28 -> 0.22, solo entropy 2.15 -> 2.2,
circling 0.27 -> 0.25, bridge register +2.5 -> +2.4, cell8 2.2 -> 1.95, dyn range 5.2 -> 6.0, peak_x 0.69 -> 0.72,
top_x 0.63 -> 0.61, intro / tag copies 0, isolated reharms 0. Watch: the solo's top velocity over the head +4.5 ->
+8.6 (the shapes that started soft now don't; rise / chords solos were already +13..+16), density 1.08 -> 1.01.
r6 renders (same pins as r5): LRA 6.5 / 5.7 / 8.0 / 5.2 (r5 6.6 / 5.9 / 7.6 / 4.9), clicks 0. All four pro-piano
songs and the pro2 waltz / blues re-rendered (LRA 6.1 / 7.4 / 6.7 / 4.8 / 6.1 / 5.4, clicks 0). Packets: pro2 waltz
and blues replace the pro waltz and blues.

## After the r6 listening (fix/piano-breath; A/B in `songs/_endless_jazz_piano/out/breath`)

The user LISTENED to r6 003 ("A Bridge for Grove") after five rounds at chance level: "sounds like an endless monotone
line of notes". The notation judges could not hear it - the agent-written references share the density (both sides
use the same players), so the blind test only proved "as good as our references". Its loudness.png shows it: the
head's short-term loudness one flat line for 80 s, 7-8 attacks and a mean velocity of 65-73 in EVERY 2-bar unit.
Causes, all in the shared players / the performer, mostly earlier over-corrections: "never a whole bar silent"
(`soloist._free_phrases` capped every breath; `_lines` put a pickup or a landing note into every empty bar;
`piano_vocab._no_empty_bars` re-struck the left hand there; `perform` added pickups / sweeps at the section
boundaries and a landing note in a bar left empty before the head out), a solo slot whose last move overflowed 75 %
into the planned rest, high fill / ornament rates (fill 0.6-0.75 of the gaps), a voicing under nearly every head note
(every quarter counted as strong), one velocity window per part, a pickup into the next phrase at 25 % of the phrase
ends. Fixed by deleting those rules and by data in the owning tools: `soloist.BREATH` (half a bar to two bars after
a phrase, longer after a long line, shorter as the solo builds; the last note rings, no attack), `soloist.CONTRAST`
(a quiet phrase after a 2-bar+ line), `pianist.STYLES` fill 0.2-0.4 / embellish 0.2-0.4 / quick 0.04-0.15 and a fill
only after three plain phrase ends, voicings on beat 1 / 3, held notes and the goal (parallel 3rds / 6ths on about
half the notes between), the left hand's answers density x 0.5, `humanize.touch(levels=)` + `perform.phrase_levels`
(each head phrase its level: the plan's arc + a drawn step, the part's loudest at the plan, the others up to 8 below),
`genres.PHRASE_ENDS` with a 'breath' ending (the landing held, half a bar of silence) and pickups 25 -> 10 %. Measured
by `composer.breath()` over 24 tunes (seeds 100-123, odd seeds swing 0.6) before -> after, the 8 pro songs in brackets
(pro waltz / blues / latenight / bossa, pro2 waltz / blues / latenight / bossa - all use the shared players):
- right hand quiet for a beat+ (share of time) 0.37 -> 0.41 (0.15-0.33 -> 0.16-0.38); the solo 0.41 -> 0.47, the head
  0.34 -> 0.36, the head out 0.35 -> 0.37; both hands 0.19 -> 0.22; r6 003 0.32 -> 0.34 (solo 0.31 -> 0.36)
- rests of a bar+ per 32 bars 3.9 -> 5.3 (0.4-2.8 -> 0.4-5.7), the longest 6.0 -> 8.1 beats; silent solo bars 0 -> 3.2
  per tune (breaths after a phrase; single-note bar runs 1.2 -> 1.6, none over 3)
- attacks per bar: head 3.61 -> 3.35, solo 3.63 -> 3.14 (its spread per bar 2.15 -> 2.21), out 3.81 -> 3.50; r6 003
  solo 5.1 -> 4.3
- ornament notes (onsets < a 16th apart) per 32 bars 8.8 -> 6.3 (r6 003 14.0 -> 2.4); fast figures per tune 3.5 ->
  1.8, per chorus 0.8 -> 0.5; left-hand attacks per bar 2.60 -> 2.48, bars with one LH attack or none 0.40 -> 0.48
- phrase-to-phrase velocity change 8.5 -> 8.9 (r6 003 6.7 -> 8.4); density change 0.57 -> 0.50, register 3.3 -> 3.3
- the r6 003 A/B renders: LRA 8.0 -> 8.6, head LUFS -18.8 -> -20.0 against the solo's -16.8 -> -17.2 (the solo
  builds out of the head), clicks 0; the solo's short-term loudness now dips at every breath.
Blind-test measures moved (24 tunes): clashes 0.29 -> 0.04, chromatic notes 4.8 -> 3.8 per 32 bars, licks recurring
0.17 -> 0.04, block runs 3.4 -> 2.3, dyn range 6.0 -> 6.1, peak_x 0.72 -> 0.72. Watch: the double-time burst got
short (16th bars per tune 1.04 -> 0.25), the solo's last chorus the loudest 0.96 -> 0.88 of the tunes, its top
velocity over the head +8.6 -> +11.0 (the head breathes down) at density 1.01 -> 0.95 (round 1's "velocity plateau"
pattern - watch it in a next round), chord tones in one direction 5+ 0.08 -> 0.27 per 32 bars. The head's DENSITY is
still one level per 2-bar unit (the composer's cells): the next lever (TODO "Piano breath").

## Round 6 prepared (the r7 renders in `songs/_endless_jazz_piano/out/r7`, packets seed `blind-jazz-piano-v7`)

After the breath / body / endless-piano / jazz follow-ups. Composed side: the four agent-composed pro2 songs
(waltz, blues, latenight, bossa; re-rendered, LRA 6.9 / 5.6 / 6.6 / 7.5, clicks 0; `song.py --leadsheet` rewrote
leadsheet.txt / tune.json). Generated side: the same slots and pins as r6 (seed 105 'bright' waltz, seed 100 'blue'
unpinned, seed 106 'late-night' swing 0.6 straight AABA, seed 202 its set-plan bossa) through
`endless.run.render_tune` with the current code (LRA 11.3 / 8.7 / 13.5 / 10.1, clicks 0). The packets now give the
section loudness relative to the piece's integrated loudness (the master gain is a mixing choice: the composed songs
landed 1-4 LU louder). Known musical differences left in: the generated tunes' wider loudness range and quieter
intro / tag / ending (-5..-12 LU vs -2..-5), the composed swing ratio 0.58 against the generated 0.60.

## Round 6 (2026-10-10, current players vs the four pro2 references; 3 composer judges + pianist + statistician)

| Judge lens | Correct | Confidence |
|---|---|---|
| composer A | 8/8 | 78-88 |
| composer B (arranger) | 8/8 | 70-85 |
| composer C (teacher) | 8/8 | 70-85 |
| pianist | 8/8 | 78-88 |
| statistician | 8/8 | 75-85 |

The stronger pro2 references (hand-written heads and solos per recipes/jazz-composition.md) reopened the gap, and the
breath fix (after the user's "endless monotone line") overshot. Unanimous tells:
1. Solos fall apart: whole silent RH bars every 3-4 bars (4-10 per solo), 2.5 attacks/bar - LESS than the head - vs
   4.3-6.2 in the references with no empty bar. Breath belongs to phrase ends (1-2 beats inside a chorus, at most one
   silent bar per chorus, never at a cadence/turnaround); solo density >= 1.3x the head; phrases 2-4 bars of mostly
   8ths starting on upbeats.
2. The form fades: head-out 1.7-2.4 LU under the head, tag/ending 6-12 LU under the piece, final notes v16-40, notes
   after the final chord. References: head-out at head level, ending 2-5 LU down, LRA 5.6-7.5 (generated 8.7-13.5).
3. No climax ladder: the peak in the head-out, the ending flourish or at 58 %; references put the piece's highest
   note in the solo's last 8-16 bars at 60-72 %, a 3rd-6th above the head's peak, v>=110, approached by a rising line.
4. Heads without a hook: chord tones placed bar by bar inside a 5th/6th (A4-E5) at low velocity; references: one cell
   + sequence along the root motion (chromatic or diatonic), a contour per 8 bars peaking a 6th+ up, A1/A2 endings
   differ, register centre ~G5-C6.
5. Melody ignores the reharms (colour tones #11/b9/13 on substitutes); charts identical across choruses.
6. Cells looped at the same pitch over changing chords (6x); a verbatim head quote then silence.
7. LH: bare roots x4/x6 per bar, a fixed "rest every second bar", switching 6<->1 attacks at section boundaries.
8. Intros/tags: a single held note over 4 changing chords, pads; references state the motif and reprise it.
9. Spelling: flat-side chords with sharps in sharp keys (A#maj7#11 in D, A# in Gm6); "shuffle, straight 8ths" header.

The statistician (also 8/8) added measured targets: solo phrase length 5.0-8.7 beats with a near-constant spread
(composed 12.5-46, heavy-tailed); direction changes per step 0.51-0.61 (0.30-0.42), leaps of 5+ semitones 18-27 %
(7-15 %), repeated pitches 4-11 % (0-3 %); empty solo bars on a grid (0); the right hand's p10 velocity 35-37 (47-52);
a left hand on a fixed pulse instead of a dialogue; two shared gestures - a turn into the head out's last note and one
rolled final-chord stagger in every piece.

## After round 6 (fix/endless-r6; the r8 renders in `songs/_endless_jazz_piano/out/r8`, packets seed `blind-jazz-piano-v8`)

BALANCE, not revert: the user's breath A/B ("b sounds better") and letters-to-the-morning's dynamics stay the goal -
the head keeps its phrase-end rests, the body model is untouched; what changed is where silence and softness were
applied by rule. Every fix is data or a budget in the owning tool. 24 tunes (seeds 100-123, odd ones swing 0.6), the
round-6 code -> now (the same measures, `composer._tells_r6`), the pro2 references in brackets (waltz / blues /
latenight / bossa):
1. Solo continuity (`soloist.PHRASES` heavy-tailed phrases - a 1-bar fragment to an 8-bar line, a 16+-beat line per
   ~40 beats, 60 % of the starts off the beat -, `soloist.BREATH` a beat or two (x bpb / 4), a bar at most once per ~96
   beats after a line and across a 4-bar start, `CONTRAST` register and touch instead of density x 0.6; a move fills
   its slot: `piano_vocab._line_on`, a resolution coming down as a line and holding its target a bar at most): solo
   attacks per bar 3.16 -> 4.78 (4.30 / 6.17 / 4.81 / 4.94), solo / head 1.08 -> 1.64 (1.16-1.48), silent solo bars
   per chorus 3.41 -> 1.24 (most 3.5 -> 1.3; 1 / 0 / 0 / 0), of them in a part's last 2 bars 0.79 -> 0.17 (0), bars
   neither hand strikes 0.62 -> 0.25 (0), solo time without a new attack for a beat+ 0.47 -> 0.29 (0.10-0.24); phrase
   length 5.4 -> 11.1 beats (29.8 / 46.3 / 12.1 / 19.1), its spread 2.3 -> 6.8 (8-52), the longest 9.6 -> 22.6
   (26-120), choruses with a 16+-beat line 0 -> 0.88 (1 / 0.33 / 1 / 1), starts off the beat 0.55 -> 0.64 (0.5-0.89),
   8th steps 0.57 -> 0.67 (0.69-0.76). The line (`soloist.RUNS` 6-9-note runs, the lean from the side the line comes
   from, no repeat into a target, `motif_line` chaining on, `MOTIVIC` 0.65 -> 0.45): direction changes per step 0.57
   -> 0.39 (0.31-0.41), leaps 5+ 0.23 -> 0.16 (0.03-0.07: the hook cells' own leaps), repeated pitches 0.04 -> 0.01
   (0-0.01); the right hand's p10 velocity 37 -> 48 (52-57).
2. The form keeps its level (`genres._JAZZ_DYN` mp / mp-mf / mf-mp / mf-mp / mp instead of p ... pp, the head out's
   touch drop 0, the last part -1 / -3 instead of -5 / -11, intro / tag touch -8 / -14 and -6 / -12 instead of -14 /
   -22 and -14 / -24; `perform._ending`: nothing after the final chord, its notes under the peak): the head out over
   the head +0.55 -> +0.49 dB of note energy, the tag + ending under the body -6.8 -> -4.1 dB (-2.7..-4.7), the final
   chord's softest note v30 -> v40 (46-48), attacks after it 0.79 -> 0.17 (0-2), the note-energy range 8.8 -> 7.6 dB
   (4.8-6.7). The r8 renders: LRA 7.8 / 7.6 / 9.8 / 8.2 LU (r7 11.3 / 8.7 / 13.5 / 10.1; pro2 6.9 / 5.6 / 6.6 / 7.5),
   head out vs head -0.8 / -0.5 / +0.2 / 0.0 LU, ending -5.0 / -3.0 / -4.3 / -3.7 LU under the piece (r7 -12.5 / -8.2
   / -10.3 / -8.7; pro2 -3.9 / -2.2 / -4.0 / -5.2), clicks 0.
3. The climax ladder (`perform.CLIMAX` / `_peak_solo`: the solo's highest note in its last 16..2 bars, 4-6 over the
   head's top, v110-118; every solo arc but trading climbs to a climax stage and resolves; the double-time burst before
   it; 'late' no longer peaks in the head out, the shout rare: weight 0.25 -> 0.08): the highest note in the solo's last
   16 bars 0.33 -> 0.88 of the tunes (the rest are shout plans; 1 / 1 / 1 / 1), over the head's top +2.2 -> +3.8 (2-3),
   at v102 -> v112 (96-124), nothing after it as high 0.67 -> 1.0 (1), at 0.77 -> 0.69 of the piece (0.66-0.73).
4. Heads (`melody` register Bb4-Eb6 around A5, peak F6 instead of G4-Bb5 / Eb5 / Db6; the A's contours a 6th+;
   `melody['hook_seq']` 0.55: the hook a 1-bar cell and its sequence along the root motion, `composer._sequenced`;
   the touch target -14..+3 -> -8..+8): the head's median pitch 72.8 -> 77.2 (78-79), its range 10.6 -> 11.1 (10-14),
   its mean top velocity 53 -> 64 (68-75), the 8-bar climb 7.5 -> 8.0 semitones (3.5-10), the A's range 11.6 -> 12.6
   (13-18); A1 / A2 endings differ as before (1).
5. Reharms (`plan['solo']['reharm']` 0.5 -> 0.75; `composer._new_note`: the note struck with the substitute moved
   to its colour - a tension, #11 on a dominant sub - the first that keeps the melody rules): the head out's
   substitutes met by a colour tone 0.11 -> 0.61.
6. Literal cell loops over changing chords: none found by a 2-6-note detector before or after (the r7 "6x" were
   trill / turn alternations and the voicings-only intro's held top); hook quotes stay at two.
7. Left hand (`lh_plan`: the ballad's body in tenths / shells / rootless voicings / walking 10ths, broken 8ths only in
   its intro / tag; `pianist.LH_RESTRIKE`: a 2-bar chord struck again where the right hand is sparse): bars of 4+
   single bass notes 5.2 -> 0.08 (0), struck / empty alternation 3.2 -> 2.8 bars (0-3), 4+-attack jumps at boundaries
   1.33 -> 0.04 (0).
8. Intros / tags: the voicings-only intro line deleted (`INTRO_LINES` augment / fragment / answer), the frame's line
   kept under the head's top: one top pitch over the frame's chords 2.8 -> 2.7 chords (1-2).
9. Spelling: `theory.spell_note` (a note by its degree over the key / the chord); the packets spell chords and notes
   by degree (Bbmaj7#11 in D, F# in D7b9) and label the 'shuffle' feel "medium blues, bar-piano groove".
Statistician's gestures: a clip's last note is never ornamented (the turn into the head out's last note: 0.08 -> 0.04
quick 4-attack groups there), the final roll's stagger drawn per piece (`perform.END_ROLL`), the plink struck with the
chord, the fade's hook played into it.
The user's breathing win kept: the head's 4-bar phrase ends with a rest of a beat+ 0.70 -> 0.75 (0.50-0.88), the head
quiet for a beat+ 0.43 -> 0.42 (0.17-0.43), phrase-to-phrase velocity change 8.2 -> 9.5, the body coupling 0.44 ->
0.42 (heard 0.25 -> 0.28).
Regressions checked (rounds 1-5, 24 tunes): wraps 0, verbatim repeats 0, isolated reharms 0, intro / tag copies 0,
clashes 0.17 -> 0.12, head 5-gram 0.24 -> 0.23, cell_max 0.26 -> 0.24, circling 0.26 -> 0.27, solo entropy 2.18 ->
1.72 (pro2 1.45-1.61), on / off-beat velocity 2.4 -> 1.3, zig-zag 0.49 -> 0.44, ornaments per 32 bars 5.7 -> 6.6.
Watch: beats on chord tones 0.86 -> 0.92 (pro2 0.69-0.81: the direction-keeping lean rarely applies), reversing
4-note cells 0 -> 0.78 per 32 bars (pro2 0-0.89), chord tones 5+ one way 0.19 -> 1.16 (1-3.6), chromatic top notes
3.6 -> 8.8 per 32 bars (2.4-20.6; unresolved 1.8 -> 2.4), licks recurring 0 -> 0.29, quarter runs 0 -> 0.21, head
guide tones 0.32 -> 0.28, hook statements in the frame 0.96 -> 0.75, the head still under the references' touch
(64 vs 68-75) and register (77 vs 78-79).

## Round 7 (2026-10-10, r8 tunes after the round-6 fixes vs the re-rendered pro2 references)

| Judge lens | Correct | Confidence |
|---|---|---|
| composer A | 5/8 | 50-70 |
| composer B | 5/8 | 55-70 |
| composer C (teacher) | 7/8 | 55-68 |
| statistician | 8/8 | 57-68 |
| pianist | 0/8 (fully inverted) | 55-62 |

Composers 17/24 (71 %, round 6: 100 %); all five 25/40 (62 %). The statistician still separates, but says most strong
features are shared by all eight (one form template, the peak at 64-72 %, the solo opening with a head quote, the
last chorus's reharm carried into the head-out); the pianist read the generated tunes as the composed ones. Remaining
tells named by the composers: the last solo chorus's reharm stamped into the head-out (but two references do it too);
licks repeated within 4 bars (a chromatic D-Eb-F-F#-G cell 4x); bossa solos in 16ths for 7 bars; heads that pad with
one-note bars every other bar and don't grow from one cell; a bridge without its own idea (empty bars); the head
quoted verbatim in the solo; a velocity step into the climax instead of a ladder; solo velocity following pitch on
74-84 % of steps (all eight); the left hand louder than the melody in places; shared skeleton (section lengths, the
head-out = second half, the peak always at 64-72 %, the tag = intro reprise, 6/9 endings).
