import datetime
import re
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

# ==================================================
# KONFIGURACJA
# ==================================================
st.set_page_config(
    page_title="System Punktacji TRAP20", page_icon="🎯", layout="wide"
)

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

WYMAGANE_KOLUMNY = [
    "Nazwisko",
    "Zmiana",
    "Typ",
    "Status",
    "Suma trafień",
    "Ile za pierwszym",
]

KOLORY = {
    "/": "shot-t1",
    "X": "shot-t2",
    "O": "shot-miss",
    "-": "shot-blank",
}


# ==================================================
# CSS
# ==================================================
st.markdown(
    """
<style>
    .main-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 4px;
    }
    .subtle {
        color: #64748b;
        font-size: 14px;
        margin-bottom: 16px;
    }
    .shot-box {
        display: inline-block;
        width: 34px;
        height: 34px;
        line-height: 34px;
        text-align: center;
        margin: 2px;
        border-radius: 7px;
        font-weight: 800;
        color: white;
        border: 1px solid #cbd5e1;
        font-size: 16px;
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
        outline: 4px solid #facc15;
        outline-offset: 1px;
    }
    .current-player {
        background: #fef9c3;
        border: 2px solid #eab308;
        padding: 18px;
        border-radius: 12px;
        margin: 12px 0 16px 0;
    }
    .card {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
        background: #ffffff;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ==================================================
# FUNKCJE POMOCNICZE I PLIKOWE
# ==================================================
def generuj_nowa_nazwe_pliku() -> Path:
    """Tworzy unikalną nazwę pliku na podstawie aktualnej daty i godziny."""
    teraz = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / f"baza_trap_{teraz}.xlsx"


def pobierz_liste_plikow_excel() -> list[str]:
    """Zwraca listę dostępnych plików baz danych w katalogu data."""
    pliki = sorted(DATA_DIR.glob("baza_trap_*.xlsx"), reverse=True)
    return [p.name for p in pliki]


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
        c = col.lower()
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

    for i in range(1, 26):
        col = f"Strzał_{i}"
        if col not in df.columns:
            df[col] = ""

    df["Nazwisko"] = (
        df["Nazwisko"].fillna("").astype(str).str.strip().str.upper()
    )
    df["Zmiana"] = df["Zmiana"].fillna("").astype(str).str.strip()
    df["Typ"] = df["Typ"].fillna("").astype(str).str.strip()
    df["Status"] = df["Status"].fillna("").astype(str).str.strip()
    df["Suma trafień"] = df["Suma trafień"].fillna("").astype(str).str.strip()
    df["Ile za pierwszym"] = (
        df["Ile za pierwszym"].fillna("").astype(str).str.strip()
    )

    df = df[df["Nazwisko"] != ""].copy()
    return df


def pobierz_liste_z_google(link: str) -> pd.DataFrame:
    csv_url = google_link_do_csv_url(link)
    df = pd.read_csv(csv_url)
    return normalizuj_naglowki(df)


def zapisz_excel_lokalny(df: pd.DataFrame, path: Path) -> None:
    df = normalizuj_naglowki(df)
    tabela_standard = zbuduj_ranking(df, "Standard")
    tabela_pk = zbuduj_ranking(df, "PK")

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Wyniki Szczegółowe", index=False)
        tabela_standard.to_excel(writer, sheet_name="Rezultaty", index=False)
        tabela_pk.to_excel(writer, sheet_name="Rezultaty PK", index=False)


def wczytaj_excel_lokalny(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        return pd.DataFrame(columns=WYMAGANE_KOLUMNY)

    try:
        df = pd.read_excel(path, sheet_name="Wyniki Szczegółowe")
    except Exception:
        df = pd.read_excel(path, sheet_name=0)

    return normalizuj_naglowki(df)


# ==================================================
# LOGIKA STATUSÓW I RANKINGÓW
# ==================================================
def czy_ma_wynik(wartosc) -> bool:
    txt = str(wartosc).strip().lower()
    return txt not in ["", "nan", "none"]


def wykryj_typ_zawodnika(df: pd.DataFrame, nazwisko: str, idx: int) -> str:
    typ = str(df.at[idx, "Typ"]).strip()
    if typ in ["Standard", "PK"]:
        return typ

    indeksy = df[df["Nazwisko"] == nazwisko].index.tolist()
    pozycja = indeksy.index(idx) if idx in indeksy else 0
    return "Standard" if pozycja == 0 else "PK"


def zbuduj_liste_dostepnych(df: pd.DataFrame) -> list[dict]:
    dostepni = []
    for nazwisko in sorted(
        df["Nazwisko"].dropna().astype(str).str.strip().unique()
    ):
        if not nazwisko:
            continue

        wiersze = df[df["Nazwisko"] == nazwisko]
        standard_zrobiony, pk_zrobiony = False, False
        standard_wolny, pk_wolny = False, False

        for idx in wiersze.index:
            typ = wykryj_typ_zawodnika(df, nazwisko, idx)
            suma = df.at[idx, "Suma trafień"]
            ma_wynik = czy_ma_wynik(suma)

            if typ == "Standard":
                if ma_wynik:
                    standard_zrobiony = True
                else:
                    standard_wolny = True
            if typ == "PK":
                if ma_wynik:
                    pk_zrobiony = True
                else:
                    pk_wolny = True

        if standard_wolny and not standard_zrobiony:
            dostepni.append(
                {"wyswietl": nazwisko, "nazwisko": nazwisko, "typ": "Standard"}
            )
        if standard_zrobiony and pk_wolny and not pk_zrobiony:
            dostepni.append(
                {
                    "wyswietl": f"{nazwisko} [PK]",
                    "nazwisko": nazwisko,
                    "typ": "PK",
                }
            )
    return dostepni


def zbuduj_ranking(df_input: pd.DataFrame, typ: str) -> pd.DataFrame:
    kolumny_wyjsciowe = [
        "Miejsce",
        "Nazwisko i Imię",
        "Typ startu",
        "Grupa / Zmiana",
        "Suma Trafień (Wynik)",
        "Trafienia z 1. Strzału",
    ]
    if df_input.empty:
        return pd.DataFrame(columns=kolumny_wyjsciowe)

    df = normalizuj_naglowki(df_input)
    df["Suma trafień num"] = pd.to_numeric(df["Suma trafień"], errors="coerce")
    df["Ile za pierwszym num"] = (
        pd.to_numeric(df["Ile za pierwszym"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    df = df[
        (df["Typ"] == typ)
        & (df["Suma trafień num"].notna())
        & (df["Zmiana"].astype(str).str.strip() != "")
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=kolumny_wyjsciowe)

    df = df.sort_values(
        by=["Suma trafień num", "Ile za pierwszym num", "Nazwisko"],
        ascending=[False, False, True],
    )

    miejsca = []
    poprzedni_wynik = None
    poprzedni_pierwszy = None

    for i, (_, row) in enumerate(df.iterrows()):
        wynik = row["Suma trafień num"]
        pierwszy = row["Ile za pierwszym num"]

        if i == 0:
            miejsce = 1
        elif wynik == poprzedni_wynik and pierwszy == poprzedni_pierwszy:
            miejsce = miejsca[-1]
        else:
            miejsce = i + 1

        miejsca.append(miejsce)
        poprzedni_wynik = wynik
        poprzedni_pierwszy = pierwszy

    return pd.DataFrame(
        {
            "Miejsce": miejsca,
            "Nazwisko i Imię": df["Nazwisko"].values,
            "Typ startu": df["Typ"].values,
            "Grupa / Zmiana": df["Zmiana"].values,
            "Suma Trafień (Wynik)": df["Suma trafień num"].astype(int).values,
            "Trafienia z 1. Strzału": df["Ile za pierwszym num"].values,
        }
    )


def kolejny_numer_zmiany(df: pd.DataFrame) -> int:
    max_nr = 0
    if "Zmiana" not in df.columns:
        return 1

    for zm in df["Zmiana"].dropna().astype(str):
        if "Zmiana" in zm:
            try:
                nr = int(zm.replace("Zmiana", "").strip())
                max_nr = max(max_nr, nr)
            except ValueError:
                pass
    return max_nr + 1


def zapisz_wyniki_zmiany_do_df(df_baza: pd.DataFrame) -> pd.DataFrame:
    df = normalizuj_naglowki(df_baza)
    limit = st.session_state.limit_rzutkow

    for i in range(1, limit + 1):
        col = f"Strzał_{i}"
        if col not in df.columns:
            df[col] = ""

    for zaw in st.session_state.wybrani_zawodnicy:
        nazwisko = zaw["nazwisko"].upper()
        typ_startu = zaw["typ"]
        id_u = zaw["id_unikalne"]
        strzaly = st.session_state.macierz_wynikow[id_u]

        suma_laczna = sum(1 for s in strzaly if s in ["/", "X"])
        suma_pierwszy = sum(1 for s in strzaly if s == "/")

        indeksy = df[df["Nazwisko"] == nazwisko].index.tolist()
        wybrany_idx = None

        for idx in indeksy:
            obecny_typ = wykryj_typ_zawodnika(df, nazwisko, idx)
            obecna_zmiana = str(df.at[idx, "Zmiana"]).strip()
            obecna_suma = str(df.at[idx, "Suma trafień"]).strip().lower()

            pusty_wiersz = obecna_zmiana in ["", "nan", "none"] or obecna_suma in [
                "",
                "nan",
                "none",
            ]

            if pusty_wiersz and obecny_typ == typ_startu:
                wybrany_idx = idx
                break

        if wybrany_idx is None:
            nowy = {
                "Nazwisko": nazwisko,
                "Zmiana": st.session_state.nazwa_zmiany,
                "Typ": typ_startu,
                "Status": (
                    "ZAKOŃCZONY" if typ_startu == "Standard" else "PK ZAKOŃCZONE"
                ),
                "Suma trafień": int(suma_laczna),
                "Ile za pierwszym": int(suma_pierwszy),
            }
            for i, sym in enumerate(strzaly, start=1):
                nowy[f"Strzał_{i}"] = sym
            df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
        else:
            df.at[wybrany_idx, "Zmiana"] = st.session_state.nazwa_zmiany
            df.at[wybrany_idx, "Typ"] = typ_startu
            df.at[wybrany_idx, "Status"] = (
                "ZAKOŃCZONY" if typ_startu == "Standard" else "PK ZAKOŃCZONE"
            )
            df.at[wybrany_idx, "Suma trafień"] = int(suma_laczna)
            df.at[wybrany_idx, "Ile za pierwszym"] = int(suma_pierwszy)

            for i, sym in enumerate(strzaly, start=1):
                df.at[wybrany_idx, f"Strzał_{i}"] = sym

    return normalizuj_naglowki(df)


# ==================================================
# SESSION STATE
# ==================================================
def init_state():
    defaults = {
        "tryb_pracy": "MENU_START",
        "wybrani_zawodnicy": [],
        "aktualny_strzal": 0,
        "aktualny_zawodnik_idx": 0,
        "macierz_wynikow": {},
        "limit_rzutkow": 20,
        "nazwa_zmiany": "",
        "google_link": "",
        "wybrany_plik_nazwa": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

# ==================================================
# SIDEBAR — ZARZĄDZANIE PLIKAMI BAZ
# ==================================================
st.sidebar.header("📁 Zarządzanie zawodami")

# Wybór aktywnego pliku z listy
dostepne_pliki = pobierz_liste_plikow_excel()

if dostepne_pliki:
    if (
        not st.session_state.wybrany_plik_nazwa
        or st.session_state.wybrany_plik_nazwa not in dostepne_pliki
    ):
        st.session_state.wybrany_plik_nazwa = dostepne_pliki[0]

    wybrany_plik = st.sidebar.selectbox(
        "Wybierz aktywny plik zawodów:",
        dostepne_pliki,
        index=dostepne_pliki.index(st.session_state.wybrany_plik_nazwa),
    )
    if wybrany_plik != st.session_state.wybrany_plik_nazwa:
        st.session_state.wybrany_plik_nazwa = wybrany_plik
        st.rerun()

    AKTYWNY_EXCEL_PATH = DATA_DIR / st.session_state.wybrany_plik_nazwa
else:
    AKTYWNY_EXCEL_PATH = None
    st.sidebar.warning("Brak plików zawodów w katalogu. Utwórz nowy poniżej.")

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Utwórz nowe zawody")

st.session_state.google_link = st.sidebar.text_input(
    "Publiczny link Google Sheets:",
    value=st.session_state.google_link,
    placeholder="https://docs.google.com/spreadsheets/d/...",
)

col_sb1, col_sb2 = st.sidebar.columns(2)

with col_sb1:
    if st.button("Pobierz z Google", use_container_width=True):
        if not st.session_state.google_link.strip():
            st.sidebar.error("Wklej link do arkusza Google.")
        else:
            try:
                df_google = pobierz_liste_z_google(st.session_state.google_link)
                nowy_plik = generuj_nowa_nazwe_pliku()
                zapisz_excel_lokalny(df_google, nowy_plik)

                st.session_state.wybrany_plik_nazwa = nowy_plik.name
                st.session_state.wybrani_zawodnicy = []
                st.session_state.tryb_pracy = "MENU_START"
                st.sidebar.success(f"Utworzono plik: {nowy_plik.name}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Błąd pobierania: {e}")

with col_sb2:
    if st.button("🔄 Odśwież listę", use_container_width=True):
        st.rerun()

uploaded = st.sidebar.file_uploader(
    "Lub wgraj plik Excel jako nową bazę:", type=["xlsx"]
)
if uploaded is not None:
    try:
        df_upload = pd.read_excel(uploaded, sheet_name=0)
        nowy_plik = generuj_nowa_nazwe_pliku()
        zapisz_excel_lokalny(df_upload, nowy_plik)

        st.session_state.wybrany_plik_nazwa = nowy_plik.name
        st.sidebar.success(f"Wgrano jako: {nowy_plik.name}")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Nie udało się wczytać Excela: {e}")

if AKTYWNY_EXCEL_PATH and AKTYWNY_EXCEL_PATH.exists():
    st.sidebar.markdown("---")
    st.sidebar.download_button(
        "⬇️ Pobierz wybrany plik Excel",
        data=AKTYWNY_EXCEL_PATH.read_bytes(),
        file_name=st.session_state.wybrany_plik_nazwa,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


# ==================================================
# WIDOK GŁÓWNY
# ==================================================
st.markdown(
    '<div class="main-title">🎯 System Punktacji TRAP20</div>',
    unsafe_allow_html=True,
)
if AKTYWNY_EXCEL_PATH:
    st.markdown(
        f'<div class="subtle">Pracujesz na pliku: <b>{st.session_state.wybrany_plik_nazwa}</b></div>',
        unsafe_allow_html=True,
    )
else:
    st.warning(
        "Brak aktywnej bazy danych. Pobierz dane z Google Sheets lub wgraj plik Excel w panelu bocznym."
    )
    st.stop()

df_baza = wczytaj_excel_lokalny(AKTYWNY_EXCEL_PATH)


# ==================================================
# MENU STARTOWE
# ==================================================
if st.session_state.tryb_pracy == "MENU_START":
    col_cfg1, col_cfg2, col_cfg3 = st.columns([1, 1, 2])

    with col_cfg1:
        nr_zmiany = st.number_input(
            "Numer zmiany:",
            min_value=1,
            value=kolejny_numer_zmiany(df_baza),
            step=1,
        )

    with col_cfg2:
        limit_rzutkow = st.selectbox(
            "Liczba rzutków:", [10, 15, 20, 25], index=2
        )

    with col_cfg3:
        st.metric("Liczba zawodników w bazie", df_baza["Nazwisko"].nunique())

    st.markdown("---")
    st.subheader("📋 Budowanie składu zmiany")

    dostepni = zbuduj_liste_dostepnych(df_baza)
    juz_dodani = [z["id_unikalne"] for z in st.session_state.wybrani_zawodnicy]
    opcje = [z["wyswietl"] for z in dostepni if z["wyswietl"] not in juz_dodani]

    col1, col2, col3 = st.columns([3, 3, 2])

    with col1:
        wybor = st.selectbox("Wybierz zawodnika z bazy:", [""] + opcje)

    with col2:
        reczny = st.text_input("Lub dopisz ręcznie:").strip().upper()

    with col3:
        typ_reczny = st.selectbox("Typ startu:", ["Standard", "PK"])

    if st.button("➕ Dodaj do zmiany", type="primary"):
        if len(st.session_state.wybrani_zawodnicy) >= 6:
            st.error("W zmianie może być maksymalnie 6 zawodników.")
        else:
            nazwisko = ""
            typ = ""

            if wybor:
                obj = next(
                    (z for z in dostepni if z["wyswietl"] == wybor), None
                )
                if obj:
                    nazwisko = obj["nazwisko"]
                    typ = obj["typ"]
            elif reczny:
                nazwisko = reczny
                typ = typ_reczny

            if not nazwisko:
                st.error("Wybierz zawodnika albo wpisz nazwisko ręcznie.")
            else:
                id_unikalne = f"{nazwisko} [PK]" if typ == "PK" else nazwisko

                if id_unikalne in juz_dodani:
                    st.error("Ten zawodnik jest już dodany do tej zmiany.")
                else:
                    st.session_state.wybrani_zawodnicy.append(
                        {
                            "nazwisko": nazwisko,
                            "id_unikalne": id_unikalne,
                            "typ": typ,
                        }
                    )
                    st.rerun()

    if st.session_state.wybrani_zawodnicy:
        st.markdown("#### Aktualny skład zmiany")

        for i, z in enumerate(st.session_state.wybrani_zawodnicy):
            col_z1, col_z2, col_z3 = st.columns([1, 5, 1])

            with col_z1:
                st.write(f"**Stan. {i + 1}**")
            with col_z2:
                st.info(f"{z['id_unikalne']} — {z['typ']}")
            with col_z3:
                if st.button("Usuń", key=f"usun_{i}"):
                    st.session_state.wybrani_zawodnicy.pop(i)
                    st.rerun()

        if st.button("🧹 Wyczyść skład"):
            st.session_state.wybrani_zawodnicy = []
            st.rerun()

    st.markdown("---")

    if st.button(
        "🚀 ROZPOCZNIJ STRZELANIE", type="primary", use_container_width=True
    ):
        if not st.session_state.wybrani_zawodnicy:
            st.error("Nie można rozpocząć bez zawodników.")
        else:
            st.session_state.tryb_pracy = "OS_STRZELECKA"
            st.session_state.aktualny_strzal = 0
            st.session_state.aktualny_zawodnik_idx = 0
            st.session_state.limit_rzutkow = int(limit_rzutkow)
            st.session_state.nazwa_zmiany = f"Zmiana {nr_zmiany}"
            st.session_state.macierz_wynikow = {
                z["id_unikalne"]: ["-"] * int(limit_rzutkow)
                for z in st.session_state.wybrani_zawodnicy
            }
            st.rerun()

    st.markdown("---")
    st.subheader("📊 Aktualne rankingi")

    tab1, tab2, tab3 = st.tabs(["🏆 Standard", "🎯 PK", "📄 Dane szczegółowe"])

    with tab1:
        st.dataframe(
            zbuduj_ranking(df_baza, "Standard"),
            use_container_width=True,
            hide_index=True,
        )
    with tab2:
        st.dataframe(
            zbuduj_ranking(df_baza, "PK"),
            use_container_width=True,
            hide_index=True,
        )
    with tab3:
        st.dataframe(df_baza, use_container_width=True, hide_index=True)


# ==================================================
# EKRAN STRZELANIA
# ==================================================
elif st.session_state.tryb_pracy == "OS_STRZELECKA":
    st.subheader(
        f"🏟️ Karta konkurencji — {st.session_state.nazwa_zmiany} — {st.session_state.limit_rzutkow} rzutków"
    )

    for i, z in enumerate(st.session_state.wybrani_zawodnicy):
        id_u = z["id_unikalne"]
        strzaly = st.session_state.macierz_wynikow[id_u]

        suma_laczna = sum(1 for s in strzaly if s in ["/", "X"])
        suma_pierwszy = sum(1 for s in strzaly if s == "/")

        html = ""
        for s_idx, s in enumerate(strzaly):
            klasa = KOLORY.get(s, "shot-blank")

            pokaz_symbol = s
            if (
                st.session_state.aktualny_strzal
                < st.session_state.limit_rzutkow
                and s_idx == st.session_state.aktualny_strzal
                and i == st.session_state.aktualny_zawodnik_idx
            ):
                klasa += " current-target"
                if s == "-":
                    pokaz_symbol = "●"

            html += f'<span class="shot-box {klasa}">{pokaz_symbol}</span>'
            if (s_idx + 1) % 5 == 0:
                html += "&nbsp;&nbsp;"

        col_a, col_b, col_c = st.columns([1, 3, 6])
        with col_a:
            st.write(f"**Stan. {i + 1}**")
        with col_b:
            st.write(f"**{id_u}**")
            st.caption(z["typ"])
        with col_c:
            st.markdown(
                f"{html} &nbsp;&nbsp;&nbsp; **Suma: {suma_laczna} / {suma_pierwszy}**",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    def rejestruj(symbol: str):
        # 1. Zapisz symbol strzału w pamięci sesji
        id_u = st.session_state.wybrani_zawodnicy[
            st.session_state.aktualny_zawodnik_idx
        ]["id_unikalne"]
        st.session_state.macierz_wynikow[id_u][
            st.session_state.aktualny_strzal
        ] = symbol

        # 2. ZAPIS W CZASIE RZECZYWISTYM: Zrzucenie aktualnego stanu sesji prosto do pliku Excel
        try:
            df_aktualny = wczytaj_excel_lokalny(AKTYWNY_EXCEL_PATH)
            df_po_zapisie = zapisz_wyniki_zmiany_do_df(df_aktualny)
            zapisz_excel_lokalny(df_po_zapisie, AKTYWNY_EXCEL_PATH)
        except Exception as e:
            st.error(f"Błąd automatycznego zapisu strzału: {e}")

        # 3. Przesunięcie kolejki na następnego zawodnika / strzał
        st.session_state.aktualny_zawodnik_idx += 1
        if st.session_state.aktualny_zawodnik_idx >= len(
            st.session_state.wybrani_zawodnicy
        ):
            st.session_state.aktualny_zawodnik_idx = 0
            st.session_state.aktualny_strzal += 1

    if st.session_state.aktualny_strzal >= st.session_state.limit_rzutkow:
        st.success(
            "🔥 Zmiana zakończona! Wszystkie wyniki zostały bezpiecznie zapisane na bieżąco."
        )

        if st.button(
            "ZAKOŃCZ ZMIANĘ I WRÓĆ DO MENU",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.wybrani_zawodnicy = []
            st.session_state.macierz_wynikow = {}
            st.session_state.tryb_pracy = "MENU_START"
            st.rerun()
    else:
        aktualny = st.session_state.wybrani_zawodnicy[
            st.session_state.aktualny_zawodnik_idx
        ]

        st.markdown(
            f"""
<div class="current-player">
    <h3>📣 Bieżący strzał</h3>
    <b>Stanowisko {st.session_state.aktualny_zawodnik_idx + 1}</b>: 
    {aktualny["id_unikalne"]} 
    &nbsp; | &nbsp; 
    <b>Strzał {st.session_state.aktualny_strzal + 1}</b> z {st.session_state.limit_rzutkow}
</div>
""",
            unsafe_allow_html=True,
        )

        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            st.button(
                "🔵 Trafiony 1 ( / )",
                use_container_width=True,
                type="primary",
                on_click=rejestruj,
                args=("/",),
            )
        with col_b2:
            st.button(
                "🟢 Trafiony 2 ( X )",
                use_container_width=True,
                on_click=rejestruj,
                args=("X",),
            )
        with col_b3:
            st.button(
                "🔴 Pudło ( O )",
                use_container_width=True,
                on_click=rejestruj,
                args=("O",),
            )

    st.markdown("---")
    col_nav1, col_nav2 = st.columns([1, 1])

    with col_nav1:
        if st.button("⬅️ Anuluj i wróć do menu"):
            st.session_state.tryb_pracy = "MENU_START"
            st.session_state.wybrani_zawodnicy = []
            st.session_state.macierz_wynikow = {}
            st.rerun()

    with col_nav2:
        if (
            st.session_state.aktualny_strzal > 0
            or st.session_state.aktualny_zawodnik_idx > 0
        ):
            if st.button("↩️ Cofnij ostatni wpis"):
                # Cofnięcie indeksu
                if st.session_state.aktualny_zawodnik_idx == 0:
                    st.session_state.aktualny_strzal -= 1
                    st.session_state.aktualny_zawodnik_idx = (
                        len(st.session_state.wybrani_zawodnicy) - 1
                    )
                else:
                    st.session_state.aktualny_zawodnik_idx -= 1

                id_u = st.session_state.wybrani_zawodnicy[
                    st.session_state.aktualny_zawodnik_idx
                ]["id_unikalne"]
                st.session_state.macierz_wynikow[id_u][
                    st.session_state.aktualny_strzal
                ] = "-"

                # Nadpisanie cofniętego strzału w pliku Excel
                try:
                    df_aktualny = wczytaj_excel_lokalny(AKTYWNY_EXCEL_PATH)
                    df_po_zapisie = zapisz_wyniki_zmiany_do_df(df_aktualny)
                    zapisz_excel_lokalny(df_po_zapisie, AKTYWNY_EXCEL_PATH)
                except Exception as e:
                    st.error(f"Błąd zapisu przy cofaniu: {e}")

                st.rerun()
