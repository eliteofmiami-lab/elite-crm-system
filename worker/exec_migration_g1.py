"""GATE G1 — EXECUÇÃO da migração ELITE ADS → New Pipeline (aprovada pelo Rafael no chat).
Fonte da verdade: out/migration_dryrun.csv (o dry-run aprovado). Loga tudo em write_log.jsonl."""
import csv
import json
import time
import datetime as dt
import sys
import os

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from brain import rules  # noqa: E402

c = config.load()
H = config.ghl_headers(c["GHL_API_TOKEN"])
H["Content-Type"] = "application/json"
BASE = config.GHL_BASE_URL
LOGP = "out/write_log.jsonl"


def log(entry):
    entry["ts"] = dt.datetime.now(dt.timezone.utc).isoformat()
    entry["gate"] = "G1 (aprovado pelo Rafael no chat)"
    entry["dry_run"] = False
    with open(LOGP, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def req(method, url, payload, motivo):
    for attempt in range(4):
        r = requests.request(method, url, headers=H, json=payload, timeout=30)
        if r.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        break
    log({"motivo": motivo, "method": method, "url": url.replace(BASE, ""),
         "status": r.status_code})
    return r


def main():
    rows = list(csv.DictReader(open("out/migration_dryrun.csv")))
    migrate = [r for r in rows if r["decisão"] == "MIGRA"]
    dups = [r for r in rows if r["decisão"].startswith("TAG dup")]
    print(f"plano aprovado: {len(migrate)} migram, {len(dups)} recebem tag dup")

    moved = failed = 0
    for i, r in enumerate(migrate, 1):
        dest_id = rules.STAGES.get(r["stage_destino"])
        if not dest_id:
            print(f"  SEM MAPA: {r['stage_destino']} ({r['nome']})")
            failed += 1
            continue
        resp = req("PUT", f"{BASE}/opportunities/{r['opportunityId']}",
                   {"pipelineId": rules.NEW_PIPELINE_ID, "pipelineStageId": dest_id},
                   f"G1 migrar {r['nome']!r}: {r['stage_legado']} → {r['stage_destino']}")
        if resp.status_code == 200:
            moved += 1
            req("POST", f"{BASE}/contacts/{r['contactId']}/tags",
                {"tags": ["migrated-from-elite-ads"]},
                f"G1 tag migrated {r['nome']!r}")
        else:
            failed += 1
            print(f"  FALHA mover {r['nome']}: {resp.status_code} {resp.text[:100]}")
        if i % 25 == 0:
            print(f"  ...{i}/{len(migrate)} (ok={moved})", flush=True)

    tagged = 0
    for i, r in enumerate(dups, 1):
        resp = req("POST", f"{BASE}/contacts/{r['contactId']}/tags",
                   {"tags": ["dup-elite-ads"]}, f"G1 tag dup {r['nome']!r}")
        tagged += resp.status_code in (200, 201)
        if i % 25 == 0:
            print(f"  ...dups {i}/{len(dups)}", flush=True)

    print(f"\nMIGRAÇÃO G1: {moved} movidas, {failed} falhas, {tagged}/{len(dups)} dups etiquetadas")


if __name__ == "__main__":
    main()
