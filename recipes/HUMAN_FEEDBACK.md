# Human feedback (read before every song)

- 2026-10-27, "Gold über den Wolken" (an Endless orchestra adaptation with gritty Hero Sax):
  "ziemlich cool"; user asks to integrate this as an occasional guest in Endless.
  Reuse suitable orchestral themes, give the sax room and preserve orchestral interludes.

What the user said after listening, and the rule it implies. The recipes and analysis profiles cannot hear these
things; the user can. Every entry is a mistake a song has already made: do not make it again. Newest first.
Add new feedback here (date, song, the user's words, the rule) whenever the user reacts to a render.

## Style / feel

- **2026-09-30, lamplight-avenue (soft-rock sax homage):** "der Song ist jedenfalls schon mal nicht schlecht" -
  what worked: one recurring hook (two rising 8ths leaping to a held peak) that opens the song, returns between
  sections, is harmonized a third below in the choruses and climbs higher in the last one; a guitar solo that
  trades with the sax motif; clear form with a long sax fade. Only the sax sound lacked "epic / present" (see
  Sound quality / hero sax).
- **2026-09-30, jazz reference:** "Beegie Adair does it all right". The user's model for piano jazz: Beegie Adair's
  trio - elegant, lyrical, polished piano-trio jazz on standards / ballads: the melody always clear and singable,
  rich but warm voicings, tasteful fills and runs (never busy), gentle, relaxed time, a soft round piano sound,
  unobtrusive bass and brushes, romantic endings. Rule: aim jazz piano pieces at that - melody first, polish over
  virtuosity. For numbers, a reference track in assets/refrences/ + `agentsound compare` (analysis only).
- **2026-09-30, next jazz wish:** "New York Bar Jazz, aber ohne Swing ;D".
  Rule: jazz for this user = piano-led New York bar jazz with STRAIGHT (even) 8ths, no swing ratio. Keep the jazz
  harmony, voicings and piano technique; drop the swing feel.
- **2026-09-30, lanterns-on-carmine (medium-swing tenor quartet):** "das Sax bzw. Trompete klingt irgendwie
  leiernd" - then: "das Leiernde ist eher auf die Komposition bezogen, nicht das Instrument selber", "vielleicht ist
  das auch das Swingige, und das gefällt mir dann nicht so", "dann liegt's am Jazz-Typ".
  Measured first: the MTG tenor itself is steady (plain notes hold within +-2-5 ct, std-dev 1.5 ct over the first
  300 ms; vibrato only on long notes, about +-4-10 ct; the raw samples drift 2.5-6 ct; the microshift double changes
  nothing measurable) - no instrument defect. What the user dislikes is the style: a lazy medium-swing feel with
  meandering, laid-back, bendy horn lines.
  Rule: for this user prefer straighter, tighter feels - straight 8ths, bossa, a ballad in even 8ths, or a light
  swing (ratio 0.55-0.58 at most, `jazz.Feel(ratio=...)`, `horn_line(ratio=...)`). Give phrases a clear shape and
  rhythmic drive (motifs, repetition, answers on the beat) instead of long wandering bebop lines. Fewer pitch
  gestures on horns: `horn_line(scoop<=0.15, fall<=0.1, glide=0)`, a small lay-back (`late_ms` ~5-10), vibrato only
  on the last long note of a phrase. The original wish was "New York bar jazz: piano, soft drums and bass" - make
  jazz piano-led (trio first; a horn only when asked for).

## Playing technique

- **2026-09-30, lamplight-avenue (the hero sax vs Baker Street):** "da spielt er eine Note und pustet mal kurz mehr,
  mal kurz weniger – versteht was ich meine?", then: "ich denke, die bewegen das Sax gezielt und gewollt relativ zum
  Mikrofon". Measured in the record (the riff's held notes, the harmonics of the tracked sax): the level moves 3.7-7
  dB inside a held note (p5-p95, 90 ms smoothed; median ~4.5), 1-3 breath bumps of 2-4 dB lasting 100-170 ms, vibrato
  +-20-30 ct at 5.4-5.5 Hz on the held peaks, and the brightness moves 4-12 dB within a note only loosely with the
  level (the bell against the mic, not just the air). Ours before: the hero compressor held every note at one level
  (2.4 dB of movement on the hook peaks, the sample's own) and flattened the velocities (0.35 dB per 10 steps after
  the chain, 1.2 before it).
  Rule: held wind notes breathe. Every sax / brass / woodwind lead (bowed strings: bow pressure) goes through
  `hornist.arrange(...).place(track, sec)`: air pushes on the beat or a syncopation, pulses over long notes, swells /
  blooms / fp / tapers, breath releases - frequent but not on every note, the hook peaks the most (`peaks=`,
  `section=`); vibrato mostly on the held peaks, deepening with the air; shakes / growls rare (one per 24-32 bars, the
  climax); mic moves (lean in on the hook peaks, turn away / fade away on soft endings, a bell swing in a long note).
  On a compressed (hero) chain the air goes AFTER the compressor (the 'air' breath stage, `fx.air.gain`), with the
  phrase accents, or the compressor erases it. lamplight-avenue after (sax stem vs the same song without the player):
  the hook peaks move 2.4 -> 3.8 dB inside the note (Baker Street 3.7-4.7), all held notes >= 1.25 s 2.9 -> 3.6 dB,
  pushes +2.6 dB, swells +2.7 dB, lean_in +4.9 dB (and +0.5 dB 3-8 kHz share), fade_away 2.1 dB darker, vibrato 24 ct
  at 5.5 Hz on the peaks; sax level unchanged (-17.1 LUFS), note dynamics 3.9 dB (automated), 0 warnings, 0 clicks.
- **2026-09-30, perry-street-rain v3 (after "WOW"):** "nice nice ... etwas zu viele von diesen schnellen
  Zwei-Tasten-Wechseln ... sonst cool" (the arranger had played 14 trills / tremolos / shakes / repeated notes /
  alternating-hands breaks in 84 bars, ~1 every 6 bars, plus the intro trill).
  Rule: fast two-key alternations are spice, not a habit - budget them. `pianist.arrange` does (`fast_every`: about
  one per 16 bars per style, ballad 10-12, sparse none; never in neighbouring phrases; never two of a kind within 32
  bars; only at structural moments - the last long note of a section, a phrase end, the top of the line, the climax,
  the final chord), the other ornaments (turn, mordent, crush, slip, roll) share a larger budget (`spice_every`
  1.5-3 bars). Share one `pianist.Memory()` across a song's arrange() calls (`memory=, at=`), book hand-placed
  set pieces (`mem.played(at, 'trill')`) and save the big figure for the climax (`mem.save(at)`). Ornaments are
  played light and legato: the figure 25-40 velocity under its principal note, swelling in and fading, the pedal
  down, a soft landing ("man könnte es etwas smoother machen"). v4: 3 fast figures from the arranger + the intro
  trill.
