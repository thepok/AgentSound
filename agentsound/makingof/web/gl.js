// WebGL2 side of the making-of: the audio-reactive scenes (one fragment shader, crossfaded per section), the 3D note
// highway (instanced), particles (instanced points: ambient motes + onset bursts), and the post chain (UI composite,
// bloom, chromatic aberration, grading, grain, fades). Every draw is a pure function of the uniforms of one frame.

export const SCENE_IDS = { nebula: 0, ink: 1, ring: 2, grid: 3, mandala: 4, scope: 5 };

const COMMON = `#version 300 es
precision highp float;
uniform vec2 R;
float hash(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+1.),f.x), f.y); }
float fbm(vec2 p){ float v=0., a=.5; mat2 m=mat2(1.6,1.2,-1.2,1.6); for(int i=0;i<5;i++){ v+=a*noise(p); p=m*p; a*=.5; } return v; }
`;

const VS_QUAD = `#version 300 es
in vec2 p; out vec2 v_uv; void main(){ v_uv = p*.5+.5; gl_Position = vec4(p,0,1); }`;

const FS_SCENE = COMMON + `
in vec2 v_uv; out vec4 o;
uniform float T, BEAT, LEVEL, KICK, ONSET, SLOW, WIDTH, INTENS, DIM, MIXB, HASCOVER, SEED;
uniform int SA, SB;
uniform sampler2D BANDS, COVER;
uniform vec3 C0, C1, C2, C3;
float band(float x){ return texture(BANDS, vec2(clamp(x,0.,1.), .5)).r; }
float bass(){ return (band(.03)+band(.08)+band(.13))/3.; }
vec3 stars(vec2 uv, float dens, float tw){
  vec3 c = vec3(0);
  for(int l=0;l<3;l++){
    float s = 40. + float(l)*55.;
    vec2 g = uv*s + float(l)*17.3; vec2 id = floor(g), f = fract(g)-.5;
    float h = hash(id + SEED);
    if(h > 1.-dens){ float r = length(f - (vec2(hash(id+3.1),hash(id+7.7))-.5)*.6);
      float b = smoothstep(.09, 0., r) * (.5+.5*sin(T*(1.+h*3.)+h*40.)) * (0.5 + tw);
      c += mix(C3, vec3(1), .5) * b * (1. - float(l)*.25); }
  }
  return c;
}
vec3 nebula(vec2 uv){
  vec2 p = uv*1.5; float t = T*.025;
  vec2 q = vec2(fbm(p + vec2(0., t)), fbm(p + vec2(5.2, 1.3) - t));
  vec2 r = vec2(fbm(p + 3.6*q + vec2(1.7, 9.2) + .08*T), fbm(p + 3.6*q + vec2(8.3, 2.8) - .05*T));
  float f = fbm(p + 3.2*r + KICK*.25);
  vec3 col = mix(C0*.6, C2, clamp(f*f*2.2, 0., 1.));
  col = mix(col, C1, clamp(length(q)*.55*f*(.6+LEVEL), 0., 1.));
  col += C3 * pow(f, 6.) * (.35 + .7*LEVEL);
  col *= .22 + .62*LEVEL + .18*KICK;
  col += stars(uv, .06, ONSET) * (.5 + LEVEL);
  return col;
}
vec3 ink(vec2 uv){
  float t = T*.07;
  vec2 p = vec2(uv.x*1.3, uv.y - t*1.4);
  float warp = fbm(p*1.3 + vec2(0., -t));
  float n = fbm(vec2(p.x*2.2 + warp*1.8 + sin(p.y*1.5+t)*.3, p.y*1.7 - t));
  float plume = exp(-pow(uv.x*1.3 + .25*sin(uv.y*2.+T*.2), 2.)*1.6) * smoothstep(-.6, .2, uv.y + .1) * smoothstep(.55, -.2, uv.y);
  float smoke = smoothstep(.38, .9, n) * plume;
  float flick = .75 + .25*noise(vec2(T*7., 1.)) + .35*LEVEL + .25*KICK;
  vec2 cpos = vec2(0., -.3);
  float glow = exp(-length((uv - cpos)*vec2(1., 1.6))*2.6) * flick;
  float flame = exp(-length((uv - cpos - vec2(0., .06))*vec2(9., 3.5))*3.) * flick;
  vec3 warm = mix(C1, vec3(1., .72, .38), .5);
  vec3 col = C0*.35 + warm*glow*.55 + vec3(1., .85, .6)*flame*.9;
  col += mix(C3*.45, warm*.75, clamp(glow*2., 0., 1.)) * smoke * (.5 + 1.1*LEVEL);
  col += stars(uv*.7, .025, 0.) * .25;
  return col;
}
vec3 coverDisc(vec2 uv, float r0){
  float r = length(uv);
  vec3 c = vec3(0);
  if(HASCOVER > .5 && r < r0){
    vec2 cu = uv/(2.*r0) + .5; cu.y = 1. - cu.y;
    c = texture(COVER, cu).rgb * smoothstep(r0, r0-.006, r);
  }
  return c;
}
vec3 ring(vec2 uv){
  float k = 1. + KICK*.035;
  float r = length(uv)/k, a = atan(uv.y, uv.x);
  float r0 = .24;
  vec3 col = C0*.25 + C2*.18*exp(-r*2.2)*(0.5+LEVEL);
  float rays = pow(max(0., sin(a*9. + T*.12)*.5+.5), 8.) * exp(-r*1.2) * .15 * LEVEL;
  col += C1*rays;
  float x = fract(a/6.2831853 + .25 + T*.004);
  float mirror = abs(x*2. - 1.);
  float nb = 90.;
  float seg = floor(mirror*nb)/nb;
  float v = band(.02 + seg*.9);
  v = pow(v, 1.6) * (.55 + .45*INTENS);
  float r1 = r0 + .025, len = .012 + .2*v;
  float inBar = smoothstep(.0, .002, fract(mirror*nb)/nb - .0015) * smoothstep(.0, .002, (1./nb - fract(mirror*nb)/nb) - .0015);
  float along = smoothstep(r1-.002, r1, r) * smoothstep(r1+len+.002, r1+len, r);
  vec3 bc = mix(C1, C2, smoothstep(0., .8, v)) + C3*pow(v, 3.);
  col += bc * along * inBar * (.75 + .5*v);
  col += bc * exp(-abs(r - r1 - len*.5)*18.) * .08 * v;
  col += C1 * smoothstep(.004, 0., abs(r - r0 - .008)) * .9;
  col += C1 * smoothstep(.003, 0., abs(r - r0 - .045 - .03*SLOW)) * .25;
  col = mix(col, coverDisc(uv/k, r0), step(r, r0));
  col += stars(uv, .04, ONSET)*.5;
  return col;
}
vec3 grid(vec2 uv){
  float hz = -.08;
  vec3 col;
  if(uv.y > hz){
    float h = (uv.y - hz);
    col = mix(C2*.9 + C1*.15, C0*.4, smoothstep(0., .55, h));
    vec2 sc = uv - vec2(0., .2);
    float sun = smoothstep(.29, .285, length(sc));
    float stripes = step(.5, fract((sc.y + .3)*18. - T*.35)) + step(.02, sc.y+.02);
    sun *= clamp(stripes, 0., 1.) + step(0., sc.y);
    vec3 sunc = mix(C1*1.2 + vec3(.25,.1,.0), C2, smoothstep(.25, -.25, sc.y));
    col = mix(col, sunc*(1.1 + .5*LEVEL), sun);
    col += C1*exp(-length(sc)*4.)*.35*(1.+KICK);
    float mx = abs(uv.x);
    float m = hz + .03 + .20*band(.04 + mx*.55)*(1.-mx*.4) + .03*noise(vec2(uv.x*6., 1.));
    float mt = smoothstep(m+.003, m, uv.y);
    col = mix(col, C0*.25, mt);
    col += C1*smoothstep(.004, 0., abs(uv.y - m))*.9*(1.-mt*.2)*step(uv.y, m+.01);
    col += stars(uv, .05, ONSET)*smoothstep(.1, .5, h)*.8;
  } else {
    float d = hz - uv.y;
    float z = .22/d;
    float x = uv.x*z;
    vec2 g = vec2(x*1.6, z + BEAT*1.0);
    vec2 fw = fwidth(g);
    vec2 gl2 = abs(fract(g - .5) - .5)/max(fw, 1e-4);
    float line = 1. - min(min(gl2.x, gl2.y), 1.);
    float fade = exp(-z*.09);
    col = C0*.2 + mix(C2, C1, .5)*line*fade*(1.1 + 1.2*KICK) + C1*exp(-d*7.)*.4*(1.+LEVEL);
  }
  return col;
}
vec3 mandala(vec2 uv){
  float r = length(uv), a = atan(uv.y, uv.x) + T*.06;
  float N = 10.;
  float sa = mod(a, 6.2831853/N); sa = abs(sa - 3.14159265/N);
  vec2 p = vec2(cos(sa), sin(sa))*r;
  float f = fbm(p*3.5 + vec2(T*.12, -T*.07) + KICK*.3);
  float rings = sin(r*38. - T*2.2 + f*5. + band(r*.9)*7.)*.5+.5;
  float petals = pow(max(0., cos(sa*N*.5 + r*9. - T*.8)), 6.);
  vec3 col = mix(C2, C1, .5+.5*sin(r*7. - T*.5 + f*3.));
  rings = pow(rings, 2.5);
  col = col*(rings*.5 + petals*.55)*(.3 + .75*LEVEL + .4*ONSET)*exp(-r*1.1);
  col += C3*exp(-r*7.)*(.35 + .6*KICK);
  col += C0*.2;
  return col;
}
vec3 scopeBg(vec2 uv){
  float r = length(uv);
  vec3 col = C0*.3 + C2*.12*exp(-r*1.8)*(0.6+LEVEL);
  float circ = smoothstep(.002, 0., abs(fract(r*6.) - .5)*.1666 - .0002) * .04 * exp(-r);
  col += C3*circ;
  col += C2*fbm(uv*2. + T*.03)*.12*(.4+LEVEL);
  return col;
}
vec3 scene(int s, vec2 uv){
  if(s==0) return nebula(uv);
  if(s==1) return ink(uv);
  if(s==2) return ring(uv);
  if(s==3) return grid(uv);
  if(s==4) return mandala(uv);
  return scopeBg(uv);
}
void main(){
  vec2 uv = (gl_FragCoord.xy - .5*R)/R.y;
  vec3 c = scene(SA, uv);
  if(MIXB > .001) c = mix(c, scene(SB, uv), MIXB);
  o = vec4(c*DIM, 1.);
}`;

