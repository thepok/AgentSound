import {iconBounds} from './assets/icons/bounds.js';
import {instruments,byId,presets} from './catalog.js';
import {arrangeOrchestra} from './layout.js';
const $=s=>document.querySelector(s);let scene=structuredClone(presets.symphony),selected='oboe_solo',objectURL;
let previewScene=null;let states={};const backgrounds=['autumn-lake','autumn-forest','autumn-river'];
function initialState(id,index){return {state:id===scene.solo?'melody':index%5===0?'rest':'active',level:[.45,.7,.25,.85,.55][index%5]};}
export function setInstrumentState(id,{state,level}){if(!byId[id])throw new Error(`Unknown instrument: ${id}`);if(!['rest','active','melody'].includes(state))throw new Error('Unknown visual state');if(!Number.isFinite(level)||level<0||level>1)throw new Error('Level must be 0…1');states[id]={state,level};paint();}
function stageItems(){return arrangeOrchestra(previewScene||scene).placed.map(p=>({...p,id:p.item,kind:byId[p.item].solo?'solo':''}));}
function paint(){const items=stageItems();$('#title').textContent=scene.title;$('#subtitle').textContent=scene.subtitle;$('#players').replaceChildren(...items.map(({id,x,y,width,height,kind},index)=>{const d=byId[id];states[id]??=initialState(id,index);const s=states[id];const b=document.createElement('button');b.className=`player ${kind}${selected===id?' selected':''}`;b.style.left=x+'%';b.style.top=y+'%';b.style.width=width+'%';b.style.height=height+'%';b.dataset.state=s.state;b.dataset.instrument=id;b.setAttribute('aria-label',`${d.label}, ${s.state}, preview level ${Math.round(s.level*100)} percent`);b.setAttribute('aria-pressed',String(selected===id));const art=document.createElement('span');art.className='instrument-art'+(d.copies?' group':'');for(let i=0;i<(d.copies||1);i++){const box=iconBounds[d.icon.split('/').pop().replace('.png','')];
 const seat=document.createElement('span');seat.className='instrument-seat';
 seat.style.width=d.copies?'48%':'100%';seat.style.left=d.copies?(i*52/(d.copies-1))+'%':'0';
 const crop=document.createElement('span');crop.className='instrument-crop';crop.style.aspectRatio=`${box.w}/${box.h}`;
 crop.style.width=`min(100%, ${80*height/width/0.88/(d.copies?.48:1)*box.w/box.h*9/16}cqw)`;
 const img=document.createElement('img');img.src=d.icon;img.alt='';img.draggable=false;
 img.style.width=(box.iw/box.w*100)+'%';img.style.height=(box.ih/box.h*100)+'%';img.style.left=(-box.x/box.w*100)+'%';img.style.top=(-box.y/box.h*100)+'%';
 crop.append(img);seat.append(crop);art.append(seat)}const meter=document.createElement('span');meter.className='meter';meter.setAttribute('aria-hidden','true');for(let i=0;i<12;i++){const bar=document.createElement('i');if(s.state!=='rest'&&i<Math.round(s.level*12))bar.className='on';meter.append(bar)}const label=document.createElement('span');label.className='player-label';label.textContent=d.label;b.append(art,meter,label);b.onclick=()=>{selected=id;paint()};return b}));syncInspector();document.querySelectorAll('.catalog-item').forEach(c=>c.classList.toggle('active',items.some(x=>x.id===c.dataset.id)));}
function syncInspector(){if(!stageItems().some(x=>x.id===selected))selected=stageItems()[0].id;const s=states[selected];$('#selected-name').textContent=byId[selected].label;$('#appearance').value=s.state;$('#level').value=s.level;$('#level-text').textContent=Math.round(s.level*100)+'%';}
function setBackground(url){$('#background').src=url;}
function options(select,items,empty){select.replaceChildren();if(empty){let o=new Option('None','');select.add(o)}for(const d of items)select.add(new Option(d.label,d.id))}
options($('#solo'),instruments.filter(x=>x.solo),true);options($('#guest'),instruments.filter(x=>['colours','percussion'].includes(x.family)&&!['harp','timpani','percussion'].includes(x.id)),true);
function syncControls(){$('#solo').value=scene.solo||'';$('#guest').value=scene.guest||'';$('#choir').checked=!!scene.choir;}
$('#preset').onchange=e=>{previewScene=null;$('#density').value=0;$('#density-value').textContent='Song ensemble';scene=structuredClone(presets[e.target.value]);states={};selected=scene.solo;syncControls();paint();};$('#solo').onchange=e=>{scene.solo=e.target.value;selected=scene.solo||scene.strings[0];if(scene.solo)states[scene.solo]={state:'melody',level:.8};paint()};$('#guest').onchange=e=>{scene.guest=e.target.value;paint()};$('#choir').onchange=e=>{scene.choir=e.target.checked?'choir':null;paint()};
$('#appearance').onchange=e=>setInstrumentState(selected,{...states[selected],state:e.target.value});$('#level').oninput=e=>setInstrumentState(selected,{...states[selected],level:+e.target.value});
document.querySelectorAll('[data-bg]').forEach(b=>b.onclick=()=>{if(objectURL){URL.revokeObjectURL(objectURL);objectURL=null}setBackground(`assets/backgrounds/${b.dataset.bg}.png`);document.querySelectorAll('[data-bg]').forEach(x=>x.classList.toggle('selected',x===b));$('#bg-status').textContent='Any image · cropped to fill · stays on your computer';});
$('#upload').onchange=e=>{const file=e.target.files[0];if(!file)return;if(!file.type.startsWith('image/')){$('#bg-status').textContent='Please choose an image file.';return}if(objectURL)URL.revokeObjectURL(objectURL);objectURL=URL.createObjectURL(file);setBackground(objectURL);document.querySelectorAll('[data-bg]').forEach(b=>b.classList.remove('selected'));$('#bg-status').textContent=file.name+' · local preview';};
const exit=document.createElement('button');exit.className='exit-clean';exit.textContent='Back to studio';document.body.append(exit);$('#clean').onclick=()=>document.body.classList.add('clean');exit.onclick=()=>document.body.classList.remove('clean');document.addEventListener('keydown',e=>{if(e.key==='Escape')document.body.classList.remove('clean')});$('#fullscreen').onclick=()=>$('#stage').requestFullscreen().catch(()=>document.body.classList.add('clean'));

