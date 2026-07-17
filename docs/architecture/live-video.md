# Vídeo ao vivo — topologia

## Decisão

O vídeo vai **do edge direto para o navegador** (WebRTC/WHEP). Ele **nunca passa pelo nosso cloud**.

Motivos:

1. **LGPD.** Imagem de rosto de funcionário é dado pessoal. Se o vídeo não sai da planta, o cliente não precisa nos auditar como operador de imagem — é o nosso argumento de venda contra concorrente que centraliza.
2. **Banda e custo.** Streamar N câmeras × N clientes para o cloud não escala: uma câmera 1080p contínua são ~2 Mbps; 50 câmeras já são 100 Mbps de ingest permanente por cliente.
3. **Latência.** Edge → navegador na mesma LAN é sub-segundo; passar pelo cloud e voltar adiciona RTT desnecessário.

O cloud faz o que só ele pode fazer: **decidir quem vê o quê** (multi-tenant, permissão) e guardar **eventos e evidências** (que são pequenos).

## Componentes

```
   câmera IP ──RTSP──> MediaMTX (edge) ──RTSP──> edge worker (YOLO)
                          │                          │
                          │                          └──detecções──> API (cloud) ──> incidente + evidência
                          │
                          └──WebRTC/WHEP──> navegador do cliente
                                  ↑
                            ticket assinado (60s) emitido pela API
```

- **MediaMTX** roda no edge, ao lado do worker. Componente pronto — não implementamos RTSP→WebRTC na mão.
- **Em dev** não há câmera IP: o stack `infra/compose/docker-compose.cameras.yml` faz esse papel, num compose **separado** do sistema (câmera é equipamento do cliente, não parte do produto). Cada vídeo da pasta vira uma câmera RTSP em loop — ver `docs/development/cameras-dev.md`. Para o resto do sistema é indistinguível de uma câmera real — inclusive o worker, que reconecta com backoff quando o stream cai.
- **Um stream, dois consumidores:** o worker lê por RTSP para rodar a visão computacional e o navegador lê o mesmo path por WebRTC. Nenhum dos dois atrapalha o outro.

## Autorização

Ninguém lê um stream sem passar pela nossa API. O MediaMTX delega toda leitura via `authHTTPAddress` → `POST /api/v1/internal/stream-auth`, e há exatamente dois leitores legítimos:

| Leitor | Como se autentica | Escopo |
|---|---|---|
| Navegador do cliente | Ticket JWT de **60s** na query (`?token=`), emitido por `GET /organizations/{org}/operations/cameras/{id}/live` | Só o path daquela câmera (o claim `path` é comparado com o path pedido) |
| Edge worker | Credencial de máquina (`client_id`/`api_key`) no userinfo da URL RTSP | Só as câmeras em `allowed_camera_ids` do worker |

Consequências desenhadas de propósito:

- **Sem URL pública eterna.** O ticket expira em 60s (`LIVE_STREAM_TICKET_TTL_SECONDS`); depois disso o link não abre mais.
- **Ticket não vaza lateralmente.** Ticket da câmera A não abre a câmera B (validado em `test_ticket_does_not_open_another_camera`).
- **Publish fica fora do gate** (`authHTTPExclude`) porque o publisher é o próprio ffmpeg local do container; nada vindo de fora publica.
- Um ticket de leitura **nunca** vira permissão de publicação.

## Overlay de detecção (as caixas sobre o vídeo)

O vídeo vai direto do edge, mas as **caixas** passam pelo cloud:

```
edge worker ──POST /edge-workers/me/frame-analysis──> API ──WebSocket──> navegador
```

Por que aqui o cloud entra, se no vídeo ele não entra? Porque **bbox não é imagem**: são quatro números normalizados. Não carrega rosto, não pesa (~200 bytes/frame contra ~2 Mbps de vídeo) e, indo pelo cloud, funciona igual quando o cliente acessa de fora da planta — coisa que o vídeo P2P ainda não faz (ver TURN, abaixo).

- O worker publica **todo frame analisado**, não só violação: pessoa em conformidade aparece de verde na tela do cliente.
- O fanout (`services/detection_stream.py`) é **efêmero de propósito**: sem ninguém assistindo, o frame morre ali. O que precisa durar (incidente, evidência) segue pelo pipeline normal para o Postgres.
- Navegador lento **perde frame velho** em vez de segurar a fila — melhor pular quadro do que atrasar o que está na tela.
- O WebSocket usa o **mesmo ticket** do vídeo: um ticket abre a câmera e as caixas dela, nada além.
- Sem análise nova por 3s, o overlay some: melhor nenhuma caixa do que caixa fantasma sobre um vídeo que continua andando.

## Configuração

| Env (API) | Default | Para que serve |
|---|---|---|
| `LIVE_STREAM_PUBLIC_BASE_URL` | `http://localhost:8889` | Base WebRTC do edge que o **navegador** acessa. Em produção, o endereço do MediaMTX na rede do cliente. |
| `LIVE_STREAM_TICKET_TTL_SECONDS` | `60` | Validade do ticket. |

Em dev, `DEMO_CAMERA_STREAM` (default `rtsp://mediamtx:8554/camera-demo-01`) é o stream que o seed grava na câmera demo.

## Como rodar

```bash
cd infra/compose
docker compose --profile cv up -d                     # sistema + edge worker
docker compose -f docker-compose.cameras.yml up -d    # as câmeras (stack separado)
```

Depois, em `localhost:5173` → **Operações/Câmeras** → **Ao vivo** na Câmera Demo 01.

Sem o stack de câmeras no ar, a câmera aparece como offline no player (estado tratado) e o resto do sistema segue funcionando — é uma forma barata de testar o caminho de câmera caída.

## Validação

`apps/web/tests-live/live-stream.spec.ts` roda contra o stack real (sem mock) e só passa se o vídeo **chegar e andar**: exige `videoWidth > 0` e `currentTime` avançando. Resultado medido: **1280×720**, `currentTime` 0.04s → 1.59s.

```bash
cd apps/web && npx playwright test -c playwright.live.config.ts
```

`tests-live/detection-overlay.spec.ts` cobre o overlay e exige o edge worker rodando: só passa se as caixas da CV real chegarem via WebSocket e forem desenhadas sobre o vídeo.

## Limitações conhecidas

- **Sem TURN.** `webrtcICEServers2` está vazio: funciona quando navegador e edge se enxergam (mesma LAN, ou VPN). Cliente acessando de fora da planta precisa de TURN ou de um túnel — decisão adiada até existir um cliente com essa topologia.
- **Fanout do overlay é em memória**, então vale para **uma instância** de API. Com mais de uma atrás de um load balancer, o navegador conectado na instância A não recebe o que o worker publicou na B. Resolve com Redis pub/sub (o Redis já está no compose) quando houver segunda instância.
- **O overlay depende do stride do worker** (`EDGE_VIDEO_FRAME_STRIDE`): as caixas atualizam ~1.6×/s enquanto o vídeo roda a 25 fps, então elas "seguem" a pessoa com um passo perceptível. Suavizado por transição CSS de 220ms.
- **Provisionamento**: em dev, qualquer vídeo da pasta vira câmera (path por regex). Em produção, provisionar o MediaMTX a partir do cadastro de câmeras da API continua sendo trabalho futuro.
- **A porta 8554 (RTSP) está exposta no compose** por conveniência de debug. Em produção ela não deve sair da LAN do edge.
