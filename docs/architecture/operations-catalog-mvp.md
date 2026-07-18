# Catálogo operacional MVP

O catálogo operacional persistente descreve o contexto físico usado por edge workers, incidentes e evidências.

## Entidades persistidas

- `sites`: unidades/plantas dentro de uma organização.
- `cameras`: câmeras vinculadas a um site.
- `zones`: áreas monitoradas por câmera/site, com geometria simplificada em JSON.
- `workers`: trabalhadores/operadores monitorados, sem login no MVP.
- `safety_rules`: regras operacionais por organização, site ou zona.
- `required_ppe`: EPIs exigidos por regra.

Todas as entidades carregam `organization_id`; relações entre site, câmera, zona, trabalhador e regra devem pertencer ao mesmo tenant.

## Limites do MVP

- Não há streaming ao vivo nem gestão avançada de RTSP no catálogo; `stream_identifier` é apenas referência operacional.
- `polygon_json` é armazenado como JSON sem validação geométrica avançada.
- Workers continuam entidades operacionais, não usuários autenticáveis.
- Regras e EPIs são suficientes para seed/demo e validação de incidentes; motor avançado de regras fica para etapa futura.
- O seed local cria `site-demo`, `camera-demo-01`, `zone-demo-01`, `worker-demo-01` e regra/PPE mínimos de forma idempotente.

## Semântica de zonas e geometria

- Polígonos de `zones` são **coordenadas 2D da imagem**; eles não representam volume 3D.
- A zona deve ser desenhada sobre a área do chão/solo visível no frame.
- A avaliação de pertencimento usa o **centro da base do bbox** (pés/base), não o centro geométrico do corpo.
- Se os pés/base estão cortados ou fora do frame, o sistema **não deve inferir** que a pessoa está dentro da zona.
- Retângulos de porta, parede ou fachada podem ser ambíguos em vídeo; prefira áreas do piso claramente visíveis.
- Falhas conhecidas: pés ocluídos por objeto/pessoa, pés recortados pela borda inferior do frame.
- Mitigações futuras: homografia/calibração da câmera, keypoints de pose, melhor posicionamento da câmera e zonas mais alinhadas ao plano do chão.

## Runtime

- `REPOSITORY_BACKEND=memory`: usa repositório in-memory para testes rápidos.
- `REPOSITORY_BACKEND=postgres`: usa PostgreSQL/SQLAlchemy como fonte de verdade do catálogo.

## Painel de configuração operacional

O dashboard expõe uma seção protegida de **Configuração operacional** para o tenant ativo. Ela é leitura no MVP e usa o catálogo persistente para revisar:

- `site_id`, nome, endereço e status de cada site.
- `camera_id`, `site_id`, nome, `stream_identifier` e status das câmeras.
- `zone_id`, `camera_id`, `site_id`, tipo de zona e status.
- regras de segurança e EPIs exigidos associados a site/zona.

Esses IDs são os mesmos usados na configuração do edge worker. Antes de um piloto, o operador deve confirmar que o worker recebeu `site_id`, `camera_id` e `zone_id` existentes e ativos no mesmo tenant.

Endpoints HTTP de leitura:

- `GET /api/v1/organizations/{organization_id}/operations/catalog`
- `GET /api/v1/organizations/{organization_id}/operations/sites`
- `GET /api/v1/organizations/{organization_id}/operations/cameras`
- `GET /api/v1/organizations/{organization_id}/operations/zones`
- `GET /api/v1/organizations/{organization_id}/operations/safety-rules`
- `GET /api/v1/organizations/{organization_id}/operations/required-ppe`

Todos exigem membership no `organization_id` solicitado e permissão de visualização do dashboard. Endpoints de edição seguem fora do MVP; criação/ajuste continua por seed, serviço interno ou ferramenta administrativa controlada.
