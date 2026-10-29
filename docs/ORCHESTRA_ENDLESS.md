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

## The symphonic composer (`endless/symphony.py`, genre `orchestra-symphonic`, 2026-10-16)

This is the first roadmap row built, the romantic symphony with symphonic development. HUMAN_FEEDBACK 2026-10-16 asked
for it: the film pieces were "very meditative, hardly anything happens". It is its own composer layer, not the
new-age tune orchestrated. It writes lines straight into the shared `OrchScore`, and the orchestrator, the player,
the record, the runner and the gate are unchanged.

What `endless/symphony.py` does:

- **The form.** The material is a row of blocks from `plan['layouts']`. Each block has a kind, and each kind has its
  writer:
  - opening: `intro` (the motto as a call), `mist`, `source`;
  - exposition: `t1` / `t1b` (a sentence), `trans` (the kernel sequenced), `t2` / `t2b` (a cantilena period in the
    second key), `close`;
  - the river's `river` / `episode`;
  - development: `dev_dialogue` (a 2-bar call-and-response model through a key path), `dev_fugato` (four entries
    with a counter-subject);
  - `retrans` (the kernel liquidated over a dominant pedal);
  - `recap` (the climax);
  - coda: `coda` / `coda_soft`, then `end` / `end_soft`.
- **The motto.** The piece draws a rhythm cell (`CELLS`), its landing step, its chord member and the answer through
  `plan['set']` (`composer.set_draws`). It is stated through `motto_notes` transforms: invert, augment, diminish,
  head, kernel and chordal. A guard keeps out the famous knock: three repeated notes and a third.
- **Melody-first harmony.** `harmonize` runs a DP over bars or half bars (fit + NEXT + priors + forced cadences).
  `fit_line` then snaps clashes, and `_mono` turns every theme into one line.
- **The accompaniment.** The texture's slots name a figure: drive (pulse / rock / the motto's rhythm), arp, pump,
  pluck, wave or run figuration, the motto in the timpani, a long roll or a cymbal swell.

What the shared modules got (hooks, not forks; the piano and film genres stay bit-identical):

- `orch.TEXTURES` has symphonic rows (`orch.SYMPHONIC`).
- The new function `figuration`.
- Slot keys `enter` / `leave` (`_window`): a role or a doubling plays from or until a drawn share of the block,
  snapped to a bar.
- The texture key `theme: 'bass'` (the motto in the low strings).
- `Part.sf` (sforzandi on the theme's long notes).
- Tuple-safe marks (subito steps).
- `RULES['bass_floor']`: the bass's octave doubling under C3. The symphony turns it off; film keeps it.

The genre has these axes:

- Feels: allegro 4/4, vivace 6/8, scherzo 3/4 (scale 2), river 6/8 and andante.
- Seven moods.
- Layouts: sonata, fugal, compact and journey.
- Best-of-4 by the PROVISIONAL `SCORES['symphony']`.

Measured on the four pieces of blind round q1 (the notes, then the rendered audio):

| | orchestra-film q1 (4) | symphonic q1 (4) | pro-orch references (4) |
|---|---|---|---|
| tempo (BPM) | 58-98 | 100-143 | 62-80 |
| notes per second | 1.2-2.2 | 3.5-4.4 | 1.5-2.1 |
| running share | 0-0.004 | 0.84-0.97 | 0.07-0.34 |
| motto statements / transforms / roles / in the bass | - | 42-70 / 6-7 / 8-11 / 6-10 | - |
| roles_sd | 1.1-2.0 | 2.0-2.8 | 2.4-3.7 |
| db_bar_sd (dB) | 5.5-6.3 | 7.2-11.4 | 7.9-10.0 |
| tutti share | 0-0.19 | 0.06-0.29 | 0.15-0.27 |
| LRA (LU) | 9.3-12.8 | 9.3-11.1 | 11.5-12.6 |

The blind round q1 (songs/_blind/ROUNDS.md "Orchestra") rated the symphonic pieces overall 6.57, against 5.19 for
orchestra-film and 5.96 for the lyrical references. On life the gap is 7.29 against 4.26, on development 6.86
against 4.78. So `endless orchestra` now means the symphonic genre. Its open ends are in TODO.md "Endless orchestra".

### Round o2: set diversity, idiom, repair (branch only: no paired win)

What round o2 added:

- **Set variety.** The symphonic arc rolls feel dice (`feel_noise` 0.35, `feel_max` 2, `tempo_spread` 0.4: optional
  set-arc keys only this genre uses). Journey and mysterious may be dorian.
- **Draws per set:**
  - a climax type (`symphony.CLIMAXES`: brass, an apotheosis in the strings, a tutti chorale, a quiet climax);
  - a pre-climax build (`BUILDS`: tremolo or pulse);
  - an orchestra size (full or chamber).
  The mood weights gate all three.
- **Idiom.** Trombones stay at or below Bb4 and bassoons at or below C5, and the brass gets no runs. Themes lose
  their two-note shakes.
- **Sampler.** The sampler's `repair` (dB) bridges the edit-splice glitches in SSO sustain files at load. It keeps
  the loop points, and the symphony uses 9 dB.
- **References.** Three hand-made references: `songs/pro-orch-symphonic-stormy`, `-river` and `-scherzo`.

Over three 8-piece sets, the features that one value holds in 5 or more of the 8 pieces dropped from 5 to 2 (of 12).
The texture Jaccard between pieces dropped from 0.43 to 0.33. Gate rejects dropped from about 40 % to 11 %.

The paired blind round, with 8 slots on one plan and split panels of 7 judges, put the new code against master at
-0.09 overall (se 0.17), with 3 of 8 slots won. The judges still flag one template: 51.6 template flags per packet
against 39.1 for master. They hear it in the timpani-pedal build, a development that does not use the motto, a
climax that is the theme in octaves, and the shared flute-thirds and oboe-over-harp textures. These shared
textures are the next fixes (TODO.md).

### Round o3: the material - development, builds, climax (branch only: no paired win)

Round o3 worked inside the plan: the material the o2 judges heard as one template. Everything sits in the owning
tables of `endless/symphony.py` and `bandlib/orchestration.py`, drawn per piece through `plan['set']` with
set_memory:

- **The development works the motto.** `Writer.develop` replaces the generic dialogue with a drawn technique
  (`DEV_TECH`): the motto sequenced through the key path, fragmented down to its kernel, in stretto, against the
  second theme (`combine`), or in the bass under the strings. The fugato's subject tail is the kernel sequenced, and
  its counter-subject is the motto (plain or inverted, anchored near home).
- **Builds from the piece's material** (`BUILDS`): motto stretto, brass calls answered closer and closer, a bass
  pedal carrying the motto, subito pp then crescendo, a fugato that thickens, tremolo or pulse. The long timpani
  roll is kept only at the end of the tremolo build.
- **A transformed climax** (`APEX`): the theme augmented under running figures, motto and theme combined,
  reharmonised in a new key, or the second theme as apotheosis. A minor piece may end in the tonic major.
  `RULES['reserve']` keeps the top register for the peak: earlier lines that reach the peak's top note move or fold
  down an octave.
- **Material draws:** the opening source (`SOURCES`), the second theme's colour (`T2_COLOURS`), the accompaniment
  figure (`ACCOMPANIMENTS`), the ending (`ENDINGS`) and `derive` (the second theme's head from the motto's contour).
- **Mottos with character** (`MOTTO_CHARACTER`): a leap of a fourth or more, one peak, at most one repeated note,
  span within an octave, plus new cells. **Range floors** (`ROLE_TRAITS` 'bottom').
- `songs/_blind/tells_orch.py` measures the judges' tells on any code version without audio.

On 24 pieces the stock roll fell from 1 to 0 and the climax-as-theme share from 0.76 to 0.21. The top register spent
early fell from 0.71 to 0, the range slips from 36 per piece to 0, and the mottos with character rose from 0.63 to 1.
The paired round (7 slots; master's slot 8 never passed the gate) came out at +0.08 overall (se 0.38). Development
(+0.27) and harmony (+0.31) lean new, life (-0.18) and form (-0.12) lean old. Template flags per packet: new 37.7,
old 38.0.

The judges now hear the **block row**: one section plan for every piece, recapitulations copied from the
exposition, and the dominant pedal with a rising line before the climax. The next fixes are in TODO.md.

### Round o4: form, recapitulation, builds, tunes, idiom (on the o3 branch)

Round o4 builds on o3 and fixes the o3 judges' tells, again in the owning tables of `endless/symphony.py` and
`endless/genres.py`, drawn per piece through `plan['set']`:

- **Forms.** `_SYM_LAYOUTS` adds rondo (A-B-A-C-A), variations, ternary, arch, through-composed, a false
  recapitulation, scherzo + trio and a journey with variations. Each feel lists the `layouts` it allows, and the set
  draws one (set_memory 3). `draws['phrase'] == 'free'` draws the block lengths from `PHRASES` (6 / 10 / 12-bar
  phrases, total capped at `PHRASE_CAP`), and one block of `ELIDE` is elided by a bar.
- **Recapitulations recomposed.** The restated recap is reharmonised and dotted (`RECAP_VARY`) with the second theme
  under it (`Writer.theme_under`). recap2 brings the second theme back changed (`cantilena(vary=True)`, its answer a
  motto counter-line). The apex forms combine a varied sentence with the theme. The new kinds are refrain, trio and
  `var` (`Writer.variation`: ornamented, in the bass, minore, canon, march, chorale).
- **Build frames** (`BUILD_FRAMES`, drawn): the dominant pedal, a bass ascent, a circle of fifths, or a lament bass
  descending, with slash chords. The bass build keeps the pedal.
- **Second themes as tunes.** The cantilena is a period: a head cell of 3+ notes (a leap, then steps), an answer
  phrase in the head's rhythm, one high point, and lengths of 6 / 10 / 12 bars via `stretch`. `sentence` can vary
  (invert, reharm, dot). New LYRIC cells.
- **Figuration.** A run turns at the range edge instead of folding an octave, scales continue from the last note,
  and `_reserve` turns notes under the top. The ostinato changes its figure every 4-8 bars (`OSTINATO_VARY`).
- **Idiom** (`IDIOM`, `_orchestra_pass`): the timpani are tuned per block to tonic / dominant (F2-E3), violas above
  the violins move down an octave, a chamber climax without horns gets horn harmony, and the flute's top is A6.
- **Dynamics.** Melody / counter / doubling lines outside the motto statements arc per two bars (`SHAPE['phrase']`).
  A loud part's shape moves under `SHAPE['ceiling']`, and sforzandi fall only on a theme's arrivals (one a bar).
  Before this, a recap of half notes was all sforzandi, and its doubling sat at 127, a flat_dynamics reject.

Measured with `songs/_blind/tells_orch.py` (24 pieces, master / o3 / o4):

- **Form:** mod48 (4 / 8 / 16-bar blocks) 0.88 / 0.79 / 0.57; pairs with the same macro form 0.25 / 0.27 / 0.06;
  row similarity 0.65 / 0.65 / 0.52.
- **Recap:** recap melody copies 0.37 / 0.42 / 0.16; second theme copied on return 0.83 / 0.77 / 0.43.
- **Builds:** the pedal-build frame 1.0 / 0.75 / 0.29.
- **Second themes:** second themes as tunes 0.08 / 0.21 / 0.88.
- **Figuration:** folds 2.1 / 2.5 / 0.9; longest unchanged ostinato 7 / 5.9 / 3.7 bars.
- **Orchestration:** violas over the violins 11 / 19 / 0.25; timpani off 5.1 / 4.4 / 0; flute at B6+ 1.25 / 0.46 / 0.
- **Score:** 97.7 / 95.1 / 94.0.

The gate check (8 slots, 1 candidate, 4 tries) has 1 reject in 9 renders.

The paired round (8 slots, seed 99000, 14 judges) came out at +0.14 overall (se 0.24), with 5 slots won and 3 lost.
Melody (+0.32) and development (+0.30) lean new; form (-0.18) and orchestration (-0.16) lean old. That is not a clear
win, so the code is not merged. Template flags per packet fell to 17.5 (master 42.0). The judges no longer hear
one block row: they hear master's recipe. Master lost slot 5 in 7 of 8 candidates to the gate. The next tells
(TODO.md) are:

- thin middles and held-note themes
- figuration that does not follow the harmony
- bare-unison endings
- the melody under the harp
- tutti climaxes doubled on one line

### Round o5: dance, chord figuration, voiced endings, audible melody, brass range (on master = o2 + o3 + o4)

Round o5 fixes the o4 judges' tells in the owning tables (`endless/symphony.py`, `bandlib/orchestration.py`,
`bandlib/orchestra.py`, `endless/genres.py`). Everything sits under the symphonic gate (`RULES['idiom']` or the
symphonic writer), so film and the piano genres stay bit-identical.

- **The scherzo's tune** (`DANCE`, `Writer.dance`): `sentence` at scale 2 writes a 3/4 dance. It has a basic idea on
  the motto's contour in dance cells (`idea` / `land`), its answer, a fragment sequenced by steps, and a cadence run
  falling from a dominant chord tone into the goal. The trio's cantilena is re-rhythmed per bar with `DANCE['lyric']`
  cells. The scherzo's bass is a pump (downbeat + beat 3), not a 6/8 gallop.
- **Figuration from the chords** (`figuration`, `RUN_FIGURES`): 'c' figures (arch, broken, climb, leap) walk a ladder
  of chord tones. 's' figures are scale runs whose strong positions are chord tones, so passing tones fall on the
  weak ones. The figure re-snaps at every chord change, continues from its last note, and turns toward the range
  when it reaches an edge.
- **Voiced endings** (`ENDINGS` cadence / strokes / motto / held / plagal, `ENDING_CADENCE`, `STROKES`,
  `SOFT_ENDINGS`; textures `end_cadence` / `end_strokes` / `end_motto` / `end_held`). The end block is a V7-I (or
  IV-I) cadence voiced over four harmony voices, an inner choir and the bass. Its soprano lands on the tonic, the
  fermata and the ring fall on the tonic chord, and 'strokes' cut the approach bar into tutti strokes. The draw has
  set_memory 2.
- **An audible melody** (`AUDIBLE`, `_audible`, run first in `_orchestra_pass`): under a high lead, accompaniment
  notes at or above the melody note move down. The harp moves by octaves, or the note is dropped. The other parts
  move as a whole part when that fits, otherwise note by note. Climax and cantabile textures get `counter` slots
  (cellos / horns / violas), and `apotheosis_strings` no longer doubles the line in three octaves.
- **The 6/8 family's codas and openings**: `CODA_PLANS` (triumph: stretto / pedal / hymn; dissolve: descent / echo
  / memory) are drawn per piece (`coda_plan`, set_memory 2). The river's source block draws its chart
  (`SOURCE_CHARTS` plagal / circle / pedal), its melody's entry (`SOURCE_ENTRIES` late / early / answer) and its
  length (`PHRASES['source']`).
