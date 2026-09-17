# Políticas das plataformas — regras vigentes

**Data desta versão:** 2026-09-17.
**Status de leitura:** ⚠️ Nesta sessão, a rede bloqueou TODAS as páginas oficiais (support.google.com, developers.google.com, kdp.amazon.com, support.spotify.com, newsroom.spotify.com, etsy.com, merch.amazon.com, help.redbubble.com). O que está abaixo foi coletado em 2026-09-17 por **busca na web (trechos de fontes secundárias)**, não pela leitura da página oficial. Por isso, cada regra traz:

- **Fonte oficial** — a URL que vale. É ela que precisa ser lida.
- **Status** — `secundário` (lido em fonte não oficial em 2026-09-17) ou `lido em <data>` (depois que `research/fetch_policies.py` rodar no Mac e eu conferir o texto).
- **Fontes secundárias** — de onde saiu o trecho, com data de coleta.

**Como fechar essa pendência (5 min, no seu Mac):**
```bash
cd renda-automatizada && python3 research/fetch_policies.py
```
Isso baixa cada página oficial, grava texto + data + hash em `research/policies_raw/<data>/`. Me avise e eu troco `secundário` por `lido em <data>` regra por regra, corrigindo o que estiver diferente.

**Regra de uso:** onde duas fontes secundárias divergem, o valor fica marcado **conflito** e não entra em nenhuma conta até a leitura oficial. Nenhum número daqui vira premissa de score sem status `lido`.

Os IDs (Y-01, K-03…) são os mesmos de `research/fetch_policies.py`.

---

## 1. YouTube

### Y-01 — Conteúdo inautêntico (ex-"repetitious content") e conteúdo reutilizado — Programa de Parcerias
- **Fonte oficial:** https://support.google.com/youtube/answer/1311392?hl=en (YouTube channel monetization policies)
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Em **15/07/2025** o YouTube renomeou a política de "repetitious content" para **"inauthentic content"** e esclareceu que ela cobre conteúdo **repetitivo ou produzido em massa** ("mass-produced"). Frase atribuída ao YouTube: "This update better reflects what 'inauthentic' content looks like today."
  - Descrição do que é atingido: conteúdo que segue um **template com variação mínima**, fácil de reproduzir em escala, **sem contribuição autoral clara** ou substância.
  - Em **13/07/2026** o YouTube reorganizou a mesma política em três categorias nomeadas (comunicado como esclarecimento, não regra nova):
    1. **Generic or repetitive content** — "content that looks like it's made with a template, or that may feel repetitive to viewers after watching several videos in a row from the same channel".
    2. **Unsatisfying or off-putting content** — fórmulas emocionalmente manipuladoras ou feitas para chocar.
    3. **AI personas on sensitive topics** — "especialistas" de IA falsos aconselhando sobre temas sensíveis.
  - YouTube afirma que IA não é proibida: vídeos com IA que **adicionam valor original** (comentário, narrativa, pesquisa, perspectiva humana) continuam monetizáveis.
  - **Reused content** (política separada, sem mudança): usar material de terceiros sem adicionar valor ou comentário significativo. Não é questão de copyright/permissão. Exemplos não monetizáveis: clipes editados juntos sem narrativa; compilações de outras redes; vídeo alheio com filtro/velocidade/corte. Exemplos monetizáveis: reação com análise genuína, vídeo educativo usando clipes, comentário de notícia com insight próprio.
- **Impacto no projeto:** é a regra que mais ameaça "produção automatizada". Cada peça precisa de ângulo, pesquisa ou narrativa própria e variação real entre peças do mesmo canal. Isso entra no checklist pré-publicação (Fase 2) e no "risco de plataforma" do score.
- **Fontes secundárias (coletadas 2026-09-17):** Search Engine Journal https://www.searchenginejournal.com/youtube-targets-mass-produced-content-in-monetization-update/550337/ ; Social Media Today https://www.socialmediatoday.com/news/youtube-clarifies-monetization-update-inauthentic-repeated-content/752892/ ; Tubefilter (13/07/2026) https://www.tubefilter.com/2026/07/13/youtube-inauthentic-content-monetization-policy-update/ ; vidIQ https://vidiq.com/blog/post/youtube-reused-content-policy-guide/

