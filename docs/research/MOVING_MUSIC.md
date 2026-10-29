# What makes music moving and good: a literature review for the endless composers

Written 2026-10-25 for the endless orchestra (`agentsound/endless/symphony.py`) and the endless piano
(`agentsound/endless/perform.py`). The question: what does research say makes music **moving** (chills, frisson,
tears, "being moved") and **good** (quality, memorability, expressiveness)? The answer is aimed at what a rule-based
composer and performer can do differently, and at how to measure it.

The bar: the judges' masterpiece-scale gap (songs/_endless_orchestra/out/masterpiece_gap/REPORT.md), the code review
(out/code_review/REPORT.md) and rounds o21-o24 / p-div (songs/_blind/ROUNDS.md).

**Evidence grades** used below:

| Grade | Meaning |
|---|---|
| **A** | Replicated across labs, or a meta-analysis / systematic review with many studies |
| **B** | One well-controlled experiment (or a few consistent ones) with a causal manipulation or a large n |
| **C** | Correlational, survey, or small-n (n < 30) lab work, or a single corpus study |
| **D** | Theory, music-analytic tradition, or expert opinion with no listener test |

**Two caveats that run through everything.**

- **Chills are rare and personal.** In lab studies most listeners have few or none. The same passage chills one
  listener and not the next, and familiarity, personality (openness) and musical training raise the rate (Grewe et
  al. 2007, 2009; de Fleurian & Pearce 2021). So the features below **raise the odds** of a strong response. They do
  not guarantee one.
- **Features come bundled.** A crescendo usually brings a new instrument, a wider range, a brighter spectrum and a
  harmonic arrival all at once. Correlational studies cannot pull these apart (Bannister & Eerola 2018). That is
  itself useful to us: the effect probably comes from the **stack**.

---

## 0. The top 10 levers (prioritised for the endless orchestra and piano)

The ranking weighs three things: the evidence, what the judges already say is missing, and what the code does not
yet do. "Code today" comes from a brief grep of `symphony.py`, `perform.py`, `genres.py`, `expressive.py` and the
docs, not a full audit.

| # | Lever (what to do) | Main evidence | Judges' gap it serves | Code today |
|---|---|---|---|---|
| 1 | **Stage one "chill moment" as a stack of events at the summit**: a long, predictable build, then a brief withdrawal (bass out or a hush), then a new voice entering with the theme, the range opening both ways, a harmonic surprise and a loudness jump, all inside about 2 bars | Sloboda 1991; Guhn 2007; Grewe 2007; Nagel 2008; Bannister 2020; Solberg & Dibben 2019; de Fleurian et al. 2024; Salimpoor 2011 | #4 no climax hierarchy; o24 "every climax the same marcato tutti" | Partly. SUMMIT doubles everything; CHROMA_EVENT exists but is off (o15b -0.7 se); CHOIR (oc1) is off; RT_PEDAL builds; `'gp'` pauses. Piano: goosebump chord, suspended pause, cascade |
| 2 | **Appoggiaturas, suspensions and short descending sequences in the lyrical themes**, concentrated at phrase peaks and cadences (the "tears" features) | Sloboda 1991 (tears); Steinbeis 2006 (tension rises with each harmonic violation); KTH melodic charge | #5 themes without a kernel; #6 harmonic stasis | Inner voices have suspensions (INNER_MOTION). There is no melodic appoggiatura rule in symphony.py. The piano has some (PIANO_MOVES) |
| 3 | **Surprise on a confident expectation**: establish a pattern twice, then break it on the third time; keep the music conventional where it is already uncertain. Hold a per-piece surprise budget (an inverted U) | Cheung 2019; Gold 2019; Chmiel & Schubert 2017 (50 of 57 studies); Huron 2006; Egermann 2013 | #1 block sequences; #6 square phrasing; the set's template tells | Not modelled. No surprisal or entropy measure is used for composing |
| 4 | **Build by addition, release by reduction**: summits come from instruments, voices and register being added, not from capping everything before them; after the summit, thin out slowly (the intensity lingers) | Goodchild, Wild & McAdams 2019; Farbood 2012; Panksepp 1995; Bannister 2020 (loudness is causal) | #4; code review G4 (the summit is won by lowering the rest) | LOUDEST, `_reserve` and SUMMIT `drop` lower what comes earlier (the code review's G4). There is no additive plan |
| 5 | **One unambiguous peak and a strong ending (peak-end rule)**; never pad length | Rozin, Rozin & Goldberg 2004 (peak and end predict remembered affect; duration neglect) | #4, #8 clipped endings; o24 "endings by loudness" | One summit exists. MIN_LEN pads (code review G5); ending types are drawn but the loudness of endings did not differ in o24 |
| 6 | **A planned tension curve**: waves that rise toward one summit, all tension features moving together into it, and deliberately decoupled elsewhere (a hush over a dissonance) | Lerdahl & Krumhansl 2007; Farbood 2012; Huron's ITPRA | #4, #7 pacing | Loudness is planned per section. Pitch height, onset density and harmonic tension are not planned as one curve |
| 7 | **Recognisable returns, varied in colour**: the theme's head comes back audibly (often in a new colour or with a counter-line); local recognisability matters more than large-scale key closure | Margulis 2013/2014; Huron 2013; Cook 1987; Tillmann & Bigand 2004; Granot & Jacoby 2011 | #2 the return does not arrive; #3 autopilot accompaniment | RETURN and RECAP_VARY exist; t1_home / t2_home are guaranteed by construction (code review G1) |
| 8 | **Memorable kernels**: a common overall contour (an arch) with one unusual interval or rhythm, a single highpoint, the leap answered by a step, repeated within the piece, the melody clearly on top of the mix | Jakubowski 2017; Müllensiefen & Halpern 2014; Van Balen et al. 2015; Huron 1996; von Hippel & Huron 2000; Eitan 1997 | #5; "memorable" is the lens with the smallest gains (o23 +0.19) | MOTTO_CHARACTER (one leap, one highest note, no scale runs). No "typical contour + rare detail" test |
| 9 | **A tender, sad-sounding moving section in most pieces**: slow, soft, legato, a dark timbre, a solo "voice-like" instrument with vibrato / portamento over strings, more rubato | Vuoskoski & Eerola 2017 (being moved mediates the pleasure of sad music); de Fleurian & Pearce 2021b (chill tracks are sadder, slower); Panksepp 1995; Huron et al. 2014 (small pitch movements); Juslin & Laukka 2003 | Listener lens: emotion; "keep the quiet lyrical second themes" | Lyrical second themes exist. Portamento is not built (TECH: "not built: portamento") |
| 10 | **Shape the peak in performance**: the phrase arch (tempo and loudness together), a breath or "inhale" before the summit's downbeat, doubled lines and tuttis placed together (a shared deviation), a final ritard of the runner's-stop shape | Todd 1992; Repp 1992/1997; Friberg et al. 2006; Bhatara 2011; Chapin 2010 | #10 ensemble timing as independent jitter | Mostly there: `expressive.py` (KTH charge, phrase arch, final ritard, correlated timing), the piano's inhale. Check the tutti onset spread and add the orchestra's pre-summit breath |

**If only three things are done:** levers 1, 2 and 3.
- They are the best-evidenced triggers of strong responses.
- They are the ones the generator lacks most.
- They answer the judges' "competent but anonymous": nothing in the pieces is both prepared and surprising.

**Lessons the rounds already taught, which the literature explains:**
- **p-div lost when the early peak dropped the build.** In Salimpoor 2011 and de Fleurian et al. 2024, the build's
  predictability is what gets paid off.
- **o15b's CHROMA_EVENT, judged alone, did not win.** A harmonic surprise alone is weak. The chill comes from the
  stack, placed after a confident expectation (Cheung 2019).
- **o24's varied climax positions were not heard as variety.** The golden-section position has no listener evidence
  (section 5), and the texture of the peak (lever 1) is what makes peaks different.

---

## 1. Chills, frisson, tears and "being moved"

### 1.1 Which musical events trigger strong responses

