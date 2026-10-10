"""Kites over Bank Street - a bright jazz waltz for solo piano (AABA, F major, 3/4, straight 8ths).

The "pro" reference for the blind comparison against the endless jazz-piano generator: the SAME sound (the endless
jazz-piano genre's band, set up by agentsound.endless.perform.band: the solo_piano preset, the master gain, the
'piano' profile) and the same shape class (intro | head AABA | one solo chorus | head out from the bridge | tag |
rolled ending), played by the same players (pianist.arrange via jazz.chorus, soloist.solo with the pianist's
vocabulary, song.ending). What differs is the writing: a through-composed lead sheet (see ARRANGEMENT.md).
Build: python -m agentsound build songs/pro-piano-waltz
"""
import functools
import random

from agentsound import jazz, pianist, soloist
from agentsound.endless import Tune, genre
from agentsound.endless.composer import Harm, melody_issues
from agentsound.endless import perform
from agentsound.endless.perform import end_clips
from agentsound.song import Song
from agentsound.theory import Key, chord, note, note_name

GENRE = genre('jazz-piano')
FEEL = 'waltz'
METER = 3
SEED = 4127                      # the performance seeds (pianist / soloist dice), as an endless tune's seed


# ------------------------------------------------------------------------------------------------ the lead sheet

def changes(spec: str) -> list:
    """'Fmaj9:2 Am7 ...' (bars, default 1) -> [(symbol, beats)]."""
    out = []
    for tok in spec.split():
        sym, _, bars = tok.partition(':')
        out.append((sym, float(bars or 1) * METER))
    return out


def mel(spec: str) -> list:
    """'C5:1.5 D5:0.5 F5:1 | E5:2.5 r:0.5 | ...' (beats; '|' = bar line, checked) -> [(start, dur, midi)]."""
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


A_CHANGES = 'Fmaj9:2 Bbmaj7#11:2 Am7 D7b9 Gm9 C13 Am7 Abdim7 Gm9 C7b9'
CHANGES = {
    'A1': changes(A_CHANGES + ' Am7 D7b9 Gm9 C13'),                  # turnaround back to the top
    'A2': changes(A_CHANGES + ' Fmaj9:2 Cm9 F13'),                   # home, then ii-V into the IV
    'B': changes('Bbmaj9:2 Ebm9 Ab13 Dbmaj9:2 Gm7b5 C7b9 Am7 D7b9 Gm9 Bbm6 Am7 Ab13 Gm9 C7b9'),
    'A3': changes(A_CHANGES + ' Dbmaj7#11 C7sus4 Fmaj9:2'),         # deceptive: bVI (the bridge's key) - V - I
}

# The hook: a dotted lilt up to a held major 7th (C D F | E), sequenced onto the IV where the SAME E becomes its #11
# (the tune's colour); the second half answers with a falling line onto the b9 of the D7, climbs to the 13th of C,
# then the hook rhythm sequenced a third higher reaches the B natural over the diminished chord (the #11 again).
A_HEAD = ('C5:1.5 D5:0.5 F5:1 | E5:2.5 r:0.5 | D5:1.5 E5:0.5 A5:1 | E5:2.5 r:0.5 | '
          'G5:1.5 F5:0.5 E5:1 | Eb5:2 F#5:1 | G5:1 A5:1 Bb5:1 | A5:2.5 r:0.5 | '
          'E5:1.5 G5:0.5 C6:1 | B5:2.5 r:0.5 | A5:1.5 G5:0.5 F5:1 | E5:1 Db5:1 Bb4:1 | ')
