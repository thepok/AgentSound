/* Independent background, keyboard and event layers. Times are seconds, pitches MIDI. */
const canvas=document.querySelector('#piano'),keyboardCtx=canvas.getContext('2d'),stage=document.querySelector('#stage');
const noteCanvas=document.createElement('canvas');noteCanvas.id='notes';noteCanvas.setAttribute('aria-hidden','true');canvas.before(noteCanvas);
const noteCtx=noteCanvas.getContext('2d');let ctx=keyboardCtx;
const $=s=>document.querySelector(s),blackPC=new Set([1,3,6,8,10]);
const keys=[];let whites=0;
for(let pitch=21;pitch<=108;pitch++){const black=blackPC.has(pitch%12);keys.push({pitch,black,slot:black?whites-.32:whites,width:black?.64:1});if(!black)whites++;}
const byPitch=new Map(keys.map(k=>[k.pitch,k]));
let W=1600,H=900,t=3,paused=false,speed=1,density=3,next=0,notes=[],last=0,objectURL=null;
let song=null,pedal=0;const audio=new Audio();audio.preload='auto';const exportMode=new URLSearchParams(location.search).has('render');if(exportMode)document.body.classList.add('render');
const pick=a=>a[Math.floor(Math.random()*a.length)];
function add(pitch,start,duration,hand){notes.push({pitch,start,duration,hand,velocity:.55+Math.random()*.4});}
function schedule(){if(song)return;while(next<t+7){const harmony=Math.floor(next/8)%4,root=[45,41,48,43][harmony];const step=.46+(5-density)*.13;
 add(root,next,1.2+Math.random()*1.6,'left');if(density>1)add(root+7,next+.08,.8+Math.random(),'left');
 for(let i=0;i<density;i++)add(root+pick([19,24,26,28,31,36]),next+i*step,.35+Math.random()*1.4,'right');
 next+=step*density+Math.random()*.5;
 }notes=notes.filter(n=>n.start+n.duration>t-.6);}
