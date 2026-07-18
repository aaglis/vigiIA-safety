# Acurácia da visão computacional — o que medimos e o que ainda não sabemos

## O número local (18/07/2026)

Modelo `ppe-multiclass.pt`, dataset interno `cv-real/v2`, confiança mínima 0.4:

| Métrica | Valor |
|---|---|
| Precisão (EPI, por frame) | **1.00** |
| Recall (EPI, por frame) | **0.50** |
| F1 | **0.667** |
| TP / FP / FN / TN | 7 / 0 / 7 / 19 |
| Pessoas detectadas | 76 de 76 |
| `no-helmet` esperado/detectado | 28 / 22 |
| Latência de inferência | **353 ms** (média), 489 ms (p95), 579 ms (máx) |

Cobertura do `cv-real/v2`:

| Cobertura | Quantidade |
|---|---:|
| Frames avaliados | 33 |
| Frames com pessoa usando capacete | 24 |
| Frames com pessoa sem capacete | 14 |
| Frames sem pessoa anotada | 2 |
| Cenários | `textil` (3), `obra` (30) |

Métrica EPI por cenário:

| Cenário | Frames | Precisão | Recall | F1 | TP / FP / FN / TN |
|---|---:|---:|---:|---:|---:|
| `textil` | 3 | 1.000 | 0.333 | 0.500 | 1 / 0 / 2 / 0 |
| `obra` | 30 | 1.000 | 0.545 | 0.706 | 6 / 0 / 5 / 19 |

Proxy de intrusão por frame (pessoa presente vs `restricted_intrusion`, zona cobrindo o
quadro inteiro): TP 25, FP 2, FN 6, TN 0. Ainda **não** valida geometria de polígono.

Reproduzir o smoke local:

```bash
docker compose -f infra/compose/docker-compose.dev.yml --profile cv run --rm --no-deps \
  -v "$PWD/apps/edge-worker/datasets:/datasets:ro" \
  --entrypoint python edge-worker -m vigia_edge_worker.evaluation_real \
  --dataset /datasets/cv-real/v2/manifest.json \
  --model /models/ppe-multiclass.pt \
  --min-samples 30 \
  --min-helmet-samples 1 \
  --min-empty-samples 1 \
  --min-ppe-recall 0.45
```

O piso de CI acordado para o modelo atual é **recall EPI ≥ 0.45** com pelo menos 30 frames,
1 frame com capacete e 1 negativo/sem pessoa. `scripts/ci-smoke.sh` roda esse gate quando o
artefato `ppe-multiclass.pt` está disponível (localmente em `apps/edge-worker/models/` ou,
no GitHub Actions, baixado via secret `CV_MODEL_URL`). Se o modelo estiver presente e o
recall cair abaixo do piso, o job falha.

## Avaliação pública defensável

Para um dataset YOLO com `data.yaml`, use o mesmo pipeline do worker:

```bash
PYTHONPATH=apps/edge-worker/src python3 -m vigia_edge_worker.evaluation_real \
  --dataset /caminho/para/data.yaml \
  --model /models/ppe-multiclass.pt \
  --split test
```

Sem dependências CV no host, rode pelo container do worker:

```bash
docker compose -f infra/compose/docker-compose.dev.yml --profile cv run --rm --no-deps \
  -v "$DATASET_DIR:/external-dataset:ro" \
  --entrypoint python edge-worker -m vigia_edge_worker.evaluation_real \
  --dataset /external-dataset/data.yaml --model /models/ppe-multiclass.pt --split test
```

### Métricas

- `ppe_violation`: frame-level precision/recall/F1/TP/FP/FN/TN usando `no-helmet`/
  `NO-Hardhat` como verdade esperada.
- `restricted_intrusion_proxy`: **apenas proxy de pessoa detectada** com a zona cobrindo
  o frame inteiro; isso **não** é benchmark geométrico de zona anotada.
- contagem de pessoas, contagem de `no-helmet`, latência média/máxima/p95.

### Dataset recomendado

- RF100 / Roboflow `construction-safety-gsnvb` v1 `release-640`
- Mirror Hugging Face: `LibreYOLO/construction-safety-gsnvb`
- Atribuição/licença esperada: **CC-BY-4.0** (cite a fonte ao publicar números)

Texto mínimo de atribuição: "Dataset: Roboflow 100 / Construction Safety
(`construction-safety-gsnvb`), version `release-640`, licensed CC-BY-4.0. Source:
Roboflow Universe / RF100; mirror: `LibreYOLO/construction-safety-gsnvb`."

Resultado medido no split `test` completo do mirror Hugging Face (90 imagens), com o mesmo modelo
`ppe-multiclass.pt` e confiança mínima 0.4:

