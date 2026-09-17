#!/usr/bin/env python3
"""
Coleta da Fase 1A (YouTube) — roda no Mac. Idempotente e resumível: pode rodar todo dia.

    python3 research/fase1_coleta.py tudo      # descoberta + canais + vídeos + uploads + derivar (respeita a quota)
    python3 research/fase1_coleta.py diario    # snapshot diário dos canais conhecidos (barato) + derivar
    python3 research/fase1_coleta.py status    # o que já foi coletado e quanto de quota foi gasta hoje

Etapas (cada uma grava em data/ e nunca refaz o que já está gravado):
  descobrir : search.list por categoria/idioma/janela (100 unidades cada) → data/discovery/*.jsonl
  canais    : channels.list de todos os canais descobertos → snapshot do dia (1 unidade por 50 canais)
  videos    : videos.list dos vídeos descobertos (estatísticas, duração, madeForKids) → data/videos/*.jsonl
  uploads   : últimos 50 uploads dos top canais por categoria (cadência, duração, Shorts) → data/uploads/*.jsonl
  derivar   : métricas por canal (medidas) + delta de views entre snapshots → data/derived/ e reports/coleta_resumo.md

Regra: nada aqui estima. O que a API não dá fica "sem dado".
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yt_client import YT, QuotaExceeded, DATA, SNAP  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config" / "categorias.json").read_text())
DISC = DATA / "discovery"
VIDS = DATA / "videos"
UPL = DATA / "uploads"
DER = DATA / "derived"
KNOWN = DATA / "canais_conhecidos.json"       # {channel_id: {"categorias": [...], "first_seen": "..."}}
RESERVA_UNIDADES = 1500                        # descoberta para quando sobrar só isso (deixa espaço p/ canais/vídeos)
TOP_CANAIS_UPLOADS = 12                        # por categoria
SHORTS_MAX_S = 180                             # heurística: ≤ 3 min = possível Short (rotulado como heurística)

for d in (DISC, VIDS, UPL, DER):
    d.mkdir(parents=True, exist_ok=True)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_jsonl(p: Path):
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def append_jsonl(p: Path, rows):
    with p.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_known():
    return json.loads(KNOWN.read_text()) if KNOWN.exists() else {}


def save_known(k):
    KNOWN.write_text(json.dumps(k, indent=1, ensure_ascii=False, sort_keys=True))


def iso_dur_to_s(d: str) -> int | None:
    if not d:
        return None
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d)
    if not m:
        return None
    dd, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


# ---------------------------------------------------------------- descobrir
def descobrir(yt: YT):
    known = load_known()
    feitas = pulos = 0
    for cat in CFG["categorias"]:
        for lang, queries in cat["buscas"].items():
            loc = CFG["idiomas"][lang]
            for q in queries:
                for jan, dias in CFG["janelas"].items():
                    slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")[:60]
                    out = DISC / f"{cat['id']}__{lang}__{jan}__{slug}.jsonl"
                    if out.exists():
                        pulos += 1
                        continue
                    used, _ = yt.used_today()
                    if used + 100 > yt.budget - RESERVA_UNIDADES:
                        print(f"[descobrir] parando: quota {used}/{yt.budget} (reserva {RESERVA_UNIDADES}). Retoma amanhã.")
                        return feitas
                    after = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT00:00:00Z")
                    try:
                        items = yt.search(q=q, n=50, order="viewCount", published_after=after,
                                          region=loc["regionCode"], lang=loc["relevanceLanguage"])
                    except QuotaExceeded as e:
                        print(f"[descobrir] {e}")
                        return feitas
                    rows = []
                    for it in items:
                        vid = it.get("id", {}).get("videoId")
                        if not vid:
                            continue
                        sn = it["snippet"]
                        rows.append({"video_id": vid, "channel_id": sn["channelId"], "channel_title": sn["channelTitle"],
                                     "title": sn["title"], "published_at": sn["publishedAt"],
                                     "categoria": cat["id"], "idioma_busca": lang, "janela": jan, "query": q,
                                     "coletado_em": today})
                        k = known.setdefault(sn["channelId"], {"categorias": [], "first_seen": today, "title": sn["channelTitle"]})
                        if cat["id"] not in k["categorias"]:
                            k["categorias"].append(cat["id"])
                    append_jsonl(out, rows)
                    save_known(known)
                    feitas += 1
                    print(f"[descobrir] {cat['id']} {lang} {jan} '{q}' → {len(rows)} vídeos")
    print(f"[descobrir] concluído: {feitas} buscas novas, {pulos} já feitas")
    return feitas


# ---------------------------------------------------------------- canais
def canais(yt: YT):
    known = load_known()
    ids = sorted(known)
    if not ids:
        print("[canais] nenhum canal conhecido ainda")
        return
    path = yt.snapshot_channels(ids, day=today)
    n = len(load_jsonl(path))
    print(f"[canais] snapshot {today}: {n} canais em {path.name}")


# ---------------------------------------------------------------- videos
def videos(yt: YT):
    have = {r["video_id"] for f in VIDS.glob("*.jsonl") for r in load_jsonl(f)}
    want = []
    for f in DISC.glob("*.jsonl"):
        for r in load_jsonl(f):
            if r["video_id"] not in have and r["video_id"] not in want:
                want.append(r["video_id"])
    if not want:
        print("[videos] nada novo")
        return
    out = VIDS / f"videos_{today}.jsonl"
    rows = []
    try:
        for v in yt.videos(want):
            sn, st, cd, stt = v.get("snippet", {}), v.get("statistics", {}), v.get("contentDetails", {}), v.get("status", {})
            rows.append({"video_id": v["id"], "channel_id": sn.get("channelId"), "title": sn.get("title"),
                         "published_at": sn.get("publishedAt"), "category_id": sn.get("categoryId"),
                         "default_language": sn.get("defaultLanguage") or sn.get("defaultAudioLanguage") or None,
                         "duration_s": iso_dur_to_s(cd.get("duration")), "definition": cd.get("definition"),
                         "made_for_kids": stt.get("madeForKids"), "license": stt.get("license"),
                         "view_count": int(st["viewCount"]) if "viewCount" in st else None,
                         "like_count": int(st["likeCount"]) if "likeCount" in st else None,
                         "comment_count": int(st["commentCount"]) if "commentCount" in st else None,
                         "topics": v.get("topicDetails", {}).get("topicCategories", []),
                         "tags_n": len(sn.get("tags", []) or []), "coletado_em": today})
    finally:
        append_jsonl(out, rows)
    print(f"[videos] {len(rows)} vídeos gravados em {out.name}")


# ---------------------------------------------------------------- uploads
def top_canais_por_categoria():
    """Top N canais por categoria pelo viewCount do snapshot mais recente (medido)."""
    known = load_known()
    snaps = sorted(SNAP.glob("channels_*.jsonl"))
    if not snaps:
        return {}
    latest = {r["id"]: r for r in load_jsonl(snaps[-1])}
    por_cat = defaultdict(list)
    for cid, k in known.items():
        if cid in latest:
            for c in k["categorias"]:
                por_cat[c].append((latest[cid]["view_count"], cid))
    return {c: [cid for _, cid in sorted(v, reverse=True)[:TOP_CANAIS_UPLOADS]] for c, v in por_cat.items()}


def uploads(yt: YT):
    done = {r["channel_id"] for f in UPL.glob("*.jsonl") for r in load_jsonl(f)}
    todo = []
    for c, ids in top_canais_por_categoria().items():
        todo += [i for i in ids if i not in done and i not in todo]
    if not todo:
        print("[uploads] nada novo")
        return
    out = UPL / f"uploads_{today}.jsonl"
    n = 0
    for cid in todo:
        try:
            items = yt.uploads(cid, n=50)
            vids = [i["contentDetails"]["videoId"] for i in items]
            det = {v["id"]: v for v in yt.videos(vids, parts="contentDetails,statistics,status,snippet")}
        except QuotaExceeded as e:
            print(f"[uploads] {e}")
            break
        except RuntimeError as e:   # ex.: playlist de uploads inexistente
            print(f"[uploads] {cid}: {str(e)[:120]}")
            continue
        rows = []
        for v in vids:
            d = det.get(v)
            if not d:
                continue
            st = d.get("statistics", {})
            rows.append({"channel_id": cid, "video_id": v, "published_at": d["snippet"]["publishedAt"],
                         "title": d["snippet"]["title"], "duration_s": iso_dur_to_s(d["contentDetails"].get("duration")),
                         "made_for_kids": d.get("status", {}).get("madeForKids"),
                         "view_count": int(st["viewCount"]) if "viewCount" in st else None,
                         "default_language": d["snippet"].get("defaultLanguage") or d["snippet"].get("defaultAudioLanguage"),
                         "coletado_em": today})
        append_jsonl(out, rows)
        n += 1
    print(f"[uploads] {n} canais processados → {out.name}")


# ---------------------------------------------------------------- derivar
def derivar():
    known = load_known()
    snaps = sorted(SNAP.glob("channels_*.jsonl"))
    if not snaps:
        print("[derivar] sem snapshots")
        return
    first = {r["id"]: r for r in load_jsonl(snaps[0])}
    latest = {r["id"]: r for r in load_jsonl(snaps[-1])}
    # snapshot mais antigo por canal (canal pode ter entrado depois do primeiro dia)
    earliest = {}
    for s in snaps:
        for r in load_jsonl(s):
            earliest.setdefault(r["id"], r)
    ups = defaultdict(list)
    for f in UPL.glob("*.jsonl"):
        for r in load_jsonl(f):
            ups[r["channel_id"]].append(r)
    now = datetime.now(timezone.utc)
    out_rows = []
    for cid, k in known.items():
        L = latest.get(cid)
        if not L:
            continue
        E = earliest.get(cid)
        row = {"channel_id": cid, "title": L["title"], "categorias": k["categorias"], "country": L.get("country") or "sem dado",
               "published_at": L.get("published_at"), "made_for_kids_canal": L.get("made_for_kids"),
               "subs": L["sub_count"], "views_total": L["view_count"], "videos_total": L["video_count"],
               "snapshot_dia": L["day"]}
        if E and E["day"] != L["day"]:
            days = (datetime.fromisoformat(L["day"]) - datetime.fromisoformat(E["day"])).days
            dv = L["view_count"] - E["view_count"]
            row.update({"delta_dias": days, "delta_views_medido": dv, "delta_videos_medido": L["video_count"] - E["video_count"],
                        "views_30d_extrapolado": round(dv / days * 30) if days > 0 else None,
                        "views_30d_status": f"medido em {days} dias, extrapolado para 30"})
        else:
            row.update({"delta_dias": 0, "delta_views_medido": None, "views_30d_extrapolado": None,
                        "views_30d_status": "sem dado (precisa de 2 snapshots em dias diferentes)"})
        if L.get("published_at"):
            age_days = (now - datetime.fromisoformat(L["published_at"].replace("Z", "+00:00"))).days
            row["idade_canal_dias"] = age_days
        u = ups.get(cid)
        if u:
            u90 = [x for x in u if (now - datetime.fromisoformat(x["published_at"].replace("Z", "+00:00"))).days <= 90]
            durs = [x["duration_s"] for x in u if x["duration_s"] is not None]
            kids = [x["made_for_kids"] for x in u if x["made_for_kids"] is not None]
            views = [x["view_count"] for x in u if x["view_count"] is not None]
            langs = [x["default_language"] for x in u if x.get("default_language")]
            oldest = min(x["published_at"] for x in u)
            span_days = max(1, (now - datetime.fromisoformat(oldest.replace("Z", "+00:00"))).days)
            row.update({
                "amostra_uploads": len(u),
                "uploads_ult_90d": len(u90),
                "uploads_por_mes_medido": round(len(u) / span_days * 30, 2) if len(u) < 50 else round(len(u90) / 3, 2),
                "uploads_por_mes_nota": "sobre os últimos 50 uploads" if len(u) >= 50 else "sobre todos os uploads do canal",
                "duracao_media_s": round(sum(durs) / len(durs)) if durs else None,
                "pct_shorts_heuristica": round(100 * sum(1 for d in durs if d <= SHORTS_MAX_S) / len(durs)) if durs else None,
                "pct_made_for_kids": round(100 * sum(1 for x in kids if x) / len(kids)) if kids else None,
                "views_media_por_video": round(sum(views) / len(views)) if views else None,
                "idioma_predominante": max(set(langs), key=langs.count) if langs else "sem dado",
                "sinal_automacao_upload_gt_1_dia": (len(u90) / 90) > 1 if u90 else None,
                "sinal_sem_rosto_voz_sintetica": "sem dado (requer inspeção manual)",
            })
        out_rows.append(row)
    out = DER / f"canais_{today}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_rows))

    # resumo em markdown
    por_cat = defaultdict(list)
    for r in out_rows:
        for c in r["categorias"]:
            por_cat[c].append(r)
    nomes = {c["id"]: c["nome"] for c in CFG["categorias"]}
    md = [f"# Resumo da coleta YouTube — {today}", "",
          f"Snapshots: {len(snaps)} dia(s) ({snaps[0].stem[-10:]} → {snaps[-1].stem[-10:]}). Canais conhecidos: {len(known)}. "
          f"Canais com amostra de uploads: {len(ups)}.", "",
          "Legenda: views/30d = **medido** por delta entre snapshots (extrapolado do intervalo); uploads/mês e % Shorts/kids = medidos na amostra de uploads; "
          "'sem dado' = a API não dá ou ainda falta um segundo snapshot.", ""]
    for c in sorted(por_cat):
        rows = sorted(por_cat[c], key=lambda r: (r.get("views_30d_extrapolado") or -1, r["views_total"]), reverse=True)[:15]
        md += [f"## {nomes.get(c, c)}", "",
               "| Canal | País | Inscritos | Views/30d (medido) | Δ dias | Uploads/mês | Dur. média | % Shorts* | % kids | Idade (dias) | Upload >1/dia |",
               "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for r in rows:
            md.append("| {t} | {co} | {s:,} | {v} | {dd} | {um} | {du} | {sh} | {k} | {age} | {auto} |".format(
                t=r["title"].replace("|", "/")[:40], co=r["country"], s=r["subs"],
                v=f"{r['views_30d_extrapolado']:,}" if r.get("views_30d_extrapolado") is not None else "sem dado",
                dd=r.get("delta_dias", 0), um=r.get("uploads_por_mes_medido", "sem dado"),
                du=f"{r['duracao_media_s']//60}m" if r.get("duracao_media_s") else "sem dado",
                sh=r.get("pct_shorts_heuristica", "sem dado"), k=r.get("pct_made_for_kids", "sem dado"),
                age=r.get("idade_canal_dias", "sem dado"), auto=r.get("sinal_automacao_upload_gt_1_dia", "sem dado")))
        md.append("")
    md.append("\\* heurística: vídeos com ≤ 180 s contados como possíveis Shorts (a API não marca Shorts).")
    (ROOT / "reports" / "coleta_resumo.md").write_text("\n".join(md))
    print(f"[derivar] {len(out_rows)} canais → {out.name} e reports/coleta_resumo.md")


# ---------------------------------------------------------------- status
def status(yt: YT | None = None):
    known = load_known()
    total_q = sum(len(q) for c in CFG["categorias"] for q in c["buscas"].values()) * len(CFG["janelas"])
    feitas = len(list(DISC.glob("*.jsonl")))
    snaps = sorted(SNAP.glob("channels_*.jsonl"))
    nv = sum(len(load_jsonl(f)) for f in VIDS.glob("*.jsonl"))
    nu = len({r["channel_id"] for f in UPL.glob("*.jsonl") for r in load_jsonl(f)})
    print(f"buscas feitas: {feitas}/{total_q} | canais conhecidos: {len(known)} | snapshots: {[s.stem[-10:] for s in snaps]}")
    print(f"vídeos com estatísticas: {nv} | canais com amostra de uploads: {nu}")
    if yt:
        u, s = yt.used_today()
        print(f"quota hoje: {u}/{yt.budget} unidades, {s} search.list")


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        try:
            status(YT())
        except SystemExit:
            status(None)
        return
    yt = YT()
    if cmd == "tudo":
        # ordem: barato primeiro (canais/vídeos/uploads do que já existe), descoberta com o que sobrar, e de novo o barato
        for step in (canais, videos, uploads):
            try:
                step(yt)
            except QuotaExceeded as e:
                print(f"[{step.__name__}] {e}")
        descobrir(yt)
        for step in (canais, videos, uploads):
            try:
                step(yt)
            except QuotaExceeded as e:
                print(f"[{step.__name__}] {e}")
        derivar()
    elif cmd == "diario":
        try:
            canais(yt)
        except QuotaExceeded as e:
            print(f"[canais] {e}")
        derivar()
    elif cmd in ("descobrir", "canais", "videos", "uploads"):
        globals()[cmd](yt)
        derivar()
    elif cmd == "derivar":
        derivar()
    else:
        sys.exit(__doc__)
    status(yt)


if __name__ == "__main__":
    main(sys.argv[1:])
