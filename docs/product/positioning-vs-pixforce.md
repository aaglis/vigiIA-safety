# Posicionamento do VigIA vs PixForce (Pix Safety)

Documento de **posicionamento**, não de features. Existe para responder, sem rodeios, a pergunta
que a banca da incubadora **vai** fazer: *"e a PixForce?"*.

## 1. Quem é o concorrente

**PixForce** ([pixforce.com](https://pixforce.com/pt-br/)) — startup brasileira de visão
computacional, fundada em **2016** (Porto Alegre), faturamento na casa de **R$ 12M / US$ 2,9M**.
Produto relevante: **Pix Safety**.

O que o Pix Safety **já entrega hoje**:

- EPI: capacete, colete, luvas
- **Quedas** de trabalhador, distração, interação pessoa-máquina, postura inadequada, alcance excessivo
- **Invasão de perímetro** (zona restrita)
- Roda sobre o **CCTV existente**, 24/7 (inclusive noite e fim de semana)
- Alerta em **tempo real** na plataforma e por **WhatsApp**
- **Privacy by design**: rostos anonimizados por blur (LGPD)
- Modelos prontos, configuráveis sob demanda
- Modelo de negócio: **assinatura + setup contratado** (perfil enterprise / mid-market)

## 2. A verdade desconfortável

Todos os "diferenciais" que assumíamos **a PixForce já tem**:

| O que achávamos ser nosso diferencial | PixForce |
|---|---|
| Conectar nas câmeras existentes | ✅ já faz |
| Alerta em tempo real por WhatsApp | ✅ já faz |
| LGPD / privacidade | ✅ blur de rostos, privacy by design |
| EPI (capacete/colete/luva) | ✅ + quedas, ergonomia, comportamento |
| Zona restrita | ✅ "invasão de perímetro" |

**Conclusão honesta:** não vencemos no *"o que faz"*. Eles têm ~10 anos de modelos treinados,
dados reais de campo, cases e um time grande. Um time de 4 alunos não ganha deles em tecnologia,
maturidade ou catálogo de detecções — e **fingir que ganha derruba o pitch na primeira pergunta**.

## 3. Onde NÃO vamos competir

Decisão explícita, para não desperdiçar o pouco recurso que temos:

- **Não** vamos competir em catálogo de detecções (quedas, ergonomia, postura, EPI completo).
- **Não** vamos disputar grande indústria com processo de compra longo e setup sob medida.
- **Não** vamos vender "somos a PixForce, mais barato" — comparação em que o incumbente ganha sempre.

## 4. A cunha (wedge) escolhida

> **PME industrial do Distrito Industrial de Maracanaú (Ceará), com foco em conformidade NR,
> plug-and-play e suporte local.**

Por que essa cunha se sustenta:

1. **Geografia + porte que o incumbente não alcança.** A PixForce é do Sul e opera com conta
   grande e setup contratado. A fábrica média do Nordeste não é atendida: caro demais, longe
   demais, ciclo de venda incompatível. Nós estamos **na porta do distrito** (campus IFCE
   Maracanaú) — proximidade, visita presencial e suporte no mesmo fuso/cidade são armas que um
   fornecedor distante não replica.
2. **Conformidade NR, não só detecção.** Eles focam em *detectar*. Nós focamos no **depois**:
   relatório/laudo de NR gerado sozinho, trilha de auditoria (**já temos**), evidência assinada
   com SHA-256 (**já temos**), retenção/LGPD com purga auditada (**já temos**). Para uma PME, a dor
   real não é só "ver o incidente" — é **provar conformidade para a fiscalização** sem um time
   de SESMT dedicado.
3. **Preço e implantação.** Plug-and-play sobre a câmera que a fábrica já tem, sem projeto de
   implantação faturado à parte.

Terceiro ângulo avaliado e **descartado como principal**: "on-premise radical" — é um diferencial
fraco, já que a PixForce anuncia privacy by design com blur. Continua sendo um argumento de apoio
(o vídeo nunca sai da planta), não a tese central.

## 5. Cliente-alvo (ICP)

- Indústria de **médio porte** (~50–300 funcionários) no Distrito Industrial de Maracanaú e região.
- Já tem **CCTV instalado** (não quer comprar câmera nova).
- Tem obrigação de **NR** (NR-6 EPI, NR-12 máquinas) e sofre com auditoria/fiscalização.
- **Não tem** time de segurança do trabalho grande nem orçamento para enterprise.
- Decisor: dono / gerente industrial / técnico de segurança — ciclo de venda curto, decisão local.

**Caso de uso matador:** *"a fiscalização chegou / houve um acidente — preciso provar que a
área de risco estava monitorada e que o EPI era cobrado"*. VigIA entrega o incidente **com
evidência visual carimbada e trilha de auditoria**, e o relatório de NR sai pronto.

## 6. A resposta de 30 segundos

> *"A PixForce é uma empresa consolidada e faz um produto muito bom — para a grande indústria,
> com projeto de implantação sob medida. A gente não compete com eles nesse jogo. Nosso alvo é a
> **fábrica média do Distrito de Maracanaú**, que hoje não é atendida por ninguém: é cara demais
> para o fornecedor do Sul e não tem time de segurança para operar uma plataforma complexa. Nós
> entramos plug-and-play na câmera que ela já tem, com **suporte local**, e resolvemos a dor que
> ela sente de verdade: **a papelada da NR**. Eles focam em detectar; nós entregamos o incidente
> **já com evidência e o laudo de conformidade pronto**."*

Note o que a resposta **não** diz: "fazemos o mesmo, mais barato".

## 7. Reflexo no roadmap

**Construir (serve à cunha):**
- **Relatório de NR** (exportável, com evidência e trilha) — hoje inexistente; é o coração da tese.
- Capacete + zona restrita **impecáveis** numa vertical (profundidade > amplitude).
- Onboarding simples: cadastrar câmera e desenhar a zona sem consultor.
- Alerta que funciona (e-mail/WhatsApp).

**Não construir (não serve à cunha, e é onde o incumbente é forte):**
- Detecção de quedas, ergonomia, postura, análise comportamental.
- Plataforma multi-indústria (agro, varejo).
- Billing self-serve elaborado antes de existir cliente pagante.

## 8. Estado atual honesto (17/07/2026)

O que **já funciona de verdade**: CV real (YOLO) sobre câmera/vídeo, detecção de **capacete
ausente** e **intrusão em zona restrita** com geometria, incidente com **evidência anotada**
(SHA-256, URL assinada), trilha de auditoria, multi-tenant, dashboard com atualização automática.

O que **falta para a tese**: relatório de NR (o principal), alerta realmente entregue
(Resend implementado, envio real pendente de chave), desenho de zona pela UI, live-view.

## Fontes

- [Pix Force — Home](https://pixforce.com/pt-br/)
- [Pix Safety](https://pixforce.com/pix-safety/)
- [Pix Force — Detecção de EPIs na indústria](https://pixforce.com/pt-br/deteccao-de-epis-na-industria-ia/)
- [Startupi — Pix Force prevê faturar US$ 2,9 milhões](https://startupi.com.br/pix-force-startup-preve-faturar-us-29-milhoes/)
- [Exame — startup usa IA há 7 anos e vai faturar R$ 12 milhões](https://exame.com/negocios/essa-startup-ja-usa-inteligenica-artificial-ha-7-anos-e-vai-faturar-r-12-milhoes-com-ela/)
