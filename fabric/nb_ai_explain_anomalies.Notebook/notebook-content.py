# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_ai_explain_anomalies
# **Explicar e orientar a ação.** Para cada anomalia ainda sem hipótese, as **Fabric AI functions**
# (`ai.generate_response`, Azure OpenAI embutido na capacidade, sem chave para gerenciar) recebem só os fatos já
# calculados (monitor, taxa x padrão, impacto, sinal principal e evidências) e devolvem, em JSON:
# hipótese de causa, ação recomendada e confiança.
#
# Guardrails (ADR 0003):
# - A IA **não vê dados brutos** nem identifica clientes; o vendedor aparece só pelo prefixo do código anonimizado.
# - A resposta precisa citar o sinal principal e ser coerente com as evidências; o prompt proíbe tratar hipótese
#   como causa confirmada e inventar dados que não estão no contexto.
# - Saída validada (JSON, campos obrigatórios, tamanho, confiança em Alta/Média/Baixa). Resposta inválida ou IA
#   indisponível **não para o pipeline**: o texto cai para um modelo por regra a partir do sinal principal
#   (`ai_status_code = Regra`), e o alerta sai do mesmo jeito.
# - Versão do prompt e modelo gravados em cada linha para auditoria; `temperature = 0`.
#
# Requer capacidade F2 ou superior paga (AI functions não rodam em trial) e Fabric Runtime 1.3+.

# PARAMETERS CELL ********************

batch_id = ""
max_rows = 50
regenerate_all = False

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

%run nb_ai_utils

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import json

import pandas as pd

NOTEBOOK_NAME = "nb_ai_explain_anomalies"
PROMPT_VERSION = "loss-hypothesis-v1"
batch_id = new_batch_id(batch_id)
started_ts = datetime.now(timezone.utc)

anomalies = read_table("loss", "fact_loss_anomaly")
todo_filter = F.lit(True) if regenerate_all else F.col("ai_status_code").isin("Pendente", "Regra")
todo = (
    anomalies.where(todo_filter)
    .orderBy(F.desc("is_alert_pending"), "priority_rank", F.desc("impact_amount"))
    .limit(int(max_rows))
    .select("anomaly_id", "monitor_name", "loss_type_name", "dimension_name", "segment_name", "week_start_date",
            "observed_rate", "baseline_rate", "rate_factor", "impact_amount", "priority_name", "main_signal_name",
            "evidence_text")
    .toPandas()
)
print(f"{len(todo)} anomalias para explicar")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Prompt
# Template com placeholders `{coluna}`, preenchido linha a linha pelas AI functions (`is_prompt_template=True`).
# Fora dos placeholders o texto não usa chaves, para não depender de como o template trata `{` literal.

# CELL ********************

PROMPT = """Você é analista sênior de prevenção de perdas de um marketplace de e-commerce brasileiro.
Uma regra estatística detectou a anomalia abaixo. Escreva para o gestor responsável, em português do Brasil.

Monitor: {monitor_name}
Tipo de perda: {loss_type_name}
{dimension_name}: {segment_name}
Semana iniciada em: {week_label}
Taxa observada: {observed_label} | linha de base (mediana das 8 semanas anteriores): {baseline_label} | {factor_label}
Impacto estimado acima do padrão: {impact_label} | prioridade {priority_name}
Sinal principal calculado por regra: {main_signal_name}
Evidências: {evidence_text}

Regras:
- Use apenas os fatos acima. Não invente números, nomes, eventos ou dados que não estão no contexto.
- A hipótese é uma causa provável, não confirmada: escreva "provável" ou "indica" e cite pelo menos um número das evidências.
- A hipótese deve ser coerente com o sinal principal; se as evidências forem fracas, diga isso e use confiança Baixa.
- A ação deve ser concreta, executável pelo responsável nesta semana, e dizer o que conferir para validar a hipótese.
- Hipótese com no máximo 300 caracteres; ação com no máximo 300 caracteres.

Responda somente com um objeto JSON, sem texto fora dele, com três chaves de texto: "hipotese",
"acao_recomendada" e "confianca" (valor Alta, Média ou Baixa)."""


def brl(value) -> str:
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value) -> str:
    return f"{float(value) * 100:.1f}%".replace(".", ",")


todo["week_label"] = pd.to_datetime(todo["week_start_date"]).dt.strftime("%d/%m/%Y")
todo["observed_label"] = todo["observed_rate"].map(pct)
todo["baseline_label"] = todo["baseline_rate"].map(pct)
todo["factor_label"] = todo["rate_factor"].map(
    lambda f: "sem perda nas semanas anteriores" if pd.isna(f) else f"{f:.1f}x o padrão".replace(".", ",")
)
todo["impact_label"] = todo["impact_amount"].map(brl)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Geração com Fabric AI functions

# CELL ********************

AI_MODEL = "gpt-4.1-mini"
ai_error = None

