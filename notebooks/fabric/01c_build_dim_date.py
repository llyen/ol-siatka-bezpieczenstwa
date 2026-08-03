# CELL
# Budowanie tabeli kalendarza dim_date dla okna scenariusza demonstracyjnego.
# Zakres: 2026-09-14 (D-1) do 2026-09-26 (D+11), D0 = 2026-09-15 (POWODZ_WRZESIEN).
# Wymaganie MODEL.md: Direct Lake potrzebuje oznaczonej tabeli dat z relacjami
# do fact_readiness_declaration[readiness_date] i fact_task_activation[activation_date].

# CELL
from pyspark.sql import functions as F
from pyspark.sql import types as T
import datetime

# D0 i granice okna demonstracyjnego — zmienne jawne, zeby latwiej bylo rozszerzyc
# zakres przy kolejnych scenariuszach bez zmiany logiki.
D0_STR     = "2026-09-15"
START_STR  = "2026-09-14"
END_STR    = "2026-09-26"

D0_DATE    = datetime.date(2026, 9, 15)
START_DATE = datetime.date(2026, 9, 14)
END_DATE   = datetime.date(2026, 9, 26)
N_DAYS     = (END_DATE - START_DATE).days + 1  # musi byc 13

print(f"Zakres kalendarza: {START_STR} .. {END_STR}")
print(f"D0: {D0_STR}")
print(f"Liczba dni: {N_DAYS}")
assert N_DAYS == 13, f"Oczekiwano 13 dni, wyliczono: {N_DAYS}"

# CELL
# Nazwy polskie dla miesiecy i dni tygodnia — wartosci w danych moga miec
# polskie znaki (to sa stringi w tabelach), komentarze w kodzie ich nie maja.
# Mapowanie przez F.create_map jest deterministyczne i nie wymaga UDF ani
# zewnetrznych bibliotek, co jest wazne w srodowiskach bez dostepu do PyPI.

# Spark dayofweek(): 1=niedziela, 2=poniedzialek, ..., 7=sobota (konwencja US).
# Przeliczamy na ISO (1=poniedzialek, ..., 7=niedziela) — standard europejski
# i sposob liczenia week_of_year (weekofyear() w Spark jest ISO 8601).
month_map = F.create_map(
    F.lit(1),  F.lit("styczeń"),
    F.lit(2),  F.lit("luty"),
    F.lit(3),  F.lit("marzec"),
    F.lit(4),  F.lit("kwiecień"),
    F.lit(5),  F.lit("maj"),
    F.lit(6),  F.lit("czerwiec"),
    F.lit(7),  F.lit("lipiec"),
    F.lit(8),  F.lit("sierpień"),
    F.lit(9),  F.lit("wrzesień"),
    F.lit(10), F.lit("październik"),
    F.lit(11), F.lit("listopad"),
    F.lit(12), F.lit("grudzień"),
)

# Mapa: Spark dayofweek (1-7) -> ISO day_of_week (1-7)
# Spark: 1=Sun, 2=Mon, ..., 7=Sat
# ISO:   1=Mon, ..., 6=Sat, 7=Sun
iso_dow_map = F.create_map(
    F.lit(1), F.lit(7),  # Sun -> 7
    F.lit(2), F.lit(1),  # Mon -> 1
    F.lit(3), F.lit(2),  # Tue -> 2
    F.lit(4), F.lit(3),  # Wed -> 3
    F.lit(5), F.lit(4),  # Thu -> 4
    F.lit(6), F.lit(5),  # Fri -> 5
    F.lit(7), F.lit(6),  # Sat -> 6
)

# Mapa: ISO day_of_week (1-7) -> polska nazwa dnia
day_name_map = F.create_map(
    F.lit(1), F.lit("poniedziałek"),
    F.lit(2), F.lit("wtorek"),
    F.lit(3), F.lit("środa"),
    F.lit(4), F.lit("czwartek"),
    F.lit(5), F.lit("piątek"),
    F.lit(6), F.lit("sobota"),
    F.lit(7), F.lit("niedziela"),
)

