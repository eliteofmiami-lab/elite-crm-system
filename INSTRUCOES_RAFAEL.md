# INSTRUÇÕES PARA O RAFAEL — o que só você pode fazer (contas + cliques na UI)

> O sistema (worker + painel) eu construo. Mas algumas coisas dependem de **você** criar conta, colar chave no `.env` ou clicar na interface do GHL. Enquanto você faz isso, eu adianto tudo que não depende de chave (score, dry-runs, auditorias).
>
> **Regra de ouro:** chaves e senhas **só no arquivo `.env`** (nunca no chat). Eu nunca vejo o valor — só uso.
> O arquivo fica em `Desktop → Elite Customs → ELITE CRM → .env` (já existe, é só preencher as linhas vazias).

---

## PARTE 1 — Chaves e contas (colar no `.env`)

### 1.1 GHL — ampliar as permissões da Private Integration ⚠️ (bloqueia todas as escritas)
Hoje o token só **lê**. Para o sistema trabalhar, ele precisa **escrever**.
1. GHL → subconta Elite → **Settings → Private Integrations**.
2. Abra a integração que você criou (a do token `pit-…`).
3. Marque também estes escopos de **escrita** (mantendo os de leitura que já estão):
   - Contacts — **write**
   - Opportunities — **write**
   - Conversations / Messages — **write** (para enviar SMS)
   - Notes — **write**
   - Tasks — **write**
   - Custom Fields — **write**
   - Tags — **write**
4. Salve. **O token continua o mesmo** — não precisa colar de novo. (Se o GHL gerar um token novo, aí sim me avise que atualizo o `.env`.)

O Token ja te da total acesso! Desde o inicio

### 1.2 Deepgram (transcrição das chamadas) — pago por uso
1. Crie conta em **deepgram.com** → console → **API Keys** → crie uma chave.
2. Cole no `.env` na linha `DEEPGRAM_API_KEY=`.
3. Custo é por minuto de áudio transcrito (barato); eu monto para transcrever só o que vale.
✅ Chave recebida — já está no `.env` (removida daqui: este arquivo vai pro git). **Rafael: feche este arquivo no seu editor** — se salvar de novo, a chave volta.

### 1.3 Anthropic (o "cérebro" que analisa as conversas)
1. Você já tem uma `ANTHROPIC_API_KEY` no projeto do livro. Pode usar a mesma ou criar outra em **console.anthropic.com**.
2. Cole no `.env` na linha `ANTHROPIC_API_KEY=`.
Devemos criar outro projeto dentro da mesma conta? Pra manter o projeto do livro separado da Elite? 


### 1.4 Supabase (banco de dados do painel) — de graça no início
1. Em **supabase.com** → New Project → nome `elite-crm` (mesmo fluxo do Portal de Vagas).
2. Em **Project Settings → API**, copie e cole no `.env`:
   - `SUPABASE_URL=` https://blybofxubrusitydpfwq.supabase.co
   - `SUPABASE_ANON_KEY=` (anon public)
   - `SUPABASE_SERVICE_ROLE_KEY=` (service_role — **secreta**, nunca no painel/site)

### 1.5 GitHub + Vercel (onde o sistema roda 24/7)
1. **GitHub:** crie um repositório **privado** chamado `elite-crm-system`. Me diga o nome de usuário/URL que eu configuro o envio do código.
2. **Vercel:** conta grátis, conectada ao GitHub (para publicar o painel). Fazemos junto quando o painel estiver pronto.
3. **Secrets do GitHub Actions:** vou te passar a lista exata (é espelhar o `.env`) quando chegarmos lá — um item por vez, você cola no GitHub.

### 1.6 Telefone do Eugene (para os avisos por SMS)
- Coloque o número no `.env` em `EUGENE_PHONE=` (formato `+1305...`). É para onde vão os "cutucões" quando a fila ficar parada.

---

## PARTE 2 — Cliques na interface do GHL (a API não faz isso)

