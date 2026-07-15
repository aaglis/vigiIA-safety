# VigIA — Segurança industrial por visão computacional

> Documento de projeto para o Programa de Incubação do IFCE Maracanaú (Edital 5/2026, modalidade Pré-incubação).
> Nome de trabalho: **VigIA** (vigia + IA). Alternativas: SafeVision, OlhoSeguro, SentinelaEPI, VisãoSegura.
> Time: 4 alunos de Ciência da Computação — full-stack + infra (VPS/Docker/Caddy) + visão computacional + dados/segurança.

---

## 1. Resumo em uma frase

Software que se conecta às **câmeras que a indústria já tem** e usa **visão computacional** para fiscalizar segurança em tempo real — detecta operário sem EPI, pessoa em zona de risco e quedas, alerta na hora e gera a evidência para auditoria de NR. Sem hardware novo, sem identificar pessoas.

---

## 2. O problema

Toda indústria no Brasil é obrigada a cumprir as **Normas Regulamentadoras (NRs)**:
- **NR-6** — uso obrigatório de EPI (capacete, óculos, luva, botina, protetor auricular...).
- **NR-12** — proteção em máquinas e equipamentos.
- **NR-18** — segurança na construção civil.

Hoje a fiscalização é feita pelo **técnico de segurança do trabalho** andando pela planta. Um humano **não vê tudo, 24 h, em todos os setores ao mesmo tempo**. Quando alguém tira o capacete num setor sem ninguém olhando, o risco vira acidente.

Custo de um acidente grave: **indenização + processo trabalhista + afastamento + parada de produção + multa do Ministério do Trabalho + aumento do seguro (FAP/RAT)**. Um único acidente sério paga anos do software.

> **Validar (entrevistas):** quantos quase-acidentes/mês? Qual o custo do último acidente? Quantos técnicos de segurança e quantos setores cada um cobre? Esses números viram o slide de ROI.

---

## 3. Como funciona

### 3.1 Visão geral do fluxo

```
Câmera existente (RTSP)  ->  Detecção (pessoa + EPI + zona)  ->  Lógica de violação  ->  Alerta em tempo real  ->  Registro + dashboard
(CCTV da fábrica)            (modelo de visão, ex.: YOLO)        (persiste N frames?)     (WhatsApp/painel/som)     (foto, hora, setor, relatório NR)
```

### 3.2 Passo a passo técnico

1. **Captura.** Conectar ao stream **RTSP** das câmeras que a fábrica já possui (OpenCV/FFmpeg). Sem instalar câmera nova.
2. **Detecção de pessoas e EPI.** Modelo de detecção de objetos (ex.: **YOLOv8/v11** ou **RT-DETR**) localiza cada pessoa e os itens de EPI no frame.
3. **Associação EPI ↔ pessoa.** Para cada pessoa detectada, verificar se o EPI correspondente está nela. Estratégias:
   - duas etapas: detecta pessoa → recorta → classifica "com/sem capacete, com/sem colete";
   - estimativa de **pose** (keypoints) para checar se o capacete está na cabeça, não na mão.
4. **Zona de risco (geofencing).** Desenhar polígonos na imagem (áreas proibidas, perto de máquina, sob carga). Checar se os pés/bbox da pessoa estão dentro.
5. **Rastreamento + anti-falso-positivo.** **ByteTrack/DeepSORT** acompanha a mesma pessoa entre frames; a violação só dispara se **persistir N frames** (evita alarme quando o EPI fica um instante oculto). Reduz fadiga de alerta.
6. **Comportamento.** Queda (pose horizontal + queda súbita), pessoa caída/parada demais (passou mal), aglomeração.
7. **Alerta + registro.** Violação → alerta em tempo real (painel, som, **WhatsApp** para o técnico) + salva evidência (clipe/foto, timestamp, setor).
8. **Painel.** Histórico, **% de conformidade**, mapa de calor de zonas de risco, relatório pronto para auditoria de NR.

