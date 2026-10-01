# Third-party components and assets

AgentSound's own code, docs, recipes, role briefs and songs are MIT licensed (see [LICENSE](LICENSE)). This file
lists everything in the repository that comes from elsewhere or carries its own licence, and the things AgentSound
uses but does not ship.

## Bundled in this repository

| component | where | licence | notes |
|---|---|---|---|
| nlohmann/json 3.12.0 | `third_party/nlohmann/json.hpp` | MIT | Copyright (c) 2013-2025 Niels Lohmann; licence text in `third_party/nlohmann/LICENSE.MIT` |
| MSFA DX7 DSP subset (Music Synthesizer for Android, via Dexed v0.9.4) | `third_party/msfa/` | Apache-2.0 | Copyright 2012 Google Inc., 2016-2017 Pascal Gauthier and contributors. Only the Apache-2.0 DSP core - no Dexed app / JUCE / GPL code. Locally modified files carry a modification notice; per-file provenance and changes in `third_party/msfa/PROVENANCE.json` and `README.md`, licence text in `third_party/msfa/LICENSE-APACHE-2.0.txt` |
| GeneralUser GS v2.0.3 SoundFont | `assets/soundfonts/GeneralUser-GS.sf2` | GeneralUser GS License v2.0 | by S. Christian Collins (schristiancollins.com); free use for music creation, private or commercial, and in software projects. Full text in `assets/soundfonts/GeneralUser-GS-LICENSE.txt` |
| "AgentSound Geo" stroke font | `engine/art/StrokeFont.h` / `.cpp` | CC0 (public domain dedication) | drawn for this project (cover-art titles) |
| Vocoder speech one-shots | `songs/*/samples/speech/*.wav` | see note | short words generated with the built-in Windows text-to-speech voices (Microsoft Zira via SAPI, Microsoft Stefan via OneCore) by `agentsound.speech`; cached so a song re-renders identically without Windows. Regenerate them with `python -m agentsound speak` on Windows if you prefer |

No other third-party source is vendored: the PNG writer, WAV I/O, SoundFont / SFZ readers, analysis and all DSP
(apart from the MSFA core above) are AgentSound's own code. Textbook algorithms (e.g. the RBJ audio-EQ-cookbook
biquad formulas, EBU R128 loudness) are implemented from their published descriptions.

## Not bundled - install or download yourself

| what | where it goes | licence | notes |
|---|---|---|---|
| Yamaha DX7 factory ROM cartridges (8 banks, 256 voices) | `assets/dx7/*.syx` | Yamaha's; not redistributed here | see [assets/dx7/README.md](assets/dx7/README.md). Without them the `dx7` instrument and DX7-based patches are unavailable; everything else works |
| Sample packs (pianos, orchestra, drums, guitars, IRs, ...) | `assets/samples/<id>/` | per pack: CC0, CC-BY / CC-BY-SA, CC-BY-NC, GPL with sample exceptions, royalty-free / freeware **without redistribution**, some unclear | only the list is versioned (`assets/samples/manifest.json`: url, licence, attribution, genres). `python -m agentsound samples fetch ID` downloads one from its original source and writes `SOURCE.json` with the licence and attribution. Every build writes `songs/<slug>/out/credits.txt` with the packs a song used and warnings for NC / no-redistribution / unclear licences; CC-BY packs need the printed attribution when you publish a song |
| Reference tracks for `compare` | `references/`, `assets/refrences/` (gitignored) | commercial / yours | never committed |
| Breeze TTS 2 (making-of narration, optional) | a local WSL installation (`$AGENTSOUND_BREEZE_DIR`, default `~/services/breeze-tts`) | research / non-commercial | only used by `python -m agentsound makingof --tts breeze`; making-of films narrated with it are for private / non-commercial use. `--tts sapi` (Windows voices) or `--tts none` avoid it |
| ffmpeg, Node.js, Chrome / Edge | system tools | their own | called as external programs (mp3 encoding, reference decoding, making-of video); not bundled |

## Music in `songs/`

The songs are original compositions made with AgentSound, except the piano études that render public-domain scores
(`gymnopedie-etude`: Satie, Gymnopédie No. 1, 1888; `nocturne-etude`: Chopin, Nocturne op. 9 no. 2, 1832). Their
notes are written as data in the song folder from the score, not copied from a modern edition's typesetting or a
MIDI file. Reference recordings were used for analysis only and are not part of the repository.
