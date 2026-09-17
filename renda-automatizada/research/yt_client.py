#!/usr/bin/env python3
"""
Cliente mínimo da YouTube Data API v3 com:
  - cache em disco (data/cache/) para não pagar duas vezes pela mesma chamada;
  - contador de quota (data/quota_ledger.jsonl) com orçamento diário e trava;
  - snapshots diários de canais (data/snapshots/) para medir views/mês por DELTA
    entre coletas em dias diferentes — nunca por estimativa.

Só biblioteca padrão. Chave lida de renda-automatizada/.env (YOUTUBE_API_KEY).

Uso em outros scripts:
    from yt_client import YT
    yt = YT()
    ch = yt.channels(ids=["UC..."])            # 1 unidade por chamada (até 50 ids)
    vids = yt.videos(ids=["..."])              # 1 unidade por chamada (até 50 ids)
    ups = yt.uploads(channel_id="UC...", n=50) # 1 + 1 unidade (playlistItems + channels)
    hits = yt.search(q="lofi sleep", n=25)     # 100 unidades — cacheado 7 dias, máx. 90/dia
    yt.snapshot_channels(["UC...", ...])       # grava data/snapshots/channels_AAAA-MM-DD.jsonl
    yt.delta_views("UC...", "2026-09-17", "2026-09-24")  # views medidas no intervalo
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # renda-automatizada/
DATA = ROOT / "data"
CACHE = DATA / "cache"
SNAP = DATA / "snapshots"
LEDGER = DATA / "quota_ledger.jsonl"
API = "https://www.googleapis.com/youtube/v3/"

# Custos oficiais: https://developers.google.com/youtube/v3/determine_quota_cost (confirme na página)
COST = {"search": 100, "channels": 1, "videos": 1, "playlistItems": 1, "videoCategories": 1}
# TTL do cache em horas. Estatísticas mudam todo dia → 20h (uma coleta por dia); descoberta → 7 dias.
TTL_H = {"search": 24 * 7, "channels": 20, "videos": 20, "playlistItems": 20, "videoCategories": 24 * 30}
SEARCH_CALLS_PER_DAY = 90     # abaixo do balde de ~100/dia reportado (secundário) para search.list


def _load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _pacific_today():
    # A quota do Google reseta à meia-noite no horário do Pacífico (PT). Aproximação: UTC-7.
    return (datetime.now(timezone.utc) - timedelta(hours=7)).strftime("%Y-%m-%d")


class QuotaExceeded(RuntimeError):
    pass


class YT:
    def __init__(self, key: str | None = None, budget: int | None = None):
        _load_env()
        self.key = key or os.environ.get("YOUTUBE_API_KEY", "")
        if not self.key:
            sys.exit("YOUTUBE_API_KEY vazio. Siga research/GUIA_YOUTUBE_API.md e preencha renda-automatizada/.env")
        self.budget = int(os.environ.get("YOUTUBE_DAILY_BUDGET_UNITS", "9000")) if budget is None else budget
        for d in (CACHE, SNAP):
            d.mkdir(parents=True, exist_ok=True)

    # ---------- quota ----------
    def used_today(self) -> tuple[int, int]:
        """(unidades gastas hoje, chamadas search.list hoje) — só chamadas reais, não cache."""
        day = _pacific_today()
        units = searches = 0
        if LEDGER.exists():
            for line in LEDGER.read_text().splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("day") == day and not r.get("cached"):
                    units += r.get("units", 0)
                    searches += 1 if r.get("endpoint") == "search" else 0
        return units, searches

    def _log(self, endpoint, params, units, cached):
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "day": _pacific_today(),
               "endpoint": endpoint, "units": units, "cached": cached,
               "params": {k: v for k, v in params.items() if k != "key"}}
        with LEDGER.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---------- chamada genérica com cache ----------
    def call(self, endpoint: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        raw = json.dumps({"e": endpoint, "p": params}, sort_keys=True)
        h = hashlib.sha1(raw.encode()).hexdigest()
        cpath = CACHE / f"{endpoint}_{h}.json"
        ttl = timedelta(hours=TTL_H.get(endpoint, 20))
        if cpath.exists():
            blob = json.loads(cpath.read_text())
            fetched = datetime.fromisoformat(blob["fetched_at"])
            if datetime.now(timezone.utc) - fetched < ttl:
                self._log(endpoint, params, 0, True)
                return blob["data"]

        cost = COST.get(endpoint, 1)
        used, searches = self.used_today()
        if used + cost > self.budget:
            raise QuotaExceeded(f"orçamento diário atingido: {used}+{cost} > {self.budget} unidades")
        if endpoint == "search" and searches >= SEARCH_CALLS_PER_DAY:
            raise QuotaExceeded(f"limite local de {SEARCH_CALLS_PER_DAY} search.list/dia atingido")

        url = API + endpoint + "?" + urllib.parse.urlencode({**params, "key": self.key})
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            self._log(endpoint, params, cost, False)
            raise RuntimeError(f"HTTP {e.code} em {endpoint}: {body[:500]}") from None
        self._log(endpoint, params, cost, False)
        cpath.write_text(json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat(), "data": data}))
        return data

    # ---------- atalhos ----------
    def channels(self, ids=None, handle=None, parts="snippet,statistics,contentDetails,topicDetails,brandingSettings,status"):
        if ids:
            out = []
            for i in range(0, len(ids), 50):
                out += self.call("channels", part=parts, id=",".join(ids[i:i + 50]), maxResults=50).get("items", [])
            return out
        return self.call("channels", part=parts, forHandle=handle).get("items", [])

    def videos(self, ids, parts="snippet,statistics,contentDetails,status,topicDetails"):
        out = []
        for i in range(0, len(ids), 50):
            out += self.call("videos", part=parts, id=",".join(ids[i:i + 50]), maxResults=50).get("items", [])
        return out

    def uploads(self, channel_id: str, n: int = 50):
        """Últimos n uploads via playlist 'UU...' (1 unidade/página) — evita search.list."""
        pl = "UU" + channel_id[2:]
        items, token = [], None
        while len(items) < n:
            page = self.call("playlistItems", part="snippet,contentDetails", playlistId=pl,
                             maxResults=min(50, n - len(items)), pageToken=token)
            items += page.get("items", [])
            token = page.get("nextPageToken")
            if not token:
                break
        return items

    def search(self, q=None, n=25, type_="video", order="viewCount", published_after=None,
               region=None, lang=None, category_id=None, duration=None, topic_id=None):
        return self.call("search", part="snippet", q=q, type=type_, order=order, maxResults=min(n, 50),
                         publishedAfter=published_after, regionCode=region, relevanceLanguage=lang,
                         videoCategoryId=category_id, videoDuration=duration, topicId=topic_id).get("items", [])

    # ---------- snapshots para medir por delta ----------
    def snapshot_channels(self, ids, day: str | None = None) -> Path:
        day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = SNAP / f"channels_{day}.jsonl"
        seen = set()
        if path.exists():
            seen = {json.loads(l)["id"] for l in path.read_text().splitlines() if l.strip()}
        todo = [i for i in ids if i not in seen]
        with path.open("a") as f:
            for ch in self.channels(todo, parts="snippet,statistics,status,topicDetails"):
                st = ch.get("statistics", {})
                rec = {"id": ch["id"], "day": day, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "title": ch["snippet"].get("title"), "country": ch["snippet"].get("country"),
                       "published_at": ch["snippet"].get("publishedAt"),
                       "made_for_kids": ch.get("status", {}).get("madeForKids"),
                       "view_count": int(st.get("viewCount", 0)), "sub_count": int(st.get("subscriberCount", 0)),
                       "video_count": int(st.get("videoCount", 0)),
                       "topics": ch.get("topicDetails", {}).get("topicCategories", [])}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return path

    @staticmethod
    def delta_views(channel_id: str, day_a: str, day_b: str) -> dict:
        """Views MEDIDAS entre dois snapshots. Extrapola para 30 dias só como aritmética, marcado."""
        def load(day):
            p = SNAP / f"channels_{day}.jsonl"
            if not p.exists():
                return None
            for l in p.read_text().splitlines():
                r = json.loads(l)
                if r["id"] == channel_id:
                    return r
            return None
        a, b = load(day_a), load(day_b)
        if not a or not b:
            return {"status": "sem dado", "reason": f"snapshot ausente para {channel_id} em {day_a} ou {day_b}"}
        days = (datetime.fromisoformat(day_b) - datetime.fromisoformat(day_a)).days
        if days <= 0:
            return {"status": "sem dado", "reason": "intervalo inválido"}
        dv = b["view_count"] - a["view_count"]
        return {"status": "medido", "channel_id": channel_id, "from": day_a, "to": day_b, "days": days,
                "delta_views": dv, "delta_videos": b["video_count"] - a["video_count"],
                "views_per_30d_extrapolated": round(dv / days * 30),
                "note": "views_per_30d_extrapolated é aritmética sobre o intervalo medido; rotular como 'medido em N dias, extrapolado para 30'"}


if __name__ == "__main__":
    yt = YT()
    u, s = yt.used_today()
    print(f"quota gasta hoje (dia PT {_pacific_today()}): {u} unidades, {s} chamadas search.list; orçamento {yt.budget}")
