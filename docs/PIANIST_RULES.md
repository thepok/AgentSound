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
| Level budget: in every phrase the accompaniment sits under the melody. This holds wherever the melody plays; a left hand alone keeps its own level. | Palmer 1996; Goebl 2001 | melody about 10-25 velocity steps above the other voices (approx.) | `below_db` 6: the phrase's LH median at least 6 dB (velocity) under the melody's |

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
| The hand-to-hand figure (Für Elise's A section). In a bar whose melody note is struck by the half bar and held to the next downbeat, the left hand climbs and holds, and the right hand carries the figure on from just above it into the next melody note: the chord's tones, or the key's scale when the chord has too few there. It is never placed into a phrase end. | `_handoffs`, `handoff`, `bloom_hand` / `hand` (ring / up / ring16 / up16 / waltz_hand / waltz_up / waltz_hand16) | bloom 0.85 per held bar; elsewhere A 0.12, B 0.2, C 0.25 |
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
its push) and 15 (the left hand rises to the melody in the bloom).

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
