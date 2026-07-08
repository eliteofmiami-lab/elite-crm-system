// PUSH em tempo real (PAINEL_DIARIO — camada 1): os workflows de webhook do GHL
// apontam pra cá. Cada evento roda um MINI-ESPELHO do contato (leitura no GHL →
// board_cards no Supabase). ZERO escrita no GHL. Card de stage movido some em ≤5s.
// Requer env (Vercel): GHL_API_TOKEN · SUPABASE_SERVICE_ROLE_KEY · WEBHOOK_KEY.
import { NextResponse } from "next/server";

const GHL = "https://services.leadconnectorhq.com";
const LOC = "Ao5ER8XBg3AtCJMccesF";
const NEW_PIPELINE = "oUL5N3vxYqL13sBLrZUF";
const STAGE_BY_ID = {
  "22b4c971-42cb-4665-89dd-72966fe3a1cc": "Great Cars",
  "5750c231-d5d4-4959-9112-0e2c78b1d2c2": "New Lead",
  "f1c50583-3e96-40ed-980c-de0e2b47a84c": "Contact 1 (AM)",
  "f6ad51ef-1973-4089-a119-e8dee6d065a6": "Contact 1 (PM)",
  "8e199abc-afb4-468e-8d0b-41922714e3ca": "Contact 2 (AM)",
  "9c10347f-188b-4c9b-abf2-ebbff8c49201": "Contact 2 (PM)",
  "f0480213-6014-4f7e-8b1f-0bf18255163e": "Contact 3 (AM)",
  "f4132e16-72fe-4fd7-af4d-046e80596e56": "Contact 3 (PM)",
  "41e90499-e2f5-4a80-a772-9dc08dc86475": "Follow Up",
  "708575b3-2b8e-4bd8-91cb-a2fb4774484a": "Quote Sent",
  "77313fe9-fba1-4955-a62e-9094f1140fce": "Appointment Booked",
  "8ecb943b-01d3-4d95-b3c2-7ece780dc512": "Win",
  "125cfc10-4578-4275-86ae-5344aeea0676": "Lost",
  "361f01f1-fd89-4e2f-8e74-eaf3a17b6cad": "HOT LEADS",
};
// Follow Up/Quote Sent NÃO criam card aqui: são regidos por TASK (ciclo cuida);
// o webhook só FECHA os cards do stage antigo em ≤8s.
const STAGE_CARD = {
  "HOT LEADS": [1, "hot"], "New Lead": [2, "new_lead"],
  "Contact 1 (AM)": [4, "pipeline"], "Contact 1 (PM)": [4, "pipeline"],
  "Contact 2 (AM)": [4, "pipeline"], "Contact 2 (PM)": [4, "pipeline"],
  "Contact 3 (AM)": [4, "pipeline"], "Contact 3 (PM)": [4, "pipeline"],
};
const STAGE_KINDS = ["hot", "new_lead", "pipeline", "followup", "followup_notask", "quote_notask"];
const CLOSES = {
  hot: "Closes when: call made → one resolution (appointment · task · estimate+stage · Lost). Unanswered: next stage.",
  new_lead: "Closes when: call made → appointment · task · estimate+stage · Lost. Unanswered: move to Contact 1.",
  pipeline: "Closes when: call made → resolution. Unanswered: next stage.",
  sms_reply: "Closes when: reply sent.",
  missed_inbound: "Closes when: return call made → then one resolution (appointment · task · estimate+stage · Lost). Unanswered: next stage.",
  appt_confirm: "Closes when: confirmation SMS sent OR status \"confirmed\" in GHL.",
};
const CF_VEH = { make: "CiRd678lAFn854igklGR", model: "LHwTnTb8TPz5BbJ0I2XV", year: "C01IzbXlbESCLfhoHkrZ" };
const CF_INTEREST = "D5TgphY9HlZMoS8wcWj1";

