// Registro de INATIVIDADE LONGA (report 09/jul): o board do Eugene chama quando fica
// ≥20min parado no horário comercial. Grava em inactivity_blocks (aparece na aba do
// Rafael) usando o service role — o cliente do Eugene não tem RLS de insert nessa tabela.
// Dedup server-side: 1 bloco por shift a cada ~25min. ZERO escrita no GHL.
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function sb(method, path, body) {
  const url = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/rest/v1/${path}`;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  return fetch(url, {
    method,
    headers: { apikey: key, Authorization: `Bearer ${key}`,
      "Content-Type": "application/json", Prefer: "return=representation" },
    body: body ? JSON.stringify(body) : undefined,
  }).then(async (r) => (r.status === 204 ? [] : r.json().catch(() => [])));
}

export async function POST(req) {
  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json({ ok: false, reason: "env missing" }, { status: 503 });
  }
  const b = await req.json().catch(() => ({}));
  if (!b.shift_id) return NextResponse.json({ ok: false, reason: "no shift" }, { status: 400 });
  const since = new Date(Date.now() - 25 * 60000).toISOString();
  const recent = await sb("GET",
    `inactivity_blocks?shift_id=eq.${b.shift_id}&started_at=gte.${since}&select=id`);
  if (Array.isArray(recent) && recent.length) {
    return NextResponse.json({ ok: true, skipped: "recent block exists" });
  }
  const r = await sb("POST", "inactivity_blocks", {
    shift_id: b.shift_id, queue_size: b.queue_size || null, nudges_sent: 3,
    started_at: b.started_at || new Date().toISOString() });
  return NextResponse.json({ ok: true, created: Array.isArray(r) ? r.length : 1 });
}
