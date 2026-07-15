# VigIA Safety — Riscos críticos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Falso positivo alto | Alarme excessivo, perda de confiança | Persistência por N frames, tracking, calibração por site e medição de FP no piloto |
| Qualidade variável das câmeras | Queda de precisão | Regras mínimas de instalação, checklist de onboarding e calibração por ambiente |
| EPI pequeno ou ocluso | Baixa detecção em classes difíceis | Priorizar capacete/colete no MVP; ampliar classes depois; exigir câmera mais próxima quando necessário |
| Vazamento de dados/evidências | Risco legal e reputacional | Bucket privado, URL assinada, RBAC, auditoria e retenção controlada |
| Incidente criado por evento inválido | Workflow incorreto | API valida schema, origem e contexto antes de persistir incidente |
| Latência de processamento | Atraso na resposta | Processamento no edge e envio apenas de eventos/metadados |
| Dependência de rede entre edge e cloud | Interrupção parcial | Buffer local, reenvio idempotente e operação degradada offline |
| Resistência do cliente por LGPD/vigilância | Dificuldade comercial | Borrar rosto, guardar evento e evidência mínima, comunicação focada em segurança do trabalho |
| Crescimento de escopo prematuro | MVP atrasado | Limitar MVP a fluxo base: captura, detecção, validação, incidente e evidência |
