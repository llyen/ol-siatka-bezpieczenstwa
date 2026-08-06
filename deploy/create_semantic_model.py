"""Tworzy model semantyczny OL_SIA_SemanticModel (Direct Lake) w Microsoft Fabric.

Model jest wspólną warstwą dla raportu Power BI, Data Agenta i reguł Activatora —
opis w `semantic-model/MODEL.md`, miary w `semantic-model/MEASURES.md`.

Schematy tabel czytamy z `deploy/lakehouse_schemas.json` (zrzut z `get_schemas.py`),
a nie przepisujemy z dokumentacji: kolumny zmieniają się przy każdej zmianie
notatnika i ręczna lista rozjechałaby się po pierwszej takiej zmianie.
"""
import argparse
import base64
import json
import subprocess
import time
import uuid
from pathlib import Path

import requests

API = "https://api.fabric.microsoft.com/v1"
BASE = Path(__file__).resolve().parent.parent

_ap = argparse.ArgumentParser(description="Tworzy model semantyczny Direct Lake w Fabric.")
_ap.add_argument("--deployment", default=str(BASE / ".fabric" / "deployment.json"))
_ap.add_argument("--schemas", default=str(BASE / "deploy" / "lakehouse_schemas.json"))
_ap.add_argument("--name", default="OL_SIA_SemanticModel")
ARGS = _ap.parse_args()

CFG = json.load(open(ARGS.deployment, encoding="utf-8"))
WS = CFG["workspaceId"]
LAKEHOUSE = CFG["lakehouseName"]
SQL_EP = CFG["sqlEndpoint"]
NAME = ARGS.name

SCHEMAS = {t: [tuple(c) for c in cols]
           for t, cols in json.load(open(ARGS.schemas, encoding="utf-8")).items()}

DTYPE = {"string": "string", "integer": "int64", "long": "int64", "double": "double",
         "float": "double", "boolean": "boolean", "date": "dateTime", "timestamp": "dateTime"}

