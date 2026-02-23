"""
E2E: Fluxo completo da etapa no admin Fazer Etapa.
- Tabela de qualify
- Botão "Finalizar Qualificação" abaixo da tabela
- Após clicar: tabela ordenada (soma das notas) aparece
- Chamadas Challonge enviadas; chaveamento das batalhas aparece em cards

Requer: app rodando com TEST_E2E=1 (run_com_e2e.bat)
Rodar: pytest tests/e2e/test_etapa_completa_visual.py -v -s --headed
- test_etapa_batalhas_modal_e_colocacoes: pausa no modal para você escolher qual piloto avança; após Continue,
  completa as batalhas via API e verifica a lista de colocações abaixo dos cards.
"""
import time
import pytest
import re
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_etapa_qualify_finalizar_challonge_batalhas(page: Page, base_url: str):
    """
    Fluxo: login admin -> cria etapa+equipes+pilotos -> inicia qualify ->
    salva notas via API -> abre fazer-etapa -> clica Finalizar Qualificação ->
    verifica tabela ordenada e chaveamento Challonge em cards.
    """
    # 1. Login admin
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    suf = str(int(time.time() * 1000))

    # 2. Criar campeonato e etapa
    result_camp = page.evaluate(
        """
        async (suf) => {
            const r = await fetch('/api/admin/criar-campeonato', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ nome: 'E2E Etapa Visual ' + suf, serie: 'A', numero_etapas: 5 })
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
            "nome": "Etapa E2E Visual",
            "data_etapa": "2026-08-15",
            "hora_etapa": "10:00:00",
            "serie": "A",
        },
    )
    assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
    etapa_id = result_etapa.get("etapa_id")
    assert etapa_id

    # 3. Criar carro modelo
    result_carro = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/cadastrar-carro', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ marca: 'E2E Visual', modelo: 'Q1', preco: 5000, classe: 'basico', descricao: '' })
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

    # 4. Criar 4 equipes com pilotos alocados
    equipes_ids = []
    for i in range(4):
        idx = i + 1
        r_eq = page.evaluate(
            """
            async ([modelo_id, idx]) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        nome: 'Equipe Q' + idx, senha: 's1', doricoins: 50000,
                        serie: 'A', carro_id: modelo_id
                    })
                });
                const d = await r.json();
                const eq = d.equipe || {};
                return { ok: r.ok, equipe_id: eq.id, carro_id: eq.carro_instancia_id || eq.carro_id };
            }
            """,
            [str(modelo_id), idx],
        )
        assert r_eq.get("ok"), f"Erro criar equipe {i+1}: {r_eq}"
        equipe_id = r_eq.get("equipe_id")
        carro_id = r_eq.get("carro_id")
        assert equipe_id and carro_id

        r_saldo = page.evaluate(
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
        if r_saldo.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário para /api/test/atualizar-saldo-pix")

        page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        etapa_id: p.etapa_id, equipe_id: p.equipe_id, carro_id: p.carro_id,
                        tipo_participacao: 'precisa_piloto'
                    })
                });
                const d = await r.json();
                return { ok: r.ok, sucesso: d.sucesso };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id},
        )

        r_pil = page.evaluate(
            """
            async (nome) => {
                const r = await fetch('/api/pilotos/cadastrar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nome, senha: 's123' })
                });
                const d = await r.json();
                return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || nome };
            }
            """,
            f"Piloto Q{i+1} {suf[:6]}",
        )
        assert r_pil.get("ok"), f"Erro criar piloto: {r_pil}"
        piloto_id = r_pil.get("piloto_id")
        piloto_nome = r_pil.get("piloto_nome", f"Piloto Q{i+1}")

        r_cand = page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/test/inscrever-candidato-piloto', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        etapa_id: p.etapa_id, equipe_id: p.equipe_id,
                        piloto_id: p.piloto_id, piloto_nome: p.piloto_nome
                    })
                });
                if (r.status === 404) return { ok: false, status: 404 };
                const d = await r.json();
                return { ok: r.ok, sucesso: d.sucesso };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": piloto_id, "piloto_nome": piloto_nome},
        )
        if r_cand.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário para /api/test/inscrever-candidato-piloto")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, {
                    method: 'POST', credentials: 'include'
                });
                const d = await r.json();
                return { ok: r.ok, sucesso: d.sucesso };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        equipes_ids.append({"equipe_id": equipe_id, "nome": f"Equipe Q{i+1}"})
        page.wait_for_timeout(200)

    # 5. Iniciar qualify
    r_fazer = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/admin/fazer-etapa', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ etapa: etapa_id })
            });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso };
        }
        """,
        etapa_id,
    )
    assert r_fazer.get("ok") and r_fazer.get("sucesso"), f"Erro fazer-etapa: {r_fazer}"

    # 6. Salvar notas (Q4 melhor, Q3, Q2, Q1 pior)
    notas = [
        {"equipe_id": equipes_ids[0]["equipe_id"], "nota_linha": 10, "nota_angulo": 8, "nota_estilo": 7},
        {"equipe_id": equipes_ids[1]["equipe_id"], "nota_linha": 12, "nota_angulo": 9, "nota_estilo": 8},
        {"equipe_id": equipes_ids[2]["equipe_id"], "nota_linha": 14, "nota_angulo": 10, "nota_estilo": 9},
        {"equipe_id": equipes_ids[3]["equipe_id"], "nota_linha": 15, "nota_angulo": 11, "nota_estilo": 10},
    ]
    r_notas = page.evaluate(
        """
        async (payload) => {
            const r = await fetch('/api/test/salvar-notas-etapa', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify(payload)
            });
            if (r.status === 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso, status: r.status };
        }
        """,
        {"etapa_id": etapa_id, "notas": notas},
    )
    if r_notas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para /api/test/salvar-notas-etapa")
    assert r_notas.get("ok") and r_notas.get("sucesso"), f"Erro salvar notas: {r_notas}"

    # 7. Ir para fazer-etapa
    page.goto(f"{base_url}/admin/fazer-etapa?etapa_id={etapa_id}")
    page.wait_for_load_state("networkidle")

    # 8. Aguardar tabela
    page.wait_for_timeout(1500)
    iniciar_btn = page.locator("#botaoIniciarQualificacao")
    if iniciar_btn.is_visible():
        iniciar_btn.click()
        page.wait_for_timeout(1500)

    # 9. Aguardar botão Finalizar Qualificação
    container = page.locator("#containerVoltasAdmin")
    container.wait_for(state="visible", timeout=10000)
    expect(container).to_be_visible()

    btn_finalizar = page.locator("#botaoFinalizarQualificacao")
    btn_finalizar.wait_for(state="visible", timeout=10000)
    expect(btn_finalizar).to_be_visible()

    # 10. Aceitar confirm e clicar
    page.on("dialog", lambda d: d.accept())
    btn_finalizar.click()

    # 11. Aguardar Resultado da Qualificação
    secao_resultado = page.locator("#secaoResultadoQualificacao")
    secao_resultado.wait_for(state="visible", timeout=15000)
    expect(secao_resultado).to_be_visible()
    expect(page.locator("#secaoResultadoQualificacao")).to_contain_text("Resultado")

    # 12. Aguardar Chaveamento das Batalhas (cards)
    secao_chaveamento = page.locator("#secaoChaveamentoBatalhas")
    secao_chaveamento.wait_for(state="visible", timeout=15000)
    expect(secao_chaveamento).to_be_visible()
    expect(page.locator("#secaoChaveamentoBatalhas")).to_contain_text("Chaveamento")

    # 13. Pausar na tela das batalhas para análise (deixa o browser aberto)
    page.pause()


