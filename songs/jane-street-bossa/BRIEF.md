# Down on Jane Street (songs/jane-street-bossa) - brief

## The wish

> "mach mir mehr straight jazz :)"

and, while it was being made:

> "und diesmal mit Gesang von der Frau, ein Jazz-Song"

More of what the user loved in perry-street-rain v3 ("WOW!!!"): piano-led New York bar jazz with STRAIGHT 8ths, no
swing - this time a SONG, sung by a woman: a new tune with its own tempo, feel and colour, not a copy.

## The song

- **Genre / profile**: jazz, a vocal jazz song with piano trio, `ANALYSIS = {'profile': 'jazz'}`.
- **Tempo / key / meter / feel**: 126 BPM, Bb major, 4/4, straight 8ths (Feel ratio 0.5, small lay-backs: piano
  +8 ms, bass / kit on the beat, the voice ~10 ms behind). Bossa-tinged: the A / B sections ride a soft bossa groove
  (brush 8ths, feathered kick, hat foot, cross-stick, a whisper of egg shaker), the C sections and the solo's climax
  open into a straight "push" four - the even-8th New York sound - and fall back into the bossa.
- **Why this and not another ballad**: the existing straight-jazz songs are a 96 BPM straight-8th ballad-trio
  (perry-street-rain, Ab major), a 152 BPM 3/4 waltz (minetta-lane-waltz, D minor) and a medium-swing tenor quartet
  (lanterns-on-carmine). None has a bossa feel, none sits at a mid-up 126, none is in Bb major, none is sung.
  HUMAN_FEEDBACK names bossa as one of the feels the user prefers ("straight 8ths, bossa, a ballad in even 8ths") and
  Beegie Adair (the user's model) plays bossas in trio - melody first, warm, polished. Bb (not the first draft's F)
  puts the tune where Hanami sings best: A3-G5, the hook F4-D5, the top G5 only once, at the climax.
- **The voice**: Hanami (licensed DiffSinger voicebank, female pop soprano, F3-A5) through `agentsound.singer`,
  style `ballad` laid back a little more (late_ms 10), soft-leaning (soft 0.75 / power 0.35), small falls, a narrow
  vibrato that blooms only on the held peaks; ONE intimate voice (no doubles, no harmony stack - jazz); the vocal hero
  chain `hero(vox.track, family='vocal', genre='jazz', drive=False)` (clean: no tube), the piano dipped where the words
  live. Credits: Hanami's vocoder is CC-BY-NC-SA (non-commercial): private listening fine, the build warns.
- **Theme / lyrics** (roles/lyricist.md, LYRICS.md): a woman at a sidewalk table on Jane Street late at night, waiting
  for someone who does not come, deciding she is fine - circled with images (rain on the awning, the empty chair,
  the candle, the waiter, the taxis), one direct line, attitude at the end. Hook line = title: "Down on Jane Street,
  rain".
- **Length**: ~3:25 (102 bars + fermata).
- **Form** (32-bar ABAC tune, 8-bar parts):
  `intro 8 | head (sung) ABAC 32 | piano solo ABAC 32 | head out (sung) B A2 C 24 | tag 4 | end 2`.
  Energy arc: groove intro (2) -> sung head (3, the C lifts to 4) -> piano solo builds 3 -> 5 (climax in its C) ->
  out chorus (4, the last C the warmest, its last line turned) -> tag (3 -> 2) -> the voice's last "rain" over the
  rolled final chord (1).
- **The hook**: a pickup leaping a sixth to a held D on "JANE", sighing to C, and the A of "rain" held while Bbmaj9
  turns into Eb9#11 (the maj7 becomes the #11 - the Jobim trick); in the C it returns a fourth higher (the song's top
  note, G5). Carried by the voice; the piano states it in the intro and makes it the motif of its solo.
- **Band**: `bands.make('bossa', s, without=('guitar', 'sax'))` - the preset's Salamander grand (both hands on one
  track), Meatbass upright, Swirly brush kit, Blonde Bop cross-stick, FreePats shaker, salon IR + 224XL plate,
  straight feel; the bossa groove from `jazzband.bossa_groove`, the straight sections from `brushes(straight=True)`.
- **The piano around the voice**: under the voice it comps (`jazz.comp(style='bossa', voicing='rootless',
  register=('A2', 'E4'), answer=<the vocal line>)`: below the voice, answering its rests) and plays short answers in
  the voice's gaps (written, harmonized by `pianist.arrange`); it never doubles or sits on top of the sung line. The
  solo: `soloist.solo` with a PIANO vocabulary (built for this song: `pianist.vocabulary()`).
- **Reference**: none available for jazz in `assets/refrences/` (only synthwave / rock / classical tracks) -
  `compare` skipped; the jazz profile, the mixer's jazz targets and the preset's measured balance are the targets.

## HUMAN_FEEDBACK checklist (the A&R ticks these)

