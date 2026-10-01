# Synthwave recipe

Retro-futurist 80s sound: analog polysynths, DX7, drum machines with gated reverb, huge chorus and
reverb, sidechain pumping, nostalgic minor-key harmony, cinematic night-drive mood.

## Sub-styles (pick one per song, say which in song.py)

| style | tempo | feel | signature |
|---|---|---|---|
| Outrun / nightdrive | 100–118 | driving 8th/16th octave bass, four-on-the-floor | Kavinsky, Lazerhawk |
| Dreamwave / chillsynth | 80–100 | laid-back, lush pads, half-time drums | FM-84, Timecop1983 |
| Retrowave pop (instrumental) | 110–125 | punchy, anthemic lead hooks | The Midnight, Gunship |
| Darksynth | 110–140 | aggressive distorted bass, dark minor/phrygian | Perturbator, Carpenter Brut |
| Sci-fi / soundtrack | 70–100 | arps + slow pads, sparse drums | Stranger Things (S U R V I V E), Vangelis |

## Harmony

- Keys: minor (A, E, F#, C#, D, F minor common). Aeolian is home; borrow Dorian (major IV) for hope,
  Phrygian bII for darkness, and the major subdominant iv→IV lift.
- Classic progressions (minor, 1 bar each unless noted):
  - `i – VI – III – VII` (Am F C G) — the anthem.
  - `i – VII – VI – VII` (Am G F G) — driving, unresolved.
  - `VI – VII – i – i` (F G Am Am) — lift into the tonic.
  - `i – iv – VI – V` (Am Dm F E) — cinematic, harmonic-minor V for tension before drops.
  - `i – VI – iv – VII` / `i – III – VII – VI` — melancholic variations.
  - Chorus lift: move the same melody over `VI – VII – i` or modulate up a whole step for the last chorus.
- Colour: add9, maj7 on VI, sus2/sus4 on VII, min9 on i for dreamwave. Pads use open/spread voicings;
  keep the lead above ~A4, pads C3–C5, bass below C3.
- Pedal points: keep the bass on the tonic while chords move (tension), release on the chorus.

## Rhythm & drums

- Kick four-on-the-floor (outrun) or kick on 1 and the "and" of 2/3 (dreamwave half-time).
- Snare on 2 and 4 with **gated reverb** (the 80s sound): `gatedreverb` on the snare, or a send to a gated bus.
- Hats: 8ths or 16ths with accents on the off-beats; open hat on the "and" of 4 before transitions.
- Claps layered with the snare in choruses. Toms fills (high→low 16ths) into sections; crash on downbeats of new sections.
- Humanize lightly (velocity jitter, 2–5 ms timing); drum machines were tight, so keep kicks on grid.
- Sidechain: pads, bass and big synths ducked by the kick (`ducker` keyed from the kick, 3–8 dB, release ~ 1/8 note).

## Sound palette

- **Bass**: 8th-note octave pulse (root, root+12) on a saw/square VA with short decay and filter envelope;
  or 16th-note "rolling" bass. DX7 `BASS 1` for funkier lines. Keep sub mono.
- **Pads**: Juno/Jupiter style: 2 detuned saws, slow attack (0.3–1.5 s), long release, low-pass ~2–4 kHz,
  Juno chorus (mode II, or I for subtler; I+II is a fast vibrato-like shimmer), big hall reverb. Strings: DX7 `STRINGS` layered with VA.
- **Leads**: supersaw (unison 7, `unison.detune` 0.6–0.75 — the engine uses the real JP-8000 curve, below 0.4 is only a subtle chorus), or a square/pulse lead with vibrato (delayed LFO);
  dotted-8th ping-pong delay + plate reverb; glide for expressive leads. Brass stabs (DX7 `BRASS 1` or VA brass).
- **Piano hooks** (the alternative to the synth lead - The Midnight, FM-84, Timecop1983, 80s ballads; a thin, beepy
  synth hook is the most common complaint about our songs): `sampled/piano_lead` (Salamander Grand, mono centre,
  high-passed, presence + air, compressed, chorused; `gm/piano_lead` without the pack), or `lead='piano'` on every
  synthwave band preset. Play it high, C5-C7, octave-doubled like a pianist's right hand
  (`hook.clip(octave=5, vel=105).octave_double(-12, vel=0.8)`), velocities 90-115 with accents; a piano decays, so
  write repeated / rhythmic notes (8ths, dotted figures, re-struck long notes) instead of held synth notes, and
  step `instrument.pedal` at chord changes for legato lines. A soft pad under it, or the hook doubled by
  `synthwave/epiano_bright` / `synthwave/arp_glass` at -8..-12 dB, adds the FM sparkle. Calibrated in every preset (the
  demo hooks an octave up, octave-doubled): the piano track as loud as the synth lead or louder (+0.1..+0.9 LU), the
  loudness-matched bands within 2.6 dB of the synth-lead numbers (mids +0.1..+2.6: the higher melody), 0 warnings.
- **Layered hooks** (one track, several instruments: `layered/*`, docs/COMPOSE_API.md "Layered instruments"):
  `layered/piano_saw_lead` (the piano attack over a sustaining supersaw, -8 dB, presence-dipped) and
  `layered/piano_glass_lead` (+ a DX glass octave up and a pad swelling under long notes) are drop-in replacements for
  `sampled/piano_lead` (same calibration; the layer tweaks of the piano chain are `layers.piano.fx.<type>.<param>`).
  Measured on children-of-neon's hook (drop2 vs The Midnight "Sunset" 4:00-4:30, loudness-matched, every hook at the
  same -18.8 LUFS, the song's pedal steps on the hook track): piano_glass_lead brings the most top - the 2.5-12.5 kHz
  gap to Sunset -1.15 -> -0.80 dB at the same fader, same note dynamics (3.3 vs 3.4 dB per phrase) and warnings as
  piano_lead; piano_saw_lead sustains long notes (gap -1.00 dB, note dynamics 3.7 dB; ~0.5 LU hotter at the same
  fader: -4.0 instead of -3.5). The saw ignores the sustain pedal: pedalled, it piled each chord's hook notes into a
  held supersaw cluster (+1.7 LU, a brighter but smeared hook, flat_dynamics 2.2 dB). `layered/bell_piano` is keys,
  not a hook (a stereo grand: the hook went 114 % wide and 1.6 LU quieter).
- **Hero sounds** (`hero/*`, agentsound/patches/hero_synth.py: the lead that stands in front like on a record - the
  sound, its chain, its mix and playing rules in one patch; `hero_synth.perform(line, lo=64, hi=112)` plays it). Use
  them through the hero wrapper, which also applies the mix rules below (bed duck + carve, dips, rides, throws;
  docs/COMPOSE_API.md "Hero sounds"): `hero(s.track('lead', 'hero/synth_lead'), bed=[pad, choir, strings],
  competitors=[arp, keys], genre='synthwave')` (`family='synth'`, `'darksynth'`, `'piano_synth'`):
  `hero/synth_piano` (the FM-84 / The Midnight hybrid: the melody piano's attack over a sustaining hero saw that only
  comes in on harder notes; play it like the piano hook, octave-doubled: `perform(line, double=-12)`),
  `hero/synth_lead` (the fat singing saw lead: two-saw voice + an octave-down square body from G#4 up + a supersaw halo;
  mono, every note re-attacks and glides 40 ms, delayed vibrato, velocity -> level and brightness, tape, Juno chorus,
  micro-pitch double, plate + dotted-8th echo; one line, no octave doubling in the notes) and `hero/darksynth_lead`
  (hard-sync saw over a driven saw body, tube drive: Kavinsky / Perturbator). All at -18.0 LUFS on the audition.
  Space (chain-order review): the synth leads keep their constant echo next to the hall / plate - the dotted-8th
  repeats filling the gaps are the genre's sound; a hero with its own plate bus (sax, voice) drops a quieter preset
  hall send (plate + echo, not three returns); the bed's duck / carve listen to the hero before its echo and ride
  (`tap='pre:air'`), so the pads come back under the repeats and throws. Drive goes in front of chorus / doubler
  (`s.track(..., pre=[fx.saturator(...)])`, the darksynth band's `pre_fx`). Measured
  on children-of-neon's hook (scratch copies, drop2 / lift; the old hook `layered/piano_glass_lead` at -17.8 LUFS: lead
  -9.3 / -7.5 dB under the mix RMS, bed vs lead -0.7 / -1.0 dB, note dynamics 3.7 dB): with the hero mix rules (hero
  about as loud as the piano hook, +1 / +1.5 dB in drop2 / lift, -0.5 dB in drop1 where one pad is the bed; choir,
  strings and violins keyed to the hero 2 dB deeper and -2.5 dB at 1.6 kHz) `hero/synth_piano` reads most in front -
  lead -7.9 / -6.6 dB under the mix, bed -3.2 / -3.1 dB under it, note dynamics 4.0 dB, mix mids +3.8 / presence +2.8 vs
  the profile (the old hook +3.5 / +3.4), no new warnings; `hero/synth_lead` -8.4 / -7.5 dB, bed -1.9 / -1.3 dB,
  dynamics 3.8 dB, no new warnings. Pushed 1 LU without the carve both hit the mid limit (+4.1..+4.2) and the synth lead
  masked the drums' presence; `hero/darksynth_lead` is too bright for this dreamy mix (presence +4.8: a darksynth
  hook). On `songs/_bands/outrun` (chorus, `sounds={'lead': ...}`, the same `perform` velocities) the preset's supersaw
  reads flat (1.4 dB note dynamics), the heroes 4.9-5.7 dB; `hero/synth_lead` and `darksynth_lead` played in C#4-G#5 put
  their fundamentals in the low mids (+4.1, over the limit) - carve: the pad -2 dB at 400 Hz while the hero plays and
  keyed to it, the keys -2 dB at 400 Hz -> low mids +3.7, bed -4.9 dB under the lead (supersaw: -3.1), no new warnings;
  `hero/synth_piano` (octave up, doubled) passes as is. Against Kavinsky "Nightcall" (1:15-1:45) the hero lead narrows
  the low-mid gap (-2.5 -> -1.8 dB) but reads darker than the supersaw (presence -0.2 -> -2.2 dB, vs Sunset -3.8 ->
  -5.6): it is voiced for presence-heavy mixes; in a lean one brighten it
  (`.but(**{'layers.voice.cutoff': 2600})` or `.but_fx('eq', **{'peak3.gain': -2})`).
