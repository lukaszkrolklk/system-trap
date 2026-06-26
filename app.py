import base64
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import qrcode
from io import BytesIO, StringIO

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
PUBLIC_RESULTS_DIR = APP_DIR / "public_results"
EVENTS_FILE = APP_DIR / "events.json"
DATA_DIR.mkdir(exist_ok=True)
ARCHIWUM_DIR.mkdir(exist_ok=True)
PUBLIC_RESULTS_DIR.mkdir(exist_ok=True)

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
        padding-top: 2.5rem;
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


def str_to_bool(value) -> bool:
    txt = str(value).strip().upper()
    return txt in ["TRUE", "TAK", "YES", "1", "Y"]


def safe_cell(row, col: str, default: str = "") -> str:
    if col not in row:
        return default

    value = row.get(col, default)

    if pd.isna(value):
        return default

    return str(value).strip()


def wczytaj_lokalny_events_json() -> dict:
    """
    Lokalny events.json nie jest już bazą zawodów.
    Służy tylko jako wskaźnik do arkusza TRAP_CONFIG oraz opcjonalnie do hasła administratora.
    """
    if not EVENTS_FILE.exists():
        return {}

    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def wczytaj_events_z_trap_config(config_sheet_link: str) -> dict:
    """
    Czyta konfigurację zawodów z publicznego arkusza Google Sheets przez CSV.
    Nie używa Google API.

    Wymagany arkusz / gid powinien mieć kolumny:
    kod, enabled, event_id, nazwa, google_sheet, aktywny_od, aktywny_do,
    pk_wymaga_standard, trap10, trap20, pk, standard
    """
    csv_url = google_link_do_csv_url(config_sheet_link)
    df = pd.read_csv(csv_url, dtype=str).fillna("")
    df.columns = [str(c).strip().lower() for c in df.columns]

    wymagane = [
        "kod",
        "enabled",
        "event_id",
        "nazwa",
        "google_sheet",
        "aktywny_od",
        "aktywny_do",
        "pk_wymaga_standard",
        "trap10",
        "trap20",
        "pk",
        "standard",
    ]

    brakujace = [c for c in wymagane if c not in df.columns]
    if brakujace:
        raise ValueError(f"Brakuje kolumn w TRAP_CONFIG: {', '.join(brakujace)}")

    events = {}

    for _, row in df.iterrows():
        kod = safe_cell(row, "kod").lower()

        if not kod or kod.startswith("_"):
            continue

        def limit_int(col: str, default: int) -> int:
            raw = safe_cell(row, col, str(default))
            try:
                val = int(float(str(raw).replace(",", ".")))
            except Exception:
                val = default
            return max(1, min(val, MAX_RZUTKOW))

        event_id_raw = safe_cell(row, "event_id", kod)

        events[kod] = {
            "enabled": str_to_bool(safe_cell(row, "enabled")),
            "event_id": slugify_event_id(event_id_raw or kod),
            "nazwa": safe_cell(row, "nazwa", kod),
            "google_sheet": safe_cell(row, "google_sheet"),
            "organizator": safe_cell(row, "organizator"),
            "link_rezultaty": safe_cell(row, "link_rezultaty"),
            "plik_rankingu": safe_cell(row, "plik_rankingu"),
            "aktywny_od": safe_cell(row, "aktywny_od"),
            "aktywny_do": safe_cell(row, "aktywny_do"),
            "pk_wymaga_standard": str_to_bool(safe_cell(row, "pk_wymaga_standard")),
            "konkurencje": {
                "TRAP10": limit_int("trap10", 10),
                "TRAP20": limit_int("trap20", 20),
                "PK": limit_int("pk", 20),
                "STANDARD": limit_int("standard", 20),
            },
        }

    return events


