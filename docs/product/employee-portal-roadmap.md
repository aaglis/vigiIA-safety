# Roadmap do portal do funcionário

## Status
Futuro. Fora da Sprint 1.

## Objetivo
Oferecer uma experiência dedicada para o trabalhador monitorado consultar alertas, evidências permitidas, orientações e confirmações operacionais.

## Quando considerar
O portal deve ser avaliado quando houver:
- necessidade recorrente de autoatendimento do worker;
- contratos que exijam confirmação de alertas;
- fluxos de treinamento/recado operacional;
- demanda por histórico individual com controles LGPD claros.

## Riscos
- ampliação de superfície LGPD;
- confusão entre conta do trabalhador e conta administrativa;
- aumento de suporte e complexidade de UX;
- necessidade de regras rígidas de escopo e auditoria.

## Integração possível sem mudar o MVP
- consumir dados existentes da API;
- mostrar apenas o que for permitido por organização/papel;
- manter `User` e `Worker` como entidades separadas;
- usar notificações externas e convites controlados quando aplicável.

## Não objetivos agora
- login do trabalhador comum;
- substituir o portal administrativo;
- alterar o modelo atual de workers como entidade operacional.