- [ ] Straight 8ths, no swing ratio anywhere (Feel ratio 0.5).
- [ ] Piano-led bar jazz, melody first, polish over virtuosity (Beegie Adair): the hook clear and singable.
- [ ] A real song: form, tension / release, the hook returns and grows, variation, fills, a proper ending.
- [ ] Piano never a bare line: the intro hook and the solo harmonized, ornaments budgeted, rolled chords; under the
      voice it comps and answers.
- [ ] Fast two-key alternations are SPICE (about one per 16 bars, structural moments only).
- [ ] Warm, not hard piano ("es klingt hart").
- [ ] Drums well behind: 13-16 dB (RMS) under the lead in every section.
- [ ] Never robotic dynamics: `flat_dynamics` = 0 (piano, bass; the voice's dynamics live in its takes).
- [ ] Vocals: realism first (the singer's moves), word-final consonants audible (no coda_short / coda_buried),
      lyrics circled not on the nose, 2-3 quotable lines, the lyrics sent with the song.
- [ ] 0 clicks, 0 silent notes.

## Targets

- Mix: jazz mixer profile (rhythm -16..-13 dB under the lead, bass -6.5..-3), `python -m agentsound mix`; the voice
  in front in the sung sections, the piano in the solo.
- Master: jazz profile, -16..-13 LUFS integrated, LRA 6-12 LU, true peak <= -1 dBTP, platform `auto`.
- Delivery: METADATA (album "Blue Hour Sessions" like the other straight-jazz songs), COVER style jazz,
  `out/lyrics.txt` next to the mp3.

## Log

- producer: brief written (bossa-tinged straight-8th piano trio, F major 126, ABAC). Found: there is no piano
  vocabulary for `soloist.solo` (only guitarist / hornist / drummer) - built as system work
  (`agentsound/piano_vocab.py`, `pianist.vocabulary`); the soloist's saved moment now blocks the other phrases of a
  solo.
- arranger: instrumental draft rendered (head harmonized 90-97 %, the solo arc statement -> resolve with the trill at
  the climax, a 16-bar bass solo). Mixer: `track.feature()` now makes the featured track the lead of its section
  (the bass solo was judged against the piano's comping).
- producer: the user asked for a SUNG song with a female voice - re-briefed: Bb major (the voice's range), the bass
  solo dropped, a sung head + out chorus from the B, the piano comps / answers around the voice, lyrics (LYRICS.md).
- sound / mix: the first vocal render read `flat_dynamics` on the vocal - its notes are one trigger per sung phrase
  (velocity 127), the dynamics live in the takes: system fix `analysis.audioOnsets` (the compiler names singer tracks,
  the engine hears their note dynamics from the audio). Diction warnings ('drank', 'and', 'writes', 'on' too short in
  legato) fixed in the melody / words.
- a-and-r: revise - [major] the piano lays out under the voice (`jazz.comp(answer=)` drops every hit under a sung
  note: 9 of 32 head bars with 0 piano notes, the rest one chord on 1; the sung sections narrow, width >150 Hz ~10 %);
  minors: the out chorus a note-for-note repeat, the final chord dies with the voice in ~0.4 s, sub +3 dB (63 Hz +6),
  shaker vs voice 6-12 kHz, the solo's statement = hook x3, listen to the out chorus' scoops, ARRANGEMENT.md /
  docstring stale (AR.md).
- revise round 1 (arranger / sound / mix / master): the piano comps the bossa cells all through under the voice
  (register A2-E4, vel 50-58) and its answers are voiced (thirds / sixths / guide / drop 2 - harmonized 83-100 %);
  the out chorus paraphrased (same words, freer rhythm) with one soft harmony a third below on the climax line;
  fewer scoops (scoop_first 0.3, leap 0.4, peak 0.5); the solo in 4-bar phrases (the hook stated once, then answered;
  13 phrases: motif, answer, riff, blues, block, run, trill at the climax, resolve); the voice lets go of the last
  "rain" after 4.5 beats, the chord rings on; MIX -2 dB at 63 Hz on the bass, the master's low shelf dropped (sub
  +3.0 -> +1.1); the shaker -2 dB under the voice; master width x1.2 (the sung sections 13 % -> 18-20 % wide above
  150 Hz: 'lush'). Build: 0 warnings, 0 info; mix 0 findings; master check all ok (-15.1 LUFS, LRA 5.7, TP -1.2).
- a-and-r (round 2): ship - every round-1 issue fixed or improved (no empty piano bar, answers voiced, sung sections
  lush 18-20 %, out chorus paraphrased + one harmony, sub +1.1); minors only: the final chord rings < 1 s after the
  voice (tail 1.4 s at -21 dB), 630-800 Hz +4-5 dB / 63 Hz +4 (polish), the solo opens 3-5 LU under the head and is
  6/13 motif, listen once to the out chorus' onset bends (AR.md).
