# CELL
"""Responsibility graph export with optional NetworkX centrality."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
DERIVED = DATA / "derived"
DERIVED.mkdir(exist_ok=True)


# CELL
with (DATA / "fact_safety_grid.csv").open(encoding="utf-8", newline="") as f:
    grid = list(csv.DictReader(f))
with (DATA / "dim_admin_division.csv").open(encoding="utf-8", newline="") as f:
    adm = {r["admin_division"]: r for r in csv.DictReader(f)}

edges = []
nodes = {}
for r in grid:
    if r["hazard_code"] == "Z02" and r["task_modules"] and r["role"] != "wspierający":
        h = "hazard:Z02"
        d = "division:" + r["admin_division"]
        nodes[h] = {"id": h, "label": "Z02 Powódź", "type": "hazard"}
        nodes[d] = {"id": d, "label": adm[r["admin_division"]]["admin_name"], "type": "division"}
        edges.append({"source": h, "target": d, "role": r["role"], "phase": r["phase"], "modules": r["task_modules"]})


# CELL
try:
    import networkx as nx
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from((e["source"], e["target"]) for e in edges)
    centrality = nx.degree_centrality(graph)
except Exception:
    centrality = {n: 0 for n in nodes}

load = Counter(e["target"] for e in edges)
single_points = [{"node": n, "label": nodes[n]["label"], "degree": load[n], "centrality": centrality.get(n, 0)} for n in load if load[n] >= 2]
export = {
    "nodes": [{**v, "centrality": centrality.get(k, 0)} for k, v in nodes.items()],
    "edges": edges,
    "single_points_of_failure": single_points,
}
(DERIVED / "responsibility_graph.json").write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"nodes": len(nodes), "edges": len(edges), "single_points_of_failure": len(single_points)}, ensure_ascii=False, indent=2))
