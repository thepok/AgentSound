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

## Round g1 (2026-10-15, all ten generated, with the bloom; renders `songs/_endless_piano/out/na_g1`, packets seed `blind-new-age-g1`)

A new round type (the user: "make 10 pieces and ask agents how many are machine-generated"). All ten packets are
endless pieces (`endless new-age-piano --count 10 --seed 63000`, best-of-8, seeds 63004-63152, the bloom /
hand-to-hand code of 57f90ab: two waltzes, four minor, six major). The judges were not told: the brief stays "either
composed or generated, the split is not disclosed", and now asks for a `## Count` (how many of the packets are
generated). `make_packets_newage.py g1` (rounds named g...: no composed side, every tune folder); the analysis now
prints the tempo per section as performed, so a push is visible. `score_round.py` prints each judge's count and the
judges each generated piece fooled. The target over the next rounds: the count estimate down to ~3 of 10.

| Judge | Called generated | Count estimate | Confidence |
|---|---|---|---|
| composer A | 5 | 5 of 10 ("could be 4 to 7") | 52-72 |
| composer B | 5 | 5 of 10 ("five pairs that share a template, one per pair generated") | 50-72 |
| composer C | 4 | 4 of 10 | 52-75 |
| statistician | 3 | 4 of 10 | 50-75 |
| pianist | 6 | 6 of 10 ("would not surprise me if 7-8") | 52-90 |

23 of 50 verdicts said generated (46 %); the mean count estimate is 4.8 of 10 (truth 10). Earlier rounds, on the
generated side only: r11 15/20 caught (75 %), r12 19/20 (95 %). The rates are not directly comparable: in g1 the
judges expected a mix and split near half (their notes say so), so the count, not the accuracy, is the measure. Fooled
(called composed) by: DAJD 010 Db major 5/5; ELED 001 E major, HQXS 003 D minor, THHC 002 G major 4/5; TKSA 004
waltz, TSCB 008 G major 3/5; RRRK 005 E minor 2/5; PWMQ 006, UPTY 009 waltz 1/5; NCJL 007 Bb major 0/5. Seven of ten
fooled two or more judges.

What the convincing pieces share (the judges' reasons for "composed"): the climax built from the theme's cell
(rhythm and contour raised a 6th / an octave over new chords: DAJD 33, THHC 34, HQXS 33, RRRK 37); a reharmonised
return (A2 / A3 over a new bass line or a held Gb/Bb); a borrowed colour planted before it is used (TSCB's Cm6 in A2
-> an Eb climax; DAJD's Gbm6 in B1 and the climax); irregular proportions (HQXS's A3 cut to 6 bars).

The tells, ranked by judges x pieces:
1. Runs and fills in the home key's scale over a chord or section in another key (all five judges; NCJL 35-40,
   Bb-scale 16ths over G/B, C/E, Am7; RRRK 35 an E-minor shape and Gb over Fmaj7; ELED 51 E-major notes over Am6;
   HQXS 28-29 a C arpeggio carried over the bar line into Gm). The runs come from the bloom's hand-off / weave
   (`perform._handoffs` draws on the home key's scale when the chord has too few tones); the carried-over arpeggio
   is likely its `link` bar.
2. The climax not derived from the theme: a key or octave transplant (PWMQ jumps to E6-F6, TSCB / NCJL / RRRK a
   whole climax in a foreign key), chord-tone tiling (TKSA long tones, UPTY top-third-top for 8 bars).
3. A 16th run on beat 4 of every climax / build bar, one cell repeated (NCJL 34-41, UPTY 83-90, TKSA 69-75, ELED
   49-52, TSCB 35-37): "a texture switched on for the section". The statistician called DAJD's build cascades
   idiomatic, the pianist the same bars a generic fill.
4. Returns copied (ELED A3 = A1 8/8, NCJL 7/8, THHC 8/8) and the same opening rhythm skeleton in three pieces.
5. Short 4-5 note "chord grabs" of 0.08 beat mid-phrase (ELED 24, RRRK 15 / 49, PWMQ 51, UPTY 33, TKSA 96).
6. The waltzes: the right hand silent for whole intro / interlude / coda stretches (UPTY 13 % of its bars),
   "X | X/inversion" two-bar pairs (11 and 8), 16-bar sections; TKSA's climax thinner and quieter than its build.
7. Smaller: a chorus that sits lower than the verse or loops two bars (THHC 9-16), a right-hand bar of
   accompaniment triplets at a cadence (PWMQ 26), a whole-bar RH rest at the same slot in every A (TSCB).

The bloom: no judge named the tempo push (1.03-1.08 x, visible in the per-section tempo line), an accelerando or the
hands sharing a register. Its texture was noticed only as tell 1 (the hand-off's scale) and tell 3 (16ths every
bar), and once as praise (DAJD: "the climax thins after the build's cascades, register and weight carry it").
Measured (bloom_tells): tempo_push 1.03-1.08, climax_tempo 0.93-1.00, rh_peak_den 1.56-3.25, flow32 2.1-5.3,
hand_meet 0.01-0.18. Open points in TODO.md (the bloom, 6-7).

## Round g2 (2026-10-15, all ten generated, after the g1 fixes; renders `songs/_endless_piano/out/na_g2`, packets seed `blind-new-age-g2`)

The same setup as g1: `endless new-age-piano --count 10 --seed 64000` (best-of-8), `make_packets_newage.py g2`, five
judges (composer A / B / C, statistician, pianist) on the neutral brief with the `## Count`, never shown a KEY; mp3s
by packet ID + KEY in `songs/_endless_piano/out/blind_g2`. Two waltzes (HWCM, WKUS). A first generation of this set
was discarded unjudged: the new set climax table could not repeat `grow` (set_memory 1), so four slots drew
climb / lift; set_memory for the climax is now 0 and the set was regenerated from the same seed.

The fixes before the round (docs/PIANIST_RULES.md "After the all-generated blind round g1"): hand-offs, weave,
ornaments and the cadenza in the LOCAL key / chord scale (`perform._key_spans`), the climax from the theme (set
climax `grow` 1.4, `grow_aug` 0.5: the hook augmented 2x), hand-offs phrase-shaped with a per-run grid, reharmonised
and varied returns, a per-set `opening` cell table, the 0.08-beat "chord grabs" printed as ornaments (they were
turns / slides), waltz frame melodies augmented and fewer "X | X/inv" pairs. Measured over this set vs the g1 set
(tells_newage.py): off_scale 2.3 -> 0.1, ret_chart .74 -> .43, clx_foreign .5 -> .2, waltz xx_inv 16 -> 3,
b4_streak max 3 -> 2.

| Judge | Called generated | Count estimate | g1 count |
|---|---|---|---|
| composer A | 6 | 6 of 10 ("could easily be 7-8") | 5 |
| composer B | 8 | 8 of 10 ("may be 9 or 10") | 5 |
| composer C | 7 | 7 of 10 ("quite possible all ten") | 4 |
| statistician | 5 | 5 of 10 (6-7 if the template is in the writing) | 4 |
| pianist | 5 | 5 of 10 ("perhaps 6-7") | 6 |

31 of 50 verdicts said generated (62 %, g1 46 %); the mean count is 6.2 of 10 (g1 4.8). Worse than g1: the fixed
tells are gone from the reasons (no judge named a wrong-scale run as a pattern, only single fill notes), but the
judges now compared pieces with each other and found templates SHARED ACROSS THE SET. Fooled by: GSKY 005, KYQN 001,
PQTV 007 4/5; YWEJ 002 3/5; QRLH 008 2/5; FECV 006, XCGN 003 1/5; HWCM 004 (waltz), QMAH 010, WKUS 009 (waltz) 0/5.

The tells, ranked by judges x pieces:
1. One form skeleton for every piece (B, C, statistician, pianist): intro / A / A / B / build / climax / A / coda, the
   highest note at 71-76 % in 10/10, 8 + 1 held-bar sections, every section ending Vsus4 -> V, the final bar a
   4-note LH chord under a RH 2nd / 3rd, the coda 21-39 % slower, the LH escalating 8ths -> triplets -> 16ths with an
   octave bass in the climax and thinning in A3.
2. Progressions shared between pieces (all three composers, statistician): the climax route Eb7 -> Ab/C -> Dbm6 ->
   G7 in FECV and HWCM (both C major, same `_key` move), the build G D Am Em C D Bsus4 B in PQTV and QMAH, the
   vi-IV-I-Vsus4 intro and the I-Vsus4 interlude in QRLH and YWEJ; a minor-iv6 colour in nearly every piece (QRLH
   Cm6 x5).
3. The climax as a repeated 3-note neighbour cell ("x, upper neighbour, x" on the 1 / 2.5 / 3 grid, one per bar:
   QMAH 38-46, XCGN 37-45, WKUS 61-76 F5 for four bars, YWEJ 41-45) or as fragments (FECV 40 empty, 43/45/47 three
   8ths each). This is the `grow` climax tiling the hook's head cell; GSKY 46-50 and PQTV 37 were named the model.
4. The hand-off / weave texture as a stock gesture: the low-velocity 16th broken chord under a held top note in 8 of
   10 packets (FECV 28-29, PQTV 23/25, XCGN 32/34/36, YWEJ 36/38, QMAH 26-28, WKUS 55/58), the 4-note 16th pickup on
   beat 4 in the climax (YWEJ 40/41/44, PQTV 38, QRLH 40, XCGN 38/42). Fewer per piece than g1, but present in all.
5. Unstable or copied themes: the waltz A2 a new meander over the same chords (HWCM 5-8 vs 37-40, WKUS), HWCM A3 = A2
   an octave up note for note, literal bar copies (QMAH 20 = 19, YWEJ 45 = 43); returns truncated (FECV 48-53, XCGN
   46-51).
6. A chorus without contrast: QRLH 21-28 reuses A's progression and cell, GSKY's chorus sits below the verse.
7. Dynamics as a plateau (GSKY climax v104-120 for 8 bars, WKUS 85-105 for 16) and a build louder than its climax
   (GSKY 43-44, QMAH).
8. Smaller: the long-short-long bar (1.5 / 0.5 / 2 beats) in most bars, phrases always 2+2; home-scale fill notes
   over borrowed chords (G over Ebm7 WKUS 47, D over Fm7 HWCM 21, C over B major QMAH 29); both hands striking one key
   (FECV 2, GSKY 5); oom-pah-pah block chords in the 3/4 climaxes.

What convinced: reharmonised returns (KYQN 46-53, GSKY 54-61, QRLH 48, PQTV 45 - named by every judge), the climax
grown from the theme (FECV 39-44), a staged climax climb (PQTV 37-43), a chorus with its own register and bass
(KYQN 13-21). Open points in TODO.md (the new-age set, g2).

## Round g3 (2026-10-15, the first QUALITY round: 8 generated + 2 hidden references; renders `songs/_endless_piano/out/na_g3`, packets seed `blind-new-age-g3`)

The format changed. Judges now RATE every piece 1-10 on six dimensions: melody, harmony, form, development,
performance and overall. Each also names one fix with bars and gives a side `## Count` of how many pieces they think
are generated. Brief: `JUDGE_NEWAGE.md`; the old verdict brief is kept as `JUDGE_NEWAGE_g1g2.md`.

The set:
- 8 generated pieces: `endless new-age-piano --count 8 --seed 65000`, best-of-8.
- 2 hidden composed references: BAXD = pro-newage-homecoming, SLCA = pro-newage-longing.

The packets also print, per section, the right hand's level over the left hand's in dB and the share of RH notes at
or above C6.

There were five judges: composer A, B and C, the statistician, and a new PERFORMANCE judge ('performer') who weighs
the hands' balance, register, touch, rubato and RH voicing. No judge was shown a KEY. The mp3s, named by packet ID,
and the KEY are in `songs/_endless_piano/out/blind_g3`. Scored with `score_round.py KEY_newage.json
D:/tmp/g3_judges/verdicts --tells` (the quality tables).

The set's forms, from the set plan:

| Piece | Packet | Form |
|---|---|---|
| 001 | RAKJ | late |
| 002 | TNFH | return |
| 003 | RAPR | chorus |
| 004 | PBQV | song |
| 005 | GAZC | variations |
| 006 | HLEU | arch |
| 007 | EKPT | late, waltz |
| 008 | EWXH | song, F# minor |

The fixes before the round are in docs/PIANIST_RULES.md "After round g2". They cover:
- six forms per set;
- peak spread;
- irregular phrase lengths;
- drawn section closes and final voicings;
- set memory for chord blocks and intros;
- the grow climax extending the hook;
- bloom texture per piece;
- per-section RH texture;
- one dynamic line per phrase.

### Quality, generated vs references (mean of 5 judges)

| Dimension | Generated (8) | References (2) | Gap |
|---|---|---|---|
| melody | 5.60 | 7.00 | +1.40 |
| harmony | 6.20 | 6.90 | +0.70 |
| form | 5.53 | 6.30 | +0.77 |
| development | 5.30 | 6.40 | +1.10 |
| performance | 5.75 | 6.50 | +0.75 |
| overall | 5.58 | 6.90 | +1.33 |

Per packet, overall:

| Packet | Source | Form | Overall |
|---|---|---|---|
| SLCA | ref | | 7.2 |
| BAXD | ref | | 6.6 |
| EWXH | gen | song, minor | 6.6 |
| TNFH | gen | return | 6.4 |
| HLEU | gen | arch | 6.0 |
| RAKJ | gen | late | 6.0 |
| GAZC | gen | variations | 5.2 |
| EKPT | gen | waltz | 4.8 |
| PBQV | gen | song | 4.8 |
| RAPR | gen | chorus | 4.8 |

EWXH ties the weaker reference. TNFH has the best harmony rating of the set (7.4).

Counts (truth: 8 of 10):

| Judge | Count |
|---|---|
| composer A | 7 |
| composer B | 7 |
| composer C | 6 |
| statistician | 7 |
| performer | 6 |

The mean count is 6.6. The statistician named BAXD, EWXH and SLCA as free of his fingerprints, so the generated
EWXH passed his count.

### The fixes the judges name, ranked by judges x pieces

1. **The climax harmony lurches to an unprepared remote key and stays there.**
   - Examples: PBQV 54-61 (Eb -> D7 / Am / G / C), RAPR 36-44, RAKJ 40-47, GAZC 21-26.
   - Named by all three composers and the statistician.
   - Wanted: a pivot over 2-4 build bars and a route home, or the climax kept near home with one borrowed chord.
   - EWXH and RAKJ were named as the good examples.
2. **A themes without a profile.**
   - Examples: HLEU 3-10, PBQV 3-6, RAPR 5-11, EKPT 9-24. They circle inside a third or fourth, or are a 2-note
     neighbour cell.
   - Named by all three composers.
   - Wanted: a 4+4 sentence with one leap and one held peak, and a B that answers A rather than replaces it. In PBQV,
     RAPR and HLEU the B tune is stronger than A.
3. **The melody is absent at the peak.**
   - Examples: EWXH 35-39, RAPR 39, GAZC 22/27, TNFH 26/30.
   - What happens: RH rests or beat-4-only entries while the LH 16ths carry the climax, with the hands within 0-2 dB
     in builds and climaxes.
   - Named by all five judges.
   - Wanted: the hook augmented or in octaves on the downbeats, and the LH arpeggio velocity capped under the line.
4. **Proportions.**
   - The `variations` form peaks at 49 % and then repeats A twice (GAZC 28-43). Named by every judge.
   - The `late` form has no return after its climax (RAKJ).
   - Wanted: the climax at 65-80 %, then one transformed return.
5. **Copied 4-bar blocks inside a section, and stock gestures shared across the set (statistician).**
   - Copied blocks: PBQV 46-49 -> 50-53, RAKJ 25-28 -> 29-32, TNFH 23-26 -> 27-30 and 35-38 -> 39-42. These are likely
     the new `bars` extensions, where the reharm / vary can leave the RH unchanged (to check).
   - The beat-4.5 note held into an empty bar, in 6 pieces.
   - Whole-bar RH rests in the body, in 7 pieces.
   - The end-of-bar 4-note 16th run in the climax, in 7 pieces.
6. **Climax dynamics hammered, not shaped.**
   - Examples: RAKJ 41-47 at v102-121, RAPR 38/42 at v115-123, TNFH 45 at v126.
   - The build is louder than the climax in EWXH.
   - Seam jumps from pp to ff (RAPR 11-14).
7. **Smaller.**
   - The waltz's tune sits in F4-D5 against a LH up to F4, at a flat 94-99 BPM over 119 bars.
   - EKPT A3 = A1.
   - The performer and the statistician wanted the references' one-finger A sections voiced earlier. SLCA's RH is
     single notes in bars 5-52.

### What convinced

- Reharmonised returns: BAXD 29/32, EWXH 43.
- EWXH's prepared climax.
- TNFH's colour.
- Thirds / sixths on a second statement (BAXD 27-34, a reference), which the performer named as the model.
- No judge named one form skeleton, the 70-78 % peak, Vsus4 section ends or a shared progression. Those were the g2
  set tells, now gone from the reasons.

### Baseline for future rounds

The tells are measured with `songs/_blind/tells_newage.py` over 48 seeds (64000-64047) and 6 sets of 10.

- **Form:** 6 layouts per set; top_at p10/median/p90 = .54 / .73 / .87; peaks at 70-78 %: 3.8 per 10; grid8 .66;
  end_V .45; end_sus .18; shared3 / shared4 = 42 / 7.8 per set; weave pieces 2.7 per set; clx_tile 0; clx_hold 4.0.
- **Flow:** mel_rate .99; dvel_med 3.8 (p90 7.0); rh_multi .44 (A1 .20 / A .35 / B .54 / climax .63);
  inner_move .22.
- **Score:** mean 95.6.
- **Quality:** generated overall 5.58 vs references 6.90 (gap +1.33). The largest gaps are melody (+1.40) and
  development (+1.10).

The open points are in TODO.md under "the new-age set, g3".

## Round g4 (2026-10-16, the first five signature moves; renders `songs/_endless_piano/out/na_g4`, packets seed `blind-new-age-g4`)

The format is g3's: five judges rate every piece 1-10 on six dimensions, name one fix and give a side `## Count`.
New in the brief (JUDGE_NEWAGE.md) is the memorable moment: `moment` (bars and what happens), `memorable` 0-3,
`recurs` and `shared`. `score_round.py` adds the mean memorable, the hit rate (named moments on a planned move's bars,
from the KEY's `moves`) and the shared flags.

The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 66000`, best-of-8.
- 2 hidden references the judges had not seen: VJMK = pro-newage-embers (a C minor passacaglia), JQBE =
  pro-newage-tide (a D Dorian 6/8 arch).

The same five judges as g3; no judge was shown a KEY. The mp3s, named by packet ID, the KEY and SCORES.txt (per piece:
the overall rating and a line from the judges) are in `songs/_endless_piano/out/blind_g4`. Scored with
`score_round.py KEY_newage.json D:/tmp/g4_judges/verdicts --tells`.

Before the round: g3's fixes and the signature moves (docs/PIANIST_RULES.md "After round g3", docs/PIANO_MOVES.md
section 11).

| Piece | Packet | Form | Moves |
|---|---|---|---|
| 001 | ABBF | variations | motto (sigh) |
| 002 | HYSW | arch | ostinato, goosebump, cascade |
| 003 | HNGF | chorus, D minor | motto (toll), goosebump, cascade |
| 004 | ZKYC | late | motto (sigh), ostinato, pause, cascade |
| 005 | ANQT | song | pause |
| 006 | NYVX | arch | pause |
| 007 | EWEK | variations, waltz | goosebump |
| 008 | FBKR | chorus, A minor | ostinato |

### Quality, generated vs references (mean of 5 judges), against g3

| Dimension | g4 generated | g4 references | g4 gap | g3 generated | g3 gap |
|---|---|---|---|---|---|
| melody | 5.35 | 6.90 | +1.55 | 5.60 | +1.40 |
| harmony | 5.97 | 6.70 | +0.73 | 6.20 | +0.70 |
| form | 5.20 | 7.20 | +2.00 | 5.53 | +0.77 |
| development | 5.15 | 6.90 | +1.75 | 5.30 | +1.10 |
| performance | 5.45 | 6.80 | +1.35 | 5.75 | +0.75 |
| overall | 5.30 | 7.10 | +1.80 | 5.58 | +1.33 |

Per packet, overall: VJMK 7.2, JQBE 7.0 (the references); HNGF 5.8, HYSW 5.8, ABBF 5.6, ANQT 5.4, FBKR 5.4, NYVX 5.2,
ZKYC 5.0, EWEK 4.2. The new references rated higher than g3's (7.10 vs 6.90). The generated set fell 0.28 overall,
and form fell the most (-0.33).

Counts: every judge counted 8 of 10, the truth (g3: mean 6.6).

### The memorable moment

- **memorable:** the generated pieces 1.93, the references 2.90 (gap +0.97). Top generated: ABBF and HNGF 2.4. Lowest:
  EWEK 1.2 (no move but a goosebump chord in a hookless waltz).
- **Hit rate:** in 18 of 40 answers the named moment sits on a planned move's bars: motto 14, goosebump 4, pause 2,
  cascade 1. 3 more fall only inside an ostinato section.
  - The motto is the move the judges remember. All five named ABBF's motto returning an octave up to open the climax,
    and three gave it 3.
  - Every judge named the cascade, but as a fault ("mechanical", "texture, not music", "a gimmick": HNGF 41-42, HYSW
    37-38, ZKYC 55). None named it as the moment.
- **Shared flags: 22, want 0.**
  - Every judge put the three motto pieces ABBF / HNGF / ZKYC together as one "D-C-C" cell. Two drew 'sigh', which
    ignores its drawn interval and grid, and 'toll' has a similar step-and-repeat shape. All three were anchored on
    the theme head's D5. The fingerprint passed because it counted the interval and grid. **Fixed after the round:**
    the motto's fingerprint is now its kind (osc: with its interval). Still open: one anchor register for every
    motto.
  - FBKR ~ NYVX: 3 judges.

### The fixes the judges name, ranked by judges x pieces

1. **The climax has no theme.** All five judges, 7 of 8 pieces.
   - It is chord stabs, held mid-register notes (HNGF 36 C5, ZKYC 49-50, ANQT 49/52), new material (NYVX, HYSW), or
     it dissolves into the cascade.
   - Wanted: the A or B hook at the peak, up an octave in octaves / chords. Both references do this (VJMK 41-45, JQBE 37-45).
   - The cascade takes the bars after the peak note away from the melody. Make it a link out of the climax's last
     bar, under a held melody note, or drop it.
2. **The A theme restated near-verbatim.** All judges.
   - ZKYC 5 = 13 = 33 = 57, ABBF A2 ~ A3, ANQT A4 = A2, EWEK 85-90 = 53-58.
   - Wanted: keep the head and rewrite or sequence the second half; reharmonise as HNGF 19-26 and FBKR 40-47 already
     do.
3. **Climax key moves still read as unprepared.**
   - FBKR Bm7b5 -> Dmaj7 has no dominant: a short build, so no pivot.
   - NYVX Dm7 -> C7 -> F (the pivot did play) was called "abrupt", and the judges want a longer preparation.
   - The climax there is also lower and quieter than the build (FBKR +1.2 vs +2.5 LU).
4. **B or the build too loud too early.** NYVX B1 at v86-106 in bar 8, ANQT B1 at climax volume, ZKYC's build at
   0.0 dB between the hands.
5. **Loops and grids.** The statistician counted these.
   - A 4-bar build cell played twice (ANQT 41-44 = 45-48).
   - Held notes landing every 2nd / 4th bar.
   - The IV-iv6 split in the penultimate bar (FBKR, NYVX, ZKYC, HYSW).
   - EWEK's 20-bar A sections without a hook.
6. **The hands collide.**
   - ZKYC A4 drops the melody to D4-Bb3 inside the left hand's arpeggio.
   - HNGF 27: the motto's octave-down recurrence (D4) sits in the left hand's register.
   - The cascade's right hand falls into the left hand's register.
   - The rule to add: a motto recurrence an octave down only above the left hand's cap.

### What convinced

- The motto returning at the climax (ABBF 28), when it stays in the melody's register.
- Borrowed colour: HYSW's Bbm6 / F7/Eb, ZKYC's Ebm6 -> Gb, ABBF's Fm6.
- Reharmonised returns: HNGF A2, FBKR A3.
- NYVX's bVI climax key as an idea.
- The goosebump chord was named 4 times as a moment (EWEK 77 three times, HNGF 37), each at memorable 1-2.

### Baseline for future rounds

48 seeds 64000-64047, 6 sets of 10:
- **Form:** top_at .59 / .74 / .80.
- **Flow:** inner_move .32; phrase_rests .77 (with LEAN).
- **Climax:** clx_bal 5.1 / clx_pk_bal 6.8; clx_vmax 104.
- **Theme head:** a_leap 5.8.
- **Signature moves:** sig_repeat 0, sig_max_share 0.40, 1.75 moves a piece in a set.
- **Score:** 95.6.
- **Quality:** generated overall 5.30 vs 7.10 (gap +1.80); memorable 1.93 vs 2.90.

The open points are in TODO.md under "the new-age set, g4".

## Round g5 (2026-10-16, the theme at the climax; renders `songs/_endless_piano/out/na_g5`, packets seed `blind-new-age-g5`)

The format is g4's. The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 67000`, best-of-8.
- The same 2 references as g4 under new IDs: PUQX = pro-newage-embers (g4 VJMK), ALMJ = pro-newage-tide (g4 JQBE).

The same five judges; no judge was shown a KEY. The mp3s by packet ID, the KEY and SCORES.txt are in
`songs/_endless_piano/out/blind_g5`. Scored with `score_round.py KEY_newage.json D:/tmp/g5_judges/verdicts --tells`.

Before the round: g4's fixes (docs/PIANIST_RULES.md "After round g4"): the theme sung at the climax (`_anthem`), the
cascade a link, returns that keep the head and rewrite the second half, prepared key moves, the climax the loudest
section, the coda approach and the motto band as set draws.

| Piece | Packet | Form | Climax | Moves |
|---|---|---|---|---|
| 001 | AZTL | song, D major | theme augmented | motto, goosebump, pause |
| 002 | XXUB | chorus, F major | theme in octaves | motto |
| 003 | VUUY | return, C major | theme in chords | ostinato, goosebump |
| 004 | UHVW | variations, A minor | theme reharmonised | motto, pause, cascade |
| 005 | QTZG | late, E major | theme sequenced | cascade |
| 006 | BGME | chorus, A major | lift (into G#m) | ostinato |
| 007 | QJUG | song, D minor waltz | theme in octaves | cascade, pause |
| 008 | GNRR | return, A minor | theme in chords | ostinato, goosebump |

### Quality, generated vs references (mean of 5 judges), against g4 and g3

| Dimension | g5 generated | g5 references | g5 gap | g4 generated | g4 gap | g3 generated | g3 gap |
|---|---|---|---|---|---|---|---|
| melody | 5.53 | 7.00 | +1.47 | 5.35 | +1.55 | 5.60 | +1.40 |
| harmony | 6.17 | 7.20 | +1.03 | 5.97 | +0.73 | 6.20 | +0.70 |
| form | 5.25 | 6.80 | +1.55 | 5.20 | +2.00 | 5.53 | +0.77 |
| development | 5.62 | 7.20 | +1.58 | 5.15 | +1.75 | 5.30 | +1.10 |
| performance | 5.38 | 7.00 | +1.62 | 5.45 | +1.35 | 5.75 | +0.75 |
| overall | 5.40 | 7.10 | +1.70 | 5.30 | +1.80 | 5.58 | +1.33 |

Per packet, overall: PUQX 7.6, ALMJ 6.6 (the references; g4 7.2 / 7.0); AZTL 6.8, XXUB 5.6, BGME 5.4, UHVW 5.4,
QTZG 5.2, VUUY 5.2, GNRR 5.0, QJUG 4.6. The generated set rose 0.10 overall, development the most (+0.47), and AZTL is
the first generated piece rated above a reference (tide 6.6). Performance fell 0.07.

Counts: every judge counted 8 of 10, the truth.

### The memorable moment

- **memorable:** the generated pieces 2.10 (g4 1.93), the references 2.60 (g4 2.90): gap +0.50 (g4 +0.97). AZTL 3.0
  (every judge named its motto), UHVW and XXUB 2.8; lowest BGME 1.4 (no motto, no theme at the climax).
- **Hit rate:** 16 of 40 on a planned move's bars: motto 11, pause 6, goosebump 3, cascade 3 (as a "nice pedal
  effect" once, QTZG 45; twice still "a flourish"). 8 more inside an ostinato section.
- **Shared flags: 27** (g4 22), but no shared cell: the motto template is gone. The judges grouped the pieces by their
  shape: AZTL ~ UHVW ~ VUUY (one A register E4-C5, few contrasts), BGME ~ QTZG ~ VUUY (an ostinato intro, a 4-note
  final grip), and the "long note 2.5 beats + two eighths" cadence cell (statistician: AZTL, UHVW, XXUB, GNRR).

### The fixes the judges name, ranked by judges x pieces

1. **The climax states the theme, but in its own register.** All five judges, 7 of 8 pieces (AZTL 41-44 B4-D5,
   GNRR 37-42 C5-A4, XXUB 43-46 down to G4 / F4, UHVW, VUUY 45-46 G4-A4, QTZG never above B5).
   - `_anthem` plays the theme's units at A1's pitch and lifts only the head at the peak unit; the judges want the
     whole climax line an octave up (C6 band), in octaves / sixths, with no dip back into the alto.
2. **The melody lives too low.** The A theme in E4-C5, 0 % of RH notes at C6+ outside the climax, inside the left hand's
   arpeggios (UHVW, XXUB, GNRR, AZTL). The g2 "too many very high notes" ceiling overshot.
3. **B1 still as loud as the climax.** QTZG (B1 v108, +1.6 vs +1.5 LU), AZTL (B1 v115 at bar 24, the coda v105),
   GNRR (+2.7 vs +2.9). `_dyn_order` caps the marks, `_loud_order` the section energy over 1 dB; single phrase peaks
   and the peak note are not capped.
4. **Form and proportions.** No B section in 'variations' (UHVW: A1 A2 A3 climax A4); the waltz at 129 bars with a
   20-bar build vamping on Asus4 (QJUG 73-92); QTZG at 2:31 too short with a 2-bar intro / 6-bar A2.
5. **A climax that leaves the key with new material** (BGME: 'lift' into G#m7 / D#m7 after F#7): the key lead-in was
   measured as present (key_dom 1) but read as unprepared; the 'lift' climax has no theme.
6. **Returns still close to A1** (VUUY A3 = A1 softer, BGME A3 ~ A2): the head unit is kept by design; the judges count
   the second unit of the head phrase as copied too.
7. **A busy left hand** (VUUY's triplets ~10 attacks a bar, GNRR 12.2 at the climax) over a thin climax right hand
   (XXUB 3.4 notes a bar).

### What convinced

- The motto as architecture: AZTL's cell planted in bar 1, soft at the build, full at the climax, inside the
  reprise, closing the coda (all five judges, memorable 3.0); UHVW's and XXUB's (the Bbm6 sigh) too.
- Borrowed colours: Gm6 / E7/G# / Bb -> Bm7 (AZTL), Bbm6 (XXUB), Bb -> E (GNRR), Dadd9 bVII (QTZG), Bbadd9 (VUUY).
- Reharmonised returns (BGME A3 on F#m7, QTZG A3 on C#m7, QJUG A4 on Bbmaj7) and the D-major colour before UHVW's
  final chord.
- The right hand in thirds / sixths through BGME's B1 and A2 (the performer).

### Baseline for future rounds

48 seeds 64000-64047, 6 sets of 10:
- **Climax:** the theme near the peak 36 of 48 (clx_theme_pk); clx_theme .85; climax loudest in 45 (clx_loud 1.14).
- **Returns:** ret_tail .21 (max .56); **keys:** key_dom / key_home 1.0 / 1.0.
- **Flow:** phrase_rests .85; breath rejects in a set slot 11.3 %, arc 37.1 %.
- **Score:** 95.0.
- **Quality:** generated overall 5.40 vs 7.10 (gap +1.70); memorable 2.10 vs 2.60.

The open points are in TODO.md under "the new-age set, g5".

## Round g6 (2026-10-16, the climax an octave up; renders `songs/_endless_piano/out/na_g6`, packets seed `blind-new-age-g6`)

The format is g5's. The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 69000`, best-of-8.
- The same 2 references under new IDs: KFCM = pro-newage-embers (g5 PUQX), ZESN = pro-newage-tide (g5 ALMJ). Their
  packets are byte for byte g5's.

The same five judges (D:/tmp/g6_judges); no judge was shown a KEY. The mp3s by packet ID, the KEY and SCORES.txt are
in `songs/_endless_piano/out/blind_g6`. Scored with `score_round.py KEY_newage.json D:/tmp/g6_judges/verdicts --tells`.

Before the round: g5's fixes (docs/PIANIST_RULES.md "After round g5"):
- the sung climax an octave over A1 (the C6 band);
- the A theme a whole step higher, over the left hand;
- every section's phrase peaks under the climax's;
- 'variations' with the chorus;
- waltzes without extensions;
- 'lift' as the sung theme;
- a key lead-in on the dominant of the section's first chord;
- the broad climax left hand.

| Piece | Packet | Form | Climax | Moves |
|---|---|---|---|---|
| 001 | QNFS | chorus, A major | theme reharmonised, in G#m (a key move, D#7 lead-in) | cascade |
| 002 | TLTG | variations, D major | the chorus climbing | pause |
| 003 | WHKZ | return, A minor | the chorus climbing | motto, ostinato, pause |
| 004 | XEDV | song, C major | theme in octaves | ostinato |
| 005 | XUMB | chorus, A major | theme in chords | goosebump, motto |
| 006 | SGVL | variations, Db major | theme reharmonised | motto, pause |
| 007 | FUKP | late, Eb major waltz | theme sequenced | cascade |
| 008 | GVPE | return, C# minor | a step up (new key) | goosebump |

### Quality, generated vs references (mean of 5 judges), against g5, g4 and g3

| Dimension | g6 generated | g6 references | g6 gap | g5 generated | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|
| melody | 5.80 | 6.60 | +0.80 | 5.53 | +1.47 | +1.55 | +1.40 |
| harmony | 6.55 | 6.00 | -0.55 | 6.17 | +1.03 | +0.73 | +0.70 |
| form | 6.12 | 6.50 | +0.38 | 5.25 | +1.55 | +2.00 | +0.77 |
| development | 5.80 | 6.50 | +0.70 | 5.62 | +1.58 | +1.75 | +1.10 |
| performance | 6.08 | 6.00 | -0.08 | 5.38 | +1.62 | +1.35 | +0.75 |
| overall | 5.95 | 6.40 | +0.45 | 5.40 | +1.70 | +1.80 | +1.33 |

Per packet, overall: SGVL 7.2, KFCM 6.8 (embers), GVPE 6.6, TLTG 6.4, QNFS 6.2, WHKZ 6.2, ZESN 6.0 (tide), XUMB 5.4,
XEDV 5.0, FUKP 4.6.

The generated set rose 0.55 overall (5.40 -> 5.95). Form and performance rose the most (+0.87 / +0.70). Three pieces
beat the tide reference, and SGVL beat both.

The gap closed partly because the same two references were rated lower: 6.40, against 7.10 in g4 and g5 (embers 7.6
-> 6.8, tide 6.6 -> 6.0). Against g5's reference level, the generated set is still about 1.1 under.

Counts: every judge counted 8 of 10, the truth (as in g4 and g5). The judges still find the generated pieces.

### The memorable moment

- **memorable:** the generated pieces 2.17 (g5 2.10), the references 2.30 (g5 2.60), a gap of +0.12.
  - SGVL 3.0: every judge named its motto and the one-bar silence before the climax.
  - TLTG 2.6.
  - Lowest: XUMB 1.6.
- **Hit rate:** 21 of 40 named moments sit on a planned move's bars (g5 16): motto 13, pause 9, goosebump 4, cascade 1.
  4 more fall only inside an ostinato section.
- **Shared flags: 24** (g5 27).
  - FUKP ~ SGVL ~ TLTG (all five judges): a climax that restates one cell.
  - QNFS ~ XUMB: A-major songs with a Dm6 colour.

### The fixes the judges name, ranked by judges x pieces

1. **The climax states no theme.** Named in 3 pieces by most judges.
   - GVPE's 'step' climax brings a new tune in G#m.
   - QNFS's reharmonised theme in a new key (G#m) was heard as "an arpeggio, not the theme": the reharmonisation plus
     the key move hid the head.
   - XUMB's chords climax read as new material, and the line breaks off at bar 43.
   - Wanted: the A1 head on top, recognisable, in the new key.
2. **A climax that loops one cell.**
   - FUKP (the waltz, 'sequence'): the D-Eb-C head cell 8-12 times over two chords. All five judges named it.
     `_anthem`'s 'sequence' climbs only while 2k < the peak level. Sung an octave up, the peak level is small, so the
     statements repeat at one pitch.
   - TLTG's climbing chorus: the same cell 3 times in 5 bars.
   - Wanted: the head twice, then a continuation that climbs to the peak.
3. **Themes without a phrase.**
   - XEDV: a tritone pickup followed by half-empty bars (bars 5, 9, 15, 29, 33, 35, 49).
   - WHKZ: the head a B-C-D-C neighbour figure.
   - SGVL: A1 after the motto wanders in small steps.
   - Wanted: a continuous 4 + 4-bar sung phrase with one long note.
4. **A3 after the climax literal or thin.**
   - Literal: WHKZ, QNFS, GVPE.
   - Thin: TLTG, where the right hand rests through bar 44 and bar 48.
   - Wanted: a return changed by the climax, reharmonised or with a new ending.
5. **A busy left hand in the build.** GVPE and QNFS have 12-13 attacks a bar: the bloom's 16ths, now in the build more
   often. The right hand leads them by only +1.5-2.2 dB there.
6. **Loudness plan.**
   - TLTG's intro already reaches v88 / C#6.
   - FUKP's B1 plays at climax level (mean v86).
   - XUMB's climax is flat at v98.
7. **The register.** The performer asks SGVL's climax to start in the 5th octave and save the octave-up for its peak
   bars (55 % of that climax at C6+). This is the first complaint in that direction since g2.

### What convinced

- SGVL: the motto as architecture, with a bar of silence before the climax (the pause) and the Gbm6 colour.
- Borrowed and remote harmony:
  - GVPE's D#m7b5, bVI-V and Neapolitan A3;
  - TLTG's chorus in Eb / Bb, reached by a pivot and left by A7;
  - QNFS's D#7 -> G#m, "well prepared" (the g5 key lead-in fix);
  - WHKZ's Dorian colour.
- The climax is now heard in the high register: no judge asked for "the climax an octave up" (g5: every judge).
- B1 louder than the climax was named once (FUKP), against three pieces in g5.

### Baseline for future rounds

48 seeds 64000-64047:
- **Register:** the A melody's median 73.7, the climax's 84.5, the climax 11.0 semitones over A1.
- **Climax:** the theme near the peak in 37 of 48.
- **Flow:** phrase_rests .79.
- **Rejects in set slots:** arc 41.4 %, breath 12.9 %.
- **Score:** 95.2.
- **Quality:** the generated overall 5.95 against the references' 6.40 (gap +0.45); memorable 2.17 against 2.30.

The open points are in TODO.md under "the new-age set, g6".

## Round g7 (2026-10-16, the theme at every climax, three references; renders `songs/_endless_piano/out/na_g7`, packets seed `blind-new-age-g7`)

The format is g6's, with a third hidden reference so that one round's yardstick drift averages out (g6 rated embers
and tide 0.7 lower than g5). The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 71000`, best-of-8.
- 3 references under new IDs: ZSKQ = pro-newage-embers, RRXV = pro-newage-tide (the g4-g6 pair), and EEDE =
  pro-newage-longing (the B minor 3/4 piece, g3's best-rated reference at 7.2; `make_packets_newage.py`: g7 on).

The same five judges (D:/tmp/g7_judges); no judge was shown a KEY. The mp3s by packet ID, the KEY and SCORES.txt are
in `songs/_endless_piano/out/blind_g7`. Scored with `score_round.py KEY_newage.json D:/tmp/g7_judges/verdicts --tells
--refs pro-newage-embers,pro-newage-tide` (new: the gap against each reference and against the g4-g6 pair).

Before the round: g6's fixes (docs/PIANIST_RULES.md "After round g6"): 'step' as the sung theme a whole step up; a
reharmonised climax keeps the head's chords; 'sequence' states the head twice, then the theme; the sung climax mostly
in C5-C6, the octave at the peak unit only; waltzes ~80-90 bars; no half-empty theme bars, no neighbour heads; the
first return after the climax varied; the bloom's left hand calmer; a soft intro, B under the climax, the climax
swelling into its peak.

| Piece | Packet | Form | Climax | Moves |
|---|---|---|---|---|
| 001 | KTBL | arch, A minor | theme in octaves | pause, goosebump |
| 002 | VWBU | song, F major | theme reharmonised | motto, goosebump |
| 003 | AARM | variations, Db major | theme in chords | motto, pause |
| 004 | FBHB | return, Ab major | theme sequenced | goosebump |
| 005 | JTQL | late, D major | theme augmented | motto, pause |
| 006 | LXCD | chorus, G major | theme in octaves | cascade |
| 007 | VJGT | variations, C minor waltz (86 bars) | theme reharmonised, in C major | ostinato |
| 008 | ZGLR | return, E major | theme in chords, a step up (F#) | cascade |

### Quality, generated vs references (mean of 5 judges), against g6, g5, g4 and g3

| Dimension | g7 generated | g7 refs (3) | g7 gap (3) | g7 gap (embers + tide) | g6 generated | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|
| melody | 5.75 | 6.73 | +0.98 | +0.65 | 5.80 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.58 | 6.67 | +0.09 | +0.12 | 6.55 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 6.05 | 6.73 | +0.68 | +0.45 | 6.12 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 5.75 | 6.60 | +0.85 | +0.85 | 5.80 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | 5.62 | 6.33 | +0.71 | +0.58 | 6.08 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | 5.83 | 6.73 | +0.91 | +0.67 | 5.95 | +0.45 | +1.70 | +1.80 | +1.33 |

Per packet, overall: EEDE 7.2 (longing), FBHB 7.0, ZSKQ 7.0 (embers), ZGLR 6.8, AARM 6.6, VWBU 6.4, RRXV 6.0 (tide),
KTBL 5.6, JTQL 4.8, VJGT 4.8, LXCD 4.6.

- **The yardstick held.** longing 7.2 (g3 7.2), embers 7.0 (g6 6.8, g5 7.6), tide 6.0 (g6 6.0, g5 6.6). Against the
  g4-g6 pair the gap is +0.67 (g6 +0.45), against all three +0.91.
- **The generated set as a whole stayed level** (5.95 -> 5.83). Its top half rose: FBHB ties embers, and four pieces
  (FBHB, ZGLR, AARM, VWBU) beat tide. Its bottom three (JTQL, VJGT, LXCD, 4.6-4.8) sit under g6's lowest (FUKP 4.6).
  The spread is wider: 4.6-7.0 (g6 4.6-7.2).
- Performance fell the most (6.08 -> 5.62): the climax runs and cascades (JTQL, LXCD, ZGLR) and the right hand only
  +1.2-2.7 dB over the left in B1 / the build.

Counts: 8, 9, 9, 8, 8 of 11 (truth 8): two composers took one reference for generated.

### The memorable moment

- **memorable:** the generated pieces 2.10 (g6 2.17), the references 2.33 (g6 2.30), a gap of +0.23.
  - FBHB 3.0: every judge named its oscillating hook, sequenced and lifted at the climax (39-42, Eb6).
  - AARM 3.0: the motto planted in bar 1, reharmonised, crowning the climax (33-34), closing the coda.
  - Lowest: JTQL and LXCD 1.0.
- **Hit rate:** 19 of 40 named moments sit on a planned move's bars (g6 21): motto 13, goosebump 9. 5 more fall only
  inside an ostinato section.
- **Shared flags: 28** (g6 24).
  - AARM ~ FBHB ~ VWBU (every judge): the planted gesture paid off at the climax, now read as one plan.
  - JTQL ~ LXCD ~ ZGLR (four judges): the end-of-climax cascade.

### What the g6 fixes did

- **The theme at the climax:** no judge named a 'step' or a reharmonised climax as new material. ZGLR's whole-step lift
  into F# major ("gives the theme a new meaning") and FBHB's sequence ("developed by sequence rather than copied") were
  praised. FUKP's g6 loop is gone. The cell count at the climax is 1-3 in every piece.
- **The register:** no judge asked for more height, and the performer named ZGLR's climax "keeps the high notes rare
  (5 % at C6+)". The only C6 complaint was JTQL's climax at 37 % - 'augment' with a long held top. The references
  drew the high-note complaints this time (tide's B1 / build, embers' A3 / build).
- **The returns:** the post-climax return was not called literal in any piece. Copied bars moved earlier: LXCD A2 =
  A1 (24-26 = 4-6), VWBU's four A statements.
- **Loudness:** no loud intro and no B1 at climax level was named. FBHB's climax "starts soft and builds the same
  figure higher". JTQL's climax starting at v51 was named once (the swell from an 'augment' long note).
- **The waltz:** VJGT at 86 bars (g6 FUKP 99); "87 bars of slow harmonic rhythm feel long" once.

### The fixes the judges name, ranked by judges x pieces

1. **Themes without a profile.** All five judges, 4-5 pieces. JTQL circles D5-E5, LXCD A4-B4 (bars 8-12), VJGT stays
   in G4-D5, VWBU's E5-D5-E5. Wanted: a head of 1-2 bars with one leap and a held peak note (FBHB, ZGLR, EEDE). The
   g6 rule (no neighbour head in its first 4 notes) catches only the tightest case.
2. **The climax as gestures.** All five judges: JTQL (44-51: runs at 45 / 51, held fortissimo single notes 46-47),
   LXCD (45-48, a cascade into the left hand's range, a doubled D4), ZGLR's bar-40 cascade, VWBU 48 / 52. The cascade
   is a fault in all its g7 appearances (3 of 3).
3. **The climax too early, a long tail.** KTBL at 57 % (the arch) followed by a louder A2; tide (a reference) too.
4. **Copied A bars and too many A statements.** LXCD 24-26 = 4-6, VWBU 11-14 / 62-65, KTBL 41-48 against 13-21.
5. **Returns that sink.** JTQL A3 at F#4-G4 (52-53), VJGT A3 quiet and low, ZGLR 43-44.
6. **The left hand still close to the melody** in B1 / the build (AARM B1 +1.2 dB, JTQL build +1.3, FBHB +2.7).
7. **Holes and artefacts** (the statistician): RH rests KTBL 20 / 22, AARM 46, VJGT 64 (inside the climax); LXCD 59
   stops mid-bar; repeated-chord comping (JTQL 41, VJGT 32).

### What convinced

- FBHB's hook and its sequenced climax; AARM's motto as architecture with a recurring Gbm6; VWBU's repeated-note motto
  and its earned bVI Db; ZGLR's appoggiatura hook and the lift to F# major.
- Borrowed colour again: Dbm6 (FBHB), Gbm6 (AARM), Am6 (ZGLR), the Neapolitan Bb (KTBL), VJGT's parallel-major
  climax with a bIII colour.

### Baseline for future rounds

48 seeds 64000-64047 / 48 set slots from 72000 (`tells_newage.py --slots 6 --set-n 8`):
- **Register:** the climax at C6+ 0.27 / 0.27, its longest C6+ run 1.8 / 1.6 bars (max 4).
- **Climax:** the theme 0.83 / 0.82, at the peak 0.71 / 0.69; the swell 22.7 / 24.2 velocity steps.
- **Returns:** the post-climax return note for note 0.10 / 0.05.
- **Left hand:** the build 8.4 / 8.6 attacks a bar (max 11).
- **Rejects in set slots:** arc 43.4 %, breath 11.3 %.
- **Score:** 95.3 / 95.6.
- **Quality:** the generated overall 5.83 against the three references' 6.73 (gap +0.91), against embers + tide +0.67;
  memorable 2.10 against 2.33.

The open points are in TODO.md under "the new-age set, g7".

## Round g8 (2026-10-16, a theme with a profile, the climax at two thirds; renders `songs/_endless_piano/out/na_g8`, packets seed `blind-new-age-g8`)

g7's format, the same three references under new IDs. The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 73000`, best-of-8.
- 3 references: XRSP = pro-newage-embers, MZMT = pro-newage-tide, BSFW = pro-newage-longing.

The same five judges (D:/tmp/g8_judges); no judge was shown a KEY. The mp3s by packet ID, the KEY and SCORES.txt are
in `songs/_endless_piano/out/blind_g8`. Scored with `score_round.py KEY_newage.json D:/tmp/g8_judges/verdicts --tells
--refs pro-newage-embers,pro-newage-tide`. New in the packets: a bar with no right-hand onset but a note held over
half of it from the bar before prints `(tied: ...)`, not `rest` (g7's "RH holes" were partly such ties).

Before the round: g7's fixes (docs/PIANIST_RULES.md "After round g7"): A heads with a profile (a leap of a 4th+, the
top note held, no 2-3 note band; `composer.HEAD_PROFILE`, 0.21 -> 0.94 of the heads over 48 seeds); no 'augment' and
no cascade at the climax; the arch's climax at ~0.68 of the piece and every section after the climax 2 dB under the
loudest one before it; the returns before the climax varied over every unit; returns not sinking over 3 semitones;
the melody ~5 dB over the left hand in B1 / the build (`BALANCE`); RH holes filled outside phrase ends, the pulse
comping on two alternating dyads.

| Piece | Packet | Form | Climax | Moves |
|---|---|---|---|---|
| 001 | LXAN | variations, Db major | theme in chords | pause, goosebump |
| 002 | JKGC | chorus, E major | theme reharmonised (C major) | motto, ostinato |
| 003 | EUNP | song, G minor | theme in octaves (G major) | motto, pause, goosebump |
| 004 | DMZT | return, C major | theme sequenced (Ab) | ostinato, pause |
| 005 | NSFY | arch, G major | theme in chords (Eb) | ostinato |
| 006 | PKCG | variations, Bb minor | theme reharmonised | goosebump |
| 007 | ECYA | song, C# minor waltz | theme in octaves | motto |
| 008 | ZACW | late, A minor | theme sequenced | - |

### Quality, generated vs references (mean of 5 judges), against g7-g3

| Dimension | g8 generated | g8 refs (3) | g8 gap (3) | g8 gap (embers + tide) | g7 generated | g7 gap (3) | g7 gap (e + t) | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| melody | 6.00 | 6.60 | +0.60 | +0.60 | 5.75 | +0.98 | +0.65 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.50 | 6.47 | -0.03 | +0.20 | 6.58 | +0.09 | +0.12 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 5.97 | 6.07 | +0.09 | +0.12 | 6.05 | +0.68 | +0.45 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 5.88 | 6.27 | +0.39 | +0.53 | 5.75 | +0.85 | +0.85 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | 5.95 | 6.20 | +0.25 | +0.15 | 5.62 | +0.71 | +0.58 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | 5.88 | 6.27 | +0.39 | +0.42 | 5.83 | +0.91 | +0.67 | +0.45 | +1.70 | +1.80 | +1.33 |

Per packet, overall: DMZT 6.8, XRSP 6.8 (embers), EUNP 6.6, PKCG 6.6, BSFW 6.2 (longing), ZACW 6.2, LXAN 6.0,
MZMT 5.8 (tide), ECYA 5.0, JKGC 5.0, NSFY 4.8.

- **The gap halved** against all three references (+0.91 -> +0.39) and fell against the g4-g7 pair (+0.67 -> +0.42),
  the smallest yet. Part of it is the yardstick: the references fell 6.73 -> 6.27, mostly longing (7.2 -> 6.2);
  embers 7.0 -> 6.8, tide 6.0 -> 5.8. The generated set rose a little (5.83 -> 5.88), its melody (5.75 -> 6.00) and
  performance (5.62 -> 5.95) the most - the two dimensions the g7 fixes aimed at.
- **The top half:** DMZT ties embers; EUNP, PKCG over longing; five pieces at or over tide. The bottom three (ECYA,
  JKGC 5.0, NSFY 4.8) sit above g7's (4.6-4.8). Spread 4.8-6.8 (g7 4.6-7.0).
- Counts: 8 of 11 from every judge (truth 8).

### The memorable moment

- **memorable:** the generated pieces 2.27 (g7 2.10), the references 2.27 (g7 2.33): **level for the first time**.
  - DMZT 3.0: every composer named the head's bar-4 climb sung in the bVI key at the climax, rising to G6.
  - EUNP 2.8: the motto (A5-A5-Bb5-G5-G5) planted, back in four functions.
  - ZACW 2.8: the neighbour-note head paid off an octave up (49-50) - a piece with no planned move.
  - Lowest: NSFY 1.2 (no judge's moment on its theme), ECYA and JKGC 1.8.
- **Hit rate:** 13 of 40 named moments sit on a planned move's bars (g7 19): motto 11, goosebump 3, pause 2. The drop
  is the point of the round: 12 more name **the theme sung at the climax** (DMZT, PKCG, ZACW, LXAN), which is the
  anthem, not a signature move.
- **Shared flags: 30** (g7 28). DMZT ~ PKCG ~ ZACW (~ JKGC, LXAN) from four judges: "the theme returns at the
  climax, an octave up / in a new key" is now heard as the set's common plan. g7's cascade cluster is gone.

### What the g7 fixes did

- **The theme profile:** no judge called a head a circled band in DMZT, LXAN ("a truly singable Yiruma-like head"),
  PKCG, ZACW ("a clear Einaudi-like neighbour-note hook"). Still named: EUNP's A1 "circles A4-D5" (all five; its
  head is the motto, the A body around it low), ECYA "no hook" (the waltz), NSFY's head "awkward". The profile holds
  the head's first 2 bars only; the rest of the A statement is not checked.
- **The climax content:** no cascade, no half-speed climax named. The theme was heard at the climax in 5 of 8; three
  were read as new material: NSFY's Eb line, JKGC's C-major climax, EUNP's G-major line (the octaves 'theme'
  anthem where the key change bent its intervals). ECYA's waltz opened its climax on two held notes for 2 bars each.
  PKCG's runs at 34-36 (the performer's connecting notes over the octave line) were named by two judges.
- **The climax placement:** no "too early" complaint. The arch piece (NSFY) now has the opposite problem: a 10-bar
  tail after a 16-bar build + climax, "rushed".
- **Copies:** no copied A bars named before the climax. ZACW's A2 / A3 restate the head "note for note" (3 judges);
  the head is the same, only the bars after it are rewritten.
- **Returns:** no sinking return named. The performer named NSFY bar 22 (B1's RH under the LH register).
- **Hand balance:** the left hand under the melody was named once in B1 (ECYA +1.9 dB, the waltz) and in A sections
  (DMZT A2 +3.0, JKGC A3 +2.3, NSFY A2 +1.7): the A sections are now the closest.
- **Holes:** named inside the climax / build (JKGC 37 / 42, LXAN 36) and in B1 / A2 (PKCG 16 / 24). The packets'
  tied notation removed the false ones; these are real silences.

### The fixes the judges name, ranked by judges x pieces

1. **The climax built from the head everywhere.** All five, 4 pieces: NSFY, JKGC (new tunes in the bVI / bIII key),
   EUNP (a new line), ECYA (held notes). A sung climax must keep the head's intervals after a key change.
2. **Right-hand holes inside the build and the climax.** Four judges: JKGC 37 / 42, LXAN 36, PKCG 16 / 24.
3. **The busy 16th left hand under the theme** (DMZT A1-A3, 14-16 attacks a bar; all five) and the A-section hand
   balance (+1.7-3.0 dB).
4. **A returns that restate the head note for note** (ZACW 9 / 27, 3 judges) and four static bars on one chord
   (ZACW 15-18, 4 judges).
5. **Stock B sections:** JKGC's Am-F-C-G pop loop (4 judges), ZACW's diatonic loop.
6. **Proportions:** NSFY's rushed tail after the arch climax (B2 4 + A2 6); LXAN's short, low climax without a build;
   ECYA's 14-bar blocks.
7. **Artefacts:** DMZT 52's lone F6 over a silent left hand (all five); PKCG 34-36 two-octave jumps inside a beat.

### What convinced

- DMZT's climax: the head carried into Ab via Fm7-Eb7, then the Fm6 plagal close. EUNP's Picardy G-major climax and
  the motto framing it. PKCG's Neapolitan Cb and the head's tail sung an octave up. LXAN's held Cb6 over Db7 with the
  left hand silent before the climax. ZACW's sung right hand in thirds and sixths (the performer: "the best sung
  right hand").

### Baseline for future rounds

48 seeds 64000-64047 / 48 set slots from 72000 (`tells_newage.py --slots 6 --set-n 8`):
- **Heads:** a profile 0.94 / 1.00 planned, 0.50 / 0.69 played.
- **Climax:** the theme 0.84 / 0.84, at the peak 0.75 / 0.875; no 'augment', no cascade; the arch's peak at 0.68 /
  0.65 of the piece.
- **Hands:** the melody over the left hand in B1 5.1 / 5.3 dB, in the build 4.6 / 4.5.
- **Rejects in set slots:** arc 37.1 %, breath 12.9 %.
- **Score:** 95.6 / 95.0.
- **Quality:** the generated overall 5.88 against the three references' 6.27 (gap +0.39), against embers + tide
  +0.42; memorable 2.27 against 2.27.

The open points are in TODO.md under "the new-age set, g8".

## Round g9 (2026-10-16: the head kept as played, the climax's arrival per piece, B with a destination; renders `songs/_endless_piano/out/na_g9`, packets seed `blind-new-age-g9`)

The format is g8's, with the same three references under new IDs. The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 75000`, best-of-8.
- 3 references: KUDQ = pro-newage-embers, UMWA = pro-newage-tide, DWXT = pro-newage-longing.

The same five judges ran in D:/tmp/g9_judges, and no judge was shown a KEY. The mp3s by packet ID, the KEY and
SCORES.txt are in `songs/_endless_piano/out/blind_g9`. Scoring: `score_round.py KEY_newage.json
D:/tmp/g9_judges/verdicts --tells --refs pro-newage-embers,pro-newage-tide`. The packets have two new notation rules:
- An inner voice struck under a held, higher right-hand note prints as `(under)`.
- A downbeat struck a hair early prints on its downbeat. g8's "holes" in JKGC, PKCG and LXAN were such downbeats,
  printed at 4.92 in the bar before.

Before the round, g8's fixes went in (docs/PIANIST_RULES.md "After round g8"):
- The played head keeps its profile (0.50 -> 0.92). `articulate` no longer cuts the held top note when an inner voice
  moves under it.
- The anthem keeps its intervals through a key move.
- A has a thin ostinato and sits at least 4 dB over its left hand. The score's hand_bal range is 3-6.
- The returns are rewritten over the head too. A stalled chord moves after 3 bars.
- The hook blocks get a destination (B with one: 0.33 -> 0.79).
- The arch's last A is 8-10 bars, and a variations climax grows to 12 bars.
- The pause's high note belongs to the climax seam only.
- The climax's ARRIVAL is a set draw: direct / pause / key / dominant / fragment.

| Piece | Packet | Form | Climax (anthem, arrival) | Moves |
|---|---|---|---|---|
| 001 | KNUB | arch, Bb major | reharmonised, after a key move (C major) | motto, pause (coda), goosebump |
| 002 | QKNJ | song, E major | in chords, direct | ostinato |
| 003 | AHVN | late, A minor | in octaves, after a pause | motto, pause, goosebump |
| 004 | LMUP | chorus, C major | sequenced, after a held dominant | ostinato, pause (return) |
| 005 | KVRY | return, E major | reharmonised, after a key move (G) | ostinato, goosebump |
| 006 | JRCY | arch, A major | in chords, direct | motto |
| 007 | FCJZ | late, Db major waltz | in octaves, the head's fragment first | - |
| 008 | NMPC | song, F# minor | sequenced, after a held dominant | - |

### Quality, generated vs references (mean of 5 judges), against g8-g3

| Dimension | g9 generated | g9 refs (3) | g9 gap (3) | g9 gap (embers + tide) | g8 generated | g8 gap (3) | g8 gap (e + t) | g7 gap | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| melody | 6.10 | 6.67 | +0.57 | +0.10 | 6.00 | +0.60 | +0.60 | +0.98 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.42 | 6.60 | +0.17 | -0.02 | 6.50 | -0.03 | +0.20 | +0.09 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 6.15 | 6.53 | +0.38 | +0.05 | 5.97 | +0.09 | +0.12 | +0.68 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 6.10 | 6.40 | +0.30 | +0.10 | 5.88 | +0.39 | +0.53 | +0.85 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | 5.78 | 6.33 | +0.56 | +0.42 | 5.95 | +0.25 | +0.15 | +0.71 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | **6.05** | 6.60 | +0.55 | **+0.15** | 5.88 | +0.39 | +0.42 | +0.91 | +0.45 | +1.70 | +1.80 | +1.33 |

Per packet, overall: DWXT 7.4 (longing), QKNJ 6.8, FCJZ 6.6, JRCY 6.4, UMWA 6.4 (tide), LMUP 6.2, KUDQ 6.0
(embers), NMPC 6.0, KNUB 5.8, AHVN 5.4, KVRY 5.2.

- **The generated set scored its highest yet: 6.05** (g8 5.88, g7 5.83). Against embers + tide the gap is the
  smallest yet, +0.15 (g8 +0.42): three generated pieces rate at or over tide and five at or over embers.
- **The gap against all three references grew, +0.39 -> +0.55.** The cause is longing, which moved 6.2 -> 7.4 (it
  was 7.2 in g3 and 6.2 in g8). The yardstick drifts by about a point per reference from round to round, so the
  embers + tide pair, judged in every round since g4, is the steadier gauge.
- **Performance is the one dimension that fell (5.95 -> 5.78).** The judges named heavy left hands in B1 and the
  climaxes, the climax entering softer than the build, and loud returns after a soft B2 (see below).
- Spread 5.2-6.8 (g8 4.8-6.8). Counts: 8 of 11 from every judge (truth 8).

### The memorable moment

- **memorable:** the generated pieces 2.42 (g8 2.27), the references 2.40 (g8 2.27). This is the first round in which
  the generated pieces are above the references.
  - FCJZ 3.0: the waltz's rising head, stated twice and then an octave up at the climax (the 'fragment' arrival).
  - JRCY 3.0: the motto (the rocking E-D cell), named by all five judges, in four sections at three registers.
  - QKNJ 3.0: the head (a rising sixth, held across the bar line), previewed in the intro and sung an octave up.
  - Lowest: KVRY 1.4 (its climax has no theme), KNUB 2.0.
- **Hit rate:** 17 of 40 named moments sit on a planned move's bars (g8 13): motto 13, goosebump 3, pause 3.
- **Shared flags: 25** (g8 30). The cluster is now AHVN ~ FCJZ ~ LMUP ~ QKNJ from all five judges: the head
  planted, then "A1 an octave up at the climax". The judges still hear the theme at the climax as the common plan,
  however it arrives. The arrival varies, but the payoff is the same octave-up statement.

### What the g8 fixes did

- **The head's profile as played:** no judge called QKNJ's, FCJZ's or LMUP's head a band. LMUP still reads as
  "generic arpeggio-and-step" to composerB. KVRY ("an awkward shape, no hook", four judges) and AHVN's A1 ("wanders",
  three judges) are named as heads without a cell. The profile rule (a leap, a held top) holds, but a REPEATED cell
  is what the judges ask for.
- **The climax after a key change:** KNUB's step-up to C was praised by four judges as "a real event". KVRY's
  chromatic-mediant climax (G / Cm) was praised as colour but heard as "new material, not the theme" by all five.
  NMPC's 'sequence' climax was heard as "a new cell" by four (the performer: "really is the theme"). The theme
  survives the key move in KNUB, but not in KVRY's reharmonised anthem or NMPC's sequence.
- **The A balance:** no busy 16th left hand under A was named. The heavy left hand moved to B1 (JRCY +2.1 dB, v92-99,
  all five; QKNJ +2.9) and to the climax's bass octaves (JRCY v102-106).
- **Returns, stalls, B loops:** no note-for-note return and no stalled chord were named, and no B was called a pop
  loop. QKNJ's climax "stays on the A1 loop" (the statistician).
- **Proportions:** no rushed arch tail (KNUB, JRCY). FCJZ's 16-bar waltz climax "sags" after its peak (three
  judges), and AHVN has 10 sections in 65 bars ("episodic", two judges).
- **Artefacts:** no lone high note and no two-octave jumps were named. RH holes: LMUP 48 (the climax's last bar, two
  judges) and LMUP 56.
- **The arrival:** the held dominant (LMUP, NMPC) and the key move (KNUB) were heard and praised. AHVN's pause led
  into a climax "softer than the build" (four judges).

### The fixes the judges name, ranked by judges x pieces

1. **The climax from the head after a reharmonisation or sequence** (KVRY 5 judges, NMPC 4, KNUB 1). The anthem's
   'reharm' and 'sequence' kinds in another key lose the head's contour.
2. **The dynamics around the climax.**
   - It enters under the build: AHVN after its pause, four judges; KVRY's LH at v15.
   - A return or the coda comes in loud after a soft B2: KNUB at v94-106, four judges.
   - NMPC's peak is hammered at v108-114 for four bars, three judges.
3. **The heavy left hand in B1 and at the climax:** JRCY (all five), QKNJ (two). B1 is also louder than the build
   (JRCY +2.3 vs +1.0 LU).
4. **The climax's way out.**
   - QKNJ drops from A6 to C#5 in one bar, four judges.
   - LMUP ends the climax on an empty RH bar, two judges.
   - NMPC lands on an unresolved D over C#, one judge.
   - FCJZ's last 6 climax bars sag, three judges.
5. **Thick climax chords:** 10-12 RH notes a bar (QKNJ, KNUB, JRCY; statistician, performer, composerB).
6. **The return after the climax without the head** (FCJZ A2, JRCY A2; three judges).
7. **Heads without a repeated cell** (KVRY, AHVN A1, LMUP).

### What convinced

- QKNJ's head, previewed in the intro, varied in A2, sung up an octave and reharmonised in C#m in A3 ("the best
  developed theme in the set", composerC).
- FCJZ's modal mixture (Gbm6, Db7/Cb, Cbadd9) and its climax rising out of the head's cell.
- JRCY's rocking motto as a structural signal.
- KNUB's step-up key change.
- NMPC's C#-pedal build ("the strongest arc", the performer).
- AHVN's playing: "the best-played piece in the set", with thirds and sixths under the tune and a real coda
  ritardando.

### Baseline for future rounds

Measured on 48 seeds 64000-64047 / 48 set slots from 72000:
- **Heads:** played with a profile 0.92 / 0.875.
- **Climax:** the theme 0.845 / 0.83, at the peak 0.79 / 0.77, in another key 0.93 / 0.71. Every 8-piece set plays
  all five arrivals.
- **Hands:** A over the left hand 5.3 / 5.3 dB, the weakest A section 4.2 / 4.1, hand_bal 5.2 / 5.2.
- **Form:** B with a destination 0.79 / 0.94, the arch's tail 16.6 / 15.8 bars.
- **Rejects in set slots:** arc 34.0 %, breath 12.9 %.
- **Score:** 95.5 / 95.6.
- **Quality:** the generated overall 6.05 against the three references' 6.60 (gap +0.55), against embers + tide
  +0.15; memorable 2.42 against 2.40.

The open points are in TODO.md under "the new-age set, g9".

## Round g10 (2026-10-16: the climax from the head, its dynamics, the way out; renders `songs/_endless_piano/out/na_g10`, packets seed `blind-new-age-g10`)

The format is g9's, with the same three references under new IDs. The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 77000`, best-of-8.
- 3 references: LZVQ = pro-newage-embers, ZJJB = pro-newage-tide, QKTJ = pro-newage-longing.

The same five judges ran in D:/tmp/g10_judges, and no judge was shown a KEY. The mp3s by packet ID, the KEY and
SCORES.txt are in `songs/_endless_piano/out/blind_g10`. Scoring: `score_round.py KEY_newage.json
D:/tmp/g10_judges/verdicts --tells --refs pro-newage-embers,pro-newage-tide`.

Before the round, g9's fixes went in (docs/PIANIST_RULES.md "After round g9"):
- The tells follow the head's contour and rhythm at the climax (`contour_match`). The climax follows the head: 0.62 ->
  0.83. Every sung climax is a theme kind.
- The dynamics around the climax:
  - a pause at the seam goes into a forte entry;
  - the climax opens over the last bars before it;
  - after the climax, each section stays under the one before;
  - one accented peak.
  Peak hammering fell 3.6 -> 1.7 bars.
- The left hand is under the right hand -6 outside A. B1 sits under the build (-0.3 -> -1.1 dB).
- The way out: the peak is never in the last unit, and the bars after it fall gradually (the largest drop 10.2 -> 7.3
  semitones).
- Climax chords at most 8 / 6 RH notes a bar.
- The first return after the climax states the head (0.04 -> 0.54).
- Heads restate their bar-1 rhythm in bar 2 (`half_cell`).
- A new climax payoff: 'canon'.

Of the 8 pieces, 2 were picked from 2-3 candidates: the best-of-8 rerolled the arc / breath rejects.

| Piece | Packet | Form | Climax (anthem, arrival) | Moves |
|---|---|---|---|---|
| 001 | VBJZ | arch, Ab major | in chords, direct | motto |
| 002 | ZVNR | return, E major | sequenced, after a pause | motto, pause |
| 003 | XWPQ | chorus, A minor | in octaves, after a held dominant | goosebump |
| 004 | VEAS | song, Gb major | canon, the head's fragment first | ostinato |
| 005 | CDSQ | variations, A major | in chords, direct | pause (return), goosebump |
| 006 | HABQ | return, D major | reharmonised, after a key move (F) | ostinato |
| 007 | ELNQ | arch, G minor waltz | sequenced, after a pause | motto, pause |
| 008 | HJJR | song, C# minor | in octaves, the head's fragment first | ostinato, goosebump |

### Quality, generated vs references (mean of 5 judges), against g9-g3

| Dimension | g10 generated | g10 refs (3) | g10 gap (3) | g10 gap (embers + tide) | g9 generated | g9 gap (3) | g9 gap (e + t) | g8 gap | g7 gap | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| melody | 6.00 | 6.73 | +0.73 | +0.30 | 6.10 | +0.57 | +0.10 | +0.60 | +0.98 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.62 | 6.60 | -0.03 | -0.12 | 6.42 | +0.17 | -0.02 | -0.03 | +0.09 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 6.28 | 6.27 | -0.01 | -0.28 | 6.15 | +0.38 | +0.05 | +0.09 | +0.68 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 6.08 | 6.47 | +0.39 | +0.52 | 6.10 | +0.30 | +0.10 | +0.39 | +0.85 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | **6.10** | 6.33 | +0.23 | +0.20 | 5.78 | +0.56 | +0.42 | +0.25 | +0.71 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | 5.97 | 6.67 | +0.69 | +0.43 | 6.05 | +0.55 | +0.15 | +0.39 | +0.91 | +0.45 | +1.70 | +1.80 | +1.33 |

Per packet, overall: QKTJ 7.2 (longing), HABQ 6.8, LZVQ 6.8 (embers), VBJZ 6.6, VEAS 6.6, ZVNR 6.6, CDSQ 6.4, ZJJB
6.0 (tide), HJJR 5.2, XWPQ 5.0, ELNQ 4.6.

- **Performance, the dimension that fell in g9, rose the most: 5.78 -> 6.10.** The gap fell from +0.56 to +0.23. No
  judge named:
  - a heavy B1 left hand;
  - a climax softer than the build;
  - a loud return after a soft B2;
  - a hammered peak;
  - a drop out of the climax.
- **Harmony and form are at parity with the references** (-0.03 and -0.01), and both are over embers + tide.
- **The overall level is unchanged: 5.97** (g9 6.05). The generated set is wider than in g9:
  - six pieces at 6.4-6.8 (g9: four at 6.2-6.8);
  - three at 4.6-5.2 (HJJR, XWPQ, ELNQ), all named for a weak head or copied returns.
- **The gap against embers + tide is +0.43** (g9 +0.15). The pair's mean rose 6.2 -> 6.4: embers 6.0 -> 6.8, tide
  6.4 -> 6.0. The yardstick again drifts by about 0.5-1 point per reference between rounds.
- Melody is the largest gap (+0.73). Longing alone is +1.60 on melody.
- Counts: 8 of 11 from every judge (truth 8), as in every round since g7.

### The memorable moment

- **memorable:** the generated pieces 2.38 (g9 2.42), the references 2.33 (g9 2.40). The generated pieces are ahead
  for the second round in a row.
  - HABQ 3.0: the head (a turn onto a held E5), transformed in the F-major climax.
  - VBJZ 3.0: the C-Bb oscillation motto, planted in the intro and recalled five times (all five judges).
  - VEAS 2.8: the head climbing its own sequence at the climax (the canon / fragment payoff).
  - Lowest: HJJR 1.6, ELNQ 1.8, XWPQ 1.8.
- **Hit rate:** 30 of 40 named moments sit on a planned move's bars (g9 17): goosebump 15, motto 15, pause 10.
- **Shared flags: 31** (g9 25). The cluster is CDSQ ~ HABQ ~ VEAS ~ ZVNR (four judges): bright major pieces whose
  head comes back an octave up or sequenced. XWPQ ~ ELNQ (three judges) is the "shapeless head" pair.

### What the g9 fixes did

- **The climax from the head:**
  - Praised:
    - VEAS's climax was called "built directly from the head by sequence" (three judges).
    - HABQ's reharmonised climax in F was heard as "the head transformed at the top" (four judges). g9's KVRY, also
      reharmonised in another key, was heard as new material by all five judges.
    - The climaxes of ZVNR, CDSQ and VBJZ quote the head.
  - Still missed:
    - ELNQ's climax is "loud new material" (two judges). Its head never forms, so there is nothing to recall.
    - HJJR's climax is "a new scale climb, not the theme" (the statistician; `clx_head` 1.0).
    - XWPQ (`clx_head` 0.0: an octaves anthem after a held dominant).
- **The dynamics:** none of g9's four complaints came back. Two new ones:
  - XWPQ's build "does not build" (v38-56, +0.5 LU; two judges).
  - CDSQ spends its register and loudness early: B1 at F#6, and A2 at v105 louder than most of the climax (two
    judges).
- **The left hand:** no heavy B1 or bass octaves were named. The performer flags thin balances instead:
  - HABQ A2 at +3.3 dB;
  - HJJR's build at +2.2 dB, with a 16th LH under RH inner arpeggios.
- **The way out:** no drop and no empty last RH bar. XWPQ has a whole bar of RH rest INSIDE its climax (bar 41, after
  the turn, before the peak; three judges).
- **Thick chords:** none named at the climax. Density moved to B1 and the build:
  - VEAS's B1 at 11.9 RH notes a bar (three judges);
  - ZVNR's build at 9.7, with RH inner arpeggios (two judges).
- **The return after the climax:** the head is back in it, but the judges now count the copies.
  - The statistician counts note-for-note bars in HJJR, HABQ, ZVNR, XWPQ and VBJZ.
  - HJJR's four near-identical A statements were named by all five judges.
  - `ret_head_copy` is 0 in all 8 pieces, because it compares heads only.
- **Heads:**
  - ELNQ's waltz head was called shapeless by all five judges.
  - VBJZ's head is off-beat fragments (four judges).
  - VEAS's third bar is a Cb-Db oscillation (three judges).
  - The tells pass all 8: head_cell 1, head_prof 1.
- **Set variety:** five anthems (chords, sequence and octaves twice each, canon and reharm once) and five
  arrivals. The shared flags still rose, 25 -> 31.

### The fixes the judges name, ranked by judges x pieces

1. **Copied returns:** A2 / A3 / A4 copy A1's bars beyond the head (HJJR 5 judges, HABQ / ZVNR / XWPQ / VBJZ the
   statistician, CDSQ's B1 copying itself).
   - Measure bar copies over the whole return, not only the head.
   - Then vary every return past its head, and cut or reharmonise a fourth A statement in the 'song' layout (HJJR,
     4:48).
2. **The head itself** (ELNQ 5, VBJZ 4, VEAS 3, XWPQ 2, HABQ 1): a head that starts off the beat in fragments, a
   two-note neighbour shuffle, or a waltz head that never lands on a chord tone. HEAD_PROFILE checks a leap, a held
   top and the bar-1 rhythm. It should also want:
   - a downbeat arrival;
   - no 4+ note two-pitch oscillation;
   - a cadence on a chord tone by bar 4.
3. **The energy before the climax:**
   - XWPQ's build is softer than A2 (two judges).
   - CDSQ has F#6 in B1 and v105 in A2 (two judges).
   - XWPQ's empty RH bar inside the climax (three judges).
   `tail_under` / `build_over` check only sections; the register and velocity peaks before the climax are not
   checked.
4. **Short last returns and codas:**
   - ZVNR's and HABQ's A3 are 6 bars and do not cadence home (four judges).
   - VBJZ's 3-bar coda after a rest bar (two judges).
   - CDSQ's coda without the head (one judge).
5. **Dense RH textures outside the climax** (VEAS B1, ZVNR's build, HJJR's build: six judge-mentions). CLIMAX_NOTES
   caps only the climax.
6. **Length:** ELNQ's 95-bar waltz (three judges), HJJR's 4:48 at 59 BPM (with #1).
7. **The stock scale run** at VBJZ bar 36 (G6 -> Db5 in 16ths; two judges).

### What convinced

- HABQ's bIII key move for the climax, prepared by Gm7-C7, with the head transformed at the top.
- VEAS's sequence climax and its IV-iv frame (Cbmaj7-Cbm6).
- VBJZ's motto as the form's binding thread.
- ZVNR's planted intro gesture returning at the climax, and its borrowed Am6.
- CDSQ's colour chords (Gm6, Dm6) and the head reharmonised at every return.
- The playing: "a voiced right hand (thirds and sixths, inner voices under held tops)" (the performer, CDSQ).

### Baseline for future rounds

Measured on 48 seeds 64000-64047 / 48 set slots from 72000:
- **Climax:**
  - it follows the head 0.83 / 0.85, and the head is at its peak 0.60 / 0.74;
  - entry +1.1 / +1.25 dB over the build;
  - peak hammering 1.7 / 1.4 bars;
  - the largest drop 7.3 / 7.4 semitones;
  - 6.5 RH notes a bar.
- **Hands:** B1 -1.1 / -1.05 dB under the build.
- **Returns:** the first return after the climax states the head 0.54 / 0.58. Heads with a repeated cell 0.85 / 0.79.
- **Rejects in set slots:** arc 36.7 %, breath 14.1 %.
- **Score:** 95.3 / 95.3.
- **Quality:**
  - the generated overall 5.97 against the three references' 6.67 (gap +0.69), and +0.43 against embers + tide;
  - performance 6.10 (gap +0.23);
  - memorable 2.38 against 2.33.

The open points are in TODO.md under "the new-age set, g10".

## Round g11 (2026-10-16: the floor - copied returns, head shape, the energy before the climax, the endings; renders `songs/_endless_piano/out/na_g11`, packets seed `blind-new-age-g11`)

The format is g10's, with the same three references under new IDs. The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 79000`, best-of-8.
- 3 references: YACF = pro-newage-embers, ZYBJ = pro-newage-tide, WWVM = pro-newage-longing.

The same five judges ran in D:/tmp/g11_judges, and no judge was shown a KEY. The mp3s by packet ID, the KEY and
SCORES.txt are in `songs/_endless_piano/out/blind_g11`. Scoring: `score_round.py KEY_newage.json
D:/tmp/g11_judges/verdicts --tells --refs pro-newage-embers,pro-newage-tide`.

Before the round, g10's fixes went in (docs/PIANIST_RULES.md "After round g10"). They target the floor, the bottom
three of g10 (HJJR, XWPQ, ELNQ):
- Returns are compared bar by bar against every earlier A statement. A copied body is varied, and a piece has at most
  3 A statements over 4 minutes. Return bodies copying an earlier bar: 0.078 -> 0.005.
- The head's shape (`composer.HEAD_SHAPE`, best-of-N in the A1 fit): downbeat arrivals, no a-b-a-b, a chord-tone
  cadence by bar 4. 0.44 -> 0.92 of the heads pass.
- The energy before the climax: the build is never under the sections before it, and those stay 3 semitones / 12
  velocity under the climax's peak.
- The endings: the last A has 8+ bars and closes V7 -> I (0.125 -> 1.0); the coda has 6+ bars and the head
  (codas under 6 bars 0.85 -> 0).
- RH density capped in B1 / the build (7.3 -> 5.9 notes a bar); waltzes at most 95 bars; no cadenza run at a sung
  climax.
- Two new set draws: 'peak' (the climax peak 0 / 2 / 4 under the ceiling) and 'big' (the climax's left-hand
  figure).

The g11 set measures clean on the g10 tells: every head has a downbeat and a cadence, 7 of 8 pass the whole shape
(ERDL has an oscillation), return bodies copy 0.033, every last A is 8+ bars and home, every coda 6 bars, B1 5.4 RH
notes a bar, no stock run, the waltz 84 bars. Of the 8 pieces, 6 needed 1-2 rerolls (arc / breath).

| Piece | Packet | Form | Climax (anthem, arrival) | Moves |
|---|---|---|---|---|
| 001 | LESU | variations, G minor | canon, after a held dominant | motto, ostinato, goosebump, pause (coda) |
| 002 | WNTP | arch, E major | sequenced, after a key move | goosebump (A3) |
| 003 | ERDL | chorus, A minor | in chords, the head's fragment first | motto |
| 004 | CNWE | late, F major | in octaves (a step up), direct | ostinato, goosebump |
| 005 | NKTZ | return, G major | canon, after a pause | motto, ostinato, pause |
| 006 | PTCV | variations, E major | sequenced, after a key move (C) | pause (A4) |
| 007 | KTGG | song, Bb minor waltz | in chords (a step up), the head's fragment first | - |
| 008 | BFHK | late, D minor | in octaves, after a held dominant | - |

### Quality, generated vs references (mean of 5 judges), against g10-g3

| Dimension | g11 generated | g11 refs (3) | g11 gap (3) | g11 gap (embers + tide) | g10 generated | g10 gap (3) | g10 gap (e + t) | g9 gap | g8 gap | g7 gap | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| melody | 5.88 | 7.13 | +1.26 | +0.92 | 6.00 | +0.73 | +0.30 | +0.57 | +0.60 | +0.98 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.55 | 7.07 | +0.52 | +0.25 | 6.62 | -0.03 | -0.12 | +0.17 | -0.03 | +0.09 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 6.20 | 7.20 | +1.00 | +0.90 | 6.28 | -0.01 | -0.28 | +0.38 | +0.09 | +0.68 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 6.03 | 7.00 | +0.97 | +0.88 | 6.08 | +0.39 | +0.52 | +0.30 | +0.39 | +0.85 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | 5.88 | 6.67 | +0.79 | +0.72 | 6.10 | +0.23 | +0.20 | +0.56 | +0.25 | +0.71 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | 5.97 | 7.33 | +1.36 | +1.12 | 5.97 | +0.69 | +0.43 | +0.55 | +0.39 | +0.91 | +0.45 | +1.70 | +1.80 | +1.33 |

Per packet, overall: WWVM 7.8 (longing), YACF 7.2 (embers), ZYBJ 7.0 (tide), NKTZ 6.8, BFHK 6.4, LESU 6.4, CNWE 6.2,
WNTP 6.2, ERDL 5.8, PTCV 5.6, KTGG 4.4.

The generated mean of the bottom three, against earlier rounds:

| (from the per-packet overall lines) | g7 | g8 | g9 | g10 | g11 |
|---|---|---|---|---|---|
| bottom three (generated) | 4.73 | 4.93 | 5.47 | 4.93 | **5.27** |
| generated mean | 5.58 | 5.88 | 6.05 | 5.97 | 5.97 |
| references' mean (3) | 6.73 | 6.27 | 6.60 | 6.67 | **7.33** |

- **The generated level held: 5.97, as in g10. The floor rose 4.93 -> 5.27.** Five pieces are at 6.2-6.8, two at
  5.6-5.8, and one at 4.4 (KTGG, the waltz). The top fell: g10's best was 6.8 (HABQ), and only NKTZ reaches it here.
- **The references rose 6.67 -> 7.33**, all three: longing 7.2 -> 7.8, embers 6.8 -> 7.2, tide 6.0 -> 7.0. Every
  gap widened with them: +0.69 -> +1.36 against all three, +0.43 -> +1.12 against embers + tide. This round the
  judges contrasted the generated pieces more sharply with the references (composerA rated the references 8.0 overall,
  g10 ~7). The generated scores did not fall. The yardstick moved more than in any round since g5, so this round's
  gap does not compare well with g10's.
- Harmony stays the closest dimension (+0.52; +0.25 against embers + tide; tide is under the generated mean). Melody is
  again the largest (+1.26; longing alone +1.92).
- Counts: 8 of 11 from every judge (truth 8), as in every round since g7.

### The memorable moment

- **memorable:** the generated pieces 2.17 (g10 2.38), the references 2.67 (g10 2.33). The generated pieces had been
  ahead for two rounds; this round they are behind.
  - BFHK, LESU, NKTZ, WNTP 2.6: the head an octave up at the climax (LESU 38-39, NKTZ 39, WNTP's step-then-octave
    climb, BFHK's climb to D6 at 42).
  - Lowest: KTGG 1.4, PTCV 1.6, ERDL 1.8 - the three whose climax is not the head.
- **Hit rate:** 5 of 40 named moments sit on a planned move's bars (g10 30), all on ERDL's / NKTZ's motto; 4 more only
  inside an ostinato section. The judges named the climaxes' head statements, which are not counted as moves.
- **Shared flags: 30** (g10 31). Two clusters, each named by four or five judges:
  - BFHK ~ LESU ~ NKTZ ~ WNTP: the head an octave up at the climax, a reharmonised A3, a soft plagal or held close;
  - CNWE ~ KTGG ~ PTCV ~ WNTP: a key moved up for the climax and a modest head.

### What the g10 fixes did

- **Copied returns:** HJJR's case is gone, and no judge named four A statements or a return past its head copying
  A1. The statistician still counts copies in three places:
  - **every coda copies A1's bars 3-8** (BFHK, CNWE, ERDL, LESU, PTCV, WNTP: the statistician, six pieces). It
    comes from `CODA`: a short coda's head is A1's first units, played as they were, only softer. It is a fix's own
    tell.
  - NKTZ's A3 restates A1 note for note (one judge). ERDL's A2 restates A1 over nearly the same chords (one judge).
- **The head:** no off-beat fragments and no two-note shuffle were named. The 4/4 heads were called "pleasant rather
  than catchy" (CNWE, PTCV, ERDL), not shapeless. **The waltz head failed again:** KTGG's A1 is 1.9 RH attacks a bar,
  one long note per bar (all five judges). HEAD_SHAPE passes it: a downbeat, a held chord tone and no oscillation
  are all true of a line of whole notes.
- **The energy before the climax:** no build was called softer than A2, and no B1 or A2 was called too high or loud.
  The weak spot moved INTO the climax's first bars:
  - LESU's climax opens on three repeated D6s and sinks to D5 at v47-60, so it only starts at bar 36 (all five).
  - PTCV's climax enters at v54-64 (two).
  - KTGG's climax jumps v93 -> v120 in two bars (two).
- **The endings:** no short last A and no short coda was named. The coda's head now draws the copy flag (above).
  WNTP's 19 bars after a peak at 59% were named by two judges.
- **Density:** no dense B1 or build was named. CNWE's B1 left hand is 16ths at 10.7 attacks a bar (the performer).
- **Length and runs:** the waltz is 84 bars and nobody named the length; no stock run was named.
- **Set variety:** peaks were spread (86-93), but the octave-up head still reaches A6 in four pieces (LESU, NKTZ,
  CNWE, WNTP; four judges: "shrill", "glassy"). ERDL's climax sits at C6-G6 (35 % of its RH notes at C6+).

### The fixes the judges name, ranked by judges x pieces

1. **The climax is not the head** (PTCV 5 judges, KTGG 4, ERDL 3, NKTZ 35-38 2, CNWE 1). `clx_head` measures 1.0
   in all 8. Its window lets a climax pass when only its peak bars state the head. PTCV's 12-bar climax in C sings
   new scale material; KTGG's is a stepwise climb; ERDL's is high chord tones. These are the 'sequence' anthem after a key move,
   the waltz's 'step' and the 'chords' anthem after the 'fragment' arrival. Make the climax's first 4 bars state the
   head (moved into the key), and measure that window.
2. **The coda copies A1's head** (the statistician, six pieces). The CODA head should be varied as a return is
   (`_vary_changed` against `prior`): its head reharmonised, fragmented, or an octave down, never A1's bars as
   played.
3. **The climax peak is too high** (A6 in four pieces, ERDL at C6-G6; four judges). The octave-up head reaches A6
   when the head tops at A5. Cap the sung peak at E6 / F6 and play the octave-up head in octaves an octave lower when
   it would cross.
4. **The waltz head has no rhythm** (KTGG, all five). Add a rhythm check to HEAD_SHAPE: at least ~3 onsets a bar on
   average over bars 1-4 (3/4) and one bar with a short-long cell.
5. **The climax's first bars** (LESU 5, PTCV 2, KTGG 2): the climax should enter at full weight on the head, not on
   repeated top notes, and not sink before its peak. Also, no velocity jump of 25+ inside two bars.
6. **B1 without contrast or a hook** (WNTP 3, NKTZ 2, CNWE 2): B in the A section's register and chords, or long held
   notes over a two-chord seesaw.
7. **The tail after an early peak** (WNTP, peak at 59 %: two judges), and 4-bar B2s with no purpose.
8. **RH holes** (LESU 49, PTCV 32, WNTP 20, KTGG 18, BFHK 53): bars with only an inner voice or no melody.

### What convinced

- NKTZ's B section in Ab (bVI) through Cm7-Eb7, back through D7, and its Cm6 plagal close.
- LESU's hook over a lament bass, reharmonised in A3, crowned an octave up and laid to rest in the coda.
- BFHK's head planted in the intro and grown to the climax's D6; its hand balance "exemplary" (the performer).
- CNWE's F7/Eb bass, the borrowed Bbm6, the whole-step climax key and the Db colour in A3.
- WNTP's head turned into the climax by a key lift, and the Bm6-B7 / G-B7/D# turns home.
- KTGG's tonal plan (Cbmaj7 -> G7 -> a C-minor climax -> F7 back), the one strength of the waltz.

### Baseline for future rounds

Measured on 48 seeds 64000-64047 / 48 set slots from 72000 (docs/PIANIST_RULES.md "After round g10"):
- **Returns:** bodies copying an earlier bar 0.005 / 0.014; copied bars a piece 1.71 / 1.79.
- **Heads:** HEAD_SHAPE 0.92 / 0.90; profile 0.96 / 0.92.
- **Before the climax:** the build's melody +2.8 / +2.9 over the loudest section before it.
- **Endings:** the last A 8+ bars and home 1.0 / 1.0; codas under 6 bars 0 / 0.
- **Density:** B1 / build RH notes a bar 5.9 / 6.9.
- **Climax:** it follows the head 0.82 / 0.86; the highest note 91.1 / 90.75.
- **Rejects in set slots:** arc 40.2 %, breath 7.8 % (kept 52.0 %).
- **Score:** 94.9 / 94.8.
- **Quality:**
  - the generated overall 5.97, bottom three 5.27, against the three references' 7.33 (gap +1.36), and +1.12 against
    embers + tide;
  - performance 5.88 (gap +0.79);
  - memorable 2.17 against 2.67.

The open points are in TODO.md under "the new-age set, g11".

## Round g12 (2026-10-16: the climax is the head, the coda varied, a lower peak, the waltz head's rhythm, the climax's entry; renders `songs/_endless_piano/out/na_g12`, packets seed `blind-new-age-g12`)

The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 81000`, best-of-8.
- 3 references under new IDs: HEHJ = pro-newage-embers, WXPW = pro-newage-tide, CVPJ = pro-newage-longing.

**Seven judges** ran in D:/tmp/g12_judges, and no judge was shown a KEY. The mp3s by packet ID, the KEY and SCORES.txt
are in `songs/_endless_piano/out/blind_g12`. Scoring: `score_round.py KEY_newage.json D:/tmp/g12_judges/verdicts
--tells --refs pro-newage-embers,pro-newage-tide`.

### The measurement change

The raw gap (references minus generated) moved with the references' ratings: embers + tide ran from 7.10 (g4 / g5) to
6.27 (g8). In g11 the references rose 0.66 while the generated pieces held. Two changes address this.

**1. A relative score.** `score_round.py` now also prints the generated pieces relative to the references, per judge
and dimension, then averaged over the judges:
- `rel` = the generated mean / the references' mean;
- `z` = (generated - references) / that judge's standard deviation over all packets;
- `pct` = the share of (generated, reference) pairs in which the generated piece is rated at or above the reference
  (a tie counts half).

It prints the same block against `--refs` (embers + tide). `score_round.py --retro g3,...,g12 --keys PATTERN
--verdicts PATTERN` recomputes the table for earlier rounds from their KEYs and verdicts:

| round | judges | generated | references | gap | rel | z | pct | e+t gap | e+t rel | e+t z |
|---|---|---|---|---|---|---|---|---|---|---|
| g3 | 5 | 5.58 | 6.90 | +1.33 | 0.809 | -1.49 | 0.11 | - | - | - |
| g4 | 5 | 5.30 | 7.10 | +1.80 | 0.746 | -1.92 | 0.00 | +1.80 | 0.746 | -1.92 |
| g5 | 5 | 5.40 | 7.10 | +1.70 | 0.764 | -1.71 | 0.07 | +1.70 | 0.764 | -1.71 |
| g6 | 5 | 5.95 | 6.40 | +0.45 | 0.938 | -0.50 | 0.38 | +0.45 | 0.938 | -0.50 |
| g7 | 5 | 5.83 | 6.73 | +0.91 | 0.873 | -0.81 | 0.28 | +0.67 | 0.904 | -0.60 |
| g8 | 5 | 5.88 | 6.27 | +0.39 | 0.949 | -0.38 | 0.40 | +0.42 | 0.951 | -0.39 |
| g9 | 5 | 6.05 | 6.60 | +0.55 | 0.923 | -0.64 | 0.34 | +0.15 | 0.983 | -0.18 |
| g10 | 5 | 5.97 | 6.67 | +0.69 | 0.909 | -0.65 | 0.33 | +0.43 | 0.956 | -0.42 |
| g11 | 5 | 5.97 | 7.33 | +1.36 | 0.822 | -1.27 | 0.14 | +1.12 | 0.852 | -1.02 |
| **g12** | **7** | **5.88** | **6.19** | **+0.32** | **0.959** | **-0.30** | **0.41** | **+0.12** | **0.999** | **-0.13** |
| g12, the five g11 judges | 5 | 5.85 | 6.00 | +0.15 | 0.986 | -0.15 | 0.45 | -0.05 | 1.031 | +0.02 |

Per dimension in g12 (rel / z, all three references):
- melody 0.94 / -0.38;
- harmony 1.05 / +0.37;
- form 1.02 / +0.12;
- development 0.95 / -0.33;
- performance 1.03 / -0.01.

The g11 line, for comparison: melody 0.83 / -1.19, harmony 0.94 / -0.73, form 0.87 / -1.12, development 0.87 / -0.91,
performance 0.89 / -1.10.

The within-judge normalisation does **not** remove the yardstick's swings. `rel` and `z` follow the raw gap round by
round (g11 still reads as a step back: z -1.27). The swing is not one judge's scale moving; it is how the panel rates
the references against the generated pieces of that round, a contrast effect inside each judge. So the relative score
reads in units that compare across panels of different sizes, but it is no steadier than the raw gap. `pct` is the most
readable of the three ("the generated piece wins 41 % of the pairs"). A round still needs the generated level and the
bottom three next to it.

**2. Seven judges.** Two composer-lens judges joined the panel (`judge_newage.LENS`):
- `composerD`, the dramatist: a film / theatre composer judging the arc, the climax's preparation and payoff, the
  sections' contrast, the transitions, and whether the ending is earned.
- `composerE`, the melodist: a songwriter judging whether the theme can be hummed, the phrases breathe and answer, the
  hook returns changed, B has a hook of its own, and the high point is sung rather than loud.

The performer and the statistician stay. JUDGE_NEWAGE.md tells the judges that the panel compares ratings within each
judge. The two new judges rated the generated pieces 5.9 / 6.0 against 6.7 / 6.7 for the references, the harshest
contrast on the panel. Without them, the five g11 judges alone put the generated pieces level with embers + tide (last
row above).

### The set

The g12 set measures clean on the g12 tells:
- the climax states the head in its first 4 bars in 7 of 8 (VQXW 0.75: its 'reharm' anthem's contour);
- the peak is at most F6 (84-89), and 0.77 of the climax's sung notes sit in C5-B5;
- coda copies 0.02 (one piece);
- every head passes the rhythm check;
- no long tail after an early peak and no inner-voice-only bars;
- B1 passes its contrast check in 2 of 8.

| Piece | Packet | Form | Climax (anthem, arrival) | Moves |
|---|---|---|---|---|
| 001 | ZSTD | song, D major | in chords, after a key move | ostinato, goosebump |
| 002 | ZEFU | arch, G major | reharmonised, after a pause | ostinato, pause |
| 003 | NFLS | variations, D minor | sequenced, the head's fragment | motto |
| 004 | JQTJ | late, G minor | canon, after a held dominant | goosebump |
| 005 | VYDA | return, E major | in octaves, direct | motto |
| 006 | VQXW | song, A major | reharmonised, after a pause | ostinato, motto, pause |
| 007 | EXWH | variations, F# minor waltz | in chords, the head's fragment | goosebump |
| 008 | GZAT | late, Db major | sequenced, after a held dominant | pause (A4) |

### Quality, generated vs references (mean of 7 judges), against g11-g3

| Dimension | g12 generated | g12 refs (3) | g12 gap (3) | g12 gap (e + t) | g12 rel / z | g11 gap (3) | g11 gap (e + t) | g10 gap | g9 gap | g8 gap | g7 gap | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| melody | 5.88 | 6.29 | +0.41 | +0.12 | 0.94 / -0.38 | +1.26 | +0.92 | +0.73 | +0.57 | +0.60 | +0.98 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.43 | 6.19 | -0.24 | -0.43 | 1.05 / +0.37 | +0.52 | +0.25 | -0.03 | +0.17 | -0.03 | +0.09 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 6.09 | 6.00 | -0.09 | -0.30 | 1.02 / +0.12 | +1.00 | +0.90 | -0.01 | +0.38 | +0.09 | +0.68 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 5.73 | 6.19 | +0.46 | +0.41 | 0.95 / -0.33 | +0.97 | +0.88 | +0.39 | +0.30 | +0.39 | +0.85 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | 6.18 | 6.10 | -0.08 | -0.39 | 1.03 / -0.01 | +0.79 | +0.72 | +0.23 | +0.56 | +0.25 | +0.71 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | 5.88 | 6.19 | +0.32 | +0.12 | 0.96 / -0.30 | +1.36 | +1.12 | +0.69 | +0.55 | +0.39 | +0.91 | +0.45 | +1.70 | +1.80 | +1.33 |

Per packet, overall:

| packet | source | overall |
|---|---|---|
| EXWH | the waltz | 7.0 |
| GZAT | generated | 7.0 |
| CVPJ | longing | 6.6 |
| HEHJ | embers | 6.3 |
| NFLS | generated | 6.3 |
| VQXW | generated | 6.3 |
| WXPW | tide | 5.7 |
| JQTJ | generated | 5.4 |
| ZEFU | generated | 5.4 |
| ZSTD | generated | 5.0 |
| VYDA | generated | 4.6 |

The bottom three and the means, against earlier rounds:

| (from the per-packet overall lines) | g7 | g8 | g9 | g10 | g11 | g12 (7 judges) | g12 (the 5) |
|---|---|---|---|---|---|---|---|
| bottom three (generated) | 4.73 | 4.93 | 5.47 | 4.93 | 5.27 | **5.00** | 4.93 |
| generated mean | 5.58 | 5.88 | 6.05 | 5.97 | 5.97 | **5.88** | 5.85 |
| the best generated piece | - | - | - | 6.8 | 6.8 | **7.0** (two) | 7.4 |
| references' mean (3) | 6.73 | 6.27 | 6.60 | 6.67 | 7.33 | **6.19** | 6.00 |

- **The generated level is flat: 5.88 (g11 5.97), the bottom three 5.00 (g11 5.27).** These are 7 judges against 5;
  the five g11 judges alone give 5.85 and 4.93.
- **The top moved.** For the first time, two generated pieces outrank every reference: the waltz EXWH 7.0 (g11's
  waltz KTGG 4.4, the worst piece) and GZAT 7.0. Three more generated pieces sit at 5.4-6.3 with the references.
- **The references fell 7.33 -> 6.19:** longing 7.8 -> 6.6, embers 7.2 -> 6.3, tide 7.0 -> 5.7. The raw gap fell with
  them, +1.36 -> +0.32 (+1.12 -> +0.12 against embers + tide). This is the yardstick's largest swing so far, the other
  way round from g11's. On the relative score g12 is the best round (rel 0.959, z -0.30, pct 0.41; g8's 0.949 / -0.38
  / 0.40 came next), but by less than the raw gap suggests.
- Harmony, form and performance are at or above the references on every measure. Melody and development stay behind
  (+0.41 / +0.46; z -0.38 / -0.33). The judges' fixes below point at the same two dimensions.
- Counts: 8 of 11 from every judge (truth 8), as in every round since g7.

### The memorable moment

- **memorable:** the generated pieces 2.12 (g11 2.17), the references 2.33 (g11 2.67). The five g11 judges alone: 2.15
  vs 2.27.
  - Highest: EXWH 2.71, GZAT 2.57: the head reharmonised at each return and crowned at the climax (EXWH 43-56, GZAT
    45 an octave up).
  - Lowest: ZSTD 1.14, its climax heard as new melody; JQTJ 1.86.
- **Hit rate:** 22 of 56 named generated moments sit on a planned move's bars (39 %; g11 5 of 40):
  - every judge named NFLS's and VYDA's motto;
  - ZSTD's goosebump chord (the G-Eb flash at 39) was named by six judges;
  - 13 more moments fall inside an ostinato section (VQXW, ZEFU).
- **Shared flags: 42**, i.e. 6.0 a judge, as in g11 (30 / 5). The main cluster is EXWH ~ GZAT ~ VQXW ~ ZEFU (five
  judges): the head reharmonised or lifted at the climax. A second pair, NFLS ~ VYDA (five judges), is the motto that
  frames the piece.

### What the g11 fixes did

- **The climax is the head:** no judge said a climax "sings new material" of EXWH, GZAT, VQXW, ZEFU, JQTJ or VYDA.
  - GZAT's octave-up head at 45 was named the best payoff (four judges).
  - Two climaxes were still heard as new melody:
    - ZSTD (four judges): its 'chords' anthem after a key move sings the head's rhythm and contour, but a 4th up and
      over IV (F#5-B5-G5-A5 against C#5-F#5-D5-E5). `clx4` passes it, since it checks contour and rhythm only.
    - NFLS (two judges): its sequenced head opens on a 3-note cell (A5-E5-F5) stated twice.
  - **The new complaint is the reverse: "A1 replayed louder"** (EXWH composerD / E, VQXW five judges, ZEFU two). The
    head now opens the climax, often at A1's pitches, since the C5-C6 band leaves no octave to lift into. The
    judges want it transformed: an extended second phrase to a new peak, a reharmonisation, or the octave lift GZAT
    has. This is the `climax_copy` cost accepted in "After round g11".
- **The coda:** nobody named a coda copying A1. The statistician counted another template instead: seven codas of
  exactly 7 bars, a sus4 bar before the final chord in 5, and an RH rest bar before it in 3.
- **The peak:** no A6, and no judge called a generated climax shrill. The reference climaxes at G6-Ab6 (embers 41-47,
  tide 45) were the ones named too high (three judges). ZEFU's C6 peak and VYDA's D#6 were called too low or modest
  (three).
- **The waltz head:** EXWH's rising B4-C#5-E5-A5 head was praised by every judge, and the waltz rated 7.0 (g11's
  KTGG 4.4). composerA named its 16th-note fills (bars 5, 11, 75) clutter.
- **The climax's entry:** no soft entry or v93 -> v120 jump was named. Instead:
  - JQTJ's climax enters after a beat of rest at v57 (composerD);
  - EXWH's climax is played at 96 BPM against 92 (the performer);
  - GZAT's climax collapses within two bars (two judges).
- **B1:** still the most named section (below).
- **The tail and inner voices:** no generated tail after an early peak was named (only tide's, a reference). No
  inner-voice holes were named.

### The fixes the judges name, ranked by judges x pieces

1. **Transform the head at the climax, at its own degrees.**
   - Copied louder: VQXW 5, EXWH 2, ZEFU 2.
   - Not recognisable: ZSTD 4 (a 4th up over IV after a key move), NFLS 2.
   - The fix: the climax states the head at its own scale degrees (octave or home transposition), then changes its
     second phrase. Extend it to a new peak, sequence it up, or reharmonise it. GZAT 41-46 is the model.
   - Measure it: `clx4` with the degree match (pitch classes against the head after the key shift), plus "the climax
     past bar 2 differs from A1".
2. **Heads with no profile, and heads with no answer.**
   - No profile: VYDA (all 7; it circles C#5-D#5), ZSTD 4, JQTJ 3, ZEFU 3 (a plain scale climb).
   - No answer: the second phrase wanders (JQTJ 5-8, ZSTD 7-10, EXWH 5-9; composerE).
   - `head_prof` passes all 8, so its leap / held / band test is too lenient. Also needed: an answer phrase that
     mirrors the head's rhythm and cadences.
3. **B1 has no hook of its own** (ZSTD 4, NFLS 5, GZAT 3, JQTJ 4, ZEFU 2): held notes, or busy 8ths around two notes.
   `b1_ok` 0.25 is still open. The fix: a repeated cell with a held goal note, in another register from A.
4. **Literal head returns** (VQXW 4: four identical statements; JQTJ A4 = A1's bars 3-4; GZAT, ZSTD 11-12 / 47-48 =
   3-4: the statistician). `VARIED` checks bodies past the head; the head bars themselves still return as written. The
   fix: the second bar of every return diverges.
5. **An RH hole at the climax** (VYDA bar 38, all seven) and ZEFU's peak bar of four repeated C5s (three). `peak_holes`
   did not flag VYDA; check it.
6. **Wrong-sounding chromatics:** Gb5 over Ebmaj7 (JQTJ 3 / 53, three judges), Gb5 over F (VQXW 23, two), and an F4
   inner voice under Em7 / Gadd9 (ZEFU 5 / 10). A chromatic neighbour must be spelled and resolve as one.
7. **Dynamics:** ZSTD's RH at 3.8 dB (three) with low LH octaves on every bar; VQXW loud from A2 on (the performer).
8. **The coda template** (the statistician: 7-bar codas, the sus4 bar before the end).

### What convinced

- EXWH's chromatic lament bass (F#-D-E#-E-D#-D, bars 1-9), the Neapolitan G (11, 73) and the head reharmonised at each
  return (F#m7, Dmaj7, Amaj7).
- GZAT's two-voice writing, the head over Bbm7 in A3 and an octave up at the climax (45).
- VQXW's hook ("the catchiest of the set") and its bVI F major in B1 (23).
- NFLS's sigh motif framing the piece, with its Neapolitan Eb at 10 / 37.
- ZEFU's recurring Cm6, VYDA's Am6 intro colour, and ZSTD's goosebump G-Eb at 39.

### Baseline for future rounds

Measured on 48 seeds 64000-64047 / 48 set slots from 72000 (docs/PIANIST_RULES.md "After round g11"):
- **The climax:** the head in the first 4 bars 0.98 / 0.94; peaks over F6 0 / 0; the highest note 86.9 / 86.6; sung
  notes in C5-B5 0.73 / 0.75.
- **Endings:** coda copies 0.065 / 0.072; long tails after an early peak 0.02 / 0.02.
- **Heads:** with the rhythm 1.0 / 1.0. B1 contrast (`b1_ok`) 0.33 / 0.29.
- **Rejects in set slots:** arc 40.6 %, breath 9.0 % (kept 50.4 %).
- **Score:** 94.7 / 94.5.
- **Quality, 7 judges:**
  - the generated overall 5.88, bottom three 5.00, best 7.0, against the three references' 6.19 (gap +0.32);
  - rel 0.959, z -0.30, pct 0.41;
  - against embers + tide: +0.12, rel 0.999;
  - memorable 2.12 against 2.33.

The open points are in TODO.md under "the new-age set, g12".

## Round g13 (2026-10-16: the climax's head at its own degrees and a new second phrase, heads that do not circle, the answer in the head's rhythm, B's own rhythm, the head varied on return; renders `songs/_endless_piano/out/na_g13`, packets seed `blind-new-age-g13`)

The set:
- 8 generated pieces: `endless piano --style new-age --count 8 --seed 83000`, best-of-8.
- 3 references under new IDs: FQWT = pro-newage-embers, QUEM = pro-newage-tide, CNWG = pro-newage-longing (rebuilt
  in this worktree).

The same seven judges ran in D:/tmp/g13_judges, and no judge was shown a KEY. The mp3s by packet ID, the KEY and
SCORES.txt are in `songs/_endless_piano/out/blind_g13`. Scoring: `score_round.py KEY_newage.json
D:/tmp/g13_judges/verdicts --tells --refs pro-newage-embers,pro-newage-tide`.

Before the round, g12's fixes went in (docs/PIANIST_RULES.md "After round g12"): every sung climax opens with the
head at its own degrees, then the head a third higher (`ANTHEM_HEAD`, GZAT's plan); its key move is a step up or the
parallel major only (`SUNG_KEYS`); A1's first 4 bars may not circle a 2-semitone window (`HEAD_PROFILE['circle']`);
the answer phrase keeps the head's rhythm; B's counter-motif cell has a rhythm of its own; a return's head moves its
second bar (`HEAD_RETURN`); the motto payoff answers the peak when it cannot precede it and leaves no empty bar; the
coda's length is a draw.

The g13 set measures clean on the g13 tells: the climax's head at its own degrees in 8 of 8, its second unit not
A1's in 7 of 8 (MYUS: its 'reharm' climax), every head under the circle share (0.36-0.50), every answer in the head's
rhythm, every B1 in a rhythm of its own (but only RFZC's passes the register / pace contrast), no return's head
copying A1's second bar, no empty climax bar on the tell (its last bar out), codas of 6 or 8 bars (7 / 9 printed).

| Piece | Packet | Form | Climax (anthem, arrival) | Moves |
|---|---|---|---|---|
| 001 | RFZC | arch, C# minor | canon, after a pause | motto, pause |
| 002 | GALR | variations, E major | sequenced, the head's fragment | goosebump |
| 003 | CNCJ | song, Bb major | in chords, after a key move (C) | motto, ostinato, pause |
| 004 | TCMN | return, G major | in octaves, after a held dominant | motto, pause |
| 005 | MYUS | arch, C major | reharmonised, direct | goosebump, ostinato |
| 006 | QTNU | late, Bb major | sequenced, the head's fragment | goosebump |
| 007 | PPHK | chorus, E major waltz | in chords, after a key move | ostinato |
| 008 | CPED | variations, A minor | in octaves, after a held dominant | - |

### Quality, generated vs references (mean of 7 judges), against g12-g3

| Dimension | g13 generated | g13 refs (3) | g13 gap (3) | g13 gap (e + t) | g13 rel / z | g12 gap (3) | g12 gap (e + t) | g11 gap | g10 gap | g9 gap | g8 gap | g7 gap | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| melody | 5.80 | 6.81 | +1.01 | +0.48 | 0.86 / -0.92 | +0.41 | +0.12 | +1.26 | +0.73 | +0.57 | +0.60 | +0.98 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.50 | 6.67 | +0.17 | -0.07 | 0.98 / -0.20 | -0.24 | -0.43 | +0.52 | -0.03 | +0.17 | -0.03 | +0.09 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 5.98 | 6.95 | +0.97 | +0.73 | 0.87 / -0.91 | -0.09 | -0.30 | +1.00 | -0.01 | +0.38 | +0.09 | +0.68 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 5.71 | 6.52 | +0.81 | +0.57 | 0.88 / -0.69 | +0.46 | +0.41 | +0.97 | +0.39 | +0.30 | +0.39 | +0.85 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | 5.61 | 6.57 | +0.96 | +0.82 | 0.86 / -0.94 | -0.08 | -0.39 | +0.79 | +0.23 | +0.56 | +0.25 | +0.71 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | 5.57 | 6.90 | +1.33 | +0.93 | 0.82 / -1.06 | +0.32 | +0.12 | +1.36 | +0.69 | +0.55 | +0.39 | +0.91 | +0.45 | +1.70 | +1.80 | +1.33 |

The relative score over the rounds (`score_round.py --retro g3,...,g13`):

| round | judges | generated | references | gap | rel | z | pct | e+t gap | e+t rel | e+t z |
|---|---|---|---|---|---|---|---|---|---|---|
| g3 | 5 | 5.58 | 6.90 | +1.33 | 0.809 | -1.49 | 0.11 | - | - | - |
| g4 | 5 | 5.30 | 7.10 | +1.80 | 0.746 | -1.92 | 0.00 | +1.80 | 0.746 | -1.92 |
| g5 | 5 | 5.40 | 7.10 | +1.70 | 0.764 | -1.71 | 0.07 | +1.70 | 0.764 | -1.71 |
| g6 | 5 | 5.95 | 6.40 | +0.45 | 0.938 | -0.50 | 0.38 | +0.45 | 0.938 | -0.50 |
| g7 | 5 | 5.83 | 6.73 | +0.91 | 0.873 | -0.81 | 0.28 | +0.67 | 0.904 | -0.60 |
| g8 | 5 | 5.88 | 6.27 | +0.39 | 0.949 | -0.38 | 0.40 | +0.42 | 0.951 | -0.39 |
| g9 | 5 | 6.05 | 6.60 | +0.55 | 0.923 | -0.64 | 0.34 | +0.15 | 0.983 | -0.18 |
| g10 | 5 | 5.97 | 6.67 | +0.69 | 0.909 | -0.65 | 0.33 | +0.43 | 0.956 | -0.42 |
| g11 | 5 | 5.97 | 7.33 | +1.36 | 0.822 | -1.27 | 0.14 | +1.12 | 0.852 | -1.02 |
| g12 | 7 | 5.88 | 6.19 | +0.32 | 0.959 | -0.30 | 0.41 | +0.12 | 0.999 | -0.13 |
| **g13** | **7** | **5.57** | **6.90** | **+1.33** | **0.815** | **-1.06** | **0.21** | **+0.93** | **0.874** | **-0.71** |
| g13, the five g11 judges | 5 | 5.42 | 6.87 | +1.44 | 0.798 | -1.13 | 0.18 | +1.08 | 0.847 | -0.83 |

Per packet, overall:

| packet | source | overall |
|---|---|---|
| CNWG | longing | 7.7 |
| QTNU | generated | 6.7 |
| FQWT | embers | 6.6 |
| QUEM | tide | 6.4 |
| CPED | generated | 6.3 |
| TCMN | generated | 6.3 |
| RFZC | generated | 6.0 |
| CNCJ | generated | 5.9 |
| MYUS | generated | 4.7 |
| GALR | generated | 4.6 |
| PPHK | generated (the waltz) | 4.1 |

The bottom three and the means, against earlier rounds:

| (from the per-packet overall lines) | g7 | g8 | g9 | g10 | g11 | g12 (7 judges) | g13 (7 judges) |
|---|---|---|---|---|---|---|---|
| bottom three (generated) | 4.73 | 4.93 | 5.47 | 4.93 | 5.27 | 5.00 | **4.48** |
| generated mean | 5.58 | 5.88 | 6.05 | 5.97 | 5.97 | 5.88 | **5.57** |
| the best generated piece | - | - | - | 6.8 | 6.8 | 7.0 (two) | **6.7** |
| references' mean (3) | 6.73 | 6.27 | 6.60 | 6.67 | 7.33 | 6.19 | **6.90** |

- **A step back: the generated mean 5.88 -> 5.57, the bottom three 5.00 -> 4.48**, the lowest floor since g7. The
  top held: QTNU 6.7 outranks embers and tide, CPED / TCMN 6.3 sit level with tide.
- **The references rose 6.19 -> 6.90** (longing 6.6 -> 7.7, embers 6.3 -> 6.6, tide 5.7 -> 6.4), so the raw gap
  (+1.33) overstates the fall, as g11's did. The relative score still reads a worse round than g12 (rel 0.815, z
  -1.06, pct 0.21), close to g11 (0.822 / -1.27 / 0.14). The five g11 judges alone give the same picture.
- Harmony stays level with the references (+0.17; -0.07 against embers + tide). Form and performance fell back from
  level (g12 -0.09 / -0.08) to +0.97 / +0.96: the judges' top complaints this round are holes, broken phrase ends
  and proportions, not the tune alone.
- Counts: 8 of 11 from every judge (truth 8), as in every round since g7. The statistician named the right eight.

### The memorable moment

- **memorable:** the generated pieces 2.05 (g12 2.12), the references 2.38 (g12 2.33).
  - Highest: QTNU 2.86 (its Eb5-A4-Bb4-C5 appoggiatura head, "the best-planted motif", 3 from six judges), TCMN 2.57
    (its rising G4-A4-B4-D5 motto at bars 1 / 27 / 37 / 43 / 57, all seven).
  - Lowest: PPHK 1.00 (a waltz head circling a narrow cell, all seven), GALR 1.43.
- **Hit rate:** 33 of 56 named generated moments sit on a planned move's bars (59 %; g12 39 %): motto 16, goosebump
  12, pause 11.
- **Shared flags: 49**, i.e. 7.0 a judge (g12 6.0). Two clusters:
  - CPED ~ GALR ~ MYUS ~ QTNU ~ RFZC (all seven judges, in subsets): the climax opening on the head's first bar;
  - CNCJ ~ PPHK ~ TCMN (six judges): the climax a whole step up.

### What the g12 fixes did

- **The climax's head at its own degrees:** no climax was called "a 4th up over IV"; the statistician counts all 8
  opening on the head's first bar. But the two halves of the fix read differently:
  - **The head at A1's pitches is again heard as "A1 replayed louder"** where the third-up second phrase comes late
    or is covered: MYUS (five judges), GALR (four), CPED (three), QTNU (three: "note for note until bar 51"), RFZC
    (two). The step a third up itself was praised where it was heard (MYUS: three judges; CPED 33-36: four).
  - **The key-up climaxes** (CNCJ, TCMN, PPHK: the head a whole step up) were not heard as the head by about half the
    judges (CNCJ 3, TCMN 3, PPHK 2) - the statistician measured the head there.
  - And the set now shares one plan: the head-first climax is the main shared flag (all seven judges), as "A1 an
    octave up" was in g10.
- **Heads that do not circle:** VYDA's case is gone from the 4/4 heads, but heads without a profile are still the third
  complaint (about 23 judge-pieces): **PPHK's waltz head, all seven** (the circle check skips 3/4 heads), GALR 4,
  CNCJ 3, TCMN 3.
- **The answer in the head's rhythm:** no "second phrase wanders" was named.
- **B1 with its own rhythm:** no judge said B1 sounds like A's rhythm; B1 without a hook is still named (MYUS 3, PPHK 3,
  GALR 2, CPED 2), now as a missing hook, register and harmonic world. The praised B1s (QTNU's Gb-Ab, RFZC's
  Neapolitan D major, CNCJ's Ebm6) are harmonic.
- **The head varied on return:** the moved second bar went almost unnoticed. Literal returns are still named (RFZC A2
  four judges, GALR four, QTNU three) - the bodies, not the head's second bar. One judge called CPED's A2 "a
  near-miss" of the head.
- **The motto payoff:** kept in all three motto pieces, but it is now their weak spot: TCMN's bar 38 (its held last
  note, four judges: "empty"), RFZC 29-30 (the melody buried, three), CNCJ 41 ("filler", four).
- **Chromatic notes:** JQTJ's case is gone; four pieces still have a stray inner note (MYUS's Bb4 under Cadd9 at 5 /
  44, TCMN's F4 at 21 / 53, CNCJ's Fb5 in bar 2).
- **The coda template:** the statistician now counts codas of exactly 7 or 9 bars (four each).

### The fixes the judges name, ranked by judges x pieces

1. **Holes and broken-off phrase ends (about 32).** The phrase end that flicks into 32nds and a 0.08-beat stab, then
   an empty bar: GALR 13-14 / 27-28 (all seven), MYUS 7-8 / 21-22 (all seven), PPHK 77-78 (three) - the single most
   named machine tell. Inside the climax: TCMN 38 (four), RFZC 29-30 (three), both on the motto payoff. The climax's
   exit: CNCJ 45-46 (six). A hole check per phrase end (an RH bar after a fast figure with only a stab) is the fix.
2. **Proportions and length (about 29).** PPHK's 93 bars and static 16-bar climax (all seven / six); codas too long
   (MYUS, CPED 4 each, RFZC 3); QTNU's inter + 4-bar A3 (five).
3. **Heads without a profile (about 23).** PPHK (all seven: the waltz head is not checked), GALR 4, CNCJ 3, TCMN 3.
   Extend the circle / profile check to 3/4 heads over 8 bars.
4. **The climax opens as A1 replayed (17).** MYUS 5, GALR 4, CPED 3, QTNU 3, RFZC 2. The head at its own pitches is
   right for recognition, but its first unit needs a change heard at once (the chords - reharmonised under the
   head - or the octave / the texture) and the third-up unit must come straight after it, not after a payoff.
5. **Literal return bodies (about 15).** RFZC A2, GALR A3, QTNU.
6. **Wrong-sounding inner notes (about 13):** MYUS 4, TCMN 3, CNCJ 3 - inner voices ("under") off the chord.
7. **B1 without a hook (about 11)**, the key-up climax not heard as the head (8), the motto as a mannerism (CNCJ 4),
   intros unrelated to the piece (5), flat dynamics (the performer: QTNU, CPED, PPHK).

### What convinced

- QTNU's appoggiatura cell, its Gb-Ab B1 (bVI-bVII-I, all seven) and the Db surprise at its climax (bar 49, five).
- TCMN's rising pickup motto, its lift to A major and its Cm6 close (all seven).
- RFZC's held B#5 pause at bar 26 (six) and its Neapolitan D-major B1 (seven).
- CNCJ's G7 lift into C at 38-39 (all seven) and its Ebm6 colour; CPED's A3 reharmonised over Cmaj7 (five); MYUS's
  Fm6-Abmaj7 build (six).

### The statistician's counts

- (under) inner voices: 8+ per generated piece, 0 in the references.
- RH notes at C6+ in the highest section: 2-10 % generated, against 21-59 % in the references.
- RH notes per attack in A1: 1.03-1.53 generated, 1.00-1.06 references (the generated A1s are thicker).
- Every climax opens on the head's first bar; six over an octave bass with triads on 2 and 4.
- Every last A is 8+ bars, every coda 7 or 9 bars; section lengths irregular (7, 10, 13, 6, 2 + 4).

### Baseline for future rounds

Measured on 48 seeds 64000-64047 / 48 set slots from 72000 (docs/PIANIST_RULES.md "After round g12"):
- **The climax:** its head at its own degrees 0.98 / 0.96; its second unit A1's 0.02 / 0; empty bars 0.04 / 0.
- **Heads:** circle-free 0.98 / 1.0; the answer in the head's rhythm 0.90 / 0.85; profile 0.90 / 0.90.
- **B:** its own rhythm 0.98 / 1.0; with a hook (rhythm + restated + contrast) 0.23 / 0.38.
- **Returns:** the head's second bar copying A1's 0 / 0; copied bars a piece 0.90 / 0.81.
- **Rejects in set slots:** arc 39.5 %, breath 10.5 % (kept 50.0 %).
- **Score:** 94.9 / 94.5.
- **Quality, 7 judges:**
  - the generated overall 5.57, bottom three 4.48, best 6.7, against the three references' 6.90 (gap +1.33);
  - rel 0.815, z -1.06, pct 0.21;
  - against embers + tide: +0.93, rel 0.874;
  - memorable 2.05 against 2.38.

The open points are in TODO.md under "the new-age set, g13".

## Round g14 (2026-10-16, a PAIRED round: the climax's first unit changed at once, holes, proportions, the waltz head, inner voices; renders `songs/_endless_piano/out/na_g14/{g14code,g12code}`, packets seed `blind-new-age-g14`)

g13 fell back (5.57, rel 0.815) and was not merged. Round g14 starts from g13's branch, repairs its tells
(docs/PIANIST_RULES.md "After round g13"), and judges the result **against the g12 code (master) on the same set**.

The set:
- 8 seeds by both codes: `endless piano --style new-age --count 8 --seed 85000` (the same set plan), best-of-8. Once
  with this branch's code, once with the g12 code in a checkout of master.
- 3 references: MCRW = pro-newage-embers, FHJE = pro-newage-tide, SXEM = pro-newage-longing.
- 19 packets, dealt by `make_packets_paired.py deal g14 ... --panels 2`: slot k goes to panel k % 2 + 1, so both
  halves of a pair go to the same judges. Every panel also gets the 3 references, i.e. 11 packets a judge as in
  g7-g13. `judge_newage.py g14 ROOT --panel P` sets up each panel.
- Judges: two panels of the seven judges in D:/tmp/g14_judges/p{1,2} (14 judge files), no KEY shown.
- The g14-code mp3s by packet ID, the KEY and SCORES.txt are in `songs/_endless_piano/out/blind_g14`.
- Scoring:
  - the halves: `score_round.py <subset KEY> <merged verdicts> --tells --refs pro-newage-embers,pro-newage-tide`;
  - the pair: `score_round.py KEY_newage.json <merged verdicts> --paired g14,g12` (new: per dimension the mean of the
    (judge, slot) differences, then per slot).

| Slot | g14 code | g12 code | Panel | The pair (from the packets) |
|---|---|---|---|---|
| 001 | ZNSH | TQTV | 2 | Bb major, the climax a step up (both) |
| 002 | RQHP | TKNU | 1 | F major |
| 003 | YPCW | YDBM | 2 | A minor, motto |
| 004 | JUJW | FJSQ | 1 | Eb major, ostinato |
| 005 | MFMM | MNLT | 2 | F major, motto, B1 in Db |
| 006 | WYQD | GACE | 1 | F# minor |
| 007 | XTHR | SSTQ | 2 | Bb major, the waltzes (80 / 84 bars) |
| 008 | JQHZ | FSLJ | 1 | C# minor |

### The paired result: g14 code - g12 code (same judges, same seed)

| dimension | mean diff | sd | pairs won / tied / lost (of 56) |
|---|---|---|---|
| melody | **+0.38** | 1.08 | 26 / 15 / 15 |
| harmony | -0.02 | 0.69 | 11 / 32 / 13 |
| form | +0.29 | 1.08 | 24 / 16 / 16 |
| development | **+0.54** | 1.25 | 24 / 19 / 13 |
| performance | +0.09 | 0.91 | 13 / 31 / 12 |
| overall | **+0.29** | 1.16 | 25 / 14 / 17 |
| memorable (0-3) | **+0.33** (1.95 vs 1.62) | | |

Per slot, overall (the 7 judges of its panel):

| slot | g14 | g12 | diff | judges |
|---|---|---|---|---|
| 001 | ZNSH 5.4 | TQTV 5.6 | -0.14 | +0 -1 +0 +1 +0 +0 -1 |
| 002 | RQHP 5.3 | TKNU 5.1 | +0.14 | +0 +1 -1 +0 +0 +1 +0 |
| 003 | YPCW 6.1 | YDBM 5.6 | +0.57 | +1 +0 +0 +0 +0 +2 +1 |
| 004 | JUJW 6.3 | FJSQ 5.0 | **+1.29** | +1 +2 +1 +1 +1 +2 +1 |
| 005 | MFMM 5.7 | MNLT 4.7 | **+1.00** | +2 +1 +2 +1 -1 +2 +0 |
| 006 | WYQD 4.7 | GACE 6.0 | **-1.29** | -1 -2 -1 -1 -2 -1 -1 |
| 007 | XTHR 5.6 | SSTQ 4.0 | **+1.57** | +1 +1 +1 +2 +3 +1 +2 |
| 008 | JQHZ 4.3 | FSLJ 5.1 | -0.86 | -1 -1 -1 -1 -1 +0 -1 |

- **The g14 code wins, modestly:** +0.29 overall, five slots up and three down. Over the 8 slots the standard error
  is about 0.36 (slot sd 1.02), so the win is not significant on its own. Melody (+0.38), development (+0.54) and memorable (+0.33)
  carry it; harmony and performance are level.
- **The clear wins are the repaired tells:**
  - the waltz XTHR over SSTQ (+1.57, every judge): 80 bars, a planted head paid off an octave up, against SSTQ's
    18-bar static climax;
  - JUJW over FJSQ (+1.29, every judge);
  - MFMM over MNLT (+1.00).
- **The losses:**
  - WYQD under GACE (-1.29, every judge): A3 as loud and high as the climax, B1 circling A5-B5;
  - JQHZ under FSLJ (-0.86): the climax never above B5, then sinking into dominant figuration.
  - Both losses are the climax and the bars after it, not the repaired holes.
- Panel 2 (the motto and waltz slots) gave g14 +0.75 (5.71 vs 4.96); panel 1 gave g12 +0.18 (5.32 vs 5.14).

### Quality, against the references (14 judges)

| Dimension | g14 code | g12 code (same round) | refs (3) | g14 gap (3) | g14 gap (e + t) | g14 rel / z | g12-code gap (3) | g13 gap | g12 gap | g11 gap | g10 gap | g9 gap | g8 gap | g7 gap | g6 gap | g5 gap | g4 gap | g3 gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| melody | 5.59 | 5.21 | 7.26 | +1.67 | +1.38 | 0.77 / -1.62 | +2.05 | +1.01 | +0.41 | +1.26 | +0.73 | +0.57 | +0.60 | +0.98 | +0.80 | +1.47 | +1.55 | +1.40 |
| harmony | 6.12 | 6.14 | 7.29 | +1.16 | +1.16 | 0.84 / -1.40 | +1.14 | +0.17 | -0.24 | +0.52 | -0.03 | +0.17 | -0.03 | +0.09 | -0.55 | +1.03 | +0.73 | +0.70 |
| form | 5.80 | 5.52 | 7.29 | +1.48 | +1.55 | 0.80 / -1.33 | +1.77 | +0.97 | -0.09 | +1.00 | -0.01 | +0.38 | +0.09 | +0.68 | +0.38 | +1.55 | +2.00 | +0.77 |
| development | 5.45 | 4.91 | 7.02 | +1.58 | +1.70 | 0.78 / -1.40 | +2.11 | +0.81 | +0.46 | +0.97 | +0.39 | +0.30 | +0.39 | +0.85 | +0.70 | +1.58 | +1.75 | +1.10 |
| performance | 5.73 | 5.64 | 7.05 | +1.32 | +1.38 | 0.82 / -1.60 | +1.40 | +0.96 | -0.08 | +0.79 | +0.23 | +0.56 | +0.25 | +0.71 | -0.08 | +1.62 | +1.35 | +0.75 |
| overall | 5.43 | 5.14 | 7.50 | +2.07 | +2.04 | 0.73 / -1.71 | +2.36 | +1.33 | +0.32 | +1.36 | +0.69 | +0.55 | +0.39 | +0.91 | +0.45 | +1.70 | +1.80 | +1.33 |

The relative score, extending g13's table:

| round | judges | generated | references | gap | rel | z | pct | e+t gap | e+t rel | e+t z |
|---|---|---|---|---|---|---|---|---|---|---|
| g11 | 5 | 5.97 | 7.33 | +1.36 | 0.822 | -1.27 | 0.14 | +1.12 | 0.852 | -1.02 |
| g12 | 7 | 5.88 | 6.19 | +0.32 | 0.959 | -0.30 | 0.41 | +0.12 | 0.999 | -0.13 |
| g13 | 7 | 5.57 | 6.90 | +1.33 | 0.815 | -1.06 | 0.21 | +0.93 | 0.874 | -0.71 |
| **g14, g14 code** | **14** | **5.43** | **7.50** | **+2.07** | **0.726** | **-1.71** | **0.03** | **+2.04** | **0.730** | **-1.70** |
| g14, g12 code | 14 | 5.14 | 7.50 | +2.36 | 0.686 | -1.78 | 0.01 | +2.32 | 0.690 | -1.75 |

- **This round cannot be read against g3-g13.** The g12 code, which scored 5.88 / rel 0.959 in round g12, scores
  5.14 / rel 0.686 here. The references rose to 7.50, the highest yet. Two reasons:
  - Each judge saw two pieces of the same set plan side by side (same key, tempo, form, often the same intro figure).
    The template showed itself: "so close to FSLJ in key, tempo and shape", "shares its intro and build figures with
    TQTV". Shared flags rose to 32 (g14 half) and 24 (g12 half).
  - Each judge's sd was narrow, so z fell for both halves alike.
- The yardstick for this round is the paired difference; the raw gap only ranks pieces within the round.
- Bottom three (generated): g14 code 4.77 (JQHZ 4.3, WYQD 4.7, RQHP 5.3); g12 code 4.57 (SSTQ 4.0, MNLT 4.7,
  FJSQ 5.0).
- Best piece: g14 code JUJW 6.3; g12 code GACE 6.0.
- Counts: 8 of 11 from every judge (truth 8).

Per packet, overall (14 judges, each packet by its panel's 7):

| packet | source | overall | | packet | source | overall |
|---|---|---|---|---|---|---|
| SXEM | longing | 7.6 | | GACE | g12 006 | 6.0 |
| FHJE | tide | 7.5 | | TQTV | g12 001 | 5.6 |
| MCRW | embers | 7.4 | | YDBM | g12 003 | 5.6 |
| JUJW | g14 004 | 6.3 | | FSLJ | g12 008 | 5.1 |
| YPCW | g14 003 | 6.1 | | TKNU | g12 002 | 5.1 |
| MFMM | g14 005 | 5.7 | | FJSQ | g12 004 | 5.0 |
| XTHR | g14 007 (waltz) | 5.6 | | MNLT | g12 005 | 4.7 |
| ZNSH | g14 001 | 5.4 | | SSTQ | g12 007 (waltz) | 4.0 |
| RQHP | g14 002 | 5.3 | | | | |
| WYQD | g14 006 | 4.7 | | | | |
| JQHZ | g14 008 | 4.3 | | | | |

### The memorable moment

- memorable: g14 code 1.95, g12 code 1.62, references 2.62.
  - Highest: YPCW 2.71 (the head an octave up at the climax, bar 40), XTHR 2.43 (the waltz head planted, paid off
    at 57), JUJW 2.29.
  - Lowest: JQHZ / WYQD 1.14.
- Hit rate on planned moves: g14 18 of 56 (32 %), g12 26 of 56 (46 %). XTHR's named moment (its head's payoff) is
  not a planned move.

### What the g13 repairs did (judge notes, g14 half against g12 half)

- **Holes:** no judge named a 32nd flick, a 0.08-beat stab or an empty bar after a phrase end (g13: about 32
  judge-pieces).
  - Still named: JQHZ B1's D#5 tied over bars 18-21 (three), and YPCW B1 ending on a bar of left hand alone (one).
  - TCMN's case (the motto payoff's held note) did not recur; MFMM / YPCW / ZNSH all keep their payoffs.
  - New: a 16th-note inner "tick" under a held note before the climax (MFMM 46, ZNSH 36: three judges).
- **Proportions:**
  - the waltz is no longer the bottom piece (XTHR 5.6, SSTQ 4.0); the statistician calls XTHR's coda thin (9
    bars);
  - "too long" / "static" fell for the waltz, but rose elsewhere: the climaxes rocking between two chords (RQHP
    33-36, YPCW 36-39).
- **The climax's first unit:** the g14 half was named "A1 replayed" about 12 times, the g12 half about 16.
  - The reharmonised open was heard (JQHZ "reharmonizing the head on Emaj7 (38) is a good idea"; RQHP "opening on
    Am7").
  - But the head still sits at A1's register, and the statistician counts it as an aligned copy (YPCW 36 = 5, MFMM
    47-48 = 5-6, XTHR 45 / 47 / 48).
- **Inner voices:** no "wrong inner note" was named in either half's 4/4 heads. Still named: ZNSH 42's Ab/Cb6
  chromatic chord in the C-major climax (three judges), the ornament over the key move.
- **The waltz head's circle:** XTHR's head was "recognisable" and "planted" (five judges); the complaint moved to
  the bars between its statements (static, quiet A1 at v39-60, four judges).

### The fixes the judges name for the g14 code, ranked by judges x pieces

1. **The climax peaks low or collapses (about 16).** JQHZ never above B5 (all seven); MFMM D6 only (four); ZNSH under
   C6 (three); YPCW falls within a bar after its octave lift (two); JUJW stalls on a held D5 before its peak (one).
   The g12 "lower peak" (`peak` set draws) and the ceiling went too far for the minor-key and middle-register heads.
2. **After the climax (about 16):** RQHP's A2 replays A1 at mf for 10 bars (five); WYQD's A3 as loud and high as
   the climax (four); JUJW's A3 drops to -5.7 LU at once (four). The return after the climax needs its own dynamic
   (between the climax and the coda) and a shortened or varied body.
3. **The climax's first unit still at A1's register (about 12):** YPCW, XTHR, MFMM, RQHP, JQHZ - start it at the
   octave (or the third), keep the reharmonisation.
4. **The key-up climax's way back (four, ZNSH):** a single F7sus4 back to Bb. Two bars of preparation.
5. **Heads with no downbeat or no hook:** MFMM (three), WYQD, ZNSH, RQHP; B1 still aimless in WYQD / YPCW / RQHP.
6. **Fussy inner 16ths under a held note (three)**, ZNSH 42's chromatic chord (three).

### Baseline for future rounds

- Measured on 48 seeds 64000-64047 / 48 set slots, as in docs/PIANIST_RULES.md "After round g13":
  - the climax opening as A1 at pitch: 0.08 / 0.04;
  - flicks into a phrase landing: 0 / 0;
  - empty bars after a phrase end: 0.02 / 0.02;
  - waltzes: 79-80 bars;
  - inner voices sung at melody level: 0.08 / 0.10;
  - score: 95.2 / 95.8.
- Quality, a paired round (14 judges):
  - g14 code - g12 code: +0.29 overall (melody +0.38, development +0.54), memorable +0.33;
  - the g14 code 5.43 against the references' 7.50 (rel 0.726); the g12 code 5.14 (0.686) in the same round.

The open points are in TODO.md under "the new-age set, g14".

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

## Round q1: orchestra-symphonic vs orchestra-film, a QUALITY round (2026-10-16)

The trigger was HUMAN_FEEDBACK 2026-10-16: the orchestra-film seeds 93006 / 93018 were "very meditative, hardly
anything happens". The new genre `orchestra-symphonic` (endless/symphony.py) has its own orchestral composer.

- Renders: `songs/_endless_orchestra/out/q1`. Packets seed `blind-orch-q1`, `KEY_orch_q1.json` (with each generated
  packet's `code` = its genre).
- The 12 packets: 4 symphonic (stormy allegro, heroic vivace 6/8, river journey 6/8, dance scherzo 3/4; best-of-4), 4
  orchestra-film (the seeds near 93006 / 93018 after the gate's rerolls: 93008, 93019, 248 and the 261 slot), and
  the 4 hidden pro-orch-* references.
- The brief is JUDGE_ORCH_Q.md: rate 1-10 on melody, harmony, form, development, orchestration, life and overall,
  plus memorable 0-3. Seven judges (`judge_orch.py --quality`): composers A/B/C, a dramatist, a melodist, a
  statistician and an orchestrator.

| | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| orchestra-symphonic | 6.18 | 6.50 | 6.75 | 6.86 | 6.14 | 7.29 | **6.57** | 2.39 |
| orchestra-film | 5.33 | 6.04 | 5.33 | 4.78 | 4.96 | 4.26 | 5.19 | 1.89 |
| references (lyrical) | 6.07 | 6.14 | 6.32 | 5.46 | 5.79 | 5.07 | 5.96 | 2.50 |

- Per packet (overall), the symphonic pieces:
  - 'Overture: Golden Mountains', G minor allegro: 7.6, the top of the set.
  - 'The Iron Horizons', Eb vivace: 7.3.
  - 'Silver Banners of the North', river: 6.9.
  - 'Toward the Dawn', the scherzo: 4.6, the bottom of the set.
- References: epic 6.6, longing 6.3, hopeful 6.3, night 4.7. orchestra-film: 4.6-5.6.
- The symphonic genre beats orchestra-film on every dimension (overall +1.39, life +3.03, development +2.08). It also
  beats the references on life and development, but the references are lyrical pieces, so that comparison is not
  like with like.
- The judges' generated count is 8-10 of 12 (truth 8). They take the fast pieces as possibly composed; named moments
  are the motto, the bVI shock, the fugato and the pedal build.
- Tells on the symphonic pieces:
  - The development stands still. The dialogue / fugato blocks are thin and pp, and the scherzo's bars 93-124 hold
    notes for 32 bars.
  - The scherzo is too long: 188 bars, because one compound bar = two 3/4 bars, so the long layouts double.
  - Themes are chord-tone outlines in long values (the scherzo; the vivace's second-key flute episode).
  - Trombones go above Bb4 and bassoons above C5 against the brass. Horns get running 16ths in the river.
  - The shared plan: the statistician sees "GYQV's plan stretched" in YQLV. There are 23 `shared` flags among the
    generated packets, mostly between the symphonic pieces (one plan family).
  - The 8-bar opening figuration ostinato is the same in two pieces.

## After q1 (not judged)

- The dialogue texture keeps the drive (the strings' ostinato and a staccato pump instead of held harmony).
- The fugato builds: the horns' dominant pedal and the timpani roll enter in its second half.
- The development starts at mp / mf instead of p / mp.
- The scherzo plays the compact layout: 'Toward the Dawn' re-rendered is 128 bars, 2:47.

The four mp3s and the re-rendered scherzo are in `songs/_endless_orchestra/out/life/` (main checkout, with a README).
`endless orchestra` is now `orchestra-symphonic`.

## Round o2: the post-q1 fixes, idiom, themes and set diversity - a PAIRED round (2026-10-16)

The question: does the round-o2 code beat master (the post-q1 scherzo / dialogue / fugato fixes included on both
sides) on the same set plan?

- One shared plan (`shared_plan.py plan ... 95000 8 --genre orchestra-symphonic`, drawn by the new code: vivace,
  andante, vivace, river, allegro, scherzo, andante, river), best-of-4 per code, seed 95000. Master ignores the
  draws it does not know (climax, build, size).
- 16 generated packets + 3 hidden references (`songs/pro-orch-symphonic-stormy` / `-river` / `-scherzo`, written
  for this round). `deal o2 ... --panels 2 --split --orch`: each slot's two versions go to different panels, both
  panels get the references. Seven lenses per panel (composers A/B/C, a dramatist, a melodist, an orchestrator, a
  statistician), 14 judges. JUDGE_ORCH_Q.md gained a `template:` flag per packet (the same plan as other packets).
- `KEY_orch_o2.json`; the new code's mp3s (by packet ID), the KEY and SCORES.txt are in
  `songs/_endless_orchestra/out/blind_o2/` (main checkout).

| new - old (paired by lens across the panels) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| mean (n 56) | +0.05 | -0.05 | -0.05 | -0.23 | +0.04 | -0.16 | **-0.09** | -0.04 |

- Per slot (overall, raw): +0.29, -0.71, -0.29, -0.14, +0.29, +0.71, -0.57, -0.29. Over the 8 slots -0.09 (se
  0.17), normalised by each judge's reference mean -0.09 (se 0.26); slots won / lost 3 / 5. **No paired win: DON'T
  MERGE** (the composition changes are a wash).
- The references lead by far: stormy 8.43, scherzo 7.79, river 6.00. The generated pieces score 4.0-6.0 (best:
  old-007 6.00; new-007 'The Stormy Mountains', an andante with the quiet climax on a chamber orchestra, 5.43).
- Template flags: per packet new 51.6, old 39.1, references 3.3. Panel 2 grouped the new pieces (and old-002) into
  one plan family; the climax / build / size draws did not make the pieces sound less alike, because the shared
  material sits elsewhere.
- The tells, ranked by judges x pieces:
  1. The stock pre-climax build: a 12-32 beat timpani dominant pedal, a rising oboe line, a cymbal roll, then the
     tutti with a crash (13 of 14 judges, about 8 pieces per panel; both builds keep the timpani roll).
  2. The development does not develop the motto: generic broken-chord sequences through a key chain, fugato
     subjects unrelated to the main idea (12 of 14).
  3. The climax restates the theme louder in octaves instead of transforming it (augmented, in the major, against
     a counter-line), and the top register is spent early (11 of 14).
  4. Shared material across pieces: the flute parallel-thirds opening over harp, the same oboe / clarinet second
     theme over harp, the same accompaniment cells (violins2 eighths, violas on 1/2/3) (9 of 14).
  5. Mottos as repeated-note signals; themes without a leap, a held peak or an answering phrase (6 of 14).
  6. Orchestration (the orchestrators): basses under E1, horns at E5-F5, trumpets at D#6, a flute under A4 under
     the horns, the whole tutti on the melody.
- Not judged but measured (24 pieces, sets 95000 / 96000 / 96100, the same seeds both codes):

| | master | o2 |
|---|---|---|
| theme two-note shakes per theme | 0.42 | 0 |
| trombones over Bb4 / bassoons over C5 / brass runs (3 onsets < 0.2 s) | 91 / 9 / 180 | 0 / 0 / 0 |
| distinct (feel, layout, kinds, climax, build, coda, size, ...) plans per set | 7.3 / 8 | 8 / 8 |
| features one value holds in 5+ of 8 pieces (of 12) | 5 | 2 |
| climax types / builds / development forms / first textures per set | 2 / 1 / 2.7 / 3 | 3.7 / 2 / 4.7 / 4.3 |
| texture-set Jaccard between pieces | 0.43 | 0.33 |
| feel order per set | the same every set | drawn |
| score mean (best-of-1) | 97.6 | 95.2 |
| gate rejects (`--candidates 1 --tries 4`) | 13 of 32 | 2 of 18 |

- The gate's "no single track" sum clicks were the SSO sustain samples' edit-splice glitches (113 of 211 sustain
  files have one; 1st-violins-sus-g4 at 2.27 s, inside its loop). The sampler's new `repair` bridges them at load;
  `film_orchestra(repair=9)` on the symphonic genre. A VPO cello file's "glitch" at its loop end is the seam and is
  kept (`keep` = the loop points).
- The six HEAD_SHAPE profile checks pass on 0.09 of the themes (master 0.18): the shake fix moved landings.

## Round o3: development from the motto, builds, a transformed climax, material variety - PAIRED (2026-10-17)

The question: does the round-o3 code (o2's branch merged, then the six judge-ranked fixes below) beat master (q1) on
the same set plan?

- The fixes (all symphonic-only; piano genres + orchestra-film bit-identical, 24 of 24 hashes):
  1. The development works the motto: `Writer.develop` with `DEV_TECH` (sequence through keys, fragmentation to the
     kernel, stretto, the motto against the second theme, the motto in the bass); the fugato's tail is the kernel
     sequenced and its counter-subject the motto (plain or inverted, anchored near home).
  2. Pre-climax builds drawn per piece from its material (`BUILDS`: motto stretto, brass calls answered closer, a
     bass pedal with the motto, subito pp then crescendo, a thickening fugato, tremolo, pulse; textures
     stretto_build / calls_build / bass_build / subito_build / fugato_build); the long timpani roll only ends a
     tremolo build.
  3. The climax transformed (`APEX`: augment under running figures, motto + theme combined, reharmonised in a new
     key, the second theme as apotheosis; a minor piece may close in the tonic major) and `RULES['reserve']`: no
     line before the peak reaches the peak's top note (moved or folded down an octave).
  4. Material draws per set (`SOURCES` for the opening, `T2_COLOURS` for the second theme, `ACCOMPANIMENTS`,
     `ENDINGS`, `derive`: the second theme's head from the motto), held apart by set_memory; the flute-thirds
     opening down to weight 0.25.
  5. Mottos with character (`MOTTO_CHARACTER`: a leap of a fourth+, one peak, at most one repeat, span <= 12; new
     cells spring / arch / fanfare / plunge, leap / soar / fall); generated skeletons.
  6. Range floors / ceilings (`ROLE_TRAITS` 'bottom': basses E1, flutes G4; horns top D5, trumpets C6), inner parts
     kept off the melody in the tutti (oboes 0.4 / trumpets 0.3 doublings).
- Measured (`songs/_blind/tells_orch.py`, 24 pieces: sets 96000 / 96100 / 96200, one candidate, no render):

| | master (q1) | o2 | o3 |
|---|---|---|---|
| mottos with character | 0.63 | 0.54 | 1.00 |
| motto repeated notes | 0.71 | 0.58 | 0.04 |
| development bars stating a motto shape | 0.74 | 0.75 | 0.85 |
| stock build (timpani roll 8+ beats before the peak) | 1.00 | 1.00 | 0.00 |
| climax = the first theme copied (onset + interval share) | 0.76 | 0.65 | 0.21 |
| climax roles doubling the melody | 0.27 | 0.28 | 0.23 |
| top register spent before the climax | 0.71 | 0.75 | 0.00 |
| range slips per piece (basses < E1, horns > D5, trumpets > C6, flutes < G4) | 36.3 | 42.8 | 0 |
| cross-piece material similarity (pair share, 6 gestures) | 0.114 | 0.089 | 0.083 |
| score mean | 97.7 | 94.9 | 95.1 |

- The round: one shared plan (`shared_plan.py plan ... 97000 8`, drawn by the new code: river, vivace, andante,
  river (E dorian), allegro, vivace, andante, allegro). `shared_plan.fit` (new): a drawn value the code's set table
  does not offer (the new motto cells, intro 'solo') is dropped for that code, which draws its own. Best-of-4 per
  code. Master's slot 8 (C major heroic allegro, compact) failed the gate in all 21 candidates (flat_dynamics:
  trombones as melody, then the whole piece flat) - slot 8 is out, 7 pairs. 14 generated packets + the 3 hidden
  references, `deal o3 ... --panels 2 --split --orch`, the o2 lenses (composers A/B/C, dramatist, melodist,
  orchestrator, statistician) per panel, 14 judges. `KEY_orch_o3.json`; the new code's mp3s (by packet ID; slot 8
  as unjudged-new-008), the KEY and SCORES.txt in `songs/_endless_orchestra/out/blind_o3/` (main checkout).

| new - old (paired by lens across the panels, n 49) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | +0.18 | +0.31 | -0.12 | +0.27 | +0.10 | -0.18 | **+0.08** | +0.06 |
| won / tied / lost | 20/16/13 | 17/24/8 | 15/18/16 | 23/10/16 | 19/16/14 | 19/12/18 | 23/8/18 | 18/15/16 |

- Per slot (overall, raw): 001 +1.00, 002 +1.43, 003 +0.71, 004 -0.43, 005 0.00, 006 -0.86, 007 -1.29. Over the 7
  slots +0.08 (se 0.38), normalised by each judge's reference mean +0.01 (se 0.42); slots won / tied / lost 3 / 1 / 3.
  **No paired win: DON'T MERGE** the composition (development +0.27 and harmony +0.31 lean new, life -0.18 and form
  -0.12 lean old; all inside one se).
- References: stormy 8.14, scherzo 7.43, river 5.86. Generated 3.9-6.7: best old-007 'Toward the Sea' 6.71 (the
  andante fugal, its own motto: a cello motto, a late build), best new new-003 'Overture: Golden Rivers' (GEUP) 5.86;
  worst new new-004 (WDUH) 4.57, new-006 (XLQR) 4.71. Slot 7 lost most: new XPBX (andante fugal, no brass on a
  chamber size) life 4.1.
- Template flags per packet: new 37.7, old 38.0, references 22.0 (o2: 51.6 / 39.1 / 3.3) - the new code lost its
  o2 excess, but no more than that; this panel flagged the references far more.
- The tells now (both codes; judges x pieces):
  1. One section plan for the whole set (6 of 14): intro -> theme over a repeated-8th vamp -> the motto in the bass
     under violin 16ths -> a thin solo second theme over harp / off-beats -> fugato or sequence -> pedal build ->
     recap -> coda; equal section layouts across pieces (XLQR = YWCN, SZDR ~ XARK), 4 / 8-bar modules. The block
     ROW is the template now, not the textures inside it.
  2. Recapitulations copied (11 of 14): the return = the exposition's bars; the second theme never comes back or
     comes back unchanged.
  3. The pedal build still heard (7 of 14; new CDCY / LCCA / XPBX among the pieces named): "a bare dominant pedal
     (timpani + basses), a woodwind line climbing, a tutti" - the long roll is gone, the pedal + rising line is not
     (tells_orch's build_stock counts only the roll: it reads 0 where the judges still hear the stock build).
  4. Second themes that are held notes / broken chords, not a 4+4 tune; leads with few rhythm cells (7 in 25 bars).
  5. Figuration: octave-folded runs (GEUP violins1 13-18), 16-bar unchanged ostinati (WDUH violas 1-16, LCCA 1-16).
  6. Orchestration: violas above the violins, timpani off tonic / dominant (A3, B3, Cb4), the flute's C7 as the
     tutti top, GEUP 76% unison / octave role pairs, quiet 6/8 sections with one line.

## Round o4: forms, recomposed returns, build frames, tunes, idiom - PAIRED, o3 + o4 vs master (2026-10-17)

The question: does the o4 code beat master (q1 + the o3 infrastructure) on the same set plan? The o4 code is o3's
branch merged, plus the o3 judges' seven fixes. o3 and o4 together are compared against master.

- The fixes (all symphonic-only; piano genres + orchestra-film bit-identical, 24 of 24 hashes after the last change):
  1. Forms: `_SYM_LAYOUTS` adds rondo, variations, ternary, arch, through, false, scherzo_trio and journey_var. Each
     feel lists its `layouts`, and the set draws one (set_memory 3). Free phrase lengths (`PHRASES`: 6 / 10 / 12
     bars, capped by `PHRASE_CAP`) and one elided block (`ELIDE`). The new kinds are refrain, trio and var
     (`Writer.variation`).
  2. Recomposed returns: the restated recap is reharmonised and dotted (`RECAP_VARY`) over `Writer.theme_under`.
     recap2 is `cantilena(vary=True)` with a motto counter-line, and the apex returns are a varied sentence with the
     second theme.
  3. Build frames (`BUILD_FRAMES`: pedal / ascent / circle of fifths / lament, slash chords).
  4. Second themes as periods: a head cell with a leap, an answer phrase in the head's rhythm, one high point, and
     6 / 10 / 12-bar stretches by `stretch`. Varied sentences; new LYRIC cells.
  5. Runs turn at the range edge (no octave fold), and `_reserve` turns notes under the top. Ostinati change their
     figure every 4-8 bars (`OSTINATO_VARY`).
  6. `IDIOM` / `_orchestra_pass`: timpani tuned to tonic / dominant per block (F2-E3), violas under the violins,
     horns at a chamber climax, the flute's top at A6.
  7. Dynamics: every line arcs per two bars (`SHAPE['phrase']`), the shape moves under `SHAPE['ceiling']`, and
     sforzandi fall only on a theme's arrivals. A recap of half notes had been all sforzandi, its doubling at 127.
     Gate check, 8 slots x 1 candidate: 1 reject in 9 renders. In this round master lost slot 5 in 4 of 4
     candidates and 3 more in a re-run.
- Measured (`tells_orch.py`, 24 pieces: sets 96000 / 96100 / 96200, one candidate, no render):

| | master | o3 | o4 |
|---|---|---|---|
| blocks of 4 / 8 / 16 bars (mod48) | 0.88 | 0.79 | 0.57 |
| distinct block lengths per piece | 3.0 | 3.2 | 4.3 |
| pairs with the same macro form (same_core) | 0.25 | 0.27 | 0.06 |
| pairs with the same block row / row similarity | 0.20 / 0.65 | 0.04 / 0.65 | 0 / 0.52 |
| recap melody bars inside a copied exposition pair (recap_mel) | 0.37 | 0.42 | 0.16 |
| recap role-bars copied note for note | 0.30 | 0.07 | 0.12 |
| second theme copied on its return (t2_copy) | 0.83 | 0.77 | 0.43 |
| pedal-build frame (dominant pedal + rising line) | 1.00 | 0.75 | 0.29 |
| second theme a tune (t2_ok) / its notes per bar | 0.08 / 2.5 | 0.21 / 2.5 | 0.88 / 3.2 |
| melody rhythm cells per 25 bars | 6.8 | 6.9 | 7.5 |
| octave folds in fast lines | 2.1 | 2.5 | 0.9 |
| longest unchanged ostinato (bars) / parts 8+ | 7.0 / 1.17 | 5.9 / 0.38 | 3.7 / 0.08 |
| viola notes above the violins | 11.1 | 19.2 | 0.25 |
| timpani off tonic / dominant or range | 5.1 | 4.4 | 0 |
| flute notes at B6+ | 1.25 | 0.46 | 0 |
| score mean | 97.7 | 95.1 | 94.0 |

- The round: one shared plan (`shared_plan.py plan ... 99000 8`, drawn by the o4 code: andante variations,
  vivace ternary, andante sonata, river journey, scherzo compact, allegro variations, vivace rondo, river false).
  Master's fit dropped the new layouts, motto cells and the 'solo' intro, and drew its own. Best-of-4 per code.
  Master's slot 5 (Bb scherzo) failed the gate in all 4 candidates (flat_dynamics on flutes / oboes) and stopped
  its run. Slots 6-8 were rendered with seed 99100, and slot 5 again with seed 99300 and 6 tries: 3 more rejects,
  then 'Symphonic Dance: Mountains of the Storm'. 16 generated packets + the 3 hidden references went through
  `deal o4 ... --panels 2 --split --orch`, with the o2 lenses per panel (14 judges). `KEY_orch_o4.json`. The o4
  mp3s (by packet ID), the KEY and SCORES.txt are in `songs/_endless_orchestra/out/blind_o4/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | +0.32 | +0.07 | -0.18 | +0.30 | -0.16 | -0.11 | **+0.14** | +0.16 |
| won / tied / lost | 24/22/10 | 19/22/15 | 17/20/19 | 26/11/19 | 17/20/19 | 18/15/23 | 21/21/14 | 19/27/10 |

- Per slot (overall, raw): 001 -1.00, 002 +0.29, 003 +0.71, 004 +0.71, 005 -0.57, 006 +0.57, 007 +0.71, 008
  -0.29. Over the 8 slots the mean is +0.14 (se 0.24); normalised by each judge's reference mean, +0.14 (se 0.25).
  Slots won / lost: 5 / 3.
- **DON'T MERGE:** this is not a clear win (under 2 se, and under +0.3). o3 (+0.08) and o4 (+0.14) both lean new,
  but each sits inside one se. Melody (+0.32) and development (+0.30) lean new; form (-0.18) and orchestration
  (-0.16) lean old.
- **Template flags** per packet: new 17.5, old 42.0, references 0 (o3: new 37.7, old 38.0). The form fix is what the
  judges heard. The flagged families are mostly master's: the flute-thirds intro over harp, then theme / 16ths /
  fugato / timpani-pedal + cymbal roll / literal tutti recap (AJHL, RUCM, UHSK, KNHS), and BXBH = TWJT bar for bar.
  New CDLV / HVEE / XKWU (6/8) still share a bVI-harp coda plan and an 8-bar opening ostinato.
- **References:** stormy 8.0, scherzo 7.0, river 6.6. Generated pieces 3.0-5.7; the gap is +2.49 overall. The best
  piece is new-003 GBKJ 'The Distant Riders' (A dorian andante sonata) at 5.7, then new-006 SXQW 'Overture: Golden
  Storms' at 5.6. The worst are slot 5's scherzo in both codes: new KKWX 3.0 (held notes over oom-pah, a bare
  unison ending) and old KXSJ 3.6. Slot 1 lost most: new PLHU (the variations andante; violin 16th filler at 23-30
  and 41-50, an abrupt end) 4.1 against old BXBH 5.1.
- The tells now, new pieces:
  1. Thin middles and held-note themes: KKWX 9-58, TVLW 13-34 / 53-58, XKWU 45-62, HVEE 51-68. These two- or
     three-voice stretches need a counter-line.
  2. Figuration that does not follow the harmony: PLHU's 16th circling (23-30, 41-50) and GBKJ 24-25 clusters. A
     variation's figure should come from the theme's intervals.
  3. Endings: a bare unison or a stop (KKWX 115-118, PLHU 64, HVEE / XKWU 79, TVLW 64). These want a voiced cadence
     from a dominant.
  4. Melody balance: violins1 at G4-A4 under the harp / violas (CDLV 13-18, HVEE 9-26, XKWU 9-22). The climax
     doubles every wind on one line.
  5. Brass idiom: trumpets carrying tunes at Bb3-Eb4 (KKWX 25-38); a scherzo melody in held notes.
  6. Recaps: still named for master's pieces (AJHL / RUCM / KNHS / UHSK 59-66 = 17-24), rarely for the new ones.

## Round o5: dance, chord figuration, voiced endings, audible melody, brass range - PAIRED, o5 vs master (= o2 + o3 + o4) (2026-10-17)

The question: does the o5 code (master, which now holds o2 + o3 + o4, plus the o4 judges' fixes) beat master on
the same set plan?

- The fixes (all symphonic-only; piano genres + orchestra-film bit-identical, 24 of 24 hashes after the last change):
  1. The scherzo's theme as a dance (`DANCE`, `Writer.dance`): dance cells on the motto's contour, its answer, a
     fragment sequenced by steps, a cadence run. The trio is re-rhythmed with `DANCE['lyric']` cells, and the bass
     is a pump (downbeat + beat 3).
  2. Figuration from the chords (`RUN_FIGURES`, `figuration`): chord-tone ladders, and scales with chord tones on
     the strong positions. The figure re-snaps at every chord change and turns toward the range at an edge.
  3. Voiced endings (`ENDINGS` cadence / strokes / motto / held / plagal; `end_cadence` / `end_strokes` /
     `end_motto`): V7-I or IV-I over four harmony voices, with the fermata on the tonic. The draw has set_memory 2.
  4. The melody audible (`_audible`): the accompaniment and the harp move under a high lead. Climax and cantabile
     textures got counter slots, and the apotheosis no longer triples the line.
  5. The 6/8 family drawn: `CODA_PLANS` (stretto / pedal / hymn, descent / echo / memory), `SOURCE_CHARTS`,
     `SOURCE_ENTRIES`, and `PHRASES['source']`.
  6. Brass range: the trumpets' tune floor G4 (ROLE_TRAITS 'tune', `_tune_ok`). A tune that does not fit a role's
     range whole goes to another role.
  7. Chamber climaxes: the plan has 2 chamber slots (1, 7). o4's horns at a chamber climax still apply.
- Measured (`tells_orch.py measure_o5`, 24 pieces: sets 96000 / 96100 / 96200):

| | master | o5 |
|---|---|---|
| held bars in the scherzo's themes (sch_held) | 0.43 | 0.20 |
| melody bars carried by one line (one_line) | 0.24 | 0.20 |
| off-chord notes on strong positions in figuration (fig_off) | 0.34 | 0.04 |
| beats circling inside a third (fig_circ) | 0.31 | 0.34 |
| final chord pitch classes / bare endings / approached from V or IV | 2.5 / 0.25 / 0 | 3.0 / 0.04 / 1 |
| melody notes under the accompaniment's top (mel_under) | 0.22 | 0.02 |
| harp over the melody | 0.04 | 0.005 |
| climaxes with a counter-line | 0.33 | 0.79 |
| trumpet tune notes under G4 per piece | 4.0 | 0 |
| 6/8 pairs: same coda plan / same opening / same ending | 0.18 / 0.09 / 0.18 | 0.03 / 0.11 / 0.12 |
| score mean | 94.0 | 93.5 |

- The round: one shared plan (`shared_plan.py`, seed 101000, drawn by the o5 code; master fitted it):
  - 1: andante G minor, chamber
  - 2: vivace 6/8 C major
  - 3: andante B minor
  - 4: river E minor
  - 5: allegro D major
  - 6: scherzo A major
  - 7: vivace 6/8 G major, chamber
  - 8: river E minor

  Best-of-4 per code, no gate rejects. 16 packets + the 3 hidden references went through
  `deal o5 ... --panels 2 --split --orch`, with the o4 lenses (14 judges). The KEY is `KEY_orch_o5.json`. The o5
  mp3s (by packet ID), the KEY and SCORES.txt are in `songs/_endless_orchestra/out/blind_o5/` (main checkout).

| new - old (paired by lens across the panels, n 55) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | +0.29 | +0.49 | +0.35 | +0.60 | +0.25 | +0.15 | **+0.40** | +0.24 |
| won / tied / lost | 24/19/12 | 27/17/11 | 22/22/11 | 27/14/14 | 20/21/14 | 17/28/10 | 21/23/11 | 15/35/5 |

- Per slot (overall, raw): 001 -0.33, 002 +1.43, 003 +0.43, 004 0.00, 005 +0.29, 006 -0.29, 007 +1.86, 008 -0.29.
  - Over the 8 slots: +0.39 (se 0.29); normalised +0.41 (se 0.34).
  - Slots won / tied / lost: 4 / 1 / 3.
  - Every dimension leans new. Development (+0.60) and harmony (+0.49) lean the most.
- **The merge bar.** The clear-win bar is missed: +0.39 is under 2 se (0.58), and 4 of 8 slots won is under 5.
  This is the second lean in a row (o4 +0.14 against its master, o5 +0.39 against master = o4), and two
  consecutive leans count under the brief. **Recommendation: MERGE**, on the two-leans rule, not on a clear win.
- **Template flags** per packet: new 29.0, old 27.0, references 2.0 (o4: new 17.5, old 42.0). The judges flag one
  family over both codes. It is a minor piece whose loudest section is the second-to-last: the parallel-major harp
  apotheosis with violins in octaves, horn / bassoon dyads, then a pp coda with a timpani bar. The flagged packets
  are SNDS, EXLQ, TTTU, RFGB, and BCRZ, SKUD, EQYV.
- **References:** stormy 8.3, river 7.8, scherzo 7.7. Generated pieces 3.6-7.1 (mean 5.27; gap +2.66).
  - Best piece: new-003 RXEZ 'Wild Rivers of the Harvest' (B minor andante, through-composed) at 7.1 (o4's best
    was 5.7).
  - Then old-003 HZWH at 6.7.
  - Worst: the scherzo again, new GRGF 3.6 and old APPG 3.9.
- The tells now, new pieces:
  1. Climaxes bring new material instead of the motto (SNDS, EXLQ, WYVP, BCRZ, SJKT 46-54 / 45-52 / 53-60). A new
     hymn or a harp-arpeggio texture appears where the motto should be transformed in horns / trumpets.
  2. The scherzo still has no tune on top (GRGF 1-28, 65-91). Its t1 drew `motto_bass`: the dance tune is in the
     cellos / basses, and violins1 plays broken-chord eighths over it. The judges hear the arpeggio as the theme.
  3. Developments and episodes not built from the motto (SJKT 24-41, WYVP 23-32, BCRZ 29-47, EXLQ 25-44).
  4. Repeated-note wind accompaniment (SKUD 1-16: flutes in 16th thirds, repeated-note rate 0.76) and a bare tutti
     unison scale as filler (SKUD 35-40).
  5. The shared minor-to-major harp apotheosis plan (the template flags above). Also endings on a held tutti chord
     with a 12-beat timpani roll (GRGF, SJKT).

## Round o6: the climax from the piece's material, the development on the theme, the climax's key per set - PAIRED, o6 vs master (= o5) (2026-10-17)

The question: does the o6 code (the o5 judges' fixes on master, which holds o2-o5) beat master on the same set plan?

- The fixes are symphonic-only: piano genres and orchestra-film are bit-identical (24 of 24 hashes after the last
  change). docs/ORCHESTRA_ENDLESS.md "Round o6" has the details.
  1. The climax from the piece's own material:
     - `APEX` 'combine' puts the motto on top with the second theme under it as the counter-line.
     - 'theme_aug' (new) is the first theme augmented.
     - 'augment' is in the trumpets over a viola / horn counter.
     - The apotheosis texture has a spiccato run instead of a default harp arpeggio.
  2. The scherzo's tune on top (`SCHERZO_TEX`): its theme blocks never draw `motto_bass` / `running_strings`.
  3. The development on the first theme (`DEV_TECH['theme']`): imitative two-bar models from the theme's opening,
     shortening and liquidating. 'sequence' states the whole motto only in its first half.
  4. Filler:
     - The river's wave figuration was stuck on one repeated note (a bug: `p_first` was never cleared).
     - The river's flutes leave the texture partway through.
     - `close` no longer draws the tutti unison scale.
  5. The set plan:
     - Climax key modes `CLX_MODES` home / picardy / parallel / relative (draw `clx_mode`, set_memory 2).
     - The second theme keeps its first statement's skeleton in either mode (`Writer.tmode`), so the climax brings
       no new hymn.
     - Coda set_memory 1, `end_soft` draws three textures, and the timpani end rolls are chance draws.
     - Drawn intro lengths.
- Measured (`tells_orch.py measure_o6`, 24 pieces, sets 96000 / 96100 / 96200; the references with `--refs`):

| | master | o6 |
|---|---|---|
| climax melody windows matching the motto (clx_motto) | 0.25 | 0.50 |
| climax windows matching any own material (clx_own) | 0.50 | 0.60 |
| development / episode bars with own material (dev_own; references 0.84) | 0.77 | 0.79 |
| the same with the motto (dev_mot) | 0.65 | 0.69 |
| scherzo theme bars with the tune under another line (sch_buried) | 0.44 | 0.02 |
| longest woodwind repeated-note run, bars (rep_wind) | 1.0 | 0 |
| body bars in 5+-role unison per piece (unison) | 0.79 | 0.54 |
| beats circling inside a third (fig_circ) | 0.34 | 0.07 |
| climaxes with harp arpeggios / with a counter-line | 0.29 / 0.79 | 0.08 / 0.92 |
| pairs with the same climax-mode / coda / ending plan (same_plan) | 0.05 | 0.01 |
| pairs with the same climax turn (same_turn) | 0.23 | 0.13 |
| 6/8 pairs with the same opening / pairs with the same ending | 0.11 / 0.12 | 0.11 / 0.21 |
| score mean | 93.5 | 93.0 |

- The round used one shared plan (`shared_plan.py`, seed 103200, drawn by the o6 code; master fitted it, dropping
  `clx_mode` and turning 'theme_aug' into its own apex draw).
  - Seed 103100 was tried first. Its slot 2 (a Bb vivace) failed the gate in every candidate of BOTH codes
    (silent_notes: violins2's first 16th, F4 at 1:1, in a `river_strings` intro), so it was replaced.
  - The slots:
    - 1: andante Ab major
    - 2: vivace 6/8 Eb major, chamber
    - 3: river D minor
    - 4: vivace 6/8 G minor
    - 5: allegro C major, chamber
    - 6: scherzo G minor, chamber
    - 7: andante Eb major
    - 8: river A minor
  - Best-of-4 per code. The new code had 2 gate rejects on slot 8 (silent violins2 A4), master had none.
  - The 16 packets plus the 3 hidden references went through `deal o6 ... --panels 2 --split --orch`, with 14
    judges. composerA / composerB of panel 2 left out the `overall:` lines, and were asked to add them without
    changing anything else.
  - The KEY is `KEY_orch_o6.json`. The o6 mp3s (by packet ID), the KEY and SCORES.txt are in
    `songs/_endless_orchestra/out/blind_o6/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | -0.11 | -0.02 | +0.04 | +0.16 | -0.05 | +0.21 | **+0.00** | -0.14 |
| won / tied / lost | 14/23/19 | 14/22/20 | 18/22/16 | 23/18/15 | 12/28/16 | 23/19/14 | 18/18/20 | 9/30/17 |

- Per slot (overall, raw): 001 -0.43, 002 +0.57, 003 -0.14, 004 -0.14, 005 +0.43, 006 -0.86, 007 +0.29, 008 +0.29.
  - Over the 8 slots: +0.00 (se 0.17); normalised +0.00 (se 0.23).
  - Slots won / lost: 4 / 4.
- **The merge bar.** The bar is missed on every count. 0.00 is not over 2 se. +0.3 with 5 of 8 slots won is not
  reached. And no lean, so o5's lean is not followed by a second one. **Recommendation: DON'T MERGE.** Keep the
  branch for its parts: the wave bug, `SCHERZO_TEX`, `clx_mode`, the `theme` development and the tells.
- **Template flags** per packet: new 26.5, old 23.4, references 23.7 (o5: 29.0 / 27.0 / 2.0). This round the
  judges also flagged the references with each other and with generated pieces, so the flags no longer separate
  the codes.
- **References:** stormy 7.8, scherzo 6.9, river 6.0. Generated pieces 3.4-6.7 (mean 4.93; gap +1.98).
  - Best piece: new-007 GKJW 'Golden Storms of the Sea' (Eb andante, false recap, reharm climax in the parallel
    minor, combine development) at 6.7, over the river reference.
  - Then old-001 GVZW at 6.6.
  - Worst: the scherzo again, new GKVA 3.4 and old FDXG 4.3. The new scherzo lost slot 6 by -0.86.
- The tells now:
  1. The scherzo's climax. GKVA drew `combine`, and its plain motto statements span two bars of the internal U.
     At scale 2 that is one note per 3/4 bar, so the dance tune comes back as whole-bar notes (113-124, "the theme
     augmented into whole-bar notes", 5 of 7 judges). At scale 2, state the motto at its own speed (or diminished),
     and keep 'augment' / 'theme_aug' out of the scherzo.
  2. Repeated-note inner strings with no melody (GKVA 17-24 and 73-96, a chromatic repeated-note patch) and
     near-empty interludes (89-96).
  3. The voiced endings:
     - A dominant without a bass, then a tonic voiced upside-down: trombone or bassoon on top, the bassoon an
       octave over the clarinet (orchestrator p1 / p2: GKVA, JADZ, KZCG, WCKZ, XZLB, FDXG, RDLB, TSGG, UZFK).
     - Several pieces stop on two or three held chords (5 judges).
     - Fix `ENDING_CADENCE`'s voicing: the root in the bassoons / tuba / basses, the trombones closed under the
       horns.
  4. Climaxes as octave-unison tuttis of the motto (MYKG 57-61, XZLB 54-77, JADZ 88-93, WCKZ 59-63 and others).
     The motto now appears at the climax (the tell rose), but it is stacked in octaves. Give the line to one or two
     colours, with brass harmony and a counter.
  5. The stock climax build: a cymbal roll, a crash and the choir at the build (5+ pieces, statistician), and the
     shared 6/8 bass cell (1 / 0.92, 2 / 0.42 ...).
  6. Melodies under their accompaniment in low registers (UZFK violins at C4-A4, MYKG oboe C4-E4), and figuration
     that runs as a random walk.
  7. The silent first 16th of a `river_strings` intro at 1:1 (violins2): every candidate of plan slot 103100/2 failed
     the gate in both codes.

## Round o7: the scherzo's climax, voice-led endings, climaxes in colours, moving inner parts - PAIRED, o7 (= o6 + o7) vs master (= o5) (2026-10-17)

The question: does the o7 code (o6's branch plus the o6 judges' fixes) beat master on the same set plan?

- The fixes are symphonic-only, except for one infra fix in `bandlib/orchestra.lead`. Piano genres and
  orchestra-film are bit-identical: 24 of 24 hashes and scores after the last change. docs/ORCHESTRA_ENDLESS.md
  "Round o7" has the details.
  1. **The scherzo's climax** (`APEX_SCHERZO`): at scale 2, 'augment' and 'theme_aug' become 'combine' and 'reharm'.
     There 'combine' is the dance tune itself over the second theme, and the triumph coda's motto is diminished
     (one statement per song bar).
  2. **Voice-led endings**:
     - `_approach` writes the approach bars per ending: cad64 (I6/4-V7, 3-2 in the top), IV-V7, a plagal IV, or a
       tonic pedal.
     - `_resolve` voice-leads the final chord: the leading tone up, the seventh down, the third present.
     - `END_VOICING` puts the tune in violins / flutes on top, and the dominant keeps its bass.
     - The end textures' harmony voices go in score order.
     - The soft ending is drawn per piece (`SOFT_OF`), and the ending has set_memory 3.
  3. **The climax in colours**: `tutti_symphonic`, `apex_*`, `hammer` and `tutti_chorale` give the line to 1-2
     colours (plus chance doublings), the brass the harmony, and another choir the counter.
  4. **Moving inner parts** (`INNER_MOTION`, `_move_inner`: suspensions, neighbour alternations, passing tones).
     The bass plays the tune's rhythm instead of the octave unison (`_bass_in_rhythm`).
  5. **Infra** (branch `orch-infra-lead-start` = 70d9df2 + 0161157 on master, which can go alone; here 54a63b1 +
     c906d49 + f93b2a0): `orchestra.lead` clamped a run at 0 into a flam, so the first note sounded 38 ms and was
     silent. The long notes after a clamped one now keep LEAD_KEEP (0.75) of their distance and at least
     LEAD_FLOOR (0.15 s) of it. All 6 gate rejects of o6 pass, and so does a 16th cello pickup (o7 slot 5, 76 ms with
     LEAD_KEEP alone).
- Measured (`tells_orch.py measure_o7`, 24 pieces, sets 96000 / 96100 / 96200):

| | master | o6 | o7 |
|---|---|---|---|
| scherzo theme bars in whole-bar notes (sch_whole) / held (sch_held) | 0.072 / 0.195 | 0.042 / 0.121 | 0.036 / 0.121 |
| final chords inverted / upside-down (end_inv) | 1.0 | 0.79 | 0.08 |
| final chords with the tune on top in violins / flutes (end_top) | 0.79 | 0.96 | 0.96 |
| endings on held chords only (end_held) | 0.54 | 0.71 | 0.58 |
| climax melody roles / octaves (clx_mroles / clx_moct) | 1.83 / 1.67 | 1.92 / 1.58 | 1.67 / 1.50 |
| coda roles following the melody / in octaves (coda_follow / _oct) | 2.53 / 2.02 | 2.28 / 1.80 | 1.50 / 1.28 |
| body bars in 5+-role unison per piece (unison) | 0.79 | 0.54 | 0.13 |
| inner parts static (inner_static) | 0.27 | 0.27 | 0.01 |
| stock build per piece (stock_n) | 0.67 | 0.58 | 0.54 |
| pairs with the same ending (same_end / same_end7) | 0.12 / 0.13 | 0.21 / 0.21 | 0.16 / 0.10 |
| folds per piece | 1.67 | 0.92 | 1.63 (worse) |
| score mean | 93.5 | 93.0 | 92.9 |

- The round used one shared plan (`shared_plan.py`, seed 105100, drawn by the o7 code; master fitted it, dropping
  `dev_tech='theme'` / 'theme_aug' in slots 2 and 6).
  - The slots:
    - 1: river A dorian, chamber
    - 2: vivace 6/8 G minor
    - 3: river D dorian
    - 4: vivace 6/8 G minor, chamber
    - 5: allegro C major, chamber
    - 6: scherzo 3/4 G minor
    - 7: andante C minor, chamber
    - 8: allegro D major
  - Best-of-4 per code, 0 gate rejects in both. A first new-code run had one reject (slot 5's cello pickup), which
    led to LEAD_FLOOR; it was then rerun.
  - The 16 packets plus the 3 hidden references went through `deal o7 ... --panels 2 --split --orch`, with 14
    judges.
  - The KEY is `KEY_orch_o7.json`. The o7 mp3s (by packet ID), the KEY and SCORES.txt are in
    `songs/_endless_orchestra/out/blind_o7/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | +0.30 | +0.16 | +0.07 | +0.07 | +0.38 | +0.68 | **+0.23** | +0.04 |
| won / tied / lost | 23/18/15 | 22/17/17 | 20/18/18 | 20/16/20 | 25/18/13 | 31/18/7 | 25/15/16 | 15/26/15 |

- Per slot (overall, raw): 001 +0.57, 002 +0.00, 003 -1.14, 004 +0.14, 005 -0.14, 006 +2.14, 007 +0.29,
  008 +0.00.
  - Over the 8 slots: +0.23 (se 0.33); normalised +0.23 (se 0.39).
  - Slots won / tied / lost: 4 / 2 / 2.
- **The merge bar.** The bar is missed:
  - +0.23 is not over 2 se (0.66).
  - It is not over +0.3 with 5 of 8 slots won (4 won).
  - o6 was a tie, so this lean is the first, not the second in a row.
  - **Recommendation: DON'T MERGE yet.** It is a lean, and the scherzo fix is clear (+2.14). A round o8 on this
    branch that leans again would meet the second-lean bar. The infra fix (`orch-infra-lead-start`) can go to master
    now on its own.
- **Template flags** per packet: new 29.4, old 26.8, references 8.3 (o6: 26.5 / 23.4 / 23.7).
- **References:** stormy 7.9, scherzo 7.1, river 6.2. Generated pieces 3.0-5.4 (mean 4.71; gap +2.37, o6 +1.98).
  Against o6 the references rated higher (7.07 vs 6.9) and the generated pieces lower (4.71 vs 4.93): a harsher
  panel or set, which the paired diff does not see.
  - Best piece: new-004 JWCL 'Burning Storms' (G minor 6/8 vivace, arch, chamber) at 5.4.
  - Worst: old-006 PLSN, master's scherzo, at 3.0. The new scherzo XGPD reached 5.1.
  - The losing slot 3 (new WGKU 4.1 vs old KGRJ 5.3): a D dorian river whose development is a chromatic trumpet line
    over C# / Eb / G# chords (7 of 7 judges).
- The tells now:
  1. Development / episode passages with chromatic material unrelated to the motto (WGKU 37-46, SKKW 36-43, PFBT
     13-20). Sequence the motto / theme head through related keys instead.
  2. The climax / coda without the motto (THGD 47-64, WDMN 86-92, PFBT 61-68, JWCL 51-58). State it in the brass
     at the climax and the close.
  3. Themes that are only running arpeggios / sixteenths (AMNU 5-12, THGD v1 in 32 of 66 bars, SKKW's clarinet
     scale for 14 bars without a breath).
  4. The scherzo cell restated almost literally about 6 times (XGPD), and a 16-bar horn solo over held strings.
  5. Short climaxes after a 4-bar build (JWCL), a quiet harp section between the build and the final tutti (WDMN),
     and soft held-chord codas after ff climaxes.
  6. Final-chord bass: basses and tuba both on D3, the tuba in repeated eighths (WDMN).

## Round o8: related development keys, the motto at the climax and close, a singable theme, proportions, the final bass, folds - PAIRED, o8 (= o6 + o7 + o8) vs master (= o5 + orch-infra-lead-start) (2026-10-17)

The question: does the o8 code (the o7 branch plus the o7 judges' fixes) beat master on the same set plan?

- The fixes are symphonic-only. Piano genres and orchestra-film are bit-identical: 24 of 24 hashes and scores after the
  last change. docs/ORCHESTRA_ENDLESS.md "Round o8" has the details.
  1. **Development keys** (`DEV_PATHS` as home-key degrees, `dev_keys`): the development sequences through the keys
     of the home key's own triads (rise / fifths / thirds / fall), never a chromatic mode on its own. Chromaticism is
     left to the voice-leading.
  2. **The motto at the climax and the close**:
     - The climax tutti textures double the line in trumpets / horns (`tutti_symphonic`, `apotheosis_strings`,
       `apex_*`, `tutti_chorale`, `quiet_climax`), and a brass chorale climax `tutti_chorale_brass` is added.
     - The hymn / memory codas recall the motto in their last bars (`CODA_RECALL`).
     - 'descent' opens on the whole motto.
     - The triumph coda's motto is no longer snapped to the chord.
  3. **A singable theme**: the figuration moves under the tune (`FIG_RANGE`, `FIG_UNDER`), and 't1' no longer draws
     `motto_bass` (the theme as a bass under running violins).
  4. **The scherzo's restatements** (`DANCE_VARY`): the consequent answers with another cell, every second
     fragmentation bar is inverted, and t1b is dotted. The climax dance is reharmonised and inverted.
     `cantabile_horn` gives the strings motion (violins2 / violas arpeggios) under the horn.
  5. **Proportions** (`PROPORTION`: build >= 8 % and 6 bars, peak >= 13 % and 8 bars) and a written fall from the ff
     climax into a soft coda (`CODA_FALL` f -> mp -> pp).
  6. **The final bass** (`END_BASS`): the cellos G2-F#3 / basses G1-F#2 on the low tonic, an octave apart. The
     `end_motto` tuba is an octave doubling at 0.5, and the bass in rhythm merges repeats within a beat
     (`BASS_HOLD`), so there are no tuba repeated eighths.
  7. **Folds** (`FOLD`, `_lower`): a part over the tune is re-voiced to the highest chord tone under it within a
     ninth. Only otherwise does it drop an octave, with a neighbour check, else it is dropped. The whole-part shift
     stays for a share >= 0.25.
  8. **The stock build** (`ARRIVALS`): the arrival is drawn per piece (roll + crash / a dry crash / the timpani only / none), so the cymbal
     roll + crash is no longer every climax's signature.
- Measured (`tells_orch.py measure_o8`, 24 pieces, sets 96000 / 96100 / 96200):

| | master | o7 | o8 |
|---|---|---|---|
| development bars far from the home key (dev_far) / off the chord (dev_off) | 0.13 / 0.042 | 0.104 / 0.066 | 0.017 / 0.034 |
| climaxes with the motto in the brass (clx_brass) | 0.54 | 0.42 | 0.67 |
| codas with the motto (coda_mot) | 0.67 | 0.75 | 0.83 |
| theme bars buried under figuration (th_buried) | 0.28 | 0.32 | 0.09 |
| ff climax straight into a soft held coda (ff_soft) | 1.0 | 1.0 | 0 |
| final bass low tonic + octave (end_oct) / lowest note (end_low) | 0.88 / 38.3 | 0.67 / 38.8 | 0.75 / 36.8 |
| folds per piece | 1.67 | 1.63 | 0.88 |
| stock build per piece (stock_n) | 0.67 | 0.54 | 0.33 |
| scherzo cell share (sch_cell) / literal restatements (sch_lit) | 0.24 / 1.5 | 0.26 / 2.5 | 0.19 / 2.5 |
| build / peak share (prop_build / prop_peak) | 0.086 / 0.120 | 0.081 / 0.124 | 0.092 / 0.133 |
| score mean | 93.5 | 92.9 | 92.6 |

- The round used one shared plan (`shared_plan.py`, seed 107200).
  - The slots:
    - 1: allegro Eb major, arch, chamber
    - 2: river 6/8 C minor
    - 3: andante F major, fugal
    - 4: vivace 6/8 Bb major
    - 5: allegro C major, rondo
    - 6: scherzo 3/4 Bb major, chamber
    - 7: andante Eb major, ternary, chamber
    - 8: river 6/8 B dorian, chamber
  - Best-of-4 per code. Master had 0 gate rejects. The new code had 3 flat_dynamics rejects (rerolled):
    - a tuba pump-bass doubling in `tutti_drive` (unchanged, a 0.4 draw) read as a lead
    - a violins2 ostinato read as melody
    - the trumpets' harmony in `apex_augment` / `chorale_brass` read as melody
  - The references were built with the master code.
  - The 16 packets plus the 3 hidden references went through `deal o8 ... --panels 2 --split --orch`, with 14
    judges.
  - The KEY is `KEY_orch_o8.json`. The o8 mp3s (by packet ID), the KEY and SCORES.txt are in
    `songs/_endless_orchestra/out/blind_o8/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | +0.43 | +0.41 | +0.23 | +0.18 | +0.41 | +0.29 | **+0.39** | -0.02 |
| won / tied / lost | 25/22/9 | 25/20/11 | 20/22/14 | 19/22/15 | 21/31/4 | 20/25/11 | 21/26/9 | 15/26/15 |

- Per slot (overall, raw): 001 +0.86, 002 -0.14, 003 +0.14, 004 -0.43, 005 +0.14, 006 +1.29 (the scherzo again),
  007 +0.57, 008 +0.71.
  - Over the 8 slots: +0.39 (se 0.20); normalised +0.39 (se 0.21).
  - Slots won / lost: 6 / 2.
- **The merge bar.** It is met twice:
  - +0.39 is just under 2 se (0.40).
  - It is over +0.3 with 6 of 8 slots won.
  - It is the second lean in a row (o7 +0.23).
  - **Recommendation: MERGE** (the o8 branch = o6 + o7 + o8).
- **Template flags** per packet: new 24.0, old 19.0, references 0 (o7: 29.4 / 26.8 / 8.3). Most new-new flags are
  in panel 2 (CLND / KQFD / FVNG / PZSU): the same violin 16th broken-chord climax over a brass chorale.
- **References:** stormy 8.4, river 8.2, scherzo 7.8 (o7 7.07 mean, now 8.14). Generated pieces 3.6-6.0 (mean 5.04,
  o7 4.71; gap +3.11, o7 +2.37). The panels rated the references higher, which the paired diff does not see.
  - Best piece: new-007 PZSU 'Toward Summer' (Eb major andante, ternary, chamber) at 6.0.
  - Worst: old-008 UUAC (master's B dorian river) at 3.6; the new XBGS reached 4.3.
  - The losing slots: 004 (FFYD 4.6 vs FGHD 5.0, a 6/8 vivace whose choir arrives only in the last 10 bars over a
    I-IV-V close) and 002 (QMBR 5.9 vs SKNA 6.0, a new arpeggio idea at the climax instead of the opening theme).
- The tells now:
  1. The climax / coda as violins1 16th broken chords over a brass chorale, with the theme absent
     (CLND 57-74, KQFD 56-65 + 72-79, FVNG 72-77, QMBR 55-64, FFYD 53-61; 7 of 7 judges on CLND). Put the theme in
     horns / trumpets there, augmented or in canon, and let the 16ths drop out.
  2. The apotheosis motto restated literally (PZSU 58-63: the same two bars three times, 7 of 7 judges). Sequence,
     reharmonise or raise the third statement.
  3. Episodes with new tunes unrelated to the theme (KQFD S4 / S6, XBGS 25-52, QMBR's climax arpeggio, FFYD
     41-61). Derive them from the first theme.
  4. A static trio / retransition: TZKN 29-64, a harp ostinato under held string notes for 28 bars, then violins1
     alone.
  5. A harp interlude between the climax and the coda (FVNG 64-71), and a coda that thins to tuba + basses + one
     violin (CLND 67-74).
  6. Endings: a bare 2-beat V-I (CLND, FVNG, KQFD), the choir only in the last 10 bars (FFYD), the trumpets
     holding Bb5 at the end.

## Round o9: the theme at the climax, no literal restatements, episodes from the theme, the lead-in, the endings, analysis.leads - PAIRED, o9 vs master (= o8) (2026-10-17)

The question: does the o9 code (master plus the o8 judges' fixes) beat master on the same set plan?

- The fixes are symphonic-only. Piano genres and orchestra-film are bit-identical: 24 of 24 hashes and scores after the
  last change. docs/ORCHESTRA_ENDLESS.md "Round o9" has the details.
  1. **The climax carries the theme** (`APEX_CANON`, `Writer.canon`): the augmented motto / theme in trumpets / horns
     (over the trumpets' G4 floor), the material at its own speed over it as the counter (a canon), the new
     `apex_theme` / `apex_theme_strings` for 'theme_aug'. The 16th figuration enters at 5/8 or 3/4 of the block.
     `set_memory` apex 3.
  2. **No literal restatements** (`REPEAT`, `_unrepeat`): a copied 1- / 2-bar unit moves up a scale step.
  3. **Episodes from the theme** (`DERIVE`, `EPISODE_FROM`): the trio / river tunes grow from the motto, a river's
     episode is its tune varied, the scherzo's consequent takes another cell (`DANCE_VARY['idea']`).
  4. **Static stretches** (`STATIC` 8 bars, `_move_inner`) and the retransition's lead-in (`RETRANS_LEAD`: the
     motto's head over V7).
  5. **After the climax** (`POST_PEAK`): cantabile strings / horn, f -> mf -> mp, no light interlude.
  6. **Endings** (`END_PRE`, `STROKES['motto']`, end rows 3 bars): a predominant bar with the motto's head before V - I;
     the choir out of the symphonic full size.
  7. **The gate** (`analysis.leads`, engine NoteDynamics + test_dynamics): `Song.lead_hint` names the melody's track
     per section; the note-dynamics judge reads the lead kind from it.
- Measured (`tells_orch.py measure_o9`, 24 pieces, sets 96000 / 96100 / 96200; master is o8):

| | master | o9 |
|---|---|---|
| climax bars with running 16ths (clx_fig) / coda (coda_fig) | 0.45 / 0.21 | 0.10 / 0.07 |
| 16ths over a brass melody in half the climax or coda (fig_chorale) | 0.33 | 0 |
| set pairs with the same climax texture (same_clx_tex) | 0.17 | 0.10 |
| climax bars on the theme / motto (clx_theme) | 0.65 | 0.65 |
| most consecutive literal copies (lit_max) / the scherzo's (sch_lit) | 0.083 / 2.5 | 0 / 1.5 |
| episode bars from the theme (epi_own) | 0.30 | 0.34 |
| retransition with a lead-in (rt_lead) | 0 | 0.54 |
| a light block after the climax (post_light) | 0.46 | 0.29 |
| a predominant before the final V (end_pre) / the choir only at the end (choir_late) | 0.63 / 0.36 | 1.0 / none |
| stock build per piece (stock_n) | 0.33 | 0.08 |
| the longest static run (static_run, bars) / folds | 4.0 / 0.88 | 4.1 / 1.08 |
| score mean | 92.6 | 91.8 |

- The round used one shared plan (`shared_plan.py`, seed 109300).
  - The slots: 1 river 6/8 A major; 2 allegro D major, sonata, chamber; 3 andante A dorian; 4 river 6/8 B dorian;
    5 vivace 6/8 Bb major; 6 allegro D minor; 7 andante E minor, fugal; 8 scherzo 3/4 A minor, chamber.
  - Best-of-4 per code. The new code had 0 gate rejects (the lead hint); master had 3 (flat_dynamics on trombones
    and horns read as leads by their names, a silent choir).
  - The new code rendered with the worktree engine (analysis.leads), master with the main engine. The references
    were built with the master code.
  - 16 packets plus the 3 hidden references through `deal o9 ... --panels 2 --split --orch`, 14 judges. The KEY is
    `KEY_orch_o9.json`. The o9 mp3s (by packet ID), the KEY and SCORES.txt are in
    `songs/_endless_orchestra/out/blind_o9/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | +0.45 | +0.09 | +0.32 | +0.32 | +0.29 | +0.34 | **+0.30** | +0.23 |
| won / tied / lost | 27/21/8 | 13/34/9 | 25/19/12 | 23/23/10 | 24/22/10 | 22/23/11 | 25/19/12 | 19/31/6 |

- Per slot (overall, raw): 001 +0.71 (the A major river), 002 0.00, 003 +1.29, 004 +1.14 (the B dorian river),
  005 -0.29, 006 +0.14, 007 -1.00, 008 +0.43 (the scherzo).
  - Over the 8 slots: +0.30 (se 0.27; 17/56 = +0.304); normalised +0.30 (se 0.28). Slots won / lost: 5 / 2.
- **The merge bar.** > 2 se: no (1.1 se). > +0.3 with at least 5 of 8 won: yes, by 0.004 (+0.304, 5 won). A second
  lean in a row: no (o8 was merged; this is the o9 branch's first round). **Recommendation: MERGE** on the letter of
  the bar, a weak one: every dimension but harmony leans new, and melody +0.45 (27 / 8) is the clearest.
- **Template flags** per packet: new 23.1, old 18.9, references 4.0 (o8: 24.0 / 19.0 / 0). The panel-2 new pieces
  (CKNM / DEXR / UZWK / EMWY) share "a solo cello entry that grows into a fugato" and the 6/8 plan (CKNM, EMWY, XXAF).
- **References:** stormy 7.9, river 7.8, scherzo 7.7 (o8 8.14 mean, now 7.79). Generated pieces 3.6-6.4 (mean 5.08,
  o8 5.04; gap +2.71, o8 +3.11).
  - Best piece: new-003 DEXR 'Storms of Winter' (A dorian andante, through) at 6.4 - the best generated piece of the
    symphonic rounds so far.
  - Worst: old-001 FKDT at 3.6; the new CKNM (the same slot) reached 4.3.
  - The losing slots: 007 (UZWK 5.0 vs TKAJ 6.0; 7 of 7 judges: the final E minor chord keeps D#4 in the violins II,
    a FOLD bug - fixed after the round, below) and 005 (EMWY 3.9 vs APRV 4.1, a 6/8 vivace whose loudest music is in
    the middle, S6, with a thin Bb ending).
- **Fixed after the round** (not judged; the 24 hashes unchanged): `_audible` folded the violins II's B4 over the
  approach's dipping soprano to D#4 under B7 and held it into the final tonic. A folded note is now cut at the chord
  change, and each piece is re-voiced to its own chord (test `test_a_folded_note_never_holds_into_the_next_chord`).
- The tells now:
  1. Openings without a theme: the river's clarinet / violin 16th scale runs for 12 bars (CKNM 1-12, 7 of 7 judges), an
     opening that empties after a few bars (ECER 5-10: bar 9 silent, -9 LU; 4 of 7 judges).
  2. The climax placed in the middle: the loudest section mid-piece (EMWY S6, BLMX S6 +3.6 LU), the recap quieter; a
     climax of held brass blocks under a violin line with chromatic side-slips (APPS 69-80), violins I + II in unison
     to B6 (UZWK 72).
  3. Static trios / episodes: the scherzo trio a flute over block clarinet / bassoon chords for 28 bars (EYPC 29-56,
     4 of 7 judges), a static F major oboe episode (cellos on 1 and 3 for 12 bars). The scherzo theme still restated
     nearly literally (EYPC 9-28).
  4. The motto over-stated: its head opens almost every phrase (BLMX, UZWK "about thirty times"), the same
     repeated-eighth bass under whole pieces.
  5. Endings still short after a long build (two bars, EYPC 65-66, UZWK 90-92).
  6. A shared plan signature: the solo cello entry growing into a fugato (CKNM / DEXR / UZWK / XXAF).

## Round o10: early themes, the loudest climax, moving trios, the motto rationed, proportional endings, folds - PAIRED, o10 vs master (= o9) (2026-10-17)

The question: does the o10 code (master plus the o9 judges' fixes, commit f899eee) beat master (13e29d1) on the same
set plan?

- The fixes are symphonic-only (piano genres and orchestra-film bit-identical, 24 of 24 hashes). docs/ORCHESTRA_ENDLESS.md
  "Round o10" has the details and the measured tells (`tells_orch.py measure_o10`): `OPENING` (the mist cut to 8 bars),
  `LOUDEST` (the peak block up to ff, the rest capped at f), `HOLD['restrike']`, `VLN_UNISON`, moving trios
  (`STATIC['figure']`), `DANCE_VARY['return']`, `MOTTO_RATION`, `BASS_FIGS`, `END_LEN`, `FUGUE_ORDERS`, `UNFOLD`.
- The round used one shared plan (`shared_plan.py`, seed 111100, `PLAN_111100.json`), best-of-4 per code, both codes
  rendered with the main engine.
  - The slots: 1 river 6/8 D major; 2 allegro Bb major, arch; 3 andante G major, ternary; 4 river 6/8 C minor;
    5 scherzo 3/4 F major; 6 vivace 6/8 D minor, rondo; 7 andante B dorian (new: through, seed 111126; old: ternary,
    seed 111124 - best-of-4 picked different candidates); 8 allegro D major, arch.
  - 0 gate rejects for either code.
  - 16 packets plus the 3 hidden references through `deal o10 ... --panels 2 --split --orch`, 14 judges (staged in
    D:\tmp\o10\judges, the verdicts scored as `<lens>_p<panel>.md`). The KEY is `KEY_orch_o10.json`. The 16 mp3s (by
    packet ID), the KEY and SCORES.txt are in `songs/_endless_orchestra/out/blind_o10/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable |
|---|---|---|---|---|---|---|---|---|
| raw mean | +0.20 | +0.20 | +0.23 | +0.29 | +0.16 | +0.05 | **+0.39** | +0.09 |
| won / tied / lost | 21/25/10 | 19/28/9 | 24/18/14 | 27/18/11 | 20/26/10 | 20/20/16 | 26/20/10 | 12/37/7 |

- Per slot (overall, raw / normalised): 001 -1.43 / -0.90 (NYQP vs DJZK, the D major river: 6 of 7 lenses for old),
  002 +0.29 / -0.24, 003 +0.14 / +0.67, 004 +0.71 / +0.19, 005 +0.57 / +1.10 (the scherzo), 006 +1.00 / +0.48,
  007 +0.86 / +1.38, 008 +1.00 / +0.48.
  - Over the 8 slots: raw +0.39 (se 0.28), normalised +0.39 (se 0.26). Slots won / lost: 7 / 1.
  - By code (all ratings): new overall 5.04, old 4.64; memorable 2.02 / 1.93.
- **The merge bar.** > 2 se: no (1.4 se raw, 1.5 normalised). > +0.3 with at least 5 of 8 won: yes (+0.39, 7 won).
  **Recommendation: MERGE** on the bar, more clearly than o9 (+0.30, 5 / 2): every dimension leans new, development
  (+0.29, 27 / 11) the most; life (+0.05) barely moved. The one lost slot is a large loss (the river's opening, below).
- **Template flags** per packet: new 28.1, old 28.1, references 1.3 (o9: 23.1 / 18.9 / 4.0). Both codes draw the same
  plan, so the flags are the plan's, not the code's: panel 1's 4/4 pieces (CWAF / DCQG / QTDX / UCVQ: the motto over
  the same build) and its 6/8 pieces (DJZK / FWLD / SCPP), panel 2's (QYCG / TUQB / XFBA, NYQP ~ PPPC).
- **References:** stormy 7.9, river 7.4, scherzo 6.8 (o9 7.79 mean, now 7.36; panel 2 was harsher on them, composerB
  8.0 / 6.3). Generated pieces 3.7-6.1 (mean 4.84, o9 5.08; gap +2.52, o9 +2.71; the normalised paired number
  removes the panels' lenience).
  - Best piece: new-007 UEQX 'Toward the North' (B dorian andante, through) at 6.1, memorable 2.86 (two lenses 7).
  - Worst: new-001 NYQP 'Stormy Rivers' at 3.7, memorable 1.0 - the lost slot.
- The tells now (the new pieces' fixes, by judge count of 56):
  1. **Static middle episodes** (about 30 of 56): held chords under a thin line with no theme and no bass motion before
     the climax - UCVQ 38-49 (7 of 7: clarinet / horn fragments over an F pedal), XFBA 30-37 (6: held clarinet /
     violins over a cello line), FWLD 31-44 (6), UEQX 31-42 (4: twelve bars of flute over a tuba oom-pah), QUGR 49-60
     (3: harp chords under violin long notes), SCPP 43-66 (4: filler instead of the theme). Fix: the episode develops
     the motto (sequence, imitation, the head in the bass or a fresh colour) and keeps a moving bass; or is halved.
  2. **Endings without a cadence** (about 12): DCQG 52-60 (7 of 7: the recap sits on tuba / cello repeated-eighth
     pedals, then fades to held chords and a soft plagal G - D with no V - I), XFBA 66-69 (C - D - G, no V7), QUGR
     (the head ten times over I - V - I in the coda, then three bars of timpani alone), UCVQ (repeated F chords).
  3. **The climax restates instead of transforming** (about 8): SCPP 75-87 the S3 theme note for note (3), QUGR
     97-114 / 115-124 (the theme over held brass in I / V, the return near-literal), DCQG 45-51 a new tune at the peak
     instead of the motto. The tonic-dominant loop through whole pieces (QUGR).
  4. **No tune to hold** (NYQP, 3 + 2): the river's 16th / viola figure with lines that wander, a new idea each
     section, never the opening back at the climax (53-62); unprepared clashes at 41-46.
  5. **Orchestration registers** (the orchestrator in every packet plus composers, about 9): bassoons and trombones
     held at A4 / G#4-Bb4 at f (NYQP, FWLD), the harp holding single notes, thumping bass quarters or striking
     unisons (NYQP, XFBA, UEQX, DCQG, QUGR), the theme in low horns F2-C3 (UCVQ) or the flute's low register under
     violins in the same octave (FWLD), trumpets held at B5 at ff (UEQX), cellos above the violas (DCQG).

## Round o11: the form's argument - the development's share and ladder, the return home, the dominant pedal, one summit, V - I endings, the length - PAIRED, o11 vs master (= o10) (2026-10-17)

The question: does the o11 code (master plus the masterpiece panel's form plan and o10's tells, commit 4fccc1b) beat
master (c691e2f) on the same set plan, and how far is it from a masterpiece?

- The fixes are symphonic-only (piano genres and orchestra-film bit-identical, 24 of 24 hashes; the full
  `python tests/run.py` passed, 77 modules / 1648 tests). docs/ORCHESTRA_ENDLESS.md "Round o11" has the details:
  `DEV_SHARE`, `DEV_LADDER` / `dev_stages`, `RETURN` (recap2 rows in compact / through), `RT_PEDAL` (6 bars with the
  head in imitation), `REHARM` / `APEX_RIVER` (the climax at home, no 'relative' / 'restate'), RULES `reserve` 3 +
  `reserve_after`, `LOUDEST` 'pre' / 'quiet', the plagal ending as pre - V7 - I, `STATIC['walk']`, `MIN_LEN` (3:00),
  `form_stats` in `SCORES['symphony']`.
- Measured (`tells_orch.py measure_o11`, 24 pieces, sets 96000 / 96100 / 96200, master / o11): seconds 168 / 225;
  development share 0.13 / 0.27 (10.7 / 29.7 song bars); longest transposed chain 1.9 / 1.6; dominant pedal bars
  1.5 / 6.3; climax at home 0.71 / 1.0; t1 home 0.71 / 1.0, t2 home 0.85 / 1.0; V - I at the end 0.83 / 1.0; the
  climax's top over everything before it 1.6 / 3.5 semitones, loudness margin 0.8 / 1.7 proxy LU; one_summit 0.17 /
  0.42; tutti at the peak 0.33 / 0.42; folds 0.79 / 1.54 (worse); dev_own 0.80 / 0.67 (worse); still_run 4.4 / 4.6.
- The judge brief (`JUDGE_ORCH_Q.md`) adds the masterpiece question: an absolute `masterpiece` score (10 canon, 7 solid
  professional concert work, 5 competent but anonymous, 3 student exercise) and `missing` (one located sentence);
  `score_round.py --paired` reports the masterpiece means and `--missing` lists the sentences.
- The round used one shared plan (`shared_plan.py`, seed 113000, `PLAN_113000.json`), best-of-4 per code, the main
  engine.
  - The slots: 1 river 6/8 G major; 2 allegro C major, rondo; 3 andante Ab major, ternary; 4 vivace 6/8 Eb major,
    sonata; 5 scherzo 3/4 E minor, compact; 6 vivace 6/8 A minor, rondo; 7 andante C minor, arch; 8 river 6/8 D
    dorian (best-of-4 picked different candidates in slots 1, 3, 4, 7).
  - 0 gate rejects. New pieces 191-298 s (mean 226 s), old 122-215 s (mean 170 s).
  - 16 packets plus the 3 hidden references through `deal o11 ... --panels 2 --split --orch`, 14 judges (staged in
    D:\tmp\o11\judges, verdicts as `<lens>_p<panel>.md`). The KEY is `KEY_orch_o11.json`. The 8 new mp3s (by packet
    ID), the KEY and SCORES.txt are in `songs/_endless_orchestra/out/blind_o11/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| raw mean | +0.43 | +0.25 | +0.34 | **+0.52** | -0.02 | +0.09 | **+0.32** | +0.38 | +0.34 |
| won / tied / lost | 23/23/10 | 21/24/11 | 23/20/13 | 27/16/13 | 17/20/19 | 21/17/18 | 24/17/15 | 24/27/5 | 23/18/15 |

- Per slot (overall, raw / normalised): 001 +1.57 / +1.95 (ARFK vs NZLC, the G major river), 002 +0.43 / +0.05,
  003 +1.29 / +1.67 (YVCM vs TKMN, the Ab andante), 004 -0.71 / -1.10 (RHDT vs QZEJ, the Eb sonata: its climax still
  in the transition at 18 %, the middle a static strings-only development), 005 -0.86 / -0.48 (WBTS vs RMTE, the
  scherzo: the whole piece tops out at F#5 under the reserve margin, 68 bars on one accompaniment), 006 +0.29 / -0.10,
  007 -0.29 / +0.10 (JAUQ vs BRCS: a brass-less C minor climax), 008 +0.86 / +0.48.
  - Over the 8 slots: raw +0.32 (se 0.32), normalised +0.32 (se 0.36). Slots won / lost: 5 / 3.
  - By code (packet means): overall new 5.25, old 4.93, references 6.95; memorable generated 1.97, references 2.62.
- **Masterpiece (absolute, 1-10):** new **4.23**, old 3.89, references 5.50 (the masterpiece panel: generated 4.67,
  references 5.69). Per packet: stormy LNLM 6.36, YVCM (new-003) 5.29, scherzo NFGA 5.14, river QDFH 5.00; the new
  pieces 3.14-5.29, the old 3.29-4.57. One generated piece (YVCM) is rated above two of the three references.
- **The merge bar.** > 2 se: no (1.0 se). > +0.3 with at least 5 of 8 won: yes (+0.32, 5 won), by a small margin.
  **Recommendation: MERGE** (the second merge in a row after o10's +0.39). Development (+0.52, 27 / 13) and melody
  (+0.43) moved most - the form plan worked where it was aimed; orchestration (-0.02) and life (+0.09) did not move,
  and the three lost slots are the reserve margin's and the static middle's cost.
- **Template flags** per packet: new 22.6, old 25.5, references 15.0.
- Best piece: new-003 YVCM 'Symphonic Dance: Riders of the Plains' (Ab major andante, ternary, 4:58) at overall 6.4,
  masterpiece 5.29 (`D:\tmp\o11\r\new\003-symphonic-dance-riders-of-the-plains`, `blind_o11/YVCM.mp3`). Worst: new-005
  WBTS (the scherzo) at 3.6, masterpiece 3.14.
- What the judges say is missing (the `missing` sentences of the 8 new pieces, 56):
  1. **The development is a row of textures, not an argument with the motto** (about 18): ARFK 30-83 (7 of 7: harp
     arpeggios, a D pedal, sixteenths side by side), YFQA 53-66 (the oboe sequence never touches the theme), BLZF 42-57,
     RHDT 47-90 (a vamp), WBTS 120-150. dev_own fell 0.80 -> 0.67: the longer development is filled with frames.
  2. **The summit has no brass and no top** (about 15): JAUQ 60-72 (7 of 7: violins alone to C7, no trumpets /
     trombones), BLZF 85-95 (no trumpets), WBTS (the highest note of the piece F#5), FUQW (never above B5), YVCM 71-82
     (the motto in unison, no trumpets). The reserve margin lowers the earlier material, but the peak block does not
     get the full tutti (tutti_peak 0.42).
  3. **Long single-texture middles** (about 10): JAUQ 24-45 (22 bars of clarinet / bassoon / viola), WBTS 71-138
     (68 bars on one repeated-eighth accompaniment), RHDT 63-90, YFQA 37-52 (thin and mezzo).
  4. **Themes without profile** (about 7): FUQW 4-11 (a scale fragment over sixteenth wallpaper), WBTS 7-22 (G-A-B-C),
     YFQA 7-14 (a three-note cell that never becomes a phrase), BLZF 30-41 (a bland second theme over pedals).
  5. **The dominant pedal has no bass and no drive** (about 6): YVCM 64-70 (5 lenses: violin scales over one held horn
     Eb, no bass, the motto not yet fragmenting), YFQA 67-74. And codas that sustain instead of transforming (YFQA
     87-99, ARFK 96-107).
- **Fixes for o12:**
  1. The development's frames work the motto: every dev block's material is a stage of the kernel (sequence,
     inversion, imitation, the head in the bass), no harp / pedal / sixteenth frame without the motto over it; a gate on
     dev_own.
  2. The summit gets the full tutti: trumpets and trombones on the motto's transformation at the peak, the violins'
     top at least a third over everything before; the reserve margin lowers the accompaniment, not the melody (folds
     1.54 -> back under 0.8).
  3. No texture holds longer than 8 bars in the middle: a fresh colour or density change (still_run, a hard tell).
  4. Themes with a profile: a leap and a rhythmic cell in the first two bars, no step-scale heads (a gate on the
     motto's contour).
  5. The dominant pedal in the bass (cellos / basses / timpani) under the motto's fragments, rising in density into the
     return; codas transform the motto instead of sustaining chords.

## Round o12: the development on the motto, the summit with brass and a top, no endless accompaniment, the drive into the return, themes with profile - PAIRED, o12 vs master (= o11) (2026-10-17)

The question: does the o12 code (master plus o11's `missing` sentences, commits b719752 + 31b5071) beat master
(fba10f4) on the same set plan, and how far is it from a masterpiece?

- The fixes are symphonic-only (piano genres and orchestra-film bit-identical, 24 of 24 hashes; the full
  `python tests/run.py` passed, 77 modules / 1652 tests). docs/ORCHESTRA_ENDLESS.md "Round o12" has the details:
  `DEV_LADDER['imitate']` (the head over I then V, answered a fourth under), motto episodes (`motto_brass` /
  `dialogue_brass` / `motto_bass`), `INNER_MOTION` 'floor' (no harp ostinato under C3), `DEV_BASS_RAW`, dev_own a hard
  score gate (0.8); `SUMMIT` / `_summit` (the violins I over every earlier line - the line or its closing units up the
  octave, the earlier phrases that reach it down whole -, the trumpets / trombones or the horns on the climax's
  melody, every role of the piece in the peak, the flutes an octave over it), RULES `reserve_lines` 1 (the margin
  lowers the accompaniment, not the tunes); `TEX_RUN` / `_vary_runs` (no accompaniment grid over 8 song bars);
  `RT_DRIVE` (the retransition's dominant re-struck in the basses / cellos / timpani); `MOTTO_CHARACTER['scale']` (no
  scale heads), `DANCE_FILL`; `CODA_RECALL['unit']` (the coda's motto every 2 bars, transformed); `UNFOLD_ALL` /
  `_refold`; `summit_stats` / `own_stats` in `SCORES['symphony']`; `tells_orch.py measure_o12`.
- Measured (`tells_orch.py`, 24 pieces, sets 96000 / 96100 / 96200, master / o12): dev_own 0.67 / 0.75; tutti at the
  peak 0.42 / 1.0; one_summit 0.42 / 1.0; the peak's violins over every earlier line 0.75 / 4.6 semitones (the
  climax's top over everything before 3.5 / 4.4, loudness margin 1.7 / 2.7 proxy LU); trumpets + trombones on a line
  at the peak 0.29 / 2.0; the longest unchanged accompaniment run 16.3 / 8.0 song bars; the dominant re-struck before
  the return 0.8 / 4.7 bars; folds 1.54 / 1.08; the motto's longest step run 1.75 / 1.21. Kept: seconds 225 / 225,
  dev_share 0.27 / 0.27, t1 / t2 home 1.0 / 1.0, recap_weight 1.07 / 1.07, V - I at the end 1.0 / 1.0, motto_ok 1.0.
- The round used one shared plan (`shared_plan.py`, seed 115000, `PLAN_115000.json`), best-of-4 per code, the main
  engine.
  - The slots: 1 river 6/8 E dorian; 2 allegro D minor, compact; 3 andante G major, fugal; 4 river 6/8 D major; 5
    allegro C major, through; 6 scherzo 3/4 F minor; 7 andante Ab major, ternary; 8 vivace 6/8 F major, compact
    (best-of-4 picked the same candidate in slots 3 and 5).
  - New: 0 gate rejects, 20 of 32 candidates capped by the dev_own gate (slots 2, 6, 8 kept a capped best: 39.1, 9.5,
    25.1). Old: 3 gate rejects (silent_notes, flat_dynamics x2). New pieces 189-349 s (mean 233 s), old 188-349 s
    (mean 238 s).
  - 16 packets plus the 3 hidden references through `deal o12 ... --panels 2 --split --orch`, 14 judges (staged in
    D:\tmp\o12\judges, verdicts as `<lens>_p<panel>.md`). The KEY is `KEY_orch_o12.json`. The 8 new mp3s (by packet
    ID), the KEY and SCORES.txt are in `songs/_endless_orchestra/out/blind_o12/` (main checkout).

| new - old (paired by lens across the panels, n 56) | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| raw mean | +0.45 | +0.46 | **+0.59** | +0.50 | +0.45 | **+0.61** | **+0.54** | +0.46 | +0.39 |
| won / tied / lost | 25/25/6 | 23/28/5 | 33/16/7 | 27/21/8 | 24/19/13 | 30/16/10 | 26/24/6 | 25/26/5 | 28/19/9 |

- Per slot (overall, raw / normalised): 001 +0.00 / +0.67 (LWLA vs QQUR, the E dorian river), 002 +1.71 / +1.05 (ZZGJ
  vs KHSM, the D minor allegro), 003 +0.29 / +0.95, 004 +0.71 / +0.05, 005 +0.86 / +1.52 (MBSQ vs AHQG, the C major
  allegro), 006 +0.14 / -0.52 (AYYZ vs KWYP, the scherzo), 007 +0.43 / +1.10, 008 +0.14 / -0.52.
  - Over the 8 slots: raw +0.54 (se 0.20), normalised +0.54 (se 0.27). Slots won / lost (raw): 7 / 0 (one tie).
  - By code (packet means): overall new 5.20, old 4.66, references 7.05; memorable new 1.88, old 1.41, references
    2.60.
- **Masterpiece (absolute, 1-10):** new **3.98**, old 3.59, references 5.74 (o11: new 4.23, old 3.89, references
  5.50 - another panel; the gap new - old +0.39 against o11's +0.34). Per packet: stormy RTST 6.29, scherzo MLXL 5.93,
  river SXKT 5.00, MBSQ (new-005) 4.71, ZZGJ (new-002) 4.43, AYYZ (new-006) 4.29; the new pieces 3.14-4.71, the old
  3.14-4.29.
- **The merge bar.** > 2 se: yes (+0.54 = 2.7 se). > +0.3 with at least 5 of 8 won: yes (7 won, 0 lost).
  **Recommendation: MERGE** (the third merge in a row after o10 / o11). Every dimension moved +0.39 to +0.61; life
  (+0.61) and orchestration (+0.45), flat in o11, moved most with form - the summit, the drive and the varied
  accompaniment were heard.
- **Template flags** per packet: new 50.3, old 46.6, references 13.7 (more flags per packet from every code than in
  o11 - this panel's statisticians and composers flagged more pairs).
- Best piece: new-005 MBSQ 'Stormy Fields' (C major allegro, through-composed, 3:09) at overall 5.86, masterpiece
  4.71 (`D:\tmp\o12\r\new\005-stormy-fields`, `blind_o12/MBSQ.mp3`); new-002 ZZGJ 'Fields of the Valley' ties it on
  overall (5.86, masterpiece 4.43). Worst: new-001 LWLA (the E dorian river) at 4.43, masterpiece 3.14.
- What the judges say is missing (the `missing` sentences of the 8 new pieces, 56):
  1. **The development repeats the whole motto instead of breaking it** (about 15): AYYZ 41-118 (6 of 7: "re-scored,
     never fragmented or put in canon"), ZZGJ 43-72 ("modulates through seven keys, always by repeating the whole
     motto"), YYPR 47-74 ("a fixed ladder"), DPQX 41-56 ("entries on one pitch level"), MBSQ 41-64 (runs that drop
     the turn).
  2. **The summit is one line doubled, not layers** (about 10): DPQX 75-86 ("one line in 7 roles, no counter-line or
     bass motion of its own"), YYPR 82-94 ("five octaves, no counter-line"), ZZGJ 82-96 (the motto in unison brass
     over held strings), QJFY 77-88, GFLP / LWLA (a countermelody and inner harmony wanted). The fullest tutti came
     as doublings.
  3. **Codas that fade or close plainly instead of the motto's last word** (about 12): DPQX 87-99 (a bare harp
     repeat), QJFY 96-108, MBSQ 84-102, ZZGJ 109-118 (a chorale where the motto should transform), YYPR 95-105, GFLP
     87-107 (two codas).
  4. **The second theme without profile, never meeting the motto** (about 8): GFLP 27-38, YYPR 33-46 (chordal, no
     melody), ZZGJ 31-38 (never returns), AYYZ 40-60, DPQX 57-74 (combine them before the pedal).
  5. **The climax states nothing heard before** (about 6): LWLA 82-93 (an E minor tutti peak at A6 with no theme),
     GFLP 75-86 and LWLA (the main theme wanted at the climax); the short / quiet dominant pedal (DPQX 67-74, QJFY
     66-73).
- **Fixes for o13:**
  1. The development's unit must break: after one whole statement, only the head / the kernel (the o11 ladder's
     later stages) - fragmentation, inversion, stretto at a beat, the motto against the second theme; the dialogues'
     2-bar statements of the whole motto capped at two (a gate on whole-motto repeats in the development).
  2. The summit in layers: the theme on top (violins + trumpets), a countermelody (horns / cellos, the second theme's
     head or the motto inverted), moving inner harmony and a bass line of its own - the fill roles join those layers,
     not a unison doubling.
  3. Codas transform the motto: augmented in the bass under the last cadence, or inverted and answered, over a real
     V - I; no harp-alone or chorale-only endings.
  4. The second theme with its own melody and rhythm (no chordal theme), returning home and combined with the motto
     once (the recap2 or the development's 'combine').
  5. The climax quotes the main theme (the river / journey layouts included) and the dominant drive lasts at least 8
     bars, crescendo; the river 'journey' development (dev_own 0.3-0.5 in its var blocks) needs the tune's cells.

## Round o14: CHROMA_CADENCE on vs off - the first STRICT paired round (best-of-1, the same composition seeds), 16 slots (2026-10-17)

The question: does the code review's A2 step 1 - the chromatic predominant (`CHROMA_CADENCE_ON`: It / Fr / Ger 6, N6,
vii°7/V, V7/V, V7/IV chosen by `harmonize()`, two chords a bar over the last 2 bars) before the return's dominant pedal
and before the final cadence - beat the same master code with the flag off? (o13 / o13b, on branch
worktree-agent-a682ef48f318d01f2, are not in master: master = o12 + the code review's infrastructure, 5a57ff5.)

- **The strict protocol** (the user after o13b: "the higher we get the more precise the tests, no lucky merges";
  o13b's pooled lean came mostly from slots where best-of-4 and the gate's rerolls picked different pieces):
  - ONE code, the flag only: new = `CHROMA_CADENCE_ON`, old = off (the worktree, both halves). One shared plan
    (`shared_plan.py plan ... 121000 16`, `PLAN_121000.json`), 16 slots.
  - Best-of-1: slot k renders composition seed 121000 + 10 (k - 1) in both codes (`D:\tmp\o14\one.py` calls
    `run.render_tune` with the slot's plan; no set memory between slots, `prev` None in both). A gate reject or
    compose error in EITHER code drops the attempt for both, then seed + 1 (`D:\tmp\o14\orchestrate.py`).
  - Dropped: 2 attempts, both slot 12. Seed 121110 crashed in BOTH codes (`_summit`: `max()` of an empty sequence, a
    violins I line that ends before the summit's last 2-bar units - a master bug, fixed below); 121111 was rejected in
    the new code only (flat_dynamics, the oboes' lead). Slot 12 compares seed 121112. 0 silent_notes rejects in 34
    renders: o13b's "one inaudible violins I / oboe note" rejects were o13's code, not master's - no fix needed.
  - Every slot's pair differs (34-830 packet lines; the added pedal bars shift some layouts: slots 4, 8, 14). Every new
    piece has a chromatic final approach, and the 12 major / minor pieces with a pedal retransition one before it:
    retransition Fr6 3, It6 4, vii°7/V 3, V7/V 1, N6 1; final approach V7/IV 5, N6 4, Ger6 3, V7/V 2, It6 1, Fr6 1 -
    none in the dorian retransitions (no chromatic vocabulary in a church mode).
  - 12 of 16 pieces are capped by a SYMPHONY_GATES miss in both codes (best-of-1 does not select), score mean 34.2 /
    34.1. Lengths 187-386 s (mean 221 s) in both.
  - 32 packets plus the 3 hidden references through `deal o14 ... --panels 2 --split --orch` (19 per judge), two
    panels of 7 judges (the o13 lenses), the masterpiece question. KEY `KEY_orch_o14.json`; all 32 mp3s (by packet
    ID), the KEY, SCORES.txt and SCORES_quality.txt in `songs/_endless_orchestra/out/blind_o14/` (main checkout);
    scripts, renders and verdicts in D:\tmp\o14.
- Before judging: the 24 protected hashes bit-identical (with the `_summit` fix), the full `python tests/run.py`
  passed (77 modules, 1657 tests).

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.06 | -0.01 | -0.04 | -0.01 | -0.09 | +0.02 | **-0.05** | -0.10 | +0.02 |
| se | 0.18 | 0.11 | 0.18 | 0.17 | 0.14 | 0.18 | 0.18 | 0.13 | 0.13 |
| slots won / lost | 7/6 | 8/6 | 7/7 | 7/8 | 6/6 | 7/8 | 7/8 | 7/7 | 10/6 |

- Per slot (overall, raw): 001 TADX / PATU -1.29, 002 JDPU / LSES +0.14, 003 SHKU / GTEA +1.14, 004 LDBS / EXUP +1.00,
  005 UABH / YVKE -0.14, 006 USWD / YJLD -0.71, 007 MWCW / VJCV -0.86, 008 EUJQ / BYUJ -0.29, 009 BUHR / ZTDU +0.14,
  010 GNLG / ANQS -0.57, 011 MVKB / ENWP +0.00, 012 CPKQ / PHVY +0.71, 013 UMZX / YACY -0.14, 014 ZVBD / NFAA -0.86,
  015 AUXF / XPXW +0.71, 016 WKCC / EXMH +0.14. Normalised -0.05 (se 0.27).
- Packet means (overall): on 4.71, off 4.76, references 6.50 (stormy 7.5, scherzo 6.4, river 5.6). Template flags per
  packet: on 68.6, off 68.2, references 28.3.
- **Masterpiece (absolute, 1-10):** on 3.50, off 3.48, references 5.17 (o13b: 3.70 / 3.44 / 5.21).
- **The merge bar** (overall > 2 se): -0.05 = -0.3 se. **DON'T MERGE - CHROMA_CADENCE stays off** (the default is not
  flipped). A clean null: no dimension moves by more than 0.8 se, harmony included (-0.01, se 0.11).
- **What the judges say about the cadences** (`D:\tmp\o14\cad.py`: every sentence on chromatic chords / cadences,
  161):
  - The retransition's chromatic predominant was not heard: no judge names one in any new piece. The pedals stay "the
    stock preparation" / "a formula" (AUXF 53-68: "the D pedal with timpani arrives with no harmonic surprise" - over
    a vii°7/V at bar 60), and the advice asks for exactly what was there: "a Neapolitan or augmented-sixth
    predominant, a delayed dominant" (composerA_p2), "a chromatic predominant before the arrival" (composerD_p1).
  - The final approach was named in 5 of 16 new pieces. Praised in 2: BUHR (N6 -> V7 in the brass coda, 104-108, by 5
    of 7 judges: "a well-placed chromatic cadence", "one good harmonic stroke") and UABH (103-106, "a nice touch" /
    "pretty but unearned"). A colour, not an idea, in 3: EUJQ ("the coda's Gb/Db mixture is a colour, not an idea"),
    UMZX ("good, but unconnected to the motto"), ZVBD ("the coda's chromatic chords wander").
  - The model is the stormy reference VRNU: its Neapolitan at bar 112 (a sudden Eb tutti chord before the last
    cadence) and its chromatic chord-block chain at 71-74 (Eb / C#dim / Bb / E7 into the A pedal) were praised by 10+
    judges as structural. Ours are two chords a bar for 2 bars in the voiced harmony under an unchanged texture and
    dynamic: correct voice-leading that nobody notices.
- Best piece: CPKQ (on, slot 12) 'Overture: Stormy Forests' (F minor allegro, fugal, 102 bars), overall 6.4 (above the
  scherzo and river references), masterpiece 5.00 (`D:\tmp\o14\r\new\012-overture-stormy-forests`,
  `blind_o14/CPKQ.mp3`); its off twin PHVY 5.7 / 4.43. The judges hear the same piece in both: the string fugato on
  the motto (52-63) and the stock C pedal (64-71).
- What is missing (the 112 `missing` sentences of the new pieces; the same list for both codes):
  - the climax restated louder / in unison doublings, no transformation or counter-line (about 38: TADX, SHKU, LSES,
    EUJQ, CPKQ);
  - the development transposing or sequencing without changing the material, thin placeholder textures (a lone violin
    line over a timpani pedal: MWCW, GNLG, WKCC; about 38);
  - the shared plan, quiet -> pedal + timpani -> major tutti -> harp / brass coda (about 20 "pedal / formula / stock");
  - codas that fade without the motto's last word (about 22);
  - themes without profile (triad-arpeggio mottos, second themes as stepwise filler).
- **Fixes for o15** (one flag per round, the strict protocol):
  1. The chromatic chord as an EVENT, at the structural cadence only: tutti / brass, accented and held (a fermata or a
     ritardando into it), the bass on the chromatic step (b6 -> 5, b2 -> 1), the texture changing under it - not two
     quiet inner-voice bars. Before the return: a chromatic chord-block chain (VRNU 71-74) or a deceptive move instead
     of the plain pedal frame.
  2. The summit transforms the theme (o13's fix 1: augmentation in the brass bass, against the second theme, at most
     two doublings of the top) - o13's code on the strict protocol.
  3. No lone line over a pedal as a build: the retransition's line from the development's material, in two parts.
  4. The 12-of-16 hard-gate caps under best-of-1: the gates are assertions now, so a capped piece is a construction
     bug to find, not a ranking signal.

The `_summit` fix (`symphony.py`): a violins I line too high to rise whole, whose last 2-bar units should rise, read
`max()` over its notes after the cut - empty when the line ends earlier in the peak block: a ValueError that a normal
`endless` run does not catch (it stops the run). Now `default=-99`: nothing rises. Bit-identical wherever it did not
crash (24 of 24 protected hashes; the 32 o14 renders).

## Round o15b: CHROMA_EVENT on vs off - the chromatic chord as an event, strict paired, 16 slots (2026-10-18)

The question: does o14's fix 1 (the chromatic chord as an EVENT, at the structural points only) beat the same master
code with the flag off? The comparison code is 909891f plus this round's gate fixes. o15a, o13's fixes on the strict
protocol, ran in parallel in another worktree.

- **CHROMA_EVENT** (`symphony.py`, off; `CHROMA_EVENT_ON` = {'final', 'recap', 'level' ff, 'soft' f, 'hold' 2.0,
  'chain' 4, 'chain_level' f, 'chain_top' ff}):
  - The final cadence: the bar before the last V - I becomes ONE chromatic predominant, with the bass on b2 / b6.
    `EVENT_FINAL` picks N6 or Fr6 before V, and Ger6 / N6 before the cadential six-four. It is voiced by
    `_event_voice`, a DP chorale voicer:
    - complete chords; the fifth is optional on the triads / sevenths of `EVENT_FIFTH`;
    - tendency tones move by step;
    - no doubled tendency tone or leading tone;
    - no parallels, the bass included.

    The melody's top is kept. The chord is a held tutti: brass, then strings, then winds (`EVENT_ROLES`), and
    `_event_tutti` cuts the other non-melody parts in the span. It is struck sf at ff with a fermata (hold 2.0), then
    V(7) - I at f.
  - Before the return: a 4-chord chain on half-bar slots in the internal bars before the dominant pedal, arriving on V
    (`Writer._event_rt`; `EVENT_CHAINS`: descent / deceptive / ascent / neapolitan). It uses the same voiced tutti,
    rising from f to ff. The chart, bass line and melody tops are rebuilt in the span. There is no chain in the 'bass'
    builds, which have no pedal frame.
  - The tutti never outnumbers or tops the summit: the role count is capped at the peak's, and the pitch at the peak
    top - 2 before the peak. Without the cap top_peak / tutti_peak fail.
  - Every new piece got its final event (N6 11, Fr6 4, Ger6 1), and the 12 non-'bass' pieces a chain (neapolitan 6,
    deceptive 3, ascent 2, descent 1). 0 voicing failures and 0 parallels in 32 composes.
- **The protocol** (o14's):
  - One code, the flag only: `shared_plan.py --flag event` for new. Plan `PLAN_125000.json`, 16 slots, best-of-1 on
    seed 125000 + 10 (k - 1) in both codes.
  - A reject in either code drops the attempt for both. Dropped: 1 attempt, slot 2's seed 125010 (the new half was
    rejected by flat_dynamics, the oboes' lead). Slot 2 compares seed 125011.
  - Judging: two panels of 7 (the o14 lenses and JUDGE.md), the 3 hidden references and the masterpiece question.
  - Files: KEY `KEY_orch_o15b.json`. The 32 mp3s (by packet ID), the KEY, SCORES.txt and SCORES_quality.txt are in
    `songs/_endless_orchestra/out/blind_o15b/` (main checkout). Scripts, renders and verdicts are in D:\tmp\o15b.
- Checks before judging:
  - the 24 protected hashes are bit-identical;
  - with the flag off, the code equals the gate-fixed code on 40 of 40 test pieces;
  - the full `python tests/run.py` passed (77 modules, 1660 tests).

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.15 | +0.17 | -0.16 | -0.16 | +0.03 | -0.29 | **-0.12** | -0.04 | -0.03 |
| se | 0.15 | 0.14 | 0.17 | 0.21 | 0.16 | 0.20 | 0.16 | 0.10 | 0.15 |
| slots won / lost | 7/8 | 8/5 | 7/8 | 7/8 | 7/6 | 5/8 | 5/8 | 7/8 | 7/8 |

- Per slot (overall, raw), new / old:

  | Slot | Pair | Overall |
  |---|---|---|
  | 001 | RSVN / CMUM | -0.29 |
  | 002 | YYKU / ZVVG | +0.57 |
  | 003 | VMZR / ZDVX | -0.43 |
  | 004 | QHTU / JGKR | +0.00 |
  | 005 | JRAD / HYBM | -0.43 |
  | 006 | ATBQ / QQXX | +0.00 |
  | 007 | QJRL / DKLQ | -0.57 |
  | 008 | HWEU / GHKT | -0.29 |
  | 009 | RMDA / FTUL | -0.86 |
  | 010 | KHRW / SFZN | +1.00 |
  | 011 | MAPR / DXUD | -1.00 |
  | 012 | AWTK / WBJN | +0.57 |
  | 013 | BKEH / XZRB | +0.86 |
  | 014 | JWSV / TDRS | +0.14 |
  | 015 | VQAA / SLRV | +0.00 |
  | 016 | CSXA / AVJP | -1.14 |

  Normalised: -0.12 (se 0.15).
- Packet means (overall): on 4.75, off 4.87, references 7.21 (stormy 7.5, river 7.3, scherzo 6.9).
- **Masterpiece (absolute, 1-10):** on 3.52, off 3.54, references 5.67.
- **The merge bar** (overall > 2 se): -0.12 = -0.7 se. **DON'T MERGE - CHROMA_EVENT stays off.** Harmony leans up
  (+0.17, 1.3 se, 8 won / 5 lost) and life down (-0.29, 1.5 se): the events are heard, and heard as a formula.
- **What the judges say about the cadences** (`D:\tmp\o15b\cad.py`: 278 sentences, 33 of them ADVICE lines, from all 14
  judges):
  - Unlike o14's, the events were HEARD. Every judge names the chain and the final cadence by bar and chord ("a brass
    chorale on Eb, then C# diminished, then Bb, then E, into the A pedal" - VMZR 60-63).
  - Single events were praised:
    - RSVN's Ger6 / It6 close: "a strong final cadence", "earned more than in its siblings";
    - HWEU's Ger6 chorale: "has weight", "a good chord thrown away inside a formula";
    - BKEH's Neapolitan march: "nice", "well-placed".
  - Across the set they are a template. Every lens's ADVICE asks to retire "the stock brass chorale before the
    retransition" and "the formula codas: Neapolitan or augmented sixth, then V, then I". The template flags per
    packet rose to 66.9 (old 42.8, references 26.0). The fixed slots make it worse: the chain is ALWAYS at the pedal,
    the event ALWAYS in the last 4 bars, and both use the same held-tutti block texture.
  - The neapolitan chain was modelled on the stormy reference's bars 71-74 (Eb / C#dim / Bb / E7). In D minor / major
    (VMZR, JRAD) it is that chain chord for chord, so the judges hear the reference GPYE and our pieces as one family:
    "The chord sequences match JRAD chord for chord at the retransition and at the cadence."
  - What they want instead:
    - the chromatic chord PREPARED from earlier material, or inside the theme's own rhythm (GPYE bars 74-82; its
      Neapolitan at 112 "feels earned rather than inserted");
    - voice-led from a moving line, not struck as blocks bar by bar;
    - the route to the climax and the ending varied per piece: a deceptive turn, a silence, a key shock, no pedal, a
      plagal or quiet close;
    - no lone timpani stroke on the last bar (present in both codes).
  - By chain (overall, raw; small n):

    | Chain | Pieces | Overall |
    |---|---|---|
    | deceptive | 3 | +0.24 |
    | ascent | 2 | +0.29 |
    | neapolitan | 6 | -0.10 |
    | descent | 1 | -1.14 |
    | none ('bass' builds) | 4 | -0.36 |
- Best piece: AWTK (on, slot 12) 'Burning Mountains of the Storm', overall 5.6
  (`D:\tmp\o15b\r\new\012-burning-mountains-of-the-storm`, `blind_o15b/AWTK.mp3`). It is in D minor, with the deceptive
  chain A7 - Bb - Bb7b5 - A at bar 70 and the N6 final at 103. Its off twin WBJN scored 5.0. The largest win is KHRW
  (slot 10, the deceptive chain) +1.00; the largest loss is CSXA (slot 16, the descent chain) -1.14.
- **Fixes for o16** (one flag per round):
  1. If the event idea returns, at most ONE event per piece: a draw among the retransition, the final cadence or none.
     Prepare it with the chromatic step in the bass or the melody in the bars before (the motto's own interval), and
     with the texture moving into it, not a block chorale. Copy no chain from a reference.
  2. Vary the endings per piece: a draw over plagal / deceptive-then-V-I / quiet / the motto's last word. Drop the
     lone timpani stroke on the last bar.
  3. o14's fixes 2-3 (the summit transforms the theme; no lone line over a pedal) stay the open composition work.

**The gate fixes** (this round; flag-independent; bit-identical wherever no gate failed). The o14 slots' hard-gate
misses, 12 of 16 slots capped:

| Gate | Misses | Where / what |
|---|---|---|
| dev_own | 9 | |
| acc_run | 4 | slots 4, 7, 10, 13: runs of 10-12 bars |
| seq_links | 3 | slots 6, 9, 11: a fugato counter-subject oscillating a semitone for up to 9 links; a dialogue ladder |
| seconds | 1 | slot 7: 179.4 s |
| tutti_peak | 1 | slot 15: a harp variation |

Fixed:
- acc_run: `_vary_runs` has a new repair pass (`TEX_RUN['repair']`). It recounts the runs with `acc_runs`' own block
  index, then thins every bar after the 8th of a run that is still over 8 bars, using that run's grid
  (`_thin_bar(exact=True)`).
- seq_links: `SEQ_BREAK` / `_break_links`. In the development blocks, the unit that would make the 3rd sequential link
  ties its last note into the one before. `_seq_units` / `_seq_same` are factored out of `_seq_links`.
- seconds: `MIN_LEN['more']` (t1 12, t2 14, recap 14, recap2 14 bars) applies when 'grow' stalls, with the slow intro
  counted.
- tutti_peak: `summit_stats` no longer counts harp / percussion as a tutti role (`TUTTI_SKIP`).

Results:
- 26 of the 40 o14 + test pieces are bit-identical. Every changed piece had failed a gate, except one capped by
  dev_own whose 'more' lengthened it (195 -> 209 s).
- In o15b's plan, 11 of 16 slots are still capped, the same set in both codes:
  - dev_own 9: a quality gate, not a construction bug;
  - seconds 1: slot 2, 171.7 s, still short after 'more';
  - pre_semis + vln_over 1: slot 14.
- acc_run, seq_links and tutti_peak now miss 0.

## Round o16: DEV_WALK on vs off - the derivation engine (the code review's A1), strict paired, 16 slots (2026-10-18)

The first ARCHITECTURE round. The question: does the development as a planned walk over a motivic derivation graph
beat the same master code (b81e3d3) with the flag off? docs/ORCHESTRA_ENDLESS.md "Round o16: the derivation engine"
describes the engine.

- **The engine**:
  - Step 1 (bit-identical): `motto_notes` is `Kernel.motto(m).apply(...)`, and every statement logs a derivation node
    `{node, parent, ops, depth, src}`.
  - Step 2: `DEV_WALK` (off; `DEV_WALK_ON` = {'split', 'recall', 'graph'}).
    - The dev_dialogue blocks become 1-3 phases, each a block with its own texture: call / imitate / against / bass /
      false.
    - Each phase is made of segments: a 1-4 bar model, sequenced 1-3 times (up / down / fifths / thirds / real),
      with plain or applied-dominant links. Each segment arrives in the next key (pac / hc / deceptive / chroma).
    - Each segment's unit is an op chain on the motto K1 or the second theme's K2, from `DERIVE_OPS`, with depth
      rising from 1 to 4.
    - recap2 and the coda recall one counter-line derived in the development.
    - The score uses `derive_stats` (dev_ops / dev_depth / dev_literal) instead of the dev_own gate. tells_orch is
      untouched.
- **The protocol** (o14's):
  - One code, the flag only: `shared_plan.py --flag derive` for new.
  - Plan `PLAN_127000.json`, 16 slots, best-of-1 on seed 127000 + 10 (k - 1) in both codes.
  - A reject in either code drops the attempt for both. Dropped: 1 attempt, slot 5's seed 127040 (the old half was
    rejected by silent_notes, one violas note). Slot 5 compares seed 127041.
  - Judging: two panels of 7 (the o14 lenses and JUDGE.md), the 3 hidden references and the masterpiece question.
  - Files: KEY `KEY_orch_o16.json`. The 32 mp3s (by packet ID), the KEY, SCORES.txt and SCORES_quality.txt are in
    `songs/_endless_orchestra/out/blind_o16/` (main checkout). Scripts, renders and verdicts are in D:\tmp\o16.
- Checks before judging:
  - the 24 protected hashes are bit-identical;
  - with the flag off, the code equals master on 40 of 40 orchestra-symphonic test pieces;
  - 48 composes with the flag on raised no errors;
  - the full `python tests/run.py` passed (77 modules, 1664 tests).
- Route diversity over the 16 slots, on / off (`D:\tmp\o16\route_div.py`):

  | Measure | On | Off |
  |---|---|---|
  | Mean pairwise Jaccard distance of the route tokens | 0.605 | 0.285 |
  | Distinct segment kinds | 110 of 110 | 23 of 140 |
  | Distinct tokens | 92 | 23 |
  | Distinct phase / technique orders | 15 of 16 | 10 of 16 |
  | Distinct route signatures | 16 of 16 | 14 of 16 |

- Hard-gate caps:
  - on: 2 of 16 slots (slot 6: top_peak / pre_semis / vln_over; slot 7: dev_ops 5);
  - off: 8 of 16 slots (dev_own 7, slot 6 top_peak / pre_semis).

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.26 | -0.28 | -0.39 | -0.27 | -0.15 | -0.14 | **-0.28** | -0.10 | -0.18 |
| se | 0.14 | 0.17 | 0.21 | 0.21 | 0.16 | 0.16 | 0.19 | 0.08 | 0.11 |
| slots won / lost | 5/10 | 5/8 | 3/10 | 5/9 | 5/10 | 4/9 | 5/9 | 5/7 | 5/10 |

- Per slot (overall, raw), new / old:

  | Slot | Pair | Overall |
  |---|---|---|
  | 001 | BGGM / RYXH | -0.43 |
  | 002 | BQNN / WUEE | -0.14 |
  | 003 | UASB / SDCH | -1.71 |
  | 004 | ZTVA / HBSC | -0.29 |
  | 005 | DDYG / JEML | -1.14 |
  | 006 | XJFD / YGYR | +0.43 |
  | 007 | AJTS / XPVX | +0.00 |
  | 008 | SCGY / PBRY | -0.43 |
  | 009 | BJTJ / MJJS | +1.14 |
  | 010 | ZFMW / NTLK | -0.71 |
  | 011 | PXWY / SRUX | +0.14 |
  | 012 | UJUY / DGFB | +0.57 |
  | 013 | UZNZ / AHXN | -1.43 |
  | 014 | TSJS / YVQV | +0.00 |
  | 015 | TUTC / RYPF | -0.57 |
  | 016 | LSBM / NPAS | +0.14 |

  Normalised: -0.28 (se 0.33).
- Packet means (overall): on 4.68, off 4.96, references 6.67 (stormy 7.2, scherzo 6.9, river 5.9).
- **Masterpiece (absolute, 1-10):** on 3.54, off 3.71, references 5.05.
- Template flags per packet: on 45.0, off 45.8, references 14.7. Both codes share the same plan-level templates: the
  6/8 family (a running violins2 intro, the theme over harp, fugato, timpani pedal, a major tutti, a harp coda) and
  the short-short-long motto family (pedal-timpani retransition, stepwise brass climax).
- **The merge bar** (overall > 2 se): -0.28 = -1.5 se. **DON'T MERGE - DEV_WALK stays off.** Every dimension leans
  down; form most (-0.39, 3 won / 10 lost).
- **What the judges say about the development** (`D:\tmp\o16\dev.py`, `devcount.py`; the sentences in the packets,
  on / off / references):

  | Tell | On | Off | References |
  |---|---|---|---|
  | panels, switching, patchwork, fragmentary, never settles | 29 | 6 | 0 |
  | unrelated material, no motivic link, filler | 16 | 6 | 3 |
  | loop, ostinato, static | 31 | 23 | 3 |
  | fugato, imitation, canon, stretto | 33 | 56 | 12 |
  | inversion, combination, augmentation | 20 | 29 | 5 |
  | false entry | 0 | 0 | 0 |

  - The phase split is the main loss. Each phase is its own block, with its own texture and dynamic, so the
    development becomes 4-6 bar panels. The judges hear channel-switching, not an argument:
    - "five sections of 4-6 bars each (S6-S10) chop the development into a mosaic" (TSJS);
    - "fragmentary, with sixteen sections, no line and no arc" (UASB);
    - "four 5-bar sections in a row; the music never settles" (DDYG);
    - composerD's ADVICE: "Sections shorter than 8 bars, each with a new colour, read as channel-switching, not as
      development."
  - The deep op chains (depth 3-4: liquidate / expand / combine / displace stacked) lose the motto's identity. The
    on developments are heard as "six small sections, each a different texture, with no motivic link" (UZNZ) and
    "the episodes are unrelated textures" (UASB).
  - Every lens's ADVICE asks for the opposite: one idea WORKED over a longer span, so that the motto is fragmented,
    sequenced and recoloured (AHXN and JEML, both off, and the reference ZNZP are the models named).
  - Old's imitation / fugato was named more, and its unfinished ones were faulted: "when a fugato starts, finish it"
    (composerA_p2: bring in all the voices, stretto, drive it into the pedal). The walk's 'imitate' and 'call'
    phases are too short to be heard as one.
  - The false entries and the recalled counter-lines in recap2 / coda went unnamed.
  - The walk's diversity was real (route Jaccard 0.61 vs 0.29) but was not heard as quality. Diversity inside a
    piece read as incoherence. The set-level templates the judges flag sit outside the development.
  - Positive: XJFD (on, slot 6) - "the E-E-A-C# head motive enters in imitation ... a small fugato that gives the
    retransition real energy"; BJTJ (slot 9, +1.14) won with 5 lenses, tied 1, lost 1.
- Best piece: JEML (off, slot 5, seed 127041) 'Overture: Hidden Fields', overall 6.4, above the river reference
  (`D:\tmp\o16\r\old\005-overture-hidden-fields`, `blind_o16/JEML.mp3`). Its on twin DDYG scored 5.3.
  - The best on piece: XJFD (slot 6) 'Toward Summer' 5.7 (`D:\tmp\o16\r\new\006-toward-summer`).
  - The largest win: BJTJ (slot 9) +1.14. The largest loss: UASB (slot 3) -1.71.
- **Fixes for the next derive round** (the engine stays; the flag off):
  1. No phase split: the walk stays ONE block with one texture family (`DEV_WALK['split']` False). The phases are
     levels and orchestration changes inside it, never a new block under 8 bars.
  2. Keep the motto audible:
     - cap the op depth at 2, so every unit keeps the head's rhythm or its intervals;
     - stack at most one interval op (expand / contract / liquidate);
     - fill a model's rest with rests or a held pad, not inner derivations (`_fill`).
  3. One worked process per phase, at least 8-12 bars: a sequence that runs 3 models toward a goal, an imitation that
     tightens into stretto and drives into the pedal (old's fugato, finished).
  4. A false entry needs its frame: a silence or thinning before it, then a tutti break-off. Otherwise drop it.
  5. Set level (both codes): the 6/8 and short-short-long plan templates, and the stepwise one-bar summit sequence,
     are the shared tells (template flags 45 vs references 15).

## Round o17: DEV_WALK v2 on vs off - one development block of worked processes, strict paired, 16 slots (2026-10-18)

The second derivation-engine round. The question: does v2 of the walk (o16's fixes) beat the same master code
(23eb82d + v2, flag off = master) with the flag off? docs/ORCHESTRA_ENDLESS.md "Round o17" describes v2.

- **v2** (`DEV_WALK_ON = {'v2', 'recall', 'graph'}`; o16's walk is `DEV_WALK_V1`; `Writer.walk2`, `WALK2`):
  - no new blocks: the layout's dev_dialogue blocks stay whole, each 1-3 PROCESSES of 8-12 song bars, one texture
    family per block (`walk_dialogue` / `walk_poly`: a doubling enters at the block's middle - the colour grows at a
    phrase boundary, never switches);
  - each process one worked gesture with a goal: `sequence` (the unit 2-3 times, its answer half / a quarter / an
    eighth of a model late, then head and kernel in the two lines into the arrival), `stretto` (exposition, overlap
    at half the subject, the head, the kernel half a bar apart, each pair a step higher; preferred as the
    development's last process, into the pedal), `against` (the unit over the second theme's augmented head), `bass`;
    every process rises 7 semitones and climbs in level (p / mp to f) and arrives in the next key (pac / chroma /
    hc / deceptive; the last in the home key);
  - op depth <= 2 in every statement, one interval op at most (expand / contract), no retro / liquidate / combine;
    a statement's rest is its last note held 2 beats, then rests;
  - false entries only after a thinning (the arrival before breaks off, the level drops to p);
  - route diversity drawn per piece (process kinds and order, keys along the piece's path, K2 sequences and the
    `against` combination).
- **The protocol** (o14's / o16's): one code, the flag only (`shared_plan.py --flag derive`); plan `PLAN_129000.json`
  (16 slots, drawn by master), best-of-1 on seed 129000 + 10 (k - 1) in both codes; a reject in either code drops
  the attempt for both. Dropped: 3 attempts, all slot 11 (129100-129102: the new half rejected by silent_notes -
  flutes / violins I / cellos notes 51-56 dB under their tracks); slot 11 compares seed 129103. Two panels of 7 (the
  o14 lenses, JUDGE.md), the pair halves in different panels (`deal --split`), the 3 hidden references, the
  masterpiece question. KEY `KEY_orch_o17.json`; the 32 mp3s (by packet ID), the KEY, SCORES.txt and
  SCORES_quality.txt in `songs/_endless_orchestra/out/blind_o17/` (main checkout); scripts, renders and verdicts in
  D:\tmp\o17.
  - A first deal went out without `--split` (both halves of a slot with the same judges): new - old -0.13 (se
    0.08), 4 slots won / 8 lost, 55 of 112 lens pairs tied (`blind_o17/SCORES_samejudges_firstdeal.txt`). It was
    redealt with `--split` (o16's protocol) and judged by 14 fresh judges before its result was read against the
    merge bar; the split round below is the round. Both say the same.
- Checks before judging: the 24 protected hashes bit-identical; flag off = master on 40 of 40 orchestra-symphonic
  pieces (o14's 16 slots, o15b's 16, 8 set pieces); 32 composes with the flag on without errors; the full
  `python tests/run.py` passed (77 modules, 1665 tests).
- Route diversity over the 16 slots, on / off (`D:\tmp\o17\route_div.py`, o16's measure; one route entry per process
  now, per segment in o16):

  | Measure | On (v2) | Off | o16 on (v1) |
  |---|---|---|---|
  | Mean pairwise Jaccard distance of the route tokens | 0.611 | 0.288 | 0.605 |
  | Distinct route signatures | 16 of 16 | 16 of 16 | 16 of 16 |
  | Distinct phase / technique orders | 13 of 16 | 12 of 16 | 15 of 16 |
  | Distinct tokens | 49 | 23 | 92 |

- Hard-gate caps (the judged seeds): on 0 of 16; off 7 of 16 (dev_own).

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.07 | +0.12 | -0.21 | -0.06 | -0.03 | -0.24 | **-0.14** | -0.08 | -0.10 |
| se | 0.18 | 0.12 | 0.17 | 0.21 | 0.10 | 0.18 | 0.20 | 0.13 | 0.17 |
| slots won / lost | 8/5 | 7/4 | 6/9 | 10/6 | 6/6 | 6/9 | 8/7 | 6/7 | 7/7 |

- Per slot (overall, raw), new / old: 001 FTLJ / KAWY +0.29, 002 CBDE / QKNP +0.29, 003 HGHD / HHQN +0.86,
  004 VNLM / HUDC -1.71, 005 JDWF / QNLX -0.14, 006 PKHQ / RKAZ +0.00, 007 WKHZ / QFPR -0.43, 008 ZQYZ / SAMY +0.29,
  009 QFCP / DHTC +0.14, 010 LBGE / PMFF +0.86, 011 NNDY / NKVD -1.14, 012 ZRNR / VAZA -0.43, 013 WTGA / SHZH +0.14,
  014 AVPD / MAYP +1.00, 015 SZMP / ANEY -0.86, 016 GZSB / XECL -1.43. Normalised -0.14 (se 0.21).
- Packet means (overall): on 4.86, off 5.00, references 7.07 (stormy 7.9, scherzo 6.9, river 6.4).
- **Masterpiece (absolute, 1-10):** on 3.40, off 3.50, references 5.48.
- Template flags per packet: on 51.4, off 52.3, references 7.0 (the shared 6/8 plan, the dominant-pedal build with
  timpani quavers, the unison climax, the harp coda - set-level, both codes).
- **The merge bar** (overall > 2 se): -0.14 = -0.7 se. **DON'T MERGE - DEV_WALK stays off.** A smaller loss than
  o16 (-0.28, 5 won / 9 lost): won / lost is even (8 / 7), harmony leans up (+0.12, 7 / 4), development is even
  (10 won / 6 lost, -0.06); form and life lean down (-0.21 / -0.24, 6 / 9 each).
- **What the judges say about the development** (`D:\tmp\o17\devcount.py`, o16's patterns + sequence-to-goal; the
  sentences per packet, on / off / references):

  | Tell | On | Off | References | o16 on / off |
  |---|---|---|---|---|
  | panels, switching, patchwork, fragmentary, never settles | 23 | 11 | 1 | 29 / 6 |
  | unrelated material, no motivic link, filler | 12 | 10 | 4 | 16 / 6 |
  | loop, ostinato, static | 30 | 27 | 6 | 31 / 23 |
  | sequence to a goal (arrives, drives into the pedal / cadence) | 1 | 2 | 0 | - |
  | fugato, imitation, canon, stretto | 12 | 30 | 14 | 33 / 56 |
  | inversion, combination, augmentation | 13 | 15 | 3 | 20 / 29 |
  | modulation, new key | 21 | 11 | 5 | - |
  | false entry | 0 | 0 | 0 | 0 / 0 |

  - "Unrelated material" is level now (12 / 10): the depth cap keeps the motto audible.
  - The panels stay ahead (23 / 11), but they are KEY panels now, not texture panels: "the theme set in one new key
    after another with no preparation ... drop one or two of the key panels" (FTLJ), "the sudden Ab/Eb flat-side
    panel arrives with no preparation" (QFCP), "a string of key panels (Ab, a B/Db wander, semiquavers in Ab)".
    Every process arrives in a new key, so a 16-bar block is two keys and a piece of two dev blocks four - with a
    chromatic arrival often the jolt (modulation 21 / 11).
  - The worked processes were not heard as goal-directed (sequence-to-goal 1 / 2); v2's stretto was never named
    (all 12 imitation sentences on new are the layout's dev_fugato, which both codes have - old's 30 add its
    dev_dialogue's head imitation).
  - The losses are the slow pieces: "the most static development of the 4/4 group (b40-55)", "bars 40-55 stand
    still", S6 strings only, S7 a solo line (VNLM, -1.71); "bars 61-76 recycle the same cell", "obsessive repetition"
    (GZSB andante, 76 BPM, -1.43). At a slow tempo the held-then-rest models and the head / kernel drive read as one
    cell hammered over a thin texture.
  - The false entries were unnamed again.
- Best piece: HUDC (old, slot 4, seed 129030) 'Symphonic Dance: Riders of the Storm', overall 6.1, masterpiece 4.4
  ("a real fugato (bars 40-55)", `D:\tmp\o17\r\old\004-symphonic-dance-riders-of-the-storm`, `blind_o17/HUDC.mp3`);
  its on twin VNLM 4.6. The best on piece: AVPD (slot 14, seed 129130) 'Fields of the Sea' 6.0, masterpiece 4.4,
  the largest win (+1.00: "the motto in 7 of 9 sections, transposed and sequenced", "pays off in augmentation at
  bar 59"; `D:\tmp\o17\r\new\014-fields-of-the-sea`, `blind_o17/AVPD.mp3`). The largest loss: VNLM (slot 4) -1.71.
- **Fixes for the next derive round** (the engine stays; the flag off):
  1. One key per block, or a prepared modulation: a process modulates by its sequence (the real sequence, the
     applied links) and arrives in a key the block's path prepares (pivot chord / the dominant), not by a chromatic
     jolt at each 8-bar boundary; at most one new key per dev block.
  2. Slow tempi: the process length by time, not bars (an andante process of 8 bars is 25 s); keep the line moving
     through the model's rest at slow tempi (the answer overlapping from the first model, an inner voice) instead of
     the held note and rests; no head / kernel drive longer than 2 bars.
  3. Make the stretto heard as one: more voices (3-4 entries over the strings, violas / cellos), the subject in the
     bass at the end, and the drive into the retransition's pedal continuous (no arrival cadence before it).
  4. The silent_notes rejects (slot 11, 3 of 4 seeds on the new code): the walk_dialogue flute doubling / thin
     orchestration at p - check the doubling's level against its line before the gate.
  5. Set level (both codes): the 6/8 plan, the timpani-quaver dominant pedal build, the unison climax and the harp
     coda carry the template flags (51 vs references 7).

## Round o18a: DEV_WALK v3 on vs off - one key per development block, processes by time, a four-voice stretto, strict paired, 16 slots (2026-10-18)

The third derivation-engine round (o17's fixes 1-4; round o18b, in parallel, works on the set-level plan
templates). The question: does v3 of the walk beat the same master code (f3cf603 + v3, flag off = master) with the
flag off? docs/ORCHESTRA_ENDLESS.md "Round o18a" describes v3.

- **v3** (`DEV_WALK_ON = {'v3', 'recall', 'graph'}`; o17's walk is `DEV_WALK_V2`, o16's `DEV_WALK_V1`;
  `Writer.walk3`, `WALK3`):
  1. Keys: every development block is in ONE key (its path's j-th for the j-th dialogue), or makes ONE prepared
     modulation into the next block's key (`_next_area`: the next dialogue's, the fugato's, the false
     recapitulation's). The modulation comes at a process boundary (`mid` 0.4) or in the block's last arrival: a
     pivot chord diatonic in both keys before the new V7 (`_pivot`), or the new key's V7 held a bar. In-key arrivals
     are mostly elided or half cadences (`arrive`). No `mode` op (a key change in disguise), no real sequence, no
     false entry.
  2. Time: the processes are sized by seconds (`secs` 17), so an andante block holds more, shorter processes than an
     allegro block. At slow tempi (an internal bar of 2.7 s or more) the models are one bar long, the answer comes a
     quarter model late, and a rest of 1 s or more is bridged by the kernel. A held note lasts 1.2 s at most. The
     head / kernel drive is 2 bars / 6.5 s at most.
  3. The stretto: four voices - the melody, the counter, the tenor (the harmony's top voice, violas) and the bass
     (cellos + basses arco). The exposition comes a subject apart (or half), the later entries half a subject apart,
     then the head in turn, the bass last. No voice drops out once it has entered (kernel inverted / fragment /
     head contracted toward its next entry). Texture `walk_stretto`. Before the retransition the last process
     drives on (`drive`): the kernel in both lines each half bar and the bass on the pivot and the home key's
     dominant, with no cadence and no landing (stretto weight x3 there).
  4. silent_notes: o17's slot-11 rejects were not the doubling's level. They were the unit DIMINISHED into 32nds
     (0.125 beats: `_fit_ops` appends 'diminish' when even the kernel outlasts its room), played at velocity 14-23,
     at a model's end (seeds 129100-129102: violins I / flutes / cellos). v3's `_fit3` never diminishes (it cuts
     instead), `diminish` is not drawn, and no walk note is shorter than a 16th / 0.12 s (`min_beat`, `min_s`).
     Also, the flute doubling is gone from the walk's textures. `walk_dialogue3` doubles the call with the oboes in
     unison and `walk_stretto` with the violins II, because a flute an octave over a low call at p was a near-silent
     track on a trial seed.
  - One level ramp per block (p / mp to f) instead of one per process. Route diversity drawn per piece as in v2
    (process kinds and order, the arrival, the move, the K2 unit).
- **The protocol** (o14's / o16's / o17's split deal):
  - One code, the flag only: `shared_plan.py --flag derive`.
  - Plan `PLAN_131000.json`, 16 slots drawn by master; best-of-1 on seed 131000 + 10 (k - 1) in both codes.
  - A reject in either code drops the attempt for both. Dropped: 1 attempt, slot 2 seed 131010. The new half was
    rejected by silent_node: the flutes lead the retransition's pulse_build, but their part plays no note - a
    role-pick consequence in shared code, not a walk note. Slot 2 compares seed 131011.
  - No silent_notes reject on the flag (o17: 3).
  - Two panels of 7 (the o14 lenses, JUDGE.md). Each slot's two halves go to different panels (`deal --split`). The
    3 hidden references and the masterpiece question.
  - Files: KEY `KEY_orch_o18a.json`. The 32 mp3s (by packet ID), the KEY, SCORES.txt and SCORES_quality.txt are in
    `songs/_endless_orchestra/out/blind_o18a/` (main checkout). Scripts, renders and verdicts are in D:\tmp\o18a.
- Checks before judging:
  - the 24 protected hashes are bit-identical;
  - with the flag off, the code equals master on 40 of 40 orchestra-symphonic pieces (o14's 16 slots, o15b's 16,
    8 set pieces);
  - `DevWalk.test_v3_one_key_time_sized_stretto`: one key or one move per block, prepared into the next block's key,
    'drive' into the retransition, the drive cap, no sub-16th notes, the entries in their window, andante > allegro
    process counts;
  - the full `python tests/run.py`: 77 modules, 1666 tests. test_voicing's 5 s timing failed once under the
    parallel hash load (5.95 s) and passed alone.
- Keys and processes over the 16 judged slots (`D:\tmp\o18a\keys.py`, the same plan and seeds):

  | Measure | v3 (on) | v2 (o17's) |
  |---|---|---|
  | Keys per development block | 1.88 | 2.75 |
  | New-key arrivals per block | 0.88 (all prepared) | 1.75 |
  | Processes per block | 1.88 | 1.75 |
  | Process length, mean | 16.0 s | - |

- Route diversity over the 16 slots (`route_div.py`, o17's measure):

  | Measure | On (v3) | Off | o17 on (v2) |
  |---|---|---|---|
  | Mean pairwise Jaccard distance of the route tokens | 0.680 | 0.296 | 0.611 |
  | Distinct route signatures | 16 of 16 | 13 of 16 | 16 of 16 |
  | Distinct phase / technique orders | 13 of 16 | 10 of 16 | 13 of 16 |
  | Distinct tokens | 62 | 23 | 49 |

- Hard-gate caps on the judged seeds:
  - on: 2 of 16 (slot 2: seconds, shared; slot 12: dev_ops 3 - a block of one 'bass' process);
  - off: 8 of 16 (dev_own; slot 2 seconds).

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.01 | +0.04 | +0.07 | -0.18 | +0.09 | +0.06 | **+0.03** | -0.10 | +0.01 |
| se | 0.16 | 0.13 | 0.16 | 0.18 | 0.12 | 0.14 | 0.16 | 0.08 | 0.13 |
| slots won / lost | 8/6 | 9/7 | 8/8 | 6/8 | 8/7 | 9/5 | 8/7 | 5/8 | 7/8 |

- Per slot (overall, raw), new / old:

  | Slot | Pair | Overall |
  |---|---|---|
  | 001 | EQRA / SUEH | +0.57 |
  | 002 | ZPNE / LGNB | -0.71 |
  | 003 | ERSJ / QGKG | +0.43 |
  | 004 | GURQ / ZVXK | +0.14 |
  | 005 | JVVH / WKVR | -0.86 |
  | 006 | XBHB / UFSG | -0.14 |
  | 007 | UBVC / LATS | -0.71 |
  | 008 | PZUV / VSBM | +0.57 |
  | 009 | CXMN / XNFT | +0.00 |
  | 010 | ATKS / WFCE | +1.43 |
  | 011 | PGQS / TQTM | +0.86 |
  | 012 | ESGW / EBXH | -0.43 |
  | 013 | QDMZ / FWBC | +0.14 |
  | 014 | SVRG / BCSD | -0.86 |
  | 015 | YUWZ / YPEV | +0.14 |
  | 016 | WWEW / WWDJ | -0.14 |

  Normalised: +0.03 (se 0.20).
- Packet means (overall): on 4.85, off 4.82, references 7.05 (stormy 7.9, scherzo 7.4, river 5.9).
- **Masterpiece (absolute, 1-10):** on 3.33, off 3.32, references 5.14.
- Template flags (score_round's packet-end count, per packet): on 82.2, off 80.7, references 60.7 - set level, both
  codes.
- **The merge bar** (overall > 2 se): +0.03 = +0.2 se. **DON'T MERGE - DEV_WALK stays off.** This is the first
  derive round that is level (o16 -0.28, o17 -0.14). Form, life, orchestration and harmony lean up slightly (+0.07 /
  +0.06 / +0.09 / +0.04). Development is the weakest dimension (-0.18 se 0.18, 6 won / 8 lost).
  - The slow pieces no longer lose. The andantes: slot 4 +0.14, slot 6 -0.14, slot 14 -0.86, slot 16 -0.14 (o17:
    -1.71 / -1.43).
- **What the judges say about the development** (`D:\tmp\o18a\devcount.py`, o17's patterns; the sentences per
  packet, on / off / references):

  | Tell | On | Off | References | o17 on / off |
  |---|---|---|---|---|
  | panels, switching, patchwork, fragmentary, never settles | 43 | 41 | 8 | 23 / 11 |
  | unrelated material, no motivic link, filler | 13 | 19 | 3 | 12 / 10 |
  | loop, ostinato, static | 30 | 30 | 6 | 30 / 27 |
  | sequence to a goal (arrives, drives into the pedal / cadence) | 3 | 2 | 0 | 1 / 2 |
  | fugato, imitation, canon, stretto | 31 | 51 | 16 | 12 / 30 |
  | inversion, combination, augmentation | 10 | 11 | 7 | 13 / 15 |
  | modulation, new key | 20 | 14 | 3 | 21 / 11 |
  | unprepared / abrupt key, key panels, by jump | 16 | 20 | 3 | - |
  | "stretto" named | 2 | 8 | 3 | - |
  | static / stands still / stalls | 16 | 14 | 4 | - |

  - The panels are level now (43 / 41; o17 23 / 11), and so are the unprepared keys (16 / 20). The new-side key
    complaints are mostly outside the walk: "the E, A, G, C and F# panels come without modulation" (PZUV, bars
    13-46, the exposition), "the cuts from G to F minor/Eb (bar 14)" (ESGW), the climaxes' mode switches. Those are
    set-level (o18b).
  - v3's stretto is still not named. Both "stretto" sentences on new are fix requests ("prepare the tutti with the
    bar-7 theme in stretto", YUWZ). The new side's imitation sentences are the layout's dev_fugato blocks, which
    both codes have.
  - Old's own `develop()` stretto IS named: "a four-voice stretto" (WKVR, YPEV: vln2, viola, vln1, cellos + basses,
    one entry per bar) and "layered stretto entries ... build tension before the E pedal" (LATS). Old's is a
    whole-motto entry per bar, in the strings only, one choir; v3's entries spread over winds / violas / basses and
    are heard as texture.
  - The development's remaining fault is the MATERIAL, not the keys. Each process restates the unit; it does not
    take it apart. On the walk's blocks (`bars.py` maps the bars):
    - "moves it to C minor and Ab instead of transforming it" (ATKS, walk bars 28-45; ATKS still won, +1.43);
    - "restates the motto shape in Ab, Bb and C minor at the same soft level" (WWEW, walk bars 41-56 - the Eb
      sequence's degrees are heard as keys);
    - "the dialogue ... repeats the motto whole in each key and never takes it apart" (BCSD, old's develop() -
      both codes share this fault).
  - Several of the loudest development faults fall on the layout's dev_fugato, which both codes share:
    - "18 bars of one repeated sequence pattern" (SVRG bars 62-79, slot 14);
    - "violas, cellos, bassoons and basses play the same line in octaves" (SVRG 72-79);
    - "the lone violin 1 ... too thin to carry a development" (ESGW 41-51);
    - "20 bars of one to three violin lines, with no bass until bar 61" (ZPNE 43-62).
  - In a trial render (slot 4, andante) the four stretto voices sometimes meet on one pitch for a beat (the
    continuations step from their last notes).
- Best piece: BCSD (old, slot 14, seed 131130) 'The Distant Tides', overall 6.4, above the river reference
  (`D:\tmp\o18a\r\old\014-the-distant-tides`, `blind_o18a/BCSD.mp3`). Its on twin SVRG scored 5.6.
  - The best on piece: ATKS (slot 10, seed 131090) 'Toward the Storm' 6.1, the largest win (+1.43, all 7 lenses
    for or tied; `D:\tmp\o18a\r\new\010-toward-the-storm`, `blind_o18a/ATKS.mp3`).
  - The largest losses: slot 5 (JVVH, -0.86) and slot 14 (SVRG, -0.86).
- **Fixes for the next derive round** (the engine stays; the flag off):
  1. The stretto as an event: whole-motto entries one per bar in ONE choir (old's develop() stretto, which the
     judges name). Then join the other choirs. No voice should land on another's pitch (a voice-leading check
     against the others: no unisons / octaves between the entries - A4).
  2. Transform, don't transpose: each process should change the unit audibly (augmentation in the bass,
     fragmentation to the kernel, inversion as an answer) rather than restate it on the next degree. The judges
     hear a diatonic sequence's degrees as keys.
  3. The layout's dev_fugato (both codes) carries several of the worst development sentences: thin (one to three
     lines, no bass for 8+ bars), one sequence pattern for 18 bars, inner voices in octaves. It is outside the walk;
     fix it in a round of its own.
  4. Set level (o18b, both codes): the exposition's key panels and the climaxes' mode switches carry most of the
     "unprepared keys" left.
  5. The shared role-pick case that dropped slot 2's first seed: a retransition lead (the flutes) whose part plays
     no note fails silent_node.

## Round o18b: SET_PLAN on vs off - diverse, memoryful set-level plans, strict paired, 16 slots (2026-10-18)

The template round. The judges flag 45-52 template tells per packet on our pieces (7-28 on the references). The
tells are set-level plans that both codes share:

- the 6/8 plan;
- the timpani dominant-pedal build;
- the unison / doubled climax;
- the harp coda;
- the short-short-long motto;
- the stock brass chorale;
- the lone timpani last bar;
- the one-bar step sequence into the climax.

The question: does a set plan that draws those choices diverse and memoryful beat the same code with the flag off?
docs/ORCHESTRA_ENDLESS.md "Round o18b" describes the flag.

- **SET_PLAN** (`genres.symphony_setplan`, `shared_plan.py --flag setplan`; off is bit-identical). The data is in
  the owning tables, and `set_memory` is extended:
  - the tables in symphony.py: `GESTURES`, `ARC_CRISIS`, `VOICING`, `CONTOURS`, `END_FAMILIES` / `END_TEX` /
    `END_COLOURS`, `CELLS_V` / `MOTTO_FAMILIES`;
  - the tables in genres.py: `SETPLAN_SET`, `SETPLAN_MEMORY`, `SETPLAN_ARC`.

  What it draws:
  - **Builds**: 10 gestures, plus the crisis's collapse. Only `pulse` keeps the timpani drive. No build repeats
    within 4 pieces.

    | Gesture | Gesture | Gesture | Gesture | Gesture |
    |---|---|---|---|---|
    | swell | silence | fugato | lowbrass | deceptive |
    | stretto | calls | bass | pulse | subito |

  - **Climax arcs**:
    - `return` or `crisis`. In the crisis arc the climax sits in the development, in the parallel minor; a collapse
      follows, then a calm recapitulation.
    - The voicing: `layers` (melody, chords and brass in their own lines) or `tutti`.
    - The apex contour: rise, wave, arch or terrace.
  - **Endings**: the motto's last word, a plagal amen, deceptive then V-I, a falling line over the dissolve, the
    strokes, the cadence. No ending repeats within 4 pieces.
    - The harp is out of every coda.
    - The timpani is out of the last block unless the ending is `strokes`.
  - **Motto rhythm families**: 5 new five-note cells (syncope, trochee, hemiola, sigh, pickup). No family repeats
    within 3 pieces.
  - **The meter mix**: 6/8 0.25, 4/4 0.5 and 3/4 0.25 of the set, no meter twice in a row.
  - **The layout**: drawn among the feel's own layouts, with memory.
- **The protocol** (o14's / o16's / o17's).
  - One code (snapshot 06e42ad), the flag only.
  - The flag draws its own plan, so the pairing is by SLOT: `PLAN_on.json` (drawn with the flag on) vs
    `PLAN_off.json` (= master's draw). Both are drawn from seed 133000, 16 slots.
  - Best-of-1 on seed 133000 + 10 (k - 1) in both codes. A reject in either code drops the attempt for both.
  - **Dropped: 2 attempts**, both on the new half, by the gate's silent_node: the harp never rose above -50 dBFS.
    The harp is cut from the codas and has too little left elsewhere.
    - Slot 5: seed 133040 dropped, 133041 compared.
    - Slot 16: seed 133150 dropped, 133151 compared.
  - Two panels of 7 (the o14 lenses, JUDGE.md). The halves of a slot are in different panels (`deal --split`).
    The 3 hidden references and the masterpiece question.
  - composerE_p1 wrote its ratings on one line. It was reformatted before scoring (`D:\tmp\o18b\fixfmt.py`); the
    original is `blind_o18b/composerE_orig.txt`.
  - KEY `KEY_orch_o18b.json`.
  - The 32 mp3s, the KEY, SCORES.txt and SCORES_quality.txt are in `songs/_endless_orchestra/out/blind_o18b/`
    (main checkout). Scripts, renders and verdicts are in D:\tmp\o18b.
- **Checks before judging**:
  - The 24 protected hashes are bit-identical.
  - Flag off = master on 40 of 40 orchestra-symphonic pieces.
  - 16 + 16 composes ran without errors.
  - The full `python tests/run.py`: 77 modules, 1668 tests, one timing failure under the render load (test_voicing's
    5 s budget took 9.2 s; it passes alone in 1.9 s).
- **Gesture diversity over the 16 slots** (`D:\tmp\o18b\variety.py`; the features as played, from the composed
  blocks and the orchestration):

  | Measure | On | Off |
  |---|---|---|
  | Template similarity (mean pairwise share of 16 identical plan features) | **0.418** | 0.495 |
  | Distinct builds / endings (cadences) / motto families / climax arcs / contours | 10 / 5 / 9 / 2 / 4 | 7 / 3 / 6 / 1 / 1 |
  | Repeats within 4 slots: build / ending / motto family | 0 / 3 / 3 | 4 / 12 / 8 |
  | Timpani-pedal build / dominant pedal before the peak | 3 / 5 | 16 / 11 |
  | Harp in the coda / timpani in the last block | 0 / 2 | 10 / 6 |
  | Short-short-long or shorts motto / 6/8 | 3 / 4 | 6 / 7 |
  | Peak at 72-87 % / the return is the climax | 13 / 13 | 15 / 16 |

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.06 | -0.01 | -0.16 | -0.18 | -0.11 | -0.14 | **-0.16** | -0.22 | -0.12 |
| se | 0.24 | 0.22 | 0.30 | 0.38 | 0.16 | 0.24 | 0.27 | 0.17 | 0.21 |
| slots won / lost | 7/9 | 7/8 | 5/10 | 6/10 | 6/7 | 7/9 | 6/9 | 6/8 | 6/8 |

- **Per slot** (overall, raw, new - old):

  | Slot | New / old | Overall | The new plan |
  |---|---|---|---|
  | 001 | MLXA / EJFY | -0.57 | lowbrass build, deceptive end |
  | 002 | ELFR / YTVZ | +0.57 | stretto build |
  | 003 | HYRF / VGVX | +0.29 | silence build |
  | 004 | SRUS / TXPW | -0.43 | subito build |
  | 005 | QEPD / PFEM | -0.57 | crisis arc |
  | 006 | RFWG / VEYQ | **+2.29** | fugal layout, fugato build, amen end |
  | 007 | BWVE / UFLM | +1.29 | pulse build, deceptive end |
  | 008 | VSDP / WTUZ | +0.00 | |
  | 009 | JDGP / AWBJ | -1.29 | crisis arc, scherzo |
  | 010 | NFCX / QUJF | -0.57 | crisis arc |
  | 011 | PLLW / BVMD | +0.71 | deceptive build, amen end |
  | 012 | UURQ / ELPQ | -2.00 | scherzo_trio, a classical-size orchestra |
  | 013 | XMYN / ZKMQ | +0.57 | |
  | 014 | DFJA / KJPB | -0.86 | |
  | 015 | WDFG / DXNC | -0.43 | |
  | 016 | HQRA / CYPB | -1.57 | |

  - Normalised: -0.16 (se 0.33).
  - The lens pairs, overall: 33 won / 40 tied / 39 lost.
- **Packet means** (overall): on 4.93, off 5.09, references 7.31.
- **Masterpiece** (absolute, 1-10): on 3.59, off 3.71, references 5.62.
- **Template flags per packet** (the main target): on 34.4, off 39.0, references 23.7. That is 12 % fewer on the
  new pieces, but still 1.5x the references.
- **The merge bar** (overall > 2 se): -0.16 = -0.6 se. **DON'T MERGE - SET_PLAN stays off.**
- **What the judges say** (`D:\tmp\o18b\tells.py`: the verdict lines per packet that name the tell; on / off /
  references, per 7 readings):

  | Tell | On | Off | References |
  |---|---|---|---|
  | 6/8 | 0.38 | 0.94 | 0.00 |
  | timpani pedal build | **0.50** | 2.06 | 0.67 |
  | a pedal (dominant / X pedal) | **1.69** | 3.69 | 3.67 |
  | unison / octave climax | 1.50 | 1.88 | 2.83 |
  | harp (any) | 4.81 | 3.06 | 4.67 |
  | timpani ending / short-short-long | 0.00 / 0.00 | 0.06 / 0.06 | 0 / 0 |
  | brass chorale | 0.69 | 0.50 | 0.83 |
  | step sequence into the climax | 0.75 | 0.88 | 0.17 |
  | panels | 1.06 | 1.12 | 0.33 |
  | "same device / template / formula" | 1.19 | 1.19 | 0.33 |

  - **Where the flag acts, its tells dropped**: the timpani pedal build (0.50 vs 2.06), the pedal (1.69 vs 3.69),
    6/8 (0.38 vs 0.94).
  - **The harp coda is gone, but the harp is not.** The judges still name the harp SECTION after the climax (the
    post-peak episode block before the coda) as often as before: 14 on / 17 off sentences on a harp after the
    climax.
    - ELFR: "the harp and coda after the climax are generic".
    - NFCX: "the harp episode after the climax deflates the piece".
  - **The template flags left are the LAYOUT plans and shared material, not the gestures.**
    - UURQ (new) vs BVMD (old), both scherzo_trio: "it is the BVMD plan exactly (202 bars, 13 sections, tutti at
      141-162, harp episode S12, coda S13)".
    - HYRF / JDGP, two new 3/4 pieces: "bars 93-104 are identical to JDGP bars 73-84".
    - HQRA: "the same viola-semiquavers-under-held-violin opening as DXNC".
    - The statistician: "S10 loudest with the highest note at 76-81 %" (the peak position: 13 of 16 still at
      72-87 %).
    - The 3/4 share (4 of 16 on vs 2 off) put the scherzo's fixed form in front of each panel twice.
  - **The crisis arc lost all three of its slots** (5 / 9 / 10: -0.57 / -1.29 / -0.57).
    - The climax in the development was not heard as a climax. JDGP: "the minor-key climax is too short to redeem
      it", "the one tutti comes from nowhere".
    - The calm recapitulation was heard as a fade: "ends in a fade after an oboe recitative that stops the flow".
  - **The amen and deceptive endings were not heard as events.** They won 3 of their 6 slots: 6 / 7 / 11 (+2.29 /
    +1.29 / +0.71). Slots 1 / 12 / 16 lost (-0.57 / -2.00 / -1.57), on other grounds: the scherzo layout and the
    panels.
    - No verdict names a plagal or deceptive cadence.
    - The codas are still judged as winding down. PLLW (amen): "the coda simply fades".
- **Best piece**: RFWG (new, slot 6, seed 133050) 'The Bright Voyages'.
  - Overall 7.3, above the river and scherzo references; masterpiece 5.57. Its off twin VEYQ: 3.57.
  - The judges: "the C#-C#-G#-C#-B-E motto is the whole piece: sequenced, canonised, made a fugato and crowned in
    the C# major tutti"; "the only packet in the set that develops an idea the way the repertoire does".
  - Its plan: 4/4 fugal layout, fugato build, chorale climax, combine apex, arch contour, plagal amen, dotted motto.
  - `D:\tmp\o18b\r\new\006-the-bright-voyages`, `blind_o18b/RFWG.mp3`.
  - The largest losses: UURQ (slot 12, scherzo_trio) -2.00, HQRA (slot 16) -1.57.
- **Fixes for the next set-plan round** (the flag stays off):
  1. The layout is the template now. The scherzo_trio's fixed 13-section / 202-bar plan and the fugal / sonata
     section lists repeat bar for bar across pieces. Vary the section counts and proportions per piece (the memory
     on the layout's SHAPE, not its name), and cap 3/4 so one panel never gets two scherzos.
  2. Cross-piece verbatim material (HYRF / JDGP: bars 93-104 = 73-84). Find the shared source (the 3/4 trio /
     episode writer fed the same seedless figure) and seed it per piece.
  3. The harp after the climax. Retire the post-peak harp episode as a default too (the harp coda was only half the
     tell), and fix the silent_node rejects this caused (a piece whose only harp was in the coda).
  4. The crisis arc. Give the development climax the full summit treatment (brass, the top, the loudest section)
     and the calm recapitulation a growing line - or drop the arc: all three crisis slots lost.
  5. The peak position: 13 of 16 still sit at 72-87 % (the statistician's formula). Draw it per piece (0.55-0.9).
  6. The endings. Make the deceptive / amen cadences events: the deceptive chord at the tutti's level with the motto
     on it, and the coda recalling the motto transformed. 17 fix / missing lines (both codes) ask for the motto or theme
     at the close, e.g. "the motto should be heard once more in augmentation".

## Round o19a: SET_PLAN v2 on vs off - the layout's shape, the climax's place, no post-climax harp, the crisis, the endings, strict paired, 16 slots (2026-10-18)

The o18b fixes on the same flag. o18b moved the template from the gestures to the LAYOUT: a scherzo with the old
scherzo's plan exactly, two 3/4 pieces with identical bars (HYRF 93-104 = JDGP 73-84), the harp section after the
climax, 13 of 16 climaxes at 72-87 %. The crisis arc lost all 3 of its slots, and the new endings went unheard.
docs/ORCHESTRA_ENDLESS.md "Round o19a" describes the mechanics.

- **SET_PLAN v2** (`genres.symphony_setplan`, `shared_plan.py --flag setplan`; `SET_PLAN_ON['v2']`, o18b's flag as
  `SET_PLAN_V1`; off is bit-identical):
  1. **The shape**: `plan['set']['sections']` (-2 .. +2) drops or adds sections (`FORM_SHAPE`, `_shape_rows`).
     `composer._set_shape` (`plan['set_shape']`, generic) keeps a feel's (layout, sections) unique in a set. The 3/4
     share is capped at 2 of 16.
  2. **The verbatim bars** (master, flag-independent): the development's chart and voicings are a function of the key
     and the meter, so two F major scherzos shared bars. `_symphonic_arc` `key_apart`: `composer._slot` never draws
     a key that an earlier slot of the same time signature has. A clash is redrawn with its own die, so a slot
     without one draws as before. **What changes on master**: 96000 slot 8 (D major -> C major, outside the
     40-piece check), 133000 slots 10-13, 135000 slots 10, 11, 12 and 15 - keys only. No protected hash changes.
  3. **No harp after the climax**: `_set_plan_pass` empties the harp in every block after the peak. A harp with fewer
     than 16 notes is taken out of the piece. The post-peak recap2 is `POST_PEAK_V2` (dev_poly / cantabile horn /
     driving tutti, mf).
  4. **The crisis** (`CRISIS_V2`): the crisis 2 bars longer; the return after it the first theme augmented as a
     wind chorale (p - mf); a dissolving coda that recalls the motto. A mood without the dissolving coda plays the
     return arc.
  5. **The climax's place**: `plan['set']['peak_at']` (0.6 / 0.66 / 0.72 / 0.8 / 0.88; the crisis's mapped into
     0.48-0.62). `_place_peak` grows the short side, shortens the other, and if the climax is too early moves the
     second theme's return before the retransition (the reversed recap). It never goes under MIN_LEN, and the
     development stays within DEV_SHARE.
  6. **The endings** (`END_V2`): an end block of at least 5 bars with the whole motto at its own speed. The amen is
     V7 - I, then IV - I with 4 - 3 on top. The deceptive chord comes at f with the melody's tonic held over vi, then
     subito p.
- **The protocol** (o18b's):
  - One code (snapshot b41a119), the flag only.
  - Plans drawn by each mode from seed 135000, 16 slots, paired by slot.
  - Best-of-1 on 135000 + 10 (k - 1). A reject in either code drops the attempt for both.
  - **Dropped: 1 attempt** (new): slot 2, seed 135010, silent_node. The harp had 16 or more notes but stayed below
    -50 dBFS. 135011 compared.
  - Two panels of 7 (`deal --split`), 3 hidden references (river, stormy, scherzo), the masterpiece question.
  - KEY `KEY_orch_o19a.json`. The 32 mp3s, the KEY, SCORES.txt and SCORES_quality.txt are in
    `songs/_endless_orchestra/out/blind_o19a/` (main checkout). Scripts, renders and verdicts are in D:\tmp\o19a.
- **Checks before judging**:
  - The 24 protected hashes are bit-identical.
  - Flag off = master on 40 of 40 orchestra-symphonic pieces. key_apart changes none of them.
  - The full `python tests/run.py`: 77 modules, 1673 tests, 0 failed.
- **Gesture diversity over the 16 slots** (`D:\tmp\o19a\variety2.py`; o18b's measures plus the shape):

  | Measure | On | Off | o18b on / off |
  |---|---|---|---|
  | Template similarity (16 plan features) | **0.423** | 0.473 | 0.418 / 0.495 |
  | Shape similarity (same section kind at the same index) | **0.123** | 0.191 | |
  | Same feel + layout + section count (pairs) | **0** | 4 | |
  | Sections: mean / sd / range | 11.4 / 1.80 / 8-15 | 11.9 / 1.45 / 9-14 | |
  | Peak position: sd / range | **0.078** / 0.58-0.85 | 0.040 / 0.72-0.84 | |
  | Peak at 72-87 % | **9** | 15 | 13 / 15 |
  | Harp after the peak / no harp at all | **0** / 2 | 11 / 2 | |
  | Timpani-pedal build / dominant pedal before the peak | 4 / 1 | 16 / 10 | 3 / 5 / 16 / 11 |
  | 3/4 / 6/8 | 2 / 5 | 2 / 8 | 4 / 4 / 2 / 7 |
  | Crisis arc / reversed recap | 2 / 3 | 0 / 0 | |
  | The whole motto in the end block / amen on top / deceptive on top | 16 / 3 / 3 | 0 / 0 / 0 | |
  | Pairs with a cross-piece verbatim run (one role, 4+ bars) | 0 within the set | 3 within the set | |

  - The verbatim runs left are bass / cello pumps in relative or parallel keys (4-5 bars). They are chart-level
    coincidences, not a shared figure.

| new (on) - old (off), over the lens pairs, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.12 | -0.03 | -0.31 | -0.26 | -0.25 | -0.41 | **-0.25** | -0.04 | +0.00 |
| lens pairs won / tied / lost | 35/41/36 | 33/46/33 | 30/37/45 | 33/31/48 | 22/50/40 | 23/40/49 | 31/40/41 | 27/56/29 | 29/53/30 |

- **Over the 16 slots**: overall -0.25 (se 0.20), normalised -0.25 (se 0.19), 6 won / 9 lost.
- **Per slot** (overall, raw, new - old):

  | Slot | New / old | Overall | The new plan |
  |---|---|---|---|
  | 001 | YZGH / GZBB | -0.57 | 6/8 journey, 9 sections |
  | 002 | EYAF / RUES | +0.29 | arch, amen end |
  | 003 | YPEH / VDSU | -0.71 | 6/8 rondo, peak 0.63 |
  | 004 | HFEH / BNQU | +0.00 | variations, **crisis arc** (peak 0.58) |
  | 005 | FYAE / VGLT | **-1.86** | 6/8 journey_var, subito build |
  | 006 | ZAVN / CPAB | -0.14 | sonata, 14 sections, deceptive end |
  | 007 | LEPD / YHWA | -0.43 | scherzo_trio, 8 sections, amen end |
  | 008 | UXNW / KUZJ | +0.29 | 6/8 compact, swell build |
  | 009 | REJE / PSND | -0.29 | scherzo_trio, 10 sections |
  | 010 | USYF / MXJM | +0.43 | rondo, stretto build, peak 0.65 |
  | 011 | KDFY / VSJP | -0.29 | 6/8 journey, deceptive end |
  | 012 | BAPY / XUUS | **+1.14** | fugal, pulse build, amen end |
  | 013 | RKJR / YZEG | +0.71 | through-composed, peak 0.82 |
  | 014 | GCWZ / BZWP | -1.29 | sonata, **15 sections** |
  | 015 | EWFT / BUKJ | -1.57 | ternary, **crisis arc**, 14 sections |
  | 016 | TKNH / HASG | +0.29 | arch, deceptive end |

  - **By draw** (mean of the slot overalls):
    - The crisis arc: 2 slots, -0.79.
    - 14 or more sections: 3 slots, -1.00.
    - Peak before 0.7: 7 slots, -0.43. Peak at 0.7 or later: 9 slots, -0.11.
    - Amen ending: 3 slots, +0.33. Deceptive ending: 3 slots, -0.05.
- **Packet means** (overall, quality lens): generated 5.08, references 6.48.
- **Masterpiece** (absolute, 1-10): on 3.62, off 3.62, references 5.10.
- **Template flags per packet**: on 37.1, off 48.6, references 15.3. That is 24 % fewer on the new pieces (o18b:
  12 %), but still 2.4x the references.
- **The merge bar** (overall > 2 se): -0.25 = -1.25 se. **DON'T MERGE - SET_PLAN stays off.** key_apart (fix 2) is
  in this branch's master code. It is flag-independent and changes only the slot keys listed above.
- **What the judges say** (`D:\tmp\o19a\tells.py`, o18b's regexes plus two; verdict lines per packet, references per
  7 readings):

  | Tell | On | Off | References |
  |---|---|---|---|
  | 6/8 | 0.06 | 0.25 | 0.33 |
  | timpani pedal build | **0.50** | 1.69 | 0.33 |
  | a pedal (dominant / X pedal) | **1.44** | 3.19 | 2.17 |
  | unison / octave climax | 1.56 | 1.81 | 3.67 |
  | harp (any) | 3.50 | 4.44 | 4.67 |
  | harp after the climax | **0.00** | 0.50 | 0.00 |
  | brass chorale | 0.44 | 0.88 | 0.50 |
  | step sequence into the climax | **0.19** | 0.88 | 0.17 |
  | amen / plagal / deceptive named | **1.00** | 0.12 | 0.00 |
  | "same device / template / formula" | **0.94** | 1.56 | 0.17 |

  - **The tells the flag targets are gone.** No verdict names a harp after the climax on the new pieces. On the old
    pieces they do: "Five pieces then add a harp + violins1 + low-strings section ... after the climax: CPAB, HASG,
    MXJM, RUES, XUUS" (all old). No layout-copy or verbatim-bars sentence on any piece.
  - **The endings are heard now, but as expected closes, not events.**
    - BAPY: "the plagal close at 112-114 is gentle but expected".
    - TKNH: "the coda is just horn arpeggios and a plagal cadence".
    - REJE: "The deceptive Bb before the last D minor ... is a nice touch".
  - **The shared section plan is still named, on both codes.** One composer lists nine packets sharing "running
    figure over a held note, tutti statement, remote-key or harp block, 16-bar dialogue over bassoon bass, oboe line
    over pulsing bass, timpani pedal, climax, quiet coda". Four of the nine are new (EWFT, FYAE, KDFY, YZGH). The
    section COUNT varies now; the section TEXTURES (the 16-bar violins1 / cellos dialogue, the oboe over pulsing
    bass) do not.
  - **What the flag lost on** (life -0.41, form -0.31):
    - **Added sections make the piece choppy.** ZAVN: "seven sections of four to six bars start and stop". GCWZ:
      "nine short sections of 4-6 bars never let a theme establish itself". These are the +2 shapes.
    - **The long fades** (all new): "The fades run 19-20 bars (EWFT 106-124, YPEH 90-108, YZGH 80-99, KDFY
      94-113)". The dissolving / echo codas plus the 5+ bar end block.
    - **An early climax leaves a long wind-down.** HFEH: "the peak comes too early and the remaining 40 % (64-98)
      only winds down".
    - **The crisis arc is still not convincing.** EWFT (the ternary crisis) lost -1.57 on every lens except the
      statistician; the judges hear its dialogue and pedal blocks "idle on the turn motto". HFEH (the variations
      crisis) is level.
    - LEPD (scherzo, 8 sections): "56 bars of near-silence in a scherzo kill the drive".
- **Best piece**: UXNW (new, slot 8, seed 135070) 'Symphonic Dance: Fires of Home', overall 6.7 (quality lens),
  masterpiece 4.71 - level with its off twin KUZJ (6.4 / 4.71). Its plan: 6/8 compact, swell build, peak 0.68,
  strokes ending. Below o18b's RFWG (7.3).
  - The largest win: BAPY (slot 12, fugal, pulse build, amen) +1.14. The largest losses: FYAE (slot 5) -1.86, EWFT
    (slot 15, crisis) -1.57, GCWZ (slot 14, 15 sections) -1.29.
- **Fixes for the next set-plan round** (the flag stays off):
  1. Shape by merging, not adding: the +1 / +2 shapes add short sections, and the judges hear stop-and-start. Vary
     the section count by changing the section LENGTHS and merging blocks (fewer, longer sections), and cap the
     count at about 12.
  2. Vary the section textures, not only their count: the 16-bar violins1 / cellos dialogue, the oboe over a pulsing
     bass and the running figure under a held note are the template now (both codes). Draw them with set memory
     like the gestures.
  3. The codas: cap the fade / dissolve at 8-10 bars after the end block; the 19-20 bar fades read as winding down.
  4. Drop the crisis arc (5 of 5 slots across o18b / o19a lost or tied), or make it a real development crisis with
     new material, not a stronger dynamic curve.
  5. Keep the climax at 0.66 or later: the early peaks (< 0.7) lost -0.43 on average, the later ones -0.11.
  6. Keep: no harp after the climax, the whole motto at the end, the amen (it won 2 of 3), key_apart.
  7. The harp gate: a harp with 16+ notes can still be too quiet for silent_node (slot 2's drop). Gate on its level,
     not its note count.
## Round o19b: FUGUE on vs off - a real fugato and a joint voice-leading core, strict paired, 16 slots (2026-10-18)

The development round on the shared FUGATO block. In o18a several of the worst development sentences in both codes
fell on it: "18 bars of one repeated sequence pattern", "lone violin", inner voices in octaves. Code review C7 / A4
asked for real counterpoint. docs/ORCHESTRA_ENDLESS.md "Round o19b" describes the flag.

- **FUGUE** (`symphony.FUGUE = FUGUE_ON`, `shared_plan.py --flag fugue`; off is bit-identical):
  - `Writer.fugue2` writes the `dev_fugato` blocks: a subject from the motto (`fsubject`), a tonal answer at the
    fifth, a counter-subject (rhythmically complementary, written once against the first answer, restated), 3-4
    entries over four registers and the choirs (`fugue_mixed` / `fugue_horn` / `fugue_reeds`), the entering voice
    on top in velocity.
  - After the exposition: a modulating episode from a subject fragment (falling fifths or a rising chain, imitated
    half a bar later), a middle entry in a long block, the final entry in the bass or a stretto, a half cadence
    with the bass driving 8ths.
  - The fugato key is drawn from the related keys (vi / ii / iii / IV / V; minor iv / v / III / VI).
  - The joint voice-leading core in voicing.py: `cp_issues`, `repair`, `complement_rhythm`, `counterline` (a beam
    search with a hook), for the summit's layers later.
- **The fugato count, and the forced plan.** Master's plan for seed 137000 (16 slots) has a fugato in only 8 of 16
  slots. For power, the plan was forced: dev = `fugato_dialogue` in slots 1, 3, 4, 6, 7, 10, 11 and 15, for BOTH
  codes (`D:\tmp\o19b\r\PLAN_137000_f.json`). **16 of 16 pieces hold a fugato** (dev1; dev2 in slot 14).
- **The protocol** (o18a's). One code (snapshot 5de2c3d), the flag only, the same forced plan in both codes:
  - Best-of-1 on seed 137000 + 10 (k - 1). A gate reject would drop the slot for both: **0 dropped**, all 16
    slots passed on the first seed in both codes.
  - Two panels of 7 (the o14 lenses, JUDGE.md). The halves of a slot are in different panels (`deal --split`).
    The 3 hidden references (o18b's) and the masterpiece / missing questions.
  - composerC_p2 wrote its ratings on one line. They were reformatted before scoring (`D:\tmp\o19b\fixfmt.py`);
    the original is `D:\tmp\o19b\r\composerC_p2_orig.txt`.
  - A machine shutdown interrupted the judging. p1 composerA-D came from a second launch of the same prompts (the
    first launch never wrote); the other 10 were relaunched with the same briefs and packets after the restart.
    Every judge read only its own folder.
  - KEY `KEY_orch_o19b.json`. The 32 mp3s, the KEY, SCORES.txt and SCORES_quality.txt are in
    `songs/_endless_orchestra/out/blind_o19b/` (main checkout). Scripts, renders and verdicts are in D:\tmp\o19b.
- **Checks before judging**:
  - The 24 protected hashes are bit-identical.
  - Flag off = master on 40 of 40 orchestra-symphonic pieces.
  - The full `python tests/run.py`: 77 modules, 1673 tests, 0 failed.

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | +0.21 | +0.08 | +0.20 | +0.26 | +0.27 | +0.31 | **+0.27** | +0.08 | +0.12 |
| se | 0.13 | 0.10 | 0.12 | 0.16 | 0.14 | 0.14 | 0.15 | 0.14 | 0.13 |
| slots won / lost | 10/5 | 7/7 | 10/5 | 10/5 | 11/4 | 10/3 | 9/4 | 8/8 | 7/6 |

- **Per slot** (overall, raw, new - old):

  | Slot | New / old | Overall | Note |
  |---|---|---|---|
  | 001 | GEPR / BUNU | -0.57 | forced; the 20-bar viola-led fugato read as a quiet lull in a 6/8 vivace |
  | 002 | GKER / RECB | +0.29 | |
  | 003 | DDQS / XXNW | +0.57 | forced; "a real fugato" from the motto (violas, cellos, oboe, violins) |
  | 004 | TNSF / EQTH | **+1.43** | forced; horn subject, clarinet answer, a modulating episode into C |
  | 005 | LHZX / KPMS | -0.29 | cello-first fugato, then 28 thin bars |
  | 006 | FDJQ / REUF | **+1.29** | forced; the best generated packet (6.3) |
  | 007 | LPAF / NMQF | -0.29 | forced; a lone horn line led the fugato |
  | 008 | HZMX / CJTK | +0.00 | |
  | 009 | ZRGR / FYEK | +0.00 | |
  | 010 | VEBZ / XPSZ | +0.71 | forced |
  | 011 | UZBH / GELL | +0.43 | forced; a scherzo, 52 thin bars from the fugato on |
  | 012 | XUHE / NPDD | +0.00 | |
  | 013 | LUNL / XEVZ | +0.14 | |
  | 014 | AVSK / SECE | +0.29 | the fugato in dev2 |
  | 015 | ERUV / FXXQ | -0.71 | forced; a 32-bar clarinet fugato and episode at one level in an andante |
  | 016 | KBRL / PJFK | +1.00 | |

  - The 8 forced slots: +0.36 mean; the 8 unforced: +0.18.
  - Normalised: +0.27 (se 0.22).
  - The lens pairs, overall: 46 won / 39 tied / 27 lost.
- **Packet means** (overall, all readings): on 5.06, off 4.79, references 6.64.
- **Masterpiece** (absolute, 1-10): on 3.54, off 3.41, references 5.07.
- **The merge bar** (overall > 2 se): +0.27 = +1.7 se. **DON'T MERGE - FUGUE stays off.** It is the best paired
  result since o12, every dimension leans up (life +0.31, 2.2 se; orchestration +0.27, 1.9 se), but it is under the
  bar.
- **What the judges say about the fugato** (`D:\tmp\o19b\fugsent.py`: the verdict lines per code that match;
  16 packets x 7 readings each side, references 6 x 7):

  | Pattern | On | Off | References |
  |---|---|---|---|
  | fugato / fugue / fugal | 40 | 55 | 6 |
  | imitation / entries / subject / answer | 48 | 58 | 17 |
  | counter-subject | 4 | 5 | 0 |
  | stretto | 5 | 3 | 1 |
  | episode | 11 | 10 | 8 |
  | counterpoint praise ("real counterpoint", "genuine imitation") | 3 | 4 | 0 |
  | lone / thin | 16 | 16 | 3 |
  | octaves / unison / parallels | 26 | 23 | 23 |
  | one pattern / long sequence | 9 | 16 | 0 |
  | modulation | 17 | 23 | 7 |

  - On: "a real fugato" (DDQS, from the motto; TNSF with "a modulating episode through Bb and F that winds into
    C"); HZMX's "fugato really uses the motto"; GEPR's fugato "the clearest texture in the piece"; LHZX's
    cellos-first fugato "gives the middle some weight".
  - On, still wrong:
    - The first entry alone, and the block quiet and thin for 16-20 bars (GEPR "20 bars of viola, then two
      violins, alone and quiet"; LPAF "a lone horn line"; VEBZ "enters alone ... the later entries come in thin";
      roles per bar 1-5 at -1.5 to -5 LU, statistician).
    - The counter-subject not heard (DDQS "never gain a countersubject"; GEPR); entries 2 bars apart "with
      identical shape at the octave".
    - The subject heard as new material in 3 pieces (TNSF, KBRL, ERUV): the motto kernel is not the tune the
      judges call the opening theme.
    - The fugato never returns at the summit (LHZX, ERUV, FDJQ "lands at the summit as register, not as
      combination").
    - The same 2-bar-entry recipe in every piece (FDJQ = TNSF, statistician).
  - Off, in the same block: "one bare violin line" / "unaccompanied first-violin fugato" (EQTH, REUF, PJFK, XPSZ),
    "doubling disguised as imitation" (EQTH), the subject "repeated 6 times on the same pitch" (NMQF). The
    one-pattern lines fall 16 -> 9 and the "unaccompanied violin" lines are gone. The thin-texture lines stay level
    (16 / 16): the lone voice moved from the violin to the viola / horn / clarinet.
- **Best piece**: FDJQ (on, slot 6, "Rising Forests of Winter") overall 6.3, level with TNSF (on, slot 4) and
  the scherzo reference (6.3); the references river 6.4, stormy 7.3. `blind_o19b/FDJQ.mp3`.
- **Fixes, next** (one flag round each):
  1. The exposition's opening: the first entry over a held bass / pedal or the continuing accompaniment, never one
     voice alone; the block's dynamic grows entry by entry (mp -> f is too little in 16-20 bars); roles per bar
     at least 3 from the second entry.
  2. Make the counter-subject audible: a different register and colour from the entry, its own dynamics; entries
     not only at the octave (alternate the fifth / octave over the four registers).
  3. The subject from the tune the listener hears as the theme (the motto's first phrase), not the kernel alone.
  4. Shorten the fugato in fast 6/8 and scherzo pieces (20 bars max 12 at vivace), and keep the dance accompaniment
     under the entries.
  5. Bring the fugato subject back at the summit: in augmentation in the bass, or combined with the motto (A4's
     `counterline` against the summit's melody, the next use of the core).
  6. Vary the entry spacing (1, 1.5 or 2 bars, a false entry) so the recipe is not shared across pieces.

## Round o20: SET_PLAN v3 on vs off - the shape by merging, the textures with set memory, the fades capped; per piece strict paired, 16 slots, plus the first set-level judgment (2026-10-18)

o19a's fixes on the same flag, plus a second kind of measurement. Per-piece judging cannot reward diversity across an
endless stream, so this round also judges whole programmes: 8 pieces in a row from one set plan seed, per code.
docs/ORCHESTRA_ENDLESS.md "Round o20" describes the mechanics.

- **SET_PLAN v3** (`genres.symphony_setplan(on, version)`; `shared_plan.py --flag setplan` is v3, `--flag setplan2`
  is o19a's v2; `SET_PLAN_ON = SET_PLAN_V3`, `SETPLAN_VERSION = 3`; off is bit-identical):
  1. **The shape by merging and lengthening** (o19a fix 1, `FORM_MERGE`, `_merge_rows`): `plan['set']['sections']`
     is now -3 .. 0. `_merge_rows` folds the shortest eligible block into its predecessor (t1b into t1, the closing
     group into the second theme / river / episode / trio / variation, the episodes into a neighbour) up to a
     per-kind maximum bar count, and never touches the climax or a false recapitulation. The section count is capped
     at 12, and v2's `_shape_rows` (the added blocks) does not run. Every long kind is at least 8 bars, and
     `_grow_len` uses a per-kind grow list (`FORM_MERGE['more']`), so a piece with fewer sections is not shorter.
  2. **The section textures with set memory** (fix 2, `TEX_V3`): `plan['set']` draws `tex_t1` (drive / walking
     dialogue / cantabile / running strings / driving tutti), `tex_t1b` (motto in the bass / tutti drive / motto in
     the brass / brass dialogue) and `tex_dev` (dialogue / brass dialogue / dev_poly / walking dialogue / walking
     poly) with memory 3 / 2 / 3, and `t2col` / `src` with longer memory. A block the layout gave no texture plays
     the drawn one; the development's dialogue blocks rotate through it.
  3. **The fades capped** (fix 3, `FADE_V3`): a dissolving coda plus the end block at most 10 bars, the coda at least
     4.
  4. **No crisis arc** (fix 4): `arc` is always the return.
  5. **The climax at 0.7 or later** (fix 5, `PEAK_AT_V3`): `peak_at` 0.7 / 0.74 / 0.78 / 0.82 / 0.86; `_place_peak`
     with v3's pre / post tables (an 8-bar floor for the long kinds), the floor 0.66 checked after the growth.
  6. **The harp gate** (fix 7, `POST_HARP_V3`): no harp after the climax as in v2. A role with no notes, or a harp
     with fewer than 4, is removed from the band, not only emptied. o19a's slot-2 silent_node was an EMPTY harp
     track: `plan_o.roles()` lists every role with parts, also parts without notes. Every section where a harp did
     play measured -22 to -42 dBFS RMS, well above the gate's -50.
  7. Kept: the whole motto in the end block, the amen / deceptive endings (`END_V2`), the build gestures with memory,
     `key_apart` (master).
- **The protocol** (o19a's, per piece):
  - One code (snapshot 7113845), the flag only. Plans drawn by each mode from seed 139000, 16 slots, paired by slot.
  - Best-of-1 on 139000 + 10 (k - 1). A reject in either code drops the attempt for both.
  - **Dropped: 1 attempt** (old): slot 1, seed 139000, silent_node (flutes). 139001 compared.
  - Two panels of 7 (`deal --split`), 3 hidden references, the masterpiece question.
  - KEY `KEY_orch_o20.json`.
- **The set-level protocol** (new; `songs/_blind/set_round.py`, the judges' brief `songs/_blind/JUDGE_SET.md`):
  - Per code one continuous 8-piece set drawn by the CLI's set planning (`composer.set_plan`, the code's flags applied
    first) from the set seed. Slot k is composed with seed SET_SEED + 10 (k - 1) + attempt, best-of-1, the same
    seeds in both codes; a reject in either code drops the attempt for both. The symphony's build ignores `prev`, so
    per-slot renders are the CLI's continuous set.
  - 3 set pairs (set seeds 139500, 139600, 139700) x 7 judges (judge_orch's quality lenses) = 21 forced choices.
    Dropped attempts: 139500 slot 7 (old, silent_notes); 139600 slot 2 (new, 4 x silent_notes: a cellos A#3 three
    times, a violins1 F4 once) and slot 6 (old, flat_dynamics, horns); 139700 none.
  - Each judge reads both programmes' 8 packets IN ORDER as "an evening's programme from one composer". The codes are
    anonymised as X / Y and the reading order is drawn per judge; the judges never see the KEY or the code.
  - Questions: which programme they would keep listening to after piece 8 (forced choice, strength 1-5); variety and
    coherence / identity 1-10 per programme; where it started to feel like the same piece again (piece number +
    why); the repetition tells across the set; best and weakest piece.
  - The set KEY is `KEY_orch_o20_sets.json`.
  - The 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt and SET_SCORES.txt are in
    `songs/_endless_orchestra/out/blind_o20/` (main checkout). Scripts, renders and verdicts are in D:\tmp\o20.
- **Checks before judging**:
  - The 24 protected hashes are bit-identical.
  - Flag off = master on 40 of 40 orchestra-symphonic pieces.
  - The full `python tests/run.py`: 77 modules, 1677 tests, 0 failed. `test_endless_symphony` `SetPlanV3`: v2
    reachable, no crisis, peak_at >= 0.7, the texture memory, the merge's fold and cap, and v3 pieces with at most
    12 blocks, the peak at the floor, fades of at most 10 bars, no empty role, no harp after the peak.
- **Gesture diversity over the 16 slots** (`D:\tmp\o20\variety3.py`: o19a's variety2.py plus the textures, the short
  sections and the fades):

  | Measure | On | Off | o19a on / off |
  |---|---|---|---|
  | Template similarity (16 plan features) | **0.436** | 0.496 | 0.423 / 0.473 |
  | Distinct layouts / builds | 11 / 10 | 7 / 7 | |
  | Timpani-pedal build / dominant pedal before the peak | **2 / 4** | 16 / 11 | 4 / 1 / 16 / 10 |
  | Harp in the coda / after the peak | **0 / 0** | 7 / 9 | 0 / 11 |
  | Sections: mean / range / over 12 | 11.2 / 8-12 / **0** | 12.0 / 10-14 / 6 | 11.4 / 8-15 |
  | Same feel + layout + section count (pairs) | 1 | 7 | 0 / 4 |
  | Shape similarity (same kind at the same index) | 0.276 | 0.204 | 0.123 / 0.191 |
  | Peak position: mean / sd / range | 0.801 / 0.051 / 0.73-0.88 | 0.778 / 0.037 / 0.74-0.85 | |
  | Peak at 72-87 % | 15 | 16 | 9 / 15 |
  | Texture similarity (t1 / t1b / t2 / first dev dialogue) | **0.130** | 0.345 | |
  | Dissolving fade, longest | **10 bars** | 16 bars | 19-20 bars on |
  | Sections under 8 bars (all pieces) | 40 | 53 | |
  | Motto in the end block / amen / deceptive on top | 14 / 3 / 3 | 0 / 0 / 0 | 16 / 3 / 3 |
  | Length: mean / range | 231 s / 178-339 | 220 s | |

  - Off's t1 / t1b textures come from the kind table, not from the layout's override, so its texture similarity is
    overstated a little. The shape similarity rose, probably because the merges leave the same kinds at the same indices.
  - Cross-piece verbatim runs are left: bass / cello pumps of 4-6 bars between relative or parallel keys, and slot 11
    on x off at 15 bars (the same slot and key in both codes, not within one set).

| new (on) - old (off), over the lens pairs, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.06 | +0.10 | +0.09 | +0.04 | +0.02 | **-0.32** | **-0.04** | +0.12 | -0.01 |
| lens pairs won / tied / lost | 38/33/41 | 42/32/38 | 39/34/39 | 43/25/44 | 41/34/37 | 27/33/52 | 44/25/43 | 38/50/24 | 39/33/40 |

- **Over the 16 slots**: overall -0.04 (se 0.24) = -0.17 se, normalised -0.04 (se 0.36), 9 won / 7 lost. The first
  SET_PLAN round that is level per piece (o18b -0.16, o19a -0.25). Only life lost.
- **Per slot** (overall, raw, new - old):

  | Slot | New / old | Overall | The new plan |
  |---|---|---|---|
  | 001 | LLZF / PWLW | +0.50 | river journey_var, -1, peak 0.86, subito |
  | 002 | SNKM / XFEC | **-1.36** | scherzo compact, peak 0.74, deceptive build + end |
  | 003 | CJJW / EXJH | +1.07 | vivace sonata, -2, calls, strokes |
  | 004 | FTPG / CTVU | +0.86 | andante arch, -1, swell, amen |
  | 005 | AVSQ / XALC | +0.36 | river journey, -3, pulse, motto |
  | 006 | VYBY / GWHQ | +0.14 | andante through, -2, fugato, line |
  | 007 | CJEJ / TQAX | +0.21 | vivace compact, silence, deceptive |
  | 008 | CUXB / PJWM | **-1.21** | allegro false, -1, deceptive build, strokes |
  | 009 | UGFG / MVGS | -0.14 | scherzo_trio, -2, bass, amen |
  | 010 | KVCW / BWQH | **-1.71** | allegro rondo, -3, stretto |
  | 011 | DAQA / JFGU | -0.93 | vivace variations, swell, motto |
  | 012 | GVBG / MQHK | -0.50 | allegro compact, -1, lowbrass |
  | 013 | BPBB / HBJZ | +1.07 | andante sonata, -2, fugato, deceptive |
  | 014 | GTLW / JTAT | -0.79 | allegro false, -3, silence, amen |
  | 015 | LNEV / CMEE | **+1.36** | andante fugal, deceptive build |
  | 016 | BQXJ / APQS | +0.43 | allegro through, -1, pulse, strokes |

  - By draw: the andantes won all 4 (+0.86 mean); the allegros 1 of 5 (-0.76); the -3 merges -0.71 over 3 slots
    (KVCW's rondo lost -1.71 against the round's best generated piece, BWQH).
- **Packet means** (overall, quality lens): new 5.05, old 5.09, references 7.13.
- **Masterpiece** (absolute, 1-10): on 3.59, off 3.60, references 5.65.
- **Template flags per packet**: on 37.9, off 36.4, references 7.3. Not fewer this time (o19a: 37.1 vs 48.6); the
  judges name the shared skeleton (soft intro, a quiet middle, an 8-bar brass-entry build, the tutti summit at 3/4,
  a coda) on both codes alike.
- **What the judges say per piece** (`D:\tmp\o20\tells20.py`, o19a's regexes plus five; verdict lines per packet):

  | Tell | On | Off | References |
  |---|---|---|---|
  | 6/8 | **0.56** | 1.75 | 0.83 |
  | timpani pedal build | **0.44** | 1.00 | 0.67 |
  | a pedal (dominant / X pedal) | **1.00** | 2.81 | 2.67 |
  | unison / octave climax | 0.81 | 1.69 | 3.33 |
  | harp (any) / harp after the climax | 1.50 / **0.00** | 3.12 / 0.31 | 3.50 / 0.00 |
  | brass chorale | 0.56 | 0.31 | 0.50 |
  | step sequence into the climax | 1.25 | 0.50 | 0.50 |
  | amen / plagal / deceptive named | 0.56 | 0.31 | 0.17 |
  | "same device / template / formula" | 0.94 | 1.31 | 0.33 |
  | dialogue (any) | **0.31** | 0.94 | 0.33 |
  | fade / dies away / winds down | 0.75 | 0.62 | 0.33 |
  | short / choppy sections | **0.06** | 0.38 | 0.17 |
  | long / too long / static / loops | **2.06** | 0.75 | 1.00 |

  - **The o19a complaints are gone**: no choppy-section sentence on a new piece (0.06 lines per packet), no 19-20 bar
    fade, no crisis, no harp after the climax, the dialogue texture named a third as often.
  - **The new complaint is the long block** (2.06 vs 0.75): the merged sections are long and the merged material
    does not develop. BPBB composerD: "cut or merge S4-S8 (about 60 bars of thin texture)". The life lens (-0.32,
    27 / 33 / 52) is where the round lost. Some new pieces end without a closing gesture after the climax (GTLW:
    "the after-climax oboe solo and the quiet coda drift").
  - The step sequence into the climax is named more often on the new pieces (1.25 vs 0.50): the gestures that
    replaced the timpani pedal are heard, and one of them (the rising one-step-per-bar ladder) is the next tell.
- **The set-level judgment** (`set_round.py score`, D:\tmp\o20\r\SET_SCORES.txt; 21 verdicts):

  | Set pair | Judges | New kept | Variety new / old | Coherence new / old |
  |---|---|---|---|---|
  | set139500 | 7 | **6** | 5.43 / 4.43 | 6.29 / 6.00 |
  | set139600 | 7 | **5** | 5.00 / 4.29 | 6.14 / 5.86 |
  | set139700 | 7 | **0** | 4.29 / 5.71 | 5.71 / 6.00 |
  | all | 21 | **11 (0.524)** | 4.90 / 4.81 (paired +0.10 se 0.34) | 6.05 / 5.95 (paired +0.10 se 0.12) |

  - **The forced choice**: new kept by 11 of 21 = 0.524, 95 % CI Wilson 0.32-0.72, exact 0.30-0.74, binomial p 1.00.
    The CI does not lie above 50 %. Strength-signed mean +0.14 (se 0.58), mean strength 2.5 ("close, not clear"
    in most verdicts). The programme read first was kept 9 of 21 (no order effect worth naming).
  - **"Where did it start to feel like the same piece again"**: new at piece 5.38 on average (3 x piece 3, 6 x piece
    5, 11 x piece 6, 1 x piece 8), old at 4.48 (1 x 2, 15 x piece 4, 2 x 5, 2 x 7, 1 x 8). Paired per judge new
    later by +0.90 (se 0.36), later in 15 of 21. No judge answered "never" for either code.
  - **The sets disagree.** 139500 and 139600 went to the new code 11 of 14: its builds differ from piece to piece
    ("X gets to its summits by different routes: a horn sequence over a falling bass, a walking bass, running horns,
    a rising bass line, a timpani pedal only once, a general pause"), and the openings differ. 139700 went to the
    old code 7 of 7, for reasons the flag does not touch and one it does:
    - The keys: the new set drew seven major keys and one dorian, F major three times (3, 5, 7), no true minor;
      the old set (the same set seed, but v3's extra draws move the stream) drew D dorian, G minor and F minor.
      "Y is seven major pieces out of eight, with F major three times" (composerE). `key_apart` only keeps a key
      apart per time signature.
    - The layout twins: new pieces 2 and 7 are both allegro rondos ("3|12|12|8|12" at the start of both, the same
      violin figure "D5 Ab5 D5 Ab5 E5" in S7 of both), and 6 and 8 have the same 11-section plan with two 16-20 bar
      quiet blocks in S6-S7. `set_shape` keeps (feel, layout, SECTIONS DRAW) unique, and two rondos with different
      deltas merged into almost the same bar plan. Measured over the packets' layout lines (the share of section
      lengths equal +-1 bar at the same index, `D:\tmp\o20\setlayout.py`), the within-set similarity is the same
      for both codes (new 0.256 / 0.198 / 0.253, old 0.250 / 0.241 / 0.204), so the twins are the gap, not a
      general convergence.
    - The loud endings: six of eight new pieces close loud (tutti cadence); the old set alternates three dissolving
      codas with loud ones.
  - **Tells per programme**: new 8.3, old 8.0 lines. Named on the new sets: the pre-climax brass-entry section in
    every piece, the summit at 79-91 %, the two-half-notes-stepping-down cadence before the final tonic, the
    one-step-per-bar climax ladder, the long quiet middle pair before the build. On the old sets: the timpani /
    dominant pedal build in all eight pieces, the 6/8 openings with a running figure under a held note, the
    scherzo played twice, identical section tails (16|16|8|12|13).
  - Best piece in the programme: new pieces 3-4 most often, old piece 3 (and 7). Weakest: new piece 5-7, old piece
    8 (the last piece of the old programme is the weakest in 8 of 21 verdicts: often the second scherzo or a copy).
- **The decision rule** (stated before the round): MERGE (flag on by default) only if the per-piece overall paired
  mean is not worse than -1 se AND the set-level win rate's 95 % CI lies above 50 %, or the per-piece result alone
  clears > 2 se.
  - Per piece -0.04 = -0.17 se: non-inferiority met; > 2 se not met.
  - Set level 0.524, CI 0.30-0.74 (exact): not above 50 %.
  - **DON'T MERGE - SET_PLAN stays off** (v3 is the flag's default version for the next round).
- **Best piece**: by overall BQXJ (new, slot 16, seed 139150) 'Symphonic Dance: Banners of the Dawn', 6.1 (quality
  lens); by masterpiece BPBB (new, slot 13, seed 139120) 'Hidden Rivers of the Dawn', 4.50. The round's best
  generated piece is the old code's BWQH (slot 10), 6.4 / 4.71. Below o18b's RFWG (7.3).
- **Fixes for the next set-plan round** (the flag stays off):
  1. **The long block**: merging and the 8-bar floor make long sections whose material does not move ("too long /
     static" 2.06 vs 0.75 lines per packet, life -0.32). A merged block needs an inner change: a new texture, a
     phrase-level variation or a key step at its join, not only more bars of the same.
  2. **Set memory on the key's mode**: at least 2 minor / modal pieces in 8, and no key three times in a set
     (key_apart is per time signature only). 139700's all-major programme lost 7 of 7.
  3. **Set memory on the realised bar plan**, not on the sections draw: two rondos in one set (and two plans that
     merge into the same 3|12|12|8|12) were heard as twins. Keep a layout unique per feel in a set and compare the
     section-length vectors after the merge.
  4. **The endings' dynamic**: alternate dissolving and loud closes across a set (set memory on the ending's
     loudness); 139700's new set ended loud six times in eight.
  5. **The climax ladder**: the rising one-step-per-bar sequence into the summit is the new named gesture (1.25 vs
     0.50); give it memory like the timpani pedal.
  6. The skeleton (soft intro, quiet middle, 8-bar brass-entry build, the tutti summit at 3/4, a coda) is named on
     both codes alike; the template flags did not fall this round. The next layer of the template is the order of
     the dynamic levels, not the gestures.
  7. Keep: the merges (no choppy sections), the fade cap, no crisis arc, the climax at 0.7+, the empty-role removal,
     no harp after the climax, the build memory (2 vs 16 timpani-pedal builds).
- **Reusing the set-level judgment** (`songs/_blind/set_round.py`, the docstring has the details):
  1. `run --code new=ROOT_A:setplan --code old=ROOT_B --set-seed S --n 8 --seed0 S --out DIR [--workers 2]` per set
     pair (a code is NAME=ROOT[:FLAG,...], ROOT a Windows path like D:/tmp/o20/code, the FLAGs shared_plan.py's).
  2. `dump --code ... DIR` per pair (the packets, in a child process with the code's flags).
  3. `deal ROUND JUDGE_ROOT DIR [DIR ...] --judges 7` (the judges' folders, the prompts, JUDGE_ROOT/SET_KEY.json);
     each judge agent reads its own folder's prompt.txt and writes JUDGE_ROOT/verdicts/<pair>_<judge>.md.
  4. `score JUDGE_ROOT/SET_KEY.json JUDGE_ROOT/verdicts --codes new,old` (the win rate with its CIs, variety /
     coherence, the same-again positions, the tells).
  - 3 pairs x 7 judges: 48 renders (plus the drops) and 21 judge agents of 2-5 minutes each.
## Round o21: FUGUE v2 on vs off - the fugato accompanied, its counter-subject heard, its subject the opening theme, strict paired, 16 slots (2026-10-18)

The second round on the shared FUGATO block: o19b's fix list (1-6) as one flag. docs/ORCHESTRA_ENDLESS.md "Round o21"
describes it.

- **FUGUE v2** (`symphony.FUGUE_ON` is now v2 = `FUGUE_ON_V1` + `'v2': FUGUE_V2`, `shared_plan.py --flag fugue`;
  o19b's is `--flag fugue1`; off is bit-identical):
  1. Never one voice alone. A pedal under each exposition entry (the entry's tonic, until the bass voice enters),
     a soft string pad until the third entry. The marks rise entry by entry (mp, mf, mf, f; capped under the
     climax by LOUDEST), and every voice gains 3 velocity steps per entry begun.
  2. The counter-subject heard: +3 velocity steps over the free voices (-6), doubled in its own colour (the
     texture's 'counter' role: clarinets / bassoons / oboes ...). A restatement that clashes is free counterpoint.
  3. The subject is the first theme's opening S bars as heard (`Writer.fsubject2`); a long landing is continued by
     fsubject's tail.
  4. Vivace capped at 12 bars and the scherzo at 6 compound bars (12 3/4 bars), the surplus to the dialogue (at
     most cap // 3 bars). The dance accompaniment (a staccato ostinato) stays under the entries:
     `fugue2_dance` / `fugue2_dance_winds`.
  5. The subject back at the summit (`Writer.fug_return`): in the bass, augmented x2 (the scherzo: as written),
     its start bar and octave by `voicing.cp_issues` against the climax's melody, `voicing.repair` within 2
     semitones.
  6. The entry spacing drawn (`gap`: the subject's length, + a codetta bar, - half a bar, - a bar for a 3-bar
     subject; an overlap only where subject and answer agree). In this round: 2 bars x 9, 3 bars x 6, 1.5 bars
     x 1.
  - Textures `fugue2_mixed` / `fugue2_horn` / `fugue2_reeds`: o19b's choirs + pedal, pad and counter.
- **The fugato count, and the forced plan.** Master's plan for seed 141000 (16 slots) has a fugato in only 7 of 16
  slots. The plan was forced for BOTH codes: dev = `fugato_dialogue` in slots 1, 2, 3, 6, 9, 11, 12, 14 and 16
  (`D:\tmp\o21\r\PLAN_141000_f.json`). **16 of 16 pieces hold a fugato**, and all 16 on-pieces have the subject
  back at the summit.
- **The protocol** (o19b's). One code (snapshot cb77459), the flag only, the same forced plan in both codes:
  - Best-of-1 on seed 141000 + 10 (k - 1). A gate reject would drop the slot for both: **0 dropped**, all 16
    slots passed on the first seed in both codes.
  - Two panels of 7 (the o14 lenses, JUDGE.md). The halves of a slot are in different panels (`deal --split`).
    The 3 hidden references (o18b's) and the masterpiece / missing questions. All 14 verdicts on the first launch,
    every judge reading only its own folder.
  - KEY `KEY_orch_o21.json`. The 32 mp3s, the KEY, SCORES.txt and SCORES_quality.txt are in
    `songs/_endless_orchestra/out/blind_o21/` (main checkout). Scripts, renders and verdicts are in D:\tmp\o21.
- **Checks before judging**:
  - The 24 protected hashes are bit-identical.
  - Flag off = master (812f07f) on 40 of 40 orchestra-symphonic pieces.
  - The full `python tests/run.py`: 77 modules, 1677 tests, 0 failed.

| new (on) - old (off), per slot over the lens pairs, n 16 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | +0.26 | +0.21 | +0.26 | +0.19 | +0.31 | +0.49 | **+0.38** | +0.14 | +0.14 |
| se | 0.10 | 0.08 | 0.11 | 0.13 | 0.12 | 0.15 | 0.13 | 0.07 | 0.11 |
| slots won / lost | 9/2 | 11/3 | 11/1 | 10/5 | 11/3 | 12/3 | 9/3 | 9/4 | 8/7 |

- **Per slot** (overall, raw, new - old):

  | Slot | Feel | New / old | Overall | Note |
  |---|---|---|---|---|
  | 001 | river | EVNJ / TYRS | +0.71 | forced; old: "the fugato begins with a solo first violin for four bars" |
  | 002 | allegro | KSMZ / DERX | +0.86 | forced; "the fugato S6 starts from the motto of bar 5" |
  | 003 | scherzo | VWZA / SBBW | +0.00 | forced; capped; then "the same 32-bar thin development slot" |
  | 004 | andante | QWXN / ZLAV | **+1.00** | the best generated packet (6.4); the turn motto "in canon ... as a fugato ... in the climax bass" |
  | 005 | river | TTNH / ENKH | +0.00 | old: "single lines with gaps and no counter-subject" |
  | 006 | andante | DJAH / JXWF | **+1.14** | forced; 6.3 |
  | 007 | allegro | GMXR / FEYR | -0.14 | "the middle runs figuration ... without carrying the motto" |
  | 008 | vivace | GUHD / EJFH | +0.29 | capped; "the horn starts a fugato on the motto"; "the climax drops the fugato subject" |
  | 009 | scherzo | LMHJ / CRMC | +0.00 | forced; capped; "a 28-bar development of thin two-part fragments" |
  | 010 | vivace | UPQR / TJLD | -0.29 | capped; "42 bars at 4.0-5.7 roles per bar, the fugato and its links" |
  | 011 | scherzo | AMNU / CKXQ | +0.00 | forced; capped; "the 32-bar development only sequences thin two-voice fragments" |
  | 012 | river | AFMD / HDPE | +0.57 | forced; "the thin fugato-like stretch ... give it a counter-subject" |
  | 013 | vivace | TRSL / RCCM | -0.14 | capped |
  | 014 | andante | DRDK / XCPM | **+1.43** | forced; old: "the cello-alone fugato"; new 6.3 |
  | 015 | river | JVZS / YHKT | +0.43 | |
  | 016 | andante | RATN / TMLR | +0.14 | forced |

  - The 9 forced slots: +0.54 mean; the 7 unforced: +0.16.
  - By feel: andante +0.93 (4 slots), river +0.43 (4), allegro +0.36 (2), vivace -0.05 (3), scherzo 0.00 (3).
    The capped fast pieces, the ones fix 4 aimed at, are level.
  - Normalised: +0.38 (se 0.11).
  - The lens pairs, overall: 51 won / 38 tied / 23 lost.
- **Packet means** (overall, all readings): on 5.17, off 4.79, references 7.12.
- **Masterpiece** (absolute, 1-10): on 3.72, off 3.58, references 5.57.
- **The merge bar** (overall > 2 se): +0.38 = **+2.9 se** (9 won / 3 lost). It passes: **MERGE**. Every dimension
  is up. Melody, harmony, form, orchestration and life (+0.49, 3.2 se) are each over 2 se; development (+0.19,
  1.5 se) and masterpiece (+0.14, 1.3 se) are not. Not merged here: the branch is left for the merge decision, and the flag stays
  off on master until it is merged and switched on.
- **Context only** (not for the decision - different code): pooled with o19b (v1), 32 slots: +0.32 se 0.10
  (3.2 se), 18 won / 7 lost.
- **What the judges say about the fugato** (`D:\tmp\o21\fugsent.py`: the verdict lines that match, per code;
  16 packets x 7 readings each side, references 3 x 14):

  | Pattern | On | Off | References |
  |---|---|---|---|
  | fugato / fugue / fugal | 14 | 59 | 6 |
  | imitation / entries / subject / answer | 37 | 49 | 11 |
  | counter-subject (all of them asked for, none praised) | 2 | 10 | 0 |
  | stretto | 8 | 1 | 1 |
  | counterpoint praise ("real counterpoint", "genuine imitation") | 0 | 4 | 0 |
  | pedal / accompanied | 89 | 85 | 14 |
  | episode | 12 | 11 | 5 |
  | lone / thin | 9 | 31 | 2 |
  | octaves / unison / parallels | 44 | 33 | 23 |
  | one pattern / long sequence | 14 | 8 | 2 |
  | modulation | 20 | 7 | 4 |
  | fugato / canon / stretto on the motto or opening | 12 | 11 | 2 |
  | augmented / in the bass at the climax | 6 | 2 | 0 |
  | the fugato subject named at the climax | 9 | 11 | 0 |

  - Lone / thin (fix 1): 31 -> 9. The off fugato draws "solo first violin for four bars", "the cello-alone
    fugato", "single lines with gaps", "no bass until bar 58". Most of the 9 new lines are elsewhere (openings,
    codas, the climax). In a fugato only DRDK's: "a lone violin line" over the B pedal, 4.1-4.6 roles per bar.
  - The counter-subject (fix 2): "no counter-subject" falls 10 -> 2 (AFMD, VWZA). No judge praises one by name.
    Its doubling may feed the octave / unison lines (44 vs 33).
  - The subject as the opening theme (fix 3): QWXN is read the way the fix intends - "the C#-D-C#-B-F# turn (bar
    1) is used everywhere - in canon ... as a fugato ... in the climax bass"; "the motto really is the piece". The
    word "fugato" itself falls (14 vs 59): the entries are read as the theme in imitation, canon or stretto (stretto
    8 vs 1) rather than as a separate fugato block.
  - The return at the summit (fix 5): it is heard in QWXN only ("augmented at the peak", "the motto in the
    bass"). Elsewhere the 4-bar augmented bass is missed: GUHD "the D major brass climax drops the fugato subject
    entirely"; climaxes "in parallel octaves" or "the motto restated unchanged" (EVNJ, GMXR, VWZA; QWXN's own "runs the motto in octaves for 13 bars").
  - The fast feels (fix 4): the three scherzo pieces (AMNU, LMHJ, VWZA) share one complaint: "the same 32-bar thin
    development slot" - the dialogue after the capped fugato (28-32 bars, 2-part fragments, 7 roles). All three
    tie.
  - The development: dev_own (the share of development bars on the piece's own material) falls, on 0.70 / off 0.76.
    The counterline-written counter-subject and the codettas are new material, but the judges' development
    dimension still rises (+0.19).
- **Best piece**: QWXN (on, slot 4, "Symphonic Dance: Rivers of Home", an F# minor andante) overall 6.4. It is
  level with the river reference (6.4); the references scherzo 7.4 and stormy 7.6. DJAH and DRDK (on) are 6.3.
  `blind_o21/QWXN.mp3`.
- **Fixes, next**:
  1. Make the return at the summit audible. It should run longer than 4 bars, in the low brass / horns as well as
     the basses, from the climax's first bar, and be marked in the dynamics. Or use `counterline` to set the subject
     against the climax melody, so the climax is a combination and not the motto in octaves.
  2. The scherzo / vivace development after the capped fugato is 28-32 bars of thin 2-part dialogue in both codes:
     put no surplus into it (drop the bars), or give the dialogue a third voice / the ostinato.
  3. Fewer unison doublings: double the counter-subject at the octave in a contrasting register, or not at all,
     and add dynamics marks instead.
  4. The fugato as a named event: a clear rest or cadence before the first entry, so the judges hear it as a
     fugato and not as texture.

## Round o22: SET_PLAN v4 on vs off - a change at every join, set memory on mode / key / bar plan / endings / ladder; per piece strict paired, 16 slots, plus 4 set pairs (2026-10-18)

o20's five fixes on the same flag. docs/ORCHESTRA_ENDLESS.md "Round o22" has the mechanics.

- **SET_PLAN v4** (`--flag setplan` is v4, `setplan3` o20's v3, `setplan2` o19a's v2; off and v3 are bit-identical
  to master on 40 of 40 symphonic pieces and 24 of 24 protected hashes):
  1. **A change at every join** (`JOIN_V4`): each merged block keeps its parts as their own material blocks in one
     song section, and `plan_blocks(change=)` never repeats the texture across the join.
  2. **Mode and key memory**: `key_max` 2 over all meters, `mode_quota` (2, 8), `major_run` 3.
  3. **The realised bar plan**: `form_seed` / `bar_plan`, `_set_bars` (no earlier slot shares > 0.4), a feel's
     layout once per set.
  4. **The endings alternate** (`end_alt`): no dissolve after a dissolve, no three loud in a row.
  5. **The ladder** (`FRAG_V4`): `Writer.sentence` steps by rise / wave / terrace / fall / arch, memory 3.
- **Protocol**: code snapshot 8685ab4, the flag only.
  - Per piece: seeds 143000 + 10 (k - 1), best-of-1, 16 slots, 0 drops, `deal --split` two panels of 7, 3 hidden
    references, KEY `KEY_orch_o22.json`.
  - Sets: 4 pairs of 8-piece sets (set seeds 143500 / 143600 / 143700 / 143800), 0 drops, 7 judges each = 28
    forced choices, KEY `KEY_orch_o22_sets.json`.
  - The full `python tests/run.py` before judging: 77 modules, 1686 tests, 0 failed.
- **Variety over the 16 slots** (on / off, `D:\tmp\o22\variety4.py`):

  | Measure | On | Off |
  |---|---|---|
  | Song sections: mean / over 12 | 9.6 / 0 | 10.5 / 1 |
  | Bar-plan similarity, worst per piece: mean / max | **0.366 / 0.50** | 0.614 / 1.00 |
  | Pairs over 0.4 | 4 | 14 |
  | Joins (all with a new texture) | 17 in 10 pieces | - |
  | Ladders of 4+ bars (pieces) / mean longest | 6 / 3.44 | 9 / 4.25 |
  | Texture similarity | **0.149** | 0.425 |
  | Template similarity | 0.436 | 0.474 |
  | Timpani-pedal builds | 4 | 16 |
  | Minor / modal pieces | 8 | 9 |
  | Keys: distinct / most repeated | 14 / 2x | 11 / F major 3x |
  | Longest loud-ending run | 2 | 3 |
  | Longest dissolving fade | 14 bars | 16 bars |

  Within-set bar-plan similarity over the set packets (`setlayout.py`): new 0.22 / 0.20 / 0.18 / 0.17 with 1 pair
  at or over 0.5; old 0.28 / 0.23 / 0.23 / 0.22 with 10 such pairs. Old set 143800 had a scherzo twin (pieces 2 and 6).

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | +0.02 | +0.00 | +0.09 | +0.03 | -0.07 | -0.04 | **+0.05** | -0.03 | +0.12 |
| won / tied / lost | 31/47/34 | 38/36/38 | 38/42/32 | 38/39/35 | 35/39/38 | 37/31/44 | 36/41/35 | 35/38/39 | 36/50/26 |

- **Per piece** (16 slots): overall +0.05 (se 0.21), +0.24 se; 8 slots won, 7 lost.
  - Best slots: 015 YYFC +1.57, 011 QDCT +1.14, 006 AGXQ +1.00. Worst: 009 and 010 at -1.29 each.
  - Andantes +0.75 (3 of 4 won, as in o20), allegros -0.20, scherzos -0.65.
  - Pieces with joins vs without: +0.01 vs +0.12, no difference.
- **Absolute scores**:
  - Packet means (overall): new 4.79, old 4.74, references 6.79.
  - Masterpiece: new 3.46, old 3.35, references 5.29.
  - Template flags per packet: new 35.0, old 40.6, references 18.3.
- **Tells** (verdict lines per packet, new / old / references):

  | Tell | New | Old | References |
  |---|---|---|---|
  | Timpani pedal | 0.44 | 2.56 | 0.67 |
  | Dominant pedal | 1.56 | 4.06 | 2.83 |
  | Same device / template | 0.81 | 1.75 | 0.33 |
  | Short / choppy | 0.12 | 0.50 | 0.17 |
  | Long / static | 2.00 | 2.00 | 0.67 |
  | Step sequence to the climax | **0.88** | 0.06 | 0.33 |

  The long-block complaint is level now (o20: 2.06 vs 0.75). The ladder is still named more on new.
- **The set-level judgment** (`D:\tmp\o22\r\SET_SCORES.txt`, 28 verdicts):

  | Set pair | New kept | Variety new / old | Coherence new / old |
  |---|---|---|---|
  | set143500 | 4 / 7 | 5.14 / 4.43 | 5.86 / 5.71 |
  | set143600 | **7 / 7** | 5.57 / 4.14 | 6.29 / 6.00 |
  | set143700 | **7 / 7** | 5.86 / 4.00 | 6.00 / 6.00 |
  | set143800 | 3 / 7 | 5.00 / 5.14 | 6.14 / 6.00 |
  | all | **21 / 28 = 0.750** | 5.39 / 4.43 (paired +0.96 se 0.26) | 6.07 / 5.93 (+0.14 se 0.10) |

  - **The forced choice**: 95 % CI Wilson 0.566-0.873, exact 0.551-0.893, p 0.0125. The CI lies above 50 %.
    Strength-signed mean +1.36 (se 0.43).
  - **Same piece again**: new at piece 5.82 on average, old at 4.64 (o20: 5.38 / 4.48).
  - **Caveat, order**: the programme read SECOND was kept 21 of 28. With new read second, new was kept 14 of 14;
    with new read first, 7 of 14. The order was balanced (14 / 14), so the 0.75 is the mean of the two
    conditions. The judges cluster by set pair, though: 2 pairs 7/7, 2 pairs split.
  - **What the judges named on new** (the next template layer):
    - The climax at 76-90 % in every piece.
    - Note-identical violins2 broken-chord accompaniments across pieces (e.g. "D4 F#4 D5 A3 A4 A5" in two pieces).
    - Two recurring openings: a held string chord, and running 16ths under a held note.
    - A shared theme-rhythm cell (pickup, long note, two steps down, leap).
    - The post-climax woodwind chorale coda.
- **Decision** (rule stated before the round: per piece not worse than -1 se AND the set CI above 50 %, or per piece
  > 2 se):
  - Per piece +0.24 se: met.
  - Sets 0.75, CI 0.55-0.89: met.
  - **MERGE: SET_PLAN v4 on by default.** Not merged here: master has since turned FUGUE v2 on (846a50f+), so the
    default switch needs the protected hashes re-checked on the new master.
- **Best piece**:
  - Of new: QDCT (slot 011) 'Symphonic Dance: Fires of the North' and AGXQ (slot 006) 'Rivers of the Sea', 5.6
    overall each. YYFC (slot 015) 'Wild Mountains of Winter' was the round's biggest paired win and the top
    masterpiece score (2.43).
  - The round's best generated piece is old ABNT (slot 010), 6.3.
- **Next fixes**:
  1. The climax position: vary it, earlier or withheld (76-90 % in every piece).
  2. Seedless shared accompaniment figures: the violins2 broken-chord pitches repeat verbatim across pieces.
  3. Opening memory: the held chord and the running 16ths under a held note.
  4. The theme-rhythm cell and the post-climax chorale coda.
  5. The ladder: still 0.88 vs 0.06 lines per packet, mostly in the peak block. Apply `FRAG_V4` to the
     reharmonised climax as well.
- **Files**:
  - The 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt and SET_SCORES.txt are in
    `songs/_endless_orchestra/out/blind_o22/`. A 5-piece listening set (v4 on, seed 145000) is in `listen_o22/`.
  - Scripts, renders and verdicts are in D:\tmp\o22.

## Round o23: TECH on vs off - the playing techniques as musical events with set memory; per piece strict paired, 16 slots, plus 4 set pairs (2026-10-24)

User feedback 2026-10-24: "techniques are missing, e.g. plucked strings". docs/ORCHESTRA_ENDLESS.md "Round o23" has the
mechanics.

- **Inventory** (all in publishable packs, nothing needs a non-publishable one):
  - SSO section strings: sustain, staccato/spiccato, marcato, pizzicato, tremolo, col legno, harmonics (not basses).
  - SSO brass: sustain / marcato / staccato only. VSCO2-CE adds FHornMute and TrumpetStraightMute (`MUTES`).
  - Also VSCO2-CE harp and timpani rolls; VPO section strings, brass accents, timpani roll.
  - Built from notes: trills, measured tremolo, walking pizzicato, harp glissando, stopped-horn stabs.
  - Not built: sul ponticello, con sordino strings, fp, portamento.
- **TECH** (`--flag tech`, default off; off is bit-identical to master on 40 of 40 symphonic pieces and 24 of 24
  protected hashes):
  - A palette of 13 techniques (`symphony.TECHNIQUES`), each tied to a block kind, a feel and a dynamic: pizz_choir
    (the `pizz_choir` texture), pizz_walk, trem_build, measured_trem, trill, harp_gliss, ww_chatter, muted_brass,
    stopped_horn, harmonics, col_legno, sfz and timp_roll.
  - A ranking per piece (`tech_rank`), drawn by the set plan with memory over the slot before and the one before that.
    4 are featured per piece, placed after the orchestration in free parts.
  - The muted and col legno / harmonics level offsets live in `orchestra.MUTES` / `TECH_GAINS`.
- **Protocol**: code snapshot e67bfff, the flag only.
  - Per piece: seeds 147000 + 10 (k - 1), best-of-1 (slot 15 on 147141: both codes' 147140 dropped by the gate),
    `deal --split` two panels of 7, 3 hidden references, KEY `KEY_orch_o23.json`.
  - The packets of both codes carry the articulation marks (`AGENTSOUND_PACKET_ARTS=1`), and the judges name the
    techniques they hear.
  - Sets: 4 pairs (set seeds 147500 - 147800), 7 judges each = 28 forced choices, reading order balanced
    (`deal --balance`), KEY `KEY_orch_o23_sets.json`.
  - The full `python tests/run.py` on the final code: 77 modules, 1690 tests, 0 failed. The off bit-identity was
    re-checked on the final code (40 / 40, 24 / 24).
- **Distribution** (16 pieces, % of notes, on / off):

  | Family | On | Off |
  |---|---|---|
  | Strings: sustain / staccato / spiccato | 62.3 / 18.0 / 6.8 | 66.9 / 20.9 / 5.3 |
  | Strings: pizzicato / tremolo / col legno / harmonics | **6.1** / 2.1 / **2.8** / 0.0 | 3.1 / 2.0 / 0 / 0 |
  | Violins 2 / violas / cellos pizzicato | 5.8 / 2.9 / 4.7 | 0 / 0 / 1.9 |
  | Woodwinds sustain / staccato | 91.3 / 1.9 | 92.8 / 0 |
  | Brass muted (horns) | 1.7 (3.4) | 0 |
  | Timpani roll | 3.2 | 1.6 |

  - Pieces per technique: stopped_horn 8, measured_trem 7, harp_gliss 7, trill 6, col_legno 6, ww_chatter 5,
    pizz_choir 5, sfz 4, timp_roll 4, trem_build 4, harmonics 3, pizz_walk 2, muted_brass 1.
  - 4 techniques in 15 pieces, 2 in one.
  - Audible: 70 events, 0 silent notes, 0 clicks. 5 events under 1 % of their section's energy (4 harp glissandi in
    tuttis, one clarinet chatter).
  - Muted horns are calibrated -3 dB under open; col legno was ~9 dB under staccato before `TECH_GAINS`.

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | +0.37 | +0.35 | +0.36 | +0.36 | +0.43 | +0.44 | **+0.42** | +0.19 | +0.34 |
| won / tied / lost | 53/35/24 | 54/33/25 | 56/30/26 | 52/32/28 | 61/28/23 | 50/39/23 | 56/35/21 | 42/45/25 | 47/47/18 |

- **Per piece** (16 slots): overall **+0.42 (se 0.15) = +2.8 se**, normalised +0.42 (se 0.14); 12 slots won, 4 lost.
  - Best slots: 014 MBGG and 016 WPAT +1.14 each, 012 CXAV and 015 LDMW +1.00.
  - Worst: 001, 006, 007 and 013 at -0.43 each.
- **Absolute scores**:
  - Packet means (overall): new 5.29, old 4.87, references 7.21.
  - Masterpiece: new 4.12, old 3.78, references 5.86.
  - Template flags per packet: new 44.5, old 44.0, references 9.3.
  - Best piece: MBGG (new, slot 014 "The Distant Fires") 6.6 overall, the only generated packet above 6.4.
- **Techniques the judges named** (share of the judge-packet answers, `TECH_NAMED.txt`; the `mute` match includes
  stopped horns):

  | Technique | New | Old | References |
  |---|---|---|---|
  | Pizzicato | 64 | 67 | 64 |
  | Tremolo | 62 | 55 | 67 |
  | Muted brass | **46** | 0 | 5 |
  | Col legno | **38** | 0 | 0 |
  | Glissando | **27** | 0 | 5 |
  | Trill | **24** | 0 | 0 |
  | Harmonics | **14** | 0 | 0 |
  | Spiccato / staccato | 48 / 37 | 41 / 47 | 86 / 38 |

  The old code's "pizzicato" is the bass line; the new one's is the pizzicato choir and the walking basses.
- **Sets**: new kept **28 of 28** (Wilson 0.88 - 1.00, exact 0.88 - 1.00), strength +2.39 (se 0.09).
  - By order: new read first 14 of 14, new read second 14 of 14 (Wilson 0.79 - 1.00 each). There is no order effect
    this time (o22: the programme read second was kept 21 of 28).
  - Variety new 5.14 / old 4.11 (+1.04 se 0.04). Coherence 6.57 / 6.21. "Same piece again" new at position 4.71,
    old at 4.14.
  - Every set judge says the two evenings share the same skeleton (forms, keys, climaxes) and only the colour
    differs. From about piece 4 on, the techniques return "as a checklist": the pizzicato interlude under a wind
    solo 3-4 times per set, col legno 3 times, a flute trill crowning two climaxes.
- **Decision: MERGE** (per piece +2.8 se > 2 se; the set CI is above 50 %).
- **Top fixes**:
  1. **The techniques carry the theme.** Col legno and the pizzicato choir are often "texture for its own sake"
     (GALA, LDMW, RAVU, RNCG, PJGA). Put the motto or a fragment on top, or let them accompany a theme statement.
  2. **Set memory over the whole set, per gesture.** No technique more than twice in 8 pieces; the climax crown
     (trill, glissando) is never repeated.
  3. **Harmonics** reach only 0.1 % of notes: give them a home (the dissolve endings, the nocturne).
  4. **Harp glissandi in tuttis** are under 1 % of the section energy: place them before the tutti or thin it.
  5. **The shared skeleton** (soft intro, staccato middle, tremolo build, marcato unison tutti at 78 - 85 %, coda)
     stays the main tell in sets and per piece (template flags 44 vs references 9).
- **Files**:
  - The 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt, SET_SCORES.txt, TECH_NAMED.txt and distribution.txt are
    in `songs/_endless_orchestra/out/blind_o23/`. A 5-piece listening set (TECH on, seed 149000) is in `listen_o23/`.
  - Scripts, renders and verdicts are in D:\tmp\o23.

## Round o24: SHAPE on vs off - the macro shape per piece with whole-set memory, TECH v2; per piece strict paired, 16 slots, plus 4 set pairs (2026-10-25)

o23's top fixes (the techniques carry the theme, whole-set technique memory, a home for the harmonics, harp glissandi
heard, and the big tell: one macro shape in every piece). docs/ORCHESTRA_ENDLESS.md "Round o24" has the mechanics.

- **SHAPE** (`--flag shape`, `genres.symphony_shape`, default off; off is bit-identical to master on 40 of 40 symphonic
  pieces and 24 of 24 protected hashes; the shared plan's other keys are master's, verified equal):
  - Per slot a drawn `{open, arc, climax, end}`: openings motto / solo / soft / in medias res / dance; arcs classic,
    mid (0.64-0.7), early (0.56-0.62, a second summit in the coda), late (0.86-0.9), twin (an f summit near 0.42),
    inverse (quiet); climaxes brass / strings / chorale / the new `apex_dialogue` / quiet; endings loud, cut (no coda),
    dying, surprise (f, then a pp coda). Set memory: no dimension as the slot before, caps per value, no repeated
    (open, arc, end); the realised peak is checked before an arc is accepted.
  - TECH v2: 3 techniques a piece, each at most twice a set, the pizzicato choir at most once per 3 slots, the trill
    crown once a set; the pizzicato choir and col legno carry the tune / the motto's head; harmonics on the soft
    endings and quiet chorales; the harp glissando only into the climax (the build thinned) or a soft arrival.
- **Protocol**: code snapshot cc405a5, the flag only (old = master 2204ef6 with TECH v1).
  - Per piece: seeds 151000 + 10 (k - 1), best-of-1 (slot 16 on 151151 after a spiky_track reject), `deal --split`
    two panels of 7, 3 hidden references, KEY `KEY_orch_o24.json`.
  - Sets: 4 pairs (set seeds 155500 - 155800; pair 155700 has 7 pieces), 7 judges each = 28 forced choices, order
    balanced, KEY `KEY_orch_o24_sets.json`.
  - The full `python tests/run.py`: 77 modules, 1694 tests; only test_voicing's timing check failed under the render
    load (it passes idle).
- **The 16 shapes drawn**: open medias 5, motto 4, soft 3, dance 2, solo 2; arc classic 4, late 3, mid 3, twin 3,
  early 2, inverse 1; climax dialogue 4, strings 4, chorale 4, brass 3, quiet 1; end cut 5, loud 5, dying 3,
  surprise 3.
- **Measured** (`macro.txt`: the loudest section's centre, LUFS relative to the median section):

  | | new | old |
  |---|---|---|
  | loudest centre, mean / sd | 0.76 / **0.077** | 0.77 / 0.038 |
  | in 0.70-0.85 | 10 of 16 | 16 of 16 |
  | first section vs median | **-0.9 LU** (10 at >= 0) | -4.3 LU (4) |
  | last section vs median | -0.8 LU (9) | -0.7 LU (9) |

  The 4 set pairs: sd 0.058-0.084 vs 0.037-0.049. The earliest realised peak is 0.63 (the early arc's 0.56-0.62 is
  never reached), and the endings did not change in loudness.
  - Techniques (`distribution.txt`): 3 a piece (old 4); harp_gliss in 5 pieces (old 10), pizz_choir 4 (7), col legno 3
    (1), harmonics 4 (3). Named by the judges (`TECH_NAMED.txt`, new / old): harmonics 27 / 19 %, col legno 19 / 6 %,
    glissando 29 / 54 %, trill 12 / 33 %, tremolo 61 / 79 %.

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.02 | +0.04 | -0.03 | +0.08 | -0.05 | -0.11 | **-0.09** | -0.03 | -0.03 |
| won / tied / lost | 40/28/44 | 31/52/29 | 38/36/38 | 36/41/35 | 27/51/34 | 30/44/38 | 36/36/40 | 32/44/36 | 32/46/34 |

- **Per piece** (16 slots): overall **-0.09 (se 0.20) = -0.45 se**; 7 slots won, 7 lost.
  - Best: 016 ZVHF (motto / inverse / quiet / surprise) +1.29, 009 NHKR and 011 MKMM +0.71.
  - Worst: 006 UHJB (soft / twin / strings / loud) -1.86, 002 XHBC (soft / early) -0.86.
  - By opening (small n): motto +0.32 (4), solo +0.36 (2), medias -0.14 (5), dance -0.36 (2), soft -0.67 (3); twin
    arcs -0.67 (3).
- **Absolute**: masterpiece new 3.96, old 3.99, references 6.17; generated overall 5.15 vs references 7.67.
  Template flags (the pairs the judges link, per packet of the version): new 88.9, old 105.6, references 0.3 - 16 %
  fewer links for the new code (this round's count is the linked pairs, not comparable with o23's 44).
- **Sets**: new kept **14 of 28** (Wilson 0.33 - 0.67), strength 0.00 (se 0.43). Pairs: 4 / 4 / 2 / 4 of 7.
  - By order: the programme read second kept 24 of 28 (new read first 2 of 14, new read second 12 of 14) - a strong
    order effect, back from o23's none.
  - Variety new 4.82 / old 4.75 (+0.07 se 0.24); coherence 6.46 / 6.54; "same piece again" new at position 4.39,
    old 3.68.
  - What the set judges still hear in both: every climax at 71-90 % as a marcato tutti with brass doubling octave
    violins, most pieces fading in a soft coda; in the new code the loud unison motto openings repeat piece 1's head
    rhythm (long-short-leap-short-long) and its harp-arpeggio S2; the staccato octave-bass ostinato under a woodwind
    tune in 3-4 pieces. In the old code: the harp glissando into every tutti (fixed by TECH v2: glissando named 29 vs
    54 %).
- **Decision: NOT MERGED** (per piece -0.45 se is inside -1 se, but the set CI is not above 50 %). The flag stays off.
- **Top fixes**:
  1. **The early / mid arcs must land**: the realised loudest section never comes before 0.63. Move the summit's
     material itself (not only the peak marks): the climax block and its build ahead, the second half a real
     wind-down; at least one in medias res piece whose opening IS the loudest music.
  2. **Endings by loudness, measured**: cut / loud endings are not louder at the end than the dying ones (last
     section -0.8 vs -0.7 LU). End on the summit (no coda, no fade) and check it on the render.
  3. **The opening theme's rhythm cell** is shared across the set (motto openings repeat piece 1's head and its S2
     texture): give the motto / the first theme's rhythm set memory.
  4. **The climax texture** (marcato tutti, brass in octaves with the violins) stays the tell; `apex_dialogue` and
     the chorale climax are not heard as different - make the non-unison climaxes audibly other (a canon, a brass
     chorale without the strings' tune, the tune in the low strings).
  5. **The staccato octave-bass ostinato under a woodwind tune** recurs in 3-4 pieces a set: give that accompaniment
     figure set memory.
  6. Keep: TECH v2's ration (glissando, the pizzicato choir) and the louder openings; re-test them alone on top of
     master if SHAPE is reworked.
- **Files**:
  - The 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt, SET_SCORES.txt, TECH_NAMED.txt, distribution.txt and
    macro.txt are in `songs/_endless_orchestra/out/blind_o24/`. A 5-piece listening set (SHAPE on, seed 153000) is in
    `listen_o24/`.
  - Scripts, renders and verdicts are in D:\tmp\o24.

## Round o24b: TECH2 alone (A) and SHAPE2 + TECH2 vs TECH2 (B) - o24 split; per piece strict paired, 16 slots each, plus 4 set pairs each with the two-pass set protocol (2026-10-25)

o24 mixed two changes. Here each one is judged on its own. A is TECH v2 alone on top of master. B is SHAPE2, o24's
top fixes 1-5 for the macro shape, judged as shape2 + tech2 against tech2 alone. docs/ORCHESTRA_ENDLESS.md "Round
o24b" has the mechanics.

- **The flags** (both default off; off is bit-identical to master: 40 of 40 symphonic pieces, 24 of 24 protected
  hashes):
  - **TECH2** (`--flag tech2`, `genres.symphony_tech2`): o24's TECH v2 drawn per set slot (`symphony.tech2_slot`,
    its own dice), with no macro shape.
  - **SHAPE2** (`--flag shape2`, `genres.symphony_shape2`):
    - The early (0.50-0.56) and mid (0.57-0.62) arcs move the climax's material: the development blocks go after the
      climax as its aftermath.
    - The cut ends on the climax, in hammered ff tutti chords. The loud ending's coda is at ff.
    - Own textures for the climax types: `apex_low`, `apex_chorale2`, `apex_dialogue2`.
    - Set memory on the motto rhythm, the first theme's texture and the pumping-bass figures.
- **Protocol**:
  - Code snapshot 0bedc7b, on the engine build of the round's start; master's later click fix is not in either arm.
    One shared PLAN per experiment, and B's TECH2 rankings are identical in both codes (16 of 16).
  - Per piece: A on seeds 157000 + 10 (k - 1), B on 158000 + 10 (k - 1). Best-of-1, `deal --split`: two panels of 7,
    3 hidden references.
  - Sets: 4 pairs each (A 159100-159400, B 159500-159800). The new two-pass protocol (`set_round.py deal --cleanse
    --two-pass`): 7 judges a pair, each reading twice with the labels swapped and the order reversed, plus a palate
    cleanser between the programmes. That gives 56 verdicts and 28 judges an experiment; the decision is on the AGREED
    judges.
  - The full `python tests/run.py`: 1706 tests, 0 failed.

### A: TECH2 alone vs master

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | +0.04 | +0.00 | +0.02 | -0.03 | +0.03 | +0.01 | **+0.03** | -0.03 | -0.01 |
| won / tied / lost | 39/41/32 | 38/41/33 | 38/41/33 | 37/41/34 | 34/47/31 | 37/38/37 | 41/36/35 | 26/56/30 | 38/39/35 |

- **Per piece**: overall **+0.03 (se 0.24) = +0.1 se**; 10 slots won, 6 lost. Best: 010 +1.57, 005 +1.14. Worst:
  009 -2.14, 015 -1.43.
- **Absolute**: masterpiece new 4.03, old 4.04, references 5.40. Template flags 27.9 vs 31.2 (references 15.3).
- **Techniques**: 3 a piece (old 4). Named by the judges (`TECH_NAMED.txt`, new / old): harmonics 23 / 5 %,
  glissando 12 / 25 %, muted brass 19 / 33 %.
- **Endings** (`endcheck.txt`, per bar LUFS): unchanged, as they should be. The peak is at 0.79 / 0.80 (sd 0.05), and
  the last 8 bars are -6.9 LU under the climax in both.
- **Sets** (56 verdicts): new kept **35 of 56** (Wilson 0.49-0.74).
  - Pass 1: 18 of 28. Pass 2: 17 of 28.
  - Agreement: 25 of 28 judges keep the same code in both passes.
  - **AGREED: new 16 of 25 = 0.64, Wilson 0.45-0.80** - not above 50 %.
  - By order: new read first kept 17 of 28, read second 18 of 28. With two passes the order effect is gone.
  - The result depends on the pair: 14 / 3 / 4 / 14 of 14.
  - Variety new 4.55 / old 4.29 (+0.27 se 0.12). Coherence 6.59 / 6.59.
  - What the judges hear: the same eight skeletons in both (keys, forms, climaxes at 71-89 %). The choice comes down
    to how the techniques are spread. Old's harp glissando into every climax and its pizzicato episodes lose. New's
    muted horn in many middle sections is its own tell.
- **Decision A: NOT MERGED** (+0.1 se per piece; the agreed set CI is not above 50 %). Neutral per piece, a small and
  pair-dependent set gain.

### B: SHAPE2 + TECH2 vs TECH2

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.25 | -0.34 | **-0.46** | -0.25 | -0.29 | -0.39 | **-0.39** | -0.12 | -0.27 |
| won / tied / lost | 31/39/42 | 25/43/44 | 21/43/48 | 30/38/44 | 27/40/45 | 21/41/50 | 26/38/48 | 29/41/42 | 29/38/45 |

- **Per piece**: overall **-0.39 (se 0.21) = -1.86 se**; 5 slots won, 9 lost.
  - Worst slots:
    - 012 (soft / mid / brass / dying) -2.21: "38 quiet bars after the climax at 65 %".
    - 016 (solo / classic / chorale / surprise) -1.86: the chorale climax is homorhythmic brass on stepwise lines.
    - 003 (medias / late / strings / cut) -1.43.
  - Best slot: 006 (medias / mid / strings / surprise) +1.0.
- **Absolute**: masterpiece new 3.88, old 4.14, references 4.93. Template flags 31.2 vs 32.8.
- **The 16 shapes drawn**:
  - Openings: soft 5, motto 5, medias 4, solo 2.
  - Arcs: late 5, twin 4, early 3, classic 2, mid 2.
  - Climaxes: 4 of each type.
  - Endings: loud 7, dying 4, surprise 3, cut 2.
- **Measured** (`endcheck.txt`):

  | | new | old |
  |---|---|---|
  | peak position, mean / sd | 0.74 / **0.139** | 0.80 / 0.049 |
  | peaks under 0.65 | **5 of 16** (min 0.46) | 0 (min 0.72) |
  | loud ending, last 8 bars vs climax (n 7) | **-2.6 LU** | -3.1 |
  | cut ending, last 8 bars vs climax (n 2) | **-2.0 LU** | -2.8 |
  | endings within 2 LU of the climax | 4 | 2 |

  The macro shape now really moves: early and mid peaks land at 0.46-0.62. The loud and cut endings sit at about 2 LU
  under the climax.
- **Sets** (56 verdicts): new kept **53 of 56** (Wilson 0.85-0.98), strength +2.34 (se 0.16).
  - Pass 1: 26 of 28. Pass 2: 27 of 28.
  - Agreement: 25 of 28.
  - **AGREED: new 25 of 25, Wilson 0.87-1.00.**
  - By order: new read first kept 25 of 28, read second 28 of 28.
  - Variety new 5.50 / old 4.27 (**+1.23 se 0.10**). Coherence 6.69 / 6.70.
  - The first round where the set judges clearly hear the shapes as different.
- **Decision B: NOT MERGED by the rule.** Per piece, -1.86 se is worse than -1 se, even though the set level is the
  clearest win so far. The set variety is bought with weaker single pieces: form -0.46 and life -0.39 are the biggest
  losses.

### Top fixes (for a SHAPE3)

1. **The aftermath after an early / mid climax is too thin.** The moved development blocks run f -> mp, so up to 38
   quiet bars follow the climax. Give it a second build, or a real return of the theme at f (a recapitulation that
   rises again), so the piece does not deflate after 0.6.
2. **The chorale climax is weak** (homorhythmic brass on stepwise lines). Give `apex_chorale2` a real tune (the
   motto's head in augmentation) and a moving bass, or draw it less often.
3. **The late / cut slots lost.** The cut's moved returns make the run-up long and the end abrupt. Keep the second
   theme's return before the climax short, and let the ff hammer chords be the motto's rhythm, not plain chords.
4. Keep: the moved material (the peak spread), the louder loud / cut endings, the set memory on motto / t1 texture /
   bass figures (variety +1.23). Re-test them on the new master (CHOIR v2, SOLO and COLOUR on) with fix 1.
5. TECH2 alone is neutral per piece and a small set gain. If the next round is SHAPE3 + TECH2, it can ride along.

- **Files**:
  - `songs/_endless_orchestra/out/blind_o24b/A/` and `B/`: the 32 mp3s each, the per-piece and set KEYs
    (`KEY_orch_o24b_{A,B}.json`, `KEY_orch_o24b_{A,B}_sets.json`), SCORES.txt, SCORES_quality.txt, SET_SCORES.txt,
    TECH_NAMED.txt, distribution.txt and endcheck.txt.
  - A 5-piece listening set (tech2 + shape2, set seed 157900, final code) is in `listen_o24b/`. The earlier render
    from before the cut fix is in `listen_o24b_precut/`.
  - Scripts, renders and verdicts are in D:\tmp\o24b.

## Round o25: SHAPE3 + TECH2 vs master (CHOIR v2 / SOLO / COLOUR on) - per piece strict paired, 16 slots, plus 4 set pairs with the two-pass set protocol (2026-10-25)

o24b's SHAPE2 won the set level clearly but lost per piece (-1.86 se). SHAPE3 adds o24b's three fixes on top of it and
is judged with TECH2 against master's defaults. docs/ORCHESTRA_ENDLESS.md "Round o25" has the mechanics.

- **SHAPE3** (`--flag shape3`, `genres.symphony_shape3`, default off; off is bit-identical to master 0b7dafb: 40 of
  40 symphonic pieces, 24 of 24 protected hashes). It is SHAPE2 (the moved climax material, the louder loud / cut
  endings, the set memory on motto / first-theme texture / bass figures) plus:
  - **The aftermath of an early / mid climax**: a release and a second build (f -> mp -> f), then a rising theme
    return at f in the driving tutti (`tutti_drive`).
  - **The chorale climax** (`apex_chorale3`): the brass chorale with the violins in the motto's rhythm and a walking
    bass.
  - **The late arc and the cut ending**: no second-theme return before the build, and the build at most 6 bars.
    The cut's chords are in the motto's rhythm (`hammer_motto`).
- **The interplay with CHOIR v2 / SOLO / COLOUR**, checked on all 16 slots built: every choir summit and every guest
  summit (organ, bells, celesta) sits on the moved peak block. The soloists avoid the climax and the tutti return.
- **Protocol**:
  - Code snapshot 2444565. new = `tech2,shape3`, old = the same snapshot without flags (= master: CHOIR v2, SOLO and
    COLOUR on, TECH v1).
  - Both arms on the click-fixed engine, rebuilt from master's sources in the worktree.
  - One shared PLAN; master's keys are equal in both plans (16 of 16).
  - Per piece: seeds 165000 + 10 (k - 1), best-of-1 (slots 4 and 7 on their second seed after an old-code gate
    reject). `deal --split`: two panels of 7, 3 hidden references, KEY `KEY_orch_o25.json`.
  - Sets: 4 pairs (set seeds 167100-167400). Two-pass deal (`--cleanse --two-pass`): 7 judges a pair, each reading
    twice with the labels swapped and the order reversed. That gives 56 verdicts from 28 judges; the decision is on
    the AGREED judges. KEY `KEY_orch_o25_sets.json`.
  - The full `python tests/run.py`: 81 modules, 1727 tests. Only test_voicing's timing check failed under the render
    load; it passes idle.
- **The 16 shapes drawn**:
  - Openings: motto 4, medias 4, solo 3, soft 3, dance 2.
  - Arcs: mid 4, twin 4, late 3, classic 2, early 2, inverse 1.
  - Climaxes: chorale 5, dialogue 4, brass 3, strings 3, quiet 1.
  - Endings: loud 7, dying 3, cut 3, surprise 3.
- **Measured** (`endcheck.txt`, per-bar LUFS):

  | | new | old |
  |---|---|---|
  | peak position, mean / sd | 0.71 / **0.144** | 0.79 / 0.045 |
  | peaks under 0.65 | **6 of 16** (min 0.46) | 0 (min 0.73) |
  | loud ending, last 8 bars vs climax (n 7) | **-2.5 LU** | - |
  | cut ending, last 8 bars vs climax (n 3) | **-1.1 LU** (fade -1.4) | - |
  | endings within 2 LU of the climax | 5 | 2 |
  | after the climax (pieces with >= 16 bars before the last 8): level / bars > 6 LU under | -3.8 LU / 7.7 (n 7) | -2.9 LU / 3.3 (n 3) |

  The release after a moved climax is still audible (about -19 LUFS against a climax of -11). The rising return is
  louder than in o24b: the listening set's piece 1 recap2 is at -14.2 LUFS, against -17.4 in SHAPE2.
- **Techniques** (`distribution.txt`): harp glissando in 6 pieces (old 11), pizzicato choir 4 (7), trill 0 (5),
  harmonics 6 (3). Named by the judges (`TECH_NAMED.txt`, new / old): tremolo 39 / 69 %, timpani roll 42 / 66 %,
  harmonics 31 / 17 %, glissando 14 / 24 %, trill 0 / 10 %.

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.01 | -0.01 | -0.01 | +0.11 | +0.04 | **+0.19** | **-0.06** | -0.06 | -0.03 |
| won / tied / lost | 31/47/34 | 33/44/35 | 31/45/36 | 39/40/33 | 34/41/37 | 38/48/26 | 29/44/39 | 25/54/33 | 28/54/30 |

- **Per piece** (16 slots): overall **-0.06 (se 0.18) = -0.33 se**; 7 slots won, 8 lost. o24b's form -0.46 and life
  -0.39 are gone: form -0.01, life +0.19.
  - Best: 012 (motto / early / strings / loud) +1.86, 002 (dance / mid / chorale / loud) and 003 (motto / classic /
    dialogue / dying) +0.43.
  - Worst: 015 (medias / early / dialogue / loud) -1.43, 009 (medias / twin / chorale / cut) -1.00, 006 (soft / mid /
    brass / loud) -0.71.
  - By shape (small n):
    - Openings: motto +0.43 (4), medias -0.61 (4).
    - Climaxes: strings +0.67 (3), chorale -0.11 (5), dialogue -0.43 (4).
    - Endings: loud +0.08 (7), cut -0.38 (3).
    - Arcs: early +0.22 (2), twin -0.39 (4).
- **Absolute**: masterpiece new 3.43, old 3.46, references 6.05. Template links (`flags.py`, the packets a judge
  links as the same template): new 13.3 a packet, old 14.2.
- **Sets** (56 verdicts): new kept **44 of 56** (Wilson 0.66-0.87), strength +1.30 (se 0.25).
  - Pass 1: 23 of 28. Pass 2: 21 of 28.
  - Agreement: 20 of 28 judges keep the same code in both passes.
  - **AGREED: new 18 of 20 = 0.90, Wilson 0.70-0.97** - above 50 %.
  - By order: new read first kept 18 of 28, read second 26 of 28.
  - Pairs: 14 / 5 / 13 / 12 of 14.
  - Variety new 5.52 / old 4.71 (**+0.80 se 0.13**). Coherence 6.84 / 6.88. "Same piece again" new at position
    5.91, old 4.75.
  - What the judges hear:
    - For new: the midpoint climax with an aftermath and a second build ("the most original formal stroke in either
      evening"), and fewer pizzicato-under-woodwind episodes.
    - Against new, in pair 167200 (old kept 9 of 14):
      - Two pieces open with the same brass fanfare (marcato horn call, trombone chord, timpani, crash, string
        tremolo; pieces 2 and 8).
      - Two neighbouring cut endings stop on the same hammered staccato brass (pieces 6 and 7).
      - Some judges miss old's later-placed climaxes being followed by a real coda.
- **Decision: MERGE** by the rule: per piece -0.33 se is not worse than -1 se, and the agreed set CI (0.70-0.97) is
  above 50 %. Not merged on the branch (the coordinator merges).
- **Top fixes** (a SHAPE4, or a polish):
  1. **Set memory on the opening's texture**: the in medias res / motto openings repeat one fanfare (the horn call
     over tremolo with a crash) in a set - draw the opening texture with the set's memory.
  2. **The cut ending at most once in 4 slots**, never next to another cut, and its texture varied (`hammer_motto` /
     `end_strokes` / a unison motto). Two cuts in a row on the same staccato brass are a tell.
  3. **The in medias res opening loses per piece** (-0.61, 4 slots; 015 and 009 are the worst): its loud first
     theme leaves the climax less room. Give it a quieter second section, or weight it down.
  4. **The dialogue and twin shapes are weakest** (-0.43, -0.39). The dialogue climax could take the motto-rhythm
     treatment that the chorale got.
- **Files**:
  - `songs/_endless_orchestra/out/blind_o25/`: the 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt,
    SET_SCORES.txt, TECH_NAMED.txt, distribution.txt and endcheck.txt.
  - A 5-piece listening set (tech2 + shape3, set seed 166000) is in `listen_o25/`.
  - Scripts, renders and verdicts are in D:\tmp\o25.

## Round p-div: PIANO_DIVERSE on vs off - the score as a gate, the most different near-tie, anti-template arc / endings / climax hands; per piece strict paired, 16 slots, plus 4 set pairs (2026-10-24)

**The switch** (`genres.piano_diverse(True)`, `shared_plan.py --flag pdiv`; off = master bit-identical; new-age-piano
only, jazz-piano shares `run.candidates` but is untouched):
- Selection (`run.diverse_pick`): the best-of-8 score becomes a gate (candidates more than 1.5 below the best are
  dropped; ~3 of ~7 pass), then the gated candidate farthest from the set memory wins (`run.diverse_distance`:
  key, mode, tempo, meter, layout, texture, climax LH, peak place / kind, ending, interlude, motif; decay 0.7 per
  piece back). Ties by score, then seed.
- Arc (`perform._diverse`, its own `Random("pdiv:seed")`): the peak placed early (52-62 %), golden (63-72 %) or late
  (75-85 %) by dropping / adding body sections and biasing their bars; at times a double peak (a B1 swell before) or a
  quiet peak (mp climax); the climax LH drawn from broad / surge / tenths / nocturne / rolled / drive (waltz: big /
  arp / open / roll / octave); six endings (roll, open, plagal, deceptive-then-tonic, a single line fading, a
  ritardando arpeggio); the interlude refitted from the head (fragment / augment / answer) instead of the intro copy.
- Bit-identity off: 16/16 new-age set slots, 8 plan-less seeds, the 24 protected hashes (8 genres), 8 orchestra slots.
  `tests/python/test_endless_pdiv.py` (5); full `python tests/run.py` 78 modules / 1695 tests pass.
- Measured (4 sets x 8): climax position of the chosen pieces 0.62-0.76 -> 0.55-0.78; 'broad' as the climax LH
  15/32 -> 3/32; mean chosen score 97.76 -> 97.22.

**Protocol**: the CLI's own set plan, best-of-8 (`--tries 8`), seeds 350000 / 351000 (per piece, 16 slots) and
350000-353000 (sets). Per piece: `--split` deal, two panels of 7 lenses, 3 hidden references (embers / tide /
longing), quality 1-10 + top fix + template flags. Sets: 8-piece programmes, 4 pairs x 7 judges, reading order
balanced. Keys: `KEY_newage_pdiv.json`, `KEY_newage_pdiv_sets.json`; mp3s + SCORES in
`songs/_endless_piano/out/blind_div/`.

**Per piece** (on - off, paired across panels, n 112):

| lens | melody | harmony | form | development | performance | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|
| on - off | -0.29 | -0.23 | -0.29 | -0.29 | -0.21 | **-0.38** | -0.17 | -0.29 |

Over the 16 slots: overall **-0.38 se 0.16 (-2.4 se)**, won / lost 6 / 10. Slots: 001 +0.57, 002 +0.43, 003 -1.00,
004 +0.14, 005 -0.86, 006 -0.43, 007 -1.14, 008 -0.86, 009 -1.57, 010 -0.29, 011 +0.14, 012 +0.43, 013 -0.57,
014 +0.14, 015 -0.29, 016 -0.86. Masterpiece on 4.19 / off 4.48 / refs 5.45; generated overall 5.71 vs refs 6.93.
Template flags per packet: on 29.06, off 29.44 (no change per piece).

Why the on pieces lost (the judges' top fixes):
1. The early peak lost its build: dropping A2 / A3 / the interlude before the climax left "no build" (BFAR, MFZF:
   climax at ~42 %).
2. The sparse climax hands (rolled2, broad2 blocks): "the climax sags, 2.1 attacks per bar" (LQLE).
3. Climaxes restating A1; weak heads - the diversity pick takes a near-tie that scores ~0.9 lower on average (e.g.
   slot 011 95.4 vs 98.7); a gate of 1.5 is inside the score's noise band but still costs.
4. More flat_dynamics rejects in the on arm (4 vs 1 in set 351000, caught by the audio gate).

**Set level** (28 verdicts): on kept **28 of 28** (Wilson 0.879-1.000, exact 0.877-1.000), strength 2.18 se 0.07;
order balanced (on read first 14 / 28, kept 14 / 14 either way). Variety on 5.04 / off 3.96 (paired +1.07 se 0.11),
coherence 6.71 / 6.50 (+0.21 se 0.08), "same piece again" at mean position 4.93 vs 3.71; tells per programme 8.54
vs 8.61. The judges: the two evenings are near-twins (same keys / tempi / section plans from the shared set plan); on
wins on varied climaxes and endings. Remaining set tells: the build always ending in LH 16ths / triplets, the
octave-pair climax LH, the 10-bar section plan.

**Decision: DON'T MERGE** (rule: per piece > 2 se, or not worse than -1 se AND the set CI above 50 %; per piece is
-2.4 se, so the set win alone does not carry it). The variety is real and strongly heard at the set level; the cost
is in the single pieces. Next: keep the build when the peak moves early (move post-climax material, never drop the
pre-climax sections), keep motion under every climax (drop rolled2 / broad2 or add inner 8ths), gate tighter (~0.8)
or weigh distance against score, then re-run the paired round.

## Round p-div2: PIANO_DIVERSE v2 on vs off - p-div's fixes (the build kept, running climax hands, a tighter weighed gate, a dynamics guard, the bloom's second stage drawn); per piece strict paired, 16 slots, plus 4 set pairs, fresh seeds (2026-10-25)

**What changed from p-div** (`perform.PIANO_DIVERSE_ON`, `run.diverse_pick`; off still master bit-identical: 16/16
new-age set slots, 8 plan-less seeds, 24 protected hashes, 8 orchestra slots, a full measure set's rows; full
`python tests/run.py` 78 modules / 1698 tests pass; `test_endless_pdiv.py` 8 tests):
1. The early peak: nothing before the climax is dropped or shortened any more (`PEAK_DROP['early'] = ()`,
   `_bias_bars` leaves the pre-climax sections as drawn); the sections after it grow (longest bars, an optional
   section added); early range 56-63 %.
2. The climax hands run: 4/4 big / nocturne / arc8 / rise8, 3/4 waltz_arp / barcarolle / waltz_arc (new figures
   `arc8`, `rise8`, `waltz_arc`); rolled2, broad2, octdrive, walk10, surge, the waltz's rolled / open / octave bars
   are out (no rest token, the bass octave at most once a bar - a test). The quiet summit is out.
3. The gate 0.8 (was 1.5), the distance less 0.06 per point under the best, and a dynamics guard: the pick's
   sub-scores on ph_vel / ph_vspread / vel_jump12 never more than 0.05 under the best's.
4. The bloom's second stage drawn per piece (`bloom2`): 16ths / triplets as before, 8ths throughout, or 16ths only in
   its last quarter.

Measured (4 sets x 8, seeds 300000-303000): chosen score 97.43 (master 97.76, p-div 97.22); climax_x of the chosen
0.62-0.80 (the early place barely moves the peak now - its median 0.68: the cost of keeping the build); climax hands
nocturne 10 / rise 8 / arc 7 / big 3 / waltz 4 of 32. In the judged sets the pick kept the best candidate in 23 of 28
diverse calls (the gate passes 1-2 of 8). flat_dynamics render rejects: on 0, off 1 (p-div: on 4, off 1).

**Protocol**: as p-div, fresh seeds: sets 370000-373000 (CLI set plan, best-of-8, `--tries 8`), per piece slots
001-016 = sets 370000 / 371000, two panels of 7 lenses, 3 hidden references, `--split`; sets 4 pairs x 7 judges,
the reading order balanced. Keys `KEY_newage_pdiv2.json`, `KEY_newage_pdiv2_sets.json`; mp3s + SCORES in
`songs/_endless_piano/out/blind_div2/`.

**Per piece** (on - off, n 112):

| lens | melody | harmony | form | development | performance | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|
| on - off | +0.21 | +0.09 | +0.14 | +0.17 | +0.18 | **+0.22** | +0.15 | +0.17 |

Over the 16 slots: overall **+0.22 se 0.24 (+0.9 se)**, won / lost 8 / 8 (p-div: -0.38 se 0.16, 6 / 10). Slots: 001
-0.14, 002 +1.00, 003 -1.14, 004 +1.43, 005 +0.57, 006 -0.29, 007 +0.71, 008 -0.43, 009 +1.57, 010 -0.57, 011 -1.29,
012 -0.29, 013 +0.71, 014 -0.29, 015 +0.14, 016 +1.86. Masterpiece on 4.49 / off 4.32 / refs 4.83; generated overall
5.72 vs refs 6.36. Template flags per packet: on 27.81, off 33.50, refs 14.33 (p-div: 29.06 / 29.44) - the on pieces
read as less of one formula.
The on losers: 003 GHVJ - the climax only the A1 head at forte, a static A1; 011 NDBW - an early peak (56 %) with a
long quiet tail after it, and a double peak whose B1 already reaches v106 ("the climax has nowhere to go").

**Set level** (28 verdicts): on kept **19 of 28** = 0.68 (Wilson 0.493-0.821, exact 0.476-0.841, p 0.087) - the CI
does NOT clear 50 %. Strength +0.82 se 0.38. A strong order effect: the programme read second kept 23 of 28 (on read
second 14 / 14, on read first 5 / 14). Pairs: A 4 / 7, B 3 / 7, C 5 / 7, D 7 / 7. Variety on 4.50 / off 4.18 (paired
+0.32 se 0.19; p-div +1.07), coherence 6.71 / 6.75, "same piece again" at 4.57 vs 4.04, tells 8.29 vs 8.46. The
judges: "the two evenings share half their music" - with the gate at 0.8 the pick mostly keeps the best candidate, so
on and off play the same tunes; on wins on its endings, flowing climaxes and the odd surprise (a forte first wave, a
new key area), not on a different programme.

**Decision: DON'T MERGE** (rule: per piece > 2 se, or per piece >= -1 se AND the set CI above 50 %; per piece +0.9 se
passes the first half, the set CI 0.49-0.82 misses by a hair). The trade-off is now clear: p-div's wide gate won the
set (28 / 28) and lost the piece (-2.4 se); p-div2's tight gate fixed the piece (-0.38 -> +0.22) and gave most of the
set win back, because the variety came from choosing other candidates. Next (p-div3): keep p-div2's draws, widen the
gate again (~1.2) under the weighed distance and the dynamics guard, so the pick changes the tune in about half of the
slots; the first wave at mf, not f (NDBW); the early place only with a long build (or out); then the same strict round.

## Round oc1: CHOIR on vs off - a real SATB choir (vocalset-choir) as events of the form; per piece strict paired, 16 slots, plus 4 set pairs (2026-10-25)

User feedback (HUMAN_FEEDBACK, 2026-10-24): the choir as the orchestra's goosebump lever. docs/ORCHESTRA_ENDLESS.md
"Round oc1" has the mechanics.

- **Pack**: `vocalset-choir` (SATB wordless vowels ah / oh / oo, p / mf / f layers, from the 20 VocalSet singers,
  CC BY 4.0; the credits print the VocalSet attribution). The DiffSinger choir packs (NC) are never used.
- **CHOIR** (`--flag choir`, default off; off is bit-identical to master on 40 of 40 symphonic pieces and 24 of 24
  protected hashes):
  - `endless/choir.py` on the shared primitives: `orchestra.vocalset_choir` (one sfz track per part and vowel, the
    hall send) -> `orch.Choir` (lane 'dynamics' = the CC1 layer crossfade, early speaking starts, messa di voce) ->
    `Score.sing`; SATB voicing by `voicing.voice` under a soprano taken from the piece's most singable line. Ranges
    S C4-G5, A A3-D5, T C3-G4, B A2-D4 (inside the pack's ranges).
  - Plans drawn per piece by the set plan with memory (`set_choir`; never "none" twice in a row, a share penalty on
    the summit): none, summit (a soft `lead_in` "oo" then the theme / chorale on "ah" at the climax arrival),
    acappella (4-8 bars of the choir alone over at most a bass pedal at -8 dB, oo -> oh -> ah, before the final build,
    then the summit), halo ("oo" over the quietest chorale-like block), coda ("ah", soft "oh/oo" at -5 dB), and the
    halo + summit / halo + coda pairs.
  - Phrases of 4 bars with breath gaps (0.32 s), long notes re-attacked staggered per part, the vowel per phrase
    moving oo -> ah toward the peak. The pack's layers are level-matched, so the level is an expression lane from the
    velocity (`CHOIR['level']`) plus per-event offsets; gain -7.5 dB, its own send into the same hall.
  - The packets show the choir as choir_S / A / T / B with the vowel per attack (`make_packets_orch`).
- **Protocol**: code snapshot c7c38ac, the flag only.
  - Per piece: seeds 155000 + 10 (k - 1), best-of-1 (slots 11 and 15 moved on: 155100 / 155140 dropped by the gate in
    both codes), `deal --split` two panels of 7, 3 hidden references, KEY `KEY_orch_oc1.json`; packets audio-derived
    with the articulation marks (`AGENTSOUND_PACKET_ARTS=1`) as in o23; the judges answer a `choir:` line.
  - Sets: 4 pairs (set seeds 155500 - 155800), 7 judges each = 28 forced choices, reading order balanced, KEY
    `KEY_orch_oc1_sets.json`.
  - The full `python tests/run.py` on the final code: 77 modules, 1693 tests, 0 failed.
- **Distribution** (16 pieces): a choir in 11 (69 %; 74.5 % over 200 dry plans): acappella 3, summit 4, coda 1,
  halo 1, halo + coda 2, none 5. Events: summit 7, lead_in 4, acappella 3, coda 3, halo 3; vowels oo 13, ah 8, oh 4.
  - 0 silent notes, 1 click (not the choir), no choir warnings. Share of the section's energy: summits 13-29 %,
    acappella 9-22 %, halos 20-27 %, codas 21-47 % (010's soft coda 46.7 %); one lead-in under 5 % (3.8 %).

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | -0.12 | -0.07 | -0.05 | -0.18 | +0.00 | -0.04 | **-0.02** | -0.04 | -0.06 |
| won / tied / lost | 29/44/39 | 28/50/34 | 35/40/37 | 36/34/42 | 34/47/31 | 31/43/38 | 38/34/40 | 31/50/31 | 32/41/39 |

- **Per piece** (16 slots): overall **-0.02 (se 0.15) = -0.1 se**, normalised -0.02 (se 0.15); 10 slots won, 5 lost.
  - Best: 001 NVQF (acappella + summit) and 009 JSKR (acappella + summit) +0.86.
  - Worst: 004 PVCX (coda) and 015 LPSN (no choir) -1.14, 013 LMAS (halo + coda) -0.86.
  - The 5 slots without a choir have packets identical to old (the choir draw has its own rng; LPSN = DZMA byte for
    byte), so their -0.20 mean (-1.14 to +0.29) is the panels' noise. The 11 choir slots: +0.07; a cappella +0.43
    (3), summit +0.18 (4), halo / coda -0.32 (4).
- **Absolute scores**: overall generated 5.25 (new and old within 0.02), references 6.86. Masterpiece new 3.73, old
  3.79, references 5.17. Template flags per packet new 67.8, old 77.0, references 21.7.
- **Choir named** (`CHOIR_NAMED.txt`): in 77 of 112 new answers (69 %, = the share of pieces with a choir), 0 of the
  old, 0 of the references. Praised: the a cappella transitions (JSKR "a cappella transition (good)"), YSNS's SATB
  "ah" carrying the theme to G6 ("the emotional core"), SHBM's serene oh / oo chorale ending. Criticised: the summit
  "ah" only doubles the brass ("routine", MUTP, ZXQD, JSKR, KNYT), "vowels, not a phrase" (NVQF), and twice "the
  choir is listed in S9 but has no notes" (PVCX, SHBM) - a packet bug, see fix 4.
- **Sets**: new kept **28 of 28** (Wilson 0.88 - 1.00, exact 0.88 - 1.00), strength +2.07 (se 0.05).
  - By order: new read first 14 of 14, new read second 14 of 14 (Wilson 0.79 - 1.00 each); no order effect.
  - Variety new 4.93 / old 4.21 (+0.71 se 0.09). Coherence 6.50 / 6.36. "Same piece again" new at 4.07, old 3.89.
  - Every set judge sees that the two evenings are the same scores note for note plus the choir, so the choice is
    "the same evening with one more colour" (strength 2, "a small edge"). From about piece 4 on, the choir itself
    becomes a routine: "a soft [oo] preview, then [ah] doubling the final tutti" at 75-90 % of the piece, on the
    same cue every time.
- **Decision: MERGE** by the rule (per piece -0.1 se, not worse than -1 se; the set CI 0.88 - 1.00 is above 50 %),
  with the caveat that the set win is a colour win on identical scores, while per piece the choir did not lift the
  music. Keep the default off until fix 1-2 land, or switch it on as a colour lever.
- **Top fixes**:
  1. **The choir sings the theme, not the tutti's chords.** The summit "ah" doubles the brass homophonically; give
     it the motto / the chorale melody in the soprano with its own rhythm, the orchestra thinned under it
     (`_line` picks the line, but the S part follows the top of the chords too often).
  2. **Set memory per gesture.** The lead_in "oo" -> summit "ah" pair is the formula: at most twice per set, and the
     choir sometimes at a non-climax (the second theme, the development's quiet core, the opening).
  3. **The a cappella wins** (both best slots): more of it (with the summit after it), and the halo / coda events
     (the worst slots 004, 013) need a phrase, not held vowels.
  4. **Packet bug**: the orchestration line counts the choir's early speaking start (beat 0.83 of the next bar)
     in the section before, while the notation (EARLY) puts it into the next bar - use the same EARLY shift in both.
  5. The shared skeleton (template flags 68 / 77 vs 22) stays the main tell.
- **Files**:
  - The 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt, SET_SCORES.txt, CHOIR_NAMED.txt and distribution.txt
    are in `songs/_endless_orchestra/out/blind_oc1/`. A 5-piece listening set (CHOIR on, set seed 156000) is in
    `listen_oc1/`.
  - Scripts, renders and verdicts are in D:\tmp\oc1.

## Round p-div3: PIANO_DIVERSE v3 on vs off - gate 1.2 weighed, the first wave at mf, no early place, the sung climax varied; set judges with a palate cleanser; per piece strict paired, 16 slots, plus 4 set pairs, fresh seeds (2026-10-25)

**What changed from p-div2** (branch `pdiv3` from master 2aca085, which carries p-div2 with the flag off; off still
bit-identical: the pre-merge master 97a7ecd = the merged master = this branch on 16 new-age set slots, 8 plan-less
seeds, 24 protected, 8 orchestra slots; full `python tests/run.py` 78 modules / 1702 tests pass):
1. The gate 1.2 (was 0.8), 0.02 a point under the best (was 0.06), the dynamics guard kept: measured on 4 sets, the
   pick plays another tune in 12 of 28 slots with a memory (p-div2: 4, p-div: 16); chosen score 97.46 (master 97.76).
2. The first wave (kind 'double') at mf (was f; p-div2's NDBW: "the climax has nowhere to go").
3. No early place (golden / late only).
4. The sung climax varied: where the set slot pins the head as written in octaves / chords (or nothing), the piece
   draws 'sequence' / 'reharm' / 'canon' (`PIANO_DIVERSE_ON['anthem']`; p-div2's slot 003: "the climax only
   restates the A1 head at forte").
5. Set level: `pdiv_round.py sets ... --cleanse` - JUDGE.md tells each judge the order is random, that earlier judges
   kept the second programme four times in five, and to write notes on the first programme before opening the
   second, re-read both before choosing and name one point where the programme not kept is better (all 28 judges
   wrote both notes files).

**Protocol**: as p-div2, fresh seeds: sets 380000-383000, per piece slots 001-016 = sets 380000 / 381000. Keys
`KEY_newage_pdiv3.json`, `KEY_newage_pdiv3_sets.json`; mp3s + SCORES in `songs/_endless_piano/out/blind_div3/`.

**Per piece** (on - off, n 112):

| lens | melody | harmony | form | development | performance | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|
| on - off | -0.41 | -0.36 | -0.33 | -0.33 | -0.23 | **-0.40** | -0.21 | -0.31 |

Over the 16 slots: overall **-0.40 se 0.16 (-2.5 se)**, won / lost 6 / 10. Slots: 001 -0.29, 002 +0.14, 003 -0.86,
004 +0.43, 005 +0.43, 006 -0.71, 007 -0.86, 008 -0.57, 009 +0.14, 010 +0.14, 011 -1.00, 012 +0.29, 013 -0.71,
014 -0.71, 015 -0.43, 016 -1.86. Masterpiece on 4.24 / off 4.55 / refs 5.31. Template flags per packet on 37.6 /
off 44.0 / refs 8.3. flat_dynamics render rejects on 1 / off 2.
Where it lost: the 9 slots that played the SAME tune as off lost -0.49 on average, the 7 with another tune -0.28 -
the loss is the arrangement draws, not the selection. New in p-div3 among them: the varied anthem (reharm -0.54,
canon -0.40, sequence -0.33 by slot); the judges' fixes on the losers: HTXL "the 16-bar climax has 2.2 right-hand
attacks a bar, mostly held notes" (the varied anthem drops the octave / chord climax texture of _texture's
'octaves' / 'chords'), HMTP / FNRZ the form (an A3 copying A2, a short climax with a long tail), weak static heads.
p-div2's same arrangement draws without the anthem change were +0.22.

**Set level** (28 verdicts, the cleanser): on kept **17 of 28** = 0.61 (Wilson 0.424-0.764, exact 0.406-0.785,
p 0.34) - not above 50 %. Strength +0.54 se 0.40. The order effect smaller but there: the programme read second kept
21 of 28 (p-div2: 23 of 28); on read first 5 / 14, on read second 12 / 14. Pairs A 5, B 1, C 7, D 4 of 7. Variety on
4.54 / off 4.04 (+0.50 se 0.17), coherence 6.57 / 6.64, "same piece again" at 4.39 vs 3.86, tells 8.64 vs 8.46.

**Decision: DON'T MERGE** (per piece -2.5 se: worse than -1 se; the set CI 0.42-0.76). The three rounds:

| round | gate | per piece (se) | sets kept (Wilson) | read second kept |
|---|---|---|---|---|
| p-div | 1.5 | -0.38 (0.16) | 28 / 28 (0.88-1.00) | 14 / 28 |
| p-div2 | 0.8 + weigh | +0.22 (0.24) | 19 / 28 (0.49-0.82) | 23 / 28 |
| p-div3 | 1.2 + weigh, anthem varied | -0.40 (0.16) | 17 / 28 (0.42-0.76) | 21 / 28 |

Next: p-div2's draws were the only per-piece win - revert the anthem override (or keep the octave / chord texture
under a sequenced / reharmonised statement: the climax needs its density), keep gate 1.2; p-div's 28 / 28 came with
equal reading order (14 / 28) - the later set judgements are order-driven, so the set level should keep the
cleanser and add a second pass with the order swapped per judge.

## Round oc2: CHOIR v2 vs choir off - the theme sung, the gestures' set memory, more a cappella, sung halos / codas; per piece strict paired, 16 slots, plus 4 set pairs (2026-10-25)

Round oc1's top fixes 1-4. docs/ORCHESTRA_ENDLESS.md "Round oc2" has the mechanics.

- **CHOIR v2** (`--flag choir2` = `genres.symphony_choir(True, v2=True)`: `choir.CHOIR_V2` on top of `CHOIR_ON`;
  v1 `--flag choir` unchanged; off bit-identical to master on 40 of 40 symphonic pieces and 24 of 24 protected
  hashes):
  1. **The theme sung**: the peak's melody (a `melody` part first) in its own rhythm (notes under 0.2 s join, not
     0.42 s). The summit's texture is drawn per piece: `unison` (60 %: the theme in sopranos and tenors in octaves,
     alto / bass the harmony per chord) or `hymn` (40 %: harmonised SATB). 40 % of summits on 8+ bar peaks enter at
     the peak's second half. The brass / woodwind parts doubling a line play 12 / 6 velocity steps softer under it.
  2. **The gestures' set memory**: an event at most 3 (summit, a cappella), 2 (halo, coda) or 1 (lead-in) times in
     any 8 slots, x 0.7 per earlier use; the lead-in only in the rare `swell` plan.
  3. **More a cappella** (`acappella` 1.2, new `acappella_coda` 0.7; +3.5 dB) and **sung phrases**: the halo sings
     the quiet block's line (its instrument 14 steps softer), codas / a cappellas fall back to any upper line.
  4. **Packet fix**: the orchestration / roles-per-section lines count an attack in the bar the notation prints it.
- **Protocol**: code snapshot 519767a, choir2 vs off.
  - Per piece: seeds 161000 + 10 (k - 1), best-of-1 (all 16 slots passed on the first seed), `deal --split` two
    panels of 7, 3 hidden references, KEY `KEY_orch_oc2.json`, packets with articulation marks, a `choir:` answer.
  - Sets: 4 pairs (set seeds 161500 - 161800), 7 judges each = 28 forced choices, reading order balanced, KEY
    `KEY_orch_oc2_sets.json`. One engine build for both arms throughout.
  - The full `python tests/run.py`: 78 modules, 1707 tests, 0 failed.
- **Distribution** (16 pieces): a choir in 10 (62.5 %; 65.8 % over 30 dry sets): acappella 3, acappella_coda 1,
  halo_coda 2, halo_summit 1, summit 2, coda 1, none 6. Events: summit 6, a cappella 4, coda 4, halo 3 (lead-in 0).
  Summit textures: hymn 5, unison 1 (the draw's bad luck: 3.7 % at 60 / 40); one late entry.
  - 0 silent notes, 0 clicks, no choir warnings; no event under 5 % of its section's energy (oc1: 1). Shares:
    summits 10-27 %, a cappellas 7-21 %, codas 13-33 %, halos 8-57 % (015's halo is the 8 s intro, 42 %).

| new - old, n 112 | melody | harmony | form | development | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|
| mean | +0.14 | +0.19 | +0.18 | +0.12 | +0.15 | +0.11 | **+0.18** | +0.06 | +0.13 |
| won / tied / lost | 39/36/37 | 45/34/33 | 44/31/37 | 44/29/39 | 42/42/28 | 45/28/39 | 43/33/36 | 31/58/23 | 42/37/33 |

- **Per piece** (16 slots): overall **+0.18 (se 0.18) = +1.0 se**, normalised +0.18 (se 0.22); 8 slots won, 7 lost
  (oc1: -0.02).
  - The 6 slots without a choir have byte-identical packets (noise): -0.07. The 10 choir slots: **+0.33** (se 0.24);
    a cappella +0.52 (3: +1.43, -0.43, +0.57), acappella_coda +0.29, halo_coda +0.50, halo_summit +1.14, coda +0.43,
    summit only -0.57 (2: -0.71, -0.43).
  - Best: 001 KHNB (a cappella + summit) +1.43, 002 CYLW (halo + coda) and 004 JNXR (halo + summit) +1.14.
- **Absolute scores**: overall new 5.37 / old 5.19 (generated 5.28), references 7.02. Masterpiece new 4.03, old 3.89,
  references 5.48. Template flags per packet new 47.8, old 48.2, references 14.7.
- **Choir named** (`CHOIR_NAMED.txt`): in 70 of 112 new answers (62 %), 0 old, 0 references. The a cappella is the
  praised moment again ("the most beautiful quiet moment of the set", "a real lift"), and so are the sung codas ("the
  payoff of the piece") and the soft "oo" chorales on the second theme. The summit still reads as "doubling the
  tutti / brass" in most answers ("weight, not lift", "mass rather than a new voice"): with 5 of 6 summits `hymn`,
  the sung theme is also played by the violins / horns, so the judges hear a doubling.
- **Sets**: new kept **28 of 28** (Wilson 0.88 - 1.00, exact 0.88 - 1.00), strength +2.11 (se 0.06).
  - By order: new read first 14 of 14, new read second 14 of 14 (Wilson 0.79 - 1.00 each).
  - Variety new 5.25 / old 4.39 (+0.86 se 0.07; oc1 +0.71). Coherence 6.57 / 6.54. "Same piece again" new at 4.25,
    old 3.89.
  - The judges again see the same scores plus the choir. Praised: the near a cappella hush, the "oo" hymn, the sung
    theme in the codas. Criticised: the choir "pushed into almost every tutti climax" (3 of 8 pieces per set), "a
    routine ff 'ah' doubling" from piece 3 on.
- **Decision: MERGE and DEFAULT ON** by the rule (per piece +1.0 se >= 0 and not worse than -1 se; the set CI
  0.88 - 1.00 above 50 %; the user wants the choir). Not switched in this branch: switch `symphony_choir(True,
  v2=True)` on as the default on master and re-check the protected hashes (the symphonic hashes change by design).
- **Top fixes**:
  1. **The summit: the choir alone on the theme.** At the sung theme's bars the orchestra's melody instruments
     (violins1 / horns / trumpets) leave the theme (counter-line, held harmony or rest), so the choir is the voice,
     not a doubling; and `unison` more often (or always the first sung statement).
  2. **Fewer summits, more inner events**: cap the summit at 2 per 8 slots; more a cappella / halo / coda (the
     events that score +0.3 to +1.1; summit-only -0.57).
  3. **The halo in a real block**: not the 8-s intro (015); at least 4 bars of a line.
  4. **Master bug** (not the choir): set seed 162000's slot 2 (andante C# minor variations, seeds 162004-162007)
     fails the click gate in every candidate with the choir off too - violins2 at bar 76 beat ~2.1, a one-beat swell
     lane (0 -> 0.19 -> 0.01) on a note ending there.
- **Files**:
  - The 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt, SET_SCORES.txt, CHOIR_NAMED.txt and distribution.txt
    are in `songs/_endless_orchestra/out/blind_oc2/`. The listening set (CHOIR v2, set seed 162000: pieces 001,
    003-006; slot 2 fails the click gate in both codes, see fix 4) is in `listen_oc2/`.
  - Scripts, renders and verdicts are in D:\tmp\oc2.

## Round p-div4: PIANO_DIVERSE v4 on vs off - p-div3 without its varied climax; two-pass set judging (each judge twice, the order swapped); per piece strict paired, 16 slots, plus 4 set pairs x 7 judges x 2 passes, fresh seeds (2026-10-25)

**The switch** (branch `pdiv4` from master 8c46c89): p-div3's draw of the sung climax's statement reverted (the set
slot's octaves / chords / sequence / reharm / canon plays again); kept: p-div2's draws (the build kept, running
climax hands, the bloom's second stage), the gate 1.2 with 0.02 a point, the dynamics guard, the first wave at mf, no
early place. Off bit-identical (the merged master 2aca085 = this branch on the 56 protected / set / orchestra
pieces); full `python tests/run.py` 79 modules / 1708 tests pass.

**Two-pass set judging** (reusable: `set_round.py deal ... --cleanse --two-pass`, `pdiv_round.py sets ... --cleanse
--two-pass`; `set_round.second_pass`, `deal_judge`, `two_pass_lines`; `tests/python/test_set_round.py`): every judge
also judges the pair as `<judge>__p2` - a fresh agent, the codes relabelled (X / Y swapped) and the other programme
read first, the palate cleanser in both. `score` prints per pass, the agreement rate and the AGREED result (a judge
counts only when both passes keep the same code).

**Protocol**: as p-div3, fresh seeds 390000-393000 (per piece = sets 390000 / 391000). Keys `KEY_newage_pdiv4.json`,
`KEY_newage_pdiv4_sets.json`; mp3s + SCORES in `songs/_endless_piano/out/blind_div4/`.

**Per piece** (on - off, n 112):

| lens | melody | harmony | form | development | performance | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|
| on - off | -0.10 | +0.04 | -0.33 | -0.04 | -0.16 | **-0.22** | -0.01 | -0.17 |

Over the 16 slots: overall **-0.22 se 0.22 (-1.0 se; normalised -0.22 se 0.25, -0.9 se)**, won / lost 5 / 10.
Slots: 001 -0.14, 002 +0.29, 003 -0.86, 004 +1.00, 005 0.00, 006 -0.29, 007 +0.14, 008 -0.57, 009 -0.71, 010 -1.57,
011 -0.43, 012 -0.86, 013 +1.57, 014 +1.00, 015 -0.43, 016 -1.71. Masterpiece on 4.28 / off 4.45 / refs 5.21.
Template flags per packet on 47.5 / off 43.9. Same tune as off in 7 slots (-0.12), another tune in 9 (-0.30).
flat_dynamics rejects on 4 / off 3. The losers: RURD (016) "the climax keeps the verse's 8th-note left-hand arpeggio
... give it octave bass and fuller texture"; MXRR (010) the climax's peak one beat at C#6, hardly above A2. The
running-8ths-only climax hands (p-div2) read like the verse; the octave bass was what made a climax arrive.

**Set level** (56 verdicts = 28 judges x 2 passes, the cleanser):

| measure | value |
|---|---|
| all verdicts | on kept 34 of 56 = 0.61 (Wilson 0.48-0.72) |
| pass 1 / pass 2 | on 17 / 28 each; the programme read second kept 23 / 28 in each pass |
| by order | on read first kept 8 / 28, on read second 26 / 28 |
| **agreement** | **10 of 28 judges (0.36)** keep the same code in both passes - below chance (0.5) |
| **AGREED** | on kept by 8 of 10 (Wilson 0.49-0.94, exact 0.44-0.98): **not above 50 %**; of all 28 judges 0.29 |
| variety | on 4.43 / off 4.11, paired +0.32 se 0.10 (3.2 se) |
| coherence | 6.64 / 6.68 (-0.04 se 0.03) |

The two passes show what the set choice measures: 18 of 28 judges flipped with the order - the forced choice is
mostly recency (82 % of verdicts kept the programme read second, cleanser or not). The paired variety rating is the
steady signal (+0.32 here, +0.32 p-div2, +0.50 p-div3, +1.07 p-div).

**Decision: DON'T MERGE** (per piece -1.0 se sits on the "not worse than -1 se" line; the set CI - all verdicts and
the agreed ones - does not clear 50 %). The four rounds:

| round | per piece (se) | sets kept | read second kept | variety paired |
|---|---|---|---|---|
| p-div (gate 1.5) | -0.38 (0.16) | 28 / 28 | 14 / 28 | +1.07 |
| p-div2 (gate 0.8) | +0.22 (0.24) | 19 / 28 | 23 / 28 | +0.32 |
| p-div3 (1.2, anthem varied) | -0.40 (0.16) | 17 / 28 | 21 / 28 | +0.50 |
| p-div4 (1.2) | -0.22 (0.22) | 34 / 56; agreed 8 / 10 | 46 / 56 | +0.32 |

Next: the set-level forced choice cannot carry a merge decision while order decides it - rate each programme alone
(one judge, one programme: variety / coherence / "keep listening" 1-10, unpaired) or use the agreed two-pass count
with more judges; per piece, give the climax hand back its bass octave (big / broad with motion: 'o' on 1 then 8ths)
rather than only running 8ths.

## Round os1: SOLO on vs off - the solo players for expression (principal winds / horn on exposed lines, a string solo event per piece with set memory, the concertmaster on the violins I's cantilena, swells and smoother string legato); per piece strict paired, 16 slots, plus 4 set pairs, two passes (2026-10-25)

**What changed** (`agentsound/endless/solo.py`, `genres.symphony_solo`, `--flag solo`; docs/ORCHESTRA_ENDLESS.md
"Round os1"): the user's question "single instruments or sampled groups?" - every role was a section program. With
SOLO on, the exposed woodwind / horn melody and counter lines go to the VSCO 2 CE principals (flute / oboe / clarinet
/ bassoon / horn _solo, legato, dynrange 20 dB, `orch.SOLO_RANGE` = the programs' common range, no notes under
0.1 s). The tutti and the doublings keep the section. A string solo event (violin / cello / none per set slot, never
the same twice in a row) puts the most lyrical soft violins I / cellos block on the quartet's player, with the
strings under it 10 velocity steps softer. The concertmaster (SSO Violin Solo 2, 12 dB under the section by fader)
doubles slow soft violins I lines. Swells on long notes and 55-90 ms string legato come from the score's rules. Off
is bit-identical to master 2aca085: 40 / 40 symphonic slots and 24 / 24 protected hashes on the final code. The
full `python tests/run.py` passes: 79 modules, 1706 tests (`test_endless_solo.py` 4).

**Distribution** (the 16 judged on-pieces): silent_notes 0 in all; flat_dynamics only on timpani / harp, plus once
on horn_solo (011). 89 wind solo blocks, 6 violin solo events, 0 cello events (no soft cellos theme block passed the
filter), 25 concertmaster blocks. The concertmaster sits 17.3 dB under the violins I on average (14.8-23.9): deeper
than the 10-14 target, and no judge heard it as phasing or sticking out ("a quiet edge").

**Protocol**: as o24. The plan comes from set seed 159000 (PLAN_on.json, one plan for both codes; off ignores the
'solo' draws). Slots 159000 + 10 (k - 1), best-of-1, `--split --orch` with the articulation marks, two panels of 7
lenses, 3 hidden references. The brief added a 7th rating "performance" (expression / phrasing / the solo lines) and
"solos:" (where a solo sings or is lost). A slot whose new render failed the gate re-drew both codes. Sets: 4 pairs
(set seeds 159500-159800, 8 pieces). Per the p-div4 protocol, `set_round.py deal --balance --cleanse --two-pass`
ran every judge twice, relabelled and in the other order, and the criterion is on the AGREED verdicts; the brief
adds "expression: 1-10" per programme. Keys `KEY_orch_os1.json`, `KEY_orch_os1_sets.json`. mp3s, SCORES.txt,
SET_SCORES.txt and SET_EXPRESSION.txt are in `songs/_endless_orchestra/out/blind_os1/`.

**Per piece** (on - off, n 112):

| lens | melody | harmony | form | development | performance | orchestration | life | overall | memorable | masterpiece |
|---|---|---|---|---|---|---|---|---|---|---|
| on - off | +0.51 | +0.26 | +0.31 | +0.43 | **+1.10** | +0.78 | +0.27 | **+0.51** | +0.29 | +0.38 |

Over the 16 slots, overall was **+0.51 se 0.12 (+4.3 se)**, normalised +0.51 se 0.21. Won / lost 13 / 3. By slot:

| slot | 001 | 002 | 003 | 004 | 005 | 006 | 007 | 008 | 009 | 010 | 011 | 012 | 013 | 014 | 015 | 016 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| on - off | +1.00 | -0.14 | +0.14 | -0.43 | +1.00 | +0.57 | +1.00 | +0.71 | -0.29 | +0.29 | +0.14 | +1.14 | +0.86 | +0.57 | +0.86 | +0.71 |

Masterpiece: on 4.05, off 3.67, refs 5.31. The generated performance rating (5.56) is now nearly the references'
(5.81; gap +0.25, the smallest of all dimensions). Template flags per packet: on 39.7, off 34.9, refs 16.0. The
solo role names make the on pieces' layouts look alike to the statisticians ("four solo sections in turn").
What the judges miss in the on pieces: a "parade" of 3-4 soft solo episodes (oboe -> concertmaster -> clarinet ->
horn) that hand the same phrase round instead of developing it; once an oboe_solo inside a loud tutti, "lost". The
cause is composition, not the players: the solos make the episode chain visible.

**Set level** (56 verdicts, 28 judges x 2 passes): on kept **56 of 56**. Pass 1: 28 / 28, the programme read second
kept 14 / 28. Pass 2: 28 / 28, the second read kept 14 / 28. Agreement 28 of 28. **AGREED: on 28 of 28 (Wilson
0.879-1.000)**. There is no order effect this time: on read first kept 28 / 28, on read second 28 / 28. Pairs 14 /
14 each. Expression (paired) **+2.62 se 0.07**, won 56 / 0. Variety on 4.96 / off 4.68 (paired +0.29 se 0.06);
coherence 6.66 / 6.38 (+0.29 se 0.06). Tells per programme: on 9.11, off 8.80. The judges' caveat: "the two evenings
are the same eight compositions" (same plan, same seeds). The set choice is a pure performance / orchestration
choice, and the solo role names are visible in the packets, so the set win is not blind to the flag. It measures
whether the solo writing reads as better orchestration, not whether a listener hears it.

**Learned ears** (second opinion, the 16 pairs): Audiobox PQ +0.022 se 0.012 (13 / 16 up) and CE +0.012
se 0.017 (10 / 16), both flat. CLAP P(real orchestra) -0.017 se 0.006 (3 / 16 up): small, but consistent. The
solo players read slightly less like "an orchestra" to CLAP, which is expected from exposed single instruments and
is no realism gate.

**Decision: MERGE** (rule: per piece > 2 se, or per piece >= -1 se AND the set CI above 50 %). Per piece +4.3 se
and the agreed set CI 0.88-1.00 both pass. Next:
- the concertmaster +3-4 dB;
- the cello event's filter (it never fired);
- no wind solo in blocks of 9-10 roles at f;
- the composer to develop the theme across consecutive solo episodes rather than pass it round.

## Round ox1: COLOUR on vs off - guest colour instruments (organ, classical guitar, harpsichord, celesta / glockenspiel, tubular bells) a piece is built around; per piece strict paired, 16 slots, plus 4 set pairs, two-pass set judges (2026-10-25)

User feedback (HUMAN_FEEDBACK, 2026-10-25): "more exotic instruments like a church organ or an acoustic guitar" and
"above all increase diversity". docs/ORCHESTRA_ENDLESS.md "Round ox1" has the mechanics.

- **Packs** (all redistributable): Lars Palo's Burea / Pitea church organs (CC-BY-SA 2.5; the credits print the
  attribution, checked in every organ render), the nylon guitar, harpsichord, glockenspiel and tubular bells patches
  (CC0), the SSO celesta. Not used: fiedler-natural-concert-guitar (NC), sampleradar-* (no redistribution),
  mslp-vibes (NC), mellotron-sfz.
- **COLOUR** (`--flag colour`, default off; off is bit-identical to master on 40 of 40 symphonic pieces and 24 of 24
  protected hashes): `endless/colour.py` (new module) + hooks in `composer.set_plan` (`set_guest`),
  `symphony.compose / build` and `bandlib/orchestra.guests` / `church_organ(hall=)` (the guests sit in the
  orchestra's hall bus).
  - The set plan draws a colour per piece with memory: never the previous colour, at most ceil(n / 4) per set,
    'none' never twice in a row, the feel steers it (no guitar / harpsichord in a scherzo, celesta favoured there).
  - Plans per colour: organ cathedral / chorale / voluntary (prelude or interlude alone on soft flues + a solo stop,
    the swell pedal, a full-organ + 16 ft pedal summit, an amen); guitar serenade / nocturne (the piece capped in
    tempo, chamber size, the guitar's arpeggios under a solo wind with pizzicato strings, brass and harp out, an
    envoi); harpsichord grosso / continuo (continuo under the theme, a concertino episode, the 8 ft / full / 4 ft
    registrations, a cadence); celesta magic / glitter (the theme doubled high, the glockenspiel on a recap, a
    twinkle into the last chord); bells peal / toll (the climax downbeats, the coda's tolling).
  - The orchestra is thinned where the guest plays (soft / continuo / concertino / serenade modes).
- **Protocol**: code snapshot 0ab983e (bf15a1b + the master click fix), the flag only, one engine (master's build)
  for both codes.
  - Per piece: seeds 163000 + 10 (k - 1), best-of-1 (slot 3 moved on to 163021: 163020 failed the gate in the new
    code on a flat horn lead), `deal --split` two panels of 7, 3 hidden references, KEY `KEY_orch_ox1.json`, packets
    with the articulation marks; the judges answer a `colour:` line.
  - Sets: 4 pairs (set seeds 163500 - 163800), 7 judges each, `deal --balance --cleanse --two-pass` (p-div4's
    set_round: every judge twice, the second pass relabelled in the other reading order) = 56 verdicts, KEY
    `KEY_orch_ox1_sets.json`.
  - The full `python tests/run.py` on the branch: 79 modules, 1710 tests, 0 failed.
- **Distribution** (16 + 4 x 8 = 48 plans): organ 9, celesta 10, guitar 9, harpsichord 9, bells 8, none 3 (6 %);
  never the same colour in neighbours, at most 2 of a colour per 8-piece set. Round plan 163000: organ 4, guitar 3,
  harpsichord 3, celesta 2, bells 2, none 2. The guest plays 21-30 % of a piece's seconds (organ 30 %, harpsichord
  30 %, guitar 24 %, bells 22 %, celesta 21 %).
  - Gate: 0 silent notes, 0 flat_dynamics warnings (infos only), clicks only low-severity stem clicks not in the mix
    (new 2, old 3; one organ_pedal_full release); masking warnings 3.75 / 3.5 per piece (new / old).
- **Per piece** (paired new - old, 112 pairs, raw): overall +0.05 (se 0.19), slots won / lost 8 / 8; melody +0.01,
  harmony -0.03, form +0.01, development -0.19, orchestration +0.14, life +0.10, memorable +0.02, masterpiece +0.06.
  Masterpiece (absolute): new 3.71, old 3.65, refs 5.17. Template flags per packet: new 37.0, old 41.3, refs 17.3.
  - By colour (slot means): bells +0.29, guitar +0.19, organ +0.11, harpsichord -0.09, celesta -0.21. The best slot
    is a harpsichord piece (009 +1.86), the worst too (012 -1.43). The 2 no-colour slots have byte-identical packets
    and scored +0.57 / -0.57: the per-slot noise is about +-0.6.
  - The colour is heard: every judge named the right guest in all 98 colour packets, none named one in the 14
    no-colour / 112 old / 42 reference packets. By the wording, 55 of 98 say it lifts the piece / is idiomatic, 43 a
    cameo / routine / framing (celesta 10 of 14 cameo, guitar 12 of 21, harpsichord 10 of 21, organ 9 of 28, bells
    2 of 14).
  - "What is missing" names the guest's absence: "the celesta disappears for 94 bars", "the guitar is absent from the
    development, climax and coda", "the organ is silent until S6", "the harpsichord vanishes (S5-S10)", "the bells
    are not foreshadowed before the climax".
- **Sets** (56 verdicts): new kept 56 of 56 = 1.000, Wilson 0.936-1.000; by order: new read first 28 / 28, read
  second 28 / 28 (the programme read second kept 28 of 56). Two passes: pass 1 28 / 28, pass 2 28 / 28; agreement
  28 of 28 judges; agreed: new 28 of 28, Wilson 0.879-1.000. Variety new 5.18 vs old 3.96 (paired +1.21 se 0.06),
  coherence 6.38 vs 6.25; "same piece again" first heard at position 4.55 (new) vs 3.96 (old).
  - Every judge saw that the two programmes are the same compositions and that the colours alone separate them; the
    guitar serenade (no brass, a chamber texture), the organ frame + full-organ climax and the harpsichord continuo
    are named as "a world of its own".
  - The point for old, named by nearly every judge: the colours repeat their own gestures inside a set - the same
    celesta arpeggio C5-C7 closes two pieces, the same descending three-stroke bell peal ending on a lone bell closes
    both bells pieces, a lone harpsichord chord ends both harpsichord pieces; the bells' climax-then-coda plan is the
    same each time. The plain orchestral climax (trumpets / trombones) of the guitar piece is missed.
- **Recommendation by the rule: MERGE** - per piece +0.05 (not worse than -1 se) and the set-level CI (0.936-1.000,
  agreed 0.879-1.000) above 50 %, in both reading orders and both passes. As in oc1 it is a colour win on identical
  compositions: the set variety rises, the per-piece quality does not.

Next: (1) vary the colour gestures per piece with set memory (the twinkle's arpeggio shape / register / chord, the
peal's pattern and its last stroke, the harpsichord's ending - never the same gesture twice in a set); (2) keep the
guest through the piece: one return in the development or the recap (a guitar or celesta that vanishes after the
opening reads as a cameo), and foreshadow the bells before the climax; (3) the guitar piece keeps one real brass
tutti at its climax; (4) the colour should change the composition too (form, theme, harmony), not only the
scoring - the judges hear the same skeleton under each colour; (5) 'none' came out in 3 of 48 plans (6 %) - raise it
if the user wants plain orchestral pieces.

## Round op1: POLISH on vs off - the choir / solo / colour features' top fixes (oc2, os1, ox1) and the titles' label memory; per piece strict paired, 16 slots, plus 4 set pairs, two-pass set judges (2026-10-25)

**What changed** (`--flag polish` = `genres.symphony_polish(True)`, on top of master 0b7dafb's defaults; off is
bit-identical: 40 of 40 symphonic pieces and 24 of 24 protected hashes; docs/ORCHESTRA_ENDLESS.md "Round op1"):
- SOLO (`solo.SOLO_POLISH`): the concertmaster +4 dB (measured on the 16 judged pieces: -12.4 dB under the violins I
  per section, -9.1 .. -17.3; off -16.4); at most 2 blocks in a row with an exposed solo player (the third on the
  section: 18 blocks in 16 pieces); the cello event fires (5 cello events in 16 pieces, all the violins I's theme an
  octave or two down; off 0).
- COLOUR (`colour.COLOUR_POLISH`): a return in every stretch of more than 30 % without the guest (16 returns in 14
  guest pieces: organ solo stop on the tune, guitar's own tune, continuo, celesta sparkle, bell hint), the coda always
  with the guest (one guitar `farewell`), the bells' hint before the climax, the signature gestures with set memory
  (celesta rise / fall / wave / chime, bells scale / rounds / motto / toll, harpsichord rolled / flourish / with /
  broken), the guitar piece on the full orchestra, celesta / glockenspiel / guitar +2.5 / +1.5 / +2 dB.
- CHOIR (`choir.CHOIR_POLISH`, `PLANS_POLISH`): at the sung summit the orchestra's melody instruments hold chord tones
  instead of the theme (`_leave`), the summit +2 dB, the summit's texture with set memory (unison 2 / hymn 1 of the 3
  summits), at most 2 summits per 8 slots (3 in 16; off 3), no halo under 4 bars (two 'halo' plans then sang
  nothing: slots 4, 9).
- Titles (`composer.title_slot`): a form label at most once in any 4 slots (3 of 16; off 4 of 16).

**Protocol**: code snapshot c1e0ebe, one engine built from the worktree's source (master's click fix) for both arms.
Per piece: each code its own plan from set seed 167000 (they differ only in POLISH's draws), slots 167000 + 10 (k - 1),
best-of-1; slot 2 moved to 167012 (167010 both codes failed, 167011 new failed: a silent choir alto 'oo' note) and slot
12 to 167113 (167110 both, 167111 / 167112 new: harp spiky_track). `deal --split` two panels of 7, 3 hidden
references, packets with articulation marks; the brief rates 8 dimensions (performance added) plus masterpiece /
missing and solos / choir / colour lines. KEY `KEY_orch_op1.json`. Sets: 4 pairs (set seeds 167500 - 167800; 167700's
slot 8 failed the gate in all 5 new attempts - choir alto 'ah' C4 silent at bars 69-70 - so that pair is 7 pieces),
`set_round.py deal --balance --cleanse --two-pass`, 56 verdicts, the set brief with expression 1-10 and a voices line,
KEY `KEY_orch_op1_sets.json`. Full `python tests/run.py`: 82 modules, 1726 tests, 1 failure - test_voicing's 5-s
timing assertion under the parallel renders (19 s); it passes alone.

**Per piece** (new - old, n 112): melody -0.11, harmony -0.01, form -0.09, development -0.05, performance -0.03,
orchestration -0.10, life -0.08, **overall -0.15 (se 0.20, -0.75 se)**, normalised -0.15 (se 0.16), memorable -0.04,
masterpiece -0.11. Slots won / lost 6 / 9: 001 -0.29, 002 -0.86, 003 -0.71, 004 +1.00, 005 -0.14, 006 +0.14,
007 -0.43, 008 +1.14, 009 -1.43, 010 0.00, 011 -0.86, 012 +0.71, 013 -0.86, 014 +0.29, 015 -1.00, 016 +0.86.
Absolute overall new 4.76 / old 4.91 / refs 7.64; masterpiece new 3.47, old 3.58, refs 6.33. Template flags per
packet new 49.1, old 52.3, refs 2.7.
- The sung-summit slots lost (002 -0.86, 007 -0.43, 015 -1.00). The judges still hear the choir as a doubling or a
  pad, and now the climax as static: "a wall of held notes (oboes / horns / trumpets / violins in octaves) with the
  choir doubling - nothing moves" (DGGK, slot 15); "the sopranos sing a slow wandering [oo]/[oh] line UNDER the held
  F#/E winds". `_leave`'s held chord tones sit in the melody instruments' register, above the sopranos, and the
  skeletonised sung theme is not read as the theme.
- The guitar pieces on the full orchestra: 004 +1.00, 008 +1.14 (015, with the summit, -1.00). The guests read as
  more built in ("frames the piece and returns at the end, built in"); the bells' hints once "used too often to stay
  special".

**Set level** (56 verdicts): new kept **9 of 56** (Wilson 0.09-0.28); pass 1 5 / 28, pass 2 4 / 28; agreement 21 of
28; **AGREED: new 1 of 21 (Wilson 0.01-0.23)**; no order effect (the programme read second kept 27 of 56). Variety new
5.07 / old 5.36 (paired **-0.29 se 0.07**), coherence 6.73 / 6.75, **expression paired -0.95 se 0.04 (0 won / 52
lost)**. Per pair new kept 0, 2, 7 (of 14), 0. The reasons (`SET_WHY.txt`), nearly unanimous:
1. "old keeps more exposed single players" (one statistician counted 46 solo-role section entries vs 36): the no-parade
   rule and the guests' returns (the organ cornet, the guitar's tune) take the solo winds / violin off the quiet
   middles - the judges of whole evenings want MORE solos, not fewer.
2. The guitar pieces on the full orchestra: "new brings marc trumpets, trombones and tuba at nearly every peak", "old
   keeps the 6/8 pastorals on horns and woodwinds, so only 2, 4, 6, 8 bring the full brass" - the evening loses its
   weight contrast.
3. Organ + choir in the opener, the organ cornet tune making two organ pieces twins; the bells "a one-note-per-bar pad
   all through".
The 9 new verdicts (7 in pair 167700) praise exactly the returns: "the guest colours return inside their pieces (34
sections with a guest vs 23)", "plants its colours before the big moment".

**Decision: DON'T MERGE.** Per piece -0.75 se passes the ">= -1 se" line, but the agreed set CI (0.01-0.23) is far
below 50 %, and expression / variety fall. Keep from it (each judged positive or neutral): the concertmaster +4 dB,
the cello event on the theme, the guests' returns and coda presence, the gesture memory, the title label memory, the
summit cap. Drop / rework:
1. **No parade, but keep the solos**: instead of handing the third solo block back to the section, vary it - another
   player, the section on a DIFFERENT texture, or a guest - and never let a guest's return replace a solo wind / violin
   line (return only where no solo plays).
2. **The guitar piece's climax**: not the full brass by default - the set's memory on the climax weight (full brass at
   most every other piece; a guitar piece takes horns + trumpets, no tuba / trombones).
3. **The sung summit**: the orchestra's held notes UNDER the sopranos (capped below the sung note) and moving (a
   counter-line from the motto, or an ostinato) - not a wall of held octaves; sing the theme's own rhythm (no
   skeleton) at the summit.
4. **No silent choir plan**: when the halo has no 4-bar place, fall back to another event (slots 4, 9 sang nothing).
5. **Master bug** (both codes): choir alto notes silent at a bar's beat 4.9 (167010 'oo' C#4 bar 80; set 167700 slot 8
   'ah' C4 bars 69-70, all 5 new seeds) - the gate rejects them; look at the alto's lane / re-attack there.

**Files**: the 32 mp3s, both KEYs, SCORES.txt, SCORES_quality.txt, SET_SCORES.txt, SET_EXPRESSION.txt, SET_WHY.txt and
distribution.txt are in `songs/_endless_orchestra/out/blind_op1/`; the listening set (POLISH on, set seed 168000, 5
pieces) in `listen_op1/`; scripts, renders and verdicts in D:\tmp\op1.
