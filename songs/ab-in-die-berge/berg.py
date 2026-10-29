"""Ab in die Berge! - every music cue of the kids' audio drama (D:/Projekte/hoerspiele/bergurlaub/manifest.json).

One function per cue (CUES), each its own short Song, rendered one by one by render_all.py (song.py picks the cue
from $BERG_CUE). Series colour from songs/drachen-sandkasten: F major, xylophone / clarinet / bassoon / upright bass /
brushes / glockenspiel; the Drachen hook is quoted in intro, einschlafen and outro.

New material (original):
  BERG   - the "Ab in die Berge" theme: a rising fifth-to-octave call (the mountain), a stepwise answer, half
           cadence; the second phrase climbs to the 10th and settles home. Harmony I vi ii V | I vi IV-V I.
  NACHT  - the night / music-box lullaby (trost, nacht_ende).
  LIEBE  - the love theme in Bb (liebe, huette_ende).
Solo cues end on a held final chord that rings out (Song tail = the reverb tail); beds ("unter") are sparse, keep
their lead colours soft and above / below the speech centre, and end on a held chord that can be faded.
"""
import json as _json
from pathlib import Path as _Path

from agentsound import *
from agentsound import hornist

HERE = _Path(__file__).resolve().parent
try:
    LEVELS = _json.loads((HERE / 'levels.json').read_text(encoding='utf-8'))
except (OSError, ValueError):
    LEVELS = {}

# ---------------------------------------------------------------------------------------------- material

BERG_A = '1:1/4. 5:1/8 8:1/2 | 7:1/8 6:1/8 5:1/4 6:1/4 3:1/4 | 4:1/4. 5:1/8 6:1/4 9:1/4 | 5:1/1'
BERG_B = '1:1/4. 5:1/8 8:1/2 | 10:1/8 9:1/8 8:1/4 6:1/4 8:1/4 | 4:1/4 6:1/4 5:1/4 2:1/4 | 1:1/1'
BERG_HEAD = '1:1/4. 5:1/8 8:1/2'                       # the mountain call (1 bar)
BERG_PROG_A = 'I vi ii V'
BERG_PROG_B = 'I vi IV:0.5 V:0.5 I'

DRACHE = ('1:1/8 3:1/8 5:1/8 r:1/8 6:1/8 5:1/8 3:1/4 | 4:1/8 6:1/8 8:1/8 r:1/8 7:1/8 6:1/8 5:1/4 '
          '| 6:1/8 5:1/8 4:1/8 3:1/8 2:1/8 3:1/8 4:1/8 2:1/8 | 5:1/4 r:1/8 5:1/8 8:1/4 r:1/4')
DRACHE_HEAD = '1:1/8 3:1/8 5:1/8 r:1/8 6:1/8 5:1/8 3:1/4'
DRACHE_PROG = 'I vi IV V'

NACHT = '5:1/4 3:1/8 5:1/8 8:1/2 | 7:1/4 5:1/4 6:1/2 | 4:1/4 6:1/8 4:1/8 3:1/4 2:1/4 | 1:1/1'
NACHT_PROG = 'I iii ii:0.5 V:0.5 I'

LIEBE = ('3:1/2 5:1/4 6:1/4 | 5:1/1 | 4:1/2 3:1/4 2:1/4 | 3:1/1 '
         '| 3:1/2 5:1/4 8:1/4 | 7:1/2 6:1/2 | 5:1/4 4:1/4 2:1/2 | 1:1/1')
LIEBE_PROG = 'I iii IV vi I V:0.5 vi:0.5 ii:0.5 V:0.5 I'        # in Bb major

ACC = [1.15, 0.8, 0.95, 0.82]                         # bouncing 8ths: strong / passing

# patch, gain_db, pan (None = the patch's seat), sends
KIT = {
    'clarinet': ('sampled/solo_clarinet', -1, 0.3, {'plate': -12}),
    'xylo': ('sampled/xylophone', -3, 0.5, {'plate': -10}),
    'glock': ('sampled/glockenspiel', -6, -0.35, None),
    'accordion': (None, -8, 0.25, {'hall': -10}),
    'strings': ('sampled/strings', -6, None, None),
    'bassoon': ('sampled/bassoon', -5, -0.25, None),
    'bass': ('sampled/upright_bass', -4, None, {'plate': -16}),
    'brushes': ('sampled/brush_kit', -9, None, {'hall': -14}),
    'perc': ('sampled/orchestral_percussion', -6, None, None),
    'celesta': ('sampled/celesta', -5, 0.25, None),
    'celli': ('sampled/celli', -4, -0.1, None),
    'basses': ('sampled/double_basses', -6, 0.05, None),
    'violas': ('sampled/violas', -6, -0.25, None),
    'violins': ('sampled/violins', -8, -0.25, None),
    'pizz': ('sampled/strings_pizz', -6, None, None),
    'trem': ('sampled/strings_tremolo', -9, None, None),
    'horn': ('sampled/solo_horn', -2, -0.1, {'hall': -8}),
    'horns': ('sampled/french_horns', -7, -0.15, None),
    'trumpet': ('sampled/solo_trumpet', -3, 0.1, {'hall': -9}),
    'timp': ('sampled/timpani_rolls', -6, None, None),
    'musicbox': ('gm/music_box', -4, 0.15, None),
    'harp': ('sampled/harp', -7, 0.2, None),
}


