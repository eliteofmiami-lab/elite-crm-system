// Editorial content for the drawing set. Preliminary issue: regulatory verification still running.
const issueDate = '14 Sep 2026 · Issue P2 (verified)';
const stamp = 'Conceptual · assumes setback variances · not for construction';

const sheets = [
  ['A-000', 'Feasibility verdict'], ['A-001', 'Site plan'], ['A-002', 'Height section'],
  ['A-101', 'Ground / garage'], ['A-102', 'Level 1'], ['A-103', 'Level 2'], ['A-104', 'Level 3 · primary'], ['A-105', 'Rooftop'],
  ['A-201', 'Area schedule'], ['A-301', 'Approvals matrix'], ['A-401', 'Sources'], ['A-402', 'Findings register'],
];

const verdict = `
<div class="callout"><p><b>Resumo em português.</b> As plantas (A-101 a A-105) são plantas baixas arquitetônicas completas dentro do envelope de 30' × 55', com núcleo fixo, e passam na validação geométrica. A verificação regulatória terminou, com uma limitação que precisa ficar clara: a rede desta sessão bloqueou os sites primários (código de Hollywood no amlegal, Legistar, FDEP, FEMA, BCPA), então tudo foi lido por trechos de busca dessas páginas e por espelhos de estatutos estaduais; nada do código municipal foi lido na íntegra. O que ficou estabelecido: (1) o mínimo de 5.800 sf para casa unifamiliar na NBDD-CZ está confirmado, mas a cláusula "or as platted" que você citou <b>não apareceu em nenhum trecho</b>; se ela está no texto que você leu, o lote é edificável by right, senão a área do lote vira a primeira variance. (2) Os 33 ft / 3 pavimentos e os recuos 25/15/7,5 não foram encontrados nos trechos; ficam como sua leitura do §4.2(E). (3) Dois trechos apontam recuo lateral de <b>5 ft by right</b> para lotes platted de até 50 ft de largura ou até 6.500 sf, o que reduziria as variances de recuo para duas (frente e fundos). (4) A altura é medida a partir do "established grade of the plot"; nada mede a partir da cota de inundação, e o código de edificações conta o pavimento de garagem como pavimento. Com garagem sob a casa, três pavimentos residenciais ficam a ~42 ft do terreno: o programa pedido depende de uma determinação escrita da Cidade sobre datum e contagem de pavimentos, ou de variance de altura. (5) O precedente 5405 N Surf: a variance de cobertura do rooftop (24-V-45, aprovada em 9 jul 2024) existe, mas o percentual aprovado, as condições e as "cinco variances de março de 2023" com os números de recuo <b>não foram encontrados</b>. (6) Regras de inundação e CCCL (FBC R322.3, FBC 3109, F.S. 161.053) foram confirmadas em texto estadual e estão incorporadas ao desenho.</p></div>
<div class="verdict-grid">
  <div class="vcard bad"><h3>Lot area: 3,146 sf against a 5,800 sf minimum</h3><p>The minimum is confirmed at snippet level in §4.2(E). No "or as platted" or lot-of-record clause surfaced in any snippet of §4.2(E), Article 3 or §2.2. If your copy of the code carries it, the lot is buildable by right; if not, a lot-of-record determination or lot-area variance comes before everything else. Title must also show no §4.2E.4 open-space dedication on Lot 20.</p></div>
  <div class="vcard warn"><h3>Envelope 30' × 55'</h3><p>Front 20' and rear 5' need variances from the figures you read (25' and 15'); those by-right figures were not found in snippets. Side 5' may be by right: §4.23 reportedly sets 5' "for platted lots of 50 feet or less", and a §4.2 rule gives 5' for lots of 6,500 sf or less. Two setback variances instead of four is the likely count.</p></div>
  <div class="vcard bad"><h3>Height and story count</h3><p>ZLDR §2.2 measures height from the "established grade of the plot"; no source measures from BFE or DFE, and the 33' / 3-story figures themselves did not appear in snippets. With a garage under the house, three residential floors put the roof deck ≈42' above grade. The program as drawn needs a written determination that the flood level is excluded, or a height and story variance. The two-story fallback on A-002 fits from grade.</p></div>
  <div class="vcard ok"><h3>Floor-plan geometry</h3><p>All five levels tile the envelope exactly; core identical on every level; two transverse lines (x = 26', 40') plus the east face stack from roof to piles and bound the pool. At the parking level those lines are column lines, not solid walls, which is what FBC-B 3109 requires seaward of the CCCL.</p></div>
  <div class="vcard warn"><h3>Rooftop covered area</h3><p>The 10%-of-ground-floor cap is a City staff paraphrase (501 S Surf Rd report), attributed to §4.22(E). File 24-V-45 at 5405 N Surf Rd, same district and lot type, was approved on 9 July 2024 for covered rooftop area above 10%; the approved percentage, conditions and vote are unread. The March 2023 "five variances" and the "25% → 29%" item were not found. Option A (126 sf, 7.6%) stays under the cap; Option B (266 sf, 16.1%) follows the 24-V-45 path.</p></div>
  <div class="vcard info"><h3>Rooftop pool</h3><p>≈360 sf of water, ≈72,000 lb, ≈135,000 lb with the shell (≈375 psf) on lines x = 40' and the east face. Under F.S. 161.54 a pool is a "nonhabitable major structure"; the statute allows a general permit for a single-family house with an associated pool that does not advance the line of construction, while FDEP's own guidance excludes pools from the general permit, so get a written pre-application answer. If §4.23 pool setbacks (6' to water's edge) are applied on the roof, the basin pulls in 1' from each side face.</p></div>
  <div class="vcard info"><h3>Ground level (verified rules)</h3><p>FBC-R R322.3: bottom of the lowest horizontal member at BFE + 1' or DFE; space below only for parking, access and storage; breakaway walls 10–20 psf with flood openings; no plumbing fixtures, panels or condensers below the elevation; pool equipment only if elevated, anchored and GFCI-protected. The garage clearance, not the flood map, is what lifts Level 1 to ≈9'-6" above the driveway.</p></div>
  <div class="vcard warn"><h3>Parking count</h3><p>§7.1 allows tandem spaces and 8'-6" × 18' stalls for single-family, so the 2 × 2 garage is geometrically fine. The required or maximum count for NBDD-CZ was not retrieved; the Beach CRA treats 1.5 spaces as a maximum (501 S Surf Rd needed a variance for 5) and 5405 N Surf Rd reportedly needed parking relief. Treat the 4-car garage as possibly needing a variance.</p></div>
  <div class="vcard info"><h3>Coastal jurisdiction (verified statute)</h3><p>F.S. 161.053: nothing seaward of the CCCL without FDEP authorization; the 30-year erosion projection bars major structures seaward of it, with a single-family exception on pre-existing platted lots built "as far landward as is practicable". F.S. 161.191: a recorded erosion control line is the fixed seaward boundary, so the rear setback runs from the surveyed ECL. Turtle-lighting plan required. The CCCL position itself must come from FDEP Map Direct or the survey.</p></div>
  <div class="vcard info"><h3>Property facts (listing only)</h3><p>MLS snippets: Lot 20, Hollywood Central Beach, 40' frontage, listed 6 Aug 2026 at $600,000, last sale 17 Oct 2018. 3,146 sf equals exactly 40' × 78.65', so the plan should assume ≈78.6' of depth until a survey ties the plat line, ECL and CCCL. The property appraiser record and the neighbors' built forms could not be opened.</p></div>
</div>
<h3>How to read the evidence</h3>
<ul>
  <li><b>Code snippet</b>: wording of the Hollywood ZLDR or City Code as returned by a search engine from the official host (codelibrary.amlegal.com). Repeated across independent snippets where marked verified. Not a full-text read.</li>
  <li><b>Staff-report snippet</b>: wording from City of Hollywood Planning and Development Board documents on Legistar, same limitation.</li>
  <li><b>State rule</b>: Florida Statutes and the Florida Building Code, read in full from statute and code mirrors; these are the firmest findings.</li>
  <li><b>Adversarial pass</b>: 14 critical claims were handed to independent refuters. Because the session's web-search allowance was exhausted and the primary hosts were blocked, every refuter returned "cannot confirm" rather than a contradiction. One substantive correction survived: FBC-R R322.2.1 does not govern Coastal A zones in Florida, R322.3 does. Statuses on A-402 reflect evidence level, not refutation.</li>
</ul>
<h3>Decisions the drawings already make</h3>
<ul>
  <li><b>Core on the north side</b> (x 8'–32': stair, lobby-landing, glass elevator), keeping the full 30' ocean face free on every level. The glass elevator looks east through the interior on L1–L3 and directly at the ocean at the roof stop.</li>
  <li><b>Balconies carved from the envelope</b>: the L1 ocean terrace is 5' × 30' inside the 30' × 55' box. No projections beyond the box are assumed on any level; §4.23 would allow at most 25% of a yard up to 6', i.e. 1'-3" into a 5' side yard.</li>
  <li><b>Pool recessed 2'-6" into the Level 3 ceiling zone</b> under the master bed and bath (ceiling there drops to ≈8'-6"), so the coping sits ≈2'-6" above the deck instead of 5'. The fully raised alternative with a grand stair is possible but adds height to the projection review.</li>
  <li><b>Level 3 west side</b> is drawn as a private gym and a sauna/steam spa. It is optional program and can become a sunset terrace or a second dressing room without touching the core.</li>
  <li><b>Massing can slide west.</b> If FDEP's 30-year line bites, the single-family exception pushes the house to the minimum front setback; the plan keeps the same core if the whole envelope shifts.</li>
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
  { element: 'Single-family house on a 3,146 sf lot (5,800 sf minimum in §4.2(E))', requires: ['zoning', 'variance'], status: 'risk', why: 'Minimum confirmed at snippet level; no "or as platted" or lot-of-record clause found. Written determination or lot-area variance first; confirm no §4.2E.4 dedication on title.' },
  { element: 'Front setback 20\' (by-right figure read as 25\')', requires: ['variance'], status: 'variance', why: 'By-right figure not found in snippets; taken from the owner\'s reading of §4.2(E).' },
  { element: 'Rear / ocean setback 5\' (read as 15\' or 15%)', requires: ['variance', 'fdep'], status: 'variance', why: 'Measured from the surveyed ECL (F.S. 161.191). FDEP may not permit anything that contravenes a stricter local setback (F.S. 161.053).' },
  { element: 'Side setbacks 5\' each', requires: ['zoning'], status: 'confirm', why: 'Possibly by right: §4.23 "platted lots of 50 feet or less, the setback is 5 feet" and a §4.2 rule of 5\' for lots ≤ 6,500 sf (snippets). Otherwise 7\'-6" applies and the envelope narrows to 25\'.' },
  { element: 'Three residential stories over parking, roof deck ≈42\' above grade', requires: ['zoning', 'variance'], status: 'risk', why: 'Height from "established grade of the plot" (§2.2 snippet); no BFE/DFE datum found; FBC counts the parking level as a story above grade plane. Needs a written determination or a height and story variance; two-story fallback on A-002 fits.' },
  { element: 'Setback areas kept visually open to the beach', requires: ['zoning'], status: 'byright', why: 'Confirmed §4.2(E) rule: no opaque fences, sheds or canopies in setback areas that block visual access to the beach. Drawn with open rails and planting only.' },
  { element: 'Exterior entry stair and driveway apron in the 20\' front zone', requires: ['zoning'], status: 'confirm', why: '§4.23 allows listed features up to 25% of a yard, max 6\'; some are "not permitted in the front yard" (list unread). §7.1: driveway 12\' one-way, 3\' from side lines; ≥ 20% of the front yard pervious with a canopy tree.' },
  { element: 'Four-car tandem garage (2 × 2)', requires: ['zoning'], status: 'confirm', why: '§7.1 permits tandem spaces and 8\'-6" × 18\' stalls. Required or maximum count for NBDD-CZ not retrieved; Beach CRA caps single-family at 1.5 spaces and 5405 N Surf Rd reportedly needed parking relief.' },
  { element: 'L1 ocean terrace 5\' × 30\' inside the envelope', requires: ['zoning'], status: 'byright', why: 'No projection beyond the box; only the envelope variances apply.' },
  { element: 'Rooftop covered gourmet · Option A 126 sf (7.6%)', requires: ['zoning'], status: 'byright', why: 'Under the 10%-of-ground-floor scenery-loft cap that City staff attribute to §4.22(E). Confirm that the elevator bulkhead and rooftop bath are not counted against it.' },
  { element: 'Rooftop covered gourmet · Option B 266 sf (16.1%)', requires: ['variance'], status: 'variance', why: 'Precedent: 24-V-45, 5405 N Surf Rd, approved 9 July 2024 for covered rooftop area above 10% in NBDD-CZ; approved percentage and conditions unread.' },
  { element: 'Rooftop bath enclosure (8\' × 7\')', requires: ['zoning', 'building'], status: 'confirm', why: 'Enclosed rooftop space may count toward coverage or read as a story; rooftop plumbing needs building review.' },
  { element: 'Elevator bulkhead ≈12\' above the deck and stair vestibule', requires: ['zoning', 'building'], status: 'confirm', why: 'The "not intended for human occupation" exemption found is a §4.6 (Beach CRA) rule; the §4.22(E) list for NBDD-CZ was not read. Penthouses must be screened as part of the design (snippet).' },
  { element: 'Rooftop infinity pool (360 sf water, ≈135,000 lb with shell)', requires: ['structural', 'fdep', 'building', 'zoning'], status: 'confirm', why: 'Fluid load ≈250 psf plus deck and 170 mph wind; long walls on column lines to pile caps. F.S. 161.54: pool is a nonhabitable major structure; statute allows a general permit for a house with an associated pool, FDEP guidance excludes pools: get a written answer. §4.23 pool setbacks (6\' to water\'s edge) may apply on the roof.' },
  { element: 'Pool coping, weir and guard height', requires: ['zoning'], status: 'confirm', why: 'No ZLDR text on rooftop pools versus height was found; recessing the shell 2\'-6" keeps the coping low. Barrier ≥ 48" per FBC.' },
  { element: 'Pool equipment at ground level on an elevated platform', requires: ['flood', 'building'], status: 'confirm', why: 'R322.1.6: equipment below the elevation only if elevated as practical, anchored and GFCI-protected; §154.50 (snippet) puts MEP at or above BFE + 1\'. Alternative: rooftop closet.' },
  { element: 'Ground-level enclosures: lobby, storage, mechanical, garage doors', requires: ['flood', 'building'], status: 'confirm', why: 'R322.3.5: non-structural breakaway or lattice walls (10–20 psf) with flood openings; frangible slab; no fixtures. Enclosure limited to what the plan shows; no bathroom at this level.' },
  { element: 'Glass elevator serving the flood level', requires: ['flood', 'building'], status: 'confirm', why: 'Shaft exempt from breakaway rules but must meet ASCE 24 (FBC-B 3109.3.4); cab, controls and pit below DFE per FEMA TB-4.' },
  { element: 'Pile foundation, breakaway construction and shear-wall orientation', requires: ['fdep', 'structural'], status: 'confirm', why: 'FBC-B 3109 seaward of the CCCL: piles or columns only, no stem walls; lowest member above the higher of ASCE 24, City or FDEP 100-year storm elevation; shore-parallel shear walls limited to 20% of length (6\' on 30\').' },
  { element: 'Siting against the 30-year erosion projection', requires: ['fdep'], status: 'confirm', why: 'F.S. 161.053(5): major structures barred seaward of the 30-year line; single-family exception for pre-existing platted lots built as far landward as practicable. The line must be plotted on the survey.' },
  { element: 'Grade sun deck east of the house', requires: ['zoning', 'fdep', 'flood'], status: 'confirm', why: 'Minor structure seaward of the CCCL; must stay landward of dune and vegetation lines and within rear-yard rules.' },
  { element: 'Ocean-facing glazing and rooftop lighting', requires: ['fdep', 'building'], status: 'confirm', why: 'Marine-turtle lighting ordinance (reported §108) in force 1 March – 31 October; FDEP may require a lighting plan: tinted glass, shielded amber fixtures.' },
  { element: 'Lot depth 80\' vs 78.65\' implied by 3,146 sf', requires: ['zoning'], status: 'confirm', why: 'Boundary and topographic survey tying the plat line, ECL and CCCL before any dimension is fixed.' },
  { element: 'FEMA zone, BFE and effective FIRM', requires: ['flood'], status: 'confirm', why: 'Not obtained: sources conflict between 2014 and 2024 map dates; VE inferred from the 5405 N Surf Rd record (100% VE). BFE 10 ft NAVD88 is a placeholder.' },
];

const sources = `<p class="fine">Evidence caveat: the session's network policy blocked direct access to codelibrary.amlegal.com (Hollywood ZLDR and City Code), hollywoodfl.legistar.com, floridadep.gov, msc.fema.gov and bcpa.net. The research read search-engine snippets of those pages and full text of Florida Statutes and Florida Building Code mirrors. Web-search allowance was exhausted before the adversarial pass, so refuters could not re-test the claims. Nothing municipal below was read in full.</p>
<ul class="src">
  <li>Hollywood ZLDR §4.2 incl. §4.2(E) NBDD (uses, 5,800 sf minimum, TDR, visual-access rule) — <a href="https://codelibrary.amlegal.com/codes/hollywood/latest/hollywoodldr_fl/0-0-0-722">amlegal 0-0-0-722</a></li>
  <li>Hollywood ZLDR §2.2 Terms Defined (height of a building) — <a href="https://codelibrary.amlegal.com/codes/hollywood/latest/hollywoodldr_fl/0-0-0-105">amlegal 0-0-0-105</a></li>
  <li>Hollywood ZLDR §4.22 / §4.22(E) height exemptions, scenery lofts — <a href="https://codelibrary.amlegal.com/codes/hollywood/latest/hollywoodldr_fl/0-0-0-1787">amlegal 0-0-0-1787</a></li>
  <li>Hollywood ZLDR §4.23 encroachments, side yards for platted lots ≤ 50', pool setbacks — <a href="https://codelibrary.amlegal.com/codes/hollywood/latest/hollywoodldr_fl/0-0-0-1975">amlegal 0-0-0-1975</a></li>
  <li>Hollywood ZLDR §7.1 parking geometry, tandem spaces, driveways — <a href="https://codelibrary.amlegal.com/codes/hollywood/latest/hollywoodldr_fl/0-0-0-2622">amlegal 0-0-0-2622</a></li>
  <li>Hollywood Code §154.50 Flood Damage Prevention — <a href="https://codelibrary.amlegal.com/codes/hollywood/latest/hollywood_fl/0-0-0-13913">amlegal 0-0-0-13913</a></li>
  <li>Planning and Development Board minutes, 9 July 2024, File 24-V-45 (5405 N Surf Rd) — <a href="https://hollywoodfl.legistar.com/View.ashx?GUID=3A0C011F-EC3C-41E0-91D1-A100CF29C6E2&ID=1205519&M=M">Legistar 1205519</a></li>
  <li>Staff report, 12 Aug 2025, 5405 N Surf Rd (unread) — <a href="https://hollywoodfl.legistar.com/View.ashx?GUID=638A890D-8EFC-449C-B3BD-E3C2CA03C8E1&ID=14554393&M=F">Legistar 14554393</a></li>
  <li>Staff report, 22 July 2025, 501 S Surf Rd scenery-loft variance (10% cap wording) — <a href="https://hollywoodfl.legistar.com/View.ashx?GUID=D3D5D7FA-B97E-41AF-9785-9A1ED3F52CC2&ID=14340780&M=F">Legistar 14340780</a></li>
  <li>Florida Statutes 161.053 (CCCL, 30-year erosion projection, general permits) and 161.181–161.201, 161.54 (ECL, definitions) — <a href="http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0100-0199/0161/0161.html">leg.state.fl.us ch. 161</a></li>
  <li>Florida Building Code, Residential 2023, R322.2 and R322.3 (flood-resistant construction) — <a href="https://codes.iccsafe.org/s/FLRC2023P1/chapter-3-building-planning/FLRC2023P1-Pt03-Ch03-SecR322.2">ICC FLRC 2023</a></li>
  <li>Florida Building Code, Building 2023, §3109 structures seaward of the CCCL; Ch. 16 loads — <a href="https://up.codes/viewer/florida/fl-building-code-2023/chapter/31/special-construction">up.codes mirror</a></li>
  <li>FEMA Map Service Center query for the address (not reachable in session) — <a href="https://msc.fema.gov/portal/search?AddressQuery=5785%20N%20Surf%20Rd%2C%20Hollywood%2C%20FL%2033019">msc.fema.gov</a></li>
  <li>Broward County Property Appraiser, folio 514201027042 (not reachable in session) — <a href="https://web.bcpa.net/BcpaClient/#/Record-Search?folio=514201027042">bcpa.net</a></li>
  <li>Listing snippets for 5785 N Surf Rd (MLS #B26061057) — <a href="https://www.zillow.com/homedetails/5785-N-Surf-Rd-Hollywood-FL-33019/103031315_zpid/">Zillow</a></li>
</ul>
<h3>Method</h3>
<ul>
  <li>Geometry: every room is a rectangle on a 6-inch grid inside the 30' × 55' box; a script checks that each level tiles exactly 1,650 sf with no overlaps, that the core is identical on all five levels, that the program (suite counts, orientation, shower on the east face, storage count, pool bounds) is met, and that the structural lines coincide with room edges on every level. Walls, doors, glazing and furniture are data on each room; the drawings and the schedule are rendered from the same file.</li>
  <li>Verification: eight parallel research agents per regulatory topic (115 findings), a completeness critic, six gap-fill agents and a 14-claim adversarial pass; 29 agents in total. A synthesis pass reduced the file to the 26 facts on A-402, each tied to a source URL and quote from the research file.</li>
  <li>What would close the open items fastest: the full text of §4.2(E), §2.2 and §4.22(E); the 24-V-45 staff report and minutes; the FIRM panel; FDEP Map Direct for the CCCL and 30-year line; the BCPA card. Any of these pasted into the conversation can be checked directly against the drawings.</li>
</ul>`;

const footer = 'Preliminary conceptual study for the owner\'s use in early feasibility conversations. It is not a survey, a zoning determination, a permit drawing or engineering. Setbacks, height, coverage, flood and coastal items are labelled by status on sheet A-301; nothing marked "subject to variance" or "to confirm" is represented as compliant.';

module.exports = { issueDate, stamp, sheets, verdict, siteNotes, sectionIntro, sections, sectionNotes, levelNotes, reqLabel, statusLabel, approvals, sources, footer };
