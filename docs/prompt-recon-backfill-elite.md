# MISSÃO: Reconnaissance GHL/Urable + Backfill de Score (40 dias) — Elite Premium Detailing

## Contexto

Você vai construir um sistema de gestão de leads para a Elite Premium Detailing (auto detailing, Miami). Esta é a **Fase 0**: levantamento completo do sistema atual + análise dos últimos 40 dias de leads. Nas próximas fases construiremos um pipeline de análise de chamadas e um painel de trabalho para o assistente (Eugene).

**REGRA ABSOLUTA DESTA FASE: somente leitura.** Não crie, edite ou delete NADA no GHL ou no Urable. Nenhum contato, tag, nota, task, workflow ou oportunidade deve ser modificado. Apenas GET requests. Toda a saída desta fase são arquivos locais.

**REGRA DE SEGURANÇA:** As credenciais estão no arquivo `.env`. Nunca imprima, logue ou inclua os valores das chaves em nenhum arquivo de saída, commit ou mensagem. Se o `.env` não existir, pare e peça ao Rafael para criá-lo — não peça as chaves no chat.

## Setup

1. Trabalhe na pasta do projeto (ex.: `~/elite-crm-system`). Se não existir, crie.
2. Verifique se existe `.env` com:
   ```
   GHL_API_TOKEN=...        (Private Integration token do GoHighLevel)
   GHL_LOCATION_ID=...      (Location ID da subconta da Elite)
   URABLE_API_KEY=...       (se o Urable tiver API — investigar)
   ```
3. Crie `.gitignore` incluindo `.env` ANTES de qualquer commit, se for usar git.
4. Use Python. Crie um `requirements.txt` e um ambiente virtual.
5. API do GHL: use a API v2 (`https://services.leadconnectorhq.com`), header `Authorization: Bearer {token}` e `Version: 2021-07-28`. Consulte a documentação oficial (highlevel.stoplight.io) para endpoints exatos — não invente endpoints.

## Parte 1 — Reconnaissance do GHL

Levante e documente:

1. **Pipelines e stages** — todos os pipelines, seus stages em ordem, e quantas oportunidades há em cada stage hoje. Identifique onde está o stage "Great Cars" e "Quote Sent" (ou equivalentes).
2. **Custom fields** — todos os campos customizados de contato e oportunidade (nome, tipo, opções). Precisamos saber onde ficam os dados do veículo (marca/modelo/ano) que vêm dos leads do Meta.
3. **Tags** — lista completa e contagem de uso, se disponível.
4. **Workflows/automações ativas** — nome, trigger e status de cada um. Em especial: o SMS automático de novo lead (9am–5pm) — documente o conteúdo da mensagem e as condições.
5. **Calendários e appointments** — estrutura dos calendários, appointments futuros, e como o sistema de confirmação por SMS está configurado.
6. **Usuários** — quem existe na conta (Rafael, Eugene, etc.) para futuras atribuições de tasks.
7. **Conversas e mensagens** — como acessar o histórico de SMS/conversas por contato via API. Verifique os templates de mensagem salvos (incluindo o "nice to talk to you" se existir como template/snippet).
8. **Gravações de chamadas** — PONTO CRÍTICO: verifique se as gravações de chamadas são acessíveis via API (endpoint de conversations/messages com tipo call, URL de recording). Documente exatamente como obter o áudio de uma chamada. Teste com 1–2 chamadas reais e confirme que o download funciona.
9. **Fonte dos leads** — como os leads do Meta chegam (campos preenchidos, source/attribution) e o que já vem estruturado.

## Parte 2 — Investigação do Urable

1. Verifique se o Urable possui API pública (documentação em urable.com ou dentro do app em Settings → Integrations/API).
2. Se houver API: autentique com a chave do `.env` e documente os endpoints disponíveis. **Pergunta-chave: é possível criar quotes/ofertas programaticamente?** Liste também clientes, serviços cadastrados e estrutura de uma quote existente.
3. Se não houver API utilizável, documente isso claramente — o fluxo será "Code prepara os dados → Eugene cria a quote manualmente".

## Parte 3 — Backfill e Score dos últimos 40 dias

Puxe todos os contatos/oportunidades criados nos últimos 40 dias e calcule o score de cada um.

### Modelo de score (0–100)

**Carro (0–35):**
- Exótico (Porsche, McLaren, Lamborghini, Rolls-Royce, Bentley, Ferrari, Aston Martin, Maserati, Lotus, e similares) OU premium (BMW M, Mercedes-AMG, Audi RS, Corvette, Tesla Plaid, e similares) = 35
- Qualquer marca ano 2025/2026 = 25
- Demais = 10
- (Se exótico/premium E 2025/2026, vale 35 — não soma.)

