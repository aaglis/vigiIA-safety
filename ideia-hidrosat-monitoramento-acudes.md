# HidroSat CE — Monitoramento de açudes por satélite + ML

> Documento de projeto para o Programa de Incubação do IFCE Maracanaú (Edital 5/2026, modalidade Pré-incubação).
> Nome de trabalho: **HidroSat CE** (alternativas: Olho d'Água, SentinelÁgua, AçudeWatch).
> Time: 4 alunos de Ciência da Computação — full-stack + infra (VPS/Docker/Caddy) + visão computacional + engenharia de dados.

---

## 1. Resumo em uma frase

Plataforma que usa **imagem de satélite gratuita + visão computacional** para medir continuamente o volume de água dos açudes do Ceará, **prever escassez com antecedência** e entregar alertas a gestores públicos — sem hardware, sem satélite pago, validado contra os dados oficiais.

---

## 2. O problema

O Ceará é semiárido e depende de **açudes** para abastecimento, irrigação e dessedentação. Saber quanta água há em cada açude define racionamento, plantio e gestão de crise.

Hoje a medição é majoritariamente **manual e esporádica** (régua, sensor in loco, visita técnica). A COGERH e a FUNCEME acompanham os açudes grandes, mas:

- os **açudes pequenos do interior** ficam sem monitoramento contínuo;
- o dado chega com **atraso**;
- o monitoramento existente **não é preditivo** (não diz "vai ficar crítico em X semanas");
- ir a campo é **caro** e não escala para centenas de reservatórios.

Resultado: decisões de racionamento chegam tarde, safras se perdem, cidades entram em colapso hídrico de surpresa.

---

## 3. A solução — como funciona

### 3.1 Visão geral do fluxo

```
Satélite (grátis)  ->  Download automático  ->  Visão computacional       ->  Curva Cota-Área-Volume  ->  Série temporal  ->  Previsão + alerta
(Sentinel-2/-1)        (por açude, semanal)     (segmenta espelho d'água)     (área -> volume em hm³)      (enche/esvazia?)    (dashboard + WhatsApp/e-mail)
```

### 3.2 Passo a passo técnico

1. **Aquisição.** Para cada açude (definido por um polígono/bounding box), baixar automaticamente as imagens mais recentes de Sentinel-2 (óptico, 10 m) e Sentinel-1 (radar, atravessa nuvem). Fontes gratuitas no §5.
2. **Pré-processamento.** Recorte na área de interesse, máscara de nuvem (Sentinel-2 banda SCL/cloud mask), correção radiométrica. Para o radar: calibração, filtro de speckle, correção de terreno.
3. **Segmentação da água (núcleo de CV).** Calcular um índice de água e separar "água" de "não-água":
   - **NDWI** (McFeeters) = `(Green - NIR) / (Green + NIR)` → bandas B3 e B8 do Sentinel-2.
   - **MNDWI** (Xu) = `(Green - SWIR) / (Green + SWIR)` → bandas B3 e B11; melhor onde há solo exposto/construção.
   - Limiar automático com **Otsu**, ou modelo supervisionado (**U-Net** / Random Forest) treinado com máscaras de referência (ver JRC Global Surface Water no §5).
   - No radar (Sentinel-1): água tem **baixo retroespalhamento** (fica escura) → limiar no backscatter VV/VH.
4. **Cálculo de área.** `área = nº de pixels de água × área do pixel` (100 m² no Sentinel-2). Resultado em hectares/km².
5. **Área → Volume.** Interpolar na **curva Cota-Área-Volume (CAV)** do açude (publicada pela COGERH/DNOCS/ANA para os monitorados). Resultado em hm³.
   - Sem curva (açude pequeno): derivar uma curva aproximada de um **DEM** (SRTM 30 m ou Copernicus DEM) "enchendo" a bacia, **ou** reportar só a tendência de área.
6. **Série temporal.** Acumular volume estimado ao longo das semanas → curva de evolução (enchendo/esvaziando, em que ritmo).
7. **Previsão.** Extrapolar a tendência (Theil-Sen robusto / Prophet / ARIMA), incorporando evaporação e chuva (dados da FUNCEME) → cenários com **intervalo de confiança**. Nunca uma data exata.
8. **Entrega.** Dashboard com mapa (vermelho = crítico), série histórica e **alerta** ("Açude X em 23%, caindo 2%/semana, crítico em ~6–10 semanas").

### 3.3 O truque que vira diferencial: nuvem

Satélite **óptico não enxerga através de nuvem** — e o Ceará tem estação chuvosa. Solução: combinar com **radar Sentinel-1 (SAR)**, que atravessa nuvem e enxerga a água de dia ou de noite. Processar SAR é mais difícil (poucos times fazem) → vira **moat técnico**. Estratégia: óptico quando o céu está limpo (mais preciso), radar para não ter buraco na série.

---

## 4. Precisão e confiabilidade (o ponto crítico)

**Posicionamento que resolve o medo de "estar errado":** não substituímos a medição oficial — **calibramos contra ela** e reportamos a incerteza. Vendemos *monitoramento contínuo de baixo custo + alerta precoce, validado*, não "medição ao litro".

### 4.1 Onde a precisão é ganha ou perdida

| Camada | Dificuldade | Precisão realista |
|---|---|---|
| Medir área do espelho | Baixa-média | ~95%+ para açude > poucos hectares (Sentinel-2 10 m). Erro concentrado na borda (pixel misto). |
| Área → Volume | Baixa *se* há curva CAV | Erro dominado pela qualidade da curva e pelo **assoreamento** (curva antiga superestima). |
| Previsão futura | Média-alta | Incerteza inerente (chuva/evaporação/retirada). Sempre cenários + intervalo, nunca data exata. |

Erro de volume típico relatado na literatura de sensoriamento remoto: **~5–15%**, dependendo da curva e do assoreamento. Suficiente para alerta precoce e para cobrir o açude pequeno; **não** substitui medição legal.

### 4.2 Quantificação de incerteza

Sempre reportar `Volume = 18 hm³ ± 8%`. Propagar:
- erro de borda da segmentação (≈ perímetro × resolução);
- incerteza da curva CAV.

Mostrar a barra de erro **aumenta** a credibilidade — gestor confia em sistema que conhece o próprio erro.

### 4.3 Não precisa de hardware nem satélite pago

- **Dispositivo dentro do açude? NÃO.** A COGERH/ANA já têm sensores in loco nos açudes monitorados e **publicam o dado** — usamos isso como *ground truth* gratuito para calibrar. (Opcional: 1 sensor barato num açude-vitrine só para demonstração.)
- **Satélite pago? NÃO para precisão.** Dado grátis (Sentinel/Landsat) é o padrão científico e operacional. Pago (Planet ~3 m, Maxar sub-metro) só ajuda em **açude pequeno** ou frequência maior → **tier premium futuro**. Planet tem programa gratuito de pesquisa para o protótipo.

A alavanca real de precisão é **boa curva CAV + quantificação de incerteza**, não satélite caro.

---

## 5. Fontes de dados (todas gratuitas)

| Dado | Fonte | Uso |
|---|---|---|
| Sentinel-2 (óptico 10 m, ~5 dias) | Copernicus Data Space Ecosystem | Segmentação da água (NDWI/MNDWI) |
| Sentinel-1 (radar C, ~6–12 dias) | Copernicus Data Space Ecosystem | Enxergar através de nuvem |
| Landsat 8/9 (30 m, ~16 dias) | USGS EarthExplorer | Série histórica longa (validação) |
| CBERS-4A (INPE) | Catálogo INPE | Alternativa nacional, frequência extra |
| JRC Global Surface Water (Pekel et al.) | Google Earth Engine | Máscara de referência para treinar/validar |
| DEM (SRTM / Copernicus DEM) | USGS / Copernicus | Curva aproximada onde falta CAV |
| Volume oficial dos açudes | Portal Hidrológico do Ceará (COGERH/FUNCEME), SAR/ANA | **Ground truth** para calibrar e validar |
| Chuva / evaporação | FUNCEME | Variável da previsão |

---

## 6. O primeiro experimento: BACKTEST (mata o risco antes de vender)

Antes de prometer qualquer coisa a uma prefeitura, **medir a precisão real** com dado histórico. Custo: **R$ 0**. É também o **MVP** e a prova de venda.

### Passo a passo do backtest

1. **Selecionar** 5–10 açudes que a COGERH/ANA monitora e que têm **histórico de volume medido** (ex.: Castanhão, Orós, Banabuiú e alguns médios/pequenos).
2. **Baixar o arquivo histórico** gratuito de Sentinel-2 (e Sentinel-1) desses açudes para 2018–2024.
3. **Rodar o pipeline** (segmentação → área → volume via curva CAV) para cada data com imagem boa.
4. **Alinhar** a série estimada com a série de **volume oficial medido** (mesmas datas).
5. **Calcular métricas de erro:** MAE, RMSE, **MAPE (% médio)**, viés (bias), R². Plotar estimado × medido.
6. **Analisar** o erro por tamanho do açude, cobertura de nuvem e estação.
7. **Conclusão:** esse é o **número real** de precisão → define o que se pode prometer.
   - ~8%? Já temos o gráfico de validação para mostrar à prefeitura.
   - ~30%? Descobrimos cedo e barato — ajusta ou pivota.

### Pseudocódigo do backtest

```python
# Dependências: rasterio, numpy, geopandas, scikit-image, requests/openeo/sentinelsat
for acude in acudes_monitorados:
    cav = carregar_curva_cav(acude)            # cota-area-volume oficial
    medido = carregar_volume_oficial(acude)    # serie historica COGERH/ANA
    estimado = []
    for data, imagem in baixar_serie_sentinel(acude, 2018, 2024):
        if cobertura_nuvem(imagem) > 0.4:
            imagem = baixar_sar(acude, data)    # fallback radar
        agua = segmentar_agua(imagem)           # NDWI/MNDWI + Otsu  ou  U-Net
        area_ha = contar_pixels(agua) * area_pixel
        volume_hm3 = cav.area_para_volume(area_ha)
        estimado.append((data, volume_hm3))
    erro = comparar(estimado, medido)           # MAE, RMSE, MAPE, bias, R2
    plotar(estimado, medido, erro)
```

> **Este experimento é a primeira coisa a fazer.** Responde quantitativamente "nosso sistema é confiável?" e cabe nas 4 primeiras semanas.

---

## 7. Stack técnica

**Processamento / ciência de dados**
- Python, **rasterio** + **GDAL** (raster), **geopandas** + **PostGIS** (vetor/geo), **scikit-image** (índices/Otsu), **PyTorch** (U-Net), **SNAP/pyroSAR** ou **snappy** (pré-processamento SAR).
- Acesso a imagem via **STAC API** / **openeo** / **sentinelsat** / **Google Earth Engine** (ótimo para o backtest e prototipagem; atenção à licença de uso comercial — para produção, mover processamento para o VPS próprio).

**Produto (joga na força de infra do time)**
- Banco: **PostgreSQL + PostGIS** (geo + série temporal num só banco).
- API: **FastAPI**.
- Front: **React** + mapa (**MapLibre/Leaflet/deck.gl**).
- Agendamento: cron / job runner leve para baixar e processar imagens automaticamente.
- Deploy: **Docker + Caddy** no **VPS próprio** → COGS baixo = margem alta (argumento de "rentabilidade real" para a banca).
- Alertas: e-mail + WhatsApp.

---

## 8. Roadmap de construção — 12 meses (entregáveis da pré-incubação)

| Fase | Período | Objetivo | Entregável |
|---|---|---|---|
| **Fase 0 — Prova de precisão** | Semana 1–4 | Validar viabilidade técnica | **Backtest** em 5–10 açudes + relatório de erro (MAPE). Go/No-Go. |
| **Fase 1 — MVP** | Mês 2–3 | Pipeline automatizado | Download + segmentação + volume para 1 bacia/conjunto de açudes + dashboard básico. **EVTE inicial.** |
| **Fase 2 — Robustez + parceiro** | Mês 4–6 | Furar nuvem e validar mercado | Integração do **radar (SAR)**, multi-açude, alertas. **Professor orientador** + **1 design partner** (COGERH/prefeitura/comitê de bacia). |
| **Fase 3 — Previsão + piloto** | Mês 7–9 | Antecipar crise | Módulo de previsão + intervalo de confiança. **Piloto real** rodando. **Plano de negócios.** |
| **Fase 4 — Escala** | Mês 10–12 | Pronto para vender | Multi-tenant, onboarding, métricas de precisão e de uso para o pitch de graduação. |

### Divisão dos 4 (full-stack + infra + CV + dados)

- **Pessoa A — Visão computacional:** segmentação (NDWI/MNDWI/U-Net), validação da máscara, métricas de área.
- **Pessoa B — Infra / pipeline de dados:** ingestão automática de imagem, processamento SAR, VPS/Docker, agendamento, escala.
- **Pessoa C — Dados / hidrologia / ML:** curvas CAV, calibração, backtest, modelo de previsão, quantificação de incerteza.
- **Pessoa D — Produto / negócio:** dashboard, mapas, alertas, onboarding, entrevistas de validação, EVTE/plano.

(Ao menos 1 sócio com as **10 h/semana** exigidas pelo edital.)

---

## 9. Modelo de negócio

- **SaaS B2B/B2G por assinatura**, faixas por número de açudes/bacias monitorados — receita recorrente.
- Possível **setup/projeto inicial** pago (configurar curvas, integrar bacia).
- **Tier premium:** satélite de alta resolução (Planet) para açudes pequenos + previsão avançada.
- COGS baixo (dado grátis + self-host) = margem alta.

**Compradores:** COGERH, FUNCEME, prefeituras, comitês de bacia, CAGECE (saneamento), agro/irrigantes, ANA. Expansível a outros estados do semiárido (PE, PB, RN, BA, PI) — mesmo código.

---

## 10. Concorrência e posicionamento

- **Governo (COGERH/FUNCEME/ANA — SAR):** já monitora os grandes, mas grosso, atrasado, **não preditivo**, muita medição manual. → É **cliente/parceiro**, não inimigo.
- **Ferramentas globais (Earth Engine, Sentinel Hub, startups internacionais):** genéricas, não-localizadas, sem relação com o gestor cearense, não cobrem o açude pequeno.
- **Academia:** há artigo fazendo isso, mas **não virou produto operacional**.

**Brecha (onde temos poucos concorrentes):** localizado + preditivo + cobre o açude pequeno + entregue como serviço operacional pronto, validado contra dado oficial. O verdadeiro concorrente é o **status quo manual**.

---

## 11. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Precisão insuficiente | **Backtest primeiro** (Fase 0); só promete o que o erro medido permite; reporta incerteza. |
| Nuvem bloqueia óptico | Radar Sentinel-1 (SAR) como fallback. |
| Curva CAV ausente/assoreada | Usar tendência de área onde falta curva; sinalizar assoreamento como produto extra. |
| Falta de domínio em hidrologia | Professor orientador do IFCE + design partner (o programa de incubação existe para isso). |
| Governo "já faz" | Entregar mais (açude pequeno, previsão, automação) e validar disposição a pagar cedo. |
| Venda pública lenta | Começar por agro/comitês/prefeitura pequena; usar a incubadora como ponte institucional. |

---

## 12. Encaixe na incubadora IFCE (Edital 5/2026)

| Critério da banca | Como atende |
|---|---|
| Grau de inovação | CV + SAR + previsão hídrica localizada; quase ninguém faz no CE |
| Tamanho real do mercado | Centenas de açudes no CE + todo o semiárido nordestino |
| Potencial de crescimento | SaaS replicável a outros estados com o mesmo código |
| Familiaridade técnica | CV + dados + infra = exatamente o núcleo técnico |
| Rentabilidade real | Recorrente + COGS baixo (dado grátis + self-host) |
| Impacto social/ambiental regional | Água é a dor nº 1 do Ceará; ajuda gestão pública e produtor |
| Apresentação do pitch | Demo do dashboard + gráfico de validação do backtest |

**O gap de domínio é o encaixe perfeito com o programa:** a pré-incubação oferece "orientação técnica de servidor do IFCE", "articulação com pesquisadores" e o NIT. Time técnico + professor de domínio é a fórmula clássica de spin-off.

---

## 13. Próximos passos imediatos

1. **Rodar o backtest** (Fase 0) em 5–10 açudes com histórico oficial → descobrir a precisão real.
2. **Procurar professor orientador** no IFCE em recursos hídricos / meio ambiente / geoprocessamento / sensoriamento remoto.
3. **Mapear 1 design partner** (COGERH, FUNCEME, prefeitura do interior, comitê de bacia) para validar a dor e o pagamento.
4. **Definir nome** + registrar domínio (~R$ 40).
5. **Gravar o vídeo pitch** (≤ 5 min) com a demo + gráfico de validação.
6. **Inscrever** (fluxo contínuo — qualquer momento em 2026). Contato: incubadora.mar@ifce.edu.br.

---

*Documento de trabalho. Os números de precisão devem vir do backtest real antes de qualquer promessa a cliente — a banca pontua "rentabilidade real" e "tamanho real do mercado", e o gestor público exige confiabilidade comprovada.*