// the note highway: one instance per note; x = pitch, depth = time ahead of now
const VS_NOTES = `#version 300 es
precision highp float;
in vec2 p;                // corner 0..1
in vec4 n;                // t0, dur, pitch, vel
in vec4 c;                // r, g, b, hook + 2 * track index
uniform float NOW, AHEAD, PMIN, PMAX, ASPECT, HY, K, D0, SPREAD;
uniform sampler2D MASK;
out vec2 v_q; out vec4 v_c; out float v_act; out float v_z;
void main(){
  float z0 = n.x - NOW, z1 = n.x + n.y - NOW;
  float ti = floor(c.a*.5 + .01), hook = c.a - 2.*ti;
  float m = texture(MASK, vec2((ti + .5)/256., .5)).r;
  if(z1 < -.7 || z0 > AHEAD || m < .01){ gl_Position = vec4(2.,2.,2.,1.); return; }
  float zz = mix(max(z0, -.7), min(z1, AHEAD), p.y);
  float x = ((n.z - PMIN)/(PMAX - PMIN) - .5)*SPREAD;
  float w = SPREAD/(PMAX - PMIN)*.42*(1. + hook*.6);
  float xx = x + (p.x - .5)*2.*w;
  float zc = zz + D0;
  float sx = xx*K/zc/ASPECT;
  float sy = HY - K*.55/zc;
  gl_Position = vec4(sx, sy, 0., 1.);
  v_q = p; v_c = vec4(c.rgb*m, hook); v_z = zz;
  v_act = step(z0, 0.)*step(0., z1);
}`;
const FS_NOTES = `#version 300 es
precision highp float;
in vec2 v_q; in vec4 v_c; in float v_act; in float v_z; out vec4 o;
uniform float AHEAD, GAIN;
void main(){
  float ex = abs(v_q.x - .5)*2.;
  float edge = smoothstep(1., .55, ex);
  float core = smoothstep(.5, 0., ex);
  float far = smoothstep(AHEAD, AHEAD*.55, v_z) * smoothstep(-.7, -.05, v_z);
  vec3 col = v_c.rgb*(.35 + .9*core) + vec3(1)*core*.25*v_act;
  float b = (.35 + 1.1*v_act + .6*v_c.a) * edge * far * GAIN;
  if(v_c.a > .5) col = mix(col, vec3(1., .9, .6), .35);
  o = vec4(col*b, 1.);
}`;

