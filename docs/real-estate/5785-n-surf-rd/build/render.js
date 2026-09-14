// Renders SVG floor plans + area schedule fragments from the validated design JSON.
// Single source of truth: every dimension in the drawings and tables comes from design.json.
const fs = require('fs');

const S = 12;              // px per foot for plans
const M = { l: 70, r: 70, t: 56, b: 56 };
const W = 55, H = 30;      // envelope ft
const NET_FACTOR = 0.88;   // net usable ≈ gross enclosed minus walls/shafts allowance

function ftin(v) {
  const f = Math.floor(v + 1e-9);
  const i = Math.round((v - f) * 12);
  return i ? `${f}'-${i}"` : `${f}'-0"`;
}
function fmt(n) { return Math.round(n).toLocaleString('en-US'); }
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

const KIND_LABEL = { stair: 'Stair', elevator: 'Elevator', lobby: 'Lobby', enclosed: 'Enclosed', outdoor: 'Open outdoor', covered_outdoor: 'Covered outdoor', pool: 'Pool', garage: 'Garage', storage: 'Storage', mechanical: 'Mechanical', void: 'Void' };
const CORE = new Set(['stair', 'elevator', 'lobby']);

function wrap(text, maxChars) {
  const words = text.split(/\s+/);
  const lines = []; let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > maxChars && cur) { lines.push(cur); cur = w; } else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  return lines;
}