- **Brass range**: ROLE_TRAITS `'tune': 'G4'` for the trumpets. Under the idiom, `_tune_ok` gives a melody or
  counter-line to another of the slot's roles when it falls under the role's tune floor or does not fit the role's
  range whole. Doublings under the floor are skipped. The melody's own role is never windowed by a slot's `enter`.

Measured with `songs/_blind/tells_orch.py` (`measure_o5`; 24 pieces, master (= o4) / o5):

- **Scherzo:** held-bar share in the scherzo's themes 0.43 / 0.20. Melody bars carried by one line 0.24 / 0.20.
- **Figuration:** off-chord strong positions 0.34 / 0.04. Beats circling inside a third 0.31 / 0.34 (unchanged; high in the
  river pieces).
- **Endings:** final-chord pitch classes 2.5 / 3.0; bare endings 0.25 / 0.04; approached from V / IV 0 / 1.
- **Balance:** melody notes under the accompaniment's top 0.22 / 0.02; harp over the melody 0.04 / 0.005; climaxes
  with a counter-line 0.33 / 0.79.
- **Brass:** trumpet tune notes under G4 per piece 4.0 / 0.
- **The 6/8 family:** pairs with the same coda plan 0.18 / 0.03, the same opening 0.09 / 0.11, the same ending 0.18
  / 0.12.
- **Score:** 94.0 / 93.5.

The paired round (8 slots, seed 101000, 2 chamber slots, a scherzo and four 6/8 pieces, 14 judges) came out at
+0.39 overall (se 0.29), with 4 slots won, 1 tied and 3 lost. Every dimension leans new: development +0.60, harmony
+0.49, form +0.35, melody +0.29. That misses the clear-win bar, but it is the second lean in a row after o4's +0.14,
which the brief counts: recommended for merge. The best piece is RXEZ, a B minor through-composed andante, at 7.1.
The worst is the scherzo, whose t1 drew `motto_bass`: violins1 arpeggiates over the dance tune in the bass. The next
tells (TODO.md, ROUNDS.md "Round o5") are:

- climaxes bring new material instead of the motto
- the scherzo's tune is under the figuration
- episodes are not built from the motto
- repeated-note wind accompaniment
- the shared minor-to-major harp apotheosis plan

### Round o6: the climax from the piece's material, the development on the theme, the climax's key per set

Round o6 fixes the o5 judges' tells in the owning tables (`endless/symphony.py`, `bandlib/orchestration.py`,
`endless/genres.py`). All of it is symphonic-only (24 of 24 protected hashes bit-identical).

- **The climax from the piece's own material** (`APEX`, `Writer.apex`):
  - 'combine' puts the motto on top (plain statements over two bars, then diminished ones) with the second theme
    under it as the counter-line (`theme_under`). Its texture `apex_combine` gives the line to violins1 + trumpets
    and the counter to cellos / horns / violas.
  - 'theme_aug' is new: the first theme augmented into the climax's key.
  - 'augment' gives the motto to the trumpets (horns 0.3) over a viola / horn counter.
  - The apotheosis texture has a spiccato run instead of the harp arpeggio (harp chance 0.3).
- **The climax's key per set** (`CLX_MODES` home / picardy / parallel / relative, `clx_keys`, draw `clx_mode` with
  set_memory 2): a minor piece's climax stays minor, turns to the relative major, or turns to the parallel major. With
  'picardy' only the last chord turns. The recap2 after the peak takes the coda's key.
- **The second theme is one tune in either mode** (`Writer.tmode`): every statement of a theme sings the skeleton
  of its first statement's mode. o5 drew the other mode's skeleton, which made a new hymn at the climax. The
  derived themes (B / C / R) apply too.
- **The development on the first theme** (`DEV_TECH['theme']`): two-bar models from the first theme's opening,
  transposed by the model anchors. The counter imitates an octave below a bar later, then half a bar later. The
  second half shortens to the first bar plus a copy a step up, and the last model liquidates into kernels.
  'sequence' states the whole motto only in its first half, then the head.
- **The scherzo's tune on top** (`SCHERZO_TEX`): the scherzo's theme blocks never draw `motto_bass` /
  `running_strings` (the tune in the bass under violin arpeggios); they get `tutti_drive` / `drive_strings` instead.
- **Filler**:
  - The river's wave figuration was stuck on one repeated note (`p_first` was never cleared). It now moves, with
    a direction tie-break.
  - The flutes' river figuration leaves the texture after half to three quarters of the block.
  - The `close` kind no longer draws `motto_unison` (the full-orchestra unison scale).
- **Set variety**:
  - The coda draw has set_memory 1.
  - `end_soft` draws dissolve / chorale_winds / strings_pad.
  - The timpani rolls at the end are chance 0.4-0.6.
  - The slow intro draws 3 or 4 bars (`SLOW['bars']`), the call 3 / 4 / 6 (`PHRASES['intro']`).

Measured with `songs/_blind/tells_orch.py` (`measure_o6`; 24 pieces, sets 96000 / 96100 / 96200, master / o6;
the references from `tells_orch.py ROOT --refs`):

- **Climax:** climax melody windows matching the motto 0.25 / 0.50; matching any own material 0.50 / 0.60; climaxes with a counter-line 0.79 / 0.92;
  climaxes with harp arpeggios 0.29 / 0.08.
- **Development:** development / episode bars with own material 0.77 / 0.79 (the references 0.84); with the motto 0.65 / 0.69.
- **Scherzo:** scherzo theme bars whose tune is under another line 0.44 / 0.02.
- **Filler:** the longest woodwind run of repeated-note bars 1.0 / 0 bars per piece; body bars with 5+ roles in one
  unison line 0.79 / 0.54 per piece; beats circling inside a third 0.34 / 0.07.
- **Set plan:** pairs with the same climax-mode / coda / ending plan 0.05 / 0.01; the same climax turn 0.23 / 0.13; the same 6/8
  opening 0.11 / 0.11; the same ending 0.12 / 0.21 (worse: fewer ending types survive the voiced endings).
- **Score:** 93.5 / 93.0.

The paired round (8 slots, seed 103200, three chamber slots, a scherzo, two 6/8 vivaces and two rivers, 14
judges) came out at +0.00 overall (se 0.17), 4 slots won and 4 lost.

- Development +0.16 and life +0.21 lean new; melody -0.11 and memorable -0.14 lean old.
- No bar is met and there is no second lean: **not merged**.
- The best piece is GKJW, an Eb andante with a false recap, at 6.7, over the river reference.
- The worst is the new scherzo. Its 'combine' climax states the motto plainly over two internal bars, which in 3/4
  at scale 2 is one note per bar: the dance tune comes back in whole-bar notes.

The next tells (TODO.md, ROUNDS.md "Round o6"):

- the scherzo's climax at its own speed
- the voiced endings' layout (the root in the bass instruments, no trombone / bassoon on top, no bass-less
  dominant)
- octave-unison tutti climaxes
- repeated-note inner strings
- the stock cymbal / choir build

### Round o7: the scherzo's climax, voice-led endings, climaxes in colours, moving inner parts (on the o6 branch)

Round o7 fixes the o6 judges' tells in the owning tables (`endless/symphony.py`, `bandlib/orchestration.py`,
`endless/genres.py`). It is symphonic-only (24 of 24 protected hashes bit-identical), with one infra fix in
`bandlib/orchestra.lead`.

- **The scherzo's climax** (`APEX_SCHERZO`): at scale 2 (the 3/4 scherzo), 'augment' becomes 'combine' and
  'theme_aug' becomes 'reharm'. `Writer.apex` writes 'combine' as the dance tune itself, a PAC phrase a third
  higher, over the second theme as the counter. The triumph coda's motto statements are diminished (one per song
  bar, rising a step every second), and the hymn / memory are not augmented.
- **Voice-led endings**:
  - `_approach` writes the bars before the last chord per `ENDING_CADENCE`: cad64 (I6/4 - V7, the top 3-2), pre
    (IV - V7, 1-7), plagal IV, or a tonic pedal under IV (4-3).
  - `_resolve` voice-leads the final chord from the chord before it. Over V7 the leading tone rises and the seventh
    falls to the third. Every other voice takes the nearest chord tone in range, the doubled third is penalised, and
    the third is always present.
  - `END_VOICING` gives the end blocks' harmony and inner ranges, so the tune sits on top in violins / flutes and
    the dominant keeps its bass.
  - The end textures list their harmony voices in score order: violins2, clarinets, violas, horns.
  - The soft ending follows the loud one (`SOFT_OF`) or is drawn (`SOFT_ENDINGS`), and the ending draw has
    set_memory 3.
- **The climax in colours**: `tutti_symphonic`, `apex_augment`, `apex_combine`, `apotheosis_strings`,
  `tutti_chorale` and `hammer` give the line to violins1 or trumpets with chance doublings (flutes an octave up,
  oboes, violins2 an octave down). The brass take the harmony and another choir the counter-line. apex_augment has
  no inner slot (it folded).
- **Moving inner parts** (`INNER_MOTION`, `_move_inner`):
  - suspensions into the chord change
  - held notes of 3+ beats alternate with the next chord tone
  - passing tones on the last beat across thirds
  The bass of coda / end / close / recap blocks and of the non-unison blocks with a melody plays the theme's rhythm
  on the chord roots (`_bass_in_rhythm`), not the octave unison. The unison kinds (intro / mist / solo / slow) keep
  theirs.
- **Infra** (`orchestra.lead`, branch `orch-infra-lead-start`, master-based): a long note led before 0 was clamped
  to 0 while the next note still led, so a run at the song's start became a flam and its first note was silent
  (the o6 gate). The long notes after a clamped one now keep `LEAD_KEEP` (0.75) of their written distance, and at
  least `LEAD_FLOOR` (0.15 s) of it, until the full lead is reached. The path without a clamp is unchanged.

Measured with `songs/_blind/tells_orch.py` (`measure_o7`, `pair_shares_o7`; 24 pieces, sets 96000 / 96100 / 96200;
master / o6 / o7):

- **Scherzo:** whole-bar tune notes 0.072 / 0.042 / 0.036.
- **Endings:** inverted final chords 1.0 / 0.79 / 0.08; the tune on top 0.79 / 0.96 / 0.96; held-only endings
  0.54 / 0.71 / 0.58; pairs with the same ending 0.13 / 0.21 / 0.10.
- **Climax / coda:** roles on the climax melody 1.83 / 1.92 / 1.67; coda roles following the melody in octaves
  2.02 / 1.80 / 1.28.
- **Texture:** body bars in 5+-role unison 0.79 / 0.54 / 0.13; static inner parts 0.27 / 0.27 / 0.01; the stock
  build 0.67 / 0.58 / 0.54.
- **Folds:** 1.67 / 0.92 / 1.63 (worse).
- **Score:** 93.5 / 93.0 / 92.9.

The paired round (8 slots, seed 105100, four chamber slots, a scherzo, two 6/8 vivaces and two rivers, 14 judges)
came out at +0.23 overall (se 0.33), with 4 slots won, 2 tied and 2 lost.

- Life +0.68, orchestration +0.38 and melody +0.30 lean new.
- The scherzo slot is +2.14 (new 5.1, master 3.0, the worst piece).
- It is a first lean (o6 tied): **not merged**. A second lean on this branch would meet the bar.
- The best piece is JWCL, a G minor 6/8 vivace, at 5.4.

The next tells (TODO.md, ROUNDS.md "Round o7"):

- chromatic development passages unrelated to the motto
- the climax and coda without the motto
- themes that are only running figuration
- the scherzo cell restated literally
- short climaxes and soft codas after ff
- the final chord's bass doubling

### Round o8: related development keys, the motto in the brass, a singable theme, proportions, the final bass, folds (on the o7 branch)

Round o8 fixes the o7 judges' tells in the owning tables (`endless/symphony.py`, `bandlib/orchestration.py`,
`endless/genres.py`). It is symphonic-only: 24 of 24 protected hashes are bit-identical.

- **Development keys**: `DEV_PATHS` holds home-key scale degrees per mode (rise, fifths, thirds, fall).
  `dev_keys(home, path)` gives each degree the key of its own triad; a diminished degree takes the next one. The
  development sequences through related keys. `dev_mode` no longer picks a chromatic mode, and chromaticism is left
  to the voice-leading.
- **The motto in the brass**:
  - The climax tutti doubles the line in trumpets (over their G4 floor) or in horns an octave under it:
    `tutti_symphonic`, `apotheosis_strings`, `apex_augment_strings`, `apex_combine`, `quiet_climax`, `tutti_chorale`.
  - `tutti_chorale_brass` is a chorale climax with the harmony in horns and trombones and the counter in
    cellos / violas.
  - A quiet climax takes apex 'reharm'.
  - The hymn / memory codas cut the second theme's head and recall the motto in their last `CODA_RECALL` bars.
  - 'descent' opens on the whole motto.
  - The triumph coda / apex keep the augmented motto off the chord snap (forced (0, 0)).
