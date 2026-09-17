# Guia: criar a chave da YouTube Data API v3 (gratuita)

Tempo: ~10 minutos. Não precisa de cartão de crédito. A chave é gratuita e vem com
10.000 "unidades" de quota por dia (fonte oficial: https://developers.google.com/youtube/v3/getting-started — confira lá o valor no dia em que ler).

> Regra de ouro: a chave é um segredo. Ela só vai no arquivo `.env`, que nunca entra no git.

## Passo 1 — Entrar no Google Cloud Console
1. Abra https://console.cloud.google.com no navegador.
2. Entre com a conta Google que você quer usar para o projeto (pode ser a mesma do futuro canal, mas não precisa).
3. Se aparecer um termo de uso, aceite.

## Passo 2 — Criar um projeto
1. No topo da página há um seletor de projeto (um botão com o nome de um projeto ou "Select a project"). Clique nele.
2. Clique em **New Project** (Novo projeto).
3. Nome do projeto: `renda-automatizada`. Organização: deixe "No organization". Clique **Create**.
4. Espere alguns segundos. Depois clique no seletor de novo e escolha `renda-automatizada` para garantir que ele está selecionado.

## Passo 3 — Ativar a YouTube Data API v3
1. Menu ☰ (canto superior esquerdo) → **APIs & Services** → **Library**.
2. Na busca digite `YouTube Data API v3` e clique no resultado.
3. Clique em **Enable** (Ativar).

## Passo 4 — Criar a chave
1. Menu ☰ → **APIs & Services** → **Credentials**.
2. Clique em **+ Create Credentials** → **API key**.
3. Vai aparecer a chave (começa com `AIza...`). Copie e guarde num lugar seguro por um minuto.

## Passo 5 — Restringir a chave (importante, evita uso indevido)
1. Ainda em **Credentials**, clique no nome da chave criada (ex.: "API key 1").
2. Em **Name**, renomeie para `renda-automatizada-mac`.
3. Em **API restrictions**, marque **Restrict key** e selecione só **YouTube Data API v3**. Salve.
4. Deixe **Application restrictions** em "None" por enquanto (scripts rodando no seu Mac não têm um site ou IP fixo).

## Passo 6 — Guardar a chave no `.env`
No Terminal do Mac, dentro da pasta do repositório:

```bash
cp renda-automatizada/.env.example renda-automatizada/.env
open -e renda-automatizada/.env
```

Cole a chave depois de `YOUTUBE_API_KEY=` (sem aspas, sem espaço). Salve e feche.

## Passo 7 — Testar (gasta 1 unidade de quota)
```bash
cd renda-automatizada
python3 research/test_key.py
```
Saída esperada: o nome e as estatísticas do canal oficial do YouTube, e a linha `quota gasta hoje: 1 unidade`.
Se der erro 403 com "API key not valid" → refaça o Passo 4. Se der 403 "quotaExceeded" → espere o reset (meia-noite, horário do Pacífico).

## Como a quota é gasta (por que cacheamos)
Fonte oficial da tabela de custos: https://developers.google.com/youtube/v3/determine_quota_cost (leia para confirmar os valores do dia).

| Método | Custo (unidades) | Uso no projeto |
|---|---|---|
| `search.list` | 100 | Só para DESCOBRIR canais/vídeos novos. Resultado cacheado por 7 dias. |
| `channels.list` | 1 | Snapshot diário de `viewCount`/`subscriberCount` (mede views/mês por delta). |
| `videos.list` | 1 | Estatísticas e duração de até 50 vídeos por chamada. |
| `playlistItems.list` | 1 | Listar os uploads de um canal (50 por página) em vez de `search.list`. |

Nota (fonte secundária, ver `config/policies.md` §Y-08): em 2026 o Google teria movido `search.list` e `videos.insert` para "baldes" próprios com limite de ~100 chamadas/dia cada. O cliente `research/yt_client.py` conta `search.list` como 100 unidades E limita a 90 chamadas/dia, o que é seguro nos dois cenários.

## Se você travar
Me mande a mensagem de erro inteira (pode colar aqui). Não mande a chave.