def wczytaj_events() -> dict:
    """
    Główna funkcja konfiguracji.
    Priorytet:
    1. events.json zawiera config_sheet -> pobieramy zawody z TRAP_CONFIG.
    2. Jeżeli TRAP_CONFIG nie działa, używamy lokalnego events.json jako awaryjnego fallbacku.
    """
    lokalny = wczytaj_lokalny_events_json()
    config_sheet = str(lokalny.get("config_sheet", "")).strip()

    if config_sheet:
        try:
            events = wczytaj_events_z_trap_config(config_sheet)

            # Hasło administratora zostaje lokalnie w events.json, żeby nie używać Google API do edycji.
            events["_admin"] = lokalny.get("_admin", {"password": "TRAPADMIN"})
            events["_config"] = {
                "source": "TRAP_CONFIG",
                "config_sheet": config_sheet,
            }
            return events

        except Exception as e:
            # Komunikat pokazujemy dopiero tam, gdzie jest dostępny Streamlit.
            st.sidebar.error(f"Nie udało się pobrać TRAP_CONFIG: {e}")
            lokalny["_config_error"] = str(e)
            return lokalny

    return lokalny



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


def pobierz_secret(name: str, default: str = "") -> str:
    """Czyta ustawienie najpierw ze st.secrets, potem ze zmiennych środowiskowych."""
    try:
        if name in st.secrets:
            return str(st.secrets.get(name, default)).strip()
    except Exception:
        pass

    return str(os.environ.get(name, default)).strip()


def aktualny_host() -> str:
    try:
        return str(st.context.headers.get("host", "")).lower()
    except Exception:
        return ""


def czy_adres_lokalny(host: str) -> bool:
    host = str(host).split(":")[0].strip().lower()
    if host in ["localhost", "127.0.0.1", "0.0.0.0"]:
        return True
    if host.startswith("10.") or host.startswith("192.168."):
        return True
    if re.match(r"^172\.(1[6-9]|2\d|3[0-1])\.", host):
        return True
    return False


def tryb_uruchomienia() -> str:
    host = aktualny_host()
    if host and czy_adres_lokalny(host):
        return "LOKALNY"
    if host:
        return "ONLINE"
    return "NIEZNANY"


def sciezka_rankingu_online(event_id: str | None = None) -> Path:
    event_id = slugify_event_id(event_id or aktywny_event_id())
    return PUBLIC_RESULTS_DIR / event_id / "ranking.csv"


def github_sciezka_rankingu(event_id: str | None = None) -> str:
    event_id = slugify_event_id(event_id or aktywny_event_id())
    cfg = st.session_state.get("event_cfg", {}) or {}
    custom = str(cfg.get("plik_rankingu", "")).strip() if isinstance(cfg, dict) else ""
    if custom:
        return custom.replace("\\", "/").lstrip("/")
    return f"public_results/{event_id}/ranking.csv"


def link_panelu_zawodnika(event_id: str | None = None) -> str:
    event_id = slugify_event_id(event_id or aktywny_event_id())
    cfg = st.session_state.get("event_cfg", {}) or {}
    custom = str(cfg.get("link_rezultaty", "")).strip() if isinstance(cfg, dict) else ""
    if custom:
        return custom
    return (
        "https://system-trap-ud8ffzmuwxrxsnzm7rbvlq.streamlit.app/"
        f"?event={event_id}&view=zawodnik"
    )


