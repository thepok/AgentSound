"""Render the same browser stage at fixed timestamps, then mux its original WAV."""
import argparse,base64,json,math,subprocess,time
from pathlib import Path
from playwright.sync_api import sync_playwright
from prepare_song import prepare

def main():
 p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--out',required=True);p.add_argument('--fps',type=int,default=30);p.add_argument('--limit',type=float);p.add_argument('--url',default='http://127.0.0.1:8775/');a=p.parse_args()
 folder=Path(a.folder);out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 data=prepare(folder,out.parent/'timeline');duration=min(data['duration'],a.limit) if a.limit else data['duration'];frames=math.ceil(duration*a.fps);duration=frames/a.fps
 ffmpeg='C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe'
 log=out.with_suffix('.ffmpeg.log').open('w');start=time.monotonic()
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
  page=b.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(a.url+'?render=1&v=3');page.locator('#background').evaluate('(e)=>e.decode()');page.evaluate('(d)=>loadPianoSong(d)',data)
  page.evaluate('renderPianoAt(10)');page.screenshot(path=str(out.with_suffix('.preview.png')))
  page.add_style_tag(content='canvas{visibility:hidden}')
  backdrop=base64.b64encode(page.screenshot(type='png')).decode()
  page.add_style_tag(content='canvas{visibility:visible}')
  page.evaluate('''async (base)=>{
    const bg=new Image();bg.src='data:image/png;base64,'+base;await bg.decode();
    const output=document.createElement('canvas');output.width=1920;output.height=1080;const c=output.getContext('2d');
    const fade=document.createElement('canvas');fade.width=1920;fade.height=1080;const f=fade.getContext('2d');
    const mask=f.createLinearGradient(0,0,0,1080*.785*2/3);mask.addColorStop(0,'transparent');mask.addColorStop(1,'black');
    window.exportFrame=(time)=>{renderPianoAt(time);c.drawImage(bg,0,0);f.clearRect(0,0,1920,1080);f.globalCompositeOperation='source-over';f.drawImage(document.querySelector('#notes'),0,0);f.globalCompositeOperation='destination-in';f.fillStyle=mask;f.fillRect(0,0,1920,1080);c.drawImage(fade,0,0);c.drawImage(document.querySelector('#piano'),0,0);return output.toDataURL('image/jpeg',.97).split(',')[1];};
  }''',backdrop)
  cmd=[ffmpeg,'-y','-f','image2pipe','-vcodec','mjpeg','-framerate',str(a.fps),'-i','pipe:0','-i',str(folder/'mix.wav'),'-map','0:v:0','-map','1:a:0','-vf','scale=in_range=pc:out_range=tv','-color_range','tv','-colorspace','bt470bg','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-af','apad','-c:a','aac','-b:a','256k','-t',str(duration),'-movflags','+faststart',str(out)]
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
  try:
   for i in range(frames):
    proc.stdin.write(base64.b64decode(page.evaluate('(t)=>exportFrame(t)',i/a.fps)))
    if i%(a.fps*5)==0:
     status=dict(frame=i,frames=frames,percent=round(i/frames*100,1),elapsed=round(time.monotonic()-start,1));out.with_suffix('.progress.json').write_text(json.dumps(status));print(status,flush=True)
   proc.stdin.close();code=proc.wait()
   if code:raise RuntimeError(f'ffmpeg exited {code}')
   if errors:raise RuntimeError(str(errors))
  finally:
   if proc.poll() is None:proc.kill()
   b.close();log.close()
 out.with_suffix('.render.json').write_text(json.dumps(dict(duration=duration,frames=frames,fps=a.fps,source=str(folder),timeline=str(out.parent/'timeline/song.json'),elapsed=time.monotonic()-start),indent=2))
 print('DONE',out,flush=True)
if __name__=='__main__':main()