const VS_PART = `#version 300 es
precision highp float;
in vec4 s;                  // seed.x, seed.y, burst index (-1 ambient), speed
uniform float T, ASPECT, LEVEL, KICK;
uniform vec4 BURSTS[16];    // t_age, strength, cx, cy
uniform float RING;
out float v_a; out float v_h;
float h1(float x){ return fract(sin(x*127.1)*43758.5453); }
void main(){
  vec2 pos; float a; float size;
  if(s.z < 0.){
    float sp = .004 + .012*s.w;
    pos = vec2(fract(s.x + T*sp*.3 + .03*sin(T*.2 + s.y*6.)) - .5, fract(s.y + T*sp) - .5)*vec2(2.*ASPECT, 2.);
    a = (.25 + .75*h1(s.x*9.1))*(.35 + .9*LEVEL)*(.6 + .4*sin(T*(1. + 2.*s.w) + s.x*50.));
    size = 1.5 + 2.5*h1(s.y*3.3) + 2.*KICK;
  } else {
    vec4 b = BURSTS[int(s.z)];
    float age = b.x;
    if(age < 0. || age > 2.2 || b.y <= 0.){ gl_Position = vec4(2,2,2,1); return; }
    float ang = s.x*6.2831853;
    vec2 dir = vec2(cos(ang), sin(ang));
    float v = (.25 + .9*s.w)*(.6 + b.y);
    float dist = v*(1. - exp(-age*2.8))/2.8;
    vec2 c0 = b.zw + dir*RING;
    pos = c0 + dir*dist + vec2(0., -.05*age*age);
    pos.x *= 1.;
    a = b.y*exp(-age*2.2)*(.6 + .4*s.y);
    size = 2. + 4.*s.y*b.y*exp(-age);
  }
  v_a = a; v_h = s.y;
  gl_PointSize = size;
  gl_Position = vec4(pos.x/ASPECT, pos.y, 0., 1.);
}`;
const FS_PART = `#version 300 es
precision highp float;
in float v_a; in float v_h; out vec4 o;
uniform vec3 C1, C3;
void main(){
  float d = length(gl_PointCoord - .5)*2.;
  float m = smoothstep(1., 0., d);
  vec3 col = mix(C1, C3, v_h);
  o = vec4(col*m*m*v_a, 1.);
}`;

