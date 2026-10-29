"""An authored Hero-Sax adaptation of the selected Endless piece, seed 27110."""
from pathlib import Path
import statistics
from agentsound import Clip, hero, hornist
from agentsound.endless.run import load_scored

ANALYSIS = {'profile': 'classical', 'loudness': [-23, -15]}
METADATA = {'title': 'Gold über den Wolken', 'artist': 'AgentSound',
            'album': 'Orchestra meets Hero Sax', 'genre': 'Symphonic Crossover', 'year': 2026}
COVER = {'style': 'classical', 'palette': ['#142c42', '#dca54a'],
         'title': 'Gold über den Wolken', 'subtitle': 'Orchestra meets Hero Sax', 'seed': 27110}
MIX = {'trim': {'bells': -6}, 'ramp': 2,
       'ride': {'hero_sax': {'recap': 7, 'dev1': 2},
                'violins1': {'recap': -4}, 'horns': {'recap': -3},
                'trombones': {'recap': -2}, 'basses': {'recap': -2},
                'bassoons': {'recap': -2}, 'timpani': {'recap': -5},
                **{f'choir_{v}_ah': {'recap': -4} for v in ('s','a','t','b')}},
       'lead': {'var3': 'hero_sax', 'recap': 'hero_sax', 'coda': 'hero_sax'}}


def sax_line(notes, start, end, lift=0):
    ns = [(a-start, min(d, end-a), q+lift) for a,d,q in notes if start <= a < end]
    # Preserve phrase contour with one octave choice, then fold only outliers.
    middle = statistics.median(q for _,_,q in ns)
    shift = 12 if middle < 65 else -12 if middle > 77 else 0
    shaped = []
    for a,d,q in ns:
        q += shift
        while q > 80: q -= 12
        while q < 61: q += 12
        shaped.append((a,d,q,96))
    # A tiny pickup plus arrival becomes one singing arrival, leaving space
    # for the original orchestral rhythm rather than copying every flourish.
    out = []
    i = 0
    while i < len(shaped):
        a,d,q,v = shaped[i]
        if d <= .25 and i+1 < len(shaped):
            b,e,r,w = shaped[i+1]
            if abs(b-a-d) < .03 and abs(r-q) <= 2:
                out.append((a,b+e-a,r,w));i += 2;continue
        out.append((a,d,q,v));i += 1
    return Clip(out, length=end-start)


def build():
    s, tune, genre = load_scored(Path(__file__).parent/'source')
    s.title = METADATA['title']
    blocks = {b.name:b for b in s.orch_score.blocks}
    parts = s.orchestration.parts
    features = [('var2','melody',0,0,False), ('var3','melody',0,0,False),
                ('dev1','bass',16,32,False), ('recap','melody',0,0,True),
                ('coda','melody',0,0,False)]
    sax = hero(s.track('hero_sax','hero/sax',gain_db=-3.5),family='sax',genre='film',
               double=False,octave=False,duck=False,carve=False,dips=False,ride=False,throws=False)
    sax.sends.pop('echo', None)  # the orchestral hall and hero plate provide the space
    memory = hornist.Memory()
    log = []
    for n,(name,fn,aoff,zoff,peak) in enumerate(features):
        b = blocks[name]
        start,end = b.start+aoff, b.start+zoff if zoff else b.end
        lead = next(p for p in parts if p.block==name and p.function==fn and p.notes)
        line = sax_line(lead.notes,start,end,lift=24 if name=='recap' else 12 if name=='coda' else 0)
        # Give this phrase to the sax. Keep the low development bass as its
        # foundation; it is a deliberate octave dialogue, not a removed bass.
        if fn=='melody':
            roles = {p.role for p in parts if p.block==name and
                     (p.function=='melody' or (p.function=='doubling' and p.voice=='melody'))}
            for role in roles:
                if role in s.tracks:
                    s.tracks[role].clear(max(0,start-.12),end-.12)
        perf = hornist.arrange(line,tune.tempo,family='sax',style='hero70s',
            section='chorus' if peak else 'outro' if name=='coda' else 'verse',
            vel=(86,123) if peak else (76,112) if name=='coda' else (82,119),
            seed=27110+n,memory=memory,at=start,climax=peak,max_phrase=8,
            depth=.8,accent=.28)
        perf.place(sax,start)
        log.append((name,start,end,len(perf.clip),perf.summary()))
    # Analysis treats the featured sax as a lead in the relevant formal sections.
    s.lead_hint['hero_sax'] = sorted({sec.name for sec in s.sections for _,a,z,_,_ in log
                                    if sec.start < z and sec.end > a})
    s.sax_adaptation = log
    print('Hero-Sax adaptation:',log)
    return s