- **Keys**: DX7 `E.PIANO 1` is THE 80s ballad keys — chorus + reverb. Bells (`TUB BELLS`), marimba for plucky arps.
- **Arps**: 16th arpeggios of the chord tones on a plucky saw/square with filter envelope, ping-pong delay.
- **FX**: noise risers (VA noise + rising filter automation) into choruses, downlifters, reverse-like swells (slow attack pad).
- **Real machines and 80s samples** (sampled, when the pack is installed): drum machines `sampled/linndrum`,
  `sampled/tr808`, `sampled/tr909`, `sampled/tr707`, `sampled/dmx`, `sampled/drumtraks`; big 80s studio drums with gated
  snares `sampled/80s_pop_kit`, `sampled/80s_gated_kit`; the Fairlight CMI's `sampled/fairlight_orch5` (THE orchestra
  hit), `sampled/fairlight_choir`, `sampled/fairlight_aahs`, `sampled/fairlight_strings`, `sampled/fairlight_brass`.
  Any other one-shot folder: `inst.kit('samples/<pack>/<folder>')` (`python -m agentsound kit <folder>` shows the map).

## Arrangement template (~3:30 at 108 BPM ≈ 94 bars)

| section | bars | content |
|---|---|---|
| intro | 8 | pad + arp, filtered (cutoff automation opening), no drums or just hats |
| verse 1 | 16 | drums (no crash), bass, pad, keys/E.piano, sparse counter-melody |
| pre-chorus | 8 | build: snare roll last 2 bars, riser, filter opening, drop kick in last bar |
| chorus 1 | 16 | everything: lead hook, full drums + claps, crash, sidechain pump |
| verse 2 | 16 | variation: different drum pattern/arp, add a new layer |
| pre-chorus | 8 | build again (shorter or different fill) |
| chorus 2 | 16 | hook + harmony line (3rd/6th above) or octave-up lead |
| bridge / breakdown | 8–16 | drop drums, pads + E.piano, new chord colour (e.g. bVI-bVII-i), solo or keytar-style lead |
| final chorus | 16 | biggest: key change up or extra layers, tom fills |
| outro | 8 | strip down to pad/arp, filter closing, long reverb tail |

