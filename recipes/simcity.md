# SimCity recipe: city-building jazz (the SimCity 3000 sound)

Bright, optimistic, relaxed instrumental jazz for building a city: the late-90s Maxis sound of Jerry Martin and his
team on SimCity 3000 (1999) and SimCity 3000 Unlimited (2000). Music that plays for hours under a game, is noticed
now and then and liked every time: real players, a clear tune, a groove that never pushes, and nothing that asks for
attention. The example song is `songs/blueprint-boulevard` (original: own hook, changes and title).

Write ORIGINAL music in this idiom. Never copy a melody, a chord sequence, a riff or a title from the game's tracks,
and never put game audio in the repo (`references/` and `assets/refrences/` are for analysis only).

## What the research says (sources at the end)

- **Who**: Jerry Martin joined Maxis in 1996 as studio audio director and lead composer [1][2]; before that he had
  spent 1985-1995 scoring TV commercials (AT&T, Toyota, Honda, the NBA) and is known for jazz [2]. The game credits six
  composers: Kirk Casey, Kent Jolly, Anna Karney, Robi Kauker, Jerry Martin, Marc Russo [1]. Live players are
  named: David Lauser on drums, Darol Anger on violin [1]. Marc Russo is the saxophonist of the Yellowjackets
  (1980s) and the Doobie Brothers (from 1998) [9].
- **What**: a live score of new-age and live jazz pieces, a big change from SimCity 2000's MIDI music [1][7].
  Reviews at the time: "upbeat urban jazz and space-age electronica" that does not wear out over long sessions,
  "bright jazz with festive horns to moody blues", music that sits with the city sounds without drowning them, players
  leaving the game running just to listen [3]. A track-by-track listener review of the Unlimited soundtrack (23 tracks,
  just under two hours): new-age, electronica, jazz and big band, "relentless optimism about urban living"; *Magic
  City* builds to crescendos and falls back into new-age calm, holding repeated single notes that shift together;
  *Sim Broadway* is light and airy with a marimba-like voice, compared to *Rhapsody in Blue* [4]. One listener calls
  *UpDown Town* "90s modern jazz" with a lounge / cocktail-bar feel [8].
- **Track names** (the 10-track soundtrack CD listing as reported by search results of MobyGames; not verified
  against the disc): Sim Broadway, Building, Magic City, New Terrain, Updown Town, Night Life, Power Grid,
  Infrastructure, Concrete Jungle, Illumination [5]. Unlimited also plays "City of Dreams" and the SimCity 2000 theme;
  an unofficial patch restores tracks Unlimited fails to play (Sim Broadway, Concrete Jungle, City of Dreams, the
  SimCity 2000 theme) [6].
- **Why it works** (Martin, about the Maxis scores): the music is "mostly subliminal and unconscious"; jazz carried
  "the busy energy of the city" in SimCity 3000, new-age jazz piano the build modes of The Sims; less structure holds
  up better on endless repeats, and repetition itself makes the music stick; he learned "patternistic minimalism"
  from Terry Riley [2b]. For The Sims' build mode the brief was "happy and innocent and hopeful", the music "very
  relaxing and very contemplative" and explicitly "not like a big build-up to something" [10]; Martin recorded
  improvising players and edited the best bars together (cut-and-paste), so the tracks sound played, not programmed
  [10].
- **Not documented**: tempos and keys of the tracks. The ranges below are this recipe's working choices for the
  style (late-90s contemporary / smooth jazz, lounge, light fusion and new-age piano), not measured values.

## The style in one paragraph

A small studio jazz band playing a clean, sunny tune in a major key with lydian colour: Rhodes and grand piano, a
fingered electric bass, a drummer on sticks keeping it light (hats or ride, side-stick or a soft backbeat), a
saxophone (alto or soprano) carrying the melody, vibes / marimba / percussion for sparkle, a soft pad underneath, horns
only for a festive lift. The hook is singable and short, repeated with small changes; the solos are melodic, not
virtuoso; the energy rises a little and comes back. Clean late-90s digital production: close, polished, a plate
and a short room, gentle chorus on the keys, nothing distorted.

## Tempo, feel, key