**Momento (0–25):** — só preenchível se houver dado (transcrição ou nota existente)
- Carro chegando / recém-entregue = 25
- Comprou há menos de 3 meses = 20
- Mais de 3 meses = 15
- Mais de 6 meses = 10
- Mais de 1 ano = 5
- Desconhecido = marcar como `?` (não pontuar como zero)

**Engajamento (0–25):** — extraído do histórico de conversas
- Pediu ligação explicitamente = 25
- Respondeu SMS = 15
- Atendeu uma chamada = 10
- Sem resposta = 0

**Intenção (0–15):** — só via transcrição de chamada
- Pediu quote / discutiu preço sem recuar = 15
- Interessado mas indeciso = 10
- Só pesquisando = 5
- Desconhecido = `?`

### Regras do backfill

- Score parcial é aceitável: reporte `score_conhecido / máximo_possível_com_dados` e liste os componentes faltantes.
- Se as gravações de chamada forem acessíveis (Parte 1, item 8): transcreva e analise as chamadas dos leads dos últimos 40 dias, priorizando os de maior score parcial, para completar Momento e Intenção. Use a API da Anthropic (chave `ANTHROPIC_API_KEY` no `.env`) para análise das transcrições; para transcrição de áudio, use uma solução local (ex.: whisper) ou pergunte ao Rafael qual serviço prefere antes de gerar custo.
- Exclua leads marcados como spam/teste, se identificáveis.
- Registre também: data de entrada, source, stage atual no pipeline, última atividade, se tem appointment marcado, e se houve no-show.

## Entregáveis (arquivos locais, nada gravado no GHL)

1. **`RECON_REPORT.md`** — relatório completo das Partes 1 e 2, organizado por seção, com suas observações sobre o que existe, o que está bem configurado e o que está faltando para o sistema que vamos construir. Inclua a resposta definitiva sobre: (a) acesso às gravações via API, (b) capacidade da API do Urable de criar quotes.
2. **`leads_score.csv`** — todos os leads dos 40 dias com: nome, telefone, data de entrada, veículo, ano, stage, componentes do score (com `?` onde faltar dado), score total, link direto do contato no GHL (`https://app.gohighlevel.com/v2/location/{locationId}/contacts/detail/{contactId}`).
3. **`TOP_PRIORITIES.md`** — a fila de trabalho do Eugene para amanhã: top 20 leads em ordem de score, cada um com: score e por quê, contexto conhecido (veículo, engajamento, última interação), ação recomendada (ligar / follow-up / enviar quote) e o link direto no GHL. Inclua uma seção separada com leads que pediram ligação e nunca foram atendidos — esses vão pro topo independente de score.
4. **`GAPS_E_RECOMENDACOES.md`** — o que você descobriu que precisa ser corrigido ou criado no GHL antes das próximas fases (custom fields faltantes, workflows a criar, dados inconsistentes).

## Ao final

Apresente um resumo do que foi encontrado e aguarde instruções. O Rafael vai levar os relatórios para revisão antes de autorizarmos qualquer escrita no GHL.

---

## ADENDO — Levantamentos adicionais (mesma fase, somente leitura)

10. **Transferências de chamada** — investigue como uma chamada transferida (Eugene → Rafael) aparece nos dados da API (evento de transfer? duas calls encadeadas? campo específico?). Documente com um exemplo real, se existir no histórico.
11. **Appointments e no-shows** — além da estrutura dos calendários (item 5), levante dos últimos 40 dias: appointments criados, status de cada um (confirmed, showed, no-show, cancelled) e como o status é registrado via API. Liste os no-shows dos 40 dias no `leads_score.csv` (coluna própria) — eles serão a base da lista de cold calls.
12. **Links do Urable nas conversas** — busque no histórico de SMS dos últimos 40 dias mensagens contendo links do Urable (domínio urable.com ou similar). Documente o padrão do link (formato da URL) — o sistema futuro vai detectar envio de quote por esse padrão.
13. **Onde as vendas são registradas** — investigue onde uma venda fechada aparece: oportunidade movida para stage "won" no GHL? Registro no Urable (invoice/job)? Ambos? Documente o caminho do dado de faturamento — será usado no fechamento mensal (Fase 2).
14. **Eventos com timestamp para detecção de atividade** — confirme quais eventos retornam timestamp confiável via API (calls, mensagens outbound, notas, edição de campos, criação de appointment). Essa lista define o "heartbeat" do monitoramento de atividade do assistente.

Inclua os achados 10–14 no `RECON_REPORT.md`, em seções próprias.
