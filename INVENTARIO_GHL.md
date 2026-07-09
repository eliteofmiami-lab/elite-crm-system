# INVENTÁRIO GHL — workflows da conta Elite (mapa do que roda)

Referência do que está rodando na conta GHL (`locationId Ao5ER8XBg3AtCJMccesF`).
Base: última leitura da API `/workflows/` desta sessão (a API só devolve
nome/status/id — **triggers e ações internas não são expostos pela API**, então os
detalhes abaixo vêm de (a) o que EU criei e sei, (b) inferência pelo nome + recon).
Marcação de confiança: **[criei]** = eu montei, sei o conteúdo · **[pré-existente]**
= já existia, propósito inferido · **⚠ verificar** = confirmar no builder.

> Atualizar a lista COMPLETA (113 workflows) rodando `/workflows/` quando a cota
> diária do GHL resetar — hoje bateu no limite (429). Este doc cobre os principais
> e todos os que eu criei.

---

## 1. Webhooks que alimentam o PAINEL (Board *) — [criei] · published

Cada um dispara um POST para `https://elite-crm-panel.vercel.app/api/ghl-event`
com um `type=` distinto. São a fonte de tempo real do board (Lote 2).

| Workflow | Trigger GHL | Ação | Serve |
|---|---|---|---|
| `Board Stage` | Pipeline Stage Changed (New Pipeline) | POST `?type=stage&key=…` | card muda de coluna em <5s |
| `Board Reply` | Customer Replied (SMS) | POST `?type=reply` | card de SMS aguardando resposta |
| `Board call` | Call Status (qualquer) | POST `?type=call` | card de chamada perdida |
| `Board booked` | Customer Booked Appointment | POST `?type=appt` | cria card de appointment |
| `Board appt status` | Appointment Status changed | POST `?type=appt` | confirmado/cancelado/showed |

O endpoint `?type=newlead` também é usado (boas-vindas fora de horário + card);
disparado pelo `After hours: New lead welcome` (ver §3). **⚠ verificar** exatamente
qual workflow manda o `newlead` no builder.

**Sem duplicação:** cada trigger é único. `Board booked` e `Board appt status`
batem no mesmo `?type=appt` mas em triggers diferentes; o handler é idempotente
(relê o appointment) → sem efeito dobrado.

---

## 2. Disposition — resultado da call move o lead — [criei] · published

Disparam quando o atendente registra a disposição da ligação.

| Workflow | Trigger | Ação |
|---|---|---|
| `Disposition: No Answer (ladder)` | disposição "No Answer" | move p/ próximo Contact stage (escada). **Inclui o degrau Great Cars → Contact 1 (AM)** que o Rafael adicionou 09/jul |
| `Disposition: Follow Up` | disposição "Follow Up" | move p/ stage Follow Up |
| `Disposition: Not Interested` | disposição "Not Interested" | move p/ Lost (não interessado) |
| `Disposition: Incorrect Number` | disposição "Incorrect Number" | move p/ Lost (número inválido) |

---

## 3. After hours — fora do horário comercial — [criei] · published

| Workflow | Trigger | Ação |
|---|---|---|
| `After hours: New lead welcome` | lead novo (form/Meta) fora do horário | SMS de boas-vindas + expectativa; dispara `?type=newlead` p/ o painel |
| `After hours: Missed call SMS` | chamada perdida fora do horário | SMS "retorno logo" |
| `After hours: SMS auto-reply` | SMS inbound fora do horário | auto-resposta |

---

## 4. Cadência de ligação / New Pipeline — [pré-existente]

Disparam quando o lead ENTRA no stage e mandam o SMS/tarefa daquele passo. A escada
de stages é movida pelos `Disposition:` (§2); estes fazem a mensagem de cada degrau.

