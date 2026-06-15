import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# KONFIGURACJA
# ============================================================

st.set_page_config(
    page_title="TRAP20 — System Punktacji",
    page_icon="🎯",
    layout="wide",
)

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
ARCHIWUM_DIR = APP_DIR / "archiwum"
EVENTS_FILE = APP_DIR / "events.json"
DATA_DIR.mkdir(exist_ok=True)
ARCHIWUM_DIR.mkdir(exist_ok=True)

MAX_RZUTKOW = 25

KOLUMNA_KONKURENCJA = "Konkurencja"
KOLUMNA_KOLEJNOSC = "Kolejność w zmianie"
KOLUMNA_LIMIT = "Limit rzutków"

WYMAGANE_KOLUMNY = [
    "Nazwisko",
    "Zmiana",
    KOLUMNA_KONKURENCJA,
    "Status",
    "Suma trafień",
    "Ile za pierwszym",
]

KOLUMNY_STRZALOW = [f"Strzał_{i}" for i in range(1, MAX_RZUTKOW + 1)]

ARKUSZ_WYNIKI = "Wyniki Szczegółowe"
ARKUSZ_REZULTATY_PREFIX = "Ranking"
ARKUSZ_REZULTATY = "Rezultaty"
ARKUSZ_REZULTATY_PK = "Rezultaty PK"

KONKURENCJE_DOMYSLNE = ["TRAP20", "TRAP10", "PK", "STANDARD"]


# ============================================================
# STYL
# ============================================================

