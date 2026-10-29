# Endless Piano / Orchester - licences

Everything in this folder is redistributed under the terms below. The page is non-commercial (no ads, no fees, no
sales).

## AgentSound (code)

`engine/agentsound.js`, `engine/agentsound.wasm` (the AgentSound engine compiled to WebAssembly),
`py/repo.zip` (the AgentSound Python composer and the sample-mapping text files it reads), `app.js`,
`compose-worker.js`, `engine-worker.js`, `index.html`, `store.js`, `sw.js`, `manifest.webmanifest`, the icons `icon-192.png` /
`icon-512.png` (drawn by a script for this page), and `bank/` (pieces pre-composed by the same AgentSound
composer: note data and render settings, gzipped JSON; no audio).

AgentSound, https://github.com/thepok/AgentSound, MIT License (the full text is `LICENSE` inside `py/repo.zip`).
The engine bundles nlohmann/json (MIT) and the Music Synthesizer for Android DX7 core (Apache-2.0).

## Splendid Grand Piano (samples)

`samples/beste/*.opus` (every sample, Opus 160 kbps) and `samples/spar/*.opus` (3 of the 5 velocity layers and
every second sampled key, Opus 128 kbps), plus `Splendid Grand Piano.sfz` and `Data/*.txt` inside `py/repo.zip`.

Splendid Grand Piano: AKAI Steinway samples, released into the **public domain** by Akai; fixed and mapped to SFZ by
kinwie (sfzinstruments). https://github.com/sfzinstruments/SplendidGrandPiano. Converted here to Opus; no further
changes.

## The orchestra (samples)

`samples/orch/*.opus` (5179 files), `samples/orch/index.json` and `samples/orch/ATTRIBUTION-vocalset-choir.txt`. Each file is one sample of the packs below, converted
to Opus (96-112 kbps stereo); looped sustains end shortly after their loop, one-shots lose the tail below -66 dB of
their peak (with a 30 ms fade). The file name is a short hash of the original path plus the original file name. The
SFZ mapping text of the same packs is inside `py/repo.zip` (`assets/samples/...`, text only, no audio).

