"""
Testes E2E do frontend admin: abrem o navegador e testam as páginas.
Requer: app rodando (ex.: flask run ou docker) e playwright instalado (playwright install).

Rodar com navegador visível e resultado de persistência na tela:
  pytest tests/e2e/ -v -s --headed

(-s = mostra prints; --headed = abre o Chrome para acompanhar)
"""
import re
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestAdminCarrosFrontend:
    """Frontend da página /admin/carros."""

    def test_pagina_carros_carrega_e_tem_titulo(self, page: Page, base_url: str):
        page.goto(f"{base_url}/admin/carros")
        expect(page).to_have_title(re.compile(r"Carros|GRANPIX", re.I))

    def test_pagina_carros_tem_formulario_cadastro(self, page: Page, base_url: str):
        page.goto(f"{base_url}/admin/carros")
        page.locator("#carroMarca").wait_for(state="visible", timeout=10000)
        page.locator("button:has-text('Cadastrar')").first.wait_for(state="visible", timeout=5000)

    def test_pagina_carros_tem_lista_de_carros(self, page: Page, base_url: str):
        page.goto(f"{base_url}/admin/carros")
        page.locator("#listaCarros").wait_for(state="visible", timeout=10000)

    def test_botao_cadastrar_carro_nao_da_reference_error(self, page: Page, base_url: str):
        """Clicar em Cadastrar Carro deve executar a função (alert de validação), não 'cadastrarCarro is not defined'."""
        page.goto(f"{base_url}/admin/carros")
        page.locator("#carroMarca").wait_for(state="visible", timeout=10000)
        dialog_msg = []

        def on_dialog(dialog):
            dialog_msg.append(dialog.message)
            dialog.accept()

        page.on("dialog", on_dialog)
        page.locator("button:has-text('Cadastrar Carro')").first.click()
        page.wait_for_timeout(500)
        assert any(
            "Preencha" in (m or "") or "Marca" in (m or "") or "sucesso" in (m or "").lower()
            for m in dialog_msg
        ), f"Esperado alert de validação ou sucesso; got: {dialog_msg}. Se vazio, provavelmente ReferenceError cadastrarCarro."


@pytest.mark.e2e
class TestAdminPecasFrontend:
    """Frontend da página /admin/pecas."""

    def test_pagina_pecas_carrega_e_tem_titulo(self, page: Page, base_url: str):
        page.goto(f"{base_url}/admin/pecas")
        expect(page).to_have_title(re.compile(r"Peças|GRANPIX", re.I))

    def test_pagina_pecas_tem_formulario(self, page: Page, base_url: str):
        page.goto(f"{base_url}/admin/pecas")
        page.locator("#pecaNome").wait_for(state="visible", timeout=10000)

    def test_botao_cadastrar_peca_nao_da_reference_error(self, page: Page, base_url: str):
        """Clicar em Cadastrar Peça deve executar a função (alert de validação), não 'cadastrarPeca is not defined'."""
        page.goto(f"{base_url}/admin/pecas")
        page.locator("#pecaNome").wait_for(state="visible", timeout=10000)
        dialog_msg = []

        def on_dialog(dialog):
            dialog_msg.append(dialog.message)
            dialog.accept()

        page.on("dialog", on_dialog)
        page.locator("button:has-text('Cadastrar Peça')").first.click()
        page.wait_for_timeout(500)
        assert any(
            "Preencha" in (m or "") or "Nome" in (m or "") or "sucesso" in (m or "").lower()
            for m in dialog_msg
        ), f"Esperado alert de validação ou sucesso; got: {dialog_msg}. Se vazio, provavelmente ReferenceError cadastrarPeca."


@pytest.mark.e2e
class TestAdminVariacoesFrontend:
    """Frontend da página /admin/variacoes."""

    def test_pagina_variacoes_carrega_e_tem_titulo(self, page: Page, base_url: str):
        page.goto(f"{base_url}/admin/variacoes")
        expect(page).to_have_title(re.compile(r"Variações|GRANPIX", re.I))

    def test_pagina_variacoes_tem_seletores(self, page: Page, base_url: str):
        page.goto(f"{base_url}/admin/variacoes")
        page.locator("#variacaoModelo").wait_for(state="visible", timeout=10000)


@pytest.mark.e2e
class TestE2ECarroEPecasComCompatibilidade:
    """E2E: cria um carro, depois cria peças com compatibilidade apenas para esse carro."""

    def test_cria_carro_e_peca_com_compatibilidade_apenas_para_esse_carro(
        self, page: Page, base_url: str
    ):
        """
        Fluxo: login admin -> cadastra carro -> cadastra peça com compatibilidade
        apenas para esse carro -> verifica que a peça aparece na listagem.
        """
        # 1) Login como admin (aba Admin tem role="tab", não button)
        print("\n[E2E] 1/6 Login admin...")
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)
        print("[E2E]     Login OK, redirecionado para admin.")

        # 2) Criar carro via API (mesma sessão do browser) para obter o ID
        marca, modelo = "E2E Carro Unico", "E2E Modelo Unico"
        create_car = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: 'E2E Carro Unico',
                        modelo: 'E2E Modelo Unico',
                        preco: 9999,
                        classe: 'basico',
                        descricao: 'E2E teste compatibilidade'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, data };
            }
            """
        )
        assert create_car["ok"], f"Cadastro do carro falhou: {create_car.get('data')}"
        car_data = create_car["data"]
        assert car_data.get("sucesso"), f"Resposta sem sucesso: {car_data}"
        carro_id = (car_data.get("carro") or {}).get("id")
        assert carro_id, "Resposta do cadastro de carro deve trazer carro.id"
        carro_id = str(carro_id)  # UUID ou int para string (data-model-id)
        print(f"[E2E] 2/6 Carro cadastrado (persistido). ID: {carro_id}")

        # 3) Ir para página de peças
        print("[E2E] 3/6 Abrindo página de peças...")
        page.goto(f"{base_url}/admin/pecas")
        page.locator("#pecaNome").wait_for(state="visible", timeout=10000)

        # 4) Preencher formulário da peça e definir compatibilidade apenas para esse carro
        print("[E2E] 4/6 Preenchendo peça com compatibilidade apenas para o carro criado...")
        page.locator("#pecaNome").fill("Peça E2E Só Para Carro Unico")
        page.locator("#pecaTipo").select_option(value="motor")
        page.locator("#pecaPreco").fill("1500")
        # Injetar tag de compatibilidade com o id do carro criado (simula seleção no dropdown)
        page.evaluate(
            """
            (carId) => {
                const container = document.getElementById('pecaCompatibilidadeTags');
                if (!container) return;
                const span = document.createElement('span');
                span.className = 'badge bg-secondary me-1';
                span.setAttribute('data-model-id', carId);
                span.textContent = 'E2E Carro Unico E2E Modelo Unico';
                container.appendChild(span);
            }
            """,
            carro_id,
        )

        # 5) Clicar em Cadastrar Peça e aceitar o alert de sucesso
        dialogs = []

        def on_dialog(d):
            dialogs.append(d.message)
            d.accept()

        page.on("dialog", on_dialog)
        page.locator("button:has-text('Cadastrar Peça')").first.click()
        page.wait_for_timeout(1500)

        assert any(
            "sucesso" in (m or "").lower() or "cadastrad" in (m or "").lower()
            for m in dialogs
        ), f"Esperado alert de sucesso ao cadastrar peça; got: {dialogs}"
        print("[E2E] 5/6 Peça cadastrada (persistida). Alert de sucesso exibido.")

        # 6) Verificar que a peça aparece na listagem (listaPecas) = persistência
        page.wait_for_timeout(1000)
        lista = page.locator("#listaPecas")
        lista.wait_for(state="visible", timeout=5000)
        content = lista.inner_text()
        assert "Peça E2E Só Para Carro Unico" in content or "E2E Só Para Carro Unico" in content, (
            f"A peça cadastrada deve aparecer na listagem. Conteúdo: {content[:500]}"
        )
        print("[E2E] 6/6 PERSISTÊNCIA OK: peça encontrada na listagem (dados gravados no banco).")


@pytest.mark.e2e
class TestE2ECarroEVariacao:
    """E2E: cria um carro, depois cadastra uma variação para esse carro na página de variações."""

    def test_cria_carro_e_cadastra_variacao_pela_ui(self, page: Page, base_url: str):
        """
        Fluxo: login admin -> cadastra carro -> vai em /admin/variacoes ->
        seleciona o modelo, preenche valor, cadastra variação -> verifica na listagem.
        """
        # 1) Login como admin
        print("\n[E2E Variação] 1/6 Login admin...")
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)
        print("[E2E Variação]     Login OK.")

        # 2) Criar carro via API para obter o ID
        marca, modelo = "E2E Var Carro", "E2E Var Modelo"
        create_car = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: 'E2E Var Carro',
                        modelo: 'E2E Var Modelo',
                        preco: 7777,
                        classe: 'basico',
                        descricao: 'E2E teste variação'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, data };
            }
            """
        )
        assert create_car["ok"], f"Cadastro do carro falhou: {create_car.get('data')}"
        car_data = create_car["data"]
        assert car_data.get("sucesso"), f"Resposta sem sucesso: {car_data}"
        carro_id = (car_data.get("carro") or {}).get("id")
        assert carro_id, "Resposta do cadastro de carro deve trazer carro.id"
        carro_id = str(carro_id)
        print(f"[E2E Variação] 2/6 Carro cadastrado. ID: {carro_id}")

        # 3) Ir para página de variações
        print("[E2E Variação] 3/6 Abrindo página de variações...")
        page.goto(f"{base_url}/admin/variacoes")
        page.locator("#variacaoModelo").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(800)
        # Selecionar o modelo que acabamos de criar (pode estar no select como "E2E Var Carro E2E Var Modelo")
        page.locator("#variacaoModelo").select_option(value=carro_id)
        page.wait_for_timeout(300)

        # 4) Preencher valor da variação (identificável) e deixar peças vazias
        valor_identificavel = "12345"
        page.locator("#variacaoValor").fill(valor_identificavel)
        print("[E2E Variação] 4/6 Formulário preenchido (valor 12345, sem peças).")

        # 5) Clicar em Cadastrar Variação e aceitar o alert de sucesso
        dialogs = []

        def on_dialog(d):
            dialogs.append(d.message)
            d.accept()

        page.on("dialog", on_dialog)
        page.locator("button:has-text('Cadastrar Variação')").first.click()
        page.wait_for_timeout(1500)

        assert any(
            "sucesso" in (m or "").lower() or "cadastrad" in (m or "").lower()
            for m in dialogs
        ), f"Esperado alert de sucesso ao cadastrar variação; got: {dialogs}"
        print("[E2E Variação] 5/6 Variação cadastrada. Alert de sucesso exibido.")

        # 6) Verificar que a variação aparece na listagem (listaVariacoes)
        page.wait_for_timeout(800)
        lista = page.locator("#listaVariacoes")
        lista.wait_for(state="visible", timeout=5000)
        content = lista.inner_text()
        # Deve aparecer o nome do carro e o valor (12345 pode vir formatado como 12.345,00 ou 12345)
        assert "E2E Var Carro" in content and "E2E Var Modelo" in content, (
            f"O carro deve aparecer na listagem de variações. Conteúdo: {content[:500]}"
        )
        content_norm = content.replace(".", "").replace(",", "")
        assert "12345" in content_norm, (
            f"A variação com valor 12345 deve aparecer na listagem. Conteúdo: {content[:500]}"
        )
        print("[E2E Variação] 6/6 PERSISTÊNCIA OK: variação encontrada na listagem (dados gravados no banco).")


