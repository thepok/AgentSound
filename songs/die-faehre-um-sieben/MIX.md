# Die Fähre um sieben - mix

`python -m agentsound mix songs/die-faehre-um-sieben`; the moves are `MIX` in song.py.

- Voice inside the record: trim -3.5 (it read +8.7 dB over the picking in verse 1), tag +6 (the whispered line).
- Guitar: trim +1.5, rides -5 intro (the tune leads), -2.5 break, -1.5/-2/-2 in the choruses; eq -1.5 dB at 450 Hz and
  3.3 kHz; a vocal-keyed carve at 220 Hz (depth 4.5) - the voice-vs-guitar masking findings went from warn to info.
- Bass -3 / -2.5 in choruses 2 / 3 (back into its 3-6.5 dB window under the voice); strings bridge -2.5, chorus3
  +4.5, tag -2.5.
- Width: 2-11 % at first -> double guitar, pans, dimension + width fx, master width 1.25: 17 % above 150 Hz (lush).

Final: voice vs the band verse1 +6.7, chorus1 +3.3, verse2 +1.0, chorus2 -0.8, bridge -0.7, chorus3 -1.5, tag -0.7
dB. Low end in its window except the tag (-8.4: the bass thins out into the ending, deliberate). Remaining info:
moderate masking (they alternate), level_jump tag -> outro (the ringing last chord), gtr_melody node_hot +1.7 dBFS
pre-master in float (no clipping: true peak -1.2 dBTP).
