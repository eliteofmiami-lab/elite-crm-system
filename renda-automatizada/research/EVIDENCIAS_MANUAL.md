# Coleta manual de evidências de receita (filtro zero)

Só para as fontes que o script `evidencias_coleta.py` marcou como `[MAN]`. Objetivo: encontrar operações REAIS (à venda ou já vendidas) nas categorias candidatas, com receita mensal informada pelo marketplace.

## Empire Flippers (maior confiança: P&L verificado)
1. Abra https://empireflippers.com/marketplace/ no Safari.
2. Filtro **Monetization**: marque *Display Advertising*, *Amazon KDP*, *Amazon Merch*, *Etsy* (um de cada vez se preferir). Filtro **Niche**: veja se há *YouTube*.
3. Marque também **Sold** (listagens vendidas) — são a melhor prova.
4. Para cada listagem relevante, abra e copie para a tabela abaixo: número da listagem, monetização, nicho, **Monthly Net Profit**, **Monthly Revenue**, **Hours per week** (esforço do dono), **Team** (se houver), **Created** (idade), preço pedido/vendido, e a URL.
5. Alternativa rápida: na página da listagem, ⌘A, ⌘C e cole num arquivo `data/evidencias/manual/ef_<numero>.txt`.

## Flippa
1. Abra as URLs de `config/evidencias_fontes.json` (YouTube aberto / vendido, KDP, Etsy).
2. Para cada listagem: título, tipo, **Profit/mo**, **Revenue/mo**, "Verified" (Flippa marca revenue verificada pela integração) ou não, idade, horas/semana, URL.

## Acquire.com / Motion Invest
Mesmo procedimento; marque `verificado` só quando o marketplace disser que verificou.

## Tabela (cole aqui ou num arquivo em data/evidencias/manual/)
| Marketplace | ID/URL | Categoria (nossa) | Monetização | Receita/mês US$ | Lucro/mês US$ | Horas/semana do dono | Equipe | Idade | Status (à venda/vendida) | Classificação (verificado/autodeclarado) | Data da coleta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | |

Regra: só entra no relatório o que tiver URL e data. "Estimativa" de calculadora não é prova.
