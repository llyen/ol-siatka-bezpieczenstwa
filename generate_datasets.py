"""Generate deterministic synthetic datasets for OL Safety Grid demo (seed=42)."""
from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
random.seed(SEED)
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "datasets"
DERIVED = DATA / "derived"
DATA.mkdir(exist_ok=True)
DERIVED.mkdir(exist_ok=True)
TZ = timezone(timedelta(hours=2))

PROB = {"bardzo rzadkie": 1, "rzadkie": 2, "możliwe": 3, "prawdopodobne": 4, "bardzo prawdopodobne": 5}
IMPACT = {"nieistotne": 1, "małe": 2, "średnie": 3, "duże": 4, "katastrofalne": 5}


def risk_color(score: int) -> str:
    if score <= 6:
        return "zielony"
    if score <= 14:
        return "żółty"
    if score <= 24:
        return "czerwony"
    return "brązowy/krytyczny"


def risk_level(score: int) -> str:
    if score <= 6:
        return "niskie"
    if score <= 14:
        return "podwyższone"
    if score <= 24:
        return "wysokie"
    return "krytyczne"


HAZARDS = [
    ("Z01", "Epidemia", "społeczne", "możliwe", "katastrofalne"),
    ("Z02", "Powódź", "naturalne", "prawdopodobne", "duże"),
    ("Z03", "Zakłócenie funkcjonowania systemów i sieci teleinformatycznych", "techniczne", "możliwe", "duże"),
    ("Z04", "Działania hybrydowe", "hybrydowe", "możliwe", "duże"),
    ("Z05", "Susza/upał", "naturalne", "prawdopodobne", "średnie"),
    ("Z06", "Epizootia", "naturalne", "prawdopodobne", "średnie"),
    ("Z07", "Zakłócenie w systemie energetycznym", "techniczne", "prawdopodobne", "średnie"),
    ("Z08", "Silny wiatr", "naturalne", "prawdopodobne", "średnie"),
    ("Z09", "Zakłócenie w systemie paliwowym", "techniczne", "możliwe", "średnie"),
    ("Z10", "Pożar wielkopowierzchniowy", "naturalne", "możliwe", "średnie"),
    ("Z11", "Epifitoza", "naturalne", "możliwe", "średnie"),
    ("Z12", "Zakłócenie funkcjonowania systemów i usług telekomunikacyjnych", "techniczne", "możliwe", "średnie"),
    ("Z13", "Skażenie chemiczne na lądzie", "techniczne", "rzadkie", "małe"),
    ("Z14", "Zakłócenie w systemie gazowym", "techniczne", "rzadkie", "średnie"),
    ("Z15", "Katastrofa morska", "techniczne", "rzadkie", "średnie"),
    ("Z16", "Zdarzenie o charakterze terrorystycznym", "społeczne", "bardzo rzadkie", "duże"),
    ("Z17", "Skażenie promieniotwórcze", "techniczne", "bardzo rzadkie", "duże"),
    ("Z18", "Zbiorowe zakłócenie porządku publicznego", "społeczne", "prawdopodobne", "małe"),
    ("Z19", "Silny mróz/intensywne opady śniegu", "naturalne", "możliwe", "małe"),
    ("Z20", "Dezinformacja", "hybrydowe", "możliwe", "średnie"),
]

