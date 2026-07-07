# RECON REPORT — Elite Premium Detailing (Fase 0, somente leitura)

> Status: **COMPLETO** (Partes 1, 2, 3 + adendo 10–14). Transcrição de chamadas fica para a próxima fase (áudio já confirmado acessível).
> Data: 2026-07-07. Todas as chamadas desta fase foram `GET` (somente leitura). Nenhuma escrita no GHL ou Urable.
>
> **Location:** Elite Premium Detailing - Ceramic Coating & PPF · timezone America/New_York · 23.496 contatos · 3.977 oportunidades.

## Respostas definitivas (as duas perguntas críticas)
- **(a) Gravações de chamada acessíveis via API? SIM.** `GET /conversations/messages/{messageId}/locations/{locationId}/recording` devolve o áudio `audio/x-wav`. Testado com 3 chamadas reais — download OK (3,2 / 6,4 / 4,7 MB). **GHL não transcreve** (endpoint de transcription = 404) → transcrição é por nossa conta (whisper).
- **(b) API do Urable cria quotes? NÃO.** Só expõe Customers e Items. Fluxo: Code prepara dados → Eugene cria a quote manual. Detecção de quote enviada pelo link `go.urable.com/…`.

---

## Estado das credenciais

| Serviço | Chave | Status |
|---|---|---|
| GoHighLevel | `GHL_API_TOKEN` (Private Integration, `pit-…`) | ✅ Autentica. Token é **location-scoped** (o endpoint de agência `/locations/search` retorna 403 — esperado). |
| GoHighLevel | `GHL_LOCATION_ID` | ❌ **FALTANDO.** Sem ele, nenhuma chamada de dados do GHL funciona (`422 "LocationId can't be undefined"`). Bloqueia Partes 1 e 3. |
| Urable | `URABLE_API_KEY` (JWT) | ✅ Autentica (`GET /auth → 200 {"success": true}`). |
| Anthropic | `ANTHROPIC_API_KEY` | ⏳ Ainda não preenchida (necessária só na fase de transcrição/análise de chamadas). |

As credenciais estão em `.env` (gitignored). Nenhum valor foi impresso, logado ou commitado.

---

## PARTE 2 — Urable (CONCLUÍDA)

### 2.1 Existe API pública? **SIM.**
- **Documentação:** https://api.urable.com/ (renderizada em JS; bloqueia fetch automático, lida via navegador).
- **Base URL (produção):** `https://app.urable.com/api`
- **Autenticação:** header `Authorization: Bearer <ACCESS_TOKEN>` + `Content-Type: application/json`.
  - O token é o **Access Token do usuário admin**, obtido em Urable → **Settings → Developer → Access Token → SHOW**.
  - Teste de auth: `GET /api/auth` → `{"success": true}`. ✅ Confirmado com o token da Elite.
- **Rate limit:** 1000 requisições/hora; excedeu → HTTP 429.
- **Conta (do JWT):** `accountId = lMzctANozq9gRYDFAjyJ`.

### 2.2 Endpoints disponíveis (TODOS os que a API expõe)
A API pública tem **apenas dois recursos**: Customers e Items. Cada um com CRUD completo.

**Customers** (`/api/v1/customers`) — pessoas/empresas para quem os Jobs/Orders são criados:
- `POST /v1/customers` — criar
- `PATCH/PUT /v1/customers/{id}` — atualizar
- `GET /v1/customers/{id}` — recuperar
- `GET /v1/customers?email=&startAfter=&endBefore=&limit=` — listar (paginação por cursor)
- `DELETE /v1/customers/{id}` — deletar

**Items** (`/api/v1/items`) — a posse do cliente sobre a qual o serviço é feito (para a Elite = **o veículo**):
- `POST /v1/items` — criar
- `PATCH/PUT /v1/items/{id}` — atualizar
- `GET /v1/items/{id}` — recuperar
- `GET /v1/items?limit=` — listar
- `DELETE /v1/items/{id}` — deletar

### 2.3 PERGUNTA-CHAVE: dá para criar quotes/ofertas via API? **NÃO.**
A API **não expõe** quotes, estimates, ofertas, jobs, orders, invoices, serviços (line items) nem appointments. Só Customers e Items. Embora a doc mencione "Jobs/Orders", **não há endpoint** para eles.

