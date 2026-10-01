# Ghosts of Ocean Drive - sound

Base: `bands.retrowave(s, without=('lead',))` (80s pop kit + TR-909 kick, Linn clap, keyed gated snare, octave bass,
Juno pad, bright DX e-piano, brass stabs, Fairlight choir, 224XL concert hall + CD plate, dotted-8th echo,
master/synthwave with the retrowave eq / exciter / width). Own additions below.

## Parts

| role | sound | range | chain + sends | why | checks (final build) |
|---|---|---|---|---|---|
| hook (lead) | `hero(s.track('lead', 'hero/synth_piano'), genre='synthwave', bed=[pad, choir, strings], competitors=[keys, arp, brass, glass])` = hero piano_synth: Salamander melody piano + poly hero saw -6 dB (velcurve 1.6, pedal=False) | E2-G#6 (hook B4-F#6 over octaves / 6ths / 3rds; breakdown LH tenths) | tone (-1.5 dB 3.3 kHz, +1.5 dB 9.5 kHz) -> tape 15 ips -> microshift 7 ct -> air; plate -12, hall -14, echo -12 -> -4 throws (14 phrase ends); bed duck 2.5 dB + carve -2 dB @ 1.8 kHz; competitors -2 dB @ 1.8 kHz; ride +1 dB in chorus1-3 | "no beepy synth lead" / "lieber eine hohe Piano-Taste": a real piano attack with a singing saw under long notes (The Midnight / FM-84 hybrid), played in octaves by the pianist | -17.6 LUFS, note dynamics 7.5 dB per phrase (vel 31-121), bed 4.0-5.9 dB under it in every lead section (chorus1 -5.5, chorus2 -4.7, chorus3 -4.3) |
| solo / outro farewell | `hero(s.track('sax', 'hero/sax'), family='sax', genre='synthwave', ...)`: Weresax alto + 2 MTG takes -10 dB (+9 / -8 ct, 17 / 26 ms, panned) + muted tenor octave | D4-F#5 | hero sax chain (honk out, 3:1 comp, tube, bite 3 kHz, air 8 kHz, exciter, air stage + mic eq from the hornist); hero_plate -14, hall -16, echo -24 -> -5 throws | the solo needs "epic / present" (lamplight-avenue lesson) and breathing held notes | -17.8 LUFS, 3.9 dB note dynamics (automated air), hornist: 7 pushes, 5 swells, 3 blooms, 6 vibratos, 2 lean-ins, 1 shake (climax) |
| drums | preset pop80 kit (keyed gated snare), hats played x0.7 | - | preset kit chain; gated -8, plate -15; MIX +2 dB, -1.5 dB @ 3.3 kHz | 80s machine kit | hats still ~5-7 dB "punchier" than the references (see weaknesses) |
| bass | preset octave bass (sub 0.25) | B0-B2 | preset chain + ducker keyed by the kick: depth 9 dB, threshold -48 (preset 5 / -30) | the kick through the bass wall; verse 1 interlocks with the sparse half-time kick | masking only info (ducking 3.7 dB in verse1) |
| pad | preset Juno pad | C3-C5 spread | preset chain, hall -6, shimmer -20 (automated -6..-8 in intro / breakdown / outro); MIX -2 dB @ 450 Hz, -1.5 dB @ 1.4 kHz | the wide bed | bed within 3-6 dB of the lead |
| strings | `sampled/strings` | A3-E5 | -2.5 dB @ 480 Hz, hall -8, kick pump 6 dB | the cinematic lift (pre swells, chorus 2/3, breakdown, solo) | - |
| choir | preset Fairlight choir | C#3-C#5 | preset | chorus 2 (2nd half), breakdown, chorus 3 | - |
| keys | preset bright DX e-piano, velsens 0.5 -> 0.85 | C4-C5 drop2 | preset + MIX -2 dB @ 1.4 kHz (room for the verse tune) | the 80s comp | 4.0 dB note dynamics (was flat: 0.0) |
| brass | preset brass stabs, amp.velocity 0.5 -> 0.75 | C4-C5 | preset | off-beat stabs in chorus 2/3, pre 2 hits | 5.2 dB note dynamics (was flat: 2.2) |
| arp | `synthwave/arp_pluck` | B3-C#5 16ths | echo -10, hall -14, kick pump | drive from verse 2 on | - |
| glass | `synthwave/arp_glass` + lp filter `gf` (opens in the intro) | D4-F#5 8ths | echo -12, hall -10, shimmer -18 | sparkle in intro / breakdown / chorus 2-3 / outro | - |
| fx | `synthwave/noise_riser`, `impact`, `downlifter` | - | own reverbs | transitions | - |

## Choosing the hook sound (measured, chorus2, scratch renders with GOD_LEAD=...)

Each candidate through the same `hero()` call, chorus2 rendered alone and compared with The Midnight "Sunset" 4:00-4:30
(loudness-matched):

