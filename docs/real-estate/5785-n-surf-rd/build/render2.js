// Architectural plan renderer: walls with thickness, doors, windows, fixtures and furniture.
// Geometry (rooms) comes from the same validated design file; furnishing is data on each room.
const { ftin, fmt, esc, tally } = require('./render.js');
const S = 16;                     // px per foot
const M = { l: 72, r: 72, t: 62, b: 90 };
const W = 55, H = 30;
const EXT = 0.75, INT = 0.5;     // wall thickness, ft
const CORE = new Set(['stair', 'elevator', 'lobby']);
const OPEN_KINDS = new Set(['outdoor', 'pool', 'garage', 'covered_outdoor']);
const eps = 1e-6;

function fx(n) { return +n.toFixed(2); }
function autoOpen(a, b) {
  // no wall between these kinds
  if (OPEN_KINDS.has(a.kind) && OPEN_KINDS.has(b.kind)) return true;
  if ((a.kind === 'lobby' && b.kind === 'stair') || (b.kind === 'lobby' && a.kind === 'stair')) return true;
  return false;
}

function planSvg(level, rooms, opts) {
  const pw = W * S, ph = H * S;
  const vw = pw + M.l + M.r, vh = ph + M.t + M.b;
  const X = x => M.l + x * S;
  const Y = y => M.t + (H - y) * S;
  const openPairs = new Set((opts.open || []).map(p => p.join('||')));
  const isOpen = (a, b) => autoOpen(a, b) || openPairs.has(a.name + '||' + b.name) || openPairs.has(b.name + '||' + a.name);
  const byName = Object.fromEntries(rooms.map(r => [r.name, r]));
  const out = [];
  out.push(`<svg class="plan arch" viewBox="0 0 ${vw} ${vh}" role="img" aria-label="${esc(opts.aria)}" xmlns="http://www.w3.org/2000/svg">`);
  out.push(`<defs><marker id="ar-${level}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
  <pattern id="wt-${level}" width="14" height="6" patternUnits="userSpaceOnUse"><path d="M0,3 q3.5,-3 7,0 t7,0" fill="none" stroke="currentColor" stroke-width="0.6" opacity="0.4"/></pattern>
  <pattern id="ht-${level}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="currentColor" stroke-width="0.5" opacity="0.35"/></pattern></defs>`);

  // ---- floors
  for (const r of rooms) {
    out.push(`<rect x="${X(r.x)}" y="${Y(r.y + r.h)}" width="${r.w * S}" height="${r.h * S}" class="f-${r.kind}" stroke="none"/>`);
    if (r.kind === 'pool') out.push(`<rect x="${X(r.x)}" y="${Y(r.y + r.h)}" width="${r.w * S}" height="${r.h * S}" fill="url(#wt-${level})" stroke="none"/>`);
    if (r.kind === 'covered_outdoor') out.push(`<rect x="${X(r.x) + 4}" y="${Y(r.y + r.h) + 4}" width="${r.w * S - 8}" height="${r.h * S - 8}" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="6 4" opacity="0.7"/>`);
    if (r.kind === 'void') out.push(`<rect x="${X(r.x)}" y="${Y(r.y + r.h)}" width="${r.w * S}" height="${r.h * S}" fill="url(#ht-${level})" stroke="none"/>`);
  }

  // ---- openings registry: {o:'h'|'v', pos, from, to}
  const openings = [];
  const sideGeom = (r, side) => {
    // returns {o, pos, from, to, dir} ; dir = +1 if the room is on the increasing side of the line
    if (side === 'N') return { o: 'h', pos: r.y + r.h, from: r.x, to: r.x + r.w, inward: -1 };
    if (side === 'S') return { o: 'h', pos: r.y, from: r.x, to: r.x + r.w, inward: +1 };
    if (side === 'E') return { o: 'v', pos: r.x + r.w, from: r.y, to: r.y + r.h, inward: -1 };
    return { o: 'v', pos: r.x, from: r.y, to: r.y + r.h, inward: +1 };
  };
  for (const r of rooms) for (const d of [...(r.doors || []), ...(r.win || [])]) {
    const g = sideGeom(r, d.side);
    openings.push({ o: g.o, pos: g.pos, from: g.from + d.at, to: g.from + d.at + d.w });
  }
  const subtract = (o, pos, from, to) => {
    let segs = [[from, to]];
    for (const op of openings) {
      if (op.o !== o || Math.abs(op.pos - pos) > eps) continue;
      const next = [];
      for (const [a, b] of segs) {
        if (op.to <= a + eps || op.from >= b - eps) { next.push([a, b]); continue; }
        if (op.from > a + eps) next.push([a, op.from]);
        if (op.to < b - eps) next.push([op.to, b]);
      }
      segs = next;
    }
    return segs;
  };

  // ---- walls
  const wall = (o, pos, from, to, t, offset) => {
    // offset: -1 draw on decreasing side of the line, 0 centered, +1 increasing side
    for (const [a, b] of subtract(o, pos, from, to)) {
      if (b - a < 0.05) continue;
      if (o === 'h') {
        const y0 = offset === 0 ? pos + t / 2 : offset > 0 ? pos + t : pos;
        out.push(`<rect x="${X(a)}" y="${Y(y0)}" width="${(b - a) * S}" height="${t * S}" class="wall"/>`);
      } else {
        const x0 = offset === 0 ? pos - t / 2 : offset > 0 ? pos : pos - t;
        out.push(`<rect x="${X(x0)}" y="${Y(b)}" width="${t * S}" height="${(b - a) * S}" class="wall"/>`);
      }
    }
  };
  // exterior walls: envelope boundary, only where an enclosed/core/storage/mechanical room touches it
  const solidKinds = new Set(['enclosed', 'stair', 'elevator', 'lobby', 'storage', 'mechanical']);
  for (const r of rooms) {
    const solid = solidKinds.has(r.kind);
    if (!solid) continue;
    if (Math.abs(r.y - 0) < eps) wall('h', 0, r.x, r.x + r.w, EXT, +1);
    if (Math.abs(r.y + r.h - H) < eps) wall('h', H, r.x, r.x + r.w, EXT, -1);
    if (Math.abs(r.x - 0) < eps) wall('v', 0, r.y, r.y + r.h, EXT, +1);
    if (Math.abs(r.x + r.w - W) < eps) wall('v', W, r.y, r.y + r.h, EXT, -1);
  }
  // interior walls: for each room's N and E sides, find neighbours across
  for (const r of rooms) {
    // N side
    const yN = r.y + r.h;
    if (yN < H - eps) for (const s of rooms) {
      if (s === r || Math.abs(s.y - yN) > eps) continue;
      const a = Math.max(r.x, s.x), b = Math.min(r.x + r.w, s.x + s.w);
      if (b - a < eps) continue;
      if (isOpen(r, s)) { out.push(`<line x1="${X(a)}" y1="${Y(yN)}" x2="${X(b)}" y2="${Y(yN)}" class="openline"/>`); continue; }
      const t = (solidKinds.has(r.kind) && solidKinds.has(s.kind)) ? INT : EXT;
      wall('h', yN, a, b, t, 0);
    }
    const xE = r.x + r.w;
    if (xE < W - eps) for (const s of rooms) {
      if (s === r || Math.abs(s.x - xE) > eps) continue;
      const a = Math.max(r.y, s.y), b = Math.min(r.y + r.h, s.y + s.h);
      if (b - a < eps) continue;
      if (isOpen(r, s)) { out.push(`<line x1="${X(xE)}" y1="${Y(a)}" x2="${X(xE)}" y2="${Y(b)}" class="openline"/>`); continue; }
      const t = (solidKinds.has(r.kind) && solidKinds.has(s.kind)) ? INT : EXT;
      wall('v', xE, a, b, t, 0);
    }
  }

  // ---- door & window symbols
  for (const r of rooms) {
    for (const d of (r.doors || [])) {
      const g = sideGeom(r, d.side);
      const a = g.from + d.at, b = a + d.w;
      const type = d.type || 'swing';
      const hinge = d.hinge || 'l';
      const sw = d.swing === 'out' ? -g.inward : g.inward; // +1 => toward increasing coordinate
      if (g.o === 'h') {
        const y = g.pos;
        if (type === 'swing' || type === 'double') {
          const leaves = type === 'double' ? [[a, a + d.w / 2, 'l'], [b, b - d.w / 2, 'r']] : [[hinge === 'l' ? a : b, hinge === 'l' ? b : a, hinge]];
          for (const [hx, tx] of leaves) {
            const len = Math.abs(tx - hx);
            const ty = y + sw * len;
            out.push(`<line x1="${X(hx)}" y1="${Y(y)}" x2="${X(hx)}" y2="${Y(ty)}" class="leaf"/>`);
            const sweep = ((tx > hx) === (sw > 0)) ? 0 : 1;
            out.push(`<path d="M${X(hx)},${Y(ty)} A${len * S},${len * S} 0 0 ${sweep} ${X(tx)},${Y(y)}" class="arc"/>`);
          }
        } else if (type === 'slider' || type === 'glass') {
          out.push(`<line x1="${X(a)}" y1="${Y(y) - 2}" x2="${X(a + d.w * 0.55)}" y2="${Y(y) - 2}" class="glassline"/><line x1="${X(a + d.w * 0.45)}" y1="${Y(y) + 2}" x2="${X(b)}" y2="${Y(y) + 2}" class="glassline"/>`);
        } else if (type === 'pocket') {
          out.push(`<rect x="${X(a)}" y="${Y(y) - 2}" width="${d.w * 0.5 * S}" height="4" class="leafrect"/>`);
        } else if (type === 'garage') {
          out.push(`<line x1="${X(a)}" y1="${Y(y)}" x2="${X(b)}" y2="${Y(y)}" class="garagedoor"/><line x1="${X(a)}" y1="${Y(y - sw * 0.5)}" x2="${X(b)}" y2="${Y(y - sw * 0.5)}" class="garagedoor"/>`);
        } else if (type === 'opening') {
          out.push(`<line x1="${X(a)}" y1="${Y(y)}" x2="${X(b)}" y2="${Y(y)}" class="openline"/>`);
        }
      } else {
        const x = g.pos;
        if (type === 'swing' || type === 'double') {
          const leaves = type === 'double' ? [[a, a + d.w / 2], [b, b - d.w / 2]] : [[hinge === 'l' ? a : b, hinge === 'l' ? b : a]];
          for (const [hy, ty] of leaves) {
            const len = Math.abs(ty - hy);
            const tx = x + sw * len;
            out.push(`<line x1="${X(x)}" y1="${Y(hy)}" x2="${X(tx)}" y2="${Y(hy)}" class="leaf"/>`);
            const sweep = ((ty > hy) === (sw > 0)) ? 1 : 0;
            out.push(`<path d="M${X(tx)},${Y(hy)} A${len * S},${len * S} 0 0 ${sweep} ${X(x)},${Y(ty)}" class="arc"/>`);
          }
        } else if (type === 'slider' || type === 'glass') {
          out.push(`<line x1="${X(x) - 2}" y1="${Y(a)}" x2="${X(x) - 2}" y2="${Y(a + d.w * 0.55)}" class="glassline"/><line x1="${X(x) + 2}" y1="${Y(a + d.w * 0.45)}" x2="${X(x) + 2}" y2="${Y(b)}" class="glassline"/>`);
        } else if (type === 'pocket') {
          out.push(`<rect x="${X(x) - 2}" y="${Y(a + d.w * 0.5)}" width="4" height="${d.w * 0.5 * S}" class="leafrect"/>`);
        } else if (type === 'garage') {
          out.push(`<line x1="${X(x)}" y1="${Y(a)}" x2="${X(x)}" y2="${Y(b)}" class="garagedoor"/><line x1="${X(x - sw * 0.5)}" y1="${Y(a)}" x2="${X(x - sw * 0.5)}" y2="${Y(b)}" class="garagedoor"/>`);
        } else if (type === 'opening') {
          out.push(`<line x1="${X(x)}" y1="${Y(a)}" x2="${X(x)}" y2="${Y(b)}" class="openline"/>`);
        }
      }
    }
    for (const wdw of (r.win || [])) {
      const g = sideGeom(r, wdw.side);
      const a = g.from + wdw.at, b = a + wdw.w;
      const t = EXT;
      const full = wdw.type === 'glass';
      if (g.o === 'h') {
        const y0 = g.inward > 0 ? g.pos : g.pos - t; // wall band inside the room
        const yy = Y(y0 + t), hh = t * S;
        out.push(`<rect x="${X(a)}" y="${yy}" width="${(b - a) * S}" height="${hh}" class="${full ? 'glassband' : 'winband'}"/>`);
        out.push(`<line x1="${X(a)}" y1="${yy + hh * 0.5}" x2="${X(b)}" y2="${yy + hh * 0.5}" class="glassline"/>`);
        if (!full) out.push(`<line x1="${X(a)}" y1="${yy + hh * 0.3}" x2="${X(b)}" y2="${yy + hh * 0.3}" class="glassline"/><line x1="${X(a)}" y1="${yy + hh * 0.7}" x2="${X(b)}" y2="${yy + hh * 0.7}" class="glassline"/>`);
      } else {
        const x0 = g.inward > 0 ? g.pos : g.pos - t;
        const xx = X(x0), ww = t * S;
        out.push(`<rect x="${xx}" y="${Y(b)}" width="${ww}" height="${(b - a) * S}" class="${full ? 'glassband' : 'winband'}"/>`);
        out.push(`<line x1="${xx + ww * 0.5}" y1="${Y(a)}" x2="${xx + ww * 0.5}" y2="${Y(b)}" class="glassline"/>`);
        if (!full) out.push(`<line x1="${xx + ww * 0.3}" y1="${Y(a)}" x2="${xx + ww * 0.3}" y2="${Y(b)}" class="glassline"/><line x1="${xx + ww * 0.7}" y1="${Y(a)}" x2="${xx + ww * 0.7}" y2="${Y(b)}" class="glassline"/>`);
      }
    }
  }

  // ---- furniture
  const F = [];
  const R = (x, y, w, h, cls = 'furn', rx = 0) => F.push(`<rect x="${X(x)}" y="${Y(y + h)}" width="${w * S}" height="${h * S}" class="${cls}"${rx ? ` rx="${rx}"` : ''}/>`);
  const L = (x1, y1, x2, y2, cls = 'furn') => F.push(`<line x1="${X(x1)}" y1="${Y(y1)}" x2="${X(x2)}" y2="${Y(y2)}" class="${cls}"/>`);
  const C = (cx, cy, r, cls = 'furn') => F.push(`<circle cx="${X(cx)}" cy="${Y(cy)}" r="${r * S}" class="${cls}"/>`);
  const T = (x, y, s, cls = 'ftxt', anchor = 'middle', rot = 0) => F.push(`<text transform="translate(${X(x)} ${Y(y)}) rotate(${rot})" text-anchor="${anchor}" class="${cls}">${esc(s)}</text>`);
  const draw = (r, f) => {
    // f: {t, x, y, w, h, r(rotation 0/90/180/270), n, label}
    const gx = r.x + f.x, gy = r.y + f.y;
    const w = f.w, h = f.h;
    const rot = f.r || 0;
    // rotate the local drawing about the item's centre
    const cx = gx + w / 2, cy = gy + h / 2;
    const grp = [];
    const push = s => grp.push(s);
    const Rr = (x, y, ww, hh, cls = 'furn', rx = 0) => push(`<rect x="${X(x)}" y="${Y(y + hh)}" width="${ww * S}" height="${hh * S}" class="${cls}"${rx ? ` rx="${rx}"` : ''}/>`);
    const Ll = (x1, y1, x2, y2, cls = 'furn') => push(`<line x1="${X(x1)}" y1="${Y(y1)}" x2="${X(x2)}" y2="${Y(y2)}" class="${cls}"/>`);
    const Cc = (x, y, rr, cls = 'furn') => push(`<circle cx="${X(x)}" cy="${Y(y)}" r="${rr * S}" class="${cls}"/>`);
    const Ee = (x, y, rx, ry, cls = 'furn') => push(`<ellipse cx="${X(x)}" cy="${Y(y)}" rx="${rx * S}" ry="${ry * S}" class="${cls}"/>`);
    switch (f.t) {
      case 'bed': { // headboard on the north (y+h) side
        Rr(gx, gy, w, h, 'furn', 3); Rr(gx, gy + h - 0.5, w, 0.5, 'furn-dark');
        Rr(gx + 0.3, gy + h - 1.9, w / 2 - 0.45, 1.2, 'furn', 3); Rr(gx + w / 2 + 0.15, gy + h - 1.9, w / 2 - 0.45, 1.2, 'furn', 3);
        Ll(gx, gy + h - 2.6, gx + w, gy + h - 2.6); break; }
      case 'nightstand': Rr(gx, gy, w, h); Cc(gx + w / 2, gy + h / 2, Math.min(w, h) * 0.25); break;
      case 'sofa': { Rr(gx, gy, w, h, 'furn', 4); Rr(gx, gy + h - 0.6, w, 0.6, 'furn-dark', 3); Rr(gx, gy, 0.6, h, 'furn-dark', 3); Rr(gx + w - 0.6, gy, 0.6, h, 'furn-dark', 3); const n = Math.max(1, Math.round(w / 2.3)); for (let i = 1; i < n; i++) Ll(gx + i * w / n, gy, gx + i * w / n, gy + h - 0.6); break; }
      case 'chaise': Rr(gx, gy, w, h, 'furn', 4); Rr(gx, gy + h - 0.6, w, 0.6, 'furn-dark', 3); break;
      case 'armchair': Rr(gx, gy, w, h, 'furn', 5); Rr(gx, gy + h - 0.5, w, 0.5, 'furn-dark', 3); Rr(gx, gy, 0.5, h, 'furn-dark'); Rr(gx + w - 0.5, gy, 0.5, h, 'furn-dark'); break;
      case 'table': Rr(gx, gy, w, h, 'furn', 2); break;
      case 'rtable': Cc(gx + w / 2, gy + h / 2, w / 2); break;
      case 'dining': { Rr(gx, gy, w, h, 'furn', 2); const n = f.n || 6; const per = Math.ceil(n / 2); for (let i = 0; i < per; i++) { const cxx = gx + (i + 0.5) * w / per; Rr(cxx - 0.8, gy + h + 0.15, 1.6, 1.5, 'furn', 4); if (i < n - per) Rr(cxx - 0.8, gy - 1.65, 1.6, 1.5, 'furn', 4); } break; }
      case 'chair': Rr(gx, gy, w, h, 'furn', 4); break;
      case 'stool': Cc(gx + w / 2, gy + h / 2, w / 2); break;
      case 'island': { Rr(gx, gy, w, h, 'furn-counter'); const n = f.n || 0; for (let i = 0; i < n; i++) Cc(gx + (i + 0.5) * w / n, gy - 0.9, 0.6); if (f.sink) { Rr(gx + w * 0.6, gy + h / 2 - 0.8, 2.3, 1.6, 'furn'); Cc(gx + w * 0.6 + 1.15, gy + h / 2, 0.25); } break; }
      case 'counter': { Rr(gx, gy, w, h, 'furn-counter'); break; }
      case 'sink': Rr(gx, gy, w, h, 'furn', 3); Cc(gx + w / 2, gy + h / 2, 0.22); break;
      case 'cooktop': { Rr(gx, gy, w, h, 'furn'); const pts = [[0.3, 0.3], [0.7, 0.3], [0.3, 0.7], [0.7, 0.7]]; for (const [a, b] of pts) Cc(gx + a * w, gy + b * h, 0.35); break; }
      case 'range': { Rr(gx, gy, w, h, 'furn'); const pts = [[0.3, 0.3], [0.7, 0.3], [0.3, 0.7], [0.7, 0.7]]; for (const [a, b] of pts) Cc(gx + a * w, gy + b * h, 0.32); break; }
      case 'fridge': Rr(gx, gy, w, h, 'furn-dark'); Ll(gx + w / 2, gy, gx + w / 2, gy + h, 'furn-light'); break;
      case 'dw': Rr(gx, gy, w, h, 'furn'); Ll(gx, gy + h - 0.3, gx + w, gy + h - 0.3); break;
      case 'washer': Rr(gx, gy, w, h, 'furn'); Cc(gx + w / 2, gy + h / 2, Math.min(w, h) * 0.32); break;
      case 'wc': Rr(gx, gy + h - 0.7, w, 0.7, 'furn'); Ee(gx + w / 2, gy + (h - 0.7) / 2, w * 0.38, (h - 0.7) * 0.48); break;
      case 'vanity': { Rr(gx, gy, w, h, 'furn-counter'); const n = f.n || 1; for (let i = 0; i < n; i++) Ee(gx + (i + 0.5) * w / n, gy + h / 2, 0.75, 0.55); break; }
      case 'shower': Rr(gx, gy, w, h, 'furn-wet'); Ll(gx, gy, gx + w, gy + h, 'furn-light'); Ll(gx, gy + h, gx + w, gy, 'furn-light'); Cc(gx + w / 2, gy + h / 2, 0.18); break;
      case 'tub': Rr(gx, gy, w, h, 'furn-wet', 6); Rr(gx + 0.35, gy + 0.35, w - 0.7, h - 0.7, 'furn', 10); Cc(gx + w - 0.9, gy + h / 2, 0.15); break;
      case 'sauna': Rr(gx, gy, w, h, 'furn'); Rr(gx + 0.3, gy + h - 2.2, w - 0.6, 1.8, 'furn-dark'); Rr(gx + 0.3, gy + 0.4, 1.2, 1.2, 'furn-dark'); break;
      case 'car': { Rr(gx, gy, w, h, 'furn-car', 8); Ll(gx + w * 0.22, gy + 0.35, gx + w * 0.22, gy + h - 0.35, 'furn-light'); Ll(gx + w * 0.75, gy + 0.35, gx + w * 0.75, gy + h - 0.35, 'furn-light'); Rr(gx + w * 0.3, gy + 0.4, w * 0.4, h - 0.8, 'furn-car2', 4); break; }
      case 'cart': Rr(gx, gy, w, h, 'furn-car', 6); Rr(gx + w * 0.3, gy + 0.3, w * 0.4, h - 0.6, 'furn-car2', 3); break;
      case 'bike': Rr(gx, gy, w, h, 'furn', 2); Cc(gx + 0.5, gy + h / 2, 0.45, 'furn-light'); Cc(gx + w - 0.5, gy + h / 2, 0.45, 'furn-light'); break;
      case 'lounger': Rr(gx, gy, w, h, 'furn', 4); Rr(gx, gy + h - 1.6, w, 1.6, 'furn-dark', 3); break;
      case 'firepit': Cc(gx + w / 2, gy + h / 2, w / 2, 'furn-dark'); Cc(gx + w / 2, gy + h / 2, w / 4, 'furn-fire'); break;
      case 'planter': Rr(gx, gy, w, h, 'furn-green', 2); break;
      case 'grill': Rr(gx, gy, w, h, 'furn-dark'); Ll(gx + 0.3, gy + h / 2, gx + w - 0.3, gy + h / 2, 'furn-light'); break;
      case 'bench': Rr(gx, gy, w, h, 'furn', 3); break;
      case 'tv': Rr(gx, gy, w, h, 'furn-dark'); break;
      case 'desk': Rr(gx, gy, w, h, 'furn'); Rr(gx + w / 2 - 0.8, gy - 1.7, 1.6, 1.5, 'furn', 4); break;
      case 'closet': { // hanging rods along the long side; label
        Rr(gx, gy, w, h, 'furn-closet'); if (w >= h) { Ll(gx, gy + h / 2, gx + w, gy + h / 2, 'furn-light'); for (let i = 0.5; i < w; i += 0.5) Ll(gx + i, gy + h * 0.25, gx + i, gy + h * 0.75, 'furn-hanger'); } else { Ll(gx + w / 2, gy, gx + w / 2, gy + h, 'furn-light'); for (let i = 0.5; i < h; i += 0.5) Ll(gx + w * 0.25, gy + i, gx + w * 0.75, gy + i, 'furn-hanger'); } break; }
      case 'shelf': Rr(gx, gy, w, h, 'furn-closet'); break;
      case 'equip': Rr(gx, gy, w, h, 'furn-dark', 2); break;
      case 'treadmill': Rr(gx, gy, w, h, 'furn', 3); Rr(gx, gy + h - 0.7, w, 0.7, 'furn-dark'); break;
      case 'mat': Rr(gx, gy, w, h, 'furn-green', 4); break;
      case 'steps': { // pool / stair steps: n treads across w, descending toward +x (rotation handles direction)
        const n = f.n || 3; Rr(gx, gy, w, h, 'furn-wet'); for (let i = 1; i < n; i++) Ll(gx + i * w / n, gy, gx + i * w / n, gy + h, 'furn-light'); break; }
      case 'bar': { Rr(gx, gy, w, h, 'furn-counter'); const n = f.n || 0; for (let i = 0; i < n; i++) Cc(gx + (i + 0.5) * w / n, gy - 0.9, 0.55); break; }
      case 'wetstool': Cc(gx + w / 2, gy + h / 2, w / 2, 'furn-light'); break;
      case 'trough': Rr(gx, gy, w, h, 'furn-dark'); break;
      case 'column': Rr(gx, gy, w, h, 'wall'); break;
      case 'label': break;
      case 'rect': Rr(gx, gy, w, h, f.cls || 'furn'); break;
      default: Rr(gx, gy, w, h);
    }
    if (rot) F.push(`<g transform="rotate(${-rot} ${X(cx)} ${Y(cy)})">${grp.join('')}</g>`); else F.push(grp.join(''));
    if (f.label) T(cx, cy - 0.15, f.label, 'ftxt', 'middle', f.lr || 0);
  };
  for (const r of rooms) for (const f of (r.furn || [])) draw(r, f);

  // ---- stairs and elevator symbols
  for (const r of rooms) {
    if (r.kind === 'stair') {
      const st = r.stair || { landing: 3.5, treads: 8, tread: 11 / 12, up: 'W', arrive: level !== 'ground', depart: level !== 'roof' };
      // flights run E-W; half landing at the west end; south half = departing flight (rises westward); north half = arriving flight
      const half = r.h / 2;
      const runLen = st.treads * st.tread;
      const x0 = r.x + st.landing; // first riser of the south flight (at the east end of the landing)... flights run from x0 east to x0+runLen
      const xe = x0 + runLen;
      // landing (west)
      R(r.x, r.y, st.landing, r.h, 'furn-landing');
      // south flight treads
      if (st.depart !== false) for (let i = 0; i <= st.treads; i++) L(x0 + i * st.tread, r.y, x0 + i * st.tread, r.y + half, 'tread');
      if (st.arrive !== false) for (let i = 0; i <= st.treads; i++) L(x0 + i * st.tread, r.y + half, x0 + i * st.tread, r.y + r.h, 'tread');
      L(r.x + st.landing, r.y + half, r.x + r.w, r.y + half, 'furn-dark');
      // direction arrows: UP on the south flight (east → west), DN on the north flight (east → west as well, since one descends westward from the arrival)
      if (st.depart !== false) { L(xe + 0.6, r.y + half / 2, x0 + 0.6, r.y + half / 2, 'stairarrow'); T(xe + 0.9, r.y + half / 2 - 0.15, 'UP', 'ftxt', 'start'); }
      if (st.arrive !== false) { L(xe + 0.6, r.y + half + half / 2, x0 + 0.6, r.y + half + half / 2, 'stairarrow'); T(xe + 0.9, r.y + half + half / 2 - 0.15, 'DN', 'ftxt', 'start'); }
      // floor-level strip east of the treads
      R(xe, r.y, r.x + r.w - xe, r.h, 'furn-landing');
    }
    if (r.kind === 'elevator') {
      const cw = Math.min(r.w - 2.4, 4), ch = Math.min(r.h - 1.6, 5);
      const cx = r.x + (r.w - cw) / 2, cy = r.y + (r.h - ch) / 2;
      R(cx, cy, cw, ch, 'furn-cab', 2);
      L(cx, cy, cx + cw, cy + ch, 'furn-light'); L(cx, cy + ch, cx + cw, cy, 'furn-light');
      // door: on the side with a door, else west
      const d = (r.doors || [])[0];
      const side = d ? d.side : 'W';
      if (side === 'W') L(r.x + 0.2, cy + 0.5, r.x + 0.2, cy + ch - 0.5, 'leaf');
      if (side === 'E') L(r.x + r.w - 0.2, cy + 0.5, r.x + r.w - 0.2, cy + ch - 0.5, 'leaf');
      if (side === 'S') L(cx + 0.5, r.y + 0.2, cx + cw - 0.5, r.y + 0.2, 'leaf');
      if (side === 'N') L(cx + 0.5, r.y + r.h - 0.2, cx + cw - 0.5, r.y + r.h - 0.2, 'leaf');
    }
  }
  out.push(F.join('\n'));

  // ---- structural lines & columns
  (opts.lines || []).forEach((lx, i) => {
    out.push(`<line x1="${X(lx)}" y1="${Y(H) - 12}" x2="${X(lx)}" y2="${Y(0) + 12}" class="sline"/>`);
    out.push(`<text x="${X(lx)}" y="${Y(0) + 24}" text-anchor="middle" class="rl-dim">S${i + 1} · ${ftin(lx)}</text>`);
  });
  for (const c of (opts.columns || [])) out.push(`<rect x="${X(c[0] - 0.5)}" y="${Y(c[1] + 0.5)}" width="${S}" height="${S}" class="wall"/>`);

  // ---- room labels (top-left of each room, or key number)
  const keyed = [];
  rooms.forEach((r, i) => {
    const n = i + 1;
    const x = X(r.x) + 13, y = Y(r.y + r.h) + 20;
    const label = (r.label !== undefined) ? r.label : r.name;
    const dim = `${ftin(r.w)} × ${ftin(r.h)} · ${fmt(r.w * r.h)} sf`;
    const wpx = r.w * S, hpx = r.h * S;
    const est = label.length * 5.8;
    if (wpx >= est + 26 && hpx >= 40) {
      out.push(`<text x="${x}" y="${y}" class="rl-name">${esc(label)}</text>`);
      if (wpx >= dim.length * 5.2 + 26 && hpx >= 52) out.push(`<text x="${x}" y="${y + 11}" class="rl-dim">${dim}</text>`);
    } else if (hpx >= est + 26 && wpx >= 40) {
      out.push(`<text transform="translate(${X(r.x) + 20} ${Y(r.y) - 14}) rotate(-90)" class="rl-name">${esc(label)}</text>`);
      if (hpx >= dim.length * 5.2 + 26 && wpx >= 52) out.push(`<text transform="translate(${X(r.x) + 31} ${Y(r.y) - 14}) rotate(-90)" class="rl-dim">${dim}</text>`);
    } else {
      out.push(`<circle cx="${X(r.x + r.w / 2)}" cy="${Y(r.y + r.h / 2)}" r="7" class="keycirc"/><text x="${X(r.x + r.w / 2)}" y="${Y(r.y + r.h / 2) + 3.5}" text-anchor="middle" class="rl-key">${n}</text>`);
      keyed.push(n);
    }
    out.push(`<text x="${X(r.x + r.w) - 4}" y="${Y(r.y) - 4}" text-anchor="end" class="rl-tag">${n}</text>`);
  });

  // ---- dimension strings
  const dy = Y(H) - 26;
  out.push(`<line x1="${X(0)}" y1="${dy}" x2="${X(W)}" y2="${dy}" class="dim" marker-start="url(#ar-${level})" marker-end="url(#ar-${level})"/>`);
  out.push(`<text x="${X(W / 2)}" y="${dy - 5}" text-anchor="middle" class="rl-dim">${ftin(W)} overall (E–W)</text>`);
  const dx = X(0) - 26;
  out.push(`<line x1="${dx}" y1="${Y(H)}" x2="${dx}" y2="${Y(0)}" class="dim" marker-start="url(#ar-${level})" marker-end="url(#ar-${level})"/>`);
  out.push(`<text transform="translate(${dx - 6} ${Y(H / 2)}) rotate(-90)" text-anchor="middle" class="rl-dim">${ftin(H)} overall (N–S)</text>`);
  const xs = [...new Set(rooms.flatMap(r => [r.x, r.x + r.w]))].sort((a, b) => a - b);
  const by = Y(0) + 46;
  out.push(`<line x1="${X(0)}" y1="${by}" x2="${X(W)}" y2="${by}" class="dim"/>`);
  xs.forEach(x => out.push(`<line x1="${X(x)}" y1="${by - 4}" x2="${X(x)}" y2="${by + 4}" class="dim"/>`));
  for (let i = 0; i < xs.length - 1; i++) { const a = xs[i], b = xs[i + 1]; if (b - a >= 2) out.push(`<text x="${X((a + b) / 2)}" y="${by - 6}" text-anchor="middle" class="rl-chain">${ftin(b - a)}</text>`); }
  const ys = [...new Set(rooms.flatMap(r => [r.y, r.y + r.h]))].sort((a, b) => a - b);
  const rx = X(W) + 28;
  out.push(`<line x1="${rx}" y1="${Y(H)}" x2="${rx}" y2="${Y(0)}" class="dim"/>`);
  ys.forEach(y => out.push(`<line x1="${rx - 4}" y1="${Y(y)}" x2="${rx + 4}" y2="${Y(y)}" class="dim"/>`));
  for (let i = 0; i < ys.length - 1; i++) { const a = ys[i], b = ys[i + 1]; if (b - a >= 1.5) out.push(`<text transform="translate(${rx + 8} ${Y((a + b) / 2)}) rotate(90)" text-anchor="middle" class="rl-chain">${ftin(b - a)}</text>`); }
  out.push(`<text x="${X(W) + 8}" y="${Y(H) - 36}" text-anchor="end" class="rl-orient">ATLANTIC OCEAN · EAST →</text>`);
  out.push(`<text x="${X(0) - 8}" y="${Y(H) - 36}" text-anchor="start" class="rl-orient">← N SURF RD · CITY · WEST</text>`);
  const nx = vw - 34, ny = vh - 44;
  out.push(`<g><circle cx="${nx}" cy="${ny}" r="14" fill="none" stroke="currentColor" stroke-width="1"/><path d="M${nx},${ny - 11} L${nx + 5},${ny + 6} L${nx},${ny + 2} L${nx - 5},${ny + 6} z" fill="currentColor"/><text x="${nx}" y="${ny + 26}" text-anchor="middle" class="rl-dim">N</text></g>`);
  // scale bar
  out.push(`<line x1="${X(0)}" y1="${vh - 10}" x2="${X(10)}" y2="${vh - 10}" class="scalebar"/><text x="${X(10) + 6}" y="${vh - 7}" text-anchor="start" class="rl-dim">10 ft</text>`);
  out.push('</svg>');
  return { svg: out.join('\n'), keyed };
}

