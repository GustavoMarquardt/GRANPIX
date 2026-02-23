#!/usr/bin/env python3
"""
Finaliza todos os torneios não encerrados no Challonge.
Requer: CHALLONGE_API_KEY e CHALLONGE_USERNAME no .env

Rodar: python scripts/finalizar_torneios_challonge.py
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, '.env'))
except ImportError:
    pass

def _load_env(key):
    v = os.environ.get(key, '').strip()
    if not v and os.path.exists(os.path.join(_root, '.env')):
        with open(os.path.join(_root, '.env'), encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith(f'{key}='):
                    v = line.split('=', 1)[1].strip().strip('"\'')
                    break
    return v

CHALLONGE_API_KEY = _load_env('CHALLONGE_API_KEY')
CHALLONGE_USERNAME = _load_env('CHALLONGE_USERNAME')
CHALLONGE_API_BASE = 'https://api.challonge.com/v1'


def _auth():
    if CHALLONGE_USERNAME and CHALLONGE_API_KEY:
        return (CHALLONGE_USERNAME, CHALLONGE_API_KEY)
    if CHALLONGE_API_KEY:
        return (CHALLONGE_API_KEY, '')
    return None


def challonge_get(endpoint, params=None):
    import requests
    auth = _auth()
    if not auth:
        print('Configure CHALLONGE_API_KEY e CHALLONGE_USERNAME no .env')
        sys.exit(1)
    r = requests.get(
        f'{CHALLONGE_API_BASE}{endpoint}',
        auth=auth,
        headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
        params=params,
        timeout=30,
    )
    return r


def challonge_post(endpoint):
    import requests
    auth = _auth()
    if not auth:
        print('Configure CHALLONGE_API_KEY e CHALLONGE_USERNAME no .env')
        sys.exit(1)
    r = requests.post(
        f'{CHALLONGE_API_BASE}{endpoint}',
        auth=auth,
        headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
        timeout=30,
    )
    return r


def main():
    print('Buscando torneios no Challonge...')
    r = challonge_get('/tournaments.json', params={'state': 'all', 'per_page': 100})
    if r.status_code not in (200, 201):
        print(f'Erro ao listar: {r.status_code} {r.text[:300]}')
        sys.exit(1)

    data = r.json()
    tournaments = data if isinstance(data, list) else data.get('tournaments', data)
    if not isinstance(tournaments, list):
        tournaments = [tournaments] if tournaments else []

    to_finalize = []
    for t in tournaments:
        obj = t.get('tournament', t) if isinstance(t, dict) else t
        if not isinstance(obj, dict):
            continue
        state = obj.get('state', '')
        url_slug = obj.get('url', obj.get('id', ''))
        name = obj.get('name', url_slug)
        if state in ('in_progress', 'awaiting_review'):
            to_finalize.append((url_slug, name, state))

    if not to_finalize:
        print('Nenhum torneio pendente de finalização (todos já estão encerrados).')
        return

    print(f'Encontrados {len(to_finalize)} torneio(s) para finalizar:')
    for slug, name, state in to_finalize:
        print(f'  - {name} ({slug}) [{state}]')

    for slug, name, state in to_finalize:
        print(f'\nFinalizando: {name} ({slug})...')
        rf = challonge_post(f'/tournaments/{slug}/finalize.json')
        if rf.status_code in (200, 201):
            print(f'  OK - {name} finalizado.')
        else:
            print(f'  ERRO {rf.status_code}: {rf.text[:200]}')


if __name__ == '__main__':
    main()
