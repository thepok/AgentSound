# Carousel on Morton Street - arrangement

**Frame:** Eb major, 150 BPM, 3/4, straight, 178 bars, 3:42. Solo piano (right hand `piano`, left hand `comp`).
Written with `recipes/jazz-composition.md`; every line is notation in song.py (`MEL`, `SOLO`, `INTRO_MEL`, `TAG_MEL`).

## Form
| section | bars | harmony | energy | what happens |
|---|---|---|---|---|
| intro | 8 | Ebmaj9 Ab7#11 Ebmaj9 Ab7#11 Gm7 C7b9 Fm9 Bb7sus4 | 1 | its own vamp (I - IV7#11): the motif's first bar stops on D = the Ab7's #11; the second try bends G -> Gb; rubato, ballad touch, LH tenths |
| head A1 | 16 | Ebmaj9 Dm7b5 G7b9 Cm9 F13 / Fm9 Bb13 Gm7 C7b9 Fm9 Bb13 Ebmaj9 Bb13 | 2 | the motif + its sequence re-fitted to the ii-V of Cm; an 8th answer to the A natural of F13; the peak phrase to D6; down to G4 |
| head A2 | 16 | ... Fm9 Bb7b9 Ebmaj9 Eb13 | 2 | A1 note for note to bar 12, then D C Cb Bb (a chromatic descent) and a rising line into the bridge |
| head B | 16 | Abmaj7#11 Abm9 Db13 Gbmaj7#11 Fm9 Bb13 Gm7 C7b9 Fm9 Abm6 Gm7 Gb7#11 Fm9 Bb7b9 | 3 | long high notes falling Eb D C Cb (lydian -> minor), the shape a step down in Gb, then the climb to the head's F6 (Abm6's 6th) |
| head A3 | 16 | ... Fm9 E7#11 Ebmaj9 | 2 | the tritone sub E7#11 takes A1's D as its 7th; the motif's head as the last phrase, home on G |
| solo A1 | 16 | A1 | 2 | the motif displaced by two beats, re-fitted to Dm7b5-G7b9 (Ab B / D F), a dorian answer with a triplet, an enclosure of Bb over Gm7, the chorus's one diminished climb (E G Bb Db -> C6) |
| solo A2 | 16 | A2 | 3 | the motif inverted, a lydian turn (A natural), a locrian line, an enclosure of C (Db B), the chromatic G G# A into F13 and its #11, longer 8th lines to C6, a chromatic B5 into the bridge |
| solo B | 16 | B | 4 | call and response: a long high note answered by a low line (C6 / a lydian line, Cb6 / a Db13 line), then the calls get lines of their own, chromatic Ab A -> Bb, Eb6 over Abm6, the lydian-dominant scale over Gb7#11 |
| solo A3 | 16 | A3 with B7#11 in bar 7 | 5 | the motif in diminution sequenced up three times, B5 over G7b9, the lydian-dominant climb over B7#11, the arch to the PEAK G6 over Bb13 (octaves / locked hands), down by scale and a chromatic Bb A Ab G, E7#11's G# -> G, a pickup into the head out |
| out B | 16 | B | 3 | the bridge near the head's level |
| out A3 | 16 | A3 with B7#11 (the solo's reharm, shared) | 2 | softer, the last A |
| tag | 8 | Ebmaj9 Ab7#11 Ebmaj9 Ab7#11 Abm9 Db13 Ebmaj9 | 1 | the intro's vamp, the motif an octave up then its echo, the backdoor (Abm9 Db13) home, ritardando |
| end | 2 | Eb69 | 1 | the endless `_ending` in its 'spread' style (the v1 waltz: rolled) |

## The craft moves (jazz-composition.md)
- Period plan per A: phrase landings G5 (via the b9 Ab), D5 (13th), Bb5, G4; the A's top D6 in its third phrase.
- Restatement: A2 / A3 repeat A1 up to bar 12; three different cadences (turnaround / chromatic descent into the
  bridge / tritone sub + the motif's head).
- Bridge contrast: long notes, higher (Eb6-F6), its own key areas (Ab lydian, Ab minor, Gb lydian).
- Solo: phrases start off the beat and cross bar lines; every change aimed at a guide tone; enclosures (Bb, C, Bb
  from Cb); chromatic passing notes on 12-29 % of the off-beat 8ths per part; one upper-structure arpeggio per 16
  bars; triplets and long landings for rhythmic variety (duration entropy 1.78).
- One reharm (B7#11 for F13), tied to the melody's A5 (its 7th), shared by the last solo A and the head out's A3.
- Velocities from `jazz.touch` per phrase (no beat accents); the left hand's chords breathe per 4 bars.

## Players
- `jazz.chorus` = `pianist.arrange` per part; one `pianist.Memory`; head style `straight`, LH `shell`.
- Solo devices per part: single + guide -> guide / 3rds / 6ths -> drop 2 / quartal -> octave / locked / drop 2
  (`climax=True`); touch 48-86 -> 52-94 -> 56-100 -> 64-116; solo fills only answer / approach / enclosure / stabs
  (no arpeggio sweeps).

## Needs from sound design
None (the endless sound, locked).
