"""Offline JSONL replay helper for demo event streams."""
import argparse, json, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(); p.add_argument("--speed", type=float, default=10); p.add_argument("--from", dest="source", default="datasets/fact_task_activation.jsonl"); p.add_argument("--to", default="datasets/derived/realtime_dry_run.jsonl"); p.add_argument("--dry-run", action="store_true")
args=p.parse_args(); src=ROOT/args.source; dst=ROOT/args.to
if not args.dry_run: raise SystemExit("Demo nie wysyła danych bez konfiguracji endpointu; użyj --dry-run.")
dst.parent.mkdir(parents=True, exist_ok=True)
with src.open(encoding="utf-8") as f, dst.open("w", encoding="utf-8") as o:
    for line in f:
        ev=json.loads(line); ev["replayed_at"]="dry-run"; o.write(json.dumps(ev, ensure_ascii=False)+"\n"); time.sleep(max(0, 0.01/args.speed))
print(f"dry-run zapisany: {dst}")