# CELL
# Generowanie sekwencji dat przez spark.range — bez pliku zrodlowego,
# bez UDF, deterministyczne i kompatybilne z Fabric Spark Connect.
dim_date = (spark
    .range(N_DAYS)
    .select(
        F.date_add(
            F.lit(START_STR).cast(T.DateType()),
            F.col("id").cast(T.IntegerType())
        ).alias("date")
    )
    .withColumn("year",         F.year("date"))
    .withColumn("quarter",      F.quarter("date"))
    .withColumn("month",        F.month("date"))
    .withColumn("month_name",   month_map[F.month("date")])
    .withColumn("day",          F.dayofmonth("date"))
    .withColumn("_spark_dow",   F.dayofweek("date"))
    .withColumn("day_of_week",  iso_dow_map[F.col("_spark_dow")])
    .withColumn("day_name",     day_name_map[iso_dow_map[F.col("_spark_dow")]])
    .withColumn("week_of_year", F.weekofyear("date"))
    .withColumn("is_weekend",   iso_dow_map[F.col("_spark_dow")].isin(6, 7))
    .withColumn("day_offset",
        F.datediff(F.col("date"), F.lit(D0_STR).cast(T.DateType())))
    .withColumn("is_demo_window", F.lit(True))
    .drop("_spark_dow")
    .orderBy("date")
)

print("Wygenerowane kolumny:", dim_date.columns)
print("Liczba wierszy:", dim_date.count())

# CELL
(dim_date.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("dim_date"))

print("Zapisano dim_date.")

# CELL
# Weryfikacja zawartosci — wypisanie pelnej tabeli, bo 13 wierszy to malo
# i log powinien byc samowystarczajaca dokumentacja okna scenariusza.
dim_date_loaded = spark.table("dim_date")
dim_date_loaded.show(20, truncate=False)

# CELL
# Asercje finalne — sprawdzamy wszystkie kluczowe wymagania MODEL.md i zadania.
n = dim_date_loaded.count()
assert n == 13, f"dim_date: {n} wierszy, oczekiwano dokladnie 13"

# Zakres dat
min_date = dim_date_loaded.agg(F.min("date")).collect()[0][0]
max_date = dim_date_loaded.agg(F.max("date")).collect()[0][0]
assert str(min_date) == START_STR, f"dim_date: pierwsza data {min_date}, oczekiwano {START_STR}"
assert str(max_date) == END_STR,   f"dim_date: ostatnia data {max_date}, oczekiwano {END_STR}"

# day_offset dla D0 musi byc 0
d0_offset = dim_date_loaded.filter(F.col("date") == F.lit(D0_STR)).select("day_offset").collect()[0][0]
assert d0_offset == 0, f"dim_date: day_offset dla D0={D0_STR} wynosi {d0_offset}, oczekiwano 0"

# day_offset dla D-1 musi byc -1
dm1_offset = dim_date_loaded.filter(F.col("date") == F.lit(START_STR)).select("day_offset").collect()[0][0]
assert dm1_offset == -1, f"dim_date: day_offset dla {START_STR} wynosi {dm1_offset}, oczekiwano -1"

# Liczba weekendow w oknie 2026-09-14..26:
#   19 wrz 2026 = sobota, 20 wrz = niedziela, 26 wrz = sobota -> 3 dni weekendowe
n_weekend = dim_date_loaded.filter(F.col("is_weekend")).count()
assert n_weekend == 3, f"dim_date: {n_weekend} dni weekendowych, oczekiwano 3 (19-sob, 20-ndz, 26-sob)"

# Wszystkie wiersze maja is_demo_window = True
non_demo = dim_date_loaded.filter(~F.col("is_demo_window")).count()
assert non_demo == 0, f"dim_date: {non_demo} wierszy bez is_demo_window=True"

# Brak null w kluczowych kolumnach
for col in ["date", "year", "month", "month_name", "day", "day_of_week", "day_name",
            "week_of_year", "is_weekend", "day_offset"]:
    n_null = dim_date_loaded.filter(F.col(col).isNull()).count()
    assert n_null == 0, f"dim_date.{col}: {n_null} wartosci NULL"

# Typ kolumny date musi byc DateType — Power BI wymaga tego do oznaczenia Date table
date_type = dict(dim_date_loaded.dtypes)["date"]
assert date_type == "date", f"dim_date.date powinno byc date, jest: {date_type}"

print(f"\ndim_date zwalidowana: {n} wierszy, zakres {min_date}..{max_date}, D0 offset=0.")
print("Tabela gotowa do oznaczenia jako Date table w modelu semantycznym.")
