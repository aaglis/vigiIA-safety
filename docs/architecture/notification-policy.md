# VigIA Safety — Política de notificações

## Escopo
Esta política define quando notificar, para quem notificar, em quais canais e quando suprimir mensagens.

## Canais
### MVP
- Dashboard/in-app
- E-mail

### Futuro
- WhatsApp (fora do MVP e deste card)

## Destinatários
- Supervisor / operação interna
- Worker externo, somente se a organização habilitar notificações externas

## Template de mensagem — supervisor
Conteúdo mínimo:
- tipo do incidente;
- severidade;
- organização e unidade/câmera;
- horário do evento;
- resumo objetivo;
- link para evidência e ação requerida.

## Template de mensagem — worker externo
Conteúdo mínimo:
- alerta resumido;
- unidade/câmera;
- horário;
- instrução operacional curta;
- referência para contato ou retorno.

Observação: worker externo não usa login web no MVP; o canal externo só pode ser ativado por configuração organizacional explícita.

## Antispam
A plataforma deve impedir excesso de alertas por:
- mesmo tipo de incidente;
- mesma organização;
- mesma câmera/local;
- mesma janela temporal.

## Cooldown
- Após disparo de alerta, nova notificação equivalente deve respeitar uma janela mínima configurável.
- Durante o cooldown, novos eventos podem ser anexados ao incidente existente, mas não disparam alerta repetido.

## Deduplicação
Um alerta é considerado duplicado quando compartilha chaves suficientes para representar o mesmo caso, por exemplo:
- organization_id;
- camera_id / source;
- tipo de detecção;
- janela temporal;
- correlação com incidente aberto.

Deduplicados devem atualizar o incidente e a auditoria, sem reenviar o mesmo aviso.

## Política de envio
- Incidente persistido é pré-requisito para notificação.
- Canal dashboard/in-app é o primeiro destino.
- E-mail é enviado conforme preferência e permissão da organização.
- Falha em um canal não impede os demais.

## Estados e rastreio
- `pending`
- `sent`
- `delivered`
- `seen`
- `acknowledged`
- `failed`
- `suppressed`

## Auditoria obrigatória
- quem recebeu;
- quem viu;
- quem reconheceu;
- quem resolveu;
- quem descartou;
- quando cada evento ocorreu;
- qual canal foi usado;
- qual incidente originou o aviso.
