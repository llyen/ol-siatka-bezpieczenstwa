# CELL
# Silnik aktywacji: zagrozen + faza + skala -> posortowana lista operacyjna.
# Port notatnika notebooks/02_activation_engine.py na PySpark.
# Wynik referencyjny: 44 zadania, 5 modulow, kolejnosc 1,2,4,5,7.

# CELL
from collections import defaultdict, deque
from pyspark.sql import functions as F
from pyspark.sql import types as T

# Parametry scenariusza — zmienne na gorze, zeby Jobs API móglo je nadpisac
# przez parametry notebooka bez edycji kodu.
HAZARD = "Z02"
PHASE = "R"
SCALE = 4

# Wartosc bazowa SLA: im wyzsza skala, tym krotszy czas reakcji.
# Dla SCALE=4: 24 - 4*3 = 12 godzin bazowych.
BASE_SLA_HOURS = 24 - SCALE * 3
assert BASE_SLA_HOURS > 0, f"Nieprawidlowa kombinacja SCALE={SCALE}: BASE_SLA_HOURS={BASE_SLA_HOURS}"

print(f"Parametry scenariusza: HAZARD={HAZARD}, PHASE={PHASE}, SCALE={SCALE}")
print(f"Bazowy SLA: {BASE_SLA_HOURS} godzin")

# CELL
# Krok 1: Filtrowanie siatki bezpieczenstwa i rozbicie list modulow.
# Rola 'wspierajacy' jest pomijana zgodnie z logiką macierzy — tylko wiodacy
# i wspolpracujacy generuja realne zadania operacyjne w planie aktywacji.
grid_raw = (spark.table("fact_safety_grid")
    .filter(
        (F.col("hazard_code") == HAZARD) &
        (F.col("phase") == PHASE) &
        (F.col("role") != "wspierający") &
        F.col("task_modules").isNotNull() &
        (F.col("task_modules") != "")
    ))

print(f"Komorki siatki (rola != wspierajacy) dla {HAZARD}/{PHASE}: {grid_raw.count()}")

# Rozbicie pola task_modules (lista srednikow) na osobne wiersze.
# Pusty string po splicie jest filtrowany, zeby uniknac kasztowania None->null.
grid_exploded = (grid_raw
    .withColumn("module_str", F.explode(F.split("task_modules", ";")))
    .filter(F.trim(F.col("module_str")) != "")
    .withColumn("task_module_id", F.trim(F.col("module_str")).cast(T.IntegerType()))
    .drop("module_str", "task_modules"))

print(f"Wierszy po explode modulow: {grid_exploded.count()}")

# CELL
# Krok 2: Sortowanie topologiczne na driverze.
# Spark nie ma wbudowanego operatora grafu topologicznego, a zbior modulow
# jest maly (max 7), wiec collect() jest tu uzasadniony i szybki.
selected = {row["task_module_id"] for row in grid_exploded.select("task_module_id").distinct().collect()}
deps_rows = spark.table("fact_interdependency").select("task_module_id", "depends_on_task_module_id").collect()
deps = [(r["task_module_id"], r["depends_on_task_module_id"]) for r in deps_rows]

print(f"Wybrane moduly: {sorted(selected)}")
print(f"Wszystkie zaleznosci: {deps}")


def topo_sort(selected_modules: set, all_deps: list) -> list:
    """Sortowanie topologiczne Kahna — te same zasady co w skrypcie pandas."""
    incoming = {m: set() for m in selected_modules}
    outgoing = defaultdict(set)
    for module_id, dep_id in all_deps:
        if module_id in selected_modules and dep_id in selected_modules:
            incoming[module_id].add(dep_id)
            outgoing[dep_id].add(module_id)
    queue = deque(sorted(m for m, deps in incoming.items() if not deps))
    ordered = []
    while queue:
        m = queue.popleft()
        ordered.append(m)
        for nxt in sorted(outgoing[m]):
            incoming[nxt].discard(m)
            if not incoming[nxt]:
                queue.append(nxt)
    # Moduly bez zaleznosci lub tworzace cykl dodawane na koniec
    return ordered + sorted(selected_modules - set(ordered))


order_list = topo_sort(selected, deps)
order_map = {m: idx + 1 for idx, m in enumerate(order_list)}
print(f"Kolejnosc topologiczna: {order_map}")

# CELL
# Krok 3: Obliczenie SLA i dolaczenie kolejnosci zaleznosci.
# Logika SLA: krotszy czas dla wiodacych (odp. krytyczna rola) i wysokiej
# krytycznosci, bo te zadania musza byc wykonane jako pierwsze.
role_factor_expr = F.when(F.col("role") == "wiodący", F.lit(0.75)).otherwise(F.lit(1.0))
crit_factor_expr = F.when(F.col("criticality") == "wysoka", F.lit(0.75)).otherwise(F.lit(1.0))

