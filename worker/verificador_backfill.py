"""MVP item 6 — passa o verificador pós-call nas calls JÁ analisadas dos últimos
N dias (padrão 10) e roda um sweep de resoluções. Só leitura no GHL + pendencias
no Supabase. Uso: python worker/verificador_backfill.py [dias]"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
import ghl  # noqa: E402
from brain import cards, rules, verificador  # noqa: E402


def main(days=10):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat()
    rows = cards._sb("GET", ("analyses?select=call_id,payload,"
                             "calls!inner(contact_id,direction,duration_sec,called_at,dialed_number)"
                             f"&calls.called_at=gte.{since}&limit=600")) or []
    print(f"calls analisadas ({days}d): {len(rows)}")
    n_new = 0
    contacts = {}
    for i, r in enumerate(rows, 1):
        c = r["calls"]
        cid = c["contact_id"]
        if cid not in contacts:
            cr = ghl.get(f"/contacts/{cid}")
            contact = cr.json().get("contact", {}) if cr.status_code == 200 else {}
            opr = ghl.get("/opportunities/search", {"location_id": ghl.LOCATION_ID,
                                                    "contact_id": cid, "limit": 5})
            opps = opr.json().get("opportunities", []) if opr.status_code == 200 else []
            opp = next((o for o in opps if o.get("status") == "open"),
                       opps[0] if opps else None)
            contacts[cid] = (contact, opp)
        contact, opp = contacts[cid]
        if "teste-interno" in (contact.get("tags") or []):
            continue
        msg = {"id": r["call_id"], "contactId": cid, "dateAdded": c.get("called_at"),
               "meta": {"call": {"duration": c.get("duration_sec")}},
               "direction": c.get("direction")}
        try:
            n_new += verificador.check_call(msg, contact, opp, r["payload"])
        except Exception as e:
            print(f"  [warn] {r['call_id']}: {str(e)[:60]}")
        if i % 50 == 0:
            print(f"  {i}/{len(rows)} · {n_new} pendências")
    print(f"pendências novas: {n_new}")
    resolved = verificador.sweep_resolutions(limit=400)
    print(f"resolvidas no sweep imediato: {resolved}")
    open_now = cards._sb("GET", "pendencias?status=eq.open&select=id") or []
    print(f"abertas agora: {len(open_now)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