function resize(){const r=stage.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,2);W=r.width;H=r.height;for(const layer of [canvas,noteCanvas]){layer.width=Math.round(W*d);layer.height=Math.round(H*d);layer.getContext('2d').setTransform(d,0,0,d,0,0);}draw();}
function rect(x,y,w,h,r=2){ctx.beginPath();ctx.roundRect(x,y,w,h,r);}
function draw(){ctx=keyboardCtx;ctx.clearRect(0,0,W,H);noteCtx.clearRect(0,0,W,H);const kw=W/52,hit=H*.785,kh=H*.17,travel=hit/5.3;const active=new Map();
 pedal=0;if(song)for(const point of song.pedal){if(point[0]>t)break;pedal=point[1];}
 for(const n of notes)if(t>=n.start&&t<n.start+n.duration)active.set(n.pitch,Math.max(active.get(n.pitch)||0,n.velocity));
 // Extremely faint octave lanes; notes themselves remain precisely aligned with their keys.
 ctx.lineWidth=.5;ctx.strokeStyle='#ffe2ac12';for(const k of keys)if(k.pitch%12===0){const x=(k.slot+.5)*kw;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,hit);ctx.stroke();}
 // Separate note layer: the spatial fade never affects keys or background.
 ctx=noteCtx;ctx.save();ctx.beginPath();ctx.rect(0,0,W,hit);ctx.clip();
 for(const n of notes){const k=byPitch.get(n.pitch),bottom=hit-(n.start-t)*travel,top=hit-(n.start+n.duration-t)*travel;if(bottom<0||top>hit)continue;
 if(!k)continue;const width=kw*(k.black?.56:.78),x=(k.slot+k.width/2)*kw-width/2,y=Math.max(-8,top),h=bottom-y;
 const lit=t>=n.start,base=n.hand==='left'?'#ffb34d':'#ffe4a5';ctx.shadowColor=base;ctx.shadowBlur=lit?W*.009:W*.004;
 const g=ctx.createLinearGradient(x,0,x+width,0);g.addColorStop(0,n.hand==='left'?'#b9712399':'#ca9b5999');g.addColorStop(.5,n.hand==='left'?'#f9ad4bd9':'#ffe3a6db');g.addColorStop(1,n.hand==='left'?'#bd7b2bb8':'#e2b776b8');ctx.fillStyle=g;rect(x,y,width,Math.max(1,h),Math.min(width*.2,5));ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle=lit?'#fff3ce':'#f6d18cb8';ctx.lineWidth=.9;ctx.stroke();}
 ctx.restore();ctx=keyboardCtx;
 // Ebony frame and the single shared strike line.
 const frame=ctx.createLinearGradient(0,hit,0,H);frame.addColorStop(0,'#30261b');frame.addColorStop(.08,'#080807');frame.addColorStop(.9,'#211a13');frame.addColorStop(1,'#030303');ctx.fillStyle=frame;ctx.fillRect(0,hit,W,H-hit);
 function key(k){const strength=active.get(k.pitch)||0,x=k.slot*kw+1,y=hit+6+(strength?H*.003:0),w=k.width*kw-1.5,h=k.black?kh*.63:kh;const g=ctx.createLinearGradient(x,y,x,y+h);
 if(k.black){g.addColorStop(0,strength?'#c38b3b':'#37312b');g.addColorStop(.75,strength?'#765023':'#090909');g.addColorStop(1,strength?'#e6b45c':'#211d19');}else{g.addColorStop(0,strength?'#ffdf95':'#a99c87');g.addColorStop(.2,strength?'#ffe8b0':'#d7cbb6');g.addColorStop(1,strength?'#f8c66b':'#eee2cb');}
 ctx.fillStyle=g;rect(x,y,w,h,Math.min(2,w*.1));ctx.fill();ctx.fillStyle=k.black?'#000':'#756049';ctx.fillRect(x,y+h-3,w,3);ctx.strokeStyle=k.black?'#5a4b3733':'#fff4cf44';ctx.lineWidth=.6;ctx.strokeRect(x+.5,y+.5,w-1,h-3);
 if(strength){ctx.save();ctx.shadowColor='#ffd47a';ctx.shadowBlur=W*.014;ctx.fillStyle='#ffe7a2';ctx.fillRect(x+1,hit+1,Math.max(1,w-2),3);ctx.restore();}
 }
 keys.filter(k=>!k.black).forEach(key);keys.filter(k=>k.black).forEach(key);
 ctx.fillStyle='#ba8b4c';ctx.fillRect(0,hit-1,W,1);ctx.fillStyle='#0007';ctx.fillRect(0,hit+kh+9,W,H*.01);
 // Contact bloom is anchored to the key, never the falling end of a note.
 for(const [pitch,v] of active){const k=byPitch.get(pitch),x=(k.slot+k.width/2)*kw;const glow=ctx.createRadialGradient(x,hit,0,x,hit,kw*1.5);glow.addColorStop(0,`rgba(255,220,145,${v*.65})`);glow.addColorStop(1,'rgba(255,185,70,0)');ctx.fillStyle=glow;ctx.fillRect(x-kw*1.5,hit-kw*1.5,kw*3,kw*3);}
 // One actual sustain pedal, including its recorded half-pedal position.
 const px=W*.5,py=H*.979,pw=W*.043,ph=H*.015*(1-.35*pedal);
 ctx.save();ctx.translate(px,py+pedal*H*.004);ctx.shadowColor='#e5b760';ctx.shadowBlur=pedal*W*.006;
 const metal=ctx.createLinearGradient(0,-ph,0,ph);metal.addColorStop(0,pedal?'#f6d58d':'#9c8258');metal.addColorStop(.45,pedal?'#b88b44':'#5e4c32');metal.addColorStop(1,'#332618');ctx.fillStyle=metal;rect(-pw/2,-ph/2,pw,ph,ph/2);ctx.fill();ctx.shadowBlur=0;ctx.fillStyle='#bca77e';ctx.font=`${H*.0105}px Georgia`;ctx.textAlign='right';ctx.fillText('SUSTAIN',-pw*.7,ph*.3);ctx.textAlign='left';ctx.fillText(pedal===0?'OFF':pedal<1?'HALF':'ON',pw*.7,ph*.3);ctx.restore();
}
function loop(now){if(!exportMode){if(song)t=audio.currentTime;else if(last&&!paused)t+=Math.min((now-last)/1000,.1)*speed;schedule();draw();}last=now;requestAnimationFrame(loop);}
function toggle(){if(song){if(audio.paused)audio.play().catch(e=>$('#message').textContent=e.message);else audio.pause();return;}paused=!paused;$('#pause').textContent=paused?'▶ Weiter':'Ⅱ Pause';$('#pause').setAttribute('aria-pressed',String(paused));}
$('#pause').onclick=toggle;$('#speed').oninput=e=>{speed=+e.target.value;audio.playbackRate=speed;$('#speedValue').value=speed.toFixed(1)+'×';};
$('#density').oninput=e=>{density=+e.target.value;notes=notes.filter(n=>n.start<=t);next=t+.6;schedule();};
$('#brightness').oninput=e=>$('#background').style.filter=`brightness(${e.target.value/100})`;
async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await stage.requestFullscreen();}catch{$('#message').textContent='Vollbild ist in diesem Browser nicht verfügbar.';}}
$('#fullscreen').onclick=fullscreen;
$('#upload').onchange=async e=>{const f=e.target.files[0];if(!f)return;const url=URL.createObjectURL(f),img=new Image();img.src=url;try{await img.decode();if(objectURL)URL.revokeObjectURL(objectURL);objectURL=url;$('#background').src=url;$('#message').textContent=f.name+' · nur lokal in dieser Vorschau';}catch{URL.revokeObjectURL(url);$('#message').textContent='Dieses Bild konnte nicht geladen werden.';}e.target.value='';};
$('#reset').onclick=()=>{$('#background').src='assets/after-hours.png';if(objectURL)URL.revokeObjectURL(objectURL);objectURL=null;$('#message').textContent='';};
document.addEventListener('keydown',e=>{if(/INPUT|BUTTON|SELECT|TEXTAREA/.test(e.target.tagName))return;if(e.code==='Space'){e.preventDefault();toggle();}if(e.key.toLowerCase()==='f')fullscreen();});
new ResizeObserver(resize).observe(stage);schedule();requestAnimationFrame(loop);
// Small read-only inspection hook for verifying timing and keyboard geometry.
window.pianoPreview={get time(){return t},get active(){return notes.filter(n=>t>=n.start&&t<n.start+n.duration).map(n=>n.pitch)},get keys(){return keys},get paused(){return paused}};

