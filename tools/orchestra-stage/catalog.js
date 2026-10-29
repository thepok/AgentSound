// Visual vocabulary for Endless orchestra. Different sampled registrations share pictures.
const define=(id,label,icon,family,extra={})=>({id,label,icon:`assets/icons/${icon}.png`,family,...extra});
export const instruments=[
 define('violins1','Violins I','violin','strings',{copies:4}),define('violins2','Violins II','violin','strings',{copies:3}),define('violas','Violas','viola','strings',{copies:3}),define('cellos','Celli','cello','strings',{copies:3}),define('basses','Basses','double-bass','strings',{copies:2}),
 define('flutes','Flutes','flute','woodwinds',{copies:2}),define('oboes','Oboes','oboe','woodwinds',{copies:2}),define('clarinets','Clarinets','clarinet','woodwinds',{copies:2}),define('bassoons','Bassoons','bassoon','woodwinds',{copies:2}),
 define('horns','Horns','horn','brass',{copies:2}),define('trumpets','Trumpets','trumpet','brass',{copies:2}),define('trombones','Trombones','trombone','brass',{copies:2}),define('tuba','Tuba','tuba','brass'),
 define('timpani','Timpani','timpani','percussion'),define('percussion','Percussion','percussion','percussion'),define('harp','Harp','harp','colours'),define('celesta','Celesta','celesta','colours'),define('harpsichord','Harpsichord','harpsichord','colours'),define('organ','Organ','organ','colours'),define('guitar','Guitar','guitar','colours'),define('bells','Tubular bells','bells','percussion'),define('glockenspiel','Glockenspiel','glockenspiel','percussion'),define('choir','Choir','choir','voices'),
 ...[['violin_solo','Solo violin','violin'],['cello_solo','Solo cello','cello'],['violin_concertmaster','Concertmaster','violin'],['flute_solo','Solo flute','flute'],['oboe_solo','Solo oboe','oboe'],['clarinet_solo','Solo clarinet','clarinet'],['bassoon_solo','Solo bassoon','bassoon'],['horn_solo','Solo horn','horn'],['hero_sax','Hero Sax','saxophone']].map(([id,label,icon])=>define(id,label,icon,'solo',{solo:true}))
];
export const byId=Object.fromEntries(instruments.map(x=>[x.id,x]));
export function resolveInstrument(id){if(byId[id])return byId[id];if(id.startsWith('choir_'))return byId.choir;if(id.startsWith('organ_'))return byId.organ;if(id==='low_brass')return byId.trombones;return null;}
export const presets={
 symphony:{title:'Rising Forests of the Sea',subtitle:'F major · 80 BPM · 4/4',strings:['violins1','violins2','violas','cellos','basses'],winds:['flutes','oboes','clarinets','bassoons'],rear:['horns','timpani','trumpets','trombones','tuba'],harp:'harp',guest:'celesta',solo:'oboe_solo'},
 chamber:{title:'A Clearing in the Woods',subtitle:'Chamber orchestra · visual study',strings:['violins1','violins2','violas','cellos','basses'],winds:['flutes','oboes','clarinets','bassoons'],rear:['horns'],harp:'harp',guest:'guitar',solo:'violin_solo'},
 nocturne:{title:'Gold over the Water',subtitle:'Orchestra & Hero Sax · visual study',strings:['violins1','violins2','violas','cellos','basses'],winds:['flutes','oboes','clarinets','bassoons'],rear:['horns','timpani','trumpets','trombones'],harp:'harp',guest:'organ',solo:'hero_sax',choir:'choir'}
};