### Y-02 / Y-03 / Y-10 — Requisitos mínimos para entrar no YPP
- **Fontes oficiais:** https://support.google.com/youtube/answer/72851?hl=en ; https://support.google.com/youtube/answer/12843009?hl=en ; anúncio https://blog.youtube/news-and-events/youtube-partner-program-updates-2027-new-opportunities-earn/
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - **Hoje (até 31/01/2027), dois níveis:**
    - Nível 1 (fan funding, Shopping): **500 inscritos** + 3 uploads públicos válidos nos últimos 90 dias + (**3.000 horas** públicas válidas de exibição nos últimos 365 dias OU **3 milhões** de views públicas válidas de Shorts em 90 dias).
    - Nível 2 (receita de anúncios e Premium): **1.000 inscritos** + (**4.000 horas** em 365 dias OU **10 milhões** de views de Shorts em 90 dias).
    - Também: sem strikes ativos de diretrizes da comunidade, verificação em 2 etapas, conta AdSense vinculada, país elegível, seguir todas as políticas de monetização.
  - **A partir de 01/02/2027 (anunciado em agosto/2026):** novos candidatos à divisão de receita precisam de **8.000 horas** em 365 dias OU **20 milhões** de views de Shorts em 90 dias (mais 1.000 inscritos). Um limiar de **10 milhões** de Shorts em 90 dias daria direito à divisão de receita **só em Shorts**. Quem já está no YPP não é afetado.
- **Impacto no projeto:** "tempo até a primeira receita" no YouTube = tempo até bater esses números. Piloto de YouTube que não entrar no YPP até janeiro/2027 enfrenta o dobro da exigência. Isso pesa no score.
- **Fontes secundárias (2026-09-17):** vidIQ https://vidiq.com/blog/post/youtube-partner-program-guide/ ; AIR Media-Tech https://air.io/en/monetization/youtube-partner-program-requirements-2026-the-complete-guide ; No Film School https://nofilmschool.com/youtube-partner-program-changes ; Business Standard (11/08/2026) https://www.business-standard.com/technology/tech-news/technology-tech-news-youtube-partner-program-monetisation-rules-2027-watch-hours-shorts-views-126081100708_1.html

### Y-04 / Y-05 — "Made for kids" (COPPA) e restrições de anúncio
- **Fontes oficiais:** https://support.google.com/youtube/answer/9528076?hl=en (definir se é para crianças) ; https://support.google.com/youtube/answer/9713557?hl=en (como anúncios funcionam em conteúdo para crianças) ; https://support.google.com/youtube/answer/9527654?hl=en (marcar a audiência)
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - O criador é obrigado por lei (COPPA, EUA) a marcar vídeo/canal como "made for kids" quando o público-alvo principal são crianças. O YouTube também pode marcar por conta própria.
  - Em conteúdo marcado para crianças: **sem anúncios personalizados** (só anúncios contextuais); **comentários desativados**; notificações, botão de inscrição, salvar em playlist/assistir mais tarde, cards/end screens e outros recursos desativados ou limitados; sem coleta de dados pessoais (device ID, IP, geolocalização).
  - Consequência prática relatada: receita de anúncios menor que em conteúdo geral, por não haver anúncio personalizado. **Sem dado numérico oficial** de quanto menor.
- **Impacto no projeto:** categoria "músicas e histórias infantis" é obrigatoriamente made-for-kids → RPM menor e sem recursos de engajamento. O score de risco trata isso como restrição estrutural, não como proibição.
- **Fontes secundárias (2026-09-17):** Google Ads policy (proteções para crianças) https://support.google.com/adspolicy/answer/15416897?hl=en ; SuperAwesome https://www.superawesome.com/blog/everything-brands-and-creators-need-to-know-about-youtubes-new-policy-on-kids/ ; Forbes (06/01/2020) https://www.forbes.com/sites/johanmoreno/2020/01/06/youtube-disables-personalized-ads-comments-on-childrens-videos/

