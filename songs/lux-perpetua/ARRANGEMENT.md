# ARRANGEMENT - Lux Perpetua

The notes live in `score.py`: harmony tables, the tunes, the fugue material, and `satb()`, the SATB voicer. The
performance lives in `song.py`: who doubles whom, articulations, dynamics, tempo.

## How the parts are made

- Four-part choir writing: each movement has a table of (duration, chord, soprano, bass). The soprano and bass are
  written by hand; `satb()` fills alto and tenor with a voice-leading search. The search:
  - keeps chord tones in the SATB ranges (S C4-G5, A G3-C5, T C3-G4, B G2-D4);
  - wants complete chords;
  - never doubles the leading tone or a seventh;
  - forbids parallel fifths and octaves;
  - keeps S-A and A-T within an octave;
  - takes the smallest motion;
  - in the fugue, keeps a free voice a semitone away from a written line.
- A chorale row may fix an inner voice too (`(dur, chord, S, B, {'A': 'D5'})`), where the search's choice made
  parallels with a passing tone of the written soprano.
- The fugue's free voices then move: `arpeggiate()` gives the last beat of a held note to another chord tone that
  approaches the next note, `passing_eighths()` fills thirds and fourths with passing 8ths (local key, leading tone
  into the tonic) - each only where it makes no parallels and rubs no semitone against another voice.
- The soprano sings its own line with passing tones over the structural soprano.
- Checked by scratch scripts (not committed): every strong-beat non-chord tone and every semitone clash, per
  section, and every parallel fifth / octave between any two sung voices (similar motion, 0 after the revision) and
  every violin note of the Lacrimosa against the choir's sounding pitches (0 semitone / minor-ninth rubs). What remains is deliberate: the countersubject's chromatic passing tones (Eb / D over A7, the b5 colour
  of an augmented sixth), the violins' appoggiatura sighs in the Lacrimosa, and passing 8ths.

## Frame and form

Tempo map: 56 (rubato, rit., fermata) -> 88 (rit. to Adagio 48, fermata) -> 144 -> 72 (rubato, fermata) -> 12/8 at
q=72 (rubato, rit., fermata). 79 bars, 4:33 with the tails.

