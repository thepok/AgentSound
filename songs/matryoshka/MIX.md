# Matryoshka - mix

Tool: `python -m agentsound mix songs/matryoshka` (profile pop; roles: lead piano, bed choir / pad / strings /
violins, rhythm drums / perc, low bass / cello). The plan's moves were taken as they came; the rides the concept needs
were added by hand (the tool reads the cello as `low` and the choir as `bed`, but in the minor section and in the
coda they are voices).

```python
MIX = {
    'trim': {'drums': -2.5, 'perc': -2.5, 'bass': 1.5, 'cello': 0.7, 'choir': -0.5, 'pad': -0.5, 'strings': -0.5,
             'violins': -0.5},
    'ride': {
        'cello': {'minor': 5.0, 'coda': 2.0},
        'choir': {'chorus4': -2.0, 'coda': 6.0, 'end': 4.0},
        'violins': {'verse2': -3.0, 'chorus4': -1.5},
        'strings': {'chorus1': 1.5, 'verse2': -1.5, 'chorus2': 1.5, 'chorus3': 1.5, 'chorus4': -1.0},
        'bass': {'verse1': -2.0, 'build': -2.0, 'minor': -1.5, 'chorus2': 1.0, 'chorus3': 1.5, 'chorus4': 2.0},
    },
    'eq': {'pad': [{'freq': 1200.0, 'gain': -2.0, 'q': 0.9}],
           'strings': [{'freq': 450.0, 'gain': -2.0, 'q': 1.0}],
           'cello': [{'freq': 450.0, 'gain': -2.0, 'q': 1.0}]},
    'duck': [{'targets': ['violins'], 'key': 'piano', 'depth': 2.0, 'threshold': -36.0, 'attack': 15.0, 'hold': 60.0,
              'release': 260.0}],
}
```

| move | reason |
|---|---|
| drums / perc -2.5 | rhythm +0.9..+2.8 dB over the piano in build / chorus1 / verse2 / chorus2 / chorus3 (want -4..-0.5 in the hooks) |
| bass +1.5 (+1 / 1.5 / 2 in choruses 2-4) | after the sound pass pulled it 5 dB it read -5.2 under the lead in chorus 4 and the sub -4.3 dB vs the profile |
| cello +5 in minor, +2 in the coda | the minor section's first cycle is the cello's hook; the coda's x4 line must be followable |
| choir +6 in the coda, +4 on the end chord, -2 in chorus 4 | the x16 line (the key journey in 16 bars) sat 10 dB under the piano (-32 vs -22 dBFS RMS) - too hidden for the revelation; chorus 4's chords are colour |
| violins -3 / -1.5, ducked 2 dB under the piano | bed -1.3 dB vs the lead in verse 2 (bed_too_loud) |
| pad -2 dB at 1.2 kHz | pad / piano masking in the mids in verse 1 |
| strings / cello -2 dB at 450 Hz | strings / choir low mids on the end chord; cello / piano low mids in the minor section |
| bass -2 in verse1 / build, -1.5 in minor | bass_too_loud +2.1 / +2.5 there after the song-wide +1.5 |
| strings +1.5 in choruses 1-3 (A&R round 1) | the choruses read narrow (width 9-15 %): more of the wide section, the bed still 5-8 dB under the piano |

Before (pass 3) -> after (pass 5): report warnings 4 -> 0 (info only: masked choir loop clicks, cello / piano mid
overlap in the minor section = call and response, hats / tambourine share 6-12 kHz); mixer findings drums_too_loud,
bed_too_loud, bass_too_quiet -> none. Sound-design moves that came first (SOUND.md): bass -5 dB and a 1 kHz dip
(masked the piano), cello -7 dB + high-pass + an octave up in the coda (masked the bass), pad width 1.2, the bass
ducker 10 dB under the kick (sub masking in the build).

The master's input: the mix is ~0.7 LU quieter than the preset balance (drums / bed down): the mastering engineer
re-sets the drive (MASTER.md).

Final (pass 9): hooks bed -5.1..-7.7 / rhythm -1.9..-3.3 / low -1.6..-2.9 dB under the piano; width above 150 Hz 63 %;
0 report warnings; the one remaining mixer finding (bed_too_loud -0.5 in 'minor') is the cello's solo cycle read as bed
(AR.md round 2, TODO.md). The cello's counter-line in minor bars 5-8 is dipped 8 dB by the arranger's own gainDb lane.
