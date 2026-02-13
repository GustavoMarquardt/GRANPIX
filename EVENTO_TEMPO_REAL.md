# Sistema de Evento em Tempo Real (EM ANDAMENTO)

## Visão Geral

O sistema de evento em tempo real permite que admin, equipes e pilotos vejam **simultaneamente** e **em tempo real** o status de uma etapa quando ela está no estado `em_andamento`.

## Fluxo de Funcionamento

### 1. Admin Inicia o Evento
```javascript
abrirQualificacao(etapaId) 
  ↓
POST /api/admin/fazer-etapa
  ↓ (status → 'em_andamento')
  ↓
mostrarEventoAoVivo(etapaId)
  ↓
Polling a cada 2 segundos: GET /api/etapas/<etapaId>/evento
  ↓
Renderização reativa dos pits com dados atualizados
```

### 2. Admin Vê Banner e Entra no Evento
- Quando `etapa.status == 'em_andamento'`, um banner aparece no topo
- Banner mostra: "🔴 EVENTO EM ANDAMENTO"
- Clique no botão abre `mostrarEventoAoVivo(etapaId)`

### 3. Equipes/Pilotos Clicam em Etapa
```javascript
entrarQualificacao(etapaId, botao)
  ↓
POST /api/etapas/<etapaId>/entrar-qualificacao
  ↓
if (status == 'em_andamento')
  ↓ Automático: mostrarEventoAoVivo(etapaId)
  ↓
else
  ↓ Resposta normal de qualificação
```

### 4. Visualização de Pits
```javascript
mostrarPitsEtapa(etapaId)
  ↓
Verifica: GET /api/etapas/<etapaId>/evento
  ↓
if (status == 'em_andamento')
  ↓ Mostra evento ao vivo com polling
  ↓
else
  ↓ Mostra view estática de qualificação
```

## Endpoints da API

### GET /api/etapas/<etapaId>/evento
**Descrição**: Retorna todos os dados da etapa em tempo real

**Response**:
```json
{
  "sucesso": true,
  "evento": {
    "etapa": {
      "id": "uuid",
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
        "participacao_id": "uuid",
        "equipe_id": "uuid",
        "ordem_qualificacao": 1,
        "equipe_nome": "smokedNinja",
        "piloto_id": "uuid",
        "piloto_nome": "Piloto Teste 8",
        "carro_id": "uuid",
        "carro_modelo": "Fusca",
        "tipo_participacao": "completa",
        "status": "inscrito"
      }
    ],
    "total_equipes": 3,
    "timestamp": "2026-02-09T22:30:45.123456"
  }
}
```

### POST /api/etapas/<etapaId>/entrar-evento
**Descrição**: Registra que um usuário entrou no evento

**Request Body**:
```json
{
  "tipo": "admin|equipe|piloto",
  "id": "uuid_usuario",
  "nome": "Nome do Usuário"
}
```

### Ordem dos Pits
Os pits são ordenados por `ordem_qualificacao`:
1. Primeiramente, equipes COM ordem_qualificacao (em ordem crescente)
2. Depois, equipes SEM ordem_qualificacao (em ordem alfabética)

Exemplo de display no pit card:
```
┌─────────────────────────────────────┐
│ PIT          QUAL                   │
│ 01           01                     │
└─────────────────────────────────────┘
│ EQUIPE: smokedNinja                 │
├─────────────────────────────────────┤
│ PILOTO: 🏎️     │  STATUS: 📋       │
│ Piloto Nome    │  INSCRITO          │
└─────────────────────────────────────┘
```

## Dados Observable (Em Tempo Real)

Todos estes campos são atualizados automaticamente a cada 2 segundos para TODOS os viewers:

- `ordem_qualificacao` - Posição no grid
- `piloto_nome` - Nome do piloto atualizado
- `status` - Status da participação
- `carro_modelo` - Modelo do carro
- `tipo_participacao` - Se está completo ou não
- Qualquer outro campo na resposta

## Intervalo de Polling

- **Padrão**: 2000ms (2 segundos)
- **Duração**: Contínuo enquanto modal está aberto
- **Cache-bust**: Campo `timestamp` evita cache de dados antigos

## Integração com Diferentes Contextos

### Admin Dashboard
- Carrega etapa com `carregarEtapaHoje()`
- Se `status='em_andamento'`, mostra banner
- Clique em pit card → verifica status → abre evento se ativo

### Team/Pilot Campaign
- Botão "ENTRAR NA QUALIFICACAO" → `entrarQualificacao()`
- Se evento ativo → auto-abre `mostrarEventoAoVivo()`
- Polling sincroniza dados entre todos os viewers

### Admin View Estática
- Pode ver equipes/pilotos sem polling
- Ao clicar no pit → verifica se ativo
- Se ativo → muda para view com polling

## Observações Importantes

1. **Sincronização**: Todos os usuários veem os MESMOS pits NO MESMO ORDEM
2. **Real-time**: Mudanças refletem em TODOS os clientes dentro de 2-3 segundos
3. **Escalabilidade**: Para 100+ usuários, considerar WebSocket no futuro
4. **Falhas**: Se polling falha, tenta novamente na próxima iteração (sem interromper)
5. **Status**: Modal fecha automaticamente se usuário sair (`hidden.bs.modal` event)

## Variáveis Globais Importantes

```javascript
eventos = {
    ativo: false,           // Se há um evento ativo em polling
    etapaId: null,         // ID da etapa sendo monitorada
    dados: null,           // Últimos dados recebidos
    ultimaAtualizacao: null // Timestamp da última atualização
}

intervaloEventoAtual: null  // ID do setInterval para poder fazer clearInterval
```

## Troubleshooting

### Evento não atualiza
- Verificar se `status='em_andamento'` no banco
- Verificar console para erros de polling
- Verificar se `/api/etapas/<etapaId>/evento` retorna dados válidos

### Banner não aparece
- Verificar se `etapa.status` é carregado em `preencherEtapaHoje`
- Banner só aparece se `status === 'em_andamento'`

### Modal fecha sem motivo
- Pode ser qualidade de conexão fazendo polling falhar
- Implementar retry logic se necessário

## Próximos Passos Sugeridos

1. ✅ Polling implementado (2s)
2. ✅ Reactive UI updates
3. ⏳ Indicador visual de "atualizado x segundos atrás"
4. ⏳ WebSocket para melhor performance com muitos usuários
5. ⏳ Histórico de eventos (logs de mudanças)
6. ⏳ Notificações em tempo real quando alguém entra
7. ⏳ Limitar polling apenas pabras cliente ativo
