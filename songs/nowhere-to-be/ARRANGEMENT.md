# Nowhere to Be - arrangement (roles/arranger.md)

## Frame

72 BPM, Eb major, 4/4, STRAIGHT 8ths (the bossa preset's Feel: ratio 0.5, the keys laid back 8 ms, the voice ~60 ms
on its vowels), 78 bars + the fermata = ~4:25 (4:30 with the tail). A soul-ballad pulse: one chord per bar, a
two-feel upright, brush stirs one per beat, a feathered kick, the cross-stick on 4 (2 and 4 from chorus 1 on).

## Form

| section | bars | harmony | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 4 | Abmaj9 Gm7 Fm9 Bb13sus4 | 1 | Rhodes, then bass + stirs (bar 3), tenor | the Rhodes rolls the chords alone, the tenor states the hook at the voice's pitch (G4-C5) from bar 2 (an octave lower it masked the upright and the Rhodes) |
| verse1 | 8 | Abmaj9 Gm7 Fm9 Bb13sus4 / Abmaj9 Gm7-C7b9 Fm9 Bb7sus4-Bb7b9 | 2 | voice, Rhodes, bass, kit (rim on 4) | "Turn the clock to the wall" - 4 two-bar lines, a breath after each, the Rhodes answers in the rests |
| chorus1 | 8 | Ebmaj9 Cm9 Abmaj9 Bb13sus4 / Ebmaj9 Gm7-C7b9 Fm9-Bb13sus4 Ebmaj9 | 3 | + pad (far under), rim on 2 and 4 | the hook "Nowhere to be" (C5 held across the bar) |
| inter | 4 | = intro | 2 | tenor, Rhodes, bass, kit | the tenor answers the hook with a new second half (Bb4 C5 | Bb4 Ab4 G4 F4) |
| verse2 | 8 | = verse | 2.5 | the Rhodes a little denser, ghost taps | "Leave your coat on the chair"; line 3 climbs (Ab4 Bb4 C5 Bb4) where verse 1 fell |
| chorus2 | 8 | = chorus | 3.5 | + the tenor's two short answers in her gaps (bars 2 and 4) | the hook again |
| solo | 16 | verse + chorus changes | 3 -> 4 | tenor (featured +2 dB), Rhodes sparser, bass 'push', pad in its second half | `soloist.solo`, arc `ballad` (statement / answer / develop / climax: a long tone / resolve), no burst |
| bridge | 8 | Bmaj7 Bbm9-Eb9 Abmaj9 Abm6-Db9 / Gm7 C7alt Fm9 Bb7sus4-Bb7b9 | 4 | voice, full band | the turn to bVI (B major); "you said slow down" on the song's only D5; "so I stayed" lands on F4 over Bb7sus4 |
| chorus3 | 8 | = chorus, the last bar Cm9 (deceptive) | 4 | + a soft harmony a third below (lines 1 and 3), the tenor answers | the last line turns: "nowhere but you", lifted to G4 (open into the deceptive Cm9) |
| tag | 4 | = intro | 2 | voice, tenor answer, the band softer | "Nowhere to be" up to C5 once more; the tenor answers; ritardando from bar 3 |
| end | 2 | Ebmaj9 (6/9 on top) | 1 | voice, Rhodes chord rolled, bass Eb2, pad, last stir | the last "be" on Eb4 over the rolled chord, fermata, the room opens |

## The hook

`G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2` (degrees 3 . 4 5 6~6): a dotted quarter on the 3rd, two 8ths stepping up, the 6th
held over the bar line where Ebmaj9 becomes Cm9 (the 6th becomes the root). Appears: the tenor in the intro and the
inter, the motif of the tenor's solo, every chorus (x3), the tag. It grows by a harmony a third below in chorus3, by the last line's turn ("nowhere but you") and the
deceptive Cm9 that lets the tag sing it once more.