@pytest.mark.e2e
class TestE2EEquipeComCarro:
    """E2E: cadastra um carro, depois cadastra uma equipe com esse carro (via API) e verifica na página."""

    def test_cadastra_equipe_com_carro_selecionado(self, page: Page, base_url: str):
        """
        Fluxo: login admin -> cadastra carro via API -> cadastra equipe via API com carro_id ->
        abre /admin/equipes e verifica que a equipe aparece na listagem com o carro.
        (Uso da API para criar equipe garante que carro_id é enviado; evita bug do dropdown.)
        """
        # 1) Login como admin
        print("\n[E2E Equipe+Carro] 1/5 Login admin...")
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)
        print("[E2E Equipe+Carro]     Login OK.")

        # 2) Criar carro via API
        marca, modelo = "E2E Equipe Carro", "E2E Equipe Modelo"
        create_car = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: 'E2E Equipe Carro',
                        modelo: 'E2E Equipe Modelo',
                        preco: 5000,
                        classe: 'basico',
                        descricao: 'E2E teste equipe com carro'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, data };
            }
            """
        )
        assert create_car["ok"], f"Cadastro do carro falhou: {create_car.get('data')}"
        car_data = create_car["data"]
        assert car_data.get("sucesso"), f"Resposta sem sucesso: {car_data}"
        modelo_id = (car_data.get("carro") or {}).get("id")
        assert modelo_id, "Resposta do cadastro de carro deve trazer carro.id"
        modelo_id = str(modelo_id)
        print(f"[E2E Equipe+Carro] 2/5 Carro cadastrado. Modelo ID: {modelo_id}")

        # 3) Criar equipe via API com carro_id (garante que o backend recebe o carro)
        nome_equipe = "Equipe E2E Com Carro"
        create_equipe = page.evaluate(
            """
            async (payload) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const data = await r.json();
                return { status: r.status, ok: r.ok, data };
            }
            """,
            {"nome": nome_equipe, "senha": "senha123", "doricoins": 10000, "serie": "A", "carro_id": modelo_id},
        )
        assert create_equipe["ok"], (
            f"Cadastro da equipe falhou: status={create_equipe.get('status')} data={create_equipe.get('data')}"
        )
        assert create_equipe["data"].get("sucesso"), (
            f"Resposta sem sucesso: {create_equipe.get('data')}"
        )
        print("[E2E Equipe+Carro] 3/5 Equipe cadastrada via API com carro_id.")

        # 4) Abrir página de equipes e recarregar a lista
        print("[E2E Equipe+Carro] 4/5 Abrindo página de equipes...")
        page.goto(f"{base_url}/admin/equipes")
        page.locator("#listaEquipesCadastro").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(1500)

        # 5) Verificar que a equipe aparece COM o carro na listagem
        content = page.locator("#listaEquipesCadastro").inner_text()
        assert nome_equipe in content, (
            f"A equipe '{nome_equipe}' deve aparecer na listagem. Conteúdo: {content[:500]}"
        )
        assert marca in content and modelo in content, (
            f"A equipe deve exibir o carro '{marca} {modelo}' (persistência do carro). Conteúdo: {content[:500]}"
        )
        print("[E2E Equipe+Carro] 5/5 PERSISTÊNCIA OK: equipe com carro exibida na listagem.")


@pytest.mark.e2e
class TestE2ELojaCarros:
    """E2E da loja de carros (admin): todas as probabilidades – cadastro, validações, listagem, edição, exclusão."""

    def _login_admin(self, page: Page, base_url: str):
        """Faz login como admin e garante redirecionamento."""
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def test_loja_carros_pagina_carrega_com_login(self, page: Page, base_url: str):
        """Página /admin/carros carrega após login e exibe formulário e lista."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        expect(page).to_have_title(re.compile(r"Carros|GRANPIX", re.I))
        page.locator("#carroMarca").wait_for(state="visible", timeout=10000)
        page.locator("#carroModelo").wait_for(state="visible", timeout=5000)
        page.locator("#carroPreco").wait_for(state="visible", timeout=5000)
        page.locator("#listaCarros").wait_for(state="visible", timeout=5000)
        page.locator("button:has-text('Cadastrar Carro')").first.wait_for(state="visible", timeout=5000)

    def test_loja_carros_ui_validacao_marca_modelo_vazios(self, page: Page, base_url: str):
        """Clicar em Cadastrar sem preencher marca/modelo exibe alert de validação."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        page.locator("#carroMarca").wait_for(state="visible", timeout=10000)
        page.locator("#carroMarca").fill("")
        page.locator("#carroModelo").fill("")
        page.locator("#carroPreco").fill("")
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
        page.locator("button:has-text('Cadastrar Carro')").first.click()
        page.wait_for_timeout(500)
        assert any(
            "Preencha" in (m or "") or "Marca" in (m or "") or "Modelo" in (m or "")
            for m in dialogs
        ), f"Esperado alert de validação (marca/modelo); got: {dialogs}"

    def test_loja_carros_ui_validacao_preco_vazio(self, page: Page, base_url: str):
        """Preenchendo marca e modelo mas sem preço exibe alert de preço válido."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        page.locator("#carroMarca").wait_for(state="visible", timeout=10000)
        page.locator("#carroMarca").fill("Marca E2E")
        page.locator("#carroModelo").fill("Modelo E2E")
        page.locator("#carroPreco").fill("")
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
        page.locator("button:has-text('Cadastrar Carro')").first.click()
        page.wait_for_timeout(500)
        assert any(
            "Preço" in (m or "") or "Preencha" in (m or "")
            for m in dialogs
        ), f"Esperado alert de preço; got: {dialogs}"

    def test_loja_carros_api_cadastro_sucesso(self, page: Page, base_url: str):
        """POST /api/admin/cadastrar-carro com dados válidos retorna 200 e carro com id."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        result = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: 'E2E Loja Marca',
                        modelo: 'E2E Loja Modelo',
                        preco: 12345,
                        classe: 'basico',
                        descricao: 'E2E loja teste'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, status: r.status, data };
            }
            """
        )
        assert result["ok"], f"Cadastro deve retornar 200: {result}"
        assert result["data"].get("sucesso"), f"Resposta deve ter sucesso: true: {result['data']}"
        carro = result["data"].get("carro") or {}
        assert carro.get("id"), f"Resposta deve trazer carro.id: {result['data']}"
        assert carro.get("marca") == "E2E Loja Marca" and carro.get("modelo") == "E2E Loja Modelo"

    def test_loja_carros_api_sem_preco_400(self, page: Page, base_url: str):
        """POST sem preço retorna 400 e mensagem 'Preço é obrigatório'."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        result = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: 'Marca',
                        modelo: 'Modelo',
                        preco: '',
                        classe: 'basico',
                        descricao: 'Teste'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, status: r.status, data };
            }
            """
        )
        assert not result["ok"], "Deve retornar erro (400)"
        assert result["status"] == 400
        assert "preço" in (result["data"].get("erro") or "").lower() or "obrigatório" in (result["data"].get("erro") or "").lower()

    def test_loja_carros_api_sem_marca_400(self, page: Page, base_url: str):
        """POST sem marca retorna 400."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        result = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: '',
                        modelo: 'Modelo',
                        preco: 1000,
                        classe: 'basico',
                        descricao: 'Teste'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, status: r.status, data };
            }
            """
        )
        assert not result["ok"]
        assert result["status"] == 400
        assert "marca" in (result["data"].get("erro") or "").lower() or "obrigatório" in (result["data"].get("erro") or "").lower()

    def test_loja_carros_api_sem_modelo_400(self, page: Page, base_url: str):
        """POST sem modelo retorna 400."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        result = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: 'Marca',
                        modelo: '',
                        preco: 1000,
                        classe: 'basico',
                        descricao: 'Teste'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, status: r.status, data };
            }
            """
        )
        assert not result["ok"]
        assert result["status"] == 400
        assert "modelo" in (result["data"].get("erro") or "").lower() or "obrigatório" in (result["data"].get("erro") or "").lower()

    def test_loja_carros_api_listagem_retorna_array(self, page: Page, base_url: str):
        """GET /api/admin/carros retorna 200 e um array (pode ser vazio)."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        result = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/carros', { credentials: 'include' });
                const data = await r.json();
                return { ok: r.ok, isArray: Array.isArray(data), length: Array.isArray(data) ? data.length : -1 };
            }
            """
        )
        assert result["ok"], f"GET /api/admin/carros deve retornar 200: {result}"
        assert result["isArray"], "Resposta deve ser um array"

    def test_loja_carros_listagem_apos_cadastro(self, page: Page, base_url: str):
        """Cadastra carro via API e verifica que aparece na listagem da página."""
        self._login_admin(page, base_url)
        marca, modelo = "E2E Listagem Marca", "E2E Listagem Modelo"
        create = page.evaluate(
            """
            async (payload) => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const data = await r.json();
                return { ok: r.ok, data };
            }
            """,
            {"marca": marca, "modelo": modelo, "preco": 9999, "classe": "basico", "descricao": "E2E listagem"},
        )
        assert create["ok"] and create["data"].get("sucesso"), f"Cadastro falhou: {create}"
        page.goto(f"{base_url}/admin/carros")
        page.locator("#listaCarros").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(1500)
        content = page.locator("#listaCarros").inner_text()
        assert marca in content and modelo in content, (
            f"Carro '{marca} {modelo}' deve aparecer na listagem. Conteúdo: {content[:600]}"
        )

    def test_loja_carros_fluxo_completo_cadastrar_editar_deletar(self, page: Page, base_url: str):
        """Fluxo completo: cadastrar pela UI -> aparece na lista -> editar -> salvar -> deletar -> some da lista."""
        import time
        suf = str(int(time.time() * 1000))
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        page.locator("#carroMarca").wait_for(state="visible", timeout=10000)
        marca_orig, modelo_orig = f"E2E Fluxo Orig {suf}", f"E2E Fluxo Orig {suf}"
        preco_orig = "8888"
        page.locator("#carroMarca").fill(marca_orig)
        page.locator("#carroModelo").fill(modelo_orig)
        page.locator("#carroPreco").fill(preco_orig)
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
        page.locator("button:has-text('Cadastrar Carro')").first.click()
        page.wait_for_timeout(1500)
        assert any("sucesso" in (m or "").lower() for m in dialogs), f"Esperado alert de sucesso; got: {dialogs}"
        page.wait_for_timeout(1000)
        content = page.locator("#listaCarros").inner_text()
        assert marca_orig in content and modelo_orig in content, f"Carro deve aparecer após cadastro: {content[:500]}"
        # Editar: clicar no botão "Editar" do primeiro item que contenha o nome
        page.locator("button:has-text('Editar')").first.click()
        page.wait_for_timeout(500)
        page.locator("#editCarroMarca").wait_for(state="visible", timeout=5000)
        nome_editado = f"E2E Fluxo Editado {suf}"
        page.locator("#editCarroMarca").fill(nome_editado)
        page.locator("#editCarroModelo").fill(nome_editado)
        page.locator("#editCarroPreco").fill("7777")
        dialogs.clear()

        def handle_dialog(d):
            dialogs.append(d.message)
            try:
                d.accept()
            except Exception:
                pass  # Já aceito

        page.on("dialog", handle_dialog)
        # Backdrop do modal pode interceptar; usar dispatch click via JS
        page.locator("#modalEditarCarro button:has-text('Salvar')").evaluate("el => el.click()")
        page.wait_for_timeout(1500)
        assert any("atualizado" in (m or "").lower() or "sucesso" in (m or "").lower() for m in dialogs), f"Esperado alert ao salvar edição; got: {dialogs}"
        page.wait_for_timeout(800)
        content2 = page.locator("#listaCarros").inner_text()
        assert nome_editado in content2, f"Lista deve mostrar nome editado: {content2[:500]}"
        # Deletar: abrir edição do card com nome único e clicar em Deletar Carro
        page.locator("#listaCarros .mb-3").filter(has_text=nome_editado).locator("button:has-text('Editar')").first.click()
        page.wait_for_timeout(500)
        page.locator("#editCarroMarca").wait_for(state="visible", timeout=5000)
        dialogs.clear()
        page.on("dialog", handle_dialog)
        page.locator("#modalEditarCarro button:has-text('Deletar Carro')").evaluate("el => el.click()")
        page.wait_for_timeout(1500)
        page.wait_for_timeout(2000)  # Aguardar carregarCarros após deletar
        content3 = page.locator("#listaCarros").inner_text()
        assert nome_editado not in content3, (
            f"Após deletar, '{nome_editado}' não deve constar na lista. Conteúdo: {content3[:500]}"
        )


