import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Konfiguracja strony Streamlit
st.set_page_config(page_title="System Punktacji TRAP v7.6", layout="wide")

st.title("🎯 System Punktacji TRAP — Wersja Chmurowa v7.6")

# Piękna i czytelna siatka strzałów (Karta Strzelań)
st.markdown("""
<style>
    .shot-box {
        display: inline-block;
        width: 32px;
        height: 32px;
        line-height: 32px;
        text-align: center;
        margin: 2px;
        border-radius: 6px;
        font-weight: bold;
        color: white;
        border: 1px solid #ccc;
        font-size: 16px;
    }
    .shot-blank { background-color: #e5e7eb; color: #9ca3af; }
    .shot-t1 { background-color: #1e40af; }
    .shot-t2 { background-color: #15803d; }
    .shot-miss { background-color: #b91c1c; }
    .current-player { background-color: #fef08a; border: 2px solid #eab308; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .current-target { border: 2px solid #000000; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.5; } }
</style>
""", unsafe_allow_html=True)

# Inicjalizacja połączenia za pomocą Secrets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"❌ Problem z inicjalizacją połączenia Google Sheets. Sprawdź Secrets. Błąd: {e}")
    st.stop()

def pobierz_i_napraw_baze():
    try:
        # Pobranie danych przez oficjalny konektor (gwarantuje odświeżenie danych)
        df = conn.read(worksheet="Wyniki_Szczegolowe", ttl="0d")
        
        # Słownik auto-naprawy uciętych nagłówków z Excela
        mapa_kolumn = {
            'uma trafie': 'Suma trafień', 'Suma trafie': 'Suma trafień',
            'za pierwsz': 'Ile za pierwszym', 'Ile za pierwsz': 'Ile za pierwszym',
            'Nazwisko': 'Nazwisko', 'Zmiana': 'Zmiana', 'Typ': 'Typ'
        }
        
        nowe_nazwy = {}
        for col in df.columns:
            for klucz, wartosc in mapa_kolumn.items():
                if klucz in col:
                    nowe_nazwy[col] = wartosc
        df = df.rename(columns=nowe_nazwy)
        
        for wymagana in ["Nazwisko", "Zmiana", "Typ", "Suma trafień", "Ile za pierwszym"]:
            if wymagana not in df.columns:
                df[wymagana] = None
        return df
    except Exception as e:
        st.error(f"⚠️ Nie można odczytać arkusza 'Wyniki_Szczegolowe'. Upewnij się, że taka zakładka istnieje. Błąd: {e}")
        st.stop()

# Wczytanie bazy danych
df_baza = pobierz_i_napraw_baze()

if not df_baza.empty:
    df_baza["Nazwisko"] = df_baza["Nazwisko"].fillna("").astype(str).str.strip().str.upper()
    df_baza = df_baza[df_baza["Nazwisko"] != ""]