| candidate | lead LUFS | bed vs lead | lead note dynamics | report warnings | presence vs Sunset |
|---|---|---|---|---|---|
| `hero/synth_piano` (piano_synth) | -16.2 | -3.7 dB | 8.9 dB | none (besides the section-render's silent_section) | -4.0 dB |
| `hero/synth_lead` (synth) | -17.1 | -2.1 dB | 9.3 dB | balance_mid_high | -3.0 dB |
| `hero/piano_pop` (piano) | -15.5 | -4.6 dB | 10.5 dB | balance_mid_high | -4.1 dB |
| `layered/piano_glass_lead` (via hero piano) | -12.3 | -7.2 dB | 3.1 dB | loudness_high, thin_bed, lowmid/mid/presence high | -1.0 dB |

piano_synth: the only one with the bed >= 3 dB under the hook and no balance warning, with strong dynamics; the synth
lead sits too close to the bed, the pure piano pushes the mids, the glass stack came out 4 LU hot and flat through the
piano hero chain. `GOD_LEAD` stays in song.py only for such A/B renders (default = piano_synth).

## Rooms

224XL concert hall (-10.7 LU under the mix), CD plate, dotted-8th echo (-17 LU), shimmer (breakdown / intro / outro
blooms), hero_plate (sax). Width above 150 Hz 50-59 % in the full sections (74 % intro), correlation 0.6.

## For the mixer

The hook is the lead in every section but the solo (sax). The bed is meant to sit 4-6 dB under it; the verse tune
is soft by design (ridden +1.5 dB in the MIX). The master limiter drive is automated per section (the energy arc).

## Revision (A&R issues 2, 3, 5)

The rows above describe the first pass. These changes are on top of them.

**Hook (lead)**
- Change: `hero(..., tone={'peak3.gain': 0, 'high.freq': 5000, 'high.gain': 3})`. The -1.5 dB at 3.3 kHz is gone,
  replaced by a +3 dB air shelf.
- Change: the saw layer cutoff goes from 1.5 to 2 kHz, and the saw plays only from A4 up (fade over 5 semitones),
  so the doubles stay piano.
- Change: a new layer `glass` = `synthwave/arp_glass`, an octave up at -13 dB, from E5 up (the piano_glass_lead
  sparkle).
- Change: the pianist's doubles under the top note play at 75 %.
- Why: the "hohe Piano-Taste" had no top. The shelves alone changed the mix by less than 0.1 dB.
- Check: in the lead stem (chorus 2), 2.5-6 kHz goes 0.9 -> 2.7 % and the centroid 972 -> 1087 Hz. Note dynamics go
  7.1 -> 8.2 dB, and loud hits show no glassy smear (spectrogram_11).

**Drums (kit A)**
- Change: the compressor attack goes 10 -> 28 ms (3:1, release 120) and the tape drive 5 -> 3.5.
- Change: a new -3 dB bell at 160 Hz.
- Change: hats and crashes are split off (below).
- Why: the soft, boomy kick.
- Check: see the kick layer.

**Kick (new track)**
- Sound: `sampled/linndrum` kick under kit A's kick, -3 dB, low-pass 3 kHz.
- Why: the thump. Kit A's kick is soft and long.
- Check: chorus 3 kick punch goes 13.6 -> 18.7 dB (Sunset 18.9).

**Hats (new track)**
- Sound: kit A's hats on their own track, through the kit chain.
- Change: velocities back to the drummer's (was x0.7).
- Change: +2 dB.
- Change: -1.5 dB at 4.2 kHz, a -3 dB shelf from 9 kHz, low-pass at 14 kHz.
- Why: they were -54 LUFS, 35 dB under the kit, so the "hats" punch was the snare / clap crack. They are now a soft
  sheen.
- Tried and dropped: +6 dB made the air +2.6 dB over Sunset.

**Cymbals (new track)**
- Sound: `sampled/80s_gated_kit` crashes (49), high-passed at 350 Hz, hall -18.
- Why: kit A has no cymbals, so the drummer's 18 section crashes were silent. The drummer's kit now has a crash key.

**Bass**
- Change: a new -3 dB bell at 150 Hz.
- Why: 89-354 Hz read +2.8 dB over Sunset.
- Check: 111-224 Hz is now +2.2 dB, and the 7-band bass reads -0.4.

**Pad**
- Change: `width` 1.2 (monobass 150), from verse 1 on.
- Change: the preset's +2 dB presence goes to 0.
- Why: width in the low mids; the hook owns the presence band.
- Check: the intro's low-end correlation is 0.85.

**Strings**
- Change: `width` 1.35.
- Why: width in the low mids.

**Keys / arp**
- Change: pans -0.45 / +0.45 (were -0.3 / +0.3).
- Why: width.

**Sax**
- Change: the hero_plate send goes -14 -> -11.
- Change: the bed duck is 4 dB and the carve 4.5 dB (was the profile's 2.5 / 3).
- Why: an "epic / present", wider solo.
- Check: stems, bars 93-100: the sax sits +2.4 dB over the band (was -2.9), and the bed 6.3 dB under it.

**Result**
- Width above 150 Hz: 52 -> 58 % (full sections 55-64 %).
- Chorus 3 vs Sunset: 58 % vs 59 %.