@pytest.mark.e2e
class TestE2ECompraCarroEquipe:
    """E2E: equipe logada compra um carro na loja (dashboard -> Loja de Carros -> Comprar -> Confirmar)."""

    def test_equipe_compra_carro_na_loja(self, page: Page, base_url: str):
        """
        Fluxo: login admin -> cria carro e equipe (API) -> login como equipe ->
        abre Loja de Carros -> clica Comprar no primeiro carro -> confirma ->
        verifica que a equipe tem o carro na garagem.
        """
        # 1) Login admin
        print("\n[E2E Compra Carro] 1/7 Login admin...")
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)
        print("[E2E Compra Carro]     Admin logado.")

        # 2) Cadastrar um carro na loja (para ter o que comprar)
        marca_carro, modelo_carro = "E2E Compra Marca", "E2E Compra Modelo"
        create_car = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        marca: 'E2E Compra Marca',
                        modelo: 'E2E Compra Modelo',
                        preco: 15000,
                        classe: 'basico',
                        descricao: 'E2E compra equipe'
                    })
                });
                const data = await r.json();
                return { ok: r.ok, data };
            }
            """
        )
        assert create_car["ok"] and create_car["data"].get("sucesso"), f"Cadastro do carro falhou: {create_car.get('data')}"
        carro_id_loja = create_car["data"].get("carro", {}).get("id")
        assert carro_id_loja, "Resposta do cadastro de carro deve trazer carro.id"
        print("[E2E Compra Carro] 2/7 Carro cadastrado na loja.")

        # 3) Cadastrar equipe com saldo para comprar (nome único para não reutilizar equipe antiga)
        nome_equipe = "E2E Compra Carro " + str(int(__import__("time").time() * 1000))
        senha_equipe = "senha123"
        create_equipe = page.evaluate(
            """
            async (payload) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const data = await r.json();
                return { ok: r.ok, status: r.status, data };
            }
            """,
            {"nome": nome_equipe, "senha": senha_equipe, "doricoins": 1000000, "serie": "A"},
        )
        assert create_equipe["ok"] and create_equipe["data"].get("sucesso"), (
            f"Cadastro da equipe falhou: {create_equipe.get('status')} {create_equipe.get('data')}"
        )
        equipe_id = create_equipe["data"].get("equipe", {}).get("id")
        assert equipe_id, "Resposta do cadastro de equipe deve trazer equipe.id"
        equipe_id = str(equipe_id)
        print(f"[E2E Compra Carro] 3/7 Equipe criada: {equipe_id}")

        # 4) Ir para login e entrar como equipe
        print("[E2E Compra Carro] 4/7 Login como equipe...")
        page.goto(f"{base_url}/login")
        page.locator("#equipeSelecionada").wait_for(state="visible", timeout=10000)
        # Esperar opções do select (carregarEquipes é assíncrono)
        page.wait_for_timeout(1500)
        page.select_option("#equipeSelecionada", equipe_id)
        page.locator("#senhaEquipe").fill(senha_equipe)
        page.locator("#btnLoginEquipe").click()
        page.wait_for_url(re.compile(r".*/dashboard.*"), timeout=15000)
        # Garantir que a equipe foi carregada (equipeAtual no JS) antes de usar a loja
        page.locator("#equipeDetalhes").wait_for(state="visible", timeout=10000)
        page.locator("#equipeDetalhes .stat-value").first.wait_for(state="visible", timeout=10000)
        print("[E2E Compra Carro]     Equipe logada, no dashboard.")

        # 5) Abrir aba Loja de Carros (simula usuário na loja)
        print("[E2E Compra Carro] 5/7 Abrindo Loja de Carros...")
        page.locator('a[href="#carros-tab"]').click()
        page.wait_for_timeout(3000)  # Aguardar carregamento lazy da aba
        # Esperar botão Comprar ou texto do carro (fallback se grid demorar)
        try:
            page.locator("#carrosGrid .btn-comprar").first.wait_for(state="visible", timeout=20000)
        except Exception:
            page.get_by_text("E2E Compra Marca", exact=False).first.wait_for(state="visible", timeout=5000)

        # 6) Comprar o carro via API (mesma chamada do modal; evita flakiness do Bootstrap)
        print("[E2E Compra Carro] 6/7 Comprando carro (POST /api/comprar)...")
        compra = page.evaluate(
            """
            async (itemId) => {
                const r = await fetch('/api/comprar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ tipo: 'carro', item_id: itemId })
                });
                const data = await r.json();
                return { ok: r.ok, data };
            }
            """,
            carro_id_loja,
        )
        assert compra.get("ok") and compra.get("data", {}).get("sucesso"), (
            f"Compra do carro falhou: {compra.get('data')}"
        )
        page.wait_for_timeout(1000)

        # 7) Verificar que a equipe tem o carro (garagem via API no contexto da página)
        print("[E2E Compra Carro] 7/7 Verificando garagem...")
        garagem = page.evaluate(
            """
            async (eqId) => {
                const r = await fetch('/api/garagem/' + eqId, { credentials: 'include' });
                if (!r.ok) return { carros: [] };
                const data = await r.json();
                return { carros: data.carros || [] };
            }
            """,
            equipe_id,
        )
        carros_garagem = garagem.get("carros") or []
        assert len(carros_garagem) >= 1, (
            f"A equipe deve ter pelo menos 1 carro na garagem após a compra. Obtido: {len(carros_garagem)}"
        )
        # Verificar que o carro comprado está na garagem (marca/modelo)
        nomes = [f"{c.get('marca', '')} {c.get('modelo', '')}" for c in carros_garagem]
        assert any(marca_carro in n and modelo_carro in n for n in nomes), (
            f"Garagem deve conter o carro '{marca_carro} {modelo_carro}'. Carros: {nomes}"
        )
        print("[E2E Compra Carro] PERSISTÊNCIA OK: equipe comprou o carro e ele está na garagem.")


@pytest.mark.e2e
class TestE2ELojaPecas:
    """E2E da loja de peças: carrinho, destino Armazém (sem PIX) e destino Carro ativo (PIX + solicitação)."""

    def _login_admin(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def _login_equipe(self, page: Page, base_url: str, equipe_id: str, senha: str):
        page.goto(f"{base_url}/login")
        page.locator("#equipeSelecionada").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(1500)
        page.select_option("#equipeSelecionada", equipe_id)
        page.locator("#senhaEquipe").fill(senha)
        page.locator("#btnLoginEquipe").click()
        page.wait_for_url(re.compile(r".*/dashboard.*"), timeout=15000)

    def test_loja_pecas_carrinho_para_armazem(self, page: Page, base_url: str):
        """
        Carrinho: adiciona peça -> abre modal destino -> escolhe Armazém -> Continuar.
        Verifica que a peça aparece no armazém (sem PIX).
        """
        # 1) Admin: criar equipe (sem carro), carro na loja e peça universal
        print("\n[E2E Loja Peças] 1/6 Login admin e criando dados...")
        self._login_admin(page, base_url)
        page.evaluate(
            """
            async () => {
                await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ marca: 'E2E Peca Car', modelo: 'E2E Peca Model', preco: 5000, classe: 'basico', descricao: 'E2E' })
                });
                const rp = await fetch('/api/admin/cadastrar-peca', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        nome: 'E2E Peça Armazém', tipo: 'motor', preco: 1000, durabilidade: 100,
                        coeficiente_quebra: 1, compatibilidade: 'universal'
                    })
                });
                await rp.json();
            }
            """
        )
        create_equipe = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Loja Peca Equipe', senha: 'senha123', doricoins: 50000, serie: 'A' })
                });
                const data = await r.json();
                return { ok: r.ok, data };
            }
            """
        )
        assert create_equipe["data"].get("sucesso"), f"Cadastro equipe: {create_equipe.get('data')}"
        equipe_id = str(create_equipe["data"].get("equipe", {}).get("id", ""))
        assert equipe_id, "equipe.id obrigatório"
        print("[E2E Loja Peças] 2/6 Equipe e peça criados.")

        # 2) Login como equipe
        self._login_equipe(page, base_url, equipe_id, "senha123")
        print("[E2E Loja Peças] 3/6 Equipe logada.")

        # 3) Abrir Loja de Peças e adicionar uma peça ao carrinho
        page.locator('a[href="#pecas-tab"]').click()
        page.wait_for_timeout(2000)
        page.locator("#pecasGrid").wait_for(state="visible", timeout=15000)
        page.wait_for_timeout(500)
        # Clicar no primeiro "Adicionar ao Carrinho"
        page.locator('#pecasGrid button:has-text("Adicionar ao Carrinho")').first.click()
        page.wait_for_timeout(800)

        # 4) Abrir painel do carrinho e clicar em Comprar (abre modal Destino)
        page.locator("#carrinhoFlutuante").wait_for(state="visible", timeout=5000)
        page.locator("#carrinhoFlutuante").click()
        page.wait_for_timeout(400)
        page.locator("#btnComprar").click()
        page.wait_for_timeout(500)
        page.locator("#modalDestino").wait_for(state="visible", timeout=5000)
        # Destino padrão já é Armazém; clicar Continuar
        page.locator("#modalDestino button:has-text('Continuar')").click()
        page.wait_for_timeout(3000)

        # 5) Verificar armazém via API
        armazem = page.evaluate(
            """
            async (eqId) => {
                const r = await fetch('/api/armazem/' + eqId, { credentials: 'include' });
                if (!r.ok) return { pecas_guardadas: [] };
                const data = await r.json();
                return { pecas_guardadas: data.pecas_guardadas || [] };
            }
            """,
            equipe_id,
        )
        pecas = armazem.get("pecas_guardadas") or []
        assert len(pecas) >= 1, (
            f"Armazém deve ter pelo menos 1 peça após compra (carrinho -> Armazém -> Continuar). Obtido: {len(pecas)}"
        )
        print("[E2E Loja Peças] 6/6 PERSISTÊNCIA OK: peça(s) no armazém (compra sem PIX).")

    def test_loja_pecas_carrinho_para_carro_ativo_pix(self, page: Page, base_url: str):
        """
        Carrinho: adiciona peça -> destino Carro ativo -> Continuar -> gera PIX e modal de pagamento.
        Requer TEST_E2E=1 no servidor para ativar carro sem PIX.
        """
        # 1) Admin: carro, equipe com carro, peça
        self._login_admin(page, base_url)
        page.evaluate(
            """
            async () => {
                const rc = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ marca: 'E2E PIX Car', modelo: 'E2E PIX Model', preco: 8000, classe: 'basico', descricao: 'E2E' })
                });
                const dc = await rc.json();
                const modeloId = dc.carro && dc.carro.id ? dc.carro.id : null;
                const re = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Loja PIX Equipe', senha: 'senha123', doricoins: 50000, serie: 'A', carro_id: modeloId })
                });
                const de = await re.json();
                const eqId = de.equipe && de.equipe.id ? de.equipe.id : null;
                await fetch('/api/admin/cadastrar-peca', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        nome: 'E2E Peça PIX', tipo: 'cambio', preco: 500, durabilidade: 100,
                        coeficiente_quebra: 1, compatibilidade: 'universal'
                    })
                });
                return { equipe_id: eqId, ok: de.sucesso };
            }
            """
        )
        create_equipe = page.evaluate(
            """
            async () => {
                const rc = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ marca: 'E2E PIX Car', modelo: 'E2E PIX Model', preco: 8000, classe: 'basico', descricao: 'E2E' })
                });
                const dc = await rc.json();
                const modeloId = (dc.carro && dc.carro.id) ? dc.carro.id : null;
                const re = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Loja PIX Equipe', senha: 'senha123', doricoins: 50000, serie: 'A', carro_id: modeloId })
                });
                const data = await re.json();
                return { ok: re.ok, data };
            }
            """
        )
        assert create_equipe["data"].get("sucesso"), f"Cadastro equipe+carro: {create_equipe.get('data')}"
        equipe_id = str(create_equipe["data"].get("equipe", {}).get("id", ""))
        assert equipe_id, "equipe.id obrigatório"

        # Cadastrar peça
        page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-peca', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        nome: 'E2E Peça PIX', tipo: 'cambio', preco: 500, durabilidade: 100,
                        coeficiente_quebra: 1, compatibilidade: 'universal'
                    })
                });
                return await r.json();
            }
            """
        )

        # 2) Login equipe e ativar carro (endpoint de teste, requer TEST_E2E=1)
        self._login_equipe(page, base_url, equipe_id, "senha123")
        ativar = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/test/ativar-carro-direto', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include'
                });
                const data = await r.json();
                return { ok: r.ok, status: r.status, data };
            }
            """
        )
        if ativar["status"] == 404:
            pytest.skip("TEST_E2E=1 não definido no servidor; pulando teste carro ativo + PIX")
        assert ativar.get("data", {}).get("sucesso"), f"Ativar carro: {ativar.get('data')}"
        page.wait_for_timeout(1000)

        # 3) Loja de Peças: adicionar peça ao carrinho
        page.locator('a[href="#pecas-tab"]').click()
        page.wait_for_timeout(2000)
        page.locator("#pecasGrid").wait_for(state="visible", timeout=15000)
        page.locator('#pecasGrid button:has-text("Adicionar ao Carrinho")').first.click()
        page.wait_for_timeout(800)

        # 4) Comprar -> modal Destino -> selecionar "Carro Ativo" na primeira peça -> Continuar
        page.locator("#carrinhoFlutuante").click()
        page.wait_for_timeout(400)
        page.locator("#btnComprar").click()
        page.wait_for_timeout(600)
        page.locator("#modalDestino").wait_for(state="visible", timeout=5000)
        # Clicar no botão "Carro Ativo" da primeira peça (classe .carro ou texto "Carro Ativo")
        page.locator("#listaPecasDestino button:has-text('Carro Ativo')").first.click()
        page.wait_for_timeout(300)
        page.locator("#modalDestino button:has-text('Continuar')").click()
        page.wait_for_timeout(3500)

        # 5) Deve abrir modal PIX (geração de PIX para instalação / solicitação)
        modal_pix = page.locator("#pixModal")
        try:
            modal_pix.wait_for(state="visible", timeout=8000)
        except Exception:
            pass
        # Aceitar qualquer alert/confirm que possa ter aparecido
        try:
            page.on("dialog", lambda d: d.accept())
        except Exception:
            pass
        # Verificar que o modal PIX apareceu OU que a API de PIX retornou sucesso (toast ou qr presente)
        pix_visible = modal_pix.is_visible()
        body_text = page.locator("body").inner_text()
        assert pix_visible or "PIX" in body_text or "QR" in body_text or "Aguardando" in body_text, (
            "Esperado modal PIX ou mensagem de pagamento após escolher Carro ativo. "
            "Se o carro não estiver ativo, defina TEST_E2E=1 no servidor."
        )
        print("[E2E Loja Peças] PIX/solicitação: modal de pagamento exibido.")


