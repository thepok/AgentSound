# Catch Fire - sound design

| role | sound | range played | chain + sends | why | checks (final build) |
|---|---|---|---|---|---|
| vocal (lead) | TIGER (DiffSinger, `singer.sing`, style `rock`, pitch `hybrid`), chorus parts `base_power=1.0, power=0.6` (TIGER's Electric mode on the drops), bridge `soft=0.6, base_soft=0.3` | C3-A4 | `hero(family='vocal', genre='rock', deess 5.5 kHz)`: hp 90, -2 dB 280 Hz, 3:1 8 ms, tube 3 dB, +2 dB 3.5 kHz, air shelf, de-esser after the boosts; + an eq 'words' +1.5 dB at 3 kHz; dry space: `vocal_plate` -20 dB, no constant echo, throws on 9 section ends | the hook carrier ("no beepy synth hooks"); dry and close ("der Gesang hat immer viel Hall") | -14.7 LUFS (the loudest part), note dynamics 21.7 dB (audio onsets), diction clean (shortest coda 46 ms; no coda_short / coda_buried) |
| vocal_dbl_l / _r, vocal_harm | the chorus (and the build's pre) SUNG again: `singer.double` takes 100+ / 110+ (two performances, not a copy), `singer.harmony(steps=-2)` a third below, takes 120+ | D4-A4 / B3-F4 | same vocal chain, no rides / throws / carve; pan -0.85 / +0.85 / 0; -7 / -7 / -8 dB | width and weight on the hook without phasing | -24 LUFS each, 7 % wide each side |
| gang (chant + "hey!") | TIGER x3 takes (centre +1.5 dB, L / R -1.5 dB at +-0.85), a TIGER harmony a third below (-6 dB), Hanami +12 (`gang_dbl_hi`, -11 dB) | G3-D4 (Hanami G4-D5) | vocal chain; the centre one gets the echo throws (its "hey!" tails) | the Imagine-Dragons group shout, original chant | gang -14.9 LUFS where it sings |
| drums | rock_band Big Rusty kit (close + OH), punch compressor, drum bus crush + tape, crushed drum room (send raised -5 -> -2 dB: the arena) | - | preset + MIX eq -3 dB at 45 Hz (the sub owns the bottom on the drops) | the live kit under the stomp | peaks +3 dBFS pre-master (info: the master limiter takes them) |
| taiko | MuseScore General "Taiko Drum" (GM 116), G1 = huge, C3 = medium | G1 / C3 | eq hp 75 Hz, -3 dB 300 Hz; drum_room -4; levels: verses -5, pres -3, choruses +3 | the stomp: the idiom's floor hits | no sub-band masking warning left |
| claps | Hydrogen Gimme-a-Hand claps (5 layers) | key 39 | plate -14, drum_room -10 | the clap on the half-time 3 | |
| sub | `synthwave/sub_bass` (sine + a little triangle) on the chord root F1-E2 with the kick, choruses only | F1-E2 | MIX: ducked 10 dB under the kick (1 ms / 40 ms hold / 160 ms) | the drop's weight; kick first, then the sub blooms | masking drums/sub now info: they alternate (3.7-4.7 dB) |
| bass | rock_band picked Growlybass -> SVT-style rig (tube amp + DI) | E1-D3 | preset (ducks 5 dB under the kick) | | |
| gtr_l / gtr_r | rock_band, `gain='crunch'`: FSBS Strat DI -> Plexi -> Marshall 4x12 (L), Emily SG DI -> crunch -> 2x12 V30 (R); `guitarist.riff` + `guitarist.double` | power chords D2-D4 | preset + room -9 dB; MIX -3.5 dB at 400 Hz; in the vocal's carve bed (up to -5 dB at 3 kHz while the voice sings) | the wall; 'crunch' instead of 'high' (less fizz, a little more dynamics) | flat_dynamics INFO (1.9-2.1 dB per phrase): see AR.md / TODO |
| keys | rock_band piano (Salamander) | A3-D6 | preset, MIX -2 dB at 350 Hz, hero dip -2 dB at 3 kHz, echo only in the bridge (-12) | pulse in verse2 / pres, sparkle in the choruses, the bridge's arpeggio | |
| choir | `sampled/choir_oh` (NBO "oh") | D3-A4 | hall -6, plate -16; carved under the voice; MIX +5 dB, -3 dB at 350 Hz | the "oh" bed of the drops, the bridge's pad | bed -10.4 dB vs lead |
| pulse | `synthwave/seq_pulse`, cutoff lane 300 -> 5000 Hz | D4-D5 | echo -5, carved | the electronic edge, filtered | |
| riser / reverse / impact / down | library synthwave transition hits (`s.transitions`) | - | riser -6 dB, ends on the breath | builds, drops, downlifters | |

Rooms: drum_room (Voxengo drum room + crush), room (clean), plate (224XL CD plate), hall (`s.hall()`: choir, the end's
last chord), vocal_plate (the vocal hero's short plate), echo (dotted 8th ping-pong; throws only). Reverb -14.9 LU
under the mix (rock -20..-9), space 'lush', width above 150 Hz 32 % after the master's x1.25.

Grit: off. The user allows `grit='light'` on rock vocals ("kein großer Unterschied, beides ok"), but it raises the
vowels' 2-8 kHz and makes word-final consonants read lower against their vowels (TODO "Vocal grit" (5)); here the
words already compete with a guitar wall, so the clean chain wins.

## Hero log (build)

```
hero 'vocal' (vocal, rock): carve: choir, pulse, gtr_l, gtr_r up to -5 dB at 3000 Hz (Q 0.7) while the hero plays
hero 'vocal' (vocal, rock): dips: keys, claps -2 dB at 3000 Hz (Q 0.9, eq 'hero_dip')
hero 'vocal' (vocal, rock): ride: +1 dB in chorus1, chorus2, chorus3
hero 'vocal' (vocal, rock): throws: 9 section ends, send.echo -60 -> -10 dB
hero 'vocal' (vocal, rock): space: plate -> 'vocal_plate' at -20 dB; no constant echo
```
