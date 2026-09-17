# O que realmente precisa de você amanhã (Mac) — 2026-09-18

Tudo o que não dependia de você já foi feito hoje (ver `STATUS.md`). Abaixo só o que exige suas mãos, em ordem, com tempo estimado de atenção.

| # | Tarefa | Por que só você | Tempo | Como |
|---|---|---|---|---|
| 1 | **Criar a chave da YouTube Data API** e colar em `renda-automatizada/.env` | Exige conta Google e projeto no Google Cloud em seu nome | 10 min | `research/GUIA_YOUTUBE_API.md` |
| 2 | **Rodar o dia 1**: `bash research/rodar.sh` | Só o seu Mac alcança as páginas oficiais (Google, Amazon, Spotify, Etsy, Flippa, Empire Flippers); a rede desta sessão bloqueia todas | 5 min de atenção; ~2 h rodando sozinho | `research/COMO_RODAR.md` |
| 3 | **Agendar a coleta diária**: `bash research/install_launchd.sh` | Precisa do seu usuário do macOS (launchd) | 1 min | idem |
| 4 | **Conseguir enviar para o GitHub pelo Mac** (login no GitHub Desktop ou token) | Credencial é sua | 5 min (uma vez) | `research/COMO_RODAR.md`, passo 3 |
| 5 | **Empire Flippers, à mão** (só se o script marcar `[MAN]`, o que é provável): abrir as listagens de KDP e YouTube e copiar receita, lucro, horas/semana, equipe, idade e URL das que passarem de US$ 10 mil/mês. Prioridade: a listagem KDP com royalties de 40–80 mil/mês em dezembro | Site renderizado por JavaScript e parte dos números exige conta gratuita | 20–30 min | `research/EVIDENCIAS_MANUAL.md` |
| 6 | **Seus números da Jornada Green Card / Portal de Vagas**: tamanho da lista de e-mail, seguidores por rede, inscritos/views se houver canal, vendas/mês, preço, conversão | Não existe fonte pública; sem isso o candidato "ativo próprio" não pode ser pontuado | 10 min | colar aqui no chat (sem dados pessoais de clientes) |
| 7 | Me dizer **"rodou"** no chat | Eu leio o que subiu e entrego as respostas aqui | — | — |

Não precisa de você: análise das políticas baixadas, leitura dos dados do YouTube/KDP/marketplaces, ranking, relatório. Isso eu faço assim que os arquivos chegarem no repositório.

## Se der problema
- Erro no Terminal → cole a mensagem inteira aqui (nunca a chave).
- Amazon pediu captcha → normal; espere 1–2 h e rode `python3 research/kdp_coleta.py` de novo. Se insistir, coleta manual de 20 livros por nicho (`research/KDP_MANUAL.md`), ou me diga e reduzo a lista de nichos.
- `sync.sh` não conseguiu enviar → me mande a saída de `git status`.