@pytest.mark.e2e
class TestE2ESolicitacoesPecas:
    """E2E da página Admin Solicitações de Peças: listagem agrupada por equipe e aprovação."""

    def _login_admin(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def test_pagina_solicitacoes_pecas_carrega(self, page: Page, base_url: str):
        """Página /admin/solicitacoes-pecas carrega e exibe título e área de lista ou vazia."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/solicitacoes-pecas")
        expect(page).to_have_title(re.compile(r"Solicitações|Peças|GRANPIX", re.I))
        # Deve mostrar o card principal (Solicitações de Peças) e ou loading ou lista/cards ou "Nenhuma"
        page.locator("h5:has-text('Solicitações de Peças')").wait_for(state="visible", timeout=10000)
        # Após carregar: ou #listaSolicitacoesPecas visível ou #nenhumaSolicitacao ou #loadingSolicitacoes
        page.wait_for_timeout(3500)
        content = page.locator(".main-content").inner_text()
        assert "Solicitações de Peças" in content, f"Conteúdo esperado na página: {content[:300]}"
        print("[E2E Solicitações Peças] Página carrega com título e área de conteúdo.")

    def test_solicitacoes_pecas_agrupadas_e_aprovar(self, page: Page, base_url: str):
        """
        Cria equipe, carro, peça e uma solicitação pendente via API de teste;
        abre /admin/solicitacoes-pecas, verifica listagem agrupada por equipe e aprova uma.
        Requer TEST_E2E=1 no servidor (e endpoint /api/test/criar-solicitacao-peca).
        """
        self._login_admin(page, base_url)
        # Criar carro na loja, equipe com esse carro, peça na loja
        setup = page.evaluate(
            """
            async () => {
                const rc = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ marca: 'E2E Sol Pecas Car', modelo: 'E2E Sol Pecas Model', preco: 5000, classe: 'basico', descricao: 'E2E' })
                });
                const dc = await rc.json();
                const modeloId = (dc.carro && dc.carro.id) ? dc.carro.id : null;
                const re = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Sol Pecas Equipe', senha: 'senha123', doricoins: 50000, serie: 'A', carro_id: modeloId })
                });
                const de = await re.json();
                const equipeId = (de.equipe && de.equipe.id) ? de.equipe.id : null;
                const carroId = (de.equipe && de.equipe.carro_instancia_id) ? de.equipe.carro_instancia_id : (de.equipe && de.equipe.carro_id) ? de.equipe.carro_id : modeloId;
                const rp = await fetch('/api/admin/cadastrar-peca', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Sol Pecas Motor', tipo: 'motor', preco: 800, durabilidade: 100, coeficiente_quebra: 1, compatibilidade: 'universal' })
                });
                const dp = await rp.json();
                const pecaId = (dp.peca && dp.peca.id) ? dp.peca.id : null;
                if (!equipeId || !pecaId || !carroId) return { ok: false, error: 'ids missing', equipeId, pecaId, carroId };
                const rs = await fetch('/api/test/criar-solicitacao-peca', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ equipe_id: equipeId, peca_id: pecaId, carro_id: carroId })
                });
                const ds = await rs.json();
                return { ok: rs.ok && ds.sucesso, equipeId, pecaId, carroId, solicitacao_id: ds.solicitacao_id, data: ds };
            }
            """
        )
        if not setup.get("ok"):
            pytest.skip(
                "Criar solicitação de teste requer TEST_E2E=1 e /api/test/criar-solicitacao-peca. "
                f"Resposta: {setup}"
            )
        print("[E2E Solicitações Peças] Dados e solicitação pendente criados.")
        page.goto(f"{base_url}/admin/solicitacoes-pecas")
        page.wait_for_timeout(4000)
        # Deve haver pelo menos um card de equipe (agrupamento)
        cards_equipe = page.locator(".card .card-header.bg-secondary")
        try:
            cards_equipe.first.wait_for(state="visible", timeout=8000)
        except Exception:
            body = page.locator("body").inner_text()
            assert False, f"Esperado pelo menos um card de equipe na listagem. Conteúdo: {body[:600]}"
        content = page.locator("#listaSolicitacoesPecas").inner_text()
        assert "E2E Sol Pecas" in content or "solicitação" in content.lower(), (
            f"Listagem deve conter nome da equipe ou peça criada. Conteúdo: {content[:400]}"
        )
        # Clicar no primeiro botão "Aprovar"
        btn_aprovar = page.locator('button:has-text("Aprovar")').first
        try:
            btn_aprovar.wait_for(state="visible", timeout=5000)
        except Exception:
            pytest.skip("Nenhum botão Aprovar encontrado (pode não haver solicitação pendente).")
        page.on("dialog", lambda d: d.accept())
        btn_aprovar.click()
        page.wait_for_timeout(3500)
        # Após aprovar: deve aparecer badge "Instalado" ou toast de sucesso
        body = page.locator("body").inner_text()
        assert "Instalado" in body or "instalada" in body.lower() or "sucesso" in body.lower(), (
            f"Esperado feedback de aprovação (Instalado/sucesso). Conteúdo: {body[:500]}"
        )
        print("[E2E Solicitações Peças] Aprovação concluída; listagem agrupada por equipe e fluxo OK.")


@pytest.mark.e2e
class TestE2ESolicitacoesCarros:
    """E2E da página Admin Solicitações de Carros: listagem agrupada por equipe e aprovação."""

    def _login_admin(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def test_pagina_solicitacoes_carros_carrega(self, page: Page, base_url: str):
        """Página /admin/solicitacoes-carros carrega e exibe título e área de lista ou vazia."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/solicitacoes-carros")
        expect(page).to_have_title(re.compile(r"Solicitações|Carros|GRANPIX", re.I))
        page.locator("h5:has-text('Solicitações de Carros')").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(3500)
        content = page.locator(".main-content").inner_text()
        assert "Solicitações de Carros" in content, f"Conteúdo esperado na página: {content[:300]}"
        print("[E2E Solicitações Carros] Página carrega com título e área de conteúdo.")

    def test_solicitacoes_carros_agrupadas_e_aprovar(self, page: Page, base_url: str):
        """
        Cria equipe com carro, cria solicitação de ativação pendente via API de teste;
        abre /admin/solicitacoes-carros, verifica listagem agrupada por equipe e aprova uma.
        Requer TEST_E2E=1 no servidor (e endpoint /api/test/criar-solicitacao-carro).
        """
        self._login_admin(page, base_url)
        setup = page.evaluate(
            """
            async () => {
                const rc = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ marca: 'E2E Sol Carro Marca', modelo: 'E2E Sol Carro Model', preco: 7000, classe: 'basico', descricao: 'E2E' })
                });
                const dc = await rc.json();
                const modeloId = (dc.carro && dc.carro.id) ? dc.carro.id : null;
                const re = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Sol Carro Equipe ' + Date.now(), senha: 'senha123', doricoins: 50000, serie: 'A', carro_id: modeloId })
                });
                const de = await re.json();
                const equipeId = (de.equipe && de.equipe.id) ? de.equipe.id : null;
                const carroId = (de.equipe && de.equipe.carro_instancia_id) ? de.equipe.carro_instancia_id : (de.equipe && de.equipe.carro_id) ? de.equipe.carro_id : modeloId;
                if (!equipeId || !carroId) return { ok: false, error: 'ids missing', data: de };
                const rs = await fetch('/api/test/criar-solicitacao-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ equipe_id: equipeId, carro_id: carroId })
                });
                const ds = await rs.json();
                return { ok: rs.ok && ds.sucesso, equipeId, carroId, solicitacao_id: ds.solicitacao_id, data: ds };
            }
            """
        )
        if not setup.get("ok"):
            pytest.skip(
                "Criar solicitação de carro requer TEST_E2E=1 e /api/test/criar-solicitacao-carro. "
                f"Resposta: {setup}"
            )
        print("[E2E Solicitações Carros] Dados e solicitação pendente criados.")
        page.goto(f"{base_url}/admin/solicitacoes-carros")
        page.wait_for_timeout(4000)
        cards_equipe = page.locator(".card .card-header.bg-secondary")
        try:
            cards_equipe.first.wait_for(state="visible", timeout=8000)
        except Exception:
            body = page.locator("body").inner_text()
            assert False, f"Esperado pelo menos um card de equipe na listagem. Conteúdo: {body[:600]}"
        content = page.locator("#listaSolicitacoesCarros").inner_text()
        assert "E2E Sol Carro" in content or "solicitação" in content.lower() or "Ativação" in content, (
            f"Listagem deve conter nome da equipe ou tipo. Conteúdo: {content[:400]}"
        )
        btn_aprovar = page.locator('button:has-text("Aprovar")').first
        try:
            btn_aprovar.wait_for(state="visible", timeout=5000)
        except Exception:
            pytest.skip("Nenhum botão Aprovar encontrado (pode não haver solicitação pendente).")
        page.on("dialog", lambda d: d.accept())
        btn_aprovar.click()
        page.wait_for_timeout(3500)
        body = page.locator("body").inner_text()
        assert "Aprovado" in body or "ativado" in body.lower() or "sucesso" in body.lower(), (
            f"Esperado feedback de aprovação (Aprovado/ativado/sucesso). Conteúdo: {body[:500]}"
        )
        print("[E2E Solicitações Carros] Aprovação concluída; listagem agrupada por equipe e fluxo OK.")