| Métrica pública | Valor |
|---|---:|
| Precision `ppe_violation` por frame | **1.000** |
| Recall `ppe_violation` por frame | **0.545** |
| F1 `ppe_violation` por frame | **0.706** |
| TP / FP / FN / TN | 6 / 0 / 5 / 79 |
| Pessoas esperadas/detectadas | 214 / 268 |
| `no-helmet` esperado/detectado | 24 / 21 |
| Latência | 399 ms média, 513 ms p95, 580 ms máx |

Leitura honesta: no benchmark público o modelo ainda perde ~45% dos frames com pessoa sem
capacete e superconta pessoas. A precisão ficou alta porque deixamos de inferir zona quando
os pés/base não estão visíveis; o recall ainda precisa melhorar antes de prometer cobertura
autônoma.

## Como ler isso

**Precisão 1.00** = quando o sistema acusa "sem capacete", ele está certo nesta amostra. Não gritou à
toa em nenhum frame. É a métrica que decide se o operador continua confiando no alerta —
produto de segurança que dá alarme falso é desligado na primeira semana.

**Recall 0.50** = ele ainda **perdeu metade dos frames com violação real de capacete**. Para
segurança do trabalho isso é o erro que mais dói: o acidente que o sistema deveria ter
evitado.

Casos concretos: no frame `f05` há duas pessoas sem capacete, o modelo detectou as duas
pessoas e não classificou nenhuma como `NO-Hardhat`; no `f09`, a pessoa está com a base/pés
cortados pelo frame, então o sistema deixa de inferir pertencimento à zona do chão.

**Latência ~353 ms** por frame no container CV local. Com `EDGE_VIDEO_FRAME_STRIDE=15`
sobre 25 fps, dá ~1,6 análises/s — suficiente para o loop atual, mas é o teto por câmera
nesse hardware.

Na avaliação pública, latência é referência operacional; acurácia vem das métricas acima.

## O que este número NÃO diz

Isto é o mais importante desta página. **A amostra agora tem 33 frames**, mas continua
pequena. Serve para exercitar a medição, cobrir falso positivo de capacete e quebrar build
em regressão grosseira; **não é taxa de acerto publicável** e não deve ir para pitch como
"nossa acurácia é X".

Além do tamanho:

- **Dois cenários, ainda estreitos**: fábrica têxtil interna + construção pública. Não cobre
  pátio real de cliente, contraluz, chuva, noite, câmera baixa ou operação externa.
- **Falso positivo de capacete agora é medido**, porque há 24 frames com capacete; ainda é
  pouco para declarar precisão operacional em domínio novo.
- **Frames "sem pessoa" do RF100 não são cena vazia perfeita**: podem conter EPIs anotados
  sem bbox de `person`. Eles servem para alarme fantasma por frame, não para validar todos
  os negativos possíveis.
- **Ground truth por inspeção visual humana**, em nível de frame. Não é bbox anotada, e
  duas pessoas poderiam discordar sobre a pessoa borrada ao fundo.
- **Mede detecção, não geometria.** A zona de EPI cobre o quadro inteiro de propósito:
  misturar detecção e polígono esconderia de qual dos dois veio o erro.
- **Não inferimos zona com pés/base cortados.** Isso reduz falso positivo geométrico, mas
  também derruba recall quando a câmera enquadra trabalhadores pela metade.

## Por que medimos por frame, e não mAP

mAP avalia o **modelo**. Aqui interessa a **decisão do produto**: "este quadro vira
incidente?". É isso que chega ao cliente, e é isso que precisa estar certo. Um modelo com
mAP alto que erra a decisão não serve; um com mAP médio que acerta a decisão serve.

## O que existia antes

`evaluation.py` (o antigo) instanciava o detector **sem** `cv_model_path`, então media o
stub de bytes-marcador — um `grep`. O "dataset" eram arquivos `.txt`. As métricas ~1.0 que
o Sprint 5 registrou mediam isso. Este documento existe porque aquele número não media
visão computacional nenhuma.

## Próximos passos para o número virar defensável

1. **Investigar o `f05` e falsos negativos RF100**: por que a pessoa é detectada e a cabeça não é julgada? Pode ser
   limiar de confiança, tamanho do objeto (cabeça pequena e borrada) ou o domínio do
   dataset de treino (construção) contra o nosso (têxtil).
2. **Adicionar pátio e negativos reais de cliente**: frames vazios de verdade, pessoas com
   outros EPIs, visitantes e fundo industrial sem obra.
3. **Medir geometria de zona separadamente**: este benchmark cobre detecção por frame;
   polígonos no chão precisam de dataset próprio com zona anotada.
4. **Subir o piso de CI conforme o modelo melhorar**: o piso atual é 0.45 porque o modelo
   medido faz 0.50; não é meta final de produto.
