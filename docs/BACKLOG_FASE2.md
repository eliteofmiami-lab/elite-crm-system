# BACKLOG — Fase 2 (registrado, NÃO construir agora)

## Card pós-Win: pedido de review no Google
*Registrado em 2026-07-08 a pedido do Rafael (junto com a regra de elegibilidade A7.4).*

Quando uma oportunidade vira **Win**:
- Hoje: cards abertos do lead são fechados com resultado "won" e a comissão vinculada é confirmada (implementado).
- **Fase 2:** gerar um card novo de tipo `review_request` (camada 2, alguns dias após a entrega do serviço) para pedir avaliação no Google — com rascunho de SMS pré-aprovável contendo o link direto do perfil do Google da Elite, e detecção de review recebida (fechar o card sozinho quando possível).
- Considerações anotadas: não pedir review antes do carro ser entregue; excluir `teste-interno`; 1 pedido por cliente (não por opp); métrica no dashboard do dono (reviews pedidas × recebidas).

## Outros itens já conhecidos da Fase 2
- Fechamento mensal: conciliação comissões × vendas (Urable invoices).
- ROI por canal usando origem corrigida + CAPI.
- Valor no Purchase do Meta via invoice real do Urable (se o valor do GHL divergir).
