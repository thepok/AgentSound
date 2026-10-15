# The orchestra's performance rules

This document covers what the rule-based orchestra does to written notes so that they sound played by sections
under a conductor. It also says where each rule lives and which research it comes from.

There is no human performance data and no learned model. Every rule is a published finding. Each one is written as
a distribution or a budget in a table that `agentsound/bandlib/ensemble.py` keeps. The pianist's counterpart is
[PIANIST_RULES.md](PIANIST_RULES.md).

## Which layer plays the orchestra

`orch.perform(band, role, clip, at)` plays every part of the orchestra presets: `string_quartet`,
`chamber_orchestra`, `symphony_orchestra` and `film_orchestra`. `orch.Score` collects a whole piece and calls it at
the end. The organ (`church_organ`) is untouched: its roles stay plain legato. Four layers act on the notes:

| layer | what it owns | where |
|---|---|---|
| the score | the dynamics map: marks, hairpins, subito, bar accents, phrase arcs; doublings; which notes are a LINE (melody) | `bandlib/scoring.py` (`orch.Score`) |
| the desk | balance (accompaniment phrases under the melody), melodic and harmonic charge | `Score._apply_balance`, `Score._apply_charge` (shared rules: `expressive`) |
| the section | articulation from the sounding length, legato overlaps, bowing, breaths, brass entries, releases, ensemble timing, the dynamics lane, solo vibrato | `orch.perform` -> `ensemble.*` |
| tempo lanes | ritardandi, fermatas, tempo changes: the conductor's tempo | `song.ritardando` / `fermata` / `set_tempo` (`tempo.py`) |

You can change single values with `orch.perform(..., rules={'breath': {'budget_s': {'flutes': (5, 7)}}})` or
`orch.Score(..., rules=...)`. Unknown tables or keys are errors.

`style=` scales the rules (`ensemble.STYLES`). The default is `'film'` for `film_orchestra`, and `'classical'` or
the band's `info['style']` otherwise.

| style | effect |
|---|---|
| `baroque` | terraced dynamics (steps, not hairpins), half the swell and vibrato |
| `classical` | 0.8 swell, 0.8 vibrato |
| `romantic` | 1.2 swell, 1.1 vibrato and timing, 1.2 phrasing |
| `film` | 0.85 timing: a click-track session plays tighter |

## The shared layer: `agentsound/expressive.py`

These rules are not specific to any instrument. They live in one module that the pianist (`romantic`) and the
orchestra both use. Each player then turns them into its own vocabulary.

| rule | source | pianist | orchestra |
|---|---|---|---|
| Melodic charge (`CHARGE`, `melodic_charge`) | Sundberg, Friberg & Frydén 1991 | velocity on the melody | velocity on the Score's LINE notes, which then becomes the dynamics lane |
| Harmonic charge (`harmonic_charge`, per-change keys, `tension`) | as above | left hand, with tension | every covered note, from the Score's harmonies (`sc.harmony`, and `winds` / `brass` / `stabs` / `bed`) |
| Punctuation (`PUNCTUATION`, `punctuation`) | Friberg, Bresin, Frydén & Sundberg 1998 | (articulation rules) | a bow lift or breath of air at a group's end inside a legato line (`ensemble.connect`) |
| High-loud (`HIGH_LOUD`) | Friberg 1991 | `humanize.touch(pitch=)` | through `Score._shape` (`humanize.touch`) |
| Correlated timing (`correlated`, `rho` = `tempo.LILT_RHO` 0.6) | Hennig et al. 2011 | the lilt | each section's onset deviation, and the leader's drift |
| Phrase arc, final ritard | Todd 1992; Friberg & Sundberg 1999 | `humanize.Body` | the Score's phrase arcs; ritardandi and fermatas are the song's tempo lanes |

`romantic.CHARGE`, `romantic.melodic_charge` and `romantic.harmonic_charge` are the `expressive` objects, so the
pianist's behaviour is unchanged (`test_ensemble.TestShared`, `test_romantic`).

## The rule tables

Ranges marked "approx." are summaries of the cited studies, not one measured number. The lane is the sampler's
dynamics controller, 0..1. Below velocity 112 it follows 16^v / 16, about 24 dB over the range; above that it is
flat (`ensemble.db_of`).

