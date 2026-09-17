# STATUS — Fase 0 (Setup)

Atualizado: 2026-09-17 (v3 — noite)

| Item | Estado | Observação |
|---|---|---|
| 0.1 Estrutura do repo (`research/ data/ reports/ bots/ config/ README`) | ✅ feito | Dentro de `renda-automatizada/` no repositório existente |
| 0.2 Guia da chave YouTube Data API v3 | ✅ escrito | `research/GUIA_YOUTUBE_API.md` — **aguarda você criar a chave e preencher `.env`** |
| 0.2 Cliente da API com cache + contador de quota + snapshots (delta de views) | ✅ feito, testado offline | `research/yt_client.py`, `research/test_key.py` |
| 0.3 `config/policies.md` | ⚠️ parcial | Todas as regras coletadas hoje por **fonte secundária**; páginas oficiais bloqueadas nesta sessão. Fechar com `research/fetch_policies.py` (Mac) |
| `config/score.yaml` (rascunho de pesos) | ✅ rascunho | Congelar antes do Gate 1 |
| `config/licenses.md` | ✅ vazio por design | Preenche na Fase 2 |

## Fase 1 — ferramentas prontas para rodar no Mac (decisão: coleta roda no Mac, respostas no chat)
| Item | Estado | Arquivo |
|---|---|---|
| Coletor YouTube (descoberta, snapshots diários, vídeos, uploads, métricas derivadas) | ✅ testado com API simulada | `research/fase1_coleta.py`, `config/categorias.json` |
| Coletor KDP (busca → página do produto → BSR, preço, avaliações, data, páginas, IA) | ✅ parser testado com HTML de exemplo; não testado contra a Amazon real | `research/kdp_coleta.py`, `config/kdp_nichos.json`, `research/KDP_MANUAL.md` |
| Coletor de evidências de receita (Empire Flippers, Flippa, Motion Invest, Acquire) | ✅ escrito; páginas JS/login caem para manual | `research/evidencias_coleta.py`, `config/evidencias_fontes.json`, `research/EVIDENCIAS_MANUAL.md` |
| Envio automático dos dados para o repositório | ✅ | `research/sync.sh` |
| Agendador diário do Mac (launchd 08:00) | ✅ | `research/install_launchd.sh`, `research/diario.sh` |
| Passo a passo | ✅ | `research/COMO_RODAR.md`, `research/rodar.sh` |

## Feito hoje sem depender de você (por busca na web; tudo rotulado como secundário até a leitura oficial no Mac)
| Item | Arquivo |
|---|---|
| Filtro zero preliminar: ~35 operações com número, por categoria, com URL, classificação e status | `research/evidencias_secundarias.md` |
| Faixas de RPM por categoria + views/mês necessárias para US$ 50 mil | `research/rpm_fontes.md` |
| Custos de produção por unidade (TTS, música, imagem, vídeo) e custo por peça | `research/custos_producao.md` |
| 29 URLs primárias de evidência e 7 páginas oficiais de preço adicionadas às listas que o Mac baixa | `config/evidencias_fontes.json`, `research/fetch_policies.py` |
| Lista do que exige você amanhã | `research/AMANHA.md` |

## O que depende de você (em ordem)
1. Seguir `research/COMO_RODAR.md`: chave da API → `bash research/rodar.sh` → `bash research/install_launchd.sh`.
2. Me dizer "rodou" no chat. Eu leio os dados enviados e respondo aqui.
3. Se o coletor de evidências marcar `[MAN]`, fazer a coleta manual dos marketplaces (`research/EVIDENCIAS_MANUAL.md`).

## Gates
- **Gate 1** (fim da Fase 1): ranking em `reports/oportunidades.md` → você escolhe até 3 pilotos. Nada é criado antes.
- **Gate 2** (Fase 2): 3 amostras finalizadas + checklist de política por piloto → só publica com seu OK.
