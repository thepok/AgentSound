# The endless orchestra

`python -m agentsound endless orchestra-film [--mood M] [--count N | --hours H --join] [--candidates N]` writes
orchestral pieces without an LLM: a composed lead sheet becomes a polyphonic SCORE of lines with musical FUNCTIONS,
an ORCHESTRATOR assigns the functions to the sections of the orchestra by data tables, and the orchestral player
(`orch.Score` / `orch.perform`, docs/ORCHESTRA_RULES.md) plays them on the `film_orchestra` band. The first style is
new-age / lyrical film orchestral. The design goal is that the hardest orchestral genres plug in later without a
rewrite: every stage is one shared component with its own vocabulary as data.

This document was written before the code (the design) and is kept as the reference for how the parts fit and how
each harder genre plugs in (the roadmap, last section); the names below are the built ones, "Results" has what the
first run measured.

## The pipeline

```
 Tune (endless.composer: the lead sheet)           a later composer (counterpoint, fugue, development ...)
      |                                                       |
      v  COMPOSER  (endless/orchestra.py: lines_from_block)   v  writes lines directly
 OrchScore  ---  blocks (sections) x Lines(function, notes)  ---  ONE representation
      |
      v  ORCHESTRATOR  (bandlib/orchestration.py: orchestrate)
 Orchestration  ---  {role: parts (notes, articulation, offset, line?)} + the decisions made
      |                driven by: TEXTURES (orchestration plans), RULES (budgets / distributions),
      |                           orch.ROLE_TRAITS + band.info range / sweet spot (the instrument table)
      v  PLAYER  (orch.Score -> orch.perform, ensemble rules, style 'film' | 'romantic' | 'classical' | 'baroque')
 Song (one track per SECTION of the orchestra, not per player) -> render, gate, score
```

All decisions above the notes are drawn through the endless `Dice` into the `Arrangement` record (kind
`'orchestra'`), so they replay and are tokenizable for the learned student.

## 1. The score representation (`agentsound/bandlib/orchestration.py`: `OrchScore`, `Block`, `Line`)

Instrument-independent, composer-independent:

- `OrchScore(title, key, meter, tempo)`: an ordered list of `Block`s (a section of the piece: name, start, length in
  beats, its chord timeline `[(start, beats, symbol)]`, its key, its dynamics marks, `peak` / `frame` flags, the
  texture the orchestrator will use) and per block its `Line`s.
- `Line(function, notes, voice='', of=None, art=None, meta={})`: one musical line, `notes` = `(start, dur, pitch)`
  in song beats with concrete pitches in a natural register (the orchestrator may move a line by octaves to fit an
  instrument, never re-compose it). A line may hold simultaneous notes (a chord stream), but real parts are the rule:
  the harmony is written as voice-led voices `h1` (top) .. `hN`.
- FUNCTIONS (data, `orchestration.FUNCTIONS`): `melody`, `counter` (a counter-melody), `harmony` (sustained chord
  voices: the pad), `inner` (moving inner voices), `bass`, `ostinato` (a rhythmic repeated figure), `colour`
  (figuration / sparkle: harp arpeggios, flute arabesques, tremolo shimmer), `pedal` (a held pedal point),
  `voice` (an equal contrapuntal voice: fugue / canon / invention - for the later composers) and `doubling`
  (written by the orchestrator: `of` names the line it doubles). Each function has a balance rank (its velocity
  offset under the melody) and a default articulation.

The first composer (`endless/orchestra.py: lines_from_block`, per block) fills it from the new-age lead sheet: the
sections the
new-age pianist's plan draws (`perform._piano_plan`: layout, variations, the lifted / grown climax, key changes,
returns) become blocks; per block it writes only the functions the block's drawn texture needs - the melody, the
harmony (voicing.voice over the chart, under the melody - over it when the lead is a tenor role, `HARMONY_HIGH` -,
spacing rules), the bass (organ_vocab.bass_line, walking
where the plan says so), a counter-melody (organ_vocab.counterline against melody and bass, thinned to long notes
where the melody moves and moving where it holds), an ostinato (`OSTINATO`: a rocking / arpeggiated / pulsing
string figure, drawn) or a colour figure (`HARP` figures drawn per block, timpani rolls on a chord tone, the cymbal
roll into the crash, the choir on the harmony's parts).
Shared primitives only - no parallel technique.

## 2. The orchestrator (`bandlib/orchestration.py: orchestrate`, data in the owning tools)

- **The instrument table** is the band's own data: `band.info['range']` / `['sweet']` (bandlib/orchestra.py role
  tables) plus `orch.ROLE_TRAITS` (bandlib/orchestra.py): per role its family, agility (fast notes), power (how much
  it adds in a tutti), the functions it is good at `{function: weight}`, its doubling partners and whether it
  breathes. A new instrument = a row there.