### 3.3 Exemplo concreto

Câmera sobre o setor de prensa. Operário entra **sem capacete**. O sistema detecta "pessoa + sem capacete + zona prensa", confirma por alguns frames, e dispara: *"Violação NR-6 — setor prensa — 14h32"* no WhatsApp do técnico, com a foto. O técnico age **antes** de virar acidente. No fim do mês, o relatório mostra que o setor prensa teve 12 violações de capacete → ação de treinamento direcionada.

---

## 4. Módulos do produto

- **EPI:** capacete, colete refletivo, óculos, luva, botina, protetor auricular, máscara/respirador.
- **Zona de risco:** entrada em área proibida, proximidade de máquina, sob carga suspensa, empilhadeira × pedestre.
- **Comportamento:** queda, pessoa caída, aglomeração, ausência prolongada de movimento.
- **Relatórios:** conformidade por setor/turno, evidência para auditoria (ISO 45001 / NR), tendência no tempo.

**Estratégia de entrada:** começar pelos EPIs **mais fáceis e de maior contraste** (capacete + colete) — maior precisão — e expandir para os difíceis (óculos, luva) depois.

---

## 5. Viabilidade técnica e precisão (o ponto crítico)

**Posicionamento:** vendemos **detecção assistiva com evidência**, não juiz infalível. Reportamos precisão medida e deixamos o técnico decidir. O valor é cobrir o que o humano não consegue ver o tempo todo.

### 5.1 O que é fácil e o que é difícil

| Tarefa | Dificuldade | Observação |
|---|---|---|
| Detectar pessoa | Baixa | Modelos pré-treinados são muito bons. |
| Capacete / colete | Baixa-média | Objeto grande, alto contraste → boa precisão. Melhor caso de entrada. |
| Óculos / luva | Alta | Pequeno, oclusão, distância da câmera → exige câmera mais próxima e mais dados. |
| Zona de risco | Baixa | Geometria de polígono; depende de boa marcação por setor. |
| Queda | Média | Pose + temporal; cuidar de falso positivo (agachar ≠ cair). |

### 5.2 De que depende a precisão

- **Ângulo, altura e distância da câmera** — fator nº 1. Câmera muito alta/longe perde EPI pequeno.
- **Iluminação** e oclusão (pessoas se cruzando, máquinas na frente).
- **Dados de treino** representativos do ambiente do cliente.

**Mitigação central — calibração por site:** no onboarding, coletar e rotular algumas horas de vídeo das câmeras do cliente e **fazer fine-tune** do modelo para aquele ambiente. Isso eleva muito a precisão real e vira parte paga do serviço (setup).

### 5.3 Como provar a precisão antes de vender (Fase 0)

1. Pegar **datasets públicos de EPI** (ver §7) + fine-tune de um YOLO.
2. Montar um **conjunto de teste rotulado** (idealmente de um ambiente industrial real / vídeo do design partner).
3. Medir **precisão, recall e mAP por classe** + **taxa de falso positivo** (crucial — alarme demais = ninguém usa).
4. Conclusão = número real de precisão por EPI → define o que prometer.

Reportar por classe, sempre. "Capacete: precisão 96% / recall 93%" é honesto e vendável; prometer "detecta tudo" não é.

---

## 6. LGPD e privacidade (vira argumento de venda)

- Detecta **comportamento/EPI, não identidade**. **Borrar rostos** por padrão.
- Guardar **eventos** (violação) e clipes curtos, **não** vídeo contínuo; política de retenção.
- Processamento **on-premise** (vídeo não sai da fábrica) — opção forte para o cliente preocupado com dado.
- Base legal: segurança do trabalho / cumprimento de obrigação legal (NR).

---

## 7. Stack técnica e dados

