// Editorial content for the drawing set. Preliminary issue: regulatory verification still running.
const issueDate = '14 Sep 2026 · Preliminary issue P1';
const stamp = 'Conceptual · assumes setback variances · not for construction';

const sheets = [
  ['A-000', 'Feasibility verdict'], ['A-001', 'Site plan'], ['A-002', 'Height section'],
  ['A-101', 'Ground / garage'], ['A-102', 'Level 1'], ['A-103', 'Level 2'], ['A-104', 'Level 3 · primary'], ['A-105', 'Rooftop'],
  ['A-201', 'Area schedule'], ['A-301', 'Approvals matrix'], ['A-401', 'Sources'],
];

const verdict = `
<div class="callout"><p><b>Resumo em português.</b> As plantas abaixo cabem no envelope-alvo de 30' × 55' com o núcleo de escada/elevador fixo em todos os pavimentos e passam na validação geométrica automática (sem sobreposições, 1.650 sf exatos por nível, mínimos de escada, elevador, quartos e banheiros). O que ainda não está resolvido não é a planta: é a <b>altura</b>. Com a garagem embaixo da casa exigida pela zona de inundação, três pavimentos residenciais mais o roof deck ficam a cerca de 42 ft acima do nível da rua. Se Hollywood medir os 33 ft a partir do terreno (a definição encontrada até agora diz "established grade of the plot"), o programa pedido não cabe e precisaria de variance de altura e de número de pavimentos, muito mais difícil que a variance de recuo. Se a Cidade medir a partir do primeiro piso habitável ou da cota de inundação, cabe com folga pequena. Essa é a primeira pergunta a levar ao Planning Department. As demais confirmações (setbacks do §4.2(E), precedente 5405, CCCL, FEMA) estão em verificação e entram na próxima emissão.</p></div>
<div class="verdict-grid">
  <div class="vcard warn"><h3>Envelope 30' × 55'</h3><p>Not by right. Needs four setback variances: front 25'→20', both sides 7'-6"→5', rear 15'→5'. The plan is drawn to this envelope and labeled accordingly.</p></div>
  <div class="vcard bad"><h3>Height and story count</h3><p>Garage + three residential floors + roof deck reaches ≈42' above grade with 8' parking clearance and 10–10'-6" ceilings. Fits 33' only if the City measures from the first habitable floor or a flood datum. Unconfirmed; treat as the project's main risk.</p></div>
  <div class="vcard ok"><h3>Floor-plan geometry</h3><p>All five levels tile the envelope exactly; core identical on every level; two structural lines (x = 26', x = 40') plus the east face stack from roof to foundation and bound the pool.</p></div>
  <div class="vcard warn"><h3>Rooftop covered area</h3><p>Option A (126 sf, 7.6% of ground floor) sits under the reported 10% scenery-loft allowance. Option B as drawn (266 sf, 16.1%) requires a rooftop-coverage variance; 5405 N Surf Rd obtained a larger one in July 2024 (snippet-level evidence, to be confirmed).</p></div>
  <div class="vcard info"><h3>Rooftop pool</h3><p>≈360 sf of water, ≈72,000 lb of water (≈36 t), ≈135,000 lb with the concrete shell, ≈375 psf over the pool area. Sits between structural lines x = 40' and the east face; needs structural, FDEP (pools are outside the CCCL general permit) and height-projection review.</p></div>
  <div class="vcard info"><h3>Ground level</h3><p>Parking, access, one storage room, elevated mechanical only. No bathroom, no habitable room. If the lot is in a VE zone: pile foundation, breakaway enclosures, elevator per FEMA TB-4.</p></div>
  <div class="vcard warn"><h3>Lot area 3,146 sf vs 5,800 sf minimum</h3><p>Buildability depends on the "or as platted" / lot-of-record clause. Get it confirmed in writing before design spend.</p></div>
  <div class="vcard info"><h3>Coastal jurisdiction</h3><p>A lot east of N Surf Rd is expected to be entirely seaward of the CCCL: FDEP permit, 30-year erosion projection, turtle lighting, and pool rules apply. Exact CCCL position must come from FDEP Map Direct / survey.</p></div>
</div>
<h3>What this issue is and is not</h3>
<ul>
  <li><b>Is:</b> a dimensioned conceptual plan set that satisfies the owner's program inside the target envelope, with every number on the drawings generated from one geometry file, so plans and the area schedule cannot disagree.</li>
  <li><b>Is not:</b> a code determination. The regulatory verification workflow is still running, and this session's network policy blocks the primary code sites (amlegal.com for the Hollywood ZLDR, Legistar, FDEP, FEMA, the property appraiser). Claims below are marked by evidence level; the next issue replaces this section with the verified findings.</li>
</ul>
<h3>Decisions the drawings already make</h3>
<ul>
  <li><b>Core on the north side</b> (x 8'–32': stair, lobby-landing, glass elevator), keeping the full 30' ocean face free on every level. The glass elevator looks east through the interior on L1–L3 and directly at the ocean at the roof stop.</li>
  <li><b>Balconies carved from the envelope</b>: the L1 ocean terrace is 5' × 30' inside the 30' × 55' box. No projections beyond the box are assumed on any level.</li>
  <li><b>Pool recessed 2'-6" into the Level 3 ceiling zone</b> under the master bed and bath (ceiling there drops to ≈8'-6"), so the coping sits ≈2'-6" above the deck instead of 5'. The fully raised alternative with a grand stair is possible but adds height to the projection review.</li>
  <li><b>Level 3 west side</b> is drawn as a private gym and a sauna/steam spa. It is optional program and can become a sunset terrace or a second dressing room without touching the core.</li>
</ul>`;

