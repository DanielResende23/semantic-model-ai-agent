# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_ai_utils
# Funções compartilhadas pelos notebooks da camada de IA. Carregado com `%run nb_ai_utils`.
# - **Caminhos OneLake resolvidos em tempo de execução** no workspace atual: sem lakehouse padrão nem GUID fixo,
#   o mesmo código roda em DEV, TST e PRD.
# - **Contrato de entrada**: só lê `lh_ai`. A Gold do projeto Lakehouse Medallion chega por shortcuts
#   (`commercial`, `shared`) e a Silver só para a data de postagem (`silver_commercial`), criados pelo `nb_ai_setup_shortcuts`.
# - **`build_item_events`**: um DataFrame por item de pedido com tudo que os monitores e as evidências usam.
# - **Run log** em `lh_ai.framework.etl_run_log`, no mesmo formato do projeto 1.

# CELL ********************

import re
import uuid
from datetime import datetime, timezone

import notebookutils
from delta.tables import DeltaTable
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

IDENT = re.compile(r"^[a-z0-9_]+$")
LH_AI = "lh_ai"


def _check_ident(*names: str) -> None:
    """Só aceita identificadores snake_case: evita injeção em caminhos e SQL montados por string."""
    for name in names:
        if not IDENT.match(name):
            raise ValueError(f"Identificador inválido: {name!r}")


def new_batch_id(batch_id: str = "") -> str:
    """Usa o RunId do pipeline quando vier por parâmetro; em execução manual gera um id local."""
    return batch_id.strip() or f"manual-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Caminhos OneLake e escrita Delta

# CELL ********************

_LAKEHOUSE_ROOT: dict = {}


def lakehouse_root(lakehouse: str = LH_AI) -> str:
    """abfss://<workspaceId>@onelake.dfs.fabric.microsoft.com/<lakehouseId> do lakehouse no workspace atual."""
    _check_ident(lakehouse)
    if lakehouse not in _LAKEHOUSE_ROOT:
        workspace_id = notebookutils.runtime.context["currentWorkspaceId"]
        item = notebookutils.lakehouse.get(lakehouse)
        lakehouse_id = item["id"] if isinstance(item, dict) else item.id
        _LAKEHOUSE_ROOT[lakehouse] = f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{lakehouse_id}"
    return _LAKEHOUSE_ROOT[lakehouse]


def table_path(schema: str, table: str, lakehouse: str = LH_AI) -> str:
    _check_ident(schema, table)
    return f"{lakehouse_root(lakehouse)}/Tables/{schema}/{table}"


def table_exists(schema: str, table: str) -> bool:
    return DeltaTable.isDeltaTable(spark, table_path(schema, table))


def read_table(schema: str, table: str) -> DataFrame:
    return spark.read.format("delta").load(table_path(schema, table))


def overwrite_table(df: DataFrame, schema: str, table: str) -> int:
    path = table_path(schema, table)
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(path)
    spark.sql(f"ALTER TABLE delta.`{path}` SET TBLPROPERTIES ('delta.parquet.vorder.enabled' = 'true')")
    return spark.read.format("delta").load(path).count()


