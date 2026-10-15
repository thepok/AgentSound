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

## After round 7 (fix/endless-r7; the r9 renders in `songs/_endless_jazz_piano/out/r9`, packets seed `blind-jazz-piano-v9`)

Every tell is now a budget or a drawn distribution in the plan data, never an always / never rule (earlier fixes
overshot). Measured by the new `composer._tells_r7` (in `tells()` and the score). There are 24 tunes (seeds 100-123,
odd seeds swing 0.6), compared before -> after. The pro2 references are in brackets (waltz / blues / latenight /
bossa):
1. Licks within 4 bars (`soloist.LICKS` + `fresh()`: a shared ledger over `budget.Budget`. A line is redrawn, up to 4
   tries, when its 5-note cells sounded in the last 4 bars; `target_line` / `motif_line` / `m_run` go through it).
   5-note licks recurring within 4 bars, per 32 solo bars: 0.45 -> 0.12 (0 / 0 / 0 / 2).
2. 16ths per feel (`sixteenths` per feel in `genres`: one 16th line per `every` bars, at most `bars` long. Ballad
   4 / 2, straight 8 / 1.5, bossa 16 / 1, waltz 8 / 2, shuffle 8 / 1. Applied in `piano_vocab._grid`, with the burst
   cut short and continued in 8ths). The longest run of 16th solo bars: 0.75 -> 0.33, max 5 -> 2 (0). The share of
   16th bars: 0.028 -> 0.012.
3. Heads grow from one cell (`melody['half_cell']` 0.6: an A's half cadence states the hook cell's first bar, then
   lands. A 'tail' ending: the landing, then two notes stepping away. The jazz 'long' cells have two attacks a bar.
   `melody['pads']` 0.125: `_style_issues` flags one-note bars outside the landings beyond that budget).
   - One-note head bars: 0.23 -> 0.18 (0-0.19).
   - The longest one-note / busy alternation: 5.7 -> 4.6 bars (0-7).
4. The bridge's own idea (its counter cell sequenced with `hook_seq`; its return varied by
   `melody['bridge_return']`, mostly displaced). One-note bridge bars: 0.28 -> 0.15 (0-0.25).
5. Quotes (`plan['solo']['opening']`: motif 0.25 / fragment 0.4 / line 0.35; `quotes` 0: 0.6, 1: 0.3, 2: 0.1).
   - The hook in the solo's first two bars: 20 -> 4 of 24 (0).
   - Verbatim 6-attack head windows in the solo: 0.21 -> 0.08 (0).
   - Hook quotes: 0.42 -> 0.08.
6. Touch:
   - `soloist.RUN_TOUCH`: a run swells to a drawn focus (its top / its landing / early), with 0.25 velocity per
     semitone and a ghosted low neighbour. Solo steps whose velocity follows the pitch: 0.83 -> 0.69 (pro2 0.74-0.85;
     the round-7 judge put real players at ~50-60 %).
   - `perform.CLIMAX['ladder']`: the 3 bars before the peak climb to it in 5-9 steps. The largest step into the top:
     20.8 -> 17.4 (10-33).
   - `perform.LH_UNDER`: a body bar's left hand 2-7 under the melody's loudest. Bars where the left hand is louder
     than the melody: 0.033 -> 0.005 (0-0.11).
7. The skeleton, drawn per tune:
   - The head out (`genres.OUT_PARTS`): AABA B-A3 0.55 / the whole form 0.3 / A3 0.15. ABAC A2-C 0.55 / whole
     0.45. Blues 2 choruses 0.6 / 1 0.4. Where it starts in the form: 22 of 24 at the half -> 12 / 9 / 3.
   - The reharm (`plan['solo']['reharm_in']`): in the last solo chorus and the head out 0.55, the head out alone 0.45.
   - The tag (`genres.TAG_FRAMES`): the intro's reprise 0.5 / another vamp 0.25 / the A's turnaround 0.25. Tags on
     the intro's vamp: 24 -> 18 of 24.
   - The end chord (`ENDINGS`): 6/9 and maj9 joined by maj13, maj7#11, 6 and maj9#11 (minor: m9, m11, m69, mMaj9).
     The most common end chord: 11 -> 4 of 24.
   - The climax window (`perform.CLIMAX['window']`, drawn per tune): 16..2 bars before the solo's end 0.5, 10..1
     0.3, 16..7 0.2. The loudest 4 bars at 0.35-0.82 -> 0.30-0.80 of the piece; the highest note at 0.57-0.84 ->
     0.19-0.83.
The score (`genres._SCORE_JAZZ`, new round-7 rows, weight 0.5-1, ranges from the pro2 references): lick_near 0..1,
run16 0..1, head_one 0..0.2, bridge_one 0..0.25, head_quote 0, vel_pitch 0.5..0.85, climb_step 4..24, lh_over 0..0.11.
- vel_pitch is widened below the references because the round-7 judge measured real players lower.
- climb_step's top is 24, under the pro2 bossa's 33: a step that large was the tell.
- Measured with the new table, the 24 tunes score 73.4 -> 71.8. Their mean before the hard cap is 86.0 -> 86.8, and
  hard-capped tunes go from 5 -> 6 (sil_cad 4, both_mid, cell_loop; best-of-8 drops them).
- The pro2 references: 100 / 98.7 / 100 / 98.4.
- Watch: leap5 (0.15, pro2 0.03-0.07) and dyn_range (7.7 dB, 4.8-6.4) are the most frequent losses.
- Waltz solos keep 4-9 silent bars per chorus, which caps 5 of the 7 bright-waltz candidates by sil_cad. This was
  already so before these fixes.
- The waltz 'long' cells changed, and the classical waltz shares them: classical seed 102's metrics moved, score
  100 -> 99.9.
The r9 renders (best-of-8): LRA 8.4 / 8.5 / 10.5 / 7.9 LU, clicks 0 (r8 7.8 / 7.6 / 9.8 / 8.2). The pro2 references
were re-rendered: LRA 6.5 / 5.6 / 6.6 / 7.6, clicks 0.

## Round 8 (2026-10-10, r9 tunes (best-of-8) after the round-7 fixes vs the re-rendered pro2 references)

| Judge lens | Correct | Confidence | Round 7 |
|---|---|---|---|
| composer A (composer / arranger) | 6/8 | 55-72 | 5/8 |
| composer B (pianist-composer) | 8/8 | 55-70 | 5/8 |
| composer C (teacher) | 7/8 | 55-75 | 7/8 |
| statistician | 8/8 | 52-68 | 8/8 |
| pianist | 6/8 | 55-78 | 0/8 |

The composers got 21/24 right (88 %, round 7: 71 %). All five judges got 35/40 right (88 %, round 7: 62 %).
- Misses: the pro2 bossa was called generated once, the blues once. The r9 latenight tune (003, AABA swing) was
  called composed by three of the five judges; its line-cliché head and its recomposed last A read as written.
- The lens prompts were written fresh for this round, so the per-judge numbers are not fully comparable with
  round 7's.
- The round-7 tells were not named again: licks within 4 bars, 16th solos, verbatim head quotes, the head out always
  at the half, the left hand louder than the melody.

The remaining tells:
1. Solos switched, not built (all five judges): near-empty bars early in the solo (r9 002 bar 33, 004 bars 49-50,
   001 bars 123-124 right after the climax run), then 7-10 bars of unbroken 8ths at a flat v90-116. The densities
   per chorus stack as fixed textures.
2. Velocity: the statistician measured velocity following pitch less in the generated solos (r 0.45-0.52) than in
   the composed ones (0.52-0.71). The round-7 fix (`RUN_TOUCH` pitch 0.25) overshot.
3. Chromatic noodling without targets (004 bars 63-64), arpeggio leaps (001: 24 % leaps of 5+, composed 4-7 %), and
   little motif reuse in the solo (3-note interval patterns 0.21-0.26, composed 0.42-0.54).
4. Heads:
   - Guide tones on a fixed dotted-quarter grid (004, 002), repeated pitches (002: Ab5 x3), heads chorded on nearly
     every note (004: 73 %).
   - The waltz head alternates busy and empty / one-note bars (001 bars 10-24).
   - The waltz bridge parks 4 bars per chord (001 bars 25-36: a 4/4 chart doubled).
5. Frames:
   - Two tunes share the same intro progression, Ebmaj9-Ebm6-Cm9-F13 in Bb.
   - The pad skeleton is shared: a dotted half, then a chord on 3 and an empty bar.
   - Tags reprise the intro, and the run-then-roll ending recurs.
   - A shuffle "bar-piano groove" left hand of bare roots four to the bar, and a blues ending on maj9.
6. Charts that repeat unchanged in every chorus (no reharm in the solo when `reharm_in` is 'out').

Fixed after round 8 (cheap ones):
- `piano_vocab._set_piece` / `_crowned`: a figure's landing is held its drawn length, and the slot goes on as a line.
  Before, a fourths cascade's chord was held 7.5 beats.
- `soloist.ANSWER_HOLD` 0.6 bar: a sparse answer line runs long enough that its landing holds 0.6 bar at most.
- `RUN_TOUCH` pitch 0.25 -> 0.5. `_SCORE_JAZZ` vel_pitch is now 0.65-0.85.
- On 24 tunes, silent solo bars per chorus went 1.29 -> 1.13 and vel_pitch 0.69 -> 0.71. On the bright-waltz slot,
  silent bars per chorus went 1-9 -> 3-8. sil_cad tunes went 4 -> 5 of 24, noise at this sample size.
