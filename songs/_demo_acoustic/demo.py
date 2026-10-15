"""The played acoustic guitar demos (shared builders): a singer-songwriter strum with chucks and a fingerpicked
ballad, each on any guitar patch - sampled/acoustic_guitar (the played acoustic: Shinyguitar's mic set with its
chucks, mutes and finger noises, guitarist hand 'acoustic' / 'fingerstyle') or the old sampled/steel_guitar (FSS:
2 layers, one sample per note, no noises) for the A/B. The song files (song.py, fingerpick.py, strum_fss.py) call
these; build them with --out (README of the folder: song.py's docstring)."""
from agentsound import *
from agentsound import guitarist as gtr

ACOUSTIC = 'sampled/acoustic_guitar'
STEEL = 'sampled/steel_guitar'


def _space(s: Song, limiter_gain: float) -> None:
    """A small wooden room (the guitar's own patch sends: room + a little hall) and a gentle master."""
    s.bus('room', 'bus/ir_room_small')
    s.hall(decay=2.2)
    s.master.add(fx.compressor(threshold=-16, ratio=1.6, attack=30, release=250, name='glue'))
    s.master.add(fx.limiter(gain=limiter_gain, release=200))


def strum(patch: str = ACOUSTIC, title: str = 'Acoustic strum', seed: int = 7, gain_db: float = -8.0) -> Song:
    """~47 s at 96 BPM in G: a let-ring intro, a verse of chuck strumming (the backbeat a muted strum), an open
    strummed chorus, the last chord ringing - guitarist.arrange(style='songwriter') section by section."""
    t = 96
    s = Song(title, tempo=t, key='G major', seed=seed)
    intro = s.section('intro', bars=2, prog=s.prog('G Cadd9'))
    verse = s.section('verse', bars=8, prog=s.prog('G D Em C G D C C'))
    chorus = s.section('chorus', bars=8, prog=s.prog('C G D Em C G D D'))
    outro = s.section('outro', bars=2, prog=s.prog('G G'))
    _space(s, 6.0)
    g = s.track('guitar', patch, gain_db=gain_db)
    mem = gtr.Memory()
    order = [intro, verse, chorus, outro]
    for i, sec in enumerate(order):
        nxt = order[i + 1] if i + 1 < len(order) else None
        arr = gtr.arrange(sec.prog, bpm=t, key=s.key, style='songwriter', section=sec, sound=g, memory=mem,
                          seed=seed, into=nxt, section_end=nxt is not None, hand='acoustic')
        arr.play(g, sec)
    return s


def fingerpick(patch: str = ACOUSTIC, title: str = 'Acoustic fingerpicking', seed: int = 5,
               gain_db: float = -4.0) -> Song:
    """~46 s at 76 BPM in C: a ballad arpeggio intro, Travis picking through the A section, the last phrase
    arpeggiated and slowing into a let-ring ending - guitarist.arrange(style='fingerstyle') and the player's calm
    body (track.humanize(body='calm'): phrase arcs, the ritardando into the end)."""
    t = 76
    s = Song(title, tempo=t, key='C major', seed=seed)
    intro = s.section('intro', bars=2, prog=s.prog('C Fmaj7'))
    verse = s.section('verse', bars=8, prog=s.prog('C Am7 Fmaj7 G C Em F G'))
    bridge = s.section('bridge', bars=3, prog=s.prog('Am F G'))
    outro = s.section('outro', bars=1, prog=s.prog('C'))
    _space(s, 6.0)
    # the thumb's low strings fill 250-500 Hz in a solo picked part: a little room for them
    g = s.track('guitar', patch, gain_db=gain_db, fx=[fx.eq({'peak1.freq': 320, 'peak1.gain': -2.0, 'peak1.q': 1.0})])
    g.humanize(body='calm')
    mem = gtr.Memory()
    order = [intro, verse, bridge, outro]
    for i, sec in enumerate(order):
        nxt = order[i + 1] if i + 1 < len(order) else None
        arr = gtr.arrange(sec.prog, bpm=t, key=s.key, style='fingerstyle', section=sec, sound=g, memory=mem,
                          seed=seed, into=nxt, section_end=nxt is not None, hand='fingerstyle')
        arr.play(g, sec)
    return s