**Consequência para o sistema:** o fluxo de quote **não pode ser automatizado ponta-a-ponta**. Modelo obrigatório:
> **Code prepara os dados (cliente + veículo + serviços sugeridos + preço) → Eugene cria a quote manualmente no Urable.**

O que o Code *pode* automatizar via API (fase futura, com autorização de escrita): criar/atualizar o **Customer** e o **Item (veículo)** no Urable a partir do lead do GHL, deixando tudo pronto para o Eugene só montar a quote.

### 2.4 Estrutura dos dados (amostra real, PII omitida)

**Customer:**
```
id, name, firstName, lastName, type ("person"|"business"), status ("new"...),
emails[{value,label}], phoneNumbers[{value,label}], phoneNumberValues[],
notes (texto livre — frequentemente contém o VEÍCULO, ex.: "GLC 300"),
origin (ex.: "New Pipeline"), zapier (bool — indica entrada via Zapier),
created{uid,timestamp}, modified{uid,timestamp}
```

**Item (veículo):**
```
id, name (ex.: "2026 TESLA Model Y"), industry "vehicleCare", type "automotive",
metadata { make, model, year, trim, submodel, factoryColor{name,rgb}, vins[], licensePlates[] },
customerRef ("accounts/{accountId}/customers/{customerId}"), customerName,
notes, photoURL, customData[], created{...}, modified{...}
```

**Achado relevante para o score (Carro):** o Urable guarda **make / model / year / VIN** de forma estruturada no Item, e o `notes` do Customer costuma ter o veículo. Isso é uma **segunda fonte** para o componente Carro do score, cruzável com os leads do GHL por telefone. Os leads chegam ao Urable via **Zapier** (`zapier: true`, `origin: "New Pipeline"`).

### 2.5 Serviços cadastrados
Não expostos na API pública (fazem parte de Jobs/quotes, que não têm endpoint). Levantar manualmente no app se necessário para a lógica de preço.

---

## PARTE 1 — GoHighLevel (CONCLUÍDA)

### 1.1 Pipelines e stages (com contagem HOJE)
Dois pipelines. **O ativo é "New Pipeline"** (é onde entram os leads via Zapier/Urable). O "ELITE ADS" é legado mas ainda recebe opps.

**ELITE ADS** (`gxSzYT8gC2sYY1QrXnDZ`) — total 2.269:
`FOLLOW UP-CHECK LEAD` 5 · `NEW LEADS-CALL ASAP` 30 · **`GREAT CARS` 18** · `HOT LEADS` 267 · `Day1 No Answer1` 19 · `Day1 2nd Call` 2 · `Day2 No Answer2` 0 · `Day2 3rd Call` 2 · `Day3 No Answer3` 2 · `Day3 4th Call` 0 · `NEVER ANSWERED-REMARKETING` 698 · `NOT INTERESTED` 740 · `APPOINTMENT BOOKED` 486

**New Pipeline** (`oUL5N3vxYqL13sBLrZUF`) — total 1.704:
**`Great Cars` 9** · `New Lead` 7 · `Contact 1 (AM)` 212 · `Contact 1 (PM)` 5 · `Contact 2 (AM)` 121 · `Contact 2 (PM)` 7 · `Contact 3 (AM)` 0 · `Contact 3 (PM)` 0 · `Follow Up` 183 · **`Quote Sent` 11** · `Appointment Booked` 161 · `Win` 115 · `Lost` 873 · `delete` 0

- **"Great Cars"**: existe nos dois (é o balde de carro-alvo). **"Quote Sent"**: `708575b3-2b8e-4bd8-91cb-a2fb4774484a` (só no New Pipeline).
- Funil New Pipeline: entra em New Lead → Contact 1/2/3 → Follow Up → Quote Sent → Appointment Booked → **Win** (115) / **Lost** (873). Taxa Win/Lost ≈ 12%.

### 1.2 Custom fields
- **Oportunidade: 0 custom fields.** **Contato: 12.** Os dados do veículo do Meta ficam no CONTATO:
  - `contact.vehicle_make`, `contact.vehicle_model`, `contact.vehicle_year` (todos TEXT).
  - `contact.how_soon_are_you_looking_to_get_this_done` — **quando quer fazer o serviço** (preenchido em 214/330 dos últimos 40d).
  - `contact.what_services_are_you_interested_in`, `contact.questions_for_us` (LARGE_TEXT).
  - `contact.user_provided_phone_number`, e `utm_source/medium/campaign/content/term`.