| sub-style | tempo | feel | typical keys |
|---|---|---|---|
| urban / lounge jazz (the "city" tracks) | 100-120 BPM | straight 8ths, a light 16th lift on the hats, or a light swing <= 0.56 | C, F, Bb, Eb, G major |
| new-age jazz piano (calm / build) | 66-90 | rubato phrases over a steady pulse, pedalled | C, G, D, F major |
| big-band / Broadway lift (festive) | 120-160 | straight or light swing, horn shout | Bb, Eb, F |
| ambient / electronica (power, night) | 80-100 | pulse, sequenced figures, pads | D / E dorian, minor pentatonic |

User rules apply first: straight or barely swung 8ths (recipes/HUMAN_FEEDBACK.md: "aber ohne Swing", swing <= 0.58),
clear phrase shapes, no wandering bebop.

## Harmony

- Major keys with **lydian colour**: the IV as `maj7#11` (`Fmaj7#11` in C) - a melody note on the #11 over it is
  the signature brightness. Tonic `maj9` / `6/9`.
- **Two-chord modal vamps** for intros, outros and solos: `Imaj9 - IVmaj7#11`, `Imaj9 - bVIImaj9`, `ii9 - V13sus4`.
- **ii-V turnarounds** to close an 8: `iii7 VI9 ii9 V13sus4`, with a `V7b9` or `VI7b9` passing chord.
- **The sunrise lift** for the B / bridge: `bVImaj7#11 - bVIImaj9 - Imaj9` (`Abmaj7#11 Bbmaj9 Cmaj9`), the borrowed
  `iv6` (`Fm6`) for a moment of shade before a turnaround.
- Sus chords (`13sus4`) instead of hard dominants: the music resolves without tension spikes.
- Avoid dark minor-key tension and dramatic modulations; a "moody blues" track is the exception, not the rule.

## Form (3-4 min, loopable)

`intro 8 (vamp) | A 16 (hook) | B 8 (lift) | A' 16 (another voice has the hook) | solo 16 | solo 16 | B 8 | A'' 16
(hook doubled, the second half climbing) | outro 4 + ending 2`. The ending lands on the tonic `maj9` / `6/9` and may
fade back into the intro vamp (game music loops). Energy 1-5: intro 1.5, A 2.5, B 3.5, A' 2.5, solos 3-3.5, B 4,
A'' 4, outro 2: a gentle arc, no drop, no big build-up.

## Instrumentation -> AgentSound