const FS_COMP = `#version 300 es
precision highp float;
in vec2 v_uv; out vec4 o;
uniform sampler2D SCENE, UI;
uniform float CA;
void main(){
  vec4 u = texture(UI, vec2(v_uv.x, 1. - v_uv.y));
  vec2 d = v_uv - .5, off = d*CA*(.4 + length(d));
  vec3 s = vec3(texture(SCENE, v_uv - off).r, texture(SCENE, v_uv).g, texture(SCENE, v_uv + off).b);
  o = vec4(s*(1. - u.a) + u.rgb, 1.);
}`;
const FS_BRIGHT = `#version 300 es
precision highp float;
in vec2 v_uv; out vec4 o;
uniform sampler2D SRC; uniform float THR;
void main(){
  vec3 c = texture(SRC, v_uv).rgb;
  float l = max(c.r, max(c.g, c.b));
  o = vec4(c*max(0., l - THR)/max(l, 1e-4), 1.);
}`;
const FS_BLUR = `#version 300 es
precision highp float;
in vec2 v_uv; out vec4 o;
uniform sampler2D SRC; uniform vec2 DIR;
void main(){
  vec3 c = texture(SRC, v_uv).rgb*.227;
  c += (texture(SRC, v_uv + DIR*1.384).rgb + texture(SRC, v_uv - DIR*1.384).rgb)*.316;
  c += (texture(SRC, v_uv + DIR*3.230).rgb + texture(SRC, v_uv - DIR*3.230).rgb)*.070;
  o = vec4(c, 1.);
}`;
const FS_FINAL = COMMON + `
in vec2 v_uv; out vec4 o;
uniform sampler2D COMP, B1, B2, B3, B4;
uniform float BLOOM, FADE, WARM, GRAIN, FRAME, VIG;
vec3 soft(vec3 c){ return mix(c, .8 + .2*(1. - exp(-(c - .8)/.2)), step(.8, c)); }
void main(){
  vec2 d = v_uv - .5;
  vec3 c = texture(COMP, v_uv).rgb;
  vec3 b = texture(B1, v_uv).rgb*.5 + texture(B2, v_uv).rgb*.7 + texture(B3, v_uv).rgb*.9 + texture(B4, v_uv).rgb*1.1;
  c += b*BLOOM;
  c *= mix(vec3(.94, 1., 1.07), vec3(1.07, 1., .92), WARM);
  c *= 1. - VIG*dot(d, d)*1.6;
  c = soft(c);
  c += (hash(gl_FragCoord.xy + FRAME*1.618) - .5)*GRAIN;
  o = vec4(clamp(c*FADE, 0., 1.), 1.);
}`;

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(`shader: ${gl.getShaderInfoLog(s)}\n${src.split('\n').map((l, i) => `${i + 1}: ${l}`).join('\n')}`);
  return s;
}
function program(gl, vs, fs, attribs) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vs));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fs));
  attribs.forEach((a, i) => gl.bindAttribLocation(p, i, a));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(`link: ${gl.getProgramInfoLog(p)}`);
  const u = {};
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i); u[info.name.replace(/\[0\]$/, '')] = gl.getUniformLocation(p, info.name); }
  return { p, u };
}

