# When the Year Turns Gold - A&R (roles/a-and-r.md)

# Round 2

Judged on build6 (.tmp/build6.log, the new out/report.json + images, the re-measured .tmp/measure.json, song.py at
bafd887), `mix` (findings: 1 warn `drums_too_quiet` A4 -17.7, deliberate; the piano info is gone; "moves": drums +1
only) and `master --check --platform dynamic` (all ok: -15.6 LUFS-I, TP -1.20 dBTP, LRA 6.5, corr 0.74). 0 clicks in
the mix, 0 clipped samples, 0 silent notes, `flat_dynamics` 0.

```
verdict: ship
summary: The same hushed songbook ballad, and now it ends like one: she lets the last "gold" go while the strings and
the harp are still sounding. The third A has its own turn, the half chorus speaks up, the top is a little more open,
and the new leaning on words and the whispered last line stay inside the calm.
```

No blocker, no major.

## Issue status (round 1 numbering)

1. The last note too long / too loud - **fixed** (was major). spectrogram_11_end.png: her C5 now stops at ~4:50.2 and
   the chord rings on alone for ~5.5 s; the level strip falls steadily instead of standing. Vocal RMS in 'end' -19.4
   -> -24.5 dBFS (about -22 while she sings: no longer her loudest section, 1 dB under A4), voice vs band +7.2 ->
   +2.0 dB over the section (~+4.5 while she sings = the bed 4-5 dB under her: inside the target); section loudness
   -16.9 -> -20.1 LUFS, so the song really closes down (LRA 6.0 -> 6.5); bands.png's "voice alone" signature is gone
   (space 'narrow' -> 'lush'). Remaining, minor: the note still sounds ~8.3 s in real time (build6: `4:41.8-8.3s
   'gold'`, the fermata stretches the one bar) against the 6-7 s asked for - with the diminuendo it reads as a held
   ending, not as a stuck one. Leave it.
2. One cadence six times - **improved, minor remains**. A3 now sings its own `a3` (line 2 lifted Bb-Ab-Bb down to
   Gb, the last line turned up and left open on Ab4 before the half chorus); A4's "gold turns gray" on even quarters.
   The cadence `F4 Gb4 | Ab4 Gb4 F4` now ends A2, A4 and both bridges (4x, was 6x). The bridge still closes on the A's
   cadence - a note for the next ballad, not for this one.
3. Vibrato / scoops - **fixed**. Vibrato median 12.4 -> 9.0 ct (p90 19.9 -> 15.0; nowhere-to-be 8.0), planned on 58
   notes (was 72) at 15.3 ct; scooped onsets 14 % -> 10 % (10 of 96; 3 planned, the rest the voicebank's own approach,
   median -60 ct). Still above nowhere-to-be's 3 %, far from jane-street's half; no further action.
4. Dark top - **improved, minor remains**: brilliance -3.9 -> -3.0, air -4.6 -> -3.7 dB vs the profile (shelf +3.2 dB
   at 6.3 kHz), presence 0.0, "no harshness". The check now only suggests +0.5 dB at 10 kHz. Warm by design; stop here.
5. Half chorus understated - **fixed**: Ai -15.8 -> -15.3 LUFS, short-term max -13.1 -> -12.6 (B2 keeps the song's
   max at -11.9), piano track peak -5.4 -> -3.4 dBFS.
6. Piano fills over her in A3 - **fixed**: -2.4 -> -4.9 dB (A4 -4.5), the `part_over_lead` info is gone.
7. Stereo extremes (wide, briefly phasey solo intro; verse 8 % wide) - **open, minor**, unchanged.
8. Words - **fixed**: "in the coat you used to hate, / like the year before" (no "liked, like"), "but I thought you
   knew" (no clash with the summer; a second plain line next to "I should have asked you to stay" - it suits the
   bridge, and the rest stays circled).
9. Legato /t/ elisions - **unchanged, watch only**: "that" -25.7, "out" -25.2, new "used" /d/ -28.6 dB ("used to":
   normal English); "but" is gone with the new line. Diction passes in all 8 takes (shortest "it's" /t/ 46 ms).
10. Housekeeping (2 masked violins II discontinuities at 3:40.269 / 3:48.277, -37 / -43 dBFS; cello SFZ second-filter
    warning) - **open, minor**, unchanged, inaudible in the mix.