grid_with_sla = (grid_exploded
    .withColumn("sla_hours", F.greatest(
        F.lit(2),
        (F.lit(BASE_SLA_HOURS) * role_factor_expr * crit_factor_expr).cast(T.IntegerType())
    )))

# Mapowanie kolejnosci topologicznej jako mala tabela do JOIN.
# createDataFrame z listy tupli zamiast broadcastu — czytelniejsze i odporne
# na problemy z serializacja closure w Spark Connect.
order_rows = [(int(m), int(o)) for m, o in order_map.items()]
order_df = spark.createDataFrame(order_rows, T.StructType([
    T.StructField("task_module_id", T.IntegerType()),
    T.StructField("dependency_order", T.IntegerType()),
]))

grid_with_order = grid_with_sla.join(order_df, "task_module_id")

# CELL
# Krok 4: Dolaczenie wymiarow i zapis do tabeli Delta activation_plan.
adm = spark.table("dim_admin_division").select("admin_division", "admin_name", "ministry")
mods = spark.table("dim_task_module").select("task_module_id", "task_module_name")

plan = (grid_with_order
    .join(adm, "admin_division")
    .join(mods, "task_module_id")
    .select(
        F.lit(HAZARD).alias("hazard_code"),
        F.lit(PHASE).alias("phase"),
        F.lit(SCALE).alias("scale"),
        "task_module_id",
        "task_module_name",
        "admin_division",
        "admin_name",
        "ministry",
        "role",
        "criticality",
        "sla_hours",
        "dependency_order",
    )
    .orderBy(
        "dependency_order",
        F.when(F.col("role") == "wiodący", F.lit(0)).otherwise(F.lit(1)),
        "admin_division",
    ))

(plan.write
     .format("delta")
     .mode("overwrite")
     .option("overwriteSchema", "true")
     .saveAsTable("activation_plan"))

# CELL
# Weryfikacja wyniku referencyjnego.
# Wartosci referencyjne: 44 zadania, 5 modulow, kolejnosc 1->2->4->5->7.
plan_loaded = spark.table("activation_plan")
n_tasks = plan_loaded.count()
modules_found = sorted([r["task_module_id"] for r in plan_loaded.select("task_module_id").distinct().collect()])
order_found = sorted(
    [(r["task_module_id"], r["dependency_order"])
     for r in plan_loaded.select("task_module_id", "dependency_order").distinct().collect()],
    key=lambda x: x[1]
)

REF_TASKS = 44
REF_MODULES = [1, 2, 4, 5, 7]
REF_ORDER = [1, 2, 4, 5, 7]  # kolejnosc topologiczna

print(f"\n=== Porownanie z wartosciami referencyjnymi ===")
print(f"Liczba zadan:   {n_tasks:>4}  (ref: {REF_TASKS}) {'OK' if n_tasks == REF_TASKS else 'ROZNICA!'}")
print(f"Moduly:         {modules_found}  (ref: {REF_MODULES}) {'OK' if modules_found == REF_MODULES else 'ROZNICA!'}")
order_ids = [m for m, o in order_found]
print(f"Kol. topol.:    {order_ids}  (ref: {REF_ORDER}) {'OK' if order_ids == REF_ORDER else 'ROZNICA!'}")

assert n_tasks == REF_TASKS, \
    f"activation_plan: {n_tasks} zadan, oczekiwano {REF_TASKS}"
assert modules_found == REF_MODULES, \
    f"activation_plan: moduly {modules_found}, oczekiwano {REF_MODULES}"
assert order_ids == REF_ORDER, \
    f"activation_plan: kolejnosc {order_ids}, oczekiwano {REF_ORDER}"

print("\nWynik referencyjny potwierdzony.")
plan_loaded.show(10, truncate=False)

# CELL
# Podsumowanie planu aktywacji — rozkład rol i modulow.
print("Rozklad rol w planie aktywacji:")
plan_loaded.groupBy("role").count().show()

print("Obciazenie dzialow wiodacych (rola wiodacy):")
(plan_loaded
 .filter(F.col("role") == "wiodący")
 .groupBy("admin_division", "admin_name")
 .count()
 .orderBy(F.col("count").desc())
 .show(10))

print("Zadania według modulu i kolejnosci zaleznosci:")
(plan_loaded
 .select("dependency_order", "task_module_id", "task_module_name")
 .distinct()
 .orderBy("dependency_order")
 .show(truncate=False))
