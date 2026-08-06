# Miary DAX

Miary modelu `OL_SIA_SemanticModel`, wygenerowane z `deploy/create_semantic_model.py`.
Plik powstaje skryptem `deploy/export_measures.py` — nie edytuj go ręcznie,
bo przy najbliższym wdrożeniu zmiany zostaną nadpisane.
Łącznie 38 miar w 11 tabelach.


## `activation_plan`

### Zadania w planie

```dax
Zadania w planie =
COUNTROWS ( activation_plan )
```

Format: liczba całkowita.

### Zadania wiodące

```dax
Zadania wiodące =
CALCULATE ( COUNTROWS ( activation_plan ), activation_plan[role] = "wiodący" )
```

Format: liczba całkowita.

### Zadania współpracujące

```dax
Zadania współpracujące =
CALCULATE ( COUNTROWS ( activation_plan ), activation_plan[role] = "współpracujący" )
```

Format: liczba całkowita.

### Zadania krytyczne

```dax
Zadania krytyczne =
CALCULATE ( COUNTROWS ( activation_plan ), activation_plan[criticality] = "wysoka" )
```

Format: liczba całkowita.

### Obciążenie działu

```dax
Obciążenie działu =
[Zadania wiodące]
```

Format: liczba całkowita.

### Działy przeciążone

```dax
Działy przeciążone =
COUNTROWS (
    FILTER (
        SUMMARIZE ( activation_plan, activation_plan[admin_division],
            "Wiodace", [Zadania wiodące] ),
        [Wiodace] >= 4
    )
)
```

Format: liczba całkowita.

### Mediana SLA zadania (h)

```dax
Mediana SLA zadania (h) =
MEDIANX ( activation_plan, activation_plan[sla_hours] )
```

Format: liczba z jednym miejscem.

## `dim_admin_division`

### Działy administracji

```dax
Działy administracji =
COUNTROWS ( dim_admin_division )
```

Format: liczba całkowita.

### Ministerstwa

```dax
Ministerstwa =
DISTINCTCOUNT ( dim_admin_division[ministry] )
```

Format: liczba całkowita.

## `dim_contact_point`

### Punkty kontaktowe

```dax
Punkty kontaktowe =
COUNTROWS ( dim_contact_point )
```

Format: liczba całkowita.

## `dim_hazard`

### Zagrożenia w katalogu

```dax
Zagrożenia w katalogu =
COUNTROWS ( dim_hazard )
```

Format: liczba całkowita.

### Zagrożenia wysokiego ryzyka

```dax
Zagrożenia wysokiego ryzyka =
CALCULATE ( COUNTROWS ( dim_hazard ), dim_hazard[risk_level] = "wysokie" )
```

Format: liczba całkowita.

### Średnie ryzyko

```dax
Średnie ryzyko =
AVERAGE ( dim_hazard[risk_score] )
```

Format: liczba z jednym miejscem.

### Ryzyko skorygowane gotowością

```dax
Ryzyko skorygowane gotowością =
AVERAGEX ( dim_hazard, dim_hazard[risk_score] * ( 1 - [Gotowość %] ) )
```

Format: liczba z jednym miejscem.

## `dim_spo`

### Procedury SPO

```dax
Procedury SPO =
COUNTROWS ( dim_spo )
```

Format: liczba całkowita.

## `dim_task_module`

### Moduły zadaniowe

```dax
Moduły zadaniowe =
COUNTROWS ( dim_task_module )
```

Format: liczba całkowita.

## `fact_readiness_declaration`

### Deklaracje gotowości

```dax
Deklaracje gotowości =
COUNTROWS ( fact_readiness_declaration )
```

Format: liczba całkowita.

### Zadania gotowe

```dax
Zadania gotowe =
CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] = "gotowe" )
```

Format: liczba całkowita.

### Zadania niegotowe

```dax
Zadania niegotowe =
CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] <> "gotowe" )
```

Format: liczba całkowita.

### Zadania w toku

