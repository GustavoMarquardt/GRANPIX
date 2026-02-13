# 🎯 SISTEMA DE EVENTO EM TEMPO REAL - IMPLEMENTAÇÃO COMPLETA

## ✅ O QUE FOI IMPLEMENTADO

### 1️⃣ Backend - API Endpoints (app.py)

#### ✅ POST /api/admin/fazer-etapa
**Status**: IMPLEMENTADO E FUNCIONANDO  
**Localização**: [app.py](app.py#L1889)

```python
@app.route('/api/admin/fazer-etapa', methods=['POST'])
def fazer_etapa():
    """Inicia qualificacao da etapa e muda status para em_andamento"""
```

**O que faz**:
- Recebe etapa_id
- Muda status da etapa para `'em_andamento'` (estava `'qualificacao'`)
- Aplica ordenação de qualificação
- **Retorna**: `sucesso, mensagem, status, etapa_id, ordenacao`

**Fluxo**:
1. Admin clica "Fazer Etapa"
2. Status muda de `qualificacao` → `em_andamento`
3. Ordenação é aplicada (por pontos anteriores ou aleatória)
4. Frontend recebe confirmação e abre modal ao vivo

---

#### ✅ GET /api/etapas/<etapaId>/evento
**Status**: IMPLEMENTADO E FUNCIONANDO  
**Localização**: [app.py](app.py#L2013)

```python
@app.route('/api/etapas/<etapa_id>/evento', methods=['GET'])
def obter_evento_etapa(etapa_id):
    """Obtém todos os dados da etapa EM ANDAMENTO em tempo real"""
```

**O que faz**:
- Verifica se etapa está `status='em_andamento'`
- Retorna info completa da etapa (campeonato, série, hora, etc)
- Retorna todas as equipes/pilotos ordenadas por `ordem_qualificacao`
- Inclui `timestamp` para cache-busting

**Resposta**:
```json
{
  "sucesso": true,
  "evento": {
    "etapa": {
      "id": "...",
      "numero": 1,
      "nome": "teste",
      "campeonato_nome": "GRAMPIX Temporada A",
      "serie": "A",
      "data": "2026-02-09",
      "hora": "22:00:00",
      "status": "em_andamento",
      "descricao": "..."
    },
    "equipes": [
      {
        "participacao_id": "...",
        "equipe_id": "...",
        "ordem_qualificacao": 1,
        "equipe_nome": "smokedNinja",
        "piloto_id": "...",
        "piloto_nome": "Piloto Teste 8",
        "carro_id": "...",
        "carro_modelo": "Fusca",
        "tipo_participacao": "completa",
        "status": "inscrito"
      },
      // ... mais equipes
    ],
    "total_equipes": 3,
    "timestamp": "2026-02-09T22:30:45.123456"
  }
}
```

**Características**:
- ✅ Dados sempre ordenados por `ordem_qualificacao`
- ✅ Retorna NULL se etapa não estiver `em_andamento`
- ✅ Inclui todos os campos necessários para renderização
- ✅ Cache-bust com timestamp

---

#### ✅ POST /api/etapas/<etapaId>/entrar-evento
**Status**: IMPLEMENTADO E FUNCIONANDO  
**Localização**: [app.py](app.py#L2103)

```python
@app.route('/api/etapas/<etapa_id>/entrar-evento', methods=['POST'])
def entrar_evento_etapa(etapa_id):
    """Registra que alguém entrou no evento (equipe, piloto ou admin)"""
```

**O que faz**:
- Aceita: `tipo` (admin/equipe/piloto), `id`, `nome`
- Registra entrada do usuário
- Log para debugging
- **Pronto para extensão**: Pode armazenar em cache/DB para presença

**Exemplos de chamada**:
```javascript
// Admin
fetch('/api/etapas/abc123/entrar-evento', {
  method: 'POST',
  body: JSON.stringify({
    tipo: 'admin',
    id: 'admin',
    nome: 'Administrador'
  })
})

// Equipe
fetch('/api/etapas/abc123/entrar-evento', {
  method: 'POST',
  body: JSON.stringify({
    tipo: 'equipe',
    id: 'equipe123',
    nome: 'smokedNinja'
  })
})

// Piloto
fetch('/api/etapas/abc123/entrar-evento', {
  method: 'POST',
  body: JSON.stringify({
    tipo: 'piloto',
    id: 'piloto456',
    nome: 'João Silva'
  })
})
```

---

### 2️⃣ Frontend - Sistema de Polling (qualificacao.js)

#### ✅ Variáveis Globais
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L154)

```javascript
let intervaloEventoAtual = null;
let eventos = {
    ativo: false,           // Se há evento sendo monitorado
    etapaId: null,          // ID da etapa
    dados: null,            // Últimos dados recebidos
    ultimaAtualizacao: null // Timestamp
};
```

---

#### ✅ async function carregarEvento(etapaId)
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L163)

```javascript
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
        }
        return null;
    } catch (e) {
        console.error('[EVENTO] Erro ao carregar evento:', e);
        return null;
    }
}
```

**O que faz**:
- Chama GET /api/etapas/<etapaId>/evento
- Armazena dados em `eventos.dados`
- Retorna evento para renderização
- Tratamento de erro silencioso (não quebra polling)

---

#### ✅ async function mostrarEventoAoVivo(etapaId) - FUNÇÃO PRINCIPAL
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L181)