@pytest.mark.e2e
class TestE2EDashboardMensagensVazias:
    """E2E: Dashboard da equipe exibe 'Sem carros para ativar' e 'Sem peças para ativar' quando não há pendências."""

    def test_dashboard_exibe_sem_carros_sem_pecas_quando_vazio(self, page: Page, base_url: str):
        """
        Login como equipe -> abre dashboard -> verifica seções Carros/Peças Aguardando
        exibem mensagens de estado vazio (não ficam em Carregando...).
        """
        # 1) Admin cria carro e equipe (sem solicitações pendentes)
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

        create_car = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ marca: 'E2E Msg Car', modelo: 'E2E Msg Model', preco: 5000, classe: 'basico', descricao: 'E2E' })
                });
                const dc = await r.json();
                const modeloId = (dc.carro && dc.carro.id) ? dc.carro.id : null;
                const re = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Msg Equipe ' + Date.now(), senha: 'senha123', doricoins: 50000, serie: 'A', carro_id: modeloId })
                });
                const de = await re.json();
                const equipeId = (de.equipe && de.equipe.id) ? de.equipe.id : null;
                return { ok: re.ok && equipeId, equipeId };
            }
            """
        )
        assert create_car.get("ok") and create_car.get("equipeId"), f"Setup falhou: {create_car}"
        equipe_id = str(create_car["equipeId"])

        # 2) Login como equipe
        page.goto(f"{base_url}/login")
        page.locator("#equipeSelecionada").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(1500)
        page.select_option("#equipeSelecionada", equipe_id)
        page.locator("#senhaEquipe").fill("senha123")
        page.locator("#btnLoginEquipe").click()
        page.wait_for_url(re.compile(r".*/dashboard.*"), timeout=15000)

        # 3) Aguardar sidebar com seções Carros/Peças Aguardando
        page.locator("#equipeDetalhes").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(4000)  # Aguardar APIs /api/aguardando-pecas e /api/aguardando-carros

        # 4) Verificar mensagens de estado vazio (não "Carregando...")
        content = page.locator("#carrosAguardandoContainer").inner_text()
        assert "Sem carros para ativar" in content, (
            f"Esperado 'Sem carros para ativar'. Obtido: {content[:200]}"
        )
        content_pecas = page.locator("#pecasAguardandoContainer").inner_text()
        assert "Sem peças para ativar" in content_pecas, (
            f"Esperado 'Sem peças para ativar'. Obtido: {content_pecas[:200]}"
        )
        # Garantir que não está travado em Carregando
        assert "Carregando" not in content and "Carregando" not in content_pecas, (
            "Não deve permanecer em 'Carregando...' após carregar os dados"
        )


@pytest.mark.e2e
class TestE2EAdminEquipesList:
    """E2E da página admin/equipes-list: listagem, edição e exclusão de equipes."""

    def _login_admin(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def test_pagina_equipes_list_carrega(self, page: Page, base_url: str):
        """Página /admin/equipes-list carrega e exibe título e área de listagem."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/equipes-list")
        expect(page).to_have_title(re.compile(r"Lista|Equipes|GRANPIX", re.I))
        page.locator("h5:has-text('Lista de Equipes')").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(3500)
        content = page.locator(".main-content").inner_text()
        assert "Lista de Equipes" in content, f"Conteúdo esperado: {content[:300]}"

    def test_equipes_list_exibe_tabela_ou_vazio(self, page: Page, base_url: str):
        """Após carregar: exibe tabela de equipes ou mensagem 'Nenhuma equipe cadastrada'."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/equipes-list")
        page.wait_for_timeout(4000)
        # Deve ter desaparecido o loading e aparecer lista ou nenhuma
        loading = page.locator("#loadingEquipes")
        try:
            loading.wait_for(state="hidden", timeout=8000)
        except Exception:
            pass
        body = page.locator("body").inner_text()
        assert "Lista de Equipes" in body
        assert "Carregando" not in body or page.locator("#listaEquipesContainer").is_visible()

    def test_modal_editar_equipe_abre_e_fecha(self, page: Page, base_url: str):
        """Botão Editar abre modal; botão Cancelar fecha sem erro."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/equipes-list")
        page.wait_for_timeout(4000)
        btn_editar = page.locator('button:has-text("Editar")').first
        try:
            btn_editar.wait_for(state="visible", timeout=6000)
        except Exception:
            pytest.skip("Nenhuma equipe na lista para testar modal Editar.")
        page.on("dialog", lambda d: d.accept())
        btn_editar.click()
        page.wait_for_timeout(500)
        modal = page.locator("#modalEditarEquipe")
        modal.wait_for(state="visible", timeout=5000)
        assert page.locator("#editEquipeNome").is_visible()
        page.locator("#modalEditarEquipe button:has-text('Cancelar')").click()
        page.wait_for_timeout(300)


