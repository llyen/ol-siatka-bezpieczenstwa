"""Tworzy raport Power BI OL_SIA_Raport (PBIR) na modelu OL_SIA_SemanticModel.

Uklad wynika z `report/REPORT_SPEC.md`: piec stron prowadzi rozmowe od pytania
"czym sie zajmujemy" (ryzyko), przez "kto za to odpowiada" (siatka, dzial),
po "co sie dzieje teraz" (aktywacja) i "co wymaga decyzji" (luki).

Paleta jasna, rzadowa - raport ma byc czytelny na rzutniku w sali posiedzen,
a nie na monitorze analityka. Wartosci kolorow za `_program/CONVENTIONS.md`.
"""
import argparse
import base64
import json
import subprocess
import time
from pathlib import Path

import requests

API = "https://api.fabric.microsoft.com/v1"
BASE = Path(__file__).resolve().parent.parent

_ap = argparse.ArgumentParser(description="Tworzy raport Power BI (PBIR) na modelu semantycznym.")
_ap.add_argument("--deployment", default=str(BASE / ".fabric" / "deployment.json"))
_ap.add_argument("--dataset", help="Identyfikator modelu (domyslnie z deployment.json).")
_ap.add_argument("--name", default="OL_SIA_Raport")
ARGS = _ap.parse_args()

CFG = json.load(open(ARGS.deployment, encoding="utf-8"))
WS = CFG["workspaceId"]
DATASET = ARGS.dataset or CFG["semanticModelId"]
NAME = ARGS.name
SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"

W, H = 1280, 720
PAGE_BG = "#f5f7fa"
CARD_BG = "#ffffff"
BORDER = "#d8dee6"
INK = "#1b1b1b"
MUTED = "#5b6674"
GOV = "#0052a5"
GOV_DARK = "#00417f"
GOV_50 = "#e8eef7"
RED = "#d5233f"
GREEN = "#15803d"
AMBER = "#a16207"
ORANGE = "#c2410c"

SIA = "fact_safety_grid"
PLAN = "activation_plan"
DECL = "fact_readiness_declaration"
GAP = "gap_analysis_overdue"
ACT = "fact_task_activation"
CHK = "fact_spo_checklist"
HAZ = "dim_hazard"
DIV = "dim_admin_division"
MOD = "dim_task_module"
CON = "dim_contact_point"
SPO = "dim_spo"