const siteNotes = `<ul>
  <li>Lot depth is taken as 80' for concept only; 3,146 sf ÷ 40' = 78.65', so the east line is probably shorter or irregular (erosion control line). A boundary and topographic survey governs.</li>
  <li>The 20' front zone holds the driveway apron for the two garage doors and the exterior entry stair to Level 1 (drawn 12' × 6'). Open stairs are normally an allowed projection; confirm under §4.23 and confirm the driveway width the City accepts.</li>
  <li>The grade sun deck east of the house is shown only as a hatched strip. Its extent depends on the rear setback, the CCCL and flood rules; it must not be assumed to reach the property line.</li>
</ul>`;

const sectionIntro = `<p>Two questions decide whether three residential stories fit: how high the first floor must sit, and where the City starts measuring the 33'. The first is largely physics. A car needs 7'-0" of clear height by code and 8'-0" for comfort; with 1'-6" of floor structure, Level 1 lands about 9'-6" above the driveway regardless of the flood map, which is above the FBC minimum for a VE zone (bottom of lowest horizontal member at BFE + 1'). The second is the open item. Elevations below use an assumed grade of +5.5 ft NAVD88 and an assumed BFE of +10 ft NAVD88; both must be replaced by survey and FIRM values.</p>`;

const sections = [
  {
    title: 'Scenario 1 · program as requested (3 residential + roof)', aria: 'Section, three residential stories over parking; roof deck about 42 feet above grade',
    unit: 'NAVD88 (assumed)', grade: 5.5, datum: 10.0, datumLabel: 'BFE +10.0 (assumed)', limit33: 38.5, limitNote: 'from grade → +38.5', groundLabel: 'Parking · 8\'-0" clear · breakaway walls',
    levels: [
      { name: 'Ground · parking', ff: 5.5, structure: 1.5, cls: 'k-garage' },
      { name: 'Level 1', ff: 15.0, structure: 1.0 },
      { name: 'Level 2', ff: 26.0, structure: 1.0 },
      { name: 'Level 3', ff: 36.5, structure: 1.0 },
    ],
    roofDeck: 47.5, parapet: 51.0, poolTop: 50.0, bulkheadTop: 59.5, canopyTop: 57.5,
    caption: 'Scenario 1: as requested. Roof deck at +47.5 = 42\'-0" above grade, 37\'-6" above BFE, 32\'-6" above the Level 1 floor. Passes 33\' only against a first-floor / DFE datum.',
  },
  {
    title: 'Scenario 2 · by-right fallback (2 residential + roof)', aria: 'Section, two residential stories over parking; roof deck 32 feet above grade',
    unit: 'NAVD88 (assumed)', grade: 5.5, datum: 10.0, datumLabel: 'BFE +10.0 (assumed)', limit33: 38.5, limitNote: 'from grade → +38.5', groundLabel: 'Parking · 8\'-0" clear · breakaway walls',
    levels: [
      { name: 'Ground · parking', ff: 5.5, structure: 1.5, cls: 'k-garage' },
      { name: 'Level 1', ff: 15.0, structure: 1.0 },
      { name: 'Level 2', ff: 26.5, structure: 1.0 },
    ],
    roofDeck: 37.5, parapet: 41.0, poolTop: 40.0, bulkheadTop: 49.5, canopyTop: 47.5,
    caption: 'Scenario 2: two residential stories with 10\'-6" and 10\'-0" clear ceilings. Roof deck at +37.5 = 32\'-0" above grade; fits the 33\' limit measured from grade with 1\' to spare. Rooftop projections still need review.',
  },
];

