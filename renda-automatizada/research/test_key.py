#!/usr/bin/env python3
"""Testa a chave da YouTube Data API com UMA chamada channels.list (1 unidade de quota)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yt_client import YT  # noqa: E402

YOUTUBE_OFFICIAL_CHANNEL = "UCBR8-60-B28hp2BmDPdntcQ"  # canal "YouTube"

yt = YT()
items = yt.channels([YOUTUBE_OFFICIAL_CHANNEL], parts="snippet,statistics")
if not items:
    sys.exit("A chamada funcionou mas não voltou canal. Me mande esta mensagem.")
ch = items[0]
st = ch["statistics"]
print("Chave OK.")
print(f"  canal: {ch['snippet']['title']}  (criado em {ch['snippet']['publishedAt'][:10]})")
print(f"  inscritos: {int(st.get('subscriberCount', 0)):,}  views totais: {int(st.get('viewCount', 0)):,}  vídeos: {st.get('videoCount')}")
units, _ = yt.used_today()
print(f"quota gasta hoje: {units} unidade(s) de {yt.budget} do orçamento local (Google dá 10.000/dia).")
