# Blueprint Boulevard - arrangement

**Frame**: 112 BPM, C major, 4/4, straight 8ths; 110 bars (+ the ritardando / fermata of the end), ~4:05.

| section | bars | harmony | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 8 | `Cmaj9 Fmaj7#11` x3, `Dm9 G13sus4` | 1.5 | Rhodes alone 4 bars, then bass + drums (intro role) | vibes hint the hook's head high (bars 5-8) |
| head1 | 16 | A (below) | 2.5 | alto hook, Rhodes comp (swing cells, straight), bass pop verse, drums verse | the hook stated |
| lift1 | 8 | `Abmaj7#11 Bbmaj9 Cmaj9 Em7/A9 Fmaj9 Em7 Dm9 G13sus4/G7b9` | 3.5 | sax climbs (Ab5 -> peak), pad, soft horn swells (long) | the sunrise |
| head2 | 16 | A | 2.5 | grand piano has the hook (paraphrased, harmonized, `pianist.arrange`), Rhodes sparse, ride, shaker | the sax answers into bar 9 and into the solo |
| sax_solo | 16 | A | 3 | `soloist.solo` with `hornist.vocabulary('sax', style='pop')`, arc classic, motif = the hook's head | Rhodes comps |
| piano_solo | 16 | A | 3 | `soloist.solo` with `pianist.vocabulary('straight')` (its LH comps), Rhodes out, ride | fast figure saved for bar 12 |
| lift2 | 8 | B | 4 | alto + MTG tenor a third under, horn stabs (accent) and a long chord, pad, open-hat shaker | festive |
| head3 | 16 | A, second half climbing | 4 | alto (climax=True), vibes double the first 8 an octave up, tenor a third under the second 8, pad | top G5 held over Em7 |
| outro | 4 | `Cmaj9 Fmaj7#11` | 2 | the sax quotes the hook's head, lands on C | ritardando from bar 3 |
| end | 2 | `Cmaj9` | 1 | `s.ending`: Rhodes C6/9 + piano top voicing rolled, bass C2, cymbal swell, fermata | loops back to the intro vamp |

A = `Cmaj9 Fmaj7#11 Cmaj9 Fmaj7#11 | Em7 A9 Dm9 G13sus4 | Cmaj9 Fmaj7#11 Em7 Am9 | Dm9 Fm6 Em7 A7b9 Dm9 G13sus4`.

**The hook** (written in F, played a fourth lower): `r/8 A4/8 C5 G5/4. E5/8 D5 | E5/2 ...` -> sounding
`E4 G4 D5(held) B4 A4 | B4 (the #11 of Fmaj7#11)`. Answered a step higher (`... E5 held`), the A's second half
climbs C5 -> the held G5 over Em7.

**Transitions**: the drummer's fills into every section (budget: fills 8 bars apart, flashy 16), crashes on the lifts;
the bassist's section-end fills; the sax pickups; the outro ritardando into the rolled final chord.

**Players**: one `hornist.Memory` per sax, one `pianist.Memory` (head2 + piano solo), one `bassist.Memory`; the
drummer locks its kick to the bass (`lock=bass`); soloist budgets: spice every 2 bars, fast every 16.

**Needs from sound design**: alto E4-G5 legato (mono='legato'), the grand warm, vibes F3-F6 with pedal, tenor A3-E5.
