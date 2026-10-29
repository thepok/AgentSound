# The pianist's performance rules

What the rule-based pianist does to written notes to play them like a person, where each rule lives, and the
research it comes from. No human performance data and no learned model: every rule is a published finding written
as a distribution or a budget in a table that its owning tool keeps.

## Which layer plays the piano

The endless piano genres (`new-age-piano`, `classical-piano`, `lofi-piano`, `new-age-epiano`) and the hand-written
`songs/pro-newage-*` references are played by the ROMANTIC pianist, `romantic.Score.perform`. `jazz-piano` uses
`pianist.arrange` instead and shares only the left hand's broken-chord figures (`pianist.figure`). Three layers act
on the notes, in this order:

| layer | what it owns | where |
|---|---|---|
| tempo lanes | phrase rubato (`song.rubato`), ritardandi and fermatas, the beat-level lilt | `song.py`, `tempo.py`; set by `endless/perform.build_piano` or the song |
| `Score.perform` | touch per phrase, singing line, dynamics, the melody's timing against the left hand, chord spread, charge, articulation, pedal | `romantic.py` (`RULES`), `humanize.touch`, `pianist.figure` |
| the body | one gesture per phrase: the Todd arc, phrase-end and final ritardandi, hand travel after leaps, breaths, weight in the bar, motor noise; the left hand follows the right | `humanize.Body` / `BODIES`, applied at compile (`track.humanize(body=)`) |

`Score.perform(..., rules={'async': {'max_ms': 30}})` overrides single values; unknown families or keys are errors.

## The rule tables

Ranges marked "approx." are summaries of the cited studies, not one measured number. Velocity is MIDI velocity;
on the Salamander grand one velocity step is about 0.25 dB.

### Asynchrony: `romantic.ASYNC` (`travel_ms`, `spread`, `melody_rubato(lead=, anticipate=)`)

| rule | source | published range | value |
|---|---|---|---|
| Melody lead as a velocity artifact. The louder note's hammer reaches the string first, so a voiced melody sounds before the accompaniment struck with it, by more when the velocity gap is wider. Modelled as hammer travel time `a / (vel + b)`, the melody earlier by the difference. | Goebl 2001; Palmer 1989, 1996; Repp 1996a | melody 20-40 ms ahead on average (approx.), rarely beyond 50 ms; the lead correlates with the velocity difference | `travel` (4000, 20): about 25 ms for a 30-step gap at mp. `max_ms` 45, `sd_ms` 5 |
| Chord spread. Notes struck together sound in hammer order, loudest first, plus the hand's own scatter. | Goebl 2001; Repp 1996a | non-melody asynchronies within about +-15 ms (approx.) | `chord_sd_ms` 8 (half-normal), capped at `max_ms` |
| Bass anticipation. A share of the long notes on a half-bar anchor follow the bass, the romantic expressive asynchrony. | Vernon 1936; Goebl 2001 | an occasional device; 30-70 ms in Romantic-era recordings (approx.) | `anticipate` 0.12 of the long anchor notes, `anticipate_ms` 25-55 |
| Melody push-pull inside a half bar (Chopin's rubato, kept small). | the nocturne etude's concert recording (songs/nocturne-etude) | melody vs bass at the bar lines: SD about 47 ms in that recording | `lean_ms` 18, `sync_ms` 14 |
| Agogic accent on a melodic summit (a long local top arrives late). | Repp 1992 (summit lengthening); DM *leap tone duration* | tens of ms | `peak_ms` 25 |
| Left-hand chords (`spread(hand='lh')`) hold no melody, so they have no fixed loudest-first order. Each chord draws either near-simultaneous (half the velocity artifact plus a small scatter) or rolled from the bass up; a soft chord rolls wider. | Repp 1996a; Goebl 2001 (non-melody asynchronies are small); the arpeggio sign is played upward by convention | within about +-15 ms (approx.) | `lh_roll` (0.6 together, 0.4 bottom-up), `roll_ms` 4-10 per note x softness |
| Now and then an arpeggiated cadence chord: a phrase's last harmony rolled slowly up from the bass. | Vernon 1936 (spread chords in artistic playing) | an occasional expressive device | `arp` 0.4 of the phrase-end chords, `arp_ms` 35-70 per note (not capped by `max_ms`) |

The right hand also takes the left hand's groove lay-back. The jazz band feel lays the melody hand back about 12 ms
against the comping, but a solo pianist is one player.

### Voicing: `pianist.FIGURE_VOICING`, `Score.perform(inner=)`

| rule | source | published range | value |
|---|---|---|---|
| Melody over the accompaniment (a level budget). | Palmer 1996; Repp 1996a; Goebl 2001 | melody about 10-25 velocity steps above the other voices (approx.) | `touch` lo/hi against `figure_vel` 41: about +30 at shared onsets, measured |
| Melody over the inner notes of its own chords. | as above | | `inner` 0.78: +20 measured |
| Bass over the left hand's inner notes (melody > bass > inner). | piano pedagogy; Palmer 1996 | | `bass` 1.16 x the figure's level, about +3 to +11 measured |

### Pedal: `romantic.PEDAL` (`pedal_changes(delay_ms=, half=, vary=)`)

| rule | source | published range | value |
|---|---|---|---|
| Syncopated (legato) pedal. The pedal goes up just after the new harmony's onset, so the new keys are already down and their notes are caught, then down again. | Repp 1996b | release some tens to about 150 ms after the onset, re-depression about 100-200 ms after it (approx.); both scale with the tempo | `delay_ms` 60, `lift_ms` 110, x (72/BPM)^0.5 |
| The foot is no clock. | Repp 1996b | timing varies from change to change | `vary` 0.25 (x 1 + N(0, 0.25), within 0.5..1.6) |
| Half change at the resolution of a melodic non-chord tone inside a harmony of 2+ beats: the treble dampers touch, the bass rings on. | Banowetz 1985 (half and flutter pedalling) | | `half_to` 0.6, `half_beats` 2 |
| A new chord over the same bass gets a half change, not a full one. | Banowetz 1985 | | `same_bass` 'half' |
| Chromatic runs are cleared by quick half lifts. | the nocturne etude | | `flutter_ms` 320, `flutter_to` 0.6 |

### Charge: `romantic.CHARGE` (`melodic_charge`, `harmonic_charge`)

The charge rules are shared with the orchestra. They live in `agentsound/expressive.py` (with punctuation, high-loud
and the correlated timing), and `romantic` imports them, so the pianist's behaviour is unchanged. The orchestra's
use of them is in [ORCHESTRA_RULES.md](ORCHESTRA_RULES.md).

| rule | source | published range | value |
|---|---|---|---|
| Melodic charge. Leaning on melody notes far from the chord root on the circle of fifths: 9th, 6th, major 7th, #11 and b9 are emphasized; root and 5th rest. | Sundberg, Friberg & Frydén 1991; Friberg 1991 (KTH / Director Musices) | +0.2 dB per unit of charge at k = 1 (approx.) | 0.6 velocity per unit; `pcs` is the charge table (circle-of-fifths distance, +0.5 on the flat side) |
| Harmonic charge. The level grows toward a chord far from the tonic (ii, vi, bII, bVI, secondary dominants) and relaxes after it, linearly between the changes. | as above | a few dB at the most remote chords (approx.) | 1.4 velocity x sqrt(charge); the left hand uses `ACCOMPANIMENT['charge']` 2.4 x `lh_dyn` |

### Phrase tempo: `romantic.PHRASE_TEMPO` (`Score.rubato`, `Score.lilt`; `song.rubato(peak=, close=)`)

| rule | source | published range | value |
|---|---|---|---|
| Every phrase gets its own arch. The depth of the tempo arch differs from phrase to phrase, and some phrases are played nearly straight. | Repp 1992 (the timing profiles share a shape but differ in depth); Todd 1985 | | depth x U(0.4, 1.6); `straight`: 0.15 of the phrases at x 0.2 |
| The phrase's fastest point moves. | Todd 1985 / 1992 (the arch follows the phrase's own structure) | | `peak` U(0.3, 0.8) for a phrase, (0.25, 0.7) for a period, (0.2, 0.55) at the end |
| Final lengthening grows with the depth of the boundary. A phrase inside a period closes lightly, the period's cadence closes more, and the piece's end closes most. | Todd 1985; Repp 1992; Penel & Drake 1998 | phrase-final IOIs lengthened by tens of % at section ends (approx.) | `close` (x the depth at the end) by level: U(0, 1) / U(0.6, 1.5) / U(1.2, 2) |
| The beat lilt is not a fixed delay in every bar. Each phrase draws how much of it to play, and the per-beat jitter stays small because the phrase carries the shape. | Hennig et al. 2011 (correlated, small beat fluctuations); the round-1 judges (a sawtooth tempo map) | | `lilt` x U(0, 1) per phrase, `lilt_jitter` x 0.4 |

A fioritura that a forward-moving phrase would push past its `max_rate` is played with a flatter shape (ease
0.8 -> 0.55 -> 0.3 -> 0): the pianist evens the gesture out instead of the run failing.

`Score.rubato(phrase='drawn')` is the default. A phrase's level is 'phrase'; every second phrase is a 'period', and
the last is the 'end'. The draws are seeded by the song's seed and the phrase's first bar, so no two pieces share
them. `shapes=` and named shapes still work for the hand-tuned etudes.

### Left-hand dynamics: `romantic.ACCOMPANIMENT` (`Score.perform(figures=)`)

