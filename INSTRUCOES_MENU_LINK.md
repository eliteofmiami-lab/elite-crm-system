# Fila DENTRO do GHL — Custom Menu Link (passo a passo, 3 minutos)

A fila agora vive numa coluna única e somente-leitura, feita pra abrir dentro do GHL.

## Passos (você faz uma vez)

1. No GHL, abra **Settings** (engrenagem, menu da esquerda, lá embaixo).
2. No menu de Settings, clique em **Custom Menu Link** (às vezes aparece como
   "Custom Menu Links" dentro de *Company/Location settings*).
3. Clique **+ Add Custom Menu Link** e preencha:
   - **Title:** `Elite — Fila`
   - **URL:** `https://elite-crm-panel.vercel.app/?layout=rail`
   - **Icon:** o que preferir (sugestão: telefone 📞)
   - **Open in:** `iFrame` (abre DENTRO do GHL — recomendado).
     Se a tela ficar em branco no iFrame, troque para `New tab` (funciona igual).
   - **Show to:** marque a location Elite (Ao5ER8XBg3AtCJMccesF) e deixe visível
     para os usuários (você e Eugene).
4. Salvar. O item **Elite — Fila** aparece no menu lateral esquerdo do GHL.

## Primeiro uso (cada um faz uma vez)

- Ao abrir, aparece a tela de login do painel: cada um entra com o próprio
  e-mail/senha de sempre do painel. Fica logado nas próximas vezes.

## O que vocês vão ver

- A fila ordenada (camada → gatilho → score → antiguidade). **O card nº 1 é o
  próximo a ligar.**
- Cada card: nome · veículo · o que ele procura · **a história em 2 linhas (com
  datas)** · score conhecido/máximo (✓ = verificado por call) · telefone · botão
  **Open contact ↗** que abre o contato no GHL.
- **Nenhum botão escreve nada.** O Eugene registra tudo direto no GHL (notas,
  campos, tags) — o cérebro LÊ no ciclo seguinte (≤5 min) e a fila se reordena
  sozinha. Cards somem quando a ligação/SMS é detectada.

## Estados que governam a fila (Regra Zero)

- `CALLBACK OWED` (vermelho) — cliente ligou e não foi atendido: topo absoluto.
- `Client deciding — don't chase` — pediu espaço: fora da discagem, nurture na data.
- `Waiting external event` — ex.: esperando modelo novo: volta só na janela.
- `Scheduled` — agendado: aparece só na data do follow-up/confirmação.
- Pós-venda — invisível (gestão pessoal sua).
