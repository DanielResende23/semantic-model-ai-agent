# 0005 Data Agent como código, com regras no modelo e teste de regressão

**Status:** aceita · **Data:** 2026-10-23

## Contexto

Gestores querem perguntar "por que MG estourou o atraso?" sem abrir relatório. O Fabric Data Agent responde em linguagem natural sobre modelos semânticos e lakehouses. Configurado só pelo portal, ele vira uma caixa que ninguém sabe reproduzir nem testar.

## Decisão

- Agente `da_prevencao_perdas` criado, configurado e publicado pelo **Fabric Data Agent SDK** no `nb_ai_setup_data_agent`: instruções, fontes, tabelas e exemplos de SQL versionados no Git.
- Duas fontes com papéis claros: **modelo semântico** para KPIs e contagem/impacto de anomalias; **lakehouse `lh_ai`** para evidências, linha de base semana a semana e responsáveis.
- **Regras de negócio no modelo** (descrições, AI instructions, verified answers em [`ai/`](../../ai)): na fonte semântica, o agente gera DAX só com os metadados do modelo e o Prep data for AI, e ignora instruções escritas no agente. No agente fica só persona, escolha de fonte e forma da resposta.
- **Teste de regressão** no `nb_ai_evaluate_data_agent`: 12 perguntas com resposta esperada, resultado gravado no `lh_ai`, falha abaixo de 80% de acerto. Roda antes de promover para PRD.

## Consequências

- O mesmo modelo serve Copilot, Data Agent e relatório com as mesmas definições.
- O SDK está em preview; se a API mudar, o ajuste fica concentrado em um notebook.
- Exige capacidade F2 ou superior paga e o Data Agent habilitado no tenant.
