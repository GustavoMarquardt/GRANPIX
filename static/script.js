// Estado global
let equipeAtual = null;
let carros = [];
let pecas = [];
let carrinho = [];  // Carrinho de peças {id, nome, preco, compatibilidade}
let carrinhoArmazem = [];  // Carrinho de peças do armazém {nome, tipo, id, preco, quantidade, pix_id}
let destinoCarrinhoArmazem = null;  // 'ativo' ou 'repouso'

// Cache para evitar atualizações desnecessárias e flicker
let _cachePecasAguardando = null;
let _cacheCarrosAguardando = null;
let _cacheGaragem = null;
let _cacheCarrosLoja = null;
let _cachePecasLoja = null;
let _cacheSolicitacoesPecas = null;
let _cacheSolicitacoesCarros = null;

// Função global para contadores admin - só atualiza DOM se valor mudou (evita flicker)
window.atualizarContadoresSolicitacoesAdmin = async function() {
    try {
        const [rP, rC] = await Promise.all([
            fetch('/api/admin/solicitacoes-pecas'),
            fetch('/api/admin/solicitacoes-carros')
        ]);
        const pecas = await rP.json();
        const carros = await rC.json();
        const nPecas = Array.isArray(pecas) ? pecas.filter(s => s.status === 'pendente').length : 0;
        const nCarros = Array.isArray(carros) ? carros.filter(s => s.status === 'pendente').length : 0;
        const ep = document.getElementById('solicitacoesPecasPendentes');
        const ec = document.getElementById('solicitacoesCarrosPendentes');
        if (ep && String(ep.textContent) !== String(nPecas)) ep.textContent = nPecas;
        if (ec && String(ec.textContent) !== String(nCarros)) ec.textContent = nCarros;
    } catch (e) { console.error('Erro atualizar contadores:', e); }
};

// ============= AUTO-REFRESH DO SISTEMA =============
let intervaloAutoRefresh = null;
let intervaloSolicitacoes = null;

function temModalAberto() {
    // Verificar se algum modal do Bootstrap está aberto
    const modals = document.querySelectorAll('.modal');
    for (let modal of modals) {
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        if (bootstrapModal && bootstrapModal._isShown) {
            return true;
        }
        // Alternativa: verificar a classe "show"
        if (modal.classList.contains('show')) {
            return true;
        }
    }
    return false;
}

function iniciarAutoRefresh() {
    console.log('[AUTO-REFRESH] Iniciando auto-refresh do sistema...');

    // Recarregar dados gerais a cada 5 segundos (apenas aba ativa)
    if (intervaloAutoRefresh) clearInterval(intervaloAutoRefresh);
    intervaloAutoRefresh = setInterval(() => {
        if (document.hidden) return; // Não atualizar se aba não está visível
        if (temModalAberto()) return; // Não atualizar se tem modal aberto

        if (window.location.pathname === '/dashboard') {
            const abaAtiva = obterAbaAtiva();
            if (abaAtiva) {
                // Recarregar apenas dados da aba ativa
                switch (abaAtiva) {
                    case 'garagem-tab':
                        carregarGaragem();
                        recarregarDadosEquipe();
                        break;
                    case 'carros-tab':
                        carregarCarrosLoja();
                        recarregarDadosEquipe();
                        break;
                    case 'pecas-tab':
                        carregarPecasLoja();
                        recarregarDadosEquipe();
                        break;
                    default:
                        recarregarDadosEquipe();
                        break;
                }
            }
        }
    }, 5000);

    // Recarregar solicitações a cada 3 segundos
    if (intervaloSolicitacoes) clearInterval(intervaloSolicitacoes);
    intervaloSolicitacoes = setInterval(() => {
        if (document.hidden) return;
        if (temModalAberto()) return; // Não atualizar se tem modal aberto

        // Dashboard - solicitações de peças e carros
        if (window.location.pathname === '/dashboard') {
            carregarPecasAguardando();
            carregarCarrosAguardando();
        }

        // Página de solicitações de peças
        if (window.location.pathname === '/solicitacoes-pecas') {
            carregarPecasAguardando();
        }

        // Página de solicitações de carros
        if (window.location.pathname === '/solicitacoes-carros') {
            carregarCarrosAguardando();
        }
    }, 3000);
}

function pararAutoRefresh() {
    console.log('[AUTO-REFRESH] Parando auto-refresh...');
    if (intervaloAutoRefresh) clearInterval(intervaloAutoRefresh);
    if (intervaloSolicitacoes) clearInterval(intervaloSolicitacoes);
}

// Adicionar listeners a TODOS os modals para pausar/retomar auto-refresh
function configurarListenersModals() {
    const modals = document.querySelectorAll('.modal');

    modals.forEach(modal => {
        // Pausar quando modal é mostrado
        modal.addEventListener('show.bs.modal', function () {
            console.log('[AUTO-REFRESH] Modal sendo aberto, pausando...');
            pararAutoRefresh();
        });

        // Retomar quando modal é fechado
        modal.addEventListener('hidden.bs.modal', function () {
            console.log('[AUTO-REFRESH] Modal fechado, retomando...');
            iniciarAutoRefresh();
        });
    });
}

// Monitorar visibilidade da aba - só iniciar refresh se estivermos em página que usa
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        pararAutoRefresh();
    } else {
        const path = window.location.pathname || '';
        if (path === '/dashboard' || path === '/solicitacoes-pecas' || path === '/solicitacoes-carros' || path === '/admin') {
            iniciarAutoRefresh();
        }
    }
});

// Inicializar quando página carrega
document.addEventListener('DOMContentLoaded', function () {
    try {
        if (window.location.pathname === '/dashboard') {
            carregarDetalhesEquipe().then(() => {
                setTimeout(() => verificarEtapaEmAndamento(), 500);
            }).catch(e => console.error('[INIT] Erro carregarDetalhesEquipe:', e));
            obterPrecoInstalacaoWarehouse().catch(e => console.error('[INIT] Erro obterPrecoInstalacaoWarehouse:', e));
            configurarListenersModals();
            configurarCarregamentoLazy(); // Sistema de carregamento lazy
            iniciarAutoRefresh();
        } else if (window.location.pathname === '/solicitacoes-pecas') {
            carregarPecasAguardando();
            configurarListenersModals();
            iniciarAutoRefresh();
        } else if (window.location.pathname === '/solicitacoes-carros') {
            carregarCarrosAguardando();
            configurarListenersModals();
            iniciarAutoRefresh();
        } else if (window.location.pathname === '/admin') {
            // Listener para aba de etapas
            const tabEtapas = document.querySelector('a[href="#cadastro-etapas"]');
            if (tabEtapas) {
                tabEtapas.addEventListener('shown.bs.tab', function () {
                    carregarCampeonatos();
                    carregarEtapasCadastro();
                });
                // Carregar na primeira vez
                carregarCampeonatos();
                carregarEtapasCadastro();
            }
            
            // Listener para aba de equipes
            const tabEquipes = document.querySelector('a[href="#cadastro-equipes"]');
            if (tabEquipes) {
                tabEquipes.addEventListener('shown.bs.tab', function () {
                    carregarEquipesCadastro();
                });
                // Carregar na primeira vez se for a aba ativa
                if (tabEquipes.classList.contains('active')) {
                    carregarEquipesCadastro();
                }
            }
            
            // Listener para aba de peças
            const tabPecas = document.querySelector('a[href="#cadastro-pecas"]');
            if (tabPecas) {
                tabPecas.addEventListener('shown.bs.tab', function () {
                    carregarSolicitacoes();
                    carregarSolicitacoesCarros();
                });
                // Carregar na primeira vez se for a aba ativa
                if (tabPecas.classList.contains('active')) {
                    carregarSolicitacoes();
                    carregarSolicitacoesCarros();
                }
            }
        }
    } catch (e) {
        console.error('[INIT ERROR] Erro durante inicialização:', e);
    }
});

// ============= FUNÇÕES AUXILIARES =============

function obterEquipeIdDaSession() {
    return localStorage.getItem('equipe_id');
}

function obterHeaders() {
    const equipeId = obterEquipeIdDaSession();
    const headers = { 'Content-Type': 'application/json' };
    if (equipeId) {
        headers['X-Equipe-ID'] = equipeId;
    }
    return headers;
}

// ========== SISTEMA DE CARREGAMENTO LAZY POR ABA ==========

// Variáveis para controlar carregamento inicial
let dadosCarregados = {
    garagem: false,
    carrosLoja: false,
    pecasLoja: false,
    equipe: false
};

function obterAbaAtiva() {
    const abasAtivas = document.querySelectorAll('.nav-link.active');
    if (abasAtivas.length > 0) {
        const href = abasAtivas[0].getAttribute('href');
        return href ? href.replace('#', '') : null;
    }
    return null;
}

function carregarDadosPorAba(abaId = null) {
    const aba = abaId || obterAbaAtiva();
    if (!aba) return;

    console.log(`[LAZY-LOAD] Carregando dados para aba: ${aba}`);

    switch (aba) {
        case 'garagem-tab':
            if (!dadosCarregados.garagem) {
                carregarGaragem();
                dadosCarregados.garagem = true;
            }
            if (!dadosCarregados.equipe) {
                recarregarDadosEquipe();
                dadosCarregados.equipe = true;
            }
            break;

        case 'carros-tab':
            if (!dadosCarregados.carrosLoja) {
                carregarCarrosLoja();
                dadosCarregados.carrosLoja = true;
            }
            if (!dadosCarregados.equipe) {
                recarregarDadosEquipe();
                dadosCarregados.equipe = true;
            }
            break;

        case 'pecas-tab':
            if (!dadosCarregados.pecasLoja) {
                carregarPecasLoja();
                dadosCarregados.pecasLoja = true;
            }
            if (!dadosCarregados.equipe) {
                recarregarDadosEquipe();
                dadosCarregados.equipe = true;
            }
            break;

        default:
            // Para outras abas, carregar apenas dados básicos se necessário
            if (!dadosCarregados.equipe) {
                recarregarDadosEquipe();
                dadosCarregados.equipe = true;
            }
            break;
    }
}

function configurarCarregamentoLazy() {
    // Carregar dados da aba inicial (garagem)
    carregarDadosPorAba('garagem-tab');

    // Adicionar event listeners para mudança de abas
    const abas = document.querySelectorAll('.nav-link[data-bs-toggle="tab"]');
    abas.forEach(aba => {
        aba.addEventListener('shown.bs.tab', function(e) {
            const targetId = e.target.getAttribute('href').replace('#', '');
            carregarDadosPorAba(targetId);
        });
    });
}