- **A singable theme**:
  - Under a tune, the figuration's range (`FIG_RANGE`) moves below the tune's median minus `FIG_UNDER['gap']`, when
    12 semitones remain.
  - 't1' draws `drive_strings` / `running_strings`, not `motto_bass`.
- **The scherzo** (`DANCE_VARY`):
  - The consequent answers with another cell of the same note count.
  - Every second fragmentation bar is the inverted head.
  - t1b is dotted at scale 2.
  - The climax dance has vary ('reharm', 'invert').
  - `cantabile_horn` puts violins2 / violas arpeggios under the horn instead of held strings.
- **Proportions**:
  - `PROPORTION`: the build at least 8 % / 6 bars, the peak at least 13 % / 8 bars, set in form_rows.
  - `CODA_FALL` (f -> mp -> pp) writes the fall from an ff peak into a soft coda.
- **The final bass**:
  - `END_BASS` / `_end_bass` put the end blocks' bass on the low tonic: cellos G2-F#3, basses G1-F#2, an octave
    apart.
  - `_bass_in_rhythm` merges same-pitch repeats within `BASS_HOLD` (1 beat).
  - The `end_motto` tuba is an octave doubling.
- **Folds** (`FOLD`, `_lower`): an accompaniment note over the tune is re-voiced to the highest chord tone under it
  (within a ninth), else it drops an octave with a neighbour check, else it is dropped. This is used in `_audible`
  (the harp drops) and in the viola pass. The whole-part octave shift stays when 25 %+ of a part is over the tune.
- **The stock build** (`ARRIVALS` / `ARRIVAL_FIG`): the peak's arrival is drawn per piece from its own seed:
  'crash' (roll + crash), 'dry' (a dry crash, no swell), 'timp' (the timpani only) or 'none', so the plan's other draws do not shift.

Measured with `songs/_blind/tells_orch.py` (`measure_o8`; 24 pieces, sets 96000 / 96100 / 96200; master / o7 / o8):

- **Development:** bars far from the home key 0.13 / 0.10 / 0.02; off the chord 0.042 / 0.066 / 0.034.
- **Motto:** climaxes with it in the brass 0.54 / 0.42 / 0.67; codas with it 0.67 / 0.75 / 0.83.
- **Theme:** bars buried under figuration 0.28 / 0.32 / 0.09.
- **Proportions:** an ff climax straight into a soft held coda 1 / 1 / 0; peak share 0.120 / 0.124 / 0.133.
- **The final bass:** low tonic with its octave 0.88 / 0.67 / 0.75; the lowest note 38.3 / 38.8 / 36.8.
- **Folds:** 1.67 / 1.63 / 0.88.
- **The stock build:** 0.67 / 0.54 / 0.33.
- **Score:** 93.5 / 92.9 / 92.6.

The paired round (8 slots, seed 107200: a scherzo, two rivers, four chamber slots, 4/4 + 6/8 + 3/4; 14 judges) came
out at +0.39 overall (se 0.20), with 6 slots won and 2 lost.

- Melody +0.43, harmony +0.41 and orchestration +0.41 (21 / 31 / 4) lean new; memorable is flat.
- The scherzo slot is +1.29 again.
- It meets the bar of > +0.3 with 5 / 8 won, and it is the second lean in a row: **merge**.
- The best piece is PZSU, an Eb andante, at 6.0.

The next tells (TODO.md, ROUNDS.md "Round o8"):

- the climax / coda as violin 16th broken chords over a brass chorale, with no theme
- the apotheosis motto restated literally
- episodes with unrelated new tunes
- a static trio
- the harp interlude after the climax
- bare 2-beat V-I endings

### Round o9: the theme at the climax, no literal restatements, episodes from the theme, the lead-in, the endings, analysis.leads (on the o8 branch)

Round o9 fixes the o8 judges' tells in the owning tables. It is symphonic-only: 24 of 24 protected hashes are
bit-identical.

- **The climax carries the theme** (`APEX`, `APEX_CANON`, `Writer.canon`):
  - 'theme_aug' is its own texture, `apex_theme` (trumpets / horns sing the first theme augmented) and
    `apex_theme_strings` for the chamber orchestra (violins1 with the horns an octave under).
  - Over an augmented line the counter is the material at its own speed: the theme, or the motto every two bars a
    step higher (a canon over its augmentation).
  - The augmented line moves up by octaves to the trumpets' G4 floor (while its top stays at or under C6).
  - The climax / coda figuration enters late (`enter` 0.625 / 0.75 in `chorale_brass`, `apotheosis_strings`,
    `apex_augment(_strings)`): the theme is heard first. `set_memory` 'apex' 3 spreads the climax kinds over a set.
- **No literal restatements** (`REPEAT`, `_unrepeat`): a 1- / 2-bar unit of the line that copies the unit before it
  moves up a scale step (sentence, dance, the climax, the codas).
- **Episodes from the theme** (`DERIVE`, `EPISODE_FROM`): the trio / river tune always grow from the motto and its
  answer bars continue it. A river piece's episode is its tune varied ('march') in the second key.
  `DANCE_VARY['idea']` gives the scherzo's consequent another cell. A river's 'reharm' climax is its own tune.
- **Static stretches** (`STATIC`): the harmony of a non-peak block over 8 bars moves its inner voices (`_move_inner`),
  and the harp arpeggio stops after 8 bars.
- **The retransition** (`RETRANS_LEAD`): its last bar is the motto's head over V7 as the lead-in.
- **After the climax** (`POST_PEAK`): recap2 / coda_soft draw cantabile strings / horn textures, with the dynamics
  stepping down (f -> mf -> mp), no light interlude.
- **Endings** (`END_PRE`, `STROKES['motto']`): the end block is 3 bars with a predominant bar (IV / iv, vi / VI)
  carrying the motto's head before V - I; the strokes fall in the motto's rhythm. The choir is out of the symphonic
  full size (it entered in the last bars only).
- **The gate** (`analysis.leads`, docs/RENDER_FORMAT.md): `Song.lead_hint` names the track that carries the melody per
  section, and the engine's note-dynamics judge takes the lead kind from it. A trumpet chorale or a tuba doubling no
  longer reads as a robotic lead.

Measured with `songs/_blind/tells_orch.py` (`measure_o9`; 24 pieces, sets 96000 / 96100 / 96200; master / o9):

- **Climax:** bars with running figuration 0.45 / 0.10; 16ths over a brass melody in half the climax or coda 0.33 / 0;
  coda figuration 0.21 / 0.07; set pairs with the same climax texture 0.17 / 0.10; climax bars on the theme / motto
  0.65 / 0.65.
- **Restatements:** the most consecutive literal copies 0.083 / 0; the scherzo's 2.5 / 1.5.
- **Episodes** from the theme 0.30 / 0.34; the retransition with a lead-in 0 / 0.54.
- **After the climax:** a light block 0.46 / 0.29.
- **Endings:** a predominant before V 0.63 / 1.0; the choir only at the end 0.36 / none; stock builds 0.33 / 0.08.
- **Static runs:** 4.0 / 4.1 bars. Folds 0.88 / 1.08. Score 92.6 / 91.8.

The paired round (8 slots, seed 109300: a scherzo, two rivers, two chamber slots, 4/4 + 6/8 + 3/4; 14 judges) came
out at +0.30 overall (se 0.27), with 5 slots won and 2 lost.

- Melody +0.45 (27 / 8), life +0.34, form / development +0.32 lean new; harmony is flat (+0.09).
- The new code had 0 gate rejects (the lead hint), master 3.
- It meets the bar of > +0.3 with 5 / 8 won by 0.004: **merge**, a weak one.
- The best piece is DEXR, an A dorian andante, at 6.4.
- After the round, `_audible` cuts a folded note at the chord change (a D#4 held into the final E minor in 7 of 7
  verdicts on UZWK).

The next tells (TODO.md, ROUNDS.md "Round o9"):

- openings without a theme (16th scale runs) or that empty after a few bars
- the loudest section in the middle, a climax of held brass blocks
- static trios / episodes, the scherzo theme still restated nearly literally
- the motto's head opening almost every phrase over one repeated-eighth bass
- short endings after a long build, a shared solo-cello-to-fugato entry

### Round o10: early themes, the loudest climax, moving trios, the motto rationed, proportional endings, folds (on master = o9)

Round o10 fixes the o9 judges' tells in the owning tables. It is symphonic-only: 24 of 24 protected hashes
(piano genres, orchestra-film) are bit-identical after the last change.

- **Openings** (`OPENING`, the 'mist' writer): the rows before the first theme are cut to 8 bars (a slow bar counts
  twice), at least 3; a longer mist states the motto every 2 bars, rising, over I / V. Zero-length chart rows are
  dropped (a 2-bar solo intro wrote a 0-beat note).
- **The climax is the loudest** (`LOUDEST`): the peak block's marks go up to ff, every other block's (but the
  retransition's) are capped at f; a quiet climax is left alone.
- **No held brass blocks under the violins** (`HOLD['restrike']`, `APEX_CANON['answer']`, `AUDIBLE['counter_top']`):
  a harmony / inner / pedal note held past 4 s is re-struck (not in the last block); a one-bar motto in the augmented
  climax is answered by its head inverted; in the climax textures the counter is a protected top line.
- **Violins in unison at the top** (`VLN_UNISON` 84): the violins II an octave under the I above C6.
- **Static trios** (genres trio 'tex', `STATIC['figure']`, `_figure_held`): the trio draws moving-string textures
  ('cantabile', 'cantabile_pulse'), the wind choir rarer; a long non-peak block without an ostinato / figuration
  arpeggiates (or rocks) its two top harmony voices in alternate 4-bar spans. `FIG_UNDER`: the figuration lies under
  the tune's lowest note.
- **The scherzo's return** (`DANCE_VARY['return']`): the restatement dotted and reharmonised.
- **The motto rationed** (`MOTTO_RATION`, `Writer.free`): the sentence's fragmentation, the transition, the
  retransition's kernel, the triumph stretto and the counter state the head every other time; the rest are free 8th
  runs to the next goal.
- **The bass figure** (`BASS_FIGS`, `_pump_figure`): a block's pumping bass draws eighths / octaves / quarters / a walk
  / dotted (6/8: gallop, octaves, dotted, walk), never the block before's.
- **Endings** (`END_LEN`): the end block is 25 % of the peak + coda bars (3-6); a longer end alternates I / IV with
  the motto's head, a step lower each bar, before the predominant and V - I.
- **The fugato's entry** (`FUGUE_ORDERS`, set draw 'fug_order' in `composer.LATE_DRAWS`): rise (cellos first) is one
  of four orders, the rarest.
- **Folds at the source** (`UNFOLD`, `_lower_runs`, `_unfold`): a chord run over its role's range moves down an
  octave as a whole, an octave leap inside a line goes back; the non-end inner voices sit over G3.
- **The choir** stays out (o9, deliberate): the symphonic full size has no choir role and no symphonic texture writes
  for one (`test_no_choir_and_the_lead_hint`); its stock entry in the last bars was a judges' tell. The film genre
  keeps its choir.

Measured with `songs/_blind/tells_orch.py` (`measure_o10`; 24 pieces, sets 96000 / 96100 / 96200; master / o10):
bars before the theme 5.75 / 4.79; the loudest section is the climax 0.67 / 0.88 (margin 0.30 / 0.48 proxy dB);
violins I + II unison above C6 0.21 / 0; the longest still run 5.4 / 4.4 bars, in trios / episodes 1.86 / 0.86;
static_run 4.1 / 2.9; motto statements per 8 bars 4.6 / 3.6; phrase openings on the motto 0.52 / 0.50; repeated-note
bass bars 0.20 / 0.13, bass rhythms per 25 bars 2.3 / 3.0; end bars 3.25 / 4.38 (ratio 0.19 / 0.26); a cello-first
fugato 1.0 / 0.30; folds 1.08 / 0.79; sch_lit 1.5 / 1.0; score 91.8 / 93.4.

### Round o11: the form's argument - the development, the return, one summit, the endings, the length (on master = o10)

Round o11 takes the masterpiece panel's plan (`songs/_endless_orchestra/out/masterpiece_gap/REPORT.md`, "Round o10":
generated 4.67 / 10 against the references' 5.69 on an absolute scale) and o10's tells. It is symphonic-only: 24 of 24
protected hashes (piano genres, orchestra-film) are bit-identical.

- **The development works the kernel** (`DEV_SHARE`, `DEV_LADDER`, `dev_stages`):
  - The development's blocks take at least 25 % of the bars and 16 song bars (at most 33 %). The dialogues grow to
    16 song bars each; beyond that a second dialogue follows on the next key path (two arguments, not one unit 12
    times). The scherzo / trio and the ternary forms have a development row now.
  - Every technique states its own unit in at most three 2-bar models (two transposed copies), then the unit
    shrinks: the head inverted and answered (1 bar), the kernel per half bar, the kernel diminished in the last
    model. A stage that goes on inverts its statements; a one-note kernel is the head diminished.
- **The return closes the argument** (`RETURN`, layouts): the compact and through forms bring the second theme home
  (a recap2 row); the return's blocks after the development weigh at least the exposition's theme blocks (the
  recap2, then the recap grow, to 12 bars).
- **The summit at home** (genres, `REHARM`, `APEX_RIVER`): no 'relative' climax key and no 'restate' climax in the
  set table; the 'reharm' climax of a major piece stays home over another harmony (no bVI / IV / bIII summit); a
  river's augmented climax augments its own tune.
- **The dominant pedal before the return** (`RT_PEDAL`): the retransition ends on 6 song bars over the dominant (a
  harmonic frame before them gets 2 bars or more), and the kernel builds answer the motto's head in imitation half a
  bar later an octave under (a counter slot in `tremolo_build`, `pulse_build`, `subito_build`).
- **One summit** (RULES `reserve` 3 + `reserve_after`, `LOUDEST` 'pre' / 'quiet'): nothing before the peak block
  comes within 3 semitones of its top note, nothing after it reaches it; the blocks before the peak are capped at mf
  (the opening call keeps its f), and under a quiet climax every other block too. A figure under a wider margin moves
  down as a whole where it fits.
- **Endings** (`ENDING_CADENCE`, `SOFT_ENDINGS`, `SOFT_OF`): the plagal ending is predominant - V7 - I; no soft
  ending fades on IV or over the tonic pedal.
- **Moving lyrical basses** (`STATIC['walk']`, `_walk_long`): the long bass of the second themes, trios, rivers and
  episodes moves by the half bar (another chord tone, a passing step into the next chord).
- **The movement's length** (`MIN_LEN`): a movement under 3:00 grows its development, then its themes and returns,
  two bars at a time (`form_rows(bar_s=...)` from the tempo).
- **The score** (`form_stats`, `SCORES['symphony']`): dev_share, seq_links, t1_home, t2_home, recap_weight,
  cadence_end, peak_pos, top_peak, pre_semis, seconds; the motto counts weigh 1 (they rated ASFP 99.8).

Measured with `songs/_blind/tells_orch.py` (`measure_o11`; 24 pieces, sets 96000 / 96100 / 96200; master / o11):
seconds 168 / 225; development share 0.13 / 0.27 (10.7 / 29.7 song bars); the longest chain of transposed copies 1.9 /
1.6; dominant pedal bars before the climax 1.5 / 6.3; the climax at home 0.71 / 1.0; the first theme home at or after
it 0.71 / 1.0, the second theme home 0.85 / 1.0; a V - I at the end 0.83 / 1.0; the climax's top over everything
before it 1.6 / 3.5 semitones, the loudness margin 0.8 / 1.7 proxy LU; the highest note in the climax (one_summit)
0.17 / 0.42; folds 0.79 / 1.54 (worse: melodies kept under the reserve fold the figuration over them); dev_own 0.80 /
0.67.

The paired round (songs/_blind/ROUNDS.md "Round o11"): +0.32 se 0.32 against master, 5 of 8 slots won (development
+0.52, melody +0.43, orchestration -0.02); the absolute masterpiece score new 4.23, old 3.89, references 5.50.

### Round o12: the development on the motto, the summit with brass and a top, no endless accompaniment, themes with profile (on master = o11)

Round o12 takes o11's masterpiece panel ("what is missing": a development of textures, a summit without brass or
top, 8-bar-plus accompaniment runs, step-scale heads) and o11's tells (dev_own 0.80 -> 0.67, folds 0.79 -> 1.54,
tutti at the peak 0.42). It is symphonic-only: 24 of 24 protected hashes are bit-identical.

