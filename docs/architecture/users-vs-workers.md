# Users vs Workers

## Objetivo
Separar formalmente quem acessa o sistema de quem é monitorado pelo sistema.

## Definições
### User
`User` é a identidade humana que acessa o VigIA Safety.
- autentica com e-mail/senha;
- pode ter session/tokens;
- participa de organizações por membership;
- possui papéis como `org_owner`, `org_admin`, `manager` e `auditor/viewer` opcional.

### Worker
`Worker` é a pessoa operacional monitorada no domínio.
- não é conta de login no MVP;
- não possui senha, sessão ou token próprio;
- pertence a uma organização;
- pode ser vinculada a site, setor, turno e função.

## Atributos do Worker
Campos de negócio esperados:
- nome;
- matrícula/identificação interna;
- setor;
- turno;
- função;
- contato opcional;
- requisitos de EPI;
- status operacional.

## Notificações
Notificações para worker, quando existirem, são externas ao login:
- WhatsApp;
- SMS;
- e-mail;
- painel futuro do funcionário.

Isso não cria sessão de usuário no MVP.

## Portal do funcionário
Portal/app do funcionário é um módulo futuro.
- não faz parte da Sprint 1;
- não altera o modelo atual de `User`;
- pode ser integrado depois sem quebrar o contrato de domínio.

## Regra de ouro
Se alguém precisa entrar no sistema, é `User`.
Se alguém é monitorado pelo sistema, é `Worker`.