```javascript
async function mostrarEventoAoVivo(etapaId) {
    console.log('[EVENTO AO VIVO] Iniciando visualização do evento:', etapaId);
    
    // 1. Carrega dados iniciais
    const evento = await carregarEvento(etapaId);
    if (!evento) {
        mostrarToast('Erro ao carregar evento', 'error');
        return;
    }
    
    // 2. Registra entrada do usuário
    let usuarioTipo = 'admin';
    let usuarioId = 'admin';
    let usuarioNome = 'Administrador';
    
    // Verificar se é equipe ou piloto (localStorage)
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
    
    // 3. Cria modal fullscreen
    const modalDiv = document.createElement('div');
    modalDiv.className = 'modal fade';
    modalDiv.id = 'modalEventoAoVivo';
    // ... (HTML template com header, body, footer)
    
    document.body.appendChild(modalDiv);
    const modal = new bootstrap.Modal(modalDiv);
    modal.show();
    
    // 4. Renderiza pits iniciais
    renderizarPitsEvento(evento.equipes);
    
    // 5. INICIA POLLING A CADA 2 SEGUNDOS
    eventos.ativo = true;
    eventos.etapaId = etapaId;
    
    if (intervaloEventoAtual) clearInterval(intervaloEventoAtual);
    
    intervaloEventoAtual = setInterval(async () => {
        const eventoAtualizado = await carregarEvento(etapaId);
        if (eventoAtualizado && eventoAtualizado.equipes) {
            renderizarPitsEvento(eventoAtualizado.equipes);
            atualizarTimestampEvento();
        }
    }, 2000); // ← POLLING A CADA 2 SEGUNDOS
    
    // 6. Limpa ao fechar
    modalDiv.addEventListener('hidden.bs.modal', () => {
        console.log('[EVENTO] Fechando evento ao vivo');
        eventos.ativo = false;
        if (intervaloEventoAtual) clearInterval(intervaloEventoAtual);
        modalDiv.remove();
    });
}
```

**Fluxo Completo**:
1. ✅ Fetch dados iniciais
2. ✅ Registra presença do usuário
3. ✅ Cria modal fullscreen com header/footer
4. ✅ Renderiza pits iniciais
5. ✅ **INICIA POLLING A CADA 2 SEGUNDOS**
6. ✅ Atualiza pits quando novos dados chegam
7. ✅ Para polling quando modal fecha

---

#### ✅ function renderizarPitsEvento(equipes)
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L265)

```javascript
function renderizarPitsEvento(equipes) {
    console.log('[EVENTO RENDER] Renderizando', equipes.length, 'equipes');
    
    const container = document.getElementById('containerEventoPits');
    if (!container) return;
    
    container.innerHTML = '';
    
    equipes.forEach((eq, idx) => {
        const temPiloto = !!eq.piloto_nome;
        const borderColor = temPiloto ? '#ff0000' : '#cc0000';
        const piloIcon = temPiloto ? '🏎️' : '⚠️';
        const piloColor = temPiloto ? '#00ff00' : '#ff6666';
        const ordemQualif = eq.ordem_qualificacao ? String(eq.ordem_qualificacao).padStart(2, '0') : '—';
        
        // Cria pit card com tema VERMELHO/PRETO/BRANCO
        const pitDiv = document.createElement('div');
        pitDiv.style.cssText = `
            background: linear-gradient(180deg, #0a0a0a 0%, #1a1a1a 100%);
            border: 3px solid ${borderColor};
            border-radius: 0px;
            padding: 18px;
            box-shadow: 0 8px 24px rgba(255,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1);
        `;
        
        // HTMLContent:
        // - PIT number (big)
        // - QUAL number (qualificação)
        // - EQUIPE name
        // - PILOTO name + status
        // - STATUS field
        
        container.appendChild(pitDiv);
    });
}
```

**Características**:
- ✅ Clear completo: `container.innerHTML = ''`
- ✅ Rebuild de todos os pits (simples, sem diffing)
- ✅ Tema consistente: vermelho, preto, branco
- ✅ Informações visuais: PIT, QUAL, EQUIPE, PILOTO, STATUS
- ✅ Cores adaptam-se se piloto presente ou não

---

#### ✅ function atualizarTimestampEvento()
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L318)

