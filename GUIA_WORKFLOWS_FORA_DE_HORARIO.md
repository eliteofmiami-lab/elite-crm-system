# GUIA — 4 workflows fora-de-horário (nativos do GHL, você cria em ~15 min)

O painel NÃO cria nem envia nada — estes workflows são do próprio GHL (zero custo,
zero IA, é o GHL enviando). Horário comercial proposto: **seg–sáb, 9:00–17:00 ET**
(você confirma). Caminho: **Automation → Workflows → + Create Workflow → Start from
Scratch** para cada um.

---

## 1. Chamada perdida FORA do horário → SMS imediato

- **Trigger:** `Call Status` → filtro `Call direction = Incoming` + `Call status = missed/no answer`
- **Condição de horário:** adicione um passo **If/Else** → `Current time` fora de
  seg–sáb 9:00–17:00 (no builder: Branch com "Business Hours" invertido — crie as
  Business Hours em Settings → Business Profile antes, se ainda não existem)
- **Ação (branch FORA do horário):** `Send SMS`:

> Hi! This is Elite Premium Detailing — we're closed right now, but you're first in
> line tomorrow. Reply with your car and what you're looking for, and we'll call you
> at 9 AM sharp.

- Resultado: às 9:00 o card já está na **coluna 1** do painel esperando o Eugene.

## 2. Lead novo (form/Meta) FORA do horário → boas-vindas + expectativa

- **Trigger:** `Facebook Lead Form Submitted` (e/ou `Form Submitted` do site) —
  duplique o workflow para cada fonte se preferir
- **Condição:** mesmo If/Else de horário do item 1
- **Ação (fora do horário):** `Send SMS`:

> Thanks for reaching out to Elite Premium Detailing! We'll call you first thing at
> 9 AM. Meanwhile: what car is it, and are you thinking PPF, ceramic, or a wrap?

- Muitos respondem de noite — o Eugene abre o dia com contexto na coluna 1.

## 3. SMS recebido FORA do horário → auto-reply (1× por conversa)

- **Trigger:** `Customer Replied` → filtro `Reply channel = SMS`
- **Condição:** If/Else de horário + **Workflow settings → "Allow re-entry" OFF**
  (garante 1× por conversa/noite)
- **Ação:** `Send SMS`:

> We're closed at the moment — back at 9 AM and you'll hear from us first thing.

## 4. Chamada perdida DENTRO do horário → validar o existente

- Já existe um workflow de missed-call no ar. **Validar:** Automation → Workflows →
  procure o de missed call → confira o texto atual e padronize com a linguagem acima
  ("saw your call — how can I help?" + nome da loja). Sem criar duplicado: se o
  trigger já cobre 24h, adicione o If/Else de horário para separar o texto diurno
  (curto, "retornamos já") do noturno (item 1).

---

### Checklist final (2 min)
- [ ] Business Hours configuradas em Settings (seg–sáb 9–17 ET)
- [ ] 4 workflows publicados (toggle **Publish** em cada um)
- [ ] Teste com o lead teste-interno: ligação perdida fora do horário → SMS chega →
      às 9:00 o card aparece na coluna 1 do painel
