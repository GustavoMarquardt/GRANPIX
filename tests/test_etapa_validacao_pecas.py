"""
Testes para validação de inscrição em etapas:
- Equipe não pode participar sem carro ativo
- Equipe não pode participar sem todas as peças instaladas
- API batalhas-recentes retorna passadas
"""
import uuid

import pytest


class TestInscricaoCarroAtivoEPecas:
    """Valida que inscrição em etapa exige carro ativo e peças completas."""

    def test_inscrever_etapa_com_carro_em_repouso_rejeita(self, client_admin):
        """Equipe com carro em repouso não pode se inscrever na etapa."""
        from app import api

        nome = f"Etapa Repouso {uuid.uuid4().hex[:8]}"
        r_camp = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"nome": nome, "serie": "A", "numero_etapas": 3},
            headers={"Content-Type": "application/json"},
        )
        assert r_camp.status_code == 200
        campeonato_id = r_camp.get_json().get("campeonato_id")
        r_etapa = client_admin.post(
            "/api/admin/cadastrar-etapa",
            json={
                "campeonato_id": campeonato_id,
                "numero": 1,
                "nome": "Etapa Teste Repouso",
                "data_etapa": "2026-06-01",
                "hora_etapa": "10:00:00",
                "serie": "A",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_etapa.status_code == 200
        etapa_id = r_etapa.get_json().get("etapa_id")

        r_carro = client_admin.post(
            "/api/admin/cadastrar-carro",
            json={
                "marca": "Teste",
                "modelo": "Repouso",
                "preco": 5000,
                "classe": "basico",
                "descricao": "",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_carro.status_code == 200
        modelo_id = (r_carro.get_json().get("carro") or {}).get("id")

        r_eq = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={
                "nome": "Equipe Carro Repouso",
                "senha": "s1",
                "doricoins": 50000,
                "serie": "A",
                "carro_id": str(modelo_id),
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_eq.status_code == 200
        equipe = r_eq.get_json().get("equipe") or {}
        equipe_id = equipe.get("id")
        carro_id = equipe.get("carro_instancia_id") or equipe.get("carro_id")
        api.db.atualizar_saldo_pix(equipe_id, 5000.0)

        # Colocar carro em repouso
        conn = api.db._get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE carros SET status = %s WHERE id = %s", ("repouso", carro_id))
        conn.commit()
        cur.close()
        conn.close()

        r_part = client_admin.post(
            "/api/etapas/equipe/participar",
            json={
                "etapa_id": etapa_id,
                "equipe_id": equipe_id,
                "carro_id": carro_id,
                "tipo_participacao": "precisa_piloto",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_part.status_code == 400
        data = r_part.get_json()
        assert data.get("sucesso") is False
        assert "ativo" in (data.get("erro") or "").lower()

    def test_inscrever_etapa_sem_pecas_completas_rejeita(self, client_admin):
        """Equipe com carro sem todas as peças não pode se inscrever na etapa."""
        from app import api

        nome = f"Etapa Pecas {uuid.uuid4().hex[:8]}"
        r_camp = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"nome": nome, "serie": "A", "numero_etapas": 3},
            headers={"Content-Type": "application/json"},
        )
        assert r_camp.status_code == 200
        campeonato_id = r_camp.get_json().get("campeonato_id")
        r_etapa = client_admin.post(
            "/api/admin/cadastrar-etapa",
            json={
                "campeonato_id": campeonato_id,
                "numero": 1,
                "nome": "Etapa Teste Pecas",
                "data_etapa": "2026-06-02",
                "hora_etapa": "10:00:00",
                "serie": "A",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_etapa.status_code == 200
        etapa_id = r_etapa.get_json().get("etapa_id")

        r_carro = client_admin.post(
            "/api/admin/cadastrar-carro",
            json={
                "marca": "Teste",
                "modelo": "Incompleto",
                "preco": 5000,
                "classe": "basico",
                "descricao": "",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_carro.status_code == 200
        modelo_id = (r_carro.get_json().get("carro") or {}).get("id")

        r_eq = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={
                "nome": "Equipe Carro Incompleto",
                "senha": "s1",
                "doricoins": 50000,
                "serie": "A",
                "carro_id": str(modelo_id),
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_eq.status_code == 200
        equipe = r_eq.get_json().get("equipe") or {}
        equipe_id = equipe.get("id")
        carro_id = equipe.get("carro_instancia_id") or equipe.get("carro_id")
        api.db.atualizar_saldo_pix(equipe_id, 5000.0)

        # Remover peças instaladas do carro (deixar incompleto)
        conn = api.db._get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE pecas SET instalado = 0 WHERE carro_id = %s", (carro_id,))
        conn.commit()
        cur.close()
        conn.close()

        r_part = client_admin.post(
            "/api/etapas/equipe/participar",
            json={
                "etapa_id": etapa_id,
                "equipe_id": equipe_id,
                "carro_id": carro_id,
                "tipo_participacao": "precisa_piloto",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_part.status_code == 400
        data = r_part.get_json()
        assert data.get("sucesso") is False
        assert "peças" in (data.get("erro") or "").lower() or "pecas" in (data.get("erro") or "").lower()


class TestBatalhasRecentes:
    """API GET /api/etapas/<id>/batalhas-recentes"""

    def test_batalhas_recentes_requer_login(self, client):
        """Sem sessão retorna 401."""
        etapa_id = str(uuid.uuid4())
        r = client.get(f"/api/etapas/{etapa_id}/batalhas-recentes")
        assert r.status_code == 401

    def test_batalhas_recentes_com_admin_retorna_lista(self, client_admin):
        """Admin autenticado recebe lista de passadas (pode ser vazia)."""
        from app import api

        r_camp = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"nome": f"Camp Bat {uuid.uuid4().hex[:8]}", "serie": "A", "numero_etapas": 1},
            headers={"Content-Type": "application/json"},
        )
        assert r_camp.status_code == 200
        campeonato_id = r_camp.get_json().get("campeonato_id")
        r_etapa = client_admin.post(
            "/api/admin/cadastrar-etapa",
            json={
                "campeonato_id": campeonato_id,
                "numero": 1,
                "nome": "Etapa Bat",
                "data_etapa": "2026-06-01",
                "hora_etapa": "10:00:00",
                "serie": "A",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_etapa.status_code == 200
        etapa_id = r_etapa.get_json().get("etapa_id")

        r = client_admin.get(f"/api/etapas/{etapa_id}/batalhas-recentes")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True
        assert "passadas" in data
        assert isinstance(data["passadas"], list)
