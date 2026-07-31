# Reguły Data Activator

## Założenia

Reguły obserwują tabele `activation_plan`, `fact_readiness_declaration`, `gap_analysis_overdue`, `gap_analysis_summary` i opcjonalnie `fact_task_activation`. Progi są dobrane do demo tak, aby pokazać reakcję w trakcie prezentacji. W produkcji należy je zatwierdzić formalnie dla każdego typu zagrożenia i fazy.

## 1. SLA exceeded

**Cel biznesowy:** wykryć zadania, które nie są `gotowe` po przekroczeniu SLA.  
**Źródło danych:** `gap_analysis_overdue`.  
**Warunek KQL/pseudokod:**
```kql
gap_analysis_overdue
| where hours_over_sla > 0 and status != "gotowe"
```
**Próg:** `hours_over_sla > 0`; w danych demo jest 28 takich zadań.  
**Odbiorca:** dyżurny działu, RCB coordinator.  
**Treść:** „Zadanie {task_module_name} dla działu {admin_division} przekroczyło SLA o {hours_over_sla} h.”  
**Akcja:** potwierdzić status lub zgłosić blokadę. **SPO:** `SPO-12` obieg informacji.

## 2. Missing readiness declaration

**Cel biznesowy:** wykryć brak deklaracji po aktywacji modułu.  
**Źródło danych:** `activation_plan` left join `fact_readiness_declaration`.  
**Warunek:**
```kql
activation_plan
| join kind=leftanti fact_readiness_declaration on admin_division, task_module_id
```
**Próg:** brak deklaracji po 6 godzinach od aktywacji; 6 h jest wystarczająco krótkie dla demo i pokazuje presję czasu w fazie `R`.  
**Odbiorca:** Ministry duty officer i RCB coordinator.  
**Treść:** „Brak deklaracji gotowości dla modułu {task_module_id} w dziale {admin_division}.”  
**Akcja:** wysłać przypomnienie i oznaczyć rekord jako `brak deklaracji`. **SPO:** `SPO-12`.

## 3. Critical path blocker

**Cel biznesowy:** natychmiast eskalować blokadę na modułach ścieżki krytycznej `[1,2,4,3]`.  
**Źródło:** `fact_readiness_declaration`, `fact_interdependency`.  
**Warunek:**
```kql
fact_readiness_declaration
| where status == "zablokowane" and task_module_id in (1,2,3,4)
```
**Próg:** każda blokada; w danych demo jest 9 blokad łącznie.  
**Odbiorca:** RCB coordinator, dyrektor RCB.  
**Treść:** „Blokada na ścieżce krytycznej: moduł {task_module_id}, dział {admin_division}, komentarz {comment}.”  
**Akcja:** otworzyć ekran RCB i rozważyć `Escalate to RZZK`. **SPO:** `SPO-1`, `SPO-12`.

## 4. Division overload

**Cel biznesowy:** wykryć przeciążenie działu wiodącego.  
**Źródło:** `activation_plan`.  
**Warunek:**
```kql
activation_plan
| where role == "wiodący"
| summarize lead_count=count() by admin_division
| where lead_count >= 4
```
**Próg:** co najmniej 4 zadania wiodące; w danych demo `VIII` i `XIX` mają po 5.  
**Odbiorca:** RCB coordinator.  
**Treść:** „Dział {admin_division} jest wiodący w {lead_count} zadaniach. Sprawdź potrzebę wsparcia lub redystrybucji.”  
**Akcja:** przydzielić wsparcie, zwołać uzgodnienie międzyresortowe. **SPO:** `SPO-1`.

## 5. Disinformation coupling

**Cel biznesowy:** wymusić moduł 7, gdy `Z20 Dezinformacja` współwystępuje z powodzią.  
**Źródło:** `fact_task_activation`, `activation_plan`.  
**Warunek:**
```kql
fact_task_activation
| where hazard_code in ("Z02","Z20")
| summarize hazards=make_set(hazard_code) by event_id
| where set_has_element(hazards, "Z02") and set_has_element(hazards, "Z20")
```
**Próg:** każde współwystąpienie.  
**Odbiorca:** RCB communication lead, `X Informatyzacja`, `I Administracja publiczna`.  
**Treść:** „Aktywna powódź i dezinformacja. Wymagane wzmocnienie modułu 7 Ochrona informacji.”  
**Akcja:** uruchomić komunikację publiczną i monitoring narracji. **SPO:** `SPO-3`, `SPO-16`.

## 6. RZZK escalation candidate

**Cel biznesowy:** wskazać zdarzenie wymagające poziomu RZZK.  
**Źródło:** `gap_analysis_summary`.  
**Warunek:** `blocked_tasks >= 1 OR overloaded_leading_divisions not empty OR overdue_tasks >= 5`.  
**Próg:** w demo spełniony: 9 blokad i 28 po SLA.  
**Odbiorca:** dyrektor RCB.  
**Treść:** „Zdarzenie spełnia warunki kandydackie do eskalacji RZZK. Rekomendowana procedura: SPO-1.”  
**Akcja:** wygenerować listę uczestników i pakiet decyzyjny.
