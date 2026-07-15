# apps/web

Frontend do VigIA Safety.

## Stack
- React
- Vite
- TypeScript
- Tailwind CSS

## Responsabilidade
- autenticação e sessão do usuário humano;
- dashboard operacional;
- consumo da API via HTTP.

## Configuração
- `VITE_API_BASE_URL` — base da API (padrão: `/api/v1`)

## Login demo
- e-mail: `admin@vigia.local`
- senha: `change-me-dev`
- Se a API não responder, o frontend ativa automaticamente o modo de demonstração local.

## Triagem de evidência
- Ao abrir um incidente, o painel carrega incidente, auditoria e evidências visuais.
- A evidência só recebe URL assinada quando o usuário clica em "Abrir evidência segura".
- Se não houver snapshot/clip, o painel mostra estado vazio sem quebrar a triagem.
- Fluxo demo: `inc-demo-1` tem snapshot visual, `inc-demo-2` mostra vídeo/metadado, `inc-demo-3` não tem evidência.

## Skeleton
- Entrypoints em `src/`
- Landing, login e dashboard conectável em `src/App.tsx`
- Client HTTP central em `src/api/client.ts`
- Auth em `src/api/auth.ts`
- Tipos e operações de incidentes em `src/api/incidents.ts`

## Dev commands
- `npm install`
- `npm run dev`
- `npm run build`
- `npm run lint` (futuro)

## Docker/demo local
- Servido em `http://localhost:5173`.
- Conecta na API via `VITE_API_BASE_URL=http://localhost:8000/api/v1`.
- Se a API estiver indisponível, a UI cai em modo demo local.

> Dependências ainda não estão instaladas neste repositório.
