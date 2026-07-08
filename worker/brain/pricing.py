"""
A9.1/A10 — fonte única de preços no worker: classes (tabela | starting_price |
custom_quote), tier determinístico e validação de ballpark falado.
Regra de validação: classe starting → falar ACIMA do starting do tier é ok
(material melhor); falar ABAIXO gera alerta. Classe tabela → divergência gera alerta.
"""
import json
import re
from pathlib import Path

from brain import cards

_ROOT = Path(__file__).resolve().parent.parent.parent
_prices = None
_tiers_kw = None


def prices():
    global _prices
    if _prices is None:
        _prices = json.load(open(_ROOT / "config" / "prices.json"))
    return _prices


def tier_for(text):
    """Tier determinístico por palavra-chave (config/vehicle_tiers.json)."""
    global _tiers_kw
    if _tiers_kw is None:
        _tiers_kw = json.load(open(_ROOT / "config" / "vehicle_tiers.json"))
    t = (text or "").lower()
    for tier in ("Large", "Medium", "Compact"):
        if any(k in t for k in _tiers_kw.get(tier, [])):
            return tier
    return None  # desconhecido → nunca chutar


def keys_for_interest(interest):
    il = (interest or "").lower()
    if not il:
        return []
    for kw, ks in prices().get("_interest_map", {}).items():
        if kw in il:
            return ks
    return []


def classify(service_text):
    """(classe, key) p/ um texto de serviço: 'starting'|'tabela'|'custom'|None."""
    p = prices()
    il = (service_text or "").lower()
    if any(s.lower() in il for s in p.get("custom_quote_services", [])):
        return "custom", None
    for k in keys_for_interest(service_text):
        if k in p.get("starting", {}):
            return "starting", k
        if k in p.get("matrix", {}):
            return "tabela", k
    return None, None


def _parse_usd(v):
    m = re.findall(r"\d[\d,]*", str(v or ""))
    if not m:
        return None
    try:
        return int(m[0].replace(",", ""))
    except ValueError:
        return None


def check_ballparks(analysis, contact_id, call_id, vehicle_text=""):
    """Valida precos_falados contra a tabela → linhas em price_alerts (vista do dono).
    Conservador: só alerta divergência clara (abaixo do starting; ±5% na tabela)."""
    p = prices()
    tier = tier_for(vehicle_text)
    n = 0
    for item in (analysis or {}).get("precos_falados", []) or []:
        val = _parse_usd(item.get("valor"))
        if not val or val < 50:
            continue
        cls, key = classify(f"{item.get('servico', '')} {item.get('escopo', '')}")
        if not key:
            continue
        row = (p.get("starting", {}) if cls == "starting" else p.get("matrix", {})).get(key, {})
        ref_vals = [row[t] for t in p.get("_tiers", []) if isinstance(row.get(t), (int, float))]
        if row.get("flat") is not None:
            ref_vals = [row["flat"]]
        if row.get("from") is not None:
            ref_vals = [row["from"]]
        if not ref_vals:
            continue
        ref = row.get(tier) if tier and isinstance(row.get(tier), (int, float)) else None
        kind = detail = None
        if cls == "starting":
            floor = ref if ref is not None else min(ref_vals)
            if val < floor * 0.98:  # ACIMA é ok (material melhor); ABAIXO alerta
                kind = "below_starting"
                detail = f"falado ${val:,} < starting ${floor:,}" + (f" ({tier})" if tier else " (piso geral)")
        else:
            if ref is not None:
                if abs(val - ref) > ref * 0.05:
                    kind = "off_table"
                    detail = f"falado ${val:,} ≠ tabela ${ref:,} ({tier})"
            elif val < min(ref_vals) * 0.95 or val > max(ref_vals) * 1.05:
                kind = "off_table"
                detail = f"falado ${val:,} fora da faixa ${min(ref_vals):,}–${max(ref_vals):,} (tier desconhecido)"
        if kind:
            cards._sb("POST", "price_alerts", json={
                "call_id": call_id, "contact_id": contact_id,
                "servico": item.get("servico"), "valor_falado": str(item.get("valor"))[:40],
                "kind": kind, "detail": detail, "tier": tier})
            n += 1
    return n
