# ARRANGEMENT - Toccata Tenebrae

## The motif

E5 (lower mordent E-D#-E) 1.5 | B4 .5 | C5 D5 E5 F#5 16ths | G5 1 - a mordent, a falling fourth, a scale climbing a
sixth to the minor third. Its mordent (a note and its chromatic lower neighbour) becomes the toccata cell
(T, T-1, T, chord tone below) - so the 16ths are the motif's ornament spun out.

| section | bars | time | registration | material |
|---|---|---|---|---|
| exordium | 7 | 0:00 | principal; full + pedal_full for the chords | motif in octaves, fermata, silence; accelerating run into D#o7 over E (fermata); Em; rising Em arpeggio, trill A#5 -> B5; bariolage on a B4 pivot over a B pedal; iv6 - V (trill D#5) - i, fermata, silence |
| toccata | 16 | 0:31 | principal + pedal (Subbas 16' + Gedakt 8') | 4 bars turn cells over an E pedal point (Em, Am/E, D#o7/E, Em); 4 bars scales (C, Am, F#o7, B7); turn cells over a G pedal (G, C/G, D7/G, G); bariolage (Am, F#o7, B7); a rushing E6->D#4 scale, rit. LH: chords on 2 and 4, then off-beat 8ths |
| recitative | 4 | 1:10 | full + pedal_full; flourishes on principal | C#o7 / Do7 / D#o7, each with a fermata and a silence, an echoing 32nd flourish between; Em6/4 - B7 - C (deceptive), fermata |
| pedal_solo | 6 | 1:33 | pedal_reed (Basun 16'), last 2 bars pedal | the motif in A minor and E minor in the feet, 16th toe-heel runs; the reed off, a falling scale, rit., D3 fermata (V of G) |
| flutes | 12 | 1:50 | swell solo Rorflojt 8' + Halflojt 4'; Brostverk Gedakt 8'; Subbas 16' | G major: the motif augmented (a turn on G, D, E F# G A, B held), sequence on B, back to E minor; trill on F# over B7, fermata |
| toccata_ii | 20 | 2:39 | principal (bars 1-8) then full; swell chorus + Skalmeja; pedal_full | the motif x4 in the pedal (E3 6 beats, B2, C D E F#, G3 4) answered in A minor; upper-neighbour cells; circle of fifths in scales; dominant pedal B2 with bariolage and A#o7; climb C - C# - D# in the pedal; D#o7 over E2 fermata, general pause |
| finale | 7 | 3:27 | full + pedal_full | the motif harmonised (Em, Em/G, Am, D/F#, Em/G, B7/A, Em/G), fermata; a rushing run; Neapolitan F/A, fermata, silence; Em6/4; B7 with a trill on D#5; breath; E major; Am/E; E major held ~10 s |

## Organist's performance (local helpers, song.py `Organist`)

- Ornaments as played notes: lower / upper mordents (~68 ms notes), trills from the upper note with a turned ending,
  turns.
- Articulation: detache 16ths (gap ~20 % of the slot, strong 16ths held longer), legato with 20 ms overlap, chords
  lifted ~70 ms before the next, staccato off-beat chords; one pipe per key (a re-struck key ends the earlier note).
- Timing: per-hand gaussian (+-2-7 ms), chord notes spread 0-10 ms, runs accelerating into their goal
  (`accel=(1.35, 0.75)`), agogic breaths (0.1-0.25 beat) before the big chords.
- Tempo map: rubato in the free exordium / the toccata / the episode, ritardandi at every section end, fermatas.
- The church: orch.ring at each fermata before a silence, given back when the music resumes.