def base(title, cue, tempo, *, key='F major', meter=None, tail=3.0, seed=11, hall_decay=None, bed=False):
    s = Song(f'Ab in die Berge - {title}', tempo=tempo, key=key, seed=seed, sample_rate=44100, tail=tail,
             meter=meter)
    s.hall(**({'decay': hall_decay} if hall_decay else {}))
    s.plate()
    eq = {'hp.freq': 30}
    if bed:                                            # beds step out of the speech centre
        eq.update({'peak1.freq': 330, 'peak1.gain': -1.5, 'peak1.q': 0.8,
                   'peak2.freq': 1900, 'peak2.gain': -3.5, 'peak2.q': 0.6})
    s.master.add(fx('eq', eq))
    s.master.add(fx.width(width=1.0, monobass=140))
    s.master.add(fx.limiter(gain=float(LEVELS.get(cue, 0.0)), release=220, lookahead=8))
    return s


def tr(s, name, *, gain=0.0, pan=False, fx=(), sends=None, id=None):
    """a track from KIT (gain= trims the kit gain, pan= overrides)."""
    patch, g, p, snd = KIT[name]
    if name == 'accordion':
        patch = inst.sf2('Accordion', attack=1.6, release=1.6)
    sd = dict(snd or {})
    sd.update(sends or {})
    return s.track(id or name, patch, gain_db=g + gain, pan=(p if pan is False else pan), fx=list(fx),
                   sends=sd or None)


def mo(s, spec, octave=4, vel=96, gate=0.92):
    return s.motif(spec).clip(octave=octave, vel=vel, gate=gate).vel_random(7, seed=len(spec))


def wind(s, track, spec, at, *, family='clarinet', octave=4, vel=(70, 100), seed=1, section='verse'):
    """a written line through the wind player (air, vibrato on the held peaks)."""
    perf = hornist.arrange(mo(s, spec, octave), s.tempo, family=family, style='classical', section=section,
                           vel=vel, seed=seed)
    perf.place(track, at)
    return track


def stirs(kit, start, end, every, vel=70):
    """continuous brush 'shhh': a slow stir every `every` beats."""
    b = start
    while b < end - 0.01:
        kit.note(60, b, every, vel=vel)
        b += every


def held(s, numeral, beats, register=('C3', 'C5'), vel=60, voices=4):
    """one held chord of `beats` beats."""
    return s.prog(numeral).block(register=register, vel=vel, voices=voices).slice(0, beats)


# ---------------------------------------------------------------------------------------------- solo cues