| Workflow | Papel (inferido) |
|---|---|
| `Contact 1 AM` / `Contact 1 PM` | SMS/tarefa ao entrar em Contact 1 |
| `Contact 2 AM` / `Contact 2 PM` | idem Contact 2 |
| `Contact 3 AM` / `Contact 3 PM` | idem Contact 3 |
| `5: No Answer` · `No Answer New Lead` (draft) | variações antigas de no-answer |
| `2/3/4/5/6/7/8/9.x … STAGE - ADS/CERAMIC/PPF` | escada de ligação do pipeline ANTIGO (ADS) — muitos publicados; **⚠ verificar** se ainda estão ativos ou são legado |

---

## 5. Intake — lead novo → opt-in → 1º SMS — [pré-existente]

| Workflow | Papel |
|---|---|
| `00: New Lead Submitted - ADS` (pub) / `- Window tint` (draft) | entrada do lead |
| `0: Opt-in - Ads` (pub) / `- Window Tint` (draft) | opt-in |
| `1: FIRST SMS - Ads` (pub) / `- Window Tint` (draft) | primeiro SMS |
| `1: Optin - 2nd pipeline` (+ copies, draft) | opt-in de outro pipeline |
| `Create opportunity via incoming Phone call` (pub) | cria opp quando entra ligação |

---

## 6. Appointments — [misto]

| Workflow | Status | Papel |
|---|---|---|
| `Appointments Booked` | pub · [pré-existente] | **os 3 SMS de lembrete** (feito → 2 dias antes pedindo confirmação → dia) |
| `Phone APPT Booked` | pub · [pré-existente] | appointment por telefone |
| `Appointment cancelled` | **draft** · [pré-existente] | cancelamento (não publicado) |
| `6: No Show` | pub · [pré-existente] | no-show |

---

## 7. Meta / CAPI — ⚠ VERIFICAR DUPLICAÇÃO (item crítico do Rafael)

| Workflow | Status | Manda p/ Meta |
|---|---|---|
| `CAPI - META ADS` | pub · [pré-existente] | evento(s) padrão de conversão |
| `CAPI - Purchase / Sold` | pub · [pré-existente] | evento de compra/venda |
| `2.1: GREAT CARS - ADS` | pub · [pré-existente, mexido 09/jul] | evento de Great Cars |
| `Opened Emails - FB Audience` | pub · [pré-existente] | audiência FB |

**⚠ Pendente de verificação no builder (NÃO alterar sem OK do Rafael):** confirmar
se `2.1: GREAT CARS - ADS` e `CAPI - META ADS` disparam o **mesmo evento no mesmo
gatilho** (duplicando dado de campanha). Só reportar.

---

## 8. Remarketing / Nurture / Lost — [misto]

| Workflow | Status | Papel |
|---|---|---|
| `Remarketing - Leads Perdidos Meta` | pub · [mexido: refinei exclusão de tags] | drip de leads perdidos |
| `Remarketing: Great Cars not reached` | **draft** · [criei] | Great Cars não alcançado → audiência FB (não publicado) |
| `Lost Deal - Unable to reach / Never answered` | pub · [pré-existente] | fim da linha |
| `8: Long Term Nurture` · `A)/B)/C)/D) … Nurture` | pub/draft · [pré-existente] | nutrição de longo prazo |

---

## 9. Discador / IA — [pré-existente]

| Workflow | Papel |
|---|---|
| `Nedzo AI | Add To List` · `Nedzo AI | End Of Call Report` | integração com discador/IA "Nedzo AI" — **relevante quando formos montar o Power Dialer** |

---

## Pendências de verificação no builder (quando a API/Chrome liberar)
1. **Trigger de Task existe no GHL?** Se sim, criar `Board Task` → `?type=task`
   (fecha/atualiza card de task em tempo real). Se não, tasks seguem pelo cache. **Não criar nada até confirmar.**
2. **2.1 GREAT CARS vs CAPI - META ADS** — duplicação de evento Meta (§7). Só reportar.
3. Confirmar quais workflows do pipeline ADS antigo (`2–9.x STAGE`) ainda estão
   ativos vs legado.
4. Refrescar a lista COMPLETA (113) via API `/workflows/` quando a cota resetar.