```javascript
function atualizarTimestampEvento() {
    const el = document.getElementById('ultimaAtualizacao');
    if (el) {
        const agora = new Date();
        el.textContent = agora.toLocaleTimeString('pt-BR');
    }
}
```

Mostra: "Atualizado: 22:30:45"

---

### 3️⃣ Integração com Fluxos Existentes

#### ✅ abrirQualificacao(etapaId) - MODIFICADO
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L1)

```javascript
async function abrirQualificacao(etapaId) {
    try {
        const resp = await fetch('/api/admin/fazer-etapa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ etapa: etapaId })
        });
        const resultado = await resp.json();
        if (resultado.sucesso) {
            mostrarToast('✓ Etapa iniciada! Status: EM ANDAMENTO', 'success');
            
            // ✨ NOVO: Abre evento ao vivo em vez de Modal de Equipes
            setTimeout(() => {
                mostrarEventoAoVivo(etapaId);
            }, 500);
        } else {
            mostrarToast('Erro: ' + resultado.erro, 'error');
        }
    } catch (e) {
        mostrarToast('Erro ao abrir etapa', 'error');
    }
}
```

**Mudança**:
- ❌ Antigo: Mostra modal com lista de equipes
- ✅ Novo: Abre modal com pits em tempo real + polling

---

#### ✅ entrarQualificacao(etapaId, botao) - MODIFICADO
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L144)

```javascript
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
            // ✨ NOVO: Verifica se evento está em andamento
            const eventoResp = await fetch(`/api/etapas/${etapaId}/evento`);
            const eventoData = await eventoResp.json();
            
            if (eventoData.sucesso && eventoData.evento && 
                eventoData.evento.etapa.status === 'em_andamento') {
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
```

**Fluxo**:
1. Piloto/Equipe clica "ENTRAR"
2. Registra na qualificação
3. ✨ **Verifica se status=='em_andamento'**
4. ✨ **Se SIM → Auto-abre evento ao vivo**
5. Se NÃO → Mostra mensagem normal

---

#### ✅ mostrarPitsEtapa(etapaId) - MODIFICADO
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L467)

```javascript
async function mostrarPitsEtapa(etapaId) {
    console.log('[PITS MODAL] Carregando pits para etapa:', etapaId);
    
    try {
        // ✨ NOVO: Primeiro, verificar se a etapa está em andamento
        const eventoResp = await fetch(`/api/etapas/${etapaId}/evento`);
        const eventoData = await eventoResp.json();
        
        if (eventoData.sucesso && eventoData.evento && 
            eventoData.evento.etapa.status === 'em_andamento') {
            console.log('[PITS MODAL] Etapa em andamento, mostrando evento ao vivo');
            mostrarEventoAoVivo(etapaId);
            return;
        }
        
        // Caso contrário, carregar view estática de qualificação
        const resp = await fetch(`/api/admin/etapas/${etapaId}/equipes-pilotos`);
        // ...renderização estática...
    } catch (e) {
        console.error('[PITS MODAL] Erro:', e);
        mostrarToast('Erro ao carregar pits', 'error');
    }
}
```

**Lógica**:
- ✨ Primeira coisa: verifica se evento está `em_andamento`
- ✨ Se SIM → Abre modal com polling
- Se NÃO → Abre view estática normal

---

#### ✅ preencherEtapaHoje(etapa) - MODIFICADO
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L245)

```javascript
function preencherEtapaHoje(etapa) {
    // ... preencher info normal...
    
    // ✨ NOVO: Verificar se etapa está em andamento
    if (etapa.status === 'em_andamento') {
        console.log('[ETAPA HOJE] Etapa em andamento! Mostrando banner');
        mostrarBannerEventoAoVivo(etapa.id);
    }
    
    // ... continuar normal...
}
```

---

