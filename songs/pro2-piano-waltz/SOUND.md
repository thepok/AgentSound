# Carousel on Morton Street - sound design

Locked by the brief: the endless jazz-piano sound by construction - song.py calls `agentsound.endless.perform.band`
(the genre's `solo_piano` preset, its master gain + the waltz feel's shift, the genre spec's trims / pans / sends /
eq). Nothing changed here. Range used: RH G3-G6, LH Eb2-Eb4.

One performance touch in song.py (not a sound change): `_lh_breath` gives the left hand's chords a 4-bar phrase arc
(x0.84..1.16, the bar's first attack leaned on) - the pianist's waltz left hand measured 4.5 dB per phrase (a
flat_dynamics info); now 6.0 dB.
