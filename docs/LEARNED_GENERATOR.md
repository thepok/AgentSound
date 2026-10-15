# The learned generator: lab notebook

**Question.** Can a transformer of about 30M parameters match the rule-based endless generators (its teachers) and
then exceed them, when it is trained only on what those generators compose? No human music data and no pretrained
weights are used.

**Short answer (2026-10-12, first run).**

- It matches them. With the same cheap lead-sheet checks the rule composer applies to its own drafts, the student
  scores within about 1 point of the teacher on every genre.
- On `composer.score` it exceeds them modestly. This takes score-filtered distillation, and the comparison must use
  matched inference compute: one piece against one piece, best-of-8 against best-of-8.
- In one small blind round the student pieces were mistaken for composed pieces 3 times out of 12. The teacher pieces
  were mistaken 0 times out of 12. This is suggestive but not significant.
- Raw sampling, with no check at all, is still clearly worse than the teacher.
- RL (GRPO on the score) made the raw policy more reliable, but did not raise the score of the pieces that pass.
- Embedding blends snap to the majority parent instead of interpolating.
- Phase 2 (section 12, 2026-10-13): with the players' arrangement as tokens, the student reproduces the teacher's
  arrangement and a spread set reaches variety 0.87. In a blind round of 8 pieces per source and 5 judges, both the
  student and the teacher were caught 40 of 40 times. The tells are the teacher's own template.
- Phase 3 (section 13, 2026-10-13): a warm start from base2 grows the vocabulary and the context in 40 % of a fresh
  run's steps. The student follows the widened teacher closely: score 96.6 against 96.1, the lowest tells so far. In
  blind round 3, 6 of 40 verdicts called a student piece composed and 4 of 40 a teacher piece (round 2: 0 and 0).
  Student and teacher stay indistinguishable from each other (p = 0.74).
- A set of samples is only as varied as the teacher's header distribution and chance make it. Forcing an even
  header spread per set (`--spread`) raises set variety from 0.63 to 0.72 at the same score. Header temperature
  does not help. The climax plan is the teacher's own invariant (section 10).

Details, numbers and the negative results follow.

Code: `agentsound/learn/` (`python -m agentsound learn ...`, the README section "Learned generator"). Data, checkpoints
and every eval file are outside git in `D:/agentsound-learn/` (`data/`, `runs/<name>/<tag>/report.json` +
`<genre>.jsonl`). Torch runs only in the CUDA venv `D:/venvs/agentsound-ears` (torch 2.14.1+cu126, Quadro RTX 5000
16 GB). The tokenizer, grammar, decoder, export and measures need no torch.

## 1. Token schema (composition level) - `learn/tokens.py`

One piece is one endless `Tune`: the composer's lead sheet, which is what the players get. The players still do the
left hand, voicings, ornaments, touch, rubato and pedal, so the tokens carry no velocities.

```
BOS
header   Mood_* Feel_* Form_* Meter_* Key_<tonic> Mode_* Tempo_<bpm> Swing_* Energy_<x1000>
plan     Dyn_* SoloShape_* Double_* Shout_* EndKind_* Second_* ReharmIn_*
         OutParts Part_* .. EndList   SoloCharts Part_* .. EndList
         Climax Part_* U_<unit> Bn_<bar> Pos_<12ths> P_<pitch>   |  Climax_none
         EndChord <chord>
arrange  Arr [ALayout_*] [ATouch_*] (ASec_<name> <key tokens>)* EndArr  |  Arr_none          schema 2 only (section 11)
harmony  H Part_<p> Blk_<progression/cadence block> .. (<chord> L_<12ths>)* EndH      per head part, form order
         HIntro IKind_* ILine_* IAppr_* IFrame_* (<chord> L_*)* EndH | HIntro_none;  HTag ... the same
         HSolo Part_<p> (<chord> L_*)* EndH                                         the reharm per part
notes    M Part_<p> <bars> EndM           head melody per part
         MOut Part_<p> <bars> EndM        the out melody where it differs
         MIntro <bars> EndM   MTag <bars> EndM
         Motif (Ref_<src>_<n> | <bars> EndM)   Counter (Ref_<src>_<n> | Ref_none | <bars> EndM)
EOS
<chord> = Root_<roman> Q_<quality> [Bass_<roman>]
<bars>  = BarPre? (Bar (Pos_<12ths> P_<pitch - tonic pc> D_<12ths>)*)*
```

- **Roots as spelled roman numerals.** A root is written as the letter degree plus accidentals, measured from the
  tonic. Cb in Bb major is `bII`; Fb in G# minor is `bbbVII`. Chord symbols therefore come back letter-exact, and
  harmony is the same across keys.
- **Pitches relative to the tonic.** The register is kept, and a transposed copy reads as a copy.
- **Times** sit on a 1/12-beat grid (8ths, 16ths and triplets).
- **Plan levels** are not tokens. `tokens.levels_for` recomputes them as the composer does, from the form curve plus
  the energy.
