# Hollis Street Shuffle Club - sound design

Locked by the brief: the endless jazz-piano sound by construction - song.py calls `agentsound.endless.perform.band`
(the genre's `solo_piano` preset, its master gain, the genre spec's trims / pans / sends / eq). Nothing changed.

- Register: written in F, the riff and solo (C5-G6) put the 800 Hz-2.5 kHz band at +6.0..6.1 dB over the piano
  reference (a `balance_mid_high` warning); played a whole step down in Eb it measures +3.2 dB and the report is
  clean. A writing decision (the key), not a sound change.
- Ending: the endless `_ending` in its 'cadenza' style; the 'plink' style masked piano / comp in the mid band of the
  2-bar ending (a report warning) in Eb.
- `_lh_breath` (song.py): a 2-bar phrase arc on the left hand's chords (piano 7.5 dB, comp 6.9 dB per phrase).
