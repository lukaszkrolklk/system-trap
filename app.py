import re
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
DATA_DIR.mkdir(exist_ok=True)

MAX_RZUTKOW = 25
WYMAGANE_KOLUMNY = [
    "Nazwisko",
    "Zmiana",
    "Typ",
    "Status",
    "Suma trafień",
    "Ile za pierwszym",
]

KOLUMNY_STRZALOW = [f"Strzał_{i}" for i in range(1, MAX_RZUTKOW + 1)]
ARKUSZ_WYNIKI = "Wyniki Szczegółowe"
ARKUSZ_REZULTATY = "Rezultaty"
ARKUSZ_REZULTATY_PK = "Rezultaty PK"

# Kolumny techniczne używane do bezpiecznego wznowienia przerwanej zmiany.
# Zostają w Excelu, ale nie przeszkadzają rankingom ani panelowi zawodnika.
KOLUMNA_KOLEJNOSC = "Kolejność w zmianie"
KOLUMNA_LIMIT = "Limit rzutków"


# ============================================================
# STYL
# ============================================================

st.markdown(
    """
<style>
    /* ============================================================
       TRAP20 — styl responsywny pod telefon / tablet
       ============================================================ */

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

    /* Kompaktowy wiersz zawodnika (Komputer) */
    .player-row {
        display: grid;
        /* Zwężono pierwszą kolumnę z 76px na 45px */
        grid-template-columns: 45px 160px minmax(300px, 1fr) 84px;
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
        /* Pozwolenie na zawijanie długich nazwisk */
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

    /* Telefon poziomo / mały tablet */
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
            /* Zwężono pierwszą kolumnę z 56px na 38px */
            grid-template-columns: 38px 124px minmax(235px, 1fr) 62px;
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

    /* Telefon pionowo (NAJWAŻNIEJSZE ZMIANY) */
    @media (max-width: 620px) {
        .player-row {
            /* Pierwsza kolumna na stanowisko (S 1) zwężona z 50px do 32px */
            grid-template-columns: 32px 1fr 58px;
            row-gap: 2px;
        }

        .player-stand {
            font-size: 12px;
        }

        .player-name {
            font-size: 13px;
            white-space: normal; /* Pozwala na ALICJA [następna linia] PIENIĘŻNIK */
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
        
        /* Poprawka dla mobilnego wyszukiwania - zapobiega ucinaniu kliknięć w selectboxy */
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

def lista_plikow_zawodow() -> list[Path]:
    return sorted(DATA_DIR.glob("trap20_zawody_*.xlsx"), reverse=True)


def nazwa_nowego_pliku() -> Path:
    znacznik = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / f"trap20_zawody_{znacznik}.xlsx"


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
        elif c == "typ" or "typ startu" in c:
            mapa[col] = "Typ"
        elif "status" in c:
            mapa[col] = "Status"
        elif "suma" in c and "traf" in c:
            mapa[col] = "Suma trafień"
        elif "pierwsz" in c:
            mapa[col] = "Ile za pierwszym"

    df = df.rename(columns=mapa)

    for col in WYMAGANE_KOLUMNY:
        if col not in df.columns:
            df[col] = ""

    for col in KOLUMNY_STRZALOW:
        if col not in df.columns:
            df[col] = ""

    # Wszystko jako tekst. To usuwa problem dtype str/int w Streamlit Cloud.
    for col in df.columns:
        df[col] = df[col].fillna("").astype(str)

    df["Nazwisko"] = df["Nazwisko"].str.strip().str.upper()
    df["Zmiana"] = df["Zmiana"].str.strip()
    df["Typ"] = df["Typ"].str.strip()
    df["Status"] = df["Status"].str.strip()
    df["Suma trafień"] = df["Suma trafień"].str.strip()
    df["Ile za pierwszym"] = df["Ile za pierwszym"].str.strip()

    df = df[df["Nazwisko"] != ""].copy()

    # kolejność ważnych kolumn na początku
    pozostale = [c for c in df.columns if c not in WYMAGANE_KOLUMNY + KOLUMNY_STRZALOW]
    return df[WYMAGANE_KOLUMNY + KOLUMNY_STRZALOW + pozostale]


def pobierz_liste_z_google(link: str) -> pd.DataFrame:
    csv_url = google_link_do_csv_url(link)
    df = pd.read_csv(csv_url, dtype=str)
    return normalizuj_naglowki(df)


def czy_ma_wynik(wartosc) -> bool:
    txt = str(wartosc).strip().lower()
    return txt not in ["", "nan", "none"]


def wykryj_typ_zawodnika(df: pd.DataFrame, nazwisko: str, idx) -> str:
    typ = str(df.at[idx, "Typ"]).strip()

    if typ in ["Standard", "PK"]:
        return typ

    indeksy = df[df["Nazwisko"] == nazwisko].index.tolist()
    pozycja = indeksy.index(idx) if idx in indeksy else 0

    return "Standard" if pozycja == 0 else "PK"


def zbuduj_ranking(df_input: pd.DataFrame, typ: str) -> pd.DataFrame:
    kolumny = [
        "Miejsce",
        "Nazwisko i Imię",
        "Typ startu",
        "Grupa / Zmiana",
        "Suma Trafień (Wynik)",
        "Trafienia z 1. Strzału",
    ]

    if df_input.empty:
        return pd.DataFrame(columns=kolumny)

    df = normalizuj_naglowki(df_input)

    df["Suma_num"] = pd.to_numeric(df["Suma trafień"], errors="coerce")
    df["Pierwszy_num"] = pd.to_numeric(df["Ile za pierwszym"], errors="coerce").fillna(0)

    df = df[
        (df["Typ"] == typ)
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
        "Typ startu": df["Typ"].values,
        "Grupa / Zmiana": df["Zmiana"].values,
        "Suma Trafień (Wynik)": df["Suma_num"].astype(int).values,
        "Trafienia z 1. Strzału": df["Pierwszy_num"].astype(int).values,
    })


def zapisz_excel(df: pd.DataFrame, path: Path) -> None:
    df = normalizuj_naglowki(df)

    ranking_standard = zbuduj_ranking(df, "Standard")
    ranking_pk = zbuduj_ranking(df, "PK")

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=ARKUSZ_WYNIKI, index=False)
        ranking_standard.to_excel(writer, sheet_name=ARKUSZ_REZULTATY, index=False)
        ranking_pk.to_excel(writer, sheet_name=ARKUSZ_REZULTATY_PK, index=False)


def wczytaj_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=WYMAGANE_KOLUMNY + KOLUMNY_STRZALOW)

    try:
        df = pd.read_excel(path, sheet_name=ARKUSZ_WYNIKI, dtype=str)
    except Exception:
        df = pd.read_excel(path, sheet_name=0, dtype=str)

    return normalizuj_naglowki(df)


def aktywny_path() -> Path | None:
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


def statusy_zawodnika(df: pd.DataFrame, nazwisko: str) -> tuple[bool, bool]:
    wiersze = df[df["Nazwisko"] == nazwisko]
    standard_zrobiony = False
    pk_zrobiony = False

    for idx in wiersze.index:
        typ = wykryj_typ_zawodnika(df, nazwisko, idx)
        suma = df.at[idx, "Suma trafień"]

        if typ == "Standard" and czy_ma_wynik(suma):
            standard_zrobiony = True
        if typ == "PK" and czy_ma_wynik(suma):
            pk_zrobiony = True

    return standard_zrobiony, pk_zrobiony



def zbuduj_liste_dostepnych(df: pd.DataFrame) -> list[dict]:
    wynik = []

    for nazwisko in sorted(df["Nazwisko"].dropna().astype(str).str.strip().unique()):
        if not nazwisko:
            continue

        wiersze = df[df["Nazwisko"] == nazwisko].index.tolist()

        for idx in wiersze:
            typ = wykryj_typ_zawodnika(df, nazwisko, idx)
            suma = df.at[idx, "Suma trafień"]

            if czy_ma_wynik(suma):
                continue

            if typ == "Standard":
                wyswietl = nazwisko
            else:
                wyswietl = f"{nazwisko} [PK]"

            wynik.append({
                "wyswietl": wyswietl,
                "nazwisko": nazwisko,
                "typ": typ,
            })

    return wynik




def zapisz_pusty_start_zmiany(path: Path) -> None:
    """
    Od razu po rozpoczęciu zmiany rezerwuje w aktywnym Excelu informację,
    kto strzela w tej zmianie. Dzięki temu plik zawodów od razu jest bazą roboczą.
    """
    df = wczytaj_excel(path)

    for kolejnosc, zaw in enumerate(st.session_state.wybrani_zawodnicy, start=1):
        nazwisko = zaw["nazwisko"]
        typ = zaw["typ"]

        maska = (
            (df["Nazwisko"] == nazwisko)
            & (df["Typ"] == typ)
            & (df["Zmiana"] == st.session_state.nazwa_zmiany)
        )

        if maska.any():
            continue

        indeksy = df[df["Nazwisko"] == nazwisko].index.tolist()
        pusty_idx = None

        for idx in indeksy:
            typ_wiersza = wykryj_typ_zawodnika(df, nazwisko, idx)
            if typ_wiersza == typ and not czy_ma_wynik(df.at[idx, "Suma trafień"]):
                pusty_idx = idx
                break

        if pusty_idx is not None:
            df.at[pusty_idx, "Zmiana"] = st.session_state.nazwa_zmiany
            df.at[pusty_idx, "Typ"] = typ
            df.at[pusty_idx, "Status"] = "W TRAKCIE"
            df.at[pusty_idx, KOLUMNA_KOLEJNOSC] = str(kolejnosc)
            df.at[pusty_idx, KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
        else:
            nowy = {col: "" for col in WYMAGANE_KOLUMNY + KOLUMNY_STRZALOW}
            nowy["Nazwisko"] = nazwisko
            nowy["Zmiana"] = st.session_state.nazwa_zmiany
            nowy["Typ"] = typ
            nowy["Status"] = "W TRAKCIE"
            nowy[KOLUMNA_KOLEJNOSC] = str(kolejnosc)
            nowy[KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)

    zapisz_excel(df, path)


def zapisz_robocze_strzaly_zmiany(path: Path) -> None:
    """
    Awaryjny zapis po każdym kliknięciu podczas strzelania.
    Zapisuje aktualnie wpisane strzały do aktywnego Excela jako W TRAKCIE,
    ale nie wpisuje jeszcze sumy końcowej, żeby niedokończona zmiana nie weszła do rankingu.
    """
    if not st.session_state.get("wybrani_zawodnicy"):
        return

    df = wczytaj_excel(path)

    for kolejnosc, zaw in enumerate(st.session_state.wybrani_zawodnicy, start=1):
        nazwisko = zaw["nazwisko"]
        typ = zaw["typ"]
        id_u = zaw["id_unikalne"]
        strzaly = st.session_state.macierz_wynikow.get(id_u, [])

        maska = (
            (df["Nazwisko"] == nazwisko)
            & (df["Typ"] == typ)
            & (df["Zmiana"] == st.session_state.nazwa_zmiany)
        )

        if maska.any():
            idx = df[maska].index[0]
        else:
            nowy = {col: "" for col in WYMAGANE_KOLUMNY + KOLUMNY_STRZALOW}
            nowy["Nazwisko"] = nazwisko
            nowy["Zmiana"] = st.session_state.nazwa_zmiany
            nowy["Typ"] = typ
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
        typ = zaw["typ"]
        id_u = zaw["id_unikalne"]

        strzaly = st.session_state.macierz_wynikow.get(id_u, [])
        suma = str(sum(1 for s in strzaly if s in ["/", "X"]))
        pierwszy = str(sum(1 for s in strzaly if s == "/"))

        maska = (
            (df["Nazwisko"] == nazwisko)
            & (df["Typ"] == typ)
            & (df["Zmiana"] == st.session_state.nazwa_zmiany)
        )

        if maska.any():
            idx = df[maska].index[0]
        else:
            nowy = {col: "" for col in WYMAGANE_KOLUMNY + KOLUMNY_STRZALOW}
            nowy["Nazwisko"] = nazwisko
            nowy["Zmiana"] = st.session_state.nazwa_zmiany
            nowy["Typ"] = typ
            nowy[KOLUMNA_KOLEJNOSC] = str(kolejnosc)
            nowy[KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
            idx = df.index[-1]

        df.at[idx, "Status"] = "STANDARD ZAKOŃCZONY" if typ == "Standard" else "PK ZAKOŃCZONE"
        df.at[idx, KOLUMNA_KOLEJNOSC] = str(kolejnosc)
        df.at[idx, KOLUMNA_LIMIT] = str(st.session_state.limit_rzutkow)
        df.at[idx, "Suma trafień"] = suma
        df.at[idx, "Ile za pierwszym"] = pierwszy

        for i in range(1, MAX_RZUTKOW + 1):
            col = f"Strzał_{i}"
            df.at[idx, col] = strzaly[i - 1] if i <= len(strzaly) else ""

    zapisz_excel(df, path)


def znajdz_przerwana_zmiane(df_input: pd.DataFrame) -> dict | None:
    """
    Szuka w aktywnym Excelu zmiany oznaczonej jako W TRAKCIE.
    Zwraca dane potrzebne do pokazania przycisku wznowienia.
    """
    if df_input.empty or "Status" not in df_input.columns or "Zmiana" not in df_input.columns:
        return None

    df = normalizuj_naglowki(df_input)
    robocze = df[df["Status"].str.upper().str.strip() == "W TRAKCIE"].copy()

    if robocze.empty:
        return None

    # Bierzemy ostatnią/najnowszą zmianę z pliku. Przy normalnej pracy będzie tylko jedna.
    nazwy_zmian = [z for z in robocze["Zmiana"].dropna().astype(str).unique() if z.strip()]
    if not nazwy_zmian:
        return None

    nazwa_zmiany = nazwy_zmian[-1]
    robocze = robocze[robocze["Zmiana"].astype(str) == nazwa_zmiany].copy()

    limit_series = pd.to_numeric(robocze.get(KOLUMNA_LIMIT, pd.Series(dtype=str)), errors="coerce").dropna()
    if not limit_series.empty:
        limit = int(limit_series.iloc[0])
    else:
        # Awaryjnie dla starszych kopii, które nie mają jeszcze kolumny Limit rzutków.
        ostatni_zapisany = 0
        for i in range(1, MAX_RZUTKOW + 1):
            col = f"Strzał_{i}"
            if col in robocze.columns:
                ma_dane = robocze[col].astype(str).str.strip().replace({"nan": "", "None": ""})
                if ma_dane.apply(lambda x: x not in ["", "-"]).any():
                    ostatni_zapisany = i
        limit = max(20, ostatni_zapisany)
        limit = min(limit, MAX_RZUTKOW)

    return {
        "nazwa_zmiany": nazwa_zmiany,
        "liczba_zawodnikow": len(robocze),
        "limit": limit,
    }


def wznow_przerwana_zmiane(path: Path, nazwa_zmiany: str | None = None) -> bool:
    """
    Odbudowuje session_state z Excela po resecie Streamlit.
    Przywraca listę zawodników, macierz strzałów i następne pole do wpisania.
    """
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
        limit = max(20, ostatni_zapisany)
        limit = min(limit, MAX_RZUTKOW)

    wybrani = []
    macierz = {}

    for _, row in robocze.iterrows():
        nazwisko = str(row.get("Nazwisko", "")).strip().upper()
        typ = str(row.get("Typ", "Standard")).strip() or "Standard"
        id_unikalne = f"{nazwisko} [PK]" if typ == "PK" else nazwisko

        if not nazwisko:
            continue

        wybrani.append({
            "nazwisko": nazwisko,
            "id_unikalne": id_unikalne,
            "typ": typ,
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
    st.session_state.nazwa_zmiany = str(nazwa_zmiany)
    st.session_state.zapisano_zmiane = ""
    st.session_state.kopia_pobrana = False

    return True

def zakoncz_i_wroc_do_menu():
    st.session_state.tryb_pracy = "MENU"
    st.session_state.wybrani_zawodnicy = []
    st.session_state.macierz_wynikow = {}
    st.session_state.aktualny_strzal = 0
    st.session_state.aktualny_zawodnik_idx = 0
    st.session_state.zapisano_zmiane = ""


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
    "nazwa_zmiany": "",
    "reset_wyszukiwarki": 0,
    "kopia_pobrana": False,
    "ostatnio_przywrocony_upload": "",
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

    # ------------------------------------------------------------
    # KODY LIST KLUBOWYCH
    # ------------------------------------------------------------
    # To są wygodne skróty dla sędziów.
    # Nie jest to zabezpieczenie, tylko prosty sposób, żeby nie wpisywać długiego linku.
    KODY_LIST = {
        "snajper": "https://docs.google.com/spreadsheets/d/1I8OGAXZEDWY3wgP_hKaepQF390BCUwxMBOrcPDJmlhA/edit?gid=0#gid=0",
    }

    kod_listy = st.sidebar.text_input(
        "Kod listy klubowej:",
        placeholder="np. Ala ma kota a kot ma strzelbę ;)",
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
                if kod_listy not in KODY_LIST:
                    st.sidebar.error("Nieznany kod listy klubowej.")
                    st.stop()

                link_do_pobrania = KODY_LIST[kod_listy]

            elif uzyj_wlasnego_linku:
                if not wlasny_link:
                    st.sidebar.error("Wklej własny link Google Sheets.")
                    st.stop()

                link_do_pobrania = wlasny_link

            else:
                st.sidebar.error("Wpisz kod listy klubowej albo zaznacz własny link.")
                st.stop()

            df_google = pobierz_liste_z_google(link_do_pobrania)
            nowy_plik = nazwa_nowego_pliku()
            zapisz_excel(df_google, nowy_plik)

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
                # Jeżeli nazwa pliku nie jest zgodna ze schematem aplikacji,
                # nadajemy bezpieczną nazwę, żeby plik pojawił się na liście zawodów.
                if upload_backup.name.startswith("trap20_zawody_") and upload_backup.name.endswith(".xlsx"):
                    backup_name = upload_backup.name
                else:
                    znacznik = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_name = f"trap20_zawody_przywrocony_{znacznik}.xlsx"

                backup_path = DATA_DIR / backup_name
                backup_path.write_bytes(upload_backup.getbuffer())

                # Próba odczytu od razu waliduje, czy to jest poprawny plik Excel dla programu.
                df_backup = wczytaj_excel(backup_path)
                zapisz_excel(df_backup, backup_path)

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

    if pliki:
        nazwy = [p.name for p in pliki]

        aktualny = aktywny_path()
        aktualna_nazwa = aktualny.name if aktualny else nazwy[0]
        index = nazwy.index(aktualna_nazwa) if aktualna_nazwa in nazwy else 0

        wybor_pliku = st.sidebar.selectbox(
            "Aktywny plik zawodów:",
            nazwy,
            index=index,
        )

        wybrany_path = DATA_DIR / wybor_pliku

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

        if st.sidebar.button("🗑️ Usuń aktywny plik zawodów", use_container_width=True):
            try:
                if wybrany_path.exists():
                    wybrany_path.unlink()

                st.session_state.aktywny_plik = ""
                zakoncz_i_wroc_do_menu()

                st.sidebar.success("Usunięto aktywny plik zawodów.")
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"Nie udało się usunąć pliku: {e}")
    else:
        st.sidebar.warning("Brak pliku zawodów. Pobierz listę z Google.")


# ============================================================
# GŁÓWNY WIDOK
# ============================================================

path = aktywny_path()

if path is None:
    st.warning("Najpierw pobierz listę z Google i utwórz plik zawodów.")
    st.stop()

df_baza = wczytaj_excel(path)


def pokaz_info_o_pliku_na_dole(path: Path) -> None:
    st.markdown(
        f"""
<div class="file-info-footer">
    <div>Google służy tylko do pobrania listy. Cała praca odbywa się na aktywnym pliku Excel zawodów.</div>
    <div style="margin-top: 6px;">Aktywny plik: <code>{path.name}</code></div>
</div>
""",
        unsafe_allow_html=True,
    )


def html_strzaly_dla_podgladu(row: pd.Series) -> str:
    html = ""
    for i in range(1, MAX_RZUTKOW + 1):
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

    tab1, tab2, tab3 = st.tabs(["🏆 Ranking Standard", "🎯 Ranking PK", "🔎 Sprawdź zawodnika"])

    with tab1:
        st.dataframe(zbuduj_ranking(df, "Standard"), use_container_width=True, hide_index=True)

    with tab2:
        st.dataframe(zbuduj_ranking(df, "PK"), use_container_width=True, hide_index=True)

    with tab3:
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
            for _, row in df_pokaz.sort_values(["Nazwisko", "Typ", "Zmiana"]).iterrows():
                suma = str(row.get("Suma trafień", "")).strip() or "0"
                pierwszy = str(row.get("Ile za pierwszym", "")).strip() or "0"
                st.markdown(
                    f"""
<div class="player-row">
    <div class="player-stand">{row.get('Zmiana', '')}</div>
    <div>
        <div class="player-name">{row.get('Nazwisko', '')}</div>
        <div class="player-type">{row.get('Typ', '')}</div>
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
    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        nr_zmiany = st.number_input(
            "Numer zmiany:",
            min_value=1,
            value=kolejny_numer_zmiany(df_baza),
            step=1,
        )

    with col_m2:
        limit_rzutkow = st.selectbox("Liczba rzutków:", [10, 15, 20, 25], index=2)

    with col_m3:
        st.metric("Zawodnicy w pliku", df_baza["Nazwisko"].nunique())

    przerwana = znajdz_przerwana_zmiane(df_baza)
    if przerwana and not st.session_state.get("wybrani_zawodnicy"):
        st.warning(
            f"Wykryto przerwaną zmianę: {przerwana['nazwa_zmiany']} "
            f"({przerwana['liczba_zawodnikow']} zawodników, {przerwana['limit']} rzutków)."
        )
        if st.button("▶️ Wznów przerwaną zmianę", type="primary", use_container_width=True):
            if wznow_przerwana_zmiane(path, przerwana["nazwa_zmiany"]):
                st.rerun()
            else:
                st.error("Nie udało się wznowić przerwanej zmiany z aktywnego pliku.")

    st.markdown("---")
    st.subheader("📋 Skład zmiany")

    dostepni = zbuduj_liste_dostepnych(df_baza)

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

    col1, col2, col3 = st.columns([4, 3, 2])

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

    with col3:
        typ_reczny = st.selectbox(
            "Typ:",
            ["Standard", "PK"],
            key="typ_reczny",
        )

    if st.button("➕ Dodaj zawodnika", type="primary"):
        if len(st.session_state.wybrani_zawodnicy) >= 6:
            st.error("W jednej zmianie może być maksymalnie 6 zawodników.")
        else:
            nazwisko = ""
            typ = ""

            if wybor and wybor.strip():
                obj = next((z for z in dostepni if z["wyswietl"] == wybor), None)

                if obj:
                    nazwisko = obj["nazwisko"]
                    typ = obj["typ"]

            elif reczny:
                nazwisko = reczny
                typ = typ_reczny

            if not nazwisko:
                st.error("Wybierz zawodnika albo wpisz nazwisko ręcznie.")
            else:
                standard_zrobiony, pk_zrobiony = statusy_zawodnika(df_baza, nazwisko)

                if typ == "Standard" and standard_zrobiony:
                    st.error(f"{nazwisko} ma już wynik Standard. Może startować tylko jako PK.")

                elif typ == "PK" and not standard_zrobiony:
                    st.error(f"{nazwisko} nie ma jeszcze wyniku Standard. PK jest możliwe dopiero po Standardzie.")

                elif typ == "PK" and pk_zrobiony:
                    st.error(f"{nazwisko} ma już zapisany wynik PK.")

                else:
                    id_unikalne = f"{nazwisko} [PK]" if typ == "PK" else nazwisko

                    if id_unikalne in juz_dodani:
                        st.error("Ten zawodnik jest już dodany do tej zmiany.")
                    else:
                        st.session_state.wybrani_zawodnicy.append({
                            "nazwisko": nazwisko,
                            "id_unikalne": id_unikalne,
                            "typ": typ,
                        })

                        # Po dodaniu zawodnika czyścimy wyszukiwarkę i wybór z listy.
                        st.session_state.reset_wyszukiwarki = int(st.session_state.get("reset_wyszukiwarki", 0)) + 1

                        st.rerun()

    if st.session_state.wybrani_zawodnicy:
        st.markdown("#### Wybrani zawodnicy")

        for i, z in enumerate(st.session_state.wybrani_zawodnicy):
            c1, c2, c3 = st.columns([1, 5, 1])

            with c1:
                st.write(f"**S {i + 1}**")

            with c2:
                st.info(f"{z['id_unikalne']} — {z['typ']}")

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

    tab1, tab2, tab3 = st.tabs(["🏆 Standard", "🎯 PK", "📄 Wyniki szczegółowe"])

    with tab1:
        st.dataframe(zbuduj_ranking(df_baza, "Standard"), use_container_width=True, hide_index=True)

    with tab2:
        st.dataframe(zbuduj_ranking(df_baza, "PK"), use_container_width=True, hide_index=True)

    with tab3:
        st.dataframe(df_baza, use_container_width=True, hide_index=True)

    pokaz_info_o_pliku_na_dole(path)


# ============================================================
# STRZELANIE
# ============================================================

elif st.session_state.tryb_pracy == "STRZELANIE":
    limit = int(st.session_state.limit_rzutkow)

    st.subheader(f"🏟️ {st.session_state.nazwa_zmiany} — {limit} rzutków")

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
        <div class="player-type">{z["typ"]}</div>
    </div>
    <div class="player-shots">{html}</div>
    <div class="player-sum">{suma} / {pierwszy}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    def rejestruj(symbol: str):
        # twarda blokada przed kliknięciami po limicie
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

        # Awaryjny zapis bieżących strzałów po każdym kliknięciu.
        # Chroni przed zwykłym odświeżeniem/resetem sesji Streamlit w trakcie zmiany.
        try:
            zapisz_robocze_strzaly_zmiany(path)
        except Exception as e:
            st.session_state["blad_autozapisu"] = str(e)

    if st.session_state.aktualny_strzal >= limit:
        st.success("🔥 Zmiana zakończona.")

        # zapisujemy wyniki automatycznie po wejściu w stan zakończenia
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