function levelTable(level, rooms) {
  const rows = rooms.map((r, i) => `<tr><td class="num">${i + 1}</td><td>${esc(r.name)}</td><td class="mono">${ftin(r.w)} × ${ftin(r.h)}</td><td class="mono num">${fmt(r.w * r.h)}</td><td class="note">${esc(r.notes || '')}</td></tr>`).join('\n');
  const t = tally(rooms);
  return `<div class="tablewrap"><table class="rooms"><thead><tr><th>#</th><th>Room</th><th>Gross dims</th><th class="num">Gross sf</th><th>Notes</th></tr></thead><tbody>${rows}</tbody><tfoot><tr><td></td><td colspan="2">Envelope total</td><td class="mono num">${fmt(t.total)}</td><td></td></tr></tfoot></table></div>`;
}

function build(design) {
  const meta = { ground: 'Ground / flood / garage level', L1: 'Residential Level 1', L2: 'Residential Level 2', L3: 'Residential Level 3 · Primary suite', roof: 'Rooftop amenity deck' };
  const outLevels = {};
  for (const l of design.levels) {
    const p = planSvg(l.level, l.rooms, { lines: design.structural_lines_x, columns: l.columns, open: l.open, aria: `${meta[l.level]} plan, 55 by 30 foot envelope, ocean to the east` });
    outLevels[l.level] = { title: meta[l.level], svg: p.svg, table: levelTable(l.level, l.rooms), tally: tally(l.rooms), keyed: p.keyed, rooms: l.rooms };
  }
  return outLevels;
}
module.exports = { build };
