"""Python/Pillow frame compositor. Browser used once to bake the approved artwork, never per frame."""
import argparse,base64,io,json,math,subprocess,time
from pathlib import Path
from functools import lru_cache
import numpy as np
from PIL import Image,ImageChops
from playwright.sync_api import sync_playwright
from prepare_song import prepare
W,H=1920,1080
HIT=H*.785
KW=W/52
FF='C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe'
def png(data):return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA')
def bake(data,cache,url):
 cache.mkdir(parents=True,exist_ok=True)
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
  page=b.new_page(viewport={'width':W,'height':H},device_scale_factor=1)
  page.goto(url+'?render=1');page.locator('#background').evaluate('(e)=>e.decode()')
  empty={**data,'notes':[],'pedal':[]};page.evaluate('(d)=>loadPianoSong(d)',empty)
  page.evaluate('renderPianoAt(0)');base=Image.open(io.BytesIO(page.screenshot())).convert('RGB')
  keys=page.evaluate('pianoPreview.keys');(cache/'keys.json').write_text(json.dumps(keys))
  if not (cache/'ready').exists():
   for k in keys:
    d={**empty,'notes':[{'pitch':k['pitch'],'start':0,'duration':1,'velocity':.8,'hand':'right'}]}
    page.evaluate('(d)=>loadPianoSong(d)',d);page.evaluate('renderPianoAt(0)')
    art=png(page.evaluate("canvas.toDataURL('image/png')"));x=round(k['slot']*KW);right=round((k['slot']+k['width'])*KW)
    art.crop((x,math.ceil(HIT+6),right,1042)).save(cache/f"key-{k['pitch']}.png")
   for value in [0,.6,1]:
    page.evaluate('(d)=>loadPianoSong(d)',{**empty,'pedal':[[0,value]]});page.evaluate('renderPianoAt(0)')
    png(page.evaluate("canvas.toDataURL('image/png')")).crop((800,1043,1120,1080)).save(cache/f'pedal-{value}.png')
   # Capture exact browser note geometry as stretchable top/middle/bottom sections.
   for black,pitch in [(False,60),(True,61)]:
    for hand in ['left','right']:
     for lit in [False,True]:
      page.evaluate('(d)=>loadPianoSong(d)',empty)
      # Draw an isolated bar at y=80..280 with original gradients, border and glow.
      script='''([black,hand,lit])=>{const c=noteCtx;c.clearRect(0,0,1920,1080);const width=1920/52*(black?.56:.78),x=50,y=80,h=200;c.shadowColor=hand==='left'?'#ffb34d':'#ffe4a5';c.shadowBlur=lit?1920*.009:1920*.004;const g=c.createLinearGradient(x,0,x+width,0);g.addColorStop(0,hand==='left'?'#b9712399':'#ca9b5999');g.addColorStop(.5,hand==='left'?'#f9ad4bd9':'#ffe3a6db');g.addColorStop(1,hand==='left'?'#bd7b2bb8':'#e2b776b8');c.fillStyle=g;c.beginPath();c.roundRect(x,y,width,h,Math.min(width*.2,5));c.fill();c.shadowBlur=0;c.strokeStyle=lit?'#fff3ce':'#f6d18cb8';c.lineWidth=.9;c.stroke();return noteCanvas.toDataURL('image/png')}'''
      art=png(page.evaluate(script,[black,hand,lit]));art.crop((20,50,110,310)).save(cache/f'note-{int(black)}-{hand}-{int(lit)}.png')
   (cache/'ready').write_text('1')
  b.close()
 return base,keys