# --- FUNKCJE POMOCNICZE DO RANKINGU ---
def zbuduj_tabela_rankingu(df_input, typ_konkurencji):
    df = df_input.copy()
    df["Typ"] = df["Typ"].fillna("").astype(str).str.strip()
    df["Suma trafień"] = pd.to_numeric(df["Suma trafień"], errors='coerce')
    df["Ile za pierwszym"] = pd.to_numeric(df["Ile za pierwszym"], errors='coerce').fillna(0)
    df["Zmiana"] = df["Zmiana"].fillna("").astype(str).str.strip()
    
    df_filtrowany = df[
        (df["Typ"] == typ_konkurencji) & (df["Suma trafień"].notna()) & (df["Zmiana"] != "")
    ].copy()
    
    if df_filtrowany.empty:
        return pd.DataFrame(columns=["Miejsce", "Nazwisko i Imię", "Grupa / Zmiana", "Suma Trafień", "Z 1. Strzału"])
        
    df_filtrowany = df_filtrowany.sort_values(by=["Suma trafień", "Ile za pierwszym", "Nazwisko"], ascending=[False, False, True])
    
    miejsca = []
    poprzedni_wynik, poprzedni_pierwszy = None, None
    for idx, (_, row) in enumerate(df_filtrowany.iterrows()):
        w, p = row["Suma trafień"], row["Ile za pierwszym"]
        miejsce = 1 if idx == 0 else (miejsca[-1] if (w == poprzedni_wynik and p == poprzedni_pierwszy) else idx + 1)
        miejsca.append(miejsce)
        poprzedni_wynik, poprzedni_pierwszy = w, p
        
    return pd.DataFrame({
        "Miejsce": miejsca, "Nazwisko i Imię": df_filtrowany["Nazwisko"].values,
        "Grupa / Zmiana": df_filtrowany["Zmiana"].values, "Suma Trafień": df_filtrowany["Suma trafień"].astype(int).values,
        "Z 1. Strzału": df_filtrowany["Ile za pierwszym"].astype(int).values
    })

# --- INICJACJA STANU APLIKACJI ---
if "tryb_pracy" not in st.session_state: st.session_state.tryb_pracy = "MENU_START"
if "wybrani_zawodnicy" not in st.session_state: st.session_state.wybrani_zawodnicy = []
if "aktualny_strzal" not in st.session_state: st.session_state.aktualny_strzal = 0
if "aktualny_zawodnik_idx" not in st.session_state: st.session_state.aktualny_zawodnik_idx = 0
if "macierz_wynikow" not in st.session_state: st.session_state.macierz_wynikow = {}

