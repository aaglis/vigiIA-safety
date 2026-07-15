# Política de acesso e auditoria de evidências

## Princípio
O acesso a metadados operacionais é diferente do acesso a imagens e clipes. Evidências exigem permissões separadas e auditoria completa.

Política consolidada: [LGPD, auditoria e retenção](./lgpd-audit-retention-policy.md).

## Separação de acesso
- **Metadados**: podem ser consultados por perfis operacionais autorizados.
- **Imagens/clipes**: acesso restrito a perfis com permissão específica.
- O acesso a evidências não deve ser presumido pelo acesso aos metadados.

## Regras de segurança
- Evidências ficam em storage privado.
- Downloads e visualização usam URLs assinadas com expiração curta.
- Tudo deve ser filtrado por `organization_id`.
- Acesso deve respeitar função, contexto e necessidade.

## Auditoria obrigatória
Registrar, no mínimo:
- quem acessou;
- quando acessou;
- qual evidência foi acessada;
- qual ação foi feita (visualizar, baixar, compartilhar interno);
- organização e contexto do acesso.

## Eventos de auditoria recomendados
- criação de upload URL de evidência;
- visualização de imagem;
- abertura de clipe;
- download de evidência;
- atualização de política de retenção;
- expurgo em modo dry-run;
- expurgo confirmado;
- expiração/revogação de URL assinada;
- tentativa negada de acesso.

## Critério de conformidade interna
Se não houver trilha de auditoria, o acesso a evidência não é considerado válido para operação sensível.
