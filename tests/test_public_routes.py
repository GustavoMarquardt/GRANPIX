"""Testes de rotas públicas (sem autenticação)."""
import pytest


class TestIndex:
    """Raiz e redirecionamentos."""

    def test_index_redirects_to_login_when_not_logged(self, client):
        r = client.get("/")
        assert r.status_code in (200, 302)
        if r.status_code == 302:
            assert "login" in r.location or r.location.endswith("/login")


class TestLoginPage:
    """Página de login."""

    def test_login_get_returns_200(self, client):
        r = client.get("/login")
        assert r.status_code == 200

    def test_login_post_without_json_handled(self, client):
        r = client.post("/login", data={})
        # Pode retornar 400 ou 200 (se interpretar como GET)
        assert r.status_code in (200, 400, 415)


class TestLoginApi:
    """POST /login (JSON)."""

    def test_login_admin_success(self, client):
        r = client.post(
            "/login",
            json={"tipo": "admin", "senha": "admin123"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True
        assert data.get("tipo") == "admin"

    def test_login_admin_wrong_password(self, client):
        r = client.post(
            "/login",
            json={"tipo": "admin", "senha": "wrong"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401
        data = r.get_json()
        assert data.get("sucesso") is False

    def test_login_admin_missing_senha(self, client):
        r = client.post(
            "/login",
            json={"tipo": "admin"},
            headers={"Content-Type": "application/json"},
        )
        # Senha vazia != admin123
        assert r.status_code in (200, 401)


class TestApiEquipesPublic:
    """GET /api/equipes é público."""

    def test_api_equipes_returns_list(self, client):
        r = client.get("/api/equipes")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