## New in this build: the singer's expression - does it stay calm?

Yes. What the build lists (build6.log `singer` lines) and what it measures:
- **Back-phrasing**: one phrase per section starts +111..+175 ms late. Later, never earlier: vowels still 0 % early in
  every section, median +59.3 ms; P-centre +5.8 ms overall.
- **Messa di voce** on 10 words, 3.7-5.2 dB swells; emphasis on 2 words per A (*said*, *five*, *hate*, *lamps*,
  *gone*, *you*, *stay*, *gray*, *still*). Note levels p10-p90 3.3 -> 3.6 dB, gain lane -2.6..+1.3 dB (was
  -1.3..+1.2), soft share 100 % -> 96.9 %, power 0 %: leaning, not pushing.
- **Ornaments**: 5 in the whole song (anticipation 'used', 'asked'; grace 'letters', 'gray'; a run on 'away'), none in
  the verse, A1, B or A3, two in the last A. Leaps of a 4th+ still 1 (150 intervals, mean 1.77 st), 0 % at/above D5.
- **The intimate line** "(( it's not far away ))" in A4: one line, the right one.
- NEW [minor, watch] The run on "away" sits inside the whispered line - the one spot where two expressive devices
  stack (the word's hold shrank 4.4 -> 2.5 s). If the user says anything like "aufgeregt" / "verschnörkelt" about the
  last A, drop that run first (`ornament` off for A4's last phrase). The two "anticipation" ornaments are the only
  moves that go ahead of the beat (P-centre B / B2 / A4 -0.4..-0.6 ms = on the beat, not early): fine at two per song,
  do not raise `amount`.

## Calm / laid back / dry / in the band - round 2 numbers

| question | build6 | round 1 (build4) | verdict |
|---|---|---|---|
| (1) calm vs agitated | 0.0 % at/above D5, 1 leap of a 4th+ in 150 intervals (mean 1.77 st); soft mode 96.9 % / power 0 %; scooped onsets 10 % (median -60 ct); vibrato median 9.0 ct at 5.6 Hz (p90 15.0); 0 falls / doits; note levels 3.6 dB; 5 ornaments | soft 100 %, scooped 14 %, vibrato 12.4 ct (p90 19.9), 3.3 dB | **calm** (calmer in pitch, a little more alive in level) |
| (2) rushed vs laid back | vowels median +59.3 ms (p10 +56.5, p90 +78.0), 0 % early in every section; phrase starts +78 ms, one back-phrased phrase per section +111..+175 ms; consonant lead 108 ms -> P-centre +5.8 ms (verse +6.0, A1 +10.6, A2 +16.5, B -0.4, A3 +10.1, B2 -0.6, A4 -0.5, tag +24.0); 1.03 syllables/s, median step 516 ms, 1.43 s rests | +58.7 ms, P-centre +5.6 ms | **laid back** |
| (3) wet vs dry | returns 20.2 LU under the dry voice (her plate only), no echo, no throws; 30 dB down 0.1 s after a phrase end (wet -33.9 dB at 250 ms, -51.1 at 500 ms) | 20.1 LU, 0.2 s | **dry** |
| (4) vocal vs band | within +0.7..-1.2 dB of the band's sum in every refrain section, +4.9 over the lone piano in the verse, +2.0 in 'end' | +7.2 in 'end' | **in the band, everywhere** |

Vocal vs band per section (report nodes' section RMS, pre-master, unweighted, her rests included; `mix` K-weighted):

| section | vocal dBFS | all other parts | voice vs band | `mix`: bed / low / rhythm vs her |
|---|---|---|---|---|
| verse | -21.5 | -26.4 | +4.9 | comp -4.7 |
| A1 | -21.9 | -22.6 | +0.7 | - / -6.4 / -18.2 |
| A2 | -22.0 | -22.1 | +0.1 | -7.7 / -4.1 / -15.7 |
| B | -21.1 | -20.3 | -0.8 | -4.0 / -4.7 / -16.0 |
| A3 | -21.3 | -20.7 | -0.6 | -6.6 / -4.2 / -16.8 |
| B2 | -21.0 | -19.8 | -1.2 | -3.5 / -4.1 / -15.6 |
| A4 | -21.2 | -20.8 | -0.4 | -6.0 / -5.6 / -17.7 |
| tag | -22.9 | -22.9 | 0.0 | -6.8 / -5.7 / -16.7 |
| end | -24.5 | -26.5 | +2.0 | (not judged: she stops at 4:50) |

"vocal: intelligible (presence band owned), not buried, no harshness". Not on top anywhere, not buried in B / B2.

**Songbook feel**: intact and better finished. Arc verse -18.4 -> A1 -16.9 -> A2 -16.2 -> B -14.4 -> A3 -14.9 -> Ai
-15.3 -> B2 -13.2 (max) -> A4 -14.5 -> tag -17.1 -> end -20.1: the verse, the staircase of entries, the climax at the
second bridge, and now a true dying close. A3's open ending on Ab4 hands the tune to the violins instead of closing
before them - the half chorus now feels asked for. No swing. Originality: the two new lines ("in the coat you used to
hate", "but I thought you knew") quote nothing; the round-1 judgement on melody / harmony / form stands.

## HUMAN_FEEDBACK checklist (the brief's)

- [x] CALM, not "aufgeregt": soft 96.9 %, 0 % >= D5, 1 leap, vibrato 9.0 ct, scooped 10 %, no falls; the expression
      features stay small (5 ornaments, swells <= 5.2 dB).
- [x] LAID BACK, not "gerusht": P-centre +5.8 ms, vowels +59 ms, 0 % early, back-phrasing only later, 1.03 syll/s.
- [x] DRY and close: returns 20.2 LU under her, no echo, no throws, tail gone in 0.1 s.
- [x] The voice IN the band, not on top: +0.7..-1.2 dB vs the band in the refrain, the last note 2.5 dB back and
      ended before the chord.
- [x] NO swing.
- [x] A song, not a loop: verse + AABA + half chorus + bridge + turned last A + tag + fermata; A1 / A2 / A3 / A4 now
      four different endings.
- [x] Real dynamics: `flat_dynamics` 0 (vocal 18.0 dB onsets / 6.0 dB vowel levels, piano 10.4, comp 11.4, bass 8.5,
      violins I 7.0, violins II 5.8).
- [x] Played, not keyboard-like (as round 1, plus back-phrasing, messa di voce, emphasis).
- [x] Warm piano, fast two-key figures budgeted (none reported).
- [x] Jazz drums soft: brushes -15.6..-18.2 dB under her (the brief: >= 15; `drums_too_quiet` A4 acknowledged).
- [x] No doublers on any acoustic solo instrument.
- [x] Diction passes (8 takes, no `coda_short` / `coda_buried`); out/lyrics.txt to send along - check that it carries
      the two new lines before sending.
- [x] 0 clicks (mix), 0 clipped samples, true peak -1.20 dBTP, 0 silent notes.
- [x] "Does it feel like a classic songbook ballad?": yes, including the ending.
- [x] Brief targets: -15.6 LUFS-I (-16..-13), LRA 6.5 (>= 6), 4:59, bed -3.5..-7.7 dB under her, bass -4.1..-6.4.

## Keep

Everything listed under round 1's Keep, plus: the one-bar last "gold" with the vocal's `end -2.5` and the strings'
`end +3` (the chord outlasting her), A3's open ending, the vibrato settings (`vib_ct=13`, `vib_min_s=1.1`,
`model_vib=0.35`), `ORN_EARLY = dict(amount=0.12)` and exactly one intimate line. Do not add ornaments or emphasis
beyond this - the calm is the product.

Hand-over to the producer: ship. Open minors (7 intro stereo, 10 violins II discontinuities / cello SFZ, 2 the
bridge's cadence, 1 the 8.3 s note, the run on "away") are optional and must not delay delivery.

Producer follow-up (build7, after merging master): issue 1's remaining minor done - the last "gold" is `C5/2. r/4`
(three beats into the fermata): mic pull `4:41.8-6.0s` (was 8.3 s), she stops at ~4:47.9 and the chord rings on ~8 s;
vocal RMS in 'end' -24.5 -> -25.7 dBFS, 'end' -20.6 LUFS, LRA 6.7, -15.6 LUFS-I, TP -1.20 dBTP; 0 clicks in the mix,
0 silent notes, `flat_dynamics` 0. The merged `mix` now judges Ai / end with violins2 as the lead (she is out there):
its Ai / end warnings are that role choice, not a change - balance kept as A&R asked.

---

# Round 1

Judged on the final build (.tmp/build4.log, out/report.json, the images, .tmp/measure.json), plus
`python -m agentsound mix` (findings: 1 warn `drums_too_quiet` A4, 1 info `part_over_lead` piano A3) and
`master --check --platform dynamic` (all ok: -15.5 LUFS-I, TP -1.20 dBTP, LRA 6.0, corr 0.74). No reference for this
idiom exists in the repo: `compare` skipped. 0 clicks in the mix, 0 clipped samples, 0 silent notes, `flat_dynamics` 0.

```
verdict: revise
summary: A real songbook ballad - a rubato verse over the piano, a slow refrain with a tune one can hum, strings
that come in late and swell at the bridge, and she sings low, soft and unhurried inside the band. Only the very end
breaks the spell: the last "gold" is held for about 13 seconds, louder than she sang anywhere else, over a band that
has almost gone.
```

One major, cheap to fix (the last two bars). Everything else is minor; nothing else needs touching before delivery.

## Issues (most severe first)

1. [major] The last note is too long and too loud against the band - the one place where the user's last sentence
   ("die Stimme im Vergleich zum Rest zu laut") comes back. build4.log: `mic pull 4:41.8-13.4s 'gold'`;
   spectrogram_11_end.png: her C5 (523 Hz and its harmonics, even vibrato) runs unbroken from 4:41.5 to 4:55 at a
   nearly flat level (the level strip does not fall until the last second). report nodes, section 'end': vocal RMS
   -19.4 dBFS = her LOUDEST section (sung sections -21.1..-22.9), everything else together -26.6 dBFS -> the voice
   ~7 dB over the whole band (`mix`: bed -8.9); bands.png 'end': mid +9.6, lowmid +8.3, presence +5.9 dB vs the
   profile = the voice alone. Everywhere else she sits within +-1.5 dB of the band. A singer holds a last note 5-7 s
   and lets it die with the chord; 13 s of a steady synthetic vowel is exactly the long exposed moment where the
   voicebank stops sounding like a person.
   owner: arranger (length) + mix-engineer (level)
   fix: hold the last "gold" 6-7 s in real time (one bar + the fermata instead of `C5/1~ | C5/1` under `hold=3`, or a
   smaller `hold`), let her diminuendo with the strings (a deeper final taper / mic pull ~-8 dB over the note, or
   `MIX ride vocal end -2.5`), keep the strings' `end +3`. Target: vocal in 'end' no louder than in A4 (-21 dBFS RMS),
   bed -4..-6 dB under her, the chord outlasting the voice by 2-3 s. Re-check spectrogram_11_end.png and `mix` 'end'.

2. [minor] The tune has one cadence and uses it six times. song.py: A3 sings `VOX('a2')` note for note (only the
   take differs), A1 differs from A2 only in its last two bars, A4 only in bars 3-4; line 3 (`C5 Bb4 G4 Ab4 | Bb4`)
   is identical in all four As, and the closing figure `F4 Gb4 | Ab4 Gb4 F4~` ends A2, A3, A4 AND both bridges
   ("like the year before" / "but the year was new" / "till the light is gone" / "it's not far away"). Same tune in
   every A is the AABA idiom; the bridge ending on the A's cadence is not - it gives away the bridge's contrast, and
   every section of the refrain lands on the same held F4. Over 5 minutes at 62 BPM that reads a little static.
   owner: arranger   fix (optional here, a rule for the next ballad): let the bridge end open - line 4 up to Ab4 / Bb4
   over Ab7sus4 instead of the A cadence; give A3 one displaced or lifted note in line 3 (e.g. "bench" on Db5 -> C5).

3. [minor] Vibrato and scoops are the least calm numbers of the take - still calm, but above the approved
   nowhere-to-be: vibrato median 12.4 ct at 5.6 Hz (p90 19.9; nowhere-to-be 8.0 ct at 5.2 Hz; the planner put vibrato
   on 72 of 172 notes at a 20.8 ct mean), scooped onsets 14 % (14 of 99, median -62 ct, p10 -118 ct; nowhere-to-be
   3 %; jane-street "aufgeregt": half the openers, -82 ct). Only 7 scoops were planned (31 ct): the other half is the
   voicebank's own approach on the slow notes. Not agitated (soft mode 100 %, no leaps, 3.3 dB note levels) - a
   watch item, and it compounds with issue 1 (13 s of that vibrato alone).
   owner: sound-designer   fix: vibrato depth x0.7 and only on notes >= 1.2 s (`ballad` at 62 BPM makes almost every
   note "long"); nothing if the user does not react.

4. [minor] The mix is dark on top: brilliance -3.9, air -4.6 dB vs the jazz profile (bands.png: A4 air -6.6,
   Ai brilliance -5.5), sub +2.0. Warm is the brief, and the user has complained about "hart", never about dull - but
   on a phone speaker the brushes (18 LU under the mix, -42..-44 dBFS RMS) and the strings' sheen are mostly gone.
   owner: mastering-engineer   fix: the check's own +0.9 dB shelf at 6.3 kHz / -0.6 dB at 630 Hz; no more.

5. [minor] The instrumental half chorus is understated: the tune drops ~5 dB when she hands over (violins I + II in
   octaves ~-27 dBFS RMS together, the piano's second half -29 section RMS, vs her -21..-22), under a bass at -23.7;
   `mix` cannot judge Ai ("no lead"). It reads as an interlude rather than "the piano sings". Fine for a breather
   before the climax, but the piano half is the Beegie-Adair moment of the song and could be 1.5-2 dB prouder.
   owner: mix-engineer   fix: `ride piano Ai +2`, violins I / II `Ai +1.5` in bars 43-46.

6. [minor] Piano fills -2.4 dB vs her in A3 and -3.8 in A4 (`mix` info, limit -4): they answer in her rests (song.py
   FILLS `@6`, `@14`, `@30`), so they do not cover a word; A3's are the loudest thing between her lines.
   owner: mix-engineer   fix: `ride piano A3 -1.5` (not the global -2 trim: Ai needs the piano).

7. [minor] Stereo extremes: the solo piano intro is wide and briefly out of phase (corr 0.27, width 58 %, a red dip at
   ~0:09; the 'plate' return reads corr -0.19 / 147 %), then the verse collapses to 8 % width ("narrow") and the end
   to 6 %. Mono sum only 0.6 dB down overall, so no phone problem; the jump intro -> verse is audible on headphones.
   owner: mix-engineer / mastering-engineer   fix: master width x1.0 for the intro, or narrow the band plate return.

8. [minor] Words: "in the coat you never liked, / like the year before" puts "liked, like" back to back, and three
   similes open with "like" (verse, A2, bridge). "but the year was new" sits oddly beside a verse in which he left with
   the summer (a year that is new in summer?) - it reads as "we were new", but it makes the listener stop.
   owner: lyricist   fix (next revision only if the song is touched anyway): "in the coat you never liked, / same as
   the year before"; leave the bridge - it is the best couplet of the song.

9. [minor] Legato word-final /t/ nearly silent in the 2-8 kHz band (measure.json codas): "but" -30.5 / -31.5 dB,
   "that" -27.4, "at" -27.8, "out" -27.4 ("out by the gate" - the word of "out verliert sein t"), "gold" /d/ before
   "turns" -26.2. All run into the next consonant (natural elision); every phrase-final coda is clearly there
   ("gate" +38 / +24, "liked" +24, "said" +32, "red" +33) and the build's diction lines pass in all 8 takes (shortest
   'turns' /n/ 46 ms). Watch item.
   owner: producer   fix: none; if the user hears "ou' by the gate", give "out" a 40 ms gap.

10. [minor] Housekeeping: 2 masked sample discontinuities inside violins II (3:40.269 -37 dBFS, 3:48.277 -43 dBFS;
    click_01.png: nothing visible in the mix trace - the mix sits at -6 dBFS there) - voice overlaps of the octave
    line in B2; the cello patch reports unplayed SFZ second-filter opcodes (build warning).
    owner: sound-designer   fix: a 5 ms release / a small gap between touching violins II notes in B2; TODO.md entry
    for the Celli KS second filter if not there yet.

## Calm / laid back / dry / in the band - judged from the numbers

| question | this build | nowhere-to-be (shipped) | jane-street "aufgeregt / gerusht" | verdict |
|---|---|---|---|---|
| (1) calm vs agitated | 0.0 % at/above D5 (top Db5 twice), 0 notes >= G5, 1 leap of a 4th+ in 142 intervals (mean 1.77 st); soft mode 100 % / power 0 %; scooped onsets 14 % (median -62 ct); vibrato median 12.4 ct at 5.6 Hz (p90 19.9); 0 falls / doits; gain lane -1.3..+1.2 dB, note levels p10-p90 3.3 dB | 0.9 % >= D5, 0 leaps, 3 % scooped, vibrato 8.0 ct | 1/3 >= D5, 11 leaps per chorus, half the openers scooped, +-21 ct | **calm** (vibrato / scoops: issue 3) |
| (2) rushed vs laid back | 62 BPM; vowels median +58.7 ms behind the beat (p10 +56.5, p90 +76.9), **0 % early** overall and in every section; phrase starts +77.7 ms; consonants lead 105.5 ms -> P-centre +5.6 ms (per section verse +4.9, A1 +11.0, A2 +15.9, B +1.7, A3 +11.6, B2 +3.3, A4 +1.9, tag +24.1: never ahead); 1.03 syllables/s, median step 516 ms, 0 % of steps <= an 8th; 1.43 s rest between phrases | vowels +61 ms, P-centre +1.8 ms, 0.8 syll/s | syllables ~20 ms AHEAD, 62 % 8th steps at 126 BPM | **laid back** - no syllable is early at this tempo |
| (3) wet vs dry | returns 20.1 LU under the dry voice (one bus: her own plate, send -25 dB; she is in neither the room nor the strings' hall); no echo, no throws; 30 dB down 0.2 s after a phrase end (wet -34.9 dB at 250 ms, -49.4 at 500 ms). The mix reads "lush" (-15.8 LU) from the strings' hall and the band chamber - around her, not on her | 20.5 LU, 0.1 s | plate -12 + echo -20 + throws | **dry** |
| (4) vocal vs band | see the table below: within +-1.5 dB of the band's sum in every refrain section, 5 dB over the lone piano in the verse, **+7 dB in 'end'** | - | - | **in the band**, except the last note (issue 1) |

Vocal vs band per section (report nodes' section RMS, pre-master, unweighted; the vocal's RMS includes her rests, so
while she sings she is ~2 dB further up; `mix` columns K-weighted vs the lead):

| section | vocal dBFS | all other parts summed | voice vs band | `mix`: bed / low / rhythm vs her | reading |
|---|---|---|---|---|---|
| verse | -21.4 | -26.5 (piano) | +5.1 | comp -4.8 | voice and piano: right for a rubato verse, the piano clearly there |
| A1 | -22.2 | -22.8 | +0.6 | - / -6.0 / -17.9 | in the band |
| A2 | -21.7 | -22.1 | +0.4 | -7.8 / -4.4 / -16.0 | in the band |
| B | -21.3 | -20.3 | -1.0 | -3.7 / -4.3 / -15.6 | the strings swell to her level - not buried (presence owned) |
| A3 | -22.0 | -20.6 | -1.4 | -5.7 / -3.4 / -16.1 | in the band (the fills in her gaps: issue 6) |
| B2 | -21.1 | -19.8 | -1.3 | -3.3 / -4.1 / -15.5 | the climax: band and voice level - the furthest "in" she goes; do not push the strings further |
| A4 | -21.1 | -20.9 | -0.2 | -6.0 / -5.5 / -17.6 | in the band |
| tag | -22.9 | -22.9 | 0.0 | -6.7 / -5.7 / -16.7 | in the band |
| end | **-19.4** | -26.6 | **+7.2** | -8.9 | on top, alone, 13 s: issue 1 |

Neither on top nor buried in the refrain: the build reports "vocal: intelligible (presence band owned), not buried,
no harshness". The -1.5 dB vocal trim did what the user asked for; going lower would start to bury her in B / B2.

## (5) Does it feel like a classic songbook ballad?

Yes. What carries it (song.py):
- A real **verse**: 8 bars out of time at 56 BPM in the relative minor (Bbm9 - Gbmaj9 - Ebm9 - F7sus - ... - Ab7sus
  with a fermata), voice + rolled piano + left-hand roots, then "a tempo" into the refrain. loudness.png: verse -18.3
  -> A1 -17.1 -> A2 -16.2 -> B -14.5 -> A3 -15.0 -> Ai -15.8 -> B2 -13.1 (the max, short-term -11.6) -> A4 -14.4 ->
  tag -17.1: a clear arc with the climax at the second bridge.
- A 32-bar **AABA** with the title as the first line of every A - the hook F-Gb-Ab-Bb up to "gold" on C5, the major
  7th of Dbmaj9, a songbook colour in itself - then the half chorus (strings in octaves 4 bars, harmonized piano 4
  bars), "take it from the bridge", a turned last A (Db5 on "gold turns gray"), a deceptive Fm7 - E°7 into the tag.
- **Harmony**: I - VI7b9 - ii9 - V13/b9 - iii - biii°7 - ii, a different turnaround for every A (backdoor Gbm6 - Cb9,
  Bm7 - E7b9 into the bridge, home, deceptive), the bridge in bVI (A major) and back through C7b9 - Fm9 - Bb13 - Ebm9
  - Ab7sus; "stay" on Db5 = the #9 of Bb7 in B2. Last chord Dbmaj9#11.
- **Orchestration by stages**: piano alone -> + voice -> + bass and brushes (A1) -> strings pp (A2) -> swell (B) ->
  full strings in octaves, cello counter-line, harp gliss (B2) -> settle. tracks.png shows exactly that staircase.
- Word painting: "Leaves come down like letters" falls down the A-major scale.

What is thin, static or un-idiomatic: the six-fold cadence and the literal A3 (issue 2), the understated half chorus
(issue 5), and the ending (issue 1 - the held last note is idiomatic, its length and level are not). No swing anywhere
(Feel ratio 0.5, `straight=True` on bass and brushes, rubato / ritardando only).

## (6) Lyrics (roles/lyricist.md, HUMAN_FEEDBACK lyric rules)

- **Circled, not named**: yes. Neither "autumn", "wait", "lonely" nor "miss" is sung; the season and the waiting are
  things - the early train, sandals left in the hall, streets putting on coats, the ferry gate at five, the coat he
  never liked, the bench, the lamps. One deliberate direct line, at the melody's climb: "I should have asked you to
  stay".
- **Quotable lines** (3): "Summer took the early train", "Leaves come down like letters, none of them from you",
  "and the gold turns gray". The hook is sung 6 times (4 As + the tag twice) and turned once.
- **Sparse**: 5-7 syllables per 2-bar line, 172 syllables in 5 minutes, every line ends on a long open vowel or voiced
  coda and is followed by a rest.
- **Originality**: nothing quotes or paraphrases "Autumn in New York" (no New York, no skyline / crowds / canyons of
  steel, no "why does it seem so inviting", no first-night image; a different story - a kept date, not a love letter
  to a city). Nearest neighbour in the repertoire is the generic autumn palette - leaves, red, gold ("Autumn Leaves"
  has "red and gold") - but no line, rhyme pair or title phrase is taken; "the year turns gold" and "leaves ... like
  letters" are the song's own. lyrics.txt is in out/ to send along.
- Weak spots: issue 8.

**Melody / harmony / form vs the standard** (as far as it can be reasoned): the standard is in a different form (no
AABA with a modulating bridge; its refrain wanders through several keys and closes in minor), opens over rising
parallel chords from ii, and its tune is built on a leaping, sequenced motif. Here: AABA in Db, the A on a static
tonic then I - VI7 - ii - V, a stepwise scale hook to the major 7th, a bridge in bVI, a major #11 close. Shared: only
the idiom (verse + refrain, ii-V chains, strings, a held ending). No objection.

## (7) Diction, clicks, peaks, silent notes, dynamics

- Diction: all 8 takes pass (12-18 word-final consonants sung each, shortest 'turns' /n/ 46 ms; no `coda_short` /
  `coda_buried`). Legato /t/ elisions: issue 9.
- Clicks: 0 in the mix; 2 masked in violins II (issue 10). Clipped samples 0. True peak -1.20 dBTP.
- Silent notes: 0 on every node. `flat_dynamics`: 0 - vocal 20.3 dB (onsets; vowel levels 6.1 dB p10-p90), piano
  9.7, comp 11.5, bass 8.5, violins I 7.0, violins II 6.0 (violas / cellos are beds, not judged).
- Mic pull: 37 held words pulled 2.8-5.7 dB, the user's own idea, on.

## HUMAN_FEEDBACK checklist (the brief's)

- [x] CALM, not "aufgeregt": `ballad`, soft mode 100 %, Db4-C5 + Db5 twice (0 % >= D5), 1 leap of a 4th+, no falls;
      scoops 14 % / vibrato 12.4 ct are the watch item (issue 3).
- [x] LAID BACK, not "gerusht": P-centre +5.6 ms (+1.7..+24 per section), vowels +59 ms, 0 % early, 1.03 syllables/s,
      1.43 s rests, 62 BPM.
- [x] DRY and close: returns 20.1 LU under her, no echo, no throws, tail gone in 0.2 s.
- [ ] The voice IN the band, not on top: yes in verse / refrain (+0.6..-1.4 dB vs the band), **no on the last note**
      (+7.2 dB for 13 s) - issue 1.
- [x] NO swing: straight / rubato everywhere.
- [x] A song, not a loop: verse + AABA + half chorus + bridge + turned last A + tag + fermata; the hook in every A.
      (Variation between the As is small: issue 2, minor.)
- [x] Real dynamics: `flat_dynamics` 0 (voice, piano, bass, strings).
- [x] Played, not keyboard-like: `singer.sing` (4 takes, breaths, releases, tapers, mic pulls), `jazz.comp` rolled
      16-34 ms with the pedal, `pianist.arrange` for intro / fills / half chorus, two-feel `walking_bass`, brush stirs,
      one `orch.Score` with a dynamics map (pp -> mf), harp gliss, `s.ending` with rit and `last_stir`.
- [x] Warm piano: the preset's soft hammers, no presence boost (presence +0.0, brilliance -3.9); fast two-key figures:
      one shared `pianist.Memory`, ballad budget - none reported by the build.
- [x] Jazz drums soft: brushes -15.5..-17.9 dB under her (softer than the profile's -13..-16 on purpose; the brief asks
      for >= 15). `mix` warn `drums_too_quiet` A4 acknowledged, not an issue.
- [x] No doublers on any acoustic solo instrument: the hero only on the voice (`drive=False`), piano and strings plain;
      violins I / II in octaves in Ai / B2 is orchestration, not a doubler.
- [x] Diction passes; lyrics.txt in out/.
- [x] 0 clicks (mix), 0 clipped samples, true peak -1.20 dBTP, 0 silent notes.
- [x] "Does it feel like a classic songbook ballad?": yes (section 5) - up to the last 13 seconds.
- [x] Brief targets: 62 BPM Db, 72 bars, 4:59 (brief ~4:50); -15.5 LUFS-I (-16..-13), LRA 6.0 (>= 6: exactly on the
      line), bed -3.3..-7.8 dB under her (brief: 2-4 dB in the bridge), bass -3.4..-6.0.

One unticked box = one major: `revise`.

## Keep

- The voice exactly as it is in the verse and refrain: Hanami `ballad`, soft mode only, `late_ms=58` /
  `late_first_ms=20` (0 % early at 62 BPM), `vel=(56, 84)`, the -1.5 dB trim, her own plate 20 LU under her, mic pull.
  Do not touch any of it while fixing the end.
- The verse (rubato, Bb minor, voice + piano + left-hand roots) and the staircase of entries (bass / brushes in A1,
  strings pp in A2, the swell in B, octaves + cello line + harp in B2).
- The hook to the major 7th, the four different turnarounds, the bridge in A major, "stay" on Db5 over Bb7#9, the
  turned last A, the deceptive cadence into the tag, the Dbmaj9#11.
- The balance of the refrain: strings -3.3 dB under her at the climax and no closer; brushes very soft.
- The loudness arc (verse -18.3 ... B2 -13.1 ... tag -17.1) and the master (-15.5 LUFS-I, TP -1.20).
- The cover (jazz style, gold label, "when the year turns gold") and the credits note: Hanami's vocoder is
  CC BY-NC-SA (non-commercial), the 224XL IRs unclear, Salamander / SSO need attribution - private listening fine.

Hand-over to the producer: fix issue 1 only (the last note's length and level), rebuild, re-check 'end' in `mix`,
spectrogram_11_end.png and the vocal's section RMS; issues 2-10 are optional and must not delay delivery.
