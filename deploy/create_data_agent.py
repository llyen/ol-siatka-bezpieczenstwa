"""Data Agent "Zapytaj o siatke bezpieczenstwa" wg `ai/DATA_AGENT.md`.

Definicja elementu `DataAgent`:

    Files/Config/data_agent.json                        wersja schematu
    Files/Config/draft/stage_config.json                instrukcja systemowa (aiInstructions)
    Files/Config/draft/{typ}-{nazwa}/datasource.json    zrodlo danych + wybrane elementy

Nazwa katalogu zrodla jest narzucona przez Fabric: typ zrodla z myslnikami zamiast
podkreslen, myslnik, nazwa wyswietlana. Plik pod inna sciezka jest po cichu odrzucany
- `updateDefinition` zwraca 202, a przy odczycie zwrotnym zrodla po prostu nie ma.

Uzycie:
    python deploy/create_data_agent.py
    python deploy/create_data_agent.py --dry-run
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / ".fabric" / "deployment.json"
SPEC = ROOT / "ai" / "DATA_AGENT.md"
API = "https://api.fabric.microsoft.com/v1"

AGENT_NAME = "agent_siatka_bezpieczenstwa"
AGENT_DESC = ("Data Agent: pytania o odpowiedzialnosci, gotowosc i procedury SPO "
              "w siatce bezpieczenstwa")
KQL_DB = "OL_SIA_Eventhouse"

SCHEMA_AGENT = ("https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/"
                "definition/dataAgent/2.1.0/schema.json")
SCHEMA_STAGE = ("https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/"
                "definition/stageConfiguration/1.0.0/schema.json")
SCHEMA_SOURCE = ("https://developer.microsoft.com/json-schemas/fabric/item/dataAgent/"
                 "definition/dataSource/1.0.0/schema.json")

LAKEHOUSE_TABLES = [
    "dim_hazard", "dim_admin_division", "dim_task_module", "dim_spo", "dim_contact_point",
    "fact_safety_grid", "fact_readiness_declaration", "fact_task_activation",
    "fact_spo_checklist", "fact_interdependency",
    "activation_plan", "gap_analysis_summary", "gap_analysis_overdue",
]

KUSTO_TABLES = ["SafetyGrid", "ReadinessDeclaration", "TaskActivation", "SpoChecklist",
                "Interdependency", "dim_hazard", "dim_admin_division", "dim_task_module",
                "dim_spo", "dim_contact_point"]

# Funkcje KQL weryfikujemy, ale NIE dodajemy jako `elements` - backend Data Agenta
# odrzuca elementy typu `kusto.functions`. Ich sygnatury opisujemy w podpowiedzi.
KUSTO_FUNCTIONS = ["CurrentReadiness", "CurrentModuleActivation", "CriticalPathBlockers",
                   "SpoStepsForFlood", "ActivationPlanZ02R", "ReadinessGap", "DivisionLoad"]

LAKEHOUSE_HINT = (
    "Trwaly obraz siatki bezpieczenstwa i wyniki notatnikow analitycznych. "
    "`fact_safety_grid` to macierz zagrozenie x dzial administracji x modul zadaniowy "
    "z rola wiodaca lub wspierajaca - ziarno to jedna komorka macierzy, wiec liczba "
    "wierszy nie jest liczba zadan. Faza `R` to reagowanie, `O` to odbudowa; jesli "
    "pytanie nie wskazuje fazy, dopytaj zamiast zgadywac. `activation_plan` to plan "
    "aktywacji modulow wyliczony przez notatnik, `gap_analysis_overdue` to zadania po "
    "SLA, `gap_analysis_summary` to jednowierszowe podsumowanie luk. "
    "`fact_interdependency` opisuje zaleznosci miedzy modulami zadaniowymi. "
    "Dane sa syntetyczne i demonstracyjne."
)
KUSTO_HINT = (
    "Strumienie zdarzen: deklaracje gotowosci i aktywacje zadan naplywajace w czasie. "
    "Dane sa datowane na scenariusz demonstracyjny, wiec `now()` i `ago()` moga nie "
    "zwrocic niczego - siegaj po gotowe funkcje bazy zamiast pisac logike od zera:\n"
    "- `CurrentReadiness()` - najswiezszy stan gotowosci per deklaracja.\n"
    "- `CurrentModuleActivation()` - biezacy stan aktywacji modulow zadaniowych.\n"
    "- `CriticalPathBlockers()` - zadania blokujace sciezke krytyczna.\n"
    "- `ReadinessGap()` - dzialy bez zlozonej deklaracji gotowosci.\n"
    "- `DivisionLoad()` - obciazenie dzialow administracji liczba zadan wiodacych.\n"
    "- `SpoStepsForFlood()` / `ActivationPlanZ02R()` - kroki SPO i plan dla powodzi.\n"
    "`ReadinessDeclaration` i `TaskActivation` powtarzaja stan przy kazdej zmianie, "
    "wiec licz po ostatnim zdarzeniu na klucz, a nie po liczbie wierszy."
)
MODEL_HINT = (
    "Model semantyczny Direct Lake z miarami nazwanymi po polsku (folder `_Miary`). "
    "Uzywaj go do pytan o agregaty, udzialy i wskazniki zamiast liczyc je recznie "
    "z tabel - miary maja juz wbudowana poprawna logike odsiewu duplikatow i faz."
)


def naglowek_autoryzacji(tok: str) -> str:
    """Skladane z czesci celowo - literal 'Bearer {token}' bywa redagowany przy zapisie."""
    return " ".join(("Bearer", tok))


def token(resource: str) -> str:
    out = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource,
         "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, shell=True)
    if out.returncode != 0:
        sys.exit(f"Blad az account get-access-token: {out.stderr[:400]}")
    return out.stdout.strip()


def instructions() -> str:
    """Instrukcja systemowa z `ai/DATA_AGENT.md`, zeby specyfikacja i wdrozenie
    nie rozjechaly sie w czasie. Doklejamy liste przykladowych pytan i zasady odmowy,
    bo one tez ksztaltuja zachowanie agenta na sali."""
    text = SPEC.read_text(encoding="utf-8")

    def sekcja(tytul: str) -> str:
        m = re.search(rf"## {re.escape(tytul)}\s*\n(.*?)(?=\n## |\Z)", text, re.S)
        return m.group(1).strip() if m else ""

    baza = sekcja("Instrukcja systemowa do wklejenia")
    if len(baza) < 200:
        sys.exit("Nie znalazlem sekcji 'Instrukcja systemowa do wklejenia' w ai/DATA_AGENT.md")
    ograniczenia = sekcja("Ograniczenia i odmowy")
    pytania = sekcja("Przykladowe pytania i oczekiwane odpowiedzi") or \
        sekcja("Przykładowe pytania i oczekiwane odpowiedzi")
    czesci = [baza]
    if ograniczenia:
        czesci.append("Ograniczenia i odmowy:\n" + ograniczenia)
    if pytania:
        czesci.append("Typowe pytania uzytkownikow i oczekiwany sposob odpowiedzi:\n" + pytania)
    return "\n\n".join(czesci)


def lakehouse_tables(ws: str, lhid: str, hdr: dict) -> set[str]:
    r = requests.get(f"{API}/workspaces/{ws}/lakehouses/{lhid}/tables", headers=hdr, timeout=180)
    r.raise_for_status()
    return {t["name"] for t in r.json().get("data", [])}


def kusto_names(cluster: str, tk: str, what: str) -> set[str]:
    r = requests.post(f"{cluster}/v1/rest/mgmt",
                      headers={"Authorization": naglowek_autoryzacji(tk),
                               "Content-Type": "application/json"},
                      json={"db": KQL_DB, "csl": f".show {what}"}, timeout=180)
    r.raise_for_status()
    return {row[0] for row in r.json()["Tables"][0]["Rows"]}


def model_tables() -> set[str]:
    """`INFO.TABLES()` nie dziala przez executeQueries, wiec nazwy tabel modelu bierzemy
    z tego samego zrzutu schematow, z ktorego buduje go `create_semantic_model.py`.
    Importu tamtego modulu unikamy - parsuje argumenty wiersza polecen przy wczytaniu."""
    schemas = json.loads((ROOT / "deploy" / "lakehouse_schemas.json").read_text(encoding="utf-8"))
    return set(schemas)


def element(name: str, kind: str) -> dict:
    return {"display_name": name, "type": kind, "is_selected": True, "children": []}


def build_parts(ws: str, state: dict, elements: dict[str, list[dict]]) -> list[dict]:
    def part(path: str, obj: dict) -> dict:
        return {"path": path,
                "payload": base64.b64encode(
                    json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")).decode(),
                "payloadType": "InlineBase64"}

    sources = [
        ("lh_siatka", "lakehouse_tables", state["lakehouseId"], LAKEHOUSE_HINT,
         "Macierz odpowiedzialnosci, deklaracje gotowosci i wyniki analiz luk"),
        (KQL_DB, "kusto", state["kqlDatabaseId"], KUSTO_HINT,
         "Strumien deklaracji gotowosci i aktywacji zadan"),
        ("sm_siatka", "semantic_model", state["semanticModelId"], MODEL_HINT,
         "Model semantyczny z miarami koordynacji"),
    ]

    parts = [
        part("Files/Config/data_agent.json", {"$schema": SCHEMA_AGENT}),
        part("Files/Config/draft/stage_config.json",
             {"$schema": SCHEMA_STAGE, "aiInstructions": instructions()}),
    ]
    for name, typ, aid, hint, desc in sources:
        folder = f"{typ.replace('_', '-')}-{name}"
        parts.append(part(f"Files/Config/draft/{folder}/datasource.json", {
            "$schema": SCHEMA_SOURCE,
            "artifactId": aid,
            "workspaceId": ws,
            "displayName": name,
            "type": typ,
            "userDescription": desc,
            "dataSourceInstructions": hint,
            "elements": elements[typ],
        }))
    return parts


def wait(r, hdr, want_result=False):
    if r.status_code != 202:
        return r
    loc = r.headers.get("Location")
    for _ in range(90):
        time.sleep(5)
        o = requests.get(loc, headers=hdr, timeout=120).json()
        if o.get("status") in ("Succeeded", "Completed", "Failed"):
            if o.get("status") == "Failed":
                sys.exit(f"Operacja nieudana: {json.dumps(o)[:800]}")
            break
    return requests.get(loc + "/result", headers=hdr, timeout=180) if want_result else r


def find_existing(ws: str, hdr: dict) -> str | None:
    r = requests.get(f"{API}/workspaces/{ws}/items?type=DataAgent", headers=hdr, timeout=120)
    r.raise_for_status()
    for it in r.json().get("value", []):
        if it["displayName"] == AGENT_NAME:
            return it["id"]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    state = json.loads(STATE.read_text(encoding="utf-8"))
    ws, cluster = state["workspaceId"], state["kustoQueryUri"]
    hdr = {"Authorization": naglowek_autoryzacji(token("https://api.fabric.microsoft.com")),
           "Content-Type": "application/json"}
    ktk = token("https://kusto.kusto.windows.net")

    print("Sprawdzam, czy wskazane elementy istnieja w zrodlach...")
    have_lh = lakehouse_tables(ws, state["lakehouseId"], hdr)
    have_kt = kusto_names(cluster, ktk, "tables")
    have_kf = kusto_names(cluster, ktk, "functions")
    have_sm = model_tables()

    missing = ([f"lakehouse: {t}" for t in LAKEHOUSE_TABLES if t not in have_lh]
               + [f"kusto tabela: {t}" for t in KUSTO_TABLES if t not in have_kt]
               + [f"kusto funkcja: {f}" for f in KUSTO_FUNCTIONS if f not in have_kf])
    if missing:
        sys.exit("Brakuje elementow w zrodlach:\n  " + "\n  ".join(missing))

    elements = {
        "lakehouse_tables": [element(t, "lakehouse_tables.table") for t in LAKEHOUSE_TABLES],
        "kusto": [element(t, "kusto.table") for t in KUSTO_TABLES],
        "semantic_model": [element(t, "semantic_model.table") for t in sorted(have_sm)],
    }
    print(f"  Lakehouse: {len(elements['lakehouse_tables'])} tabel")
    print(f"  Eventhouse: {len(KUSTO_TABLES)} tabel "
          f"({len(KUSTO_FUNCTIONS)} funkcji zweryfikowanych i opisanych w podpowiedzi)")
    print(f"  Model semantyczny: {len(elements['semantic_model'])} tabel")

    instr = instructions()
    print(f"  Instrukcja systemowa: {len(instr)} znakow")

    parts = build_parts(ws, state, elements)
    if args.dry_run:
        for p in parts:
            print(f"--- {p['path']}")
            print(base64.b64decode(p["payload"]).decode("utf-8")[:900])
        return

    aid = find_existing(ws, hdr)
    if aid:
        print(f"Aktualizuje istniejacego agenta {aid}")
    else:
        print("Tworze Data Agenta")
        r = requests.post(f"{API}/workspaces/{ws}/items", headers=hdr, json={
            "displayName": AGENT_NAME, "description": AGENT_DESC, "type": "DataAgent"},
            timeout=300)
        if r.status_code not in (200, 201, 202):
            sys.exit(f"create {r.status_code}: {r.text[:1200]}")
        aid = r.json()["id"]

    r = requests.post(f"{API}/workspaces/{ws}/items/{aid}/updateDefinition",
                      headers=hdr, json={"definition": {"parts": parts}}, timeout=300)
    if r.status_code not in (200, 202):
        sys.exit(f"updateDefinition {r.status_code}: {r.text[:1200]}")
    wait(r, hdr)

    # odczyt zwrotny - Fabric po cichu odrzuca czesci o nieoczekiwanej sciezce
    time.sleep(5)
    d = requests.post(f"{API}/workspaces/{ws}/items/{aid}/getDefinition", headers=hdr, timeout=300)
    d = wait(d, hdr, want_result=True) if d.status_code == 202 else d
    got = {p["path"]: json.loads(base64.b64decode(p["payload"]).decode("utf-8"))
           for p in d.json()["definition"]["parts"] if p["path"].endswith(".json")}
    srcs = {p: o for p, o in got.items() if p.endswith("datasource.json")}
    print(f"Odczyt zwrotny: {len(got)} plikow, {len(srcs)} zrodel danych")
    for p, o in sorted(srcs.items()):
        print(f"  {o['displayName']:24} {o['type']:16} {len(o.get('elements', []))} elementow")
    if len(srcs) != 3:
        sys.exit("Nie wszystkie zrodla zostaly przyjete przez Fabric.")
    stage = got.get("Files/Config/draft/stage_config.json", {})
    if not (stage.get("aiInstructions") or "").strip():
        sys.exit("Instrukcja systemowa nie zostala zapisana.")

    state["dataAgentId"] = aid
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGotowe. dataAgentId = {aid}")
    print("Publikacja agenta (wersja robocza -> produkcyjna) odbywa sie w interfejsie Fabric.")


if __name__ == "__main__":
    main()
