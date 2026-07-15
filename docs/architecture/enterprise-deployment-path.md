# VigIA Safety — Caminho de implantação enterprise

## Objetivo
Descrever o caminho evolutivo para clientes enterprise do **VigIA Safety** sem alterar o modelo MVP SaaS centralizado.

## Estado atual do MVP
- SaaS centralizado multi-tenant.
- Uma plataforma central atende múltiplas organizações.
- Edge workers operam por organização/site e reportam para a nuvem.
- Usuários e memberships são globais e organizacionais, respectivamente.

## Caminho futuro enterprise
O produto pode evoluir para opções como:
- instância dedicada por cliente;
- deploy on-premise;
- topologia híbrida com controle local maior;
- requisitos específicos de rede, compliance e residência de dados.

## Separação entre MVP e enterprise
- **MVP:** uma plataforma SaaS única com isolamento lógico por tenant.
- **Enterprise futuro:** infraestrutura dedicada, conforme demanda comercial e regulatória.

## Pressupostos para a evolução
- o modelo de domínio já deve carregar `organization_id`;
- os workers devem falar com a API por contratos estáveis;
- eventos devem ser versionados;
- autenticação técnica do edge deve ser independente de login humano.

Segredos e ambientes: [secret management policy](../security/secret-management-policy.md) e [environment separation](../security/environment-separation.md).

## Possível direção arquitetural futura
- control plane central com tenants dedicados;
- edge workers locais com sincronização assíncrona;
- opções de segregação por cliente em rede, storage e banco;
- políticas de retenção configuráveis por contrato.

## Diagrama textual da transição
```text
MVP atual
  [Edge workers org/site] -> [SaaS central multi-tenant] -> [DB compartilhado com organization_id]

Futuro enterprise
  [Edge workers local] -> [Instância dedicada do cliente] -> [Recursos isolados por contrato]
```

## Limites do escopo atual
- não implementar deploy dedicado no MVP;
- não tratar on-prem como requisito de primeira versão;
- não fragmentar o produto em instalações por cliente agora.