DIVISIONS = [
    ("I", "Administracja publiczna", "Minister Spraw Wewnętrznych i Administracji", "RCB; wojewodowie; administracja zespolona"),
    ("II", "Budownictwo, planowanie przestrzenne i mieszkalnictwo", "Minister Rozwoju i Technologii", "GUNB; instytuty budownictwa; nadzór budowlany"),
    ("III", "Budżet", "Minister Finansów", "Departament Budżetu Państwa; dysponenci części budżetowych"),
    ("IV", "Energia", "Minister Klimatu i Środowiska", "operatorzy systemów energetycznych; URE"),
    ("V", "Finanse publiczne", "Minister Finansów", "KAS; BGK; jednostki finansów publicznych"),
    ("VI", "Gospodarka", "Minister Rozwoju i Technologii", "PARP; UOKiK; wsparcie przedsiębiorstw"),
    ("VII", "Gospodarka morska", "Minister Infrastruktury", "urzędy morskie; SAR; porty"),
    ("VIII", "Gospodarka wodna", "Minister Infrastruktury", "Wody Polskie; IMGW-PIB; RZGW"),
    ("IX", "Zdrowie", "Minister Zdrowia", "NFZ; GIS; szpitale; Lotnicze Pogotowie Ratunkowe"),
    ("X", "Informatyzacja", "Minister Cyfryzacji", "CSIRT GOV; COI; NASK"),
    ("XI", "Kultura i ochrona dziedzictwa narodowego", "Minister Kultury i Dziedzictwa Narodowego", "NID; archiwa państwowe; instytucje kultury"),
    ("XII", "Kultura fizyczna", "Minister Sportu i Turystyki", "COS; obiekty sportowe jako miejsca wsparcia"),
    ("XIII", "Łączność", "Minister Cyfryzacji", "UKE; operatorzy telekomunikacyjni; łączność kryzysowa"),
    ("XIV", "Obrona narodowa", "Minister Obrony Narodowej", "SZ RP; WOT; Żandarmeria Wojskowa"),
    ("XV", "Oświata i wychowanie", "Minister Edukacji Narodowej", "kuratoria; szkoły; placówki oświatowe"),
    ("XVI", "Praca", "Minister Rodziny, Pracy i Polityki Społecznej", "PIP; urzędy pracy"),
    ("XVII", "Rolnictwo", "Minister Rolnictwa i Rozwoju Wsi", "GIW; PIORiN; KOWR; ARiMR"),
    ("XVIII", "Sprawiedliwość", "Minister Sprawiedliwości", "prokuratura; sądy; Służba Więzienna"),
    ("XIX", "Sprawy wewnętrzne", "Minister Spraw Wewnętrznych i Administracji", "Policja; PSP; Straż Graniczna; SOP"),
    ("XX", "Sprawy zagraniczne", "Minister Spraw Zagranicznych", "placówki dyplomatyczne; centrum operacyjne MSZ"),
    ("XXI", "Środowisko", "Minister Klimatu i Środowiska", "GIOŚ; parki narodowe; inspekcja ochrony środowiska"),
    ("XXII", "Transport", "Minister Infrastruktury", "GDDKiA; PKP PLK; UTK; GITD"),
    ("XXIII", "Zabezpieczenie społeczne", "Minister Rodziny, Pracy i Polityki Społecznej", "ZUS; OPS; centra usług społecznych"),
    ("XXIV", "Klimat", "Minister Klimatu i Środowiska", "IMGW-PIB; instytuty klimatu; system adaptacji"),
    ("XXV", "Aktywa państwowe", "Minister Aktywów Państwowych", "spółki strategiczne; rezerwy infrastrukturalne"),
]

TASK_MODULES = [
    (1, "Monitorowanie i ostrzeganie", "Monitoring zagrożenia, prognozy, komunikaty ostrzegawcze, obieg meldunków i dyżury."),
    (2, "Zabezpieczenie potrzeb ludności", "Ewakuacja, schronienie, woda, żywność, opieka socjalna i logistyka pierwszej potrzeby."),
    (3, "Odtworzenie infrastruktury", "Ocena szkód, priorytety napraw, przywracanie dróg, mostów, energii, wody i usług publicznych."),
    (4, "Zapewnienie łączności", "Łączność kryzysowa, kanały zapasowe, koordynacja operatorów oraz ścieżki satelitarne i radiowe."),
    (5, "Wsparcie sił zbrojnych", "Wniosek o użycie SZ RP/WOT, mosty tymczasowe, transport, rozpoznanie i logistyka."),
    (6, "Pomoc humanitarna i międzynarodowa", "Mechanizm UE, HNS, pomoc zagraniczna, darowizny, magazyny i dystrybucja."),
    (7, "Ochrona informacji", "Bezpieczeństwo informacji, przeciwdziałanie dezinformacji, ochrona danych i jednolity przekaz."),
]