function planSvg(level, rooms, opts) {
  const pw = W * S, ph = H * S;
  const vw = pw + M.l + M.r, vh = ph + M.t + M.b;
  const X = x => M.l + x * S;
  const Y = y => M.t + (H - y) * S; // y up = north
  const out = [];
  out.push(`<svg class="plan" viewBox="0 0 ${vw} ${vh}" role="img" aria-label="${esc(opts.aria)}" xmlns="http://www.w3.org/2000/svg">`);
  out.push(`<defs><marker id="arr-${level}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
  <pattern id="hatch-${level}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="currentColor" stroke-width="0.6" opacity="0.35"/></pattern>
  <pattern id="water-${level}" width="14" height="6" patternUnits="userSpaceOnUse"><path d="M0,3 q3.5,-3 7,0 t7,0" fill="none" stroke="currentColor" stroke-width="0.6" opacity="0.35"/></pattern></defs>`);
  // envelope
  out.push(`<rect x="${X(0)}" y="${Y(H)}" width="${pw}" height="${ph}" class="env" fill="none" stroke="currentColor" stroke-width="2.5"/>`);
  // rooms
  const keyed = [];
  rooms.forEach((r, idx) => {
    const x = X(r.x), y = Y(r.y + r.h), w = r.w * S, h = r.h * S;
    const cls = `k-${r.kind}`;
    out.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" class="room ${cls}" stroke="currentColor" stroke-width="1"/>`);
    if (r.kind === 'pool') out.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#water-${level})" stroke="none"/>`);
    if (r.kind === 'covered_outdoor') out.push(`<rect x="${x + 3}" y="${y + 3}" width="${Math.max(0, w - 6)}" height="${Math.max(0, h - 6)}" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="4 3" opacity="0.6"/>`);
    if (r.kind === 'void') out.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#hatch-${level})" stroke="none"/>`);
    const n = idx + 1;
    const cx = x + w / 2, cy = y + h / 2;
    const maxChars = Math.max(4, Math.floor((w - 8) / 5.6));
    const lines = wrap(r.name, maxChars);
    const dim = `${ftin(r.w)} × ${ftin(r.h)}`;
    const area = `${fmt(r.w * r.h)} sf`;
    const needed = (lines.length + 2) * 11;
    const rlines = wrap(r.name, Math.max(4, Math.floor((h - 8) / 5.6)));
    const rneeded = (rlines.length + 2) * 11;
    if (w >= 60 && h >= needed + 4 && lines.length <= 3) {
      const y0 = cy - needed / 2 + 9;
      lines.forEach((ln, i) => out.push(`<text x="${cx}" y="${y0 + i * 11}" text-anchor="middle" class="rl-name">${esc(ln)}</text>`));
      out.push(`<text x="${cx}" y="${y0 + lines.length * 11}" text-anchor="middle" class="rl-dim">${dim}</text>`);
      out.push(`<text x="${cx}" y="${y0 + (lines.length + 1) * 11}" text-anchor="middle" class="rl-dim">${area}</text>`);
    } else if (h >= 96 && w >= rneeded + 4 && rlines.length <= 3) {
      // tall narrow room: rotate the label 90° so it reads along the long side
      const x0 = cx - rneeded / 2 + 9;
      rlines.forEach((ln, i) => out.push(`<text transform="translate(${x0 + i * 11} ${cy}) rotate(-90)" text-anchor="middle" class="rl-name">${esc(ln)}</text>`));
      out.push(`<text transform="translate(${x0 + rlines.length * 11} ${cy}) rotate(-90)" text-anchor="middle" class="rl-dim">${dim}</text>`);
      out.push(`<text transform="translate(${x0 + (rlines.length + 1) * 11} ${cy}) rotate(-90)" text-anchor="middle" class="rl-dim">${area}</text>`);
    } else {
      out.push(`<text x="${cx}" y="${cy + 3.5}" text-anchor="middle" class="rl-key">${n}</text>`);
      keyed.push(n);
    }
    // number tag in corner for cross-reference with the table
    out.push(`<text x="${x + 3}" y="${y + 9}" class="rl-tag">${n}</text>`);
  });
  // structural lines
  (opts.lines || []).forEach((lx, i) => {
    out.push(`<line x1="${X(lx)}" y1="${Y(H) - 10}" x2="${X(lx)}" y2="${Y(0) + 10}" stroke="currentColor" stroke-width="1" stroke-dasharray="6 4" opacity="0.7"/>`);
    out.push(`<text x="${X(lx)}" y="${Y(0) + 22}" text-anchor="middle" class="rl-dim">S${i + 1} · ${ftin(lx)}</text>`);
  });
  // overall dimension strings
  const dy = Y(H) - 22;
  out.push(`<line x1="${X(0)}" y1="${dy}" x2="${X(W)}" y2="${dy}" stroke="currentColor" stroke-width="1" marker-start="url(#arr-${level})" marker-end="url(#arr-${level})"/>`);
  out.push(`<text x="${X(W / 2)}" y="${dy - 5}" text-anchor="middle" class="rl-dim">${ftin(W)} overall (E–W)</text>`);
  const dx = X(0) - 22;
  out.push(`<line x1="${dx}" y1="${Y(H)}" x2="${dx}" y2="${Y(0)}" stroke="currentColor" stroke-width="1" marker-start="url(#arr-${level})" marker-end="url(#arr-${level})"/>`);
  out.push(`<text transform="translate(${dx - 6} ${Y(H / 2)}) rotate(-90)" text-anchor="middle" class="rl-dim">${ftin(H)} overall (N–S)</text>`);
  // chained dims along the bottom (unique x edges)
  const xs = [...new Set(rooms.flatMap(r => [r.x, r.x + r.w]))].sort((a, b) => a - b);
  const by = Y(0) + 34 + ((opts.lines || []).length ? 10 : 0);
  out.push(`<line x1="${X(0)}" y1="${by}" x2="${X(W)}" y2="${by}" stroke="currentColor" stroke-width="0.8"/>`);
  xs.forEach(x => out.push(`<line x1="${X(x)}" y1="${by - 4}" x2="${X(x)}" y2="${by + 4}" stroke="currentColor" stroke-width="0.8"/>`));
  for (let i = 0; i < xs.length - 1; i++) { const a = xs[i], b = xs[i + 1]; if (b - a >= 2.5) out.push(`<text x="${X((a + b) / 2)}" y="${by - 6}" text-anchor="middle" class="rl-chain">${ftin(b - a)}</text>`); }
  // chained dims along the right (unique y edges)
  const ys = [...new Set(rooms.flatMap(r => [r.y, r.y + r.h]))].sort((a, b) => a - b);
  const rx = X(W) + 26;
  out.push(`<line x1="${rx}" y1="${Y(H)}" x2="${rx}" y2="${Y(0)}" stroke="currentColor" stroke-width="0.8"/>`);
  ys.forEach(y => out.push(`<line x1="${rx - 4}" y1="${Y(y)}" x2="${rx + 4}" y2="${Y(y)}" stroke="currentColor" stroke-width="0.8"/>`));
  for (let i = 0; i < ys.length - 1; i++) { const a = ys[i], b = ys[i + 1]; if (b - a >= 2) out.push(`<text transform="translate(${rx + 8} ${Y((a + b) / 2)}) rotate(90)" text-anchor="middle" class="rl-chain">${ftin(b - a)}</text>`); }
  // orientation labels
  out.push(`<text x="${X(W) + 8}" y="${Y(H) - 30}" text-anchor="end" class="rl-orient">ATLANTIC OCEAN · EAST →</text>`);
  out.push(`<text x="${X(0) - 8}" y="${Y(H) - 30}" text-anchor="start" class="rl-orient">← N SURF RD · CITY · WEST</text>`);
  // north arrow (points up = north)
  const nx = vw - 34, ny = vh - 40;
  out.push(`<g class="north"><circle cx="${nx}" cy="${ny}" r="14" fill="none" stroke="currentColor" stroke-width="1"/><path d="M${nx},${ny - 11} L${nx + 5},${ny + 6} L${nx},${ny + 2} L${nx - 5},${ny + 6} z" fill="currentColor"/><text x="${nx}" y="${ny + 26}" text-anchor="middle" class="rl-dim">N</text></g>`);
  out.push('</svg>');
  return { svg: out.join('\n'), keyed };
}

