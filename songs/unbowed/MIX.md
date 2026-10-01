# Unbowed - mix

`python -m agentsound mix songs/unbowed` cannot judge this piece: it picks one lead role for the whole song (the
solo clarinet / horn / oboe, which play in three short sections) and leaves every other section "not judged" - the
TODO entry "Mixer: pick the lead per section" again. The balance was set by hand from the per-section stem levels of
the report (RMS dB per section, `.scratch`-style table from `report.json` nodes[].sections), the theme carriers
against their own accompaniment.

## Before -> after (section RMS, dB)

| section | theme carrier | before | after | the accompaniment that covered it |
|---|---|---|---|---|
| t1 (p) | violins I | -42.4 vs violins II -43.6, violas -44.2, cellos -42.0 | -38.5 vs -46.5 / -49.9 / -44.2 | the inner strings' 8th drive sat level with the theme |
| t1ff (ff) | violins I + flutes + oboes | -27.5 / -31.5 / -31.5 vs violas -25.7, cellos -25.1, horns -26.2 | -25.4 / -30.0 / -30.5 vs -31.0 / -28.3 / -27.7 | the violas' and cellos' 8ths were louder than the theme |
| closing | violins I | -26.8 vs violas -26.6 | -24.5 vs -31.8 | |
| storm | tutti syncopes | violas -22.3 on top | -28.0 | the violas' two voices of the tutti chord led |
| rec3 | violins I | -42.3 vs cellos -38.6 | -38.5 vs -43.5 | the cello cell and pizzicato over the theme |
| coda2 | violins I + horns | -28.7 vs violas -26.6, cellos -25.2 | -26.5 vs -31.9 / -28.3 | |

Basses +3 dB (sub -8.6 -> -4.3 dB vs the classical reference with the master's low shelf), the violas' and violins
II's low mids -2..-2.5 dB at 300 Hz, the violins I's 1.2 kHz box -1.5 dB and presence -1 dB at 3.3 kHz (presence
+6.1 -> +2.7 dB with the sound designer's steel dip), the hall's 650 Hz -2 dB.

## The MIX (song.py)

```python
MIX = {
    'trim': {'violins1': 1.5, 'violas': -2.5, 'cellos': -1.5, 'basses': 3.0, 'horns': -1.5, 'timpani': -1.0},
    'ride': {'violins1': {'t1': 3.0, 't1ff': 1.5, 't2': 2.0, 'closing': 1.5, 'rec1': 1.5, 'rec3': 3.0, 'rec4': 1.5,
                          'coda2': 1.5},
             'violins2': {'t1': -2.0},
             'violas': {'t1': -2.0, 't1ff': -1.5, 'closing': -1.5, 'storm': -2.0, 'rec1': -1.5, 'rec4': -1.5,
                        'coda2': -1.5},
             'cellos': {'t1ff': -1.0, 'rec1': -1.0, 'rec3': -3.0, 'coda2': -1.0},
             'flutes': {'t1ff': 1.5, 'rec1': 1.5, 'rec3': 2.0, 'coda2': 1.5},
             'oboes': {'t1ff': 1.0, 'rec1': 1.0, 'rec3': 2.0}},
    'eq': {'violins1': [{'freq': 1200, 'gain': -1.5, 'q': 1.0}, {'freq': 3300, 'gain': -1.0, 'q': 1.0}],
           'violins2': [{'freq': 300, 'gain': -2.0, 'q': 1.0}],
           'violas': [{'freq': 300, 'gain': -2.5, 'q': 1.0}],
           'cellos': [{'freq': 400, 'gain': -1.5, 'q': 1.0}],
           'hall': [{'freq': 650, 'gain': -2.0, 'q': 0.7}]},
}
```

No glue, no ducks: a concert mix, the hall and the players balance. The solo clarinet (t2) sits 8-11 dB over the
string pad, the oboe in the cadenza 18 dB over the held strings, the horn calls 6-10 dB over the tremolo.

## Revision 1 (A&R round 1: "the climax never arrives", "the soft passages are too soft for a phone")

- The conductor's arc: a `utility` named `arc` FIRST in the master chain (before the master eq and the limiter),
  ridden per section with 0.5-beat smooth ramps: t1 +3.5, rec3 +3, t2 +1, cadenza +1.5, the intro's pp bars +3
  (its two unison blows -1.5), the pedal's pp start +3 easing to 0 into its crescendo, coda1's subito p +2.5; the
  earlier fortissimos under the coda: closing -2.5, rec4 -2, storm -1.5, t1ff -1, rec1 -0.5; coda2 / coda3 +1.
  The dynamics map (arranger) moved the same way: earlier ff at velocity 104-112, the coda at 126-127, pp floor
  42-58.
- MIX: violins I t2 +4.5 and flutes t2 +2.5 (the restatement no longer drops under the clarinet's statement),
  basses fugato -4 (with the arranger's thinner doubling) and coda2 -2, oboes dev1 +1.5, clarinets dev1 +1.

| per section (LUFS / short-term max) | before | after |
|---|---|---|
| t1 | -32.0 / -25.6 | -26.6 / -23.1 |
| rec3 | -30.3 | -25.2 / -20.7 |
| closing | -17.2 / -14.2 | -19.4 / -16.4 |
| rec4 | -17.6 / -14.6 | -19.6 / -16.6 |
| intro (blows) | -19.0 / -15.2 | -22.1 / -15.9 |
| coda2 | -17.8 / -16.3 | -16.0 / -14.3 |
| coda3 | -15.8 | -14.2 / -13.0 (the loudest moment) |
| song | -19.6 LUFS-I, LRA 20.9 | -19.8 LUFS-I, LRA 17.3 |

## Revision 2 (A&R round 2)

- The arc: the fugato +6 dB for its first two entries (it opened at -36..-43 LUFS, after dev1 at -21), easing to 0
  by its last entry; the pedal +3 -> +2.5 -> +1.5 -> 0 at bar 13 (it no longer works against the crescendo); the
  transition -1 (it was louder than the counterstatement); the closing's and rec4's codettas +1.5 / +0.5 (the ff
  cuts had pulled them to -37..-40 LUFS).
- MIX: oboes dev1 +4, clarinets dev1 +3 (the winds' cells were ~4 dB under the violins' answers); coda2's cello
  8ths in bars 5-8 4 velocity softer (the theme sat under them in bar 7).
- Result: -19.8 LUFS-I, LRA 16.2 LU; fugato -28.2 LUFS (bars -30..-23), pedal -34.9 -> -15.5 over 16 bars;
  coda2 / coda3 short-term max -14.6 / -13.1 (everything earlier <= -15.9).

## Open

- Remaining warnings are the intended octave doublings: cellos / basses (coda1) and basses / timpani (coda2) in the
  bass band. Kept.
- The mix's master input change: -0.3 LU (the trims) - re-set by the mastering engineer.
