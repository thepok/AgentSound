"""Render the stage UI with measured stem levels. Requires numpy, scipy, playwright, Edge and ffmpeg."""
import argparse, json, math, subprocess
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from playwright.sync_api import sync_playwright

def main():
 ap=argparse.ArgumentParser();ap.add_argument('tune_dir',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--fps',type=int,default=12);ap.add_argument('--url',default='http://127.0.0.1:8772/');ap.add_argument('--preview',action='store_true');args=ap.parse_args()
 tune=json.loads((args.tune_dir/'tune.json').read_text());sr,mix=wavfile.read(args.tune_dir/'mix.wav',mmap=False);duration=len(mix)/sr;frames=math.ceil(duration*args.fps)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
  page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1);page.goto(args.url);page.wait_for_function('window.orchestraStage')
  # Prevent development reloads during an offline export.
  page.evaluate('()=>{for(let i=1;i<1000;i++)clearInterval(i);document.body.classList.add("clean");document.querySelector(".exit-clean").remove()}')
  track_files=tune['files']['stems']['tracks']
  mapping=page.evaluate('''async(ids)=>{const {resolveInstrument}=await import('./catalog.js');return Object.fromEntries(ids.map(id=>[id,resolveInstrument(id)?.id]))}''',list(track_files))
  missing=[k for k,v in mapping.items() if not v]
  if missing:raise ValueError(f'Missing artwork: {missing}')
  power={}
  for track,filename in track_files.items():
   path=Path(filename);path=path if path.is_absolute() else args.tune_dir/'stems'/path.name
   rate,data=wavfile.read(path,mmap=False);block=round(rate/args.fps);n=min(frames,len(data)//block)
   v=data[:n*block].astype(np.float32)
   if np.issubdtype(data.dtype,np.integer):v/=float(2**(np.iinfo(data.dtype).bits-1))
   rms=np.zeros(frames,dtype=np.float32);rms[:n]=np.mean(v.reshape(n,block,-1)**2,axis=(1,2))
   if n<frames:rms[n:]=rms[n-1]
   key=mapping[track];power[key]=power.get(key,0)+rms
  levels={k:np.clip((10*np.log10(np.maximum(v,1e-12))+60)/48,0,1) for k,v in power.items()}
  for values in levels.values():
   for i in range(1,len(values)):values[i]=max(values[i],values[i-1]*math.exp(-1/(args.fps*.22)))
  ids=list(power)
  page.evaluate('''async({ids,tune})=>{const {byId}=await import('./catalog.js');const s={title:tune.title,subtitle:`${tune.key} · ${tune.tempo} BPM · ${tune.meter}`,strings:[],winds:[],rear:[],extraStacks:{featured:[],rightColour:[]}};for(const id of ids){const d=byId[id];if(d.solo)s.extraStacks.featured.push(id);else if(d.family==='strings')s.strings.push(id);else if(d.family==='woodwinds')s.winds.push(id);else if(id==='choir')s.choir=id;else if(id==='harp')s.harp=id;else if(d.family==='colours')s.extraStacks.rightColour.push(id);else s.rear.push(id)}window.orchestraStage.setScene(s);document.querySelector('.legend').innerHTML='<span><i class="gold"></i>Solo active</span><span><i class="sage"></i>Active</span><span><i></i>Rest</span>';document.querySelector('.stage-caption').textContent='LIVE LEVELS FROM INDIVIDUAL TRACKS'}''',{'ids':ids,'tune':tune})
  page.wait_for_function('Array.from(document.querySelectorAll("#players img,#stage-floor,#background")).every(i=>i.complete&&i.naturalWidth>0)')
  def frame(i):
   values={k:{'level':float(v[i]),'state':'rest' if v[i]<.04 else 'melody' if ('solo' in k or k in ('hero_sax','violin_concertmaster')) else 'active'} for k,v in levels.items()}
   page.evaluate('v=>window.orchestraStage.setFrame(v)',values)
  frame(min(frames-1,round(60*args.fps)));page.screenshot(path=str(args.out.with_suffix('.preview.png')))
  if args.preview:
   browser.close();return
  log=args.out.with_suffix('.ffmpeg.log').open('w')
  enc=subprocess.Popen(['ffmpeg','-y','-f','image2pipe','-vcodec','mjpeg','-framerate',str(args.fps),'-i','pipe:0','-i',str(args.tune_dir/'mix.wav'),'-map','0:v','-map','1:a','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-t',str(duration),'-movflags','+faststart',str(args.out)],stdin=subprocess.PIPE,stderr=log)
  try:
   for i in range(frames):
    frame(i);enc.stdin.write(page.screenshot(type='jpeg',quality=94))
    if i%(args.fps*10)==0:print(f'{i/args.fps:.0f}/{duration:.1f}s',flush=True)
   enc.stdin.close();code=enc.wait()
   if code:raise RuntimeError(f'ffmpeg exit {code}')
  finally:
   if enc.poll() is None:enc.kill()
   log.close();browser.close()
  args.out.with_suffix('.json').write_text(json.dumps({'title':tune['title'],'duration':duration,'fps':args.fps,'tracks':mapping,'meter':'RMS dBFS, fixed -60 to -12 dB range, 220ms release; grouped registrations combine powers; no master or bus audio double counted'},indent=2))
  print(args.out,flush=True)
if __name__=='__main__':main()
