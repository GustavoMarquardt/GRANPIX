/**
 * Sistema de Notificações Global
 * Exibe notificação quando evento está em andamento
 * Aparece para TODOS no sistema
 */

let notificacaoIntervalId = null;
let etapaAtualEmAndamento = null;

/**
 * Inicia o sistema de notificação global
 * Executa a cada 3 segundos para verificar se há etapa em andamento
 */
function iniciarSistemaNotificacao() {
    console.log('[NOTIFICACAO] Iniciando sistema de notificações global');
    
    // Verificar imediatamente
    verificarEtapaEmAndamento();
    
    // Depois verificar a cada 3 segundos
    notificacaoIntervalId = setInterval(() => {
        verificarEtapaEmAndamento();
    }, 3000);
}

/**
 * Verifica se há etapa em andamento e notifica
 */
async function verificarEtapaEmAndamento() {
    try {
        // Primeiro verificar se é admin - se for, ignorar completamente
        let isAdmin = false;
        try {
            const adminResp = await fetch('/api/user/is-admin');
            if (adminResp.ok) {
                const adminData = await adminResp.json();
                isAdmin = adminData.is_admin;
            }
        } catch (e) {
            console.log('[NOTIFICACAO] Erro ao verificar admin:', e);
        }
        
        // Se é admin, não fazer nenhuma verificação ou notificação
        if (isAdmin) {
            console.log('[NOTIFICACAO] Admin detectado - sistema de notificação desabilitado');
            return;
        }
        
        const resp = await fetch('/api/admin/etapa-hoje');
        if (!resp.ok) return;
        
        const data = await resp.json();
        
        if (data.sucesso && data.etapa) {
            const etapa = data.etapa;
            
            // Se status é em_andamento e não havia notificação
            if (etapa.status === 'em_andamento') {
                if (!etapaAtualEmAndamento || etapaAtualEmAndamento !== etapa.id) {
                    etapaAtualEmAndamento = etapa.id;
                    console.log('[NOTIFICACAO] Etapa em andamento detectada:', etapa.nome);
                    
                    // Mostrar banner para não-admins
                    console.log('[NOTIFICACAO] Usuário não-admin, mostrando banner');
                    mostrarNotificacaoEventoAoVivo(etapa);
                }
            } else {
                // Se não está mais em andamento, remover notificação
                if (etapaAtualEmAndamento) {
                    etapaAtualEmAndamento = null;
                    removerNotificacaoEventoAoVivo();
                }
            }
        } else {
            // Sem etapa hoje, remover notificação se existir
            if (etapaAtualEmAndamento) {
                etapaAtualEmAndamento = null;
                removerNotificacaoEventoAoVivo();
            }
        }
    } catch (e) {
        console.error('[NOTIFICACAO] Erro ao verificar etapa:', e);
    }
}

/**
 * Mostra o banner de evento ao vivo
 */