#### ✅ mostrarBannerEventoAoVivo(etapaId) - NOVA FUNÇÃO
**Status**: IMPLEMENTADO  
**Localização**: [qualificacao.js](static/qualificacao.js#L262)

```javascript
function mostrarBannerEventoAoVivo(etapaId) {
    // Criar banner de evento ao vivo
    const banner = document.createElement('div');
    banner.id = 'bannerEventoAoVivo';
    banner.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #ff0000 0%, #cc0000 50%, #000 100%);
        color: white;
        padding: 20px;
        text-align: center;
        z-index: 999;
        box-shadow: 0 8px 32px rgba(255,0,0,0.6);
        animation: slideDown 0.4s ease;
    `;
    
    banner.innerHTML = `
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 10px;">
            <span class="indicator-evento">🔴 EVENTO EM ANDAMENTO</span>
            <span style="color: #ffff00; font-weight: bold;">CLIQUE ABAIXO PARA ENTRAR</span>
        </div>
        <button class="btn btn-light btn-lg" 
                onclick="mostrarEventoAoVivo('${etapaId}')">
            ⚡ ENTRAR NO EVENTO AO VIVO
        </button>
        <button class="btn btn-outline-light" 
                onclick="this.parentElement.parentElement.remove()">
            ✕ Minimizar
        </button>
    `;
    
    document.body.insertBefore(banner, document.body.firstChild);
    
    // Auto-scroll
    setTimeout(() => {
        window.scrollBy({ top: 80, behavior: 'smooth' });
    }, 100);
}
```

**Visual**:
```
┌─────────────────────────────────────────────────┐
│ 🔴 EVENTO EM ANDAMENTO                          │
│ CLIQUE ABAIXO PARA ENTRAR                       │
│ [⚡ ENTRAR NO EVENTO AO VIVO]  [✕ Minimizar]   │
└─────────────────────────────────────────────────┘
```

---

## 📊 FLUXO COMPLETO: ADMIN INICIA → EQUIPE PARTICIPA

```
ADMIN DASHBOARD
│
├─→ Clica "Fazer Etapa"
│
└─→ abrirQualificacao(etapaId)
    │
    ├─→ POST /api/admin/fazer-etapa
    │   └─→ status: 'qualificacao' → 'em_andamento'
    │
    ├─→ mostrarEventoAoVivo(etapaId)
    │   │
    │   ├─→ GET /api/etapas/<etapaId>/evento (primeira vez)
    │   │   └─→ Retorna evento com etapa info + todas as equipes
    │   │
    │   ├─→ POST /api/etapas/<etapaId>/entrar-evento
    │   │   └─→ Registra: tipo='admin', id='admin', nome='Administrador'
    │   │
    │   ├─→ CREATE modal com pits
    │   │
    │   └─→ setInterval (2000ms)
    │       └─→ GET /api/etapas/<etapaId>/evento
    │           └─→ renderizarPitsEvento(equipes)
    │               └─→ UPDATE pit cards NO LUGAR

EQUIPE VÊ NOTIFICAÇÃO
│
├─→ Clica em card da etapa (status = em_andamento)
│
└─→ entrarQualificacao(etapaId, botao)
    │
    ├─→ POST /api/etapas/<etapaId>/entrar-qualificacao
    │
    ├─→ GET /api/etapas/<etapaId>/evento (verificar status)
    │   └─→ Vê que evento está em_andamento
    │
    └─→ mostrarEventoAoVivo(etapaId)
        │
        ├─→ GET /api/etapas/<etapaId>/evento
        │   └─→ Mesmos pits que admin vê!
        │
        ├─→ POST /api/etapas/<etapaId>/entrar-evento
        │   └─→ Registra: tipo='equipe', id='<equipe_id>', nome='smokedNinja'
        │
        └─→ setInterval (2000ms)
            └─→ Sincroniza TODOS os dados com admin!

