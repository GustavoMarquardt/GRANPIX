async function abrirQualificacao(etapaId) {
    try {
        // Primeiro, verificar se a etapa já possui um evento em andamento
        try {
            const eventoResp = await fetch(`/api/etapas/${etapaId}/evento`);
            const eventoData = await eventoResp.json();
            if (eventoData.sucesso && eventoData.evento && eventoData.evento.etapa && (eventoData.evento.etapa.status === 'em_andamento' || eventoData.evento.etapa.status === 'batalhas')) {
                mostrarToast('ℹ️ Etapa já em andamento — abrindo interface de qualificação...', 'info');

                // Garantir aba e carregar tabela sem tentar iniciar novamente
                setTimeout(() => {
                    try {
                        const abaFazerEtapa = document.querySelector('a[href="#fazer-etapa"]');
                        if (abaFazerEtapa) {
                            if (window.bootstrap && bootstrap.Tab) {
                                new bootstrap.Tab(abaFazerEtapa).show();
                            } else {
                                abaFazerEtapa.click();
                            }
                        }

                        const pane = document.getElementById('fazer-etapa');
                        if (pane) { pane.classList.add('show', 'active'); pane.style.display = ''; }
                        if (typeof carregarEtapaHoje === 'function') carregarEtapaHoje().catch(() => {});
                    } catch (e) { console.error('[QUALIFICACAO] Fallback ativar aba:', e); }
                }, 120);

                // Carregar a tabela de qualificação no painel admin
                setTimeout(() => { carregarTabelaVoltasAdmin(etapaId); }, 300);
                return;
            }
        } catch (e) {
            console.warn('[QUALIFICACAO] Não foi possível verificar status do evento, prosseguindo para iniciar:', e);
        }

        // Se não estiver em andamento, solicitar início ao servidor
        const resp = await fetch('/api/admin/fazer-etapa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ etapa: etapaId })
        });
        const resultado = await resp.json();
        if (resultado.sucesso) {
            mostrarToast('✓ Etapa iniciada! Carregando interface de qualificação...', 'success');

            // Aguardar um pouco e ativar a aba "Fazer Etapa" de forma robusta
            setTimeout(() => {
                try {
                    const abaFazerEtapa = document.querySelector('a[href="#fazer-etapa"]');
                    if (abaFazerEtapa) {
                        if (window.bootstrap && bootstrap.Tab) {
                            new bootstrap.Tab(abaFazerEtapa).show();
                            console.log('[QUALIFICACAO] Aba "Fazer Etapa" ativada via bootstrap.Tab.show()');
                        } else {
                            abaFazerEtapa.click();
                            console.log('[QUALIFICACAO] Aba "Fazer Etapa" ativada via click()');
                        }

                        const pane = document.getElementById('fazer-etapa');
                        if (pane) { pane.classList.add('show', 'active'); pane.style.display = ''; }
                        if (typeof carregarEtapaHoje === 'function') carregarEtapaHoje().catch(e => console.error('Erro carregarEtapaHoje (abrirQualificacao):', e));
                    }
                } catch (e) {
                    console.error('[QUALIFICACAO] Erro ao ativar aba Fazer Etapa:', e);
                }
            }, 200);

            // Carregar a tabela de qualificação no painel admin
            setTimeout(() => { carregarTabelaVoltasAdmin(etapaId); }, 800);
        } else {
            mostrarToast('Erro: ' + resultado.erro, 'error');
        }
    } catch (e) {
        mostrarToast('Erro ao abrir etapa', 'error');
    }
}

