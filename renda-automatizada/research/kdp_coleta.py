#!/usr/bin/env python3
"""
Coleta 1B — Amazon KDP (páginas públicas da Amazon.com). Roda no Mac.

    python3 research/kdp_coleta.py            # todos os nichos de config/kdp_nichos.json
    python3 research/kdp_coleta.py sudoku     # só um nicho (id)

Para cada nicho: busca (2 páginas) → ASINs → página de cada produto → BSR, preço, nº de avaliações,
nota, data de publicação, nº de páginas, editora, autor, e se a página mostra declaração de IA.

Saída:
    data/kdp/raw/<nicho>/<ASIN>.html      HTML bruto (só local, não versionado)
    data/kdp/<nicho>_<data>.jsonl          um registro por título (versionado)
    data/kdp/debug/<nicho>_<ASIN>.txt      trecho de texto quando o parser não achou campos (para eu ajustar o parser)
    data/kdp/bloqueios.log                 quando a Amazon devolveu captcha/robô

Se a Amazon bloquear (captcha), o script para e explica a coleta manual. Nada aqui é estimado:
BSR→vendas/mês só será convertido no relatório, com calculadora pública citada e marcado como estimativa.
"""
import html
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "kdp_nichos.json").read_text())
OUT = ROOT / "data" / "kdp"
RAW = OUT / "raw"
DBG = OUT / "debug"
for d in (OUT, RAW, DBG):
    d.mkdir(parents=True, exist_ok=True)
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/17.5 Safari/605.1.15")
CAPTCHA_MARKERS = ("Enter the characters you see below", "api-services-support@amazon.com", "Type the characters you see in this image")


def get(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                                               "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    erro de rede: {e}")
        return None
    if any(m in body for m in CAPTCHA_MARKERS):
        with (OUT / "bloqueios.log").open("a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} CAPTCHA {url}\n")
        return "CAPTCHA"
    return body


def rx(pattern, text, flags=re.S | re.I, group=1):
    m = re.search(pattern, text, flags)
    return html.unescape(m.group(group)).strip() if m else None


def to_int(s):
    if not s:
        return None
    s = re.sub(r"[^\d]", "", s)
    return int(s) if s else None


def parse_product(asin: str, page: str) -> dict:
    d = {"asin": asin, "coletado_em": today, "url": f"{CFG['marketplace']}/dp/{asin}"}
    d["titulo"] = rx(r'id="productTitle"[^>]*>\s*([^<]+?)\s*<', page)
    d["autor"] = rx(r'class="author[^"]*">.*?<a[^>]*>([^<]+)</a>', page) or rx(r'contributorNameID=[^"]*"[^>]*>([^<]+)<', page)
    price = rx(r'id="corePrice[^"]*".*?class="a-offscreen">\$([\d.,]+)<', page) or rx(r'class="a-offscreen">\$([\d.,]+)<', page)
    d["preco_usd"] = float(price.replace(",", "")) if price else None
    d["bsr_livros"] = to_int(rx(r'#([\d,]+)\s+in\s+Books', page))
    subs = re.findall(r'#([\d,]+)\s+in\s+([^<(#]+?)\s*(?:\(|<)', page)
    d["bsr_subcategorias"] = [{"rank": to_int(r), "categoria": html.unescape(c).strip()} for r, c in subs if "Books" != c.strip()][:5]
    d["n_avaliacoes"] = to_int(rx(r'id="acrCustomerReviewText"[^>]*>\s*([\d,]+)', page))
    nota = rx(r'a-icon-alt">([\d.]+) out of 5 stars', page)
    d["nota"] = float(nota) if nota else None
    d["data_publicacao"] = (rx(r'Publication date\s*</span>\s*(?:</div>\s*<div[^>]*>\s*)?<span[^>]*>\s*([^<]+?)\s*<', page)
                            or rx(r'Publication date\s*:?\s*</span>\s*<span[^>]*>\s*([^<]+?)\s*<', page))
    d["paginas"] = to_int(rx(r'(\d+)\s+pages', page))
    d["editora"] = (rx(r'Publisher\s*</span>\s*(?:</div>\s*<div[^>]*>\s*)?<span[^>]*>\s*([^<]+?)\s*<', page)
                    or rx(r'Publisher\s*:?\s*</span>\s*<span[^>]*>\s*([^<]+?)\s*<', page))
    txt = re.sub(r"<[^>]+>", " ", page)
    d["declaracao_ia_visivel_na_pagina"] = bool(re.search(r"\bAI[- ]generated\b|generated (?:by|with|using) (?:AI|artificial intelligence)", txt, re.I))
    d["independently_published"] = bool(d.get("editora") and "independently" in d["editora"].lower())
    d["campos_faltando"] = [k for k in ("titulo", "preco_usd", "bsr_livros", "n_avaliacoes", "data_publicacao", "paginas") if d.get(k) is None]
    return d


