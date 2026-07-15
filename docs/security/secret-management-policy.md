# Política de rotação e proteção de segredos

## Princípios
- Segredo real nunca deve ser colocado em Git, chat, issue, card ou README.
- Segredos reais vivem apenas em `.env` local ignorado ou em secret manager.
- `*.example` e documentação usam apenas placeholders e valores de demonstração.

## Ambientes
- **dev**: pode usar valores `dev-only`/mock para facilitar execução local.
- **staging**: usa segredos próprios, nunca reutilizados de dev.
- **prod**: usa secret manager; não depende de `.env` com segredo real.

## Segredos cobertos
| Segredo | Uso | Rotação normal | Rotação emergencial |
| --- | --- | --- | --- |
| JWT secret | assinar access tokens | periódica | imediata em incidente |
| Session/refresh secret | rotação/revogação de sessão | periódica | imediata em incidente |
| Cookie/CSRF secret | proteção de cookie/CSRF | periódica | imediata |
| DB credentials | acesso ao PostgreSQL | por política do ambiente | imediata |
| Redis credentials | filas/cache | por política do ambiente | imediata |
| MinIO/S3 credentials | evidências e objetos privados | por política do ambiente | imediata |
| SMTP/API keys | notificações e integrações | por política do ambiente | imediata |
| Edge-worker API keys | autenticação técnica da borda | curta e revogável | imediata |

## Secret manager
Em produção, segredos devem vir de um secret manager ou mecanismo equivalente da infraestrutura.
- não expor em logs;
- não versionar em arquivos do repositório;
- não compartilhar o mesmo segredo entre ambientes.

## Rotação e revogação
- rotação planejada deve ser agendada e auditada;
- rotação emergencial ocorre após suspeita de vazamento ou comprometimento;
- JWT/session secrets devem invalidar tokens antigos conforme janela de migração;
- credenciais do edge-worker devem ser revogadas por `client_id`/`worker_id` e reemitidas após confirmação.

## Revogação de edge-worker credentials
Fluxo mínimo:
1. marcar credencial como revogada;
2. impedir novos heartbeats/eventos/upload requests;
3. registrar auditoria da revogação;
4. emitir nova credencial somente se necessário.

## Auditoria mínima
Registrar, no mínimo:
- quem rotacionou/revogou;
- qual segredo/credencial foi afetado;
- ambiente;
- motivo;
- data/hora;
- efeito esperado (expiração, revogação, reemissão).

## Checklist pré-publicação
- confirmar que nenhum segredo real está no Git;
- confirmar que `.env` real está ignorado;
- confirmar que staging/prod usam segredos diferentes;
- confirmar que documentos e cards não contêm segredos;
- confirmar que credenciais antigas foram revogadas quando aplicável.