- **Not tokenized:** the title (drawn again), the seed (the players' dice: `decode(seed=)`) and the composer's retry
  count.
- **Vocabulary:** 571 tokens. Pieces are 560-772 tokens on average per genre (max 1194). The context is 1152 tokens,
  which drops a handful of the longest pieces.
- **Round trip** (`tests/python/test_learn.py`): over 500 tunes (100 seeds x 5 genres), every tune -> tokens -> tune
  is note-identical at the composition level. That covers header, plan, every chord symbol, every melody / intro /
  tag / out / motif / counter note and the levels. The players then play bit-identical notes; this is tested on a
  new-age and a jazz tune.
- **Grammar** (`learn/grammar.py`): an incremental parser that gives the allowed next tokens, used for
  grammar-constrained decoding. It admits 5000 / 5000 teacher pieces.

## 2. Dataset - `learn/export.py`

| set | what | pieces | throughput |
|---|---|---|---|
| `data/tok` | seeds 4000-23999 x 5 genres: compose + the arc check, tokens only | 100,000 (80,278 pass the arc check, 55M tokens) | 87 pieces/s on 10 processes (19 min) |
| `data/full` | seeds 0-3999 x 5 genres: compose, the arc check, PERFORMED (no audio), the breath gate, `composer.score` + every `score_metrics` tell | 20,000 | 3.8 pieces/s (88 min; `score_metrics`' body measure compiles the song, ~60 % of the time) |

The base model trains on `data/tok`. `data/full` is the teacher's measured distribution: no model was trained on it
except the score-filtered fine-tunes. Teacher statistics from `data/full`:

| genre | pass every check | score mean (sd) | p10 | capped by a hard rule | best-of-8 mean |
|---|---|---|---|---|---|
| jazz-piano | 0.88 | 64.7 (32.1) | 24.6 | 0.37 | 92.6 |
| jazz-trio | 0.88 | 62.5 (33.0) | 24.4 | 0.40 | 92.6 |
| new-age-piano | 0.69 | 94.2 (2.6) | 90.8 | 0 | 97.1 |
| classical-piano | 0.88 | 95.4 (3.5) | 90.3 | 0 | 99.0 |
| lofi-piano | 0.53 | 98.8 (1.8) | 96.6 | 0 | 99.9 |

The best-of-8 column takes blocks of 8 consecutive seeds, each slot rolled freely, so it approximates the runner,
which pins one slot.

**Control: how much of the score belongs to the lead sheet at all?** I performed 24 teacher tunes per genre with 4
different player seeds each (`D:/agentsound-learn/pvar.log`).

| genre | score sd within a tune (players' dice) | sd between tunes |
|---|---|---|
| jazz-piano | 20.5 | 20.1 |
| new-age-piano | 1.4 | 2.1 |

For jazz, the score is mostly the soloist's dice: the hard caps `sil_cad` and `both_mid` come from the improvised
solo. A lead-sheet generator can only shift it statistically. New-age is the genre where the composition carries the
score, so the RL and the blind round use new-age.

## 3. Model and training - `learn/model.py`, `learn/train.py`

- **Model.** A decoder-only GPT: d=512, 10 layers, 8 heads, 4x MLP, learned positions, tied embeddings, dropout 0.1.
  **32.4M params.**
- **Conditioning.** A learned genre matrix (5 x 512). The conditioning vector (one-hot, or any blend weights) is added
  to every position and also fed as a soft prefix position. Mood, feel, form, key and tempo are sampled by the model
  after BOS, or forced by a prompt.
- **Training.** AdamW (3e-4, warmup 400, cosine to 10 %, wd 0.1), fp16 autocast with GradScaler, length-bucketed
  batches of up to 20k tokens, about 46k tokens/s. 5 epochs over `data/tok` = 14,000 steps in 97 min.

| step | epoch | train loss | val loss (nats/token) |
|---|---|---|---|
| 1000 | 0.36 | 0.745 | 0.657 |
| 2000 | 0.71 | 0.385 | 0.324 |
| 3000 | 1.07 | 0.244 | 0.250 |
| 5000 | 1.78 | 0.208 | 0.214 |
| 8000 | 2.85 | 0.241 | 0.192 |
| 11000 | 3.92 | 0.215 | 0.183 |
| 14000 | 4.99 | 0.235 | 0.1795 |

Val loss was still falling slowly at the end, and train and val stay close, so there is no overfitting at this data
size. A loss of 0.18 nats/token is low because most tokens are forced by the structure.

## 4. Evaluation (`learn eval`; 128 pieces per genre unless noted)

Status of a sampled piece:

- `decodable`: it decodes to a Tune.
- `arc pass`: it passes `composer.shape`'s arc check, as the runner requires.
- `all checks`: it also passes the breath gate.

Score is `composer.score` over the pieces that pass all checks. The teacher row is from `data/full`.

### 4.1 Validity and score: student against teacher (one piece against one piece)

| genre | variant | decodable | arc pass | all checks | score mean (sd) | capped | teacher (single) |
|---|---|---|---|---|---|---|---|
| new-age | base, temp 1.0 | 0.88 | 0.71 | 0.70 | 81.8 (22.6) | 0.24 | 94.4 (2.5) |
| new-age | base, top-p 0.95 | 1.00 | 0.73 | 0.73 | 86.9 (18.8) | 0.14 | 94.4 |
| new-age | base, top-p 0.95 + grammar, temp 0.8 | 1.00 | 0.81 | 0.81 | 86.3 (18.3) | 0.15 | 94.4 |
| new-age | base, p0.95 + **retry** | 1.00 | 0.99 | 0.98 | 94.2 (2.4) | 0 | 94.4 |
| new-age | **top30**, p0.95 + retry | 1.00 | 1.00 | 0.98 | **95.2 (2.3)** | 0 | 94.4 |
| new-age | RL, p0.95 + retry | 1.00 | 1.00 | 1.00 | 94.6 (2.5) | 0 | 94.4 |
| classical | base, p0.95 | 1.00 | 0.94 | 0.94 | 82.4 (21.1) | 0.23 | 95.4 (3.5) |
| classical | base, p0.95 + retry | 1.00 | 0.99 | 0.99 | 93.5 (4.5) | 0 | 95.4 |
| classical | **top30**, p0.95 + retry | 1.00 | 1.00 | 0.99 | **96.1 (3.2)** | 0 | 95.4 |
| lofi | base, p0.95 | 1.00 | 0.82 | 0.66 | 89.0 (19.5) | 0.15 | 98.9 (1.7) |
| lofi | base, p0.95 + retry | 1.00 | 1.00 | 0.82 | 97.3 (2.5) | 0 | 98.9 |
| lofi | top30, p0.95 + retry | 1.00 | 1.00 | 0.85 | 97.7 (2.2) | 0 | 98.9 |
| jazz-piano | base, temp 1.0 | 0.91 | 0.77 | 0.77 | 63.8 (31.7) | 0.37 | 65.3 (31.9) |
| jazz-piano | base, p0.95 + retry | 1.00 | 1.00 | 1.00 | 62.3 (32.2) | 0.41 | 65.3 |
| jazz-piano | **top30**, p0.95 | 0.98 | 0.88 | 0.88 | **74.6 (29.6)** | 0.26 | 65.3 |
| jazz-piano | top30, p0.95 + retry | 1.00 | 1.00 | 1.00 | 74.1 (29.7) | 0.27 | 65.3 |
| jazz-trio | base, p0.95 | 0.99 | 0.88 | 0.88 | 60.6 (32.8) | 0.44 | 62.3 (33.3) |
| jazz-trio | top30, p0.95 + retry | 1.00 | 1.00 | 1.00 | 70.2 (31.9) | 0.32 | 62.3 |

Files: `runs/base/{eval-t1,p95,sw-*,p95-retry8}`, `runs/top30/{p95,p95-retry8}`, `runs/rl/p95-retry8`.

**What the variants mean.**

- **Sampling.** At temperature 1.0 about 10 % of the samples were syntax errors: a tail token sampled at step 1, for
  example. Top-p 0.95 removes all of them. Grammar-constrained decoding gives the same samples, because the in-grammar
  mass is already above 0.95.
- **Retry** (`--retry 8`). Draw up to 8 candidates per piece and keep the first whose lead sheet passes the
  composer's own cheap checks, measured without performing it: it decodes, has no `shape()` arc issue, and its
  `melody_issues` stay inside the score table's range. This is not a peek at the score. It is the budget the rule
  composer spends internally (`Tune.retries`: 14-18 drafts per new-age tune). The student needs 1.1-1.5 candidates
  on average.
- **The gap without retry** is almost entirely the hard rule `mel_issues`: melody notes clashing with the chord on
  strong or long beats, unrecovered leaps. The teacher never shows it, because its composer rejects such drafts
  before they exist. With retry, the gap closes.

**(a) Score-filtered training (`top30`).** Base fine-tuned for 800 steps (lr 1e-4) on the top 30 % by score per
genre of `data/full` (4,532 pieces). With the same retry budget it beats the teacher's single-piece distribution on:

| genre | student | teacher | delta (standard errors) |
|---|---|---|---|
| new-age | 95.2 | 94.4 | +0.8 (~3 se) |
| classical | 96.1 | 95.4 | +0.7 (~2 se) |
| jazz-piano | 74.1 | 65.3 | +8.8 (~3 se) |
| jazz-trio | 70.2 | 62.3 | +7.9 |

Lofi stays below (97.7 against 98.9; the lofi teacher is saturated). This is distillation of best-of-~3 into one
sample. On jazz the student learned which lead sheets the soloist handles better: the hard-capped share dropped from
0.37 to 0.27.

**(b) Best-of-N at matched compute** (`runs/top30/bo8`: top-p 0.95, 8 candidates per piece, best by score, 64
pieces):

| genre | student best-of-8 | teacher best-of-8 |
|---|---|---|
| new-age | **97.6** (sd 1.0) | 97.1 |
| classical | **99.0** (0.9) | 99.0 |
| jazz-piano | **93.9** (1.4) | 92.6 |

The student is at least as good as the teacher at the same inference budget, with a small edge on new-age and jazz.

**(c) Expert iteration** (`runs/ei`: from top30; 3 rounds; 256 samples per genre per round at temperature 1.0; keep
the top 25 % by score; fine-tune 400 steps on everything kept so far plus a replay of the teacher's top 30 %). The
table shows the raw policy (no retry, temperature 1.0):

| round | new-age all checks / score | classical | jazz-piano |
|---|---|---|---|
| 0 (top30) | 0.70 / 84.9 | 0.77 / 83.6 | 0.69 / 68.5 |
| 1 | 0.70 / 82.2 | 0.77 / 83.0 | 0.70 / 68.7 |
| 2 | 0.73 / 83.6 | 0.85 / 84.4 | - |
| 3 | 0.75 / 85.1 | 0.76 / 86.7 | 0.74 / 68.2 |

**Negative or flat.** The kept samples (192-576) were swamped by about 2,900 replay pieces, and the differences sit
inside the noise (se about 1.5). Expert iteration as configured did not move the student. Next time: less replay,
more kept pieces, more rounds.

### 4.2 The tells against the teacher (Goodhart watch)

`metric_table`: for each metric, the 1-D Wasserstein distance between the student and teacher distributions, in
teacher sd units. The figures below are for `top30` + retry. "Unscored" means the `score_metrics` tells that the
style's score table does not weigh.

| genre | scored: median W1/sd | farthest scored | unscored: median W1/sd | farthest unscored |
|---|---|---|---|---|
| new-age | 0.17 | `mel_style` 0.83 vs 0.07 (2.4) | 0.22 | `off_chord32` 0.95 vs 1.27 (0.31) |
| classical | 0.38 | `mel_style` 1.64 vs 0.28 (1.9), `hook_sections` 3.98 vs 4.84 (0.59) | 0.40 | `lh_figures` (0.56) |
| lofi | 0.14 | `mel_style` 1.62 vs 0.61 (1.3) | 0.12 | `rest_half` (0.26) |
| jazz-piano | 0.22 | `mel_issues` 0.35 vs 0.01 (2.6), `mel_style` (1.1) | 0.22 | `nct_ph` 0.71 vs 0.88 (1.2), `lh_rootless` (0.75) |

**What separates the student from the teacher:**

- **`mel_style`.** The student over-uses a rhythm cell and circles pitches more often. The teacher's composer rejects
  such drafts; the student's retry checks do not look at `mel_style`.
- **Jazz phrases.** Fewer non-chord tones per phrase (`nct_ph`).
- **Classical.** Fewer hook statements across sections.

Everything else is inside about 0.3 sd of the teacher.

### 4.3 Novelty and memorisation

For each genre, the student's head melodies are compared with up to 30,000 training pieces of that genre. The
teacher baseline is pieces from `data/full`, which no model was trained on.

| genre | 6-gram seen in train (student / teacher) | bars seen | nearest-neighbour Jaccard | exact copies | distinct 6-grams in the set (student / teacher) |
|---|---|---|---|---|---|
| new-age (base p95) | 0.264 / 0.246 | 0.922 / 0.919 | 0.104 / 0.106 | 0 | 0.93 / 0.94 |
| classical | 0.080 / 0.086 | 0.943 / 0.948 | 0.150 / 0.146 | 0 | 0.83 / 0.82 |
| lofi | 0.094 / 0.111 | 0.976 / 0.984 | 0.147 / 0.148 | 0 | 0.90 / 0.90 |
| jazz-piano | 0.037 / 0.039 | 0.846 / 0.849 | 0.111 / 0.105 | 0 | 0.84 / 0.84 |
| new-age, RL (raw) | 0.211 / 0.246 | 0.887 / 0.921 | 0.095 / 0.105 | 0 | - |

The student is exactly as "novel" as a fresh teacher seed:

- **No memorisation.** No piece reaches nearest-neighbour Jaccard ~1, and there are no copies, even after 5 epochs.
- **Diversity holds.** Diversity within a set equals the teacher's.
- **New-age vocabulary is shared.** The high 6-gram overlap there (0.25) belongs to the teacher too: its cell
  vocabulary is shared across pieces.

## 5. Blending (`--genre new-age-piano=0.7,jazz-piano=0.3`)

- **Setup.** The player is the heaviest genre, and the header is constrained to that genre's moods, feels and forms.
- **Measure.** For each lead-sheet feature, `x = (blend - parent B) / (parent A - parent B)`: x = 1 means "like A",
  0 means "like B", 0.5 means halfway.
- **Most telling feature.** The share of extended or altered chord colours: new-age 0.15, jazz 0.76.
- **Files:** `runs/top30/blend-grammar*`, grammar on.

| blend | mode | all checks | score | ext_share (x) | notes/bar (x) | chord rate (x) |
|---|---|---|---|---|---|---|
| new-age 0.7 / jazz 0.3 | embedding | 0.63 | 81.3 | 0.15 (0.99) | 3.33 (1.05) | 1.06 (0.96) |
| new-age 0.5 / jazz 0.5 | embedding | 0.46 | 34.1 | 0.49 (0.45) | 2.93 (0.31) | 1.00 (0.29) |
| jazz 0.7 / new-age 0.3 | embedding | 0.91 | 65.5 | 0.77 (1.01) | 3.07 (0.43) | 1.07 (-0.09) |
| new-age 0.7 / jazz 0.3 | logit mix | 0.70 | 83.0 | 0.05 (1.16) | 3.25 (0.90) | 1.05 (0.90) |
| new-age 0.5 / jazz 0.5 | logit mix | 0.67 | 29.2 | 0.22 (0.89) | 3.18 (0.77) | 1.00 (0.31) |
| jazz 0.7 / new-age 0.3 | logit mix | 0.81 | 70.7 | 0.47 (**0.52**) | 3.12 (0.33) | 1.04 (0.31) |

**Findings:**

- **70/30 embedding blends snap to the majority parent** (x ≈ 1 on the colour feature). The genre embedding acts as
  a switch, not a dial: the model never saw intermediate conditioning.
- **50/50 is incoherent.** Without the grammar, 66 % of pieces were not decodable: a new-age header followed by a
  jazz AABA body. With the grammar every piece decodes, but scores collapse (34). Its features do land between the
  parents, but by alternating between parents, not by blending them.
- **Logit mixing does interpolate the harmony.** The `--blend-mode logits` option mixes the per-genre next-token
  log-probs. At jazz 0.7 it gives a real halfway colour (ext_share 0.47, x 0.52) at a reasonable validity (0.81).
- **Next step.** Train with random mixture conditioning (Dirichlet weights over the genres with the matching mixed
  data), so the embedding learns a continuum.

## 6. RL: GRPO with composer.score (`learn/rl.py`, new-age)

**Setup:**

- **Batch.** Per step, 4 prompts x 8 pieces, generated in one batch. Advantage = (r - group mean) / group sd. There
  is no value network.
- **Update.** One on-policy update per step, on the mean token log-prob, plus a KL penalty (k3 estimator) to the
  supervised model `top30`. Dropout is off.
- **Reward.** score / 100 for a piece that passes all checks; 0 for an arc or breath reject; -0.2 for an undecodable
  or unplayable sequence.
- **Logged every step** (`runs/<rl>/rl.jsonl`): reward, score, rates, KL, entropy, diversity, the held-out unscored
  tells, and every 10 steps the nearest-neighbour similarity.

**RL1** (`runs/rl`: lr 2e-5, beta 0.05, 150 steps, about 50 min):

| steps | reward | score (passing) | all checks | KL | entropy | distinct 6-grams | NN Jaccard | mel_style | held-out: off_chord32 / a1_range / rest_half / hook_head |
|---|---|---|---|---|---|---|---|---|---|
| 1-15 | 0.621 | 84.3 | 0.765 | 0.003 | 0.196 | 0.943 | 0.099 | 0.79 | 1.29 / 11.81 / 3.15 / 2.95 |
| 31-45 | 0.690 | 85.3 | 0.831 | 0.011 | 0.194 | 0.942 | 0.103 | 0.89 | 1.17 / 11.57 / 3.15 / 2.85 |
| 76-90 | 0.684 | 85.0 | 0.833 | 0.015 | 0.199 | 0.938 | 0.103 | 1.00 | 1.23 / 11.81 / 3.08 / 2.80 |
| 136-150 | 0.711 | 87.7 | 0.837 | 0.030 | 0.203 | 0.945 | 0.095 | 1.00 | 1.29 / 12.05 / 3.10 / 2.69 |

Evaluated on 256 raw samples at temperature 1.0 with the same seeds (`runs/{rl,top30}/raw256`):

| policy | pass all checks | score of passing pieces | capped | 6-gram seen | NN Jaccard |
|---|---|---|---|---|---|
| top30 | 0.668 | 85.2 | 0.18 | 0.230 | 0.098 |
| RL1 | **0.852** | 87.1 | 0.14 | 0.211 | 0.095 |

**What RL learned:**

- **It mostly learned to pass the runner's arc check:** +18 points of pass rate, and retry needs 1.10 candidates
  instead of ~1.5.
- **The quality of passing pieces did not improve.** With retry: 94.6 against 95.2 for top30, within noise.
- **Diversity and novelty held** (slightly more novel), and there were no copies.

**Where it started to game the reward:**

- **`mel_style` rose** (0.79 to 1.00). This is a scored metric, but its weight is small, so pass-rate gains outweigh
  it.
- **The held-out `hook_head` fell** (2.95 to 2.69 statements of the hook in the head; teacher 2.96). The policy
  states its hook less. The score cannot see this, and it is exactly the kind of musical property a judge would
  notice.
- Both drifts are small. The blind judges (section 7) still name hook and development issues for both generators.

**RL2** (`runs/rl2`: continued from RL1, lr 5e-5, beta 0.02; stopped at 60 of 150 steps):

| steps | reward | all checks | KL | entropy | distinct 6-grams | mel_style |
|---|---|---|---|---|---|---|
| 1-15 | 0.684 | 0.829 | 0.05 | 0.206 | 0.955 | 1.13 |
| 16-30 | 0.682 | 0.835 | 0.28 | 0.217 | 0.966 | 1.46 |
| 31-45 | 0.629 | 0.814 | 0.37 | 0.224 | 0.961 | 1.35 |
| 46-60 | 0.683 | 0.850 | 0.12 | 0.210 | 0.960 | 1.35 |

**Negative.** With the higher step size and the weaker KL, the policy drifted (KL 10x, entropy up, 6 % undecodable,
`mel_style` worse) and gained no reward. With 32 noisy samples per step (score sd ~20 because of hard caps), the
gradient is mostly noise. A larger batch or a lower lr is needed, not a larger step.

**RL with a discriminator term** (`runs/rl-disc`: from RL1, disc weight 0.3, 60 steps; `learn/disc.py`):

- **Discriminator.** An L2 logistic regression on the notes-level metrics. Its "real" class is the four LLM-composed
  references (`letters-to-the-morning`, `pro-newage-rain` / `-hopeful` / `-waltz`). It was refit every 10 steps on
  the policy's latest pieces.
- **What it keyed on:** `frame_pitches` (+0.72: the references use more pitches in their intro and coda frames,
  ROUNDS.md's open tell), `final_jump` (+0.5), and fewer `quiet1` / `climax_x` / `rest_max`.
- **P(real)** for the policy's pieces stayed at 0.08-0.12 through all 60 steps. Score and pass rate behaved like RL1.
- **Negative.** The frames (intro / interlude / coda texture) mostly come from the arrangement plan and the players,
  not from the lead sheet. The student can barely move what the critic measures, and four references are far too few
  for a critic that generalizes.

## 7. Blind round (new-age, 2026-10-12)

**Setup:**

- **Pieces:** 12 anonymized packets made by the new-age packet writer (`learn blind`, which reuses
  `songs/_blind/make_packets_newage.py`):
  - 4 composed references: `letters-to-the-morning`, `pro-newage-rain`, `pro-newage-hopeful`, `pro-newage-waltz`.
  - 4 teacher tunes: what `endless new-age-piano --candidates 8` delivers. Scores 95.0-98.3.
  - 4 student tunes: top30, top-p 0.95, best-of-8 by score, the first 4 of 6 drawn. Scores 94.7-99.8.
- **Judges:** three composer-lens judges, run as foreground subagents. They read only `JUDGE.md` + `packets/` in an
  isolated copy (`D:/agentsound-judging/learn-r1`). The KEY (`D:/agentsound-learn/blind/KEY-judge1.json`) was read
  only by the scorer.

| source | verdicts "composed" | mean confidence of the "generated" verdicts |
|---|---|---|
| composed references | 11 / 12 (pro-newage-rain called generated once) | - |
| teacher | **0 / 12** | 62 |
| student | **3 / 12** | 62 |

Per student piece:

| piece | score | judges fooled |
|---|---|---|
| VWWR | 94.7 | 1 of 3 |
| THRH | 99.7 | 1 of 3 |
| KQAQ | 98.2 | 1 of 3 |
| RBQN | 99.8 | 0 of 3 |

**Conclusions:**

- **The fooled verdicts do not follow the score.** The highest-scoring student piece was caught by all three judges.
- **Student versus teacher is not significant.** 3/12 against 0/12 gives Fisher's exact p ≈ 0.11. The student is
  not worse than the teacher in the judges' eyes, and maybe slightly better.

**Tells named for both generators:**

- The climax is the A theme an octave up in block chords.
- A1 is copied in the last A at a softer level, and the return is labelled "A4" with no A3.
- A2 is padded to 9 bars.
- A stock Xsus4-IV-iv6-I coda with an empty right hand.
- Narrow themes that circle on 2-3 pitches.
- Narrow left-hand voicings that repeat notes.

Most of these come from the shared arrangement plan and the players, not from the notes the student chooses. They
match the "tells left" of round r5.

**Student-specific tells:**

- Out-of-key held tones: G#4 over B in E minor, held at three cadences.
- Two identical bars back to back (RBQN 19-20).
- A theme opening on the 6th and 4th over the chord.

These are the `mel_style` / `melody_issues` kind that section 4.2 measures.

## 8. Renders (the existing players + engine, through the endless render gate: 0 clicks, loudness window)

| piece | file | score | LUFS |
|---|---|---|---|
| student new-age (fooled 1 of 3 judges) | `D:/agentsound-learn/blind/student/002-windows-to-the-evening/mix.mp3` | 99.7 | -20.6 |
| student new-age (highest score) | `D:/agentsound-learn/blind/student/001-stones-to-the-sea/mix.mp3` | 99.8 | -19.1 |
| student new-age | `D:/agentsound-learn/blind/student/003-rivers-of-the-tide/mix.mp3`, `004-the-distant-bridges/mix.mp3` | 98.2 / 94.7 | -21.1 / -20.5 |
| student 70/30 new-age/jazz (embedding blend, new-age players) | `D:/agentsound-learn/renders/blend/001-the-soft-postcards-student-new-age-70-jazz-30/mix.mp3` | 96.8 | -20.4 |
| student 70/30 (second) | `D:/agentsound-learn/renders/blend/002-quiet-gardens-student-new-age-70-jazz-30/mix.mp3` | 96.0 | -19.7 |
| teacher (for A/B) | `D:/agentsound-learn/blind/teacher/00{1..4}-*/mix.mp3` | 95.0-98.3 | |

Per section 5, the 70/30 embedding blend is musically almost pure new-age.

## 9. Answer to the research question, and next steps

**Can the student match its teachers?** Yes, given the same cheap lead-sheet checks the composer uses on itself.
Without them, raw samples lose 7-13 points on the piano styles. The cause is `mel_issues` clashes that the teacher
never ships, because it rejects them internally. A model of 32M parameters, trained on 80k pieces, learns the
distribution with no memorisation and full diversity.

**Can it exceed them?**

- **On the score, modestly.** It takes score-filtered distillation (top 30 %) plus the same retry budget:
  +0.7-0.8 on new-age and classical, +8 on jazz. At matched best-of-8 it is ≥ the teacher on every genre measured.
  This is "exceeding" in the AlphaZero-lite sense: the student bakes the teacher's best-of-N into one sample.
- **Expert iteration and RL did not add quality on top of that in this run.** RL made the raw policy more reliable,
  and it started to trade a held-out tell (`hook_head`) for the reward.
- **In the blind judges' eyes,** the student is at least as convincing as the teacher (3/12 against 0/12). The sample
  is too small to call it.

**The ceiling is the score itself.** It rewards closeness to the teacher's own references, and judges catch both
generators by the same arrangement-level tells, which the lead-sheet student cannot change.

**Next steps, ranked:**

1. Give the student the arrangement plan as tokens (section plan, climax treatment, frame texture). That is where
   the judges' tells live. Phase 1 (the record + the tokens, no retraining) is done: section 11.
2. Add `mel_style` to the retry checks and to the RL reward (or as a KL-free penalty).
3. Train the genre embedding on Dirichlet-mixed conditioning so that blends interpolate.
4. RL with larger batches (≥128 pieces per step, which the CPU scoring pool limits: ~1.5 s per piece) and a learned
   scorer fitted to the judges' verdicts (roadmap stage 2) instead of the hand table.
5. Use a bigger blind round (8+ pieces per source, 5 judges) before claiming a difference.
6. Give the RL reward and the endless runner the set budget of section 10 (variety across a set, not per piece).

## 10. Set variety (2026-10-12)

**The verdict.** The user heard three top30 samples (embedding blend new-age 0.7 / jazz 0.3) and said "so nicht sehr
abwechslungsreich" (recipes/HUMAN_FEEDBACK.md). All three were gentle, minor, 65-68 BPM, with the climax on C6 at
about 90 %. A temperature sweep (top30, new-age, 12 pieces) showed that temperature only adds noise to the notes:
at 1.0, 9 of 12 pieces pass (mean 89.2); at 1.2 the mean drops to 67.3 with 3 invalid; at 1.4, 10 are invalid. The
header tokens barely moved (8 of 12 'longing', 12 of 12 'verse').

**The measure: `learn.evaluate.variety(seqs, genre)`.** `sample` and `eval` report it for every set, and so does
each blend in `eval`. For each field it takes the normalized entropy over the values the genre allows. The fields
are mood, feel, form, mode, key (the tonic), tempo (5-BPM bands), climax position (fifths of the head), climax pitch
(MIDI note) and ending (EndKind + end chord). A score of 1 means the set is spread as evenly as its size allows, and
0 means every piece is alike. A field with a single possible value, such as the new-age form, is left out.
`variety` is the mean over the remaining fields. The fields are read straight from the tokens (`header_of`), so no
performance is needed.

**Did the top-30 % fine-tune collapse onto the slow minor mode? No.** The header distributions for new-age are:

| set | n | mood (hopeful / morning / longing / rain) | feel (flowing / gentle / bright) | minor | tempo median (p10-p90) |
|---|---|---|---|---|---|
| teacher, data/tok (base training) | 4000 | 26 / 25 / 23 / 25 % | 50 / 37 / 13 % | 41 % | 72 (62-85) |
| teacher, data/full ok | 2775 | 26 / 27 / 24 / 23 % | 51 / 35 / 14 % | 39 % | 73 (63-86) |
| teacher top 30 % (top30's training set) | 832 | 25 / 28 / 24 / 24 % | 52 / 35 / 13 % | 39 % | 73 (63-85) |
| base, temp 1.0 (`eval-t1`) | 122 | 20 / 29 / 35 / 16 % | 53 / 41 / 6 % | 38 % | 71 (62-80) |
| top30, temp 1.0 (`raw256`) | 244 | 23 / 33 / 22 / 22 % | 55 / 32 / 13 % | 36 % | 73 (63-85) |
| top30 blend 0.7 / 0.3, embedding (`blend-grammar`) | 128 | 20 / 24 / 26 / **30** % | 55 / 40 / **5** % | **50** % | 72 |
| top30 blend 0.5 / 0.5, embedding | 128 | 16 / 13 / 16 / **47** % | 46 / 45 / 9 % | **62** % | 70 |
| top30 blend 0.7 / 0.3, logit mix | 128 | 20 / 20 / 20 / **39** % | 45 / 46 / 9 % | **52** % | 70 |

- **Score filtering did not narrow the header.** The top 30 % by score has the same moods, feels and modes as the
  whole teacher set, and top30's samples match it. The base model is the one that drifts (bright 6 %, longing 35 %).
- **The jazz half of a blend darkens it.** Even with the header masked to new-age values, the blends move towards
  rain (30-47 % against 25 %), minor (50-62 % against 39 %) and away from bright (5-9 % against 14 %). Gentle and
  minor together take 31 % of the 70/30 blend's pieces, against 24 % for the teacher. Three such pieces in a row
  then come out about 3 % of the time, so the user's three samples were partly the blend and partly chance.
- **The climax is the teacher's own invariant.** Every new-age teacher piece puts the climax in part C, bar 4 or 5
  (87-91 % of the head), on C6 (63 %) or B5 (34 %). The genre's `melody.peak` is C6 for every mood. The student copies
  this exactly: 100 % of the climaxes fall in the last fifth of the head, at every header temperature tried.
  Only a change to the genre spec can vary it (a per-mood `peak`, more climax positions), followed by a re-export
  and retraining (TODO.md).

**The controls.**

- `--header-temp T` (sample and eval): a separate temperature for the header and plan tokens, which means everything
  before the first harmony part, climax plan included. The notes keep `--temp`. Implemented in `model.sample`
  (per-row temperature until the row emits 'H').
- `--spread` (sample and eval): `sample.spread_headers(player, n, seed)` forces Mood, Feel, Form, Meter, Key, Mode
  and Tempo for each piece. It works field by field: the least-used mood (so the moods take turns exactly), then
  the least-used feel, form and mode of that mood, among the combinations the composer itself can draw
  (`header_combos`: the mood's feels and forms, FEEL_FORMS pairings of at least 0.2, modes that have keys). It then
  picks the least-used tonic (never the previous piece's) and the least-used third of the feel's tempo range. Every
  header passes `compose(plan=...)`, which encodes exactly these seven tokens, and the grammar
  (`tests/python/test_learn.py` Spread). With `--best-of K` the K candidates of a piece share its header. The rest
  of the header (energy, ending, swing) and the plan stay sampled.

**The experiment** (`D:/agentsound-learn/varied/exp/*.jsonl`): new-age, 48 pieces, seed 7, temp 1.0, top-p 1.0, one
candidate per piece. "Per set of 6" is the mean over the 8 consecutive sets of 6, which is the size a listener
hears. The blends use the grammar.

| set | pass | score (passing) | variety (48) | variety per 6 | of the passing, per 6 | mood / feel / mode / tempo per 6 |
|---|---|---|---|---|---|---|
| base | 35/48 | 82.5 | 0.685 | 0.640 | 0.643 | 0.77 / 0.74 / 0.84 / 0.77 |
| base, header-temp 1.3 | 27/48 | 79.9 | 0.691 | 0.670 | 0.651 | 0.82 / 0.73 / 0.84 / 0.81 |
| base, spread | 35/48 | 83.3 | 0.725 | 0.716 | 0.675 | 0.97 / 0.92 / 0.92 / 0.80 |
| top30 | 39/48 | 86.1 | 0.662 | 0.632 | 0.588 | 0.77 / 0.74 / 0.80 / 0.77 |
| top30, header-temp 1.3 | 33/48 | 88.2 | 0.665 | 0.640 | 0.606 | 0.81 / 0.70 / 0.69 / 0.81 |
| top30, header-temp 1.6 | 15/48 | 83.7 | 0.550 | 0.529 | 0.476 | 0.61 / 0.39 / 0.52 / 0.64 |
| top30, spread | 33/48 | 83.6 | 0.719 | 0.716 | 0.709 | 0.97 / 0.89 / 0.97 / 0.77 |
| top30, spread + header-temp 1.3 | 34/48 | 82.5 | 0.723 | 0.726 | 0.715 | 0.97 / 0.89 / 0.98 / 0.76 |
| top30 logit blend 0.5 / 0.5, constrained header | 28/48 | 18.2 | 0.704 | 0.659 | 0.633 | 0.77 / 0.62 / 0.94 / 0.65 |
| top30 logit blend 0.5 / 0.5, spread | 28/48 | 28.4 | 0.749 | 0.741 | 0.747 | 1.00 / 0.90 / 0.94 / 0.77 |

- **The spread is what makes a set varied.** Per set of 6, mood rises from 0.77 to 0.97, feel from 0.74 to 0.89,
  mode from 0.80 to 0.97, and overall variety from 0.63 to 0.72 on top30. For the pieces that actually pass, it
  rises from 0.59 to 0.71. The pass rate and score are about the same; the top30 score dips 2.5 points, at n = 48
  per row. The spread forces the rarer combinations (bright, morning-gentle) as often as the common ones.
- **Header temperature alone does not help.** At 1.3 it costs validity (27-33 pass instead of 35-39) and buys
  almost no variety (0.632 to 0.640). At 1.6 the header turns invalid (33 of 48 undecodable without the grammar),
  and the survivors are the most typical pieces (variety 0.53). The model's header is confident and the plan is the
  teacher's invariant, so heating it only breaks it.
- **The ceiling is the teacher.** Variety tops out around 0.72 because the climax position (0.00) and pitch (about
  0.33) cannot move, and the endings repeat (0.55-0.60). Reaching 1.0 needs teacher variety (TODO.md).
- **Spread blends** keep the new-age header even. The logit blend pulls the climax higher (F6 in 40-60 %) and the
  harmony jazzier, which costs `composer.score` under the new-age table (28 mean). Best-of-12 still finds pieces
  above 90.

**Renders** (`D:/agentsound-learn/renders/varied/`, top30, `--spread --grammar --best-of 8`, seed 11; the blends at
best-of-12, seed 12; all through the endless render gate):

| piece | header | score | LUFS |
|---|---|---|---|
| `new-age/001-the-falling-postcards/mix.mp3` | longing, flowing, A minor, 76 BPM, climax C6 | 99.0 | -20.4 |
| `new-age/002-silver-promises-of-snowfall/mix.mp3` | hopeful, bright, D major, 82 BPM, climax B5 | 96.8 | -19.7 |
| `new-age/003-slow-mirrors-of-autumn/mix.mp3` | morning, gentle, Eb major, 65 BPM, climax C6 | 95.6 | -21.0 |
| `new-age/004-petals-in-autumn/mix.mp3` | rain, flowing, B minor, 70 BPM, climax B5 | 95.7 | -20.6 |
| `new-age/005-before-the-hills/mix.mp3` | hopeful, bright, C major, 88 BPM, climax C6 | 99.4 | -19.1 |
| `new-age/006-after-dawn/mix.mp3` | morning, flowing, Bb major, 75 BPM, climax C6 | 96.9 | -20.3 |
| `blend50/001-before-the-rain-new-age-50-jazz-50/mix.mp3` | logit blend 0.5 / 0.5: rain, gentle, D minor, 63 BPM | 92.6 | -21.2 |
| `blend50/002-soft-stones-of-the-tide-new-age-50-jazz-50/mix.mp3` | logit blend 0.5 / 0.5: longing, flowing, Db major, 71 BPM, climax F6 | 94.4 | -20.5 |

The new-age set has variety 0.72: 4 moods, 3 feels, 2 modes, 6 keys and 65-88 BPM. Its climaxes are still all in
the build at C6 or B5 (the teacher's invariant above).

## 11. The arrangement as tokens, phase 1 (2026-10-12)

**Why.** Section 9's next step 1: the judges catch both generators by arrangement-level tells (the climax as the
theme an octave up in chords, identical intro / interlude / coda frames, the stock coda, the 9-bar A2 tail, the left
hand's textures). The players decided all of that with their own dice, out of the student's reach.

**The record: `endless.arrangement.Arrangement(kind, piece, sections)`.** It holds every decision the players draw
per piece above the notes, as plain data whose values come from the players' own vocabularies. `perform.arrange(tune)`
draws it from the seed. `perform.build(tune, arrangement=None)` plays it, and draws it first when it is absent (or
plays `tune.arrangement`, which a decoded piece carries). All draws go through one `Dice`. Without a record it stores
the dice's value. With a record it throws the same dice and lets the record's value win, so every random stream stays
where it was. The default output is therefore bit-identical to the code before the record existed.

| kind | sections | keys (values) |
|---|---|---|
| piano (new-age-piano, new-age-epiano, classical-piano, lofi-piano) | the `plan['sections']` entries played, in order (each entry's `chance` drawn) | copied from the entry: `melody` (lift), `dyn` (marks), `figures` (the left hand's figure set), `harmonize`, `harm_share`, `tempo`, `rit`, `fermata`, `keep_bars`, `lh_only` / `dyn` (drawn when the entry gives weights), `peak`, `drums`; drawn: `octave`, `climax` (lift / theme / climb / step / grow - grown from the hook to a new peak; the set-level pin wins), `reharm` (share), `bars` (bar spans), `tail`, `cadence` (home / vi / IV), `bass` (root / walk), `octave_half`, `fill`, `turn`, `swell` (hairpin levels per 4-bar phrase), `cadenza` (the flourish wanted), `moves` (a waltz's later bar of a held chord: hold / bass / sub / ped - a neighbour chord over the held root), `vary` (`AVary`: a return's development per 2-bar unit: keep / orn / rhythm / seq / invert), `key` (`AKey`: the section's key: home / step / IV / bVI / bIII / III / par / rel); piece: `layout` (the form: `plan['set']['layout']`, the set-level pin `Tune.arrange` or drawn), `touch` (the touch window shift), the pianist's `plan['play']` knobs (arrangement.PLAY_KEYS: `rubato` ARubato, `inhale` AInhale, `lilt` ALilt, `breath` ABreath, `push` APush, `inner` AInner, `cap` ACap, `lh_vel` ALhVel, `pedal` APedal, `end_dyn` AEndDyn, `end_roll` AEndRoll, `end_hold` AEndHold) |
| jazz (jazz-piano, jazz-trio) | `intro`, `head:<part>`, `solo`, `out:<label>`, `tag` | `lh` (LH style / figure per section), `steps` (phrase-touch step per 4-bar phrase), solo: `choruses`, `opening`, `quotes`, `over` (ceiling over the head's top), `window` (the climax window), `burst` (the double-time stage) |

The organ (endless/organ.py) has no record yet (`arrange` returns None). Note-level dice stay with the players: the
left hand's figure per bar (drawn from the section's set), ornaments, reharm chord choices, voicings, rolls, rubato.

**The tokens (schema 2).** An `Arr` block sits between the plan and the harmony:
`Arr [ALayout_<form>] [ATouch_<lo,hi>] (ASec_<name> <prefix>_<value> ...)* EndArr`, or `Arr_none`. Each key has its own prefix
(`tokens.ARR_FIELDS`, fixed order; a list key repeats). Example, new-age seed 101: `ASec_A2 ATail_0 ABass_root
ATurn_1 AFill_1 ASw_0 ASw_1`, `ASec_climax AClimax_theme AReharm_1.0 ATail_1 AFill_1`. A piano section's keys that
equal its plan entry's are left out and filled back by the decoder, so the teacher data carries only the drawn
decisions. The tokens can still say "this section another way" (e.g. `AFig_chorus` on A1). The decoder is strict:
a value must be in the player genre's vocabulary (`arrangement.values`), a section must be one its players know in
the piece's layout (a section name may repeat across layouts; each layout's entry is its own), and the keys must come
in order and only once.

**Vocabulary.** `Vocab.build(seqs, arrangement=True)` (train.py) adds every token of `tokens.arrangement_tokens(
GENRE_NAMES)` to the data's tokens when the data is schema 2 (238 tokens since the new-age sweep of 2026-10-13 - the pianist's `play` keys, the waltz move 'ped' -, 188 after the r9 widening, 169 before: every key's values of every student genre,
every section name of every layout, the jazz head / out labels). A fixed key (`AFig_*`, `ADyn_*` per section) or a
rarely drawn value therefore has a token to sample even when the teacher data never wrote it. Schema-1 data builds
the same vocabulary as before.

**Versioning.** `tokens.SCHEMA = 2`. Checkpoints now store `schema` (`save_ckpt`), and an old checkpoint has none, so
`load_ckpt` reads it off the vocabulary (no `Arr` token means 1). The grammar takes the schema from the vocabulary
(`batch_allowed`) or from the sequence (`check`). `decode` reads both schemas, and `encode(tune)` without an
arrangement still writes schema 1. `learn sample --run runs/top30` (old checkpoint, with and without `--grammar`) gives
the same tokens and scores as the code before the change.

**Lengths** (seeds 100-149, tokens per piece; the context is 1152; new-age after the r7/r8 layouts and the 3/4
waltz, whose `moves` add one token per held chord's later bar):

| genre | schema 1 mean / max | schema 2 mean / max | added (min-max) | over 1152 |
|---|---|---|---|---|
| new-age-piano | 760 / 1020 | 810 / 1106 | +50 (38-97) | 0 |
| new-age-epiano | 749 / 1047 | 796 / 1144 | +47 (38-97) | 0 |
| classical-piano | 741 / 976 | 752 / 989 | +11 (10-13) | 0 |
| lofi-piano | 560 / 600 | 570 / 610 | +10 (9-11) | 0 |
| jazz-piano | 644 / 921 | 682 / 970 | +38 (25-62) | 0 |
| jazz-trio | 654 / 1004 | 685 / 1047 | +31 (21-50) | 0 |

Every piece still fits. Over 400 more seeds (1000-1399): new-age-piano mean 828, p95 1101, max 1142;
new-age-epiano max 1127; jazz-piano max 1167 (1 of 400 over the context). The waltz pieces are the long new-age ones
(their `moves` and their doubled bars). The longest pieces in the old export (max 1194) were over the context already, and they gain
the same 10-60 tokens. Classical and lofi draw few decisions: only which sections play, plus a cadenza.

**Export speed.** `arrange()` costs 0.1-0.2 ms per piece (1.4 ms for new-age, whose plan with its reharm is drawn
twice: once to record, once to play). Tokens-only export stays at 25-65 ms per piece, the same as before within
noise, and the full export is unchanged (`build` drew the same decisions before).

**Verification.**

- Bit identity (phase 1 against master; phase 1b, after merging the new-age r7/r8 branch, against that branch's
  head 1afb0b4): every track's notes, automation, phrase marks and humanize settings, plus the tempo
  map and the sections, for seeds 100-149 of all 7 endless genres (350 pieces, organ and new-age-epiano included).
  0 differ.
- Round trip (`tests/python/test_learn_arrangement.py`): for seeds 100-149 of the six piano / jazz genres, tune +
  arrangement -> tokens -> decode gives the same record (section order included), re-encodes to the same tokens, and
  performs to note-identical tracks. A changed record (climax step, no interlude, A1 on the chorus figures; a jazz
  head's left hand, the solo's quotes; a waltz told another layout and other `moves`) changes the notes, and the same
  change through the tokens plays the same notes. Every Arr token of seeds 200-205 is in `arrangement_tokens`.
- Phase 1b folded the r7/r8 decisions into the record instead of a parallel one: the layout (and its set-level pin),
  the climax 'climb', the drawn `lh_only`, `harm_share`, the waltz's `moves` (the `form_bars` stretch itself follows
  the meter). The players' `s.endless_arrange` / `_drawn` are gone; `song.endless_arrangement` is the one record.
  The section cadences and the register shift were already covered (`cadence` per section; the shift is the
  tune's set-level pin, `Tune.arrange`, a composer-level decision that reaches the tokens through the notes).

**Phase 2** is section 12. Still open: should the left hand's per-bar figures become tokens too (about one per bar,
+60-70 tokens)?

## 12. The arrangement as tokens, phase 2: re-export, retrain, evaluate, blind round (2026-10-13)

**Short answer.**

- **The mechanics worked.** The schema-2 student (`runs/top30_2`) reproduces the teacher's arrangement
  distributions within a total variation of 0.03-0.12 on new-age. `--spread` now also spreads the layout and the
  climax kind. Set variety per 6 pieces rose from 0.72 to 0.87, and the climax position is no longer fixed.
- **The score kept parity.** With the same retry budget, the student is at or slightly above the new teacher on
  new-age, classical and jazz, and below it on lofi, as before.
- **The judges were not fooled at all.** In a blind round of 24 packets with 5 judges, the student was called
  "composed" 0 times in 40 verdicts, the teacher 0 in 40, and the composed references 31 in 40.
- **Why.** The Arr block lets the student choose among the players' options, but every option is the teacher's
  template. The judges name the template itself in every layout: verbatim returns, a climax rebuilt from earlier
  bars, the stock intro / build / coda frame, and no key plan.

### 12.1 Data (`learn export`, schema 2, on master 3e763eb: the new-age loop r6-r8, pianist rounds 1-2, pack fallback)

| set | what | pieces | time |
|---|---|---|---|
| `data/tok2` | seeds 4000-23999 x 5 student genres, tokens only | 100,000; 79,617 pass the arc check (new-age 13,508 = 68 %, was 14,169) | 845 s at 118 pieces/s (11 processes) |
| `data/full2` | seeds 0-3999 x 5, performed + scored | 20,000 | about 105 min (see below) |

**Export speed and the `sfz.load` memo.** Jazz-trio ran about 15x slower than before (0.7 pieces/s on 10
processes). The profile showed that each performance re-imported ~10k SFZ regions: 34 s of 46 s per piece went
to `sfz.load` (four loads per compile; only the parse was cached). `sfz.load` is now memoized per process, keyed by
the file, its mtime and every argument, and returns a deep copy. The export records are byte-identical with and
without the memo. After the memo, steady state is 3-6 s per piece under load.

**Lengths and the context.** Tokens per piece including EOS (`data/tok2`, the pieces that pass the arc check):

| genre | mean | p50 | p95 | p99 | max | over 1152 |
|---|---|---|---|---|---|---|
| new-age-piano | 810 | 768 | 1089 | 1118 | 1166 | 4 (0.03 %) |
| classical-piano | 784 | 890 | 988 | 1006 | 1034 | 0 |
| lofi-piano | 572 | 575 | 600 | 609 | 619 | 0 |
| jazz-piano | 708 | 683 | 1022 | 1075 | 1236 | 18 (0.10 %) |
| jazz-trio | 703 | 679 | 1014 | 1069 | 1234 | 29 (0.17 %) |

None is over 1280. The context stays at 1152: the new-age waltz p95 (1089) fits, and the training drops 51 of 79,617
pieces (0.06 %; the old run dropped 10).

**The new teacher** (`data/full2` against `data/full`; pass = every check; capped = a hard rule):

| genre | pass | score mean (sd) | p10 | capped | best-of-8 | old: pass / score / best-of-8 |
|---|---|---|---|---|---|---|
| new-age-piano | 0.68 | **96.2** (2.4) | 93.0 | 0 | 98.6 | 0.69 / 94.2 / 97.1 |
| classical-piano | 0.89 | 94.8 (3.4) | 90.1 | 0 | 98.7 | 0.88 / 95.4 / 99.0 |
| lofi-piano | 0.55 | 98.8 (1.7) | 96.6 | 0 | 99.9 | 0.53 / 98.8 / 99.9 |
| jazz-piano | 0.88 | 64.7 (32.1) | 24.6 | 0.37 | 92.6 | identical |
| jazz-trio | 0.88 | 62.5 (33.0) | 24.4 | 0.40 | 92.6 | identical |

Teacher arrangement distributions (new-age, `data/tok2`):

- layout: song 43 / chorus 31 / return 26 %
- climax kind: theme 42 / climb 33 / lift 21 / step 5 %
- climax position (fifths of the head): 4th 47 / 3rd 26 / 2nd 27 %. The old teacher put 100 % in the last fifth.
- cadences: vi 44 / home 31 / IV 26 %
- swell levels: 1 60 / 0 30 / 2 10 %

### 12.2 Training

- **Base** (`runs/base2`): same model as section 3 (d 512, 10 layers, 32.5M params). The vocabulary has 749 tokens:
  571 + 178 from the Arr block, built from `arrangement_tokens` plus the data. It trained on 77,991 pieces (55.9M
  tokens) for 5 epochs = 14,600 steps in 101 min at 46k tok/s. Validation loss by step:

  | step | 1000 | 2000 | 3000 | 5000 | 8000 | 11000 | 14000 | final |
  |---|---|---|---|---|---|---|---|---|
  | val (nats/token) | 0.676 | 0.333 | 0.276 | 0.232 | 0.204 | 0.193 | 0.189 | **0.1887** |

  The old base ended at 0.1795 on different data. The Arr block adds tokens that are genuinely drawn, so the
  per-token entropy is a little higher.
- **Top 30 %** (`runs/top30_2`): 800 steps at lr 1e-4 on the top 30 % by score per genre of `data/full2` (4,551
  pieces, 3.1M tokens), 5.3 min. The best validation loss is 0.2264 at step 200, which is the saved checkpoint, as in
  the old run.

### 12.3 Validity and score against the new teacher (128 pieces per genre, top-p 0.95)

**Raw (no retry, no grammar):**

| genre | base2: decodable / all checks / score / capped | top30_2 | old base, section 4.1 |
|---|---|---|---|
| new-age | 1.00 / 0.84 / 87.4 / 0.16 | 1.00 / 0.77 / 88.0 / 0.17 | 1.00 / 0.73 / 86.9 / 0.14 |
| classical | 1.00 / 0.95 / 86.1 / 0.12 | 1.00 / 0.89 / 90.8 / 0.09 | 1.00 / 0.94 / 82.4 / 0.23 |
| lofi | 1.00 / 0.74 / 92.7 / 0.10 | 0.99 / 0.78 / 91.8 / 0.10 | 1.00 / 0.66 / 89.0 / 0.15 |
| jazz-piano | 0.96 / 0.90 / 66.8 / 0.32 | 0.96 / 0.87 / 70.5 / 0.30 | - |
| jazz-trio | 0.98 / 0.87 / 65.9 / 0.35 | 0.95 / 0.86 / 70.7 / 0.31 | 0.99 / 0.88 / 60.6 / 0.44 |

The raw piano pass rates are a little higher than the old base's. Jazz now has 2-5 % syntax errors at top-p 0.95 (a
non-Tempo token at position 7, where the jazz tempo tail is long). Grammar-constrained decoding removes them.

**With the retry budget (`--retry 8`, the composer's own cheap checks):**

| genre | top30_2: all checks / score (sd) / capped | old top30 (schema 1) on the new players | teacher, one piece |
|---|---|---|---|
| new-age | 0.97 / **96.9** (2.1) / 0 | 1.00 / 96.5 (2.4) / 0 | 96.3 (2.2) |
| classical | 0.99 / **95.2** (3.5) / 0 | 0.99 / 94.9 (3.6) / 0 | 94.7 (3.5) |
| lofi | 0.92 / 97.2 (2.5) / 0 | 0.84 / 97.2 (2.9) / 0 | 98.9 (1.7) |
| jazz-piano | 1.00 / **71.6** (31.1) / 0.28 | 1.00 / 70.4 (30.6) / 0.32 | 65.3 (31.9) |
| jazz-trio | 1.00 / **72.1** (30.9) / 0.29 | 1.00 / 62.6 (33.7) / 0.42 | 62.3 (33.3) |

Score parity holds and the small edge remains (+0.6 new-age, +0.5 classical, +6-10 jazz). On new-age the old student
scores just as well on the new players (96.5), so the score cannot tell the two students apart; variety and the
arrangement can.

**The tells** (`metric_table`, median W1 / teacher sd, retry sets):

| genre | top30_2 scored / unscored | old top30 scored / unscored | farthest |
|---|---|---|---|
| new-age | 0.16 / 0.22 | 0.18 / 0.35 | `mel_style` 1.14 (old 0.89); old: `off_chord32` 0.70, `arc_pitch_r` 0.85 |
| classical | 0.48 / 0.26 | 0.36 / 0.28 | `mel_style` 2.14 (old 1.89), `lh_figures` 0.60 |
| lofi | 0.18 / 0.12 | 0.17 / 0.15 | `mel_style` 1.54 |
| jazz-piano | 0.22 / 0.23 | 0.22 / 0.24 | `mel_issues` 2.9, `nct_ph` 1.07 |

`mel_style` is still the student's main measured tell (section 4.2). The schema-2 student is closer to the new
teacher on the unscored new-age tells (0.22 against 0.35).

**Novelty** (new-age, against `data/tok2`): 6-gram seen 0.184 (teacher 0.184), bars seen 0.884 (0.880),
nearest-neighbour Jaccard 0.093 (0.098), 0 copies. Classical, lofi and jazz have 6-gram overlap within 0.03 of the
teacher, the same nearest-neighbour Jaccard and no copies. Jazz reuses fewer of the training bars (0.78 against
0.85). There is no memorisation.

### 12.4 The arrangement: does the student reproduce the teacher's distributions?

New-age, top30_2 with retry (128 pieces) against the teacher's 392 passing pieces. TV is the total variation (0 the
same, 1 disjoint):

| field | student | teacher | TV |
|---|---|---|---|
| layout | chorus 37 / song 37 / return 27 % | song 45 / chorus 31 / return 24 % | 0.085 |
| climax kind | theme 46 / climb 41 / lift 9 / step 5 % | theme 43 / climb 33 / lift 21 / step 3 % | 0.123 |
| climax position (fifths) | 4th 54 / 3rd 29 / 2nd 17 % | 47 / 28 / 25 % | 0.073 |
| cadences (every ACad) | vi 44 / home 35 / IV 21 % | 43 / 31 / 27 % | 0.055 |
| swell levels | 1 63 / 0 28 / 2 9 % | 60 / 30 / 10 % | 0.030 |
| form (the sections in order) | | | 0.084 |

Jazz: the left hand per section has TV 0.18 (jazz-piano) and 0.09 (trio). Classical and lofi draw only which
sections play (form TV 0.31 / 0.09; climax position 0.02 / 0).

The student reproduces the teacher's arrangement closely. Its one bias is towards the common choices: the 'lift'
climax is under-drawn (9 % against 21 %) and the earliest climax position is rarer (17 % against 25 %).

### 12.5 Set variety, and the spread over layout and climax kind

`--spread` now also forces the set-level arrangement draws (`plan['set']`) for schema-2 checkpoints:

- The layout and the climax kind take turns like the moods. A value below `MIN_PAIR` of the commonest is left out
  (the climax 'step', weight 0.1).
- A mask (`sample.arr_mask`) applies them where the grammar reaches `ALayout_*` / `AClimax_*`.
- The rest of the block (the sections of that layout, the cadences) stays the model's.
- The spread uses its own RNG, so the forced headers are unchanged.
- `variety` gains two fields, layout and climax kind (schema 2 only).

The experiment of section 10 (new-age, 48 pieces, seed 7, temperature 1.0, top-p 1.0, one candidate) on the new
players. "9-field" is the old variety without the two new fields, so it compares like with like. "per 6" is the
mean over the 8 sets of 6.

| set | pass | score | variety, 9-field (48 / per 6) | variety, 11-field per 6 (all / passing) | climax position | layout | climax kind |
|---|---|---|---|---|---|---|---|
| top30 | 34/48 | 86.5 | 0.636 / 0.623 | - / 0.579 (9-field) | 0.00 | - | - |
| top30, spread | 27/48 | 88.3 | 0.706 / 0.719 | - / 0.705 (9-field) | 0.00 | - | - |
| top30_2 | 28/48 | 79.9 | 0.806 / 0.785 | 0.779 / 0.786 | 0.60 | 0.99 | 0.78 |
| **top30_2, spread** | 30/48 | 81.0 | **0.877 / 0.866** | **0.868 / 0.854** | 0.61 | 1.00 | 0.79 |

What the table shows:

- **Climax position.** The old student's climax is in the last fifth every time, because that was the old teacher's
  invariant. The new student places it like the new teacher.
- **Variety.** Per 6 it rises from 0.72 to 0.87 with the spread.
- **The spread's arrangement.** It balances the climax kinds at 34 / 34 / 32 % (theme / climb / lift); the teacher
  draws 43 / 33 / 21 / 3. The layout and climax-kind tokens it forces come out exactly where the grammar asks for
  them (`tests/python/test_learn.py`).
- **Cost.** At temperature 1.0 without retry, the schema-2 student passes less often and scores lower (79.9-81.0
  against 86.5-88.3). With retry the gap closes (12.3), and the renders below all pass at 95-99.

### 12.6 Blind round 2 (new-age, `learn blind`, 24 packets, 5 judges)

**Setup:**

- **Composed references:** 8 of the 12 reference pieces, drawn with a seeded shuffle and built in the worktree:
  `letters-to-the-morning`, plus `pro-newage-` embers, homecoming, hopeful, longing, snowfield, tide and waltz.
- **Teacher:** `endless new-age-piano --count 8 --candidates 8 --seed 60000`, which is the runner with its set plan
  and its best-of-8. Scores 97.2-99.9.
- **Student:** top30_2, `--spread --grammar --best-of 8 --top-p 0.95 --seed 21`. The first 8 of 10 were taken, all
  passing, with no picking. Scores 96.0-100.0; three are 3/4 waltzes.
- **Judges:** five judges with r8's lenses (three composers, a pianist, a statistician), run as foreground
  subagents. Each had an isolated folder (`D:/agentsound-judging/learn-r2/<judge>/`: `JUDGE.md` + `packets/`). The
  KEY (`D:/agentsound-learn/blind2/KEY-judge.json`) was read only by the scorer.

**Results:**

| source | verdicts "composed" | mean confidence of the "generated" verdicts |
|---|---|---|
| composed references | **31 / 40** (letters 1/5, waltz 2/5, hopeful 3/5, the other five 5/5) | 61 |
| teacher | **0 / 40** | 73 |
| student | **0 / 40** | 75 |

- Every judge got 21-24 of the 24 right; all of their misses were composed pieces called generated.
- Student against teacher: Fisher p = 1.0. Student against composed: p ≈ 4e-14.
- Round 1's 3/12 for the student (section 7) does not replicate at 8 pieces x 5 judges.

**Tells named for both generators** (all five Advice sections agree):

1. **The returns are copied, not developed.** The last A repeats an earlier A note for note, or only re-bassed or
   up an octave. The statistician counted 21-40 % exactly copied bars in the generated pieces against 2-15 % in the
   composed ones.
2. **The climax is built from earlier material.** It is B1 replayed, A up an octave, or a generic falling cell. It is
   never a new idea derived from the motif, and it has no harmonic event (modulation, pedal, deceptive move) under it.
3. **One frame in every piece:**
   - a 4-bar intro on vi-IV-I-Vsus4 with the right hand silent;
   - a build whose penultimate chord is bVII;
   - an interlude pasted from intro bar 3;
   - a coda of IV-ivm6-I(add9) over a block chord;
   - identical layouts across pieces, whatever layout was chosen.
4. **No key plan.** One key, colour chords that do not resolve (V/x not to x). The composed pieces move to bVI, the
   parallel major, bIII, or a Neapolitan region.
5. **The waltz template.** One 2-bar cell (pickup, a note held 3 beats, an echo), two bars per chord, and 4 bars of
   left hand alone before the final chord.
6. **Phrase onsets.** A beat-2 pickup in 17-46 % of bars, against 0-8 % in the composed pieces.

### 12.7 Renders (`D:/agentsound-learn/renders/schema2/`, top30_2, `--spread --grammar --best-of 8`, seed 31; every piece through the endless render gate)

| piece | header | layout | climax (kind, pitch, position) | score | LUFS |
|---|---|---|---|---|---|
| `new-age/001-wings-of-the-hills-waltz/mix.mp3` | morning, waltz 3/4, Db major, 87 BPM | return | lift, C#6, 91 % | 95.0 | -18.5 |
| `new-age/002-lights-of-the-morning/mix.mp3` | rain, gentle, A minor, 66 BPM | chorus | theme, B5, 88 % | 98.1 | -19.9 |
| `new-age/003-other-promises/mix.mp3` | longing, flowing, E major, 69 BPM | song | climb, D#6, 62 % | 99.0 | -19.2 |
| `new-age/004-distant-seasons-of-spring/mix.mp3` | hopeful, bright, C major, 84 BPM | chorus | theme, B5, 59 % | 98.8 | -18.8 |
| `new-age/005-little-leaves/mix.mp3` | morning, flowing, Ab major, 79 BPM | song | climb, D#6, 84 % | 99.3 | -17.9 |
| `new-age/006-soft-waves/mix.mp3` | longing, gentle, Bb minor, 58 BPM | return | lift, A#5, 63 % | 98.8 | -20.2 |
| `blend70/001-the-hidden-bridges-new-age-70-jazz-30/mix.mp3` | logit blend 0.7 / 0.3: longing, gentle, D minor, 60 BPM | return | climb, E6, 66 % | 99.3 | -19.5 |
| `blend70/002-wings-in-the-hills-new-age-70-jazz-30/mix.mp3` | logit blend 0.7 / 0.3: morning, flowing, Ab major, 77 BPM | song | lift, D#6, 88 % | 98.6 | -18.8 |

The set has variety 0.88: 4 moods, 4 feels (one a waltz), 2 modes, 6 keys, 58-87 BPM, all three layouts and three
climax kinds, and climaxes at 59-91 % of the head.

**The blends.** The 0.5 / 0.5 logit blend (best-of-12, seed 32) gave one valid piece at score 43.3
(`blend50/001-...`, kept for the record) and one invalid piece. Its jazz half wrote a jazz left hand (`ALH_*`), then a
section unknown to the forced layout. The blends now keep the Arr block in the player genre's vocabulary
(`sample.player_arr_mask`, applied with a blend or `--constrain`), but layout-section consistency is still the
model's job. The two delivered blends are 0.7 / 0.3 (best-of-16, seed 33, the 2 best of 4 that pass).

### 12.8 Answer, and what next

**Did the arrangement tokens help?**

- **As a generator, yes.**
  - The student now owns the decisions the players used to make on their own: layout, climax kind, cadences,
    hairpins, which sections play, the waltz bass.
  - It samples them with the teacher's distribution (TV 0.03-0.12).
  - A set can be spread over them: variety per 6 pieces is 0.87 against 0.72, and the climax moves through the
    head.
  - It does this at score parity, with no memorisation.
- **As a way to pass the blind test, no.**
  - The student and the teacher are equally detectable: 0/40 each, at 73-75 % confidence.
  - The tells are in the material the tokens select from: the players' and composer's single intro / build / coda
    formula, verbatim returns, a climax made from earlier bars, no modulation.
  - A student that only chooses among the teacher's options cannot leave the teacher's template. Round 1's 3/12 was
    noise.

**Next, ranked:**

1. **Widen the teacher's vocabulary where the judges point.** The arrangement tokens then expose it to the student
   at no extra cost. Concretely:
   - a developed return (reharmonized, re-rhythmed, a new continuation), drawn per return;
   - climax material derived from the motif (sequence to a new peak) with a harmonic event;
   - a key plan (a section in bVI / the relative / a step up);
   - several intro / interlude / coda frames instead of one;
   - waltz phrases built on a one-bar harmonic rhythm.
2. **Then re-export, fine-tune from base2,** and run blind round 3 at the same size (8 x 3 sources, 5 judges).
3. **Add `mel_style` to the retry checks** (still the student's main measured tell, section 4.2).
4. **Let a blend draw the arrangement from the player genre only.** Mix the logits after `EndArr`, not inside the
   block, so that 0.5 / 0.5 blends stay valid.


## 13. Phase 3: the widened teacher (2026-10-13)

**Short answer.** The warm start from base2 extends the vocabulary and the context and needs 40 % of a fresh run's
steps, so base3 from scratch is not needed. top30_3 follows the widened teacher closely: score 96.6 against 96.1,
every new arrangement key at the teacher's shares, and the lowest tells so far. In blind round 3, 6 of 40 verdicts
called a student piece composed and 4 of 40 a teacher piece (round 2: 0 and 0); the composed pieces got 36 of 40. The
judges still cannot tell the student from the teacher (p = 0.74). The remaining tells are the teacher's: climax key
blocks without a pivot, phrase ends tied into empty bars, form templates and too many rhythm cells.

### 13.1 Data (`learn export`, schema 2, master ba43ff8: the new-age r9-r12 rounds + the "every sensible choice
variable" sweep; the arrangement vocabulary is now 238 tokens: `AVary`, `AKey`, `ARubato`, `ABreath`, `AEndHold`,
`AMove_ped` ...)

| set | pieces | time |
|---|---|---|
| `data/tok3` (seeds 4000-23999 x 5, tokens only) | 100,000; 79,353 pass the arc check (new-age 13,244 = 66 %) | 830 s, 121 pieces/s |
| `data/full3` (seeds 0-3999 x 5, performed + scored) | 20,000 | about 60 min (see below) |

**Lengths: the widened teacher writes longer new-age pieces.** The per-unit `AVary` and the per-section `AKey`
(14.6 + 2 tokens per piece) and the longer forms push the context:

| genre | mean | p50 | p95 | p99 | max | over 1152 | over 1280 |
|---|---|---|---|---|---|---|---|
| new-age-piano | 876 (phase 2: 810) | 825 | **1203** | 1242 | 1298 | **1580 (11.9 %)** | 13 (0.1 %) |
| classical / lofi / jazz-piano / jazz-trio | unchanged from 12.1 | | | | | | 0 |

Every eighth new-age piece would be dropped at 1152, so **the context is now 1280** (`learn train --ctx`). The
training drops 12 of 79,353 pieces.

**Two more export bottlenecks, fixed bit-identically:**

- `TempoMap._seg` scanned the segments linearly. A performed piece now has a tempo segment per rubato phrase (the
  pianist rounds), and 13 of 32 s per classical piece went to that scan. It now bisects the segment starts. The
  export records are identical (with `PYTHONHASHSEED` fixed; see the `lh_distinct` determinism item in TODO.md) and
  the export runs 2x faster.
- The `sfz.load` memo from 12.1 still holds.

**The new teacher** (`data/full3`):

| genre | pass | score mean (sd) | p10 | best-of-8 | phase 2 (`full2`): pass / score |
|---|---|---|---|---|---|
| new-age-piano | **0.59** (breath gate 324 of 4000) | 96.0 (2.6) | 92.3 | 98.4 | 0.68 / 96.2 |
| classical / lofi / jazz | unchanged | | | | |

New-age arrangement (passing pieces):

- climax kind: grow 40 / climb 22 / theme 20 / lift 14 / step 4 %
- layout: song 45 / chorus 29 / return 26 %
- returns, per 2-bar unit (`AVary`, 14.6 per piece): orn 35 / rhythm 30 / keep 27 / seq 6 / invert 3 %
- sections in another key (`AKey`, 2 per piece): home 70 / IV 8 / bVI 8 / par 6 / bIII 3 / step 2 / rel 1 / III 1 %

### 13.2 Training: warm start from base2 against a fresh base

The vocabulary grew 749 -> 839 tokens (90 new: 69 arrangement values plus plan / note tokens of the widened
teacher). The context grew 1152 -> 1280. `learn train --init` now grows both:

- **Old rows stay.** Every old token keeps its row, so the old logits are unchanged
  (`tests/python/test_learn.py` WarmStart).
- **New tokens.** A new token starts as the mean of its key's rows (`ARit_0.68` <- every `ARit_*`), plus noise 0.01.
  An `A...` token with no relatives starts from the arrangement mean, anything else from the global mean.
- **New positions.** Each new position starts as the last trained one.

Validation loss on the same validation split of `tok3`:

| step | 500 | 1000 | 2000 | 3000 | 4000 | 4500 | 5500 | end |
|---|---|---|---|---|---|---|---|---|
| **warm** (`runs/base3w`, lr 2e-4, 2 epochs) | 0.197 | 0.197 | 0.194 | 0.192 | 0.188 | 0.187 | 0.186 | **0.1854** (5,914 steps, 46 min) |
| fresh (`runs/base3`, lr 3e-4, 5 epochs planned) | 1.305 | 0.675 | 0.330 | 0.270 | 0.240 | 0.234 | - | stopped at step 4,800 |
| base2 on `tok2` (phase 2, for scale) | - | 0.676 | 0.333 | 0.276 | 0.246 | - | - | 0.1887 (14,600 steps, 101 min) |

**The warm start wins.**

- After 500 steps it is where a fresh run is after about 10,000.
- After 2 epochs (46 min) it is below base2's full 5-epoch result.
- The fresh run tracks base2's curve step for step, so it would end near 0.187-0.19 after about 100 min.
- I stopped the fresh run at step 4,800 because the GPU was shared and overloaded; the comparison was already
  decided.
- The warm start costs 40 % of the steps and less than half the time.
- `runs/top30_3`: 800 steps at lr 1e-4 from base3w on the top 30 % of `full3` (4,448 pieces); best val 0.2345 at step
  200.

### 13.3 Validity, score and the tells against the new teacher (128 pieces per genre, top-p 0.95, retry 8)

Every student is measured against `full3` here; the old students sample with their own vocabulary and are played by
the new players (the players are deterministic and unchanged for the other genres, so their non-new-age numbers equal
section 12.3).

| genre | top30_3: all checks / score (sd) / capped | top30_2 | top30 | teacher (`full3`, passing) |
|---|---|---|---|---|
| new-age-piano | 0.977 / **96.6** (1.9) / 0 | 0.984 / 97.1 (1.8) / 0 | 0.992 / 96.9 (2.1) / 0 | 96.1 (2.5) |
| classical-piano | 1.00 / 95.6 (3.2) / 0 | 0.992 / 95.2 | 0.992 / 94.9 | 94.7 |
| lofi-piano | 0.859 / 97.8 (2.1) / 0 | 0.922 / 97.2 | 0.844 / 97.2 | 98.9 |
| jazz-piano | 1.00 / 69.6 (31.4) / 0.32 | 1.00 / 71.6 / 0.28 | 1.00 / 70.4 / 0.32 | 65.3 |
| jazz-trio | 1.00 / 68.4 (31.6) / 0.34 | 1.00 / 72.1 / 0.29 | 1.00 / 62.6 / 0.42 | 62.3 |

**Raw validity** (top-p 0.95, no retry; decodes / all checks / score / capped):

| genre | base3w | top30_3 |
|---|---|---|
| new-age-piano | 0.984 / 0.695 / 86.2 / 0.19 | 1.00 / 0.766 / 83.4 / 0.245 |
| classical-piano | 1.00 / 0.961 / 88.6 | 1.00 / 0.922 / 88.7 |
| lofi-piano | 1.00 / 0.688 / 95.5 | 1.00 / 0.727 / 95.0 |
| jazz-piano | 0.945 / 0.883 / 61.7 / 0.40 | 0.969 / 0.906 / 68.6 |
| jazz-trio | 0.961 / 0.844 / 59.5 | 0.969 / 0.883 / 68.2 |

**Tells** (median W1 of the metric distributions against the teacher, scored / unscored metrics):

| genre | top30_3 | top30_2 | top30 |
|---|---|---|---|
| new-age-piano | **0.14 / 0.24** (worst: mel_style 0.90, chords_n 0.35) | 0.23 / 0.28 (long_share 0.98, hook_sections 0.91) | 0.26 / 0.32 |
| classical-piano | 0.48 / 0.35 | | |
| lofi-piano | 0.17 / 0.11 | | |
| jazz | 0.17 / 0.20 | | |

The old students were trained on the old teacher, so on the new-age metrics they drift from the new one (twice the
W1 on the scored metrics); top30_3 is the closest.

**Novelty** (new-age, against the `tok3` index): 4-gram share seen 0.158 (teacher 0.142), bars seen 0.885 (0.875),
nearest neighbour 0.098 (0.097), 0 copies. The old students' bars_seen 0.74 / 0.76 is not comparable: `tok3` is not
their training data.

**Against the 12 composed references** (the score_metrics of the 12 pieces; per metric the set's mean in reference
sd units):

| set | n | score | median abs z | metrics within 1 sd | farthest | rep_pitch / a1_copy / block_copy / climax_copy |
|---|---|---|---|---|---|---|
| references | 12 | 98.9 (1.5) | - | - | - | - |
| teacher (`full3`) | 405 | 96.1 | 0.45 | 0.72 | peak_holes +8.6, orn32 +2.5, dyn_range -2.1, rep_pitch +1.9 | +1.9 / +0.1 / +0.6 / +0.4 |
| **top30_3** | 125 | 96.6 | 0.45 | 0.72 | peak_holes +6.4, orn32 +2.3, dyn_range -2.0, rest_max +1.7 | **+1.5** / +0.1 / +0.7 / +0.4 |
| top30_2 on the new players | 126 | 97.1 | 0.52 | 0.78 | peak_holes +7.9, orn32 +2.9, rest_max +2.1 | +0.9 / +0.2 / +0.6 / +0.4 |
| top30 on the new players | 127 | 96.9 | 0.56 | 0.78 | peak_holes +19.7, orn32 +2.6, dyn_range -2.4 | +0.7 / +0.2 / +0.7 / +0.4 |
| phase 2: teacher (`full2`, the old code's measures) | 463 | 96.4 | 0.55 | 0.78 | climax_copy +6.6, peak_holes +5.8 | +0.7 / +0.8 / +1.4 / +6.6 |
| phase 2: top30_2 | 124 | 96.9 | 0.58 | 0.78 | peak_holes +5.6, climax_copy +2.3 | +0.5 / +0.8 / +1.4 / +2.3 |

The widened teacher fixed the copying tells the judges named in round 2:

- `climax_copy` moved from +6.6 to +0.4 reference sd.
- `a1_copy` moved from +0.8 to +0.1, and `block_copy` from +1.4 to +0.6.
- The student follows the teacher exactly on these.

The widened players also lower the copying of the old students' pieces (climax_copy +0.4 for both), so that fix
lives in the players, not in the learned plans.

`rep_pitch` got worse for the teacher (+1.9) and a little less so for the student (+1.5). The largest remaining
gaps are `peak_holes`, `orn32` (ornaments per 32 bars) and the dynamic range.

### 13.4 The arrangement (new-age, top30_3 with retry, 125 pieces, against the 2,355 passing teacher pieces)

| field | TV | student | teacher |
|---|---|---|---|
| layout | 0.068 | song 41 / return 33 / chorus 26 % | 45 / 26 / 29 % |
| climax kind | 0.060 | grow 46 / climb 20 / theme 19 / lift 14 / step 2 % | 40 / 22 / 20 / 14 / 4 % |
| climax position | 0.050 | 4th 54 / 2nd 27 / 3rd 19 % | 50 / 26 / 24 % |
| cadences | 0.049 | vi 47 / home 33 / IV 21 % | 44 / 30 / 26 % |
| swell | 0.017 | | |
| returns (`AVary`) | 0.033 | orn 39 / rhythm 29 / keep 25 / seq 5 / invert 3 % | 35 / 30 / 27 / 6 / 3 % |
| keys (`AKey`) | 0.033 | home 70 / bVI 11 / IV 9 / par 6 / step 3 / bIII 2 % | 70 / 8 / 8 / 6 / 2 / 3 % |
| `ARubato` / `AEndHold` / `ABreath` | 0.055 / 0.073 / 0.106 | | |
| waltz moves (`AMove`) | 0.065 | | |
| form (sections in order) | 0.141 | | |

Every new key the widened teacher draws, the student draws with the teacher's shares (TV 0.02-0.11; it was
0.03-0.12 in phase 2).

**Variety** (the 128 pieces, no spread): 0.822 against the teacher's 0.854 (128 pieces). The student is a little less
spread in mode (0.89 against 0.95) and key (0.86 against 0.95).

### 13.5 Sets (new-age, top30_3, 48 pieces, seed 7, temperature 1.0, no retry; as in 10 and 12.5)

| run | all checks | score | variety (9 fields) | per 6 | variety (11 fields: + layout, climax kind) | per 6 | per 6, passing pieces only |
|---|---|---|---|---|---|---|---|
| set48 | 29 / 48 | 78.6 | 0.824 | 0.779 | 0.837 | 0.762 | 0.731 |
| **spread48** | 26 / 48 | 79.0 | **0.874** | **0.866** | **0.885** | **0.869** | **0.822** |
| phase 2: top30_2 spread48 | | | | 0.866 | | | |
| section 10: top30 spread | | | | 0.719 | | | |

- Without spread, set48 repeats the climax position (field variety 0.649) and the climax kind (0.824); the layout is
  already varied (0.953).
- Spread48 draws every climax kind (lift 27 / theme 27 / grow 24 / climb 22 %) and every layout (35 / 32 / 32 %).
- The spread does not cost validity (26 against 29 of 48 at temperature 1.0, within noise). Retry and best-of fill
  the rest (13.3).

### 13.6 GPU memory (the card spilled into shared system RAM)

- **Training alone fits.** One training step of the 32.6 M student at ctx 1280 and max_tokens 20,000 peaks at
  4.3 GiB allocated / 4.6 GiB reserved, well inside the 16 GiB card.
- **The spill came from concurrency.**
  - An eval process plus its 10 worker processes held 16.0 of 16.4 GiB; every CUDA process costs its own context,
    model and KV cache.
  - base3 and base3w trained at the same time: base3 dropped from 41.7k to 21.8k tok/s.
- **Now:**
  - Only the parent process holds the model on the GPU.
  - The worker pools (`evaluate.cpu_pool`, used by eval / sample scoring and by the export) start with
    `CUDA_VISIBLE_DEVICES=-1`, so a worker cannot open a CUDA context even if something imports torch there.
  - Training logs `vram_gib` (`torch.cuda.max_memory_reserved`) at every validation and in the final line; eval logs
    the peak in its last line.
  - GPU jobs run strictly one at a time; the phase-3 evals, samples and renders ran as one sequential chain.
  - `-1`, not an empty value: on Windows an empty value removes the variable, so the workers would still see the
    card (the test caught it).
- **Not measured yet:** the eval / sample peak under the new log line (the next GPU run will print it; TODO.md).

### 13.7 Blind round 3 (24 packets, 5 judges; the round-2 protocol)

**Setup:**

- **Packets:** 8 student, 8 teacher and 8 composed pieces, the composed drawn from the 12 references (seeded
  `learn-blind-3`).
- **Student:** top30_3, grammar, spread, best-of-8, top-p 0.95, seed 21; the first 8 rows that pass the render gate,
  in order.
  - Rows 3 and 6, both waltzes, failed the render's breath gate, so rows 8 and 9 took their places.
  - No row was picked by score.
- **Teacher:** `endless new-age-piano --count 8 --candidates 8`.
- **Judges:** five foreground judges in isolated folders: three composers, a pianist and a statistician. Only the
  scorer read the KEY.

| source | judged 'composed' | round 2 |
|---|---|---|
| composed | **36 / 40** | 31 / 40 |
| student (top30_3) | **6 / 40** | 0 / 40 |
| teacher (`full3`'s generator) | **4 / 40** | 0 / 40 |

- **The judges were right 106 of 120 times:**
  - composerA 18 / 24
  - composerB 20 / 24
  - pianist 20 / 24
  - composerC and the statistician 24 / 24
- **Student vs teacher:** Fisher p = 0.74, so the judges cannot tell the student from the teacher, as in round 2.
- **Student vs composed:** p = 7e-12.
- **Fooled at least once:**
  - Student pieces: 5 of 8. Two pieces fooled 2 of 5 judges: B minor 'flowing' (row 9) and D minor 'gentle'.
  - Teacher pieces: 3 of 8.
  - In round 2, no generated piece fooled any judge.
- **The student's waltz** (row 8, the only student piece in 3/4) fooled no one: the statistician counted its
  "X | X/inversion" two-bar chord grid.

**What the judges still name** (their Advice sections, consistent across all five):

1. **The climax.**
   - Unprepared chromatic blocks under an octave-up A1 cell at v100-120: an E-major block in Ab, D# / G#maj7 in A
     minor, Fm6 straight after G7.
   - Neighbour-note cells or scale runs instead of a transformed theme.
   - Most likely the widened teacher's new key plan (`AKey`, the 'grow' climax): a key change is now drawn, but
     without a pivot or a way back (my reading; the judges only see the chords).
2. **Phrase ends.** A late note held over the barline into a bar with no right hand. The statistician counts 0-1 of
   these per composed piece against several per generated piece.
3. **Form templates.**
   - Five pieces share "build 7-9 | climax 9 | inter 2 (= the intro) | A3 6 | coda 3".
   - Four share the fixed "A B A build climax A coda" frame.
   - 19 of 24 pieces put the highest note at 70-79 % of the piece.
4. **Rhythm cells.** 0.33-0.49 distinct right-hand cells per bar against 0.12-0.30 in the composed pieces. The
   composed pieces repeat one or two motto cells at fixed formal places.
5. **Melody against the harmony.** Long notes are chord tones 69-79 % of the time, against 88-98 % in the composed
   pieces.
6. **A chorus of held notes** (B1 as a column of long notes).
7. **The waltz's two-bar harmonic grid** (named in round 2 as well).

The copying tells of round 2 (verbatim returns, a copied climax) are mostly gone. When they still appear, they
appear as "A3 copies A1 with a thinner left hand", in both teacher and student pieces.

### 13.8 Renders (`D:/agentsound-learn/renders/schema3/`, the new-age players, through the endless render gate)

A varied set: top30_3, spread, grammar, best-of-8, top-p 0.95, seed 31. Row 0, a Db-major waltz, failed the render's
breath gate (quiet1 0.228 < 0.25). It was replaced by the first passing waltz of a second spread draw: seed 32,
best-of-16, row 1.

| piece | header | layout / sections | climax: kind, pitch, position | score | LUFS / LRA |
|---|---|---|---|---|---|
| `new-age/001-paper-stones-of-the-morning-waltz` | morning, waltz 3/4, Bb major, 85 BPM | return | lift, C6, 82 % of the head | 95.9 | -18.8 / 11.2 |
| `new-age/002-gardens-to-the-rain` | rain, gentle, A minor, 66 BPM | return: intro A1 A2 B1 build climax inter A3 coda | lift, C6, 89 % | 99.4 | -19.9 / 13.1 |
| `new-age/003-northern-gardens-of-snowfall` | longing, flowing, E major, 69 BPM | song: intro A1 A2 B1 A3 build climax A4 coda | climb, B5, 90 % | 99.4 | -19.0 / 14.5 |
| `new-age/004-other-gardens-of-dawn` | hopeful, bright, C major, 84 BPM | return: intro A1 A2 B1 build climax A3 coda | theme, C6, 52 % | 99.0 | -17.7 / 14.7 |
| `new-age/005-after-dawn` | morning, flowing, Ab major, 79 BPM | song: intro A1 A2 B1 build climax A4 coda | grow, B5, 84 % | 99.9 | -18.7 / 12.3 |
| `new-age/006-after-summer` | longing, gentle, Bb minor, 58 BPM | chorus: intro A1 B1 A2 build climax A4 coda | climb, C6, 53 % | 98.5 | -20.4 / 14.2 |
| `blend70/001-stones-of-autumn-new-age-70-jazz-30` | longing, gentle, D minor, 60 BPM | chorus: intro A1 B1 A2 build climax A4 coda | theme, C#6, 91 % | 100.0 | -19.3 / 14.9 |
| `blend70/002-little-footsteps-of-the-tide-new-age-70-jazz-30` | morning, flowing, Ab major, 77 BPM | return: intro A1 A2 B1 build climax A3 coda | grow, G#5, 58 % | 99.2 | -18.4 / 14.2 |

- **The set:** all four moods, all four feels, all three layouts and all four main climax kinds (lift 2, climb 2, theme 1,
  grow 1). The climax falls early (52-53 %) in two pieces and late (82-90 %) in four.
- **The blends:** a logit blend of new-age 0.7 and jazz-piano 0.3, played by the new-age players; 4 drawn, best-of-16,
  the best 2 rendered.
  - All 4 passed (98.2 mean); variety 0.95.
  - The new-age players keep the surface, as in 12.7.
- **Waltzes and the breath gate.** Of the student's 5 waltz candidates in this phase (blind rows 3, 6, 8; set rows 0
  and b1), 3 failed the render gate's breath check (quiet1 under 0.25), although each was the best of 8 candidates.
  This is a student weakness to fix with a waltz-aware retry (TODO.md).

### 13.9 Answer

- **Does the warm start work?** Yes.
  - Growing the embedding / head (new rows from their key's mean) and the positions (from the last trained one)
    starts at val 0.197, where a fresh run is after about 10k steps.
  - It ends at 0.1854 after 2 epochs (46 min). A fresh base would need about 5 epochs and 100 min to reach the same
    loss.
  - It costs 40 % of the steps. A fresh base3 is not needed.
- **Does the student follow the widened teacher?** Yes, closely.
  - Validity: 98 % pass with retry, new-age score 96.6 against the teacher's 96.1.
  - Tells: median W1 0.14 scored / 0.24 unscored, the lowest of any student so far.
  - Every new arrangement key is drawn at the teacher's shares (TV 0.02-0.11).
  - Novelty is at the teacher's level, with 0 copies.
  - Against the 12 references it sits where the teacher sits: median |z| 0.45, 72 % of the metrics within 1 sd.
- **The old students on the new players.** top30_2 and top30 still pass and score as well as before. Their plans
  lack `AVary` / `AKey` / 'grow', and their tells against the new teacher are twice as large.
- **Is it indistinguishable from composed music?** Not yet, but it moved.
  - Round 3: 6 / 40 'composed' verdicts for the student and 4 / 40 for the teacher (round 2: 0 / 0). The composed
    pieces got 36 / 40.
  - Student and teacher stay indistinguishable from each other (p = 0.74). The student is as good as its teacher;
    to fool the judges further, the teacher has to improve.
- **What to fix in the teacher next** (judges' advice, ranked):
  1. Climaxes built from the theme, with a prepared key plan (pivot and return) instead of chromatic blocks.
  2. Phrase ends on a strong beat with a pickup, not a tie into an empty bar.
  3. Fewer, recurring motto rhythm cells.
  4. Chord tones under long notes.
  5. Varied section proportions and peak positions.
  6. A waltz harmonic rhythm that is not "X | X/inversion".
- **The orchestra genre.** Master added it during this phase. It is left out of training and eval for now: the
  student's genre set is pinned (`GENRE_NAMES`), and a new genre needs a conditioning row plus its own export /
  scoring path (the orchestra's band, `endless.orchestra`). That is not a trivial export.
- **base3 EXIT 1.** `runs/base3.out` ends with EXIT 1 at step 4,800 because I stopped the fresh run deliberately
  (13.2). It did not crash.