- Tried and dropped: `PHRASES` dense 1.0 -> 0.4. The composed solos' phrases are longer still (ph_max 26-120), so the
  plateau is a touch / texture tell, not phrase length.

# New-age (endless `piano --style new-age` vs letters-to-the-morning + three pro pieces)

The references are songs/letters-to-the-morning and the agent-composed songs/pro-newage-rain ("Glass After Rain",
E minor 68 BPM), songs/pro-newage-hopeful ("First Light Over the Fields", D major 84 BPM, a climax a step up) and
songs/pro-newage-waltz ("Where the Light Lingers", Eb major 3/4). All four use the endless spec's piano band and
players. The packets come from `songs/_blind/make_packets_newage.py`: chart, right hand per bar, every left-hand
attack, analysis. The judge brief is `JUDGE_NEWAGE.md`. Scoring runs through `score_round.py KEY_newage.json DIR`
(the KEY is never read by hand). The 24-seed measure is `measure_newage.py`; `rescore_newage.py` re-scores saved
results with the current table.

## Round N0 (2026-10-10, renders `songs/_endless_piano/out/na_n0`, best-of-8 on)

| Judge | Correct | Confidence |
|---|---|---|
| composer A / B / C | 8/8 each | 64-88 |
| statistician | 8/8 | |
| pianist | 8/8 | |

The composers got 24/24 (100 %). All five judges got 40/40.

Unanimous tells:
1. The climax is B1 copied note for note, only louder and thicker.
2. A4 = A2 and A3 = A1 verbatim, and the last return closes on a plain tonic.
3. One grid in every piece: 4|8|8|8|4|(8)|8|8|8|5.
4. Intro = interlude = coda chord rows, with a stock "Vsus4 - iv6 - I" coda.
5. The final chord's top note sits 1.5-2 octaves over the line and is the piece's highest note.
6. Repeated pitches:
   - The intro, interlude and coda melodies are repeated-pitch scraps.
   - The theme has repeated-note pickups: 14-15 % of melody steps are unisons, against 0-2 % in the references.
7. A narrow harmonic vocabulary:
   - 14-19 chords, against 21-36 in the references.
   - 43-67 % of 4-chord windows reused, against 9-25 %.
   - No secondary dominants and no bVII.