async function mostrarPitsEtapa(etapaId) {
    console.log('[PITS MODAL] Carregando pits para etapa:', etapaId);
    
    try {
        const resp = await fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos`);
        const data = await resp.json();
        
        if (!data.sucesso || !data.equipes) {
            mostrarToast('Erro ao carregar pits', 'error');
            return;
        }
        
        // Criar modal
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modalPitsEtapa';
        modalDiv.tabIndex = '-1';
        modalDiv.setAttribute('data-bs-backdrop', 'static');
        modalDiv.setAttribute('data-bs-keyboard', 'false');
        
        // Grid de pits com tema vermelho, preto e branco
        let pitsHtml = '<div style="max-height: 70vh; overflow-y: auto; padding: 10px 0;">';
        
        data.equipes.forEach((eq, idx) => {
            const temPiloto = !!eq.piloto_nome;
            const borderColor = temPiloto ? '#ff0000' : '#cc0000';
            const piloIcon = temPiloto ? '🏎️' : '⚠️';
            const piloColor = temPiloto ? '#dc143c' : '#ff6666';
            const ordemQualif = eq.ordem_qualificacao ? String(eq.ordem_qualificacao).padStart(2, '0') : '—';
            
            pitsHtml += `
                <div style="
                    background: linear-gradient(180deg, #0a0a0a 0%, #1a1a1a 100%);
                    border: 3px solid ${borderColor};
                    border-radius: 0px;
                    padding: 18px;
                    margin-bottom: 15px;
                    position: relative;
                    box-shadow: 0 8px 24px rgba(255,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 2px solid rgba(255,0,0,0.3);">
                        <div>
                            <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 2px;">PIT</div>
                            <div style="font-size: 28px; font-weight: bold; color: rgba(255,255,255,0.3); font-family: 'Courier New';">
                                ${String(idx + 1).padStart(2, '0')}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">QUAL</div>
                            <div style="font-size: 26px; font-weight: bold; color: #ff0000; font-family: 'Courier New';">
                                ${ordemQualif}
                            </div>
                        </div>
                    </div>
                    
                    <div style="padding: 8px 0; margin-bottom: 12px;">
                        <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px; text-transform: uppercase;">EQUIPE</div>
                        <div style="font-size: 20px; font-weight: bold; color: #fff; text-shadow: 0 0 15px rgba(255,0,0,0.4);">
                            ${eq.equipe_nome}
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div style="background: rgba(255,0,0,0.1); padding: 10px; border-left: 3px solid ${borderColor}; border-radius: 0;">
                            <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">PILOTO</div>
                            <div style="font-size: 18px; font-weight: bold; color: ${piloColor};">${piloIcon}</div>
                            <div style="font-size: 12px; color: ${piloColor}; margin-top: 4px; word-break: break-word;">
                                ${eq.piloto_nome || 'VAZIO'}
                            </div>
                        </div>
                        
                        <div style="background: rgba(255,0,0,0.1); padding: 10px; border-left: 3px solid ${borderColor}; border-radius: 0;">
                            <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">STATUS</div>
                            <div style="font-size: 12px; font-weight: bold; color: #fff; background: rgba(255,0,0,0.3); padding: 6px 8px; border-radius: 2px; text-align: center;">
                                ${eq.status.toUpperCase()}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        pitsHtml += '</div>';
        
        modalDiv.innerHTML = `
            <div class="modal-dialog modal-fullscreen">
                <div class="modal-content" style="background: #000; border: 2px solid #ff0000;">
                    <div class="modal-header" style="background: linear-gradient(90deg, #1a0000 0%, #330000 100%); border-bottom: 2px solid #ff0000;">
                        <h5 class="modal-title" style="color: #ff0000; font-weight: bold; letter-spacing: 2px; font-size: 24px;">
                            🏁 PITS - ETAPA
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" style="padding: 30px; background: #0a0a0a;">
                        ${pitsHtml}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modalDiv);
        const modal = new bootstrap.Modal(modalDiv);
        modal.show();
        
        // Remover do DOM ao fechar
        modalDiv.addEventListener('hidden.bs.modal', () => {
            modalDiv.remove();
        });
        
    } catch (e) {
        console.error('[PITS MODAL] Erro:', e);
        mostrarToast('Erro ao carregar pits', 'error');
    }
}

// ============= CARREGAMENTO DE DADOS =============

// Variável global para armazenar preço de instalação warehouse
let precoInstalacaoWarehouse = 10; // valor padrão (config admin)

async function obterPrecoInstalacaoWarehouse() {
    /**Obtém o preço configurado para instalação de peças do warehouse*/
    try {
        const respConfig = await fetch('/api/admin/configuracoes', {
            headers: obterHeaders()
        });
        if (respConfig.ok) {
            const configResult = await respConfig.json();
            if (configResult.configuracoes && Array.isArray(configResult.configuracoes)) {
                const config = configResult.configuracoes.find(c => c.chave === 'preco_instalacao_warehouse');
                if (config) {
                    precoInstalacaoWarehouse = parseFloat(config.valor || '10');
                    console.log('[CONFIG] Preço instalação warehouse atualizado:', precoInstalacaoWarehouse);
                    return precoInstalacaoWarehouse;
                }
            }
        }
    } catch (e) {
        console.error('[CONFIG] Erro ao obter preço instalação warehouse:', e);
    }
    return precoInstalacaoWarehouse;
}

async function recarregarDadosEquipe() {
    try {
        const equipeId = obterEquipeIdDaSession();
        if (!equipeId) return;

        const resp = await fetch(`/api/equipes/${equipeId}`, {
            headers: obterHeaders()
        });

        if (resp.ok) {
            equipeAtual = await resp.json();
            renderizarDetalhesEquipe();
            // Recarregar também a garagem para mostrar peças atualizadas
            carregarGaragem();
        }
    } catch (e) {
        console.log('Erro ao recarregar dados da equipe:', e);
    }
}

async function carregarDetalhesEquipe() {
    try {
        const equipeId = obterEquipeIdDaSession();
        if (!equipeId) {
            window.location.href = '/login';
            return;
        }

        const resp = await fetch(`/api/equipes/${equipeId}`, {
            headers: obterHeaders()
        });

        if (!resp.ok) {
            if (resp.status === 401 || resp.status === 403) {
                window.location.href = '/login';
            }
            return;
        }

        equipeAtual = await resp.json();
        renderizarDetalhesEquipe();
    } catch (e) {
        console.log('Erro ao carregar detalhes:', e);
        mostrarToast('Erro ao carregar detalhes', 'error');
    }
}

async function carregarCarrosLoja() {
    try {
        const resp = await fetch('/api/loja/carros', { headers: obterHeaders() });
        carros = await resp.json();
        const hash = JSON.stringify(carros);
        if (_cacheCarrosLoja === hash) return;
        _cacheCarrosLoja = hash;
        renderizarCarros();
    } catch (e) {
        console.error('[ERRO] Erro ao carregar carros:', e);
        _cacheCarrosLoja = null;
        mostrarToast('Erro ao carregar carros', 'error');
    }
}

async function carregarPecasLoja() {
    try {
        const resp = await fetch('/api/loja/pecas', { headers: obterHeaders() });
        pecas = await resp.json();
        const hash = JSON.stringify(pecas);
        if (_cachePecasLoja === hash) return;
        _cachePecasLoja = hash;
        renderizarPecas();
    } catch (e) {
        console.error('[ERRO] Erro ao carregar peças:', e);
        _cachePecasLoja = null;
        mostrarToast('Erro ao carregar peças', 'error');
    }
}

async function carregarHistorico() {
    try {
        const resp = await fetch('/api/historico/compras', {
            headers: obterHeaders()
        });
        const historico = await resp.json();
        renderizarHistorico(historico);
    } catch (e) {
        mostrarToast('Erro ao carregar histórico', 'error');
    }
}

async function carregarGaragem() {
    try {
        const equipeId = obterEquipeIdDaSession();
        if (!equipeId) return;

        const resp = await fetch(`/api/garagem/${equipeId}`, {
            headers: obterHeaders()
        });

        if (!resp.ok) {
            throw new Error('Erro ao carregar garagem');
        }

        let garagem = await resp.json();
        
        // Validar e garantir estrutura mínima
        if (!garagem) garagem = {};
        if (!Array.isArray(garagem.carros)) garagem.carros = [];
        
        console.log('[GARAGEM] Dados recebidos:', {
            temCarros: !!garagem.carros,
            numCarros: garagem.carros?.length || 0,
            estrutura: Object.keys(garagem)
        });
        const respArmazem = await fetch(`/api/armazem/${equipeId}`, {
            headers: obterHeaders()
        });

        let armazem = { pecas_guardadas: [], total: 0 };
        if (respArmazem.ok) {
            armazem = await respArmazem.json();

            if (armazem.pecas_guardadas && armazem.pecas_guardadas.length > 0) {
                console.log('[DEBUG] Peças no armazém:', armazem.pecas_guardadas);
                armazem.total = armazem.pecas_guardadas.length;
            }
        }

        // Carregar solicitações pendentes de mudança de carro
        let solicitacoesPendentes = [];
        let solicitacoesPecasPendentes = [];
        try {
            const respSolicitacoes = await fetch(`/api/admin/solicitacoes-carros`);
            if (respSolicitacoes.ok) {
                const todasSolicitacoes = await respSolicitacoes.json();
                // Filtrar apenas solicitações pendentes desta equipe
                solicitacoesPendentes = todasSolicitacoes.filter(sol =>
                    sol.equipe_id === equipeId && sol.status === 'pendente'
                );
            }
        } catch (e) {
            console.log('Erro ao carregar solicitações de carros:', e);
        }

        // Carregar solicitações pendentes de peças
        try {
            const respSolicitacoesPecas = await fetch(`/api/admin/solicitacoes-pecas`);
            if (respSolicitacoesPecas.ok) {
                const todasSolicitacoesPecas = await respSolicitacoesPecas.json();
                console.log(`[DEBUG] Total solicitações de peças: ${todasSolicitacoesPecas.length}, equipeId: ${equipeId}`);
                // Filtrar apenas solicitações pendentes desta equipe
                solicitacoesPecasPendentes = todasSolicitacoesPecas.filter(sol => {
                    const match = String(sol.equipe_id) === String(equipeId) && sol.status === 'pendente';
                    if (match) {
                        console.log(`[DEBUG] Solicitação pendente encontrada: ${sol.peca_nome} (${sol.peca_tipo})`);
                    }
                    return match;
                });
                console.log(`[DEBUG] Solicitações de peças pendentes filtradas: ${solicitacoesPecasPendentes.length}`);
            }
        } catch (e) {
            console.log('Erro ao carregar solicitações de peças:', e);
        }
        // Armazenar garagem em window para uso em outras funções
        window.garagemAtual = garagem || {};
        
        // Garantir que carros é um array
        if (!Array.isArray(garagem?.carros)) {
            console.warn('[GARAGEM] carros não é um array:', garagem?.carros);
            garagem = { ...garagem, carros: [] };
            window.garagemAtual.carros = [];
        }
        
        // Adicionar armazém aos dados da garagem
        window.garagemAtual.armazem = armazem;

        // Garantir que todos os carros têm um array de peças
        if (garagem && garagem.carros && Array.isArray(garagem.carros)) {
            garagem.carros = garagem.carros.map(carro => ({
                ...carro,
                pecas: carro.pecas || []
            }));
        }

        const payload = { garagem, armazem, solicitacoesPendentes, solicitacoesPecasPendentes };
        const hash = JSON.stringify(payload);
        if (_cacheGaragem === hash) return;
        _cacheGaragem = hash;

        renderizarGaragem(garagem, armazem, solicitacoesPendentes, solicitacoesPecasPendentes);
        atualizarUICarrinho();
        atualizarUICarrinhoArmazem();
        carregarProximaEtapa();
    } catch (e) {
        console.log('Erro ao carregar garagem:', e);
        _cacheGaragem = null;
        mostrarToast('Erro ao carregar garagem', 'error');
    }
}

// ============= RENDERIZAÇÃO =============

function renderizarDetalhesEquipe() {
    if (!equipeAtual) return;

    const container = document.getElementById('equipeDetalhes');
    container.innerHTML = `
        <div class="card mb-3">
            <div class="card-header bg-dark text-white">
                <h5 class="mb-0">Informações</h5>
            </div>
            <div class="card-body">
                <h6>${equipeAtual.nome}</h6>
                
                <div class="stat-card mt-3">
                    <div class="stat-label">Saldo</div>
                    <div class="stat-value">${formatarMoeda(equipeAtual.saldo)}</div>
                </div>
                
                <div class="stat-card mt-2">
                    <div class="stat-label">Carro Atual</div>
                    <div class="stat-value">${equipeAtual.carro ? `${equipeAtual.carro.marca} ${equipeAtual.carro.modelo}` : '-'}</div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header">
                        <h6 class="mb-0">⏳ Carros Aguardando Ativação</h6>
                    </div>
                    <div class="card-body" id="carrosAguardandoContainer">
                        <p class="text-muted">Sem carros para ativar</p>
                    </div>
                </div>
                
                <div class="card mt-3">
                    <div class="card-header">
                        <h6 class="mb-0">⏳ Peças Aguardando Instalação</h6>
                    </div>
                    <div class="card-body" id="pecasAguardandoContainer">
                        <p class="text-muted">Sem peças para ativar</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Limpar cache para forçar atualização (evita ficar em "Carregando" após re-render)
    _cachePecasAguardando = null;
    _cacheCarrosAguardando = null;
    // Carregar peças e carros aguardando
    carregarPecasAguardando();
    carregarCarrosAguardando();
}

async function carregarPecasAguardando() {
    try {
        const resp = await fetch('/api/aguardando-pecas', { headers: obterHeaders() });
        if (!resp.ok) throw new Error('Erro ao carregar peças');
        const pecasAguardando = await resp.json();
        const hash = JSON.stringify(pecasAguardando);
        if (_cachePecasAguardando === hash) return;
        _cachePecasAguardando = hash;
        renderizarPecasAguardando(pecasAguardando);
    } catch (e) {
        console.log('Erro ao carregar peças aguardando:', e);
        _cachePecasAguardando = null;
        const container = document.getElementById('pecasAguardandoContainer');
        if (container) container.innerHTML = '<p class="text-danger">Erro ao carregar peças</p>';
    }
}

function renderizarPecasAguardando(pecas) {
    const container = document.getElementById('pecasAguardandoContainer');
    if (!container) return;

    if (!pecas || !Array.isArray(pecas) || pecas.length === 0) {
        container.innerHTML = '<p class="text-muted">Sem peças para ativar</p>';
        return;
    }

    const tipoMap = {
        'motor': '⚙️ Motor',
        'cambio': '⛓️ Câmbio',
        'kit_angulo': '📐 Kit Ângulo',
        'suspensao': '🔧 Suspensão',
        'diferencial': '🔀 Diferencial'
    };

    container.innerHTML = `<div class="list-group list-group-flush">
        ${pecas.map(p => {
        const tipoLabel = tipoMap[p.peca_tipo] || p.peca_tipo;
        const carroDisplay = p.carro
            ? `${p.carro.marca} ${p.carro.modelo} ${p.carro.status === 'repouso' ? '(Repouso)' : '(Ativo)'}`
            : 'Desconhecido';
        return `
                <div class="list-group-item p-2 mb-2 border rounded">
                    <div class="d-flex justify-content-between align-items-start">
                        <div style="flex: 1;">
                            <h6 class="mb-1">${p.peca_nome}</h6>
                            <small class="text-muted d-block">
                                <strong>Tipo:</strong> ${tipoLabel}<br>
                                <strong>Preço:</strong> ${formatarMoeda(p.preco)}<br>
                                <strong style="color: #dc143c;">🎯 Será instalado em:</strong> <span style="color: #dc143c;">${carroDisplay}</span>
                            </small>
                        </div>
                        <span class="badge bg-warning text-dark">Pendente</span>
                    </div>
                </div>
            `;
    }).join('')}
    </div>`;
}

async function carregarCarrosAguardando() {
    try {
        const resp = await fetch('/api/aguardando-carros', { headers: obterHeaders() });
        if (!resp.ok) throw new Error('Erro ao carregar carros');
        const carrosAguardando = await resp.json();
        const hash = JSON.stringify(carrosAguardando);
        if (_cacheCarrosAguardando === hash) return;
        _cacheCarrosAguardando = hash;
        renderizarCarrosAguardando(carrosAguardando);
    } catch (e) {
        console.log('Erro ao carregar carros aguardando:', e);
        _cacheCarrosAguardando = null;
        const container = document.getElementById('carrosAguardandoContainer');
        if (container) container.innerHTML = '<p class="text-danger">Erro ao carregar carros</p>';
    }
}

const tipoPecaLabel = { motor: 'Motor', cambio: 'Câmbio', suspensao: 'Suspensão', kit_angulo: 'Kit Ângulo', diferencial: 'Diferencial' };

function renderizarCarrosAguardando(carros) {
    const container = document.getElementById('carrosAguardandoContainer');
    if (!container) return;

    if (!carros || !Array.isArray(carros) || carros.length === 0) {
        container.innerHTML = '<p class="text-muted">Sem carros para ativar</p>';
        return;
    }

    container.innerHTML = `<div class="list-group list-group-flush">
        ${carros.map(c => {
        const pecasHtml = (c.pecas && Array.isArray(c.pecas) && c.pecas.length > 0)
            ? `<div class="mt-2 small"><strong class="text-secondary">Peças no carro:</strong><ul class="mb-0 ps-3 mt-1">${c.pecas.map(p => {
                const linhas = [`<li><strong>${tipoPecaLabel[p.tipo] || p.tipo}:</strong> ${p.nome || '—'}</li>`];
                (p.upgrades || []).forEach(u => linhas.push(`<li class="ps-2"><em>Upgrade:</em> ${u || '—'}</li>`));
                return linhas.join('');
            }).join('')}</ul></div>`
            : '<div class="mt-2 small text-muted">Nenhuma peça cadastrada</div>';
        return `
                <div class="list-group-item p-2 mb-2 border rounded">
                    <div class="d-flex justify-content-between align-items-start">
                        <div style="flex: 1;">
                            <h6 class="mb-1">🚗 ${c.marca} ${c.modelo}</h6>
                            <small class="text-muted d-block">
                                <strong style="color: #ff9800;">⏳ Aguardando Ativação</strong>
                            </small>
                            ${pecasHtml}
                        </div>
                        <span class="badge bg-success">Aguardando</span>
                    </div>
                </div>
            `;
    }).join('')}
    </div>`;
}

function renderizarCarros() {
    const container = document.getElementById('carrosGrid');
    if (!container) return; // Se não existe o container, sair silenciosamente
    container.innerHTML = '';

    if (carros.length === 0) {
        container.innerHTML = '<p class="text-muted">Nenhum carro disponível</p>';
        return;
    }

    carros.forEach(carro => {
        // Se o carro tem variações, criar um card para cada variação
        if (carro.variacoes && carro.variacoes.length > 0) {
            carro.variacoes.forEach((variacao, idxVar) => {
                const card = document.createElement('div');
                card.className = 'col-md-6 col-lg-4 mb-3';

                const produtoCard = document.createElement('div');
                produtoCard.className = 'produto-card';

                const header = document.createElement('div');
                header.className = 'produto-header';
                header.textContent = `${carro.modelo} (V${idxVar + 1})`;

                const body = document.createElement('div');
                body.className = 'produto-body';

                // Adicionar imagem se existir
                if (carro.imagem) {
                    const img = document.createElement('img');
                    img.src = carro.imagem;
                    img.style.width = '100%';
                    img.style.height = '220px';
                    img.style.objectFit = 'cover';
                    img.style.borderRadius = '4px';
                    img.style.marginBottom = '10px';
                    img.alt = `${carro.marca} ${carro.modelo}`;
                    body.appendChild(img);
                }

                const marca = document.createElement('p');
                marca.className = 'mb-2';
                marca.innerHTML = `<strong>Marca:</strong> ${carro.marca}`;
                body.appendChild(marca);

                // Adicionar peças da variação
                if (variacao.pecas) {
                    const pecasDiv = document.createElement('div');
                    pecasDiv.className = 'mb-3';
                    pecasDiv.style.backgroundColor = '#f8f9fa';
                    pecasDiv.style.padding = '10px';
                    pecasDiv.style.borderRadius = '4px';
                    pecasDiv.style.fontSize = '0.9em';

                    const pecasTitle = document.createElement('strong');
                    pecasTitle.textContent = '⚙️ Peças:';
                    pecasDiv.appendChild(pecasTitle);

                    const pecasList = document.createElement('div');
                    pecasList.style.marginTop = '8px';

                    // Motor
                    const motorDiv = document.createElement('div');
                    motorDiv.textContent = variacao.pecas.motor ? `🔧 Motor: ${variacao.pecas.motor}` : `🔧 Motor: ❌ Sem motor`;
                    motorDiv.style.color = variacao.pecas.motor ? 'inherit' : '#dc3545';
                    pecasList.appendChild(motorDiv);

                    // Câmbio
                    const cambioDiv = document.createElement('div');
                    cambioDiv.textContent = variacao.pecas.cambio ? `⛓️ Câmbio: ${variacao.pecas.cambio}` : `⛓️ Câmbio: ❌ Sem câmbio`;
                    cambioDiv.style.color = variacao.pecas.cambio ? 'inherit' : '#dc3545';
                    pecasList.appendChild(cambioDiv);

                    // Suspensão
                    const suspensaoDiv = document.createElement('div');
                    suspensaoDiv.textContent = variacao.pecas.suspensao ? `🛞 Suspensão: ${variacao.pecas.suspensao}` : `🛞 Suspensão: ❌ Sem suspensão`;
                    suspensaoDiv.style.color = variacao.pecas.suspensao ? 'inherit' : '#dc3545';
                    pecasList.appendChild(suspensaoDiv);

                    // Kit Ângulo
                    const kitDiv = document.createElement('div');
                    kitDiv.textContent = variacao.pecas.kit_angulo ? `📐 Kit Ângulo: ${variacao.pecas.kit_angulo}` : `📐 Kit Ângulo: ❌ Sem kit ângulo`;
                    kitDiv.style.color = variacao.pecas.kit_angulo ? 'inherit' : '#dc3545';
                    pecasList.appendChild(kitDiv);

                    // Diferencial
                    const diferencialDiv = document.createElement('div');
                    diferencialDiv.textContent = variacao.pecas.diferencial ? `⚡ Diferencial: ${variacao.pecas.diferencial}` : `⚡ Diferencial: ❌ Sem diferencial`;
                    diferencialDiv.style.color = variacao.pecas.diferencial ? 'inherit' : '#dc3545';
                    pecasList.appendChild(diferencialDiv);

                    pecasDiv.appendChild(pecasList);
                    body.appendChild(pecasDiv);
                }

                const preco = document.createElement('div');
                preco.className = 'preco';
                preco.textContent = formatarMoeda(variacao.valor);

                const btn = document.createElement('button');
                btn.className = 'btn-comprar';
                btn.textContent = 'Comprar';
                btn.style.cursor = 'pointer';
                btn.onclick = function (e) {
                    e.stopPropagation();
                    // Usar variacao.id e variacao.valor em vez de carro.id e carro.preco
                    abrirConfirmacao(variacao.id, 'carro', `${carro.modelo} (V${idxVar + 1})`, variacao.valor, true);
                };

                body.appendChild(preco);
                body.appendChild(btn);

                produtoCard.appendChild(header);
                produtoCard.appendChild(body);

                card.appendChild(produtoCard);
                container.appendChild(card);
            });
        } else {
            // Compatibilidade: mostrar carro sem variações (pode não ter variações ainda)
            const card = document.createElement('div');
            card.className = 'col-md-6 col-lg-4 mb-3';

            const produtoCard = document.createElement('div');
            produtoCard.className = 'produto-card';

            const header = document.createElement('div');
            header.className = 'produto-header';
            header.textContent = carro.modelo;

            const body = document.createElement('div');
            body.className = 'produto-body';

            // Adicionar imagem se existir
            if (carro.imagem) {
                const img = document.createElement('img');
                img.src = carro.imagem;
                img.style.width = '100%';
                img.style.height = '220px';
                img.style.objectFit = 'cover';
                img.style.borderRadius = '4px';
                img.style.marginBottom = '10px';
                img.alt = `${carro.marca} ${carro.modelo}`;
                body.appendChild(img);
            }

            const marca = document.createElement('p');
            marca.className = 'mb-2';
            marca.innerHTML = `<strong>Marca:</strong> ${carro.marca}`;
            body.appendChild(marca);

            const preco = document.createElement('div');
            preco.className = 'preco';
            preco.textContent = formatarMoeda(carro.preco);

            const btn = document.createElement('button');
            btn.className = 'btn-comprar';
            btn.textContent = 'Comprar';
            btn.style.cursor = 'pointer';
            btn.onclick = function (e) {
                e.stopPropagation();
                abrirConfirmacao(carro.id, 'carro', carro.modelo, carro.preco, false);
            };

            body.appendChild(preco);
            body.appendChild(btn);

            produtoCard.appendChild(header);
            produtoCard.appendChild(body);

            card.appendChild(produtoCard);
            container.appendChild(card);
        }
    });
}

function renderizarPecas() {
    const container = document.getElementById('pecasGrid');
    if (!container) return; // Se não existe o container, sair silenciosamente
    container.innerHTML = '';

    const filtroTipo = document.getElementById('filtroTipoPeca') ? document.getElementById('filtroTipoPeca').value : '';

    // Verificar se peças foram carregadas
    if (!pecas || pecas.length === 0) {
        container.innerHTML = '<p class="text-muted">Carregando peças...</p>';
        return;
    }

    // Filtrar peças
    let pecasFiltradas = pecas;
    if (filtroTipo) {
        pecasFiltradas = pecas.filter(p => p.tipo === filtroTipo);
    }

    if (pecasFiltradas.length === 0) {
        container.innerHTML = '<p class="text-muted">Nenhuma peça disponível</p>';
        return;
    }

    pecasFiltradas.forEach(peca => {
        const card = document.createElement('div');
        card.className = 'col-md-6 col-lg-4 mb-3';

        // Determinar texto de compatibilidade e validar compatibilidade com carros do usuário
        let textoCompatibilidade = '';
        let podeComprar = true;
        let estilo_card = '';

        if (peca.compatibilidade === 'universal') {
            textoCompatibilidade = '✅ Universal - Compatível com qualquer carro';
            podeComprar = true;  // Universal sempre pode comprar
        } else {
            // Peça compatível com modelo específico
            const nomeModelo = peca.compatibilidade_nome || peca.compatibilidade;
            textoCompatibilidade = `🎯 Compatível com: ${nomeModelo}`;
            podeComprar = false;
            estilo_card = ' produto-card-inativo';  // Desabilitar visualmente

            // Verificar se equipe tem algum carro compatível
            if (equipeAtual && equipeAtual.carros && Array.isArray(equipeAtual.carros)) {
                // Verificar se tem carro com modelo_id compatível
                const temCarroCompativel = equipeAtual.carros.some(carro => {
                    return carro.modelo_id === peca.compatibilidade;
                });
                if (temCarroCompativel) {
                    podeComprar = true;
                    estilo_card = '';  // Remover desabilitação visual
                    textoCompatibilidade = `✅ Compatível com: ${nomeModelo}`;
                }
            }
        }

        let imagemHTML = '';
        if (peca.imagem) {
            imagemHTML = `<div style="margin-bottom: 10px;"><img src="${peca.imagem}" style="width: 100%; height: 400px; object-fit: cover; border-radius: 4px;" alt="${peca.nome}"></div>`;
        }

        const isUpgrade = !!peca.is_upgrade;
        const tipoCarrinho = isUpgrade ? 'upgrade' : peca.tipo;
        const linhaParaPeca = isUpgrade ? `<p class="mb-2"><strong>Para peça:</strong> ${peca.peca_nome || '-'}</p>` : '';

        card.innerHTML = `
            <div class="produto-card${estilo_card}">
                <div class="produto-header">${peca.nome}</div>
                <div class="produto-body">
                    ${imagemHTML}
                    ${linhaParaPeca}
                    <p class="mb-2"><strong>Descrição:</strong> ${peca.descricao || '-'}</p>
                    <p class="mb-2"><small class="text-info">${textoCompatibilidade}</small></p>
                    <div class="preco">${formatarMoeda(peca.preco)}</div>
                    <button class="btn-comprar w-100" onclick="adicionarAoCarrinho('${peca.id}', '${peca.nome.replace(/'/g, "\\'")}', ${peca.preco}, '${peca.compatibilidade}', '${tipoCarrinho}')" ${!podeComprar ? 'disabled' : ''}>
                        🛒 Adicionar ao Carrinho
                    </button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderizarGaragem(garagem, armazem = { pecas_guardadas: [], total: 0 }, solicitacoesPendentes = [], solicitacoesPecasPendentes = []) {
    const container = document.getElementById('garagemContent');
    container.innerHTML = '';

    // ========== SEÇÃO CARROS ==========
    const secaoCarros = document.createElement('div');
    secaoCarros.innerHTML = '<h5 class="mt-4 mb-3">🚗 Carros</h5>';

    if (!garagem || !garagem.carros || garagem.carros.length === 0) {
        secaoCarros.innerHTML += '<p class="text-muted">Você ainda não possui carros na garagem</p>';
    } else {
        // Separar carros ativos dos em repouso
        const carrosAtivos = (garagem.carros || []).filter(c => c && c.status === 'ativo');
        const carrosRepouso = (garagem.carros || []).filter(c => c && c.status !== 'ativo');

        // Renderizar carros ativos: metade tela = card, metade = imagem do carro
        if (carrosAtivos.length > 0) {
            const divAtivos = document.createElement('div');
            divAtivos.className = 'row mb-4 align-items-stretch';

            carrosAtivos.forEach(carro => {
                const condicaoGeral = carro.condicao_geral || 100;
                const corCondicao = condicaoGeral > 75 ? 'success' : condicaoGeral > 50 ? 'warning' : 'danger';
                const statusBadgeClass = 'bg-success';
                const statusText = '🏁 Ativo';

                const apelido = carro.apelido || '';
                const nomeCarro = `${carro.marca} ${carro.modelo}`;
                const imagemUrl = carro.imagem_url || '';
                const escApelido = (apelido || '').replace(/'/g, "\\'");

                let htmlPecas = gerarHtmlPecas(carro);

                const wrapper = document.createElement('div');
                wrapper.className = 'col-12';
                wrapper.innerHTML = `
                    <div class="row g-3 align-items-stretch">
                        <div class="col-md-6">
                            <div class="card border-success border-2 card-garagem-compact h-100">
                                <div class="card-header py-2 bg-success text-white">
                                    <div class="d-flex justify-content-between align-items-start">
                                        <div class="flex-grow-1">
                                            <h6 class="mb-0">${nomeCarro}</h6>
                                            ${apelido ? `<div class="small"><strong>${apelido}</strong></div>` : ''}
                                            <small style="cursor: pointer; opacity: 0.9;" onclick="editarApelidoCarro('${carro.id}', '${escApelido}', this)">✏️ Editar apelido</small>
                                            <br><small style="cursor: pointer; opacity: 0.9;" onclick="document.getElementById('fileImagem_${carro.id}').click()">📷 Carregar imagem</small>
                                            <input type="file" accept="image/*" style="display:none" id="fileImagem_${carro.id}" onchange="enviarImagemCarro('${carro.id}', this)">
                                        </div>
                                        <span class="badge ${statusBadgeClass}">${statusText}</span>
                                    </div>
                                </div>
                                <div class="card-body py-2 px-3">
                                    <div class="mb-2 pb-2 border-bottom">
                                        <small class="text-muted">Status</small>
                                        <div><span class="badge ${statusBadgeClass}">${statusText}</span></div>
                                    </div>
                                    <div class="row mb-2">
                                        <div class="col-6">
                                            <small class="text-muted">Condição</small>
                                            <div class="progress" style="height: 10px;">
                                                <div class="progress-bar bg-${corCondicao}" style="width: ${condicaoGeral}%"></div>
                                            </div>
                                            <div class="small">${condicaoGeral.toFixed(1)}%</div>
                                        </div>
                                        <div class="col-6">
                                            <small class="text-muted">Classe</small>
                                            <div class="badge bg-info">${carro.classe || 'N/A'}</div>
                                        </div>
                                    </div>
                                    <div class="mt-2">
                                        <h6 class="small mb-1">Peças Instaladas:</h6>
                                        ${htmlPecas}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6 d-flex align-items-center justify-content-center bg-dark bg-opacity-10 rounded overflow-hidden" style="min-height: 280px;">
                            ${imagemUrl
                                ? `<img src="${imagemUrl}" alt="${nomeCarro}" class="img-fluid w-100 h-100" style="object-fit: contain; max-height: 320px;">`
                                : `<div class="text-center text-muted py-5 px-3">
                                    <p class="mb-2">📷 Nenhuma foto do carro</p>
                                    <small style="cursor: pointer;" onclick="document.getElementById('fileImagem_${carro.id}').click()">Clique para carregar imagem</small>
                                   </div>`}
                        </div>
                    </div>
                `;
                divAtivos.appendChild(wrapper);
            });
            secaoCarros.appendChild(divAtivos);
        }

        // Renderizar carros em repouso (em linha, um do lado do outro)
        if (carrosRepouso.length > 0) {
            const divRepouso = document.createElement('div');
            divRepouso.innerHTML = '<h6 class="mt-4 mb-3">⏸️ Carros em Repouso</h6>';

            const carrosDiv = document.createElement('div');
            carrosDiv.className = 'row';

            carrosRepouso.forEach(carro => {
                const condicaoGeral = carro.condicao_geral || 100;
                const corCondicao = condicaoGeral > 75 ? 'success' : condicaoGeral > 50 ? 'warning' : 'danger';
                const statusBadgeClass = 'bg-secondary';
                const statusText = '⏸️ Repouso';

                // Apelido do carro
                const apelido = carro.apelido || '';
                const nomeCarro = `${carro.marca} ${carro.modelo}`;

                let htmlPecas = gerarHtmlPecas(carro);

                // Verificar se carro tem todas as peças
                const pecasCompletas = verificarPecasCompletas(carro);

                // Verificar se há solicitação de ativação pendente para este carro
                // O tipo_carro está em formato "UUID|marca|modelo", então extraímos o primeiro parte
                const temSolicitacaoPendente = solicitacoesPendentes && solicitacoesPendentes.some(sol => {
                    const tipoPartes = sol.tipo_carro ? sol.tipo_carro.split('|') : [];
                    const carroIdDaSolicitacao = tipoPartes[0];
                    return carroIdDaSolicitacao === carro.id;
                });

                // Botão desativado se:
                // 1. Carro está ativo OU
                // 2. Há solicitação de ativação pendente OU
                // 3. Faltam peças obrigatórias (motor, câmbio, suspensão, diferencial, kit ângulo)
                const btnDisabled = (carro.status === 'ativo' || temSolicitacaoPendente || !pecasCompletas) ? 'disabled' : '';
                let btnTitle;
                if (carro.status === 'ativo') {
                    btnTitle = 'Carro já está ativo';
                } else if (temSolicitacaoPendente) {
                    btnTitle = 'Aguardando ativação...';
                } else if (!pecasCompletas) {
                    btnTitle = 'Carro com peças faltando - Complete a variação antes de ativar';
                } else {
                    btnTitle = 'Gerar QR Code PIX para ativar este carro';
                }
                const btnClass = (carro.status === 'ativo' || temSolicitacaoPendente || !pecasCompletas) ? 'btn-secondary' : 'btn-primary';
                const imagemUrlRepouso = carro.imagem_url || '';
                const escApelidoRepouso = (apelido || '').replace(/'/g, "\\'");

                const card = document.createElement('div');
                card.className = 'col-md-6 mb-3';
                card.innerHTML = `
                    <div class="card card-garagem-compact">
                        <div class="card-header py-2 bg-dark text-white">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="flex-grow-1">
                                    ${imagemUrlRepouso ? `<img src="${imagemUrlRepouso}" alt="${nomeCarro}" class="rounded me-2 float-start" style="width:48px;height:36px;object-fit:cover;">` : ''}
                                    <h6 class="mb-0">${nomeCarro}</h6>
                                    ${apelido ? `<div class="small"><strong>${apelido}</strong></div>` : ''}
                                    <small style="cursor: pointer; opacity: 0.9;" onclick="editarApelidoCarro('${carro.id}', '${escApelidoRepouso}', this)">✏️ Editar apelido</small>
                                    <br><small style="cursor: pointer; opacity: 0.9;" onclick="document.getElementById('fileImagem_${carro.id}').click()">📷 Carregar imagem</small>
                                    <input type="file" accept="image/*" style="display:none" id="fileImagem_${carro.id}" onchange="enviarImagemCarro('${carro.id}', this)">
                                </div>
                                <span class="badge ${statusBadgeClass}">${statusText}</span>
                            </div>
                        </div>
                        <div class="card-body py-2 px-3">
                            <div class="mb-2 pb-2 border-bottom">
                                <small class="text-muted">Status</small>
                                <div><span class="badge ${statusBadgeClass}">${statusText}</span></div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-6">
                                    <small class="text-muted">Condição</small>
                                    <div class="progress" style="height: 10px;">
                                        <div class="progress-bar bg-${corCondicao}" style="width: ${condicaoGeral}%"></div>
                                    </div>
                                    <div class="small">${condicaoGeral.toFixed(1)}%</div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted">Classe</small>
                                    <div class="badge bg-info">${carro.classe || 'N/A'}</div>
                                </div>
                            </div>
                            <div class="mt-2">
                                <h6 class="small mb-1">Peças Instaladas:</h6>
                                ${htmlPecas}
                            </div>
                            <button class="btn btn-sm btn-success mt-2 w-100"
                                onclick="solicitarMudarCarro('${carro.id}', '${carro.marca} ${carro.modelo}')"
                                title="Ativar carro">
                                💳 Ativar Carro (PIX)
                            </button>
                        </div>
                    </div>
                `;
                carrosDiv.appendChild(card);
            });

            divRepouso.appendChild(carrosDiv);
            secaoCarros.appendChild(divRepouso);
        }
    }

    container.appendChild(secaoCarros);

    // ========== SEÇÃO ARMAZÉM ==========
    const secaoArmazem = document.createElement('div');
    secaoArmazem.innerHTML = '<h5 class="mt-5 mb-3">📦 Armazém</h5>';

    if (!armazem.pecas_guardadas || armazem.pecas_guardadas.length === 0) {
        secaoArmazem.innerHTML += '<p class="text-muted">Nenhuma peça guardada no armazém</p>';
    } else {
        const tabelaArmazem = document.createElement('div');
        tabelaArmazem.className = 'table-responsive';
        tabelaArmazem.innerHTML = `
            <table class="table table-sm table-striped">
                <thead class="table-dark">
                    <tr>
                        <th></th>
                        <th>Peça</th>
                        <th>Tipo</th>
                        <th>Durabilidade</th>
                        <th>Preço</th>
                        <th>Carro Original</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${armazem.pecas_guardadas.map((peca) => {
            const durabilidade = peca.durabilidade_percentual != null ? peca.durabilidade_percentual : 100;
            const durabilidadeClass = durabilidade > 75 ? 'success' : durabilidade > 50 ? 'warning' : 'danger';
            const temPagamento = peca.pix_id ? '<span class="badge bg-success">✓ Pago</span>' : '<span class="badge bg-secondary">Pendente</span>';
            const thumb = peca.imagem ? `<img src="${peca.imagem}" alt="" class="rounded" style="width:36px;height:36px;object-fit:cover;">` : '<span class="text-muted">—</span>';
            const tipoLabel = peca.upgrade_id ? '<span class="badge bg-warning text-dark">Upgrade</span>' : `<span class="badge bg-info">${peca.tipo}</span>`;
            return `
                            <tr>
                                <td>${thumb}</td>
                                <td><strong>${peca.nome}</strong></td>
                                <td>${tipoLabel}</td>
                                <td>
                                    <div class="d-flex align-items-center gap-2">
                                        <div class="progress" style="flex: 1; min-width: 100px; height: 20px;">
                                            <div class="progress-bar bg-${durabilidadeClass}" style="width: ${durabilidade}%"></div>
                                        </div>
                                        <small>${durabilidade}%</small>
                                    </div>
                                </td>
                                <td>${formatarMoeda(peca.preco)}</td>
                                <td><small>${peca.carro_nome}</small></td>
                                <td>${temPagamento}</td>
                            </tr>
                        `;
        }).join('')}
                </tbody>
            </table>
        `;
        
        secaoArmazem.appendChild(tabelaArmazem);
        
        // Botão para adicionar peças (criado como elemento separado)
        const botaoContainer = document.createElement('div');
        botaoContainer.style.marginTop = '15px';
        const botao = document.createElement('button');
        botao.className = 'btn btn-success';
        botao.textContent = '➕ Adicionar Peças do Armazém';
        botao.onclick = function() {
            abrirModalAdicionarPecasArmazem();
        };
        botaoContainer.appendChild(botao);
        secaoArmazem.appendChild(botaoContainer);
    }

    container.appendChild(secaoArmazem);
}

function renderizarHistorico(historico) {
    const container = document.getElementById('historicoList');
    container.innerHTML = '';

    if (historico.length === 0) {
        container.innerHTML = '<p class="text-muted">Nenhuma transação realizada</p>';
        return;
    }

    const statusMap = {
        'pendente': '⏳ Pendente',
        'instalado': '✅ Instalado',
        'guardada': '📦 Guardado',
        'confirmado': '✅ Confirmado'
    };

    const tipoMap = {
        'motor': '⚙️ Motor',
        'cambio': '⛓️ Câmbio',
        'kit_angulo': '📐 Kit Ângulo',
        'suspensao': '🔧 Suspensão',
        'diferencial': '🔀 Diferencial'
    };

    const badgeColorMap = {
        'pendente': 'warning',
        'instalado': 'success',
        'guardada': 'info',
        'confirmado': 'success'
    };

    historico.forEach(item => {
        const div = document.createElement('div');
        div.className = 'card mb-2';

        const dataProcessamento = new Date(item.processado_em).toLocaleString('pt-BR');
        const statusLabel = statusMap[item.status] || item.status;

        // Para transações PIX
        if (item.tipo === 'pix_payment') {
            const tipoItemMap = {
                'carro': '🚗 Carro',
                'peca': '🔩 Peça',
                'warehouse': '📦 Instalação Warehouse'
            };
            const tipoItemLabel = tipoItemMap[item.tipo_item] || item.tipo_item;

            div.innerHTML = `
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div style="flex: 1;">
                            <h6 class="mb-1">💳 ${item.item_nome}</h6>
                            <small class="text-muted d-block">
                                <strong>Tipo:</strong> ${tipoItemLabel}<br>
                                <strong>Data:</strong> ${dataProcessamento}
                            </small>
                        </div>
                        <div class="text-end">
                            <div class="fw-bold">${formatarMoeda(item.valor_total || item.preco)}</div>
                            <span class="badge bg-${badgeColorMap[item.status]}">${statusLabel}</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // Para solicitações de peças
            const tipoLabel = tipoMap[item.peca_tipo] || item.peca_tipo;

            div.innerHTML = `
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div style="flex: 1;">
                            <h6 class="mb-1">${item.peca_nome}</h6>
                            <small class="text-muted d-block">
                                <strong>Tipo:</strong> ${tipoLabel}<br>
                                <strong>Data:</strong> ${dataProcessamento}
                            </small>
                        </div>
                        <div class="text-end">
                            <div class="fw-bold">${formatarMoeda(item.preco)}</div>
                            <span class="badge bg-${badgeColorMap[item.status]}">${statusLabel}</span>
                        </div>
                    </div>
                </div>
            `;
        }
        container.appendChild(div);
    });
}

// ============= MODAL DE CONFIRMAÇÃO =============

let compraPendente = { id: null, tipo: null, nome: '', preco: 0, carroSelecionado: null };

async function abrirEscolherCarro(id, tipo, nome, preco, compatibilidade = 'universal') {
    console.log('[ESCOLHER CARRO] ========== INICIANDO ==========');
    console.log('[ESCOLHER CARRO] id:', id);
    console.log('[ESCOLHER CARRO] tipo:', tipo);
    console.log('[ESCOLHER CARRO] nome:', nome);
    console.log('[ESCOLHER CARRO] preco:', preco);
    console.log('[ESCOLHER CARRO] compatibilidade:', compatibilidade);
    console.log('[ESCOLHER CARRO] equipeAtual:', equipeAtual);

    try {
        alert(`[DEBUG] Clicou em Comprar\nTipo: ${tipo}\nNome: ${nome}`);
    } catch (e) {
        console.error('[ESCOLHER CARRO] Erro ao mostrar alert:', e);
    }

    if (!equipeAtual) {
        mostrarToast('Erro ao carregar equipe', 'error');
        console.error('[ESCOLHER CARRO] equipeAtual é null');
        return;
    }

    if (equipeAtual.saldo < preco) {
        mostrarToast('❌ Saldo insuficiente', 'error');
        console.error('[ESCOLHER CARRO] Saldo insuficiente');
        return;
    }

    // Para peças, precisa escolher o carro
    if (tipo === 'peca') {
        console.log('[ESCOLHER CARRO] Tipo é PEÇA, carregando carros...');
        try {
            const resp = await fetch(`/api/garagem/${obterEquipeIdDaSession()}`, {
                headers: obterHeaders()
            });
            const garagem = await resp.json();

            console.log('[ESCOLHER CARRO] Peça compatibilidade:', compatibilidade);
            console.log('[ESCOLHER CARRO] Carros na garagem:', garagem.carros);

            if (!garagem || !garagem.carros || garagem.carros.length === 0) {
                mostrarToast('Você não possui carros', 'error');
                console.error('[ESCOLHER CARRO] Nenhum carro na garagem');
                return;
            }

            compraPendente = { id, tipo, nome, preco, carroSelecionado: null, compatibilidade: compatibilidade };

            const listaCarros = document.getElementById('listaCarrosModal');
            listaCarros.innerHTML = '';

            // Filtrar carros compatíveis
            const carrosCompativeis = [];

            if (compatibilidade === 'universal') {
                // Se universal, todos os carros são compatíveis
                console.log('[ESCOLHER CARRO] Peça universal, todos carros compatíveis');
                carrosCompativeis.push(...garagem.carros);
            } else {
                // Se tem restrição, apenas carros compatíveis
                const idsCompatibilidade = String(compatibilidade).split(',').map(id => id.trim());
                console.log('[ESCOLHER CARRO] IDs compatibilidade:', idsCompatibilidade);
                console.log('[ESCOLHER CARRO] Comparando com carros:');
                garagem.carros.forEach(carro => {
                    const carroModeloId = String(carro.modelo_id || '').trim();
                    console.log(`  Carro: ${carro.marca} ${carro.modelo}`);
                    console.log(`    modelo_id: '${carroModeloId}'`);
                    console.log(`    Procurando em:`, idsCompatibilidade);
                    const isCompativel = idsCompatibilidade.includes(carroModeloId);
                    console.log(`    Compatível?: ${isCompativel}`);
                    // Verificar se este carro é compatível
                    // Usar modelo_id do carro para comparar
                    if (isCompativel) {
                        carrosCompativeis.push(carro);
                    }
                });
            }

            console.log('[ESCOLHER CARRO] Total de carros compatíveis:', carrosCompativeis.length);

            if (carrosCompativeis.length === 0) {
                listaCarros.innerHTML = '<p class="text-danger">❌ Você não possui carros compatíveis com esta peça!</p>';
            } else {
                // Adicionar opção "Armazém" no topo
                const divArmazem = document.createElement('div');
                divArmazem.className = 'mb-2';
                divArmazem.innerHTML = `
                    <button class="btn btn-warning w-100 text-start" onclick="selecionarCarroPeca('armazem', '📦 Armazém')">
                        📦 Armazém (Guardar peça) - Sem taxa PIX
                    </button>
                `;
                listaCarros.appendChild(divArmazem);

                carrosCompativeis.forEach(carro => {
                    const div = document.createElement('div');
                    div.className = 'mb-2';
                    const statusText = carro.status === 'ativo' ? '🏁 (Ativo)' : '⏸️ (Repouso)';
                    div.innerHTML = `
                        <button class="btn btn-outline-primary w-100 text-start" onclick="selecionarCarroPeca('${carro.id}', '${carro.marca} ${carro.modelo}')">
                            🏎️ ${carro.marca} ${carro.modelo} ${statusText}
                        </button>
                    `;
                    listaCarros.appendChild(div);
                });
            }

            console.log('[ESCOLHER CARRO] Abrindo modal escolherCarroModal...');
            const modal = new bootstrap.Modal(document.getElementById('escolherCarroModal'));
            console.log('[ESCOLHER CARRO] Modal instance criado, mostrando...');
            modal.show();
            alert('[DEBUG] Modal de escolha de carro foi aberta!');
            console.log('[ESCOLHER CARRO] Modal mostrada com sucesso');
        } catch (e) {
            console.error('Erro ao carregar carros:', e);
            mostrarToast('Erro ao carregar carros', 'error');
        }
    } else {
        // Para carros, compra direto
        abrirConfirmacao(id, tipo, nome, preco);
    }
}

async function selecionarCarroPeca(carroId, carroNome) {
    console.log('[SELEÇÃO CARRO] Carro selecionado:', carroId, carroNome);
    alert(`[DEBUG] Carro selecionado:\nID: ${carroId}\nNome: ${carroNome}`);

    compraPendente.carroSelecionado = carroId;
    console.log('[SELEÇÃO CARRO] compraPendente:', compraPendente);

    // Fechar modal de escolher carro
    bootstrap.Modal.getInstance(document.getElementById('escolherCarroModal')).hide();

    // Validações gerais
    if (!equipeAtual) {
        mostrarToast('Erro ao carregar equipe', 'error');
        return;
    }

    if (equipeAtual.saldo < compraPendente.preco) {
        mostrarToast('❌ Saldo insuficiente', 'error');
        return;
    }

    // SE ARMAZÉM: Compra direto sem PIX
    if (carroId === 'armazem') {
        console.log('[COMPRA ARMAZÉM] Comprando peça para o armazém');

        try {
            const respCompra = await fetch('/api/comprar-peca-armazem', {
                method: 'POST',
                headers: obterHeaders(),
                body: JSON.stringify({
                    peca_id: compraPendente.id,
                    tipo: compraPendente.tipo
                })
            });

            const resultado = await respCompra.json();

            if (resultado.sucesso) {
                mostrarToast(`✅ Peça '${compraPendente.nome}' adicionada ao armazém!`, 'success');
                // Recarregar loja de peças e saldo
                setTimeout(() => {
                    carregarPecasLoja();
                    recarregarDadosEquipe();
                }, 500);
            } else {
                mostrarToast('❌ Erro ao comprar para armazém: ' + (resultado.erro || 'Desconhecido'), 'error');
            }
        } catch (e) {
            console.error('[COMPRA ARMAZÉM] Erro:', e);
            mostrarToast('Erro ao comprar para armazém', 'error');
        }
        return;
    }

    // FLUXO NORMAL: Instalar em carro com PIX
    console.log('[SELEÇÃO CARRO] Abrindo confirmação para carro:', carroId);

    document.getElementById('modalNome').textContent = compraPendente.nome;
    document.getElementById('modalPreco').textContent = `${formatarMoeda(compraPendente.preco)}`;
    document.getElementById('modalDescricao').textContent = `Instalar em: ${carroNome}`;
    document.getElementById('modalNovoSaldo').textContent = `${formatarMoeda(equipeAtual.saldo - compraPendente.preco)}`;

    const modal = new bootstrap.Modal(document.getElementById('confirmacaoModal'));
    modal.show();
}

function abrirConfirmacao(id, tipo, nome, preco, isVariacao = false) {
    if (!equipeAtual) {
        mostrarToast('Erro ao carregar equipe', 'error');
        return;
    }

    if (equipeAtual.saldo < preco) {
        mostrarToast('❌ Saldo insuficiente', 'error');
        return;
    }

    // Se for variação, usar variacao_id em vez de item_id
    compraPendente = {
        id,
        tipo,
        nome,
        preco,
        isVariacao: isVariacao
    };

    // Compatibilidade com diferentes modais
    const textoEl = document.getElementById('modalNome') || document.getElementById('confirma-texto');
    const precoEl = document.getElementById('modalPreco') || document.getElementById('confirma-preco');
    const descricaoEl = document.getElementById('modalDescricao');
    const saldoEl = document.getElementById('modalNovoSaldo');
    const modalEl = document.getElementById('confirmacaoModal') || document.getElementById('confirmaModal');

    console.log('modalEl:', modalEl);

    if (textoEl) textoEl.textContent = nome;
    if (precoEl) precoEl.textContent = `${formatarMoeda(preco)}`;
    if (descricaoEl) descricaoEl.textContent = tipo === 'carro' ? 'Carro' : 'Peça';
    if (saldoEl) saldoEl.textContent = `${formatarMoeda(equipeAtual.saldo - preco)}`;

    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } else {
        console.error('Modal de confirmação não encontrado!');
    }
}

async function confirmarCompra() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Processando...';

    // Compatibilidade com diferentes modais
    const modalEl = document.getElementById('confirmacaoModal') || document.getElementById('confirmaModal');

    try {
        const body = {
            tipo: compraPendente.tipo
        };

        // Se for carro com variação, usar variacao_id
        if (compraPendente.tipo === 'carro' && compraPendente.isVariacao) {
            body.variacao_id = compraPendente.id;
        } else {
            body.item_id = compraPendente.id;
        }

        // Se for peça e tem carro selecionado, adicionar ao body
        if (compraPendente.tipo === 'peca' && compraPendente.carroSelecionado) {
            body.carro_id = compraPendente.carroSelecionado;
        }

        console.log('[COMPRA] Enviando requisição:');
        console.log('  Tipo:', compraPendente.tipo);
        console.log('  Variacao:', compraPendente.isVariacao);
        console.log('  Item ID:', compraPendente.id);
        console.log('  Nome:', compraPendente.nome);
        console.log('  Preco:', compraPendente.preco);
        console.log('  CarroSelecionado:', compraPendente.carroSelecionado);
        console.log('  Body FINAL:', JSON.stringify(body));

        if (!body.carro_id && compraPendente.tipo === 'peca') {
            console.warn('[COMPRA] ERRO: Peça sendo comprada sem carro_id!');
            mostrarToast('ERRO: Você deve selecionar um carro para instalar a peça', 'error');
            btn.disabled = false;
            btn.textContent = 'Confirmar Compra';
            return;
        }

        // ===== FLUXO PARA CARROS: Não gera PIX, apenas compra =====
        if (compraPendente.tipo === 'carro') {
            btn.textContent = 'Comprando carro...';

            const resp = await fetch('/api/comprar', {
                method: 'POST',
                headers: obterHeaders(),
                body: JSON.stringify(body)
            });

            const resultado = await resp.json();

            if (resultado.sucesso) {
                if (modalEl) bootstrap.Modal.getInstance(modalEl).hide();
                mostrarToast(`✅ ${resultado.mensagem}`, 'success');
                // Recarregar dados relevantes após compra
                setTimeout(() => {
                    carregarGaragem(); // Sempre recarregar garagem após compra
                    if (obterAbaAtiva() === 'carros-tab') {
                        carregarCarrosLoja(); // Só recarregar loja se estiver na aba
                    }
                }, 500);
            } else {
                mostrarToast('Erro: ' + resultado.erro, 'error');
            }
        }
        // ===== FLUXO PARA PEÇAS: Gera QR Code PIX =====
        else {
            btn.textContent = 'Gerando QR Code...';

            const respQr = await fetch('/api/gerar-qr-pix', {
                method: 'POST',
                headers: obterHeaders(),
                body: JSON.stringify({
                    tipo: body.tipo,
                    item_id: body.item_id,
                    carro_id: body.carro_id || null
                })
            });

            const resultadoQr = await respQr.json();

            if (resultadoQr.sucesso) {
                // Fechar modal de confirmação
                if (modalEl) bootstrap.Modal.getInstance(modalEl).hide();

                // Abrir modal de PIX
                mostrarModalPix(resultadoQr);
            } else {
                mostrarToast('Erro ao gerar QR Code: ' + resultadoQr.erro, 'error');
            }
        }
    } catch (e) {
        console.error('[COMPRA] Erro:', e);
        mostrarToast('Erro ao processar compra', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Confirmar Compra';
    }
}

// ============= UTILITÁRIOS =============

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

function mostrarToast(mensagem, tipo = 'success') {
    const container = document.querySelector('.toast-container') || criarToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    toast.textContent = mensagem;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

async function solicitarMudarCarro(carroId, carroNome) {
    try {
        const equipeId = obterEquipeIdDaSession();

        // Chamar /api/ativar-carro para gerar PIX de ativação
        const resp = await fetch('/api/ativar-carro', {
            method: 'POST',
            headers: { ...obterHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ carro_id: carroId })
        });

        if (!resp.ok) {
            const erro = await resp.json();
            if (erro.pecas_faltando && erro.pecas_faltando.length > 0) {
                mostrarToast(`❌ Carro incompleto. Faltam: ${erro.pecas_faltando.join(', ')}`, 'error');
            } else {
                mostrarToast(erro.erro || 'Erro ao solicitar ativação', 'error');
            }
            return;
        }

        const resultado = await resp.json();

        if (resultado.sucesso) {
            // Exibir modal de PIX para ativação
            mostrarModalPix(resultado);
        } else {
            mostrarToast(resultado.erro || 'Erro ao gerar QR Code de ativação', 'error');
        }
    } catch (e) {
        console.error('Erro:', e);
        mostrarToast('Erro ao ativar carro', 'error');
    }
}

function gerarHtmlPecas(carro) {
    /**Gera HTML das peças do carro em ordem específica, mostrando "sem [tipo]" se faltar */
    let htmlPecas = '';

    // Usar durabilidade_atual do backend (0-100 ou valor real); só usar 100 se ausente/NaN
    function durabilidadeAtual(peca) {
        const v = peca.durabilidade_atual;
        if (typeof v === 'number' && !Number.isNaN(v)) return v;
        const n = Number(v);
        if (!Number.isNaN(n)) return n;
        return 100;
    }

    // Ordem padrão das peças
    const ordemPecas = ['motor', 'cambio', 'suspensao', 'kit_angulo', 'diferencial'];
    
    // Criar mapa de peças para acesso rápido (por tipo; normalizar tipo para minúscula para lookup)
    const mapaPecas = {};
    if (carro.pecas && Array.isArray(carro.pecas)) {
        carro.pecas.forEach(peca => {
            const tipo = (peca.tipo || '').toLowerCase();
            if (tipo === 'diferencial') {
                if (!mapaPecas['diferencial']) mapaPecas['diferencial'] = [];
                mapaPecas['diferencial'].push(peca);
            } else {
                mapaPecas[tipo] = peca;
            }
        });
    }

    // Renderizar na ordem especificada
    ordemPecas.forEach(tipo => {
        const nomeDisplay = {
            'motor': 'Motor',
            'cambio': 'Câmbio',
            'suspensao': 'Suspensão',
            'kit_angulo': 'Kit Ângulo',
            'diferencial': 'Diferencial'
        }[tipo];

        if (tipo === 'diferencial') {
            // Tratamento especial para diferenciais (pode haver múltiplos)
            const diferenciais = mapaPecas['diferencial'] || [];
            
            if (diferenciais.length > 0) {
                // Renderizar cada diferencial
                diferenciais.forEach((peca, idx) => {
                    const durabilidade = durabilidadeAtual(peca);
                    const durabilidadeMax = Number(peca.durabilidade_maxima) || 100;
                    const percentual = durabilidadeMax > 0 ? (durabilidade / durabilidadeMax * 100) : 0;
                    const corDesgaste = percentual > 75 ? 'success' : percentual > 50 ? 'warning' : percentual > 25 ? 'danger' : 'danger';
                    const somaUpgrades = (peca.upgrades && Array.isArray(peca.upgrades)) ? peca.upgrades.reduce((s, u) => s + (Number(u.preco) || 0), 0) : 0;
                    const custoRetifica = ((Number(peca.preco_loja) || 0) + somaUpgrades) / 2;
                    const btnRetifica = percentual < 100 ? `<button class="btn btn-sm btn-outline-success me-2" onclick="recuperarPecaVida('${peca.id}', ${custoRetifica})" title="Fazer retífica: 100% (${custoRetifica.toFixed(2)} doricoins)">🔧 Fazer retífica</button>` : '';
                    const upgradesDiferencial = (peca.upgrades && Array.isArray(peca.upgrades) && peca.upgrades.length) ? ' + ' + peca.upgrades.map(u => u.nome).join(', ') : '';
                    htmlPecas += `
                        <div class="peca-item mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <div class="flex-grow-1">
                                    <strong>${peca.nome}${upgradesDiferencial}</strong>
                                </div>
                                <div>
                                    ${btnRetifica}<span class="badge bg-${corDesgaste} me-2">${percentual.toFixed(1)}%</span>
                                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="abrirModalRemoverPeca('${carro.id}', '${peca.tipo}', '${peca.nome}')">✕</button>
                                </div>
                            </div>
                            <div class="progress" style="height: 10px;">
                                <div class="progress-bar bg-${corDesgaste}" style="width: ${percentual}%"></div>
                            </div>
                            <small class="text-muted">Tipo: ${peca.tipo}</small>
                        </div>
                    `;
                });
            } else {
                // Mostrar como faltando
                htmlPecas += `
                    <div class="peca-item mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong>⚠️ Sem ${nomeDisplay}</strong>
                            <span class="badge bg-danger">0.0%</span>
                        </div>
                        <div class="progress" style="height: 10px;">
                            <div class="progress-bar bg-danger" style="width: 0%"></div>
                        </div>
                        <small class="text-muted">Tipo: ${tipo}</small>
                    </div>
                `;
            }
        } else {
            // Tipos únicos
            const peca = mapaPecas[tipo];
            
            if (peca) {
                // Peça instalada (usa durabilidade_atual do backend; 0 é válido)
                const durabilidade = durabilidadeAtual(peca);
                const durabilidadeMax = Number(peca.durabilidade_maxima) || 100;
                const percentual = durabilidadeMax > 0 ? (durabilidade / durabilidadeMax * 100) : 0;
                const corDesgaste = percentual > 75 ? 'success' : percentual > 50 ? 'warning' : percentual > 25 ? 'danger' : 'danger';
                const somaUpgrades = (peca.upgrades && Array.isArray(peca.upgrades)) ? peca.upgrades.reduce((s, u) => s + (Number(u.preco) || 0), 0) : 0;
                const custoRetifica = ((Number(peca.preco_loja) || 0) + somaUpgrades) / 2;
                const btnRetifica = percentual < 100 ? `<button class="btn btn-sm btn-outline-success me-2" onclick="recuperarPecaVida('${peca.id}', ${custoRetifica})" title="Fazer retífica: 100% (${custoRetifica.toFixed(2)} doricoins)">🔧 Fazer retífica</button>` : '';
                const upgradesTxt = (peca.upgrades && Array.isArray(peca.upgrades) && peca.upgrades.length) ? ' + ' + peca.upgrades.map(u => u.nome).join(', ') : '';
                htmlPecas += `
                    <div class="peca-item mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div class="flex-grow-1">
                                <strong>${peca.nome}${upgradesTxt}</strong>
                            </div>
                            <div>
                                ${btnRetifica}<span class="badge bg-${corDesgaste} me-2">${percentual.toFixed(1)}%</span>
                                <button class="btn btn-sm btn-outline-danger ms-1" onclick="abrirModalRemoverPeca('${carro.id}', '${peca.tipo}', '${peca.nome}')">✕</button>
                            </div>
                        </div>
                        <div class="progress" style="height: 10px;">
                            <div class="progress-bar bg-${corDesgaste}" style="width: ${percentual}%"></div>
                        </div>
                        <small class="text-muted">Tipo: ${peca.tipo}</small>
                    </div>
                `;
            } else {
                // Peça faltando
                htmlPecas += `
                    <div class="peca-item mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <strong>⚠️ Sem ${nomeDisplay}</strong>
                            <span class="badge bg-danger">0.0%</span>
                        </div>
                        <div class="progress" style="height: 10px;">
                            <div class="progress-bar bg-danger" style="width: 0%"></div>
                        </div>
                        <small class="text-muted">Tipo: ${tipo}</small>
                    </div>
                `;
            }
        }
    });

    return htmlPecas || '<p class="text-muted">Nenhuma peça especial instalada</p>';
}

function verificarPecasCompletas(carro) {
    /**Verifica se o carro tem todas as peças necessárias (usando array pecas) */
    if (!carro || !carro.pecas || !Array.isArray(carro.pecas)) return false;

    const tipos_necessarios = ['motor', 'cambio', 'suspensao', 'diferencial', 'kit_angulo'];
    const tipos_instalados = carro.pecas
        .filter(p => p && p.tipo)  // Filtrar peças válidas
        .map(p => p.tipo);

    // Verificar se todos os tipos necessários estão no array
    // Para diferencial, apenas precisa ter PELO MENOS um (pode ter vários)
    return tipos_necessarios.every(tipo => {
        if (tipo === 'diferencial') {
            // Diferencial pode ter múltiplos, então verificar se há pelo menos um
            return tipos_instalados.includes(tipo);
        }
        // Outros tipos devem aparecer exatamente uma vez
        return tipos_instalados.includes(tipo);
    });
}

function criarToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// CSS para animação do toast
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to { opacity: 0; transform: translateX(100%); }
    }
    
    .transferencia-enviado {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    
    .transferencia-recebido {
        background-color: #f5f5f5;
        border-left: 4px solid #dc143c;
    }
`;
document.head.appendChild(style);

// ============= TRANSFERÊNCIAS DE DINHEIRO =============

async function carregarEquipesParaTransferencia() {
    try {
        // Tentar obter do localStorage primeiro
        let equipeAtualId = obterEquipeIdDaSession();
        console.log('[TRANSFERÊNCIA] 1. Equipe ID do localStorage:', equipeAtualId);

        // Se não tiver no localStorage, carregar dados da equipe para obter o ID
        if (!equipeAtualId && equipeAtual) {
            equipeAtualId = equipeAtual.id;
            console.log('[TRANSFERÊNCIA] 1b. Equipe ID da variável global:', equipeAtualId);
        }

        const resp = await fetch('/api/equipes', {
            headers: obterHeaders()
        });

        if (!resp.ok) {
            console.log('[TRANSFERÊNCIA] Erro ao carregar equipes');
            return;
        }

        const equipes = await resp.json();
        console.log('[TRANSFERÊNCIA] 2. Equipes do servidor:', equipes.map(e => ({ id: e.id, nome: e.nome })));
        console.log('[TRANSFERÊNCIA] 2b. Filtrando com ID da equipe atual:', equipeAtualId);

        const select = document.getElementById('equipeDestino');
        select.innerHTML = '<option value="">Selecione uma equipe...</option>';

        let equipesFiltradas = 0;
        equipes.forEach(equipe => {
            const equipeIdString = String(equipe.id).trim().toLowerCase();
            const equipeAtualIdString = String(equipeAtualId).trim().toLowerCase();
            const ehMesmEquipe = equipeIdString === equipeAtualIdString;

            console.log(`[TRANSFERÊNCIA] 3. Comparando: "${equipeIdString}" vs "${equipeAtualIdString}" → mesma=${ehMesmEquipe} (${equipe.nome})`);

            // Não mostrar a própria equipe
            if (!ehMesmEquipe) {
                const option = document.createElement('option');
                option.value = equipe.id;
                option.textContent = `${equipe.nome}`;
                select.appendChild(option);
                equipesFiltradas++;
            }
        });

        console.log('[TRANSFERÊNCIA] 4. Total de equipes para enviar:', equipesFiltradas);
    } catch (e) {
        console.error('[TRANSFERÊNCIA] Erro ao carregar equipes:', e);
    }
}

async function atualizarPreviewTransferencia() {
    const valor = parseFloat(document.getElementById('valorTransferencia').value) || 0;
    let taxa = 10;
    try {
        const r = await fetch('/api/taxa-transferencia', { headers: obterHeaders() });
        const d = await r.json();
        if (d.taxa != null) taxa = parseFloat(d.taxa);
    } catch (e) {}

    if (valor <= 0) {
        document.getElementById('previewTransferencia').style.display = 'none';
        return;
    }

    const taxaValor = valor * (taxa / 100);
    const recebe = valor - taxaValor;

    document.getElementById('previewEnvio').textContent = formatarMoeda(valor);
    document.getElementById('previewTaxa').textContent = formatarMoeda(taxaValor);
    document.getElementById('previewRecebe').textContent = formatarMoeda(recebe);
    const taxaPreviewLabel = document.getElementById('previewTaxaLabel');
    if (taxaPreviewLabel) taxaPreviewLabel.textContent = 'Taxa (' + taxa + '%):';

    document.getElementById('previewTransferencia').style.display = 'block';
}

async function executarTransferencia() {
    const equipeDestino = document.getElementById('equipeDestino').value;
    const valor = parseFloat(document.getElementById('valorTransferencia').value) || 0;
    let taxa = 10;
    try {
        const r = await fetch('/api/taxa-transferencia', { headers: obterHeaders() });
        const d = await r.json();
        if (d.taxa != null) taxa = parseFloat(d.taxa);
    } catch (e) {}

    if (!equipeDestino) {
        mostrarToast('Selecione uma equipe destino', 'error');
        return;
    }

    if (valor <= 0) {
        mostrarToast('Digite um valor válido', 'error');
        return;
    }

    try {
        const resp = await fetch('/api/transferencia', {
            method: 'POST',
            headers: { ...obterHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({
                equipe_id_destino: equipeDestino,
                valor: valor
            })
        });

        const resultado = await resp.json();

        if (!resp.ok) {
            mostrarToast(resultado.erro || 'Erro na transferência', 'error');
            return;
        }

        mostrarToast('✅ Transferência realizada com sucesso!', 'success');

        // Limpar formulário
        document.getElementById('valorTransferencia').value = '';
        document.getElementById('equipeDestino').value = '';
        document.getElementById('previewTransferencia').style.display = 'none';

        // Recarregar dados
        recarregarDadosEquipe();
        carregarHistoricoTransferencias();
    } catch (e) {
        console.error('Erro:', e);
        mostrarToast('Erro ao processar transferência', 'error');
    }
}

async function carregarHistoricoTransferencias() {
    try {
        const resp = await fetch('/api/transferencias/historico', {
            headers: obterHeaders()
        });

        if (!resp.ok) return;

        const transferencias = await resp.json();
        const container = document.getElementById('historicoTransferencias');

        if (!transferencias || transferencias.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhuma transferência realizada</p>';
            return;
        }

        container.innerHTML = '';

        transferencias.forEach(transf => {
            const isEnviado = transf.tipo === 'enviado';
            const classeCor = isEnviado ? 'transferencia-enviado' : 'transferencia-recebido';
            const icone = isEnviado ? '📤' : '📥';
            const corTexto = isEnviado ? 'text-danger' : 'text-success';
            const simbolo = isEnviado ? '-' : '+';

            const div = document.createElement('div');
            div.className = `p-3 mb-2 rounded ${classeCor}`;
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small class="text-muted d-block">${new Date(transf.timestamp).toLocaleDateString('pt-BR')} às ${new Date(transf.timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</small>
                        <strong>${icone} ${transf.outra_equipe}</strong><br>
                        <small class="text-muted">Taxa: ${transf.taxa_percentual}%</small>
                    </div>
                    <div class="text-right">
                        <div class="h6 ${corTexto} mb-0">
                            ${simbolo} ${formatarMoeda(transf.valor)}
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (e) {
        console.error('Erro ao carregar histórico:', e);
    }
}

// ========== INSTALAR PEÇAS DO ARMAZÉM ==========
let pecaSelecionadaArmazem = null;

function abrirModalInstalarPecaArmazem(pecaNome, pecaTipo, idx, preco) {
    // Validar se garagem foi carregada
    if (!window.garagemAtual || !window.garagemAtual.carros) {
        mostrarToast('⏳ Aguarde o carregamento da garagem...', 'info');
        return;
    }

    pecaSelecionadaArmazem = { nome: pecaNome, tipo: pecaTipo, idx: idx, preco: preco };

    const modal = new bootstrap.Modal(document.getElementById('modalInstalarArmazem'));
    document.getElementById('pecaNomeModal').textContent = pecaNome;
    document.getElementById('pecaTipoModal').textContent = pecaTipo;

    // Popular lista de carros com botões
    const listaCarros = document.getElementById('listaCarrosInstalarModal');
    listaCarros.innerHTML = '';

    // Buscar carros da garagem
    const carrosDisponiveis = window.garagemAtual.carros || [];

    if (carrosDisponiveis.length > 0) {
        carrosDisponiveis.forEach(carro => {
            const botao = document.createElement('button');
            botao.type = 'button';
            botao.className = 'btn btn-outline-primary w-100 mb-2 text-start';
            botao.innerHTML = `
                <strong>${carro.marca} ${carro.modelo}</strong><br>
                <small class="text-muted">#${carro.numero_carro}</small>
            `;
            botao.onclick = () => {
                instalarPecaDoArmazem(carro.id);
            };
            listaCarros.appendChild(botao);
        });
    } else {
        listaCarros.innerHTML = '<p class="text-muted text-center">Nenhum carro disponível</p>';
    }

    // Pausar auto-refresh enquanto modal está aberto
    const modalElement = document.getElementById('modalInstalarArmazem');

    // Listener para quando modal abre
    modalElement.addEventListener('show.bs.modal', () => {
        console.log('[MODAL INSTALAR] Modal aberto, pausando auto-refresh');
        if (intervaloAutoRefresh) clearInterval(intervaloAutoRefresh);
        if (intervaloSolicitacoes) clearInterval(intervaloSolicitacoes);
    });

    // Listener para quando modal fecha
    modalElement.addEventListener('hidden.bs.modal', () => {
        console.log('[MODAL INSTALAR] Modal fechado, retomando auto-refresh');
        iniciarAutoRefresh();
    });

    modal.show();
}

async function instalarPecaDoArmazem(carroId) {
    try {
        if (!pecaSelecionadaArmazem) {
            mostrarToast('Erro: peça não selecionada', 'error');
            return;
        }

        // Mostrar mensagem de carregamento
        mostrarToast('⏳ Gerando QRCode...', 'info');

        // STEP 1: Criar solicitação de instalação (SEM instalar ainda)
        console.log('[INSTALAR ARMAZÉM] Criando solicitação de instalação...');

        const respSolicitacao = await fetch('/api/garagem/solicitar-instalacao-armazem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                peca_nome: pecaSelecionadaArmazem.nome,
                peca_tipo: pecaSelecionadaArmazem.tipo,
                carro_id: carroId
            })
        });

        const resultadoSolicitacao = await respSolicitacao.json();

        if (!resultadoSolicitacao.sucesso) {
            mostrarToast('Erro: ' + (resultadoSolicitacao.erro || 'Desconhecido'), 'error');
            return;
        }

        // STEP 2: Gerar QRCode PIX para a instalação
        const { transacao_id, qr_code_url, valor_item, valor_taxa, valor_total, peca_loja_id } = resultadoSolicitacao;

        if (!qr_code_url) {
            mostrarToast('Erro: não conseguiu gerar QRCode', 'error');
            return;
        }

        // STEP 3: Armazenar dados ANTES de mostrar modal (importante para polling)
        window.compraPendentePix = {
            transacao_id: transacao_id,
            tipo: 'instalacao_armazem',
            item_id: peca_loja_id,  // ID da peça_loja para instalar
            carro_id: carroId  // Carro ID
        };

        console.log('[INSTALAR ARMAZÉM] Dados para processamento armazenados:', window.compraPendentePix);

        // STEP 4: Mostrar modal de pagamento PIX
        const dadosPix = {
            transacao_id: transacao_id,
            qr_code_url: qr_code_url,
            item_nome: pecaSelecionadaArmazem.nome,
            item_id: carroId,
            tipo_item: 'instalacao_armazem',
            valor_item: valor_item,
            taxa: valor_taxa,
            valor_total: valor_total
        };

        console.log('[INSTALAR ARMAZÉM] Abrindo modal de pagamento PIX');
        mostrarModalPix(dadosPix);

        // Fechar modal de instalação
        bootstrap.Modal.getInstance(document.getElementById('modalInstalarArmazem')).hide();

    } catch (e) {
        console.error('Erro ao instalar peça:', e);
        mostrarToast('Erro ao instalar peça: ' + e.message, 'error');
    }
}
// ============= FUNÇÕES PIX / MERCADO PAGO =============

// Rastreador de pollings ativos
const pixPollings = {};

function mostrarModalPix(dadosPix) {
    // Parar polling anterior se houver
    if (window.transacaoPixAtual && pixPollings[window.transacaoPixAtual]) {
        clearInterval(pixPollings[window.transacaoPixAtual]);
        delete pixPollings[window.transacaoPixAtual];
        console.log(`[PIX] Polling anterior parado: ${window.transacaoPixAtual}`);
    }

    // Preencher dados no modal
    document.getElementById('pixItemNome').textContent = dadosPix.item_nome;
    document.getElementById('pixValorItem').textContent = dadosPix.valor_item.toFixed(2);
    document.getElementById('pixValorTotal').textContent = dadosPix.valor_total.toFixed(2);
    document.getElementById('pixTaxaValor').textContent = dadosPix.taxa.toFixed(2);

    // Mostrar QR Code
    if (dadosPix.qr_code_url) {
        const qrImg = document.getElementById('pixQrCode');
        qrImg.src = dadosPix.qr_code_url;
        qrImg.onerror = () => {
            console.error('Erro ao carregar QR Code');
            document.getElementById('pixStatus').innerHTML = '<div class="alert alert-danger">❌ Erro ao carregar QR Code. Tente novamente.</div>';
        };
        document.getElementById('pixQrCodeContainer').style.display = 'block';
    }

    // Armazenar ID da transação e dados da compra para polling
    window.transacaoPixAtual = dadosPix.transacao_id;
    window.transacaoPixAtualDividido = dadosPix.transacao_id;  // Para compatibilidade com confirmarPagamentoManual()

    // Só armazenar dados de compra se não estiver já armazenado
    // (pode ter sido definido em instalarPecaDoArmazem ou outros contextos)
    if (!window.compraPendentePix || !window.compraPendentePix.tipo) {
        window.compraPendentePix = {
            transacao_id: dadosPix.transacao_id,
            tipo: dadosPix.tipo_item,
            item_id: dadosPix.item_id,
            carro_id: dadosPix.carro_id || null
        };
    }

    console.log('[PIX] Dados da compra armazenados:', window.compraPendentePix);

    // Resetar status
    document.getElementById('pixStatus').innerHTML = '<div class="alert alert-info">⏳ Aguardando confirmação...</div>';

    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('pixModal'));
    modal.show();

    // Começar a monitorar o status
    monitorarTransacaoPix(dadosPix.transacao_id);
}

async function monitorarTransacaoPix(transacaoId) {
    // Parar polling anterior para este ID se houver
    if (pixPollings[transacaoId]) {
        clearInterval(pixPollings[transacaoId]);
        console.log(`[PIX] Polling anterior parado: ${transacaoId}`);
    }

    let tentativas = 0;
    const maxTentativas = 120; // 2 minutos (120 segundos)

    const intervalo = setInterval(async () => {
        tentativas++;

        if (tentativas > maxTentativas) {
            clearInterval(intervalo);
            delete pixPollings[transacaoId];
            document.getElementById('pixStatus').innerHTML = '<div class="alert alert-danger">⏱️ Tempo limite expirado. Feche e tente novamente.</div>';
            return;
        }

        try {
            const resp = await fetch(`/api/transacao-pix/${transacaoId}`, {
                headers: obterHeaders()
            });

            // Se transação não foi encontrada (foi cancelada/deletada)
            if (!resp.ok) {
                console.log(`[PIX POLLING] Transação não encontrada ou cancelada (${resp.status})`);
                clearInterval(intervalo);
                delete pixPollings[transacaoId];
                return;
            }

            const transacao = await resp.json();
            console.log(`[PIX POLLING] Tentativa ${tentativas}: Status = ${transacao.status}`);

            // Verificar se ainda é a transação ativa (pode ter sido substituída)
            if (window.transacaoPixAtual !== transacaoId) {
                clearInterval(intervalo);
                delete pixPollings[transacaoId];
                console.log(`[PIX] Polling parado (transação substituída): ${transacaoId}`);
                return;
            }

            if (transacao.status === 'aprovado') {
                console.log(`[PIX] Pagamento aprovado! Processando compra...`);
                clearInterval(intervalo);
                delete pixPollings[transacaoId];
                document.getElementById('pixStatus').innerHTML = '<div class="alert alert-success">✅ Pagamento confirmado! Processando sua compra...</div>';

                // Processar a compra (criar solicitação de instalação para peças, adicionar carro, etc)
                await processarCompraAposPagamento(window.compraPendentePix);

                // Aguardar um pouco e fechar modal
                setTimeout(() => {
                    bootstrap.Modal.getInstance(document.getElementById('pixModal')).hide();
                    mostrarToast('✅ Compra realizada com sucesso!', 'success');

                    // Recarregar dados
                    carregarDetalhesEquipe();
                    carregarGaragem();
                    carregarHistorico();
                }, 2000);
            } else if (transacao.status === 'pendente') {
                // Ainda aguardando
                const segundosRestantes = (maxTentativas - tentativas);
                document.getElementById('pixStatus').innerHTML = `<div class="alert alert-info">⏳ Aguardando confirmação... (${segundosRestantes}s)</div>`;
            } else if (transacao.status === 'recusado' || transacao.status === 'cancelado') {
                clearInterval(intervalo);
                delete pixPollings[transacaoId];
                document.getElementById('pixStatus').innerHTML = '<div class="alert alert-warning">❌ Pagamento não realizado. Tente novamente.</div>';
            }
        } catch (e) {
            console.error('Erro ao monitorar transação:', e);
        }
    }, 1000); // Verificar a cada 1 segundo

    // Armazenar referência do intervalo
    pixPollings[transacaoId] = intervalo;
    console.log(`[PIX] Polling iniciado: ${transacaoId}`);
}

async function processarCompraAposPagamento(dadosCompra) {
    // Processa a compra (cria solicitação, adiciona carro, etc) após pagamento confirmado
    try {
        if (!dadosCompra || !dadosCompra.transacao_id) {
            console.log('[COMPRA] Sem dados de compra para processar');
            return;
        }

        const tipo = dadosCompra.tipo;
        const transacao_id = dadosCompra.transacao_id;

        console.log(`[COMPRA PIX] Processando compra: tipo=${tipo}, transacao_id=${transacao_id}`);
        console.log(`[COMPRA PIX] Dados completos:`, dadosCompra);

        // Chamar endpoint de confirmação de pagamento (processa baseado no tipo_item armazenado no BD)
        const respCompra = await fetch('/api/confirmar-pagamento-manual', {
            method: 'POST',
            headers: obterHeaders(),
            body: JSON.stringify({
                transacao_id: transacao_id
            })
        });

        const resultado = await respCompra.json();
        console.log(`[COMPRA PIX] Resposta do servidor:`, resultado);

        if (resultado.sucesso) {
            console.log('[COMPRA PIX] Compra processada com sucesso');
            
            // Limpar carrinho de armazém se foi compra de múltiplas peças do armazém
            if (tipo === 'multiplas_pecas_armazem' || tipo === 'multiplas_pecas_armazem_ativo' || tipo === 'multiplas_pecas_armazem_ativo_modal') {
                console.log('[COMPRA PIX] Limpando carrinho do armazém...');
                limparCarrinhoArmazem(true);  // silencioso = true
                // Recarregar garagem para atualizar lista de peças
                setTimeout(() => carregarGaragem(), 1000);
            }
        } else {
            console.error('[COMPRA PIX] Erro ao processar:', resultado.erro);
            mostrarToast('Erro ao processar compra: ' + resultado.erro, 'error');
        }
    } catch (e) {
        console.error('[COMPRA PIX] Erro:', e);
        mostrarToast('Erro ao processar compra', 'error');
    }
}

async function confirmarPagamentoManual() {
    // Confirma o pagamento manualmente (para testes)
    // Suporta tanto sistema antigo (transacaoPixAtual) quanto novo (transacaoPixAtualDividido)
    const transacaoId = window.transacaoPixAtualDividido || window.transacaoPixAtual;

    if (!transacaoId) {
        mostrarToast('Nenhuma transação ativa', 'error');
        return;
    }

    console.log('[PAGAMENTO MANUAL] Confirmando transação:', transacaoId);

    try {
        const resp = await fetch('/api/confirmar-pagamento-manual', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                transacao_id: transacaoId
            })
        });

        console.log('[PAGAMENTO MANUAL] Status resposta:', resp.status);
        const resultado = await resp.json();
        console.log('[PAGAMENTO MANUAL] Resposta:', resultado);

        if (!resp.ok || !resultado.sucesso) {
            mostrarToast('Erro: ' + (resultado.erro || 'Erro desconhecido'), 'error');
            return;
        }

        document.getElementById('pixStatus').innerHTML = '<div class="alert alert-success">✅ Pagamento confirmado! Processando sua compra...</div>';

        // Guardar saldo anterior
        const saldoAnterior = equipeAtual?.saldo || 0;
        let valorGastoTotal = 0;
        carrinho.forEach(peca => {
            valorGastoTotal += (peca.preco * (peca.quantidade || 1));
        });

        // Parar polling
        if (window.pixPollings && window.pixPollings[transacaoId]) {
            clearInterval(window.pixPollings[transacaoId]);
            delete window.pixPollings[transacaoId];
        }

        // Aguardar um pouco e fechar modal
        setTimeout(() => {
            try {
                const modal = bootstrap.Modal.getInstance(document.getElementById('pixModal'));
                if (modal) {
                    modal.hide();
                }
            } catch (e) {
                console.error('[PAGAMENTO MANUAL] Erro ao fechar modal:', e);
            }

            mostrarToast('✅ Compra realizada com sucesso!', 'success');

            // Fechar painel flutuante
            document.getElementById('carrinhoPanel').style.display = 'none';
            document.getElementById('carrinhoFlutuante').style.display = 'none';

            limparCarrinho();
            atualizarPainelCarrinho();

            // Recarregar dados
            if (typeof carregarDetalhesEquipe === 'function') carregarDetalhesEquipe();
            if (typeof carregarGaragem === 'function') carregarGaragem();
            if (typeof carregarHistorico === 'function') carregarHistorico();

            // Mostrar modal de compra finalizada
            setTimeout(() => {
                mostrarModalCompraFinalizada(saldoAnterior, valorGastoTotal);
            }, 500);
        }, 1500);
    } catch (e) {
        console.error('[PAGAMENTO MANUAL] Erro:', e);
        mostrarToast('Erro ao confirmar pagamento: ' + e.message, 'error');
    }
}

// ============= SISTEMA DE CARRINHO DO ARMAZÉM =============

function mudarQtdArmazem(pecaNome, pecaTipo, operacao) {
    /**Aumenta ou diminui a quantidade de peça no carrinho do armazém*/
    const pecaExistente = carrinhoArmazem.find(p => p.nome === pecaNome && p.tipo === pecaTipo);
    
    if (operacao === 'mais') {
        if (pecaExistente) {
            pecaExistente.quantidade += 1;
        } else {
            // Encontrar a peça no armazém para pegar os dados
            const pecaArmazem = window.garagemAtual && window.garagemAtual.armazem ? 
                window.garagemAtual.armazem.pecas_guardadas.find(p => p.nome === pecaNome && p.tipo === pecaTipo) : null;
            
            if (pecaArmazem) {
                // Definir destino padrão se não houver nenhum
                if (!destinoCarrinhoArmazem) {
                    destinoCarrinhoArmazem = 'ativo';
                    document.getElementById('destino_ativo').checked = true;
                }
                
                carrinhoArmazem.push({
                    nome: pecaNome,
                    tipo: pecaTipo,
                    id: pecaArmazem.id,
                    preco: pecaArmazem.preco,
                    pix_id: pecaArmazem.pix_id,
                    quantidade: 1
                });
            }
        }
    } else if (operacao === 'menos') {
        if (pecaExistente) {
            pecaExistente.quantidade -= 1;
            if (pecaExistente.quantidade <= 0) {
                carrinhoArmazem = carrinhoArmazem.filter(p => !(p.nome === pecaNome && p.tipo === pecaTipo));
            }
        }
    }
    
    atualizarUICarrinhoArmazem();
}

function mudarDestinoArmazem(destino) {
    /**Muda o destino das peças (ativo ou repouso)*/
    destinoCarrinhoArmazem = destino;
    console.log(`[ARMAZÉM] Destino mudado para: ${destino}`);
    atualizarUICarrinhoArmazem();
}

function atualizarUICarrinhoArmazem() {
    /**Atualiza a interface do carrinho do armazém baseado no destino*/
    const painel = document.getElementById('carrinhoArmazemPanel');
    const conteudo = document.getElementById('carrinhoArmazemConteudo');
    const totalPecas = document.getElementById('totalPecasArmazem');
    const totalValor = document.getElementById('totalValorArmazem');
    const avisoDestino = document.getElementById('avisoDestino');
    
    if (!painel) return;
    
    // Mostrar/ocultar painel
    painel.style.display = carrinhoArmazem.length > 0 ? 'block' : 'none';
    
    if (carrinhoArmazem.length === 0) {
        if (conteudo) conteudo.innerHTML = '';
        return;
    }
    
    // Atualizar aviso de destino
    if (avisoDestino) {
        if (destinoCarrinhoArmazem === 'ativo') {
            avisoDestino.innerHTML = '💡 Peças SEM pix_id serão cobradas. Peças COM pix_id (já pagas) não serão cobradas novamente.';
        } else {
            avisoDestino.innerHTML = '💡 Carros em repouso não cobram PIX. As peças serão apenas guardadas.';
        }
    }
    
    // Calcular totais baseado no destino
    let totalQtd = 0;
    let totalValorCalc = 0;
    
    let htmlItens = '<div class="list-group list-group-flush">';
    carrinhoArmazem.forEach((peca, idx) => {
        totalQtd += peca.quantidade;
        
        // Calcular valor baseado no destino
        if (destinoCarrinhoArmazem === 'ativo') {
            // Carro ativo: cobrar apenas peças SEM pix_id
            if (!peca.pix_id) {
                totalValorCalc += peca.preco * peca.quantidade;
            }
        }
        // Se destino é repouso, não cobra nada
        
        const contemPagamento = peca.pix_id ? '✓ Pago' : '';
        const statusValor = !peca.pix_id ? `${formatarMoeda(peca.preco)} × ${peca.quantidade}` : 'Sem cobrança';
        
        htmlItens += `
            <div class="list-group-item py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="flex-grow-1">
                        <strong>${peca.nome}</strong>
                        <small class="d-block text-muted">${peca.tipo}</small>
                        ${contemPagamento ? `<small class="badge bg-success">${contemPagamento}</small>` : ''}
                    </div>
                    <div class="text-right">
                        <div>
                            <strong>${statusValor}</strong>
                            <small class="d-block text-muted">Qtd: ${peca.quantidade}</small>
                        </div>
                        <button class="btn btn-sm btn-outline-danger mt-1" onclick="removerDoCarrinhoArmazem(${idx})">
                            ✕
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    htmlItens += '</div>';
    
    if (conteudo) conteudo.innerHTML = htmlItens;
    if (totalPecas) totalPecas.textContent = totalQtd;
    if (totalValor) totalValor.textContent = formatarMoeda(totalValorCalc);
}

