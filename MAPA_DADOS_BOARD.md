# MAPA REAL DE DADOS DO BOARD (como o código funciona HOJE)

Lido do código real: `worker/board_sync.py` (cria/fecha os cards no Supabase) e
`web/components/BoardView.js` (desenha). Não é a spec — é o que roda. Foco em achar
falha, então os ⚠ são o mais importante.

## Como os dados chegam na tela (visão geral)
- **Fonte da verdade da TELA = Supabase `board_cards`** (nunca lê o GHL pra desenhar).
  `page.js` carrega a cada **20s** + **realtime** do Supabase em `board_cards` (throttle 1.5s) + ping `/api/delta` 60s.
- **Quem escreve `board_cards` = 2 caminhos:**
  1. **Worker `board_sync.py`** (polling): bridge roda a cada ~2min, MAS só em **horário comercial seg-sáb 9-17 ET** (Lote 1). Fora disso NÃO roda.
  2. **Webhooks `/api/ghl-event`** (tempo real, <5s): `Board Stage/Reply/call/booked/appt status`.
- **Dados do card** vêm de `contact_brief(cid)` (GHL `/contacts/{id}`, **cache 4h** ou forçado no delta) + `contact_tasks(cid)` (GHL `/contacts/{id}/tasks`, **cache 45min** ou forçado) + `last_note_for(cid)` (GHL `/contacts/{id}/notes`).
- **`contact_brief` monta:** `nome`=firstName+lastName · `phone`=contact.phone · `veh`=customFields year/make/model · `interest`=customField CF_INTEREST **ou** 1º custom field que contenha ppf/coating/wrap/tint · `tags` · `dnd`.

---

## Coluna 1 — "Return · Reply · Hot" (kinds: hot, missed_inbound, sms_reply)
- **GATILHO:**
  - `hot`: opp em stage **"HOT LEADS"** (STAGE_COLS: `"HOT LEADS": (1,"hot")`), via `paged_opps(STAGES["HOT LEADS"])`.
  - `missed_inbound`: call **inbound sem duration** (`c["direction"]=="inbound" and not c["duration"]`) nos últimos `col1_days` (3d), **sem** retorno outbound depois, e sem appointment.
  - `sms_reply`: última msg da conversa é **inbound** (`conv_last[cid].direction=="inbound"`) dentro da janela, e não é cortesia/misdial.
- **FONTE DOS DADOS:** nome/veh/interest/phone = `contact_brief` (cache 4h). origem_ts = ts da call/SMS. last_note = `/contacts/{id}/notes`.
- **FECHA/REMOVE:** missed → **retorno de call** feito (outbound depois) OU appointment marcado OU cortesia SMS. sms_reply → **resposta enviada** (SMS outbound não-workflow depois) OU cortesia OU tem appointment. hot → **stage saiu** de HOT LEADS OU appointment futuro (regra Peter). Todos → **DND ativado** (spam).
- **FREQUÊNCIA:** webhooks `Board call` (Call Status), `Board Reply` (Customer Replied), `Board Stage` (Pipeline Stage Changed) = tempo real. + worker 2min (só 9-17).
- **⚠ DADO FALTANDO:** `veh`/`interest` quase sempre vazios no GHL → "—"/"interest not set". `nome` vazio se o contato não tem firstName/lastName.
- **⚠ RISCO:** (a) call "answered" = `duration>0`; **voicemail de 56s conta como atendida** (caso Shandor) — mitigado só se o stage avançou depois. (b) `missed_inbound` depende do scan de conversas achar a call; se o webhook `Board call` não chega E o worker está fora de horário, **não aparece até 9h**. (c) misdial/cortesia é detectado por lista de palavras (`no_action_reply`) — texto fora da lista escapa.