def zbuduj_ranking_publiczny(df_input: pd.DataFrame) -> pd.DataFrame:
    df = normalizuj_naglowki(df_input)
    konkurencje = lista_konkurencji(df)
    frames = []

    for konkurencja in konkurencje:
        ranking = zbuduj_ranking(df, konkurencja)
        if ranking.empty:
            continue
        ranking.insert(0, "event_id", aktywny_event_id())
        ranking.insert(1, "nazwa_zawodow", st.session_state.get("event_name", aktywny_event_id()))
        ranking.insert(2, "opublikowano", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        frames.append(ranking)

    if not frames:
        return pd.DataFrame(columns=[
            "event_id", "nazwa_zawodow", "opublikowano", "Miejsce", "Nazwisko i Imię",
            "Konkurencja", "Grupa / Zmiana", "Limit rzutków", "Suma Trafień (Wynik)",
            "Trafienia z 1. Strzału"
        ])

    return pd.concat(frames, ignore_index=True)


def zapisz_ranking_publiczny_lokalnie(df_input: pd.DataFrame, event_id: str | None = None) -> Path:
    event_id = slugify_event_id(event_id or aktywny_event_id())
    out_path = sciezka_rankingu_online(event_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ranking = zbuduj_ranking_publiczny(df_input)
    ranking.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def github_api_request(method: str, url: str, token: str, payload: dict | None = None) -> dict | None:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TRAP20-Streamlit",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API HTTP {e.code}: {body}")


def publikuj_plik_na_github(local_path: Path, repo_path: str, message: str) -> dict:
    token = pobierz_secret("GITHUB_TOKEN")
    repo = pobierz_secret("GITHUB_REPO")
    branch = pobierz_secret("GITHUB_BRANCH", "main") or "main"

    if not token or not repo:
        raise RuntimeError(
            "Brakuje konfiguracji GitHub. Ustaw GITHUB_TOKEN i GITHUB_REPO w .streamlit/secrets.toml "
            "albo w zmiennych środowiskowych."
        )

    repo_path = repo_path.replace("\\", "/").lstrip("/")
    base_url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"

    sha = None
    try:
        existing = github_api_request("GET", f"{base_url}?ref={branch}", token)
        if isinstance(existing, dict):
            sha = existing.get("sha")
    except RuntimeError as e:
        if "HTTP 404" not in str(e):
            raise

    content_b64 = base64.b64encode(local_path.read_bytes()).decode("ascii")
    payload = {
        "message": message,
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    return github_api_request("PUT", base_url, token, payload) or {}


def usun_plik_z_github(repo_path: str, message: str) -> dict:
    token = pobierz_secret("GITHUB_TOKEN")
    repo = pobierz_secret("GITHUB_REPO")
    branch = pobierz_secret("GITHUB_BRANCH", "main") or "main"

    if not token or not repo:
        raise RuntimeError("Brakuje GITHUB_TOKEN albo GITHUB_REPO.")

    repo_path = repo_path.replace("\\", "/").lstrip("/")
    base_url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"
    existing = github_api_request("GET", f"{base_url}?ref={branch}", token)
    sha = existing.get("sha") if isinstance(existing, dict) else None
    if not sha:
        raise RuntimeError("Nie znaleziono pliku online do usunięcia.")

    payload = {"message": message, "sha": sha, "branch": branch}
    return github_api_request("DELETE", base_url, token, payload) or {}


def publikuj_ranking_online(path: Path) -> tuple[Path, str]:
    df = wczytaj_excel(path)
    local_csv = zapisz_ranking_publiczny_lokalnie(df, aktywny_event_id())
    repo_path = github_sciezka_rankingu(aktywny_event_id())
    publikuj_plik_na_github(
        local_csv,
        repo_path,
        f"TRAP20: publikacja rankingu {aktywny_event_id()} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )
    return local_csv, repo_path


def pobierz_plik_z_github(repo_path: str) -> bytes | None:
    """Pobiera plik z GitHub przez Contents API. Działa także dla prywatnego repo, jeżeli ustawiono token."""
    token = pobierz_secret("GITHUB_TOKEN")
    repo = pobierz_secret("GITHUB_REPO")
    branch = pobierz_secret("GITHUB_BRANCH", "main") or "main"

    if not token or not repo:
        return None

    repo_path = str(repo_path).replace("\\", "/").lstrip("/")
    url = f"https://api.github.com/repos/{repo}/contents/{repo_path}?ref={branch}"

    try:
        data = github_api_request("GET", url, token)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    content = str(data.get("content", "")).replace("\n", "")
    if not content:
        return None

    try:
        return base64.b64decode(content)
    except Exception:
        return None


def wczytaj_opublikowany_ranking(event_id: str | None = None) -> pd.DataFrame:
    """Czyta opublikowany ranking.

    Priorytet:
    1. GitHub — dla Streamlit Cloud i publicznego panelu zawodnika.
    2. Lokalny public_results — awaryjnie i podczas testów lokalnych.
    """
    event_id = slugify_event_id(event_id or aktywny_event_id())
    repo_path = github_sciezka_rankingu(event_id)

    github_bytes = pobierz_plik_z_github(repo_path)
    if github_bytes:
        try:
            txt = github_bytes.decode("utf-8-sig")
            return pd.read_csv(StringIO(txt), dtype=str).fillna("")
        except Exception:
            pass

    csv_path = sciezka_rankingu_online(event_id)
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path, dtype=str).fillna("")


def policz_pliki_eventu(event_id: str) -> tuple[int, int]:
    event_id = slugify_event_id(event_id)
    active_dir = DATA_DIR / event_id
    archive_dir = ARCHIWUM_DIR / event_id

    active = len(list(active_dir.glob("*.xlsx"))) if active_dir.exists() else 0
    archive = len(list(archive_dir.glob("*.xlsx"))) if archive_dir.exists() else 0

    return active, archive


def pokaz_panel_administratora() -> None:
    st.markdown('<div class="main-title">⚙️ TRAP20 — Panel administratora</div>', unsafe_allow_html=True)
    st.caption("Podgląd konfiguracji zawodów z TRAP_CONFIG oraz plików aktywnych/archiwum. Edycję wykonujemy w Google Sheets.")

    events = wczytaj_events()
    config_info = events.get("_config", {}) if isinstance(events.get("_config", {}), dict) else {}

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Zawody",
        "📦 Pliki i archiwum",
        "🧾 Konfiguracja",
        "☁️ Publikacja online",
    ])

    with tab1:
        st.subheader("Kody zawodów z TRAP_CONFIG")

        rows = []
        for kod, cfg in eventy_uzytkowe(events).items():
            event_id = slugify_event_id(cfg.get("event_id", kod))
            aktywne_pliki, archiwum_pliki = policz_pliki_eventu(event_id)
            aktywny, komunikat = event_aktywny(cfg)
            limity = cfg.get("konkurencje", {}) if isinstance(cfg.get("konkurencje", {}), dict) else {}

            rows.append({
                "Kod": kod,
                "Włączony": bool(cfg.get("enabled", False)),
                "Aktywny teraz": aktywny,
                "Komunikat": komunikat,
                "Nazwa": cfg.get("nazwa", ""),
                "Organizator": cfg.get("organizator", ""),
                "event_id": event_id,
                "Aktywny od": cfg.get("aktywny_od", ""),
                "Aktywny do": cfg.get("aktywny_do", ""),
                "PK wymaga Standard": bool(cfg.get("pk_wymaga_standard", False)),
                "TRAP10": limity.get("TRAP10", ""),
                "TRAP20": limity.get("TRAP20", ""),
                "PK": limity.get("PK", ""),
                "STANDARD": limity.get("STANDARD", ""),
                "Pliki aktywne": aktywne_pliki,
                "Pliki archiwum": archiwum_pliki,
                "Google Sheet": cfg.get("google_sheet", ""),
                "Link rezultatów": cfg.get("link_rezultaty", ""),
                "Plik rankingu": cfg.get("plik_rankingu", ""),
            })

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Brak skonfigurowanych zawodów w TRAP_CONFIG.")

        if st.button("🔄 Odśwież podgląd", use_container_width=True):
            st.rerun()

        st.info(
            "Panel administratora jest teraz tylko do podglądu. "
            "Zmiany kodów, dat, linków i limitów rzutków wykonuj w arkuszu Google Sheets TRAP_CONFIG."
        )

    with tab2:
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

            wybor_pliku = st.selectbox(
                "Wybierz plik:",
                list(opis_do_sciezki.keys())
            )

            file_path = Path(opis_do_sciezki[wybor_pliku])

            if file_path.exists():
                st.download_button(
                    "⬇️ Pobierz wybrany Excel",
                    data=file_path.read_bytes(),
                    file_name=file_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            st.markdown("---")
            st.markdown("#### 📦 Przenieś aktywne pliki eventu do archiwum")

            eventy_aktywne = sorted({
                r["event_id"]
                for r in wszystkie_pliki
                if r["Typ"] == "AKTYWNE"
            })

            if eventy_aktywne:
                event_id_do_archiwizacji = st.selectbox(
                    "Wybierz event_id do przeniesienia aktywnych plików:",
                    eventy_aktywne,
                    key="event_id_move_active_to_archive",
                )

                aktywny_dir = DATA_DIR / event_id_do_archiwizacji
                arch_dir = ARCHIWUM_DIR / event_id_do_archiwizacji
                arch_dir.mkdir(parents=True, exist_ok=True)

                aktywne_pliki = list(aktywny_dir.glob("*.xlsx")) if aktywny_dir.exists() else []

                st.warning(
                    f"To przeniesie {len(aktywne_pliki)} aktywne pliki eventu "
                    f"{event_id_do_archiwizacji} do archiwum."
                )

                potwierdz_przeniesienie = st.checkbox(
                    f"Potwierdzam przeniesienie aktywnych plików eventu {event_id_do_archiwizacji} do archiwum",
                    key=f"confirm_move_active_{event_id_do_archiwizacji}",
                )

                if potwierdz_przeniesienie:
                    if st.button("📦 Przenieś aktywne pliki do archiwum", use_container_width=True):
                        try:
                            for plik in aktywne_pliki:
                                arch_path = arch_dir / (
                                    f"{plik.stem}_ARCHIWUM_{datetime.now().strftime('%Y%m%d_%H%M%S')}{plik.suffix}"
                                )
                                shutil.move(str(plik), str(arch_path))

                            if st.session_state.get("event_id") == event_id_do_archiwizacji:
                                st.session_state.aktywny_plik = ""

                            st.success(f"Przeniesiono {len(aktywne_pliki)} plików do archiwum.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Nie udało się przenieść plików do archiwum: {e}")
            else:
                st.info("Brak aktywnych plików do przeniesienia.")

            st.markdown("---")
            st.markdown("#### 🗑️ Usuń wybrany plik archiwalny")

            czy_archiwum = wybor_pliku.startswith("ARCHIWUM |")

            if czy_archiwum:
                potwierdz_usuniecie = st.checkbox(
                    f"Potwierdzam usunięcie pliku: {file_path.name}",
                    key=f"confirm_delete_file_{file_path.name}",
                )

                if potwierdz_usuniecie:
                    if st.button("🗑️ Usuń wybrany plik archiwalny", use_container_width=True):
                        try:
                            file_path.unlink()
                            st.success(f"Usunięto plik archiwalny: {file_path.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Nie udało się usunąć pliku: {e}")
            else:
                st.info("Usuwanie jest dostępne tylko dla plików z ARCHIWUM. Aktywnych zawodów nie usuwamy.")

            st.markdown("---")
            st.markdown("#### ⚠️ Wyczyść całe archiwum eventu")

            eventy_archiwum = sorted({
                r["event_id"]
                for r in wszystkie_pliki
                if r["Typ"] == "ARCHIWUM"
            })

            if eventy_archiwum:
                event_id_do_czyszczenia = st.selectbox(
                    "Wybierz event_id do wyczyszczenia archiwum:",
                    eventy_archiwum,
                    key="event_id_clear_archive",
                )

                arch_dir = ARCHIWUM_DIR / event_id_do_czyszczenia
                liczba_archiwum = len(list(arch_dir.glob("*.xlsx"))) if arch_dir.exists() else 0

                st.warning(
                    f"To usunie {liczba_archiwum} plików z archiwum eventu: {event_id_do_czyszczenia}"
                )

                potwierdz_cale = st.checkbox(
                    f"Potwierdzam wyczyszczenie całego archiwum eventu {event_id_do_czyszczenia}",
                    key=f"confirm_clear_archive_{event_id_do_czyszczenia}",
                )

                if potwierdz_cale:
                    if st.button("🗑️ Wyczyść archiwum tego eventu", use_container_width=True):
                        try:
                            if arch_dir.exists():
                                for plik in arch_dir.glob("*.xlsx"):
                                    plik.unlink()

                            st.success(f"Wyczyszczono archiwum eventu: {event_id_do_czyszczenia}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Nie udało się wyczyścić archiwum: {e}")
            else:
                st.info("Brak plików archiwalnych do wyczyszczenia.")
        else:
            st.info("Brak plików aktywnych i archiwalnych.")

    with tab3:
        st.subheader("Źródło konfiguracji")

        local_cfg = wczytaj_lokalny_events_json()
        config_sheet = config_info.get("config_sheet") or local_cfg.get("config_sheet", "")

        st.markdown("#### events.json")
        st.code(json.dumps(local_cfg, ensure_ascii=False, indent=2), language="json")

        st.markdown("#### TRAP_CONFIG")
        if config_sheet:
            st.write(config_sheet)
            st.caption("Aplikacja czyta dane z tego arkusza przez publiczny eksport CSV. Nie używa Google API.")
        else:
            st.warning("W events.json brakuje pola config_sheet.")

        if "_config_error" in events:
            st.error(f"Ostatni błąd pobierania TRAP_CONFIG: {events['_config_error']}")

        st.markdown("#### Podgląd danych używanych przez aplikację")
        podglad = {
            k: v for k, v in events.items()
            if isinstance(v, dict) and not str(k).startswith("_")
        }
        st.code(json.dumps(podglad, ensure_ascii=False, indent=2), language="json")

    with tab4:
        st.subheader("Publikowane rankingi online")
        st.caption("Pliki ranking.csv są przechowywane w katalogu public_results/<event_id>/ranking.csv i mogą być publikowane do GitHub.")

        events_user = eventy_uzytkowe(events)
        if not events_user:
            st.info("Brak eventów w konfiguracji.")
        else:
            opcje_eventow = sorted(events_user.keys())
            wybor_kodu = st.selectbox("Wybierz event:", opcje_eventow, key="admin_online_event")
            cfg = events_user[wybor_kodu]
            event_id = slugify_event_id(cfg.get("event_id", wybor_kodu))
            repo_path = str(cfg.get("plik_rankingu", "")).strip() or f"public_results/{event_id}/ranking.csv"
            local_csv = sciezka_rankingu_online(event_id)

            st.write(f"**event_id:** `{event_id}`")
            st.write(f"**plik online:** `{repo_path}`")
            if cfg.get("link_rezultaty"):
                st.write(f"**link rezultatów:** {cfg.get('link_rezultaty')}")
            else:
                st.write(f"**link rezultatów:** `...?event={event_id}&view=zawodnik`")

            if local_csv.exists():
                st.success(f"Lokalny plik publikacji istnieje: {local_csv}")
                st.download_button(
                    "⬇️ Pobierz ranking.csv",
                    data=local_csv.read_bytes(),
                    file_name="ranking.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.info("Brak lokalnego pliku public_results dla tego eventu.")

            st.markdown("---")
            st.markdown("#### 🗑️ Usuń ranking online")
            st.warning("To usuwa ranking.csv z GitHub dla wybranego eventu. Lokalnego Excela zawodów nie usuwa.")
            potwierdz = st.checkbox(f"Potwierdzam usunięcie publikacji online dla {event_id}", key=f"confirm_delete_online_{event_id}")
            if potwierdz:
                if st.button("🗑️ Usuń ranking online z GitHub", use_container_width=True):
                    try:
                        usun_plik_z_github(repo_path, f"TRAP20: usunięcie rankingu {event_id}")
                        if local_csv.exists():
                            local_csv.unlink()
                        st.success("Ranking online usunięty.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Nie udało się usunąć rankingu online: {e}")


def event_aktywny(event_cfg: dict) -> tuple[bool, str]:
    if not event_cfg.get("enabled", False):
        return False, "Kod zawodów jest wyłączony."

    aktywny_od = str(event_cfg.get("aktywny_od", "")).strip()
    aktywny_do = str(event_cfg.get("aktywny_do", "")).strip()

    if not aktywny_od and not aktywny_do:
        return True, ""

    def parse_date(txt: str, end_of_day: bool = False):
        if not txt:
            return None

        txt = txt.strip()

        try:
            return datetime.strptime(txt, "%Y-%m-%d %H:%M")
        except Exception:
            pass

        try:
            d = datetime.strptime(txt, "%Y-%m-%d")

            if end_of_day:
                return d.replace(hour=23, minute=59, second=59)

            return d.replace(hour=0, minute=0, second=0)

        except Exception:
            raise ValueError(txt)

    try:
        teraz = datetime.now()

        od = parse_date(aktywny_od)
        do = parse_date(aktywny_do, end_of_day=True)

    except Exception:
        return (
            False,
            "Błędny format daty w TRAP_CONFIG. Użyj RRRR-MM-DD lub RRRR-MM-DD GG:MM."
        )

    if od and teraz < od:
        return False, f"Kod będzie aktywny od {aktywny_od}."

    if do and teraz > do:
        return False, f"Kod wygasł {aktywny_do}."

    return True, ""


def ustaw_event(event_id: str, nazwa: str = "", cfg: dict | None = None) -> None:
    event_id = slugify_event_id(event_id)
    st.session_state.event_id = event_id
    st.session_state.event_name = nazwa or event_id
    st.session_state.event_cfg = cfg or {}


def aktywny_event_id() -> str:
    return slugify_event_id(st.session_state.get("event_id", "default"))

def pokaz_qr_panel_zawodnika(event_id: str):

    url = link_panelu_zawodnika(event_id)

    with st.sidebar.expander("📱 QR dla zawodników", expanded=False):

        st.write("Link do panelu zawodnika:")

        st.code(url)

        qr = qrcode.make(url)

        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)

        st.image(
            buffer,
            caption="Skanuj telefonem",
            use_container_width=True,
        )

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


def znajdz_konfiguracje_eventu(event_value: str) -> tuple[str, str, dict]:
    """Dopasowuje parametr event z linku QR do TRAP_CONFIG.

    Zwraca: event_id, nazwa, konfiguracja. Jeżeli TRAP_CONFIG jest niedostępny,
    wraca do samego parametru event, żeby panel publiczny nadal mógł szukać rankingu po ID.
    """
    event_value = str(event_value).strip()
    event_slug = slugify_event_id(event_value)

    try:
        events = wczytaj_events()
        for kod, cfg in eventy_uzytkowe(events).items():
            cfg_event_id = slugify_event_id(cfg.get("event_id", kod))
            if event_slug in [slugify_event_id(kod), cfg_event_id]:
                return cfg_event_id, str(cfg.get("nazwa", cfg_event_id)), cfg
    except Exception:
        pass

    return event_slug, event_value or event_slug, {}


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
    resolved_event_id, resolved_name, resolved_cfg = znajdz_konfiguracje_eventu(str(event_param).strip())
    ustaw_event(resolved_event_id, resolved_name, resolved_cfg)

if TRYB_ZAWODNIKA:
    st.markdown(
        """
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    .block-container {padding-top: 2.5rem;}
</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================

if not TRYB_ZAWODNIKA:
    st.sidebar.header("🏆 TRAP")

    _tryb = tryb_uruchomienia()
    if _tryb == "LOKALNY":
        st.sidebar.info("🟠 TRYB LOKALNY — wyniki zapisują się na tym komputerze. Publikacja online wymaga przycisku 📤.")
    elif _tryb == "ONLINE":
        st.sidebar.success("🟢 TRYB ONLINE — pracujesz na serwerze Streamlit.")
    else:
        st.sidebar.warning("⚪ Nie udało się jednoznacznie wykryć trybu uruchomienia.")

    EVENTS = wczytaj_events()


    if st.session_state.get("event_name"):
        st.sidebar.caption(f"Aktywne zawody: {st.session_state.event_name}")
        st.sidebar.caption(f"ID: {aktywny_event_id()}")
    
        pokaz_qr_panel_zawodnika(aktywny_event_id())

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
                    st.sidebar.error("Nieznany kod zawodów. Sprawdź arkusz TRAP_CONFIG.")
                    st.stop()

                event_cfg = EVENTS[kod_listy]
                aktywny, komunikat = event_aktywny(event_cfg)
                if not aktywny:
                    st.sidebar.error(komunikat)
                    st.stop()

                link_do_pobrania = str(event_cfg.get("google_sheet", "")).strip()
                if not link_do_pobrania:
                    st.sidebar.error("W TRAP_CONFIG brakuje pola google_sheet dla tego kodu.")
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
                st.sidebar.error("Wpisz kod zawodów z TRAP_CONFIG albo zaznacz własny link.")
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

    st.sidebar.markdown("---")

    col_admin_btn, _ = st.sidebar.columns([1, 5])

    with col_admin_btn:
        if st.button("⚙️", help="Panel serwisowy", key="btn_show_admin_sidebar"):
            st.session_state.show_admin_sidebar = not st.session_state.get("show_admin_sidebar", False)
            st.rerun()

    if st.session_state.get("show_admin_sidebar", False):
        with st.sidebar.expander("⚙️ Serwis", expanded=True):
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

if not TRYB_ZAWODNIKA and st.session_state.get("admin_logged", False) and st.session_state.get("admin_mode", False):
    pokaz_panel_administratora()
    st.stop()


# ============================================================
# GŁÓWNY WIDOK
# ============================================================

path = aktywny_path()

# W trybie zawodnika najpierw próbujemy pokazać opublikowany ranking.csv.
# Dzięki temu Streamlit Cloud może działać jako publiczna tablica wyników,
# nawet jeżeli pełny plik Excel zawodów znajduje się tylko lokalnie u sędziego.
if TRYB_ZAWODNIKA:
    df_publiczny = wczytaj_opublikowany_ranking(aktywny_event_id())
    if not df_publiczny.empty:
        st.markdown('<div class="main-title">📊 TRAP20 — wyniki zawodów</div>', unsafe_allow_html=True)
        st.caption("Publiczny ranking opublikowany przez organizatora.")
        if st.button("🔄 Odśwież wyniki"):
            st.rerun()
        st.markdown("---")

        if "opublikowano" in df_publiczny.columns and not df_publiczny["opublikowano"].empty:
            st.info(f"Ostatnia publikacja: {df_publiczny['opublikowano'].iloc[0]}")

        konkurencje_pub = sorted(df_publiczny.get("Konkurencja", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
        if not konkurencje_pub:
            st.info("Brak opublikowanych wyników.")
        else:
            tabs_pub = st.tabs([f"🏆 {k}" for k in konkurencje_pub] + ["🔎 Sprawdź zawodnika"])
            for tab, konkurencja in zip(tabs_pub[:-1], konkurencje_pub):
                with tab:
                    df_k = df_publiczny[df_publiczny["Konkurencja"].astype(str) == konkurencja].copy()
                    kolumny = [c for c in [
                        "Miejsce", "Nazwisko i Imię", "Konkurencja", "Grupa / Zmiana",
                        "Limit rzutków", "Suma Trafień (Wynik)", "Trafienia z 1. Strzału"
                    ] if c in df_k.columns]
                    st.dataframe(df_k[kolumny], use_container_width=True, hide_index=True)

            with tabs_pub[-1]:
                szukaj = st.text_input("Wpisz nazwisko zawodnika:", placeholder="np. KOWALSKI").strip().upper()
                df_s = df_publiczny.copy()
                if szukaj and "Nazwisko i Imię" in df_s.columns:
                    df_s = df_s[df_s["Nazwisko i Imię"].astype(str).str.upper().str.contains(szukaj, na=False)]
                if df_s.empty:
                    st.info("Brak wyników dla podanego filtra.")
                else:
                    kolumny = [c for c in [
                        "Miejsce", "Nazwisko i Imię", "Konkurencja", "Grupa / Zmiana",
                        "Suma Trafień (Wynik)", "Trafienia z 1. Strzału"
                    ] if c in df_s.columns]
                    st.dataframe(df_s[kolumny], use_container_width=True, hide_index=True)
        st.stop()

if path is None:
    if st.session_state.get("zawody_zakonczone", False):
        st.success("Zawody zostały zakończone. Aby rozpocząć nowe, pobierz listę z Google i utwórz nowy plik zawodów.")
    else:
        st.warning("Najpierw wpisz kod zawodów / link Google i utwórz plik zawodów.")
    st.stop()

df_baza = wczytaj_excel(path)



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
            help="Limit wynika z konfiguracji konkurencji w TRAP_CONFIG.",
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
            key=f"reczny_zawodnik_{reset_id}",
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

        st.markdown("---")
        st.subheader("☁️ Publikacja wyników online")
        if tryb_uruchomienia() == "LOKALNY":
            st.info("Pracujesz lokalnie. Ranking online dla zawodników zaktualizuje się dopiero po kliknięciu przycisku publikacji.")
        else:
            st.info("Pracujesz online. Ten przycisk może dodatkowo zapisać ranking.csv w public_results dla stałego podglądu zawodników.")

        if st.button("📤 Opublikuj aktualny ranking online", use_container_width=True):
            try:
                local_csv, repo_path = publikuj_ranking_online(path)
                st.success(f"Opublikowano ranking: {repo_path}")
                st.caption(f"Lokalna kopia CSV: {local_csv}")
            except Exception as e:
                st.error(f"Nie udało się opublikować rankingu online: {e}")

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

