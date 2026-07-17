# Pesos do modelo de visão computacional (dev)

O worker carrega o modelo YOLO indicado por `CV_MODEL_PATH`.

- Padrão do compose: `yolov8n.pt` (COCO) — o Ultralytics baixa na 1ª execução e detecta
  `person`, cobrindo **intrusão em zona restrita** (mas **não** capacete).
- Para **EPI (capacete)**: `ppe-hardhat.pt` — YOLOv8n de hard hat, classes `Hardhat` /
  `NO-Hardhat`, que o worker mapeia para `helmet` / `no_helmet`. Validado: detecta a
  cabeça sem capacete e gera `ppe_violation` real.

      curl -L -o ppe-hardhat.pt \
        https://huggingface.co/keremberke/yolov8n-hard-hat-detection/resolve/main/best.pt

  Depois aponte no `infra/compose/.env`: `CV_MODEL_PATH=/models/ppe-hardhat.pt`

## Escolha do modelo (importante)

Nenhum dos dois cobre os **dois** cenários sozinho:

| Modelo | `person` (intrusão) | capacete (EPI) |
|---|---|---|
| `yolov8n.pt` (COCO) | ✅ | ❌ |
| `ppe-hardhat.pt` | ❌ | ✅ |

Para os dois ao mesmo tempo, é preciso um modelo multi-classe de construção/PPE (classes
`Person` + `Hardhat` + `NO-Hardhat`, ex.: datasets SH17 / Construction Site Safety) ou rodar
dois workers, um por cenário. Fica como próximo passo.

Licença: verifique a licença do modelo no repositório de origem antes de uso comercial.

Os pesos não são versionados.
