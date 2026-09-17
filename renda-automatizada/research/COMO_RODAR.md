# Como rodar a coleta no Mac (passo a passo)

Tudo roda no seu Mac. Os dados vão para o repositório e eu leio e respondo aqui no chat. Tempo total do seu lado: ~30 minutos de atenção no primeiro dia; depois é automático.

## Antes de começar (uma vez só)

**1. Abrir o Terminal.** ⌘ + espaço, digite `Terminal`, Enter.

**2. Ter o git e o Python.** Cole no Terminal e dê Enter:
```bash
xcode-select --install
```
Se aparecer uma janela pedindo para instalar, aceite e espere terminar. Se disser que já está instalado, ótimo.

**3. Ter o repositório no Mac.** Se você já tem a pasta `elite-crm-system` no Mac, pule para o passo 4. Se não:
```bash
cd ~/Documents
git clone https://github.com/eliteofmiami-lab/elite-crm-system.git
```
Se pedir usuário e senha do GitHub: a senha tem que ser um **token** (GitHub → Settings → Developer settings → Personal access tokens → Generate new token, com permissão `repo`). O caminho mais fácil é instalar o **GitHub Desktop** (https://desktop.github.com), entrar com sua conta e clonar o repositório por lá. Depois disso o Terminal também consegue enviar.

**4. Entrar na branch do projeto:**
```bash
cd ~/Documents/elite-crm-system
git fetch origin claude/renda-automatizada-50k-w63bt3
git checkout claude/renda-automatizada-50k-w63bt3
git pull origin claude/renda-automatizada-50k-w63bt3
cd renda-automatizada
```

**5. Criar a chave da YouTube API** (10 min, gratuito): siga `research/GUIA_YOUTUBE_API.md` e cole a chave em `renda-automatizada/.env`.

## Dia 1 — rodar tudo
Dentro de `renda-automatizada/`:
```bash
bash research/rodar.sh
```
O que acontece, em ordem:
1. Baixa as páginas oficiais de política (para eu fechar o `policies.md`).
2. Testa a chave (gasta 1 unidade).
3. YouTube: descobre canais e vídeos das 11 categorias, tira o primeiro "retrato" (snapshot) dos canais. Usa até 9.000 unidades e para; o resto continua no dia seguinte, sozinho.
4. Marketplaces de aquisição (prova de receita). Se alguma página for só JavaScript, ele avisa e a coleta é manual (`research/EVIDENCIAS_MANUAL.md`, 10–15 min por site).
5. Envia os dados para o repositório.
6. Amazon KDP: ~1h30 abrindo páginas de livros com pausa entre elas (para não ser bloqueado). Pode deixar rodando ou parar com Ctrl+C e rodar depois com `python3 research/kdp_coleta.py`.
7. Envia os dados KDP.

## Agendar a coleta diária (uma vez)
```bash
bash research/install_launchd.sh
```
Todo dia às 08:00 o Mac continua a coleta (retoma buscas que faltaram, tira novo snapshot dos canais e envia). É esse snapshot diário que permite **medir** views/mês por diferença, sem estimar. Se o Mac estiver dormindo, roda quando acordar. Precisa de pelo menos 7 dias de snapshots para a medição valer.

## Depois
Me diga no chat: **"rodou"**. Eu leio o que chegou e entrego aqui:
- no mesmo dia: `policies.md` fechado com datas oficiais, retrato das categorias (quem são os canais, cadência de upload, % kids, % Shorts, idade), evidências de receita encontradas, primeiros dados KDP;
- após 7 dias de snapshots: views/mês medidas por canal e o ranking completo (`reports/oportunidades.md`) para o Gate 1.

## Se algo der errado
Copie a mensagem de erro inteira do Terminal e cole aqui. Os logs ficam em `renda-automatizada/data/logs/`. Nunca cole a chave da API.