function removerDoCarrinhoArmazem(indice) {
    /**Remove uma peça do carrinho do armazém por índice*/
    carrinhoArmazem.splice(indice, 1);
    atualizarUICarrinhoArmazem();
}

function limparCarrinhoArmazem(silencioso = false) {
    /**Limpa todo o carrinho do armazém*/
    carrinhoArmazem = [];
    destinoCarrinhoArmazem = null;
    atualizarUICarrinhoArmazem();
    if (!silencioso) {
        mostrarToast('Carrinho do armazém limpo', 'success');
    }
}

async function processarCarrinhoArmazem() {
    /**Processa o carrinho do armazém baseado no destino selecionado*/
    try {
        if (carrinhoArmazem.length === 0) {
            mostrarToast('Nenhuma peça no carrinho', 'warning');
            return;
        }
        
        if (!destinoCarrinhoArmazem) {
            mostrarToast('Selecione um destino (Carro Ativo ou Carros em Repouso)', 'warning');
            return;
        }
        
        if (destinoCarrinhoArmazem === 'ativo') {
            await processarCarrinhoArmazemAtivo();
        } else {
            await processarCarrinhoArmazemRepouso();
        }
    } catch (e) {
        console.error('Erro ao processar carrinho:', e);
        mostrarToast('Erro ao processar carrinho: ' + e.message, 'error');
    }
}