### Y-06 — Content ID
- **Fonte oficial:** https://support.google.com/youtube/answer/2797370?hl=en ; reclamações: https://support.google.com/youtube/answer/6013276?hl=en
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Content ID compara cada upload com um banco de arquivos de referência enviados por detentores de direitos. Ao dar match, o vídeo recebe uma **reclamação (claim)**, com política escolhida pelo detentor: **monetizar** (anúncios vão para ele), **bloquear** ou **rastrear**; pode variar por país.
  - Para SER parceiro Content ID (proteger o próprio catálogo): é preciso ter **direitos exclusivos sobre um corpo substancial de material original frequentemente enviado ao YouTube**; acesso normalmente via distribuidora/agregador para músicos independentes.
- **Impacto no projeto:** (a) toda música/imagem/voz usada tem que ser gerada por nós ou licenciada para uso comercial — qualquer sample de terceiros pode virar claim; (b) música original nossa pode ser registrada em Content ID via distribuidora, virando fonte extra de receita (Fase 1C).
- **Fontes secundárias (2026-09-17):** AIR https://air.io/en/academy/youtube-content-id-how-it-works ; Talentir https://www.talentir.com/blog/what-is-youtube-content-id-and-how-do-i-enable-it ; FUGA https://support.fuga.com/hc/en-us/articles/39156341356564-Content-ID-Policy-Guidelines-YouTube

### Y-07 — Rótulo de conteúdo alterado ou sintético (IA)
- **Fonte oficial:** https://support.google.com/youtube/answer/14328491?hl=en
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Divulgação obrigatória (caixa "altered or synthetic content" no Studio) quando o conteúdo **realista** pode ser confundido com pessoa, lugar ou evento real (ex.: voz/rosto sintético de pessoa real, cena realista que não aconteceu).
  - **Não exige** divulgação para conteúdo claramente irreal, animação, efeitos, roteiro/ideias geradas por IA, ou uso de IA em produção que não altera realismo.
  - Divulgar não afeta recomendação nem elegibilidade de monetização, segundo o YouTube. **Não divulgar** quando devido: o YouTube pode aplicar o rótulo à força, dar avisos, remover conteúdo e, em reincidência, suspender do YPP. Fontes citam que desde **maio/2026** o YouTube aplica detecção automática e rotula sozinho.
- **Impacto no projeto:** o checklist pré-publicação marca o rótulo sempre que houver voz/imagem sintética realista. Para animação/lofi/histórias claramente ficcionais, marcar é opcional; decisão: marcar sempre que houver dúvida.
- **Fontes secundárias (2026-09-17):** Minimatters https://minimatters.com/youtube-altered-or-synthetic-content-disclosure/ ; SyncStudio https://syncstudio.ai/blog/youtube-synthetic-content-disclosure ; SEOVendor https://seovendor.co/decoding-youtubes-latest-ai-content-labeling-tool/

### Y-08 / Y-09 — YouTube Data API v3: quota e custos
- **Fontes oficiais:** https://developers.google.com/youtube/v3/determine_quota_cost ; https://developers.google.com/youtube/v3/getting-started ; histórico https://developers.google.com/youtube/v3/revision_history
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Quota padrão: **10.000 unidades/dia** por projeto. `videos.list`, `channels.list`, `playlistItems.list`: **1 unidade**. `search.list`: **100 unidades**.
  - Mudanças reportadas: em 04/12/2025 `videos.insert` caiu de ~1.600 para ~100 unidades; em **01/06/2026** `search.list` e `videos.insert` teriam passado a "baldes" próprios de **~100 chamadas/dia cada**, fora do pool de 10.000. **Conflito/incerteza:** fontes secundárias divergem sobre se `search.list` ainda debita 100 unidades do pool geral. Até leitura oficial, `research/yt_client.py` assume o pior dos dois mundos (100 unidades E máximo de 90 chamadas/dia).
