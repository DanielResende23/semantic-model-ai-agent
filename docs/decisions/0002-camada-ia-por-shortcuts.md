# 0002 Camada de IA em workspace próprio, lendo a Gold por shortcuts

**Status:** aceita · **Data:** 2026-10-23

## Contexto

O projeto [Lakehouse Medallion](https://github.com/danielresende23/fabric-lakehouse-medallion) já entrega a Gold (`lh_gold.commercial`, `lh_gold.shared`) e o modelo `Olist Vendas e Perdas`. Este projeto acrescenta detecção, IA generativa, agente e alerta. A Git integration do Fabric liga um workspace a uma pasta de um repositório.

## Decisão

- Workspace próprio (`Olist - Prevenção de Perdas [DEV]`), ligado à pasta `/fabric` deste repositório.
- Lakehouse `lh_ai` com **schema shortcuts** do OneLake para o workspace do projeto 1: `commercial` e `shared` (Gold) e `silver_commercial` (Silver), criados pelo `nb_ai_setup_shortcuts` a partir do **nome** do workspace de origem.
- Saídas no schema `loss` do `lh_ai`. O modelo `Olist Prevenção de Perdas` é uma cópia estendida do modelo do projeto 1, com uma única expressão Direct Lake (`OneLake_AI`) apontando para o `lh_ai`.

## Por quê

- **Zero cópia e um contrato só:** a camada de IA lê a mesma Gold que o relatório do projeto 1; se a regra de perda mudar lá, muda aqui.
- **Ciclos de vida separados:** monitores, prompts e agente mudam toda semana no começo; a engenharia de dados não. Repositórios e workspaces separados mantêm os deployment pipelines independentes.
- **Shortcut por notebook, não em `shortcuts.metadata.json`:** o destino tem GUIDs do workspace de origem, diferentes em DEV, TST e PRD. Resolver por nome em tempo de execução segue o mesmo princípio do projeto 1 (nenhum GUID fixo no código).
- **Uma expressão no modelo:** o Data Agent, o Copilot e o relatório enxergam a Gold e as anomalias pelo mesmo lakehouse.

## Exceção registrada

`silver_commercial` existe só para uma evidência: se o vendedor postou o item depois do prazo limite (`shipping_limit_ts` x `delivered_carrier_ts`). Essa informação não chegou à Gold no projeto 1 e é o sinal que separa atraso do vendedor de atraso do transporte. O caminho certo é promover a coluna para `fact_sales` no projeto 1 e remover este shortcut; fica como evolução.
