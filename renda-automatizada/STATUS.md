# STATUS — Fase 0 (Setup)

Atualizado: 2026-09-17

| Item | Estado | Observação |
|---|---|---|
| 0.1 Estrutura do repo (`research/ data/ reports/ bots/ config/ README`) | ✅ feito | Dentro de `renda-automatizada/` no repositório existente |
| 0.2 Guia da chave YouTube Data API v3 | ✅ escrito | `research/GUIA_YOUTUBE_API.md` — **aguarda você criar a chave e preencher `.env`** |
| 0.2 Cliente da API com cache + contador de quota + snapshots (delta de views) | ✅ feito, testado offline | `research/yt_client.py`, `research/test_key.py` |
| 0.3 `config/policies.md` | ⚠️ parcial | Todas as regras coletadas hoje por **fonte secundária**; páginas oficiais bloqueadas nesta sessão. Fechar com `research/fetch_policies.py` (Mac) |
| `config/score.yaml` (rascunho de pesos) | ✅ rascunho | Congelar antes do Gate 1 |
| `config/licenses.md` | ✅ vazio por design | Preenche na Fase 2 |

## O que depende de você (em ordem)
1. Criar a chave da API seguindo `research/GUIA_YOUTUBE_API.md` (10 min) e rodar `python3 research/test_key.py`.
2. Rodar `python3 research/fetch_policies.py` e me avisar. Eu leio os textos e fecho o `policies.md`.
3. Dizer se prefere que a coleta da Fase 1 rode no seu Mac (cron/launchd) ou por aqui. A API do Google respondeu desta sessão, então dá para rodar por aqui também se você me passar a chave num canal seguro. Recomendação: rodar no Mac, como combinado.

## Gates
- **Gate 1** (fim da Fase 1): ranking em `reports/oportunidades.md` → você escolhe até 3 pilotos. Nada é criado antes.
- **Gate 2** (Fase 2): 3 amostras finalizadas + checklist de política por piloto → só publica com seu OK.
