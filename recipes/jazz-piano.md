# Jazz piano: composing a performance, not decorating a loop

Research and practical conclusions, 2026-09-28. These are compositional tools, not a formula
that proves a performance sounds like an experienced pianist. Keep the user's approved
sound design and judge musical improvements through listening, not just analysis scores.

## Harmony and voicing
Identify the chord quality precisely. Thirds and sevenths establish the quality of seventh
chords; additional colour notes should support that sound. Follow individual voices through
changes instead of moving an entire grip mechanically. With a bassist, piano roots are often
optional; solo-piano passages need their own harmonic foundation. For ii-V-I, try connecting
third/seventh guide tones before adding extensions. Keep low-register tensions uncluttered.
Source: Randy Felts / Berklee, [Piano Voicing Techniques](https://online.berklee.edu/takenote/basic-piano-voicing-techniques/).

## Melodic direction
Write the arrival notes first, then the route. Chromatic notes become meaningful through their
resolution: approach or surround an intended chord tone instead of inserting an arbitrary run.
An enclosure can start before a chord change and resolve after the bar line. Not every note
needs to be a chord tone, and not every chord requires its own fresh phrase.
Source: Forrest / Jazzadvice, [How to Use Enclosure](https://www.jazzadvice.com/lessons/how-to-effectively-use-enclosure/).

A solo should develop a recognisable idea over several measures. Change its rhythm, register,
ending or direction; balance short remarks with longer connected lines. Do not reset the melody
at every chord or concatenate unrelated licks to manufacture sophistication.
Source: Jazzadvice, [Playing Longer Lines](https://www.jazzadvice.com/lessons/playing-longer-lines-in-your-solos/).

## Rhythm and the left hand
Syncopation changes the relationship between attacks and the underlying pulse. A missing
expected attack, an offbeat anticipation, or displacement of an existing rhythmic cell can be
more effective than another note. A sustained offbeat and a short offbeat have different effects.
Source: Scott McCormick / Berklee, [Two Cool Rhythmic Devices](https://www.berklee.edu/berklee-today/fall-2009/the-woodshed/rhythmic-devices).

Use multiple piano textures: sparse shells, spread voicings, occasional inner lines and melody
support. The left hand should complement the melodic role rather than strike an identical
four-note block on every downbeat. Motive-based independent lines offer another option.
Sources: [Open Studio, Jazz Piano for the Bandstand](https://www.openstudiojazz.com/courses/jazz-piano-for-the-bandstand/),
[Neil Olmstead / Berklee, Contrapuntal Improvisation](https://www.berklee.edu/berklee-today/fall-2003/contrapuntal-improvisation).

## Application to AgentSound (our engineering / composition judgments)
- Compose rhythm, accents and articulation explicitly. Random millisecond jitter and a periodic
  tempo wave cannot create phrasing on their own. Keep the shared clock, but place intentional
  phrase accents and releases above it.
- Pedal is part of articulation, not a full-bar blanket. Catch a resonance, clear before chromatic
  motion, and preserve genuinely short comping. FluidSynth supports CC64; the native DX7 path
  currently approximates sustain by extending held-note durations.
- Verify actual pitches as well as chord labels. In our earlier material, labels such as Bb9/F9
  were shorthand for major-ninth sonorities, which is misleading jazz notation.
- Evaluate piano alone, then in context. Reverb, extra notes and low error counts cannot certify
  musical maturity. State when a result was checked by metrics rather than heard.
- For a revision, preserve approved backing audio and export a piano-only study plus the full mix
  so phrasing and sound design can be assessed separately.

## Articulation correction from listening feedback
A line written across bars is still fragmented if its keys release long before the next
attack. Do not confuse sparse note-on events with short durations. For a sung legato
sentence, write intentional breaths first and carry each inner note to the following
performed onset, allowing a small finger overlap where appropriate. Sustain pedal and
finger legato are separate controls: pedal clearing must not automatically sever the
melodic line. Verify overlapping same-pitch MIDI notes across hands do not cause an old
note-off to cut a newly struck key. Preserve user-approved passages when revising.