# Miary nazwane po polsku, bo to one pojawiają się w raporcie i w odpowiedziach
# Data Agenta — czyli u decydenta, nie u inżyniera.
MEASURES = {
    "fact_safety_grid": [
        ("Komórki siatki", "COUNTROWS ( fact_safety_grid )", "#,0"),
        ("Zagrożenia w siatce", "DISTINCTCOUNT ( fact_safety_grid[hazard_code] )", "#,0"),
        ("Działy w siatce", "DISTINCTCOUNT ( fact_safety_grid[admin_division] )", "#,0"),
    ],
    "activation_plan": [
        ("Zadania w planie", "COUNTROWS ( activation_plan )", "#,0"),
        ("Zadania wiodące",
         'CALCULATE ( COUNTROWS ( activation_plan ), activation_plan[role] = "wiodący" )', "#,0"),
        ("Zadania współpracujące",
         'CALCULATE ( COUNTROWS ( activation_plan ), activation_plan[role] = "współpracujący" )', "#,0"),
        ("Zadania krytyczne",
         'CALCULATE ( COUNTROWS ( activation_plan ), activation_plan[criticality] = "wysoka" )', "#,0"),
        ("Obciążenie działu", "[Zadania wiodące]", "#,0"),
        # Cztery zadania wiodące to próg, po którym dział prowadzi więcej wątków,
        # niż jest w stanie obsłużyć jednym dyżurem — stąd ta wartość, a nie okrągła piątka.
        ("Działy przeciążone",
         "COUNTROWS (\n"
         "    FILTER (\n"
         "        SUMMARIZE ( activation_plan, activation_plan[admin_division],\n"
         '            "Wiodace", [Zadania wiodące] ),\n'
         "        [Wiodace] >= 4\n"
         "    )\n"
         ")", "#,0"),
        ("Mediana SLA zadania (h)",
         "MEDIANX ( activation_plan, activation_plan[sla_hours] )", "#,0.0"),
    ],
    "fact_readiness_declaration": [
        ("Deklaracje gotowości", "COUNTROWS ( fact_readiness_declaration )", "#,0"),
        ("Zadania gotowe",
         'CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] = "gotowe" )', "#,0"),
        ("Zadania niegotowe",
         'CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] <> "gotowe" )', "#,0"),
        ("Zadania w toku",
         'CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] = "w toku" )', "#,0"),
        ("Zadania zablokowane",
         'CALCULATE ( [Deklaracje gotowości], fact_readiness_declaration[status] = "zablokowane" )', "#,0"),
        ("Gotowość %", "DIVIDE ( [Zadania gotowe], [Deklaracje gotowości] )", "0.0%"),
        ("Udział blokad %", "DIVIDE ( [Zadania zablokowane], [Deklaracje gotowości] )", "0.0%"),
        # Moduły 1-4 to zawiadomienie, ocena, zwołanie zespołu i uruchomienie sił.
        # Blokada tutaj wstrzymuje wszystko, co za nimi — dlatego liczona osobno.
        ("Blokady na ścieżce krytycznej",
         "CALCULATE ( [Zadania zablokowane],\n"
         "    fact_readiness_declaration[task_module_id] IN { 1, 2, 3, 4 } )", "#,0"),
        ("Działy bez deklaracji",
         "COUNTROWS ( EXCEPT (\n"
         "    VALUES ( dim_admin_division[admin_division] ),\n"
         "    VALUES ( fact_readiness_declaration[admin_division] )\n"
         ") )", "#,0"),
    ],
    "gap_analysis_overdue": [
        ("Zadania po SLA",
         "COUNTROWS ( FILTER ( gap_analysis_overdue, gap_analysis_overdue[hours_over_sla] > 0 ) )", "#,0"),
        ("Średnie przekroczenie SLA (h)",
         "AVERAGE ( gap_analysis_overdue[hours_over_sla] )", "#,0.0"),
        ("Największe przekroczenie SLA (h)",
         "MAX ( gap_analysis_overdue[hours_over_sla] )", "#,0.0"),
        ("Zadania krytyczne po SLA",
         'CALCULATE ( [Zadania po SLA], gap_analysis_overdue[criticality] = "wysoka" )', "#,0"),
    ],
    "fact_task_activation": [
        ("Aktywacje modułów", "COUNTROWS ( fact_task_activation )", "#,0"),
        ("Moduły aktywne",
         'CALCULATE ( DISTINCTCOUNT ( fact_task_activation[task_module_id] ),\n'
         '    fact_task_activation[activation_status] = "aktywny" )', "#,0"),
        ("Pierwszy dzień aktywacji", "MIN ( fact_task_activation[day_offset] )", "#,0"),
    ],
    "fact_spo_checklist": [
        ("Kroki SPO", "COUNTROWS ( fact_spo_checklist )", "#,0"),
        ("Wymagane dokumenty",
         "DISTINCTCOUNT ( fact_spo_checklist[required_document] )", "#,0"),
    ],
    "dim_hazard": [
        ("Zagrożenia w katalogu", "COUNTROWS ( dim_hazard )", "#,0"),
        ("Zagrożenia wysokiego ryzyka",
         'CALCULATE ( COUNTROWS ( dim_hazard ), dim_hazard[risk_level] = "wysokie" )', "#,0"),
        ("Średnie ryzyko", "AVERAGE ( dim_hazard[risk_score] )", "#,0.0"),
        # Ryzyko samo w sobie nie mówi, gdzie działać. Ryzyko przemnożone przez lukę
        # gotowości wskazuje zagrożenia, które są groźne i jednocześnie nieobsłużone.
        ("Ryzyko skorygowane gotowością",
         "AVERAGEX ( dim_hazard, dim_hazard[risk_score] * ( 1 - [Gotowość %] ) )", "#,0.0"),
    ],
    "dim_admin_division": [
        ("Działy administracji", "COUNTROWS ( dim_admin_division )", "#,0"),
        ("Ministerstwa", "DISTINCTCOUNT ( dim_admin_division[ministry] )", "#,0"),
    ],
    "dim_task_module": [
        ("Moduły zadaniowe", "COUNTROWS ( dim_task_module )", "#,0"),
    ],
    "dim_spo": [
        ("Procedury SPO", "COUNTROWS ( dim_spo )", "#,0"),
    ],
    "dim_contact_point": [
        ("Punkty kontaktowe", "COUNTROWS ( dim_contact_point )", "#,0"),
    ],
}

