# Baseline de volume sintético de incidentes

## Objetivo

Validar que o dashboard e os filtros de triagem continuam utilizáveis com volume inicial de beta, sem usar dados reais, imagens reais ou informações de cliente.

## Runner sintético

Execute localmente:

```bash
PYTHONPATH=apps/api/src python3 -m vigia_api.scripts.seed_synthetic_incidents --count 1000 --days 30
```

Para comparar com PostgreSQL real/local isolado:

```bash
POSTGRES_VOLUME_SMOKE_DATABASE_URL='postgresql+psycopg://user:pass@localhost:5432/vigia' bash scripts/postgres-volume-smoke.sh
```

O runner usa apenas dados fake determinísticos:

- organização `org-demo` por padrão;
- sites, câmeras, zonas e workers sintéticos;
- severidades e status distribuídos;
- alguns registros de evidência metadata-only, sem binários;
- nenhuma pessoa, imagem, RTSP real, segredo ou URL assinada real.

## O que é medido

- primeira página da lista de incidentes;
- filtro por status;
- filtro por severidade;
- filtro por site/câmera/zona;
- filtro por janela recente;
- detalhe de incidente;
- auditoria do incidente;
- evidência metadata-only do incidente.

## Baseline local registrado

Em ambiente de desenvolvimento, 1k incidentes sintéticos é o alvo mínimo para beta. Como referência operacional inicial:

- execução local registrada com `--count 1000 --days 30`: lista primeira página 0.042ms, status aberto 0.150ms, severidade alta 0.050ms, site/câmera/zona 0.066ms, janela de 7 dias 0.086ms, detalhe 0.001ms, auditoria 0.091ms e evidência 0.006ms;
- queries do dashboard devem permanecer abaixo de ~100ms em hardware de desenvolvimento;
- paginação deve continuar limitada ao máximo da API;
- payloads devem carregar apenas a página solicitada no frontend;
- filtros com poucos resultados não devem quebrar seleção/detalhe/evidência.

Se o runner apontar consultas acima desse alvo, investigar antes do beta:

- índice composto `(organization_id, created_at)` para listagem recente;
- índice composto `(organization_id, status, severity)` para triagem;
- índice composto por site/câmera/zona conforme o padrão real do cliente;
- redução de payload ou carregamento sob demanda no dashboard.

## Relação com outros gates

- `bash scripts/validate.sh`: gate rápido obrigatório.
- `npm --workspace apps/web run test:e2e`: valida experiência browser com API mockada.
- `bash scripts/pilot-smoke.sh`: valida fluxo Docker local completo.
- Este runner mede volume sintético local e não substitui staging real.

## Limites

O runner atual usa repositório in-memory para baseline leve. Antes de cliente beta, repetir validação em staging/PostgreSQL com dados sintéticos aprovados e comparar latência real de API, banco e frontend.

O runner PostgreSQL cria as tabelas se necessário, prepara um catálogo sintético mínimo (`org-demo`, sites, câmeras e zonas fake) e mede os mesmos caminhos de listagem/filtros/detalhe/auditoria/evidência com 1k+ incidentes sintéticos. Se houver regressão, os primeiros candidatos são índices por `organization_id + created_at`, `organization_id + status + severity` e os filtros mais usados pelo cliente.
