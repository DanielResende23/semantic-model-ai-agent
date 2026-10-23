# 0004 Alerta pelo Power Automate, consultando o modelo semântico

**Status:** aceita · **Data:** 2026-10-23

## Contexto

A anomalia precisa chegar ao responsável certo no canal que ele já usa, uma única vez, com a hipótese e a ação. Opções avaliadas: Power Automate, Fabric Activator (Data Activator) e n8n (usado no post do Caso 01).

## Decisão

Fluxo agendado do Power Automate (07:30) que roda uma consulta DAX no modelo `Olist Prevenção de Perdas` e, para cada anomalia pendente de prioridade Alta ou Média, manda um card adaptativo no Teams e um e-mail ao responsável. Definição e passo a passo em [`automation/power-automate`](../../automation/power-automate).

## Por quê

- **Ecossistema do cliente:** Teams e Outlook já estão lá; conectores padrão, sem licença premium.
- **Regra no dado, não no fluxo:** `is_alert_pending` é calculado pelo notebook (nova no lote e da última semana completa). O fluxo é burro de propósito: consultar e entregar. Mudar a regra é pull request no notebook, não edição no designer.
- **Pelo modelo, não pelo lakehouse:** mesma segurança, mesmos nomes de negócio e mesmas regras que o Copilot e o relatório.
- **Idempotência:** cada anomalia fica pendente em um lote só; a janela de 24 h em `Detectada em` evita reenvio se o pipeline falhar num dia.

## Alternativas

| Opção | Quando usar |
|---|---|
| Fabric Activator | Alerta em tempo quase real sobre eventos (Eventstream/Eventhouse). Para um lote semanal, o agendamento é mais simples de testar e explicar |
| n8n | Fora do ecossistema Microsoft; boa escolha quando o canal é WhatsApp ou a empresa já usa n8n. O desenho é o mesmo do post: agenda, consulta, filtro, IA, mensagem |
| Atividades Teams/Outlook do Data Pipeline | Funcionam, mas misturam orquestração de dados com comunicação e não têm card adaptativo |