- **2026-09-30, perry-street-rain v3 (played by `pianist.arrange`):** "WOW!!!" - the benchmark for piano parts.
  What made it: a harmonized melody (83-95 % of melody notes voiced: sixths, drop-2, quartal, octaves), LH shells /
  rootless voicings, one ornament per phrase (trill, tremolo, blues crush, turn, shake, slip note), runs / sweeps /
  a gliss in the gaps, two-handed climax, straight 8ths, `touch()` phrase velocities (8 dB dynamics per phrase).
  Rule: every piano part goes through `pianist.arrange` (or its moves) - never a bare line.
- **2026-09-30, perry-street-rain (straight-8th piano trio):** "es ist, als würde ein Kind Taste für Taste drücken
  beim Lead – zu simpel", then: "es gibt doch da so schöne Moves, z. B. wo zwei Tasten sehr schnell abgewechselt
  werden usw." (the sound and the new dynamics were liked).
  Rule: a piano lead is never a bare single-note line. A pianist harmonizes the melody (guide tones, 3rds / 6ths
  under a moving line, close / drop-2 / quartal voicings, upper structures, octaves with an inner tone, locked
  hands for the climax - the melody always on top, above C4 when the left hand plays), decorates the long notes
  (trill, tremolo, turn, mordent, crushed / blues-crushed grace notes, slip notes, re-struck voicings, rolls),
  fills the gaps (runs, arpeggio sweeps, cascading 4ths, answers, stabs, alternating-hands breaks, a glissando into
  the next section) and gives it rhythmic life (anticipations, delayed entrances) - mixed phrase by phrase, a move
  per phrase or so, not everywhere. Use `pianist.arrange(melody, prog, bpm=..., key=..., style=..., density=...,
  lh=...)` (= `jazz.pianist`) for every piano melody and solo, and the named moves (`pianist.trill`, `.tremolo`,
  `.gliss`, `.shake`, `.alternating_hands` ...) for set pieces; one pianist = two hands: its `.lh` replaces a
  separate comping part.
- **2026-09-30, lanterns-on-carmine:** "Piano ganz gut" - keep doing what worked: comping chords rolled 8-22 ms
  (25-75 ms in intro / tag / the final chord, `clip.strum`), crushed grace notes before long solo notes, drop-2 /
  locked-hands block chords (`jazz.block_chords`) and octaves for the climax, answers in the horn's gaps, pedal
  steps with the harmony, a rolled final chord held in the pedal.
- **2026-09-30, jazz:** "bei Jazz ist auch die Technik wichtig, gerollte Akkorde usw."
  Rule: a jazz part is performed, not quantised block chords. Piano: roll (arpeggiate) chords, especially ballad
  and intro/ending chords and big left-hand voicings (`clip.strum(ms=25-60, 'up')`, vary the speed). Use grace notes
  and crushed notes into melody tones, turns and enclosures, octave melodies and block chords (`jazz.block_chords`)
  for climaxes, tremolos and fills in the gaps of the head, pedal steps, a left hand that anticipates the beat,
  and a real ending (a rolled final chord, a ritardando, `tempo.fermata`). Sax: scoops, falls, ghosted notes, breath
  gaps and vibrato on long notes (`jazz.horn_line`, `scoop`, `fall`). Bass: chromatic approaches, ghost notes,
  slides, and a fill into each chorus. Drums: ride variation, comping snare and kick ("bombs"), and brush sweeps.
  The same technique thinking applies to every genre: guitar strums and bends, string bowing, drum ghost notes.
- **2026-09-30, polaroid-summer:** "sind alle Lead-Noten gleich laut?" (the melody was written at velocities 81-103
  through a patch with velocity sensitivity 0.3: ~0.5 dB from note to note, robotic).
  Rule: every melodic line needs real dynamics - velocity arcs over each phrase in 55-118, accents on the phrase
  peaks and strong beats, softer passing and repeated notes, octave doubles softer than the line, sounds that
  respond to velocity (`amp.velocity` >= 0.7 on va, `velsens` >= 0.8 on dx7 / sf2 / sampler) and compression that
  keeps the note-to-note differences. The report's `flat_dynamics` warning must be 0 (see `nodes[].dynamics`
  and the "note dynamics" lines of the build summary).

## Melody / lead sound

- **2026-09-30, children-of-neon (layered hook `piano_glass_lead`):** "der Lead ist jetzt zu leise". The layered hook
  measured the same LUFS as the plain piano, but the pad/glass layers soften the attack and the bed sat only 0.4 dB
  under it. Rule: the hook must read clearly in front - bed (pads/choir/strings) >= 2-3 dB under the lead in its
  sections (report: `bed ... vs lead`); get there by carving (sidechain the bed to the lead ~2-3 dB, a presence dip
  on the lead where it masks the drums) before pushing the lead into the mid/presence limits. Re-check the lead level
  whenever its sound changes (layers, patch swaps).
- **2026-09-30, children-of-neon (after the piano + dynamics pass):** "ein guter Fortschritt, keine
  on-the-nose Probleme". What worked (keep doing it): the hook on the high melody piano (sampled/piano_lead, C5-D#7,
  octave-doubled at ~70 %, re-struck notes instead of long holds, pedal steps, pickups into the drops), the supersaw
  only as a bed ~10 dB under it, and real dynamics: downbeat accents, softer 8th passing notes (x0.86) and grace
  notes (x0.7), 4-bar phrase arches, a section arc (first statement soft, drops louder, the lift strongest),
  velocities 44-116, a compressor loose enough (2:1) that attacks still differ ~8-16 dB.
