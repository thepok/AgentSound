"""Piano rewrite: continuous melodic sentences, responsive comping and selective sustain.
Original performance, informed by recipes/jazz-piano.md; no copied solo/transcription.
Tuple fields in RH: onset, key duration, MIDI pitch, relative accent.
"""
import random

# Eight-bar sentence, with A-D-C identity retained. Notes carry across bar lines;
# bar 4's E-F# enclosure resolves to F (the third of Dm) in bar 5.
RH=[
 [(.5,.22,69,-3),(1,1.25,74,6),(2.5,.32,72,-3),(3.5,1.05,69,1)],
 [(1.25,.24,67,-6),(1.75,.42,69,0),(2.5,.36,72,-2),(3.5,.95,77,4)],
 [(.75,.28,76,-2),(1.25,.3,74,-5),(1.75,.55,72,1),(2.75,.48,69,-4)],
 [(.5,.3,67,-2),(1.25,.65,76,4),(2.75,.2,76,-7),(3.5,.24,78,-5)],
 [(.25,1.1,77,6),(1.75,.24,76,-6),(2.25,.42,74,1),(3.5,1.0,69,-2)],
 [(1.5,.18,70,-7),(1.75,.68,69,3),(3.25,.45,74,0)],
 [(.5,.3,76,1),(1.25,.7,79,6),(2.5,.22,77,-5),(3,.6,76,-1)],
 [(.5,.6,76,2),(1.5,.27,74,-4),(2,.5,72,-2),(3.5,1.0,69,-3)]
]
# The four-bar solo is one line, not four isolated arpeggios.
# F-Eb -> E across Gm9/C13; Bb -> A across C13/Fmaj9; C# -> D into homeward.
SOLO=[
 [(.5,.27,70,-4),(1,.3,74,0),(1.5,.6,77,4),(2.5,.3,81,5),(3.25,.2,77,-5),(3.65,.2,75,-8)],
 [(0,.65,76,5),(1,.25,79,-2),(1.5,.45,81,3),(2.25,.3,82,6),(2.75,.22,79,-2),(3,.2,76,-5),(3.5,.35,70,-5)],
 [(0,.75,69,5),(1,.28,72,-3),(1.5,.25,76,1),(2,.58,79,6),(3,.28,76,-4),(3.5,.24,73,-7)],
 [(0,.48,73,4),(.75,.23,76,-1),(1,.3,79,2),(1.5,.4,82,4),(2.25,.2,77,-5),(2.5,.18,76,-4),(2.75,.24,73,-6),(3.5,.4,73,-2)]
]
VOICES={
 'Dm9':[[53,60,64],[57,60,64,67]],
 'Bb9':[[53,57,62],[57,60,62,65]],  # actual sound: Bbmaj9
 'F9':[[52,57,62],[52,55,57,60]],   # Fmaj13 / Fmaj9
 'C9':[[52,57,62],[55,60,62,64]],   # C6/9 / Cadd9
 'Gm9':[[53,58,62],[57,58,62,65]],
 'C13':[[52,58,62],[58,62,64,69]],
 'A7':[[55,58,61],[55,61,64,70]],
 'Dmaj9':[[54,61,64],[57,61,64,66]]}
# Eight-bar comping conversation. Short touches alternate with held shells and empty spaces.
COMP=[[(0,.65,0),(2.5,.24,1)],[(.75,.3,0),(3,.42,1)],
      [(1.25,.85,0)],[(.5,.26,0),(2.25,.48,1)],
      [(1.5,.32,0),(3,.26,1)],[(.25,.7,0),(2.75,.24,1)],
      [(0,.3,0),(2,.48,1)],[(1,.55,0)]]

