"""
Testes para: (1) desgaste só em peças base (upgrades não recebem dano);
(2) retífica com custo = (peça + upgrades) / 2 e apenas peça base recuperável.
"""
import uuid

import pytest


@pytest.mark.integration
class TestDesgasteApenasPecasBase:
    """aplicar_desgaste_passada deve aplicar dano só em peças base; upgrades não sofrem desgaste."""

    def test_upgrade_nao_recebe_dano_na_passada(self):
        """Carro com motor (base) e um upgrade instalado no motor: só o motor perde durabilidade."""
        from app import api

        if not api.db._column_exists("pecas", "upgrade_id") or not api.db._column_exists(
            "pecas", "instalado_em_peca_id"
        ):
            pytest.skip("Colunas upgrade_id/instalado_em_peca_id não existem")

        conn = api.db._get_conn()
        cur = conn.cursor()

        pl_id = str(uuid.uuid4())
        try:
            cur.execute(
                "INSERT INTO pecas_loja (id, nome, tipo, preco) VALUES (%s, %s, %s, %s)",
                (pl_id, "Motor PL Desgaste", "motor", 50.0),
            )
            conn.commit()
        except Exception:
            conn.close()
            pytest.skip("Inserir pecas_loja falhou")

        tbl_ul = "upgrade_loja" if api.db._table_exists("upgrade_loja") else "upgrades"
        col_base = "peca_base" if api.db._table_exists("upgrade_loja") else "peca_loja_id"
        upgrade_loja_id = str(uuid.uuid4())
        try:
            cur.execute(
                f"INSERT INTO {tbl_ul} (id, {col_base}, nome, preco) VALUES (%s, %s, %s, %s)",
                (upgrade_loja_id, pl_id, "Kit Upgrade Desgaste", 20.0),
            )
            conn.commit()
        except Exception:
            cur.execute("DELETE FROM pecas_loja WHERE id = %s", (pl_id,))
            conn.commit()
            conn.close()
            pytest.skip(f"Inserir {tbl_ul} falhou")

        carro_id = str(uuid.uuid4())
        cur.execute("SELECT COALESCE(MAX(numero_carro), 0) + 1 FROM carros")
        num = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO carros (id, numero_carro, marca, modelo) VALUES (%s, %s, %s, %s)",
            (carro_id, num, "Teste", "DesgasteUpgrade"),
        )

        motor_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO pecas
            (id, carro_id, peca_loja_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado)
            VALUES (%s, %s, %s, %s, %s, 100, 100, 50, 1.0, 1)""",
            (motor_id, carro_id, pl_id, "Motor Base", "motor"),
        )

        upgrade_peca_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO pecas
            (id, carro_id, peca_loja_id, upgrade_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado, instalado_em_peca_id)
            VALUES (%s, %s, %s, %s, %s, %s, 100, 100, 20, 1.0, 1, %s)""",
            (upgrade_peca_id, carro_id, pl_id, upgrade_loja_id, "Kit Upgrade", "motor", motor_id),
        )
        conn.commit()

        try:
            with __import__("unittest.mock").patch("src.database.random.randint", return_value=5):
                resultado = api.db.aplicar_desgaste_passada([carro_id], dado_faces=6)
            assert resultado.get("sucesso") is True

            cur.execute("SELECT durabilidade_atual FROM pecas WHERE id = %s", (motor_id,))
            dur_motor = cur.fetchone()[0]
            cur.execute("SELECT durabilidade_atual FROM pecas WHERE id = %s", (upgrade_peca_id,))
            dur_upgrade = cur.fetchone()[0]

            assert abs(float(dur_motor) - 95) < 0.01, (
                f"Motor base deve ter sofrido desgaste (esperado ~95), obtido {dur_motor}"
            )
            assert abs(float(dur_upgrade) - 100) < 0.01, (
                f"Upgrade não deve sofrer desgaste (esperado 100), obtido {dur_upgrade}"
            )
        finally:
            cur.execute("DELETE FROM pecas WHERE carro_id = %s OR id IN (%s, %s)", (carro_id, upgrade_peca_id, motor_id))
            cur.execute("DELETE FROM carros WHERE id = %s", (carro_id,))
            cur.execute(f"DELETE FROM {tbl_ul} WHERE id = %s", (upgrade_loja_id,))
            cur.execute("DELETE FROM pecas_loja WHERE id = %s", (pl_id,))
            conn.commit()
        cur.close()
        conn.close()


