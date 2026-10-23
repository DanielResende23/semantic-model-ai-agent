# Imagens

| Arquivo | O que é | Origem |
|---|---|---|
| `deteccao-rj.png`, `deteccao-mg.png` | Atraso semanal x linha de base, com as anomalias marcadas | Replay local da regra sobre os CSVs do Olist |
| `alerta-teams-card.png` | Card adaptativo do Teams para a anomalia de MG (semana de 02/04/2018) | `automation/power-automate/samples/card-mg-2018-04-02.json` renderizado com o SDK de Adaptive Cards |
| `alerta-email.png` | E-mail ao responsável para a mesma anomalia | `email-template.html` preenchido com os mesmos dados |

Nos dois alertas, os números (taxa, linha de base, impacto, evidências) são os do replay; a hipótese e a ação são um exemplo no formato que o `nb_ai_explain_anomalies` devolve.

## Capturas pendentes (primeira execução no Fabric)

Exigem capacidade F2 ou superior paga (AI functions e Data Agent não rodam em trial):

1. `01-workspace-lineage.jpg`: workspace com `lh_ai`, notebooks, pipeline, modelo e relatório, sincronizado com a `main`.
2. `02-pipeline-run.jpg`: `pl_daily_loss_alerts` com `as_of_date = 2018-04-09`.
3. `03-central-anomalias.jpg`: página Central de Anomalias do relatório.
4. `04-data-agent.jpg`: Data Agent respondendo "Por que MG entrou em anomalia de atraso na semana de 02/04/2018?".
5. `05-copilot.jpg`: Copilot no relatório respondendo uma verified answer ("quais anomalias temos").
6. `06-teams-alert.jpg`: alerta real recebido no Teams.
