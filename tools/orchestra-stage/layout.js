/** Pure visual layout: percentages of the stage, no music-specific logic.
 * A stack chooses rows/columns and scales every element until ALL items fit.
 * Regions and their gaps are supplied by the composition, never by the icons.
 */
export function layoutStacks(stacks, {gap=1.2, rowGap=1.5}={}) {
 const placed=[];
 for(const stack of stacks){
  const {id,items,bounds}=stack;const {x,y,width,height}=bounds;
  if(![x,y,width,height].every(Number.isFinite)||width<=0||height<=0)throw new Error(`Invalid stack bounds: ${id}`);
  if(!items.length)continue;
  const idealWidth=stack.idealWidth??12,idealHeight=stack.idealHeight??height;
  // A shared stage-space parabola follows the projected curved terrace edges.
  // Reserve its full excursion before fitting, so curved rows cannot overflow.
  const curve=stack.curve??0,center=stack.curveCenter??50,radius=stack.curveRadius??50;
  const bend=px=>curve*(1-((px-center)/radius)**2);
  const edgeValues=[bend(x),bend(x+width)];
  if(center>=x&&center<=x+width)edgeValues.push(bend(center));
  const low=Math.min(...edgeValues),excursion=Math.max(...edgeValues)-low;
  let best={scale:-1};
  for(let columns=stack.columns??1;columns<=Math.min(items.length,stack.columns??stack.maxColumns??items.length);columns++){
   const rows=Math.ceil(items.length/columns);
   const staggerSpace=stack.stagger&&rows>1?.5*(idealWidth+gap):0;
   const scale=Math.min(1,width/(columns*idealWidth+(columns-1)*gap+staggerSpace),height/(rows*(idealHeight+excursion)+(rows-1)*rowGap));
   if(scale>best.scale+1e-9||(Math.abs(scale-best.scale)<1e-9&&rows<best.rows))best={scale,columns,rows};
  }
  const {columns,rows,scale}=best;const cellHeight=idealHeight*scale,cellWidth=idealWidth*scale;
  const top=y+(height-(rows*(cellHeight+excursion*scale)+(rows-1)*rowGap*scale))/2;
  for(let row=0;row<rows;row++){
   const chunk=items.slice(row*columns,(row+1)*columns);
   const used=chunk.length*cellWidth+(chunk.length-1)*gap*scale;
   const spread=stack.spread&&chunk.length>1;
   const inset=stack.stagger&&row%2 ? cellWidth*.35:0;
   const shift=stack.stagger&&rows>1?(row%2?1:-1)*.25*(cellWidth+gap*scale):0;
   const left=spread?x+inset:x+(width-used)/2+shift;
   const step=spread?(width-cellWidth-2*inset)/(chunk.length-1):cellWidth+gap*scale;
   chunk.forEach((item,column)=>{
    const px=left+column*step;
    placed.push({item,stack:id,row,rows,x:px,y:top+row*(cellHeight+(rowGap+excursion)*scale)+(bend(px+cellWidth/2)-low)*scale,width:cellWidth,height:cellHeight,scale});
   });
  }
 }
 return {placed};
}

// A theatre plan is just regions. Another setting can supply an entirely different plan.
export const orchestraPlan={
 rear:{bounds:{x:19,y:35,width:62,height:30},idealWidth:16,idealHeight:18,seatY:51,depth:8},
 middle:{bounds:{x:8,y:55,width:84,height:28},idealWidth:14,idealHeight:16,seatY:78,depth:12},
 stringsLeft:{bounds:{x:3,y:77,width:31,height:20},idealWidth:12,idealHeight:18,seatY:97.5,depth:5},
 stringsRight:{bounds:{x:66,y:77,width:31,height:20},idealWidth:12,idealHeight:18,seatY:97.5,depth:5},
 leftColour:{bounds:{x:3,y:52,width:13,height:22},idealWidth:11,idealHeight:19,seatY:75,depth:15},
 rightColour:{bounds:{x:84,y:52,width:13,height:22},idealWidth:11,idealHeight:19,seatY:75,depth:15}
};
export function arrangeOrchestra(scene,plan=orchestraPlan){
 const extras=scene.extraStacks||{};
 const strings=[...new Set([...(scene.strings||[]),...(extras.strings||[])])];
 const mid=Math.ceil(strings.length/2);
 const groups={rear:[...(scene.rear||[]),...(extras.rear||[]),...(scene.choir?[scene.choir]:[]),...(extras.choir||[])],middle:[...(scene.winds||[]),...(scene.solo?[scene.solo]:[]),...(extras.featured||[]),...(extras.leftWinds||[]),...(extras.rightWinds||[])],stringsLeft:strings.slice(0,mid),stringsRight:strings.slice(mid),leftColour:[...(scene.harp?[scene.harp]:[]),...(extras.leftColour||[])],rightColour:[...(scene.guest?[scene.guest]:[]),...(extras.rightColour||[])]};
 // The side voices share the middle terrace instead of reserving empty wings.
 groups.middle=[...groups.leftColour,...groups.middle,...groups.rightColour];
 groups.leftColour=[];groups.rightColour=[];
 const rowColumns=(id,n)=>{
  const region=plan[id];
  const singleWidth=n*(region.idealWidth??12)+Math.max(0,n-1)*1.2;
  return singleWidth<=region.bounds.width/.78?Math.max(1,n):Math.max(1,Math.ceil(n/2));
 };
 // Each terrace fits independently. Crowded solo rows must not shrink a sparse
 // brass row. Broad middle rows retain their side seats while scaling.
 const fits=Object.fromEntries(Object.keys(groups).map(id=>[id,1]));
 for(let attempt=0;attempt<120;attempt++){
  const out=layoutStacks(Object.entries(groups).map(([id,items])=>{
   const n=new Set(items).size,columns=["rear","middle"].includes(id)?rowColumns(id,n):undefined;
   const spread=id==='middle'&&(columns??n)*(plan[id].idealWidth??12)>=plan[id].bounds.width*.6;
   return {id,items:[...new Set(items)],spread,stagger:true,...plan[id],columns,curve:0,idealWidth:(plan[id].idealWidth??12)*fits[id],idealHeight:(plan[id].idealHeight??plan[id].bounds.height)*fits[id]};
  }));
  for(const p of out.placed){
   const {seatY:baseline,depth}=plan[p.stack];
   const cx=p.x+p.width/2;
   const feet=baseline-depth*((cx-50)/50)**2+(p.row-(p.rows-1)/2)*(p.height+1.5);
   p.y=feet-p.height*.8;
  }
  const a=out.placed;
  const crowded=new Set();
  a.forEach((p,i)=>{
   if(p.x<0||p.y<0||p.x+p.width>100||p.y+p.height>100)crowded.add(p.stack);
   for(const q of a.slice(i+1))if(Math.min(p.x+p.width,q.x+q.width)>Math.max(p.x,q.x)+.01&&Math.min(p.y+p.height,q.y+q.height)>Math.max(p.y,q.y)+.01){crowded.add(p.stack);crowded.add(q.stack)}
  });
  if(!crowded.size)return out;
  for(const id of crowded)fits[id]*=.97;
 }
 throw new Error('Stage arrangement could not fit');
}
