"""
Testes para upgrade_loja: compra de upgrade -> armazém, instalação em peça, exibição no card.
Requer banco de testes (integration).
"""
import os
import uuid
import pytest


@pytest.fixture
def db():
    """DatabaseManager do app."""
    from src.database import DatabaseManager
    config = os.environ.get("MYSQL_CONFIG", "mysql://root:granpix@127.0.0.1:3307/granpix_test")
    return DatabaseManager(config)


@pytest.mark.integration
class TestUpgradeLoja:
    """Testes de upgrade_loja: cadastro, compra, armazém, instalação e listagem no card."""

    def test_carregar_upgrades_usa_upgrade_loja_ou_upgrades(self, db):
        """carregar_upgrades retorna lista (pode ser vazia)."""
        lista = db.carregar_upgrades()
        assert isinstance(lista, list)

    def test_criar_upgrade_insere_em_upgrade_loja(self, db):
        """Criar upgrade insere em upgrade_loja (ou upgrades) com peca_base/peca_loja_id."""
        # Precisamos de pelo menos uma peça na loja
        pecas = db.carregar_pecas_loja()
        if not pecas:
            pytest.skip("Nenhuma peça na loja para vincular upgrade")
        peca_base_id = pecas[0].id
        upgrade_id = str(uuid.uuid4())
        ok = db.criar_upgrade(upgrade_id, peca_base_id, "Kit Teste", 100.0, "Desc teste", None)
        assert ok is True
        lista = db.carregar_upgrades()
        assert any(u["id"] == upgrade_id for u in lista)
        db.deletar_upgrade(upgrade_id)

    def test_buscar_upgrade_por_id_retorna_dict(self, db):
        """buscar_upgrade_por_id retorna dict com nome, preco, peca_tipo ou None."""
        pecas = db.carregar_pecas_loja()
        if not pecas:
            pytest.skip("Nenhuma peça na loja")
        uid = str(uuid.uuid4())
        db.criar_upgrade(uid, pecas[0].id, "Upgrade Busca", 50.0, "", None)
        u = db.buscar_upgrade_por_id(uid)
        assert u is not None
        assert u["nome"] == "Upgrade Busca"
        assert u["preco"] == 50.0
        db.deletar_upgrade(uid)

    def test_adicionar_upgrade_armazem_cria_peca_com_upgrade_id(self, db):
        """adicionar_upgrade_armazem insere linha em pecas com upgrade_id e equipe_id."""
        pecas_loja = db.carregar_pecas_loja()
        if not pecas_loja:
            pytest.skip("Sem peças na loja")
        equipes = db.carregar_todas_equipes()
        if not equipes:
            pytest.skip("Sem equipes")
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, pecas_loja[0].id, "Upgrade Armazém", 99.0, "", None)
        ok = db.adicionar_upgrade_armazem(equipes[0].id, upgrade_id)
        assert ok  # retorna peca_id (str) em sucesso
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, upgrade_id, equipe_id, instalado FROM pecas WHERE upgrade_id = %s",
            (upgrade_id,),
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[2] == equipes[0].id
        assert row[3] == 0
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE upgrade_id = %s", (upgrade_id,))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)

    def test_instalar_upgrade_em_peca_atualiza_instalado_em_peca_id(self, db):
        """Instalar upgrade em peça preenche instalado_em_peca_id e instalado=1."""
        if not db._column_exists("pecas", "instalado_em_peca_id"):
            pytest.skip("Coluna instalado_em_peca_id não existe")
        pecas_loja = db.carregar_pecas_loja()
        equipes = db.carregar_todas_equipes()
        carros = []
        for e in (equipes or []):
            conn = db._get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM carros WHERE equipe_id = %s LIMIT 1",
                (e.id,),
            )
            r = cur.fetchone()
            conn.close()
            if r:
                carros.append((e.id, r[0]))
                break
        if not carros:
            pytest.skip("Nenhum carro instalado para teste")
        equipe_id, carro_id = carros[0]
        # Peça base no carro (motor)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, peca_loja_id FROM pecas WHERE carro_id = %s AND instalado = 1 AND (upgrade_id IS NULL OR upgrade_id = '') LIMIT 1",
            (carro_id,),
        )
        base = cur.fetchone()
        conn.close()
        if not base:
            pytest.skip("Nenhuma peça base no carro")
        peca_alvo_id, peca_loja_id = base[0], base[1]
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, peca_loja_id, "Kit Instalar", 10.0, "", None)
        db.adicionar_upgrade_armazem(equipe_id, upgrade_id)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE upgrade_id = %s AND instalado = 0 LIMIT 1", (upgrade_id,))
        up_row = cur.fetchone()
        conn.close()
        if not up_row:
            db.deletar_upgrade(upgrade_id)
            pytest.skip("Upgrade não encontrado no armazém")
        peca_upgrade_id = up_row[0]
        ok, msg = db.instalar_upgrade_em_peca(equipe_id, peca_upgrade_id, peca_alvo_id)
        assert ok is True, msg
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT instalado_em_peca_id, instalado, carro_id FROM pecas WHERE id = %s",
            (peca_upgrade_id,),
        )
        row = cur.fetchone()
        conn.close()
        assert row[0] == peca_alvo_id
        assert row[1] == 1
        assert row[2] == carro_id
        pecas_carro = db.obter_pecas_carro_com_compatibilidade(carro_id)
        base_peca = next((p for p in pecas_carro if p["id"] == peca_alvo_id), None)
        assert base_peca is not None
        assert "upgrades" in base_peca
        assert any(u["nome"] == "Kit Instalar" for u in base_peca["upgrades"])
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE id = %s", (peca_upgrade_id,))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)

    def test_instalar_upgrade_em_peca_no_armazem(self, db):
        """Instalar upgrade em peça que está no armazém: upgrade fica com instalado_em_peca_id, instalado=0, carro_id=NULL."""
        if not db._column_exists("pecas", "instalado_em_peca_id"):
            pytest.skip("Coluna instalado_em_peca_id não existe")
        pecas_loja = db.carregar_pecas_loja()
        equipes = db.carregar_todas_equipes()
        if not pecas_loja or not equipes:
            pytest.skip("Sem peças na loja ou sem equipes")
        equipe_id = equipes[0].id
        peca_loja_id = pecas_loja[0].id
        pl = next((p for p in pecas_loja if p.id == peca_loja_id), None)
        tipo = getattr(pl, "tipo", "motor")
        db.adicionar_peca_armazem(equipe_id, peca_loja_id, pl.nome, tipo, 100, 50.0, 1.0)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM pecas WHERE peca_loja_id = %s AND equipe_id = %s AND instalado = 0 AND (upgrade_id IS NULL OR upgrade_id = '') LIMIT 1",
            (peca_loja_id, equipe_id),
        )
        base_row = cur.fetchone()
        conn.close()
        if not base_row:
            pytest.skip("Peça base não encontrada no armazém")
        peca_alvo_id = base_row[0]
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, peca_loja_id, "Kit Armazém", 25.0, "", None)
        db.adicionar_upgrade_armazem(equipe_id, upgrade_id)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE upgrade_id = %s AND instalado = 0 LIMIT 1", (upgrade_id,))
        up_row = cur.fetchone()
        conn.close()
        if not up_row:
            db.deletar_upgrade(upgrade_id)
            pytest.skip("Upgrade não no armazém")
        peca_upgrade_id = up_row[0]
        ok, msg = db.instalar_upgrade_em_peca(equipe_id, peca_upgrade_id, peca_alvo_id)
        assert ok is True, msg
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT instalado_em_peca_id, instalado, carro_id FROM pecas WHERE id = %s", (peca_upgrade_id,))
        row = cur.fetchone()
        conn.close()
        assert row[0] == peca_alvo_id
        assert row[1] == 0
        assert row[2] is None
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE id IN (%s, %s)", (peca_upgrade_id, peca_alvo_id))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)

    def test_exigir_alvo_no_carro_bloqueia_se_peca_no_armazem(self, db):
        """Com exigir_alvo_no_carro=True, se a peça alvo estiver no armazém retorna erro claro."""
        if not db._column_exists("pecas", "instalado_em_peca_id"):
            pytest.skip("Coluna instalado_em_peca_id não existe")
        pecas_loja = db.carregar_pecas_loja()
        equipes = db.carregar_todas_equipes()
        if not pecas_loja or not equipes:
            pytest.skip("Sem peças ou equipes")
        equipe_id = equipes[0].id
        peca_loja_id = pecas_loja[0].id
        pl = next((p for p in pecas_loja if p.id == peca_loja_id), None)
        db.adicionar_peca_armazem(equipe_id, peca_loja_id, pl.nome, getattr(pl, "tipo", "motor"), 100, 50.0, 1.0)
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
        peca_alvo_id = base_row[0]
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, peca_loja_id, "Kit Bloqueio", 10.0, "", None)
        db.adicionar_upgrade_armazem(equipe_id, upgrade_id)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE upgrade_id = %s AND instalado = 0 LIMIT 1", (upgrade_id,))
        up_row = cur.fetchone()
        conn.close()
        if not up_row:
            db.deletar_upgrade(upgrade_id)
            pytest.skip("Upgrade não no armazém")
        peca_upgrade_id = up_row[0]
        ok, msg = db.instalar_upgrade_em_peca(equipe_id, peca_upgrade_id, peca_alvo_id, exigir_alvo_no_carro=True)
        assert ok is False
        assert "peça base" in msg.lower() or "instalada no carro" in msg.lower()
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE id IN (%s, %s)", (peca_upgrade_id, peca_alvo_id))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)

    def test_obter_preco_total_peca_com_upgrades(self, db):
        """obter_preco_total_peca_com_upgrades retorna preço da peça + soma dos upgrades nela."""
        if not db._column_exists("pecas", "instalado_em_peca_id"):
            pytest.skip("Coluna instalado_em_peca_id não existe")
        pecas_loja = db.carregar_pecas_loja()
        equipes = db.carregar_todas_equipes()
        if not pecas_loja or not equipes:
            pytest.skip("Sem peças ou equipes")
        equipe_id = equipes[0].id
        peca_loja_id = pecas_loja[0].id
        pl = next((p for p in pecas_loja if p.id == peca_loja_id), None)
        db.adicionar_peca_armazem(equipe_id, peca_loja_id, pl.nome, getattr(pl, "tipo", "motor"), 100, 100.0, 1.0)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, preco FROM pecas WHERE peca_loja_id = %s AND equipe_id = %s AND instalado = 0 AND (upgrade_id IS NULL OR upgrade_id = '') LIMIT 1",
            (peca_loja_id, equipe_id),
        )
        base_row = cur.fetchone()
        conn.close()
        if not base_row:
            pytest.skip("Peça base não no armazém")
        peca_id, preco_base = base_row[0], float(base_row[1] or 0)
        total_sem_upgrade = db.obter_preco_total_peca_com_upgrades(peca_id)
        assert total_sem_upgrade == preco_base
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, peca_loja_id, "Upgrade Preço", 30.0, "", None)
        db.adicionar_upgrade_armazem(equipe_id, upgrade_id)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE upgrade_id = %s LIMIT 1", (upgrade_id,))
        up_row = cur.fetchone()
        conn.close()
        if up_row:
            ok, _ = db.instalar_upgrade_em_peca(equipe_id, up_row[0], peca_id)
            assert ok
            total_com_upgrade = db.obter_preco_total_peca_com_upgrades(peca_id)
            assert total_com_upgrade == preco_base + 30.0
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE peca_loja_id = %s OR upgrade_id = %s", (peca_loja_id, upgrade_id))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)

    def test_instalar_peca_por_id_no_carro_move_upgrades(self, db):
        """instalar_peca_por_id_no_carro instala a peça e todas com instalado_em_peca_id nela."""
        if not db._column_exists("pecas", "instalado_em_peca_id"):
            pytest.skip("Coluna instalado_em_peca_id não existe")
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
        db.adicionar_peca_armazem(equipe_id, peca_loja_id, pl.nome, getattr(pl, "tipo", "motor"), 100, 50.0, 1.0)
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
        peca_armazem_id = base_row[0]
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, peca_loja_id, "Kit Move", 15.0, "", None)
        db.adicionar_upgrade_armazem(equipe_id, upgrade_id)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE upgrade_id = %s AND instalado = 0 LIMIT 1", (upgrade_id,))
        up_row = cur.fetchone()
        conn.close()
        if not up_row:
            db.deletar_upgrade(upgrade_id)
            pytest.skip("Upgrade não no armazém")
        db.instalar_upgrade_em_peca(equipe_id, up_row[0], peca_armazem_id)
        ok, msg = db.instalar_peca_por_id_no_carro(peca_armazem_id, carro_id, equipe_id)
        assert ok is True, msg
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT instalado, carro_id FROM pecas WHERE id IN (%s, %s)", (peca_armazem_id, up_row[0]))
        rows = cur.fetchall()
        conn.close()
        assert len(rows) == 2
        for r in rows:
            assert r[0] == 1 and r[1] == carro_id
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE id IN (%s, %s)", (peca_armazem_id, up_row[0]))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)

    def test_instalar_peca_por_id_rejeita_upgrade(self, db):
        """instalar_peca_por_id_no_carro rejeita quando a peça é um upgrade (não pode instalar upgrade direto no carro)."""
        if not db._column_exists("pecas", "upgrade_id"):
            pytest.skip("Coluna upgrade_id não existe")
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
        peca_loja_id = pecas_loja[0].id
        pl = next((p for p in pecas_loja if p.id == peca_loja_id), None)
        upgrade_id = str(uuid.uuid4())
        db.criar_upgrade(upgrade_id, peca_loja_id, "Kit Rejeitar", 10.0, "", None)
        db.adicionar_upgrade_armazem(equipe_id, upgrade_id)
        conn = db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pecas WHERE upgrade_id = %s AND instalado = 0 LIMIT 1", (upgrade_id,))
        up_row = cur.fetchone()
        conn.close()
        if not up_row:
            db.deletar_upgrade(upgrade_id)
            pytest.skip("Upgrade não no armazém")
        ok, msg = db.instalar_peca_por_id_no_carro(up_row[0], carro_id, equipe_id)
        assert ok is False
        assert "upgrade" in msg.lower() or "peça base" in msg.lower()
        cur2 = db._get_conn().cursor()
        cur2.execute("DELETE FROM pecas WHERE upgrade_id = %s", (upgrade_id,))
        db._get_conn().commit()
        db.deletar_upgrade(upgrade_id)
