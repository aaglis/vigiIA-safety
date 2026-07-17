# Typing baseline

Snapshot (repo search):
- `Any`: 42 files / 174 hits
- `dict[str, Any]`: 21 files / 66 hits
- `type: ignore`: 29 files / 80 hits

Allowed / inevitable:
- External JSON boundaries
- Free-form metadata blobs
- Sanitized logging helpers
- Third-party runtime stubs / optional imports

Must reduce first:
- Domain contracts
- Container/service wiring
- Serializers / API adapters
- Edge event payloads

Current safe moves in this card:
- Frontend shared JSON / metadata aliases
- One edge-worker payload module narrowed from broad `Any`

Examples to revisit later:
- `apps/api/src/vigia_api/services/*`
- `apps/api/src/vigia_api/api/v1/*`
- `apps/api/src/vigia_api/domain/*`
