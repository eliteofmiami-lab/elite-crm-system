# FILA_PRONTA — MVP · 2026-07-08 10:48 ET

## Aceite (gabarito do Rafael — binário)

| Caso | Esperado | Como está | OK |
|---|---|---|---|
| Agie Pee | topo da Camada 1, callback_devido | posição 1 · estado callback_devido | ✅ |
| Naomi | AUSENTE (pos_venda) | cards abertos: 0 · estado pos_venda | ✅ |
| ROBERT R | fora da discagem; nurture C3 com estado | abertos: 0 · nurture: [(3, '2026-07-28')] · estado aguardando_decisao_cliente | ✅ |
| Shawn | só na data do follow-up | abertos: 0 · retomadas: [] · estado agendado | ✅ |
| Adam Nguyen | aguardando_evento_externo (~setembro) | abertos: 0 · retomadas: [] · estado aguardando_evento_externo | ✅ |

## Zero escritas no GHL
- `out/write_log.jsonl` INTOCADO: 1763 linhas · md5 `140adf2ce93062f1afee84ab46a9de24` (idêntico ao baseline capturado no início do MVP). Todo caminho de escrita bloqueado no código (`writer.MVP_READONLY`) e removido da UI (RailView é somente-leitura).

## Custo real da rodada
- **$2.13** / teto $40 (estimado $15.29) — tudo em `cost_log`.

## Estado da base
- 82 leads com estado sintetizado: esfriou: 45 · ativo_venda: 28 · callback_devido: 4 · agendado: 1 · aguardando_evento_externo: 1 · pos_venda: 1 · aguardando_decisao_cliente: 1 · spam_nao_lead: 1
- Fila: **117 cards abertos** (80 call-verified) · congelados fora da fila: pós-venda invisível, aguardando/agendado dormindo até a janela.

## Como abrir dentro do GHL
- [INSTRUCOES_MENU_LINK.md](INSTRUCOES_MENU_LINK.md) — Custom Menu Link (3 min). URL: `https://elite-crm-panel.vercel.app/?layout=rail`

## Verificador pós-call — Pendências (item 6)
- **88 pendências abertas** (somem sozinhas quando a LEITURA confirma qualquer resolução válida; o sistema só aponta, nunca executa).

### Amostra de 10 (validação do formato)

- **[sem_fechamento]** Call answered 03/07 14:54 (50s) with no closure logged after. **→ Send today's follow-up OR, if the customer has no interest, mark Lost with the reason.**
- **[interesse_faltando]** Call 03/07 14:54 — interest stated: "I need to check it out, but I'm not in the mechanical right now.". **→ Interest is not on the contact → fill the interest field with 'Ceramic coating'.**
- **[interesse_faltando]** Call 06/07 15:01 — interest stated: "I was just I was looking at everything, but you guys were like, I might wanna, you know, reach out to you guys. They're ". **→ Interest is not on the contact → fill the interest field with 'Ceramic coating'.**
- **[sem_fechamento]** Call answered 04/07 11:57 (46s) with no closure logged after. **→ Send today's follow-up OR, if the customer has no interest, mark Lost with the reason.**
- **[interesse_faltando]** Call 04/07 11:57 — interest stated: "Ceramic coating". **→ Interest is not on the contact → fill the interest field with 'Ceramic coating'.**
- **[sem_fechamento]** Call answered 30/06 15:25 (39s) with no closure logged after. **→ Send today's follow-up OR, if the customer has no interest, mark Lost with the reason.**
- **[interesse_faltando]** Call 30/06 15:25 — interest stated: "Ceramic coating". **→ Interest is not on the contact → fill the interest field with 'Ceramic coating'.**
- **[interesse_faltando]** Call 29/06 09:02 — interest stated: "Ceramic coating". **→ Interest is not on the contact → fill the interest field with 'Ceramic coating'.**
- **[interesse_faltando]** Call 06/07 16:26 — interest stated: "Client asked about pricing ($699) and immediately proceeded to schedule the appointment without hesitation.". **→ Interest is not on the contact → fill the interest field with 'Ceramic coating'.**
- **[interesse_faltando]** Call 07/07 16:00 — interest stated: "so what the deal is still on with your deal... I get the full on?". **→ Interest is not on the contact → fill the interest field with 'Paint Protection Film'.**

## Top 30 da fila (posição · estado · por quê · score com breakdown)