# Indeks przygotowania łączy trzy sygnały w jedną liczbę: gotowość obniżoną karą
# za blokady i za przekroczenia SLA. Bez kar sam procent gotowości wygląda dobrze
# nawet wtedy, gdy stoi ścieżka krytyczna.
MEASURES["fact_readiness_declaration"].append((
    "Indeks przygotowania",
    "VAR Gotowosc = [Gotowość %]\n"
    "VAR KaraBlokady = DIVIDE ( [Zadania zablokowane], [Deklaracje gotowości] )\n"
    "VAR KaraSla = DIVIDE ( [Zadania po SLA], [Deklaracje gotowości] )\n"
    "RETURN MAX ( 0, Gotowosc - KaraBlokady * 0.3 - KaraSla * 0.2 )", "0.00"))

RELATIONSHIPS = [
    ("dim_date", "date", "fact_readiness_declaration", "readiness_date"),
    ("dim_date", "date", "fact_task_activation", "activation_date"),
    ("dim_hazard", "hazard_code", "fact_safety_grid", "hazard_code"),
    ("dim_hazard", "hazard_code", "fact_task_activation", "hazard_code"),
    ("dim_hazard", "hazard_code", "activation_plan", "hazard_code"),
    ("dim_hazard", "hazard_code", "gap_analysis_overdue", "hazard_code"),
    ("dim_admin_division", "admin_division", "fact_safety_grid", "admin_division"),
    ("dim_admin_division", "admin_division", "fact_readiness_declaration", "admin_division"),
    ("dim_admin_division", "admin_division", "fact_spo_checklist", "responsible_admin_division"),
    ("dim_admin_division", "admin_division", "activation_plan", "admin_division"),
    ("dim_admin_division", "admin_division", "gap_analysis_overdue", "admin_division"),
    ("dim_admin_division", "admin_division", "dim_contact_point", "admin_division"),
    ("dim_task_module", "task_module_id", "fact_readiness_declaration", "task_module_id"),
    ("dim_task_module", "task_module_id", "fact_task_activation", "task_module_id"),
    ("dim_task_module", "task_module_id", "activation_plan", "task_module_id"),
    ("dim_task_module", "task_module_id", "gap_analysis_overdue", "task_module_id"),
    ("dim_task_module", "task_module_id", "fact_interdependency", "task_module_id"),
    # Druga noga zależności jest nieaktywna: dwie aktywne relacje do tego samego
    # wymiaru dałyby dwuznaczną ścieżkę filtrowania i model by się nie zapisał.
    ("dim_task_module", "task_module_id", "fact_interdependency", "depends_on_task_module_id", False),
    ("dim_spo", "spo_code", "fact_spo_checklist", "spo_code"),
]

# Tabele robocze grafu i jednowierszowe podsumowanie zasilają aplikację, a nie raport.
HIDDEN_TABLES = {"responsibility_graph_nodes", "responsibility_graph_edges",
                 "gap_analysis_summary"}
NUMERIC = {"int64", "double"}


def lt() -> str:
    return str(uuid.uuid4())


def ind(text: str, n: int) -> str:
    pad = "\t" * n
    return "\n".join(pad + line if line else line for line in text.split("\n"))