def measure(table, name):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def column(table, name):
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def proj(field, table, name):
    return {"field": field, "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def m(table, name):
    return proj(measure(table, name), table, name)


def c(table, name):
    return proj(column(table, name), table, name)


_seq = [0]


def visual(vtype, x, y, w, h, states, title=None, sort=None):
    _seq[0] += 1
    vid = f"v{_seq[0]:03d}"
    objects = {"title": [{"properties": {
        "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
        "fontColor": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{INK}'"}}}}},
        "fontSize": {"expr": {"Literal": {"Value": "12D"}}},
        "show": {"expr": {"Literal": {"Value": "true"}}},
    }}]} if title else {}
    v = {
        "$schema": f"{SCH}/visualContainer/1.4.0/schema.json",
        "name": vid,
        "position": {"x": x, "y": y, "z": _seq[0], "width": w, "height": h, "tabOrder": _seq[0]},
        "visual": {
            "visualType": vtype,
            "query": {"queryState": {k: {"projections": p} for k, p in states.items()}},
            "objects": objects,
            "drillFilterOtherVisuals": True,
        },
    }
    if sort:
        v["visual"]["query"]["sortDefinition"] = {"sort": sort}
    return v


def textbox(x, y, w, h, paragraphs):
    _seq[0] += 1
    vid = f"v{_seq[0]:03d}"
    return {
        "$schema": f"{SCH}/visualContainer/1.4.0/schema.json",
        "name": vid,
        "position": {"x": x, "y": y, "z": _seq[0], "width": w, "height": h, "tabOrder": _seq[0]},
        "visual": {"visualType": "textbox", "objects": {"general": [{"properties": {
            "paragraphs": [{"textRuns": [{"value": t, "textStyle": {
                "fontSize": f"{s}pt", "color": col, "fontWeight": "bold" if b else "normal"}}]}
                for t, s, col, b in paragraphs]}}]}},
    }


def sort_m(table, name, direction="Descending"):
    return [{"field": measure(table, name), "direction": direction}]


def sort_c(table, name, direction="Ascending"):
    return [{"field": column(table, name), "direction": direction}]


def naglowek(tytul, podtytul):
    return textbox(16, 12, 1248, 46, [(tytul, 18, INK, True),
                                      ("   " + podtytul, 11, MUTED, False)])


def stopka(jak_czytac):
    return textbox(16, 676, 1248, 34, [
        ("Jak czytac: " + jak_czytac, 10, MUTED, False),
        ("   Dane syntetyczne demo, seed=42.", 10, MUTED, False)])


PAGES = []


def page(name, display, visuals):
    PAGES.append((name, display, visuals))


# --- 1. Matryca ryzyka KPZK ---------------------------------------------------
page("s1", "1 | Matryca ryzyka", [
    naglowek("Matryca ryzyka KPZK",
             "wybierz zagrozenie - filtr przechodzi na kolejne strony"),
    visual("card", 16, 66, 240, 96, {"Values": [m(HAZ, "Zagrożenia w katalogu")]},
           "Zagrozen w katalogu"),
    visual("card", 268, 66, 240, 96, {"Values": [m(HAZ, "Zagrożenia wysokiego ryzyka")]},
           "Wysokiego ryzyka"),
    visual("card", 520, 66, 240, 96, {"Values": [m(HAZ, "Średnie ryzyko")]},
           "Srednia ocena ryzyka"),
    visual("card", 772, 66, 240, 96, {"Values": [m(HAZ, "Ryzyko skorygowane gotowością")]},
           "Ryzyko po korekcie o gotowosc"),
    visual("slicer", 1024, 66, 240, 268, {"Values": [c(HAZ, "category")]}, "Kategoria zagrozenia"),
    visual("pivotTable", 16, 174, 996, 300,
           {"Rows": [c(HAZ, "probability_label")], "Columns": [c(HAZ, "impact_label")],
            "Values": [m(HAZ, "Zagrożenia w katalogu")]},
           "Prawdopodobienstwo x skutki - liczba zagrozen"),
    visual("barChart", 16, 486, 500, 182,
           {"Category": [c(HAZ, "category")], "Y": [m(HAZ, "Średnie ryzyko")]},
           "Srednie ryzyko wg kategorii", sort=sort_m(HAZ, "Średnie ryzyko")),
    visual("tableEx", 528, 486, 736, 182,
           {"Values": [c(HAZ, "hazard_code"), c(HAZ, "hazard_name"), c(HAZ, "risk_level"),
                       c(HAZ, "risk_score"), c(HAZ, "probability_label"), c(HAZ, "impact_label")]},
           "Katalog zagrozen", sort=sort_c(HAZ, "risk_score", "Descending")),
    visual("slicer", 1024, 342, 240, 132, {"Values": [c(HAZ, "risk_level")]}, "Poziom ryzyka"),
    stopka("kafelki u gory to skala problemu, tabela po prawej to lista zagrozen "
           "posortowana od najgrozniejszego."),
])

# --- 2. Siatka bezpieczenstwa -------------------------------------------------
page("s2", "2 | Siatka bezpieczenstwa", [
    naglowek("Siatka bezpieczenstwa",
             "kto odpowiada za co - macierz zagrozenie x dzial administracji"),
    visual("card", 16, 66, 240, 96, {"Values": [m(SIA, "Komórki siatki")]}, "Komorek w siatce"),
    visual("card", 268, 66, 240, 96, {"Values": [m(SIA, "Zagrożenia w siatce")]},
           "Zagrozen objetych"),
    visual("card", 520, 66, 240, 96, {"Values": [m(SIA, "Działy w siatce")]}, "Dzialow objetych"),
    visual("card", 772, 66, 240, 96, {"Values": [m(DIV, "Ministerstwa")]}, "Ministerstw"),
    visual("slicer", 1024, 66, 240, 200, {"Values": [c(SIA, "phase")]}, "Faza"),
    visual("slicer", 1024, 274, 240, 200, {"Values": [c(SIA, "role")]}, "Rola"),
    visual("pivotTable", 16, 174, 996, 300,
           {"Rows": [c(DIV, "admin_name")], "Columns": [c(HAZ, "hazard_name")],
            "Values": [m(SIA, "Komórki siatki")]},
           "Macierz odpowiedzialnosci"),
    visual("tableEx", 16, 486, 1248, 182,
           {"Values": [c(SIA, "hazard_code"), c(DIV, "admin_name"), c(DIV, "ministry"),
                       c(SIA, "phase"), c(SIA, "role"), c(SIA, "criticality"),
                       c(SIA, "task_modules")]},
           "Szczegoly przypisan"),
    stopka("kazda komorka macierzy to przypisana odpowiedzialnosc; pusta komorka "
           "oznacza brak przypisania, nie brak danych."),
])

# --- 3. Panel dzialu administracji -------------------------------------------
page("s3", "3 | Panel dzialu", [
    naglowek("Panel dzialu administracji",
             "wybierz dzial po prawej - ekran odpowiada, co ma zrobic"),
    visual("card", 16, 66, 240, 96, {"Values": [m(PLAN, "Obciążenie działu")]},
           "Zadania wiodace dzialu"),
    visual("card", 268, 66, 240, 96, {"Values": [m(DECL, "Zadania gotowe")]}, "Gotowe"),
    visual("card", 520, 66, 240, 96, {"Values": [m(DECL, "Zadania zablokowane")]}, "Zablokowane"),
    visual("card", 772, 66, 240, 96, {"Values": [m(DECL, "Gotowość %")]}, "Gotowosc"),
    visual("slicer", 1024, 66, 240, 268, {"Values": [c(DIV, "admin_name")]}, "Dzial administracji"),
    visual("donutChart", 16, 174, 380, 288,
           {"Category": [c(DECL, "status")], "Y": [m(DECL, "Deklaracje gotowości")]},
           "Statusy deklaracji"),
    visual("tableEx", 408, 174, 604, 288,
           {"Values": [c(PLAN, "task_module_name"), c(PLAN, "role"), c(PLAN, "criticality"),
                       c(PLAN, "sla_hours"), c(PLAN, "phase")]},
           "Zadania przypisane dzialowi", sort=sort_c(PLAN, "dependency_order")),
    visual("slicer", 1024, 342, 240, 120, {"Values": [c(PLAN, "role")]}, "Rola w zadaniu"),
    visual("tableEx", 16, 474, 620, 194,
           {"Values": [c(CON, "role"), c(CON, "unit"), c(CON, "duty_phone"), c(CON, "email"),
                       c(CON, "deputy")]},
           "Punkty kontaktowe"),
    visual("tableEx", 648, 474, 616, 194,
           {"Values": [c(DECL, "task_module_id"), c(DECL, "status"), c(DECL, "readiness_date"),
                       c(DECL, "comment")]},
           "Ostatnie deklaracje", sort=sort_c(DECL, "readiness_date", "Descending")),
    stopka("kafelek Obciazenie liczy zadania, w ktorych dzial jest wiodacy; "
           "cztery i wiecej to przeciazenie jednego dyzuru."),
])

# --- 4. Postep aktywacji ------------------------------------------------------
page("s4", "4 | Postep aktywacji", [
    naglowek("Postep aktywacji w zdarzeniu",
             "os D-1...D+10 - ktore moduly zadaniowe juz pracuja"),
    visual("card", 16, 66, 240, 96, {"Values": [m(ACT, "Aktywacje modułów")]}, "Aktywacji lacznie"),
    visual("card", 268, 66, 240, 96, {"Values": [m(ACT, "Moduły aktywne")]}, "Modulow aktywnych"),
    visual("card", 520, 66, 240, 96, {"Values": [m(ACT, "Pierwszy dzień aktywacji")]},
           "Pierwszy dzien"),
    visual("card", 772, 66, 240, 96, {"Values": [m(MOD, "Moduły zadaniowe")]},
           "Modulow w katalogu"),
    visual("slicer", 1024, 66, 240, 200, {"Values": [c(ACT, "activation_status")]},
           "Status aktywacji"),
    visual("slicer", 1024, 274, 240, 200, {"Values": [c(ACT, "hazard_code")]}, "Zagrozenie"),
    visual("columnChart", 16, 174, 620, 288,
           {"Category": [c(ACT, "day_offset")], "Y": [m(ACT, "Aktywacje modułów")],
            "Series": [c(ACT, "activation_status")]},
           "Aktywacje wg doby zdarzenia", sort=sort_c(ACT, "day_offset")),
    visual("pivotTable", 648, 174, 364, 288,
           {"Rows": [c(MOD, "task_module_name")], "Columns": [c(ACT, "day_offset")],
            "Values": [m(ACT, "Aktywacje modułów")]},
           "Modul x doba"),
    visual("tableEx", 16, 474, 1248, 194,
           {"Values": [c(ACT, "day_offset"), c(MOD, "task_module_name"),
                       c(ACT, "leading_admin_division"), c(ACT, "activation_status"),
                       c(ACT, "trigger")]},
           "Wyzwalacze aktywacji", sort=sort_c(ACT, "day_offset")),
    stopka("doba ujemna to czas przed zdarzeniem - tam zapadaja decyzje "
           "o wyprzedzajacym uruchomieniu modulow."),
])

# --- 5. Analiza luk -----------------------------------------------------------
page("s5", "5 | Analiza luk", [
    naglowek("Analiza luk - co wymaga decyzji",
             "trzy liczby, ktore powinny paść na odprawie"),
    visual("card", 16, 66, 240, 96, {"Values": [m(DECL, "Zadania niegotowe")]}, "Niegotowe"),
    visual("card", 268, 66, 240, 96, {"Values": [m(GAP, "Zadania po SLA")]}, "Po terminie"),
    visual("card", 520, 66, 240, 96, {"Values": [m(DECL, "Zadania zablokowane")]}, "Zablokowane"),
    visual("card", 772, 66, 240, 96, {"Values": [m(DECL, "Indeks przygotowania")]},
           "Indeks przygotowania"),
    visual("card", 1024, 66, 240, 96, {"Values": [m(DECL, "Blokady na ścieżce krytycznej")]},
           "Blokady sciezki krytycznej"),
    visual("tableEx", 16, 174, 736, 288,
           {"Values": [c(GAP, "task_module_name"), c(GAP, "admin_name"), c(GAP, "criticality"),
                       c(GAP, "sla_hours"), c(GAP, "hours_over_sla"), c(GAP, "status")]},
           "Zadania po terminie", sort=sort_c(GAP, "hours_over_sla", "Descending")),
    visual("barChart", 764, 174, 500, 288,
           {"Category": [c(DIV, "admin_name")], "Y": [m(PLAN, "Zadania wiodące")]},
           "Obciazenie dzialow zadaniami wiodacymi", sort=sort_m(PLAN, "Zadania wiodące")),
    visual("card", 16, 474, 240, 96, {"Values": [m(DECL, "Działy bez deklaracji")]},
           "Dzialy bez deklaracji"),
    visual("card", 268, 474, 240, 96, {"Values": [m(PLAN, "Działy przeciążone")]},
           "Dzialy przeciazone"),
    visual("card", 520, 474, 240, 96, {"Values": [m(GAP, "Średnie przekroczenie SLA (h)")]},
           "Srednie przekroczenie (h)"),
    textbox(772, 474, 492, 194, [
        ("Rekomendacja na odprawe", 12, GOV_DARK, True),
        ("Blokady na sciezce krytycznej wstrzymuja wszystko, co za nimi - to one, "
         "a nie ogolny procent gotowosci, decyduja o terminie osiagniecia zdolnosci. "
         "Dzialy przeciazone wymagaja przesuniecia roli wiodacej albo wzmocnienia dyzuru; "
         "przeslanki eskalacji do RZZK opisuje SPO-1.", 10, INK, False)]),
    visual("pivotTable", 16, 578, 736, 90,
           {"Rows": [c(HAZ, "hazard_name")], "Values": [m(DECL, "Gotowość %")]},
           "Gotowosc wg zagrozenia"),
    stopka("indeks przygotowania to gotowosc pomniejszona o kary za blokady "
           "i przekroczenia terminow - sam procent gotowosci potrafi maskowac stojaca sciezke."),
])

THEME = {
    "name": "OL_SIA_Gov",
    "dataColors": [GOV, GOV_DARK, GREEN, AMBER, ORANGE, RED, "#7e22ce", "#64748b"],
    "background": PAGE_BG, "foreground": INK, "tableAccent": GOV,
    "good": GREEN, "neutral": AMBER, "bad": RED,
    "visualStyles": {"*": {"*": {
        "background": [{"color": {"solid": {"color": CARD_BG}}, "transparency": 0}],
        "border": [{"show": True, "color": {"solid": {"color": BORDER}}, "radius": 6}],
        "labels": [{"color": {"solid": {"color": INK}}}],
        "title": [{"fontColor": {"solid": {"color": INK}}, "fontSize": 12,
                   "background": {"solid": {"color": GOV_50}}}],
        "outspacePane": [{"backgroundColor": {"solid": {"color": CARD_BG}},
                          "foregroundColor": {"solid": {"color": INK}}}],
    }}},
}


def build_parts():
    parts = {}
    parts["definition.pbir"] = json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/"
                   "definitionProperties/1.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": None, "byConnection": {
            "connectionString": None, "pbiServiceModelId": None,
            "pbiModelVirtualServerName": "sobe_wowvirtualserver",
            "pbiModelDatabaseName": DATASET, "name": "EntityDataSource",
            "connectionType": "pbiServiceXmlaStyleLive"}}})
    parts["definition/version.json"] = json.dumps(
        {"$schema": f"{SCH}/versionMetadata/1.0.0/schema.json", "version": "4.0.0"})
    parts["definition/report.json"] = json.dumps({
        "$schema": f"{SCH}/report/1.4.0/schema.json",
        "themeCollection": {"customTheme": {"name": "OL_SIA_Gov", "type": "SharedResources",
                                            "reportVersionAtImport": "5.55"}},
        "layoutOptimization": "None",
        "settings": {"allowChangeFilterTypes": True},
    })
    parts["StaticResources/SharedResources/BaseThemes/OL_SIA_Gov.json"] = json.dumps(THEME)
    parts["definition/pages/pages.json"] = json.dumps({
        "$schema": f"{SCH}/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p[0] for p in PAGES], "activePageName": PAGES[0][0]})
    for pname, display, visuals in PAGES:
        parts[f"definition/pages/{pname}/page.json"] = json.dumps({
            "$schema": f"{SCH}/page/1.4.0/schema.json",
            "name": pname, "displayName": display, "displayOption": "FitToPage",
            "height": H, "width": W})
        for v in visuals:
            parts[f"definition/pages/{pname}/visuals/{v['name']}/visual.json"] = json.dumps(v)
    return [{"path": p, "payload": base64.b64encode(cnt.encode("utf-8")).decode(),
             "payloadType": "InlineBase64"} for p, cnt in parts.items()]


def naglowek_autoryzacji(tok):
    return " ".join(("Bearer", tok))


def main():
    tok = subprocess.run(["az", "account", "get-access-token", "--resource",
                          "https://api.fabric.microsoft.com", "--query", "accessToken", "-o", "tsv"],
                         capture_output=True, text=True, shell=True).stdout.strip()
    hh = {"Authorization": naglowek_autoryzacji(tok), "Content-Type": "application/json"}
    items = requests.get(f"{API}/workspaces/{WS}/items?type=Report", headers=hh).json()["value"]
    existing = next((i for i in items if i["displayName"] == NAME), None)
    definition = {"parts": build_parts()}
    if existing:
        r = requests.post(f"{API}/workspaces/{WS}/reports/{existing['id']}/updateDefinition",
                          headers=hh, json={"definition": definition})
        print("aktualizacja:", r.status_code, r.text[:1200])
        print("id:", existing["id"])
    else:
        r = requests.post(f"{API}/workspaces/{WS}/reports", headers=hh,
                          json={"displayName": NAME, "definition": definition})
        print("utworzenie:", r.status_code, r.text[:1200])
    if r.status_code == 202:
        loc = r.headers.get("Location")
        for _ in range(60):
            time.sleep(5)
            s = requests.get(loc, headers=hh).json()
            if s.get("status") in ("Succeeded", "Failed"):
                print(json.dumps(s, ensure_ascii=False)[:1500])
                break


if __name__ == "__main__":
    main()
