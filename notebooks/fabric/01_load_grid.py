# CELL
# Ladowanie slownikow i faktow statycznych KPZK do tabel Delta w Lakehouse.
# Zrodlem sa pliki CSV z Files/datasets/ w OneLake.

# CELL
from pyspark.sql import functions as F
from pyspark.sql import types as T

base = "Files/datasets"

# Jawne schematy zamiast inferSchema — pliki maja polskie znaki i kolumny
# z listami rozdzielanymi srednikami, ktore Spark moze zle zinterpretowac
# przy automatycznym wywnioskowaniu typu.

schema_dim_hazard = T.StructType([
    T.StructField("hazard_code", T.StringType()),
    T.StructField("hazard_name", T.StringType()),
    T.StructField("category", T.StringType()),
    T.StructField("probability", T.IntegerType()),
    T.StructField("probability_label", T.StringType()),
    T.StructField("impact", T.IntegerType()),
    T.StructField("impact_label", T.StringType()),
    T.StructField("risk_score", T.IntegerType()),
    T.StructField("risk_level", T.StringType()),
    T.StructField("color", T.StringType()),
])

schema_dim_admin_division = T.StructType([
    T.StructField("admin_division", T.StringType()),
    T.StructField("admin_name", T.StringType()),
    T.StructField("ministry", T.StringType()),
    T.StructField("subordinate_institutions", T.StringType()),
])

schema_dim_task_module = T.StructType([
    T.StructField("task_module_id", T.IntegerType()),
    T.StructField("task_module_name", T.StringType()),
    T.StructField("description", T.StringType()),
])

schema_dim_spo = T.StructType([
    T.StructField("spo_code", T.StringType()),
    T.StructField("spo_name", T.StringType()),
    T.StructField("related_hazards", T.StringType()),
])

schema_dim_contact_point = T.StructType([
    T.StructField("admin_division", T.StringType()),
    T.StructField("role", T.StringType()),
    T.StructField("unit", T.StringType()),
    T.StructField("duty_phone", T.StringType()),
    T.StructField("email", T.StringType()),
    T.StructField("deputy", T.StringType()),
])

schema_fact_safety_grid = T.StructType([
    T.StructField("hazard_code", T.StringType()),
    T.StructField("admin_division", T.StringType()),
    T.StructField("phase", T.StringType()),
    T.StructField("task_modules", T.StringType()),
    T.StructField("role", T.StringType()),
    T.StructField("criticality", T.StringType()),
])

schema_fact_spo_checklist = T.StructType([
    T.StructField("spo_code", T.StringType()),
    T.StructField("step_number", T.IntegerType()),
    T.StructField("step_description", T.StringType()),
    T.StructField("responsible_admin_division", T.StringType()),
    T.StructField("sla_hours", T.IntegerType()),
    T.StructField("required_document", T.StringType()),
])

schema_fact_interdependency = T.StructType([
    T.StructField("task_module_id", T.IntegerType()),
    T.StructField("depends_on_task_module_id", T.IntegerType()),
    T.StructField("dependency_reason", T.StringType()),
])

# CELL
# Mapowanie: nazwa tabeli -> schema i plik CSV.
# Kolejnosc ladownia nie ma znaczenia dla tabel statycznych, ale zachowujemy
# konwencje: wymiary przed faktami, zeby ewentualne JOIN-y w pozniejszych
# komorkach zastawalyz juz zwalidowane wymiary.
table_definitions = [
    ("dim_hazard",          schema_dim_hazard,          "dim_hazard.csv"),
    ("dim_admin_division",  schema_dim_admin_division,  "dim_admin_division.csv"),
    ("dim_task_module",     schema_dim_task_module,     "dim_task_module.csv"),
    ("dim_spo",             schema_dim_spo,             "dim_spo.csv"),
    ("dim_contact_point",   schema_dim_contact_point,   "dim_contact_point.csv"),
    ("fact_safety_grid",    schema_fact_safety_grid,    "fact_safety_grid.csv"),
    ("fact_spo_checklist",  schema_fact_spo_checklist,  "fact_spo_checklist.csv"),
    ("fact_interdependency", schema_fact_interdependency, "fact_interdependency.csv"),
]