Every repeat must change something (drum variation, new counter-line, filter state, octave, harmony).
Transitions: fills + crash + riser/downlifter; 1-beat or 1-bar silence (drop) before the chorus is effective.

## Mix targets (check report.json)

- Integrated loudness −12…−9 LUFS (genre is loud but dynamic); true peak ≤ −1 dBTP; chorus 2–4 LU louder than verse
  (a limiter flattens this: thin the verse out rather than turning it down).
- Spectral balance: solid sub/bass (kick + bass own 40–120 Hz, sidechained), warm low-mids not muddy,
  presence controlled (no harsh supersaw 3–5 kHz build-up; EQ dip if report warns), sparkly air from hats/reverb.
- Stereo: bass/kick/snare/lead centre, low end mono (`width` with monobass ~120 Hz on master or bass bus),
  pads/arps/chorus wide. Correlation 0.2–0.6 (see Size and space).
- Reverb: big but not washing out the groove — high-pass the reverb returns (~200–300 Hz), pre-delay 20–40 ms.
- Master: `master/synthwave` (glue 2:1, tape, gentle exciter, width with mono lows, limiter ceiling −1.2 dB);
  optional glue for the synths on `bus/music`.

## Size and space: sound expensive, never "Gameboy"

The first songs made here were judged by a listener as "pale, thin, 8-bit, like a Gameboy". Measured cause:
stereo width 11–27 %, hall return 14–20 LU under the mix, plate/echo inaudible, pads 5–10 dB under the lead.
Synthwave is a *wall* of chorused, reverberant synths around a punchy centre. Targets (`report.json` → `space`,
per full section in `space.sections`; look at `stereo.png`):