- **The development works the motto** (`DEV_LADDER['imitate']`, the episode / dialogue textures, `INNER_MOTION`
  'floor'): the ladder's second stage states the head over the tonic, then the dominant, its answer half a unit
  later a fourth under (inverted every other statement); the episodes are `motto_brass` / `dialogue_brass` /
  `motto_bass` (no harp-only colour); the dialogues' melody stays in the violins / winds, the ostinato enters under
  it; the ostinato's lower part never moves under C3 (the harp took it there); the 'bass' technique's motto in the
  bass and its answer keep their intervals in the key (`DEV_BASS_RAW`: fit_line had snapped them to the chords). `dev_own` (`own_stats`, the share of
  development bars stating the piece's material) is a hard gate of the score at 0.8.
- **The summit** (`SUMMIT`, `_summit`, RULES `reserve_lines`): the peak's violins I sit at least 4 semitones over every
  line before it and at A5 or higher - the line up the octave under C7, else its closing 2-bar units; still short,
  the earlier blocks' phrases that reach it go an octave down whole, breath to breath (or are handed to the oboe /
  clarinet / violins II / violas when the role has no lower octave), their accompaniment with them. The trumpets and
  trombones double the climax's melody at the octave that holds most of it (a classical orchestra: the horns). Every
  role the piece plays elsewhere joins the peak (the fullest tutti), never over the top line except the flutes an
  octave over it; the timpani on the chords. The reserve's margin for lines is 1 (the accompaniment keeps 3): the
  margin lowers the accompaniment, not the tunes.
- **No endless accompaniment** (`TEX_RUN`, `_vary_runs`, `acc_runs`): after 8 song bars of one accompaniment onset grid
  the next 2 bars thin to twice the finest pulse (held bars re-struck at the half); the peak and the retransition /
  ending blocks are free.
- **The drive into the return** (`RT_DRIVE`, `_rt_drive`): the retransition's last `RT_PEDAL` bars put the basses /
  cellos and the timpani on re-struck dominants (quarters, then 8ths) under the motto's fragments, unless they carry
  the motto themselves.
- **Themes with profile** (`MOTTO_CHARACTER` 'scale', `DANCE_FILL`): a motto runs at most 2 steps one way (no scale
  heads; the fallback cells are drawn by weight); a dance's contour fills its narrowest gap with a neighbour note
  and keeps its leap. Codas (`CODA_RECALL` 'unit') state the motto every 2 bars, transformed (rising / inverted).
- **Folds** (`UNFOLD_ALL`, `_refold`): every ostinato / figuration of the finished orchestration goes through
  `_unfold`, then a leap no single octave mends moves its run (or the repeated notes on one side) an octave.
- **The score** (`summit_stats`, `own_stats`, `SCORES['symphony']`): dev_own (hard), tutti_peak, vln_over, brass_peak,
  acc_run.

The paired round (songs/_blind/ROUNDS.md "Round o12"): +0.54 se 0.20 against master, 7 of 8 slots won, none lost
(form +0.59, life +0.61, orchestration +0.45); the absolute masterpiece score new 3.98, old 3.59, references 5.74.

### After o12: the code review's infrastructure (no judging round)

A code-reading judge (`songs/_endless_orchestra/out/code_review/REPORT.md`, main checkout) found the score circular,
the tells a copy of the generator's own window logic and the harmony diatonic, one chord a bar. This step prepares the
next paired rounds; with every new flag off the symphonic renders are bit-identical to o12 (and the 24 protected
hashes too).

- **The score is no longer circular** (G1; `genres.SYMPHONY_GATES`, `symphony_table`, `symphony_ranking`): the 13
  metrics a construction rule guarantees (seq_links, acc_run, vln_over, tutti_peak, brass_peak, t1_home, t2_home,
  cadence_end, seconds, dev_share, peak_pos, top_peak, pre_semis) rank nothing - weight 0, hard: a candidate that
  misses one is capped and listed in `score()['hard']`. Best-of-N ranks on the rest. `SYMPHONY_RANK_GATES` /
  `symphony_ranking(True)` restore o12's ranking for a paired test. On the 24 slots of sets 96000 / 96100 / 96200
  (best-of-4, 96 candidates) no slot changes its pick; the score values sit 1-4 points lower (the gates' perfect
  sub-scores no longer pad the mean). acc_run is NOT guaranteed: 15 of the 96 candidates run 9-14 song bars after
  `_vary_runs` (why is open) - an assertion that fires, see TODO; seconds missed twice, seq_links / vln_over /
  tutti_peak once each.
- **Independent tells** (5.5; `songs/_blind/tells_orch.py`): the material windows match on GENERIC intervals (unison,
  step, third ... octave; inverted allowed) with the IOI ratios within 3 %, no scale runs (a run of steps one way
  states no material - symphony's `run_to` fills matched anything), and only the rendered lines (no
  `symphony.motto_notes` cell); `seq_links_max` reads the rendered development lines with generic intervals instead
  of the composer's block lines with +-1 semitone. symphony.own_stats / _seq_links keep their o12 logic (the score), so
  the two can now disagree. The shift (24 pieces of sets 96000-96200, old / new tells): master (o12) dev_own 0.753 /
  0.604, dev_mot 0.677 / 0.532, clx_motto 0.528 / 0.412, clx_own 0.564 / 0.455, clx_theme 0.689 / 0.578, clx_top
  0.367 / 0.272, coda_mot 0.917 / 0.75, seq_links_max 1.71 / 1.38; the o13 branch dev_own 0.831 / 0.644, seq_links_max
  1.17 / 0.75 (o13 still above o12, its dev_own lead halved: +0.078 -> +0.040); the references' dev_own 0.83 / 0.63
  (stormy 0.96 / 0.96, river 0.86 / 0.58, scherzo 0.67 / 0.33). The other 144 tells are unchanged.
- **The chromatic vocabulary** (A2 step 1; `CHROMA`, `chroma_symbol`, `chroma_spell`, `realise`, `harmonize(chroma=,
  forced tuple pins)`): applied dominants V7/V, V7/IV, V7/ii, V7/vi, vii°7/V, the Neapolitan sixth, the Italian /
  French / German sixths, mixture bVI / iv in major (bVI after V: the deceptive cadence). `CHROMA_WEIGHTS` are 0: no
  candidate unless a call asks. `realise()` voices a chord into its resolution: the augmented sixth's b6 down and #4
  up to the dominant (the German into the cadential six-four), the Neapolitan's b2 down, the applied leading tone up
  and its seventh down or held; no parallel fifths / octaves between any two voices, no doubled tendency tone or
  leading tone.
- **CHROMA_CADENCE** (off; `CHROMA_CADENCE_ON` = {'recap', 'final', 'bars': 2}): the chromatic predominant before the
  return's dominant pedal (`Writer._chroma_rt`: the pedal frame gets 2 bars more first, a frame its last 2 bars) and
  before the final cadence's approach (the end block), chosen by `harmonize()` among the vocabulary that resolves to
  the next chord (`chroma_pre`, `CHROMA_PRE`, `END_CHROMA`), the harmonic rhythm two chords a bar over those bars; the
  harmony / inner parts take `realise()`'s voicing (`_chroma_voice`), the melody over it snaps to the chord's scale
  (`fit_line(chroma=)`). A paired round switches it on with `songs/_blind/shared_plan.py run ... --flag chroma`
  (`--flag rank_gates`: o12's ranking). On the 24 pieces of sets 96000 / 96100 / 96200: every ending and 17 retransitions take one
  (It6 8, V7/IV 8, Fr6 6, N6 6, vii°7/V 6, V7/V 6, Ger6 1); score mean 91.45 -> 91.35, clash 2.11 -> 2.13.
  **Round o14** (on vs off, best-of-1 on the same seeds, 16 slots): a null, overall -0.05 se 0.18, harmony -0.01 se
  0.11 - the flag stays off. The retransition's chord went unheard, the final one was heard as colour in 5 of 16
  pieces; the next step makes it an event (tutti / brass, held, the bass on the chromatic step: ROUNDS.md "Round o14").
- **CHROMA_EVENT** (off; `CHROMA_EVENT_ON`): the chromatic chord as an event at the structural points. The final
  cadence's bar before V - I becomes one held tutti predominant (`EVENT_FINAL`: N6 / Fr6 / Ger6, the bass on b2 / b6;
  sf, ff, a fermata, `_final_event`); before the return's dominant pedal a 4-chord chain on half bars arriving on V
  (`EVENT_CHAINS` descent / deceptive / ascent / neapolitan, `Writer._event_rt`). Voiced by `_event_voice` (a DP
  chorale voicer: complete chords, tendency tones by step, no doubled leading tone, no parallels incl. the bass),
  scored by `_event_tutti` (brass, strings, winds; capped at the summit's role count and top) and `_event_marks`.
  `shared_plan.py run ... --flag event`. **Round o15b** (on vs off, best-of-1, 16 slots): -0.12 se 0.16, harmony
  +0.17, life -0.29 - the flag stays off: heard, but as the shared formula in every piece (ROUNDS.md "Round o15b").
- **Gate repairs** (o15b, bit-identical where no gate failed): `TEX_RUN['repair']` (`_vary_runs` thins any accompaniment
  run `acc_runs` still counts over 8 bars), `SEQ_BREAK` / `_break_links` (no 3rd sequential link in the development's
  lines), `MIN_LEN['more']` (longer t1 / t2 / recaps when 'grow' stalls under the seconds floor), `TUTTI_SKIP` (harp /
  percussion are no tutti role in `summit_stats`).
- **Dead code / docstrings** (5.4, 5.7): REHARM retired (it could only draw 0), the stacked docstrings of
  MOTTO_CHARACTER / CELLS, SOFT_OF / ENDING_CADENCE and CODA_RECALL / CODA_CANON put back on their constants, the
  'plagal' ending documented as what it is (the predominant, V7, I); `dev_mode` (read by nothing) stays in the set
  table - a removed draw would re-roll every plan.

### Round o16: the derivation engine (the code review's A1; `DEV_WALK`, off)

- **Step 1, bit-identical**: `motto_notes` is `Kernel.motto(m).apply(...)`. A `Kernel` holds a rhythm cell, an
  interval cell (scale steps, the landing resolved), its contour and signature (the accent pattern), and states
  itself through an op chain: motto_notes' transforms (invert, augment, diminish, head, kernel, chordal), then the
  `DERIVE_OPS` in order - retro, expand / contract (every interval a step wider / narrower), liquidate (every interval
  a step its way), displace (half a beat late), shift (half a bar late: the metric position), frag2 / frag3
  (fragment(k)), combine (the line's rhythm on the other kernel's intervals), and the harmony ops mode / reharm that
  the walk realises. `Kernel.line(notes, key)` is a written line's head - the second theme's kernel K2. Every
  statement logs a derivation node `{node, parent, ops, depth, src}` in the composer's log (`Writer.node`,
  `Writer.derive`), so the derivation is readable afterwards.
