"""
FOCO DO RAFAEL (2026-07-08): quote enviada + sem contato desde abril → tentar
contato → card instrui ativar o warm-up no GHL (zero escrita: quem ativa é o Eugene).

Varredura one-time: conversas com última mensagem entre JANELA_INI e CUTOFF
(dormentes) → procura link go.urable.com nos SMS outbound → card quote_rescue (C2).
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
import ghl  # noqa: E402
from brain import cards, rules  # noqa: E402

JANELA_INI = "2026-01-01"   # quotes do Urable são deste ano
CUTOFF = "2026-05-01"       # "sem contato desde abril"
MAX_CARDS = 30              # foco do dia; o resto entra por top-up diário


def log(m):
    print(f"[{dt.datetime.now():%H:%M:%S}] {m}", flush=True)


def ms_to_date(ms):
    try:
        return dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return str(ms)[:10]


def dormant_conversations():
    """Pagina DESC até passar de JANELA_INI; devolve as com última msg < CUTOFF."""
    out, page = [], 1
    while True:
        r = ghl.get("/conversations/search",
                    {"locationId": ghl.LOCATION_ID, "limit": 100, "page": page,
                     "sortBy": "last_message_date", "sort": "desc"})
        if r.status_code != 200:
            break
        convs = r.json().get("conversations", [])
        if not convs:
            break
        stop = False
        for cv in convs:
            d = ms_to_date(cv.get("lastMessageDate"))
            if d < JANELA_INI:
                stop = True
                break
            if d < CUTOFF and cv.get("contactId"):
                out.append({"id": cv["id"], "contact_id": cv["contactId"],
                            "last": d, "name": (cv.get("fullName") or "").strip()})
        if stop or len(convs) < 100:
            break
        page += 1
        if page > 80:
            break
    return out


def main():
    log("varredura de conversas dormentes (jan–abr)…")
    dorm = dormant_conversations()
    log(f"dormentes na janela: {len(dorm)}")
    made = scanned = 0
    results = []
    for i, cv in enumerate(dorm, 1):
        m = ghl.get(f"/conversations/{cv['id']}/messages")
        if m.status_code != 200:
            continue
        scanned += 1
        quote_msgs = []
        for msg in m.json().get("messages", {}).get("messages", []):
            if (msg.get("messageType") == "TYPE_SMS" and msg.get("direction") == "outbound"
                    and rules.URABLE_LINK.search(msg.get("body") or "")):
                quote_msgs.append(msg)
        if not quote_msgs:
            continue
        last_q = max(quote_msgs, key=lambda x: x.get("dateAdded") or "")
        link = rules.URABLE_LINK.search(last_q.get("body") or "").group(0).rstrip(".,)")
        sent = (last_q.get("dateAdded") or "")[:10]
        cid = cv["contact_id"]
        nome = cv.get("name")
        if not nome:
            cr = ghl.get(f"/contacts/{cid}")
            if cr.status_code == 200:
                c = cr.json().get("contact", {})
                nome = f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip()
        results.append({"contact_id": cid, "nome": nome, "quote_sent": sent,
                        "silent_since": cv["last"], "link": link})
        if made < MAX_CARDS:
            ok = cards.create_card(
                "quote_rescue", 2, cid,
                f"QUOTE RESCUE — {nome or 'lead'}",
                f"Quote enviada em {sent} ({link}) — sem NENHUM contato desde {cv['last']}.",
                {"passos": [
                    "Call now — the quote is the door back in: ask what they thought.",
                    "No answer: leave a short voicemail mentioning the quote.",
                    "Still nothing → activate the WARM-UP automation in GHL yourself "
                    "(reaquecimento flow/tag) so the drip takes over.",
                    "Goal: revive the conversation and close the VISIT."],
                 "quote": {"link": link, "sent_date": last_q.get("dateAdded")}})
            made += bool(ok)
        if i % 100 == 0:
            log(f"  {i}/{len(dorm)} varridas · {len(results)} com quote · {made} cards")
    json.dump(results, open(Path(__file__).resolve().parent.parent / "out" / "quote_rescue.json", "w"),
              indent=2, ensure_ascii=False)
    log(f"FIM: {len(results)} leads quote-dormente · {made} cards criados "
        f"(cap {MAX_CARDS}; resto em out/quote_rescue.json p/ top-up)")


if __name__ == "__main__":
    main()