async function processarCarrinhoArmazemAtivo() {
    /**Processa o carrinho para carro ativo - gera PIX para peças sem pix_id*/
    try {
        // Validar se equipe tem carro ativo
        if (!equipeAtual || !equipeAtual.carro_ativo) {
            mostrarToast('⚠️ Você não tem um carro ativo selecionado', 'warning');
            return;
        }
        
        const carroAtivoId = equipeAtual.carro_ativo.id;
        
        // Filtrar peças que precisam de pagamento (sem pix_id)
        const pecasParaPagar = carrinhoArmazem.filter(p => !p.pix_id);
        
        if (pecasParaPagar.length === 0) {
            mostrarToast('ℹ️ Todas as peças já foram pagas. Criando solicitações...');
            // Mesmo sem PIX, criar as solicitações
            await criarSolicitacoesInstalacaoArmazem(carroAtivoId, carrinhoArmazem, true);
            return;
        }
        
        mostrarToast('⏳ Gerando PIX...', 'info');
        
        // Chamar backend para criar transação PIX
        const respPix = await fetch('/api/instalar-multiplas-pecas-no-carro-ativo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                carro_id: carroAtivoId,
                pecas: pecasParaPagar.map(p => ({
                    nome: p.nome,
                    tipo: p.tipo,
                    quantidade: p.quantidade,
                    pix_id: p.pix_id
                }))
            })
        });
        
        const resultado = await respPix.json();
        
        if (!resultado.sucesso) {
            mostrarToast('Erro: ' + (resultado.erro || 'Erro desconhecido'), 'error');
            return;
        }
        
        // Armazenar dados para polling
        window.compraPendentePix = {
            transacao_id: resultado.transacao_id,
            tipo: 'multiplas_pecas_armazem_ativo',
            carro_id: carroAtivoId,
            pecas: carrinhoArmazem
        };
        
        // Mostrar modal de PIX
        const dadosPix = {
            transacao_id: resultado.transacao_id,
            qr_code_url: resultado.qr_code_url,
            item_nome: `${pecasParaPagar.length} peça(s) do armazém`,
            item_id: carroAtivoId,
            tipo_item: 'multiplas_pecas_armazem_ativo',
            valor_item: resultado.valor_item,
            taxa: resultado.valor_taxa,
            valor_total: resultado.valor_total
        };
        
        mostrarModalPix(dadosPix);
        
    } catch (e) {
        console.error('Erro ao processar carro ativo:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

async function processarCarrinhoArmazemRepouso() {
    /**Processa o carrinho para carros em repouso - sem PIX, apenas guarda*/
    try {
        const carrosGaragem = Array.isArray(window.garagemAtual?.carros) ? window.garagemAtual.carros : [];
        if (!window.garagemAtual || carrosGaragem.length === 0) {
            mostrarToast('⏳ Aguarde o carregamento da garagem...', 'info');
            return;
        }
        
        // Filtrar carros em repouso (carro_ativo = false ou não existe)
        const carrosEmRepouso = carrosGaragem.filter(c => !c.carro_ativo);
        
        if (carrosEmRepouso.length === 0) {
            mostrarToast('Nenhum carro em repouso disponível', 'warning');
            return;
        }
        
        // Criar modal para selecionar carro
        let modal = document.getElementById('modalSelecionarCarroRepouso');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modalSelecionarCarroRepouso';
            modal.className = 'modal fade';
            modal.tabIndex = -1;
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-dark text-white">
                            <h5 class="modal-title">😴 Selecionar Carro em Repouso</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="mb-3">Selecione o carro em repouso para guardar as peças:</p>
                            <div id="listaCarrosRepouso"></div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Popular lista de carros
        const listaCarros = modal.querySelector('#listaCarrosRepouso');
        listaCarros.innerHTML = '';
        
        carrosEmRepouso.forEach(carro => {
            const botao = document.createElement('button');
            botao.type = 'button';
            botao.className = 'btn btn-outline-info w-100 mb-2 text-start';
            botao.innerHTML = `
                <strong>${carro.marca} ${carro.modelo}</strong><br>
                <small class="text-muted">#${carro.numero_carro}</small>
            `;
            botao.onclick = () => {
                criarSolicitacoesInstalacaoArmazem(carro.id, carrinhoArmazem, false);
                bootstrap.Modal.getInstance(modal).hide();
            };
            listaCarros.appendChild(botao);
        });
        
        // Mostrar modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
    } catch (e) {
        console.error('Erro ao processar repouso:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

async function criarSolicitacoesInstalacaoArmazem(carroId, pecas, comPix) {
    /**Cria solicitações de instalação para as peças do carrinho*/
    try {
        mostrarToast('⏳ Criando solicitações...', 'info');
        
        const respSolicitacoes = await fetch('/api/garagem/criar-multiplas-solicitacoes-armazem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                carro_id: carroId,
                pecas: pecas.map(p => ({
                    nome: p.nome,
                    tipo: p.tipo,
                    quantidade: p.quantidade,
                    pix_id: p.pix_id
                })),
                com_pix: comPix
            })
        });
        
        const resultado = await respSolicitacoes.json();
        
        if (!resultado.sucesso) {
            mostrarToast('Erro: ' + (resultado.erro || 'Erro desconhecido'), 'error');
            return;
        }
        
        mostrarToast(`✅ ${resultado.solicitacoes_criadas} solicitações criadas com sucesso!`, 'success');
        limparCarrinhoArmazem(true);
        carregarGaragem();
        
    } catch (e) {
        console.error('Erro ao criar solicitações:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

// ============= MODAL DE ADIÇÃO DE PEÇAS DO ARMAZÉM (NOVA VERSÃO) =============

function abrirModalAdicionarPecasArmazem() {
    /**Abre modal para selecionar peças do armazém e seu destino (por item)*/
    console.log('[MODAL] Abrindo modal de adição de peças');
    console.log('[MODAL] window.garagemAtual:', window.garagemAtual);
    
    // Carregar preço de instalação warehouse
    obterPrecoInstalacaoWarehouse();
    
    if (!window.garagemAtual || !window.garagemAtual.armazem) {
        console.error('[MODAL] Garagem ou armazém não carregado');
        mostrarToast('⏳ Aguarde o carregamento do armazém...', 'info');
        return;
    }
    
    const pecasArmazem = window.garagemAtual.armazem.pecas_guardadas || [];
    console.log('[MODAL] Peças no armazém:', pecasArmazem);
    
    if (pecasArmazem.length === 0) {
        console.warn('[MODAL] Nenhuma peça no armazém');
        mostrarToast('Nenhuma peça no armazém', 'warning');
        return;
    }
    
    // Criar ou obter modal
    let modal = document.getElementById('modalAdicionarPecasArmazem');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modalAdicionarPecasArmazem';
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.setAttribute('data-bs-backdrop', 'static');
        modal.setAttribute('data-bs-keyboard', 'false');
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-dark text-white">
                        <h5 class="modal-title">➕ Adicionar Peças do Armazém</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="listaPecasParaAdicionar"></div>
                        <div id="resumoAdicaoPecas" style="display: none; margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                            <h6>📊 Resumo da Adição</h6>
                            <div class="d-flex justify-content-between mb-2">
                                <strong>Total de Peças Selecionadas:</strong>
                                <strong id="totalPecasSelecionadas">0</strong>
                            </div>
                            <div class="d-flex justify-content-between">
                                <strong>Valor Total PIX Estimado:</strong>
                                <strong id="valorTotalPIXEstimado">R$ 0,00</strong>
                            </div>
                            <small class="text-muted d-block mt-2">💡 PIX será cobrado apenas para peças SEM pagamento indo para o carro ativo</small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-success" onclick="confirmarAdicaoPecasArmazem()">✓ Confirmar Adição</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    // Popular lista de peças
    const listaPecas = modal.querySelector('#listaPecasParaAdicionar');
    listaPecas.innerHTML = '';
    
    // Estrutura: selecaoAdicaoPecas = { "peca_id_ou_nome": { quantidade: 1, destino_carro_id: null, ... } }
    if (!window.selecaoAdicaoPecas) {
        window.selecaoAdicaoPecas = {};
    }
    
    pecasArmazem.forEach((peca, idx) => {
        const durabilidade = peca.durabilidade_percentual || 0;
        const durabilidadeClass = durabilidade > 75 ? 'success' : durabilidade > 50 ? 'warning' : 'danger';
        const pecaKey = peca.id || `${peca.nome}-${peca.tipo}`;
        
        if (!window.selecaoAdicaoPecas[pecaKey]) {
            window.selecaoAdicaoPecas[pecaKey] = {
                selecionada: false,
                quantidade: 1,
                destino_tipo: 'ativo', // 'ativo' ou 'repouso'
                destino_carro_id: null,
                peca: peca
            };
        }
        
        const selecao = window.selecaoAdicaoPecas[pecaKey];
        
        // Gerar lista de carros para dropdown
        let opcoesCarros = '<option value="">-- Selecione um carro --</option>';
        const carrosGaragem = Array.isArray(window.garagemAtual?.carros) ? window.garagemAtual.carros : [];
        if (carrosGaragem.length) {
            opcoesCarros += carrosGaragem.map(carro => {
                const ativo = carro.carro_ativo ? ' [ATIVO]' : '';
                return `<option value="${carro.id}" ${carro.carro_ativo ? 'selected' : ''}>${carro.marca} ${carro.modelo}${ativo}</option>`;
            }).join('');
        }
        
        const itemHtml = `
            <div class="card mb-3 pecaArmazemItem" id="pecaItem_${pecaKey}">
                <div class="card-body p-3 text-dark">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <input type="checkbox" class="form-check-input form-check-input-lg" 
                                id="selecionar_${pecaKey}" 
                                ${selecao.selecionada ? 'checked' : ''}
                                onchange="atualizarSelecaoPecasArmazem('${pecaKey}')">
                        </div>
                        <div class="col">
                            <div class="form-check">
                                <label class="form-check-label text-dark" for="selecionar_${pecaKey}">
                                    <strong class="text-dark">${peca.nome}</strong>
                                    <br>
                                    <span class="badge bg-info text-dark">${peca.tipo}</span>
                                    <span class="badge bg-secondary text-dark">${formatarMoeda(peca.preco)}</span>
                                    ${peca.pix_id ? '<span class="badge bg-success text-dark">✓ Pago</span>' : '<span class="badge bg-warning text-dark">Não Pago</span>'}
                                </label>
                            </div>
                            <small class="d-block mt-2" style="color: #000 !important;">
                                Durabilidade: ${durabilidade}% | Carro Original: ${peca.carro_nome}
                            </small>
                        </div>
                        <div class="col-md-4" style="display: ${selecao.selecionada ? 'block' : 'none'}" id="config_${pecaKey}">
                            <div class="mb-2">
                                <label class="form-label form-label-sm">Destino:</label>
                                <select class="form-select form-select-sm" onchange="atualizarDestinoPecasArmazem('${pecaKey}', this.value)">
                                    <option value="">-- Escolha o destino --</option>
                                    <option value="ativo" ${selecao.destino_tipo === 'ativo' ? 'selected' : ''}>🏁 Carro Ativo</option>
                                    <option value="repouso" ${selecao.destino_tipo === 'repouso' ? 'selected' : ''}>😴 Carro em Repouso</option>
                                </select>
                            </div>
                            <div id="carroSelect_${pecaKey}" style="display: none;">
                                <label class="form-label form-label-sm">Qual carro?</label>
                                <select class="form-select form-select-sm" onchange="atualizarCarroDestino('${pecaKey}', this.value)">
                                    ${opcoesCarros}
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        listaPecas.innerHTML += itemHtml;
    });
    
    // Mostrar modal
    console.log('[MODAL] Criando Bootstrap Modal instance');
    try {
        if (modal.getAttribute('data-bs-modal-instance')) {
            console.log('[MODAL] Usando modal existente');
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.show();
            } else {
                const novaInstancia = new bootstrap.Modal(modal);
                novaInstancia.show();
            }
        } else {
            console.log('[MODAL] Criando nova instância do modal');
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
            modal.setAttribute('data-bs-modal-instance', 'true');
        }
    } catch (e) {
        console.error('[MODAL] Erro ao abrir modal:', e);
        mostrarToast('Erro ao abrir modal: ' + e.message, 'error');
        return;
    }
    
    atualizarResumoAdicaoPecas();
    console.log('[MODAL] Modal aberto com sucesso');
}

function atualizarSelecaoPecasArmazem(pecaKey) {
    /**Marca/desmarca uma peça para adição*/
    const checkbox = document.getElementById(`selecionar_${pecaKey}`);
    const config = document.getElementById(`config_${pecaKey}`);
    
    if (!window.selecaoAdicaoPecas || !window.selecaoAdicaoPecas[pecaKey]) return;
    
    const selecionada = checkbox.checked;
    window.selecaoAdicaoPecas[pecaKey].selecionada = selecionada;
    
    // Mostrar/ocultar configurações
    if (config) {
        config.style.display = selecionada ? 'block' : 'none';
    }
    
    // Se selecionou, aplicar filtro de compatibilidade
    if (selecionada) {
        atualizarCompatibilidadeCarrosArmazem(pecaKey);
    } else {
        // Se deselecionar, remover restrições de compatibilidade
        removerFiltroCompatibilidadeArmazem();
    }
    
    // Mostrar/ocultar dropdown de carro
    const carroSelect = document.getElementById(`carroSelect_${pecaKey}`);
    if (carroSelect) {
        carroSelect.style.display = 
            selecionada && window.selecaoAdicaoPecas[pecaKey].destino_tipo === 'repouso' ? 'block' : 'none';
    }
    
    atualizarResumoAdicaoPecas();
}

function atualizarCompatibilidadeCarrosArmazem(pecaKey) {
    /**Desabilita carros incompatíveis com a peça selecionada*/
    if (!window.selecaoAdicaoPecas || !window.selecaoAdicaoPecas[pecaKey]) return;
    
    const peca = window.selecaoAdicaoPecas[pecaKey].peca;
    const compatibilidades = peca.compatibilidades || [];
    
    // Se vazia, significa universal - todos são compatíveis
    const ehUniversal = compatibilidades.length === 0;
    
    console.log(`[COMPATIBILIDADE] Peça ${peca.nome}: universal=${ehUniversal}, compatíveis=[${compatibilidades.join(',')}]`);
    
    // Converter para inteiros para comparação
    const compatibilidadesInt = compatibilidades.map(c => parseInt(c));
    
    // Atualizar todos os dropdowns de carros no modal
    const selectsCarros = document.querySelectorAll('[id^="carroSelect_"] select');
    selectsCarros.forEach(select => {
        const opcoes = select.querySelectorAll('option');
        opcoes.forEach(opcao => {
            const carroId = opcao.value;
            
            if (!carroId) {
                // Opção vazia (placeholder)
                opcao.disabled = false;
                opcao.style.opacity = '1';
                opcao.style.cursor = 'pointer';
                return;
            }
            
            // Verificar se é compatível
            const carroIdInt = parseInt(carroId);
            const ehCompativel = ehUniversal || compatibilidadesInt.includes(carroIdInt);
            
            if (!ehCompativel) {
                opcao.disabled = true;
                opcao.style.opacity = '0.5';
                opcao.style.cursor = 'not-allowed';
                opcao.textContent = opcao.textContent.split(' (')[0] + ' (Incompatível)';
            } else {
                opcao.disabled = false;
                opcao.style.opacity = '1';
                opcao.style.cursor = 'pointer';
                opcao.textContent = opcao.textContent.split(' (')[0]; // Remover label de incompatível
            }
        });
    });
}

function removerFiltroCompatibilidadeArmazem() {
    /**Remove o filtro de compatibilidade, habilitando todos os carros*/
    const selectsCarros = document.querySelectorAll('[id^="carroSelect_"] select');
    selectsCarros.forEach(select => {
        const opcoes = select.querySelectorAll('option');
        opcoes.forEach(opcao => {
            opcao.disabled = false;
            opcao.style.opacity = '1';
            opcao.style.cursor = 'pointer';
            opcao.textContent = opcao.textContent.split(' (')[0]; // Remover labels
        });
    });
}

function atualizarDestinoPecasArmazem(pecaKey, novoDestino) {
    /**Atualiza o tipo de destino (ativo ou repouso) e filtra carros disponíveis*/
    if (!window.selecaoAdicaoPecas || !window.selecaoAdicaoPecas[pecaKey]) return;
    
    window.selecaoAdicaoPecas[pecaKey].destino_tipo = novoDestino;
    
    // Mostrar/ocultar dropdown de carro baseado no destino
    const carroSelect = document.getElementById(`carroSelect_${pecaKey}`);
    if (carroSelect) {
        carroSelect.style.display = novoDestino === 'repouso' ? 'block' : 'none';
        
        // Se selecionou repouso, filtrar para mostrar apenas carros em repouso
        if (novoDestino === 'repouso') {
            const carrosEmRepouso = (window.garagemAtual?.carros || []).filter(c => c && !c.carro_ativo);
            const selectElement = carroSelect.querySelector('select');
            if (selectElement) {
                const opcoes = selectElement.querySelectorAll('option');
                let carrosRepousoHabilitados = [];
                opcoes.forEach(opcao => {
                    if (opcao.value === '') return; // Manter placeholder
                    
                    const carro = window.garagemAtual?.carros?.find(c => String(c.id) === String(opcao.value));
                    
                    if (carro && carro.carro_ativo) {
                        opcao.disabled = true;
                        opcao.style.opacity = '0.5';
                        opcao.style.cursor = 'not-allowed';
                        if (!opcao.textContent.includes('(Ativo)')) {
                            opcao.textContent = opcao.textContent.split(' (')[0] + ' (Ativo - não disponível)';
                        }
                    } else {
                        opcao.disabled = false;
                        opcao.style.opacity = '1';
                        opcao.style.cursor = 'pointer';
                        opcao.textContent = opcao.textContent.split(' (')[0];
                        if (carro) carrosRepousoHabilitados.push({ id: carro.id });
                    }
                });
                // Se só tem 1 carro em repouso, auto-selecionar
                if (carrosRepousoHabilitados.length === 1) {
                    const carroUnico = carrosRepousoHabilitados[0];
                    selectElement.value = carroUnico.id;
                    window.selecaoAdicaoPecas[pecaKey].destino_carro_id = carroUnico.id;
                }
            }
        } else {
            // Se selecionou ativo, habilitar todos os carros ativos
            const selectElement = carroSelect.querySelector('select');
            if (selectElement) {
                const opcoes = selectElement.querySelectorAll('option');
                opcoes.forEach(opcao => {
                    if (opcao.value === '') return;
                    
                    const carro = window.garagemAtual?.carros?.find(c => String(c.id) === String(opcao.value));
                    
                    if (carro && carro.carro_ativo) {
                        opcao.disabled = false;
                        opcao.style.opacity = '1';
                        opcao.style.cursor = 'pointer';
                        opcao.textContent = opcao.textContent.split(' (')[0];
                    } else {
                        // Repouso não é válido para ativo
                        opcao.disabled = true;
                        opcao.style.opacity = '0.5';
                        opcao.style.cursor = 'not-allowed';
                        if (!opcao.textContent.includes('(Repouso)')) {
                            opcao.textContent = opcao.textContent.split(' (')[0] + ' (Repouso - não disponível)';
                        }
                    }
                });
            }
        }
    }
    
    atualizarResumoAdicaoPecas();
}

function atualizarCarroDestino(pecaKey, carroId) {
    /**Atualiza o carro de destino para repouso*/
    if (!window.selecaoAdicaoPecas || !window.selecaoAdicaoPecas[pecaKey]) return;
    
    window.selecaoAdicaoPecas[pecaKey].destino_carro_id = carroId || null;
    
    atualizarResumoAdicaoPecas();
}

function atualizarResumoAdicaoPecas() {
    /**Atualiza o resumo de peças e valores a serem cobrados*/
    if (!window.selecaoAdicaoPecas) return;
    
    const resumoDiv = document.getElementById('resumoAdicaoPecas');
    if (!resumoDiv) return;
    
    const pecasSelecionadas = Object.values(window.selecaoAdicaoPecas).filter(s => s.selecionada);
    
    if (pecasSelecionadas.length === 0) {
        resumoDiv.style.display = 'none';
        return;
    }
    
    resumoDiv.style.display = 'block';
    
    let totalPecas = 0;
    let valorTotalPix = 0;
    
    pecasSelecionadas.forEach(selecao => {
        totalPecas += 1;
        
        // Calcular PIX: apenas peças SEM pix_id indo para carro ativo
        // USA O PREÇO DE INSTALAÇÃO WAREHOUSE DA CONFIG, NÃO O PREÇO DA PEÇA
        if (selecao.destino_tipo === 'ativo' && !selecao.peca.pix_id) {
            valorTotalPix += precoInstalacaoWarehouse;
        }
    });
    
    document.getElementById('totalPecasSelecionadas').textContent = totalPecas;
    document.getElementById('valorTotalPIXEstimado').textContent = formatarMoeda(valorTotalPix);
}

async function confirmarAdicaoPecasArmazem() {
    /**Processa a adição de peças selecionadas*/
    try {
        if (!window.selecaoAdicaoPecas) {
            mostrarToast('Nenhuma seleção realizada', 'warning');
            return;
        }
        
        const pecasSelecionadas = Object.entries(window.selecaoAdicaoPecas)
            .filter(([_, s]) => s.selecionada)
            .map(([_, s]) => ({
                id: s.peca.id,
                nome: s.peca.nome,
                tipo: s.peca.tipo,
                preco: s.peca.preco,
                pix_id: s.peca.pix_id,
                quantidade: 1, // Sempre 1
                destino_tipo: s.destino_tipo,
                destino_carro_id: s.destino_carro_id
            }));
        
        if (pecasSelecionadas.length === 0) {
            mostrarToast('Selecione pelo menos uma peça', 'warning');
            return;
        }
        
        // Validar destinos
        for (const peca of pecasSelecionadas) {
            if (!peca.destino_tipo) {
                mostrarToast(`${peca.nome}: Selecione um destino`, 'warning');
                return;
            }
            if (peca.destino_tipo === 'repouso' && !peca.destino_carro_id) {
                mostrarToast(`${peca.nome}: Selecione um carro em repouso`, 'warning');
                return;
            }
        }
        
        // Separar por destino
        const pecasParaAtivo = pecasSelecionadas.filter(p => p.destino_tipo === 'ativo');
        const pecasParaRepouso = pecasSelecionadas.filter(p => p.destino_tipo === 'repouso');
        
        // Fechar modal
        const modal = document.getElementById('modalAdicionarPecasArmazem');
        const bootstrapModal = bootstrap.Modal.getInstance(modal);
        if (bootstrapModal) bootstrapModal.hide();
        
        // Processar peças para carro ativo (gerar PIX se necessário)
        if (pecasParaAtivo.length > 0) {
            await processarPecasParaAtivoModal(pecasParaAtivo);
        }
        
        // Processar peças para carros em repouso (sem PIX)
        if (pecasParaRepouso.length > 0) {
            await processarPecasParaRepousoModal(pecasParaRepouso);
        }
        
        // Limpar seleção
        window.selecaoAdicaoPecas = {};
        
    } catch (e) {
        console.error('Erro ao confirmar adição:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

async function processarPecasParaAtivoModal(pecas) {
    /**Peças para carro ativo: gera PIX (cobrança). Após pagamento, peças vão ao armazém e são criadas solicitações de instalação.*/
    try {
        if (!equipeAtual || !equipeAtual.carro_ativo) {
            mostrarToast('⚠️ Você não tem um carro ativo selecionado', 'warning');
            return;
        }

        const carroAtivoId = equipeAtual.carro_ativo.id;
        mostrarToast('⏳ Gerando PIX...', 'info');

        const respPix = await fetch('/api/instalar-multiplas-pecas-no-carro-ativo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...obterHeaders() },
            body: JSON.stringify({
                carro_id: carroAtivoId,
                pecas: pecas.map(p => ({
                    nome: p.nome,
                    tipo: p.tipo,
                    quantidade: p.quantidade || 1,
                    id: p.id
                }))
            })
        });

        const resultado = await respPix.json();
        if (!resultado.sucesso) {
            mostrarToast('Erro: ' + (resultado.erro || 'Erro desconhecido'), 'error');
            return;
        }

        pecas.forEach(p => { p.pix_id = resultado.pix_id; });
        window.compraPendentePix = {
            transacao_id: resultado.transacao_id,
            tipo: 'multiplas_pecas_armazem_ativo_modal',
            carro_id: carroAtivoId,
            pecas: pecas
        };

        const dadosPix = {
            transacao_id: resultado.transacao_id,
            qr_code_url: resultado.qr_code_url,
            item_nome: resultado.item_nome || (pecas.length + ' peça(s) → Carro Ativo'),
            item_id: carroAtivoId,
            tipo_item: 'multiplas_pecas_armazem_ativo_modal',
            valor_item: resultado.valor_item,
            taxa: resultado.valor_taxa,
            valor_total: resultado.valor_total
        };
        mostrarModalPix(dadosPix);
    } catch (e) {
        console.error('Erro ao processar ativo:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

async function processarPecasParaRepousoModal(pecas) {
    /**Processa peças para carros em repouso (instala direto sem solicitação)*/
    try {
        console.log('[REPOUSO] Processando peças para repouso:', pecas);
        
        // Validar que todas as peças têm destino_carro_id
        for (const peca of pecas) {
            if (!peca.destino_carro_id) {
                console.error('[REPOUSO] Peça sem destino_carro_id:', peca);
                mostrarToast(`${peca.nome}: Selecione um carro em repouso`, 'warning');
                return;
            }
        }
        
        mostrarToast('⏳ Instalando peças...', 'info');
        
        // Agrupar por carro
        const porCarro = {};
        pecas.forEach(peca => {
            if (!porCarro[peca.destino_carro_id]) {
                porCarro[peca.destino_carro_id] = [];
            }
            porCarro[peca.destino_carro_id].push(peca);
        });
        
        console.log('[REPOUSO] Carros agrupados:', Object.keys(porCarro));
        
        // Instalar peças para cada carro (sem PIX, sem solicitações)
        for (const [carroId, pecasDoCarrro] of Object.entries(porCarro)) {
            console.log(`[REPOUSO] Instalando ${pecasDoCarrro.length} peça(s) no carro ${carroId}`);
            await instalarPecasRepouso(carroId, pecasDoCarrro);
        }
        
    } catch (e) {
        console.error('Erro ao processar repouso:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

async function instalarPecasRepouso(carroId, pecas) {
    /**Instala peças diretamente em carro em repouso (sem solicitação, sem PIX)*/
    try {
        console.log('[REPOUSO] Instalando peças:', pecas);
        
        const respInstalar = await fetch('/api/garagem/instalar-multiplas-pecas-armazem-repouso', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                carro_id: carroId,
                pecas: pecas.map(p => ({
                    nome: p.nome,
                    tipo: p.tipo,
                    pix_id: p.pix_id
                }))
            })
        });
        
        const resultado = await respInstalar.json();
        
        console.log('[REPOUSO] Resposta status:', respInstalar.status);
        console.log('[REPOUSO] Resultado:', resultado);
        
        if (!resultado.sucesso) {
            const erro = resultado.erro || 'Erro desconhecido';
            console.error('[REPOUSO] Erro ao instalar:', erro);
            mostrarToast('Erro: ' + erro, 'error');
            return;
        }
        
        mostrarToast(`✅ ${resultado.pecas_instaladas} peça(s) instalada(s)!`, 'success');
        carregarGaragem();
        
    } catch (e) {
        console.error('Erro ao instalar peças repouso:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

async function criarSolicitacoesModalPecas(carroId, pecas, comPix) {
    /**Cria solicitações para peças adicionadas pelo modal*/
    try {
        console.log('[SOLICITAÇÕES] Criando solicitações:', {
            carro_id: carroId,
            pecas: pecas,
            com_pix: comPix
        });
        
        const respSolicitacoes = await fetch('/api/garagem/criar-multiplas-solicitacoes-armazem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                carro_id: carroId,
                pecas: pecas.map(p => ({
                    nome: p.nome,
                    tipo: p.tipo,
                    quantidade: p.quantidade,
                    pix_id: p.pix_id
                })),
                com_pix: comPix
            })
        });
        
        const resultado = await respSolicitacoes.json();
        
        console.log('[SOLICITAÇÕES] Resposta status:', respSolicitacoes.status);
        console.log('[SOLICITAÇÕES] Resultado:', resultado);
        
        if (!resultado.sucesso) {
            const erro = resultado.erro || 'Erro desconhecido';
            console.error('[SOLICITAÇÕES] Erro ao criar:', erro);
            mostrarToast('Erro: ' + erro, 'error');
            return;
        }
        
        mostrarToast(`✅ ${resultado.solicitacoes_criadas} solicitações criadas!`, 'success');
        carregarGaragem();
        
    } catch (e) {
        console.error('Erro ao criar solicitações:', e);
        mostrarToast('Erro: ' + e.message, 'error');
    }
}

// ============= SISTEMA DE CARRINHO DE PEÇAS =============

function mostrarModalCompraFinalizada(saldoAnterior, valorGasto) {
    /**Mostra modal de compra finalizada com saldo antes e depois*/
    
    // Se é regularização de etapa, não mostrar modal de compra
    if (window.tipo_transacao_atual === 'regularizacao') {
        console.log('[MODAL COMPRA] Skipping - transação é regularização, não carrinho');
        window.tipo_transacao_atual = null;  // Limpar
        return;
    }
    
    const modal = document.getElementById('compraFinalizadaModal');

    if (!modal) {
        console.error('Modal de compra finalizada não encontrado');
        return;
    }

    const novoSaldo = saldoAnterior - valorGasto;

    // Atualizar valores no modal
    document.getElementById('saldoAnterior').textContent = formatarMoeda(saldoAnterior);
    document.getElementById('valorGasto').textContent = formatarMoeda(valorGasto);
    document.getElementById('novoSaldo').textContent = formatarMoeda(novoSaldo);

    console.log('[MODAL COMPRA] Saldo Anterior:', saldoAnterior);
    console.log('[MODAL COMPRA] Valor Gasto:', valorGasto);
    console.log('[MODAL COMPRA] Novo Saldo:', novoSaldo);

    // Mostrar modal
    bootstrap.Modal.getOrCreateInstance(modal).show();
}

function fecharModalCompraFinalizada() {
    /**Fecha o modal de compra finalizada*/
    const modal = document.getElementById('compraFinalizadaModal');
    if (modal) {
        bootstrap.Modal.getInstance(modal)?.hide();
    }
}

function adicionarAoCarrinho(pecaId, nomePeca, preco, compatibilidade, tipo) {
    /**Adiciona uma peça ao carrinho*/
    const peca = {
        id: pecaId,
        nome: nomePeca,
        preco: parseFloat(preco),
        compatibilidade: compatibilidade,
        tipo: tipo,
        quantidade: 1
    };

    // Verificar se a peça já está no carrinho
    const existente = carrinho.find(p => p.id === pecaId);
    if (existente) {
        // Apenas 1 peça de cada tipo no carrinho do carro ativo!
        mostrarToast(`${nomePeca} já está no carrinho! Cada peça pode ser adicionada apenas uma vez.`, 'warning');
        return;
    } else {
        carrinho.push(peca);
    }

    console.log('[CARRINHO] Peça adicionada:', peca);
    console.log('[CARRINHO] Total de itens:', carrinho.length);
    atualizarUICarrinho();

    // Atualizar painel flutuante se existir
    if (typeof atualizarPainelCarrinho === 'function') {
        atualizarPainelCarrinho();
    }
}

function removerDoCarrinho(pecaId) {
    /**Remove uma peça do carrinho*/
    carrinho = carrinho.filter(p => p.id !== pecaId);
    console.log('[CARRINHO] Peça removida. Total de itens:', carrinho.length);
    atualizarUICarrinho();
}

function limparCarrinho() {
    /**Limpa o carrinho inteiro*/
    carrinho = [];
    console.log('[CARRINHO] Carrinho limpo');
    atualizarUICarrinho();
}

function calcularTotalCarrinho() {
    /**Calcula o valor total do carrinho*/
    return carrinho.reduce((total, peca) => total + (peca.preco * peca.quantidade), 0);
}

function atualizarUICarrinho() {
    /**Atualiza a interface do carrinho*/
    const badge = document.getElementById('carrinhoQtd');
    const container = document.getElementById('carrinhoPanelContent');
    const btnComprar = document.getElementById('btnComprar');

    if (badge) {
        badge.textContent = carrinho.length;
        badge.style.display = carrinho.length > 0 ? 'inline-block' : 'none';
    }

    // Mostrar/ocultar botão de comprar
    if (btnComprar) {
        btnComprar.style.display = carrinho.length > 0 ? 'block' : 'none';
    }

    if (container) {
        if (carrinho.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">Carrinho vazio</p>';
            return;
        }

        const total = calcularTotalCarrinho();
        let html = `
            <div class="carrinho-itens">
                <h6>Itens no Carrinho (${carrinho.length})</h6>
                <div style="max-height: 300px; overflow-y: auto;">
        `;

        carrinho.forEach(peca => {
            html += `
                <div class="carrinho-item mb-2 p-2 border rounded d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${peca.nome}</strong><br>
                        <small class="text-muted">${formatarMoeda(peca.preco)} x ${peca.quantidade || 1}</small>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="removerDoCarrinho('${peca.id}')">
                        ✕
                    </button>
                </div>
            `;
        });

        html += `
                </div>
                <div class="mt-3 pt-2 border-top">
                    <strong>Total: ${formatarMoeda(total)}</strong>
                </div>
                <button class="btn btn-sm btn-warning w-100 mt-2" onclick="limparCarrinho()">
                    Limpar Carrinho
                </button>
            </div>
        `;

        container.innerHTML = html;
    }
}



// Armazenar destino de cada peça no carrinho
let destinosPecas = {};

function abrirModalDestino() {
    if (carrinho.length === 0) {
        mostrarToast('Carrinho vazio! Adicione peças antes de continuar', 'error');
        return;
    }

    // Inicializar destinos (padrão: armazém)
    destinosPecas = {};
    carrinho.forEach(peca => {
        if (!destinosPecas[peca.id]) {
            destinosPecas[peca.id] = 'armazem';
        }
    });

    renderizarListaPecasDestino();

    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('modalDestino'));
    modal.show();
}

function verificarPecasDuplicadasNoCarroAtivo() {
    /**Verifica se há mais de 1 peça BASE do mesmo tipo destinada ao carro ativo. Upgrades não contam (1 base + N upgrades por slot).*/
    const pecasCarroAtivo = carrinho.filter(p => destinosPecas[p.id] === 'carro_ativo');

    // Contar apenas peças BASE por tipo (upgrades têm tipo === 'upgrade' e não limitam)
    const contagemTipos = {};
    let temDuplicatas = false;
    const idsComDuplicatas = [];

    pecasCarroAtivo.forEach(peca => {
        if (peca.tipo === 'upgrade') return; // upgrades não contam para o limite de 1 por slot
        const tipo = peca.tipo || peca.compatibilidade || 'desconhecido';
        contagemTipos[tipo] = (contagemTipos[tipo] || 0) + 1;
        if (contagemTipos[tipo] > 1) {
            temDuplicatas = true;
            if (!idsComDuplicatas.includes(peca.id)) idsComDuplicatas.push(peca.id);
        }
    });

    return { temDuplicatas, idsComDuplicatas };
}

function renderizarListaPecasDestino() {
    const container = document.getElementById('listaPecasDestino');
    const carroAtivo = equipeAtual?.carro_ativo;  // Usar carro_ativo (status='ativo' do banco)

    // Contar apenas peças BASE por tipo; upgrades (tipo === 'upgrade') não limitam — 1 base + N upgrades por slot
    const pecasCarroAtivo = carrinho.filter(p => destinosPecas[p.id] === 'carro_ativo');
    const contagemTipos = {};
    const tiposComDuplicatas = [];

    pecasCarroAtivo.forEach(peca => {
        if (peca.tipo === 'upgrade') return;
        const tipo = peca.tipo || 'desconhecido';
        contagemTipos[tipo] = (contagemTipos[tipo] || 0) + 1;
    });

    Object.keys(contagemTipos).forEach(tipo => {
        if (contagemTipos[tipo] > 1) tiposComDuplicatas.push(tipo);
    });

    const temDuplicatas = tiposComDuplicatas.length > 0;

    let avisoHtml = '';
    if (temDuplicatas) {
        avisoHtml = '<div style="background-color: #ffcccc; border: 2px solid #cc0000; color: #cc0000; padding: 15px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; text-align: center;">⚠️ AVISO: Existem peças base do mesmo tipo destinadas ao carro ativo! Cada tipo pode ter apenas 1 peça base (e vários upgrades).</div>';
    }

    let html = avisoHtml;

    carrinho.forEach(peca => {
        const destino = destinosPecas[peca.id] || 'armazem';
        const subtotal = peca.preco * (peca.quantidade || 1);

        // Verificar se esta peça é duplicata: apenas peças base contam; upgrades nunca são duplicata
        const tipo = peca.tipo || 'desconhecido';
        const ehDuplicata = destino === 'carro_ativo' && peca.tipo !== 'upgrade' && tiposComDuplicatas.includes(tipo);
        const bgColor = ehDuplicata ? 'background-color: #ffeeee;' : '';
        const borderColor = ehDuplicata ? 'border: 2px solid #ff6666;' : 'border: 1px solid #ddd;';
        
        // Buscar qual peça será substituída no carro ativo (mostrar sempre como preview)
        let pecaSubstituinda = '';
        const carrosGaragemAtual = Array.isArray(window.garagemAtual?.carros) ? window.garagemAtual.carros : [];
        if (carrosGaragemAtual.length) {
            const carro = carrosGaragemAtual.find(c => c.carro_ativo);
            if (carro && carro.pecas) {
                const pecaExistente = carro.pecas.find(p => p.tipo === tipo);
                if (pecaExistente) {
                    // Mostrar como preview mesmo se não está selecionado para carro ativo
                    const avisoStyle = destino === 'carro_ativo' 
                        ? 'text-warning' 
                        : 'text-muted';
                    const prefixo = destino === 'carro_ativo' 
                        ? '↪️ Substituirá' 
                        : '📌 Se enviado para Carro Ativo, substituirá';
                    pecaSubstituinda = `<div class="${avisoStyle}" style="font-size: 0.85em; margin-top: 5px;">${prefixo}: <strong>${pecaExistente.nome}</strong>${destino === 'carro_ativo' ? ' (irá para armazém)' : ''}</div>`;
                }
            }
        }

        html += `
            <div class="peca-destino-item" style="${bgColor}${borderColor}border-radius: 8px;">
                <div class="peca-destino-header">
                    <div>
                        <div class="peca-destino-nome">${peca.nome}</div>
                        <div class="peca-destino-preco">${formatarMoeda(peca.preco)} x ${peca.quantidade || 1} = ${formatarMoeda(subtotal)}</div>
                        ${pecaSubstituinda}
                    </div>
                </div>
                <div class="peca-destino-buttons">
                    <button class="peca-destino-btn armazem ${destino === 'armazem' ? 'active' : ''}" onclick="selecionarDestinoPeca('${peca.id}', 'armazem')">
                        📦 Armazém
                    </button>
                    <button class="peca-destino-btn carro ${destino === 'carro_ativo' ? 'active' : ''}" 
                        onclick="selecionarDestinoPeca('${peca.id}', 'carro_ativo')"
                        ${!carroAtivo ? 'disabled' : ''}>
                        🚗 ${carroAtivo ? 'Carro Ativo' : 'Sem Carro'}
                    </button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    atualizarTotaisPecas();
}

function selecionarDestinoPeca(pecaId, novoDestino) {
    const carroAtivo = equipeAtual?.carro_ativo;  // Usar carro_ativo (status='ativo' do banco)

    // Validar se escolheu carro ativo sem ter um
    if (novoDestino === 'carro_ativo' && !carroAtivo) {
        mostrarToast('Você não tem um carro ativo selecionado!', 'error');
        return;
    }

    destinosPecas[pecaId] = novoDestino;
    renderizarListaPecasDestino();  // Redesenhar para mostrar avisos de duplicata
}

function atualizarTotaisPecas() {
    let totalArmazem = 0;
    let totalCarroAtivo = 0;
    let qtdArmazem = 0;
    let qtdCarroAtivo = 0;

    carrinho.forEach(peca => {
        const subtotal = peca.preco * (peca.quantidade || 1);
        const destino = destinosPecas[peca.id] || 'armazem';

        if (destino === 'armazem') {
            totalArmazem += subtotal;
            qtdArmazem++;
        } else if (destino === 'carro_ativo') {
            totalCarroAtivo += subtotal;
            qtdCarroAtivo++;
        }
    });

    document.getElementById('totalArmazem').textContent = formatarMoeda(totalArmazem);
    document.getElementById('totalCarroAtivo').textContent = formatarMoeda(totalCarroAtivo);
    document.getElementById('qtdArmazem').textContent = `${qtdArmazem} peça${qtdArmazem !== 1 ? 's' : ''}`;
    document.getElementById('qtdCarroAtivo').textContent = `${qtdCarroAtivo} peça${qtdCarroAtivo !== 1 ? 's' : ''}`;
}

async function confirmarDistribuicaoPecas() {
    // Verificar se há duplicatas no carro ativo
    const { temDuplicatas } = verificarPecasDuplicadasNoCarroAtivo();

    if (temDuplicatas) {
        mostrarToast('❌ Não é permitido ter peças duplicadas no carro ativo! Verifique os itens em vermelho.', 'error');
        return;  // Bloqueia o avanço e fica na modal
    }

    const modal = bootstrap.Modal.getInstance(document.getElementById('modalDestino'));
    modal.hide();

    // Separar peças por destino
    const pecasArmazem = carrinho.filter(p => destinosPecas[p.id] === 'armazem');
    const pecasCarroAtivo = carrinho.filter(p => destinosPecas[p.id] === 'carro_ativo');

    console.log('[CARRINHO] Distribuição de peças:');
    console.log(`  - Armazém: ${pecasArmazem.length} peças`);
    console.log(`  - Carro Ativo: ${pecasCarroAtivo.length} peças`);

    // Aguardar modal fechar antes de processar
    await new Promise(resolve => setTimeout(resolve, 300));

    // Se tem peças para carro ativo: enviar ao armazém + criar solicitação; se tem para armazém, enviar ao armazém
    if (pecasCarroAtivo.length > 0) {
        window.pecasCarrinho = carrinho;
        window.pecasCarroAtivo = pecasCarroAtivo;
        window.pecasArmazem = pecasArmazem;
        await processarPecasParaAtivoModal(pecasCarroAtivo);
    }
    if (pecasArmazem.length > 0) {
        window.pecasArmazem = pecasArmazem;
        await enviarCarrinhoParaArmazemDividido();
    }
}

async function gerarPixCarroAtivoDividido() {
    /**Gera PIX apenas para peças que vão para o carro ativo*/
    const pecasCarroAtivo = window.pecasCarroAtivo || [];

    if (pecasCarroAtivo.length === 0) {
        mostrarToast('Nenhuma peça selecionada para o carro ativo!', 'error');
        return;
    }

    const carroAtivo = equipeAtual?.carro_ativo;  // Usar carro_ativo (status='ativo' do banco)
    if (!carroAtivo) {
        mostrarToast('Nenhum carro ativo selecionado!', 'error');
        return;
    }

    console.log('[CARRINHO PIX DIVIDIDO] Peças para carro ativo:', pecasCarroAtivo);

    try {
        // 1. Buscar configuração de comissão
        let comissaoPeca = 10;  // Valor padrão
        try {
            const respConfig = await fetch('/api/admin/configuracoes', {
                headers: obterHeaders()
            });
            const configResult = await respConfig.json();
            console.log('[CARRINHO PIX DIVIDIDO] Resposta de configurações:', configResult);

            if (configResult.configuracoes && Array.isArray(configResult.configuracoes)) {
                // Procurar pela configuração "comissao_peca" na lista
                const configComissao = configResult.configuracoes.find(c => c.chave === 'comissao_peca');
                if (configComissao && configComissao.valor) {
                    comissaoPeca = parseFloat(configComissao.valor);
                    console.log('[CARRINHO PIX DIVIDIDO] Comissão encontrada na config:', comissaoPeca);
                } else {
                    console.log('[CARRINHO PIX DIVIDIDO] Comissão não encontrada, usando padrão:', comissaoPeca);
                }
            }
        } catch (e) {
            console.warn('[CARRINHO PIX DIVIDIDO] Aviso ao buscar configuração, usando padrão:', e);
        }

        // 2. Calcular valor do PIX (comissão × quantidade de peças)
        const quantidadePecas = pecasCarroAtivo.reduce((sum, peca) => sum + (peca.quantidade || 1), 0);
        const valorSemTaxa = comissaoPeca * quantidadePecas;
        const taxaValor = valorSemTaxa * 0.01;
        const valorPixTotal = valorSemTaxa + taxaValor;

        console.log('[CARRINHO PIX DIVIDIDO] Comissão por peça:', comissaoPeca);
        console.log('[CARRINHO PIX DIVIDIDO] Quantidade total:', quantidadePecas);
        console.log('[CARRINHO PIX DIVIDIDO] Valor sem taxa:', valorSemTaxa.toFixed(2));
        console.log('[CARRINHO PIX DIVIDIDO] Taxa Mercado Pago (1%):', taxaValor.toFixed(2));
        console.log('[CARRINHO PIX DIVIDIDO] Valor PIX (com taxa):', valorPixTotal.toFixed(2));

        // 3. Verificar saldo (para doricoins das peças)
        const equipe = equipeAtual;
        const totalPrecoPecas = pecasCarroAtivo.reduce((sum, peca) => sum + (peca.preco * (peca.quantidade || 1)), 0);

        if (equipe.doricoins < totalPrecoPecas) {
            mostrarToast(`Saldo insuficiente! Faltam ${formatarMoeda(totalPrecoPecas - equipe.doricoins)}`, 'error');
            return;
        }

        // 4. Descontar saldo (em doricoins, não em reais)
        equipe.doricoins -= totalPrecoPecas;
        const saldoElement = document.getElementById('saldoEquipe');
        if (saldoElement) {
            saldoElement.textContent = formatarMoeda(equipe.doricoins);
        }

        // 5. Preparar dados do PIX
        const transacaoId = 'compra_' + Date.now();

        console.log('[CARRINHO PIX DIVIDIDO] Gerando QR code...');

        // 6. Gerar PIX com valor correto (comissão, não preço das peças)
        const resposta = await fetch('/api/gerar-qr-pix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Equipe-ID': localStorage.getItem('equipe_id') },
            body: JSON.stringify({
                tipo: 'peca',
                item_id: transacaoId,
                carro_id: carroAtivo.id,
                valor_custom: valorPixTotal  // Valor em reais (comissão)
            })
        });

        const resultado = await resposta.json();

        if (!resultado.sucesso) {
            mostrarToast('Erro ao gerar QR Code: ' + resultado.erro, 'error');
            equipe.doricoins += totalPrecoPecas;
            if (saldoElement) {
                saldoElement.textContent = formatarMoeda(equipe.doricoins);
            }
            return;
        }

        console.log('[CARRINHO PIX DIVIDIDO] QR code gerado:', resultado.transacao_id);

        // 7. Armazenar dados da transação para uso posterior
        window.transacaoPixAtualDividido = resultado.transacao_id;
        window.pecasCarroPixDividido = pecasCarroAtivo;
        window.pecasArmazemPendente = window.pecasArmazem || [];
        window.carroAtivoDividido = carroAtivo.id;

        // 8. Mostrar modal PIX com Promise para garantir que está renderizado
        await new Promise((resolve) => {
            setTimeout(() => {
                const pixQrCode = document.getElementById('pixQrCode');
                const pixQrCodeContainer = document.getElementById('pixQrCodeContainer');
                const pixItemNome = document.getElementById('pixItemNome');
                const pixValorItem = document.getElementById('pixValorItem');
                const pixTaxaValor = document.getElementById('pixTaxaValor');
                const pixValorTotal = document.getElementById('pixValorTotal');
                const pixStatus = document.getElementById('pixStatus');

                if (!pixQrCode || !pixQrCodeContainer || !pixItemNome || !pixValorItem || !pixValorTotal || !pixStatus) {
                    console.error('[CARRINHO PIX DIVIDIDO] ❌ Elementos do modal PIX não encontrados!');
                    mostrarToast('Erro: Modal PIX não encontrado no HTML', 'error');
                    resolve();
                    return;
                }

                try {
                    // Usar os valores já calculados acima
                    pixQrCode.src = resultado.qr_code_url || resultado.qr_code;
                    pixQrCodeContainer.style.display = 'block';
                    pixItemNome.textContent = `Carro Ativo - ${pecasCarroAtivo.length} peça(s)`;
                    pixValorItem.textContent = valorSemTaxa.toFixed(2);  // Valor sem taxa
                    if (pixTaxaValor) {
                        pixTaxaValor.textContent = taxaValor.toFixed(2);  // Taxa separada
                    }
                    pixValorTotal.textContent = valorPixTotal.toFixed(2);  // Valor com taxa
                    pixStatus.innerHTML = '⏳ Aguardando confirmação do pagamento...';

                    console.log('[CARRINHO PIX DIVIDIDO] Elementos do modal atualizados com sucesso');
                    console.log('[CARRINHO PIX DIVIDIDO] Valor sem taxa:', valorSemTaxa.toFixed(2));
                    console.log('[CARRINHO PIX DIVIDIDO] Taxa:', taxaValor.toFixed(2));
                    console.log('[CARRINHO PIX DIVIDIDO] Valor com taxa:', valorPixTotal.toFixed(2));

                    // 9. Mostrar modal PIX
                    const pixModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('pixModal'));
                    pixModal.show();

                    console.log('[CARRINHO PIX DIVIDIDO] Iniciando polling com ID:', resultado.transacao_id);
                    iniciarPollingPixDividido(resultado.transacao_id);
                } catch (erro) {
                    console.error('[CARRINHO PIX DIVIDIDO] Erro ao atualizar elementos:', erro);
                    mostrarToast('Erro ao exibir modal: ' + erro.message, 'error');
                }

                resolve();
            }, 100);
        });

    } catch (erro) {
        console.error('[CARRINHO PIX DIVIDIDO] Erro ao gerar PIX:', erro);
        mostrarToast('Erro ao processar compra: ' + erro.message, 'error');
    }
}

function iniciarPollingPixDividido(transacaoId) {
    /**Inicia polling para verificar PIX com destino dividido*/
    let tentativas = 0;
    const maxTentativas = 120;  // 2 minutos

    const intervalo = setInterval(async () => {
        tentativas++;

        try {
            const resp = await fetch(`/api/transacao-pix/${transacaoId}`, {
                headers: obterHeaders()
            });

            if (!resp.ok) {
                console.warn(`[POLLING DIVIDIDO] Resposta ${resp.status}`);
                if (tentativas >= maxTentativas) {
                    clearInterval(intervalo);
                    mostrarToast('Timeout: a transação levou muito tempo', 'warning');
                }
                return;
            }

            const dados = await resp.json();
            console.log('[POLLING DIVIDIDO] Status:', dados.status);

            // Verificar se foi aprovada
            if (dados.status === 'aprovado' || dados.status === 'aprovada' || dados.status === 'confirmada' || dados.pago === true) {
                clearInterval(intervalo);
                console.log('[POLLING DIVIDIDO] ✅ Pagamento aprovado!');
                document.getElementById('pixStatus').innerHTML = '<div class="alert alert-success">✅ Pagamento confirmado! Processando seu carrinho...</div>';

                setTimeout(async () => {
                    try {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('pixModal'));
                        if (modal) {
                            modal.hide();
                        }
                    } catch (e) {
                        console.error('[POLLING DIVIDIDO] Erro ao fechar modal:', e);
                    }

                    // Processar peças do carro via PIX
                    const pecasCarroAtivo = window.pecasCarroPixDividido || [];
                    const carroId = window.carroAtivoDividido;

                    if (pecasCarroAtivo.length > 0) {
                        await processarPecasCarroDividido(pecasCarroAtivo, carroId);
                    }

                    // Processar peças do armazém (sem PIX)
                    const pecasArmazem = window.pecasArmazemPendente || [];
                    if (pecasArmazem.length > 0) {
                        await processarPecasArmazemDividido(pecasArmazem);
                    }

                    // Limpar carrinho
                    carrinho = [];
                    atualizarUICarrinho();

                    mostrarToast(`✅ Compra realizada! ${pecasCarroAtivo.length} peça(s) instalada(s) no carro e ${pecasArmazem.length} peça(s) no armazém`, 'success');
                }, 500);
            }
        } catch (erro) {
            console.error('[POLLING DIVIDIDO] Erro ao conferir:', erro);
        }
    }, 1000);  // Polling a cada 1 segundo
}

async function processarPecasCarroDividido(pecas, carroId) {
    console.log('[CARRINHO] Processando peças para carro:', pecas);
    console.log('[CARRINHO] PIX ID para registro:', window.transacaoPixAtualDividido);

    for (const peca of pecas) {
        try {
            const resposta = await fetch('/api/processar-compra-pix', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...obterHeaders()
                },
                body: JSON.stringify({
                    tipo: 'peca',
                    item_id: peca.id,
                    carro_id: carroId,
                    transacao_id: window.transacaoPixAtualDividido  // Passar PIX ID
                })
            });

            const resultado = await resposta.json();

            if (resultado.sucesso) {
                console.log('[CARRINHO] Peça instalada no carro:', peca.nome);
            } else {
                console.error('[CARRINHO] Erro ao instalar peça:', resultado.erro);
            }
        } catch (erro) {
            console.error('[CARRINHO] Erro ao processar peça:', erro);
        }
    }
}

async function enviarCarrinhoParaArmazemDividido() {
    /**Envia peças para armazém (sem PIX) - versão dividida*/
    const pecasArmazem = window.pecasArmazem || [];

    if (pecasArmazem.length === 0) {
        mostrarToast('Nenhuma peça para o armazém!', 'error');
        return;
    }

    console.log('[CARRINHO ARMAZÉM DIVIDIDO] Processando peças:', pecasArmazem);

    for (const peca of pecasArmazem) {
        try {
            const resposta = await fetch('/api/comprar-peca-armazem', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...obterHeaders()
                },
                body: JSON.stringify({ peca_id: peca.id })
            });

            const resultado = await resposta.json();

            if (resultado.sucesso) {
                console.log('[CARRINHO ARMAZÉM DIVIDIDO] Peça adicionada ao armazém:', peca.nome);
            } else {
                console.error('[CARRINHO ARMAZÉM DIVIDIDO] Erro:', resultado.erro);
            }
        } catch (erro) {
            console.error('[CARRINHO ARMAZÉM DIVIDIDO] Erro ao processar:', erro);
        }
    }

    // Limpar carrinho
    carrinho = [];
    atualizarUICarrinho();

    mostrarToast(`✅ ${pecasArmazem.length} peça(s) adicionada(s) ao armazém!`, 'success');
}