| measure (`space` key) | target (full sections) | too little sounds | too much sounds |
|---|---|---|---|
| mix stereo width (`widthPct`) | 30–55 % | mono, cheap, chiptune | hollow, phasey |
| correlation (`correlation`) | 0.2–0.6 | narrow | < 0: collapses in mono |
| width above 150 Hz (`widthAbove150HzPct`, the one the report judges) | 40–100 % (lush: 60–80) | narrow | over-wide |
| reverb returns (hall, plate, shimmer) vs mix (`wetnessLu`) | 8–14 LU below | dry, 8-bit | washy, groove lost |
| pad/bed vs lead (`bedVsLeadDb`) | 0 to −5 dB | thin, lead + drums only | lead buried |
| echo while it sounds (`returns[].activeLu`) | about −16..−22 LU (heard in the gaps; below −24 it is lost) | static | cluttered |

The whole-mix width counts the mono kick and bass, so it depends on the arrangement: a full chorus (lead, two bed
layers, keys, arp, bells) reads 35–40 %, a lean one (lead + one pad + keys + arp) ~30 %, a verse of just pad + keys +
arp over drums and bass ~25 % (give it a wide counter-line or a second bed layer and let the kick/bass hold back,
as `songs/_demo_lush` does: 36 %); intros and breakdowns without drums read 70–90 % with correlation ~0.05–0.1 (not
judged, fine: the correlation only has to stay above 0). The image above 150 Hz is what sounds wide or narrow: keep
it at 60–80 % in every full section.

**The lush setup** (library defaults: use it as is; `songs/_template` starts with it):

