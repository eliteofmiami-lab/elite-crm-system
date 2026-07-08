"""
ACEITE DO TEMPO REAL (item 4 da missão) — mede com timestamps reais:
  A) push type=stage: card de stage órfão some em ≤5s (ingestão completa)
  B) push type=reply: card entra na coluna 1 em ≤5s
  C) delta: execução medida + cadência (60s ping + throttle 45s ⇒ pior caso ≤90s)
Usa o lead teste-interno. Roda DEPOIS que o Rafael colocar as 2 envs na Vercel.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
from brain import cards as sb  # noqa: E402

BASE = "https://elite-crm-panel.vercel.app"
KEY = "WldabAmdqGdnRn-ZMu2RHA64kpK1wijk"


def get_test_contact():
    rows = sb._sb("GET", "config?key=eq.test_contact_ids&select=value") or []
    ids = rows[0]["value"] if rows else []
    return ids[0] if ids else None


def wait_card(query, timeout_s=10):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if sb._sb("GET", query):
            return time.time() - t0
        time.sleep(0.4)
    return None


def main():
    cid = get_test_contact()
    if not cid:
        print("!! sem contato teste-interno no config.test_contact_ids")
        return
    print(f"lead teste-interno: {cid}")
    r = requests.post(f"{BASE}/api/ghl-event?type=stage&key={KEY}",
                      json={"contact_id": cid}, timeout=30)
    if r.status_code == 503:
        print("!! envs ainda não configuradas na Vercel (503) — rode após o PASSO 0 do guia")
        return

    # --- A) stage: card órfão criado de propósito → push deve fechá-lo ---
    sb._sb("POST", "board_cards", json={
        "coluna": 1, "kind": "hot", "contact_id": cid, "nome": "TESTE INTERNO",
        "origem": "HOT LEADS · aceite realtime", "origem_ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "stage": "HOT LEADS", "closes_when": "aceite"})
    t0 = time.time()
    r = requests.post(f"{BASE}/api/ghl-event?type=stage&key={KEY}",
                      json={"contact_id": cid}, timeout=30)
    dt_a = wait_card(f"board_cards?contact_id=eq.{cid}&kind=eq.hot&status=eq.resolved"
                     "&resolved_by=like.*webhook*&select=id&limit=1", 10)
    total_a = time.time() - t0
    print(f"A) STAGE MOVE → card fechado: endpoint {r.json().get('latency_ms')}ms · "
          f"fim-a-fim {total_a:.2f}s {'✅ ≤5s' if total_a <= 5 else '❌'}")

    # --- B) reply: card col 1 em ≤5s ---
    t0 = time.time()
    r = requests.post(f"{BASE}/api/ghl-event?type=reply&key={KEY}",
                      json={"contact_id": cid}, timeout=30)
    dt_b = wait_card(f"board_cards?contact_id=eq.{cid}&kind=eq.sms_reply&status=eq.open"
                     "&select=id&limit=1", 10)
    total_b = time.time() - t0
    print(f"B) SMS INBOUND → card col 1: endpoint {r.json().get('latency_ms')}ms · "
          f"fim-a-fim {total_b:.2f}s {'✅ ≤5s' if total_b <= 5 else '❌'}")

    # --- C) delta: execução medida ---
    t0 = time.time()
    r = requests.get(f"{BASE}/api/delta", timeout=60)
    dt_c = time.time() - t0
    j = r.json()
    print(f"C) DELTA: execução {dt_c:.2f}s ({j}) · cadência 60s + throttle 45s ⇒ "
          f"pior caso ~90s pro SMS outbound fechar card {'✅' if dt_c < 30 else '❌'}")

    # limpeza dos artefatos de teste
    sb._sb("PATCH", f"board_cards?contact_id=eq.{cid}&status=eq.open",
           json={"status": "resolved", "resolved_by": "aceite realtime (limpeza)"})
    print("cards de teste limpos.")


if __name__ == "__main__":
    main()
