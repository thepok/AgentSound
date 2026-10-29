"""Reproducible acoustic-piano / trip-hop render. No real-time audio device needed."""
from pathlib import Path
import json, re, struct, subprocess, sys, shutil
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from song import material, BPM, FORM, CH, performed
from piano_revision import score
OUT=HERE/'out'; OUT.mkdir(exist_ok=True)
FLUID=next((ROOT/'work/jazz-tools/fluidsynth').rglob('fluidsynth.exe'))
SF=ROOT/'assets/soundfonts/GeneralUser-GS.sf2'

def vl(n):
    b=[n&127]; n>>=7
    while n:b.insert(0,128|(n&127));n>>=7
    return bytes(b)

def midi(path,parts):
    ticks=960
    events=[(0,b'\xff\x51\x03'+int(60000000/BPM).to_bytes(3,'big'))]
    for channel,program,notes in parts:
        events += [(0,bytes([0xc0|channel,program])),(0,bytes([0xb0|channel,7,100])),
                   (0,bytes([0xb0|channel,10,69 if channel==9 else 64]))]
        if channel==0:
            for at,value in score(FORM,CH)[1]:
                events.append((round(performed(at)*ticks),bytes([0xb0,64,value])))
        for t,d,p,v in notes:
            events.append((round(performed(t)*ticks),bytes([0x90|channel,p,v])))
            events.append((round(performed(t+d)*ticks),bytes([0x80|channel,p,0])))
    end=sum(len(p) for _,p in FORM)*4+8
    events.append((int(performed(end)*ticks),b'\xff\x2f\x00'))
    events.sort(key=lambda e:(e[0],0 if e[1][0]&0xf0==0x80 else 1))
    data=b'';last=0
    for t,msg in events:data+=vl(t-last)+msg;last=t
    path.write_bytes(b'MThd'+struct.pack('>IHHH',6,0,1,ticks)+b'MTrk'+struct.pack('>I',len(data))+data)

def run(args, **kw):
    return subprocess.run([str(a) for a in args],check=True,**kw)

def fluid(mid, wav):
    run([FLUID,'-ni','-C','0','-R','1','-r','48000','-g','0.5',
         '-o','synth.reverb.room-size=0.32','-o','synth.reverb.level=0.1',
         '-T','wav','-O','float','-F',wav,SF,mid])

def measure(path):
    x=run(['ffmpeg','-hide_banner','-i',path,'-af',
           'loudnorm=I=-16:TP=-1.5:LRA=12:print_format=json','-f','null','-'],capture_output=True,text=True)
    return json.loads(x.stderr[x.stderr.rfind('{'):x.stderr.rfind('}')+1])

def master(src,dst,target=-16):
    stats=measure(src)
    args=':'.join(f'{k}={stats[v]}' for k,v in [('measured_I','input_i'),('measured_TP','input_tp'),
         ('measured_LRA','input_lra'),('measured_thresh','input_thresh')])
    run(['ffmpeg','-y','-v','error','-i',src,'-af',
         f'loudnorm=I={target}:TP=-1.5:LRA=12:linear=true:'+args,'-ar','48000','-c:a','pcm_s24le',dst])
    actual=measure(dst)
    correction=target-float(actual['input_i'])
    if correction < -0.1:
        temp=Path(dst).with_name(Path(dst).stem+'-level.wav')
        run(['ffmpeg','-y','-v','error','-i',dst,'-af',f'volume={correction}dB','-c:a','pcm_s24le',temp])
        temp.replace(dst)


def gain_to(src,dst,target):
    measured=measure(src)
    gain=target-float(measured['input_i'])
    run(['ffmpeg','-y','-v','error','-i',src,'-af',f'volume={gain}dB','-c:a','pcm_f32le',dst])
    return {'source':measured,'gain_db':round(gain,3),'target_lufs':target}

piano,drums,bass,pads,sections=material()
midi(OUT/'piano.mid',[(0,0,piano)])
midi(OUT/'drums.mid',[(9,8,drums)])
midi(OUT/'performance.mid',[(0,0,piano),(1,33,bass),(9,8,drums)])
if '--piano-only' not in sys.argv:
    run([sys.executable,'-m','agentsound','build',HERE,'--no-mp3'],cwd=ROOT)
    shutil.copy2(OUT/'mix.wav',OUT/'bed-raw.wav')
fluid(OUT/'piano.mid',OUT/'piano-raw.wav')
if '--piano-only' not in sys.argv:
    fluid(OUT/'drums.mid',OUT/'drums-raw.wav')
levels={}
levels['piano']=gain_to(OUT/'piano-raw.wav',OUT/'piano.wav',-20.0)
levels['drums']=gain_to(OUT/'drums-raw.wav',OUT/'drums.wav',-27.0)
levels['bed']=gain_to(OUT/'bed-raw.wav',OUT/'bed.wav',-25.5)
end=performed(sum(len(prog) for _,prog in FORM)*4)*60/BPM
render_end=end+7.5
run(['ffmpeg','-y','-v','error','-i',OUT/'piano.wav','-i',OUT/'drums.wav','-i',OUT/'bed.wav',
     '-filter_complex',f'[0:a]highpass=f=65[p];[1:a]highpass=f=35,lowpass=f=10500[d];[p][d][2:a]amix=inputs=3:normalize=0:duration=longest,afade=t=in:d=0.025,afade=t=out:st={end+1}:d=6.5,atrim=end={render_end}[m]',
     '-map','[m]','-c:a','pcm_f32le',OUT/'premaster.wav'])
master(OUT/'premaster.wav',OUT/'mix.wav',-15.5)
run(['ffmpeg','-y','-v','error','-i',OUT/'mix.wav','-c:a','libmp3lame','-b:a','320k',
     '-metadata','title=Last Train, Blue Hour','-metadata','artist=AgentSound',OUT/'mix.mp3'])
final=measure(OUT/'mix.wav')
(OUT/'master-analysis.json').write_text(json.dumps({'final':final,'stem_levels':levels,
    'sections':[{'name':n,'start_seconds':performed(a)*60/BPM,'end_seconds':performed(b)*60/BPM} for n,a,b in sections]},indent=2))
run(['ffmpeg','-y','-v','error','-i',OUT/'mix.wav','-filter_complex',
     'showwavespic=s=1500x350:split_channels=1:colors=0x65c9a5|0x77aadd','-frames:v','1',OUT/'final-waveform.png'])
run([ROOT/'build/agentsound.exe','clicks',OUT/'mix.wav','--json'])
print('FINAL',json.dumps(final),flush=True)
print('LEVELS',json.dumps(levels),flush=True)
print('SECTIONS',[(n,round(performed(a)*60/BPM,1)) for n,a,b in sections],flush=True)