async function processarPecasArmazemDividido(pecas) {
    console.log('[CARRINHO] Processando peças para armazém:', pecas);

    for (const peca of pecas) {
        try {
            const resposta = await fetch('/api/comprar-peca-armazem', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...obterHeaders()
                },
                body: JSON.stringify({ peca_id: peca.id })
            });

            const resultado = await resposta.json();

            if (resultado.sucesso) {
                console.log('[CARRINHO] Peça adicionada ao armazém:', peca.nome);
            } else {
                console.error('[CARRINHO] Erro ao adicionar ao armazém:', resultado.erro);
            }
        } catch (erro) {
            console.error('[CARRINHO] Erro ao processar:', erro);
        }
    }
}
async function confirmarCompraCarrinho() {
    // Esta função foi substituída pela modal. Mantida aqui para compatibilidade.
    abrirModalDestino();
}

async function gerarPixCarroAtivo() {
    /**Gera PIX para enviar peças do carrinho para o carro ativo*/
    if (carrinho.length === 0) {
        mostrarToast('Carrinho vazio! Adicione peças antes de continuar', 'error');
        return;
    }

    console.log('[CARRINHO PIX CARRO ATIVO] Confirmando compra de carrinho:');
    console.log('[CARRINHO PIX CARRO ATIVO] Peças no carrinho:', carrinho);

    try {
        // Buscar configuração de comissão
        const respConfig = await fetch('/api/admin/configuracoes', {
            headers: obterHeaders()
        });
        const configResult = await respConfig.json();

        let comissaoPeca = 10;  // Padrão
        if (configResult.sucesso && configResult.configuracoes) {
            comissaoPeca = parseFloat(configResult.configuracoes.comissao_peca || '10');
        }

        // Calcular total: comissão × quantidade total de peças
        let quantidadeTotal = 0;
        carrinho.forEach(peca => {
            quantidadeTotal += peca.quantidade || 1;
        });

        let valorTotal = comissaoPeca * quantidadeTotal;

        // Adicionar taxa do Mercado Pago (1%)
        const taxaMercadoPago = valorTotal * 0.01;
        valorTotal += taxaMercadoPago;

        console.log('[CARRINHO PIX CARRO ATIVO] Comissão por peça:', comissaoPeca);
        console.log('[CARRINHO PIX CARRO ATIVO] Quantidade total:', quantidadeTotal);
        console.log('[CARRINHO PIX CARRO ATIVO] Taxa Mercado Pago (1%):', taxaMercadoPago.toFixed(2));
        console.log('[CARRINHO PIX CARRO ATIVO] Valor total (com taxa):', valorTotal.toFixed(2));

        try {
            // Gerar uma única transação PIX com o valor total
            const resp = await fetch('/api/gerar-qr-pix', {
                method: 'POST',
                headers: obterHeaders(),
                body: JSON.stringify({
                    tipo: 'peca',
                    item_id: 'carrinho_' + Date.now(),  // ID único para o carrinho
                    carro_id: null,
                    valor_custom: valorTotal  // Valor customizado baseado na comissão
                })
            });

            const resultado = await resp.json();

            console.log('[CARRINHO PIX CARRO ATIVO] Resposta do servidor:', resultado);

            if (resultado.sucesso) {
                console.log('[CARRINHO PIX CARRO ATIVO] Transação criada com ID:', resultado.transacao_id);

                window.carrinhoPixAtual = {
                    transacao_id: resultado.transacao_id,
                    carrinho: carrinho,
                    valor_total: valorTotal
                };

                mostrarPixModalCarrinho(resultado);
            } else {
                mostrarToast('Erro: ' + (resultado.erro || 'Erro desconhecido'), 'error');
            }
        } catch (e) {
            mostrarToast('Erro ao gerar QR Code: ' + e.message, 'error');
        }
    } catch (e) {
        mostrarToast('Erro ao buscar configurações: ' + e.message, 'error');
    }
}