class Compositor:
 def __init__(self,data,base,keys,cache):
  self.data=data;self.base=base;self.keys={k['pitch']:k for k in keys};self.notes=data['notes'];self.starts=np.array([n['start'] for n in self.notes]);self.ends=np.array([n['start']+n['duration'] for n in self.notes]);self.pedals=data['pedal'];self.pt=[p[0] for p in self.pedals];self.cache=cache
  self.keyart={k:Image.open(cache/f'key-{k}.png').convert('RGBA') for k in self.keys};self.pedalart={v:Image.open(cache/f'pedal-{v}.png').convert('RGBA') for v in [0,.6,1]}
  self.templates={(black,hand,lit):Image.open(cache/f'note-{int(black)}-{hand}-{int(lit)}.png').convert('RGBA') for black in [False,True] for hand in ['left','right'] for lit in [False,True]}
 @lru_cache(maxsize=2048)
 def bar(self,black,hand,lit,height):
  src=self.templates[black,hand,lit];height=max(12,height);dest=Image.new('RGBA',(90,height+60));cap=min(16,height//2)
  dest.paste(src.crop((0,0,90,30+cap)),(0,0));dest.paste(src.crop((0,129,90,130)).resize((90,max(1,height-2*cap))),(0,30+cap));dest.paste(src.crop((0,230-cap,90,260)),(0,30+height-cap));return dest
 def frame(self,t):
  im=self.base.copy();active={};travel=HIT/5.3
  for i in np.flatnonzero((self.starts<t+5.5)&(self.ends>t)):
   n=self.notes[i];k=self.keys.get(n['pitch'])
   if k is None:continue
   lit=n['start']<=t;bottom=HIT-(n['start']-t)*travel;top=HIT-(n['start']+n['duration']-t)*travel
   # Browser clips the top at -8 before drawing its rounded rectangle.
   top=max(-8,top);height=max(1,round(bottom-top));sprite=self.bar(k['black'],n['hand'],lit,height)
   x=round((k['slot']+k['width']/2)*KW-KW*(.56 if k['black'] else .78)/2-30);y=round(top)-30
   y0=max(0,y);y1=min(math.ceil(HIT),y+sprite.height)
   if y1>y0:
    patch=sprite.crop((0,y0-y,90,y1-y));alpha=patch.getchannel('A');fade=np.clip(np.arange(y0,y1)/(HIT*2/3),0,1);mask=Image.fromarray((np.asarray(alpha)*fade[:,None]).astype('uint8'));im.paste(patch,(x,y0),mask)
   if lit:active[n['pitch']]=n['velocity']
  for pitch in sorted(active,key=lambda p:self.keys[p]['black']):
   k=self.keys[pitch];art=self.keyart[pitch];im.paste(art,(round(k['slot']*KW),math.ceil(HIT+6)),art)
  for pitch,v in active.items():
   k=self.keys[pitch];r=KW*1.5;size=math.ceil(r*2);yy,xx=np.ogrid[:size,:size];a=np.clip(1-np.sqrt((xx-r)**2+(yy-r)**2)/r,0,1)*v*.65*255
   glow=Image.new('RGBA',(size,size),(255,220,145,0));glow.putalpha(Image.fromarray(a.astype('uint8')));im.paste(glow,(round((k['slot']+k['width']/2)*KW-r),round(HIT-r)),glow)
  idx=np.searchsorted(self.pt,t,side='right')-1;pedal=self.pedals[idx][1] if idx>=0 else 0;art=self.pedalart[pedal];im.paste(art,(800,1043),art)
  return im
def main():
 p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--out',required=True);p.add_argument('--url',default='http://127.0.0.1:8775/');p.add_argument('--cache',help='Artwork cache directory (default: next to output)');p.add_argument('--limit',type=float);p.add_argument('--hardware',action='store_true');a=p.parse_args();out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);data=prepare(a.folder,out.parent/'timeline');cache=Path(a.cache) if a.cache else out.parent/'art-cache'
 base,keys=bake(data,cache,a.url);renderer=Compositor(data,base,keys,cache);renderer.frame(10).save(out.with_suffix('.preview.png'));fps=30;frames=math.ceil(min(a.limit or data['duration'],data['duration'])*fps);duration=frames/fps;start=time.monotonic()
 encoder=['-c:v','h264_nvenc','-preset','p6','-rc','vbr','-cq','16','-b:v','0'] if a.hardware else ['-c:v','libx264','-threads','4','-preset','fast','-crf','18']
 with out.with_suffix('.ffmpeg.log').open('w') as log:
  proc=subprocess.Popen([FF,'-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','30','-i','pipe:0','-i',str(Path(a.folder)/'mix.wav'),'-map','0:v','-map','1:a',*encoder,'-color_range','tv','-colorspace','bt470bg','-pix_fmt','yuv420p','-af','apad','-c:a','aac','-b:a','256k','-t',str(duration),'-movflags','+faststart',str(out)],stdin=subprocess.PIPE,stderr=log)
  try:
   for i in range(frames):
    proc.stdin.write(renderer.frame(i/fps).tobytes())
    if i%300==0:
     stat=dict(frame=i,frames=frames,percent=round(i/frames*100,1),elapsed=round(time.monotonic()-start,2));out.with_suffix('.progress.json').write_text(json.dumps(stat));print(stat,flush=True)
   proc.stdin.close();assert proc.wait()==0
  finally:
   if proc.poll() is None:proc.kill()
 out.with_suffix('.render.json').write_text(json.dumps(dict(duration=duration,frames=frames,fps=fps,source=a.folder,renderer='python-pillow',encoder='nvenc-p6-cq16' if a.hardware else 'x264-fast-crf18',elapsed=time.monotonic()-start),indent=2));print('DONE',out,flush=True)
if __name__=='__main__':main()
