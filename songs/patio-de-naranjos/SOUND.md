# Patio de Naranjos - sound

- **Guitar:** `sampled/concert_guitar` (Fiedler Natural Concert Guitar: nylon, 4 velocity layers - pp <= 60,
  p 61-90, f 91-120, ff 121+ - up to 7 round robins, release-triggered finger-off / fret noises). The installed
  alternatives (`sampled/nylon_guitar` FreePats: one sample per note, one layer; `gm/nylon_guitar`) are less alive.
  No physical-model guitar.
- **Stereo pair:** the samples are mono; the song builds the patch's instrument as `inst.sfz_multi` with a keypan
  (E2 -0.5 .. C4 -0.12 .. C5 +0.2 .. C6 +0.3: the low strings a little left, the treble right, like a pair at the
  12th fret) and `fx.width(2.0, monobass=150)`; the track panned -0.06 to centre the tune's weight. Width above
  150 Hz 2 % -> 18 %, L/R balanced.
- **Tone** (after the patch's high-pass 70 Hz and -1.5 dB at 220 Hz): -1.5 dB low shelf at 110 Hz (the thumb's
  boom on E2 / A2), +1 dB at 1.1 kHz (the tune's voice), -2 dB at 3.5 kHz (the close mic's edge), -3.5 dB shelf at
  7 kHz and a 15 kHz low-pass (string zing, air: nylon is warm).
- **Space:** a small wooden room (`bus/ir_room_small`, -13) close around it, the Musikverein hall
  (`bus/ir_concert_hall`, -13) behind; the hall send opens to 0 dB over the coda's last chord (the tail rings out).
- **Velocities:** the pattern mostly pp / p, the tune p / f, the ff layer only on a2's summit. A softer tune (-6)
  was A/B'd: the learned ears did not move (realism 83.8 vs 83.6) - the tune stays in front.
