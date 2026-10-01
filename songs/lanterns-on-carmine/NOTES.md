# Lanterns on Carmine Street - production notes

Original medium-swing tune, Eb major, 140 BPM (ritardando + fermata at the end), ~4:05 + room tail.
Band: `bands.make('jazz_quartet')` - Salamander Grand (right hand + comping), Meatbass pizz upright, Swirly Drums
brushes, MTG tenor (legato player), salon IR room + 224XL plate. Analysis profile `jazz`.

## Form (140 bars)

| section | bars | what happens |
|---|---|---|
| intro | 4 | piano alone in time: rolled drop-2 block chords preview the head motif over a Bb pedal (Fm9 Bb13 x2), pedalled; brushes stir, swell into the head |
| head | 32 | AABA. Tenor states the head (A2 / A3 paraphrased: anticipations, pickups, enclosures, grace notes); bass in two for A1/A2, walking from the bridge; piano fills the gaps at the end of A1 and A2; comping answers the horn |
| sax_solo | 32 | tenor chorus: quotes and sequences the motif, bebop lines with enclosures (Ab-F#-G), triplet turns, builds through the bridge (brushes move to the ride, kick/snare "bombs") to a high E5 over Gb7#11, winds down, leaves space |
| piano_solo | 32 | drops back: single-note lines (solo_line with the motif, crushed grace notes), bridge in locked-hands block chords, last A in octaves; left hand shells |
| bass_solo | 16 | Meatbass solo over the A's: melodic, upper register, ghosted passing notes, four pitch-bend slides; fader +2.5 dB; piano whispers sparse shells, brushes only stir + hat foot |
| head_out | 16 | tenor from the bridge, calmer; piano answers the last phrase |
| tag | 6 | iii-VI-ii-V tag, then with tritone subs (Gm7 Gb7#11 Fm7 E7#11), then Gm7 C7alt Fm9 Bb7sus4 with a ritardando, pedal following the harmony |
| end | 2 | Ebmaj9#11 rolled from the left hand to A5, bass Eb, tenor holds G4 with scoop, swell and vibrato; fermata; room send opens |

## Harmony

- A1: `Ebmaj7 | C7b9 | Fm9 | Bb13 | Gm7 C7b9 | Fm7 Bb7 | Ebmaj7 C7b9 | Fm7 Bb7`
- A2/A3 reharmonised: tritone sub `Gb7#11` for C7b9 in bar 2, `Bb7sus4 -> Bb7b9` in bar 4; A2 ends `Eb6 | Bbm7 Eb7` (ii-V into the bridge)
- Bridge: `Abmaj7 | Db9 (backdoor) | Gm7 | C7b9 | Cm9 | F13 (V/V) | Fm9 | E7#11 (tritone sub of Bb7)`
- Melody design: rising arpeggio landing syncopated on the maj7 (D5), falling back through the b9 of C7; sequenced a half
  step up onto Fm's 7th; guide-tone resolutions (Ab over Bb7 -> G over Eb); the bridge sequences a two-bar phrase
  whose held note is the #11 (G over Db9, F# over C7b9), climbs to Eb5 over Cm9. Strong-beat tones checked against
  the chords (only deliberate 9/11/13 tensions remain).

## Performance / technique

- Piano: every comping chord rolled 8-22 ms (bottom up), 25-45 ms in the tag, 55-75 ms in intro / final chord;
  crushed grace notes before long solo notes; locked hands and octaves for the solo climax; pedal steps with the
  harmony in intro and tag, pedal held into the last chord.
- Tenor: `jazz.horn_line` - swing + lay-back baked in, legato transitions, breaths, scoops, falls at phrase ends,
  swells on the live dynamics, delayed vibrato, portamento into leaps; grace notes written into the head; solo
  phrases shaped with `phrase_dynamics` (upbeat accents, ghosted low notes); heads in the soft layer, the solo climax
  in the loud one (vel 105-121).
- Bass: walking with chromatic approaches, triplet / swung skip ghosts, a new seed per 8 bars; a descending Bb7
  triplet fill into every new chorus; solo with slides and ghost notes.
- Drums: two-feel brushes in the first half of the head, medium stir + taps, ride (spang-a-lang) for the second half
  of each solo, kick/snare-dig bombs setting up phrases, swells into new sections, soft crash + stirs on the final chord.

## Mix / analysis (final render)

Final render: 4:09 incl. tail, -15.4 LUFS-I, TP -1.2 dBTP, LRA 5.3 LU, width >150 Hz 23 %, reverb -14.2 LU,
0 clicks, 0 warnings (1 info: piano and tenor share the mids on the final chord - intended).
Section arc (LUFS-I): intro -17.1, head -15.4, sax solo -13.9 (climax), piano solo -15.4, bass solo -18.8,
head out -15.9, tag -15.3, end -20.6.

Iterations: (1) piano solo was louder than the sax climax and peaked +1 dBFS pre-master -> softer solo_line /
block-chord / octave velocities; bass solo was 6 LU under everything -> fader lift; the tag's pedal-up collided
with the final chord's pedal-down -> pedal ends before the last chord. (2) LRA 4.3 and piano/brush-ride masking in
the piano solo -> softer intro, first A's, head out and tag, no ride under the piano solo. (3) LRA 4.7 ->
smaller bass-solo lift, master limiter drive 5 -> 4 dB. (4) final right-hand chord without the tenor's G4.
(5) user feedback "Drums etwas zu laut": the jazz presets' drums -3 dB (`bandlib.jazz.DRUM_TRIM`): brushes now 13.8-16.3 dB (RMS) under the lead per section (were 10.8-13.3), drum peaks -8.7 dBFS (were -5.7); the final bass Eb vel 80 -> 88 (with softer drums the comping's share of the bass band on the last chord reached the masking limit). Mix -15.5 LUFS-I, LRA 5.3 LU, 0 clicks, 0 warnings. The sax 'leiernd' was measured (plain notes within +-2-5 ct, vibrato +-4-10 ct on long notes only): the sound is fine - the user dislikes the lazy swing style itself (recipes/HUMAN_FEEDBACK.md).
No jazz reference audio exists in assets/refrences (only synthwave references), so no reference comparison was run.

## Credits

CC-BY: Salamander Grand Piano V3 - Alexander Holm (CC-BY 3.0); MTG Solo Saxophones - MTG (UPF) / Freesound, SFZ by
kinwie (CC-BY 4.0). CC0: Meatbass, Swirly Drums (Karoryfer). The 224XL plate IR has an unclear license: fine for
private listening, check before publishing.
