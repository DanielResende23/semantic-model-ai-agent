# AI data schema

Recorte para **Prep data for AI → Simplify the data schema**. Ocultar no modelo não é o mesmo que tirar do schema: o recorte abaixo é aplicado explicitamente.

Montado a partir dos KPIs prioritários (receita perdida, atraso, nota e anomalias) e das dependências de cada medida: toda coluna usada por uma medida incluída também entra, mesmo oculta.

| Objeto | Decisão | Motivo |
|---|---|---|
| **Anomalias de Perda**: todas as medidas e colunas visíveis | Incluir | Núcleo do caso de uso |
| Anomalias de Perda: `Valor do Impacto Estimado`, `Ordem da Prioridade` (ocultas) | Incluir | Dependências de `Impacto Estimado das Anomalias` e da ordenação por prioridade |
| Anomalias de Perda: `Código da Anomalia`, `Escore Robusto` | Incluir | Citar uma anomalia; explicar por que virou anomalia |
| Anomalias de Perda: `E-mail do Responsável`, `Pendente de Alerta`, `Código do Monitor`, `Código do Segmento` | Excluir | Uso do fluxo de alerta e de auditoria, não de pergunta |
| **Vendas**: medidas de receita, perda, atraso por item, AA/MA/YTD | Incluir | KPIs principais |
| Vendas: colunas ocultas `Valor Bruto`, `Valor do Item`, `Valor do Frete`, `Pedido Perdido`, `Entrega Atrasada`, `Entregue`, `Código do Pedido` | Incluir | Dependências das medidas |
| **Pedidos**: medidas de pedidos, atraso, prazo, nota, AA | Incluir | KPIs de nível de serviço e satisfação |
| Pedidos: `Nota da Avaliação`, `Código do Pedido` e as colunas ocultas usadas pelas medidas (`Entregue`, `Entrega Atrasada`, `Pedido Perdido`, `Dias de Atraso`, `Dias até a Entrega`, `Avaliado`, `Avaliação Negativa`) | Incluir | Dependências |
| Pedidos: `Valor dos Itens`, `Valor do Frete do Pedido`, `Valor do Pedido`, `Valor Pago no Pedido`, `Avaliação com Comentário` | Excluir | Sem medida que dependa delas; valores já cobertos por Vendas |
| **Pagamentos** e **Forma de Pagamento** | Incluir só `Valor Pago`, `% Pago com Cartão de Crédito`, as colunas ocultas `Valor do Pagamento` e `Forma de Pagamento[payment_type_code]` (filtro da medida de cartão) e `Forma de Pagamento[Forma de Pagamento]` | Fora do caso de perdas; mantido o mínimo com as dependências |
| **Calendário**: `Data`, `Ano`, `Trimestre`, `Mês`, `Ano-Mês`, `Dia da Semana` | Incluir | Perguntas por período |
| Calendário: `Mês Abreviado`, `Fim de Semana` | Excluir | Redundantes para pergunta |
| **Cliente**: `UF do Cliente`, `Estado do Cliente`, `Região do Cliente`, `Cidade do Cliente`, `Código Único do Cliente` | Incluir | Recortes geográficos e contagem de clientes |
| Cliente: `CEP do Cliente`, `Latitude/Longitude do Cliente` | Excluir | Só para mapa |
| **Vendedor**: `Código do Vendedor`, `UF do Vendedor`, `Estado do Vendedor`, `Região do Vendedor`, `Cidade do Vendedor` | Incluir | Ranking de vendedores |
| Vendedor: CEP, latitude e longitude | Excluir | Só para mapa |
| **Produto**: `Categoria`, `Categoria em Inglês` | Incluir | Recorte por categoria |
| Produto: `Código do Produto`, `Fotos do Anúncio`, `Peso (g)` | Excluir | Sem pergunta de negócio no escopo |
| **Status do Pedido**: `Status do Pedido`, `Grupo do Status` | Incluir | "Cancelados", "em andamento" |

Rodar [`test-questions.md`](test-questions.md) depois de mudar o recorte: se uma pergunta passa a falhar por campo ausente, a dependência faltou aqui.
