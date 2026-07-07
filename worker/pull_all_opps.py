"""Puxa TODAS as oportunidades da location (paginado) — SOMENTE LEITURA.
Salva out/opps_all.json. Deduplica por id e para quando não há registro novo
(a API repete dados no fim da paginação — visto na prática)."""
import json
import ghl

LOC = ghl.LOCATION_ID
KEEP = ("id", "name", "pipelineId", "pipelineStageId", "status", "source",
        "createdAt", "updatedAt", "lastStageChangeAt", "monetaryValue", "contactId")


def main():
    seen = {}
    start_after = None
    start_after_id = None
    total = None
    pages = 0
    while True:
        p = {"location_id": LOC, "limit": 100}
        if start_after:
            p["startAfter"] = start_after
            p["startAfterId"] = start_after_id
        j = ghl.get_json("/opportunities/search", p)
        meta = j.get("meta", {})
        if total is None:
            total = meta.get("total")
            print("total reportado pela API:", total)
        batch = j.get("opportunities", [])
        new = 0
        for o in batch:
            if o["id"] in seen:
                continue
            new += 1
            slim = {k: o.get(k) for k in KEEP}
            c = o.get("contact") or {}
            slim["contact_name"] = c.get("name")
            slim["phone"] = c.get("phone")
            slim["tags"] = c.get("tags", [])
            seen[o["id"]] = slim
        pages += 1
        if pages % 10 == 0:
            print(f"  página {pages}: {len(seen)} únicos", flush=True)
        # condições de parada (à prova do loop infinito da API)
        if not batch or new == 0 or not meta.get("nextPageUrl"):
            break
        if total and len(seen) >= total:
            break
        start_after = meta.get("startAfter")
        start_after_id = meta.get("startAfterId")
    opps = list(seen.values())
    json.dump(opps, open("out/opps_all.json", "w"), ensure_ascii=False)
    print(f"OK: {len(opps)} oportunidades únicas em {pages} páginas -> out/opps_all.json")


if __name__ == "__main__":
    main()
