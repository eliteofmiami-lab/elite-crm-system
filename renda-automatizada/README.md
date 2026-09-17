# renda-automatizada

Máquina de renda automatizada. Meta: US$ 50 mil/mês recorrentes com produção e distribuição o mais automatizadas possível, só com conteúdo e produto originais.

## Regras do projeto (valem para tudo)
1. **Nenhum número inventado.** Todo dado vem de API ou fonte pública, com URL e data de coleta. O que não dá para medir fica marcado **sem dado**. Estimativas vêm sempre marcadas como **estimado**.
2. **Só conteúdo e produto original.** Categorias e formatos podem ser replicados; obras não. Nada de conteúdo reaproveitado, compilado de terceiros ou clone.
3. **Gates.** Nenhum canal, conta ou robô de produção é criado antes do OK por escrito do dono do projeto.

## Estrutura
| Pasta | O que tem |
|---|---|
| `config/` | `policies.md` (regras das plataformas, com URL e data), `score.yaml` (pesos do ranking, editáveis), `licenses.md` (licenças comerciais dos geradores, Fase 2) |
| `research/` | Guias e scripts de coleta. `GUIA_YOUTUBE_API.md`, `fetch_policies.py`, `yt_client.py`, `test_key.py` |
| `data/` | Dados brutos coletados: snapshots diários (`snapshots/`), cache da API (`cache/`, não versionado), contador de quota |
| `reports/` | Relatórios: `oportunidades.md` (Fase 1), `semanal.md` (Fase 2) |
| `bots/` | Um robô de produção por piloto aprovado no Gate 1 (vazio até lá) |

## Fases e gates
- **Fase 0 — Setup** (em andamento): repo, chave da YouTube API, `config/policies.md`. Status em `STATUS.md`.
- **Fase 1 — Pesquisa e ranking** → `reports/oportunidades.md` → **Gate 1**: o dono escolhe até 3 pilotos.
- **Fase 2 — Robôs de produção** por piloto → **Gate 2**: 3 amostras finalizadas + checklist de política por piloto antes do primeiro upload real.

## Como começar (Mac)
```bash
# 1. chave da API (10 min, gratuito)
open renda-automatizada/research/GUIA_YOUTUBE_API.md

# 2. baixar as páginas oficiais de política e gravar a data (a sessão do Claude não tem acesso a esses sites)
cd renda-automatizada && python3 research/fetch_policies.py

# 3. testar a chave (1 unidade de quota)
python3 research/test_key.py
```
Tudo roda localmente (Python 3 já vem no macOS com o Xcode Command Line Tools; se faltar, o Terminal oferece instalar). Sem servidor até um piloto provar receita.

## Convenção de rótulos nos relatórios
- **medido** — veio de API ou página pública, com URL e data.
- **verificado / autodeclarado / estimado** — classificação da evidência de receita (ver Fase 1, filtro zero).
- **secundário** — regra ou número lido em fonte não oficial; precisa de confirmação na página oficial.
- **sem dado** — não foi possível medir. Nunca chutado.
- **hipótese** — raciocínio nosso, sem dado.