PROFILES = {
    "Z01": {"R": (["IX"], ["I", "XIX", "XIII", "XV", "XX", "XVII"], [1, 2, 4, 7]), "O": (["IX", "XXIII"], ["III", "V", "XV", "XVI"], [2, 3, 7])},
    "Z02": {"R": (["VIII", "XIX"], ["IV", "IX", "XIII", "XIV", "XXI", "XXII", "XXIII", "XXIV"], [1, 2, 4, 5, 7]), "O": (["VIII", "II", "XXII"], ["IV", "IX", "XIII", "XIX", "XXI", "XXIII", "XXIV"], [2, 3, 4, 6, 7])},
    "Z03": {"R": (["X"], ["XIII", "XIX", "XIV", "V", "XXV"], [1, 4, 7]), "O": (["X"], ["XIII", "VI", "V", "XXV"], [3, 4, 7])},
    "Z04": {"R": (["XIX", "XIV", "X"], ["XX", "XIII", "XVIII", "I"], [1, 4, 5, 7]), "O": (["I", "X"], ["XX", "XVIII", "XIII"], [3, 7])},
    "Z05": {"R": (["XXIV", "VIII"], ["XVII", "IX", "IV", "XXI"], [1, 2, 7]), "O": (["XVII", "VIII"], ["III", "V", "XXI", "XXIV"], [3, 6, 7])},
    "Z06": {"R": (["XVII"], ["IX", "XIX", "XX", "V"], [1, 2, 7]), "O": (["XVII"], ["V", "VI", "XX"], [3, 6, 7])},
    "Z07": {"R": (["IV"], ["XIX", "XIII", "XXV", "IX", "XXII"], [1, 2, 3, 4, 7]), "O": (["IV", "XXV"], ["VI", "XXII", "XIII"], [3, 4, 7])},
    "Z08": {"R": (["XIX"], ["XXIV", "IV", "XIII", "XXII", "VIII"], [1, 2, 4, 7]), "O": (["II", "XXII"], ["IV", "XIII", "XXI"], [3, 4, 7])},
    "Z09": {"R": (["VI", "XXV"], ["IV", "XXII", "XIX", "XIV"], [1, 2, 5, 7]), "O": (["VI", "XXV"], ["IV", "XXII", "V"], [3, 6, 7])},
    "Z10": {"R": (["XIX", "XXI"], ["XIV", "IX", "XXIV", "XXII"], [1, 2, 4, 5, 7]), "O": (["XXI"], ["II", "IX", "XXIII"], [3, 6, 7])},
    "Z11": {"R": (["XVII"], ["XXI", "IX", "VI"], [1, 2, 7]), "O": (["XVII"], ["V", "VI", "XXI"], [3, 6, 7])},
    "Z12": {"R": (["XIII"], ["X", "XIX", "XIV", "IV"], [1, 4, 7]), "O": (["XIII"], ["X", "VI", "XXV"], [3, 4, 7])},
    "Z13": {"R": (["XIX", "XXI"], ["IX", "XVII", "XXII", "XIV"], [1, 2, 4, 5, 7]), "O": (["XXI", "IX"], ["II", "XVII", "XXII"], [3, 6, 7])},
    "Z14": {"R": (["IV"], ["XIX", "XXV", "IX", "XXII"], [1, 2, 3, 4, 7]), "O": (["IV", "XXV"], ["II", "XXII"], [3, 4, 7])},
    "Z15": {"R": (["VII"], ["XIX", "XIV", "IX", "XX", "XXI"], [1, 2, 4, 5, 6, 7]), "O": (["VII", "XXI"], ["XX", "IX", "VI"], [3, 6, 7])},
    "Z16": {"R": (["XIX"], ["XIV", "IX", "X", "XIII", "XX", "XVIII"], [1, 2, 4, 5, 7]), "O": (["XVIII", "XIX"], ["IX", "XXIII", "X"], [3, 7])},
    "Z17": {"R": (["XXI", "XIX"], ["IX", "XIV", "XX", "XXII"], [1, 2, 4, 5, 6, 7]), "O": (["XXI", "IX"], ["II", "XXIII", "XX"], [3, 6, 7])},
    "Z18": {"R": (["XIX"], ["XVIII", "IX", "XIII", "I"], [1, 2, 4, 7]), "O": (["XVIII", "XIX"], ["XXIII", "I"], [3, 7])},
    "Z19": {"R": (["XIX", "XXIV"], ["IV", "IX", "XXII", "XXIII", "XIII"], [1, 2, 4, 7]), "O": (["II", "XXII"], ["IV", "IX", "XXIII"], [3, 4, 7])},
    "Z20": {"R": (["X", "I"], ["XIX", "XIII", "XX", "XIV"], [1, 4, 7]), "O": (["X", "I"], ["XX", "XVIII", "XIII"], [3, 7])},
}


def write_csv(name: str, rows: list[dict], fieldnames: list[str]) -> None:
    with (DATA / name).open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(rows)


def write_jsonl(name: str, rows: list[dict]) -> None:
    with (DATA / name).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


hazard_rows = []
for code, name, category, probability_label, impact_label in HAZARDS:
    probability, impact = PROB[probability_label], IMPACT[impact_label]
    score = probability * impact
    hazard_rows.append({
        "hazard_code": code, "hazard_name": name, "category": category,
        "probability": probability, "probability_label": probability_label,
        "impact": impact, "impact_label": impact_label, "risk_score": score,
        "risk_level": risk_level(score), "color": risk_color(score),
    })
write_csv("dim_hazard.csv", hazard_rows, list(hazard_rows[0].keys()))

