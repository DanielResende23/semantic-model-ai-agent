# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_ai_setup_data_agent
# **Agente como código.** Cria (ou atualiza) o Fabric Data Agent `da_prevencao_perdas` com o
# [Fabric Data Agent SDK](https://learn.microsoft.com/fabric/data-science/fabric-data-agent-sdk) e publica.
# A configuração inteira está nas células abaixo e é revisada por pull request; o portal fica só para testar.
#
# | Fonte | Para quê | Onde ficam as regras |
# |---|---|---|
# | Modelo semântico `Olist Prevenção de Perdas` | KPIs (receita perdida, atraso, nota) e contagem/impacto de anomalias | No **modelo**: descrições + Prep data for AI (`ai/`). O agente gera DAX só com os metadados do modelo; instrução escrita no agente não muda o DAX |
# | Lakehouse `lh_ai` (schema `loss`) | Evidências, linha de base semana a semana, responsáveis, histórico de uma anomalia | Instruções da fonte + exemplos de SQL (few-shots) abaixo |
#
# Requer capacidade F2 ou superior paga, Data Agent habilitado no tenant e o pipeline `pl_daily_loss_alerts` executado
# ao menos uma vez (as tabelas `loss.*` precisam existir). O SDK está em preview: se um nome de método mudar,
# o ajuste fica concentrado aqui.

# PARAMETERS CELL ********************

agent_name = "da_prevencao_perdas"
semantic_model_name = "Olist Prevenção de Perdas"
lakehouse_name = "lh_ai"
publish = True

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

# MARKDOWN ********************

# ## Instruções do agente
# Persona, roteamento entre as fontes e forma da resposta. Regras de negócio (o que é perda, qual medida usar)
# ficam no modelo, para valerem também para o Copilot.

# CELL ********************

AGENT_INSTRUCTIONS = """Você é o assistente de prevenção de perdas do marketplace Olist. Responde gestores de categoria,
logística e sucesso do seller, em português do Brasil, sobre vendas perdidas, atrasos de entrega e as anomalias de perda
detectadas toda semana.

Escolha da fonte:
- Indicadores (receita bruta, receita perdida, % de pedidos atrasados, nota média, ticket) por período, categoria, UF,
  região ou vendedor: use o modelo semântico Olist Prevenção de Perdas.
- Quantidade, impacto estimado e prioridade de anomalias por período, monitor ou responsável: use o modelo semântico
  (tabela Anomalias de Perda).
- "Por que" uma anomalia aconteceu, evidências, hipótese de causa, ação recomendada, linha de base semana a semana,
  responsável e e-mail: use o lakehouse lh_ai, schema loss.

Como responder:
- Comece pela resposta direta (número ou lista curta), depois o contexto em até 3 frases.
- Ao falar de uma anomalia, cite monitor, segmento, semana, taxa observada x linha de base, impacto estimado e prioridade.
- A hipótese de causa foi gerada por IA a partir das evidências: apresente como "hipótese provável", nunca como causa
  confirmada, e diga que a validação é do responsável. Se ai_status_code for Regra, diga que o texto veio da regra.
- Valores em R$ com duas casas; percentuais com uma casa.
- Os dados vão de set/2016 a out/2018; "esta semana" ou "agora" significa a semana mais recente com dados.
- Não invente dados que não estejam nas fontes. Se a pergunta pedir algo que não existe (custo, margem, estoque),
  diga isso e sugira o indicador mais próximo."""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Fonte lakehouse: tabelas, instruções e exemplos de SQL

# CELL ********************

LAKEHOUSE_TABLES = [
    ("loss", "fact_loss_anomaly"),
    ("loss", "fact_loss_monitor_week"),
    ("loss", "dim_loss_monitor"),
    ("loss", "dim_loss_owner"),
]

LAKEHOUSE_INSTRUCTIONS = """Schema loss do lh_ai.
- loss.fact_loss_anomaly: uma linha por anomalia (monitor_code + segment_code + week_start_date). Colunas-chave:
  monitor_name, segment_name (categoria, UF do cliente ou 'Vendedor ' + 8 caracteres), week_start_date (segunda-feira),
  observed_rate e baseline_rate (frações de 0 a 1), rate_factor, impact_amount (BRL), priority_name (Alta, Média, Baixa),
  alert_status_name (Nova, Recorrente), main_signal_name, evidence_text, ai_hypothesis_text, ai_action_text,
  ai_confidence_name, ai_status_code (Gerada, Regra, Pendente), owner_area_name, owner_name, owner_email,
  is_alert_pending (1 = alerta enviado no último lote).
- loss.fact_loss_monitor_week: todas as semanas avaliadas por monitor e segmento, inclusive as normais (is_anomaly = 0).
  Use para linha de base, tendência e "como estava antes".
- loss.dim_loss_owner: responsável por monitor; route_key é a região do cliente no M02 e '*' nos demais.
- Monitores: M01 Receita perdida por categoria, M02 Atraso de entrega por UF do cliente, M03 Atraso de entrega por vendedor.
- Para filtrar por UF use segment_name = 'MG'; para vendedor use segment_name LIKE 'Vendedor 88460e8e%'.
- Taxas são frações: multiplique por 100 ao mostrar percentual.
- Ordene anomalias por priority_rank e depois impact_amount desc."""

