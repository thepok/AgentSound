"""Low Ceiling Blues - a minor blues with a riff head for solo piano (C minor, 4/4, straight 8ths, 104 BPM).

The "pro" reference for the blind comparison against the endless jazz-piano generator: the SAME sound (the endless
jazz-piano genre's band, set up by agentsound.endless.perform.band: the solo_piano preset, the master gain, the
'piano' profile) and the same shape class as an endless blues (intro 4 | head = two 12-bar choruses | three solo
choruses | head out = two choruses | tag 4 | rolled ending 2), played by the same players (pianist.arrange via
jazz.chorus, soloist.solo with the pianist's vocabulary, song.ending). What differs is the writing (ARRANGEMENT.md).
Build: python -m agentsound build songs/pro-piano-blues
"""
import functools
import random

from agentsound import jazz, pianist, soloist
from agentsound.endless import Tune, genre
from agentsound.endless.composer import Harm, melody_issues
from agentsound.endless import perform
from agentsound.endless.perform import end_clips
from agentsound.song import Song
from agentsound.theory import Key, note

GENRE = genre('jazz-piano')
FEEL = 'straight'
METER = 4
SEED = 7319                      # the performance seeds (pianist / soloist dice), as an endless tune's seed


# ------------------------------------------------------------------------------------------------ the lead sheet

def changes(spec: str) -> list:
    """'Cm9 Gm7b5:0.5 ...' (bars, default 1) -> [(symbol, beats)]."""
    out = []
    for tok in spec.split():
        sym, _, bars = tok.partition(':')
        out.append((sym, float(bars or 1) * METER))
    return out


def mel(spec: str) -> list:
    """'C5:0.5 C5:0.5 ... | r:0.5 G5:0.5 ...' (beats; '|' = bar line, checked) -> [(start, dur, midi)]."""
    out, t = [], 0.0
    for b, bar in enumerate(spec.split('|')):
        bt = 0.0
        for tok in bar.split():
            p, _, d = tok.partition(':')
            d = float(d)
            if p != 'r':
                out.append((t + bt, d, note(p)))
            bt += d
        if abs(bt - METER) > 1e-6:
            raise ValueError(f"bar {b + 1} holds {bt:g} beats: {bar.strip()!r}")
        t += METER
    return out


# A1: the minor blues as it is (Ab13 - G7alt), a ii-V turnaround. A2: the twist - bar 8 a ii-V that promises Db, bar
# 9 the Neapolitan Dbmaj7#11 instead of the bVI7, its #11 (G) = the tonic's fifth, then G7alt home.
FIRST6 = 'Cm9 Fm9 Cm9 Gm7b5:0.5 C7b9:0.5 Fm9:2'
CHANGES = {
    'A1': changes(FIRST6 + ' Cm9:2 Ab13 G7alt Cm9:0.5 Ab13:0.5 Dm7b5:0.5 G7alt:0.5'),
    'A2': changes(FIRST6 + ' Cm9 Ebm9:0.5 Ab13:0.5 Dbmaj7#11 G7alt Cm9 Dm7b5:0.5 G7alt:0.5'),
}

# THE RIFF (two bars): repeated tonic, the minor third, then the blue climb F - F# - G; answered by a fall back
# G F Eb C. AAB: riff on I, a short call over the ii-V into IV, the riff a fourth up on IV, the riff home, then the
# punchline (a rising arpeggio to the top, falling through the altered dominant).
RIFF = 'C5:0.5 C5:0.5 Eb5:0.5 C5:0.5 F5:0.5 F#5:0.5 G5:1 | r:0.5 G5:0.5 F5:0.5 Eb5:0.5 C5:1.5 r:0.5 | '
CALL = 'r:2.5 Eb5:0.5 D5:0.5 C5:0.5 | Bb4:1.5 r:0.5 Db5:0.5 E5:0.5 G5:1 | '
RIFF_IV = 'F5:0.5 F5:0.5 Ab5:0.5 F5:0.5 Bb5:0.5 B5:0.5 C6:1 | r:0.5 C6:0.5 Bb5:0.5 Ab5:0.5 F5:1.5 r:0.5 | '
RIFF_1 = 'C5:0.5 C5:0.5 Eb5:0.5 C5:0.5 F5:0.5 F#5:0.5 G5:1 | '
MELODY = {
    'A1': mel(RIFF + CALL + RIFF_IV + RIFF_1 + 'r:0.5 G5:0.5 F5:0.5 Eb5:0.5 C5:1.5 r:0.5 | '
              'Eb5:0.5 F5:0.5 Ab5:0.5 C6:2 r:0.5 | B5:1.5 Ab5:0.5 F5:1 Eb5:1 | D5:1 C5:1 r:2 | r:2 Ab4:1 B4:1'),
    # the second chorus: the riff's answer bends to Gb over the Ebm9 (the twist in the tune too), the punchline
    # turns into the Neapolitan: a rising Db arpeggio onto G held as its #11, down the altered dominant, home
    'A2': mel(RIFF + CALL + RIFF_IV + RIFF_1 + 'r:0.5 Gb5:0.5 F5:0.5 Eb5:0.5 C5:1.5 r:0.5 | '
              'Ab4:0.5 C5:0.5 F5:0.5 G5:2 r:0.5 | F5:1.5 Eb5:0.5 Db5:1 B4:1 | C5:3 r:1 | r:4'),
}
# The head out's first chorus is THE climax: the riff voiced in octaves / locked hands, the punchline climbs to
# Eb6 (the top of the tune) and falls through the altered dominant's b5
A1_OUT = mel(RIFF + CALL + RIFF_IV + RIFF_1 + 'r:0.5 G5:0.5 F5:0.5 Eb5:0.5 C5:1.5 r:0.5 | '
             'Eb5:0.5 Ab5:0.5 C6:0.5 Eb6:2 r:0.5 | Db6:1 B5:0.5 Ab5:0.5 F5:1 Eb5:1 | D5:1 C5:1 r:2 | r:2 Ab4:1 B4:1')

