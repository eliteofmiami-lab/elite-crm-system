// DELTA 60–90s (PAINEL_DIARIO — camada 3): o navegador do painel pinga esta rota a
// cada 60s; ela cobre o que NÃO tem gatilho de webhook — SMS outbound manual (fecha
// sms_reply/urable/warm-up, valida tentativa pendente de SMS ≤10min) e tasks de cards
// abertos. Throttle server-side: roda no máximo 1×/45s (vários navegadores = 1 delta).
// ZERO escrita no GHL. Requer env: GHL_API_TOKEN · SUPABASE_SERVICE_ROLE_KEY.
import { NextResponse } from "next/server";

// rota GET dinâmica SEMPRE (sem cache da Vercel — bug pego no teste de aceite:
// resposta cacheada = delta nunca roda de verdade)
export const dynamic = "force-dynamic";

const GHL = "https://services.leadconnectorhq.com";
const LOC = "Ao5ER8XBg3AtCJMccesF";
const EUGENE = "EbVhbGHnGfuvbQurQoga";
const RAFAEL = ["7dYD2aALTReBpvw0YYCM", "AiqssnKwfohnWd7KBead"];

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
const userKey = (uid, src) => src === "workflow" ? "automation"
  : uid === EUGENE ? "eugene" : RAFAEL.includes(uid) ? "rafael" : "other";

export async function GET() {
  const t0 = Date.now();
  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json({ ok: false, reason: "env missing" }, { status: 503 });
  }
  // throttle compartilhado
  const liveRows = await sb("GET", "config?key=eq.board_live&select=value");
  const live = liveRows?.[0]?.value || {};
  if (live.last_delta && Date.now() - new Date(live.last_delta).getTime() < 45000) {
    return NextResponse.json({ ok: true, skipped: "throttled" });
  }
  const sinceMs = live.last_delta
    ? new Date(live.last_delta).getTime() - 120000 : Date.now() - 10 * 60000;

  // 1ª página de conversas (mais recentes) → eventos novos
  const cs = await ghl("/conversations/search",
    { locationId: LOC, limit: 40, sortBy: "last_message_date", sort: "desc" });
  const convs = (cs?.conversations || []).filter((c) => Number(c.lastMessageDate) >= sinceMs);
  let closed = 0, validated = 0;
  const today = new Date().toISOString().slice(0, 10);

  for (const cv of convs.slice(0, 25)) {
    const cid = cv.contactId;
    if (!cid) continue;
    const mj = await ghl(`/conversations/${cv.id}/messages`);
    const msgs = mj?.messages?.messages || [];
    const news = msgs.filter((m) => new Date(m.dateAdded).getTime() >= sinceMs);
    const outSms = news.filter((m) => m.messageType === "TYPE_SMS" &&
      m.direction === "outbound" && m.source !== "workflow");
    if (!outSms.length) continue;
    const who = userKey(outSms[0].userId, outSms[0].source);

    // fecha cards cuja resolução é SMS: sms_reply (reply sent) · urable · warm-up reativação
    const open = await sb("GET",
      `board_cards?status=eq.open&contact_id=eq.${cid}&kind=in.(sms_reply,urable,warmup)&select=id,kind,unres_call_ts,unres_call_answered`);
    for (const card of open) {
      const after = outSms.some((s) => !card.unres_call_ts ||
        new Date(s.dateAdded) > new Date(card.unres_call_ts));
      if (card.kind === "sms_reply" ||
          (card.kind === "warmup" && card.unres_call_ts && !card.unres_call_answered && after) ||
          (card.kind === "urable" && after && card.unres_call_ts)) {
        await sb("PATCH", `board_cards?id=eq.${card.id}`, {
          status: "resolved",
          resolved_by: card.kind === "sms_reply" ? "reply sent (delta)" : "reactivation SMS sent (delta)",
          resolved_user: who, resolved_at: new Date().toISOString(), unres: false });
        closed++;
      }
    }
    // valida tentativas pendentes de SMS ≤10min
    const pend = await sb("GET",
      `board_attempts?pending_sms=eq.true&contact_id=eq.${cid}&day=eq.${today}&select=call_id,call_ts,user_key`);
    for (const a of pend) {
      const winEnd = new Date(a.call_ts).getTime() + 10 * 60000;
      const hit = outSms.some((s) => userKey(s.userId, s.source) === a.user_key &&
        new Date(s.dateAdded).getTime() >= new Date(a.call_ts).getTime() &&
        new Date(s.dateAdded).getTime() <= winEnd);
      if (hit) {
        await sb("PATCH", `board_attempts?call_id=eq.${a.call_id}`,
          { valid: true, pending_sms: false });
        validated++;
      }
    }
  }
  const latency = Date.now() - t0;
  await sb("POST", "config?on_conflict=key", { key: "board_live",
    value: { ...live, last_delta: new Date().toISOString(),
      last_event: new Date().toISOString(), source: "delta", delta_ms: latency } },
    { Prefer: "resolution=merge-duplicates" });
  return NextResponse.json({ ok: true, convs: convs.length, closed, validated, latency_ms: latency });
}