# --- INTERFEJS 1: MENU STARTOWE ---
if st.session_state.tryb_pracy == "MENU_START":
    col_config1, col_config2 = st.columns(2)
    with col_config1:
        maks_zmiana = 0
        for zm in df_baza["Zmiana"].dropna().astype(str):
            if "Zmiana" in zm:
                try:
                    nr = int(zm.replace("Zmiana", "").strip())
                    if nr > maks_zmiana: maks_zmiana = nr
                except ValueError: pass
        nr_zmiany = st.number_input("Numer zmiany:", min_value=1, value=maks_zmiana + 1, step=1)
        nazwa_zmiany_global = f"Zmiana {nr_zmiany}"
    with col_config2:
        limit_rzutkow = st.selectbox("Łączna liczba rzutków w serii:", [10, 15, 20, 25], index=2)

    st.markdown("---")
    st.subheader("📋 Budowanie składu zmiany (Maksymalnie 6 osób)")
    
    zawodnicy_dostepni = []
    for nazwisko in df_baza["Nazwisko"].unique():
        wiersze = df_baza[df_baza["Nazwisko"] == nazwisko]
        standard_zrobiony = any(wiersze[(wiersze["Typ"] == "Standard") | (wiersze["Typ"].isna())]["Suma trafień"].notna())
        pk_zrobiony = any(wiersze[wiersze["Typ"] == "PK"]["Suma trafień"].notna())
        
        if not standard_zrobiony: zawodnicy_dostepni.append({"wyswietl": nazwisko, "czyste": nazwisko, "typ": "Standard"})
        if standard_zrobiony and not pk_zrobiony: zawodnicy_dostepni.append({"wyswietl": f"{nazwisko} [PK]", "czyste": nazwisko, "typ": "PK"})

    juz_dodani = [z["id_unikalne"] for z in st.session_state.wybrani_zawodnicy]
    opcje_wyboru = [z["wyswietl"] for z in zawodnicy_dostepni if z["wyswietl"] not in juz_dodani]
    
    col_dodaj1, col_dodaj2, col_dodaj3 = st.columns([3, 2, 2])
    with col_dodaj1: wybrany_z_listy = st.selectbox("Wybierz zawodnika z bazy klubowej:", [""] + opcje_wyboru)
    with col_dodaj2: wpisany_recznie = st.text_input("Lub dopisz nowego (Nazwisko Imię):").strip()
    with col_dodaj3: typ_reczny = st.selectbox("Typ startu dla dopisanego:", ["Standard", "PK"])

    if st.button("➕ Dodaj zawodnika do stanowiska"):
        if len(st.session_state.wybrani_zawodnicy) >= 6:
            st.error("W zmianie może być maksymalnie 6 zawodników!")
        else:
            finalne_nazwisko, finalny_typ = "", ""
            if wybrany_z_listy != "":
                obj = next(z for z in zawodnicy_dostepni if z["wyswietl"] == wybrany_z_listy)
                finalne_nazwisko, finalny_typ = obj["czyste"].upper(), obj["typ"]
            elif wpisany_recznie != "":
                finalne_nazwisko, finalny_typ = wpisany_recznie.upper(), typ_reczny
                
            if finalne_nazwisko:
                id_unikalne = f"{finalne_nazwisko} [PK]" if finalny_typ == "PK" else finalne_nazwisko
                st.session_state.wybrani_zawodnicy.append({"nazwisko": finalne_nazwisko, "id_unikalne": id_unikalne, "typ": finalny_typ})
                st.rerun()

    if st.session_state.wybrani_zawodnicy:
        st.markdown("#### Wybrani zawodnicy na stanowiskach:")
        for i, zaw in enumerate(st.session_state.wybrani_zawodnicy):
            col_z1, col_z2, col_z3 = st.columns([1, 5, 2])
            with col_z1: st.markdown(f"**Stanowisko {i+1}**")
            with col_z2: st.info(f"👤 {zaw['id_unikalne']} ({zaw['typ']})")
            with col_z3:
                if st.button(f"🗑️ Usuń", key=f"del_{i}"):
                    st.session_state.wybrani_zawodnicy.pop(i)
                    st.rerun()
                    
        if st.button("❌ Wyczyść cały skład"):
            st.session_state.wybrani_zawodnicy = []
            st.rerun()

    st.markdown("---")
    if st.button("🚀 ROZPOCZNIJ SEKWENCJĘ STRZELAŃ", type="primary"):
        if not st.session_state.wybrani_zawodnicy:
            st.error("Nie można rozpocząć bez zawodników!")
        else:
            st.session_state.tryb_pracy = "OS_STRZELECKA"
            st.session_state.aktualny_strzal, st.session_state.aktualny_zawodnik_idx = 0, 0
            st.session_state.limit_rzutkow, st.session_state.nazwa_zmiany = limit_rzutkow, nazwa_zmiany_global
            st.session_state.macierz_wynikow = {z["id_unikalne"]: ["-"] * limit_rzutkow for z in st.session_state.wybrani_zawodnicy}
            st.rerun()
            
    st.markdown("---")
    st.subheader("📊 Aktualne Klasyfikacje Generalne")
    tab1, tab2 = st.tabs(["🏆 Klasyfikacja Główna (Standard)", "🎯 Klasyfikacja Poza Konkurencją (PK)"])
    with tab1: st.dataframe(zbuduj_tabela_rankingu(df_baza, "Standard"), use_container_width=True)
    with tab2: st.dataframe(zbuduj_tabela_rankingu(df_baza, "PK"), use_container_width=True)