```python
s.hall(), s.plate(), s.echo()                         # bus/hall, bus/plate, bus/echo: calibrated returns
shimmer = s.bus('shimmer', 'bus/shimmer')             # octave halo: pad sends -8 in intros/breaks, -20 elsewhere
kit = s.track('drums', 'synthwave/drums_outrun')      # (the kits send -6 dB to 'gated')
s.gated(key=kit, pitches=['snare', 'clap'])           # the 80s gated snare, keyed; gain_db 0..+3
s.master.use('master/synthwave')                      # or master/dreamwave (softer, more tape), master/darksynth (harder)
```

Every library patch carries its own width (chorus / dimension / microshift inserts) and the recommended sends:
beds hall −8 (dream_pad −6), leads hall −10..−12 + echo −12, keys plate −12, arps echo −10 + hall −14, bells
hall −10 + echo −14, kits gated −6. The returns are calibrated so that with these sends a full mix lands at hall +
plate ~11 LU and the echo ~19 LU under the mix. Proof: `songs/_demo_lush` (32 bars, library patches and their
default sends only): full sections width 36 / 35 / 39 %, correlation 0.48 / 0.48 / 0.44, reverb −11.3..−11.4 LU,
echo −18.4..−20.9 LU, bed −0.3 dB, 0 clicks, 0 warnings. The faders are still yours: lead +2 dB over a two-layer
bed (the second layer −3 dB), e-piano and arp panned −0.3 / +0.3, the bass pumped harder than the bed (sidechain
depth 8–10 vs 4–6).

| role | patches (dry width) | how they sit |
|---|---|---|
| bed | `synthwave/warm_pad` (60 %), `juno_pad` (66), `dream_pad` (82), `sweep_pad` (73), `choir_pad` (77), `jupiter_strings` (73), `dx_strings` (69), `gm/strings` (52), `gm/warm_pad` (68), `gm/synth_strings` (48); darksynth: `dark_pad` (62) | Juno chorus II + `dimension` inside; spread voicings C3–C5 |
| keys | `synthwave/epiano` (66), `epiano_bright` (68), `dx_bells` (71), `poly_stab` (58), `dx_brass` (53), `brass_stab` (47), `organ` (37), `gm/grand_piano` (31) | pan against the arp; plate −12 |
| arps | `synthwave/arp_pluck` (74), `arp_glass` (58), `seq_pulse` (43), `marimba` (30), `stranger_arp` (21 + its ping-pong) | echo −10; the dimension keeps the mono sum clean |
| leads | `synthwave/supersaw_lead` (35), `brass_lead` (42), `sync_lead` (38), `dx_lead` (33), `soft_lead` (31), `pulse_lead` (24), `solo_lead` (21) | a `microshift` halo around a solid centre |
| low end | every bass, the kits' kick and snare | mono, centred; the kits spread only claps, cymbals and toms |

| return / master | use it for |
|---|---|
| `bus/hall` (`s.hall()`) | the default big hall: 3.4 s, 30 ms pre-delay, 250 Hz high-pass, natural width (correlation ~0), modulated |
| `bus/hall_lush` | 4.8 s, deeper modulation + chorus on the tail: dreamwave, ballads, intros/breaks (`s.bus('hall', 'bus/hall_lush')`) |
| `bus/plate` (`s.plate()`) | bright 2.0 s plate: e-piano, keys, stabs, snare |
| `bus/plate_80s` | brighter EMT with an Abbey-Road-filtered send (500 Hz–10 kHz): 80s ballad snare, claps, bells |
| `bus/echo` (`s.echo()`) | dotted-1/8 ping-pong (first bounce left), wide, filtered repeats; keep its `width` at 1.0 (1.2 goes out of phase) |
| `bus/tape_echo` | Space-Echo tape ping-pong (first bounce right): wow/flutter, saturation, ducked; dreamwave / lo-fi throws |
| `bus/echo_quarter` | quarter-note stereo echo for pads, keys and slow leads |
| `bus/shimmer` | octave-up shimmer halo for intros, breaks, outros (automate `send.shimmer`; the report judges a reverb return in its loudest section) |
| `bus/wide` | microshift + dimension double: widens a centred part (send −8) |
| `bus/gated` (`s.gated(key=kit, pitches=...)`) | the gated snare/clap burst |
| `master/synthwave`, `master/dreamwave`, `master/darksynth` | glue + tape + exciter + width (mono below 120–150 Hz) + limiter |

