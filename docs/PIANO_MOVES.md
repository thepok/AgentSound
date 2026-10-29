# Piano moves: signature gestures for the endless solo piano

Status: **the first five built** (round g4, 2026-10-16: the motto, the signature ostinato, the suspended pause, the
goosebump chord, the cascade - section 11 says how they were built and measured); the rest is design (2026-10-15). The user: famous piano pieces have a few iconic "cool moves", moments
everyone recognises, and our endless new-age / romantic / pop-classical pieces lack them. This document is the
research behind that remark and a ranked, generator-ready vocabulary of such moves. Each move has its parameter
space (so every piece plays its own version), placement rules, interactions with the existing systems, tell risk, a
metric and the owning tool. Section 10 recommends the first five moves for blind round g4.

Copyright rule: the research describes the **mechanism** of each gesture (texture, rhythm, harmony, register, pedal,
timing), never its notes. No melody of a protected piece goes into the repo. The generator builds every move from
the piece's own material: its hook, chords, key and register.

Related: [PIANIST_RULES.md](PIANIST_RULES.md) (the bloom, the hand-to-hand figure, the hands' balance, the
register ceiling, the "Ideas" table this document builds on), [LEARNED_GENERATOR.md](LEARNED_GENERATOR.md) (the
student's tokens), `songs/_blind/ROUNDS.md` (the blind rounds g1 / g2 and their tells).

## 1. What makes a piano moment memorable

Six findings recur across the pieces in section 2. They are the design rules for every move below.

1. **Plant, recur, pay off.** An iconic gesture is heard early and alone (an intro or the first bar), comes back at
   the seams of the form, and is transformed at the high point or the ending. A gesture heard once is just an effect.
   One that comes back changed becomes the piece's identity.
2. **It is exposed.** Something drops away right before it (the left hand, the pedal, the pulse) or the texture
   around it is static, so the gesture is the only thing that moves. Für Elise's motto opens unaccompanied.
   Gymnopédie's melody floats over a bass that never changes.
3. **One parameter changes per recurrence.** The listener recognises the gesture because most of it stays the same,
   and is moved because one thing (the chord, the register, the rhythm, the dynamics) changes. A literal copy is
   boring, and the g1 judges named copied returns as a tell. A full transformation is no longer recognisable.
4. **The surprise falls on a known note.** The goosebump moment is usually familiar melody over a new harmony, a new
   key or a new register. New material at the climax is rarely what listeners remember.
5. **Time stops before the payoff.** A fermata, a held suspension, a bar of silence or a ritardando into a pause.
   The listener's expectation is the effect.
6. **The texture is idiomatic to the hands.** The moves that pianists love (cascades across both hands, hand
   crossings, rolling arpeggios, bell chords) show the keyboard's geometry. Our pieces split at E4 / G4 and never
   cross (HUMAN_FEEDBACK 2026-10-15). The bloom started to fix that.

## 2. Research: the gestures in famous solo-piano pieces

Each row is one gesture, its mechanism, where it lives in the form, why it is memorable and how often it recurs.

### Classical and romantic

| piece | the move (mechanism) | where | why memorable | recurrence |
|---|---|---|---|---|
| Beethoven, Für Elise (WoO 59) | **The neighbour-note oscillation.** A semitone oscillation between the tonic chord's 5th and its chromatic lower neighbour (the leading tone of the dominant), in 16ths, starting on an upbeat, unaccompanied, for 2-4 swings. It then falls into a broken-chord descent onto the tonic. | the first bar, the pickup into every return of the rondo refrain (A B A C A) | It is exposed (no left hand), and the chromatic half step is ambiguous: a question that does not yet say which chord it belongs to. | at the start of every refrain, about 5-6 times. Between refrains the motto also links the episodes back in as a retransition: a dominant pedal with the oscillation over it. |
| Für Elise, the refrain | **The hand-to-hand arpeggio.** The left hand plays a 3-note broken chord rising in 16ths (root, 5th, 10th) and stops. The right hand continues the same 16th motion from just above, into the next melody note. One continuous line passes from hand to hand. | every bar of the refrain where the melody holds a note | One figure flows over three octaves with no audible seam. The melody and the accompaniment are the same motion. | every refrain, several times per phrase. We have this already (`perform._handoffs`, the bloom). |
| Debussy, Clair de lune | **Static floating chords, then the shift into flowing motion.** The opening sits in parallel 3rds / 6ths in the middle register over a soft, slowly moving harmony, in 9/8 with ties that hide the downbeat (the time floats). At the "un poco mosso" the left hand starts continuous broken-chord arpeggios across the bass and tenor, the melody comes in octaves above, and the music suddenly flows. | the section line about a third into the piece; the arpeggios come back under the return of the theme | It is a pure texture event: the same mood, but now there is motion. The listener feels the pulse arrive. | once as an event; then it is the texture of the middle section and colours the return |
| Clair de lune, the climax | **The arpeggio cascade.** Wide, pedalled arpeggios that roll up and down two or three octaves, shared between the hands, with the melody on top in octaves and a crescendo to the peak. They die away in a long decrescendo. | the middle section's peak | The whole keyboard rings in one pedal. The register is at its widest. | 1-2 waves |
| Chopin, Nocturnes (op. 9 no. 2, op. 27 no. 2) | **The fioritura.** On a return of the theme, a long melody note is decorated by a free run of 7-30 notes in the time of 1-2 beats, outside the meter (often notated in small notes), from a chord tone around the chord's scale or chromatically, landing on the next melody note. The left hand keeps strict time underneath (the "tempo rubato" of the right hand alone). | the 2nd / 3rd statement of the theme, and a cadenza near the end (op. 9 no. 2: a repeated-note cadenza before the coda) | The tune is familiar, so the run is heard as the player's improvisation on it. It shows virtuosity at a soft dynamic. | rising: few in the first statement, more in each return, the biggest at the last |
| Chopin, Nocturnes | **The nocturne left hand.** A wide arpeggio from the bass through the 10th or 12th and back, in 8th-note triplets or 12/8. The pedal holds the harmony and the bass rings through. | the whole piece | the stable bed under which the right hand is free | constant (our `nocturne` figure) |
| Liszt, Liebestraum no. 3, the Consolations, the Hungarian Rhapsodies | **The hand crossing / cascade between the hands.** The left hand crosses over the right to place single bell notes or the melody high. Cadenzas are descending arpeggio cascades split between the hands in groups of 3-4 notes, the hands leapfrogging down the keyboard. In Liebestraum the melody moves to the tenor (thumbs) with the arpeggio split above and below it. | the transitions between strophes (the cadenzas), the climax | The visual and aural sweep, the melody heard in a new register. The cadenza stops time. | Liebestraum has 2 cadenzas, one after each climax. The melody appears in a new register in each of its 3 strophes (middle, tenor, high). |
| Satie, Gymnopédie no. 1 | **Floating dissonance over a rocking bass.** In 3/4 the left hand alternates a low bass note on beat 1 with a mid-register chord on beats 2-3. The harmony rocks between two major-7th chords (IVmaj7 and Imaj7). The melody enters late and moves slowly, mostly in long notes on the chords' 7ths and 9ths, so it never fully resolves. Marked "lent et douloureux", pp. | the whole piece; the rocking pair is the intro alone for 4 bars | It is still. The dissonance is soft, not tense. The two-chord rock is hypnotic. | the pair is constant; the melody's second strophe is a near repeat with a different end |
| Beethoven, Moonlight Sonata, I | **The triplet ostinato under a tolling melody.** Right-hand triplet 8ths broken over the chord, middle register, the same rhythm from the first bar to the last. Bass octaves move slowly in the left hand. The melody enters as a dotted figure on repeated notes over the triplets (in the top of the right hand). It is played with the dampers raised ("senza sordino"), pp throughout. | the whole movement; the ostinato alone for the first 4 bars | The rhythm never changes, so every harmonic step is felt. The repeated melody note tolls like a bell. | constant; the melody returns transposed |
| Rachmaninoff, Prelude in C# minor op. 3 no. 2 | **Bell chords.** A 3-note descending motto in fff octaves, then massive chords spread over four staves at the climax: a low bass octave strikes, then high chords on the following beats, all in one pedal, like a church bell (the strike, the overtones). | the motto opens the piece (alone, ff), the climax restates it in bell chords, the coda echoes it ppp | The register is extreme and the dynamics huge. The motto is three notes and unforgettable. | at the start, the climax and the end: plant, payoff, echo |

### New-age, pop-classical and film piano

| piece / style | the move (mechanism) | where | why memorable | recurrence |
|---|---|---|---|---|
| Yiruma, River Flows in You | **Rolling left hand plus an octave melody.** The left hand rolls 8th-note broken chords (root, 5th, 10th, 5th) over a 4-chord pop loop (vi-IV-I-V-like). The melody is a 16th-pickup cell that repeats with small changes. In the chorus the melody comes in right-hand octaves, louder, with the left hand unchanged. | the octaves at the chorus and its repeats | It needs no harmonic surprise. The same tune in octaves is "the same, but bigger". The pickup cell is the hook. | the chorus 2-3 times; the octave doubling at the 2nd / 3rd |
| Einaudi (Nuvole bianche, Una mattina, I giorni, Experience) | **The ostinato build by layers.** A 2- or 4-bar left-hand cell (an Alberti-like broken chord or open 5ths in 8ths) repeats unchanged for many bars over a 4-chord loop. Layers enter one at a time: the melody, the melody in octaves, a 16th right-hand figure, a bass octave. Each layer enters at a 4- or 8-bar boundary and the dynamics rise in steps. The music then subtracts back to the bare cell. Melodies are simple and repeated, and get decorated (triplets, 16ths, grace notes) as the piece goes on. | the whole piece is the build; the peak at 60-80 %; the ending is the bare cell | The listener tracks the layers. Hypnotic, but with a clear arc. | the cell is constant; each layer stays once added, then the layers leave in reverse |
| Tiersen, Comptine d'un autre été (L'après-midi) | **A driving broken-chord pattern in both hands.** The left hand plays a steady 8th-note broken chord (a 2-chord or 4-chord loop in minor, no root-position bass on the beat). The right hand adds its own 16th broken pattern on top: two interlocking ostinati, no melody at first. Then a melody comes in as the top notes of the right hand's pattern. | the whole piece; the right hand's pattern changes at 8-bar boundaries | It is pure rhythm and pattern. The interlocking hands make a machine-like drive (in this style that is the idiom, not a tell). The minor loop gives melancholy. | constant, with 8-bar variants |
| George Winston (December, Autumn; "folk piano") | **Left-hand patterns as the piece.** Rolling 8th / 16th left-hand patterns with an open 5th or 10th at the bottom, often a pedal tone (the bass held on one note under changing chords). The right hand plays simple diatonic tunes, often in parallel 3rds / 6ths, with bell-like single high notes and long pedal resonance. | the whole piece; the pedal-tone stretches under the intros and the climaxes | Resonance: the open intervals and the pedal tone ring like a guitar or a harp | the pattern is constant; the pedal tone under the intro and the build |
| Richter / Ólafur Arnalds style minimal | **Repetition plus one change.** A 4-chord loop repeated, a single line on top. Each pass adds one thing (an inner voice, an octave, a bass note), sometimes takes one away. Often there is a sudden drop to near-silence before the last pass. | the whole piece as passes | Every change is audible because nothing else changes. | 4-8 passes |
| Film piano (Hans Zimmer piano themes, Max Richter's "On the Nature of Daylight" played on piano) | **The suspended pause.** Before the payoff the music stops on a held suspension (sus4, sus2, an added-9 dominant) or on silence, with the pedal held or released. Then the theme comes in, often subito p, not loud. | before the climax or before the last return | Expectation. The silence is louder than the climax. | once or twice |
| Film piano | **The sudden key lift.** The last statement of the theme a step or a minor 3rd up, entered directly (the pop "truck-driver" change) or through a one-bar dominant of the new key. | the last chorus or the climax | "The same, but higher": the arrival feels like hope. | once |
| Film / new-age piano | **The pedal-point bloom.** The harmony moves above a sustained or repeating bass note (usually the dominant, sometimes the tonic). The tension rises because the upper chords clash with the held bass. The release comes when the bass moves at the climax. | the build before the climax, the intro, the coda (a tonic pedal) | Rising tension with a fixed floor. The bass's move is the arrival. | once per build; a tonic pedal in the coda |
| Film / new-age piano | **The goosebump chord.** A known melody note is reharmonised once with a chromatic-mediant or borrowed chord (bVI, bIII, iv, II major, III major) at the climax or the last return. | the payoff | Principle 4: the surprise falls on a known note. | once, maybe echoed in the coda |
| Pop-classical endings (Yiruma, Einaudi, film cues) | **The hanging ending.** The final chord rolls and then a single high note (the 9th, the 3rd or the motto's first note) sounds alone after it. Or the motto returns as a fragment, slower, and stops before its resolution. | the last bar | It leaves the piece open. The listener completes it in their head. | once, echoing the opening |

### What our pieces have today (from the code, and the g1 / g2 judges)

- The bloom: the left hand's 16ths, the hand-to-hand figure and the woven right hand. It is the Für Elise refrain
  move, but it is a generic texture, not a planted motto. The g2 judges named "the hand-off broken chord" as a stock
  gesture shared across pieces (TODO bloom 6d).
- The climax: `grow` / `theme` / `climb` / `lift` / `step`, the cadenza (a 2-beat fioritura over the last dominant
  in 15 % of the climaxes), the fermata after the peak.
- No planted motto (the `opening` cell is a rhythm, not a recognisable gesture). No piece-specific left-hand
  ostinato: the figures are drawn per bar from shared sets. No pause, no harmonic surprise reserved for the payoff, no
  register gesture (crossings, cascades), no designed ending gesture.

## 3. The shared parameter grammar

Every move is described with the same five slots. They map onto the existing code, so a move is mostly data.

| slot | what | drawn | where it lives |
|---|---|---|---|
| **identity** | what makes this piece's version of the move its own: intervals, rhythm cell, grid, register band, the hand(s), the chord degree | once per piece, from the piece's seed and its own material (hook, chords, key) | the move's entry in the signature table (section 8) |
| **placement** | the form roles of its statements: `plant` (first, exposed), `recur` (at seams), `payoff` (climax or last return), `close` (coda / last bar) | per piece, from the layout's roles | derived from `plan['sections']` names + `_role` |
| **transform** | how each later statement differs from the previous one | a sequence drawn without repeat, one transform per recurrence (two at the payoff) | the shared `TRANSFORMS` table below |
| **performance** | dynamics, pedal, tempo treatment, touch | per statement | the section's `dyn`, `romantic.PEDAL`, `PHRASE_TEMPO`, `play` keys |
| **idiom guard** | the combinations that become nonsense | constraints checked at draw time; a failed draw takes the next choice | the move's draw function |

**TRANSFORMS** (one table, shared by all moves; it extends `genres.VARY` and composer `DEVELOP_RHYTHM` rather than
adding a parallel vocabulary):

| transform | what | idiomatic for | nonsense when |
|---|---|---|---|
| `same` | literal | the 2nd statement of an ostinato / a texture move | used for a melodic motto twice running (the copy tell) |
| `octave` | +-12 | motto, octave melody, far return | it crosses the ceiling (`line` 86, `peak` 89) or drops the melody under E4 without a tenor role |
| `augment` / `diminish` | durations x2 / x0.5 | motto at the payoff / in the bloom | a diminution under 1/16 at fast tempi (> 14 notes/s) |
| `reharm` | the same pitches, a new chord under them | motto, the goosebump chord | the new chord clashes with a long melody note (`melody_issues` long-note rule) |
| `harmonize` | add 3rds / 6ths / octaves under it | motto, octave melody | 3rds over a chromatic oscillation (parallel minor 2nds) |
| `fragment` | head only; 2-1-1 liquidation | coda, the build's approach | under 2 notes (no longer recognisable) |
| `invert` | the contour mirrored | the B section's answer | an oscillation (it is its own inversion: no change) |
| `sequence` | restated a step / a 3rd higher | build, climax | more than 3 links (the tile tell, g2 TODO 6c) |
| `displace` | started a beat / half a beat later | motto in 4/4, hemiola in 3/4 | the start crosses a chord change and the cell loses its harmony |
| `answer` | played by the other hand (tenor) | motto, echo | the left hand is in a 16th figure (no hand free) |
| `thin` / `thicken` | layers removed / added | ostinato, layered build | more than one layer per 4 bars (the build turns into a ramp) |
| `delay` | arrives after a pause | the payoff | it is used twice in a piece |

**The recurrence rule.** A statement changes 1 transform against the one before (2-3 at the payoff, where register,
harmony and dynamics move together). The transform sequence is drawn without repeat per piece. A literal `same` is
allowed only for texture moves (ostinato, rocking pair) and never twice running for a melodic move.

## 4. The vocabulary, ranked

Ranked by expected impact on "a moment I remember" (the user's ask) against effort and tell risk. The **owner** is
the tool or table where the move belongs (KISS: a table / preset in the owning tool, not a parallel technique).

| # | move | slot in the piece | owner | builds on | impact | effort | tell risk |
|---|---|---|---|---|---|---|---|
| 1 | The motto (planted cell) | identity | composer (`frame` lines, `CELLS` motif, `plan['set']['opening']`) | `FRAME_LINES`, `_vary` | high | medium | medium |
| 2 | The signature ostinato | identity | `pianist.FIGURES` (a generated figure per piece) + `_NA_FIGURES` | `figure()`, `lh_only` | high | low-medium | medium |
| 3 | The suspended pause | transition | `perform._play_piano` tempo / pedal, section `fermata` | `fermata`, pedal `dry` spans | high | low | high if every piece |
| 4 | The goosebump chord | payoff | `perform._reharm` + `NEW_AGE_HARMONY['reharm']` | `_reharm`, `_key_spans` | high | low | low |
| 5 | The cascade | payoff / way out | `pianist.sweep` / `alternating_hands`, `perform` climax exit | Ideas #17 | high | medium | medium |
| 6 | The pedal-point build | transition | `figure()` fixed bass, set `build` block `pedal` | Ideas #11 | medium-high | low | low |
| 7 | The texture switch (static -> flowing) | transition | section `figures` per piece (set draw) | `_NA_FIGURES` | medium-high | low | low |
| 8 | The octave melody | payoff | `romantic.harmonize` / section `harmonize` value | `harmonize` | medium-high | low | medium |
| 9 | The hand-crossing bell | colour | `perform._handoffs` event kind `cross` | `_handoffs`, `_lh_reach` | medium | medium | medium |
| 10 | The fioritura on a return | colour | `romantic.fioritura`, return `vary` 'orn' | `cadenza`, `_local_scale` | medium | low | medium |
| 11 | The launch run | transition | `pianist.run` / `gliss`, the `into` bar | `cadenza` | medium | low | medium |
| 12 | Bell chords | payoff | `pianist.FIGURES` `bell` + climax `harmonize` 2 | `big`, `roll` | medium | low | low |
| 13 | The floating pair (Gymnopédie rock) | identity (frames) | `genres.INTROS` vamp + `NEW_AGE_HARMONY` blocks | intro vamps, `waltz` figures | medium | low | low |
| 14 | The tenor melody (register swap) | colour | `perform` section role `tenor`, `BALANCE` | Ideas #15, `lh_lead` | medium | medium-high | low |
| 15 | The tenor echo (call and response) | colour | `perform._handoffs` event kind `echo` | Ideas #3 / #9 | medium | medium | medium |
| 16 | The layered build | transition (replaces the bloom) | `perform` build section kind + `_NA_BLOOM` sibling | the bloom | medium | medium-high | high |
| 17 | The prepared key lift | payoff | climax `key` 'step' + `_pivot` | `_modulate`, `_pivot` | medium | low | medium |
| 18 | The hanging ending | close | `perform._ending`, `END_STYLES` | `END_ROLL` | medium | low | high if every piece |
| 19 | The tremolo swell | transition | `pianist.tremolo` in the `into` bar | `tremolo` | low-medium | low | medium |
| 20 | The hemiola / displaced motto | colour | composer cells, `_moving_bass` | Ideas #10 | low-medium | medium | low |
| 21 | The inner duet (3rds / 6ths line) | colour | `perform._handoffs` event kind `counter` | Ideas #9 | low-medium | medium | low |
| 22 | The far return | close | A3 / A4 `octave` + `figures` thin + `tempo` | exists in part | low | low | low |

## 5. The moves in detail

For each move: the mechanism, its parameter space (values and draw weights; "nonsense" lists the combinations to
forbid), placement, how it transforms on recurrences, how it interacts with the existing systems, the tell risk, a
metric, and the owner.

Notation: pitches are MIDI numbers (60 = C4); the register ceiling is `plan['ceiling']` {'line': 86 (D6),
'peak': 89 (F6)}; "the hook" is the tune's chorus motif, "the head" the theme's first cell.

### 5.1 The motto (planted cell)

**Mechanism.** A 1-2 bar cell that is the piece's signature. It is stated alone or nearly alone (left hand silent or
a single held bass) at the very start. It returns at the seams (the pickup into a return, the interlude) and pays off
transformed at the climax. In the coda it comes back as a fragment. It is not the hook (the hook is the chorus's
singable line), but it is derived from the theme's head so it belongs to the piece (Für Elise's oscillation opens
its refrain; Rachmaninoff's three-note motto is the climax's material).

**Parameter space.**
- `kind` (the cell's shape): `osc` neighbour oscillation 1.0 (Für Elise), `sigh` appoggiatura + resolution, the
  pair repeated a step lower 0.8, `toll` repeated note with a dotted rhythm 0.5 (Moonlight's tolling melody), `call`
  rising 3-4 notes ending on an open degree (2, 5, 6) 0.8, `leap` a 6th / octave leap up and a stepwise fall 0.7,
  `fall3` three falling notes (the Rachmaninoff pattern, in our case stepwise or by 3rds) 0.6.
- `interval` (osc / sigh): m2 1.0, M2 0.8; direction lower 1.0 / upper 0.5 neighbour. The degree it hovers on: 5
  1.0, 3 0.8, 1 0.4, 6 0.3 (major), 5 1.0, b3 0.6, 1 0.6 (minor). An `osc` on the 5th with its chromatic lower
  neighbour (#4: the dominant's leading tone) is the strongest. In minor the lower neighbour is the raised 7th only on V.
- `swings` (osc): 2 0.5, 3 1.0, 4 0.6 alternations before it breaks off.
- `grid`: 16ths 0.8 (needs tempo <= 80), 8ths 1.0, triplet 8ths 0.6 (needs meter 4), 8ths in 3/4 for the waltz.
- `breakoff` (what follows the cell): `arp_fall` broken chord down to the tonic 1.0, `step_land` 0.8, `held` (the
  last note held, the chord enters under it) 0.6.
- `entry`: upbeat 1.0 / downbeat 0.5.
- `register`: the theme's register (G4-Bb5, never above D6 for a plant; the payoff may reach the `peak`).
- `exposure` at the plant: `alone` 1.0 (no left hand), `over_bass` 0.8 (one held bass note), `over_figure` 0.3.
- `recurrences`: 2-5 (seams of the layout; a long `song` layout up to 5).
- `transforms`: drawn from TRANSFORMS without repeat; the payoff draws two of {`augment`, `reharm`, `octave`,
  `harmonize`, `sequence`}; the close draws `fragment` (+ `augment` 0.5).
- `dyn` at the plant: pp 0.6 / p 1.0; `rubato` at the plant: the first statement may stretch 5-12 %.

**Nonsense.** 16ths above 80 BPM (a trill, not a motto). An oscillation on a degree outside the local chord's scale
(the g1 home-scale tell). `harmonize` in 3rds over a semitone oscillation. A `leap` beyond the ceiling at the plant.
`swings` 4 at 8ths in a slow piece (a full bar of two notes: a repeated-note tell). Motto = the hook's literal first
cell (it then has no identity of its own; derive it with at least one change of rhythm or interval).

**Placement.** Plant: the intro's first bar(s) (a frame line `motto`, the intro's `lh_only` > 0). Recur: the pickup
into A2 / A3 (the last beat(s) of the previous section, Für Elise's retransition), the interlude (`inter` frame:
its line is the motto instead of an echo), the build's opening bar (the motto `sequence`d up). Payoff: the climax's
first bar or its peak bar (`augment` + `reharm` or `octave` + `harmonize`). Close: the coda's last 2 bars, a
`fragment` that stops on its open note (move 18 can take it).

**Interactions.** Bloom: in a blooming build the motto can be the woven figure's material (the weave quotes the motto
instead of chord tones: Ideas #1 diminution). Hand-offs: a hand-off never covers a motto statement. Balance: the plant
is a melody statement (`A1` role, a clear melody); `alone` needs no balance. Ceiling: the plant <= `line`, the payoff
<= `peak`. Form archetypes: the plant is always the first section; in a layout without an intro, A1's first bar.
Dice / play: the motto is a composition decision (the tune's), stored on the tune like the hook, so a decoded student
tune carries it. Student tokens: the motto is notes and needs no new token; a `Motto_<kind>` header token (like
`Ref_<part>_<n>` for the motif) lets the student learn its placement.

**Tell risk.** Medium: the same kind in several pieces of a set, or the motto at every seam (a mechanical refrain).
Guards: the set memory (section 7) on (kind, interval, grid); at most 4 recurrences; at least one recurrence absent
(the B section never has it).

**Metric.** `motto_hits`: statements found with `composer.hook_matches(line, motto, scales=(0.5, 1, 2))` per piece
(want 3-6), `motto_plant_exposed` (left-hand onsets in the plant bar, want 0-1), `motto_payoff` (a match inside the
climax section, want 1), `motto_change` (the share of recurrences that differ from the one before in pitch, rhythm
or chord, want 1.0). Audibility in the render: the plant's phrase level from report.json per phrase within 3 dB of
A1.

**Owner.** composer: a `motto` frame line in `genres.FRAME_LINES` / `INTRO_LINES` and a motto field on the Tune,
the kinds as a `MOTTOS` table next to `CELLS` (data), its placement in `perform._piano_plan` (section lines). Set:
`plan['set']['motto']` (the kind) with `set_memory`.

### 5.2 The signature ostinato

**Mechanism.** One left-hand figure that is this piece's own, not drawn per bar from a shared set. It is established
alone in the intro and is the A sections' texture. B / the build use other figures, and the return of the ostinato
is the return home. (Moonlight's triplets, Comptine's broken pattern, Einaudi's cells, Winston's rolling hands, River
Flows in You's rolling 8ths.)

**Parameter space.**
- `grid`: 8ths 1.0, triplet 8ths 0.7 (4/4 only), 16ths 0.4 (tempo <= 76), 3/4 8ths for the waltz.
- `contour` (the token order over the chord's ladder, generated, not picked from FIGURES): `rise` (0 1 2 3 ...)
  0.6, `rise_fall` 1.0, `rock` (alternating a low and a high step: 0 2 1 3 ...) 0.8, `pendulum` (bass, crest, mid,
  crest) 0.7, `alberti` (0 3 1 3) 0.4, `interlock` (Comptine: the bass off the beat, the crest on the beat) 0.3.
  Generated as a token string from `contour` + `span`, checked against `pianist.figure`'s rules (repeats <= 2).
- `span`: the ladder steps used, 3-6 (a 10th to two octaves). Wider spans want slower grids.
- `bass`: on 1 1.0, on 1 + the octave below at section starts 0.5, `pedal` (the same bass note under two chords)
  0.3.
- `colour`: 0 0.6 / the chord's 7th or 9th at one fixed token position 0.4.
- `cycle`: 1 bar 1.0, 2 bars (a figure whose second bar answers its first) 0.5.
- `accent`: the crest note leaning (+8 %) 0.6, flat 0.4.
- `hands`: left alone 1.0; `split` (the left hand plays the bass and the right hand's thumb completes the figure
  under the melody: Moonlight's right-hand triplets) 0.3, which needs the melody >= 2 steps above the figure's top.
- `recurrences`: the A sections and the coda; `thin` / `thicken` per return (drop the bass octave, add the colour).

**Nonsense.** A 16th figure with span 6 under a busy melody (mud, and the left hand drowns the right). An `alberti`
in the climax (a classical cliché at the peak). `interlock` with a melody that also syncopates. A cycle of 2 bars
under a chord rhythm of 1 bar (the second bar's figure no longer fits).

**Placement.** Plant: the intro with `lh_only` 1-2 bars (the ostinato heard alone first). Recur: A1, A2, the returns.
Absent in B / the build (contrast). Payoff: the last return keeps it and thins it (Moonlight's end), or the climax
plays it doubled in octaves (`big` built from it). Close: the coda's last figure is the ostinato `thin`.

**Interactions.** The figure sets `_NA_FIGURES` get a `sig` slot whose figure name is filled per piece. The g2 tell
"the LH escalation 8ths -> triplets -> 16ths in every climax" falls away when the build does not escalate from a
shared ladder. Bloom: the bloom's two stages start from the ostinato (its contour at a faster grid) instead of the
generic `trip12` / `span16`. Balance: A sections with the ostinato keep the A balance; `split` is a balance role of
its own (the right hand's inner notes x `inner`). Ceiling: the figure's cap is the existing cap (G4, the bloom's
`lift`). Dice / play: the ostinato's descriptor (grid, contour, span) is a piece-level play key, recorded; the
student gets `ASig_<grid>_<contour>` tokens (a small vocabulary: 4 x 6). Figure tokens are per section (`AFig`), so
the student already learns where the figures change.

**Tell risk.** Medium: the judges called per-bar toggling a machine (round 3), and a constant figure could read as a
loop. It is idiomatic in this genre (Einaudi, Tiersen), so the risk is low when the harmony and melody develop over
it. Guard: the ostinato never runs more than 16 bars without a `thin` / `rest` bar at a phrase end.

**Metric.** `sig_share`: the share of A-section bars whose left-hand onset pattern (positions + ladder steps)
equals the piece's signature (want 0.6-0.9), `sig_distinct_set`: no two pieces in a set share (grid, contour, span)
(want true), `lh_variety` (exists) not lower than before. Audibility: the intro's `lh_only` bars at -8..-3 LU of the
piece (report.json per section).

**Owner.** `pianist.figure` (a figure string generated from the descriptor; data, not a new player), `_NA_FIGURES`
`sig` slot, `perform._play_piano` (the per-piece figure name), `genres` play key `sig`.

### 5.3 The suspended pause

**Mechanism.** Before the payoff, time stops: the last bar of the build ends on a held suspension or on silence, a
fermata, sometimes the pedal released into true silence, then the payoff enters (film piano; Liszt's cadenza
fermatas; Ideas #6 "a bar of silence before the climax", #16).

**Parameter space.**
- `kind`: `sus_hold` (V7sus4 / Vsus2 / IV/V held, pedalled, decaying) 1.0, `rest` (a measured rest with the pedal
  up: real silence) 0.6, `high_note` (one high note of the chord alone, held) 0.5, `bass_only` (the bass note rings
  alone) 0.4.
- `length`: 1-3 beats + a fermata of 1.5-3 beats; in seconds 1.2-3.5 s (rest: 0.8-2 s, longer is a stop).
- `approach`: `rit` (ritardando over 1-2 bars, x0.8-0.9) 1.0, `subito` (no rit, cut off) 0.5, `dim` (a decrescendo
  to pp into it) 0.7.
- `after`: `subito_p` (the payoff starts soft and grows: the film way) 0.8, `forte` (the payoff starts strong) 0.6,
  `pickup` (a 1-beat pickup run into the payoff) 0.4.
- `pedal`: held (the chord decays) / lifted (silence) by kind; `rest` always lifted.
- Recurrences: 1 per piece, a second (shorter) only before the last return in a long layout (0.25).

**Nonsense.** A `rest` pause directly after a phrase-end breath (two silences). A pause and the key lift's pivot bar
on the same seam (move 17: the pivot is the preparation, the pause would double it). `subito_p` into a climax whose
first bar is its peak note (the peak must then come later). A pause over 4 s (the listener thinks the piece ended).

**Placement.** The seam into the payoff section (the climax, or the last return in a `return` layout). Never into
the first return. In a layout without a climax (Ideas #6 archetypes) it goes before the coda.

**The climax's arrival (round g9).** All five g8 judges heard "the theme returns at the climax" as the plan every
piece in the set shares. A set draw, `plan['set']['arrival']`, now decides how each piece's climax arrives:
- `direct`: the climax just enters.
- `pause`: this move, at the climax seam. One is drawn when the piece's signature has none.
- `key`: the climax is in another key. Since round g13 only a whole step up or the parallel major
  (`perform.SUNG_KEYS`): ZSTD's climax a 4th up over IV was heard as new melody by four g12 judges.
- `dominant`: the section before ends on V7sus4 | V7 with a fermata.
- `fragment`: the head's first bar, then the same bar a step higher, then the whole theme. Since round g12 it plays
  the whole head first and then the fragment, and only for a cell of 3+ notes. The climax's first 4 bars always state
  the head (`clx4_ok`).

Since round g12, the motto's payoff in the climax enters 2 bars in, or 4 after a `fragment` arrival
(`perform.MOTTO_PAYOFF`). It is placed only when it ends before the peak note, so it never replaces the head's first
bars. Since round g13, a payoff with no room before the peak answers it instead, from the bar after the peak note
(the payoff kept in every set slot with a motto: 0.89 -> 1.0), and its last note leaves no empty bar (VYDA 38).

A slot never repeats an arrival from the three slots before it, so an 8-piece set plays all five. When the arrival
is not 'pause', a pause drawn for the climax seam moves to the return. The `high_note` kind belongs to the climax
seam only, because a lone high note before the coda sounds like an artefact (DMZT 52):
`composer.arrival_pause`, `perform._arrive`.

**Interactions.** The `inhale` play key (the slowing into the climax) becomes the `approach`. The bloom's `carry`
(the climax keeps part of the push) is cancelled by a pause: after a pause the climax starts at its own tempo.
Balance: no effect. The pedal: `pedal_changes(dry=)` spans for `rest`. Dice: a piece-level play key `pause`
(kind), recorded; tokens `APause_<kind>`. The breath gate: a `rest` pause lowers quiet1 a little; it is wanted
silence, so the gate should exclude the span.

**Tell risk.** High if every piece pauses before the climax (a new template; g2's "one form skeleton"). Guards: the
set memory (no `kind` repeat within 2 slots); the pause in at most 50 % of the pieces of a set; its seam also drawn
(before the climax 0.6, before the last return 0.25, before the coda 0.15).

**Metric.** `pause_s`: seconds with no new onset and the render's short-term level 15+ dB under the section's
(report.json `sections` / a 100 ms RMS from the stems), want one span 0.8-3.5 s at the drawn seam; `pause_after`:
the payoff's first-bar level vs the pause's previous bar. Score: present where planned, absent elsewhere.

**Owner.** `perform._play_piano` (the seam's tempo and pedal), section keys `fermata` / `rit` (exist), a new section
key `pause` in `ARRANGE_KEYS` / `PIANO_DRAWN` drawn on the seam's section.

### 5.4 The goosebump chord

**Mechanism.** A known melody note, heard earlier over its home chord, is harmonised once with a chromatic-mediant
or borrowed chord at the payoff. Principle 4: the tune stays, the floor moves.

**Parameter space.**
- `which note`: the hook's goal note (its longest / highest note) 1.0, the motto's last note 0.6, the theme's
  cadence note 0.5.
- `chord` (the substitute; it must hold the melody note as a chord tone or a 9th): major: bVI 1.0, iv 0.9 (the
  minor IV), bIII 0.5, II major (V/V) 0.6, III major (V/vi) 0.6, bVII 0.5, IVmaj7/I 0.4; minor: VI 1.0, IV major
  (the Dorian IV) 0.8, bII 0.3, V/V 0.5.
- `voicing`: open (root + 5th + 10th in the left hand, the melody on top) 1.0, rolled 0.6, bell (move 12) 0.4.
- `length`: 1 bar 1.0 / 2 bars 0.4; it then returns to the original chord route.
- `dyn`: an accent of +1 level or a subito p (the surprise soft) 0.4.
- `echo`: the coda restates it once, softer (0.3).

**Nonsense.** The substitute already heard earlier under the same note (no surprise). A melody note that becomes a
b9 / #11 over the substitute (the `melody_issues` long-note rule). Two goosebump chords in a piece. A substitute in a
section that is already in another key (the local key's degrees; `_key_spans`).

**Placement.** Payoff only: the climax's peak bar or the last return's equivalent bar. The earlier statements of the
same note must have the home chord (the move needs a reference).

**Interactions.** `perform._reharm` already swaps chords with a share per section; the goosebump is the opposite: one
chosen bar, a stronger substitute, nothing else reharmonised there (the climax's `reharm` share must leave the bar's
predecessors as written). The key spans: the substitute is in the local key. Bloom / balance / ceiling: none. Dice:
a section key `goose` (degree) in `PIANO_DRAWN`; the student's `AGoose_<degree>` tokens.

**Tell risk.** Low: one bar per piece. The set memory on the degree avoids "bVI at every climax".

**Metric.** `goose`: the payoff's goal-note bar has a chord whose root differs from every earlier bar under the same
melody pitch (+-1 beat), outside the diatonic set; want exactly 1. `goose_fit`: the melody note is a chord tone or 9th.

**Owner.** `perform._reharm` with a `goose` table in `NEW_AGE_HARMONY['reharm']` (data), placed by `_arrange`.

### 5.5 The cascade

**Mechanism.** From the peak, a pedalled arpeggio waterfall falls 2.5-4 octaves. The hands leapfrog in groups of 3-4
notes (Liszt's cadenzas, Clair de lune's climax), with a ritardando, onto the low bass. It replaces the single
"tempo collapse over the low octave walk" that every climax ends with today (Ideas #17).

**Parameter space.**
- `chord`: the peak chord 1.0, its colour version (add9 / maj9 / 6/9) 0.8, the dominant (falling into the next
  section's tonic) 0.5.
- `groups`: 3 notes 0.8 / 4 notes 1.0 per hand turn; `pattern` RL (right then left) 1.0, RRL 0.4, both hands in
  contrary motion (the left rising while the right falls, meeting in the middle) 0.3.
- `span`: from the peak note (<= `peak` 89) down to 31-43 (G1-G2): 30-50 semitones.
- `grid`: 16ths 1.0, sextuplets 0.6, 32nds with an accel-rit shape (non-metrical, like a fioritura) 0.4.
- `length`: 1 bar 0.6, 2 bars 1.0 (with a ritardando to x0.7).
- `dyn`: from the peak's level down two levels (ff -> mp) 1.0, or held level and a diminuendo only in the last group
  0.4.
- `direction`: down 1.0 (the way out), up 0.3 (into the peak: then it is move 11).
- `landing`: the low tonic + a rolled chord 1.0, the bass alone ringing 0.5, straight into the next section's
  figure 0.4.

**Nonsense.** A cascade over a chord change mid-way (the pedal smears two chords). Groups of 5+ per hand at 16ths
(not playable). The left hand above the right at the start (a crossing is move 9). A cascade in a piece whose climax
is `subito p` (the cascade is the release of a loud peak).

**Placement.** The climax's way out (the bar after its peak note), or the last bar of the bloom into the climax.
Once per piece; the coda may echo it in 3 groups, pp (0.3).

**Interactions.** `pianist.sweep` (one hand, evenly) and `pianist.alternating_hands` (the hands trading) are the
building blocks. The cascade is an `alternating_hands` with a falling ladder and a rit, so it goes there as a
`pattern` / `direction` option, not as a new function. Ceiling: it starts at the peak note (<= 89). Balance: the
cascade's notes are counted to both hands, so the bar is near equal. The pedal: one pedal over it, `dry` after the
landing. `_NA_FIGURES['big']`: the climax's last bar figure becomes the cascade. Dice: section key `exit` on the
climax (`cascade` / `broaden` / `tenuto` / `rest` / `run_down`: Ideas #17's way-out draw); tokens `AExit_<kind>`.

**Tell risk.** Medium. Every climax ending in the same cascade would be the next "C1-C2 octave walk" tell, so `exit`
is a draw with set memory.

**Metric.** `cascade`: >= 10 onsets in <= 2 bars, falling overall >= 30 semitones, both hands with >= 3 onsets each,
alternating; want 1 where drawn. `flow32` already counts it. Audibility: the stems' peak-to-landing level drop
(report.json).

**Owner.** `pianist.alternating_hands` (a falling, ritardando option), the climax `exit` draw in `perform`
(`_ending` sits next to it), `_NA_FIGURES`.

### 5.6 The pedal-point build

**Mechanism.** The harmony moves over a held or repeating bass note (usually the dominant; Winston's pedal tones,
the film build). The clash between the moving chords and the fixed bass grows the tension. The bass moving at the
climax is the arrival.

**Parameter space.**
- `degree`: V 1.0, I 0.6 (a tonic pedal: calmer; the coda), bVI 0.2 (minor, dark).
- `bass rhythm`: held (restruck each 2 bars) 0.6, repeated 8ths (a pulse) 0.8, octave pulse on 1 and 3 0.6.
- `upper route`: the set `build` block (`pedal` exists) or the build's own chords over the pedal; the chords that
  clash most come last (IV/V, ii7/V, bVII/V -> V7).
- `length`: 4 bars 0.6, 6 bars 0.6, 8 bars 1.0.
- `dyn`: a crescendo over the pedal, mp -> f.
- `release`: the bass moves to I on the climax's downbeat 1.0; deceptively to vi 0.3.

**Nonsense.** A tonic pedal under a dominant chord at a cadence (I under V7 is fine in passing, not as the cadence).
A pedal under a section in another key. A pedal and the bloom's 16ths both in the left hand (the figure's bass token
becomes the pedal: `figure()` with lad[0] fixed, the rest rises; that works).

**Placement.** The build (0.35 of builds), the intro (a tonic pedal under the motto, 0.3), the coda (a tonic pedal,
0.4).

**Interactions.** The bloom's natural floor (Ideas #11): its rising left hand sits on the pedal. Set `build` table:
the `pedal` block exists; the move makes it a texture (the bass fixed) and not only a chord block. Balance: the bass
pedal note x bass weight (`FIGURE_VOICING['bass']`) slightly lower so it does not pound. Dice: section key `pedal`
(degree / none), tokens `APed_<degree>`.

**Tell risk.** Low.

**Metric.** `pedal_bars`: the longest run of bars with the same lowest pitch class under >= 2 different chords (want
4-8 in the build where drawn).

**Owner.** `pianist.figure` (a fixed bass option), `perform._play_piano` (section key), the set `build` table.

### 5.7 The texture switch (static -> flowing)

**Mechanism.** The piece opens static: held chords, a slow left hand ('still', 'open', 'quart', block chords on 1).
At a planned section line the flowing figure starts and the music suddenly moves (Clair de lune's "un poco mosso").
The contrast is the event.

**Parameter space.**
- `from`: `still` / `open` / `quart` / chords on 1 and 3 / the floating pair (move 13).
- `to`: the signature ostinato (move 2) 1.0 / `flow` / `nocturne` / `tenths`.
- `at`: A2 1.0, B1 0.6, the build 0.3 (then it is the bloom's first stage).
- `announce`: a left-hand-alone bar before the line 0.4, none 0.6.
- `tempo`: a slight push x1.02-1.04 at the line (the "mosso").
- `ratio`: the left hand's onsets / beat after vs before, >= 2.

**Nonsense.** A switch into a section that is also the bloom (two events at once: the bloom's stage 1 already is a
switch). A switch back and forth more than once.

**Placement.** One line per piece, in the first third.

**Interactions.** `_NA_FIGURES`: A1's `calm` set would be replaced by a `still` set in pieces that draw the switch
(a per-piece figure-set draw: the set table, so a set does not do it in every piece). The bloom: one of the two
per piece, unless the switch is early (A2) and the bloom late (the build). Dice: a play key `switch` (section name);
`AFig` per section already records the result.

**Tell risk.** Low.

**Metric.** `switch_ratio`: the max ratio of left-hand onsets / beat between adjacent 4-bar phrases at a section
line (want >= 2 at the planned line, < 1.6 elsewhere).

**Owner.** `genres` (`_NA_FIGURES` sets), `perform._play_piano`.

### 5.8 The octave melody

**Mechanism.** The hook restated in right-hand octaves, louder, over the unchanged left hand (River Flows in You's
chorus, Clair de lune's middle section). "The same, but bigger."

**Parameter space.**
- `doubling`: octave below 1.0 (the top stays under the ceiling), octave with an inner 3rd / 6th filled on long
  notes 0.5 (the full romantic octave chord), octave above 0.2 (only where top + 12 <= `line`).
- `where`: the 2nd chorus 1.0 / the climax 0.7 / the last return 0.3.
- `share`: all notes 0.6, the long notes only (>= 1 beat; the 16ths single) 1.0.
- `dyn`: +1 level over the previous statement.

**Nonsense.** Octaves in 16ths faster than 8 notes/s. Octaves in the same statement as the woven right hand (one
hand cannot do both). An octave doubling over a `harmonize` 2 chord voicing (too thick).

**Placement.** A recurrence of the hook (never its first statement).

**Interactions.** `romantic.harmonize` (`voices`), section `harmonize` gets an `octave` value; the climax's
`harmonize` 1 / 2 draw gains it. Balance: the octave adds right-hand energy (+2-3 dB), so the balance plan for the
section subtracts it (the energy model counts the doubled notes: `_lh_balance` sees them). Ceiling: doubling below
keeps the top. Dice: `AHarm_octave` token.

**Tell risk.** Medium: an octave climax in every piece. Set memory on (move, where).

**Metric.** `oct_share`: the share of right-hand melody notes with a simultaneous note 12 below in the section,
want >= 0.5 where drawn.

**Owner.** `romantic.harmonize` + the section `harmonize` value.

### 5.9 The hand-crossing bell

**Mechanism.** The left hand crosses over the right to strike a single high note (a bell: the motto's first note,
the chord's 5th or 9th) while the right hand holds or ripples underneath (Liszt, Winston's high bell tones). The
gesture is visual, and in sound it is a high, soft, isolated note with the pedal ringing.

**Parameter space.**
- `pitch`: the motto's first / last note +12 1.0, the chord's 5th 0.6, the 9th 0.5. Register 84-89 (C6-F6): the
  ceiling's rare peaks are exactly this, so it uses that budget (`rh_c6` counts it).
- `when`: the beat after the melody's phrase end (the bell answers the phrase) 1.0, on a held note 0.5.
- `count`: 2 0.6, 3 1.0, 4 0.4 per piece, in one section (A2 or the last return) or spread.
- `dyn`: pp-p, the bell softer than the melody, a long pedal.
- `pattern`: single 1.0, a 2-note falling 3rd 0.6.

**Nonsense.** A crossing while the left hand plays a 16th figure (no time to cross). More than 4. A bell over the
climax's loud texture (inaudible). A bell note that clashes with the chord.

**Placement.** Colour in A2 / the interlude / the last return; never the plant.

**Interactions.** `perform._handoffs` already places events in held bars; a `cross` event kind adds the bell (the
left hand's figure ends early in that bar, like the hand-off). Ceiling: within `peak`, counted by `hands_tells`
rh_c6 (rename: notes over C6 of either hand). Balance: a left-hand note at the top; `_lh_balance` must not push it up.

**Tell risk.** Medium: the same bell at every phrase end. Count <= 4, the set memory.

**Metric.** `crossings`: left-hand onsets above the right hand's sounding notes (want 2-4 where drawn).

**Owner.** `perform._handoffs` (an event kind), data in `_NA_BLOOM` (`cross` chance) or the signature table.

### 5.10 The fioritura on a return

**Mechanism.** On a return of the theme, a long melody note is decorated by a free run (7-22 notes in 1-2 beats)
that lands on the next melody note. The left hand keeps strict time (Chopin's nocturnes).

**Parameter space.**
- `count`: per return, rising: 0 in A1, 1 in A2, 1-2 in the last return.
- `notes`: 7-22; `shape`: `arch` 1.0, `accel` 0.6, `wave` 0.5 (`romantic.SHAPES`).
- `scale`: the local chord scale (`_local_scale`) 1.0, chromatic descent 0.3 (only falling, only over a dominant).
- `range`: a 6th-12th around the long note, never over `line`.
- `dyn`: p, softer than the melody (x0.8), a little hairpin.
- `where`: the longest note of a 4-bar phrase that is not a phrase end.

**Nonsense.** A fioritura over a chord change (the run then must follow two scales). Over 22 notes in a new-age
piece (the style is simple). Two in one phrase. In the climax (it competes with the peak).

**Placement.** Returns (A2, A3, A4) and the coda's cadenza.

**Interactions.** `romantic.fioritura` exists and the climax `cadenza` already plays one. The `vary` kind `orn` on
returns places turns and mordents; a `fior` kind goes in the same table (`genres.VARY`). The g1 tell "runs in the
home scale" is fixed by `_local_scale`; reuse it. `orn32` in the score counts it.

**Tell risk.** Medium (g1: runs everywhere). Guard: count rule above, <= 3 per piece.

**Metric.** `fior`: runs of >= 7 right-hand notes within 1.5 beats starting on a held note in a return (want 1-3).

**Owner.** `perform._vary` (`fior` kind in `genres.VARY`), `romantic.fioritura`.

### 5.11 The launch run

**Mechanism.** An upward scale or arpeggio run in the right hand (sometimes both hands in octaves or a gliss-like
sweep) from the middle register to the climax's first note: the climax is launched.

**Parameter space.** `kind`: arpeggio 1.0, scale 0.6 (in the local scale), octave run 0.3. `length`: 1-2 beats 1.0, a
whole bar 0.4. `start`: 48-60. `target`: the climax's first melody note (<= `peak`). `dyn`: crescendo p -> f. Not
with a pause (move 3) on the same seam unless the order is pause -> run (a pickup run after the fermata, `after`
'pickup').

**Placement.** The bar before the payoff (the `into` bar), or after a pause.

**Interactions.** `pianist.run` / `sweep` / `octave_run`; the `into` figure set. Dice: the seam's `pause` / `launch`
draw shares one key (`seam`).

**Tell risk.** Medium: today's `cadenza` 15 % already sits there.

**Metric.** `launch`: >= 6 rising notes in <= 2 beats ending on the climax's first note.

**Owner.** `perform` (the `into` bar), `pianist.run`.

### 5.12 Bell chords

**Mechanism.** At the climax: a low bass octave struck, then a high chord on the following beat(s), all pedalled,
like a bell's strike and its overtones (Rachmaninoff's climax). For new-age a softer version: the bass octave on 1, a
spread chord with the melody on top on 2 or 3.

**Parameter space.** `bass`: octave 31-43 1.0. `chord`: the melody note + 3-4 chord tones below within an octave,
rolled 30-60 ms. `rhythm`: `o - c -` (half notes) 1.0, `o - - c` 0.5, the 3/4 `o - c` 1.0. `bars`: the climax's peak
bars, 2-4. `dyn`: f-ff with a long pedal.

**Nonsense.** At pp (it is a power move). Over more than 4 bars (pounding). With octave melody in the same bars.

**Placement.** The payoff, 2-4 bars around the peak.

**Interactions.** A `bell` figure in `pianist.FIGURES` (`o - - - c - - -`) in `_NA_FIGURES['big']`; climax
`harmonize` 2. Balance: climax role. The g2 tell "the climax velocity plateau" means the bell bars need a hairpin
inside them.

**Tell risk.** Low.

**Metric.** `bell_bars`: bars with a bass octave <= 43 and a >= 4-note chord with the melody on top >= 2 beats
later.

**Owner.** `pianist.FIGURES`, `_NA_FIGURES`.

### 5.13 The floating pair (Gymnopédie rock)

**Mechanism.** Two chords alternate bar by bar, with a low bass on 1 and a mid chord on 2-3, in 3/4 or a slow 4/4.
The melody floats on long notes that are 7ths and 9ths of the chords, never quite resolving.

**Parameter space.** `pair`: Imaj7-IVmaj7 1.0, IVmaj7-Imaj7 0.8, i9-VImaj7 0.8, Imaj7-iii7 0.5, vi9-IVmaj7 0.6.
`meter`: 3/4 (the waltz feel) 1.0, 4/4 in half notes 0.5. `length`: the intro 4 bars, the interlude 2-4, the coda
4. `melody`: none (the pair alone) 0.5, long colour notes 0.5. `dyn`: pp-p.

**Nonsense.** In the climax. With a busy figure. Colour notes that are b9 / #11 (the soft dissonance is 7 / 9 / 6).

**Placement.** Frames only: intro, interlude, coda (an identity alternative to the motto for calm pieces: `rain`,
`longing`).

**Interactions.** `genres.INTROS` (a `float` vamp), `_NA_FIGURES['intro']` with the waltz figure, the long-note
chord-tone rule (Ideas #4) needs an exception for 7ths / 9ths of a maj7 / m9 chord in this frame.

**Tell risk.** Low.

**Metric.** `float_pair`: a frame with exactly two alternating chords, >= 50 % of its melody's long notes on 7 / 9.

**Owner.** `genres.INTROS` + `NEW_AGE_HARMONY` blocks, `_NA_FIGURES`.

### 5.14 The tenor melody (register swap)

**Mechanism.** One statement of the theme goes into the tenor (C3-C4), played by the left hand's thumb or both
thumbs, while the right hand plays the broken chord above it (Liebestraum's middle strophe; Ideas #15). The theme
in a new register is a moment.

**Parameter space.** `where`: A2 0.5 / the last return 0.6 / B (the chorus) 0.2. `octave`: -12 / -24 (whatever puts
the line at 52-64). `rh figure`: `flow` / `rock` mirrored above the melody (a cap 5 steps above). `share`: the whole
section 0.5, its second half 0.5.

**Nonsense.** In the climax. With the ostinato in the left hand at the same time.

**Placement.** One return.

**Interactions.** BALANCE gets a `tenor` role (the left hand leads by 3-5 dB: the `lead` logic). `lh_lead` exists
as touch only (TODO hands 1); this gives it a line. Ceiling: helps (fewer high notes).

**Tell risk.** Low.

**Metric.** `tenor_bars`: bars whose melody (the hook-matched line) is in the left hand's register.

**Owner.** `perform._play_piano` (a section `register` key), `perform.BALANCE`.

### 5.15 The tenor echo (call and response)

**Mechanism.** At a phrase end, while the melody holds or rests, the left hand echoes the melody's last cell 1-2
octaves lower (Ideas #3 / #9).

**Parameter space.** `cell`: the last 2-4 notes. `delay`: 1-2 beats. `transform`: same / `invert` / `fragment`.
`count`: 1-4 per piece. `octave`: -12 / -24.

**Nonsense.** Over a phrase whose last cell is a single held note. While the left hand runs a 16th figure.

**Placement.** Phrase ends in A2 / B / the returns, not in the climax.

**Interactions.** A `_handoffs` event kind `echo`. Balance: the echo bar is a left-hand lead moment.

**Tell risk.** Medium.

**Metric.** `echoes`: left-hand cells matching the right hand's last cell (`hook_matches` on the LH line).

**Owner.** `perform._handoffs`.

### 5.16 The layered build

**Mechanism.** Einaudi's build: a 4-chord loop repeated 3-5 times, one layer entering per pass (the melody, the
melody in octaves, a 16th right-hand figure, a bass octave), dynamics in steps, then the layers leave.

**Parameter space.** `passes`: 3-5 x 4 bars. `layers` (in order, drawn): bass octave, octave melody, inner 16ths,
high bell. `drop`: a near-silent pass before the last 0.4.

**Nonsense.** Over a non-loop progression. With the bloom (the build is one or the other).

**Placement.** The build, instead of the bloom (0.25 of the pieces; `return` layouts more).

**Interactions.** `_NA_BLOOM['at']` and a sibling table `_NA_LAYERS`; the arc check.

**Tell risk.** High: literal repeats are the copy tell (g1). It is only idiomatic when each pass changes audibly.

**Metric.** `layer_steps`: one new layer per pass, measured by onset density / pitch span per 4 bars.

**Owner.** `perform` (a build kind next to `_bloom`), `genres`.

### 5.17 The prepared key lift

**Mechanism.** The last statement of the hook a step or a minor 3rd up. Through a one-bar dominant of the new key
or straight after a pause.

**Parameter space.** `interval`: +2 1.0, +1 0.4, +3 0.4. `prep`: pivot V7 of the new key 1.0, the pause 0.5, direct
0.2. `where`: the climax 0.6 / the last chorus 0.4. The ceiling: the lifted top <= `peak`.

**Nonsense.** A lift and a goosebump chord in the same bar. A lift into the coda (it never comes home).

**Placement.** The payoff.

**Interactions.** Climax `key` 'step' + `_pivot` exist; this makes the preparation a draw and pairs it with the
pause. Ideas #2.

**Tell risk.** Medium (g1: foreign-key climaxes read as transplants; keep it rare, 0.1-0.15).

**Metric.** `lift_prepared`: a key span change with a V7 of the new key in the bar before.

**Owner.** `perform._arrange` / `_pivot`, the climax `key` table.

### 5.18 The hanging ending

**Mechanism.** After the final rolled chord, one note alone (the 9th, the 3rd, the motto's first note), or the
motto's fragment stopping before its resolution.

**Parameter space.** `kind`: high single note 1.0, the motto fragment 0.8, a low bass note 0.3, resolved (none) 1.0.
`degree`: 9 / 3 / 5 / the motto's note. `register`: 72-86. `delay`: 0.5-1.5 beats after the roll. `dyn`: pp.

**Nonsense.** A b9 / #11 hanging note. A hanging note after a fade ending.

**Placement.** The last bar.

**Interactions.** `perform._ending`, `END_STYLES` / `END_ROLL`; the `end_top` rule. Ideas: the motto's close.

**Tell risk.** High if constant: in half the pieces at most.

**Metric.** `end_hang`: an onset after the final chord's onset, alone.

**Owner.** `perform._ending`, `genres.END_STYLES`.

### 5.19 The tremolo swell

**Mechanism.** A measured or free tremolo on a chord's outer tones (an octave, a 6th) in the left or right hand,
crescendoing into the climax (Liszt).

**Parameter space.** `interval`: octave 1.0, 6th 0.6, the chord's 3rd + 5th alternating 0.3. `hand`: left (under
the melody's held note) 1.0, right (the melody's last note trembling, the left hand holding the bass) 0.4. `length`:
1 bar 1.0, 2 bars 0.5. `rate`: 8-12 / s, `accel` from 8 to 12 0.5. `dyn`: p -> f over its length (`swell`
'accel'), landing on the climax's downbeat. `chord`: the dominant 1.0, the pedal point's top chord (with move 6) 0.6.

**Nonsense.** At pp throughout. More than once. Under a moving melody (the tremolo must be the only motion). In 3/4
under a waltz figure. A 6th whose upper note clashes with the melody.

**Placement.** The `into` bar (one seam move: pause, launch run or tremolo).

**Interactions.** `pianist.tremolo` exists (rate, swell, land). The seam draw is shared with moves 3 and 11. The
balance: the tremolo bar is a left-hand lead bar when `hand` = left.

**Tell risk.** Medium (a dated effect if loud and long): 1 bar mostly, in <= 25 % of a set.

**Metric.** `tremolo`: >= 8 alternations of two pitches within one bar, rising level (velocity slope > 0).

**Owner.** `pianist.tremolo`, the seam draw.

### 5.20 The hemiola / displaced motto

**Mechanism.** In 3/4 two bars re-grouped as 3 x 2 beats into the cadence; in 4/4 the motto displaced by a beat or
grouped 3+3+2 (Ideas #10).

**Parameter space.** `where`: the cadence bars of a return 1.0, the climax's approach 0.4. `grouping`: 3/4: 3 x 2
beats over 2 bars (the left hand's bass on 1, 3, 2 of the pair) 1.0, 2 x 3 beats against 3 x 2 in the right hand
only 0.5; 4/4: 3+3+2 8ths per bar 1.0, the motto entering a beat late (`displace`) 0.8. `hands`: both 1.0, the right
only 0.5 (the left keeps the meter). `bars`: 2 (one hemiola) 1.0, 4 0.3.

**Nonsense.** A hemiola that is not followed by a cadence (it must resolve the grouping). Over a chord rhythm that
contradicts it (the chord changes on the old beat 3). Two hemiolas running.

**Placement.** Colour: one per piece, at a cadence of a return.

**Interactions.** The waltz's `_moving_bass` (the chord change on beat 3 now and then is the harmonic side of it);
the left-hand figure in the hemiola bars is a 2-beat figure (a new `waltz_hemi` figure in `pianist.FIGURES`).

**Tell risk.** Low.

**Metric.** `hemiola`: in 3/4 two bars whose onset accents fall on 1, 3, 2 (the bass / long notes); in 4/4 bars with
onsets at 0, 1.5, 3.

**Owner.** composer cells (`DEVELOP_RHYTHM` 'displace' exists), `perform._moving_bass` (the waltz), `pianist.FIGURES`.

### 5.21 The inner duet

**Mechanism.** Under held melody notes, an alto or tenor line in 3rds / 6ths moving against the tune (Ideas #9).
One voice, not an arpeggio: the hand-off's sibling.

**Parameter space.** `interval`: 6ths below 1.0, 3rds below 0.7, 10ths (the left hand's thumb) 0.5. `motion`:
contrary to the melody's last step 1.0, parallel 0.4. `grid`: 8ths 1.0, quarters 0.6. `length`: the held note's span
(1-3 beats). `count`: 2-6 per piece, in A2 / B / the returns. `vel`: x0.7 of the melody.

**Nonsense.** Parallel 5ths / octaves with the melody. A duet over a 16th left hand (three layers in motion). Under
a melody note shorter than a beat.

**Placement.** Colour in returns and the chorus's second statement.

**Interactions.** A `counter` event kind in `perform._handoffs` (the same held-note detection as the hand-off and the
weave; one event per held note). Balance: inner (`inner` play key).

**Tell risk.** Low.

**Metric.** `duet`: right-hand notes under a held melody note that move stepwise >= 3 in a row, in 3rds / 6ths of a
chord tone.

**Owner.** `perform._handoffs` event kind `counter`.

### 5.22 The far return

**Mechanism.** After the climax, the theme returns an octave higher, pp, slower, over a thinned left hand (exists in
part: A3 `octave` + `thin` + `tempo` 0.9-0.97). The move makes it a planned close: the motto's `augment` or the
ostinato's `thin` on top.

**Owner.** The A3 / A4 sections in `genres` (data only).

## 6. A piece's move set

A piece picks from slots, not from a flat list, so that moves do not crowd each other.

| slot | moves | per piece |
|---|---|---|
| identity | 1 motto, 2 signature ostinato, 13 floating pair | exactly 1 (the motto and the ostinato can be combined: 0.35) |
| transition (into the payoff) | 3 pause, 6 pedal-point build, 7 texture switch, 11 launch run, 16 layered build, 19 tremolo | 1-2, at most one per seam |
| payoff | 4 goosebump chord, 5 cascade, 8 octave melody, 12 bell chords, 17 key lift | 1-2 |
| colour | 9 crossing bell, 10 fioritura, 14 tenor melody, 15 echo, 20 hemiola, 21 duet | 0-2 |
| close | 18 hanging ending, 22 far return (+ the motto's fragment) | 0-1 |

Total: 3-6 moves, and at most 5 marked moments a listener could name.

**Conflicts** (never together): the floating pair + the signature ostinato (both are the frame texture), the
layered build + the bloom (one build), the tenor melody + the tenor echo in one section, the goosebump chord + the
key lift on one bar, the pause + the key lift's pivot on one seam, bell chords + the octave melody in one bar, the
launch run + the tremolo on one seam.

**Affinities** (drawn together more often, x1.5): motto + goosebump (the motto's last note is the goosebump note),
motto + hanging ending (the motto's fragment closes), signature ostinato + texture switch (the switch introduces
the ostinato), pedal-point build + pause (the pedal stops on the suspension), cascade + far return (after the
waterfall, the high soft theme), pause + octave melody (subito p, then the octaves grow).

**Order of the draw:** identity -> payoff -> transition (given the payoff seam) -> colour -> close. Each draw is
checked against the conflicts and against the set memory (section 7).

## 7. The set: no two pieces share a move + parameter combination

The g2 judges compared the pieces of a set and named shared templates. The moves must not become the next one.

1. **A fingerprint per move:** (move, its identity bucket). The bucket is the coarse parameters a listener would
   recognise: motto (kind, interval, grid), ostinato (grid, contour, span band), pause (kind, seam), goosebump
   (degree), cascade (pattern, length), pedal (degree), octave melody (doubling, where), crossing (pattern), key lift
   (interval, prep), ending (kind). The fine parameters (exact pitches, swings, notes) come from the piece's own
   material and differ anyway.
2. **Memory:** a fingerprint never repeats within the set (memory = the whole set; sets are 6-12 pieces and the
   buckets give 20-100 combinations per move). A move's identity choice (the motto kind, the ostinato contour) is
   not reused within 2 slots. A payoff move is not the slot before's.
3. **Shares:** no move in more than 40 % of a set's pieces (4 of 10), except the identity slot's two main moves
   (each <= 60 %). The pause and the hanging ending <= 50 %.
4. **Where it goes:** `composer.set_draws` already draws per-slot keys with `plan['set_memory']`. Add one key,
   `signature`, whose value is the piece's move set (a dict {slot: (move, bucket)}). The memory check for it compares
   fingerprints over the full history instead of the last n slots: one branch in `set_draws`, `set_memory`
   {'signature': 'all'}. The slot pins it for every best-of-N candidate (the score cannot collapse a set onto its
   safest moves), like the other set draws. Without a set plan (the teacher export), compose draws it from the seed.
5. **Check:** `songs/_blind/variety_newage.py` reports the fingerprint collisions of a rendered set (want 0).

## 8. Where it goes in the code (KISS)

- **One table**, `genres._NA_SIGNATURE` (`plan['signature']`, validated strictly like `BLOOM_KEYS`): per move its
  slot, chance, parameter weights, conflicts and affinities. `plan['moves']` is taken (the waltz's bar moves), hence
  the name. The classical / lofi / e-piano genres opt in by a table of their own (`dict(_NA_SIGNATURE, ...)`), not by
  code.
- **One draw**, `perform._signature(tune, g, plan)` next to `_bloom`: it draws the move set from the seed (or the set
  pin), fills the identity parameters from the tune's material and places each move by its section roles (`_role`).
- **The moves themselves** reuse the owners named per move: the composer's frame lines and cells (motto), the
  figure string (ostinato), `_reharm` (goosebump), `alternating_hands` (cascade), `figure()` with a fixed bass
  (pedal point), `romantic.harmonize` (octaves), `_handoffs` event kinds (cross / echo / counter), `romantic.fioritura`
  via `genres.VARY` (fioritura), `_ending` (hanging note). New player functions are not needed for the top ten.
- **The record:** the move kinds (coarse) are arrangement decisions, recorded as piece-level play keys
  (`arrangement.PLAY_KEYS`: `motto`, `sig`, `pause`, `goose`, `exit`, ...) and section keys where they sit on a
  section. The fine parameters are drawn from the seed, like the bloom's. The student gets one token family per key
  (`AMotto_<kind>`, `ASig_<grid>_<contour>`, `APause_<kind>`, `AGoose_<degree>`, `AExit_<kind>`): a few dozen tokens,
  added to `learn.tokens.ARR_PIECE`, so its checkpoints need a re-export (like `ABalance` / `ALhLead`, TODO hands 5).
- **The metrics** go into one function, `composer.signature_tells(song, tune)` (like `bloom_tells` / `hands_tells`),
  reported first and scored in the new-age table only once the ranges are measured on the references.

## 9. Verifying a move is present and audible

1. **Notes:** `signature_tells` per move (the metrics in section 5) over 48 seeds in `songs/_blind/tells_newage.py`:
   present where planned, absent elsewhere, the set's fingerprints unique.
2. **Audio:** the move's span from the arrangement, checked in report.json: the pause's level drop, the plant's
   level, the cascade's span; `python -m agentsound zoom songs/<slug> --at <time>` at each planned moment for a look.
3. **A/B:** the bloom's method. One judge agent gets each tune with and without its move set (piano rolls / packets,
   shuffled), and says which has "a moment you would remember" and where.
4. **The blind round** (section 10).

## 10. Round g4: the first five moves and how the judges rate a memorable moment

**The first five** (they cover plant -> transition -> payoff, reuse existing tools and answer g2's set templates
when the set memory ships with them):

1. **The motto** (5.1): the plant / recur / payoff structure itself. Without a planted cell no later moment refers
   to anything. It also gives the `grow` climax its material (g2 TODO 6c: the grown climax tiling one cell).
2. **The signature ostinato** (5.2): each piece gets its own left-hand identity instead of figures drawn per bar
   from shared sets. That attacks the g2 "LH escalation 8ths -> triplets -> 16ths in every climax" template.
3. **The suspended pause** (5.3): the cheapest strong moment (Ideas #6 / #16), drawn by seam with a set share cap.
4. **The goosebump chord** (5.4): one bar per piece, low tell risk, `_reharm` does the work. It pairs with the
   motto (its last note) for the payoff.
5. **The cascade** (5.5) as one value of the climax's `exit` draw (Ideas #17): it replaces the shared tempo
   collapse over the low octave walk and gives the keyboard-wide gesture the user missed.

Ship them with the slot rules (section 6) and the set memory (section 7). Next would be the pedal-point build and
the octave melody (both low effort).

**How the judges rate "a memorable moment"** (an addition to `songs/_blind/JUDGE_NEWAGE.md`; the verdict format stays):

```
moment: bars <a-b>: <what happens, in the notes>      (the one moment of this piece you would remember)
memorable: 0-3
  0 none - nothing stands out
  1 a pleasant texture or a loud peak, nothing you would recognise again
  2 a distinct gesture you would recognise if the piece came back to it
  3 a gesture planted early, brought back changed, paying off at the high point or the end
recurs: bars <...> | none       (where the same gesture appears before / after, changed or not)
shared: <IDs of packets with the same gesture> | none
```

Scoring (`score_round.py`): the mean `memorable` of the generated pieces against the composed ones (target: at
least equal); the hit rate (the share of generated pieces whose named moment overlaps a planned move's bars); the
`shared` flags among generated pieces (a template tell: want 0); and, as before, the count of pieces judged
generated (it must not rise: a move that makes the judges say "generated" is a tell, not a moment). The renders get
the same question from the listener (the user) through HUMAN_FEEDBACK: "which moment would you hum?"

## 11. As built (round g4, 2026-10-16)

The first five moves, as section 10 proposed; where the build differs from sections 5-8 it says so.

- **The table:** `genres._NA_SIGNATURE` (`plan['signature']`: `cap` 0.4, `after` 0.35, `both` 0.35, and per move its
  slot, chance and parameter weights). Genre validates it strictly (`genres._signature_problem`,
  `SIGNATURE_KEYS`).
- **The draw:** per set slot in `composer.set_draws` (`signature_draw`, the slot's key / tempo / feel as ctx).
  - By slot: identity, then transition, then payoff. A move the slot before had: x `after`. A second identity move:
    x `both`. No move in more than `cap` of the set. Every piece gets one move at least.
  - Each move's parameters are redrawn until its fingerprint (`signature_prints`) is new in the set. The motto's
    fingerprint is its kind (the oscillation: with its interval) since round g4. There, two 'sigh' mottos differing
    only in grid and an unused interval read as one gesture to every judge.
  - Tempo and meter rules: 16th mottos only at 80 BPM or slower; no triplet motto in 3/4; the ostinato's fast
    grids only at 76 BPM or slower.
  - A tune without set pins draws its own (`perform._set_pins`).
- **The plan:** `perform._signature` reads the pins and records the moves' kinds as piece keys.
  - The keys: `arrangement.SIGN_KEYS` = motto / sig / pause / goose / exit, each the kind or `none`. The student's
    tokens are `AMotto_` / `ASig_` / `APause_` / `AGoose_` / `AExit_` in `learn.tokens.ARR_PIECE`.
  - `perform._sign` writes the moves into the sections, with `_sig` per section. An intro is forced when a motto or
    ostinato is planned.
- **The motto:** `composer.MOTTOS` plus `motto_cell` / `motto_anchor`. The kinds are osc (neighbour oscillation +
  break-off), sigh, toll, call, leap and fall3, on the grid drawn.
  - Anchored (round g5) on the head's first note, the key's 3rd, 5th or tonic (`anchor`), in a register band
    (`register`: `composer.MOTTO_BANDS` low G4-C5 / mid B4-F5 / high Eb5-A5). The band is in the fingerprint, so the
    mottos of a set never share one (g4: three mottos from the head's D5, one "D-C-C" cell to every judge).
  - Never in the left hand's register: a cell under E4 is lifted an octave, and an octave-down recurrence that would
    go under E4 is sequenced instead.
  - Planted in the intro: its left hand silent ('alone') or one held bass ('over_bass'). Over the ostinato instead,
    when both are drawn.
  - Back at the start of up to two seams (inter / build / B2 / the variation / A4): sequenced, an octave away or
    reharmonised.
  - Paid off at the climax's start in the climax register under its peak. Augmented only when that fits two bars,
    because longer augmentations left holes.
  - A fragment in the coda's last two bars.
  - Its long notes snapped to the chord tones; connecting notes kept out of it.
- **The ostinato:** `pianist.ostinato_figure(grid, contour, span, colour, bass)`, a FIGURES token string.
  - The contours: rise, rise_fall, rock, pendulum, alberti and interlock.
  - It is the intro's left hand alone (lh_only 1-2 bars) and every A section's figure (breaths and the bloom keep
    their own). The coda plays it thinned.
  - Under a raised `bass_lo` (the e-piano) its bass stays single.
- **The pause:** the last bar (form bar) before its seam: the climax, the first return after it, or the coda.
  - The kinds: a rolled V7sus4 of the next key with the 4th held; a silence after beat 1 (the pedal up: a dry
    window); a high chord tone alone; the bass alone.
  - A fermata of `hold` beats, after a ritardando, subito, or a diminuendo to pp.
  - The next section starts subito p or forte.
  - This replaces any cadenza there.
- **The goosebump chord:** `perform.GOOSE`, degree -> (semitones, quality): major bVI / iv / bIII / II / III / bVII,
  minor VI / IV / bII / V/V.
  - It goes under the climax's peak note, or the return's first long note. That note must be a chord tone or the 9th
    of the drawn degree; otherwise the next degree is tried.
  - Spliced over the note (2 beats at least), the left hand rolled or in an open 10th, an ff accent or subito p.
- **The cascade:** a link out of the climax (round g5; in g4 it took the bars after the peak note and read as
  "mechanical, texture not music"): the climax's last bar (the bar before when the pause takes it), on one chord,
  under the melody note held from that bar's downbeat, the left hand holding the bass. Chance 0.25, one bar.
  **Retired in round g8 (chance 0):** the g7 judges still heard it as a filler run where the theme should end the
  climax; the code stays (a set can pin it), the signature fallback skips chance-0 moves. The anthem's `augment`
  went too (g8: the theme sung at its own pace, not half-speed).
  - `perform._cascade_notes`: chord tones from two below the held note, down 2.5 octaves (not under the genre's
    `bass_lo`), in groups of 3-4, hands RL or RRL, each group starting lower (a group starting under C4 in the left
    hand). 16ths or sextuplets, the touch falling two levels, a ritardando into the landing (roll / bass / figure).
  - The top-line metrics leave it out as figuration (`composer.sig_spans`: climax_lift, peak_holes, orn32).
- **The record and the tells:** `song.endless_signature` = {'moves', 'statements': [{move, role, at, end, bars, ...}]}.
  `composer.signature_tells` checks them on the notes played:
  - motto_hit, motto_exposed, motto_payoff;
  - sig_share (the share of an ostinato section's bars playing it);
  - pause_s (seconds over the written bar);
  - goose (the note over its chord);
  - casc_span / casc_turns.
  - `tells_newage.py --sets` adds sig_repeat (want 0), sig_max_share (at most 0.4) and sig_none.
- **Round g10 changes to the climax** (docs/PIANIST_RULES.md "After round g9"):
  - The canon payoff (`perform.CANON`, anthem 'canon'). The theme echoes an octave lower, one bar later, before the
    peak unit, as an inner voice. The echo is played at 0.72 x the melody's touch, under the melody note sounding
    over it.
  - A pause at the climax seam goes into a forte climax. A pause after the climax comes out soft.
  - The climax opens at least as loud as the last bars before it (`LOUD_ORDER['enter']`).
  - One shaped peak: the notes before it at 0.95, the peak strike +6, then a taper to 0.85. A near repeat of the
    peak note is lowered a step.
  - The way out: the peak is never in the climax's last unit (`ANTHEM_OUT`). The bars after it fall gradually to
    the theme's level. The tail chords link down by chord tones.
  - The first return after the climax keeps its head (`POST_RETURN`), and the motto is not spliced there.
- **Round g11 changes** (docs/PIANIST_RULES.md "After round g10"):
  - A `sus_hold` pause at the coda seam no longer replaces the last A's home cadence. There it plays as a `rest`:
    the tonic struck, then the silence (`FINAL_A`).
  - The coda opens with the theme's head when its tag is under 6 bars (`CODA`). That is one more place the head
    is heard, after the motto's 'close'.
  - The sung climax plays no cadenza run out of it; it holds its note under the fermata.
  - Two set draws spread the climax across a set: its peak 0-4 semitones under the ceiling ('peak') and its
    favoured left-hand figure ('big').
- **Round g13 changes** (docs/PIANIST_RULES.md "After round g12"):
  - Every sung climax opens with the head at its own degrees, then the head a third higher, then the peak
    (`perform.ANTHEM_HEAD`, GZAT's plan; it was the 'sequence' anthem's alone). The anthems differ by texture.
  - The climax's key move is a step up or the parallel major only (`SUNG_KEYS`).
  - The motto's payoff answers the peak when it cannot come before it; no empty bar after it.
  - The coda's length is a draw (`CODA['bars']`: 6 or 8 bars at least).

## Sources

Research read for this document (no audio, no scores downloaded; mechanisms only):

- Wikipedia: [Clair de lune / Suite bergamasque](https://en.wikipedia.org/wiki/Clair_de_lune_(Debussy)) (9/8,
  "un poco mosso" middle section, D-flat major), [Gymnopédies](https://en.wikipedia.org/wiki/Gymnop%C3%A9dies)
  (3/4, the alternating major-7th chords on IV and I, "lent et douloureux", the mild dissonances),
  [Piano Sonata No. 14](https://en.wikipedia.org/wiki/Piano_Sonata_No._14_(Beethoven)) (the triplet figuration, the
  octave bass, "senza sordino", pp throughout).
- [Classical Ex-Burns: Ludovico Einaudi, I Giorni](https://classicalexburns.com/?p=3853) (the repeating left-hand
  accompaniment, the melody stated plainly then decorated with triplets, 16ths and grace notes) and
  [Brilliant Classics: Einaudi piano music](https://brilliantclassics.com/articles/e/einaudi-piano-music) (the
  minimalist framing).
- General music-theory knowledge of the standard repertoire (Für Elise's rondo and its refrain texture, the Chopin
  nocturnes' fioriture, Liszt's Liebestraum cadenzas and tenor strophe, Rachmaninoff's op. 3 no. 2, Yiruma, Tiersen,
  George Winston's left-hand style, film-piano practice), summarised as mechanisms in our own words.
