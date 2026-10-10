# Low Ceiling Blues - sound

Fixed by the brief: the endless jazz-piano genre's sound, built by `make_band()` exactly as
`agentsound/endless/perform.py` does - `bands.make('jazz_trio', without=('bass', 'drums'))`: one Salamander grand
(jazz_grand) for both hands (`piano` = right hand, `comp` = left hand), the salon room + plate; trims piano -2 dB /
comp +3 dB, pans -0.4 / -0.1, sends room +6 dB / plate +8 dB (comp room +6), EQ on the piano 3.5 kHz -3.5 dB Q 0.8.
No sound-design changes: only composition and performance may differ from an endless tune.

2026-10-09 ("schrill und hart" -> smooth): the sound is no longer copied here - song.py takes it from `agentsound.endless.perform.band` (the genre's band: the `solo_piano` preset), so it stays identical to an endless tune by construction. The settings above are history.
