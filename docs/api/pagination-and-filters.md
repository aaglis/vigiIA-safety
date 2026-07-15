# Paginação e filtros da API

Listagens operacionais usam paginação `limit/offset`.

## Padrão

- `limit`: quantidade de itens por página. Padrão `50`; máximo efetivo `100`.
- `offset`: deslocamento inicial. Padrão `0`.
- Resposta:

```json
{
  "items": [],
  "page_info": {
    "limit": 50,
    "offset": 0,
    "total": 0,
    "has_next": false
  }
}
```

## Incidentes

`GET /api/v1/organizations/{organization_id}/incidents`

Filtros suportados:

- `status`
- `site_id`
- `camera_id`
- `zone_id`
- `severity`
- `created_from` em ISO 8601
- `created_to` em ISO 8601

Esses filtros alimentam a triagem do dashboard de incidentes e podem ser combinados com paginação `limit/offset`.

## Auditoria de incidente

`GET /api/v1/organizations/{organization_id}/incidents/{incident_id}/audit-log`

Filtros suportados:

- `action`

## Evidências

`GET /api/v1/organizations/{organization_id}/evidence`

Filtros suportados:

- `incident_id`

## Auditoria de evidências

`GET /api/v1/organizations/{organization_id}/evidence/audit-logs`

Filtros suportados:

- `incident_id`
- `file_id`
- `action`

Todos os endpoints continuam isolados por `organization_id`.
