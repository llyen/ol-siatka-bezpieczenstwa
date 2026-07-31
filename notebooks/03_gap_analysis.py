# CELL
"""Gap analysis for readiness, SLA, overload and critical path."""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
DERIVED = DATA / "derived"
DERIVED.mkdir(exist_ok=True)
PLAN = DERIVED / "activation_plan_Z02_R.csv"
NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone(timedelta(hours=2)))
BASE = datetime(2026, 9, 15, 8, 0, tzinfo=timezone(timedelta(hours=2)))


# CELL
def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


plan = read_csv(PLAN)
readiness = read_jsonl("fact_readiness_declaration.jsonl")
status = {(r["admin_division"], str(r["task_module_id"])): r for r in readiness}


# CELL
gaps = []
overdue = []
for task in plan:
    key = (task["admin_division"], task["task_module_id"])
    dec = status.get(key)
    st = dec["status"] if dec else "brak deklaracji"
    deadline = BASE + timedelta(hours=int(task["sla_hours"]))
    if st != "gotowe":
        gaps.append({**task, "status": st, "comment": dec.get("comment") if dec else "brak wpisu"})
    if st != "gotowe" and NOW > deadline:
        overdue.append({**task, "status": st, "deadline": deadline.isoformat(), "hours_over_sla": round((NOW - deadline).total_seconds() / 3600, 1)})

lead_load = Counter(t["admin_division"] for t in plan if t["role"] == "wiodący")
overload = {d: c for d, c in lead_load.items() if c >= 4}
blocked = [g for g in gaps if g["status"] == "zablokowane"]
summary = {
    "plan_tasks": len(plan),
    "not_ready_tasks": len(gaps),
    "overdue_tasks": len(overdue),
    "blocked_tasks": len(blocked),
    "overloaded_leading_divisions": overload,
    "critical_path_modules": [1, 2, 4, 3],
    "analysis_time": NOW.isoformat(),
}


# CELL
if overdue:
    with (DERIVED / "gap_analysis_overdue.csv").open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(overdue[0].keys()))
        wr.writeheader()
        wr.writerows(overdue)
(DERIVED / "gap_analysis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