| section | bars | harmony | energy | who plays | what happens |
|---|---|---|---|---|---|
| intro | 6 | Dm A7/C# Dm7/C G/B Gm/Bb (6/4) A, Bb Eø7/G, Eb/G (N6) Dm/A, A7 | 1 -> 2.5 | strings, bassoons, basset horns, timpani | offbeat violin 8ths over the lament bass D-C#-C-B-Bb-A; the bassoon's sigh, handed to the basset horns in thirds; A7 crescendo with a timpani roll |
| requiem | 10 | Dm, A7/C# Dm A7, Dm Bb C7, F Gm7 C7, F F/A, Bb Gm7 F/C C7, F Dm/F Eb/G (N6), Dm/A A7 Dm Dm7/C, G/B Gm/Bb Dm/A A7, Asus4 A | 3 (f entry) -> 2 -> 3.5 ('lux') -> 2 | + choir, trombones (f passages), trumpets + timpani on the entry, organ continuo | the choir enters voice by voice, B T A S a beat apart, each on 'Re-qui-em' (a note, its upper neighbour, back), f; subito p at bar 3; F major 'lux' f; the Neapolitan turns back to D minor; lament bass; half cadence, fermata, the hall blooms |
| kyrie | 19 | subject Dm Eø7 A7 Dm / answer Am Bø7 E7 Am; episode Dm Gm7 C7 F Bb Gm7 C7sus4 C7; F entry F Gm7 C7 F; Dm..; Gm A7 C#dim7 Dm; A7; Gm/Bb Eb/G A7; D5 | 2.5 -> 5 | choir colla parte with strings, bassoons, basset horns; trombones from the middle entry; trumpets + timpani on the last entries and the cadence | fugue: B subject, T answer (tonal: A-D answers D-A; + B countersubject), A subject (+ T countersubject), S answer (+ A countersubject); each entering voice a level above the others for two bars; the free voices in quarters and passing 8ths; episode with the head in S / A / T over a walking bass (circle of fifths) into F major; middle entry in the tenors (F major); B subject + A subject a bar later; Adagio: iv6 - N6 - V7 onto a bare fifth D-A (fermata) |
| dies | 8 | Dm, A7/C# Dm, Bb Gm/Bb, A (G.P.), Dm Bb, C7/E F, Bb C7, F | 5 | tutti | f, not yet ff: declaimed choir blocks (syllables sung detached, gaps parted on the expression lane), violins I running 16ths, violins II measured 16ths on the alto, violas tremolo, 8th basses, timpani in the choir's rhythm on D / A; the trumpets hold back in the first phrase, then dotted figures (dotted 8th, 16th, quarter) on D / A; a one-beat general pause |
| tremor | 8 | Dm/F F#dim7 Gm G#dim7 (a bar each), Dm/A A7, Dm/A A7, Bb, Eb/G A7 | 1 -> 5 | strings tremolo, choir, then trombones / brass / timpani | subito pp, trembling repeated quarter chords over F-F#-G-G#-A, crescendo into the dominant pedal (soprano up to A5), deceptive Bb, the Neapolitan |
| ira | 8 | Dm Dm/F, Gm/Bb C#dim7/G, Dm/A A7, Dm; Dm Bb, Eb/G A7, Dm | 5 -> 0 | tutti, then low strings + timpani | the climax, ff (the only ff of the piece): violins in octaves (II an octave under I), trumpet fanfares, a timpani roll into the perfect cadence, hammered chords, the last blow, a low D tremolo pp into silence |
| tuba | 8 | Bb, Bb Eb, Cm F7, F; Bb/D Eb, Cm7 F7, Bb/F F7 Gm Eb, Gm A7 | 2 | solo trombone, strings pp, organ, 'oh' choir (low voices), bassoons | the trombone's call (Bb arpeggio up, a falling answer, half cadence); the low voices answer in unison with the trombone above; A7 fermata (the dominant of the Lacrimosa) |
| lacrimosa | 8 (12/8) | Dm Dm A7/C# Dm, Gm/Bb Eb/G Dm/A A7, Dm A/C# Eø7/G A, Dm Gm/Bb Dm/A A, climb: Dm Gm E7/G# Am, A Bb Eø7/Bb A7, Dm Gm/Bb Dm/A A7, Dm Bb Eø7/G A7 | 1.5 -> 4 -> 2.5 | strings (sighs), basses pizzicato then arco, basset horns, bassoons, 'oh' choir, then 'ah' choir + trombones + timpani | the violins' sighs (8th rest, appoggiatura, resolution) in thirds; the choir's lament ('oh', p); the soprano climbs A4-Bb4-B4-C5-C#5-D5-E5 over a descending bass to F5 forte (timpani roll into the hit); the sinking answer |
| amen | 4 (12/8) | Dm Gm/D Dm Bb/D, Eb/G Dm/A A7 A7, Dm Gm/D D, D | 2.5 -> 1 | 'oh' choir, strings sustained, trombones, bassoons, basset horns, organ; trumpets + timpani on the last chord | plagal Amen over a D pedal, the Neapolitan, the seventh resolving into the Picardy third (soprano F#4 on top), fermata, the hall blooms |

## The themes (instead of a hook)

- The Introitus soprano: D5 held, the turn C#5-D5-E5, the sigh F5-E5, the F major rise to G5.
- The fugue subject (D4 A4 Bb4. A4 | G4 F4 E4 D4 C#4 D4) and its chromatic countersubject (F3 E3 | Eb3 D3 E3 F3).
  Both return: the head motif in the episode, a major-mode middle entry, a close pair of final entries.
- The Lacrimosa soprano (A4 D5 C#5 D5 E5 F5 E5, the q-e siciliano rhythm) and its chromatic climb. It goes back to
  the Introitus lament bass, turned upside down: the voices rise while the bass falls.
- Homages (the delivery text names them): the Lacrimosa's chromatic soprano climb over a falling bass and the Tuba's
  rising Bb-major trombone arpeggio follow the gestures of K. 626's Lacrimosa and Tuba mirum (public domain); the
  notes are this piece's own.

## Transitions

- A7 crescendo and timpani roll into the choir's f entry.
- A half-cadence fermata into the fugue, attacca.
- An Adagio cadence and a bare-fifth fermata into the Dies irae's ff.
- A one-beat general pause in the Dies irae; the subito pp of the tremor.
- The hush on a low D (the third of Bb) into the Tuba.
- The A7 fermata into the 12/8 Lacrimosa.
- The ritardando and fermata of the Amen.

## Players and performance

- Orchestra: `orch.perform` for every role, one clip per role for the whole piece. Articulations are marked per
  passage:
  - staccato: the Introitus pulse and the 16ths;
  - tremolo: the storm and the tremor;
  - marcato: the brass hits;
  - pizzicato: the Lacrimosa basses;
  - hit / roll: the timpani.

  Velocities become the live dynamics lane, long notes swell (messa di voce), and slow attacks start early.
- Dynamics come from one map for the whole piece: hairpins, subito p / pp as steps, pp = 34 .. ff = 120. On top of
  it:
  - `humanize.touch` phrase arcs on every line (the line rises to its goal and relaxes);
  - bar accents;
  - a seeded +-3 jitter;
  - on the 16ths, beats +10 and offbeats -5.
- Choir: sung at a speaking velocity (110-124: the VPO / NBO choirs speak slowly at low velocity, TODO.md). The
  written dynamics go on each voice's live `dynamics` lane (a (v/127)^1.6 curve), with a messa di voce on notes of
  2.4 s or more. Long notes start 70 ms early, with 10 ms of humanized timing.
- Solo trombone: `hornist.arrange(family='trombone', style='classical', section='verse', peaks=(2, 4, 12, 20),
  vel=(66, 104))`. It played 14 vibratos, 7 blooms, 5 swells, 4 pushes, 1 scoop, 1 taper and 1 turn away.
- Tempo: rubato ('breath' / 'arch', +-5-5.5 %) in the Introitus, Tuba and Lacrimosa, a small tenuto (+0.35-0.4
  beat) on the Neapolitan chords of the intro, the Requiem and the Amen, ritardandi into every fermata, and the
  Adagio of the Kyrie's cadence.
- Figures over chords: the Introitus pulse is written 20-24 velocity steps (mp-mf) above the chords it decorates,
  the Lacrimosa sighs 10-14 above the lament (the appoggiatura +5 over its resolution, and never on a pitch the
  choir sings at that moment), the storm's 16ths f (+6, beats +10), the trumpets f-ff (+4 / +10 in the ira).
- The organ is a continuo: the bass line throughout (tasto solo in the Kyrie and the storm), a light right hand (the
  alto and tenor) only in the soft chorales - the Requiem's p passages, the Tuba, the Amen.
- Choir, the Dies irae / tremor / ira: syllables, not a vowel pad. Notes last 55-85 % of their value (1-beat notes
  60 %), and the `expression` lane parts them: after each syllable it falls to 0.4 (-8 dB) within 50 ms and opens on
  the next attack (the samples' own release is 1.25 s and cannot be shortened per track).
- Choir, the Lacrimosa and Amen ('oh'): a swell on each 'Lacrimosa' bar on the expression lane (0.64 -> 1 -> 0.64,
  ~7.5 dB, peaking on the bar's highest soprano note); the Amen leans into its plagal chords and blooms into the
  Picardy D major. The Tuba's men answer with one swell per phrase.

## Needs from sound design

- Every section needs its articulations as keyswitches: SSO sustain / staccato / marcato / tremolo / pizzicato, and
  timpani hit / roll.
- The choir needs 'ah' per voice (seated S-A-T-B from left to right) and a clean-looping 'oh' for the soft
  movements.
- A continuo organ, and a solo tenor trombone that plays legato.