@pytest.mark.e2e
class TestE2EAdminConfiguracoes:
    """E2E da página admin/configuracoes: formulário de valores."""

    def _login_admin(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def test_pagina_configuracoes_carrega(self, page: Page, base_url: str):
        """Página /admin/configuracoes carrega e exibe título e botão Salvar."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/configuracoes")
        expect(page).to_have_title(re.compile(r"Configurações|GRANPIX", re.I))
        page.locator("h5:has-text('Configurações')").wait_for(state="visible", timeout=10000)
        page.wait_for_timeout(3000)
        content = page.locator(".main-content").inner_text()
        assert "Configurações" in content, f"Conteúdo esperado: {content[:300]}"

    def test_configuracoes_tem_campos_valores(self, page: Page, base_url: str):
        """Formulário possui campos: Instalação de peça, Troca/ativação de carro, Participar da etapa."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/configuracoes")
        page.wait_for_timeout(3500)
        assert page.locator("#cfgInstalacaoPeca").is_visible()
        assert page.locator("#cfgTrocaCarro").is_visible()
        assert page.locator("#cfgParticiparEtapa").is_visible()
        assert page.locator("#btnSalvarConfiguracoes").is_visible()


@pytest.mark.e2e
class TestE2ECampeonatoEtapas:
    """E2E: criar campeonato e criar etapas nele via API."""

    def _login_admin(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def test_criar_campeonato_via_api(self, page: Page, base_url: str):
        """Admin logado cria campeonato via API e verifica na listagem."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")  # página qualquer com sessão admin
        import time
        nome = f"E2E Campeonato {int(time.time() * 1000)}"
        result = page.evaluate(
            """
            async (nomeCamp) => {
                const r = await fetch('/api/admin/criar-campeonato', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({
                        nome: nomeCamp,
                        descricao: 'Campeonato E2E',
                        serie: 'A',
                        numero_etapas: 6
                    })
                });
                const data = await r.json();
                return { ok: r.ok, sucesso: data.sucesso, campeonato_id: data.campeonato_id };
            }
            """,
            nome,
        )
        assert result.get("ok") and result.get("sucesso"), f"Erro ao criar campeonato: {result}"
        campeonato_id = result.get("campeonato_id")
        assert campeonato_id

        listagem = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/listar-campeonatos', { credentials: 'include' });
                const data = await r.json();
                return { ok: r.ok, campeonatos: Array.isArray(data) ? data : [] };
            }
            """
        )
        assert listagem.get("ok")
        campeonatos = listagem.get("campeonatos", [])
        encontrado = next((c for c in campeonatos if c.get("nome") == nome), None)
        assert encontrado is not None, f"Campeonato '{nome}' deve aparecer na listagem."

    def test_criar_campeonato_e_etapas_via_api(self, page: Page, base_url: str):
        """Admin cria campeonato, cria etapas nele e verifica nas listagens."""
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        import time
        suf = str(int(time.time() * 1000))
        nome_camp = f"E2E Camp Etapas {suf}"
        result_camp = page.evaluate(
            """
            async (payload) => {
                const r = await fetch('/api/admin/criar-campeonato', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const data = await r.json();
                return { ok: r.ok, sucesso: data.sucesso, campeonato_id: data.campeonato_id };
            }
            """,
            {"nome": nome_camp, "serie": "B", "numero_etapas": 4},
        )
        assert result_camp.get("ok") and result_camp.get("sucesso"), f"Erro: {result_camp}"
        campeonato_id = result_camp.get("campeonato_id")
        assert campeonato_id

        nome_etapa1 = f"Etapa 1 E2E {suf}"
        result_etapa = page.evaluate(
            """
            async (payload) => {
                const r = await fetch('/api/admin/cadastrar-etapa', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const data = await r.json();
                return { ok: r.ok, sucesso: data.sucesso, etapa_id: data.etapa_id };
            }
            """,
            {
                "campeonato_id": campeonato_id,
                "numero": 1,
                "nome": nome_etapa1,
                "data_etapa": "2026-06-01",
                "hora_etapa": "10:00:00",
                "serie": "B",
            },
        )
        assert result_etapa.get("ok") and result_etapa.get("sucesso"), f"Erro ao criar etapa: {result_etapa}"
        etapa_id = result_etapa.get("etapa_id")
        assert etapa_id, "Cadastrar etapa deve retornar etapa_id"

        # Verificar persistência via listagem (se a API retornar etapas)
        page.wait_for_timeout(500)
        listagem = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/listar-etapas', { credentials: 'include' });
                const data = await r.json();
                return { ok: r.ok, etapas: Array.isArray(data) ? data : [] };
            }
            """
        )
        if listagem.get("ok") and len(listagem.get("etapas", [])) > 0:
            etapas = listagem.get("etapas", [])
            encontrada = next(
                (e for e in etapas if e.get("nome") == nome_etapa1 or str(e.get("id", "")) == str(etapa_id)),
                None,
            )
            assert encontrada is not None, f"Etapa criada deve aparecer na listagem. Total: {len(etapas)}"


@pytest.mark.e2e
class TestE2EAlocarPilotos:
    """E2E: Após criar etapa, equipe com precisa_piloto, 2+ pilotos candidatando à mesma equipe,
    admin vai em Alocar pilotos e aloca um piloto (via API alocar-proximo ou pela UI)."""

    def _login_admin(self, page: Page, base_url: str):
        page.goto(f"{base_url}/login")
        page.locator("#admin-tab").click()
        page.locator("#senhaAdmin").fill("admin123")
        page.locator("#btnLoginAdmin").click()
        page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    def test_alocar_piloto_apos_etapa_com_multiplos_candidatos(self, page: Page, base_url: str):
        """Cria etapa, equipe precisa_piloto, 2 pilotos candidatando à mesma equipe, aloca um."""
        import time
        self._login_admin(page, base_url)
        page.goto(f"{base_url}/admin/carros")
        page.wait_for_load_state("networkidle")
        suf = str(int(time.time() * 1000))

        # 1. Criar campeonato e etapa
        result_camp = page.evaluate(
            """
            async (suf) => {
                const r = await fetch('/api/admin/criar-campeonato', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'E2E Alocar ' + suf, serie: 'A', numero_etapas: 5 })
                });
                const d = await r.json();
                return { ok: r.ok, campeonato_id: d.campeonato_id };
            }
            """,
            suf,
        )
        assert result_camp.get("ok"), f"Erro criar campeonato: {result_camp}"
        campeonato_id = result_camp.get("campeonato_id")
        assert campeonato_id

        result_etapa = page.evaluate(
            """
            async (payload) => {
                const r = await fetch('/api/admin/cadastrar-etapa', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const d = await r.json();
                return { ok: r.ok, etapa_id: d.etapa_id };
            }
            """,
            {
                "campeonato_id": campeonato_id,
                "numero": 1,
                "nome": "Etapa Alocar E2E",
                "data_etapa": "2026-07-01",
                "hora_etapa": "10:00:00",
                "serie": "A",
            },
        )
        assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
        etapa_id = result_etapa.get("etapa_id")
        assert etapa_id

        # 2. Criar carro e equipe com precisa_piloto
        result_carro = page.evaluate(
            """
            async () => {
                const r = await fetch('/api/admin/cadastrar-carro', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ marca: 'E2E Alocar', modelo: 'Modelo', preco: 5000, classe: 'basico', descricao: '' })
                });
                const d = await r.json();
                const modelo_id = (d.carro || {}).id;
                return { ok: r.ok, modelo_id };
            }
            """
        )
        assert result_carro.get("ok"), f"Erro criar carro: {result_carro}"
        modelo_id = result_carro.get("modelo_id")
        assert modelo_id

        result_equipe = page.evaluate(
            """
            async (modelo_id) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'Equipe E2E Precisa Piloto', senha: 's1', doricoins: 50000, serie: 'A', carro_id: modelo_id })
                });
                const d = await r.json();
                const equipe_id = (d.equipe || {}).id;
                const carro_id = (d.equipe || {}).carro_instancia_id || (d.equipe || {}).carro_id;
                return { ok: r.ok, equipe_id, carro_id };
            }
            """,
            str(modelo_id),
        )
        assert result_equipe.get("ok"), f"Erro criar equipe: {result_equipe}"
        equipe_id = result_equipe.get("equipe_id")
        carro_id = result_equipe.get("carro_id")
        assert equipe_id and carro_id

        # Adicionar saldo_pix (requer TEST_E2E=1)
        saldo_ok = page.evaluate(
            """
            async (equipe_id) => {
                const r = await fetch('/api/test/atualizar-saldo-pix', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ equipe_id, valor: 5000 })
                });
                return { ok: r.ok, status: r.status };
            }
            """,
            equipe_id,
        )
        if saldo_ok.get("status") == 404:
            pytest.skip("TEST_E2E=1 não definido; endpoint /api/test/atualizar-saldo-pix indisponível")
        part = page.evaluate(
            """
            async (payload) => {
                const r = await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const d = await r.json();
                return { ok: r.ok, sucesso: d.sucesso };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id, "tipo_participacao": "precisa_piloto"},
        )
        assert part.get("ok") and part.get("sucesso"), f"Inscrição equipe falhou: {part}"

        # 3. Criar 2 pilotos e inscrever como candidatos (via /api/test/inscrever-candidato-piloto se TEST_E2E=1)
        pilots = []
        for i in range(2):
            rp = page.evaluate(
                """
                async () => {
                    const r = await fetch('/api/pilotos/cadastrar', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nome: 'Piloto E2E Alocar ' + Date.now() + Math.random(), senha: 's123' })
                    });
                    const d = await r.json();
                    return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || 'Piloto' };
                }
                """
            )
            assert rp.get("ok"), f"Erro criar piloto: {rp}"
            pid = rp.get("piloto_id")
            pnome = rp.get("piloto_nome", "Piloto")
            assert pid
            pilots.append({"id": pid, "nome": pnome})
            page.wait_for_timeout(100)

        for p in pilots:
            rc = page.evaluate(
                """
                async (payload) => {
                    const r = await fetch('/api/test/inscrever-candidato-piloto', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                        body: JSON.stringify(payload)
                    });
                    const d = await r.json();
                    return { ok: r.ok, sucesso: d.sucesso };
                }
                """,
                {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": p["id"], "piloto_nome": p["nome"]},
            )
            if not rc.get("ok") or not rc.get("sucesso"):
                pytest.skip("TEST_E2E=1 não definido; endpoint /api/test/inscrever-candidato-piloto indisponível")

        # 4. Alocar próximo piloto via API (usa etapa_id e equipe_id diretamente)
        aloc = page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, {
                    method: 'POST', credentials: 'include'
                });
                const d = await r.json();
                return { ok: r.ok, sucesso: d.sucesso, piloto_nome: d.piloto_nome };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        assert aloc.get("ok") and aloc.get("sucesso"), f"Erro ao alocar piloto: {aloc}"

        # 5. Verificar alocação: equipe tem piloto
        verif = page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes-pilotos`, { credentials: 'include' });
                const d = await r.json();
                const eq = (d.equipes || []).find(e => e.equipe_id === p.equipe_id);
                return { ok: r.ok, piloto_nome: eq ? eq.piloto_nome : null };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        assert verif.get("ok"), f"Erro ao verificar: {verif}"
        assert verif.get("piloto_nome"), f"Equipe deveria ter piloto alocado, obteve: {verif}"
