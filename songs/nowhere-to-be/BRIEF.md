# Nowhere to Be (songs/nowhere-to-be) - brief

## The wish

> "versuch nochmal Smooth Jazz mit Sängerin, ganz smooth"

Another try at SMOOTH jazz with the female voice (Hanami), as smooth as it can get. The idiom: a late-night
smooth / soul-jazz ballad (the intimacy of a Sade or Norah Jones record) - original, nothing lifted. It follows
jane-street-bossa, whose voice the user found "aufgeregt" and "gerusht" until it was sung soft, low, stepwise, sparse,
laid back, slower and dry. This song starts where that one ended and goes further.

## The song

- **Genre / profile**: smooth jazz / soul-jazz ballad with a sung lead, `ANALYSIS = {'profile': 'jazz'}`.
- **Tempo / key / meter / feel**: 72 BPM (jane-street's calm version was 100: another ~28 % slower), Eb major, 4/4,
  STRAIGHT 8ths (Feel ratio 0.5, no swing anywhere), a gentle soul-ballad groove: brush stirs, a feathered kick, a
  soft cross-stick on 4 (2 and 4 in the choruses), no busy fills.
- **The voice**: Hanami (licensed DiffSinger voicebank; female pop soprano, F3-A5) through `agentsound.singer`, style
  `jazz` (sung soft - the soft mode alone, the level by make-up gain -, few small scoops, slow narrow late vibrato,
  no falls, laid back: vowels ~35 ms behind the beat). Register Eb4-C5 (one D5 in the bridge, 1.5 beats): nothing
  long above D5. A stepwise melody (leaps of a third at most, one of a fourth), FEW syllables: 18-20 per 8 bars
  (~27 s), mostly quarter / dotted-quarter / half notes, each 2-bar line followed by 1-2 beats of rest.
  ONE intimate voice; one soft harmony line a third below in the last chorus only. The vocal hero clean and DRY
  (`hero(vox.track, family='vocal', genre='jazz', drive=False)`: its own short plate ~20 LU under the voice, no echo,
  no throws, not in the band's room).
- **Theme / lyrics** (roles/lyricist.md, LYRICS.md): two people with nowhere to be - a late night that turns into a
  slow morning; the clock turned to the wall, the coffee going cold, the phone left to ring out, sunrise asked to
  wait. Circled with images, one direct line in the bridge ("you said slow down, and so I stayed"). Hook = title:
  "Nowhere to be". English, original, sparse, open vowels on the long notes.
- **Length**: ~4:20 (78 bars at 72 + the fermata).
- **Form** (8-bar sections, one chord per bar mostly):
  `intro 4 | verse1 8 | chorus1 8 | inter 4 | verse2 8 | chorus2 8 | solo 16 (sax) | bridge 8 | chorus3 8 | tag 4 | end 2`.
  Energy arc (1-5): intro 1 -> verse 2 -> chorus 3 -> inter 2 -> verse 2.5 -> chorus 3.5 -> solo 3 -> 4 -> bridge 4
  (the D5, the direct line) -> last chorus 4 (harmony, sax answers) -> tag 2 -> the last "be" over Ebmaj9, fermata 1.
  The dynamic range stays small and soft: smooth, not dramatic.
- **The hook**: "No-where to be": a dotted-quarter on the 3rd (G4), two 8ths stepping up and the C5 held across the
  bar line (Ebmaj9 -> Cm9: the 6th becomes the root); the tenor states it in the intro, answers it in the inter,
  builds its solo on it; the tag sings it once more and the last "be" lands on the tonic.
- **Band**: `bands.make('bossa', s, without=('guitar', 'shaker'), sounds={'piano': 'sampled/rhodes'})` - the
  preset's straight feel, the salon IR room (0.8 s, close) + the 224XL plate, the Meatbass upright (long notes, two-feel),
  the Swirly brush kit, the Blonde Bop cross-stick, the MTG tenor - with a warm Rhodes (jRhodes3d) instead of the
  grand for the keys, and a soft analogue pad (`sampled/soft_poly`) far under it in the choruses and the bridge.
  Keys comp AROUND the voice (`jazz.comp(style='ballad', answer=<the vocal line>)`, rolled, below the voice).
- **The horn**: the MTG tenor as a SOFT hero (`hero(family='sax')` without tube / exciter, gentle presence): the hook
  in the intro and the inter, a few short answers in the voice's gaps in chorus2 / chorus3 (calm, `hornist` style
  `ballad`), the solo through `soloist.solo` with the hornist's ballad vocabulary (arc `ballad`: no burst; fast figures
  are spice - one at most).
- **Reference**: none for smooth jazz in `assets/refrences/` - `compare` skipped; the jazz profile, the mixer's jazz
  targets and the preset's measured balance are the targets.

## HUMAN_FEEDBACK checklist (the A&R ticks these)

