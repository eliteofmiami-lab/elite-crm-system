# SCORE_DEBUG — K WASHINGTON (A12-a) · 2026-07-08

## O número que o painel mostrava: **35** (seco, sem contexto)

## Componente a componente — de onde veio o 35

| Componente | Valor exibido | O que o cálculo usou | O que EXISTIA e foi ignorado |
|---|---|---|---|
| Carro (0–35) | **10** "comum" | só o nome da opp (`"K WASHINGTON"` — sem carro no nome) | análise da call de 2/jul: **Tesla Model Y 2026** → 25 pontos (ano 2026) |
| Momento (0–25) | **0 invisível** | nada (e o `?` não aparecia na tela) | segue sem evidência gravada (ver "o que falta" abaixo) |
| Engajamento (0–25) | **25** "ligou (inbound)" | mensagens da 1ª conversa | ✓ correto (único componente certo) |
| Intenção (0–15) | **0 invisível** | proxy `how_soon` (vazio p/ ela) | análise: **pediu_quote** ("asked how much it costs to wrap a Tesla Model Y") = 15 · quote enviada em 3/jul = 15 |

**35 = 10 + 25 + dois componentes sem dado exibidos como zero silencioso.**

## As 5 causas raiz (todas de integração, nenhuma da régua)

1. **Amnésia de análise** — `refresh_score` só usava a análise DO CICLO; a análise salva no
   Supabase nunca era consultada. Score recalculado em evento de SMS = Momento/Intenção
   sempre `?`, para sempre.
2. **Veículo ignorado** — o cálculo recebia só `opp_name`; CFs de veículo do contato,
   veículo extraído da call e Log call details nunca entravam.
3. **Quote enviada não era sinal** — lead em Quote Sent com link Urable detectado não
   pontuava intenção.
4. **Visita à loja não existia no modelo** (o sinal mais forte do funil).
5. **Exibição desonesta** — o painel mostrava número seco; `?` virava zero invisível
   (35 parecia score completo; era 35/60 parcial).

Origem histórica: o script da "extensão G0-B" (incidente já auditado) usava exatamente esse
caminho pobre — está **aposentado por construção** (`backfill_scores_active.py` agora aborta
com instrução de usar o motor v3).

## A correção (motor v3 — `worker/brain/score_engine.py`, vale para TODOS os leads)

Precedência por componente, com fonte registrada em `lead_scores.components`:

- **Carro**: manual (Log call VENCE) → CFs do contato → análise de call → nome da opp
- **Momento**: manual → transcrição → `?`
- **Engajamento**: mensagens de TODAS as conversas (bug antigo: só a 1ª)
- **Intenção**: **visita à loja (prova)** → transcrição → **quote enviada** → proxy how_soon

Exibição honesta (A12-b): sempre `conhecido/máximo-apurável` + selo **✓ call-verified**
(Momento/Intenção com evidência real) ou **partial** + breakdown com `?` visível
("? = no data yet — never counted as zero").

Visita à loja (A12-c, convenção Rafael 2026-07-07): appointment `showed` OU tag
`visitou-loja` OU confirmação no painel = **prova** (Intenção 15 + flag no card/briefing);
menção em transcrição = `visita_provavel` — chip âmbar no card com confirmação de 1 clique,
só pontua depois de confirmada. **Caso inaugural: Shawn** (+1 954 557 2564) tagueado
`visitou-loja` por ordem do Rafael (write_log) → score v3 60/75 ✓ call-verified.

## K WASHINGTON depois da correção

| Componente | Antes | Depois | Fonte |
|---|---|---|---|
| Carro | 10 | **25** (Tesla Model Y 2026) | análise da call 2/jul |
| Momento | 0 invisível | **?** (visível, honesto) | sem evidência ainda |
| Engajamento | 25 | **25** (ligou inbound) | mensagens |
| Intenção | 0 invisível | **15** (pediu quote na call) | análise da call |
| **Total** | **35** | **65/75 · ✓ call-verified** | nos 2 cards dela |

## Sobre o ~100 do Rafael — o que ainda falta e como fecha

- **Momento "carro chegando em dias"**: a análise da call de 2/jul não achou essa fala
  (evidência vazia). A re-análise de hoje à noite (análise total, prompt novo) reprocessa a
  call dela; se a fala existir, vira **+25 → 90/100**. Se não estiver NA CALL, o caminho é o
  Log call details (entrada manual vence) — honestidade: o sistema não pontua o que não tem
  evidência.
- **Visita à loja dela**: não há appointment `showed` nem tag — o appointment de 2/jul está
  `invalid` no GHL. Se ela de fato visitou, é 1 clique (chip no card) ou tag `visitou-loja`.
  Intenção já está no teto (15), então o número não muda — mas a flag 🏪 passa a aparecer no
  card e no briefing pré-venda.
- **Carro = 25 e não 35**: a régua dá 35 só para exótico/premium; Tesla Model Y 2026 pontua
  pelo ano (25). Se o Rafael quiser Tesla/EV premium valendo 35, é 1 linha na régua — dizer.

## Estado aplicado agora (Supabase; GHL continua gated)

- **101 leads com card aberto** rescorados no motor v3 · selos: 12 ✓ call-verified, 89 partial
  (os partial viram call-verified conforme a análise total processa as calls esta noite).
- Cards agora carregam `score/score_max · selo · breakdown` — painel exibe.
- Write-back dos CFs `elite_score`/`breakdown` no GHL: **aguardando G-SCORE-FIX/G2**
  (disciplina de gate — nenhuma exceção).

## Advice (A12-d) — executado no mesmo passe

- Portão de qualidade ATIVO no worker: evidência literal obrigatória + só alavanca de
  conversão + não-redundância + lista banida + **crítico Haiku fail-closed** antes de exibir;
  `advice=""` (silêncio) é output válido e preferível a filler. Reprovados → `advice_rejected`.
- **Expurgo dos advices no ar**: todos os advices pré-portão saíram de exibição (auditados em
  `advice_rejected`). O caso-teste morreu: *"grab his phone number before transferring"*
  (K WASHINGTON) — banido por recomendar dado que o caller ID já captura.
- Os advices são regenerados esta noite pela análise total, já passando pelo portão.
