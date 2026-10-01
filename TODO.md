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
- **Choir samples speak slowly at low velocity.** The attack slows as velocity drops, so a soft answer took about
  0.4 s to be heard. The epic worked around it with velocity 120 plus an `instrument.expression` lane and a 100 ms
  sample offset. The choir patches (`sampled/choir*`, fairlight) should do this by default, and the
  hornist/arranger docs should say so.
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

## Medium: tools, engine and library

- **Guitar lead lanes (fretwork):**
  - Everything on one lead track must go through ONE `fretwork.render` (one automation lane per target; points of two
    writers in the same window would interleave). `guitarist.lead(gestures=False)` automation on a track the soloist /
    fretwork also plays clashes on `instrument.pitchbend`. A per-track lane registry that sums additive lanes from
    every player at compile would lift it.
  - The hero guitars are mono legato stacks: a unison / oblique bend's held string plays on a twin track
    (`fretwork.twin_track`, a second instance of the stack). `bendfollow` (the sampler's per-note bend latch) only
    helps polyphonic guitars (`sampled/hero_guitar_clean`).
  - Palm mute on the hero is emulated (the voices' low-pass, the 'mute' lane): its DI zones load only the 'open'
    articulation. Add the FSBS 'palm mute' / 'dead note' keyswitches to the hero zones (hero_guitar.play would have to
    copy each keyswitch note into every velocity zone - a stack routes a note to one zone by velocity).
  - The wah goes ahead of the amp in every zone of a hero stack (5-6 instances); a stack-level pre-split insert would be
    cheaper. The pick scrape / finger squeak are synthetic (va noise through an amp); a sampled string-noise pack would
    be more real.
  - The sampler's `harmonic` follows `key + tune` as the note's fundamental: zones with a pitch keytrack other than
    100 % or a detuned root would isolate the wrong partial.
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
  - No 6/8 or 12/8 feel.
  - Cymbal chokes and the live hi-hat work on the `sampled/big_rusty_kit` / `unruly_kit` / `mf_natural` layouts only
    (their choke keys; `Kit.live_hat` = the SFZ CC4 imported live). The band presets' `rock_kit()` copies tom 47 over
    the Big Rusty crash choke (50), so `ending='choke'` has nothing to grab there; kits without choke samples need a
    silent choke zone (`*silence` + `offBy` on the cymbal zones: a kits.py helper) - and both silent-notes ears would
    then report those strokes as silent (they must learn that a choke-only key is meant to be silent).
  - Big Rusty's snare layers 2-4 (velocity 14-51) are recorded at nearly one level (-35 dB RMS rendered for velocity
    15, 25, 35, 50; then +8 dB at 65): ghost notes and soft taps sound alike, and at the same low velocity its toms
    are ~10 dB louder than its snare (velocity 50: tom 45 -24 dB, snare -34 dB). A soft solo passage jumps when the
    hands move to the toms. A per-piece level / velocity curve in `Kit` (or the patch) would let the drummer balance
    it (measured in `the-drummer-speaks`, `.scratch/velcurve`).
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
- **Kick/bass overlap check is touchy.** In `ghosts-of-ocean-drive` it came and went with small bass edits. Its
  stability and thresholds need checking.
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
- **Orchestra: a held note does not follow a crescendo.** `orch.perform` turns each note's start velocity into the
  dynamics lane (long notes get a messa di voce), so a chord held through a written crescendo stays at its start
  level. `unbowed`'s dominant pedal climbed only ~2 LU over bars 9-15 with held tremolo strings / horns / wind chords
  under a velocity ramp of 78 -> 120; re-attacking every held part each bar made it 8 LU. perform() could follow a
  song-wide dynamics map (a function of the beat) inside held notes, or `orch.dynamics` could merge with perform's
  lane instead of competing with it.
- **One keyswitch per section track.** A role that plays two articulations at the same moment (the violas' staccato
  8ths under a marcato tutti stab, the basses' pizzicato under a sustained doubling) gets one of them ("notes at beat
  X ask for different articulations"): 44 collisions in `unbowed`. Options: a second track per role for the
  doublings (`violins1_div`), or the compiler splitting colliding articulations onto a twin sampler.
- **A conductor's arc helper.** `unbowed` rides the master input per section (a `utility` named `arc` first in the
  master chain: soft passages +3..+6 dB, the earlier fortissimos -1..-2.5 dB under the coda) to keep the LRA in the
  classical window (20.9 -> 16.2 LU) without flattening the written dynamics. A `MIX['arc'] = {section: dB}` (with
  in-section points) would make it a logged mixer move instead of hand-written automation.
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