@pytest.mark.integration
class TestRetificaCustoPeçaMaisUpgrades:
    """recuperar_peca_vida (retífica): custo = (peça + upgrades) / 2; só peça base pode ser recuperada."""

    def test_retifica_custo_peca_sem_upgrades_metade_preco(self, client, client_admin):
        """Peça base sem upgrades: custo = preço_loja / 2 (comportamento já existente)."""
        from app import api

        modelos = api.db.carregar_modelos_loja()
        if not modelos:
            pytest.skip("Nenhum modelo no banco")
        pl_id = str(uuid.uuid4())
        try:
            conn = api.db._get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT IGNORE INTO pecas_loja (id, nome, tipo, preco) VALUES (%s, %s, %s, %s)",
                (pl_id, "Motor Retífica Sem Up", "motor", 800.0),
            )
            conn.commit()
            conn.close()
        except Exception:
            pytest.skip("Inserir peças_loja falhou")

        r_eq = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={
                "nome": "Eq Retífica " + uuid.uuid4().hex[:6],
                "senha": "s1",
                "doricoins": 5000,
                "serie": "A",
                "carro_id": modelos[0].id,
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
                "UPDATE pecas SET durabilidade_atual = 50, peca_loja_id = %s, preco = 800 WHERE id = %s",
                (pl_id, peca_id),
            )
            conn.commit()
            conn.close()
        except Exception:
            pytest.skip("Atualizar peça falhou")

        with client.session_transaction() as sess:
            sess["equipe_id"] = equipe_id
            sess["equipe_nome"] = "Eq Retífica"
            sess["tipo"] = "equipe"
        r = client.post(
            "/api/garagem/recuperar-peca",
            json={"peca_id": peca_id},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data.get("sucesso") is True
        # Sem upgrades: custo = 800 / 2 = 400
        assert data.get("custo") == 400.0

        pecas_depois = api.db.obter_pecas_carro_com_compatibilidade(carro.id)
        motor_depois = next((p for p in pecas_depois if p["id"] == peca_id), None)
        assert motor_depois is not None
        assert motor_depois["durabilidade_atual"] == 100
        try:
            conn = api.db._get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM pecas_loja WHERE id = %s", (pl_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def test_retifica_custo_peca_com_upgrades_soma_sobre_dois(self, client, client_admin):
        """Peça base com upgrades instalados: custo = (preço_peça + soma preço upgrades) / 2."""
        from app import api

        if not api.db._column_exists("pecas", "instalado_em_peca_id"):
            pytest.skip("Coluna instalado_em_peca_id não existe")

        modelos = api.db.carregar_modelos_loja()
        if not modelos:
            pytest.skip("Nenhum modelo no banco")
        pl_id = str(uuid.uuid4())
        try:
            conn = api.db._get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT IGNORE INTO pecas_loja (id, nome, tipo, preco) VALUES (%s, %s, %s, %s)",
                (pl_id, "Motor Retífica Up", "motor", 1000.0),
            )
            conn.commit()
            conn.close()
        except Exception:
            pytest.skip("Inserir peças_loja falhou")

        r_eq = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={
                "nome": "Eq Ret Up " + uuid.uuid4().hex[:6],
                "senha": "s1",
                "doricoins": 10000,
                "serie": "A",
                "carro_id": modelos[0].id,
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
        peca_base_id = motor["id"]

        # Atualizar peça base para nosso peca_loja e danificar
        conn = api.db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE pecas SET durabilidade_atual = 60, peca_loja_id = %s, preco = 1000 WHERE id = %s",
            (pl_id, peca_base_id),
        )
        conn.commit()

        # Inserir 2 upgrades "instalados" nesta peça (instalado_em_peca_id = peca_base_id)
        up_id_1 = str(uuid.uuid4())
        up_id_2 = str(uuid.uuid4())
        cols = "id, carro_id, peca_loja_id, upgrade_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado, instalado_em_peca_id"
        vals = "%s, %s, %s, %s, %s, %s, 100, 100, 100, 1.0, 1, %s"
        if api.db._column_exists("pecas", "equipe_id"):
            cols += ", equipe_id"
            vals += ", %s"
        cur.execute(
            f"INSERT INTO pecas ({cols}) VALUES ({vals})",
            (up_id_1, carro.id, pl_id, up_id_1, "Upgrade A", "motor", peca_base_id)
            + ((equipe_id,) if "equipe_id" in cols else ()),
        )
        vals2 = "%s, %s, %s, %s, %s, %s, 100, 100, 200, 1.0, 1, %s" + (", %s" if "equipe_id" in cols else "")
        cur.execute(
            f"INSERT INTO pecas ({cols}) VALUES ({vals2})",
            (up_id_2, carro.id, pl_id, up_id_2, "Upgrade B", "motor", peca_base_id)
            + ((equipe_id,) if "equipe_id" in cols else ()),
        )
        conn.commit()
        conn.close()

        with client.session_transaction() as sess:
            sess["equipe_id"] = equipe_id
            sess["equipe_nome"] = "Eq Ret Up"
            sess["tipo"] = "equipe"
        r = client.post(
            "/api/garagem/recuperar-peca",
            json={"peca_id": peca_base_id},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_json()
        data = r.get_json()
        assert data.get("sucesso") is True
        # Custo = (1000 + 100 + 200) / 2 = 650
        assert data.get("custo") == 650.0, f"Esperado 650.0, obtido {data.get('custo')}"

        pecas_depois = api.db.obter_pecas_carro_com_compatibilidade(carro.id)
        motor_depois = next((p for p in pecas_depois if p["id"] == peca_base_id), None)
        assert motor_depois is not None
        assert motor_depois["durabilidade_atual"] == 100

        # Limpeza
        conn = api.db._get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM pecas WHERE id IN (%s, %s)", (up_id_1, up_id_2))
        cur.execute("DELETE FROM pecas_loja WHERE id = %s", (pl_id,))
        conn.commit()
        conn.close()

    def test_retifica_apenas_peca_base_upgrade_rejeitado(self, client, client_admin):
        """Passar id de um upgrade para recuperar-peca deve falhar (só peça base pode fazer retífica)."""
        from app import api

        if not api.db._column_exists("pecas", "upgrade_id") or not api.db._column_exists(
            "pecas", "instalado_em_peca_id"
        ):
            pytest.skip("Colunas upgrade_id/instalado_em_peca_id não existem")

        modelos = api.db.carregar_modelos_loja()
        if not modelos:
            pytest.skip("Nenhum modelo no banco")
        pl_id = str(uuid.uuid4())
        conn = api.db._get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT IGNORE INTO pecas_loja (id, nome, tipo, preco) VALUES (%s, %s, %s, %s)",
            (pl_id, "Motor Base Rej", "motor", 500.0),
        )
        conn.commit()

        r_eq = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={
                "nome": "Eq Rej " + uuid.uuid4().hex[:6],
                "senha": "s1",
                "doricoins": 5000,
                "serie": "A",
                "carro_id": modelos[0].id,
            },
        )
        if r_eq.status_code != 200:
            conn.close()
            pytest.skip("Cadastrar equipe falhou")
        eq = r_eq.get_json()
        equipe_id = eq.get("equipe", {}).get("id") or eq.get("id")
        equipe = api.db.carregar_equipe(equipe_id)
        if not equipe or not equipe.carros:
            conn.close()
            pytest.skip("Equipe/carro não criado")
        carro = equipe.carros[0]
        pecas = api.db.obter_pecas_carro_com_compatibilidade(carro.id)
        if not pecas:
            conn.close()
            pytest.skip("Nenhuma peça no carro")
        motor = next((p for p in pecas if p.get("tipo") == "motor"), pecas[0])
        peca_base_id = motor["id"]

        cur.execute(
            "UPDATE pecas SET peca_loja_id = %s WHERE id = %s",
            (pl_id, peca_base_id),
        )
        upgrade_peca_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO pecas (id, carro_id, peca_loja_id, upgrade_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado, instalado_em_peca_id)
            VALUES (%s, %s, %s, %s, %s, %s, 100, 80, 50, 1.0, 1, %s)""",
            (upgrade_peca_id, carro.id, pl_id, upgrade_peca_id, "Upgrade Rej", "motor", peca_base_id),
        )
        conn.commit()
        conn.close()

        with client.session_transaction() as sess:
            sess["equipe_id"] = equipe_id
            sess["equipe_nome"] = "Eq Rej"
            sess["tipo"] = "equipe"
        r = client.post(
            "/api/garagem/recuperar-peca",
            json={"peca_id": upgrade_peca_id},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is not True
        assert "não encontrada" in (data.get("erro") or "").lower() or "não instalada" in (
            data.get("erro") or ""
        ).lower()

        conn = api.db._get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM pecas WHERE id = %s", (upgrade_peca_id,))
        cur.execute("DELETE FROM pecas_loja WHERE id = %s", (pl_id,))
        conn.commit()
        conn.close()