- **Orchestration plans** (`orchestration.TEXTURES`): a texture type is a dict `{function: slot}` - the roles that
  carry the function (`pick` one by weight, or a fixed `voices` list for real parts / divisi), its articulation, its
  doublings `{role: (interval, weight)}`, a `tutti` / `peak` flag, the size it needs. The film / new-age vocabulary:
  `strings_pad` (a hushed string pad, a solo above it), `solo_pad` (a wind / horn / cello solo over strings), `harp_solo`
  (a solo over harp arpeggios and a horn pad), `strings_melody` (violins sing, violas / cellos / horns hold the
  harmony), `cello_theme`, `chorale_winds` (a woodwind choir), `horn_ostinato` (strings drive in 8ths, the horns carry
  the tune), `counter_strings` (the theme with a cello / horn counter-melody), `tutti` and `tutti_lyrical` (the
  climax: violins in octaves + flutes on top + horns, brass harmony, timpani, choir).
- **Rules as budgets / distributions** (`orchestration.RULES`): every role stays in its range (lines move by octaves
  as a whole phrase toward the sweet spot; a note still outside is folded and counted); spacing - close in the
  treble, wide in the bass (the harmony's adjacent upper voices within an octave, no third under C3); doublings by
  register (a melody above E5 doubles an octave down, below A4 an octave up; the basses double the cellos an octave
  down); a melody balance budget (velocity offsets per function, then the Score's BALANCE rule); a colour change at
  section boundaries (the melody's instrument differs from the block before with the plan's probability); the tutti
  reserved for the peak blocks (a tutti-share budget); the coda thins (at most N roles).
- **Per section the orchestration plan is drawn** from the genre's `{texture: weight}` for that section (the plan
  entry's `orch` key), then the roles per function (`lead`, `counter`, `colour` picks), all through the Dice.

## 3. The arrangement record (`endless/arrangement.py`, kind `'orchestra'`)

The orchestra record is the piano record (layout, the sections played and their drawn keys - the same composer
draws) plus the orchestrator's decisions: piece `size` ('chamber' | 'full'), per section `texture`, `lead` (the
melody's role), `counter` (the counter-melody's role, or 'none') - `orchestra.RECORDED`. The colour roles and the
doublings are seeded draws below them (they replay with the record; a later student may record them too). The
learned student's token schema (learn/tokens.py) has the prefixes `ASize`, `ATex`, `ALead`, `ACtr` appended to the
Arr block's field order (`PLAN_KINDS` = piano, orchestra): schema 2 unchanged, a piano / jazz genre's vocabulary
unchanged, old checkpoints still sample (tests/python/test_endless_orchestra.py round-trips the tokens).

## 4. The player

`orch.Score(song, band, marks, style=genre.band['style'])` - the dynamics map from the sections' marks and phrase
hairpins, the parts added per role (the melody and its doublings as LINES, so the balance rule keeps the accompaniment
under them), `perform()`: articulation, legato, bowing, breathing, brass entries, releases, ensemble timing, the
dynamics lane. The style parameter (`film` default; `romantic`, `classical`, `baroque`) comes from the genre. The
tempo plan is the piano genre's: section tempi, ritardandi, fermatas, an inhale before the peak.

Tracks: one per section of the orchestra (violins1 .. tuba, harp, timpani, percussion, choir). The band is built
by `endless.orchestra.band(song, roles)` - the genre's master chain (`master/film-lyrical`: eq, a slow ride, the
limiter), `gain` on every role, the `trims` - with `without=` every role the piece does not use: a chamber piece
renders ~10 tracks, a full one ~16. The hand-written references call the same function. Lines get at least the
genre's `line_phrasing` arc; held notes follow the hairpins (`perform(follow=True)`).

## 5. The genre (`endless/genres.py: ORCHESTRA_FILM`)

`orchestra-film`: the new-age composer's data (cells, phrase plans, harmony, set draws) with orchestral moods
(hopeful, longing, epic, pastoral, night), the film_orchestra band, `plan['perform'] = 'orchestra'`, the new-age
section plan with an `orch` texture weight table per section, sizes per mood (`plan['sizes']`).

