# When the Year Turns Gold (songs/when-the-year-turns-gold) - brief

## The wish

> "ich dachte eher an etwas wie Autumn in New York!"

Said after the smooth-jazz try "Nowhere to Be". What the user means: not a smooth / soul groove but a classic VOCAL
JAZZ BALLAD in the Great-American-Songbook / torch-song tradition - the feel of the famous ballad recordings of
that era (Billie Holiday, Ella, the Sinatra-era string arrangements): a rubato verse with voice and piano, then the
refrain in a slow tempo, songbook harmony, a lush but tender string orchestration swelling under the voice, a
ritardando ending on a held note and a colourful last chord. Sung by Hanami.

ORIGINAL: nothing of "Autumn in New York" (or any other standard) is used - not its melody, chords, form or words.
Only the idiom: the verse / refrain form, the AABA refrain, ii-V chains, secondary dominants, a backdoor cadence, a
passing diminished chord, a bridge that modulates, maj7 / 9 / 13 / #11 colours.

## The song

- **Genre / profile**: vocal jazz ballad / torch song with strings, `ANALYSIS = {'profile': 'jazz'}`.
- **Tempo / key / meter / feel**: 62 BPM, Db major (the verse in its relative Bb minor, the bridge in A major =
  bVI), 4/4. NO swing anywhere (the jazz_ballad preset gets `feel=jazz.Feel(62, ratio=0.5)`; brushes and bass
  `straight=True`). The intro and the verse are RUBATO (out of time: `s.rubato` + a slower tempo + fermatas), the
  refrain in tempo with a gentle `s.rubato` breathing, the ending a ritardando into a fermata.
- **The voice**: Hanami through `agentsound.singer`, style `ballad` (sung soft - the soft mode alone, the level by
  make-up gain -, few small scoops, slow narrow late vibrato on long notes only, no falls). Register Db4-C5, the
  bridge's top C#5 (= Db5) - nothing above. Stepwise lines with few leaps (a 4th at most), FEW syllables: 5-7 per
  2-bar line (~20 per 8 bars = 31 s), long vowels on the long notes, a rest after every line (the piano / strings
  answer there). Laid back: at 62 BPM the consonants are long, so the lay-back is derived from them (TODO
  nowhere-to-be: target P-centre 0..+10 ms; start from late_ms ~60-70). One voice, DRY and CLOSE
  (`hero(..., family='vocal', genre='jazz', drive=False)`), and IN the band, not on top of it (the user found the
  last vocal too loud): judge vocal vs band per section and err quieter.
- **Theme / lyrics** (roles/lyricist.md, LYRICS.md): an autumn city and a promise - "when the year turns gold" was
  what he said when he left in the summer; now it is autumn and she keeps the date at the ferry gate. Circled with
  concrete images (the summer leaving on the early train, the city putting its coat on, the ferry gate at five,
  maples, lamps coming on, leaves like letters), a few direct lines (the bridge: "I should have asked you to stay").
  Hook = title "When the year turns gold" opens every A; the last A turns it ("and the gold turns gray"). English,
  original.
- **Length**: ~4:50 (74 bars at 62 + the rubato verse and the fermatas).
- **Form**: `intro 2 (rubato, piano) | verse 8 (rubato, voice + piano) | A1 8 | A2 8 | B 8 | A3 8 | Ai 8
  (instrumental: piano melody + strings) | B2 8 | A4 8 | tag 4 (rit) | end 2 (fermata)`.
  Energy arc (1-5): intro 1 -> verse 1.5 -> A1 2 (bass + brushes enter) -> A2 2.5 (strings enter, a pad) -> B 3.5
  (strings swell, a countermelody) -> A3 3 -> Ai 3 (piano sings, strings answer) -> B2 4.5 (the climax: full strings,
  "stay" lifted) -> A4 3.5 -> tag 2.5 -> the held "gold" over Dbmaj9#11, fermata, 1.
- **Harmony** (ARRANGEMENT.md): A = `Dbmaj9 | Dbmaj9 Bb7b9 | Ebm9 | Ab13 Ab7b9 | Fm7 E°7 | Ebm9 Db9 (Bb7b9) |` + a
  turnaround per A (A1: the backdoor `Gbmaj9 | Gbm6 Cb9`; A2: `Ebm9 Ab13 | Dbmaj9 Bm7 E7b9` into the bridge; A3:
  `| Dbmaj9 Ebm9 Ab13` home; A4: the deceptive `Fm7 E°7` into the tag). Bridge in A major: `Amaj9 | F#m9 B13 |
  Bm9 E13 | Amaj9 Gm7 C7b9 | Fm9 | Bb13 Bb7b9 | Ebm9 | Ab7sus4 Ab7b9`. Verse in Bb minor; the last chord
  Dbmaj9#11 (6/9 with the #11 on top).