function sb(method, path, body, extra = {}) {
  const url = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/rest/v1/${path}`;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return fetch(url, {
    method,
    headers: { apikey: key, Authorization: `Bearer ${key}`,
      "Content-Type": "application/json", Prefer: "return=representation", ...extra },
    body: body ? JSON.stringify(body) : undefined,
  }).then(async (r) => (r.status === 204 ? [] : r.json().catch(() => [])));
}
function ghl(path, params) {
  const qs = params ? "?" + new URLSearchParams(params) : "";
  return fetch(GHL + path + qs, {
    headers: { Authorization: `Bearer ${process.env.GHL_API_TOKEN}`,
      Version: "2021-07-28", Accept: "application/json" },
  }).then((r) => (r.ok ? r.json() : null));
}

async function contactBrief(cid) {
  const j = await ghl(`/contacts/${cid}`);
  const c = j?.contact || {};
  const cfs = Object.fromEntries((c.customFields || []).map((f) => [f.id, f.value]));
  const veh = [cfs[CF_VEH.year], cfs[CF_VEH.make], cfs[CF_VEH.model]].filter(Boolean).join(" ");
  return {
    nome: `${c.firstName || ""} ${c.lastName || ""}`.trim() || null,
    phone: c.phone || null, veh: veh || null,
    interest: cfs[CF_INTEREST] || null, tags: c.tags || [],
  };
}

async function miniMirrorStage(cid) {
  // espelho do contato: stages atuais → fecha cards órfãos, cria o do stage novo
  const j = await ghl("/opportunities/search", { location_id: LOC, contact_id: cid, limit: 10 });
  const opps = (j?.opportunities || []).filter((o) => o.pipelineId === NEW_PIPELINE);
  const stagesNow = new Set(opps.filter((o) => o.status === "open")
    .map((o) => STAGE_BY_ID[o.pipelineStageId]).filter(Boolean));
  const isWin = opps.some((o) => o.status === "won" || STAGE_BY_ID[o.pipelineStageId] === "Win");
  const open = await sb("GET", `board_cards?status=eq.open&contact_id=eq.${cid}&select=*`);
  let closed = 0, created = 0;
  for (const card of open) {
    const stale = STAGE_KINDS.includes(card.kind) &&
      card.stage && !stagesNow.has(card.stage);
    if (isWin || stale) {
      // espelho primeiro: opp saiu do stage (ou virou Win) → card fecha SEMPRE
      await sb("PATCH", `board_cards?id=eq.${card.id}`, {
        status: "resolved", resolved_by: isWin ? "won" : "stage moved (webhook)",
        resolved_at: new Date().toISOString(), unres: false });
      closed++;
    } else if (card.unres && stagesNow.has("Lost")) {
      // resolução da árvore: marcado Lost limpa o SEM RESOLUÇÃO
      await sb("PATCH", `board_cards?id=eq.${card.id}`, {
        status: "resolved", resolved_by: "marked Lost (webhook)",
        resolved_at: new Date().toISOString(), unres: false });
      closed++;
    }
  }
  if (!isWin) {
    // regra Peter (08/jul): appointment futuro → nenhum card de stage nasce;
    // o lead vive na coluna 5
    const aj = await ghl(`/contacts/${cid}/appointments`);
    const hasApptUp = (aj?.events || []).some((e) => {
      const stt = new Date(e.startTime).getTime();
      return !isNaN(stt) && stt > Date.now() - 3 * 3600e3 &&
        !["cancelled", "invalid", "noshow"].includes(e.appointmentStatus);
    });
    if (hasApptUp) return { closed, created };
    // cadência (regra Rafael): 2 mudanças de stage HOJE = completo por hoje —
    // não recria card do pipeline até amanhã
    const today = new Date().toISOString().slice(0, 10);
    const movedToday = await sb("GET",
      `board_cards?contact_id=eq.${cid}&status=eq.resolved&resolved_at=gte.${today}T04:00:00Z&resolved_by=like.stage*&select=id`);
    for (const o of opps.filter((x) => x.status === "open")) {
      const st = STAGE_BY_ID[o.pipelineStageId];
      const map = STAGE_CARD[st];
      if (!map) continue;
      if (map[1] === "pipeline" && (movedToday || []).length >= 2) continue;
      const dup = await sb("GET",
        `board_cards?status=eq.open&contact_id=eq.${cid}&kind=eq.${map[1]}&select=id&limit=1`);
      if (dup.length) continue;
      // ⚑ reportado: mesma ocorrência (stage não mudou desde o report) não recria;
      // stage novo (lastStageChangeAt mais novo) recria normal
      const ots = o.lastStageChangeAt || o.updatedAt || new Date().toISOString();
      const rep = await sb("GET",
        `board_cards?contact_id=eq.${cid}&kind=eq.${map[1]}&resolved_by=like.*reported*&select=origem_ts&order=resolved_at.desc&limit=1`);
      if (rep.length && rep[0].origem_ts && ots <= rep[0].origem_ts) continue;
      const b = await contactBrief(cid);
      if ((b.tags || []).includes("teste-interno")) continue; // exceto durante aceite (config)
      await sb("POST", "board_cards", {
        coluna: map[0], kind: map[1], contact_id: cid, opportunity_id: o.id,
        nome: b.nome, veh: b.veh, interest: b.interest, phone: b.phone,
        origem: `${st} · since ${new Date(ots).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "America/New_York" })} (live)`,
        origem_ts: ots, closes_when: CLOSES[map[1]], stage: st });
      created++;
    }
  }
  return { closed, created };
}

async function handleReply(cid) {
  // Customer Replied → card col 1 (sms_reply) + fecha urable "no reply"
  // + REGRA CARL: resposta do cliente LIMPA o vermelho SEM RESOLUÇÃO na hora
  const b = await contactBrief(cid);
  let created = 0, closed = 0;
  await sb("PATCH", `board_cards?contact_id=eq.${cid}&status=eq.open&unres=eq.true`,
    { unres: false, unres_call_ts: null });
  // regra Greg/Coleen: cortesia/misdial não cobra ação; appointment futuro vence a col 1
  const NO_ACTION = ["thank you", "thanks", "thank u", "ok", "okay", "sounds good",
    "perfect", "great", "got it", "no worries", "misdial", "miss dial", "wrong number",
    "by accident", "no thanks", "all set", "👍", "🙏"];
  const cs0 = await ghl("/conversations/search", { locationId: LOC, contactId: cid });
  const conv0 = cs0?.conversations?.[0];
  if (conv0) {
    const mj0 = await ghl(`/conversations/${conv0.id}/messages`);
    const msgs0 = (mj0?.messages?.messages || []).filter((m) => m.messageType === "TYPE_SMS");
    const last0 = msgs0.sort((a, b) => (a.dateAdded < b.dateAdded ? 1 : -1))[0];
    const body = ((last0 && last0.direction === "inbound" && last0.body) || "").trim().toLowerCase();
    if (body && body.length <= 60 && NO_ACTION.some((p) => body.includes(p))) {
      // regra Coleen (report 08/jul): cortesia/misdial TAMBÉM resolve a chamada
      // perdida — o próprio cliente explicou, não precisa retornar
      const mi = await sb("GET",
        `board_cards?status=eq.open&contact_id=eq.${cid}&kind=in.(missed_inbound,sms_reply)&select=id`);
      for (const m of mi) {
        await sb("PATCH", `board_cards?id=eq.${m.id}`, {
          status: "resolved", resolved_by: "client replied — misdial/courtesy, no action needed (webhook)",
          resolved_at: new Date().toISOString(), unres: false });
        closed++;
      }
      return { created: 0, closed, skipped: "courtesy reply" };
    }
  }
  const aj = await ghl(`/contacts/${cid}/appointments`);
  const hasAppt = (aj?.events || []).some((e) => {
    const st = new Date(e.startTime).getTime();
    return !isNaN(st) && st > Date.now() - 3 * 3600e3 &&
      !["cancelled", "invalid", "noshow"].includes(e.appointmentStatus);
  });
  if (hasAppt) return { created: 0, closed: 0, skipped: "has upcoming appointment" };
  const dup = await sb("GET",
    `board_cards?status=eq.open&contact_id=eq.${cid}&kind=eq.sms_reply&select=id&limit=1`);
  if (!dup.length) {
    await sb("POST", "board_cards", {
      coluna: 1, kind: "sms_reply", contact_id: cid,
      nome: b.nome, veh: b.veh, interest: b.interest, phone: b.phone,
      origem: `SMS awaiting reply · last msg is theirs, ${new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" })} (live)`,
      origem_ts: new Date().toISOString(), closes_when: CLOSES.sms_reply });
    created++;
  }
  const ur = await sb("GET",
    `board_cards?status=eq.open&contact_id=eq.${cid}&kind=eq.urable&select=id`);
  for (const u of ur) {
    await sb("PATCH", `board_cards?id=eq.${u.id}`, {
      status: "resolved", resolved_by: "customer replied (webhook)",
      resolved_at: new Date().toISOString() });
    closed++;
  }
  return { created, closed };
}