MELODY = {
    'A1': mel(A_HEAD + 'C5:1.5 D5:0.5 E5:1 | F#5:1.5 Eb5:0.5 C5:1 | D5:2.5 r:0.5 | r:1 A4:1 Bb4:1'),
    'A2': mel(A_HEAD + 'A4:1 C5:1 E5:1 | F5:2.5 r:0.5 | Eb5:1.5 D5:0.5 C5:1 | r:1.5 F5:0.5 A5:0.5 C6:0.5'),
    # the bridge: long high notes falling (contrast: register, rhythm, the Db key), then the hook rhythm low
    'B': mel('D6:3 | C6:1 A5:1 F5:1 | Gb5:2 F5:1 | Eb5:1 F5:2 | C6:3 | Bb5:1 Ab5:1 F5:1 | Db6:2 Bb5:1 | '
             'E5:2.5 r:0.5 | E5:1 A5:1 C6:1 | C6:2 F#5:1 | Bb5:1.5 A5:0.5 G5:1 | G5:1.5 F5:0.5 Db5:1 | '
             'C5:1.5 E5:0.5 G5:1 | F5:2.5 r:0.5 | Bb5:1.5 A5:0.5 F5:1 | E5:1 A4:1 Bb4:1'),
    # the last A: the hook rhythm returns over the Db (F G C: its #11 again), the sus chord, home on the 3rd
    'A3': mel(A_HEAD + 'F5:1.5 G5:0.5 C6:1 | Bb5:2.5 r:0.5 | A5:3 | r:3'),
}
# The head out's bridge is THE climax: the second half climbs to Eb6 (the b9 of the D7 on top), falls through Gm9
B_OUT = mel('D6:3 | C6:1 A5:1 F5:1 | Gb5:2 F5:1 | Eb5:1 F5:2 | C6:3 | Bb5:1 Ab5:1 F5:1 | Db6:2 Bb5:1 | '
            'E5:2.5 r:0.5 | G5:1 C6:1 E6:1 | Eb6:2 C6:1 | D6:1.5 C6:0.5 Bb5:1 | Db6:1.5 Bb5:0.5 G5:1 | '
            'C5:1.5 E5:0.5 G5:1 | F5:2.5 r:0.5 | Bb5:1.5 A5:0.5 F5:1 | E5:1 A4:1 Bb4:1')

# intro: the hook's second bar-pair and the answer's b9 over the IV, alone and rubato; the hook's pickup into the head
INTRO = {'changes': changes('Bbmaj7#11:2 Am7 D7b9 Gm9 Bbm6 Gm9 C13'),
         'melody': mel('D5:1.5 E5:0.5 A5:1 | E5:3 | G5:1.5 F5:0.5 E5:1 | Eb5:3 | Bb4:1.5 C5:0.5 D5:1 | Db5:3 | '
                       'A4:3 | r:1 A4:1 Bb4:1')}
# tag: the A3's deceptive Db / sus cadence twice - first with the Db hook, then the hook's head on the IV with its
# #11 held, the last ii-V, the hook's first bar over the tonic (the end chord brings the 9th on top)
TAG = {'changes': changes('Dbmaj7#11 C7sus4 Bbmaj7#11:2 Gm9 C13 Fmaj9:2'),
       'melody': mel('F5:1.5 G5:0.5 C6:1 | Bb5:3 | C5:1.5 D5:0.5 F5:1 | E5:3 | A4:1.5 Bb4:0.5 D5:1 | E5:3 | '
                     'C5:1.5 D5:0.5 F5:1 | r:3')}

TUNE = Tune(genre=GENRE.name, seed=SEED, mood='bright', title='Kites over Bank Street', key='F major', mode='major',
            tempo=150, meter=METER, feel=FEEL, swing=None, form='AABA', parts=['A1', 'A2', 'B', 'A3'],
            changes=CHANGES, melody=MELODY, motif=[n for n in MELODY['A1'] if n[0] < 2 * METER],
            intro=INTRO, tag=TAG, end_chord='F69',
            blocks={'A1': ['I_IV_lydian', 'iii_VI_ii_V_turn'], 'A2': ['I_IV_lydian', 'home_v_I7'],
                    'B': ['IV_bVI_cycle'], 'A3': ['I_IV_lydian', 'bVI_V_I']})

