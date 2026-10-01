// Canvas 2D helpers for the overlay: type, easing, shapes, icons. Coordinates are a logical 1920 x 1080 page.

export const SERIF = '"Sitka Banner", "Sitka Display", Cambria, Georgia, serif';
export const SERIF_TEXT = '"Sitka Text", Cambria, Georgia, serif';
export const SANS = 'Bahnschrift, "Segoe UI", Arial, sans-serif';
export const MONO = 'Consolas, "Cascadia Mono", "Courier New", monospace';

export const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const eOut = (t) => 1 - Math.pow(1 - clamp(t), 3);
export const eInOut = (t) => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
export const eBack = (t) => { t = clamp(t); const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
export const ramp = (x, a, b) => clamp((x - a) / (b - a));
// visible 0..1 for an element shown from a to b with fades fi / fo
export const vis = (u, a, b, fi = 0.5, fo = 0.5) => Math.min(ramp(u, a, a + fi), 1 - ramp(u, b - fo, b));

export function rgba(hex, a = 1) {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}
export function hexToRgb01(hex) {
  const n = parseInt(hex.replace('#', ''), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}
export function rgb01ToHex(c) {
  return '#' + c.map((x) => Math.round(clamp(x) * 255).toString(16).padStart(2, '0')).join('');
}

export function text(g, s, x, y, o = {}) {
  g.save();
  g.font = `${o.style || ''} ${o.weight || 400} ${o.size || 28}px ${o.font || SANS}`;
  g.textAlign = o.align || 'left';
  g.textBaseline = o.base || 'alphabetic';
  g.letterSpacing = `${o.track || 0}px`;
  g.globalAlpha = (o.alpha ?? 1) * g.globalAlpha;
  if (o.glow) { g.shadowColor = o.glowColor || o.color || '#fff'; g.shadowBlur = o.glow; }
  g.fillStyle = o.color || '#f2efe8';
  g.fillText(s, x, y);
  g.restore();
}

const MEASURED = new Map();
export function measure(g, s, o = {}) {
  const font = `${o.style || ''} ${o.weight || 400} ${o.size || 28}px ${o.font || SANS}`;
  const key = `${font}|${o.track || 0}|${s}`;
  let w = MEASURED.get(key);
  if (w === undefined) {
    g.save();
    g.font = font;
    g.letterSpacing = `${o.track || 0}px`;
    w = g.measureText(s).width;
    g.restore();
    if (MEASURED.size > 20000) MEASURED.clear();
    MEASURED.set(key, w);
  }
  return w;
}

const WRAPPED = new Map();
export function wrap(g, s, maxW, o = {}) {
  const key = `${o.style || ''}|${o.weight || 400}|${o.size || 28}|${o.font || SANS}|${o.track || 0}|${maxW}|${s}`;
  const hit = WRAPPED.get(key);
  if (hit) return hit;
  const lines = wrapRaw(g, s, maxW, o);
  if (WRAPPED.size > 5000) WRAPPED.clear();
  WRAPPED.set(key, lines);
  return lines;
}

function wrapRaw(g, s, maxW, o = {}) {
  const words = String(s).split(/\s+/);
  const lines = []; let cur = '';
  for (const w of words) {
    const t = cur ? `${cur} ${w}` : w;
    if (measure(g, t, o) > maxW && cur) { lines.push(cur); cur = w; } else cur = t;
  }
  if (cur) lines.push(cur);
  return lines;
}

export function paragraph(g, s, x, y, maxW, o = {}) {
  let lines = wrap(g, s, maxW, o);
  if (o.maxLines && lines.length > o.maxLines) {
    lines = lines.slice(0, o.maxLines);
    let last = lines[o.maxLines - 1];
    while (measure(g, last + '…', o) > maxW && last.includes(' ')) last = last.slice(0, last.lastIndexOf(' '));
    lines[o.maxLines - 1] = last.replace(/[,;:(\s-]+$/, '') + '…';
  }
  const lh = o.lineHeight || (o.size || 28) * 1.3;
  lines.forEach((l, i) => text(g, l, x, y + i * lh, o));
  return lines.length * lh;
}

export function rrect(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}

export function panel(g, x, y, w, h, o = {}) {
  g.save();
  g.globalAlpha *= o.alpha ?? 1;
  rrect(g, x, y, w, h, o.r ?? 18);
  const grd = g.createLinearGradient(x, y, x, y + h);
  grd.addColorStop(0, o.top || 'rgba(22,24,34,0.78)');
  grd.addColorStop(1, o.bottom || 'rgba(10,11,17,0.82)');
  g.fillStyle = grd; g.fill();
  if (o.border) { g.lineWidth = o.lineWidth || 1.5; g.strokeStyle = o.border; g.stroke(); }
  g.restore();
}

export function chip(g, s, x, y, color, o = {}) {
  const size = o.size || 20;
  const w = measure(g, s, { size, weight: 600, track: 1.5 }) + size * 1.1;
  const h = size * 1.55;
  g.save();
  g.globalAlpha *= o.alpha ?? 1;
  rrect(g, x, y - h * 0.72, w, h, h / 2);
  g.fillStyle = rgba(color, o.fill ?? 0.18); g.fill();
  g.lineWidth = 1.5; g.strokeStyle = rgba(color, 0.9); g.stroke();
  g.restore();
  text(g, s, x + size * 0.55, y, { size, weight: 600, color: o.textColor || color, track: 1.5, alpha: o.alpha ?? 1 });
  return w;
}

// small line icons per role (drawn in a unit box centred on 0,0, radius r)
export function icon(g, role, x, y, r, color) {
  g.save();
  g.translate(x, y);
  g.strokeStyle = color; g.fillStyle = color; g.lineWidth = Math.max(2, r * 0.09); g.lineCap = 'round'; g.lineJoin = 'round';
  const L = (pts) => { g.beginPath(); pts.forEach(([a, b], i) => (i ? g.lineTo(a * r, b * r) : g.moveTo(a * r, b * r))); g.stroke(); };
  switch (role) {
    case 'producer': { // a slate / clapper
      g.strokeRect(-0.55 * r, -0.2 * r, 1.1 * r, 0.75 * r);
      L([[-0.55, -0.2], [-0.45, -0.55], [0.6, -0.55], [0.55, -0.2]]);
      L([[-0.2, -0.55], [-0.3, -0.2]]); L([[0.15, -0.55], [0.05, -0.2]]); L([[0.45, -0.55], [0.35, -0.2]]);
      break; }
    case 'arranger': { // staff + notes
      for (let i = 0; i < 5; i++) L([[-0.65, -0.4 + i * 0.2], [0.65, -0.4 + i * 0.2]]);
      [[-0.3, 0.1], [0.05, -0.1], [0.4, -0.3]].forEach(([a, b]) => { g.beginPath(); g.ellipse(a * r, b * r, 0.12 * r, 0.09 * r, -0.4, 0, 7); g.fill(); L([[a + 0.11, b], [a + 0.11, b - 0.55]]); });
      break; }
    case 'pianist': { // keys
      g.strokeRect(-0.65 * r, -0.4 * r, 1.3 * r, 0.8 * r);
      for (let i = 1; i < 6; i++) L([[-0.65 + i * 0.2167, -0.4], [-0.65 + i * 0.2167, 0.4]]);
      [0, 1, 3, 4].forEach((i) => g.fillRect((-0.65 + (i + 1) * 0.2167 - 0.06) * r, -0.4 * r, 0.12 * r, 0.45 * r));
      break; }
    case 'drummer': { // drum + sticks
      g.beginPath(); g.ellipse(0, -0.1 * r, 0.55 * r, 0.18 * r, 0, 0, 7); g.stroke();
      L([[-0.55, -0.1], [-0.55, 0.35]]); L([[0.55, -0.1], [0.55, 0.35]]);
      g.beginPath(); g.ellipse(0, 0.35 * r, 0.55 * r, 0.18 * r, 0, 0, Math.PI); g.stroke();
      L([[-0.2, -0.3], [-0.65, -0.75]]); L([[0.2, -0.3], [0.65, -0.75]]);
      break; }
    case 'bassist': { // bass clef
      g.beginPath(); g.arc(-0.05 * r, -0.1 * r, 0.35 * r, Math.PI * 1.05, Math.PI * 0.35, false); g.stroke();
      L([[0.24, 0.1], [-0.35, 0.6]]);
      g.beginPath(); g.arc(-0.33 * r, -0.12 * r, 0.1 * r, 0, 7); g.fill();
      g.beginPath(); g.arc(0.5 * r, -0.25 * r, 0.06 * r, 0, 7); g.fill(); g.beginPath(); g.arc(0.5 * r, 0.05 * r, 0.06 * r, 0, 7); g.fill();
      break; }
    case 'guitarist': { // pick
      g.beginPath(); g.moveTo(0, 0.65 * r); g.bezierCurveTo(-0.7 * r, -0.05 * r, -0.55 * r, -0.6 * r, 0, -0.6 * r);
      g.bezierCurveTo(0.55 * r, -0.6 * r, 0.7 * r, -0.05 * r, 0, 0.65 * r); g.stroke();
      break; }
    case 'hornist': { // horn bell
      L([[-0.65, -0.1], [0.05, -0.1]]); L([[-0.65, 0.1], [0.05, 0.1]]);
      g.beginPath(); g.moveTo(0.05 * r, -0.1 * r); g.quadraticCurveTo(0.35 * r, -0.2 * r, 0.6 * r, -0.5 * r); g.lineTo(0.6 * r, 0.5 * r);
      g.quadraticCurveTo(0.35 * r, 0.2 * r, 0.05 * r, 0.1 * r); g.stroke();
      [-0.45, -0.25, -0.05].forEach((a) => { g.beginPath(); g.arc(a * r, -0.22 * r, 0.05 * r, 0, 7); g.fill(); });
      break; }
    case 'sound-designer': { // waveform
      g.beginPath();
      for (let i = 0; i <= 40; i++) { const a = -0.7 + i * 0.035; const b = Math.sin(i * 0.9) * 0.45 * Math.exp(-Math.abs(i - 20) / 12); i ? g.lineTo(a * r, b * r) : g.moveTo(a * r, b * r); }
      g.stroke();
      break; }
    case 'mix-engineer': { // faders
      [-0.45, 0, 0.45].forEach((a, i) => { L([[a, -0.6], [a, 0.6]]); g.fillRect((a - 0.13) * r, ([-0.2, 0.25, -0.35][i] - 0.07) * r, 0.26 * r, 0.14 * r); });
      break; }
    case 'mastering-engineer': { // meter arc + needle
      g.beginPath(); g.arc(0, 0.35 * r, 0.7 * r, Math.PI * 1.15, Math.PI * 1.85); g.stroke();
      L([[0, 0.35], [0.35, -0.2]]);
      g.beginPath(); g.arc(0, 0.35 * r, 0.08 * r, 0, 7); g.fill();
      break; }
    case 'a-and-r': { // ear / check: a verdict seal
      g.beginPath(); g.arc(0, 0, 0.58 * r, 0, 7); g.stroke();
      g.beginPath(); g.arc(0, 0, 0.42 * r, 0, 7); g.stroke();
      L([[-0.2, 0.0], [-0.05, 0.16], [0.24, -0.16]]);
      break; }
    default:
      g.beginPath(); g.arc(0, 0, 0.5 * r, 0, 7); g.stroke();
  }
  g.restore();
}
