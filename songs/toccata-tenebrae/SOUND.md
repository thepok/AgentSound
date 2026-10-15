# SOUND - Toccata Tenebrae

`bands.church_organ(s, organ='burea', without=('soft',))` - the preset's principal / full / pedal / pedal_full
roles, its St Nicolaes church IR, master and `classical` profile. Extra registrations (song tracks, same pack, same
hall bus):

| track | division / stops | use |
|---|---|---|
| principal | Huvudverk Principal 8' Oktava 4' Oktava 2' (+3.5 dB over the preset: a 16th line reads under its chord calibration) | exordium, toccata, echoes, toccata_ii 1-8 |
| full | Huvudverk + Mixtur V, Trumpet 8' | dim7 chords, toccata_ii 9-20, finale |
| pedal | Subbas 16' + Gedakt 8' | toccata, end of the pedal solo |
| pedal_full | Subbas 16' Principal 8' Oktava 4' Basun 16' | with 'full' |
| pedal_reed | the same stops, upper ranks as recorded (spaced pair), Subbas 16' on one mic | pedal solo (a line in the church, not a mono point; lows corr 0.98) |
| pedal_soft | Subbas 16' alone, -6 dB | flute episode |
| solo | Svallverk Rorflojt 8' + Halflojt 4' (enclosed: `instrument.expression` swells each phrase) | flute episode, an octave above the accompaniment |
| accomp | Brostverk Gedakt 8' (stereo flip: in phase) | flute episode |
| swell | Svallverk Rorflojt 8' Salicional 8' Principal 4' Skalmeja 8' (box 0.3 -> 1.0 over 8 bars) | toccata_ii LH chords |

Pedal tracks: low shelf -3 dB at 70 Hz (the 16' fundamentals; sub +8.7 -> +3.1 dB vs the classical balance).

Organ A/B: Pitea (French-romantic swell, C2-C7) vs Burea, same score: Burea wider (width 42 % vs 24 %, the spaced
pair reads as a church), sub +2.4 vs +6.1 dB, same loudness arc - Burea chosen. `TOCCATA_ORGAN=pitea` renders the
other (its registration table is kept in song.py).
