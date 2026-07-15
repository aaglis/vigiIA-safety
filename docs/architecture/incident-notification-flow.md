# VigIA Safety — Fluxo de incidente e notificações

## Objetivo
Definir quando um `DetectionEvent` vira incidente, como o incidente dispara notificações e como o ciclo operacional é auditado.

## Princípio central
- O edge worker apenas detecta e publica `DetectionEvent`.
- A API valida, decide e persiste primeiro.
- Notificações são consequência assíncrona da persistência do incidente.

## Quando detecção vira incidente
Uma detecção vira incidente quando a API confirma, no mínimo:
1. autenticidade do evento;
2. tenant/organização válido;
3. schema e assinatura/contexto mínimos válidos;
4. regra de negócio que caracteriza risco operacional;
5. ausência de bloqueio por antispam/deduplicação.

### Regra prática
- `DetectionEvent` com confiança baixa ou contexto insuficiente pode permanecer como candidato interno.
- Quando a política aprovar, a API cria o incidente e registra o `source_event_id`.
- Se o mesmo caso já estiver aberto, a API deve anexar o evento ao incidente existente em vez de criar um novo.

## Fluxo operacional
1. O worker publica `DetectionEvent`.
2. A API valida e normaliza o evento.
3. A API decide: criar incidente, anexar a incidente existente ou descartar.
4. Se criar, grava no banco e emite rastros de auditoria.
5. O serviço de notificação consome o incidente criado.
6. A plataforma envia notificações para dashboard/in-app e, quando permitido, e-mail.
7. Ações do usuário atualizam entrega, visualização, reconhecimento e encerramento.

## Estados do incidente
- `candidate`: detecção validada parcialmente, ainda sem abertura operacional.
- `open`: incidente persistido e notificado.
- `acknowledged`: alguém assumiu o caso.
- `resolved`: o caso foi tratado.
- `dismissed`: o caso foi descartado com justificativa.

## Estados de notificação
- `pending`: pronta para envio.
- `sent`: enviada ao canal.
- `delivered`: recebida pelo canal/integração, quando suportado.
- `seen`: vista no dashboard/app.
- `acknowledged`: reconhecida pelo destinatário.
- `failed`: falha no envio.
- `suppressed`: bloqueada por antispam, cooldown ou deduplicação.

## Trilhas de auditoria
Devem ser registrados, com usuário, canal e timestamp:
- visualização (`seen`/`viewed`);
- reconhecimento (`acknowledged`);
- resolução (`resolved`);
- descarte (`dismissed`).

## Canais iniciais
- Dashboard/in-app.
- E-mail.

## Canal futuro
- WhatsApp: fora de escopo do MVP e deste card.

## Regras de mensagem
- Supervisor: foco em severidade, local, timestamp, evidência e ação esperada.
- Worker externo: permitido apenas quando a organização habilitar notificação externa e o worker não depender de login web.

## Resumo do contrato
- Persistência sempre antes do disparo.
- Notificação não pode gerar incidente duplicado.
- Antispam, cooldown e deduplicação são aplicados por organização, tipo de evento e janela temporal.
- Toda mudança relevante precisa ficar auditada.
