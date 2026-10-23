# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_ai_refresh_semantic_model
# Último passo do pipeline, mesmo padrão do projeto 1:
# 1. **Rebind**: garante que a expressão `OneLake_AI` do modelo aponte para o `lh_ai` **deste** workspace. O TMDL do Git
#    guarda IDs de exemplo; depois de um sync do Git ou de um deploy para TST/PRD, este passo corrige o endereço.
# 2. **Framing**: refresh do modelo Direct Lake (operação de metadados, não copia dados). Roda depois do
#    `nb_ai_explain_anomalies`, para que o alerta, o Copilot e o Data Agent nunca leiam anomalias sem hipótese.
#
# Usa Semantic Link (`sempy`), pré-instalado no runtime do Fabric.

# PARAMETERS CELL ********************

semantic_model_name = "Olist Prevenção de Perdas"
ai_lakehouse = "lh_ai"
expression_name = "OneLake_AI"
batch_id = ""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import time

import notebookutils
import sempy.fabric as fabric

workspace_id = notebookutils.runtime.context["currentWorkspaceId"]
lakehouse = notebookutils.lakehouse.get(ai_lakehouse)
lakehouse_id = lakehouse["id"] if isinstance(lakehouse, dict) else lakehouse.id
onelake_url = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}"

expected_expression = (
    "let\n"
    f'    Fonte = AzureStorage.DataLake("{onelake_url}", [HierarchicalNavigation = true])\n'
    "in\n"
    "    Fonte"
)

server = fabric.create_tom_server(readonly=False, workspace=workspace_id)
database = server.Databases.GetByName(semantic_model_name)
expression = database.Model.Expressions.Find(expression_name)
if expression is None:
    raise ValueError(f"Expressão {expression_name!r} não encontrada em {semantic_model_name!r}")

if onelake_url not in expression.Expression:
    expression.Expression = expected_expression
    database.Model.SaveChanges()
    print(f"Modelo reapontado para {onelake_url}")
else:
    print("Modelo já aponta para o lh_ai deste workspace")
server.Disconnect()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

request_id = fabric.refresh_dataset(semantic_model_name, workspace=workspace_id, refresh_type="full")

for _ in range(165):   # até ~27 min, abaixo do timeout de 30 min da atividade no pipeline
    status = fabric.get_refresh_execution_details(semantic_model_name, request_id, workspace=workspace_id).status
    if status in ("Completed", "Failed", "Cancelled", "Disabled", "TimedOut"):
        break
    time.sleep(10)

print(f"Framing {request_id}: {status}")
if status != "Completed":
    raise RuntimeError(f"Refresh do modelo terminou com status {status}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
