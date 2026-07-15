# Edge worker — visão geral

## Responsabilidade
O edge worker executa captura local, inferência e envio de eventos para a API central.

## Integração
- Autentica com credencial técnica própria.
- Envia `DetectionEvent v1` e `EdgeHeartbeat v1`.
- Solicita configuração, uploads e permissões via API HTTP.
- O detector é selecionável via `CV_MODE=mock|real`.
- `mock` permanece determinístico para testes e demo.
- `real` é um adapter inicial leve, baseado em frame local/bytes e marcador explícito.

## Detector selecionável
- `CV_MODE=mock` é o padrão seguro para Compose/dev e testes rápidos.
- `CV_MODE=real` ativa o adapter real inicial, mas exige `CV_REAL_ENABLED=1`.
- `CV_REAL_MARKER` define o marcador textual esperado nos bytes do frame local usado pelo adapter inicial.
- `CV_REAL_MODEL_VERSION` identifica a versão do adapter/modelo reportada no evento.
- Se `CV_MODE=real` não tiver frame/bytes ou marcador configurado, o worker falha explicitamente em vez de emitir detecção falsa como real.

## Captura de frames
- `EDGE_SOURCE_TYPE=mock|image|video|rtsp` escolhe a origem do frame.
- `EDGE_SOURCE_URI` aponta para arquivo ou diretório local; `image` lê um arquivo, `video` itera arquivos do diretório como frames.
- `EDGE_FRAME_INTERVAL_SECONDS` controla a cadência do loop.
- `EDGE_MAX_FRAMES` limita a execução em smoke/testes e encerra o loop de forma limpa.
- `rtsp` é experimental e falha explicitamente neste card; a implementação local atual usa apenas fontes locais sem depender de OpenCV.

## Regras operacionais no edge
- a API de config retorna `site_id`, `allowed_camera_ids`, `zones`, `safety_rules` e `required_ppe` do tenant;
- o worker usa isso para rotular severidade/summary/event_type e validar escopo da câmera;
- `EDGE_DETECTION_COOLDOWN_SECONDS` reduz spam por `(camera_id, zone_id, event_type)`;
- o MVP não faz interpretação geométrica de polígonos nem fusão multi-câmera.

## Buffer offline
- `EDGE_BUFFER_PATH` ativa spool local de detecções pendentes;
- o buffer armazena `pending/`, `sent/` e `failed/` em arquivos JSON por `event_id`;
- `EDGE_BUFFER_MAX_ATTEMPTS` e `EDGE_BUFFER_BACKOFF_SECONDS` controlam retry simples;
- o objetivo atual é evitar perda em falhas HTTP transitórias; upload binário de mídia ainda não é parte deste card.

## Telemetria operacional
- o heartbeat inclui `worker_version`, `cv_mode`, `source_type`, contadores e `pending_queue` dentro de `status`;
- `last_error` é sanitizado e truncado;
- logs estruturados incluem `request_id/correlation_id`, `camera_id`, `site_id`, `organization_id`, latência e resultado;
- diagnóstico local: `python -m vigia_edge_worker.main --diagnose`.
- para câmera sem frame: verificar `EDGE_SOURCE_TYPE`/`EDGE_SOURCE_URI` e o erro sanitizado no heartbeat;
- API fora: buffer offline permanece ativo e o diagnóstico mostra `pending_queue`;
- modelo indisponível: `CV_MODE=real` exige `CV_REAL_ENABLED=1` e marcador/bytes válidos.

## Dataset e validação da visão computacional
- dataset mínimo versionado: `apps/edge-worker/datasets/cv-mini/v1/`;
- contém apenas texto/bytes sintéticos, sem imagens reais nem PII;
- runner: `python -m vigia_edge_worker.evaluation --dataset apps/edge-worker/datasets/cv-mini/v1 --format json|markdown`;
- métricas iniciais: `tp`, `fp`, `fn`, `tn`, `precision`, `recall`, `average_latency_ms`;
- critérios beta/demo modestos: precisão e recall próximos de 1.0 no dataset sintético, latência baixa e sem false positives no conjunto mínimo.

### Como adicionar novos exemplos
- usar arquivos pequenos `*.txt` ou `*.bin` com conteúdo sintético;
- atualizar `manifest.json` com `expected_detection`, `marker` e notas;
- não versionar imagens reais ou qualquer material identificável/sensível;
- se houver vídeo/imagem real para teste, manter fora do repo e referenciar apenas localmente em ambientes controlados.

Exemplo local controlado:

```bash
CV_MODE=real CV_REAL_ENABLED=1 CV_REAL_MARKER=helmet CV_REAL_MODEL_VERSION=real-cv-0 \
EDGE_SOURCE_TYPE=image EDGE_SOURCE_URI=/tmp/frame.jpg \
EDGE_RUN_ONCE=true EDGE_API_BASE_URL=http://localhost:8000/api/v1 \
EDGE_CLIENT_ID=dev-client-id EDGE_API_KEY=dev-api-key \
python -m vigia_edge_worker.main --once --send-api
```

## Evidências
- O worker não deve acessar evidência de outras organizações.
- Uploads precisam respeitar o escopo do tenant e do incidente.
- A plataforma central decide retenção, auditoria e URLs assinadas.
- Quando a API devolver `upload_url`, o worker faz `PUT` com os bytes do frame; se falhar, o incidente segue normalmente e o status da evidência marca `failed`.
- Se a API devolver apenas `upload_path`, o worker registra referência e segue sem bloquear o incidente.
- O upload binário usa somente a URL assinada; não reenviar headers `X-Edge-*` para o storage.
- Se `frame.image_bytes` estiver vazio, o worker não tenta upload binário e apenas envia a evidência textual.
- Limite prático: snapshot do frame atual; para anexos maiores ou históricos, usar o fluxo manual de upload no dashboard.
- Troubleshooting: conferir `upload_error` sanitizado no log e a conectividade com o bucket privado.

## Triagem no dashboard
- O dashboard carrega o incidente e, em seguida, lista as evidências do mesmo `incident_id`.
- A URL assinada só é solicitada quando o supervisor clica em "Abrir evidência segura".
- O visor de triagem mostra confiança, modelo, câmera, zona, site e timestamp ao lado do frame.
- Em demo local, o painel exibe snapshot sintético para o primeiro alerta, um clipe/metadado para o segundo e estado vazio para o terceiro.

## Split futuro
O worker foi desenhado para virar deploy e repositório separado.
Para isso:
- manter dependência apenas de contratos;
- evitar imports da API;
- manter endpoints estáveis e versionados;
- tratar a borda como cliente técnico da plataforma.

## Não objetivos do MVP
- UI local do worker.
- Banco local do worker.
- Integração direta com implementação interna da API.
- Pipeline completo de captura contínua de vídeo (fica para o próximo card).