def add_audit_columns(df: DataFrame, batch_id: str) -> DataFrame:
    now = F.current_timestamp()
    return (
        df.withColumn("dp_inserted_ts", now)
        .withColumn("dp_updated_ts", now)
        .withColumn("dp_source_system", F.lit("olist"))
        .withColumn("dp_batch_id", F.lit(batch_id))
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Eventos por item
# Uma linha por item de pedido, com as duas datas de semana que os monitores usam:
# - `purchase_week_start`: venda perdida é um fato da **compra** (o pedido foi cancelado ou ficou indisponível).
# - `delivered_week_start`: o atraso só é conhecido na **entrega**; agrupar pela entrega evita olhar para o futuro
#   quando a detecção roda no fim da semana.
#
# `is_dispatch_late` vem da Silver (postagem na transportadora depois do prazo limite do vendedor) e separa
# atraso do vendedor de atraso do transporte. É a única coluna que não está na Gold (ADR 0002).

# CELL ********************

def week_start(date_col):
    """Segunda-feira da semana da data."""
    return F.date_trunc("week", date_col).cast("date")


def date_key(date_col):
    return F.date_format(date_col, "yyyyMMdd").cast("int")


def build_item_events() -> DataFrame:
    sales = read_table("commercial", "fact_sales")
    orders = read_table("commercial", "fact_order").select(
        "order_id", "delivered_date_key", "estimated_delivery_date_key", "delay_days", "review_score",
    )
    dates = read_table("shared", "dim_date").select("date_key", "date")
    customer = read_table("commercial", "dim_customer").select(
        "customer_key", F.col("state_code").alias("customer_state_code"), F.col("region_name").alias("customer_region_name"),
    )
    seller = read_table("commercial", "dim_seller").select(
        "seller_key", "seller_id", F.col("state_code").alias("seller_state_code"),
    )
    product = read_table("commercial", "dim_product").select("product_key", "category_name")
    status = read_table("commercial", "dim_order_status").select("order_status_key", "order_status_code")
    dispatch = (
        read_table("silver_commercial", "sales_order_item").select("order_id", "order_item_number", "shipping_limit_ts")
        .join(read_table("silver_commercial", "sales_order").select("order_id", "delivered_carrier_ts"), "order_id", "left")
        .select(
            "order_id", "order_item_number",
            (F.col("delivered_carrier_ts") > F.col("shipping_limit_ts")).alias("is_dispatch_late"),
        )
    )
    purchase_date = dates.select(F.col("date_key").alias("purchase_date_key"), F.col("date").alias("purchase_date"))
    delivered_date = dates.select(F.col("date_key").alias("delivered_date_key"), F.col("date").alias("delivered_date"))

    return (
        sales
        .join(orders, "order_id", "left")
        .join(purchase_date, "purchase_date_key", "left")
        .join(delivered_date, "delivered_date_key", "left")
        .join(customer, "customer_key", "left")
        .join(seller, "seller_key", "left")
        .join(product, "product_key", "left")
        .join(status, "order_status_key", "left")
        .join(dispatch, ["order_id", "order_item_number"], "left")
        .select(
            "order_id", "order_item_number", "order_status_code",
            "category_name", "customer_state_code", "customer_region_name", "seller_id", "seller_state_code",
            F.col("gross_amount").cast("decimal(18,4)").alias("gross_amount"),
            "is_lost", "is_delivered", "is_late", "delay_days", "review_score",
            F.coalesce("is_dispatch_late", F.lit(False)).alias("is_dispatch_late"),
            week_start(F.col("purchase_date")).alias("purchase_week_start"),
            F.when(F.col("is_delivered"), week_start(F.col("delivered_date"))).alias("delivered_week_start"),
        )
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Run log

# CELL ********************

RUN_LOG_SCHEMA = T.StructType([
    T.StructField("batch_id", T.StringType()),
    T.StructField("notebook_name", T.StringType()),
    T.StructField("layer_name", T.StringType()),
    T.StructField("target_table", T.StringType()),
    T.StructField("status_code", T.StringType()),
    T.StructField("row_count", T.LongType()),
    T.StructField("started_ts", T.TimestampType()),
    T.StructField("finished_ts", T.TimestampType()),
    T.StructField("message_text", T.StringType()),
])


def log_run(batch_id: str, notebook_name: str, target_table: str, status_code: str,
            row_count: int = None, started_ts: datetime = None, message_text: str = None) -> None:
    row = [(batch_id, notebook_name, "ai", target_table, status_code,
            None if row_count is None else int(row_count), started_ts, datetime.now(timezone.utc), message_text)]
    (
        spark.createDataFrame(row, RUN_LOG_SCHEMA)
        .write.format("delta").mode("append")
        .save(table_path("framework", "etl_run_log"))
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