function levelTable(level, rooms) {
  const rows = rooms.map((r, i) => `<tr><td class="num">${i + 1}</td><td>${esc(r.name)}</td><td class="mono">${KIND_LABEL[r.kind]}</td><td class="mono">${ftin(r.w)} × ${ftin(r.h)}</td><td class="mono num">${fmt(r.w * r.h)}</td>${r.notes ? `<td class="note">${esc(r.notes)}</td>` : '<td class="note"></td>'}</tr>`).join('\n');
  const t = tally(rooms);
  return `<div class="tablewrap"><table class="rooms"><thead><tr><th>#</th><th>Room</th><th>Type</th><th>Gross dims</th><th class="num">Gross sf</th><th>Notes</th></tr></thead><tbody>${rows}</tbody>
<tfoot><tr><td></td><td colspan="3">Envelope total</td><td class="mono num">${fmt(t.total)}</td><td></td></tr></tfoot></table></div>`;
}

function tally(rooms) {
  const t = { total: 0, enclosed: 0, core: 0, outdoor: 0, covered: 0, pool: 0, garage: 0, storage: 0, mechanical: 0, void: 0, bath: 0, closet: 0, circulation: 0 };
  for (const r of rooms) {
    const a = r.w * r.h; t.total += a;
    if (CORE.has(r.kind)) t.core += a;
    else if (r.kind === 'enclosed') t.enclosed += a;
    else if (r.kind === 'outdoor') t.outdoor += a;
    else if (r.kind === 'covered_outdoor') t.covered += a;
    else if (r.kind === 'pool') t.pool += a;
    else if (r.kind === 'garage') t.garage += a;
    else if (r.kind === 'storage') t.storage += a;
    else if (r.kind === 'mechanical') t.mechanical += a;
    else if (r.kind === 'void') t.void += a;
    if (r.kind === 'enclosed' && /bath|shower|wc|powder|toilet/i.test(r.name)) t.bath += a;
    if (r.kind === 'enclosed' && /closet|wic|dress/i.test(r.name)) t.closet += a;
    if (r.kind === 'lobby' || (r.kind === 'enclosed' && /foyer|hall|corridor|gallery|passage|vestibule/i.test(r.name))) t.circulation += a;
  }
  return t;
}

function build(design) {
  const byLevel = {}; for (const l of design.levels) byLevel[l.level] = l.rooms;
  const meta = { ground: 'Ground / flood / garage level', L1: 'Residential Level 1', L2: 'Residential Level 2', L3: 'Residential Level 3 · Primary suite', roof: 'Rooftop amenity deck' };
  const outLevels = {};
  for (const L of ['ground', 'L1', 'L2', 'L3', 'roof']) {
    const rooms = byLevel[L];
    const p = planSvg(L, rooms, { lines: design.structural_lines_x, aria: `${meta[L]} plan, 55 by 30 foot envelope, ocean to the east` });
    outLevels[L] = { title: meta[L], svg: p.svg, table: levelTable(L, rooms), tally: tally(rooms), keyed: p.keyed, rooms };
  }
  return outLevels;
}

if (require.main === module) {
  const design = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const levels = build(design);
  fs.writeFileSync(process.argv[3], JSON.stringify({ levels, net_factor: NET_FACTOR }, null, 1));
  for (const [k, v] of Object.entries(levels)) console.log(k, JSON.stringify(v.tally));
}
module.exports = { build, ftin, fmt, esc, tally, NET_FACTOR };