**1. 📞 CALLBACK OWED — customer called US and nobody answered**  
C1 · `callback_devido` · score 85/100 ✓ · +13053182042  
_Carro 25 (ano 2026 · cf) · Momento 25 (I just have a new car. · call) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 10 (I haven't even done my research, but I just have a new car. · call)_  
Since the Jun 17 call about her brand-new Tesla Model Y, Agie stayed indecisive despite a tentative store visit for Tuesday. Multiple follow-up calls/texts through late June went unanswered. On Jul 7 she called us back b  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/YpB8EZBqUWBVjIL6n1jh)

**2. 📞 CALLBACK OWED — customer called US and nobody answered**  
C1 · `callback_devido` · score 35/60 (partial) · +14709218482  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção ? (sem how_soon)_  
On Jul 4, an inbound call lasted only 40s with an automated gatekeeper message asking for name and reason. No real info was captured, and we haven't called back yet.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/6VjgrdQUuV85sHPTRdCv)

**3. 📞 CALLBACK OWED — customer called US and nobody answered**  
C1 · `callback_devido` · score 35/60 (partial) · +19544806789  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção ? (sem how_soon)_  
Jul 7: Jamie called in but got caught by an automated screening system - never reached a person, no voicemail left. We owe her a callback ASAP, top of the queue.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/97e16ll5jKwNWKBbFqA4)

**4. 📞 CALLBACK OWED — customer called US and nobody answered**  
C1 · `callback_devido` · score 35/60 (partial) · +18624592850  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção ? (sem how_soon)_  
Missed inbound call on Jul 4 (4s), no callback made since. Client tried to reach us — callback overdue, top of queue.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/WPRRPUdKLNePVJl48JBJ)

**5. FIRST CONTACT — KERRI (HOT LEADS)**  
C2 · `ativo_venda` · score 90/100 ✓  
_Carro 25 (ano 2026 · call) · Momento 25 (Resumo da call menciona 'her new 2026 Lexus IS350', indicand · call) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Carrie ligou solicitando quote para ceramic window tint, com · call)_  
One inbound call on Jun 26: Carrie asked for a ceramic tint quote on her new 2026 Lexus IS350, comparing Ceramic Pro Nuview Mid IR to XPEL XR Plus. Quote still pending — no follow-up sent since then.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/WfB45n9D8XlkAsU4VP7r)

**6. FIRST CONTACT — WILLIAM (HOT LEADS)**  
C2 · `ativo_venda` · score 75/75 ✓  
_Carro 35 (premium · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (He requested to text photos and references to get a personal · call)_  
1 call on Jun 10; William asked about vinyl wrap/color change for his AMG and agreed to text photos for a personalized quote. Waiting on those photos to close the deal.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/fyfdIEPeWBPyGkeyzZWn)

**7. FIRST CONTACT — lead (HOT LEADS)**  
C2 · `esfriou` · score 70/75 ✓  
_Carro 35 (exótico · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 10 (He asked for same-day service, couldn't get it, and declined · call)_  
Apr 22: inbound call, he wanted same-day windshield PPF on his McLaren 750S before flying out; no availability until May 4 so he declined and hung up politely. No contact since — gone cold, worth a light nudge.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/vn7baxkUGnpypw8Hywj1)

**8. FIRST CONTACT — MAURICE (HOT LEADS)**  
C2 · `ativo_venda` · score 65/75 ✓  
_Carro 25 (ano 2025 · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Lead requested full window tint pricing and received a $1,00 · call)_  
Jul 1: inbound call, lead asked for a full window tint quote on his 2025 BMW X2. We quoted $1,000 total including a ceramic IR film discount. No decision yet — quote still pending.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/PYVdVmFdjh8ujMTDJvZJ)

**9. FIRST CONTACT — lead (HOT LEADS)**  
C2 · `ativo_venda` · score 65/75 ✓  
_Carro 25 (ano 2025 · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Caller asked for ceramic coating pricing, was quoted $709-79 · call)_  
Jun 11: inbound call, quoted ceramic coating ($709-799) for his 2025 Mercedes CLA 250; he reacted well and call ended as 'moving forward.' No contact since — nearly a month has passed, call him now to close.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/m6B6uUWP39Pg1UI02Lwf)

**10. FIRST CONTACT — lead (HOT LEADS)**  
C2 · `ativo_venda` · score 65/75 ✓  
_Carro 25 (ano 2026 · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Cliente pediu quote de window tint e recebeu detalhes de pre · call)_  
1 call on Jun 8: customer asked for a tint quote for his 2026 Audi S5, got pricing, and a Wednesday shop visit was offered. No confirmation since — needs a nudge to lock in the appointment.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/CS31nX444nngRQP92MxR)

