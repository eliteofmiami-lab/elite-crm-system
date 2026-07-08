"""
COMPRESSÃO DE PRAZO (ordem do Rafael): batch lento → sínteses SÍNCRONAS só para os
leads que a fila de HOJE precisa (contatos com card aberto nas Camadas 1 e 2).
A cauda (Camada 3 / demais elegíveis) fica para o batch em segundo plano.
"""
import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
from brain import cards, lead_state, score_engine, analyze  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HOJE = f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}"


def log(m):
    print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)


def main():
    oc = cards._sb("GET", "cards?status=eq.open&select=contact_id,layer") or []
    l12 = sorted({c["contact_id"] for c in oc if c["layer"] in (1, 2)})
    # pula quem já tem estado sintetizado HOJE (os 5 do gabarito etc.)
    fresh = {r["contact_id"] for r in
             (cards._sb("GET", f"lead_states?computed_at=gte.{HOJE}&select=contact_id") or [])}
    todo = [c for c in l12 if c not in fresh]
    est = len(todo) * 0.04
    log(f"L1/L2 abertos: {len(l12)} contatos · já com estado de hoje: {len(l12) - len(todo)}"
        f" · a sintetizar síncrono: {len(todo)} (~${est:.2f})")

    done = fail = 0
    spend = 0.0
    dist = {}

    def one(cid):
        state, usd = lead_state.synthesize(cid)
        lead_state.apply_state(cid, state)
        score_engine.compute_for(cid)
        return cid, state.get("situacao"), usd

    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(one, cid): cid for cid in todo}
        for n, fut in enumerate(as_completed(futs), 1):
            try:
                cid, sit, usd = fut.result()
                spend += usd
                dist[sit or "?"] = dist.get(sit or "?", 0) + 1
                done += 1
            except Exception as e:
                fail += 1
                log(f"  [warn] {futs[fut]}: {str(e)[:70]}")
            if n % 25 == 0:
                log(f"  {n}/{len(todo)} · ${spend:.2f}")
    log(f"sínteses L1/L2: {done} ok, {fail} falhas · ${spend:.2f} · situações: {dist}")
    stats = cards.sync_all()
    log(f"fila: {stats}")
    json.dump({"synth": done, "situacoes": dist, "spend_usd": round(spend, 2),
               "mode": "compress-L1L2", "tail": "batch em segundo plano",
               "finished": dt.datetime.now(dt.timezone.utc).isoformat()},
              open(ROOT / "out" / "mvp_result.json", "w"), indent=2)
    log("== compressão concluída ==")


if __name__ == "__main__":
    main()
