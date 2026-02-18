"""
Configuração do pytest para o GRANPIX.
Define variável de ambiente para banco de testes antes de importar o app.
Requer banco MySQL/MariaDB acessível (Docker ou local) para testes de integração.
"""
import os
import sys

# Apontar para banco de testes antes de qualquer import do app
_TEST_DB = os.environ.get(
    "TEST_MYSQL_CONFIG",
    "mysql://root:granpix@127.0.0.1:3307/granpix_test"
)
os.environ["MYSQL_CONFIG"] = _TEST_DB

# Garantir que o projeto está no path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# App carregado sob demanda no fixture client (evita travar collection se o banco estiver down)
_app_obj = None
_skip_reason = "App não carregado"
APP_AVAILABLE = False  # Atualizado por _get_app() na primeira chamada


def _get_app():
    """Importa e retorna o app; usa cache. Em caso de erro, retorna None."""
    global _app_obj, _skip_reason, APP_AVAILABLE
    if _app_obj is not None:
        return _app_obj
    try:
        from app import app as a
        a.config["TESTING"] = True
        _app_obj = a
        APP_AVAILABLE = True
        return _app_obj
    except Exception as e:
        _skip_reason = f"App não disponível (banco?): {e}"
        return None


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: testes que exigem app e banco (deseja com -m 'not integration')"
    )
    config.addinivalue_line(
        "markers", "e2e: testes E2E no navegador (app deve estar rodando em localhost:5000)"
    )


import pytest


@pytest.fixture
def client():
    """Cliente de teste Flask. Skip se o app não carregar (banco indisponível)."""
    app = _get_app()
    if app is None:
        pytest.skip(_skip_reason)
    return app.test_client()


@pytest.fixture
def client_admin(client):
    """Cliente com sessão de admin logado."""
    with client.session_transaction() as sess:
        sess["admin"] = True
        sess["tipo"] = "admin"
    return client


@pytest.fixture
def client_equipe(client):
    """Cliente com sessão de equipe. Usar TEST_EQUIPE_ID no env para ID real."""
    equipe_id = os.environ.get("TEST_EQUIPE_ID", "")
    with client.session_transaction() as sess:
        sess["equipe_id"] = equipe_id
        sess["equipe_nome"] = "Equipe Teste"
        sess["tipo"] = "equipe"
    return client
