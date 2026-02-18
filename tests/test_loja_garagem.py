"""Testes de endpoints de loja e garagem."""
import pytest


class TestLojaCarros:
    """GET /api/loja/carros (pode exigir auth em alguns casos)."""

    def test_loja_carros_returns_200_or_401(self, client):
        r = client.get("/api/loja/carros")
        # Se for público retorna 200; se exige auth retorna 401
        assert r.status_code in (200, 401)
        if r.status_code == 200:
            data = r.get_json()
            assert isinstance(data, (list, dict)) or data is None

    def test_loja_carros_with_header(self, client):
        r = client.get(
            "/api/loja/carros",
            headers={"X-Equipe-ID": "00000000-0000-0000-0000-000000000001"},
        )
        assert r.status_code in (200, 401, 404)


class TestLojaPecas:
    """GET /api/loja/pecas."""

    def test_loja_pecas_returns_200_or_401(self, client):
        r = client.get("/api/loja/pecas")
        assert r.status_code in (200, 401)
        if r.status_code == 200:
            data = r.get_json()
            assert isinstance(data, (list, dict)) or data is None


class TestGaragemArmazem:
    """Garagem e armazém exigem autenticação."""

    def test_garagem_without_auth_401(self, client):
        r = client.get("/api/garagem/00000000-0000-0000-0000-000000000001")
        assert r.status_code == 401

    def test_armazem_without_auth_401(self, client):
        r = client.get("/api/armazem/00000000-0000-0000-0000-000000000001")
        assert r.status_code == 401