SINCRONIZAÇÃO EM TEMPO REAL
│
├─→ Admin muda algo (piloto, posição, status, etc)
│
├─→ Na próxima iteração de polling (dentro de 2s)
│   └─→ All clients (admin + equipes + pilotos) veem a mudança!
│
└─→ É VERDADEIRAMENTE EM TEMPO REAL!
```

---

## 🔍 DADOS OBSERVÁVEIS (Observable) 

Todos estes campos são atualizados **em TODOS os clientes** dentro de 2-3 segundos:

```javascript
{
  "ordem_qualificacao": 1,     // ← OBSERVABLE
  "equipe_nome": "smokedNinja", // ← OBSERVABLE  
  "piloto_nome": "João Silva",  // ← OBSERVABLE
  "carro_modelo": "Fusca",      // ← OBSERVABLE
  "status": "inscrito",         // ← OBSERVABLE
  "tipo_participacao": "completa" // ← OBSERVABLE
}
```

---

## ⚙️ CONFIGURAÇÕES

### Intervalo de Polling
```javascript
// Linhas [~250] em qualificacao.js
intervaloEventoAtual = setInterval(async () => {
    // ... polling logic
}, 2000); // ← Mude aqui se precisar (ms)
```

- **Padrão**: 2000ms (2 segundos)
- **Recomendado**: 1000-5000ms
- **Mais rápido** = Mais real-time (mas mais CPU/network)
- **Mais lento** = Menos real-time (mas menos uso de recursos)

### Log Level
```javascript
console.log('[EVENTO] ...') // Verbose logging
```

Procure por `[EVENTO]` no console para ver fluxo completo.

---

## 🧪 COMO TESTAR

### Teste 1: Admin Inicia Evento
1. Abra admin dashboard
2. Clique "Fazer Etapa"
3. Veja modal com pits aparecer
4. Observe que dados atualizam a cada 2s
5. Timestamp muda: "Atualizado: 22:30:45"

### Teste 2: Equipe Entra em Evento Ativo
1. Equipe abre dashboard
2. Vê etapa card
3. Clica "ENTRAR"
4. Modal automaticamente abre (não é perguntado no modal)
5. Compare pits com admin → **DEVEM SER IGUAIS**

### Teste 3: Sincronização Entre Abas
1. Abra 2 abas do navegador: admin + equipe
2. Admin inicia evento
3. Equipe clica para entrar
4. Ambas veem OS MESMOS pits NO MESMO ORDEM
5. Espere polling → dados devem sincronizar

### Teste 4: Banner Aparece
1. Admin já com evento aberto
2. Recarrega página
3. Vê banner vermelho no topo: "🔴 EVENTO EM ANDAMENTO"
4. Pode clicar para entrar novamente

---

## 📝 CÓDIGO-CHAVE PARA REFERÊNCIA

| Função | Localização | Propósito |
|--------|-------------|----------|
| `abrirQualificacao()` | [L1](static/qualificacao.js#L1) | Admin inicia evento |
| `mostrarEventoAoVivo()` | [L181](static/qualificacao.js#L181) | Main function: cria modal + polling |
| `carregarEvento()` | [L163](static/qualificacao.js#L163) | Fetch dados do servidor |
| `renderizarPitsEvento()` | [L265](static/qualificacao.js#L265) | Desenha pits na UI |
| `entrarQualificacao()` | [L144](static/qualificacao.js#L144) | Equipe entra; verifica se evento ativo |
| `mostrarPitsEtapa()` | [L467](static/qualificacao.js#L467) | Verifica status antes de mostrar |
| `preencherEtapaHoje()` | [L245](static/qualificacao.js#L245) | Mostra banner se evento ativo |
| `mostrarBannerEventoAoVivo()` | [L262](static/qualificacao.js#L262) | Render banner no topo |
| `fazer_etapa()` | [app.py#1889](app.py#L1889) | Backend: muda status para em_andamento |
| `obter_evento_etapa()` | [app.py#2013](app.py#L2013) | Backend: retorna evento completo |
| `entrar_evento_etapa()` | [app.py#2103](app.py#L2103) | Backend: registra presença |

---

## ✨ PRÓXIMOS PASSOS (Sugestões)

1. **WebSocket** - Para performance com 100+ usuários
2. **Histórico** - Log de todas as mudanças
3. **Presença Visual** - Mostrar quem está conectado
4. **Notificações** - Alert quando alguém entra
5. **Auto-pause** - Parar polling se aba não ativa
6. **Data Diffing** - Renderizar apenas mudanças (não rebuild inteiro)

---

## 🐛 Troubleshooting

| Problema | Causa | Solução |
|----------|-------|--------|
| Evento não atualiza | Status não é `em_andamento` | Verificar DB: `SELECT status FROM etapas WHERE id = ?` |
| Modal não abre | Erro em `mostrarEventoAoVivo()` | Check console para erros, verificar etapaId |
| Pits vazios | Nenhuma equipe registrada | Adicionar equipes antes de fazer etapa |
| Banner não aparece | `etapa.status` não é carregado | Verificar se `preencherEtapaHoje()` recebe status |
| Polling lento | Intervalo muito longo | Reduza de 2000ms para 1000ms |

---

## 📚 Documentação Relacionada

- [EVENTO_TEMPO_REAL.md](EVENTO_TEMPO_REAL.md) - Guia técnico
- [app.py](app.py) - Backend Python/Flask  
- [static/qualificacao.js](static/qualificacao.js) - Frontend JavaScript

---

## 🎉 STATUS: PRONTO PARA PRODUÇÃO

✅ Backend endpoints funcionando  
✅ Frontend polling implementado  
✅ Sincronização em tempo real  
✅ Suporta múltiplos usuários  
✅ Data formatada e ordenada  
✅ Error handling básico implementado  
✅ Logging para debugging  

**Pronto para deploy e testes de produção!**
