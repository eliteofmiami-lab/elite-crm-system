"""Cache de mensagens dos contatos da janela de 40 dias (SOMENTE LEITURA).
Salva out/messages_40d.json = { contactId: [msgs...] }. Reutilizado por score v2, A2 e A3."""
import json, ghl

LOC = ghl.LOCATION_ID
KEEP = ("id", "messageType", "direction", "status", "body", "dateAdded",
        "meta", "from", "to", "userId", "source", "conversationId")


def slim(m):
    return {k: m.get(k) for k in KEEP}


def main():
    opps = json.load(open("out/opps_40d.json"))
    cids = list(dict.fromkeys(o["contactId"] for o in opps))  # únicos, preserva ordem
    cache = {}
    for i, cid in enumerate(cids, 1):
        r = ghl.get("/conversations/search", {"locationId": LOC, "contactId": cid})
        if r.status_code != 200:
            cache[cid] = []
            continue
        msgs = []
        for cv in r.json().get("conversations", []):
            mr = ghl.get(f"/conversations/{cv['id']}/messages")
            if mr.status_code == 200:
                msgs += [slim(m) for m in mr.json().get("messages", {}).get("messages", [])]
        cache[cid] = msgs
        if i % 25 == 0:
            print(f"  ...{i}/{len(cids)}")
            json.dump(cache, open("out/messages_40d.json", "w"))
    json.dump(cache, open("out/messages_40d.json", "w"))
    print(f"OK: {len(cache)} contatos, {sum(len(v) for v in cache.values())} mensagens -> out/messages_40d.json")


if __name__ == "__main__":
    main()
