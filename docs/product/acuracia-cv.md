# Acurácia da visão computacional — o que medimos e o que ainda não sabemos

## O número (17/07/2026)

Modelo `ppe-multiclass.pt`, dataset `cv-real/v1`, confiança mínima 0.4:

| Métrica | Valor |
|---|---|
| Precisão (EPI, por frame) | **1.00** |
| Recall (EPI, por frame) | **0.67** |
| F1 | **0.80** |
| Pessoas detectadas | 4 de 5 |
| Latência de inferência | **493 ms** (média), 813 ms (máx) |

Reproduzir:

```bash
docker compose --profile cv run --rm --no-deps \
  -v "$PWD/../../apps/edge-worker/datasets:/datasets:ro" \
  --entrypoint python edge-worker -m vigia_edge_worker.evaluation_real \
  --dataset /datasets/cv-real/v1/manifest.json --model /models/ppe-multiclass.pt
```

## Como ler isso

**Precisão 1.00** = quando o sistema acusa "sem capacete", ele está certo. Não gritou à
toa em nenhum frame. É a métrica que decide se o operador continua confiando no alerta —
produto de segurança que dá alarme falso é desligado na primeira semana.

**Recall 0.67** = ele **perdeu 1 violação real de 3**. Uma pessoa sem capacete passou sem
ser vista. Para segurança do trabalho isso é o erro que mais dói: o acidente que o sistema
deveria ter evitado.

O caso concreto: no frame `f05` há duas pessoas sem capacete, o modelo **detectou as duas
pessoas** e não classificou nenhuma como `NO-Hardhat`. Ou seja: viu a pessoa, não julgou a
cabeça.

**Latência 493 ms** por frame na CPU do notebook. Com `EDGE_VIDEO_FRAME_STRIDE=15` sobre
25 fps, dá ~1,6 análises/s — suficiente para o loop atual, mas é o teto por câmera nesse
hardware.

## O que este número NÃO diz

Isto é o mais importante desta página. **A amostra tem 3 frames.** Serve para exercitar a
medição e pegar regressão grosseira; **não é taxa de acerto publicável** e não deve ir
para pitch como "nossa acurácia é X".

Além do tamanho:

- **Uma câmera, um cenário**: fábrica têxtil, luz artificial, câmera alta entre
  prateleiras. Não cobre obra, pátio, contraluz, chuva, noite.
- **Nenhuma pessoa COM capacete no material.** Então o número **não mede** o erro mais
  constrangedor: acusar quem está usando o EPI. Precisão 1.00 aqui não prova ausência
  desse falso positivo — prova que não inventou violação onde não há gente.
- **Ground truth por inspeção visual humana**, em nível de frame. Não é bbox anotada, e
  duas pessoas poderiam discordar sobre a pessoa borrada ao fundo.
- **Mede detecção, não geometria.** A zona de EPI cobre o quadro inteiro de propósito:
  misturar detecção e polígono esconderia de qual dos dois veio o erro.

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

1. **Ampliar o dataset**: dezenas de frames, mais de uma câmera/cenário, e — obrigatório —
   pessoas **com** capacete, para medir o falso positivo que hoje não conseguimos ver.
2. **Investigar o `f05`**: por que a pessoa é detectada e a cabeça não é julgada? Pode ser
   limiar de confiança, tamanho do objeto (cabeça pequena e borrada) ou o domínio do
   dataset de treino (construção) contra o nosso (têxtil).
3. **Medir por cenário**: intrusão e EPI têm custos de erro diferentes e merecem números
   separados.
4. **Rodar no CI** com um piso mínimo, para regressão de modelo quebrar o build.
