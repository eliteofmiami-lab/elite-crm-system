"""Transcrição de chamadas: GHL (WAV) -> Deepgram nova-2 (diarização, idioma auto)."""
import requests

import config
import ghl

_cfg = config.load()
DG_URL = "https://api.deepgram.com/v1/listen"
DG_PARAMS = {
    "model": "nova-2",           # decisão do Rafael: modelo nova
    "diarize": "true",
    "detect_language": "true",   # en/es/pt
    "smart_format": "true",
    "punctuate": "true",
    "utterances": "true",
}


def download_recording(message_id):
    """Baixa o WAV da chamada. Retorna bytes ou None (sem gravação)."""
    r = ghl.get(f"/conversations/messages/{message_id}/locations/{ghl.LOCATION_ID}/recording")
    if r.status_code == 200 and r.content and "audio" in (r.headers.get("Content-Type") or ""):
        return r.content
    return None


def transcribe(audio_bytes):
    """Manda o áudio pro Deepgram. Retorna dict {language, full_text, diarized, raw}."""
    key = _cfg["DEEPGRAM_API_KEY"]
    if not key:
        raise RuntimeError("DEEPGRAM_API_KEY ausente no .env")
    r = requests.post(
        DG_URL, params=DG_PARAMS,
        headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
        data=audio_bytes, timeout=300,
    )
    r.raise_for_status()
    raw = r.json()
    ch = raw["results"]["channels"][0]
    alt = ch["alternatives"][0]
    full_text = alt.get("transcript", "")
    language = ch.get("detected_language")
    diarized = []
    for u in raw["results"].get("utterances", []):
        diarized.append({"speaker": u.get("speaker"), "start": u.get("start"),
                         "end": u.get("end"), "text": u.get("transcript")})
    return {"language": language, "full_text": full_text,
            "diarized": diarized, "raw": raw}


def diarized_as_text(diarized):
    """Formata p/ o prompt do Claude: 'S0: ... / S1: ...'"""
    return "\n".join(f"S{u['speaker']}: {u['text']}" for u in diarized) if diarized else ""