async function handleAppt(cid) {
  // Booked / Status changed → espelho col 5 do contato (próximos 2 dias)
  const j = await ghl(`/contacts/${cid}/appointments`);
  const evs = j?.events || [];
  const now = Date.now();
  const b = await contactBrief(cid);
  let created = 0, closed = 0;
  // regra Peter (08/jul): appointment futuro fecha NA HORA os cards de prioridade
  // do contato — o lead vive na coluna 5 (Hot/New/Pipeline/perdida/SMS somem).
  const hasUpcoming = evs.some((e) => {
    const st = new Date(e.startTime).getTime();
    return !isNaN(st) && st > now - 3 * 3600e3 &&
      !["cancelled", "invalid", "noshow"].includes(e.appointmentStatus);
  });
  if (hasUpcoming) {
    const pri = await sb("GET",
      `board_cards?status=eq.open&contact_id=eq.${cid}` +
      `&kind=in.(hot,new_lead,pipeline,missed_inbound,sms_reply,urable,warmup,` +
      `followup_notask,quote_notask,uncategorized)&select=id`);
    for (const p of pri) {
      await sb("PATCH", `board_cards?id=eq.${p.id}`, {
        status: "resolved", resolved_by: "appointment booked — lives in Appointments (webhook)",
        resolved_at: new Date().toISOString(), unres: false });
      closed++;
    }
  }
  for (const e of evs) {
    const st = new Date(e.startTime).getTime();
    if (isNaN(st) || st < now - 3 * 3600e3 || st > now + 2 * 86400e3) continue;
    const status = e.appointmentStatus;
    if (["cancelled", "invalid", "noshow"].includes(status)) continue;
    const kind = status === "confirmed" ? "appt_info" : "appt_confirm";
    if (status === "confirmed") {
      const pend = await sb("GET",
        `board_cards?status=eq.open&contact_id=eq.${cid}&kind=eq.appt_confirm&select=id`);
      for (const p of pend) {
        await sb("PATCH", `board_cards?id=eq.${p.id}`, {
          status: "resolved", resolved_by: "confirmed (webhook)",
          resolved_at: new Date().toISOString() });
        closed++;
      }
    }
    const dup = await sb("GET",
      `board_cards?status=eq.open&contact_id=eq.${cid}&kind=eq.${kind}&select=id&limit=1`);
    if (!dup.length) {
      await sb("POST", "board_cards", {
        coluna: 5, grupo: status === "confirmed" ? "confirmed" : "to_confirm",
        kind, contact_id: cid, event_id: e.id, appt_start: e.startTime,
        nome: b.nome, veh: b.veh, interest: b.interest, phone: b.phone,
        origem: `Appointment ${new Date(e.startTime).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York" })} · ${status === "confirmed" ? "confirmed" : "not confirmed"} (live)`,
        origem_ts: new Date().toISOString(),
        closes_when: kind === "appt_confirm" ? CLOSES.appt_confirm : null });
      created++;
    }
  }
  return { created, closed };
}