**11. FIRST CONTACT — lead (HOT LEADS)**  
C2 · `ativo_venda` · score 65/75 ✓  
_Carro 25 (ano 2025 · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Client asked about window tint for his 2025 Audi A5; operato · call)_  
May 16: short inbound call (43s), no analysis captured. May 18: client asked about XPEL then requested a quote for window tint on his 2025 Audi A5 — quoted $1,100 with Ceramic Pro + lifetime warranty, felt it was pricier  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/ayCKRku1c5kaDuKHj74n)

**12. FIRST CONTACT — MARIO (HOT LEADS)**  
C2 · `esfriou` · score 63/75 ✓  
_Carro 35 (premium (M/RS) · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 3 (desqualificado na call (resolução) · call)_  
Only one call on May 2: he asked for a re-tint quote on his 2022 BMW M3 Competition, we quoted $1,000 total, but the lead was disqualified afterward. No further activity since.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/zdkD4GGTJiglIDFKOUEI)

**13. FIRST CONTACT — LISTEN (HOT LEADS)**  
C2 · `ativo_venda` · score 55/75 ✓  
_Carro 25 (ano 2025 · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 5 (Caller said she's unsure/still researching wrap options for  · call)_  
Jun 19: Savannah called about a full black wrap for her 2025 Nissan Sentra; quoted $3,500 and invited to visit the shop Tue 12-5PM. No follow-up since — reach out now to see if she came by or still wants it.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/kkw4hVdaDtEvND643Bgo)

**14. FIRST CONTACT — DALTON (HOT LEADS)**  
C2 · `ativo_venda` · score 55/100 ✓  
_Carro 10 (comum · call) · Momento 5 (Vehicle is a 2006 Honda Civic, not new or recently acquired  · call) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Caller explicitly requested pricing for tinting the rear win · call)_  
One inbound call on Apr 22: quoted tint for a 2006 Civic ($100/side window, $350 rear windshield). Resolution left pending, no follow-up since — almost 3 months of silence. Needs a reconnect call now.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/GWZ5HxPVn6ShNDE6otnW)

**15. FIRST CONTACT — ANTHON (HOT LEADS)**  
C2 · `esfriou` · score 53/75 ✓  
_Carro 25 (ano 2026 · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 3 (desqualificado na call (resolução) · call)_  
Inbound call on Jul 1: caller asked about installing a side decal on his 2026 Dodge Scat Pack. Operator said we don't offer that service. Call ended there, no further engagement.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/UpQybqQ3dwiJyhsgfehT)

**16. FIRST CONTACT — GEORGE (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (George Lashley called requesting a price quote for window ti · call)_  
Jul 5: George called in asking for a window tint quote on a second car; he's a past customer of another shop (the guy from Trinidad). The right contact wasn't available, so we owe him a quote. No follow-up sent yet.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/bXEbXuWB2IOBwYdYh8ES)

**17. FIRST CONTACT — JUDY (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Cliente ativamente buscando corrigir a compra do vinil (tama · call)_  
Jul 4: inbound call - customer bought wrong-size vinyl wrap and asked about satin black options to match his sample. He agreed to bring a piece of material to compare. No follow-up yet; needs a nudge to confirm and sched  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/JDGmc1c1zoMMEgqkVyat)

**18. FIRST CONTACT — NADEEM (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Caller asked about ceramic window tint pricing and received  · call)_  
Jul 4: inbound call, customer asked about ceramic window tint for his Tesla Model 3 Performance; quoted $900 bundle. Call ended with no commitment, no follow-up sent yet — reach out to close.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/bEEHEd80oVoUv3KxJWKw)

**19. FIRST CONTACT — JOSHUA (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Cliente recebeu cotação detalhada de $700 para window tint e · call)_  
1 call on Jun 30: customer asked about window tinting for his 2015 Honda CR-V, got a $700 quote, and ended the call moving forward. Follow up to close.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/U3eGOu9HJI9mKFXBiPj9)

**20. FIRST CONTACT — CARMEN (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Caller explicitly requested a quote for ceramic window tint  · call)_  
Single inbound call on Jun 25: caller requested a ceramic window tint quote for a Tesla Model 3; operator gave detailed pricing and call ended on a positive note. No confirmation or follow-up yet - reach out to move the   
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/sFPQqhIaWiG4KDeQAAb2)

