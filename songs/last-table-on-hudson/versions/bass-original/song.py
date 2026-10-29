"""Last Table on Hudson: original piano-jazz trio, Eb major, 92 BPM.
DX7 E.PIANO 1 and BASS 1 are rendered by AgentSound; sampled brushes come from MIDI.
Run: python songs/last-table-on-hudson/render.py
"""
from agentsound import *
import random

BPM = 92
A = ['Eb9','C7','Fm9','Bb13','Gm7','C7','Fm9','Bb13']
A2 = ['Eb9','Eb7','Ab9','Abm6','Gm7','C7','Fm9','Bb13']
B = ['Gm7','C7','Fm9','Bb13','Am7b5','D7','Gm7','Bb13']
A3 = ['Eb9','C7','Fm9','Bb13','Gm7','C7','Fm9','Eb6']
FORM = [('doorway', ['Eb9','C7','Fm9','Bb13']), ('theme_a',A), ('theme_a2',A2),
        ('middle_eight',B), ('theme_home',A3), ('piano_solo',A+A2),
        ('last_round',B+A3), ('goodnight',['Ab9','Abm6','Eb6','Eb6'])]
# Root, quality intervals for bass, rootless piano voicing: thirds and sevenths carry the changes.
CH = {
 'Eb9':(39,[0,4,7,11],[55,58,62,65]), 'Eb6':(39,[0,4,7,9],[55,60,65,70]),
 'C7':(36,[0,4,7,10],[52,58,61,69]), 'Fm9':(41,[0,3,7,10],[56,60,63,67]),
 'Bb13':(34,[0,4,7,10],[56,60,62,67]), 'Gm7':(43,[0,3,7,10],[53,57,58,62]),
 'Eb7':(39,[0,4,7,10],[55,61,65,69]), 'Ab9':(44,[0,4,7,11],[55,58,60,67]),
 'Abm6':(44,[0,3,7,9],[53,59,63,68]), 'Am7b5':(45,[0,3,6,10],[55,60,63,67]),
 'D7':(38,[0,4,7,10],[54,60,63,69])}
# Explicit right-hand phrases. Each tuple is beat, duration, pitch; breathing room is deliberate.
M = [
 [(0,1.4,67),(1.5,.4,70),(2,1.35,72),(3.5,.4,70)],
 [(0,1.35,69),(1.5,.4,67),(2,.85,64),(3, .7,61)],
 [(0,1.4,65),(1.5,.4,67),(2,1.4,68)],
 [(.5,.4,67),(1,.85,65),(2,1.7,62)],
 [(0,1.4,65),(1.5,.4,67),(2,.85,70),(3,.7,69)],
 [(0,.8,67),(1,.8,64),(2,1.5,70)],
 [(.5,.4,68),(1,.9,67),(2,1.3,65),(3.5,.35,63)],
 [(0,1.5,62),(2,.8,65),(3,.45,66),(3.5,.35,67)],
 [(0,1.4,67),(1.5,.4,70),(2,.9,74),(3,.8,72)],
 [(0,1.4,73),(1.5,.4,70),(2,1.4,67)],
 [(0,1.4,72),(1.5,.4,70),(2,1.4,67)],
 [(0,1.4,71),(1.5,.4,68),(2,1.4,65)],
 [(.5,.4,65),(1,.8,67),(2,1.4,70)],
 [(0,.85,69),(1,.85,67),(2,.85,64),(3,.75,61)],
 [(0,1.4,65),(1.5,.4,68),(2,1.4,67)],
 [(0,1.5,65),(2,1.5,62)],
 [(0,.85,70),(1,.85,74),(2,1.4,77)],
 [(.5,.4,76),(1,.85,73),(2,1.4,70)],
 [(0,1.4,75),(1.5,.4,72),(2,1.4,68)],
 [(.5,.4,74),(1,.85,72),(2,1.4,67)],
 [(0,1.4,75),(1.5,.4,72),(2,1.4,69)],
 [(0,.8,69),(1,.85,66),(2,1.4,63)],
 [(0,1.4,62),(1.5,.4,65),(2,1.4,70)],
 [(.5,.4,69),(1,.85,68),(2,1.4,65)],
 [(0,1.4,67),(1.5,.4,70),(2,1.4,72)],
 [(0,1.4,69),(1.5,.4,67),(2,1.4,64)],
 [(0,.8,65),(1,.4,67),(1.5,.4,68),(2,1.4,72)],
 [(0,.8,74),(1,.85,72),(2,1.4,67)],
 [(0,.8,70),(1,.8,69),(2,1.4,67)],
 [(0,1.4,64),(1.5,.4,67),(2,1.4,70)],
 [(0,.85,68),(1,.85,67),(2,.85,65),(3,.7,62)],
 [(0,2.6,63)]
]
SOLO = [
 [67,70,74,72,70,67], [64,67,70,73,72,70,69], [68,72,75,74,72], [74,72,68,67,65,62],
 [70,74,77,76,74,70], [73,72,70,69,67,64], [65,67,68,72,70,68], [67,65,62,60,62],
 [67,70,72,74,77,75,74], [73,70,67,65,61], [72,75,79,77,75,72], [71,68,65,63,65],
 [70,69,67,65,62,65], [64,67,69,70,73,72,70], [68,67,65,63,60], [62,65,68,67,65,62]]