const sectionNotes = `<h3>Arithmetic behind the sections</h3>
<div class="tablewrap"><table class="sched"><thead><tr><th>Item</th><th class="num">Scenario 1</th><th class="num">Scenario 2</th></tr></thead><tbody>
<tr><td>Grade / driveway (assumed)</td><td class="mono num">+5.5</td><td class="mono num">+5.5</td></tr>
<tr><td>Parking clear height + floor structure</td><td class="mono num">8.0 + 1.5</td><td class="mono num">8.0 + 1.5</td></tr>
<tr><td>Level 1 finished floor</td><td class="mono num">+15.0</td><td class="mono num">+15.0</td></tr>
<tr><td>Floor-to-floor L1 / L2 / L3</td><td class="mono num">11.0 / 10.5 / 11.0</td><td class="mono num">11.5 / 11.0 / —</td></tr>
<tr><td>Top of roof deck</td><td class="mono num">+47.5</td><td class="mono num">+37.5</td></tr>
<tr><td>Height above grade</td><td class="mono num">42.0</td><td class="mono num">32.0</td></tr>
<tr><td>Height above BFE (assumed +10)</td><td class="mono num">37.5</td><td class="mono num">27.5</td></tr>
<tr><td>Height above Level 1 floor</td><td class="mono num">32.5</td><td class="mono num">22.5</td></tr>
<tr><td>Pool coping (recessed 2'-6")</td><td class="mono num">+50.0</td><td class="mono num">+40.0</td></tr>
<tr><td>Elevator bulkhead top (≈12' over deck)</td><td class="mono num">+59.5</td><td class="mono num">+49.5</td></tr>
</tbody></table></div>
<ul>
  <li>Compressing Scenario 1 to 9'-0" ceilings everywhere only brings the deck to ≈+44.5 (39' above grade). The shortfall is structural, not decorative: the parking level under the house is what pushes everything up.</li>
  <li>Lowering Level 1 to the FBC minimum (≈+12.0) leaves ≈5' under the beams, so cars do not fit. A partly sunken garage is not realistic on a beach lot with a high water table and CCCL excavation limits.</li>
  <li>Therefore the height datum question goes first to the City: written zoning determination on (a) the measuring point for the 33' limit on an elevated coastal house and (b) whether the parking level counts as one of the three stories.</li>
</ul>`;

const levelNotes = {
  ground: `<ul>
    <li>Four cars in two tandem pairs (9'-9" bays, 20'-0" per car) entered from two 8' overhead doors on the west face; a fifth open bay behind them for a golf cart, bikes and beach gear, with a breakaway beach door east.</li>
    <li>Only one storage room. The mechanical/pool-equipment room is drawn on an elevated platform (equipment at or above BFE + 1'); the alternative is a screened closet in the rooftop stair block.</li>
    <li>A 3'-6" open gallery along the north side of the parking leads from the driveway to the lobby door, the storage room and the mechanical room; enclosures use breakaway construction if the lot is VE.</li>
    <li>Nothing habitable and no plumbing fixtures at this level.</li>
  </ul>`,
  L1: `<ul>
    <li>Kitchen (12' × 18', range wall south, column fridge west, 4' × 10' island with sink and four stools) → dining for eight (14' × 18') → living (10' × 30') → 5' ocean terrace: one 41' long great room with a 28' sliding-glass wall on the east face.</li>
    <li>Guest suite 14' × 13' on the city side with its own bath and closet; a door to the foyer lets it work as a home office.</li>
    <li>Front door opens into a 26' entry gallery along the north side that leads past the powder room to the lobby, stair and elevator. Laundry, butler's pantry and walk-in pantry sit behind the core so no service room takes the ocean face.</li>
  </ul>`,
  L2: `<ul>
    <li>Family lounge (6' + 14' zones, 460 sf, sofa facing a media wall, reading chairs and games table) is the circulation: City Suite 1 enters through a dressing vestibule from the lounge, City Suite 2 through a short hall, the Ocean Suite from the lounge's east wall.</li>
    <li>Mini bar / beverage center (8' × 7' pocket beside the elevator) with cabinetry, undercounter fridge, sink and a three-stool peninsula opening to the lounge through a 6' cased opening.</li>
    <li>Ocean suite 15' × 18' with floor-to-ceiling glass; its bath also takes 8' of the ocean face and stacks under the master bath.</li>
  </ul>`,
  L3: `<ul>
    <li>Arrival lobby → master lounge (fireplace, sofa) → dressing gallery with closets on both sides → bed (15' × 18', king bed facing the ocean through a 16' sliding-glass wall). The 5' × 12' ocean shower and the double-vanity bath with tub and private WC sit south of the bed at the glass; the bath also opens from the sitting room with its morning bar.</li>
    <li>No office, no second bedroom. The west 14' strip (gym, spa wet room, sauna and steam) is optional program; laundry and air handlers sit behind the elevator.</li>
    <li>Ceiling under the pool zone (x 40'–55') drops to ≈8'-6" to recess the pool shell 2'-6". The U-stair has 18 risers per floor; the lobby is its floor landing on every level.</li>
  </ul>`,
  roof: `<ul>
    <li>Three experiences: fire pit lounge and planters on the west (sunset, city), covered gourmet in the center, water on the east.</li>
    <li>The granite counter runs 10' along the pool edge at x = 40': two stools on the deck side per bay, four swim-up stools in the water. Option A (126 sf) is the counter bay plus the outdoor kitchen behind the elevator (grill, sink, fridge); Option B adds the 140 sf covered dining lounge south of it.</li>
    <li>Pool (360 sf of water): four wide in-water steps (5' × 8') down into a 10' × 8' Baja shelf with two in-water loungers, a 10' × 19' main pool 4'–5' deep, and a 5' × 10' swim-up bar; infinity edge and overflow trough along the full east face with a 3' walkway on the north to reach it.</li>
    <li>Rooftop bath (8' × 7') sits west of the stair, out of the ocean frontage. Bulkhead, bath and canopy heights are subject to the projection review.</li>
  </ul>`,
};