**21. FIRST CONTACT — JORGE (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Lead called about a 2022 black Tesla Model Y, asking for a p · call)_  
Jorge called Jun 19 asking for a paint correction & wax quote on his black 2022 Tesla Model Y. Operator quoted starting at $500, pending inspection. No follow-up sent since; quote still open 3 weeks later.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/vczlaOEvHxtc8ZJrKVJn)

**22. FIRST CONTACT — LAURA (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Operator quoted the Silver package: $799 ceramic coating + $ · call)_  
1 inbound call on Jun 8: Laura asked about paint correction + 5-yr ceramic coating for her 2019 Fiat Spider after a repaint. Quoted the Silver package ($799 ceramic + $500 correction), resolution left pending. No follow-  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/9240XQ22izJVmu6Paamv)

**23. FIRST CONTACT — JANET (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Lead called asking for a window tint quote for his 2023 Toyo · call)_  
Missed call then answered right after on Jun 2; he asked for a window tint quote on his 2023 Camry and got full pricing ($100/side, $350 windshield, $250 back, $1000 whole car). Left pending, no response since — follow u  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/Htyr41R5CKVTcWGYRkkx)

**24. FIRST CONTACT — JEAN (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Caller asked for window tinting pricing for a GMC Denali tru · call)_  
Jun 2: inbound call, asked for tint pricing on a GMC Denali; quoted $380 windshield / $125 per side. Call ended without booking. No follow-up since — over a month has passed, need to reach out.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/CPCNyggx8KDaVDtkZBeK)

**25. FIRST CONTACT — lead (HOT LEADS)**  
C2 · `esfriou` · score 50/75 ✓  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Caller identified himself as Grant and stated he was trying  · call)_  
Grant called on May 23 asking for a quote but reached only an automated screening system, never a live person. No callback has been made since — this is an overdue, urgent callback.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/bETo9XZz0mCbLjwk0egP)

**26. FIRST CONTACT — HORTONH (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Joel actively wanted to drop off the car that same day betwe · call)_  
May 22: Joel called wanting to drop off his car same day for a windshield sunstrip tint (4:30-5pm window); operator said he'd check with the technician and call back. No callback was ever made, and the lead has sat untou  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/G1U30qDpCaQrAw4COXne)

**27. FIRST CONTACT — JASON (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Caller asked for a ceramic tint quote for his Lexus IS250 in · call)_  
One inbound call on May 8: client asked for a ceramic tint quote on his Lexus IS250 (incl. windshield), got full pricing ($1000 total) and thanked the operator. No follow-up since — need to close the loop.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/sVQsiLfsOLKbZCm0FOvL)

**28. FIRST CONTACT — KATHERIN (HOT LEADS)**  
C2 · `ativo_venda` · score 50/75 ✓  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Cliente quer seguir com o serviço de ceramic coating e disse · call)_  
May 2: inbound call, customer asked about ceramic coating for a boat; Eugene said pricing needs photos first. Customer agreed to send pictures and wants the job done. No follow-up logged since — over two months of silenc  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/MDZ59ceQfMypehZS5OBs)

**29. FIRST CONTACT — IRSHAA (HOT LEADS)**  
C2 · `esfriou` · score 50/75 ✓  
_Carro 10 (comum · nome_opp) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 15 (Agent quoted $350 for ceramic front windshield tint (Ultimat · call)_  
Apr 22: inbound call, customer wanted windshield tint same day; no slots until May 4, so agent quoted $350 for ceramic front tint. No booking or further contact since — gone quiet for over 2 months.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/8jf9r0Pgc4qTAGmbHYFG)

**30. FIRST CONTACT — SHAUNA (HOT LEADS)**  
C2 · `esfriou` · score 45/75 ✓  
_Carro 10 (comum · call) · Momento ? (sem transcrição/nota) · Engaj. 25 (ligou (inbound) · mensagens) · Intenção 10 (Caller asked for PPF pricing on her 2021 GLC Coupe, got quot · call)_  
One inbound call on Apr 17 — quoted $2,450 for front PPF or $5,908.50 for full car (with free ceramic on front); she balked at the full price and pulled back. No contact since, now over 80 days cold.  
[Abrir contato](https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/zIXqy9XrcshamRDgIN7k)

---
**Congelado até segunda ordem** (código preservado, execução off): advice, rascunhos/aprovações, wrap-up, bonus guard, comissões, relatório 18:30, Appointments Board, briefing, cupom, retro (batch pago aguardando no servidor), nudges/clock-in, extensão Chrome.

*Após este arquivo: parado, aguardando o Rafael.*