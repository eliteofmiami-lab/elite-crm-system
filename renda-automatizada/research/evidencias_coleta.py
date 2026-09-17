#!/usr/bin/env python3
"""
Coleta do FILTRO ZERO — prova de existência de operações com receita (marketplaces de aquisição).
Roda no Mac. Baixa cada fonte de config/evidencias_fontes.json e salva texto/JSON datado em data/evidencias/.
Quando a página não traz listagens no HTML (JavaScript/login), avisa para coleta manual.

    python3 research/evidencias_coleta.py
"""
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "evidencias_fontes.json").read_text())
OUT = ROOT / "data" / "evidencias"
OUT.mkdir(parents=True, exist_ok=True)
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
MONEY = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?[kKmM])?")


def main():
    index = {}
    manual = []
    for f in CFG["fontes"]:
        req = urllib.request.Request(f["url"], headers={"User-Agent": UA, "Accept": "application/json, text/html;q=0.9"})
        rec = {"url": f["url"], "confianca": f["confianca"], "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read().decode("utf-8", errors="replace")
                rec["http_status"] = r.status
        except Exception as e:
            rec["erro"] = str(e)[:200]
            index[f["id"]] = rec
            manual.append(f)
            print(f"[ERR] {f['id']}: {rec['erro']}")
            continue
        if f["tipo"] == "api":
            try:
                data = json.loads(body)
                (OUT / f"{f['id']}_{today}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
                n = len(data.get("data", {}).get("listings", data.get("data", data if isinstance(data, list) else []))) if isinstance(data, (dict, list)) else 0
                rec["registros"] = n
                print(f"[OK ] {f['id']}: JSON com ~{n} registros")
            except json.JSONDecodeError:
                rec["erro"] = "não é JSON"
                (OUT / f"{f['id']}_{today}.txt").write_text(body[:200000])
                manual.append(f)
                print(f"[?? ] {f['id']}: resposta não é JSON (salva como texto)")
        else:
            text = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", body)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            (OUT / f"{f['id']}_{today}.txt").write_text(text[:300000])
            valores = MONEY.findall(text)
            rec["chars"] = len(text)
            rec["valores_monetarios_encontrados"] = len(valores)
            if len(text) < 3000 or len(valores) < 5:
                manual.append(f)
                print(f"[MAN] {f['id']}: página com pouco conteúdo estático ({len(text)} chars, {len(valores)} valores) → coleta manual")
            else:
                print(f"[OK ] {f['id']}: {len(text)} chars, {len(valores)} valores monetários no texto")
        index[f["id"]] = rec
    (OUT / f"index_{today}.json").write_text(json.dumps(index, indent=1, ensure_ascii=False))
    if manual:
        print("\nColeta manual necessária para:", ", ".join(m["id"] for m in manual))
        print("Instruções em research/EVIDENCIAS_MANUAL.md (10–15 min por marketplace).")


if __name__ == "__main__":
    main()
