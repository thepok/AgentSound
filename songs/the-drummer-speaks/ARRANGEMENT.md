# The Drummer Speaks - arrangement

**Frame**: 116 BPM, E minor, 4/4, straight 8ths (16th subdivisions straight), 92 bars, ~3:10.

## Form

| section | bars | harmony | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 4 | Em | 2 -> 3 | mallets, drums, organ; band from bar 3 | bar 1: a soft-mallet cymbal swell; bar 2: the drummer ALONE on the toms - the riff's rhythm as a tom figure (the solo's motif, orchestrated), kick on the quarters; bars 3-4: the riff (bass + two guitars in unison), the drummer's groove with a crash |
| A | 16 | riff (Em) x2, C D Em B7, riff x2, C D Em B7 | 3 | full band, hero guitar head | the head on the hero guitar over the riff; the 2nd 8 bars end higher (the B7 bar on F#5); organ pads under the riff, pushes in the turnaround; drummer: hat 8ths, kick locked to the bass |
| B | 8 | C D Em Em C D B7 B7 | 4 | full band | the chorus: open power chords, organ drop-2 pushes, the lead's line peaks on B5 over B7; drums on the ride, crash at the top |
| riff | 4 | riff x2 | 4 | bass + guitars + drums in unison | the band and the drummer play the riff's accents together (snare + kick under every riff note, crash / china on the 1s, the hat between); the last beat a flam tom pickup into ... |
| solo | 40 | (Em ringing out) | 2 -> 5 | DRUMS ALONE (the band's Em hit rings for 2 bars) | see the solo plan below |
| B2 | 8 | as B | 5 | full band | the band explodes back on the finish's downbeat (crash); the lead's chorus line louder |
| A3 | 8 | riff, C D Em B7 | 4 | full band | the head's second half (the high ending) |
| end | 4 | riff, B7, Em | 5 | full band | the riff in unison with the drums, B7 held while the drummer's last run goes around the kit, the final Em hit with crash + snare + kick - the crash choked a beat later and the band cuts with it |

## The hook

The riff (`riff_notes()`): `E E . G . A G E | D B A . E G A# B` in 16ths - accent rhythm `x..x..x...x.x...` (3 + 3 +
4 + 2 + 4). It opens the song on the toms (bar 2), is the A section's ground, comes back as the band-and-drums unison
before the solo, IS the solo's motif (`DrumMotif.make(cell=RIFF_CELL)`), and ends the song. The head melody (hero
guitar, degrees in E minor): `5:1.5 4:0.5 3:1 5:1 | 8:2 7:1 5:1 | 6:1.5 5:0.5 4:1 3:1 | 5:3` + a turnaround phrase,
its second statement ending higher; the chorus line climbs to B5 over B7.

## The solo (40 bars: a hand-written frame around `soloist.solo`)

| bars | who decides | what the listener hears |
|---|---|---|
| 1-4 | by hand: `drummer.perform([('time', 4, 0.6, {'crash': True})])` | the band's last hit with a crash; the groove keeps going while the chord rings away, then dissolves bar by bar (hat to quarters, to the ride, the snare starts talking) |
| 5-38 | `soloist.solo(s, kit, drummer.vocabulary(kit, hands='master'), at=(bar 5, 34 bars), motif=<the riff's rhythm>, arc='classic', seed=11)` | statement (the motif soft on the snare, three times, the space between kept by the hat foot) -> answer (the motif's head as the call, answered by a tom melody, snare / tom call and response, the hi-hat dancing, the motif developed) -> develop (calls answered by flams down the toms, paradiddles around the kit, a tom melody) -> burst (the gated 80s tom break, hand-hand-foot triplets, double bass) -> climax (a press roll from a whisper to a roar, the motif developed loud) -> resolve (the motif low, cymbal swells) |
| 39-40 | by hand: `('finish', 2, 1.0, {'motif': True})` | unison hits on the riff's accents (the band's cue), a gap, a run around the whole kit into B2's 1 |

The soloist's moves (seed 11, logged in the build): statement motif x3 | answer: motif + tom_melody, motif +
call_response, motif + hat_dance, motif + develop | develop: motif + flam_toms, motif + rudiment, motif +
tom_melody | burst: gated_toms, bonham, double_bass | climax: buzz, develop | resolve: motif + swell (x2). The budget
kept flam_toms, gated_toms, bonham, double_bass and buzz (the one fast move: the press roll). The first version of
the song ordered 22 moves by hand (`drummer.perform`, commit 797fc2f); both play the same vocabulary.

## Transitions

intro bar 1 -> 2: the cymbal swell lands on the drummer's tom figure; intro -> A: a crash with the riff; A -> B: the
drummer's fill (budgeted); B -> riff: crash, unison; riff -> solo: a flam tom pickup, then the band's Em hit (crash);
inside the solo: each move's last beat leads into the next (the finish's run lands on B2's 1); B2 -> A3: a fill;
A3 -> end: unison riff; the end: the run, the hit, the choke.

## Players

- drums: `drummer.perform` (intro tom figure, the solo's frame, the end), `soloist.solo` with `drummer.vocabulary` (the solo's body), `drummer.arrange` (intro groove, A, B / B2, A3: rock,
  density 0.55-0.6, one `Memory`, kick locked to the bass), `drummer.pattern` (the riff unisons), `drummer.swell`
  (mallets).
- bass: the riff (written, staccato on the short notes) + `bassist.arrange` (rock, verse / chorus) on the changes.
- guitars: the riff as palm-muted power chords (two takes, L / R), open power chords in the turnarounds / choruses,
  loud-quiet per section.
- organ: pads under the riff, pushes on the changes, the Leslie speeding up into the choruses.
- lead: the hero guitar (`hero_guitar.play`, vibrato, echo throws), velocities from `touch()`.

## Needs from sound design

A sampled kit with deep velocity layers, round robins, choke keys and a live hi-hat (Big Rusty: the patch, not the
band's rock_kit) with re-strike damping for the fast tom passages; a gated reverb for the tom break; a mallet kit for
the swell; a drum room and a parallel-compressed drum bus.
