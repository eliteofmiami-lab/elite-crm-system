#!/usr/bin/env python3
"""
Baixa as páginas OFICIAIS de política de cada plataforma e grava um snapshot datado.

Por quê: a sessão remota do Claude não consegue acessar support.google.com, kdp.amazon.com,
support.spotify.com, etsy.com etc. (bloqueio de rede). Este script roda no SEU Mac, onde
não há bloqueio, e deixa a prova de "lido em <data>" para cada regra de config/policies.md.

Uso (dentro de renda-automatizada/):
    python3 research/fetch_policies.py            # baixa tudo
    python3 research/fetch_policies.py Y-01 K-03   # só alguns IDs

Saída:
    research/policies_raw/<AAAA-MM-DD>/<ID>.html   (HTML bruto; não versionado)
    research/policies_raw/<AAAA-MM-DD>/<ID>.txt    (texto extraído; versionado)
    research/policies_raw/<AAAA-MM-DD>/index.json  (URL, status HTTP, sha256, data/hora, tamanho)

Só usa a biblioteca padrão do Python. Não precisa instalar nada.
"""
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# IDs batem com config/policies.md. Se uma URL mudar, atualize aqui E lá.
SOURCES = {
    # --- YouTube ---
    "Y-01": ("YouTube - Channel monetization policies (inclui 'inauthentic content' e 'reused content')",
             "https://support.google.com/youtube/answer/1311392?hl=en"),
    "Y-02": ("YouTube - YouTube Partner Program overview & eligibility",
             "https://support.google.com/youtube/answer/72851?hl=en"),
    "Y-03": ("YouTube - Changes to the YouTube Partner Program (limiares 2027)",
             "https://support.google.com/youtube/answer/12843009?hl=en"),
    "Y-04": ("YouTube - Determine if your content is 'made for kids'",
             "https://support.google.com/youtube/answer/9528076?hl=en"),
    "Y-05": ("YouTube - How ads work on 'made for kids' content",
             "https://support.google.com/youtube/answer/9713557?hl=en"),
    "Y-06": ("YouTube - How Content ID works",
             "https://support.google.com/youtube/answer/2797370?hl=en"),
    "Y-07": ("YouTube - Disclosing use of altered or synthetic content",
             "https://support.google.com/youtube/answer/14328491?hl=en"),
    "Y-08": ("YouTube Data API - Quota cost table",
             "https://developers.google.com/youtube/v3/determine_quota_cost"),
    "Y-09": ("YouTube Data API - Getting started (quota diária)",
             "https://developers.google.com/youtube/v3/getting-started"),
    "Y-10": ("YouTube Blog - YPP updates 2027 (anúncio oficial)",
             "https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/"),
    # --- Amazon KDP ---
    "K-01": ("KDP - Content Guidelines (inclui seção de IA generativa)",
             "https://kdp.amazon.com/en_US/help/topic/G200672390"),
    "K-02": ("KDP - Guide to Kindle Content Quality (conteúdo decepcionante / baixa qualidade)",
             "https://kdp.amazon.com/en_US/help/topic/G200952510"),
    "K-03": ("KDP - Paperback printing cost (tabela oficial)",
             "https://kdp.amazon.com/en_US/help/topic/G201834340"),
    "K-04": ("KDP - Paperback royalty",
             "https://kdp.amazon.com/en_US/help/topic/G201834330"),
    "K-05": ("KDP - eBook royalty options (35% / 70%)",
             "https://kdp.amazon.com/en_US/help/topic/G200644210"),
    "K-06": ("KDP Community - Update on KDP Title Creation Limits (aviso oficial do limite diário)",
             "https://www.kdpcommunity.com/s/article/Update-on-KDP-Title-Creation-Limits?language=en_US"),
    # --- Spotify / Apple / distribuidoras ---
    "S-01": ("Spotify for Artists - Artificial streaming",
             "https://support.spotify.com/us/artists/article/artificial-streaming/"),
    "S-02": ("Spotify for Artists - Modernizing our royalty system (1.000 streams, ruído 2 min)",
             "https://support.spotify.com/us/artists/article/modernizing-our-royalty-system/"),
    "S-03": ("Spotify Newsroom - Spotify strengthens AI protections (25/09/2025)",
             "https://newsroom.spotify.com/2025-09-25/spotify-strengthens-ai-protections/"),
    "S-04": ("Spotify Loud & Clear - FAQ sobre limiar de 1.000 streams",
             "https://loudandclear.byspotify.com/faqs/why-dont-songs-with-less-than-1000-annual-streams-earn-recording-royalties-on-spotify-anymore/"),
    "S-05": ("DistroKid - Is there a minimum payout threshold?",
             "https://support.distrokid.com/hc/en-us/articles/360013648353-Is-There-a-Minimum-Payout-Threshold"),
    "S-06": ("DistroKid - How and when do I get paid?",
             "https://support.distrokid.com/hc/en-us/articles/360013547274-How-and-When-Do-I-Get-Paid"),
    # --- Print on demand ---
    "P-01": ("Etsy - Creativity Standards",
             "https://www.etsy.com/legal/policy/creativity-standards/1311734473574"),
    "P-02": ("Amazon Merch on Demand - Content Policy",
             "https://merch.amazon.com/resource/201858630"),
    "P-03": ("Redbubble - Community and Content Guidelines",
             "https://help.redbubble.com/hc/en-us/articles/202270929-Community-and-Content-Guidelines"),
    "P-04": ("Redbubble - How does my Account Tier determine my platform fee?",
             "https://help.redbubble.com/hc/en-us/articles/50959863016724"),
    # --- Preços oficiais dos provedores (custos de produção) ---
    "C-01": ("ElevenLabs - Pricing", "https://elevenlabs.io/pricing"),
    "C-02": ("OpenAI - API pricing (TTS, imagem, LLM)", "https://platform.openai.com/docs/pricing"),
    "C-03": ("Suno - Pricing", "https://suno.com/pricing"),
    "C-04": ("Google Gemini API - Pricing (Veo, Nano Banana, Gemini)", "https://ai.google.dev/gemini-api/docs/pricing"),
    "C-05": ("Black Forest Labs (FLUX) - Pricing", "https://bfl.ai/pricing"),
    "C-06": ("Runway - Pricing", "https://runwayml.com/pricing"),
    "C-07": ("Kling AI - Pricing", "https://klingai.com/global/dev/pricing"),
}

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h\d>|</tr>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
    raw = re.sub(r"\n\s*\n+", "\n\n", raw)
    return raw.strip()