const reqLabel = { variance: 'City variance', zoning: 'Zoning confirmation', building: 'Building code', flood: 'FEMA / flood', fdep: 'FDEP / CCCL', structural: 'Structural' };
const statusLabel = { variance: 'Subject to variance', confirm: 'To confirm', byright: 'Expected by right', risk: 'Feasibility risk' };
const approvals = [
  { element: '30\' × 55\' envelope (front 20\', sides 5\', rear 5\')', requires: ['variance'], status: 'variance', why: 'Four dimensional variances from the by-right 25\' / 7\'-6" / 15\'. Precedent claimed at 5405 N Surf Rd (2023); exact numbers to be confirmed from the staff report.' },
  { element: 'Three residential stories over parking, ≈42\' above grade', requires: ['zoning', 'variance'], status: 'risk', why: 'Depends on the height datum and story-count rule. If measured from established grade, needs height and story variances.' },
  { element: 'Lot of 3,146 sf below the 5,800 sf minimum', requires: ['zoning'], status: 'confirm', why: 'Rely on the "or as platted" / lot-of-record provision; get a written determination.' },
  { element: 'Exterior entry stair and driveway apron in the 20\' front zone', requires: ['zoning'], status: 'confirm', why: 'Open stairs are usually an allowed projection (§4.23, 25% of yard up to 6\'); the stair is drawn deeper than 6\' into the yard.' },
  { element: 'L1 ocean terrace 5\' × 30\'', requires: ['zoning'], status: 'byright', why: 'Carved inside the envelope; no projection assumed. Only the envelope variance applies.' },
  { element: 'Rooftop covered gourmet · Option A 126 sf', requires: ['zoning'], status: 'byright', why: '7.6% of the 1,650 sf ground floor, under the 10% scenery-loft allowance reported for §4.22(E). Confirm that the bulkhead and bath do not count against it.' },
  { element: 'Rooftop covered gourmet · Option B 266 sf', requires: ['variance'], status: 'variance', why: '16.1% of ground floor. Precedent: 5405 N Surf Rd rooftop-coverage variance 24-V-45 (July 2024, snippet-level evidence).' },
  { element: 'Rooftop bath enclosure (8\' × 7\')', requires: ['zoning', 'building'], status: 'confirm', why: 'Enclosed rooftop space may count toward coverage or read as a story; plumbing on the roof needs building review.' },
  { element: 'Elevator bulkhead ≈12\' above the deck', requires: ['zoning', 'building'], status: 'confirm', why: 'Height-exemption rules for non-occupiable projections must be read for NBDD-CZ specifically, not the §4.6 beach-CRA rule.' },
  { element: 'Rooftop infinity pool (360 sf water, ≈135,000 lb with shell)', requires: ['structural', 'fdep', 'building', 'zoning'], status: 'confirm', why: 'Transfer beams on lines x = 40\' and the east face; FDEP treats pools outside the general permit; pool barrier, coping height and overflow trough need review.' },
  { element: 'Pool equipment at ground level', requires: ['flood', 'building'], status: 'confirm', why: 'Equipment must sit at or above BFE + 1\' (City §154.50 per snippet); alternative rooftop closet.' },
  { element: 'Ground-level enclosures: garage, storage, mechanical', requires: ['flood', 'building'], status: 'confirm', why: 'VE zone: breakaway walls, flood openings not applicable, no finished space; AE / Coastal A: flood vents. Zone to be read from the FIRM.' },
  { element: 'Glass elevator serving the flood level', requires: ['flood', 'building'], status: 'confirm', why: 'FEMA Technical Bulletin 4: cab, controls and pit below DFE need flood-resistant design or a landing above DFE.' },
  { element: 'Pile foundation and 30-year erosion siting', requires: ['fdep', 'structural'], status: 'confirm', why: 'Rule 62B-33 siting and foundation criteria; exact CCCL and erosion-projection lines from FDEP.' },
  { element: 'Grade sun deck east of the house', requires: ['zoning', 'fdep', 'flood'], status: 'confirm', why: 'Minor structure seaward of the CCCL; must stay landward of dune/vegetation lines and within the rear setback rules.' },
  { element: 'Ocean-facing glazing and rooftop lighting', requires: ['fdep', 'building'], status: 'confirm', why: 'Marine-turtle lighting rules (tinted glass, shielded fixtures) for all seaward-facing openings.' },
  { element: 'Two 9\'-9" garage bays behind two 8\' doors on a 20\' apron', requires: ['zoning'], status: 'confirm', why: 'Confirm the parking count required for a single-family home and that tandem stalls satisfy it (5405 N Surf Rd needed a parking variance).' },
];

