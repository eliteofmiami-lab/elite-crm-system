"""Score v2 para leads ATIVOS do New Pipeline que ainda não têm elite_score
(ex.: os 198 HOT LEADS migrados do legado). Extensão do G0-B já aprovado.
Grava o CF na opportunity + atualiza o score nos cards abertos do painel."""
import json
import os
import sys
import time
import datetime as dt

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import ghl  # noqa: E402
import score  # noqa: E402
from brain import rules, cards  # noqa: E402

c = config.load()
H = config.ghl_headers(c["GHL_API_TOKEN"])
H["Content-Type"] = "application/json"
CF = json.load(open("out/opportunity_customfields.json"))
STAGES_ATIVOS = ["HOT LEADS", "Great Cars", "New Lead", "Quote Sent",
                 "Appointment Booked", "Follow Up",
                 "Contact 1 (AM)", "Contact 1 (PM)", "Contact 2 (AM)", "Contact 2 (PM)"]


def messages_for(contact_id):
    r = ghl.get("/conversations/search", {"locationId": ghl.LOCATION_ID, "contactId": contact_id})
    msgs = []
    if r.status_code == 200:
        for cv in r.json().get("conversations", [])[:1]:
            m = ghl.get(f"/conversations/{cv['id']}/messages")
            if m.status_code == 200:
                msgs = m.json().get("messages", {}).get("messages", [])
    return msgs


def main():
    logf = open("out/write_log.jsonl", "a")
    done = failed = skipped = 0
    for stage in STAGES_ATIVOS:
        r = ghl.get("/opportunities/search",
                    {"location_id": ghl.LOCATION_ID, "pipeline_id": rules.NEW_PIPELINE_ID,
                     "pipeline_stage_id": rules.STAGES[stage], "limit": 100})
        if r.status_code != 200:
            continue
        opps = [o for o in r.json().get("opportunities", []) if o.get("status") == "open"]
        pend = [o for o in opps if cards.opp_score(o) is None]
        print(f"{stage}: {len(opps)} open, {len(pend)} sem score")
        for o in pend:
            msgs = messages_for(o["contactId"])
            s = score.compute(opp_name=o.get("name"), msgs=msgs)
            payload = {"customFields": [
                {"id": CF["Elite Score"]["id"], "field_value": s["known"]},
                {"id": CF["Elite Score Breakdown"]["id"], "field_value": s["breakdown"]},
            ]}
            for attempt in range(4):
                pr = requests.put(f"{config.GHL_BASE_URL}/opportunities/{o['id']}",
                                  headers=H, json=payload, timeout=30)
                if pr.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                break
            ok = pr.status_code == 200
            done += ok
            failed += (not ok)
            logf.write(json.dumps({
                "ts": dt.datetime.now(dt.UTC).isoformat(),
                "gate": "G0-B (extensão: leads ativos sem score)",
                "motivo": f"score {s['known']} p/ {o.get('name')!r} ({stage})",
                "method": "PUT", "url": f"/opportunities/{o['id']}",
                "status": pr.status_code, "dry_run": False}) + "\n")
            # espelha no card aberto (se houver)
            cards._sb("PATCH",
                      f"cards?status=eq.open&contact_id=eq.{o['contactId']}&score=is.null",
                      json={"score": s["known"]})
            if (done + failed) % 25 == 0:
                print(f"  ...{done + failed} processados", flush=True)
    logf.close()
    print(f"\nBACKFILL ATIVOS: {done} gravados, {failed} falhas, {skipped} pulados")


if __name__ == "__main__":
    main()
