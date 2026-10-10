# When the Year Turns Gold - mix (roles/mix-engineer.md)

Profile `jazz`. The aim of this mix: the voice IN the band (the user on the last song: "die Stimme im Vergleich zum
Rest zu laut"), a piano one can hear under her, strings that swell but never cover her.

## Moves (`MIX` in song.py)

| move | why (first build -> final, dB vs the voice) |
|---|---|
| trim vocal -1.5 | the voice sat 2.5-4 dB further over the band than the brief wants; vocal -15.9 -> -17.4 LUFS in a -15.4 mix |
| trim comp +4, ride verse +1 / intro +2 | the chords read -13..-16 under her (verse: -15.8, a voice over almost nothing) -> -7 in the refrain, -4.8 in the verse |
| the verse's left hand (roots, `VERSE_LH`) | the verse had no bass register at all |
| trim piano -2.5 | the fills in her gaps read -1.4 in A3 -> -2.4 (they answer in rests, never under a word) |
| trim drums +1.5 | brushes -19..-21 -> -15.5..-17.9: softer than the profile's -13..-16 on purpose (brief: very soft brushes, stirs only) |
| strings ride B -1, B2 -3.5, end +3 | B2 read -1.1 (the full strings over her) -> -3.3; the last chord -13.3 -> -8.9 |
| eq violins1 -1.5 dB at 3.3 kHz | violins I and the voice both carried >35 % of the presence band in B2: the warning is gone |
| harp +12 (was +8) | 'nearly inaudible' at +8, too loud at +16 |

## Result (`python -m agentsound mix`)

verse comp -4.8 | A1 rhythm -17.9, low -6.0, piano -5.4 | A2 -16.0 / -4.4 / bed -7.8 | B -15.6 / -4.3 / bed -3.7 |
A3 -16.1 / -3.4 / bed -5.7 | B2 -15.5 / -4.1 / bed -3.3 | A4 -17.6 / -5.5 / bed -6.0 | tag -16.7 / -5.7 / bed -6.7 |
end bed -8.9. Open findings: `drums_too_quiet` in A4 (-17.6, deliberate, see above) and an info for the piano fills
in A3 (-2.4, in her rests). Build: 0 warnings, 0 clicks in the mix (2 masked sample discontinuities of -37 / -43 dBFS
inside the violins II stem at bars 55 / 57).
