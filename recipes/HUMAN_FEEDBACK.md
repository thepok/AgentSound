# Human feedback (read before every song)

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

## Clicks and parameter changes

- "In msound wurden Parameteränderungen deswegen manchmal über ein paar Millisekunden gestreckt, um Klicks zu vermeiden."
  Rule: automation jumps must be smoothed (the engine does this; do not work around it), and every render's `clicks`
  must be 0 in the mix before delivery. Look at `clicks/click_NN.png`.
