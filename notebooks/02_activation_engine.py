# CELL
"""Activation engine: hazard + phase + scale -> ordered operational task list."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
DERIVED = DATA / "derived"
DERIVED.mkdir(exist_ok=True)
HAZARD = sys.argv[1] if len(sys.argv) > 1 else "Z02"
PHASE = sys.argv[2] if len(sys.argv) > 2 else "R"
SCALE = int(sys.argv[3]) if len(sys.argv) > 3 else 4


# CELL
def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


grid = read_csv("fact_safety_grid.csv")
mods = {int(r["task_module_id"]): r for r in read_csv("dim_task_module.csv")}
adm = {r["admin_division"]: r for r in read_csv("dim_admin_division.csv")}
deps = [(int(r["task_module_id"]), int(r["depends_on_task_module_id"])) for r in read_csv("fact_interdependency.csv")]


# CELL
def topo(selected_modules: set[int]) -> list[int]:
    incoming = {m: set() for m in selected_modules}
    outgoing = defaultdict(set)
    for module_id, dependency_id in deps:
        if module_id in selected_modules and dependency_id in selected_modules:
            incoming[module_id].add(dependency_id)
            outgoing[dependency_id].add(module_id)
    queue = deque(sorted([m for m, dep in incoming.items() if not dep]))
    ordered = []
    while queue:
        module_id = queue.popleft()
        ordered.append(module_id)
        for nxt in sorted(outgoing[module_id]):
            incoming[nxt].discard(module_id)
            if not incoming[nxt]:
                queue.append(nxt)
    return ordered + sorted(selected_modules - set(ordered))


# CELL
rows = []
selected = set()
for r in grid:
    if r["hazard_code"] != HAZARD or r["phase"] != PHASE or not r["task_modules"] or r["role"] == "wspierający":
        continue
    for module_id in [int(x) for x in r["task_modules"].split(";") if x]:
        selected.add(module_id)
        role_factor = 0.75 if r["role"] == "wiodący" else 1.0
        crit_factor = 0.75 if r["criticality"] == "wysoka" else 1.0
        sla = max(2, int((24 - SCALE * 3) * role_factor * crit_factor))
        rows.append({
            "hazard_code": HAZARD,
            "phase": PHASE,
            "scale": SCALE,
            "task_module_id": module_id,
            "task_module_name": mods[module_id]["task_module_name"],
            "admin_division": r["admin_division"],
            "admin_name": adm[r["admin_division"]]["admin_name"],
            "ministry": adm[r["admin_division"]]["ministry"],
            "role": r["role"],
            "criticality": r["criticality"],
            "sla_hours": sla,
        })

order = {m: idx + 1 for idx, m in enumerate(topo(selected))}
for r in rows:
    r["dependency_order"] = order[r["task_module_id"]]
rows.sort(key=lambda r: (r["dependency_order"], 0 if r["role"] == "wiodący" else 1, r["admin_division"]))


# CELL
out_csv = DERIVED / f"activation_plan_{HAZARD}_{PHASE}.csv"
with out_csv.open("w", encoding="utf-8", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    wr.writeheader()
    wr.writerows(rows)

summary = {"hazard_code": HAZARD, "phase": PHASE, "scale": SCALE, "tasks": len(rows), "modules": sorted(selected), "dependency_order": order}
(DERIVED / f"activation_plan_{HAZARD}_{PHASE}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