def material():
    rng=random.Random(814)
    chords=[c for _,prog in FORM for c in prog]
    piano=[]; drum=[]; bass=[]
    def swing(b):
        i=int(b); f=b-i
        return i+(0.60+(f-.5) if .45<f<.55 else f)
    def pn(at,dur,p,v):
        piano.append((max(0,swing(at)+rng.uniform(-.014,.018)),dur,p,max(25,min(110,v+rng.randint(-4,4)))))
    barno=0
    for sec,prog in FORM:
        for local,c in enumerate(prog):
            t=barno*4; root,iv,voicing=CH[c]
            end=sec=='goodnight'; intro=sec=='doorway'; solo=sec=='piano_solo'
            # Left hand: spacious syncopated rootless comping, not a repeated block on every beat.
            rhythm=([(.0,2.5)] if intro or end else
                    [[(.0,1.1),(2.5,.85)],[(.5,.8),(2,1.2)],[(0,1.6)],[(1,.8),(3,.65)]][barno%4])
            for pos,dur in rhythm:
                for j,p in enumerate(voicing[:3] if not (intro or end) else voicing):
                    pn(t+pos+j*.009,dur,p,48 if solo else (46 if end else 51))
            if intro:
                for pos,p in [(1.5,voicing[-1]+12),(3,voicing[-2]+12)]: pn(t+pos,.75,p,58)
            elif end:
                line=[[72,70],[71,68],[67,65],[63]][local]
                for j,p in enumerate(line): pn(t+j*1.5,3.0 if local==3 else 1.2,p,62-local*4)
            elif solo:
                pitches=SOLO[local]
                positions={5:[.5,1,1.5,2.5,3],6:[0,.5,1.5,2,2.5,3],7:[0,.5,1,1.5,2.5,3,3.5]}[len(pitches)]
                for j,(pos,p) in enumerate(zip(positions,pitches)):
                    dur=(positions[j+1]-pos)*.83 if j+1<len(pitches) else .65
                    pn(t+pos,dur,p,73+(4 if j in (0,3) else 0))
            else:
                idx=barno-4 if barno<36 else 16+local
                for pos,dur,p in M[idx]: pn(t+pos+.02,dur,p,69+(3 if sec=='last_round' else 0))
            # Sparse opening; gently walking bass through the solo and bridge.
            nr=CH[chords[min(barno+1,len(chords)-1)]][0]
            while nr-root>7: nr-=12
            while nr-root< -7: nr+=12
            if intro or end:
                bn=[(0,root,2.9)] if local==3 and end else [(0,root,1.5),(2,root+7,1.25)]
            elif solo or sec in ('middle_eight','last_round'):
                third=root+iv[1]; fifth=root+7
                approach=nr-1 if nr>=root else nr+1
                bn=[(0,root,.85),(1,third,.82),(2,fifth,.84),(3,approach,.76)]
            else:
                bn=[(0,root,1.4),(2,root+7,1.05)]
                if local%2: bn.append((3.5,nr-1,.35))
            for pos,p,d in bn:
                while p>55:p-=12
                while p<33:p+=12
                bass.append((swing(t+pos)+.008,d,p,76+rng.randint(-5,5)))
            # GM brush kit: light ride skip beat, pedal hats on 2/4, sparse brush taps.
            if not intro and not end:
                for pos,v in [(0,42),(1,51),(1.5,32),(2,41),(3,49),(3.5,31)]:
                    drum.append((swing(t+pos)+rng.uniform(-.006,.006),.08,51,v+rng.randint(-3,3)))
                for pos in (1,3): drum.append((t+pos+.012,.1,44,39))
                for pos in ([1,3] if local%2==0 else [.5,2.5]):
                    drum.append((swing(t+pos)+.022,.09,38,26+rng.randint(-3,3)))
                drum.append((t,.12,36,29))
                if local%8==7:
                    for pos in (3,3.5):drum.append((swing(t+pos),.07,38,34))
            barno+=1
    return piano,drum,bass

def build():
    s=Song('Last Table on Hudson - DX7 duo',tempo=BPM,key='Eb major',seed=814,tail=5)
    for name,prog in FORM:s.section(name,len(prog))
    room=s.bus('room', [fx.reverb(type='room',decay=1.35,predelay=18,
                  lowcut=180,highcut=7000,moddepth=0.35,width=0.85,mix=1)])
    piano=s.track('epiano',patches.get('synthwave/epiano').but(brightness=-0.12).with_mix(sends={'plate':None,'hall':None}),
                   gain_db=2,pan=-0.1,sends={room:-10})
    for t,d,p,v in material()[0]:piano.note(p,t,d,v)
    bass=s.track('dx7_bass', patches.get('synthwave/dx_bass').but(brightness=-0.35,velsens=0.7),
                 gain_db=-3,fx=[fx.eq(**{'lp.freq':4500})])
    for t,d,p,v in material()[2]:bass.note(p,t,d,v)
    s.master.add(fx.limiter(ceiling=-2,gain=0))
    return s
