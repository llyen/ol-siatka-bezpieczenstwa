# CELL
# Analiza luk gotowosci, przekroczonych SLA i blokad.
# Port notatnika notebooks/03_gap_analysis.py na PySpark.
# Wynik referencyjny: 28 nie-gotowych, 28 po SLA, 9 blokad,
# przeciazone dzialy wiodace VIII i XIX (po 5 zadan).

# CELL
import datetime
from pyspark.sql import functions as F
from pyspark.sql import types as T
from pyspark.sql.window import Window

# Punkt odniesienia czasowego: poczatek zdarzenia POWODZ_WRZESIEN i chwila "teraz".
# Wszystkie SLA liczymy od BASE — dzialy mialy czas od ogłoszenia zdarzenia.
# Timestamps jako UTC, zeby uniknac niejednoznacznosci stref przy arytmetyce Sparka.
BASE_DT = datetime.datetime(2026, 9, 15, 6, 0, 0, tzinfo=datetime.timezone.utc)   # 08:00 CEST
NOW_DT  = datetime.datetime(2026, 9, 17, 10, 0, 0, tzinfo=datetime.timezone.utc)  # 12:00 CEST

BASE_EPOCH = int(BASE_DT.timestamp())
NOW_EPOCH  = int(NOW_DT.timestamp())

print(f"BASE (poczatek zdarzenia): {BASE_DT.isoformat()} -> epoch {BASE_EPOCH}")
print(f"NOW  (chwila analizy):     {NOW_DT.isoformat()} -> epoch {NOW_EPOCH}")
print(f"Uplynelo od startu: {(NOW_EPOCH - BASE_EPOCH) / 3600:.1f} godzin")

# CELL
# Wczytanie planu aktywacji i deklaracji gotowosci.
# activation_plan zostal zapisany przez 02_activation_engine.py —
# notatniki musza byc uruchamiane w kolejnosci przez Jobs API.
plan = spark.table("activation_plan")
readiness_all = spark.table("fact_readiness_declaration")

assert plan.count() > 0, "activation_plan jest pusta — uruchom najpierw 02_activation_engine.py"
assert readiness_all.count() > 0, "fact_readiness_declaration jest pusta — uruchom najpierw 01b_load_streams.py"

# Deklaracja gotowosci jest zdarzeniem, nie stanem: dzial moze zglosic sie kilka razy
# dla tego samego modulu (najpierw 'nie rozpoczeto', potem 'w toku', potem 'gotowe').
# Bez redukcji do ostatniej deklaracji LEFT JOIN rozmnaza wiersze planu (44 -> 71)
# i luka gotowosci wychodzi wieksza niz sam plan, co jest bez sensu.
_w = Window.partitionBy("admin_division", "task_module_id").orderBy(F.col("timestamp").desc())
readiness = (readiness_all
    .withColumn("_rn", F.row_number().over(_w))
    .filter(F.col("_rn") == 1)
    .drop("_rn"))

print(f"Wierszy w planie aktywacji: {plan.count()}")
print(f"Deklaracji gotowosci (zdarzen): {readiness_all.count()}")
print(f"Deklaracji po redukcji do ostatniej: {readiness.count()}")

# CELL
# Laczenie planu z deklaracjami gotowosci (LEFT JOIN po dziale i module).
# LEFT JOIN zachowuje zadania, dla ktorych dano brak deklaracji — sa traktowane
# jako 'brak deklaracji', co jest najgorszym mozliwym stanem.
joined = (plan.alias("p")
    .join(
        readiness.select("admin_division", "task_module_id", "status", "comment")
                 .alias("r"),
        (F.col("p.admin_division") == F.col("r.admin_division")) &
        (F.col("p.task_module_id") == F.col("r.task_module_id")),
        "left",
    )
    .select(
        F.col("p.hazard_code"),
        F.col("p.phase"),
        F.col("p.scale"),
        F.col("p.task_module_id"),
        F.col("p.task_module_name"),
        F.col("p.admin_division"),
        F.col("p.admin_name"),
        F.col("p.ministry"),
        F.col("p.role"),
        F.col("p.criticality"),
        F.col("p.sla_hours"),
        F.col("p.dependency_order"),
        F.coalesce(F.col("r.status"), F.lit("brak deklaracji")).alias("status"),
        F.col("r.comment").alias("comment"),
    ))

print(f"Polaczone wiersze: {joined.count()}")

# CELL
# Identyfikacja luk: zadania bez statusu 'gotowe'.
gaps = joined.filter(F.col("status") != "gotowe")

# Obliczenie deadline i naduzycia SLA.
# Arytmetyka na epochach zamiast na Timestamp, bo INTERVAL z kolumna nie dziala
# we wszystkich wersjach Spark SQL bez uzycia expr().
gaps = (gaps
    .withColumn("deadline_epoch",
        F.lit(BASE_EPOCH) + F.col("sla_hours").cast(T.LongType()) * F.lit(3600))
    .withColumn("deadline",
        F.to_timestamp(F.from_unixtime("deadline_epoch")))
    .withColumn("hours_over_sla",
        F.round((F.lit(NOW_EPOCH) - F.col("deadline_epoch")) / F.lit(3600.0), 1))
    .withColumn("is_overdue",
        F.lit(NOW_EPOCH) > F.col("deadline_epoch"))
    .drop("deadline_epoch"))

