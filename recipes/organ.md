# Pipe organ (church organ)

Chorale preludes, chorales and partitas, trios, French-romantic toccatas, meditations / elevations, trumpet tunes and
festive postludes on a real sampled pipe organ in its church (`bands.church_organ`, played by `agentsound.organist`).
The endless generator: `python -m agentsound endless organ` (README "Endless ORGAN"). The references: the four
`songs/pro-organ-*` pieces and `songs/toccata-tenebrae`.

## The instrument: no touch dynamics

A pipe speaks at its level whatever the finger does. Every organ track plays at one velocity (`organist.ORGAN_VEL`);
the music's dynamics are:

1. **Registration** - which stops sound. Change it between sections (verses, episodes), never inside a phrase. A
   4-note chord reads roughly: flutes -29, soft swell -30, positive chorus -27.5, principal chorus -25, full organ
   (mixture + trumpet) -20 LUFS dry; the pedal 16'+8' ~-28, the full pedal with the 16' reed ~-24.
2. **The swell box** - `orch.swell(band, [(beat, 0..1 open[, 'smooth']), ...], roles=)` on the Swell's roles
   (`band.info['swell']`: soft, oboe, strings, swell_full): the gain AND the shade (closed = 12 dB down and darker).
   A crescendo in the box, a phrase that breathes, a diminuendo into the end. The only continuous dynamics.
3. **Texture and register** - more voices, the pedal entering, a higher tessitura.

The report judges an organ that way (`analysis.registration`, every `inst.organ` track): its combined level must
move 3+ dB between sections, or a swell lane must move it - else ONE `flat_dynamics` warn for the organ.

## Registrations (church_organ roles)

One role = one registration on one division. **Two roles of one division never sound at once** (one manual, one
set of stops): `organist.perform` raises. Burea (default) and Pitea have the same roles:

| division | roles | use |
|---|---|---|
| Great (Huvudverk) | `principal` (8' 4' 2'), `full` (plenum: mixture, trumpet), `cornet` (sesquialtera), `trumpet` (8' + a flute) | hymns, counterpoint, the climax; the cantus / trumpet-tune solo |
| Positive (Brostverk / Positiv) | `flute` (8' 4'), `positiv` (8' 4' 2': the echo manual), `reed` (cromorne / krumhorn) | accompaniment, the echo, a trio voice, a tenor cantus |
| Swell (Svallverk, enclosed) | `soft` (flutes / strings), `oboe`, `strings` (salicional / gamba), `swell_full` (chorus + reed) | the meditation's bed and solo, the toccata's crescendo |
| Pedal | `pedal` (16' + 8'), `pedal_soft` (16' alone), `pedal_full` (+ 4' and the 16' reed), `pedal_cantus` (4' reed: a cantus in the pedal) | the bass line, the toccata's pedal theme |

`church_organ(s, registers=('flute', 'cornet', ...), without=(unused classic roles), tremulant=True | ('oboe',))`.
Combinations that work: cornet solo / flute accompaniment / pedal_soft (chorale prelude); oboe solo / flute (the
oboe and the strings share the Swell); flute solo / strings; trumpet / positiv / pedal (trumpet tune); full +
pedal_full (plenum); swell_full + pedal (crescendo); positiv + pedal_soft (echo). A soft solo needs `pedal_soft`,
not `pedal` (13 dB louder).

## Idioms (the vocabulary: `agentsound.organ_vocab`)

- **Chorale**: four parts, a chord per beat, cadences at every phrase end (vary them: authentic, half, plagal,
  deceptive; a Picardy third in minor), a fermata on most phrase ends, the chord held into the breath. The bass in
  the pedal. Variations: passing 8ths in the inner voices and 4-3 suspensions (`flow`), the echo manual, the last
  verse on the full organ.
- **Chorale prelude**: the tune (cantus firmus) on a solo stop, ornamented at cadences (an upper-note trill with a
  turn), over ONE motif's counterpoint on another manual (`counterline(motif=)`: sighing 16ths, flowing 8ths, a
  dactyl) that keeps going through the cantus' rests (interludes), the pedal walking in quarters.
- **Trio**: three independent lines - right hand, left hand on another manual, pedal - no doubling, no parallels.
- **Toccata**: 16th figuration in the right hand (Widor's oscillation, broken chords, the turn cell, the rocking
  figure around a pivot, scale runs that rush into their goal), short detached off-beat chords in the left hand, the
  theme in long notes in the full pedal; a quiet middle (echo / closed swell) and a crescendo back; a held final
  chord.
- **Meditation**: a singing line on oboe / flute (tremulant) over held, voice-led chords; the swell breathing with
  the phrases; colour in the middle (planing: parallel chords under the tune, added 6ths, a chromatic inner voice).
- **Trumpet tune**: a dotted tune on the trumpet with cadential trills, detached chords on the beats, a detached
  walking pedal; an echo on a softer stop; the tune back on the full organ.
- **Fugue / fugato**: subject, tonal answer, countersubject (`fugue`), an episode sequenced, the pedal entering last.

Check the counterpoint before you play it: `organist.parallel_motion(voices)` lists parallel 5ths / octaves.

What gave the generator away in the blind organ rounds (songs/_blind/ROUNDS.md "Organ") - write the opposite:
- a verse that only changes stops: re-harmonize a repeat, move the tune to a solo stop, add a descant, ornament it;
- an end on the tag's IVm6 or on V: close V7 - I with the root in the pedal and a full chord;
- the climax early (a toccata's top note in bar 2): the highest note and the fullest stops in the last third;
- one figuration cell for 60 bars, the pedal theme in every section: change figures, let the pedal walk between the
  theme's entries, run a scale into the cadence;
- the 4 + 8k + 4 grid: a dominant pedal point (2-4 bars) before a return, uneven sections;
- a pedal in the tenor above the left hand, one dyad struck on every beat, a tune stuck on one note.

## Performance (agentsound.organist)

- Articulation is the organ's accent: `touch='auto'` (by note values and tempo), legato inner voices, detached
  chords and pedal in a trumpet tune, ordinary touch in fast lines; repeated notes are always re-struck.
- Breaths before phrases and big chords; the accompaniment keeps its pickups (`Voice(breathe=False)`).
- The agogic accent: the downbeat a little late, its note a little longer.
- Ornaments: `Voice(ornaments={beat or index: 'trill' | 'mordent' | 'prall' | 'turn'})`.
- At a change of stops on one manual the registrant needs time and the church rings: leave 1.5-2.5 s of silence
  before a verse on new stops (a fermata on the rest); a hand moving to a manual already drawn needs none.
  `organist.ring_gaps(song)` measures it.
- Ritardandi at section ends, a long final chord with a fermata (`song.fermata(at, hold=)`), `tail=8`.

## Mixing the church

- The recorded pipes carry the church already: the hall send stays moderate; let it bloom into the silences
  (`orch.ring(band, at, back=)` on the held chord before a pause).
- The pedal is the foundation (sub 30-100 Hz): mono (`stereo='left'` on the pedal roles - a stereo 16' reed reads
  `low_end_not_mono`); 4' pedal ranks may be stereo.
- Two registrations of one organ share bands by design (the plenum over the full pedal): the report marks that
  masking info only.
- Analysis profile `organ` (`ANALYSIS = {'profile': 'organ'}`): -24..-14 LUFS, a wide LRA, a top that follows the
  registration (a trumpet stop alone is bright: presence up to +6.5 dB).
- Phase: the Burea registers are recorded with a spaced pair; the preset flips the ones that read out of phase
  (flute, positiv, cornet, trumpet, reed).
