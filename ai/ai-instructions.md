# AI instructions

Texto para colar em **Prep data for AI → Add AI instructions** do modelo `Olist Prevenção de Perdas` (Desktop ou serviço). Vale para o Copilot e para o Fabric Data Agent, que gera DAX apenas com os metadados do modelo e com esta configuração. Regras de persona e de escolha de fonte do agente ficam no `nb_ai_setup_data_agent`.

O Desktop grava a configuração na pasta `Copilot/` do `.SemanticModel`. Depois de aplicar, salve o PBIP e versione essa pasta junto com o TMDL; não edite os arquivos dela à mão. O bloco abaixo tem cerca de 3 mil caracteres, bem abaixo do limite do campo.

```text
Contexto: marketplace de e-commerce brasileiro Olist, pedidos de set/2016 a out/2018, valores em reais (BRL).
O modelo serve à prevenção de perdas: medir vendas perdidas e atrasos, e acompanhar as anomalias de perda que um
processo automático detecta toda semana, com hipótese de causa e ação recomendada geradas por IA.

Glossário:
- "Vendas", "faturamento", "GMV" = [Receita Bruta] (produto + frete, todos os status).
- "Perda", "receita perdida", "venda perdida" = [Receita Perdida]: pedidos Cancelados ou Indisponíveis.
- "Atraso", "fora do prazo" = entrega depois da data prevista. KPI de pedido: [% Pedidos Atrasados]; por vendedor ou
  categoria: [% Itens Atrasados].
- "Satisfação", "nota" = [Nota Média de Avaliação] (1 a 5). Avaliação negativa = nota 1 ou 2.
- "Cliente" = [Qtd Clientes] (pessoa única). "Lojista", "seller", "parceiro" = Vendedor. "Departamento" = Produto[Categoria].
- "Anomalia", "alerta", "desvio", "ocorrência fora do padrão" = uma linha da tabela Anomalias de Perda. Conte com
  [Qtd Anomalias]; "críticas" ou "urgentes" = [Anomalias de Alta Prioridade].
- "Impacto", "quanto custou a anomalia" = [Impacto Estimado das Anomalias]: perda acima do padrão, estimada.
- "Padrão", "normal", "linha de base" = coluna Linha de Base (mediana das 8 semanas anteriores do mesmo segmento).
- "Causa", "por quê" = coluna Hipótese de Causa. "O que fazer" = coluna Ação Recomendada. "Dono" = Responsável.

Regras:
- Em Vendas, Pedidos e Pagamentos, períodos referem-se à data da compra (Calendário). Para volume de entregas por
  período use [Pedidos Entregues por Data de Entrega].
- Em Anomalias de Perda, o Calendário filtra pela segunda-feira da semana analisada (coluna Semana): semana da compra
  nas anomalias de venda perdida e semana da entrega nas de atraso. Uma semana conta no mês e no ano da sua segunda-feira.
- A coluna Anomalias de Perda[Semana] não serve para vendas ou pedidos por semana; ela só filtra anomalias.
- Perguntas por vendedor ou produto usam medidas da tabela Vendas. Medidas de Pedidos não filtram por vendedor nem produto.
- A tabela Anomalias de Perda só se relaciona com o Calendário, pela Semana. Para anomalias de uma categoria, UF ou
  vendedor filtre Anomalias de Perda[Segmento] junto com [Dimensão]; não use Produto, Cliente ou Vendedor.
- Vendedor aparece em Segmento como "Vendedor " + 8 primeiros caracteres do código.
- Taxa Observada e Linha de Base são percentuais; Fator sobre o Padrão é vezes (ex.: 5,3x).
- "Esta semana", "agora" ou "último alerta" = maior Semana com anomalia ([Última Semana com Anomalia]).
- Ordene anomalias por Prioridade (Alta, Média, Baixa) e depois por impacto.
- Hipótese de Causa é hipótese gerada por IA: diga "hipótese provável", nunca "a causa foi". Se Status da Hipótese
  for Regra, avise que o texto veio de uma regra, não da IA.
- 2016 tem poucos pedidos e set-out/2018 está incompleto; avise ao comparar anos.
- Não há custo, margem, estoque ou meta no modelo; diga isso em vez de aproximar.

Respostas: R$ com duas casas, percentuais com uma casa. Em rankings, os 10 primeiros, salvo pedido diferente.
```

Cada regra tem ao menos uma pergunta em [`test-questions.md`](test-questions.md) que a exercita (coluna "Regra").