overdue = gaps.filter(F.col("is_overdue"))
blocked = gaps.filter(F.col("status") == "zablokowane")

n_gaps = gaps.count()
n_overdue = overdue.count()
n_blocked = blocked.count()

print(f"Zadania bez pelnej gotowosci: {n_gaps}")
print(f"Zadania po SLA:               {n_overdue}")
print(f"Zadania zablokowane:          {n_blocked}")

# CELL
# Analiza przeciazen dzialow wiodacych.
# Przeciazony = dzia wiodacy z >= 4 zadaniami w planie (nie tylko w lukach).
lead_load = (plan
    .filter(F.col("role") == "wiodący")
    .groupBy("admin_division", "admin_name")
    .agg(F.count("*").alias("task_count"))
    .filter(F.col("task_count") >= 4)
    .orderBy(F.col("task_count").desc()))

print("Przeciazone dzialy wiodace (>= 4 zadania):")
lead_load.show(truncate=False)

overload_dict = {r["admin_division"]: r["task_count"] for r in lead_load.collect()}
print(f"Slownik przeciazen: {overload_dict}")

# CELL
# Zapis gap_analysis_overdue do tabeli Delta.
# Tabela uzywana przez raporty i reguly Activatora — musi miec stabilny schemat.
overdue_out = (overdue
    .select(
        "hazard_code", "phase", "scale",
        "task_module_id", "task_module_name",
        "admin_division", "admin_name", "ministry",
        "role", "criticality", "sla_hours", "dependency_order",
        "status", "comment", "deadline", "hours_over_sla",
    )
    .orderBy("dependency_order", "admin_division"))

(overdue_out.write
     .format("delta")
     .mode("overwrite")
     .option("overwriteSchema", "true")
     .saveAsTable("gap_analysis_overdue"))

print(f"Zapisano gap_analysis_overdue: {overdue_out.count()} wierszy")

# CELL
# Zapis gap_analysis_summary jako jednowierszowej tabeli Delta.
# Tabela sluzy jako zrodlo kart KPI w raporcie Power BI.
summary_rows = [(
    int(plan.count()),
    int(n_gaps),
    int(n_overdue),
    int(n_blocked),
    str(overload_dict),
    NOW_DT.isoformat(),
)]
summary_schema = T.StructType([
    T.StructField("plan_tasks",                  T.IntegerType()),
    T.StructField("not_ready_tasks",             T.IntegerType()),
    T.StructField("overdue_tasks",               T.IntegerType()),
    T.StructField("blocked_tasks",               T.IntegerType()),
    T.StructField("overloaded_leading_divisions", T.StringType()),
    T.StructField("analysis_time",               T.StringType()),
])
summary_df = spark.createDataFrame(summary_rows, summary_schema)

(summary_df.write
     .format("delta")
     .mode("overwrite")
     .option("overwriteSchema", "true")
     .saveAsTable("gap_analysis_summary"))

print("Zapisano gap_analysis_summary:")
summary_df.show(truncate=False)

# CELL
# Weryfikacja wynikow referencyjnych.
REF_NOT_READY = 28
REF_OVERDUE   = 28
REF_BLOCKED   = 9
REF_OVERLOAD  = {"VIII": 5, "XIX": 5}

print("\n=== Porownanie z wartosciami referencyjnymi ===")
print(f"Nie-gotowe: {n_gaps:>4}  (ref: {REF_NOT_READY}) {'OK' if n_gaps == REF_NOT_READY else 'ROZNICA!'}")
print(f"Po SLA:     {n_overdue:>4}  (ref: {REF_OVERDUE}) {'OK' if n_overdue == REF_OVERDUE else 'ROZNICA!'}")
print(f"Blokady:    {n_blocked:>4}  (ref: {REF_BLOCKED}) {'OK' if n_blocked == REF_BLOCKED else 'ROZNICA!'}")
print(f"Obciaz.:    {overload_dict}  (ref: {REF_OVERLOAD}) {'OK' if overload_dict == REF_OVERLOAD else 'ROZNICA!'}")

assert n_gaps == REF_NOT_READY, \
    f"gap_analysis: {n_gaps} nie-gotowych, oczekiwano {REF_NOT_READY}"
assert n_overdue == REF_OVERDUE, \
    f"gap_analysis: {n_overdue} po SLA, oczekiwano {REF_OVERDUE}"
assert n_blocked == REF_BLOCKED, \
    f"gap_analysis: {n_blocked} blokad, oczekiwano {REF_BLOCKED}"
assert overload_dict == REF_OVERLOAD, \
    f"gap_analysis: przeciazenia {overload_dict}, oczekiwano {REF_OVERLOAD}"

print("\nWynik referencyjny potwierdzony.")

# CELL
# Szczegolowy widok zadan zablokowanych — uzyteczny do diagnozy na demo.
print("Zadania zablokowane:")
(spark.table("gap_analysis_overdue")
 .filter(F.col("status") == "zablokowane")
 .select("admin_division", "admin_name", "task_module_name", "role", "comment", "hours_over_sla")
 .orderBy("admin_division")
 .show(20, truncate=False))