- [ ] CALM, not "aufgeregt": sung soft (style `jazz`, the soft mode alone), low comfortable register (little or
      nothing above D5), stepwise, few small scoops, no falls.
- [ ] LAID BACK, not "gerusht": vowels on / behind the beat, few syllables on long notes, breathing space, 72 BPM.
- [ ] DRY and close: the voice's returns ~20 LU under it, no echo, no throws (`wetness.py`).
- [ ] Straight 8ths, no swing ratio anywhere ("aber ohne Swing").
- [ ] A song, not a loop: form, the hook returns and grows (sax intro, chorus x3, tag), variation, a real ending.
- [ ] Lead in front: band >= 3-4 dB under the voice in the sung sections; the pad far under it.
- [ ] Real dynamics: `flat_dynamics` 0 (voice, Rhodes, bass, sax).
- [ ] Played, not keyboard-like: rolled Rhodes chords, bass touch, the sax breathing (hornist), brush stirs.
- [ ] Warm, not hard: Rhodes (no bark: velocities under ~95), no presence boost on keys or sax.
- [ ] Jazz drums soft: brushes / cross-stick 13-16 dB under the lead per section.
- [ ] Hero sax present in its solo but smooth (no tube grit, no fast tricks as a habit).
- [ ] No busy fills; ornaments / fast figures budgeted.
- [ ] Diction passes (no `coda_short` / `coda_buried`); lyrics sent as text (lyrics.txt).
- [ ] 0 clicks, 0 clipped samples, true peak <= -1 dBTP, 0 silent notes.

## Targets

- Mix: the jazz mixer profile; lead (voice) on top, bass 3-7 dB under, drums 13-16 dB under, pad >= 6 dB under.
- Master: the jazz profile (-16..-13 LUFS integrated, LRA >= 5 LU, true peak <= -1 dBTP), platform `auto`.
- Credits: Hanami (voicebank: credit Lotte V; its vocoder CC BY-NC-SA 4.0 = non-commercial), jRhodes3d (CC-BY-NC 4.0),
  MTG tenor (CC-BY 4.0), Blonde Bop (CC-BY-SA 3.0), Meatbass / Swirly (CC0), SampleRadar soft poly (check the
  credits warning). Private listening: fine; publishing: non-commercial only.

## Log

- producer: brief written (72 BPM Eb, straight soul-ballad groove, Rhodes + upright + brushes/cross-stick + soft
  tenor + pad, Hanami `jazz`, sparse stepwise melody Eb4-C5).
- lyricist: LYRICS.md / lyrics.txt - hook "Nowhere to be" (turned to "nowhere but you" at the end), 15-20 syllables
  per 8 bars, open vowels on the long notes; `lyrics.check` clean after 5 fixes (coffee stress, ring / city / morning /
  years closed vowels); "and so I stayed" -> "so I stayed" (the legato /d/ of "and" read 35 ms: diction warn).
- arranger: ARRANGEMENT.md - intro 4 | verse 8 | chorus 8 | inter 4 | verse 8 | chorus 8 | solo 16 | bridge 8 |
  chorus 8 | tag 4 | end 2; the voice laid back to late_ms 60 (at 72 BPM the consonants run ~120 ms: the style's 35 ms put
  the P-centre 24 ms ahead of the beat - now +2 ms); the solo: soloist + hornist ballad vocabulary, no fast figure.
- sound designer: SOUND.md - jRhodes3d stereo-vibrato Rhodes in the bossa preset (pan -0.05), the tenor as a soft
  hero (no tube / exciter, 2:1: its note dynamics 3.6 -> 5.4 dB), level trims for the ballad (bass +12, drums +9, rim +11).
- mix engineer: MIX.md - the low group 2.5 dB down, the tenor up where it leads, Rhodes out of 150 / 450 Hz, the voice
  -1.5 dB at 380 Hz; the arc LRA 3.6 -> 5.1; mixer: "moves: none - inside the targets"; open: Rhodes / bass share
  60-250 Hz in the sparse sections (minor).
- mastering engineer: MASTER.md - dynamic, -2.2 dB at 630 Hz, x1.6 width, -15.0 LUFS-I, TP -1.20, LRA 5.1; check all ok.
- a-and-r: round 1 ship (6 minors: solo ST max over chorus3, Rhodes/upright low-mid overlap + low intro tenor, narrow sung sections, verse 2 = verse 1, legato "clock"/"let" codas, pad hall send); round 2 ship - verse 2 / chorus3 lines varied and the intro tenor at pitch fixed, solo peak +0.7 -> +0.3 LU over chorus3, one new minor (intro sax phrase under 4 dB); calm (0.9 % >= D5, 0 leaps), laid back (vowels +61 ms, P-centre +1.8 ms), dry (returns 20.5 LU under). AR.md.