- **2026-09-29, the synthwave songs:** "die Lieder scheinen oft als Melodie-Main-Synth etwas Piepsiges zu haben" /
  "das klingt bissel lahm, lieber eine hohe Piano-Taste oder so".
  Rule: no thin, beepy synth as the main hook (triangle/sine "soft lead", high supersaw lines in A4-A6 without
  body). Put the hook on a bright, high, real sampled piano (octave-doubled right hand, C5-C7; bands:
  `lead='piano'`, patch `sampled/piano_lead`), or on a lead with real weight and character (brass lead, sax,
  guitar, a fat lower-register synth doubled an octave down). If a synth lead stays, it needs body below 1 kHz,
  movement (vibrato, glide, filter) and a doubling layer. A melody that only "beeps" is a failed song.

## Sound quality / production

- **2026-09-30, lamplight-avenue (Baker-Street-style soft rock, Weresax alto hook):** "bei Baker Street klingt das
  Sax irgendwie epischer und präsenter?!?"
  Measured (sax stem vs the rest of the band, K-weighted, pre-master): the sax sat 0-2 dB UNDER the band in the riffs
  and choruses, the bed's 1-4 kHz only 2.4-5 dB under the sax in the choruses (report bed vs lead -3.6..-4.8), the
  song's own sax EQ cut its presence (-2.5 dB at 3.2 kHz; 1.5-5 kHz share -5.8 dB, 400-800 Hz honk -1.9 dB = 65 % of
  its energy), a light 2.5:1 compressor (50 ms level spread 7-8.5 dB), one mono take with a microshift, the plate of
  the band. Against the record's riff (`compare`, loudness-matched): -2.2 dB at 1.6-4 kHz, -3.3 dB at 1-1.6 kHz, +3.7 dB
  at 500-800 Hz.
  Rule: a hook instrument that has to sound epic is a HERO lead, produced like one - `layered/hero_sax`
  (`agentsound/patches/hero.py`, values in `HERO_SAX`): close-miked and bright (the Weresax dynamic mic, honk out at
  650 Hz / 1.3 kHz, bite at 3 kHz, air at 8 kHz), 6-9 dB of compression with a 25 ms attack (level nearly constant,
  the accents still pass), tube grit, double-tracked by other takes ~10 dB under it (width without phasing), its own
  big pre-delayed bright plate (`bus/hero_plate`), echo THROWS at the phrase ends (`articulation.throws`), wide vibrato
  on the held peaks, confident velocities 78-126 that still arc per phrase. Mix: the lead 1-2 dB OVER the whole band
  (pre-master) in the hook sections and ridden 2-4 dB up from the verses, the bed 6-8 dB under it (report: bed vs lead),
  the bed's presence band carved while it plays (`song.carve(strings, pad, piano, keys, key=sax, depth=4)`: a keyed
  dynamic EQ), the drums' crack 2 dB. lamplight-avenue, hook sections before -> after: sax vs band -2.0..0.0 ->
  +0.8..+1.7 dB, bed vs lead -3.6..-5.4 -> -5.3..-8.3 dB, the bed's 1-4 kHz under the sax 2.4-15 -> 9-20 dB, 50 ms
  level spread 6.4-8.5 -> 3.7-4.5 dB; vs the record (riff) 1.6-4 kHz -2.2 -> -0.8 dB, 1-1.6 kHz -3.3 -> -1.9 dB,
  500-800 Hz +3.7 -> +2.5 dB; 0 warnings, 0 clicks, sax note dynamics 3.8 dB per phrase.