async function carregarAndMostrarEquipes(etapaId) {
    try {
        const resp = await fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos`);
        const data = await resp.json();
        
        if (data.sucesso && data.equipes) {
            mostrarEquipesQualificacao(data.equipes, etapaId);
        } else {
            mostrarToast('Erro ao carregar equipes', 'error');
            setTimeout(() => location.reload(), 1500);
        }
    } catch (e) {
        console.error('Erro:', e);
        mostrarToast('Erro ao carregar equipes', 'error');
        setTimeout(() => location.reload(), 1500);
    }
}

function mostrarEquipesQualificacao(equipes, etapaId) {
    // Criar um modal com as equipes
    const modalElement = document.createElement('div');
    modalElement.className = 'modal fade';
    modalElement.id = 'modalEquipesQualificacao';
    modalElement.tabIndex = '-1';
    modalElement.setAttribute('aria-hidden', 'true');
    modalElement.setAttribute('data-bs-backdrop', 'static');
    modalElement.setAttribute('data-bs-keyboard', 'false');
    
    let equipesHtml = '<div class="row">';
    equipes.forEach(eq => {
        const pilotoInfo = eq.piloto_nome ? `<strong>${eq.piloto_nome}</strong>` : '<span class="text-danger">⚠️ SEM PILOTO</span>';
        const carroInfo = eq.carro_modelo ? `(${eq.carro_modelo})` : '';
        
        equipesHtml += `
            <div class="col-md-6 mb-3">
                <div class="card ${eq.piloto_nome ? 'border-success' : 'border-danger'}">
                    <div class="card-header ${eq.piloto_nome ? 'bg-success' : 'bg-danger'} text-white">
                        <h6 class="mb-0">🏁 ${eq.equipe_nome}</h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <strong>Piloto:</strong> ${pilotoInfo}
                        </div>
                        ${eq.carro_modelo ? `<div><strong>Carro:</strong> ${carroInfo}</div>` : ''}
                        <div class="mt-2">
                            <small class="text-muted">Tipo: ${eq.tipo_participacao} | Status: ${eq.status}</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    equipesHtml += '</div>';
    
    modalElement.innerHTML = `
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-warning text-dark">
                    <h5 class="modal-title">📋 Equipes na Qualificação</h5>
                </div>
                <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                    <div class="alert alert-info">
                        <strong>QUALIFICAÇÃO INICIADA!</strong><br>
                        Total de equipes: <strong>${equipes.length}</strong><br>
                        Equipes com piloto: <strong>${equipes.filter(e => e.piloto_nome).length}</strong>
                    </div>
                    ${equipesHtml}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" onclick="confirmarQualificacao()">
                        ✓ Confirmar e Continuar
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modalElement);
    const modal = new bootstrap.Modal(modalElement, {
        backdrop: 'static',
        keyboard: false
    });
    
    modal.show();
    
    // Remover modal do DOM após fechado
    modalElement.addEventListener('hidden.bs.modal', () => {
        modalElement.remove();
    });
}

function confirmarQualificacao() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('modalEquipesQualificacao'));
    if (modal) {
        modal.hide();
        setTimeout(() => location.reload(), 300);
    }
}

async function finalizarQualificacao(etapaId) {
    if (!confirm('Tem certeza? Vai finalizar a qualificacao e calcular pontos!')) {
        return;
    }
    try {
        const resp = await fetch(`/api/admin/finalizar-qualificacao/${etapaId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const resultado = await resp.json();
        if (resultado.sucesso) {
            mostrarToast('Qualificacao finalizada! Etapa agora esta ATIVA.', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            mostrarToast('Erro: ' + resultado.erro, 'error');
        }
    } catch (e) {
        mostrarToast('Erro ao finalizar qualificacao', 'error');
    }
}

async function entrarQualificacao(etapaId, botao) {
    try {
        botao.disabled = true;
        botao.innerHTML = 'Processando...';
        
        const resp = await fetch(`/api/etapas/${etapaId}/entrar-qualificacao`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const resultado = await resp.json();
        
        if (resultado.sucesso) {
            // Verificar se evento está em andamento
            const eventoResp = await fetch(`/api/etapas/${etapaId}/evento`);
            const eventoData = await eventoResp.json();
            
            if (eventoData.sucesso && eventoData.evento && eventoData.evento.etapa.status === 'em_andamento') {
                mostrarAlerta('Bem-vindo! Abrindo evento ao vivo...', 'sucesso');
                setTimeout(() => mostrarEventoAoVivo(etapaId), 500);
            } else {
                mostrarAlerta('Bem-vindo a qualificacao! Boa sorte!', 'sucesso');
                botao.innerHTML = 'Participando';
                botao.className = 'btn btn-success w-100 mt-2';
            }
        } else {
            mostrarAlerta('Erro: ' + resultado.erro, 'erro');
            botao.disabled = false;
            botao.innerHTML = 'ENTRAR NA QUALIFICACAO';
        }
    } catch (e) {
        mostrarAlerta('Erro ao entrar na qualificacao', 'erro');
        botao.disabled = false;
        botao.innerHTML = 'ENTRAR NA QUALIFICACAO';
    }
}

// ==================== ENTRAR NAS BATALHAS ====================

async function entrarBatalhas(etapaId, botao) {
    try {
        botao.disabled = true;
        botao.innerHTML = 'Processando...';
        
        const resp = await fetch(`/api/etapas/${etapaId}/entrar-batalhas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const resultado = await resp.json();
        
        if (resultado.sucesso) {
            // Verificar se evento está em batalhas
            const eventoResp = await fetch(`/api/etapas/${etapaId}/evento`);
            const eventoData = await eventoResp.json();
            
            if (eventoData.sucesso && eventoData.evento && (eventoData.evento.etapa.status === 'em_andamento' || eventoData.evento.etapa.status === 'batalhas')) {
                mostrarAlerta('Bem-vindo! Abrindo batalhas ao vivo...', 'sucesso');
                setTimeout(() => mostrarEventoAoVivo(etapaId), 500);
            } else {
                mostrarAlerta('Bem-vindo as batalhas! Boa sorte!', 'sucesso');
                botao.innerHTML = 'Participando';
                botao.className = 'btn btn-success w-100 mt-2';
            }
        } else {
            mostrarAlerta('Erro: ' + resultado.erro, 'erro');
            botao.disabled = false;
            botao.innerHTML = '⚔️ ENTRAR NAS BATALHAS';
        }
    } catch (e) {
        mostrarAlerta('Erro ao entrar nas batalhas', 'erro');
        botao.disabled = false;
        botao.innerHTML = '⚔️ ENTRAR NAS BATALHAS';
    }
}

// ==================== CARREGAR ETAPA DO DIA ====================

async function carregarEtapaHoje() {
    try {
        console.log('[ETAPA HOJE] Iniciando carregamento...');
        const resp = await fetch('/api/admin/etapa-hoje');
        const data = await resp.json();
        
        console.log('[ETAPA HOJE] Resposta recebida:', data);
        
        if (data.sucesso && data.etapa) {
            console.log('[ETAPA HOJE] Preenchendo informações...');
            preencherEtapaHoje(data.etapa);
        } else {
            console.log('[ETAPA HOJE] Nenhuma etapa encontrada. Erro:', data.mensagem);
            exibirSemEtapaHoje();
        }
    } catch (e) {
        console.error('[ETAPA HOJE] Erro ao carregar etapa de hoje:', e);
        exibirSemEtapaHoje();
    }
}

// Tornar função global para acesso do HTML
window.carregarEtapaHoje = carregarEtapaHoje;

function preencherEtapaHoje(etapa) {
    console.log('[ETAPA HOJE] preencherEtapaHoje chamado com:', etapa);
    
    // Verificar se os elementos existem (podem não existir em outras páginas)
    const infoElement = document.getElementById('infoEtapaHoje');
    const semEtapaElement = document.getElementById('semEtapaHoje');
    const grupoEtapaElement = document.getElementById('grupoEtapa');
    const botaoElement = document.getElementById('botaoIniciarQualificacao');
    
    // Se nenhum elemento foi encontrado, sair silenciosamente (estamos em outra página)
    if (!infoElement && !semEtapaElement && !grupoEtapaElement && !botaoElement) {
        console.log('[ETAPA HOJE] Elementos não encontrados - script rodando em página diferente');
        return;
    }
    
    console.log('[ETAPA HOJE] Elementos encontrados:', {
        infoElement: !!infoElement,
        semEtapaElement: !!semEtapaElement,
        grupoEtapaElement: !!grupoEtapaElement,
        botaoElement: !!botaoElement
    });
    
    if (infoElement) infoElement.style.display = 'block';
    if (semEtapaElement) semEtapaElement.style.display = 'none';
    
    // Verificar se a etapa já está em andamento
    verificarStatusEtapa(etapa.id);
    
    // Preencher dados
    console.log('[ETAPA HOJE] Preenchendo dados do campeonato e etapa...');
    if (document.getElementById('etapaHojeCampeonatoNome')) document.getElementById('etapaHojeCampeonatoNome').textContent = etapa.campeonato_nome;
    if (document.getElementById('etapaHojeCampeonatoSerie')) document.getElementById('etapaHojeCampeonatoSerie').textContent = etapa.serie;
    if (document.getElementById('etapaHojeNumero')) document.getElementById('etapaHojeNumero').textContent = etapa.numero;
    if (document.getElementById('etapaHojeNome')) document.getElementById('etapaHojeNome').textContent = etapa.nome;
    if (document.getElementById('etapaHojeHora')) document.getElementById('etapaHojeHora').textContent = etapa.hora_etapa ? etapa.hora_etapa.substring(0, 5) : '-';
    
    if (document.getElementById('etapaIdAtual')) document.getElementById('etapaIdAtual').value = etapa.id;
    
    // Carregar equipes e pilotos
    console.log('[ETAPA HOJE] Carregando equipes para etapa:', etapa.id);
    carregarEquipesETapaHoje(etapa.id);
    
    console.log('[ETAPA HOJE] Etapa carregada:', etapa.nome, '- ID:', etapa.id);
}

async function carregarEquipesETapaHoje(etapaId) {
    try {
        console.log('[EQUIPES] Carregando equipes da etapa:', etapaId);
        const resp = await fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos`);
        const data = await resp.json();
        
        console.log('[EQUIPES] Resposta recebida:', data);
        
        if (data.sucesso && data.equipes) {
            console.log('[EQUIPES] Preenchendo tabela com', data.equipes.length, 'equipes');
            preencherTabelaEquipes(data.equipes);
        } else {
            console.error('[EQUIPES] Erro na resposta:', data.erro);
        }
    } catch (e) {
        console.error('[EQUIPES] Erro ao carregar equipes:', e);
    }
}

async function verificarStatusEtapa(etapaId) {
    try {
        console.log('[STATUS ETAPA] Verificando status da etapa:', etapaId);
        const resp = await fetch(`/api/etapas/${etapaId}/evento`);
        const data = await resp.json();
        
        const grupoEtapaElement = document.getElementById('grupoEtapa');
        const botaoElement = document.getElementById('botaoIniciarQualificacao');
        const containerVoltas = document.getElementById('containerVoltasAdmin');
        
        if (data.sucesso && data.evento && data.evento.etapa && data.evento.etapa.status === 'em_andamento') {
            console.log('[STATUS ETAPA] Etapa já em andamento - mostrando tabela diretamente');
            // Etapa já em andamento - esconder botão e mostrar tabela
            if (grupoEtapaElement) grupoEtapaElement.style.display = 'none';
            if (botaoElement) botaoElement.style.display = 'none';
            if (containerVoltas) containerVoltas.style.display = 'block';
            
            // Carregar a tabela de qualificação
            carregarTabelaVoltasAdmin(etapaId);
        } else {
            console.log('[STATUS ETAPA] Etapa não iniciada - mostrando botão');
            // Etapa não iniciada - mostrar botão e esconder tabela
            if (grupoEtapaElement) grupoEtapaElement.style.display = 'block';
            if (botaoElement) botaoElement.style.display = 'block';
            if (containerVoltas) containerVoltas.style.display = 'none';
        }
    } catch (e) {
        console.warn('[STATUS ETAPA] Erro ao verificar status, assumindo etapa não iniciada:', e);
        // Em caso de erro, mostrar botão por padrão
        const grupoEtapaElement = document.getElementById('grupoEtapa');
        const botaoElement = document.getElementById('botaoIniciarQualificacao');
        const containerVoltas = document.getElementById('containerVoltasAdmin');
        
        if (grupoEtapaElement) grupoEtapaElement.style.display = 'block';
        if (botaoElement) botaoElement.style.display = 'block';
        if (containerVoltas) containerVoltas.style.display = 'none';
    }
}

function preencherTabelaEquipes(equipes) {
    console.log('[TABELA] preencherTabelaEquipes chamado com', equipes.length, 'equipes');
    
    const gridContainer = document.getElementById('gridEquipesPits');
    const container = document.getElementById('containerEquipesPilotos');
    
    // Se o elemento grid não existe, é normal - foi removido da interface
    if (!gridContainer) {
        console.log('[TABELA] Grid de pits não existe (foi removido da interface)');
        return;
    }
    
    gridContainer.innerHTML = '';
    
    equipes.forEach((eq, idx) => {
        console.log(`[TABELA] Adicionando equipe ${idx + 1}:`, eq.equipe_nome);
        
        // Determinar cores baseadas no status do piloto (vermelho, preto e branco)
        const temPiloto = !!eq.piloto_nome;
        const borderColor = temPiloto ? '#ff0000' : '#cc0000';
        const piloIcon = temPiloto ? '🏎️' : '⚠️';
        const piloColor = temPiloto ? '#00ff00' : '#ff6666';
        
        const pitCard = document.createElement('div');
        pitCard.className = 'pit-card-admin';
        pitCard.style.cssText = `
            background: linear-gradient(180deg, #0a0a0a 0%, #1a1a1a 100%);
            border: 3px solid ${borderColor};
            border-radius: 0px;
            padding: 20px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(255,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
        `;
        
        pitCard.onmouseover = () => {
            pitCard.style.transform = 'translateY(-4px)';
            pitCard.style.boxShadow = '0 12px 36px rgba(255,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.2)';
            pitCard.style.borderColor = '#ff3333';
        };
        
        pitCard.onmouseout = () => {
            pitCard.style.transform = 'translateY(0)';
            pitCard.style.boxShadow = '0 8px 24px rgba(255,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)';
            pitCard.style.borderColor = borderColor;
        };
        
        // Número do pit grande no topo
        pitCard.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid rgba(255,0,0,0.3); padding-bottom: 12px;">
                <div>
                    <div style="font-size: 11px; color: #ff0000; font-weight: bold; letter-spacing: 2px;">PIT</div>
                    <div style="font-size: 32px; font-weight: bold; color: rgba(255,255,255,0.3); font-family: 'Courier New'; line-height: 1;">
                        ${String(idx + 1).padStart(2, '0')}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">QUAL</div>
                    <div style="font-size: 28px; font-weight: bold; color: #ff0000; font-family: 'Courier New';">
                        ${eq.ordem_qualificacao ? String(eq.ordem_qualificacao).padStart(2, '0') : '—'}
                    </div>
                </div>
            </div>
            
            <div style="padding: 8px 0;">
                <div style="font-size: 11px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px; text-transform: uppercase;">EQUIPE</div>
                <div style="font-size: 22px; font-weight: bold; color: #fff; text-shadow: 0 0 15px rgba(255,0,0,0.4); line-height: 1.2;">
                    ${eq.equipe_nome}
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                <div style="background: rgba(255,0,0,0.1); padding: 10px; border-left: 3px solid ${borderColor}; border-radius: 0;">
                    <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">PILOTO</div>
                    <div style="font-size: 18px; font-weight: bold; color: ${piloColor};">${piloIcon}</div>
                    <div style="font-size: 12px; color: ${piloColor}; margin-top: 4px; word-break: break-word;">
                        ${eq.piloto_nome ? eq.piloto_nome.split(' ')[0] : 'VAZIO'}
                    </div>
                </div>
                
                <div style="background: rgba(255,0,0,0.1); padding: 10px; border-left: 3px solid ${borderColor}; border-radius: 0;">
                    <div style="font-size: 10px; color: #ff0000; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">STATUS</div>
                    <div style="font-size: 12px; font-weight: bold; color: #fff; background: rgba(255,0,0,0.3); padding: 6px 8px; border-radius: 2px; text-align: center;">
                        ${eq.status.toUpperCase()}
                    </div>
                </div>
            </div>
        `;
        
        gridContainer.appendChild(pitCard);
    });
    
    if (container) {
        console.log('[TABELA] Mostrando container');
        container.style.display = 'block';
    } else {
        console.error('[TABELA] Elemento containerEquipesPilotos não encontrado!');
    }
}

// Função para mostrar pits em um modal (para pilotos e equipes)
async function mostrarPitsEtapa(etapaId) {
    console.log('[PITS MODAL] Carregando pits para etapa:', etapaId);
    
    try {
        // Primeiro, obter info da etapa para saber o status
        const eventoResp = await fetch(`/api/etapas/${etapaId}/evento`);
        const eventoData = await eventoResp.json();
        
        if (eventoData.sucesso && eventoData.evento) {
            const etapaStatus = eventoData.evento.etapa.status;
            
            if (etapaStatus === 'em_andamento' || etapaStatus === 'batalhas') {
                console.log('[PITS MODAL] Etapa em andamento, mostrando evento ao vivo');
                mostrarEventoAoVivo(etapaId);
                return;
            } else if (etapaStatus === 'agendada') {
                console.log('[PITS MODAL] Etapa agendada, mostrando equipes procurando piloto');
                mostrarEquipesProcurandoPiloto(etapaId, eventoData.evento.etapa);
                return;
            }
        }
        
        // Caso contrário, carregar view estática de qualificação
        const resp = await fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos`);
        const data = await resp.json();
        
        if (!data.sucesso || !data.equipes) {
            console.error('[PITS MODAL] Erro ao carregar pits');
            return;
        }
        
        // Criar modal
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modalPitsEtapa';
        modalDiv.tabIndex = '-1';
        modalDiv.setAttribute('data-bs-backdrop', 'static');
        modalDiv.setAttribute('data-bs-keyboard', 'false');
        modalDiv.style.zIndex = '100000';
        
        // Grid de pits com tema vermelho, preto e branco
        let pitsHtml = '<div style="max-height: 70vh; overflow-y: auto; padding: 10px 0;">';
        
        data.equipes.forEach((eq, idx) => {
            const temPiloto = !!eq.piloto_nome;
            const borderColor = temPiloto ? '#ff0000' : '#cc0000';
            const piloIcon = temPiloto ? '🏎️' : '⚠️';
            const piloColor = temPiloto ? '#00ff00' : '#ff6666';
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
            <div class="modal-dialog modal-fullscreen" style="z-index: 100000;">
                <div class="modal-content" style="background: #000; border: 2px solid #ff0000; z-index: 100000;">
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
        
        // Ajustar z-index do backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.style.zIndex = '99999';
        }
        
        // Remover do DOM ao fechar
        modalDiv.addEventListener('hidden.bs.modal', () => {
            modalDiv.remove();
        });
        
    } catch (e) {
        console.error('[PITS MODAL] Erro:', e);
        mostrarToast('Erro ao carregar pits', 'error');
    }
}

function exibirSemEtapaHoje() {
    // Verificar se os elementos existem
    const infoElement = document.getElementById('infoEtapaHoje');
    const semEtapaElement = document.getElementById('semEtapaHoje');
    const grupoEtapaElement = document.getElementById('grupoEtapa');
    const botaoElement = document.getElementById('botaoIniciarQualificacao');
    
    // Se nenhum elemento foi encontrado, sair silenciosamente
    if (!infoElement && !semEtapaElement && !grupoEtapaElement && !botaoElement) {
        console.log('[ETAPA HOJE] Elementos não encontrados - script rodando em página diferente');
        return;
    }
    
    // Esconder informações
    if (infoElement) infoElement.style.display = 'none';
    if (semEtapaElement) semEtapaElement.style.display = 'block';
    if (grupoEtapaElement) grupoEtapaElement.style.display = 'none';
    if (botaoElement) botaoElement.style.display = 'none';
    
    console.log('[ETAPA HOJE] Nenhuma etapa agendada para hoje');
}

// ==================== EQUIPES PROCURANDO PILOTO - ETAPA AGENDADA ====================

async function mostrarEquipesProcurandoPiloto(etapaId, etapaInfo) {
    console.log('[EQUIPES PROCURANDO] Carregando equipes procurando piloto:', etapaId);
    
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/equipes-procurando-piloto`);
        const data = await resp.json();
        console.log('[EQUIPES PROCURANDO] Dados recebidos:', data);
        
        if (!data.sucesso || !Array.isArray(data.procurando_piloto) || data.procurando_piloto.length === 0) {
            console.log('[EQUIPES PROCURANDO] Sem equipes procurando piloto');
            return;
        }
        
        // Criar modal com equipes procurando piloto
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modalEquipesProcurando';
        modalDiv.tabIndex = '-1';
        modalDiv.setAttribute('data-bs-backdrop', 'static');
        modalDiv.setAttribute('data-bs-keyboard', 'false');
        modalDiv.style.zIndex = '100000';
        
        // Grid de equipes procurando piloto
        let equipasHtml = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; padding: 10px 0;">';
        
        data.procurando_piloto.forEach((equipe, idx) => {
            const carroInfo = equipe.carro_ativo ? `🏎️ ${equipe.carro_ativo.modelo}` : 'Sem carro ativo';
            
            equipasHtml += `
                <div style="
                    background: linear-gradient(180deg, #f0f0f0 0%, #e8e8e8 100%);
                    border: 3px solid #dc143c;
                    border-radius: 8px;
                    padding: 20px;
                    position: relative;
                    box-shadow: 0 8px 24px rgba(220, 20, 60, 0.2);
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 12px; border-bottom: 2px solid #dc143c;">
                        <div>
                            <div style="font-size: 11px; color: #dc143c; font-weight: bold; letter-spacing: 1px;">EQUIPE</div>
                            <div style="font-size: 20px; font-weight: bold; color: #000; line-height: 1;">
                                ${equipe.equipe_nome}
                            </div>
                        </div>
                        <div style="background: #dc143c; color: white; padding: 6px 12px; border-radius: 4px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold;">🔍 PROCURANDO</div>
                        </div>
                    </div>
                    
                    <div style="padding: 8px 0;">
                        <div style="font-size: 10px; color: #dc143c; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">CARRO</div>
                        <div style="font-size: 16px; font-weight: bold; color: #000;">
                            ${carroInfo}
                        </div>
                    </div>
                    
                    <div style="background: rgba(220, 20, 60, 0.1); padding: 12px; border-left: 3px solid #dc143c; border-radius: 2px; margin-bottom: 12px;">
                        <div style="font-size: 10px; color: #dc143c; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px;">TIPO</div>
                        <div style="font-size: 13px; color: #000;">
                            ${equipe.tipo_participacao === 'precisa_piloto' ? '🔍 Precisa de piloto' : '✓ Completa'}
                        </div>
                    </div>
                    
                    <button class="btn btn-danger" onclick="inscreverPilotoEmEquipe('${etapaId}', '${equipe.equipe_id}', '${equipe.equipe_nome}')" style="font-weight: bold; width: 100%;">
                        ✓ ME INSCREVER
                    </button>
                </div>
            `;
        });
        
        equipasHtml += '</div>';
        
        modalDiv.innerHTML = `
            <div class="modal-dialog modal-fullscreen" style="z-index: 100000;">
                <div class="modal-content" style="background: #fff; border: 2px solid #dc143c; z-index: 100000;">
                    <div class="modal-header" style="background: linear-gradient(90deg, #1a1a1a 0%, #333 100%); border-bottom: 3px solid #dc143c;">
                        <div>
                            <h5 class="modal-title" style="color: #dc143c; font-weight: bold; letter-spacing: 2px; font-size: 24px; margin: 0;">
                                🏁 EQUIPES PROCURANDO PILOTO
                            </h5>
                            <small style="color: #ccc; display: block; margin-top: 5px;">
                                ${etapaInfo.nome} • ${etapaInfo.data} • ${etapaInfo.hora}
                            </small>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" style="filter: brightness(0) invert(1);"></button>
                    </div>
                    <div class="modal-body" style="padding: 30px; background: #fafafa;">
                        <div style="margin-bottom: 20px; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;">
                            <strong style="color: #856404;">🔍 ${data.procurando_piloto.length} EQUIPE(S) PROCURANDO PILOTO</strong> - Clique em ME INSCREVER para participar
                        </div>
                        ${equipasHtml}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modalDiv);
        const modal = new bootstrap.Modal(modalDiv);
        modal.show();
        
        // Ajustar z-index do backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.style.zIndex = '99999';
        }
        
        // Remover do DOM ao fechar
        modalDiv.addEventListener('hidden.bs.modal', () => {
            modalDiv.remove();
        });
        
    } catch (e) {
        console.error('[EQUIPES PROCURANDO] Erro:', e);
    }
}

// ==================== PILOTOS CONFIRMADOS - ETAPA AGENDADA ====================

async function mostrarPilotosConfirmadosEtapa(etapaId, etapaInfo) {
    console.log('[PILOTOS CONFIRMADOS] Carregando pilotos confirmados para etapa agendada:', etapaId);
    
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/pilotos-confirmacao`, {
            credentials: 'include'
        });
        
        const data = await resp.json();
        console.log('[PILOTOS CONFIRMADOS] Dados recebidos:', data);
        
        if (!data.sucesso || !Array.isArray(data.pilotos) || data.pilotos.length === 0) {
            console.log('[PILOTOS CONFIRMADOS] Sem pilotos ainda');
            return;
        }
        
        // Agrupar pilotos por equipe
        const equipes = {};
        data.pilotos.forEach(piloto => {
            if (!equipes[piloto.equipe_id]) {
                equipes[piloto.equipe_id] = {
                    equipe_id: piloto.equipe_id,
                    equipe_nome: piloto.equipe_nome,
                    pilotos: []
                };
            }
            equipes[piloto.equipe_id].pilotos.push(piloto);
        });
        
        // Converter em array e ordenar
        const equipesArray = Object.values(equipes).sort((a, b) => 
            a.equipe_nome.localeCompare(b.equipe_nome)
        );
        
        // Grid de equipes com pilotos
        let equipasHtml = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; padding: 10px 0;">';
        
        equipesArray.forEach((equipe, eIdx) => {
            const pilotosCardHtml = equipe.pilotos.map((piloto, pIdx) => {
                const nomePartes = piloto.piloto_nome ? piloto.piloto_nome.split(' ') : ['Desconhecido'];
                const primeiroNome = nomePartes[0];
                const sobrenome = nomePartes.length > 1 ? nomePartes[nomePartes.length - 1] : '';
                
                return `
                    <div style="background: rgba(220, 20, 60, 0.05); padding: 12px; border-left: 3px solid #28a745; border-radius: 2px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-size: 12px; font-weight: bold; color: #000;">
                                    #${String(pIdx + 1).padStart(2, '0')} ${primeiroNome} <span style="font-size: 11px;">${sobrenome}</span>
                                </div>
                                ${piloto.carro_modelo ? `<div style="font-size: 11px; color: #666;">🏎️ ${piloto.carro_modelo}</div>` : ''}
                            </div>
                            <div style="background: #28a745; color: white; padding: 4px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">
                                ✓ CONFIRMADO
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            equipasHtml += `
                <div style="
                    background: linear-gradient(180deg, #f0f0f0 0%, #e8e8e8 100%);
                    border: 3px solid #dc143c;
                    border-radius: 8px;
                    padding: 20px;
                    position: relative;
                    box-shadow: 0 8px 24px rgba(220, 20, 60, 0.2);
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 12px; border-bottom: 2px solid #dc143c;">
                        <div>
                            <div style="font-size: 11px; color: #dc143c; font-weight: bold; letter-spacing: 1px;">EQUIPE</div>
                            <div style="font-size: 20px; font-weight: bold; color: #000; line-height: 1;">
                                ${equipe.equipe_nome}
                            </div>
                        </div>
                        <div style="background: #dc143c; color: white; padding: 6px 12px; border-radius: 4px; text-align: center;">
                            <div style="font-size: 11px; font-weight: bold;">PILOTOS</div>
                            <div style="font-size: 22px; font-weight: bold;">${equipe.pilotos.length}</div>
                        </div>
                    </div>
                    
                    <div>
                        ${pilotosCardHtml}
                    </div>
                </div>
            `;
        });
        
        equipasHtml += '</div>';
        
        // Criar modal com equipes e seus pilotos
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modalPilotosConfirmados';
        modalDiv.tabIndex = '-1';
        modalDiv.setAttribute('data-bs-backdrop', 'static');
        modalDiv.setAttribute('data-bs-keyboard', 'false');
        modalDiv.style.zIndex = '100000';
        
        modalDiv.innerHTML = `
            <div class="modal-dialog modal-fullscreen" style="z-index: 100000;">
                <div class="modal-content" style="background: #fff; border: 2px solid #dc143c; z-index: 100000;">
                    <div class="modal-header" style="background: linear-gradient(90deg, #1a1a1a 0%, #333 100%); border-bottom: 3px solid #dc143c;">
                        <div>
                            <h5 class="modal-title" style="color: #dc143c; font-weight: bold; letter-spacing: 2px; font-size: 24px; margin: 0;">
                                🏁 PILOTOS CONFIRMADOS
                            </h5>
                            <small style="color: #ccc; display: block; margin-top: 5px;">
                                ${etapaInfo.nome} • ${etapaInfo.data} • ${etapaInfo.hora}
                            </small>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" style="filter: brightness(0) invert(1);"></button>
                    </div>
                    <div class="modal-body" style="padding: 30px; background: #fafafa;">
                        <div style="margin-bottom: 20px; padding: 15px; background: #e8f5e9; border-left: 4px solid #28a745; border-radius: 4px;">
                            <strong style="color: #28a745;">✓ ${equipesArray.length} EQUIPE(S) COM PILOTOS CONFIRMADO(S) • Total: ${data.pilotos.length} piloto(s)</strong>
                        </div>
                        ${equipasHtml}
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modalDiv);
        const modal = new bootstrap.Modal(modalDiv);
        modal.show();
        
        // Ajustar z-index do backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.style.zIndex = '99999';
        }
        
        // Remover do DOM ao fechar
        modalDiv.addEventListener('hidden.bs.modal', () => {
            modalDiv.remove();
        });
        
    } catch (e) {
        console.error('[PILOTOS CONFIRMADOS] Erro:', e);
    }
}

// ==================== INSCRIÇÃO DE PILOTO EM EQUIPE ====================

async function inscreverPilotoEmEquipe(etapaId, equipeId, equipeName) {
    console.log('[INSCRICAO] Inscrevendo piloto na equipe:', equipeName);
    
    try {
        const resp = await fetch(`/api/etapas/participar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                etapa_id: etapaId,
                equipe_id: equipeId
            }),
            credentials: 'include'
        });
        
        const data = await resp.json();
        console.log('[INSCRICAO] Resposta:', data);
        
        if (data.sucesso) {
            console.log('[INSCRICAO] ✓ Piloto inscrito com sucesso!');
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalEquipesProcurando'));
            if (modal) modal.hide();
            // Mostrar modal de sucesso
            setTimeout(() => {
                // Criar modal de sucesso
                const successModal = document.createElement('div');
                successModal.className = 'modal fade';
                successModal.id = 'modalInscricaoSucesso';
                successModal.innerHTML = `
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header bg-success text-white">
                                <h5 class="modal-title">✓ Inscrição Realizada!</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>Você foi inscrito com sucesso na equipe <strong>${equipeName}</strong>!</p>
                                <p>Aguarde a confirmação do administrador.</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-success" data-bs-dismiss="modal">OK</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(successModal);
                const modalInstance = new bootstrap.Modal(successModal);
                modalInstance.show();
                // Remover modal do DOM ao fechar
                successModal.addEventListener('hidden.bs.modal', () => {
                    successModal.remove();
                });
            }, 300);
        } else {
            console.error('[INSCRICAO] ✗ Erro:', data.erro);
            // Mostrar modal de erro
            setTimeout(() => {
                // Criar modal de erro
                const errorModal = document.createElement('div');
                errorModal.className = 'modal fade';
                errorModal.id = 'modalInscricaoErro';
                errorModal.innerHTML = `
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header bg-danger text-white">
                                <h5 class="modal-title">✗ Erro na Inscrição</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>Erro: ${data.erro || 'Falha ao se inscrever'}</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-danger" data-bs-dismiss="modal">OK</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(errorModal);
                const modalInstance = new bootstrap.Modal(errorModal);
                modalInstance.show();
                // Remover modal do DOM ao fechar
                errorModal.addEventListener('hidden.bs.modal', () => {
                    errorModal.remove();
                });
            }, 300);
        }
    } catch (e) {
        console.error('[INSCRICAO] Erro:', e);
        alert('Erro ao se inscrever: ' + e.message);
    }
}