- **Step 2 (`DEV_WALK_ON`)**: a dev_dialogue block is a PLANNED WALK (`Writer.walk`, `WALK`), drawn per piece from
  the composition seed:
  - 1-3 phases, each one arrangement and its own block / texture (`_phase_blocks`, `WALK['tex']`): call (the unit
    answered by its transform in the other choir), imitate (a canon a step-count under / over, delay a half / whole
    bar), against (the motto's derivation against the second theme's), bass (the line in the bass under a counter
    from the other kernel), false (a false entry: the motto's head plain in the home key, broken off); each phase a
    level over the one before.
  - segments: a model of 1-4 bars by the block's shape (shrink / grow / arch / wave / ...: the unit can grow back as
    well as shrink), 1-3 models a sequence - diatonic up / down a step, by falling fifths or thirds, or real
    (transposed by semitones) -, linked by its own chords or applied dominants (V7/x, CHROMA, through `harmonize()`'s
    pins), each segment ARRIVING in the next segment's key (ii / iv - V7 - I, a half cadence, V7 - vi, or a chromatic
    predominant from CHROMA before the V7); the last arrives on the home dominant (the retransition follows).
  - each segment's unit is an op chain on K1 or K2 whose depth rises from 1 to 4 over the development, grown from the
    segment before or a new branch, ops the piece has not used preferred, never the last unit again; a model too
    short for its unit fragments it (`_fit_ops`); its rest is filled by the unit's inner derivations (`_fill`).
  - the return: the recapitulation's second theme (recap2) and the coda take one counter-line the development
    derived (`Writer.dev_line` / `recall`) instead of the motto / canon counter.
  - the score: `derive_stats` (dev_ops, dev_depth, dev_literal) replaces the dev_own gate (`genres.symphony_derive`,
    `SYMPHONY_DERIVE_ROWS`; dev_own stays at weight 0). `songs/_blind/tells_orch.py` is untouched (independent).
  - `shared_plan.py run ... --flag derive`.
- Route diversity over round o16's 16 slots (`D:\tmp\o16\route_div.py`): mean pairwise Jaccard distance of the route
  tokens 0.605 on / 0.285 off, distinct segment kinds 110 of 110 on / 23 of 140 off, distinct tokens 92 / 23, phase
  (technique) orders 15 / 10 of 16.
- Round o16's result (ROUNDS.md "Round o16"): on vs off -0.28 se 0.19, 5 won / 9 lost - DEV_WALK stays off. The
  phase split was heard as short panels, and the deep op chains as material unrelated to the motto. The next try
  drops the split and caps the op depth at 2.

### Round o17: DEV_WALK v2 - one block of worked processes (`Writer.walk2`, `WALK2`)

- The flag's meaning is now v2 (`DEV_WALK_ON = {'v2', 'recall', 'graph'}`); o16's walk stays reachable as
  `DEV_WALK_V1` (the phase split, `Writer.walk`). Off is bit-identical (40 of 40 symphonic pieces, 24 of 24
  protected hashes).
- The layout's development blocks stay as they are - no new blocks. Each holds 1-3 PROCESSES of 8-12 song bars
  (`WALK2['bars']`), drawn per piece (`procs`, `reuse`: the piece's other blocks draw other kinds):
  - `sequence`: the unit 2-3 times as a sequence (up a step, up by thirds, the falling-fifths chain, or real: two
    semitones up per model), its answer half a model late in the first model, then a quarter, then an eighth (the
    lines overlap more); then the head per bar and the kernel per half bar in the two lines in turn into the arrival;
  - `stretto`: the subject (the motto, one op at most) in imitation 3 / 4 / 7 scale steps under - two entries a
    subject's length apart, two at half of it (overlapping), the head, then the kernel half a bar apart, each pair a
    step higher; the development's last process prefers it (`drive`: into the retransition's pedal);
  - `against`: the unit over the second theme's head (augmented), from the second model with its own head inverted
    as an answer;
  - `bass`: the unit in the bass under the other kernel's head (a block of one process: `dev_bass`).
  Every process arrives in the next one's key (ii / iv - V7, a chromatic predominant - V7, a half cadence, V7 - vi),
  the last in the home key; its register rises 7 semitones (`_band2` keeps every statement's median near the rising
  centre) and its level climbs (one `dyn` ramp per process, p / mp to f, capped under the climax by LOUDEST).
- The unit: at most 2 ops (`cap`) in any statement, one interval op at most (expand / contract; liquidate and
  combine are not drawn - they lose the contour), no retrograde; a statement's rest is its last note held 2 beats,
  then rests (no `_fill`).
- One texture per block: `walk_dialogue` / `walk_poly` (orchestration.py) - the dialogue / polyphony with a doubling
  entering at the block's middle (a phrase boundary: the colour grows, never switches). The storm's second block
  keeps its brass and dynamics.
- A false entry (one a piece, `false` 0.35) only opens a later process, after the process before it breaks off its
  arrival (the thinning) and its level drops to p.