- **2026-09-30, perry-street-rain v3:** "man könnte es etwas smoother machen, es klingt hart" - then: "das ist, denke
  ich, eine Sound-Design-Frage, nicht so sehr Structure".
  Measured: the Salamander's (close-miked) velocity layers get much brighter than they get louder - from velocity 64
  to 127 the 2-5 kHz share rises ~12 dB and the 5-12 kHz share ~20 dB, the level only ~6-10 dB - and the chain
  added presence on top (+1.5 dB at 3 kHz in the jazz preset, the song's +2.5 dB shelf at 4.2 kHz): loud notes turned
  glassy and percussive, the master limiter grabbed their attacks.
  Rule: a sampled acoustic piano is voiced warm - the loud layers must bloom, not bite. Use `sampled/jazz_grand` (the
  Salamander with softened hammers: `inst.sfz(..., hammers=0.5-0.8)`, a velocity -> brightness curve), no presence
  boost at 2-5 kHz (air above 10 kHz instead), the loud attacks rounded on the piano track (a fast, soft-knee
  compressor that only reaches the loudest hits, a touch of tape), the piano a little further back in the room. The
  jazz presets (`bands.make('jazz_trio' ...)`) do it. Keep the note dynamics (piano dynamics >= 6-8 dB) and the
  clarity: smooth is not flat and not dull. Check the piano stem: presence share and spectral centroid of the loud
  hits, onset crest, and LOOK at a spectrogram zoom of the loudest hits (v4: loud-hit centroid 1172 -> 1042 Hz,
  their 2-5 kHz share -2.6 dB, onset crest -0.7 dB, piano dynamics 7.8 dB).
- **2026-09 (first engine), polaroid-summer / midnight-interstate:** "klingt schön, aber auch bissel blass/dünn,
  8-bit, als käme es von einem Gameboy und nicht von übelst geilen Reverbs und Effekten".
  Rule: no bare oscillators. Every part gets its production: detune/unison or doubling, chorus, saturation, real
  reverbs (the 224XL IR halls/plates), echoes, width, a full low end (sub + low mids). Check against a reference with
  `python -m agentsound compare`: the first drafts were +7.5 dB too bright and -9 dB short on sub, and only half as
  wide as the reference.
- **First song ever:** "it sounds rather simplistic". Rule: compose deliberately, with a real form, tension and
  release, a memorable hook, variation between repeats, fills and transitions, and counter-lines. A loop with a
  melody on top is not a song.

## Instruments

- **2026-10-11, acoustic guitar demos (`songs/_demo_acoustic`: `sampled/acoustic_guitar` + guitarist `hand=`
  'songwriter' / 'fingerstyle'):** "sounded nice". Rule: for acoustic guitar parts use that patch and those hands
  (fingerpicked travis / arpeggio verses, songwriter strum with chucks) - first used in die-faehre-um-sieben.

- **2026-09-30, lanterns-on-carmine:** "Drums etwas zu laut". The brushes sat 10.8-13 dB (RMS) under the lead
  per section, but taps, digs and kick bombs are transient (crest ~29 dB): their peaks reached the sax's and piano's.
  Rule: in acoustic jazz the drums sit clearly behind the piano and the horn, like a club trio record - brushes
  13-16 dB (RMS) under the lead in every section and their peaks well below the lead's; judge it per section in
  `tracks.png`, not by integrated LUFS. The jazz presets carry it (`bandlib.jazz.DRUM_TRIM` = -3 dB); drummer
  "bombs" and ride choruses stay soft (velocity 45-60).
- **2026-09, realism:** "möglichst realistische, nicht keyboard-artige Instrumente".
  Rule: sampled acoustic instruments must sound played, not keyboard-triggered. Use velocity variation, round
  robins, legato and portamento for mono instruments, the articulations (keyswitches, scoops, falls), live dynamics
  (the `dynamics` crossfade), and expression and pedal automation, and write idiomatic lines for the instrument (the
  range, breathing gaps for winds, bowing phrases for strings). Prefer a sampled instrument over a GM or synth
  imitation whenever the pack is installed.
- **2026-10-01, kestrel-bay (the first guitar-solo showcase):** "die Technik ist bestimmt toll, aber die Gitarre klingt
  einfach lahm". Every fretwork technique was in and measured (bends, up-vibrato, pinch, feedback), the mids matched
  Baker Street within 2 dB - and it still sounded lame. Rule: technique and spectrum numbers do not make a guitar
  hero; the TONE must be exciting first (saturated, singing sustain, attitude, presence, a real amp-and-cab feel), and
  a lead guitar must be judged against a great rock/guitar-solo recording, not a sax-era mono rip. Never ship a lead
  guitar whose tone has not been A/B'd against a real guitar-solo reference.
  Fixed by the `amp` effect (cascaded tube preamp, tone stack, power amp with sag) and the neck-pickup-voiced
  `layered/hero_guitar_heavy` v2 (songs/kestrel-bay/TONE.md: odd harmonics leading, body and bite restored, the lead
  1-2 dB over the band in solos): "ja genau jetzt its cool". That A/B (old vs new, same 18 s, level-matched) is how
  a tone change is presented to the user.

- **2026-10-01, the-drummer-speaks rock pass (A/B: tube amp for all guitars, palm mute, double-tracking, SVT bass,
  kit calibration, drum bus):** "kann keine großen Unterschiede erkennen, mag sie alle". Measured improvements
  of 1-3 dB in band balance and punch are below what the user notices on a phone. Rule: the user hears big things
  (a lame vs singing lead tone, a beepy lead, robotic phrasing, missing consonants) - spend effort there; fine mix
  polish is fine to do but not worth long A/B rounds with the user.

## Vocals

- **2026-10-01, _demo_vocal (first sung vocals, Hanami + TIGER via DiffSinger + the singer player):** "die Stimmen
  klingen super". The timbre and the singer moves work. ("kann die Konsonanten nicht erkennen" only meant the user
  did not know the words.) Rule: always send the lyrics as text along with a sung song.
- **2026-10-01, _demo_vocal:** "out verliert sein t" - the final /t/ of "out" (a two-note melisma "out -" at a phrase
  end before a breath) is not heard. Rule: word-final consonants (t, d, k, p, s ...) must be sung and audible, also
  after a melisma and at a phrase end - placed at the END of the word's last note, before the breath, never dropped
  or swallowed by the release / de-esser.

- **2026-10-02, jane-street-bossa singer-expression A/B (back-phrasing, ornaments on repeats, messa di voce, word
  emphasis / intimate lines):** "ja, alle vier zusammen - das ist deutlich menschlicher geworden, super". Keep all
  four on for jazz / ballad vocals (ornaments sparse, more toward the end); they are what makes the voice human.