if len(todo):
    try:
        import synapse.ml.aifunc as aifunc

        aifunc.default_conf.model_deployment_name = AI_MODEL
        aifunc.default_conf.temperature = 0.0
        todo["ai_raw"] = todo.ai.generate_response(PROMPT, is_prompt_template=True)
    except Exception as error:  # capacidade sem AI functions, limite de taxa, etc.: segue com o texto por regra
        ai_error = f"{type(error).__name__}: {error}"
        print(f"AI functions indisponíveis, usando texto por regra. {ai_error}")
        todo["ai_raw"] = None

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Validação e texto por regra
# O texto por regra é a mesma recomendação que um analista daria só olhando o sinal principal. Ele garante que todo
# alerta tenha uma ação, e serve de base de comparação para a qualidade da IA (ver `docs/anomaly-detection.md`).

# CELL ********************

RULE_TEXT = {
    "Postagem do vendedor fora do prazo": (
        "Provável atraso na postagem pelos vendedores: boa parte dos itens atrasados saiu depois do prazo limite.",
        "Cobrar dos vendedores com mais itens atrasados o plano de postagem e revisar o prazo de manuseio prometido.",
    ),
    "Atraso no transporte": (
        "Provável gargalo no transporte até o destino: a maior parte dos itens foi postada no prazo e chegou atrasada.",
        "Abrir chamado com as transportadoras da rota, conferir rastreios da semana e ajustar o prazo prometido na região.",
    ),
    "Concentrado em um vendedor": (
        "Provável problema operacional de um vendedor que concentra a perda do segmento.",
        "Contatar o vendedor, confirmar estoque e capacidade de envio e suspender temporariamente anúncios se repetir.",
    ),
    "Cancelamentos": (
        "Provável aumento de cancelamentos na categoria (preço, prazo ou fraude), não falta de estoque.",
        "Revisar motivos de cancelamento dos pedidos da semana e checar mudanças de preço ou prazo nos anúncios.",
    ),
    "Indisponibilidade de estoque": (
        "Provável ruptura: pedidos vendidos sem estoque disponível no vendedor.",
        "Conferir a sincronização de estoque dos principais vendedores da categoria e bloquear anúncios sem saldo.",
    ),
    "Cancelamento e indisponibilidade": (
        "Perda dividida entre cancelamentos e indisponibilidade; sem causa dominante nas evidências.",
        "Separar os pedidos por motivo e tratar primeiro o grupo de maior valor.",
    ),
}
CONFIDENCE = {"alta": "Alta", "média": "Média", "media": "Média", "baixa": "Baixa"}


def parse(raw):
    """Devolve (hipótese, ação, confiança) ou None quando a resposta não segue o contrato."""
    if not isinstance(raw, str):
        return None
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except ValueError:
        return None
    # Aspas retas viram tipográficas: o texto é interpolado no JSON do card adaptativo pelo Power Automate.
    hypothesis = str(data.get("hipotese", "")).strip().replace('"', "”")
    action = str(data.get("acao_recomendada", "")).strip().replace('"', "”")
    confidence = CONFIDENCE.get(str(data.get("confianca", "")).strip().lower())
    if not (20 <= len(hypothesis) <= 400 and 20 <= len(action) <= 400 and confidence):
        return None
    return hypothesis, action, confidence


now = datetime.now(timezone.utc)
results = []
for row in todo.itertuples(index=False):
    parsed = parse(row.ai_raw)
    if parsed:
        hypothesis, action, confidence = parsed
        status, model = "Gerada", AI_MODEL
    else:
        hypothesis, action = RULE_TEXT[row.main_signal_name]
        confidence, status, model = "Baixa", "Regra", None
    results.append((row.anomaly_id, hypothesis, action, confidence, status, model, PROMPT_VERSION, now))

generated = sum(1 for r in results if r[4] == "Gerada")
print(f"Geradas pela IA: {generated} | por regra: {len(results) - generated}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Gravação
# `MERGE` por `anomaly_id`: só as colunas de IA mudam; o resto da linha é do `nb_ai_detect_loss_anomalies`.

# CELL ********************

if results:
    updates = spark.createDataFrame(
        results,
        "anomaly_id string, ai_hypothesis_text string, ai_action_text string, ai_confidence_name string, "
        "ai_status_code string, ai_model_name string, ai_prompt_version string, ai_generated_ts timestamp",
    )
    target = DeltaTable.forPath(spark, table_path("loss", "fact_loss_anomaly"))
    (
        target.alias("t")
        .merge(updates.alias("s"), "t.anomaly_id = s.anomaly_id")
        .whenMatchedUpdate(set={
            **{c: f"s.{c}" for c in updates.columns if c != "anomaly_id"},
            "dp_updated_ts": "current_timestamp()",
        })
        .execute()
    )

display(
    read_table("loss", "fact_loss_anomaly").where("is_alert_pending")
    .select("segment_name", "week_start_date", "main_signal_name", "ai_hypothesis_text", "ai_action_text",
            "ai_confidence_name", "ai_status_code")
)
log_run(batch_id, NOTEBOOK_NAME, "lh_ai.loss.fact_loss_anomaly", "succeeded", len(results), started_ts,
        f"geradas={generated}; regra={len(results) - generated}; prompt={PROMPT_VERSION}" + (f"; erro={ai_error}" if ai_error else ""))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

notebookutils.notebook.exit(batch_id)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
