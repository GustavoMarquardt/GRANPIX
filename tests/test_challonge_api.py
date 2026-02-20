"""
Teste da API Challonge v1 com Basic Auth (username, api_key).
Rodar: pytest tests/test_challonge_api.py -v -s

Requer no .env: CHALLONGE_API_KEY e CHALLONGE_USERNAME
"""
import os
import time
import pytest

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, '.env'))
except ImportError:
    pass


def _load_env(key):
    v = os.environ.get(key, '').strip()
    if not v and os.path.exists(os.path.join(_root, '.env')):
        with open(os.path.join(_root, '.env')) as f:
            for line in f:
                if line.strip().startswith(f'{key}='):
                    v = line.split('=', 1)[1].strip().strip('"\'')
                    break
    return v


CHALLONGE_API_KEY = _load_env('CHALLONGE_API_KEY')
CHALLONGE_USERNAME = _load_env('CHALLONGE_USERNAME')
CHALLONGE_API_BASE = "https://api.challonge.com/v1"


def _challonge_auth():
    if CHALLONGE_USERNAME and CHALLONGE_API_KEY:
        return (CHALLONGE_USERNAME, CHALLONGE_API_KEY)
    if CHALLONGE_API_KEY:
        return (CHALLONGE_API_KEY, "")
    return None


def challonge_request(method, endpoint, data=None, params=None):
    """Mesmo padrão do app: User-Agent Mozilla/5.0, Basic Auth, data= para form (v1)."""
    import requests
    auth = _challonge_auth()
    if not auth:
        raise ValueError("Configure CHALLONGE_API_KEY e CHALLONGE_USERNAME no .env")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    url = f"{CHALLONGE_API_BASE}{endpoint}"
    kw = {
        "method": method,
        "url": url,
        "auth": auth,
        "params": params,
        "headers": headers,
        "timeout": 20,
    }
    if data is not None:
        kw["data"] = data  # v1 usa form-urlencoded, não json
    r = requests.request(**kw)
    print(r.status_code, r.text[:200])
    return r


def _skip_on_520(r):
    if r.status_code == 520:
        pytest.skip("Challonge 520 (Cloudflare). Tente mais tarde ou outra rede.")


def _assert_ok(r, msg="Esperado 200/201"):
    _skip_on_520(r)
    assert r.status_code in (200, 201), f'{msg}: {r.status_code} {r.text[:200]}'


# ---------- Testes ----------

@pytest.mark.skipif(not CHALLONGE_API_KEY, reason="CHALLONGE_API_KEY não configurado")
def test_challonge_get_tournaments():
    """GET /tournaments.json - lista torneios."""
    r = challonge_request("GET", "/tournaments.json")
    _assert_ok(r)
    data = r.json()
    assert isinstance(data, list) or "tournaments" in str(data).lower(), "Resposta deve ser lista de torneios"


@pytest.mark.skipif(not CHALLONGE_API_KEY, reason="CHALLONGE_API_KEY não configurado")
def test_challonge_create_tournament():
    """POST /tournaments.json - cria torneio com slug único."""
    slug = f"granpix_test_{int(time.time())}"
    payload = {
        "tournament[name]": "GRANPIX Test",
        "tournament[url]": slug,
        "tournament[tournament_type]": "single elimination",
    }
    r = challonge_request("POST", "/tournaments.json", data=payload)
    _assert_ok(r)
    tour = r.json()
    t = tour.get("tournament", tour)
    assert t.get("url") == slug
    challonge_request("DELETE", f"/tournaments/{slug}.json")


@pytest.mark.skipif(not CHALLONGE_API_KEY, reason="CHALLONGE_API_KEY não configurado")
def test_challonge_add_participant():
    """POST /tournaments/{slug}/participants.json - adiciona participante."""
    slug = f"granpix_test_p_{int(time.time())}"
    cr = challonge_request("POST", "/tournaments.json", data={
        "tournament[name]": "GRANPIX Test Part",
        "tournament[url]": slug,
        "tournament[tournament_type]": "single elimination",
    })
    _assert_ok(cr)
    r = challonge_request("POST", f"/tournaments/{slug}/participants.json", data={
        "participant[name]": "Equipe A",
        "participant[seed]": 1,
    })
    _assert_ok(r)
    challonge_request("DELETE", f"/tournaments/{slug}.json")


