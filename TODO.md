# TODO: open findings

Grouped by the tool that owns the fix. Each entry says where it came from, with numbers where we have them. Remove an
entry in the same commit that fixes it; add new findings here instead of losing them in a report. Fixes follow the
user's rule: KISS - a preset / patch / chain / default / data table before new code, the shared tool before song code.

## Endless generators (`agentsound.endless`)

- **The new-age bloom - open points** (2026-10-15, `plan['bloom']`, docs/PIANIST_RULES.md "The bloom"; renders
  `songs/_endless_piano/out/bloom_v1`). Not yet heard by the user. Open:
  1. The right hand's density in the bloom depends on the composed melody. Hand-offs need a note held from the half
     bar to the downbeat, and the weave needs holds of a beat or more. A busy build melody gets few (`rh_peak_den`
     1.3-1.5 in about a third of the candidates). The bloom could re-rhythm its melody instead: the head in
     diminution (docs/PIANIST_RULES.md "Ideas" #1, #7).
  2. `hand_meet` stays at 0.04-0.2. The new-age melody rarely drops below G4, so the left hand's lift has little
     room. A tenor statement (Ideas #15) would open the register.
  3. The breath gate: the weave lowers quiet1 by 0.02-0.04, and more candidates fail at 0.25.
  4. The learned student: its decoded tunes bloom by their seed (the bloom is not in the arrangement record). A
     re-export would let it learn where blooms sit.
  5. The hand-written references score lower under the new metrics (`tempo_push` 1.0-1.07, `flow32` 0-2.9).

- **new-age-epiano: the DX7's level barely follows velocity** (2026-10-11, the first 30-minute set, seed 2000):
  E.PIANO 1 moves its tine, not its level (0.5 dB per 10 velocity steps; a grand ~2.2), so the genre stacks three
  velocity-fade-in voices of the patch for the right hand (1.6-2.5 dB / 10 measured over the set). Still marginal: 5
  of 14 rendered tunes failed the gate on flat_dynamics (3.6-4.3 dB per phrase, want 4.5) and the 3 voices x
  crossfade instances make the render ~1x real time (up to 2.3x). KISS fix in the owning tool: a dx7 param that maps
  velocity to output level (dB range) - then one voice per note. Also: the 224XL chamber's licence is unclear
  (private listening only; a clear-licence hall for publishing), brilliance +7.3..7.8 dB vs the piano profile in 3 of
  9 tunes (an e-piano has little sub / bass: the relative balance reads bright; an e-piano profile?).

- **Endless score - the learned-generator roadmap (feat/endless-score; stage 1 done)**. Stage 1: `composer.score`
  (one number 0-100 from the notes: the blind tells + breath + body + the lead sheet's checks, weighed by the DATA
  table `genres.SCORES` per style, hard rules capping) and best-of-N in the runner (`endless --candidates N`, default
  8; `python -m agentsound score`). Open: (1) classical / lofi tables are PROVISIONAL (no composed reference of the
  generated kind; the generated lofi tunes score 91-100, so best-of-N rarely changes a lofi pick) - write one
  reference per style (as pro2 for jazz) and measure it; the real etudes (Chopin nocturne 47, Satie Gymnopedie 64)
  score low under the classical table: it describes OUR nocturne / salon waltz, not classical piano. (2) Flattened
  right-hand velocities cost a reference only 3-7 points (the note-energy measures are coarse; the render gate's
  flat_dynamics catches a flat lead). (3) The score is not the ears: it rewards closeness to the references, so a
  tune that is better than them in a new way loses points - the user / judges stay the final check; next blind round
  compare best-of-8 winners against first seeds. **Stage 2**: a learned scorer - the same metrics as features, the
  weights (and ranges) fitted to the blind judges' verdicts and the user's reactions (HUMAN_FEEDBACK) instead of hand
  set (`score(table=)` takes a fitted table); collect pairwise preferences per round (which of two tunes is
  better / composed). **Stage 3**: a learned note-level generator (phrase / bar proposals ranked by the stage-2
  scorer, then trained on the winners), keeping the rule composer's plan (form, arc, harmony) as its conditioning.

- **Set variety budget: the RL reward, the endless runner, the new-age climax** (2026-10-12, the HUMAN_FEEDBACK
  "so nicht sehr abwechslungsreich" on three learned-generator samples; docs/LEARNED_GENERATOR.md section 10). The
  learned generator has a set measure (`learn.evaluate.variety`: the normalized entropy of mood, feel, form, mode,
  key, tempo, climax position and pitch, and ending across a set) and a set spread (`learn sample --spread`). Open:
  (1) the GRPO reward (`learn/rl.py`) scores pieces one by one. Give a group a variety term, or sample groups with
  spread headers, so RL cannot narrow the header. (2) The endless runner's `set_plan` follows the energy arc. It
  should also keep a coverage budget (moods and modes taking turns over a set; `sample.spread_headers` is the
  reference) and report `variety` per set. (3) The new-age teacher has no climax variety. Every tune peaks in part
  C, bar 4 or 5 (87-91 % of the head), on C6 (63 %) or B5 (34 %), because `melody.peak` is C6 for every mood. The
  fix is a per-mood `peak` / `center` and more than one climax place in the genre spec. Then re-export, and the
  student learns it. Until then a set's variety tops out at about 0.72. (3) done 2026-10-12 (ROUNDS.md "After r5"): the set draws
  layout / climax kind / register shift per slot, the climax part per tune; teacher variety 0.68 -> 0.85 - re-export the teacher.

- **Learned generator after the arrangement tokens** (docs/LEARNED_GENERATOR.md sections 12-13; phases 1-3 done:
  schema-2 data `data/tok3` / `data/full3` from the widened teacher, `runs/base3w` warm-started from base2,
  `runs/top30_3`; the student follows the teacher's arrangement at its shares. Blind round 3: student 6/40, teacher
  4/40, composed 36/40; student vs teacher p = 0.74). Open:
  - (1) The judges' tells are the teacher's template. Widen the new-age players' / composer's vocabulary:
    - developed returns (reharmonized, re-rhythmed, a new continuation) instead of verbatim copies;
    - climax material derived from the motif, with a harmonic event;
    - a key plan (bVI / relative / a step up);
    - several intro / interlude / coda frames;
    - a one-bar harmonic rhythm in the waltz.
    Teacher side done 2026-10-13 (ROUNDS.md "After r8: widening the teacher", r9 / r10): `vary` / `key` per section
    (tokens `AVary` / `AKey`), climax 'grow', drawn frames / dynamics, 'na' / 'na3' cells, wider harmony; a1_copy
    0.24 -> 0.09, block_copy 0.21 -> 0.13, chords_n 21 -> 26, climax_chart 0.39 -> 0.18. Student side done
    (section 13). The round-3 judges' remaining tells are the teacher's (section 13.7):
    - climax key blocks without a pivot or a way back (`AKey` / 'grow'), and neighbour-cell climaxes instead of the
      transformed theme;
    - phrase ends tied over the barline into a bar with no right hand;
    - form templates (the "climax 9 | inter 2 | A3 6 | coda 3" tail) and the peak at 70-79 % in 19 of 24 pieces;
    - 0.33-0.49 right-hand rhythm cells per bar (composed: 0.12-0.30), long notes on chord tones only 69-79 %;
    - the waltz's "X | X/inversion" two-bar harmonic grid.
  - (2) A logit blend mixes inside the Arr block: at 0.5 / 0.5 its jazz half writes sections the forced layout does
    not have. Mix after `EndArr` only.
  - (3) `mel_style` in the retry checks.
  - (4) Context: done (`train --ctx 1280`; the widened teacher reaches p99 1242 / max 1298; 12 of 79,353 dropped).
  - (7) Student waltzes fail the render's breath gate (quiet1 < 0.25) in 3 of 5 spread-forced draws even as the best
    of 8: add the breath measure to `sample --best-of` / retry, or weight waltzes in the fine-tune.
  - (8) GPU memory: the worker pools now run with `CUDA_VISIBLE_DEVICES=-1` and train / eval log the peak reserved
    memory (training: 4.6 GiB at ctx 1280). Read the eval / sample peak from the next GPU run's log.
  - (5) The organ has no record (`arrange` returns None).
  - (6) The left hand's per-bar figure is still the players' dice.

- **Endless piano figure-summary determinism**: `perform.build_piano` records `endless_lh` with
  `max(set(v), key=v.count)`. Tied counts depend on Python's hash seed, so `lh_distinct` and a score using it can
  differ across processes for the same composition seed. NoteView parity tests fix `PYTHONHASHSEED=0`; choosing a
  stable tie-break is a separate behaviour change (left out of the behaviour-preserving note-metrics refactor).

- **Endless generators: next genres** (feat/endless: `agentsound/endless`, `python -m agentsound endless`). Built:
  `jazz-piano` (solo, default) and `jazz-trio` - a genre is a `Genre` data spec + the shared composer / players.
  Next as specs (+ a player hook where the plan cannot express it): a bossa band (`bands.make('bossa')`: nylon
  guitar comping, the sax on the head), a jazz ballad with the tenor (`jazz_ballad`, hornist on the head), synthwave
  (sections + heroes; the pop form `verse` and the new-age
  harmony exist now - add its sections + heroes as a 'perform' kind). Open findings of
  the first runs: (1) The loudness varies by
  feel (bossa ~2 dB louder: a per-feel `master` offset; waltz / ballad land -15.5..-16.5): a measured auto-trim (one
  quick render of the head, then the drive) would make an endless stream level. (2) The user's verdict on the sound
  ("schrill und hart") led to the `solo_piano` preset (presence +1.2..+2.3 dB vs the profile, the loud solo notes'
  2-5 kHz 4-5 dB lower); still to hear whether it now reads smooth enough. (3) Render speed 3.4-5x real time on this
  machine: `--play` stays ahead, but a bossa (dense left hand) is the slowest. (4) The stereo grand leans by
  register: with solo_piano's pan -0.35 the demo tunes (seeds 105 / 100 / 106) measure L/R -0.1 / +0.6 / -0.5 dB, its
  demo (a lower ballad) +1.3; a measured counter-pan per tune (the mixer's `seat` idea) instead
  of the fixed pan. The 'end' masking warning piano/comp is the two hands of one piano (benign).
- **Endless piano in general (feat/endless-piano, fix/endless-piano-followups) - open points**: `new-age-piano` /
  `classical-piano` / `endless piano --style`. (1) Not yet heard by the user: the demos re-rendered with the
  follow-ups (same seeds: new-age 21 / 13 / 31, nocturnes 3 / 6, the waltz 8, jazz 49 / 47; the worktree's
  `songs/_endless_piano/out/<style>/`, clicks 0; one overview per style in `out/overview/`). (2) Done in the
  follow-ups: the feel's body on both hands (`genres` feel 'body'), the waltz's strains twice (~2:57) with 8 3/4
  figures, key-aware chord spelling (`theory.spell_above`), the jazz piece's highest note in its planned peak (56/56
  tunes, was 38/56). (3) The nocturne gate is tight: seed 3 failed flat_dynamics (4.0-4.4 dB per phrase under 4.5)
  already on master; its touch is now (40, 104) (5.1 dB) - deeper touch arcs on the quiet sections would be the real
  fix (the 'flat_dynamics' info on 2-5 phrases per new-age / classical piece: A1, A3, coda). (4) The waltz's left
  hand still mostly oom-pah-pah (the 'rest' figure under every breath); its loudness range 10.3 LU (new-age 16-17).
  (5) A block-chord jazz solo's top note repeats (climax_single false) - fine for chords, or lift only the last.
  (6) The run log names the climax with sharps ('A#5' in Gb): theory.note_name has no key. (7) The jazz solo against
  the quieter written head: its top velocity over the head rose (vel +12 -> +20, solo_vel2 16 -> 26; round 1's
  'velocity plateau' tell) - watch it in the next blind round.
- **New-age score vs reference set 2 (2026-10-12, songs/_blind/ROUNDS.md "Reference set 2")**: eight more
  hand-written pieces (songs/pro-newage-skylight / morning / longing / lantern / tide / snowfield / homecoming /
  embers; `measure_newage.py --set2`) score 84.5-97.9, mean 94.3 = the generator's 94.3 (the old four 98.7-100): the
  `_SCORE_NEWAGE` ranges are the old three's style, not "composed". Widen / re-think (owner: genres table, after the
  generator work in flight): climax_x / peak_x (set 0.47-0.86; reward spread across a set), climax_lift (1.6-14.9),
  att_cv4 (to ~0.36), ph_vel (to ~16), rest_bar (0-5), frame_pitches (5-16: no longer separates), ret_tonic (a rondo
  goes home; the metric ignores modulation / chord quality), climax_chart for variation forms. Tighten where set 2
  sharpens the gap: block_copy (set 0-0.07, gen 0.22), a1_copy (0-0.17 vs 0.28), chords_n (25-33 vs 20.4). Artefacts:
  phrase_rests counts an early-played downbeat as the old phrase's last note, a pickup after a long rest as no breath;
  quiet1 / long_share read 6/8 dotted quarters as unbroken. Also: 4 of the 8 render with balance_mid_high (+6.1..+7.3
  dB; their melodies sit higher than rain's, +4.6) - a register property of the writing on the fixed genre sound.
  Done 2026-10-12: the table fit on the 12 (`_SCORE_NEWAGE.update`), blind rounds r6-r8 with set-2 pieces. Open:
  the learned discriminator refit on 12 instead of 4, the artefacts above.

- **Endless new-age blind loop (songs/_blind/ROUNDS.md "New-age") - open points**: composer judges N0-r4 100 %, r5 96 %, r6 100 % (the set-variety generator vs letters + three of the 12 references), r7 88 %, r8 71 % (17/24; all judges 70 %); the loop stopped after r8; the teacher-widening rounds r9 88 % (21/24, all 85 %) and r10 96 % (23/24, all 88 %) against three set-2 pieces (3/4, 6/8) - stopped at r10 (no improvement). r10's tells became distributions, then the sweep of 2026-10-13 made every sensible single choice a distribution (ROUNDS.md "After r10": the audit table, 6 of 115 decisions still fixed); r11 71 % (17/24, all 75 %), r12 96 % (23/24, all 88 %) - stopped at r12. Open (r12's tells): (a) one hook cell (the dotted upper-neighbour cell) in three of four pieces - make the motif cell a set-level draw with no repeat; (b) the 'grow' / 'climb' climaxes stamp the hook cell on each chord (fragmentation reaches only the grow's later units); (c) a climax in another key without a pivot (bIII via a bare C7, a climax on IV of V) and A3 straight back home; (d) the waltz's right hand silent 4-6 bars (intro lh_only stretched, B1's end + the interlude), a bar without the right hand at a climax top; (e) one borrowed colour (iv6) two bars in every section; (f) A3 = A2 after the climax, the peak at exactly 75 % of the piece in four pieces, the interlude = intro bars 1-2; (g) frame_pitches ~6 (refs mostly 8+), quiet1 0.31, rep_pitch 0.06 (refs <= 0.05). Still open from r8: (1) the theme static (a 3rd-4th, two attacks a bar), single-note bars; (2) a full-bar RH rest in the climax's 4th bar (the breath rule at the peak); (5) chromatic approach notes by augmented leaps (F#5 -> Bb4 over Am); (6) the left hand's broken figures repeat one top note three times (C#4-C#4-C#4); (7) climax_x still 0.70-0.80 (refs 0.47-0.86): a layout with an early climax; (8) the waltz's hook count (~12 vs 3-8) and its 'pickup + long note on 3' cell in every other bar; (9) metric artefacts (phrase_rests: an early downbeat counts as the old phrase's note; quiet1 / long_share in 6/8).
- **Endless lofi-piano (feat/endless-lofi) - open points**: `endless piano --style lofi` (genre spec + the
  `lofi_piano` band preset + drummer style 'lofi' + `pianist.FIGURES` lofi_*). (1) Not yet heard by the user: the demos
  `songs/_endless_piano/out/lofi/` (study seed 7 with the kit, rain seed 21 piano only, late-night seed 35 soft kit; seeds 33 / 34 were rerolled by the arc and breath checks).
  (2) The kick and the left hand share 60-250 Hz: the report keeps a 'masking' warn (comp ~70 % / drums ~35 % of the
  bass band) although the kick ducks the left hand 4 dB and the kit is thinned below 150 Hz - a lower kit / a higher
  left-hand bass (`pianist.figure(bass_lo=)` per genre) would clear it; listen first whether it is a problem at all.
  (3) The vinyl bed uses SampleRadar loops (royalty-free, no redistribution: the credits flag them); a CC0 surface
  noise would make the demos shareable. (4) The Osiris piano's layers differ per key (C5's loud layer +8 dB over its
  soft one at the change, C4 / G4 even after `LOFI['velcurve']`): a per-key layer trim (`inst.sfz(keymap / zone)`)
  would even the melody. (5) The lo-fi mix reads 'mid' -7..-11 dB under the 'piano' balance (by design dull); an
  analysis profile for lo-fi would judge it against its own reference.
- **Endless piano follow-ups (fix/endless-piano-followups) - songs to re-render**: the body's breath settles over the
  rise into the phrase peak (humanize.gesture; was the first beat), `jazz.paraphrase` never encloses over the
  melody's top note, the soloist's block-chord stage owns the range top when an arc has no climax. Render JSON changed
  (every song compiled before / after; samples from the main checkout): `_endless_jazz_piano`, `lanterns-on-carmine`,
  `letters-to-the-morning`, `minetta-lane-waltz`, `perry-street-rain`, `pro-piano-blues`, `pro-piano-bossa`,
  `pro-piano-latenight`, `pro-piano-waltz`, the four `pro2-piano-*`; the sung songs on the jazz presets surely too
  (not compiled: `jane-street-bossa`, `nowhere-to-be`, `when-the-year-turns-gold`). Chord symbols spelled by the key
  (Key.chord / Key.triad) change names only, not pitches.
- **Blind test round 6** (`songs/_blind`; the r6 renders of the 4 tunes in `songs/_endless_jazz_piano/out/r6` and the
  re-rendered `songs/pro-piano-*/out`, `songs/pro2-piano-waltz/out`, `pro2-piano-blues/out` were made in the
  fix/endless-r5 worktree - copy them into the checkout that runs `make_packets.py` (ID_SEED 'blind-jazz-piano-v6',
  the pro2 waltz / blues in place of the pro ones; not run)). Left after the round-5 fixes (ROUNDS.md "After round
  5"): solo phrases holding a hook-cell development only 0.16 -> 0.19 by `composer.developed` (rhythm x1/x2/x0.5 +
  contour; the arranger's anticipations / ornaments break exact rhythms - a looser measure, or the judges' reading,
  decides whether more is needed); bars of 85 %+ chord tones 0.19 -> 0.34 (motif lines snap strong notes to chord
  tones); the smallest A range 11.1 (18 % of the tunes under an octave: a calm A1 sits low against the G4 floor -
  a lower floor made the climax climbs leap); the solo's top velocity over the head +4.5 -> +8.6, density 1.08 ->
  1.01; one 14-semitone leap at a call / response seam (seed 111, wraps 0.04); the head's 8th lines still lean ~+7 on
  the beat (fills soft into the melody, the phrase goal excepted from the step cap); `test_the_round_3_tells` allows
  vel_onoff < 6 (6 tunes; 24-tune mean 3.6). Round 4's open points that stay: a 'shout' plan's 2 loud bars can be one
  long note; the set memory makes a set's tunes depend on the tune before (blind tunes rendered one by one); the trio
  has no trading 4s; a cold-stop tag measures its room tail inaudible; the hand-written latenight / bossa solos keep
  3-5 strong-beat clashes; the blues left hand (stride / tenths roots) and straight double-time 16ths in swung tunes
  (both noted by the other judges) untouched.
- **Endless round-5 fixes (fix/endless-r5) - songs to re-render**: the shared soloist (`motif_line`, `MOTIVIC`, calls
  developing the stage's cell, `scale(ctx, t)` chord-aware, chromatic approaches only into the beat, the velocity
  build, phrases 3-12 beats, landing notes before the other hand / the end, the 'early' arc), the piano vocabulary
  (motif sequences / riffs, the traded line's level), the pianist (a chromatic note never harmonized),
  `humanize.touch` (`pickup`), `perform._end_clips` (the drawn grip). Render JSON changed (every non-sung song
  compiled before / after; the sung ones not checked): `_demo_soloist`, `_endless_jazz_piano`,
  `ashes-and-chandeliers`, `ghosts-of-ocean-drive`, `kestrel-bay`, `lamplight-avenue`, `matryoshka`,
  `minetta-lane-waltz`, `nocturne-etude`, `perry-street-rain`, the pro-piano songs and the pro2 songs (those
  re-rendered in the worktree, clicks 0); round 4's `jane-street-bossa` / `nowhere-to-be` still to re-render; songs
  using `touch` / the soloist with sung parts likely changed too.

- **Blind round 6 balance (fix/endless-r6) - songs to re-render, round 7, and what is left** (ROUNDS.md "After round
  6"): the solo's phrasing / breath / line shape (`soloist.PHRASES` / `BREATH` / `CONTRAST` / `RUNS`, `MOTIVIC`,
  `piano_vocab._line_on`, the resolution), the form's level (`genres._JAZZ_DYN`, touches), the climax
  (`perform.CLIMAX`), heads (register, `hook_seq`, contours), reharm colours, the left hand (`lh_plan`,
  `pianist.LH_RESTRIKE`), the ending (`perform.END_ROLL`, nothing after the chord), a clip's last note plain,
  ornaments under the ceiling, `theory.spell_note` + the packets' spelling. Render JSON changed (every song compiled
  before / after; samples from the main checkout): `_demo_soloist`, `_endless_jazz_piano`, `ashes-and-chandeliers`,
  `ghosts-of-ocean-drive`, `kestrel-bay`, `lamplight-avenue`, `matryoshka`, `minetta-lane-waltz`, the four
  `pro-piano-*` and the four `pro2-piano-*`; not compiled (no voicebank in the worktree): `_demo_vocal`,
  `_demo_vocal_fx`, `_demo_vocal_rock`, `catch-fire`, `expensive-habits`, `jane-street-bossa`, `nowhere-to-be`,
  `one-more-round`, `when-the-year-turns-gold`; `unbowed` fails on its own. Only the 4 blind tunes re-rendered
  (`songs/_endless_jazz_piano/out/r8`, clicks 0). Round 7: `make_packets.py` (r8, 'blind-jazz-piano-v8') stops on
  the pro2 waltz / latenight / bossa until they are re-rendered (their piano note counts moved by 1-2: the shared
  ending / ornament changes). Left: beats on chord tones 0.92 (pro2 0.69-0.81) - the lean now keeps the run's
  direction and rarely applies, a passing tone on the beat would be the lever; leaps of 5+ 16 % (pro2 3-7 %: the
  hook cells' own leaps inside `motif_line`); phrases 11 beats on average (pro2 12-46: the call / response slots
  still cut a long phrase in two); the head's touch 64 / register 77 under the references' 68-75 / 78-79; the r8 waltz
  keeps 2 silent solo bars in its 64-bar chorus; the trading-4s shape has no climax stage (its peak is raised by
  `_peak_solo`); the ballad blues' head breathes at only 1 of 6 phrase ends (r8 002).
- **Blind rounds 7 / 8 (fix/endless-r7) - songs to re-render, and what is left** (ROUNDS.md "After round 7",
  "Round 8"). The shared players changed:
  - `soloist.fresh` / `LICKS`, `RUN_TOUCH`, `ANSWER_HOLD`, `solo(opening=, quotes=)`;
  - `piano_vocab` 16th budget (`sixteenths`), and `_set_piece` landings going on as a line;
  - the endless composer / perform data (`OUT_PARTS`, `TAG_FRAMES`, `ENDINGS`, `CLIMAX` window / ladder,
    `LH_UNDER`, the heads' `half_cell` / `pads` / `bridge_return` / 'tail', the jazz 'long' cells - the classical
    waltz shares them).

  Re-render every song that uses the soloist / pianist vocabulary: `_demo_soloist`, `_endless_jazz_piano`,
  `jane-street-bossa`, `kestrel-bay`, `nowhere-to-be`, the four `pro-piano-*`, `the-drummer-speaks`. Only the r9 set
  (`songs/_endless_jazz_piano/out/r9`) and the four `pro2-piano-*` were re-rendered, in the worktree, clicks 0, and
  the round-8 packets were made from them. The four `pro2-piano-*` were re-rendered BEFORE the round-8 fixes
  (`_set_piece`, `ANSWER_HOLD`, `RUN_TOUCH` 0.5): re-render them again before `make_packets.py` (r10).

  Left (round-8 judges, 35/40 right):
  - Solos switch textures instead of building: near-empty early bars, then 7-10 bars of flat-loud 8ths (the arc's
    stages as fixed densities).
  - Little motif reuse in the solo (3-note interval patterns 0.21-0.26, composed 0.42-0.54) and leap5 0.15 (pro2
    0.03-0.07).
  - Waltz solos keep 3-8 silent bars per 64-bar chorus (BREATH's bar breath and phrase gaps in 3/4); sil_cad caps
    ~20 % of the candidates.
  - Heads on a fixed dotted-quarter grid, chorded on almost every note; the waltz bridge's 4/4 chart doubled
    (4 bars per chord).
  - Frames: two tunes share one intro progression (INTROS draws per key / mode), the pad skeleton, a tag that
    reprises the intro, the same run-then-roll ending. A shuffle left hand of bare roots four to the bar; a blues
    ending on maj9.
  - orn32 7.7 per 32 bars on the test seeds (pro2 5.6-7.2).
- **Piano breath (fix/piano-breath) - songs to re-render, and what is left**: the user on r6 003: "sounds like an
  endless monotone line of notes" (ROUNDS.md "After the r6 listening"). Changed: `soloist.BREATH` / `CONTRAST`, the
  deleted empty-bar pickups / landing notes / left-hand re-strikes / section-boundary pickups, `pianist.STYLES` fill /
  embellish / quick rates, head voicings on arrivals, left-hand answers, `humanize.touch(levels=)`,
  `perform.phrase_levels`, `genres.PHRASE_ENDS` ('breath'). Render JSON changed (every song compiled before / after,
  samples from the main checkout): `_demo_soloist`, `_endless_jazz_piano`, `ashes-and-chandeliers`,
  `ghosts-of-ocean-drive`, `kestrel-bay`, `lamplight-avenue`, `matryoshka`, `minetta-lane-waltz`, `perry-street-rain`,
  the four `pro-piano-*` and the four `pro2-piano-*` (their written lines go through `pianist.arrange`); not compiled
  (no voicebank in the worktree; they use the pianist / touch): `_demo_vocal`, `_demo_vocal_fx`, `_demo_vocal_rock`,
  `catch-fire`, `expensive-habits`, `jane-street-bossa`, `nowhere-to-be`, `one-more-round`,
  `when-the-year-turns-gold`; `unbowed` fails on its own. None re-rendered except the A/B and the 4 r6 tunes
  (`songs/_endless_jazz_piano/out/breath`). Open: (1) the head's DENSITY is one level per 2-bar unit (7-8 attacks in
  every unit of r6 003): sparse statements need the composer's cells drawn by the unit's level (long notes in a calm
  phrase) - the next lever, after the user hears the A/B; (2) the double-time burst got short (16th bars per tune
  1.04 -> 0.25) and the solo's last chorus is the loudest in 0.88 of the tunes (was 0.96); (3) the solo's top velocity
  over the head +8.6 -> +11 at density 0.95 (round 1's plateau pattern); (4) the pro references are as continuous
  (right hand quiet a beat+ 15-38 % of the time): a human-played reference (a transcription's note density / rest
  statistics) would be the real target for `composer.breath`.
- **Piano body (feat/body-model) - songs to re-render, and what is left**: the user after the breath A/B ("I imagine a
  player gently moving his body"). `track.humanize(body=, lead=)` (`humanize.BODIES` calm / lyrical / swing: Todd's
  phrase arc coupling tempo and velocity, Friberg-Sundberg ritardandi into phrase / section ends, leap delays, breaths,
  bar sway, the left hand following the right) replaces the random jitter on the jazz presets' piano / comp tracks
  (`jazz.Feel.body`); the soloist and `romantic.Score.perform` mark their phrases; melody_rubato's free jitter and
  agogic leap delay are off under a body. Render JSON changed (compiled before / after; samples from the main
  checkout): `_endless_jazz_piano`, `lanterns-on-carmine`, `letters-to-the-morning`, `minetta-lane-waltz`,
  `perry-street-rain`, the four `pro-piano-*` and the four `pro2-piano-*`; sung songs on the jazz presets surely too
  (the baseline copy could not compile them): `jane-street-bossa`, `nowhere-to-be` (bossa), `when-the-year-turns-gold`
  (jazz_ballad). Only the A/Bs re-rendered (`songs/_endless_jazz_piano/out/body`, `songs/letters-to-the-morning/out/
  body_{before,after}.mp3`). Open: (1) the user's verdict on the A/B (then tune the profiles: arc size, the swing
  section-end lay-back); (2) the fitted ritardando q is noisy on the shallow swing ends (one section end per tune
  qualifies) - a reference recording's phrase ends would calibrate rit_w / q; (3) a body for the other players
  (bassist / hornist / guitarist have their own timing - one shared band body would let the band breathe together);
  (4) letters-to-the-morning's right hand has float velocities (x 0.78 in song.py), so test_notation's round trip
  fails on it (it did before this change too) - round them in the song.
- **Requests of the pro2 composer (2026-10-09)** - done: `pianist.arrange(written=True)` (no anticipations / delays /
  fills / quick ornaments), phrase-level touch (`humanize.touch(levels=)`, through `jazz.chorus` touch dicts),
  `perform.end_clips` public; an ornament-type switch exists already (`ornaments={}` or chosen weights for the long
  notes, `quick=0` for the short ones; `embellish=0` only stops the long-note ones). Open: (1) voice a WRITTEN
  anticipation (a note an 8th before the change, held over it) with the chord it leads into (arrange voices only its
  own anticipations that way); (2) shell / rootless voicings instead of bare roots under climaxes in the solo-piano
  left hand; (3) a wider default bossa bass velocity range (`_PIANO_FEELS['bossa']['bass_vel']` (46, 70)) and a guard
  against doubled roots where the tenths left hand and the bossa line meet.
- **Endless orchestra: open ends (blind rounds r1 / r2: judges 80 % / 100 %, composers 100 %; songs/_blind/ROUNDS.md
  "Orchestra", docs/ORCHESTRA_ENDLESS.md).**
  - The composer's tells (the shared new-age composer - fix there, the orchestra inherits it): melodies built on a
    two-note neighbour shake / three-note neighbour cells, phrases starting off the downbeat (1.42 / 1.92), the
    climax fragmenting into 2-beat cells, the 2-bar `inter` stub, chromatic mediants / Neapolitan chords dropped in
    without voice-leading, endings on the 2nd degree over the tonic.
  - Harmony layers disagree: the harp / harmony follow the chart while the melody holds a non-chord tone (bar 2 of
    a piece: E major in the harp under a G natural) - the harmony should take the melody's long notes as chord tones
    (or the chart the melody's), the harp avoid the melody's pitch classes a semitone apart.
  - Orchestration density: roles_sd 1.8 (references 2.4-3.7), db_bar_sd 5.5 dB (8-10), tutti 0.11 (0.15-0.27) - the
    references thin to 2-4 roles and stack 12+; a texture's slots could carry a per-bar density plan (enter / drop out
    by phrase) instead of all roles for the whole block.
  - Templates the judges named after r2: the string ostinato cell (now drawn from rock / arp / pulse, still one per
    block), the coda look (horns + harp + violins1 + cellos), the climax as octave stacks (a counter-line now 60 %),
    a melody doubled in unison by horns and cellos for 8 bars.
  - The colour roles and the doublings are seeded draws below the record (not `orchestra.RECORDED`): record them
    (`ACol`, `ADbl`) when the student should learn orchestration choices.
  - The gate rejects ~1 render in 3-4: a single click "in no single track (master chain or the sum)" (find it -
    the limiter / the hall?), and flat_dynamics on an accompaniment track named after an instrument (the analysis
    judges `violins2` / `trombones` as leads by name: NoteDynamics.cpp leadIntentName) - a Score-level hint
    (an analysis role 'bed' for parts that are only harmony / ostinato) would stop it.
  - The harder genres (romantic symphony, development, fugue, Debussy / Ravel colour, late-romantic film): the
    roadmap in docs/ORCHESTRA_ENDLESS.md - each a composer writing lines + TEXTURES rows + a player style.

## Mixer (`agentsound.mixer`)

- **A lead change inside a section** (matryoshka's minor section: a solo cello 4 bars, then the piano 4 bars, read as
  one section): the per-section lead (MIX `lead`, inference) works per section, not per bar.
- **Levels** are unweighted bar RMS plus one whole-song K offset per part, not per-section LUFS; `auto()` lowers the
  master input by 0.5-0.8 LU and only logs it.
- **Stereo stems see a balance pan**: a stereo sample set that leans (the SSO choir by pitch range: lux-perpetua's
  tenor +2.3 dB left at pan +0.14) needs a counter-pan; a `seat` helper (width + a pan that measures the lean) or
  centred choir zones in the patch.
- `fx.width` 1.5 on a duck-carved bed goes out of phase (expensive-habits: corr -0.23); no mixer move for a narrow
  chorus.

## Mastering (`agentsound.mastering`)

- `apply()` only estimates the loudness change inside the song
  chain; the plan overestimates the gain of limiter drive on an already limited mix (expensive-habits).
- **The limiter saturates around -9 LUFS on a dense club drop** (one-more-round, EDM branch): past ~10 dB of drive the
  output loudness follows the release, not the gain (drop at 50 ms: gain 11 -> -9.3, gain 20 -> -9.2 LUFS; release 25 ms
  -> -8.9; a hard-clip saturator before it or -4 dB on the bass changed < 0.2 LU). master/edm uses 30 ms; a real -7
  LUFS club master needs a clipper stage that cuts the crest (output crest stays ~9 dB) or a multiband limiter.

## Heroes (`agentsound.heroes`, patches/hero*)

- **Guitar**: a velocity-scaled `filterEnv` depth (SFZ `fileg_vel2depth`) for a bright pick that follows the picking
  (the per-pick filter envelope took the hero's velocity dynamics 1.9 -> 0.0 dB); the FSBS DI is a bridge pickup (a
  neck-pickup DI set or a per-note pickup comb); the `rock` profile's balance curve is darker in the mids than a
  guitar-solo record (kestrel-bay solos +4 dB mid/presence vs the profile, +-1.5 dB vs Sweet Child O' Mine): re-derive.
- **Sax**: the hero chain flattens velocity (0.35 dB per 10 steps after the compressor; the jazz / ballad voicing is
  2:1 now) - the pop voicing still relies on the hornist's accents.
- **Synth heroes** are darker than the references in lean mixes (presence -2.2 dB vs Nightcall); hooks below C5 need a
  low-mid dip on the bed; `hero/darksynth_lead` needs +4.6 dB of patch gain; their doubling layer (halo micro-shift,
  the piano layer's chorus) sits before the compressor / tape (`chain_order.ALLOW`) - the clean fix is a layer-level
  'post' fx.
- **Hero piano**: its left hand shares the bassist's octave in a band.
- A pre-fader / pre-insert key does not follow the key's fader (only the hero wrapper moves the thresholds:
  `HeroInfo.key_fx`): a `tap`-aware threshold for `s.sidechain(..., tap=)` by hand; patch sends cannot carry a tap.

## Players (pianist, hornist, soloist, drummer, bassist)

- **Romantic pianist: the blind judges' remaining tells after round 2** (2026-10-12, docs/PIANIST_RULES.md
  "Round 2", songs/_demo_pianist ab2_*; round 2 fixed the shared tempo template, the sawtooth lilt, the flat
  left hand and the top-down left-hand rolls, 9/9 for the new rules):
  1. Within a piece the phrase arcs are still alike: tempo-shape correlation 0.7-0.85 between phrases, all "faster
     in the middle, slower at the end" (PHRASE_TEMPO draws depth / peak / close, not the shape family). Fix: let the
     phrase's content pick it (its goal note's place, its harmonic charge, the cadence type): a phrase that drives
     into the next one, a held-back opening.
  2. The pedal looks clockwork: up ~54 ms / down ~154 ms after every change in every piece (PEDAL vary 0.25 is
     not enough to show), three levels only (0 / 0.6 / 1). Fix: the delay from the texture (bass register, how much
     rings), occasional re-pedalling inside a long harmony, more half depths.
  3. The melody lead is a near-constant +19 ms, only loosely tied to the velocity gap (r 0.24-0.44); the classical
     lead stays small (+7 ms against new-age's +18): melody_rubato's lean / peak / anticipation take it back; a
     nocturne melody at p over an arpeggio wants 20+ ms.
  4. The tempo collapses to under 12 BPM at fermatas and the final ritardando (a cliff in the tempo map, not a
     shaped breath).
  5. The accompaniment figure has no shape inside the bar (every LH eighth about the same length and level): the
     figure's crest could lean on its top note and lighten the repeated inner notes.

- **Soloist / pianist tells fixed (fix/soloist-tells) - songs to re-render** (not re-rendered: their render JSON
  changes, checked by compiling every song before / after): `_demo_soloist`, `_endless_jazz_piano`,
  `ashes-and-chandeliers`, `ghosts-of-ocean-drive`, `jane-street-bossa`, `kestrel-bay`, `lamplight-avenue`,
  `matryoshka`, `minetta-lane-waltz`, `nowhere-to-be`, `perry-street-rain`, `pro-piano-blues`, `pro-piano-bossa`,
  `pro-piano-latenight`, `pro-piano-waltz`, `when-the-year-turns-gold` (pianist.arrange; not compiled here: its
  DiffSinger runner), `one-more-round` (pianist.arrange, merged from master after the check); any untracked song
  using `soloist.solo` / `pianist.arrange` / `jazz.chorus` too. Open: the solo's densest third is +20 % over the head
  after the breath fix (the blind test's composed solos +40-70 %). (Silent solo bars are breaths now - see "Piano
  breath".)
- **Player details from blind test round 2 (fix/endless-composer-r2) - songs to re-render**: the waltz left hand
  keeps the pulse (`LH_METERS` 3/4 'pulse': a chord of two bars+ struck on every downbeat), no left-hand push whose
  bass rubs a half step against the chord still sounding (`pianist._bass_clash`), no ornament on a note held into a
  chord it clashes with (`_rings_clear`), the swing groove moves a rolled chord as a whole (`humanize.groove`), the
  soloist's lines with rarer triplets, landing lengths on the 8th grid (`soloist.held`) and a varied displacement of
  the quoted motif. Render JSON changed (every song compiled before / after): `_endless_jazz_piano`, `kestrel-bay`,
  `lanterns-on-carmine`, `minetta-lane-waltz`, `perry-street-rain`, `pro-piano-blues`, `pro-piano-latenight`,
  `pro-piano-waltz` (the three pro pieces re-rendered in that branch's worktree for blind round 3); not compiled
  (no voicebank in the worktree; they use the pianist / a swing groove): `_demo_vocal_fx`, `catch-fire`,
  `expensive-habits`, `jane-street-bossa`, `nowhere-to-be`, `one-more-round`, `when-the-year-turns-gold`.

- **Player fixes from blind test round 3 (fix/player-r3) - songs to re-render**: `humanize.touch` (contour, not beat;
  neighbour cap, jitter), the soloist's line rules (chords, unisons, breaths, the run ramp), the pianist's grace
  figures / fill lift / FAST runs / `LH_SHELL` texture and pushes. Render JSON changed (every song compiled before /
  after, samples + voices from the main checkout): `_demo_soloist`, `_demo_vocal`, `_demo_vocal_fx`,
  `_demo_vocal_rock`, `_endless_jazz_piano`, `ashes-and-chandeliers`, `catch-fire`, `expensive-habits`,
  `ghosts-of-ocean-drive`, `gymnopedie-etude`, `jane-street-bossa`, `kestrel-bay`, `lamplight-avenue`,
  `lux-perpetua`, `matryoshka`, `minetta-lane-waltz`, `nocturne-etude`, `nowhere-to-be`, `one-more-round`,
  `perry-street-rain`, `the-drummer-speaks`, `when-the-year-turns-gold`, and the four `pro-piano-*` (re-rendered in
  the branch's worktree, clicks 0, no warnings); not compiled: `unbowed` (fails on its own).

- **Piano realism** (Gymnopedie / Nocturne études): no damper / soundboard model (decay inside a bar 15.3 dB vs 11.6
  in the reference: two-stage decay, pedal coupling); soft notes lack a bright attack (1.18x vs 1.37x); `touch()`
  never accents single notes (7.7 vs 9.0 dB) and rubato does not linger on peaks (bar-length variation 0.075 vs 0.13);
  trills are too even (0.19 vs 0.47).
- **pianist.answers(vocal_line, prog, ...)**: fills sized to the voice's rests (jane-street-bossa wrote them by hand);
  `jazz.chorus(comp=...)` on a band without a `comp` track (bossa) fails on `None.play`.
- **Soloist** move choice is nearly fixed by energy / density (kestrel-bay: seeds 22-28 chose the same moves): more
  moves per role and a seeded spread in the scoring.
- **Drummer**: no 6/8 / 12/8 feel (16th grids in 4/4; needs triplet grids for patterns, hands, the bassist and the
  guitarist); cymbal chokes: SoundFont kits and the drum machine have none (`ending='choke'` lets the hit ring;
  inst.kit and the sampled/ SFZ kits have them); the hands' physics run move by move (a stroke
  at a slot's end and the next slot's start can collide: re-run `_resolve` over a whole solo); the soloist's calls all
  open with the motif (the-drummer-speaks: ~10 times in 34 bars); the pop
  Chart kit's hat foot is the closed hat; an intro (energy 0.38) and a `groove` section read the same level; the
  `songs/_bands` demos are not ported to the drummer.
- **hornist**: `Performance.place(level=)` is a target name, not a dB offset (matryoshka needed a gainDb lane).
- **Tempo**: millisecond timing in the drummer and hornist assumes a constant tempo.
- **One keyswitch per section track**: two articulations at once on a role (violas' staccato under a marcato stab)
  collide - 44 in unbowed; a `_div` twin track per role or the compiler splitting onto a twin sampler.

## Singer / vocals (`agentsound.singer`; vocal FX on feat/vocal-fx - the next batch after that merge)

- **German lyrics are hand phonemes only** (die-faehre-um-sieben, `lyrics.spell` + a per-song `LEX`): no German G2P /
  dictionary, so every word is typed by hand. Intelligibility is unverified by ear: a German SAPI recognizer as proxy
  picked 4/4 spoken-style Hanami lines out of 10 sentences, but only 2/12 SUNG lines out of 24 (dictation caught
  fragments; the desktop SAPI engine is poor on singing in general, so the proxy is weak). Next: the user's
  verdict, then maybe a small German G2P (rules + exceptions) and diction checks for German codas (ch / cc, -en).

- **Mic pull**: every long phrase end is pulled (chance `end` 1.0: may read as a habit); no coda-vs-band measure (with the pull the final consonants
  ended 14-17 dB under the band and passed) - and no pull-back for a deadpan voice; the report reads the trigger
  notes, not the pulled vowels.
- **Expression**: an emphasised word before a rest has nothing to lengthen; `*word*` is uneven (nothing on "cheap",
  +2.7..3.7 dB on "time"); the intimate line reads -0.8 dB (planned -2); a run on a phrase-end hold shortens it under
  the mic pull's `min_s`.
- **Diction**: word-final stops before a consonant-initial word stay unreleased in legato (a gap >= 80 ms releases them).
- `build --section`: a phrase whose take starts before the section is not heard (one-shot triggers).
- No register-dependent make-up (a part a minor third lower reads ~2 dB softer: `makeup_db` by hand);
  `SOFT_MAKEUP_DB` is measured for Hanami only; the banks have no variance model (energy / breathiness) and the
  vibrato does not follow the air like the hornist's.
- **vocal_buried uses unweighted RMS**: in an EDM drop the kick + sub read 4-6 dB RMS over the vocal while the mixer
  (K-weighted) says the bass is 5-11 dB too QUIET against it (one-more-round drop2: vocal -22.0 RMS vs bass -16.3;
  the mixer wanted bass +7). Compare by loudness or leave the low-end roles out of the check.
- **Talk box velocities**: the LPC talk box + the guitar's amp + compressor flatten the picking (0.0 dB per 10 velocity
  steps, also with the mouth singing the line's velocities - singer.mouth vel=False now); one-more-round writes an
  'accent' utility lane from the notes by hand - fold that into speech.talkbox (a lane from the carrier's notes at
  compile).
- **Chops**: a chop note longer than its slice is cut (no loop / freeze of the vowel for held chops); slices are
  syllable / word / phrase only (no 'vowel only' unit for the pitched 'oh' pads of future bass).

## Bands / presets (`agentsound.bands`, bandlib)

- **soul_ballad**: the Rhodes / upright masking is gone (SOUL_DIP + REGISTER Bb3-C5); the demo's low mids read +4.5 dB
  (limit +4), 62 % of it the tenor's - a lowmid dip in the shared sax chain would touch every jazz preset.
- `songs/_bands/rock_band` warns: the intro riff's kick + bass unison (separation -3.3 dB) and flat dynamics on gtr_r /
  lead (velocities 89-117 through driven amps); decide whether a locked kick + bass unison stays a warning.
- The rhythm guitars' note dynamics come only from the articulation (velocity -> level ~0 dB through the driven
  amps): velocity zones or a velocity -> amp input lane.
- power_ballad's echo bus idles under a hero lead (reverb_inaudible on kestrel-bay until the clean guitar / piano sent
  to it); the retrowave kit and master are dull in full choruses (raising hats does not fix the air); the funk_band
  demo keeps a drums / bass masking warning.
- The orchestra hall's crossfeed and rock_band's clean room were set by numbers (width 82 -> 69 % on
  the-drummer-speaks); the library's 2-channel IR returns have no crossfeed.
- **EDM presets**: only melodic_house is tuned on a song (one-more-round); house / techno / big_room / future_bass are
  set from the recipe (songs/_bands/house builds every STYLE) - calibrate their pump / trims / master drive on a demo
  each and fill bandlib/edm.py TUNED. The house demo itself reports flat_dynamics on piano-house chords (1.8 dB through
  the chords compressor) and loudness_low.
- **Orchestra performance rules: the judges' remaining tells** (2026-10-12, docs/ORCHESTRA_RULES.md; A/B in
  songs/_demo_orchestra_player; new preferred 6/6 by blind judges, realism about 3.5 -> 6.5 of 10).
  (1) In ff tutti passages the lanes still move with the written velocities. Judges want one ff plateau per phrase:
  `ensemble.lane` could hold a phrase whose notes all sit above the curve's flat top (vel >= 112) at one level.
  (2) A mono low-brass or tuba line breathes at every chord change of a slow 8-beat pad (film peak: about 120-230 ms
  every 4.8 s). A section of desks would stagger; one line cannot. Options: a `desks` count per role that
  splits the line and staggers the breaths, or a longer budget for a pad (`BREATH['budget_s']`).
  (3) The melody margin over the accompaniment is still 1.8 dB median, 17 % masked (unbowed). Most of it is ff
  tutti, where everything saturates. Raise `BALANCE['db']` to 3 or let the line's lane lead at ff.
  (4) `ensemble.db_of` assumes the orchestra curve (`_DYN_CURVE`, flat above velocity 112). SFZ zones with their
  own `dynGain` (the SSO sections: up to +2.4 dB from 112 to 127) are not flat there, so `_fit` lowers an
  accented ff note a little too far on them.
  (5) The ms -> beats conversions read the song's tempo map while `Score.perform` runs. A fermata or ritardando
  added after `perform()` is not seen (the lead and the ensemble shifts would be off there). Set the tempo lanes
  first.
  (6) The final ritard and the fermata releases come from the song's tempo lanes. `ensemble.RELEASE` only
  staggers the ends. Songs without a `ritardando` on the last bars end in tempo.
  (7) `hornist`'s solo vibrato (the unbowed horn / clarinet / oboe solos) starts at about 550-600 ms and does not
  follow the dynamics. `ensemble.VIBRATO` / `vibrato_depth` could be reused there.

## Analysis / checks (engine/analysis, silent_notes, the report)

- **Silent-notes ear gaps**: the compile-time check does not know `{'dir': ...}` samplers or sf2 layers inside a
  stack; the render-time ear cannot hear a silent note that starts with a sounding one on the same
  track (a crash on the kick).
- **Dynamics role inference**: a stack is judged by its first layer only.
- **Organ: open ends (the organist / endless organ work).**
  - The `organ` analysis profile's spectrum curve is provisional (the Lars Palo pipes through the preset); measure it
    on commercial organ recordings when one is in `references/`.
  - The pedal has no expression: an unenclosed pedal cannot fade with the swell (the meditation reference ends its
    last pedal note early instead). A per-role `instrument.expression` fade on the pedal would be the fix.
  - Burea's `strings` is a Salicional alone (no celeste): thin as a meditation bed; Pitea's Gamba + Voix celeste is the
    better meditation organ.
  - `song.fermata(at)` needs a note starting at `at` (or a silence): a held common tone merged into one key moves the
    final fermata onto an earlier onset.
  - Endless organ, the tells left after blind round 3 (judges 100 %, songs/_blind/ROUNDS.md "Organ"): the 4 + 8k + 4
    section grid (the composer's 8-bar parts; the pedal point breaks it only once); the A tune restated three times
    with the same opening bars (re-harmonized, but the melody is the composer's copy - vary the tune itself on a
    return: ornamented, extended, another voice); one toccata cell in every bar (16 attacks per bar; no theme in the
    top voice); the trumpet tune's accompaniment one triad per beat; meditation inner voices as dyads of seconds
    under the cromorne; the chorale-prelude's counter-line a stream of turns. The ORGAN score barely separates the
    references (94.5) from the endless pieces (91.7): these tells need metrics (a melodic-copy share of the tune's
    returns, figure variety per section, section-length variety).
- `hero_vocal.GRIT_MEASURED`'s coda numbers need a re-run after the offset fix; the build's vocal wetness
  (`singer.wetness`) is an estimate from the send shares (exact: `songs/_demo_vocal/wetness.py`).

- **Processed-voice effects (feat/vocal-fx, songs/_demo_vocal_fx): open ends.**
  - Pitch correction lives on the singer's curve only (`sing(tune=)`): there is no engine effect that tunes ARBITRARY
    monophonic audio (a recorded / sampled vocal, a speech track, a lead synth's audio). It would need a pitch
    tracker (YIN) + a formant-preserving shifter (PSOLA / a phase vocoder with an envelope) in C++ - not cheap.
  - The talk box speaks from the instrument's harmonics: a guitar line in the upper register (E5 and up) shapes badly
    (measured: F1 / F2 band balance follows the mouth with r 0.21 an octave up vs 0.55 at B3-G4); the LPC vocoder
    has no formant-sharpness control (its lag window is a fixed constant) - an engine `resonance` / bandwidth param
    could give the throatier, more nasal talk-box peak; the guitar patches' compressor after the vocoder eats ~4 dB of
    its output (`TALKBOX` output +6 dB nets about +2.6 dB).

- **The learned ears (`agentsound.ears`) cannot hear "real" yet** (calibration 2026-10, docs/COMPOSE_API.md "The
  learned ears"). Audiobox PQ / CU and CLAP P(real) rank degraded renders (one velocity, grid, bitcrush, telephone)
  below the original 8/8, but our mixes beat 6 of 8 paired commercial records, the old FSS strum beats the new
  Shinyguitar strum on every axis (PQ 8.05 vs 7.61, CE 7.13 vs 5.74: listen - are the recorded noises / the
  Shinyguitar mic blend heard as low quality, or is FSS really cleaner?), and composed pro piano vs endless new-age
  is a coin flip (AUC 0.29-0.68). Next: (1) per-instrument stems instead of the mix for P(real) (a piano stem vs a
  real solo piano), (2) a learned real-vs-render probe: logistic regression on CLAP / Audiobox embeddings trained on
  our renders vs real recordings of the same instrument (needs ~50+ real excerpts per instrument: ask the user which
  recordings may be used), (3) feed the ears' scores into the endless best-of-N only after (2) beats the rules on a
  blind round. FAD needs >= ~50 reference windows per set to mean anything (two piano references give 24).

## Engine: stack / layers

- `layered/piano_strings`, `piano_pad`, `piano_organ` peak at +0.6 to
  +0.8 dBFS on the track.

## Engine: wavetable (feat/wavetable)

- **Warps are not band-limited**: `osc<N>.warp` sync / bend / mirror at amount 0.5 on the saw at C7 measure only
  -35..-38 dB inharmonic energy (test_wavetable; the plain tables -70..-90). The mip level follows the warp's
  multiplier, but the discontinuities fold. Fix when a song needs bright warps up high: 4x oversampling of the warped
  oscillator only, or bake the warp into a derived table at prepare time (sync / bend per frame).
- **No third-party tables yet**: only the 7 built-ins ship. Candidates (not downloaded, licences to check before any
  manifest entry): AKWF-FREE (Adventure Kid single cycles, CC0, ~4,300 cycles, ~10-20 MB), the Surge XT factory
  wavetables (in the GPL-3 Surge repo, some sets under their own terms; .wt), WaveEdit Online (single cycles, CC0 per
  its site). A `samples`-style manifest for wavetable packs (`assets/wavetables/`, gitignored) + a catalog listing of
  the installed files would follow.
- Not heard by the user yet: `songs/_demo_wavetable` and the five `wavetable/` presets.

## Kits / samples (assets, patches)

- Not re-rendered after a library change - listen when they are touched: every VPO choir song (`sampled.CHOIR_SPEAK`:
  the soft notes speak sooner - ashes-and-chandeliers, lux-perpetua, unbowed, polaroid-summer, matryoshka,
  film_orchestra, the voice hero), the songs on the rock presets / guitar patches (the tube amp, Big Rusty, the drum
  bus and bass rig: ashes-and-chandeliers, kestrel-bay, lamplight-avenue, `_demo_soloist`, `songs/_bands/*`), the
  synthwave songs on `synthwave/octave_bass` (4 ms filter attack), every song on a sampled drum patch (re-strike
  damping 6 dB on by default, inst.kit's cymbal choke keys).
- Loop seams: `sampled/choir_mixed` on long held notes (matryoshka's coda: 7-10 masked clicks, -45 dBFS),
  `choir_f` (2), `sampled/choir_male` (a held D3 in lux-perpetua), SSO trumpets / violins II on a 9 s fermata
  (lux-perpetua: 11 masked), the orchestral basses (5 masked). SSO crotales (octave mapping) and string harmonics
  (loops click) are unusable as they are.
- Ranges: `sampled/choir` (VPO female) has samples G4-C6 only (ashes' `choir_f` 41 notes under G4, polaroid-summer's
  `choir` 37), `sampled/choir_oh` D2-C#5 (above is stretched; `film_orchestra(choir='oh')` still gives C3-A5),
  orbital-station plays 14 tambourines on the TR-808 kit (none: map one from 80s Digital / Chart).
- Missing: a bass cabinet IR (`bass_rig` rolls off with an eq), a real neck-pickup guitar DI, palm-mute / dead-note DI
  samples for the hero zones (`sampled_guitars.PALM` is an emulation), a sampled string-noise pack (pick scrape /
  squeak are synthetic), basset horns (Mozart's Requiem: the SSO clarinets stand in). YDP grand has no SFZ variant;
  the Iowa alto sax and double bass files are multi-note runs (need slicing); compare `karoryfer-bigcat-cello` with
  `sampled/solo_cello`.
- The guitar hero's wah goes ahead of the amp in every zone of a stack (5-6 instances): a stack-level pre-split
  insert; the sampler's `harmonic` assumes 100 % pitch keytrack and an in-tune root.
- **Acoustic guitar (`sampled/acoustic_guitar`, guitarist hand feel; `songs/_demo_acoustic`)**: (1) the Shinyguitar is
  an ARCHTOP: the EQ opens it, but it stays darker than a flat-top dreadnought (air ~-8 dB vs the jazz reference,
  FSS steel +7) and has less low-string boom - a real flat-top steel pack (mic'd, velocity layers + noises) would be
  the better source. (2) Only one mic program in stereo: a solo acoustic is ~4 % wide (narrow_mix on a solo demo);
  a stereo-pair option (two round robins panned, or the DI as a second channel) would widen it honestly. (3) No real
  string-squeak recording: position shifts play the pack's release fret noises (leave + land); a slide squeak sample
  would be better. (4) The older styles (pop, folk, ballad, country, indie) still play with the 'plain' hand - move
  them to 'acoustic' / 'fingerstyle' after a listening A/B (changes their songs' renders). (5) Not judged by ear:
  the A/B vs `sampled/steel_guitar` is from the analysis only.
- **Orchestral gaps after `sampled_sections`** (2026-10-12; `songs/_demo_orch_sections`). Closed from the installed
  packs: the five symphonic string sections, woodwinds a2 / a3, muted horns / trumpets a3 (KISS stacks of the VSCO
  solo mute recordings, measured: no comb filtering). Still missing, no installed source: string con sordino / sul
  ponticello / sul tasto SECTIONS (Philharmonia has them only for the solo violin, 1 s notes G3-A6 and single
  phrases: no-redistribution, not playable as a line), trombone mutes (straight / cup / harmon), a muted tuba
  (Philharmonia: 1 s notes A1-D#4, no-redistribution - possible as a short-note patch), flutter-tongue (Philharmonia:
  phrases only), piccolo trumpet, Wagner tuba, cimbasso, euphonium, flugelhorn, recorded legato transitions for
  sections (SSO / VPO have none; VPO's author kept overlapping sustains). The `sampled/oboes` sustain (VPO re-loop of
  the SSO oboes) shows one soft masked loop seam on the audition phrase. Free libraries checked (web research,
  2026-10-12; nothing downloaded):

  | library | URL | licence | size / format | adds | direct? |
  |---|---|---|---|---|---|
  | OrchideaSOL (IRCAM Studio On Line) | forum.ircam.fr (metadata zenodo.org/records/3686252) | Ircam Forum License: free, NON-COMMERCIAL, registration | 12,253 WAV single notes (size not stated) | solo strings with sordina / piombo mutes, brass with harmon / wah / straight mutes, flatterzunge, stopped horn (solo players; ordinario chromatic, techniques partly every whole tone) | no: an Ircam Forum account (the user downloads) |
  | TinySOL | zenodo.org/record/3685367 | CC-BY 4.0 | 1.0 GB, 2,913 mono WAV | ordinario only: chromatic solo viola / double bass (we have SSO solos) | yes |
  | Univ. of Iowa MIS | theremin.music.uiowa.edu/MIS.html | "used for any projects, without restrictions" | AIFF chromatic runs (need slicing) | no mutes / sordino / flutter (vib / non-vib only) | yes |
  | Virtual Playing Orchestra 3 | virtualplaying.com | royalty-free | 603 MB + scripts | installed; no sordino / mutes / legato | yes |
  | Sig-Ex Sustain Strings / Woodwinds lite | sig-ex.com/free | freeware, no redistribution | OGG, a sample every minor third | viola / bass sections, woodwind unisons (sustain only) | no: Gumroad (email) |
  | Freesound packs (Carlos_Vaquero viola / bass ponticello) | freesound.org | CC-BY-NC | 6 + 1 files | too few notes | no: login |
  | Pianobook (Solo Brass Untamed: flugelhorn, euphonium; muted sets) | pianobook.co.uk | free, "may not give away any sample(s)" | DecentSampler WAV | flugelhorn / euphonium, some muted brass | no: login |
  | Bell & Bone (Libre Wave) | librewave.com (URL unverified) | GPL3 per KVR (unverified) | Rhapsody player only | trumpet / trombone bucket, cup, harmon mutes | no: account + player |

  Excluded as plugin-only: Spitfire LABS, BBC SO Discover, Orchestral Tools / Bitwig, Blueprint Gentle Strings
  (Kontakt). No free plain-file source found for gap 4 (piccolo trumpet, Wagner tuba, cimbasso), section con
  sordino, or true legato. KISS fallbacks if wanted: a sordino voicing of the sections (an eq / tone tilt - an
  emulation, judge it by ear first), flutter as amplitude modulation, legato by the sampler's crossfade.

## Sampled-instrument realism (plan: docs/SAMPLE_REALISM_PLAN.md)

The alternative to physical modelling (HUMAN_FEEDBACK: keyboard-like samples, static sax sustain, the physical guitar
"simple and empty"). Lever 1 (per-voice random micro-modulation + random tremolo LFO) is being built separately. It is
the shared foundation; its open item: map the SFZ noise LFO (`lfoN_wave=-1`, played as a sine today) to its noise
source (Weresax's own humanize, cc117-119). Every new param defaults to off (bit-identical renders). Batches as in plan
section 9:

- **Batch 0, tooling**: done (`audition --ab/--set` + probes repeat / sweep / legato / sustain / pedal, `build --set`,
  report `nodes[].realism`, `NoteExpression` + `articulation.note_params`, GuitarBody.h parked in engine/instruments for
  lever 5). Open: the `wave` repeat measure barely moves under small detune (a +-6 ct take reads 0.98) - judge
  round robins by `sim` plus the ear; `transitionDip.pitchMs` is coarse (5 ms steps, octaves skipped).
- **Batch A, levers 2 + 3**: built (sampler `rrpitch` / `rrtone` / `rrattack` / `rrstart` / `rrlevel` / `rrborrow`,
  `layers='blend'` + `blendwidth`, `veltone`; values in `patches/realism.py` FAMILY / BLEND / VELTONE). **No patch
  opts in yet**: the blind pairs (nylon solo + patio-de-naranjos on the FreePats nylon, Salamander repeats,
  pro-piano-bossa, a concert-grand crescendo, nocturne-etude) wait for the user's verdict; opting in is one spread per
  patch (`_sfz(..., **realism.FAMILY['nylon'])`), then the patch's songs go on "Not re-rendered after a library
  change" (nylon_guitar: the jazz band's 'guitar' role, bandlib/jazz.py). Measured on the probes: nylon `repeat`
  sim/wave 1.0/1.0 -> 0.99/0.91 (the 7-RR concert guitar 0.84/0.27: `sim` barely sees a static detune); concert grand
  `sweep` brightness seam 17.2 -> 7.0 dB with blend (level steps unchanged, 2.7 -> 2.9 dB). Findings on the way:
  (1) a static detune beats against the same key's still-ringing earlier notes (nylon release 1.5 s: 6-7 dB level
  jumps on `sweep`) - FAMILY nylon / plucked carry `restrike=12`; (2) FreePats nylon neighbours differ 3-7 dB in
  attack brightness and +-5 dB in level, so `rrborrow` is gated (only a neighbour within 1.5 dB brightness,
  level-matched) and rarely fires on that pack; (3) the Splendid layers' onsets are up to 1.5 ms apart with
  correlation 0.92-0.96: blending them combed the attack (-3 dB dips, +2.5 dB bumps) until the onset alignment and
  the coherence-normalised gain law; (4) `veltone` on a 16-layer pack made a darker-brighter sawtooth across the
  narrow layers until its depth followed the layer width; (5) `rrborrow` on the Salamander (a sample every 3 keys)
  still let notes stick out by up to 20 dB brightness in nocturne-etude (the gate compares the samples at their roots)
  - FAMILY piano / rhodes carry no rrborrow. Open: `rrborrow` across a register break is only guarded
  by the brightness gate; `layerStep` on chords (in songs) is noisy - judge it on `sweep`; blend's 2x voices for
  ~0.4 s per note (piano patches have 128-192 polyphony: fine so far).
- **Lever 4, performance noises**: `sampled_guitars.NOISES` -> `patches.NOISES` with roles per family; recorded
  zones (Fiedler fretnoise, Salamander pedalD/U, Weresax cc122 wind) before synthesized `*noise` presets; placed by
  guitarist / hornist / pianist via Budget.
- **Lever 5, hybrid resonance**: the sampler's piano `StringBank` -> a shared `Resonance` (sets
  piano / guitar / nylon / violin / cello, `strings`, `tuning`, `body` with cx-physguitar's GuitarBody.h modes).
- **Lever 6, transitions**: `mono='string'` (per-string legato: slides / hammer-ons), `legatodip`, `legatonoise`,
  `glidemax`.
- **Lever 7a, wandering sustain**: `wander` / `wanderxf` (multi-point pitch-synchronous sustain instead of one loop).
  7b sinusoidal+noise resynthesis only if 7a + lever 1 lose the blind A/B; lever 8 (learned timbre) is outlook only.

## Notation / songs

- **Library adoption that changes a song's sound** (listen before migrating): nowhere-to-be onto `soul_ballad` (its
  own Rhodes chain instead of the grand's, no trims), the multi-part pieces declaring MIX `lead` per section (unbowed,
  ashes-and-chandeliers, lux-perpetua), lux-perpetua's syllable gate vs `inst.sfz(zone={'release': ...})`,
  unbowed / lux `follow=True`, lamplight-avenue onto `hero()` / `drummer.arrange` / `pianist.pedal`, children-of-neon's
  pedal (every 4th chord change; `pianist.pedal` is the per-chord one), ghosts-of-ocean-drive's solo strings / pre-2
  arp a bar late (`bars=4` in a plan), orbital-station's `arp_line` (`patterns.arp` voice-leads differently).
- **Notation**: a Line's extras survive shift / transpose / octave / velocity / with_length only; one automation lane
  per target per track (gesture lanes, `fretwork.render` and `guitarist.lead(gestures=)` on `instrument.pitchbend`
  interleave - a per-track lane registry that sums additive lanes would fix both); ornaments need `bpm=` at parse
  time; `format()` writes absolute names only and does not split notes at bar lines; `s.arc(within=)` steps need a
  hold point (`(beat - 0.5, old)` before a step).
- **Songs**: the epic (ashes-and-chandeliers): the finale / summit tutti +4.2 / +7.6 dB mids vs the film reference,
  Part III's solo only 0.2 LU over anthem2, the ballad piano without air (> 7 kHz); unbowed's intro places two
  harmony passages two beats late (kept for the byte-identical migration); jane-street-bossa's A&R notes were made in
  Bb (it sounds in G now) and its A line is leapy (9 leaps of a 4th+ in 25 intervals).

## Making-of film (`agentsound.makingof`)

- "before" clips need the judged commit in AR.md and a version that builds with today's
  library; Breeze narration is ~8-10x slower than real time (cached after); stems are post-fader and dry of the shared
  reverbs (a soloed group sounds drier than in the mix).

## Docs / housekeeping

- Disk: C: is ~99 % full - scratch renders go to D: (git-ignored folders in the worktrees); clean
  `%TEMP%\claude\...\scratchpad` and stale worktrees (`git worktree prune`) now and then.

## Waiting on the user

- **Orchestral techniques download** (Kits / samples, "Orchestral gaps"): OrchideaSOL is the only free plain-file
  library with sordino / mutes / flutter, but it needs an Ircam Forum account and is non-commercial - your decision
  and download (then a manifest entry and patches from it).

- **Sampler `flutter` defaults on the sampled winds** (2026-10-15, blueprint-boulevard A/B, D:\tmp\flutter): the
  living-sustain primitive is in the sampler (`flutter` / `flutterpitch` / `flutterrate`), every patch still at 0. The
  v1 modulator sounded shrill (fixed: steep band-limit, test_sampler "no hash"); once the user approves the v2 clips,
  give sampled/alto_sax, tenor_sax, bari_sax, the hero sax takes (bump patches/hero.py VERSION + the LEGACY digest in
  test_hero) and the VPO / played solo winds and brass a subtle default (~0.5 dB, 1-2 ct, 11 Hz), one table per family.
  Related: the Weresax `Sax.sfz` has its own humanize - a random LFO (`lfo03_wave=-1`, ~5 Hz at cc117 = 32) to pitch
  (cc119 "Unsteady Vibrato", 6 ct max), to the vibrato rates (cc118) and to the wind-noise layer (`lfo03_volume_oncc122`
  4 dB). At the patch's CCs (119 / 118 = 0) it is inactive; with them raised, sfz.py plays it as a sine on the zone
  vibrato (`lfoN_wave=-1 (played as a sine)`) - map a random LFO's pitch / volume depth onto the instrument's flutter
  instead (one primitive); the breath layer (cc122 = 16, done 2026-10-15) then also gets its slow random level wander.
  (The hero sax's 10 Hz autopan tremolo covers the audible part of this since hero/sax v2.)
- **Weresax breath layer follow-ups** (2026-10-15): the engine's `*noise` region is a 1 s loop read at the key's
  playback rate (a held note repeats the same noise every second; low keys resample it darker) - sfizz plays SFZ noise
  unpitched and unlooped. Inaudible at the trace level the hero uses (-12 dB under the sax in 3-16 kHz); revisit
  (a per-voice seeded noise generator in the sampler) if a patch ever raises cc122.
- **lamplight-avenue on the v2 hero sax**: the song stays on `hero/sax_clean` (its octave-tenor automation and
  doubles are built on the v1 layers); moving it to the 70s sax means dropping that automation - ask the user.

- **Jazz references**: a Beegie Adair trio track (her site's previews are streaming-only) and a vocal jazz track in
  `assets/refrences/` would make `compare` useful for the jazz presets.
- **Before publishing any song: licenses.** The 224XL IRs are unclear, jRhodes3d is CC-BY-NC, the Kalthallen /
  Overdriven / SampleRadar packs are no-redistribution, CC-BY credits are printed in `credits.txt`; Hanami's bundled
  vocoder is CC BY-NC-SA and TIGER is non-commercial (a commercially clear voice needs its own approval).

## Parked (by decision)

- Not worth it (batch 3): the synthwave references disagree (Sunset too dark, Deckard's Dream too bright, Nightcall too
  wide: already measured, pick per style); SoulX-Singer A/B (prepared in `songs/_demo_vocal/soulx_ab.py`, blocked by
  disk on C:); the master post-pass above 19 kHz; the stack's minor gaps (glide in crossfades, muted layers render);
  prism's per-phrase level match; a players' journal for the making-of; the genre-package leftovers.

- The other five synthwave songs' `-piano` passes (branches `song/<slug>-piano`) were stopped. System work is
  validated on one reference song (`children-of-neon`), and more songs come once the system is polished.

- **Songbook ballad with strings: open findings from songs/when-the-year-turns-gold** (jazz_ballad + four SSO / VPO
  string sections + Hanami `ballad`, 62 BPM; done: `lead='vocal'` - both vocal ballads migrated, balance unchanged -,
  the held-note / fermata warning, `mix`'s voice vs band line, the slow ballad vibrato). (2) `symphony_orchestra`
  sections behind a close voice needed +9 dB, the harp +12 dB (at +8 'nearly inaudible', at +16 too loud): an
  `orchestra behind a band` level option. (3) A rubato verse without a bass has no left hand: `jazz.comp(voicing=
  'rootless')` alone is thin - a `pianist.accompany(prog, answer=line, roots=True)` would replace the hand-written
  `VERSE_LH`. (4) The mixer's jazz window for brushes (-16..-13 under the lead) flags a deliberate "stirs only" ballad
  (`drums_too_quiet` at -17.7): a `ballad` sub-profile or a per-song target override. (5) The mic pull's depth does not
  grow with a note's length. (7) VPO/SSO violins II sustain: 2 masked sample discontinuities (-37 / -43 dBFS, bars
  55 / 57, likely a loop point of one zone). (8) `out/lyrics.txt` is still a hand copy (generate it from the `sing()`
  calls, markup stripped). The jazz_trio / soul_ballad rows of `jazz.VOCAL_LEAD` are estimates (no song yet).