8. A right-hand rest or held-note bar at every phrase end, and no ornaments.
9. A 4+4 chorus with the same answer twice. Clashes (Cb over Dbmaj7, an unresolved A#). The left hand varies only
   its density.

## After N0 (data / distributions; tells measured by `composer.newage_tells`, table `genres._SCORE_NEWAGE`)

The new-age table gets its own rows (the shared `_SCORE_SING` stays as it is for classical and lofi). The breath
ranges are widened from letters alone to all four references.

Changes per tell:

| Tell | Change | Measured as (references) |
|---|---|---|
| 1, 2, 3 | The plan sections draw arrangement options (`perform.ARRANGE_KEYS`) with their own dice: `bars` (a shortened inter / A3 / build), `tail` (a 9-bar A2, a longer climax), `climax` lift / theme (A1 an octave up) / step (+2 with a pivot, `_pivot`), `cadence` (A4 closing on vi / IV), `octave_half`, `bass` walk (`_walk_bass`: slash chords over a stepwise bass) | climax_copy (0), block_copy (0.06-0.24) |
| 4 | Harmony data: `tag_approach` IV / ii / IV_iv, `tag_frames`, `intro_lines` / `tag_lines` with a 'head' kind (the hook's head and its echo) | frame_pitches (9-13) |
| 5 | Plan `end_top: 'line'`: the end chord's top note is the chord tone just over the last melody note | final_jump (0-8), final_top (0) |
| 6 | Melody `repeat` cost (2.5, 1.5) in `_choose`; `_NA_STEPS` | rep_pitch (0.017-0.046) |
| 7 | New blocks: open 'lament', turn 'vi_V2_V' and 'IV_III7_vi_V', hook 'IV_III7', build 'bVII' | chords_n (19-33), chord_rep4 (0.06-0.26) |
| 8 | Plan `ornaments` (turn 0.45, mordent 0.2 per part section); `_NA_ENDS` (fewer whole-bar breaths, pickups) | orn32 (0.4-4.6) |
| 9 | The chorus plays its own left hand: `_NA_FIGURES` 'chorus' (tenths / flow / pulse / color); `pianist.FIGURES` 'pulse' | |

24 seeds (100-123), scored by the new table:

| | Score | Gap to references |
|---|---|---|
| Before | 76.5 sd 3.8 (references 98.3 / 100 / 100 / 99.5) | 23.0 |
| After | 90.3 sd 10.5 | 9.5 |

Metrics:

| Metric | Before | After | References |
|---|---|---|---|
| block_copy | 0.50 | 0.26 | |
| climax_copy | 0.65 | 0.19 | |
| rep_pitch | 0.092 | 0.045 | |
| final_jump | 18.6 | 6.7 | |
| final_top | 0.88 | 0 | |
| frame_pitches | 5.2 | 7.9 | |
| chords_n | 15.2 | 19.5 | |
| chord_rep4 | 0.37 | 0.23 | |
| ret_tonic | 1.0 | 0.25 | |
| orn32 | 0 | 4.3 | |
| quiet1 | 0.38 | 0.36 | 0.25-0.30, still high |

Jazz, classical and lofi are unchanged: seeds 100-105 give the same notes and scores.

## Round r1 (2026-10-10, renders `songs/_endless_piano/out/na_r1`, packets seed `blind-new-age-r1`)

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 8/8 | 62-80 |
| composer B | 8/8 | 62-78 |
| composer C | 8/8 | 60-85 |
| statistician | 8/8 | 80-90 |
| pianist | 6/8 | 60-80 (called two references generated: shared grace-chord blips, the template grid) |

The composers got 24/24 (100 %). All five judges got 38/40 (95 %). Confidence is lower than in N0, and the N0 tells
(copied climax, verbatim returns, chord loops, final-chord top) were not named again.

The tells:
1. The climax is foreign and unprepared (5/5):
   - "sus4, then a bare major chord a step up", then B1 transposed up a tone.
   - The return home has no pivot.
   - The climax line is only +5-7 semitones over A1; the references are +9-14 with the theme an octave up.
2. Whole-bar right-hand rests in the build and at the climax (5/5).
3. Weak-beat chromatic lower neighbours against the chord: G over E, A over Cbmaj7 (5/5).
4. Holds of 4.5-7 beats (5/5):
   - an A2 padded to 9 bars by a held tonic and an empty sus4 bar;
   - the coda's intro cell an octave low with a 5-beat hold.
5. The interlude copies intro bar 3 verbatim (4/5).
6. Narrow, circling themes and near-verbatim A returns (4/5). Measured, the A1 range is 12.1 against 9-17 in the
   references, so this is contour, not range.
7. Smaller points: grace-chord blips (the shared performer: the references have them too); the velocity follows the
   pitch; add9 on any degree; the non-functional coda turns "F#sus4 E Em6".

## After r1 (the r2 renders in `songs/_endless_piano/out/na_r2`)

Changes per tell:

| Tell | Change | Measured as (references) |
|---|---|---|
| 1 | climax {lift 0.15, theme 0.65, step 0.2} (was 0.25 / 0.4 / 0.35). The theme ceiling is now C7. A 'theme' climax strikes its top note once (the others a scale step lower). The step's pivot lands on the new key's V7 (`_re_triad`). Climax tail 0.25 (was 0.4). | climax_lift (9.7-14) |
| 2, 4 | New arrangement option `fill` (`perform._fill`): a bar without a right-hand onset echoes the last bar with 2+ notes on its own chord tones, under the section's peak, and a note held into it is cut. A2 0.9, build 0.9, climax 0.9. | peak_holes (0) |
| 4 | Plan `max_hold` 3.5 beats. The 'head' frame line's echo is cut under a bar, and the tag's echo stays in the home register (no octave-low ending). | long_holds (0) |
| 3 | Genre melody `chromatic` (the half-step approach chance; the default stays 0.3, new-age 0.04) | off_chord32 is only a diagnostic: the references have more off-chord notes (2.7-6.3), so the tell is the mechanical approach, not chromaticism |
| 5 | The interlude draws `octave` {0, +1} | |

24 seeds (100-123):

| | Score | Gap to references |
|---|---|---|
| r1 generator, new table | 86.8 sd 10.3 (best-of-8 gain 5.2 / 9.6 / 7.4) | 12.7 |
| After | 91.7 sd 10.3 (best-of-8 gain 4.7 / 8.9 / 5.3; references 98.5 / 100 / 100 / 99.5) | 7.8 |

Metrics:

| Metric | Before | After | References |
|---|---|---|---|
| climax_lift | 6.8 | 10.0 | 9.7-14 |
| peak_holes | 0.79 | 0.13 | 0 |
| long_holds | 2.5 | 0 | 0 |
| climax_copy | 0.19 | 0.06 | 0 |
| off_chord32 | 2.9 | 0.8 | |

Jazz, classical and lofi: still the same notes and scores (seeds 100-105).

## Round r2 (2026-10-11, renders `songs/_endless_piano/out/na_r2`, packets seed `blind-new-age-r2`)

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 8/8 | 70-80 |
| composer B | 8/8 | 62-80 |
| composer C | 8/8 | 58-76 (BRRX called generated at 58) |
| statistician | 8/8 | 68-85 |
| pianist | 8/8 | 60-82 |

The composers got 24/24 (100 %). All five judges got 40/40, so the round did not improve on r1 (38/40) and the loop
stops here.

None of the r1 tells came back: no long holds, no holes at the peak, no chromatic clashes, no octave-low coda. The
judges found new ones, a layer deeper:
1. The theme is restated rather than developed (5/5):
   - The 'theme' climax is A1 an octave up note for note over the same chords.
   - A4 (and A3) repeat A1, moved only in register or bass.
   - The statistician counted 4-8 of 8 bars copied in A2 / A3 / the climax / A4, against 1-2 in the references.
2. Phrase ends are template slots:
   - A2 and A4 end on one chord held two bars ("X | %").
   - The right hand is empty on every half cadence (bar 4 of each A).
3. The coda's crammed second-to-last bar: "sus4 / IV / iv6" in one bar, the right hand resting, the left hand on bare
   roots (the iv6's 3rd never sounds) (5/5).
4. The 'step' climax: a V7 that resolves deceptively to the new key's VI, a stock relative-major run, then snapping
   home (4/5).
5. Repeated-note filler: a filled tail bar "G4 G4 G4 G4" (the `_fill` echo snapped every note to one chord tone),
   and the build's last bar B4 x4.
6. Smaller points:
   - The same melody rhythm cell in every A.
   - The same ~17 LU loudness budget and velocity p10/p90 41/93 in all four generated pieces.
   - Intro = interlude = coda chord loop.
   - Narrow themes (7-12 semitones; the references 12-15).

## After r2 (data / distributions, not judged - the stop rule; measured over seeds 100-123)

Changes per tell:

| Tell | Change | Measured as (references) |
|---|---|---|
| 1 | A 'theme' climax keeps A1's first half and plays its second half as a sequence of the first, a scale step higher, with beat notes on chord tones and no new unisons (`perform._sequel`). Climax {lift 0.2, theme 0.7, step 0.1}. `fill` drawn on A1 / A3 / A4 (0.5). | a1_copy (0.20-0.29). With the r2 data off vs on: 0.386 -> 0.345 |
| 2 | New arrangement option `turn`: a closing chord held 2+ bars gets ii - V (iiø - V in minor) in its last bar. A2 0.7, A4 0.6. | ret_tonic 0.25 -> 0.08 |
| 3 | Harmony `tag_span` 1.0: the coda's approach chords take a whole bar (two chords, not three in one bar). The tag's line plays the whole head again over it (refitted), so the right hand sings into the end chord. | |
| 4 | 'step' weight 0.2 -> 0.1 | |
| 5 | `_fill` keeps the copied bar's motion: a moving line does not snap into one repeated pitch | |

Score over 24 seeds:

| Table | Generated | Gap to references |
|---|---|---|
| Final | 90.9 sd 10.5 (best-of-8 gain 4.8 / 9.9 / 4.7; references 98.6 / 100 / 100 / 99.6) | 8.7 |
| Final, scoring the r2 generator | 91.7 | 7.8 (that generator lacks the a1_copy metric) |

The whole loop, same 24 seeds:

| Generator | Score | Gap to references |
|---|---|---|
| Before N0 | 76.5 | 23.0 |
| After N0 | 90.3 | |
| r1 generator, r1 table | 86.8 | 12.7 |
| After r2 | 90.9 | 8.7 |

With the old shared table, the generator scored 95.8 against references at 97-100, so the old table barely
separated them.

Tried and dropped: one breath per 8 bars in A / B (`_NA_PHRASES`) and a 'tail' phrase end. quiet1 went 0.35 -> 0.29,
but the fixed-seed arrangement tests broke (the body coupling, a second climax note). quiet1 (0.33-0.35, references
0.25-0.30) and frame_pitches (7, references 9-13) stay open.

Jazz, classical and lofi are unchanged: seeds 100-105 give the same notes and scores, and their baselines were not
regenerated. Note: the lofi baseline's `body_heard` needs AGENTSOUND_SAMPLES set, or the parity test fails
(environment only, also on master).

## Round r3 (2026-10-11, renders `songs/_endless_piano/out/na_r3`, packets seed `blind-new-age-r3`)

The post-r2 generator (`_sequel`, `turn`, `tag_span`, the `_fill` fix), unjudged until now. From this round on the
judges are set up by `songs/_blind/judge_newage.py ROUND DIR` (an isolated folder per judge with JUDGE.md + the
packets, and the brief per lens: 3 composers, a statistician, a pianist - the same prompts every round).

| Judge | Correct | Confidence |
|---|---|---|
| composer A / B / C | 8/8 each | 63-80 |
| statistician | 8/8 | 64-80 |
| pianist | 8/8 | 60-75 |

The composers got 24/24 (100 %), all five judges 40/40: no better than r2.

The tells:
1. The climax is A1's chord chart cell for cell (8/8), its melody A1 an octave up in chords (5/5, all 4 pieces).
2. Two pieces in E major drew the same chorus chart (IV V iii vi IV V/3 iv6 Vsus4-V), with rests in the same slots.
3. A2 / A4 restate A1's first 4-6 bars note for note; the theme a short cell that never develops.
4. A 9-bar A2 padded "I | I | Vsus4" whose filled tail bars repeat one figure three times.
5. The statistician: within-phrase dynamics 6.4-7.0 dB against 8.7-9.6 in the references; the climax -> A4 cliff.
6. The intro cell replayed by the interlude and the coda; a sus4 -> V cadence every 4 bars.

## After r3 (the r4 renders in `songs/_endless_piano/out/na_r4`)

| Tell | Change | Measured as (references) |
|---|---|---|
| 1 | New arrangement option `reharm` {share: weight} (climax {0: 0.05, 0.7: 0.45, 1.0: 0.5}): `perform._reharm` swaps that share of the section's chords (not the last bar, not a sus4) for a substitute of its degree - harmony data `reharm` {mode: {'VIm': {'IVmaj7': 1, 'III7@3': 0.8, ...}}} - drawn among those the melody sings over (every note on a beat / held a beat+ a chord tone or tension), never on a neighbour's root | climax_chart (0-0.5): 0.98 -> 0.39 |
| 2 | Hook bank: 3 more major, 2 more minor chorus blocks | |
| 3 | Melody `restate` {2: 0.7, 1: 0.3}: a later A restates 1-2 two-bar units of A1, not 3 (composer `copied`) | a1_copy (0.20-0.29): 0.345 -> 0.28 |
| 4 | `_fill`: an echo of an echo falls a step (no 3-bar vamp) | |
| 5 | Plan `swell` {0: 0.3, 1: 0.6, 2: 0.1}: a hairpin per 4-bar phrase of a part section - marks at its start, its highest note (levels up) and its end (`perform._swell`) | ph_vspread (23.1-24.8): 21.0 -> 24.3 |
| TODO | Plan `touch_span`: the tune's touch window moved per tune (its own loudness budget) | |
| TODO | Plan `candidate_tries` 2: best-of-8 replaces arc-check rejects from up to 16 seeds (run.seeds_for); the build's contour starts higher (C 'climb' / 'wave') - arc rejects 24/40 -> 13/40 | the r3 log: best of 3-7, now best of 8 |

## Round r4 (2026-10-11, renders `songs/_endless_piano/out/na_r4`, packets seed `blind-new-age-r4`)

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 8/8 | 55-80 |
| composer B | 8/8 | 62-75 |
| composer C | 8/8 | 65-80 |
| statistician | 5/8 | 55-68 (a composed piece called generated twice, a generated one composed: "the highest rhythm-cell variety of the set") |
| pianist | 8/8 | 58-74 |

The composers got 24/24 (100 %), all five 37/40 (92 %, r3 100 %). The climax chart and the copied A returns were not
named; the climax melody (the theme an octave up) still was.

The tells:
1. Dynamics dropped onto notes: the chorus jumping v64 -> v111 in two bars, louder than the climax; the build at a flat
   ff in the middle register (the uncapped swells over a mf / f section).
2. Narrow themes of neighbour oscillation (D-C-D-C); the climax the theme 8va over a static reharm (C/E three times).
3. The coda loops the head's 2-bar cell twice (5, 6, 5, 6); intro / interlude two long notes.
4. The 9-bar A2 template, a chorus repeating its first two bars.

## After r4 (the r5 renders in `songs/_endless_piano/out/na_r5`)

| Tell | Change | Measured as (references) |
|---|---|---|
| 1 | A swell never passes the section's own loudest mark (a quiet section up to mp); the build's dynamics mp -> mf (was mp -> f) | vel_jump12 (0.18-0.29): 0.27 |
| 2 | `_reharm`: no substitute a third time in the section | |
| 3 | Harmony `tag_lines` head 0.35 / augment 0.35 / answer 0.3 (head 0.6); `intro_lines` head 0.6 / answer 0.4 (no augmented two-note line); the intro's 'head' echo sings the whole head a third up | |
| 4 | A2 `tail` 0.25 (0.4) | |

The neighbour-oscillation tell was measured (top-line a-b-a triples): the generated 0.18, the references 0.10-0.19 -
not a difference in the notes, so it stays unfixed.

## Round r5 (2026-10-11, renders `songs/_endless_piano/out/na_r5`, packets seed `blind-new-age-r5`)

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 7/8 | 55-85 (called 005-before-the-sea composed, 55) |
| composer B | 8/8 | 55-82 |
| composer C | 8/8 | 55-80 |
| statistician | 7/8 | 60-80 (a composed piece called generated) |
| pianist | 7/8 | 55-80 (called 005-before-the-sea composed, 55) |

The composers got 23/24 (96 %) - their first miss in the new-age loop -, all five 37/40 (92 %). The loop stops here
(three rounds this run).

The tells left (next):
1. The theme: narrow (a 4th-6th), circling neighbour tones, its head on non-chord tones (G over Dm), scale runs.
2. The climax is still the theme an octave up in chords ("new chords, no new melodic idea").
3. The 9-bar A2 "I | % | Vsus4" tail (3 of 4 pieces), a lone held note in the chorus's 4th bar (all 4).
4. Frames: intro / interlude a held note + a pickup at the same positions in every piece, the interlude's notes on
   odd beats (4.92), the coda whole notes, the coda chords = the intro's.
5. Spelling / chromatic slips: Fb over Ab, A against Cb in Gbm6.

## The score over this run (24 seeds 100-123, the final table)

| Generator | Score | Gap to the references (98.7 / 99.8 / 100 / 99.6) |
|---|---|---|
| r3 (post-r2) | 87.6 sd 10.1, min 43.1 (best-of-8 gain 5.8 / 8.7 / 3.5) | 11.9 |
| final (r5) | 94.3 sd 1.6, min 91.6 (best-of-8 gain 1.5 / 2.2 / 2.5) | 5.2 |

| Metric | r3 | final | References |
|---|---|---|---|
| climax_chart | 0.98 | 0.40 | 0-0.5 |
| a1_copy | 0.345 | 0.283 | 0.20-0.29 |
| ph_vspread | 21.0 | 23.0 | 23.1-24.8 |
| vel_jump12 | 0.22 | 0.27 | 0.18-0.29 |
| chords_n | 19.1 | 20.4 | 19-33 |
| quiet1 | 0.34 | 0.34 | 0.25-0.30 (open) |
| frame_pitches | 7.0 | 7.0 | 9-13 (open) |

Jazz, classical and lofi are unchanged: seeds 100-105 give the same notes and scores (a digest of every track's notes
against HEAD's package); only the new-age baseline entry was regenerated.

## Reference set 2 (2026-10-12, eight more hand-written pieces; not judged yet)

Written against every tell above (each `songs/pro-newage-*/NOTES.md`), same band / players as the old three, built
with the Salamander grand (a worktree needs `AGENTSOUND_SAMPLES`, or the piano falls back to the GM SoundFont):

| piece | mood | key / mode | meter, tempo | form | climax at | score |
|---|---|---|---|---|---|---|
| skylight | rain | F minor | 6/8, q 63 | ternary, climax before the return | 0.55 | 96.4 |
| morning | morning | G major, Lydian | 4/4, 76 | theme + 5 variations, no intro | 0.65 | 91.4 |
| longing | longing | B minor | 3/4, 72 | A A' B, climax then fragments | 0.86 | 95.5 |
| lantern | hopeful | Ab major | 4/4, 88 | rondo, climax in an episode (E major) | 0.68 | 97.9 |
| tide | flowing | D Dorian | 6/8, q 84 | arch A B C B' A', hemiola climax | 0.55 | 97.3 |
| snowfield | still | E major | 3/4, 60 | through-composed, early soft climax | 0.47 | 84.5 |
| homecoming | nostalgic | Eb -> Gb major | 4/4, 66 | AABA, the climax modulates | 0.76 | 95.3 |
| embers | elegy | C minor | 4/4, 58 | passacaglia (8-bar ground x 7) | 0.80 | 96.2 |

`measure_newage.py --set2` over seeds 100-123: generated 94.3 sd 1.6; the old four 98.7-100 (mean 99.5); **set 2
84.5-97.9, mean 94.3 - the same as the generator**. The table describes the old three, not "composed": every set-2
point lost is a range drawn from them. Ranges set 2 widens (old refs -> set 2; generator mean):

| metric | table | old | set 2 | generator | reading |
|---|---|---|---|---|---|
| climax_x / peak_x | 0.6-0.85 | 0.71-0.77 | 0.47-0.86 | 0.78 | placement is a style choice; reward the set's spread, not a window |
| climax_lift | 8-16 | 9.7-14 | 1.6-14.9 | 10.0 | a climax that is a key change / hemiola / swell lifts 4-8 |
| att_cv4 | 0.08-0.25 | 0.10-0.17 | 0.15-0.36 | 0.15 | variations and passacaglias change density per section |
| ph_vel | 8-13 | 9.6-11.2 | 8.4-15.9 | 10.8 | |
| frame_pitches | 8-16 | 9-13 | 5-16 | 7.0 | no intro (3 pieces) or fragment frames: no longer separates |
| rest_bar | 0.5-3 | 0.67-2.4 | 0-5.1 | 3.0 | |
| quiet1 / long_share | 0.22-0.33 / 0.15-0.28 | | 0.20-0.32 / 0.12-0.26 | 0.34 / 0.22 | 6/8 dotted quarters read as "no breath" |
| ret_tonic | 0 | 0 | 0-1 | 0.08 | a rondo goes home; also blind to modulation (Ebm in Gb = 1) |
| climax_chart | 0-0.5 | 0-0.5 | 0-0.62 | 0.40 | variations share the harmony by design |
| vel_jump12 | 0-0.27 | 0.18-0.29 | 0.17-0.36 | 0.27 | |

Where set 2 sharpens the gap instead (the generator outside every hand-written piece): **block_copy** set 2 0-0.07 vs
generated 0.22; **a1_copy** 0-0.17 vs 0.28; **chords_n** 25-33 vs 20.4; **chord_rep4** 0-0.18 vs 0.17 (old 0.06-0.26);
quiet1 0.20-0.32 vs 0.34. Those are the restating / small-vocabulary tells of rounds r2-r5, still open.

Metric artefacts found on the way: phrase_rests counts a phrase's first downbeat played a few ms early as the old
phrase's last note (homecoming 0.64 with a breath at most boundaries); a pickup 8th after a 1.5-beat rest counts as
no breath. None of the 8 maps faithfully onto an endless Tune / learn.tokens today: the trained vocabulary has Form
verse / AABA / ABAC / blues, Mode major / minor, one key per piece, no sus2; the section plan, its lengths, the
left-hand figures, dynamics and tempo are regenerated by the players, not tokens. The lead-sheet layer (chords as
roman numerals, melody on the 1/12 grid, Meter 3 / 4) would encode; the forms would not. Set 2 is a target for the
notes-level score and the judges, not training data for the lead-sheet student (that needs the arrangement plan as
tokens, docs/LEARNED_GENERATOR.md next step 1).

## After r5: set variety and the twelve references (2026-10-12)

HUMAN_FEEDBACK 2026-10-12 ("nicht sehr abwechslungsreich") and the learned generator's finding (every teacher climax
in part C bar 4-5 at 87-91 % of the head, on C6 / B5): the set now varies as data, not by a second system.

| Change | Where |
|---|---|
| Set draws per slot, never the slot before's, pinned for the slot's best-of-N: `layout` (song / chorus / return), `climax` kind (theme / climb / lift / step), `shift` (-3..+3 semitones: the register and the climax pitch) | `plan['set']`, `composer.set_draws`, `set_plan`; `compose` draws them itself without a plan (the teacher export), `Tune.arrange` |
| Layouts: the sections a layout plays (`'layouts'`), chorus = the hook right after A1, return = climax, interlude, the theme's return (ternary, like the waltz reference) | section key `layouts` |
| A 3/4 waltz feel (84-104 BPM, the form doubled: `plan['form_bars']`), its own cells (`song3`), phrase plans and figures | `CELLS['song3']`, `_NA_WALTZ_PHRASES`, `_NA_WALTZ_FIGURES` |
| The head's climax part drawn per tune (build 1.0 / chorus 0.8) | melody `climax_parts` |
| A chorus's inner half cadence may run on as a line (0.4) | melody `half_line` |
| A hook statement's first 3 notes stay chord tones | melody `plain_head` |
| 'climb' climax: the chorus an octave up, developed (`_sequel`) | `perform._arrange` |
| Frames: intro lines head / answer / fragment, tag lines incl. augment, endings add9 / plain / maj9 / 6 / maj7 (minor madd9 / m / m9 / m7), coda frame vamp / turnaround / reprise, the intro's left hand alone 0-2 bars (drawn) | harmony, section `lh_only` |
| The score table from the 12 references (letters + 3 + set 2): climax_x / peak_x 0.47-0.86, climax_lift 1.6-15, att_cv4 to 0.36, ph_vel to 15.9, rest_bar 0-5.1, frame_pitches 5-16, climax_chart to 0.62, ret_tonic 0-1, block_copy 0-0.24, a1_copy 0-0.29, chords_n 19-33 ... (weights unchanged) | `_SCORE_NEWAGE.update` |

Set variety (`songs/_blind/variety_newage.py`, headline `learn.evaluate.variety` over seeds 100-123; the set = a set
plan of 24 slots, best of 8 each):

| | teacher before | teacher after | set before | set after |
|---|---|---|---|---|
| learn.evaluate.variety | 0.679 | **0.852** | 0.689 | **0.853** |
| climax_pos | 0.00 (bar 4: 100 %) | 0.66 | 0.00 | 0.56 |
| climax_pitch | 0.27 | 0.71 | 0.27 | 0.77 |
| ending | 0.57 | 0.75 | 0.61 | 0.85 |
| feel / meter | 3 feels, 4/4 only | 4 feels, 3/4 in 21 % | 3, 4/4 only | 4, 3/4 in 25 % |
| layout / climax kind / shift (effective counts) | 1 / 1 / 1 | 2.6 / 2.7 / 5.7 | 1 / 1 / 1 | 2.9 / 2.9 / 6.4 |
| climax_x mean, sd | 0.78, 0.02 | 0.75, 0.03 | 0.78, 0.01 | 0.75, 0.03 |

climax_x still sits in 0.70-0.80 (the references 0.47-0.86): the climax place moves between parts, not across the
piece - a layout with an early climax (set 2's skylight / snowfield / tide) is the next step.

## Round r6 (2026-10-12, renders `songs/_endless_piano/out/na_r6`, packets seed `blind-new-age-r6`)

Composed side from now on: letters-to-the-morning, pro-newage-waltz, -lantern, -homecoming (two of set 2). The four
generated pieces (001, 003, 005, 007 - by chance all four the 'return' layout) vs them:

| Judge | Correct | Confidence |
|---|---|---|
| composer A / B / C | 8/8 each | 55-86 |
| statistician | 8/8 | 68-88 |
| pianist | 8/8 | 60-85 |

40/40. The tells: the same section skeleton in every piece (the waltz its doubling), the interlude = the intro's first
two bars at -9..-12 LU (a cut-off), the climax = A1 / B1 an octave up with +2 chords under every note, A3 = A1 note
for note and its octave_half dropping back mid-phrase, the coda's split bar 'Vsus4 | ii Vsus4', the waltz's 'X | %'
two-bar harmonic rhythm.

## After r6 (the r7 renders in `songs/_endless_piano/out/na_r7`)

| Tell | Change |
|---|---|
| +2 chords under every climax note | section `harm_share`: the climax harmonizes 45 % of its long notes |
| interlude = intro bars 1-2, a cut-off | the interlude plays the intro's half cadence (bars 3-4), p instead of pp; coda (p, pp); A3 / A4 (mp, p) |
| A3 = A1, octave_half breaking the phrase | A3 / A4 high or low throughout (`octave`), A3 a half return (0-4 + 6-8) in 55 % |
| the coda's split bar | `composer.frame`: the approach takes the whole held chord when it returns to its root |
| waltz 'X | %' | waltz bars split, the later bar over its 3rd / 5th (r7: replaced again, below) |
| build quieter than B1 | build (mp, f) |

## Round r7 (2026-10-12, renders `songs/_endless_piano/out/na_r7`, packets seed `blind-new-age-r7`)

Generated 002 (song / step), 003 (chorus / theme), 006 (return / lift), 007 (waltz, chorus / climb):

| Judge | Correct | Confidence |
|---|---|---|
| composer A / B / C | 7/8 each (each called one composed piece generated) | 55-80 |
| statistician | 6/8 (two composed called generated) | 60-80 |
| pianist | 7/8 | 58-72 |

Composers 21/24 (88 %), all 34/40 (85 %). Every generated piece still caught. Tells: every 8-bar unit closes 'Vsus4 V'
(no authentic cadence until the end); the waltz's 'X | X/3rd' in every pair (a slot rule); C#, D#, F# over E in A
minor (E's own major scale); the step climax lurches into a key a step up; a 'lift' climax staying under the build;
section names 'A4 with no A3' in the packets; the neighbour-note cell restated in every A.

## After r7 (the r8 renders in `songs/_endless_piano/out/na_r8`)

| Tell | Change |
|---|---|
| 'Vsus4 V' closing every unit | harmony blocks: half the sus4 cadences now V alone, ii7 V, IV V, iv7 V, two hooks end on I |
| waltz 'X | X/3rd' | `perform._moving_bass`: each later bar drawn held 0.3 / its bass moved 0.35 / a substitute under the melody 0.35 (`_reharm(only=)`) |
| E's major scale over E in A minor | `composer.RaisedPcs`, melody `raised_v`: a plain major triad over the key's minor 3rd takes the key's scale with the raised 3rd (new-age only; classical / organ would change, so opt-in) |
| the step climax's lurch | set climax step 0.1 (0.3), lift 0.5 |
| a lift climax under the build | lift: the line an octave up when it fits under G6 |
| a turn re-striking the climax note | ornaments never on a note whose upper neighbour reaches the piece's peak |
| 'A4 with no A3' | `make_packets_newage.py` numbers the A sections in playing order (a label, not the music) |

## Round r8 (2026-10-12, renders `songs/_endless_piano/out/na_r8`, packets seed `blind-new-age-r8`)

Generated 002 (return / lift), 005 (chorus / theme), 006 (song / climb, minor), 007 (waltz, return / theme):

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 5/8 (called 005 and 007 composed) | 55-72 |
| composer B | 6/8 (two composed called generated) | 55-75 |
| composer C | 6/8 (called 005 composed) | 55-65 |
| statistician | 6/8 (called 007 composed) | 55-75 |
| pianist | 5/8 (called 005 and 006 composed) | 52-72 |

Composers 17/24 (71 %), all 28/40 (70 %): r6 100 % -> r7 88 % -> r8 71 %. Five times a generated piece was called
composed (005 three times: "the climax restates the hook an octave up and extends it to a new peak", "a borrowed Cm6
planted in the chorus and recalled in the coda"). The loop stops here (r8, the brief's last round).

The tells left (next):
1. The theme: static (circling a 3rd-4th, two attacks a bar), single-note bars and dead space; A3 still A1 / A2 note
   for note in most pieces (only the bass or the octave differs).
2. The climax: either unrelated new chord-tone gestures or a paste of A1 / B1 an octave up; a full-bar RH rest in
   its 4th bar (the breath rule applied at the peak).
3. Phrase lengths that read as truncation: the 9-bar A2 tail with an empty bar, a 6-bar half return without a closing
   melody note.
4. A statistical fingerprint across the generated pieces: intro 4 / coda 5 bars, intro -8 LU, build +3.0, climax
   +4.0, coda -7.5 LU, RH p90 velocity 101 in every piece; the interlude = intro bars 3-4 verbatim.
5. Chord vocabulary: 24 of ~40 labels add9 / sus4; the same G# over B7 (V/vi) in two pieces; a chromatic approach by
   an augmented leap (F#5 -> Bb4 over Am).
6. The left hand's broken figures repeat one top note three times (C#4-C#4-C#4) - mechanical voicing.

## The score over this run (24 seeds 100-123, the 12-reference table)

| Generator | Score (12-reference table) | References |
|---|---|---|
| r5 | 95.9 | 98.7-100 (the table was fit on them) |
| final (r8) | 95.7 sd 2.1, min 90.3 (best-of-8 gain 3.4 / 2.0 / 3.5) | 98.7-100 |

The score did not move while the judges' accuracy fell from 100 % to 71 % - the fixes were not chasing it. The
metrics still outside the references: quiet1 0.33 (0.20-0.32), frame_pitches 6.7 (5-16 but most refs 8+), block_copy
0.21 and a1_copy 0.24 (set 2: 0-0.07 / 0-0.17), chords_n 21 (25-33), hook 9.6 (waltz pieces up to 15). Worst
offenders: hook 15, quiet1 14, block_copy 8, a1_copy 8.

Other genres: jazz-piano, jazz-trio, classical-piano, lofi-piano and organ give the same notes and scores for seeds
100-105 (a digest of every track's notes against the package before the round); new-age-piano and new-age-epiano
(which shares the new-age harmony and players) changed on purpose; only the new-age baseline entry was regenerated.

## After r8: widening the teacher (the learned generator's blind round 2 tells)

The learned student (agentsound/learn, schema 2) learns from this teacher, so the work went where the judges of the
student's round 2 pointed. Every new decision is a distribution in the genre's data, drawn per piece / section and
recorded in the Arrangement record (`vary` / `key` -> tokens `AVary` / `AKey`; the decoder's vocabulary
`arrangement.values`); the composer's changes reach the tokens through the notes and the harmony.

| Tell | Change |
|---|---|
| the last A note for note (a1_copy / block_copy) | `perform._vary`: a return developed per 2-bar unit, drawn from {keep, orn, rhythm, seq, invert} (`vary` per section; odd units and the last keep their cadence: orn / rhythm / keep only) - `_embellish` (passing / neighbour / appoggiatura), `_rerhythm` (downbeat start, one anticipation of a chord tone, dotted 8ths), a sequence a scale step from the unit before, an inversion re-fitted to the chords |
| the climax rebuilt from earlier bars | climax kind 'grow' (`perform._grow`): the hook's head sequenced up a scale step per unit, answered, a climb unit to one new peak (struck once), the head augmented as release, a landing - set weights grow 1.2 / climb 0.7 / theme 0.6 / lift 0.4 / step 0.1 |
| no key change | `key` per section from `genres.KEY_SHIFTS` (home / step / IV / bVI / bIII / III; minor: par / rel / IV), B1 home 0.8, climax home 0.55 / 0.5; only targets with a common key signature (`_key_named`); `_keys` leads in on the new key's V7 and back on home's V7; melody tails re-fitted |
| one frame in every piece | intro chance 0.85, 4 or 2 bars, lh_only 0 / 1 / 2 bars drawn; interlude chance 0.6 / 0.7 with its own `vary`; coda 4 or 2 bars; every section's dynamics drawn (`dyn` {marks: weight}); new intros (pedal, descend, ii-V, lament) |
| waltz: one 2-bar cell | 'na3' 3/4 cells (lean, stroll, arch3, hemiola, flow3, turn3; no pickup-and-hold), the waltz's frames move their bass too (`moves` from plan, closing chords held 3+ bars move) |
| add9 / sus4 everywhere, chords_n 21 | colours: plain triads / m7 first (add9 0.5, madd9 0.2); new blocks (I-I7-IV, iii-VI7-ii-V, IV-vii-III7-vi, IV-V-VI7-ii, I7-IV-iv, iv-bVI build, pedal build; minor i-V3-VII-IV3, iio-V-VI-V, VI-N-V, iv-i-ii-V, lament); the 'na' 4/4 cells start on the downbeat |
| Bb7sus4/D# | `composer.chord_name`: a sus chord's inversion over its 4th is spelled as the 4th |

## Round r9 (2026-10-13, renders `songs/_endless_piano/out/na_r9`, packets seed `blind-new-age-r9`)

Composed side now three of set 2: letters-to-the-morning, pro-newage-homecoming, pro-newage-longing (3/4),
pro-newage-skylight (6/8). Generated 002 (song / grow), 003 (chorus / climb, minor), 005 (return / lift),
007 (waltz, chorus / lift).

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 7/8 (called 002 composed) | 55-80 |
| composer B | 7/8 (called 002 composed) | 62-85 |
| composer C | 7/8 (called 002 composed) | 55-82 |
| statistician | 6/8 (called 007 composed, one composed generated) | 55-82 |
| pianist | 7/8 (called 002 composed) | 55-80 |

Composers 21/24 (88 %), all 34/40 (85 %) - against harder references than r8 (two of the composed pieces are now in
3/4 and 6/8). The 'grow' piece (002) fooled four of five judges ("the chorus progression returns at the climax with a
new, higher melody", "phrase extensions read like a composer stretching a cadence"). Tells: the climb / lift climax =
the chorus transposed (bars copied note for note); the chorus dropped an octave into the left hand's register (F#3
under the LH's C#4: `_under_peak` lowering a whole section that reached the peak); F# held over A in D minor, A over
Cadd9 (the jazz reading of a triad as a 6th chord made the 6th a core tone); the same 4 | 8 x 6 | 3 grid; the
waltz's one-note bars.

## After r9 (the r10 renders in `songs/_endless_piano/out/na_r10`)

| Tell | Change |
|---|---|
| climax = the chorus transposed | the climax's own `vary` (keep 0.15 / orn 0.3 / rhythm 0.3 / seq 0.15 / invert 0.1; its top struck once after it, `_single_top`); a climb / lift without room for the octave grows instead (`plan['peak_floor']`) |
| the chorus in the left hand's register | `_under_peak(plan, key_pcs, floor)`: a section as high as the peak comes down an octave only when its line stays over E4 (`plan['peak_floor']` 64), else only its peak notes come down a key step |
| held 6ths (F# over A in D minor) | `composer.ChordInfo`: with `RaisedPcs` (melody 'raised_v', new-age only) a triad's 6th is no core tone |
| the 8-bar grid | tails drawn more often: A2 0.4, B1 0.3 (new), climax 0.45 |
| waltz one-note bars | the 'na3' long cells two attacks a bar |
| intro LH alone | lh_only {0: 0.6, 1: 0.3, 2: 0.1} |

## Round r10 (2026-10-13, renders `songs/_endless_piano/out/na_r10`, packets seed `blind-new-age-r10`)

Generated 001 (chorus / climb), 002 (song / theme, a climax a key up), 007 (waltz, return / climb), 008 (song / grow,
minor); the same four composed pieces.

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 8/8 | 72-82 |
| composer B | 8/8 | 55-80 |
| composer C | 7/8 (called 007 composed) | 55-75 |
| statistician | 7/8 (called 007 composed) | 60-85 |
| pianist | 5/8 (called 007 and 008 composed, one composed generated) | 56-80 |

Composers 23/24 (96 %), all 35/40 (88 %): no improvement over r9, so the loop stops here (the brief's rule). The
waltz is now the generated piece the judges miss most (3 of 5: "a planned 16-bar ascent", "C7/E tonicising F, F to
Fm6", "A3 re-voiced over a new bass"); the held 6ths, the chorus in the bass and the copied climaxes were not named
again. The new tells (next):
1. One chorus chart in three of four pieces: the hook block 'I7_IV_iv' (I - I7/3 - IV - iv6 - iii - VI7 - ii7 - V,
   added in r9) - `_choose_from` draws the blocks uniformly; 5 of 16 r9 / r10 renders drew it. Needs block weights or
   a per-set no-repeat.
2. The chorus opening with three empty beats and a beat-4 pickup (bars 1 and 5 of B1) in the same pieces.
3. The left hand's broken figure striking one inner note three times running (E3 E3 E3) - the r8 finding 6, still
   open (pianist.FIGURES indexing past the chord tones).
4. A layout cluster: intro 4 | A1 8 | A2 9 | B1 8 | inter 2 = intro bars 3-4 | build 8 in two pieces; every phrase of
   a minor piece closing Vsus4 - V (eleven times in 60 bars).
5. A climax that alternates two chords (Bbm7 / Abmaj7, B/D# / F#/A#) under a repeated 2-bar cell; a key-up climax
   entered without a pivot and left through a bare V7.

## The score over this run (24 seeds 100-123, the 12-reference table)

| metric | before r9 (HEAD) | final (r10 code) | references (12; set 2 = 8) |
|---|---|---|---|
| score | 95.9 | 95.8 sd 2.4 | 95.4-100 |
| a1_copy | 0.240 | 0.094 | 0-0.31 (set 2: 0-0.17) |
| block_copy | 0.214 | 0.128 | 0-0.24 (set 2: 0-0.07) |
| chords_n | 21.0 | 25.9 | 19-33 (set 2: 25-31) |
| chord_rep4 | - | 0.096 | 0-0.26 |
| climax_chart | 0.386 | 0.181 | 0-0.63 |
| climax_copy | - | 0.000 | 0 |
| frame_pitches | 6.6 | 5.5 | 5-16 |
| quiet1 | 0.323 | 0.321 | 0.19-0.32 |

frame_pitches fell (the shorter / absent frames carry fewer pitches) and stays the metric furthest under the
references with quiet1 over them. The score table was not re-fit (no range had to move). Other genres: the notes of
every other genre for seeds 100-105 are bit-identical to the package before the round (digest); new-age-piano and
new-age-epiano changed on purpose, only the new-age baseline entry was regenerated.

## After r10: the five tells as data, then the sweep (2026-10-13)

The r10 tells, each a distribution (commit feb568d): (1) the chorus block a set-level draw per mode
(`plan['set']['hook']`, weights, no repeat within 4 set slots: `set_memory`); (2) the motif's opening weighted
(`melody['openings']`: across the bar line .15, beat-4 pickup .5, a rising 3-note head .6); (3) the left hand's inner
tone at most twice running (`plan['lh']['repeats']`, pianist.figure: the nearest other chord tone instead); (4) the
dominant sus4s kept per tune drawn (`harmony['sus_budget']` 0-3), the others V7 / ii - V / IV - V (`sus_swap`);
(5) no X Y X Y climax (the peak's top line a single top, its chords varied).

Then the user's "simply make everything that's sensible variable - no more tells": an audit of the new-age path
(three readers over genres.py, composer.py, perform.py, arrangement.py, romantic.py / pianist.py) for every single
choice or constant above the note that shaped every piece the same. Varied = a distribution in the genre data
(`NEW_AGE_PIANO`), drawn per piece (or per set, with no repeat across `set_memory` slots where a repeat is heard
across pieces), recorded in the Arrangement record when the player draws it (tokens: the A... names). Coherence
stays inside a piece: the motif, the hook, a section's figure set and the drawn knobs hold for the whole piece.

| Where | What | Before | Now |
|---|---|---|---|
| genres.py `plan['set']` | the theme's (open) and build's chord block | uniform per tune, sets could repeat | `open` / `build` set draws per mode, weights, no repeat in 3 / 2 slots |
| composer.compose (phrase plans) | the period plan per part kind | one plan per kind (A always peaking in its 3rd phrase) | `plan['phrase_variants']`: A 4, B 3, C 3 plans (waltz A 2, C 2), drawn |
| genres.py melody `contours` | the A / B contour | arch / wave only | + `early` (peak at 30 %), A `end` (peak at 90 %) |
| genres.py melody `restate` | 2-bar units a later A restates | 1-2 | 1 / 2 / 3 (.35 / .5 / .15) |
| composer.compose (counter) | the chorus's counter-motif shape | always the hook mirrored | `melody['counter']` mirror .5 / own shape .5 |
| genres.py melody `bridge_long` | the chorus on the long cells | 0 (always the contrast cell) | 0.2 |
| genres.py `_NA_FIGURES` rest / into | the left hand where the melody breathes / before the peak | 'half' / 'up' (waltz 'waltz_held' / 'barcarolle') | half / open / ring, up / flow (waltz held / open, barcarolle / arp) |
| plan sections `figures` | the figure set per section | one set per section | intro, A1, A2, B1, inter, A3, climax drawn from 2 sets (build, coda: one family - kept) |
| plan sections `rit` | the ritardando depth | 0.72-0.85 fixed per section | 3 values per section (e.g. climax .68 / .72 / .8) |
| plan sections `tempo` | the return's / coda's tempo | .93 / .95 | .9 / .93 / .97, coda .9 / .95 / 1.0 |
| plan sections `harmonize` | 3rds / 6ths under the melody | A2, A3 1; climax 2 | A2 / A3 0 .3 / 1 .7; climax 1 .3 / 2 .7 |
| climax `harm_share`, `fermata` | the harmonized share, the hold after the peak | .45, 2.5 beats | .35 / .45 / .6, 1.5 / 2.5 / 3.5 |
| climax / A4 `cadenza` | the flourish over the last dominant | climax none | climax 0.15 (A4 0.12 tried: ornaments over the references, dropped) |
| A1 `turn`, B1 `fill`, build `tail`, A3 song `octave` | a turnaround, a fill, a tail, the return's register | fixed | drawn (A1 turn .4, B1 fill .6, build tail .3, A3 octave up .3) |
| perform._play_piano `play` | rubato depth, inhale before the peak, the 3/4 / 4/4 lilt, phrase breath, tempo push, inner voices, top velocity cap, left-hand level, pedal delay, last chord's dynamic / roll / hold | rubato seed 3, 2 beats, .03 / .04, .35, 18 ms, .78, 106, 41, 60 ms, pp / 110 ms / 3 beats | `plan['play']` 3 values each (rubato .7 / 1 / 1.4, inhale 0 / 1 / 2, ...; recorded: ARubato ... AEndHold), the rubato seeded per tune |
| genres.py melody `hook_seq` | the hook as a sequenced 1-bar cell | 0 | tried 0.25 - kept 0: one rhythm 4x in 8 bars (the style rule) and repeated pitches over the references |
| perform._under_peak | a section over the peak folded to one key tone | all notes at the peak | only when <= 1/4 of its notes, else the octave down (an octave-up return held on G5 for 8 bars) |

Kept as constants (rules, not choices): the voice-leading and spelling (theory / Harm), the instrument's ranges and
`peak_floor` (E4: the chorus out of the left hand's register), the single climax (one top note per piece), hammer
and pedal physics (romantic), the chord-tone fit of strong beats (melody_issues), the phrase length (4 bars: the
references' periods; the plans vary inside it), LEVELS / ACCOMPANIMENT / ASYNC (the measured touch tables), the
interlude's bars (the intro's half cadence, round r6), the build's and coda's figure families, the climax's 'peak'
and 'lift' (the form). The solo piano ignores `end_styles` (its last chord is the roll; the roll's speed, dynamic and
hold are now drawn).

Before / after (24 seeds 100-123; `variety.py` in the session: every record field, the blocks per part, the motif's
opening and first-bar rhythm, the dominant sus4 count; normalized entropy, 0 = the same in every piece):

| | r10 code (1ebf346) | r10 tells as data (feb568d) | after the sweep |
|---|---|---|---|
| decisions measured | 99 (+12 player constants) | 99 (+12) | 115 |
| fixed in all 24 pieces | 29 (+12) | 30 (+12) | 6 (climax melody / peak, inter bars / keep_bars, build / coda figure family) |
| mean entropy per decision | 0.347 | 0.341 | 0.399 |
| learn.evaluate.variety | 0.854 | 0.866 | 0.867 (layout .98, climax kind .81) |
| score (mean, 24 seeds) | 95.8 | 95.7 | 95.0 sd 2.9 |
| a1_copy | 0.094 | 0.092 | 0.141 (references 0-0.31) |
| block_copy | 0.128 | 0.110 | 0.112 |
| rep_pitch (performed) | 0.039 | 0.051 | 0.061 (references 0.017-0.046; the lead sheets 0.03-0.04) |
| orn32 | 4.2 | - | 4.5 |

The score fell 0.7 (rep_pitch, hook, ph_vspread the most frequent worst offenders, as before); the best-of-8 lifts
it 3-4 points per block.

## Round r11 (2026-10-13, renders `songs/_endless_piano/out/na_r11`, packets seed `blind-new-age-r11`)

After the sweep. Generated 002 (F major, chorus / grow), 003 (C minor, song / climb), 004 (Ab major, return / theme),
007 (F major waltz, chorus / lift); the same composed side as r9-r10 (letters-to-the-morning, pro-newage-homecoming,
pro-newage-longing, pro-newage-skylight).

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 4/8 (called 002 and 004 composed, two composed generated) | 52-70 |
| composer B | 7/8 (one composed called generated) | 55-75 |
| composer C | 6/8 (called 002 composed, one composed generated) | 55-78 |
| statistician | 8/8 | 55-74 |
| pianist | 5/8 (called 002 and 004 composed, one composed generated) | 52-72 |

Composers 17/24 (71 %), all 30/40 (75 %): better than r10 (96 % / 88 %) and r9 (88 % / 85 %), so r12 runs. The
generated major pieces now pass as composed with 3 of 5 judges (002: "a planned harmonic trajectory", "each return of
A varied, not copied"; 004: "the climax develops the theme"). The tells:
1. An Am7 in a C minor coda (the tag's 'vi' / 'ii' approach spelled in major) - all five judges.
2. The 'grow' climax: the hook sequenced up the scale five times in the same rhythm (the waltz), the top line parked
   on one tone under the peak for five bars (002, 007: every note over the peak folded to the same scale tone).
3. The waltz's harmonic rhythm 'X | X/3rd' in most 2-bar pairs (a 4/4 plan stretched to 3/4); four bars of left hand
   alone in its intro and coda.
4. The statistician: the same copy map in three pieces (the returns keep the first unit, vary bar 3), a shared coda
   formula (ii - Vsus4 split bar -> tonic +3), a B1 velocity terrace (+17..+27 in one step), the within-phrase
   dynamics 5-6.6 dB against 8-9 in the composed pieces, a shared chord vocabulary (G7sus4/C, Bbm6, Gm7 Csus4).
5. B1 choruses of held notes rocking between two pitches (004: Ab5 G5 Ab5 G5); the climax a register jump with
   neighbour-note circling (003: Eb6 F6 Eb6 D6).

Fixed for r12 (data / distributions, other genres bit-identical): (1) in minor the tag's 'vi' approach is VImaj7 and
'ii' the half-diminished ii (composer.frame); the tag approaches reweighted (plagal .35, ii .35, IV - iv .3);
(2) the grow climax breaks its sequence after two statements (every other later unit the head, then the head a step
higher and held: fragmentation), notes over the peak mirrored under it instead of folded onto one tone; (3) a new
waltz move 'ped' (`plan['moves']`: hold .12, bass .25, sub .4, ped .3 - the chord a 4th up over the held root,
F | Bb/F, where the melody's downbeat / long notes are its tones, else the chord over its 5th; recorded as the
`moves` value 'ped', token AMove_ped): 'same chord over its 3rd' fell to 25 % of the waltz's one-bar pairs.
Score (24 seeds) 95.2 (sweep 95.0).

## Round r12 (2026-10-13, renders `songs/_endless_piano/out/na_r12`, packets seed `blind-new-age-r12`)

Generated 002 (D major, return / grow, a bIII climax), 004 (B minor, chorus / grow), 005 (E major, song / step),
007 (Eb major waltz, song / climb); the same composed side.

| Judge | Correct | Confidence |
|---|---|---|
| composer A | 8/8 | 55-72 |
| composer B | 8/8 | 55-75 |
| composer C | 7/8 (one composed called generated) | 55-80 |
| statistician | 6/8 (two composed called generated) | 60-75 |
| pianist | 6/8 (called 004 composed, one composed generated) | 55-75 |

Composers 23/24 (96 %), all 35/40 (88 %): worse than r11 (71 % / 75 %), so the loop stops at r12 (the r11 code is
what the 30-minute set plays: `songs/_endless_piano/out/na_r11b`). Four pieces are a small sample - r11 drew two
major pieces the judges liked, r12 three 'grow' / sequence climaxes. The tells (open, TODO.md):
1. One hook cell in three of four pieces: the upper-neighbour cell in a dotted rhythm (D5 1.67, E5 0.5, D5 1.08) -
   the motif cell is not a set-level draw yet; and the climax grows it bar by bar (the 'grow' / 'climb' climaxes
   both stamp the cell on each chord) - the fragmentation of r11 does not reach the 4/4 climb.
2. A climax in another key without a pivot (bIII via a bare C7; a climax on V/V's IV - B / C# in E - and A3 straight
   back): `_keys` enters on the new key's dominant only for some moves.
3. The waltz's right hand silent for 4-6 bars (the intro's left hand alone, the end of B1 + the interlude) and one
   bar at the climax's top; a whole bar without the right hand at a 4/4 climax too (005 bar 46).
4. One borrowed colour as a formula: Abm6 (iv6) two bars in every section of the waltz (11 bars).
5. A3 = A2 (chords 8 of 8, melody 4 bars exact) after the climax; the peak at exactly 75 % in four pieces; the
   interlude = the intro's bars 1-2.

# Organ

The endless organ genre (`python -m agentsound endless organ`) against four hand-composed references
(`songs/pro-organ-prelude`, `-toccata`, `-meditation`, `-postlude`, written blind by subagents). Per round: the 4
references and the best-of-8 endless pieces of 4 moods (chorale, toccata, meditation, festive) as notation packets
(`make_packets_organ.py ROUND`, KEY_organ.json), 5 judges with identical prompts (`judge_organ.py ROUND ROOT`: three
composers, a statistician, an organist), scored by `score_round.py KEY_organ.json ROOT/verdicts --tells` (nobody reads
the KEY).

## Round r1 (renders `songs/_endless_organ/out/r1`)

All judges 40/40 = 100 %, composers 24/24. The tells:
1. Every piece ended off the tonic: on the tag's plagal IVm6 (Eb minor in Bb, C minor in G) or on V (the toccata).
2. Verses that only change stops: the same 8 bars six times on principal / flute / positiv / full.
3. The toccata: one figure in all 60 bars, the highest note in bar 2, an abrupt chorale coda.
4. The trumpet tune's accompaniment one dyad struck four times a bar; its climax lower than the cornet episode.
5. The meditation: the pedal in the tenor above the left hand, a tune of fragments after a rest on beat 1.
6. The 4 + 8k + 4 grid; voices appearing and vanishing; a section cut in the middle of a bar before the ring.

Fixes (data / budgets): the coda's last chord V7 under the tune's 2nd degree and a tonic bar (`FINAL_BARS`; the
toccata's figuration stops on a held full chord, every voice holds its final-bar note on a chord tone); a part heard
again is re-harmonized (`VARY`: harmonize avoid / vary); the chorale's second verse a chorale-prelude verse (cantus on
cornet / cromorne / oboe), the last verse with a descant; the toccata's figuration band climbs per section (`register`)
with three drawn figures; three-note trumpet-tune chords in drawn rhythms (`TRUMPET_ACC`); `PEDAL_RANGE` per texture;
the meditation on new `aria` cells (19 % late phrase starts instead of 51 %); the last chord before a ring held to the
last beat; a spread chord's notes no longer cut each other short (`organist.CLUSTER_TOL_MS` - a bug from the chord
spread); counterline fills checked for parallels. New tells end_tonic (hard), bar_copy, top_at, pedal_high; the score
table measured on the references.

## Round r2 (renders `songs/_endless_organ/out/r2`)

38/40 = 95 %, composers 22/24 (composer A called the endless chorale "composed" and one reference "generated"). Tells:
the toccata cell and its pedal pattern copied into five sections; the meditation tune stuck on F4 (eight repeated
notes - the register floor); the trumpet tune low (D4-B4) over static chords and a root pedal; still the 8-bar grid.

Fixes: dominant pedal points (`frame='pedal_point'`, `PEDAL_POINT`, 2-4 bars, drawn) before the returns; the toccata's
pedal a bass line between the theme's entries, beat chords in two sections, scale runs into cadences, nine figures in
the pool; a mood may set the melody's centre / peak (meditation C5 / Ab5, festive C5 / A5); the meditation's reprise an
octave up (`lift`); a walking pedal under the trumpet tune; VARY 2.0; tell rep_run.

## Round r3 (renders `songs/_endless_organ/out/r3`)

40/40 = 100 %, composers 24/24 - no improvement on r2, so the loop stops (three rounds). The new fixes brought new
tells: the scale run stamped at every section end (identical), the pedal at C4 in the plenum chorale and a pedal
cluster at a pedal point's start, the meditation's soft dyads moving in seconds under the cromorne. Still: the grid,
the A tune's opening bars three times, one toccata cell. After r3 (not judged): the run share 0.3, the chorale's pedal
in C2-A3. Open: TODO.md "Organ: open ends".

## The organ score over 24 seeds (1000-1023, all five moods)

| | Score |
|---|---|
| References | prelude 100, toccata 90.0, meditation 91.6, postlude 96.5 (mean 94.5) |
| Endless (single draws) | median 93.4, p10 84.8, min 81.1; by mood chorale 92.4, festive 95.0, meditation 96.5, toccata 84.5, trio 89.9 |

| Metric | r1 | final | References |
|---|---|---|---|
| end_tonic | 0 (every piece) | 1 (every piece) | 1 |
| bar_copy | (verses copied) | 0.04 (p90 0.19) | 0-0.19 |
| top_at | 0.02-0.61 (round 1 pieces) | 0.56 (p10 0.42) | 0.55-0.96 |
| pedal_high | - | 0.07 (p90 0.20) | 0-0.30 |
| par58 | 0 | 0.12 (p90 0.77) | 0 (meditation 12.9: planing) |

Jazz, classical, lofi and new-age are unchanged (MetricParity: seeds 101-103 metrics, scores and candidate order);
the baseline file only gained an 'organ' entry.


# Orchestra

Endless `orchestra-film` (the new-age composer's tune and section plan as a score of lines, orchestrated per section:
docs/ORCHESTRA_ENDLESS.md) vs four hand-written references written blind by subagents on the SAME band
(`endless.orchestra.band`): songs/pro-orch-hopeful (D major, full, 3:30), pro-orch-longing (D minor, chamber, 3:37),
pro-orch-epic (D major -> F, full with choir, 3:15), pro-orch-night (F major, chamber, 4:02). Packets:
`make_packets_orch.py` (per section the roles and their dynamics, per bar every role's notes as played, '%' = its
previous bar), judges `judge_orch.py` (3 composers, a statistician, an orchestrator / conductor), `JUDGE_ORCH.md`;
scored by `score_round.py KEY_orch_rN.json`.

## The references measured (the orchestration part of `genres.SCORES['orchestra']`)

| Metric | epic | hopeful | longing | night | endless before (16 seeds) | endless after r2 |
|---|---|---|---|---|---|---|
| dbl_share | 0.85 | 0.81 | 0.72 | 0.73 | 0.47 | 0.73 |
| roles_bar | 8.9 | 8.1 | 6.8 | 6.7 | 5.5 | 6.2 |
| roles_sd | 3.7 | 3.2 | 2.4 | 2.4 | 1.3 | 1.8 |
| tutti | 0.20 | 0.15 | 0.27 | 0.20 | 0.03 | 0.11 |
| db_bar_sd | 9.8 | 10.0 | 7.9 | 9.0 | 5.1 | 5.5 |
| mel_db | 1.3 | 1.7 | 1.5 | 1.5 | 2.3 | 2.1 |
| score | 96.9 | 56.4 (one tuba note under E1: range_out) | 95.5 | 97.1 | mean 96.1 (provisional table) | mean 94.9 |

## Round r1 (2026-10-13, renders `songs/_endless_orchestra/out/r1`, packets seed `blind-orch-r1`, `KEY_orch_r1.json`)

32/40 = 80 %, composers 24/24 = 100 %, orchestrator 8/8, statistician 0/8 (inverted: he read the references'
regular sections as the template). Tells (generated): the 2nd violins an octave ABOVE the 1st at the climax (a
doubling computed from the line before the orchestrator moved it down an octave); four instruments in unison on the
climax tune, no octave spread; violins / violas hammering one pitch in 8ths for 8 bars (the ostinato = held notes
repeated); one up-down harp arpeggio in every bar of every piece, doubled bass notes in it; a Db timpani roll under a
C chord (the roll fell back to the tonic when the chord's root was not tuned); the violins holding low inner notes
under a cello / viola tune (the harmony voiced under a tenor melody); harp and winds on different chords; composer
level: chromatic mediants without voice-leading, a 2-bar section, the climax fragmenting.

## After r1

Doublings from the PLACED line; the lyrical tutti in octaves (violins 2 an octave down, flutes up, cellos two down);
the harmony over a tenor lead (`HARMONY_HIGH`); harp figures drawn per block (`HARP['figures']`) and de-duplicated;
the string ostinato a rocking figure; timpani rolls on a tuned chord tone or none; a free bass role when the bass's
roles sing; voices only on roles that hold them (no folding; a doubling never folded); the tutti block's marks a step
louder (never past f: an ff tutti saturated the velocities and the gate called the oboe doubling flat); every phrase
a hairpin (`plan['swell']`); `perform(follow=True)`; the oboes' range F6 (the VSCO sustain's top).

## Round r2 (2026-10-13, renders `songs/_endless_orchestra/out/r2`, packets seed `blind-orch-r2`, `KEY_orch_r2.json`)

40/40 = 100 %, composers 24/24. Worse than r1 (the statistician found the new templates). Tells: the composer's
melody built on a two-note neighbour shake (F-G-F-G) or 3-note neighbour cells, phrases starting at 1.42 / 1.92, the
climax tune breaking off at beat 2.5; ONE accompaniment cell in every piece (violins 2 rocking two chord tones in 8ths,
violas on every quarter) - the r1 fix became the new template; the coda look (horns + harp + violins 1 + cellos, a
bare horn triad); the climax as octave stacks with no counter-line; horns and cellos in unison on the tune for 8
bars; chromatic chords pasted against the harp. NOTE: the r2 packets printed `(rest)` for a bar whose notes were all
held from the bar before - the judges read four "silent bars" that were sounding chords; fixed after r2 (`no attack -
held: ...`), so part of the "blocks with dead air" reasons is a packet artifact.

## After r2 (not judged; the set below was rendered with these)

The ostinato drawn from rock / arp / pulse (`orchestra.OSTINATO`), a counter-line in the lyrical tutti (60 %), the
horns-cellos unison rarer, the coda's textures re-weighted, the packet's held bars. After the set: trims percussion
-10, choir -6, clarinets -3 dB (the set's climax: the choir and the clarinets' inner parts as loud as the violins'
tune; a crash 7-10 dB under the loudest part tripped the gate's spiky_track). Open: TODO.md "Endless orchestra".

## Render time

Rendering is ~0.12-0.20 min per minute of music on this machine alone (a 3:30 piece in 25-40 s; 60-110 s while
other renders / judges ran), composing a candidate ~1-3 s (the first band build in a process ~20 s). The set below:
22.5 min of music in 6:22 wall (28 candidates scored, 8 renders of which 1 gated) = 0.28 min per minute; the gate
rejected about one render in four over r1 / r2 / set1 (a click in the sum, flat_dynamics on an accompaniment track
named after an instrument, a spiky crash).

## Set 1 (2026-10-13, `songs/_endless_orchestra/out/set1`, best-of-4, seed 500)

`endless-orchestra-film-502-7.mp3`: 7 pieces, 22:56 incl. the gaps, 44 MB (256 kbps; under 50 MB, not re-encoded), -16.9 ..
-18.7 LUFS, LRA 10.8-14.9 LU. The best three by score: 001 'Toward Autumn' (G major, pastoral, chamber, 98.4),
006 'Endless Fields of the Dawn' (D minor, epic, full with choir, 98.0), 004 'Open Horizons of Evening Waltz' (Db
major, night, 3/4, chamber, 97.0).
