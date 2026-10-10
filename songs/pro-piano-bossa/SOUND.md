# Folded Letter Bossa - sound design

Locked by the brief: the endless jazz-piano sound with the bossa feel, unchanged.

- `bands.make('jazz_trio', without=('bass', 'drums'), feel=jazz.Feel(116, ratio=0.5, layback={'piano': 8, 'comp': 4,
  ...}), master_gain=6.5 - 1.5)`: `piano` / `comp` = the Salamander `jazz_grand`, the room + plate.
- The genre's trims (piano -2 / comp +3 dB), pans (-0.4 / -0.1), sends (+6 room, +8 plate on the piano), eq (piano
  -3.5 dB at 3.5 kHz).
- Verified: the compiled `tracks` / `buses` / `master` equal those of an endless bossa tune (seed 1, 'The Velvet Hour
  Blues'), sample zones aside.

2026-10-09 ("schrill und hart" -> smooth): the sound is no longer copied here - song.py takes it from `agentsound.endless.perform.band` (the genre's band: the `solo_piano` preset), so it stays identical to an endless tune by construction. The settings above are history.
