# GAPS & RECOMENDAÇÕES — o que ajustar no GHL/Urable antes das próximas fases

> Baseado na recon somente-leitura dos últimos 40 dias (330 oportunidades). Nada foi alterado.

## 1. Dados do veículo inconsistentes
- **75 de 330 leads (23%)** não têm os custom fields `Vehicle Make/Model/Year` preenchidos — o veículo só existe no **nome da oportunidade** (texto livre, ex.: "Escalade black", "Tesla model 3 frost blue").
- Consequência: o score do carro depende de parsing do nome. Funciona, mas é frágil.
- **Recomendação:** garantir no formulário do Meta/Google que Make/Model/Year sejam sempre capturados nos custom fields. Idealmente separar Ano em campo numérico (hoje é TEXT). Cruzar com o **Item do Urable** (que tem make/model/year/VIN estruturados) como fonte secundária de verdade.

## 2. Campo `source` poluído (atribuição não confiável)
- O `source` da oportunidade vem preenchido com **o nome do veículo** em dezenas de casos (ex.: source="Porsche 911", "Tesla model y"). Atribuição real utilizável só aparece em: `Google` (53), `Call Google Ads` (34), `Facebook` (2); **41 sem source**.
- **Recomendação:** parar de gravar texto livre no `source`. Usar `attributionSource` do contato + os campos `utm_source/medium/campaign` (que existem mas precisam ser conferidos se estão sendo preenchidos). Isso é pré-requisito pro fechamento de ROI por canal na Fase 2.

## 3. Leads duplicados entre os dois pipelines
- **17 telefones** aparecem em **ambos** os pipelines (ELITE ADS **e** New Pipeline) = 35 oportunidades para 17 pessoas. Ex.: "J MARTINEZ" e "JAIME VASQUEZ" existem nas duas esteiras.
- Consequência: dupla contagem, confusão de qual esteira seguir, risco do Eugene trabalhar o lead errado.
- **Recomendação:** decidir **um** pipeline oficial (o **New Pipeline** é o ativo — é onde os leads do Zapier/Urable entram) e arquivar/migrar o ELITE ADS, ou criar automação que impeça o mesmo contato de abrir opp nos dois. Deduplicar por telefone.

## 4. "How soon" existe mas não é usado no score
- **214/330** têm o campo *"How soon are you looking to get this done?"* preenchido — sinal forte de intenção/urgência que hoje não alimenta nenhuma priorização.
- **Recomendação:** incorporar `how_soon` ao score (é um proxy de Intenção que não exige transcrição). Ver seção "Momento vs. how_soon" no RECON_REPORT.

## 5. Momento e Intenção do score dependem de transcrição — pipeline a construir
- Hoje esses dois componentes ficam `?` para quase todos. As gravações **estão acessíveis via API** (confirmado), mas o GHL **não transcreve** (endpoint 404).
- **Recomendação:** construir o pipeline de transcrição (whisper local) + análise (Claude) na próxima fase, priorizando os leads de maior score parcial. Precisa: `ANTHROPIC_API_KEY` no `.env` e decisão sobre whisper local vs. serviço pago.

## 6. Sem custom fields de oportunidade
- A conta tem **12 custom fields de contato e 0 de oportunidade**. Dados de veículo/serviço ficam no contato — ok, mas para o painel do Eugene convém ter no nível da oportunidade: `score`, `momento`, `intencao`, `quote_enviada` (bool), `no_show` (bool).
- **Recomendação:** criar esses custom fields de oportunidade (**escrita — só após autorização**) para o sistema gravar o score de volta e o painel ler.

## 7. Quote não é criável via API do Urable
- A API do Urable expõe só Customers e Items. Não dá para criar quote/job/invoice programaticamente.
- **Recomendação:** o sistema vai **preparar** cliente + veículo + serviços sugeridos e o **Eugene finaliza a quote manualmente**. Detectar "quote enviada" pelo padrão de link `go.urable.com/xxxxx` nas SMS.

## 8. Higiene de calendários
- Há **20 calendários**, a maioria "Personal Calendar" de pessoas (vários nomes que talvez não estejam mais na operação). Appointments reais caem em `Booking Request`, `ELITE BOCA RATON`, `Ceramic Pro Silver Package`.
- **Recomendação:** confirmar quais calendários estão em uso e desativar os obsoletos, para o monitoramento de no-show não olhar lugar errado.
