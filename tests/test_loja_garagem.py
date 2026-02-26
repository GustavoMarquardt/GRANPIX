"""Testes de endpoints de loja e garagem."""
import pytest
import uuid


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


class TestRecuperarPecaGaragem:
    """POST /api/garagem/recuperar-peca - Recuperar vida da peça para 100%."""

    def test_recuperar_peca_without_auth_401(self, client):
        r = client.post(
            "/api/garagem/recuperar-peca",
            json={"peca_id": "algum-id"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401

    def test_recuperar_peca_sem_peca_id_400(self, client, client_admin):
        """Sem peca_id retorna 400."""
        r_eq = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={"nome": "Eq Rec Test", "senha": "s1", "doricoins": 5000, "serie": "A"},
        )
        if r_eq.status_code != 200:
            pytest.skip("Banco não disponível")
        eq = r_eq.get_json()
        equipe_id = eq.get("equipe", {}).get("id") or eq.get("id")
        with client.session_transaction() as sess:
            sess["equipe_id"] = equipe_id
            sess["equipe_nome"] = "Eq Rec Test"
            sess["tipo"] = "equipe"
        r = client.post(
            "/api/garagem/recuperar-peca",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert "peca_id" in (data.get("erro") or "").lower()

    def test_recuperar_peca_ok(self, client, client_admin):
        """Recupera peça danificada: custo = metade do preço na loja."""
        from app import api

        modelos = api.db.carregar_modelos_loja()
        modelo = modelos[0] if modelos else None
        if not modelo:
            pytest.skip("Nenhum modelo no banco")
        pl_id = str(uuid.uuid4())
        try:
            conn = api.db._get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT IGNORE INTO pecas_loja (id, nome, tipo, preco) VALUES (%s, %s, %s, %s)",
                (pl_id, "Motor Test Recuperar", "motor", 1000.0),
            )
            conn.commit()
            conn.close()
        except Exception:
            pytest.skip("Inserir peças_loja falhou")

        r_eq = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={
                "nome": "Eq Recuperar " + uuid.uuid4().hex[:6],
                "senha": "s1",
                "doricoins": 10000,
                "serie": "A",
                "carro_id": modelo.id,
            },
        )
        if r_eq.status_code != 200:
            pytest.skip("Cadastrar equipe falhou")
        eq = r_eq.get_json()
        equipe_id = eq.get("equipe", {}).get("id") or eq.get("id")
        equipe = api.db.carregar_equipe(equipe_id)
        if not equipe or not equipe.carros:
            pytest.skip("Equipe/carro não criado")
        carro = equipe.carros[0]
        pecas = api.db.obter_pecas_carro_com_compatibilidade(carro.id)
        if not pecas:
            pytest.skip("Nenhuma peça no carro")
        motor = next((p for p in pecas if p.get("tipo") == "motor"), pecas[0])
        peca_id = motor["id"]

        try:
            conn = api.db._get_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE pecas SET durabilidade_atual = 50, peca_loja_id = %s, preco = 1000 WHERE id = %s",
                (pl_id, peca_id),
            )
            conn.commit()
            conn.close()
        except Exception:
            pytest.skip("Atualizar peça falhou")

        with client.session_transaction() as sess:
            sess["equipe_id"] = equipe_id
            sess["equipe_nome"] = "Eq Recuperar"
            sess["tipo"] = "equipe"
        r = client.post(
            "/api/garagem/recuperar-peca",
            json={"peca_id": peca_id},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data.get("sucesso") is True
        assert data.get("custo") == 500.0

        pecas_depois = api.db.obter_pecas_carro_com_compatibilidade(carro.id)
        motor_depois = next((p for p in pecas_depois if p["id"] == peca_id), None)
        assert motor_depois is not None
        assert motor_depois["durabilidade_atual"] == 100

        eq_depois = api.db.carregar_equipe(equipe_id)
        assert eq_depois.doricoins == 10000 - 500