def score(form,ch):
    rng=random.Random(404)
    notes=[]; pedals=[]
    total=sum(len(prog) for _,prog in form)*4
    def put(t,d,p,v,late=0):
        onset=max(0,t+late+rng.uniform(-.004,.005))
        notes.append((onset,min(d,total-onset-.01),p,max(22,min(108,v))))
    def catch(a,b):
        # Binary MIDI sustain; short resonance windows, not a permanent blanket.
        pedals.extend([(a,127),(b,0)])
    bar=0
    for sec,prog in form:
        for b,h in enumerate(prog):
            t=bar*4;root=ch[h][0];intro=sec=='empty_platform';outro=sec=='last_train'
            quiet=sec=='between_stations';solo=sec=='a_private_smile'
            k=(bar-4)%8
            if intro or outro:
                # Solo texture: bass root, inner guide tones, then melody; independent attacks.
                put(t,2.8,root+12,42)
                voicing=VOICES[h][0]
                for j,p in enumerate(voicing):put(t+.16+j*.035,2.4,p,43+(3 if j==2 else 0))
                catch(t+.3,t+2.8)
                if b%2==0:
                    put(t+3.1,.55,voicing[-1],46)
                    catch(t+3.15,t+3.85)
            elif quiet:
                for j,p in enumerate(VOICES[h][0]):put(t+.45+j*.02,2.3,p,42)
                catch(t+.55,t+2.65)
            else:
                rhythm=([(1.75,.22,0)] if solo and b in (0,2) else
                        [(2.5,.3,0)] if solo else COMP[k])
                for pos,dur,variation in rhythm:
                    voice=VOICES[h][variation]
                    # Omit a non-essential note in the sparse shell answers.
                    if dur<.35 and len(voice)>3:voice=voice[1:]
                    for j,p in enumerate(voice):put(t+pos+j*.005,dur,p,46+(2 if j==len(voice)-1 else -2))
                    if dur>=.55:catch(t+pos+.04,min(t+pos+dur+.16,t+3.9))
            if intro:
                phrase=[[(.8,.35,69,-4),(1.5,1.25,74,3),(3,.45,72,-6)],
                        [(.35,1.3,69,0),(2.25,.5,65,-4)],
                        [(.75,.3,69,-4),(1.25,.3,72,-2),(2,1.3,76,3)],
                        [(.75,.65,74,-2),(2,.38,72,-5),(3.4,.8,69,-4)]][b]
            elif quiet:
                phrase=[[(.1,.4,74,0),(1,1.4,70,-4)],[(.3,1.2,69,-2),(2.5,.2,68,-8),(2.8,.6,67,-3)],
                        [(.5,1.3,65,-2),(2.5,.4,62,-5)],[(.5,.55,64,-2),(1.5,.35,62,-5),(2.5,.85,61,0)]][b]
            elif solo:phrase=SOLO[b]
            elif outro:
                phrase=[[(.5,.28,69,-4),(1.25,1.0,74,2),(2.75,.3,72,-4)],
                        [(.5,1.25,69,-1),(2.5,.7,67,-5)],
                        [(1,1.25,65,0),(3,.45,64,-5)],[(.3,1.8,62,-2)],
                        [(.5,.7,65,-3),(2,1.2,69,-1)],[(1,.7,67,-3),(2.5,.4,64,-5)],
                        [(.5,1.0,66,1),(2,.38,69,-4),(2.75,.6,73,1)],
                        [(0,1.25,76,2),(1.7,2.0,66,-3)]][b]
            else:
                phrase=RH[k]
                if sec=='engine_starts' and b in (1,3):phrase=[]
                if sec=='homeward' and b==0:
                    # Resolve the previous A7 line on D before recalling the theme.
                    phrase=[(0,.65,74,6),(1.5,.3,72,-4),(2.25,.48,69,-1),(3.5,1,69,-4)]
                elif sec=='homeward' and k in (2,6):
                    # Same motif, slightly delayed; the beat keeps going underneath.
                    phrase=[(a+.125,d,p,v) for a,d,p,v in phrase]
            level=58 if intro or outro else 61 if quiet else 74 if solo else 67
            for pos,d,p,accent in phrase:put(t+pos,d,p,level+accent,late=.014 if not solo else .003)
            # A few voiced melodic arrivals, not every note doubled.
            if sec in ('blue_hour','homeward') and k in (0,4,6) and phrase:
                pos,d,p,v=max(phrase,key=lambda n:n[1])
                tones=[n+octave for n in VOICES[h][1] for octave in (0,12) if p-8<=n+octave<=p-3]
                if tones:put(t+pos,min(d,.9),max(tones),49,.02)
            bar+=1
    # Merge sustain windows and ensure every depressed pedal is released at the end.
    windows=[];stack=None
    for a,b in zip(pedals[::2],pedals[1::2]):windows.append((a[0],b[0]))
    merged=[]
    for a,b in sorted(windows):
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    pedal=[event for a,b in merged for event in ((a,127),(b,0))]
    notes.sort()
    return notes,pedal