Production moves that create size (use several at once):

- **Every sustained synth gets width**: the library pads, strings, keys and arps already carry Juno chorus II
  (mix 0.45–0.65) plus a `dimension` side layer (mode 1; mode 2 on arps and mono sources): mono-compatible, the
  centre stays. Custom sounds: `fx.chorus(mode='II', mix=0.6), fx.dimension(mode=1)`. Keep every part's
  correlation above 0 (a fully wet chorus plus a width boost goes out of phase; the report flags `over_wide`).
- **Leads**: `fx.microshift(style='smooth', detune=9, mix=0.35)` (built into the lead patches) or a send to
  `bus/wide`; the dotted-1/8 echo and the hall do the rest.
- **Wide beds**: pads/strings in open/spread voicings across C3–C5, layered (analog pad + DX strings or GM
  strings), a second bed layer at −3 dB. Beds sit loud enough to be felt (0–5 dB under the lead).
- **Sends everywhere**: the patch defaults above; raise them 2–4 dB for ballads, sparse arrangements and dreamwave
  (the dreamwave profile wants −11..−5 LU: use `bus/hall_lush` as the hall and send the beds at −6).
- **Space in the breaks**: when the drums drop, let the reverb bloom (automate `send.shimmer` / `send.hall` up
  3–12 dB, as `songs/_demo_lush` does with the shimmer); end phrases on a delay throw (`send.echo` to −4 on the
  last note).
- **Stereo delays**: `bus/echo` / `bus/tape_echo` ping-pongs on leads, arps and bells; the repeats are filtered
  (250 Hz–5.5 kHz) so they sit behind the parts.
- **Warmth and sheen**: the master chains carry the tape and a gentle exciter; `bus/music` glues the synths; the
  analog drift of the VA synths and the saturation on bass and drums do the rest. Brighten with the exciter
  (`but_fx('exciter', amount=0.5)`) rather than EQ boosts on every part.
- **Keep the centre punchy and mono**: kick, bass, snare body and the lead centre; everything else is the wide
  wall around them (the master chains keep everything below 120 Hz mono).

## Band presets: start from a finished, reference-calibrated sound

One call sets up the whole ensemble - sampled drum machines and the lush synth patches, every mix chain, pans,
faders, the return buses (224XL IR halls and plates when installed), the keyed gated snare, the kick pump and the
master chain - calibrated against a real record of the sub-style (`python -m agentsound bands synthwave`):

```python
from agentsound import bands
ANALYSIS = {'profile': 'synthwave'}            # = b.analysis: the profile the preset is tuned for
b = bands.outrun(s)                             # or bands.make('outrun', s, without=('arp',), sounds={'lead': ...})
b.bass.loop(prog.bass('octave', rate='1/8', gate=0.85), verse, chorus)
b.lead.play(hook.clip(octave=4), chorus)
print(b.describe())                             # roles, buses and how to play each role (registers, velocities)
b.arp.automate('gainDb', ramp(intro.start, verse.start, -12, 0))   # dB on the track's gain_db (the preset's level)

```

