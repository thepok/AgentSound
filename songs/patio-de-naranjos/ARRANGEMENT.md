# Patio de Naranjos - arrangement

One player, one guitar: `guitarist.arrange(style='fingerstyle', hand='fingerstyle', melody=...)` per section with a
shared `Memory` (budgets, the last grip). The tune is written by hand (`notes()`), given phrase dynamics by
`humanize.touch(lo, hi)`, and fretted on top of the picked pattern by the guitarist (chord melody).

| section | bars | harmony | pattern under the tune | pattern vel | tune touch | idea |
|---|---|---|---|---|---|---|
| intro | 4 | Em Cmaj7 Am B7 | arpeggio `arp_pima` | 42-70 | - | the guitar alone, a B5 harmonic on B7, a bass run into a1 |
| a1 | 16 | Em Em Am Am D D G B7 / Em Em Am Am C B7 Em Em | `arp_ballad` | 32-56 | 64-102 | the tune low and quiet; 2 x 8 bars, the second answers higher (neighbour G5, a run to G5 over Am), a breathing empty last bar |
| b | 8 | C D G Em Am D G B7 (G major) | `arp_pima` | 34-60 | 68-106 | the contrast: long notes from G4 rising to G5, back to B7; ritardando into the key change |
| c | 16 | E E A A B7 B7 E E / C#m G#m A E F#m B7 E E | Travis (alternating thumb) | 36-62 | 72-110 | E major: a syncopated dancing tune, hammered chords on the changes (the guitarist's ornaments); a pickup into the bridge |
| bridge | 4 | Am G Fmaj7 B7 | `arp_up` | 38-66 | 70-110 | the Andalusian fall, the tune stepping down with it, up to F#5 over B7; ritardando + fermata |
| a2 | 16 | as a1 | `arp16` (16th arpeggios) | 38-68 | 78-120 | the tune again, louder over the fuller pattern; its last phrase climbs (E5-G5-E5-G5) to the climax and resolves on E5 |
| coda | 6 | Am B7 E E + E E | `arp_ballad`, then one rolled E chord (`let_ring`, 95 ms) | 38-64 | 62-100 | the hook's fall once more into the Picardy E major (fermata), B5 / E6 harmonics over the last chord |

Time: every 8-bar phrase breathes (`s.rubato(depth=0.03, phrase='breath')`), ritardandi at the end of b, the bridge
(+ a fermata on its last beat) and into the coda's E major (fermata), staying slow to the end.

The tune stays at or under G5 (the concert guitar's real samples end there; G#5 and up are flageolets).