| rule | source | published range | value |
|---|---|---|---|
| The accompaniment follows the phrase arc, at a smaller range than the melody. | Todd 1992 (dynamics follow the phrase); piano pedagogy | | `arc` U(0.12, 0.28) per phrase, cresting at `peak` U(0.45, 0.75) |
| It also follows the melody's level. | Palmer 1996 (voicing as a whole-texture plan) | | x (the melody now / its phrase mean) ^ `follow` 0.4 |
| It swells into a tension chord and relaxes at the resolution. A tension chord holds a tritone (a dominant 7th, a diminished chord) or resolves down a fifth. | Sundberg, Friberg & Frydén 1991 (harmonic charge) | | `tension` +3 velocity; `charge` 2.4 x sqrt(harmonic charge) |
| The balance of bass and figure shifts across the phrase. | piano pedagogy | | the bass x U(0.92, 1.1) at the phrase's start and end, linear between |
| Level budget: in every phrase the accompaniment sits under the melody. This holds wherever the melody plays; a left hand alone keeps its own level. | Palmer 1996; Goebl 2001 | melody about 10-25 velocity steps above the other voices (approx.) | `below_db` 6: the phrase's LH median at least 6 dB (velocity) under the melody's - without a balance plan only |
| A balance plan (`Score.perform(balance=[(from, to, dB)])`, the endless pianos): each phrase is set to its span's dB, up or down - the hands' summed note energy ((velocity / 127) ^ `ENERGY_EXP` 2.5, about the stems' RMS), the left hand never struck over the phrase's loudest melody note. | Palmer 1996 (voicing as a whole-texture plan); the user, HUMAN_FEEDBACK 2026-10-15 | melody a few dB over the accompaniment, not a constant | `scale` 0.55-1.9 per phrase; the plan: see "The hands' balance" below |
| Give and take (with a balance plan). The left hand recedes under a melody note just struck and swells into the melody's held notes and rests; in a phrase's last bar it leads the way on. | the user (2026-10-15); piano pedagogy (the accompaniment fills the melody's gaps) | | `take` x0.93 -> `give` x1.24 from 0.6 to 2 beats after the melody's onset (`give_beats`); `lead_end` +12 % of it |

### Articulation: `romantic.ARTICULATION` (`articulate`)

| rule | source | published range | value |
|---|---|---|---|
| Repetition articulation. A key struck again must come up first. | Friberg 1991 (DM *repetition articulation*); Bresin & Battel 2000 | a micro-pause of some tens of ms | 25 % of the IOI within 40-90 ms |
| Leap articulation. The note before a wide leap lets go early. | DM *leap articulation* (Friberg et al. 2006) | grows with the interval | 7+ semitones: 15 ms (at a 5th) to 45 ms (at two octaves) |
| Finger legato. The key overlap grows with the IOI and is never the same twice. | Repp 1997; Bresin & Battel 2000 | legato overlap of some tens of ms; key overlap ratio roughly 5-20 % of the IOI (approx.) | `legato` KOR N(0.07, 0.03), within 12-100 ms |

### Rules that were already in place (unchanged, cited here)

| rule | source | where |
|---|---|---|
| Phrase arc: tempo and loudness rise together into the phrase peak and relax together (+-8 % tempo, +-7 % level). | Todd 1992; DM *phrase arch* | `humanize.Body` arc_ms / tempo / arc_vel |
| Phrase-final and final ritardando on the decelerating-motion curve v(x) = (1 + (w^q - 1) x)^(1/q). | Friberg & Sundberg 1999 | `Body` rit_* / end_*, `humanize.rit_curve` |
| Hand travel. A note after a leap beyond a 4th arrives late (about 2 ms per semitone, at most 25 ms). | DM *leap tone duration* / hand-shift studies | `Body.leap_ms` |
| High-loud. About 0.9 velocity per semitone above the phrase mean, about 0.22 dB/semitone, near DM's 3 dB/octave. | Friberg 1991 (DM *high loud*) | `humanize.touch(pitch=)` |
| Duration contrast. Long notes get more tone, short passing notes are lighter. | DM *duration contrast* | `lean_on_long`, `touch(passing=)` |
| Dynamics follow the melodic contour and the phrase goal, not the beat. | Todd 1992; the blind rounds (touch's docstring) | `humanize.touch` |
| Metrical weight stays subtle (+4 % / -2.5 % per beat position). | Sloboda 1983 | `Body.sway` |
| Correlated beat-level timing. The lilt's jitter is AR(1) with rho 0.6, not white: human timing fluctuations are long-range correlated, and white per-beat jitter reads as a sawtooth tempo. | Hennig et al. 2011 | `tempo.LILT_RHO`, `song.lilt(jitter=)`; drawn per phrase by `Score.lilt` |

## Audit and A/B (2026-10)

Measured on the compiled notes (body, tempo map and groove applied) of three pieces with the same notes:
`songs/_demo_pianist/newage` (endless new-age-piano, seed 5), `.../lantern` (`songs/pro-newage-lantern`) and
`.../classical` (endless classical-piano, seed 3). Old vs new:

| measure | new-age | lantern | classical | published |
|---|---|---|---|---|
| melody lead over the LH, mean / median ms (+ = melody first) | -18.7 / -12.9 -> **+19.2 / +20.6** | -19.8 / -12.4 -> **+19.6 / +20.6** | -15.8 / -15.0 -> **+8.3 / +10.9** | +20..40 |
| melody first, share | 0.18 -> 0.85 | 0.18 -> 0.91 | 0.29 -> 0.67 | most onsets |
| lead vs velocity gap, r | 0.01 -> 0.43 | 0.07 -> 0.24 | -0.02 -> 0.24 | positive |
| RH chord spread, ms (top first by) | 1.2 -> 17.6 (15) | 1.3 -> 13.8 (12) | 1.2 -> 15.2 (14) | ~10-20 |
| LH chord spread, ms | 0.8 -> 9.4 | 1.4 -> 13.7 | 1.1 -> 5.7 | ~10 |
| bass over the following LH notes, velocity | +0.2 -> +2.8 | +1.2 -> +5.0 | +6.5 -> +11.3 | > 0 |
| pedal up / down after the harmony change, ms | 0 / 109 -> 60 / 171 | 0 / 110 -> 54 / 153 | 0 / 107 -> 72 / 192 | 40-150 / 100-250 (approx.) |
| half-pedal points | 0 -> 41 | 0 -> 35 | 10 -> 23 | |
| melody legato overlap median / p90, ms | 27 / 37 -> 39 / 88 | 22 / 28 -> 37 / 92 | 35 / 47 -> 64 / 106 | tens of ms, varied |

The audit found that the melody came LATE against the left hand. The jazz band feel's lay-back put the right hand
12 ms behind the comping hand, and melody_rubato's 6 ms downbeat delay plus a +-42 ms spread on every anchor added
to it. Chords sounded within 1-2 ms, which no hand does. The pedal came up exactly on the change. The bass was not
voiced above the LH's inner notes.

Unchanged: the tempo phrase arcs (+3 % into the middle of a phrase, 0.88-0.92 in its last tenth), the phrase-final
lengthening (x1.10-1.25), the melody's dynamic arc per phrase and high-loud (r 0.2-0.5).

- **Learned ears** (`python -m agentsound ears`, realism). New-age 80.5 -> 80.7, lantern 83.6 -> 84.9, classical
  79.4 -> 79.2. That is neutral to slightly better: the ears hear sound quality more than micro-timing.
- **Blind judge panel.** Three judges with identical prompts saw anonymised plots and numbers, A/B shuffled per
  piece. Old vs new: 9 of 9 votes for new in round 1 and again in the final round (confidence 3-5). The
  intermediate round (round-1 rules vs the iterated ones) went 9 of 9 for the iterated rules. The iteration added
  the varied pedal foot, finger-legato variety, correlated lilt jitter, a stronger bass, the same-bass half change
  and a smaller lean / anticipation.
- **Gates.** 0 clicks, 0 silent notes, no warn-level flat_dynamics. Integrated loudness is +0.4 to +0.7 LU, inside
  the genres' windows.

### The judges' remaining tells

Round 2 (below) fixed the first four. The fifth is still open in TODO.md.

- The tempo phrase template is the same in every piece.
- The beat-level tempo still looks jagged in the tempo map, from the fixed beat-3 lilt.
- The left hand's accompaniment dynamics are flat (velocity SD 6-7).
- Left-hand chords roll in a fixed top-down order (crest velocities).
- The classical melody lead is small (+8 ms) under its rubato.

### Where the sound changed

These songs' render JSON changed when the rules came in (each song compiled before and after):

- every `Score.perform` user: `songs/pro-newage-*` (11 songs), `letters-to-the-morning`, `nocturne-etude` (its
  'after'; NOTES.md's numbers are from before the rules), and the endless `new-age-piano`, `new-age-epiano`,
  `classical-piano` and `lofi-piano` tunes;
- the correlated lilt jitter: `gymnopedie-etude`, `when-the-year-turns-gold`;
- the bass voicing of `pianist.figure`: the endless `jazz-piano` tunes whose left hand plays a broken-chord figure
  (`songs/_endless_jazz_piano`).

Unchanged: `pro-piano-*`, `pro2-piano-*`, the organ pieces and the band songs. Because the endless score reads the
performed notes, the score baseline was re-measured, and the best-of-N order moved for new-age and classical.

## Round 2: phrase tempo, left-hand dynamics, left-hand rolls (2026-10)

Round 2 uses the same three pieces and the same notes. ab2_old plays round 1's final rules and ab2_new plays these
(`songs/_demo_pianist/<piece>/out/ab2_old.mp3` and `ab2_new.mp3`). Old -> new:

| measure | new-age | lantern | classical | target |
|---|---|---|---|---|
| beat-to-beat tempo zigzag, median / p90 % (a beat's IOI against its neighbours' mean) | 5.5 / 12.4 -> **2.5 / 6.8** | 5.1 / 12.7 -> **2.7 / 10.4** | 4.7 / 11.2 -> **2.1 / 6.0** | small; the phrase carries the shape |
| IOI direction flips, share of beats | 0.66 -> 0.57 | 0.72 -> 0.60 | 0.69 -> 0.51 | white noise: 0.67 |
| phrase lane (rubato alone): swing SD between phrases | 0.012 -> 0.053 | 0.010 -> 0.039 | 0.017 -> 0.083 | varied |
| phrase lane: final lengthening, mean | 1.016 -> 1.067 | 1.009 -> 1.059 | 1.019 -> 1.102 | > 1, deeper at section ends |
| LH roll order: together / bottom-up / top-down | 0.10 / 0.06 / **0.76** -> 0.57 / 0.27 / 0.10 | 0.16 / 0.09 / **0.63** -> 0.40 / 0.40 / 0.12 | (6 chords, all together) | not top-down |
| LH per-phrase range (per-bar mean, p10-p90 dB) / the melody's | 1.4 / 2.5 -> 2.3 / 2.4 | 1.6 / 2.5 -> 2.3 / 2.4 | 1.0 / 2.6 -> 1.3 / 2.4 | below the melody's, not flat |
| melody over the LH, phrase medians, dB (velocity) | 5.4 -> 5.7 | 5.6 -> 5.8 | 4.1 -> 6.3 | budget >= 6 |

The remaining top-down share comes from the figure's own rolled tokens and from figure notes that fall into the
audit's 20 ms clusters. The melody lead (+18 / +19 / +7 ms), the RH chord spread and the pedal are unchanged.

- **Learned ears** (realism): new-age 80.4 -> 80.0, lantern 84.9 -> 85.5, classical 79.2 -> 81.1. Neutral.
- **Blind judge panel** (the same prompt, three judges, A/B shuffled): 9 of 9 votes for the new rules, on an
  intermediate setting and again on the final one (confidence 3-5). The judges cited a smooth tempo against a
  sawtooth, left-hand rolls bottom-up or together instead of top-down, clearer phrase-end lengthening, and the
  accompaniment staying under the melody.
- **Gates.** 0 clicks, 0 silent notes, no new warn-level warnings (classical's info-level flat_dynamics note is
  unchanged). Section loudness is within 0.7 LU, except new-age's coda (2.0 LU quieter) and lantern's interlude
  (1.1 LU quieter).

Still open (TODO.md):

- The phrase arcs are still alike within a piece: tempo-shape correlation 0.7-0.85, every phrase "faster in the
  middle, slower at the end".
- The pedal timing looks clockwork.
- The melody lead is a near-constant offset, and the classical lead stays small.
- The tempo collapses below 12 BPM at fermatas.
- The accompaniment figure has no shape inside the bar.

Where the sound changed:

- every `Score.perform` user with a broken-chord left hand: `songs/pro-newage-*`, `letters-to-the-morning` and the
  endless piano genres;
- `Score.rubato` / `Score.lilt` replace the fixed shape cycle and `song.lilt` in those songs and in
  `endless/perform.build_piano`;
- the left hand's `spread` in the `accompany()` path (`nocturne-etude`).

## The bloom and the hand-to-hand figure (2026-10-15)

The user on the endless new-age pieces and the learned student's renders: "they lack a blossoming where the tempo
gets faster and more happens; they just ripple along; bass and lead always very clearly separated; nothing flowing
like Für Elise, where it is played across the whole keyboard" (recipes/HUMAN_FEEDBACK.md). Measured on the six
`na_final` pieces before the change, every climax was slower than A1 (section means 0.88-0.94 of A1's tempo). The
right hand played 0.6-1.7 notes a beat in every section. The left hand never rose above G4 (its cap) and the melody
never went below E4, so the hands split at E4 / G4 in every bar.

What the players do now. All of it is in one table, `genres._NA_BLOOM` (`plan['bloom']`, validated strictly), and is
drawn per piece from its own seed. It is not in the arrangement record: like the left hand's figures it is a texture
decision, so a student's decoded tune blooms by its seed too, and the student's token vocabulary is unchanged.

| rule | where | value |
|---|---|---|
| One section blooms: the build, the chorus or the climax. | `perform._bloom`, `at` | build 1.0, B1 0.35, climax 0.3 |
| The tempo pushes forward: an accelerando over the first part of the section, then held. A blooming climax pushes up to a beat before its peak note. | `push`, `reach` | x1.04-1.10; reached at 40-65 % of the section |
| The bloom breathes lightly into the next section, not with a full ritardando. | `rit` | 0.93-0.98 (a section's own rit: 0.8-0.9) |
| The climax after a bloom keeps part of the push. It is broad only at its peak, where its fermata and final ritardando stay. | `carry` | 50-100 % of the push |
| The left hand grows in two stages, one figure per 2-bar unit: triplets or 8ths first, then 16ths from `reach` on, over two and a half octaves. | `figures`, `pianist.FIGURES` trip12 / span16 / wave16 / waltz_span / waltz_wave | |
| The left hand rises to the melody. Its cap goes up to a whole step under the lowest right-hand note (at most `lift` over the usual G4), and the figure turns at the cap instead of folding an octave down. | `perform._lh_reach`, `pianist.figure(mirror=True)` | `lift` 12 |
| The woven right hand (once the bloom has grown). Under a melody note held a beat or more, the right hand plays the chord's tones below it in 16ths / triplets, softer, while the melody note rings in the pedal. At a phrase end it leaves a beat of breath. The left hand turns under the woven notes there. | `_handoffs`, `weave`, `grid` | x0.7 velocity |
| The hand-to-hand figure (Für Elise's A section). In a bar whose melody note is struck by the half bar and held to the next downbeat, the left hand climbs and holds, and the right hand carries the figure on from just above it into the next melody note: the chord's tones, or the chord's scale in the key the section plays in when the chord has too few there (round g1). It is never placed into a phrase end, and it is phrase-shaped: full chance in the bars that lead into the phrase's half and its goal, less elsewhere, much less right after another one, each with its own grid (round g1). | `_handoffs`, `handoff`, `bloom_hand` / `hand` (ring / up / ring16 / up16 / waltz_hand / waltz_up / waltz_hand16) | bloom 0.85 per held bar; elsewhere A 0.12, B 0.2, C 0.25 |
| The bloom's last bar runs on into the next section. | `link` | 0.5 |
| A blooming genre's climax keeps its left-hand figure for 2 bars (a student blind judge: "16ths / 8ths toggling strictly bar by bar" read as a machine). | `_play_piano` | |

The score checks it (`composer.bloom_tells`, new-age table only; the other styles' scores and the score baseline are
unchanged):

| metric | what | range (weight) |
|---|---|---|
| `tempo_push` | the tempo the fastest body section holds (its beats' median) over the first body section's | 1.03-1.12 (1.5) |
| `climax_tempo` | the climax section's mean tempo (fermata included) over the first body section's | 0.93-1.06 (1) |
| `rh_peak_den` | right-hand onsets per beat in the densest 4-bar window | 1.6-3.2 (1) |
| `flow32` | figures per 32 bars that run 8ths or faster in one direction over two octaves, with notes from both hands | 4-14 (0.5) |
| `hand_meet` | share of bars where the left hand's top comes within a whole step of the right hand's lowest note (reported, not scored) | |
| `orn32` | (widened 5.5 -> 7: the bloom's 16ths under the melody's rubato count as ornaments) | 0.4-7 (0.5) |

These ranges are not the references' ranges. The twelve hand-written references do not push forward either
(`tempo_push` 1.0-1.07, `climax_tempo` 0.80-0.99, `flow32` 0-2.9), so they now score a little lower under the
new-age table. That is intended: the user's remark applies to them too.

Before and after. The set `songs/_endless_piano/out/bloom_v1` is six new pieces: `endless new-age-piano --count 6
--seed 61000`, best-of-8, all six through the render gate. Each piece is measured as played and again with
`plan['bloom'] = None` (the same tune). The set plan drew no waltz, so the 3/4 tables are covered by the tests only.

| measure (mean, min..max over 6) | before: the same tunes, no bloom | after: bloom_v1 |
|---|---|---|
| bloom section tempo / A1 (section means) | 0.99 (0.98..1.00) | **1.06** (1.03..1.07) |
| `tempo_push` | 1.002 (1.00..1.01) | **1.063** (1.04..1.08) |
| `climax_tempo` (fermata included) | 0.916 (0.90..0.93) | **0.964** (0.94..1.00) |
| right-hand onsets / beat in the bloom section | 1.00 (0.88..1.18) | **1.42** (1.16..1.67) |
| left-hand onsets / beat in the bloom section | 1.85 (1.44..2.00) | **3.02** (2.56..3.25) |
| `rh_peak_den` | 1.24 (1.12..1.31) | **1.78** (1.44..2.06) |
| bloom: right hand's lowest vs left hand's highest note | RH above LH in 4 of 6 | **RH dips under the LH top in 6 of 6** (e.g. RH 61 / LH 72) |
| `flow32` | 2.6 (0.7..5.7) | **5.1** (3.8..5.8) |
| quiet1 (render gate >= 0.25) | 0.321 (0.26..0.36) | 0.291 (0.25..0.32) |
| phrase_rests | 0.88 | 0.88 |
| new-age score (the new table) | 94.8 | 98.7 |
| clicks / silent notes / warn-level flat_dynamics | - | 0 / 0 / 0 |

The user's `na_final` set (six pieces, the old players) measured `tempo_push` 1.00, `climax_tempo` 0.88-0.94,
`rh_peak_den` 0.94-1.31 and `flow32` 1.4-5.6.

A cheap blind check: one judge agent saw piano rolls only (no audio, no key). For each piece it got the same tune
with and without the bloom, A/B shuffled. It preferred the bloom version in 6 of 6 pairs (confidence 2-4). Its
reasons were the left hand rising to meet the right hand in the build, more notes, and the tempo lifting. It also
named three tells:

- Two-tone rocking in the woven right hand. Fixed: the weave now needs three chord tones.
- The push starts at the section line (Ideas #18).
- Every climax ends in the same tempo collapse over the same low octave walk (Ideas #17).

The judge also said the hands overlap but do not yet trade one figure back and forth as in Für Elise. Hand-offs are
2-6 per piece, limited by the melody's rhythm (TODO.md).

## After the all-generated blind round g1 (2026-10-15)

Round g1 (songs/_blind/ROUNDS.md) gave the judges ten generated pieces without telling them. They estimated 4.8 of
10 as generated. Their tells were fixed in the teacher, mostly as data. `songs/_blind/tells_newage.py` measures them on
a seed range without audio.

| g1 tell | fix | where |
|---|---|---|
| Runs and fills in the home key's scale over a borrowed chord or a section in another key (all five judges) | Every hand-off run, turn and cadenza takes its notes from the chord's scale in the key the section plays in. A section moved by `_modulate`, a 'step' climax and their pivot bars are tracked as key spans. A turn's neighbours come from that scale, and a mordent is placed only where the key's neighbour is in it. The woven figure stops where its chord ends, so it never carries a chord over the bar line. | `perform._key_spans`, `_local_scale`, `_orn_steps`, `_handoffs`; `song.endless_keys` |
| The climax not derived from the theme: an octave or key transplant, chord tones tiled | The set and section climax weights favour `grow` and `theme`. `climb` and `lift` (the chorus an octave up) are rarer, and a climax stays in the home key more often. Half the `grow` climaxes open with the hook augmented: its rhythm and contour twice as slow, raised, over the climax's reharmonised chords. | `plan['set']['climax']`, the climax section's `climax` / `key`, `plan['grow_aug']`, `_grow(aug=)` |
| The same 16th run on beat 4 of every build or climax bar | The hand-off is phrase-shaped. It has full chance in the bars leading into the phrase's half and its goal, `goal` (0.45) elsewhere, and `goal / 2` right after another one. Each hand-off may take its own grid (16ths, triplets or 8ths). The woven figure follows a woven bar only by the same chance. | `plan['bloom']` `goal`, `regrid`, `grids` |
| Returns copied, 7-8 of 8 bars; one opening rhythm in three pieces | Every return draws a reharmonisation (`reharm` 0.7 in 60-70 % of them) and keeps a unit as written less often (`vary`). An inversion that ran over the range's top no longer folds onto one repeated pitch. The theme's opening cell is a set draw with no repeat in 3 slots. | the A2 / A3 / A4 sections' `reharm` / `vary`, `_vary`, `plan['set']['opening']` |
| 0.08-beat "chord grabs" | A packet artefact. A turn's four quick notes were chained into one cluster and printed as a chord. The packets now print an ornament as `(a b c) note`, and the turn's neighbours are fixed as above. | `make_packets_newage.py` |
| The waltz: the right hand silent in intro / interlude / coda stretches, 'X / X-inversion' pairs, the climax thinner than its build | A frame line written for half of a waltz's doubled bars is augmented to fill them. Before, the coda had 4 empty bars and an interlude could have no line. A failed `ped` move tries a substitute instead of the chord over its 5th, and the `bass` move is rarer. A climax right after the bloom keeps part of its hand-off chance (`carry`). | `_piano_plan`, `_moving_bass`, `plan['moves']`, `_handoffs` |

Before and after, measured by `tells_newage.py` over seeds 64000-64047 (48 pieces, 8 waltzes; compose without a set
plan):

| measure (mean) | before | after |
|---|---|---|
| figure / ornament notes outside the local chord scale, per piece | 2.23 (39 of 48 pieces) | **0.21** (8 of 48) |
| build / climax bars with a beat-4 run; the longest streak | 7.7 %; 0.98 (max 4) | **6.2 %; 0.67 (max 2)** |
| the climax an octave transplant (lift / climb); in another key | 33 %; 29 % | **8 %; 23 %** |
| returns: the share of bars whose chord equals the earlier A's | 0.76 | **0.55** |
| returns: the share of bars whose line equals the earlier A's | 0.63 | 0.59 |
| waltz: bars without a right-hand note; the longest such stretch | 3.9 %; 2.75 bars | **0.8 %; 0.9 bars** |
| waltz: 'X / X-inversion' bar pairs per piece | 16.5 | **3.4** |
| new-age score (no best-of-8) | 95.8 | 96.3 |
| `rh_peak_den` / `flow32` / `tempo_push` / quiet1 | 2.17 / 3.31 / 1.062 / 0.287 | 1.70 / 3.13 / 1.062 / 0.301 |

The bloom's peak density came down (2.17 -> 1.70, inside the score's 1.6-3.2) because the runs and the woven figure no
longer fill every bar. The pinned opening cell raises the arc check's rejects, from 34 % to 44 % of the seeds.

Round g2 (ten pieces with these fixes, seed 64000) did not lower the count. It rose to 6.2 of 10 (g1 4.8), with 31 of
50 verdicts 'generated'. The g1 tells no longer appear as patterns in the judges' reasons. Instead, the judges compared
the pieces with each other and named templates shared across the set:
- one form skeleton, with the peak at 71-76 % in 10/10 pieces (Ideas #6);
- climax routes and build progressions repeated between pieces;
- the `grow` climax tiling the hook's head cell bar by bar (Ideas #1: a 4+4 phrase with one peak);
- the hand-off broken chord used as a stock gesture.

These are the next targets (TODO.md, the bloom 6).

## The hands' balance and the register (2026-10-15)

The user, on the 1 h new-age set: "the right hand always feels louder than the left", "it should be dynamic too",
and "too many very high notes". Measured: the right hand 4.6-8.1 dB RMS over the left per piece and +4..+9 in
nearly every section. The cause was the fixed level budget (`below_db` 6: every phrase's left-hand median at least 6
dB of velocity under the melody's). Raising `lh_vel` alone moved the balance by only ~0.5 dB, because the budget
pulled it back. The register: a 'theme' climax was always the theme an octave up (up to C7), and octave-up returns
put whole sections over C6.

| rule | where | value |
|---|---|---|
| A balance plan per piece: dB of the right hand over the left per phrase, in summed note energy ((velocity / 127) ^ 2.5: many soft notes add up like the stems' RMS), set both ways. | `romantic.Score.perform(balance=)`, `_lh_balance`; `perform._balance` | `ENERGY_EXP` 2.5 |
| Per section, over the piece's base: a theme's first statement keeps a clear melody, a return less, B less, the build and the bloom near equal (the left hand carries the motion), the climax both strong, the coda close; jittered per section. | `perform.BALANCE`, `_role`; play key `balance` {4.5, 5, 5.5} | A1 +1.5, A +0.5, B -0.5, build -1.5, bloom -3, climax / coda / inter -1, intro -1, jitter +-1.5 |
| The left hand leads a phrase or two: the melody's quietest-moving phrases of a return or the B section (the fewest onsets, drawn among three, never two running). | `perform._balance`; play key `lh_lead` {0, 1, 2} | `lead` +1 dB (renders 2-5 dB left-leading: the held melody decays) |
| Give and take inside the phrase: the left hand recedes under a melody note just struck, swells into held notes and rests, and leads the way on in the phrase's last bar; it never strikes over the phrase's loudest melody note. | `ACCOMPANIMENT` give / take / give_beats / lead_end | x0.93 -> x1.24 over 0.6-2 beats; +12 % in the last bar |
| The register's ceiling: an octave-up section only where its line stays at or under D6; an octave-up 'theme' / 'climb' climax (with its sequel a step higher), a 'lift', a climax in another key and a grown peak at or under F6, else the climax grows from the hook. | `plan['ceiling']` {'line': 86, 'peak': 89}, `perform._arrange` (new-age; not the orchestra) | |

Velocity is the tool (touch), so the piano's tone changes with the level; no track gain moves. The other endless
pianos (classical, lofi, e-piano) play the same plan with the default base 4.5 dB. Without `balance=` (the
hand-written songs) the fixed budget stays.

Measured: `composer.hands_tells` (hand_bal, hand_bal_sd, hand_lead, rh_c6, rh_e6, rh_med; the new-age score gains
hand_bal 3-5, hand_bal_sd 1.5-4, rh_c6 0-0.06, rh_e6 0-0.015) and `songs/_blind/tells_newage.py --folders` (the
rendered balance per 4-bar phrase from report.json and the three moments where the left hand comes forward most).
The 10-piece set `endless new-age-piano --count 10 --seed 64000` (best-of-8), before (HEAD ccf5d6f) and after
(`songs/_endless_piano/out/balance_v1`; the selection picked another seed in 3 slots):

| measure (10 pieces) | before | after |
|---|---|---|
| RH - LH RMS, whole piece | 5.7 (4.3..7.5) | 3.8 (2.4..5.0) |
| RH - LH per 4-bar phrase, mean | 5.2 (4.1..6.7) | 4.1 (2.6..5.3) |
| ... its spread (sd) | 1.6 (1.2..2.1) | 2.4 (1.7..3.1) |
| phrases at 1 dB or less (the left hand level or leading) | 1 % | 12 % (7-29 % per piece) |
| rh_c6 / rh_med (rebuilt notes) | 0.036 (max 0.124) / 73.6 | 0.017 (max 0.047) / 73.3 |

Over 48 seeds (64000-64047, no audio): hand_bal 5.2 -> 4.2, hand_bal_sd 1.5 -> 1.9 (sd >= 2 in 4 -> 20 pieces);
rh_c6 0.043 -> 0.020, pieces over 6 % above C6 15 -> 6, over 10 % 6 -> 0; rh_e6 0.006 -> 0.001. The gates hold:
silent_notes 0, no flat lead, breath rejections 18 -> 14 over the set's candidates.

## After round g2: the set-level templates, and the right hand's flow (2026-10-15)

Round g2's judges compared the pieces and named templates shared by the set. In the same days the user said of the
balance set: "the right hand still plays excessively note by note - not very flowing", then "as if he had only one
finger" (recipes/HUMAN_FEEDBACK.md). Both were fixed in the owning tables (genres.NEW_AGE_PIANO; orchestra-film and
new-age-epiano inherit the plan).

| tell | fix | where |
|---|---|---|
| One form for every piece, the peak at 71-76 % in 10/10 | Six forms drawn per set slot, none within 3 slots: song, chorus (a rondo A B A C A), return (A B A'), arch (A B C B' A'), theme and variations (no chorus, the climax a variation of the theme over its own chords), late (the climax into a short coda) | `plan['set']['layout']`, `set_memory['layout']`, the sections' `layouts`, the new B2 and the A1-climax entries |
| 8 + 1 held-bar sections everywhere | `bars` draws irregular lengths: an extension (a span played again, its line varied and half its chords reharmonised: 10 / 12 bars), a 6-bar phrase, a 7-bar elision; the held 'tail' bar rarer | `_NA_BARS`, `perform._arrange` |
| Vsus4 -> V at every section end | A section ending on the dominant draws its close: kept, a full close, a deceptive close, a plagal half close, the backdoor bVII, an open ii7; the melody in that bar refitted | `_NA_CLOSE`, `perform._close`, ARRANGE_KEYS / the record's 'close' (token AClose) |
| The same final grip | The last chord's right hand per piece: the full grip, an open 5th / 6th, the note alone | play key `end_voice` |
| Progressions shared between pieces | The hook, open and build blocks and the intro's vamp remember the whole set (per mode); 6 more intro vamps | `set_memory`, `plan['set']['intro']`, `composer.frame(pin=)`, `set_draws` |
| The grown climax tiling the hook's head cell | The even statements extend the hook (its first bar, then a stepwise line on), the climb runs up by step to the peak (held a bar at most), the release is the whole hook upside down; the climb's place drawn | `perform._grow(at=)`, `plan['grow_at']` |
| The soft 16th broken chord under a held note in 8 of 10 | The bloom's right-hand texture per piece: the woven figure, repeated 8th dyads, or none; hand-offs outside the bloom half as often | `plan['bloom']['texture']`, `'handoff'` |
| "One finger": 91-96 % single-note onsets, neighbouring melody notes 5-7 velocity steps apart | The right hand's texture per section kind, drawn per piece: the theme mostly a single line, thirds / sixths in the returns, dyads and chords in the chorus, chords and octaves at the climax; an inner voice moving under held notes (not under a phrase's landing); connecting passing / neighbour notes (a phrase's last two notes kept); the melody one dynamic line per phrase (a smoothed arc, its range kept, small neighbour steps, accents kept) | `plan['texture']`, `perform._texture`, `romantic.harmonize(voices=3, move=, still=)`, `plan['line']`, `Score.perform(line=)`, `composer.flow_tells` (scored for new-age) |

Measured by `tells_newage.py` (48 seeds 64000-64047, no set plan; `--sets 6`: six sets of ten through
composer.set_plan, one candidate per slot):

| measure (mean) | before | after |
|---|---|---|
| forms in a set of ten; pieces with the peak at 70-78 % | 3; 8.8 | **6; 3.8** |
| the peak's place over 48 pieces (p10 / median / p90) | 0.71 / 0.75 / 0.78 | **0.54 / 0.73 / 0.87** |
| part sections 8 or 9 bars long | 0.88 | **0.66** |
| inner section ends on the dominant; on a sus4 | 0.72; 0.20 | **0.45**; 0.18 |
| 4-chord routes shared by two pieces of a set | 13.8 | **7.8** (3-chord: 51 -> 42) |
| pieces of a set with the woven 16ths | 5.5 of 10 | **2.7** |
| the final grip's right-hand notes (distinct per set) | 3.5 (2.8) | 2.0 (4.5) |
| the climax's longest top-line hold (beats) | 4.5 | 4.0 |
| melody onsets per beat | 0.84 | **0.99** |
| neighbour melody velocity step, median / p90 | 6.2 / 16.8 | **3.8 / 7.0** |
| right-hand onsets with 2+ notes (A1 / returns / chorus / climax) | 0.07 (0.01 / 0.08 / 0.01 / 0.27) | **0.44 (0.20 / 0.35 / 0.54 / 0.63)** |
| held melody notes with a moving inner voice | 0.21 | 0.22 |
| new-age score (no best-of-8) | 96.4 | 95.6 |

Costs: the phrase-end breath share fell (phrase_rests ~0.8 -> ~0.6 on 16 seeds; the connecting notes and the inner
voices lead some phrases on - the user's ask) and quiet1 0.29 -> 0.22 (the band's breath gate is now 0.2). Shared
3-chord routes stay frequent: they are the pop vocabulary (I - IV - V, the tag's ii - iv6 - I). The agogic part of
the feedback (a push into the phrase's peak) is the existing phrase rubato (`Score.rubato`), not changed.

## After round g3: the judges' fixes, and the first signature moves (2026-10-16)

Round g3 rated every piece. The generated set scored 5.58 against the references' 6.90 overall; the widest gaps were
melody (+1.40) and development (+1.10). The judges' ranked fixes went into the owning tables, and the first five
signature moves were added (docs/PIANO_MOVES.md section 11).

| g3 fix | change | where |
|---|---|---|
| The climax jumps to a remote key unprepared and never comes back | A key move is prepared over two bars both ways. Going in: a pivot chord in both keys (the new key's ii / vi / IV / iii), then its V7. Going home: the home IV / ii / iv / vi / bVI / bIII, then V7. Remote climax keys are rarer (home 0.78-0.8; III dropped) | `perform.PIVOTS`, `_pivot_chord`, `_keys`; `_NA_SECTIONS` climax `key` |
| A themes without a profile; B stronger than A | The theme's head gets one leap of a 4th to a 6th at move 1-2, stepping back after it. It mostly leaps down: a leap up lifted A over the chorus, and the arc check then rejected 41 % of the seeds. The head phrase's ceiling gets room for it | `melody['head']`, `composer.compose` (head leap, `u_hi`) |
| The melody absent at the peak; the hands level | The climax's late first onsets move to the downbeat. Its balance is at least `climax_min` 4 dB for the melody. Hand-offs at the peak are rarer | `perform._downbeats`, `BALANCE['climax'/'climax_min']`, `_NA_BLOOM['handoff']['peak']` |
| `variations` peaks at 49 %, `late` has no return | variations: a third variation (A3) before the climax, the post-climax A3 only in return / arch. late: a short A4 (4 or 6 bars) after the climax | `_NA_SECTIONS` |
| Copied 4-bar blocks (the `bars` extensions) | The extension's varied span is checked: a unit whose (onset, pitch) still match 75 %+ retries another vary kind | `perform._vary_changed` |
| Climax velocities hammered at v115-126 | The cap is drawn per piece at 96 / 102 / 108, with one accent at most `accent_over` 6 above it. The climax dynamics are drawn as an arc (mf ff mp, ...) | `plan['play']['cap']`, `plan['accent_over']`, the climax `dyn` |
| Phrase-end breaths ~0.58; inner motion .22 | phrase_rests treats a downbeat struck up to `LEAN` 0.1 beat early (the melody's lean) as on the beat: most of g3's "drop" was this measurement. Inner motion: `texture['move']` 0.85 / 1.0, and held notes of 1.5 beats+ voiced at `long` 0.9, an open 4th or a moving companion when no 3rd / 6th fits | `composer.phrase_rests`, `plan['texture']`, `romantic.harmonize(long_share=)` |

Measured by `tells_newage.py` (48 seeds 64000-64047; the new measures `g3_tells`):

| measure (mean) | before | after |
|---|---|---|
| climax: RH over LH dB (section / at the peak) | 3.4 / 4.5 | **5.1 / 6.8** |
| climax: top velocity; pieces with notes over 112 | 109; 15 of 48 | **104; 1** |
| climax bars with an RH onset on the downbeat | 0.75* | **0.99** |
| foreign-key climaxes with a pivot in / out | 0.45 / 0.45 | **1.0 / 0.88** |
| A head: largest interval / range (semitones) | 3.8 / 7.8 | **5.8 / 9.1** |
| copied 4-bar blocks in a section | 2 pieces | **0** |
| held notes with a moving inner voice | 0.22 | **0.32** |
| phrase_rests (with `LEAN`) | 0.64 (old metric) | **0.77** |
| peaks at 70-78 % (p10 / median / p90) | 18 (0.54 / 0.73 / 0.87) | 23 (0.59 / 0.74 / 0.80) |
| new-age score (no best-of-8) | 96.0 | 95.6 |

\* measured with the strict window, which counted notes struck early as the bar before.

The signature moves on the same 48 seeds (no set caps; per piece 2.25 moves): the motto in 18 (every statement
played: motto_hit 1.0, the plant exposed, the payoff at the climax), the ostinato in 26 (0.84 of its sections' bars),
the pause in 18 (held 1.8 s over its bar), the goosebump chord in 17 (always over its note), the cascade in 28 (a
38.6-semitone span, 9 hand changes). In sets of ten (`--sets 6`) no fingerprint repeats and no move is in more than
40 % of a set.

Costs: the score fell 0.4 (the motto adds hook statements and repeated notes; a pause bar counts as a peak hole).
The arc check rejects more seeds in a set slot, and the breath gate also rejects more: the inner voices fill quiet1
(0.24 -> 0.22). A slot sometimes keeps only 1-4 of its 16 candidates. Open: TODO.md.

## After round g4: the theme at the climax (2026-10-16)

Round g4 scored the generated set 5.30 against the references' 7.10. All five judges ranked the same fix first: 7 of
8 climaxes had no theme. The measurement showed why: 47 of 48 climaxes were 'grow', because the old 'theme' (the A1
an octave up) never fit under the ceiling peak and fell back to 'grow'.

| g4 fix | change | where |
|---|---|---|
| The climax has no theme | The default climax kind is now 'theme' (`_anthem`). Over A1's own chords it states the theme's units, then its head again a 3rd / 5th / octave higher at the peak (the highest lift that fits under the ceiling), then falls back a step per unit and lands on the theme's own last unit. How it is stated is a set draw per slot: octaves, chords (the right hand's texture), augmented, sequenced up a third per statement, or reharmonised (every chord the line allows). Its long notes keep still (no moving inner voice), so the climax keeps its breath | `perform._anthem`, `ANTHEMS`, `_arrange`, `_texture`; `plan['set']['climax'/'anthem']` |
| The cascade read as "mechanical, texture not music" | A link now, not the climax's content: the climax's last bar (the bar before when the pause takes it), under the held melody note, over 2.5 octaves; chance 0.45 -> 0.25, one bar only | `perform._sign` (cascade), `_cascade_notes`; `plan['signature']['cascade']` |
| A restated near-verbatim | A return (A2 / A3 / A4) keeps its head unit and rewrites its second half: a sequence and an inversion alternate unit by unit, starting on the other one in each return, the step growing in the later returns; the cadence's last note stays | `perform.RETURNS`, `_vary_draw`, `_vary(land=, size=)`, `_vary_changed(only=)` |
| Climax key moves sudden | The dominant lead-in also for a mode change (A minor -> A major), and the pivot chord whenever the section before has 2 bars (was 3) | `perform._keys` |
| B1 / the build louder than the climax | Every mark outside the climax at least a level under its loudest, B1's first two bars mf at most; a section whose note energy still beats the climax's is played softer (touch, x0.8 at most). The build rises to mf, the 4-bar cell no longer repeats (`bars` (0,8)+(6,8)) | `perform._dyn_order`, `_loud_order`, `LOUD_ORDER`; `_NA_SECTIONS` build / climax `dyn`, `bars` |
| The IV - iv6 split in the penultimate bar of 4 pieces | The coda's approach is a set draw (sus / IV / ii / vi, the minor plagal once a set at most) | `plan['set']['tag']`, `composer.frame(tag_pin=)` |
| The motto a set template ("D-C-C" in three pieces), octave-down recurrences in the left hand | The cell starts on the head's first note, the key's 3rd, 5th or tonic, in a register band (low / mid / high) the set's mottos never share; a cell under E4 is lifted an octave, an octave-down recurrence under E4 becomes a sequence | `composer.MOTTO_BANDS`, `motto_anchor`, `signature_prints`; `plan['signature']['motto']` `anchor` / `register` |

Measured by `tells_newage.py` (48 seeds 64000-64047; the new measures `g4_tells`):

| measure (mean) | before | after |
|---|---|---|
| the climax states the theme (head match near the peak) | 3 of 48 | **36 of 48** |
| climax melody vs the written theme / hook | 0.62 / 0.63 | **0.85 / 0.85** |
| cascades; in the climax's last bar / under a held note | 28; 2 / 0 | **15; 14 / 12** |
| a return's second half vs earlier A (mean / max) | 0.31 / 1.0 | **0.21 / 0.56** |
| climax key moves with a dominant in / back home | 0.88 / 0.63 | **1.0 / 1.0** |
| climax over the loudest other section (dB; pieces > 0) | 0.70; 26 | **1.14; 45** |
| B1 entering louder than the climax | 7 pieces | **2** |
| a 4-bar build cell looped twice | 5 pieces | **0** |
| mottos with notes under E4 | 8 of 18 | **4 of 23** |
| sets of ten: shared penultimate bar / IV-iv6 / same motto cell | 1.67 / 2.33 / 0.5 | **1.5 / 2.0 / 0.17** |
| phrase_rests | 0.77 | **0.85** |
| new-age score (no best-of-8) | 95.6 | 95.0 |

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000): arc 35.9 % -> 37.1 %, breath 14.8 % -> 11.3 %,
kept 49.2 % -> 51.6 %. Costs: off_scale rose (0.15 -> 0.69 a piece; the motto's chromatic neighbour notes), the
score fell 0.6. The orchestra keeps its own climax draw (no `_anthem`: its tutti and its higher ceiling).

## After round g5: the climax an octave up, the theme over the left hand (2026-10-16)

Round g5 scored the generated set 5.40 against the references' 7.10. Every judge's first fix: the climax states the
theme now (36 of 48), but in A1's own register (B4-D5), and the A theme itself sits in E4-C5 inside the left hand's
arpeggios. Measured on 48 seeds before the fix: the A melody's median C5 (its 10th percentile Ab4), the climax's
median C#5, only 1.6 semitones over A1. The references (embers, tide, letters, hopeful, waltz) sing their A sections
at D5-G5 and their climax at C6-D6 (top 92-93).

The user's earlier "too many very high notes" (recipes/HUMAN_FEEDBACK.md) was about high notes everywhere: a theme
an octave up as every return, a C7 top. The reconciliation: the C6 band belongs to the climax. Outside it, notes at C6+
stay rare (`rh_c6` now counts the notes outside the climax).

| g5 fix | change | where |
|---|---|---|
| The climax sings the theme in A1's register | The whole sung climax is an octave over A1: the statements, the head at the peak, the falling continuation and the landing. This applies where the theme's head fits under the new ceiling 'sung' (A6, the references' top). The peak is a step or two over the octave theme's top. A repeat of the top within a bar of the peak steps under it, so there is one peak | `perform._anthem(octave=)`, `_arrange`; `plan['ceiling']['sung']` 93 |
| The A theme inside the left hand | The melody's register is a whole step up (A4-C6, centre F5, peak D6). The set's register shift loses -3 (the floor stays at G4) and +3 (no room for the octave climax) | `NEW_AGE_PIANO.melody`, `plan['set']['shift']` |
| B1 / the coda as loud as the climax in single phrases (v108 / v115) | Every other section's loudest note, per hand, is at least `peak_under` 6 velocity steps under that hand's loudest in the climax. The notes within `knee` 14 of that cap are pressed into it, so the phrase keeps its shape | `perform.LOUD_ORDER`, `_loud_order` |
| 'variations' without a contrast | The chorus (B1) is its second section: A1 B1 A3 (the variation) climax A4 | `_NA_SECTIONS` layouts (A2 out of 'variations', B1 in) |
| The waltz at 129 bars, a 20-bar build vamping Asus4 \| A | A waltz (its form bars doubled) plays no extension span. Its optional body section (the third A) comes half as often | `perform._arrange` (bars), `_piano_plan` (chance) |
| The 'lift' climax left the key with the chorus and no theme (BGME) | In a genre with the sung theme, 'lift' is the sung theme | `perform._arrange` |
| A key move into a section that opens on the new key's vi (F#7 -> G#m7) read as unprepared | The lead-in is the dominant of the section's first chord (D#7 -> G#m7), after the pivot; `tells_newage.py` key_dom accepts it | `perform._keys` |
| A busy left hand under the climax's theme (GNRR 12.2 attacks a bar) | The climax's hand is mostly 'broad' (`o - c - 3 - c -`: the bass octave, the chord, its 10th, the chord), with 'big' less often and the 16th sweep rare. The bloom lands in the climax less often (0.3 -> 0.1). The right hand there plays octaves / chords (the anthem texture) | `pianist.FIGURES['broad']`, `_NA_FIGURES['big']`, the climax `figures`, `_NA_BLOOM['at']` |
| The cadenza's run from above a section's top (a C7 flourish over the A6 peak) | The run starts under the piece's peak | `perform._play_piano` (cadenza) |
| A waltz running through its phrase ends (one at 0.36) | phrase_rests is a gate minimum now (0.45, the tests' floor) | `band['breath']['phrase_rests']`, `run.breath_gate` |

The orchestra keeps its old register and shift draw (its violins sing higher; one seed hit a fermata overlap with
the raised register, see TODO.md).

Measured by `tells_newage.py` (48 seeds 64000-64047; the new measures `g5_tells`; the melody is the right hand's
top line):

| measure (mean) | before | after |
|---|---|---|
| A sections' melody: median / 10th percentile | 72.1 (C5) / 67.9 | **73.7 / 69.4** |
| ... its 10th percentile over the left hand's 90th (semitones) | 6.8 | **8.1** |
| B / build / climax melody median | 75.0 / 73.3 / 73.6 | 76.4 / 75.3 / **84.5 (C6)** |
| climax over A1 (semitones); its 10th percentile | 1.6; 67.0 | **11.0; 75.3** |
| climax melody at C6+; right-hand notes at C6+ outside the climax | 0.05; 0.003 | **0.61**; 0.013 |
| the theme at the climax (head match; at the peak) | 0.85; 36 of 48 | 0.86; 37 of 48 |
| part sections within 4 velocity steps of the climax's loudest; B1's loudest - the climax's | 0.48 (15 pieces); max +7 | **0; max -6** |
| climax over the loudest other section (dB) | 1.14 | 1.49 |
| bars (waltzes); the build's longest | 116 (max 132); 20 | **104 (max 112); 16** |
| 'variations' with a contrasting section | 0 of 9 | **9 of 9** |
| climax: left-hand attacks a bar; right-hand onsets with 2+ notes | 10.0; 0.50 | **8.0; 0.78** |
| off_scale (a piece) | 0.69 | 0.71 |
| phrase_rests; quiet1 (100 seeds 64100-64199) | 0.85; 0.243 | 0.79; 0.230 |
| new-age score (no best-of-8) | 95.0 | 95.2 |

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000): arc 37.1 % -> 41.4 %, breath 11.3 % -> 12.9 %.
Without set plans (300 seeds) the arc rate is unchanged (41.0 % -> 40.3 %). The slot difference comes from the new
shift draw. Costs:
- The breath. phrase_rests fell 0.06 and quiet1 0.013. The higher register gives the inner voices and the connecting
  notes more room above the left hand. The bloom now lands in the build / B1 more often.
- The C6+ share outside the climax rose (the chorus's and the build's tops). It is still a rare event (1.3 %).
- off_scale did not creep. Its 0.7 a piece is the motto's chromatic lower neighbour (G# under A over Dm in D minor,
  4 notes a statement, the same cell every time: an expressive leading tone, not a wrong note). The rest are a vi
  chord read as Dorian by `_local_scale` (Bb over Dm7 in F major is diatonic).

## After round g6: the theme recognisable at every climax, the register band, the waltz's length (2026-10-16)

Round g6 scored the generated set 5.95 against the references' 6.40, but the same two references were rated 0.7
lower than in g5. The judges' fixes went into the owning tables. Four of them were set draws a single seed rarely
plays ('step', 'sequence', 'reharm', the waltz), so they were measured twice: 48 seeds 64000-64047 as before, and
48 set slots (`tells_newage.py --slots 6 --set-n 8`, seeds from 72000, one candidate per slot: the draws as a round
plays them). The new measures are `g7_tells`.

| g6 fix | change | where |
|---|---|---|
| The 'step' climax a new tune (GVPE); a reharmonised theme in a new key heard as "an arpeggio" (QNFS) | 'step' in a sung genre is the sung theme moved a whole step up by the key plan (`_keys`: the pivot and the dominant in, the home dominant out). A reharmonised anthem keeps the head's own chords where it is first stated and at the peak unit | `perform._arrange` (`step_key`, the reharm `keep` units) |
| The 'sequence' climax looping its head cell 8-12 times (FUKP) | The head twice, the second a third higher (from a third under the statements' level), then the theme goes on, then the head at the peak: the cell no longer climbs "only while it fits" | `perform._anthem` ('sequence') |
| The climax 55 % at C6+ for nine bars (SGVL; the user's "too many very high notes") | The statements sing over A1 in the 5th octave: a fifth / third up where at most 15 % of their notes reach C6, else as written; the unit before the peak a third higher; the octave only at the peak unit; the continuation falls from a third over the statements | `perform.ANTHEM_BAND`, `_anthem` |
| The waltz at 99 bars (FUKP; 104 on average) | An optional section by x0.3 (but the intro); no A2 right after A1 (its 8 form bars are a 16-bar period); the chorus, the returns and the build a 6- or 7-bar form phrase | `perform.WALTZ_FORM`, `_piano_plan` |
| Themes with holes: a pickup, then half-empty bars (XEDV); a neighbour-figure head (WHKZ) | A soft writing rule: an A part's bars (but its landings) sound half the bar, the theme's first 4 notes are no neighbour figure inside a whole step. 'across' (three empty beats) out of the theme's set draw | `composer._style_issues(holes=, head=)`, `melody['holes']`, `plan['set']['opening']`, `melody['openings']` |
| A3 after the climax literal (WHKZ, QNFS, GVPE) | The theme's first return after the climax re-rhythms its head unit (its pitches kept), every unit checked as changed, at least 70 % of its chords swapped | `perform.POST_RETURN`, `_arrange` (`_post`) |
| The build's left hand 12-13 attacks a bar (GVPE, QNFS) | The bloom's first stage 8ths (flow / rock), its second triplets with 8ths / 16ths between; the chorus blooms 0.35 -> 0.2 | `_NA_BLOOM['figures']`, `['at']` |
| A flat v98 climax (XUMB); the waltz's B1 at climax level (FUKP); a loud intro (TLTG v88) | The climax swells into its peak: the notes before the peak's bar from x0.84 up to x1. Every other part section's mean melody velocity 8 under the climax's. The intro's loudest note 6 under A1's and at most v72 | `perform.LOUD_ORDER` ('swell_from', 'mean_under', 'intro_under', 'intro_top'), `_loud_order(shape=)` |

The new loudness rules, the post-climax return and the 'step' rewrite apply to a genre with the sung climax only
(`perform._sung`: new-age). The orchestra inherits the theme's writing rules (`melody['holes']`, the opening draw):
its baseline seed 102 scores 93.5 -> 94.3.

Measured by `tells_newage.py` (before -> after; 48 seeds / 48 set slots):

| measure (mean) | 48 seeds | 48 set slots |
|---|---|---|
| climax melody at C6+ (share); its longest run of C6+ bars | 0.61 -> **0.27**; 4.5 -> **1.8** (max 9 -> 4) | 0.54 -> **0.27**; 4.2 -> **1.6** (max 16 -> 4) |
| climax melody median; over A1's | 84.5 -> 79.1 (G5); 11.0 -> 5.5 | 83.5 -> 79.8; 9.3 -> 5.5 |
| the theme at the climax (head match); at the peak | 0.86 -> 0.83; 0.77 -> 0.71 | 0.82 -> 0.82; 0.69 -> 0.69 |
| ... 'step' / 'sequence' climaxes | - / 0.82 -> 0.82 | **0.43 -> 0.64** / **0.79 -> 0.93** |
| the most repeated 3-note cell in the climax | 2.0 -> 1.75 | 2.0 -> 1.7 (max 5 -> 3) |
| the climax's swell (peak bars' mean velocity over its first 2 bars'); bars within 6 of its loudest | 11.3 -> **22.7**; 0.58 -> 0.41 | 13.2 -> **24.2**; 0.59 -> 0.46 |
| A1 bars sounding under half the bar; neighbour heads | 0.04 -> 0; 0 | 0.17 -> 0.06; 1 -> 0 |
| the first return after the climax note for note (bars, pitches + chord) | 0.30 -> **0.10** | 0.31 -> **0.05** |
| left-hand attacks a bar: build / chorus (max) | 9.8 (13.1) -> **8.4 (11.0)**; 7.7 (13.0) -> 6.6 (10.7) | 10.0 (13.6) -> **8.6 (11.0)**; 7.6 (13.0) -> 6.5 (10.5) |
| the intro's loudest velocity (max) | 64 (83) -> 61 (**72**) | 60 (89) -> 60 (**72**) |
| B1's mean melody velocity minus the climax's (max) | -11.1 (-1.5) -> -11.1 (**-7.9**) | -11.4 (+1.6) -> -11.3 (**-7.9**) |
| waltz bars | 106, 96, 98, 108, 102, 108, 112, 106 -> **90, 88, 80, 98, 88, 80, 86, 92** | 104.7 -> **89.7** |
| key moves with a dominant in / home | 1.0 / 1.0 | 0.78 / 0.89 -> **1.0 / 1.0** |
| phrase_rests; off_scale | 0.79 -> 0.79; 0.71 -> 0.67 | 0.78 -> 0.78; 0.40 -> 0.38 |
| new-age score (no best-of-8) | 95.2 -> 95.3 | 95.3 -> 95.6 |

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000): arc 44.1 % -> 43.4 %, breath 11.7 % -> 11.3 %,
kept 44.1 % -> 45.3 %. Costs:
- The head match at the peak fell on the 48 single seeds (0.77 -> 0.71): the statements a third over A1 and the
  key moves' refit bend some head intervals by more than a semitone. On the set slots it held (0.69).
- Short climaxes (8 bars, 4 units) still reach 0.4-0.55 at C6+: the peak unit is a quarter of them, and a motto's
  payoff an octave up adds to it. 11 of 48 slots are over 0.35; none has more than 4 C6+ bars in a row.
- `dyn_range` (2-bar windows, 10-95 %) 8.85 -> 8.5 dB over 48 seeds: the climax enters softer. The test floor is
  4.5 dB now (one test seed at 5.0).
- The bloom's left hand is 1.3x the plain hand's attacks, not 1.4x.

## After round g7: a theme with a profile, the climax at two thirds, the melody over the left hand (2026-10-16)

Round g7's judges remembered the references' themes and not ours: "a stepwise band circled", "the climax half-speed",
"a filler run out of the peak", "the build's left hand as loud as the tune". The fixes went into the owning tables and
were measured as in g7 (`tells_newage.py`, new measures `g8_tells`; 48 seeds 64000-64047 / 48 set slots from 72000).

| g7 fix | change | where |
|---|---|---|
| A themes without a profile: a stepwise 2-3 note band (the main fix) | The A head (its first 2 bars) needs a leap of a 4th+ after the first note, its top note held (>= 1 beat in 4/4, 1.5 in 3/4) and no 3-semitone window holding over 67 % of its notes. The head is planned with that profile (the drawn cell first, then up to 24 redraws), the A1 attempts cycle through the good heads, the head unit fitted with a 3x contour weight; a realised head without it is a soft issue, and `head_prof` a score term | `composer.HEAD_PROFILE`, `head_profile`, `_planned_profile`, `melody['profile']`, `_Ctx.contour`, `_SCORE_NEWAGE['head_prof']` |
| The climax 'augment' (half-speed) and the cascade out of it | 'augment' out of the anthem draw (set memory 4 -> 3); the cascade's chance 0 (the signature fallback skips chance-0 moves); the connecting notes keep the head's top note | `genres` ('anthem', 'cascade'), `composer.signature_draw`, `perform._embellish(keep=)` |
| The arch's climax at 50-58 % of the piece, a long louder tail | The post-climax 'inter' plays 'return' only, the arch's B2 4 bars; every part section after the climax at least 2 dB under the loudest one before it | `genres` (layouts), `perform.LOUD_ORDER['tail_under']`, `_loud_order` |
| Copied A bars before the climax | The returns before the climax are varied over every unit (`_pre`: the head re-ornamented, the rest rewritten, a bar copy at 75 % sameness rejected) with the post-return's reharm share | `perform._vary_changed(head=)`, `_arrange`, `_piano_plan` (`_pre`) |
| Returns sinking out of the singing register | A rewritten unit whose mean pitch sinks over 3 semitones under the source is rejected | `perform.RETURN_SINK` |
| The left hand as loud as the melody in B1 and the build | The hands' balance: B +0.5 (was -0.5), build -0.5 (-1.5), bloom -1.0 (-3.0), the jitter 2.0 dB (1.5) | `perform.BALANCE` |
| Right-hand holes, the repeated-chord comping | A sung piece's 'fill' section fills empty bars but its phrase ends; the pulse texture alternates two dyads | `perform._fill(ends=)`, `_handoffs` |

Measured (before -> after; mean (max)):

| measure | 48 seeds | 48 set slots |
|---|---|---|
| head with a profile (planned / played after the performer) | **0.21 -> 0.94** / 0.23 -> 0.50 | **0.48 -> 1.00** / 0.29 -> 0.69 |
| head leap (semitones); top note held (beats); band share | 5.4 -> 5.9; 1.05 -> 1.68; 0.65 -> 0.58 | 5.8 -> 6.1; 1.35 -> 1.72; 0.62 -> 0.56 |
| climax augmented; cascade | 0.10 -> **0**; 0.33 -> **0** | 0.17 -> **0**; 0.29 -> **0** |
| climax peak position: arch (min); all | 0.58 (0.50) -> **0.68 (0.66)**; 0.70 -> 0.72 | 0.59 (0.55) -> 0.65 (0.63); 0.70 -> 0.72 |
| share after the climax; its loudest section over the pre-climax one (dB, max) | 0.225 -> 0.214; +0.46 -> **-0.9** | 0.227 -> 0.213; -0.05 -> -0.39 |
| A statements before the climax (max); copied A bars there (max) | 3 -> 3; 0.16 (0.58) -> 0.12 (0.42) | 3 -> 3; 0.20 (0.57) -> **0.105 (0.33)** |
| returns under A1's register (share; worst drop) | 0.27 -> 0.23; +2 -> +4 | 0.29 -> 0.23; +6 -> +4 |
| melody over left hand in B1 / the build (dB) | 3.8 -> **5.1** / 2.95 -> **4.6** | 4.0 -> **5.3** / 2.8 -> **4.5** |
| hand_bal (sd across sections) | 4.66 (1.78) -> 5.28 (1.55) | 4.66 (1.77) -> 5.38 (1.53) |
| RH holes (no onset, nothing held over half the bar); repeated-chord bars | 0.02 -> 0.02; 0.23 -> 0.19 | 0.02 -> 0; 0.125 -> 0.17 |
| the theme at the climax's peak | 0.71 -> 0.75 | 0.69 -> **0.875** |
| phrase_rests; score (no best-of-8) | 0.794 -> 0.79; 95.3 -> 95.6 | 0.78 -> 0.76; 95.6 -> 95.0 |

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000): arc 46.9 % -> 37.1 %, breath 10.5 % -> 12.9 %,
kept 42.6 % -> 50.0 %. Costs:
- The played head keeps its profile in half the single seeds only: the performer's connecting notes and the
  rhythm's anticipations break the held top note. The composer side is at 0.94 / 1.0.
- Copies after the climax rose (0.10 -> 0.115 / 0.05 -> 0.13): sequence coincidences and the motto's statements.
- hand_bal sits over the table's 3-5 dB now (5.3): the score's range was left, so it costs ~0.3 points a piece.
- The baseline moved: new-age 101 95.0 -> 90.1 (the waltz's phrase_rests 0.38 with its new head), 102 94.1 -> 95.0,
  103 96.7 -> 95.6, the candidates [] -> three over 94; classical / lofi metrics through the shared BALANCE; the
  orchestra keeps the head gate off (`profile=0`), its 103 98.3 -> 98.2.

## After round g8: the head kept as played, the climax's arrival per piece, B with a destination (2026-10-16)

Round g8 put the generated set at 5.88 against the references' 6.27 and level on memorability (2.27 vs 2.27). All
five judges still named 8 of the 10 pieces correctly. The fixes went into the owning tables and were measured with
`tells_newage.py`: the new measures are in `g9_tells`, and the runs covered 48 seeds 64000-64047 and 48 set slots
from 72000. The "before" runs used the g8 code with the new measures.

| g8 fix | change | where |
|---|---|---|
| The played head lost its profile (0.50): the performer cut the held top note | Root cause: `articulate` took an inner voice under a held top note for the next melody note, so it cut the top note to about a beat (a leap articulation). Such a voice is no melody note now. An A statement's head (its first 2 bars) also keeps its notes as written: no connecting notes, no turns | `romantic.articulate` (tops), `perform._texture` (`top_`), the ornaments' `h0` |
| The climax after a key change heard as a new tune (NSFY, JKGC, EUNP) | The anthem's statements are not refit after their key move (`_modulate(refit=False)`), so the head keeps its intervals. The motto's 'augment' payoff only applies to a cell that fits the bar | `perform._modulate`, `_arrange`, the motto payoff (`aug`) |
| A busy 16th left hand under the theme; A only +1.7..+3 dB | The signature ostinato plays its thin form in A when its grid is faster than 8ths (4/4) or 6 a bar (3/4). An A statement of a sung genre sits at least 4 dB over its left hand. Its lead phrases sit at +2.5, drawn 1-3 (rarely none). The score table's hand_bal widened 3-5 -> 3-6 (the judges ask for +4-5, and the references measure 4.7-6.8) | `perform.OST_UNDER`, `BALANCE` ('a_min', 'a_lead'), genres play('lh_lead'), `_SCORE_NEWAGE['hand_bal']` |
| Returns repeating the head note for note; four bars on one chord | A sung genre's returns are rewritten over every unit ('keep' / 'orn' become 'rhythm'), the head included. In a run of 3+ bars on one root, every second bar but the last moves to the chord a fifth up, and the melody there is refit | `perform._arrange` (`sung_ret`), `STALL`, `_destall` |
| Stock B loops (Am-F-C-G) | The hook blocks get a destination: a secondary dominant (II7, III7, I7), a borrowed chord (bVI, bVII, iv) or a half cadence (Vsus4-V). B is 8 bars, or 8 + a 2-bar extension (the 4-bar loop extension is out) | `genres.NEW_AGE_HARMONY` (hook), `_NA_BARS['B']` |
| The arch's tail too short; short climaxes with no build | The arch's last A has its own entry: 8 bars, or 8 + 2 (it was 6). A variations climax over a theme of 8 bars or fewer grows to 12 bars (4/4) | `_NA_BARS` ('arch'), `perform.ANTHEM_GROW` |
| A lone high note over a silent left hand (DMZT 52); two-octave jumps in climax runs | The pause's 'high_note' is the climax's lead-in only. The weave and the pulse skip chords wider than a 6th. The packets print an inner voice under a held top note as "(under)", and an early-struck downbeat in its own bar (g8's "holes" in JKGC, PKCG and LXAN were such downbeats) | `composer.signature_draw`, `perform._handoffs`, `make_packets_newage.py` |
| One climax template across the set | A set draw: the climax's ARRIVAL. 'direct'; 'pause' (the suspended pause at the climax seam); 'key' (the climax in another key); 'dominant' (the section before ends V7sus4 \| V7 with a fermata); 'fragment' (the head's first bar, then the same bar a step higher, then the whole theme). A slot never repeats an arrival from the three slots before it (set memory 3). Any arrival other than 'pause' moves a climax-seam pause to the return. Any arrival other than 'key' keeps the climax home | `plan['set']['arrival']`, `composer.set_draws` (`LATE_DRAWS`, `arrival_pause`), `perform.ARRIVALS`, `_arrive`, `_anthem(arrive=)` |

Measured (before -> after; mean (max)):

| measure | 48 seeds | 48 set slots |
|---|---|---|
| played head with a profile | **0.50 -> 0.92** | **0.69 -> 0.875** |
| the theme at the climax; at its peak; in another key | 0.84 -> 0.845; 0.75 -> 0.79; 0.75 -> **0.93** (n 7 -> 4) | 0.84 -> 0.83; 0.875 -> 0.77; 0.73 -> 0.71 |
| climax opening on held notes | 0 -> 0 | 0 -> 0 |
| A left-hand attacks a bar (max); A bars with a busy 16th left hand | 6.9 (11.7) -> **5.8 (8.6)**; 0.17 -> **0** | 7.0 (14.4) -> **5.9 (8.1)**; 0.18 -> **0** |
| melody over the left hand in A: mean; the piece's weakest A section | 5.26 -> 5.31; **3.86 -> 4.20** (pieces under 3 dB: 12 -> 3) | 5.39 -> 5.27; 4.10 -> 4.10 |
| hand_bal (sd) | 5.28 (1.55) -> 5.21 (1.50) | 5.38 (1.53) -> 5.20 (1.50) |
| returns repeating the head note for note | **0.114 -> 0.010** | **0.080 -> 0.017** |
| the longest run on one chord (max) | 1.46 (3) -> 1.33 (**2**) | 1.63 (3) -> 1.38 (**2**) |
| B with a destination (secondary dominant / borrowed / cadence away); B loops | **0.33 -> 0.79**; 0 -> 0 | **0.52 -> 0.94**; 0.04 -> **0** |
| the arch's tail (bars); all tails | **13.1 -> 16.6**; 11.3 -> 11.8 | 14.4 -> 15.8; 11.1 -> 11.6 |
| climax bars (max); climaxes with no build before them | 8.4 (9) -> 8.9 (13); 0.125 -> 0.06 | 8.4 (9) -> 8.6 (13); 0.15 -> **0.02** |
| two-octave jumps in a climax beat | 0.125 -> 0.06 | 0.125 -> 0.08 |
| distinct climax arrivals per 8-piece set | 1 -> **5** (6 sets, every set all five) | |
| phrase_rests; score (no best-of-8) | 0.79 -> 0.78; 95.6 -> 95.5 | 0.76 -> 0.80; 95.1 -> 95.6 |

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000): arc 35.2 % -> 34.0 %, breath 16.8 % -> 12.9 %,
kept 48.0 % -> 53.1 %. Costs:
- RH holes inside the build or the climax: 0.02 -> 0.04 (2 of 48 pieces, one bar each). B1's balance fell 5.1 -> 4.8,
  because the lead phrases move to A.
- The theme at the climax's peak fell on the set slots (0.875 -> 0.77). The 'fragment' arrival states the head's
  first bar twice, and the motto's payoff replaces the first unit: both are by design.
- The baseline moved: new-age 101 90.1 -> 89.6, 102 95.0 -> 94.4, 103 95.6 -> 94.3 (the A balance and the B blocks).
  The candidates are now 301 96.0, 304 95.8, 303 94.5 (they were 302 97.6, 301 95.3, 303 94.4). The orchestra shares
  the pause draw, so seed 302 now fails the arc check and 303 / 304 score 90.5 / 95.9 (they were 88.0 / 93.9).
  Classical, lofi, jazz and organ are unchanged.

## After round g9: the climax from the head, its dynamics, the way out (2026-10-16)

Round g9 put the generated set at 6.05, the highest yet, against the references' 6.60. Against embers + tide the gap
was +0.15, and the generated pieces led on memorability (2.42 vs 2.40). The judges' top complaints were:
- the climax not built from the head (KVRY, NMPC);
- the dynamics around it;
- a heavy B1 left hand;
- the way out of the climax.
The tells first had to hear the first complaint. `tells_newage.py`'s `g10_tells` now follow the head's contour and
rhythm through the sung line (`contour_match`), not its pitch classes. The runs covered 48 seeds (64000-64047) and 48
set slots (72000-72047). The "before" runs used the g9 code with the new measures.

| g9 fix | change | where |
|---|---|---|
| The climax not heard as the head | `contour_match` follows the head's first note and its onsets: the same direction each step (a repeat stays a repeat), within a semitone, connecting notes up to a beat skipped. 'grow' / 'climb' / 'lift' become 'theme' in a sung genre, and the set's climax draw drops grow / climb. The climax's downbeats are added late (from the bar's middle), so the head's first beats stay its own | `_arrange`, `_downbeats(late=)`, `genres` set 'climax' |
| The climax entered under the build; loud returns after a soft B2; 4 bars hammering the peak | A pause at the climax seam goes into a forte climax, and a pause after the climax comes out soft. The climax's first 2 bars sit at least 0.5 dB over the last 2 sounding bars, fading over 4 bars. After the climax, each section is held to the last 2 bars of the section before, +8 velocity. Near repeats of the peak note are lowered a step. The arch has one accented peak: the notes before it at 0.95, +6 on the peak, a taper to 0.85 after | `_sign` (the pause's `after`), `LOUD_ORDER` ('enter', 'reentry', 'around', 'accent', 'taper_to'), `_loud_g10`, `_anthem` (near) |
| A heavy left hand in B1 / the climax bass | In every part section but A, the left hand is pressed per bar (a soft knee) to the right hand's loudest -6. Every section before the build sits at least 1 dB under the build | `LOUD_ORDER` ('lh_under', 'build_over'), `_press` |
| The drop out of the climax; an empty last RH bar; the waltz's sag | The peak is never in the anthem's last unit (`ANTHEM_OUT['units']`). The units after it fall from two steps under the peak to the theme's level, over the remaining span, refit to the key. The tail chords link down by chord tones under the previous note, held | `ANTHEM_OUT`, `_anthem` (`down`) |
| Climax chords of 10-12 RH notes a bar | At most 8 RH notes a bar in 4/4, 6 in 3/4. The companions of the shortest melody notes are dropped first. The octaves texture plays 3 voices, chords 2 | `CLIMAX_NOTES`, `_thin`, `_texture` |
| The return after the climax without the head | The first return after a sung climax keeps unit 0's top notes and ornaments them (`head=True`). Its other units are reharmonised at 0.7. The motto is not spliced over it | `POST_RETURN`, `_vary(head=)`, `_embellish(keep)`, `_sign` (`post`) |
| Heads with no repeated cell | `melody['half_cell']` 0.7: bar 2 restates bar 1's rhythm. The A variant that develops first is weighted 0.8, the line variant 0.2 (the latter was 0.6). This is shared with new-age-epiano and orchestra-film | `genres` melody, A `phrase_variants` |
| One climax payoff across the set | A new anthem: 'canon'. The theme echoes an octave under, a bar later, before the peak unit, as an inner voice at 0.72 x touch, never over the line | `ANTHEMS`, `CANON`, `_canon` |

Measured (before -> after; mean):

| measure | 48 seeds | 48 set slots |
|---|---|---|
| the climax follows the head's contour (`clx_head`); pieces at >= 0.8 | **0.62 -> 0.83**; 0.44 -> 0.67 | **0.68 -> 0.85**; 0.56 -> 0.73 |
| the head at the climax's peak; the climax a theme kind | 0.50 -> 0.60; 0.79 -> **1.0** | 0.56 -> 0.74; 0.73 -> **1.0** |
| the climax entry over the build (dB); pieces under it | **-0.21 -> +1.11**; 25 -> 7 | +0.39 -> +1.25; 19 -> 5 |
| the velocity jump into the first section after the climax; pieces over 10 | 2.75 -> 0.24; 11 -> 5 | 1.21 -> 0.84; 11 -> 3 |
| bars hammering the peak; pieces with 4+ | 3.6 -> 1.7; **23 -> 1** | 3.7 -> 1.4; **24 -> 2** |
| B1 left hand v90; climax LH velocity max | 54.9 -> 49.0; 73 -> 69 | 57.2 -> 49.0; 72 -> 65 |
| B1 over the build (dB) | -0.32 -> **-1.13** | -0.27 -> **-1.05** |
| the largest one-bar drop in the climax (semitones); pieces over 12 | 10.2 -> 7.3; 9 -> 2 | 10.1 -> 7.4; 15 -> 2 |
| climax RH notes a bar; pieces over 8 | 8.0 -> 6.5; 24 -> 5 | 8.1 -> 6.5; 26 -> 3 |
| bars after the peak in the climax (max) | 3.4 (9) -> 2.9 (5) | 3.0 (7) -> 3.0 (5) |
| the first return after the climax states the head | **0.04 -> 0.54** | **0 -> 0.58** |
| heads with a repeated cell | 0.75 -> 0.85 | 0.58 -> 0.79 |
| phrase_rests; score (no best-of-8) | 0.78 -> 0.82; 95.7 -> 95.3 | 0.80 -> 0.82; 95.8 -> 95.3 |

The g9 judged pieces, rebuilt from their seeds, follow the head at the climax in all 8 (KVRY was 0.2, NMPC 0.14,
LMUP 0). Seven of them state the head in the first return after the climax.

The remaining `clx_head` misses (under 0.8 in 16 of 48 seeds) are mostly a motto payoff that replaces the climax's
first unit (by design), canon echoes, and octaves with a reharmonised head.

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000): arc 33.2 % -> 36.7 %, breath 19.1 % -> 14.1 %,
kept 47.7 % -> 49.2 %.

Costs:
- RH holes at the climax end 0.10 -> 0.15 (seeds).
- Climax vmax 104 -> 107 (the peak accent).
- Two-octave jumps in the climax 0.06 -> 0.33 on seeds (the canon echo against the line).
- Returns repeating the head 0.01 -> 0.06 (seeds) and 0.02 -> 0.15 (slots). The post-climax return keeps its head on
  new chords, which is intended.
- C6+ share at the climax 0.27 -> 0.37.
- Score 95.7 -> 95.3: dyn_range 8.6 -> 7.8 (the B1 / LH press), the phrase velocity spread, and a higher hook count
  (half_cell).

The baseline moved:
- new-age 101 89.6 -> 94.7, 102 94.4 -> 92.5, 103 94.3 -> 91.5. The candidates are now 304 at 98.5 (they were 301
  96.0, 304 95.8, 303 94.5): the other candidate seeds now fail a gate.
- The orchestra shares half_cell and the variant weights: 101 96.3 -> 96.6, 102 94.3 -> 93.1, 103 98.2 -> 98.0. Its
  candidates are now 303 at 88.8.
- Classical, lofi, jazz and organ are unchanged.

## After round g10: the floor - copied returns, weak heads, the energy before the climax, the endings (2026-10-16)

Round g10 put the generated set at 5.97 against the references' 6.67. Six pieces rated 6.4-6.8, but the bottom three
(HJJR 5.2, XWPQ 5.0, ELNQ 4.6) held the mean down, all named for weak heads or copied returns. The fixes target that
floor. `tells_newage.py`'s `g11_tells` measure them first:
- the returns' copied bars over the whole statement, at any place, not only the head;
- the head's shape;
- the energy and register before the build;
- the last A and the coda;
- the right hand's density outside the climax;
- a waltz's length and the climax's scale runs.
The `--sets` run also counts the set's distinct peaks and climax left-hand figures. The runs covered 48 seeds
(64000-64047) and 48 set slots (72000-72047). The "before" runs used the g10 code with the new measures.

| g10 fix | change | where |
|---|---|---|
| Copied returns (HJJR's four A statements; the statistician's copies in five pieces), `ret_head_copy` blind to them | Each return was varied against its own source only, so A3 / A4 came out as the return before them (the same 'rhythm' / 'seq' result). A sung return's units past the head are now also checked against every bar of the statements played before it (top line, 8th grid, Jaccard 0.7: `VARIED`); a copy tries the other kinds, then a sequence a step or two wider (per unit). More than 3 A statements only in a piece under 4 minutes as planned; else the optional return before the climax goes | `perform._vary_changed(prior=)`, `_vary` (per-unit size), `VARIED`, `A_CAP`, `_a_cap` |
| Weak heads: VBJZ off the beat in fragments, VEAS's Cb-Db shuffle, ELNQ's waltz head never landing | `composer.HEAD_SHAPE`: over the head's first 4 bars, 2+ downbeats struck (one by a note of a beat+); no a-b-a-b oscillation anywhere in the A part; a chord tone held 1.5 beats (3/4: 2) on a strong beat in bars 2-4. The A1's fit pays `melody['shape']` 0.6 per missed check, so its 40-80 attempts (best-of-N) keep the head that passes | `composer.head_shape`, `compose` (A1 attempts), genres melody `shape` (orchestra 0) |
| The energy before the climax: XWPQ's build under its A2, CDSQ's F#6 in B1 and v105 in A2 | Before the build (no build: the climax), the right hand's loudest note is at least 12 under the climax's (a soft knee). Every part section before the build is scaled so its mean melody velocity is no higher than the build's (by 0.85 at most). Every section before the climax stays 3 semitones under its peak note | `LOUD_ORDER` ('pre_under', 'build_mel', 'pre_floor'), `_loud_g10`, `PRE_TOP`, `_under_peak(margin=)` |
| Short last returns and codas: ZVNR / HABQ's 6-bar A3 without the tonic, VBJZ's 3-bar coda, CDSQ's coda without the head | The theme's last statement after the climax plays 8+ form bars (a waltz 6, 12 heard bars) and closes V7 -> I; it has no tail, no deceptive cadence and no turnaround, and a 'sus_hold' pause there becomes a 'rest' (the tonic struck, then the silence). A coda under 6 bars has the theme's head (A1's first units over their chords) before its tag. After the climax, each section enters at most 4 over the mean of the last 2 bars before it | `FINAL_A`, `_final_a`, `_close(force=)`, `CODA`, `_coda_head`, `_sign` (pause), `LOUD_ORDER['after_in']` |
| Dense right hands outside the climax: VEAS's B1 at 11.9 notes a bar, inner arpeggios in ZVNR's / HJJR's builds | The harmonized chorus plays at most 7 RH notes a bar (3/4: 5), the build 8 (6), thinned as the climax is (`_thin`). The bloom's woven figure under held notes is rarer: 0.4 -> 0.25 (none 0.25 -> 0.4) | `SECTION_NOTES`, `_thin(cap=)`, genres `_NA_BLOOM['texture']` |
| ELNQ's 95-bar waltz; VBJZ's stock G6-Db5 16th run out of the climax | A waltz plans at most 95 bars: the optional sections go (the interlude first, then the latest), then the short sections and the intro play their shortest bars. The sung climax plays no cadenza run: it holds its note (the fermata stays) | `WALTZ_FORM['most']`, `_waltz_cap`, the cadenza in `_play_piano` |
| Set variety: shared flags 25 -> 31; the statistician's template points (nine of eleven peaks on A6 / Ab6, six of eight climaxes on the 'broad' left hand) | Two new set draws, drawn after the arrival so the other draws stay put. 'peak' lowers the sung climax's peak 0 / 2 / 4 semitones under the ceiling, as far as the head an octave up allows. 'big' is the climax's favoured left-hand figure ('broad' / 'big' / 'tenths', x `BIG_PIN` 4 in its figure set). Set memory 2 for each | genres `set` ('peak', 'big'), `set_memory`, `composer.LATE_DRAWS`, `perform._arrange`, `BIG_PIN` |

Measured (before -> after; mean (max)):

| measure | 48 seeds | 48 set slots |
|---|---|---|
| return bars copying an earlier A bar (`ret_bars_copy`, the head in); past the head (`ret_body_copy`) | 0.160 -> 0.107; **0.078 -> 0.005** | 0.161 -> 0.115; **0.065 -> 0.014** |
| the most copied return body (`ret_body_max`); copied bars a piece | 0.175 (1.0) -> 0.011 (0.17); 2.56 -> 1.71 | 0.152 (1.0) -> 0.029 (0.17); 2.46 -> 1.79 |
| 4 A statements in over 4 minutes | 1 -> 0 | 2 -> 0 |
| heads passing HEAD_SHAPE (down / osc / cadence) | **0.44 -> 0.92** (0.96 / 0.44 / 0.98 -> 1.0 / 0.92 / 1.0) | **0.375 -> 0.90** (1.0 / 0.40 / 0.96 -> 1.0 / 0.92 / 0.98) |
| heads with a profile; with a repeated cell | 0.96 -> 0.96; 0.85 -> 0.81 | 0.98 -> 0.92; 0.79 -> 0.90 |
| the build's melody over the loudest section before it (velocity); pieces under it | +0.2 -> **+2.8**; 17 -> 10 | 0.0 -> **+2.9**; 20 -> 11 |
| pieces with the register before the build within 2 semitones of the peak; the loudest note there within 11 | 2 -> 0; 4 -> 0 | 5 -> 1; 6 -> 0 |
| the last A closing home; 8+ bars and home | **0.15 -> 1.0**; 0.125 -> 1.0 | **0.21 -> 1.0**; 0.15 -> 1.0 |
| coda bars; codas under 6 bars | 4.0 -> 6.3; **0.85 -> 0** | 3.3 -> 6.1; **0.96 -> 0** |
| RH notes a bar in B1 / the build; pieces over 8 / 9 | 7.3 / 7.8 -> 5.9 / 6.9; 14 / 10 -> 1 / 1 | 7.2 / 7.8 -> 5.9 / 6.8; 13 / 6 -> 1 / 2 |
| bars with 12+ RH notes outside the climax; B1 multi-note onsets | 3.4 -> 1.6; 0.60 -> 0.41 | 3.0 -> 1.3; 0.60 -> 0.40 |
| waltz bars (max); over 95 | 88 (100) -> 86.5 (92); 1 -> 0 | 89 (98) -> 84 (88); 1 -> 0 |
| climaxes with a stock scale run | 3 -> 0 | 5 -> 0 |
| the highest note (mean) | 92.1 -> 91.1 | 91.5 -> 90.75 |
| the largest velocity jump into a section after the climax (`post_jump`, max) | 26.3 -> 8.4 | 17 -> 7.6 |
| the climax follows the head (`clx_head`; >= 0.8) | 0.83 -> 0.82; 0.67 -> 0.71 | 0.85 -> 0.86; 0.73 -> 0.79 |
| score (no best-of-8) | 95.3 -> 94.9 | 95.3 -> 94.8 |

Set level (`--sets 6 --set-n 8`, from 72000):
- distinct peak notes in a set 3.8 -> 5.2;
- pieces peaking on Ab6 / A6+ 5.7 -> 3.3 of 8;
- the most played climax left-hand figure 3.7 -> 3.3 pieces;
- arrivals still 5 of 5.

The g10 judged pieces, rebuilt from their seeds:
- every head passes HEAD_SHAPE;
- no return body copies (HJJR 0.32 -> 0, XWPQ 0.25 -> 0);
- HJJR has three A statements (4:32 -> 4:08);
- every last A closes home and every coda has 6 bars;
- VEAS's B1 11.9 -> 6.2 RH notes a bar, ZVNR's build 9.7 -> 8.3;
- XWPQ's build melody -7.5 -> -1.0 under its A2;
- VBJZ's climax run is gone, and ELNQ has 90 bars (94 before).

Judged in round g11 (songs/_blind/ROUNDS.md "Round g11"): the generated mean held at 5.97 and the bottom three rose
4.93 -> 5.27. None of g10's complaints came back, except the waltz head (HEAD_SHAPE passes whole notes). New: the
coda's head copies A1's bars (the CODA head is unvaried), climaxes not from the head, and A6 peaks.

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000): arc 36.7 % -> 40.2 %, breath 14.1 % -> 7.8 %,
kept 49.2 % -> 52.0 %. The heads fitted for their shape move the parts' mean register more often (the arc check); the
thinner B1 / build breathe more.

Costs:
- The score fell 95.3 -> 94.9. The coda's head counts as one more hook statement (`hook`). The head-shape fit adds
  repeated pitches (`rep_pitch`) and a few style issues: a missed head check costs 0.6, a style issue 0.3. At 0.3
  the heads pass 0.81 / 0.83 only.
- The peak sits earlier: top_at median 0.72 -> 0.70, p90 0.78 -> 0.73 (seeds). The longer last A and coda add 2-4
  bars after the climax.
- RH holes at the climax's end 0.15 -> 0.19 (seeds).

The baseline moved: new-age 101 94.7 -> 91.6 (mel_style 3: its head fit took style issues), 102 92.5 -> 94.0, 103
91.5 -> 92.5; the candidates 304 98.5 -> 98.3. The orchestra (melody `shape` 0, PRE_TOP for a sung genre only) and
classical, lofi, jazz and organ are unchanged.

## After round g11: the climax is the head, the coda varied, a lower peak, the waltz head's rhythm, the climax's entry (2026-10-16)

In round g11 the generated mean held at 5.97 and the bottom three rose to 5.27. The judges' complaints moved into the
climax:
- its first bars were not the head;
- it peaked on A6;
- it entered softly or with a jump.

They also named the coda, which copied A1's head bars, and the waltz head, which was all whole notes.

The new `g12_tells` in `tells_newage.py` measure these first:
- `clx4_*`: the head in the climax's first 4 bars. The pass is contour 0.8+ at tolerance 0.25, rhythm 0.6+, and a
  register no more than 2 semitones under the head.
- `clx_dip`, `clx_rise2`, `clx_in_v0`: the climax's entry. These are its sag before the peak, its steepest rise over
  1-2 bars, and its first bar against the bars before it.
- `peak_a6` / `peak_over`, and `clx_c5c6`: the share of the climax's sung notes in C5-B5.
- `coda_copy`: coda bars that copy an A bar.
- `head_rate`, `head_sl`, `head_rhy_ok`: the head's rhythm.
- `b1_*`: B1's contrast.
- `pk_tail` / `tail_long`: the tail after an early peak.
- `inner_only`: RH bars with only inner voices.

The runs cover 48 seeds (64000-64047) and 48 set slots (72000-72047). The "before" runs used the g11 code with the
new tells.

A measurement fix came first. A note now counts as an inner voice (the packets' "(under)" and the tells' sung line)
only if a higher RH note is held `UNDER_HELD` = 0.25 beats past its onset. The old threshold was 0.1. At 0.1, the
melody note before it, still overlapping by a finger legato, made the melody print as an inner voice. Most of the
"RH holes with only an inner voice" that the g11 judges named came from that rule. On the same code, `inner_only`
drops from 0.35 to 0.04 under the fixed rule.

| g11 complaint | change | where |
|---|---|---|
| The climax is not the head (PTCV, KTGG, ERDL, NKTZ bars 35-38). `clx_head`'s window passed a climax whose peak bars alone stated the head. | **Motto payoff:** enters 2 bars into the climax (4 after a 'fragment' arrival), and only if it ends before the peak. It no longer replaces the head's first bars.<br>**Anthem start:** the head starts no lower than A1's, within a semitone of A1's top after the key shift (`floor`); so do the 'sequence' and 'fragment' starts.<br>**'fragment':** plays the whole head first, then the fragment (only for a cell of 3+ notes).<br>**B sections:** unswung in a sung genre, like the climax. | `perform.MOTTO_PAYOFF`, `_sign`, `_anthem(shift=)`, `ARRIVALS`, `_arrange` |
| The coda copies A1's head bars 3-8 (the statistician, six pieces). | The coda's head is now a varied return. Units 0-1 play A1's bars augmented x2 over their stretched chords. Later units are liquidated: the opening cell a step lower, then held, refitted over A1's chords. | `perform.CODA`, `_coda_head` |
| A6 peaks (LESU, NKTZ, CNWE, WNTP); ERDL sits at C6-G6. | The sung ceiling is 89 (F6; it was 93). The anthem keeps a single peak: every other strike of the top note moves a step down. A motto recurrence before the climax stays under `top - PRE_TOP`, and goes an octave down when it can. | genres `ceiling['sung']`, `_anthem`, `_sign` |
| The waltz head has no rhythm (KTGG: 1.9 RH attacks a bar). | `HEAD_SHAPE` now checks rhythm. The head's first 4 bars need 2.5+ onsets a bar in 4/4 (2.0 in 3/4), and bars 1-2 need a short-long cell: a note of 1 beat or less joined to one at least twice as long. The A1 fit pays for a miss as it does for the other checks. The hemiola opening (whole-bar notes in a 3/4 head) is no longer a set draw, and is rare in the melody openings (0.05). | `composer.HEAD_SHAPE` ('rate', 'short'), `head_shape`, genres `openings` / set 'opening' |
| The climax's entry: LESU sinks to v47, PTCV enters softly, KTGG jumps v93 -> v120. | `LOUD_ORDER['ramp']` shapes the climax's bars as a crescendo to its peak bar. The first bar is 3-12 over the bars before it, with no upper limit after a silent pause bar. Bars more than 4 under the ramp are raised and bars more than 6 over it are lowered. Both hands get the same factor, capped at the climax's top. | `LOUD_ORDER['ramp']`, `_ramp`, `_loud_g10` |
| The tail after an early peak (WNTP at 59 %). | When the planned peak sits under 0.66 of the piece, the B2 after the climax is dropped. | `perform.TAIL`, `_tail_cap` |
| B1 without contrast or a hook (WNTP, NKTZ, CNWE). | Measured only (`b1_*`). A B shift draw had no effect and was reverted. Still open. | TODO.md |

Measured (before -> after; means):

| measure | 48 seeds | 48 set slots |
|---|---|---|
| the head in the climax's first 4 bars (`clx4_ok`) | **0.40 -> 0.98** | **0.46 -> 0.94** |
| its contour there (`clx4_head`) | 0.46 -> 1.0 | 0.56 -> 0.99 |
| the old window (`clx_head`) | 0.94 -> 0.99 | 0.93 -> 0.99 |
| peaks over F6 (`peak_over`) | **0.79 -> 0** | **0.77 -> 0** |
| peaks on A6+ (`peak_a6`) | 0.44 -> 0 | 0.42 -> 0 |
| the highest note | 91.1 -> 86.9 | 90.75 -> 86.6 |
| the climax's sung notes in C5-B5 (`clx_c5c6`) | 0.62 -> 0.73 | 0.61 -> 0.75 |
| the climax's sung notes at C6+ (`clx_c6`) | 0.33 -> 0.15 | 0.34 -> 0.15 |
| coda bars copying an A bar (`coda_copy`) | **0.39 -> 0.065** | **0.40 -> 0.072** |
| heads with the rhythm (`head_rhy_ok`) | 0.94 -> 1.0 | 0.96 -> 1.0 |
| the climax's sag before its peak (`clx_dip`) | 8.1 -> 4.4 | 6.8 -> 3.1 |
| the climax's steepest 1-2 bar rise (`clx_rise2`) | 21.0 -> 15.9 | 18.1 -> 15.1 |
| the climax's first bar over the bars before it (`clx_in_v0`) | 5.5 -> 4.1 | 6.9 -> 5.5 |
| a long tail after an early peak (`tail_long`) | 0.25 -> 0.02 | 0.23 -> 0.02 |
| bars after the arch's climax | 19.1 -> 15.1 | 19.25 -> 15.25 |
| RH bars with only inner voices (`inner_only`, fixed rule) | 0.042 -> 0.021 | 0.062 -> 0.083 |
| B1 with contrast and no seesaw (`b1_ok`; still open) | 0.35 -> 0.33 | 0.35 -> 0.29 |
| the motto's payoff kept (pieces with a motto) | 1.0 -> 0.96 | 1.0 -> 0.89 |
| return bodies copying (`ret_body_copy`) | 0.005 -> 0.005 | unchanged |
| the last A 8+ bars and home | 1.0 -> 1.0 | unchanged |
| score (no best-of-8) | 94.87 -> 94.72 | 94.82 -> 94.47 |

Set level (`--sets 6 --set-n 8`, from 72000):
- pieces on A6 or higher: 3.33 -> 0 of 8;
- distinct peak notes: 5.17 -> 4.67 (the lower ceiling leaves less room);
- the most played climax left-hand figure: 3.83 -> 4.0 pieces;
- arrivals: still 5 of 5.

The g11 judged pieces, rebuilt from their seeds:
- PTCV's climax opens on the head (G5-D5-E5-F5) and peaks at E6.
- LESU, NKTZ and ERDL open their climaxes with the head. NKTZ and ERDL peak at E6.
- KTGG's old tune.json still carries the hemiola opening, because the draw is pinned in it.

Judged in round g12 (songs/_blind/ROUNDS.md "Round g12", seven judges):
- The generated mean was 5.88 and the bottom three 5.00.
- The waltz EXWH and GZAT, both 7.0, outrank every reference.
- None of g11's complaints came back: high peaks, the coda copy, the waltz head, the soft entry.
- New: the climax's head is A1 replayed louder (the `climax_copy` cost), or it is unrecognisable after a key move to
  IV (ZSTD).
- Still open: heads without a profile and B1 without a hook.

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000):
- arc: 40.2 % -> 40.6 %;
- breath: 7.8 % -> 9.0 %;
- kept: 52.0 % -> 50.4 %.

The ramp lifts some soft climax bars, and the breath gate fails a few more pieces.

Costs (points lost a piece, 48 seeds):
- `climax_copy`: +0.22. The climax now opens with the head, at A1's pitches when the C5-C6 band leaves no room for a
  lift, and this metric charges a climax for copying A1. Its range (0-0.1) was measured on the references, so it
  stays: a little copying is the price of a recognisable climax.
- `vel_jump12`: +0.09 (the ramp's first bar after a pause).
- `head_prof`: +0.06 (the rhythm check costs some fits).
- `peak_holes`: +0.06.
- `hook`: 1.37 -> 1.12, a gain, because the coda's head no longer counts as a copied hook.

The baseline moved for new-age only:

| baseline entry | before -> after |
|---|---|
| 101 | 91.6 -> 93.0 |
| 102 | 94.0 -> 93.5 |
| 103 | 92.5 -> 92.0 |
| candidates 304 | 98.3 -> 98.7 |

The orchestra, classical, lofi, jazz and organ are unchanged. The sung ceiling, the ramp, the coda and the motto
payoff are sung-genre or new-age data only.

## After round g12: the climax's head at its own degrees and a new second phrase, heads that do not circle, an answer in the head's rhythm, B's own rhythm, the head varied on return (2026-10-16)

Round g12 (seven judges) put harmony, form and performance level with the references; melody and development stayed
behind (rel 0.94 / 0.95). The judges' fixes all point at the tune: the climax heard as "A1 replayed louder" or, after a
key move, as new melody; heads that circle two notes; second phrases that wander; B1 without a hook; heads returning
as played.

The new `g13_tells` in `tells_newage.py` measure these first:
- `clx4_deg` / `clx4_dreg` / `clx4_own`: the climax's head at A1's head's pitch classes (or a whole step up), and
  within 3 semitones of its height - clx4's contour passed ZSTD's head a 4th up after a key move to IV.
- `clx_a1_cont` / `clx_a1_copy` / `clx_new2`: the climax's second unit restates A1's second unit (contour, or the
  pitches) - "A1 replayed louder" - or is new.
- `head_circle` / `head_circ_ok`: A1's first 4 bars, the most notes in one 2-semitone window (VYDA 0.58, GZAT 0.50).
- `ans_rhy` / `ans_ok`: A1's consequent (its third unit) in the head's rhythm.
- `b1_rhy_j` / `b1_rhy_own` / `b1_hook`: the B part's first unit's rhythm against the head's; its own rhythm, restated in
  B and in another register or pace. (g12_tells' `b1_cell` read `tune.parts[1]`, which is A2 in a verse form; the
  g13 tells read the B part.)
- `ret_h2_copy`: the A returns whose head's second bar copies A1's.
- `clx_holes`: climax bars with no right-hand onset (its held last bar out); `chrom_leap`: right-hand top notes
  outside the local chord scale that are leapt to or do not resolve by step; `coda_len`.

The runs cover 48 seeds (64000-64047) and 48 set slots (72000-72047); "before" is the g12 code with the new tells.

| g12 complaint | change | where |
|---|---|---|
| The climax copied (VQXW five judges, EXWH / ZEFU two: "A1 replayed louder") or unrecognisable (ZSTD four: the head a 4th up over IV after a key move). GZAT, the model: the head as written, then a third up, then the peak. | **ANTHEM_HEAD:** every anthem but 'augment' opens with the head at its own degrees (A1's, or the key move's `floor`; also the 'fragment' arrival's head and fragment), then the head a third higher, then the peak; the theme goes on from its second unit after them. The anthem kinds now differ by texture and chords.<br>**SUNG_KEYS:** a sung climax's key move is a whole step up or the parallel major (minor: also a step up); IV, bVI, bIII and the relative major are dropped. | `perform.ANTHEM_HEAD`, `_anthem`, `SUNG_KEYS`, `_arrange` |
| Heads circling two notes (VYDA, all seven: G#5, then C#5-D#5-C#5-B4-D#5-C#5; it passed `head_prof` on its bar-1 leap and held top). | `HEAD_PROFILE['circle']` {4/4: (4 bars, 2 semitones, 0.5)}: over the first 4 bars no 2-semitone window holds more than half the notes; the A1 fit pays for a miss as for the other profile checks. A waltz head's 4 bars hold too few notes to tell (not checked). | `composer.HEAD_PROFILE`, `head_profile` |
| The second phrase wanders (composerE: JQTJ 5-8, ZSTD 7-10; JQTJ's answer displaced an 8th onto beat 3). | new-age `melody['develop']` {'same': 0.55, 'truncate': 0.3, 'augment': 0.15}: the A's answer phrase keeps the head's rhythm, never displaced (DEVELOP_RHYTHM stays the default). | genres new-age `melody['develop']`, `composer.compose` |
| B1 without a hook of its own (NFLS 5, ZSTD 4, JQTJ 4, GZAT 3, ZEFU 2). | new-age `melody['b_contrast']` 0.45: the chorus's counter-motif cell shares at most that onset Jaccard with the hook's cell, else the most different opening cell (`_cell_jacc`). A wider B register shift was tried ({3, 4, -3}): it moved neither `b1_reg` nor `b1_contrast` and was reverted. | `composer.compose`, `_cell_jacc` |
| Literal head returns (VQXW four times; JQTJ A4 = bars 3-4; ZSTD 11-12 / 47-48). | `HEAD_RETURN` {A2: +1, A3: -1, A4: +1}: a sung return's head keeps its first bar (re-rhythmed or ornamented as before), its second bar moves that many scale steps, re-fitted to the return's chords, wherever it still copies the source's (VARIED); the other way where that leaves it a copy. | `perform.HEAD_RETURN`, `_head_turn` |
| VYDA's climax bar 38 empty (all seven). `peak_holes` did flag it (1.4 points), the best-of-8 kept it: the motto payoff's last note ended on beat 2 and the line note under it was cut. | `_sign`'s `put`: a line note the cell covered that sounds a beat+ past it is struck again at the cell's end; none, and a bar+ to the line: a falling chord tone holds to it (the payoff). | `perform._sign` |
| The motto payoff dropped in 11 % of the set slots (when it cannot end before the peak). | The payoff answers the peak instead: as planted, from the bar after the peak note's. | `perform._sign`, `MOTTO_PAYOFF` |
| Chromatic notes heard as wrong (JQTJ Eb5-Gb5-G5 over Ebmaj7). | A chromatic approach note is placed only when the note before it is a step away (approached by step, resolving by a half step on the beat). | `composer._fit` |
| The coda template (the statistician: seven 7-bar codas). | `CODA['bars']` {6: 1.0, 8: 0.8}, a draw per tune. | `perform.CODA`, `_coda_head` |

Measured (before -> after; means):

| measure | 48 seeds | 48 set slots |
|---|---|---|
| the climax's head at its own degrees (`clx4_own`) | **0.71 -> 0.98** | **0.69 -> 0.96** |
| its pitch classes (`clx4_deg`) | 0.70 -> 0.98 | 0.71 -> 0.98 |
| the climax's second unit A1's (`clx_a1_cont`, contour) | **0.33 -> 0.02** | **0.40 -> 0** |
| ... at A1's pitches (`clx_a1_copy`) | 0.10 -> 0 | 0.06 -> 0 |
| the head in the climax's first 4 bars (`clx4_ok`) | 0.98 -> 0.96 | 0.94 -> 1.0 |
| heads that do not circle (`head_circ_ok`) | 0.94 -> 0.98 | 0.94 -> 1.0 |
| the head profile as a whole (`head_prof`, now with 'circle') | 0.92 -> 0.90 | 0.94 -> 0.90 |
| the answer in the head's rhythm (`ans_ok`) | **0.67 -> 0.90** | **0.60 -> 0.85** |
| B's first unit in a rhythm of its own (`b1_rhy_own`) | 0.60 -> 0.98 | 0.56 -> 1.0 |
| B with a hook of its own (`b1_hook`) | 0.06 -> 0.23 | 0.10 -> 0.38 |
| B1 with contrast and no seesaw (`b1_ok`) | 0.33 -> 0.38 | 0.29 -> 0.40 |
| returns whose head's second bar copies A1's (`ret_h2_copy`) | **0.53 -> 0** | **0.50 -> 0** |
| returns whose first two bars copy A1's (`ret_head_copy`) | 0.08 -> 0 | 0.11 -> 0 |
| copied bars a piece (`copy_bars`) | 1.73 -> 0.90 | 1.71 -> 0.81 |
| return bodies copying (`ret_body_copy`) | 0.005 -> 0.012 | 0.013 -> 0.015 |
| empty climax bars (`clx_holes`) | 0.13 -> 0.04 | 0.08 -> 0 |
| the motto's payoff kept (pieces with a motto) | 0.96 -> 1.0 | 0.89 -> 1.0 |
| chromatic top notes leapt to / unresolved (`chrom_leap`) | 2.02 -> 1.54 | 1.83 -> 1.35 |
| coda bars (`coda_len`; 8 bars in the slots) | 6.3 -> 7.0 | 6.1 -> 7.1 (2 -> 27 of 48) |
| the highest note | 86.9 -> 86.8 | 86.6 -> 86.9 |
| score (no best-of-8) | 94.72 -> 94.86 | 94.47 -> 94.47 |

Set level (`--sets 6 --set-n 8`, from 72000):
- arrivals: still 5 of 5;
- distinct peak notes: 4.67 -> 4.17 (every climax now climbs the same head + third; the peak note is the head's top
  moved, so it spreads less);
- the most played climax left-hand figure: 4.0 -> 3.83 pieces; distinct figures 4.0 -> 4.33;
- distinct final right-hand grips 3.5 -> 3.83; pieces with the theme at the climax 0.93 -> 0.91.

Reject rates in set slots (2 sets x 8 slots x 16 seeds from 67000; `set_plan` slots, `shape` / `breath_gate`):
- arc: 40.6 % -> 39.5 %;
- breath: 9.0 % -> 10.5 %;
- kept: 50.4 % -> 50.0 %.

The baseline moved for new-age and the orchestra (orchestra-film shares the new-age composer and its melody data: the
answer's rhythm, the B cell and the circle check move the melodies of the baseline seeds):

| baseline entry | before -> after |
|---|---|
| new-age 101 | 93.0 -> 93.2 |
| new-age 102 | 93.5 -> 93.7 |
| new-age 103 | 92.0 -> 91.6 |
| new-age candidates | [304, 98.7] -> [300, 93.9] (304 now fails the arc check, the parts' mean register) |
| orchestra 101 | 96.6 -> 94.7 |
| orchestra 102 | 93.1 -> 95.6 |
| orchestra 103 | 98.0 -> 97.0 |
| orchestra candidates | [303, 88.8] -> [302, 96.0], [303, 87.3] |

Classical, lofi, jazz and organ are unchanged: ANTHEM_HEAD, SUNG_KEYS, HEAD_RETURN and the payoff are sung-genre only,
'develop' / 'b_contrast' / 'chromatic_step' / 'circle' new-age melody data (the chromatic approach rule is gated by
`melody['chromatic_step']`: ungated it moved jazz 101).

Judged in round g13 (songs/_blind/ROUNDS.md "Round g13", seven judges): a step back - generated 5.57 (g12 5.88), the
bottom three 4.48, rel 0.815 against references rated 6.90 (g12 6.19). No climax was heard a 4th up over IV and no
second phrase "wandering"; but the head at A1's pitches opening the climax was again heard as "A1 replayed" where its
third-up unit came late (MYUS, GALR, CPED, QTNU), the key-up climaxes were half missed as the head, and the head-first
climax became the set's shared plan. The judges' first complaints moved to holes (the phrase end flicking into a
0.08-beat stab, GALR / MYUS all seven; the motto payoff's held note, TCMN 38), proportions (the 93-bar waltz) and the
unchecked waltz head (PPHK, all seven).

Still open: B1's register / pace contrast (`b1_contrast` 0.44 / 0.48), the right hand's flat dynamics (the gate
rerolls "flat_dynamics" pieces), wrong-sounding notes from the performer's ornaments over borrowed chords (VQXW 23:
F#5 over F, ZEFU 10: an F4 inner voice under Em7).

## After round g13: the climax's first unit changed at once, holes, proportions, the waltz head, inner voices (2026-10-16)

Round g13 fell back (5.57, rel 0.815; songs/_blind/ROUNDS.md "Round g13"). The judges' first complaints:
- phrase ends flicking into a 32nd and a 0.08-beat stab, then an empty bar;
- the 93-bar waltz with a static climax;
- the unchecked waltz head;
- the climax heard as "A1 replayed";
- wrong-sounding inner voices.

Round g14 repairs these on g13's branch and is judged paired against the g12 code (master).

The new `g14_tells` in `tells_newage.py`:
- `clx_open_copy` / `clx_open_ch` / `clx_open_oct`: the climax's first unit at A1's pitches over A1's chords at A1's
  octave ("A1 replayed louder"), or with the same chords, or the same octave.
- `flick_land`: an ornament or run of notes under 0.1 beat into a phrase landing.
- `stab_bars` / `hole_bars`: bars whose only right-hand notes are stabs, and empty bars after a phrase end.
- `pay_hole`: a bar under the motto payoff's held note with no onset.
- `clx_exit_bare`: the climax's last bar on the bass alone.
- `bars` / `waltz_bars`, `clx_static` (a climax top line on one or two notes), `coda_share`, `post_peak`.
- `head_circle8` / `head_circ8_ok`: a waltz head's first 8 bars in a 3-semitone window.
- `under_n` / `under_a1` / `under_off` / `under_clash` / `under_loud`:
  - inner notes struck under a held top note;
  - those in A1;
  - those off the chord;
  - those a half step from the top;
  - those as loud as the melody.

The runs cover 48 seeds (64000-64047) and 48 set slots (72000-72047), against both the g12 and the g13 code.

| g13 complaint | change | where |
|---|---|---|
| The phrase end flicking into 32nds and a stab, then an empty bar (GALR / MYUS, all seven). The cause was the romantic 'after' turn played into a phrase landing, plus the packet printing a grace as a note. | A turn is not placed before a note of 1.5 beats or more (`ORNAMENT_LAND`). The packet prints one grace within 2 semitones of a held top note as an ornament. | `perform.ORNAMENT_LAND`, `make_packets_newage.packet` |
| The climax's exit on a bare bass (CNCJ 45-46, six). The cause was the signature pause's 'rest' / 'bass_only' kinds at the return seam. | At the climax's exit, the pause is always 'sus_hold' (`PAUSE_EXIT`). | `perform.PAUSE_EXIT`, `_sign` |
| The motto payoff's held note left an empty bar (TCMN 38, four). | A payoff note held a beat or more past a bar line gets a chord tone 3-9 semitones under it at the bar line (`MOTTO_HELD`). The payoff enters 4 bars into the climax (`MOTTO_PAYOFF['after']`), after the head's first statement. | `perform._sign` (`put`) |
| The climax opening as A1 replayed (MYUS 5, GALR 4, CPED 3, QTNU 3), and the head-first climax as the set's shared plan. | The first two bars of the sung climax are reharmonised under the head (`ANTHEM_HEAD['open'] = 'reharm'`, `_reharm(only=)`). The second phrase follows straight after, as a set draw (`ANTHEM_SECOND`): a third up, a fifth up (a third where that would reach the peak's top) or mirrored within the head's span. | `perform.ANTHEM_HEAD`, `ANTHEM_SECOND`, `_anthem`, `_arrange`; genres `set['second']`, `SET_KEYS`, `set_memory`; composer `LATE_DRAWS` |
| Wrong inner voices (MYUS Bb4 under Cadd9, TCMN F4, CNCJ Fb5). Two causes. First, harmonize's fallback whole step lay outside the key, a half step from the melody. Second, `_line` shaped those inner notes as melody notes, so they sounded at melody level. | The inner voice's fallback whole step must lie in the local chord scale (`scale_at`), and an inner pitch a half step from the melody is never taken. Inner notes under a held top note are softened by the inner factor, and `_line` skips them. | `romantic.harmonize(scale_at=)`, `_under_held`, `Score.perform`, `_line`; `perform._arrange` |
| A1 crowded with inner voices (the statistician: 8+ "(under)" a piece, 0 in the references). | A1 is played plain: no moving inner voice, and no extra companion notes under held notes (`TEXTURE_PLAIN`). | `perform.TEXTURE_PLAIN` |
| PPHK's 93-bar waltz and its static 16-bar climax (all seven). | Waltzes at most 86 bars (`WALTZ_FORM['most']`): past the cap at the shortest phrase, the build, A2, A3, B1 and B2 are pinned in turn to 'least', a 4-bar phrase. The waltz climax's bass never 'hold's (`CLIMAX_STILL`). | `perform.WALTZ_FORM`, `_waltz_cap`, `CLIMAX_STILL`; `arrangement.values` (the 'least' spec is in the learner's vocabulary) |
| Long codas (MYUS / CPED 9 bars). | The coda is at most 10 % of the bars before it, and never under 4 bars (`CODA['share']`, `'least'`). The coda length draw is {4: 0.7, 6: 1.0, 8: 0.5}. | `perform.CODA`, `_coda_head` |
| PPHK's waltz head circling (all seven): the circle check skipped 3/4. | `HEAD_PROFILE['circle'][3]` = (8 bars, 3 semitones, 0.6). The A1 fit pays an extra 0.6 for a circling head. | `composer.HEAD_PROFILE`, `head_profile` ('circle_ok') |

Measured (means; g12 code / g13 code / g14 code):

| measure | 48 seeds | 48 set slots |
|---|---|---|
| the climax's first unit A1 replayed (`clx_open_copy`) | 0.65 / 0.85 / **0.08** | 0.60 / 0.83 / **0.04** |
| ... over A1's chords (`clx_open_ch`) | 0.86 / 0.95 / **0.28** | 0.81 / 0.88 / **0.26** |
| flicks into a phrase landing (`flick_land`) | 0.65 / 0.56 / **0** | 0.52 / 0.58 / **0** |
| empty bars after a phrase end (`hole_bars`) | 0.10 / 0.06 / 0.02 | 0.06 / 0 / 0.02 |
| the climax's exit on a bare bass (`clx_exit_bare`) | 0.06 / 0.06 / **0** | 0.04 / 0.04 / **0** |
| empty climax bars (`clx_holes`) | 0.13 / 0.04 / 0 | 0.08 / 0 / 0 |
| waltz bars | 87 / 87 / **79.3** | 84.3 / 85 / **80** |
| coda bars (`coda_len`) | 6.3 / 7.0 / 5.6 | 6.1 / 7.1 / 5.6 |
| bars after the peak (`post_peak`) | 18.4 / 19.2 / 17.6 | 17.8 / 19.0 / 17.4 |
| waltz heads that do not circle (`head_circ8_ok`) | 0.38 / 0.50 / **0.88** | 0.50 / 0.83 / 0.83 |
| inner notes under a held top (`under_n`) | 21.4 / 20.6 / 16.8 | 19.1 / 19.5 / 16.9 |
| ... in A1 (`under_a1`) | 2.6 / 2.4 / **0** | 2.4 / 2.5 / **0.02** |
| ... off the chord (`under_off`) | 2.0 / 2.0 / 0.31 | 1.1 / 1.5 / 0.13 |
| ... a half step from the top (`under_clash`) | 0.46 / 0.56 / 0.23 | 0.52 / 0.46 / 0.13 |
| ... at melody level (`under_loud`) | 12.7 / 12.5 / **0.08** | 11.3 / 11.6 / **0.10** |
| the head profile (`head_prof`) | 0.92 / 0.90 / 0.85 | 0.94 / 0.90 / 0.90 |
| score (no best-of-8) | 94.72 / 94.86 / 95.17 | 94.47 / 94.47 / 95.80 |

Set level (`--sets 6 --set-n 8`), g13 -> g14:
- arrivals: 5 -> 5;
- distinct peak notes: 4.17 -> 4.33;
- shared3: 23.2 -> 27.8.

On the judged set (seeds 85000-85007), the g12 half -> the g14 half:
- `clx_open_copy` 0.5 -> 0.25, `clx_a1_cont` 0.5 -> 0;
- the answer in the head's rhythm 0.375 -> 1, B1 with a hook 0 -> 0.5;
- copied bars 2.0 -> 0.75, `under_loud` 11 -> 0.25;
- waltz 84 -> 80 bars.
- Render rejects: 64 (g12 code) -> 53 (g14 code), for 55 candidates each.

The baseline moved:

| baseline entry | before -> after |
|---|---|
| new-age 101 | 93.2 -> 92.3 |
| new-age 102 | 93.7 -> 94.6 |
| new-age 103 | 91.6 -> 92.2 |
| new-age candidates | [300, 93.9] -> [302, 95.5], [300, 95.4] |
| classical candidate 300 | 92.9 -> 92.8 (the shared inner voice / harmonize change) |
| orchestra | unchanged |

Judged in round g14 (songs/_blind/ROUNDS.md "Round g14"), paired against the g12 code on the same 8 seeds and the
same 14 judges:
- **The g14 code wins by +0.29 overall** (melody +0.38, development +0.54, memorable +0.33; harmony and performance
  level). Five slots won and three lost, so the win is not significant on its own.
- No judge named a flick, a stab or an empty bar after a phrase end. The waltz rose from the bottom (+1.57, every
  judge).
- The new complaints are the climax's height and the bars after it:
  - the peak too low (JQHZ never above B5, MFMM D6);
  - the return after the climax as loud as the climax, or replayed at A1's level (WYQD, RQHP);
  - the first climax unit still at A1's register (the statistician counts it as an aligned copy).

## Ideas: what else would make the piano pieces sound composed (2026-10-15)

The ideas below are ranked by expected impact against effort. Each names the blind tells it answers: the round-3
judges (docs/LEARNED_GENERATOR.md 13.7) and the single-piece judge of the student's packet RKNF (2026-10-15,
"machine, 64 %").

| # | idea | tells it answers | impact | effort | where |
|---|---|---|---|---|---|
| 1 | **The climax carries the theme.** The climax restates the head augmented, an octave up or sequenced to a new peak (the `grow` / `theme` kinds by default), and its peak note is the melodic goal of a phrase, not an arpeggio top. The bloom before it states the head in diminution (the woven 16ths quote the head's intervals instead of plain chord tones). | climax = neighbour cells over a generic loop, the peak an arpeggio top (RKNF 3); "climaxes built from the theme" (13.9 #1) | high | medium | `perform._arrange` climax weights, `_grow`; `_handoffs` weave pitches from the motif |
| 2 | **A prepared key plan.** A key change is entered through a pivot (a secondary dominant or a common chord, one bar) and left through the old dominant, or with a common-tone shift and a return. A chromatic block with no way in is never allowed. | unprepared key jumps at the climax (13.7 #1) | high | low-medium | `perform._pivot` / `_keys` for every non-home key, not only 'step'; a `key_prep` metric |
| 3 | **Phrase-end grammar.** A phrase lands on a strong beat and the next one is entered by a pickup, an echo of the last cell in the tenor (the left hand), or a real silence with the pedal lifted. A note tied over the barline into an empty right-hand bar is avoided. | phrase ends held into empty bars (13.7 #2) | high | low | composer `ends` / `max_hold`; the hand-off mechanism can play the echo |
| 4 | **Chord tones under long notes.** A note of 1.5 beats or more is a chord tone. An appoggiatura is allowed when it resolves by step within the beat. | long notes chord tones 69-79 % vs 88-98 % (13.7 #5); stray C#5 over Gmaj7 (RKNF 5) | high | low | `melody_issues` rule + a `long_ct` score metric |
| 5 | **Motto rhythm cells.** One or two motto cells per piece, placed at formal points (phrase heads, the cadence bar). The bars between them get syncopations, triplets and held notes. Today one cell opens most bars in every section, and the pieces have 0.33-0.49 distinct cells per bar (composed pieces: 0.12-0.30). | too many rhythm cells per bar (13.7 #4); one cell opening most bars (RKNF 1) | high | medium | composer cell draw: a per-piece motto budget; `cells_bar` / `bar_open_same` metrics |
| 6 | **Form archetypes and proportions.** Draw the form from ABA', rondo ABACA, theme and variations, and an arch. Phrase lengths may be irregular when there is a reason: a 5-bar phrase from an extended cadence, an elision. Spread the climax place over 45-85 % (19/24 sat at 70-79 %), and use a subito piano or a bar of silence before the climax instead of a textbook ramp. | shared form templates, climax at 70-79 % in 19/24 (13.7 #3); the 8-bar grid padded to 9, the dynamics ramp (RKNF 5) | high | high | `plan['sections']` layouts, `set` draws |
| 7 | **Motivic development.** Sequence by step and by 3rd, fragmentation (head only, 2-1-1 liquidation before the cadence), inversion of the head in B, augmentation at the climax, diminution in the bloom. Returns transform the cells instead of reshuffling them or moving them an octave. | returns only reshuffled / octave-shifted (RKNF 4); "A3 copies A1 with a thinner left hand" (13.7) | high | medium | `perform._vary` (seq / invert exist) in the climax and bloom, not only in returns |
| 8 | **Left-hand figures shaped by the phrase.** The figure builds over 2 bars and changes at phrase boundaries, never toggling bar by bar. The octave bass is kept for the phrase peak, not every downbeat. The crest note of the figure moves by step from bar to bar (a thumb melody in the tenor). | the climax hand toggling 16th / 8th per bar, an octave bass on every downbeat (RKNF 2) | medium-high | low | done for the bloom and the climax's 2-bar units; the crest line in `pianist.figure` |
| 9 | **An inner counter-melody.** Under held melody notes, a tenor or alto line in 3rds / 6ths moving against the tune (the hand-off's sibling: one voice, not an arpeggio). | "a chorus of held notes" (13.7 #6) | medium | medium | a `counter` event kind in `_handoffs` |
| 10 | **The waltz's harmonic rhythm.** A hemiola (2 against 3) into the cadences, and chord changes on beat 3 now and then. | the waltz's two-bar "X - X/inversion" grid (13.7 #7) | medium | low-medium | `perform._moving_bass`, waltz cells |
| 11 | **Pedal points.** A dominant pedal under the build (the bloom's natural floor), a tonic pedal under the coda, the harmony moving above. | (the judges praised the pedal-point reharmonisation in RKNF) | medium | low | `figure()` with a fixed lad[0]; a `pedal` build block exists |
| 12 | **Cadenza moments.** A free run into the climax, or before the last return, over a held V7 / ii-ø with a fermata (1-2 bars; today a 2-beat run in 15 % of the climaxes). | the climax's arrival unprepared | medium | low | `cadenza` chance, length |
| 13 | **Dynamics and agogics as phrasing.** Terraced and subito dynamics, asymmetric hairpins (long crescendo, short diminuendo), agogic weight on the phrase's goal note and on its dissonances. | textbook dynamics ramp (RKNF 5) | medium | low | `plan['sections'][..]['dyn']` choices, `romantic.ASYNC` peak_ms |
| 14 | **Left-hand idioms per mood.** Rain: open 5ths and sus pedals. Longing: a lament bass (a descending tetrachord). Hopeful: walking 10ths. Morning: rising Alberti-like 8ths. The waltz: barcarolle with hemiola. | one hand vocabulary in every piece | medium | low | `_NA_FIGURES` per mood (today per feel) |
| 15 | **Register planning.** A register map per piece: the theme in the middle, the melody once in the tenor (in the left hand, the right hand accompanying above), hand crossings for a bell motif, the climax high. | the fixed bass-low / melody-high split (HUMAN_FEEDBACK 2026-10-15) | medium | medium | the bloom's lift is a first step; a 'tenor' section draw |
| 16 | **Silence.** A measured general pause before the climax or after it, and real rests with the pedal up instead of notes ringing into empty bars. | phrase ends held into empty bars (13.7 #2) | medium | low | `fermata` on a rest; the pedal's `dry` spans |
| 17 | **The climax's way out varies.** Today every climax ends with the same near-vertical tempo collapse (a deep ritardando plus a fermata) over the same low octave walk in the left hand. Draw the way out: a 2-bar broadening, a tenuto with no fermata, a fermata on a rest, or a run down; keep the octave bass for one or two peak bars. | the bloom A/B judge (2026-10-15): "the same sharp tempo collapse and the same C1-C2 octave walk in every version" | medium | low | `plan['sections']` climax `rit` / `fermata`, `_NA_FIGURES['big']` |
| 18 | **The push grows from before the section line.** The accelerando starts in the bar before the bloom, or mid-phrase, so the tempo curve does not step at the section boundary. | the bloom A/B judge: "the tempo push starts and stops exactly at the section lines" | low-medium | low | `_play_piano` tempo loop (the ramp may not cross a set_tempo: move the set) |

Done in this round: 8 for the bloom and the climax, and the first steps of 1 (the bloom leads into a climax that keeps
its push) and 15 (the left hand rises to the melody in the bloom). After round g1: more of 1 (the `grow` climax opens
with the hook augmented, the octave transplants rarer), of 7 (the returns reharmonised) and of 10 (no 'X / X-inversion'
fallback in the waltz).

## References

- Banowetz, J. (1985). *The Pianist's Guide to Pedaling*. Indiana University Press.
- Bresin, R., & Battel, G. U. (2000). Articulation strategies in expressive piano performance. *Journal of New Music
  Research* 29(3), 211-224.
- Friberg, A. (1991). Generative rules for music performance: a formal description of a rule system. *Computer Music
  Journal* 15(2), 56-71.
- Friberg, A., Bresin, R., & Sundberg, J. (2006). Overview of the KTH rule system for musical performance. *Advances
  in Cognitive Psychology* 2(2-3), 145-161.
- Friberg, A., & Sundberg, J. (1999). Does music performance allude to locomotion? A model of final ritardandi
  derived from measurements of stopping runners. *JASA* 105(3), 1469-1484.
- Goebl, W. (2001). Melody lead in piano performance: expressive device or artifact? *JASA* 110(1), 563-572.
- Hennig, H., Fleischmann, R., Fredebohm, A., et al. (2011). The nature and perception of fluctuations in human
  musical rhythms. *PLoS ONE* 6(10), e26457.
- Palmer, C. (1989). Mapping musical thought to musical performance. *JEP: Human Perception and Performance* 15(2),
  331-346.
- Palmer, C. (1996). On the assignment of structure in music performance. *Music Perception* 14(1), 23-56.
- Penel, A., & Drake, C. (1998). Sources of timing variations in music performance: a psychological segmentation
  model. *Psychological Research* 61, 12-32.
- Repp, B. H. (1992). Diversity and commonality in music performance: an analysis of timing microstructure in
  Schumann's "Träumerei". *JASA* 92(5), 2546-2568.
- Repp, B. H. (1996a). Patterns of note onset asynchronies in expressive piano performance. *JASA* 100(6), 3917-3932.
- Repp, B. H. (1996b). Pedal timing and tempo in expressive piano performance: a preliminary investigation.
  *Psychology of Music* 24(2), 199-221.
- Repp, B. H. (1997). Acoustics, perception, and production of legato articulation on a computer-controlled grand
  piano. *JASA* 102(3), 1878-1890.
- Sloboda, J. A. (1983). The communication of musical metre in piano performance. *Quarterly Journal of
  Experimental Psychology* 35A, 377-396.
- Sundberg, J., Friberg, A., & Frydén, L. (1991). Common secrets of musicians and listeners: an
  analysis-by-synthesis study of musical performance. In P. Howell, R. West & I. Cross (Eds.), *Representing
  Musical Structure*. Academic Press.
- Todd, N. P. M. (1985). A model of expressive timing in tonal music. *Music Perception* 3(1), 33-58.
- Todd, N. P. M. (1992). The dynamics of dynamics: a model of musical expression. *JASA* 91(6), 3540-3550.
- Vernon, L. N. (1936). Synchronization of chords in artistic piano music. In C. E. Seashore (Ed.), *Objective
  Analysis of Musical Performance* (University of Iowa Studies in the Psychology of Music IV).
