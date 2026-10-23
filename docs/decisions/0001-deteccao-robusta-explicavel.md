# 0001 Detecção por linha de base robusta por segmento, não por modelo caixa-preta

**Status:** aceita · **Data:** 2026-10-23

## Contexto

A série *Além do Dashboard* (Caso 01) propõe detectar perdas fora do padrão antes do fechamento do mês. O exemplo do post usa `IsolationForest`. Aqui o alerta vai para um gestor que precisa entender, em uma linha, **por que** aquilo é anomalia, e a mesma explicação alimenta a IA generativa e o agente.

Volume por célula é pequeno: uma categoria ou um vendedor tem de 15 a algumas centenas de itens por semana. Taxas de perda ficam perto de zero na maior parte das semanas e explodem em poucas.

## Decisão

Três monitores declarados no código (`MONITORS` no `nb_ai_detect_loss_anomalies`), cada um com a mesma regra:

- Taxa da semana por segmento (categoria, UF do cliente, vendedor).
- **Linha de base = mediana das 8 semanas anteriores do próprio segmento**, só com semanas de pelo menos 5 itens e que **não foram anomalia**.
- **Escore robusto** = (taxa − mediana) / (1,4826 × MAD), com piso de desvio por monitor (1 p.p. para venda perdida, 3 p.p. para atraso).
- Anomalia quando escore ≥ 3,5 **e** taxa ≥ fator mínimo × linha de base **e** impacto estimado ≥ mínimo do monitor **e** volume mínimo.
- Impacto = (taxa − linha de base) × valor bruto da semana; prioridade pelo impacto (Alta ≥ R$ 5 mil, Média ≥ R$ 2 mil).

## Por quê

- **Explicável em uma frase:** "24,9% contra 3,9% nas 8 semanas anteriores, 6,3x". Um score de `IsolationForest` não diz isso.
- **Mediana e MAD** não se deixam levar por uma semana extrema, ao contrário de média e desvio padrão.
- **Piso de desvio:** segmento com histórico zerado teria MAD = 0 e qualquer item perdido viraria alerta.
- **Quatro condições juntas:** estatística sozinha alerta segmentos minúsculos; impacto sozinho alerta segmentos grandes em semanas normais. O gestor só recebe o que é ao mesmo tempo improvável e caro.
- **Excluir semanas anômalas da linha de base** veio do primeiro replay: sem isso, a onda de atraso do RJ em dez/2017-jan/2018 subiu a mediana e escondeu a segunda onda, em mar/2018 (35% de itens atrasados contra ~6% normal). Com a exclusão, as duas são detectadas.

## Consequências

- Replay sobre o Olist inteiro: 30 anomalias em dois anos (4 de venda perdida, 13 de atraso por UF, 13 de atraso por vendedor), 10 de prioridade Alta. Volume que um time consegue tratar.
- Depois de 8 semanas seguidas em anomalia o segmento fica sem linha de base e para de alertar; o novo nível vira o padrão. É intencional (um problema crônico vai para o painel, não para alerta semanal), e está documentado em [`../anomaly-detection.md`](../anomaly-detection.md).
- Sem sazonalidade: Black Friday e Natal aparecem como anomalia. Para o Olist isso é desejado (os atrasos de dez/2017 foram reais); num varejo com sazonalidade forte, a linha de base passaria a ser a mesma semana do ano anterior.
- `IsolationForest` fica como evolução para combinar sinais (perda, atraso e nota ao mesmo tempo), mantendo a regra atual como explicação.