FEWSHOTS = {
    "Quais anomalias de perda estão pendentes de alerta agora?":
        """SELECT monitor_name, segment_name, week_start_date, observed_rate, baseline_rate, impact_amount,
       priority_name, main_signal_name, owner_name
FROM loss.fact_loss_anomaly
WHERE is_alert_pending = 1
ORDER BY priority_rank, impact_amount DESC""",
    "Por que MG entrou em anomalia de atraso na semana de 02/04/2018?":
        """SELECT segment_name, week_start_date, observed_rate, baseline_rate, rate_factor, impact_amount,
       main_signal_name, evidence_text, ai_hypothesis_text, ai_action_text, ai_confidence_name, ai_status_code
FROM loss.fact_loss_anomaly
WHERE monitor_code = 'M02' AND segment_name = 'MG' AND week_start_date = '2018-04-02'""",
    "Como estava o atraso em MG nas semanas antes da anomalia de abril de 2018?":
        """SELECT week_start_date, item_count, hit_count, observed_rate, baseline_rate, robust_z, is_anomaly
FROM loss.fact_loss_monitor_week
WHERE monitor_code = 'M02' AND segment_code = 'MG'
  AND week_start_date BETWEEN '2018-01-29' AND '2018-04-30'
ORDER BY week_start_date""",
    "Quais vendedores tiveram mais de uma anomalia de atraso?":
        """SELECT segment_name, COUNT(*) AS anomalias, SUM(impact_amount) AS impacto_estimado,
       MIN(week_start_date) AS primeira_semana, MAX(week_start_date) AS ultima_semana
FROM loss.fact_loss_anomaly
WHERE monitor_code = 'M03'
GROUP BY segment_name
HAVING COUNT(*) > 1
ORDER BY anomalias DESC, impacto_estimado DESC""",
    "Quais são as 5 anomalias de maior impacto e qual a ação recomendada para cada uma?":
        """SELECT TOP 5 monitor_name, segment_name, week_start_date, impact_amount, priority_name,
       ai_action_text, owner_name
FROM loss.fact_loss_anomaly
ORDER BY impact_amount DESC""",
    "Quem é o responsável pelos alertas de atraso no Nordeste?":
        """SELECT owner_area_name, owner_name, owner_email
FROM loss.dim_loss_owner
WHERE monitor_code = 'M02' AND route_key = 'Nordeste'""",
    "Em quantas anomalias a postagem do vendedor fora do prazo foi o sinal principal?":
        """SELECT main_signal_name, COUNT(*) AS anomalias, SUM(impact_amount) AS impacto_estimado
FROM loss.fact_loss_anomaly
GROUP BY main_signal_name
ORDER BY anomalias DESC""",
}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Criar ou atualizar e publicar

# CELL ********************

from fabric.dataagent.client import FabricDataAgentManagement, create_data_agent

try:
    agent = FabricDataAgentManagement(agent_name)
    print(f"Atualizando {agent_name}")
except Exception:
    agent = create_data_agent(agent_name)
    print(f"Criado {agent_name}")

agent.update_configuration(instructions=AGENT_INSTRUCTIONS)


def datasource(name: str, type_: str):
    """Reaproveita a fonte se já existir; o SDK não deduplica por nome."""
    for ds in agent.get_datasources():
        if name in str(ds.get_configuration()):
            return ds
    return agent.add_datasource(name, type=type_)


model_source = datasource(semantic_model_name, "semantic_model")
# Recorte de tabelas do modelo vem do AI data schema (Prep data for AI); nenhuma instrução aqui, ver markdown acima.

lakehouse_source = datasource(lakehouse_name, "lakehouse")
for schema, table in LAKEHOUSE_TABLES:
    lakehouse_source.select(schema, table)
lakehouse_source.update_configuration(instructions=LAKEHOUSE_INSTRUCTIONS)

existing = lakehouse_source.get_fewshots()
known = set(existing["Question"]) if hasattr(existing, "columns") and "Question" in existing.columns else set()
lakehouse_source.add_fewshots({q: sql for q, sql in FEWSHOTS.items() if q not in known})

if publish:
    agent.publish()
    print(f"{agent_name} publicado")
agent.get_configuration()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
