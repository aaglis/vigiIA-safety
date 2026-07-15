# VigIA Safety — Decisões de arquitetura

## 1. Stack oficial
**Decisão:** adotar React + Vite + TypeScript + Tailwind no frontend; FastAPI no backend; Python para o worker de CV; PostgreSQL, Redis e MinIO/S3 como base de dados e storage.

**Motivo:** stack rápida para MVP, boa compatibilidade com o time e adequada para SaaS industrial com processamento assíncrono e evidências.

## 2. FastAPI e não Flask
**Decisão:** usar **FastAPI** como framework oficial da API.

**Motivo:** tipagem com Pydantic, documentação automática, melhor ergonomia para contratos de API, alta produtividade e maior alinhamento com integrações assíncronas.

## 3. Separação entre API e CV worker
**Decisão:** API e worker de visão computacional serão aplicativos separados e deployáveis independentemente.

**Motivo:** desacopla inferência de regras de negócio, facilita escala, mantém a borda operando mesmo com indisponibilidade parcial da nuvem e simplifica evolução futura.

Ver também: [monorepo structure](./monorepo-structure.md) e [app boundaries](./app-boundaries.md).

## 4. Processamento de eventos
**Decisão:** o worker de CV emite eventos de detecção; a API valida esses eventos e cria incidentes/workflows; um worker separado trata notificações e rotinas assíncronas.

**Motivo:** evita acoplamento entre inferência, persistência e comunicação externa.

## 5. Multitenancy
**Decisão:** modelo centralizado multi-tenant com `organization_id` em todas as tabelas operacionais.

**Motivo:** simplifica governança, auditoria e separação de dados sem multiplicar a infraestrutura por cliente.

## 6. Autenticação e sessão
**Decisão:** senha com Argon2id, access token curto em cookie HttpOnly/Secure, refresh token opaco com rotação e proteção CSRF.

**Motivo:** reduz exposição de credenciais e adequa o produto a uso corporativo.

## 7. Evidências
**Decisão:** snapshots e clipes vão para bucket privado em MinIO/S3, acessados por URL assinada e com auditoria.

**Motivo:** atende privacidade, controle de acesso e retenção.

Segredos: ver [secret management policy](../security/secret-management-policy.md).

## 8. Usuários e perfis
**Decisão:** haverá login para plataforma admins, org owners/admins, managers/supervisors e auditor/viewer opcional. Trabalhadores/operários são entidades operacionais sem login no MVP.

**Motivo:** reduz complexidade inicial e reflete o fluxo real de operação.

Ver também: [Users vs Workers](./users-vs-workers.md) e [Employee portal roadmap](../product/employee-portal-roadmap.md).
