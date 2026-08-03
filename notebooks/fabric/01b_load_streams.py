# CELL
# Ladowanie strumieni zdarzen JSONL do tabel Delta w Lakehouse.
# Pliki: fact_readiness_declaration.jsonl i fact_task_activation.jsonl.

# CELL
from pyspark.sql import functions as F
from pyspark.sql import types as T

base = "Files/streams"

# Generator zapisuje czas w formacie ISO-8601 z offsetem (+02:00) i pelnym
# zapisem sekund, np. "2026-09-15T08:00:00+02:00". Jednak rozne generatory moga
# wytwarzac rozne formaty (np. bez sekund), a domyslny to_timestamp bez wzorca
# zwraca null po cichu i psuje cala warstwe analityczna.
# Stad lista wzorcow z F.coalesce jako fallback — ta sama konwencja co w ol-blackout.
def parse_event_time(column):
    return F.coalesce(
        F.to_timestamp(column, "yyyy-MM-dd'T'HH:mm:ssXXX"),
        F.to_timestamp(column, "yyyy-MM-dd'T'HH:mmXXX"),
        F.to_timestamp(column, "yyyy-MM-dd'T'HH:mm:ss"),
        F.to_timestamp(column, "yyyy-MM-dd'T'HH:mm"),
        F.to_timestamp(column),
    )

# CELL
# --- fact_readiness_declaration ---
# JSON niesie task_module_id jako liczbe — rzutowanie jawne, bo Direct Lake
# bedzie uzywac tej kolumny do relacji 1:* z dim_task_module.
rd = spark.read.json(f"{base}/fact_readiness_declaration.jsonl")

rd = rd.withColumn("task_module_id", F.col("task_module_id").cast(T.IntegerType()))
rd = rd.withColumn("timestamp", parse_event_time("timestamp"))
rd = rd.withColumn("readiness_date", F.to_date("timestamp"))
rd = rd.withColumn("ingested_at", F.current_timestamp())

(rd.write
   .format("delta")
   .mode("overwrite")
   .option("overwriteSchema", "true")
   .saveAsTable("fact_readiness_declaration"))

n_rd = rd.count()
print(f"fact_readiness_declaration: {n_rd} wierszy | kolumny: {', '.join(rd.columns)}")

# CELL
# --- fact_task_activation ---
ta = spark.read.json(f"{base}/fact_task_activation.jsonl")

ta = ta.withColumn("task_module_id", F.col("task_module_id").cast(T.IntegerType()))
ta = ta.withColumn("day_offset", F.col("day_offset").cast(T.IntegerType()))
ta = ta.withColumn("timestamp", parse_event_time("timestamp"))
ta = ta.withColumn("activation_date", F.to_date("timestamp"))
ta = ta.withColumn("ingested_at", F.current_timestamp())

(ta.write
   .format("delta")
   .mode("overwrite")
   .option("overwriteSchema", "true")
   .saveAsTable("fact_task_activation"))

n_ta = ta.count()
print(f"fact_task_activation: {n_ta} wierszy | kolumny: {', '.join(ta.columns)}")

# CELL
# Weryfikacja parsowania czasu — krytyczna asercja, bo NULL w kolumnie timestamp
# powoduje ciche wyniki puste w raportach i blad CANNOT_INFER_EMPTY_SCHEMA
# przy probach odczytu przez dalsze notatniki.
null_rd = spark.table("fact_readiness_declaration").filter(F.col("timestamp").isNull()).count()
assert null_rd == 0, \
    f"fact_readiness_declaration: {null_rd} rekordow z NULL timestamp — sprawdz wzorzec parsowania"

null_ta = spark.table("fact_task_activation").filter(F.col("timestamp").isNull()).count()
assert null_ta == 0, \
    f"fact_task_activation: {null_ta} rekordow z NULL timestamp — sprawdz wzorzec parsowania"

# Weryfikacja wolumenow zgodna z DATA_MODEL.md
assert spark.table("fact_readiness_declaration").count() == 106, \
    "fact_readiness_declaration: oczekiwano 106 deklaracji"
assert spark.table("fact_task_activation").count() == 79, \
    "fact_task_activation: oczekiwano 79 aktywacji"

# Typ task_module_id musi byc integer, zeby relacja z dim_task_module dzialala
# w Direct Lake bez utraty filtrow.
tm_type_rd = dict(spark.table("fact_readiness_declaration").dtypes)["task_module_id"]
assert tm_type_rd == "int", f"fact_readiness_declaration.task_module_id powinno byc int, jest: {tm_type_rd}"

tm_type_ta = dict(spark.table("fact_task_activation").dtypes)["task_module_id"]
assert tm_type_ta == "int", f"fact_task_activation.task_module_id powinno byc int, jest: {tm_type_ta}"

print("Strumienie zaladowane i zwalidowane.")

# CELL
# Podsumowanie zakresu czasowego i rozkladu statusow.
print("Zakres czasowy fact_readiness_declaration:")
spark.table("fact_readiness_declaration").agg(
    F.min("timestamp").alias("od"),
    F.max("timestamp").alias("do_"),
    F.count("*").alias("rekordy")
).show(truncate=False)

print("Rozklad statusow gotowosci:")
spark.table("fact_readiness_declaration").groupBy("status").count().orderBy("status").show()

print("Zakres czasowy fact_task_activation:")
spark.table("fact_task_activation").agg(
    F.min("timestamp").alias("od"),
    F.max("timestamp").alias("do_"),
    F.min("day_offset").alias("day_min"),
    F.max("day_offset").alias("day_max")
).show(truncate=False)

print("Rozklad statusow aktywacji:")
spark.table("fact_task_activation").groupBy("activation_status").count().show()