- **Impacto no projeto:** descoberta via `search.list` é escassa (≤ 90-100 por dia). Coleta em massa usa `playlistItems` + `videos.list`/`channels.list` e cache.
- **Fontes secundárias (2026-09-17):** DEV Community https://dev.to/siyabuilt/youtubes-api-quota-is-10000-unitsday-heres-how-i-track-100k-videos-without-hitting-it-5d8h ; SocialCrawl https://www.socialcrawl.dev/blog/youtube-data-api-2026 ; Blotato https://www.blotato.com/blog/youtube-api-pricing ; bundle.social https://bundle.social/blog/youtube-api-quota-exceeded-limits-fixes

---

## 2. Amazon KDP

### K-01 — Declaração obrigatória de conteúdo gerado por IA
- **Fonte oficial:** https://kdp.amazon.com/en_US/help/topic/G200672390 (Content Guidelines, seção "AI-generated content")
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias, texto próximo do oficial):**
  - A KDP **exige informar** conteúdo **AI-generated** (texto, imagens ou traduções) ao publicar livro novo ou republicar edição. **Não exige** informar conteúdo **AI-assisted**.
  - **AI-generated:** "text, images, or translations created by an AI-based tool" — vale **mesmo com edições substanciais depois**. Inclui capa e imagens internas.
  - **AI-assisted:** você criou o conteúdo e usou IA para editar, refinar, corrigir ou melhorar; ou usou IA para brainstorm mas produziu o texto/imagem você mesmo.
  - O autor é responsável por garantir que todo conteúdo gerado/assistido por IA respeita as diretrizes, inclusive propriedade intelectual.
  - A declaração é feita no formulário de publicação e **não aparece publicamente** na página do livro (segundo fontes secundárias; confirmar na leitura oficial — relevante para a coleta 1B, "declaração de IA visível").
- **Impacto no projeto:** livro de colorir com imagens geradas por IA = **AI-generated**, declaração obrigatória. Sem exceção.
- **Fontes secundárias (2026-09-17):** Authors Guild https://authorsguild.org/news/amazon-adds-to-kdp-generative-ai-policy-caps-daily-self-publishing-uploads/ ; Univers Studio https://www.univers.studio/blog/kdp-ai-content-policy-2026/ ; Blurbbio https://app.blurbbio.com/blog/amazon-kdp-ai-disclosure-guide

### K-06 — Limite diário de novos títulos
- **Fonte oficial:** https://www.kdpcommunity.com/s/article/Update-on-KDP-Title-Creation-Limits?language=en_US (aviso da KDP no fórum oficial)
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Em **setembro/2023** a KDP anunciou redução do limite de criação de títulos "para proteger contra abuso", sem publicar o número. Imprensa (Publishers Weekly, Authors Guild, Slashdot) reportou **3 novos títulos por dia** por conta. Contas com histórico podem pedir exceção.
  - Atualizações de livros existentes não contam. O limite é **por conta**, não por pseudônimo.
  - **Conflito de datas:** uma fonte secundária diz "introduzido no fim de 2024"; Publishers Weekly e Authors Guild datam de setembro/2023. Prevalece a imprensa especializada até leitura oficial.
- **Impacto no projeto:** teto físico de ~90 títulos/mês por conta KDP. Entra no cálculo de "vendas/mês necessárias" e no agendador de publicação (Fase 2).
- **Fontes secundárias (2026-09-17):** Publishers Weekly https://www.publishersweekly.com/pw/by-topic/digital/content-and-e-books/article/93207-kdp-will-limit-daily-number-of-new-titles.html ; Jane Friedman https://janefriedman.com/amazon-kdp-limits-how-many-books-can-be-uploaded-per-day/ ; Slashdot (25/09/2023) https://news.slashdot.org/story/23/09/25/2028200/amazon-restricts-authors-from-self-publishing-more-than-three-books-a-day-after-ai-concerns

