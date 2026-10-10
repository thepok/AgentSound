# Expensive Habits - sound (roles/sound-designer.md)

| part | sound | why / what was changed |
|---|---|---|
| drums | `bands.retrowave` kit: SampleRadar 80s pop Kit A + the LinnDrum clap, crash, ride, tambourine mapped in; the keyed gated snare bus | the LinnDrum-era machine kit; Kit A has no cymbals (the drummer's crashes fell on the open hat). Ending `hit` (no choked crash in the kit) |
| bass | the preset's octave saw bass (va, mono), `osc.retrig` off, -2.5 dB at 220 Hz, ducker depth 9 under the kick | the sequenced octave bass; retriggered saws clicked at note changes (11 masked clicks with a slower attack, 2 free-running); out of TIGER's low register |
| pad | Juno pad, -2.5 dB at 1.1 kHz, width 1.25 | the bed under the words |
| strings | `synthwave/jupiter_strings`, hp 180 Hz, -3 dB at 420 Hz, width 1.25, pan -0.35, hall -3.5 | the string machine: left, in the hall |
| choir | the Fairlight choir, width 1.3, pan +0.35, hall -3.5 | the chorus "aah" bed, right |
| keys | bright DX e-piano, `velsens` 0.85, pan +0.45, hall -7 | offbeat stabs with real accents |
| brass | `synthwave/brass_stab`, `amp.velocity` 1.0, pan -0.4 | doubles the riff an octave down; played dynamics 1.4 -> 7.1 dB per phrase |
| riff | `layered/piano_glass_lead` (sampled melody piano + DX glass + pad), its compressor opened (-10 dB, 2:1), dimension 1.15 | the instrumental hook: bright with body, no beep; accents survive (6.7 dB per phrase) |
| marimba | `synthwave/marimba` (DX), pan +0.5, echo -14 | the 16th bell sequence |
| orch | `gm/orchestra_hit` (GeneralUser GS), hall -8 | the Fairlight-era stab; dynamics written (ff / mf / p, the lift pp -> ff) |
| vocal | TIGER through `hero(family='vocal', genre='pop')`: clean (no tube), de-esser 5.5 kHz, its own short plate -21 dB, no constant echo, section-end throws at -15 dB (not -10), ride +0.5 dB in the hooks | cool and DRY: returns 15.8 LU under the dry voice (`wetness.py`), 250 ms after a phrase end -21.9 dB |
| ahs | Hanami through the vocal hero chain without duck / ride / throws, pan -0.55, -10.5 dB | soft "ahs" far under him, choruses 2-4 |
| fx | noise riser, impact, downlifter (`s.transitions`) | into the choruses, the bridge, the key change |

Space: the 224XL hall (width 1.0) + plate from the preset, the echo bus for marimba / riff and the vocal throws.
The kit steps aside up to 3 dB at 3.5 kHz while he sings (`s.carve`), the bed ducks 2 dB and carves 3 kHz (the hero).

The delivery (measured, `python songs/_demo_vocal/wetness.py songs/expensive-habits`): 14 % of the onsets scooped
(median -37 ct), vibrato median 8 ct on held notes, 0 falls / doits, the soft mode 78 % of the time, the power mode
0.6 %, note levels 5.3 dB (10-90 %).

Licences: TIGER CC BY-NC-ND 4.0 + Commons Clause (non-commercial), Hanami (credit Lotte V; vocoder CC BY-NC-SA),
SampleRadar 80s pop drums (no redistribution), hyperreal LinnDrum / Fairlight library / 224XL IRs (unclear),
Salamander grand (CC-BY 3.0, Alexander Holm), GeneralUser GS. Private listening only.

## Round 2 (after the A&R's first pass and the singer-expression merge)

- The singer: `back_phrase` / `ornament` / `messa_di_voce` OFF in both voices (the deadpan: no jazz phrasing); the
  lyric markup ON: `*cheap*` and `*time*` in every chorus (`*running*` in the last), `*dance*` in verse 2, and the
  bridge's last line as an intimate aside `(( the phone switched off and the radio low ))`. The library's mic pull-back
  on long held notes was on in the verse voice here (-4.3..-5.7 dB) and switched off after A&R round 2.
- Delivery after it: 15 % scooped onsets (median -44 ct), vibrato median 8 ct, soft mode 75 %, power mode 1.5 %,
  0 falls / doits; returns 15.8 LU under the dry voice, 250 ms after a phrase end -20.9 dB.
- Hats -14 -> -12 dB in the kit (air was -2.3 dB vs the profile).
- After A&R round 2: `mic_pull=False` on the lead (line ends stay at line level), the riff's last chord on the pedal.
