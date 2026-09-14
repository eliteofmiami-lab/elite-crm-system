// Site plan (lot 40 x 80) and vertical section generators.
const { ftin, esc } = require('./render.js');
const S = 8; // px/ft
function siteSvg(opts) {
  const M = { l: 90, r: 90, t: 70, b: 60 };
  const LW = 80, LH = 40; // lot: 80 deep (E-W), 40 wide (N-S)
  const X = x => M.l + x * S, Y = y => M.t + (LH - y) * S;
  const vw = LW * S + M.l + M.r, vh = LH * S + M.t + M.b;
  const o = [];
  o.push(`<svg class="plan site" viewBox="0 0 ${vw} ${vh}" role="img" aria-label="Site plan: 40 by 80 foot lot, target 30 by 55 building envelope assuming variances, by-right 25 by 40 envelope dashed, driveway west, ocean east" xmlns="http://www.w3.org/2000/svg">`);
  o.push(`<defs><marker id="arr-site" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
  <pattern id="hatch-site" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="currentColor" stroke-width="0.7" opacity="0.35"/></pattern>
  <pattern id="sand" width="10" height="10" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="0.8" fill="currentColor" opacity="0.35"/><circle cx="7" cy="6" r="0.8" fill="currentColor" opacity="0.35"/></pattern></defs>`);
  // context: road west, beach east
  o.push(`<rect x="${X(-11)}" y="${Y(LH) - 20}" width="${6 * S}" height="${LH * S + 40}" class="k-road" stroke="none"/>`);
  o.push(`<text transform="translate(${X(-8)} ${Y(LH / 2)}) rotate(-90)" text-anchor="middle" class="rl-orient">N SURF RD · WEST</text>`);
  o.push(`<rect x="${X(LW)}" y="${Y(LH) - 20}" width="${10 * S}" height="${LH * S + 40}" fill="url(#sand)" stroke="none"/>`);
  o.push(`<text transform="translate(${X(LW + 5)} ${Y(LH / 2)}) rotate(90)" text-anchor="middle" class="rl-orient">BEACH · ATLANTIC · EAST</text>`);
  // lot
  o.push(`<rect x="${X(0)}" y="${Y(LH)}" width="${LW * S}" height="${LH * S}" fill="none" stroke="currentColor" stroke-width="2.5"/>`);
  // driveway zone 0..20
  o.push(`<rect x="${X(0)}" y="${Y(LH)}" width="${20 * S}" height="${LH * S}" class="k-drive" stroke="currentColor" stroke-width="0.8" stroke-dasharray="3 3"/>`);
  o.push(`<text x="${X(10)}" y="${Y(12)}" text-anchor="middle" class="rl-name">Driveway / apron</text>`);
  o.push(`<text x="${X(10)}" y="${Y(12) + 12}" text-anchor="middle" class="rl-dim">20'-0" front zone</text>`);
  o.push(`<text x="${X(10)}" y="${Y(12) + 24}" text-anchor="middle" class="rl-dim">(by-right setback 25'-0")</text>`);
  // front entry stair (site element)
  const st = opts.entryStair || { x: 12, y: 5, w: 8, h: 4 };
  o.push(`<rect x="${X(st.x)}" y="${Y(st.y + st.h)}" width="${st.w * S}" height="${st.h * S}" class="k-stair" stroke="currentColor" stroke-width="1"/>`);
  for (let i = 1; i < st.w; i += 1) o.push(`<line x1="${X(st.x + i)}" y1="${Y(st.y + st.h)}" x2="${X(st.x + i)}" y2="${Y(st.y)}" stroke="currentColor" stroke-width="0.6"/>`);
  o.push(`<text x="${X(st.x)}" y="${Y(st.y + st.h) - 5}" text-anchor="start" class="rl-dim">Entry stair ${ftin(st.w)}×${ftin(st.h)}</text>`);
  // target envelope 30x55 at x 20..75, y 5..35
  o.push(`<rect x="${X(20)}" y="${Y(35)}" width="${55 * S}" height="${30 * S}" class="k-enclosed" stroke="currentColor" stroke-width="2"/>`);
  o.push(`<text x="${X(47.5)}" y="${Y(20) - 18}" text-anchor="middle" class="rl-name">TARGET ENVELOPE 30' × 55' = 1,650 sf</text>`);
  o.push(`<text x="${X(47.5)}" y="${Y(20) - 5}" text-anchor="middle" class="rl-dim">SUBJECT TO VARIANCE · front 20' · sides 5' · rear 5'</text>`);
  // by-right envelope 25x40 at x 25..65, y 7.5..32.5
  o.push(`<rect x="${X(25)}" y="${Y(32.5)}" width="${40 * S}" height="${25 * S}" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="7 4"/>`);
  o.push(`<text x="${X(45)}" y="${Y(20) + 12}" text-anchor="middle" class="rl-dim">by-right envelope 25' × 40' = 1,000 sf (dashed)</text>`);
  o.push(`<text x="${X(45)}" y="${Y(20) + 24}" text-anchor="middle" class="rl-dim">setbacks 25' / 7.5' / 7.5' / 15'</text>`);
  // sun deck east 75..80 (hatched, subject to approvals)
  o.push(`<rect x="${X(75)}" y="${Y(35)}" width="${5 * S}" height="${30 * S}" fill="url(#hatch-site)" stroke="currentColor" stroke-width="0.8" stroke-dasharray="3 3"/>`);
  o.push(`<text transform="translate(${X(77.5)} ${Y(20)}) rotate(90)" text-anchor="middle" class="rl-dim">Grade sun deck · extent subject to City / FDEP / flood</text>`);
  // side setbacks labels
  o.push(`<text x="${X(47.5)}" y="${Y(37.5) + 3}" text-anchor="middle" class="rl-dim">5'-0" north side (by-right 7'-6")</text>`);
  o.push(`<text x="${X(47.5)}" y="${Y(2.5) + 3}" text-anchor="middle" class="rl-dim">5'-0" south side (by-right 7'-6")</text>`);
  // dims
  const dy = Y(LH) - 24;
  o.push(`<line x1="${X(0)}" y1="${dy}" x2="${X(LW)}" y2="${dy}" stroke="currentColor" stroke-width="1" marker-start="url(#arr-site)" marker-end="url(#arr-site)"/>`);
  o.push(`<text x="${X(LW / 2)}" y="${dy - 5}" text-anchor="middle" class="rl-dim">80'-0" lot depth (MLS) · 3,146 sf reported ⇒ verify by survey</text>`);
  const dx = X(0) - 26;
  o.push(`<line x1="${dx}" y1="${Y(LH)}" x2="${dx}" y2="${Y(0)}" stroke="currentColor" stroke-width="1" marker-start="url(#arr-site)" marker-end="url(#arr-site)"/>`);
  o.push(`<text transform="translate(${dx - 6} ${Y(LH / 2)}) rotate(-90)" text-anchor="middle" class="rl-dim">40'-0" lot width</text>`);
  // chain along bottom
  const by = Y(0) + 26;
  const xs = [0, 20, 25, 65, 75, 80];
  o.push(`<line x1="${X(0)}" y1="${by}" x2="${X(LW)}" y2="${by}" stroke="currentColor" stroke-width="0.8"/>`);
  xs.forEach(x => o.push(`<line x1="${X(x)}" y1="${by - 4}" x2="${X(x)}" y2="${by + 4}" stroke="currentColor" stroke-width="0.8"/>`));
  for (let i = 0; i < xs.length - 1; i++) o.push(`<text x="${X((xs[i] + xs[i + 1]) / 2)}" y="${by - 6}" text-anchor="middle" class="rl-chain">${ftin(xs[i + 1] - xs[i])}</text>`);
  // north arrow
  const nx = vw - 40, ny = 40;
  o.push(`<g><circle cx="${nx}" cy="${ny}" r="14" fill="none" stroke="currentColor" stroke-width="1"/><path d="M${nx},${ny - 11} L${nx + 5},${ny + 6} L${nx},${ny + 2} L${nx - 5},${ny + 6} z" fill="currentColor"/><text x="${nx}" y="${ny + 26}" text-anchor="middle" class="rl-dim">N</text></g>`);
  o.push('</svg>');
  return o.join('\n');
}