st.markdown(
    """
<style>
    .main-title {
        font-size: 30px;
        font-weight: 900;
        margin-bottom: 2px;
        line-height: 1.12;
    }

    .subtitle {
        color: #64748b;
        margin-bottom: 12px;
        font-size: 14px;
    }

    .block-container {
        padding-top: 1.0rem;
        padding-bottom: 0.8rem;
    }

    .shot-box {
        display: inline-block;
        width: 30px;
        height: 30px;
        line-height: 28px;
        text-align: center;
        margin: 1px;
        border-radius: 7px;
        font-weight: 900;
        color: white;
        border: 1px solid #cbd5e1;
        font-size: 14px;
        box-sizing: border-box;
    }

    .shot-blank {
        background-color: #e5e7eb;
        color: #64748b;
    }

    .shot-t1 {
        background-color: #1e40af;
    }

    .shot-t2 {
        background-color: #15803d;
    }

    .shot-miss {
        background-color: #b91c1c;
    }

    .current-target {
        outline: 3px solid #facc15;
        outline-offset: 1px;
    }

    .player-row {
        display: grid;
        grid-template-columns: 45px 180px minmax(300px, 1fr) 84px;
        align-items: center;
        column-gap: 8px;
        padding: 4px 0;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
    }

    .player-stand {
        font-weight: 900;
        font-size: 14px;
        white-space: nowrap;
    }

    .player-name {
        font-weight: 900;
        font-size: 14px;
        line-height: 1.2;
        white-space: normal;
        word-wrap: break-word;
    }

    .player-type {
        color: #94a3b8;
        font-size: 12px;
        margin-top: 1px;
    }

    .player-shots {
        line-height: 32px;
    }

    .player-sum {
        font-weight: 900;
        font-size: 15px;
        white-space: nowrap;
        text-align: right;
    }

    .current-player {
        background: #111827;
        border: 1px solid #334155;
        color: white;
        padding: 8px 12px;
        border-radius: 10px;
        margin: 8px 0 10px 0;
    }

    .current-player h3 {
        margin: 0;
        font-size: 15px;
        color: white;
        display: inline;
    }

    .current-player .current-line {
        font-size: 14px;
        font-weight: 800;
        color: white;
        display: inline;
        margin-left: 10px;
    }

    .file-info-footer {
        margin-top: 18px;
        padding: 10px 12px;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 10px;
        color: #64748b;
        font-size: 13px;
        background: rgba(15, 23, 42, 0.25);
    }

    .file-info-footer code {
        color: #22c55e;
        background: rgba(34, 197, 94, 0.08);
        padding: 2px 6px;
        border-radius: 6px;
    }

    .danger-zone {
        margin-top: 28px;
        padding-top: 16px;
        border-top: 1px solid rgba(239, 68, 68, 0.35);
    }

    @media (max-width: 950px) {
        .main-title {
            font-size: 22px;
        }

        .subtitle {
            display: none;
        }

        .block-container {
            padding-left: 0.65rem;
            padding-right: 0.65rem;
            padding-top: 0.55rem;
        }

        h2, h3 {
            margin-top: 0.4rem !important;
            margin-bottom: 0.35rem !important;
        }

        .shot-box {
            width: 25px;
            height: 25px;
            line-height: 23px;
            margin: 1px;
            border-radius: 6px;
            font-size: 12px;
        }

        .player-row {
            grid-template-columns: 38px 135px minmax(235px, 1fr) 62px;
            column-gap: 5px;
            padding: 3px 0;
        }

        .player-stand {
            font-size: 12px;
        }

        .player-name {
            font-size: 12px;
            white-space: normal;
        }

        .player-type {
            font-size: 10px;
        }

        .player-shots {
            line-height: 27px;
        }

        .player-sum {
            font-size: 12px;
        }

        .current-player {
            padding: 6px 8px;
            margin: 7px 0 7px 0;
        }

        .current-player h3 {
            font-size: 13px;
        }

        .current-player .current-line {
            font-size: 12px;
            display: block;
            margin-left: 0;
            margin-top: 3px;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0.4rem;
        }

        .stButton > button {
            min-height: 2.25rem;
            padding-top: 0.22rem;
            padding-bottom: 0.22rem;
            font-size: 13px;
        }
    }

    @media (max-width: 620px) {
        .player-row {
            grid-template-columns: 32px 1fr 58px;
            row-gap: 2px;
        }

        .player-stand {
            font-size: 12px;
        }

        .player-name {
            font-size: 13px;
            white-space: normal;
            line-height: 1.2;
        }

        .player-shots {
            grid-column: 1 / 4;
            line-height: 28px;
            padding-top: 2px;
        }

        .shot-box {
            width: 24px;
            height: 24px;
            line-height: 22px;
            font-size: 11px;
        }

        .player-sum {
            font-size: 12px;
        }

        div[data-baseweb="select"] {
            z-index: 999;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FUNKCJE PLIKÓW I DANYCH
# ============================================================

def slugify_event_id(value: str) -> str:
    txt = str(value).strip().lower()
    txt = re.sub(r"[^a-z0-9_-]+", "_", txt)
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt or "default"


def wczytaj_events() -> dict:
    if not EVENTS_FILE.exists():
        return {}

    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}




def zapisz_events(data: dict) -> None:
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def haslo_admina(events: dict) -> str:
    return str(events.get("_admin", {}).get("password", "TRAPADMIN2026"))


def eventy_uzytkowe(events: dict) -> dict:
    return {
        k: v for k, v in events.items()
        if not str(k).startswith("_") and isinstance(v, dict)
    }


def policz_pliki_eventu(event_id: str) -> tuple[int, int]:
    event_id = slugify_event_id(event_id)
    active_dir = DATA_DIR / event_id
    archive_dir = ARCHIWUM_DIR / event_id

    active = len(list(active_dir.glob("*.xlsx"))) if active_dir.exists() else 0
    archive = len(list(archive_dir.glob("*.xlsx"))) if archive_dir.exists() else 0

    return active, archive


def pokaz_panel_administratora() -> None:
    st.markdown('<div class="main-title">⚙️ TRAP20 — Panel administratora</div>', unsafe_allow_html=True)
    st.caption("Zarządzanie kodami zawodów, konfiguracją events.json oraz archiwum.")

    events = wczytaj_events()

    if "_admin" not in events:
        events["_admin"] = {"password": "TRAPADMIN2026"}
        zapisz_events(events)

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Zawody",
        "➕ Dodaj / edytuj kod",
        "📦 Pliki i archiwum",
        "🧾 events.json",
    ])

    with tab1:
        st.subheader("Aktywne kody zawodów")

        rows = []
        for kod, cfg in eventy_uzytkowe(events).items():
            event_id = slugify_event_id(cfg.get("event_id", kod))
            aktywne_pliki, archiwum_pliki = policz_pliki_eventu(event_id)
            aktywny, komunikat = event_aktywny(cfg)

            rows.append({
                "Kod": kod,
                "Włączony": bool(cfg.get("enabled", False)),
                "Aktywny teraz": aktywny,
                "Komunikat": komunikat,
                "Nazwa": cfg.get("nazwa", ""),
                "event_id": event_id,
                "Aktywny od": cfg.get("aktywny_od", ""),
                "Aktywny do": cfg.get("aktywny_do", ""),
                "PK wymaga Standard": bool(cfg.get("pk_wymaga_standard", False)),
                "Pliki aktywne": aktywne_pliki,
                "Pliki archiwum": archiwum_pliki,
            })

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Brak skonfigurowanych zawodów w events.json.")

        st.markdown("#### Szybkie akcje")

        event_keys = list(eventy_uzytkowe(events).keys())

        if event_keys:
            wybrany_kod = st.selectbox("Wybierz kod:", event_keys, key="admin_quick_event")
            cfg = events[wybrany_kod]

            c1, c2, c3 = st.columns(3)

            with c1:
                if st.button("Włącz / wyłącz kod", use_container_width=True):
                    events[wybrany_kod]["enabled"] = not bool(cfg.get("enabled", False))
                    zapisz_events(events)
                    st.success("Zmieniono status kodu.")
                    st.rerun()

            with c2:
                if st.button("Ustaw jako aktywne zawody", use_container_width=True):
                    ustaw_event(
                        cfg.get("event_id", wybrany_kod),
                        cfg.get("nazwa", wybrany_kod),
                        cfg,
                    )
                    st.session_state.zawody_zakonczone = False
                    st.session_state.admin_mode = False
                    st.success("Ustawiono zawody jako aktywne.")
                    st.rerun()

            with c3:
                if st.button("Odśwież panel", use_container_width=True):
                    st.rerun()

    with tab2:
        st.subheader("Dodaj albo edytuj kod zawodów")

        event_keys = ["<NOWY KOD>"] + list(eventy_uzytkowe(events).keys())
        wybor = st.selectbox("Tryb:", event_keys, key="admin_edit_select")

        if wybor == "<NOWY KOD>":
            cfg0 = {
                "enabled": True,
                "event_id": "",
                "nazwa": "",
                "google_sheet": "",
                "aktywny_od": "",
                "aktywny_do": "",
                "pk_wymaga_standard": False,
                "konkurencje": {
                    "TRAP10": 10,
                    "TRAP20": 20,
                    "PK": 20,
                    "STANDARD": 20
                },
            }
            kod0 = ""
        else:
            cfg0 = events.get(wybor, {})
            kod0 = wybor

        with st.form("admin_event_form"):
            kod = st.text_input("Kod zawodów:", value=kod0, placeholder="np. snajper2026").strip().lower()
            nazwa = st.text_input("Nazwa zawodów:", value=str(cfg0.get("nazwa", "")))
            event_id = st.text_input(
                "event_id / katalog zawodów:",
                value=str(cfg0.get("event_id", "")),
                placeholder="np. snajper_lublin_20260620",
            )
            google_sheet = st.text_input("Link Google Sheets:", value=str(cfg0.get("google_sheet", "")))
            aktywny_od = st.text_input("Aktywny od:", value=str(cfg0.get("aktywny_od", "")), placeholder="2026-06-20 07:00")
            aktywny_do = st.text_input("Aktywny do:", value=str(cfg0.get("aktywny_do", "")), placeholder="2026-06-20 20:00")
            enabled = st.checkbox("Kod włączony", value=bool(cfg0.get("enabled", True)))
            pk_wymaga_standard = st.checkbox(
                "PK wymaga wcześniejszego startu Standard",
                value=bool(cfg0.get("pk_wymaga_standard", False)),
            )

            limity_konkurencji_txt = st.text_area(
                "Limity rzutków dla konkurencji / JSON:",
                value=json.dumps(
                    cfg0.get(
                        "konkurencje",
                        {
                            "TRAP10": 10,
                            "TRAP20": 20,
                            "PK": 20,
                            "STANDARD": 20
                        },
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                height=150,
                help='Przykład: {"TRAP10": 10, "TRAP20": 20, "PK": 20}. Limit blokuje ręczną zmianę liczby rzutków przez sędziego.',
            )

            submitted = st.form_submit_button("💾 Zapisz kod zawodów", type="primary")

        if submitted:
            if not kod:
                st.error("Kod zawodów nie może być pusty.")
            else:
                try:
                    limity_konkurencji = json.loads(limity_konkurencji_txt.strip() or "{}")

                    if not isinstance(limity_konkurencji, dict):
                        raise ValueError("Limity konkurencji muszą być obiektem JSON.")

                    limity_konkurencji = {
                        normalizuj_konkurencje(k): int(v)
                        for k, v in limity_konkurencji.items()
                        if str(k).strip()
                    }

                    for k, v in limity_konkurencji.items():
                        if not (1 <= int(v) <= MAX_RZUTKOW):
                            raise ValueError(f"Limit dla {k} musi być od 1 do {MAX_RZUTKOW}.")

                    if not event_id:
                        event_id = kod

                    events[kod] = {
                        "enabled": bool(enabled),
                        "event_id": slugify_event_id(event_id),
                        "nazwa": nazwa.strip() or kod,
                        "google_sheet": google_sheet.strip(),
                        "aktywny_od": aktywny_od.strip(),
                        "aktywny_do": aktywny_do.strip(),
                        "pk_wymaga_standard": bool(pk_wymaga_standard),
                        "konkurencje": limity_konkurencji,
                    }

                    zapisz_events(events)
                    st.success(f"Zapisano kod: {kod}")
                    st.rerun()

                except Exception as e:
                    st.error(f"Nie zapisano kodu. Błąd w limitach konkurencji: {e}")

        st.markdown("#### Zmiana hasła administratora")

        with st.form("admin_password_form"):
            nowe_haslo = st.text_input("Nowe hasło administratora:", type="password")
            zapisz_haslo = st.form_submit_button("Zmień hasło administratora")

        if zapisz_haslo:
            if len(nowe_haslo.strip()) < 6:
                st.error("Hasło powinno mieć minimum 6 znaków.")
            else:
                events["_admin"] = {"password": nowe_haslo.strip()}
                zapisz_events(events)
                st.success("Hasło administratora zostało zmienione.")

    with tab3:
        st.subheader("Pliki aktywne i archiwum")

        wszystkie_pliki = []

        for base_name, base_dir in [("AKTYWNE", DATA_DIR), ("ARCHIWUM", ARCHIWUM_DIR)]:
            if not base_dir.exists():
                continue

            for file in sorted(base_dir.glob("*/*.xlsx"), reverse=True):
                wszystkie_pliki.append({
                    "Typ": base_name,
                    "event_id": file.parent.name,
                    "Plik": file.name,
                    "Ścieżka": str(file),
                    "Rozmiar KB": round(file.stat().st_size / 1024, 1),
                    "Modyfikacja": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })

        if wszystkie_pliki:
            st.dataframe(pd.DataFrame(wszystkie_pliki), use_container_width=True, hide_index=True)

            st.markdown("#### Pobieranie plików")

            opis_do_sciezki = {
                f"{r['Typ']} | {r['event_id']} | {r['Plik']}": r["Ścieżka"]
                for r in wszystkie_pliki
            }

            wybor_pliku = st.selectbox("Wybierz plik do pobrania:", list(opis_do_sciezki.keys()))

            file_path = Path(opis_do_sciezki[wybor_pliku])
            if file_path.exists():
                st.download_button(
                    "⬇️ Pobierz wybrany Excel",
                    data=file_path.read_bytes(),
                    file_name=file_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        else:
            st.info("Brak plików aktywnych i archiwalnych.")

    with tab4:
        st.subheader("Edycja surowego events.json")

        raw = json.dumps(events, ensure_ascii=False, indent=2)

        edited = st.text_area(
            "Zawartość pliku events.json:",
            value=raw,
            height=420,
            key="admin_events_raw",
        )

        if st.button("💾 Zapisz surowy JSON", type="primary"):
            try:
                parsed = json.loads(edited)
                if not isinstance(parsed, dict):
                    st.error("Główny obiekt JSON musi być słownikiem.")
                else:
                    zapisz_events(parsed)
                    st.success("Zapisano events.json.")
                    st.rerun()
            except Exception as e:
                st.error(f"Nieprawidłowy JSON: {e}")


def event_aktywny(event_cfg: dict) -> tuple[bool, str]:
    if not event_cfg.get("enabled", False):
        return False, "Kod zawodów jest wyłączony."

    aktywny_od = str(event_cfg.get("aktywny_od", "")).strip()
    aktywny_do = str(event_cfg.get("aktywny_do", "")).strip()

    if not aktywny_od or not aktywny_do:
        return True, ""

    try:
        teraz = datetime.now()
        od = datetime.strptime(aktywny_od, "%Y-%m-%d %H:%M")
        do = datetime.strptime(aktywny_do, "%Y-%m-%d %H:%M")
    except Exception:
        return False, "Błędny format daty w events.json. Użyj: RRRR-MM-DD HH:MM."

    if teraz < od:
        return False, f"Kod będzie aktywny od {aktywny_od}."

    if teraz > do:
        return False, f"Kod wygasł {aktywny_do}."

    return True, ""


def ustaw_event(event_id: str, nazwa: str = "", cfg: dict | None = None) -> None:
    event_id = slugify_event_id(event_id)
    st.session_state.event_id = event_id
    st.session_state.event_name = nazwa or event_id
    st.session_state.event_cfg = cfg or {}


def aktywny_event_id() -> str:
    return slugify_event_id(st.session_state.get("event_id", "default"))


def aktywny_event_dir() -> Path:
    path = DATA_DIR / aktywny_event_id()
    path.mkdir(parents=True, exist_ok=True)
    return path


def aktywny_archiwum_dir() -> Path:
    path = ARCHIWUM_DIR / aktywny_event_id()
    path.mkdir(parents=True, exist_ok=True)
    return path


def lista_plikow_zawodow() -> list[Path]:
    return sorted(aktywny_event_dir().glob("trap20_zawody_*.xlsx"), reverse=True)


def nazwa_nowego_pliku() -> Path:
    znacznik = datetime.now().strftime("%Y%m%d_%H%M%S")
    return aktywny_event_dir() / f"trap20_zawody_{aktywny_event_id()}_{znacznik}.xlsx"


def bezpieczna_nazwa_archiwum(path: Path) -> Path:
    znacznik = datetime.now().strftime("%Y%m%d_%H%M%S")
    return aktywny_archiwum_dir() / f"{path.stem}_ARCHIWUM_{znacznik}{path.suffix}"


def google_link_do_csv_url(link: str) -> str:
    link = str(link).strip()

    if "export?format=csv" in link or "output=csv" in link:
        return link

    match_id = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", link)
    if not match_id:
        return link

    sheet_id = match_id.group(1)
    match_gid = re.search(r"gid=(\d+)", link)
    gid = match_gid.group(1) if match_gid else "0"

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def odczytaj_limit_z_konkurencji(konkurencja: str, domyslny: int = 20) -> int:
    txt = str(konkurencja).upper()
    match = re.search(r"(\d+)", txt)
    if match:
        val = int(match.group(1))
        if val in [10, 15, 20, 25]:
            return val
    return domyslny


def limit_dla_konkurencji(konkurencja: str, domyslny: int = 20) -> int:
    """
    Limit rzutków wynika z konfiguracji eventu, a nie z dowolnego wyboru sędziego.
    Najpierw czytamy st.session_state.event_cfg["konkurencje"], np. {"TRAP10": 10, "PK": 20}.
    Jeżeli nie ma konfiguracji, próbujemy wyciągnąć limit z nazwy konkurencji, np. TRAP10 -> 10.
    """
    konkurencja_norm = normalizuj_konkurencje(konkurencja)
    cfg = st.session_state.get("event_cfg", {}) or {}
    limity = cfg.get("konkurencje", {}) if isinstance(cfg, dict) else {}

    if isinstance(limity, dict):
        for key, value in limity.items():
            if normalizuj_konkurencje(key) == konkurencja_norm:
                try:
                    limit = int(value)
                    if 1 <= limit <= MAX_RZUTKOW:
                        return limit
                except Exception:
                    pass

    return odczytaj_limit_z_konkurencji(konkurencja_norm, domyslny)


def normalizuj_konkurencje(wartosc: str) -> str:
    txt = str(wartosc).strip().upper()
    if txt in ["", "NAN", "NONE"]:
        return "TRAP20"
    if txt == "STANDARD":
        return "STANDARD"
    return txt


def normalizuj_naglowki(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    mapa = {}

    for col in df.columns:
        c = str(col).strip().lower()

        if c in ["nazwisko", "nazwisko i imię", "nazwisko i imie", "zawodnik"]:
            mapa[col] = "Nazwisko"
        elif "zmiana" in c:
            mapa[col] = "Zmiana"
        elif c in ["konkurencja", "konkurencje", "konkurencja startu", "kategoria"]:
            mapa[col] = KOLUMNA_KONKURENCJA
        elif c == "typ" or "typ startu" in c:
            # Zgodność ze starymi plikami: Typ staje się Konkurencją.
            mapa[col] = KOLUMNA_KONKURENCJA
        elif "status" in c:
            mapa[col] = "Status"
        elif "suma" in c and "traf" in c:
            mapa[col] = "Suma trafień"
        elif "pierwsz" in c:
            mapa[col] = "Ile za pierwszym"
        elif "limit" in c and ("rzut" in c or "strza" in c):
            mapa[col] = KOLUMNA_LIMIT
        elif "kolej" in c:
            mapa[col] = KOLUMNA_KOLEJNOSC

    df = df.rename(columns=mapa)

    for col in WYMAGANE_KOLUMNY:
        if col not in df.columns:
            df[col] = ""

    for col in KOLUMNY_STRZALOW:
        if col not in df.columns:
            df[col] = ""

    if KOLUMNA_LIMIT not in df.columns:
        df[KOLUMNA_LIMIT] = ""

    if KOLUMNA_KOLEJNOSC not in df.columns:
        df[KOLUMNA_KOLEJNOSC] = ""

    for col in df.columns:
        df[col] = df[col].fillna("").astype(str)

    df["Nazwisko"] = df["Nazwisko"].str.strip().str.upper()
    df["Zmiana"] = df["Zmiana"].str.strip()
    df[KOLUMNA_KONKURENCJA] = df[KOLUMNA_KONKURENCJA].apply(normalizuj_konkurencje)
    df["Status"] = df["Status"].str.strip()
    df["Suma trafień"] = df["Suma trafień"].str.strip()
    df["Ile za pierwszym"] = df["Ile za pierwszym"].str.strip()
    df[KOLUMNA_LIMIT] = df[KOLUMNA_LIMIT].str.strip()
    df[KOLUMNA_KOLEJNOSC] = df[KOLUMNA_KOLEJNOSC].str.strip()

    df = df[df["Nazwisko"] != ""].copy()

    wazne = WYMAGANE_KOLUMNY + [KOLUMNA_LIMIT, KOLUMNA_KOLEJNOSC] + KOLUMNY_STRZALOW
    pozostale = [c for c in df.columns if c not in wazne]
    return df[wazne + pozostale]


def pobierz_liste_z_google(link: str) -> pd.DataFrame:
    csv_url = google_link_do_csv_url(link)
    df = pd.read_csv(csv_url, dtype=str)
    return normalizuj_naglowki(df)


def czy_ma_wynik(wartosc) -> bool:
    txt = str(wartosc).strip().lower()
    return txt not in ["", "nan", "none"]


def lista_konkurencji(df: pd.DataFrame) -> list[str]:
    if df.empty or KOLUMNA_KONKURENCJA not in df.columns:
        return KONKURENCJE_DOMYSLNE

    wynik = sorted(
        {
            normalizuj_konkurencje(x)
            for x in df[KOLUMNA_KONKURENCJA].dropna().astype(str).tolist()
            if str(x).strip()
        }
    )

    if not wynik:
        return KONKURENCJE_DOMYSLNE

    return wynik


def zbuduj_ranking(df_input: pd.DataFrame, konkurencja: str) -> pd.DataFrame:
    kolumny = [
        "Miejsce",
        "Nazwisko i Imię",
        "Konkurencja",
        "Grupa / Zmiana",
        "Limit rzutków",
        "Suma Trafień (Wynik)",
        "Trafienia z 1. Strzału",
    ]

    if df_input.empty:
        return pd.DataFrame(columns=kolumny)

    df = normalizuj_naglowki(df_input)
    konkurencja = normalizuj_konkurencje(konkurencja)

    df["Suma_num"] = pd.to_numeric(df["Suma trafień"], errors="coerce")
    df["Pierwszy_num"] = pd.to_numeric(df["Ile za pierwszym"], errors="coerce").fillna(0)
    df["Limit_num"] = pd.to_numeric(df[KOLUMNA_LIMIT], errors="coerce")

    df = df[
        (df[KOLUMNA_KONKURENCJA] == konkurencja)
        & (df["Zmiana"].str.strip() != "")
        & (df["Suma_num"].notna())
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=kolumny)

    df = df.sort_values(
        by=["Suma_num", "Pierwszy_num", "Nazwisko"],
        ascending=[False, False, True],
    )

    miejsca = []
    poprzedni_wynik = None
    poprzedni_pierwszy = None

    for i, (_, row) in enumerate(df.iterrows()):
        wynik = row["Suma_num"]
        pierwszy = row["Pierwszy_num"]

        if i == 0:
            miejsce = 1
        elif wynik == poprzedni_wynik and pierwszy == poprzedni_pierwszy:
            miejsce = miejsca[-1]
        else:
            miejsce = i + 1

        miejsca.append(miejsce)
        poprzedni_wynik = wynik
        poprzedni_pierwszy = pierwszy

    return pd.DataFrame({
        "Miejsce": miejsca,
        "Nazwisko i Imię": df["Nazwisko"].values,
        "Konkurencja": df[KOLUMNA_KONKURENCJA].values,
        "Grupa / Zmiana": df["Zmiana"].values,
        "Limit rzutków": df["Limit_num"].fillna(0).astype(int).replace(0, "").values,
        "Suma Trafień (Wynik)": df["Suma_num"].astype(int).values,
        "Trafienia z 1. Strzału": df["Pierwszy_num"].astype(int).values,
    })


def bezpieczna_nazwa_arkusza(nazwa: str) -> str:
    nazwa = re.sub(r"[\[\]\:\*\?\/\\]", "_", str(nazwa))
    nazwa = nazwa.strip() or "Ranking"
    return nazwa[:31]


def zapisz_excel(df: pd.DataFrame, path: Path) -> None:
    df = normalizuj_naglowki(df)
    konkurencje = lista_konkurencji(df)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=ARKUSZ_WYNIKI, index=False)

        # Zgodność wsteczna: jeśli istnieje STANDARD i PK, stare nazwy arkuszy też będą zapisane.
        if "STANDARD" in konkurencje:
            zbuduj_ranking(df, "STANDARD").to_excel(writer, sheet_name=ARKUSZ_REZULTATY, index=False)
        if "PK" in konkurencje:
            zbuduj_ranking(df, "PK").to_excel(writer, sheet_name=ARKUSZ_REZULTATY_PK, index=False)

        for konkurencja in konkurencje:
            ranking = zbuduj_ranking(df, konkurencja)
            nazwa_arkusza = bezpieczna_nazwa_arkusza(f"{ARKUSZ_REZULTATY_PREFIX} {konkurencja}")
            ranking.to_excel(writer, sheet_name=nazwa_arkusza, index=False)


def wczytaj_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=WYMAGANE_KOLUMNY + [KOLUMNA_LIMIT, KOLUMNA_KOLEJNOSC] + KOLUMNY_STRZALOW)

    try:
        df = pd.read_excel(path, sheet_name=ARKUSZ_WYNIKI, dtype=str)
    except Exception:
        df = pd.read_excel(path, sheet_name=0, dtype=str)

    return normalizuj_naglowki(df)


def aktywny_path() -> Path | None:
    if st.session_state.get("zawody_zakonczone", False):
        return None

    val = st.session_state.get("aktywny_plik", "")

    if val:
        path = Path(val)
        if path.exists():
            return path

    pliki = lista_plikow_zawodow()
    if pliki:
        st.session_state.aktywny_plik = str(pliki[0])
        return pliki[0]

    return None


def kolejny_numer_zmiany(df: pd.DataFrame) -> int:
    maks = 0

    if "Zmiana" not in df.columns:
        return 1

    for zm in df["Zmiana"].dropna().astype(str):
        if "Zmiana" in zm:
            try:
                nr = int(zm.replace("Zmiana", "").strip())
                maks = max(maks, nr)
            except ValueError:
                pass

    return maks + 1


def status_startu(df: pd.DataFrame, nazwisko: str, konkurencja: str) -> bool:
    df = normalizuj_naglowki(df)
    konkurencja = normalizuj_konkurencje(konkurencja)

    wiersze = df[
        (df["Nazwisko"] == str(nazwisko).strip().upper())
        & (df[KOLUMNA_KONKURENCJA] == konkurencja)
    ]

    return wiersze["Suma trafień"].apply(czy_ma_wynik).any()


def zbuduj_liste_dostepnych(df: pd.DataFrame, konkurencja: str | None = None) -> list[dict]:
    wynik = []
    df = normalizuj_naglowki(df)

    if konkurencja:
        konkurencja = normalizuj_konkurencje(konkurencja)
        df = df[df[KOLUMNA_KONKURENCJA] == konkurencja].copy()

    for _, row in df.sort_values(["Nazwisko", KOLUMNA_KONKURENCJA]).iterrows():
        nazwisko = str(row["Nazwisko"]).strip()
        konk = normalizuj_konkurencje(row[KOLUMNA_KONKURENCJA])
        suma = row["Suma trafień"]

        if not nazwisko:
            continue

        if czy_ma_wynik(suma):
            continue

        wyswietl = f"{nazwisko} [{konk}]"

        wynik.append({
            "wyswietl": wyswietl,
            "nazwisko": nazwisko,
            "konkurencja": konk,
        })

    return wynik


def zapisz_pusty_start_zmiany(path: Path) -> None:
    df = wczytaj_excel(path)

    for kolejnosc, zaw in enumerate(st.session_state.wybrani_zawodnicy, start=1):
        nazwisko = zaw["nazwisko"]
        konkurencja = zaw["konkurencja"]

        maska = (
            (df["Nazwisko"] == nazwisko)
            & (df[KOLUMNA_KONKURENCJA] == konkurencja)
            & (df["Zmiana"] == st.session_state.nazwa_zmiany)
        )

        if maska.any():
            continue

        indeksy = df[
            (df["Nazwisko"] == nazwisko)
            & (df[KOLUMNA_KONKURENCJA] == konkurencja)
        ].index.tolist()

        pusty_idx = None

        for idx in indeksy:
            if not czy_ma_wynik(df.at[idx, "Suma trafień"]):
                pusty_idx = idx
                break

        if pusty_idx is not None:
            df.at[pusty_idx, "Zmiana"] = st.session_state.nazwa_zmiany
            df.at[pusty_idx, KOLUMNA_KONKURENCJA] = konkurencja
            df.at[pusty_idx, "Status"] = "W TRAKCIE"
            df.at[pusty_idx, KOLUMNA_KOLEJNOSC] = str(kolejnosc)
            df.at[pusty_idx, KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
        else:
            nowy = {col: "" for col in WYMAGANE_KOLUMNY + [KOLUMNA_LIMIT, KOLUMNA_KOLEJNOSC] + KOLUMNY_STRZALOW}
            nowy["Nazwisko"] = nazwisko
            nowy["Zmiana"] = st.session_state.nazwa_zmiany
            nowy[KOLUMNA_KONKURENCJA] = konkurencja
            nowy["Status"] = "W TRAKCIE"
            nowy[KOLUMNA_KOLEJNOSC] = str(kolejnosc)
            nowy[KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)

    zapisz_excel(df, path)


def zapisz_robocze_strzaly_zmiany(path: Path) -> None:
    if not st.session_state.get("wybrani_zawodnicy"):
        return

    df = wczytaj_excel(path)

    for kolejnosc, zaw in enumerate(st.session_state.wybrani_zawodnicy, start=1):
        nazwisko = zaw["nazwisko"]
        konkurencja = zaw["konkurencja"]
        id_u = zaw["id_unikalne"]
        strzaly = st.session_state.macierz_wynikow.get(id_u, [])

        maska = (
            (df["Nazwisko"] == nazwisko)
            & (df[KOLUMNA_KONKURENCJA] == konkurencja)
            & (df["Zmiana"] == st.session_state.nazwa_zmiany)
        )

        if maska.any():
            idx = df[maska].index[0]
        else:
            nowy = {col: "" for col in WYMAGANE_KOLUMNY + [KOLUMNA_LIMIT, KOLUMNA_KOLEJNOSC] + KOLUMNY_STRZALOW}
            nowy["Nazwisko"] = nazwisko
            nowy["Zmiana"] = st.session_state.nazwa_zmiany
            nowy[KOLUMNA_KONKURENCJA] = konkurencja
            nowy[KOLUMNA_KOLEJNOSC] = str(kolejnosc)
            nowy[KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            idx = df.index[-1]

        df.at[idx, "Status"] = "W TRAKCIE"
        df.at[idx, KOLUMNA_KOLEJNOSC] = str(kolejnosc)
        df.at[idx, KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
        df.at[idx, "Suma trafień"] = ""
        df.at[idx, "Ile za pierwszym"] = ""

        for i in range(1, MAX_RZUTKOW + 1):
            col = f"Strzał_{i}"
            df.at[idx, col] = strzaly[i - 1] if i <= len(strzaly) else ""

    zapisz_excel(df, path)


def zapisz_wyniki_zmiany(path: Path) -> None:
    df = wczytaj_excel(path)

    for kolejnosc, zaw in enumerate(st.session_state.wybrani_zawodnicy, start=1):
        nazwisko = zaw["nazwisko"]
        konkurencja = zaw["konkurencja"]
        id_u = zaw["id_unikalne"]

        strzaly = st.session_state.macierz_wynikow.get(id_u, [])
        suma = str(sum(1 for s in strzaly if s in ["/", "X"]))
        pierwszy = str(sum(1 for s in strzaly if s == "/"))

        maska = (
            (df["Nazwisko"] == nazwisko)
            & (df[KOLUMNA_KONKURENCJA] == konkurencja)
            & (df["Zmiana"] == st.session_state.nazwa_zmiany)
        )

        if maska.any():
            idx = df[maska].index[0]
        else:
            nowy = {col: "" for col in WYMAGANE_KOLUMNY + [KOLUMNA_LIMIT, KOLUMNA_KOLEJNOSC] + KOLUMNY_STRZALOW}
            nowy["Nazwisko"] = nazwisko
            nowy["Zmiana"] = st.session_state.nazwa_zmiany
            nowy[KOLUMNA_KONKURENCJA] = konkurencja
            nowy[KOLUMNA_KOLEJNOSC] = str(kolejnosc)
            nowy[KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            idx = df.index[-1]

        df.at[idx, "Status"] = f"{konkurencja} ZAKOŃCZONE"
        df.at[idx, KOLUMNA_KOLEJNOSC] = str(kolejnosc)
        df.at[idx, KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
        df.at[idx, "Suma trafień"] = suma
        df.at[idx, "Ile za pierwszym"] = pierwszy

        for i in range(1, MAX_RZUTKOW + 1):
            col = f"Strzał_{i}"
            df.at[idx, col] = strzaly[i - 1] if i <= len(strzaly) else ""

    zapisz_excel(df, path)


def znajdz_przerwana_zmiane(df_input: pd.DataFrame) -> dict | None:
    if df_input.empty or "Status" not in df_input.columns or "Zmiana" not in df_input.columns:
        return None

    df = normalizuj_naglowki(df_input)
    robocze = df[df["Status"].str.upper().str.strip() == "W TRAKCIE"].copy()

    if robocze.empty:
        return None

    nazwy_zmian = [z for z in robocze["Zmiana"].dropna().astype(str).unique() if z.strip()]
    if not nazwy_zmian:
        return None

    nazwa_zmiany = nazwy_zmian[-1]
    robocze = robocze[robocze["Zmiana"].astype(str) == nazwa_zmiany].copy()

    konkurencje = robocze[KOLUMNA_KONKURENCJA].dropna().astype(str).unique().tolist()
    konkurencja = konkurencje[0] if konkurencje else ""

    limit_series = pd.to_numeric(robocze.get(KOLUMNA_LIMIT, pd.Series(dtype=str)), errors="coerce").dropna()
    if not limit_series.empty:
        limit = int(limit_series.iloc[0])
    else:
        ostatni_zapisany = 0
        for i in range(1, MAX_RZUTKOW + 1):
            col = f"Strzał_{i}"
            if col in robocze.columns:
                ma_dane = robocze[col].astype(str).str.strip().replace({"nan": "", "None": ""})
                if ma_dane.apply(lambda x: x not in ["", "-"]).any():
                    ostatni_zapisany = i
        limit = max(10, ostatni_zapisany)
        limit = min(limit, MAX_RZUTKOW)

    return {
        "nazwa_zmiany": nazwa_zmiany,
        "konkurencja": konkurencja,
        "liczba_zawodnikow": len(robocze),
        "limit": limit,
    }


def wznow_przerwana_zmiane(path: Path, nazwa_zmiany: str | None = None) -> bool:
    df = wczytaj_excel(path)
    robocze = df[df["Status"].str.upper().str.strip() == "W TRAKCIE"].copy()

    if robocze.empty:
        return False

    if nazwa_zmiany:
        robocze = robocze[robocze["Zmiana"].astype(str) == str(nazwa_zmiany)].copy()
    else:
        nazwy_zmian = [z for z in robocze["Zmiana"].dropna().astype(str).unique() if z.strip()]
        if not nazwy_zmian:
            return False
        nazwa_zmiany = nazwy_zmian[-1]
        robocze = robocze[robocze["Zmiana"].astype(str) == str(nazwa_zmiany)].copy()

    if robocze.empty:
        return False

    if KOLUMNA_KOLEJNOSC in robocze.columns:
        robocze["_kolejnosc_num"] = pd.to_numeric(robocze[KOLUMNA_KOLEJNOSC], errors="coerce")
        robocze = robocze.sort_values(["_kolejnosc_num", "Nazwisko"], na_position="last")
    else:
        robocze = robocze.sort_index()

    limit_series = pd.to_numeric(robocze.get(KOLUMNA_LIMIT, pd.Series(dtype=str)), errors="coerce").dropna()
    if not limit_series.empty:
        limit = int(limit_series.iloc[0])
    else:
        ostatni_zapisany = 0
        for i in range(1, MAX_RZUTKOW + 1):
            col = f"Strzał_{i}"
            if col in robocze.columns:
                ma_dane = robocze[col].astype(str).str.strip().replace({"nan": "", "None": ""})
                if ma_dane.apply(lambda x: x not in ["", "-"]).any():
                    ostatni_zapisany = i
        limit = max(10, ostatni_zapisany)
        limit = min(limit, MAX_RZUTKOW)

    wybrani = []
    macierz = {}

    for _, row in robocze.iterrows():
        nazwisko = str(row.get("Nazwisko", "")).strip().upper()
        konkurencja = normalizuj_konkurencje(row.get(KOLUMNA_KONKURENCJA, "TRAP20"))
        id_unikalne = f"{nazwisko} [{konkurencja}]"

        if not nazwisko:
            continue

        wybrani.append({
            "nazwisko": nazwisko,
            "id_unikalne": id_unikalne,
            "konkurencja": konkurencja,
        })

        strzaly = []
        for i in range(1, limit + 1):
            val = str(row.get(f"Strzał_{i}", "")).strip()
            if val in ["", "nan", "None"]:
                val = "-"
            strzaly.append(val)
        macierz[id_unikalne] = strzaly

    if not wybrani:
        return False

    aktualny_strzal = limit
    aktualny_zawodnik_idx = 0

    znaleziono_puste = False
    for s_idx in range(limit):
        for z_idx, z in enumerate(wybrani):
            id_u = z["id_unikalne"]
            if macierz.get(id_u, [])[s_idx] == "-":
                aktualny_strzal = s_idx
                aktualny_zawodnik_idx = z_idx
                znaleziono_puste = True
                break
        if znaleziono_puste:
            break

    st.session_state.tryb_pracy = "STRZELANIE"
    st.session_state.wybrani_zawodnicy = wybrani
    st.session_state.macierz_wynikow = macierz
    st.session_state.aktualny_strzal = aktualny_strzal
    st.session_state.aktualny_zawodnik_idx = aktualny_zawodnik_idx
    st.session_state.limit_rzutkow = limit
    st.session_state.konkurencja_zmiany = wybrani[0]["konkurencja"]
    st.session_state.nazwa_zmiany = str(nazwa_zmiany)
    st.session_state.zapisano_zmiane = ""
    st.session_state.kopia_pobrana = False

    return True


def anuluj_przerwana_zmiane(path: Path, nazwa_zmiany: str) -> int:
    """
    Anuluje roboczą zmianę W TRAKCIE.
    Zostawia zawodników i konkurencję na liście startowej, ale czyści zmianę, status i strzały.
    Dzięki temu komunikat o wznowieniu znika, a starty wracają do wyboru.
    """
    df = wczytaj_excel(path)

    maska = (
        (df["Status"].str.upper().str.strip() == "W TRAKCIE")
        & (df["Zmiana"].astype(str) == str(nazwa_zmiany))
    )

    ile = int(maska.sum())

    if ile == 0:
        return 0

    for idx in df[maska].index:
        df.at[idx, "Zmiana"] = ""
        df.at[idx, "Status"] = ""
        df.at[idx, "Suma trafień"] = ""
        df.at[idx, "Ile za pierwszym"] = ""
        df.at[idx, KOLUMNA_KOLEJNOSC] = ""
        df.at[idx, KOLUMNA_LIMIT] = ""

        for i in range(1, MAX_RZUTKOW + 1):
            df.at[idx, f"Strzał_{i}"] = ""

    zapisz_excel(df, path)

    st.session_state.wybrani_zawodnicy = []
    st.session_state.macierz_wynikow = {}
    st.session_state.aktualny_strzal = 0
    st.session_state.aktualny_zawodnik_idx = 0
    st.session_state.zapisano_zmiane = ""
    st.session_state.kopia_pobrana = False
    st.session_state.reset_wyszukiwarki = int(st.session_state.get("reset_wyszukiwarki", 0)) + 1

    return ile


def zakoncz_i_wroc_do_menu():
    st.session_state.tryb_pracy = "MENU"
    st.session_state.wybrani_zawodnicy = []
    st.session_state.macierz_wynikow = {}
    st.session_state.aktualny_strzal = 0
    st.session_state.aktualny_zawodnik_idx = 0
    st.session_state.zapisano_zmiane = ""


def zamknij_zawody_do_archiwum(path: Path) -> Path | None:
    if not path.exists():
        return None

    arch_path = bezpieczna_nazwa_archiwum(path)
    shutil.move(str(path), str(arch_path))
    return arch_path


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "tryb_pracy": "MENU",
    "aktywny_plik": "",
    "google_link": "",
    "wybrani_zawodnicy": [],
    "macierz_wynikow": {},
    "aktualny_strzal": 0,
    "aktualny_zawodnik_idx": 0,
    "limit_rzutkow": 20,
    "konkurencja_zmiany": "TRAP20",
    "nazwa_zmiany": "",
    "reset_wyszukiwarki": 0,
    "kopia_pobrana": False,
    "ostatnio_przywrocony_upload": "",
    "zawody_zakonczone": False,
    "event_id": "default",
    "event_name": "",
    "event_cfg": {},
    "admin_logged": False,
    "admin_mode": False,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ============================================================
# TRYB WIDOKU: ADMIN / ZAWODNIK
# ============================================================

view_param = st.query_params.get("view", "admin")
if isinstance(view_param, list):
    view_param = view_param[0] if view_param else "admin"

TRYB_ZAWODNIKA = str(view_param).strip().lower() in ["zawodnik", "wyniki", "public"]

event_param = st.query_params.get("event", "")
if isinstance(event_param, list):
    event_param = event_param[0] if event_param else ""

if str(event_param).strip():
    # Link publiczny może wyglądać: ?event=snajper_lublin_20260620&view=zawodnik
    ustaw_event(str(event_param).strip(), str(event_param).strip(), {})

if TRYB_ZAWODNIKA:
    st.markdown(
        """
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    .block-container {padding-top: 0.7rem;}
</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================

if not TRYB_ZAWODNIKA:
    st.sidebar.header("📁 Plik zawodów")

    EVENTS = wczytaj_events()

    with st.sidebar.expander("🔐 Administrator", expanded=False):
        if st.session_state.get("admin_logged", False):
            st.success("Zalogowano jako administrator.")
            st.session_state.admin_mode = st.checkbox(
                "Otwórz panel administratora",
                value=bool(st.session_state.get("admin_mode", False)),
            )

            if st.button("Wyloguj administratora", use_container_width=True):
                st.session_state.admin_logged = False
                st.session_state.admin_mode = False
                st.rerun()
        else:
            admin_pass = st.text_input("Hasło administratora:", type="password")
            if st.button("Zaloguj", use_container_width=True):
                if admin_pass == haslo_admina(EVENTS):
                    st.session_state.admin_logged = True
                    st.session_state.admin_mode = True
                    st.rerun()
                else:
                    st.error("Nieprawidłowe hasło administratora.")

    if st.session_state.get("event_name"):
        st.sidebar.caption(f"Aktywne zawody: {st.session_state.event_name}")
        st.sidebar.caption(f"ID: {aktywny_event_id()}")

    kod_listy = st.sidebar.text_input(
        "Kod zawodów:",
        placeholder="np. snajper",
    ).strip().lower()

    uzyj_wlasnego_linku = st.sidebar.checkbox("Użyj własnego linku Google Sheets")
    wlasny_link = ""

    if uzyj_wlasnego_linku:
        wlasny_link = st.sidebar.text_input(
            "Publiczny link Google Sheets do odczytu:",
            value="",
            placeholder="https://docs.google.com/spreadsheets/d/...",
            key="custom_google_link",
        ).strip()

    if st.sidebar.button("📥 Utwórz NOWY plik zawodów", use_container_width=True):
        try:
            link_do_pobrania = ""

            if kod_listy:
                if kod_listy not in EVENTS:
                    st.sidebar.error("Nieznany kod zawodów. Sprawdź events.json.")
                    st.stop()

                event_cfg = EVENTS[kod_listy]
                aktywny, komunikat = event_aktywny(event_cfg)
                if not aktywny:
                    st.sidebar.error(komunikat)
                    st.stop()

                link_do_pobrania = str(event_cfg.get("google_sheet", "")).strip()
                if not link_do_pobrania:
                    st.sidebar.error("W events.json brakuje pola google_sheet dla tego kodu.")
                    st.stop()

                event_id = event_cfg.get("event_id", kod_listy)
                event_name = event_cfg.get("nazwa", event_id)
                ustaw_event(event_id, event_name, event_cfg)

            elif uzyj_wlasnego_linku:
                if not wlasny_link:
                    st.sidebar.error("Wklej własny link Google Sheets.")
                    st.stop()
                tymczasowy_event_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                ustaw_event(tymczasowy_event_id, "Zawody ręczne", {"enabled": True, "google_sheet": wlasny_link})
                link_do_pobrania = wlasny_link

            else:
                st.sidebar.error("Wpisz kod zawodów z events.json albo zaznacz własny link.")
                st.stop()

            df_google = pobierz_liste_z_google(link_do_pobrania)
            nowy_plik = nazwa_nowego_pliku()
            zapisz_excel(df_google, nowy_plik)

            st.session_state.zawody_zakonczone = False
            st.session_state.aktywny_plik = str(nowy_plik)

            if "custom_google_link" in st.session_state:
                st.session_state.custom_google_link = ""

            zakoncz_i_wroc_do_menu()

            st.sidebar.success(f"Utworzono plik: {nowy_plik.name}")
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"Nie udało się utworzyć pliku zawodów: {e}")

    st.sidebar.markdown("---")
    st.sidebar.subheader("♻️ Przywróć z kopii")

    upload_backup = st.sidebar.file_uploader(
        "Wgraj ostatni pobrany Excel:",
        type=["xlsx"],
        key="upload_backup_excel",
    )

    if upload_backup is not None:
        upload_id = f"{upload_backup.name}_{getattr(upload_backup, 'size', 0)}"

        if st.session_state.get("ostatnio_przywrocony_upload", "") != upload_id:
            try:
                if upload_backup.name.startswith("trap20_zawody_") and upload_backup.name.endswith(".xlsx"):
                    backup_name = upload_backup.name
                else:
                    znacznik = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_name = f"trap20_zawody_przywrocony_{znacznik}.xlsx"

                backup_path = aktywny_event_dir() / backup_name
                backup_path.write_bytes(upload_backup.getbuffer())

                df_backup = wczytaj_excel(backup_path)
                zapisz_excel(df_backup, backup_path)

                st.session_state.zawody_zakonczone = False
                st.session_state.aktywny_plik = str(backup_path)
                st.session_state.ostatnio_przywrocony_upload = upload_id
                zakoncz_i_wroc_do_menu()

                st.sidebar.success(f"Przywrócono plik: {backup_path.name}")
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"Nie udało się przywrócić pliku Excel: {e}")
        else:
            st.sidebar.info("Ta kopia jest już przywrócona jako aktywny plik.")

    pliki = lista_plikow_zawodow()

    if pliki and not st.session_state.get("zawody_zakonczone", False):
        nazwy = [p.name for p in pliki]

        aktualny = aktywny_path()
        aktualna_nazwa = aktualny.name if aktualny else nazwy[0]
        index = nazwy.index(aktualna_nazwa) if aktualna_nazwa in nazwy else 0

        wybor_pliku = st.sidebar.selectbox(
            "Aktywny plik zawodów:",
            nazwy,
            index=index,
        )

        wybrany_path = aktywny_event_dir() / wybor_pliku

        if str(wybrany_path) != st.session_state.aktywny_plik:
            st.session_state.aktywny_plik = str(wybrany_path)
            zakoncz_i_wroc_do_menu()
            st.rerun()

        st.sidebar.download_button(
            "⬇️ Pobierz aktywny Excel",
            data=wybrany_path.read_bytes(),
            file_name=wybrany_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.sidebar.markdown("---")

        if st.sidebar.button("📦 Zakończ zawody i przenieś do archiwum", use_container_width=True):
            try:
                arch_path = zamknij_zawody_do_archiwum(wybrany_path)

                st.session_state.aktywny_plik = ""
                st.session_state.zawody_zakonczone = True
                st.session_state.google_link = ""

                if "custom_google_link" in st.session_state:
                    st.session_state.custom_google_link = ""

                st.session_state.ostatnio_przywrocony_upload = ""
                st.session_state.reset_wyszukiwarki = int(st.session_state.get("reset_wyszukiwarki", 0)) + 1

                zakoncz_i_wroc_do_menu()

                if arch_path:
                    st.sidebar.success(f"Zawody zakończone. Plik przeniesiono do archiwum: {arch_path.name}")
                else:
                    st.sidebar.success("Zawody zakończone.")
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"Nie udało się zakończyć zawodów: {e}")
    else:
        if st.session_state.get("zawody_zakonczone", False):
            st.sidebar.success("Zawody zakończone. Utwórz nowy plik zawodów, aby rozpocząć kolejne.")
        else:
            st.sidebar.warning("Brak pliku zawodów dla aktywnego ID. Pobierz listę z Google.")


