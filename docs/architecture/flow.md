# VigIA Safety — Fluxo principal

## Fluxo textual

```text
1. Operador entra na área monitorada.
2. O edge-worker captura o stream da câmera local.
3. O modelo de CV detecta pessoa/violação e gera um evento de detecção.
4. O edge-worker envia o evento para a API da organização.
5. A API valida autenticidade, tenant, schema e regras mínimas.
6. Se válido, a API cria ou atualiza o incidente e registra auditoria.
7. A API grava metadados no PostgreSQL e referencia evidências no MinIO/S3.
8. O worker de eventos/notificações processa o incidente e dispara alertas.
9. O frontend exibe incidente, evidência assinada e status de tratativa.
10. O supervisor acompanha, conclui a ocorrência e gera histórico/auditoria.
```

## Diagrama simples

```text
[Câmera/RTSP]
      |
      v
[Edge Worker CV] ---> [Eventos de detecção]
      |                      |
      |                      v
      |                 [API FastAPI]
      |                      |
      |                      v
      +----------------> [PostgreSQL]
                             |
                             v
                       [Worker Notificações]
                             |
                             v
                         [Frontend Web]
```

## Regras do fluxo
- O worker detecta; a API valida e decide.
- Nenhuma evidência deve ficar pública.
- Cada evento/incidente pertence a uma organização.
- Notificações são assíncronas e não bloqueiam a criação do incidente.
