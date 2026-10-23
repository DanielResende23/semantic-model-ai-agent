# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_ai_setup_shortcuts
# Liga o `lh_ai` aos dados do projeto [Lakehouse Medallion](https://github.com/danielresende23/fabric-lakehouse-medallion)
# sem copiar nada: **schema shortcuts** do OneLake para o workspace de origem do mesmo ambiente.
#
# | Schema no `lh_ai` | Aponta para | Usado por |
# |---|---|---|
# | `commercial` | `lh_gold/Tables/commercial` | Modelo semântico, monitores, Data Agent |
# | `shared` | `lh_gold/Tables/shared` | Modelo semântico (calendário) |
# | `silver_commercial` | `lh_silver/Tables/commercial` | Só a evidência de postagem fora do prazo |
#
# Roda uma vez por ambiente (e de novo se o workspace de origem mudar). Idempotente: `CreateOrOverwrite`.
# Os shortcuts não ficam em `shortcuts.metadata.json` porque o destino tem GUIDs do workspace de origem,
# diferentes em DEV, TST e PRD; o parâmetro `source_workspace` resolve isso por nome.

# PARAMETERS CELL ********************

source_workspace = "Olist - Medallion [DEV]"
target_lakehouse = "lh_ai"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import notebookutils
import sempy.fabric as fabric

SHORTCUTS = [
    # (schema no lh_ai, lakehouse de origem, schema de origem)
    ("commercial", "lh_gold", "commercial"),
    ("shared", "lh_gold", "shared"),
    ("silver_commercial", "lh_silver", "commercial"),
]


def item_id(item) -> str:
    return item["id"] if isinstance(item, dict) else item.id


workspace_id = notebookutils.runtime.context["currentWorkspaceId"]
target_id = item_id(notebookutils.lakehouse.get(target_lakehouse))
source_workspace_id = fabric.resolve_workspace_id(source_workspace)
client = fabric.FabricRestClient()

for schema, source_lakehouse, source_schema in SHORTCUTS:
    source_id = item_id(notebookutils.lakehouse.get(source_lakehouse, source_workspace_id))
    body = {
        "path": "Tables",
        "name": schema,
        "target": {
            "oneLake": {
                "workspaceId": source_workspace_id,
                "itemId": source_id,
                "path": f"Tables/{source_schema}",
            }
        },
    }
    response = client.post(
        f"v1/workspaces/{workspace_id}/items/{target_id}/shortcuts?shortcutConflictPolicy=CreateOrOverwrite",
        json=body,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Shortcut {schema}: HTTP {response.status_code} {response.text}")
    print(f"{target_lakehouse}.{schema} -> {source_workspace}/{source_lakehouse}/Tables/{source_schema}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Conferência
# As tabelas da Gold precisam aparecer pelo shortcut antes de rodar os monitores.

# CELL ********************

expected = ["commercial/fact_sales", "commercial/fact_order", "commercial/dim_customer", "commercial/dim_seller",
            "commercial/dim_product", "commercial/dim_order_status", "shared/dim_date",
            "silver_commercial/sales_order", "silver_commercial/sales_order_item"]
root = f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com/{target_id}/Tables"
missing = [t for t in expected if not notebookutils.fs.exists(f"{root}/{t}")]
if missing:
    raise RuntimeError(f"Tabelas não encontradas pelo shortcut: {missing}. Rode o pipeline do projeto 1 antes.")
print("Shortcuts ok:", ", ".join(expected))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