def cue_intro():
    """M01 solo 14 s: the Berg theme on clarinet + xylophone, accordion reed colour, Drachen hook answer."""
    s = base('Intro', 'intro', 112)
    a = s.section('thema', 4, prog=s.prog(BERG_PROG_A))
    d = s.section('drache', 1, prog=s.prog('IV:0.5 V:0.5'))
    end = s.section('ende', 1, prog=s.prog('I'))

    clar, xylo, acc = tr(s, 'clarinet'), tr(s, 'xylo'), tr(s, 'accordion')
    strings, bsn, bass = tr(s, 'strings'), tr(s, 'bassoon'), tr(s, 'bass')
    glock, kit, perc = tr(s, 'glock'), tr(s, 'brushes').humanize(3, 5), tr(s, 'perc')

    wind(s, clar, BERG_A, a, seed=3, section='chorus')
    xylo.play(mo(s, BERG_A, 5, vel=80).vel_pattern(ACC, grid='1/8'), a)
    xylo.play(mo(s, DRACHE_HEAD, 5, vel=96).vel_pattern(ACC, grid='1/8').transpose_scale(3, s.key), d)
    clar.play(mo(s, '6:1/4 r:1/4 7:1/4 r:1/4', 4, vel=72).articulate('staccato'), d)
    clar.play(mo(s, '8:1/1', 4, vel=78, gate=1.0), end)
    xylo.play(mo(s, '1:1/8 5:1/8 8:1/4 r:1/2', 5, vel=92), end)
    glock.play(mo(s, '8:1/4 r:3/4', 6, vel=74), a.bar(1))
    glock.play(mo(s, '5:1/8 8:1/8 r:3/4', 6, vel=78), end)

    acc.chords(a, d, end, voicing='close', register=('F3', 'F4'), voices=3, vel=72)
    strings.chords(a, d, end, voicing='spread', register=('C3', 'C5'), vel=72)
    bsn.chords(a, d, voicing='close', register=('F2', 'F3'), voices=1, rhythm='x...x...', vel=80,
               then=lambda c: c.articulate('staccato'))
    bass.bassline('root', a, d, rate='1/2', vel=88)
    bass.bassline('root', end, rate='1/1', vel=84)
    walk = drums({'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
    kit.plan({a: walk.velocity(0.75), d: walk.velocity(0.8)})
    perc.note(81, end, 4, vel=96)                                          # triangle on the final chord
    strings.automate('gainDb', ramp(end.start, end.end, 0, -6))
    acc.automate('gainDb', ramp(end.start, end.end, 0, -8))
    return s


def cue_fahrt_kurz():
    """M02 solo 6 s: a short driving groove, brushes + upright bass, a little xylophone tag."""
    s = base('Fahrt kurz', 'fahrt_kurz', 126, tail=2.2)
    g = s.section('groove', 2, prog=s.prog('I ii:0.5 V:0.5'))
    end = s.section('ende', 1, meter=(2, 4), prog=s.prog('I'))
    bass, kit, xylo = tr(s, 'bass', gain=1), tr(s, 'brushes', gain=2).humanize(3, 5), tr(s, 'xylo', gain=-2)
    bass.bassline('walk', g, low='E1', vel=96)
    bass.note('F1', end, 2, vel=100)
    groove = drums({'kick': 'x.....x...x.....', 'snare': '....x.......x..o', 'ride': 'x..xx..xx..xx..x'})
    kit.plan({g: groove.velocity(0.85)})
    stirs(kit, g.start, g.end, 2, vel=60)
    kit.note('kick', end, 1, vel=80).note('crash', end, 2, vel=58)
    xylo.play(mo(s, '5:1/8 6:1/8 7:1/8 8:1/8', 5, vel=84), g.bar(1, 2))
    xylo.play(mo(s, '8:1/4', 5, vel=96), end)
    return s


def cue_zeitsprung():
    """M04 solo 4 s: a xylophone run up, 'Stunden spaeter', glockenspiel sparkle on the chord."""
    s = base('Zeitsprung', 'zeitsprung', 120, tail=2.0)
    run = s.section('lauf', 1, prog=s.prog('V:0.5 I:0.5'))
    xylo, glock, harp, strings = tr(s, 'xylo'), tr(s, 'glock'), tr(s, 'harp'), tr(s, 'strings', gain=-3)
    up = mo(s, '1:1/16 2:1/16 3:1/16 4:1/16 5:1/16 6:1/16 7:1/16 8:1/16', 5, vel=80).crescendo(0.7, 1.15)
    xylo.play(up, run)
    xylo.play(mo(s, '5:1/16 r:1/16 8:1/4. r:1/8', 5, vel=104), run.bar(0, 2))
    glock.play(mo(s, '8:1/4 r:1/4', 6, vel=88), run.bar(0, 2.25))
    harp.play(mo(s, '1:1/16 3:1/16 5:1/16 8:1/16 10:1/4 r:1/4', 4, vel=70), run.bar(0, 2))
    strings.play(held(s, 'V', 2, vel=52), run)
    strings.play(held(s, 'I', 2, vel=60), run.bar(0, 2))
    return s


def cue_ankunft():
    """M06 solo 8 s: arrival fanfare, trumpet + glockenspiel, the Berg theme big."""
    s = base('Ankunft', 'ankunft', 112, tail=2.5)
    f = s.section('fanfare', 2, prog=s.prog('I IV:0.5 V:0.5'))
    end = s.section('ende', 1, prog=s.prog('I'))
    tpt, horns, glock = tr(s, 'trumpet'), tr(s, 'horns'), tr(s, 'glock')
    strings, basses, timp, perc = tr(s, 'strings', gain=1), tr(s, 'basses'), tr(s, 'timp'), tr(s, 'perc', gain=-3)
    xylo = tr(s, 'xylo', gain=-4)
    line = '1:1/4. 5:1/8 8:1/2 | 6:1/8 7:1/8 8:1/4 9:1/4 7:1/4 | 8:1/1'
    wind(s, tpt, line, f, family='trumpet', vel=(84, 112), seed=5, section='chorus')
    glock.play(mo(s, line, 6, vel=82), f)
    xylo.play(mo(s, '1:1/8 3:1/8 5:1/8 8:1/8', 5, vel=88), f.bar(1, 2))
    horns.chords(f, end, voicing='close', register=('F3', 'F4'), voices=3, vel=88)
    strings.chords(f, end, voicing='spread', register=('C3', 'F5'), vel=90)
    basses.bassline('root', f, rate='1/2', low='E1', vel=96)
    basses.note('F1', end, 4, vel=96)
    timp.play(mo(s, '1:1/4 r:1/4 r:1/2', 2, vel=96).articulate('hit'), f)
    timp.play(mo(s, '5:1/2', 2, vel=88).articulate('hit'), f.bar(1, 2))
    timp.play(mo(s, '1:1/1', 2, vel=96).articulate('hit'), end)
    perc.note(49, end, 4, vel=96)                                           # crash on the arrival chord
    strings.automate('gainDb', ramp(end.start, end.end, 0, -6))
    horns.automate('gainDb', ramp(end.start, end.end, 0, -6))
    return s


def cue_abend():
    """M07 solo 8 s: evening transition, celesta + strings, quiet - the Berg call slowed into a plagal close."""
    s = base('Abend', 'abend', 76, tail=2.6, hall_decay=3.4)
    a = s.section('ruf', 1, prog=s.prog('I'))
    end = s.section('ende', 1, prog=s.prog('IV:0.5 I:0.5'))
    cel, strings, harp = tr(s, 'celesta', gain=2), tr(s, 'strings', gain=-2), tr(s, 'harp', gain=-3)
    cel.play(mo(s, BERG_HEAD, 5, vel=72), a)
    cel.play(mo(s, '6:1/8 5:1/8 4:1/4 3:1/2', 5, vel=66), end)
    cel.play(mo(s, 'r:1/2 1:1/8 3:1/8 5:1/4', 6, vel=50), end)
    strings.chords(a, end, voicing='spread', register=('C3', 'C5'), vel=58)
    harp.arp('up', a, rate='1/8', register=('F3', 'F4'), vel=58, gate=1.0, then=lambda c: c.vel_random(10))
    strings.automate('gainDb', ramp(end.bar(0, 2), end.end, 0, -5))
    return s


def cue_nacht_ende():
    """M09 solo 6 s: the night theme dissolves, glockenspiel."""
    s = base('Nacht Ende', 'nacht_ende', 80, tail=2.2, hall_decay=3.6)
    a = s.section('nacht', 1, prog=s.prog('ii:0.5 V:0.5'))
    end = s.section('ende', 1, meter=(2, 4), prog=s.prog('I'))
    box, glock, strings = tr(s, 'musicbox'), tr(s, 'glock', gain=-1), tr(s, 'strings', gain=-4)
    box.play(mo(s, '4:1/4 6:1/8 4:1/8 3:1/4 2:1/4', 5, vel=72), a)
    glock.play(mo(s, '1:1/8 3:1/8 5:1/8 8:1/8', 6, vel=62).crescendo(0.8, 1.0), end)
    box.play(mo(s, '1:1/2', 5, vel=66), end)
    strings.chords(a, end, voicing='spread', register=('C3', 'C5'), vel=54)
    strings.automate('gainDb', ramp(a.bar(0, 2), end.end, 0, -8))
    return s


def cue_sonne():
    """M12 solo 8 s: the fog lifts (D minor -> Bb), the Berg call warm on the horn into F major, glockenspiel."""
    s = base('Sonne', 'sonne', 92, tail=2.4)
    a = s.section('nebel_weg', 1, prog=s.prog('vi:0.5 IV:0.5'))
    b = s.section('sonne', 1, prog=s.prog('I'))
    end = s.section('ende', 1, meter=(2, 4), prog=s.prog('I'))
    horn, strings, harp, glock = tr(s, 'horn'), tr(s, 'strings'), tr(s, 'harp'), tr(s, 'glock', gain=-2)
    basses = tr(s, 'basses')
    wind(s, horn, '1:1/4. 5:1/8 8:4', b, family='trombone', octave=3, vel=(78, 100), seed=7, section='chorus')
    strings.chords(a, b, end, voicing='spread', register=('C3', 'A5'), vel=74)
    strings.automate('gainDb', ramp(a.start, b.start, -10, 0), ramp(end.start, end.end, 0, -5))
    harp.play(mo(s, '1:1/16 2:1/16 3:1/16 4:1/16 5:1/16 6:1/16 7:1/16 8:1/16 '
                    '9:1/16 10:1/16 11:1/16 12:1/16 13:1/16 14:1/16 15:1/16', 3, vel=72), a.bar(0, 2))
    glock.play(mo(s, '5:1/8 8:1/8 r:1/4 10:1/8 12:1/8 r:1/4', 6, vel=70), b.bar(0, 2))
    glock.play(mo(s, '8:1/4 r:1/4', 6, vel=66), end)
    basses.bassline('root', a, b, rate='1/2', low='E1', vel=84)
    basses.note('F1', end, 2, vel=84)
    return s


def cue_huette_ende():
    """M14 solo 6 s: the love theme turns cheerful on the xylophone (Bb major)."""
    s = base('Huette Ende', 'huette_ende', 132, key='Bb major', tail=2.0)
    a = s.section('heiter', 2, prog=s.prog('I IV:0.5 V:0.5'))
    end = s.section('ende', 1, meter=(2, 4), prog=s.prog('I'))
    xylo, clar, pizz, bass = tr(s, 'xylo'), tr(s, 'clarinet', gain=-4), tr(s, 'pizz', gain=-2), tr(s, 'bass')
    kit, glock = tr(s, 'brushes').humanize(3, 5), tr(s, 'glock', gain=-3)
    line = '3:1/8 3:1/8 5:1/8 6:1/8 5:1/4 r:1/8 5:1/8 | 6:1/8 5:1/8 4:1/8 3:1/8 2:1/8 4:1/8 7:1/8 5:1/8'
    xylo.play(mo(s, line, 5, vel=92).vel_pattern(ACC, grid='1/8'), a)
    xylo.play(mo(s, '8:1/8 r:1/8 8:1/4', 5, vel=100), end)
    clar.play(mo(s, '3:1/2 5:1/4 6:1/4 | 4:1/2 2:1/2', 4, vel=72), a)
    clar.play(mo(s, '1:1/2', 4, vel=70), end)
    pizz.chords(a, end, voicing='close', register=('D3', 'D4'), voices=3, rhythm='..x...x.', vel=80)
    bass.bassline('root', a, rate='1/4', low='E1', vel=88)
    bass.note('Bb1', end, 2, vel=96)
    kit.plan({a: drums({'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'},
                       vel=75)})
    kit.note('crash', end, 2, vel=55)
    glock.play(mo(s, '8:1/4', 6, vel=72), end)
    return s


def cue_gipfel():
    """M17 solo 8 s: the Berg theme big, full orchestra, cymbals."""
    s = base('Gipfel', 'gipfel', 100, tail=2.6, hall_decay=3.0)
    f = s.section('gipfel', 2, prog=s.prog('I IV:0.5 V:0.5'))
    end = s.section('ende', 1, meter=(3, 4), prog=s.prog('I'))
    tpt, horn, horns = tr(s, 'trumpet', gain=1), tr(s, 'horn', gain=-1), tr(s, 'horns', gain=2)
    strings, violins, basses = tr(s, 'strings', gain=2), tr(s, 'violins', gain=1), tr(s, 'basses', gain=1)
    timp, perc, glock, xylo = tr(s, 'timp', gain=1), tr(s, 'perc'), tr(s, 'glock'), tr(s, 'xylo', gain=-3)
    line = '1:1/4. 5:1/8 8:1/2 | 10:1/8 9:1/8 8:1/4 9:1/4 7:1/4 | 8:3'
    wind(s, tpt, line, f, family='trumpet', octave=4, vel=(92, 120), seed=9, section='climax')
    wind(s, horn, line, f, family='trombone', octave=3, vel=(86, 112), seed=10, section='chorus')
    violins.play(mo(s, line, 5, vel=96), f)
    glock.play(mo(s, line, 6, vel=84), f)
    horns.chords(f, end, voicing='close', register=('F3', 'F4'), voices=3, vel=96)
    strings.chords(f, end, voicing='spread', register=('C3', 'C5'), vel=96)
    basses.bassline('root', f, rate='1/2', low='E1', vel=104)
    basses.note('F1', end, 3, vel=104)
    timp.play(mo(s, '1:1/4 r:1/4 1:1/8 1:1/8 5:1/4', 2, vel=104).articulate('hit'), f)
    timp.play(mo(s, '1:2', 2, vel=88), f.bar(1, 2))                         # a roll into the summit
    timp.play(mo(s, '1:3', 2, vel=112).articulate('hit'), end)
    perc.note(48, f.bar(1), 4, vel=88)                                       # suspended cymbal swell
    perc.note(49, end, 3, vel=112).note(35, end, 3, vel=100)                # crash + bass drum
    xylo.play(mo(s, '1:1/16 3:1/16 5:1/16 8:1/16', 5, vel=96), end)
    for t in (strings, horns, violins):
        t.automate('gainDb', ramp(end.bar(0, 1), end.end, 0, -6))
    return s


def cue_outro():
    """M19 solo 16 s: Berg theme + Drachen hook merged, a long final chord."""
    s = base('Outro', 'outro', 112, tail=2.8, hall_decay=3.0)
    d = s.section('drache', 2, prog=s.prog('I vi'))
    b = s.section('berg', 2, prog=s.prog('I vi'))
    c = s.section('kadenz', 1, prog=s.prog('IV:0.5 V:0.5'))
    end = s.section('ende', 2, prog=s.prog('I:2'))
    clar, xylo, horn = tr(s, 'clarinet'), tr(s, 'xylo'), tr(s, 'horn', gain=-1)
    acc, strings, bsn, bass = tr(s, 'accordion', gain=-2), tr(s, 'strings'), tr(s, 'bassoon'), tr(s, 'bass')
    glock, kit, perc, timp = tr(s, 'glock'), tr(s, 'brushes').humanize(3, 5), tr(s, 'perc', gain=-2), tr(s, 'timp')

    hook2 = '1:1/8 3:1/8 5:1/8 r:1/8 6:1/8 5:1/8 3:1/4 | 1:1/8 3:1/8 6:1/8 r:1/8 5:1/8 4:1/8 3:1/4'
    wind(s, clar, hook2, d, seed=12, section='chorus', vel=(78, 104))
    xylo.play(mo(s, hook2, 5, vel=88).vel_pattern(ACC, grid='1/8'), d)
    wind(s, horn, '1:1/4. 5:1/8 8:1/2 | 7:1/8 6:1/8 5:1/4 6:1/4 3:1/4', b, family='trombone', octave=3,
         vel=(84, 106), seed=13, section='chorus')
    xylo.play(mo(s, DRACHE_HEAD, 6, vel=70).vel_pattern(ACC, grid='1/8'), b.bar(1))  # the dragon answers
    clar.play(mo(s, '5:1/4 r:1/8 5:1/8 8:1/4 r:1/4', 4, vel=90), c)                 # the hook's cadence
    xylo.play(mo(s, '5:1/4 r:1/8 5:1/8 8:1/4 r:1/4', 5, vel=96), c)
    clar.play(mo(s, '8:6', 4, vel=82, gate=1.0), end)
    horn.play(mo(s, '5:6', 3, vel=76, gate=1.0), end)
    glock.play(mo(s, '1:1/8 3:1/8 5:1/8 8:1/8 r:1/2', 6, vel=82), end)
    glock.play(mo(s, '8:1/4 r:3/4', 6, vel=74), b)

    acc.chords(d, b, c, end, voicing='close', register=('F3', 'F4'), voices=3, vel=70)
    strings.chords(d, b, c, end, voicing='spread', register=('C3', 'C5'), vel=78)
    bsn.chords(d, b, c, voicing='close', register=('F2', 'F3'), voices=1, rhythm='x...x...', vel=80,
               then=lambda x: x.articulate('staccato'))
    bass.bassline('root', d, b, c, rate='1/2', vel=88)
    bass.note('F1', end, 6, vel=88)
    walk = drums({'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
    kit.plan({d: walk.velocity(0.75), b: walk.velocity(0.75), c: walk.velocity(0.8)})
    perc.note(49, end, 6, vel=90).note(81, end.bar(0, 2), 4, vel=80)
    timp.play(mo(s, '1:6', 2, vel=70), end)                                 # soft roll under the last chord
    for t in (strings, acc, timp):
        t.automate('gainDb', ramp(end.bar(0, 2), end.end, 0, -9))
    return s


# ---------------------------------------------------------------------------------------------- beds (unter)

def cue_fahrt_bett():
    """M03 bed (>= 46 s): very quiet groove, brushes + upright bass, a faint string floor."""
    s = base('Fahrt Bett', 'fahrt_bett', 120, tail=3.0, bed=True)
    g = s.section('groove', 26, prog=s.prog('I:2 vi:2 ii:2 V:2'))
    end = s.section('ende', 2, prog=s.prog('I:2'))
    bass, kit, strings = tr(s, 'bass'), tr(s, 'brushes').humanize(3, 5), tr(s, 'strings', gain=-8)
    bass.bassline('walk', g, low='E1', vel=82)
    bass.note('F1', end, 4, vel=84)
    groove = drums({'snare': '....x.......x...', 'ride': 'x..xx..xx..xx..x', 'pedal': '....x.......x...'},
                   vel=60)
    kit.plan({g: groove})
    stirs(kit, g.start, g.end, 2, vel=55)
    stirs(kit, end.start, end.bar(1), 2, vel=45)
    strings.chords(g, end, voicing='spread', register=('C3', 'C4'), voices=3, vel=50)
    kit.automate('gainDb', ramp(end.start, end.end, 0, -12))
    strings.automate('gainDb', ramp(end.start, end.end, 0, -8))
    return s


def cue_geheimnis():
    """M05 bed (>= 18 s): celesta + low strings, mysterious (D minor)."""
    s = base('Geheimnis', 'geheimnis', 72, key='D minor', tail=3.5, hall_decay=3.6, bed=True)
    a = s.section('geheimnis', 6, prog=s.prog('i VI iv V i VI'))
    end = s.section('ende', 1, prog=s.prog('i'))
    celli, basses, cel = tr(s, 'celli'), tr(s, 'basses'), tr(s, 'celesta', gain=-2)
    violas = tr(s, 'violas', gain=-6)
    celli.chords(a, end, voicing='spread', register=('D2', 'D3'), voices=2, vel=64)
    basses.bassline('root', a, end, rate='1/1', low='C1', vel=70)
    violas.chords(a, voicing='close', register=('D3', 'D4'), voices=2, vel=50)
    fig = ['5:1/8 r:1/8 4:1/8 r:1/8 3:1/4 r:1/2', 'r:1/2 #4:1/8 r:1/8 5:1/4',
           '1:1/8 r:1/8 b2:1/8 r:1/8 1:1/4 r:1/2', 'r:1/2 #7:1/8 r:1/8 8:1/4']
    for i in range(6):
        cel.play(mo(s, fig[i % 4], 6, vel=58 + (i % 2) * 6), a.bar(i))
    cel.play(mo(s, '5:1/4 r:1/4 1:1/2', 6, vel=54), end)
    celli.automate('gainDb', ramp(end.start, end.end, 0, -6))
    return s


def cue_trost():
    """M08 bed (>= 50 s): warm strings, the music-box night tune, very quiet."""
    s = base('Trost', 'trost', 64, tail=3.5, hall_decay=3.6, bed=True)
    a1 = s.section('a1', 4, prog=s.prog(NACHT_PROG))
    b1 = s.section('b1', 4, prog=s.prog('vi IV ii V'))
    a2 = s.section('a2', 4, prog=s.prog(NACHT_PROG))
    b2 = s.section('b2', 3, prog=s.prog('vi IV V'))
    end = s.section('ende', 1, prog=s.prog('I'))
    box, strings = tr(s, 'musicbox', gain=-3), tr(s, 'strings', gain=-4)
    harp, celli = tr(s, 'harp', gain=2), tr(s, 'celli', gain=-4)
    box.play(mo(s, NACHT, 5, vel=66), a1)
    box.play(mo(s, '5:1/4 3:1/8 5:1/8 8:1/2 | 9:1/4 8:1/4 6:1/2 | 4:1/4 6:1/8 4:1/8 3:1/4 2:1/4 | 1:1/1', 5,
                vel=62), a2)
    box.play(mo(s, 'r:1/2 3:1/4 2:1/4 | r:1 | r:1/2 6:1/4 5:1/4', 5, vel=56), b1)
    box.play(mo(s, '1:1/2', 5, vel=54), end)
    strings.chords(a1, b1, a2, b2, end, voicing='spread', register=('C3', 'C5'), vel=56)
    celli.bassline('root', a1, b1, a2, b2, end, rate='1/1', low='C2', vel=58)
    harp.arp('up', b1, b2, rate='1/4', register=('F3', 'F4'), vel=48, gate=1.0, then=lambda c: c.vel_random(10))
    strings.automate('gainDb', ramp(end.start, end.end, 0, -6))
    return s


def cue_wandern():
    """M10 bed (>= 26 s): walking groove at step tempo, bassoon staccato + pizzicato strings."""
    s = base('Wandern', 'wandern', 108, tail=3.0, bed=True)
    g = s.section('wandern', 14, prog=s.prog('I vi IV V I vi ii V'))
    end = s.section('ende', 1, prog=s.prog('I'))
    bsn, pizz, bass, xylo = tr(s, 'bassoon'), tr(s, 'pizz', gain=-2), tr(s, 'bass', gain=-3), tr(s, 'xylo', gain=-8)
    bsn.arp('up', g, rate='1/8', register=('F2', 'F3'), pattern=[0, None, 2, None, 1, None, 2, None], vel=84,
            then=lambda c: c.articulate('staccato'))
    pizz.chords(g, voicing='close', register=('A3', 'A4'), voices=3, rhythm='..x...x.', vel=66)
    bass.bassline('root', g, rate='1/2', low='E1', vel=80)
    for i in range(3, 14, 4):
        xylo.play(mo(s, '5:1/8 r:1/8 8:1/8 r:1/8', 6, vel=60), g.bar(i, 2))
    bsn.note('F2', end, 1, vel=80)
    pizz.play(held(s, 'I', 1, register=('A3', 'A4'), vel=72, voices=3), end)
    bass.note('F1', end, 2, vel=80)
    xylo.play(mo(s, '8:1/4', 6, vel=60), end.bar(0, 1))
    return s


def cue_nebel():
    """M11 bed (>= 78 s): low strings, celesta, mysterious and muffled fog (D minor)."""
    s = base('Nebel', 'nebel', 60, key='D minor', tail=4.0, hall_decay=4.2, bed=True)
    a = s.section('nebel', 22, prog=s.prog('i:2 VI:2 iv:2 V:2 i:2 III:2 iv:2 V:2'))
    end = s.section('ende', 1, prog=s.prog('i'))
    muff = [fx.filter(mode='lp', cutoff=1800, resonance=0.0)]
    celli, basses = tr(s, 'celli', fx=muff), tr(s, 'basses')
    violas, cel = tr(s, 'violas', gain=-6, fx=muff), tr(s, 'celesta', gain=-3)
    celli.chords(a, end, voicing='spread', register=('D2', 'D3'), voices=2, vel=60)
    basses.bassline('root', a, end, rate='1/1', low='C1', vel=64)
    violas.chords(a, voicing='close', register=('D3', 'D4'), voices=2, vel=48)
    figs = ['8:1/4 r:1/4 7:1/4 r:1/4 | 5:1/2 r:1/2', 'r:1/2 5:1/8 r:1/8 4:1/4 | 3:1/2 r:1/2',
            '6:1/4 r:1/4 5:1/4 r:1/4 | 1:1/2 r:1/2', 'r:1 | #7:1/4 r:1/4 2:1/4 r:1/4']
    for i, bar in enumerate(range(1, 21, 3)):
        cel.play(mo(s, figs[i % 4], 6, vel=52 + (i % 3) * 4), a.bar(bar))
    cel.play(mo(s, '5:1/4 r:1/4 1:1/2', 6, vel=48), end)
    celli.automate('gainDb', ramp(end.start, end.end, 0, -6))
    violas.automate('gainDb', ramp(a.start, a.bar(2), -10, 0))
    return s


def cue_liebe():
    """M13 bed (>= 56 s): love theme, solo clarinet (soft, sparse) + strings, slow (Bb major)."""
    s = base('Liebe', 'liebe', 66, key='Bb major', tail=3.6, hall_decay=3.4, bed=True)
    a = s.section('thema', 8, prog=s.prog(LIEBE_PROG))
    b = s.section('strings', 8, prog=s.prog(LIEBE_PROG))
    end = s.section('ende', 1, prog=s.prog('I'))
    clar, strings = tr(s, 'clarinet', gain=-4), tr(s, 'strings', gain=-4)
    harp, celli = tr(s, 'harp', gain=-6), tr(s, 'celli', gain=-5)
    wind(s, clar, LIEBE, a, seed=21, vel=(56, 76), section='verse')
    clar.play(mo(s, '3:1/2 5:1/4 6:1/4 | 5:1/1', 4, vel=58), b)
    clar.play(mo(s, '3:1/2 5:1/4 8:1/4 | 7:1/2 6:1/2', 4, vel=56), b.bar(4))
    strings.chords(a, b, end, voicing='spread', register=('Bb2', 'Bb4'), vel=56)
    celli.bassline('root', a, b, end, rate='1/1', low='C2', vel=56)
    harp.arp('up', b, rate='1/4', register=('Bb3', 'Bb4'), vel=46, gate=1.0, then=lambda c: c.vel_random(10))
    strings.automate('gainDb', ramp(end.start, end.end, 0, -6))
    return s


def cue_boot():
    """M15 bed (>= 60 s): playful waltz, accordion colour + bassoon (3/4)."""
    s = base('Boot', 'boot', 144, meter=(3, 4), tail=3.0, bed=True)
    w = s.section('walzer', 52, prog=s.prog('I I vi vi ii V I I IV IV I vi ii V I I'))
    end = s.section('ende', 2, prog=s.prog('I:2'))
    bsn, acc = tr(s, 'bassoon', gain=1), tr(s, 'accordion', gain=-2)
    pizz, glock = tr(s, 'pizz', gain=-6), tr(s, 'glock', gain=-6)
    bsn.bassline('root', w, rate='1/4', low='C2', pattern='R..', vel=86,
                 then=lambda c: c.articulate('staccato'))
    acc.chords(w, voicing='close', register=('F3', 'F4'), voices=3, rhythm='.xx', step='1/4', gate=0.45, vel=62,
               then=lambda c: c.vel_pattern([1.0, 1.1, 0.85]).vel_random(6))
    pizz.chords(w, voicing='close', register=('C4', 'C5'), voices=2, rhythm='x..', step='1/4', vel=50,
                bars=(8, 16))
    for i in range(7, 52, 8):
        glock.play(mo(s, '5:1/8 6:1/8 8:1/4 r:1/4', 6, vel=56), w.bar(i))
    bsn.note('F2', end, 1, vel=84)
    acc.play(held(s, 'I', 6, register=('F3', 'F4'), voices=3, vel=58), end)
    glock.play(mo(s, '8:1/4', 6, vel=56), end)
    acc.automate('gainDb', ramp(end.start, end.end, 0, -8))
    return s


def cue_gipfel_aufstieg():
    """M16 bed (>= 10 s): the Berg call climbs through the strings, timpani, into a held dominant."""
    s = base('Gipfel Aufstieg', 'gipfel_aufstieg', 96, tail=3.0, bed=True)
    a = s.section('aufstieg', 4, prog=s.prog('vi IV I V'))
    end = s.section('halt', 2, prog=s.prog('V:2'))
    celli, violas, violins = tr(s, 'celli'), tr(s, 'violas', gain=-2), tr(s, 'violins', gain=-3)
    trem, basses, timp = tr(s, 'trem', gain=-3), tr(s, 'basses'), tr(s, 'timp', gain=-2)
    celli.play(mo(s, '6:1/4. 3:1/8 6:1/2', 3, vel=70), a)                   # the call, in the minor (vi)
    violas.play(mo(s, '4:1/4. 8:1/8 11:1/2', 3, vel=74), a.bar(1))          # on IV
    violins.play(mo(s, BERG_HEAD, 4, vel=78), a.bar(2))                      # on I
    violins.play(mo(s, '7:1/4. 8:1/8 9:1/2', 4, vel=82), a.bar(3))          # on V, up to the 9th
    trem.chords(a, end, voicing='spread', register=('C3', 'C5'), vel=56)
    trem.automate('gainDb', ramp(a.start, end.start, -10, 0), ramp(end.bar(1), end.end, 0, -6))
    basses.bassline('root', a, end, rate='1/1', low='C1', vel=72)
    timp.play(mo(s, '5:4', 2, vel=60), a.bar(2))
    timp.play(mo(s, '5:8', 2, vel=70), end)
    timp.automate('gainDb', ramp(a.bar(2), end.start, -12, -2), ramp(end.bar(1), end.end, -2, -10))
    return s


def cue_einschlafen():
    """M18 bed (>= 33 s): music box plays the Drachen hook slowly, glockenspiel, soft strings."""
    s = base('Einschlafen', 'einschlafen', 60, tail=4.0, hall_decay=3.8, bed=True)
    i = s.section('vorspiel', 1, prog=s.prog('I'))
    h = s.section('drache', 4, prog=s.prog(DRACHE_PROG))
    h2 = s.section('echo', 4, prog=s.prog(DRACHE_PROG))
    c = s.section('kadenz', 1, prog=s.prog('IV:0.5 V:0.5'))
    end = s.section('ende', 1, prog=s.prog('I'))
    box, glock = tr(s, 'musicbox', gain=-2), tr(s, 'glock', gain=-6)
    strings, harp = tr(s, 'strings', gain=-5), tr(s, 'harp', gain=-7)
    box.play(mo(s, DRACHE, 5, vel=64).vel_pattern([1.08, 0.9, 1.0, 0.9], grid='1/8'), h)
    box.play(mo(s, '1:1/4 3:1/4 5:1/2 | 4:1/4 6:1/4 5:1/2', 5, vel=56), h2)
    box.play(mo(s, '5:1/4 r:1/8 5:1/8 8:1/2', 5, vel=54), c)
    box.play(mo(s, '8:1/2', 5, vel=48), end)
    for at in (i, h2.bar(2), end):
        glock.play(mo(s, '8:1/4 r:1/4 5:1/4 r:1/4', 6, vel=50), at)
    strings.chords(i, h, h2, c, end, voicing='spread', register=('C3', 'C5'), vel=52)
    harp.arp('up', i, h2, rate='1/4', register=('F3', 'F4'), vel=44, gate=1.0, then=lambda c: c.vel_random(10))
    strings.automate('gainDb', ramp(end.start, end.end, 0, -7))
    return s


CUES = {
    'intro': cue_intro, 'fahrt_kurz': cue_fahrt_kurz, 'fahrt_bett': cue_fahrt_bett, 'zeitsprung': cue_zeitsprung,
    'geheimnis': cue_geheimnis, 'ankunft': cue_ankunft, 'abend': cue_abend, 'trost': cue_trost,
    'nacht_ende': cue_nacht_ende, 'wandern': cue_wandern, 'nebel': cue_nebel, 'sonne': cue_sonne,
    'liebe': cue_liebe, 'huette_ende': cue_huette_ende, 'boot': cue_boot, 'gipfel_aufstieg': cue_gipfel_aufstieg,
    'gipfel': cue_gipfel, 'einschlafen': cue_einschlafen, 'outro': cue_outro,
}