def table_tmdl(name: str, cols) -> str:
    out = [f"table {name}", ""]
    if name in HIDDEN_TABLES:
        out += ["\tisHidden", ""]
    if name == "dim_date":
        out += ["\tdataCategory: Time", ""]
    for m_name, expr, fmt in MEASURES.get(name, []):
        if "\n" in expr:
            out.append(f"\tmeasure '{m_name}' =")
            out.append(ind(expr, 3))
        else:
            out.append(f"\tmeasure '{m_name}' = {expr}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append("\t\tdisplayFolder: _Miary")
        out.append(f"\t\tlineageTag: {lt()}")
        out.append("")
    for col, typ in cols:
        dt = DTYPE.get(typ, "string")
        out.append(f"\tcolumn {col}")
        out.append(f"\t\tdataType: {dt}")
        if dt in NUMERIC and name.startswith(("fact_", "activation_plan", "gap_")):
            out.append("\t\tsummarizeBy: sum")
        else:
            out.append("\t\tsummarizeBy: none")
        out.append(f"\t\tsourceColumn: {col}")
        if name == "dim_date" and col == "date":
            out.append("\t\tisKey")
        if dt == "dateTime":
            out.append("\t\tformatString: " + ("Long Date" if typ == "date" else "General Date"))
        if col == "ingested_at":
            out.append("\t\tisHidden")
        out.append(f"\t\tlineageTag: {lt()}")
        out.append("")
    out += [f"\tpartition {name} = entity", "\t\tmode: directLake", "\t\tsource",
            f"\t\t\tentityName: {name}", "\t\t\texpressionSource: DatabaseQuery", "",
            "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(out)


def model_tmdl() -> str:
    out = ["model Model", "\tculture: pl-PL", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
           "\tsourceQueryCulture: pl-PL", "\tdataAccessOptions", "\t\tlegacyRedirects",
           "\t\treturnErrorValuesAsNull", ""]
    out += [f"ref table {t}" for t in sorted(SCHEMAS)]
    out += ["", "ref cultureInfo pl-PL", ""]
    for rel in RELATIONSHIPS:
        f, fc, tt, tc = rel[:4]
        active = rel[4] if len(rel) > 4 else True
        out.append(f"relationship rel_{f}_{fc}_{tt}_{tc}")
        out.append(f"\tfromColumn: {tt}.{tc}")
        out.append(f"\ttoColumn: {f}.{fc}")
        if not active:
            out.append("\tisActive: false")
        out.append("")
    return "\n".join(out)


PBISM = {"version": "4.0", "settings": {"qnaEnabled": True}}
DATABASE = "database\n\tcompatibilityLevel: 1604\n"
EXPR = (f'expression DatabaseQuery =\n'
        f'\t\tlet\n'
        f'\t\t    database = Sql.Database("{SQL_EP}", "{LAKEHOUSE}")\n'
        f'\t\tin\n'
        f'\t\t    database\n'
        f'\tlineageTag: {lt()}\n'
        f'\tannotation PBI_IncludeFutureArtifacts = False\n')
CULTURE = ('cultureInfo pl-PL\n\tlinguisticMetadata =\n\t\t\t{\n\t\t\t  "Version": "1.0.0",\n'
           '\t\t\t  "Language": "pl-PL"\n\t\t\t}\n\t\tcontentType: json\n')


def build_parts():
    parts = {
        "definition.pbism": json.dumps(PBISM),
        "definition/database.tmdl": DATABASE,
        "definition/model.tmdl": model_tmdl(),
        "definition/expressions.tmdl": EXPR,
        "definition/cultures/pl-PL.tmdl": CULTURE,
    }
    for t, cols in SCHEMAS.items():
        parts[f"definition/tables/{t}.tmdl"] = table_tmdl(t, cols)
    return [{"path": p, "payload": base64.b64encode(c.encode("utf-8")).decode(),
             "payloadType": "InlineBase64"} for p, c in parts.items()]


def main() -> None:
    tok = subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://api.fabric.microsoft.com",
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, shell=True).stdout.strip()
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    items = requests.get(f"{API}/workspaces/{WS}/items?type=SemanticModel", headers=h).json()["value"]
    existing = next((i for i in items if i["displayName"] == NAME), None)
    definition = {"parts": build_parts()}
    if existing:
        r = requests.post(f"{API}/workspaces/{WS}/semanticModels/{existing['id']}/updateDefinition",
                          headers=h, json={"definition": definition})
        print("aktualizacja:", r.status_code, r.text[:1500])
        print("id:", existing["id"])
    else:
        r = requests.post(f"{API}/workspaces/{WS}/semanticModels", headers=h,
                          json={"displayName": NAME, "definition": definition})
        print("utworzenie:", r.status_code, r.text[:1500])
        if r.status_code == 202:
            loc = r.headers.get("Location")
            for _ in range(60):
                time.sleep(5)
                s = requests.get(loc, headers=h).json()
                if s.get("status") in ("Succeeded", "Failed"):
                    print(json.dumps(s, ensure_ascii=False)[:1500])
                    break


if __name__ == "__main__":
    main()