### K-02 — Conteúdo de baixa qualidade / "disappointing content"
- **Fontes oficiais:** https://kdp.amazon.com/en_US/help/topic/G200952510 (Guide to Kindle Content Quality) ; https://kdp.amazon.com/en_US/help/topic/G200672390
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - KDP não permite conteúdo que "decepciona o cliente": duplicado, faltando, metadados imprecisos, formatação ruim, **reuso excessivo**, conteúdo livremente disponível na web, e **guias companheiros** (resumos, workbooks, análises de outros livros) salvo exceções.
  - Enforcement em 2026 descrito como mais rígido contra **near-duplicates** e uploads gerados em massa; low-content (colorir, diários, planners) **continua permitido**, mas variações mínimas de um mesmo interior/capa são removidas.
  - Violações graves podem levar a **encerramento de conta**, não só remoção do título (detalhe do critério: sem dado nas fontes secundárias).
- **Impacto no projeto:** cada livro precisa de interior realmente distinto (verificação de duplicidade contra o próprio catálogo, Fase 2). "Séries" de 50 livros de colorir com o mesmo miolo remixado = exatamente o que a regra proíbe.
- **Fontes secundárias (2026-09-17):** Vappingo https://www.vappingo.com/word-blog/kdp-content-guidelines/ ; Pubnook https://pubnook.com/article/amazon-kdp-low-content-book-policy-2026-whats-allowed-and-what-gets-removed

### K-03 / K-04 / K-05 — Custo de impressão e royalties
- **Fontes oficiais:** https://kdp.amazon.com/en_US/help/topic/G201834340 (custo de impressão paperback) ; https://kdp.amazon.com/en_US/help/topic/G201834330 (royalty paperback) ; https://kdp.amazon.com/en_US/help/topic/G200644210 (royalty eBook)
- **Status:** secundário (2026-09-17) — **CONFLITO entre fontes; nenhum valor abaixo pode ser usado em conta até leitura oficial.**
- **O que dizem as fontes secundárias (Amazon.com, paperback):**
  - Royalty paperback: **60% do preço de capa − custo de impressão** (consenso entre fontes).
  - Custo de impressão, tinta preta: uma fonte diz **US$ 0,85 + 0,012/página**; outra diz **US$ 1,00 + 0,012/página** (exemplo citado: 300 páginas = US$ 4,60). → **conflito no custo fixo**.
  - Cor padrão: uma fonte diz **US$ 0,85 + 0,07/página**; outra diz **US$ 1,00 + 0,0255/página**. → **conflito**.
  - Cor premium: **US$ 3,60 fixo** para 24–40 páginas; acima de 40 páginas **US$ 1,00 + 0,065/página** (uma fonte).
  - Livros de colorir são normalmente tinta preta em papel branco; o custo fixo (0,85 vs 1,00) muda o royalty por título em US$ 0,15 — pequeno, mas o projeto não usa valor em conflito.
  - eBook: opções **35%** e **70%** (70% exige preço entre US$ 2,99 e 9,99 e desconta custo de entrega por MB) — valores citados por fontes secundárias; confirmar.
- **Impacto no projeto:** a fórmula por título (Fase 1B) só será preenchida com a tabela oficial lida. Até lá, campo = "sem dado (tabela oficial pendente)".
- **Fontes secundárias (2026-09-17):** Cambric https://cambric.pub/guides/kdp-printing-cost-guide/ ; KDP Tools https://kdptools.io/print-cost-calculator ; Univers Studio https://univers.studio/kdp-calculator/ ; The Author Central https://theauthorcentral.com/blog/kdp-paperback-printing-cost-guide/

---

## 3. Spotify / Apple Music via distribuidoras