The verse cell: `G4/4 F4/8 G4/4. Ab4/8 G4/8 | Bb4/2.` (a quarter, an 8th, the syncopated dotted quarter, two 8ths
into a held note). Both cells are mostly stepwise: 0 leaps of a 4th or more in the whole vocal, mean interval 1.9
semitones, 0.9 % of the sung time at D5 (the bridge's "slow"), nothing higher.

## Transitions

- intro -> verse1: the tenor's hook ends on F3 over Bb13sus4, the Rhodes rolls into Abmaj9.
- every line end: 1-2 beats of rest, the Rhodes' comping answers there (`jazz.comp(answer=<the vocal line>)`).
- chorus -> inter / solo: the voice's long Eb4 on "be"; the tenor enters on the next downbeat.
- solo -> bridge: the solo's `resolve` stage (the hook's head low, a long last note), Bmaj7 is the surprise.
- chorus3 -> tag: the deceptive Cm9 instead of Ebmaj9; the tag's changes float (IV iii ii V) into the end.
- tag -> end: ritardando from the tag's bar 3 (x0.8), the voice's pickup "nowhere to" lands on the end chord.

## Players

- **Voice**: `singer.sing(..., voice='hanami', style='jazz', vel=(58, 84), late_ms=60, late_first_ms=20)` - one
  `singer.Memory()`; takes 0-3 per repeat (other human variation in verse2 / chorus2 / chorus3); `split_s=0.5` (every
  line its own breath). The harmony: the same line `transpose_scale(-2)` on `vocal_harm`, -8 dB, formant +0.2.
- **Rhodes** (keys, one track, both hands): `jazz.comp(prog, style='ballad', voicing='rootless', register=('D3',
  'G4'), answer=<the vocal line>, density 0.3-0.55, intensity 0.22-0.36, vel 58-68)`, rolled 14-30 ms, the pedal
  with the harmony (`jazzband.pedal`). No melodic piano line in this song (the brief: comp AROUND the voice), so no
  `pianist.arrange` part; the ending chord rolled by `s.ending`.
- **Bass**: `jazz.walking_bass(prog, straight=True, feel='two', pickups=0.25, gate=0.95, vel 64-74)` - half notes
  with an 8th pickup now and then; `feel='push'` under the solo. Its touch (4-bar arcs) on.
- **Drums**: `jazzband.brushes(b, bars, style='ballad', straight=True, kick='even', ghosts 0-0.15, fills=False)`
  (no fills: "no busy fills"), the cross-stick hand-placed on 4 / 2+4 at velocity ~34-38 (+-10 %, beat 4 leaning).
  The end: `jazz.last_stir`.
- **Tenor**: `hornist.arrange(..., family='sax', style='ballad', vel=(50-58, 72-88), memory=hmem)` for the intro hook,
  the inter answer, the chorus answers and the tag; the solo `soloist.solo(s, sax, hornist.vocabulary('sax',
  style='ballad', register=('G3', 'D5'), vel=(58, 100), weights={'shake': 0, 'growl': 0, 'run': 0.4, 'motif': 0.6,
  'answer': 1.4, 'long_tone': 1.4, 'fall_off': 0.3}), arc='ballad', motif=HOOK, budget=Budget(spice_every=3,
  fast_every=16))` -> statement motif x2, answer (motif, answer, motif, scoop_call), develop (motif, riff, motif,
  answer), climax long_tone, resolve (motif, resolve); spice kept: one scoop_call; no fast figure.
- **Pad**: `pad.chords(..., voicing='spread', register=('Bb2', 'Bb4'), vel 40-50)` in the choruses, the solo's second
  half and the bridge, 4-bar velocity arches; a held Ebmaj9 under the end.

## Needs from sound design

Voice: clean, dry, close. Keys: warm, no bark (velocities under ~90). Bass: round, the long notes sustained. Drums:
the stirs continuous at 72 (one per beat), the cross-stick a click not a crack. Tenor: legato player, live dynamics,
the breath stage after its compressor (hornist air lanes), soft - no tube grit, no exciter. Pad: soft, slow, dark.