@pytest.mark.e2e
def test_etapa_batalhas_ate_final(page: Page, base_url: str):
    """
    Fluxo completo: qualificação + reportar todas as batalhas até a final.
    Login -> etapa+4 equipes -> qualify -> finalizar -> reportar vencedores em cada rodada até a final.
    """
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    suf = str(int(time.time() * 1000))

    result_camp = page.evaluate(
        """
        async (suf) => {
            const r = await fetch('/api/admin/criar-campeonato', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ nome: 'E2E Batalhas Final ' + suf, serie: 'A', numero_etapas: 5 })
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
            "nome": "Etapa Batalhas Final",
            "data_etapa": "2026-08-15",
            "hora_etapa": "10:00:00",
            "serie": "A",
        },
    )
    assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
    etapa_id = result_etapa.get("etapa_id")
    assert etapa_id

    result_carro = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/cadastrar-carro', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ marca: 'E2E', modelo: 'Batalha', preco: 5000, classe: 'basico', descricao: '' })
            });
            const d = await r.json();
            return { ok: r.ok, modelo_id: (d.carro || {}).id };
        }
        """
    )
    assert result_carro.get("ok"), f"Erro criar carro: {result_carro}"
    modelo_id = result_carro.get("modelo_id")
    assert modelo_id

    equipes_ids = []
    for i in range(4):
        idx = i + 1
        r_eq = page.evaluate(
            """
            async ([modelo_id, idx]) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        nome: 'Equipe B' + idx, senha: 's1', doricoins: 50000,
                        serie: 'A', carro_id: modelo_id
                    })
                });
                const d = await r.json();
                const eq = d.equipe || {};
                return { ok: r.ok, equipe_id: eq.id, carro_id: eq.carro_instancia_id || eq.carro_id };
            }
            """,
            [str(modelo_id), idx],
        )
        assert r_eq.get("ok"), f"Erro criar equipe: {r_eq}"
        equipe_id = r_eq.get("equipe_id")
        carro_id = r_eq.get("carro_id")
        assert equipe_id and carro_id

        page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        etapa_id: p.etapa_id, equipe_id: p.equipe_id, carro_id: p.carro_id,
                        tipo_participacao: 'precisa_piloto'
                    })
                });
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id},
        )

        r_pil = page.evaluate(
            """
            async (nome) => {
                const r = await fetch('/api/pilotos/cadastrar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nome, senha: 's123' })
                });
                const d = await r.json();
                return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || nome };
            }
            """,
            f"Piloto B{idx} {suf[:6]}",
        )
        assert r_pil.get("ok"), f"Erro criar piloto: {r_pil}"
        piloto_id = r_pil.get("piloto_id")
        piloto_nome = r_pil.get("piloto_nome", f"Piloto B{idx}")

        r_cand = page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/test/inscrever-candidato-piloto', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        etapa_id: p.etapa_id, equipe_id: p.equipe_id,
                        piloto_id: p.piloto_id, piloto_nome: p.piloto_nome
                    })
                });
                if (r.status === 404) return { ok: false, status: 404 };
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": piloto_id, "piloto_nome": piloto_nome},
        )
        if r_cand.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, {
                    method: 'POST', credentials: 'include'
                });
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        page.evaluate(
            """
            async (equipe_id) => {
                const r = await fetch('/api/test/atualizar-saldo-pix', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ equipe_id, valor: 5000 })
                });
                return { ok: r.ok };
            }
            """,
            equipe_id,
        )
        equipes_ids.append({"equipe_id": equipe_id})
        page.wait_for_timeout(100)

    r_fazer = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/admin/fazer-etapa', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ etapa: etapa_id })
            });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso };
        }
        """,
        etapa_id,
    )
    assert r_fazer.get("ok") and r_fazer.get("sucesso"), f"Erro fazer-etapa: {r_fazer}"

    notas = [
        {"equipe_id": equipes_ids[i]["equipe_id"], "nota_linha": 10 + i, "nota_angulo": 8 + i, "nota_estilo": 7 + i}
        for i in range(4)
    ]
    r_notas = page.evaluate(
        """
        async (payload) => {
            const r = await fetch('/api/test/salvar-notas-etapa', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify(payload)
            });
            if (r.status === 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso, status: r.status };
        }
        """,
        {"etapa_id": etapa_id, "notas": notas},
    )
    if r_notas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para salvar-notas-etapa")
    assert r_notas.get("ok") and r_notas.get("sucesso"), f"Erro salvar notas: {r_notas}"

    page.goto(f"{base_url}/admin/fazer-etapa?etapa_id={etapa_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    iniciar_btn = page.locator("#botaoIniciarQualificacao")
    if iniciar_btn.is_visible():
        iniciar_btn.click()
        page.wait_for_timeout(1500)

    container = page.locator("#containerVoltasAdmin")
    container.wait_for(state="visible", timeout=10000)
    btn_finalizar = page.locator("#botaoFinalizarQualificacao")
    btn_finalizar.wait_for(state="visible", timeout=10000)
    page.on("dialog", lambda d: d.accept())
    btn_finalizar.click()

    secao_chaveamento = page.locator("#secaoChaveamentoBatalhas")
    secao_chaveamento.wait_for(state="visible", timeout=15000)
    expect(secao_chaveamento).to_contain_text("Chaveamento")

    # Reportar todas as batalhas até a final via API
    max_loops = 20  # evita loop infinito
    final_com_vencedor = False
    result = {}
    for _ in range(max_loops):
        result = page.evaluate(
            """
            async (etapa_id) => {
                const br = await fetch('/api/etapas/' + etapa_id + '/bracket-challonge', { credentials: 'include' });
                const data = await br.json();
                if (!data.sucesso || !data.bracket || data.bracket.length === 0)
                    return { ok: false, rodada: null, reportado: 0 };

                let reportado = 0;
                for (const fase of data.bracket) {
                    for (const m of fase.matches || []) {
                        if (!m.winner_id && (m.player1_id || m.player2_id)) {
                            const winner_id = m.player1_id || m.player2_id;
                            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-match-report', {
                                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                                body: JSON.stringify({ match_id: m.match_id, winner_id, scores_csv: '1-0' })
                            });
                            const d = await r.json();
                            if (d.sucesso) reportado++;
                        }
                    }
                }
                const ultimaFase = data.bracket[data.bracket.length - 1];
                const finalWinner = ultimaFase && (ultimaFase.matches || []).some(m => !!m.winner_id);
                return { ok: true, reportado, finalWinner, rodada: data.bracket[data.bracket.length-1]?.label };
            }
            """,
            etapa_id,
        )
        if not result.get("ok"):
            break
        if result.get("finalWinner"):
            final_com_vencedor = True
            break
        if result.get("reportado", 0) == 0:
            break
        page.wait_for_timeout(500)

    assert final_com_vencedor, f"Final não chegou a ter vencedor. Último result: {result}"

    r_finalize = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-finalize', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({})
            });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso };
        }
        """,
        etapa_id,
    )
    assert r_finalize.get("ok") and r_finalize.get("sucesso"), f"Erro ao encerrar torneio Challonge: {r_finalize}"