- ⚠️ Ano é TEXT (não numérico). Só 47/330 leads recentes têm `vehicle_make` — o resto tem o carro só no NOME da oportunidade.

### 1.3 Tags — 163 tags no total (dump em `out/tags.json`). 13 custom values (`out/custom_values.json`).

### 1.4 Workflows/automações — 100 retornados (60 published, 40 draft)
⚠️ **Limitação da API:** o endpoint de workflows devolve só nome/status/id — **não expõe os passos internos nem o texto das mensagens**. O conteúdo do SMS foi levantado **empiricamente** nas conversas (ver 1.7).
Automação de **novo lead (SMS)**: cadeia `00: New Lead Submitted - ADS` → `0: Opt-in - Ads` → `1: FIRST SMS - Ads`. O primeiro SMS automático (confirmado no histórico):
> *"Hey {name}! How are you doing today? This is Rafael from Elite Premium Detailing - Ceramic Pro Hollywood. I just received your request for Ceramic Pro PPF / Coatings for your car. Is now a good time to help you with that through text?…"*

Outras automações relevantes publicadas: `2.1: GREAT CARS - ADS`, cadeias `Contact 1/2/3 AM/PM`, `NO ANSWER` (Ads/Ceramic/PPF), `Appointments Booked`, `Phone APPT Booked`, `6: No Show`, `Lost Deal - Unable to reach`, `Remarketing - Leads Perdidos Meta`, `CAPI - META ADS`, `CAPI - Purchase / Sold`, **`Nedzo AI | Add To List` / `Nedzo AI | End Of Call Report`** (há um discador/IA "Nedzo AI" integrado), `Create opportunity via incoming Phone call`.

### 1.5 Calendários e appointments
- **20 calendários** (dump em `out/calendars.json`), a maioria "Personal Calendar". Booking real cai em: `Booking Request` (`iktsAzvv6tKgKOyPrxWJ`), `ELITE BOCA RATON`, `Ceramic Pro Silver Package`.
- Appointments por contato: `GET /contacts/{contactId}/appointments` → lista `events` com `appointmentStatus` ∈ {`confirmed`, `showed`, `noshow`, `cancelled`, `invalid`}, `startTime`, `calendarId`, `address`. Confirmação por SMS existe (templates em 1.7).

### 1.6 Usuários — apenas 2, ambos admin
- **Eugene Baruelo** `eugenebaruelova@gmail.com` (id `EbVhbGHnGfuvbQurQoga`) — o assistente.
- **Rafael Oliveira** `rafael.oliveira91@icloud.com` (id `7dYD2aALTReBpvw0YYCM`, phone +13216953824).

### 1.7 Conversas, mensagens e templates
- Buscar conversa: `GET /conversations/search?locationId=&contactId=`. Mensagens: `GET /conversations/{conversationId}/messages` → `messages.messages[]`.
- Tipos observados: `TYPE_SMS`, `TYPE_EMAIL`, `TYPE_CALL`, `TYPE_INSTAGRAM`, `TYPE_ACTIVITY_APPOINTMENT`, `TYPE_ACTIVITY_OPPORTUNITY`, **`TYPE_ACTIVITY_INVOICE`** (invoice do Urable ecoando no GHL).
- Cada mensagem tem `direction` (inbound/outbound), `dateAdded`, `body` (SMS/email), e calls têm `meta.call.duration`+`status`, `userId` (quem discou), `from/to`.
- Templates capturados: primeiro SMS (1.4), confirmação de appointment, lembrete automático de appointment, "here's a link… go.urable.com/…" (envio de quote).

### 1.8 Gravações de chamada — PONTO CRÍTICO ✅
- `GET /conversations/messages/{messageId}/locations/{locationId}/recording` → `audio/x-wav`, download testado e funcionando (3 chamadas reais).
- **Não há transcrição via GHL.** Plano: baixar WAV → whisper (local) → análise com Claude.

### 1.9 Fonte dos leads (Meta/Google)
- Leads chegam com custom fields do formulário (veículo, serviços, how_soon, utm_*). No Urable, entram via **Zapier** (`origin: "New Pipeline"`).
- ⚠️ O campo `source` da oportunidade está **poluído** (recebe texto livre do veículo). Atribuição limpa só em `Google` (53), `Call Google Ads` (34), `Facebook` (2); 41 sem source. Ver GAPS #2.

---

