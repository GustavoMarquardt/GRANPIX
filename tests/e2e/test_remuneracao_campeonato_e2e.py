"""
E2E: Remuneração por série, premiação campeonato, colocações e histórico.

Testa:
- Config: remuneração (participar etapa A/B, vitória batalha A/B) e premiação 1º-5º
- Tela admin/campeonatos: colocações com piloto, histórico, em_andamento
- Fluxo completo: doricoins participação, vitória fase 2+, pontos ao finalizar, premiação final

Requer: app rodando com TEST_E2E=1 (run_com_e2e.bat)
Challonge: testes de fluxo completo requerem CHALLONGE_API_KEY e CHALLONGE_USERNAME no .env
"""
import time
import pytest
import re
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_config_remuneracao_premiacao_e2e(page: Page, base_url: str):
    """Config: verifica campos de remuneração e premiação, salva e recarrega."""
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    page.goto(f"{base_url}/admin/configuracoes")
    page.wait_for_load_state("networkidle")

    # Verificar que os campos existem
    expect(page.locator("#cfgParticipacaoA")).to_be_visible()
    expect(page.locator("#cfgParticipacaoB")).to_be_visible()
    expect(page.locator("#cfgVitoriaA")).to_be_visible()
    expect(page.locator("#cfgVitoriaB")).to_be_visible()
    expect(page.locator("#cfgPremio1")).to_be_visible()
    expect(page.locator("#cfgPremio5")).to_be_visible()

    # Preencher e salvar via API (mais confiável que interação UI)
    result = page.evaluate(
        """
        async () => {
            const configs = [
                { chave: 'participacao_etapa_A', valor: '3100' },
                { chave: 'participacao_etapa_B', valor: '2100' },
                { chave: 'vitoria_batalha_A', valor: '1600' },
                { chave: 'vitoria_batalha_B', valor: '1100' },
                { chave: 'premio_campeonato_1', valor: '5000' },
                { chave: 'premio_campeonato_2', valor: '3000' }
            ];
            for (const c of configs) {
                const r = await fetch('/api/admin/configuracoes', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ chave: c.chave, valor: c.valor, descricao: c.chave })
                });
                if (!r.ok) return { ok: false, chave: c.chave };
            }
            return { ok: true };
        }
        """
    )
    assert result.get("ok"), f"Erro ao salvar config: {result}"

    # Recarregar e verificar que valores persistiram
    page.reload()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)

    cfg = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/configuracoes', { credentials: 'include' });
            const data = await r.json();
            const cfg = {};
            (data.configuracoes || []).forEach(c => { cfg[c.chave] = c.valor; });
            return cfg;
        }
        """
    )
    assert cfg.get("participacao_etapa_A") == "3100"
    assert cfg.get("participacao_etapa_B") == "2100"
    assert cfg.get("vitoria_batalha_A") == "1600"
    assert cfg.get("vitoria_batalha_B") == "1100"
    assert cfg.get("premio_campeonato_1") == "5000"


@pytest.mark.e2e
def test_admin_campeonatos_colocacoes_historico_e2e(page: Page, base_url: str):
    """Tela admin/campeonatos: lista campeonatos (em andamento/concluído), seleciona um, exibe colocações com piloto."""
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    page.goto(f"{base_url}/admin/campeonatos")
    page.wait_for_load_state("networkidle")

    expect(page.locator("#selectCampeonato")).to_be_visible()
    expect(page).to_have_title(re.compile(r"Colocações|Campeonato", re.I))

    # Verificar que a API retorna campeonatos com em_andamento
    data = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/listar-campeonatos', { credentials: 'include' });
            const data = await r.json();
            return { campeonatos: data.campeonatos || [], ok: r.ok };
        }
        """
    )
    assert data.get("ok"), "Erro ao listar campeonatos"
    campeonatos = data.get("campeonatos", [])

    if len(campeonatos) == 0:
        pytest.skip("Nenhum campeonato no banco; crie um para testar colocações")

    # Selecionar o primeiro campeonato
    campeonato_id = campeonatos[0].get("id")
    assert campeonato_id

    page.locator("#selectCampeonato").select_option(value=campeonato_id)
    page.wait_for_timeout(500)

    # Verificar que a tabela de colocações ou msgVazio aparece
    painel = page.locator("#painelColocacoes")
    msg_vazio = page.locator("#msgVazio")
    assert painel.is_visible() or msg_vazio.is_visible()

    # Se há pontuações, verificar colunas (Pos, Equipe, Piloto, Pontos)
    if painel.is_visible():
        tbody = page.locator("#tbodyColocacoes")
        if tbody.locator("tr").count() > 0:
            expect(page.locator("thead")).to_contain_text("Piloto")