// Vertical section: stack of levels with heights, drawn to scale (S px/ft), two datum scenarios side by side.
function sectionSvg(sc) {
  // sc: { title, grade, datum, datumLabel, levels: [{name, ff, clear, structure}], roofDeck, parapet, poolTop, bulkheadTop, limit33 }
  const S = 7;
  const M = { l: 110, r: 30, t: 40, b: 30 };
  const base = Math.min(sc.grade, sc.datum) - 2; // ft NAVD or relative
  const top = Math.max(sc.bulkheadTop, sc.limit33 + 3) + 2;
  const H = (top - base) * S;
  const vw = 520, vh = H + M.t + M.b;
  const Y = e => M.t + (top - e) * S;
  const x0 = M.l + 40, w = 300;
  const o = [];
  o.push(`<svg class="plan section" viewBox="0 0 ${vw} ${vh}" role="img" aria-label="${esc(sc.aria)}" xmlns="http://www.w3.org/2000/svg">`);
  // ground / sand
  o.push(`<rect x="${M.l}" y="${Y(sc.grade)}" width="${vw - M.l - M.r}" height="${Y(base) - Y(sc.grade)}" class="k-road" stroke="none"/>`);
  o.push(`<text x="${M.l - 88}" y="${Y(sc.grade) + 12}" class="rl-dim">grade ≈ ${sc.grade > 0 ? '+' : ''}${sc.grade} ft</text>`);
  o.push(`<text x="${M.l - 88}" y="${Y(sc.grade) + 23}" class="rl-dim">${esc(sc.unit)}</text>`);
  // datum line
  o.push(`<line x1="${M.l - 90}" y1="${Y(sc.datum)}" x2="${x0 + w + 12}" y2="${Y(sc.datum)}" stroke="currentColor" stroke-width="1" stroke-dasharray="5 3"/>`);
  o.push(`<text x="${M.l - 88}" y="${Y(sc.datum) - 4}" class="rl-dim">${esc(sc.datumLabel)}</text>`);
  // 33 ft limit
  o.push(`<line x1="${M.l - 90}" y1="${Y(sc.limit33)}" x2="${x0 + w + 12}" y2="${Y(sc.limit33)}" stroke="currentColor" stroke-width="1.4"/>`);
  o.push(`<text x="${M.l - 88}" y="${Y(sc.limit33) - 4}" class="rl-name">33'-0" limit</text>`);
  o.push(`<text x="${M.l - 88}" y="${Y(sc.limit33) + 11}" class="rl-dim">${esc(sc.limitNote)}</text>`);
  // piles / columns
  for (const px of [x0 + 20, x0 + w / 2, x0 + w - 20]) o.push(`<rect x="${px - 4}" y="${Y(sc.levels[0].ff)}" width="8" height="${Y(base) - Y(sc.levels[0].ff)}" class="k-stair" stroke="currentColor" stroke-width="0.8"/>`);
  o.push(`<text x="${x0 + w / 2}" y="${Y(sc.grade) - 6}" text-anchor="middle" class="rl-dim">${esc(sc.groundLabel)}</text>`);
  // levels
  sc.levels.forEach((L, i) => {
    const next = sc.levels[i + 1];
    const topE = next ? next.ff : sc.roofDeck;
    const fl = L.structure; // slab depth ft
    o.push(`<rect x="${x0}" y="${Y(L.ff)}" width="${w}" height="${fl * S}" fill="currentColor" opacity="0.85"/>`);
    o.push(`<rect x="${x0}" y="${Y(topE)}" width="${w}" height="${Y(L.ff) - Y(topE)}" class="${L.cls || 'k-enclosed'}" stroke="currentColor" stroke-width="0.8"/>`);
    o.push(`<text x="${x0 + 8}" y="${Y(L.ff) - 6}" class="rl-name">${esc(L.name)}</text>`);
    const ffTxt = L.cls === 'k-garage' ? `clear ≈ ${ftin(topE - L.ff - L.structure)} under beams` : `FF ${L.ff > 0 ? '+' : ''}${L.ff.toFixed(1)} · f-to-f ${ftin(topE - L.ff)} · clear ≈ ${ftin(topE - L.ff - L.structure)}`;
    o.push(`<text x="${x0 + w - 8}" y="${Y(L.ff) - 6}" text-anchor="end" class="rl-dim">${ffTxt}</text>`);
  });
  // roof deck slab
  o.push(`<rect x="${x0}" y="${Y(sc.roofDeck)}" width="${w}" height="${0.9 * S}" fill="currentColor" opacity="0.85"/>`);
  o.push(`<text x="${x0 + w - 8}" y="${Y(sc.roofDeck) + 0.9 * S + 12}" text-anchor="end" class="rl-name">Roof deck ${sc.roofDeck > 0 ? '+' : ''}${sc.roofDeck.toFixed(1)}</text>`);
  // parapet, pool, bulkhead
  o.push(`<rect x="${x0}" y="${Y(sc.parapet)}" width="6" height="${Y(sc.roofDeck) - Y(sc.parapet)}" fill="currentColor" opacity="0.6"/>`);
  o.push(`<rect x="${x0 + w - 100}" y="${Y(sc.poolTop)}" width="90" height="${Y(sc.roofDeck) - Y(sc.poolTop)}" class="k-pool" stroke="currentColor" stroke-width="0.8"/>`);
  o.push(`<text x="${x0 + w - 55}" y="${Y(sc.poolTop) - 4}" text-anchor="middle" class="rl-dim">pool shell top ${sc.poolTop > 0 ? '+' : ''}${sc.poolTop.toFixed(1)}</text>`);
  o.push(`<rect x="${x0 + 12}" y="${Y(sc.bulkheadTop)}" width="64" height="${Y(sc.roofDeck) - Y(sc.bulkheadTop)}" class="k-elevator" stroke="currentColor" stroke-width="0.8"/>`);
  o.push(`<text x="${x0 + 44}" y="${Y(sc.bulkheadTop) - 4}" text-anchor="middle" class="rl-dim">elevator bulkhead ${sc.bulkheadTop > 0 ? '+' : ''}${sc.bulkheadTop.toFixed(1)}</text>`);
  o.push(`<rect x="${x0 + 96}" y="${Y(sc.canopyTop)}" width="88" height="${Y(sc.roofDeck) - Y(sc.canopyTop)}" class="k-covered_outdoor" stroke="currentColor" stroke-width="0.8"/>`);
  o.push(`<text x="${x0 + 140}" y="${Y(sc.canopyTop) - 4}" text-anchor="middle" class="rl-dim">gourmet canopy ${sc.canopyTop > 0 ? '+' : ''}${sc.canopyTop.toFixed(1)}</text>`);
  // scale bar
  o.push(`<line x1="${vw - M.r - 8}" y1="${Y(base + 1)}" x2="${vw - M.r - 8}" y2="${Y(base + 11)}" stroke="currentColor" stroke-width="2"/><text transform="translate(${vw - M.r - 12} ${Y(base + 6)}) rotate(-90)" text-anchor="middle" class="rl-dim">10 ft</text>`);
  o.push(`<text x="${vw / 2}" y="${M.t - 22}" text-anchor="middle" class="rl-name">${esc(sc.title)}</text>`);
  o.push('</svg>');
  return o.join('\n');
}
module.exports = { siteSvg, sectionSvg };