for table_name, schema, filename in table_definitions:
    df = (spark.read
          .option("header", True)
          .option("encoding", "UTF-8")
          .schema(schema)
          .csv(f"{base}/{filename}"))

    df = df.withColumn("ingested_at", F.current_timestamp())

    (df.write
       .format("delta")
       .mode("overwrite")
       .option("overwriteSchema", "true")
       .saveAsTable(table_name))

    n = df.count()
    print(f"{table_name:30s}  {n:>6} wierszy  | kolumny: {', '.join(df.columns[:5])} ...")

# CELL
# Weryfikacja wolumenow zgodna z DATA_MODEL.md.
# Asercje z komunikatem pomagaja zlokalizowac problem w logach Jobs API,
# gdzie tresc wyjatku nie jest zawsze widoczna.
assert spark.table("dim_hazard").count() == 20, \
    "dim_hazard: oczekiwano 20 zagrozen Z01-Z20"
assert spark.table("dim_admin_division").count() == 25, \
    "dim_admin_division: oczekiwano 25 dzialow I-XXV"
assert spark.table("dim_task_module").count() == 7, \
    "dim_task_module: oczekiwano 7 modulow"
assert spark.table("dim_spo").count() == 16, \
    "dim_spo: oczekiwano 16 procedur SPO"
assert spark.table("dim_contact_point").count() == 25, \
    "dim_contact_point: oczekiwano 25 punktow kontaktowych"
assert spark.table("fact_safety_grid").count() == 1000, \
    "fact_safety_grid: oczekiwano 1000 komorek macierzy"
assert spark.table("fact_spo_checklist").count() == 64, \
    "fact_spo_checklist: oczekiwano 64 krokow SPO"
assert spark.table("fact_interdependency").count() == 7, \
    "fact_interdependency: oczekiwano 7 zaleznosci"

# Weryfikacja integralnosci: kazdy kod zagrozen w siatce musi istniec w slowniu.
grid_codes = {r["hazard_code"] for r in spark.table("fact_safety_grid").select("hazard_code").distinct().collect()}
hazard_codes = {r["hazard_code"] for r in spark.table("dim_hazard").select("hazard_code").collect()}
unknown = grid_codes - hazard_codes
assert not unknown, f"fact_safety_grid zawiera nieznane kody zagrozen: {unknown}"

# Weryfikacja integralnosci: task_module_id w interdependency musi istniec w slowniku.
dep_ids = {r["task_module_id"] for r in spark.table("fact_interdependency").select("task_module_id").collect()}
dep_ids |= {r["depends_on_task_module_id"] for r in spark.table("fact_interdependency").select("depends_on_task_module_id").collect()}
mod_ids = {r["task_module_id"] for r in spark.table("dim_task_module").select("task_module_id").collect()}
unknown_mods = dep_ids - mod_ids
assert not unknown_mods, f"fact_interdependency zawiera nieznane task_module_id: {unknown_mods}"

# Typ kolumny risk_score musi byc liczbowy — miary DAX w modelu semantycznym
# korzystaja z agregacji na tej kolumnie.
rs_type = dict(spark.table("dim_hazard").dtypes)["risk_score"]
assert rs_type == "int", f"dim_hazard.risk_score powinno byc int, jest: {rs_type}"

# Wyniki raportu zaleza od filtrowania faz R i O — sprawdzamy, ze kolumna phase
# zawiera wylacznie te dwie wartosci.
phases = {r["phase"] for r in spark.table("fact_safety_grid").select("phase").distinct().collect()}
assert phases <= {"R", "O"}, f"fact_safety_grid.phase zawiera nieoczekiwane wartosci: {phases}"

print("Slowniki i fakty statyczne zaladowane i zwalidowane.")

# CELL
# Podsumowanie rozkładu rol w siatce — uzyteczne jako baseline do analizy obciazen.
print("Rozklad rol w fact_safety_grid:")
spark.table("fact_safety_grid").groupBy("role").count().orderBy("role").show()

print("Rozklad faz w fact_safety_grid:")
spark.table("fact_safety_grid").groupBy("phase").count().show()

print("Liczba komorek z niezerowa lista modulow:")
n_nonempty = (spark.table("fact_safety_grid")
              .filter(F.col("task_modules").isNotNull() & (F.col("task_modules") != ""))
              .count())
print(f"  {n_nonempty} / 1000 komorek ma przypisane moduly")