// Carregar etapa quando o admin abre a página
console.log('[QUALIFICACAO.JS] Script carregado! Aguardando DOMContentLoaded...');

document.addEventListener('DOMContentLoaded', () => {
    console.log('[QUALIFICACAO.JS] DOMContentLoaded disparado!');
    
    // Verificar se estamos na página correta (admin.html)
    const infoElement = document.getElementById('infoEtapaHoje');
    if (infoElement) {
        console.log('[QUALIFICACAO.JS] Página admin detectada - Carregando etapa de hoje...');
        carregarEtapaHoje();
    } else {
        console.log('[QUALIFICACAO.JS] Página diferente detectada - Pulando carregamento de etapa');
    }
    
    // Também quando clicar na aba de qualificacao (se existir - está em admin.html)
    const tab = document.querySelector('[href="#qualificacao"]');
    if (tab) {
        console.log('[QUALIFICACAO.JS] Aba de qualificacao encontrada');
        tab.addEventListener('click', () => {
            console.log('[QUALIFICACAO.JS] Clicou na aba - Recarregando etapa...');
            setTimeout(() => carregarEtapaHoje(), 100);
        });
    }
});

// ==================== EVENTO EM TEMPO REAL ====================

let intervaloEventoAtual = null;
let eventos = {
    ativo: false,
    etapaId: null,
    dados: null,
    ultimaAtualizacao: null
};