### 2.1 Criar o stage `HOT LEADS` no New Pipeline ⚠️ (bloqueia a Migração M1)
- New Pipeline → adicionar um stage chamado **`HOT LEADS`**, posicionado **logo depois de `Great Cars`**.
- É onde toda ligação recebida (inbound) vai cair. **Não começo a migração até esse stage existir** — me avise quando criar que eu confirmo pela API.

### 2.2 Workflow do primeiro SMS — branch de horário
- No workflow `1: FIRST SMS - Ads` (ou equivalente do New Pipeline), adicione uma condição de **horário**: se o lead chegar **fora do horário comercial ou no fim de semana**, enviar uma mensagem diferente (ex.: "Recebi seu contato, retorno logo pela manhã") em vez do texto padrão de horário comercial.
- Me diga o texto que você quer nas duas situações, ou eu sugiro.

### 2.3 Confirmar gatilhos de workflow (só verificar e me dizer "sim/não")
- **Great Cars → CAPI:** mover uma opp para o stage `Great Cars` **dispara** o workflow `2.1: GREAT CARS - ADS` (que manda evento pro Meta)? Confirme.
- **Remarketing:** qual stage dispara o drip de remarketing de leads perdidos? (`Lost`? `NEVER ANSWERED`?)
- **Inbound cria opp:** o workflow `Create opportunity via incoming Phone call` está ligado e realmente cria a oportunidade quando entra ligação? (para eu não criar duplicado)

### 2.4 Calendários — desativar os obsoletos
- Manter ativos só: **`Booking Request`**, **`ELITE BOCA RATON`**, **`Ceramic Pro Silver Package`**.
- Os "Personal Calendar" de gente que não está mais na operação podem ser desativados (não delete — só desative), para o monitoramento de no-show não olhar no lugar errado.

### 2.5 Nedzo AI
- Confirmado com você que o **Nedzo AI está desativado**. Vou ignorar os workflows dele; nosso sistema assume a operação. Se ainda estiver ligado, desative para não haver dois "cérebros" agindo.
OTIMO
---

## PARTE 3 — Aprovações que vou te pedir (os "gates")

Nada é escrito no GHL/Urable sem você aprovar. Cada gate = eu te mostro um CSV/relatório do que **vai** acontecer, você responde "aprovado", aí executo e registro tudo em `out/write_log.jsonl` (trilha de auditoria).

| Gate | O que aprova | Já pronto p/ revisar? |
|---|---|---|
| **G0-A** | Criar os 7 custom fields de oportunidade | ✅ `docs/GATE_G0A_custom_fields.md` |
| **G0-B** | Gravar o score dos 330 leads nesses campos | ✅ `out/writeback_dryrun_G0B.csv` (20 exemplos) |
| **G1** | Migrar os leads bons do ELITE ADS → New Pipeline | ⏳ depende do stage HOT LEADS (2.1) |
| **G2** | Ligar as escritas automáticas pós-chamada | ⏳ depende de Deepgram+Anthropic (demonstro com 5 calls antes) |
| **G2-U** | Criar Customer+Item no Urable | ⏳ na 1ª preparação de quote |

---

## RESUMO — sua lista de hoje (ordem sugerida)
1. [X] Ampliar escopos de escrita da Private Integration (1.1) ← destrava tudo
2. [ ] Criar stage `HOT LEADS` no New Pipeline (2.1) ← destrava a migração
3. [X ] Colar `DEEPGRAM_API_KEY`, `ANTHROPIC_API_KEY` no `.env` (1.2, 1.3)
4. [ X] Criar Supabase `elite-crm` e colar as 3 chaves (1.4)
5. [ ] Criar repo privado `elite-crm-system` no GitHub e me mandar a URL (1.5)
6. [ ] `EUGENE_PHONE` no `.env` (1.6)
7. [ ] Revisar e aprovar **G0-A** e **G0-B** (Parte 3)
8. [ ] Responder as confirmações de workflow (2.3)

Pode fazer em qualquer ordem; me avise o que foi feito que eu sigo destravando cada pedaço.