export class Renderer {
  constructor(canvas, W, H) {
    const gl = canvas.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false, premultipliedAlpha: false });
    if (!gl) throw new Error('no WebGL2');
    this.gl = gl; this.W = W; this.H = H;
    this.float = !!gl.getExtension('EXT_color_buffer_float') || !!gl.getExtension('EXT_color_buffer_half_float');
    gl.getExtension('OES_texture_float_linear');
    this.quad = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    this.P = {
      scene: program(gl, VS_QUAD, FS_SCENE, ['p']),
      comp: program(gl, VS_QUAD, FS_COMP, ['p']),
      bright: program(gl, VS_QUAD, FS_BRIGHT, ['p']),
      blur: program(gl, VS_QUAD, FS_BLUR, ['p']),
      final: program(gl, VS_QUAD, FS_FINAL, ['p']),
      notes: program(gl, VS_NOTES, FS_NOTES, ['p', 'n', 'c']),
      part: program(gl, VS_PART, FS_PART, ['s']),
    };
    this.sceneT = this.target(W, H); this.compT = this.target(W, H);
    this.bloom = [2, 4, 8, 16].map((d) => [this.target(W / d | 0, H / d | 0), this.target(W / d | 0, H / d | 0)]);
    this.bandsTex = this.tex(); this.coverTex = this.tex(); this.uiTex = this.tex(); this.maskTex = this.tex();
    this.maskKey = null;
    this.hasCover = 0;
    // particles
    const NP = 2600, NB = 16, PB = 60;
    const ps = new Float32Array((NP + NB * PB) * 4);
    let k = 0;
    const rnd = mulberry(7);
    for (let i = 0; i < NP; i++) { ps[k++] = rnd(); ps[k++] = rnd(); ps[k++] = -1; ps[k++] = rnd(); }
    for (let b = 0; b < NB; b++) for (let i = 0; i < PB; i++) { ps[k++] = rnd(); ps[k++] = rnd(); ps[k++] = b; ps[k++] = rnd(); }
    this.nPart = NP + NB * PB;
    this.partBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.partBuf); gl.bufferData(gl.ARRAY_BUFFER, ps, gl.STATIC_DRAW);
    this.nNotes = 0;
  }
  tex() {
    const gl = this.gl, t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  target(w, h) {
    const gl = this.gl, t = this.tex();
    if (this.float) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, w, h, 0, gl.RGBA, gl.HALF_FLOAT, null);
    else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    return { t, fb, w, h };
  }
  setCover(img) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.coverTex);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    this.hasCover = 1;
  }
  setNotes(data /* Float32Array 8 per note */) {
    const gl = this.gl;
    this.noteBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.noteBuf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    this.nNotes = data.length / 8;
  }
  setBands(u8) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.bandsTex);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, u8.length, 1, 0, gl.RED, gl.UNSIGNED_BYTE, u8);
  }
  quadDraw(prog, target) {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.fb : null);
    gl.viewport(0, 0, target ? target.w : this.W, target ? target.h : this.H);
    gl.useProgram(prog.p);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.vertexAttribDivisor(0, 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
  bindTex(prog, name, unit, tex) {
    const gl = this.gl;
    gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.uniform1i(prog.u[name], unit);
  }
  // s: frame state (see mo.js)
  draw(s, uiCanvas) {
    const gl = this.gl, P = this.P;
    gl.disable(gl.BLEND);
    // 1 scene
    const sp = P.scene; gl.useProgram(sp.p);
    gl.uniform2f(sp.u.R, this.W, this.H);
    for (const k of ['T', 'BEAT', 'LEVEL', 'KICK', 'ONSET', 'SLOW', 'WIDTH', 'INTENS', 'DIM', 'MIXB', 'SEED']) gl.uniform1f(sp.u[k], s[k] || 0);
    gl.uniform1f(sp.u.HASCOVER, this.hasCover);
    gl.uniform1i(sp.u.SA, s.SA); gl.uniform1i(sp.u.SB, s.SB);
    ['C0', 'C1', 'C2', 'C3'].forEach((k) => gl.uniform3fv(sp.u[k], s.pal[k]));
    this.setBands(s.bands);
    this.bindTex(sp, 'BANDS', 0, this.bandsTex); this.bindTex(sp, 'COVER', 1, this.coverTex);
    this.quadDraw(sp, this.sceneT);
    // 2 highway + particles (additive into the scene)
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
    if (s.highway > 0.01 && this.nNotes) {
      const np = P.notes; gl.useProgram(np.p);
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.sceneT.fb); gl.viewport(0, 0, this.W, this.H);
      const hw = s.hw;
      gl.uniform1f(np.u.NOW, hw.now); gl.uniform1f(np.u.AHEAD, hw.ahead); gl.uniform1f(np.u.PMIN, hw.pmin);
      gl.uniform1f(np.u.PMAX, hw.pmax); gl.uniform1f(np.u.ASPECT, this.W / this.H); gl.uniform1f(np.u.HY, hw.hy);
      gl.uniform1f(np.u.K, hw.k); gl.uniform1f(np.u.D0, hw.d0); gl.uniform1f(np.u.SPREAD, hw.spread);
      gl.uniform1f(np.u.GAIN, s.highway);
      const key = s.mask ? s.mask.join(',') : '*';
      if (key !== this.maskKey) {
        const m = new Uint8Array(256).fill(s.mask ? 20 : 255);
        if (s.mask) s.mask.forEach((i) => { if (i >= 0 && i < 256) m[i] = 255; });
        gl.bindTexture(gl.TEXTURE_2D, this.maskTex); gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, 256, 1, 0, gl.RED, gl.UNSIGNED_BYTE, m);
        this.maskKey = key;
      }
      this.bindTex(np, 'MASK', 0, this.maskTex);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
      // corners as a unit square from the quad (-1..1 -> 0..1 in shader via p) - use a dedicated buffer
      if (!this.cornerBuf) {
        this.cornerBuf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.cornerBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]), gl.STATIC_DRAW);
      }
      gl.bindBuffer(gl.ARRAY_BUFFER, this.cornerBuf);
      gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0); gl.vertexAttribDivisor(0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.noteBuf);
      gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 4, gl.FLOAT, false, 32, 0); gl.vertexAttribDivisor(1, 1);
      gl.enableVertexAttribArray(2); gl.vertexAttribPointer(2, 4, gl.FLOAT, false, 32, 16); gl.vertexAttribDivisor(2, 1);
      gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, this.nNotes);
      gl.vertexAttribDivisor(1, 0); gl.vertexAttribDivisor(2, 0);
      gl.disableVertexAttribArray(1); gl.disableVertexAttribArray(2);
    }
    if (s.particles > 0.01) {
      const pp = P.part; gl.useProgram(pp.p);
      gl.bindFramebuffer(gl.FRAMEBUFFER, this.sceneT.fb); gl.viewport(0, 0, this.W, this.H);
      gl.uniform1f(pp.u.T, s.T); gl.uniform1f(pp.u.ASPECT, this.W / this.H);
      gl.uniform1f(pp.u.LEVEL, s.LEVEL * s.particles); gl.uniform1f(pp.u.KICK, s.KICK); gl.uniform1f(pp.u.RING, s.ring || 0);
      gl.uniform4fv(pp.u.BURSTS, s.bursts);
      gl.uniform3fv(pp.u.C1, s.pal.C1); gl.uniform3fv(pp.u.C3, s.pal.C3);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.partBuf);
      gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 4, gl.FLOAT, false, 0, 0); gl.vertexAttribDivisor(0, 0);
      gl.drawArrays(gl.POINTS, 0, this.nPart);
    }
    gl.disable(gl.BLEND);
    // 3 UI over the scene
    gl.bindTexture(gl.TEXTURE_2D, this.uiTex);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, uiCanvas);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    const cp = P.comp; gl.useProgram(cp.p);
    gl.uniform1f(cp.u.CA, s.CA || 0);
    this.bindTex(cp, 'SCENE', 0, this.sceneT.t); this.bindTex(cp, 'UI', 1, this.uiTex);
    this.quadDraw(cp, this.compT);
    // 4 bloom
    const bp = P.bright; gl.useProgram(bp.p);
    gl.uniform1f(bp.u.THR, s.THR || 0.62);
    this.bindTex(bp, 'SRC', 0, this.compT.t);
    this.quadDraw(bp, this.bloom[0][0]);
    const bl = P.blur;
    for (let i = 0; i < this.bloom.length; i++) {
      const [a, b] = this.bloom[i];
      if (i > 0) { gl.useProgram(bl.p); gl.uniform2f(bl.u.DIR, 0, 0); this.bindTex(bl, 'SRC', 0, this.bloom[i - 1][0].t); this.quadDraw(bl, a); }
      gl.useProgram(bl.p); gl.uniform2f(bl.u.DIR, 1 / a.w, 0); this.bindTex(bl, 'SRC', 0, a.t); this.quadDraw(bl, b);
      gl.useProgram(bl.p); gl.uniform2f(bl.u.DIR, 0, 1 / a.h); this.bindTex(bl, 'SRC', 0, b.t); this.quadDraw(bl, a);
    }
    // 5 final
    const fp = P.final; gl.useProgram(fp.p);
    gl.uniform2f(fp.u.R, this.W, this.H);
    for (const k of ['BLOOM', 'FADE', 'WARM', 'GRAIN', 'FRAME', 'VIG']) gl.uniform1f(fp.u[k], s[k] || 0);
    this.bindTex(fp, 'COMP', 0, this.compT.t);
    this.bloom.forEach(([a], i) => this.bindTex(fp, `B${i + 1}`, i + 1, a.t));
    this.quadDraw(fp, null);
  }
}

export function mulberry(a) {
  return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
