# Expensive Habits (songs/expensive-habits) - brief

## The wish

> "mach mir auch einen Pet-Shop-Boys-Song"

An ORIGINAL synth-pop song in the spirit of the Pet Shop Boys' classic era (West End Girls / It's a Sin / Always on
My Mind / Go West / Heart): the idiom, not the songs. No melody, lyric, riff, chord progression or hook of theirs or
anyone's.

## The song

- **Genre / profile**: 80s Euro synth-pop / Hi-NRG-leaning dance-pop with a sung lead, `ANALYSIS = {'profile': 'pop'}`.
- **Tempo / key / meter / feel**: 118 BPM, 4/4, straight 16ths, machine-tight (the drummer's `synthpop` style, 0.8 ms
  spread). C minor verses (i VI iv V), the chorus blooms into the relative major (Eb: the V chord G of the pre-chorus
  resolves deceptively to Eb), a whole step up (D minor / F major) for the last two choruses and the outro.
- **The voice**: TIGER (male DiffSinger voicebank, A2-C#5, NON-COMMERCIAL) through `agentsound.singer`. Cool,
  understated, almost deadpan: verses half-spoken - a narrow recitation around G3 (Eb3-Bb3), repeated notes, quick
  talky 8ths followed by ~1.5 bars of rest, sung SOFT and laid back (style `ballad` base: the soft mode alone, small
  swings, almost no vibrato, vowels ~24 ms behind the beat); the chorus blooms (G3-Eb4, after the key change A3-F4),
  style `pop` but restrained (few small scoops, a narrow late vibrato on long notes only, no doits, the soft mode still
  the base, the power mode only on the loudest peaks). Dry and close (the pop vocal space: a short plate ~16 LU under
  him, echo only as section-end throws), clean (no tube grit). Hanami sings soft "ahs" in choruses 2-4, ~11 dB under
  him, panned left.
- **Theme / lyrics** (roles/lyricist.md, LYRICS.md): two people living above their means in a city at night - taxis
  at 4 a.m., a card that isn't theirs, the guest list, a flat with a view of a better flat, reading about houses like
  poems; they spend the night like money. Ironic, observational, circled with urban images; the bridge's one direct
  line ("I'll trade it all for one slow Sunday"); the hook = the title "Expensive habits" on the chorus's top note.
- **Length**: ~3:58 (116 bars at 118 + a 5 s tail).
- **Form**: `intro 8 | verse1 16 | pre1 8 | chorus1 8 | post1 4 | verse2 16 | pre2 8 | chorus2 8 | post2 4 |
  bridge 8 | lift 4 | chorus3 8 (+2) | chorus4 8 | outro 8`.
  Energy (1-5): intro 2 -> verse 2 -> pre 3 -> chorus 4 -> post 3.5 -> verse 2.5 -> pre 3.5 -> chorus 4.5 -> post 4 ->
  bridge 2.5 (half-time breakdown) -> lift 3.5 (orchestra-hit build) -> chorus3 5 -> chorus4 5 -> outro 3 -> end.
- **The hooks**: (1) the sung title "Ex-pen-sive ha-bits" (pickup to the chorus's top note Eb4); (2) the instrumental
  riff (C minor, 4 bars: a syncopated climb to G5 and its answer) on the bright layered glass piano (sampled melody
  piano + DX glass + pad), octave-doubled like a pianist's right hand, the brass stab under it - intro, post-choruses,
  outro (+2). No thin synth lead anywhere (HUMAN_FEEDBACK: "etwas Piepsiges").
- **Band**: `bands.retrowave(s, without=('lead',))` = 80s pop kit + Linn claps through the keyed gated snare, the
  octave bass, the Juno pad, the bright DX e-piano, brass stabs, the Fairlight choir, 224XL hall + plate,
  master/synthwave; plus the Jupiter string machine, the DX marimba sequence (16ths), the GM orchestra hit (the
  Fairlight-era stab), riser / impact / downlifter. Drums through `drummer.arrange(style='synthpop')`.
- **Reference**: none in `assets/refrences/` for this idiom - `compare` skipped; the pop profile, the mixer's pop
  targets and the preset's calibration are the targets.

## HUMAN_FEEDBACK checklist (the A&R ticks these)

- [ ] A song, not a loop: form, the hook returns and grows (sung title x4 + tag, riff x4), variation (verse 2's
      e-piano and marimba, Hanami from chorus 2, the key change, the turned last line), fills, a real ending.
- [ ] No beepy lead: the melody belongs to the voice; the riff on the bright layered piano with body, brass under it.
- [ ] Vocal CALM / cool, not "aufgeregt": verses soft mode alone, few scoops, little vibrato; chorus restrained.
- [ ] Vocal LAID BACK, not "gerusht": vowels behind the beat, breathing space after every line, no crammed syllables.
- [ ] Vocal DRY: returns ~15-16 LU under the voice, no constant echo.
- [ ] Vocal sits IN the band, not on top of it ("die Stimme im Vergleich zum Rest zu laut").
- [ ] Diction passes (no `coda_short` / `coda_buried`); word-final consonants audible; lyrics.txt with the song.
- [ ] Real dynamics: `flat_dynamics` 0 (riff, bass, keys, vocal).
- [ ] Produced, not "Gameboy": hall / plate / echo, width, a full low end, gated snare.
- [ ] No grit on the voice.
- [ ] 0 clicks, no clipping, true peak <= -1 dBTP, 0 silent notes.
- [ ] Does it feel like classic synth-pop (sequenced bass, machine drums + claps, pads + string machine, orchestra
      hits, a key change into the last chorus, a melancholic-but-danceable mood)?

## Targets

- Mix: the pop mixer profile (rhythm -4..-0.5, low -4..-0.5, bed -10..-4 dB under the lead in the hooks), the voice
  in the band (err quieter: nowhere-to-be's lesson), the bed carved under the words.
- Master: pop window (-11..-8 LUFS, aim ~-10), true peak <= -1 dBTP, LRA 4-8 LU, platform `auto`.
- Credits: TIGER (CC BY-NC-ND 4.0 + Commons Clause: non-commercial), Hanami (Team L❤VE licence, credit Lotte V;
  vocoder CC BY-NC-SA: non-commercial), SampleRadar 80s pop drums (no redistribution), hyperreal LinnDrum (unclear),
  Salamander (CC-BY Alexander Holm), GeneralUser GS. Private listening: fine; publishing: non-commercial only.

## Log

- producer: brief written (118 BPM C minor / Eb chorus / +2 last choruses, retrowave preset as the 80s pop band +
  strings, marimba, orchestra hits; TIGER cool and dry, Hanami "ahs"; the riff on the glass piano).
- arranger / lyricist: ARRANGEMENT.md, LYRICS.md, the first song.py (116 bars, the riff, TIGER's lines, Hanami's ahs).
- sound designer: SOUND.md - the riff's compressor opened, e-piano / brass velocity response, bass free-running (masked
  clicks 11 -> 2), the vocal clean and dry (throws -15 dB: returns 15.8 LU under the voice), the bed placed wide.
  flat_dynamics 0 (brass 1.4 -> 7.1 dB, orch 2.5 -> 3.7 dB).
- mix engineer: MIX.md - voice -2, kit +2, bed -3, the kit carved under the words; `mix`: 0 findings; space lush.
- mastering engineer: MASTER.md - limiter +2.8 dB: -10.8 LUFS-I, -1.07 dBTP, LRA 4.1 LU; `master --check` clean.
- A&R round 1: `ship` with 8 minors. Fixed: the ending (the riff's last answer climbs to D6 over D minor, a bass
  tonic under the last hit), the pres a step under the choruses, air after "sky" and "Sunday" (every line its own
  breath), "so we do" -> "then we do what we're told", hats up, the notes corrected. Kept: verse 1's talky opening
  bar, the narrow verses (the dry, centred verse against the wide chorus is the idiom), the kick / bass overlap.
- merge of master (singer expression): back-phrasing / ornaments / messa OFF, the `*word*` / `(( line ))` markup used;
  diction re-checked: no coda warnings.
- A&R round 2: `ship`, 8 minors (AR.md). Polished after it, verified with the build / `mix` / `master --check`
  (no third A&R round): `mic_pull=False` on the lead (the library's pull-back faded every verse line end 10-16 dB
  under the band: not deadpan, and a risk for the final consonants), the last chord rung out (the riff's D6 on beat 2
  with the pedal down, the bass tonic a half note: 4:00.9), the bass -2.5 dB under the bridge's aside, the lean on
  `*cheap*` dropped (it did nothing). Open, accepted: choruses 1-4 within 0.3 LU (the key change, Hanami and the
  marimba carry the climax), LRA 4.1 LU, air -2..-3 dB in the choruses, the narrow dry verses, 2 masked bass clicks.
- final build: 4:00.9, -10.9 LUFS-I, -1.10 dBTP, LRA 4.1 LU, space lush, 0 clicks in the mix, flat_dynamics 0,
  0 silent notes, no diction warnings, `mix` 0 findings, `master --check` all ok.