| Pack | Licence | Used for | Attribution |
|---|---|---|---|
| Sonatina Symphonic Orchestra 4.0 (`sso`) | Creative Commons Sampling Plus 1.0 (non-commercial redistribution of the whole work allowed; no advertising use) | violins 1 + 2, violas, cellos, basses (SSO part; with their pizzicato, col legno, harmonics, tremolo), flutes, clarinets, bassoons, horns, trumpets, trombones, tuba; the SFZ mappings | Sonatina Symphonic Orchestra by Mattias Westlund, SFZ v4.0 by Peter Eastman - https://github.com/peastman/sso, https://creativecommons.org/licenses/sampling+/1.0/ |
| Virtual Playing Orchestra 3.2 wave files (`vpo-wav`) + 3.3 standard scripts | VPO terms: free redistribution, credit the creators / link virtualplaying.com, no sale; its parts: | the string sections' sustains (basses, cellos, violas) | Virtual Playing Orchestra by Paul Battersby, http://virtualplaying.com/virtual-playing-orchestra/ |
| - VPO `libs/SSO` (basses) | CC Sampling Plus 1.0 | basses sustain | Mattias Westlund (Sonatina Symphonic Orchestra), loops by Paul Battersby |
| - VPO `libs/NoBudgetOrch/CelloSect` | CC BY-SA 4.0 | cellos sustain | Jeff Glatt (No Budget Orchestra), loops by Paul Battersby - https://creativecommons.org/licenses/by-sa/4.0/ |
| - VPO `libs/Mattias-Westlund/ViolaSect` | CC BY-SA 4.0 (its readme; Mattias Westlund's samples are CC BY-SA 3.0 elsewhere) | violas sustain | Mattias Westlund (www.mattiaswestlund.net), from the bandshed.net viola samples and FluidGM - https://creativecommons.org/licenses/by-sa/4.0/ |
| - VPO `libs/VSCO2-CE` (violas) | CC0 1.0 | violas | Versilian Studios |
| AgentSound vocalset-choir (`vocalset-choir`; also published as https://github.com/thepok/epic-choir) | CC BY 4.0 (derived from VocalSet) | the SATB choir (wordless vowels ah / oh / oo, p / mf / f layers) | Choir samples derived from VocalSet (Wilkins, Seetharaman, Wahl, Pardo 2018), CC BY 4.0, https://doi.org/10.5281/zenodo.1442513 - Wilkins, J., Prem Seetharaman, Alison Wahl, & Bryan Pardo. (2018). VocalSet: A Singing Voice Dataset (Version 1.2) [Dataset]. Zenodo. No endorsement by the VocalSet authors is implied. |
| Lars Palo: Burea Church organ (`lars-palo-burea-church`) | CC BY-SA 2.5 (Sweden), https://creativecommons.org/licenses/by-sa/2.5/ | the pipe organ (COLOUR), registrations: see the audit below | Burea Church sample set by Lars Palo (familjenpalo.se), CC BY-SA 2.5 - https://familjenpalo.se/vpo/download/ |
| Lars Palo: Piteå School of Music organ (`lars-palo-pitea-mhs`) | CC BY-SA 2.5 (Sweden) | the pipe organ (COLOUR), registrations: see the audit below | Piteå School of Music organ sample set by Lars Palo, Graham Goode and Panos Ghekas (familjenpalo.se), CC BY-SA 2.5 |
| FreePats Spanish Classical Guitar 2019-06-18 (`freepats-spanish-classical-guitar`) | CC0 1.0 | the classical guitar (COLOUR) | FreePats project, https://freepats.zenvoid.org/Guitar/acoustic-guitar.html |
| Versilian Community Sample Library 1.2.2 (`vcsl`) | CC0 1.0 | harpsichord (Flemish: 8', 4', full), glockenspiel, tubular bells (COLOUR) | Versilian Studios, https://github.com/sgossner/VCSL |
| VSCO 2 Community Edition 1.1.0 (`vsco2-ce`) | CC0 1.0 (public domain dedication) | oboes, harp (incl. glissandi), timpani (incl. rolls), percussion (cymbals), muted horns (`FHornMute.sfz`, also the stopped-horn accents), straight-muted trumpets (`TrumpetStraightMuteSus.sfz`) | Versilian Studios, https://github.com/sgossner/VSCO-2-CE |

ShareAlike: the converted BY-SA samples (`samples/orch/*` from `vpo-wav/libs/NoBudgetOrch` and
`vpo-wav/libs/Mattias-Westlund`; `index.json` names the original path of every file) are offered under the same
licence, CC BY-SA 4.0.

## Voxengo IM Reverbs (room impulse responses)

`samples/ir/French 18th Century Salon.wav` (the piano) and `samples/ir/Musikvereinsaal.wav` (the orchestra),
unaltered, with their licence `samples/ir/license.txt`.

Copyright Aleksey Vaneev (Voxengo), https://www.voxengo.com/impulses/. Royalty-free use for any purpose; the files
are redistributed unaltered, free of charge, with the copyright notice and conditions in `samples/ir/license.txt`.
Aleksey Vaneev retains exclusive ownership of the impulse files and all intellectual property rights in them.

## Pyodide (loaded from the jsDelivr CDN, not part of this folder)

Pyodide 314.0.7, https://pyodide.org, Mozilla Public License 2.0.

## Mapping text and placeholders inside `py/repo.zip`

`assets/samples/*/SOURCE.json` (licence metadata of every pack AgentSound knows), the SFZ mapping text of the packs
above, `assets/samples/salamander-grand/*.sfz` (2 KB of SFZ mapping text the composer's patch table reads: Salamander
Grand Piano V3 by Alexander Holm, CC-BY 3.0, https://sfzinstruments.github.io/pianos/salamander), and EMPTY placeholder
files (0 bytes, names only) for sample files the composer checks or lists. `agentsound_web_tables.json`: numbers the
composer reads from the samples (length, rate, channels; the RMS level of a zone's first 1.5 s), measured from the
original files - no audio.

## Audit (2026-10-25, AgentSound aa736aa: SOLO and COLOUR) - the samples they added

SOLO (the solo players) loads 19 programs more: SSO `Strings - Performance/Violin Solo 2 KS.sfz` (the concertmaster)
and `Cello Solo KS.sfz` (CC Sampling Plus 1.0), and VSCO 2 CE (CC0) `FluteSusVib`, `FluteSusNV`, `FluteStac`,
`OboeSusVib`, `OboeSusNV`, `OboeStac`, `ClarinetSus`, `ClarinetStac`, `BassoonVib`, `BassoonSus`, `BassoonStac`,
`FHornSus`, `FHornStac`, `SViolinVib`, `SViolinSpic`, `SViolinPizz`, `SViolinTrem`, `CelloEnsTrem`.

COLOUR (the guest instruments) loads: the SSO celesta (`Percussion/Celeste.sfz`, CC Sampling Plus 1.0); VCSL (CC0)
`Harpsichord, Flemish - 8'` / `- 4'` / `- Full`, `Glockenspiel`, `Tubular Bells 2` (the glockenspiel and the bells are
VCSL, not the ethan-winer packs); the FreePats Spanish classical guitar (CC0); and the two Lars Palo pipe organs (CC
BY-SA 2.5) - only the 20 registrations the composer draws: Burea - Svallverk Rorflöjt 8 + Salicional 8, the Svallverk
plenum (Salicional 8, Rorflöjt 8, Principal 4, Waldflöjt 2, Scharf III, Skalmeja 8), Brostverk Gedakt 8 + Koppelflöjt
4 and Krumhorn 8 + Gedakt 8, Huvudverk Gedakt 8 + Rorflöjt 4 + Sesquialtera II, Principal 8 + Oktava 4 + Oktava 2 (+
Mixtur V + Trumpet 8), pedal Subbas 16 (+ Gedakt 8 / + Principal 8, Oktava 4, Basun 16); Piteå - Svallverk Fl.Harm. 8
+ Gamba 8 + V.Celeste 8 and its plenum (Borduna 8, Gamba 8, Fl.Oct. 4, Piccolo 2, Mixtur V, Tr.Harm. 8, Clairon 4),
Positiv Gedackt 8 + Koppelflöjt 4 and Cromorne 8 + Gedackt 8, Huvudverk Dbl.Flöjt 8 + Cornet V, Principal 8 + Oktava
4 + Oktava 2 (+ Mixtur IV + Trumpet 8), pedal Subbas 16 (+ Gedakt 8 / + Oktava 8, Oktava 4, Basun 16). The organ
pipes are WavPack originals, decoded losslessly and converted here to Opus (104 kbps) with their loop points kept
(2,392 files, 219 MB; a piece fetches only the pipes its notes play).

ShareAlike: the converted organ samples (`samples/orch/*` from `lars-palo-burea-church` and `lars-palo-pitea-mhs`;
`index.json` names the original path of every file) are offered under the same licence, CC BY-SA 2.5,
https://creativecommons.org/licenses/by-sa/2.5/. Publishable: yes (CC0, CC Sampling Plus, CC BY-SA - the packs above).

## Audit (2026-10-25, AgentSound f0aea4a: the choir) - the samples it added

CHOIR v2 sings on the vocalset-choir pack: the 12 programs `{S,A,T,B}_{ah,oh,oo}.sfz` (the composer's choir events use
only these three vowels; `ee` / `eh` are not used and not published), each with its p / mf / f layers (they crossfade
with the dynamics), 359 files. Licence: CC BY 4.0, a derived work of VocalSet; the pack's own attribution and change
notes are published unaltered as `samples/orch/ATTRIBUTION-vocalset-choir.txt`, and the page's credits line carries
the required attribution. Converted here to Opus (104 kbps) with the tail below -66 dB of the peak cut (a 30 ms
fade) - a further change of the derived samples, offered under the same CC BY 4.0. Publishable: yes.

## Audit (2026-10-24, AgentSound 2204ef6: the playing techniques) - the samples it added

The techniques (pizzicato choir, col legno, harmonics, muted / stopped horns, straight-muted trumpet, harp
glissando, timpani rolls, trills, woodwind chatter, sforzando) load two programs more than before, both VSCO 2
Community Edition (CC0 1.0): `FHornMute.sfz` (17 files, `vsco2-ce/Brass/F Horn/MOHorn_mute_*`) and
`TrumpetStraightMuteSus.sfz` (16 files, `vsco2-ce/Brass/Trumpet/Sum_SHTrumpet_straightM-sus_*`). Everything else
(col legno, harmonics, pizzicato, rolls, harp; the stopped horn is the muted horn, loud) are regions of the SSO / VSCO 2 CE / VPO programs that
were already loaded and published (every region of every loaded program is in the cut). Publishable: yes.

`samples/index.json`: the content hash of every sample file (the page fetches `<file>?h=<hash>`); no audio.

## Audit (2026-10-24): what the orchestra uses and whether it may be published

Every zone of orchestra-symphonic over ~1200 composed pieces (all feels, moods, sizes; 656 files, the set stopped
growing after the first ~100 pieces) comes from the packs in the table above, plus the Voxengo `Musikvereinsaal` IR.
All of them allow free, non-commercial redistribution with credit (CC0, CC BY-SA, CC Sampling Plus, the VPO and
Voxengo terms) - nothing had to be substituted. Not used and not published: the No Budget Orchestra 2 choir (only
with the film orchestra's choir='oh'; its terms are unclear), the SSO chorus, MuseScore General taikos, the bass
trombone (film orchestra only), and every other pack.