- **2026-10-02, nowhere-to-be, mic pull-back on long held words** (the user's own idea: "das Mikro langsam immer
  weiter wegnehmen"): "ja schoen, das hat sich gelohnt". Keep `mic_pull` on for jazz/ballad vocals; real singer /
  mic technique moves are worth building.
- **2026-10-02, nowhere-to-be (smooth jazz, Hanami):** "die Stimme im Vergleich zum Rest zu laut" and "was ist das
  fuer ein merkwuerdiges Lead-Instrument?" - the tenor sax went through hero(family='sax'), which added a 'shift'
  micro-pitch double (a chorused, synthetic sheen) and an octave layer. Rules: a sung lead sits IN the band, not on
  top of it (check the vocal vs band balance by ear-level numbers; err quieter); a solo horn in jazz/ballads is one
  natural instrument - hero(..., double=False, octave=False) - no doublers on acoustic solo instruments.
- **2026-10-02, nowhere-to-be:** "sie singt manchmal lange gehaltene Worte - da dann das Mikro quasi langsam immer
  weiter wegnehmen, damit es leiser wird". Rule: a long held word does not stay at full level - the singer slowly
  pulls back from the mic after the onset (a few dB quieter by its end, less proximity bass, a touch more room) and
  leans back in for the final consonant. The singer does it by default in jazz / ballad (`mic_pull`, singer.MIC_PULL).
- **2026-10-01, jane-street-bossa:** "im Jazz-Song ist die Stimme viel zu aufgeregt, sollte ruhiger sein". Rule: jazz
  and ballad vocals are calm and intimate - soft voice mode as the base, few and small scoops into notes, slow
  shallow vibrato only on long notes, no falls/doits, small dynamic swings, smooth legato, relaxed timing.
  Round 2 (after fewer scoops / less wobble / 64 % soft mode): "immer noch sehr aufgeregt, vielleicht leiser singen
  lassen und dann nachträglich lauter machen?" - the calm must come from the DELIVERY: let the voice sing softly
  (softest mode / energy) and restore the level with gain; also consider register (lower key) and a stepwise melody.
  And: "sie klingt gerusht" - jazz vocals lay BACK (vowels on or slightly behind the beat, breathing space between
  phrases, not crammed syllables); never push ahead of the band.
  Verdict on the calm A/B (a-f): the user chose f = sung soft + a minor third lower + stepwise A melody + laid back
  + FEWER syllables / longer notes in the A section, and asked for the whole song 20 % slower (126 -> ~101 BPM).
  For calm jazz vocals: lower register, sparse lyrics, laid-back timing and a relaxed tempo matter more than fx.
- **2026-10-01, jane-street-bossa / grit tests:** "der Gesang hat immer viel Hall und/oder Reverb, er klingt nicht
  trocken". The vocal hero chain (plate -12 dB + a constant echo send -20 dB + throws, plus the song's halls) made
  every sung vocal wet; the user wants it drier - and a wet voice also makes grit/distortion sound mushy. Rule:
  sung vocals sit dry and close by default (short plate with pre-delay well under the voice, no constant echo -
  echo only as deliberate throws), drier still for jazz/ballads; judge the wet/dry balance on every sung song.
  (Done in the library, fix/dry-vocals: the vocal hero's own short plate 15-20 LU under the voice by genre, no constant
  echo, `python songs/_demo_vocal/wetness.py songs/<slug>` measures it.)
- **2026-10-01, jane-street-bossa:** "im Jazz-Song ist die Stimme viel zu aufgeregt, sollte ruhiger sein". The ballad
  style with overrides still scooped into half of the openers (median -82 ct: mostly the voicebank pitch model's own
  approach), wobbled +-21 ct on held notes and blended the power mode in. Rule: a jazz / ballad vocal sings calm and
  intimate - the soft mode as the base, power only on rare peaks, few small scoops, a slow, narrow, late vibrato on
  long notes only, no falls / doits, small dynamic swings, smooth legato, relaxed timing (singer style `jazz` /
  `ballad`); and check whether the melody itself is busy (leaps, high notes).
- **2026-10-01, jane-street-bossa (after the calm style):** "die Jazz-Stimme ist immer noch sehr aufgeregt, vielleicht
  leiser singen lassen und dann nachtraeglich lauter machen?" and "ja stimmt, sie klingt gerusht". Measured: the
  syllables were heard ~20 ms AHEAD of the beat (vowels only 15 ms late behind ~70 ms of consonants), a third of the
  sung time at / above D5, 11 leaps of a 4th+ per chorus, 62 % of the syllable steps eighths at 126 BPM. Rule: a calm
  vocal lays back (vowels 30-40 ms behind the beat, phrase starts ~50 ms: the syllable lands on the beat), sings in a
  comfortable middle register (key it so little sits above ~D5 for Hanami), moves mostly stepwise, sings soft (the
  soft mode alone, the level by make-up gain) and does not cram eighth-note syllables (fewer words on longer notes).
  Singer styles `jazz` / `ballad` sing soft and laid back by default; songs/jane-street-bossa/calm_ab.py has the A/B.
- **2026-10-01, _demo_vocal grit A/B (the voice through the guitar amp: light parallel, crunch, megaphone; Hanami and
  TIGER):** "keine der Stimmverrauhungen gefiel mir". Rule: no amp grit / distortion / megaphone on sung vocals by
  default; keep the voice clean (the `vocal` hero chain). Rougher rock vocals would have to come from the singing
  itself (a voice/mode with real rasp), not from distorting a clean take. Caveat (user: "vielleicht lag's am soften
  Drumherum-Sound"): it was only heard over the soft pop demo band - grit may fit a real rock backing; re-test it
  there before ruling it out for rock. Re-test over the rock band with the dry vocal chain (TIGER clean vs crunch):
  "kein großer Unterschied, beides ok". So: grit stays an OPTION (off by default), acceptable on rock vocals,
  never on soft/pop/jazz backings.
- **2026-10-01, lyrics (the user's tips before the first sung song):** "LLMs schreiben gern zu sehr on the nose,
  dabei sollte das Thema eher umgarnt als genannt werden. Ein paar catchy Phrasen sind wichtig wie 'I crashed my
  car against the bridge, I don't care'". Rule: show the theme through concrete images and actions, never name the
  emotion or topic; give every song 2-3 short, punchy, quotable lines with attitude (original - the quoted line only
  shows the tone). Not a 100 % rule ("manchmal muss man auch etwas direkter sein, aber halt nicht immer"): mostly
  circled, a few deliberate direct lines. roles/lyricist.md carries it.

- **2026-10-09, processed-voice FX demo (hard/soft auto-tune, choir-of-one, prismizer, talk box):** "cool voice
  stuff, mir fällts leider schwer die qualität ein zu schätzen. aber es verändert es und hat sicher kreative nutzen,
  gerade die guitarre lol". Rule: the effects are creative tools, not a default; the talk-box guitar was the favourite.
  The user cannot grade effect quality from an A/B alone, so judge it in a real song context (e.g. EDM / funk) and
  use the measurements (tune step, prism level match, talk-box vowel correlation) as the quality gate.

- **2026-10-09, when-the-year-turns-gold:** "bei dem song sänger 15% leiser bitte" - even after the mix engineer's
  -1.5 dB the voice was still too loud (second time after nowhere-to-be). Rule: in vocal jazz / ballads the voice sits
  INSIDE the band; start the vocal ~3 dB lower than the mixer's lead target suggests.

- **2026-10-09, endless jazz piano (arc demos + set):** "es klingt ein bischen schrill und hart, hätte es gerne etwas
  smoother, nicht von den noten her sondern vom sound". Rule: the solo jazz piano sound must be warm and smooth: no
  hard 2-5 kHz edge on loud notes / climaxes, a gentle limiter, a softer touch-to-brightness curve, enough room.
  Measured (seed 106, the trio preset without bass / drums): the loud solo frames' 2-5 kHz only 4.9 dB under their
  200-500 Hz (Chopin's Nocturne op. 9/2: 13.3 dB, Satie: 26 dB), presence +4.9 dB vs the 'piano' profile with the
  master eq still lifting 3.8 kHz; the limiter was NOT it (<= 2 dB of gain reduction); the room send was -13 dB all
  song (s.ending's room ramp held its first value from bar 1, the spec's +6 dB never sounded: dry_mix). Fix: the
  `solo_piano` preset (hammers 1.0, a split de-esser at 2.5 kHz as a dynamic presence cut, a 3.3 kHz dip, an air
  shelf, no presence on the master, no wow) and s.ending keeping the track's send: loud solo 2-5 kHz 9.4-11.7 dB
  under the body, presence +1.2..+2.3, air as before, reverb -10.3..-11.1 LU.

- **2026-10-09, endless jazz piano r6 ("A Bridge for Grove", after 5 blind-test rounds at chance level):** "sounds
  like an endless monotone line of notes :/". The notation judges cannot hear this - the agent-written references
  have the same density (8-9 attacks per bar, median gap ~0.1 beat), so the blind test only proves "as good as our
  references", not "good". Rules from earlier rounds made it worse: "never a silent bar", "an empty bar gets a
  pickup", fills/ornaments in every gap. Rule: a jazz pianist BREATHES - real silence between phrases (half a bar to
  two bars), density that rises and falls per phrase and section, sustained notes that ring, register and dynamic
  contrast between phrases; the ear is the final judge, the blind test only a filter.

- **2026-10-09, breath A/B (A Bridge for Grove):** "b sounds better" (the version with real rests, fewer fills,
  per-phrase dynamics). The user: listening to it, they imagine a player gently moving their body while playing, and
  that is easier the better the music is. Rule: playing must suggest a body - phrase arcs like an arm's movement,
  breaths, tempo that slows like a physical motion coming to rest; timing and dynamics follow one gesture per phrase.

- **2026-10-09, letters-to-the-morning (new-age solo piano, "River Flows in You" style):** "new song is nice" - and
  the wish to generalise the endless jazz-piano loop to endless PIANO in general (this style included). Later: "it was
  fantastic ... getting harder to hear it's slop". The reference for solo piano quality: a hand-written singable
  melody with rests at phrase ends, a left hand that changes its figure per section and holds still under the
  melody's breaths, one climax, a dark warm grand (2-5 kHz 10 dB under the body), loudness range ~16 LU.
  The user: "the jazz should be more like that too" - singable heads, a left hand that changes per section and
  rests under the melody's breaths, a much wider dynamic range than the jazz tunes' 6-8 LU, the warm dark grand.

- **2026-10-10, lofi-piano demos:** "das Knistern ist mir 30 % zu laut". Rule: the vinyl crackle is a faint bed,
  barely there - lofi_piano's vinyl fader -5 -> -8 -> -9.5 -> -12.5 dB ("immer noch zu laut, nochmal 15 % weg", "nochmal 30 % weniger") (LOFI['vinyl_gain']) + its pops squashed (LOFI['vinyl_tame']). Lesson: crackle is judged by its PEAKS, not RMS (it read -53 dBFS RMS but peaked as high as the drums) - the analyzer's `spiky_track` now says so and the endless gate rejects it ("der test sollte näher am menschlichen ohr sein").

- **2026-10-10, endless jazz trio:** "endless jazz trio, and with a verry smooth piano, i think the normal ones maybe
  simply to dry" (earlier pianos: "schrill und hart"; the favourite: letters-to-the-morning). Measured on two trio
  tunes: the piano's own tail was the 0.8 s salon at -11.5 plus a plate at -24 (plate return 26 LU under the piano,
  letters-to-the-morning 16 LU; the mix's reverb -16 LU vs letters -11), the club grand (hammers 0.75, +1 dB at
  3.2 kHz, +1.5 dB air) under a master with +1.5 dB presence: 2.5x letters' 2.5-6 kHz share, centroid 822 vs 797 Hz.
  Rule: the trio's piano is solo_piano's grand (hammers 1.0, the split de-esser on loud notes, a 3.3 kHz dip, no
  master presence lift) in a wetter club - every send +1-2.5 dB, the piano on the 1.9 s plate with 28 ms pre-delay
  (high-passed: the upright stays clean): `jazz_trio voicing='smooth'` (jazz.SMOOTH_TRIO), the endless jazz-trio
  default. A dry, close piano reads hard; reverb around the piano is part of "smooth".

## Clicks and parameter changes

- "In msound wurden Parameteränderungen deswegen manchmal über ein paar Millisekunden gestreckt, um Klicks zu vermeiden."
  Rule: automation jumps must be smoothed (the engine does this; do not work around it), and every render's `clicks`
  must be 0 in the mix before delivery. Look at `clicks/click_NN.png`.

## Films

- "From Robot to Rubato" (the 8-minute narrated making-of documentary about the endless jazz piano, chart-and-panel
  scenes, slow measured narration): "stop it pls, its to boring" - "the differences to small, to dry of a thema"
  (the before/after examples sound too alike to a listener; refining a generator is a dry topic). Rule: an explainer film must not be a slideshow of
  charts read aloud - short (2-3 min), the music in front (long listening excerpts, the before/after heard, not
  described), fast cuts, movement on screen every few seconds, one surprising idea per chapter, fewer numbers; only
  before/after pairs whose difference a casual listener hears instantly, and a topic with a story, not a changelog.

- **2026-10-11, physical-model guitar (cx-physguitar demos A_physical_*, Codex):** "its nice to have small samplefree
  sounds, so why not, but for the quality, it sounds simple and empty". Rule: a modelled instrument is not done when the
  measured decay numbers match - judge the fullness of the body / room / attack against the sampled guitar; the sampled
  Shinyguitar + guitarist hand feel (songs/_demo_acoustic) "sounded nice" and stays the default.

- **2026-10-12, learned generator, three top30 samples (new-age 70 / jazz 30, D:/agentsound-learn/renders/cpu-blend):**
  "so nicht sehr abwechslungsreich". All three were gentle / verse / minor at 65-68 BPM with the climax on C6 at ~90 %;
  the one bright sample (morning, flowing, C major, 78) failed the arc gate. Rule: a set of generated pieces is judged
  as a set - spread mood / feel / form / mode / tempo / climax across it (a set-level budget), and never let score
  fine-tuning plus the gate quietly collapse the student onto its safest mode.

- **2026-10-13, orchestral renders with the research-rule orchestra player (docs/ORCHESTRA_RULES.md) + section patches:
  unbowed, lux-perpetua, ashes-and-chandeliers, _bands/symphony_orchestra:** "nice, really nice". Rule: keep the
  ensemble.py rules (section asynchrony, family legato, phrase dynamics, breathing, bow weight, dynamics-coupled vibrato)
  as the orchestral default; the endless orchestra builds on this player.

- **2026-10-15, blueprint-boulevard sax A/B (an added fx.tremolo on the hero alto, solo 10 s clips 5-20 Hz):** the user
  preferred 16 Hz / 25 % and asked for 10 Hz / 25 % autopan - "it sounds more real to me with it". Reading: the sampled
  sax's looped sustain is too static; real reed tone has fast aperiodic amplitude / pitch micro-fluctuation (shimmer,
  jitter, breath turbulence) that a fast tremolo imitates. Rule: give sampled winds a band-limited random (not sine)
  amplitude + pitch micro-modulation as part of the hornist / hero chain, and judge it on the solo stem.
- **2026-10-15, same A/B, round 2:** 10 Hz / 25 % / autopan (stereo 180) is "already quite good". A slow LFO on that
  tremolo's rate and depth (10 +- 3 Hz, 0.25 +- 0.1 at 0.3 Hz, sine vs smooth random, and a stronger one): differences
  "too minimal to decide" - the feature stays, smooth random recommended for winds. The first sampler `flutter`
  (0.5 dB / 2 ct and 1.2 dB / 5 ct) sounded "fuerchterlich, irgendwas schrilles": its modulator noise was only a 2-pole
  band-pass (audio-rate hash in the level / pitch: sidebands between the partials, lifted further by the hero chain's
  exciter) and 5 ct of fast jitter chirps in the treble. Rule: a modulator must be band-limited steeply (fixed: -30
  dB/oct above the band), random pitch jitter stays at 1-2 ct, and any modulation is judged on a bright solo stem.
- **2026-10-15, the recent piano pieces (endless new-age r-sets, learned-student renders schema3):** "they lack a
  blossoming where the tempo gets faster and more happens; they just ripple along; bass and lead always very clearly
  separated; nothing flowing like Für Elise, where it is played across the whole keyboard". Rule: every piano piece
  needs at least one bloom - a section where the motion density rises (8ths -> 16ths / triplets), the tempo pushes
  forward a little and the texture opens up; and flowing textures where one continuous figure travels across the
  registers and passes between the hands (Für Elise A-section arpeggios, broken chords over 2-3 octaves, runs that
  carry into the melody) instead of a fixed bass-low / melody-high split.
- **2026-10-15, body sway A/B (blueprint-boulevard sax stem, 20 s):** of a (discrete mic moves only), b (sway 1), c
  (sway 2), d (sway 1 + mic moves every 2 bars) the user picked d. Rule: wind solos get the continuous body sway by
  default (hornist STYLES sway=1 in hero / pop / ballad / jazz) and a denser mic budget on a featured hero line.
  Comparing our hero alto with a famous late-70s sax record: ours with the 10 Hz autopan tremolo is closer, but "too
  clean" (no breath noise, no grit / saturation, no period production).
- **2026-10-15, sax grit A/B on a famous late-70s line (covers/baker-street, private):** breath noise (Weresax cc122 = 25,
  2-pole 3 kHz low-pass on the noise zone) "much too loud" -> "80 % quieter or so"; of cc122 = 0 / 4 / 8 / 12 on the
  full variant D (dynamic mic cc120 = 127, velocities 95-127, tube saturator drive 7, tape 15 ips drive 6, compressor
  4:1, 3.6 s bright plate, near-mono, two growls on held peaks) the user picked **4**. Rule: a breath-noise layer is a
  trace, felt more than heard.
  Re-sent at breath 4: of a / b / c / d the user picked **d** - "that started the imaginary sax in my head": the
  late-70s rock-sax sound = dynamic mic, hard velocity layer, tube saturation, tape, 4:1 compression, long bright
  plate, near-mono, a few growls on held peaks, plus the 10 Hz autopan tremolo and the trace of breath.
- **2026-10-15, sax grit A/B, variant d at breath 4:** "started the imaginary sax in my head" - and: "nein, das wird
  das standard sax!". Rule: the late-70s record chain (dynamic mic + breath trace, 4:1, tube + tape grit, near-mono,
  the 10 Hz smooth-random autopan, a bright 3.6 s plate, growls on held peaks) IS the hero sax (hero/sax v2) in every
  genre; the clean double-tracked v1 is only an explicit opt-out (`family='sax_clean'`).