admin_rows = [{"admin_division": n, "admin_name": name, "ministry": ministry, "subordinate_institutions": inst} for n, name, ministry, inst in DIVISIONS]
write_csv("dim_admin_division.csv", admin_rows, list(admin_rows[0].keys()))
module_rows = [{"task_module_id": i, "task_module_name": n, "description": d} for i, n, d in TASK_MODULES]
write_csv("dim_task_module.csv", module_rows, list(module_rows[0].keys()))

safety = []
for hz in hazard_rows:
    code = hz["hazard_code"]
    for phase in ["R", "O"]:
        lead, coop, mods_all = PROFILES[code][phase]
        for div, *_ in DIVISIONS:
            if div in lead:
                role, mods = "wiodący", mods_all
            elif div in coop:
                role = "współpracujący"
                mods = [m for m in mods_all if not (m == 5 and div not in ["XIV", "XIX", "XXII", "VII"])]
            else:
                role = "wspierający"
                mods = [1] if div in ["I", "III", "V", "XVIII", "XX", "XXV"] else []
            if role == "wiodący":
                criticality = "wysoka" if hz["risk_score"] >= 8 else "średnia"
            elif role == "współpracujący":
                criticality = "średnia" if hz["risk_score"] >= 8 else "niska"
            else:
                criticality = "niska"
            safety.append({
                "hazard_code": code, "admin_division": div, "phase": phase,
                "task_modules": ";".join(map(str, mods)), "role": role, "criticality": criticality,
            })
write_csv("fact_safety_grid.csv", safety, list(safety[0].keys()))

SPO = [
    ("SPO-1", "Organizacja posiedzenia Rządowego Zespołu Zarządzania Kryzysowego", "Z02;Z04;Z07;Z12;Z20"),
    ("SPO-2", "Uruchomienie dodatkowych środków finansowych", "Z01;Z02;Z05;Z07;Z10;Z17;Z19"),
    ("SPO-3", "Zasady informowania ludności o zagrożeniach – organizacja procesu komunikacji społecznej", "Z01;Z02;Z03;Z04;Z07;Z12;Z16;Z20"),
    ("SPO-4", "Tymczasowe przywrócenie kontroli granicznej na granicach RP", "Z01;Z04;Z09;Z16"),
    ("SPO-5", "Wprowadzenie stanu klęski żywiołowej", "Z01;Z02;Z05;Z07;Z10;Z17;Z19"),
    ("SPO-6", "Wprowadzenie stanu wyjątkowego", "Z04;Z16;Z18;Z20"),
    ("SPO-7", "Wprowadzenie stanu wojennego", "Z04;Z16"),
    ("SPO-8", "Postępowanie w sytuacji uprowadzenia terrorystycznego obywatela polskiego poza RP", "Z16"),
    ("SPO-9", "Działania w przypadku masowego napływu cudzoziemców", "Z04;Z16"),
    ("SPO-10", "Współpraca z właścicielami infrastruktury krytycznej w zakresie ochrony", "Z03;Z07;Z09;Z12;Z14;Z17"),
    ("SPO-11", "Organizacja ewakuacji obywateli polskich spoza granic kraju", "Z15;Z16;Z17"),
    ("SPO-12", "Obieg informacji między strukturami zarządzania kryzysowego", "Z01;Z02;Z03;Z04;Z07;Z12;Z20"),
    ("SPO-13", "Ostrzeganie wojsk oraz ludności cywilnej o zagrożeniu z powietrza", "Z04;Z16"),
    ("SPO-14", "Przekraczanie granic RP przez wojska sojusznicze", "Z04;Z16"),
    ("SPO-15", "Organizacja medycznego mostu powietrznego w zdarzeniu masowym", "Z01;Z02;Z15;Z16;Z17"),
    ("SPO-16", "Zwołanie i obsługa Zespołu do spraw Incydentów Krytycznych", "Z03;Z04;Z12;Z20"),
]
spo_rows = [{"spo_code": c, "spo_name": n, "related_hazards": h} for c, n, h in SPO]
write_csv("dim_spo.csv", spo_rows, list(spo_rows[0].keys()))

templates = [
    ("Przyjąć meldunek i potwierdzić przesłanki uruchomienia procedury", "I", 2, "meldunek_sytuacyjny.pdf"),
    ("Wyznaczyć resort wiodący i listę uczestników uzgodnień", "I", 4, "lista_uczestnikow.xlsx"),
    ("Przygotować projekt decyzji, komunikatu lub notatki dla RZZK", "XIX", 6, "projekt_decyzji.docx"),
    ("Zarejestrować status wykonania i przekazać informację do RCB", "I", 8, "potwierdzenie_wykonania.json"),
]
check = []
for code, _, _ in SPO:
    for step, (desc, div, sla, doc) in enumerate(templates, 1):
        owner = "XX" if code in ["SPO-8", "SPO-11"] and step < 3 else ("XIV" if code in ["SPO-7", "SPO-13", "SPO-14"] and step < 3 else div)
        check.append({"spo_code": code, "step_number": step, "step_description": desc, "responsible_admin_division": owner, "sla_hours": sla + (step - 1) * 2, "required_document": doc})
