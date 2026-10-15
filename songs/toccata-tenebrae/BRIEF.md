# BRIEF - Toccata Tenebrae (organ toccata in E minor)

## The wish

> AgentSound's first pipe-organ piece: an ORIGINAL organ toccata in the North-German / Baroque-to-French-Romantic
> toccata tradition (the drama of a Bach D-minor-style toccata or a Widor/Boëllmann-style toccata) ... Do NOT quote or
> copy any existing toccata.

## Frame

- Genre: classical (organ). Analysis profile `classical` (-23..-16 LUFS, very dynamic, safety limiter only).
- E minor -> E major (Picardy), 4/4, tempo map: free exordium q=66, toccata q=100, recitative q=60, pedal solo
  q=92, flute episode q=63, toccata II q=104, Grave q=54; ritardandi, 14 fermatas, rubato in the free parts.
- Length: ~4:05 + the church tail (4:09).
- Form: `exordium 7 | toccata 16 | recitative 4 | pedal_solo 6 | flutes 12 | toccata_ii 20 | finale 7`.
- Energy arc: free drama (loud dim7 chords between silences) -> running principal toccata -> three dim7 blows ->
  the feet alone -> quiet flute episode -> the second toccata growing from a closed swell box to the full organ ->
  dim7 climax, general pause -> Grave, E major held into the church.

## What carries it

No hook in the pop sense: one 7-note head motif (E with a lower mordent, B, C D E F#, G) is the whole piece's
material - octaves, figuration cell, pedal solo, flute melody, pedal theme x4, Grave chords. Sound: the real Burea
Church pipe organ (Lars Palo, GrandOrgue samples) through `bands.church_organ`, the St Nicolaes church IR.

## References

None (the user named the tradition, not a recording). Nothing quoted: no BWV 565 motif (its A-G-A mordent and
descending figure), no Widor theme.

## HUMAN_FEEDBACK checklist

- [ ] A piece, not a loop: form, the motif returns and grows, variation, transitions.
- [ ] Realism (sampled, played, articulated): real pipes, an organist's articulation and timing, not a sequencer.
- [ ] Real dynamics: an organ has none per note - registration, texture, register and the swell box carry them;
      `flat_dynamics` must be 0 where it applies (the swell solo), explained where it cannot (pipes without a box).
- [ ] Produced: a church around it (space lush), a full but not muddy pedal.
- [ ] clicks 0, silent_notes 0, true peak <= -1 dBTP.

## Targets

-23..-16 LUFS-I, LRA 8-20, no glue, safety limiter (-1.2 dB ceiling), platform auto.

## Log

- producer: brief written; preset `church_organ` read, both organs (`burea`, `pitea`) auditioned by render.
- arranger / players: form + material in song.py (local `Organist` helper: ornaments, articulation, hand timing,
  one-pipe-per-key); 7 sections, 1600 notes.
- sound designer: Burea chosen over Pitea (width 42 % vs 24 %, sub +2.4 vs +6.1 dB, same arc); extra
  registrations as tracks (swell solo, Brostverk accompaniment, swell chorus, Subbas alone, pedal solo).
- mix: MIX eq on 'full' (mixture harshness, swell masking); hall sends, rings at every fermata.
- master: air shelf +2 dB @ 8 kHz, limiter ceiling -1.2; -19.9 LUFS-I, TP -4.4.
- A&R: ship (AR.md).