const sources = `<p class="fine">Evidence level: the session's network policy blocked direct access to the primary hosts listed below, so the research agents could read search-engine snippets of those pages but not the full text. Every finding is therefore labelled at most "partially verified" until the next issue, when the workflow's adversarial re-check is complete.</p>
<ul class="src">
  <li>City of Hollywood Zoning and Land Development Regulations, hosted on American Legal Publishing (codelibrary.amlegal.com/codes/hollywood): Art. 4 §4.2(E) NBDD (multiple-family districts group), §4.22(E) supplemental regulations / scenery loft, §2.2 definitions (height from "established grade of the plot"). Note: the code is not on Municode.</li>
  <li>City of Hollywood Code §154.50 Flood Damage Prevention: lowest residential floor at the FBC-required elevation or at least 18 in above the highest adjacent street crown; mechanical equipment at BFE + 1 ft (snippet).</li>
  <li>Hollywood Legistar staff reports: 5405 N Surf Rd rooftop-coverage variance 24-V-45 (approved 9 Jul 2024, snippet); 501 S Surf Rd scenery-loft variance (sought 41%).</li>
  <li>Florida Building Code, Residential, 8th ed. (2023) R322.2 and R322.3: A-zone lowest floor at BFE + 1 ft or DFE; V-zone bottom of lowest horizontal member at BFE + 1 ft or DFE; enclosure limits.</li>
  <li>FEMA Technical Bulletins 4, 5 and 9 (elevators, free-of-obstruction, breakaway walls) — to be cited from fema.gov once reachable.</li>
  <li>Florida DEP Coastal Construction Control Line program and Rule 62B-33 F.A.C.; FDEP note that swimming pools are not covered by the CCCL general permit.</li>
  <li>Listing data for 5785 N Surf Rd (Zillow / MLS): Lot 20, Hollywood Central Beach, 40 × 80 ft, 3,146 sf, NBDD-CZ, vacant oceanfront.</li>
</ul>
<h3>Method</h3>
<ul>
  <li>Geometry: every room is a rectangle on a 6-inch grid inside the 30' × 55' box; a script checks that each level tiles exactly 1,650 sf with no overlaps, that the core is identical on all five levels, that the program (suite counts, orientation, shower on the east face, storage count, pool bounds) is met, and that the structural lines coincide with room edges on every level. The drawings and the schedule are rendered from the same file.</li>
  <li>Verification: eight parallel research agents per regulatory topic, a completeness critic, gap-fill agents and an adversarial refutation pass over the critical claims. Running at the time of this issue.</li>
  <li>Design: four independent core strategies are being scored by a three-judge panel and synthesized; the result replaces or confirms this preliminary scheme in the next issue.</li>
</ul>`;

const footer = 'Preliminary conceptual study for the owner\'s use in early feasibility conversations. It is not a survey, a zoning determination, a permit drawing or engineering. Setbacks, height, coverage, flood and coastal items are labelled by status on sheet A-301; nothing marked "subject to variance" or "to confirm" is represented as compliant.';

module.exports = { issueDate, stamp, sheets, verdict, siteNotes, sectionIntro, sections, sectionNotes, levelNotes, reqLabel, statusLabel, approvals, sources, footer };
