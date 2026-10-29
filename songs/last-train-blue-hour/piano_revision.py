"""Hand-written sentences: finger legato, harmonic repedalling, explicit breaths.
The approved first five seconds retain their original MIDI events.
"""
import math

# (local beat, MIDI note, accent); separate releases mark actual breaths.
THEME = [(.5,69,-3),(1,74,3),(2.5,72,-2),(3,69,-4),
         (4.5,65,-3),(5.5,69,-2),(6,72,0),(7,74,1),(7.5,77,3),
         (8,76,4),(9,74,-2),(9.5,72,-3),(10.5,69,-4),
         (12,67,-3),(13,69,-2),(13.5,72,0),(14,74,1)]
ANSWER = [(.25,77,3),(1.75,76,-1),(2.5,74,-3),(3,72,-4),
          (4,69,-3),(5.5,70,-4),(6,72,0),(6.5,74,2),
          (8,76,3),(9.5,77,-1),(10,76,-2),(10.5,72,-3),
          (12,69,-2),(13.5,67,-3),(14,64,-5)]
LIFT = [(.5,69,-3),(1,74,2),(2.5,77,3),(3.5,76,-2),
        (4,74,-1),(5.5,72,-2),(6,69,-3),(7,72,0),
        (8,76,3),(9,79,4),(10.5,77,-1),(11,76,-2),
        (12,74,-3),(13,72,-4),(13.5,69,-5),(14.5,67,-5)]
SOLO = [(.25,70,-3),(.75,74,-1),(1.25,77,2),(2,81,4),
        (2.75,79,0),(3.25,77,-2),(3.75,75,-4),
        (4,76,2),(5,79,1),(5.5,81,2),(6,82,3),(6.5,81,0),
        (7,79,-2),(7.5,70,-4),(8,69,2),
        (9,72,-2),(9.5,76,0),(10,79,3),(10.5,77,-1),(11,76,-2),
        (11.5,74,-3),(12,73,1),(12.5,76,0),(13,79,2),
        (13.5,82,4),(14,81,0),(14.5,79,-2),(15,76,-3),(15.5,73,-4)]
VOICES = {
    'Dm9': [[53,60,64],[57,60,64]],
    'Bb9': [[53,57,62],[57,60,62]],  # Bbmaj9
    'F9': [[52,57,62],[52,57,60]],   # Fmaj13 / Fmaj9
    'C9': [[52,55,62],[55,60,64]],
    'Gm9': [[53,58,62],[57,58,62]],
    'C13': [[52,58,62],[58,62,64]],
    'A7': [[55,58,61],[55,61,64]],
    'Dmaj9': [[54,61,64],[57,61,64]],
}
# Exact events before beat 6 (~4.89 s) from the user's preferred opening.
OPENING = [(0,2.8,50,42),(.159652561351777,2.4,53,43),
           (.1910292583753183,2.4,60,43),(.22684112738173307,2.4,64,46),
           (.8129946367532433,.35,69,54),(1.513564231385893,1.25,74,61),
           (3.0109007287039757,.45,72,52),(3.101370757772454,.55,64,46),
           (4.003942413076048,2.8,46,42),(4.162009862583802,2.4,53,43),
           (4.1953198784725085,2.4,57,43),(4.230788370594891,2.4,62,46),
           (4.361611755534527,1.3,69,58)]
OPENING_PEDAL = [(.3,127),(2.8,0),(3.15,127),(3.85,0),(4.3,127),(6.8,0)]


