import os
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

KOLORY_WYNIKOW = {
    "/": "#1e40af",
    "X": "#15803d",
    "O": "#b91c1c",
    "-": "#ffffff"
}

KOLORY_TEKSTU = {
    "/": "white",
    "X": "white",
    "O": "white",
    "-": "black"
}


class TrapApp:

    def __init__(self, root):
        self.root = root
        self.root.title("System Punktacji TRAP v5.6")
        self.root.geometry("1200x780")
        self.statusy_pk_baza = {}

        self.excel_path = os.path.join("config", "lista_trap.xlsx")

        self.zawodnicy_dostepni = []
        self.statusy_standard_baza = {}
        self.wybrani_zawodnicy = []
        self.pola_wynikow = {}

        self.limit_rzutkow = 20
        self.aktualny_strzal_idx = 0
        self.aktualny_zawodnik_idx = 0
        self.aktywne_podswietlenie = None
        self.nazwa_zmiany = ""

        self.wczytaj_zawodnikow()
        self.stworz_ekran_startowy()
        self.ustaw_kolejny_numer_zmiany()

    def wczytaj_arkusz_wynikow(self):
        if not os.path.exists(self.excel_path):
            return pd.DataFrame()

        try:
            return pd.read_excel(self.excel_path, sheet_name="Wyniki Szczegółowe")
        except Exception:
            try:
                return pd.read_excel(self.excel_path, sheet_name=0)
            except Exception:
                return pd.DataFrame()

    def wczytaj_zawodnikow(self):
        self.statusy_pk_baza = {}
        self.zawodnicy_dostepni = []
        self.statusy_standard_baza = {}

        if not os.path.exists(self.excel_path):
            os.makedirs("config", exist_ok=True)
            return

        try:
            df = self.wczytaj_arkusz_wynikow()

            if "Nazwisko" not in df.columns:
                messagebox.showwarning(
                    "Błąd formatu",
                    "Plik Excel musi zawierać kolumnę 'Nazwisko'."
                )
                return

            if "Suma trafień" not in df.columns:
                df["Suma trafień"] = ""

            if "Typ" not in df.columns:
                df["Typ"] = ""

            if "Status" not in df.columns:
                df["Status"] = ""

            df["Nazwisko"] = df["Nazwisko"].fillna("").astype(str).str.strip()
            df["Typ"] = df["Typ"].fillna("").astype(str).str.strip()
            df["Suma trafień"] = df["Suma trafień"].fillna("").astype(str).str.strip()
            df["Status"] = df["Status"].fillna("").astype(str).str.strip()

            nazwiska = []

            for _, row in df.iterrows():
                nazwa = row["Nazwisko"]

                if nazwa == "" or nazwa.lower() == "nan":
                    continue

                if nazwa not in nazwiska:
                    nazwiska.append(nazwa)

            for nazwa in nazwiska:
                indeksy = df[df["Nazwisko"] == nazwa].index.tolist()
                wiersze = df.loc[indeksy].copy().reset_index(drop=True)

                standard_zrobiony = False
                standard_wolny = False
                pk_zrobiony = False
                pk_wolny = False

                for nr, row in wiersze.iterrows():
                    idx_excel = indeksy[nr]

                    typ = row["Typ"]
                    suma = row["Suma trafień"]

                    ma_wynik = suma != "" and suma.lower() != "nan"

                    if nr == 0:
                        typ_logiczny = "Standard"
                    elif nr == 1:
                        typ_logiczny = "PK"
                    else:
                        typ_logiczny = "NADMIAR"

                    if typ == "Standard":
                        typ_logiczny = "Standard"

                    if typ == "PK" and nr <= 1:
                        typ_logiczny = "PK"

                    if nr >= 2:
                        typ_logiczny = "NADMIAR"

                    if typ_logiczny == "Standard":
                        df.at[idx_excel, "Typ"] = "Standard"

                        if ma_wynik:
                            standard_zrobiony = True
                            df.at[idx_excel, "Status"] = "STANDARD ZAKOŃCZONY"
                        else:
                            standard_wolny = True
                            df.at[idx_excel, "Status"] = "DO STARTU"

                    elif typ_logiczny == "PK":
                        df.at[idx_excel, "Typ"] = "PK"

                        if ma_wynik:
                            pk_zrobiony = True
                            df.at[idx_excel, "Status"] = "PK ZAKOŃCZONE"
                        else:
                            pk_wolny = True
                            if standard_zrobiony:
                                df.at[idx_excel, "Status"] = "PK DOSTĘPNE"
                            else:
                                df.at[idx_excel, "Status"] = "PK OCZEKUJE NA STANDARD"

                    else:
                        df.at[idx_excel, "Typ"] = "NADMIAR"
                        df.at[idx_excel, "Status"] = "NADMIAROWE ZGŁOSZENIE — NIE BRAĆ POD UWAGĘ"

                self.statusy_standard_baza[nazwa.lower()] = standard_zrobiony
                self.statusy_pk_baza[nazwa.lower()] = pk_zrobiony

                if standard_wolny and not standard_zrobiony:
                    self.zawodnicy_dostepni.append({
                        "id_wyswietlane": nazwa,
                        "czyste_nazwisko": nazwa,
                        "domyslny_typ": "Standard"
                    })

                if standard_zrobiony and pk_wolny and not pk_zrobiony:
                    self.zawodnicy_dostepni.append({
                        "id_wyswietlane": f"{nazwa} [PK]",
                        "czyste_nazwisko": nazwa,
                        "domyslny_typ": "PK"
                    })

            # zapis statusów do Excela, żeby biuro widziało od razu nadmiarowe zgłoszenia
            try:
                tabela_rezultaty = self.zbuduj_ranking(df, typ="Standard")
                tabela_rezultaty_pk = self.zbuduj_ranking(df, typ="PK")

                with pd.ExcelWriter(self.excel_path, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Wyniki Szczegółowe", index=False)
                    tabela_rezultaty.to_excel(writer, sheet_name="Rezultaty", index=False)
                    tabela_rezultaty_pk.to_excel(writer, sheet_name="Rezultaty PK", index=False)
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror(
                "Błąd bazy danych",
                f"Nie udało się przetworzyć pliku lista_trap.xlsx:\n{e}"
            )

    def ustaw_kolejny_numer_zmiany(self):
        nastepny_nr = 1

        if os.path.exists(self.excel_path):
            try:
                df = self.wczytaj_arkusz_wynikow()

                if "Zmiana" in df.columns:
                    wszystkie_zmiany = df["Zmiana"].dropna().astype(str).tolist()
                    maks_nr = 0

                    for zm in wszystkie_zmiany:
                        if "Zmiana" in zm:
                            try:
                                nr = int(zm.replace("Zmiana", "").strip())
                                if nr > maks_nr:
                                    maks_nr = nr
                            except ValueError:
                                pass

                    if maks_nr > 0:
                        nastepny_nr = maks_nr + 1
            except Exception:
                pass

        self.entry_zmiana.delete(0, tk.END)
        self.entry_zmiana.insert(0, str(nastepny_nr))

    def stworz_ekran_startowy(self):
        self.frame_start = ttk.Frame(self.root, padding="15")
        self.frame_start.pack(fill="both", expand=True)

        frame_top = ttk.Frame(self.frame_start)
        frame_top.pack(fill="x", pady=5)

        ttk.Label(frame_top, text="Zmiana nr:", font=("Arial", 11, "bold")).pack(side="left", padx=5)

        self.entry_zmiana = ttk.Entry(frame_top, width=6, font=("Arial", 11), justify="center")
        self.entry_zmiana.pack(side="left", padx=5)

        ttk.Label(frame_top, text="Liczba rzutków (łączna):", font=("Arial", 11, "bold")).pack(side="left", padx=25)

        self.combo_rzutki = ttk.Combobox(
            frame_top,
            values=["10", "15", "20", "25"],
            width=8,
            font=("Arial", 11),
            state="readonly"
        )
        self.combo_rzutki.pack(side="left", padx=5)
        self.combo_rzutki.set("20")

        frame_search = ttk.LabelFrame(
            self.frame_start,
            text=" Wyszukaj lub dopisz zawodnika ręcznie ",
            padding="15"
        )
        frame_search.pack(fill="x", pady=10)

        ttk.Label(frame_search, text="Nazwisko i Imię:", font=("Arial", 10)).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5
        )

        self.entry_szukaj = ttk.Entry(frame_search, width=45, font=("Arial", 11))
        self.entry_szukaj.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.entry_szukaj.bind("<KeyRelease>", self.filtruj_liste)

        ttk.Label(frame_search, text="Typ startu:", font=("Arial", 10)).grid(
            row=0,
            column=2,
            sticky="w",
            padx=15
        )

        self.combo_typ_reczny = ttk.Combobox(
            frame_search,
            values=["Standard", "PK"],
            width=10,
            font=("Arial", 10),
            state="readonly"
        )
        self.combo_typ_reczny.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.combo_typ_reczny.set("Standard")

        self.lista_wynikow = tk.Listbox(frame_search, height=6, width=55, font=("Arial", 10))
        self.lista_wynikow.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        self.lista_wynikow.bind("<<ListboxSelect>>", self.reaguj_na_wybor_z_listy)

        btn_dodaj = ttk.Button(frame_search, text="Dodaj do zmiany", command=self.dodaj_zawodnika)
        btn_dodaj.grid(row=2, column=1, sticky="e", padx=5, pady=5)

        frame_lista = ttk.LabelFrame(
            self.frame_start,
            text=" Skład zmiany (Maksymalnie 6 osób) ",
            padding="15"
        )
        frame_lista.pack(fill="both", expand=True, pady=10)

        self.tree = ttk.Treeview(frame_lista, columns=("Stanowisko", "Nazwisko", "Typ"), show="headings")
        self.tree.heading("Stanowisko", text="Stanowisko")
        self.tree.heading("Nazwisko", text="Nazwisko i Imię")
        self.tree.heading("Typ", text="Typ")
        self.tree.column("Stanowisko", width=100, anchor="center")
        self.tree.column("Typ", width=150, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        btn_usun = ttk.Button(frame_lista, text="Usuń zawodnika", command=self.usun_ze_zmiany)
        btn_usun.pack(side="right", padx=10, anchor="n")

        self.btn_start = tk.Button(
            self.frame_start,
            text="ZACZNIJ KONKURENCJĘ",
            bg="#15803d",
            fg="white",
            font=("Arial", 13, "bold"),
            padx=10,
            pady=10,
            command=self.uruchom_konkurencje
        )
        self.btn_start.pack(fill="x", pady=6)

        self.btn_ranking = tk.Button(
            self.frame_start,
            text="📊 POKAŻ AKTUALNY RANKING",
            bg="#1e40af",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=10,
            pady=8,
            command=self.pokaz_ranking
        )
        self.btn_ranking.pack(fill="x", pady=6)

        self.filtruj_liste(None)

    def filtruj_liste(self, event):
        tekst = self.entry_szukaj.get().lower()
        self.lista_wynikow.delete(0, tk.END)

        pokaz = [
            z for z in self.zawodnicy_dostepni
            if not any(w["id_unikalne"] == z["id_wyswietlane"] for w in self.wybrani_zawodnicy)
        ]

        for z in pokaz:
            if tekst in z["id_wyswietlane"].lower():
                self.lista_wynikow.insert(tk.END, z["id_wyswietlane"])

    def reaguj_na_wybor_z_listy(self, event):
        zaznaczenie = self.lista_wynikow.curselection()

        if not zaznaczenie:
            return

        wybrane_id = self.lista_wynikow.get(zaznaczenie[0])

        if "[PK]" in wybrane_id:
            self.combo_typ_reczny.set("PK")
        else:
            self.combo_typ_reczny.set("Standard")

    def dodaj_zawodnika(self):
        if len(self.wybrani_zawodnicy) >= 6:
            messagebox.showwarning("Limit osób", "W zmianie może znajdować się maksymalnie 6 zawodników.")
            return

        wpisany_tekst = self.entry_szukaj.get().strip()
        zaznaczenie = self.lista_wynikow.curselection()
        typ_final = self.combo_typ_reczny.get()

        if zaznaczenie:
            wybrane_id = self.lista_wynikow.get(zaznaczenie[0])
            zawodnik_obj = next(
                (z for z in self.zawodnicy_dostepni if z["id_wyswietlane"] == wybrane_id),
                None
            )

            if not zawodnik_obj:
                messagebox.showerror("Błąd", "Nie udało się odnaleźć zawodnika na liście.")
                return

            nazwisko_final = zawodnik_obj["czyste_nazwisko"]

        else:
            if not wpisany_tekst:
                messagebox.showwarning("Błąd", "Wpisz nazwisko zawodnika lub wybierz go z listy!")
                return

            nazwisko_final = wpisany_tekst

        if typ_final == "Standard":
            klucz_szukania = nazwisko_final.lower()
            ukonczony_standard = self.statusy_standard_baza.get(klucz_szukania, False)

            if ukonczony_standard:
                messagebox.showerror(
                    "Blokada ponownego startu Standard",
                    f"Zawodnik '{nazwisko_final}' ma już zapisany wynik w konkurencji Standard.\n\n"
                    f"Nie można dodać go ponownie jako Standard.\n"
                    f"Jeżeli ma strzelać poza konkurencją, może wystartować tylko raz jako PK."
                )
                return

        if typ_final == "PK":
            klucz_szukania = nazwisko_final.lower()
            ukonczony_standard = self.statusy_standard_baza.get(klucz_szukania, False)
            ukonczony_pk = self.statusy_pk_baza.get(klucz_szukania, False)

            if not ukonczony_standard:
                messagebox.showerror(
                    "Blokada startu PK",
                    f"Zawodnik '{nazwisko_final}' nie ukończył jeszcze konkurencji Standard.\n\n"
                    f"Najpierw musi wystartować w konkurencji głównej."
                )
                return

            if ukonczony_pk:
                messagebox.showerror(
                    "Blokada ponownego startu PK",
                    f"Zawodnik '{nazwisko_final}' ma już zapisany wynik PK.\n\n"
                    f"Nie można dodać go kolejny raz. Maksymalnie dozwolone są 2 starty: Standard i PK."
                )
                return

        id_wyswietlane = f"{nazwisko_final} [PK]" if typ_final == "PK" else nazwisko_final

        if any(w["id_unikalne"] == id_wyswietlane for w in self.wybrani_zawodnicy):
            messagebox.showwarning("Duplikat", "Ten zawodnik o tym statusie jest już dodany do tej zmiany!")
            return

        stanowisko = len(self.wybrani_zawodnicy) + 1

        self.wybrani_zawodnicy.append({
            "stanowisko": stanowisko,
            "nazwisko": nazwisko_final,
            "id_unikalne": id_wyswietlane,
            "typ": typ_final
        })

        self.tree.insert("", tk.END, values=(stanowisko, id_wyswietlane, typ_final))

        self.entry_szukaj.delete(0, tk.END)
        self.combo_typ_reczny.set("Standard")
        self.filtruj_liste(None)

    def usun_ze_zmiany(self):
        selected_item = self.tree.selection()

        if not selected_item:
            return

        values = self.tree.item(selected_item, "values")
        id_do_usuniecia = values[1]

        self.wybrani_zawodnicy = [
            w for w in self.wybrani_zawodnicy
            if w["id_unikalne"] != id_do_usuniecia
        ]

        for i, w in enumerate(self.wybrani_zawodnicy):
            w["stanowisko"] = i + 1

        self.tree.delete(*self.tree.get_children())

        for w in self.wybrani_zawodnicy:
            self.tree.insert("", tk.END, values=(w["stanowisko"], w["id_unikalne"], w["typ"]))

        self.filtruj_liste(None)

    def uruchom_konkurencje(self):
        if not self.wybrani_zawodnicy:
            messagebox.showwarning("Błąd", "Nie można rozpocząć konkurencji bez zawodników!")
            return

        nr_zmiany_raw = self.entry_zmiana.get().strip()

        if not nr_zmiany_raw:
            messagebox.showwarning("Błąd", "Wpisz numer zmiany!")
            return

        self.nazwa_zmiany = f"Zmiana {nr_zmiany_raw}"
        self.limit_rzutkow = int(self.combo_rzutki.get())

        self.frame_start.pack_forget()

        self.aktualny_strzal_idx = 0
        self.aktualny_zawodnik_idx = 0

        for i, w in enumerate(self.wybrani_zawodnicy):
            w["stanowisko"] = i + 1

        self.stworz_karte_konkurencji(self.nazwa_zmiany)

    def stworz_karte_konkurencji(self, nazwa_zmiany):
        self.frame_karta = ttk.Frame(self.root, padding="15")
        self.frame_karta.pack(fill="both", expand=True)

        lbl_tytul = tk.Label(
            self.frame_karta,
            text=f"KARTA KONKURENCJI TRAP — {nazwa_zmiany.upper()} "
                 f"(NA {self.limit_rzutkow} RZUTKÓW)",
            font=("Arial", 16, "bold"),
            fg="#1e3a8a"
        )
        lbl_tytul.pack(pady=2)

        lbl_legenda = tk.Label(
            self.frame_karta,
            text="Opis kolumny SUMA: Łączna liczba trafień / Trafienia za pierwszym strzałem",
            font=("Arial", 10, "italic"),
            fg="#4b5563"
        )
        lbl_legenda.pack(pady=3)

        frame_grid = ttk.Frame(self.frame_karta)
        frame_grid.pack(fill="both", expand=True, pady=10)

        tk.Label(frame_grid, text="Stan.", font=("Arial", 11, "bold"), width=5).grid(
            row=0,
            column=0,
            padx=5,
            pady=5
        )

        tk.Label(
            frame_grid,
            text="Nazwisko i Imię",
            font=("Arial", 11, "bold"),
            width=25,
            anchor="w"
        ).grid(row=0, column=1, padx=5, pady=5)

        liczba_serii = self.limit_rzutkow // 5

        for i in range(liczba_serii):
            tk.Label(
                frame_grid,
                text=f"Seria {i + 1}",
                font=("Arial", 10, "bold"),
                fg="#4b5563"
            ).grid(row=0, column=i + 2, padx=10, pady=5)

        tk.Label(
            frame_grid,
            text="SUMA\n(Trafienia / I strzał)",
            font=("Arial", 10, "bold"),
            width=18
        ).grid(row=0, column=liczba_serii + 2, padx=10, pady=5)

        self.pola_wynikow = {}

        for r_idx, zaw in enumerate(self.wybrani_zawodnicy):
            row = r_idx + 1
            id_u = zaw["id_unikalne"]

            tk.Label(frame_grid, text=str(zaw["stanowisko"]), font=("Arial", 11)).grid(
                row=row,
                column=0,
                pady=8
            )

            tk.Label(frame_grid, text=id_u, font=("Arial", 11), anchor="w").grid(
                row=row,
                column=1,
                sticky="w",
                padx=5
            )

            self.pola_wynikow[id_u] = {
                "przycisk_strzaly": [],
                "etykieta_suma": None
            }

            for b_idx in range(liczba_serii):
                frame_blok = tk.Frame(
                    frame_grid,
                    bd=1,
                    relief="solid",
                    bg="#e5e7eb",
                    padx=2,
                    pady=2
                )
                frame_blok.grid(row=row, column=b_idx + 2, padx=4, pady=4)

                for s_idx in range(5):
                    btn_strzal = tk.Button(
                        frame_blok,
                        text="-",
                        width=3,
                        font=("Arial", 10, "bold"),
                        bg="white",
                        fg="black",
                        relief="groove",
                        bd=1
                    )
                    btn_strzal.config(
                        command=lambda b=btn_strzal, z=id_u: self.otworz_menu_korekty(b, z)
                    )
                    btn_strzal.pack(side="left", padx=1)

                    self.pola_wynikow[id_u]["przycisk_strzaly"].append(btn_strzal)

            lbl_suma = tk.Label(
                frame_grid,
                text="0 / 0",
                font=("Arial", 12, "bold"),
                fg="#1e3a8a",
                width=12
            )
            lbl_suma.grid(row=row, column=liczba_serii + 2, padx=10)

            self.pola_wynikow[id_u]["etykieta_suma"] = lbl_suma

        frame_panel = ttk.LabelFrame(
            self.frame_karta,
            text=" Panel szybkiego wprowadzania wyników zawodnika ",
            padding="10"
        )
        frame_panel.pack(fill="x", side="bottom", pady=5)

        self.lbl_kto_strzela = tk.Label(
            frame_panel,
            text="Kolej na strzał...",
            font=("Arial", 12, "bold"),
            fg="#1e3a8a"
        )
        self.lbl_kto_strzela.pack(pady=2)

        frame_przyciski_punkty = tk.Frame(frame_panel)
        frame_przyciski_punkty.pack(pady=5)

        tk.Button(
            frame_przyciski_punkty,
            text="Trafiony 1 ( / )",
            font=("Arial", 14, "bold"),
            bg=KOLORY_WYNIKOW["/"],
            fg="white",
            width=15,
            height=2,
            command=lambda: self.wpisz_punkt_z_panelu("/")
        ).pack(side="left", padx=15)

        tk.Button(
            frame_przyciski_punkty,
            text="Trafiony 2 ( X )",
            font=("Arial", 14, "bold"),
            bg=KOLORY_WYNIKOW["X"],
            fg="white",
            width=15,
            height=2,
            command=lambda: self.wpisz_punkt_z_panelu("X")
        ).pack(side="left", padx=15)

        tk.Button(
            frame_przyciski_punkty,
            text="Pudło ( O )",
            font=("Arial", 14, "bold"),
            bg=KOLORY_WYNIKOW["O"],
            fg="white",
            width=15,
            height=2,
            command=lambda: self.wpisz_punkt_z_panelu("O")
        ).pack(side="left", padx=15)

        frame_nav = tk.Frame(self.frame_karta)
        frame_nav.pack(fill="x", side="bottom", pady=5)

        tk.Button(
            frame_nav,
            text="← Anuluj i wróć",
            bg="#4b5563",
            fg="white",
            font=("Arial", 10),
            padx=6,
            pady=6,
            command=self.powrot_do_menu
        ).pack(side="left")

        self.btn_zapisz_excel = tk.Button(
            frame_nav,
            text="💾 ZAPISZ WYNIKI DO EXCELA",
            bg="#16803d",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=6,
            command=self.zapisz_do_excela
        )
        self.btn_zapisz_excel.pack(side="right")

        self.aktualizuj_wskaznik_kolejki()

    def aktualizuj_wskaznik_kolejki(self):
        if self.aktywne_podswietlenie:
            try:
                if self.aktywne_podswietlenie["text"] == "-":
                    self.aktywne_podswietlenie.config(bg="white")
            except Exception:
                pass

        if self.aktualny_strzal_idx >= self.limit_rzutkow:
            self.lbl_kto_strzela.config(
                text="🔥 KONKURENCJA ZAKOŃCZONA! Możesz bezpiecznie zapisać wyniki do Excela.",
                fg="#16803d"
            )
            self.aktywne_podswietlenie = None
            return

        zawodnik = self.wybrani_zawodnicy[self.aktualny_zawodnik_idx]
        id_u = zawodnik["id_unikalne"]

        text_info = (
            f"STANOWISKO {zawodnik['stanowisko']}: {id_u} — "
            f"Strzał nr {self.aktualny_strzal_idx + 1} z {self.limit_rzutkow}"
        )

        self.lbl_kto_strzela.config(text=text_info, fg="#1e3a8a")

        btn = self.pola_wynikow[id_u]["przycisk_strzaly"][self.aktualny_strzal_idx]

        if btn["text"] == "-":
            btn.config(bg="#fef08a")

        self.aktywne_podswietlenie = btn

    def wpisz_punkt_z_panelu(self, symbol):
        if self.aktualny_strzal_idx >= self.limit_rzutkow:
            return

        zawodnik = self.wybrani_zawodnicy[self.aktualny_zawodnik_idx]
        id_u = zawodnik["id_unikalne"]

        btn = self.pola_wynikow[id_u]["przycisk_strzaly"][self.aktualny_strzal_idx]
        btn.config(text=symbol, bg=KOLORY_WYNIKOW[symbol], fg=KOLORY_TEKSTU[symbol])

        self.aktualizuj_sume_zawodnika(id_u)

        self.aktualny_zawodnik_idx += 1

        if self.aktualny_zawodnik_idx >= len(self.wybrani_zawodnicy):
            self.aktualny_zawodnik_idx = 0
            self.aktualny_strzal_idx += 1

        self.aktualizuj_wskaznik_kolejki()

    def otworz_menu_korekty(self, przycisk_cel, id_u):
        okno_pop = tk.Toplevel(self.root)
        okno_pop.title("Korekta błędu")
        okno_pop.geometry("250x110")
        okno_pop.resizable(False, False)
        okno_pop.transient(self.root)
        okno_pop.grab_set()

        tk.Label(okno_pop, text="Skoryguj wynik na:", font=("Arial", 10, "bold")).pack(pady=8)

        frame_przyciski = tk.Frame(okno_pop)
        frame_przyciski.pack(pady=5)

        def dokonaj_zmiany(symbol):
            przycisk_cel.config(
                text=symbol,
                bg=KOLORY_WYNIKOW[symbol],
                fg=KOLORY_TEKSTU[symbol]
            )
            okno_pop.destroy()
            self.aktualizuj_sume_zawodnika(id_u)

            if self.aktywne_podswietlenie == przycisk_cel and symbol == "-":
                przycisk_cel.config(bg="#fef08a", fg="black")

        tk.Button(
            frame_przyciski,
            text="/",
            font=("Arial", 12, "bold"),
            width=3,
            bg=KOLORY_WYNIKOW["/"],
            fg="white",
            command=lambda: dokonaj_zmiany("/")
        ).pack(side="left", padx=5)

        tk.Button(
            frame_przyciski,
            text="X",
            font=("Arial", 12, "bold"),
            width=3,
            bg=KOLORY_WYNIKOW["X"],
            fg="white",
            command=lambda: dokonaj_zmiany("X")
        ).pack(side="left", padx=5)

        tk.Button(
            frame_przyciski,
            text="O",
            font=("Arial", 12, "bold"),
            width=3,
            bg=KOLORY_WYNIKOW["O"],
            fg="white",
            command=lambda: dokonaj_zmiany("O")
        ).pack(side="left", padx=5)

        tk.Button(
            frame_przyciski,
            text="Cofnij",
            font=("Arial", 10),
            width=5,
            bg="white",
            fg="black",
            command=lambda: dokonaj_zmiany("-")
        ).pack(side="left", padx=5)

    def aktualizuj_sume_zawodnika(self, id_u):
        symbole = [
            b["text"]
            for b in self.pola_wynikow[id_u]["przycisk_strzaly"]
        ]

        suma_laczna = sum(1 for s in symbole if s in ["/", "X"])
        suma_pierwszy = sum(1 for s in symbole if s == "/")

        self.pola_wynikow[id_u]["etykieta_suma"].config(
            text=f"{suma_laczna} / {suma_pierwszy}"
        )

    def zbuduj_ranking(self, df_baza, typ="Standard"):
        wymagane = ["Nazwisko", "Typ", "Zmiana", "Suma trafień", "Ile za pierwszym"]

        for col in wymagane:
            if col not in df_baza.columns:
                return pd.DataFrame(columns=[
                    "Miejsce",
                    "Nazwisko i Imię",
                    "Typ startu",
                    "Grupa / Zmiana",
                    "Suma Trafień (Wynik)",
                    "Trafienia z 1. Strzału"
                ])

        df = df_baza.copy()

        df["Typ"] = df["Typ"].fillna("").astype(str).str.strip()
        df["Nazwisko"] = df["Nazwisko"].fillna("").astype(str).str.strip()
        df["Zmiana"] = df["Zmiana"].fillna("").astype(str).str.strip()

        df = df[
            (df["Typ"] == typ) &
            (df["Nazwisko"] != "") &
            (df["Nazwisko"].str.lower() != "nan") &
            (df["Suma trafień"].notna()) &
            (df["Suma trafień"].astype(str).str.strip() != "") &
            (df["Suma trafień"].astype(str).str.strip().str.lower() != "nan")
        ].copy()

        if df.empty:
            return pd.DataFrame(columns=[
                "Miejsce",
                "Nazwisko i Imię",
                "Typ startu",
                "Grupa / Zmiana",
                "Suma Trafień (Wynik)",
                "Trafienia z 1. Strzału"
            ])

        df["Suma trafień"] = pd.to_numeric(df["Suma trafień"], errors="coerce")
        df["Ile za pierwszym"] = pd.to_numeric(df["Ile za pierwszym"], errors="coerce").fillna(0)

        df = df.dropna(subset=["Suma trafień"])

        df = df.sort_values(
            by=["Suma trafień", "Ile za pierwszym", "Nazwisko"],
            ascending=[False, False, True]
        )

        miejsca = []
        poprzedni_wynik = None
        poprzedni_pierwszy = None
        aktualne_miejsce = 1

        for i, (_, row) in enumerate(df.iterrows()):
            wynik = row["Suma trafień"]
            pierwszy = row["Ile za pierwszym"]

            if i == 0:
                aktualne_miejsce = 1
            elif wynik != poprzedni_wynik or pierwszy != poprzedni_pierwszy:
                aktualne_miejsce = i + 1

            miejsca.append(aktualne_miejsce)

            poprzedni_wynik = wynik
            poprzedni_pierwszy = pierwszy

        tabela = pd.DataFrame()
        tabela["Miejsce"] = miejsca
        tabela["Nazwisko i Imię"] = df["Nazwisko"].values
        tabela["Typ startu"] = df["Typ"].values
        tabela["Grupa / Zmiana"] = df["Zmiana"].values
        tabela["Suma Trafień (Wynik)"] = df["Suma trafień"].astype(int).values
        tabela["Trafienia z 1. Strzału"] = df["Ile za pierwszym"].astype(int).values

        return tabela

    def pokaz_ranking(self):
        if not os.path.exists(self.excel_path):
            messagebox.showerror("Błąd", "Nie znaleziono pliku Excel z wynikami.")
            return

        df_baza = self.wczytaj_arkusz_wynikow()

        if df_baza.empty:
            messagebox.showinfo("Ranking", "Brak danych do wyświetlenia.")
            return

        tabela_rankingu = self.zbuduj_ranking(df_baza, typ="Standard")

        if tabela_rankingu.empty:
            messagebox.showinfo("Ranking", "Brak zapisanych wyników Standard.")
            return

        okno = tk.Toplevel(self.root)
        okno.title("Aktualny ranking — Standard")
        okno.geometry("850x600")
        okno.transient(self.root)

        lbl = tk.Label(
            okno,
            text="AKTUALNY RANKING — STANDARD",
            font=("Arial", 16, "bold"),
            fg="#1e3a8a"
        )
        lbl.pack(pady=10)

        frame = ttk.Frame(okno)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "Miejsce",
            "Nazwisko",
            "Zmiana",
            "Wynik",
            "Pierwszy"
        )

        tree = ttk.Treeview(frame, columns=columns, show="headings")

        tree.heading("Miejsce", text="Miejsce")
        tree.heading("Nazwisko", text="Nazwisko i Imię")
        tree.heading("Zmiana", text="Zmiana")
        tree.heading("Wynik", text="Suma trafień")
        tree.heading("Pierwszy", text="Za pierwszym")

        tree.column("Miejsce", width=80, anchor="center")
        tree.column("Nazwisko", width=300, anchor="w")
        tree.column("Zmiana", width=130, anchor="center")
        tree.column("Wynik", width=120, anchor="center")
        tree.column("Pierwszy", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for _, row in tabela_rankingu.iterrows():
            tree.insert(
                "",
                tk.END,
                values=(
                    row["Miejsce"],
                    row["Nazwisko i Imię"],
                    row["Grupa / Zmiana"],
                    row["Suma Trafień (Wynik)"],
                    row["Trafienia z 1. Strzału"]
                )
            )

        tk.Button(
            okno,
            text="Zamknij",
            bg="#4b5563",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=12,
            pady=6,
            command=okno.destroy
        ).pack(pady=10)

    def zapisz_do_excela(self):
        if not os.path.exists(self.excel_path):
            messagebox.showerror(
                "Błąd",
                "Nie znaleziono pliku źródłowego config/lista_trap.xlsx!"
            )
            return

        for zaw in self.wybrani_zawodnicy:
            if any(
                b["text"] == "-"
                for b in self.pola_wynikow[zaw["id_unikalne"]]["przycisk_strzaly"]
            ):
                messagebox.showwarning(
                    "Niekompletne wyniki",
                    f"Zawodnik '{zaw['id_unikalne']}' nie oddał wszystkich strzałów."
                )
                return

        try:
            df_baza = self.wczytaj_arkusz_wynikow()

            if df_baza.empty:
                messagebox.showerror("Błąd", "Nie udało się odczytać arkusza z wynikami.")
                return

            if "Nazwisko" not in df_baza.columns:
                messagebox.showerror("Błąd", "Brak kolumny 'Nazwisko' w pliku Excel!")
                return

            if "Zmiana" not in df_baza.columns:
                df_baza.insert(1, "Zmiana", "")

            if "Typ" not in df_baza.columns:
                df_baza.insert(2, "Typ", "")

            if "Suma trafień" not in df_baza.columns:
                df_baza["Suma trafień"] = ""

            if "Ile za pierwszym" not in df_baza.columns:
                df_baza["Ile za pierwszym"] = ""

            df_baza["Nazwisko"] = df_baza["Nazwisko"].astype(str).str.strip()
            df_baza["Zmiana"] = df_baza["Zmiana"].fillna("").astype(str).str.strip()
            df_baza["Typ"] = df_baza["Typ"].fillna("").astype(str).str.strip()

            for i in range(1, self.limit_rzutkow + 1):
                col = f"Strzał_{i}"

                if col not in df_baza.columns:
                    df_baza[col] = ""

                df_baza[col] = df_baza[col].fillna("").astype(str)

            modyfikacja_licznik = 0

            for zaw in self.wybrani_zawodnicy:
                nazwisko = zaw["nazwisko"]
                typ_startu = zaw["typ"]

                symbole = [
                    b["text"]
                    for b in self.pola_wynikow[zaw["id_unikalne"]]["przycisk_strzaly"]
                ]

                suma_laczna = sum(1 for s in symbole if s in ["/", "X"])
                suma_pierwszy = sum(1 for s in symbole if s == "/")

                wiersze_zawodnika = df_baza[df_baza["Nazwisko"] == nazwisko].index

                wybrany_idx = None

                for idx in wiersze_zawodnika:
                    obecna_zmiana = str(df_baza.at[idx, "Zmiana"]).strip()
                    obecny_typ = str(df_baza.at[idx, "Typ"]).strip()
                    obecna_suma = str(df_baza.at[idx, "Suma trafień"]).strip()

                    if obecny_typ in ["", "nan"]:
                        pozycja_zawodnika = list(wiersze_zawodnika).index(idx)

                        if pozycja_zawodnika == 0:
                            obecny_typ = "Standard"
                        else:
                            obecny_typ = "PK"

                    if obecna_zmiana in ["", "nan"] or obecna_suma in ["", "nan"]:
                        if obecny_typ == typ_startu:
                            wybrany_idx = idx
                            break

                    elif obecna_zmiana == str(self.nazwa_zmiany) and obecny_typ == str(typ_startu):
                        wybrany_idx = idx
                        break

                standard_zrobiony = False
                pk_zrobiony = False

                for idx_check in wiersze_zawodnika:
                    typ_check = str(df_baza.at[idx_check, "Typ"]).strip()
                    suma_check = str(df_baza.at[idx_check, "Suma trafień"]).strip()

                    if typ_check in ["", "nan"]:
                        pozycja_zawodnika = list(wiersze_zawodnika).index(idx_check)

                        if pozycja_zawodnika == 0:
                            typ_check = "Standard"
                        else:
                            typ_check = "PK"

                    ma_wynik_check = suma_check not in ["", "nan"]

                    if typ_check == "Standard" and ma_wynik_check:
                        standard_zrobiony = True

                    if typ_check == "PK" and ma_wynik_check:
                        pk_zrobiony = True

                if typ_startu == "Standard" and standard_zrobiony:
                    messagebox.showerror(
                        "Blokada zapisu",
                        f"Zawodnik '{nazwisko}' ma już zapisany wynik Standard.\n\n"
                        f"Nie można zapisać go ponownie jako Standard."
                    )
                    return

                if typ_startu == "PK" and not standard_zrobiony:
                    messagebox.showerror(
                        "Blokada zapisu",
                        f"Zawodnik '{nazwisko}' nie ma jeszcze wyniku Standard.\n\n"
                        f"Najpierw musi wystartować w konkurencji głównej."
                    )
                    return

                if typ_startu == "PK" and pk_zrobiony:
                    messagebox.showerror(
                        "Blokada zapisu",
                        f"Zawodnik '{nazwisko}' ma już zapisany wynik PK.\n\n"
                        f"Nie można zapisać go kolejny raz. Maksymalnie: Standard + PK."
                    )
                    return

                if wybrany_idx is not None:
                    df_baza.at[wybrany_idx, "Zmiana"] = str(self.nazwa_zmiany)
                    df_baza.at[wybrany_idx, "Typ"] = str(typ_startu)
                    df_baza.at[wybrany_idx, "Suma trafień"] = int(suma_laczna)
                    df_baza.at[wybrany_idx, "Ile za pierwszym"] = int(suma_pierwszy)

                    for i in range(self.limit_rzutkow):
                        df_baza.at[wybrany_idx, f"Strzał_{i + 1}"] = str(symbole[i])

                    modyfikacja_licznik += 1

                else:
                    nowy_wiersz = {
                        "Nazwisko": nazwisko,
                        "Zmiana": str(self.nazwa_zmiany),
                        "Typ": str(typ_startu),
                        "Suma trafień": int(suma_laczna),
                        "Ile za pierwszym": int(suma_pierwszy)
                    }

                    for i in range(self.limit_rzutkow):
                        nowy_wiersz[f"Strzał_{i + 1}"] = str(symbole[i])

                    df_baza = pd.concat(
                        [df_baza, pd.DataFrame([nowy_wiersz])],
                        ignore_index=True
                    )

                    modyfikacja_licznik += 1

            tabela_rezultaty = self.zbuduj_ranking(df_baza, typ="Standard")
            tabela_rezultaty_pk = self.zbuduj_ranking(df_baza, typ="PK")

            with pd.ExcelWriter(self.excel_path, engine="openpyxl") as writer:
                df_baza.to_excel(writer, sheet_name="Wyniki Szczegółowe", index=False)
                tabela_rezultaty.to_excel(writer, sheet_name="Rezultaty", index=False)
                tabela_rezultaty_pk.to_excel(writer, sheet_name="Rezultaty PK", index=False)

            odpowiedz = messagebox.askyesno(
                "Zapisano pomyślnie!",
                "Wyniki zapisane.\n\n"
                "Arkusze 'Rezultaty' i 'Rezultaty PK' zostały zbudowane od nowa.\n\n"
                "Czy chcesz przejść do wprowadzania NOWEJ ZMIANY?"
            )

            if odpowiedz:
                self.wymus_reset_do_nowej_grupy()

        except Exception as e:
            messagebox.showerror(
                "Błąd zapisu",
                f"Zamknij plik Excel przed zapisem!\n\nBłąd: {e}"
            )

    def wymus_reset_do_nowej_grupy(self):
        self.frame_karta.pack_forget()
        self.wybrani_zawodnicy = []
        self.tree.delete(*self.tree.get_children())
        self.wczytaj_zawodnikow()
        self.frame_start.pack(fill="both", expand=True)
        self.ustaw_kolejny_numer_zmiany()
        self.filtruj_liste(None)

    def powrot_do_menu(self):
        if messagebox.askyesno("Potwierdzenie", "Czy na pewno chcesz zamknąć tę kartę zmian?"):
            self.frame_karta.pack_forget()
            self.wybrani_zawodnicy = []
            self.tree.delete(*self.tree.get_children())
            self.wczytaj_zawodnikow()
            self.frame_start.pack(fill="both", expand=True)
            self.ustaw_kolejny_numer_zmiany()
            self.filtruj_liste(None)


if __name__ == "__main__":
    root = tk.Tk()
    app = TrapApp(root)
    root.mainloop()