## Coluna 2 — "New Leads — Call ASAP" (kind: new_lead)
- **GATILHO:** opp em stage **"New Lead"** OU **"Great Cars"** (ambos mapeados: `(2,"new_lead")`). Great Cars ganha `grupo="great_car"` (badge azul, "call FIRST") + a tag "great cars" é aplicada no contato.
- **FONTE:** igual col1 (contact_brief, cache 4h).
- **FECHA/REMOVE:** stage saiu de New Lead/Great Cars · appointment futuro · envelhecimento > `col2_days` (7d) → vira ração warm-up.
- **FREQUÊNCIA:** webhook `Board Stage` + worker.
- **⚠ DADO FALTANDO:** idem (veh/interest).
- **⚠ RISCO:** **contato com 2 opps** — o espelho dedup por `opp_id` (mantém o de `lastStageChangeAt` mais novo), mas se o contato tem opps em stages diferentes, `opps[cid]` guarda os 2 → pode gerar card em 2 colunas. Great Cars: a priorização depende da tag "great cars" persistir; se a tag some, perde o "call FIRST".

## Coluna 3 — "Today's tasks — Quotes · Follow-ups" (kinds: quote_task, followup, task, urable)
- **GATILHO:** para cada contato do `task_universe` (opps + cards abertos + Follow Up + Quote Sent), busca `contact_tasks(cid)`; se tem task **due hoje ou vencida** (dueDate ≤ hoje, não completa): cria card. `kind` = quote_task (se Quote Sent) / followup (se Follow Up) / task (senão). `grupo="overdue"` se vencida (vermelho). `urable`: SMS com link Urable sem resposta.
- **FONTE:** task title/dueDate = `/contacts/{id}/tasks` (**cache 45min** ou forçado no delta). nome/veh = contact_brief. Ordena pela **mais vencida primeiro**; **1 card por contato**.
- **FECHA/REMOVE:** task **concluída** OU **sumiu** do GHL OU **reagendada pro futuro** OU **opp virou Lost/Won**. Dedup fecha cards de task extras do mesmo contato.
- **FREQUÊNCIA:** **SÓ POLLING** (o webhook `Board Task` NÃO está publicado — é o rascunho pendente). Fechamento em tempo real só depois de publicar. Contato "mudou" (call/sms/stage) força re-busca; senão cache 45min. **Atraso: até 45min** (ou até 9h se fora de horário).
- **⚠ DADO FALTANDO:** task sem dueDate é ignorada. Contato sem opp aberto: card de task fecha (regra "só lead ativo").
- **⚠ RISCO:** (a) tasks **metadados** (ex.: "Spanish") aparecem como task real → ruído. (b) 45min de atraso pra refletir conclusão sem o webhook. (c) se a API de tasks falha, usa **cache velho** (pode mostrar task já concluída por até 45min).

## Coluna 4 — "Pipeline — Contact 1/2/3" (kind: pipeline)
- **GATILHO:** opp em **Contact 1 (AM/PM)**, **Contact 2 (AM/PM)**, **Contact 3 (AM/PM)** → `(4,"pipeline")`.
- **FONTE:** contact_brief (cache 4h). Ordena **mais novo primeiro**; Great Cars no topo.
- **FECHA/REMOVE:** stage saiu · 2 movimentos de stage hoje (`moves_today>=2` = "done till tomorrow") · appointment futuro · envelhecimento > `pipeline_days`.
- **FREQUÊNCIA:** webhook `Board Stage` + worker.
- **⚠ RISCO:** o "sem resolução" (faixa vermelha) atrela a última call ao card; **voicemail longo lido como conversa real** cobra categorização indevida (mitigado por "stage avançou depois da call = resolvido" via `lastStageChangeAt`). Contato com 2 opps: mesmo risco da col2.

## Coluna 7 — "Needs attention — no task" (kinds: followup_notask, quote_notask)
- **GATILHO:** opp em **Follow Up** ou **Quote Sent** que **NÃO tem** task pendente com data (`contact_tasks` vazio) → card vermelho "needs a decision".
- **FECHA/REMOVE:** quando **uma task com data passa a existir** (o Eugene cria a task).
- **FREQUÊNCIA:** **SÓ POLLING** (depende de `contact_tasks`, sem webhook de task). Atraso até 45min.
- **⚠ RISCO:** se a API de tasks falha → trata como "sem task" (mitigado: `contact_tasks` retorna cache velho ou None). Mesmo atraso da col3.

