# 5785 N Surf Rd — estudo conceitual de planta baixa

Estudo conceitual e verificação de viabilidade para uma nova residência unifamiliar frente-mar em
5785 N Surf Rd, Hollywood FL 33019 (parcel 514201027042, zoneamento NBDD-CZ).

- `index.html` — conjunto de pranchas (A-000 a A-401): veredito, implantação, corte de alturas,
  plantas do térreo/garagem, níveis 1–3 e rooftop, quadro de áreas, matriz de aprovações e fontes.
- `design.json` — geometria única de onde saem todas as plantas e o quadro de áreas
  (retângulos x, y, w, h em pés dentro do envelope 30' × 55'; x cresce para leste/oceano, y para norte).
- `build/` — scripts de geração: `validate.js` (checagem geométrica e de programa), `render.js`
  (plantas SVG e tabelas), `site.js` (implantação e cortes), `content.js` (textos), `build.js` (monta a página).

Regerar: `cd build && node build.js` (a geometria e o mobiliário vêm de `build/plan.js`; `design.json` é a exportação validada).

Status: emissão preliminar P1 (14 set 2026). "CONCEPTUAL PLAN — ASSUMES SETBACK VARIANCES". Não é
levantamento, determinação de zoneamento, desenho de licenciamento nem engenharia.