function addVoice(id){const d=byId[id];if(!stageItems().some(x=>x.id===id)){
 const stack=d.solo?'featured':d.id==='choir'?'choir':d.family==='strings'?'strings':d.family==='woodwinds'?'leftWinds':d.family==='brass'||d.family==='percussion'?'rear':'rightColour';
 scene.extraStacks??={};scene.extraStacks[stack]??=[];scene.extraStacks[stack].push(id);
}selected=id;states[id]??={state:d.solo?'melody':'active',level:.7};syncControls();paint();}

$('#catalog').replaceChildren(...instruments.map(d=>{const b=document.createElement('button');b.className='catalog-item';b.dataset.id=d.id;const image=document.createElement('img');image.src=d.icon;image.alt='';image.loading='lazy';const name=document.createElement('span');name.textContent=d.label;const family=document.createElement('small');family.textContent=d.solo?'FEATURED VOICE':d.family.toUpperCase();b.append(image,name,family);b.onclick=()=>{addVoice(d.id);};return b}));
$('#library-count').textContent=`${instruments.length} voices · ${new Set(instruments.map(x=>x.icon)).size} instrument illustrations`;
syncControls();paint();
// Visual-only integration boundary. No playback, timing or audio metering is implemented.
window.orchestraStage={setBackground,setInstrumentState,getScene:()=>structuredClone(scene),addVoice,setScene:(next)=>{previewScene=null;scene=structuredClone(next);paint()},getLayout:()=>arrangeOrchestra(previewScene||scene)};

document.querySelector('#all-voices').onclick=()=>{for(const d of instruments)addVoice(d.id)};

$("#floor-style").onchange=e=>{$("#stage-floor").src=`assets/stages/${e.target.value}.png`};

$('#density').oninput=e=>{
 const n=+e.target.value;$('#density-value').textContent=n?`${n} test instruments`:'Song ensemble';
 previewScene=n?{...scene,strings:[],winds:[],rear:[],solo:null,harp:null,guest:null,choir:null,extraStacks:{}}:null;
 if(n)for(let i=0;i<n;i++){
  const id=`dummy_${i}`,d=instruments[i%instruments.length];byId[id]={...d,id,label:`${d.label} ${i+1}`};
  const group=i%5<2?'rear':i%5<4?'winds':'strings';previewScene[group].push(id);
  states[id]={state:'active',level:.6};
 }
 paint();
};
window.orchestraStage.setFrame=(values)=>{for(const [id,value] of Object.entries(values))if(byId[id])states[id]=value;document.querySelectorAll('.player').forEach(el=>{const s=states[el.dataset.instrument];el.dataset.state=s.state;el.querySelectorAll('.meter i').forEach((bar,i)=>bar.classList.toggle('on',s.state!=='rest'&&i<Math.round(s.level*12)))});};

// Real exported ensembles can be reviewed without approximating them with dummies.
fetch('./review-scenes.json').then(r=>r.json()).then(reviews=>{
 for(const review of reviews){
  const s={title:review.title,subtitle:review.subtitle,background:review.background,strings:[],winds:[],rear:[],extraStacks:{featured:[],rightColour:[]}};
  for(const id of review.ids){const d=byId[id];if(d.solo)s.extraStacks.featured.push(id);else if(d.family==='strings')s.strings.push(id);else if(d.family==='woodwinds')s.winds.push(id);else if(id==='choir')s.choir=id;else if(id==='harp')s.harp=id;else if(d.family==='colours')s.extraStacks.rightColour.push(id);else s.rear.push(id)}
  presets[review.id]=s;$('#preset').add(new Option(`${review.label} (${review.ids.length})`,review.id));
 }
 $('#preset').addEventListener('change',()=>{const bg=presets[$('#preset').value]?.background;if(bg)setBackground(bg)});
 const requested=new URLSearchParams(location.search).get('scene');
 if(requested&&presets[requested]){$('#preset').value=requested;$('#preset').dispatchEvent(new Event('change'))}
}).catch(e=>console.warn('Review ensembles unavailable',e));