**Visão / ML**
- **Ultralytics YOLO** (v8/v11) ou RT-DETR para detecção; **ByteTrack** para rastreamento; estimativa de pose (YOLO-pose/MediaPipe) para associação e queda.
- **PyTorch**, **OpenCV** (RTSP), treino no **Colab/GPU**.

**Datasets públicos de EPI para começar (fine-tune)**
- Hard Hat Workers (capacete) · CHV (Color Helmet Vest) · SH17 · Pictor-PPE · diversos datasets de PPE no Roboflow.
- Depois: dados rotulados do próprio cliente (calibração).

**Produto / infra (joga na força do time)**
- Ingestão RTSP + inferência: serviço Python por câmera.
- **Edge vs nuvem:** processar **on-premise** num mini-PC/GPU na fábrica (vídeo fica local, menos banda, menor latência, melhor LGPD) **ou** puxar para o VPS. Recomendado: edge no site + painel/relatórios na nuvem (só metadados sobem). Aqui a força de infra do time é diferencial.
- Backend: **FastAPI**; eventos em **PostgreSQL**; front **React**; alertas **WhatsApp/e-mail**; deploy **Docker + Caddy**.
- Aceleração: GPU para tempo real (várias câmeras). Começar com YOLO-nano/small em 1 câmera.

---

## 8. Roadmap de construção — 12 meses (entregáveis da pré-incubação)

| Fase | Período | Objetivo | Entregável |
|---|---|---|---|
| **Fase 0 — Prova de precisão** | Semana 1–4 | Validar viabilidade | YOLO fine-tunado (capacete+colete) + **métricas de precisão/recall/falso positivo**. Go/No-Go. |
| **Fase 1 — MVP** | Mês 2–3 | Pipeline em tempo real | RTSP → detecção EPI → alerta → dashboard básico (1 câmera). **EVTE inicial.** |
| **Fase 2 — Robustez + parceiro** | Mês 4–6 | Reduzir falso positivo e validar mercado | Zona de risco (geofencing) + tracking + **design partner** (fábrica do Distrito Industrial via IFCE) + calibração no site real. |
| **Fase 3 — Piloto pagante** | Mês 7–9 | Mais cobertura | EPIs adicionais + queda + **relatórios de NR** + piloto pagante. **Plano de negócios.** |
| **Fase 4 — Escala** | Mês 10–12 | Multi-câmera/multi-site | Edge box, multi-tenant, métricas de precisão e ROI para o pitch de graduação. |

### Divisão dos 4

- **Pessoa A — Visão computacional:** detecção, pose, tracking, treino e fine-tune dos modelos.
- **Pessoa B — Infra / edge:** ingestão RTSP, deploy edge/VPS, Docker, performance/GPU, escala multi-câmera.
- **Pessoa C — Dados / validação / segurança:** datasets, rotulagem, calibração por site, métricas, política de LGPD.
- **Pessoa D — Produto / negócio:** dashboard, alertas, relatórios de NR, entrevistas, EVTE/plano, domínio das normas.

(Ao menos 1 sócio com as **10 h/semana** exigidas pelo edital.)

---

## 9. Modelo de negócio

- **SaaS B2B por câmera/mês** (ou por setor/planta) — receita recorrente.
- **Setup/calibração** pago no onboarding (fine-tune no ambiente do cliente).
- **Edge box** opcional (vender/locar mini-PC com GPU, ou cliente fornece).
- COGS baixo (software + edge/VPS) = margem alta = argumento de "rentabilidade real" para a banca.

**Compradores:** indústrias (Distrito Industrial de Maracanaú), construtoras (NR-18), frigoríficos, logística/armazéns, mineração. Expansível por NR e por setor com o mesmo núcleo.

### Orçamento

| Item | Custo |
|---|---|
| Câmera IP/webcam para protótipo | ~R$ 150 |
| Treino de modelo (Colab) | R$ 0 |
| Inferência protótipo (VPS/laptop) | já têm |
| Domínio | ~R$ 40 |
| **Total para começar** | **~R$ 200–800 (cabe no capital)** |

