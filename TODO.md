# TODO: open findings

Collected from the agents' reports (the reviews, études, heroes, players, mixer/mastering and the epic's A&R).
Each entry says where it came from, with numbers where we have them. Remove an entry in the same commit that fixes
it. Add new findings here instead of losing them in a report.

## High: the sound and playing the user will hear

- **Mixer: pick the lead per section.** On `ashes-and-chandeliers` (a multi-part piece), `mixer.auto` chose the oboes
  as the lead and would have cut the finale's melody by 6.5 dB. It needs a per-section lead
  (`lead={section: [ids]}`) and better inference (the melodic part that carries the theme in each section, not the
  loudest melodic role). Also inside a section: matryoshka's minor section hands the voice from a solo cello (4 bars)
  to the piano (4 bars); mix reads 'bed too loud -0.5 dB' for the whole section although the piano is 7 dB over the
  cello in its own bars (per-bar RMS). `unbowed` (a symphonic movement): `mix` took the three solo tracks (clarinet /
  horn / oboe, 3 short sections) as the lead and judged none of the 15 other sections ("no lead plays in half its
  bars"); the theme moves between violins I, the flutes / oboes doubling it and the fugato's entering voice - mixed
  by hand from per-section stem levels (songs/unbowed/MIX.md). The MIX dict has no `roles` key (strict), so the CLI cannot be told either.
  Partly done: a track with `track.feature(section)` is now the lead of that section (`mixer.features(song)`: a bass
  or piano solo is judged against the soloist - jane-street-bossa); a general per-section `lead=` is still open.
- **Choir samples speak slowly at low velocity - the patches.** The attack slows as velocity drops, so a soft answer
  took about 0.4 s to be heard. `orch.Choir` handles it by default now (the speaking velocity + the written level on
  an expression / dynamics lane, early starts), but a choir track played directly (`track.play`, `orch.perform` on the
  film orchestra's 'choir' role) still speaks late: the choir patches (`sampled/choir*`, fairlight) could start a few
  ms into the sample and flatten the velocity -> attack curve by default, and the hornist / arranger docs should
  point to `orch.Choir`.
- **Piano damper / soundboard model.** Found by the Gymnopédie étude: decay inside a bar is 15.3 dB against 11.6 in
  the reference. We need a two-stage string decay and pedal coupling between notes. Half pedal and `sympathetic`
  exist, but they are not a physical model.
- **Soft piano notes lack a bright attack.** Attack vs sustain brightness is 1.18× for ours and 1.37× for the
  reference (Gymnopédie).
- **Melody-aware dynamics and rubato.** `touch()` shapes one arc per phrase and never accents single notes: 7.7 dB vs
  9.0 in the Gymnopédie reference. Rubato does not linger on phrase peaks, and there is no bar-wise "take time here"
  tool: the Nocturne's bar-length variation is 0.075 vs the reference's 0.13.
- **Trills are too even.** Unevenness is 0.19 for ours vs 0.47 in the Nocturne reference.
- **Hero sax velocity response through its chain.** 0.35 dB per 10 velocity steps after the compressor (1.2 dB
  before it). The hornist's accents compensate; the patch itself should not flatten velocity so much.
- **Tutti tone of the epic finale is mid-heavy.** Mids are +4.2 / +7.6 dB vs the film reference in finale / summit.
  The theme lives there, so voicing and EQ need a better answer than cutting the tune.
- **Epic Part III solo** is only 0.2 LU louder than anthem2. The energy peak inside Part III is weak.
- **The ballad piano in the epic has no air** (soft-hammer grand, almost nothing above 7 kHz). A brighter ballad
  variant, or `hammers` tuned per register, would fix it.
- **Guitar tone, after the v2 heavy hero (songs/kestrel-bay/TONE.md):**
  - Not yet heard: the tube `amp` + neck-pickup tone was judged by numbers (harmonics, bands, sustain, dynamics,
    `compare` vs Sweet Child O' Mine) - A/B `songs/kestrel-bay/out/tone_ab/` by ear before more guitar songs.
  - Pick attack vs picking dynamics: a sampler filter envelope that opens the neck filter at every pick (2 octaves,
    100 ms) made every onset equally bright and took the velocity part of the note dynamics 1.9 -> 0.0 dB, so the hero
    has none. A velocity-scaled `filterEnv` depth (SFZ `fileg_vel2depth`) would give a bright pick that still follows
    the picking.
  - The FSBS DI is a bridge pickup only: the key-tracked low-pass emulates a neck pickup, but G4 and D5 (DI samples
    whose 2nd harmonic is +2.5 / +2.9 dB over the fundamental) still come out of the amp with h2 near h1. A real neck
    pickup DI set, or a pickup-position comb per note, would be better.
  - The `rock` analysis profile's balance curve is darker in the mids than a real guitar-solo record: with the hero
    1-2 dB over the band, kestrel-bay's solos read `balance_mid_high` +4.0..+4.5 dB / `balance_presence_high` ~+4 dB
    (limit +4) while against Sweet Child O' Mine's solo the same mix is within +-1.5 dB from 0.8 to 6 kHz.
    Re-derive the profile from guitar-led records.
- **The rock pass (the-drummer-speaks, songs/the-drummer-speaks/ROCK.md): verify by ear.** Judged by numbers against
  Sweet Child O' Mine's band sections only (the A/B clips in `songs/the-drummer-speaks/out/rock_ab/`):
  - Snare punch in the dense choruses: 7-8 dB over its surroundings vs 10-12 in the record (the kick improved 11.6 ->
    15 dB, ref 21). Neither the kit's slow-attack compressor, a 2 dB snare-keyed duck of the wall (dropped: no
    measurable effect, a ghost key track) nor the master's limiting moved it; the open power chords + octave ring
    under every hit. Try: a snare-only transient path (the kit split: a snare track with its own compressor / plate),
    shorter chorus chords (the riff player's 'drive' grip in the chorus), or less wall level in the hooks.
  - The wall is much wider than the record at 250-500 Hz (45-54 % vs 9-20 %; L/R correlation 0.3-0.4 there): two
    different guitars + `guitarist.double`'s tuning drift. The user asked for a wide wall; check the low-mid width and
    mono by ear (mono sum 0.9 dB quieter, mono_compat ok).
  - The rhythm guitars' note dynamics come only from the articulation: through the driven amps velocity moves the level
    ~0 dB (flat_dynamics info). A harder pick on a real amp is brighter and a little louder: velocity zones like the
    heroes', or a velocity -> amp input / bright cap lane, would give the wall picking dynamics.
  - The mixer tags `gtr_r` as a 'low' part in the-drummer-speaks (its verse riff is palm-muted single notes on E2) and
    trims it with the bass; role inference should keep a guitar a guitar (patch / track name).
  - Every other song on the rock presets / guitar patches (ashes-and-chandeliers, kestrel-bay, lamplight-avenue,
    `_demo_soloist`, `songs/_bands/*`) now plays through the tube amp, the calibrated Big Rusty, the new drum bus and the
    bass rig - not re-rendered (one-song iteration); re-check their mixes when they are touched.
  - `songs/_bands/rock_band` (the preset demo) now warns: the intro riff's kick + bass unison (separation -3.3 dB:
    they hit together - the new check measures it) and flat dynamics on its gtr_r / band lead (velocities 89-117 /
    90-113 through driven amps). Give the demo velocity arcs (or use the riff player) and decide whether a locked
    kick + bass unison should stay a warning.
  - No bass cabinet IR is installed: `bass_rig` rolls the amp + DI off with an eq ('cab' 4.5 kHz). An 8x10 / 4x10 IR
    would be more real (fetch one into the manifest).
- **Guitar solos (kestrel-bay, fretwork / soloist): verify by ear.** Everything was judged by numbers and images
  (stem pitch tracks: vibrato 5.7 Hz 0..+50 ct up from the note, the dive B5 -> B4 in 1.3 s, the pinch's partial 6
  at 2 kHz; lead note dynamics 5.4 dB). Untested by ear: whether the bend overshoot (4 + 3 x amount ct) and the
  up-only vibrato read as a player or as wobble, whether the 'harmonic' feedback bloom sounds like amp feedback or
  like a filter sweep (a real feedback note also locks / detunes slightly and keeps growing; ours holds the note's
  peak level, falling 1.5 dB/s), and the pinch squeal's level through the zones.
- **Soloist move choice is nearly fixed by energy / density.** Seeds barely change which move a slot gets (kestrel-bay
  outro: seeds 22-28 all chose motif / slides / chug / sweep-or-tremolo / scream); variety across a song comes from
  the shared budget's `played` penalty (0.35 per use) and per-solo `weights`. More moves per role (climax: only
  scream / feedback / dive / pinch / double_stop / tremolo / trill) and a seeded spread in the scoring would give two
  solos more different shapes.

- **Sung vocals (feat/singing, `agentsound.singer`): not yet heard by the user.** Everything was judged from
  spectrograms, the timelines and the report (no listening): diction, buzz and naturalness need an ear. A/B files in
  `songs/_demo_vocal/out/` (`ab_robotic` vs `ab_singer`, `ab_pitch_model`, `ab_player_pitch`, `ab_tiger`,
  `vocal_dry`, `vocal_demo`). Open questions for that listen:
  - `pitch='hybrid'` (the default): the voicebank's pitch model approaches notes from below on its own; the player's
    scoops are scaled x0.6 on top (`singer.HYBRID_SCOOP`) - they may still stack into a "sliding" voice.
  - Breaths are the bank's `AP` token at `breath_db` -4 dB (pop): level and colour unverified; a phrase start right
    after a short gap may sound gasped.
  - Consonants: lengths are the duration model's predictions x the style's `cons`, squeezed to <= 45 % of the note
    before (word-final codas keep `singer.DICTION` minimums, onsets 30 ms, a cluster may take up to 60 %); very fast
    lines can still end under the minimums (`singer.diction()` warns `coda_short`). Hanami's readme: a short `t` / `d`
    becomes a flap by itself - not checked.
  - Word-final stops in LEGATO before a consonant-initial word ("night belongs", "hold me") stay unreleased, as in
    connected English (measured on Hanami: the burst ~29 dB under the vowel; a closure or more lift did not release
    them reliably). Before a rest they are released (closure + release vowel). If such a word must be crisp, leave a
    short gap after it (>= 80 ms: the rest path) - or find a model-side fix.
  - Vocoder buzz / metallic edges on long high notes (the banks' own vocoders) - unknown until heard.
- **Vocal note dynamics in the report.** The vocal track plays one trigger note per phrase (the takes), so
  `nodes[].dynamics` reads "too few notes" and `flat_dynamics` never judges a sung line. The sung notes (one per
  syllable, with their velocities) should be handed to the analysis (e.g. as the node's analysis notes).
- **Vocal expression lanes.** The two banks have no energy / breathiness / tension embeddings (no `dsvariance`); the
  singer blends the voice modes (soft / power) per frame instead. Banks with a variance model are not driven yet
  (the runner has no `variance` op), and the vibrato does not follow the air like the hornist's.
- **`build --section` and vocals.** A phrase whose take starts before the rendered section is not heard (one-shot
  triggers); render from the phrase start (`--from-beat`).
- **Licences of the voices.** Hanami's voicebank allows commercial use, but its bundled AI❤dolGAN vocoder is
  CC BY-NC-SA 4.0: whether rendered output is covered is unclear - the build warns "non-commercial voice". TIGER is
  non-commercial outright. A commercially clear voice (another bank with an open vocoder, e.g. one using the openvpi
  NSF-HiFiGAN) would need its own approval.
- **SoulX-Singer (zero-shot, Apache-2.0) not evaluated yet** as a third A/B option; only with a licensed prompt
  (`voicebank.check_prompt`: a Hanami render), never SoulX's bundled prompts or a dataset without synthesis consent.
  Prepared: `agentsound/voicebank_runner/soulx_runner.py` (WSL, score control, torchaudio-free loading) and
  `songs/_demo_vocal/soulx_ab.py` (prompt = one Hanami take + metadata from the singer's timeline; target = the
  demo score) + the `soulx` variant of the demo. Blocked 2026-10-01: the host's C: drive (which holds the WSL disk)
  ran full during the 2.7 GB weight download (a torch venv of ~7 GB had been added before); the venv and the
  partial weights were removed again. Needs ~10 GB free on C: (or the WSL disk moved) - then: venv (torch 2.9.1,
  transformers 4.41.2, accelerate, omegaconf, soundfile, scipy, librosa, numpy<2), model.pt only (not the SVC model,
  not the 6.4 GB SoulX-Singer-Preprocess pack: our own metadata replaces it), `python songs/_demo_vocal/soulx_ab.py`,
  `make_ab.py soulx`.

## Medium: tools, engine and library

- **Signal-chain order review (fix/chain-order): verify by ear, and what it left open.** Judged by numbers and
  level-matched A/B clips only (`songs/<slug>/out/chain_ab/`: kestrel-bay solo + bed stems, the-drummer-speaks chorus /
  verse + the rooms alone, chrome-leviathan chorus + the leads / stab alone, ghosts-of-ocean-drive sax solo, unbowed
  t1 hall). Open:
  - The orchestra hall's crossfeed (0.5) made the Musikverein return mid-heavy (its two IR channels are alike):
    `HALL_WIDTH` +0.3 gives most of the side back (not on the church IR: it went 257 % wide); whether the hall now
    sounds around the listener or just narrower needs an ear. The trims were measured on two demos: the hall returns
    of ashes-and-chandeliers (-0.8 LUFS) and film_orchestra (-0.5) came out a little lower. The library's 2-channel returns (`bus/ir_concert_hall`, `ir_salon`, `ir_church`, `ir_opera`,
    `ir_hall_large`, `ir_drum_room`) and the jazz salon still have no crossfeed (solo piano / jazz songs untouched).
  - rock_band's clean band room (crossfeed 0.5, +2.5 dB, measured on one song) is narrower than the shared crushed
    room was (width 82 -> 69 % on the-drummer-speaks): listen to the rooms-only clip before more rock songs.
  - The hero synths (`hero/synth`, `hero/piano_synth`) keep a doubling layer (halo micro-shift / the piano layer's
    chorus) before their compressor / tape: allowed in `chain_order.ALLOW`; the clean fix is the doubler after the
    chain stages (a layer-level 'post' fx) - it changes measured heroes, so not done in the review.
  - A pre-fader / pre-insert key does not follow the key's fader: only the hero wrapper moves the thresholds with
    it (`HeroInfo.key_fx`); `s.sidechain(..., tap=...)` by hand needs its threshold set for the hotter signal. A
    `tap`-aware threshold helper (or a ducker 'keyGain' param) would make that automatic.
  - Patch sends cannot carry a tap (only node sends: `sends={bus: (dB, tap)}`); a patch-level parallel bus send
    would need it.
  - `bands.master_chain` lives in bandlib/rock.py (rock, pop and jazz use it); the synthwave presets replace the
    master (`master.use`) and the orchestra checks for a limiter itself - one shared guard in agentsound/bands.py.

- **Vocal jazz needs a piano that answers the voice** (songs/jane-street-bossa, the first sung jazz song). Under
  the voice the piano comps with `jazz.comp(answer=line)`, but its short answers in the voice's rests (an echo of
  the hook, a run into the next phrase) were written by hand per part (`FILL_*` notation at the gap positions) and
  harmonized through `jazz.chorus` with `fill=0`. A `pianist.answers(vocal_line, prog, bpm=, register=, density=)`
  (fills sized to every rest >= 1 beat, ending before the voice re-enters, never above the voice while it sings)
  would make it a building block. Also: `jazz.chorus(comp=...)` on a band without a `comp` track (the `bossa`
  preset) fails on `None.play` - place the comping on the piano or raise a clear error.
- **The vocal hero's jazz defaults**: `hero(family='vocal', genre='jazz')` still writes echo throws on every phrase
  end and a -12 dB hero plate: the sung sections read -8.5 LU of reverb (jazz -20..-10). jane-street-bossa turned
  them off by hand (`echo=False, throws=False`, plate -17, the band's room -15 -> -12.9 LU). The jazz profile could
  carry those defaults (throws off, plate -17, the band's room send).
- **Diction warnings flicker between takes**: a nasal coda in legato gets exactly the warn length (35 ms vs "< 35 ms"
  for a nasal) - 'on' read 46 ms in take 0 and 35 ms in take 1 of the same line. The singer's legato minimum for
  nasals should sit a few ms over the ear's threshold.
- **Section renders report silent notes after the section end**: `build --section head` warned silent_notes on every
  track for notes in the bar after the section (bars 41-43 of a 9-40 section) - the full render has none.
- **`s.arc(within=)` steps need a hold point**: a `(beat, dB, 'smooth')` mark ramps from the previous point over the
  whole span; a step at a part boundary needs `(beat - 0.5, old)` written before it. `within` could take step marks.
- **`bands.make('bossa', without=('guitar', ...))`** keeps the piano at pan -0.5 (placed opposite a guitar): the trio
  leaned 1.8 dB left until the song moved it to -0.25.
- **No jazz reference in `assets/refrences/`**: the straight-jazz songs are judged against the profile only (a Beegie
  Adair trio track, the user's model, and a vocal jazz track would make `compare` useful).

- **Compact song code, phase 2: genre packages on top of the notation** (phase 1 = `agentsound.notation` + the
  foundation helpers; migrated with byte-identical render JSON: ashes-and-chandeliers 993 -> 870 lines,
  perry-street-rain 439 -> 391, midnight-interstate 515 -> 464; the jazz package is done - song.form / ending /
  track.feature, jazz.chorus, walking_bass / brushes(straight=True), romantic.score: perry-street-rain -> 238,
  minetta-lane-waltz 442 -> 261, lanterns-on-carmine 326 -> 223, nocturne-etude 446 -> 190, gymnopedie-etude
  177 -> 153, _demo_jazz 169 -> 130, lamplight-avenue 544 -> 472). The survey found the rest of the length in
  re-implemented section logic. Each package must stay expressive (defaults overridable, raw Clips keep working) and
  prove itself the same way (a song migrated with an identical render JSON). The orchestra package is done
  (`voicing.Harmony`, `figures`, `orch.Score` / `Choir` / `bed`, `voicing.fugue`, `s.arc`; byte-identical: unbowed
  953 -> 598, lux-perpetua 759 -> 513 (+ score.py 233 -> 193), ashes-and-chandeliers 870 -> 711). What is left of
  those three is note data, comments and the songs' own decisions; unbowed / lux keep `follow=False` (their written
  re-attacks) - switching them to `follow=True` is a musical change to judge by ear. The pop / synthwave package is
  done (`agentsound.sections`: `s.section(prog=)`, `track.chords / arp / bassline / plan / rise / lane / levels`,
  `s.transitions`, `speech.voice` + `Words.robot`, `art.perform(preset=)`, `art.throws(spans=)`, `pianist.Player` /
  `top_leads` / `arrange(doubles=)`, `bassist.Player`, `s.beat_at`, `s.breath(cut=)`; byte-identical: chrome-leviathan
  569 -> 482, children-of-neon 565 -> 493, skyline-heartbeat 521 -> 429, midnight-interstate 464 -> 380,
  ghosts-of-ocean-drive 481 -> 390, polaroid-summer 454 -> 380, orbital-station 433 -> 419, matryoshka 408 -> 341,
  `_demo_lush` 89 -> 79, `_demo_vocoder` 80 -> 73; `_template` shows the idiom). What it left as written, each a
  musical change to judge by ear before adopting the library's way:
  - children-of-neon's sustain pedal lifts only at every 4th chord change (its `pedal()` helper reads
    `Harmony.items` - chord lengths in beats - and multiplies by 4 again); `pianist.pedal(prog, at, lift=0.12,
    early=0.06)` is the per-chord pedal it meant.
  - ghosts-of-ocean-drive: the solo's swelling strings and pre 2's pluck arp play bars 4-8 of their progression a bar
    late (`P.slice(16, 32)` at bar 5; the arp runs a bar into chorus 2 until the breath clears it) - `bars=4` in a
    section plan would put them on their chords.
  - orbital-station's `arp_line` (close position with the root folded into G2-F#3, accents truncated with `int()`):
    `patterns.arp(pattern=, accent=)` voice-leads in a register and rounds the accent (+1 velocity on some notes); a
    root-position voicing for `arp()` would let the song use it.
  - The filter lanes of chrome-leviathan / midnight-interstate and the masters' gainDb / width lanes stay explicit
    point lists (as section lanes they read no shorter: their jumps sit on beats that already carry a point);
    skyline-heartbeat's lead vibrato (a pitch-bend LFO whose depth follows the long notes) and the songs' scoops with a
    lead-in point (`(t - 0.05, 0)`) are their own shapes (`jazz.scoop` starts on the note).
  - A section key change applied to every pitched part (`s.modulate(final, +2)`) was not added: the songs write the
    transposed progression (`P_chorus.transpose(2)`) with its own registers and `transpose=` their lines - voicing a
    transposed progression in the same register is not the same as transposing the voiced chords, and speech /
    fx-hit samplers must not move.
  Open:
  - *orchestra, leftovers*: a harp arpeggio figure (ashes' masque harp), staggered choir entries that climb by scale
    steps (ashes' ascent: `voicing.imitation` places cells, not a held note climbing bar by bar), the lux storm's
    interleaved 16ths (violins I / II from one velocity stream - a two-voice `storm16` that takes a velocity function),
    and the nocturne's own dynamics map (romantic marks) onto `orch.Score`-style marks.
  - Migrate the other songs' note data to the notation (chrome-leviathan: `line` / `mel`; the tuple tables
    elsewhere) - the round trip test already proves every one of their notes is expressible.
- **Notation follow-ups** (phase 1): a Line's extras (gestures, peaks, voices) survive shift / transpose / octave /
  velocity / with_length but not the other Clip transforms (they return plain Clips: the gestures of
  `line.legato()` are gone - re-parse or keep the Line); gesture lanes written by `track.play(line)` merge with other
  writers of `instrument.pitchbend` on the track (the per-track lane registry above would sum them); ornaments need
  `bpm=` at parse time (`notes(expand=False)` now lists them unexpanded in `line.ornaments` - romantic.score realizes
  them - but track.play does not realize them at play time like the gestures; graces `g:` are always expanded);
  `format()` writes absolute pitch names only (no degrees / relative octaves) and splits no notes at bar lines (a
  long note across a bar leaves that bar line out); triplets written in notation count exactly while older code
  added 1/3 in floats (positions differ by ~1e-16 - the render JSON rounds to 6 decimals, so nothing audible).

- **Guitar lead lanes (fretwork):**
  - Everything on one lead track must go through ONE `fretwork.render` (one automation lane per target; points of two
    writers in the same window would interleave). `guitarist.lead(gestures=False)` automation on a track the soloist /
    fretwork also plays clashes on `instrument.pitchbend`. A per-track lane registry that sums additive lanes from
    every player at compile would lift it.
  - The hero guitars are mono legato stacks: a unison / oblique bend's held string plays on a twin track
    (`fretwork.twin_track`, a second instance of the stack). `bendfollow` (the sampler's per-note bend latch) only
    helps polyphonic guitars (`sampled/hero_guitar_clean`).
  - Palm mute on the hero is emulated (the voices' low-pass, the 'mute' lane; no installed pack has DI palm-mute
    samples - the rhythm guitars' `sampled_guitars.PALM` is measured against real amped chugs): its DI zones load only the 'open'
    articulation. Add the FSBS 'palm mute' / 'dead note' keyswitches to the hero zones (hero_guitar.play would have to
    copy each keyswitch note into every velocity zone - a stack routes a note to one zone by velocity).
  - The wah goes ahead of the amp in every zone of a hero stack (5-6 instances); a stack-level pre-split insert would be
    cheaper. The pick scrape / finger squeak are synthetic (va noise through an amp); a sampled string-noise pack would
    be more real.
  - The sampler's `harmonic` follows `key + tune` as the note's fundamental: zones with a pitch keytrack other than
    100 % or a detuned root would isolate the wrong partial.
- **Jazz package follow-ups** (phase 2, jazz):
  - lamplight-avenue still hand-wires what the library has, because adopting it would change the sound (render JSON):
    the hero sax chain + carve + sidechains (`hero(sax, family='sax', bed=[...])`), the drum grids per section
    (`drummer.arrange`), `pedal_points()` (pianist.pedal / bandlib.jazz.pedal add a release at the end), the guitar's
    'b' / 'v' marks (notation `^bend` / `^vib` are sampled gestures, not the 3-point bend). Try them by ear on the
    song, then migrate.
  - `jazz.chorus` plays piano / comping / bass / brushes; the horn (horn_line per part, with its own phrasing across
    parts) and per-part extras (bass fills, piano fills in the horn's gaps, bombs) stay hand-placed around it.
    lanterns-on-carmine's skip notes alternate swing / triplet by the seed's parity (`skip_grid=jazz.each(...)`).
  - `song.form` names sections with tokens: a section name with a space ('piano A1' in _demo_jazz) needs
    `s.section`; a part used by two sections is one Progression object (fine: progressions are immutable).
  - `romantic.score`: the left hand is its own entry grammar (accompany entries per slot), not notation; `Score.touch`
    / `rubato` cover the gymnopedie's loops, but its left hand (bass on 1, the chord on 2, rolled with a shared rng)
    and the pedal every bar are still song code - a `perform(style='satie')` would need to reproduce that rng order.
- **Section renders report silent notes after the section end** (`build --section solo`: bass / piano / pad / drums
  notes at the first bars after the section, "made no sound") - the preview stops before them; the report should skip
  notes that start after the rendered span.
- **power_ballad's echo bus idles under a hero lead** (the hero has its own echo): reverb_inaudible on kestrel-bay
  until the clean guitar / piano were sent to it.
- **Mixer:**
  - The `children-of-neon` validation was never re-rendered after the -5.5 dB bed window and verse-relaxed limits.
  - The vocoder track `robot` is tagged as bass.
  - Levels are unweighted bar RMS plus one whole-song K offset per part, not per-section LUFS.
  - `auto()` lowers the master input by 0.5-0.8 LU and only logs it.
  - **A group lead.** A choir split into voice tracks (`lux-perpetua`) is measured as one voice against the
    SUMMED orchestra groups. With `--lead choir_s ...` it proposed cutting every section by 5-7 dB, an a-cappella
    mix. The mix engineer measured it by hand: dry stems, the choir summed vs the instruments in its register.
    `lead=` should take a group, and so should the per-section lead above.
  - **Stereo stems see a balance pan.** A track's `pan` on a stereo sample set is a balance, so a set that leans
    needs a counter-pan. The SSO mixed chorus leans by pitch range: the soprano notes right, the tenors / basses
    left. In `lux-perpetua` the tenor sat +2.3 dB LEFT at pan +0.14. Seating S A T B took pans -0.7 / -0.33 / +0.6
    / +0.65 at width 0.8 and cost 0.5-2.1 dB of pan law. Options: a `seat` helper (a width + a pan that measure
    the lean), or re-levelled / centred choir zones in the patch.
- **Mastering:**
  - The post-pass is not bit-transparent above ~19 kHz.
  - `mastering.apply()` only estimates the loudness change inside the song chain.
- **Dynamics ear role inference:** in `children-of-neon`, the preset's supersaw bed (track id `lead`) is flagged
  `flat_dynamics` although it is a bed. Beds named "lead" by a preset should not count as leads, and the stack is
  judged by its first layer only.
- **Stack / layers:**
  - Legato glide is lost inside a crossfade zone.
  - Articulation marks are not supported on a stack.
  - Muted layers still render and load their samples.
  - Layers' own patch sends are dropped.
  - Delayed notes restart at the preview start.
  - Only the pedal is delayed with a delayed layer.
  - `layered/piano_strings`, `piano_pad` and `piano_organ` peak at +0.6 to +0.8 dBFS on the track.
- **Drummer:**
  - No 6/8 or 12/8 feel (looked at in the rock pass, not cheap: the drummer's beat patterns are 16th grids in 4/4 -
    the 'shuffle' style only swings them, triplet fills exist; a 12/8 ballad / 6/8 groove needs a triplet grid for the
    patterns, hands and solo vocabulary, and the bassist's / guitarist's patterns with it).
  - Cymbal chokes and the live hi-hat work on the `sampled/big_rusty_kit` / `unruly_kit` / `mf_natural` layouts only
    (their choke keys; `Kit.live_hat` = the SFZ CC4 imported live). The band presets' `rock_kit()` copies tom 47 over
    the Big Rusty crash choke (50), so `ending='choke'` has nothing to grab there; kits without choke samples need a
    silent choke zone (`*silence` + `offBy` on the cymbal zones: a kits.py helper) - and both silent-notes ears would
    then report those strokes as silent (they must learn that a choke-only key is meant to be silent).
  - The hands' physics run move by move (`drummer.perform()`) or slot by slot (`soloist.solo()` with
    `drummer.vocabulary()`): a rebound or an up-stroke across a boundary is not modelled, and `check()` / the limb
    resolver do not see two neighbouring soloist slots together (a stroke at a slot's very end and one at the next
    slot's start could collide). A vocabulary `place()` that re-runs `_resolve` over the whole solo would close it.
  - The soloist's statement / answer / develop phrases all open with the motif as the call (by design of the arc):
    in a 34-bar drum solo the riff's rhythm is heard ~10 times. Fine as an identity, but a drum vocabulary could
    offer its own 'call' moves (the motif orchestrated, fragmented on the toms) so the calls vary more
    (`the-drummer-speaks`).
  - `restrike` (the sampler's re-strike damping) is off by default and set only in `the-drummer-speaks`
    (`restrike=6`); the drum patches and the band presets do not use it yet (validate on one song before changing
    the patches).
  - The pop Chart kit's hat foot is the closed-hat sample.
  - An intro (energy 0.38) and a `groove` section read the same drum level.
  - The `songs/_bands` demos are not ported to the drummer.
- **Silent notes in the songs** (found by the silent notes ear): `ashes-and-chandeliers` `choir_f` plays 41 notes
  under G4 on `sampled/choir` (the VPO female choir has samples G4-C6 only; the patch notes said F3-A5), `choir_m` 4
  on G4 (G2-F#4), `tuba` 1 on C1, `gtr3` 1 on E6; `polaroid-summer` `choir` 37 notes under G4; `orbital-station` 14
  tambourines on the TR-808 kit (no tambourine: map one from the pack's 80s Digital / Chart kit).
- **Silent notes ear, gaps.** The compile-time check (`agentsound/silent_notes.py`) knows sampler zones, the drum
  machine and stack layers, not SoundFont key ranges (sf2 drum kits lack keys too) nor `{'dir': ...}` samplers; the
  render-time ear cannot hear a silent note that starts together with a sounding one on the same track (a crash on the
  kick), so those stay unseen for sf2 tracks. Reading sf2 preset key ranges in Python (or asking the engine) would close it.
- **Synthwave references disagree.** Sunset says "too dark", Deckard's Dream "too bright", Nightcall "too wide".
  Per-style reference choice should be documented in `recipes/synthwave.md`.
- **Bassist:** the `funk_band` demo has a remaining drums/bass masking warning.
- **Synth heroes:**
  - They are darker than the references in lean mixes (presence -2.2 dB vs Nightcall).
  - Hooks below C5 need a low-mid dip on the bed.
  - `hero/darksynth_lead` needs +4.6 dB of patch gain.
- **Hero piano:**
  - Listen to the Dimension-D and tape flutter for detune / seasick shimmer.
  - Its left hand shares the bassist's octave in a band.
- **Tempo:** millisecond timing in the drummer and hornist assumes a constant tempo.
- **Making-of film (`agentsound/makingof`), from the first pilot (ashes-and-chandeliers):**
  - The players do not log their moves with absolute beats: `capture.py` recovers the placement by patching
    `Track.play` (identity, the placing method's frame, else note matching). A `journal` of placements in the players
    themselves would be exact and simpler.
  - "Before" clips need the judged commit in AR.md (`Judged: ... @ <sha>`) and a version that still builds with
    today's library; there is no per-section old render yet (the whole judged song renders once, ~12 min).
  - Breeze narration is ~8-10x slower than real time on this GPU (a 3-minute voice-over takes ~30 min the first
    time; cached after). German is not attempted (Breeze speaks English and Chinese well).
  - Stems are post-fader and dry of the shared reverbs, so a soloed group in "meet the tracks" sounds drier than in
    the mix.
- **One keyswitch per section track.** A role that plays two articulations at the same moment (the violas' staccato
  8ths under a marcato tutti stab, the basses' pizzicato under a sustained doubling) gets one of them ("notes at beat
  X ask for different articulations"): 44 collisions in `unbowed`. Options: a second track per role for the
  doublings (`violins1_div`), or the compiler splitting colliding articulations onto a twin sampler.
- **The conductor's arc as a mixer move.** `s.arc(rides, within=)` (unbowed) is the helper now; a `MIX['arc'] =
  {section: dB}` key would make it a logged mixer move (`mix --auto` could propose it from the per-section LUFS and
  the profile's LRA window), and the pop package's lanes should extend `s.arc` rather than add a second ride.
- **unbowed's intro: two passages sit two beats after their chords.** `H(sc.INTRO[3:9], t0 + 8)` places the rows that
  start at beat 6 of the table (G7/F, Cm/Eb, Fm, G7 ...) at beat 8 under the violins' cell (Fm under its B4), and
  `winds(H(sc.INTRO[11:15], t0 + 26))` the rows from beat 24 (the rest, Db, Fm/Ab, Ab7) at 26 - the Ab7 then runs into
  the G pedal at 32 while the strings play Fm/Ab / Ab7 on time. Kept as written for the byte-identical migration
  (found while moving the tables onto `voicing.Harmony`, whose slices keep their own position: `H(sc.INTRO, t0)[3:9]`
  sounds with the table). Listen before changing it.
- **A zone's release wins over the track's `release`.** The VPO choir's `ampeg_release=1.25` joins short syllables
  into one vowel pad (lux-perpetua's Dies irae: re-attack depth 6-8 dB per written note), and `inst.sfz(...,
  release=)` cannot shorten it (only zones without their own ampeg_* take the param). lux-perpetua parts the
  syllables with an `expression` gate after each note (falls to 0.4 in 50 ms, opens on the next attack: 22-25 dB).
  A per-track release scale / override on the sampler would let a choir or a sustain section speak short.
- **No basset horns.** Mozart's Requiem needs them; the SSO clarinets stand in, kept in their low register.

## Low: samples, housekeeping, docs

- **sampled/choir_mixed loop seams on long held notes.** matryoshka's coda holds "ah" notes of 6-16 beats: 7-10
  low clicks per render in the choir stem (worst -45 dBFS, 18 dB over its surroundings; masked in the mix, clicks 0),
  although the patch notes say "clean loops". Re-articulating every 2 bars did not remove them.
- **hornist Performance.place(level=) is a target name, not a level.** Playing one performance of a bowed line
  quieter than the next (a counter-line under the piano) needs a hand-written gainDb lane on the track; a dB offset per
  performance would keep it in the player (matryoshka, minor section).

- **Samples:**
  - YDP grand has no SFZ variant (only SF2).
  - The Iowa alto sax and double bass files are multi-note runs and need slicing.
  - Compare `karoryfer-bigcat-cello` with `sampled/solo_cello`.
  - SSO crotales (octave mapping) and SSO string harmonics (loops click) are unusable as they are.
  - `choir_f` has 2 loop seams (masked clicks in the epic).
  - `sampled/choir_oh` (NBO) has samples D2-C#5 only (the patch note said "C3-C6"; corrected): everything above
    C#5 is the top sample stretched. `film_orchestra(choir='oh')` still gives the role a sweet range of C3-A5.
  - `sampled/choir_male`: a held D3 at a phrase end, exposed under a solo trombone, clicked in the mix (medium, a
    loop seam; `lux-perpetua` v1-v5).
  - A 4-beat fermata chord (~9 s) at 48 BPM passes loop seams in `choir_mixed` (S, B), the SSO trumpets and violins
    II: 11 masked clicks in `lux-perpetua`.
  - The orchestral basses have 5 masked clicks.
- **`test_sf2` speed check** (20× realtime) fails under heavy parallel load (18×). Make it load-aware or relative.
- **Docs:**
  - `catalog --markdown` mentions `docs/CATALOG.md`, which does not exist.
  - `.gitignore` excepts a nonexistent `assets/samples/README.md`.
  - `CLAUDE.md` still repeats the workflow that README.md now covers.
- **Disk:** C: is ~99 % full. Agents' scratch renders must go to D: (git-ignored folders in their worktrees).
  Periodically clean `%TEMP%\claude\...\scratchpad` and stale worktrees (`git worktree prune`).

## Waiting on the user

- **Beegie Adair reference.** Her site's previews are streaming-only (403), so a bought or saved track in
  `assets/refrences/` would let us calibrate the jazz trio preset.
- **Before publishing any song:** licenses. The 224XL IRs are unclear, jRhodes3d is CC-BY-NC, the Kalthallen /
  Overdriven / SampleRadar packs are no-redistribution, and CC-BY credits are printed in `credits.txt`.

## Parked (by decision)

- The other five synthwave songs' `-piano` passes (branches `song/<slug>-piano`) were stopped. System work is
  validated on one reference song (`children-of-neon`), and more songs come once the system is polished.