async function carregarEvento(etapaId) {
    console.log('[EVENTO] Carregando evento para etapa:', etapaId);
    
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/evento`);
        const data = await resp.json();
        
        if (data.sucesso && data.evento) {
            console.log('[EVENTO] Dados recebidos:', data.evento);
            eventos.dados = data.evento;
            eventos.ultimaAtualizacao = new Date();
            return data.evento;
        } else {
            console.error('[EVENTO] Erro na resposta:', data.erro);
            return null;
        }
    } catch (e) {
        console.error('[EVENTO] Erro ao carregar evento:', e);
        return null;
    }
}

async function mostrarEventoAoVivo(etapaId) {
    console.log('[EVENTO AO VIVO] Iniciando visualização do evento:', etapaId);
    
    // Carregar dados iniciais
    const evento = await carregarEvento(etapaId);
    if (!evento) {
        mostrarToast('Erro ao carregar evento', 'error');
        return;
    }
    
    // Registrar entrada
    let usuarioTipo = 'admin';
    let usuarioId = 'admin';
    let usuarioNome = 'Administrador';
    
    // Verificar se é equipe ou piloto
    const equipeId = localStorage.getItem('equipe_id');
    const pilotoId = localStorage.getItem('piloto_id');
    
    if (equipeId) {
        usuarioTipo = 'equipe';
        usuarioId = equipeId;
        usuarioNome = 'Equipe ' + localStorage.getItem('equipe_nome');
    } else if (pilotoId) {
        usuarioTipo = 'piloto';
        usuarioId = pilotoId;
        usuarioNome = localStorage.getItem('piloto_nome');
    }
    
    await fetch(`/api/etapas/${etapaId}/entrar-evento`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            tipo: usuarioTipo,
            id: usuarioId,
            nome: usuarioNome
        })
    });
    
    // Criar modal do evento
    const modalDiv = document.createElement('div');
    modalDiv.className = 'modal fade';
    modalDiv.id = 'modalEventoAoVivo';
    modalDiv.tabIndex = '-1';
    modalDiv.setAttribute('data-bs-backdrop', 'static');
    modalDiv.setAttribute('data-bs-keyboard', 'false');
    modalDiv.style.zIndex = '100000';  // Acima do banner (9999) e botão (9998)
    
    modalDiv.innerHTML = `
        <div class="modal-dialog modal-fullscreen" style="z-index: 100000;">
            <div class="modal-content" style="background: #000; border: 2px solid #ff0000;">
                <div class="modal-header" style="background: linear-gradient(90deg, #1a0000 0%, #330000 100%); border-bottom: 3px solid #ff0000;">
                    <div>
                        <h5 class="modal-title" style="color: #ff0000; font-weight: bold; letter-spacing: 2px; font-size: 24px;">
                            🏁 ${evento.etapa.campeonato_nome} - ETAPA ${evento.etapa.numero}
                        </h5>
                        <small style="color: #ccc;">Série: ${evento.etapa.serie} | Status: <span style="color: #00ff00; font-weight: bold;">${evento.etapa.status.toUpperCase().replace('_', ' ')}</span></small>
                    </div>
                    <div style="text-align: right; margin-left: auto;">
                        <div style="color: #999; font-size: 12px;">Atualizado: <span id="ultimaAtualizacao">agora</span></div>
                    </div>
                </div>
                <div class="modal-body" style="padding: 20px; background: #0a0a0a; overflow-x: auto; max-height: 75vh; overflow-y: auto; position: relative;">
                    ${evento.etapa.qualificacao_finalizada ? `
                    <div class="setas-esquerda-evento" style="position: fixed; left: 12px; top: 50%; transform: translateY(-50%); z-index: 100001; display: flex; flex-direction: column; gap: 10px;">
                        <button type="button" class="btn btn-outline-light btn-setas-evento" onclick="verResultadoQualificacao('${etapaId}')" title="Lista ordenada por nota">
                            ← Lista ordenada
                        </button>
                        <button type="button" class="btn btn-outline-warning btn-setas-evento" onclick="mostrarChaveamentoBatalhas('${etapaId}')" title="Ver chaveamento / batalhas">
                            ← Batalhas
                        </button>
                    </div>
                    ` : ''}
                    <div id="containerEventoPits" style="min-width: 100%; ${evento.etapa.qualificacao_finalizada ? 'margin-left: 140px;' : ''}">
                        <!-- Tabela de pits será renderizada aqui -->
                    </div>
                </div>
                <div class="modal-footer" style="background: #1a0000; border-top: 2px solid #ff0000;">
                    <small style="color: #999;">Total de equipes: ${evento.total_equipes}</small>
                    ${(evento.etapa.qualificacao_finalizada || evento.etapa.status === 'batalhas') ? `
                        <button type="button" class="btn btn-info me-2" onclick="verResultadoQualificacao('${etapaId}')">Ver Resultado Qualify</button>
                        <button type="button" class="btn btn-warning me-2" onclick="mostrarChaveamentoBatalhas('${etapaId}')">Ver Batalhas</button>
                        ${evento.etapa.status === 'batalhas' && usuarioTipo !== 'admin' ? `<button type="button" class="btn btn-warning" onclick="entrarBatalhas('${etapaId}')">Ir para Batalhas</button>` : ''}
                    ` : ''}
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modalDiv);
    const modal = new bootstrap.Modal(modalDiv, { backdrop: 'static', keyboard: false });
    modal.show();
    
    // Ajustar z-index do backdrop criado pelo Bootstrap
    const backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) {
        backdrop.style.zIndex = '99999';
    }
    
    // Renderizar pits iniciais
    renderizarPitsEvento(evento.equipes, evento.etapa);
    
    // Iniciar auto-refresh
    eventos.ativo = true;
    eventos.etapaId = etapaId;
    
    if (intervaloEventoAtual) clearInterval(intervaloEventoAtual);
    
    intervaloEventoAtual = setInterval(async () => {
        const eventoAtualizado = await carregarEvento(etapaId);
        if (eventoAtualizado && eventoAtualizado.equipes) {
            renderizarPitsEvento(eventoAtualizado.equipes, eventoAtualizado.etapa);
            atualizarTimestampEvento();
        }
    }, 2000); // Atualiza a cada 2 segundos
    
    // Limpar ao fechar modal
    modalDiv.addEventListener('hidden.bs.modal', () => {
        console.log('[EVENTO] Fechando evento ao vivo');
        eventos.ativo = false;
        if (intervaloEventoAtual) clearInterval(intervaloEventoAtual);
        modalDiv.remove();
        
        // Restaurar botão flutuante de notificação
        if (typeof mostrarBotaoFlutante === 'function') {
            mostrarBotaoFlutante();
        }
    });
}

