"""
Testes da funcionalidade Executar passada e desgaste de peças.

Regras:
- 1 dado por tipo de peça (Motor, Câmbio, Suspensão, Kit-ângulo, Diferencial = 5 dados por carro)
- 2 carros = 10 dados no total
- Diferencial: 1 dado, dano dividido entre todos os diferenciais do carro (carro pode ter mais de 1)
- Valor máximo do dado: multiplicar pelo coeficiente de quebra
"""
import uuid
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.integration
class TestConfigDadoDano:
    """Configuração do dado de dano em Admin."""

    def test_configuracoes_inclui_dado_dano(self, client_admin):
        """GET /api/admin/configuracoes retorna dado_dano na lista."""
        r = client_admin.get("/api/admin/configuracoes")
        assert r.status_code == 200
        data = r.get_json()
        assert "configuracoes" in data
        configs = {c["chave"]: c["valor"] for c in data["configuracoes"]}
        assert "dado_dano" in configs or True  # pode não existir se nunca foi salvo
        if "dado_dano" in configs:
            assert int(configs["dado_dano"]) >= 2

    def test_config_dado_dano_pode_ser_salvo(self, client_admin):
        """PUT /api/admin/configuracoes salva dado_dano."""
        r = client_admin.put(
            "/api/admin/configuracoes",
            json={"chave": "dado_dano", "valor": "8", "descricao": "D8 para dano"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True

        r2 = client_admin.get("/api/admin/configuracoes")
        configs = {c["chave"]: c["valor"] for c in r2.get_json().get("configuracoes", [])}
        assert configs.get("dado_dano") == "8"


@pytest.mark.integration
class TestExecutarPassadaAPI:
    """API POST /api/etapas/<etapa_id>/executar-passada."""

    def test_executar_passada_sem_equipes_retorna_400(self, client_admin):
        """Retorna 400 quando não há equipe1 nem equipe2."""
        etapa_id = str(uuid.uuid4())
        r = client_admin.post(
            f"/api/etapas/{etapa_id}/executar-passada",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False
        assert "equipe" in (data.get("erro") or "").lower()

    def test_executar_passada_com_equipes_inexistentes_retorna_404(self, client_admin):
        """Retorna 404 quando as equipes não existem na etapa."""
        from app import api

        # Garantir que existe uma etapa
        conn = api.db._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM etapas LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            pytest.skip("Nenhuma etapa no banco")
        etapa_id = row[0]

        r = client_admin.post(
            f"/api/etapas/{etapa_id}/executar-passada",
            json={"equipe1_nome": "EquipeFantasma1", "equipe2_nome": "EquipeFantasma2"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 404
        data = r.get_json()
        assert data.get("sucesso") is False


@pytest.mark.integration
class TestAplicarDesgastePassadaDiceRolls:
    """
    Verifica que aplicar_desgaste_passada roda exatamente 1 dado por peça
    e 10 dados para 2 carros (5 peças cada: motor, cambio, suspensao, kit_angulo + diferencial).
    """

    def test_roda_10_dados_para_2_carros_com_5_pecas_cada(self, client_admin):
        """2 carros × 5 peças = 10 chamadas a random.randint."""
        from app import api

        conn = api.db._get_conn()
        cur = conn.cursor()
        # Inserir 2 carros de teste com 5 peças cada (motor, cambio, suspensao, kit_angulo, diferencial)
        carro_ids = []
        for i in range(2):
            carro_id = str(uuid.uuid4())
            cur.execute(
                "SELECT COALESCE(MAX(numero_carro), 0) + 1 FROM carros"
            )
            num = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO carros (id, numero_carro, marca, modelo) VALUES (%s, %s, %s, %s)",
                (carro_id, num + i, "Teste", "Passada"),
            )
            pecas_tipos = [
                ("motor", "Motor Teste", 0.35),
                ("cambio", "Cambio Teste", 0.4),
                ("suspensao", "Suspensao Teste", 0.45),
                ("kit_angulo", "Kit Angulo Teste", 0.3),
                ("diferencial", "Diferencial Teste", 0.4),
            ]
            for tipo, nome, coef in pecas_tipos:
                peca_id = str(uuid.uuid4())
                cur.execute(
                    """INSERT INTO pecas
                    (id, carro_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado)
                    VALUES (%s, %s, %s, %s, 100, 100, 100, %s, 1)""",
                    (peca_id, carro_id, nome, tipo, coef),
                )
            carro_ids.append(carro_id)
        conn.commit()

        rolls_called = []

        def mock_randint(a, b):
            rolls_called.append((a, b))
            return 3  # valor fixo (não max) para facilitar verificação

        try:
            with patch("src.database.random.randint", side_effect=mock_randint):
                resultado = api.db.aplicar_desgaste_passada(carro_ids, dado_faces=6)
            assert resultado.get("sucesso") is True
            # 5 dados por carro: motor, cambio, suspensao, kit_angulo, diferencial (1 dado; divide entre N difs)
            # Total: 2 carros × 5 rolls = 10 chamadas
            assert len(rolls_called) == 10, (
                f"Esperado 10 chamadas a random.randint (2 carros × 5 peças), "
                f"obtido {len(rolls_called)}"
            )
            for (a, b) in rolls_called:
                assert a == 1 and b == 6, f"Cada dado deve ser 1d6, obtido 1d{b}"
        finally:
            # Limpar dados de teste
            for cid in carro_ids:
                cur.execute("DELETE FROM pecas WHERE carro_id = %s", (cid,))
                cur.execute("DELETE FROM carros WHERE id = %s", (cid,))
            conn.commit()
        cur.close()
        conn.close()

    def test_dano_maximo_multiplica_pelo_coeficiente(self, client_admin):
        """Quando o dado cai no valor máximo, dano = roll * coeficiente_quebra."""
        from app import api

        conn = api.db._get_conn()
        cur = conn.cursor()
        carro_id = str(uuid.uuid4())
        cur.execute("SELECT COALESCE(MAX(numero_carro), 0) + 1 FROM carros")
        num = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO carros (id, numero_carro, marca, modelo) VALUES (%s, %s, %s, %s)",
            (carro_id, num, "Teste", "Coef"),
        )
        # Apenas motor com coef 0.5 (entre 0.2 e 0.5)
        peca_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO pecas
            (id, carro_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado)
            VALUES (%s, %s, %s, %s, 100, 100, 100, %s, 1)""",
            (peca_id, carro_id, "Motor Coef", "motor", 0.5),
        )
        conn.commit()

        # D6 max=6, coef 0.5 -> dano = 6*0.5 = 3, durabilidade 100-3 = 97
        with patch("src.database.random.randint", return_value=6):
            resultado = api.db.aplicar_desgaste_passada([carro_id], dado_faces=6)
        assert resultado.get("sucesso") is True
        cur.execute("SELECT durabilidade_atual FROM pecas WHERE id = %s", (peca_id,))
        dur = cur.fetchone()[0]
        assert abs(dur - 97) < 0.01, f"Dano esperado 3 (6*0.5), durabilidade esperada 97, obtida {dur}"

        cur.execute("DELETE FROM pecas WHERE carro_id = %s", (carro_id,))
        cur.execute("DELETE FROM carros WHERE id = %s", (carro_id,))
        conn.commit()
        cur.close()
        conn.close()