# intro: the riff alone, an octave down, in tempo (a groove, not a rubato lead-in), a rising G7alt arpeggio into
# the head
INTRO = {'changes': changes('Cm9 Fm9 Cm9 Dm7b5:0.5 G7alt:0.5'),
         'melody': mel('C4:0.5 C4:0.5 Eb4:0.5 C4:0.5 F4:0.5 F#4:0.5 G4:1 | r:0.5 G4:0.5 F4:0.5 Eb4:0.5 C4:1.5 r:0.5 | '
                       'C4:0.5 C4:0.5 Eb4:0.5 C4:0.5 F4:0.5 F#4:0.5 G4:1 | r:0.5 Ab4:0.5 B4:0.5 D5:0.5 F5:1 r:1')}
# tag: the riff twice against the Neapolitan (Cm9 - Dbmaj7#11, the A2 twist as a vamp), the last G held as the
# Db's #11 - and the end chord answers it: a rolled Cm6/9
TAG = {'changes': changes('Cm9 Dbmaj7#11 Cm9 Dbmaj7#11'),
       'melody': mel(RIFF_1 + 'r:0.5 G5:0.5 F5:0.5 Eb5:0.5 C5:1.5 r:0.5 | ' + RIFF_1 + 'G5:3 r:1')}

TUNE = Tune(genre=GENRE.name, seed=SEED, mood='blue', title='Low Ceiling Blues', key='C minor', mode='minor',
            tempo=104, meter=METER, feel=FEEL, swing=None, form='blues', parts=['A1', 'A2'],
            changes=CHANGES, melody=MELODY, motif=[n for n in MELODY['A1'] if n[0] < 2 * METER],
            intro=INTRO, tag=TAG, end_chord='Cm69',
            blocks={'A1': ['minor_blues'], 'A2': ['minor_blues_neapolitan']})