def sentences(section, bars):
    """Return local-onset lines and releases, independent of bar cuts."""
    if section == 'empty_platform':
        return [(0,[(6.25,65,-4),(8.75,69,-3),(9.25,72,-1),(10,76,3),
                    (11.5,74,-2),(12.5,72,-3),(13.5,69,-4),(14.5,67,-5)],15.55)]
    if section == 'between_stations':
        return [(0,[(.1,74,0),(1,70,-3),(3,69,-4),(4.5,68,-5),(5,69,-2),
                    (6.5,73,1),(7.5,74,0)],8.55),
                (0,[(9,77,1),(10.5,74,-2),(11.5,70,-3),(12.5,69,-3),
                    (13.5,67,-4),(14.5,64,-5),(15.5,61,-3)],16.045)]
    if section == 'a_private_smile':
        return [(0,SOLO,16.045)]
    if section == 'last_train':
        return [(0,[(.5,69,-3),(1.25,74,2),(2.75,72,-2),(4.5,69,-3),
                    (6.5,67,-4),(8,65,-2),(10,64,-4),(12,62,-5)],15.2),
                (0,[(16.5,65,-3),(18,69,0),(20,67,-3),(22,64,-4),
                    (24.5,66,1),(26,69,-2),(26.75,73,1),(28,76,3),
                    (29.7,66,-3)],31.95)]
    result=[]
    for block in range(bars//4):
        line=list(ANSWER if block%2 else THEME)
        if section in ('blue_hour','homeward') and block==2:
            line=list(LIFT)
        if section=='homeward' and block==0:
            line=[(0,74,3),(1.5,72,-2),(2.5,69,-4)]+line[4:]
        if section=='engine_starts' and block==0:
            line=[(.5,69,-3),(1.5,74,2),(3,72,-2),(4.5,69,-3),
                  (6.5,65,-4),(8,69,-2),(9,72,0),(10,76,3),
                  (12,74,-2),(13.5,72,-3),(14.5,69,-5)]
        result.append((block*16,line,15.55 if block%2==0 else 15.15))
    return result


def score(form, ch):
    total=sum(len(prog) for _,prog in form)*4
    notes=list(OPENING)
    pedal=list(OPENING_PEDAL)
    def put(t,end,pitch,vel):
        if end>t:
            notes.append((t,min(end,total-.005)-t,pitch,int(vel)))
    section_start=0
    for section,prog in form:
        intro=section=='empty_platform'
        outro=section=='last_train'
        solo=section=='a_private_smile'
        quiet=section=='between_stations'
        level=58 if intro or outro else 61 if quiet else 71 if solo else 65
        for offset,line,release in sentences(section,len(prog)):
            # Release follows the next performed onset, including across barlines.
            played=[]
            for pos,pitch,accent in line:
                lean=.012*math.sin(pos*math.pi/8)
                played.append((section_start+offset+pos+.018+lean,pitch,level+accent))
            for i,(at,pitch,vel) in enumerate(played):
                if i+1<len(played):
                    nxt,np,_=played[i+1]
                    end=nxt+(.04 if pitch!=np else -.018)
                else:
                    end=section_start+offset+release
                put(at,end,pitch,vel)
        for b,harmony in enumerate(prog):
            at=section_start+b*4
            if at<8:
                continue  # Preserved opening LH and pedal already present.
            voice=VOICES[harmony][(b//2)%2]
            if intro or outro:
                put(at,at+3.92,ch[harmony][0]+12,40)
                for j,p in enumerate(voice):
                    put(at+.14+j*.028,at+3.7,p,42+(j==2)*2)
            elif quiet:
                for j,p in enumerate(voice):
                    put(at+.1+j*.022,at+3.85,p,41+(j==2)*2)
            else:
                # Settled harmony under the line, with occasional quiet answers.
                pos=[.05,.22,.08,.1][b%4]
                length=2.4 if solo else [2.65,3.35,2.9,3.45][b%4]
                for j,p in enumerate(voice):
                    put(at+pos+j*.018,at+pos+length,p,42+(j==2)*3)
                if not solo and b%4==0:
                    put(at+3.0,at+3.88,voice[-1],41)
            # Change pedal after the new harmony attacks. Clear twice per bar,
            # every beat in the solo; finger legato bridges these pedal changes.
            attacks=[0,1,2,3] if solo else [0,2]
            for pos in attacks:
                pedal.extend([(at+pos+.045,0),(at+pos+.105,127)])
        section_start+=len(prog)*4
    pedal.append((total-.01,0))
    # Shared pitches between hands cannot leave an old note-off cutting a new key.
    notes.sort()
    for i in range(len(notes)-1,-1,-1):
        at,d,p,v=notes[i]
        for following in notes[i+1:]:
            if following[0]>=at+d:
                break
            if following[2]==p:
                notes[i]=(at,max(.01,following[0]-at-.012),p,v)
                break
    return notes,sorted(pedal)