```dax
Zadania w toku =
CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] = "w toku" )
```

Format: liczba całkowita.

### Zadania zablokowane

```dax
Zadania zablokowane =
CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] = "zablokowane" )
```

Format: liczba całkowita.

### Gotowość %

```dax
Gotowość % =
DIVIDE ( [Zadania gotowe], [Deklaracje gotowości] )
```

Format: procent.

### Udział blokad %

```dax
Udział blokad % =
DIVIDE ( [Zadania zablokowane], [Deklaracje gotowości] )
```

Format: procent.

### Blokady na ścieżce krytycznej

```dax
Blokady na ścieżce krytycznej =
CALCULATE ( [Zadania zablokowane],
    fact_readiness_declaration[task_module_id] IN { 1, 2, 3, 4 } )
```

Format: liczba całkowita.

### Działy bez deklaracji

```dax
Działy bez deklaracji =
COUNTROWS ( EXCEPT (
    VALUES ( dim_admin_division[admin_division] ),
    VALUES ( fact_readiness_declaration[admin_division] )
) )
```

Format: liczba całkowita.

### Indeks przygotowania

```dax
Indeks przygotowania =
VAR Gotowosc = [Gotowość %]
VAR KaraBlokady = DIVIDE ( [Zadania zablokowane], [Deklaracje gotowości] )
VAR KaraSla = DIVIDE ( [Zadania po SLA], [Deklaracje gotowości] )
RETURN MAX ( 0, Gotowosc - KaraBlokady * 0.3 - KaraSla * 0.2 )
```

Format: wskaźnik 0–1.

## `fact_safety_grid`

### Komórki siatki

```dax
Komórki siatki =
COUNTROWS ( fact_safety_grid )
```

Format: liczba całkowita.

### Zagrożenia w siatce

```dax
Zagrożenia w siatce =
DISTINCTCOUNT ( fact_safety_grid[hazard_code] )
```

Format: liczba całkowita.

### Działy w siatce

```dax
Działy w siatce =
DISTINCTCOUNT ( fact_safety_grid[admin_division] )
```

Format: liczba całkowita.

## `fact_spo_checklist`

### Kroki SPO

```dax
Kroki SPO =
COUNTROWS ( fact_spo_checklist )
```

Format: liczba całkowita.

### Wymagane dokumenty

```dax
Wymagane dokumenty =
DISTINCTCOUNT ( fact_spo_checklist[required_document] )
```

Format: liczba całkowita.

## `fact_task_activation`

### Aktywacje modułów

```dax
Aktywacje modułów =
COUNTROWS ( fact_task_activation )
```

Format: liczba całkowita.

### Moduły aktywne

```dax
Moduły aktywne =
CALCULATE ( DISTINCTCOUNT ( fact_task_activation[task_module_id] ),
    fact_task_activation[activation_status] = "aktywny" )
```

Format: liczba całkowita.

### Pierwszy dzień aktywacji

```dax
Pierwszy dzień aktywacji =
MIN ( fact_task_activation[day_offset] )
```

Format: liczba całkowita.

## `gap_analysis_overdue`

### Zadania po SLA

```dax
Zadania po SLA =
COUNTROWS ( FILTER ( gap_analysis_overdue, gap_analysis_overdue[hours_over_sla] > 0 ) )
```

Format: liczba całkowita.

### Średnie przekroczenie SLA (h)

```dax
Średnie przekroczenie SLA (h) =
AVERAGE ( gap_analysis_overdue[hours_over_sla] )
```

Format: liczba z jednym miejscem.

### Największe przekroczenie SLA (h)

```dax
Największe przekroczenie SLA (h) =
MAX ( gap_analysis_overdue[hours_over_sla] )
```

Format: liczba z jednym miejscem.

### Zadania krytyczne po SLA

```dax
Zadania krytyczne po SLA =
CALCULATE ( [Zadania po SLA], gap_analysis_overdue[criticality] = "wysoka" )
```

Format: liczba całkowita.
