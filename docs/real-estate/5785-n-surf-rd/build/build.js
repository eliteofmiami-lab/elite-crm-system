// Assembles the final HTML page from design.json (geometry), content.js (verdict, findings, approvals) and the renderers.
const fs = require('fs');
const { ftin, fmt, esc, NET_FACTOR } = require('./render.js');
const { build } = require('./render2.js');
const { siteSvg, sectionSvg } = require('./site.js');
const C = require('./content.js');

const design = require('./plan.js');
const levels = build(design);
const L = levels;

function sheet(num, title, sub, body) {
  return `<section class="sheet" id="${num.toLowerCase()}">
  <header class="sheet-head"><span class="sheet-num">${num}</span><div><h2>${esc(title)}</h2>${sub ? `<p class="sheet-sub">${sub}</p>` : ''}</div><span class="stamp">${C.stamp}</span></header>
  ${body}
</section>`;
}
function planSheet(num, key, sub, notes) {
  const v = L[key];
  const t = v.tally;
  const chips = [
    ['Envelope', t.total], ['Enclosed', t.enclosed], ['Core (stair · elevator · lobby)', t.core], ['Open outdoor', t.outdoor], ['Covered outdoor', t.covered], ['Pool', t.pool], ['Garage', t.garage], ['Storage', t.storage], ['Mechanical', t.mechanical], ['Bathrooms', t.bath], ['Closets', t.closet], ['Circulation (lobby · foyer · halls)', t.circulation],
  ].filter(([, n]) => n > 0).map(([k, n]) => `<div class="chip"><span>${k}</span><b>${fmt(n)} sf</b></div>`).join('');
  const net = key === 'ground' ? null : Math.round(t.enclosed * NET_FACTOR);
  return sheet(num, v.title, sub, `
  <figure class="fig"><div class="figwrap">${v.svg}</div><figcaption>${esc(v.title)} · walls, doors, glazing and furniture drawn to scale inside the 30' × 55' envelope · exterior walls 9 in, interior 6 in · S1–S2 are the transverse structural lines that stack through every level · numbers key to the room table.</figcaption></figure>
  <div class="chips">${chips}${net !== null ? `<div class="chip net"><span>Net usable (enclosed × ${NET_FACTOR})</span><b>≈ ${fmt(net)} sf</b></div>` : ''}</div>
  ${notes ? `<div class="notes">${notes}</div>` : ''}
  ${v.table}`);
}

// ---------- area schedule ----------
const sched = (() => {
  const g = L.ground.tally, l1 = L.L1.tally, l2 = L.L2.tally, l3 = L.L3.tally, r = L.roof.tally;
  const rows = [
    ['Ground garage / access (garage + storage + mechanical + core)', g.garage + g.storage + g.mechanical + g.core],
    ['Level 1 enclosed (incl. core)', l1.enclosed + l1.core],
    ['Level 1 outdoor', l1.outdoor + l1.covered],
    ['Level 2 enclosed (incl. core)', l2.enclosed + l2.core],
    ['Level 2 outdoor', l2.outdoor + l2.covered],
    ['Level 3 enclosed (incl. core)', l3.enclosed + l3.core],
    ['Level 3 outdoor', l3.outdoor + l3.covered],
    ['Rooftop open deck (walkways, lounges, fire pit)', r.outdoor],
    ['Rooftop pool (water surface incl. shelf and swim-up zone)', r.pool],
    ['Rooftop covered — Option B as drawn (gourmet canopy)', r.covered],
    ['Rooftop covered — Option A subset (code-conservative)', design.rooftop_option_A_sf],
    ['Rooftop enclosed (bath + core at roof)', r.enclosed + r.core],
  ];
  const totals = [
    ['Total enclosed residential (L1 + L2 + L3, incl. core)', l1.enclosed + l1.core + l2.enclosed + l2.core + l3.enclosed + l3.core],
    ['Total garage / access', g.garage + g.storage + g.mechanical + g.core],
    ['Total covered rooftop (Option B)', r.covered],
    ['Total outdoor amenity (balconies + roof deck + pool)', l1.outdoor + l2.outdoor + l3.outdoor + r.outdoor + r.pool],
    ['Total under roof, all levels incl. rooftop enclosures (gross)', g.total + l1.enclosed + l1.core + l2.enclosed + l2.core + l3.enclosed + l3.core + r.enclosed + r.core + r.covered],
  ];
  const tr = ([k, v]) => `<tr><td>${k}</td><td class="mono num">${fmt(v)}</td></tr>`;
  return `<div class="tablewrap"><table class="sched"><thead><tr><th>Item</th><th class="num">sf</th></tr></thead><tbody>${rows.map(tr).join('')}</tbody><tfoot>${totals.map(tr).join('')}</tfoot></table></div>
  <p class="fine">Gross figures are wall-centerline areas taken directly from the plan rectangles (the same numbers printed on each sheet). Net usable is estimated at ${NET_FACTOR * 100}% of enclosed gross to allow for walls, shafts and chases; the architect of record will replace it with measured net. Nothing outside the 30' × 55' envelope is counted.</p>`;
})();

// ---------- approvals matrix ----------
const matrix = `<div class="tablewrap"><table class="matrix"><thead><tr><th>Design element</th><th>Requires</th><th>Status</th><th>Why / what to confirm</th></tr></thead><tbody>
${C.approvals.map(a => `<tr><td>${esc(a.element)}</td><td>${a.requires.map(r => `<span class="req req-${r}">${C.reqLabel[r]}</span>`).join(' ')}</td><td><span class="st st-${a.status}">${C.statusLabel[a.status]}</span></td><td>${a.why}</td></tr>`).join('\n')}
</tbody></table></div>`;