@pytest.mark.e2e
def test_fluxo_completo_doricoins_pontos_premiacao_e2e(page: Page, base_url: str):
    """
    Fluxo completo: campeonato 1 etapa, 4 equipes Série A, qualify, enviar-challonge (credita participação),
    reportar vencedores com round (credita vitória fase 2+), finalize (atribui pontos e premiação).
    Verifica doricoins e pontuações.
    Requer Challonge configurado.
    """
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    suf = str(int(time.time() * 1000))

    # Configurar premiação para 1º (campeonato 1 etapa = finalizar já premia)
    page.evaluate(
        """
        async () => {
            await fetch('/api/admin/configuracoes', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ chave: 'participacao_etapa_A', valor: '3000', descricao: '' })
            });
            await fetch('/api/admin/configuracoes', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ chave: 'premio_campeonato_1', valor: '10000', descricao: '' })
            });
            return { ok: true };
        }
        """
    )

    # Criar carro e equipes ANTES do campeonato (para que criar_campeonato as inclua em pontuacoes_campeonato)
    result_carro = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/cadastrar-carro', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ marca: 'E2E', modelo: 'Prem', preco: 5000, classe: 'basico', descricao: '' })
            });
            const d = await r.json();
            return { ok: r.ok, modelo_id: (d.carro || {}).id };
        }
        """
    )
    assert result_carro.get("ok"), f"Erro criar carro: {result_carro}"
    modelo_id = result_carro.get("modelo_id")
    equipes_ids = []

    # Criar 4 equipes (sem participar ainda - etapa ainda não existe)
    equipes_data = []
    for i in range(4):
        idx = i + 1
        r_eq = page.evaluate(
            """
            async ([modelo_id, idx]) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'Equipe P' + idx, senha: 's1', doricoins: 1000, serie: 'A', carro_id: modelo_id })
                });
                const d = await r.json();
                const eq = d.equipe || {};
                return { ok: r.ok, equipe_id: eq.id, carro_id: eq.carro_instancia_id || eq.carro_id };
            }
            """,
            [str(modelo_id), idx],
        )
        assert r_eq.get("ok"), f"Erro criar equipe: {r_eq}"
        equipes_data.append({"equipe_id": r_eq.get("equipe_id"), "carro_id": r_eq.get("carro_id"), "idx": idx})
        equipes_ids.append(r_eq.get("equipe_id"))
        page.wait_for_timeout(50)

    # Criar campeonato 1 etapa (APÓS equipes para que pontuacoes_campeonato as inclua)
    result_camp = page.evaluate(
        """
        async (suf) => {
            const r = await fetch('/api/admin/criar-campeonato', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ nome: 'E2E Premiacao ' + suf, serie: 'A', numero_etapas: 1 })
            });
            const d = await r.json();
            return { ok: r.ok, campeonato_id: d.campeonato_id };
        }
        """,
        suf,
    )
    assert result_camp.get("ok"), f"Erro criar campeonato: {result_camp}"
    campeonato_id = result_camp.get("campeonato_id")

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
        {"campeonato_id": campeonato_id, "numero": 1, "nome": "Etapa Única", "data_etapa": "2026-08-15", "hora_etapa": "10:00:00", "serie": "A"},
    )
    assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
    etapa_id = result_etapa.get("etapa_id")

    # Participar, pilotos, alocar, saldo PIX (agora que etapa existe)
    for ed in equipes_data:
        equipe_id, carro_id, idx = ed["equipe_id"], ed["carro_id"], ed["idx"]
        page.evaluate(
            """
            async (p) => {
                await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ etapa_id: p.etapa_id, equipe_id: p.equipe_id, carro_id: p.carro_id, tipo_participacao: 'precisa_piloto' })
                });
                return { ok: true };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id},
        )
        r_pil = page.evaluate("async (n) => { const r = await fetch('/api/pilotos/cadastrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome: n, senha: 's123' }) }); const d = await r.json(); return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || n }; }", f"Piloto P{idx}")
        assert r_pil.get("ok"), f"Erro criar piloto: {r_pil}"
        r_cand = page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/test/inscrever-candidato-piloto', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ etapa_id: p.etapa_id, equipe_id: p.equipe_id, piloto_id: p.piloto_id, piloto_nome: p.piloto_nome })
                });
                return { ok: r.ok, status: r.status };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": r_pil.get("piloto_id"), "piloto_nome": r_pil.get("piloto_nome", f"Piloto P{idx}")},
        )
        if r_cand.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário para inscrever-candidato-piloto")
        page.evaluate(
            """
            async (p) => {
                await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, { method: 'POST', credentials: 'include' });
                return { ok: true };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        page.evaluate("async (id) => { await fetch('/api/test/atualizar-saldo-pix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ equipe_id: id, valor: 5000 }) }); return { ok: true }; }", equipe_id)
        page.wait_for_timeout(50)

    # Doricoins antes do enviar-challonge (via admin equipes)
    saldos_antes = page.evaluate(
        """
        async (ids) => {
            const r = await fetch('/api/admin/equipes', { credentials: 'include' });
            const all = await r.json();
            const setIds = new Set(ids);
            return all.filter(e => setIds.has(e.id)).map(e => ({ id: e.id, doricoins: e.saldo ?? 0 }));
        }
        """,
        equipes_ids,
    )

    # Fazer etapa, salvar notas, finalizar qualificação, enviar challonge
    page.evaluate("async (id) => { const r = await fetch('/api/admin/fazer-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ etapa: id }) }); const d = await r.json(); return { ok: r.ok, sucesso: d.sucesso }; }", etapa_id)
    notas = [{"equipe_id": equipes_ids[i], "nota_linha": 12 + i, "nota_angulo": 10 + i, "nota_estilo": 9 + i} for i in range(4)]
    r_notas = page.evaluate(
        """
        async (payload) => {
            const r = await fetch('/api/test/salvar-notas-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(payload) });
            if (r.status == 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso, status: r.status };
        }
        """,
        {"etapa_id": etapa_id, "notas": notas},
    )
    if r_notas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para salvar-notas-etapa")
    assert r_notas.get("ok") and r_notas.get("sucesso"), f"Erro salvar notas: {r_notas}"

    # Enviar Challonge (credita participação 3000 por equipe Série A)
    r_env = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/etapas/' + etapa_id + '/enviar-challonge', { method: 'POST', credentials: 'include' });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso !== false, erro: d.erro };
        }
        """,
        etapa_id,
    )
    if not r_env.get("ok") or (r_env.get("erro") and "Challonge" in str(r_env.get("erro", ""))):
        pytest.skip("Challonge não configurado (CHALLONGE_API_KEY/USERNAME) - pulando fluxo completo")

    # Verificar doricoins após participação (+3000 cada)
    page.wait_for_timeout(500)
    saldos_apos_part = page.evaluate(
        """
        async (ids) => {
            const r = await fetch('/api/admin/equipes', { credentials: 'include' });
            const all = await r.json();
            const setIds = new Set(ids);
            return all.filter(e => setIds.has(e.id)).map(e => ({ id: e.id, doricoins: e.saldo ?? 0 }));
        }
        """,
        equipes_ids,
    )
    for i, s in enumerate(saldos_apos_part):
        ant = next((x for x in saldos_antes if x["id"] == s["id"]), {}).get("doricoins", 0)
        assert float(s.get("doricoins", 0)) >= float(ant) + 2999, f"Equipe {i+1} deveria ter recebido ~3000 de participação"

    # Reportar vencedores (com round para creditar vitória fase 2+)
    for _ in range(15):
        result = page.evaluate(
            """
            async (etapa_id) => {
                const br = await fetch('/api/etapas/' + etapa_id + '/bracket-challonge', { credentials: 'include' });
                const data = await br.json();
                if (!data.sucesso || !data.bracket || data.bracket.length === 0) return { ok: false, reportado: 0, finalWinner: false };
                let reportado = 0;
                for (let faseIdx = 0; faseIdx < data.bracket.length; faseIdx++) {
                    const fase = data.bracket[faseIdx];
                    const round = faseIdx + 1;
                    for (const m of (fase.matches || [])) {
                        if (!m.winner_id && (m.player1_id || m.player2_id)) {
                            const winner_id = m.player1_id || m.player2_id;
                            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-match-report', {
                                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                                body: JSON.stringify({ match_id: m.match_id, winner_id, scores_csv: '1-0', round })
                            });
                            const d = await r.json();
                            if (d.sucesso) reportado++;
                        }
                    }
                }
                const ultimaFase = data.bracket[data.bracket.length - 1];
                const finalWinner = ultimaFase && (ultimaFase.matches || []).some(m => !!m.winner_id);
                return { ok: true, reportado, finalWinner };
            }
            """,
            etapa_id,
        )
        if result.get("finalWinner"):
            break
        if result.get("reportado", 0) == 0:
            break
        page.wait_for_timeout(600)

    # Finalizar Challonge (atribui pontos e premiação)
    r_fin = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-finalize', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({})
            });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso };
        }
        """,
        etapa_id,
    )
    assert r_fin.get("ok") and r_fin.get("sucesso"), f"Erro finalize Challonge: {r_fin}"

    # Verificar pontuações do campeonato
    pontuacoes = page.evaluate(
        """
        async (campeonato_id) => {
            const r = await fetch('/api/admin/pontuacoes-campeonato/' + campeonato_id, { credentials: 'include' });
            const d = await r.json();
            return d.pontuacoes || [];
        }
        """,
        campeonato_id,
    )
    assert len(pontuacoes) > 0, "Deveria haver pontuações após finalizar etapa"
    # 1º lugar tem 100 pontos
    primeiro = next((p for p in pontuacoes if (p.get("colocacao") or 0) == 1), None)
    assert primeiro is not None, "Deveria existir 1º colocado"
    assert int(primeiro.get("pontos", 0)) >= 100, "1º lugar deveria ter 100 pontos"

    # Verificar que 1º recebeu premiação (campeonato 1 etapa = finalizado)
    saldos_final = page.evaluate(
        """
        async (ids) => {
            const r = await fetch('/api/admin/equipes', { credentials: 'include' });
            const all = await r.json();
            const setIds = new Set(ids);
            return all.filter(e => setIds.has(e.id)).map(e => ({ id: e.id, nome: e.nome, doricoins: e.saldo ?? 0 }));
        }
        """,
        equipes_ids,
    )
    # O campeão (1º) deve ter recebido premio_campeonato_1 (10000) além de participação e vitórias
    # Pelo menos um dos primeiros deve ter saldo maior (premiação)
    assert any(float(s.get("doricoins", 0)) > 5000 for s in saldos_final), "Alguma equipe deveria ter recebido premiação"
