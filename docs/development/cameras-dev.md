# Câmeras no ambiente de desenvolvimento

## Ideia

Câmera **não é parte do nosso produto** — é equipamento do cliente. Em produção, a câmera IP publica RTSP e o nosso edge worker consome por URL.

Por isso as câmeras de dev vivem num **compose separado** (`infra/compose/docker-compose.cameras.yml`): elas sobem e descem independentes do sistema, exatamente como câmeras reais, que estão ligadas quer o nosso software esteja rodando ou não.

## Como usar

```bash
cd infra/compose

docker compose --profile cv up -d                        # o sistema (cria a rede vigia-dev)
docker compose -f docker-compose.cameras.yml up -d       # as câmeras
```

Ordem importa: o compose do sistema cria a rede `vigia-dev`; o das câmeras entra nela (é assim que o worker alcança a câmera por hostname, como faria na LAN da planta).

Para desligar só as câmeras (útil para testar câmera offline):

```bash
docker compose -f docker-compose.cameras.yml down
```

## Adicionar uma câmera = soltar um vídeo na pasta

Qualquer `.mp4` em `apps/edge-worker/assets/` **já é uma câmera**, sem editar config nem rebuildar:

| Arquivo | URL para o worker | URL para o navegador |
|---|---|---|
| `patio-sul.mp4` | `rtsp://cameras:8554/cam-patio-sul` | `http://localhost:8889/cam-patio-sul/whep` |
| `sample-ppe.mp4` | `rtsp://cameras:8554/cam-sample-ppe` | `http://localhost:8889/cam-sample-ppe/whep` |

O `mediamtx.yml` do stack de câmeras usa um path com regex — `~^cam-(.+)$` — e passa o `$G1` para o ffmpeg. Ou seja: o nome do arquivo vira o nome da câmera.

Para apontar outra pasta de vídeos:

```bash
CAMERAS_VIDEO_DIR=/caminho/para/meus/videos docker compose -f docker-compose.cameras.yml up -d
```

### O ffmpeg só roda quando alguém assiste

O path usa `runOnDemand` (não `runOnInit`): a câmera que ninguém está assistindo **e** nenhum worker está analisando não gasta CPU. Ela sobe sozinha quando o primeiro leitor chega e desce 30s depois do último sair.

Isso importa num notebook: 5 vídeos na pasta não viram 5 ffmpeg permanentes.

## Cadastrar a câmera no sistema

Pelo dashboard (**Operações → Novo → Nova câmera**), colando a URL — igual em produção:

```
rtsp://cameras:8554/cam-sample-ppe
```

Não existe "modo vídeo de teste" no cadastro: em dev ou em produção, câmera é uma URL ao vivo. O que muda é só quem está do outro lado dela.

O seed já cria três câmeras apontando para vídeos reais:

| Câmera | Vídeo |
|---|---|
| `camera-demo-01` (Planta Demo) | `cam-sample-ppe` |
| `camera-demo-patio-sul-01` (Pátio Sul) | `cam-pexels-262484` |
| `camera-demo-doca-norte-01` (Doca Norte) | `cam-pixabay-13439512` |

Sobrescreva com `DEMO_CAMERA_STREAM`, `DEMO_CAMERA_STREAM_PATIO` e `DEMO_CAMERA_STREAM_DOCA`.

## Desenhar a zona sobre a imagem da câmera

O editor de zona captura um **frame da câmera ao vivo** no próprio navegador (WebRTC → canvas). Funciona em câmera recém-cadastrada, que nunca gerou incidente — que é justamente quando se configura a zona.

Se a câmera estiver offline, ele cai para a última evidência registrada; e se não houver nenhuma, mostra a grade (dá para desenhar às cegas, mas não é o caminho feliz).

O frame **não passa pelo nosso cloud**: é capturado direto do stream do edge, como o vídeo ao vivo. Ver `docs/architecture/live-video.md`.

## Onde arrumar vídeo

Pexels e Pixabay (uso livre). Buscas que rendem: `factory workers`, `construction site`, `warehouse forklift`, `industrial safety`. Prefira clipes com pessoas andando pelo quadro — é o que exercita a detecção de intrusão em zona.

## Limitações conhecidas

- Um vídeo com nome contendo `/` ou caracteres exóticos não vira path válido; use `a-z0-9-`.
- O ffmpeg reescala tudo para 720p (o `sample-ppe.mp4` é 1440p, que só queima CPU do worker e banda do navegador). Câmera de vigilância real raramente entrega mais que isso.
- As câmeras não têm áudio (`-an`): a CV não usa áudio e ele só gastaria banda.