function renderizarPitsEvento(equipes, etapaInfo = null) {
    console.log('[EVENTO RENDER] Renderizando', equipes.length, 'equipes em tabela');
    
    const container = document.getElementById('containerEventoPits');
    if (!container) return;

    // Determinar tipo de usuário
    let isAdmin = true;
    const equipeId = localStorage.getItem('equipe_id');
    const pilotoId = localStorage.getItem('piloto_id');
    
    if (equipeId || pilotoId) {
        isAdmin = false;  // Não é admin, é equipe ou piloto
    }

    // Ordenar equipes - se qualificação finalizada, ordenar por pontuação
    let equipesOrdenadas;
    const qualificacaoFinalizada = etapaInfo?.qualificacao_finalizada || false;
    
    if (qualificacaoFinalizada) {
        // Ordenar por pontuação total (desc) + nota linha (desc)
        equipesOrdenadas = [...equipes].sort((a, b) => {
            const totalA = (a.nota_linha || 0) + (a.nota_angulo || 0) + (a.nota_estilo || 0);
            const totalB = (b.nota_linha || 0) + (b.nota_angulo || 0) + (b.nota_estilo || 0);
            
            // Primeiro critério: total decrescente
            if (totalB !== totalA) {
                return totalB - totalA;
            }
            
            // Segundo critério: nota linha decrescente
            const linhaA = a.nota_linha || 0;
            const linhaB = b.nota_linha || 0;
            return linhaB - linhaA;
        });
        console.log('[EVENTO RENDER] Qualificação finalizada - ordenando por pontuação');
    } else {
        // Ordenar por ordem_qualificacao
        equipesOrdenadas = [...equipes].sort((a, b) => {
            const ordemA = a.ordem_qualificacao || Infinity;
            const ordemB = b.ordem_qualificacao || Infinity;
            return ordemA - ordemB;
        });
        console.log('[EVENTO RENDER] Qualificação em andamento - ordenando por ordem_qualificacao');
    }

    // Criar tabela com scroll horizontal se necessário
    let html = `
        <table style="width: 100%; border-collapse: collapse; color: #fff; font-family: Arial, sans-serif;">
            <thead style="position: sticky; top: 0;">
                <tr style="background: linear-gradient(90deg, #1a0000 0%, #330000 100%); border: 2px solid #ff0000;">
                    <th style="padding: 14px 10px; text-align: center; border: 1px solid #ff0000; color: #ff0000; font-weight: bold; min-width: 60px;">${qualificacaoFinalizada ? 'POS' : 'QUAL'}</th>
                    <th style="padding: 14px 10px; text-align: left; border: 1px solid #ff0000; color: #ff0000; font-weight: bold; min-width: 200px;">EQUIPE</th>
                    <th style="padding: 14px 10px; text-align: left; border: 1px solid #ff0000; color: #ff0000; font-weight: bold; min-width: 150px;">PILOTO</th>
                    <th style="padding: 14px 10px; text-align: center; border: 1px solid #ff0000; color: #ff0000; font-weight: bold; min-width: 100px;">NOTA LINHA</th>
                    <th style="padding: 14px 10px; text-align: center; border: 1px solid #ff0000; color: #ff0000; font-weight: bold; min-width: 100px;">NOTA ÂNGULO</th>
                    <th style="padding: 14px 10px; text-align: center; border: 1px solid #ff0000; color: #ff0000; font-weight: bold; min-width: 100px;">NOTA ESTILO</th>
                    <th style="padding: 14px 10px; text-align: center; border: 1px solid #ff0000; color: #ff0000; font-weight: bold; min-width: 100px;">TOTAL</th>
                </tr>
            </thead>
            <tbody>
    `;

    equipesOrdenadas.forEach((eq, idx) => {
        const ordemQualif = eq.ordem_qualificacao ? String(eq.ordem_qualificacao).padStart(2, '0') : '—';
        const pilotoNome = eq.piloto_nome ? eq.piloto_nome : '⚠️ SEM PILOTO';
        const notaLinha = eq.nota_linha || 0;
        const notaAngulo = eq.nota_angulo || 0;
        const notaEstilo = eq.nota_estilo || 0;
        const somaNotas = parseInt(notaLinha) + parseInt(notaAngulo) + parseInt(notaEstilo);
        
        // Se volta_status = 'em_andamento', usar background branco para destacar
        const ehProximo = eq.volta_status === 'em_andamento';
        const backgroundColor = ehProximo 
            ? 'rgba(255, 255, 255, 0.1)' 
            : (idx % 2 === 0 ? 'rgba(0,0,0,0.5)' : 'rgba(255,0,0,0.08)');
        
        const borderColor = ehProximo ? '2px solid #ffffff' : '1px solid rgba(255,0,0,0.2)';
        const statusDisplay = ehProximo ? '<span style="color: #ffffff; font-weight: bold; font-size: 12px;">▶ ANDANDO</span>' : '';
        
        // Inputs desabilitados se não for admin
        const disabledAttr = !isAdmin ? 'disabled' : '';
        const inputBg = !isAdmin ? 'rgba(100,100,100,0.3)' : 'rgba(0,0,0,0.7)';
        const inputCursor = !isAdmin ? 'not-allowed' : 'pointer';
        
        html += `
            <tr style="background: ${backgroundColor}; border-bottom: ${borderColor}; transition: background 0.3s ease;" onmouseover="this.style.background='rgba(255,0,0,0.15)'" onmouseout="this.style.background='${backgroundColor}'">
                <td style="padding: 12px 10px; border: 1px solid rgba(255,0,0,0.2); color: #ff0000; font-weight: bold; text-align: center; font-size: 18px; font-family: 'Courier New';">
                    ${ordemQualif}
                    ${statusDisplay}
                </td>
                <td style="padding: 12px 10px; border: 1px solid rgba(255,0,0,0.2); font-weight: bold; font-size: 15px;">${eq.equipe_nome}</td>
                <td style="padding: 12px 10px; border: 1px solid rgba(255,0,0,0.2); font-size: 14px; color: #ccc;">${pilotoNome}</td>
                <td style="padding: 12px 10px; border: 1px solid rgba(255,0,0,0.2); text-align: center;">
                    <input type="number" value="${notaLinha || ''}" placeholder="0" min="0" max="40" 
                        ${disabledAttr}
                        style="width: 80px; padding: 6px 4px; border: 1px solid #ff0000; background: ${inputBg}; color: #00ff00; text-align: center; font-weight: bold; border-radius: 3px; cursor: ${inputCursor};" 
                        onchange="salvarNotaEquipe('${eq.equipe_id}', 'linha', this.value)">
                </td>
                <td style="padding: 12px 10px; border: 1px solid rgba(255,0,0,0.2); text-align: center;">
                    <input type="number" value="${notaAngulo || ''}" placeholder="0" min="0" max="30" 
                        ${disabledAttr}
                        style="width: 80px; padding: 6px 4px; border: 1px solid #ff0000; background: ${inputBg}; color: #00ff00; text-align: center; font-weight: bold; border-radius: 3px; cursor: ${inputCursor};" 
                        onchange="salvarNotaEquipe('${eq.equipe_id}', 'angulo', this.value)">
                </td>
                <td style="padding: 12px 10px; border: 1px solid rgba(255,0,0,0.2); text-align: center;">
                    <input type="number" value="${notaEstilo || ''}" placeholder="0" min="0" max="30" 
                        ${disabledAttr}
                        style="width: 80px; padding: 6px 4px; border: 1px solid #ff0000; background: ${inputBg}; color: #00ff00; text-align: center; font-weight: bold; border-radius: 3px; cursor: ${inputCursor};" 
                        onchange="salvarNotaEquipe('${eq.equipe_id}', 'estilo', this.value)">
                </td>
                <td style="padding: 12px 10px; border: 1px solid rgba(255,0,0,0.2); text-align: center;">
                    <span style="color: #00ffff; font-weight: bold; font-size: 14px;">${somaNotas}</span>
                </td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function salvarNotaEquipe(equipeId, tipoNota, valor) {
    if (!eventos.etapaId) return;
    
    // Verificar se é admin
    const equipeId_check = localStorage.getItem('equipe_id');
    const pilotoId_check = localStorage.getItem('piloto_id');
    
    if (equipeId_check || pilotoId_check) {
        mostrarToast('❌ Apenas admins podem salvar notas', 'error');
        return;
    }
    
    const dados = {};
    dados[`nota_${tipoNota}`] = parseInt(valor) || 0;
    
    console.log(`[NOTAS] Salvando ${tipoNota}:`, valor, 'para equipe:', equipeId);
    
    fetch(`/api/etapas/${eventos.etapaId}/notas/${equipeId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
    })
    .then(r => {
        if (r.status === 403) {
            throw new Error('Apenas admins podem salvar notas');
        }
        return r.json();
    })
    .then(data => {
        if (data.sucesso) {
            console.log(`[NOTAS] ✓ ${tipoNota} salvo com sucesso`);
            mostrarToast(`✓ Nota de ${tipoNota} salva`, 'success');
        } else {
            console.error('[NOTAS] Erro:', data.erro);
            mostrarToast('❌ ' + data.erro, 'error');
        }
    })
    .catch(e => {
        console.error('[NOTAS] Erro na requisição:', e);
        mostrarToast('❌ Erro ao salvar:', 'error');
    });
}

function atualizarTimestampEvento() {
    const el = document.getElementById('ultimaAtualizacao');
    if (el) {
        const agora = new Date();
        el.textContent = agora.toLocaleTimeString('pt-BR');
    }
}

// ===== FUNÇÕES PARA TABELA DE VOLTAS EDITÁVEL (ADMIN) =====

async function atualizarTabelaVoltasAdmin() {
    const etapaId = document.getElementById('etapaIdAtual').value;
    if (!etapaId) {
        mostrarToast('❌ Nenhuma etapa selecionada', 'error');
        return;
    }
    
    try {
        console.log('[VOLTA ADMIN] Carregando dados da etapa:', etapaId);
        const resp = await fetch(`/api/etapas/${etapaId}/evento`);
        const data = await resp.json();
        
        if (data.sucesso && data.evento) {
            renderizarVoltasAdmin(data.evento.equipes, data.evento.etapa);
            mostrarToast('✓ Tabela atualizada', 'success');
        } else {
            mostrarToast('❌ Erro ao carregar dados', 'error');
        }
    } catch (e) {
        console.error('[VOLTA ADMIN] Erro:', e);
        mostrarToast('❌ Erro de conexão', 'error');
    }
}

// Tornar função global para acesso do HTML
window.atualizarTabelaVoltasAdmin = atualizarTabelaVoltasAdmin;

async function carregarTabelaVoltasAdmin(etapaId) {
    if (!etapaId) {
        mostrarToast('❌ ID da etapa não fornecido', 'error');
        return;
    }
    
    try {
        console.log('[VOLTA ADMIN] Carregando dados da etapa:', etapaId);
        const resp = await fetch(`/api/etapas/${etapaId}/evento`);
        const data = await resp.json();
        
        if (data.sucesso && data.evento) {
            renderizarVoltasAdmin(data.evento.equipes, data.evento.etapa);
            
            // Mostrar o container da tabela
            const containerVoltas = document.getElementById('containerVoltasAdmin');
            if (containerVoltas) {
                containerVoltas.style.display = 'block';
            }
            
            // Garantir que a aba "Fazer Etapa" esteja ativa
            const abaFazerEtapa = document.querySelector('a[href="#fazer-etapa"]');
            if (abaFazerEtapa) {
                abaFazerEtapa.click();
                console.log('[VOLTA ADMIN] Aba "Fazer Etapa" garantida como ativa');
            }
            
            const mensagem = data.evento.etapa.qualificacao_finalizada 
                ? '✓ Qualificação finalizada! A tabela mostra os resultados.' 
                : '✓ Interface de qualificação pronta! Você pode editar as notas das equipes.';
            mostrarToast(mensagem, data.evento.etapa.qualificacao_finalizada ? 'info' : 'success');
        } else {
            mostrarToast('❌ Erro ao carregar dados', 'error');
        }
    } catch (e) {
        console.error('[VOLTA ADMIN] Erro:', e);
        mostrarToast('❌ Erro de conexão', 'error');
    }
}

function renderizarVoltasAdmin(equipes, etapaInfo) {
    console.log('[VOLTA ADMIN] Renderizando', equipes.length, 'equipes');
    console.log('[VOLTA ADMIN] Ordem recebida:', equipes.map(e => ({ qual: e.ordem_qualificacao, equipe: e.equipe_nome })));
    console.log('[VOLTA ADMIN] etapaInfo:', etapaInfo);
    console.log('[VOLTA ADMIN] Qualificação finalizada:', etapaInfo?.qualificacao_finalizada);
    
    const container = document.getElementById('tabelaVoltasAdmin');
    if (!container) return;

    const qualificacaoFinalizada = etapaInfo?.qualificacao_finalizada || false;

    // Se qualificação finalizada, ordenar por pontuação (total desc, linha desc)
    let equipesOrdenadas = [...equipes];
    if (qualificacaoFinalizada) {
        equipesOrdenadas.sort((a, b) => {
            const totalA = (a.nota_linha || 0) + (a.nota_angulo || 0) + (a.nota_estilo || 0);
            const totalB = (b.nota_linha || 0) + (b.nota_angulo || 0) + (b.nota_estilo || 0);
            
            // Primeiro critério: total decrescente
            if (totalB !== totalA) {
                return totalB - totalA;
            }
            
            // Segundo critério: nota linha decrescente
            const linhaA = a.nota_linha || 0;
            const linhaB = b.nota_linha || 0;
            return linhaB - linhaA;
        });
        console.log('[VOLTA ADMIN] Equipes reordenadas por pontuação:', equipesOrdenadas.map(e => ({ 
            equipe: e.equipe_nome, 
            total: (e.nota_linha || 0) + (e.nota_angulo || 0) + (e.nota_estilo || 0),
            linha: e.nota_linha || 0
        })));
    }

    // Criar tabela com scroll - Tema Branco e Vermelho
    let html = `
        <table style="width: 100%; border-collapse: collapse; color: #333; font-family: Arial, sans-serif; background: #fff; border: 3px solid #dc3545;">
            <thead style="position: sticky; top: 0;">
                <tr style="background: linear-gradient(90deg, #dc3545 0%, #b02a37 100%); border: 3px solid #dc3545;">
                    <th style="padding: 12px 10px; text-align: center; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 60px; font-size: 14px;">QUAL</th>
                    <th style="padding: 12px 10px; text-align: left; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 200px; font-size: 14px;">EQUIPE</th>
                    <th style="padding: 12px 10px; text-align: left; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 150px; font-size: 14px;">PILOTO</th>
                    <th style="padding: 12px 10px; text-align: center; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 120px; font-size: 14px;">NOTA LINHA</th>
                    <th style="padding: 12px 10px; text-align: center; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 120px; font-size: 14px;">NOTA ÂNGULO</th>
                    <th style="padding: 12px 10px; text-align: center; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 120px; font-size: 14px;">NOTA ESTILO</th>
                    <th style="padding: 12px 10px; text-align: center; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 100px; font-size: 14px;">TOTAL</th>
                    <th style="padding: 12px 10px; text-align: center; border: 2px solid #dc3545; color: #fff; font-weight: bold; min-width: 100px; font-size: 14px;">STATUS</th>
                </tr>
            </thead>
            <tbody>
    `;

    equipesOrdenadas.forEach((eq, idx) => {
        const ordemQualif = eq.ordem_qualificacao ? String(eq.ordem_qualificacao).padStart(2, '0') : '—';
        const pilotoNome = eq.piloto_nome ? eq.piloto_nome : '⚠️ SEM PILOTO';
        const notaLinha = eq.nota_linha || 0;
        const notaAngulo = eq.nota_angulo || 0;
        const notaEstilo = eq.nota_estilo || 0;
        const somaNotas = parseInt(notaLinha) + parseInt(notaAngulo) + parseInt(notaEstilo);
        const voltaStatus = eq.volta_status || 'aguardando';
        
        // Lógica para determinar status baseado em quem ainda não foi avaliado
        let statusColor = '#666';  // cinza/aguardando
        let statusText = '○ AGUARDANDO';
        let isCurrentDriver = false;
        let isNextDriver = false;
        
        // Variáveis para estilo da linha
        let backgroundColor = '#fff';  // branco padrão
        let borderStyle = '';
        let fontWeight = 'normal';
        
        // Encontrar primeiro piloto que ainda não foi avaliado (soma = 0)
        let primeiroNaoAvaliado = -1;
        let proximoNaoAvaliado = -1;
        
        for (let i = 0; i < equipesOrdenadas.length; i++) {
            const eqCheck = equipesOrdenadas[i];
            const nl = eqCheck.nota_linha || 0;
            const na = eqCheck.nota_angulo || 0;
            const ne = eqCheck.nota_estilo || 0;
            const somaCheck = parseInt(nl) + parseInt(na) + parseInt(ne);
            
            if (somaCheck === 0) {
                if (primeiroNaoAvaliado === -1) {
                    primeiroNaoAvaliado = i;
                } else if (proximoNaoAvaliado === -1) {
                    proximoNaoAvaliado = i;
                    break;
                }
            }
        }
        
        // Verificar se este é o piloto atual ou próximo
        if (idx === primeiroNaoAvaliado) {
            isCurrentDriver = true;
            statusColor = '#007bff';  // azul
            statusText = '🎯 SUA VEZ';
        } else if (idx === proximoNaoAvaliado) {
            isNextDriver = true;
            statusColor = '#ffc107';  // amarelo
            statusText = '⏭️ PRÓXIMO';
        } else if (somaNotas > 0) {
            // Piloto já foi avaliado
            statusColor = '#28a745';  // verde
            statusText = '✓ AVALIADO';
        } else {
            // Manter status original se não for o atual ou próximo
            if (voltaStatus === 'andando') {
                statusColor = '#28a745';  // verde
                statusText = '▶ ANDANDO';
            } else if (voltaStatus === 'proximo') {
                statusColor = '#ffc107';  // amarelo
                statusText = '→ PRÓXIMO';
            } else if (voltaStatus === 'finalizado') {
                statusColor = '#dc3545';  // vermelho
                statusText = '✓ FINALIZADO';
            }
        }
        
        // Quando qualificação finalizada, mostrar posição baseada na ordenação
        const posicaoExibida = qualificacaoFinalizada ? String(idx + 1).padStart(2, '0') : ordemQualif;
        
        if (isCurrentDriver) {
            backgroundColor = '#e3f2fd';  // azul claro
            borderStyle = 'border-left: 4px solid #007bff;';
            fontWeight = 'bold';
        } else if (isNextDriver) {
            backgroundColor = '#fff3cd';  // amarelo claro
            borderStyle = 'border-left: 4px solid #ffc107;';
        }
        
        html += `
            <tr style="background: ${backgroundColor}; border-bottom: 1px solid #dee2e6; transition: background 0.3s ease; ${borderStyle}" onmouseover="this.style.background='#e9ecef'" onmouseout="this.style.background='${backgroundColor}'">
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; color: #dc3545; font-weight: ${isCurrentDriver ? 'bold' : 'bold'}; text-align: center; font-size: 18px; font-family: 'Courier New';">${posicaoExibida}</td>
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; font-weight: ${fontWeight}; font-size: 15px; color: #333;">${eq.equipe_nome}</td>
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; font-size: 14px; color: #666; font-weight: ${fontWeight};">${pilotoNome}</td>
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; text-align: center;">
                    ${qualificacaoFinalizada ? 
                        `<span style="color: #dc3545; font-weight: bold; font-size: 16px;">${notaLinha}</span>` :
                        `<input type="number" value="${notaLinha}" placeholder="0" min="0" max="40" 
                            style="width: 90px; padding: 6px 4px; border: 2px solid #dc3545; background: #fff; color: #333; text-align: center; font-weight: bold; border-radius: 3px;" 
                            onchange="salvarNotaEquipeAdmin('${eq.equipe_id}', 'linha', this.value)">`
                    }
                </td>
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; text-align: center;">
                    ${qualificacaoFinalizada ? 
                        `<span style="color: #dc3545; font-weight: bold; font-size: 16px;">${notaAngulo}</span>` :
                        `<input type="number" value="${notaAngulo}" placeholder="0" min="0" max="30" 
                            style="width: 90px; padding: 6px 4px; border: 2px solid #dc3545; background: #fff; color: #333; text-align: center; font-weight: bold; border-radius: 3px;" 
                            onchange="salvarNotaEquipeAdmin('${eq.equipe_id}', 'angulo', this.value)">`
                    }
                </td>
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; text-align: center;">
                    ${qualificacaoFinalizada ? 
                        `<span style="color: #dc3545; font-weight: bold; font-size: 16px;">${notaEstilo}</span>` :
                        `<input type="number" value="${notaEstilo}" placeholder="0" min="0" max="30" 
                            style="width: 90px; padding: 6px 4px; border: 2px solid #dc3545; background: #fff; color: #333; text-align: center; font-weight: bold; border-radius: 3px;" 
                            onchange="salvarNotaEquipeAdmin('${eq.equipe_id}', 'estilo', this.value)">`
                    }
                </td>
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; text-align: center;">
                    <span style="color: #dc3545; font-weight: bold; font-size: 14px;">${somaNotas}</span>
                </td>
                <td style="padding: 12px 10px; border: 1px solid #dee2e6; text-align: center;">
                    <span style="color: ${statusColor}; font-weight: bold; font-size: 12px;">${statusText}</span>
                </td>
            </tr>
        `;
    });

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;
    
    // Verificar se deve mostrar o botão de finalizar qualificação
    const temAvaliacoes = equipes.some(eq => {
        const nl = eq.nota_linha || 0;
        const na = eq.nota_angulo || 0;
        const ne = eq.nota_estilo || 0;
        return (nl + na + ne) > 0;
    });
    
    const botaoFinalizar = document.getElementById('botaoFinalizarQualificacao');
    if (botaoFinalizar) {
        if (qualificacaoFinalizada) {
            botaoFinalizar.style.display = 'none';
        } else {
            botaoFinalizar.style.display = temAvaliacoes ? 'block' : 'none';
        }
    }
    
    // Se qualificação finalizada, mostrar mensagem
    if (qualificacaoFinalizada) {
        const mensagemFinalizada = document.createElement('div');
        mensagemFinalizada.id = 'mensagemQualificacaoFinalizada';
        mensagemFinalizada.style.cssText = `
            background: #d4edda; 
            color: #155724; 
            padding: 15px; 
            border: 1px solid #c3e6cb; 
            border-radius: 5px; 
            margin: 20px 0; 
            text-align: center;
            font-weight: bold;
        `;
        mensagemFinalizada.innerHTML = '🏁 Qualificação Finalizada! As notas não podem mais ser alteradas. A etapa continua para as batalhas.';
        
        // Inserir após a tabela
        const tabela = document.getElementById('tabelaVoltasAdmin');
        if (tabela && tabela.parentNode) {
            // Remover mensagem anterior se existir
            const mensagemAnterior = document.getElementById('mensagemQualificacaoFinalizada');
            if (mensagemAnterior) {
                mensagemAnterior.remove();
            }
            tabela.parentNode.insertBefore(mensagemFinalizada, tabela.nextSibling);
        }
    } else {
        // Remover mensagem se existir
        const mensagemAnterior = document.getElementById('mensagemQualificacaoFinalizada');
        if (mensagemAnterior) {
            mensagemAnterior.remove();
        }
    }

    // Se qualificação finalizada, mostrar resultado e chaveamento
    if (qualificacaoFinalizada) {
        const secaoResultado = document.getElementById('secaoResultadoQualificacao');
        const secaoChaveamento = document.getElementById('secaoChaveamentoBatalhas');
        const etapaId = document.getElementById('etapaIdAtual')?.value || etapaInfo?.id;
        if (secaoResultado) secaoResultado.style.display = 'block';
        if (secaoChaveamento) secaoChaveamento.style.display = 'block';
        if (etapaId && typeof carregarResultadoQualificacaoInline === 'function') carregarResultadoQualificacaoInline(etapaId);
        if (etapaId && typeof carregarChaveamentoBatalhasInline === 'function') carregarChaveamentoBatalhasInline(etapaId);
    } else {
        const secaoResultado = document.getElementById('secaoResultadoQualificacao');
        const secaoChaveamento = document.getElementById('secaoChaveamentoBatalhas');
        if (secaoResultado) secaoResultado.style.display = 'none';
        if (secaoChaveamento) secaoChaveamento.style.display = 'none';
    }
}

async function salvarNotaEquipeAdmin(equipeId, tipoNota, valor) {
    const etapaId = document.getElementById('etapaIdAtual').value;
    if (!etapaId) return;
    
    const dados = {};
    dados[`nota_${tipoNota}`] = parseInt(valor) || 0;
    
    console.log(`[VOLTA ADMIN] Salvando ${tipoNota}:`, valor, 'para equipe:', equipeId);
    
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/notas/${equipeId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        
        const data = await resp.json();
        
        if (data.sucesso) {
            console.log(`[VOLTA ADMIN] ✓ ${tipoNota} salvo com sucesso`);
            mostrarToast(`✓ ${tipoNota} salva`, 'success');
            // Atualizar tabela com novo status
            setTimeout(() => atualizarTabelaVoltasAdmin(), 500);
        } else {
            console.error('[VOLTA ADMIN] Erro:', data.erro);
            mostrarToast('❌ ' + data.erro, 'error');
        }
    } catch (e) {
        console.error('[VOLTA ADMIN] Erro na requisição:', e);
        mostrarToast('❌ Erro ao salvar', 'error');
    }
}

// Tornar função global para acesso do HTML
window.salvarNotaEquipeAdmin = salvarNotaEquipeAdmin;

async function finalizarQualificacao() {
    const etapaId = document.getElementById('etapaIdAtual').value;
    if (!etapaId) {
        mostrarToast('❌ Nenhuma etapa selecionada', 'error');
        return;
    }
    
    if (!confirm('Tem certeza que deseja finalizar a qualificação? Esta ação não pode ser desfeita!')) {
        return;
    }
    
    try {
        console.log('[VOLTA ADMIN] Finalizando qualificação para etapa:', etapaId);
        const resp = await fetch(`/api/admin/finalizar-qualificacao/${etapaId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await resp.json();
        
        if (data.sucesso) {
            mostrarToast('✓ Qualificação finalizada! Enviando para Challonge...', 'success');
            try {
                const respCh = await fetch(`/api/etapas/${etapaId}/enviar-challonge`, { method: 'POST', credentials: 'include' });
                const dataCh = await respCh.json();
                if (dataCh.sucesso) {
                    mostrarToast(dataCh.bracket_pendente ? '⚠ Torneio criado. Inicie manualmente no Challonge (link disponível).' : '✓ Torneio criado no Challonge!', dataCh.bracket_pendente ? 'warning' : 'success');
                } else if (dataCh.erro) {
                    console.error('[CHALLONGE] 400/erro:', dataCh.erro);
                    mostrarToast('⚠ Challonge: ' + dataCh.erro, 'error');
                }
            } catch (e) {
                console.error('[CHALLONGE] Exceção:', e);
                mostrarToast('⚠ Erro ao enviar para Challonge', 'error');
            }
            setTimeout(() => {
                if (typeof carregarResultadoQualificacaoInline === 'function') carregarResultadoQualificacaoInline(etapaId);
                if (typeof carregarChaveamentoBatalhasInline === 'function') carregarChaveamentoBatalhasInline(etapaId);
                atualizarTabelaVoltasAdmin();
            }, 500);
        } else {
            mostrarToast('❌ ' + data.erro, 'error');
        }
    } catch (e) {
        console.error('[VOLTA ADMIN] Erro:', e);
        mostrarToast('❌ Erro ao finalizar', 'error');
    }
}

// Tornar função global para acesso do HTML
window.finalizarQualificacao = finalizarQualificacao;

function escapeHtml(s) {
    if (s == null) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

/** Carrega resultado da qualificação na seção inline da página admin Fazer Etapa. */
async function carregarResultadoQualificacaoInline(etapaId) {
    const secao = document.getElementById('secaoResultadoQualificacao');
    const lista = document.getElementById('listaResultadoQualificacao');
    if (!secao || !lista) return;
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/classificacao-final`);
        const data = await resp.json();
        if (!data.sucesso || !data.classificacao || !data.classificacao.length) {
            lista.innerHTML = '<p class="text-muted p-3 mb-0">Nenhum resultado ainda.</p>';
            secao.style.display = 'block';
            return;
        }
        let html = '<table class="table table-dark table-striped table-sm mb-0"><thead><tr><th>#</th><th>Equipe</th><th>Piloto</th><th>Linha</th><th>Ângulo</th><th>Estilo</th><th>Total</th></tr></thead><tbody>';
        data.classificacao.forEach((item, i) => {
            html += `<tr><td>${i + 1}</td><td>${escapeHtml(item.equipe_nome || '-')}</td><td>${escapeHtml(item.piloto_nome || '-')}</td><td>${item.nota_linha}</td><td>${item.nota_angulo}</td><td>${item.nota_estilo}</td><td><strong>${item.total_notas}</strong></td></tr>`;
        });
        html += '</tbody></table>';
        lista.innerHTML = html;
        secao.style.display = 'block';
    } catch (e) {
        lista.innerHTML = '<p class="text-danger p-3 mb-0">Erro ao carregar classificação.</p>';
        secao.style.display = 'block';
    }
}

/** Carrega chaveamento via bracket-challonge na seção inline, com cards. */
async function carregarChaveamentoBatalhasInline(etapaId) {
    if (typeof carregarResultadoQualificacaoInline === 'function') carregarResultadoQualificacaoInline(etapaId);
    const secao = document.getElementById('secaoChaveamentoBatalhas');
    const container = document.getElementById('chaveamentoBatalhasInline');
    if (!secao || !container) return;
    try {
        const respCh = await fetch(`/api/etapas/${etapaId}/bracket-challonge`);
        const dataCh = await respCh.json();
        if (dataCh.sucesso && dataCh.bracket && dataCh.bracket.length > 0) {
            const bracketData = { bracket: dataCh.bracket, url: dataCh.challonge_url, etapaId };
            container.innerHTML = renderizarBracketChallonge(bracketData);
        } else if (dataCh.challonge_url) {
            container.innerHTML = '<p class="text-muted mb-0">Chaveamento será carregado do Challonge após iniciar o torneio. <a href="' + escapeHtml(dataCh.challonge_url) + '" target="_blank">Abrir no Challonge</a></p>';
        } else {
            container.innerHTML = '<p class="text-muted mb-0">Finalize a qualificação e envie para o Challonge para ver o chaveamento.</p>';
        }
        secao.style.display = 'block';
    } catch (e) {
        container.innerHTML = '<p class="text-danger mb-0">Erro ao carregar chaveamento.</p>';
        secao.style.display = 'block';
    }
}

function calcularColocacoesBracket(bracket) {
    if (!bracket || bracket.length === 0) return [];
    const partMap = {};
    (bracket || []).forEach(fase => {
        (fase.matches || []).forEach(m => {
            const p1 = m.player1 || {}; const p2 = m.player2 || {};
            if (p1.id) partMap[String(p1.id)] = p1.name || 'TBD';
            if (p2.id) partMap[String(p2.id)] = p2.name || 'TBD';
        });
    });
    const ultimaFase = bracket[bracket.length - 1];
    const ultimoTemVencedor = ultimaFase && (ultimaFase.matches || []).some(m => !!m.winner_id);
    if (!ultimoTemVencedor) return [];
    const col = [];
    const used = new Set();
    for (let i = bracket.length - 1; i >= 0; i--) {
        const fase = bracket[i];
        (fase.matches || []).forEach(m => {
            if (i === bracket.length - 1) {
                if (m.winner_id) { col.push({ posicao: 1, name: partMap[String(m.winner_id)] || 'TBD' }); used.add(String(m.winner_id)); }
                const loserId = String(m.winner_id) === String(m.player1_id) ? m.player2_id : m.player1_id;
                if (loserId) { col.push({ posicao: 2, name: partMap[String(loserId)] || 'TBD' }); used.add(String(loserId)); }
            } else {
                const loserId = m.winner_id ? (String(m.winner_id) === String(m.player1_id) ? m.player2_id : m.player1_id) : null;
                if (loserId && !used.has(String(loserId))) { col.push({ posicao: col.length + 1, name: partMap[String(loserId)] || 'TBD' }); used.add(String(loserId)); }
            }
        });
    }
    return col.sort((a, b) => a.posicao - b.posicao);
}

function renderizarBracketChallonge(bracketData) {
    const { bracket, url, etapaId } = bracketData;
    let html = '';
    if (url) html += `<p class="mb-3"><a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="text-info"><i class="fas fa-external-link-alt me-1"></i>Abrir no Challonge</a> <small class="text-muted">(dados do Challonge • clique no card para definir vencedor)</small></p>`;
    html += '<div class="bracket-challonge-vertical" style="display: inline-flex; flex-direction: row; gap: 8px; align-items: stretch; min-width: max-content;">';
    (bracket || []).forEach((fase, faseIdx) => {
        html += '<div class="bracket-coluna" style="display: flex; flex-direction: column; gap: 16px; flex-shrink: 0; min-width: 240px;">';
        html += `<div class="bracket-fase-titulo" style="text-align: center; color: #ffc107; font-weight: bold; font-size: 0.95rem; padding: 6px 0;">${escapeHtml(fase.label || '')}</div>`;
        (fase.matches || []).forEach((m, idx) => {
            const p1 = m.player1 || {};
            const p2 = m.player2 || {};
            const w1 = m.winner_id && String(m.winner_id) === String(p1.id);
            const w2 = m.winner_id && String(m.winner_id) === String(p2.id);
            const batalhaNum = (fase.matches || []).length > 1 ? ` ${idx + 1}` : '';
            const matchJson = JSON.stringify({ match_id: m.match_id, player1: p1, player2: p2, winner_id: m.winner_id, round: m.round || 1 }).replace(/"/g, '&quot;');
            const proxFase = bracket[faseIdx + 1];
            let linhaAvanca = '';
            if (proxFase && (proxFase.matches || []).length > 0) {
                const proxIdx = Math.floor(idx / 2);
                const proxLabel = (proxFase.matches || []).length > 1 ? (proxFase.label || '') + ' ' + (proxIdx + 1) : (proxFase.label || '');
                linhaAvanca = '<div class="mt-1 pt-1" style="font-size: 0.75rem; color: #ffc107; border-top: 1px dashed rgba(255,193,7,0.4); text-align: center;">→ Vencedor avança para: ' + escapeHtml(proxLabel) + '</div>';
            } else if (faseIdx === bracket.length - 1) {
                linhaAvanca = '<div class="mt-1 pt-1" style="font-size: 0.75rem; color: #ffc107; border-top: 1px dashed rgba(255,193,7,0.4); text-align: center;">🏆 Final</div>';
            }
            html += `
            <div class="card border-warning batalha-card batalha-card-clickable" data-etapa-id="${escapeHtml(etapaId || '')}" data-match="${matchJson}" style="min-width: 220px; background: #1e1e1e; border-width: 2px; flex-shrink: 0; cursor: pointer;">
                <div class="card-header py-2 text-center" style="background: linear-gradient(135deg, #2d2d2d, #1a1a1a); color: #ffc107; font-weight: bold; font-size: 0.85rem;">
                    &#x2694; ${escapeHtml(fase.label || '')}${batalhaNum}
                </div>
                <div class="card-body p-2">
                    <div class="d-flex align-items-center justify-content-between py-2 px-2 rounded ${w1 ? 'bg-warning bg-opacity-25 border border-warning' : 'bg-dark'}" style="min-height: 38px;">
                        <span class="badge bg-secondary me-2">${p1.seed || '-'}</span>
                        <span class="flex-grow-1 text-truncate" style="color: #fff;" title="${escapeHtml(p1.name || 'TBD')}">${escapeHtml(p1.name || 'TBD')}</span>
                        <span class="ms-2 fw-bold text-end" style="min-width: 24px; color: #fff;">${p1.score != null ? p1.score : '-'}</span>
                    </div>
                    <div class="text-center my-1" style="color: #999; font-size: 0.7rem;">VS</div>
                    <div class="d-flex align-items-center justify-content-between py-2 px-2 rounded ${w2 ? 'bg-warning bg-opacity-25 border border-warning' : 'bg-dark'}" style="min-height: 38px;">
                        <span class="badge bg-secondary me-2">${p2.seed || '-'}</span>
                        <span class="flex-grow-1 text-truncate" style="color: #fff;" title="${escapeHtml(p2.name || 'TBD')}">${escapeHtml(p2.name || 'TBD')}</span>
                        <span class="ms-2 fw-bold text-end" style="min-width: 24px; color: #fff;">${p2.score != null ? p2.score : '-'}</span>
                    </div>
                    ${linhaAvanca}
                </div>
            </div>`;
        });
        html += '</div>';
        if (faseIdx < (bracket || []).length - 1) {
            const numMatches = (fase.matches || []).length;
            let connectorHtml = '<div class="bracket-connector" style="display: flex; flex-direction: column; justify-content: space-around; width: 24px; flex-shrink: 0; padding: 8px 0;">';
            for (let i = 0; i < numMatches; i++) {
                connectorHtml += '<div style="display: flex; align-items: center;"><div style="width: 100%; height: 2px; background: rgba(255,193,7,0.5);"></div><span style="color: #ffc107; font-size: 0.7rem; margin-left: 2px;">→</span></div>';
            }
            connectorHtml += '</div>';
            html += connectorHtml;
        }
    });
    html += '</div>';
    const colocações = calcularColocacoesBracket(bracket);
    if (colocações.length > 0) {
        html += '<div class="mt-4 pt-3" style="border-top: 1px solid rgba(255,193,7,0.3);">';
        html += '<h6 class="mb-2" style="color: #ffc107;">🏆 Colocações (1º ao último)</h6>';
        html += '<table class="table table-dark table-striped table-bordered tabela-colocacoes" style="color: #fff; max-width: 400px;"><thead><tr><th>Posição</th><th>Equipe</th></tr></thead><tbody>';
        colocações.forEach((c) => {
            const medal = c.posicao === 1 ? '🥇' : (c.posicao === 2 ? '🥈' : (c.posicao === 3 ? '🥉' : ''));
            html += `<tr><td style="color: #fff;">${medal} ${c.posicao}º</td><td style="color: #fff;">${escapeHtml(c.name)}</td></tr>`;
        });
        html += '</tbody></table></div>';
    }
    return html;
}

function abrirModalPartidaBatalha(el) {
    const etapaId = el.dataset.etapaId;
    const match = JSON.parse(el.dataset.match || '{}');
    if (!etapaId || !match.match_id) return;
    abrirModalPartida(etapaId, match);
}

function abrirModalPartida(etapaId, match) {
    const p1 = match.player1 || {};
    const p2 = match.player2 || {};
    const temVencedor = !!match.winner_id;
    let bodyHtml = `
        <div class="row g-2 mb-3">
            <div class="col-6">
                <div class="card bg-dark border-warning h-100">
                    <div class="card-header py-2"><strong style="color:#fff;">${escapeHtml(p1.name || 'TBD')}</strong></div>
                    <div class="card-body py-2 small">
                        <div id="modalP1Piloto" style="color:#ccc;">Piloto: carregando...</div>
                        <div id="modalP1Vida" class="mt-2" style="color:#ddd;">Vida: carregando...</div>
                    </div>
                </div>
            </div>
            <div class="col-6">
                <div class="card bg-dark border-warning h-100">
                    <div class="card-header py-2"><strong style="color:#fff;">${escapeHtml(p2.name || 'TBD')}</strong></div>
                    <div class="card-body py-2 small">
                        <div id="modalP2Piloto" style="color:#ccc;">Piloto: carregando...</div>
                        <div id="modalP2Vida" class="mt-2" style="color:#ddd;">Vida: carregando...</div>
                    </div>
                </div>
            </div>
        </div>`;
    if (temVencedor) {
        bodyHtml += `<button type="button" class="btn btn-warning w-100" onclick="desfazerResultadoPartida('${etapaId}', ${match.match_id})"><i class="fas fa-undo me-1"></i> Desfazer resultado</button>`;
    } else {
        bodyHtml += `
        <div class="d-flex gap-2">
            <button type="button" class="btn btn-success flex-fill" onclick="reportarVencedorPartida('${etapaId}', ${match.match_id}, ${p1.id || 'null'}, this, ${match.round || 1})"><i class="fas fa-trophy me-1"></i> ${escapeHtml((p1.name || 'P1').substring(0, 15))} vence</button>
            <button type="button" class="btn btn-success flex-fill" onclick="reportarVencedorPartida('${etapaId}', ${match.match_id}, ${p2.id || 'null'}, this, ${match.round || 1})"><i class="fas fa-trophy me-1"></i> ${escapeHtml((p2.name || 'P2').substring(0, 15))} vence</button>
        </div>
        <div class="mt-3">
            <button type="button" class="btn btn-outline-warning w-100" id="btnExecutarPassada">
                <i class="fas fa-dice me-1"></i> Executar passada <span id="passadaCount">(0/2)</span>
            </button>
            <small class="text-muted d-block mt-1">Roda 1 dado de dano para Motor, Câmbio, Suspensão, Kit-ângulo e Diferencial de ambos os carros. Máx. 2 vezes.</small>
            <div id="resultadoPassada" class="mt-2 p-2 rounded bg-secondary" style="display:none; max-height:180px; overflow-y:auto;">
                <div class="small fw-bold text-warning mb-1">Resultado da passada:</div>
                <div id="resultadoPassadaConteudo" class="small" style="color:#ddd;"></div>
            </div>
        </div>`;
    }
    const modalDiv = document.createElement('div');
    modalDiv.className = 'modal fade';
    modalDiv.id = 'modalPartidaBatalha';
    modalDiv.style.zIndex = '10010';
    modalDiv.setAttribute('tabindex', '-1');
    modalDiv.innerHTML = `
        <div class="modal-dialog modal-dialog-centered modal-lg" style="z-index: 10011; max-width: 90%;">
            <div class="modal-content bg-dark text-white">
                <div class="modal-header">
                    <h5 class="modal-title">Definir vencedor</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">${bodyHtml}</div>
            </div>
        </div>`;
    document.body.appendChild(modalDiv);
    const modal = new bootstrap.Modal(modalDiv);
    modal.show();
    modalDiv.dataset.etapaId = etapaId;
    modalDiv.dataset.eq1Nome = p1.name || '';
    modalDiv.dataset.eq2Nome = p2.name || '';
    modalDiv.dataset.passadaCount = '0';
    modalDiv.addEventListener('hidden.bs.modal', () => modalDiv.remove());

    carregarPilotosNoModal(etapaId, p1.name, p2.name);

    const btnPassada = modalDiv.querySelector('#btnExecutarPassada');
    if (btnPassada) {
        btnPassada.addEventListener('click', function() {
            const modal = document.getElementById('modalPartidaBatalha');
            const count = parseInt(modal?.dataset?.passadaCount || '0', 10);
            if (count >= 2) return;
            executarPassada(etapaId, {
                equipe1_id: modal?.dataset?.equipe1Id || '',
                equipe2_id: modal?.dataset?.equipe2Id || '',
                equipe1_nome: modal?.dataset?.eq1Nome || '',
                equipe2_nome: modal?.dataset?.eq2Nome || ''
            }, btnPassada, modal);
        });
    }
}

async function carregarPilotosNoModal(etapaId, nome1, nome2) {
    try {
        const r = await fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos`, { credentials: 'include' });
        const data = await r.json();
        if (!data.sucesso || !Array.isArray(data.equipes)) return;
        const eq1 = data.equipes.find(e => (e.equipe_nome || '').trim() === (nome1 || '').trim() || (nome1 && (e.equipe_nome || '').includes(nome1)));
        const eq2 = data.equipes.find(e => (e.equipe_nome || '').trim() === (nome2 || '').trim() || (nome2 && (e.equipe_nome || '').includes(nome2)));
        const el1 = document.getElementById('modalP1Piloto');
        const el2 = document.getElementById('modalP2Piloto');
        if (el1) el1.innerHTML = '<span style="color: #fff;">Equipe: ' + escapeHtml(nome1 || 'TBD') + ' | Piloto: ' + escapeHtml(eq1?.piloto_nome || '-') + '</span>';
        if (el2) el2.innerHTML = '<span style="color: #fff;">Equipe: ' + escapeHtml(nome2 || 'TBD') + ' | Piloto: ' + escapeHtml(eq2?.piloto_nome || '-') + '</span>';
        const modal = document.getElementById('modalPartidaBatalha');
        if (modal) {
            modal.dataset.equipe1Id = eq1?.equipe_id || '';
            modal.dataset.equipe2Id = eq2?.equipe_id || '';
            carregarVidaPecasModal(etapaId, eq1?.equipe_id || '', eq2?.equipe_id || '');
        }
    } catch (e) { console.warn('Erro ao carregar pilotos no modal:', e); }
}

async function carregarVidaPecasModal(etapaId, equipe1Id, equipe2Id) {
    const el1 = document.getElementById('modalP1Vida');
    const el2 = document.getElementById('modalP2Vida');
    if (!el1 || !el2) return;
    if (!equipe1Id && !equipe2Id) {
        el1.innerHTML = '<span class="text-muted">Vida: equipes não identificadas</span>';
        el2.innerHTML = '<span class="text-muted">Vida: equipes não identificadas</span>';
        return;
    }
    try {
        const url = `/api/etapas/${etapaId}/pecas-batalha?equipe1_id=${encodeURIComponent(equipe1Id)}&equipe2_id=${encodeURIComponent(equipe2Id)}`;
        const r = await fetch(url, { credentials: 'include' });
        const data = await r.json();
        if (!data.sucesso || !Array.isArray(data.carros)) {
            el1.innerHTML = '<span class="text-muted">Vida: erro ao carregar</span>';
            el2.innerHTML = '<span class="text-muted">Vida: erro ao carregar</span>';
            return;
        }
        const car1 = data.carros[0] || { pecas: [] };
        const car2 = data.carros[1] || { pecas: [] };
        el1.innerHTML = formatarVidaPecas(car1.pecas);
        el2.innerHTML = formatarVidaPecas(car2.pecas);
    } catch (e) {
        console.warn('Erro ao carregar vida das peças:', e);
        el1.innerHTML = '<span class="text-muted">Vida: erro</span>';
        el2.innerHTML = '<span class="text-muted">Vida: erro</span>';
    }
}

function formatarVidaPecas(pecas) {
    if (!pecas || pecas.length === 0) return '<span class="text-muted">Nenhuma peça instalada</span>';
    return pecas.map(p => {
        const pct = p.percentual ?? Math.round((p.durabilidade_atual || 0) / (p.durabilidade_maxima || 100) * 100);
        const tipo = (p.tipo || p.nome || '?').replace('_', '-');
        const cor = pct > 60 ? '#4ade80' : pct > 30 ? '#fbbf24' : '#f87171';
        return `<div><span style="color:${cor}">${tipo}: ${pct}%</span> (${p.durabilidade_atual ?? '-'}/${p.durabilidade_maxima ?? '-'})</div>`;
    }).join('');
}

function renderizarResultadoPassada(d) {
    const box = document.getElementById('resultadoPassada');
    const content = document.getElementById('resultadoPassadaConteudo');
    if (!box || !content) return;
    const lancamentos = d.lancamentos || [];
    const dadoFaces = d.dado_faces || 6;
    if (lancamentos.length === 0) {
        content.textContent = d.resumo || 'Passada executada.';
    } else {
        const linhas = [];
        const porCarro = {};
        lancamentos.forEach(l => {
            const cid = l.carro_id || '?';
            if (!porCarro[cid]) porCarro[cid] = [];
            porCarro[cid].push(l);
        });
        Object.keys(porCarro).forEach((cid, idx) => {
            const carLabel = 'Carro ' + (idx + 1);
            porCarro[cid].forEach(l => {
                const tipo = (l.tipo || '?').replace('_', '-');
                const maxS = l.max ? ' (MAX!)' : '';
                linhas.push(`${carLabel} | ${tipo}: dado=${l.dado}/${dadoFaces}${maxS} → dano ${l.dano}`);
            });
        });
        const total = (d.detalhes || []).reduce((s, x) => s + (x.dano || 0), 0);
        content.innerHTML = linhas.join('<br>') + '<br><strong class="text-warning mt-1">Total: ' + total.toFixed(1) + '</strong>';
    }
    box.style.display = 'block';
}

async function executarPassada(etapaId, dados, btn, modal) {
    const count = parseInt(modal?.dataset?.passadaCount || '0', 10);
    if (count >= 2) return;
    if (btn) btn.disabled = true;
    const payload = {};
    if (dados.equipe1_id) payload.equipe1_id = dados.equipe1_id;
    if (dados.equipe2_id) payload.equipe2_id = dados.equipe2_id;
    if (dados.equipe1_nome) payload.equipe1_nome = dados.equipe1_nome;
    if (dados.equipe2_nome) payload.equipe2_nome = dados.equipe2_nome;
    try {
        const r = await fetch(`/api/etapas/${etapaId}/executar-passada`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        const d = await r.json();
        if (d.sucesso) {
            const novoCount = count + 1;
            if (modal) modal.dataset.passadaCount = String(novoCount);
            const span = document.getElementById('passadaCount');
            if (span) span.textContent = '(' + novoCount + '/2)';
            if (novoCount >= 2 && btn) btn.disabled = true;
            if (typeof mostrarToast === 'function') mostrarToast('Passada executada! ' + (d.resumo || ''), 'success');
            renderizarResultadoPassada(d);
            carregarVidaPecasModal(etapaId, dados.equipe1_id || '', dados.equipe2_id || '');
        } else {
            if (typeof mostrarToast === 'function') mostrarToast('Erro: ' + (d.erro || 'Falha'), 'error');
        }
    } catch (e) {
        if (typeof mostrarToast === 'function') mostrarToast('Erro ao executar passada', 'error');
    } finally {
        if (btn && parseInt(modal?.dataset?.passadaCount || '0', 10) < 2) btn.disabled = false;
    }
}

async function reportarVencedorPartida(etapaId, matchId, winnerId, btn, round) {
    const scores = '1-0';
    if (!btn) btn = document.querySelector('[data-bs-dismiss="modal"]');
    if (btn) btn.disabled = true;
    const payload = { match_id: matchId, winner_id: winnerId, scores_csv: scores };
    if (round != null) payload.round = round;
    try {
        const r = await fetch(`/api/etapas/${etapaId}/challonge-match-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        const d = await r.json();
        if (d.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalPartidaBatalha')).hide();
            await recarregarBracketChallonge(etapaId);
            if (typeof mostrarToast === 'function') mostrarToast('Vencedor registrado!', 'success');
        } else {
            if (typeof mostrarToast === 'function') mostrarToast('Erro: ' + (d.erro || 'Falha'), 'error');
        }
    } catch (e) {
        if (typeof mostrarToast === 'function') mostrarToast('Erro ao registrar', 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function desfazerResultadoPartida(etapaId, matchId) {
    try {
        const r = await fetch(`/api/etapas/${etapaId}/challonge-match-reopen`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ match_id: matchId })
        });
        const d = await r.json();
        if (d.sucesso) {
            bootstrap.Modal.getInstance(document.getElementById('modalPartidaBatalha')).hide();
            await recarregarBracketChallonge(etapaId);
            if (typeof mostrarToast === 'function') mostrarToast('Resultado desfeito!', 'success');
        } else {
            if (typeof mostrarToast === 'function') mostrarToast('Erro: ' + (d.erro || 'Falha'), 'error');
        }
    } catch (e) {
        if (typeof mostrarToast === 'function') mostrarToast('Erro ao desfazer', 'error');
    }
}

function initBracketCardClicks() {
    if (window._bracketClicksInit) return;
    window._bracketClicksInit = true;
    document.addEventListener('click', function(e) {
        const card = e.target.closest('.batalha-card-clickable');
        if (card) abrirModalPartidaBatalha(card);
    });
}

async function recarregarBracketChallonge(etapaId) {
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/bracket-challonge`);
        const data = await resp.json();
        if (!data.sucesso || !data.bracket) return;
        const html = renderizarBracketChallonge({ bracket: data.bracket, url: data.challonge_url, etapaId });
        const container = document.getElementById('chaveamentoBatalhasInline');
        if (container) container.innerHTML = html;
        const modalBody = document.querySelector('#modalChaveamentoBatalhas .modal-body');
        if (modalBody) modalBody.innerHTML = html;
    } catch (e) { console.error('Erro ao recarregar bracket:', e); }
}

async function verResultadoQualificacao(etapaId) {
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/classificacao-final`);
        const data = await resp.json();
        
        if (data.sucesso && data.classificacao) {
            // Criar modal com a classificação
            const modalDiv = document.createElement('div');
            modalDiv.className = 'modal fade';
            modalDiv.id = 'modalClassificacaoQualificacao';
            modalDiv.tabIndex = '-1';
            
            let html = '<table class="table table-dark table-striped">';
            html += '<thead><tr><th>#</th><th>Equipe</th><th>Piloto</th><th>Linha</th><th>Ângulo</th><th>Estilo</th><th>Total</th></tr></thead><tbody>';
            
            data.classificacao.forEach((item, index) => {
                html += `<tr>
                    <td>${index + 1}</td>
                    <td>${item.equipe_nome}</td>
                    <td>${item.piloto_nome || '-'}</td>
                    <td>${item.nota_linha}</td>
                    <td>${item.nota_angulo}</td>
                    <td>${item.nota_estilo}</td>
                    <td><strong>${item.total_notas}</strong></td>
                </tr>`;
            });
            
            html += '</tbody></table>';
            
            modalDiv.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content bg-dark text-white">
                        <div class="modal-header">
                            <h5 class="modal-title">🏆 Classificação Final da Qualificação</h5>
                        </div>
                        <div class="modal-body">
                            ${html}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modalDiv);
            const modal = new bootstrap.Modal(modalDiv);
            modal.show();
            
            modalDiv.addEventListener('hidden.bs.modal', () => modalDiv.remove());
        } else {
            mostrarToast('Erro ao carregar classificação', 'error');
        }
    } catch (e) {
        console.error('Erro:', e);
        mostrarToast('Erro ao carregar classificação', 'error');
    }
}

