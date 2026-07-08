"""MVP item 7 — BETA_FEEDBACK.md: consolidação diária de todos os reportes do beta
com o contexto de cada um. Nenhum feedback altera nada automaticamente."""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

config.load()
from brain import cards  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TIPOS = {"score_errado": "Score errado", "estado_errado": "Estado errado",
         "nao_deveria_estar": "Não deveria estar na fila", "ordem_errada": "Ordem errada",
         "pendencia_incorreta": "Pendência incorreta", "outro": "Outro"}


def main():
    rows = cards._sb("GET", "beta_feedback?select=*&order=created_at.desc") or []
    m = [f"# BETA_FEEDBACK — reportes do beta · regenerado {dt.datetime.now():%Y-%m-%d %H:%M}",
         "", f"**{len(rows)} reporte(s).** Erro vira dado: nada muda automaticamente — "
         "este arquivo é a matéria-prima das rodadas de correção com o Rafael.", ""]
    por_tipo = {}
    for r in rows:
        por_tipo[r["tipo"]] = por_tipo.get(r["tipo"], 0) + 1
    if rows:
        m.append("| Tipo | Reportes |")
        m.append("|---|---|")
        for t, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
            m.append(f"| {TIPOS.get(t, t)} | {n} |")
        m.append("")
    for r in rows:
        snap = r.get("snapshot") or {}
        m.append(f"## {str(r['created_at'])[:16]} · {TIPOS.get(r['tipo'], r['tipo'])} "
                 f"· por {r.get('reported_by') or '?'}")
        m.append(f"- Card: {snap.get('title') or r.get('card_id')} (C{snap.get('layer', '?')}, "
                 f"`{snap.get('type', '?')}`)")
        m.append(f"- Contexto no momento: score {snap.get('score')}/{snap.get('score_max')} "
                 f"[{snap.get('badge')}] · estado `{snap.get('situacao')}` · "
                 f"breakdown `{snap.get('breakdown')}`")
        if r.get("texto"):
            m.append(f"- Texto: “{r['texto']}”")
        if r.get("contact_id"):
            m.append(f"- [Contato no GHL](https://app.gohighlevel.com/v2/location/"
                     f"Ao5ER8XBg3AtCJMccesF/contacts/detail/{r['contact_id']})")
        m.append("")
    if not rows:
        m.append("_Nenhum reporte ainda._")
    (ROOT / "BETA_FEEDBACK.md").write_text("\n".join(m))
    print(f"BETA_FEEDBACK.md regenerado: {len(rows)} reportes")


if __name__ == "__main__":
    main()