async function handleCall(cid) {
  // Call Status → perdida inbound vira card col 1 na hora (detalhes ficam p/ delta/CI)
  const cs = await ghl("/conversations/search", { locationId: LOC, contactId: cid });
  const conv = cs?.conversations?.[0];
  if (!conv) return { created: 0 };
  const mj = await ghl(`/conversations/${conv.id}/messages`);
  const msgs = mj?.messages?.messages || [];
  const calls = msgs.filter((m) => m.messageType === "TYPE_CALL")
    .sort((a, b) => (a.dateAdded < b.dateAdded ? 1 : -1));
  const last = calls[0];
  if (!last) return { created: 0 };
  const dur = last.meta?.call?.duration || 0;
  if (last.direction === "inbound" && dur < 20) {
    // report Rafael 08/jul: appointment futuro vence a chamada perdida
    const aj2 = await ghl(`/contacts/${cid}/appointments`);
    const hasAppt2 = (aj2?.events || []).some((e) => {
      const st2 = new Date(e.startTime).getTime();
      return !isNaN(st2) && st2 > Date.now() - 3 * 3600e3 &&
        !["cancelled", "invalid", "noshow"].includes(e.appointmentStatus);
    });
    if (hasAppt2) return { created: 0, skipped: "has upcoming appointment" };
    const dup = await sb("GET",
      `board_cards?status=eq.open&contact_id=eq.${cid}&kind=eq.missed_inbound&select=id&limit=1`);
    if (!dup.length) {
      const b = await contactBrief(cid);
      await sb("POST", "board_cards", {
        coluna: 1, kind: "missed_inbound", contact_id: cid,
        nome: b.nome, veh: b.veh, interest: b.interest, phone: b.phone,
        origem: `Missed inbound · called ${new Date(last.dateAdded).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" })}, no answer (live)`,
        origem_ts: last.dateAdded, closes_when: CLOSES.missed_inbound });
      return { created: 1 };
    }
  }
  return { created: 0 };
}