### S-03 — Política do Spotify para música gerada por IA
- **Fonte oficial:** https://newsroom.spotify.com/2025-09-25/spotify-strengthens-ai-protections/
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Anúncio de **25/09/2025** com três medidas: (1) **política de impersonação** — clone de voz de artista só com autorização do artista; (2) **filtro de spam musical** contra uploads em massa, duplicatas, "SEO hacks" e faixas artificialmente curtas; (3) adoção do padrão **DDEX** para **declaração de uso de IA** nos créditos da faixa (via distribuidora).
  - Spotify removeu **mais de 75 milhões** de faixas "spammy" nos 12 meses anteriores. Não há proibição de música feita com IA; o alvo é spam, fraude e impersonação.
- **Impacto no projeto:** música original gerada por IA é permitida, com declaração via distribuidora, sem clonar voz de ninguém, sem catálogo em massa de faixas quase iguais.
- **Fontes secundárias (2026-09-17):** Variety https://variety.com/2025/digital/news/spotify-new-ai-safeguards-1236528493/ ; Music Week https://www.musicweek.com/digital/read/spotify-cleans-up-ai-slop-with-more-protections-for-real-artists-including-disclosure-on-genai-music/092725 ; Forbes https://www.forbes.com/sites/billrosenblatt/2025/09/26/spotify-tightens-ai-policy-and-trims-catalog/

### S-01 / S-02 / S-04 — Streaming artificial e mínimos para pagamento (Spotify)
- **Fontes oficiais:** https://support.spotify.com/us/artists/article/artificial-streaming/ ; https://support.spotify.com/us/artists/article/modernizing-our-royalty-system/ ; https://loudandclear.byspotify.com/faqs/why-dont-songs-with-less-than-1000-annual-streams-earn-recording-royalties-on-spotify-anymore/
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Desde **01/04/2024**: uma faixa só entra no pool de royalties de gravação se tiver **≥ 1.000 streams nos últimos 12 meses**. Abaixo disso, não paga; o dinheiro é redistribuído.
  - Faixas de **ruído funcional** (white noise, sons da natureza, ASMR não falado, silêncio, sons de máquina) precisam de **≥ 2 minutos** para gerar royalties.
  - **Streaming artificial** detectado: cobrança de **US$/€ 10 por faixa** de labels/distribuidoras (repassada ao artista), remoção de faixas e possível encerramento.
  - Spotify **não publica taxa por stream**; o intervalo **US$ 0,003–0,005/stream** citado na web é média retroativa calculada por terceiros → tratar como **estimado**. Dados oficiais agregados: relatório Loud & Clear.
- **Impacto no projeto:** música ambiente/sleep tem de ter ≥ 2 min e precisa de ouvintes reais; qualquer "promoção" que compre streams é fatal. Payout por stream entra no score só como faixa **estimada**, com fonte.
- **Fontes secundárias (2026-09-17):** Music Business Worldwide https://www.musicbusinessworldwide.com/changes-to-spotifys-royalty-model-including-the-1000-annual-streams-royalty-policy-are-officially-live/ ; iMusician https://imusician.pro/en/resources/blog/spotify-streams-no-royalties ; Chartlex https://www.chartlex.com/blog/money/how-much-does-spotify-pay-per-stream-2026

### Apple Music — rótulos de IA ("Transparency Tags" / "Made With AI")
- **Fonte oficial:** sem URL pública única identificada (comunicados a distribuidoras/labels). Confirmar na Apple Music for Artists / Style Guide. **Marcado: fonte oficial pendente.**
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - **Março/2026:** Apple introduziu **AI Transparency Tags** (opcionais) para conteúdo "materially generated" por IA.
  - **20/08/2026:** Apple avisou labels/distribuidoras que as tags passam a ser **obrigatórias** ainda em 2026 quando IA cria "porção material" da faixa, composição, arte ou vídeo; rótulo visível ao ouvinte **"Made With AI"** previsto para o fim de 2026. Não há proibição de música com IA.