- The graph rows: `dev_ops` at least 4 (o16: 6), `dev_literal` at most 6 (a stretto's subject is the motto).
- Route diversity over o17's 16 slots: mean pairwise Jaccard 0.611 on / 0.288 off, 16 / 16 distinct route
  signatures.
- Round o17's result (ROUNDS.md "Round o17"): on vs off -0.14 se 0.20, 8 won / 7 lost - DEV_WALK stays off. The
  motto stayed audible ("unrelated material" level, 12 / 10) and harmony leaned up (+0.12), but every process
  arriving in a new key was heard as unprepared KEY panels (23 / 11 sentences), and in the slow pieces the
  held-then-rest models read as one cell hammered over a thin texture. Next: one key (or one prepared modulation) per
  block, process length by time at slow tempi, a stretto heard as one.

### Round o18a: DEV_WALK v3 - one key per block, processes by time, a four-voice stretto (`Writer.walk3`, `WALK3`)

- The flag's meaning is now v3 (`DEV_WALK_ON = {'v3', 'recall', 'graph'}`). o17's walk is `DEV_WALK_V2` and o16's
  is `DEV_WALK_V1`. Off is bit-identical (40 of 40 symphonic pieces, 24 of 24 protected hashes).
- Keys: a development block stays in ONE key (its path's j-th, for the j-th dialogue), or makes ONE prepared
  modulation into the key of the block after it (`_next_area`: the next dialogue's, the fugato's, the false
  recapitulation's; home before the retransition). The modulation comes at a process boundary (`mid`) or in the
  block's last arrival, by `modulate`:
  - 'pivot': a chord diatonic in both keys (`Writer._pivot`), then the new key's V7;
  - 'dominant': the new key's V7 held for a bar.
  In-key arrivals are mostly elided or half cadences. Before the retransition the last process drives on
  ('drive'): the kernel in both lines each half bar, the bass on the pivot and then the home key's dominant, with no
  cadence and no landing. There is no `mode` op, no real sequence and no false entry.
- Time: processes are about `secs` (17 s) long, so an andante block holds more, shorter processes than an allegro
  block. At `slow` tempi (an internal bar of 2.7 s or more):
  - the models are one bar long;
  - the answer comes a quarter model late;
  - a rest of `gap_s` or more is bridged by the kernel.
  A held note lasts `hold_s` at most. The head / kernel drive is `drive` bars / `drive_s` seconds at most.
- The stretto has four voices:
  - the melody, the counter, the tenor in the harmony's top voice, and the bass in the bass line - texture
    `walk_stretto`, with `_walk_entries` writing the tenor and bass into their window;
  - the exposition a subject apart (or half), the later entries half a subject apart, then the head in turn, the
    bass last;
  - once a voice has entered it never drops out: the kernel inverted, a fragment, the head contracted, each
    leading toward its next entry.
- No note in the walk is shorter than a 16th or 0.12 s (`min_beat` / `min_s`). `_fit3` cuts a statement instead of
  diminishing it. o17's silent_notes rejects were 32nds at velocity 14-23, from `_fit_ops`' 'diminish'.
- The walk's textures have no flute doubling: `walk_dialogue3` doubles the call with the oboes in unison, and
  `walk_stretto` with the violins II.
- One level ramp per block.
- Over o18a's 16 slots:
  - keys per development block 1.88 (v2 2.75);
  - new-key arrivals per block 0.88, all prepared (v2 1.75);
  - route diversity: mean pairwise Jaccard 0.680 on / 0.296 off.
- Round o18a's result (ROUNDS.md "Round o18a"): on vs off +0.03 se 0.16, 8 won / 7 lost - the first level derive
  round, but DEV_WALK stays off.
  - The key panels are level (43 / 41 sentences); the keys still faulted are mostly set level.
  - The andantes no longer lose.
  - Development is the weakest dimension (-0.18): the walk restates the unit on each degree rather than taking it
    apart.
  - The four-voice stretto was not named. Old's own develop() stretto (whole-motto entries one per bar in the
    strings) was named.

### Round o18b: SET_PLAN - diverse, memoryful set-level plans (`genres.symphony_setplan`, off)

- **Switch**: `genres.symphony_setplan(True)` (`shared_plan.py --flag setplan`). Apply it BEFORE the set plan is
  drawn.
  - It sets `symphony.SET_PLAN` (`SET_PLAN_ON`: builds / arc / voicing / contour / endings).
  - It adds `CELLS_V` to `CELLS`.
  - It merges `SETPLAN_SET` / `SETPLAN_MEMORY` into `plan['set']` / `plan['set_memory']`, and `SETPLAN_ARC` into
    the set arc.
  - It sets `plan['set_groups']` / `plan['set_feel']` and rebuilds the score rows (`SETPLAN_ROWS`).
  - Off restores every one of these; off is bit-identical (40 of 40 symphonic pieces, 24 of 24 protected hashes).
- **composer.set_draws**, two generic hooks for any genre:
  - `plan['set_groups'] {draw: {choice: group}}`: the memory excludes a choice's GROUP (the motto's rhythm family);
  - `plan['set_feel']`: the draws taken among the slot's feel's own choices (its `layouts`).
- **composer._slot**: the set arc's `meter_share` / `meter_gap` cap a meter's share of the set and forbid the same
  meter twice in a row. The candidates' dice are drawn first, so off consumes the rng as before.
- **The data** (symphony.py):
  - `GESTURES`: per build its writer, frames, pedal bars, drive, need and over. The new writers are `lowbrass` (the
    augmented motto in the trombones / cellos, rising a step per statement) and the `wave` steps by the contour. The
    build textures are `swell_build`, `lowbrass_build` and `collapse_build`. Only `pulse` keeps `_rt_drive`.
  - `ARC_CRISIS`: `_crisis_rows` puts the peak into the development (the parallel minor), then a collapse
    retransition and a calm recapitulation.
  - `VOICING`: `_summit`'s `layers` keeps the brass off the tune's doubling and gives the chords roles harmony parts
    (`_chord_part`).
  - `CONTOURS`: the apex statements' steps.
  - The endings:
    - `END_FAMILIES` / `END_SOFT` (the cadences `amen` = V7 - IV - I, `decep` = V7 - vi then V-I, `pre`, `cad64`,
      `V`);
    - `END_TEX` (`end_line`: a falling tenor line, `_end_line`);
    - `END_COLOURS` (`_set_plan_pass`: no harp in the codas, no timpani in the last block unless the ending is
      `strokes`).
  - `MOTTO_FAMILIES` over `CELLS` + `CELLS_V` (syncope, trochee, hemiola, sigh, pickup; five notes each, so
    dev_own keeps its material).
- Round o18b's result (ROUNDS.md "Round o18b"): on vs off -0.16 se 0.27, 6 won / 9 lost. **SET_PLAN stays off.**
  - The plans got more diverse: template similarity 0.418 vs 0.495; 10 / 7 builds; no build repeat within 4.
  - The judges' tells for those gestures fell: the timpani pedal build 0.50 vs 2.06 lines per packet, 6/8 0.38 vs
    0.94.
  - The template flags per packet fell only 12 % (34.4 vs 39.0, references 23.7). The template is now the LAYOUT
    (the scherzo_trio's fixed 13-section plan, cross-piece verbatim bars in 3/4), the post-climax harp episode, and
    the peak at 72-87 %.
  - The crisis arc lost all 3 of its slots.
  - The best piece of the round is a flag-on piece: RFWG (slot 6: fugal layout, fugato build, amen ending), overall
    7.3, masterpiece 5.57.

### Round o19a: SET_PLAN v2 - the layout's shape, the climax's place, no post-climax harp, the crisis, the endings (`genres.symphony_setplan`, off)

- **Switch**: the same flag as o18b (`shared_plan.py --flag setplan`); `SET_PLAN_ON` now carries `'v2'`
  (`SET_PLAN_V1` is o18b's). Off is bit-identical (40 of 40 symphonic pieces, 24 of 24 protected hashes).
- **The shape** (o18b fix 1): `plan['set']['sections']` (-2 .. +2) - `_shape_rows` drops (`FORM_SHAPE['drop']`: the
  first theme's restatement, the closing group, the trio's repeat, the second theme's restatement, an episode, the
  opening call, a third variation) or adds (`FORM_SHAPE['add']`: a t2b, a codetta episode before the development, a
  false recapitulation between two development blocks, the scherzo's da capo after the trio, a closing group, a
  variation) sections, in `form_rows` after the development's blocks.
  - `plan['set_shape']` (`genres.SETPLAN_SHAPE`, `composer._set_shape`, generic): a feel's (layout, sections) never
    twice in a set - the memory on the layout's shape, not its name.
  - The 3/4 (the scherzo) capped at 2 of 16 (`SETPLAN_ARC` meter shares 6/8 5, 4/4 9, 3/4 2).
- **The climax's place** (fix 5): `plan['set']['peak_at']` (0.6 / 0.66 / 0.72 / 0.8 / 0.88; the crisis's mapped into
  0.48-0.62) - `_place_peak` grows the short side's blocks (`PEAK_AT['post']` / `['pre']`), then shortens the other
  side, then (a climax too early) moves the second theme's return before the retransition (the reversed
  recapitulation); never under MIN_LEN, the development within DEV_SHARE. `SETPLAN_ROWS` peak_pos 0.42-0.92.
- **No harp after the climax** (fix 3): `_set_plan_pass` empties the harp in every block after the peak, and takes a
  harp with fewer than `POST_HARP['min']` notes out of the piece; the post-peak recap2 is `POST_PEAK_V2` (dev_poly /
  the horn's cantabile / the driving tutti, mf).
- **The crisis** (fix 4, `CRISIS_V2`): the crisis 2 bars longer than the return's climax was; the return after it the
  first theme augmented as a wind chorale (`Writer.variation` 'chorale', p - mf); the coda the dissolving kind with
  the motto recalled (memory / descent / echo). A mood without the dissolving coda plays the return arc.
- **The endings** (fix 6, `END_V2`): the end block at least 5 bars; the whole motto at its own speed over the first two
  closing bars; the amen as V7 - I, then IV - I with 4 - 3 in the melody (`blk['amen']`; the last fermata on its
  I; `cadence_end` accepts it); the deceptive chord with the melody's tonic held over it at f, then subito p.
- **Master** (fix 2, flag-independent): `_symphonic_arc` 'key_apart' - `composer._slot` never draws a key an earlier
  slot of the same time signature has (o18b's HYRF / JDGP were two F major scherzos whose development charts and
  voicings coincided; the development's chart and its voicing are a function of the key and the meter). A clash is
  redrawn with its own die, so a slot without one draws as before: of the bit-identity sets only 96000's slot 8
  changes (not in the 40-piece check); 133000 changes slots 10-13 and 135000 slots 10-12 and 15 (keys only).
- Round o19a's result (ROUNDS.md "Round o19a"): on vs off -0.25 se 0.20, 6 won / 9 lost. **SET_PLAN stays off.**
  - The plans got more diverse: template similarity 0.423 vs 0.473, shape similarity 0.123 vs 0.191, no repeated
    (feel, layout, sections); the peak's sd 0.078 vs 0.040 (9 vs 15 at 72-87 %); no harp after the peak (0 vs 11).
  - The template flags per packet fell 24 % (37.1 vs 48.6, references 15.3); no verdict names a post-climax harp or
    copied bars on the new pieces; the amen / deceptive endings are named (1.00 vs 0.12 lines per packet) but as
    expected closes.
  - It lost on life (-0.41) and form (-0.31): the added sections (14-15) read as stop-and-start, the dissolving codas
    as 19-20 bar fades, the early peaks (< 0.7) as long wind-downs; the crisis arc lost again (-0.79 over 2 slots).
  - The shared section TEXTURES (the 16-bar dialogue, the oboe over a pulsing bass) are the template left.
### Round o19b: FUGUE - a real fugato and a joint voice-leading core (`Writer.fugue2`, off)

- **Switch**: `symphony.FUGUE = dict(symphony.FUGUE_ON)` (`shared_plan.py --flag fugue`); None (the default) is
  master's `Writer.fugato`, bit-identical.
- **The fugato** (`Writer.fugue2`, the `dev_fugato` blocks; the retransition's fugato build is unchanged):
  - The key: a roman of the home key drawn from `FUGUE_ON['keys']` (`fugue_key`: vi / ii / iii / IV / V, minor iv /
    v / III / VI) - not always vi / iv.
  - The subject (`Writer.fsubject`): the motto, its landing held at most a beat, then a tail in the other rhythm
    (quarters after a quick head, 8ths after a slow one) stepping to the tonic's third or the tonic.
  - The answer at the fifth, tonal (the subject's opening dominant answered by the tonic), harmonised in the
    dominant.
  - The counter-subject: written once against the first answer (`voicing.complement_rhythm` + `counterline`:
    moving where the answer holds) and stated again with every later entry, transposed and fitted.
  - 3-4 entries in the four registers (`FUGUE_ON['voices']`) by the set's `fug_order` (`orders`: no high violin
    alone at the start), over the choirs: the textures `fugue_mixed` (violins I / oboes / violas / cellos),
    `fugue_horn` (violins I / clarinets / horns / cellos, only where the subject's shortest note lasts 0.2 s) and
    `fugue_reeds` (oboes / violins II / clarinets / cellos); the basses double the bass voice from its entry.
  - After the exposition (by the block's bars): an episode (`_FUGUE_EP`: a falling-fifths or rising chain into a
    related key diatonic to home) from a fragment of the subject - the head, or the tail's first bar - in the top
    voice, imitated half a bar later under it, the sequence's last bar held (at most 2 links: SEQ_BREAK); a middle
    entry and a second episode in a long block; the final entry in the bass or a stretto (the top voice, the bass a
    bar or half a bar later); a half cadence with the bass driving 8ths on the dominant. The voice of the next entry
    rests in the episode before it.
  - The free voices: `voicing.counterline` against everything written, in a rhythm complementary to the other lines;
    then `voicing.repair` moves the free notes (never an entry's or a fragment's) until the joint issues fall.
  - The entering voice FUGUE_ON 'lead' velocity steps up, the others 'other' (`_fugue_offs`).
- **The joint voice-leading core** (voicing.py, `CP`; README "Voicing"): `cp_issues` (parallel fifths / octaves
  between the outer voices and any pair, unison / octave runs over a beat, unprepared or unresolved strong-beat
  dissonances and weak ones by leap, `lock` attacks together, crossings), `repair(parts, scale=, movable=, hook=)`,
  `complement_rhythm`, `counterline(against, rhythm, ..., hook=)` - a shared primitive the summit's layers can use.
- **Result** (songs/_blind/ROUNDS.md "Round o19b"; the plan forced to a fugato in all 16 slots for both codes):
  +0.27 se 0.15 (1.7 se), 9 won / 4 lost - under the bar, the flag stays off. Every dimension leans up (life +0.31,
  orchestration +0.27, development +0.26), masterpiece 3.54 / 3.41 / references 5.07. The "unaccompanied violin" and
  one-pattern sentences fall; still open: the first entry alone and the block thin and quiet for 16-20 bars, the
  counter-subject unheard, the subject heard as new material, the fugato absent from the summit.

### Round o20: SET_PLAN v3 - the shape by merging, the textures with set memory, the fades capped (`genres.symphony_setplan`, off)

- **Switch**: `genres.symphony_setplan(on, version=None)`; `SETPLAN_VERSIONS` {1: `SET_PLAN_V1`, 2: `SET_PLAN_V2`,
  3: `SET_PLAN_V3`}, `SETPLAN_VERSION = 3`, `SET_PLAN_ON = SET_PLAN_V3`. `shared_plan.py --flag setplan` is v3,
  `--flag setplan2` is o19a's v2. v3 uses `SETPLAN_SET_V3` / `SETPLAN_MEMORY_V3`. Off is bit-identical (40 of 40
  symphonic pieces, 24 of 24 protected hashes).
- **The shape by merging and lengthening** (`FORM_MERGE`, `_merge_rows`, in `form_rows` after the development's
  blocks; v2's `_shape_rows` does not run): `plan['set']['sections']` -3 .. 0 folds the shortest eligible block into
  its predecessor (`FORM_MERGE['into']`: t1b into t1, the closing group into the second theme / river / episode /
  trio / variation, an episode into a neighbour), up to `FORM_MERGE['max']` bars per kind and even; never the climax
  or a false recapitulation; the section count capped at 12. Every long kind at least 8 bars (`'least'`), and
  `_grow_len(..., more=FORM_MERGE['more'])` grows the long kinds when a piece is short.
- **The section textures** (`TEX_V3`): `plan['set']` draws `tex_t1`, `tex_t1b` and `tex_dev` with set memory (3 / 2 /
  3; `t2col` 4, `src` 3). `material` gives a t1 / t1b block the layout left without a texture the drawn one, and the
  development's dialogue blocks (techniques in `TEX_V3['dev_tech']`) the drawn one rotated per block.
- **The climax** (`PEAK_AT_V3`): `peak_at` 0.7-0.86; `_place_peak(..., table=PEAK_AT_V3)` (an 8-bar floor for the
  long kinds, the coda not grown when it dissolves), then `_grow_dev`, `_fade_v3`, `_grow_len`, and the floor 0.66
  checked (twice).
- **The fades** (`FADE_V3`, `_fade_v3`): a dissolving coda plus the end block at most 10 bars, the coda at least 4.
- **No crisis arc**: `SET_PLAN_V3['arc']` False, `SETPLAN_SET_V3['arc']` the return only.
- **The harp gate** (`POST_HARP_V3`): after v2's no-harp-after-the-climax pass, a role with no notes or a harp with
  fewer than 4 is removed from `plan_o.parts`. An empty part used to stay a track (`plan_o.roles()` lists every role
  with parts) and failed the silent_node gate (o19a slot 2).
- Round o20's result (ROUNDS.md "Round o20"): per piece -0.04 se 0.24 (-0.17 se), 9 won / 7 lost - level, life
  -0.32 the only loss; set level (`songs/_blind/set_round.py`, 3 set pairs x 7 judges) new kept 11 of 21 = 0.52,
  95 % CI 0.30-0.74. **SET_PLAN stays off** (the rule needed the set CI above 50 %).
  - The o19a complaints are gone (choppy sections, the long fades, the crisis, the post-climax harp); the new one is
    the long static block (2.06 vs 0.75 lines per packet).
  - Two set pairs went to v3 11 of 14; the third went to off 7 of 7 on an all-major programme with F major three
    times, two rondo twins and six loud endings - set memory on the mode, the realised bar plan and the ending's
    loudness are next.
### Round o21: FUGUE v2 - the fugato accompanied, its counter-subject heard, its subject the opening theme (`FUGUE_V2`, off)

- **Switch**: `FUGUE_ON` is now v2 (`FUGUE_ON_V1` + `'v2': FUGUE_V2`; `shared_plan.py --flag fugue`); o19b's is
  `FUGUE_ON_V1` (`--flag fugue1`); None (the default) stays master's `Writer.fugato`, bit-identical.
- **The subject** (`Writer.fsubject2`): the first theme's opening S bars as heard (theme1: the motto and its
  continuation, moved into the fugato's key and mode); a long landing or a rest held a beat and continued by
  fsubject's tail (`fsubject(head=, S=)`); the scherzo's S = 2 compound bars (four 3/4 bars).
- **The entries**: the distance drawn per piece (`FUGUE_V2['gap']`, bars added to the subject's: 0, a codetta bar -
  the subject's head again a step on -, half a bar of overlap, a bar in a 3-bar subject; an overlap only where
  subject and answer clash at most 'overlap' by `voicing.cp_cost`); a codetta that would leave no final entry closes
  up; no episode over `ep_max` bars (a half cadence after it).
- **Never one voice alone**: a pedal under each exposition entry (the entry's tonic, until the bass voice enters,
  the texture's 'pedal' role) and a soft string pad until the third entry (the 'harmony' role, trimmed); the marks
  rise entry by entry (`marks` at each entry: mp, mf, mf, f - capped under the climax by LOUDEST) and every voice
  `grow` velocity steps per entry begun (`_fugue_offs`).
- **The counter-subject heard**: `cs` velocity steps over the free voices (`other`), doubled in its own colour (the
  texture's 'counter' role: clarinets / bassoons, oboes / flutes ...); a restatement that clashes by more than
  `cs_cost` is free counterpoint instead; the CS also follows a codetta / an overlap (`cs_lead`).
- **The fast feels** (`cap`: vivace 12 bars, scherzo 6 compound bars = 12 3/4 bars, `_fugue_cap`): the surplus to
  the development's dialogue; the dance accompaniment under the entries (`fugue2_dance` / `fugue2_dance_winds`: a
  staccato ostinato in the violins II / violas).
- **The textures** (orchestration.py): `fugue2_mixed`, `fugue2_horn`, `fugue2_reeds` (o19b's choirs + pedal, pad,
  counter), `fugue2_dance`, `fugue2_dance_winds`.
- **At the summit** (`Writer.fug_return`, `ret`): the subject in the bass of the first peak block after the fugato,
  augmented x2 (the scherzo: as written), in the climax's key; its start bar (0 / 2 / 4) and octave the least
  `voicing.cp_issues` cost against the climax's melody plus its strong-beat non-chord tones, then `voicing.repair`
  within 2 semitones (the first note fixed); it replaces the bass line over its span.
- **Result** (songs/_blind/ROUNDS.md "Round o21"; the plan forced to a fugato in all 16 slots for both codes):
  +0.38 se 0.13 (2.9 se), 9 won / 3 lost - over the bar (MERGE, on the o21 branch). Every dimension is up (life
  +0.49); masterpiece 3.72 / 3.58 / references 5.57. Lone / thin fugato sentences 31 -> 9, "no counter-subject"
  10 -> 2. Still open: the summit's return heard in 1 of 16 pieces, the long thin dialogue after the capped fast
  fugato, the counter-subject's unison doubling.

### Round o22: SET_PLAN v4 - a change at every join, the set's memory on mode / key / bar plan / endings / ladder (`genres.symphony_setplan`, MERGE per round o22)

- **Switch**: `SETPLAN_VERSIONS` gains 4: `SET_PLAN_V4`, `SETPLAN_VERSION = 4`, `SET_PLAN_ON = SET_PLAN_V4`.
  `shared_plan.py --flag setplan` is v4, `--flag setplan3` o20's v3, `--flag setplan2` o19a's v2. v4 uses
  `SETPLAN_SET_V4` / `SETPLAN_MEMORY_V4` / `SETPLAN_ARC_V4` / `SETPLAN_SHAPE_V4` and `plan['set_bars']`
  (`SETPLAN_BARS`). Off and v3 are bit-identical to master (40 of 40 symphonic pieces each, 24 of 24 protected).
- **The joins** (`JOIN_V4`): `_merge_rows(..., parts=True)` records the blocks a merged row folded in
  (`over['parts']`); after the placement (`_place_v3`, o20's mechanics as a function) `_split_joins` gives each part
  its share of the row's bars (at least 4 song bars, even internal bars) - the later parts are their own material
  blocks (their own writer: the restatement, the closing group, the episode, the next variation, the trio's growing
  repeat) marked `joined`. `build_symphony` puts a joined block into the SONG SECTION of the block it joins (the
  packets' layout and the report see one section), and `orchestration.plan_blocks(..., change=joined)` never gives it
  the texture of the block before it (the kind's own textures added as alternatives at 0.3).
- **The fragmentation's shape** (`FRAG_V4`, `plan['set']['frag']`, memory 3): `Writer.sentence` steps its kernel
  sequence by rise (the old one-step-a-bar ladder) / wave / terrace / fall / arch. The ladder was the sentence's,
  not the build's: over o20's 16 slots the 12-bar t1 climbed 6-7 bars in a row in 7 v3 pieces, the reharmonised
  climax 6-10 bars.
- **The bar plan by the slot** (`draws['form_seed']`, `_form_seed`, `bar_plan`): the phrase lengths, the slow
  introduction's bars, the layout fallback and the coda pick are seeded by the slot's form seed and key, so
  `symphony.bar_plan(genre, slot)` returns the song bars per section the piece will play (within 1-2 bars: an elided
  cadence) and every best-of-N candidate plays them.
- **The set planner** (`composer.set_plan` / `_slot`): `key_max` 2 (no key three times over all meters),
  `mode_quota` (2, 8) with `major_run` 3 (a slot the quota needs, or after three major slots, takes a minor / modal
  mood and mode), `end_alt` (a dissolving coda never after one, never three loud in a row; the slot takes a mood with
  the coda it needs - `_end_need` / `_end_coda`, the slot's `coda` is the realised one), `SETPLAN_SHAPE_V4` (a feel's
  layout once per set), `_set_bars` (a realised bar plan sharing more than 0.4 of its sections, within a bar at one
  index, with an earlier slot's redraws sections / peak_at / form_seed / phrase / span / layout, up to 48 tries).

### Round o23: TECH - the playing techniques as musical events (`genres.symphony_tech`, off)

HUMAN_FEEDBACK 2026-10-24: "I feel techniques are missing, e.g. plucked strings". `--flag tech` (shared_plan.py);
off is bit-identical (the 40 symphonic pieces and the 24 protected hashes).

- **The palette** (`symphony.TECHNIQUES`): 13 techniques, each with its dramatic function, its places in the form
  (block kinds; 'peak' / 'pre_peak'; a 'soft' cap on the block's marks; 'fast' feels only) and the feels' affinity:
  `pizz_choir` (the whole string choir plucked under a woodwind tune - the texture `orchestration.TEXTURES
  ['pizz_choir']`, violins I on the beats an octave up), `pizz_walk` (basses / cellos walking pizzicato in beats:
  `_walk`), `trem_build` (the retransition's held strings tremolo), `measured_trem` (the development's held chords as
  repeated spiccato notes: `_restrike`), `trill` (woodwind trills on the climax's held notes - a flute over the tutti
  - and on a cadence's penultimate note: `_trill`, ~85 ms notes, the turn at the end), `harp_gliss` (a scale up into
  the climax / a return: `_gliss`, ~0.75 s), `ww_chatter` (woodwind staccato answering the strings' ostinato every
  other two bars), `muted_brass` (horns / trumpets muted in the quiet blocks), `stopped_horn` (muted ff accents on
  the development's phrase starts), `harmonics` (the violins' held notes in a soft coda), `col_legno` (a fast
  block's string ostinato), `sfz` (sforzandi on the development's chords every other bar), `timp_roll` (a timpani
  roll crescendo over the bars into the climax).
- **The ranking, with the set's memory** (`tech_rank`): a weighted draw without replacement (weight x the feel's
  affinity, x 0.15 / 0.45 for a technique featured by the slot before / the one before that); the set plan carries
  it per slot (`plan['set_tech']`: `slot['tech']`, its own dice - the other draws unchanged), a piece without a
  plan draws its own. The first `TECH_ON['feature']` (4) techniques that the piece's blocks allow are written
  (`_tech_pre` before the orchestration: the pizzicato choir's block; `_tech_pass` after it: the parts' articulations
  and notes); the events are `song.tech_events`, the shares `symphony.tech_stats(song)`.
- **The sounds** (`orch.TECH_SOUNDS`): the horns and trumpets gain 'muted' - the VSCO 2 CE (CC0) muted horn (A#2-F5)
  and straight-muted trumpet (A#3-C6) inside the SSO keyswitch instruments, on the SSO dynamics curve, level-matched
  at mf (`orch.MUTES`: horns -3 dB, trumpets -1.4 dB under the open sustain); the SSO section strings' col legno
  (+6 dB: ~3 dB under the staccato) and harmonics (+1..+4 dB: 1-3 dB under the sustain) brought up (`TECH_GAINS`).
  Everything comes from the publishable packs (SSO CC Sampling Plus, VSCO 2 CE CC0); nothing needs a
  non-publishable pack. Not built: sul ponticello, con sordino strings, fp (a lane dip after the attack), string
  portamento.
- **The packets** (`make_packets_orch.ARTS`, `AGENTSOUND_PACKET_ARTS=1`): each attack's keyswitch as a mark - `[pizz]`
  for a bar, `x[trem]` for one attack, and per section the role's techniques - so judges can read the articulations
  (round o23's packets, the references' too).

### Round o24: SHAPE - the macro shape per piece and TECH v2 (`genres.symphony_shape`, off)

o23's judges: template flags 44 per packet in both codes against the references' 9 - one shape in every piece (soft
opening, staccato middle, tremolo build, unison tutti at 78-85 %, coda); measured on o23's 16 renders: the loudest
section's centre at 0.70-0.85 in 16 of 16 (sd 0.033). `--flag shape` (shared_plan.py); off is bit-identical (40 of 40
symphonic pieces, 24 of 24 protected hashes). Apply after `symphony_tech` and before the set plan is drawn.

- **The macro shape** (`symphony.MACRO` / `MACRO_ON`; `shape_draw`, `shape_slot`): per set slot (`plan['set_macro']`:
  `composer.set_plan` calls `shape_slot` after master's draws, on its own dice - the plan's other keys stay master's)
  `slot['shape'] = {'open', 'arc', 'climax', 'end', 'at'}`:
  - `open`: `motto` (the call, no slow introduction), `solo`, `soft` (mist / source), `medias` (the opening row
    left out, the first theme f in `tutti_drive`, past the LOUDEST 'pre' cap), `dance` (the opening left out, the
    first theme p in the woodwinds over the `pizz_choir` texture - the fast feels; the piece's pizzicato choir);
    the openings a layout allows by its first row (`MACRO_ON['opens']`).
  - `arc`: the climax's centre `at` - `classic` 0.76-0.8, `mid` 0.64-0.7, `early` 0.56-0.62 (the coda a second
    summit f - ff, `_macro_marks`), `late` 0.86-0.9 (the second theme's return moved before the build), `twin` (an
    exposition block near 0.42 made an f summit), `inverse` (the quiet climax, where the mood has it);
    `_place_v3` takes `at` with the floor 0.5 and longer post-climax blocks for `early`. `shape_slot` checks the
    realised centre (`_realized_peak`: form_rows + _place_v3) and bans an arc the layout cannot reach (> 0.07 off).
  - `climax`: brass / strings / chorale / `dialogue` (new `CLIMAXES` entry, texture `apex_dialogue`: the tune in the
    violins and woodwinds against the trumpets' own line, trombones under it) / `quiet` (the inverse arc).
  - `end`: by the slot's coda kind (master's `end_alt`) - triumph: `loud` / `cut` (no coda row: the end straight
    after the climax or the return, ff after a climax); dissolve: `dying` / `surprise` (the block before the coda held
    f, the coda subito pp).
  - The set's memory over the WHOLE set: no dimension as the slot before's, no value over ceil(n / its choices), no
    (open, arc, end) twice; relaxed in steps when nothing is left.
- **TECH v2** (`TECH['v2'] = TECH_V2`, 3 techniques a piece - 13 techniques x 2 can't feed 8 x 4):
  - `tech_rank_v2` (`slot['tech2']`): a technique featured at most twice in a set (over the cap only to fill a
    piece), the pizzicato choir (or a dance opening) never within 3 slots, the trill's crown on a climax once per set
    (`slot['tech_crown']`), the harmonics x 2.5 in a piece that ends softly. The pass tries only the first 4 ranks.
  - The material: the pizzicato choir on a first-theme block first (`pizz_kinds`), the violins I plucking the tune;
    the col legno's top part plays the motto's head on the chords (`_col_legno_motto`).
  - The harmonics' home (`_harmonics_v2`): the soft last block, the dissolving coda, a quiet chorale - the held violin
    notes there, else a held halo (79-91) in a free violin part.
  - The harp glissando into the climax with the build's last beats thinned to the bass / timpani / harp (+4 dB),
    elsewhere only into a soft (mf) arrival.
- **Result** (ROUNDS.md "Round o24"): per piece -0.09 (se 0.20), sets 14 of 28 (CI 0.33-0.67) - not merged, the flag
  stays off. The loudest section's spread doubled (sd 0.077 vs 0.038) and the openings got louder, but the judges
  still hear every climax at 71-90 % and the early arc never lands under 0.63.

### Round oc1: CHOIR - a real SATB choir as events of the form (`genres.symphony_choir`, off)

HUMAN_FEEDBACK 2026-10-24: "I think the choir will help the orchestra to greatness - it gives goosebumps much more
surely" (and 2026-10-19: a choir must sound like MANY people). `--flag choir` (shared_plan.py); off is bit-identical
(the 40 symphonic pieces and the 24 protected hashes). The module is `endless/choir.py`; symphony.py has three hook
lines (the plan into `tune.arrange`, `choir.prepare` after the orchestration, `choir.sing` after the parts).

- **The sound** (`orch.vocalset_choir`, bandlib/orchestra.py): the vocalset-choir pack (SATB wordless vowels summed
  from the 20 real VocalSet singers, CC BY 4.0 - the build's credits print the attribution; ranges S C4-G#5, A A3-F5,
  T B2-G#4, B A2-F4, nothing lower: the low bass stays with the orchestra), one track per part and vowel in the band's
  hall with its own send, the prototype's eq and a gentle treble cut for the distance (songs/_choir_proto). It returns
  an `orch.Choir` (lane 'dynamics': the p / mf / f layers crossfade on CC1, early speaking starts, a messa di voce on
  long notes). The pack's layers are level-matched, so the written dynamics also move the gain (`CHOIR['level']`: an
  expression point per onset, 0.07 dB per velocity step under 105).
- **The plan per piece** (`choir.PLANS`, `choir_draw`): none / summit / acappella / halo_summit / halo / coda /
  halo_coda, weighted per feel (FEELS), with the set's memory (`plan['set_choir']`: never the slot before's plan,
  0.45 for the one before that's, x 0.5 for a plan sharing an event with the slot before's, never two pieces without
  a choir in a row): the choir sings in ~75 % of the pieces, the summit in ~60 % of those.
- **The events** (`choir.EVENTS`, placed in the piece's blocks by `_places`, written by `_write`): `summit` (the
  peak block's most singable line - the theme, or the augmented motto / counter-line when the theme runs - in the
  sopranos on "ah", a quiet climax "oo" -> "oh"), `lead_in` (the build's last two bars on "oo"), `acappella` (4-8
  bars before the final build: the block's own line in the choir, oo -> ah phrase by phrase, p -> mf; the orchestra
  leaves those bars but for the bass line, 8 velocity steps softer: `_thin`), `halo` (a soft "oo" over the
  sparsest quiet block - the second half of a long one -, no voice a semitone from the line, under a high line),
  `coda` (the triumph coda's line on "ah", or the dissolving coda "oh" -> "oo" through the last chord).
- **The writing**: the line's long notes (`_skeleton`: notes under 0.42 s join the note before), moved by octaves
  into the sopranos' range with the contour kept (`_soprano`), the harmony from the chart voice-led under it in
  alto / tenor / bass (`voicing.voice`, the soprano fixed); breaths at the phrase ends (4 plan bars, 2 in the a
  cappella) and where the line rests; notes over 5 s re-attacked, staggered per part. Velocities from the piece's
  dynamics map (`Score.sing`); the stats are `choir.choir_stats(song)`.
- **The packets**: the choir's tracks as four roles `choir_S` / `choir_A` / `choir_T` / `choir_B` with the vowel
  as each attack's mark (`[ah]`, `[oh]`, `[oo]`).

### Round oc2: CHOIR v2 - the choir sings the theme (`genres.symphony_choir(True, v2=True)`, off)

Round oc1's fixes (ROUNDS.md "Round oc1": the summit "ah" only doubled the brass chords, the lead-in "oo" -> summit
"ah" pair became a formula across a set, the a cappella was the best event, halos held vowels). `--flag choir2`;
`choir.CHOIR_V2` on top of `CHOIR_ON` (`CHOIR['v2']`), v1 (`--flag choir`) unchanged, off bit-identical.

- **The theme sung** (`_line(melody=True)`, `_skeleton` with `line_min_s` 0.2 s): the peak block's melody, in
  its own rhythm, in the sopranos. The summit's texture is drawn per piece (`CHOIR['tex']`): `unison` (the theme in
  sopranos and tenors in octaves, alto and bass the harmony voiced once per chord and held: `_unison`) or `hymn`
  (the theme harmonised SATB). 40 % of the summits (peaks of 8+ bars) enter at the peak's second half, not on the
  arrival. Under the sung theme the brass / woodwind parts doubling a line play softer (`_soften`, `CHOIR['under']`:
  12 / 6 velocity steps).
- **The gestures' set memory** (`PLANS_V2`, `choir_draw`): an event at most `caps[event]` times in any 8 slots
  (summit 3, a cappella 3, halo 2, coda 2, lead-in 1), a plan's weight x 0.7 per earlier use of each of its events;
  the lead-in only in the rare `swell` plan. The a cappella twice as likely (`acappella`, `acappella_coda`), at
  +3.5 dB. The choir sings in ~66 % of the pieces.
- **Phrases, not held vowels**: the halo SINGS the quiet block's line (a block with one; the whole block up to 12
  bars, else its second half), the line's own instrument 14 velocity steps softer; the coda and the a cappella fall
  back to any upper part's line (`relaxed`) before held chords.
- **Packets** (`make_packets_orch`): the orchestration and "roles per section" lines count an attack in the bar
  the notation prints it in (`EARLY`: the choir's early speaking starts no longer list it in the section before).

### Round os1: SOLO - the solo players for expression (`genres.symphony_solo`, off)

User question 2026-10-25: "do we use single instruments or sampled groups? with single instruments we could get more
expression" - every role was an SSO section program (1st Violins, Flutes a2, Oboes, Horns a4 ...), so an exposed oboe
theme sounded like a section. `--flag solo` (shared_plan.py); off is bit-identical. `agentsound/endless/solo.py`; the
hooks are two lines each in `symphony.compose` / `build_symphony` and `composer.set_plan`.

- **The solo players** (`orch.SOLOS`, `film_orchestra(solos=...)` / `symphony_orchestra(solos=...)`, opt-in: the
  preset tables and `role_table` are master's without it): flute_solo, oboe_solo, clarinet_solo, bassoon_solo,
  horn_solo (the VSCO 2 CE single players of the chamber orchestra - `_VSCO_WINDS`, shared with `_chamber_table` -
  as legato players, dynrange 20 dB: `SOLO_DYNRANGE`), violin_solo / cello_solo (the string quartet's violin 1 and
  cello), violin_concertmaster (the quartet's violin 2, SSO Violin Solo 2). Seated at their section's pan, 0.5 dB
  drier. `SOLO_GAIN` (relative to the section's fader, measured on one legato line at mf, track RMS): the winds level
  with their section, the solo strings 2 dB under, the concertmaster 12 dB under the violins I.
  `ROLE_TRAITS` / `scoring.PHRASING` carry them (a principal shapes a phrase more: 0.7-1.0).
- **The pass** (`solo_pass`, after the techniques): (1) a woodwind / horn part with function melody / counter, a
  line, one note at a time (<= 10 % chords; the top note kept), not doubled at the unison / octave by another role
  (<= 50 % of its notes), in a block of <= 10 roles, not the climax, its top mark <= f (horns mf) -> the principal;
  (2) the string solo EVENT drawn per set slot (`slot['solo']`: violin / cello / none, `solo_slot` - never the same
  solo twice in a row, never three pieces without one): the most lyrical soft violins I (cellos) theme block (top
  mark <= mf, <= 8 roles, notes of 0.5 s+ on average, no tutti / drive / march / pulse / walk texture; `t2`, `slow`,
  `intro` ... first) goes to the solo violin (cello) - the other kind's when the drawn one has no block -, the
  strings under it 10 velocity steps softer, the line's doublings left out; (3) the concertmaster on every slow soft
  violins I melody (<= mf, 0.45 s+ notes, not the event's block); (4) the score's player rules (`SOLO['rules']`):
  swells from 1.0 s, 2 dB + 1.2 dB/s up to 7 dB, on 85 % of the long notes; string legato overlaps 55-90 ms.
- **Measured** on set 121000 (16 slots, no audio): 3-10 wind solos a piece, the event realised in 6 of the 11 drawn,
  the concertmaster in 13 of 16 pieces.
- **Result** (ROUNDS.md "Round os1"): per piece +0.51 se 0.12 (13 / 16 slots won; performance +1.10), the sets
  agreed 28 of 28 over two passes (CI 0.88-1.00), expression +2.62 - to merge. The flag is still off on this
  branch; turning it on is the merge step.

### Round ox1: COLOUR - a guest instrument per piece (`genres.symphony_colour`, off)

HUMAN_FEEDBACK 2026-10-25: "what I miss in the orchestra are more exotic instruments like a church organ or an
acoustic guitar - that can be beautiful too", "above all increase diversity". `--flag colour` (shared_plan.py); off
is bit-identical. The module is `endless/colour.py`; composer.set_plan has one hook (`guest_slot`), symphony.py three
(the guest into `tune.arrange`, `colour.prepare` after the orchestration / the choir, `colour.play` after the parts).

- **The draw** (`guest_draw`, `plan['set_guest']`): none / organ / guitar / harpsichord / celesta / bells, weighted
  by the feel (`FEELS`: the guitar in the andante / river nocturnes, the harpsichord in the allegros / vivaces, the
  celesta in the scherzos), never the slot before's colour (nor two without), at most ceil(n / 4) of a colour per
  set, the one two back x 0.35; ~15 % of the pieces without. A colour's plan (its events) and, for the organ, Burea
  or Pitea, drawn too. The guest shapes the slot: the guitar / harpsichord pieces chamber size, the organ full (where
  the mood has the size), the guitar's tempo at most 30 % into the feel's range.
- **The sound**: `orch.church_organ(..., hall=)` (the used registrations, seated in the orchestra's hall, send -14:
  the pipes carry their church) and `orch.guests(song, roles, hall=)` (GUESTS: the FreePats nylon guitar, the VCSL
  harpsichord / glockenspiel / tubular bells, the SSO celesta - all publishable; the credits print Lars Palo's CC BY-SA
  attribution), played by an own `orch.Score` on the piece's dynamics marks.
- **The events** (`_places`, written by `_organ` / `_guitar` / `_harpsichord` / `_celesta` / `_bells`):
  organ - `opening` / `interlude` (the organ alone: soft flues voice-led under a solo stop - cornet / flute / reed -
  and the soft pedal, the swell breathing), `swell` (the swell's chorus + pedal under the build, the box opening),
  `summit` (full organ + the 16' reed pedal, the climax's line as the chorale's soprano; a quiet climax on the
  principals), `amen` (the last bars on full organ, soft flues for a dying end); guitar - `opening` (alone: the tune
  with the thumb's bass, or arpeggios), `serenade` (a quiet block: `guitarist.arpeggio` fingerstyle under a solo wind,
  then the guitar's own tune; brass / percussion / harp / figures out, the bass plucked, the strings a soft pad),
  `envoi` (the soft ending's arpeggios, the last chord let ring); harpsichord - `continuo` (chords on the beats over
  the bass line: the fugato, the first theme, the recapitulation; 8' + 4' in the tutti), `concertino`
  (`organ_vocab.toccata` 16ths under the tune, the orchestra its strings only), `cadence` (the last chord rolled);
  celesta - `sparkle` (the theme two octaves up), `glitter` (the glockenspiel on the loud return's long notes),
  `twinkle` (an arpeggio into a quiet block / the end); bells - `peal` (the summit's downbeats on the line's notes),
  `toll` (the coda: rounds down the scale, or a dying tonic).
- **The packets** show the guests as roles (`guitar`, `harpsichord`, `celesta`, `glockenspiel`, `bells`,
  `organ_<registration>`); stats `colour.colour_stats(song)`.

### Round o24b: TECH2 alone and SHAPE2 (`genres.symphony_tech2`, `genres.symphony_shape2`, both off)

o24 split so each half is judged on its own: `--flag tech2` is TECH v2 without the macro shape, `--flag shape2` the
macro shape fixed (judged as shape2 + tech2 against tech2). Off is bit-identical (40 of 40 symphonic, 24 of 24
protected).

- **TECH2** (`plan['set_tech2']`: `composer.set_plan` -> `symphony.tech2_slot`, after the macro shape when there is
  one, on its own dice): `tech_rank_v2` with the whole set's memory; without a shape a dissolving coda is the soft
  ending the harmonics are weighted up for.
- **SHAPE2** (`symphony.MACRO2_ON` = MACRO_ON + `MACRO2_V2`):
  - The early / mid arcs (0.5-0.56 / 0.57-0.62) move the climax's MATERIAL (`_macro_move`): the development's blocks
    before the retransition go after the climax as its aftermath (f falling to mp, capped f). The second theme's
    return stays after them (`_place_peak` 'norev'), and the coda has no second summit.
  - The cut ends on the climax (the returns after it moved before the retransition), in the tutti's hammered chords
    at ff (`sh_tex`). The loud ending's coda and last bars are at ff, level 1.0.
  - The climax types have their own textures where the climax's material has none: `apex_low` (the tune in the
    cellos / violas / horns under the violins' run), `apex_chorale2` (the brass choir's chorale in a string tremolo
    shimmer), `apex_dialogue2` (the dialogue over a held bass).
  - The set's memory (`_shape2_extras`):
    - `shape['motto']`: a motto rhythm family heard before in the set is replaced by the least heard one.
    - `shape['tex_t1']`: the first theme's texture at most twice a set, never one of the two slots before.
    - `shape['bass_figs']`: two pumping-bass figures a piece, the least used first.
  - The in medias res opening is without the pumping drive (motto_bass / dialogue_brass).
- Result (ROUNDS.md "Round o24b"), both not merged:
  - TECH2 alone is neutral per piece (+0.1 se), with a small set gain that is not significant (agreed 16 of 25).
  - SHAPE2 really moves the peaks (sd 0.139, down to 0.46) and wins the set clearly (agreed 25 of 25, variety
    +1.23), but it loses per piece (-1.86 se). The aftermath after an early climax is too thin.

### Round op1: POLISH - the choir / solo / colour features fixed (`genres.symphony_polish`, off)

The three features merged on by default (CHOIR v2, SOLO, COLOUR) with their judges' top fixes, one switch:
`--flag polish` (shared_plan.py; it needs the three on - master's defaults). Off is bit-identical. The code sits in
the features' modules (`solo.SOLO_POLISH`, `colour.COLOUR_POLISH`, `choir.CHOIR_POLISH` / `PLANS_POLISH`) and
`composer.title_slot`; hooks: one in `composer.set_plan` (`plan['set_polish']`: the title's label, the summit's
texture), three small ones in symphony.py (the title's `prefix=`, `tune.arrange['choir_tex']`, the concertmaster's
fader `solo.polish_band`).

- **SOLO**: the concertmaster's fader +4 dB (os1: 17 dB under the violins I); no "parade" - at most 2 blocks in a row
  with an exposed solo player (wind solo, the string event, the concertmaster), the third plays on the section (the
  event's block always kept; `solo_events` 'section'); the cello event finally fires: the cellos carry no 'melody'
  part, so the cello solo sings the violins I's theme an octave or two down (median E3-E4), else the cellos' own
  counter-line, the section's line under it out.
- **COLOUR**: the coda always has the guest (the guitar over a loud coda: a 2-bar `farewell` before the last tutti);
  a stretch of more than 30 % of the piece without the guest gets a RETURN (at most 2, 10 % apart from the other
  events, the development / recap first): the organ's solo stop on the tune over soft flues (`solo`, the orchestra
  hands the tune over), the guitar's own tune (`reprise`), the continuo, the celesta's doubled theme, a distant bell
  (`hint`); the bells always hint before the climax (the build's first bars); the signature gestures drawn per piece
  with the set's memory (`guest['gest']`): the celesta's closing arpeggio rise / fall / wave / chime, the bells' coda
  peal scale / rounds (plain hunt, the last row struck together) / motto / toll, the harpsichord's last chord rolled
  / flourish / with the orchestra / broken; the guitar piece keeps the full orchestra (its climax has the brass); the
  celesta +2.5, glockenspiel +1.5, guitar +2 dB.
- **CHOIR**: at the sung summit the orchestra's melody instruments leave the theme (`_leave`: a melody / doubling
  line on the sopranos' pitch class at 40 % of its onsets holds chord tones instead, brass 6 / the rest 3 steps
  softer), the summit +2 dB; the summit's texture with the set's memory (`choir_slot`: the last summit's texture
  kept 25 %, else the other - unison / hymn about half and half); `PLANS_POLISH` (the summit rarer, an a cappella
  alone, halo / coda plans likelier) with the caps summit 2, a cappella / halo / coda 3 per 8 slots; no halo shorter
  than 4 bars.
- **Titles**: `composer.title_slot` - a form label ("Overture:", "Symphonic Dance:") at most once in any 4 slots,
  never the set's last label twice in a row (`slot['title_form']` -> `composer.title(prefix=)`).
- Result: ROUNDS.md "Round op1".

### Round o25: SHAPE3 (`genres.symphony_shape3`, off; with `--flag tech2`)

SHAPE2 with o24b's three fixes (`symphony.MACRO3_ON` = MACRO2_ON + `MACRO3_V2`). Off is bit-identical to master.

- **The aftermath after a moved climax** (`_macro_marks`): the moved development blocks are a release and a second
  build. One block goes f, down to mp, back to f; with two or more, the first falls to mp and the last rises mp -> f.
  The first return after them ('rise': recap2 / recap / river / ...) is a rising theme return at f in the driving
  tutti (`tutti_drive`), under the climax's ff.
- **The chorale climax** (`apex_chorale3`): the brass choir's chorale, with the violins striking the motto's rhythm
  (the ostinato figure 'motto') and a walking bass (the bass figure 'walk', `_walk_long`).
- **The late arc / the cut ending** (`_macro_rows`): no second-theme return before the build, and the build
  (retrans) at most 6 bars - a shorter way into the climax. The cut's end chords are `hammer_motto`: the tune on
  top, the horns and trombones in the motto's rhythm.
- The choir's summit and the guests' summits key on the peak block, so they follow the moved climax. The soloists
  avoid the climax and the tutti return.
- Result (ROUNDS.md "Round o25", SHAPE3 + TECH2 vs master): per piece -0.33 se (form and life no longer lose), sets
  agreed 18 of 20 (CI 0.70-0.97), variety +0.80 - merge by the rule.

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