def fetch(url: str, timeout: int = 40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, r.geturl(), body
    except urllib.error.HTTPError as e:
        return e.code, url, e.read() if e.fp else b""
    except Exception as e:  # rede, TLS, timeout
        return None, url, str(e).encode()


def main(argv):
    wanted = [a for a in argv if a in SOURCES]
    ids = wanted or list(SOURCES)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = Path(__file__).resolve().parent / "policies_raw" / today
    out.mkdir(parents=True, exist_ok=True)
    index_path = out / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}

    ok = 0
    for sid in ids:
        title, url = SOURCES[sid]
        status, final_url, body = fetch(url)
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = {"id": sid, "title": title, "url": url, "final_url": final_url,
                 "http_status": status, "fetched_at_utc": stamp, "bytes": len(body)}
        if status == 200 and body:
            (out / f"{sid}.html").write_bytes(body)
            text = strip_html(body.decode("utf-8", errors="replace"))
            (out / f"{sid}.txt").write_text(text)
            entry["sha256"] = hashlib.sha256(body).hexdigest()
            entry["text_chars"] = len(text)
            ok += 1
            print(f"[OK ] {sid} {status} {len(text):>7} chars  {title}")
        else:
            entry["error"] = body.decode("utf-8", errors="replace")[:300]
            print(f"[ERR] {sid} {status}  {title}\n      -> {url}\n      abra no navegador e salve como research/policies_raw/{today}/{sid}.html")
        index[sid] = entry

    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"\n{ok}/{len(ids)} páginas salvas em {out}")
    print("Próximo passo: me avise que rodou; eu leio os .txt e atualizo config/policies.md trocando 'secundário' por 'lido em <data>'.")


if __name__ == "__main__":
    main(sys.argv[1:])