ANALYSIS = {'profile': GENRE.band['profile']}
# honest tags (composed, not generated); the blind judge gets neutral lead sheets, not these tags
METADATA = {'title': TUNE.title, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#22336b', '#8fb3d9'], 'title': TUNE.title.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': 731}


def check_melody() -> list:
    """The endless composer's own melody checks on every part (clashes, register, leaps, the final note)."""
    k = Key(TUNE.key)
    out = []
    for p, notes, ch, fin in (('A1', MELODY['A1'], CHANGES['A1'], None), ('A2', MELODY['A2'], CHANGES['A2'], {0, 3, 7}),
                              ('A1_out', A1_OUT, CHANGES['A1'], None)):
        out += [f"{p}: {i}" for i in melody_issues(notes, Harm(ch, set(k.pcs)), note('G4'), note('Eb6'), meter=METER,
                                                    final_pcs=fin)]
    return out


# ------------------------------------------------------------------------------------------------ the performance

def build() -> Song:
    for issue in check_melody():
        print('melody check:', issue)
    print(TUNE.describe())
    t, sd = TUNE, SEED
    F, P = GENRE.feels[FEEL], GENRE.plan
    s = Song(t.title, tempo=t.tempo, key=t.key, seed=sd % 100000 + 1, tail=6, meter=(METER, 4))
    parts = {p: t.changes_str(p) for p in t.parts}
    # the solo: chorus 1 and 2 on the plain blues, chorus 3 (the build's top) on the Neapolitan twist
    parts.update(S1=t.changes_str('A1'), S2=t.changes_str('A1'), S3=t.changes_str('A2'),
                 intro=t.changes_str(changes=INTRO['changes']), tag=t.changes_str(changes=TAG['changes']),
                 end=f"{t.end_chord}:2")
    intro, head, solo, out, tag, end = s.form('intro:4 head:A1,A2 solo:S1,S2,S3 out:A1,A2 tag:4 end:2', parts=parts)

    feel = jazz.Feel(t.tempo, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0}, beats_per_bar=METER)
    b = perform.band(s, GENRE, FEEL, feel)          # the endless genre's sound, by construction
    lh = F['lh']
    mem = pianist.Memory()
    lo, hi = F['touch']
    orn = dict(P['head']['ornaments'], blues_crush=1.2)            # a blues pianist's crushed thirds
    play = functools.partial(jazz.chorus, b, memory=mem, defaults=dict(
        piano=dict(lh=lh, lh_vel=54, style=F['style'], ornaments=orn, lh_answers=0.85), bass=None, drums=None))

    # ---- intro: the riff alone, unaccompanied (no left hand), in time, a G7alt arpeggio up into the head
    play(intro, t.clip(INTRO['melody'], intro.length), bass=None, drums=None,
         piano=dict(style='sparse', density=0.45, seed=sd % 997 + 11, lead_in=False, touch=(lo - 10, hi - 14),
                    lh=None, section_end=True))

    # ---- head: the first chorus states the riff, the second (the twist) a shade stronger
    play(head, [t.melody_clip(p) for p in t.parts], lh_pedal=True,
         piano=dict(seed=sd % 997 + 101, lead_in=True, touch=jazz.each((lo - 4, hi - 6), (lo, hi + 2)),
                    density=jazz.each(0.55, 0.65), A1=dict(lead_in=False)))

    # ---- solo: three choruses that BUILD out of the riff's two bars (statement - development - burst - climax),
    # straight into the head out, whose first chorus is the summit; the fast figure saved for the third chorus
    bud = soloist.Budget(spice_every=2, fast_every=16, same_every=32, bpb=METER)
    bud.save(solo.parts[-1].start + 2 * METER)
    voc = pianist.vocabulary(F['solo'], lh_track=b.comp, lh=lh, lh_vel=56, memory=mem, seed=sd % 997 + 201,
                             phrase_bars=2, vel=(50, 102))
    soloist.solo(s, b.piano, voc, at=solo, prog=solo.prog, motif=t.clip(t.motif, 2 * METER), budget=bud,
                 seed=sd % 997 + 211, arc='build', energy=0.8)

    # ---- head out: the riff at full strength (octaves / locked hands, the Eb6 punchline), then the twist chorus
    # settles back down into the tag
    out_mel = [jazz.paraphrase(t.clip(A1_OUT, t.part_beats('A1')), seed=sd % 997 + 301, anticipate=0.1, delay=0.05,
                               embellish=0.1, key=s.key),
               jazz.paraphrase(t.melody_clip('A2'), seed=sd % 997 + 302, anticipate=0.2, delay=0.1, embellish=0.15,
                               key=s.key)]
    play(out, out_mel, lh_pedal=True,
         piano=dict(seed=sd % 997 + 311, lead_in=True, touch=jazz.each((lo + 12, hi + 20), (lo - 4, hi - 6)),
                    density=jazz.each(0.85, 0.55), A1=dict(climax=True)))

    # ---- no hole between the sections: an arpeggio sweep where the right hand left the bar before empty
    last_sym = t.changes['A2'][-1][0]
    for k, boundary in enumerate((solo.start, out.start)):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(2.0, boundary - last - 0.5)
            b.piano.play(pianist.sweep(last_sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=sd % 997 + 351 + k),
                         boundary - dur)

    # ---- tag + ending: the riff against the Neapolitan, its G held as the Db's #11, a rolled Cm6/9 answers
    play(tag, t.clip(TAG['melody'], tag.length), pedal_end=end.start - 0.1, lh_pedal=True, piano=dict(
        touch=(lo - 8, hi - 18), style='ballad', density=0.5, seed=sd % 997 + 401, lead_in=True, lh='tenths',
        lh_vel=48, bpm=t.tempo * 0.85, section_end=False))
    lh_end, rh_end = end_clips(t.end_chord, METER)
    s.ending(end, chords=[(b.comp, lh_end, 70), (b.piano, rh_end, 80, 0.25)],
             rit=tag.bar(tag.bars // 2), to=0.75, hold=2, length=4, room=(-13, -8))
    return s
