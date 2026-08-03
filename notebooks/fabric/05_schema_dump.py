# CELL
# Zrzut schematow tabel Delta do OneLake — weryfikacja po calym lancuchu notatnikow.
# Wzorzec: ol-blackout-wrazliwi/notebooks/fabric/05_schema_dump.py

# CELL
import json

# Lista wszystkich tabel wyprodukowanych przez lancuch 01->01b->02->03->04.
# Kolejnosc odpowiada kolejnosci notatnikow — latwiej stwierdzic, ktorego
# notatnika brakuje, gdy tabela ma 0 wierszy lub nie istnieje.
EXPECTED_TABLES = [
    # 01_load_grid.py
    "dim_hazard",
    "dim_admin_division",
    "dim_task_module",
    "dim_spo",
    "dim_contact_point",
    "fact_safety_grid",
    "fact_spo_checklist",
    "fact_interdependency",
    # 01b_load_streams.py
    "fact_readiness_declaration",
    "fact_task_activation",
    # 02_activation_engine.py
    "activation_plan",
    # 03_gap_analysis.py
    "gap_analysis_overdue",
    "gap_analysis_summary",
    # 04_graph_view.py
    "responsibility_graph_nodes",
    "responsibility_graph_edges",
]

# Minimalne oczekiwane liczby wierszy — asercje czytelne w logach Jobs API.
EXPECTED_COUNTS = {
    "dim_hazard":                 20,
    "dim_admin_division":         25,
    "dim_task_module":             7,
    "dim_spo":                    16,
    "dim_contact_point":          25,
    "fact_safety_grid":         1000,
    "fact_spo_checklist":         64,
    "fact_interdependency":        7,
    "fact_readiness_declaration": 106,
    "fact_task_activation":       79,
    "activation_plan":            44,
    "gap_analysis_overdue":       28,
    "gap_analysis_summary":        1,
    "responsibility_graph_nodes": 12,
    "responsibility_graph_edges": 20,
}

# CELL
# Sprawdzamy, ktore tabele w Lakehouse sa rzeczywiscie dostepne.
available_tables = {t.name for t in spark.catalog.listTables()}
missing = [t for t in EXPECTED_TABLES if t not in available_tables]
if missing:
    print(f"UWAGA: brakujace tabele ({len(missing)}):")
    for t in missing:
        print(f"  - {t}")
else:
    print(f"Wszystkie {len(EXPECTED_TABLES)} oczekiwanych tabel istnieje w Lakehouse.")

# CELL
# Zbieramy schemat i liczbnosc kazdej tabeli.
# Schematy sa zapisywane do Files/derived/lakehouse_schema.json —
# stanowia dokumentacje dla osoby budujaceje model semantyczny Direct Lake.
schema = {}
for name in EXPECTED_TABLES:
    if name not in available_tables:
        schema[name] = {"rows": -1, "columns": [], "error": "tabela nie istnieje"}
        continue
    df = spark.table(name)
    n = df.count()
    schema[name] = {
        "rows": n,
        "columns": [{"name": c, "type": t} for c, t in df.dtypes],
    }

payload = json.dumps(schema, ensure_ascii=False, indent=2)
mssparkutils.fs.put("Files/derived/lakehouse_schema.json", payload, True)

print(f"\nTabel w Lakehouse: {len(schema)}")
print(f"{'Tabela':<35} {'Wiersze':>8}  {'Schemat (pierwsze 5 kol.)'}")
print("-" * 90)
for name, info in schema.items():
    if info["rows"] == -1:
        print(f"  {name:<33}  {'BRAK':>8}  !")
        continue
    col_summary = ", ".join(f"{c['name']}:{c['type']}" for c in info["columns"][:5])
    expected = EXPECTED_COUNTS.get(name)
    match_mark = "OK" if info["rows"] == expected else f"!={expected}"
    print(f"  {name:<33}  {info['rows']:>8}  [{match_mark}]  {col_summary} ...")

# CELL
# Asercje finalne — jezeli ktorakolwiek tabela ma zla liczbe wierszy,
# lancuch jest niekompletny i nie nalezy uruchamiac raportu.
errors = []
for name, expected in EXPECTED_COUNTS.items():
    actual = schema.get(name, {}).get("rows", -1)
    if actual != expected:
        errors.append(f"{name}: {actual} wierszy, oczekiwano {expected}")

if errors:
    error_msg = "\n".join(errors)
    raise AssertionError(
        f"Niezgodnosci schematu Lakehouse ({len(errors)} tabel):\n{error_msg}"
    )

print(f"\nWszystkie {len(EXPECTED_COUNTS)} tabel zwalidowanych poprawnie.")
print("Lakehouse gotowe do budowy modelu semantycznego Direct Lake.")
