# Film director (making-of)

> **Role:** film-director - crafts the making-of film of a finished song: finds the song's real story in its logs,
> picks the angle, the moments, the words and the looks, and writes them as `songs/<slug>/film.py`.
> **When to use:** after delivery (the A&R said `ship`, or the user asks "show me how it was made"); again when a
> song gets a revision worth telling.
> **Inputs:** the song folder (`BRIEF.md` with its log, `ARRANGEMENT.md`, `SOUND.md`, `MIX.md`, `MASTER.md`, `AR.md`,
> `song.py`, `out/` of a build), the facts dict (`python -m agentsound makingof songs/<slug> --draft` prints them
> into a first draft), the song's git history, `recipes/HUMAN_FEEDBACK.md` (the user's quotes about this song).
> **Deliverable:** `songs/<slug>/film.py` (the film as code) and `songs/<slug>/out/making-of.mp4`
> (`python -m agentsound makingof songs/<slug>`), looked at (stills) before it is handed over.

A brief for whoever makes a song's making-of - a sub-agent, the main agent with a fresh hat, or a person. Songs are
not all the same, and neither are their films: the library is shared, the film is made to measure.

## The reusable parts (agentsound/makingof)

- **Facts** (`facts.py`, `docs.py`, `capture.py`): everything the files say - the wish, the log per role, the form
  with keys / tempi / meters, the hook and every place it returns (found in the render JSON), per-track sound / why /
  level / width / note dynamics, the players' moves on their exact beats (recorded while song.py builds), the A&R
  issues and the revision's before -> after numbers, the credits.
- **Chapters** (`film.py`, `Film` methods - any order, any number): `cold_open` (the wish typed as chat bubbles,
  the title card), `team`, `blueprint` (form, tempo, energy, the hook drawn as notes), `act` (a part of the song
  under its own scene, its sections and words), `tracks` (every part soloed from its stem, then the band back in),
  `performance` (track lanes with the players' moves popping on their frames), `crisis` (the A&R stamp, the ranked
  issues), `tried` (before / after: the judged build against today, the same bars, loudness-matched, the measured
  change), `song` (the whole song with audio-reactive scenes), `credits`.
- **Looks**: scenes per section (`Film.look`): `nebula`, `ink` (smoke and a candle), `ring` (a spectrum ring round
  the cover), `grid` (synthwave horizon), `mandala` (climaxes), `scope` (vectorscope ribbons), `+hw` the 3D note
  highway; the palette comes from the cover.
- **Voice**: `N(...)` the narrator, `AR(...)` the A&R's voice, a delivery direction of 3-12 words each.

## Method

1. Build the song if needed; run `python -m agentsound makingof songs/<slug> --draft` and read the draft: it lists
   what the files hold. Then read the files themselves - the story is rarely in the numbers alone.
2. **Find the story.** What was hard, surprising or fought over? A revise verdict and its fix (AR.md), a hook-sound
   shoot-out (SOUND.md), a user's complaint and what changed (HUMAN_FEEDBACK.md), a form with acts (ARRANGEMENT.md),
   a solo with a player's moves. Choose ONE angle and let the chapters serve it; cut what does not.
3. **Shape it like the song.** A four-part epic can be told in four `act`s under four looks; a synthwave drive can
   ride the grid; a ballad can stay by the candle. Pick the scenes per section in `look()` by the song's genre and
   energy arc, not by habit.
4. **Pick the moments** by the logs: the excerpts where the players' moves cluster, the bars an A&R issue names
   (`tried` episodes), the stems that carry the hook.
5. **Write the narration** (English): short, spoken sentences, one to three per line, at most ~260 characters.
   Every claim must be in the files - quote the A&R's issue as written, give the logged before -> after numbers,
   never invent a judgement ("it sounded bad") that no log states. Numbers may stay as digits (`-12.6 LUFS`); the
   narration speaks them.
6. **Voice (Breeze TTS 2)**: one frozen voice per role (the approved narrator, a second approved voice for the A&R),
   the identity never redesigned per line; a short per-line direction for the performance only; the raw chunks are
   cached and measured, each speaker gets one fixed gain from its median loudness (-18 LUFS), never per-sentence
   normalisation; vocal events (`(sigh)`) sparingly. Breeze is slow (~8x real time): the first render of a film
   takes a while, later ones only synthesise changed lines. Its licence is research / non-commercial - it is named
   in the credits. `--tts sapi` or `none` for quick looks.
7. **Look before handing over**: `--stills 12,40,95,...` (PNG frames) and `--preview` (960x540, 15 fps, a short
   song) until typography, spacing and sync are right; then the full render.

## Checklist (HUMAN_FEEDBACK and the facts-only rule)

- [ ] Every line is backed by a file (quote or number); the user's own words are quoted, not paraphrased into a
      judgement.
- [ ] The film has one story, told in the song's shape - not the draft's generic order.
- [ ] Before / after clips play the same bars, loudness-matched, with the measured change on screen.
- [ ] The scenes fit the section (calm = slow and soft, climaxes explosive), no flicker, moves land on their frames.
- [ ] The credits carry the CC-BY attributions and the narration's licence.

## Must not

- Invent facts, quotes or judgements; restate a number the logs do not have.
- Edit the song (song.py, the role files) to make the film easier - the film tells what happened.
- Copy reference audio or sample packs into the repo; publish the film without checking the credits' licences.