async function enviarCarrinhoParaArmazem() {
    /**Envia peças do carrinho direto para o armazém sem gerar PIX*/
    if (carrinho.length === 0) {
        mostrarToast('Carrinho vazio! Adicione peças antes de continuar', 'error');
        return;
    }

    console.log('[CARRINHO ARMAZÉM] Enviando peças do carrinho para armazém:');
    console.log('[CARRINHO ARMAZÉM] Peças:', carrinho);

    // Guardar saldo anterior
    const saldoAnterior = equipeAtual.saldo || 0;
    let totalEnviado = 0;
    let valorGastoTotal = 0;
    let erros = [];

    try {
        // Enviar cada peça para o armazém
        for (let peca of carrinho) {
            for (let i = 0; i < peca.quantidade; i++) {
                try {
                    const resp = await fetch('/api/comprar-peca-armazem', {
                        method: 'POST',
                        headers: obterHeaders(),
                        body: JSON.stringify({
                            peca_id: peca.id
                        })
                    });

                    const resultado = await resp.json();

                    if (resultado.sucesso) {
                        console.log(`[CARRINHO ARMAZÉM] ✅ Peça ${peca.nome} (${i + 1}/${peca.quantidade}) enviada para armazém`);
                        totalEnviado++;
                        valorGastoTotal += peca.preco;
                    } else {
                        console.warn(`[CARRINHO ARMAZÉM] ❌ Erro ao enviar ${peca.nome}:`, resultado.erro);
                        erros.push(`${peca.nome}: ${resultado.erro}`);
                    }
                } catch (e) {
                    console.error(`[CARRINHO ARMAZÉM] Erro ao enviar peça:`, e);
                    erros.push(`${peca.nome}: ${e.message}`);
                }
            }
        }

        // Mostrar resultado
        if (totalEnviado > 0) {
            mostrarToast(`✅ ${totalEnviado} peça(s) enviada(s) para o armazém!`, 'success');

            // Fechar painel flutuante
            document.getElementById('carrinhoPanel').style.display = 'none';
            document.getElementById('carrinhoFlutuante').style.display = 'none';

            limparCarrinho();

            // Atualizar painel flutuante
            if (typeof atualizarPainelCarrinho === 'function') {
                atualizarPainelCarrinho();
            }

            // Recarregar detalhes da equipe e garagem
            if (typeof carregarDetalhesEquipe === 'function') {
                await carregarDetalhesEquipe();
            }
            if (typeof carregarGaragem === 'function') {
                await carregarGaragem();
            }

            // Mostrar modal de compra finalizada
            setTimeout(() => {
                mostrarModalCompraFinalizada(saldoAnterior, valorGastoTotal);
            }, 500);
        }

        // Mostrar erros se houver
        if (erros.length > 0) {
            console.warn('[CARRINHO ARMAZÉM] Erros encontrados:', erros);
            mostrarToast(`⚠️ ${totalEnviado} peça(s) enviada(s), mas ${erros.length} com erro`, 'warning');
        }
    } catch (e) {
        console.error('[CARRINHO ARMAZÉM] Erro geral:', e);
        mostrarToast('Erro ao enviar para armazém: ' + e.message, 'error');
    }
}

function mostrarPixModalCarrinho(dados) {
    /**Mostra o modal do PIX para o carrinho*/
    const modal = document.getElementById('pixModal');

    // Validar dados
    if (!dados || !dados.transacao_id) {
        console.error('[PIX MODAL CARRINHO] Dados inválidos:', dados);
        mostrarToast('Erro: dados da transação inválidos', 'error');
        return;
    }

    console.log('[PIX MODAL CARRINHO] Mostrando modal com transacao_id:', dados.transacao_id);

    // Usar nome customizado se fornecido, senão usar padrão "Carrinho"
    const nomeItem = dados.item_nome || `Carrinho (${carrinho.length} peça(s))`;
    document.getElementById('pixItemNome').textContent = nomeItem;
    document.getElementById('pixValorItem').textContent = (dados.valor_item || 0).toFixed(2);
    document.getElementById('pixTaxaValor').textContent = (dados.taxa || 0).toFixed(2);
    document.getElementById('pixValorTotal').textContent = (dados.valor_total || 0).toFixed(2);

    if (dados.qr_code_url) {
        document.getElementById('pixQrCode').src = dados.qr_code_url;
        document.getElementById('pixQrCodeContainer').style.display = 'block';
    }

    document.getElementById('pixStatus').innerHTML = '<div class="alert alert-info">⏳ Aguardando confirmação do pagamento...</div>';

    window.transacaoPixAtual = dados.transacao_id;

    bootstrap.Modal.getOrCreateInstance(modal).show();

    iniciarPollingPixCarrinho(dados.transacao_id);
}
function iniciarPollingPixCarrinho(transacaoId) {
    /**Inicia polling para verificar se PIX foi pago (carrinho)*/
    let tentativas = 0;
    const maxTentativas = 120;  // 2 minutos com polling a cada segundo

    const intervalo = setInterval(async () => {
        tentativas++;

        try {
            const resp = await fetch(`/api/transacao-pix/${transacaoId}`, {
                headers: obterHeaders()
            });

            if (!resp.ok) {
                console.warn(`[POLLING CARRINHO] Resposta ${resp.status} ao consultar transação`);
                if (tentativas >= maxTentativas) {
                    clearInterval(intervalo);
                    mostrarToast('Timeout: a transação levou muito tempo para confirmar', 'warning');
                }
                return;
            }

            const dados = await resp.json();
            console.log('[POLLING CARRINHO] Status da transação:', dados.status);

            // Verificar se foi aprovada (aceitar várias variações de status)
            if (dados.status === 'aprovado' || dados.status === 'aprovada' || dados.status === 'confirmada' || dados.pago === true) {
                clearInterval(intervalo);
                console.log('[POLLING CARRINHO] ✅ Pagamento aprovado!');
                document.getElementById('pixStatus').innerHTML = '<div class="alert alert-success">✅ Pagamento confirmado! Processando seu carrinho...</div>';

                // Guardar saldo anterior antes de limpar
                const saldoAnterior = equipeAtual?.saldo || 0;
                let valorGastoTotal = 0;
                carrinho.forEach(peca => {
                    valorGastoTotal += (peca.preco * (peca.quantidade || 1));
                });

                setTimeout(() => {
                    try {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('pixModal'));
                        if (modal) {
                            modal.hide();
                        }
                    } catch (e) {
                        console.error('[POLLING CARRINHO] Erro ao fechar modal:', e);
                    }

                    mostrarToast('✅ Carrinho processado com sucesso!', 'success');

                    // Fechar painel flutuante
                    document.getElementById('carrinhoPanel').style.display = 'none';
                    document.getElementById('carrinhoFlutuante').style.display = 'none';

                    limparCarrinho();
                    atualizarPainelCarrinho();

                    // Recarregar dados
                    if (typeof carregarDetalhesEquipe === 'function') {
                        carregarDetalhesEquipe();
                    }
                    if (typeof carregarGaragem === 'function') {
                        carregarGaragem();
                    }

                    // Mostrar modal de compra finalizada
                    setTimeout(() => {
                        mostrarModalCompraFinalizada(saldoAnterior, valorGastoTotal);
                    }, 500);
                }, 1500);
            } else if (tentativas >= maxTentativas) {
                // Timeout
                clearInterval(intervalo);
                mostrarToast('Timeout: a transação levou muito tempo para confirmar', 'warning');
            }
        } catch (e) {
            console.error('[POLLING CARRINHO] Erro ao consultar transação:', e);
            if (tentativas >= maxTentativas) {
                clearInterval(intervalo);
                mostrarToast('Erro ao verificar pagamento: ' + e.message, 'error');
            }
        }
    }, 1000);  // Polling a cada 1 segundo
}

// ====== PIX REGULARIZAÇÃO (ETAPA) ======
function mostrarPixModalRegularizacao(dados) {
    /**Mostra o modal do PIX para regularização de etapa*/
    const modal = document.getElementById('pixModal');

    // Validar dados
    if (!dados || !dados.transacao_id) {
        console.error('[PIX REGULARIZAÇÃO] Dados inválidos:', dados);
        mostrarToast('Erro: dados da transação inválidos', 'error');
        return;
    }

    console.log('[PIX REGULARIZAÇÃO] Mostrando modal com transacao_id:', dados.transacao_id);

    // Setar valores
    document.getElementById('pixItemNome').textContent = dados.item_nome || 'Regularização';
    document.getElementById('pixValorItem').textContent = (dados.valor_item || 0).toFixed(2);
    document.getElementById('pixTaxaValor').textContent = (dados.taxa || 0).toFixed(2);
    document.getElementById('pixValorTotal').textContent = (dados.valor_total || 0).toFixed(2);

    if (dados.qr_code_url) {
        document.getElementById('pixQrCode').src = dados.qr_code_url;
        document.getElementById('pixQrCodeContainer').style.display = 'block';
    }

    document.getElementById('pixStatus').innerHTML = '<div class="alert alert-info">⏳ Aguardando confirmação do pagamento...</div>';

    window.transacaoPixAtual = dados.transacao_id;
    window.tipo_transacao_atual = 'regularizacao';  // Marcar tipo de transação

    bootstrap.Modal.getOrCreateInstance(modal).show();

    iniciarPollingPixRegularizacao(dados.transacao_id, dados.equipe_id, dados.etapa_id);
}

function iniciarPollingPixRegularizacao(transacaoId, equipeId, etapaId) {
    /**Inicia polling para verificar se PIX foi pago (regularização)*/
    let tentativas = 0;
    const maxTentativas = 120;  // 2 minutos com polling a cada segundo

    const intervalo = setInterval(async () => {
        tentativas++;

        try {
            const resp = await fetch(`/api/transacao-pix/${transacaoId}`, {
                headers: obterHeaders()
            });

            if (!resp.ok) {
                console.warn(`[POLLING REGULARIZAÇÃO] Resposta ${resp.status} ao consultar transação`);
                if (tentativas >= maxTentativas) {
                    clearInterval(intervalo);
                    mostrarToast('Timeout: a transação levou muito tempo para confirmar', 'warning');
                }
                return;
            }

            const dados = await resp.json();
            console.log('[POLLING REGULARIZAÇÃO] Dados recebidos:', dados);

            // Verificar status - pode estar em 'transacao' ou direto
            const status = dados.transacao?.status || dados.status;
            const pago = dados.transacao?.pago || dados.pago;
            
            console.log('[POLLING REGULARIZAÇÃO] Status:', status, 'Pago:', pago);

            // Verificar se foi aprovada (aceitar várias variações de status)
            if (status === 'aprovado' || status === 'aprovada' || status === 'confirmada' || pago === true) {
                clearInterval(intervalo);
                console.log('[POLLING REGULARIZAÇÃO] ✅ Pagamento aprovado!');
                document.getElementById('pixStatus').innerHTML = '<div class="alert alert-success">✅ Pagamento confirmado! Regularização processada...</div>';

                setTimeout(() => {
                    try {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('pixModal'));
                        if (modal) {
                            modal.hide();
                        }
                    } catch (e) {
                        console.error('[POLLING REGULARIZAÇÃO] Erro ao fechar modal:', e);
                    }

                    mostrarToast('✅ Regularização de saldo confirmada!', 'success');

                    // Recarregar apenas a lista de etapas
                    if (typeof carregarEtapasEquipe === 'function') {
                        carregarEtapasEquipe();
                    }

                }, 1500);
            } else if (tentativas >= maxTentativas) {
                // Timeout
                clearInterval(intervalo);
                mostrarToast('Timeout: a transação levou muito tempo para confirmar', 'warning');
            }
        } catch (e) {
            console.error('[POLLING REGULARIZAÇÃO] Erro ao consultar transação:', e);
            if (tentativas >= maxTentativas) {
                clearInterval(intervalo);
                mostrarToast('Erro ao verificar pagamento: ' + e.message, 'error');
            }
        }
    }, 1000);  // Polling a cada 1 segundo
}

// ====== PIX INSCRIÇÃO (sem débito prévio) ======
function mostrarPixModalInscricao(dados) {
    /**Mostra o modal do PIX para inscrição em etapa (sem débito)*/
    const modal = document.getElementById('pixModal');

    // Validar dados
    if (!dados || !dados.transacao_id) {
        console.error('[PIX INSCRIÇÃO] Dados inválidos:', dados);
        mostrarToast('Erro: dados da transação inválidos', 'error');
        return;
    }

    console.log('[PIX INSCRIÇÃO] Mostrando modal com transacao_id:', dados.transacao_id);

    // Setar valores
    document.getElementById('pixItemNome').textContent = dados.item_nome || 'Inscrição';
    document.getElementById('pixValorItem').textContent = (dados.valor_item || 0).toFixed(2);
    document.getElementById('pixTaxaValor').textContent = (dados.taxa || 0).toFixed(2);
    document.getElementById('pixValorTotal').textContent = (dados.valor_total || 0).toFixed(2);

    if (dados.qr_code_url) {
        document.getElementById('pixQrCode').src = dados.qr_code_url;
        document.getElementById('pixQrCodeContainer').style.display = 'block';
    }

    document.getElementById('pixStatus').innerHTML = '<div class="alert alert-info">⏳ Aguardando confirmação do pagamento...</div>';

    window.transacaoPixAtual = dados.transacao_id;
    window.tipo_transacao_atual = 'inscricao';  // Marcar tipo de transação

    bootstrap.Modal.getOrCreateInstance(modal).show();

    iniciarPollingPixInscricao(dados.transacao_id, dados.equipe_id, dados.etapa_id);
}

