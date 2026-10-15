# Blueprint Boulevard - sound

| role | sound | range | chain + sends | why | checks |
|---|---|---|---|---|---|
| lead | Weresax alto (`sampled/alto_sax`: dynamic mic + breath trace) through `hero(sax, family='sax', genre='pop', double=False, octave=False)` = THE hero sax v2 (2026-10-15) | E4-G5 | hero tone / comp 4:1 / drive / presence / exciter / tube 7 / tape 15 ips / 10 Hz random autopan / air; hero_plate_70s -14, echo -13 (throws -> -5) | the SimCity 3000 sax voice, now with the late-70s record grit (no doublers: nowhere-to-be feedback) | note dynamics 4.0 dB (automated air) |
| keys | `sampled/rhodes_vibrato` in the funk_band keys chain (tube, tremolo) | C3-B4 | room -12, plate -18; ducked / carved by the sax | the late-90s stereo Rhodes | 5.9 dB |
| piano | `sampled/jazz_grand` -4 dB, eq hp 70 / -2.5 dB 220 Hz / +1.5 dB air shelf | C3-C7 | room -10, plate -16 | warm, no 2-5 kHz boost (HUMAN_FEEDBACK) | 7.6 dB, peak -0.4 dBFS pre-master |
| bass | funk_band Growlybass (fingered Jazz bass) | E1-G3 | band chain + MIX cuts | clean 90s studio bass | ducks 5-7 dB under the kick |
| drums | funk_band Orange Tree jazz-funk kit (sticks) | - | drum bus, room -4 | light studio drums | 7.4 dB under the sax (LUFS) |
| vibes | `sampled/vibraphone` + tremolo (motor) + width 0.6 | E5-G6 | room -10, plate -12 | the mallet sparkle (Sim Broadway colour) | 6.3 dB; was 139 % wide before width 0.6 |
| tenor | `sampled/tenor_sax` -5 dB, -3 dB at 380 Hz | A3-E5 | plate -12, room -12 | harmony a third under | 5.9 dB |
| horns | funk_band VPO trumpet + trombone section | F3-E5 | band chain | festive lift (swells / stabs) | -31 LUFS: colour |
| pad | `sampled/soft_poly` -9 dB | G2-C5 | plate -14; ducked / carved | bed in the lifts | far under |
| shaker | `sampled/busk_kit` keys 42 / 46, -12 dB | - | room -12 | 16th lift | -44.5 LUFS |

Rooms: the band's 224XL ambience (room) and plate, the hero plate, the quarter echo - a 90s studio, no big hall.
