# Down on Jane Street - mix

Profile `jazz` (club record: brushes 13-16 dB under the lead, bass 3-6.5 dB under, others 4+ dB under, no bus glue).
Roles: lead = the voice (hero) in the sung sections, the piano in its solo (`b.piano.feature(solo, db=0.6)`: the
mixer's lead there - system fix in this branch: a featured track leads its feature sections); other = the piano
under the voice; rhythm = drums, rim, shaker; low = bass; the harmony voice (5 notes) counts as a second lead.

## MIX (song.py, module level)

```python
MIX = {
    'trim': {'drums': -0.3, 'rim': -0.3, 'shaker': -1.0, 'vocal': -1.5, 'bass': 1.0},
    'ride': {'vocal': {'end': -2.0}, 'piano': {'tag': -1.5}, 'shaker': {'head': -2.0, 'head_out': -2.0}},
    'eq': {'piano': [{'freq': 160, 'gain': -2.0, 'q': 0.8}], 'vocal': [{'freq': 3300, 'gain': -2.0, 'q': 1.0}],
           'bass': [{'freq': 63, 'gain': -2.0, 'q': 1.0}]},
}
```

| move | why (measured) |
|---|---|
| vocal -1.5 dB | the sung sections read ~3 LU over the piano solo (head -12.7, solo -15.7 LUFS) |
| vocal -2 dB at 3.3 kHz | 2-5 kHz +3.3 dB over the jazz reference, 94 % of it the voice (the hero's +2 dB presence): warm, not glassy |
| vocal ride -2 dB in the end | the last held "rain" read louder than the tag (-12.3 vs -14.5 LUFS): the song ends soft |
| piano ride -1.5 dB in the tag | the piano's fills sat -2.4 dB under the voice in the tag (others <= -4) |
| shaker ride -2 dB in the sung sections | the shaker and the voice shared 6-12 kHz (A&R) |
| bass +1 dB, -2 dB at 63 Hz | 7.7 dB under the voice in the head (window 3-6.5); the A&R found the sub +3 dB / 63 Hz +6 over the profile |
| drums / rim -0.3, shaker -1 dB | the kit inside 13-16 dB under the lead in every judged section |
| piano -2 dB at 160 Hz | the left hand and the upright both carried 60-250 Hz (masking warning in the intro / tag / end) |

Space (sound designer's moves, see SOUND.md): no echo throws on the voice, its hero plate at -17, the band's room -15
- the reverb went from -8.5 LU to -12.7 LU under the mix (jazz -20..-10). The A&R's major issue (the piano laying
out under the voice: 9 of 32 head bars empty, the sung sections 10-13 % wide) was an arrangement fix (continuous
bossa comping) plus the master's width x1.2: the sung sections now read 18-20 % wide above 150 Hz ('lush').

## Result (python -m agentsound mix, final build)

| section | lead | rhythm vs lead | low vs lead | piano (other) vs lead |
|---|---|---|---|---|
| intro | (no lead: the groove + the piano's hint) | | | |
| head | vocal | -15.0 | -5.7 | -4.8 |
| piano_solo | piano | -14.4 | -4.8 | |
| head_out | vocal | -14.7 | -5.6 | -4.0 |
| tag | vocal | -15.3 | -6.1 | -3.9 |

`moves: none - the balance is inside the targets`, `findings (0)`. Report: 0 warnings, 0 info.
