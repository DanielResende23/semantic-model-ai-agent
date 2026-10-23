# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_ai_evaluate_data_agent
# **Teste de regressão do agente.** Roda o banco de perguntas com resposta esperada contra o Data Agent publicado e
# grava o resultado em `lh_ai` (`dbo.data_agent_evaluation*`), para comparar versões de instruções, few-shots e
# Prep data for AI. Rodar antes de cada promoção para PRD e depois de mudar o modelo ou o agente.
#
# Os valores esperados valem para o histórico completo do Olist: `pl_daily_loss_alerts` executado com
# `as_of_date = 2018-09-03` (última semana completa 27/08/2018). O banco completo, com as perguntas do Copilot,
# está em `ai/test-questions.md`.

# CELL ********************

%%configure -f
{
    "defaultLakehouse": { "name": "lh_ai" }
}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# PARAMETERS CELL ********************

agent_name = "da_prevencao_perdas"
agent_stage = "production"
output_table = "data_agent_evaluation"
min_accuracy = 0.8

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%pip install -q fabric-data-agent-sdk

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import pandas as pd
from fabric.dataagent.evaluation import evaluate_data_agent, get_evaluation_details, get_evaluation_summary

QUESTIONS = [
    ("Quantas anomalias de perda foram detectadas no total?", "30 anomalias"),
    ("Quantas anomalias de alta prioridade existem?", "10 anomalias de prioridade Alta"),
    ("Quantas anomalias cada monitor detectou?",
     "M01 Receita perdida por categoria: 4; M02 Atraso de entrega por UF do cliente: 13; M03 Atraso de entrega por vendedor: 13"),
    ("Qual foi a anomalia de maior impacto estimado?",
     "Atraso de entrega em SP na semana de 13/08/2018: 14,5% contra 1,1% de linha de base, impacto de cerca de R$ 18,1 mil"),
    ("Qual o impacto estimado somado das anomalias de 2018?", "Cerca de R$ 117 mil (21 anomalias)"),
    ("Quantas anomalias foram recorrentes?", "9 anomalias recorrentes (21 novas)"),
    ("Por que MG entrou em anomalia de atraso na semana de 02/04/2018?",
     "24,9% dos itens entregues com atraso contra 3,9% de linha de base (6,3x), 85 de 342 itens, atraso médio de 8,1 dias; "
     "a hipótese aponta atraso no transporte e é uma hipótese a validar"),
    ("Quais vendedores tiveram mais de uma anomalia de atraso?", "Vendedor 4a3ca931 (três) e Vendedor 7c67e144 (duas)"),
    ("Quais categorias tiveram anomalia de receita perdida?", "Cool Stuff (duas), Ferramentas Jardim e Eletronicos"),
    ("Em quais períodos o RJ ficou em anomalia de atraso?",
     "Duas ondas: cinco semanas de 18/12/2017 a 15/01/2018 e três semanas de 12/03 a 26/03/2018"),
    ("Quem recebe os alertas de atraso de entrega do Sudeste?", "Coordenação de Logística Sudeste, logistica.sudeste@contoso.com"),
    ("Qual a margem de lucro das categorias com anomalia?",
     "O modelo não tem margem nem custo; o agente deve dizer isso e oferecer receita perdida ou impacto estimado"),
]
questions = pd.DataFrame(QUESTIONS, columns=["question", "expected_answer"])

evaluation_id = evaluate_data_agent(
    questions, agent_name, table_name=output_table, data_agent_stage=agent_stage,
)
summary = get_evaluation_summary(output_table)
display(summary)
details = get_evaluation_details(evaluation_id, output_table, get_all_rows=True)
display(details)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Portão de qualidade
# Falha o notebook (e o pipeline de promoção que o chamar) se a acurácia ficar abaixo de `min_accuracy`.
# Cada pergunta errada vira correção no **modelo** (descrição, AI instructions, verified answer) ou no agente
# (instruções, few-shot), nunca só no texto da pergunta.

# CELL ********************

latest = summary[summary["evaluation_id"] == evaluation_id].iloc[0] if "evaluation_id" in summary.columns else summary.iloc[-1]
accuracy = float(latest.get("%", latest.get("accuracy", 0)))
accuracy = accuracy / 100 if accuracy > 1 else accuracy
print(f"Acurácia {accuracy:.0%} (mínimo {min_accuracy:.0%})")
if accuracy < min_accuracy:
    raise AssertionError(f"Data Agent abaixo do mínimo: {accuracy:.0%}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
