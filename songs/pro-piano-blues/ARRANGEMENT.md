# Low Ceiling Blues - arrangement

**Frame:** C minor, 104 BPM, 4/4, straight 8ths; 94 bars, ~3:47 (with the ritardando and the ring-out).

## Changes
- **A1** (the minor blues as it is): `Cm9 | Fm9 | Cm9 | Gm7b5 C7b9 | Fm9 | % | Cm9 | % | Ab13 | G7alt | Cm9 Ab13 | Dm7b5 G7alt`
- **A2** (the twist): bar 8 `Ebm9 Ab13` promises Db; bar 9 the Neapolitan **Dbmaj7#11** instead of the bVI7 (its #11 is
  G, the tonic's fifth), G7alt, Cm9, the turnaround.

## Form

| section | bars | harmony | energy | what happens |
|---|---|---|---|---|
| intro | 4 | Cm9 Fm9 Cm9 Dm7b5/G7alt | 1 | the riff alone, an octave down, no left hand, in time; a rising G7alt arpeggio (Ab B D F) into the head |
| head A1 | 12 | A1 | 2 | riff on I - a short call over the ii-V into IV - the riff a fourth up on IV - the riff home - the punchline (Eb F Ab C -> B Ab F Eb over G7alt) - a pickup (Ab B) |
| head A2 | 12 | A2 | 2+ | the riff's answer bends to Gb over Ebm9; the punchline turns into the Neapolitan: Ab C F -> G held as Db's #11, down the altered dominant, home on C |
| solo | 36 | S1 = A1, S2 = A1, S3 = A2 | 2 -> 4 | `soloist.solo(arc='build', energy=0.8)` from the riff's two bars: statement, development, burst, climax (the third chorus on the Neapolitan changes); the fast figure saved for it |
| out A1 | 12 | A1 | **5** | THE climax: the riff in octaves / locked hands (`climax=True`, touch +12/+20), the punchline up to **Eb6**, falling through Db6 (the b5 of G7alt) |
| out A2 | 12 | A2 | 3 -> 2 | the twist chorus paraphrased, softer, landing on C |
| tag | 4 | Cm9 Dbmaj7#11 Cm9 Dbmaj7#11 | 1 | ballad, ritardando: the riff against the Neapolitan vamp (A2's twist as the coda), the last G held over Db |
| end | 2 | Cm69 | 1 | rolled from the left hand up, the 9th on top: the G of the tag resolves into the tonic chord, fermata |

## The hook (riff)
`C C Eb C F F# G | . G F Eb C~` (8ths, the G on beat 3, the answer anticipated). AAB inside each chorus; transposed
to IV (F F Ab F Bb B C); the answer altered to Gb in A2 (the harmony's twist in the tune); octaves in the climax;
low and unaccompanied in the intro; against the Neapolitan in the tag; the soloist's motif.

## Transitions
Pickups in the melody (Ab B -> C at the end of A1; the G7alt arpeggio from the intro); `lead_in=True` lets the
pianist fill each part's opening gap; arpeggio sweeps (from perform.py) where the right hand left a bar empty before
the solo / out; ritardando from the tag's middle into the fermata.

## Players
One `pianist.Memory`. `jazz.chorus` with the endless defaults (style straight, LH shell, lh_vel 54, the genre's
ornament weights + blues_crush 1.2, lh_answers 0.85); intro style sparse without left hand; tag style ballad, LH
tenths. Solo: `pianist.vocabulary('straight')`, 2-bar phrases, vel 50-102, budget spice 2 / fast 16 / same 32 bars.
Out: paraphrased (A1 lightly), A1 `climax=True`. Performance seed 7319.

## Needs from sound design
Nothing new: the endless jazz-piano sound, register C2-Eb6.