# ============================================================
# PANEL ADMINISTRATORA
# ============================================================

if not TRYB_ZAWODNIKA and st.session_state.get("admin_logged", False) and st.session_state.get("admin_mode", False):
    pokaz_panel_administratora()
    st.stop()


# ============================================================
# GŁÓWNY WIDOK
# ============================================================

path = aktywny_path()

if path is None:
    if st.session_state.get("zawody_zakonczone", False):
        st.success("Zawody zostały zakończone. Aby rozpocząć nowe, pobierz listę z Google i utwórz nowy plik zawodów.")
    else:
        st.warning("Najpierw wpisz kod zawodów / link Google i utwórz plik zawodów.")
    st.stop()

df_baza = wczytaj_excel(path)


def pokaz_info_o_pliku_na_dole(path: Path) -> None:
    st.markdown(
        f"""
<div class="file-info-footer">
    <div>Google służy tylko do pobrania listy. Cała praca odbywa się na aktywnym pliku Excel zawodów.</div>
    <div style="margin-top: 6px;">Zawody: <code>{st.session_state.get("event_name") or aktywny_event_id()}</code></div>
    <div style="margin-top: 6px;">Aktywny plik: <code>{path.name}</code></div>
</div>
""",
        unsafe_allow_html=True,
    )


def html_strzaly_dla_podgladu(row: pd.Series) -> str:
    html = ""
    limit = pd.to_numeric(row.get(KOLUMNA_LIMIT, MAX_RZUTKOW), errors="coerce")
    try:
        limit = int(limit)
    except Exception:
        limit = MAX_RZUTKOW

    limit = max(1, min(limit, MAX_RZUTKOW))

    for i in range(1, limit + 1):
        val = str(row.get(f"Strzał_{i}", "")).strip()
        if not val or val in ["-", "nan", "None"]:
            continue

        if val == "/":
            klasa = "shot-t1"
        elif val == "X":
            klasa = "shot-t2"
        elif val == "O":
            klasa = "shot-miss"
        else:
            klasa = "shot-blank"

        html += f'<span class="shot-box {klasa}">{val}</span>'
        if i % 5 == 0:
            html += "&nbsp;&nbsp;"

    return html if html else "<span style='color:#94a3b8;'>Brak zapisanych strzałów</span>"


