# Sinônimos

Termos que gestores usam para cada objeto. Estão em três lugares, do mais para o menos garantido:

1. **Descrição do objeto** no TMDL (primeiros 200 caracteres, que é o que o Copilot lê): os termos principais já estão lá, por exemplo `Qtd Anomalias` → "alertas, desvios, ocorrências fora do padrão".
2. **Glossário das AI instructions** ([`ai-instructions.md`](ai-instructions.md)): vale para o Copilot e para o Data Agent em qualquer idioma de cultura.
3. **Q&A setup → Synonyms** no Desktop: aplicar a lista abaixo quando a cultura do modelo tiver suporte a Q&A. O modelo é pt-BR e o Q&A em português tem suporte limitado, por isso os itens 1 e 2 vêm primeiro. Não escrevo o `linguisticMetadata` à mão no TMDL: formato não documentado, e um JSON inválido quebra o sync do Git.

| Objeto | Sinônimos |
|---|---|
| `Vendas[Receita Bruta]` | vendas, faturamento, GMV, receita total |
| `Vendas[Receita Perdida]` | perda, venda perdida, receita cancelada, quanto perdemos |
| `Vendas[% Receita Perdida]` | taxa de perda, índice de perda, perda sobre venda |
| `Pedidos[% Pedidos Atrasados]` | atraso, entrega fora do prazo, nível de serviço, taxa de atraso |
| `Vendas[% Itens Atrasados]` | atraso por vendedor, atraso por categoria, atraso do seller |
| `Pedidos[Nota Média de Avaliação]` | satisfação, nota, avaliação, review |
| `Vendedor` | lojista, seller, parceiro, loja |
| `Produto[Categoria]` | departamento, linha, categoria de produto |
| `Anomalias de Perda` | alertas, desvios, ocorrências, casos fora do padrão |
| `Anomalias de Perda[Qtd Anomalias]` | quantos alertas, número de anomalias, quantas ocorrências |
| `Anomalias de Perda[Anomalias de Alta Prioridade]` | alertas críticos, urgentes, prioridade alta |
| `Anomalias de Perda[Impacto Estimado das Anomalias]` | impacto, custo da anomalia, perda acima do normal, perda evitável |
| `Anomalias de Perda[Linha de Base]` | padrão, normal, média histórica, esperado |
| `Anomalias de Perda[Fator sobre o Padrão]` | quantas vezes acima, múltiplo do padrão |
| `Anomalias de Perda[Hipótese de Causa]` | causa, motivo, por quê, causa provável |
| `Anomalias de Perda[Ação Recomendada]` | o que fazer, próximo passo, recomendação, plano de ação |
| `Anomalias de Perda[Responsável]` | dono, quem trata, gestor responsável |
| `Anomalias de Perda[Segmento]` | onde, qual categoria, qual estado, qual vendedor |
| `Anomalias de Perda[Sinal Principal]` | principal evidência, sinal, indício |
