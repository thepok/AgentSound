# TODO: open findings

Grouped by the tool that owns the fix. Each entry says where it came from, with numbers where we have them. Remove an
entry in the same commit that fixes it; add new findings here instead of losing them in a report. Fixes follow the
user's rule: KISS - a preset / patch / chain / default / data table before new code, the shared tool before song code.

## Endless generators (`agentsound.endless`)

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

## Analysis / checks (engine/analysis, silent_notes, the report)

- **Silent-notes ear gaps**: the compile-time check does not know `{'dir': ...}` samplers or sf2 layers inside a
  stack; the render-time ear cannot hear a silent note that starts with a sounding one on the same
  track (a crash on the kick).
- **Dynamics role inference**: a stack is judged by its first layer only.
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
- `low_end_wide` (mixer) fires on breakdowns without bass or kick (one-more-round: correlation 0.31 / 0.65 below 150
  Hz from reverb / pad residue at a very low level): an energy floor for the low-end mono check.

## Engine: stack / layers

- `layered/piano_strings`, `piano_pad`, `piano_organ` peak at +0.6 to
  +0.8 dBFS on the track.

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