const digest = JSON.parse(fs.readFileSync('digest.json', 'utf8'));
const EV = { code_snippet: 'Code snippet', city_staff_report_snippet: 'Staff-report snippet', state_rule: 'State rule (full text)', federal: 'Federal', county_record: 'County record', listing: 'Listing', secondary: 'Secondary', none: 'Not obtained' };
const ST = { verified: 'Verified', partially_verified: 'Partially verified', refuted: 'Refuted', unverifiable: 'Unverifiable' };
const register = `<div class="tablewrap"><table class="matrix reg"><thead><tr><th>Topic</th><th>Finding</th><th>Status</th><th>Evidence</th><th>Effect on the drawings</th></tr></thead><tbody>
${digest.facts.map(f => `<tr><td class="mono">${esc(f.topic)}</td><td>${esc(f.statement)}${f.corrected_statement ? `<div class="fine">Adversarial pass: ${esc(f.corrected_statement)}</div>` : ''}${f.quote ? `<div class="fine">“${esc(f.quote)}”</div>` : ''}<div class="fine"><a href="${esc(f.source_url)}">${esc(f.source_url.replace(/^https?:\/\//, '').slice(0, 60))}…</a></div></td><td><span class="st st-${f.status === 'verified' ? 'byright' : f.status === 'partially_verified' ? 'confirm' : f.status === 'refuted' ? 'risk' : 'variance'}">${ST[f.status] || f.status}</span></td><td class="note">${EV[f.evidence_level] || f.evidence_level}</td><td class="note">${esc(f.design_effect)}</td></tr>`).join('\n')}
</tbody></table></div>
<h3>Open questions, most consequential first</h3><ol>${digest.open_questions_ranked.map(q => `<li>${esc(q)}</li>`).join('')}</ol>
<h3>Contradictions between sources</h3><ul>${digest.contradictions.map(q => `<li>${esc(q)}</li>`).join('')}</ul>`;
const css = fs.readFileSync('page.css', 'utf8');
const html = `<title>Surf Road 5785</title>
<meta name="description" content="Conceptual floor-plan study and feasibility check for a new oceanfront residence at 5785 N Surf Rd, Hollywood FL">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>${css}</style>
<div class="wrap">
<header class="titleblock">
  <div class="tb-main">
    <p class="eyebrow">Conceptual floor-plan study · feasibility check</p>
    <h1>5785 N Surf Road</h1>
    <p class="lede">New oceanfront single-family residence · Hollywood, Florida 33019 · Broward County · Parcel 514201027042 · Zoning NBDD-CZ</p>
  </div>
  <dl class="tb-meta">
    <div><dt>Issue</dt><dd>${C.issueDate}</dd></div>
    <div><dt>Status</dt><dd>${C.stamp}</dd></div>
    <div><dt>Lot (MLS)</dt><dd>40' × 80' · 3,146 sf</dd></div>
    <div><dt>Envelope</dt><dd>30' × 55' · 1,650 sf/level</dd></div>
    <div><dt>Orientation</dt><dd>West = N Surf Rd · East = Atlantic</dd></div>
  </dl>
</header>
<nav class="index" aria-label="Sheet index">
  ${C.sheets.map(s => `<a href="#${s[0].toLowerCase()}"><span class="sheet-num">${s[0]}</span>${s[1]}</a>`).join('')}
</nav>
<main>
${sheet('A-000', 'Feasibility verdict', 'What is real, what needs a variance, what could stop the project', C.verdict)}
${sheet('A-001', 'Site plan', 'Lot 40\' × 80\' · target envelope vs by-right envelope', `<figure class="fig"><div class="figwrap">${siteSvg({ entryStair: design.site_entry_stair })}</div><figcaption>Site plan. Solid box: 30' × 55' target envelope assuming variances (front 20', sides 5', rear 5'). Dashed box: 25' × 40' by-right envelope (front 25', sides 7'-6", rear 15'). Hatched strip: grade sun deck, extent subject to City setback, FDEP CCCL and flood rules.</figcaption></figure>${C.siteNotes}`)}
${sheet('A-002', 'Height section', 'Three residential stories over parking inside 33 ft — datum scenarios', C.sectionIntro + C.sections.map(s => `<figure class="fig section-fig"><div class="figwrap">${sectionSvg(s)}</div><figcaption>${esc(s.caption)}</figcaption></figure>`).join('') + C.sectionNotes)}
${planSheet('A-101', 'ground', 'Flood / garage level · parking, access, one storage room · nothing habitable', C.levelNotes.ground)}
${planSheet('A-102', 'L1', 'Living · dining · kitchen · powder · guest suite / home office', C.levelNotes.L1)}
${planSheet('A-103', 'L2', 'Family lounge with mini bar · one ocean suite · two city suites', C.levelNotes.L2)}
${planSheet('A-104', 'L3', 'Full-floor primary suite · bed and shower on the ocean', C.levelNotes.L3)}
${planSheet('A-105', 'roof', 'Infinity pool east · covered gourmet and swim-up bar center · fire pit lounge west', C.levelNotes.roof)}
${sheet('A-201', 'Area schedule', 'All figures derive from the plan rectangles on sheets A-101 to A-105', sched)}
${sheet('A-301', 'Approvals matrix', 'Every element that needs a variance, a confirmation or an agency approval', matrix)}
${sheet('A-401', 'Sources and method', 'Primary sources checked, and what an adversarial re-check changed', C.sources)}
${sheet('A-402', 'Findings register', '26 facts from the verification, each with status, evidence level and source', register)}
</main>
<footer class="foot"><p>${C.footer}</p></footer>
</div>`;
fs.writeFileSync(process.argv[3] || 'index.html', html);
console.log('built', html.length, 'bytes');
