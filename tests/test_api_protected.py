"""Testes de rotas de API que exigem autenticação."""
import pytest


class TestApiComAuth:
    """Rotas que exigem session ou header X-Equipe-ID."""

    def test_api_equipes_id_without_auth_returns_401(self, client):
        r = client.get("/api/equipes/00000000-0000-0000-0000-000000000001")
        assert r.status_code == 401

    def test_api_equipes_id_with_header_accept(self, client):
        # Com header de equipe inválida ainda pode retornar 403 ou 404
        r = client.get(
            "/api/equipes/00000000-0000-0000-0000-000000000001",
            headers={"X-Equipe-ID": "00000000-0000-0000-0000-000000000001"},
        )
        assert r.status_code in (200, 403, 404)

    def test_api_comprar_without_auth_returns_401(self, client):
        r = client.post(
            "/api/comprar",
            json={"tipo": "carro", "item_id": "algum-id"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401

    def test_api_comprar_with_auth_invalid_tipo(self, client_equipe):
        # Com sessão de equipe; tipo inválido ou item inexistente
        r = client_equipe.post(
            "/api/comprar",
            json={"tipo": "invalido"},
            headers={"Content-Type": "application/json"},
        )
        # 400 tipo inválido, 401 se equipe_id vazio, 404 se equipe não existe
        assert r.status_code in (400, 401, 404)


class TestApiAdmin:
    """Rotas admin (session admin)."""

    def test_api_user_is_admin_with_admin_session(self, client_admin):
        r = client_admin.get("/api/user/is-admin")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("is_admin") is True