function iniciarPollingPixInscricao(transacaoId, equipeId, etapaId) {
    /**Inicia polling para verificar se PIX foi pago (inscrição)*/
    let tentativas = 0;
    const maxTentativas = 120;  // 2 minutos com polling a cada segundo

    const intervalo = setInterval(async () => {
        tentativas++;

        try {
            const resp = await fetch(`/api/transacao-pix/${transacaoId}`, {
                headers: obterHeaders()
            });

            if (!resp.ok) {
                console.warn(`[POLLING INSCRIÇÃO] Resposta ${resp.status} ao consultar transação`);
                if (tentativas >= maxTentativas) {
                    clearInterval(intervalo);
                    mostrarToast('Timeout: a transação levou muito tempo para confirmar', 'warning');
                }
                return;
            }

            const dados = await resp.json();
            console.log('[POLLING INSCRIÇÃO] Dados recebidos:', dados);

            // Verificar status - pode estar em 'transacao' ou direto
            const status = dados.transacao?.status || dados.status;
            const pago = dados.transacao?.pago || dados.pago;
            
            console.log('[POLLING INSCRIÇÃO] Status:', status, 'Pago:', pago);

            // Verificar se foi aprovada (aceitar várias variações de status)
            if (status === 'aprovado' || status === 'aprovada' || status === 'confirmada' || pago === true) {
                clearInterval(intervalo);
                console.log('[POLLING INSCRIÇÃO] ✅ Pagamento aprovado!');
                document.getElementById('pixStatus').innerHTML = '<div class="alert alert-success">✅ Pagamento confirmado! Inscrição processada...</div>';

                setTimeout(() => {
                    try {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('pixModal'));
                        if (modal) {
                            modal.hide();
                        }
                    } catch (e) {
                        console.error('[POLLING INSCRIÇÃO] Erro ao fechar modal:', e);
                    }

                    mostrarToast('✅ Inscrição confirmada!', 'success');

                    // Recarregar apenas a lista de etapas
                    if (typeof carregarEtapasEquipe === 'function') {
                        carregarEtapasEquipe();
                    }
                }, 1500);
            } else if (tentativas >= maxTentativas) {
                // Timeout
                clearInterval(intervalo);
                mostrarToast('Timeout: a transação levou muito tempo para confirmar', 'warning');
            }
        } catch (e) {
            console.error('[POLLING INSCRIÇÃO] Erro ao consultar transação:', e);
            if (tentativas >= maxTentativas) {
                clearInterval(intervalo);
                mostrarToast('Erro ao verificar pagamento: ' + e.message, 'error');
            }
        }
    }, 1000);  // Polling a cada 1 segundo
}

// ====== APELIDO PARA CARRO ======
let apelidoEmEdicao = null;  // Armazenar dados da edição

function editarApelidoCarro(carroId, apelidoAtual, elemento) {
    // Armazenar os dados para uso na confirmação
    apelidoEmEdicao = {
        carroId: carroId,
        apelidoAtual: apelidoAtual || ''
    };

    // Preencher o input com o apelido atual
    const inputApelido = document.getElementById('inputApelido');
    inputApelido.value = apelidoAtual || '';
    inputApelido.focus();

    // Abrir modal
    const modal = new bootstrap.Modal(document.getElementById('editarApelidoModal'));
    modal.show();
}

async function enviarImagemCarro(carroId, fileInput) {
    const file = fileInput && fileInput.files && fileInput.files[0];
    if (!file || !file.type.startsWith('image/')) {
        mostrarToast('Selecione uma imagem (jpg, png, etc.)', 'warning');
        return;
    }
    const formData = new FormData();
    formData.append('imagem', file);
    const headers = {};
    const equipeId = typeof obterEquipeIdDaSession === 'function' ? obterEquipeIdDaSession() : null;
    if (equipeId) headers['X-Equipe-ID'] = equipeId;
    try {
        const resp = await fetch(`/api/carro/${carroId}/imagem`, {
            method: 'POST',
            body: formData,
            credentials: 'include',
            headers
        });
        const data = await resp.json().catch(() => ({}));
        if (resp.ok && data.sucesso) {
            mostrarToast('✅ Imagem do carro atualizada!', 'success');
            if (typeof carregarGaragem === 'function') setTimeout(carregarGaragem, 300);
        } else {
            mostrarToast('❌ ' + (data.erro || 'Erro ao enviar imagem'), 'error');
        }
    } catch (e) {
        mostrarToast('❌ Erro ao enviar imagem', 'error');
    }
    fileInput.value = '';
}

function confirmarEditarApelido() {
    if (!apelidoEmEdicao) return;

    const inputApelido = document.getElementById('inputApelido');
    const novoApelido = inputApelido.value.trim();

    // Fechar modal
    bootstrap.Modal.getInstance(document.getElementById('editarApelidoModal')).hide();

    // Enviar para backend
    fetch(`/api/carro/${apelidoEmEdicao.carroId}/apelido`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ apelido: novoApelido })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.sucesso) {
                mostrarToast('✅ Apelido atualizado com sucesso!', 'success');
                // Recarregar garagem após 500ms para permitir backend processar
                setTimeout(() => {
                    if (typeof carregarGaragem === 'function') {
                        carregarGaragem();
                    }
                }, 500);
            } else {
                mostrarToast('❌ Erro ao atualizar apelido: ' + (data.erro || 'Desconhecido'), 'error');
            }
        })
        .catch(error => {
            console.error('Erro ao salvar apelido:', error);
            mostrarToast('❌ Erro ao salvar apelido: ' + error.message, 'error');
        });
}

// ====== FAZER RETÍFICA (GARAGEM) – vida da peça para 100% ======
async function recuperarPecaVida(pecaId, custoRetifica) {
    const custo = Number(custoRetifica) || 0;
    if (custo <= 0) {
        mostrarToast('Custo de retífica não definido', 'error');
        return;
    }
    if (!confirm(`Fazer retífica: colocar vida da peça em 100%?\n\nCusto: ${custo.toFixed(2)} doricoins`)) return;
    try {
        const resp = await fetch('/api/garagem/recuperar-peca', {
            method: 'POST',
            headers: { ...obterHeaders(), 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ peca_id: pecaId })
        });
        const data = await resp.json();
        if (resp.ok && data.sucesso) {
            mostrarToast('Retífica feita: peça em 100%!', 'success');
            if (typeof carregarGaragem === 'function') carregarGaragem();
        } else {
            mostrarToast(data.erro || 'Erro ao fazer retífica', 'error');
        }
    } catch (e) {
        console.error('Erro:', e);
        mostrarToast('Erro ao fazer retífica', 'error');
    }
}

// ====== REMOVER PEÇA DO CARRO ======
let pecaEmRemocao = null;

async function abrirModalRemoverPeca(carroId, tipoPeca, nomePeca) {
    pecaEmRemocao = { carroId, tipoPeca, nomePeca };

    const btnConfirmar = document.getElementById('btnConfirmarRemoverPeca');
    if (btnConfirmar) {
        btnConfirmar.disabled = false;
        btnConfirmar.innerHTML = 'Retirar Peça';
    }

    document.getElementById('nomePecaRemover').textContent = nomePeca;
    document.getElementById('destinoArmazem').checked = true;
    document.getElementById('selectorCarroDest').style.display = 'none';
    document.getElementById('alertaCustoOutroCarro').style.display = 'none';

    try {
        const respConfig = await fetch('/api/admin/configuracoes', {
            headers: obterHeaders()
        });
        const configResult = await respConfig.json();
        let valorInstalacao = 0;
        if (configResult.configuracoes && Array.isArray(configResult.configuracoes)) {
            const config = configResult.configuracoes.find(c => c.chave === 'preco_instalacao_warehouse');
            if (config) {
                valorInstalacao = parseFloat(config.valor || '0');
            }
        }
        document.getElementById('valorInstalacao').textContent = formatarMoeda(valorInstalacao);
    } catch (e) {
        console.error('Erro ao buscar configuração:', e);
        document.getElementById('valorInstalacao').textContent = 'Erro ao carregar valor';
    }

    try {
        const equipeId = obterEquipeIdDaSession();
        const respGaragem = await fetch(`/api/garagem/${equipeId}`, {
            headers: obterHeaders()
        });
        const garagem = await respGaragem.json();
        
        // Buscar compatibilidade da peça
        let compatibilidades = [];
        console.log(`[MODAL REMOVER] Procurando carro origem com ID: ${carroId}, tipoPeca: ${tipoPeca}`);
        console.log(`[MODAL REMOVER] Carros disponíveis:`, garagem.carros?.map(c => ({ id: c.id, marca: c.marca })));
        
        if (garagem.carros && Array.isArray(garagem.carros)) {
            // Encontrar o carro origem
            const carroOrigem = garagem.carros.find(c => String(c.id) === String(carroId));
            console.log(`[MODAL REMOVER] Carro origem encontrado:`, carroOrigem);
            
            if (carroOrigem && carroOrigem.pecas && Array.isArray(carroOrigem.pecas)) {
                console.log(`[MODAL REMOVER] Peças do carro origem:`, carroOrigem.pecas);
                // Encontrar a peça específica
                const pecaEspecifica = carroOrigem.pecas.find(p => p.tipo === tipoPeca);
                console.log(`[MODAL REMOVER] Peça específica encontrada:`, pecaEspecifica);
                
                if (pecaEspecifica) {
                    // Se não tem compatibilidades ou é vazio, é universal
                    if (Array.isArray(pecaEspecifica.compatibilidades)) {
                        compatibilidades = pecaEspecifica.compatibilidades;
                    }
                }
            }
        }
        
        const ehUniversal = compatibilidades.length === 0;
        console.log(`[COMPATIBILIDADE] Peça ${nomePeca}: universal=${ehUniversal}, compatíveis=[${compatibilidades.join(',')}]`);
        
        // Converter para inteiros para comparação
        const compatibilidadesInt = compatibilidades.map(c => parseInt(c));
        
        const selectCarroDest = document.getElementById('carroDestSelect');
        selectCarroDest.innerHTML = '<option value="">-- Selecione um carro --</option>';

        let opcoesAdicionadas = 0;
        if (garagem.carros && Array.isArray(garagem.carros)) {
            garagem.carros.forEach(carro => {
                console.log(`[FILTRO] Analisando carro ${carro.marca} ${carro.modelo} (ID: ${carro.id})`);
                
                // Comparar como strings para evitar problemas de tipo
                if (String(carro.id) === String(carroId)) {
                    console.log(`[FILTRO] Carro é o origem, skip`);
                    return;
                }
                
                // Verificar se carro já tem peça deste tipo (vai ser substituída)
                const temPecaDoTipo = carro.pecas && carro.pecas.some(p => p.tipo === tipoPeca);
                const aviso = temPecaDoTipo ? ' (substituirá peça existente)' : '';
                console.log(`[FILTRO] Carro tem peça tipo ${tipoPeca}? ${temPecaDoTipo}, aviso: "${aviso}"`);
                
                // Verificar compatibilidade
                const carroIdInt = parseInt(carro.id);
                const ehCompativel = ehUniversal || compatibilidadesInt.includes(carroIdInt);
                console.log(`[FILTRO] Compatibilidade: universal=${ehUniversal}, compatível=${ehCompativel}`);
                
                const nomeCarro = `${carro.marca} ${carro.modelo} ${carro.apelido ? '(' + carro.apelido + ')' : ''}`;
                const option = document.createElement('option');
                option.value = carro.id;
                option.textContent = ehCompativel ? nomeCarro + aviso : nomeCarro + ' (Incompatível)';
                option.disabled = !ehCompativel;
                option.style.opacity = ehCompativel ? '1' : '0.5';
                option.style.cursor = ehCompativel ? 'pointer' : 'not-allowed';
                selectCarroDest.appendChild(option);
                opcoesAdicionadas++;
            });
        }
        console.log(`[FILTRO] Total de opções adicionadas: ${opcoesAdicionadas}`);
    } catch (e) {
        console.error('Erro ao buscar carros:', e);
    }

    document.querySelectorAll('input[name="destino"]').forEach(radio => {
        radio.onchange = function () {
            const selectorDiv = document.getElementById('selectorCarroDest');
            const alertaCusto = document.getElementById('alertaCustoOutroCarro');
            if (this.value === 'carro') {
                selectorDiv.style.display = 'block';
                alertaCusto.style.display = 'block';
            } else {
                selectorDiv.style.display = 'none';
                alertaCusto.style.display = 'none';
            }
        };
    });

    const modal = new bootstrap.Modal(document.getElementById('removerPecaModal'));
    modal.show();
}

function confirmarRemoverPeca() {
    if (!pecaEmRemocao) return;

    const btnConfirmar = document.getElementById('btnConfirmarRemoverPeca');
    if (btnConfirmar && btnConfirmar.disabled) return; // já enviou, evita duplo clique

    // Obter destino escolhido
    const destino = document.querySelector('input[name="destino"]:checked').value;
    const { carroId, tipoPeca } = pecaEmRemocao;

    let novoCarroId = null;

    if (destino === 'carro') {
        novoCarroId = document.getElementById('carroDestSelect').value;
        if (!novoCarroId) {
            mostrarToast('❌ Por favor, selecione um carro de destino', 'error');
            return;
        }
    }

    // Desabilitar botão e mostrar "Processando..." para evitar enviar várias vezes
    if (btnConfirmar) {
        btnConfirmar.disabled = true;
        btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
    }

    fetch(`/api/remover-peca-carro`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...obterHeaders()
        },
        body: JSON.stringify({
            carro_id: carroId,
            tipo_peca: tipoPeca,
            novo_carro_id: novoCarroId
        })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            bootstrap.Modal.getInstance(document.getElementById('removerPecaModal')).hide();
            pecaEmRemocao = null;
            if (data.sucesso) {
                const destinyText = novoCarroId ? 'outro carro' : 'armazém';
                mostrarToast(`✅ Peça movida para ${destinyText} com sucesso!`, 'success');
                if (typeof carregarGaragem === 'function') {
                    carregarGaragem();
                }
            } else {
                mostrarToast('❌ Erro ao mover peça: ' + (data.erro || 'Desconhecido'), 'error');
            }
        })
        .catch(error => {
            console.error('Erro ao mover peça:', error);
            mostrarToast('❌ Erro ao mover peça: ' + error.message, 'error');
            const btn = document.getElementById('btnConfirmarRemoverPeca');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Retirar Peça';
            }
        });
}

// ==================== ETAPAS / TEMPORADA ====================

async function carregarProximaEtapa() {
    try {
        const equipeId = obterEquipeIdDaSession();
        if (!equipeId) return;

        // Obter série da equipe
        const respEquipe = await fetch(`/api/equipes/${equipeId}`, {
            headers: obterHeaders()
        });

        if (!respEquipe.ok) return;

        const equipeData = await respEquipe.json();
        const serie = equipeData.serie;

        if (!serie) {
            console.log('[ETAPA] Equipe não tem série definida');
            return;
        }

        // Obter próxima etapa
        const resp = await fetch(`/api/proxima-etapa/${serie}`);

        if (!resp.ok) {
            console.log('[ETAPA] Nenhuma etapa encontrada');
            return;
        }

        const etapa = await resp.json();

        if (!etapa.id) return;

        // Mostrar card de próxima etapa
        const card = document.getElementById('proximaEtapaCard');
        if (card) {
            card.style.display = 'block';
            document.getElementById('proximaEtapaNome').textContent = etapa.nome;
            document.getElementById('proximaEtapaSerie').textContent = etapa.serie;
            document.getElementById('proximaEtapaDescricao').textContent = etapa.descricao || '-';
            
            // Formatar data e hora
            const dataHora = new Date(`${etapa.data_etapa}T${etapa.hora_etapa}`);
            document.getElementById('proximaEtapaData').textContent = 
                dataHora.toLocaleDateString('pt-BR') + ' às ' + dataHora.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});

            // Mostrar botão de inscrição se tem carro ativo
            const btnInscrever = document.getElementById('btnInscreverEtapa');
            if (btnInscrever && window.garagemAtual && window.garagemAtual.carroAtivo) {
                btnInscrever.style.display = 'inline-block';
                btnInscrever.dataset.etapaId = etapa.id;
                btnInscrever.dataset.carroId = window.garagemAtual.carroAtivo.id;
            }
        }

        // Armazenar etapa atual
        window.proximaEtapa = etapa;
    } catch (e) {
        console.error('[ETAPA] Erro ao carregar próxima etapa:', e);
    }
}

async function inscreverEtapa() {
    try {
        const equipeId = obterEquipeIdDaSession();
        if (!equipeId) {
            mostrarToast('Erro: equipe não identificada', 'error');
            return;
        }

        const etapa = window.proximaEtapa;
        const carro = window.garagemAtual?.carroAtivo;

        if (!etapa || !carro) {
            mostrarToast('Erro: dados incompletos', 'error');
            return;
        }

        // Validar peças
        const respValidacao = await fetch('/api/validar-pecas-etapa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                carro_id: carro.id,
                equipe_id: equipeId
            })
        });

        const validacao = await respValidacao.json();

        if (!validacao.valido) {
            const pecasTexto = validacao.pecas_faltando.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(', ');
            mostrarToast(`❌ Peças faltando: ${pecasTexto}`, 'error');
            
            // Mostrar modal com peças faltando
            const modal = new bootstrap.Modal(document.getElementById('modalPecasFaltando') || criarModalPecasFaltando());
            modal.show();
            return;
        }

        // Inscrever na etapa
        const respInscricao = await fetch('/api/inscrever-etapa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                etapa_id: etapa.id,
                equipe_id: equipeId,
                carro_id: carro.id
            })
        });

        const resultado = await respInscricao.json();

        if (resultado.sucesso) {
            mostrarToast('✅ Inscrição confirmada na etapa!', 'success');
            document.getElementById('btnInscreverEtapa').style.display = 'none';
        } else {
            mostrarToast('❌ Erro: ' + (resultado.erro || 'Desconhecido'), 'error');
        }
    } catch (e) {
        console.error('[INSCREVER ETAPA] Erro:', e);
        mostrarToast('Erro ao inscrever na etapa: ' + e.message, 'error');
    }
}

function criarModalPecasFaltando() {
    const html = `
        <div class="modal fade" id="modalPecasFaltando" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title">⚠️ Peças Faltando</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Seu carro não tem todas as peças necessárias para participar da etapa:</p>
                        <ul id="listaPecasFaltando" class="list-group mt-2">
                            <!-- Preenchido dinamicamente -->
                        </ul>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        <button type="button" class="btn btn-primary" onclick="irParaArmazem()">Comprar Peças</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    const container = document.querySelector('.container') || document.body;
    const div = document.createElement('div');
    div.innerHTML = html;
    container.appendChild(div.firstElementChild);
    return document.getElementById('modalPecasFaltando');
}

function irParaArmazem() {
    // Fechar modal
    bootstrap.Modal.getInstance(document.getElementById('modalPecasFaltando')).hide();
    // Ir para aba de loja
    const abaLoja = document.querySelector('a[href="#loja-tab"]');
    if (abaLoja) {
        abaLoja.click();
    }
}

// ==================== ADMIN: CAMPEONATOS ====================

async function criarCampeonato() {
    const nome = document.getElementById('campeonatoNome').value.trim();
    const descricao = document.getElementById('campeonatoDescricao').value.trim();
    const serie = document.getElementById('campeonatoSerie').value;
    const numeroEtapas = parseInt(document.getElementById('campeonatoNumeroEtapas').value) || 5;

    if (!nome || !serie) {
        mostrarToast('Nome e série são obrigatórios', 'error');
        return;
    }

    try {
        const resp = await fetch('/api/admin/criar-campeonato', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                nome,
                descricao,
                serie,
                numero_etapas: numeroEtapas
            })
        });

        const resultado = await resp.json();

        if (resultado.sucesso) {
            mostrarToast(`✅ Campeonato "${nome}" criado com sucesso!`, 'success');
            document.getElementById('campeonatoNome').value = '';
            document.getElementById('campeonatoDescricao').value = '';
            document.getElementById('campeonatoSerie').value = '';
            document.getElementById('campeonatoNumeroEtapas').value = '5';
            
            // Recarregar listas
            carregarCampeonatos();
            carregarEtapasCadastro();
        } else {
            mostrarToast('❌ Erro: ' + (resultado.erro || 'Desconhecido'), 'error');
        }
    } catch (e) {
        console.error('[CRIAR CAMPEONATO] Erro:', e);
        mostrarToast('Erro ao criar campeonato: ' + e.message, 'error');
    }
}

async function carregarCampeonatos() {
    try {
        const resp = await fetch('/api/admin/listar-campeonatos', {
            headers: obterHeaders()
        });

        const data = await resp.json();
        const campeonatos = (data && data.campeonatos) ? data.campeonatos : (Array.isArray(data) ? data : []);

        // Preencher dropdown de seleção
        const select = document.getElementById('etapaCampeonato');
        const valorSelecionado = select.value;

        select.innerHTML = '<option value="">Selecione um campeonato...</option>';

        campeonatos.forEach(c => {
            const option = document.createElement('option');
            option.value = c.id;
            option.textContent = `${c.nome} (Série ${c.serie}) - ${c.numero_etapas} etapas`;
            select.appendChild(option);
        });

        if (valorSelecionado) select.value = valorSelecionado;

        // Preencher lista de campeonatos
        const lista = document.getElementById('listaCampeonatos');
        if (lista) {
            if (campeonatos.length === 0) {
                lista.innerHTML = '<p class="text-muted">Nenhum campeonato criado</p>';
            } else {
                lista.innerHTML = campeonatos.map(c => `
                    <div class="p-2 mb-2 border rounded">
                        <strong>${c.nome}</strong> <span class="badge bg-primary">Série ${c.serie}</span>
                        <br>
                        <small class="text-muted">${c.numero_etapas} etapas</small>
                        <button class="btn btn-sm btn-danger float-end" onclick="deletarCampeonato('${c.id}')">🗑️</button>
                    </div>
                `).join('');
            }
        }
    } catch (e) {
        console.error('[CARREGAR CAMPEONATOS] Erro:', e);
    }
}

async function deletarCampeonato(campeonatoId) {
    if (!confirm('Tem certeza? Isso vai deletar todas as etapas associadas.')) return;

    try {
        const resp = await fetch('/api/admin/deletar-campeonato', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({ campeonato_id: campeonatoId })
        });

        const resultado = await resp.json();

        if (resultado.sucesso) {
            mostrarToast('✅ Campeonato deletado', 'success');
            carregarCampeonatos();
            carregarEtapasCadastro();
        } else {
            mostrarToast('❌ Erro ao deletar', 'error');
        }
    } catch (e) {
        console.error('[DELETAR CAMPEONATO] Erro:', e);
    }
}

function atualizarSerieEtapa() {
    const select = document.getElementById('etapaCampeonato');
    const campeonatoId = select.value;

    if (!campeonatoId) {
        document.getElementById('etapaSerie').value = '';
        return;
    }

    // Encontrar a série do campeonato selecionado
    const options = select.querySelectorAll('option');
    options.forEach(opt => {
        if (opt.value === campeonatoId && opt.textContent) {
            // Extrair série do texto "Nome (Série X) - N etapas"
            const match = opt.textContent.match(/Série ([AB])/);
            if (match) {
                document.getElementById('etapaSerie').value = match[1];
            }
        }
    });
}

async function cadastrarEtapa() {
    const campeonatoId = document.getElementById('etapaCampeonato').value;
    const numero = parseInt(document.getElementById('etapaNumero').value) || 1;
    const nome = document.getElementById('etapaNome').value.trim();
    const descricao = document.getElementById('etapaDescricao').value.trim();
    const data = document.getElementById('etapaData').value;
    const hora = document.getElementById('etapaHora').value;
    const serie = document.getElementById('etapaSerie').value;

    if (!campeonatoId || !data || !hora) {
        mostrarToast('Campeonato, data e hora são obrigatórios', 'error');
        return;
    }

    try {
        const resp = await fetch('/api/admin/cadastrar-etapa', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...obterHeaders()
            },
            body: JSON.stringify({
                campeonato_id: campeonatoId,
                numero,
                nome,
                descricao,
                data_etapa: data,
                hora_etapa: hora,
                serie
            })
        });

        const resultado = await resp.json();

        if (resultado.sucesso) {
            mostrarToast(`✅ Etapa "${nome}" criada com sucesso!`, 'success');
            document.getElementById('etapaNome').value = '';
            document.getElementById('etapaDescricao').value = '';
            document.getElementById('etapaData').value = '';
            document.getElementById('etapaHora').value = '10:00';
            document.getElementById('etapaNumero').value = '1';
            document.getElementById('etapaCampeonato').value = '';
            document.getElementById('etapaSerie').value = '';
            
            carregarEtapasCadastro();
        } else {
            mostrarToast('❌ Erro: ' + (resultado.erro || 'Desconhecido'), 'error');
        }
    } catch (e) {
        console.error('[CADASTRAR ETAPA] Erro:', e);
        mostrarToast('Erro ao cadastrar etapa: ' + e.message, 'error');
    }
}

async function carregarEtapasCadastro() {
    try {
        const resp = await fetch('/api/admin/listar-etapas', {
            headers: obterHeaders()
        });

        const etapas = await resp.json();

        const lista = document.getElementById('listaEtapasCadastro');
        if (!lista) return;

        // Verificar se é um array
        if (!Array.isArray(etapas)) {
            lista.innerHTML = '<p class="text-danger">Erro ao carregar etapas</p>';
            return;
        }

        if (etapas.length === 0) {
            lista.innerHTML = '<p class="text-muted">Nenhuma etapa cadastrada</p>';
        } else {
            lista.innerHTML = etapas.map(e => {
                const dataHora = new Date(`${e.data_etapa}T${e.hora_etapa}`);
                const dataStr = dataHora.toLocaleDateString('pt-BR');
                const horaStr = dataHora.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
                
                return `
                    <div class="p-2 mb-2 border rounded">
                        <strong>${e.nome || `Etapa ${e.numero}`}</strong> <span class="badge bg-info">Série ${e.serie}</span>
                        <br>
                        <small class="text-muted">📅 ${dataStr} às ${horaStr}</small>
                        <br>
                        <small class="text-muted">${e.descricao || '-'}</small>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        console.error('[CARREGAR ETAPAS] Erro:', e);
    }
}

// =================== ADMIN - ALOCAÇÃO DE PILOTOS (centralizado) ===================
// Funções usadas por `admin_alocar_pilotos.html` e pelo modal inline em `admin.html`

async function carregarEtapasParaAlocacao(selectId = 'selectEtapa', autoSelect = true) {
    try {
        const resp = await fetch('/api/admin/etapas');
        const data = await resp.json();
        const select = document.getElementById(selectId);
        if (!select) return;
        select.innerHTML = '<option value="">-- Selecione uma etapa --</option>';
        if (Array.isArray(data.etapas)) {
            data.etapas.forEach(etapa => {
                const option = document.createElement('option');
                option.value = etapa.id || etapa['id'];
                option.textContent = `Etapa ${etapa.numero || etapa['numero']} - ${etapa.nome || etapa['nome']}`;
                select.appendChild(option);
            });
            if (autoSelect && select.options.length > 1) select.selectedIndex = 1;
        }
    } catch (e) {
        console.error('[ALOCAÇÃO] Erro ao carregar etapas:', e);
    }
}

async function carregarPilotosDisponiveis(containerId = 'listaPilotosDisponiveis', excluirIds = [], etapaId = null) {
    // Implement a simple queue so concurrent calls don't abort each other.
    // If a call is in progress, store the latest requested args and schedule
    // a follow-up run after the current one finishes. This avoids lost
    // requests and the previous "re-entrada" aborts.
    if (!carregarPilotosDisponiveis._queue) {
        carregarPilotosDisponiveis._queue = { running: false, pending: null };
    }
    if (carregarPilotosDisponiveis._queue.running) {
        // Save the latest args and return; the function will be re-invoked
        // automatically after the running call completes.
        carregarPilotosDisponiveis._queue.pending = { containerId, excluirIds, etapaId };
        console.debug('[ALOCAÇÃO] Chamada enfileirada em carregarPilotosDisponiveis');
        return [];
    }
    carregarPilotosDisponiveis._queue.running = true;

    try {
        // Buscar lista de pilotos gerais
        const resp = await fetch('/api/admin/listar-pilotos');
        const pilotos = await resp.json();
        // Se a etapa for informada, buscar candidaturas para mostrar a equipe inscrita
        let candidaturaMap = {};
        if (etapaId) {
            try {
                const r = await fetch(`/api/etapas/${etapaId}/candidatos-pilotos`);
                const candidatosData = await r.json();
                if (candidatosData && candidatosData.sucesso && Array.isArray(candidatosData.candidatos)) {
                    candidatosData.candidatos.forEach(grupo => {
                        (grupo.candidatos || []).forEach(c => {
                            if (c.piloto_id) candidaturaMap[c.piloto_id] = grupo.equipe_nome || grupo.equipe_id;
                        });
                    });
                }
            } catch (e) {
                console.warn('[ALOCAÇÃO] Falha ao buscar candidaturas para etapa:', e);
            }
        }
        const container = document.getElementById(containerId);
        if (!container) return [];
        container.innerHTML = '';
        if (!Array.isArray(pilotos) || pilotos.length === 0) {
            container.innerHTML = '<div class="text-muted">Nenhum piloto cadastrado</div>';
            return [];
        }
        const disponiveis = pilotos.filter(p => !excluirIds.includes(p.id));
        if (disponiveis.length === 0) {
            container.innerHTML = '<div class="text-muted">Nenhum piloto disponível</div>';
            return [];
        }
        disponiveis.forEach(p => {
            const item = document.createElement('button');
            item.className = 'list-group-item list-group-item-action draggable-piloto';
            // Mostrar nome do piloto e, quando disponível, a equipe em que se inscreveu
            item.innerHTML = `${p.nome} ${candidaturaMap[p.id] ? `<small class="text-muted">• inscrito em: ${candidaturaMap[p.id]}</small>` : ''}`;
            item.draggable = true;
            item.dataset.pilotoId = p.id;
            item.dataset.pilotoNome = p.nome;
            item.addEventListener('dragstart', handlePilotoDragStart);
            item.addEventListener('dragend', handlePilotoDragEnd);
            container.appendChild(item);
        });
        return disponiveis;
    } catch (e) {
        console.error('[ALOCAÇÃO] Erro ao carregar pilotos disponíveis:', e);
        return [];
    } finally {
        // mark finished and, if there's a pending request, schedule it
        carregarPilotosDisponiveis._queue.running = false;
        const pending = carregarPilotosDisponiveis._queue.pending;
        if (pending) {
            carregarPilotosDisponiveis._queue.pending = null;
            // schedule asynchronously to avoid deep recursion
            setTimeout(() => {
                try { carregarPilotosDisponiveis(pending.containerId, pending.excluirIds, pending.etapaId); } catch (e) { console.warn('[ALOCAÇÃO] Erro ao reexecutar chamada enfileirada:', e); }
            }, 30);
        }
    }
}

