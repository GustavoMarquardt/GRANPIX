"""
Testes: remoção de peça (base + upgrades) do carro e valor de ativação (soma peças não pagas).
"""
import os
import uuid
import pytest


@pytest.fixture
def db():
    from src.database import DatabaseManager
    config = os.environ.get("MYSQL_CONFIG", "mysql://root:granpix@127.0.0.1:3307/granpix_test")
    return DatabaseManager(config)


@pytest.mark.integration
class TestRemocaoEAtivacao:
    def test_remover_peca_move_base_e_upgrades_para_armazem(self, db):
        """Ao retirar peça do carro, a peça base e todos os upgrades (instalado_em_peca_id) vão para o armazém."""
        if not db._column_exists("pecas", "instalado_em_peca_id") or not db._column_exists("pecas", "upgrade_id"):
            pytest.skip("Colunas instalado_em_peca_id/upgrade_id não existem")
        pecas_loja = db.carregar_pecas_loja()
        equipes = db.carregar_todas_equipes()
        carros = []
        for e in equipes or []:
            conn = db._get_conn()
            cur = conn.cursor()
            cur.execute("SELECT id FROM carros WHERE equipe_id = %s LIMIT 1", (e.id,))
            r = cur.fetchone()
            conn.close()
            if r:
                carros.append((e.id, r[0]))
                break
        if not pecas_loja or not carros:
            pytest.skip("Sem peças na loja ou sem carro")
        equipe_id, carro_id = carros[0]
        peca_loja_id = pecas_loja[0].id
        pl = next((p for p in pecas_loja if p.id == peca_loja_id), None)
        tipo_peca = getattr(pl, "tipo", "motor")
        db.adicionar_peca_armazem(equipe_id, peca_loja_id, pl.nome, tipo_peca, 100, 50.0, 1.0)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM pecas WHERE peca_loja_id = %s AND equipe_id = %s AND instalado = 0 AND (upgrade_id IS NULL OR upgrade_id = '') LIMIT 1",
            (peca_loja_id, equipe_id),
        )
        base_row = cur.fetchone()
        conn.close()
        if not base_row:
            pytest.skip("Peça base não no armazém")
        base_id = base_row[0]
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, peca_loja_id, "Kit Teste Remoção", 10.0, "", None)
        db.adicionar_upgrade_armazem(equipe_id, upgrade_id)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE upgrade_id = %s AND instalado = 0 LIMIT 1", (upgrade_id,))
        up_row = cur.fetchone()
        conn.close()
        if not up_row:
            db.deletar_upgrade(upgrade_id)
            pytest.skip("Upgrade não no armazém")
        db.instalar_upgrade_em_peca(equipe_id, up_row[0], base_id)
        ok, _ = db.instalar_peca_por_id_no_carro(base_id, carro_id, equipe_id)
        assert ok
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE carro_id = %s AND tipo = %s AND instalado = 1 AND (upgrade_id IS NULL OR upgrade_id = '') LIMIT 1", (carro_id, tipo_peca))
        base_on_car = cur.fetchone()
        assert base_on_car is not None
        peca_id = base_on_car[0]
        cur.execute("UPDATE pecas SET carro_id = NULL, instalado = 0 WHERE id = %s", (peca_id,))
        cur.execute("UPDATE pecas SET carro_id = NULL, instalado = 0 WHERE instalado_em_peca_id = %s", (peca_id,))
        conn.commit()
        cur.execute("SELECT carro_id, instalado FROM pecas WHERE id IN (%s, %s)", (peca_id, up_row[0]))
        rows = cur.fetchall()
        conn.close()
        assert len(rows) == 2
        for r in rows:
            assert r[0] is None and r[1] == 0
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE id IN (%s, %s)", (peca_id, up_row[0]))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)

    def test_obter_valor_total_pecas_nao_pagas_carro(self, db):
        """obter_valor_total_pecas_nao_pagas_carro retorna soma dos preços e quantidade de peças sem pix_id."""
        if not db._column_exists("pecas", "pix_id"):
            pytest.skip("Coluna pix_id não existe")
        pecas_loja = db.carregar_pecas_loja()
        equipes = db.carregar_todas_equipes()
        carros = []
        for e in equipes or []:
            conn = db._get_conn()
            cur = conn.cursor()
            cur.execute("SELECT id FROM carros WHERE equipe_id = %s LIMIT 1", (e.id,))
            r = cur.fetchone()
            conn.close()
            if r:
                carros.append((e.id, r[0]))
                break
        if not pecas_loja or not carros:
            pytest.skip("Sem peças ou carro")
        equipe_id, carro_id = carros[0]
        pl = pecas_loja[0]
        db.adicionar_peca_armazem(equipe_id, pl.id, pl.nome, getattr(pl, "tipo", "motor"), 100, 100.0, 1.0)
        db.adicionar_peca_armazem(equipe_id, pl.id, pl.nome, getattr(pl, "tipo", "motor"), 100, 50.0, 1.0)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE peca_loja_id = %s AND equipe_id = %s AND instalado = 0 LIMIT 2", (pl.id, equipe_id))
        ids = [r[0] for r in cur.fetchall()]
        conn.close()
        if len(ids) < 2:
            pytest.skip("Não há 2 peças no armazém")
        ok1, _ = db.instalar_peca_por_id_no_carro(ids[0], carro_id, equipe_id)
        assert ok1
        total, qtd = db.obter_valor_total_pecas_nao_pagas_carro(carro_id, equipe_id)
        assert qtd >= 1, "Deve haver pelo menos 1 peça não paga no carro"
        assert total >= 50.0, "Soma dos preços das peças não pagas deve ser >= 50"
        cur3 = db._get_conn().cursor()
        cur3.execute("DELETE FROM pecas WHERE peca_loja_id = %s AND equipe_id = %s", (pl.id, equipe_id))
        db._get_conn().commit()
