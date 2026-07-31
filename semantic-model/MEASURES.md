# Miary DAX

Poniższe miary są wzorcem dla modelu semantycznego. Nazwy tabel mogą wymagać dopasowania po utworzeniu bridge table `bridge_grid_module`. Każda miara powinna mieć opis w modelu i format wskazany poniżej.

## 1. Hazard Count — liczba zagrożeń (Whole number)
```dax
Hazard Count = COUNTROWS(dim_hazard)
```

## 2. Admin Division Count — liczba działów (Whole number)
```dax
Admin Division Count = COUNTROWS(dim_admin_division)
```

## 3. Safety Grid Cells — komórki siatki (Whole number)
```dax
Safety Grid Cells = COUNTROWS(fact_safety_grid)
```

## 4. Active Plan Tasks — zadania w planie (Whole number)
```dax
Active Plan Tasks = COUNTROWS(activation_plan)
```

## 5. Leading Tasks — zadania wiodące (Whole number)
```dax
Leading Tasks =
CALCULATE(COUNTROWS(activation_plan), activation_plan[role] = "wiodący")
```

## 6. Cooperation Tasks — zadania współpracujące (Whole number)
```dax
Cooperation Tasks =
CALCULATE(COUNTROWS(activation_plan), activation_plan[role] = "współpracujący")
```

## 7. Ready Tasks — zadania gotowe (Whole number)
```dax
Ready Tasks =
CALCULATE(COUNTROWS(fact_readiness_declaration), fact_readiness_declaration[status] = "gotowe")
```

## 8. Not Ready Tasks — zadania niegotowe (Whole number)
```dax
Not Ready Tasks =
CALCULATE(
    COUNTROWS(fact_readiness_declaration),
    fact_readiness_declaration[status] <> "gotowe"
)
```

## 9. Readiness % — procent gotowości (Percentage, 1 decimal)
```dax
Readiness % =
DIVIDE([Ready Tasks], COUNTROWS(fact_readiness_declaration), 0)
```

## 10. Blocked Tasks — blokady (Whole number)
```dax
Blocked Tasks =
CALCULATE(COUNTROWS(fact_readiness_declaration), fact_readiness_declaration[status] = "zablokowane")
```

## 11. In Progress Tasks — w toku (Whole number)
```dax
In Progress Tasks =
CALCULATE(COUNTROWS(fact_readiness_declaration), fact_readiness_declaration[status] = "w toku")
```

## 12. Tasks Over SLA — po SLA (Whole number)
```dax
Tasks Over SLA =
COUNTROWS(FILTER(gap_analysis_overdue, gap_analysis_overdue[hours_over_sla] > 0))
```

## 13. Average Hours Over SLA — średnie opóźnienie (Decimal, 1 decimal)
```dax
Average Hours Over SLA =
AVERAGE(gap_analysis_overdue[hours_over_sla])
```

## 14. Division Load — obciążenie działu (Whole number)
```dax
Division Load =
CALCULATE(COUNTROWS(activation_plan), activation_plan[role] = "wiodący")
```

## 15. Overloaded Divisions — przeciążone działy (Whole number)
```dax
Overloaded Divisions =
COUNTROWS(
    FILTER(
        SUMMARIZE(activation_plan, activation_plan[admin_division], "lead_count", [Division Load]),
        [lead_count] >= 4
    )
)
```

## 16. Hazard Preparedness Index — indeks przygotowania (Decimal, 0.00)
```dax
Hazard Preparedness Index =
VAR readiness = [Readiness %]
VAR blockedPenalty = DIVIDE([Blocked Tasks], COUNTROWS(fact_readiness_declaration), 0)
VAR slaPenalty = DIVIDE([Tasks Over SLA], COUNTROWS(fact_readiness_declaration), 0)
RETURN MAX(0, readiness - blockedPenalty * 0.3 - slaPenalty * 0.2)
```

## 17. Risk x Readiness Heatmap — ryzyko skorygowane gotowością (Decimal, 0.0)
```dax
Risk x Readiness Heatmap =
AVERAGEX(dim_hazard, dim_hazard[risk_score] * (1 - [Readiness %]))
```

## 18. Critical Path Blockers — blokady krytyczne (Whole number)
```dax
Critical Path Blockers =
CALCULATE(
    [Blocked Tasks],
    fact_readiness_declaration[task_module_id] IN {1, 2, 3, 4}
)
```

## 19. SPO Steps — kroki SPO (Whole number)
```dax
SPO Steps = COUNTROWS(fact_spo_checklist)
```

## 20. Contact Points — kontakty dyżurne (Whole number)
```dax
Contact Points = COUNTROWS(dim_contact_point)
```
