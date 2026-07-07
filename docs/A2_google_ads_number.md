# A2 — Número de tracking do Google Ads (inferência, aguardando confirmação do Rafael)

> Somente leitura. Nada foi alterado. Precisa da sua confirmação antes de virar config do cérebro.

## Como inferi
Peguei os **34 leads** com source `Call Google Ads` da recon e olhei, nas ligações **inbound** deles, qual número **foi discado** (campo `to` da call = a linha de tracking).

## Resultado
- Entre os leads Google Ads, **`+1 754 465 0696`** recebeu **37 de 56** ligações inbound (**66%**). É o forte candidato a **número de tracking do Google Ads**.
- No geral (todas as inbound calls dos 40 dias), as três linhas mais discadas são:

| Número | Inbound (Google-Ads leads) | Inbound (geral) | Palpite |
|---|---|---|---|
| **+1 754 465 0696** | 37 | 77 | **Google Ads** |
| +1 954 335 3693 | 14 | 65 | Facebook / outra campanha? |
| +1 786 876 7891 | 4 | 59 | Linha principal / orgânico? |

## O que preciso de você
Confirme (ou corrija):
1. **`+1 754 465 0696` é o número do Google Ads?** (sim/não)
2. Os outros dois (`+1 954 335 3693`, `+1 786 876 7891`) são o quê? (Facebook, linha principal, orgânico…)

## O que o cérebro fará depois (com sua confirmação)
- Ligação inbound com `to = número Google Ads` → tag `inbound-google-ads` + corrigir o `source` da oportunidade.
- Registrar a origem (Google Ads vs. outros) no card e nos relatórios diários, para medir de onde vêm as ligações boas.
