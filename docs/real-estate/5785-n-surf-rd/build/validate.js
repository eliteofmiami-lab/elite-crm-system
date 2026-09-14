const LEVELS = ['ground', 'L1', 'L2', 'L3', 'roof']
function overlap(r, s) {
  const ox = Math.min(r.x + r.w, s.x + s.w) - Math.max(r.x, s.x)
  const oy = Math.min(r.y + r.h, s.y + s.h) - Math.max(r.y, s.y)
  return (ox > 1e-6 && oy > 1e-6) ? ox * oy : 0
}
function touches(r, s) { // share an edge segment
  const ox = Math.min(r.x + r.w, s.x + s.w) - Math.max(r.x, s.x)
  const oy = Math.min(r.y + r.h, s.y + s.h) - Math.max(r.y, s.y)
  return (Math.abs(ox) < 1e-6 && oy > 1e-6) || (Math.abs(oy) < 1e-6 && ox > 1e-6)
}
function validate(d) {
  const errors = [], warnings = []
  const byLevel = {}
  for (const l of (d.levels || [])) byLevel[l.level] = l.rooms || []
  for (const L of LEVELS) {
    const rooms = byLevel[L]
    if (!rooms) { errors.push(`missing level ${L}`); continue }
    let sum = 0
    rooms.forEach((r, i) => {
      if (!(r.w > 0 && r.h > 0)) errors.push(`${L}/${r.name}: non-positive size`)
      if (r.x < -1e-6 || r.y < -1e-6 || r.x + r.w > 55 + 1e-6 || r.y + r.h > 30 + 1e-6) errors.push(`${L}/${r.name}: outside 55x30 box (x=${r.x},y=${r.y},w=${r.w},h=${r.h})`)
      for (const g of [r.x, r.y, r.w, r.h]) if (Math.abs(g * 2 - Math.round(g * 2)) > 1e-6) errors.push(`${L}/${r.name}: not on 0.5 ft grid (${g})`)
      sum += r.w * r.h
      for (let j = i + 1; j < rooms.length; j++) { const a = overlap(r, rooms[j]); if (a) errors.push(`${L}: "${r.name}" overlaps "${rooms[j].name}" by ${a.toFixed(1)} sf`) }
      const md = Math.min(r.w, r.h)
      if (r.kind === 'enclosed' && /bed|suite|master|primary/i.test(r.name) && !/bath|closet|wc|dress/i.test(r.name) && md < 11) warnings.push(`${L}/${r.name}: bedroom narrower than 11 ft (${md})`)
      if (r.kind === 'enclosed' && /bath/i.test(r.name) && md < 5) warnings.push(`${L}/${r.name}: bath narrower than 5 ft`)
      if (r.kind === 'enclosed' && /kitchen/i.test(r.name) && md < 9) warnings.push(`${L}/${r.name}: kitchen narrower than 9 ft`)
    })
    if (Math.abs(sum - 1650) > 0.5) errors.push(`${L}: rooms tile ${sum.toFixed(1)} sf, must be exactly 1650`)
  }
  const coreKinds = ['stair', 'elevator', 'lobby']
  const ref = byLevel.ground ? coreKinds.map(k => byLevel.ground.find(r => r.kind === k)) : [null, null, null]
  for (const L of LEVELS) coreKinds.forEach((k, i) => {
    const b = (byLevel[L] || []).find(r => r.kind === k)
    const cnt = (byLevel[L] || []).filter(r => r.kind === k).length
    if (!b) errors.push(`${L}: missing core element ${k}`)
    if (cnt > 1) errors.push(`${L}: more than one ${k} rectangle (${cnt})`)
    const a = ref[i]
    if (a && b && (a.x !== b.x || a.y !== b.y || a.w !== b.w || a.h !== b.h)) errors.push(`${L}: core ${k} moved (ground ${a.x},${a.y} ${a.w}x${a.h} vs ${L} ${b.x},${b.y} ${b.w}x${b.h})`)
  })
  const [st, el, lb] = ref
  if (st) { if (st.w * st.h < 80 || Math.min(st.w, st.h) < 3.5 || Math.max(st.w, st.h) < 12) errors.push(`stair ${st.w}x${st.h} below minimum (>=80 sf, min side 3.5, long side 12)`) }
  if (el) { if (Math.min(el.w, el.h) < 5.5 || Math.max(el.w, el.h) < 6.5) errors.push(`elevator ${el.w}x${el.h} below 5.5x6.5 minimum`) }
  if (lb) { if (Math.min(lb.w, lb.h) < 4 || lb.w * lb.h < 24) errors.push(`lobby ${lb.w}x${lb.h} below minimum (4 ft wide, 24 sf)`) }
  if (el && lb && !touches(el, lb)) errors.push('elevator does not open onto lobby (not touching)')
  if (st && lb && !touches(st, lb)) errors.push('stair does not touch lobby')
  // ground
  const g = byLevel.ground || []
  const garage = g.filter(r => r.kind === 'garage')
  const garageSf = garage.reduce((n, r) => n + r.w * r.h, 0)
  if (garageSf < 760) errors.push(`garage area ${garageSf} sf < 760 sf needed for 4 cars`)
  if (!garage.some(r => r.x < 1e-6)) errors.push('no garage rectangle reaches the west face x=0 (garage doors)')
  if (g.filter(r => r.kind === 'storage').length !== 1) errors.push(`ground must have exactly one storage room (found ${g.filter(r => r.kind === 'storage').length})`)
  if (g.some(r => r.kind === 'enclosed' && /bath|bed|living|gourmet|office/i.test(r.name))) errors.push('habitable room or bathroom at ground level')
  // L1
  const l1 = byLevel.L1 || []
  for (const need of [/living/i, /dining/i, /kitchen/i, /powder/i, /guest|flex|office/i]) if (!l1.some(r => need.test(r.name))) errors.push(`L1 missing ${need}`)
  if (!l1.some(r => /guest|flex|office/i.test(r.name) && /bath/i.test(r.name))) errors.push('L1 missing guest bath')
  if (!l1.some(r => /guest|flex|office/i.test(r.name) && /closet|wic/i.test(r.name))) warnings.push('L1 guest suite has no closet rectangle')
  if (!l1.some(r => /living|dining|kitchen|great/i.test(r.name) && Math.abs(r.x + r.w - 55) < 1e-6) && !l1.some(r => r.kind === 'outdoor' && Math.abs(r.x + r.w - 55) < 1e-6)) errors.push('L1 living/dining/kitchen or ocean terrace does not reach the east face')
  // L2
  const l2 = byLevel.L2 || []
  const beds2 = l2.filter(r => r.kind === 'enclosed' && /suite|bed/i.test(r.name) && !/bath|closet|wic|dress|bar/i.test(r.name))
  if (beds2.length !== 3) errors.push(`L2 must have exactly 3 bedroom rectangles (found ${beds2.length}: ${beds2.map(r => r.name).join(', ')})`)
  const ocean2 = beds2.filter(r => Math.abs(r.x + r.w - 55) < 1e-6 || l2.some(o => o.kind === 'outdoor' && Math.abs(o.x + o.w - 55) < 1e-6 && touches(o, r)))
  const city2 = beds2.filter(r => r.x < 1e-6)
  if (ocean2.length !== 1) errors.push(`L2 needs exactly 1 ocean suite touching the east face (found ${ocean2.length})`)
  if (city2.length !== 2) errors.push(`L2 needs exactly 2 city suites touching the west face x=0 (found ${city2.length})`)
  if (l2.filter(r => /bath/i.test(r.name)).length < 3) errors.push('L2 needs 3 bathrooms')
  if (l2.filter(r => /closet|wic|dress/i.test(r.name)).length < 3) errors.push('L2 needs 3 closets')
  if (!l2.some(r => /family|lounge/i.test(r.name))) errors.push('L2 missing family lounge')
  if (!l2.some(r => /bar|beverage/i.test(r.name) || (/family|lounge/i.test(r.name) && /bar/i.test(r.notes || '')))) warnings.push('L2 mini bar not called out')
  // L3
  const l3 = byLevel.L3 || []
  if (!l3.some(r => /shower/i.test(r.name) && Math.abs(r.x + r.w - 55) < 1e-6) && !l3.some(r => /bath/i.test(r.name) && /shower/i.test((r.notes || '') + r.name) && Math.abs(r.x + r.w - 55) < 1e-6)) errors.push('L3 shower (or bath containing it) does not touch the east face x=55')
  for (const need of [/bed|sleep/i, /lounge|sitting|seating/i, /dress|closet|wic/i, /bath/i, /wc|toilet/i]) if (!l3.some(r => need.test(r.name))) errors.push(`L3 missing ${need}`)
  if (l3.some(r => /office|second bed|family room/i.test(r.name))) errors.push('L3 contains an office/second bedroom/family room')
  // roof
  const rf = byLevel.roof || []
  const pools = rf.filter(r => r.kind === 'pool')
  if (!pools.length) errors.push('roof has no pool')
  if (!pools.some(r => r.x + r.w >= 54.5 - 1e-6)) errors.push('pool east edge (infinity edge) must reach x>=54.5')
  if (!pools.some(r => /shelf|baja|sun/i.test(r.name))) errors.push('roof pool missing sun shelf / baja shelf rectangle')
  if (!rf.some(r => /swim|wet bar/i.test(r.name))) warnings.push('swim-up / wet bar zone not called out')
  const cov = rf.filter(r => r.kind === 'covered_outdoor')
  if (!cov.length) errors.push('roof has no covered gourmet area')
  if (!cov.some(c => pools.some(p => touches(c, p)))) errors.push('covered gourmet counter is not adjacent to the pool (no shared edge)')
  if (!rf.some(r => /bath/i.test(r.name) && r.kind === 'enclosed')) errors.push('roof missing bathroom')
  if (!rf.some(r => /fire/i.test(r.name) && r.x < 27.5)) errors.push('roof missing fire pit lounge on the west half')
  const poolSf = pools.reduce((n, r) => n + r.w * r.h, 0)
  if (poolSf < 200) warnings.push(`pool total ${poolSf} sf is small`)
  // structural lines
  const lines = (d.structural_lines_x || []).filter(x => x > 0 && x < 55)
  if (lines.length < 2) errors.push('need at least 2 interior structural lines')
  for (const L of LEVELS) for (const x of lines) if (!(byLevel[L] || []).some(r => Math.abs(r.x - x) < 1e-6 || Math.abs(r.x + r.w - x) < 1e-6)) errors.push(`${L}: no room edge on structural line x=${x}`)
  const px = Math.min(...pools.map(p => p.x)); const pxe = Math.max(...pools.map(p => p.x + p.w))
  if (pools.length && !lines.some(x => Math.abs(x - px) < 1e-6)) errors.push(`pool west edge x=${px} is not on a structural line`)
  if (pools.length && !(pxe >= 54.5 - 1e-6 || lines.some(x => Math.abs(x - pxe) < 1e-6))) errors.push(`pool east edge x=${pxe} not on a structural line or east face`)
  return { errors, warnings }
}


module.exports={validate};