def pokaz_panel_zawodnika(df: pd.DataFrame, path: Path) -> None:
    st.markdown('<div class="main-title">📊 TRAP20 — wyniki zawodów</div>', unsafe_allow_html=True)
    st.caption("Publiczny podgląd dla zawodników. Ten widok nie pozwala edytować wyników.")

    if st.button("🔄 Odśwież wyniki"):
        st.rerun()

    st.markdown("---")

    konkurencje = lista_konkurencji(df)

    tabs = st.tabs([f"🏆 {k}" for k in konkurencje] + ["🔎 Sprawdź zawodnika"])

    for tab, konkurencja in zip(tabs[:-1], konkurencje):
        with tab:
            st.dataframe(zbuduj_ranking(df, konkurencja), use_container_width=True, hide_index=True)

    with tabs[-1]:
        szukaj = st.text_input(
            "Wpisz nazwisko zawodnika:",
            placeholder="np. KOWALSKI",
            key="public_szukaj_zawodnika",
        ).strip().upper()

        df_pokaz = normalizuj_naglowki(df)
        df_pokaz = df_pokaz[df_pokaz["Suma trafień"].apply(czy_ma_wynik)].copy()

        if szukaj:
            df_pokaz = df_pokaz[df_pokaz["Nazwisko"].str.upper().str.contains(szukaj, na=False)]

        if df_pokaz.empty:
            st.info("Brak zapisanych wyników dla podanego filtra.")
        else:
            for _, row in df_pokaz.sort_values(["Nazwisko", KOLUMNA_KONKURENCJA, "Zmiana"]).iterrows():
                suma = str(row.get("Suma trafień", "")).strip() or "0"
                pierwszy = str(row.get("Ile za pierwszym", "")).strip() or "0"
                st.markdown(
                    f"""
<div class="player-row">
    <div class="player-stand">{row.get('Zmiana', '')}</div>
    <div>
        <div class="player-name">{row.get('Nazwisko', '')}</div>
        <div class="player-type">{row.get(KOLUMNA_KONKURENCJA, '')}</div>
    </div>
    <div class="player-shots">{html_strzaly_dla_podgladu(row)}</div>
    <div class="player-sum">{suma} / {pierwszy}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    pokaz_info_o_pliku_na_dole(path)


if TRYB_ZAWODNIKA:
    pokaz_panel_zawodnika(df_baza, path)
    st.stop()


# ============================================================
# MENU STARTOWE
# ============================================================

if st.session_state.tryb_pracy == "MENU":
    konkurencje_dostepne = lista_konkurencji(df_baza)

    col_m1, col_m2, col_m3, col_m4 = st.columns([1, 2, 1, 1])

    with col_m1:
        nr_zmiany = st.number_input(
            "Numer zmiany:",
            min_value=1,
            value=kolejny_numer_zmiany(df_baza),
            step=1,
        )

    with col_m2:
        index_konk = 0
        if st.session_state.get("konkurencja_zmiany") in konkurencje_dostepne:
            index_konk = konkurencje_dostepne.index(st.session_state.konkurencja_zmiany)

        konkurencja_zmiany = st.selectbox(
            "Konkurencja:",
            konkurencje_dostepne,
            index=index_konk,
        )

    suggested_limit = limit_dla_konkurencji(konkurencja_zmiany, 20)

    with col_m3:
        opcje_limitow = [10, 15, 20, 25]
        if suggested_limit not in opcje_limitow:
            opcje_limitow = sorted(set(opcje_limitow + [int(suggested_limit)]))

        limit_index = opcje_limitow.index(int(suggested_limit))

        limit_rzutkow = st.selectbox(
            "Liczba rzutków:",
            opcje_limitow,
            index=limit_index,
            disabled=True,
            help="Limit wynika z konfiguracji konkurencji w events.json / panelu administratora.",
        )
        st.caption("Limit jest przypisany do konkurencji.")

    with col_m4:
        st.metric("Zawodnicy", df_baza["Nazwisko"].nunique())

    przerwana = znajdz_przerwana_zmiane(df_baza)
    if przerwana and not st.session_state.get("wybrani_zawodnicy"):
        st.warning(
            f"Wykryto przerwaną zmianę: {przerwana['nazwa_zmiany']} "
            f"— {przerwana.get('konkurencja', '')} "
            f"({przerwana['liczba_zawodnikow']} zawodników, {przerwana['limit']} rzutków)."
        )
        c_wznow, c_anuluj = st.columns(2)

        with c_wznow:
            if st.button("▶️ Wznów przerwaną zmianę", type="primary", use_container_width=True):
                if wznow_przerwana_zmiane(path, przerwana["nazwa_zmiany"]):
                    st.rerun()
                else:
                    st.error("Nie udało się wznowić przerwanej zmiany z aktywnego pliku.")

        with c_anuluj:
            if st.button("🧹 Anuluj przerwaną zmianę", use_container_width=True):
                ile = anuluj_przerwana_zmiane(path, przerwana["nazwa_zmiany"])
                if ile:
                    st.success(f"Anulowano przerwaną zmianę. Wyczyszczono {ile} startów roboczych.")
                    st.rerun()
                else:
                    st.info("Nie znaleziono roboczych startów do anulowania.")

    st.markdown("---")
    st.subheader("📋 Skład zmiany")

    dostepni = zbuduj_liste_dostepnych(df_baza, konkurencja_zmiany)

    juz_dodani = {
        z["id_unikalne"]
        for z in st.session_state.wybrani_zawodnicy
    }

    reset_id = int(st.session_state.get("reset_wyszukiwarki", 0))

    filtr = st.text_input(
        "Szukaj zawodnika:",
        placeholder="Wpisz kilka liter nazwiska...",
        key=f"filtr_zawodnika_{reset_id}",
    ).strip().upper()

    dostepni_po_filtrze = []

    for z in dostepni:
        if z["wyswietl"] in juz_dodani:
            continue

        if filtr and filtr not in z["wyswietl"].upper():
            continue

        dostepni_po_filtrze.append(z)

    opcje = [""] + [z["wyswietl"] for z in dostepni_po_filtrze]

    col1, col2 = st.columns([4, 3])

    with col1:
        wybor = st.selectbox(
            "Wybierz zawodnika z listy:",
            options=opcje,
            index=0,
            key=f"wybor_zawodnika_{reset_id}",
        )

        if filtr:
            st.caption(f"Znaleziono: {len(dostepni_po_filtrze)}")

    with col2:
        reczny = st.text_input(
            "Dopisz ręcznie:",
            placeholder="Nazwisko i imię",
            key="reczny_zawodnik",
        ).strip().upper()

    if st.button("➕ Dodaj zawodnika", type="primary"):
        if len(st.session_state.wybrani_zawodnicy) >= 6:
            st.error("W jednej zmianie może być maksymalnie 6 zawodników.")
        else:
            nazwisko = ""
            konkurencja = normalizuj_konkurencje(konkurencja_zmiany)

            if wybor and wybor.strip():
                obj = next((z for z in dostepni if z["wyswietl"] == wybor), None)

                if obj:
                    nazwisko = obj["nazwisko"]
                    konkurencja = obj["konkurencja"]

            elif reczny:
                nazwisko = reczny

            if not nazwisko:
                st.error("Wybierz zawodnika albo wpisz nazwisko ręcznie.")
            else:
                if status_startu(df_baza, nazwisko, konkurencja):
                    st.error(f"{nazwisko} ma już zapisany wynik w konkurencji {konkurencja}.")
                else:
                    id_unikalne = f"{nazwisko} [{konkurencja}]"

                    if id_unikalne in juz_dodani:
                        st.error("Ten start jest już dodany do tej zmiany.")
                    else:
                        st.session_state.wybrani_zawodnicy.append({
                            "nazwisko": nazwisko,
                            "id_unikalne": id_unikalne,
                            "konkurencja": konkurencja,
                        })

                        st.session_state.reset_wyszukiwarki = int(st.session_state.get("reset_wyszukiwarki", 0)) + 1
                        st.rerun()

    if st.session_state.wybrani_zawodnicy:
        st.markdown("#### Wybrani zawodnicy")

        for i, z in enumerate(st.session_state.wybrani_zawodnicy):
            c1, c2, c3 = st.columns([1, 5, 1])

            with c1:
                st.write(f"**S {i + 1}**")

            with c2:
                st.info(f"{z['id_unikalne']}")

            with c3:
                if st.button("Usuń", key=f"del_{i}"):
                    st.session_state.wybrani_zawodnicy.pop(i)
                    st.rerun()

    st.markdown("---")

    if st.button("🚀 ROZPOCZNIJ ZMIANĘ", type="primary", use_container_width=True):
        if not st.session_state.wybrani_zawodnicy:
            st.error("Nie można rozpocząć bez zawodników.")
        else:
            st.session_state.tryb_pracy = "STRZELANIE"
            st.session_state.limit_rzutkow = int(limit_rzutkow)
            st.session_state.konkurencja_zmiany = normalizuj_konkurencje(konkurencja_zmiany)
            st.session_state.nazwa_zmiany = f"Zmiana {nr_zmiany}"
            st.session_state.aktualny_strzal = 0
            st.session_state.aktualny_zawodnik_idx = 0
            st.session_state.zapisano_zmiane = ""
            st.session_state.kopia_pobrana = False

            st.session_state.macierz_wynikow = {
                z["id_unikalne"]: ["-"] * int(limit_rzutkow)
                for z in st.session_state.wybrani_zawodnicy
            }

            zapisz_pusty_start_zmiany(path)
            st.rerun()

    st.markdown("---")
    st.subheader("📊 Rankingi z aktywnego pliku")

    konkurencje = lista_konkurencji(df_baza)
    tabs = st.tabs([f"🏆 {k}" for k in konkurencje] + ["📄 Wyniki szczegółowe"])

    for tab, konkurencja in zip(tabs[:-1], konkurencje):
        with tab:
            st.dataframe(zbuduj_ranking(df_baza, konkurencja), use_container_width=True, hide_index=True)

    with tabs[-1]:
        st.dataframe(df_baza, use_container_width=True, hide_index=True)

    pokaz_info_o_pliku_na_dole(path)


# ============================================================
# STRZELANIE
# ============================================================

elif st.session_state.tryb_pracy == "STRZELANIE":
    limit = int(st.session_state.limit_rzutkow)

    st.subheader(
        f"🏟️ {st.session_state.nazwa_zmiany} — "
        f"{st.session_state.get('konkurencja_zmiany', '')} — {limit} rzutków"
    )

    for i, z in enumerate(st.session_state.wybrani_zawodnicy):
        id_u = z["id_unikalne"]
        strzaly = st.session_state.macierz_wynikow.get(id_u, ["-"] * limit)

        suma = sum(1 for s in strzaly if s in ["/", "X"])
        pierwszy = sum(1 for s in strzaly if s == "/")

        html = ""

        for s_idx, s in enumerate(strzaly):
            if s == "/":
                klasa = "shot-t1"
            elif s == "X":
                klasa = "shot-t2"
            elif s == "O":
                klasa = "shot-miss"
            else:
                klasa = "shot-blank"

            pokaz = s

            if (
                st.session_state.aktualny_strzal < limit
                and s_idx == st.session_state.aktualny_strzal
                and i == st.session_state.aktualny_zawodnik_idx
            ):
                klasa += " current-target"
                if pokaz == "-":
                    pokaz = "●"

            html += f'<span class="shot-box {klasa}">{pokaz}</span>'

            if (s_idx + 1) % 5 == 0:
                html += "&nbsp;&nbsp;"

        st.markdown(
            f"""
<div class="player-row">
    <div class="player-stand">S {i + 1}</div>
    <div>
        <div class="player-name">{id_u}</div>
        <div class="player-type">{z["konkurencja"]}</div>
    </div>
    <div class="player-shots">{html}</div>
    <div class="player-sum">{suma} / {pierwszy}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    def rejestruj(symbol: str):
        if st.session_state.aktualny_strzal >= int(st.session_state.limit_rzutkow):
            return

        if not st.session_state.wybrani_zawodnicy:
            return

        zawodnik = st.session_state.wybrani_zawodnicy[st.session_state.aktualny_zawodnik_idx]
        id_u = zawodnik["id_unikalne"]

        if id_u not in st.session_state.macierz_wynikow:
            st.session_state.macierz_wynikow[id_u] = ["-"] * int(st.session_state.limit_rzutkow)

        if st.session_state.aktualny_strzal >= len(st.session_state.macierz_wynikow[id_u]):
            return

        st.session_state.macierz_wynikow[id_u][st.session_state.aktualny_strzal] = symbol

        st.session_state.aktualny_zawodnik_idx += 1

        if st.session_state.aktualny_zawodnik_idx >= len(st.session_state.wybrani_zawodnicy):
            st.session_state.aktualny_zawodnik_idx = 0
            st.session_state.aktualny_strzal += 1

        try:
            zapisz_robocze_strzaly_zmiany(path)
        except Exception as e:
            st.session_state["blad_autozapisu"] = str(e)

    if st.session_state.aktualny_strzal >= limit:
        st.success("🔥 Zmiana zakończona.")

        if "zapisano_zmiane" not in st.session_state:
            st.session_state.zapisano_zmiane = ""

        if st.session_state.zapisano_zmiane != st.session_state.nazwa_zmiany:
            try:
                zapisz_wyniki_zmiany(path)
                st.session_state.zapisano_zmiane = st.session_state.nazwa_zmiany
                st.success("Wyniki automatycznie zapisane do aktywnego pliku Excel. Rankingi przebudowane.")
            except Exception as e:
                st.error(f"Nie udało się automatycznie zapisać wyników: {e}")

        def oznacz_kopie_pobrana():
            st.session_state.kopia_pobrana = True

        st.download_button(
            "💾 Pobierz kopię bezpieczeństwa Excel",
            data=path.read_bytes(),
            file_name=path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
            on_click=oznacz_kopie_pobrana,
        )

        if st.session_state.get("kopia_pobrana", False):
            st.success("Kopia została pobrana. Możesz rozpocząć kolejną zmianę.")
            if st.button("✅ Nowa zmiana", type="primary", use_container_width=True):
                st.session_state.kopia_pobrana = False
                zakoncz_i_wroc_do_menu()
                st.rerun()
        else:
            st.warning("Najpierw pobierz kopię bezpieczeństwa Excel, potem rozpocznij nową zmianę.")

    else:
        aktualny = st.session_state.wybrani_zawodnicy[st.session_state.aktualny_zawodnik_idx]

        b1, b2, b3 = st.columns(3)

        with b1:
            st.button(
                "🔵 Trafiony 1 ( / )",
                type="primary",
                use_container_width=True,
                on_click=rejestruj,
                args=("/",),
            )

        with b2:
            st.button(
                "🟢 Trafiony 2 ( X )",
                use_container_width=True,
                on_click=rejestruj,
                args=("X",),
            )

        with b3:
            st.button(
                "🔴 Pudło ( O )",
                use_container_width=True,
                on_click=rejestruj,
                args=("O",),
            )

        st.markdown(
            f"""
<div class="current-player">
    <h3>📣 Bieżący strzał</h3>
    <div class="current-line">
        Stanowisko {st.session_state.aktualny_zawodnik_idx + 1}: {aktualny["id_unikalne"]}
        &nbsp; | &nbsp;
        Strzał {st.session_state.aktualny_strzal + 1} z {limit}
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    cnav1, cnav2, cnav3 = st.columns([1, 1, 1])

    with cnav2:
        if st.button("↩️ Cofnij ostatni wpis", use_container_width=True):
            if st.session_state.aktualny_strzal == 0 and st.session_state.aktualny_zawodnik_idx == 0:
                st.warning("Nie ma czego cofnąć.")
            else:
                if st.session_state.aktualny_zawodnik_idx == 0:
                    st.session_state.aktualny_strzal -= 1
                    st.session_state.aktualny_zawodnik_idx = len(st.session_state.wybrani_zawodnicy) - 1
                else:
                    st.session_state.aktualny_zawodnik_idx -= 1

                zawodnik = st.session_state.wybrani_zawodnicy[st.session_state.aktualny_zawodnik_idx]
                id_u = zawodnik["id_unikalne"]

                if id_u in st.session_state.macierz_wynikow:
                    if 0 <= st.session_state.aktualny_strzal < len(st.session_state.macierz_wynikow[id_u]):
                        st.session_state.macierz_wynikow[id_u][st.session_state.aktualny_strzal] = "-"

                try:
                    zapisz_robocze_strzaly_zmiany(path)
                except Exception as e:
                    st.session_state["blad_autozapisu"] = str(e)

                st.rerun()

    st.markdown('<div class="danger-zone"></div>', unsafe_allow_html=True)

    c_cancel1, c_cancel2, c_cancel3 = st.columns([1, 1, 1])
    with c_cancel3:
        if st.button("⬅️ Anuluj zmianę i wróć do menu", use_container_width=True):
            zakoncz_i_wroc_do_menu()
            st.rerun()

    pokaz_info_o_pliku_na_dole(path)
