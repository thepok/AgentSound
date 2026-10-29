"""Last Train, Blue Hour. Original cinematic piano / trip-hop, D minor -> D major.
Render complete mix: python songs/last-train-blue-hour/render.py
Native build() supplies the synth/bass bed; sampled piano and dry drums use FluidSynth.
"""
from agentsound import *
import math, random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
BPM=78
P=['Dm9','Bb9','F9','C9']
FORM=[('empty_platform',P),('engine_starts',P*2),('window_lights',P*3),
      ('blue_hour',P*3),('between_stations',['Gm9','A7','Bb9','A7']),
      ('a_private_smile',['Gm9','C13','F9','A7']),('homeward',P*3),
      ('last_train',['Bb9','C9','Dm9','Dm9','Bb9','C9','Dmaj9','Dmaj9'])]
CH={
'Dm9':(38,[53,57,60,64],[50,57,60,65]),
'Bb9':(34,[53,57,60,62],[50,57,60,65]),
'F9':(41,[52,57,60,67],[53,60,64,69]),
'C9':(36,[52,55,60,62],[52,55,62,67]),
'Gm9':(43,[53,57,58,62],[50,57,62,65]),
'A7':(33,[55,58,61,64],[49,55,61,64]),
'C13':(36,[52,58,62,69],[52,58,62,69]),
'Dmaj9':(38,[54,57,61,64],[50,57,61,66])}

def _clock():
    c=[0.0]
    for name,prog in FORM:
        base={'empty_platform':73,'engine_starts':77,'window_lights':78,'blue_hour':80,
              'between_stations':75,'a_private_smile':82,'homeward':79,'last_train':75}[name]
        for b in range(len(prog)):
            for k in range(16):
                phase=k/16
                speed=base+0.8*math.sin((b%4+phase)*math.pi/2)
                if b%4==3:speed-=2.8*phase**2
                if name=='last_train':speed-=13*((b+phase)/len(prog))**1.7
                c.append(c[-1]+.25*BPM/speed)
    return c
CLOCK=_clock()
def performed(beat):
    x=max(0,beat)*4;i=int(x)
    if i>=len(CLOCK)-1:return CLOCK[-1]+(x-len(CLOCK)+1)*(CLOCK[-1]-CLOCK[-2])
    return cinterp(i,x-i)
def cinterp(i,f):return CLOCK[i]+f*(CLOCK[i+1]-CLOCK[i])

# The returning four-bar theme: D-A-E contour, then a descending answer.
THEME=[[(.5,1.2,69),(2,.8,74),(3,.8,72)],
       [(0,1.4,69),(2,1.4,65)],
       [(.5,.8,69),(1.5,.4,72),(2,1.4,76)],
       [(0,1.4,74),(2,.75,72),(3,.7,67)]]
ANSWER=[[(0,1.2,77),(1.5,.4,76),(2,1.4,74)],
        [(.5,.6,72),(1.5,.4,69),(2,1.4,65)],
        [(0,.8,67),(1,.8,69),(2,1.4,72)],
        [(.5,.7,74),(1.5,.4,72),(2,1.4,69)]]
# Four bars where restraint briefly gives way to a fluid, deliberately voiced run.
GRIN=[[(.0,.2,67),(.25,.2,69),(.5,.2,70),(.75,.2,74),(1,.2,77),(1.25,.2,76),(1.5,.4,74),(2.25,.6,69),(3,.65,70)],
      [(.25,.2,74),(.5,.2,75),(.75,.2,76),(1,.2,79),(1.25,.2,81),(1.5,.4,79),(2.25,.2,76),(2.5,.2,74),(2.75,.2,72),(3.25,.5,70)],
      [(0,.15,76),(.17,.15,77),(.34,.35,76),(.85,.3,72),(1.35,.3,69),(1.85,.3,67),(2.35,.7,69),(3.3,.45,72)],
      [(0,.22,73),(.3,.22,76),(.6,.22,79),(.9,.3,82),(1.35,.22,79),(1.65,.22,76),(1.95,.22,73),(2.4,.6,69),(3.3,.35,73)]]