### Ensemble timing: `ensemble.ENSEMBLE` (`timing`)

| rule | source | published range | value |
|---|---|---|---|
| Asynchronization between the voices of an ensemble. A section's onsets scatter around the beat, each section with its own spread. | Rasch 1979, 1988 | 30-50 ms RMS between two players (trios, wind and string ensembles); conductor-led orchestras at the low end (approx.) | `sd_ms`: strings 25, woodwinds 18, brass 18, horns 21, choir 22, struck 10, other 16. Pairwise between simultaneous section onsets: 18-23 ms in the audit pieces |
| Strings are looser than winds, and larger sections looser than small ones. | Rasch 1988 | strings above winds; a section's own spread grows with its size (approx.) | strings 25 vs winds 18; solo players x `solo` 0.85 |
| Sharp attacks synchronise tighter than soft ones. | Rasch 1979; Vos & Rasch 1981 (perceptual onset) | | `short` 0.7 for staccato, pizzicato, marcato and struck notes |
| Slow music is looser. | Rasch 1988 (asynchrony grows with the IOI) | | x (90 / BPM)^0.5, within 0.75..1.3 |
| Leader-follower timing. The sections follow the leader's (concertmaster's) drift by phase correction, so the deviation is partly shared. | Wing et al. 2014; Keller 2008 | correction gains about 0.2-0.8 per beat (approx.) | `drift_ms` 8 (AR(1) per beat, seeded per song); `follow` 0.7, the leader `violins1` at 1 |
| Each section's deviation is correlated from onset to onset, not white. | Hennig et al. 2011 | long-range correlated timing | AR(1) with `rho` 0.6 (= `expressive.KTH['rho']`); measured lag-1 autocorrelation 0.4-0.8 |
| The seat. The melody instruments and the leader are a little ahead; the low strings and horns a little behind (distance, slower attack). | Rasch 1979 (melody lead of a few ms) | a few ms | `seat_ms` -4 (violins I) .. +5 (basses, tuba) |
| No onset leaves the beat by more than a bound. | | | `max_ms` 60 |

Long notes still start `band.info['lead_ms'][role]` early, so that a slow sample attack SOUNDS on the beat (Vos &
Rasch 1981; Gordon 1987: perceptual attack time). `orch.lead` now converts ms to beats exactly through the tempo map.
Before this change, `Score.perform` used the song's FIRST tempo everywhere. In unbowed's Allegro at 148 BPM that
left the sustained notes 56-75 ms late against the shorts, which was the largest timing error the audit found.

### Dynamics: `ensemble.DYNAMICS` (`lane`)

