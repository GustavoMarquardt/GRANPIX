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


class TestComissoes:
    """GET /api/admin/comissoes (requer admin)."""

    def test_comissoes_retorna_200(self, client_admin):
        r = client_admin.get("/api/admin/comissoes")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("sucesso") is True
        assert "comissoes" in data
        assert "resumo" in data
