# Pesos do modelo de visão computacional (dev)

O worker carrega o modelo YOLO indicado por `CV_MODEL_PATH`. Os pesos **não são
versionados** (`.gitignore`) — baixe conforme abaixo.

## Manifest de supply-chain

Antes de carregar o YOLO, o worker valida o `.pt` contra `apps/edge-worker/models/manifest.json`
(montado em `/models/manifest.json` no container). Cada entrada precisa bater em
`filename`, `version` e `sha256`.

- `CV_MODEL_MANIFEST_PATH` pode apontar para outro manifesto; se vazio, o worker usa
  `<CV_MODEL_PATH>/../manifest.json`.
- Se o arquivo sumir, o nome não existir no manifesto ou o SHA256 divergir, o worker
  falha antes de importar/carregar `ultralytics.YOLO`.
- Para atualizar um modelo, baixe o `.pt`, calcule `sha256sum`, atualize o manifesto e
  só então altere `CV_MODEL_PATH`/`CV_REAL_MODEL_VERSION`.

## Padrão do compose: `ppe-multiclass.pt`

```bash
curl -L -o apps/edge-worker/models/ppe-multiclass.pt \
  https://huggingface.co/Hansung-Cho/yolov8-ppe-detection/resolve/main/best.pt
```

Classes: `Hardhat`, `Mask`, `NO-Hardhat`, `NO-Mask`, `NO-Safety Vest`, `Person`,
`Safety Cone`, `Safety Vest`, `machinery`, `vehicle`.

Cobre **os dois cenários numa inferência só**: `Person` → intrusão em zona restrita,
`NO-Hardhat`/`Hardhat` → EPI capacete. Licença do metadata local: **AGPL-3.0**
(verifique a licença do repositório de origem antes de uso comercial).

O `_category_for` mapeia por substring, então `Person`/`Hardhat`/`NO-Hardhat` são
reconhecidos sem mudar código; as demais classes são ignoradas.

## Validação segura do contrato do modelo

Sem carregar `torch`, `ultralytics` ou `cv2`, você pode validar o contrato do `.pt`:

```bash
PYTHONPATH=apps/edge-worker/src python3 -m vigia_edge_worker.model_contract \
  apps/edge-worker/models/ppe-multiclass.pt
```

O comando inspeciona o zip/pickle como bytes, extrai strings e confirma se o arquivo
cobre `person`, `helmet` e `no_helmet` no contrato de produto.

Saída: JSON com `classes`, `categories`, `supports_restricted_intrusion`,
`supports_ppe_helmet`, `supports_product_contract`, `license` e `warnings`.

Exit code `0` = contrato ok; `1` = arquivo inválido ou falta classe/categoria.

## Por que um modelo só importa

| Modelo | `person` (intrusão) | capacete (EPI) |
|---|---|---|
| `yolov8n.pt` (COCO) | sim | **não** |
| `ppe-hardhat.pt` | **não** | sim |
| `ppe-multiclass.pt` | sim | sim |

Com um modelo que **não enxerga capacete**, a zona de EPI não é avaliada — o worker
sinaliza `inactive_rules` no heartbeat em vez de acusar todo mundo de estar sem capacete
(era o comportamento antigo: falso positivo de 100%).

## Segurança: `.pt` é um pickle, e pickle executa código

Carregar um `.pt` de origem desconhecida é **execução de código arbitrário**. Antes de
usar qualquer modelo novo:

1. **Inspecione os opcodes sem carregar** — `pickletools.dis` desmonta o bytecode e mostra
   tudo que o arquivo tenta importar:

   ```python
   import zipfile, pickletools, io
   with zipfile.ZipFile('modelo.pt') as z:
       pickletools.dis(z.read('best/data.pkl'), out=io.StringIO())
   ```

   Um YOLO legítimo importa só `torch.*`, `ultralytics.*`, `collections.OrderedDict` e
   `set`. **Qualquer** referência a `os`, `subprocess`, `builtins.eval`, `socket`,
   `base64` etc. é motivo para descartar o arquivo.

2. **Carregue com allowlist explícita** (`torch.serialization.add_safe_globals` +
   `weights_only=True`): o torch recusa o arquivo se ele pedir algo fora da lista.

3. **Para inferência real, instale `.[cv]` ou rode o container**. No host sem essas
   dependências, a validação fica limitada ao contrato estático acima.

4. **Carregue primeiro dentro do container**, nunca direto na máquina do dev — `/models`
   é montado read-only.

O `ppe-multiclass.pt` foi validado pelo contrato estático; a inferência real ainda
depende do ambiente com `.[cv]`/container.

## Outros modelos

- `yolov8n.pt` (COCO): baixado pelo Ultralytics na 1ª execução. Só `person` — serve para
  intrusão, deixa o EPI inativo.
- `ppe-hardhat.pt`: YOLOv8n de hard hat (`Hardhat`/`NO-Hardhat`), sem `person`.
  `curl -L -o ppe-hardhat.pt https://huggingface.co/keremberke/yolov8n-hard-hat-detection/resolve/main/best.pt`

Verifique a licença do modelo **e do dataset de origem** antes de uso comercial.
