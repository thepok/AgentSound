# One More Round - sound design

From the `melodic_house` preset (bandlib/edm.py) with the library sounds; system changes made on the way are in the
EDM branch (edm/* patches, chops chain).

- **drums**: TR-909 (hyperreal) + the main-room kit's shakers on key 82, a sine sub thump on C under every kick
  (bandlib.pop.kick_sub), the drum bus (4:1 parallel, tape). Machine-tight; carved 3 dB at 3.5 kHz while the chops
  play (`b.drums.carve(chops)`).
- **bass**: `edm/reese` - two detuned saw stacks over a clean mono sine sub, pumped 8 dB by the kick.
- **chords**: `edm/supersaw` (7-voice unison + an octave-down saw), pumped 7 dB; `amp.velocity` raised 0.5 -> 0.8
  in the patch (and `edm/future_chords`) - the chords' accents were flat (2.2 dB per phrase) - and re-levelled
  (+2.3 / +2.4 dB to -18 LUFS). The build opens its cutoff 700 -> 7000 Hz.
- **pad**: `synthwave/warm_pad`, cutoff lanes in the intro / outro.
- **pluck**: `edm/pluck` 16th arps into the dotted-8th echo, touch() 52-100.
- **lead**: `sampled/piano_lead` (Salamander, bright, C5-C7), through pianist.arrange (soft ballad style in the
  breakdown, 'bar' style octaves / climax in the drops).
- **vocal**: Hanami, `tune='hard'` (retune 0 ms), the vocal hero chain (pop: dry short plate, echo throws only).
  Prism: `preset='prismizer'` on the second breakdown chorus, its bus high-passed at 200 Hz into the hall.
- **chops**: `singer.chops` on the build's hook take (syllables 'one', 'more', 'round', 'oh'), +3..+15 st (the drop
  line an octave over the sung hook: small, bright chops) and -9..+3 st (the lower answer); chain `edm/vocal_chop` +
  chorus I+II 0.4 (width), echo -9 / hall -16 (echo -4..-6 in the talk box and outro: the tails in the gaps).
- **talk box**: `sampled/lead_guitar` (DI Strat -> the lead amp) played legato with glides, TIGER mouthing the words
  on one low pitch (`singer.mouth`, now with the line's velocities), `speech.talkbox` (vocoder LPC after the amp);
  an 'accent' utility lane after the chain restores the picking dynamics (the box flattened them: 0.0 dB per 10
  velocity steps -> 6.5 dB per phrase).
- **fx**: synthwave noise riser, reverse swell, impact, downlifter (s.transitions).
- **master**: `master/edm` (eq, 2:1 glue above -10 dB, tape, width 1.45 in this song with mono < 150 Hz, limiter 30 ms).