function playbackState(){paused=audio.paused;$('#pause').textContent=paused?'? Abspielen':'? Pause';$('#pause').setAttribute('aria-pressed',String(paused));}
audio.addEventListener('play',playbackState);audio.addEventListener('pause',playbackState);audio.addEventListener('ended',playbackState);
window.loadPianoSong=function(data,audioURL){song=data;notes=data.notes;t=0;paused=true;audio.pause();if(audioURL)audio.src=audioURL;document.querySelector('h1').textContent=data.title;$('#hint').textContent='Melodie ? Champagner / Begleitung ? Gold';document.querySelector('.tag').textContent='ECHTE NOTEN ? SUSTAIN-PEDAL';$('#density').disabled=true;$('#seek').max=data.duration;playbackState();draw();};
window.renderPianoAt=function(seconds){t=seconds;draw();return {time:t,pedal,active:notes.filter(n=>t>=n.start&&t<n.start+n.duration).map(n=>n.pitch)};};
$('#seek').oninput=e=>{if(song){audio.currentTime=+e.target.value;t=+e.target.value;draw();}};
audio.addEventListener('timeupdate',()=>{$('#seek').value=audio.currentTime;$('#clock').textContent=Math.floor(audio.currentTime/60)+':'+String(Math.floor(audio.currentTime%60)).padStart(2,'0');});
if(!exportMode)fetch('demo/song.json').then(r=>{if(!r.ok)throw Error('demo unavailable');return r.json()}).then(d=>loadPianoSong(d,'demo/mix.mp3')).catch(()=>{$('#message').textContent='Zufallsnoten-Vorschau ? kein Song geladen';});