def asins_from_search(page: str) -> list[str]:
    seen, out = set(), []
    for a in re.findall(r'data-asin="([A-Z0-9]{10})"', page):
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def coletar_nicho(n: dict):
    nid, termo = n["id"], n["busca"]
    print(f"\n== {nid}: '{termo}'")
    out = OUT / f"{nid}_{today}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["asin"] for l in out.read_text().splitlines() if l.strip()}
    asins = []
    for p in range(1, CFG["paginas_de_busca"] + 1):
        url = f"{CFG['marketplace']}/s?" + urllib.parse.urlencode({"k": termo, "i": "stripbooks", "page": p})
        page = get(url)
        if page == "CAPTCHA":
            return "CAPTCHA"
        if not page:
            continue
        (RAW / nid).mkdir(exist_ok=True)
        (RAW / nid / f"search_p{p}.html").write_text(page)
        found = asins_from_search(page)
        print(f"  busca p{p}: {len(found)} ASINs")
        asins += [a for a in found if a not in asins]
        time.sleep(CFG["pausa_segundos"] + random.random())
    if not asins:
        (DBG / f"{nid}_search.txt").write_text(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page or ""))[:20000])
        print("  nenhum ASIN encontrado — trecho salvo em data/kdp/debug para eu ajustar o parser")
        return "SEM_ASIN"
    for i, asin in enumerate(asins, 1):
        if asin in done:
            continue
        page = get(f"{CFG['marketplace']}/dp/{asin}")
        if page == "CAPTCHA":
            return "CAPTCHA"
        if not page:
            continue
        (RAW / nid / f"{asin}.html").write_text(page)
        d = parse_product(asin, page)
        d.update({"nicho": nid, "termo_busca": termo, "posicao_busca": i})
        if len(d["campos_faltando"]) >= 3:
            (DBG / f"{nid}_{asin}.txt").write_text(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))[:20000])
        with out.open("a") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
        print(f"  [{i:>2}/{len(asins)}] {asin} BSR={d['bsr_livros']} ${d['preco_usd']} aval={d['n_avaliacoes']} pág={d['paginas']} {'faltando:'+','.join(d['campos_faltando']) if d['campos_faltando'] else ''}")
        time.sleep(CFG["pausa_segundos"] + random.random() * 2)
    return "OK"


def main(argv):
    nichos = [n for n in CFG["nichos"] if not argv or n["id"] in argv]
    for n in nichos:
        r = coletar_nicho(n)
        if r == "CAPTCHA":
            print("\n!! A Amazon pediu captcha (bloqueio de robô). O que fazer:\n"
                  "   1. Espere 1–2 horas e rode de novo: python3 research/kdp_coleta.py\n"
                  "   2. Se repetir, coleta manual: abra no Safari a busca do nicho na Amazon, e para os 20 primeiros livros\n"
                  "      anote em research/KDP_MANUAL.md: título, preço, BSR em Books, nº de avaliações, data de publicação, páginas.\n"
                  "   Registro do bloqueio em data/kdp/bloqueios.log")
            break
    n_reg = sum(1 for f in OUT.glob("*.jsonl") for _ in f.read_text().splitlines())
    print(f"\nRegistros KDP acumulados: {n_reg} em data/kdp/")


if __name__ == "__main__":
    main(sys.argv[1:])
