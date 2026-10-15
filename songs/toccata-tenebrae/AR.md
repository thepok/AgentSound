# A&R - Toccata Tenebrae

verdict: ship

summary: A real-pipe organ toccata with a clear dramatic arc - a free, silence-punctuated exordium, running 16ths,
three diminished-7th blows, the feet alone, a quiet flute song, a second toccata that grows from a closed swell box
to the full organ and a Grave that lands on a long E major chord in the church. One motif holds it together.

Judged on the render (report, images), not on listening - the A&R of this pipeline has no ears; the user's are the
final check.

issues (most severe first):
1. [minor] masking 'full' / 'pedal_full' 60-250 Hz in recitative and finale (report warning). The plenum's left
   hand over the full pedal: an organ tutti; lows correlation 0.98, the bass band -1.0 dB vs the classical balance,
   spectrogram_07 shows the pedal line clear under the chords. owner: arranger (a higher left hand in the chords)
   if the user hears mud. Kept.
2. [minor] top end 7.7 / 15.2 dB under the classical balance (brilliance / air, 'dull' info) - pipes through a
   stone church; the master air shelf took 2-3 dB, more would push the mixture's 2-5 kHz band. owner:
   mastering-engineer.
3. [minor] the toccata (0:31-1:10) is 3.3 LU under the exordium: principal chorus vs the exordium's full-organ
   chords - an organist's choice (the plenum saved for the climaxes); if the user wants the toccata to "kick in",
   the right hand goes to 'full' from bar 9 there too. owner: arranger.
4. [minor] the 16th figuration is generated from cells (turns, scales, bariolage) - varied every 4 bars and
   humanised (detache, hand timing), but a listener may still hear a pattern in the scale bars (toccata bars 5-8).
   owner: arranger.

checklist:
[x] a piece, not a loop - 7 sections, one motif in 6 guises, transitions (runs, fermatas, silences, rits)
[x] realism - Burea pipes, ornaments as played notes, detache / legato, one pipe per key, hand timing, agogics
[x] real dynamics - registration (soft -> principal -> full), texture, the swell box (episode solo 7.4 dB per
    phrase, 'dynamics automated'; toccata_ii box 0.3 -> 1.0); flat_dynamics warnings 0; the pedal 'info' lines are
    inapplicable (no velocity, no box on the pedal) - TODO.md
[x] produced - church lush in every section, rings into every silence, sub +3.1 dB (pedal shelf), lows corr 0.98
[x] clicks 0, silent notes 0, TP -4.4 dBTP, -19.9 LUFS-I, LRA 10.7
[x] brief: original material (no BWV 565 / Widor quotation), 4:05 + tail, registration plan, pedal on its own tracks

keep: the exordium's silences with the church blooming; the D#o7 rhyme (exordium -> climax); the pedal theme x4
under toccata_ii with the box opening; the plagal Am/E before the last E major chord.
