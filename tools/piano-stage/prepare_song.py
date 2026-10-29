"""Export the renderer's note/pedal events to a small browser timeline."""
import argparse,json,math,shutil,sys,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from agentsound.tempo import TempoMap

def prepare(folder,out):
    folder=Path(folder);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=json.loads((folder/'song.render.json').read_text())
    sr=source['sampleRate'];tempo=TempoMap(source.get('tempoMap',[[0,source.get('tempo',120)]]))
    def sample(beat):return math.floor(tempo.seconds_at(beat)*sr+.5)
    notes=[];pedals=[]
    for track in source['tracks']:
        for n in track['notes']:
            start=sample(n[0]);end=max(start+1,sample(n[0]+n[1]))
            notes.append(dict(pitch=n[2],start=start/sr,duration=(end-start)/sr,velocity=n[3]/127,hand='left' if track['id']=='comp' else 'right',track=track['id']))
        for lane in track.get('automation',[]):
            if lane['target']=='instrument.pedal':
                if any(len(p)>2 and p[2]!='step' for p in lane['points']):raise ValueError('Only step pedal lanes supported')
                # Automation is evaluated at 32-sample block boundaries.
                pedals.append([[math.ceil(tempo.seconds_at(p[0])*sr/32-1e-9)*32/sr,p[1]] for p in lane['points']])
    if pedals and any(p!=pedals[0] for p in pedals):raise ValueError('Different pedals on the two hands require separate visualization')
    with wave.open(str(folder/'mix.wav')) as w:duration=w.getnframes()/w.getframerate()
    data=dict(title=source['title'],duration=duration,sampleRate=sr,notes=sorted(notes,key=lambda n:n['start']),pedal=pedals[0] if pedals else [],source=str(folder/'song.render.json'))
    (out/'song.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    shutil.copy2(folder/'mix.mp3',out/'mix.mp3')
    print(f"{data['title']}: {len(notes)} notes, {len(data['pedal'])} pedal events, {duration:.2f}s")
    return data
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('out');a=p.parse_args();prepare(a.folder,a.out)