## 6. The score (`genres.SCORES['orchestra']`, `endless/orchestra.py: orchestra_metrics`)

Two parts, one table:
- the melodic / harmonic layer: the new-age composer metrics measured on the score's REDUCTION (the melody line as
  the right hand, everything else as the left) - the same `composer.score_metrics` code;
- the orchestration metrics measured on the performed parts (`orchestration.metrics`): range violations (hard: 0),
  melody notes in the sweet spot, spacing faults, low thirds, the melody's margin over the accompaniment, colour
  changes per boundary, the tutti share, the coda's thinning, roles per bar, doubling sanity, the climax place,
  the loudness range in note energy.
References: hand-composed pieces in this style (songs/pro-orch-*, written blind on the same band) set the ranges.

## 7. Render time

Measured per tune in the endless log (`N s in M s (compose, render)`) and summed in ROUNDS.md "Orchestra".

## Results of the first run (2026-10-13; songs/_blind/ROUNDS.md "Orchestra")

- Four references (songs/pro-orch-hopeful / longing / epic / night) set the orchestration ranges; the endless pieces
  now double like them (dbl_share 0.73) but stay flatter in density (roles_sd 1.8 against 2.4-3.7, db_bar_sd 5.5
  against 8-10 dB) - the next orchestration work.
- Blind rounds: r1 80 % (composers 100 %, the statistician inverted), r2 100 %. The orchestration tells of r1 were
  fixed (doublings from the placed line, octave stacks, harmony over a tenor tune, harp figures, timpani on chord
  tones); r2's tells are mostly the shared new-age composer's (neighbour-cell melodies, off-beat phrase starts, the
  2-bar interlude, pasted chromatic chords) and new accompaniment templates. TODO.md "Endless orchestra" lists them.
- Render time ~0.12-0.20 min per minute of music (alone), 0.28 min per minute for a best-of-4 set including the
  candidates and the gate's rerolls; set 1: 22.5 min in 6:22.

## Roadmap: how the harder genres plug in

| genre | composer (writes lines into OrchScore) | orchestration plans (TEXTURES / RULES rows) | player |
|---|---|---|---|
| romantic symphony (Brahms, Dvorak, Tchaikovsky) | a symphonic composer: themes in periods with sentence structure, a second theme in the dominant / relative, transitions; the lead-sheet composer's `classical` data as the start | `tutti_romantic` (strings in octaves, woodwinds doubling, horns sustaining), `winds_answer` (dialogue between violins and woodwinds), divisi string pads; rules: brass one dynamic under the strings, the timpani on tonic / dominant | style `romantic` (1.2 swell, rubato, phrasing) |
| symphonic development | a developer that transforms a motif (fragment, sequence, invert, augment, modulate: the motifs `patterns.Motif.head / fragment`, the composer's `_vary` kinds) and writes `voice` / `melody` lines block by block with key plans | `fragmented` (the motif passed between sections: the lead role changes per 2 bars), `stretto_tutti` | `romantic` / `classical` |
| fugue | `organ_vocab.fugue` / `voicing.fugue` write subject, answer, countersubject and free voices as `voice` lines into the blocks (exposition, episodes, stretto) | `fugue_strings`, `fugue_winds`, `fugue_tutti`: a voice per role, the orchestrator only fits ranges and adds octave doublings in the tutti; rule: each entry's role keeps its colour | `baroque` (terraced dynamics) or `classical` |
| Debussy / Ravel colour | a colour composer: planing (`organ_vocab.planing`), whole-tone / pentatonic / modal harmony vocabularies (`Genre.harmony`), arabesque `colour` lines | `flute_harp`, `muted_strings`, `celesta_glock`, harmonics / tremolo pads; the instrument table's muted brass and solo roles (sampled_sections / sampled_orchestra patches through `sounds=`) | `romantic` with less swell; the symphony band (celesta) |
| late-romantic film score | the lyrical composer with chromatic mediants / lydian (harmony data), leitmotif transformation per scene | `brass_chorale`, `horn_call`, `choir_tutti`, `ostinato_epic` (hybrid: the film band's pulse / sub roles) | `film` / `romantic` |

What never changes: the representation (new functions are rows in FUNCTIONS), the orchestrator (new texture types are
rows in TEXTURES, new instruments rows in ROLE_TRAITS), the player (orch.Score), the record (new keys are new token
prefixes), the runner, the gate and the blind-round method.
