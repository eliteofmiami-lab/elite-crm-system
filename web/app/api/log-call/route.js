// Write-through do formulário "Log call details" → GHL (custom fields + nota).
// Requer env no servidor (Vercel): GHL_API_TOKEN. Sem ela → 503 e o worker
// sincroniza via manual_logs em ≤5 min. Escrita iniciada pelo USUÁRIO (não é o cérebro).
import { NextResponse } from "next/server";

const GHL = "https://services.leadconnectorhq.com";
const CF_INTERESSE = "D5TgphY9HlZMoS8wcWj1";
const CF_VEH = {
  make: "CiRd678lAFn854igklGR",
  model: "LHwTnTb8TPz5BbJ0I2XV",
  year: "C01IzbXlbESCLfhoHkrZ",
};
const LABELS = [
  ["outcome", "Outcome"], ["make", "Make"], ["model", "Model"], ["year", "Year"],
  ["momento", "Car timing"], ["garaged", "Garaged or street"], ["arrival", "Car arrival"],
  ["motivation", "Main motivation"], ["service_interest", "Service interest"], ["interest", "Interest"],
  ["keep_or_trade", "Keep or trade"], ["seen_other_quotes", "Seen other quotes"],
  ["other_quotes_detail", "Other quotes detail"], ["lost_reason", "Lost reason"],
  ["prices", "Prices discussed"],
  ["hook", "Personal note"], ["next_step", "Next step"], ["next_date", "When"],
  ["notes", "Notes"],
];

export async function POST(req) {
  const token = process.env.GHL_API_TOKEN;
  if (!token) {
    return NextResponse.json({ ok: false, reason: "no-server-cred" }, { status: 503 });
  }
  // autenticação: valida o JWT do Supabase do usuário logado
  const auth = req.headers.get("authorization") || "";
  const u = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/auth/v1/user`, {
    headers: { apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, Authorization: auth },
  });
  if (!u.ok) return NextResponse.json({ ok: false }, { status: 401 });
  const user = await u.json();

  const { contact_id, fields } = await req.json();
  if (!contact_id || !fields) return NextResponse.json({ ok: false }, { status: 400 });

  const H = {
    Authorization: `Bearer ${token}`,
    Version: "2021-07-28",
    "Content-Type": "application/json",
  };
  const cfs = ["make", "model", "year"]
    .filter((k) => fields[k])
    .map((k) => ({ id: CF_VEH[k], field_value: fields[k] }));
  if (fields.service_interest) cfs.push({ id: CF_INTERESSE, field_value: fields.service_interest });
  if (cfs.length) {
    const r1 = await fetch(`${GHL}/contacts/${contact_id}`, {
      method: "PUT", headers: H, body: JSON.stringify({ customFields: cfs }),
    });
    if (!r1.ok) return NextResponse.json({ ok: false, step: "cf" }, { status: 502 });
  }
  const nota = ["📋 CALL LOG (manual — painel)"];
  for (const [k, lab] of LABELS) if (fields[k]) nota.push(`${lab}: ${fields[k]}`);
  nota.push(`— logged by ${user.email} via panel`);
  const r2 = await fetch(`${GHL}/contacts/${contact_id}/notes`, {
    method: "POST", headers: H, body: JSON.stringify({ body: nota.join("\n") }),
  });
  if (!r2.ok) return NextResponse.json({ ok: false, step: "note" }, { status: 502 });
  return NextResponse.json({ ok: true });
}