- **Impacto no projeto:** declarar IA na distribuidora cobre Spotify (DDEX) e Apple (tags). Sem declaração = risco de remoção.
- **Fontes secundárias (2026-09-17):** Forbes (05/03/2026) https://www.forbes.com/sites/conormurray/2026/03/05/apple-music-introduces-transparency-tags-to-flag-ai-generated-music-and-artwork/ ; AppleInsider (20/08/2026) https://appleinsider.com/articles/26/08/20/apple-musics-ai-disclosure-labels-will-soon-be-mandatory-rather-than-optional ; 9to5Mac https://9to5mac.com/2026/08/20/apple-music-will-soon-get-visible-labels-for-ai-generated-content/

### S-05 / S-06 — Distribuidoras: política de IA e mínimo de saque
- **Fontes oficiais:** DistroKid https://support.distrokid.com/hc/en-us/articles/360013648353-Is-There-a-Minimum-Payout-Threshold ; https://support.distrokid.com/hc/en-us/articles/360013547274-How-and-When-Do-I-Get-Paid ; TuneCore: URL oficial do mínimo de saque **pendente**.
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - **DistroKid:** aceita música gerada por IA desde que você detenha os direitos comerciais (fontes citam exigência de plano pago do gerador no momento da geração); desde **maio/2026** tem campo próprio de **AI credits/disclosure**; faixa com sinais de IA sem declaração é revisada, e reincidência pode suspender a conta. Mínimo de saque **US$ 6** (mais a taxa do meio de pagamento). Pagamento das plataformas chega ~2–3 meses depois do stream.
  - **TuneCore:** mínimo de saque **US$ 20** (plano base) / **US$ 10** (Unlimited); pagamentos passaram a mensais em 2026, segundo fonte secundária.
- **Impacto no projeto:** "tempo até primeira receita" em música ≈ 2–3 meses após o primeiro stream válido. Distribuidora escolhida deve ter campo de declaração de IA (DDEX).
- **Fontes secundárias (2026-09-17):** Digital Music News (14/05/2026) https://www.digitalmusicnews.com/2026/05/14/distrokid-ai-credit-disclosure-what-it-looks-like/ ; Dynamoi https://dynamoi.com/learn/music-distribution/distributor-payout-timing-comparison ; RouteNote https://routenote.com/radar/distrokid-payments-when-does-distrokid-pay-royalties/

---

## 4. Print-on-demand

### P-01 — Etsy: Creativity Standards e IA
- **Fonte oficial:** https://www.etsy.com/legal/policy/creativity-standards/1311734473574
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Padrões de criatividade (julho/2024, reforçados em 2026): todo item precisa de "toque humano criativo" e é classificado em **Made by / Designed by / Sourced by / Handpicked by**.
  - Item feito com IA generativa: permitido, mas deve ser marcado como **"Designed by [seller]"** (não "Made by"), o vendedor deve ter dirigido a criação (tema, prompts, revisão, edição, curadoria) e **divulgar o uso de IA** na listagem. Falta de divulgação → remoção da listagem (fontes relatam sem aviso prévio).
  - Proibido: revenda de itens sem contribuição criativa; arquivos de IA "brutos" sem direção do vendedor.
- **Impacto no projeto:** designs POD via Etsy exigem rótulo "Designed by" + frase de divulgação de IA em cada listagem. Automatizável, mas visível ao comprador.
- **Fontes secundárias (2026-09-17):** Bulkmockup https://www.bulkmockup.com/etsy-policy-changes/ ; Ngini https://ngini.com/en-hk/blog/etsy-ai-disclosure-policy-2026-explained ; Artomate https://www.artomate.app/blog/etsy-ai-disclosure-policy-2026