def _original_arrangement():
    rng=random.Random(301)
    piano=[];drums=[];bass=[];pads=[];sections=[]
    def pn(at,dur,p,vel):piano.append((max(0,at+rng.uniform(-.018,.025)),dur,p,max(20,min(112,vel+rng.randint(-4,4)))))
    bar=0
    for name,prog in FORM:
        sections.append((name,bar*4,(bar+len(prog))*4))
        for b,h in enumerate(prog):
            at=bar*4;root,voicing,padnotes=CH[h]
            intro=name=='empty_platform';outro=name=='last_train';grin=name=='a_private_smile'
            quiet=name=='between_stations'
            # Pedalled left hand, gently rolled, with a second reply only in selected bars.
            strikes=[(0,2.8)] if intro or outro or quiet else [(0,1.55)]+([(2.65,.8)] if b%3==1 else [])
            for pos,dur in strikes:
                for j,p in enumerate(voicing):pn(at+pos+j*.025,dur,p,45 if intro or outro else (43 if grin else 48))
            phrase=THEME[b%4]
            if name in ('window_lights','blue_hour','homeward') and 4<=b%12<8:phrase=ANSWER[b%4]
            if quiet:
                phrase=[[(1,1.8,70)],[(.5,1.7,69)],[(1,1.8,65)],[(2,1.3,61)]][b]
            if grin:phrase=GRIN[b]
            if name=='engine_starts' and b<4:phrase=THEME[b%4] if b%2==0 else []
            if outro and b>=6:
                phrase=[[(.5,1.0,74),(2,.75,73),(3,.8,69)],[(0,1.3,76),(1.7,2.0,66)]][b-6]
            for pos,dur,p in phrase:
                pn(at+pos,dur,p,(58 if intro or outro else 74 if grin else 68)+(2 if name=='homeward' else 0))
            if intro or outro:
                # Low acoustic root belongs only to the solo-piano bookends.
                pn(at,3.6,root+12,44)
            if name not in ('empty_platform','last_train') and not quiet:
                pattern=[(0,root,.95),(1.7,root+12,.4),(2.5,root+7,.65)]
                if b%4==3:pattern=[(0,root,1.3),(2.5,root+7,.5),(3.35,root+10,.35)]
                if grin:pattern=[(0,root,1.4),(2.5,root+7,.6)]
                for pos,p,d in pattern:bass.append((at+pos+.012,d,p,78+rng.randint(-5,4)))
            # Tight, lazy sampled break: kick syncopation, short rim/snare, restrained hats.
            if name not in ('empty_platform','last_train','between_stations'):
                kicks=[(0,79),(1.65,56),(2.5,71)] if b%2==0 else [(0,77),(2.25,69),(3.6,48)]
                for pos,v in kicks:drums.append((at+pos,.12,36,v))
                for pos in (1.04,3.045):drums.append((at+pos,.1,37 if name=='engine_starts' or grin else 38,60 if grin else 65))
                if b%4==2:drums.append((at+2.8,.08,38,28))
                for i in range(8):
                    off=i*.5+(.055 if i%2 else 0)+rng.uniform(-.009,.009)
                    drums.append((at+off,.055,42,(38 if i%2 else 29)+rng.randint(-3,3)))
                if b%8==7:drums.append((at+3.55,.12,46,34))
            # The distant pad arrives only after the first full statement.
            if name in ('blue_hour','homeward'):
                pads.append((at,3.85,padnotes,68 if name=='blue_hour' else 63))
            if quiet:
                pads.append((at,3.7,padnotes,42))
            bar+=1
    return piano,drums,bass,pads,sections

def material():
    # Preserve the exact approved rhythm-section RNG stream and pad performance.
    _,drums,bass,pads,sections=_original_arrangement()
    from piano_revision import score
    piano,_=score(FORM,CH)
    return piano,drums,bass,pads,sections

def build():
    s=Song('Last Train, Blue Hour - synth bed',tempo=BPM,key='D minor',seed=301,tail=9)
    piano,drums,bass,pads,sections=material()
    for name,a,b in sections:s.section(name,(performed(b)-performed(a))/4)
    hall=s.hall(decay=5.1,predelay=42,moddepth=.7,modrate=.27,lowcut=260,highcut=7200,width=1.0)
    hall.gain_db=-3
    pad=s.track('distant_pad',patches.get('synthwave/warm_pad').but(
        unison=4,unison__detune=.5,unison__spread=.9,amp__attack=1.1,amp__release=3.2,
        cutoff=2400,hpf=150),gain_db=-7,sends={hall:-3},fx=[fx.width(width=1.05,monobass=160)])
    low=s.track('bass','synthwave/dx_bass',gain_db=-8,
        fx=[fx.eq(**{'lp.freq':2200,'peak1.freq':850,'peak1.gain':-2})])
    for t,d,p,v in bass:low.note(p,performed(t),performed(t+d)-performed(t),v)
    for t,d,notes,v in pads:
        for p in notes:pad.note(p,performed(t),performed(t+d)-performed(t),v)
    s.master.add(fx.width(width=1.0,monobass=120),fx.limiter(ceiling=-2,gain=0))
    return s