## ADENDO — itens 10 a 14

### 10. Transferências de chamada (Eugene → Rafael)
- Não há um "evento de transfer" dedicado na API. O que existe: cada `TYPE_CALL` traz `direction`, `meta.call.duration/status`, `userId` (quem originou/atendeu) e `source`. Uma transferência aparece na prática como **chamadas encadeadas** no mesmo contato com `userId` diferente. Dá para inferir transfer comparando `userId` entre calls próximas no tempo, mas **não é um campo explícito**. Recomenda-se confirmar com um caso conhecido; nos 40 dias os contatos com >1 call por `userId` distinto são candidatos.

### 11. Appointments e no-shows (40 dias)
- Via `GET /contacts/{contactId}/appointments` + `appointmentStatus`. Nos 40 dias: **67 leads com appointment**, **15 no-shows** (`appointmentStatus="noshow"`). Coluna `no_show` no `leads_score.csv`. Status também: `confirmed`, `invalid`, `cancelled`, `showed`.

### 12. Links do Urable nas SMS (detecção de quote)
- Padrão confirmado: **`https://go.urable.com/{shortcode}`** (ex.: `go.urable.com/5aWeqD`). É um encurtador do Urable. Nos 40 dias, **8 leads** receberam esse link (coluna `urable_link_enviado`). É o gatilho para marcar "quote enviada".

### 13. Onde a venda é registrada
- **Dois lugares:** (1) oportunidade movida para stage **`Win`** no New Pipeline (115 no total; 26 nos últimos 40d) e (2) **invoice/job no Urable**, que ecoa no GHL como `TYPE_ACTIVITY_INVOICE` na conversa do contato. Para faturamento (Fase 2), o valor confiável vem do Urable (invoice); o `Win` do GHL marca o fechamento no funil. `monetaryValue` da opp existe mas veio 0 na amostra — não confiável ainda.

### 14. Eventos com timestamp confiável (heartbeat de atividade do assistente)
Retornam timestamp utilizável:
- **Mensagens** (SMS/email/call): `dateAdded`/`dateUpdated` por mensagem.
- **Calls**: `dateAdded` + `meta.call.duration` (duração real).
- **Oportunidade**: `createdAt`, `updatedAt`, `lastStageChangeAt`, `lastStatusChangeAt`.
- **Appointment**: `dateAdded`, `dateUpdated`, `startTime`.
- Notas de contato: `GET /contacts/{id}/notes` (têm `dateAdded`). Edição de custom field não gera evento próprio confiável — melhor usar `contact.dateUpdated`.
Esses são o conjunto de sinais para medir se o Eugene está ativo (ligou/mandou SMS/moveu stage/criou appointment).

---

## PARTE 3 — Backfill de score (40 dias) — CONCLUÍDA

- **330 oportunidades** criadas entre 2026-05-28 e 2026-07-07. Entregável: **`leads_score.csv`** (ordenado por score).
- **Score aplicado (parcial, honesto):** Carro (0–35) e Engajamento (0–25) **calculados**; **Momento (0–25) e Intenção (0–15) = `?`** (dependem de transcrição de chamada, próxima fase). Portanto `score_conhecido / 60`.
  - **Carro:** exótico/premium 35 (31 leads: 12 exóticos, 19 premium/M/RS/AMG/Corvette), ano 2025/26 → 25 (100 leads), comum → 10 (199).
  - **Engajamento:** pediu ligação 25 (9) · respondeu SMS 15 (119) · atendeu chamada 10 (171) · sem resposta 0 (31). Extraído do histórico real de conversas.
- **Momento vs. `how_soon`:** o modelo do briefing define Momento pela **recência de compra do carro** (só via transcrição/nota). O campo `how_soon` (urgência do serviço) NÃO é a mesma coisa, então foi mantido como contexto, não como Momento. Sugestão em GAPS #4.
- Também no CSV: data de entrada, source, stage atual, última atividade, appointment (sim/não), **no-show**, se recebeu link Urable, nº de chamadas, link direto do contato no GHL.
- Spam/teste: nomes claramente inválidos (ex.: "Uhfhkkklhhggfff") permaneceram mas são visíveis; nenhum lead foi excluído silenciosamente.

Entregáveis gerados: **`leads_score.csv`**, **`TOP_PRIORITIES.md`** (top 20 + fila de "pediram ligação"), **`GAPS_E_RECOMENDACOES.md`**.