## Coluna 5 — "Appointments · next 2 days" (kinds: appt_confirm=to_confirm, appt_info=confirmed)
- **GATILHO:** appointment nos **próximos 2 dias** (janela = hoje 00:00 → hoje+2 dias 00:00), lido de `/calendars/events` dos 3 calendários. status "confirmed" → `appt_info` (verde); senão → `appt_confirm` (a confirmar). Cancelado → card de reschedule (col6). "showed"/noshow/invalid → não cria.
- **FONTE:** appt_start, status = `/calendars/events`. last_note = `/contacts/{id}/notes` (nota do contato). nome/veh = contact_brief.
- **FECHA/REMOVE:** appt_confirm fecha quando status→**confirmed** (aí appt_info assume) OU cancelado/showed OU passou 3h. appt_info fecha quando **showed** OU voltou a não-confirmado OU passou.
- **FREQUÊNCIA:** webhooks `Board booked` (Customer Booked) + `Board appt status` (Appointment Status) = tempo real. + worker.
- **⚠ DADO FALTANDO:** appt_info confirmado costuma vir **sem nota** → mostra "no notes on contact yet".
- **⚠ RISCO:** **janela de 2 dias é medida do início de HOJE** → appointment daqui a exatamente 2 dias (ex.: hoje qui, appt sáb) **fica de fora até amanhã** (caso Melissa: confirmada no GHL mas não aparece hoje). Horário do card pode divergir por timezone. Se o contato tem 2 appointments, o card usa o `event_id` — mas a lista pode ter mais de um.

## Coluna 6 — "Warm up" (kind: warmup)
- **GATILHO:** pool montado pelo worker: **no-shows** (reschedule), **Lost recuperável**, leads **30d+ parados**. Ração diária (~20/dia) libera do topo por prioridade (reschedule → best car → resto). Cancelamentos de appointment também criam reschedule aqui.
- **FONTE:** contact_brief (cache 4h). Prioridade por ano do veículo (texto).
- **FECHA/REMOVE:** virou card ativo (chamou) · DND · appointment · reschedule "ignorado" pelo Eugene (por event_id).
- **FREQUÊNCIA:** **SÓ POLLING** — o pool é montado 1x/dia pelo worker, sem webhook.
- **⚠ RISCO:** o warm-up é o "balde" de recuperável; tag de exclusão errada (lost-invalid-number) muda quem entra. Pool grande (centenas) — priorização por ano do veículo depende de o ano estar no texto.

---

## CARD VERDE (metas do Eugene) — cada contador

## Calls today (`validToday` / goal)
- **FONTE:** `board_attempts` (tabela Supabase) filtrado `user_key=="eugene" && valid`. goal = `cfg.goal_calls` (100).
- **`valid`** é calculado pelo worker: `answered` (status "completed" OU duration≥25s) **OU** (duration≥25s **+ SMS manual do mesmo user em ≤10min**).
- **FREQUÊNCIA:** `board_attempts` é escrito pelo **worker** ao varrer conversas (polling). **Sem webhook de call-attempt** → depende do scan (2min, horário comercial).
- **⚠ RISCO:** **voicemail de 25s+ com um SMS manual conta como válida** → pode superestimar. Se o worker está fora de horário/caído, `validToday` congela (foi a causa do "inatividade falsa").

## Sales goal / Your wins (`wonN`, `earned`)
- **FONTE:** `board_commissions`. `won` = `eligible && status=="won"`. `earned` = escada $10 até t1(30), $20 de 31-40.
- **Elegibilidade:** `created_by==Eugene` OU **confirmação ativa** do Eugene ≤48h (call atendida ou SMS manual dele) antes de qualquer confirmação automática.
- **FREQUÊNCIA:** worker (comissões calculadas no ciclo). Polling.
- **⚠ RISCO:** **atribuição** — se a confirmação ativa não é detectada, a venda não conta pro Eugene (ou conta pra automação). Booking online (cliente se agendou) só conta com confirmação ativa dele.

