# Window on Barrow - sound design

Locked by the brief: the endless jazz-piano sound, unchanged, so a blind comparison hears composition and
performance only.

- `bands.make('jazz_trio', without=('bass', 'drums'), feel=jazz.Feel(100, ratio=0.6), master_gain=6.5)`:
  `piano` (right hand) and `comp` (left hand) = the Salamander `jazz_grand` (softened hammers), the room + plate.
- The genre's touches: trims piano -2 dB / comp +3 dB, pans piano -0.4 / comp -0.1, sends +6 dB room (both) and
  +8 dB plate (piano), eq on the piano -3.5 dB at 3.5 kHz (q 0.8).
- Verified: the compiled `tracks` / `buses` / `master` of this song equal those of an endless tune of the same feel
  (`endless.compose(g, 3, swing=0.6)`, 'straight'), sample zones aside (only the zones the notes reach are loaded).

2026-10-09 ("schrill und hart" -> smooth): the sound is no longer copied here - song.py takes it from `agentsound.endless.perform.band` (the genre's band: the `solo_piano` preset), so it stays identical to an endless tune by construction. The settings above are history.