@pytest.mark.e2e
def test_etapa_torneio_manual_finaliza(page: Page, base_url: str):
    """
    Roda o torneio inteiro: você escolhe quem avança em cada batalha (clique nos cards).
    Quando acabar, dê Continue no Inspector: o teste finaliza no Challonge e mostra o chaveamento.
    Rodar: pytest tests/e2e/test_etapa_completa_visual.py::test_etapa_torneio_manual_finaliza -v -s --headed
    """
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)
    suf = str(int(time.time() * 1000))
    result_camp = page.evaluate(
        """
        async (suf) => {
            const r = await fetch('/api/admin/criar-campeonato', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ nome: 'E2E Torneio Manual ' + suf, serie: 'A', numero_etapas: 5 })
            });
            const d = await r.json();
            return { ok: r.ok, campeonato_id: d.campeonato_id };
        }
        """, suf,
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
        {"campeonato_id": campeonato_id, "numero": 1, "nome": "Etapa Torneio Manual", "data_etapa": "2026-08-15", "hora_etapa": "10:00:00", "serie": "A"},
    )
    assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
    etapa_id = result_etapa.get("etapa_id")
    result_carro = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/cadastrar-carro', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ marca: 'E2E', modelo: 'TM', preco: 5000, classe: 'basico', descricao: '' })
            });
            const d = await r.json();
            return { ok: r.ok, modelo_id: (d.carro || {}).id };
        }
        """
    )
    assert result_carro.get("ok"), f"Erro criar carro: {result_carro}"
    modelo_id = result_carro.get("modelo_id")
    equipes_ids = []
    for i in range(4):
        idx = i + 1
        r_eq = page.evaluate(
            """
            async ([modelo_id, idx]) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'Equipe T' + idx, senha: 's1', doricoins: 50000, serie: 'A', carro_id: modelo_id })
                });
                const d = await r.json();
                const eq = d.equipe || {};
                return { ok: r.ok, equipe_id: eq.id, carro_id: eq.carro_instancia_id || eq.carro_id };
            }
            """, [str(modelo_id), idx],
        )
        assert r_eq.get("ok"), f"Erro criar equipe: {r_eq}"
        equipe_id, carro_id = r_eq.get("equipe_id"), r_eq.get("carro_id")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ etapa_id: p.etapa_id, equipe_id: p.equipe_id, carro_id: p.carro_id, tipo_participacao: 'precisa_piloto' })
                });
                return { ok: r.ok };
            }
            """, {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id},
        )
        r_pil = page.evaluate("async (n) => { const r = await fetch('/api/pilotos/cadastrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome: n, senha: 's123' }) }); const d = await r.json(); return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || n }; }", f"Piloto T{idx} {suf[:6]}")
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
            """, {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": r_pil.get("piloto_id"), "piloto_nome": r_pil.get("piloto_nome", f"Piloto T{idx}")},
        )
        if r_cand.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, { method: 'POST', credentials: 'include' });
                return { ok: r.ok };
            }
            """, {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        page.evaluate("async (id) => { const r = await fetch('/api/test/atualizar-saldo-pix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ equipe_id: id, valor: 5000 }) }); return { ok: r.ok }; }", equipe_id)
        equipes_ids.append(equipe_id)
        page.wait_for_timeout(80)
    r_fazer = page.evaluate("async (id) => { const r = await fetch('/api/admin/fazer-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ etapa: id }) }); const d = await r.json(); return { ok: r.ok, sucesso: d.sucesso }; }", etapa_id)
    assert r_fazer.get("ok") and r_fazer.get("sucesso"), f"Erro fazer-etapa: {r_fazer}"
    notas = [{"equipe_id": equipes_ids[i], "nota_linha": 12 + i, "nota_angulo": 10 + i, "nota_estilo": 9 + i} for i in range(4)]
    r_notas = page.evaluate(
        """
        async (payload) => {
            const r = await fetch('/api/test/salvar-notas-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(payload) });
            if (r.status === 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso, status: r.status };
        }
        """, {"etapa_id": etapa_id, "notas": notas},
    )
    if r_notas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para salvar-notas-etapa")
    assert r_notas.get("ok") and r_notas.get("sucesso"), f"Erro salvar notas: {r_notas}"
    page.goto(f"{base_url}/admin/fazer-etapa?etapa_id={etapa_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    if page.locator("#botaoIniciarQualificacao").is_visible():
        page.locator("#botaoIniciarQualificacao").click()
        page.wait_for_timeout(1500)
    page.locator("#containerVoltasAdmin").wait_for(state="visible", timeout=10000)
    page.on("dialog", lambda d: d.accept())
    page.locator("#botaoFinalizarQualificacao").click()
    page.locator("#secaoChaveamentoBatalhas").wait_for(state="visible", timeout=15000)
    expect(page.locator("#secaoChaveamentoBatalhas")).to_contain_text("Chaveamento")
    expect(page.locator("#chaveamentoBatalhasInline .batalha-card-clickable").first).to_be_visible()
    page.pause()
    for _ in range(30):
        result = page.evaluate(
            """
            async (etapa_id) => {
                const br = await fetch('/api/etapas/' + etapa_id + '/bracket-challonge', { credentials: 'include' });
                const data = await br.json();
                if (!data.sucesso || !data.bracket || data.bracket.length === 0) return { ok: false, reportado: 0 };
                let reportado = 0;
                for (const fase of data.bracket) {
                    for (const m of fase.matches || []) {
                        if (!m.winner_id && (m.player1_id || m.player2_id)) {
                            const winner_id = m.player1_id || m.player2_id;
                            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-match-report', {
                                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                                body: JSON.stringify({ match_id: m.match_id, winner_id, scores_csv: '1-0' })
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
            """, etapa_id,
        )
        if result.get("finalWinner"):
            break
        if result.get("reportado", 0) == 0:
            break
        page.wait_for_timeout(400)
    r_finalize = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-finalize', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({})
            });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso };
        }
        """, etapa_id,
    )
    assert r_finalize.get("ok") and r_finalize.get("sucesso"), f"Erro ao encerrar torneio Challonge: {r_finalize}"
    page.goto(f"{base_url}/admin/fazer-etapa?etapa_id={etapa_id}")
    page.wait_for_load_state("networkidle")
    page.locator("#secaoChaveamentoBatalhas").wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(3000)
    expect(page.locator("#chaveamentoBatalhasInline")).to_contain_text("1º", timeout=15000)


@pytest.mark.e2e
def test_etapa_batalhas_modal_e_colocacoes(page: Page, base_url: str):
    """
    Fluxo: qualificação -> finalizar -> clica no card para abrir modal (escolher piloto que avança).
    Pausa no modal para você interagir; após Continue, completa batalhas via API e verifica lista de colocações.
    Rodar: pytest tests/e2e/test_etapa_completa_visual.py::test_etapa_batalhas_modal_e_colocacoes -v -s --headed
    """
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    suf = str(int(time.time() * 1000))
    result_camp = page.evaluate(
        """
        async (suf) => {
            const r = await fetch('/api/admin/criar-campeonato', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ nome: 'E2E Modal Colocacoes ' + suf, serie: 'A', numero_etapas: 5 })
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
        {"campeonato_id": campeonato_id, "numero": 1, "nome": "Etapa Modal Colocacoes", "data_etapa": "2026-08-15", "hora_etapa": "10:00:00", "serie": "A"},
    )
    assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
    etapa_id = result_etapa.get("etapa_id")
    result_carro = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/cadastrar-carro', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ marca: 'E2E', modelo: 'Modal', preco: 5000, classe: 'basico', descricao: '' })
            });
            const d = await r.json();
            return { ok: r.ok, modelo_id: (d.carro || {}).id };
        }
        """
    )
    assert result_carro.get("ok"), f"Erro criar carro: {result_carro}"
    modelo_id = result_carro.get("modelo_id")
    equipes_ids = []
    for i in range(4):
        idx = i + 1
        r_eq = page.evaluate(
            """
            async ([modelo_id, idx]) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'Equipe M' + idx, senha: 's1', doricoins: 50000, serie: 'A', carro_id: modelo_id })
                });
                const d = await r.json();
                const eq = d.equipe || {};
                return { ok: r.ok, equipe_id: eq.id, carro_id: eq.carro_instancia_id || eq.carro_id };
            }
            """,
            [str(modelo_id), idx],
        )
        assert r_eq.get("ok"), f"Erro criar equipe: {r_eq}"
        equipe_id, carro_id = r_eq.get("equipe_id"), r_eq.get("carro_id")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ etapa_id: p.etapa_id, equipe_id: p.equipe_id, carro_id: p.carro_id, tipo_participacao: 'precisa_piloto' })
                });
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id},
        )
        r_pil = page.evaluate("async (n) => { const r = await fetch('/api/pilotos/cadastrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome: n, senha: 's123' }) }); const d = await r.json(); return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || n }; }", f"Piloto M{idx} {suf[:6]}")
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
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": r_pil.get("piloto_id"), "piloto_nome": r_pil.get("piloto_nome", f"Piloto M{idx}")},
        )
        if r_cand.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, { method: 'POST', credentials: 'include' });
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        page.evaluate("async (id) => { const r = await fetch('/api/test/atualizar-saldo-pix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ equipe_id: id, valor: 5000 }) }); return { ok: r.ok }; }", equipe_id)
        equipes_ids.append(equipe_id)
        page.wait_for_timeout(80)

    r_fazer = page.evaluate("async (id) => { const r = await fetch('/api/admin/fazer-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ etapa: id }) }); const d = await r.json(); return { ok: r.ok, sucesso: d.sucesso }; }", etapa_id)
    assert r_fazer.get("ok") and r_fazer.get("sucesso"), f"Erro fazer-etapa: {r_fazer}"
    notas = [{"equipe_id": equipes_ids[i], "nota_linha": 12 + i, "nota_angulo": 10 + i, "nota_estilo": 9 + i} for i in range(4)]
    r_notas = page.evaluate(
        """
        async (payload) => {
            const r = await fetch('/api/test/salvar-notas-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(payload) });
            if (r.status === 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso, status: r.status };
        }
        """,
        {"etapa_id": etapa_id, "notas": notas},
    )
    if r_notas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para salvar-notas-etapa")
    assert r_notas.get("ok") and r_notas.get("sucesso"), f"Erro salvar notas: {r_notas}"

    page.goto(f"{base_url}/admin/fazer-etapa?etapa_id={etapa_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    if page.locator("#botaoIniciarQualificacao").is_visible():
        page.locator("#botaoIniciarQualificacao").click()
        page.wait_for_timeout(1500)
    page.locator("#containerVoltasAdmin").wait_for(state="visible", timeout=10000)
    page.on("dialog", lambda d: d.accept())
    page.locator("#botaoFinalizarQualificacao").click()
    page.locator("#secaoChaveamentoBatalhas").wait_for(state="visible", timeout=15000)
    expect(page.locator("#secaoChaveamentoBatalhas")).to_contain_text("Chaveamento")

    card = page.locator(".batalha-card-clickable").first
    card.wait_for(state="visible", timeout=5000)
    card.click()
    page.wait_for_timeout(500)
    expect(page.locator("#modalPartidaBatalha")).to_be_visible()
    page.pause()

    result = {}
    for _ in range(25):
        result = page.evaluate(
            """
            async (etapa_id) => {
                const br = await fetch('/api/etapas/' + etapa_id + '/bracket-challonge', { credentials: 'include' });
                const data = await br.json();
                if (!data.sucesso || !data.bracket || data.bracket.length === 0) return { ok: false, reportado: 0 };
                let reportado = 0;
                for (const fase of data.bracket) {
                    for (const m of fase.matches || []) {
                        if (!m.winner_id && (m.player1_id || m.player2_id)) {
                            const winner_id = m.player1_id || m.player2_id;
                            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-match-report', {
                                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                                body: JSON.stringify({ match_id: m.match_id, winner_id, scores_csv: '1-0' })
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
        page.wait_for_timeout(400)

    r_finalize = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/etapas/' + etapa_id + '/challonge-finalize', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({})
            });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso };
        }
        """,
        etapa_id,
    )
    assert r_finalize.get("ok") and r_finalize.get("sucesso"), f"Erro ao encerrar torneio Challonge: {r_finalize}"

    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator("#chaveamentoBatalhasInline")).to_contain_text("Colocações", timeout=15000)


@pytest.mark.e2e
def test_etapa_desgaste_passada_visivel(page: Page, base_url: str):
    """
    E2E do desgaste: qualificação -> finalizar -> abre modal -> VOCÊ clica em "Executar passada"
    para rodar os dados de cada passada (máx. 2 vezes). O teste pausa para você clicar.
    Mostra vida dos carros e peças em 2 cards, atualizando após cada passada.
    Rodar: pytest tests/e2e/test_etapa_completa_visual.py::test_etapa_desgaste_passada_visivel -v -s --headed
    """
    page.set_viewport_size({"width": 1920, "height": 1080})  # tela cheia / fullscreen
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    suf = str(int(time.time() * 1000))
    result_camp = page.evaluate(
        """
        async (suf) => {
            const r = await fetch('/api/admin/criar-campeonato', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ nome: 'E2E Desgaste ' + suf, serie: 'A', numero_etapas: 5 })
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
        {"campeonato_id": campeonato_id, "numero": 1, "nome": "Etapa Desgaste", "data_etapa": "2026-08-15", "hora_etapa": "10:00:00", "serie": "A"},
    )
    assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
    etapa_id = result_etapa.get("etapa_id")
    result_carro = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/cadastrar-carro', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ marca: 'E2E', modelo: 'Desg', preco: 5000, classe: 'basico', descricao: '' })
            });
            const d = await r.json();
            return { ok: r.ok, modelo_id: (d.carro || {}).id };
        }
        """
    )
    assert result_carro.get("ok"), f"Erro criar carro: {result_carro}"
    modelo_id = result_carro.get("modelo_id")
    equipes_ids = []
    for i in range(4):
        idx = i + 1
        r_eq = page.evaluate(
            """
            async ([modelo_id, idx]) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ nome: 'Equipe D' + idx, senha: 's1', doricoins: 50000, serie: 'A', carro_id: modelo_id })
                });
                const d = await r.json();
                const eq = d.equipe || {};
                return { ok: r.ok, equipe_id: eq.id, carro_id: eq.carro_instancia_id || eq.carro_id };
            }
            """,
            [str(modelo_id), idx],
        )
        assert r_eq.get("ok"), f"Erro criar equipe: {r_eq}"
        equipe_id, carro_id = r_eq.get("equipe_id"), r_eq.get("carro_id")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ etapa_id: p.etapa_id, equipe_id: p.equipe_id, carro_id: p.carro_id, tipo_participacao: 'precisa_piloto' })
                });
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id},
        )
        r_pil = page.evaluate("async (n) => { const r = await fetch('/api/pilotos/cadastrar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome: n, senha: 's123' }) }); const d = await r.json(); return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || n }; }", f"Piloto D{idx} {suf[:6]}")
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
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": r_pil.get("piloto_id"), "piloto_nome": r_pil.get("piloto_nome", f"Piloto D{idx}")},
        )
        if r_cand.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, { method: 'POST', credentials: 'include' });
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        page.evaluate("async (id) => { const r = await fetch('/api/test/atualizar-saldo-pix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ equipe_id: id, valor: 5000 }) }); return { ok: r.ok }; }", equipe_id)
        equipes_ids.append(equipe_id)
        page.wait_for_timeout(80)

    r_fazer = page.evaluate("async (id) => { const r = await fetch('/api/admin/fazer-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ etapa: id }) }); const d = await r.json(); return { ok: r.ok, sucesso: d.sucesso }; }", etapa_id)
    assert r_fazer.get("ok") and r_fazer.get("sucesso"), f"Erro fazer-etapa: {r_fazer}"
    notas = [{"equipe_id": equipes_ids[i], "nota_linha": 12 + i, "nota_angulo": 10 + i, "nota_estilo": 9 + i} for i in range(4)]
    if not notas:
        pytest.skip("Nenhuma equipe na etapa")
    r_notas = page.evaluate(
        """
        async (payload) => {
            const r = await fetch('/api/test/salvar-notas-etapa', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(payload) });
            if (r.status === 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso, status: r.status };
        }
        """,
        {"etapa_id": etapa_id, "notas": notas},
    )
    if r_notas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para salvar-notas-etapa")
    assert r_notas.get("ok") and r_notas.get("sucesso"), f"Erro salvar notas: {r_notas}"

    r_pecas = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/test/garantir-pecas-etapa', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ etapa_id })
            });
            if (r.status === 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, ...d, status: r.status };
        }
        """,
        etapa_id,
    )
    if r_pecas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para garantir-pecas-etapa")
    assert r_pecas.get("ok"), f"Erro garantir peças: {r_pecas}"

    page.evaluate(
        """
        async () => {
            const put = await fetch('/api/admin/configuracoes', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ chave: 'dado_dano', valor: '20', descricao: 'Dado de dano' })
            });
            return { ok: put.ok };
        }
        """
    )

    page.goto(f"{base_url}/admin/fazer-etapa?etapa_id={etapa_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    if page.locator("#botaoIniciarQualificacao").is_visible():
        page.locator("#botaoIniciarQualificacao").click()
        page.wait_for_timeout(1500)
    page.locator("#containerVoltasAdmin").wait_for(state="visible", timeout=10000)
    page.on("dialog", lambda d: d.accept())
    page.locator("#botaoFinalizarQualificacao").click()
    page.locator("#secaoChaveamentoBatalhas").wait_for(state="visible", timeout=15000)
    expect(page.locator("#secaoChaveamentoBatalhas")).to_contain_text("Chaveamento")

    card = page.locator(".batalha-card-clickable").first
    card.wait_for(state="visible", timeout=5000)
    card.click()
    page.wait_for_timeout(800)
    expect(page.locator("#modalPartidaBatalha")).to_be_visible()
    expect(page.locator("#btnExecutarPassada")).to_be_visible()
    expect(page.locator("#modalP1Vida")).to_be_visible()
    expect(page.locator("#modalP2Vida")).to_be_visible()
    page.wait_for_timeout(500)  # aguardar carregar vida das peças
    v1 = page.locator("#modalP1Vida").inner_text()
    v2 = page.locator("#modalP2Vida").inner_text()
    print("\n--- Vida Carro 1 ---\n" + (v1 or "(vazio)") + "\n--- Vida Carro 2 ---\n" + (v2 or "(vazio)"))

    # Você clica para rodar os dados de cada passada (máx. 2 vezes); os cards de vida atualizam após cada passada
    page.pause()  # Clique em "Executar passada" para a 1ª passada. Depois Continue no Inspector.
    page.wait_for_timeout(2000)
    v1a = page.locator("#modalP1Vida").inner_text()
    v2a = page.locator("#modalP2Vida").inner_text()
    print("\n--- Vida APÓS Passada 1 ---\nCarro 1:\n" + (v1a or "(vazio)") + "\nCarro 2:\n" + (v2a or "(vazio)"))
    resultado_box = page.locator("#resultadoPassada")
    if resultado_box.is_visible():
        conteudo = page.locator("#resultadoPassadaConteudo").inner_text()
        print("\n" + "=" * 60)
        print("DANOS E VALORES DOS DADOS (Passada 1):")
        print("=" * 60)
        print(conteudo or "(nenhum resultado ainda)")
        print("=" * 60)

    page.pause()  # Clique em "Executar passada" para a 2ª passada (opcional). Depois Continue.
    page.wait_for_timeout(2000)
    v1b = page.locator("#modalP1Vida").inner_text()
    v2b = page.locator("#modalP2Vida").inner_text()
    print("\n--- Vida APÓS Passada 2 ---\nCarro 1:\n" + (v1b or "(vazio)") + "\nCarro 2:\n" + (v2b or "(vazio)"))
    if resultado_box.is_visible():
        conteudo2 = page.locator("#resultadoPassadaConteudo").inner_text()
        print("\n" + "=" * 60)
        print("DANOS E VALORES DOS DADOS (Passada 2):")
        print("=" * 60)
        print(conteudo2 or "(nenhum resultado)")
        print("=" * 60)

    span_count = page.locator("#passadaCount")
    if span_count.is_visible():
        print("\nContador de passadas:", span_count.inner_text())


# Cenário real: 20 equipes com notas da qualificação (nome, linha, angulo, estilo)
CENARIO_20_EQUIPES = [
    ("ggdrift", 36, 25, 25),
    ("Dsm", 33, 25, 26),
    ("PatrickG", 36, 22, 22),
    ("Hover", 30, 22, 23),
    ("RegLife", 33, 22, 17),
    ("ice team", 30, 18, 18),
    ("s23", 30, 18, 16),
    ("Sem xorah", 31, 15, 16),
    ("Danishow", 28, 17, 15),
    ("chiclete_drift_team", 26, 15, 18),
    ("Colonos Racing", 26, 18, 13),
    ("Smoked Ninja", 26, 11, 9),
    ("Origins", 22, 15, 7),
    ("jc_drift_team", 0, 0, 0),
    ("jc_drift_team_b", 0, 0, 0),
    ("Touge Drift", 0, 0, 0),
    ("Dzu", 0, 0, 0),
    ("ysk95", 0, 0, 0),
    ("Jdl Krm 01", 0, 0, 0),
    ("Dotb", 0, 0, 0),
]


@pytest.mark.e2e
def test_etapa_cenario_20_equipes_qualify_challonge(page: Page, base_url: str):
    """
    Simula cenário real: 20 equipes com notas exatas da qualificação.
    Fluxo: login -> cria etapa+20 equipes -> notas -> finaliza -> Challonge.
    """
    page.goto(f"{base_url}/login")
    page.locator("#admin-tab").click()
    page.locator("#senhaAdmin").fill("admin123")
    page.locator("#btnLoginAdmin").click()
    page.wait_for_url(re.compile(r".*/admin.*"), timeout=25000)

    suf = str(int(time.time() * 1000))

    result_camp = page.evaluate(
        """
        async (suf) => {
            const r = await fetch('/api/admin/criar-campeonato', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ nome: 'E2E 20 Equipes ' + suf, serie: 'A', numero_etapas: 5 })
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
            "nome": "Etapa 20 Equipes",
            "data_etapa": "2026-08-15",
            "hora_etapa": "10:00:00",
            "serie": "A",
        },
    )
    assert result_etapa.get("ok"), f"Erro criar etapa: {result_etapa}"
    etapa_id = result_etapa.get("etapa_id")
    assert etapa_id

    result_carro = page.evaluate(
        """
        async () => {
            const r = await fetch('/api/admin/cadastrar-carro', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ marca: 'E2E', modelo: 'Q20', preco: 5000, classe: 'basico', descricao: '' })
            });
            const d = await r.json();
            return { ok: r.ok, modelo_id: (d.carro || {}).id };
        }
        """
    )
    assert result_carro.get("ok"), f"Erro criar carro: {result_carro}"
    modelo_id = result_carro.get("modelo_id")
    assert modelo_id

    equipes_data = []
    for nome, linha, angulo, estilo in CENARIO_20_EQUIPES:
        r_eq = page.evaluate(
            """
            async ([modelo_id, nome, suf]) => {
                const r = await fetch('/api/admin/cadastrar-equipe', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        nome: nome + ' ' + suf, senha: 's1', doricoins: 50000,
                        serie: 'A', carro_id: modelo_id
                    })
                });
                const d = await r.json();
                const eq = d.equipe || {};
                return { ok: r.ok, equipe_id: eq.id, carro_id: eq.carro_instancia_id || eq.carro_id };
            }
            """,
            [str(modelo_id), nome, suf[:8]],
        )
        assert r_eq.get("ok"), f"Erro criar equipe {nome}: {r_eq}"
        equipe_id = r_eq.get("equipe_id")
        carro_id = r_eq.get("carro_id")
        assert equipe_id and carro_id

        page.evaluate(
            """
            async (equipe_id) => {
                const r = await fetch('/api/test/atualizar-saldo-pix', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ equipe_id, valor: 5000 })
                });
                return { ok: r.ok };
            }
            """,
            equipe_id,
        )

        page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/etapas/equipe/participar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        etapa_id: p.etapa_id, equipe_id: p.equipe_id, carro_id: p.carro_id,
                        tipo_participacao: 'precisa_piloto'
                    })
                });
                const d = await r.json();
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "carro_id": carro_id},
        )

        r_pil = page.evaluate(
            """
            async (nome) => {
                const r = await fetch('/api/pilotos/cadastrar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nome, senha: 's123' })
                });
                const d = await r.json();
                return { ok: r.ok, piloto_id: d.piloto_id, piloto_nome: d.nome || nome };
            }
            """,
            f"Piloto {nome} {suf[:6]}",
        )
        assert r_pil.get("ok"), f"Erro criar piloto: {r_pil}"
        piloto_id = r_pil.get("piloto_id")
        piloto_nome = r_pil.get("piloto_nome", nome)

        r_cand = page.evaluate(
            """
            async (p) => {
                const r = await fetch('/api/test/inscrever-candidato-piloto', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({
                        etapa_id: p.etapa_id, equipe_id: p.equipe_id,
                        piloto_id: p.piloto_id, piloto_nome: p.piloto_nome
                    })
                });
                if (r.status === 404) return { ok: false, status: 404 };
                const d = await r.json();
                return { ok: r.ok, status: r.status };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id, "piloto_id": piloto_id, "piloto_nome": piloto_nome},
        )
        if r_cand.get("status") == 404:
            pytest.skip("TEST_E2E=1 necessário")
        page.evaluate(
            """
            async (p) => {
                const r = await fetch(`/api/admin/etapas/${p.etapa_id}/equipes/${p.equipe_id}/alocar-proximo-piloto`, {
                    method: 'POST', credentials: 'include'
                });
                const d = await r.json();
                return { ok: r.ok };
            }
            """,
            {"etapa_id": etapa_id, "equipe_id": equipe_id},
        )
        equipes_data.append({"equipe_id": equipe_id, "nome": nome, "nota_linha": linha, "nota_angulo": angulo, "nota_estilo": estilo})
        page.wait_for_timeout(100)

    r_fazer = page.evaluate(
        """
        async (etapa_id) => {
            const r = await fetch('/api/admin/fazer-etapa', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify({ etapa: etapa_id })
            });
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso };
        }
        """,
        etapa_id,
    )
    assert r_fazer.get("ok") and r_fazer.get("sucesso"), f"Erro fazer-etapa: {r_fazer}"

    notas = [
        {"equipe_id": e["equipe_id"], "nota_linha": e["nota_linha"], "nota_angulo": e["nota_angulo"], "nota_estilo": e["nota_estilo"]}
        for e in equipes_data
    ]
    r_notas = page.evaluate(
        """
        async (payload) => {
            const r = await fetch('/api/test/salvar-notas-etapa', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                body: JSON.stringify(payload)
            });
            if (r.status === 404) return { ok: false, status: 404 };
            const d = await r.json();
            return { ok: r.ok, sucesso: d.sucesso, status: r.status };
        }
        """,
        {"etapa_id": etapa_id, "notas": notas},
    )
    if r_notas.get("status") == 404:
        pytest.skip("TEST_E2E=1 necessário para salvar-notas-etapa")
    assert r_notas.get("ok") and r_notas.get("sucesso"), f"Erro salvar notas: {r_notas}"

    page.goto(f"{base_url}/admin/fazer-etapa?etapa_id={etapa_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    iniciar_btn = page.locator("#botaoIniciarQualificacao")
    if iniciar_btn.is_visible():
        iniciar_btn.click()
        page.wait_for_timeout(1500)

    container = page.locator("#containerVoltasAdmin")
    container.wait_for(state="visible", timeout=10000)
    btn_finalizar = page.locator("#botaoFinalizarQualificacao")
    btn_finalizar.wait_for(state="visible", timeout=10000)
    page.on("dialog", lambda d: d.accept())
    btn_finalizar.click()

    secao_resultado = page.locator("#secaoResultadoQualificacao")
    secao_resultado.wait_for(state="visible", timeout=15000)
    expect(secao_resultado).to_contain_text("Resultado")

    secao_chaveamento = page.locator("#secaoChaveamentoBatalhas")
    secao_chaveamento.wait_for(state="visible", timeout=15000)
    expect(secao_chaveamento).to_contain_text("Chaveamento")

    expect(page.locator("#secaoResultadoQualificacao")).to_contain_text("ggdrift")

    # Pausar na tela das batalhas para análise
    page.pause()