@pytest.mark.skipif(not CHALLONGE_API_KEY, reason="CHALLONGE_API_KEY não configurado")
def test_challonge_full_flow_create_add_start():
    """Fluxo completo: criar torneio, adicionar 2 participantes, iniciar."""
    slug = f"granpix_flow_{int(time.time())}"
    # 1. Criar
    r1 = challonge_request("POST", "/tournaments.json", data={
        "tournament[name]": "GRANPIX Flow Test",
        "tournament[url]": slug,
        "tournament[tournament_type]": "single elimination",
    })
    _assert_ok(r1, "Create")
    # 2. Adicionar 2 participantes
    for i, nome in enumerate(["Equipe 1", "Equipe 2"], 1):
        r2 = challonge_request("POST", f"/tournaments/{slug}/participants.json", data={
            "participant[name]": nome,
            "participant[seed]": i,
        })
        _assert_ok(r2, f"Add participant {nome}")
    # 3. Iniciar
    r3 = challonge_request("POST", f"/tournaments/{slug}/start.json")
    _assert_ok(r3, "Start")
    # 4. Limpar: deletar torneio
    r4 = challonge_request("DELETE", f"/tournaments/{slug}.json")
    _skip_on_520(r4)
    assert r4.status_code in (200, 201, 204), f"Delete: {r4.status_code}"


@pytest.mark.skipif(not CHALLONGE_API_KEY, reason="CHALLONGE_API_KEY não configurado")
def test_challonge_get_participants_and_matches():
    """GET participants + matches de um torneio iniciado (valida estrutura da API)."""
    slug = f"granpix_mm_{int(time.time())}"
    cr = challonge_request("POST", "/tournaments.json", data={
        "tournament[name]": "GRANPIX Match Test",
        "tournament[url]": slug,
        "tournament[tournament_type]": "single elimination",
    })
    _assert_ok(cr)
    for i, nome in enumerate(["A", "B"], 1):
        challonge_request("POST", f"/tournaments/{slug}/participants.json", data={
            "participant[name]": nome,
            "participant[seed]": i,
        })
    challonge_request("POST", f"/tournaments/{slug}/start.json")
    rp = challonge_request("GET", f"/tournaments/{slug}/participants.json")
    rm = challonge_request("GET", f"/tournaments/{slug}/matches.json")
    _assert_ok(rp)
    _assert_ok(rm)
    parts = rp.json()
    matches = rm.json()
    assert isinstance(parts, list) or (isinstance(parts, dict) and "participant" in str(parts))
    assert isinstance(matches, list) or (isinstance(matches, dict) and "match" in str(matches))
    challonge_request("DELETE", f"/tournaments/{slug}.json")


@pytest.mark.skipif(not CHALLONGE_API_KEY, reason="CHALLONGE_API_KEY não configurado")
def test_challonge_report_winner_and_reopen():
    """Reporta vencedor e depois reabre a partida."""
    slug = f"granpix_rr_{int(time.time())}"
    challonge_request("POST", "/tournaments.json", data={
        "tournament[name]": "GRANPIX Report Test",
        "tournament[url]": slug,
        "tournament[tournament_type]": "single elimination",
    })
    challonge_request("POST", f"/tournaments/{slug}/participants.json", data={"participant[name]": "A", "participant[seed]": 1})
    challonge_request("POST", f"/tournaments/{slug}/participants.json", data={"participant[name]": "B", "participant[seed]": 2})
    challonge_request("POST", f"/tournaments/{slug}/start.json")
    rm = challonge_request("GET", f"/tournaments/{slug}/matches.json")
    _assert_ok(rm)
    matches = rm.json()
    m = matches[0].get("match", matches[0]) if isinstance(matches[0], dict) else matches[0]
    match_id = m.get("id")
    player1_id = m.get("player1_id")
    rr = challonge_request("PUT", f"/tournaments/{slug}/matches/{match_id}.json", data={
        "match[winner_id]": player1_id,
        "match[scores_csv]": "1-0",
    })
    _assert_ok(rr, "Report winner")
    ropen = challonge_request("POST", f"/tournaments/{slug}/matches/{match_id}/reopen.json")
    _assert_ok(ropen, "Reopen")
    challonge_request("DELETE", f"/tournaments/{slug}.json")
