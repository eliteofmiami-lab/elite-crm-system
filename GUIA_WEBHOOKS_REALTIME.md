# GUIA — Tempo real do Daily Board (webhooks do GHL + 2 variáveis na Vercel)

Três camadas: **push** (webhook do GHL → painel, ≤5s) · **Realtime** (a tela atualiza
sozinha, zero F5 — já no ar) · **delta 60s + varredura 5 min** (reconciliação — já no
ar). Falta só a SUA parte (~10 min, uma vez): 2 variáveis na Vercel + 5 workflows.

---

## PASSO 0 — 2 variáveis na Vercel (2 min, destrava o push e o delta)

1. https://vercel.com → projeto **elite-crm-panel** → **Settings → Environment Variables**
2. Adicione (Production):
   - **`SUPABASE_SERVICE_ROLE_KEY`** = a *service_role key* do Supabase
     (https://supabase.com/dashboard → projeto elite-crm → Settings → API →
     `service_role` → Copy). É a mesma que está no seu `.env` local.
   - **`WEBHOOK_KEY`** = `WldabAmdqGdnRn-ZMu2RHA64kpK1wijk`
     (chave que eu gerei — é a senha do endpoint; só vive aqui e nas URLs abaixo)
3. **Deployments → ⋯ no último deploy → Redeploy** (a variável só vale após redeploy).

## PASSO 1 — 5 workflows de webhook no GHL (Automation → Workflows → + Create)

Todos usam a ação **Webhook** (Custom Webhook / premium action, centavos por disparo),
método **POST**, e o **Custom Data** padrão já inclui o contato. Crie um por linha:

| # | Nome sugerido | Trigger | URL do webhook (cole exatamente) |
|---|---|---|---|
| 1 | Board — stage | **Pipeline Stage Changed** (pipeline: New Pipeline) | `https://elite-crm-panel.vercel.app/api/ghl-event?type=stage&key=WldabAmdqGdnRn-ZMu2RHA64kpK1wijk` |
| 2 | Board — reply | **Customer Replied** (channel: SMS) | `https://elite-crm-panel.vercel.app/api/ghl-event?type=reply&key=WldabAmdqGdnRn-ZMu2RHA64kpK1wijk` |
| 3 | Board — call | **Call Status** (qualquer status) | `https://elite-crm-panel.vercel.app/api/ghl-event?type=call&key=WldabAmdqGdnRn-ZMu2RHA64kpK1wijk` |
| 4 | Board — booked | **Customer Booked Appointment** | `https://elite-crm-panel.vercel.app/api/ghl-event?type=appt&key=WldabAmdqGdnRn-ZMu2RHA64kpK1wijk` |
| 5 | Board — appt status | **Appointment Status** (todas as mudanças) | `https://elite-crm-panel.vercel.app/api/ghl-event?type=appt&key=WldabAmdqGdnRn-ZMu2RHA64kpK1wijk` |

Em cada um: **Publish** (toggle no topo). Dica: no passo do Webhook, se houver campo
"Custom Data", adicione `contact_id` = `{{contact.id}}` (o painel também entende o
payload padrão, mas isso garante).

## PASSO 2 — teste de 30 segundos

1. Abra o painel (aba Owner) — topo deve mostrar **● Live · last event HH:MM:SS**.
2. Mova um lead de stage no GHL → o card antigo some da coluna **em ≤5 segundos, sem F5**.
3. Se nada acontecer: aba Owner mostra banner de erro do push (e o delta/varredura
   continuam cobrindo em 60s/5min — nada se perde, só perde velocidade).

## O que cada camada cobre

- **Push (≤5s):** stage movido · SMS do cliente · call perdida · appointment criado/confirmado.
- **Delta (≤90s):** SMS enviado por vocês (fecha reply/urable/warm-up e valida tentativa
  25s+SMS) · tasks.
- **Varredura 5 min (CI):** reconciliação completa (se webhook cair, nada se perde).
