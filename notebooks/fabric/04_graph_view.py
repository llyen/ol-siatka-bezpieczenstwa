# CELL
# Eksport grafu odpowiedzialnosci do tabel Delta.
# Port notatnika notebooks/04_graph_view.py na PySpark.
# Wynik referencyjny: 12 wezlow, 20 krawedzi.

# CELL
from pyspark.sql import functions as F
from pyspark.sql import types as T

# Kod zagrozen, dla ktorego budujemy graf — parametr latwy do zmiany
# bez edycji reszty logiki.
HAZARD_FILTER = "Z02"

# CELL
# Wczytanie krawedzi: komórki siatki dla wybranego zagrozen, role wiodacy/wspolpracujacy.
# Rola 'wspierajacy' jest pomijana — to samo zalozenie co w skrypcie pandas
# i w silniku aktywacji.
grid = (spark.table("fact_safety_grid")
    .filter(
        (F.col("hazard_code") == HAZARD_FILTER) &
        F.col("task_modules").isNotNull() &
        (F.col("task_modules") != "") &
        (F.col("role") != "wspierający")
    ))

n_edges_raw = grid.count()
print(f"Wiersze siatki dla {HAZARD_FILTER} (role != wspierajacy, task_modules not empty): {n_edges_raw}")

# Dolaczenie nazwy dzialu z wymiaru — potrzebne do etykiet wezlow.
adm = spark.table("dim_admin_division").select("admin_division", "admin_name")
grid = grid.join(adm, "admin_division")

# CELL
# Budowa krawedzi grafu: hazard -> division.
# Krawedzie zbieramy na driverze, bo zbior jest maly (~ 20 wierszy),
# a operacje grafowe (stopien, centralnosc) sa latwiejsze w Pythonie.
edge_rows = grid.select("admin_division", "admin_name", "role", "phase", "task_modules").collect()

# Budowa wezlow: jeden wezel zagrozen + wezly dzialow administracji.
hazard_node_id = f"hazard:{HAZARD_FILTER}"
nodes = {hazard_node_id: {"id": hazard_node_id, "label": f"{HAZARD_FILTER} Powodz", "type": "hazard"}}

edges = []
for row in edge_rows:
    div_id = f"division:{row['admin_division']}"
    nodes[div_id] = {"id": div_id, "label": row["admin_name"], "type": "division"}
    edges.append({
        "source": hazard_node_id,
        "target": div_id,
        "role": row["role"],
        "phase": row["phase"],
        "modules": row["task_modules"],
    })

n_nodes = len(nodes)
n_edges = len(edges)
print(f"Wezly: {n_nodes} | Krawedzie: {n_edges}")

# CELL
# Prosta centralnosc stopniowa (degree centrality) na driverze.
# NetworkX nie jest gwarantowany w Fabric — implementujemy reczne obliczenie
# zamiast polegac na bibliotece zewnetrznej.
# Centralnosc = stopien wezla / (N - 1), gdzie N = liczba wezlow.
in_degree = {}
out_degree = {}
for e in edges:
    out_degree[e["source"]] = out_degree.get(e["source"], 0) + 1
    in_degree[e["target"]] = in_degree.get(e["target"], 0) + 1

denom = max(1, n_nodes - 1)  # unikamy dzielenia przez zero
centrality = {}
for nid in nodes:
    deg = in_degree.get(nid, 0) + out_degree.get(nid, 0)
    centrality[nid] = round(deg / denom, 4)

# CELL
# Zapis wezlow do tabeli Delta responsibility_graph_nodes.
nodes_schema = T.StructType([
    T.StructField("id",         T.StringType()),
    T.StructField("label",      T.StringType()),
    T.StructField("type",       T.StringType()),
    T.StructField("centrality", T.DoubleType()),
])
nodes_rows = [(v["id"], v["label"], v["type"], centrality.get(v["id"], 0.0))
              for v in nodes.values()]
nodes_df = spark.createDataFrame(nodes_rows, nodes_schema)

(nodes_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("responsibility_graph_nodes"))

print(f"Zapisano responsibility_graph_nodes: {nodes_df.count()} wierszy")
nodes_df.orderBy("type", "id").show(20, truncate=False)

# CELL
# Zapis krawedzi do tabeli Delta responsibility_graph_edges.
edges_schema = T.StructType([
    T.StructField("source",  T.StringType()),
    T.StructField("target",  T.StringType()),
    T.StructField("role",    T.StringType()),
    T.StructField("phase",   T.StringType()),
    T.StructField("modules", T.StringType()),
])
edges_rows = [(e["source"], e["target"], e["role"], e["phase"], e["modules"])
              for e in edges]
edges_df = spark.createDataFrame(edges_rows, edges_schema)

(edges_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("responsibility_graph_edges"))

print(f"Zapisano responsibility_graph_edges: {edges_df.count()} wierszy")

# CELL
# Weryfikacja wynikow referencyjnych.
REF_NODES = 12
REF_EDGES = 20

actual_nodes = spark.table("responsibility_graph_nodes").count()
actual_edges = spark.table("responsibility_graph_edges").count()

print(f"\n=== Porownanie z wartosciami referencyjnymi ===")
print(f"Wezly:    {actual_nodes:>4}  (ref: {REF_NODES}) {'OK' if actual_nodes == REF_NODES else 'ROZNICA!'}")
print(f"Krawedzie:{actual_edges:>4}  (ref: {REF_EDGES}) {'OK' if actual_edges == REF_EDGES else 'ROZNICA!'}")

assert actual_nodes == REF_NODES, \
    f"responsibility_graph_nodes: {actual_nodes} wezlow, oczekiwano {REF_NODES}"
assert actual_edges == REF_EDGES, \
    f"responsibility_graph_edges: {actual_edges} krawedzi, oczekiwano {REF_EDGES}"

print("\nWynik referencyjny potwierdzony.")

# CELL
# Dzialy z najwyzszym stopniem — single points of failure w grafie odpowiedzialnosci.
# Stopien >= 2 oznacza, ze dział pojawia sie w wielu fazach lub rolach dla tego zagrozen.
print("Dzialy z najwyzszym stopniem wejsciowym (liczba krawedzi skierowanych do dzialu):")
(spark.table("responsibility_graph_edges")
 .groupBy("target")
 .count()
 .withColumnRenamed("count", "in_degree")
 .filter(F.col("in_degree") >= 2)
 .join(spark.table("responsibility_graph_nodes").select("id", "label"), F.col("target") == F.col("id"))
 .select("target", "label", "in_degree")
 .orderBy(F.col("in_degree").desc())
 .show(truncate=False))

print("Rozklad rol w krawedziach grafu:")
edges_df.groupBy("role").count().show()