| role | sound | how to play it |
|---|---|---|
| band frame | `bands.make('funk_band', s, without=('gtr',), keys='rhodes', lead='sax')` | the Orange Tree jazz-funk kit on sticks in a short 224XL ambience, the clean Growlybass, Rhodes, VPO trumpet + trombone section, Weresax alto; master: soften it (see Mix) |
| melody / hook | alto sax `sampled/alto_sax` (Weresax, C#3-G#5) through `hero(sax, family='sax', genre='pop', double=False, octave=False)`; soprano: `inst.sfz('samples/mtg-solo-sax/MTG Solo Saxophones/MTG Soprano Sax.sfz')` (D#3-E6) | `hornist.arrange(..., style='pop', peaks=...)` for every line (the air inside held notes); no microshift / octave doubles on the acoustic horn |
| keys | `sampled/rhodes_vibrato` (`sounds={'keys': patches.get('sampled/rhodes_vibrato')}`) or `sampled/rhodes` | `jazz.comp(prog, style='swing' / 'charleston' / 'ballad', voicing='rootless', register=('C3', 'G4'))`, rolled 8-30 ms |
| piano | `sampled/jazz_grand` (warm, softened hammers) | the hook in one A through `pianist.arrange(style='straight')`, the solo via `soloist.solo(..., pianist.vocabulary('straight', lh_track=piano))`; the Rhodes lays out under it |
| bass | the band's fingered bass (Growlybass); fretless colour: `gm/fretless` | `bassist.arrange(prog, style='pop', part=...)`, mid cut at 1 kHz and 3.5 kHz so it does not mask the sax / piano |
| drums | the band's Orange Tree kit | `drummer.arrange(sections, style='pop', density=0.4-0.45, lock=bass, plan={...})`, verse / solo / chorus roles, ride in the piano A and solo |
| sparkle | `sampled/vibraphone` (motor: `fx.tremolo`), `sampled/marimba` (Sim Broadway colour) | the hook's head as an intro hint, the last A doubled an octave up, velocity arcs (`touch`, 44-100) |
| percussion | shaker 16ths on `sampled/busk_kit` key 42 | velocity-shaped (`vel_pattern([1.15, 0.7, 0.9, 0.7])`), 25-30 dB under the lead |
| horns | the band's `horns` role (VPO section) | soft `'long'` swells in the first lift, a few `'accent'` stabs in the last: festive, not a funk band |
| harmony sax | `sampled/tenor_sax` | a diatonic third under the alto in the last lift / A |
| pad | `sampled/soft_poly` | spread chords under the lifts, ducked and carved by the hero |
| strings / violin (optional) | `sampled/solo_violin` (Darol Anger played on the score) | a counter-line in the new-age pieces |

## Mix and master targets

- Analysis profile `pop` with `loudness: [-14.5, -11]` (lighter than radio pop: background music). Aim -12.5..-12
  LUFS integrated, LRA >= 4 LU, true peak <= -1.2 dBTP.
- The funk_band master is a hot funk master: raise its glue threshold (`s.master.fx['compressor'].set(threshold=-11)`)
  and take 4-5 dB off its limiter drive (`mastering.apply(..., loudness_change=-5)`).
- The lead (sax or piano in its solo) 5-8 dB over the drums (node LUFS), the bed (pad, keys) >= 6 dB under it.
- The bass is the mix's mid-band thief: cut it at 1 kHz (-3.5) and 3.5 kHz (-4) and trim it ~3 dB from the preset.
- A grand piano next to a Rhodes: one keyboard comps at a time.
- Vibes samples are wide: `fx.width(width=0.6)` keeps them mono-safe.
- Space: the sax's own hero plate + echo throws, the band's 224XL room and plate; no big hall (90s studio, not a
  concert hall).

## Checklist

- [ ] Original tune, original changes, original title - the style only.
- [ ] Major key, maj7#11 colour, sus dominants, a bVI-bVII lift; no dark drama.
- [ ] A hook that returns (A, A', A''), each time different (another voice, a counter-line, a climb).
- [ ] A solo or two (sax and / or piano) that develops the hook; breathing space.
- [ ] Straight 8ths (or swing <= 0.56), relaxed, steady; no big build-ups.
- [ ] Real played instruments (hornist, pianist, bassist, drummer) - `flat_dynamics` 0, `silent_notes` 0, clicks 0.
- [ ] Ends on the tonic maj9 / 6/9 and could loop back into the intro.

## Sources

1. Wikipedia, *SimCity 3000* (soundtrack section, composers, musicians): https://en.wikipedia.org/wiki/SimCity_3000
2. Wikipedia, *Jerry Martin (composer)*: https://en.wikipedia.org/wiki/Jerry_Martin_(composer)
   2b. Mills College Quarterly, "Soundtracking one of the most enduring computer games":
   https://quarterly.mills.edu/the-sound-of-sims/
3. Jerry Martin Music, "Music and Sound Reviews" (Electric Playground, GA-Source, GamePost, CNN/IDG, Adrenaline Vault on
   SimCity 3000): https://jerrymartinmusic.com/game-reviews/
4. selectbutton.net, "Sim Everything music review" (SimCity 3000 Unlimited soundtrack):
   https://selectbutton.net/t/sim-everything-music-review/14036/33
5. MobyGames, *SimCity 3000* (soundtrack listing, via search result summaries): https://www.mobygames.com/game/69
6. PCGamingWiki community, "SimCity 3000 Unlimited Re-Composed" (unofficial music patch):
   https://community.pcgamingwiki.com/files/file/2415-simcity-3000-unlimited-re-composed/
7. GameStar, SimCity history (via search result summary): https://www.gamestar.de/artikel/simcity-historie-hier-bin-ich-der-buergermeister,3009880,seite4.html
8. musicplayer.com forum thread on Jerry Martin's music (listener comment on *UpDown Town*, via search summary):
   https://forums.musicplayer.com/topic/171190-quotthe-untold-story-of-quotthe-simsquot-new-age-jazz-piano/
9. last.fm, Marc Russo biography: https://last.fm/music/Marc+Russo/+wiki ; Wikipedia, *Yellowjackets (band)*:
   https://en.wikipedia.org/wiki/Yellowjackets_(band)
10. VICE, "The untold story of The Sims, your first favorite jazz record":
    https://vice.com/en/article/the-untold-story-of-the-sims-your-first-favorite-jazz-record
