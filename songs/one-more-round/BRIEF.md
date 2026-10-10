# One More Round - brief

**Wish** (TODO "Next", the user 2026-10-09): "EDM is big, enable that after you made the voice stuff" - the EDM
showcase: melodic house / future bass, ~3 min, a big drop, Hanami's hard-tuned hook + vocal chops from her own takes,
original lyrics, and a short talk-box guitar moment (the user's favourite vocal effect, HUMAN_FEEDBACK 2026-10-09).

- **Genre**: melodic house with future-bass colour (pitched vocal chops, breathing pumped chords). Preset
  `melodic_house` (agentsound/bandlib/edm.py), recipe recipes/edm.md. `ANALYSIS = {'profile': 'edm'}`, mixer profile
  `edm`.
- **Tempo / key / feel**: 124 BPM, C minor, 4/4, straight 16ths (machine-tight drums), `i VI III VII` (Cm Ab Eb Bb).
- **Length / form**: ~3:15, 100 bars in 8 / 16-bar blocks:
  `intro 8 | verse 16 | breakdown 8 | build 8 | DROP 16 | talk box 8 | breakdown 8 | build 8 | DROP 16 | outro 4`.
  Energy: filtered start -> groove -> soft breakdown -> build -> drop (peak) -> talk-box groove -> breakdown 2 (the
  chorus + prism) -> build 2 -> drop 2 (the sung chorus over the drop, the highest point) -> short outro.
- **The hook**: "one more round" (G4 Bb4 C5, three times, climbing to Eb5) - sung hard-tuned in the builds, CHOPPED
  (singer.chops) into the drop's hook line an octave up, doubled by the bright high piano (pianist.arrange, octaves)
  in the second half of each drop. Not beepy: a voice, chops of that voice and a sampled piano carry it; the supersaw
  only as pumped chords under it.
- **Vocal**: Hanami (female pop soprano, licensed voicebank, non-commercial vocoder), C4-Eb5, `tune='hard'`; the
  prism (`preset='prismizer'`) on the second breakdown chorus; TIGER mouths the talk-box words (singer.mouth). Theme
  for the lyricist: the last night of a summer fair - the wheel's lights going out, asking for one more turn (circled,
  never named: no "summer is over", no "I'll miss you").
- **References**: none (the recipe's mix targets).
- **Targets**: the edm profile (drops -9..-6 LUFS, the song -10..-6 integrated, TP <= -1 dBTP), clicks 0,
  silent_notes 0, flat_dynamics 0; vocal intelligible (presence owned) and IN the band.
- **HUMAN_FEEDBACK checklist**: no beepy lead; lead in front (bed under it); real dynamics on every melodic part (the
  chops and the talk box too); piano through pianist.arrange; a song, not a loop (drop 2 differs: the sung chorus, the
  offbeat bass, the chops answering); vocal dry and IN the band (2026-10-02 "die Stimme ... zu laut"); lyrics circled,
  2-3 punchy lines, the lyrics sent as text; the talk box as a short special moment.
- **Credits**: TR-909 samples (hyperreal, licence unclear), SampleRadar shakers (no redistribution), Salamander Grand
  (CC-BY, Alexander Holm), Hanami (Lotte V, attribution; AI❤dolGAN vocoder CC-BY-NC-SA), TIGER (CC-BY-NC-ND): private
  listening.

## Log

- producer: brief written; preset melodic_house, the hook on voice + chops + piano.
- arranger: ARRANGEMENT.md; first build (3:17) - drops only had 4 bars of hook: chops / piano statements now fill
  all 16 bars, the chorus sung twice in breakdown 2 and drop 2.
- lyricist: LYRICS.md ("our" was two syllables in CMUdict -> "my").
- sound designer: SOUND.md (edm/supersaw + future_chords amp.velocity 0.5 -> 0.8: the chords' flat_dynamics; chops
  chorus I+II; the talk box's accent lane).
- mix engineer: MIX.md (0 warnings; the drop-2 vocal vs kick / bass decision).
- mastering engineer: MASTER.md (master/edm release 30 ms; the limiter-saturation finding -> TODO).
- A&R: AR.md - round 1 revise (the build louder than the drop, the drop-2 vocal over the kick), round 2 ship.
