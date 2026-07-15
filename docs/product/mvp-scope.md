# VigIA Safety — Escopo do MVP

## Objetivo do MVP
Validar o ciclo principal de valor do VigIA Safety com foco em segurança industrial: detecção de risco em zonas críticas e uso de EPI básico.

## Classes de detecção iniciais
- Pessoas em zona de risco
- Capacete
- Colete de segurança

## O que entra no MVP
- Cadastro mínimo de organização, áreas e regras básicas
- Recebimento de detecção do edge-worker mock/skeleton
- Geração de evento de detecção e criação de incidente
- Dashboard com lista e detalhe do incidente
- Ação de **acknowledgement** e resolução do incidente
- Trilha de auditoria do ciclo completo
- Worker monitorado continua sem login no MVP; ver [Users vs Workers](../architecture/users-vs-workers.md).

## Demonstração principal
Fluxo esperado da demo:
1. Câmera, vídeo ou trabalhador mock gera uma detecção.
2. O sistema cria um incidente.
3. O incidente aparece no dashboard.
4. O supervisor faz acknowledgement.
5. O incidente é resolvido.
6. O log de auditoria registra a sequência.

## Critério de sucesso do MVP
O MVP está validado quando o time consegue demonstrar o fluxo completo acima com latência aceitável, baixa taxa de falso positivo e rastreabilidade de ponta a ponta.

Para exposição a cliente/piloto, use também o plano de go/no-go em [Plano de piloto](./pilot-plan.md).

## Premissas atuais
- Já existe skeleton de implementação.
- Já existe edge-worker mock.
- Já existe slice de incidentes em memória na API.
- Já existe dashboard mock.