export async function POST(req) {
  const t0 = Date.now();
  const url = new URL(req.url);
  if (!process.env.SUPABASE_SERVICE_ROLE_KEY || !process.env.WEBHOOK_KEY) {
    return NextResponse.json({ ok: false, reason: "server env missing (SUPABASE_SERVICE_ROLE_KEY / WEBHOOK_KEY)" }, { status: 503 });
  }
  if (url.searchParams.get("key") !== process.env.WEBHOOK_KEY) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }
  const type = url.searchParams.get("type") || "stage";
  let body = {};
  try { body = await req.json(); } catch (_) { /* GHL manda form às vezes */ }
  const cid = body.contact_id || body.contactId || body.contact?.id || body.id ||
    url.searchParams.get("contact_id");
  if (!cid) return NextResponse.json({ ok: false, reason: "no contact id" }, { status: 400 });

  let result = {};
  try {
    if (type === "stage") {
      // índice do GHL demora a refletir o stage novo (caso Evangelist/Alejandro):
      // 1ª tentativa após 2.5s; se nada mudou, 2ª após +4s (total ≤8s)
      await new Promise((r) => setTimeout(r, 2500));
      result = await miniMirrorStage(cid);
      if (!result.closed && !result.created) {
        await new Promise((r) => setTimeout(r, 4000));
        result = await miniMirrorStage(cid);
        result.retried = true;
      }
    }
    else if (type === "reply") result = await handleReply(cid);
    else if (type === "appt") result = await handleAppt(cid);
    else if (type === "call") result = await handleCall(cid);
    else result = await miniMirrorStage(cid);
  } catch (e) {
    await sb("POST", "config?on_conflict=key", { key: "board_live_error",
      value: { at: new Date().toISOString(), type, error: String(e).slice(0, 200) } },
      { Prefer: "resolution=merge-duplicates" });
    return NextResponse.json({ ok: false, error: String(e).slice(0, 200) }, { status: 500 });
  }
  const latency = Date.now() - t0;
  await sb("POST", "ghl_events", { type, contact_id: cid, payload: body,
    handled: true, latency_ms: latency });
  await sb("POST", "config?on_conflict=key", { key: "board_live",
    value: { last_event: new Date().toISOString(), source: `push:${type}`, latency_ms: latency } },
    { Prefer: "resolution=merge-duplicates" });
  return NextResponse.json({ ok: true, type, ...result, latency_ms: latency });
}