function mostrarNotificacaoEventoAoVivo(etapa) {
    // Verificar se já existe
    if (document.getElementById('banner-evento-ao-vivo')) {
        return;
    }
    
    // Criar estrutura do banner
    const banner = document.createElement('div');
    banner.id = 'banner-evento-ao-vivo';
    banner.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background: linear-gradient(90deg, #dc143c 0%, #ff0000 50%, #dc143c 100%);
        color: white;
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(220, 20, 60, 0.5);
        animation: slideDown 0.5s ease-out;
    `;
    
    banner.innerHTML = `
        <div style="flex: 1; display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 24px; animation: pulse 1.5s ease-in-out infinite;">🔴</div>
            <div>
                <div style="font-size: 14px; font-weight: bold; letter-spacing: 1px;">EVENTO EM ANDAMENTO</div>
                <div style="font-size: 12px; opacity: 0.9; margin-top: 2px;">${etapa.nome} - ${etapa.campeonato_nome}</div>
            </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
            <button onclick="abrirEventoEmAnda()" style="
                background: white;
                color: #dc143c;
                border: none;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: bold;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
            " onmouseover="this.style.background='#f0f0f0'" onmouseout="this.style.background='white'">
                ENTRAR
            </button>
            <button onclick="minimizarNotificacao()" style="
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                width: 36px;
                height: 36px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 18px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
            " onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                −
            </button>
        </div>
    `;
    
    document.body.insertBefore(banner, document.body.firstChild);
    
    // Adicionar styles de animação
    adicionarEstilosAnimacao();
}

/**
 * Remove o banner de evento ao vivo
 */
function removerNotificacaoEventoAoVivo() {
    const banner = document.getElementById('banner-evento-ao-vivo');
    if (banner) {
        banner.style.animation = 'slideUp 0.5s ease-in';
        setTimeout(() => {
            banner.remove();
            removerBotaoFlutante();
        }, 500);
    }
}

/**
 * Minimiza o banner para um botão flutuante
 */
function minimizarNotificacao() {
    const banner = document.getElementById('banner-evento-ao-vivo');
    if (banner) {
        banner.style.animation = 'slideUp 0.3s ease-in';
        setTimeout(() => {
            banner.remove();
            mostrarBotaoFlutante();
        }, 300);
    }
}

/**
 * Mostra botão flutuante no canto inferior esquerdo
 */
function mostrarBotaoFlutante() {
    if (document.getElementById('botao-flutuante-evento')) {
        return;
    }
    
    const botao = document.createElement('div');
    botao.id = 'botao-flutuante-evento';
    botao.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 9998;
        background: linear-gradient(135deg, #dc143c 0%, #ff0000 100%);
        color: white;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(220, 20, 60, 0.6);
        transition: all 0.3s ease;
        animation: slideUpBotao 0.5s ease-out;
    `;
    
    botao.innerHTML = `
        <div style="
            text-align: center;
            font-size: 24px;
            animation: pulse 1.5s ease-in-out infinite;
        ">
            🔴
        </div>
    `;
    
    botao.onmouseover = function() {
        this.style.transform = 'scale(1.1)';
        this.style.boxShadow = '0 6px 20px rgba(220, 20, 60, 0.8)';
    };
    
    botao.onmouseout = function() {
        this.style.transform = 'scale(1)';
        this.style.boxShadow = '0 4px 15px rgba(220, 20, 60, 0.6)';
    };
    
    botao.onclick = function() {
        restaurarNotificacao();
        abrirEventoEmAnda();
    };
    
    document.body.appendChild(botao);
    adicionarEstilosAnimacao();
}

/**
 * Remove botão flutuante
 */
function removerBotaoFlutante() {
    const botao = document.getElementById('botao-flutuante-evento');
    if (botao) {
        botao.remove();
    }
}

/**
 * Restaura o banner a partir do botão flutuante
 */
function restaurarNotificacao() {
    const botao = document.getElementById('botao-flutuante-evento');
    if (botao) {
        botao.style.animation = 'slideDownBotao 0.3s ease-in';
        setTimeout(() => {
            botao.remove();
            if (etapaAtualEmAndamento) {
                // Recarregar dados da etapa
                verificarEtapaEmAndamento();
            }
        }, 300);
    }
}

/**
 * Abre o evento ao vivo
 */
function abrirEventoEmAnda() {
    if (etapaAtualEmAndamento) {
        // Verificar se está na página admin - se estiver, não fazer nada
        const isAdminPage = window.location.pathname === '/admin' || window.location.pathname.startsWith('/admin');
        if (isAdminPage) {
            console.log('[NOTIFICACAO] Usuário está na página admin, não redirecionar');
            return;
        }
        
        // Tentar chamar a função existente
        if (typeof mostrarEventoAoVivo === 'function') {
            console.log('[NOTIFICACAO] Chamando mostrarEventoAoVivo para etapa:', etapaAtualEmAndamento);
            mostrarEventoAoVivo(etapaAtualEmAndamento);
        } else {
            // Se função não existe, tentar com delay
            console.warn('[NOTIFICACAO] Função mostrarEventoAoVivo não disponível ainda, aguardando...');
            
            // Aguardar até 5 segundos pela função estar disponível
            let tentativas = 0;
            const intervalo = setInterval(() => {
                tentativas++;
                if (typeof mostrarEventoAoVivo === 'function') {
                    console.log('[NOTIFICACAO] Função encontrada após ' + tentativas + ' tentativas');
                    clearInterval(intervalo);
                    mostrarEventoAoVivo(etapaAtualEmAndamento);
                } else if (tentativas >= 50) {
                    // Após 5 segundos, se ainda não houver função, redirecionar para admin
                    clearInterval(intervalo);
                    console.error('[NOTIFICACAO] Função mostrarEventoAoVivo não encontrada após 5s, redirecionando...');
                    window.location.href = `/admin?etapa=${etapaAtualEmAndamento}`;
                }
            }, 100);
        }
    }
}

/**
 * Adiciona estilos de animação
 */
function adicionarEstilosAnimacao() {
    // Verificar se já foram adicionados
    if (document.getElementById('estilos-notificacao')) {
        return;
    }
    
    const style = document.createElement('style');
    style.id = 'estilos-notificacao';
    style.innerHTML = `
        @keyframes slideDown {
            from {
                transform: translateY(-100%);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes slideUp {
            from {
                transform: translateY(0);
                opacity: 1;
            }
            to {
                transform: translateY(-100%);
                opacity: 0;
            }
        }
        
        @keyframes slideUpBotao {
            from {
                transform: translateY(120px) scale(0.8);
                opacity: 0;
            }
            to {
                transform: translateY(0) scale(1);
                opacity: 1;
            }
        }
        
        @keyframes slideDownBotao {
            from {
                transform: translateY(0) scale(1);
                opacity: 1;
            }
            to {
                transform: translateY(120px) scale(0.8);
                opacity: 0;
            }
        }
        
        @keyframes pulse {
            0%, 100% {
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.1);
                opacity: 0.8;
            }
        }
    `;
    
    document.head.appendChild(style);
}

/**
 * Carrega tabela de voltas para o admin quando há etapa em andamento
 */
async function carregarTabelaVoltasParaAdmin(etapaId) {
    try {
        // Mostrar container de voltas
        const containerVoltas = document.getElementById('containerVoltasAdmin');
        if (!containerVoltas) {
            console.log('[NOTIFICACAO] Container de voltas não encontrado, admin pode estar fora da página de etapas');
            return;
        }
        
        containerVoltas.style.display = 'block';
        
        // Garantir que etapaIdAtual está definido
        const etapaIdInput = document.getElementById('etapaIdAtual');
        if (etapaIdInput) {
            etapaIdInput.value = etapaId;
        }
        
        // Carregar a tabela
        console.log('[NOTIFICACAO] Carregando tabela de voltas para admin, etapa:', etapaId);
        
        // Se função atualizarTabelaVoltasAdmin existe, chamá-la
        if (typeof atualizarTabelaVoltasAdmin === 'function') {
            await atualizarTabelaVoltasAdmin();
        } else {
            console.warn('[NOTIFICACAO] Função atualizarTabelaVoltasAdmin não disponível ainda');
        }
    } catch (e) {
        console.error('[NOTIFICACAO] Erro ao carregar tabela de voltas:', e);
    }
}

/**
 * Para o sistema de notificações
 */
function pararSistemaNotificacao() {
    if (notificacaoIntervalId) {
        clearInterval(notificacaoIntervalId);
        notificacaoIntervalId = null;
    }
    removerNotificacaoEventoAoVivo();
    removerBotaoFlutante();
    etapaAtualEmAndamento = null;
}

// Iniciar automaticamente quando a página carregar (apenas para não-admins)
async function verificarEIniciarNotificacao() {
    try {
        // Verificar se é admin
        const adminResp = await fetch('/api/user/is-admin');
        if (adminResp.ok) {
            const adminData = await adminResp.json();
            if (adminData.is_admin) {
                console.log('[NOTIFICACAO] Admin detectado - sistema de notificação não será iniciado');
                return;
            }
        }
        
        // Se não é admin, iniciar o sistema de notificação
        console.log('[NOTIFICACAO] Usuário não-admin - iniciando sistema de notificação');
        iniciarSistemaNotificacao();
    } catch (e) {
        console.log('[NOTIFICACAO] Erro ao verificar admin, iniciando notificação por segurança:', e);
        // Em caso de erro, iniciar por segurança (melhor mostrar notificação do que não mostrar)
        iniciarSistemaNotificacao();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        verificarEIniciarNotificacao();
    });
} else {
    verificarEIniciarNotificacao();
}

// Parar quando sair da página
window.addEventListener('unload', () => {
    pararSistemaNotificacao();
});