| rule | source | published range | value |
|---|---|---|---|
| A phrase is one continuous curve. Inside a legato line the lane glides from note level to note level (a hairpin through the line). Detached notes step. | Todd 1992; Friberg et al. 2006 (DM phrase arch) | | `phrase_gap` 0.5 beats ends a phrase; glides only between notes that connect |
| Terraced dynamics in Baroque style; hairpins from the Classical period on. | performance practice (Quantz 1752; Donington 1963) | | `STYLES['baroque']['terrace']` |
| Messa di voce. A long note swells and fades, by more the longer it is, and only on notes that are LONG in their context. | Todd 1992; Gabrielsson & Juslin 1996; string and wind pedagogy (Galamian 1962) | a few dB (approx.) | `swell_s` 1.2 s and at least `swell_rel` 1.5 x the phrase's median length; `swell_share` 0.7; depth 1.5 dB + 1 dB/s, at most 6 dB; peak at 35-65 % |
| Accents fall back. A marcato or sforzando attack sits over the level and decays. An unmarked loud note is an accent only where it stands out from the note before it. | DM *duration contrast* / accent rules (Friberg et al. 2006) | | `accent_db` 3 over `accent_ms` 180; `accent_rise` 8 velocity |
| At ff the sampler curve is flat. An accent or swell there is heard as its FALL: the note's level drops so that the shape can rise to the top. | (the sampler's curve) | | `ensemble._fit` |
| Held notes follow a written crescendo or diminuendo inside them. | | | `follow=` (the Score's dynamics map) |

### Bowing: `ensemble.BOWING` (`bow`, `articulation.bow_changes`)

| rule | source | published range | value |
|---|---|---|---|
| Down-bow / up-bow. Detached strokes alternate, and the down-bow is heavier. After a rest the next stroke is a down-bow again (the rule of the down-bow). | Galamian 1962 | | `weight` 4 velocity, `max_beats` 1, `reset_beats` 1 |
| A repeated pitch in a connected line takes a new stroke: a short gap. | Friberg et al. 2006 (DM repetition articulation) | some tens of ms (approx.) | `repeat_ms` 30-55 |
| A solo player changes the bow in a long tied line. | Galamian 1962 | a full bow lasts a few seconds at p (approx.) | `stroke_s` 4, `change_ms` 40 |

### Breathing: `ensemble.BREATH` (`breathe`)

| rule | source | published range | value |
|---|---|---|---|
| A breath budget per instrument. The oboe's small airflow lasts longest, the flute's and the low brass's large airflow shortest. | Bouhuys 1964; Fuks & Sundberg 1999 (airflow, lung volume) | phrases of about 5-15 s between breaths (approx.) | `budget_s` (seconds, seeded): flutes 6-9, oboes 10-14, clarinets 9-12, bassoons 8-11, horns and trumpets 7-10, trombones 6-9, low brass and tuba 5-8; x `loud` 0.8 at f |
| A breath goes at a phrase point and never mid-gesture. The best boundary inside 0.45-1.3 x the budget is chosen by: a group end (punctuation) +2, after a long note, a downbeat +1 / half bar +0.5, before a leap +0.5, never between a pickup and its downbeat (-1.5), plus `jitter` 0.8 per section so the sections do not all breathe on one bar line. | Fuks & Sundberg 1999; wind pedagogy | | `min_into` 0.45, `over` 1.3 |
| The breath gap. | Fuks & Sundberg 1999 (inhalation times) | about 150-400 ms at a phrase break; a catch breath is quicker (approx.) | `gap_ms` 150-300 (at most 40 % of the note); after a held note (>= 2 beats) a catch breath of 90-160 ms |
| A section staggers its breaths, so a held chord never empties. | orchestral practice (staggered breathing) | | `stagger`: in a chord, every other voice breathes per breath point |
| A written rest of 150 ms or more is a breath already. | | | `taken_ms` 150 |

### Legato: `ensemble.LEGATO` (`connect`)

| rule | source | published range | value |
|---|---|---|---|
| Notes written connected overlap by the family's transition time: no gap and no re-attack. The sampled section crossfades. | Repp 1997 (legato overlap on the piano, by analogy); string and wind legato transitions in sampled-orchestra practice (approx.) | tens of ms | `overlap_ms`: strings 40-70, woodwinds 15-35, brass 20-40, horns 25-45, choir 30-60 |
| A group end inside a legato line gets a micro-pause (a bow lift or a breath of air). | Friberg et al. 1998 (DM punctuation) | 25-55 ms (approx.) | `expressive.PUNCTUATION`: `ms` 25-55; a note >= 2 x its predecessor followed by a shorter one, or a leap >= 9 semitones; notes >= 0.75 beats |

### Articulation: `ensemble.ARTICULATE` (`articulate`)

| rule | source | published range | value |
|---|---|---|---|
| Short, spiccato or marcato is chosen from the SOUNDING length (ms) and the tempo, not from the written beats. | Bresin & Battel 2000 (articulation vs tempo); string pedagogy | spiccato above about 6 notes/s (approx.) | `short_ms` 260, or <= 0.5 beats and < 420 ms; strings closer than 170 ms bounce (spiccato); a loud short-ish note (>= 112) is marcato |

### Brass: `ensemble.BRASS` (`entries`, `lane`)

| rule | source | published range | value |
|---|---|---|---|
| A brass entry after a rest is tongued: a light accent that falls back. | brass pedagogy; DM accent | | trumpets, trombones and tuba +6 velocity (not above 118), +1.5 dB falling back in 150 ms |
| Horns enter softer and bloom: a slower attack. | horn acoustics (slower attack transients: Luce & Clark 1967) | | -4 velocity, from 1.5 dB under the level over 250 ms |

### Releases: `ensemble.RELEASE` (`release`)

| rule | source | published range | value |
|---|---|---|---|
| A held note before a rest, a fermata or the end: the sections let go a little apart and taper instead of stopping at a wall. | Rasch 1988 (offset asynchrony larger than onset asynchrony) | offsets scatter more than onsets (approx.) | `sd_ms` 30 within 70; taper 3 dB over 300 ms; notes >= 1.5 beats before >= 2 beats of rest |

The final ritardando is the song's tempo lane (`song.ritardando` / `fermata`, Friberg & Sundberg 1999 curve). The
orchestra does not add one of its own.

### Vibrato: `ensemble.VIBRATO` (solo roles: `orch.perform` on `mono` roles)

| rule | source | published range | value |
|---|---|---|---|
| Delayed vibrato. A straight tone first, then the vibrato grows. | Seashore 1938; Geringer & Allen 2004; Gleiser & Friberg 2003 | onset some hundreds of ms (approx.) | delay 0.2-0.35 s, growing over 0.45 s; measured onset 480-570 ms (string quartet) |
| The rate. | Geringer et al. 2010 | 5.5-6.5 Hz (violin, cello) | 5.6 Hz |
| The depth follows the dynamics: wider when louder. | Gleiser & Friberg 2003; Prame 1997 (singers) | | depth x (0.6 + 0.7 x lane level); measured depth-vs-level r = 0.54-0.68 (was -0.1) |

### Balance: `ensemble.BALANCE` (`orch.Score`)

| rule | source | published range | value |
|---|---|---|---|
| Melody over the accompaniment, as a level budget. Every accompaniment phrase (not a LINE; not a short or accented note) is pulled down as a whole until 75 % of its notes sit at least 2.5 dB under the melody sounding with them, by at most 4 dB. Its own hairpins are kept. | orchestration practice (Adler 2016; Rimsky-Korsakov 1913, balance of the groups); Palmer 1996 (melody prominence, by analogy) | a few dB (approx.) | `db` 2.5, `max_db` 4, `phrase_gap` 1 beat, `share` 0.75 |

A LINE is either `add(..., line=True)` or decided automatically: one role, no figure, 4 or more notes one after
another on 3 or more pitches, moving at least every 2 beats. Voicings (dicts), figures, `hits`, `brass`, `winds`,
`unison` and `bed` are accompaniment.

## Audit and A/B (2026-10)

Two pieces were measured: `songs/unbowed` (a symphony first movement on `symphony_orchestra`, through `orch.Score`;
56 BPM introduction, 148 BPM Allegro, fugato, cadenza, coda) and the `film_orchestra` demo (100 BPM). Both use the
same notes, seed and mix. Old is master at 3e763eb; new is this branch.

The renders are `songs/_demo_orchestra_player/<piece>/out/ab_old.mp3` and `ab_new.mp3`, loudness-matched to
-20 LUFS. The audit script hooks `orch.perform`, compares every played note with its written one, and reads the
lanes.

### (a) Measured against the published ranges

| measure | unbowed old | unbowed new | film old | film new | published |
|---|---|---|---|---|---|
| onset asynchrony RMS vs the beat (all sections) | 19.9 ms | 13.8 ms | 2.4 ms | 10.3 ms | |
| pairwise asynchrony between sections' simultaneous onsets | 32.0 ms (systematic: sustains +56-75 ms late in the Allegro, the lead bug) | 23.1 ms | 4.2 ms | 18.4 ms | 30-50 ms between players (Rasch); a conductor tightens it |
| strings / winds / brass RMS | 20.8 / 11.0 / 10.5 | 13.8 / 11.2 / 10.2 | 2.2 / 2.7 / 2.6 | 10.1 / 10.1 / 10.4 | strings looser than winds |
| slow sections (intro 56 BPM, cadenza) | 8.3 / 1.2 ms | 22.9 / 15.4 ms | | | looser when slower |
| lag-1 autocorrelation of a section's deviations | 0.4-0.9 (drift from the lead bug) | 0.4-0.8 | -0.5..0.6 | 0.2-0.8 | correlated (Hennig) |
| legato pairs: median overlap, strings | -74.4 to -74.8 ms (a constant gap) | +15 to +56 ms | about 0 | +48 to +61 ms | overlap, no gap |
| legato pairs: median overlap, woodwinds | -41.5 ms (constant) | +21 to +26 ms | about 0 | +19 to +23 ms | |
| longest stretch without a breath, flutes | 19.0 s | 14.5 s (p90 6.3) | 19.2 s | 6.9 s | within the budget, never mid-phrase |
| dynamics lane range inside a phrase, strings and winds | 6-10 dB (every long note a 9 dB swell) | 3.5-6 dB | 2.2 dB on held parts (no shaping) | 5-6 dB | a few dB |
| share of long notes that swell | 0.84-0.97 | 0.31-0.76 | 0.0 | 0.6-1.0 | not every note |
| melody minus the loudest sustained accompaniment (median) / masked share | 0.9 dB / 29 % (55 onsets both saturated) | 1.8 dB / 17 % (0 saturated) | | | melody on top |
| solo vibrato depth vs dynamics (string quartet) | r = -0.1 | r = 0.54-0.68 | | | wider when louder |

### Gates

| piece | version | LUFS-I | true peak | clicks (all masked in the mix) | silent notes | flat-dynamics phrases | timpani `flat` (info) |
|---|---|---|---|---|---|---|---|
| unbowed | old | -19.8 | -1.2 | 3 | 0 | 39 | yes |
| unbowed | new | -20.6 | -2.6 | 2 | 0 | 38 | yes |
| film | old | -15.4 | -1.2 | 2 | 0 | 6 | no |
| film | new | -15.8 | -1.2 | 2 | 0 | 7 | no |

The new versions are 0.4-0.8 dB quieter. That comes from balance pulling the accompaniment down and from ff swells
being heard as falls. The section loudness arc keeps its shape, the same warnings appear, and no new warn appears.

### (b) The learned ears (same-song A/B, loudness-matched; `python -m agentsound ears --instrument orchestra`)

| piece | realism old -> new | PQ | CU | P(real orchestra) |
|---|---|---|---|---|
| unbowed | 59.1 -> 58.4 | 8.02 -> 7.99 | 8.00 -> 7.95 | 0.477 -> 0.481 |
| film | 59.9 -> 61.4 | 7.64 -> 7.69 | 7.64 -> 7.70 | 0.633 -> 0.634 |

Both differences are within the noise. The ears flag damage of about 10 points, and they cannot hear ensemble
timing or phrasing (README section 6). They were not optimised on.

### (c) Blind judges (3 conductor/orchestrator lenses, identical prompts, A/B shuffled, two rounds)

The judges saw anonymised numbers and plots (notes per section, the lanes, the mix level) and never the key.

| round | unbowed: prefers new | film: prefers new | overall realism, old -> new (mean of 3) |
|---|---|---|---|
| 1 | 3 of 3 (70-75 %) | 3 of 3 (70-75 %) | unbowed 3.8 -> 6.2; film 3.0 -> 5.7 |
| 2 (after the fixes below) | 3 of 3 (70-75 %) | 3 of 3 (80 %) | unbowed 3.8 -> 6.5; film 3.0 -> 6.0 |

The tells from round 1, and what was fixed for round 2:

- Every loud note in an ff tutti was an accent: a sawtooth. Now an unmarked note is an accent only `accent_rise`
  over the note before it.
- At the film's peak every section swelled every bar, in phase. Now only notes long in their context swell, with
  a seeded share and peak place.
- Brass breaths left holes in held chords, all on one bar line. Now chords stagger their breaths, a held note
  gets a quick catch breath, and each section has its own choice.
- Detached ostinato notes were smeared by lane glides. Now they step.

The remaining tells are open items in TODO.md:

- the ff tutti lanes still move with the written velocities instead of holding a plateau;
- a mono low-brass or tuba line breathes at every chord change of a slow pad (no desks to stagger);
- the melody margin is still under 3 dB in tuttis;
- a few sections carry a mean bias of 10-14 ms over few notes.

### Where the sound changed

Every song that plays sustaining roles through `orch.perform` or `orch.Score` changes sound. That is intended, and
the songs are not re-tuned:

- `songs/unbowed`, `songs/lux-perpetua`, `songs/ashes-and-chandeliers`, `songs/when-the-year-turns-gold`
- `songs/_bands/{string_quartet, chamber_orchestra, symphony_orchestra, film_orchestra}`
- `songs/_demo_orch_sections`

Struck and plain roles now use the ensemble timing instead of the triangular jitter (`humanize_ms=` a number keeps
the old jitter). The organ (`church_organ`, the `pro-organ-*` songs, endless organ) and every pianist song
(`romantic`, unchanged through the shared charge) do not change. No baselines were regenerated: no test pins
orchestral audio.

## References

- Adler, S. (2016). *The Study of Orchestration* (4th ed.). Norton.
- Bouhuys, A. (1964). Lung volumes and breathing patterns in wind-instrument players. *Journal of Applied
  Physiology* 19(5), 967-975.
- Bresin, R., & Battel, G. U. (2000). Articulation strategies in expressive piano performance. *Journal of New Music
  Research* 29(3), 211-224.
- Donington, R. (1963). *The Interpretation of Early Music*. Faber.
- Friberg, A. (1991). Generative rules for music performance. *Computer Music Journal* 15(2), 56-71.
- Friberg, A., Bresin, R., Frydén, L., & Sundberg, J. (1998). Musical punctuation on the microlevel: automatic
  identification and performance of small melodic units. *Journal of New Music Research* 27(3), 271-292.
- Friberg, A., Bresin, R., & Sundberg, J. (2006). Overview of the KTH rule system for musical performance. *Advances
  in Cognitive Psychology* 2(2-3), 145-161.
- Friberg, A., & Sundberg, J. (1999). Does music performance allude to locomotion? *JASA* 105(3), 1469-1484.
- Fuks, L., & Sundberg, J. (1999). Blowing pressures in bassoon, clarinet, oboe and saxophone. *Acustica / Acta
  Acustica* 85, 267-277.
- Gabrielsson, A., & Juslin, P. N. (1996). Emotional expression in music performance. *Psychology of Music* 24(1),
  68-91.
- Galamian, I. (1962). *Principles of Violin Playing and Teaching*. Prentice-Hall.
- Geringer, J. M., & Allen, M. L. (2004). An analysis of vibrato among high school and university violin and cello
  students. *Journal of Research in Music Education* 52(2), 167-178.
- Geringer, J. M., MacLeod, R. B., & Allen, M. L. (2010). Perceived pitch of violin and cello vibrato tones among
  music majors. *Journal of Research in Music Education* 57(4), 351-363.
- Gleiser, J., & Friberg, A. (2003). Vibrato rate and extent in violin performance. *Proceedings of SMAC 03*.
- Gordon, J. W. (1987). The perceptual attack time of musical tones. *JASA* 82(1), 88-105.
- Hennig, H., et al. (2011). The nature and perception of fluctuations in human musical rhythms. *PLoS ONE* 6(10).
- Keller, P. E. (2008). Joint action in music performance. In F. Morganti et al. (Eds.), *Enacting
  Intersubjectivity*. IOS Press.
- Luce, D., & Clark, M. (1967). Physical correlates of brass-instrument tones. *JASA* 42(6), 1232-1243.
- Palmer, C. (1996). On the assignment of structure in music performance. *Music Perception* 14(1), 23-56.
- Prame, E. (1997). Vibrato extent and intonation in professional Western lyric singing. *JASA* 102(1), 616-621.
- Quantz, J. J. (1752). *Versuch einer Anweisung die Flöte traversiere zu spielen*. Berlin.
- Rasch, R. A. (1979). Synchronization in performed ensemble music. *Acustica* 43, 121-131.
- Rasch, R. A. (1988). Timing and synchronization in ensemble performance. In J. Sloboda (Ed.), *Generative
  Processes in Music*. Oxford.
- Repp, B. H. (1997). Acoustics, perception, and production of legato articulation on a computer-controlled grand
  piano. *JASA* 102(3), 1878-1890.
- Rimsky-Korsakov, N. (1913). *Principles of Orchestration*. Édition russe de musique.
- Seashore, C. E. (1938). *Psychology of Music*. McGraw-Hill.
- Sundberg, J., Friberg, A., & Frydén, L. (1991). Common secrets of musicians and listeners. In *Representing
  Musical Structure*. Academic Press.
- Todd, N. P. M. (1992). The dynamics of dynamics: a model of musical expression. *JASA* 91(6), 3540-3550.
- Vos, J., & Rasch, R. (1981). The perceptual onset of musical tones. *Perception & Psychophysics* 29(4), 323-335.
- Wing, A. M., Endo, S., Bradbury, A., & Vorberg, D. (2014). Optimal feedback correction in string quartet
  synchronization. *Journal of the Royal Society Interface* 11(93), 20131125.
