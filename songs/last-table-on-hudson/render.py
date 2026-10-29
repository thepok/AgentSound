"""Reproducible DX7 E-piano/bass + sampled brush-kit render. No real-time audio device needed."""
from pathlib import Path
import json, re, struct, subprocess, sys, shutil
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from song import material, BPM, FORM, performed
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
            bars=sum(len(prog) for _,prog in FORM)
            # Repedal after each chord attack; clear the preceding harmony first.
            for bar in range(bars):
                events.append((round(performed(bar*4+0.08)*ticks),bytes([0xb0,64,127])))
                events.append((round(performed((bar+1)*4-0.07)*ticks),bytes([0xb0,64,0])))
                if 36<=bar<52:
                    events.append((round(performed(bar*4+1.93)*ticks),bytes([0xb0,64,0])))
                    events.append((round(performed(bar*4+2.08)*ticks),bytes([0xb0,64,127])))
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
         '-o','synth.reverb.room-size=0.25','-o','synth.reverb.level=0.12',
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

piano,drums,bass=material()
midi(OUT/'drums.mid',[(9,40,drums)])
midi(OUT/'grand.mid',[(0,0,piano)])
midi(OUT/'composition-dx7.mid',[(0,4,piano),(1,33,bass),(9,40,drums)])
midi(OUT/'composition-grand.mid',[(0,0,piano),(1,33,bass),(9,40,drums)])
run([sys.executable,'-m','agentsound','build',HERE,'--no-mp3'],cwd=ROOT)
shutil.copy2(OUT/'mix.wav',OUT/'dx7-duo.wav')
d=json.loads((OUT/'song.render.json').read_text())
d['tracks']=[t for t in d['tracks'] if t['id']=='dx7_bass'];d['buses']=[]
(OUT/'bass.render.json').write_text(json.dumps(d))
run([ROOT/'build/agentsound.exe','render',OUT/'bass.render.json','--out',OUT/'bass',
     '--no-analysis','--no-png','--assets',ROOT/'assets'],cwd=ROOT)
fluid(OUT/'drums.mid',OUT/'brushes.wav')
fluid(OUT/'grand.mid',OUT/'grand-raw.wav')
# Match the sampled piano's perceived level to the DX7 piano before combining the trio.
master(OUT/'grand-raw.wav',OUT/'grand.wav',-18.3)
results={}
end_seconds=performed(sum(len(prog) for _,prog in FORM)*4)*60/BPM
fade_start=end_seconds-0.5
render_end=end_seconds+5.5
for name in ('dx7','grand'):
    inputs=([OUT/'dx7-duo.wav',OUT/'brushes.wav'] if name=='dx7' else
            [OUT/'grand.wav',OUT/'bass/mix.wav',OUT/'brushes.wav'])
    opts=[v for f in inputs for v in ('-i',f)]
    n=len(inputs); drumsidx=n-1
    summands=''.join(f'[{i}:a]' for i in range(n-1))+'[d]'
    # Brushes stay well behind piano and bass; no clap and no gated noise reverb.
    chain=f'[{drumsidx}:a]volume=6,highpass=f=60,lowpass=f=10500[d];'+summands+f'amix=inputs={n}:normalize=0:duration=longest,afade=t=out:st={fade_start}:d=6,atrim=end={render_end}[m]'
    pre=OUT/f'{name}-premaster.wav';wav=OUT/f'{name}.wav'
    run(['ffmpeg','-y','-v','error',*opts,'-filter_complex',chain,'-map','[m]','-c:a','pcm_f32le',pre])
    master(pre,wav)
    run(['ffmpeg','-y','-v','error','-i',wav,'-c:a','libmp3lame','-b:a','320k',
         '-metadata',f'title=Last Table on Hudson ({name})','-metadata','artist=AgentSound',OUT/f'{name}.mp3'])
    results[name]=measure(wav)
    run(['ffmpeg','-y','-v','error','-i',wav,'-filter_complex',
         'showwavespic=s=1500x350:split_channels=1:colors=0x65c9a5|0x77aadd',
         '-frames:v','1',OUT/f'{name}-waveform.png'])
    print(name,json.dumps(results[name]),flush=True)
(OUT/'master-analysis.json').write_text(json.dumps(results,indent=2))
