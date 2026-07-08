"""
M4 — Relatório de fim de dia (18:30 ET) + motor da quinzena/bônus + payouts.
Grava na tabela `reports` (painel exibe) e exporta .md em docs/reports/.
Tudo em America/New_York. Contatos teste-interno ficam fora (os dados deles
não entram em calls/commissions por causa dos guards do ciclo).
"""
import calendar
import datetime as dt
import json
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ghl  # noqa: E402

ET = ZoneInfo("America/New_York")
SB = os.environ.get("SUPABASE_URL", "").strip()
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
ROOT = Path(__file__).resolve().parent.parent.parent


def q(path):
    r = requests.get(f"{SB}/rest/v1/{path}", headers=H, timeout=20)
    return r.json() if r.status_code == 200 else []


def period_of(day_et):
    tag = "A" if day_et.day <= 15 else "B"
    return f"{day_et:%Y-%m}{tag}"


def detect_critical_misses(today_iso, open_cards):
    """Critérios A5 mensuráveis hoje (v1). Retorna lista de strings."""
    misses = []
    # 1. lead novo sem NENHUMA tentativa o dia todo (first_touch aberto criado antes de hoje... ou hoje e ainda aberto no EOD)
    ft = [c for c in open_cards if c["type"] == "first_touch"]
    if ft:
        misses.append(f"{len(ft)} new lead(s) ended the day with zero contact attempts")
    # 2. appointment nas próximas 48h sem confirmação no fim do dia
    ap = [c for c in open_cards if c["type"] == "confirm_appt"]
    if ap:
        misses.append(f"{len(ap)} appointment(s) in the next 2 days left unconfirmed")
    # 3. 80+ órfão 24h+
    for c in open_cards:
        if (c.get("score") or 0) >= 80:
            age = (dt.datetime.now(dt.timezone.utc)
                   - dt.datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600
            if age >= 24:
                misses.append(f"Score-{c['score']} lead orphaned 24h+: {c['title'][:40]}")
    # 4. 3+ snoozes no dia (proxy dos adiamentos rejeitados — refinamento na F2)
    snoozed_today = q(f"cards?status=eq.snoozed&select=id&limit=20")
    if len(snoozed_today) >= 3:
        misses.append(f"{len(snoozed_today)} tasks snoozed (review reasons)")
    return misses


def main():
    now = dt.datetime.now(ET)
    today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    iso = today0.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    month0 = today0.replace(day=1).astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    done = q(f"cards?status=eq.done&closed_at=gte.{iso}&select=*")
    open_cards = q("cards?status=eq.open&select=*")
    wrapups = q("cards?status=eq.wrapup&select=id")
    calls = q(f"calls?called_at=gte.{iso}&select=*")
    analyses = q(f"analyses?created_at=gte.{iso}&select=payload,calls(contact_id)&order=created_at.desc")
    comms_month = q(f"commissions?booked_at=gte.{month0}&select=*")
    costs_month = q(f"cost_log?created_at=gte.{month0}&select=est_usd")
    cfg_rows = q("config?key=in.(stats_today,bonus_guard)&select=key,value")
    cfg = {r["key"]: r["value"] for r in cfg_rows}

    calls_out = sum(1 for c in calls if c.get("direction") == "outbound")
    calls_in = sum(1 for c in calls if c.get("direction") == "inbound")
    quotes_done = sum(1 for c in done if c["type"] == "quote_followup")
    comm_today = [c for c in comms_month if (c.get("booked_at") or "") >= iso]
    conf_sum = sum(float(c["amount_usd"]) for c in comms_month if c["status"] == "confirmado")
    pot_sum = sum(float(c["amount_usd"]) for c in comms_month if c["status"] == "potencial")
    cost_sum = round(sum(float(c["est_usd"]) for c in costs_month), 2)
    advices = [(a["payload"].get("advice_en"), a["payload"].get("advice_pt"),
                (a.get("calls") or {}).get("contact_id"))
               for a in analyses if a.get("payload", {}).get("advice_en")]

    # transferências (heurística: 2 calls mesmo contato, userId diferente, <30min)
    transfers = []
    by_contact = {}
    for c in sorted(calls, key=lambda x: x.get("called_at") or ""):
        by_contact.setdefault(c["contact_id"], []).append(c)
    for cid, lst in by_contact.items():
        for a, b in zip(lst, lst[1:]):
            if a.get("user_id") and b.get("user_id") and a["user_id"] != b["user_id"]:
                t1 = dt.datetime.fromisoformat(a["called_at"].replace("Z", "+00:00"))
                t2 = dt.datetime.fromisoformat(b["called_at"].replace("Z", "+00:00"))
                if (t2 - t1).total_seconds() < 1800:
                    transfers.append(cid)

    misses = detect_critical_misses(iso, open_cards)
    period = period_of(now)

    # ---- quinzena: acumula misses do dia ----
    key = f"critical_misses_{period}"
    prev = q(f"config?key=eq.{key}&select=value")
    hist = prev[0]["value"] if prev else []
    if misses:
        hist.append({"date": f"{now:%Y-%m-%d}", "misses": misses})
    requests.post(f"{SB}/rest/v1/config",
                  headers={**H, "Prefer": "resolution=merge-duplicates"},
                  json={"key": key, "value": hist}, timeout=15)
    # estado do bônus p/ o painel (on track / lost this period)
    bonus_state = ({"status": "lost", "motivo": hist[0]["misses"][0][:80],
                    "date": hist[0]["date"], "period": period,
                    "next_start": "day 16" if period.endswith("A") else "day 1 next month"}
                   if hist else {"status": "on_track", "period": period})
    requests.post(f"{SB}/rest/v1/config",
                  headers={**H, "Prefer": "resolution=merge-duplicates"},
                  json={"key": "bonus_state", "value": bonus_state}, timeout=15)

    # ---- payout no dia 15 e no último dia ----
    last_day = calendar.monthrange(now.year, now.month)[1]
    if now.day in (15, last_day):
        p_start = today0.replace(day=1 if now.day == 15 else 16)
        p_start_iso = p_start.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        conf_period = sum(float(c["amount_usd"]) for c in comms_month
                          if c["status"] == "confirmado" and (c.get("resolved_at") or "") >= p_start_iso)
        bonus = 50 if not hist else 0
        requests.post(f"{SB}/rest/v1/payouts",
                      headers={**H, "Prefer": "resolution=merge-duplicates"},
                      json={"period": period, "user_email": "eugenebaruelova@gmail.com",
                            "commissions_usd": conf_period, "bonus_usd": bonus,
                            "critical_misses": hist,
                            "detail": {"generated": now.isoformat()}}, timeout=15)

    # ---- relatório EUGENE (EN) ----
    e = [f"# Daily report — Eugene · {now:%A, %b %d}", ""]
    e.append(f"**Today:** {calls_out} calls out · {calls_in} in · {len(done)} tasks closed · {quotes_done} quote follow-ups done")
    e.append(f"**Earnings:** +${sum(float(c['amount_usd']) for c in comm_today):.0f} booked today · ${conf_sum:.0f} confirmed this month · ${pot_sum:.0f} potential")
    e.append(f"**Bonus:** {'⚠️ at risk — ' + '; '.join(misses) if misses else '✅ on track — zero critical misses today'}")
    pend = [c for c in open_cards if c["layer"] in (1, 2)][:8]
    e.append("\n## Still pending (why it matters)")
    e += [f"- {c['title']} — {(c['why'] or '')[:80]}" for c in pend] or ["- Nothing! Clean board."]
    if wrapups:
        e.append(f"\n⚠️ {len(wrapups)} call(s) missing the nice-to-talk wrap-up — approve them first thing.")
    e.append("\n## Top advice from today's calls")
    e += [f"- {a[0]}" for a in advices[:3]] or ["- No analyzed calls today."]
    eugene_md = "\n".join(e)

    # ---- relatório RAFAEL (EN) ----
    f = cfg.get("stats_today", {}).get("funil", {})
    r = [f"# Owner report · {now:%A, %b %d}", ""]
    r.append(f"**Funnel today:** new {f.get('novos','—')} → hot {f.get('hot','—')} → qualified {f.get('qualificados','—')} → quotes {f.get('quotes','—')} → appts {f.get('appointments','—')} → win {f.get('win','—')}")
    r.append(f"**Activity:** {calls_out} calls out · {calls_in} in · {len(done)} tasks closed · {len(transfers)} transfer(s) detected")
    r.append(f"**Eugene money:** ${conf_sum:.0f} confirmed · ${pot_sum:.0f} potential · bonus {period}: {'❌ misses hoje' if misses else '✅ clean day'}")
    r.append(f"**AI cost month-to-date:** ${cost_sum:.2f}" + (" ⚠️ OVER $150 CEILING" if cost_sum > 150 else " (teto $150)"))
    r.append("\n## Audited goals")
    r.append(f"- Zero-contact new leads at EOD: {'❌ ' + str(len([c for c in open_cards if c['type']=='first_touch'])) if any('new lead' in m for m in misses) else '✅'}")
    r.append(f"- Appointments confirmed: {'❌' if any('appointment' in m for m in misses) else '✅'}")
    r.append(f"- No 80+ orphans: {'❌' if any('orphaned' in m for m in misses) else '✅'}")
    r.append(f"- Quotes worked today: {'✅ ' + str(quotes_done) if quotes_done else '—'}")
    r.append("\n## Calls & advice")
    r += [f"- {a[0]}" for a in advices[:6]] or ["- No analyzed calls today."]
    if misses:
        r.append("\n## ⚠️ Critical misses today")
        r += [f"- {m}" for m in misses]
    # A10.4: briefing pré-venda das visitas de AMANHÃ (config.visit_briefing)
    vb_rows = q("config?key=eq.visit_briefing&select=value")
    visits = (vb_rows[0]["value"].get("visits", []) if vb_rows else [])
    tomorrow = f"{(now + dt.timedelta(days=1)):%Y-%m-%d}"
    tv = [v for v in visits if str(v.get("start", ""))[:10] == tomorrow]
    if tv:
        r.append("\n## 🏪 Tomorrow's visits — pre-sale briefing")
        for v in tv:
            hh = str(v.get("start", ""))[11:16]
            precos = "; ".join(f"{p['servico']} {p['valor']} ({p['date']})"
                               for p in v.get("precos_falados", [])) or "no prices discussed yet"
            r.append(f"- **{hh} {v.get('name')}** · {v.get('vehicle') or 'car ?'}"
                     f"{' (' + v['tier'] + ')' if v.get('tier') else ''}"
                     f"{' · 🏪 visited before' if v.get('visited_store') else ''}")
            r.append(f"  - Looking for: {(v.get('interest') or {}).get('value', '?')} · "
                     f"sentiment: {v.get('sentiment') or '—'} · prices said: {precos}")
            if v.get("upsells"):
                r.append(f"  - Upsell angle: {' · '.join(v['upsells'])}")
    rafael_md = "\n".join(r)

    # grava no banco + exporta .md
    for aud, md in (("eugene", eugene_md), ("rafael", rafael_md)):
        requests.post(f"{SB}/rest/v1/reports",
                      headers={**H, "Prefer": "resolution=merge-duplicates"},
                      json={"report_date": f"{now:%Y-%m-%d}", "audience": aud,
                            "content_md": md,
                            "metrics": {"calls_out": calls_out, "misses": misses,
                                        "cost_month": cost_sum}}, timeout=15)
        outdir = ROOT / "docs" / "reports"
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / f"{now:%Y-%m-%d}-{aud}.md").write_text(md)
    print(f"EOD ok · misses hoje: {len(misses)} · custo mês: ${cost_sum}")


if __name__ == "__main__":
    main()
