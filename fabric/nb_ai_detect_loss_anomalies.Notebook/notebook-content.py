# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_ai_detect_loss_anomalies
# **Detectar e priorizar.** Três monitores procuram semanas em que uma taxa de perda saiu do padrão do próprio segmento.
#
# | Monitor | Taxa | Segmento | Semana pela data | Volume mínimo |
# |---|---|---|---|---|
# | M01 Receita perdida por categoria | % da receita bruta em pedidos cancelados ou indisponíveis | Categoria | da compra | 30 itens |
# | M02 Atraso de entrega por UF do cliente | % dos itens entregues depois da data prevista | UF do cliente | da entrega | 30 itens entregues |
# | M03 Atraso de entrega por vendedor | idem | Vendedor | da entrega | 15 itens entregues |
#
# **Regra (ADR 0001).** Linha de base = mediana da taxa nas 8 semanas anteriores do segmento (semanas com pelo menos 5 itens
# e que não foram anomalia, mínimo de 4 semanas). Escore robusto = (taxa - mediana) / (1,4826 x MAD), com piso de desvio por monitor para que um
# histórico sem variação não transforme qualquer oscilação em alerta. Vira anomalia quando, ao mesmo tempo:
# escore >= 3,5, taxa >= fator mínimo x linha de base e impacto estimado >= mínimo do monitor.
#
# **Impacto estimado** = (taxa - linha de base) x valor bruto da semana: quanto a semana perdeu (ou expôs a atraso) acima do
# normal. **Prioridade**: Alta a partir de R$ 5 mil, Média a partir de R$ 2 mil.
#
# **Saídas** em `lh_ai.loss`:
# - `fact_loss_monitor_week`: toda combinação monitor x segmento x semana avaliada, com taxa, linha de base e escore.
# - `fact_loss_anomaly`: só as anomalias, com evidências, sinal principal e responsável. As colunas de IA são preenchidas
#   pelo `nb_ai_explain_anomalies` e preservadas entre execuções.
# - `dim_loss_monitor` e `dim_loss_owner`: configuração versionada aqui.
#
# **`as_of_date`** fixa "hoje": só entram semanas completas antes dessa data. Em produção fica vazio; para demonstrar com o
# Olist (2016-2018) informe uma data do período, por exemplo `2018-04-09` (ver roteiro de demonstração no README).

# PARAMETERS CELL ********************

batch_id = ""
as_of_date = ""

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

from datetime import date, timedelta

import numpy as np
import pandas as pd
from pyspark.sql.window import Window

NOTEBOOK_NAME = "nb_ai_detect_loss_anomalies"
batch_id = new_batch_id(batch_id)
started_ts = datetime.now(timezone.utc)

