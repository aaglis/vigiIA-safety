# VigIA Safety — Métricas de validação

## Objetivo
Definir como validar o MVP em operação e em demo.

## Métricas principais
- **Taxa de falso positivo**: proporção de alertas incorretos sobre o total de alertas gerados.
- **Latência**: tempo entre detecção no edge e criação/exibição do incidente no dashboard.
- **Tempo até acknowledgement**: tempo entre abertura do incidente e confirmação pelo responsável.
- **Incidentes por trabalhador**: volume de incidentes normalizado por pessoa monitorada.
- **Incidentes por site**: volume de incidentes por unidade/localidade.
- **Incidentes por setor**: volume de incidentes por área operacional.
- **Taxa de dismissão**: proporção de incidentes descartados em relação ao total.

## Leituras esperadas
- O MVP deve mostrar sinais úteis para ajuste de regras e priorização de áreas críticas.
- As métricas devem ser suficientes para comparar sites, setores e períodos.
- O dashboard deve permitir acompanhar a evolução do fluxo até resolução.

## Uso prático
Essas métricas servem para validar:
1. qualidade da detecção;
2. rapidez de resposta;
3. qualidade da triagem humana;
4. aderência do fluxo operacional.

Para critérios operacionais de beta/piloto, veja [Plano de piloto](./pilot-plan.md).