# --- INTERFEJS 2: EKRAN KARTY STRZELAŃ ---
elif st.session_state.tryb_pracy == "OS_STRZELECKA":
    st.subheader(f"🏟️ KARTA KONKURENCJI: {st.session_state.nazwa_zmiany.upper()} — {st.session_state.limit_rzutkow} RZUTKÓW")
    
    for i, z in enumerate(st.session_state.wybrani_zawodnicy):
        id_u = z["id_unikalne"]
        strzaly = st.session_state.macierz_wynikow[id_u]
        suma_laczna = sum(1 for s in strzaly if s in ["/", "X"])
        suma_pierwszy = sum(1 for s in strzaly if s == "/")
        
        html_strzaly = ""
        for s_idx, s in enumerate(strzaly):
            klasa = "shot-blank"
            if s == "/": klasa = "shot-t1"
            elif s == "X": klasa = "shot-t2"
            elif s == "O": klasa = "shot-miss"
            
            if st.session_state.aktualny_strzal < st.session_state.limit_rzutkow:
                if s_idx == st.session_state.aktualny_strzal and i == st.session_state.aktualny_zawodnik_idx:
                    klasa += " current-target"
                    s = "●"
                    
            html_strzaly += f'<div class="shot-box {klasa}">{s}</div>'
            if (s_idx + 1) % 5 == 0: html_strzaly += "&nbsp;&nbsp;"
                
        col_k1, col_k2, col_k3 = st.columns([1, 3, 5])
        with col_k1: st.markdown(f"**Stan. {i+1}** ({z['typ']})")
        with col_k2: st.markdown(f"**{id_u}**")
        with col_k3: st.markdown(f'{html_strzaly} &nbsp;&nbsp;&nbsp;&nbsp; 📊 **{suma_laczna} / {suma_pierwszy}**', unsafe_allow_html=True)
            
    st.markdown("---")
    
    if st.session_state.aktualny_strzal >= st.session_state.limit_rzutkow:
        st.success("🔥 Wszystkie serie zakończone!")
        
        if st.button("💾 ZAPISZ WYNIKI I AUTOMATYCZNIE WYŚLIJ DO GOOGLE SHEETS", type="primary", use_container_width=True):
            with st.spinner("Trwa zapis bezpośredni do chmury Google..."):
                df_aktualna_baza = pobierz_i_napraw_baze()
                df_aktualna_baza["Nazwisko"] = df_aktualna_baza["Nazwisko"].fillna("").astype(str).str.strip().str.upper()
                
                for i in range(1, st.session_state.limit_rzutkow + 1):
                    if f"Strzał_{i}" not in df_aktualna_baza.columns: df_aktualna_baza[f"Strzał_{i}"] = None

                for z in st.session_state.wybrani_zawodnicy:
                    nazwisko, typ_startu = z["nazwisko"].upper(), z["typ"]
                    strzaly_zawodnika = st.session_state.macierz_wynikow[z["id_unikalne"]]
                    suma_laczna = sum(1 for s in strzaly_zawodnika if s in ["/", "X"])
                    suma_pierwszy = sum(1 for s in strzaly_zawodnika if s == "/")
                    
                    indeksy_zawodnika = df_aktualna_baza[df_aktualna_baza["Nazwisko"] == nazwisko].index
                    wiersz_idx = None
                    
                    for idx in indeksy_zawodnika:
                        obecna_zmiana = str(df_aktualna_baza.at[idx, "Zmiana"]).strip()
                        obecny_typ = str(df_aktualna_baza.at[idx, "Typ"]).strip()
                        obecna_suma = str(df_aktualna_baza.at[idx, "Suma trafień"]).strip()
                        
                        if obecny_typ in ["", "nan", "None"]: obecny_typ = "Standard" if list(indeksy_zawodnika).index(idx) == 0 else "PK"
                        if obecna_zmiana in ["", "nan", "None"] or obecna_suma in ["", "nan", "None"]:
                            if obecny_typ == typ_startu: wiersz_idx = idx; break
                        elif obecna_zmiana == st.session_state.nazwa_zmiany and obecny_typ == typ_startu:
                            wiersz_idx = idx; break
                    
                    if wiersz_idx is not None:
                        df_aktualna_baza.at[wiersz_idx, "Zmiana"] = st.session_state.nazwa_zmiany
                        df_aktualna_baza.at[wiersz_idx, "Typ"] = typ_startu
                        df_aktualna_baza.at[wiersz_idx, "Suma trafień"] = int(suma_laczna)
                        df_aktualna_baza.at[wiersz_idx, "Ile za pierwszym"] = int(suma_pierwszy)
                        for i, sym in enumerate(strzaly_zawodnika): df_aktualna_baza.at[wiersz_idx, f"Strzał_{i+1}"] = sym
                    else:
                        nowy_wiersz = {"Nazwisko": nazwisko, "Zmiana": st.session_state.nazwa_zmiany, "Typ": typ_startu, "Suma trafień": int(suma_laczna), "Ile za pierwszym": int(suma_pierwszy)}
                        for i, sym in enumerate(strzaly_zawodnika): nowy_wiersz[f"Strzał_{i+1}"] = sym
                        df_aktualna_baza = pd.concat([df_aktualna_baza, pd.DataFrame([nowy_wiersz])], ignore_index=True)
                
                # WYGENEROWANIE RANKINGÓW PRZED ZAPISEM
                df_rezultaty_standard = zbuduj_tabela_rankingu(df_aktualna_baza, "Standard")
                df_rezultaty_pk = zbuduj_tabela_rankingu(df_aktualna_baza, "PK")
                
                try:
                    # WYWYŁANIE DO GOOGLE SŁUŻBOWYM KONEKTOREM
                    conn.update(worksheet="Wyniki_Szczegolowe", data=df_aktualna_baza)
                    conn.update(worksheet="Rezultaty", data=df_rezultaty_standard)
                    conn.update(worksheet="Rezultaty_PK", data=df_rezultaty_pk)
                    
                    st.success("✅ Sukces! Wyniki zostały zapisane bezpośrednio w chmurze.")
                    st.session_state.wybrani_zawodnicy = []
                    st.session_state.tryb_pracy = "MENU_START"
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Chmura odrzuciła zapis. Upewnij się, że w opcjach udostępniania pliku Google Sheets wybrałeś 'Każdy mający link może EDYTOWAĆ'. Błąd: {ex}")
    else:
        aktualny_zawodnik = st.session_state.wybrani_zawodnicy[st.session_state.aktualny_zawodnik_idx]
        
        st.markdown(f'<div class="current-player">', unsafe_allow_html=True)
        st.markdown(f"### 📣 Bieżący strzał:")
        st.markdown(f"**STANOWISKO {st.session_state.aktualny_zawodnik_idx + 1}**: 👤 `{aktualny_zawodnik['id_unikalne']}` | **Strzał nr {st.session_state.aktualny_strzal + 1}** z {st.session_state.limit_rzutkow}")
        st.markdown(f'</div>', unsafe_allow_html=True)
        
        def rejestruj_trafienie(symbol):
            id_u = st.session_state.wybrani_zawodnicy[st.session_state.aktualny_zawodnik_idx]['id_unikalne']
            st.session_state.macierz_wynikow[id_u][st.session_state.aktualny_strzal] = symbol
            
            st.session_state.aktualny_zawodnik_idx += 1
            if st.session_state.aktualny_zawodnik_idx >= len(st.session_state.wybrani_zawodnicy):
                st.session_state.aktualny_zawodnik_idx = 0
                st.session_state.aktualny_strzal += 1
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1: st.button("🔵 Trafiony 1 ( / )", use_container_width=True, type="primary", on_click=rejestruj_trafienie, args=("/",))
        with col_b2: st.button("🟢 Trafiony 2 ( X )", use_container_width=True, on_click=rejestruj_trafienie, args=("X",))
        with col_b3: st.button("🔴 Pudło ( O )", use_container_width=True, on_click=rejestruj_trafienie, args=("O",))

    st.markdown("---")
    if st.button("⬅️ Anuluj serię i wróć do menu głównego"):
        st.session_state.tryb_pracy = "MENU_START"
        st.session_state.wybrani_zawodnicy = []
        st.rerun()