as_of = date.fromisoformat(as_of_date) if as_of_date.strip() else started_ts.date()
last_complete_week = as_of - timedelta(days=as_of.weekday() + 7)   # segunda-feira da última semana completa
print(f"Lote {batch_id} | data de referência {as_of} | última semana completa {last_complete_week}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Configuração
# Monitores e responsáveis ficam no código para serem revisados por pull request. Os e-mails são caixas fictícias
# (`contoso.com`); o fluxo do Power Automate permite mandar tudo para um destinatário de teste.

# CELL ********************

MONITORS = [
    dict(monitor_code="M01", monitor_name="Receita perdida por categoria", loss_type_name="Venda perdida",
         dimension_name="Categoria", segment_col="category_name", week_col="purchase_week_start",
         base_filter="true", hit_col="is_lost", rate_basis="amount",
         min_items=30, sigma_floor=0.01, min_factor=2.0, min_impact=1500.0),
    dict(monitor_code="M02", monitor_name="Atraso de entrega por UF do cliente", loss_type_name="Atraso de entrega",
         dimension_name="UF do Cliente", segment_col="customer_state_code", week_col="delivered_week_start",
         base_filter="is_delivered", hit_col="is_late", rate_basis="count",
         min_items=30, sigma_floor=0.03, min_factor=1.5, min_impact=3000.0),
    dict(monitor_code="M03", monitor_name="Atraso de entrega por vendedor", loss_type_name="Atraso de entrega",
         dimension_name="Vendedor", segment_col="seller_id", week_col="delivered_week_start",
         base_filter="is_delivered", hit_col="is_late", rate_basis="count",
         min_items=15, sigma_floor=0.03, min_factor=1.5, min_impact=1500.0),
]
BASELINE_WEEKS = 8
MIN_BASELINE_WEEKS = 4
MIN_BASELINE_ITEMS = 5
Z_THRESHOLD = 3.5
PRIORITIES = [("Alta", 1, 5000.0), ("Média", 2, 2000.0), ("Baixa", 3, 0.0)]

# (monitor, chave de roteamento ou "*", área, responsável, e-mail). M02 roteia pela região do cliente.
OWNERS = [
    ("M01", "*", "Comercial", "Gestão de Categorias", "categorias@contoso.com"),
    ("M02", "Sudeste", "Logística Sudeste", "Coordenação de Logística Sudeste", "logistica.sudeste@contoso.com"),
    ("M02", "Sul", "Logística Sul", "Coordenação de Logística Sul", "logistica.sul@contoso.com"),
    ("M02", "Nordeste", "Logística Nordeste", "Coordenação de Logística Nordeste", "logistica.nordeste@contoso.com"),
    ("M02", "Norte", "Logística Norte", "Coordenação de Logística Norte", "logistica.norte@contoso.com"),
    ("M02", "Centro-Oeste", "Logística Centro-Oeste", "Coordenação de Logística Centro-Oeste", "logistica.centrooeste@contoso.com"),
    ("M02", "*", "Logística", "Coordenação de Logística", "logistica@contoso.com"),
    ("M03", "*", "Gestão de Sellers", "Time de Sucesso do Seller", "sellers@contoso.com"),
]

monitor_columns = ["monitor_code", "monitor_name", "loss_type_name", "dimension_name", "rate_basis",
                   "min_items", "sigma_floor", "min_factor", "min_impact"]
dim_monitor = spark.createDataFrame(
    [tuple(m[c] for c in monitor_columns) for m in MONITORS],
    "monitor_code string, monitor_name string, loss_type_name string, dimension_name string, rate_basis string, "
    "min_items int, sigma_floor double, min_factor double, min_impact double",
).withColumn("z_threshold", F.lit(Z_THRESHOLD)).withColumn("baseline_weeks", F.lit(BASELINE_WEEKS))
dim_owner = spark.createDataFrame(
    OWNERS, "monitor_code string, route_key string, owner_area_name string, owner_name string, owner_email string",
)
overwrite_table(add_audit_columns(dim_monitor, batch_id), "loss", "dim_loss_monitor")
overwrite_table(add_audit_columns(dim_owner, batch_id), "loss", "dim_loss_owner")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Taxas semanais por segmento e linha de base

# CELL ********************

def score_segment(pdf: pd.DataFrame) -> pd.DataFrame:
    """Pontua as semanas de um monitor x segmento em ordem cronológica.

    A linha de base usa só semanas anteriores **que não foram anomalia**: sem isso, uma onda longa (RJ em dez/2017)
    contamina a mediana e esconde a onda seguinte (RJ em mar/2018). Depois de 8 semanas seguidas fora do padrão não
    sobra base suficiente, o segmento para de alertar e o novo nível passa a formar a linha de base.
    """
    pdf = pdf.sort_values("week_index").reset_index(drop=True)
    history = []   # (week_index, taxa) das semanas que podem formar linha de base
    scores = []
    for row in pdf.itertuples(index=False):
        window = [rate for week, rate in history if row.week_index - BASELINE_WEEKS <= week < row.week_index]
        baseline = mad = z = factor = impact = None
        is_anomaly = False
        if len(window) >= MIN_BASELINE_WEEKS:
            baseline = float(np.median(window))
            mad = float(np.median([abs(rate - baseline) for rate in window]))
            z = (row.observed_rate - baseline) / max(1.4826 * mad, row.sigma_floor)
            factor = row.observed_rate / baseline if baseline > 0 else None
            impact = (row.observed_rate - baseline) * row.amount
            is_anomaly = bool(
                row.item_count >= row.min_items and z >= Z_THRESHOLD
                and (factor is None or factor >= row.min_factor) and impact >= row.min_impact
            )
        if row.item_count >= MIN_BASELINE_ITEMS and not is_anomaly:
            history.append((row.week_index, row.observed_rate))
        scores.append((len(window), baseline, mad, z, factor, impact, is_anomaly))
    scored = pd.DataFrame(scores, columns=["baseline_week_count", "baseline_rate", "baseline_mad", "robust_z",
                                           "rate_factor", "impact_amount", "is_anomaly"])
    return pd.concat([pdf[CELL_COLUMNS], scored], axis=1)


CELL_COLUMNS = ["monitor_code", "segment_code", "segment_name", "route_key", "week_start_date", "week_index",
                "item_count", "hit_count", "amount", "hit_amount", "observed_rate"]
SCORED_SCHEMA = (
    "monitor_code string, segment_code string, segment_name string, route_key string, week_start_date date, "
    "week_index int, item_count long, hit_count long, amount double, hit_amount double, observed_rate double, "
    "baseline_week_count int, baseline_rate double, baseline_mad double, robust_z double, rate_factor double, "
    "impact_amount double, is_anomaly boolean"
)

events = build_item_events().cache()

cells = None
for m in MONITORS:
    hit = F.col(m["hit_col"])
    monitor_cells = (
        events
        .where(F.expr(m["base_filter"]) & F.col(m["week_col"]).isNotNull() & F.col(m["segment_col"]).isNotNull())
        .groupBy(F.col(m["segment_col"]).alias("segment_code"), F.col(m["week_col"]).alias("week_start_date"))
        .agg(
            F.count(F.lit(1)).alias("item_count"),
            F.sum(F.when(hit, 1).otherwise(0)).alias("hit_count"),
            F.sum("gross_amount").cast("double").alias("amount"),
            F.sum(F.when(hit, F.col("gross_amount")).otherwise(0)).cast("double").alias("hit_amount"),
            F.first("customer_region_name", ignorenulls=True).alias("customer_region_name"),
        )
        .withColumn("monitor_code", F.lit(m["monitor_code"]))
        .withColumn(
            "observed_rate",
            F.col("hit_amount") / F.col("amount") if m["rate_basis"] == "amount" else F.col("hit_count") / F.col("item_count"),
        )
        .withColumn("route_key", F.col("customer_region_name") if m["monitor_code"] == "M02" else F.lit("*"))
        .withColumn(
            "segment_name",
            F.concat(F.lit("Vendedor "), F.substring("segment_code", 1, 8)) if m["monitor_code"] == "M03" else F.col("segment_code"),
        )
        .drop("customer_region_name")
    )
    cells = monitor_cells if cells is None else cells.unionByName(monitor_cells)


monitor_week = (
    cells
    .where(F.col("week_start_date") <= F.lit(last_complete_week))
    .withColumn("week_index", (F.datediff("week_start_date", F.lit("2000-01-03")) / 7).cast("int"))
    .join(dim_monitor.select("monitor_code", "min_items", "sigma_floor", "min_factor", "min_impact"), "monitor_code")
    .groupBy("monitor_code", "segment_code")
    .applyInPandas(score_segment, SCORED_SCHEMA)
    .join(dim_monitor.select("monitor_code", "monitor_name", "loss_type_name", "dimension_name"), "monitor_code")
    .withColumn("impact_amount", F.col("impact_amount").cast("decimal(18,4)"))
    .withColumn("week_start_date_key", date_key(F.col("week_start_date")))
    .cache()
)

week_rows = overwrite_table(add_audit_columns(monitor_week, batch_id), "loss", "fact_loss_monitor_week")
print(f"fact_loss_monitor_week: {week_rows} combinações monitor x segmento x semana")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Evidências das anomalias
# Para cada anomalia, olha os itens com perda daquele segmento e semana: quem concentra (vendedor, UF do vendedor,
# categoria, UF do cliente), atraso médio, postagem fora do prazo, cancelado x indisponível e a nota da avaliação.
# São esses fatos que a IA recebe; ela não vê os dados brutos.

# CELL ********************

anomalies = monitor_week.where("is_anomaly").cache()

anomaly_items = None
for m in MONITORS:
    monitor_items = (
        events.where(F.expr(m["base_filter"]))
        .join(
            anomalies.where(F.col("monitor_code") == m["monitor_code"])
            .select("monitor_code", "segment_code", "week_start_date"),
            (F.col(m["segment_col"]) == F.col("segment_code")) & (F.col(m["week_col"]) == F.col("week_start_date")),
        )
        .withColumn("is_hit", F.col(m["hit_col"]))
    )
    anomaly_items = monitor_items if anomaly_items is None else anomaly_items.unionByName(monitor_items)

keys = ["monitor_code", "segment_code", "week_start_date"]
hits = anomaly_items.where("is_hit")


def top_share(column: str, prefix: str) -> DataFrame:
    """Membro mais frequente entre os itens com perda e a parcela que ele representa."""
    counts = hits.groupBy(*keys, column).count()
    ranked = counts.withColumn(
        "rank", F.row_number().over(Window.partitionBy(*keys).orderBy(F.desc("count"), F.asc(column)))
    ).withColumn("share", F.col("count") / F.sum("count").over(Window.partitionBy(*keys)))
    return ranked.where("rank = 1").select(*keys, F.col(column).alias(f"{prefix}_name"), F.col("share").alias(f"{prefix}_share"))


evidence = (
    anomaly_items.groupBy(*keys).agg(
        F.avg(F.when(F.col("is_hit"), F.col("delay_days"))).alias("avg_delay_days"),
        F.avg(F.when(F.col("is_hit"), F.col("is_dispatch_late").cast("int"))).alias("dispatch_late_share"),
        F.avg(F.when(F.col("is_hit"), (F.col("order_status_code") == "canceled").cast("int"))).alias("canceled_share"),
        F.avg(F.when(F.col("is_hit"), F.col("review_score"))).alias("review_avg_hit"),
        F.avg(F.when(~F.col("is_hit"), F.col("review_score"))).alias("review_avg_other"),
    )
    .join(top_share("seller_id", "top_seller"), keys, "left")
    .join(top_share("seller_state_code", "top_seller_state"), keys, "left")
    .join(top_share("category_name", "top_category"), keys, "left")
    .join(top_share("customer_state_code", "top_customer_state"), keys, "left")
)

candidates = anomalies.join(evidence, keys, "left").toPandas()
print(f"{len(candidates)} anomalias no histórico até {last_complete_week}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Sinal principal, texto de evidências, prioridade, status e responsável
# O sinal principal é regra, não IA: é o que sustenta a hipótese e o que o alerta mostra mesmo se a IA falhar.

# CELL ********************

def pct(value) -> str:
    return "-" if pd.isna(value) else f"{value * 100:.1f}%".replace(".", ",")


def num(value, digits: int = 1) -> str:
    return "-" if pd.isna(value) else f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main_signal(row) -> str:
    if row.monitor_code == "M01":
        if row.top_seller_share >= 0.5:
            return "Concentrado em um vendedor"
        if row.canceled_share >= 0.7:
            return "Cancelamentos"
        if row.canceled_share <= 0.3:
            return "Indisponibilidade de estoque"
        return "Cancelamento e indisponibilidade"
    if row.dispatch_late_share >= 0.5:
        return "Postagem do vendedor fora do prazo"
    if row.monitor_code == "M02" and row.top_seller_share >= 0.4:
        return "Concentrado em um vendedor"
    return "Atraso no transporte"


def evidence_text(row) -> str:
    factor = "sem perda no padrão" if pd.isna(row.rate_factor) else f"{num(row.rate_factor)}x o padrão"
    if row.monitor_code == "M01":
        parts = [
            f"{row.hit_count} de {row.item_count} itens em pedidos perdidos; {pct(row.observed_rate)} da receita bruta "
            f"contra {pct(row.baseline_rate)} nas 8 semanas anteriores ({factor}).",
            f"{pct(row.canceled_share)} dos itens perdidos foram cancelados (o resto ficou indisponível).",
            f"Maior vendedor: {str(row.top_seller_name)[:8]} com {pct(row.top_seller_share)} dos itens perdidos.",
        ]
    else:
        parts = [
            f"{row.hit_count} de {row.item_count} itens entregues com atraso ({pct(row.observed_rate)} contra "
            f"{pct(row.baseline_rate)} nas 8 semanas anteriores, {factor}); atraso médio de {num(row.avg_delay_days)} dias.",
            f"{pct(row.dispatch_late_share)} dos itens atrasados foram postados pelo vendedor depois do prazo limite.",
        ]
        if row.monitor_code == "M02":
            parts.append(
                f"Vendedores de {row.top_seller_state_name} respondem por {pct(row.top_seller_state_share)} dos atrasos; "
                f"maior vendedor: {str(row.top_seller_name)[:8]} ({pct(row.top_seller_share)})."
            )
        else:
            parts.append(
                f"Vendedor em {row.top_seller_state_name}; clientes mais afetados em {row.top_customer_state_name} "
                f"({pct(row.top_customer_state_share)})."
            )
        parts.append(f"Nota média {num(row.review_avg_hit)} nos atrasados contra {num(row.review_avg_other)} nos demais.")
    parts.append(f"Categoria mais afetada: {row.top_category_name} ({pct(row.top_category_share)}).")
    return " ".join(parts)


def priority(impact: float):
    return next((name, rank) for name, rank, floor in PRIORITIES if impact >= floor)


owners = {(o[0], o[1]): o[2:] for o in OWNERS}
anomaly_keys = set(zip(candidates.monitor_code, candidates.segment_code, candidates.week_start_date))

rows = []
for row in candidates.itertuples(index=False):
    previous_week = row.week_start_date - timedelta(days=7)
    owner = owners.get((row.monitor_code, row.route_key)) or owners[(row.monitor_code, "*")]
    priority_name, priority_rank = priority(float(row.impact_amount))
    rows.append(dict(
        monitor_code=row.monitor_code, segment_code=row.segment_code, week_start_date=row.week_start_date,
        main_signal_name=main_signal(row), evidence_text=evidence_text(row),
        priority_name=priority_name, priority_rank=priority_rank,
        alert_status_name="Recorrente" if (row.monitor_code, row.segment_code, previous_week) in anomaly_keys else "Nova",
        owner_area_name=owner[0], owner_name=owner[1], owner_email=owner[2],
    ))

enrichment = spark.createDataFrame(
    pd.DataFrame(rows, columns=["monitor_code", "segment_code", "week_start_date", "main_signal_name", "evidence_text",
                                "priority_name", "priority_rank", "alert_status_name", "owner_area_name", "owner_name",
                                "owner_email"]),
    "monitor_code string, segment_code string, week_start_date date, main_signal_name string, evidence_text string, "
    "priority_name string, priority_rank int, alert_status_name string, owner_area_name string, owner_name string, "
    "owner_email string",
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Publicação com histórico
# A tabela é reescrita a cada execução (é pequena), mas o que já existia é preservado: data da primeira detecção e
# colunas de IA. Só fica **pendente de alerta** a anomalia nova neste lote **e** da última semana completa; o backfill
# de semanas antigas entra no histórico sem disparar alerta.

# CELL ********************

AI_COLUMNS = ["ai_hypothesis_text", "ai_action_text", "ai_confidence_name", "ai_status_code",
              "ai_model_name", "ai_prompt_version", "ai_generated_ts"]

current = (
    anomalies.join(evidence, keys, "left").join(enrichment, keys, "left")
    .withColumn("anomaly_id", F.sha2(F.concat_ws("|", "monitor_code", "segment_code", F.col("week_start_date").cast("string")), 256).substr(1, 16))
)

if table_exists("loss", "fact_loss_anomaly"):
    previous = read_table("loss", "fact_loss_anomaly").select(
        "anomaly_id", *AI_COLUMNS, F.col("detected_ts").alias("previous_detected_ts"),
        F.col("dp_batch_id").alias("previous_batch_id"), F.col("dp_inserted_ts").alias("previous_inserted_ts"),
    )
else:
    previous = spark.createDataFrame(
        [], "anomaly_id string, ai_hypothesis_text string, ai_action_text string, ai_confidence_name string, "
            "ai_status_code string, ai_model_name string, ai_prompt_version string, ai_generated_ts timestamp, "
            "previous_detected_ts timestamp, previous_batch_id string, previous_inserted_ts timestamp",
    )

is_new = F.col("previous_detected_ts").isNull()
fact_loss_anomaly = (
    current.join(previous, "anomaly_id", "left")
    .withColumn("detected_ts", F.coalesce("previous_detected_ts", F.current_timestamp()))
    .withColumn("is_alert_pending", is_new & (F.col("week_start_date") == F.lit(last_complete_week)))
    .withColumn("ai_status_code", F.coalesce("ai_status_code", F.lit("Pendente")))
    .select(
        "anomaly_id", "monitor_code", "monitor_name", "loss_type_name", "dimension_name", "segment_code", "segment_name",
        "week_start_date", "week_start_date_key", "item_count", "hit_count",
        F.col("amount").cast("decimal(18,4)").alias("amount"),
        "observed_rate", "baseline_rate", "baseline_week_count", "rate_factor", "robust_z", "impact_amount",
        "priority_name", "priority_rank", "alert_status_name", "main_signal_name", "evidence_text",
        "avg_delay_days", "dispatch_late_share", "canceled_share", "review_avg_hit", "review_avg_other",
        "top_seller_name", "top_seller_share", "top_seller_state_name", "top_seller_state_share",
        "top_category_name", "top_category_share", "top_customer_state_name", "top_customer_state_share",
        *AI_COLUMNS, "owner_area_name", "owner_name", "owner_email", "is_alert_pending", "detected_ts",
        F.when(is_new, F.lit(batch_id)).otherwise(F.col("previous_batch_id")).alias("dp_batch_id"),
        F.coalesce("previous_inserted_ts", F.current_timestamp()).alias("dp_inserted_ts"),
        F.current_timestamp().alias("dp_updated_ts"),
        F.lit("olist").alias("dp_source_system"),
    )
)

# Toda semana de anomalia precisa existir no calendário (relacionamento do modelo semântico).
calendar_keys = read_table("shared", "dim_date").select(F.col("date_key").alias("week_start_date_key"))
orphans = fact_loss_anomaly.join(calendar_keys, "week_start_date_key", "left_anti").count()
if orphans:
    raise AssertionError(f"fact_loss_anomaly: {orphans} semanas fora do calendário")

anomaly_rows = overwrite_table(fact_loss_anomaly, "loss", "fact_loss_anomaly")
pending = read_table("loss", "fact_loss_anomaly").where("is_alert_pending")
print(f"fact_loss_anomaly: {anomaly_rows} anomalias | {pending.count()} pendentes de alerta neste lote")
display(pending.select("monitor_name", "segment_name", "week_start_date", "observed_rate", "baseline_rate",
                       "impact_amount", "priority_name", "main_signal_name", "owner_name"))

log_run(batch_id, NOTEBOOK_NAME, "lh_ai.loss.fact_loss_anomaly", "succeeded", anomaly_rows, started_ts,
        f"as_of_date={as_of}; semanas até {last_complete_week}; monitor_week={week_rows}")

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