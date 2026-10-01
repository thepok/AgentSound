# Down on Jane Street - sound

The band is the `bossa` preset as a trio (`bands.make('bossa', s, without=('guitar', 'sax'))`): its sounds, chains,
placement, IR room and plate are measured productions (recipes/jazz-trio.md "Band presets"). The voice is Hanami
through the vocal hero. Changes on top are listed with the reason.

| role | sound | range played | chain + sends | why | checks (final build) |
|---|---|---|---|---|---|
| voice (lead) | Hanami (DiffSinger, `agentsound.singer`, style ballad + late_ms 10, soft 0.75, power 0.35, fall 0.12, vib 22 / 34 ct) | A3-G5 (the top G5 once: "JANE" at the C's climax) | `hero(family='vocal', genre='jazz', drive=False, echo=False, throws=False)`: hp 90, -2 dB 280 Hz, 3:1 comp 8 ms, de-esser, +2 dB 3.5 kHz, air shelf, breath stage; MIX: -2 dB at 3.3 kHz; sends: hero_plate -17, room -15 | one intimate, close voice - jazz, not a pop record: no tube (the coordinator: clean), no echo throws, little plate, the band's own wooden room | dynamics 16 dB (audio onsets), diction: every word-final consonant >= 40 ms (stops) / 35 ms (nasals), 0 coda warnings; presence 2-5 kHz back to the reference (+3.3 dB before the dip) |
| harmony voice (out chorus, one line) | Hanami take 2, formant +0.25, a third below "down on Jane Street, rain" | G4-Eb5 | the same clean hero (no ride / duck / carve / dips / throws), -8 dB, pan +0.3, hero_plate -17, room -15 | "doubles / harmony sparingly": one soft line at the song's emotional top | 5 notes, 6 dB under the lead |
| piano (comping + answers + solo) | `sampled/jazz_grand` (Salamander, softened hammers) - preset | comping A2-E4 under the voice, answers / solo C4-D6 | preset: eq > eq > soft-knee catcher > tape > eq; song: +1.5 dB air shelf at 9 kHz (no 2-5 kHz boost: "es klingt hart"); hero dip -1.5 dB at 3 kHz (the voice's words); MIX: -2 dB bell at 160 Hz (the left hand vs the upright); pan -0.25 (no guitar on the left: the mix leaned 1.8 dB left); room -13, plate -18 | the warm piano of perry-street-rain v4 ("WOW") - a hero piano (+2.5 dB at 2 kHz, Dimension-D) would be the opposite of warm | velocity response 1.8 dB / 10 vel; note dynamics 7.2 dB from velocity; peak pre-master -1.0 dBFS |
| bass | `sampled/upright_bass` (Meatbass pizz) - preset | Bb1-D3 | preset chain (eq, sub shelf, peak catcher, width); +5 dB on the fader (the preset's -9 is set for the guitar band's accented pattern at velocity 117); MIX +1 dB; room -18 | the upright, velocity = level | note dynamics 6.1 dB |
| brushes | `sampled/brush_kit` (Swirly) - preset | bossa brush 8ths, kick, hat foot; straight brushes / ride in the C sections | preset (hp 80); +1.5 dB on the fader, MIX -0.3 | "Drums etwas zu laut": 13-16 dB under the lead | rhythm vs lead -14.2..-16.2 dB per section |
| cross-stick | Blonde Bop side stick (`sampled/jazz_kit`, width 0) - preset | the 2-bar bossa clave | preset eq; MIX -0.3 | the bossa's clave, soft | in the rhythm group above |
| shaker | FreePats egg shaker - preset | 8ths, backstrokes accented | +2 dB (it read inaudible at the preset level), MIX -1 dB | a whisper of bossa colour | info: shares 6-12 kHz with the voice, alternating (moderate) |
| rooms | salon IR (convolver, ~0.8 s) for everything; 224XL plate (piano -18); the hero plate (voice -17) | | | one small wooden room, a club | reverb -12.9 LU under the mix (jazz -20..-10), tails -23 dB |

## Notes for the mixer

- Roles: the voice leads the sung sections, the piano leads its solo (`b.piano.feature(solo, db=1.0)` makes it the
  mixer's lead there), the piano is `other` under the voice (comping ~4-5 dB under it).
- The voice's dynamics live inside its takes: the report hears it from its audio (`analysis.audioOnsets`).
- No reference track for jazz is available (`assets/refrences/`): the jazz profile is the reference.