| preset | roles | sound | tuned against (loudness-matched `compare`) |
|---|---|---|---|
| `outrun` | drums bass pad keys arp lead | LinnDrum + TR-909 kick (+ Simmons toms), keyed gated snare, octave bass with sub, warm pad, DX e-piano, pluck arp, supersaw (`lead='solo'` / `'piano'`) | Kavinsky "Nightcall": all regions within +-2 dB, crest 10.9 / 11.0 dB |
| `dreamwave` | drums bass pad strings keys lead | soft LinnDrum half-time, moog bass (widened harmonics, mono sub), dream pad + Juno strings, DX e-piano, chorused soft lead (`lead='piano'`), dark 224XL hall, tape echo, shimmer | Timecop1983 "Deckard's Dream": within +-2.4 dB, width 73 % (ref 158, phasey), kick punch 7 / 12 dB |
| `darksynth` | drums bass pad arp stab lead | distorted TR-909, growl bass, dark pad, 16th sequence, distorted brass stabs, sync lead (`lead='piano'`) | Perturbator "Future Club": within +-2 dB above 35 Hz, width 36 / 27 %, crest 9.7 / 10.0 dB |
| `retrowave` | drums bass pad keys brass choir lead | 80s pop kit + Linn clap (gated), octave bass, Juno pad, bright DX e-piano, brass stabs, Fairlight choir (`choir='vocoder', voice=<track>`: robot choir), brass lead (`lead='supersaw'` / `'sax'` / `'piano'`) | The Midnight "Sunset": within +-2.3 dB, width 64 / 65 % |
| `scifi` | drums bass arp seq pad bells lead | Stranger-Things arp + sequence, drifting sweep pad, moog bass, DX bells, sparse TR-808, soft lead (`lead='piano'`), dark hall + shimmer | Timecop1983 (the closest reference): within +-2.9 dB 60 Hz-12 kHz, width 71 % |

Demos (16-24 bars, only the preset + composition): `songs/_bands/<preset>/song.py`, each 0 warnings and 0 clicks
under its profile. What the calibration taught (it is what "thin, 8-bit, Gameboy" meant, measured):

- **The records are dark and dense, the drafts were bright and spiky.** Loudness-matched, the first dreamwave draft
  was +5..12 dB too bright above 350 Hz and -8.5..-11.5 dB short in the sub; the kick stuck out 26 dB over its
  surroundings (reference 12). The fixes that closed it: a master high shelf -2..-3 dB from 3 kHz with a 13 kHz
  low-pass (dreamwave / scifi), a sub oscillator + low shelf on the bass, hats 8-15 dB under the kit, the kit's low
  shelf -3..-7 dB at 70 Hz, and above all a **sustained bass**: tied / legato roots (dreamwave) or 8ths at gate
  0.85 (outrun) instead of the default staccato gate - the gaps before each kick were what made it spiky.
- **Width lives in the low mids.** Timecop1983 is 148-195 % side/mid at 250-500 Hz (correlation 0.25, below 0 per
  octave from 250 Hz to 1 kHz: phasey); the presets use a master width 1.4-1.5 with the pads slightly narrowed
  (0.75-0.8), a chorus on the lead and a `dimension` on the bass above 150 Hz, and narrow the (decorrelated, ~105 %
  wide) IR hall return to 0.65-0.8 so pad-only intros and outros keep a correlation >= 0 (mono-safe) - they stop at
  65-75 % width instead of the reference's 158 %. Nightcall is the opposite (10 %, nearly mono): the
  outrun preset stays just above the synthwave profile's 40 % floor.
- **Retrowave is bright** (tilt -3.5 dB/oct): a +5.5 dB shelf from 6 kHz and a stronger exciter on the master, -4.5
  dB at 380 Hz; the pads and lead get presence, not the drums.
- **Darksynth is loud and flat**: the reference plays at -5 LUFS with crest 10 dB; the preset reaches the crest at
  -9 LUFS (profile range) with a hot tape and 11 dB of limiter drive - and a 16 Hz DC blocker before the limiter
  (the distorted bass through hot tape left a DC offset).
- **The 224XL IR plates return ~8 dB under `bus/plate`** (measured; the lush pass raised `bus/plate` +7 dB): the
  presets give the IR plate bus +7 dB. The halls, chambers and rooms match `bus/hall` within about +-1 dB.
- What the presets do not chase: the punch of snare and hats stays 2-5 dB under the references (the lush returns fill
  the gaps between hits), and loudness stays inside the analysis profile even where a record is hotter.

Every role takes `sounds={role: patch}` (keeps its chain), `without=(...)`, `ids={...}`; missing sample packs fall back
to the synthesized kits and pads (`b.info['fallbacks']`, the notes name the `samples fetch` command).
