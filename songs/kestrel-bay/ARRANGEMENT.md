# Kestrel Bay - arrangement

**Frame**: 84 BPM, A minor, 4/4, straight 8ths (half-time drums in the big parts), 72 bars + a 7 s ring-out = 3:33.

| section | bars | harmony | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 4 | Am F C G | 1 | clean Strat arpeggios, piano broken chords, cymbal swell; the lead | the guitar swells in (volume knob) on a long E5 that blooms into its octave (feedback) |
| verse | 8 | Am F C G Am Dm Esus4 E | 2 | + drums (ballad, side stick), bass, strings (rising) | the THEME, low and singing; half cadence on G#4 |
| chorus | 8 | Am F C G F G Am Am | 4 | + rhythm wall (crunch L / Marshall R, ringing), pad, half-time drums | the theme higher (to G5), resolving on A4 |
| bridge | 8 | F G Em Am Dm G Esus4 E | 3 -> 4 | clean arps, piano, strings, drums | a rising sequence of answers (F5, G5, A5, B5), then the set piece: a bend into A5 and G#5 held 6 beats over Esus4 -> E, blooming into feedback, an echo throw |
| solo | 8 | Am F C G x2 | 3 | the wall held back (ringing chords -6 dB), piano arps, light drums | SOLO 1 (soloist arc 'build', one arc over solo + solo2): the motif stated low, varied (sequenced up) with a wah answer |
| solo2 | 8 | Am F C G F G Esus4 E | 5 | full band, power chords, half-time | burst: tremolo picking climbing + a legato flurry; climax: a pinch-harmonic squeal with a wide vibrato, a whammy dive |
| break | 4 | F G Esus4 E | 2 | piano, pad, bass, clean, drums stop | a ghost bend sighing down, a whammy-scooped E5 with bar vibrato, a pinch harmonic, palm-muted chugs, a slide up into B4 |
| chorus2 | 8 | Am F C G Am Dm Esus4 E | 5 | everything | the theme an octave up (to D6: the song's peak), a unison bend on E5, a picked run down, vibrato |
| outro | 4 | Am F C G | 3 | drop: piano arps, clean, light drums | SOLO 2 (arc 'classic' over outro + outro2): the motif stated, answered with slides |
| outro2 | 8 | Am F C G Dm Am E Am | 5 -> 3 | full band | develop (palm-muted chugs + slide), burst (sweep-picked arpeggios), climax (the scream: a run to the top into a unison / 1.5-step bend, echo throw), resolution down to A |
| end | 4 | Am | 2 -> 0 | the band's last hit; strings / pad fading | the last A5 blooms into its twelfth (feedback), tapers, the echo carries it away |

**The hook / motif**: THEME_A (song.py): `E4 A4 C5(2) B4 A4 | A4(3) E4 | G4 C5 E5(2.5) D5 | C5 D5(2.5) | C5 E5 A5(2) G5
F5 | F5(2.5) E5 D5 | E5(3) D5 C5 | B4 G#4(2.5)`. It grows: chorus = a higher second half that resolves; chorus2 =
the whole theme an octave up with a new peak (D6). Its head (`E4 A4 C5 - B4 A4 | A4`, MOTIF) is the motif of both solos
(soloist statement / call slots, `soloist.develop` sequences and fragments it).

**Transitions**: intro -> verse: cymbal swell (drummer.swell) + the feedback note; verse -> chorus: the drummer's
fills (budgeted); bridge -> solo: the held G#5 feedback note resolves into the solo's Am; solo -> solo2: the wall
ramps in over the last two bars; solo2 -> break: the dive lands, the drums stop; break -> chorus2: palm mutes and the
slide up into B4 (pickup); chorus2 -> outro: the picked run down to E5 with vibrato; outro2 -> end: the resolution on A
and the band's final hit.

**Players**:
- drums: `drummer.arrange(order[1:], style='ballad', ending='hit', plan=...)` - ballad / halftime per section,
  energies 0.35 .. 0.95, fills budgeted by the drummer.
- bass: `bassist.arrange(prog, style='rock', part=...)` per section, one Memory; a long A1 at the end.
- rhythm guitars: `guitarist.arrange(style='rock', technique='ring' | 'power', sound=gtr_l)` + `.take(2)` on gtr_r;
  the clean Strat `guitarist.arrange(style='ballad', technique='arpeggio')` in the quiet parts.
- piano: broken chords (`arpeggiate('pinky')`) in the quiet parts, chords on 1 and 3 in the big ones, pedalled per bar.
- lead themes: `guitarist.lead(theme, prog, style='ballad' | 'rock', touch=(lo, hi), gestures=True, vib_style='wide'
  | 'rock', memory=lmem)` - picked / slurred notes, bends into long peaks (fast rise, overshoot, settle, vibrato below
  the bent pitch), finger vibrato up from the note, slides, hammer-ons, scoops.
- set pieces: `fretwork.feedback` (intro, bridge, end), `fretwork.bend`, `ghost_bend`, `whammy_scoop` +
  `whammy_vibrato`, `pinch`, `palm_mute`, `slide_in`, `unison_bend`, `picked_run`, `vibrato`.
- solos: `soloist.solo(s, lead, guitarist.vocabulary('rock'), at=[solo, solo2], arc='build', motif=MOTIF)` (the
  scream weighted down: saved for the outro) and `at=[outro, outro2], arc='classic'`, one `soloist.Budget(spice 1.5,
  fast 8, same 16 bars)` for both (fast figures: the tremolo at bar 37, the sweep at bar 63 - 26 bars apart), seeds 31
  / 22. Everything on the lead goes through ONE `fretwork.render` (one lane per target).

**Needs from sound design**: the lead G3-D6 (feedback / pinch / dive / wah need the sampler's harmonic and the wah
stage: the hero stack has them), mono legato (slurs, glides), velocity 56-127 (zones); a twin of the lead for the
unison bends' held string; rhythm guitars hard left / right, the clean guitar out of the bass's way.
