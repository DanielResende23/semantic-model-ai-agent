# Banco de perguntas de teste (Copilot e Data Agent)

Rodar antes de cada promoção para PRD e depois de mudar descrições, AI instructions, schema ou o agente. As perguntas de 1 a 12 também estão no [`nb_ai_evaluate_data_agent`](../fabric/nb_ai_evaluate_data_agent.Notebook/notebook-content.py), que roda contra o Data Agent e falha abaixo de 80% de acerto.

**Base dos valores de referência:** `pl_daily_loss_alerts` executado com `as_of_date = 2018-09-03` (histórico completo). Os números das anomalias foram conferidos com um replay local da mesma regra sobre os CSVs do Olist; confira de novo pela consulta DAX de referência depois da primeira execução no Fabric.

**Rubrica:** ✅ medida e filtro certos e valor bate · ⚠️ valor certo com explicação errada ou aviso faltando · ❌ medida, filtro ou valor errado. A coluna "Regra" aponta a instrução ou descrição que a pergunta exercita.

## Anomalias

| # | Pergunta | Resposta esperada | Regra |
|---|---|---|---|
| 1 | Quantas anomalias de perda foram detectadas no total? | 30 | `Qtd Anomalias` |
| 2 | Quantas anomalias críticas existem? | 10 (prioridade Alta) | sinônimo "críticas" |
| 3 | Quantas anomalias cada monitor detectou? | Receita perdida por categoria: 4 · Atraso de entrega por UF do cliente: 13 · Atraso de entrega por vendedor: 13 | coluna Monitor |
| 4 | Qual foi a anomalia de maior impacto? | Atraso em SP, semana de 13/08/2018: 14,5% x 1,1% de linha de base, impacto ≈ R$ 18,1 mil | ordenação por impacto |
| 5 | Qual o impacto estimado das anomalias de 2018? | ≈ R$ 117 mil (21 anomalias); aviso de 2018 incompleto | aviso de ano incompleto |
| 6 | Quantas anomalias foram recorrentes? | 9 recorrentes, 21 novas | `Status da Anomalia` |
| 7 | Por que MG entrou em anomalia de atraso na semana de 02/04/2018? | 24,9% x 3,9% (6,3x), 85 de 342 itens, atraso médio de 8,1 dias, 25% postados fora do prazo; sinal *Atraso no transporte*; resposta chama de **hipótese** | hipótese ≠ causa confirmada |
| 8 | Quais vendedores tiveram mais de uma anomalia de atraso? | Vendedor 4a3ca931 (3) e Vendedor 7c67e144 (2) | formato do Segmento |
| 9 | Quais categorias tiveram anomalia de receita perdida? | Cool Stuff (2), Ferramentas Jardim, Eletronicos | Dimensão = Categoria |
| 10 | Em quais períodos o RJ ficou em anomalia de atraso? | Duas ondas: 18/12/2017 a 15/01/2018 (5 semanas) e 12/03 a 26/03/2018 (3 semanas) | Status Recorrente |
| 11 | Quem recebe os alertas de atraso do Sudeste? | Coordenação de Logística Sudeste | `Responsável` |
| 12 | Qual a margem das categorias com anomalia? | Não há margem nem custo no modelo; oferece receita perdida ou impacto | limite do modelo |
| 13 | O que fazer com o vendedor 88460e8e? | Anomalia de 02/04/2018: 83,3% dos itens atrasados (20 de 24), 100% postados depois do prazo; mostra a Ação Recomendada | `Ação Recomendada` |
| 14 | Quais anomalias estão com prioridade média em 2018? | Lista ordenada por impacto, começando por MG 09/04/2018 (≈ R$ 4,9 mil) | ordenação por prioridade |
| 15 | Qual o fator médio sobre o padrão nas anomalias de atraso por UF? | `Fator Médio sobre o Padrão` com Monitor = Atraso de entrega por UF do cliente | `Fator sobre o Padrão` em vezes |
| 16 | Quantas hipóteses foram geradas pela IA e quantas por regra? | `Status da Hipótese` Gerada x Regra (depende da execução) | Status da Hipótese |
| 17 | Qual foi o último alerta? | Semana mais recente com anomalia: 13/08/2018 (SP, atraso) | "último alerta" |

## KPIs de perda (herdados do projeto 1)

| # | Pergunta | Resposta esperada | Regra |
|---|---|---|---|
| 18 | Quanto perdemos com pedidos cancelados ou indisponíveis? | `Receita Perdida` ≈ R$ 108 mil (0,7% da receita bruta) | glossário "perda" |
| 19 | Qual o percentual de pedidos entregues com atraso? | `% Pedidos Atrasados` ≈ 6,8% | glossário "atraso" |
| 20 | A nota cai quando a entrega atrasa? | `Nota Média - Entrega no Prazo` ≈ 4,3 x `Nota Média - Entrega Atrasada` ≈ 2,3 | medidas de nota |
| 21 | Quais vendedores têm mais itens atrasados? | `% Itens Atrasados` por `Vendedor[Código do Vendedor]` (não `% Pedidos Atrasados`) | medidas de Vendas por vendedor |
| 22 | Quais 5 categorias têm a maior receita perdida? | `Receita Perdida` por `Produto[Categoria]`, top 5 | glossário "departamento" |
| 23 | Quantos clientes compraram em 2017? | `Qtd Clientes` (pessoa única), não contagem de linhas de Cliente | glossário "cliente" |
| 24 | Quantos pedidos foram entregues em agosto de 2018? | `Pedidos Entregues por Data de Entrega` | data de entrega x compra |
| 25 | Como a receita de 2018 se compara com 2017? | `Receita Bruta Δ% AA`, com aviso de 2018 incompleto | aviso de ano incompleto |

## Consultas DAX de referência

```dax
// 1 a 3, 6
EVALUATE
SUMMARIZECOLUMNS (
    'Anomalias de Perda'[Monitor],
    'Anomalias de Perda'[Status da Anomalia],
    "Anomalias", [Qtd Anomalias],
    "Alta", [Anomalias de Alta Prioridade],
    "Impacto", [Impacto Estimado das Anomalias]
)

// 4, 17
EVALUATE
TOPN (
    5,
    SELECTCOLUMNS (
        'Anomalias de Perda',
        "Semana", 'Anomalias de Perda'[Semana],
        "Monitor", 'Anomalias de Perda'[Monitor],
        "Segmento", 'Anomalias de Perda'[Segmento],
        "Taxa", 'Anomalias de Perda'[Taxa Observada],
        "Base", 'Anomalias de Perda'[Linha de Base],
        "Impacto", 'Anomalias de Perda'[Valor do Impacto Estimado]
    ),
    [Impacto], DESC
)

// 5
EVALUATE
SUMMARIZECOLUMNS ( 'Calendário'[Ano], "Anomalias", [Qtd Anomalias], "Impacto", [Impacto Estimado das Anomalias] )
```

Registrar cada falha (pergunta, resposta, causa) e corrigir no modelo ou no agente, nunca só reescrevendo a pergunta.
