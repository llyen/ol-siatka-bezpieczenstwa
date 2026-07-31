# CELL
"""Load generated files to a Fabric Lakehouse/Delta equivalent.
In Fabric, replace local paths with lakehouse Files/Tables paths and Spark Delta writes.
"""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
OUT = DATA / "derived" / "lakehouse_preview"
OUT.mkdir(parents=True, exist_ok=True)


# CELL
counts = {}
for p in list(DATA.glob("dim_*.csv")) + list(DATA.glob("fact_*.csv")) + list(DATA.glob("fact_*.jsonl")):
    shutil.copy2(p, OUT / p.name)
    with p.open(encoding="utf-8") as f:
        counts[p.name] = sum(1 for _ in f) - (1 if p.suffix == ".csv" else 0)
(OUT / "load_counts.json").write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(counts, ensure_ascii=False, indent=2))