write_csv("fact_spo_checklist.csv", check, list(check[0].keys()))

contacts = []
for n, name, _, _ in DIVISIONS:
    contacts.append({
        "admin_division": n, "role": "dyżurny krajowy (dane syntetyczne)",
        "unit": f"Centrum operacyjne - {name}", "duty_phone": f"+48 22 100 {len(n)}{ord(n[0]) % 10}{random.randint(100, 999)}",
        "email": f"dyzurny.{n.lower()}@demo-ol.example", "deputy": f"zastępca dyżurnego {n} (syntetyczny)",
    })
write_csv("dim_contact_point.csv", contacts, list(contacts[0].keys()))

base = datetime(2026, 9, 15, 8, 0, tzinfo=TZ)
z02 = [r for r in safety if r["hazard_code"] == "Z02" and r["task_modules"]]
statuses = ["gotowe", "w toku", "gotowe", "zablokowane", "nie rozpoczęto"]
blockers = {"IV": "oczekiwanie na dostęp do zalanych stacji GPZ", "XIII": "brak zasilania dla dwóch węzłów telekomunikacyjnych", "XXII": "uszkodzony most ogranicza transport ciężki"}
readiness = []
for idx, row in enumerate(z02):
    for mod in row["task_modules"].split(";"):
        status = statuses[(idx + int(mod)) % len(statuses)]
        if row["admin_division"] in blockers and int(mod) in [3, 4]:
            status = "zablokowane"
        readiness.append({
            "timestamp": (base + timedelta(hours=idx % 72)).isoformat(), "event_id": "POWODZ_WRZESIEN_2026",
            "admin_division": row["admin_division"], "task_module_id": int(mod), "status": status,
            "comment": blockers.get(row["admin_division"], "deklaracja syntetyczna: zasoby zweryfikowane"),
            "forces_and_assets": f"zespoły={1 + (idx % 5)}; pojazdy={2 + (idx % 7)}; dyżury=24/7",
        })
write_jsonl("fact_readiness_declaration.jsonl", readiness)

activations = []
module_lead = {1: "VIII", 2: "XIX", 3: "XXII", 4: "XIII", 5: "XIV", 6: "XXIII", 7: "X"}
for day in range(-1, 11):
    for mod in range(1, 8):
        if day == -1 and mod not in [1, 7]:
            continue
        activations.append({
            "timestamp": (base + timedelta(days=day, hours=mod)).isoformat(), "event_id": "POWODZ_WRZESIEN_2026",
            "day_offset": day, "hazard_code": "Z02", "phase": "R" if day <= 3 else "O",
            "task_module_id": mod, "leading_admin_division": module_lead[mod],
            "activation_status": "aktywny" if day <= 7 else "wygaszanie",
            "trigger": "POWÓDŹ WRZESIEŃ: przekroczenie progów operacyjnych",
        })
write_jsonl("fact_task_activation.jsonl", activations)

inter = [
    (2, 1, "dystrybucja pomocy wymaga rozpoznania sytuacji"),
    (4, 1, "łączność zapasowa wymaga monitoringu awarii"),
    (3, 2, "odbudowa po ewakuacji i zabezpieczeniu ludności"),
    (3, 4, "odbudowa wymaga łączności koordynacyjnej"),
    (5, 1, "wniosek o SZ RP wymaga potwierdzonego obrazu sytuacji"),
    (6, 2, "pomoc humanitarna po identyfikacji potrzeb"),
    (7, 1, "ochrona informacji musi bazować na spójnym obrazie sytuacji"),
]
inter_rows = [{"task_module_id": a, "depends_on_task_module_id": b, "dependency_reason": c} for a, b, c in inter]
write_csv("fact_interdependency.csv", inter_rows, list(inter_rows[0].keys()))

counts = {}
for path in DATA.iterdir():
    if path.is_file() and path.suffix in [".csv", ".jsonl"]:
        with path.open(encoding="utf-8") as f:
            counts[path.name] = sum(1 for _ in f) - (1 if path.suffix == ".csv" else 0)
(DERIVED / "dataset_counts.json").write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(counts, ensure_ascii=False, indent=2))