**F1. Different structures trigger different bodily responses.** Tears and a lump in the throat follow melodic
appoggiaturas and melodic or harmonic sequences (including a descending circle of fifths to the tonic). Shivers follow
new or unexpected harmony (including enharmonic shifts) and sudden changes of dynamics or texture. A racing heart
follows acceleration, syncopation, and a prominent event arriving earlier than prepared.
- **Evidence**: C. A retrospective survey of about 83 music lovers who named the passages that moved them; there was
  no control set, which a later critique points out ([newmusicusa critique](https://newmusicusa.org/?p=275769)). It is
  still the most cited structural account, and later lab work broadly agrees on harmony and dynamics.
- **Source**: Sloboda (1991), *Psychology of Music* 19(2), 110-120,
  [doi:10.1177/0305735691192002](https://doi.org/10.1177/0305735691192002); summarised in
  [Harrison & Loui 2014](https://www.frontiersin.org/articles/10.3389/fpsyg.2014.00790/full).
- **Do**:
  - Lyrical themes (second theme, slow movement, the piano's A section) put a strong-beat appoggiatura that resolves
    down by step at the phrase's highpoint and at its cadence.
  - Before the final cadence, one short descending sequence or circle-of-fifths approach (at most 3 links, so the
    judges' "block sequence" complaint is not repeated).
  - Shivers: the summit or a return is entered through a chord that is not the expected one (a chromatic mediant,
    bVI, the Neapolitan, an enharmonic pivot).
- **Measure**:
  - `appog_rate`: strong-beat non-chord tones in the lead that resolve by step, per 4 bars of lyrical themes. Target
    at least 1, with at least one at the highest note of the phrase.
  - `seq_cadence`: a sequence of 2-3 links within 4 bars before the structural cadence.
  - `surprise_entry`: the chord at the summit's or the return's first downbeat is outside the key's diatonic set, or
    its root is 3 or more fifths from the previous one.

**F2. Chill passages share their surface.** They have:
- a sudden or gradual rise from soft to loud;
- an abrupt or gradual expansion of the frequency range, upward, downward or both;
- a solo instrument emerging from or alternating with the accompaniment;
- a harmonic progression that departs from the expected one.

Chills went with higher skin conductance.
- **Evidence**: B/C. Two rounds of 27 listeners each, slow classical movements, chill passages picked in round 1 and
  tested in round 2.
- **Source**: Guhn, Hamm & Zentner (2007), *Music Perception* 24(5), 473-484,
  [doi:10.1525/mp.2007.24.5.473](https://doi.org/10.1525/mp.2007.24.5.473); secondary summaries in
  [Bannister & Eerola 2018](https://www.frontiersin.org/article/10.3389/fpsyg.2018.02046/full) and
  [Harrison & Loui 2014](https://www.frontiersin.org/articles/10.3389/fpsyg.2014.00790/full) (which also note that a
  drop to extreme softness can trigger chills).
- **Do**: the summit opens the register in both directions within 1-2 bars (the basses an octave lower and the top
  line an octave higher). The top note and the lowest bass note of the piece are reserved for that window. The theme
  at the summit is carried by a soloist or a section that was silent just before (see F4).
- **Measure**:
  - `range_jump`: the semitones between the lowest and highest sounding notes, over 2 bars before against 2 bars
    after the summit's downbeat. Target +12 or more, with the piece's extremes inside the window.
  - `solo_emerge`: a lead role that rested at least 2 bars before the summit carries the melody at it.

**F3. Chill onsets cluster at loudness peaks, at modulations, at the entry of a new voice or instrument, and where
the melody sits in the human vocal register.** Loudness and sharpness rise at chills.
- **Evidence**: B. Real-time button presses on culturally prominent pieces (Grewe et al. 2007: a few dozen listeners; 2009:
  95 listeners, 7 pieces). Subjective intensity, skin conductance and heart rate peak together. Familiarity raises
  the chance; age, sex and training do not.
- **Sources**:
  - Grewe, Nagel, Kopiez & Altenmüller (2007), *Music Perception* 24(3), 297-314,
    [doi:10.1525/mp.2007.24.3.297](https://doi.org/10.1525/mp.2007.24.3.297)†.
  - Grewe, Kopiez & Altenmüller (2009), *Music Perception* 27(1), 61-74,
    [doi:10.1525/mp.2009.27.1.61](https://doi.org/10.1525/mp.2009.27.1.61)†.
- **Do**: the summit's melody sits in the vocal sweet spot (about G3-G5 sounding, with the top note around A5-C6 for
  violins and flutes). Sitting high for its own sake does not count. A modulation (or a lift) at the last return. A
  new colour entering exactly on the theme's head.
- **Measure**:
  - `peak_vocal`: the summit lead's median pitch lies in 55-79 (MIDI).
  - `entry_on_head`: the first onset of a newly entering role falls within one beat of the theme head's first note.

**F4. Spectral loudness in the 920-4400 Hz band (8-18 Bark) rises in chill excerpts.** Later secondary sources add
more roughness and a lower tone-to-noise ratio.
- **Evidence**: C. 20-second excerpts, chill against non-chill.
- **Source**: Nagel, Kopiez, Grewe & Altenmüller (2008), *Musicae Scientiae* 12(1), 101-113
  ([record](https://jyx.jyu.fi/handle/123456789/19439)).
- **Do**: the presence region has to swell into the summit, through brass, violins in their upper-middle register,
  and choir "ah". A rise only in the bass (timpani, low brass) does not do this.
- **Measure**: `presence_rise`, the band loudness (920-4400 Hz) over the 4 s before against the 4 s after the summit
  downbeat, from the render. Target +4 dB or more (an analysis-level feature; `report.json` already has spectra).

**F5. Loudness is causal, brightness is not simply "more".** In a crescendo piece, a louder version produced more
chills and a brighter version fewer. A guitar-solo control piece did not change.
- **Evidence**: B. A causal manipulation, 40 listeners, 5 versions per piece.
- **Source**: Bannister (2020), *A vigilance explanation of musical chills? Effects of loudness and brightness
  manipulations*, *Music & Science*
  ([record](https://sage.figshare.com/collections/A_Vigilance_Explanation_of_Musical_Chills_Effects_of_Loudness_and_Brightness_Manipulations/4933161)).
- **Do**: the summit has to be the loudest moment by a clear margin; F4's presence band is not the same as
  harshness. Avoid making the summit the brightest moment as well: keep the master's high shelf and the harshness
  checks.
- **Measure**: `peak_margin_lu`, the summit's short-term loudness above the next-loudest section. Target 2-3 LU or
  more (the code already has `pre_peak_margin_lu`). Keep the harshness warnings at 0.

**F6. Cutting out the chill passage removes the chills.** Continuous chill ratings follow loudness, brightness and
roughness in 2 of 3 pieces.
- **Evidence**: B. 24 listeners who often get chills; the passages were removed; continuous ratings plus skin
  conductance.
- **Source**: Bannister & Eerola (2018), *Frontiers in Psychology* 9:2046,
  [doi:10.3389/fpsyg.2018.02046](https://doi.org/10.3389/fpsyg.2018.02046).
- **Do**: confirms that a specific, locatable passage matters, so it can be engineered (lever 1). The pieces used were
  a crescendo climax of the whole band, a slow string theme (Holst, *Jupiter*), and a new lead instrument over the
  accompaniment.

**F7. Expectation drives chills.** In 1,019 listener-nominated pieces (1,806 chill onsets, 402 people), melodic
surprisal (IDyOM information content) is low before a chill and rises at its onset. Chill passages also carry higher
melodic uncertainty than control passages. The melodic expectation features were the strongest predictors, above the
acoustic features, but the classifier is only modestly above chance (AUC 0.60).
- **Evidence**: B/C. A large corpus with automatic melody extraction (noisy); a preprint.
- **Source**: de Fleurian, Clemente, Benetos & Pearce (2024), *Melodic expectation as an elicitor of music-evoked
  chills*, bioRxiv, [doi:10.1101/2024.10.02.616280](https://doi.org/10.1101/2024.10.02.616280).
- **Do**: in the 4-8 bars before the summit, the melody becomes **more predictable**: repetition, sequence, a
  stepwise climb, the motto's known head. The summit's first note or chord is then **surprising**: a leap, a
  non-diatonic note, an early arrival. This is exactly the shape the p-div round lost when it dropped the build.
- **Measure**: `ic_dip_peak`, the mean surprisal of the lead's notes over 8 bars before the summit against the
  summit's first 2 notes. It needs a surprisal model independent of the generator: a variable-order n-gram over
  interval and duration, trained on a corpus (the references or public folk / classical melodies), or IDyOM itself
  run offline. Target: pre-summit below the piece's median, the summit onset in the top 10 %.

**F8. Systematic review: the features linked to chills across studies.**
- Acoustic: sudden loudness changes and crescendos, roughness, sharpness / brightness, high event density, an expanded
  frequency range.
- Structural: new or unprepared harmony, sudden texture changes, appoggiaturas, enharmonic changes, sequences, events
  earlier than expected, key changes, build-ups and climaxes, the human voice, the entry of a new instrument, the
  interplay of solo and background.
- **Evidence**: A (as a review of many studies). The individual studies are mostly C.
- **Sources**:
  - de Fleurian & Pearce (2021), *Chills in music: a systematic review*, *Psychological Bulletin* 147(9), 890-920,
    [doi:10.1037/bul0000341](https://doi.org/10.1037/bul0000341) ([QMRO](https://qmro.qmul.ac.uk/xmlui/handle/123456789/75159)).
  - The feature list as summarised in the 2024 preprint's introduction (F7).
- **Do**: the checklist for lever 1.

**F9. Chill tracks are sadder, slower, less intense and more instrumental than matched tracks.**
- **Evidence**: C. A corpus of 988 chill tracks against matched controls, using streaming-service audio descriptors.
- **Source**: de Fleurian & Pearce (2021b), *i-Perception*
  ([DOAJ](https://doaj.org/article/7c30c521a2214a22a9e6c8d3dd069773)).
- **Do**: supports lever 9. A moving piece is not a loud, fast piece; the lyrical slow section is where much of the
  power lives.

**F10. Chills track perceived sadness more than happiness.** Chills clustered in a crescendo of a popular rock track,
but in other pieces they were spread out or fell on unremarkable moments. Panksepp proposed a separation-call
(social loss) account.
- **Evidence**: C. Classroom hand-raising. The separation-call account was not supported by a 2025 test
  ([Durham thesis](https://etheses.durham.ac.uk/id/eprint/15886/)).
- **Source**: Panksepp (1995), *Music Perception* 13(2), 171-207,
  [doi:10.2307/40285693](https://doi.org/10.2307/40285693)†.
- **Do**: the solo-over-strings lament (a lone voice, then the many) is a credible "social" chill (see F13).

### 1.2 The reward system: anticipation, then the peak

**F11. Intensely pleasurable music engages the reward circuit, and dopamine is causal.**
- Brain regions: PET shows chills scaling with activity in the ventral striatum, midbrain, amygdala, orbitofrontal
  cortex and vmPFC (Blood & Zatorre 2001, n = 10).
- Timing: dopamine is released in the **caudate during anticipation** (the seconds before the peak) and in the
  **nucleus accumbens at the peak** (Salimpoor et al. 2011, n = 8 PET plus fMRI).
- Causality: levodopa raises musical pleasure and the wish to buy, and risperidone lowers both (Ferreri et al. 2019,
  n = 27, double-blind).
- **Evidence**: A for the involvement of reward (replicated across methods). The anticipation / peak split is B.
- **Sources**:
  - Blood & Zatorre (2001), *PNAS* 98(20), 11818-11823,
    [doi:10.1073/pnas.191355898](https://doi.org/10.1073/pnas.191355898).
  - Salimpoor et al. (2011), *Nature Neuroscience* 14, 257-262, [doi:10.1038/nn.2726](https://doi.org/10.1038/nn.2726).
  - Ferreri et al. (2019), *PNAS* 116(9), 3793-3798,
    [doi:10.1073/pnas.1811878116](https://doi.org/10.1073/pnas.1811878116).
- **Do**: the **anticipation phase is half the reward**. Every summit needs a recognisable approach of roughly 8-20 s:
  a dominant pedal, a rising sequence, a crescendo, the motto head in imitation. That approach must signal *what* is
  coming (the theme) and roughly *when* (a hypermetric downbeat), then deliver it. An early peak with no build loses
  the anticipation half (p-div).
- **Measure**:
  - `build_len_s`: the seconds of monotone rise (tension features, see F17) ending at the summit. Target 8 s or more.
  - Judge question: "Did you know something big was coming? Did it arrive?"

### 1.3 Tears against chills, and being moved

**F12. Chills and tears are two different peaks.** Chills raise skin conductance and subjective arousal. Tears come
with slow breathing, a faster heartbeat and a calmer state. Chill songs are rated happy *and* sad; tear songs sad and
calm.
- **Evidence**: B/C. 32 + 34 students.
- **Source**: Mori & Iwanaga (2017), *Scientific Reports* 7:46063,
  [doi:10.1038/srep46063](https://doi.org/10.1038/srep46063).
- **Do**: design two kinds of moments.
  - The **chill**: arousing, a stack (lever 1).
  - The **tear**: low arousal, a tender melody with appoggiaturas (F1), a slow tempo, soft, a solo line, often at a
    return of the theme or in the coda.
  - A piece can have both. Typically the tear comes after the chill, in the reduction (F21).

**F13. "Being moved" is a mixed, mostly positive emotion.** It is typically sad plus joyful, with low-to-medium
arousal but felt as intense. It arises from scenes of closeness, reunion, loss and return.
- Being moved **fully mediates** the link between felt sadness and liking of sad music (Vuoskoski & Eerola 2017,
  n = 308 and 27 excerpts).
- Kama muta research ties it to a sudden intensification of communal closeness, with tears, goosebumps and warmth in
  the chest. The response is similar across cultures.
- A chills survey finds that the recurring triggers are crescendos, the human voice and ideas of unity or communion,
  and that chills are usually felt as "moving".
- **Evidence**: A/B for the construct (many studies, 19-nation measurement work). C for the musical features.
- **Sources**:
  - Menninghaus et al. (2015), *PLOS ONE* 10(6):e0128451,
    [doi:10.1371/journal.pone.0128451](https://doi.org/10.1371/journal.pone.0128451).
  - Vuoskoski & Eerola (2017), *Frontiers in Psychology* 8:439,
    [doi:10.3389/fpsyg.2017.00439](https://doi.org/10.3389/fpsyg.2017.00439).
  - Zickfeld et al. (2020), *Psychophysiology*, kama muta physiology
    ([record](https://ciencia.iscte-iul.pt/publications/tears-of-joy-aesthetic-chills-and-heartwarming-feelings-physiological-correlates-of-kama-muta/83323?lang=en)).
  - Bannister (2020), *Psychology of Music* 48(2), 297-314, 375 respondents
    ([record](https://durham-repository.worktribe.com/output/1347620/a-survey-into-the-experience-of-musically-induced-chills-emotions-situations-and-music)).
  - Reviews: Eerola et al. (2018), *Physics of Life Reviews* 25, 100-121,
    [doi:10.1016/j.plrev.2017.11.016](https://doi.org/10.1016/j.plrev.2017.11.016); Sachs, Damasio & Habibi (2015),
    [doi:10.3389/fnhum.2015.00404](https://doi.org/10.3389/fnhum.2015.00404).
- **Do**, translated into orchestral gestures:
  - **Reunion**: the theme that was lost (fragmented in the development) returns whole, and tenderly.
  - **One becomes many**: a solo instrument states the theme, then the whole section or a choir takes it over in
    unison or octaves. This is the communion moment.
  - **Two voices meeting**: the second theme and the motto finally sound together.
  - Use the choir (`symphony_choir`, oc1) for this, not as decoration.
- **Measure**:
  - `one_to_many`: the same melody, first in one role, then in 3 or more roles within 8 bars, with a loudness rise of
    6 LU or more.
  - Judge question: "Was there a moment of warmth or reunion? Where?"

---

## 2. Expectation, tension and surprise

**F14. Emotion and meaning come from expectations set up, delayed and fulfilled or denied.** Meyer (1956) is the
classic account: affect arises when a tendency is inhibited.

Huron's ITPRA model splits the response to an event into five parts:
- **Imagination** (before the event: the pleasure of a foreseen outcome);
- **Tension** (just before it: arousal that rises with uncertainty);
- **Prediction** (right after it: a reward for having guessed correctly);
- **Reaction** (fast and reflexive: surprise feels negative at first);
- **Appraisal** (slower and conscious: "it's only music, and it's beautiful").

**Contrastive valence**: a negative reaction (surprise, a jolt) followed by a positive appraisal feels better than
the positive alone. This is Huron's explanation of frisson, related to the fear-to-safety flip, and of the "sublime".
- **Evidence**: D/B. The theory is influential and partly tested: harmonic violations do raise tension and skin
  conductance (Steinbeis et al. 2006, F15).
- **Sources**:
  - Meyer (1956), *Emotion and Meaning in Music*, University of Chicago Press.
  - Huron (2006), *Sweet Anticipation: Music and the Psychology of Expectation*, MIT Press.
  - Huron & Margulis (2010), "Musical expectancy and thrills", in Juslin & Sloboda (eds.), *Handbook of Music and
    Emotion*, Oxford University Press.
  - A summary of the sublime idea: [Huron, CCRMA talk](https://ccrma.stanford.edu/events/david-huron-theory-of-musically-sublime).
- **Do**:
  - **Delay the expected arrival**: a deceptive cadence before the real one; a fermata on V; a bar of silence before
    the return; a written-out ritardando into it. This uses the tension response.
  - **The jolt-then-beauty pair**: a subito ff chord, or a sudden pp, immediately resolved into the most beautiful
    statement of the theme.
- **Measure**:
  - `delayed_arrivals`: structural cadences preceded by a deceptive cadence, a fermata, a general pause or a 2-bar
    dominant extension. Target at least 1 per piece.
  - `contrast_pairs`: a jump of 10 LU or more in either direction within 1 s, followed within 4 bars by a theme
    statement.

**F15. Harmonic surprise increases felt tension, emotionality and skin conductance in proportion to how unexpected
the chord is.** EEG shows an early negativity that grows with the violation.
- **Evidence**: B. 24 listeners; Bach chorales with one chord changed to expected, unexpected or very unexpected.
  The direction has been replicated many times in Koelsch's ERAN literature.
- **Source**: Steinbeis, Koelsch & Sloboda (2006), *Journal of Cognitive Neuroscience* 18(8), 1380-1393
  ([preprint](https://stefan-koelsch.de/papers/Steinbeis%2BJOCN2006_inpress.pdf)).
- **Do**: graded harmonic surprise, kept in reserve.
  - The piece's most remote chord (an N6, an augmented 6th, bVI, a chromatic mediant) goes on the approach to the
    summit, or under the summit's top note.
  - Milder ones (applied dominants, iv in major) go at phrase ends.
  - Note that o14 put CHROMA_CADENCE's chords in quiet inner voices, where the judges did not hear them. Surprise has
    to be **foregrounded** (in the lead's harmony, at a dynamic accent), as o15b's notes found for the reference's
    tutti Neapolitan.
- **Measure**: `harm_surprise_curve`, per chord the chord-transition surprisal (an n-gram over roman numerals
  trained on a corpus) or Lerdahl's pitch-space distance (F17). Check that the piece maximum falls in the 8 bars
  around the summit, and that the 2-4 strongest surprises are louder than mf.

**F16. Pleasure is highest for surprise in a low-uncertainty context, and for confirmation in a high-uncertainty
context.** Pleasure as a function of uncertainty and surprise is saddle-shaped.
- **Evidence**: B. About 80,000 chords from 745 Billboard songs; ratings plus fMRI; the amygdala, hippocampus and
  auditory cortex track the interaction.
- **Source**: Cheung, Harrison, Meyer, Pearce, Haynes & Koelsch (2019), *Current Biology* 29(23), 4084-4092,
  [doi:10.1016/j.cub.2019.09.067](https://doi.org/10.1016/j.cub.2019.09.067).
- **Do**: the most important single rule for placing surprises.
  - **Build certainty first, then break it**: two statements of a model, and on the third, change it (a new harmony,
    an extension, a leap).
  - **In unstable passages** (the development, transitions) land on the expected chord at the ends of units; the
    listener is already uncertain and craves confirmation.
  - Today's development does the opposite: many links of the same model, so there is little uncertainty and no
    surprise.
- **Measure**:
  - `surprise_after_setup`: the share of high-surprisal events (top 10 % of a piece) whose preceding 2-8 beats are low
    in entropy (the bottom 50 %). Target above 0.5.
  - `confirm_in_uncertain`: in the development blocks, the share of unit ends on an expected chord. Target above 0.6.

**F17. Tension can be modelled.**
- **Lerdahl's tonal pitch space** combines hierarchical (prolongational) tension, the surface dissonance of the chord
  and its inversion, and melodic attraction. It predicts listeners' tension ratings well for diatonic and chromatic
  music.
- **Farbood's model** combines loudness, pitch height, onset frequency, harmonic tension and tempo, read through a
  moving window. Listeners track the *trends* of features: rising features add tension, and one salient trend can
  dominate.
- **Harmony works on a longer window**: tension follows harmony over about 10-22 s, and the other features over
  about 1-4 s.
- **Evidence**: B. Several continuous-rating experiments.
- **Sources**:
  - Lerdahl (2001), *Tonal Pitch Space*, Oxford University Press.
  - Lerdahl & Krumhansl (2007), *Music Perception* 24(4), 329-366,
    [doi:10.1525/mp.2007.24.4.329](https://doi.org/10.1525/mp.2007.24.4.329)†.
  - Farbood (2012), *Music Perception* 29(4), 387-428,
    [doi:10.1525/mp.2012.29.4.387](https://doi.org/10.1525/mp.2012.29.4.387); time scales in
    [Farbood 2013, Frontiers](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00998/pdf).
- **Do**: plan a **tension curve** for each piece, before the notes are written (the code review's A5 asked for this
  for orchestration).
  - Several waves, each peak higher than the last, one summit.
  - All features co-rise into the summit: louder, higher, denser, harmonically further.
  - In lyrical sections, decouple features on purpose: soft but dissonant, or loud but static.
  - Harmonic tension is slow: plan it over 4-8 bars, not bar by bar.
- **Measure**: `tension(t) = z(loudness) + z(top-voice pitch) + z(onsets/s) + z(harmonic distance)`, each smoothed
  over its window. Then:
  - check that the summit is the global maximum;
  - `wave_peaks_rising`: the local maxima ascend before the summit, with no tie within 10 %;
  - `pre_summit_slope`: positive over 8 s or more.

  The masterpiece gap's "no hierarchy of climaxes" is exactly a failure of this curve.

**F18. Liking follows an inverted U against complexity or unfamiliarity.** Intermediate predictability is preferred,
and repeated exposure lowers liking without removing the preference for the middle.
- **Evidence**: A. Chmiel & Schubert (2017) classed 50 of 57 studies over 115 years as compatible with a (segmented)
  inverted U. Gold et al. (2019) found the same with IDyOM-defined complexity. The U can break down for extreme
  stimuli.
- **Sources**:
  - Berlyne (1971), *Aesthetics and Psychobiology*.
  - Chmiel & Schubert (2017), *Psychology of Music* 45(6), 886-909
    ([record](https://researchers.westernsydney.edu.au/en/publications/back-to-the-inverted-u-for-music-preference-a-review-of-the-liter/)).
  - Gold, Pearce, Mas-Herrero, Dagher & Zatorre (2019), *Journal of Neuroscience* 39(47), 9397-9409,
    [doi:10.1523/JNEUROSCI.0428-19.2019](https://doi.org/10.1523/JNEUROSCI.0428-19.2019).
- **Do**: aim for the middle on two levels.
  - **Within a piece**: the theme is simple enough to learn on first hearing (F26), and the development is denser.
  - **Across a set**: the set's template tells (o23: 44 flags per packet against the references' 9) are the
    "repeated exposure lowers liking" effect at programme level. Set memory is the right tool; keep it on the
    *gestures* the judges name (the climax texture, the ostinato under a woodwind tune, the opening rhythm cell).
- **Measure**:
  - `ic_mean` and `entropy_mean` of lead and harmony per piece, from the surprisal model. Target: inside the
    references' band, neither the most predictable nor the least.
  - At the set level, the template-flag count and the gesture repeat counts (already judged).

**F19. Live-concert surprise predicts arousal.** IDyOM high-information-content moments in live solo flute music
predicted rises in skin conductance, heart rate and subjective arousal, and lower expectedness ratings.
- **Evidence**: B. A live audience; computational surprisal.
- **Source**: Egermann, Pearce, Wiggins & McAdams (2013), *Cognitive, Affective, & Behavioral Neuroscience* 13(3),
  533-553, [doi:10.3758/s13415-013-0161-y](https://doi.org/10.3758/s13415-013-0161-y). Background: Pearce (2018),
  *Annals of the NYAS* 1423, 378-395, [doi:10.1111/nyas.13654](https://doi.org/10.1111/nyas.13654).
- **Do / measure**: validates using a surprisal model as an analysis signal (F7, F16, F18).

---

## 3. Emotion mechanisms and cues

**F20. Music induces emotion through several mechanisms (BRECVEMA).**

| Mechanism | What triggers it |
|---|---|
| **B**rain-stem reflexes | Sudden, loud or dissonant events |
| **R**hythmic entrainment | The body locks to the pulse |
| **E**valuative conditioning | Learned associations |
| **C**ontagion | Mimicking a voice-like expression |
| **V**isual imagery | Pictures the music evokes |
| **E**pisodic memory | Personal memories |
| **M**usical expectancy | Expectations set up and met or broken |
| **A**esthetic judgment | Admiration and awe at the craft |

- **Evidence**: D/B. A framework; the mechanisms differ in speed and in how much they depend on musical structure.
- **Sources**: Juslin & Västfjäll (2008), *Behavioral and Brain Sciences* 31(5), 559-575
  ([PubMed](https://pubmed.ncbi.nlm.nih.gov/18826699/)); Juslin (2013), *Physics of Life Reviews* 10, 235-266,
  [doi:10.1016/j.plrev.2013.05.008](https://doi.org/10.1016/j.plrev.2013.05.008)†; Juslin (2019), *Musical Emotions
  Explained*, Oxford University Press.
- **Do**: four of the eight mechanisms are under our control.
  - **Brain-stem**: subito events and sfz at the summit, used rarely.
  - **Entrainment**: a clear pulse in fast sections; a lilt in dances.
  - **Contagion**: voice-like expressive lines (F22).
  - **Expectancy**: section 2.

  Aesthetic judgment ("that was clever") is what the composer and devil's-advocate lenses score: the development's
  craft (FUGUE, DEV_WALK).
- **Measure**: a judge question per mechanism used ("What in this piece made you feel something: the sound itself,
  the pulse, a voice-like line, a surprise, the craft?").

**F21. The emotion cue code is shared by voice and music, and it is redundant.**

| Emotion | Tempo | Level | Articulation | Attack | Timbre | Timing variability | Contour |
|---|---|---|---|---|---|---|---|
| **Sadness / tenderness** | slow | low | legato | slow | dull or dark | high, with a final ritardando | falling |
| **Happiness** | fast | high | staccato | fast | bright | low | rising |
| **Anger** | fast | high | (mixed) | sharp | sharp | (irregular) | (accents) |

Sadness and tenderness also come with small level variability and slow vibrato. Anger brings irregularity and sharp
accents.
- **Evidence**: A. A meta-analysis of 104 studies of vocal expression and 41 of music performance, with decoding
  accuracy well above chance.
- **Sources**: Juslin & Laukka (2003), *Psychological Bulletin* 129(5), 770-814,
  [doi:10.1037/0033-2909.129.5.770](https://doi.org/10.1037/0033-2909.129.5.770); Juslin & Laukka (2004), *Journal
  of New Music Research* 33(3), 217-238,
  [doi:10.1080/0929821042000317813](https://doi.org/10.1080/0929821042000317813).
- **Do**: each section gets an intended emotion, and **all** its cues agree. Today the tempo is fixed per movement
  (code review C10). The lyrical second theme should get:
  - meno mosso (-5 to -10 %);
  - legato and slower attacks;
  - a darker colour (violas, cellos, clarinet chalumeau, horn);
  - more rubato.

  The summit should get faster attacks, marcato and a brighter colour (but see F5).
- **Measure**: `cue_coherence`, per section a vector (tempo, level, the legato / staccato ratio, attack time,
  spectral centroid, IOI variability). Check that it agrees in sign with the section's intended emotion. Report the
  mismatches.

**F22. Instruments sound sad in proportion to their ability to make small pitch movements** (bends, slides,
vibrato), plus their capacity for dark timbre and soft levels. This is the speech-prosody parallel.
- **Evidence**: C. 44 musicians rating instruments.
- **Source**: Huron, Anderson & Shanahan (2014), *Empirical Musicology Review* 9(1)
  ([article](https://www.osu.tests.sfulib4.publicknowledgeproject.org/index.php/EMR/article/view/4085));
  Vuoskoski's commentary ([EMR 9(1)](https://www.osu.tests.sfulib4.publicknowledgeproject.org/index.php/EMR/article/view/4086)).
- **Do**:
  - Give tender and lament lines to the cello, a solo violin, oboe, cor anglais or horn.
  - Build **portamento** for the solo strings: a slide on expressive leaps of a 4th or more, at most one per phrase,
    on a slow line. TECH lists it as "not built".
  - Keep vibrato on solo roles (`ensemble.VIBRATO`).
  - The piano cannot bend pitch. It gets its "voice" from the singing tone of the melody and from rubato.
- **Measure**: `slide_count` on solo strings per lyrical section, 1-3 at most (more is kitsch). Judge question:
  "Did any line sound like a voice?"

---

## 4. Expressive performance

**F23. Expressive timing and dynamics follow the phrase structure.**
- **Phrase arch**: speed up and get louder into the phrase's middle or peak, slow down and soften toward its end,
  nested over the phrase hierarchy (Todd's model).
- **Ritardandi**: in 28 great recordings of *Träumerei*, the ritardandi within gestures follow parabola-like curves
  and section ends get the largest ones. Listeners prefer the parabolic shape.
- **Evidence**: B/A. Many corpus measurements, and the KTH rules were validated in listening tests. The link between
  tempo and loudness is not universal: Repp found no tie in 117 Chopin performances, so treat the coupling as a
  default, not a law.
- **Sources**:
  - Todd (1992), *JASA* 91(6), 3540-3550, [doi:10.1121/1.402843](https://doi.org/10.1121/1.402843)†.
  - Repp (1992), *JASA* 92(5), 2546-2568, [doi:10.1121/1.404425](https://doi.org/10.1121/1.404425)†.
  - Friberg, Bresin & Sundberg (2006), *Advances in Cognitive Psychology* 2(2-3), 145-161,
    [doi:10.2478/v10053-008-0052-x](https://doi.org/10.2478/v10053-008-0052-x).
- **Do**: already built in `expressive.py` (`phrase_arch`, `final_ritard`, `punctuation`, `charge`) and in the
  orchestra's dynamics lanes. **New**: scale the arch's depth with the phrase's level in the form. The summit phrase
  and the last return get the deepest arch and the largest ritard into the cadence; transitional phrases stay nearly
  straight.
- **Measure**:
  - `ioi_phrase_r`: the correlation of the local tempo curve with a parabola per phrase, above 0.3 for lyrical
    phrases.
  - `rit_hierarchy`: the slowing at the ends of sections is larger than at the ends of phrases.

**F24. More expressive variation, up to a natural amount, is heard as more emotional.** Timing explains more of the
effect than intensity. Mechanical versions are rated less emotional and engage the emotion networks less. A
quantitatively *average* performance (the mean timing of 10 pianists) was rated second-best in quality, and this
replicated with 205 listeners.
- **Evidence**: B/A.
  - Bhatara et al. (2011): parametric scaling of timing and amplitude.
  - Chapin et al. (2010): expressive against mechanical performances, with fMRI.
  - Repp (1997), replicated by Wolf et al. (2018).
- **Sources**:
  - Bhatara, Tirovolas, Duan, Levy & Levitin (2011), *Journal of Experimental Psychology: Human Perception and
    Performance* 37, 921-934, [doi:10.1037/a0021922](https://doi.org/10.1037/a0021922)†.
  - Chapin et al. (2010), *PLOS ONE* 5(12):e13812,
    [doi:10.1371/journal.pone.0013812](https://doi.org/10.1371/journal.pone.0013812).
  - Repp (1997), *Music Perception* 14(4), 419-444 (the averaging and its replication are reviewed in
    [Wöllner 2013](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00361/full)).
- **Do**: aim for **normative, structure-driven** deviations of natural size, not idiosyncratic ones; they are rated
  as good. Put the variance in timing, linked to the structure (lean on appoggiaturas, delay the summit's downbeat),
  rather than in random velocity. Never quantise the lyrical lines.
- **Measure**:
  - `timing_var_struct`: the share of IOI variance explained by phrase position and metrical / harmonic charge.
    Target above 0.5 (the rest is noise).
  - Make sure the expressive depth is not lower in the lyrical sections than in the fast ones.

**F25. The arrival of the summit is made in time.** A slight broadening (an "inhale") before the summit's downbeat,
and the agogic accent on its first note, increase its weight. This is the tension response before an expected event
(F14).
- **Evidence**: B for the timing rules (KTH "phrase arch" plus "final ritard" at the higher levels; the
  corpus-measured broadening before structural downbeats in Repp's data); D for the specific link to chills.
- **Do**:
  - The piano already has `inhale`. The orchestra should get the same: about 3-6 % slower over the last bar of the
    build, the summit's downbeat 30-80 ms late, then a tempo.
  - Doubled lines and tutti attacks share **one** deviation (spread under about 20 ms). Independent jitter makes
    tuttis smear (the masterpiece gap's #10). `ensemble.ENSEMBLE['rho']` should be shared across doubled roles at the
    summit.
- **Measure**:
  - `tutti_spread_ms`: the onset spread of the summit's downbeat across roles. Target under 25 ms.
  - `pre_summit_broaden`: the tempo ratio of the last build bar against the 4 bars before it. Target 0.94-0.97.

---

## 5. Form and the large scale

**F26. Listeners' remembered affect is dominated by the peak and the end.** They rely on the moment of highest
intensity, on the last moments, and on moments more intense than what came just before, with "duration neglect". A
predictive formula was derived and applied to classical movement forms.
- **Evidence**: B. Continuous pressure ratings plus retrospective ratings. The peak-end rule is replicated widely in
  general psychology.
- **Source**: Rozin, Rozin & Goldberg (2004), *Music Perception* 22(1), 15-39,
  [doi:10.1525/mp.2004.22.1.15](https://doi.org/10.1525/mp.2004.22.1.15)†; follow-up
  [Schäfer et al. 2014](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4133782/).
- **Do**:
  - One summit clearly above everything else (lever 5).
  - Endings that are **affective events**, not stops: either the strongest statement of the theme yet, or a
    prepared, long-held soft ending with one last moving gesture (the tear moment, F12).
  - "Moments more intense than just before" means **contrast steps**: a sudden rise after a quieter passage counts
    more than a plateau, so put a quiet passage before each important entry.
  - Length by padding (MIN_LEN, code review G5) adds nothing. Duration neglect says the listener will not credit it.
- **Measure**:
  - `peak_prominence`: the summit's intensity minus the second-highest local peak.
  - `end_intensity`: the last 10 % of the piece against its median. Either above +2 LU (a triumphant ending), or below
    -6 LU with a final held chord of 4 s or more (a dissolving ending). Nothing in between.
  - `contrast_steps`: rises of 6 LU or more within 2 bars.

**F27. Listeners are only weakly sensitive to large-scale tonal structure.**
- Tonal closure is perceived only in short pieces, of about 1 minute or less (Cook 1987).
- The brain handles fine structure in short windows well and integrates poorly over long ones (Tillmann & Bigand
  2004; the "music in the moment" line).
- Listeners reordering the sections of a Mozart sonata showed some sensitivity to A-B-A' and to directionality, but
  none to global harmonic structure (Granot & Jacoby 2011).
- **Evidence**: B/A. Several paradigms agree.
- **Sources**:
  - Cook (1987), *Music Perception* 5(2), 197-205, [doi:10.2307/40285392](https://doi.org/10.2307/40285392)†.
  - Tillmann & Bigand (2004), *Journal of Aesthetics and Art Criticism* 62(2),
    [doi:10.1111/j.1540-594X.2004.00153.x](https://doi.org/10.1111/j.1540-594X.2004.00153.x).
  - Granot & Jacoby (2011), *Musicae Scientiae* 15(3), 365-386
    ([record](https://cris.huji.ac.il/en/publications/musically-puzzling-i-sensitivity-to-overall-structure-in-the-sona/)).
- **Do**: put the effort into what *is* heard.
  - Returns recognisable by melody and colour (F28).
  - Local contrast and directionality (the tension curve, F17).
  - The 10-30-second moments.
  - Do not trust key schemes alone to create drama: a modulation must be *marked* (by dynamics, colour, a pause) to
    count.
  - This also explains why the generator's tells (circular, structural) diverge from the panel (what is heard).
- **Measure**: judge questions that are local and timed ("the 3 best moments, with bars", "where did the music lose
  you"), not only global form scores.

**F28. Repetition is a source of pleasure, not only a crutch.**
- Excerpts of non-repetitive modern music (Berio, Carter) were rated more enjoyable, more interesting and *more
  likely to be by a human artist* when segments were repeated (Margulis 2013).
- Repetition shifts attention to new aspects of the music (Margulis 2014).
- Huron's habituation-fluency theory: repetition builds processing fluency, too much leads to habituation, and
  variation and rondo strategies balance the two.
- **Evidence**: B. Margulis (2013) has a modest n, but the direction is replicated (Touizrar et al. 2021).
- **Sources**:
  - Margulis (2013), *Empirical Studies of the Arts* 31(1), 45-57
    ([record](https://collaborate.princeton.edu/en/publications/aesthetic-responses-to-repetition-in-unfamiliar-music/)).
  - Margulis (2014), *On Repeat: How Music Plays the Mind*, Oxford University Press.
  - Huron (2013), *Current Musicology* 96, 7-35,
    [doi:10.7916/cm.v0i96.5312](https://doi.org/10.7916/cm.v0i96.5312).
- **Do**: themes come back **recognisably** (the head intact) and **changed in one respect** (colour, counter-line,
  register, harmonisation, mode). This matches the masterpiece panel's recap rule and its "keep motto saturation".
  The development is where variation dominates; the return is where fluency pays off. Avoid literal da capos (the
  references' own flaw) and changes that destroy recognisability.
- **Measure**:
  - `return_recog`: the head's interval and rhythm match against the exposition (target 0.8 or more).
  - `return_change`: at least 1 of {lead role, counter-line, register, harmony} differs (target 1 or more).

**F29. Build-up, breakdown and drop.** In EDM's "break routine" (breakdown, build-up, drop), the **drop** is where
peak experiences and the highest skin-conductance responses occur. The build-up uses rising sound effects, rhythmic
compression (shorter and shorter repeats) and the removal of the bass and kick, which return at the drop. Group
motion changes most at these points.
- **Evidence**: B/C. 24 listeners plus physiology (Solberg & Dibben 2019); 16 dancers with motion capture (Solberg &
  Jensenius 2017).
- **Sources**: Solberg & Dibben (2019), *Music Perception* 36(4), 371-389
  ([record](https://eprints.whiterose.ac.uk/id/eprint/145911/)); Solberg & Jensenius (2017), *Empirical Musicology
  Review* 11(3-4).
- **Do**: the orchestral equivalent is cheap and very much in the canon (Ravel, Sibelius, film).
  - In the last 1-2 bars before the summit, **withdraw the low end** (the basses, timpani and low brass rest or hold
    pp) while the upper parts climb.
  - **Compress** the motto: 2-bar units, then 1, then a half (the liquidation the masterpiece report asked for).
  - The summit enters with the full bass back on the downbeat. This is a sudden addition, which works better than a
    plateau (F30).
- **Measure**: `bass_withdraw`, the low-band (under 150 Hz) energy over the last bar before the summit against the
  first bar of it. Target +10 dB or more.

**F30. Orchestral gestures shape intensity.** Continuous ratings of emotional intensity:
- rise steadily through **gradual additive** gestures (instruments added one by one);
- jump sharply for **sudden additions**, peaking toward the end;
- show a **plateau of lingering high intensity** for reductive gestures, even as the other features fall.

Musicians, but not non-musicians, tended to anticipate sudden additions.
- **Evidence**: B/C. An exploratory experiment with musicians and non-musicians.
- **Source**: Goodchild, Wild & McAdams (2019), *Musicae Scientiae* 23(1), 25-49
  ([record](https://sonicfield.org/library/exploring-emotional-responses-to-orchestral-gestures))†.
- **Do**:
  - **Builds by addition**: one family enters every 2 bars on the motto. TSSB's clarinet sequence and the stormy
    reference's 28-beat pedal with the winds entering one by one are both judge-praised examples.
  - **Summits by sudden addition** (F29).
  - **After the summit, reduce gradually**: the intensity lingers, so a slow thinning keeps the glow. It is the place
    for the tear moment (F12).
  - Do not lower earlier passages to make room (code review G4). Plan the instrument count to rise instead.
- **Measure**: `roles_curve`, the number of sounding roles per bar. Check that it rises in steps of 1-2 through the
  build, jumps by 4 or more at the summit, and falls in steps afterwards.

**F31. Climax placement: no evidence for a golden-section optimum.**
- Golden-section proportions are found by analysts in some composers, mainly Bartók and Debussy, but there is no
  listener test showing that 0.618 is preferred, and perceived duration depends on the content.
- A corpus of 100 Chinese pop songs finds the final chorus is the arousal peak in only 31 of them.
- **Evidence**: D (analytic) against D/C.
- **Sources**: Howat (1983), *Debussy in Proportion*, Cambridge University Press; the critique at the
  [RNCM](https://research.rncm.ac.uk/en/activities/all-roads-lead-to-the-golden-section-contrasting-compositional-th/);
  [arXiv 2609.15675](https://arxiv.org/pdf/2609.15675).
- **Do**: do not tune a fixed fraction. What matters is a **build long enough to create anticipation** (F11) and a
  **post-peak section long enough to reduce gradually** (F30). Vary the place across a set (o24, p-div), but never by
  cutting the build. The 0.65-0.85 range of the masterpiece report is a sensible default, not a law.

---

## 6. Memorability: hooks and earworms

**F32. Earworm tunes have a more common global contour, less common (unusual) gradients between melodic turning
points, and faster tempi than matched tunes.** More recent chart success also predicts earworms.
- **Evidence**: B/C. 3,000 respondents; 100 earworm tunes against 100 matched tunes; 83 features.
- **Source**: Jakubowski, Finkel, Stewart & Müllensiefen (2017), *Psychology of Aesthetics, Creativity, and the
  Arts* 11(2), 122-135, [doi:10.1037/aca0000090](https://doi.org/10.1037/aca0000090).
- **Do**: the **kernel recipe**.
  - A familiar overall shape: an arch or a rise-then-fall (most European melodies are convex arches: Huron 1996, 6,251
    folksongs).
  - One distinctive interval or turn: a leap of a 6th or 7th, or a chromatic neighbour.
  - A rhythm that is recognisable on its own.
  - This is also the masterpiece report's o11 kernel test.
- **Measure**:
  - `contour_typical`: the theme's Huron contour class is convex or ascending.
  - `interval_rarity`: the theme head's rarest interval or gradient lies in the top 15 % of a corpus distribution.
  - Both should hold together.

**F33. Distinctive motifs relative to the context are better recognised.** Motifs that are rare *within the test set*
predicted correct recognition; motifs rare *against the whole corpus* predicted false alarms.
- **Evidence**: B.
- **Source**: Müllensiefen & Halpern (2014), *Music Perception* 31(5), 418-435
  ([record](https://research.gold.ac.uk/id/eprint/10838)).
- **Do**: within a set, every piece's head must be distinct from the others' heads (o24: "the motto openings repeat
  piece 1's head rhythm"). Rarity against the style in general is less useful: being *strange* can feel falsely
  familiar or wrong.
- **Measure**: `set_head_distance`, the minimum rhythm-plus-interval edit distance between heads across a set.

**F34. Catchiness (fast recognition) is predicted by melodic repetitiveness, melodic conventionality against the
corpus, and the prominence of the vocal / melody line.** Recognition times differ strongly between sections of the
same song.
- **Evidence**: B/C. The large online "Hooked" game; the feature findings are from a follow-up corpus paper (read
  here in secondary summaries).
- **Sources**: Burgoyne et al. (2013), ISMIR ([paper](https://archives.ismir.net/ismir2013/paper/000101.pdf));
  Van Balen, Burgoyne, Bountouridis, Müllensiefen & Veltkamp (2015), ISMIR (*Corpus analysis tools for computational
  hook discovery*).
- **Do**:
  - **The melody on top of the mix**: the orchestrator's balance must keep the theme well above the accompaniment.
    The masterpiece gap noted "the tune buried low" in TSSB.
  - The hook is repeated within the piece (motto saturation: keep it).
- **Measure**:
  - `lead_margin_db`: the lead's level above the loudest accompaniment role during theme statements. Target 3 dB or
    more (`mix` already reports masking).
  - `hook_count`: statements of the head per minute.

**F35. Melodic peaks and skips.**
- **Highpoints**: melodic climaxes coincide with other parameters (long notes, dissonance, a dynamic peak) in Haydn,
  Chopin and Berg (Eitan 1997).
- **Skips**: large leaps tend to be followed by a change of direction, which may come from regression to the
  tessitura's middle; listeners learn this as an expectation (von Hippel & Huron 2000).
- **Evidence**: C/B. Corpus statistics.
- **Sources**: Eitan (1997), *Highpoints: A Study of Melodic Peaks*, University of Pennsylvania Press; von Hippel &
  Huron (2000), *Music Perception* 18(1), 59-85.
- **Do**:
  - The phrase's highest note is **one** note, a long one and often an appoggiatura (F1), with the dynamic peak on it
    (KTH `high_loud`).
  - A big leap is answered by a step back.
  - In the summit phrase, the leap up to the piece's highest note is the single biggest leap in the lead.
- **Measure**:
  - `highpoint_unique`: the phrase maximum occurs once.
  - `highpoint_long`: its duration is in the top 25 % of the phrase.
  - `post_skip_reversal`: the share of leaps (5 semitones or more) followed by a reversal. Target above 0.7.

---

## 7. Orchestration effects: what the evidence supports

This section is a checklist from sections 1-6, each item weighed. "Strong" means the device is named by several
studies. "Moderate" means one study or the review lists. "Weak" means analytic or practitioner tradition only.

| Device | Evidence | Use | Code today |
|---|---|---|---|
| Crescendo into a loud arrival | Strong (F2, F3, F5, F8, F10, F13) | Every summit; the loudest by a margin | Yes (dynamics; LOUDEST) |
| Entry of a new voice or instrument on the theme, especially solo against tutti, or a choir | Strong (F2, F3, F6, F8, F13) | The summit's lead or the last return goes to a role that rested just before; the choir at the summit or as the "one to many" | Partly. CHOIR (oc1) is off; SUMMIT doubles the existing lead |
| Range expansion (bass down and top up together) | Moderate-strong (F2, F8) | The piece's top and bottom notes are reserved for the summit window | Partly (top_peak / pre_semis by suppression) |
| Unexpected harmony at the arrival (a chromatic mediant, bVI, N6, an enharmonic pivot) | Strong for shivers (F1, F8, F15) | Foregrounded at the summit or the return, ff or subito p | Built (CHROMA_EVENT) but off; was not stacked |
| Appoggiaturas / suspensions in the melody | Moderate for tears (F1, F8) | Lyrical themes, at the highpoint and cadence | Inner voices only |
| Melodic or harmonic sequence | Moderate for tears (F1, F8) | Short (2-3 links), into a cadence; *not* as the development's method | Overused in the development (judges' #1) |
| Sudden pianissimo / texture drop | Moderate (F2 secondary, F8; Huron's contrastive valence) | Before the return or the summit (the hush), then a sudden addition | Yes (subito, `'gp'`, hushes) |
| Modulation (key change), including a lift at the last return | Moderate for chills (F3, F8); the affect depends on key distance and mode (Korsakova-Kreyn & Dowling 2014) | One lift at the last statement in the piano's song-like forms; in the orchestra, mark it by colour or dynamics | Piano: key lift (PIANO_MOVES 5.17). Orchestra: recap keys |
| Bass withdrawal, then return (the "drop") | Moderate (F29, F30) | The last 1-2 bars of the build | No |
| Unison / octave doubling "everyone together" | Weak-moderate (unity / communion, F13) | One moment per piece; the masterpiece panel warns against the unison wall | SUMMIT does it every time (o24: "the tell") |
| Portamento / vibrato on a solo line | Moderate for sadness (F22) | 1-3 slides per lyrical section | Vibrato yes; portamento no |
| Roughness / brightness | Mixed (F4 against F5) | Presence-band rise yes; do not maximise brightness | Harshness checks exist |

**Korsakova-Kreyn & Dowling (2014)**: affective responses to modulations depend on the distance from the starting
key and on the mode. *Psychomusicology* 24(1), 4-20
([PDF](https://labs.utdallas.edu/mpac/files/2021/03/2014-2.pdf))†. No study isolates the pop "truck driver" semitone
lift as a chill trigger; it is practitioner lore.

---

## 8. What to measure: a summary for the analysis and the judges

**Computable features**, all from the score, the packets or the render. Keep them independent of the generator's own
code (the code review's G1 / 5.5 warning).

| Feature | From | Lever | Target |
|---|---|---|---|
| `event_stack` = count of {new role on the head, range_jump ≥ 12, surprise chord, presence_rise ≥ 4 dB, bass_withdraw ≥ 10 dB, ic_dip_peak} at the summit | score + render | 1 | ≥ 4 of 6 |
| `appog_rate`, `highpoint_unique`, `highpoint_long`, `post_skip_reversal` | score | 2, 8 | see F1, F35 |
| `surprise_after_setup`, `confirm_in_uncertain`, `ic_mean` / `entropy_mean` | an independent n-gram or IDyOM surprisal model | 3 | F16, F18 |
| `roles_curve` shape | score | 4 | steps up, a jump, steps down |
| `peak_prominence`, `end_intensity`, `contrast_steps` | render loudness | 5 | F26 |
| `tension(t)`: rising waves, summit = maximum, `build_len_s` ≥ 8 | score + render | 6 | F17 |
| `return_recog` ≥ 0.8 and `return_change` ≥ 1 | score | 7 | F28 |
| `contour_typical` and `interval_rarity`, `set_head_distance`, `lead_margin_db` | score + mix | 8 | F32-F34 |
| `cue_coherence` per section, `slide_count` | score + render | 9 | F21, F22 |
| `tutti_spread_ms` < 25, `pre_summit_broaden` 0.94-0.97, `ioi_phrase_r` > 0.3 | performed notes | 10 | F23-F25 |

These should **report**, not gate, until a blind round shows that each one tracks the panel. The code review showed
that hard-gating construction-guaranteed metrics makes the score circular.

**Judge questions**, to add to the packets' prompt; they are timed and local, per F27:
1. "Mark the single moment (bar) that gave you goosebumps, or the closest to it. What happened there: harmony,
   entry, loudness, register, silence?"
2. "Was there a moment of tenderness or reunion (a 'lump in the throat' moment)? Where?"
3. "Before the climax: did you sense it coming? Did it pay off, or come too early or too late?"
4. "Name one surprise. Was it set up (did you expect something else)?"
5. "Hum or write the opening theme's rhythm from memory after one hearing." This is a recall test; for agent judges,
   "describe the head's rhythm and contour without looking".
6. "How did it end: did the ending feel earned?" (the peak-end rule)
7. Per section, the felt emotion (tender / sad / joyful / triumphant / tense) against the intended one (cue
   coherence).

---

## 9. Where the current code stands, by lever

From a brief grep, so it is only an orientation:

1. **Stack**: `SUMMIT` (`symphony.py`, the doubling fill), `LOUDEST`, `_reserve`, `RT_PEDAL` and `RT_DRIVE` (the
   build), `'gp'` (general pauses), `subito` builds, `CHROMA_EVENT` / `CHROMA_CADENCE` (built, off after o14 / o15b),
   the `choir` module (oc1, off), TECH (merged in o23; the trill and glissando crowns). The piano has the goosebump
   chord (borrowed / chromatic-mediant chord under the climax's peak note), the suspended pause and the cascade
   (`perform._sign`, PIANO_MOVES 5.3-5.5). *Missing*: placing them **together** in one 2-bar window after a
   low-surprisal build, the bass withdrawal, a solo-to-tutti handover of the summit's theme.
2. **Appoggiaturas**: INNER_MOTION has suspensions in the inner strings, and the piano moves use appoggiaturas in
   places. *Missing*: a melodic appoggiatura rule in `sentence()` / `cantilena()`, placed at the phrase highpoint and
   cadence.
3. **Calibrated surprise**: *missing*. There is no surprisal model in the composer. `composer._entropy` and
   `learn/evaluate.norm_entropy` are distribution entropies, not note-by-note predictions. The learned generator's
   token model (`agentsound/learn`) could supply per-token surprisal, but it is trained on our own output and is not
   independent; prefer a corpus-trained n-gram or IDyOM, run offline.
4. **Additive build**: builds exist (BUILD_FRAMES, the rising clarinet sequence the judges praised). The summit's
   margin comes from lowering earlier music (code review G4). *Missing*: a role-count plan.
5. **Peak-end**: one summit (SUMMIT, LOUDEST), drawn endings (SHAPE, off). o24 measured that "cut / loud" endings were
   not louder than dying ones. *Missing*: the ending checked on the render (F26 targets).
6. **Tension curve**: the per-section loudness plan and the `macro.txt` measurement exist. *Missing*: a combined
   score-level tension curve and a check of the wave hierarchy.
7. **Returns**: RETURN, RECAP_VARY, t1_home / t2_home (by construction). *Check*: whether returns are recognisable
   and changed in one respect.
8. **Kernels**: MOTTO_CHARACTER (a leap of 5 or more, one highest note, at most 2 scale steps in a row, at most 1
   repeat). *Missing*: the "typical contour + rare detail" test, set-wide head distance (o24 fix 3).
9. **Tender section**: lyrical second themes, the piano's ballad feels, solo vibrato. *Missing*: meno mosso per
   section (tempo is fixed: code review C10), portamento (TECH "not built").
10. **Performance**: `expressive.py` (KTH charge, `phrase_arch`, `final_ritard`, `punctuation`, correlated `rho`),
    the orchestra's `ensemble` tables, the piano's `inhale` / rubato / lilt. *Check*: the tutti onset spread at the
    summit (the masterpiece gap's #10), and add a pre-summit broadening to the orchestra.

---

## References

DOIs marked † were not re-checked online for this review; the citation itself was confirmed through a search, a
repository record or a secondary source. The other DOIs or links were seen in the search results.

- Bannister, S. (2020). A survey into the experience of musically induced chills: Emotions, situations and music.
  *Psychology of Music* 48(2), 297-314. [Record](https://durham-repository.worktribe.com/output/1347620/a-survey-into-the-experience-of-musically-induced-chills-emotions-situations-and-music)
- Bannister, S. (2020). A vigilance explanation of musical chills? Effects of loudness and brightness manipulations.
  *Music & Science*. [Record](https://sage.figshare.com/collections/A_Vigilance_Explanation_of_Musical_Chills_Effects_of_Loudness_and_Brightness_Manipulations/4933161)
- Bannister, S. (2020). *A Framework of Distinct Musical Chills* (PhD thesis, Durham). [Record](https://etheses.durham.ac.uk/id/eprint/13582)
- Bannister, S., & Eerola, T. (2018). Suppressing the chills. *Frontiers in Psychology* 9:2046. [doi:10.3389/fpsyg.2018.02046](https://doi.org/10.3389/fpsyg.2018.02046)
- Berlyne, D. E. (1971). *Aesthetics and Psychobiology*. Appleton-Century-Crofts.
- Bhatara, A., Tirovolas, A. K., Duan, L. M., Levy, B., & Levitin, D. J. (2011). Perception of emotional expression in
  musical performance. *Journal of Experimental Psychology: Human Perception and Performance* 37, 921-934. [doi:10.1037/a0021922](https://doi.org/10.1037/a0021922)†
- Blood, A. J., & Zatorre, R. J. (2001). Intensely pleasurable responses to music correlate with activity in brain
  regions implicated in reward and emotion. *PNAS* 98(20), 11818-11823. [doi:10.1073/pnas.191355898](https://doi.org/10.1073/pnas.191355898)
- Burgoyne, J. A., Bountouridis, D., Van Balen, J., & Honing, H. (2013). Hooked: A game for discovering what makes
  music catchy. *ISMIR*. [PDF](https://archives.ismir.net/ismir2013/paper/000101.pdf)
- Chapin, H., Jantzen, K., Kelso, J. A. S., Steinberg, F., & Large, E. (2010). Dynamic emotional and neural responses
  to music depend on performance expression and listener experience. *PLOS ONE* 5(12):e13812. [doi:10.1371/journal.pone.0013812](https://doi.org/10.1371/journal.pone.0013812)
- Cheung, V. K. M., Harrison, P. M. C., Meyer, L., Pearce, M. T., Haynes, J.-D., & Koelsch, S. (2019). Uncertainty
  and surprise jointly predict musical pleasure and amygdala, hippocampus, and auditory cortex activity. *Current
  Biology* 29(23), 4084-4092. [doi:10.1016/j.cub.2019.09.067](https://doi.org/10.1016/j.cub.2019.09.067)
- Chmiel, A., & Schubert, E. (2017). Back to the inverted-U for music preference: A review of the literature.
  *Psychology of Music* 45(6), 886-909. [Record](https://researchers.westernsydney.edu.au/en/publications/back-to-the-inverted-u-for-music-preference-a-review-of-the-liter/)
- Cook, N. (1987). The perception of large-scale tonal closure. *Music Perception* 5(2), 197-205. [doi:10.2307/40285392](https://doi.org/10.2307/40285392)†
- de Fleurian, R., & Pearce, M. T. (2021). Chills in music: A systematic review. *Psychological Bulletin* 147(9),
  890-920. [doi:10.1037/bul0000341](https://doi.org/10.1037/bul0000341)
- de Fleurian, R., & Pearce, M. T. (2021b). The relationship between valence and chills in music: A corpus
  analysis. *i-Perception*. [DOAJ](https://doaj.org/article/7c30c521a2214a22a9e6c8d3dd069773)
- de Fleurian, R., Clemente, A., Benetos, E., & Pearce, M. T. (2024). Melodic expectation as an elicitor of
  music-evoked chills. *bioRxiv*. [doi:10.1101/2024.10.02.616280](https://doi.org/10.1101/2024.10.02.616280)
- Eerola, T., Vuoskoski, J. K., Peltola, H.-R., Putkinen, V., & Schäfer, K. (2018). An integrative review of the
  enjoyment of sadness associated with music. *Physics of Life Reviews* 25, 100-121. [doi:10.1016/j.plrev.2017.11.016](https://doi.org/10.1016/j.plrev.2017.11.016)
- Egermann, H., Pearce, M. T., Wiggins, G. A., & McAdams, S. (2013). Probabilistic models of expectation violation
  predict psychophysiological emotional responses to live concert music. *Cognitive, Affective, & Behavioral
  Neuroscience* 13(3), 533-553. [doi:10.3758/s13415-013-0161-y](https://doi.org/10.3758/s13415-013-0161-y)
- Eitan, Z. (1997). *Highpoints: A Study of Melodic Peaks*. University of Pennsylvania Press.
- Farbood, M. M. (2012). A parametric, temporal model of musical tension. *Music Perception* 29(4), 387-428. [doi:10.1525/mp.2012.29.4.387](https://doi.org/10.1525/mp.2012.29.4.387)
- Ferreri, L., Mas-Herrero, E., Zatorre, R. J., et al. (2019). Dopamine modulates the reward experiences elicited by
  music. *PNAS* 116(9), 3793-3798. [doi:10.1073/pnas.1811878116](https://doi.org/10.1073/pnas.1811878116)
- Friberg, A., Bresin, R., & Sundberg, J. (2006). Overview of the KTH rule system for musical performance. *Advances
  in Cognitive Psychology* 2(2-3), 145-161. [doi:10.2478/v10053-008-0052-x](https://doi.org/10.2478/v10053-008-0052-x)
- Gold, B. P., Pearce, M. T., Mas-Herrero, E., Dagher, A., & Zatorre, R. J. (2019). Predictability and uncertainty in
  the pleasure of music: A reward for learning? *Journal of Neuroscience* 39(47), 9397-9409. [doi:10.1523/JNEUROSCI.0428-19.2019](https://doi.org/10.1523/JNEUROSCI.0428-19.2019)
- Goodchild, M., Wild, J., & McAdams, S. (2019). Exploring emotional responses to orchestral gestures. *Musicae
  Scientiae* 23(1), 25-49. [Record](https://sonicfield.org/library/exploring-emotional-responses-to-orchestral-gestures)†
- Granot, R. Y., & Jacoby, N. (2011). Musically puzzling I: Sensitivity to overall structure in the sonata form?
  *Musicae Scientiae* 15(3), 365-386. [Record](https://cris.huji.ac.il/en/publications/musically-puzzling-i-sensitivity-to-overall-structure-in-the-sona/)
- Grewe, O., Nagel, F., Kopiez, R., & Altenmüller, E. (2007). Listening to music as a re-creative process:
  Physiological, psychological, and psychoacoustical correlates of chills and strong emotions. *Music Perception*
  24(3), 297-314. [doi:10.1525/mp.2007.24.3.297](https://doi.org/10.1525/mp.2007.24.3.297)†
- Grewe, O., Kopiez, R., & Altenmüller, E. (2009). The chill parameter: Goose bumps and shivers as promising measures
  in emotion research. *Music Perception* 27(1), 61-74. [doi:10.1525/mp.2009.27.1.61](https://doi.org/10.1525/mp.2009.27.1.61)†
- Guhn, M., Hamm, A., & Zentner, M. (2007). Physiological and musico-acoustic correlates of the chill response.
  *Music Perception* 24(5), 473-484. [doi:10.1525/mp.2007.24.5.473](https://doi.org/10.1525/mp.2007.24.5.473)
- Harrison, L., & Loui, P. (2014). Thrills, chills, frissons, and skin orgasms. *Frontiers in Psychology* 5:790. [doi:10.3389/fpsyg.2014.00790](https://doi.org/10.3389/fpsyg.2014.00790)
- Howat, R. (1983). *Debussy in Proportion*. Cambridge University Press.
- Huron, D. (1996). The melodic arch in Western folksongs. *Computing in Musicology* 10, 3-23.
- Huron, D. (2006). *Sweet Anticipation: Music and the Psychology of Expectation*. MIT Press.
- Huron, D. (2013). A psychological approach to musical form: The habituation-fluency theory of repetition. *Current
  Musicology* 96, 7-35. [doi:10.7916/cm.v0i96.5312](https://doi.org/10.7916/cm.v0i96.5312)
- Huron, D., Anderson, N., & Shanahan, D. (2014). "You can't play a sad song on the banjo". *Empirical Musicology
  Review* 9(1). [Article](https://www.osu.tests.sfulib4.publicknowledgeproject.org/index.php/EMR/article/view/4085)
- Huron, D., & Margulis, E. H. (2010). Musical expectancy and thrills. In P. N. Juslin & J. A. Sloboda (Eds.),
  *Handbook of Music and Emotion*. Oxford University Press.
- Jakubowski, K., Finkel, S., Stewart, L., & Müllensiefen, D. (2017). Dissecting an earworm. *Psychology of
  Aesthetics, Creativity, and the Arts* 11(2), 122-135. [doi:10.1037/aca0000090](https://doi.org/10.1037/aca0000090)
- Juslin, P. N. (2013). From everyday emotions to aesthetic emotions: Towards a unified theory of musical emotions.
  *Physics of Life Reviews* 10, 235-266. [doi:10.1016/j.plrev.2013.05.008](https://doi.org/10.1016/j.plrev.2013.05.008)†
- Juslin, P. N. (2019). *Musical Emotions Explained*. Oxford University Press.
- Juslin, P. N., & Laukka, P. (2003). Communication of emotions in vocal expression and music performance: Different
  channels, same code? *Psychological Bulletin* 129(5), 770-814. [doi:10.1037/0033-2909.129.5.770](https://doi.org/10.1037/0033-2909.129.5.770)
- Juslin, P. N., & Laukka, P. (2004). Expression, perception, and induction of musical emotions. *Journal of New Music
  Research* 33(3), 217-238. [doi:10.1080/0929821042000317813](https://doi.org/10.1080/0929821042000317813)
- Juslin, P. N., & Västfjäll, D. (2008). Emotional responses to music: The need to consider underlying mechanisms.
  *Behavioral and Brain Sciences* 31(5), 559-575. [PubMed](https://pubmed.ncbi.nlm.nih.gov/18826699/)
- Korsakova-Kreyn, M., & Dowling, W. J. (2014). Emotional processing in music: Study in affective responses to tonal
  modulation in controlled harmonic progressions and real music. *Psychomusicology* 24(1), 4-20. [PDF](https://labs.utdallas.edu/mpac/files/2021/03/2014-2.pdf)†
- Lerdahl, F. (2001). *Tonal Pitch Space*. Oxford University Press.
- Lerdahl, F., & Krumhansl, C. L. (2007). Modeling tonal tension. *Music Perception* 24(4), 329-366. [doi:10.1525/mp.2007.24.4.329](https://doi.org/10.1525/mp.2007.24.4.329)†
- Margulis, E. H. (2013). Aesthetic responses to repetition in unfamiliar music. *Empirical Studies of the Arts* 31(1),
  45-57. [Record](https://collaborate.princeton.edu/en/publications/aesthetic-responses-to-repetition-in-unfamiliar-music/)
- Margulis, E. H. (2014). *On Repeat: How Music Plays the Mind*. Oxford University Press.
- Menninghaus, W., et al. (2015). Towards a psychological construct of being moved. *PLOS ONE* 10(6):e0128451. [doi:10.1371/journal.pone.0128451](https://doi.org/10.1371/journal.pone.0128451)
- Meyer, L. B. (1956). *Emotion and Meaning in Music*. University of Chicago Press.
- Mori, K., & Iwanaga, M. (2017). Two types of peak emotional responses to music: The psychophysiology of chills and
  tears. *Scientific Reports* 7:46063. [doi:10.1038/srep46063](https://doi.org/10.1038/srep46063)
- Müllensiefen, D., & Halpern, A. R. (2014). The role of features and context in recognition of novel melodies.
  *Music Perception* 31(5), 418-435. [Record](https://research.gold.ac.uk/id/eprint/10838)
- Nagel, F., Kopiez, R., Grewe, O., & Altenmüller, E. (2008). Psychoacoustical correlates of musically induced chills.
  *Musicae Scientiae* 12(1), 101-113. [Record](https://jyx.jyu.fi/handle/123456789/19439)
- Panksepp, J. (1995). The emotional sources of "chills" induced by music. *Music Perception* 13(2), 171-207. [doi:10.2307/40285693](https://doi.org/10.2307/40285693)†
- Pearce, M. T. (2018). Statistical learning and probabilistic prediction in music cognition: Mechanisms of
  stylistic enculturation. *Annals of the NYAS* 1423, 378-395. [doi:10.1111/nyas.13654](https://doi.org/10.1111/nyas.13654)
- Repp, B. H. (1992). Diversity and commonality in music performance: An analysis of timing microstructure in
  Schumann's "Träumerei". *JASA* 92(5), 2546-2568. [doi:10.1121/1.404425](https://doi.org/10.1121/1.404425)†
- Repp, B. H. (1997). The aesthetic quality of a quantitatively average music performance. *Music Perception* 14(4),
  419-444.
- Rozin, A., Rozin, P., & Goldberg, E. (2004). The feeling of music past: How listeners remember musical affect.
  *Music Perception* 22(1), 15-39. [doi:10.1525/mp.2004.22.1.15](https://doi.org/10.1525/mp.2004.22.1.15)†
- Sachs, M. E., Damasio, A., & Habibi, A. (2015). The pleasures of sad music: A systematic review. *Frontiers in Human
  Neuroscience* 9:404. [doi:10.3389/fnhum.2015.00404](https://doi.org/10.3389/fnhum.2015.00404)
- Salimpoor, V. N., Benovoy, M., Larcher, K., Dagher, A., & Zatorre, R. J. (2011). Anatomically distinct dopamine
  release during anticipation and experience of peak emotion to music. *Nature Neuroscience* 14, 257-262. [doi:10.1038/nn.2726](https://doi.org/10.1038/nn.2726)
- Sloboda, J. A. (1991). Music structure and emotional response: Some empirical findings. *Psychology of Music* 19(2),
  110-120. [doi:10.1177/0305735691192002](https://doi.org/10.1177/0305735691192002)†
- Solberg, R. T., & Dibben, N. (2019). Peak experiences with electronic dance music: Subjective experiences,
  physiological responses, and musical characteristics of the break routine. *Music Perception* 36(4), 371-389. [Record](https://eprints.whiterose.ac.uk/id/eprint/145911/)
- Solberg, R. T., & Jensenius, A. R. (2017). Pleasurable and intersubjectively embodied experiences of electronic
  dance music. *Empirical Musicology Review* 11(3-4).
- Steinbeis, N., Koelsch, S., & Sloboda, J. A. (2006). The role of harmonic expectancy violations in musical
  emotions. *Journal of Cognitive Neuroscience* 18(8), 1380-1393. [Preprint](https://stefan-koelsch.de/papers/Steinbeis%2BJOCN2006_inpress.pdf)
- Tillmann, B., & Bigand, E. (2004). The relative importance of local and global structures in music perception.
  *Journal of Aesthetics and Art Criticism* 62(2). [doi:10.1111/j.1540-594X.2004.00153.x](https://doi.org/10.1111/j.1540-594X.2004.00153.x)
- Todd, N. P. M. (1992). The dynamics of dynamics: A model of musical expression. *JASA* 91(6), 3540-3550. [doi:10.1121/1.402843](https://doi.org/10.1121/1.402843)†
- von Hippel, P., & Huron, D. (2000). Why do skips precede reversals? The effect of tessitura on melodic structure.
  *Music Perception* 18(1), 59-85.
- Vuoskoski, J. K., & Eerola, T. (2017). The pleasure evoked by sad music is mediated by feelings of being moved.
  *Frontiers in Psychology* 8:439. [doi:10.3389/fpsyg.2017.00439](https://doi.org/10.3389/fpsyg.2017.00439)
- Wöllner, C. (2013). How to quantify individuality in music performance? *Frontiers in Psychology* 4:361. [Article](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00361/full)
- Zickfeld, J. H., et al. (2020). Tears of joy, aesthetic chills and heartwarming feelings: Physiological correlates
  of kama muta. *Psychophysiology*. [Record](https://ciencia.iscte-iul.pt/publications/tears-of-joy-aesthetic-chills-and-heartwarming-feelings-physiological-correlates-of-kama-muta/83323?lang=en)