Edge box com GPU (Jetson/PC usado) só na fase de piloto real — pode ser custeado pelo cliente.

---

## 10. Concorrência e posicionamento

**Honesto:** não é deserto. Há players no Brasil e no mundo (ex.: soluções de "safety analytics" e integradores; global: Protex AI, Voxel, Intenseye, Everguard). É um mercado **em crescimento**, porém **muito menos saturado que rastreamento indoor (RTLS)**.

**Onde temos espaço (diferenciação):**
- **Foco em NR brasileira** e relatório pronto para fiscalização/auditoria.
- **Preço acessível para a média indústria** (não só multinacional).
- **On-premise / LGPD** como padrão.
- **Suporte e calibração local** + respaldo de pesquisa do IFCE.
- **Vertical + regional** (Distrito de Maracanaú) em vez de genérico global.

O verdadeiro concorrente é o **status quo**: técnico de segurança sozinho + checklist em papel.

---

## 11. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Falso positivo (alarme demais) | Persistência por N frames + tracking + limiar calibrado; medir taxa de FP na Fase 0. |
| EPI pequeno (óculos/luva) difícil | Começar por capacete/colete; câmera mais próxima; mais dados; expandir depois. |
| Variação de câmera/iluminação por site | **Calibração/fine-tune por site** no onboarding (vira serviço pago). |
| LGPD / receio de vigilância | Borrar rosto, on-premise, guardar evento não vídeo; enquadrar como segurança do trabalho. |
| Resistência do operário ("estão me vigiando") | Comunicar como proteção coletiva, anônima, foco em EPI não em produtividade. |
| Concorrentes maiores | Vertical NR + preço + local + LGPD + suporte. |
| Venda B2B lenta | Começar pela fábrica-parceira do distrito via IFCE; ROI claro acelera. |

---

## 12. Encaixe na incubadora IFCE (Edital 5/2026)

| Critério da banca | Como atende |
|---|---|
| Grau de inovação | IA de visão aplicada a segurança do trabalho com foco em NR |
| Tamanho real do mercado | Toda indústria/obra obrigada a cumprir NR |
| Potencial de crescimento | SaaS replicável por câmera/site/NR/estado |
| Familiaridade técnica | Visão computacional + infra + dados = núcleo exato do time |
| Rentabilidade real | Recorrente + COGS baixo (software + edge/VPS) |
| Impacto social/regional | Reduz acidentes de trabalho; **Distrito Industrial de Maracanaú na porta do campus** |
| Apresentação do pitch | **Demo ao vivo**: câmera detectando "sem capacete" na hora |

**Vantagem do programa:** professor orientador (segurança do trabalho / visão computacional), articulação com pesquisadores e ponte com o Distrito Industrial — exatamente o que a pré-incubação oferece. Piloto real ao lado do campus.

---

## 13. Próximos passos imediatos

1. **Fase 0:** fine-tune de um YOLO em dataset público de EPI + medir precisão/recall/falso positivo (capacete + colete).
2. **Gravar uma demo** de 1 câmera detectando "sem capacete" em tempo real (vale ouro no vídeo pitch).
3. **Procurar professor orientador** no IFCE (segurança do trabalho / visão computacional).
4. **Mapear 1 design partner** no Distrito Industrial de Maracanaú (via incubadora/IFCE) para calibração e piloto.
5. **Definir nome** + registrar domínio (~R$ 40).
6. **Gravar o vídeo pitch** (≤ 5 min) com a demo + ROI.
7. **Inscrever** (fluxo contínuo — qualquer momento em 2026). Contato: incubadora.mar@ifce.edu.br.

---

*Documento de trabalho. Os números de precisão devem vir da Fase 0 (medição real) antes de qualquer promessa a cliente — a banca pontua "rentabilidade real" e a indústria exige confiabilidade comprovada. EPI pequeno e falso positivo são os riscos técnicos a vigiar de perto.*