async function entrarBatalhas(etapaId) {
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/entrar-batalhas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await resp.json();
        
        if (data.sucesso) {
            mostrarToast('✅ Bem-vindo às batalhas!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            mostrarToast('❌ ' + data.erro, 'error');
        }
    } catch (e) {
        console.error('Erro:', e);
        mostrarToast('Erro ao entrar nas batalhas', 'error');
    }
}

async function mostrarChaveamentoBatalhas(etapaId) {
    const isAdminFazerEtapa = (window.location.pathname === '/admin/fazer-etapa' || (window.location.pathname || '').indexOf('fazer-etapa') !== -1) && document.getElementById('secaoChaveamentoBatalhas');
    if (isAdminFazerEtapa) {
        await carregarChaveamentoBatalhasInline(etapaId);
        const secao = document.getElementById('secaoChaveamentoBatalhas');
        if (secao) secao.scrollIntoView({ behavior: 'smooth' });
        return;
    }
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/bracket-challonge`);
        const data = await resp.json();
        let html;
        if (data.sucesso && data.bracket && data.bracket.length > 0) {
            html = renderizarBracketChallonge({ bracket: data.bracket, url: data.challonge_url, etapaId });
        } else {
            html = '<p class="text-muted mb-0">Conecte o Challonge em Configurações e finalize a qualificação.</p>';
        }
        const modalDiv = document.createElement('div');
        modalDiv.className = 'modal fade';
        modalDiv.id = 'modalChaveamentoBatalhas';
        modalDiv.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content bg-dark text-white">
                    <div class="modal-header" style="border-bottom: 1px solid #444;">
                        <h5 class="modal-title">⚔️ Chaveamento das Batalhas</h5>
                        <div class="d-flex align-items-center gap-2">
                            <button type="button" class="btn btn-sm btn-success" id="btnEnviarChallonge" onclick="enviarParaChallonge('${etapaId}')">
                                <i class="fas fa-external-link-alt"></i> Enviar para Challonge
                            </button>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                    </div>
                    <div class="modal-body" style="max-height: 70vh; overflow-x: auto; overflow-y: auto;">
                        ${html}
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modalDiv);
        const modal = new bootstrap.Modal(modalDiv);
        modal.show();
        modalDiv.addEventListener('hidden.bs.modal', () => modalDiv.remove());
    } catch (e) {
        console.error('Erro:', e);
        mostrarToast('Erro ao carregar chaveamento', 'error');
    }
}

async function enviarParaChallonge(etapaId) {
    const btn = document.getElementById('btnEnviarChallonge');
    if (!btn) return;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
    try {
        const resp = await fetch(`/api/etapas/${etapaId}/enviar-challonge`, { method: 'POST', credentials: 'include' });
        const data = await resp.json();
        if (data.sucesso) {
            mostrarToast(data.bracket_pendente ? 'Torneio criado. Inicie manualmente no Challonge (link aberto).' : 'Torneio enviado para o Challonge!', data.bracket_pendente ? 'warning' : 'success');
            if (data.url) window.open(data.url, '_blank');
        } else {
            mostrarToast('Erro: ' + (data.erro || 'Falha ao enviar'), 'error');
        }
    } catch (e) {
        mostrarToast('Erro ao enviar para Challonge', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-external-link-alt"></i> Enviar para Challonge';
    }
}

// Tornar globais e inicializar clique nos cards
window.verResultadoQualificacao = verResultadoQualificacao;
window.entrarBatalhas = entrarBatalhas;
window.mostrarChaveamentoBatalhas = mostrarChaveamentoBatalhas;
window.enviarParaChallonge = enviarParaChallonge;
window.reportarVencedorPartida = reportarVencedorPartida;
window.desfazerResultadoPartida = desfazerResultadoPartida;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBracketCardClicks);
} else {
    initBracketCardClicks();
}