ANALYSIS = {'profile': GENRE.band['profile']}
# honest tags (composed, not generated); the blind judge gets neutral lead sheets, not these tags
METADATA = {'title': TUNE.title, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#2f7a6b', '#f0c75e'], 'title': TUNE.title.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': 412}


def check_melody() -> list:
    """The endless composer's own melody checks on every part (clashes, register, leaps, the final note)."""
    k = Key(TUNE.key)
    out = []
    for p in TUNE.parts + ['B_out']:
        notes = B_OUT if p == 'B_out' else MELODY[p]
        ch = CHANGES['B' if p == 'B_out' else p]
        fin = {5, 9, 0} if p == 'A3' else None
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
    parts.update(A=t.changes_str('A1'), intro=t.changes_str(changes=INTRO['changes']),
                 tag=t.changes_str(changes=TAG['changes']), end=f"{t.end_chord}:4")
    intro, head, solo, out, tag, end = s.form('intro:8 head:AABA solo:AABA out:B,A3 tag:8 end:4', parts=parts)

    feel = jazz.Feel(t.tempo, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0}, beats_per_bar=METER)
    b = perform.band(s, GENRE, FEEL, feel)          # the endless genre's sound, by construction
    lh = F['lh']
    rng = random.Random(f"perform:{sd}")
    mem = pianist.Memory()
    lo, hi = F['touch']
    orn = P['head']['ornaments']
    play = functools.partial(jazz.chorus, b, memory=mem, defaults=dict(
        piano=dict(lh=lh, lh_vel=54, style=F['style'], ornaments=orn), bass=None, drums=None))

    # ---- intro: alone, rubato, ballad touch - the hook's IV-colour bars and its b9 answer, the pickup into the head
    play(intro, t.clip(INTRO['melody'], intro.length), bass=None, drums=None,
         piano=dict(style='ballad', density=0.5, seed=sd % 997 + 11, lead_in=True, touch=(lo - 6, hi - 14),
                    lh='tenths', lh_vel=46, section_end=True))
    s.rubato(intro, depth=F['rubato'] + 0.02, phrase='lean')

    # ---- head: A1 plain and singing, A2 a shade more, the bridge opens up, A3 settles
    lift = (-4, 0, 6, 2)
    dens = F['density']
    play(head, [t.melody_clip(p) for p in t.parts], lh_pedal=True,
         piano=dict(seed=sd % 997 + 101, lead_in=True,
                    touch=jazz.each(*[(lo + lf // 2, hi + lf) for lf in lift]),
                    density=jazz.each(*[min(0.9, dens + 0.1 * (lf / 8)) for lf in lift]), A1=dict(lead_in=False)))

    # ---- solo: one chorus that BUILDS (statement -> development -> burst -> climax) out of the hook's two bars and
    # runs straight into the head-out bridge, the tune's one planned summit; the fast figure is saved for the
    # solo's last A
    bud = soloist.Budget(spice_every=2, fast_every=16, same_every=32, bpb=METER)
    bud.save(solo.parts[-1].start + 2 * METER)
    voc = pianist.vocabulary(F['solo'], lh_track=b.comp, lh=lh, lh_vel=56, memory=mem, seed=sd % 997 + 201,
                             phrase_bars=4, vel=(54, 104))
    soloist.solo(s, b.piano, voc, at=solo, prog=solo.prog, motif=t.clip(t.motif, 2 * METER), budget=bud,
                 seed=sd % 997 + 211, arc='build', energy=0.85)

    # ---- head out: the bridge at full height (the Eb6 climax, octaves / locked hands), the last A settles
    out_mel = [jazz.paraphrase(t.clip(B_OUT, t.part_beats('B')), seed=sd % 997 + 301, anticipate=0.15, delay=0.05,
                               embellish=0.1, key=s.key),
               jazz.paraphrase(t.melody_clip('A3'), seed=sd % 997 + 302, anticipate=0.25, delay=0.1, embellish=0.15,
                               key=s.key)]
    play(out, out_mel, lh_pedal=True,
         piano=dict(seed=sd % 997 + 311, lead_in=True, touch=jazz.each((lo + 10, hi + 18), (lo - 2, hi - 4)),
                    density=jazz.each(0.85, 0.6), B=dict(climax=True)))

    # ---- no hole between the sections: an arpeggio sweep where the right hand left the bar before empty
    last_sym = t.changes['A3'][-1][0]
    for k, boundary in enumerate((solo.start, out.start)):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(1.5, boundary - last - 0.5)
            b.piano.play(pianist.sweep(last_sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=sd % 997 + 351 + k),
                         boundary - dur)

    # ---- tag + ending: the deceptive cadence again, the hook's head on the IV, a rolled F6/9 with the 9th on top
    play(tag, t.clip(TAG['melody'], tag.length), pedal_end=end.start - 0.1, lh_pedal=True, piano=dict(
        touch=(lo - 6, hi - 14), style='ballad', density=0.5, seed=sd % 997 + 401, lead_in=True, lh='tenths',
        lh_vel=46, bpm=t.tempo * 0.85, section_end=False))
    lh_end, rh_end = end_clips(t.end_chord, METER)
    s.ending(end, chords=[(b.comp, lh_end, 70), (b.piano, rh_end, 80, 0.25)],
             rit=tag.bar(tag.bars // 2), to=0.72, hold=2, length=4, room=(-13, -8))
    return s