### P-02 — Amazon Merch on Demand
- **Fonte oficial:** https://merch.amazon.com/resource/201858630 (Content Policy)
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Não há regra publicada específica permitindo ou proibindo IA; designs com IA passam pelas mesmas checagens de PI, cópia, conteúdo, metadados e qualidade. Fontes relatam remoção de "low-effort AI artifacts" e conteúdo produzido em massa. Você deve ter direitos sobre o design.
  - **Royalties (desde 01/06/2026):** modelo em 3 níveis por origem do tráfego — **Creator** (padrão; exemplo citado: camiseta US$ 19,99 → US$ 2,44), **Plus** (≥ 15% das vendas mensais vindas de tráfego externo → US$ 4,88, igual à taxa antiga), **Premium** (≥ 35% externo → US$ 5,27). Amazon controla o número de designs por "tier" de conta (10, 25, 100…), subindo conforme vendas. Valores = **secundário**, confirmar na página oficial.
- **Impacto no projeto:** sem tráfego próprio, royalty por camiseta cai pela metade em relação a 2025. Isso reforça o candidato "aplicar o motor à audiência que já tenho" (Fase 1C).
- **Fontes secundárias (2026-09-17):** Merch Titans https://merchtitans.com/blog/amazon-merch-royalty-changes-june-2026 ; MyDesigns https://mydesigns.io/blog/amazon-merch-royalty-changes-2026/ ; AMZ Prep https://amzprep.com/amazon-merch-on-demand/

### P-03 / P-04 — Redbubble
- **Fontes oficiais:** https://help.redbubble.com/hc/en-us/articles/202270929-Community-and-Content-Guidelines ; https://help.redbubble.com/hc/en-us/articles/50959863016724 (tiers e taxa da plataforma)
- **Status:** secundário (2026-09-17)
- **O que diz (segundo fontes secundárias):**
  - Sem proibição de IA; conteúdo gerado por IA é tratado como qualquer outro perante as Community & Content Guidelines, e o artista é 100% responsável. Fontes relatam exigência de **transparência na descrição** para arte com IA e que o principal motivo de banimento é **violação de PI** (personagens, marcas, celebridades geradas por IA).
  - **Tiers de conta** (oficial, via help center): **Standard** paga **50%** de taxa de plataforma sobre ganhos mensais; **Premium** paga **20%**; **Pro** paga **0%**. Taxa limitada a US$/€/£ 150 por período. Classificação depende de qualidade, volume, atividade, sucesso comercial e conformidade. Fontes citam "spam de IA em massa" como caminho direto para o tier Standard ou suspensão.
  - Limites de upload por dia para IA (5/20/50) aparecem **só em blogs**, sem página oficial encontrada → **sem dado oficial**.
- **Impacto no projeto:** conta nova = tier Standard = metade dos ganhos vai em taxa. Score de POD-Redbubble parte com penalidade.
- **Fontes secundárias (2026-09-17):** Redbubble blog https://blog.redbubble.com/2023/04/how-accounts-are-reviewed-and-classified/ ; PrintKK https://www.printkk.com/blog/articles/can-you-sell-ai-art-on-redbubble ; Trendlytic https://www.trendlytic.io/blog/can-you-sell-ai-art-on-redbubble

---

## 5. Pendências desta página
| # | Pendência | Como fechar |
|---|---|---|
| 1 | Todas as regras estão `secundário` | Rodar `python3 research/fetch_policies.py` no Mac e me avisar |
| 2 | Custo de impressão KDP em **conflito** (0,85 vs 1,00 fixo; cor 0,07 vs 0,0255/pág) | Leitura de K-03 |
| 3 | `search.list` ainda debita 100 unidades do pool? | Leitura de Y-08 |
| 4 | URL oficial da política de IA da Apple Music | Procurar em Apple Music for Artists após leitura; se não houver página pública, registrar "comunicado a distribuidoras, sem URL pública" |
| 5 | URL oficial do mínimo de saque da TuneCore | Buscar em support.tunecore.com |
| 6 | Declaração de IA na KDP é visível ao comprador? | Leitura de K-01 (afeta a coleta 1B) |
| 7 | Limite diário de uploads de IA no Redbubble | Sem página oficial; fica "sem dado" salvo se P-03 mencionar |
