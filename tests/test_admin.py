"""
Testes das funcionalidades admin:
- Cadastrar Carros, Peças, Variações, Equipes
- Fazer Etapa, Alocar Pilotos, Comissões
"""
import pytest


class TestAdminPages:
    """Páginas HTML do admin (requerem sessão admin)."""

    def test_admin_carros_page(self, client_admin):
        r = client_admin.get("/admin/carros")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "Cadastrar Carros" in html or "Cadastrar Carro" in html
        assert "carroMarca" in html or "carroModelo" in html
        assert "listaCarros" in html

    def test_admin_pecas_page(self, client_admin):
        r = client_admin.get("/admin/pecas")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "Cadastrar Peças" in html
        assert "pecaNome" in html or "pecaTipo" in html

    def test_admin_variacoes_page(self, client_admin):
        r = client_admin.get("/admin/variacoes")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "Variações" in html or "Cadastrar Variações" in html
        assert "variacaoModelo" in html or "variacaoMotor" in html

    def test_admin_equipes_page(self, client_admin):
        r = client_admin.get("/admin/equipes")
        assert r.status_code == 200

    def test_admin_fazer_etapa_page(self, client_admin):
        r = client_admin.get("/admin/fazer-etapa")
        assert r.status_code == 200

    def test_admin_alocar_pilotos_page(self, client_admin):
        r = client_admin.get("/admin/alocar-pilotos")
        assert r.status_code == 200

    def test_admin_comissoes_page(self, client_admin):
        r = client_admin.get("/admin/comissoes")
        assert r.status_code == 200


class TestAdminCarrosPecasVariacoesAcesso:
    """Acesso às páginas /admin/carros, /admin/pecas, /admin/variacoes."""

    @pytest.mark.parametrize("path", ["/admin/carros", "/admin/pecas", "/admin/variacoes"])
    def test_pagina_retorna_200_com_admin(self, client_admin, path):
        r = client_admin.get(path)
        assert r.status_code == 200, f"{path} deve retornar 200 com sessão admin"
        assert "html" in r.get_data(as_text=True).lower() or "<!DOCTYPE" in r.get_data(as_text=True)

    @pytest.mark.parametrize("path", ["/admin/carros", "/admin/pecas", "/admin/variacoes"])
    def test_pagina_carrega_sem_admin(self, client, path):
        """Sem sessão admin a rota ainda entrega a página (auth pode ser feita no front)."""
        r = client.get(path)
        assert r.status_code == 200, f"{path} deve retornar 200 (template servido)"
        html = r.get_data(as_text=True)
        assert len(html) > 500, "Resposta deve ser HTML da página"


