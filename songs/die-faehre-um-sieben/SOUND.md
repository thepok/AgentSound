# Die Fähre um sieben - sound design

| track | sound | why |
|---|---|---|
| guitar | `sampled/acoustic_guitar` (Shinyguitar, mic'd, with chucks / fret noises), guitarist hands travis / songwriter / arpeggio / fingerstyle, width 1.9, a 'tone' eq (low shelf 180 Hz, -3.5 then -8 dB from verse 2 when the bass takes the low end), a dimension chorus at 35 %, width 1.7 with mono bass < 150 Hz | the star: real picking and noises, close but not boomy |
| gtr_melody | the same patch, `gtr.lead` style ballad (vibrato, hammer-ons), low shelf -7 dB at 350 Hz, pan +0.4 | the overdubbed second guitar of the intro / break / tag |
| guitar2 | `.take(2)` of the chorus strum, pan +0.75, low shelf -6 dB | the era's double-tracked chorus guitar |
| bass | `sampled/upright_bass`, bassist style ballad, a 4-bar velocity arc | soft, woody, from verse 2 (hollow_bass read flat) |
| strings | `sampled/strings`, low shelf -6 dB at 220 Hz | a discreet pad: bridge bars 4-8, the last chorus, the tag |
| brushes | `sampled/brush_kit`, drummer style jazz | the last chorus and tag only |
| vocal | Hanami (DiffSinger), style ballad, vel 54-86, `hero(family='vocal', genre='jazz', drive=False)` | a generic licensed voice (no clone), soft mode, mic pull on held ends |

Buses: `bus/ir_room_small` (room, guitar -9 dB send) and `bus/plate_80s` (plate, -17 dB) as the early-70s plate; the
vocal's own plate from the hero (wet -22 LU vs the dry voice: close and dry, the era's sound).

The sampler prints "undefined variable $sample_dir" for the Shinyguitar articulation files: known, the sfz reader
resolves those samples in the pack's Samples/ folder (silent_notes 0 on every guitar track).