- **Band**: `bands.make('jazz_ballad', s, feel=Feel(ratio=0.5))` - the pedalled warm Salamander grand (piano =
  melody / fills, comp = the chords), the Meatbass upright pizz (two-feel, long notes), the Swirly brushes (stirs only,
  very soft), the 224XL chamber; its tenor is not used (without=('sax',)). Strings: `bands.symphony_orchestra(s,
  without=<everything but violins I / II, violas, cellos>)` - SSO 4.0 / VPO sections in their own concert hall,
  written in ONE `orch.Score` with a dynamics map: a pad (`h.voice` / `orch.bed`) under the voice, countermelodies in
  the voice's gaps (violins I, cellos), swells into the bridge and the last A, the final chord held.
- **The piano**: rolled ballad comping around the voice (`jazz.comp(style='ballad', answer=<vocal>)` + the pedal),
  short answers / fills in the voice's gaps through `pianist.arrange(style='ballad')`, the rubato intro and the
  instrumental A as a harmonized piano melody (`pianist.arrange`, melody first, Beegie Adair polish).
- **Reference**: none in assets/refrences/ for this idiom (and never a copy) - the jazz profile, the mixer's jazz
  targets and the preset's measured balance are the targets.

## HUMAN_FEEDBACK checklist (the A&R ticks these)

- [ ] CALM, not "aufgeregt": style `ballad`, sung soft, Db4-C5 (one C#5 region in the bridge), stepwise, few small
      scoops, no falls.
- [ ] LAID BACK, not "gerusht": syllables on / behind the beat (P-centre 0..+10 ms), few syllables on long notes,
      breathing space between lines.
- [ ] DRY and close: the voice's returns ~20 LU under it, no echo, no throws (`wetness.py`).
- [ ] The voice IN the band, not on top ("die Stimme im Vergleich zum Rest zu laut"): judge per section.
- [ ] NO swing: straight / rubato everywhere.
- [ ] A song, not a loop: verse + AABA + half chorus, the hook in every A, variation between the As, a real ending.
- [ ] Real dynamics: `flat_dynamics` 0 (voice, piano, bass, strings).
- [ ] Played, not keyboard-like: rolled piano chords, pedal, the pianist's fills, bowed strings with swells.
- [ ] Warm piano (no presence boost, the preset's soft hammers); fast two-key figures budgeted (ballad: 10-12 bars).
- [ ] Jazz drums soft: brushes 13-16 dB under the lead per section (here: even softer, stirs only).
- [ ] No doublers on any acoustic solo instrument (no hero octave / shift on the piano or strings).
- [ ] Diction passes (no `coda_short` / `coda_buried`); lyrics sent as text (out/lyrics.txt).
- [ ] 0 clicks, 0 clipped samples, true peak <= -1 dBTP, 0 silent notes.
- [ ] "Does it feel like a classic songbook ballad?" (verse, torch-song harmony, strings, held ending).

## Targets

- Mix: the jazz mixer profile; the voice leads but sits IN the band (bed 2-4 dB under in the sung sections, not
  more), bass 3-7 dB under, brushes >= 15 dB under, strings swell to ~2-3 dB under her in the bridge.
- Master: the jazz profile (-16..-13 LUFS integrated, LRA >= 6 LU - a ballad with a verse and a climax), true peak
  <= -1 dBTP, platform `dynamic`.
- Credits: Hanami (voicebank: credit Lotte V; its vocoder CC BY-NC-SA 4.0 = NON-COMMERCIAL), Salamander Grand
  (CC-BY 3.0, Alexander Holm), SSO 4.0 (CC Sampling Plus), VPO (see credits), Meatbass / Swirly (CC0). Private
  listening: fine; publishing: non-commercial only.

## Log

- producer: brief written (62 BPM Db, rubato verse in Bbm, AABA refrain + half chorus, bridge in A, jazz_ballad
  preset straight + SSO string sections, Hanami `ballad` Db4-C5, the hook "When the year turns gold").
- producer (2nd run; the first producer's process died after the first draft): master merged (mic_pull default for
  `ballad`), LYRICS.md / ARRANGEMENT.md / SOUND.md / MIX.md / MASTER.md written from the built song.
- lyricist: LYRICS.md, lyrics.txt (copied to out/); hook "When the year turns gold"; diction passes in every section.
- sound-designer: strings +9 dB, hall opened; harp +12; timing measured: P-centre +5.5 ms, 0 % early at late_ms=58.
- mix-engineer: voice -1.5 dB into the band, piano chords +4 (verse: left-hand roots added), brushes +1.5, the strings
  held 3.3 dB under her at the climax; 0 build warnings. Open: brushes softer than the profile window (deliberate).
- mastering-engineer: +2.5 dB shelf 6.3 kHz, -1.8 dB 800 Hz, width x1.15; -15.5 LUFS-I, TP -1.20, LRA 6.0.