- **2026-10-15, realism batch A blind pairs:** pair 1 (nylon solo arpeggio, FreePats one-sample-per-note): the user
  picked X = the synthetic round robins (rrpitch 4, rrtone 1.5, rrattack 0.4, rrlevel 0.8, rrborrow 0.5, restrike 12)
  over the plain patch -> sampled/nylon_guitar v2 carries them. Pairs 2-6 (nylon in a song, pianos, blend) unjudged.
  Pair 5 (concert grand crescendo pp -> ff): the user picked X = the PLAIN patch over layers='blend' 0.4 + veltone
  0.5, then: "just take 5Y, maybe experts hear it" -> sampled/concert_grand v2 carries realism.BLEND anyway (no
  clear preference by ear; it removes the measured 17 dB brightness jump between layers).
- **2026-10-15, the endless new-age 1 h set (songs/_endless_piano/out/na_1h):** "the right hand always feels louder
  than the left" - and: "it shouldn't be like that in general, I think it should be dynamic too". Measured: right
  hand over left hand 4.6-8.1 dB RMS per piece, +4..+9 in nearly every section - a fixed budget (the left hand's
  phrase median at least 6 dB of velocity under the melody's). Rule: the hands' balance is a performance decision
  that moves: a melody ~3-5 dB over its accompaniment on average, the left hand swelling into the melody's held
  notes and rests and receding under a new note, near equal in a flowing build / bloom, both strong at the climax,
  and once or twice a piece a phrase where the left hand leads (romantic `balance=`, perform.BALANCE). Touch
  (velocity), never fader automation.
- **2026-10-15, same set:** "I feel too many very high notes are played." Measured: most pieces' right hand median
  C5-Eb5 with <= 5 % at or above C6, but some sit high throughout (a median of F5, 29 % >= C6, a C7 top) - the
  theme an octave up as the climax, octave-up returns. Rule: the singing register of solo new-age piano is ~C4-C6;
  above C6 is a rare event (the climax's peak, an occasional sparkle), never a whole section; climbing runs turn
  around below ~E6 (plan['ceiling']).
- **2026-10-15, the endless new-age balance set (songs/_endless_piano/out/balance_v1):** "the right hand still plays
  excessively note by note - not very flowing", then sharper: "as if he had only one finger". Measured on the
  renders: the articulation is legato already (dur / IOI median 1.07), but the melody moves at a quarter-note pace
  almost everywhere (~0.9 notes a beat), neighbouring melody notes jump in velocity (median |dvel| 5-7, p90 16-20:
  each note placed on its own), few connecting notes, and 91-96 % of the right hand's onsets are a single note (only
  4-10 % of its notes have inner motion under them). Rule: the melody is ONE dynamic line per phrase (smooth arcs,
  small neighbour steps, jumps only for real accents); connecting passing / neighbour notes between the structural
  notes; the right hand voices its melody with the other fingers - mostly a single line with an occasional dyad in
  an intimate first statement, thirds / sixths and inner motion under held notes in the returns and the chorus,
  chords and octaves at the build / climax (roughly 30-50 % multi-note onsets overall), the top note the melody and
  the loudest, the hand's span within a ninth (plan['texture'], plan['line'], composer.flow_tells).

- 2026-10-16, endless new-age piano after the blind quality loop g3-g14 (judges rate quality vs hidden references, paired A/B since g14): the user says it has become very good ("es ist mittlerweile sehr gut geworden"). Keep what got it there: the theme sung at the climax (D6-F6 peak, cap F6), profiled heads with an answer phrase, varied returns, the climax as the loudest section, a light left hand, no flicks / stabs / holes at phrase ends. Changes to the new-age generator go through a paired blind round before they reach master.

- 2026-10-16, browser/WASM prototype A/B (same endless new-age piece): the Splendid grand (concert_grand, Public Domain) sounds good to great to the user even as the 26 MB Opus and the 10 MB mini cut; the Upright KW (CC0) does not convince. Web / light-weight piano renders: Splendid, never Upright KW as the lead piano.

- 2026-10-16, endless orchestra-film (seeds 93006 / 93018, 60-75 BPM, 'gentle' verses): 'very meditative, hardly anything happens, no da-da-da-daaa of Beethoven, no Moldau source, no life - only shallow'. The new-age plan orchestrated is too static for an orchestra: it needs a short rhythmic motif that drives and is developed (sequence, fragmentation, imitation between sections, the motif in the bass), flowing running figuration that carries the music forward (the Moldau's two flutes), real tempo and energy (allegro sections, not only 60-75 BPM gentle), contrasts (tutti vs solo, loud vs soft, sudden), and development - drama, not a pad with a tune. Original material only (the techniques, never the famous themes).

- 2026-10-16, first orchestra-symphonic piece ('Overture: Golden Mountains', 128 BPM, motto + running figuration + symphonic form, interim render): 'uhhh, so much better already' compared with orchestra-film. Drive, motto and motion are the right direction for the endless orchestra.

- 2026-10-19, neural choir prototype stage 1 (DiffSinger vowel pack, 6 virtual singers per S/A part and 4 per T/B, vs the old sampled choir, the same notes): the own choir "sounds like fewer people". The learned ears rated both about the same (43.0 vs 43.3), but the ear hears a smaller ensemble: a choir needs perceived section size - more singers, wider spread of pitch / timing / formant, room position - before anything else.

- 2026-10-24, endless orchestra-symphonic (live web page / o22 master): "I feel techniques are missing, e.g. plucked strings". Measured on 8 pieces: strings 65 % sustain, 24 % staccato, spiccato 4 %, tremolo 3 %, pizzicato 2 % (almost only basses / cellos), marcato 1 %; never col legno, harmonics, trills, mutes, glissandi, a pizzicato string choir. The orchestra needs its idiomatic colour palette used as musical events (pizzicato passages, tremolo, trills, harp glissandi, brass mutes, woodwind staccato chatter), not only sustain and staccato.

- 2026-10-24, o23 listening set (TECH on: pizzicato choir, harp glissandi, measured tremolo, trills, col legno, muted / stopped brass, woodwind staccato chatter, harmonics, sfz - drawn per piece with set memory): "it definitely sounds more interesting". The playing-technique palette is the right direction for the endless orchestra.

- 2026-10-24, endless orchestra (wish): "I think the choir will help the orchestra to greatness - it gives goosebumps much more surely". A real-sounding big choir (wordless vowels) at the arrivals / climaxes of the symphonic pieces is the next big lever after the playing techniques.

- 2026-10-25, endless orchestra (wish): "what I miss in the orchestra are more exotic instruments like a church organ or an acoustic guitar - that can be beautiful too - and above all increase diversity". The endless orchestra should vary its instrumental colour per piece (organ, classical guitar, harpsichord, celesta, bells), built idiomatically into the piece, with set memory.

- 2026-10-25, 1 h endless orchestra-symphonic on master f1ced2e (D:	mp\orch1h; CHOIR v2 + SOLO + COLOUR + SHAPE3 + TECH2 on): "the ideas of the pieces are good, but the performance is restless in a negative way - sometimes it feels pumping, as if someone is playing with the volume knob". Fast level changes (swells, dynamics lanes, master chain) must stay musical: no audible gain riding.
# 2026-10-28: Endless orchestra mix A/B

User: "neu klingt besser", followed by approval to adopt it in the generator. Matched current-code Wings of the Sea, seed 4242, pass 2: bells -2 dB, horns -1.5 dB, first violins EQ at 3500 Hz / -1.5 dB / Q 0.9. Both phone MP3s approximately -18 LUFS; notes, timing and master identical. Adopt this mix in build_symphony after all voices are created. No blanket solo boost or bass-ducking change was approved or included.
