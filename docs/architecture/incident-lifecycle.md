# VigIA Safety — Ciclo de vida de incidentes

## Estados

### candidate
- Estado futuro/opcional para pré-triagem interna.
- Não faz parte do ciclo implementado neste card.

### open
- Incidente confirmado e aberto para tratamento.
- Pode receber responsável, prioridade e evidências.

### acknowledged
- Um usuário com permissão reconheceu o incidente e iniciou o atendimento.
- Indica que a operação está ciente do caso.

### resolved
- A condição de risco foi tratada ou eliminada.
- Pode permanecer com evidências e comentários para auditoria.

### dismissed
- O evento foi considerado falso positivo, irrelevante ou fora de escopo.
- Deve manter trilha de auditoria do motivo do descarte.

## Fluxo principal
`open -> acknowledged -> resolved`

## Fluxos alternativos
- `open -> resolved`
- `open -> dismissed`
- `acknowledged -> dismissed`

## Regras de transição
- `open` pode virar `acknowledged`, `resolved` ou `dismissed`.
- `acknowledged` pode virar `resolved` ou `dismissed`.
- `resolved` e `dismissed` são estados terminais.
- `resolved` e `dismissed` exigem justificativa.
- Transições inválidas são rejeitadas pelo backend.

## Observações de negócio
- `candidate` é útil para reduzir ruído e evitar abrir incidente definitivo para todo evento bruto.
- O backend é a fonte de verdade do status final.
- O edge worker apenas propõe/detecta; a decisão de lifecycle pertence à API.