## Potential (`potential`, `awaiting`)
- **FONTE:** `board_commissions` com status em (done_waiting, confirmed, booked) × taxa do próximo tier.
- **⚠ RISCO:** é uma **projeção** (dinheiro pendente de confirmação/venda), não garantido. Se o appointment não vira venda, "expira".

## Clean-board bonus (`cleanDays`, `bonusLost`)
- **FONTE:** `board_days` (flag `clean` por dia). Clean day = 100 calls válidas + zero unresolved + confirmações + tasks do dia feitas.
- **FREQUÊNCIA:** worker escreve `board_days`. Polling.
- **⚠ RISCO:** depende de TODOS os sinais estarem corretos (calls válidas, unres, tasks) — se qualquer um está frágil (voicemail, task com atraso), o "clean day" pode marcar errado.

---

# 3 LISTAS CONSOLIDADAS (pra caçar falha)

## 1. Dados que o board depende mas podem estar VAZIOS/faltando na fonte
- **`veh` (veículo)** — só de customFields year/make/model do GHL; quase sempre vazio → "—". (O worker NÃO usa o nome da opp como fallback, mesmo o carro estando lá.)
- **`interest`** — customField CF_INTEREST ou heurística de palavra; vazio → "interest not set".
- **`nome`** — firstName+lastName; contato sem nome → "—".
- **`last_note`** — só busca em criação de card OU contato com atividade recente; appointment confirmado costuma vir sem nota.
- **`dueDate` da task** — task sem data é ignorada (não vira card).
- **ano do veículo** (warm-up priority) — se não está no texto do veículo, prioriza errado.

## 2. Suposições do código que podem estar ERRADAS
- **Duração da call = atendimento:** `duration>0` = "answered", `≥25s` = "conversa real". **Voicemail longo engana** (Shandor). Mitigado só se stage avançou depois.
- **Contato com 2+ opps:** dedup por `opp_id`, não por contato → pode gerar card em 2 colunas / ler a opp "errada".
- **Janela de appointment "2 dias" medida do início de HOJE** → appt daqui a 2 dias some até amanhã (Melissa).
- **Cortesia/misdial por lista de palavras** — texto fora da lista escapa e vira card de resposta.
- **Elegibilidade de comissão** por "confirmação ativa ≤48h" — detecção pode falhar → atribuição errada.
- **Cache:** se a API do GHL falha, usa **cache velho** (brief 4h / tasks 45min) → pode mostrar dado desatualizado (task já concluída, stage já mudado) por até o TTL.
- **`valid` call com SMS manual** — voicemail 25s+ SMS conta como válida → superestima a meta.

## 3. Cards que atualizam SÓ por POLLING (sem webhook) — maior atraso
- **Coluna 3 (tasks: quote_task/followup/task)** — o webhook `Board Task` **não está publicado** (rascunho pendente). Fechamento/abertura só pelo worker: **até 45min** (cache) e **nada fora de 9-17 seg-sáb**.
- **Coluna 7 (needs attention — no task)** — mesma dependência de tasks, sem webhook.
- **Coluna 6 (Warm up)** — pool montado 1x/dia pelo worker, sem webhook.
- **Contadores do card verde** (`validToday`, `wonN`, `board_days`) — escritos pelo worker no ciclo; **sem webhook** → congelam se o worker cai/está fora de horário.
- **Janela de appointment da col5** — os webhooks `Board booked/appt status` atualizam o STATUS em tempo real, mas **QUAIS appointments entram na janela de 2 dias** é decidido pelo worker (polling) — um appt que entra na janela à meia-noite só aparece no 1º ciclo das 9h.

> **Ponto mais frágil hoje:** tudo que depende de **task** (col3, col7, "tasks do dia" do clean-day) roda **só por polling** porque o `Board Task` não foi publicado — atraso de até 45min em horário comercial e **zero atualização fora dele**. Publicar o `Board Task` fecha esse buraco.
