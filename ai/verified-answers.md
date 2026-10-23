# Verified answers

Criadas a partir dos visuais do relatório `Olist Prevenção de Perdas` (menu do visual → **Set up a verified answer**). Ficam salvas no modelo, não no relatório; revalidar sempre que um visual de origem mudar.

| # | Pergunta de negócio | Visual de origem | Frases gatilho | Filtros permitidos |
|---|---|---|---|---|
| 1 | Quais anomalias de perda temos agora? | Central de Anomalias → tabela *Fila de anomalias* | "quais anomalias temos", "alertas de perda da semana", "o que saiu do padrão", "fila de anomalias", "quais desvios foram detectados", "o que precisa de ação agora" | Prioridade, Monitor, Responsável |
| 2 | Quantas anomalias críticas existem? | Central de Anomalias → cartão *Anomalias de Alta Prioridade* | "quantas anomalias críticas", "alertas urgentes", "anomalias de alta prioridade", "quantos alertas graves", "casos críticos de perda" | Ano |
| 3 | Quanto as anomalias custaram? | Central de Anomalias → cartão *Impacto Estimado das Anomalias* | "impacto das anomalias", "quanto perdemos acima do normal", "custo das anomalias", "perda evitável estimada", "impacto estimado" | Ano, Monitor |
| 4 | Onde as anomalias se concentram? | Central de Anomalias → barras *Impacto por segmento* | "onde estão as anomalias", "quais estados mais têm anomalia", "segmentos com mais impacto", "quais vendedores aparecem nos alertas", "categorias com anomalia" | Monitor, Ano |
| 5 | Quanto perdemos em vendas? | Perdas no E-commerce → cartão *Receita Perdida* | "quanto perdemos em vendas", "qual a receita perdida", "valor de pedidos cancelados", "perda com cancelamento e indisponibilidade" | Ano |
| 6 | Qual o percentual de atraso? | Perdas no E-commerce → cartão *% Pedidos Atrasados* | "qual o percentual de atraso", "quantos pedidos chegaram atrasados", "nível de serviço de entrega", "taxa de atraso" | Ano |
| 7 | Onde mais atrasa? | Perdas no E-commerce → barras *% de pedidos atrasados por UF* | "onde mais atrasa", "atraso por estado", "quais estados têm mais atraso", "UF com mais atraso" | Ano |

A pergunta "por que tal anomalia aconteceu" **não** vira verified answer: a resposta muda por anomalia e vem da coluna Hipótese de Causa (Copilot) ou do lakehouse (Data Agent).