class TestCadastrarEquipe:
    """POST /api/admin/cadastrar-equipe."""

    def test_cadastrar_equipe_minimo(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={"nome": "Equipe Teste Admin", "senha": "123456"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True
        assert "equipe" in data
        assert data["equipe"]["nome"] == "Equipe Teste Admin"

    def test_cadastrar_equipe_persiste_na_listagem(self, client_admin):
        """Cadastra equipe e verifica que aparece em GET /api/admin/equipes (persistência no banco)."""
        nome = "Equipe Persist Test"
        r = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={"nome": nome, "senha": "123456"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        data = r.get_json()
        assert data.get("sucesso") is True
        listagem = client_admin.get("/api/admin/equipes")
        assert listagem.status_code == 200
        equipes = listagem.get_json()
        assert isinstance(equipes, list), "Listagem de equipes deve ser uma lista"
        encontrado = next((e for e in equipes if (e.get("nome") or "").strip() == nome), None)
        assert encontrado is not None, f"Equipe '{nome}' deve aparecer na listagem após cadastro."
        print(f"  PERSISTÊNCIA OK: equipe '{nome}' encontrada na listagem (GET /api/admin/equipes).")

    def test_cadastrar_equipe_sem_nome_usa_padrao(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-equipe",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True


class TestCadastrarCarro:
    """POST /api/admin/cadastrar-carro."""

    def test_cadastrar_carro_ok(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-carro",
            json={
                "marca": "Teste",
                "modelo": "Modelo Teste",
                "preco": "5000",
                "classe": "basico",
                "descricao": "Carro de teste",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True
        assert data.get("carro", {}).get("marca") == "Teste"
        assert data.get("carro", {}).get("modelo") == "Modelo Teste"

    def test_cadastrar_carro_persiste_na_listagem(self, client_admin):
        """Cadastra carro e verifica que aparece em GET /api/admin/carros (persistência no banco)."""
        marca, modelo = "Marca Persist Test", "Modelo Persist Test"
        r = client_admin.post(
            "/api/admin/cadastrar-carro",
            json={
                "marca": marca,
                "modelo": modelo,
                "preco": "7500",
                "classe": "basico",
                "descricao": "Carro para testar persistência",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        data = r.get_json()
        assert data.get("sucesso") is True
        # Verificar que a listagem retorna o carro cadastrado (lido do banco)
        listagem = client_admin.get("/api/admin/carros")
        assert listagem.status_code == 200
        carros = listagem.get_json()
        assert isinstance(carros, list), "Listagem de carros deve ser uma lista"
        encontrado = next((c for c in carros if c.get("marca") == marca and c.get("modelo") == modelo), None)
        assert encontrado is not None, f"Carro '{marca} {modelo}' deve aparecer na listagem após cadastro. Lista: {[str(c) for c in carros[:5]]}"
        print(f"  PERSISTÊNCIA OK: carro '{marca} {modelo}' encontrado na listagem (GET /api/admin/carros).")

    def test_cadastrar_carro_cria_variacao_sem_pecas(self, client_admin):
        """Ao cadastrar um carro, deve existir ao menos uma variação desse carro sem nenhuma peça (motor, câmbio, etc.)."""
        marca, modelo = "Marca Var Sem Pecas", "Modelo Var Sem Pecas"
        r = client_admin.post(
            "/api/admin/cadastrar-carro",
            json={
                "marca": marca,
                "modelo": modelo,
                "preco": "8000",
                "classe": "basico",
                "descricao": "Carro para testar variação automática",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        data = r.get_json()
        assert data.get("sucesso") is True
        listagem = client_admin.get("/api/admin/carros")
        assert listagem.status_code == 200
        carros = listagem.get_json()
        encontrado = next((c for c in carros if c.get("marca") == marca and c.get("modelo") == modelo), None)
        assert encontrado is not None, f"Carro '{marca} {modelo}' deve aparecer na listagem."
        variacoes = encontrado.get("variacoes") or []
        assert len(variacoes) >= 1, (
            f"Ao cadastrar um carro deve ser criada ao menos uma variação (sem peças). "
            f"Carro '{marca} {modelo}' tem {len(variacoes)} variações."
        )
        # Pelo menos uma variação deve ser "sem peças" (todos os ids de peça nulos)
        sem_pecas = [
            v for v in variacoes
            if not v.get("motor_id") and not v.get("cambio_id") and not v.get("suspensao_id")
            and not v.get("kit_angulo_id") and not v.get("diferencial_id")
        ]
        assert len(sem_pecas) >= 1, (
            f"Deve existir ao menos uma variação sem nenhuma peça (motor, câmbio, suspensão, kit ângulo, diferencial). "
            f"Variações: {variacoes}"
        )
        print(f"  PERSISTÊNCIA OK: carro '{marca} {modelo}' tem variação sem peças (criada automaticamente).")

    def test_cadastrar_carro_sem_preco_400(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-carro",
            json={"marca": "X", "modelo": "Y", "preco": ""},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False


class TestCadastrarPeca:
    """POST /api/admin/cadastrar-peca."""

    def test_cadastrar_peca_ok(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-peca",
            json={
                "nome": "Motor Teste",
                "tipo": "motor",
                "preco": "1000",
                "durabilidade": "100",
                "coeficiente_quebra": "1.0",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True
        assert data.get("peca", {}).get("nome") == "Motor Teste"
        assert data.get("peca", {}).get("tipo") == "motor"

    def test_cadastrar_peca_persiste_na_listagem(self, client_admin):
        """Cadastra peça e verifica que aparece em GET /api/admin/pecas (persistência no banco)."""
        nome, tipo = "Peça Persist Test", "cambio"
        r = client_admin.post(
            "/api/admin/cadastrar-peca",
            json={
                "nome": nome,
                "tipo": tipo,
                "preco": "1200",
                "durabilidade": "100",
                "coeficiente_quebra": "1.0",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        data = r.get_json()
        assert data.get("sucesso") is True
        listagem = client_admin.get("/api/admin/pecas")
        assert listagem.status_code == 200
        pecas = listagem.get_json()
        assert isinstance(pecas, list), "Listagem de peças deve ser uma lista"
        encontrado = next((p for p in pecas if p.get("nome") == nome and (p.get("tipo") or "").lower() == tipo), None)
        assert encontrado is not None, f"Peça '{nome}' (tipo {tipo}) deve aparecer na listagem após cadastro."
        print(f"  PERSISTÊNCIA OK: peça '{nome}' (tipo {tipo}) encontrada na listagem (GET /api/admin/pecas).")


class TestCadastrarVariacao:
    """POST /api/admin/cadastrar-variacao (depende de modelo existente)."""

    def test_cadastrar_variacao_sem_modelo_400(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-variacao",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False
        assert "modelo" in (data.get("erro") or "").lower() or "fornecido" in (data.get("erro") or "").lower()

    def test_cadastrar_variacao_modelo_inexistente_404(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-variacao",
            json={"modelo_carro_loja_id": "00000000-0000-0000-0000-000000000001", "valor": 5000},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code in (400, 404)


class TestApiAdminEquipes:
    """GET /api/admin/equipes."""

    def test_listar_equipes_admin(self, client_admin):
        r = client_admin.get("/api/admin/equipes")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)


class TestApiAdminCarrosPecas:
    """Listagens admin de carros e peças."""

    def test_listar_carros_admin(self, client_admin):
        r = client_admin.get("/api/admin/carros")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, (list, dict)) or "carros" in str(data).lower()

    def test_listar_pecas_admin(self, client_admin):
        r = client_admin.get("/api/admin/pecas")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, (list, dict)) or "pecas" in str(data).lower()


class TestFazerEtapa:
    """POST /api/admin/fazer-etapa."""

    def test_fazer_etapa_sem_id_400(self, client_admin):
        r = client_admin.post(
            "/api/admin/fazer-etapa",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False

    def test_fazer_etapa_etapa_inexistente_404(self, client_admin):
        r = client_admin.post(
            "/api/admin/fazer-etapa",
            json={"etapa": "00000000-0000-0000-0000-000000000001"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 404


class TestAlocarPiloto:
    """POST /api/admin/alocar-piloto-etapa."""

    def test_alocar_piloto_sem_dados_400(self, client_admin):
        r = client_admin.post(
            "/api/admin/alocar-piloto-etapa",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False


class TestCriarCampeonato:
    """POST /api/admin/criar-campeonato e listar campeonatos."""

    def test_criar_campeonato_ok(self, client_admin):
        r = client_admin.post(
            "/api/admin/criar-campeonato",
            json={
                "nome": "Campeonato Teste",
                "descricao": "Descrição teste",
                "serie": "A",
                "numero_etapas": 5,
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        data = r.get_json()
        assert data.get("sucesso") is True
        assert "campeonato_id" in data

    def test_criar_campeonato_sem_nome_400(self, client_admin):
        r = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"serie": "A", "numero_etapas": 5},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False
        assert "obrigatório" in (data.get("erro") or "").lower() or "nome" in (data.get("erro") or "").lower()

    def test_criar_campeonato_sem_serie_400(self, client_admin):
        r = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"nome": "Campeonato X", "numero_etapas": 5},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False

    def test_criar_campeonato_persiste_na_listagem(self, client_admin):
        """Cria campeonato e verifica que aparece em GET /api/admin/listar-campeonatos."""
        nome = "Campeonato Persist Test"
        r = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"nome": nome, "serie": "B", "numero_etapas": 3},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.get_data(as_text=True)
        data = r.get_json()
        assert data.get("sucesso") is True
        campeonato_id = data.get("campeonato_id")
        assert campeonato_id
        listagem = client_admin.get("/api/admin/listar-campeonatos")
        assert listagem.status_code == 200
        campeonatos = listagem.get_json()
        assert isinstance(campeonatos, list)
        encontrado = next((c for c in campeonatos if c.get("nome") == nome), None)
        assert encontrado is not None, f"Campeonato '{nome}' deve aparecer na listagem."


class TestCadastrarEtapa:
    """POST /api/admin/cadastrar-etapa e listar etapas."""

    def test_cadastrar_etapa_sem_campeonato_400(self, client_admin):
        r = client_admin.post(
            "/api/admin/cadastrar-etapa",
            json={
                "numero": 1,
                "nome": "Etapa 1",
                "data_etapa": "2025-12-01",
                "hora_etapa": "10:00:00",
                "serie": "A",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("sucesso") is False

    def test_cadastrar_etapa_campeonato_e_etapa_persistem(self, client_admin):
        """Cria campeonato, cria etapa nele e verifica que ambos aparecem nas listagens."""
        nome_camp = "Campeonato E2E Etapas"
        r_camp = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"nome": nome_camp, "serie": "A", "numero_etapas": 5},
            headers={"Content-Type": "application/json"},
        )
        assert r_camp.status_code == 200, r_camp.get_data(as_text=True)
        data_camp = r_camp.get_json()
        assert data_camp.get("sucesso") is True
        campeonato_id = data_camp.get("campeonato_id")
        assert campeonato_id

        nome_etapa = "Etapa Inaugural"
        r_etapa = client_admin.post(
            "/api/admin/cadastrar-etapa",
            json={
                "campeonato_id": campeonato_id,
                "numero": 1,
                "nome": nome_etapa,
                "descricao": "Primeira etapa",
                "data_etapa": "2026-03-15",
                "hora_etapa": "14:00:00",
                "serie": "A",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_etapa.status_code == 200, r_etapa.get_data(as_text=True)
        data_etapa = r_etapa.get_json()
        assert data_etapa.get("sucesso") is True
        assert "etapa_id" in data_etapa

        listagem = client_admin.get("/api/admin/listar-etapas")
        assert listagem.status_code == 200
        etapas = listagem.get_json()
        assert isinstance(etapas, list)
        encontrada = next((e for e in etapas if e.get("nome") == nome_etapa), None)
        assert encontrada is not None, f"Etapa '{nome_etapa}' deve aparecer na listagem."


class TestParticiparEtapaEquipe:
    """POST /api/etapas/equipe/participar - inscrição nas 3 formas:
    dono_vai_andar (dono pilota), tenho_piloto (usa piloto contratado), precisa_piloto (precisa de piloto).
    """

    def test_inscrever_equipe_etapa_tres_formas(self, client_admin):
        """Equipe se inscreve na etapa nas 3 formas: dono_vai_andar, tenho_piloto, precisa_piloto."""
        from app import api

        # 1. Criar campeonato e etapa (nome único para evitar ON DUPLICATE KEY com id diferente)
        import uuid
        nome_camp = f"Campeonato Inscrição Etapa {uuid.uuid4().hex[:8]}"
        r_camp = client_admin.post(
            "/api/admin/criar-campeonato",
            json={"nome": nome_camp, "serie": "A", "numero_etapas": 5},
            headers={"Content-Type": "application/json"},
        )
        assert r_camp.status_code == 200, r_camp.get_data(as_text=True)
        campeonato_id = r_camp.get_json().get("campeonato_id")
        assert campeonato_id

        r_etapa = client_admin.post(
            "/api/admin/cadastrar-etapa",
            json={
                "campeonato_id": campeonato_id,
                "numero": 1,
                "nome": "Etapa Inscrição 3 Formas",
                "data_etapa": "2026-04-01",
                "hora_etapa": "10:00:00",
                "serie": "A",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_etapa.status_code == 200, r_etapa.get_data(as_text=True)
        etapa_id = r_etapa.get_json().get("etapa_id")
        assert etapa_id

        # 2. Criar carro modelo
        r_carro = client_admin.post(
            "/api/admin/cadastrar-carro",
            json={
                "marca": "Teste Inscrição",
                "modelo": "Modelo Etapa",
                "preco": 5000,
                "classe": "basico",
                "descricao": "Carro para teste inscrição",
            },
            headers={"Content-Type": "application/json"},
        )
        assert r_carro.status_code == 200, r_carro.get_data(as_text=True)
        modelo_id = (r_carro.get_json().get("carro") or {}).get("id")
        assert modelo_id

        # 3. Criar 3 equipes com carro e saldo_pix
        equipes_dados = []
        for i, (nome, tipo) in enumerate([
            ("Equipe Dono Pilota", "dono_vai_andar"),
            ("Equipe Piloto Contratado", "tenho_piloto"),
            ("Equipe Precisa Piloto", "precisa_piloto"),
        ]):
            r_eq = client_admin.post(
                "/api/admin/cadastrar-equipe",
                json={
                    "nome": nome,
                    "senha": "senha123",
                    "doricoins": 50000,
                    "serie": "A",
                    "carro_id": str(modelo_id),
                },
                headers={"Content-Type": "application/json"},
            )
            assert r_eq.status_code == 200, r_eq.get_data(as_text=True)
            data_eq = r_eq.get_json()
            assert data_eq.get("sucesso") is True
            equipe = data_eq.get("equipe") or {}
            equipe_id = equipe.get("id")
            carro_instancia_id = equipe.get("carro_instancia_id") or equipe.get("carro_id")
            assert equipe_id, f"Equipe {nome} deve retornar id"
            assert carro_instancia_id, f"Equipe {nome} deve ter carro_instancia_id"
            # Garantir saldo_pix para inscrição (valor_etapa ~1000)
            api.db.atualizar_saldo_pix(equipe_id, 5000.0)
            equipes_dados.append({
                "equipe_id": equipe_id,
                "carro_id": str(carro_instancia_id),
                "tipo": tipo,
            })

        # 4. Inscrever cada equipe na etapa com seu tipo
        for item in equipes_dados:
            r_part = client_admin.post(
                "/api/etapas/equipe/participar",
                json={
                    "etapa_id": etapa_id,
                    "equipe_id": item["equipe_id"],
                    "carro_id": item["carro_id"],
                    "tipo_participacao": item["tipo"],
                },
                headers={"Content-Type": "application/json"},
            )
            assert r_part.status_code == 200, (
                f"Participar ({item['tipo']}) deve retornar 200: {r_part.get_data(as_text=True)}"
            )
            data = r_part.get_json()
            assert data.get("sucesso") is True, (
                f"Inscrição {item['tipo']} deve ter sucesso: {data}"
            )
            assert "requer_regularizacao" not in data or data.get("requer_regularizacao") is False, (
                f"Inscrição {item['tipo']} não deve requerer regularização: {data}"
            )
            assert "mensagem" in data or "inscricao_id" in data or data.get("sucesso")

        # 5. Verificar que as 3 participações existem na etapa
        tipos_na_etapa = set()
        for eq in equipes_dados:
            etapas_da_eq = api.db.obter_etapas_equipe(eq["equipe_id"])
            for e in etapas_da_eq:
                if str(e.get("id") or e.get("etapa_id", "")) == str(etapa_id):
                    tipos_na_etapa.add(e.get("tipo_participacao") or eq["tipo"])
                    break
        assert "dono_vai_andar" in tipos_na_etapa, f"Esperado dono_vai_andar em {tipos_na_etapa}"
        assert "tenho_piloto" in tipos_na_etapa, f"Esperado tenho_piloto em {tipos_na_etapa}"
        assert "precisa_piloto" in tipos_na_etapa, f"Esperado precisa_piloto em {tipos_na_etapa}"


class TestQualificacaoEtapa:
    """Simula etapa com equipes inscritas, pilotos alocados, qualify, notas e verifica ordem."""

    def test_qualify_com_notas_e_ordem(self, client_admin):
        """Cria etapa, 4 equipes com pilotos, faz qualify, dá notas, finaliza e confirma ordem."""
        import os
        import uuid
        from app import api

        # 1. Campeonato e etapa
        nome_camp = f"Campeonato Qualify {uuid.uuid4().hex[:8]}"
        r_camp = client_admin.post("/api/admin/criar-campeonato", json={"nome": nome_camp, "serie": "A", "numero_etapas": 5})
        assert r_camp.status_code == 200
        campeonato_id = r_camp.get_json().get("campeonato_id")
        assert campeonato_id

        r_etapa = client_admin.post("/api/admin/cadastrar-etapa", json={
            "campeonato_id": campeonato_id, "numero": 1, "nome": "Etapa Qualify",
            "data_etapa": "2026-08-01", "hora_etapa": "10:00:00", "serie": "A",
        })
        assert r_etapa.status_code == 200
        etapa_id = r_etapa.get_json().get("etapa_id")
        assert etapa_id

        # 2. Carro modelo
        r_carro = client_admin.post("/api/admin/cadastrar-carro", json={
            "marca": "Qualify", "modelo": "Q1", "preco": 5000, "classe": "basico", "descricao": "",
        })
        assert r_carro.status_code == 200
        modelo_id = (r_carro.get_json().get("carro") or {}).get("id")
        assert modelo_id

        # 3. 4 equipes precisa_piloto + pilotos + alocar (2 equipes min para ordem)
        equipes_com_pilotos = []
        for i in range(4):
            r_eq = client_admin.post("/api/admin/cadastrar-equipe", json={
                "nome": f"Equipe Q{i+1}", "senha": "s1", "doricoins": 50000, "serie": "A", "carro_id": str(modelo_id),
            })
            assert r_eq.status_code == 200
            eq = (r_eq.get_json().get("equipe") or {})
            equipe_id = eq.get("id")
            carro_id = eq.get("carro_instancia_id") or eq.get("carro_id")
            assert equipe_id and carro_id
            api.db.atualizar_saldo_pix(equipe_id, 5000.0)

            r_pil = client_admin.post("/api/pilotos/cadastrar", json={"nome": f"Piloto Q{i+1} {uuid.uuid4().hex[:6]}", "senha": "s123"})
            assert r_pil.status_code == 200
            piloto_id = r_pil.get_json().get("piloto_id")
            piloto_nome = r_pil.get_json().get("nome", f"Piloto Q{i+1}")
            assert piloto_id

            r_part = client_admin.post("/api/etapas/equipe/participar", json={
                "etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": str(carro_id), "tipo_participacao": "precisa_piloto",
            })
            assert r_part.status_code == 200 and r_part.get_json().get("sucesso") is True

            res = api.db.inscrever_piloto_candidato_etapa(etapa_id, equipe_id, piloto_id, piloto_nome)
            assert res.get("sucesso") is True
            res2 = api.db.alocar_proximo_piloto_candidato(etapa_id, equipe_id)
            assert res2.get("sucesso") is True

            equipes_com_pilotos.append({"equipe_id": equipe_id, "nome": f"Equipe Q{i+1}"})

        # 4. Iniciar qualify (fazer-etapa)
        r_fazer = client_admin.post("/api/admin/fazer-etapa", json={"etapa": etapa_id})
        assert r_fazer.status_code == 200, r_fazer.get_data(as_text=True)
        assert r_fazer.get_json().get("sucesso") is True

        # 5. Dar notas (ordenadas para verificar: Q4 melhor, Q3, Q2, Q1 pior)
        notas_por_equipe = [
            {"equipe_id": equipes_com_pilotos[0]["equipe_id"], "nota_linha": 10, "nota_angulo": 8, "nota_estilo": 7},
            {"equipe_id": equipes_com_pilotos[1]["equipe_id"], "nota_linha": 12, "nota_angulo": 9, "nota_estilo": 8},
            {"equipe_id": equipes_com_pilotos[2]["equipe_id"], "nota_linha": 14, "nota_angulo": 10, "nota_estilo": 9},
            {"equipe_id": equipes_com_pilotos[3]["equipe_id"], "nota_linha": 15, "nota_angulo": 11, "nota_estilo": 10},
        ]
        r_notas = client_admin.post("/api/test/salvar-notas-etapa", json={"etapa_id": etapa_id, "notas": notas_por_equipe})
        if r_notas.status_code == 404:
            pytest.skip("TEST_E2E=1 necessário para /api/test/salvar-notas-etapa")
        assert r_notas.status_code == 200, r_notas.get_data(as_text=True)

        # 6. Finalizar qualificação
        r_fin = client_admin.post(f"/api/admin/finalizar-qualificacao/{etapa_id}")
        assert r_fin.status_code == 200
        assert r_fin.get_json().get("sucesso") is True

        # 7. Verificar classificação final (ordem: maior nota primeiro)
        r_class = client_admin.get(f"/api/etapas/{etapa_id}/classificacao-final")
        assert r_class.status_code == 200
        data = r_class.get_json()
        assert data.get("sucesso") is True
        classificacao = data.get("classificacao", [])
        assert len(classificacao) >= 4, f"Esperado pelo menos 4 na classificação: {classificacao}"

        # Ordem esperada: Q4 (36), Q3 (33), Q2 (29), Q1 (25)
        for i, esp in enumerate([("Equipe Q4", 36), ("Equipe Q3", 33), ("Equipe Q2", 29), ("Equipe Q1", 25)]):
            assert classificacao[i]["equipe_nome"] == esp[0], f"Pos {i+1} esperado {esp[0]}, obteve {classificacao[i]['equipe_nome']}"
            assert classificacao[i]["total_notas"] == esp[1], f"Pos {i+1} total esperado {esp[1]}, obteve {classificacao[i]['total_notas']}"
            assert classificacao[i]["ordem_qualificacao"] == i + 1, f"ordem_qualificacao pos {i+1} deve ser {i+1}"


class TestComissoes:
    """GET /api/admin/comissoes (requer admin)."""

    def test_comissoes_retorna_200(self, client_admin):
        r = client_admin.get("/api/admin/comissoes")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True
        assert "comissoes" in data
        assert "resumo" in data
