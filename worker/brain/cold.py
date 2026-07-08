"""
M5 — Cold calls (Camada 3), ranqueadas.
Pool: Lost do New Pipeline + no-shows + legado (HOT LEADS restante, NEVER ANSWERED).
Fora: NOT INTERESTED, delete/spam, Win, teste-interno (guard na criação do card).
Rank = score_base × fator_recência × peso do ponto onde a conversa morreu.
Refresh semanal; a fila mantém a Camada 3 abastecida quando 1 e 2 estão baixas.
"""
import datetime as dt
import os

import requests

import ghl
import score as score_mod
from brain import rules, cards

SB_URL = os.environ.get("SUPABASE_URL", "").strip()
SB_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}",
     "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}

ADS = "gxSzYT8gC2sYY1QrXnDZ"
LEGACY_STAGES = {  # ids do recon (não migrados; por referência, sem mover nada)
    "HOT LEADS": "67a737b5-cf27-4d96-8a33-01fb55fccd97",
    "NEVER ANSWERED - REMARKETING": "1c5dfd32-7f12-403c-817f-06462c390f9d",
}
WEIGHT = {"no_show": 1.5, "quote_no_reply": 1.4, "replied_ghosted": 1.2,
          "never_answered": 1.0, "lost": 1.1}


def _recency(created_iso):
    """decai de 1.0 (novo) até 0.4 (1 ano+)."""
    try:
        d = (dt.datetime.now(dt.timezone.utc)
             - dt.datetime.fromisoformat(created_iso.replace("Z", "+00:00"))).days
    except Exception:
        return 0.5
    return max(0.4, 1.0 - d / 500)


def _paginate(params, cap=1200):
    out, page = [], 1
    while len(out) < cap and page <= 15:
        r = ghl.get("/opportunities/search", {**params, "limit": 100, "page": page})
        if r.status_code != 200:
            break
        batch = r.json().get("opportunities", [])
        if not batch:
            break
        out += batch
        if not r.json().get("meta", {}).get("nextPage"):
            break
        page += 1
    return out


def refresh_pool():
    """Reconstrói o cold_pool (semanal)."""
    rows = {}

    def add(o, reason):
        cid = o.get("contactId")
        if not cid:
            return  # opp órfã (contato deletado no GHL) — fora do pool
        cs = cards.opp_score(o)
        if cs is None:
            cs, _ = score_mod.car_score(name=o.get("name"))
        rank = cs * _recency(o.get("createdAt") or "") * WEIGHT[reason]
        if cid not in rows or rank > rows[cid]["rank"]:
            rows[cid] = {"contact_id": cid, "opportunity_id": o["id"],
                         "name": (o.get("contact") or {}).get("name") or o.get("name"),
                         "phone": (o.get("contact") or {}).get("phone"),
                         "rank": round(rank, 2), "reason": reason, "base_score": cs}

    # Lost do New Pipeline (respondeu e sumiu = teve conversa; sem resposta = lost simples)
    for o in _paginate({"location_id": ghl.LOCATION_ID,
                        "pipeline_id": rules.NEW_PIPELINE_ID,
                        "pipeline_stage_id": rules.STAGES["Lost"]}):
        add(o, "lost")
    # Legado por referência
    for reason, sid in (("replied_ghosted", LEGACY_STAGES["HOT LEADS"]),
                        ("never_answered", LEGACY_STAGES["NEVER ANSWERED - REMARKETING"])):
        for o in _paginate({"location_id": ghl.LOCATION_ID, "pipeline_id": ADS,
                            "pipeline_stage_id": sid}):
            if o.get("status") in ("won",):
                continue
            add(o, reason)

    payload = list(rows.values())
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    for row in payload:
        row["refreshed_at"] = now
    # upsert em lotes
    for i in range(0, len(payload), 200):
        requests.post(f"{SB_URL}/rest/v1/cold_pool", headers=H,
                      json=payload[i:i + 200], timeout=30)
    requests.post(f"{SB_URL}/rest/v1/config", headers=H,
                  json={"key": "cold_pool_refreshed", "value": {"at": now, "n": len(payload)}},
                  timeout=15)
    return len(payload)


def maybe_weekly_refresh():
    r = requests.get(f"{SB_URL}/rest/v1/config?key=eq.cold_pool_refreshed&select=value",
                     headers=H, timeout=15)
    rows = r.json() if r.status_code == 200 else []
    if rows:
        last = dt.datetime.fromisoformat(rows[0]["value"]["at"].replace("Z", "+00:00"))
        if (dt.datetime.now(dt.timezone.utc) - last).days < 7:
            return 0
    return refresh_pool()


def top_up_queue(min_open=12, batch=5):
    """Se a fila (L1+L2+L3) estiver curta, puxa os melhores do pool p/ cards frios."""
    oc = cards.open_cards()
    if len(oc) >= min_open:
        return 0
    carded = {c["contact_id"] for c in oc}
    r = requests.get(f"{SB_URL}/rest/v1/cold_pool?select=*&order=rank.desc&limit=60",
                     headers={k: v for k, v in H.items() if k != "Prefer"}, timeout=15)
    n = 0
    for row in (r.json() if r.status_code == 200 else []):
        if n >= batch:
            break
        if row["contact_id"] in carded:
            continue
        made = cards.create_card(
            "cold_call", 3, row["contact_id"],
            f"Cold call — {row['name'] or 'lead'}",
            f"Rank {row['rank']} · died at: {row['reason'].replace('_', ' ')} · reopen via timing/new offer.",
            {"passos": ["Read the old notes first — reference the last conversation",
                        "Angle: new-season offer or 'is the car still unprotected?'",
                        "No answer: short SMS, move on"]},
            opportunity_id=row["opportunity_id"], score=row["base_score"])
        n += made is not None
    return n
