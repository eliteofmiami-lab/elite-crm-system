# Custos de produção por unidade — cotações (coletado 2026-09-17, por busca)

**Aviso:** valores de fontes **secundárias** (blogs de comparação de preços). As páginas oficiais de preço estão na lista de `research/fetch_policies.py` (IDs C-xx) para o seu Mac baixar amanhã; até lá, tudo aqui é **a confirmar**. Licenças comerciais vão para `config/licenses.md` na Fase 2.

## Voz (TTS)
| Provedor | Preço citado | Observação | Fonte |
|---|---|---|---|
| OpenAI gpt-4o-mini-tts | ~US$ 0,015/min (0,60/M tokens de texto + 12/M tokens de áudio) | sem assinatura, paga por uso | https://texttolab.com/blog/openai-tts-pricing ; https://tokenmix.ai/blog/gpt-4o-mini-tts-cheapest-tts-api-2026 |
| ElevenLabs Creator | US$ 22/mês, 121 mil créditos (~121 min Multilingual v2 ou ~242 min Flash) → ~US$ 0,09–0,18/min | libera clone de voz profissional | https://texttolab.com/blog/elevenlabs-pricing ; https://bigvu.tv/blog/elevenlabs-pricing-2026-plans-credits-commercial-rights-api-costs/ |
| ElevenLabs Pro | US$ 99/mês, ~600 min → ~US$ 0,17/min | | idem |
| ElevenLabs Scale | 2 M créditos; excedente US$ 0,18/1k caracteres | | idem |

## Música
| Provedor | Preço citado | Observação | Fonte |
|---|---|---|---|
| Suno Pro | US$ 10/mês (8 anual), 2.500 créditos/mês | direitos comerciais só em planos pagos; **limite de 20 downloads/mês** (desde 03/09/2026) | https://lumimusic.ai/blog/suno-pricing ; https://dynamoi.com/learn/ai-music-distribution/suno-commercial-rights-explained |
| Suno Premier | US$ 30/mês (24 anual), 10.000 créditos/mês | **60 downloads/mês** (sem limite dentro do Suno Studio); modelos licenciados (acordo Warner) devem substituir os atuais em 2026 | idem |

Restrição importante: um canal lofi de 1 h/dia precisa de ~15–20 faixas novas por vídeo; com 60 downloads/mês no Premier, isso limita a ~3–4 vídeos/mês por assinatura, ou exige produção própria (Ableton/Logic + samples licenciados). Confirmar na página oficial.

## Imagem
| Provedor / modelo | Preço por imagem citado | Fonte |
|---|---|---|
| OpenAI GPT Image (low → high 1024²) | US$ 0,005–0,211 | https://www.cometapi.com/ai-image-api-pricing/ ; https://www.buildmvpfast.com/api-costs/ai-image |
| Google Nano Banana 2 / Lite | US$ 0,067 / 0,034 (1K) | idem |
| FLUX.2 (klein 4B → max) | US$ 0,014–0,07 | idem |
| Ideogram 3.0 (texto legível) | US$ 0,03 | idem |
| Agregadores (Replicate, fal) modelos abertos | US$ 0,008–0,04 | https://pricepertoken.com/image |

## Vídeo gerado
| Modelo | Preço por segundo citado | Fonte |
|---|---|---|
| Google Veo 3.1 (fast / standard / com áudio) | US$ 0,15 / 0,40 / 0,75 | https://www.buildmvpfast.com/api-costs/ai-video ; https://modelslab.com/blog/api/veo-3-1-vs-kling-3-sora-2-ai-video-api-cost-2026 |
| Kling 3.0 | US$ 0,09–0,14 | idem |
| Sora 2 | ~US$ 0,10 (ou 1/clip base) | idem |
| Runway Gen-4.5 | US$ 0,15 | idem |
| Seedance 2.0 | US$ 0,09–0,14 | idem |

## Montagem, thumbnail, publicação
- ffmpeg / Remotion no Mac: US$ 0 (custo = tempo de máquina).
- Upload via YouTube Data API: 1 unidade de quota por vídeo, até ~100/dia (secundário; ver policies Y-08).
- KDP: publicação gratuita; custo = impressão descontada do royalty (tabela oficial pendente, policies K-03).

## Custo por peça (aritmética sobre os valores acima; **estimado, a confirmar**)
| Peça | Componentes | Faixa (US$) |
|---|---|---|
| Vídeo faceless de 10 min (roteiro LLM + TTS + 20 imagens + montagem local + thumbnail) | TTS 0,15–1,80 · imagens 0,16–1,40 · LLM ~0,05–0,20 · thumb 0,03–0,21 | **~0,4–3,6** |
| Documentário de 60 min "para dormir" | TTS 0,90–10,80 · 60 imagens 0,50–4,20 · LLM 0,20–0,80 | **~1,6–16** |
| Vídeo lofi de 1 h (15 faixas Suno + 1 loop de imagem/vídeo) | assinatura rateada 1,50–7,50 · visual 0,07–9 (imagem vs. 60 s de vídeo Kling) | **~1,6–17** (limitado pelos downloads/mês) |
| Livro de colorir 50 páginas (50 imagens + capa) | imagens 0,70–10,50 · capa 0,03–0,21 | **~0,8–11** + custo de impressão por venda |
| Faixa musical para streaming | Suno rateado | **~0,10–0,50** + distribuidora (anual) |

Estes números NÃO incluem: horas humanas de revisão (que a política de conteúdo inautêntico praticamente exige), ferramentas de pesquisa, e refação (retries) que na prática dobra o custo de imagem/vídeo.
