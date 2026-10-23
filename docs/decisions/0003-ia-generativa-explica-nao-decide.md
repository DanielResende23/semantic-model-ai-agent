# 0003 IA generativa explica e sugere; a regra decide o que é anomalia

**Status:** aceita · **Data:** 2026-10-23

## Contexto

O Caso 01 pede uma hipótese de causa "em linguagem de negócio" e uma ação recomendada para cada anomalia. Um LLM escreve bem, mas pode inventar números, tratar hipótese como fato ou cair no meio do pipeline.

## Decisão

- **Fabric AI functions** (`ai.generate_response` sobre pandas, no `nb_ai_explain_anomalies`), com o Azure OpenAI embutido na capacidade: sem chave, sem recurso extra, cobrança na capacidade.
- O LLM **não decide nada**: quem marca a anomalia, a prioridade e o responsável é a regra (ADR 0001). O LLM só recebe os fatos já calculados (taxa, linha de base, impacto, sinal principal, evidências) e devolve JSON com hipótese, ação e confiança.
- **Sinal principal por regra** (ex.: "Postagem do vendedor fora do prazo" quando 50% ou mais dos itens atrasados saíram depois do prazo limite). Ancora a hipótese e é o texto de reserva.
- **Validação da saída:** JSON parseável, campos obrigatórios, tamanho, confiança em Alta/Média/Baixa. Falhou ou a capacidade não tem AI functions: texto por regra, `ai_status_code = Regra`, e o pipeline segue.
- `temperature = 0`, versão do prompt e modelo gravados por linha; o texto de cada anomalia só é regenerado se estiver `Pendente` ou `Regra` (ou com `regenerate_all`).
- Tudo que chega ao gestor diz que a hipótese foi gerada por IA e precisa de validação.

## Alternativas

| Opção | Por que não agora |
|---|---|
| Azure OpenAI próprio, chave no Key Vault | Mais um recurso e um segredo para gerenciar; vale quando o modelo da capacidade não servir |
| AI Builder no Power Automate | Explicação ficaria fora do lakehouse: Copilot, agente e relatório não a veriam; consumo de créditos por alerta |
| LLM decidindo o que é anomalia | Não auditável, não reproduzível, custo por linha avaliada (milhares por semana) |

## Consequências

- Custo previsível: uma chamada por anomalia nova (dezenas por mês), não por linha de dado.
- Sem a IA o produto continua funcionando, com texto mais genérico. A diferença entre os dois textos é a medida de valor da IA.
- Próximo passo natural: o gestor confirma ou descarta a hipótese no card do Teams e o retorno vira rótulo para avaliar o prompt.