async function carregarEquipesEtapa(selectId = 'selectEtapa', containerId = 'listaEquipesPilotos', excludeAssigned = true) {
    const etapaId = document.getElementById(selectId).value;
    if (!etapaId) {
        const container = document.getElementById(containerId);
        if (container) container.innerHTML = '';
        return;
    }
    try {
        const resp = await fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos${excludeAssigned ? '?exclude_assigned=1' : ''}`);
        const data = await resp.json();
        if (data.sucesso && Array.isArray(data.equipes)) {
            const allocatedIds = data.equipes.map(e => e.piloto_id).filter(Boolean);
            await carregarPilotosDisponiveis('listaPilotosDisponiveis', allocatedIds, etapaId);
            renderizarEquipesPilotos(data.equipes, etapaId, containerId);
            const container = document.getElementById(containerId);
            if (container) container.style.display = 'block';
        } else {
            console.error('[ALOCAÇÃO] Erro ao buscar equipes:', data.erro);
        }
    } catch (e) {
        console.error('[ALOCAÇÃO] Erro ao carregar equipes da etapa:', e);
    }
}

function renderizarEquipesPilotos(equipes, etapaId, containerId = 'listaEquipesPilotos') {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    equipes.forEach(equipe => {
        const col = document.createElement('div');
        col.className = 'col-md-6 mb-3';

        const card = document.createElement('div');
        card.className = 'card bg-dark text-white p-2';
        card.dataset.participacaoId = equipe.participacao_id || '';

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';

        const titulo = document.createElement('h6');
        titulo.className = 'card-title';
        titulo.textContent = equipe.equipe_nome;

        const pilotoInfo = document.createElement('p');
        pilotoInfo.className = 'card-text';
        pilotoInfo.innerHTML = `<strong>Piloto:</strong> ${equipe.piloto_nome || '<span class="text-muted">Nenhum alocado</span>'}`;

        const dropArea = document.createElement('div');
        dropArea.className = 'border rounded p-2 mt-2 drop-zone';
        dropArea.style.minHeight = '48px';
        dropArea.style.background = equipe.piloto_nome ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.02)';
        dropArea.textContent = equipe.piloto_nome ? 'Pilot already assigned' : 'Arraste um piloto aqui para alocar';

        dropArea.addEventListener('dragover', handleDragOver);
        dropArea.addEventListener('dragleave', handleDragLeave);
        dropArea.addEventListener('drop', (ev) => {
            ev.preventDefault();
            handlePilotoDrop(ev, equipe.participacao_id || equipe.equipe_id, etapaId, equipe.equipe_nome);
        });

        const btnGroup = document.createElement('div');
        btnGroup.className = 'btn-group w-100 mt-2';

        const btnProximo = document.createElement('button');
        btnProximo.className = 'btn btn-primary btn-sm';
        btnProximo.textContent = 'Alocar Próximo';
        btnProximo.onclick = () => alocarProximoPiloto(etapaId, equipe.equipe_id);

        const btnReserva = document.createElement('button');
        btnReserva.className = 'btn btn-warning btn-sm';
        btnReserva.textContent = 'Alocar Reserva';
        btnReserva.onclick = () => mostrarModalReserva(etapaId, equipe.equipe_id);

        btnGroup.appendChild(btnProximo);
        btnGroup.appendChild(btnReserva);

        cardBody.appendChild(titulo);
        cardBody.appendChild(pilotoInfo);
        cardBody.appendChild(dropArea);
        cardBody.appendChild(btnGroup);

        card.appendChild(cardBody);
        col.appendChild(card);
        container.appendChild(col);
    });
}

// Renderiza interface drag & drop com duas colunas: pilotos sem equipe (inscritos)
// e equipes que precisam de piloto (participacoes_etapas com piloto_id IS NULL)
async function carregarInterfaceAlocacaoDragDrop(selectId = 'selectEtapa', containerId = 'listaEquipesPilotos') {
        const etapaEl = document.getElementById(selectId);
        if (!etapaEl) return;
        const etapaId = etapaEl.value;
        const container = document.getElementById(containerId);
        if (!etapaId) { if (container) container.innerHTML = ''; return; }

        try {
                // Buscar equipes que precisam de piloto (participacoes_sem piloto)
                const [respEquipes, respPilotos] = await Promise.all([
                    fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos?exclude_assigned=1`, { credentials: 'include' }),
                    fetch(`/api/admin/etapas/${etapaId}/pilotos-sem-equipe`, { credentials: 'include' })
                ]);

                const equipesData = await respEquipes.json();
                const pilotosData = await respPilotos.json();

                if (respEquipes.status === 401 || respPilotos.status === 401) {
                    container.innerHTML = '<div class="alert alert-warning">Acesso não autorizado. Faça login como admin.</div>';
                    return;
                }

                const equipes = (equipesData && equipesData.sucesso && Array.isArray(equipesData.equipes)) ? equipesData.equipes : [];
                const pilotos = (pilotosData && pilotosData.sucesso && Array.isArray(pilotosData.pilotos)) ? pilotosData.pilotos : [];

                // Construir HTML parecido com o exemplo do usuário
                let html = `
                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card border-warning h-100" style="background-color: #fff9e6; min-height: 400px;">
                            <div class="card-header bg-warning text-dark"><h6 class="mb-0">📍 Pilotos Inscritos (${pilotos.length})</h6></div>
                            <div class="card-body" style="max-height: 600px; overflow-y: auto;">
                                <div id="pilotosInscritosZone" class="d-flex flex-column gap-2">
                `;

                pilotos.forEach(p => {
                        const dataIns = p.data_inscricao ? new Date(p.data_inscricao).toLocaleString('pt-BR') : '';
                        html += `
                            <div class="card p-3 draggable-piloto" draggable="true" data-piloto-id="${p.piloto_id || p.piloto_id}" data-piloto-nome="${(p.piloto_nome||p.nome||'').replace(/"/g,'&quot;')}" data-etapa-id="${etapaId}" style="background:#fff; border:3px solid #ffc107; cursor: grab;">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div><strong>👤 ${(p.piloto_nome||p.nome||'')}</strong><div class="text-muted" style="font-size:12px;">Inscrito: ${dataIns}</div><div class="text-muted" style="font-size:11px;">Equipe: ${p.equipe_nome || 'N/A'}</div></div>
                                    <div style="text-align:center;"><div style="font-size:20px; color:#ffc107;">⬌</div><small style="color:#999;">Arrastar</small></div>
                                </div>
                            </div>
                        `;
                });

                html += `
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6 mb-4">
                        <div class="card border-success h-100" style="background-color:#f5f5f5; min-height:400px;">
                            <div class="card-header bg-success text-white"><h6 class="mb-0">🏁 Equipes Pedindo Pilotos (${equipes.length})</h6></div>
                            <div class="card-body" style="max-height:600px; overflow-y:auto;">
                                <div class="d-flex flex-column gap-3" id="equipesDropZones">
                `;

                equipes.forEach(eq => {
                        html += `
                            <div class="card border-success" id="dropZone-${eq.equipe_id}" data-equipe-nome="${(eq.equipe_nome||'').replace(/\"/g,'&quot;')}" style="min-height:140px; background:#fff; border:2px dashed #dc143c;">
                                <div class="card-body pb-2">
                                    <div class="d-flex justify-content-between align-items-start mb-2">
                                        <h6 style="color:#dc143c; margin:0;">🏁 ${eq.equipe_nome}</h6>
                                        <span class="badge bg-warning text-dark">falta 1</span>
                                    </div>
                                    <div id="equipeDropZone-${eq.equipe_id}" style="min-height:60px; background:#f9f9f9; padding:12px; border-radius:4px; border:1px dashed #ccc; text-align:center;">
                                        <p class="text-muted small mb-0">👇 <strong>Arraste pilotos aqui para alocar</strong></p>
                                    </div>
                                </div>
                            </div>
                        `;
                });

                html += `
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                `;

                if (container) container.innerHTML = html;

                // Mostrar o container de equipes
                const containerEquipes = document.getElementById('containerEquipes');
                if (containerEquipes) containerEquipes.style.display = 'block';

                // Attach event listeners
                document.querySelectorAll('.draggable-piloto').forEach(el => {
                        el.addEventListener('dragstart', handlePilotoDragStart);
                        el.addEventListener('dragend', handlePilotoDragEnd);
                });

                document.querySelectorAll('[id^="dropZone-"]').forEach(dropZone => {
                        // dropZone element contains the card; add listeners to it
                        dropZone.addEventListener('dragover', handleDragOver);
                        dropZone.addEventListener('dragleave', handleDragLeave);
                        dropZone.addEventListener('drop', (ev) => {
                                ev.preventDefault();
                                const equipeId = dropZone.id.replace('dropZone-','');
                                const equipeName = dropZone.dataset.equipeNome || '';
                                handlePilotoDrop(ev, equipeId, etapaId, equipeName);
                        });
                });
        } catch (e) {
                console.error('[ALOCAÇÃO] Erro ao montar interface drag-drop:', e);
                if (container) container.innerHTML = '<div class="alert alert-danger">Erro ao carregar interface: ' + e.message + '</div>';
        }
}

window.carregarInterfaceAlocacaoDragDrop = carregarInterfaceAlocacaoDragDrop;

function handlePilotoDragStart(event) {
    const el = event.target.closest('.draggable-piloto');
    if (!el) return;
    event.dataTransfer.effectAllowed = 'move';
    const payload = {
        pilotoId: el.dataset.pilotoId,
        pilotoNome: el.dataset.pilotoNome
    };
    event.dataTransfer.setData('text/plain', JSON.stringify(payload));
    el.style.opacity = '0.5';
    el.style.cursor = 'grabbing';
}

function handlePilotoDragEnd(event) {
    const el = event.target.closest('.draggable-piloto');
    if (!el) return;
    el.style.opacity = '1';
    el.style.cursor = 'grab';
    document.querySelectorAll('.drop-zone').forEach(zone => {
        zone.classList.remove('drop-zone-active');
        zone.style.backgroundColor = '#f9f9f9';
    });
}

function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    const dropZone = event.target.closest('.drop-zone');
    if (dropZone) {
        dropZone.classList.add('drop-zone-active');
        dropZone.style.backgroundColor = '#f0f0f0';
    }
}

function handleDragLeave(event) {
    const dropZone = event.target.closest('.drop-zone');
    if (dropZone) {
        dropZone.classList.remove('drop-zone-active');
        dropZone.style.backgroundColor = '#f9f9f9';
    }
}

async function handlePilotoDrop(event, participacaoId, etapaId, equipeNomeDestino) {
    event.preventDefault();
    try {
        const dropZone = event.target.closest('.drop-zone');
        if (dropZone) {
            dropZone.classList.remove('drop-zone-active');
            dropZone.style.backgroundColor = '#f9f9f9';
        }
        const data = JSON.parse(event.dataTransfer.getData('text/plain'));
        const pilotoId = data.pilotoId;
        const pilotoNome = data.pilotoNome;
        
        // Validação
        if (!etapaId || !participacaoId || !pilotoId) {
            mostrarToast('Erro: Etapa, equipe e piloto são obrigatórios', 'error');
            return;
        }
        
        mostrarModalConfirmacaoAlocacao(pilotoNome, data.equipePrecisaNome || '', equipeNomeDestino, pilotoId, participacaoId, etapaId);
    } catch (e) {
        console.error('[DROP] Erro ao processar drop:', e);
        mostrarToast('Erro ao processar drop: ' + e.message, 'danger');
    }
}

function mostrarModalConfirmacaoAlocacao(pilotoNome, equipeOrigemNome, equipeDestinoNome, pilotoId, participacaoId, etapaId) {
    // reutiliza o modal já presente em templates (id = modalConfirmacaoAlocacao)
    // se não existir, cria um modal simples
    const existing = document.getElementById('modalConfirmacaoAlocacao');
    if (existing) {
        // preencher campos e abrir
        // para simplicidade chamamos a função global definida nos templates (se houver)
        try {
            const btn = existing.querySelector('.btn-success');
            if (btn) {
                // Se o id passado corresponde a uma participacao no DOM, usar o fluxo por participacao;
                // caso contrário, tratá-lo como um equipe_id e usar o endpoint de reserva.
                const participacaoEl = document.querySelector(`[data-participacao-id="${participacaoId}"]`);
                if (participacaoEl) {
                    btn.onclick = () => confirmarAlocacaoPiloto(pilotoId, participacaoId, etapaId, pilotoNome);
                } else {
                    btn.onclick = () => confirmarAlocacaoReserva(pilotoId, participacaoId, etapaId, pilotoNome);
                }
            }
            const body = existing.querySelector('.modal-body');
            if (body) body.innerHTML = `<div class="alert alert-info">Confirmar alocação de <strong>${pilotoNome}</strong> para <strong>${equipeDestinoNome}</strong>?</div>`;
            const modal = new bootstrap.Modal(existing, { backdrop: 'static' });
            modal.show();
            return;
        } catch (e) { console.warn('[MODAL CONF] erro ao usar modal existente', e); }
    }

    // fallback: alerta simples
    if (confirm(`Alocar ${pilotoNome} para ${equipeDestinoNome}?`)) {
        const participacaoEl = document.querySelector(`[data-participacao-id="${participacaoId}"]`);
        if (participacaoEl) confirmarAlocacaoPiloto(pilotoId, participacaoId, etapaId, pilotoNome);
        else confirmarAlocacaoReserva(pilotoId, participacaoId, etapaId, pilotoNome);
    }
}

async function confirmarAlocacaoReserva(pilotoId, equipeId, etapaId, pilotoNome) {
    try {
        const resp = await fetch(`/api/admin/etapas/${etapaId}/equipes/${equipeId}/alocar-piloto-reserva`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ piloto_id: pilotoId })
        });
        const resultado = await resp.json();
        if (resultado.sucesso) {
            mostrarToast(`Piloto ${pilotoNome} alocado com sucesso`, 'success');
            try {
                const pilotoEl = document.querySelector(`.draggable-piloto[data-piloto-id="${pilotoId}"]`);
                if (pilotoEl && pilotoEl.parentNode) pilotoEl.parentNode.removeChild(pilotoEl);
                const dropCard = document.getElementById(`dropZone-${equipeId}`);
                if (dropCard) {
                    if (dropCard.parentNode) dropCard.parentNode.removeChild(dropCard);
                }
            } catch (domErr) { console.warn('[ALOCAÇÃO] Erro ao remover elementos do DOM (reserva):', domErr); }
            setTimeout(() => { try { carregarInterfaceAlocacaoDragDrop('selectEtapa','listaEquipesPilotos'); } catch(e){console.warn(e);} }, 600);
        } else {
            mostrarToast(resultado.erro || 'Erro ao alocar piloto', 'error');
        }
    } catch (e) {
        console.error('[CONF ALLOC RES]', e);
        mostrarToast('Erro ao alocar piloto: ' + e.message, 'error');
    }
}

async function confirmarAlocacaoPiloto(pilotoId, participacaoId, etapaId, pilotoNome) {
    try {
        // usar endpoint genérico admin/alocar-piloto-etapa
        const resp = await fetch('/api/admin/alocar-piloto-etapa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ participacao_id: participacaoId, piloto_id: pilotoId })
        });
        const resultado = await resp.json();
        if (resultado.sucesso) {
            mostrarToast(`Piloto ${pilotoNome} alocado com sucesso`, 'success');
            // Remover imediatamente o piloto e a equipe do DOM para feedback instantâneo
            try {
                // remover piloto da lista de pilotos disponíveis
                const pilotoEl = document.querySelector(`.draggable-piloto[data-piloto-id="${pilotoId}"]`);
                if (pilotoEl && pilotoEl.parentNode) pilotoEl.parentNode.removeChild(pilotoEl);
                // remover card da equipe (procura por atributo participacao)
                const equipeCard = document.querySelector(`[data-participacao-id="${participacaoId}"]`);
                if (equipeCard) {
                    const col = equipeCard.closest('.col-md-6') || equipeCard.closest('[class*="col-"]');
                    if (col && col.parentNode) col.parentNode.removeChild(col);
                    else if (equipeCard.parentNode) equipeCard.parentNode.removeChild(equipeCard);
                }
            } catch (domErr) { console.warn('[ALOCAÇÃO] Erro ao remover elementos do DOM:', domErr); }

            // Atualizar listas em segundo plano após breve atraso
            setTimeout(() => {
                try { carregarEquipesEtapa(); } catch (e) { console.warn(e); }
            }, 600);
        } else {
            mostrarToast(resultado.erro || 'Erro ao alocar piloto', 'error');
        }
    } catch (e) {
        console.error('[CONF ALLOC] Erro:', e);
        mostrarToast('Erro ao alocar piloto: ' + e.message, 'error');
    }
}

// Exportar nomes legíveis globalmente (opcional)
window.carregarEtapasParaAlocacao = carregarEtapasParaAlocacao;
window.carregarPilotosDisponiveis = carregarPilotosDisponiveis;
window.carregarEquipesEtapa = carregarEquipesEtapa;
window.renderizarEquipesPilotos = renderizarEquipesPilotos;
window.handlePilotoDragStart = handlePilotoDragStart;
window.handlePilotoDragEnd = handlePilotoDragEnd;
window.handleDragOver = handleDragOver;
window.handleDragLeave = handleDragLeave;
window.handlePilotoDrop = handlePilotoDrop;
window.mostrarModalConfirmacaoAlocacao = mostrarModalConfirmacaoAlocacao;
window.confirmarAlocacaoPiloto = confirmarAlocacaoPiloto;

// =================== FIM - ALOCAÇÃO DE PILOTOS ===================

// =================== ADMIN - EQUIPES ===================

async function carregarEquipesCadastro() {
    try {
        const resp = await fetch('/api/admin/equipes');
        const equipes = await resp.json();
        
        const container = document.getElementById('listaEquipesCadastro');
        if (!container) return;
        
        if (!equipes || equipes.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhuma equipe cadastrada</p>';
            return;
        }
        
        let html = '<div class="row">';
        equipes.forEach(equipe => {
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">${equipe.nome}</h6>
                        </div>
                        <div class="card-body">
                            <p class="mb-1"><strong>Série:</strong> ${equipe.serie}</p>
                            <p class="mb-1"><strong>Saldo:</strong> ${formatarMoeda(equipe.saldo)}</p>
                            <p class="mb-1"><strong>Carro:</strong> ${equipe.carro || 'Nenhum'}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (e) {
        console.error('Erro ao carregar equipes:', e);
        mostrarToast('Erro ao carregar equipes', 'error');
    }
}

async function cadastrarEquipe() {
    const nomeEl = document.getElementById('equipeNome') || document.getElementById('nomeEquipe');
    const doricoinsEl = document.getElementById('equipeDoricoins') || document.getElementById('doricoinsEquipe');
    const senhaEl = document.getElementById('equipeSenha') || document.getElementById('senhaEquipe');
    const serieEl = document.getElementById('equipeSerie') || document.getElementById('serieEquipe');
    const carroEl = document.getElementById('equipeCarroSelecionado') || document.getElementById('carroEquipe');
    const nome = (nomeEl && nomeEl.value) ? nomeEl.value.trim() : '';
    const doricoins = (doricoinsEl && doricoinsEl.value) ? parseFloat(doricoinsEl.value) : 10000;
    const senha = (senhaEl && senhaEl.value) ? senhaEl.value.trim() : '';
    const serie = (serieEl && serieEl.value) ? serieEl.value : 'A';
    const carroId = (carroEl && carroEl.value) ? String(carroEl.value).trim() : '';
    
    if (!nome) {
        mostrarToast('Nome da equipe é obrigatório', 'error');
        return;
    }
    
    if (!senha) {
        mostrarToast('Senha é obrigatória', 'error');
        return;
    }
    
    try {
        const resp = await fetch('/api/admin/cadastrar-equipe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nome: nome,
                    doricoins: doricoins,
                    senha: senha,
                    serie: serie,
                    carro_id: carroId || undefined
                })
        });
        
        const resultado = await resp.json();
        
        if (resultado.sucesso) {
            mostrarToast('Equipe cadastrada com sucesso!', 'success');
            // Limpar formulário (suporta IDs admin_equipes ou alternativos)
            if (nomeEl) nomeEl.value = '';
            if (doricoinsEl) doricoinsEl.value = '10000';
            if (senhaEl) senhaEl.value = '';
            if (serieEl) serieEl.value = 'A';
            if (carroEl) carroEl.value = '';
            // Recarregar lista
            carregarEquipesCadastro();
        } else {
            mostrarToast('Erro: ' + resultado.erro, 'error');
        }
    } catch (e) {
        console.error('Erro ao cadastrar equipe:', e);
        mostrarToast('Erro ao cadastrar equipe', 'error');
    }
}

// Retorna true se a variação tem todas as peças (motor, câmbio, suspensão, kit ângulo, diferencial)
function variacaoCompleta(v) {
    return !!(v && v.motor_id && v.cambio_id && v.suspensao_id && v.kit_angulo_id && v.diferencial_id);
}

// Preencher dropdown de carros (equipes e variações)
async function carregarCarrosPraEquipe() {
    try {
        const resp = await fetch('/api/admin/carros');
        const carros = await resp.json();
        if (!Array.isArray(carros)) return;
        const opt = (id, label) => `<option value="${id}">${label}</option>`;
        // No dropdown da equipe: só modelos que tenham ao menos uma variação com todas as peças
        const carrosCompletos = carros.filter(c =>
            (c.variacoes || []).some(v => variacaoCompleta(v))
        );
        const elEquipe = document.getElementById('equipeCarroSelecionado');
        if (elEquipe) {
            const grp = elEquipe.querySelector('optgroup') || elEquipe;
            const inner = carrosCompletos.map(c => opt(c.id, (c.marca || '') + ' ' + (c.modelo || ''))).join('');
            if (elEquipe.querySelector('optgroup')) {
                elEquipe.querySelector('optgroup').innerHTML = inner;
            } else {
                const keepFirst = elEquipe.options.length ? elEquipe.options[0].outerHTML : '<option value="">Sem carro</option>';
                elEquipe.innerHTML = keepFirst + inner;
            }
        }
        // Dropdown de variações: todos os modelos (para cadastrar/editar variações)
        const grpVariacao = document.getElementById('variacaoModelosGroup');
        if (grpVariacao) {
            grpVariacao.innerHTML = carros.map(c => `<option value="${c.id}">${(c.marca || '')} ${(c.modelo || '')}</option>`).join('');
        }
    } catch (e) {
        console.error('Erro carregarCarrosPraEquipe:', e);
    }
}

// Tornar funções globais
window.carregarEquipesCadastro = carregarEquipesCadastro;
window.cadastrarEquipe = cadastrarEquipe;
window.carregarCarrosPraEquipe = carregarCarrosPraEquipe;

// =================== ADMIN - SOLICITAÇÕES ===================

async function carregarSolicitacoes() {
    try {
        const resp = await fetch('/api/admin/solicitacoes-pecas');
        const solicitacoes = await resp.json();
        const hash = JSON.stringify(solicitacoes);
        if (_cacheSolicitacoesPecas === hash) return;
        _cacheSolicitacoesPecas = hash;

        const container = document.getElementById('listaSolicitacoesPecas');
        if (!container) return;
        
        if (!solicitacoes || solicitacoes.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhuma solicitação de peça pendente</p>';
            return;
        }
        
        let html = '<div class="row">';
        solicitacoes.forEach(sol => {
            const statusClass = sol.status === 'pendente' ? 'warning' : 'success';
            const statusText = sol.status === 'pendente' ? 'Pendente' : 'Aprovada';
            
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-${statusClass}">
                        <div class="card-header bg-${statusClass} text-white">
                            <h6 class="mb-0">${sol.peca_nome}</h6>
                        </div>
                        <div class="card-body">
                            <p class="mb-1"><strong>Equipe:</strong> ${sol.equipe_nome}</p>
                            <p class="mb-1"><strong>Carro:</strong> ${sol.carro_nome || 'N/A'}</p>
                            <p class="mb-1"><strong>Preço:</strong> ${formatarMoeda(sol.preco)}</p>
                            <p class="mb-1"><strong>Status:</strong> <span class="badge bg-${statusClass}">${statusText}</span></p>
                            ${sol.status === 'pendente' ? `<button class="btn btn-success btn-sm" onclick="aprovarSolicitacao(${sol.id})">Aprovar</button>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (e) {
        console.error('Erro ao carregar solicitações de peças:', e);
        mostrarToast('Erro ao carregar solicitações', 'error');
    }
}

async function carregarSolicitacoesCarros() {
    try {
        const resp = await fetch('/api/admin/solicitacoes-carros');
        const solicitacoes = await resp.json();
        const hash = JSON.stringify(solicitacoes);
        if (_cacheSolicitacoesCarros === hash) return;
        _cacheSolicitacoesCarros = hash;

        const container = document.getElementById('listaSolicitacoesCarros');
        if (!container) return;
        
        if (!solicitacoes || solicitacoes.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhuma solicitação de carro pendente</p>';
            return;
        }
        
        let html = '<div class="row">';
        solicitacoes.forEach(sol => {
            const statusClass = sol.status === 'pendente' ? 'warning' : 'success';
            const statusText = sol.status === 'pendente' ? 'Pendente' : 'Aprovada';
            
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-${statusClass}">
                        <div class="card-header bg-${statusClass} text-white">
                            <h6 class="mb-0">${sol.carro_nome}</h6>
                        </div>
                        <div class="card-body">
                            <p class="mb-1"><strong>Equipe:</strong> ${sol.equipe_nome}</p>
                            <p class="mb-1"><strong>Valor:</strong> ${formatarMoeda(sol.valor_total)}</p>
                            <p class="mb-1"><strong>Status:</strong> <span class="badge bg-${statusClass}">${statusText}</span></p>
                            ${sol.status === 'pendente' ? `<button class="btn btn-success btn-sm" onclick="aprovarSolicitacaoCarro(${sol.id})">Aprovar</button>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (e) {
        console.error('Erro ao carregar solicitações de carros:', e);
        mostrarToast('Erro ao carregar solicitações', 'error');
    }
}

async function aprovarSolicitacao(solicitacaoId) {
    try {
        const resp = await fetch('/api/admin/processar-solicitacao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ solicitacao_id: solicitacaoId })
        });
        
        const resultado = await resp.json();
        
        if (resultado.sucesso) {
            mostrarToast('Solicitação aprovada!', 'success');
            carregarSolicitacoes();
        } else {
            mostrarToast('Erro: ' + resultado.erro, 'error');
        }
    } catch (e) {
        console.error('Erro ao aprovar solicitação:', e);
        mostrarToast('Erro ao aprovar solicitação', 'error');
    }
}

async function aprovarSolicitacaoCarro(solicitacaoId) {
    try {
        const resp = await fetch('/api/admin/aprovar-solicitacao-ativacao-carro', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ solicitacao_id: solicitacaoId })
        });
        
        const resultado = await resp.json();
        
        if (resultado.sucesso) {
            mostrarToast('Solicitação de carro aprovada!', 'success');
            carregarSolicitacoesCarros();
        } else {
            mostrarToast('Erro: ' + resultado.erro, 'error');
        }
    } catch (e) {
        console.error('Erro ao aprovar solicitação de carro:', e);
        mostrarToast('Erro ao aprovar solicitação', 'error');
    }
}

// Tornar funções globais
window.carregarSolicitacoes = carregarSolicitacoes;
window.carregarSolicitacoesCarros = carregarSolicitacoesCarros;
window.aprovarSolicitacao = aprovarSolicitacao;
window.aprovarSolicitacaoCarro = aprovarSolicitacaoCarro;

