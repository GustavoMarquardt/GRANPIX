"""
Sistema Web GRANPIX - Interface para gerenciar equipes e comprar
Com autenticação por equipe e painel admin
"""
import sys
import os

# Carregar .env no início (garante CWD-independent load)
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_dotenv(_env_path)
except ImportError:
    pass

# Log Challonge
if os.environ.get('CHALLONGE_API_KEY') and os.environ.get('CHALLONGE_USERNAME'):
    print("[CHALLONGE] API key + username carregados (v1).")
elif os.environ.get('CHALLONGE_API_KEY'):
    print("[CHALLONGE] API key carregada (configure CHALLONGE_USERNAME para evitar 401).")
else:
    print("[CHALLONGE] Configure CHALLONGE_API_KEY e CHALLONGE_USERNAME no .env")

# Adicionar o diretório atual ao path para que 'src' seja reconhecido como pacote
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# Também adicionar o subdiretório src
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask.json.provider import DefaultJSONProvider
from src.api import APIGranpix
from functools import wraps
import json
from pathlib import Path
from datetime import datetime
import uuid
from decimal import Decimal
from src.models import Carro, Peca
from werkzeug.security import generate_password_hash, check_password_hash


class CustomJSONProvider(DefaultJSONProvider):
    """Serializa Decimal (ex.: do banco) como float."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


app = Flask(__name__)
app.json = CustomJSONProvider(app)
app.secret_key = 'GRANPIX_SUPER_SECRET_2026'
app.config['JSON_SORT_KEYS'] = False

# Desabilitar cache HTTP para garantir dados frescos
@app.after_request
def disable_cache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.before_request
def log_request_incoming():
    """Log de toda requisição /api/* para debug (Docker/tunnel)."""
    path = getattr(request, 'path', '')
    if path.startswith('/api/'):
        method = getattr(request, 'method', '?')
        full_url = getattr(request, 'url', path)
        print(f"[REQ] >>> {method} {path} (url={full_url})", flush=True)


@app.after_request
def log_response_api(response):
    """Log status de respostas /api/* para debug."""
    path = getattr(request, 'path', '')
    if path.startswith('/api/'):
        endpoint = getattr(request, 'endpoint', None)
        print(f"[REQ] <<< {request.method} {path} -> {response.status_code} endpoint={endpoint}", flush=True)
    return response


def _rotas_contendo(texto):
    """Lista regras do url_map que contêm o texto (para log de debug)."""
    return [f"  {r.rule} | methods={sorted(r.methods - {'HEAD', 'OPTIONS'})}" for r in app.url_map.iter_rules() if texto in r.rule]


@app.errorhandler(404)
def log_404(e):
    """Log 404 detalhado: path, method e rotas registradas que contêm 'instalar' ou 'garagem'."""
    path = getattr(request, 'path', '?')
    method = getattr(request, 'method', '?')
    full_url = getattr(request, 'url', path)
    print(f"[404] ========== ROTA NAO ENCONTRADA ==========", flush=True)
    print(f"[404] method={method} path={path}", flush=True)
    print(f"[404] url completa={full_url}", flush=True)
    for line in _rotas_contendo('instalar'):
        print(f"[404] {line}", flush=True)
    if not _rotas_contendo('instalar'):
        print("[404] (nenhuma rota com 'instalar' no path)", flush=True)
    for line in _rotas_contendo('garagem'):
        print(f"[404] {line}", flush=True)
    print(f"[404] ========================================", flush=True)
    if path.startswith('/api/'):
        return jsonify({
            'erro': 'Rota não encontrada',
            'path': path,
            'method': method,
            'url': full_url,
            'debug_rotas_instalar': _rotas_contendo('instalar')[:10],
        }), 404
    from flask import make_response
    return make_response("<h1>404 Not Found</h1>", 404)

# Configuração MySQL (variável de ambiente no Docker; fallback para desenvolvimento local)
MYSQL_CONFIG = os.environ.get(
    "MYSQL_CONFIG",
    "mysql://root:@127.0.0.1:3306/granpix"
)

# Inicializar API com MySQL (sempre; driver PyMySQL para compatibilidade com MariaDB)
print("[APP] Conectando ao banco (PyMySQL)...", flush=True)
api = APIGranpix(MYSQL_CONFIG)
print("[APP] Banco inicializado.", flush=True)

# Credenciais
SENHA_ADMIN = "admin123"

# ============ DECORADORES =============

def obter_equipe_id_request():
    """Obtém equipe_id da sessão ou header"""
    print(f"[AUTH] Verificando autenticação...")
    print(f"[AUTH] session.equipe_id: {session.get('equipe_id', 'VAZIO')}")
    print(f"[AUTH] X-Equipe-ID header: {request.headers.get('X-Equipe-ID', 'VAZIO')}")
    if 'equipe_id' in session:
        print(f"[AUTH] Usando session: {session['equipe_id']}")
        return session['equipe_id']
    header_id = request.headers.get('X-Equipe-ID')
    print(f"[AUTH] Usando header: {header_id}")
    return header_id

def requer_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'equipe_id' not in session and not request.headers.get('X-Equipe-ID'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def requer_login_api(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'equipe_id' not in session and 'piloto_id' not in session and not request.headers.get('X-Equipe-ID'):
            return jsonify({'erro': 'Não autenticado'}), 401
        return f(*args, **kwargs)
    return decorated_function

def requer_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session or not session['admin']:
            return jsonify({'erro': 'Acesso negado'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ============ ROTAS AUTENTICAÇÃO =============

@app.route('/')
def index():
    if 'equipe_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        dados = request.json
        tipo_login = dados.get('tipo')
        
        print(f"\n🔐 LOGIN ATTEMPT - Tipo: {tipo_login}")
        print(f"   Dados recebidos: {dados}")
        
        if tipo_login == 'admin':
            senha = dados.get('senha', '')
            if senha == SENHA_ADMIN:
                session['admin'] = True
                session['tipo'] = 'admin'
                return jsonify({
                    'sucesso': True, 
                    'tipo': 'admin'
                })
            else:
                return jsonify({'sucesso': False, 'erro': 'Senha admin incorreta'}), 401
        
        elif tipo_login == 'equipe':
            equipe_id = dados.get('equipe_id')
            senha = dados.get('senha', '')
            
            print(f"   Equipe ID: {equipe_id} (tipo: {type(equipe_id)})")
            print(f"   Senha: {senha}")
            
            try:
                # Obter equipe pelo índice ou ID
                equipe = api.gerenciador.obter_equipe(str(equipe_id))
                
                print(f"   Equipe encontrada: {equipe}")
                
                if equipe:
                    print(f"   Equipe nome: {equipe.nome}")
                    print(f"   Equipe senha: {equipe.senha} (tipo: {type(equipe.senha)})")
                    
                    if check_password_hash(equipe.senha, senha):
                        session['equipe_id'] = equipe.id  # Armazenar UUID real
                        session['equipe_nome'] = equipe.nome
                        session['tipo'] = 'equipe'
                        print(f"   ✓ LOGIN SUCESSO!")
                        return jsonify({
                            'sucesso': True, 
                            'tipo': 'equipe',
                            'uuid': equipe.id,  # UUID real
                            'nome': equipe.nome
                        })
                    else:
                        print(f"   ✗ SENHA INCORRETA")
                        return jsonify({'sucesso': False, 'erro': 'Equipe ou senha incorreta'}), 401
                else:
                    print(f"   ✗ EQUIPE NÃO ENCONTRADA")
                    return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404
                    
            except Exception as e:
                print(f"   ✗ ERRO: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': f'Erro: {str(e)}'}), 400
        
        elif tipo_login == 'piloto':
            nome = dados.get('nome', '').strip()
            senha = dados.get('senha', '')
            
            print(f"   Piloto: {nome}")
            
            resultado = api.db.autenticar_piloto(nome, senha)
            if resultado['sucesso']:
                session['piloto_id'] = resultado['piloto_id']
                session['piloto_nome'] = resultado['nome']
                session['tipo'] = 'piloto'
                print(f"   ✓ LOGIN PILOTO SUCESSO!")
                return jsonify(resultado)
            else:
                print(f"   ✗ PILOTO LOGIN FALHOU: {resultado['erro']}")
                return jsonify(resultado), 401
        
        return jsonify({'sucesso': False, 'erro': 'Tipo de login inválido'}), 400
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    # Não verificar autenticação aqui, deixar o JavaScript verificar
    # via header X-Equipe-ID
    user_type = session.get('tipo', 'equipe')  # Default to equipe
    return render_template('dashboard.html', user_type=user_type)

@app.route('/admin')
def admin():
    return redirect(url_for('admin_etapas'))

@app.route('/admin/carros')
def admin_carros():
    return render_template('admin_carros.html')

@app.route('/admin/pecas')
def admin_pecas():
    return render_template('admin_pecas.html')

@app.route('/admin/upgrades')
def admin_upgrades():
    return render_template('admin_upgrades.html')

@app.route('/admin/variacoes')
def admin_variacoes():
    return render_template('admin_variacoes.html')

@app.route('/admin/equipes')
def admin_equipes_page():
    return render_template('admin_equipes.html')

@app.route('/admin/etapas')
def admin_etapas():
    return render_template('admin_etapas.html')

@app.route('/admin/solicitacoes-pecas')
def admin_solicitacoes_pecas():
    return render_template('admin_solicitacoes_pecas.html')

@app.route('/admin/solicitacoes-carros')
def admin_solicitacoes_carros():
    return render_template('admin_solicitacoes_carros.html')

@app.route('/admin/fazer-etapa')
def admin_fazer_etapa():
    return render_template('admin_fazer_etapa.html')

@app.route('/admin/alocar-pilotos')
def admin_alocar_pilotos():
    return render_template('admin_alocar_pilotos.html')

@app.route('/admin/comissoes')
def admin_comissoes():
    return render_template('admin_comissoes.html')

@app.route('/admin/configuracoes')
def admin_configuracoes():
    return render_template('admin_configuracoes.html')

@app.route('/admin/equipes-list')
def admin_equipes_list():
    return render_template('admin_equipes_list.html')

@app.route('/admin/campeonatos')
def admin_campeonatos():
    return render_template('admin_campeonatos.html')

@app.route('/campeonato')
def campeonato():
    # Página de campeonato para pilotos
    return render_template('campeonato.html')

# ============ ROTAS API - PILOTOS =============

@app.route('/api/pilotos/cadastrar', methods=['POST'])
def cadastrar_piloto():
    """Cadastra um novo piloto"""
    try:
        dados = request.json
        nome = dados.get('nome', '').strip()
        senha = dados.get('senha', '').strip()
        
        if not nome or not senha:
            return jsonify({'sucesso': False, 'erro': 'Nome e senha são obrigatórios'}), 400
        
        if len(senha) < 4:
            return jsonify({'sucesso': False, 'erro': 'Senha deve ter pelo menos 4 caracteres'}), 400
        
        resultado = api.db.cadastrar_piloto(nome, senha)
        
        if resultado['sucesso']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[ERRO] Cadastro de piloto: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# ============ ROTAS API - EQUIPES =============

@app.route('/api/equipes')
def get_equipes():
    """Retorna todas as equipes"""
    equipes = api.listar_todas_equipes()
    dados = []
    
    for eq in equipes:
        dados.append({
            'id': eq.id,  # UUID real da equipe
            'nome': eq.nome,
            'saldo': eq.doricoins,
            'carro': f"{eq.carro.marca} {eq.carro.modelo}" if eq.carro else "Sem carro"
        })
    
    return jsonify(dados)

@app.route('/api/equipes/<equipe_id>')
@requer_login_api
def get_equipe_detalhes(equipe_id):
    """Retorna detalhes de uma equipe"""
    # Verificar autenticação
    auth_equipe_id = obter_equipe_id_request()
    if not auth_equipe_id:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    # Se for uma equipe, só pode acessar seus próprios dados
    # Se for admin, pode acessar qualquer equipe
    if 'equipe_id' not in session and request.headers.get('X-Equipe-ID'):
        # Está autenticado via header (equipe)
        if str(auth_equipe_id) != str(equipe_id):
            return jsonify({'erro': 'Acesso negado'}), 403
    
    equipe = api.db.carregar_equipe(equipe_id)
    
    if not equipe:
        return jsonify({'erro': 'Equipe não encontrada'}), 404
    
    # Buscar peças aguardando instalação (status="pendente") do banco
    pecas_pendentes = []
    try:
        solicitacoes_db = api.db.carregar_solicitacoes_pecas(equipe_id)
        for sol in solicitacoes_db:
            if sol['status'] == 'pendente':
                pecas_pendentes.append({
                    'id': sol['id'],
                    'peca_nome': sol.get('peca_nome', ''),
                    'peca_tipo': sol.get('tipo_peca', ''),
                    'preco': sol.get('preco', 0),
                    'timestamp': sol.get('data_solicitacao', '')
                })
                print(f"[PENDENTE] Encontrada peça: {sol.get('peca_nome', '')} para equipe {equipe_id}")
    except Exception as e:
        print(f"[ERRO PENDENTE] {str(e)}")
    
    print(f"[EQUIPE {equipe_id}] Peças pendentes: {len(pecas_pendentes)}")
    
    # Encontrar carro ativo (status='ativo') no banco de dados
    carro_ativo = None
    for carro in equipe.carros:
        if getattr(carro, 'status', 'repouso') == 'ativo':
            carro_ativo = {
                'id': carro.id,
                'marca': carro.marca,
                'modelo': carro.modelo,
                'numero_carro': carro.numero_carro
            }
            break
    
    return jsonify({
        'id': equipe.id,
        'nome': equipe.nome,
        'saldo': equipe.doricoins,
        'carro': {
            'id': equipe.carro.id,
            'marca': equipe.carro.marca,
            'modelo': equipe.carro.modelo,
            'numero_carro': equipe.carro.numero_carro
        } if equipe.carro else None,
        'carro_ativo': carro_ativo,  # Carro com status='ativo' no banco
        'carros': [{
            'id': carro.id,
            'marca': carro.marca,
            'modelo': carro.modelo,
            'numero_carro': carro.numero_carro,
            'modelo_id': getattr(carro, 'modelo_id', None),
            'status': getattr(carro, 'status', 'ativo')
        } for carro in equipe.carros],
        'pecas_adicionais': pecas_pendentes
    })

@app.route('/api/equipes/<equipe_id>/saldo-pix')
@requer_login_api
def get_saldo_pix(equipe_id):
    """Retorna o saldo PIX da equipe"""
    try:
        auth_equipe_id = obter_equipe_id_request()
        if not auth_equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        
        # Se for uma equipe, só pode acessar seus próprios dados
        if str(auth_equipe_id) != str(equipe_id):
            # Verificar se é admin
            if 'user_id' not in session:
                return jsonify({'erro': 'Acesso negado'}), 403
        
        saldo = api.db.obter_saldo_pix(equipe_id)
        
        return jsonify({
            'equipe_id': equipe_id,
            'saldo_pix': saldo,
            'saldo_formatado': f'R$ {saldo:.2f}',
            'pode_participar': saldo >= -20.0
        })
    except Exception as e:
        print(f"[ERRO] Erro ao obter saldo PIX: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/equipes/<equipe_id>/carro-ativo')
@requer_login_api
def get_carro_ativo(equipe_id):
    """Retorna o carro ativo da equipe"""
    try:
        auth_equipe_id = obter_equipe_id_request()
        if not auth_equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        
        # Carregar equipe
        equipe = api.db.carregar_equipe(equipe_id)
        if not equipe:
            return jsonify({'erro': 'Equipe não encontrada', 'id': None}), 404
        
        # Procurar carro ativo
        carro_ativo = None
        for carro in equipe.carros:
            if getattr(carro, 'status', 'repouso') == 'ativo':
                carro_ativo = {
                    'id': carro.id,
                    'marca': carro.marca,
                    'modelo': carro.modelo,
                    'numero_carro': carro.numero_carro
                }
                break
        
        if not carro_ativo:
            return jsonify({'id': None, 'erro': 'Nenhum carro ativo encontrado'}), 404
        
        return jsonify(carro_ativo)
    except Exception as e:
        print(f"[ERRO] Erro ao buscar carro ativo: {e}")
        return jsonify({'id': None, 'erro': str(e)}), 500

@app.route('/api/garagem/recuperar-peca', methods=['POST'])
@requer_login_api
def recuperar_peca_garagem():
    """Recupera vida de uma peça para 100%. Custo = metade do preço na loja (doricoins)."""
    try:
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        dados = request.json or {}
        peca_id = dados.get('peca_id')
        if not peca_id:
            return jsonify({'erro': 'peca_id obrigatório'}), 400
        ok, resultado = api.db.recuperar_peca_vida(str(peca_id), str(equipe_id))
        if ok:
            return jsonify({'sucesso': True, 'custo': float(resultado), 'mensagem': 'Peça recuperada para 100%'})
        return jsonify({'sucesso': False, 'erro': resultado}), 400
    except Exception as e:
        print(f"[ERRO] recuperar-peca: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500



@app.route('/api/garagem/solicitar-instalacao-armazem', methods=['POST'])
@requer_login_api
def solicitar_instalacao_armazem():
    """Cria uma transação PIX para instalação de peça do armazém"""
    try:
        dados = request.json
        peca_nome = dados.get('peca_nome')
        peca_tipo = dados.get('peca_tipo')
        carro_id = dados.get('carro_id')
        
        if not all([peca_nome, peca_tipo, carro_id]):
            return jsonify({'erro': 'Dados inválidos'}), 400
        
        # Obter equipe do usuário
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        
        equipe_id_str = str(equipe_id)
        
        # Buscar a peça no armazém
        pecas_armazem = api.db.carregar_pecas_armazem_equipe(equipe_id_str)
        peca_encontrada = None
        for peca in pecas_armazem:
            if peca['nome'].lower() == peca_nome.lower() and peca['tipo'].lower() == peca_tipo.lower():
                peca_encontrada = peca
                break
        
        if not peca_encontrada:
            return jsonify({'sucesso': False, 'erro': 'Peça não encontrada no armazém'}), 404
        
        # Upgrade não pode ser instalado diretamente no carro: precisa estar em cima de uma peça base (ex: motor)
        if peca_encontrada.get('upgrade_id'):
            return jsonify({
                'sucesso': False,
                'erro': 'Upgrade não pode ser instalado diretamente no carro. Instale primeiro a peça base correspondente (ex: motor) no carro ou adicione o upgrade à peça no armazém.'
            }), 400
        
        # Buscar a peça_loja
        pecas_loja = api.db.carregar_pecas_loja()
        peca_loja = None
        for peca in pecas_loja:
            if peca.nome.lower() == peca_nome.lower() and peca.tipo.lower() == peca_tipo.lower():
                peca_loja = peca
                break
        
        if not peca_loja:
            return jsonify({'sucesso': False, 'erro': 'Peça não encontrada no banco'}), 404
        
        # Validar compatibilidade
        compativel, msg = api.db.validar_compatibilidade_peca_carro(peca_loja.id, carro_id)
        if not compativel:
            print(f"[INSTALAÇÃO ARMAZÉM] Incompatibilidade: {msg}")
            return jsonify({'sucesso': False, 'erro': msg}), 400
        
        # Valor = apenas taxa de instalação (config), não preço da peça
        valor_item = float(api.db.obter_configuracao('preco_instalacao_warehouse') or '10')
        taxa = valor_item * 0.01
        valor_total = valor_item + taxa
        
        print(f"[INSTALAÇÃO ARMAZÉM] Criando transação PIX:")
        print(f"  - Peça: {peca_nome} ({peca_tipo}), id armazém: {peca_encontrada['id']}")
        print(f"  - Valor (instalação config): R$ {valor_item:.2f}")
        print(f"  - Taxa (1%): R$ {taxa:.2f}")
        print(f"  - Total: R$ {valor_total:.2f}")
        
        # Criar transação PIX para a instalação
        from src.mercado_pago_client import mp_client
        
        # Obter equipe
        equipe = api.gerenciador.obter_equipe(equipe_id)
        equipe_nome = equipe.nome if equipe else 'Desconhecido'
        
        dados_adicionais = {'peca_armazem_id': peca_encontrada['id'], 'peca_loja_id': peca_loja.id}
        transacao_id = api.db.criar_transacao_pix(
            equipe_id=equipe_id_str,
            equipe_nome=equipe_nome,
            tipo_item='instalacao_armazem',
            item_id=carro_id,
            item_nome=f'{peca_nome} → Carro',
            valor_item=valor_item,
            valor_taxa=taxa,
            carro_id=carro_id,
            dados_adicionais=dados_adicionais
        )
        
        if not transacao_id:
            return jsonify({'sucesso': False, 'erro': 'Erro ao criar transação PIX'}), 500
        
        # Gerar QRCode PIX
        descricao = f"Instalação: {peca_nome} no Carro"
        resultado_mp = mp_client.gerar_qr_code_pix(descricao, valor_total, transacao_id)
        
        if not resultado_mp.get('sucesso'):
            return jsonify({'sucesso': False, 'erro': 'Erro ao gerar QRCode PIX'}), 500
        
        qr_code_url = resultado_mp.get('qr_code_url')
        mercado_pago_id = resultado_mp.get('id')  # ID do pagamento no MercadoPago
        
        # Atualizar transação com QRCode e ID do MercadoPago
        api.db.atualizar_transacao_pix(
            transacao_id=transacao_id,
            mercado_pago_id=mercado_pago_id,
            qr_code=resultado_mp.get('qr_code', ''),
            qr_code_url=qr_code_url
        )
        
        print(f"[INSTALAÇÃO ARMAZÉM] Transação {transacao_id} criada com sucesso")
        
        return jsonify({
            'sucesso': True,
            'transacao_id': transacao_id,
            'qr_code_url': qr_code_url,
            'valor_item': valor_item,
            'valor_taxa': taxa,
            'valor_total': valor_total,
            'peca_loja_id': peca_loja.id  # ID da peça_loja para usar ao confirmar pagamento
        })
        
    except Exception as e:
        print(f"[ERRO INSTALAÇÃO ARMAZÉM] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/garagem/instalar-peca-armazem', methods=['POST'])
@requer_login_api
def instalar_peca_armazem():
    """Cria uma solicitação de instalação de peça do armazém"""
    try:
        dados = request.json
        peca_nome = dados.get('peca_nome')
        peca_tipo = dados.get('peca_tipo')
        carro_id = dados.get('carro_id')
        
        if not all([peca_nome, peca_tipo, carro_id]):
            return jsonify({'erro': 'Dados inválidos'}), 400
        
        # Obter equipe do usuário
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        
        equipe_id_str = str(equipe_id)
        
        # Buscar a peça no armazém pela equipe e tipo
        pecas_armazem = api.db.carregar_pecas_armazem_equipe(equipe_id_str)
        peca_encontrada = None
        for peca in pecas_armazem:
            if peca['nome'].lower() == peca_nome.lower() and peca['tipo'].lower() == peca_tipo.lower():
                peca_encontrada = peca
                break
        
        if not peca_encontrada:
            return jsonify({'erro': 'Peça não encontrada no armazém'}), 404
        
        # Buscar a peça_loja para ter o peca_id
        pecas_loja = api.db.carregar_pecas_loja()
        peca_loja = None
        for peca in pecas_loja:
            if peca.nome.lower() == peca_nome.lower() and peca.tipo.lower() == peca_tipo.lower():
                peca_loja = peca
                break
        
        if not peca_loja:
            return jsonify({'erro': 'Peça não encontrada no banco'}), 404
        
        # Validar compatibilidade ANTES de criar solicitação
        compativel, msg = api.db.validar_compatibilidade_peca_carro(peca_loja.id, carro_id)
        if not compativel:
            print(f"[SOLICITAÇÃO ARMAZÉM] Incompatibilidade: {msg}")
            return jsonify({'erro': msg}), 400
        
        # Criar solicitação de instalação
        import uuid
        solicitacao_id = str(uuid.uuid4())
        
        ok = api.db.salvar_solicitacao_peca(
            id=solicitacao_id,
            equipe_id=equipe_id_str,
            peca_id=peca_loja.id,
            quantidade=1,
            status='pendente',
            carro_id=carro_id
        )
        if not ok:
            erro = getattr(api.db, '_erro_solicitacao_peca', None)
            msg = 'Já existe uma solicitação pendente para esta peça neste carro.' if erro == 'duplicada' else 'Não foi possível criar a solicitação.'
            return jsonify({'sucesso': False, 'erro': msg}), 400 if erro == 'duplicada' else 500
        
        print(f"[SOLICITAÇÃO ARMAZÉM] Solicitação {solicitacao_id} criada para peça {peca_nome} no carro {carro_id}")
        return jsonify({
            'sucesso': True,
            'mensagem': f'Solicitação de instalação de {peca_nome} criada com sucesso! Aguardando aprovação.'
        })
            
    except Exception as e:
        print(f"[ERRO SOLICITAÇÃO ARMAZÉM] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500

@app.route('/api/garagem/instalar-upgrade-em-peca', methods=['POST'])
@requer_login_api
def instalar_upgrade_em_peca():
    """Instala um upgrade (do armazém) em uma peça base (motor/cambio etc) que a equipe possui."""
    try:
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        dados = request.json or {}
        peca_upgrade_id = dados.get('peca_upgrade_id')
        peca_alvo_id = dados.get('peca_alvo_id')
        exigir_alvo_no_carro = dados.get('exigir_alvo_no_carro', False)  # True = instalação no carro: peça base deve estar no carro
        if not peca_upgrade_id or not peca_alvo_id:
            return jsonify({'sucesso': False, 'erro': 'peca_upgrade_id e peca_alvo_id são obrigatórios'}), 400
        ok, msg = api.db.instalar_upgrade_em_peca(str(equipe_id), str(peca_upgrade_id), str(peca_alvo_id), exigir_alvo_no_carro=exigir_alvo_no_carro)
        if ok:
            return jsonify({'sucesso': True, 'mensagem': msg})
        return jsonify({'sucesso': False, 'erro': msg}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/garagem/instalar-multiplas-pecas-armazem', methods=['POST'])
@requer_login_api
def instalar_multiplas_pecas_armazem():
    """Cria transações PIX para instalar múltiplas peças do armazém"""
    try:
        dados = request.json
        carro_id = dados.get('carro_id')
        pecas = dados.get('pecas', [])  # Lista de {nome, tipo, quantidade}
        
        if not carro_id or not pecas or len(pecas) == 0:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400
        
        # Obter equipe do usuário
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        equipe_id_str = str(equipe_id)
        
        # Carregar peças do armazém e loja uma vez
        pecas_armazem = api.db.carregar_pecas_armazem_equipe(equipe_id_str)
        pecas_loja = api.db.carregar_pecas_loja()
        
        # Processar cada peça e validar
        pecas_validadas = []
        valor_total_itens = 0.0
        
        for peca_req in pecas:
            peca_nome = peca_req.get('nome')
            peca_tipo = peca_req.get('tipo')
            quantidade = peca_req.get('quantidade', 1)
            
            # Buscar peça no armazém
            peca_armazem = None
            for p in pecas_armazem:
                if p['nome'].lower() == peca_nome.lower() and p['tipo'].lower() == peca_tipo.lower():
                    peca_armazem = p
                    break
            
            if not peca_armazem:
                return jsonify({'sucesso': False, 'erro': f'Peça {peca_nome} não encontrada no armazém'}), 404
            
            # IMPORTANTE: Só contar peças SEM pix_id (não pagas) no valor total
            if peca_armazem.get('pix_id'):
                print(f"[INSTALAR MÚLTIPLAS] Peça {peca_nome} já foi paga (pix_id: {peca_armazem.get('pix_id')}), ignorando na soma")
                continue
            
            # Buscar peça na loja para ID
            peca_loja = None
            for p in pecas_loja:
                if p.nome.lower() == peca_nome.lower() and p.tipo.lower() == peca_tipo.lower():
                    peca_loja = p
                    break
            
            if not peca_loja:
                return jsonify({'sucesso': False, 'erro': f'Peça {peca_nome} não encontrada no banco'}), 404
            
            # Validar compatibilidade
            compativel, msg = api.db.validar_compatibilidade_peca_carro(peca_loja.id, carro_id)
            if not compativel:
                print(f"[INSTALAR MÚLTIPLAS] Incompatibilidade: {msg}")
                return jsonify({'sucesso': False, 'erro': msg}), 400
            
            # Adicionar à lista validada com preço de instalação
            valor_item = float(api.db.obter_configuracao('preco_instalacao_warehouse') or '10')
            valor_total_itens += valor_item * quantidade
            
            pecas_validadas.append({
                'nome': peca_nome,
                'tipo': peca_tipo,
                'peca_loja_id': peca_loja.id,
                'quantidade': quantidade,
                'preco_unitario': valor_item
            })
        
        if len(pecas_validadas) == 0:
            return jsonify({'sucesso': False, 'erro': 'Nenhuma peça válida para instalar (todas já foram pagas)'}), 400
        
        print(f"[INSTALAR MÚLTIPLAS] Processando {len(pecas_validadas)} peça(s) para carro {carro_id}")
        print(f"[INSTALAR MÚLTIPLAS] Valor total de peças SEM pix_id: R$ {valor_total_itens:.2f}")
        
        # Calcular taxa
        taxa = valor_total_itens * 0.01
        valor_total = valor_total_itens + taxa
        
        # Obter equipe para nome
        equipe = api.gerenciador.obter_equipe(equipe_id)
        equipe_nome = equipe.nome if equipe else 'Desconhecido'
        
        # Criar transação PIX
        from src.mercado_pago_client import mp_client
        
        # Nome descritivo das peças
        nomes_pecas = ', '.join([f"{p['nome']}" for p in pecas_validadas])
        if len(nomes_pecas) > 50:
            nomes_pecas = f"{len(pecas_validadas)} peça(s)"
        
        transacao_id = api.db.criar_transacao_pix(
            equipe_id=equipe_id_str,
            equipe_nome=equipe_nome,
            tipo_item='multiplas_pecas_armazem',
            item_id=carro_id,
            item_nome=f'{nomes_pecas} → Carro',
            valor_item=valor_total_itens,
            valor_taxa=taxa
        )
        
        if not transacao_id:
            return jsonify({'sucesso': False, 'erro': 'Erro ao criar transação PIX'}), 500
        
        # Gerar QRCode PIX
        descricao = f"Instalação: {nomes_pecas}"
        resultado_mp = mp_client.gerar_qr_code_pix(descricao, valor_total, transacao_id)
        
        if not resultado_mp.get('sucesso'):
            return jsonify({'sucesso': False, 'erro': 'Erro ao gerar QRCode PIX'}), 500
        
        qr_code_url = resultado_mp.get('qr_code_url')
        mercado_pago_id = resultado_mp.get('id')
        
        # Atualizar transação
        api.db.atualizar_transacao_pix(
            transacao_id=transacao_id,
            mercado_pago_id=mercado_pago_id,
            qr_code=resultado_mp.get('qr_code', ''),
            qr_code_url=qr_code_url
        )
        
        print(f"[INSTALAR MÚLTIPLAS] Transação {transacao_id} criada com sucesso")
        
        return jsonify({
            'sucesso': True,
            'transacao_id': transacao_id,
            'qr_code_url': qr_code_url,
            'valor_item': valor_total_itens,
            'valor_taxa': taxa,
            'valor_total': valor_total,
            'pecas_processadas': len(pecas_validadas)
        })
        
    except Exception as e:
        print(f"[ERRO INSTALAR MÚLTIPLAS] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/garagem/instalar-multiplas-pecas-armazem-repouso', methods=['POST'])
@requer_login_api
def instalar_multiplas_pecas_armazem_repouso():
    """Instala múltiplas peças do armazém em carros em repouso. Se a mesma solicitação tiver a peça base (ex: motor) e os upgrades (ex: kit turbo), instala a base primeiro e depois vincula os upgrades a ela."""
    try:
        dados = request.json
        carro_id = dados.get('carro_id')
        pecas = dados.get('pecas', [])
        
        if not carro_id or not pecas:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400
        
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        equipe_id_str = str(equipe_id)
        pecas_armazem = api.db.carregar_pecas_armazem_equipe(equipe_id_str)
        used_ids = set()
        base_por_peca_loja = {}  # peca_loja_id -> id da peça base instalada no carro
        
        def achar_peca_armazem(nome, tipo, eh_upgrade):
            for p in pecas_armazem:
                if p['id'] in used_ids:
                    continue
                if p['nome'].lower() != nome.lower() or p['tipo'].lower() != tipo.lower():
                    continue
                if eh_upgrade and not p.get('upgrade_id'):
                    continue
                if not eh_upgrade and p.get('upgrade_id'):
                    continue
                return p
            return None
        
        # Validar antes de instalar: upgrades precisam da peça base (no carro ou na seleção)
        bases_no_carro = set()
        if api.db._column_exists('pecas', 'upgrade_id'):
            conn_val = api.db._get_conn()
            cur = conn_val.cursor()
            cur.execute('''
                SELECT peca_loja_id FROM pecas WHERE carro_id = %s AND equipe_id = %s AND instalado = 1
                  AND (upgrade_id IS NULL OR upgrade_id = '') AND peca_loja_id IS NOT NULL
            ''', (carro_id, equipe_id_str))
            for row in cur.fetchall():
                if row[0]:
                    bases_no_carro.add(str(row[0]))
            conn_val.close()
        bases_na_selecao = set()
        upgrades_sem_base = []
        for peca_req in pecas:
            peca_armazem = achar_peca_armazem(peca_req.get('nome', ''), peca_req.get('tipo', ''), eh_upgrade=False)
            if peca_armazem and peca_armazem.get('peca_loja_id'):
                bases_na_selecao.add(str(peca_armazem['peca_loja_id']))
        for peca_req in pecas:
            peca_armazem = achar_peca_armazem(peca_req.get('nome', ''), peca_req.get('tipo', ''), eh_upgrade=True)
            if not peca_armazem:
                continue
            peca_loja_id_base = peca_armazem.get('peca_loja_id')
            if not peca_loja_id_base:
                continue
            if str(peca_loja_id_base) in bases_na_selecao or str(peca_loja_id_base) in bases_no_carro:
                continue
            upgrades_sem_base.append(peca_armazem.get('nome', peca_req.get('nome', 'Upgrade')))
        if upgrades_sem_base:
            nomes = ', '.join(upgrades_sem_base)
            return jsonify({
                'sucesso': False,
                'erro': f'Para instalar o(s) upgrade(s) "{nomes}" é necessário ter a peça base correspondente (ex.: motor) no carro ou selecionada para instalação.'
            }), 400
        
        conn = api.db._get_conn()
        cursor = conn.cursor()
        pecas_instaladas = 0
        
        try:
            # 1) Processar peças BASE primeiro (motor, câmbio, etc.)
            for peca_req in pecas:
                peca_nome = peca_req.get('nome')
                peca_tipo = peca_req.get('tipo')
                peca_armazem = achar_peca_armazem(peca_nome, peca_tipo, eh_upgrade=False)
                if not peca_armazem:
                    continue
                peca_loja_id = peca_armazem.get('peca_loja_id')
                if not peca_loja_id:
                    continue
                tipo_peca = peca_armazem.get('tipo') or ''
                peca_antiga = api.db.obter_peca_instalada_por_tipo(carro_id, tipo_peca)
                if peca_antiga:
                    cursor.execute('UPDATE pecas SET carro_id = NULL, instalado = 0 WHERE id = %s', (peca_antiga['id'],))
                    if api.db._column_exists('pecas', 'instalado_em_peca_id'):
                        cursor.execute('UPDATE pecas SET carro_id = NULL, instalado = 0 WHERE instalado_em_peca_id = %s', (peca_antiga['id'],))
                cursor.execute('''
                    UPDATE pecas SET carro_id = %s, instalado = 1, equipe_id = %s WHERE id = %s
                ''', (carro_id, equipe_id_str, peca_armazem['id']))
                if api.db._column_exists('pecas', 'instalado_em_peca_id'):
                    cursor.execute('UPDATE pecas SET carro_id = %s, instalado = 1, equipe_id = %s WHERE instalado_em_peca_id = %s',
                                  (carro_id, equipe_id_str, peca_armazem['id']))
                conn.commit()
                base_por_peca_loja[str(peca_loja_id)] = peca_armazem['id']
                used_ids.add(peca_armazem['id'])
                pecas_instaladas += 1
                api.db.salvar_solicitacao_peca(str(uuid.uuid4()), equipe_id_str, peca_armazem['id'], 1, 'instalada', carro_id)
                print(f"[REPOUSO] Peça base instalada: {peca_nome}")
            
            # 2) Para upgrades: vincular à base do mesmo peca_loja_id (instalada nesta solicitação ou já no carro)
            for peca_req in pecas:
                peca_nome = peca_req.get('nome')
                peca_tipo = peca_req.get('tipo')
                peca_armazem = achar_peca_armazem(peca_nome, peca_tipo, eh_upgrade=True)
                if not peca_armazem:
                    continue
                peca_loja_id_base = peca_armazem.get('peca_loja_id')
                if not peca_loja_id_base:
                    continue
                base_id = base_por_peca_loja.get(str(peca_loja_id_base))
                if not base_id:
                    cursor.execute('''
                        SELECT id FROM pecas WHERE carro_id = %s AND equipe_id = %s AND instalado = 1
                          AND peca_loja_id = %s AND (upgrade_id IS NULL OR upgrade_id = '')
                        LIMIT 1
                    ''', (carro_id, equipe_id_str, peca_loja_id_base))
                    row = cursor.fetchone()
                    base_id = row[0] if row else None
                if not base_id:
                    print(f"[REPOUSO] Upgrade {peca_nome} ignorado: nenhuma peça base correspondente no carro")
                    continue
                cursor.execute('''
                    UPDATE pecas SET instalado_em_peca_id = %s, carro_id = %s, instalado = 1 WHERE id = %s
                ''', (base_id, carro_id, peca_armazem['id']))
                conn.commit()
                used_ids.add(peca_armazem['id'])
                pecas_instaladas += 1
                api.db.salvar_solicitacao_peca(str(uuid.uuid4()), equipe_id_str, peca_armazem['id'], 1, 'instalada', carro_id)
                print(f"[REPOUSO] Upgrade instalado na base: {peca_nome}")
        finally:
            conn.close()
        
        return jsonify({
            'sucesso': True,
            'pecas_instaladas': pecas_instaladas
        })
        
    except Exception as e:
        print(f"[ERRO REPOUSO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/instalar-multiplas-pecas-no-carro-ativo', methods=['POST'], strict_slashes=False)
def instalar_multiplas_pecas_armazem_ativo():
    """Cria transação PIX para instalar múltiplas peças do armazém no carro ativo via modal"""
    print("[ATIVO MODAL PIX] ===== ROTA ATIVADA =====", flush=True)
    try:
        
        # Auth check
        if 'equipe_id' not in session and not request.headers.get('X-Equipe-ID'):
            print("[ATIVO MODAL PIX] Erro: Não autenticado")
            return jsonify({'erro': 'Não autenticado'}), 401
            
        dados = request.json
        print(f"[ATIVO MODAL PIX] Dados recebidos: {dados}")
        
        carro_id = dados.get('carro_id')
        pecas = dados.get('pecas', [])
        
        if not carro_id or not pecas or len(pecas) == 0:
            print("[ATIVO MODAL PIX] Erro: Dados inválidos")
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400
        
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            print("[ATIVO MODAL PIX] Erro: Equipe não encontrada")
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        equipe_id_str = str(equipe_id)
        
        print(f"[ATIVO MODAL PIX] Criando PIX para {len(pecas)} peça(s), equipe_id={equipe_id_str}")
        
        # Carregar peças do armazém
        print(f"[ATIVO MODAL PIX] Carregando peças do armazém...")
        pecas_armazem = api.db.carregar_pecas_armazem_equipe(equipe_id_str)
        print(f"[ATIVO MODAL PIX] Peças do armazém carregadas: {len(pecas_armazem)}")
        pecas_loja = api.db.carregar_pecas_loja()
        print(f"[ATIVO MODAL PIX] Peças da loja carregadas: {len(pecas_loja)}")
        upgrades_loja = api.db.carregar_upgrades()
        print(f"[ATIVO MODAL PIX] Upgrades da loja carregados: {len(upgrades_loja)}")
        
        # Validar upgrades: precisam da peça base no carro ou na seleção
        def achar_no_armazem(nome, tipo, eh_upgrade):
            for p in pecas_armazem:
                if p['nome'].lower() != nome.lower() or p['tipo'].lower() != tipo.lower():
                    continue
                if eh_upgrade and not p.get('upgrade_id'):
                    continue
                if not eh_upgrade and p.get('upgrade_id'):
                    continue
                return p
            return None
        bases_no_carro = set()
        if api.db._column_exists('pecas', 'upgrade_id'):
            conn_ac = api.db._get_conn()
            cur_ac = conn_ac.cursor()
            cur_ac.execute('''
                SELECT peca_loja_id FROM pecas WHERE carro_id = %s AND equipe_id = %s AND instalado = 1
                  AND (upgrade_id IS NULL OR upgrade_id = '') AND peca_loja_id IS NOT NULL
            ''', (carro_id, equipe_id_str))
            for row in cur_ac.fetchall():
                if row[0]:
                    bases_no_carro.add(str(row[0]))
            conn_ac.close()
        bases_na_selecao = set()
        for peca_req in pecas:
            p = achar_no_armazem(peca_req.get('nome', ''), peca_req.get('tipo', ''), eh_upgrade=False)
            if p and p.get('peca_loja_id'):
                bases_na_selecao.add(str(p['peca_loja_id']))
        upgrades_sem_base = []
        for peca_req in pecas:
            p = achar_no_armazem(peca_req.get('nome', ''), peca_req.get('tipo', ''), eh_upgrade=True)
            if not p or not p.get('peca_loja_id'):
                continue
            if str(p['peca_loja_id']) in bases_na_selecao or str(p['peca_loja_id']) in bases_no_carro:
                continue
            upgrades_sem_base.append(p.get('nome', peca_req.get('nome', 'Upgrade')))
        if upgrades_sem_base:
            nomes = ', '.join(upgrades_sem_base)
            return jsonify({
                'sucesso': False,
                'erro': f'Para instalar o(s) upgrade(s) "{nomes}" é necessário ter a peça base correspondente (ex.: motor) no carro ou selecionada para instalação.'
            }), 400
        
        # Validar que todas as peças existem: loja (base) OU upgrade_loja (upgrades) OU armazém
        print(f"[ATIVO MODAL PIX] Validação: {len(pecas)} peça(s) pedida(s). Loja {len(pecas_loja)}. Upgrade_loja {len(upgrades_loja)}. Armazém {len(pecas_armazem)}.", flush=True)
        for peca_req in pecas:
            peca_nome = peca_req.get('nome')
            peca_tipo = (peca_req.get('tipo') or '').lower()
            
            # Buscar na loja (peças base)
            encontrada_loja = False
            for p in pecas_loja:
                if p.nome.lower() == peca_nome.lower() and (p.tipo or '').lower() == peca_tipo:
                    encontrada_loja = True
                    break
            if encontrada_loja:
                continue
            # Se tipo é upgrade: verificar upgrade_loja
            if peca_tipo == 'upgrade':
                encontrada_upgrade_loja = any(u.get('nome', '').lower() == peca_nome.lower() for u in upgrades_loja)
                if encontrada_upgrade_loja:
                    continue
            # Verificar armazém (peças e upgrades já comprados)
            encontrada_armazem = any(
                (p.get('nome') or '').lower() == peca_nome.lower() and (p.get('tipo') or '').lower() == peca_tipo
                for p in pecas_armazem
            )
            if not encontrada_armazem:
                print(f"[ATIVO MODAL PIX] *** ERRO VALIDAÇÃO: peça não está na loja nem no armazém ***", flush=True)
                print(f"[ATIVO MODAL PIX] peca_nome={repr(peca_nome)} peca_tipo={repr(peca_tipo)}", flush=True)
                print(f"[ATIVO MODAL PIX] Retornando 400 (não 404). Peça precisa estar no catálogo (loja) ou já no armazém.", flush=True)
                return jsonify({'sucesso': False, 'erro': f'Peça {peca_nome} não encontrada no armazém'}), 400
        
        # Calcular valor do PIX (uma instalação por peça)
        preco_config = float(api.db.obter_configuracao('preco_instalacao_warehouse') or '10')
        valor_total_itens = preco_config * len(pecas)  # Uma instalação por peça
        taxa = valor_total_itens * 0.01
        valor_total = valor_total_itens + taxa
        
        print(f"[ATIVO MODAL PIX] Valor: R$ {valor_total_itens:.2f} + R$ {taxa:.2f} taxa = R$ {valor_total:.2f}")
        
        # Criar transação PIX
        from src.mercado_pago_client import mp_client
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        equipe_nome = equipe.nome if equipe else 'Desconhecido'
        
        nomes_pecas = ', '.join([p.get('nome', 'Desconhecido') for p in pecas])
        if len(nomes_pecas) > 50:
            nomes_pecas = f"{len(pecas)} peça(s)"
        
        transacao_id = api.db.criar_transacao_pix(
            equipe_id=equipe_id_str,
            equipe_nome=equipe_nome,
            tipo_item='multiplas_pecas_armazem_ativo_modal',
            item_id=carro_id,
            item_nome=f'{nomes_pecas} → Carro Ativo',
            valor_item=valor_total_itens,
            valor_taxa=taxa,
            carro_id=carro_id,
            dados_adicionais={'pecas': pecas}
        )
        
        if not transacao_id:
            return jsonify({'sucesso': False, 'erro': 'Erro ao criar transação PIX'}), 500
        
        # Gerar um pix_id para associar às peças
        pix_id_pecas = str(uuid.uuid4())
        
        # Gerar QR Code
        descricao = f"Instalação: {nomes_pecas}"
        resultado_mp = mp_client.gerar_qr_code_pix(descricao, valor_total, transacao_id)
        
        if not resultado_mp.get('sucesso'):
            return jsonify({'sucesso': False, 'erro': 'Erro ao gerar QRCode'}), 500
        
        qr_code_url = resultado_mp.get('qr_code_url')
        mercado_pago_id = resultado_mp.get('id')
        
        api.db.atualizar_transacao_pix(
            transacao_id=transacao_id,
            mercado_pago_id=mercado_pago_id,
            qr_code=resultado_mp.get('qr_code', ''),
            qr_code_url=qr_code_url
        )
        
        print(f"[ATIVO MODAL PIX] ✅ PIX gerado com sucesso. pix_id={pix_id_pecas}")
        
        return jsonify({
            'sucesso': True,
            'transacao_id': transacao_id,
            'pix_id': pix_id_pecas,  # Retornar pix_id para associar às peças
            'qr_code_url': qr_code_url,
            'valor_item': valor_total_itens,
            'valor_taxa': taxa,
            'valor_total': valor_total,
            'pecas_processadas': len(pecas)
        })
        
    except Exception as e:
        print(f"[ERRO ATIVO MODAL PIX] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/garagem/criar-multiplas-solicitacoes-armazem', methods=['POST'])
@requer_login_api
def criar_multiplas_solicitacoes_armazem():
    """Cria múltiplas solicitações de instalação do armazém"""
    try:
        dados = request.json
        print(f"[SOLICITAÇÕES] Dados recebidos: {dados}")
        
        carro_id = dados.get('carro_id')
        pecas = dados.get('pecas', [])
        com_pix = dados.get('com_pix', False)
        
        print(f"[SOLICITAÇÕES] carro_id={carro_id}, pecas={len(pecas)}, com_pix={com_pix}")
        
        if not carro_id or not pecas:
            print(f"[SOLICITAÇÕES] Dados inválidos: carro_id={carro_id}, pecas={pecas}")
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400
        
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        equipe_id_str = str(equipe_id)
        
        # Carregar peças
        pecas_armazem = api.db.carregar_pecas_armazem_equipe(equipe_id_str)
        pecas_loja = api.db.carregar_pecas_loja()
        
        print(f"[SOLICITAÇÕES] Peças armazém: {len(pecas_armazem)}, Peças loja: {len(pecas_loja)}")
        
        solicitacoes_criadas = 0
        
        for peca_req in pecas:
            peca_nome = peca_req.get('nome')
            peca_tipo = peca_req.get('tipo')
            quantidade = peca_req.get('quantidade', 1)
            
            print(f"[SOLICITAÇÕES] Processando: {peca_nome} ({peca_tipo}) x{quantidade}")
            
            # Buscar peça na loja (base) ou no armazém (upgrade)
            peca_loja = None
            for p in pecas_loja:
                if p.nome.lower() == peca_nome.lower() and p.tipo.lower() == peca_tipo.lower():
                    peca_loja = p
                    break
            
            peca_armazem = None
            if not peca_loja:
                for p in pecas_armazem:
                    if p['nome'].lower() == peca_nome.lower() and p['tipo'].lower() == peca_tipo.lower():
                        peca_armazem = p
                        break
            
            peca_id = peca_loja.id if peca_loja else (peca_armazem['id'] if peca_armazem else None)
            if not peca_id:
                print(f"[SOLICITAÇÕES] Peça {peca_nome} não encontrada na loja nem no armazém")
                continue
            
            # Criar solicitação para cada quantidade (evita duplicata: só cria se não existir pendente mesma peça+carro)
            for qtd in range(quantidade):
                solicitacao_id = str(uuid.uuid4())
                ok = api.db.salvar_solicitacao_peca(
                    id=solicitacao_id,
                    equipe_id=equipe_id_str,
                    peca_id=peca_id,
                    quantidade=1,
                    status='pendente',
                    carro_id=carro_id
                )
                if ok:
                    solicitacoes_criadas += 1
                    print(f"[SOLICITAÇÕES] Criada solicitação para {peca_nome}")
        
        print(f"[SOLICITAÇÕES] Total criado: {solicitacoes_criadas}")
        return jsonify({
            'sucesso': True,
            'solicitacoes_criadas': solicitacoes_criadas
        })
        
    except Exception as e:
        print(f"[ERRO SOLICITAÇÕES] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/garagem/<uuid:equipe_id>', methods=['GET'])
@requer_login_api
def get_garagem(equipe_id):
    """Retorna dados da garagem da equipe (carros e peças). UUID evita que paths como instalar-multiplas-pecas-armazem-ativo caiam aqui (404)."""
    try:
        auth_equipe_id = obter_equipe_id_request()
        if not auth_equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401

        equipe_id_str = str(equipe_id)
        # Verificar se o equipe_id da URL corresponde ao usuário autenticado
        if equipe_id_str != auth_equipe_id:
            return jsonify({'erro': 'Acesso negado'}), 403

        # Carregar equipe do banco de dados (não da memória)
        equipe = api.db.carregar_equipe(equipe_id_str)
        if not equipe:
            return jsonify({'erro': 'Equipe não encontrada'}), 404

        carros = []

        # Processar todos os carros da equipe
        for carro in equipe.carros:
            print(f"[DEBUG] Processando carro: {carro.marca} {carro.modelo}")

            # Determinar status baseado no status do carro no banco (não apenas em memória)
            carro_status_banco = getattr(carro, 'status', 'repouso')  # 'ativo' ou 'repouso'
            status_carro = carro_status_banco

            # Buscar peças instaladas com compatibilidades (durabilidade da tabela pecas, não pecas_loja)
            pecas_instaladas = api.db.obter_pecas_carro_com_compatibilidade(carro.id)

            # Condição geral = média da durabilidade atual das peças (0-100%)
            condicao_geral = 100.0
            if pecas_instaladas:
                total = 0
                n = 0
                for peca in pecas_instaladas:
                    v_max = float(peca.get('durabilidade_maxima') or 100)
                    v_atual = float(peca.get('durabilidade_atual') or 100)
                    if v_max > 0:
                        total += (v_atual / v_max) * 100
                        n += 1
                if n:
                    condicao_geral = round(total / n, 1)

            carro_info = {
                'id': carro.id,
                'marca': carro.marca,
                'modelo': carro.modelo,
                'numero_carro': carro.numero_carro,
                'classe': getattr(carro, 'classe', 'N/A'),
                'modelo_id': getattr(carro, 'modelo_id', None),
                'status': status_carro,
                'carro_ativo': status_carro == 'ativo',
                'apelido': getattr(carro, 'apelido', None),
                'imagem_url': getattr(carro, 'imagem_url', None),
                'condicao_geral': condicao_geral,
                'pecas': pecas_instaladas
            }

            carros.append(carro_info)

        return jsonify({'carros': carros})
    except Exception as e:
        print(f"[ERRO GARAGEM] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao carregar garagem'}), 500


@app.route('/api/armazem/<equipe_id>')
@requer_login_api
def get_armazem(equipe_id):
    """Retorna peças guardadas no armazém da equipe"""
    try:
        # Verificar autenticação
        auth_equipe_id = obter_equipe_id_request()
        if not auth_equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        
        # Se for uma equipe (não admin), só pode acessar seus próprios dados
        if request.headers.get('X-Equipe-ID'):
            if str(auth_equipe_id) != str(equipe_id):
                return jsonify({'erro': 'Acesso negado'}), 403
            # Usar o equipe_id da header/session
            equipe_id_buscar = str(auth_equipe_id)
        else:
            # Admin pode acessar qualquer equipe
            equipe_id_buscar = str(equipe_id)
        
        print(f"[ARMAZÉM] Buscando peças para equipe: {equipe_id_buscar}")
        
        # Buscar todas as peças com instalado = 0 (no armazém) desta equipe
        pecas_guardadas = api.db.carregar_pecas_armazem_equipe(equipe_id_buscar)
        
        # Ordenar por tipo
        pecas_guardadas.sort(key=lambda x: x.get('tipo', ''))
        
        print(f"[ARMAZÉM] Encontradas {len(pecas_guardadas)} peças para equipe {equipe_id_buscar}")
        
        return jsonify({
            'pecas_guardadas': pecas_guardadas,
            'total': len(pecas_guardadas)
        })
    except Exception as e:
        print(f"[ERRO ARMAZÉM] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS API - LOJA =============

@app.route('/api/loja/carros')
def get_carros():
    """Retorna carros disponíveis para compra com variações"""
    carros = []
    
    # Sempre recarregar modelos direto do banco para garantir sincronização
    modelos_db = api.db.carregar_modelos_loja()
    
    print(f"\n[API LOJA CARROS] Carregando do banco: {len(modelos_db) if modelos_db else 0} modelos")
    
    # Se não houver modelos no banco, retornar lista vazia
    if not modelos_db or len(modelos_db) == 0:
        print(f"[API LOJA CARROS] Nenhum modelo disponível")
        return jsonify([])
    
    # Usar os dados do banco
    for carro in modelos_db:
        print(f"[API LOJA CARROS] Processando modelo: {carro.marca} {carro.modelo}")
        carro_dict = {
            'id': carro.id,
            'marca': carro.marca,
            'modelo': carro.modelo,
            'preco': carro.preco,
            'variacoes': []  # Lista de variações
        }
        
        # Incluir imagem se existir
        imagem = getattr(carro, 'imagem', None)
        if imagem:
            carro_dict['imagem'] = imagem
            carro_dict['temImagem'] = True
            print(f"  [{carro.modelo}] tem_imagem=True (com base64)")
        else:
            print(f"  [{carro.modelo}] tem_imagem=False")
        
        # Processar variações deste modelo
        variacoes = getattr(carro, 'variacoes', [])
        print(f"  [{carro.modelo}] {len(variacoes)} variação(ões)")
        
        for variacao in variacoes:
            variacao_dict = {
                'id': variacao.id,
                'modelo_id': variacao.modelo_carro_loja_id,
                'valor': getattr(variacao, 'valor', 0.0),  # Incluir valor da variação
                'pecas': {}
            }
            
            # Motor
            if variacao.motor_id:
                motor_peca = api.db.buscar_peca_loja_por_id(variacao.motor_id)
                if motor_peca:
                    variacao_dict['pecas']['motor'] = motor_peca.nome
                    variacao_dict['pecas']['motor_id'] = variacao.motor_id
            else:
                variacao_dict['pecas']['motor'] = '❌ nenhum'
            
            # Câmbio
            if variacao.cambio_id:
                cambio_peca = api.db.buscar_peca_loja_por_id(variacao.cambio_id)
                if cambio_peca:
                    variacao_dict['pecas']['cambio'] = cambio_peca.nome
                    variacao_dict['pecas']['cambio_id'] = variacao.cambio_id
            else:
                variacao_dict['pecas']['cambio'] = '❌ nenhum'
            
            # Suspensão
            if variacao.suspensao_id:
                suspensao_peca = api.db.buscar_peca_loja_por_id(variacao.suspensao_id)
                if suspensao_peca:
                    variacao_dict['pecas']['suspensao'] = suspensao_peca.nome
            else:
                variacao_dict['pecas']['suspensao'] = '❌ nenhum'
            
            # Kit Ângulo
            if variacao.kit_angulo_id:
                kit_peca = api.db.buscar_peca_loja_por_id(variacao.kit_angulo_id)
                if kit_peca:
                    variacao_dict['pecas']['kit_angulo'] = kit_peca.nome
            else:
                variacao_dict['pecas']['kit_angulo'] = '❌ nenhum'
            
            # Diferencial
            if variacao.diferencial_id:
                diferencial_peca = api.db.buscar_peca_loja_por_id(variacao.diferencial_id)
                if diferencial_peca:
                    variacao_dict['pecas']['diferencial'] = diferencial_peca.nome
            else:
                variacao_dict['pecas']['diferencial'] = '❌ nenhum'
            
            carro_dict['variacoes'].append(variacao_dict)
        
        carros.append(carro_dict)
    
    return jsonify(carros)

@app.route('/api/loja/pecas')
def get_pecas():
    """Retorna peças disponíveis para compra (sem autenticação necessária)"""
    equipe_id = obter_equipe_id_request()
    equipe = api.gerenciador.obter_equipe(equipe_id) if equipe_id else None
    
    print(f"\n[LOJA PECAS] Carregando peças para equipe: {equipe_id}")
    if equipe:
        print(f"[LOJA PECAS] Equipe encontrada: {equipe.nome}")
        if equipe.carro:
            print(f"[LOJA PECAS] Carro ativo: {equipe.carro.marca} {equipe.carro.modelo}")
        else:
            print(f"[LOJA PECAS] Equipe sem carro ativo!")
    else:
        print(f"[LOJA PECAS] Equipe não encontrada!")
    
    # Recarregar dados do banco para garantir sincronização
    modelos_db = api.db.carregar_modelos_loja()
    if modelos_db:
        api.loja_carros.modelos = modelos_db
    
    pecas_db = api.db.carregar_pecas_loja()
    if pecas_db:
        api.loja_pecas.pecas = pecas_db
    
    print(f"\n[API] Retornando peças")
    pecas = []
    modelos_map = {}
    # Montar um dicionário id -> modelo para lookup rápido
    if hasattr(api, 'loja_carros') and hasattr(api.loja_carros, 'modelos'):
        for modelo in api.loja_carros.modelos:
            modelos_map[str(modelo.id)] = modelo

    if api.loja_pecas and hasattr(api.loja_pecas, 'pecas'):
        for peca in api.loja_pecas.pecas:
            compatibilidade_peca = getattr(peca, 'compatibilidade', 'universal')
            compatibilidade_nome = 'universal'
            
            # Debug
            print(f"[LOJA PECAS] Peça '{peca.nome}' - compatibilidade type: {type(compatibilidade_peca).__name__}, valor: {compatibilidade_peca}")
            
            # Tratamento para compatibilidade como objeto JSON (string ou dict)
            # Se for string JSON, fazer parse
            if isinstance(compatibilidade_peca, str):
                try:
                    if compatibilidade_peca.startswith('{'):
                        import json
                        compatibilidade_peca = json.loads(compatibilidade_peca)
                        print(f"[LOJA PECAS] '{peca.nome}' parseado como JSON: {compatibilidade_peca}")
                except:
                    pass  # Não é JSON válido, continuar como string
            
            # Se compatibilidade_peca é um dict/objeto com chave "compatibilidades", extrair a lista
            if isinstance(compatibilidade_peca, dict) and 'compatibilidades' in compatibilidade_peca:
                compatibilidades_list = compatibilidade_peca['compatibilidades']
                # Se houver múltiplas compatibilidades, usar a primeira, senão usar universal
                if compatibilidades_list and len(compatibilidades_list) > 0:
                    compatibilidade_peca = compatibilidades_list[0]
                    print(f"[LOJA PECAS] '{peca.nome}' - extraído compatibilidade: {compatibilidade_peca}")
                else:
                    compatibilidade_peca = 'universal'
            
            # Se compatibilidade é um UUID específico, buscar o nome do modelo
            if compatibilidade_peca != 'universal':
                modelo_id = str(compatibilidade_peca)
                if modelo_id in modelos_map:
                    modelo = modelos_map[modelo_id]
                    compatibilidade_nome = f"{modelo.marca} {modelo.modelo}"
                    print(f"[LOJA PECAS] '{peca.nome}' - modelo encontrado: {compatibilidade_nome}")
                else:
                    # UUID não corresponde a nenhum modelo, usar como universal
                    print(f"[LOJA PECAS] '{peca.nome}' - UUID não encontrado, tratando como universal: {compatibilidade_peca}")
                    compatibilidade_peca = 'universal'
                    compatibilidade_nome = 'universal'
            
            # Retornar nome do modelo para exibição, e UUID para comparação
            peca_dict = {
                'id': peca.id,
                'nome': peca.nome,
                'tipo': getattr(peca, 'tipo', 'motor'),
                'preco': peca.preco,
                'descricao': getattr(peca, 'descricao', ''),
                'compatibilidade': compatibilidade_peca,  # UUID para comparação
                'compatibilidade_nome': compatibilidade_nome  # Nome do modelo para exibição
            }
            
            # Incluir imagem se existir
            imagem = getattr(peca, 'imagem', None)
            if imagem:
                peca_dict['imagem'] = imagem
                peca_dict['temImagem'] = True
                print(f"  [{peca.nome}] tem_imagem=True (com base64)")
            else:
                print(f"  [{peca.nome}] tem_imagem=False")
            
            pecas.append(peca_dict)

    # Incluir upgrades na lista, com o tipo da peça associada (aparecem na aba Motor, Câmbio, etc.)
    try:
        upgrades = api.db.carregar_upgrades()
        for u in upgrades:
            peca_tipo = (u.get('peca_tipo') or 'motor').strip() or 'motor'
            pecas.append({
                'id': 'upgrade_' + str(u['id']),
                'nome': u.get('nome', ''),
                'tipo': peca_tipo,
                'preco': float(u.get('preco') or 0),
                'descricao': u.get('descricao') or '',
                'compatibilidade': 'universal',
                'compatibilidade_nome': 'universal',
                'is_upgrade': True,
                'peca_nome': u.get('peca_nome') or '-',
                'imagem': u.get('imagem'),
            })
    except Exception as e:
        print(f"[API] Aviso ao incluir upgrades: {e}")

    print(f"[API] Total de peças retornadas: {len(pecas)}\n")
    return jsonify(pecas)

@app.route('/api/loja/upgrades')
def get_upgrades():
    """Retorna upgrades disponíveis para compra (filtro Upgrade na loja)"""
    try:
        upgrades = api.db.carregar_upgrades()
        return jsonify(upgrades)
    except Exception as e:
        print(f"[ERRO LOJA UPGRADES] {e}")
        return jsonify([])

@app.route('/api/aguardando-pecas', methods=['GET'])
def get_aguardando_pecas():
    """Retorna apenas peças aguardando instalação (não carros)"""
    print("\n" + "="*70)
    print("[AGUARDANDO-PECAS] ROTA ATIVADA!")
    print(f"[AGUARDANDO-PECAS] X-Equipe-ID: {request.headers.get('X-Equipe-ID')}")
    print(f"[AGUARDANDO-PECAS] Session equipe_id: {session.get('equipe_id')}")
    try:
        equipe_id = obter_equipe_id_request()
        print(f"[AGUARDANDO-PECAS] obter_equipe_id retornou: {equipe_id}")
        if not equipe_id and 'equipe_id' in session:
            equipe_id = session['equipe_id']
            print(f"[AGUARDANDO-PECAS] Usando session equipe_id: {equipe_id}")
        if not equipe_id:
            print(f"[AGUARDANDO-PECAS] ERRO 401: Nao autenticado")
            print("="*70)
            return jsonify({'erro': 'Nao autenticado'}), 401
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        print(f"[AGUARDANDO-PECAS] Equipe carregada: {equipe.nome if equipe else 'NULO'}")
        if not equipe:
            print(f"[AGUARDANDO-PECAS] ERRO 404: Equipe nao encontrada")
            print("="*70)
            return jsonify({'erro': 'Equipe nao encontrada'}), 404
        
        pecas_aguardando = []
        try:
            solicitacoes_db = api.db.carregar_solicitacoes_pecas(equipe_id)
            # Apenas adicionar PEÇAS (não carros)
            for sol in solicitacoes_db:
                if sol['status'] == 'pendente':
                    carro_info = None
                    carro_id = sol.get('carro_id')
                    if carro_id:
                        for c in equipe.carros:
                            if str(c.id) == str(carro_id):
                                carro_info = {
                                    'id': c.id,
                                    'numero': c.numero_carro,
                                    'marca': c.marca,
                                    'modelo': c.modelo,
                                    'status': c.status
                                }
                                break
                    if not carro_info and equipe.carro:
                        carro_info = {
                            'id': equipe.carro.id,
                            'numero': equipe.carro.numero_carro,
                            'marca': equipe.carro.marca,
                            'modelo': equipe.carro.modelo,
                            'status': equipe.carro.status
                        }
                    pecas_aguardando.append({
                        'id': sol.get('id'),
                        'peca_nome': sol.get('peca_nome') or '',
                        'peca_tipo': (sol.get('peca_tipo') or sol.get('tipo_peca')) or '',
                        'preco': sol.get('preco', 0),
                        'carro': carro_info,
                        'timestamp': sol.get('data_solicitacao', '')
                    })
        except Exception as e:
            print(f"[AGUARDANDO-PECAS] Erro ao carregar solicitações: {str(e)}")
        
        pecas_aguardando.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        print(f"[AGUARDANDO-PECAS] Retornando {len(pecas_aguardando)} peças")
        print("="*70)
        return jsonify(pecas_aguardando)
    except Exception as e:
        print(f"[AGUARDANDO-PECAS] ERRO: {str(e)}")
        print("="*70)
        return jsonify({'erro': str(e)}), 500

@app.route('/api/aguardando-carros', methods=['GET'])
def get_aguardando_carros():
    """Retorna apenas carros aguardando compra (não peças)"""
    print("\n" + "="*70)
    print("[AGUARDANDO-CARROS] ROTA ATIVADA!")
    try:
        equipe_id = obter_equipe_id_request()
        if not equipe_id and 'equipe_id' in session:
            equipe_id = session['equipe_id']
        if not equipe_id:
            print(f"[AGUARDANDO-CARROS] ERRO 401: Nao autenticado")
            print("="*70)
            return jsonify({'erro': 'Nao autenticado'}), 401
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            print(f"[AGUARDANDO-CARROS] ERRO 404: Equipe nao encontrada")
            print("="*70)
            return jsonify({'erro': 'Equipe nao encontrada'}), 404
        
        carros_aguardando = []
        try:
            solicitacoes_carros = api.db.carregar_solicitacoes_carros(equipe_id)
            print(f"[AGUARDANDO-CARROS] Total de solicitações carregadas: {len(solicitacoes_carros) if solicitacoes_carros else 0}")
            
            if solicitacoes_carros:
                for sol in solicitacoes_carros:
                    print(f"[AGUARDANDO-CARROS] Solicitação: ID={sol.get('id')}, status={sol.get('status')}, tipo_carro={sol.get('tipo_carro')}")
                    if sol['status'] == 'pendente':
                        # 1) Usar marca/modelo já preenchidos por carregar_solicitacoes_carros (carro encontrado na equipe)
                        if sol.get('marca') and sol.get('modelo'):
                            carro_id = sol.get('carro_id')
                            pecas = api.db.obter_pecas_instaladas_carro(carro_id) if carro_id else []
                            carros_aguardando.append({
                                'id': sol.get('id'),
                                'marca': sol['marca'],
                                'modelo': sol['modelo'],
                                'classe': sol.get('classe', 'N/A'),
                                'preco': sol.get('preco', 0),
                                'timestamp': sol.get('data_solicitacao', ''),
                                'pecas': pecas
                            })
                            continue
                        # 2) Parse tipo_carro: "carro_id|Marca|Modelo" ou UUID (legacy)
                        tipo_carro_str = sol.get('tipo_carro') or ''
                        marca = None
                        modelo_name = None
                        carro_id = None
                        if '|' in tipo_carro_str:
                            parts = tipo_carro_str.split('|')
                            carro_id = parts[0]
                            marca = parts[1] if len(parts) > 1 else None
                            modelo_name = parts[2] if len(parts) > 2 else None
                        else:
                            carro_id = tipo_carro_str
                        # 3) Se já temos marca/modelo do tipo_carro, usar
                        if marca and modelo_name:
                            pecas = api.db.obter_pecas_instaladas_carro(carro_id) if carro_id else []
                            carros_aguardando.append({
                                'id': sol.get('id'),
                                'marca': marca,
                                'modelo': modelo_name,
                                'classe': 'N/A',
                                'preco': 0,
                                'timestamp': sol.get('data_solicitacao', ''),
                                'pecas': pecas
                            })
                            continue
                        # 4) Tentar buscar modelo na loja (só quando tipo_carro é UUID de modelo, legacy)
                        modelo = None
                        if carro_id:
                            for m in api.loja_carros.modelos:
                                if str(m.id) == str(carro_id):
                                    modelo = m
                                    break
                            if not modelo:
                                modelo = api.db.buscar_modelo_loja_por_id(carro_id)
                        if modelo:
                            pecas = api.db.obter_pecas_instaladas_carro(carro_id) if carro_id else []
                            carros_aguardando.append({
                                'id': sol.get('id'),
                                'marca': modelo.marca,
                                'modelo': modelo.modelo,
                                'classe': getattr(modelo, 'classe', 'N/A'),
                                'preco': modelo.preco,
                                'timestamp': sol.get('data_solicitacao', ''),
                                'pecas': pecas
                            })
                        else:
                            # 5) Fallback: buscar marca/modelo do carro no BD pelo carro_id
                            nome_marca = marca or 'Modelo Deletado'
                            nome_modelo = modelo_name or 'Desconhecido'
                            carro_id_fk = sol.get('carro_id')
                            if carro_id_fk:
                                mar_mod = api.db.obter_marca_modelo_carro(carro_id_fk)
                                if mar_mod and mar_mod[0] and mar_mod[1]:
                                    nome_marca, nome_modelo = mar_mod[0], mar_mod[1]
                            pecas = api.db.obter_pecas_instaladas_carro(carro_id_fk) if carro_id_fk else []
                            carros_aguardando.append({
                                'id': sol.get('id'),
                                'marca': nome_marca,
                                'modelo': nome_modelo,
                                'classe': 'N/A',
                                'preco': 0,
                                'timestamp': sol.get('data_solicitacao', ''),
                                'pecas': pecas
                            })
        except Exception as e:
            print(f"[AGUARDANDO-CARROS] Erro ao carregar solicitações: {str(e)}")
            import traceback
            traceback.print_exc()
        
        carros_aguardando.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        print(f"[AGUARDANDO-CARROS] Retornando {len(carros_aguardando)} carros")
        print("="*70)
        return jsonify(carros_aguardando)
    except Exception as e:
        print(f"[AGUARDANDO-CARROS] ERRO: {str(e)}")
        print("="*70)
        return jsonify({'erro': str(e)}), 500

# ============ ROTAS API - ETAPAS =============

@app.route('/api/loja/etapas')
def get_etapas():
    """Retorna todas as etapas do campeonato"""
    try:
        etapas = api.db.listar_etapas()
        return jsonify(etapas)
    except Exception as e:
        print(f"[ERRO] Erro ao listar etapas: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/pilotos/<piloto_id>/etapas')
def get_etapas_piloto(piloto_id):
    """Retorna etapas em que o piloto está inscrito"""
    try:
        etapas = api.db.obter_etapas_piloto(piloto_id)
        return jsonify({'etapas': etapas})
    except Exception as e:
        print(f"[ERRO] Erro ao obter etapas do piloto: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/etapas/participar', methods=['POST'])
def participar_etapa():
    """Inscreve piloto como candidato para uma equipe em uma etapa"""
    try:
        dados = request.json
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id')
        piloto_id = session.get('piloto_id')
        piloto_nome = session.get('piloto_nome')
        
        if not etapa_id or not equipe_id or not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'Etapa, equipe e piloto são obrigatórios'}), 400
        
        print(f"[PILOTO CANDIDATO] Piloto {piloto_nome} ({piloto_id}) candidatando-se para equipe {equipe_id} na etapa {etapa_id}")
        
        resultado = api.db.inscrever_piloto_candidato_etapa(etapa_id, equipe_id, piloto_id, piloto_nome)
        
        if resultado['sucesso']:
            print(f"[PILOTO CANDIDATO] ✅ Piloto {piloto_nome} inscrito como candidato")
            return jsonify(resultado)
        else:
            print(f"[PILOTO CANDIDATO] ❌ Erro: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[ERRO] Erro ao inscrever piloto em etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/<etapa_id>/equipes-procurando-piloto', methods=['GET'])
def obter_equipes_etapa(etapa_id):
    """Retorna equipes de uma etapa categorizadas por tipo de participação com carro e peças"""
    try:
        print(f"[ROTA DEBUG] GET /api/etapas/{etapa_id}/equipes-procurando-piloto")
        # Buscar todas as equipes inscritas nesta etapa
        equipes_inscritas = api.db.obter_equipes_etapa(etapa_id)
        
        if not equipes_inscritas:
            return jsonify({
                'sucesso': True,
                'contratantes': [],
                'procurando_piloto': []
            })
        
        # Categorizar por tipo de participação
        contratantes = []
        procurando_piloto = []
        
        for equipe in equipes_inscritas:
            equipe_id = equipe.get('equipe_id')
            carro_id = equipe.get('carro_id')
            
            carro_ativo = None
            pecas = []
            
            if carro_id:
                # Buscar carro específico da participação
                carro_obj = api.db.carregar_carro(carro_id)
                if carro_obj:
                    carro_ativo = {
                        'id': carro_obj.id,
                        'marca': carro_obj.marca,
                        'modelo': carro_obj.modelo,
                        'apelido': getattr(carro_obj, 'apelido', None)
                    }
                    # Buscar peças instaladas do carro
                    pecas = api.db.obter_pecas_carro_com_compatibilidade(carro_id) or []
            
            equipe_info = {
                'equipe_id': equipe_id,
                'equipe_nome': equipe.get('equipe_nome'),
                'tipo': equipe.get('tipo_participacao'),
                'carro': carro_ativo,
                'pecas': pecas
            }
            
            if equipe.get('tipo_participacao') == 'tenho_piloto':
                contratantes.append(equipe_info)
            elif equipe.get('tipo_participacao') == 'precisa_piloto':
                procurando_piloto.append(equipe_info)
        
        return jsonify({
            'sucesso': True,
            'contratantes': contratantes,
            'procurando_piloto': procurando_piloto
        })
    except Exception as e:
        print(f"[ERRO] Erro ao buscar equipes da etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/equipes/<equipe_id>/etapas')
def get_etapas_equipe(equipe_id):
    """Retorna etapas em que a equipe está inscrita"""
    try:
        etapas = api.db.obter_etapas_equipe(equipe_id)
        return jsonify({'etapas': etapas})
    except Exception as e:
        print(f"[ERRO] Erro ao obter etapas da equipe: {e}")
        return jsonify({'erro': str(e)}), 500



@app.route('/api/etapas/<etapa_id>/candidatos-pilotos')
def obter_candidatos_pilotos(etapa_id):
    """Retorna lista de candidatos pilotos por equipe para uma etapa"""
    try:
        candidatos = api.db.obter_candidatos_piloto_etapa(etapa_id)
        return jsonify({'sucesso': True, 'candidatos': candidatos})
    except Exception as e:
        print(f"[ERRO] Erro ao obter candidatos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/designar-piloto-etapa', methods=['POST'])
def admin_designar_piloto_etapa():
    """Admin designa um piloto para pilotar uma equipe em uma etapa"""
    try:
        dados = request.json
        candidato_id = dados.get('candidato_id')
        
        if not candidato_id:
            return jsonify({'sucesso': False, 'erro': 'candidato_id é obrigatório'}), 400
        
        resultado = api.db.designar_piloto_etapa(candidato_id)
        
        if resultado['sucesso']:
            print(f"[ADMIN] ✅ Piloto designado para equipe")
            return jsonify(resultado)
        else:
            print(f"[ADMIN] ❌ Erro ao designar: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[ERRO] Erro ao designar piloto: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/candidatos-piloto-etapa/cancelar', methods=['POST'])
@requer_login_api
def cancelar_candidatura_piloto():
    """Piloto cancela sua candidatura para uma equipe em uma etapa"""
    try:
        dados = request.json
        candidato_id = dados.get('candidato_id')
        
        if not candidato_id:
            return jsonify({'sucesso': False, 'erro': 'candidato_id é obrigatório'}), 400
        
        # Obter piloto_id da sessão
        piloto_id = session.get('piloto_id')
        if not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'Usuário não autenticado'}), 401
        
        resultado = api.db.cancelar_candidatura_piloto_etapa(candidato_id, piloto_id)
        
        if resultado['sucesso']:
            print(f"[PILOTO] ✅ Candidatura cancelada")
            return jsonify(resultado)
        else:
            print(f"[PILOTO] ❌ Erro ao cancelar: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[ERRO] Erro ao cancelar candidatura: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/<etapa_id>/pilotos-confirmacao', methods=['GET'])
@requer_login_api
def obter_pilotos_confirmacao(etapa_id):
    """Retorna pilotos que precisam confirmar participação (1h antes da etapa)"""
    try:
        resultado = api.db.obter_pilotos_para_confirmacao(etapa_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[API] Erro ao obter pilotos para confirmação: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/participacoes-etapas/<participacao_id>/confirmar', methods=['POST'])
@requer_login_api
def confirmar_participacao(participacao_id):
    """Piloto confirma sua participação na etapa (pode ser candidato ou alocado)"""
    try:
        piloto_id = session.get('piloto_id')
        if not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'Usuário não autenticado'}), 401
        
        # Tentar confirmar como alocado em participacoes_etapas
        resultado = api.db.confirmar_participacao_piloto(participacao_id, piloto_id)
        
        if resultado['sucesso']:
            print(f"[PILOTO] ✅ Participação confirmada")
            return jsonify(resultado)
        
        # Se não achou em participacoes_etapas, tentar confirmar como candidato
        # (o participacao_id é na verdade candidato_id)
        resultado = api.db.confirmar_candidatura_piloto_etapa(participacao_id, piloto_id)
        
        if resultado['sucesso']:
            print(f"[PILOTO] ✅ Candidatura confirmada")
            return jsonify(resultado)
        else:
            print(f"[PILOTO] ❌ Erro ao confirmar: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[API] Erro ao confirmar participação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/participacoes-etapas/<participacao_id>/desistir', methods=['POST'])
@requer_login_api
def desistir_participacao(participacao_id):
    """Piloto desiste da participação"""
    try:
        piloto_id = session.get('piloto_id')
        if not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'Usuário não autenticado'}), 401
        
        resultado = api.db.desistir_participacao_piloto(participacao_id, piloto_id)
        
        if resultado['sucesso']:
            print(f"[PILOTO] ✅ Desistência registrada")
            return jsonify(resultado)
        else:
            print(f"[PILOTO] ❌ Erro ao desistir: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[API] Erro ao desistir: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/etapas/<etapa_id>/pilotos-sem-equipe', methods=['GET'])
@requer_admin
def listar_pilotos_sem_equipe(etapa_id):
    """Admin - Retorna pilotos em espera que não foram alocados"""
    try:
        resultado = api.db.obter_pilotos_sem_equipe(etapa_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[API] Erro ao listar pilotos sem equipe: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/etapas/<etapa_id>/equipes/<equipe_id>/alocar-proximo-piloto', methods=['POST'])
@requer_admin
def alocar_proximo_piloto(etapa_id, equipe_id):
    """Admin aloca próximo piloto candidato da fila"""
    try:
        resultado = api.db.alocar_proximo_piloto_candidato(etapa_id, equipe_id)
        
        if resultado['sucesso']:
            print(f"[ADMIN] ✅ Piloto alocado")
            return jsonify(resultado)
        else:
            print(f"[ADMIN] ❌ Erro ao alocar: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[API] Erro ao alocar piloto: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/etapas/<etapa_id>/equipes/<equipe_id>/alocar-piloto-reserva', methods=['POST'])
@requer_admin
def alocar_piloto_reserva(etapa_id, equipe_id):
    """Admin aloca piloto da fila de reserva para equipe"""
    try:
        dados = request.json
        piloto_id = dados.get('piloto_id')
        
        if not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'piloto_id é obrigatório'}), 400
        
        resultado = api.db.alocar_piloto_reserva_para_equipe(etapa_id, equipe_id, piloto_id)
        
        if resultado['sucesso']:
            print(f"[ADMIN] ✅ Piloto reserva alocado")
            return jsonify(resultado)
        else:
            print(f"[ADMIN] ❌ Erro ao alocar reserva: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[API] Erro ao alocar piloto reserva: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/<etapa_id>/equipes-precisando-piloto')
def get_equipes_precisando_piloto(etapa_id):
    """Retorna equipes que precisam de piloto em uma etapa"""
    try:
        equipes = api.db.obter_equipes_precisando_piloto(etapa_id)
        return jsonify({'equipes': equipes})
    except Exception as e:
        print(f"[ERRO] Erro ao obter equipes: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/etapa-em-andamento', methods=['GET'])
def obter_etapa_em_andamento():
    """Retorna a etapa atual em andamento (independente de quando for)"""
    try:
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar etapa em andamento
        cursor.execute('''
            SELECT 
                e.id,
                e.numero,
                e.nome,
                e.descricao,
                e.data_etapa,
                e.hora_etapa,
                e.status,
                c.id as campeonato_id,
                c.nome as campeonato_nome,
                c.serie,
                c.numero_etapas
            FROM etapas e
            INNER JOIN campeonatos c ON e.campeonato_id = c.id
            WHERE e.status = 'em_andamento'
            ORDER BY e.data_etapa DESC
            LIMIT 1
        ''')
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            # Converter timedelta para string HH:MM:SS
            if resultado['hora_etapa']:
                resultado['hora_etapa'] = str(resultado['hora_etapa'])
            if resultado['data_etapa']:
                resultado['data_etapa'] = resultado['data_etapa'].isoformat()
            
            return jsonify({
                'sucesso': True,
                'etapa': resultado
            })
        else:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhuma etapa em andamento'
            }), 404
    except Exception as e:
        print(f'Erro ao buscar etapa em andamento: {e}')
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/etapa-hoje', methods=['GET'])
def obter_etapa_hoje():
    """Retorna o campeonato e etapa agendada para hoje"""
    try:
        from datetime import datetime
        hoje = datetime.now().date()
        
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar etapa de hoje
        cursor.execute('''
            SELECT 
                e.id,
                e.numero,
                e.nome,
                e.descricao,
                e.data_etapa,
                e.hora_etapa,
                e.status,
                c.id as campeonato_id,
                c.nome as campeonato_nome,
                c.serie,
                c.numero_etapas
            FROM etapas e
            INNER JOIN campeonatos c ON e.campeonato_id = c.id
            WHERE DATE(e.data_etapa) = %s
            ORDER BY e.hora_etapa
            LIMIT 1
        ''', (hoje,))
        
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if resultado:
            # Converter timedelta para string HH:MM:SS
            if resultado['hora_etapa']:
                resultado['hora_etapa'] = str(resultado['hora_etapa'])
            if resultado['data_etapa']:
                resultado['data_etapa'] = resultado['data_etapa'].isoformat()
            
            return jsonify({
                'sucesso': True,
                'etapa': resultado
            })
        else:
            # Retorna 200 para não gerar 404 no console do front (sistema_notificacao.js)
            return jsonify({
                'sucesso': False,
                'etapa': None,
                'mensagem': 'Nenhuma etapa agendada para hoje'
            })
    except Exception as e:
        print(f"[ERRO] Erro ao obter etapa de hoje: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/user/is-admin', methods=['GET'])
def is_admin():
    """Verifica se o usuário atual é admin"""
    return jsonify({
        'is_admin': session.get('admin', False)
    })

@app.route('/api/admin/fazer-etapa', methods=['POST'])
def fazer_etapa():
    """Inicia qualificacao da etapa e muda status para em_andamento"""
    dados = request.json
    try:
        etapa_id = dados.get('etapa')
        if not etapa_id:
            return jsonify({'sucesso': False, 'erro': 'etapa_id obrigatorio'}), 400
        
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT id, campeonato_id, numero, nome FROM etapas WHERE id = %s', (etapa_id,))
        etapa = cursor.fetchone()
        if not etapa:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Etapa nao encontrada'}), 404
        
        # Mudar status para em_andamento
        cursor.execute('UPDATE etapas SET status = %s WHERE id = %s', ('em_andamento', etapa_id))
        
        # Inicializar voltas: criar registro agendada para cada piloto
        cursor.execute('''
            SELECT pe.piloto_id, pe.equipe_id, pe.ordem_qualificacao
            FROM participacoes_etapas pe
            WHERE pe.etapa_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
            ORDER BY 
                CASE WHEN pe.ordem_qualificacao IS NULL THEN 1 ELSE 0 END,
                pe.ordem_qualificacao ASC
        ''', (etapa_id,))
        
        participacoes = cursor.fetchall()
        
        print(f"[FAZER ETAPA] Participações em ordem: {[(p['ordem_qualificacao'], p['equipe_id'][:8]) for p in participacoes]}")
        
        # Limpar voltas anteriores (se houver)
        cursor.execute('DELETE FROM volta WHERE id_etapa COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci', (etapa_id,))
        
        # Criar volta para cada piloto com status andando/proximo/aguardando
        total_pilotos = len(participacoes)
        for idx, part in enumerate(participacoes):
            piloto_id = part['piloto_id']
            equipe_id = part['equipe_id']
            ordem = part.get('ordem_qualificacao')
            
            # Status: 1º=andando, 2º=proximo, demais=aguardando
            if ordem == 1:
                status = 'andando'  # Ordem 1 está andando
            elif ordem == 2:
                status = 'proximo'  # Ordem 2 é próximo
            else:
                status = 'aguardando'  # Demais estão aguardando
            
            print(f"[VOLTA CRIADA] idx={idx}, ordem={ordem}, status={status}, equipe={equipe_id[:8]}")
            
            cursor.execute('''
                INSERT INTO volta (id_piloto, id_equipe, id_etapa, nota_linha, nota_angulo, nota_estilo, status)
                VALUES (%s, %s, %s, 0, 0, 0, %s)
            ''', (piloto_id, equipe_id, etapa_id, status))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Aplicar ordenação de qualificação (por pontos do campeonato anterior ou aleatória)
        resultado_ordena = api.db.aplicar_ordenacao_qualificacao(etapa_id)
        
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Qualificacao aberta!',
            'status': 'em_andamento',
            'etapa_id': etapa_id,
            'ordenacao': resultado_ordena
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/etapas/<etapa_id>/equipes-pilotos')
@requer_admin
def obter_equipes_pilotos_etapa(etapa_id):
    """Retorna todas as equipes e pilotos alocados em uma etapa (ordenadas por qualificacao)"""
    try:
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar equipes e pilotos da etapa, ordenadas pela ordem de qualificacao
        exclude_assigned = request.args.get('exclude_assigned')
        base_query = '''
            SELECT 
                pe.id as participacao_id,
                pe.equipe_id,
                pe.ordem_qualificacao,
                e.nome as equipe_nome,
                pe.piloto_id,
                p.nome as piloto_nome,
                pe.carro_id,
                c.modelo as carro_modelo,
                pe.tipo_participacao,
                pe.status
            FROM participacoes_etapas pe
            INNER JOIN equipes e ON pe.equipe_id = e.id
            LEFT JOIN pilotos p ON pe.piloto_id = p.id
            LEFT JOIN carros c ON pe.carro_id = c.id
            WHERE pe.etapa_id = %s
        '''

        params = [etapa_id]
        if exclude_assigned and str(exclude_assigned).lower() in ('1', 'true', 'yes'):
            base_query += ' AND pe.piloto_id IS NULL'

        base_query += '''
            ORDER BY 
                CASE WHEN pe.ordem_qualificacao IS NULL THEN 1 ELSE 0 END,
                pe.ordem_qualificacao ASC,
                e.nome ASC
        '''

        cursor.execute(base_query, params)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Agrupar por equipe (mantendo a ordem)
        equipes_dict = {}
        for row in rows:
            equipe_id = row['equipe_id']
            if equipe_id not in equipes_dict:
                equipes_dict[equipe_id] = {
                    'participacao_id': row.get('participacao_id'),
                    'equipe_id': equipe_id,
                    'equipe_nome': row['equipe_nome'],
                    'piloto_id': row.get('piloto_id'),
                    'piloto_nome': row.get('piloto_nome'),
                    'carro_modelo': row.get('carro_modelo'),
                    'tipo_participacao': row.get('tipo_participacao'),
                    'status': row.get('status'),
                    'ordem_qualificacao': row.get('ordem_qualificacao')
                }
        
        equipes = list(equipes_dict.values())
        print(f"[API] Total de equipes na etapa {etapa_id}: {len(equipes)}")
        for i, eq in enumerate(equipes):
            print(f"  {i+1}. {eq['equipe_nome']} (ordem: {eq.get('ordem_qualificacao', 'N/A')})")
        
        return jsonify({'sucesso': True, 'equipes': equipes})
    except Exception as e:
        print(f"[API] Erro ao obter equipes/pilotos da etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/finalizar-qualificacao/<etapa_id>', methods=['POST'])
def finalizar_qualificacao(etapa_id):
    """Finaliza a fase de qualificação: atualiza ordem_qualificacao pelas notas e muda status para batalhas."""
    try:
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT id FROM etapas WHERE id = %s', (etapa_id,))
        etapa = cursor.fetchone()
        if not etapa:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Etapa nao encontrada'}), 404
        
        # Atualizar ordem_qualificacao em participacoes_etapas com base nas notas da volta
        cursor.execute('''
            SELECT pe.id as participacao_id, pe.equipe_id,
                   COALESCE(v.nota_linha, 0) + COALESCE(v.nota_angulo, 0) + COALESCE(v.nota_estilo, 0) as total_notas
            FROM participacoes_etapas pe
            LEFT JOIN volta v ON v.id_equipe COLLATE utf8mb4_unicode_ci = pe.equipe_id COLLATE utf8mb4_unicode_ci
                AND v.id_etapa COLLATE utf8mb4_unicode_ci = pe.etapa_id COLLATE utf8mb4_unicode_ci
            WHERE pe.etapa_id = %s
        ''', (etapa_id,))
        rows = cursor.fetchall()
        # Ordenar por total_notas DESC (maior nota = melhor posição)
        rows_sorted = sorted(rows, key=lambda r: (-(r['total_notas'] or 0), r['equipe_id']))
        for pos, row in enumerate(rows_sorted, 1):
            cursor.execute(
                'UPDATE participacoes_etapas SET ordem_qualificacao = %s WHERE id = %s',
                (pos, row['participacao_id'])
            )
        
        # Marcar qualificação como finalizada e mudar status para batalhas
        cursor.execute('UPDATE etapas SET qualificacao_finalizada = TRUE, status = %s WHERE id = %s', ('batalhas', etapa_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'sucesso': True, 'mensagem': 'Qualificacao finalizada! Status mudado para batalhas.'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/etapas/<etapa_id>/classificacao-final', methods=['GET'])
def obter_classificacao_final(etapa_id):
    """Obtém a classificação final da qualificação ordenada por notas"""
    try:
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # Buscar todas as equipes da etapa com suas notas
        cursor.execute('''
            SELECT 
                v.id_equipe,
                e.nome as equipe_nome,
                p.nome as piloto_nome,
                v.nota_linha,
                v.nota_angulo,
                v.nota_estilo,
                (v.nota_linha + v.nota_angulo + v.nota_estilo) as total_notas,
                pe.ordem_qualificacao
            FROM volta v
            JOIN equipes e ON v.id_equipe COLLATE utf8mb4_unicode_ci = e.id COLLATE utf8mb4_unicode_ci
            LEFT JOIN pilotos p ON v.id_piloto COLLATE utf8mb4_unicode_ci = p.id COLLATE utf8mb4_unicode_ci
            JOIN participacoes_etapas pe ON v.id_equipe COLLATE utf8mb4_unicode_ci = pe.equipe_id COLLATE utf8mb4_unicode_ci 
                AND v.id_etapa COLLATE utf8mb4_unicode_ci = pe.etapa_id COLLATE utf8mb4_unicode_ci
            WHERE v.id_etapa COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
            ORDER BY total_notas DESC, v.nota_linha DESC, v.nota_angulo DESC, v.nota_estilo DESC
        ''', (etapa_id,))
        
        classificacao = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Formatar resposta
        resultado = []
        for i, equipe in enumerate(classificacao, 1):
            resultado.append({
                'posicao': i,
                'equipe_id': equipe['id_equipe'],
                'equipe_nome': equipe['equipe_nome'],
                'piloto_nome': equipe['piloto_nome'] or 'SEM PILOTO',
                'nota_linha': equipe['nota_linha'] or 0,
                'nota_angulo': equipe['nota_angulo'] or 0,
                'nota_estilo': equipe['nota_estilo'] or 0,
                'total_notas': equipe['total_notas'] or 0,
                'ordem_qualificacao': equipe['ordem_qualificacao']
            })
        
        return jsonify({
            'sucesso': True,
            'classificacao': resultado,
            'total_equipes': len(resultado)
        })
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400


def _gerar_chaveamento_single_elimination(participantes):
    """Gera chaveamento single-elimination no estilo Challonge: 1 vs N, 2 vs N-1, etc."""
    n = len(participantes)
    if n < 2:
        return []
    # Seed order: 1º enfrenta último, 2º enfrenta penúltimo, etc.
    chaveamento = []
    for i in range(n // 2):
        a = participantes[i]
        b = participantes[n - 1 - i]
        chaveamento.append({
            'rodada': 1,
            'match_num': i + 1,
            'equipe_a': a,
            'equipe_b': b,
            'vencedor_id': None,
        })
    return chaveamento


@app.route('/api/etapas/<etapa_id>/chaveamento', methods=['GET'])
def obter_chaveamento_etapa(etapa_id):
    """Retorna o chaveamento (bracket) da etapa baseado na ordem de qualificação."""
    try:
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT pe.equipe_id, e.nome as equipe_nome, p.nome as piloto_nome,
                   pe.ordem_qualificacao,
                   COALESCE(v.nota_linha,0)+COALESCE(v.nota_angulo,0)+COALESCE(v.nota_estilo,0) as total_notas
            FROM participacoes_etapas pe
            JOIN equipes e ON pe.equipe_id = e.id
            LEFT JOIN pilotos p ON pe.piloto_id = p.id
            LEFT JOIN volta v ON v.id_equipe = pe.equipe_id AND v.id_etapa = pe.etapa_id
            WHERE pe.etapa_id = %s
            ORDER BY (pe.ordem_qualificacao IS NULL), pe.ordem_qualificacao ASC
        ''', (etapa_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        # Ordenar por total_notas DESC (melhor nota = seed 1)
        rows_ord = sorted(rows, key=lambda x: (-(x['total_notas'] or 0), x['equipe_id']))
        participantes = [
            {'equipe_id': r['equipe_id'], 'equipe_nome': r['equipe_nome'], 'piloto_nome': r['piloto_nome'] or '-', 'seed': i}
            for i, r in enumerate(rows_ord, 1)
        ]
        chaveamento = _gerar_chaveamento_single_elimination(participantes)
        return jsonify({'sucesso': True, 'participantes': participantes, 'chaveamento': chaveamento})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400


# ============ CHALLONGE API v1 (https://api.challonge.com/v1) ============
# API v1 é estável e funcional. v2.1 + OAuth retorna 520 (Cloudflare).
# Use Basic Auth com API key em challonge.com/settings/developer

CHALLONGE_API_KEY = os.environ.get('CHALLONGE_API_KEY', '')
CHALLONGE_USERNAME = os.environ.get('CHALLONGE_USERNAME', '')
CHALLONGE_API_BASE = 'https://api.challonge.com/v1'


def _challonge_auth():
    """Challonge v1: (username, api_key) ou (api_key, "")."""
    if CHALLONGE_USERNAME and CHALLONGE_API_KEY:
        return (CHALLONGE_USERNAME, CHALLONGE_API_KEY)
    if CHALLONGE_API_KEY:
        return (CHALLONGE_API_KEY, '')
    return None


def _challonge_request(method, endpoint, data=None, params=None):
    """
    Faz requisição à Challonge API v1 com Basic Auth.
    Para POST/PUT, data deve ser dict no formato form: tournament[name]=..., etc.
    """
    import requests
    auth = _challonge_auth()
    if not auth:
        raise ValueError('Configure CHALLONGE_API_KEY no .env')
    url = f"{CHALLONGE_API_BASE}{endpoint}"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
    }
    kw = {
        'method': method,
        'url': url,
        'auth': auth,
        'headers': headers,
        'params': params,
        'timeout': 20,
    }
    if data is not None:
        kw['data'] = data  # form-urlencoded (não json)
    return requests.request(**kw)


@app.route('/api/admin/challonge/status')
@requer_admin
def challonge_status():
    """Retorna se o Challonge está conectado (API key + username v1)."""
    conectado = bool(CHALLONGE_API_KEY) and bool(CHALLONGE_USERNAME)
    return jsonify({
        'conectado': conectado,
        'api_key_ok': bool(CHALLONGE_API_KEY),
        'username_ok': bool(CHALLONGE_USERNAME),
    })


@app.route('/api/etapas/<etapa_id>/enviar-challonge', methods=['POST'])
@requer_admin
def enviar_etapa_challonge(etapa_id):
    """Cria torneio no Challonge v1 a partir do chaveamento da etapa. Basic Auth (username, api_key)."""
    try:
        if not CHALLONGE_API_KEY:
            return jsonify({'sucesso': False, 'erro': 'Configure CHALLONGE_API_KEY no .env (challonge.com/settings/developer)'}), 400
        if not CHALLONGE_USERNAME:
            return jsonify({'sucesso': False, 'erro': 'Configure CHALLONGE_USERNAME no .env (seu usuário Challonge). Reinicie o servidor após editar .env'}), 400
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT e.id, e.nome, e.numero, c.nome as campeonato_nome
            FROM etapas e
            JOIN campeonatos c ON e.campeonato_id = c.id
            WHERE e.id = %s
        ''', (etapa_id,))
        etapa = cursor.fetchone()
        if not etapa:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Etapa não encontrada'}), 404
        cursor.execute('''
            SELECT pe.equipe_id, e.nome as equipe_nome, COALESCE(e.serie, 'A') as serie,
                   pe.ordem_qualificacao,
                   COALESCE(v.nota_linha,0)+COALESCE(v.nota_angulo,0)+COALESCE(v.nota_estilo,0) as total_notas
            FROM participacoes_etapas pe
            JOIN equipes e ON pe.equipe_id = e.id
            LEFT JOIN volta v ON v.id_equipe = pe.equipe_id AND v.id_etapa = pe.etapa_id
            WHERE pe.etapa_id = %s
        ''', (etapa_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        participantes = sorted(rows, key=lambda x: (-(x['total_notas'] or 0), x['equipe_id']))
        if len(participantes) < 2:
            return jsonify({'sucesso': False, 'erro': 'Mínimo 2 participantes para criar torneio'}), 400
        nome_torneio = f"{etapa['campeonato_nome']} - Etapa {etapa['numero']}"
        url_slug = f"granpix_{etapa_id.replace('-', '')[:16]}"

        # v1: form encoding (tournament[name], tournament[url], etc) - NÃO JSON:API
        payload = {
            'tournament[name]': nome_torneio,
            'tournament[url]': url_slug,
            'tournament[tournament_type]': 'single elimination',
            'tournament[game_name]': 'Drift RP',
        }
        r = _challonge_request('POST', '/tournaments.json', data=payload)
        if r.status_code not in (200, 201):
            err_detail = r.text[:400] if r.text else str(r.status_code)
            print(f"[CHALLONGE] Create falhou: {r.status_code} {err_detail}")
            if r.status_code == 401:
                msg = 'Challonge: 401 Access denied. Verifique CHALLONGE_USERNAME e CHALLONGE_API_KEY no .env e reinicie o servidor.'
            elif 500 <= r.status_code < 600:
                msg = f'Challonge temporariamente indisponível (erro {r.status_code}). Tente novamente em alguns minutos.'
            else:
                msg = f'Challonge: {r.status_code} - {err_detail[:150]}'
            return jsonify({'sucesso': False, 'erro': msg}), 400

        tour = r.json()
        # v1 retorna { tournament: { id, url, full_challonge_url, ... } }
        t = tour.get('tournament', tour)
        tour_id = t.get('id')
        tour_url = t.get('full_challonge_url') or f"https://challonge.com/{t.get('url', url_slug)}"

        # Adicionar participantes (v1: participant[name], participant[seed])
        for i, p in enumerate(participantes):
            part_data = {
                'participant[name]': p['equipe_nome'][:255],
                'participant[seed]': i + 1,
            }
            pr = _challonge_request('POST', f'/tournaments/{url_slug}/participants.json', data=part_data)
            if pr.status_code not in (200, 201):
                print(f"[CHALLONGE] Aviso ao adicionar {p['equipe_nome']}: {pr.status_code} {pr.text[:100]}")

        # Iniciar torneio (v1: POST /tournaments/{url}/start.json)
        start_r = _challonge_request('POST', f'/tournaments/{url_slug}/start.json')
        if start_r.status_code not in (200, 201):
            err_msg = start_r.text[:400] if start_r.text else str(start_r.status_code)
            print(f"[CHALLONGE] Start falhou: {start_r.status_code} {start_r.text}")
            api.db.salvar_configuracao(f'challonge_etapa_{etapa_id}', tour_url, 'URL do torneio Challonge')
            return jsonify({
                'sucesso': True,
                'url': tour_url,
                'tournament_id': tour_id,
                'bracket_pendente': True,
                'erro': f'Torneio criado. Inicie manualmente em: {tour_url} (erro: {err_msg})'
            }), 200

        api.db.salvar_configuracao(f'challonge_etapa_{etapa_id}', tour_url, 'URL do torneio Challonge')
        for p in participantes:
            serie = (p.get('serie') or 'A').strip().upper()
            if serie not in ('A', 'B'):
                serie = 'A'
            chave = f'participacao_etapa_{serie}'
            valor = float(api.db.obter_configuracao(chave) or (3000 if serie == 'A' else 2000))
            if valor > 0 and api.db.creditar_doricoins_equipe(p['equipe_id'], valor):
                print(f"[DORICOINS] +{valor} para {p.get('equipe_nome', '')} (participação etapa)")
        return jsonify({'sucesso': True, 'url': tour_url, 'tournament_id': tour_id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


def _extrair_slug_challonge(full_url):
    """Extrai o slug do torneio a partir da URL Challonge (ex: https://challonge.com/xxx -> xxx)."""
    if not full_url or not isinstance(full_url, str):
        return None
    import re
    m = re.search(r'challonge\.com/([a-zA-Z0-9_-]+)', full_url)
    return m.group(1) if m else None


def _buscar_bracket_challonge(slug):
    """
    Busca participantes e matches na API Challonge v1.
    Retorna (participants_map, matches_list) ou (None, None) em caso de erro.
    """
    if not slug or not CHALLONGE_API_KEY:
        return None, None
    try:
        r_part = _challonge_request('GET', f'/tournaments/{slug}/participants.json')
        if r_part.status_code not in (200, 201):
            return None, None
        parts = r_part.json()
        participants = []
        if isinstance(parts, list):
            participants = parts
        elif isinstance(parts, dict) and 'participant' in parts:
            participants = [parts]
        else:
            participants = parts if isinstance(parts, list) else []
        part_map = {}
        for p in participants:
            if not isinstance(p, dict):
                continue
            p_obj = p.get('participant', p)
            pid = p_obj.get('id')
            if pid is not None:
                part_map[str(pid)] = {
                    'id': pid,
                    'name': p_obj.get('name') or p_obj.get('display_name') or 'TBD',
                    'seed': p_obj.get('seed'),
                    'final_rank': p_obj.get('final_rank'),
                }
        r_mat = _challonge_request('GET', f'/tournaments/{slug}/matches.json')
        if r_mat.status_code not in (200, 201):
            return part_map, []
        mat_data = r_mat.json()
        matches = []
        if isinstance(mat_data, list):
            matches = mat_data
        elif isinstance(mat_data, dict) and 'match' in mat_data:
            matches = [mat_data]
        else:
            matches = mat_data if isinstance(mat_data, list) else []
        return part_map, matches
    except Exception as e:
        print(f"[CHALLONGE] Erro ao buscar bracket: {e}")
        return None, None


@app.route('/api/etapas/<etapa_id>/bracket-challonge', methods=['GET'])
def obter_bracket_challonge(etapa_id):
    """Retorna o bracket buscando participantes e matches diretamente da API Challonge. Fonte de verdade = Challonge."""
    try:
        challonge_url = api.db.obter_configuracao(f'challonge_etapa_{etapa_id}') or None
        slug = _extrair_slug_challonge(challonge_url)
        bracket = []
        if slug and CHALLONGE_API_KEY and CHALLONGE_USERNAME:
            part_map, matches_raw = _buscar_bracket_challonge(slug)
            if part_map is not None:
                matches_list = []
                for m in matches_raw:
                    m_obj = m.get('match', m) if isinstance(m, dict) else {}
                    p1_id = m_obj.get('player1_id')
                    p2_id = m_obj.get('player2_id')
                    winner_id = m_obj.get('winner_id')
                    round_num = m_obj.get('round', 1)
                    scores = m_obj.get('scores_csv') or ''
                    parts_scores = scores.split('-') if scores else [None, None]
                    match_id = m_obj.get('id')
                    p1 = part_map.get(str(p1_id), {}) if p1_id else {}
                    p2 = part_map.get(str(p2_id), {}) if p2_id else {}
                    matches_list.append({
                        'round': round_num,
                        'match_id': match_id,
                        'player1_id': p1_id,
                        'player2_id': p2_id,
                        'winner_id': winner_id,
                        'player1': {
                            'id': p1_id,
                            'name': p1.get('name', 'TBD'),
                            'seed': p1.get('seed'),
                            'score': int(parts_scores[0]) if parts_scores and parts_scores[0] and str(parts_scores[0]).isdigit() else None,
                        },
                        'player2': {
                            'id': p2_id,
                            'name': p2.get('name', 'TBD'),
                            'seed': p2.get('seed'),
                            'score': int(parts_scores[1]) if len(parts_scores) > 1 and parts_scores[1] and str(parts_scores[1]).isdigit() else None,
                        },
                    })
                by_round = {}
                for m in matches_list:
                    rn = m.get('round', 1)
                    by_round.setdefault(rn, []).append(m)
                round_labels = {1: 'Fase 01', 2: 'Fase 02', 3: 'Quartas', 4: 'Semi', 5: 'Final'}
                for rn in sorted(by_round.keys()):
                    label = round_labels.get(rn, f'Rodada {rn}')
                    bracket.append({
                        'label': label,
                        'matches': by_round[rn],
                    })
        # Se tem URL mas bracket vazio (ex: torneio ainda não iniciado), frontend mostra o link
        return jsonify({
            'sucesso': True,
            'bracket': bracket,
            'challonge_url': challonge_url,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/etapas/<etapa_id>/challonge-match-report', methods=['POST'])
@requer_admin
def challonge_match_report(etapa_id):
    """Reporta vencedor de uma partida no Challonge. Atualiza o match e retorna sucesso."""
    try:
        if not CHALLONGE_API_KEY or not CHALLONGE_USERNAME:
            return jsonify({'sucesso': False, 'erro': 'Challonge não configurado'}), 400
        data = request.json or {}
        match_id = data.get('match_id')
        winner_id = data.get('winner_id')
        scores_csv = data.get('scores_csv', '1-0')
        if not match_id or not winner_id:
            return jsonify({'sucesso': False, 'erro': 'match_id e winner_id obrigatórios'}), 400
        challonge_url = api.db.obter_configuracao(f'challonge_etapa_{etapa_id}') or None
        slug = _extrair_slug_challonge(challonge_url)
        if not slug:
            return jsonify({'sucesso': False, 'erro': 'Torneio Challonge não encontrado para esta etapa'}), 404
        payload = {
            'match[winner_id]': winner_id,
            'match[scores_csv]': str(scores_csv) if scores_csv else '1-0',
        }
        r = _challonge_request('PUT', f'/tournaments/{slug}/matches/{match_id}.json', data=payload)
        if r.status_code not in (200, 201):
            err = r.text[:200] if r.text else str(r.status_code)
            return jsonify({'sucesso': False, 'erro': f'Challonge: {r.status_code} - {err}'}), 400
        part_map, matches_raw = _buscar_bracket_challonge(slug)
        round_num = data.get('round')
        if round_num is not None and int(round_num) >= 2 and part_map and winner_id:
            winner_name = (part_map.get(str(winner_id)) or {}).get('name', '')
            if winner_name:
                winner_equipe_id = api.db.obter_equipe_id_por_nome_na_etapa(etapa_id, winner_name)
                if winner_equipe_id:
                    serie = api.db.obter_serie_equipe(winner_equipe_id)
                    chave = f'vitoria_batalha_{serie}' if serie in ('A', 'B') else 'vitoria_batalha_A'
                    valor = float(api.db.obter_configuracao(chave) or 1500)
                    if valor > 0 and api.db.creditar_doricoins_equipe(winner_equipe_id, valor):
                        print(f"[DORICOINS] +{valor} para {winner_name} (vitória fase {round_num})")
        # Se vencedor venceu com carro quebrado (alguma peça em 0), marca By run para próxima batalha
        if part_map and winner_id:
            winner_name = (part_map.get(str(winner_id)) or {}).get('name', '')
            if winner_name:
                winner_equipe_id = api.db.obter_equipe_id_por_nome_na_etapa(etapa_id, winner_name)
                if winner_equipe_id and api.db.carro_equipe_quebrado_etapa(etapa_id, winner_equipe_id):
                    api.db.adicionar_equipe_by_run(etapa_id, winner_equipe_id)
                    print(f"[BY-RUN] {winner_name} venceu com carro quebrado → próxima batalha adversário faz By run")
        # Se era partida By run (adversário não podia andar), remove da lista após reportar
        by_run_ids = api.db.obter_equipes_by_run(etapa_id)
        if by_run_ids and part_map and matches_raw:
            for m in matches_raw:
                mo = m.get('match', m) if isinstance(m, dict) else m
                if str(mo.get('id')) == str(match_id):
                    p1_id, p2_id = mo.get('player1_id'), mo.get('player2_id')
                    loser_id = p2_id if str(winner_id) == str(p1_id) else p1_id
                    if loser_id:
                        loser_name = (part_map.get(str(loser_id)) or {}).get('name', '')
                        if loser_name:
                            loser_equipe_id = api.db.obter_equipe_id_por_nome_na_etapa(etapa_id, loser_name)
                            if loser_equipe_id and loser_equipe_id in by_run_ids:
                                api.db.remover_equipe_by_run(etapa_id, loser_equipe_id)
                                print(f"[BY-RUN] Partida By run concluída → removido {loser_name} da lista")
                    break
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/etapas/<etapa_id>/challonge-match-reopen', methods=['POST'])
@requer_admin
def challonge_match_reopen(etapa_id):
    """Reabre uma partida no Challonge (desfaz resultado). Reseta partidas dependentes."""
    try:
        if not CHALLONGE_API_KEY or not CHALLONGE_USERNAME:
            return jsonify({'sucesso': False, 'erro': 'Challonge não configurado'}), 400
        data = request.json or {}
        match_id = data.get('match_id')
        if not match_id:
            return jsonify({'sucesso': False, 'erro': 'match_id obrigatório'}), 400
        challonge_url = api.db.obter_configuracao(f'challonge_etapa_{etapa_id}') or None
        slug = _extrair_slug_challonge(challonge_url)
        if not slug:
            return jsonify({'sucesso': False, 'erro': 'Torneio Challonge não encontrado para esta etapa'}), 404
        r = _challonge_request('POST', f'/tournaments/{slug}/matches/{match_id}/reopen.json')
        if r.status_code not in (200, 201):
            err = r.text[:200] if r.text else str(r.status_code)
            return jsonify({'sucesso': False, 'erro': f'Challonge: {r.status_code} - {err}'}), 400
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/etapas/<etapa_id>/equipes-by-run', methods=['GET'])
@requer_admin
def obter_equipes_by_run(etapa_id):
    """Retorna lista de equipe_ids que venceram com carro quebrado (próxima batalha = By run para adversário)."""
    try:
        ids = api.db.obter_equipes_by_run(etapa_id)
        return jsonify({'sucesso': True, 'equipe_ids': ids})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


def _requer_login_ou_admin():
    """Permite admin, equipe ou piloto logado."""
    if session.get('admin'):
        return True
    if 'equipe_id' in session or 'piloto_id' in session or request.headers.get('X-Equipe-ID'):
        return True
    return False

@app.route('/api/etapas/<etapa_id>/batalhas-recentes', methods=['GET'])
def batalhas_recentes(etapa_id):
    """Retorna passadas recentes da etapa para exibir cards de vida/dano para pilotos e equipes."""
    if not _requer_login_ou_admin():
        return jsonify({'erro': 'Não autenticado'}), 401
    try:
        limit = min(int(request.args.get('limit', 20)), 50)
        passadas = api.db.listar_passadas_batalha(etapa_id, limit)
        return jsonify({'sucesso': True, 'passadas': passadas})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e), 'passadas': []}), 500


@app.route('/api/etapas/<etapa_id>/pecas-batalha', methods=['GET'])
@requer_admin
def obter_pecas_batalha(etapa_id):
    """Retorna durabilidade das peças dos 2 carros da partida (equipe1_id, equipe2_id)."""
    try:
        eq1_id = request.args.get('equipe1_id', '').strip()
        eq2_id = request.args.get('equipe2_id', '').strip()
        if not eq1_id and not eq2_id:
            return jsonify({'sucesso': False, 'erro': 'equipe1_id e equipe2_id obrigatórios'}), 400
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        carros = []
        for equipe_id in (eq1_id, eq2_id):
            if not equipe_id:
                carros.append({'equipe_id': '', 'equipe_nome': '', 'pecas': []})
                continue
            cursor.execute(
                'SELECT carro_id FROM participacoes_etapas WHERE etapa_id = %s AND equipe_id = %s LIMIT 1',
                (etapa_id, equipe_id)
            )
            row = cursor.fetchone()
            cursor.execute('SELECT nome FROM equipes WHERE id = %s', (equipe_id,))
            eq_row = cursor.fetchone()
            eq_nome = (eq_row or {}).get('nome', '')
            if not row or not row.get('carro_id'):
                carros.append({'equipe_id': equipe_id, 'equipe_nome': eq_nome, 'pecas': []})
                continue
            carro_id = row['carro_id']
            cursor.execute('''
                SELECT tipo, nome, durabilidade_maxima, durabilidade_atual
                FROM pecas WHERE carro_id = %s AND instalado = 1
            ''', (carro_id,))
            pecas_rows = cursor.fetchall()
            pecas = []
            for p in pecas_rows:
                v_max = p.get('durabilidade_maxima')
                v_atual = p.get('durabilidade_atual')
                dur_max = float(v_max) if v_max is not None and v_max != '' else 100.0
                dur_atual = float(v_atual) if v_atual is not None and v_atual != '' else 100.0
                pct = int((dur_atual / dur_max * 100) if dur_max > 0 else 0)
                pecas.append({
                    'tipo': p.get('tipo', ''),
                    'nome': p.get('nome', ''),
                    'durabilidade_atual': round(dur_atual, 1),
                    'durabilidade_maxima': dur_max,
                    'percentual': pct
                })
            carros.append({'equipe_id': equipe_id, 'equipe_nome': eq_nome, 'pecas': pecas})
        cursor.close()
        conn.close()
        return jsonify({'sucesso': True, 'carros': carros})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/etapas/<etapa_id>/executar-passada', methods=['POST'])
@requer_admin
def executar_passada(etapa_id):
    """Executa uma passada: rola dados de dano para as peças dos carros. Se by_run=True, apenas equipe_que_corre_id."""
    try:
        data = request.json or {}
        eq1_id = (data.get('equipe1_id') or '').strip()
        eq2_id = (data.get('equipe2_id') or '').strip()
        eq1_nome = (data.get('equipe1_nome') or '').strip()
        eq2_nome = (data.get('equipe2_nome') or '').strip()
        by_run = data.get('by_run') is True
        equipe_que_corre_id = (data.get('equipe_que_corre_id') or '').strip()
        if not eq1_id and not eq2_id and not eq1_nome and not eq2_nome and not equipe_que_corre_id:
            return jsonify({'sucesso': False, 'erro': 'Informe os IDs ou nomes das equipes'}), 400
        dado_faces = int(api.db.obter_configuracao('dado_dano') or '20')
        if dado_faces < 2:
            dado_faces = 6
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        carro_ids = []
        if by_run and equipe_que_corre_id:
            cursor.execute(
                'SELECT carro_id FROM participacoes_etapas WHERE etapa_id = %s AND equipe_id = %s LIMIT 1',
                (etapa_id, equipe_que_corre_id)
            )
            row = cursor.fetchone()
            if row and row.get('carro_id'):
                carro_ids.append(row['carro_id'])
        else:
            for equipe_id, nome in [(eq1_id, eq1_nome), (eq2_id, eq2_nome)]:
                if equipe_id:
                    cursor.execute(
                        'SELECT carro_id FROM participacoes_etapas WHERE etapa_id = %s AND equipe_id = %s LIMIT 1',
                        (etapa_id, equipe_id)
                    )
                elif nome:
                    cursor.execute('''
                        SELECT pe.carro_id FROM participacoes_etapas pe
                        JOIN equipes e ON pe.equipe_id = e.id
                        WHERE pe.etapa_id = %s AND (e.nome = %s OR e.nome LIKE %s)
                        LIMIT 1
                    ''', (etapa_id, nome, f'%{nome}%'))
                else:
                    continue
                row = cursor.fetchone()
                if row and row.get('carro_id'):
                    carro_ids.append(row['carro_id'])
        cursor.close()
        conn.close()
        if not carro_ids:
            return jsonify({'sucesso': False, 'erro': 'Nenhum carro encontrado para as equipes informadas'}), 404
        resultado = api.db.aplicar_desgaste_passada(carro_ids, dado_faces)
        if not resultado.get('sucesso'):
            return jsonify({'sucesso': False, 'erro': resultado.get('erro', 'Erro ao aplicar desgaste')}), 500
        resumo = resultado.get('resumo', [])
        lancamentos = resultado.get('lancamentos', [])
        total_danos = sum(r.get('dano', 0) for r in resumo)
        
        # Registrar passada para cards de batalha (vida/dano) para pilotos e equipes
        eq1_nome_f = eq1_nome or ''
        eq2_nome_f = eq2_nome or ''
        if not eq1_nome_f or not eq2_nome_f:
            conn_n = api.db._get_conn()
            cursor_n = conn_n.cursor(dictionary=True)
            if eq1_id:
                cursor_n.execute('SELECT nome FROM equipes WHERE id = %s', (eq1_id,))
                r1 = cursor_n.fetchone()
                eq1_nome_f = (r1 or {}).get('nome', '') or eq1_nome_f
            if eq2_id:
                cursor_n.execute('SELECT nome FROM equipes WHERE id = %s', (eq2_id,))
                r2 = cursor_n.fetchone()
                eq2_nome_f = (r2 or {}).get('nome', '') or eq2_nome_f
            cursor_n.close()
            conn_n.close()
        carros_vida = api.db.obter_pecas_batalha_interno(etapa_id, eq1_id or '', eq2_id or '')
        vida_p1 = ''
        vida_p2 = ''
        dano_p1 = 0.0
        dano_p2 = 0.0
        if carros_vida and len(carros_vida) >= 2:
            def fmt_vida(c):
                if not c.get('pecas'):
                    return 'N/A'
                return ' | '.join(f"{p.get('tipo','?')}:{p.get('percentual',0)}%" for p in c['pecas'])
            vida_p1 = fmt_vida(carros_vida[0])
            vida_p2 = fmt_vida(carros_vida[1])
        for lm in lancamentos:
            cid = lm.get('carro_id')
            d = lm.get('dano', 0)
            if cid and carro_ids:
                if len(carro_ids) >= 2 and cid == carro_ids[0]:
                    dano_p1 += d
                elif len(carro_ids) >= 2 and cid == carro_ids[1]:
                    dano_p2 += d
                elif len(carro_ids) == 1:
                    dano_p1 += d
        api.db.registrar_passada_batalha(etapa_id, eq1_id or '', eq2_id or '', eq1_nome_f, eq2_nome_f, vida_p1, vida_p2, dano_p1, dano_p2)
        
        return jsonify({
            'sucesso': True,
            'resumo': f'Dano aplicado em {len(resumo)} peça(s), total {total_danos:.1f}',
            'detalhes': resumo,
            'lancamentos': lancamentos,
            'dado_faces': dado_faces
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


def _processar_colocacoes_challonge_e_premiar(etapa_id: str):
    """Após finalize: atribui pontos por colocação e verifica premiação final do campeonato."""
    try:
        challonge_url = api.db.obter_configuracao(f'challonge_etapa_{etapa_id}') or None
        slug = _extrair_slug_challonge(challonge_url)
        if not slug:
            return
        part_map, _ = _buscar_bracket_challonge(slug)
        if not part_map:
            return
        colocacoes = []
        for pid, p in part_map.items():
            rank = p.get('final_rank')
            if rank is not None:
                colocacoes.append((int(rank), p.get('name', '')))
        if not colocacoes:
            return
        colocacoes.sort(key=lambda x: x[0])
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT campeonato_id FROM etapas WHERE id = %s', (etapa_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return
        campeonato_id = row['campeonato_id']
        for colocacao, equipe_nome in colocacoes:
            equipe_id = api.db.obter_equipe_id_por_nome_na_etapa(etapa_id, equipe_nome)
            if equipe_id:
                pontos = api.db.obter_pontos_por_colocacao(colocacao)
                api.db.atualizar_pontuacao_equipe(campeonato_id, equipe_id, pontos)
        api.db.atualizar_colocacoes_campeonato(campeonato_id)
        cursor = api.db._get_conn().cursor(dictionary=True)
        cursor.execute('SELECT numero_etapas FROM campeonatos WHERE id = %s', (campeonato_id,))
        camp = cursor.fetchone()
        cursor.execute('SELECT COUNT(*) as n FROM etapas WHERE campeonato_id = %s AND status IN ("concluida", "encerrada")', (campeonato_id,))
        cnt = cursor.fetchone()
        cursor.close()
        api.db._get_conn().close()
        total_etapas = (camp or {}).get('numero_etapas') or 999
        concluidas = (cnt or {}).get('n') or 0
        if concluidas >= total_etapas:
            for pos in range(1, 6):
                premio = float(api.db.obter_configuracao(f'premio_campeonato_{pos}') or 0)
                if premio <= 0:
                    continue
                conn = api.db._get_conn()
                cur = conn.cursor(dictionary=True)
                cur.execute('SELECT equipe_id FROM pontuacoes_campeonato WHERE campeonato_id = %s AND colocacao = %s LIMIT 1', (campeonato_id, pos))
                r = cur.fetchone()
                cur.close()
                conn.close()
                if r and api.db.creditar_doricoins_equipe(r['equipe_id'], premio):
                    print(f"[PREMIAÇÃO] {pos}º lugar: +{premio} doricoins")
    except Exception as e:
        print(f"[CHALLONGE] Erro ao processar colocações/premiação: {e}")


@app.route('/api/etapas/<etapa_id>/challonge-finalize', methods=['POST'])
@requer_admin
def challonge_finalize(etapa_id):
    """Encerra/finaliza o torneio no Challonge. Atribui pontos e verifica premiação."""
    try:
        if not CHALLONGE_API_KEY or not CHALLONGE_USERNAME:
            return jsonify({'sucesso': False, 'erro': 'Challonge não configurado'}), 400
        challonge_url = api.db.obter_configuracao(f'challonge_etapa_{etapa_id}') or None
        slug = _extrair_slug_challonge(challonge_url)
        if not slug:
            return jsonify({'sucesso': False, 'erro': 'Torneio Challonge não encontrado para esta etapa'}), 404
        r = _challonge_request('POST', f'/tournaments/{slug}/finalize.json')
        if r.status_code not in (200, 201):
            err = r.text[:200] if r.text else str(r.status_code)
            return jsonify({'sucesso': False, 'erro': f'Challonge: {r.status_code} - {err}'}), 400
        api.db.marcar_etapa_concluida(etapa_id)
        _processar_colocacoes_challonge_e_premiar(etapa_id)
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/etapas/<etapa_id>/evento', methods=['GET'])
def obter_evento_etapa(etapa_id):
    """Obtém todos os dados da etapa (funcionado para agendada, em_andamento, etc)"""
    try:
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Buscar informações da etapa
        cursor.execute('''
            SELECT 
                e.id, e.numero, e.nome, e.campeonato_id, e.data_etapa, e.hora_etapa,
                e.serie, e.status, e.descricao, e.qualificacao_finalizada,
                c.nome as campeonato_nome
            FROM etapas e
            JOIN campeonatos c ON e.campeonato_id COLLATE utf8mb4_unicode_ci = c.id COLLATE utf8mb4_unicode_ci
            WHERE e.id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
        ''', (etapa_id,))
        
        etapa_info = cursor.fetchone()
        if not etapa_info:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Etapa não encontrada'}), 404
        
        # 2. Buscar equipes e pilotos da etapa
        cursor.execute('''
            SELECT 
                pe.id as participacao_id,
                pe.equipe_id,
                pe.ordem_qualificacao,
                e.nome as equipe_nome,
                pe.piloto_id,
                p.nome as piloto_nome,
                pe.carro_id,
                c.modelo as carro_modelo,
                pe.tipo_participacao,
                pe.status,
                COALESCE(v.nota_linha, 0) as nota_linha,
                COALESCE(v.nota_angulo, 0) as nota_angulo,
                COALESCE(v.nota_estilo, 0) as nota_estilo,
                COALESCE(v.status, 'aguardando') as volta_status
            FROM participacoes_etapas pe
            INNER JOIN equipes e ON pe.equipe_id COLLATE utf8mb4_unicode_ci = e.id COLLATE utf8mb4_unicode_ci
            LEFT JOIN pilotos p ON pe.piloto_id COLLATE utf8mb4_unicode_ci = p.id COLLATE utf8mb4_unicode_ci
            LEFT JOIN carros c ON pe.carro_id COLLATE utf8mb4_unicode_ci = c.id COLLATE utf8mb4_unicode_ci
            LEFT JOIN volta v ON v.id_piloto COLLATE utf8mb4_general_ci = pe.piloto_id COLLATE utf8mb4_general_ci 
            AND v.id_equipe COLLATE utf8mb4_general_ci = pe.equipe_id COLLATE utf8mb4_general_ci
            AND v.id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
            WHERE pe.etapa_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
            ORDER BY 
                CASE WHEN pe.ordem_qualificacao IS NULL THEN 1 ELSE 0 END,
                pe.ordem_qualificacao ASC,
                e.nome ASC
        ''', (etapa_id, etapa_id))
        
        equipes_pilotos = cursor.fetchall()
        
        # 3. Contar participantes conectados
        cursor.close()
        conn.close()
        
        evento_data = {
            'etapa': {
                'id': etapa_info['id'],
                'numero': etapa_info['numero'],
                'nome': etapa_info['nome'],
                'campeonato_nome': etapa_info['campeonato_nome'],
                'serie': etapa_info['serie'],
                'data': str(etapa_info['data_etapa']) if etapa_info['data_etapa'] else None,
                'hora': str(etapa_info['hora_etapa']) if etapa_info['hora_etapa'] else None,
                'status': etapa_info['status'],
                'qualificacao_finalizada': bool(etapa_info['qualificacao_finalizada']),
                'descricao': etapa_info['descricao']
            },
            'equipes': equipes_pilotos,
            'total_equipes': len(equipes_pilotos),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        
        return jsonify({'sucesso': True, 'evento': evento_data})
    except Exception as e:
        print(f"[API] Erro ao obter evento: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/<etapa_id>/notas/<equipe_id>', methods=['POST'])
def salvar_notas_etapa(etapa_id, equipe_id):
    """Salva as notas de linha, ângulo e estilo de uma equipe na etapa.
    Apenas admin pode salvar. Salva na tabela volta e marca o próximo piloto como em_andamento."""
    try:
        # Verificar se é admin
        if not session.get('admin') or session.get('tipo') != 'admin':
            return jsonify({'sucesso': False, 'erro': 'Apenas admin pode salvar notas'}), 403
        
        dados = request.json
        nota_linha = dados.get('nota_linha')
        nota_angulo = dados.get('nota_angulo')
        nota_estilo = dados.get('nota_estilo')
        
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Buscar o piloto_id da equipe na etapa
        cursor.execute('''
            SELECT pe.piloto_id, pe.ordem_qualificacao
            FROM participacoes_etapas pe
            WHERE pe.etapa_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
            AND pe.equipe_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
            LIMIT 1
        ''', (etapa_id, equipe_id))
        
        participacao = cursor.fetchone()
        if not participacao:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Participação não encontrada'}), 404
        
        piloto_id = participacao['piloto_id']
        
        # 2. Buscar volta existente para pegar valores anteriores
        cursor.execute('''
            SELECT nota_linha, nota_angulo, nota_estilo, status FROM volta 
            WHERE id_piloto COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
            AND id_equipe COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
            AND id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
        ''', (piloto_id, equipe_id, etapa_id))
        
        volta_atual = cursor.fetchone()
        
        # Usar valores anteriores se não foram enviados novos
        if volta_atual:
            if nota_linha is None:
                nota_linha = volta_atual['nota_linha']
            if nota_angulo is None:
                nota_angulo = volta_atual['nota_angulo']
            if nota_estilo is None:
                nota_estilo = volta_atual['nota_estilo']
        else:
            # Se não existe volta, usar 0 como padrão
            nota_linha = nota_linha if nota_linha is not None else 0
            nota_angulo = nota_angulo if nota_angulo is not None else 0
            nota_estilo = nota_estilo if nota_estilo is not None else 0
        
        # Garantir que são números
        nota_linha = int(nota_linha) if nota_linha else 0
        nota_angulo = int(nota_angulo) if nota_angulo else 0
        nota_estilo = int(nota_estilo) if nota_estilo else 0
        
        # 3. Atualizar ou criar volta - NÃO mudar status, apenas salvar notas
        if volta_atual:
            # Atualizar volta existente - manter status atual
            cursor.execute('''
                UPDATE volta 
                SET nota_linha = %s, nota_angulo = %s, nota_estilo = %s
                WHERE id_piloto COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                AND id_equipe COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                AND id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
            ''', (nota_linha, nota_angulo, nota_estilo, piloto_id, equipe_id, etapa_id))
        else:
            # Criar nova volta com status aguardando
            cursor.execute('''
                INSERT INTO volta (id_piloto, id_equipe, id_etapa, nota_linha, nota_angulo, nota_estilo, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'aguardando')
            ''', (piloto_id, equipe_id, etapa_id, nota_linha, nota_angulo, nota_estilo))
        
        # 4. Se preencheu TODAS as 3 notas da pessoa que está 'andando', marcar como finalizado e progressão
        if volta_atual and volta_atual['status'] == 'andando':
            # Verificar se TODAS as 3 notas foram preenchidas (todas > 0)
            tem_todas_notas = nota_linha > 0 and nota_angulo > 0 and nota_estilo > 0
            
            if tem_todas_notas:
                print(f"[VOLTA] Todas as 3 notas preenchidas! linha={nota_linha}, angulo={nota_angulo}, estilo={nota_estilo}")
                
                # Marcar o atual como 'finalizado'
                cursor.execute('''
                    UPDATE volta 
                    SET status = 'finalizado'
                    WHERE id_piloto COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                    AND id_equipe COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                    AND id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                ''', (piloto_id, equipe_id, etapa_id))
                
                # Buscar o que está em 'proximo' para passar para 'andando'
                cursor.execute('''
                    SELECT v.id_piloto, v.id_equipe
                    FROM volta v
                    WHERE v.id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                    AND v.status = 'proximo'
                    LIMIT 1
                ''', (etapa_id,))
                
                proximo_em_fila = cursor.fetchone()
                if proximo_em_fila:
                    # Marcar o próximo como 'andando'
                    cursor.execute('''
                        UPDATE volta 
                        SET status = 'andando'
                        WHERE id_piloto COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                        AND id_equipe COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                        AND id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                    ''', (proximo_em_fila['id_piloto'], proximo_em_fila['id_equipe'], etapa_id))
                    
                    # Buscar o primeiro 'aguardando' e passar para 'proximo'
                    cursor.execute('''
                        SELECT v.id_piloto, v.id_equipe
                        FROM volta v
                        WHERE v.id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                        AND v.status = 'aguardando'
                        ORDER BY v.id ASC
                        LIMIT 1
                    ''', (etapa_id,))
                    
                    proximo_aguardando = cursor.fetchone()
                    if proximo_aguardando:
                        cursor.execute('''
                            UPDATE volta 
                            SET status = 'proximo'
                            WHERE id_piloto COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                            AND id_equipe COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                            AND id_etapa COLLATE utf8mb4_general_ci = %s COLLATE utf8mb4_general_ci
                        ''', (proximo_aguardando['id_piloto'], proximo_aguardando['id_equipe'], etapa_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'sucesso': True, 'mensagem': 'Notas salvas com sucesso'})
    except Exception as e:
        print(f"[API] Erro ao salvar notas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/<etapa_id>/entrar-evento', methods=['POST'])
def entrar_evento_etapa(etapa_id):
    """Registra que alguém entrou no evento (equipe, piloto ou admin)"""
    try:
        dados = request.json or {}
        usuario_tipo = dados.get('tipo')  # 'admin', 'equipe', 'piloto'
        usuario_id = dados.get('id')
        usuario_nome = dados.get('nome')
        
        if not all([usuario_tipo, usuario_id, usuario_nome]):
            return jsonify({'sucesso': False, 'erro': 'Parâmetros obrigatórios: tipo, id, nome'}), 400
        
        print(f"[EVENTO] {usuario_tipo} ({usuario_id}) entrou no evento {etapa_id}")
        
        # Aqui você poderia armazenar em cache ou banco que este usuário entrou
        # Por enquanto, apenas registra
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'{usuario_tipo} {usuario_nome} conectado ao evento',
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
    except Exception as e:
        print(f"[API] Erro ao entrar no evento: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/<etapa_id>/entrar-qualificacao', methods=['POST'])
@requer_login_api
def entrar_qualificacao(etapa_id):
    """Piloto entra na qualificacao"""
    try:
        piloto_id = session.get('piloto_id')
        if not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'Nao autenticado'}), 401
        
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            'SELECT status FROM etapas WHERE id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci', 
            (etapa_id,)
        )
        etapa = cursor.fetchone()
        if not etapa:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Etapa nao encontrada'}), 404
        
        if etapa['status'] != 'qualificacao':
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Qualificacao nao esta aberta'}), 400
        
        cursor.execute(
            'SELECT id, equipe_id FROM candidatos_piloto_etapa WHERE etapa_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci AND piloto_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci',
            (etapa_id, piloto_id)
        )
        candidato = cursor.fetchone()
        if not candidato:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Piloto nao esta inscrito'}), 404
        
        cursor.close()
        conn.close()
        
        return jsonify({'sucesso': True, 'mensagem': 'Bem-vindo a qualificacao!'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/etapas/<etapa_id>/entrar-batalhas', methods=['POST'])
@requer_login_api
def entrar_batalhas(etapa_id):
    """Piloto entra nas batalhas"""
    try:
        piloto_id = session.get('piloto_id')
        if not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'Nao autenticado'}), 401
        
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            'SELECT status FROM etapas WHERE id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci', 
            (etapa_id,)
        )
        etapa = cursor.fetchone()
        if not etapa:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Etapa nao encontrada'}), 404
        
        if etapa['status'] != 'batalhas':
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Batalhas nao estao abertas'}), 400
        
        cursor.execute(
            'SELECT id, equipe_id FROM candidatos_piloto_etapa WHERE etapa_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci AND piloto_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci',
            (etapa_id, piloto_id)
        )
        candidato = cursor.fetchone()
        if not candidato:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Piloto nao esta inscrito'}), 404
        
        cursor.close()
        conn.close()
        
        return jsonify({'sucesso': True, 'mensagem': 'Bem-vindo as batalhas!'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/etapas/gerar-pix-participacao', methods=['POST'])
@requer_login_api
def gerar_pix_participacao():
    """Gera um PIX para participação quando o usuário seleciona como vai participar"""
    try:
        dados = request.json
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id') or obter_equipe_id_request()
        tipo_participacao = dados.get('tipo_participacao') or dados.get('tipo', 'dono_vai_andar')
        carro_id = dados.get('carro_id')
        
        print(f"\n[PIX PARTICIPAÇÃO] Gerando PIX")
        print(f"[PIX PARTICIPAÇÃO] Etapa: {etapa_id}")
        print(f"[PIX PARTICIPAÇÃO] Equipe: {equipe_id}")
        print(f"[PIX PARTICIPAÇÃO] Tipo: {tipo_participacao}")
        print(f"[PIX PARTICIPAÇÃO] Carro: {carro_id}")
        
        if not etapa_id or not equipe_id or not carro_id:
            return jsonify({'sucesso': False, 'erro': 'Etapa, equipe e carro são obrigatórios'}), 400
        
        # Validar tipos aceitos
        tipos_validos = ['dono_vai_andar', 'tenho_piloto', 'precisa_piloto']
        if tipo_participacao not in tipos_validos:
            return jsonify({'sucesso': False, 'erro': f'Tipo inválido. Aceitos: {tipos_validos}'}), 400
        
        # Gerar PIX de participação
        resultado = api.db.gerar_pix_participacao(equipe_id, etapa_id, tipo_participacao, carro_id)
        
        # Verificar se precisa regularizar saldo primeiro
        if 'requer_regularizacao' in resultado and resultado['requer_regularizacao']:
            print(f"[PIX PARTICIPAÇÃO] ⚠️ Regularização necessária: R$ {resultado['valor_necessario']:.2f}")
            return jsonify(resultado), 200  # Retorna 200 pois não é erro técnico, é situação esperada
        
        if resultado['sucesso']:
            print(f"[PIX PARTICIPAÇÃO] ✅ PIX gerado: {resultado['transacao_id']}")
            print(f"[PIX PARTICIPAÇÃO] Valor: R$ {resultado['valor']:.2f}")
            
            return jsonify(resultado)
        else:
            print(f"[PIX PARTICIPAÇÃO] ❌ Erro: {resultado['erro']}")
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[ERRO] Erro ao gerar PIX de participação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/gerar-pix-regularizacao', methods=['POST'])
@requer_login_api
def gerar_pix_regularizacao():
    """Gera um PIX para regularizar o saldo e então participar de uma etapa"""
    try:
        from src.mercado_pago_client import mp_client
        
        dados = request.json
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id') or obter_equipe_id_request()
        tipo_participacao = dados.get('tipo_participacao')
        carro_id = dados.get('carro_id')
        valor_regularizacao = dados.get('valor_regularizacao')
        
        print(f"\n[PIX REGULARIZAÇÃO] Gerando PIX de regularização")
        print(f"[PIX REGULARIZAÇÃO] Equipe: {equipe_id}, Valor: R$ {valor_regularizacao:.2f}")
        
        if not all([etapa_id, equipe_id, carro_id, valor_regularizacao, tipo_participacao]):
            return jsonify({'sucesso': False, 'erro': 'Parâmetros obrigatórios faltando'}), 400
        
        # Obter dados da equipe e etapa em uma única conexão
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT nome FROM equipes WHERE id = %s', (equipe_id,))
        equipe_result = cursor.fetchone()
        
        if not equipe_result:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404
        
        equipe_nome = equipe_result['nome']
        
        # Obter nome da etapa
        cursor.execute('SELECT nome FROM etapas WHERE id = %s', (etapa_id,))
        etapa_result = cursor.fetchone()
        etapa_nome = etapa_result['nome'] if etapa_result else 'Etapa desconhecida'
        
        cursor.close()
        conn.close()
        
        # Criar transação PIX de regularização
        dados_adicionais = {
            'tipo': 'regularizacao',
            'tipo_participacao': tipo_participacao,
            'carro_id': carro_id,
            'etapa_id': etapa_id
        }
        
        transacao_id = api.db.criar_transacao_pix(
            equipe_id=equipe_id,
            equipe_nome=equipe_nome,
            tipo_item='regularizacao_saldo',
            item_id=etapa_id,
            item_nome=f'Regularização de saldo para participar de {etapa_nome}',
            valor_item=valor_regularizacao,
            valor_taxa=0.0,
            carro_id=carro_id,
            dados_adicionais=dados_adicionais
        )
        
        if not transacao_id:
            return jsonify({'sucesso': False, 'erro': 'Erro ao criar transação PIX'}), 500
        
        # Agora gerar o PIX no MercadoPago
        print(f"[PIX REGULARIZAÇÃO] Gerando QR Code no MercadoPago...")
        mp_resultado = mp_client.gerar_qr_code_pix(
            descricao=f'Regularização de saldo - {etapa_nome}',
            valor=valor_regularizacao,
            referencia=transacao_id
        )
        
        if mp_resultado['sucesso']:
            print(f"[PIX REGULARIZAÇÃO] ✅ QR Code gerado: {mp_resultado['id']}")
            
            # Atualizar transação com dados do MercadoPago
            api.db.atualizar_transacao_pix(
                transacao_id=transacao_id,
                mercado_pago_id=mp_resultado.get('id'),
                qr_code=mp_resultado.get('qr_code', ''),
                qr_code_url=mp_resultado.get('qr_code_url', '')
            )
        else:
            print(f"[PIX REGULARIZAÇÃO] ⚠️ Erro ao gerar QR Code: {mp_resultado.get('erro')}")
            # Mesmo com erro no QR Code, a transação foi criada
        
        print(f"[PIX REGULARIZAÇÃO] ✅ PIX de regularização criado: {transacao_id}")
        
        return jsonify({
            'sucesso': True,
            'transacao_id': transacao_id,
            'equipe_id': equipe_id,
            'etapa_id': etapa_id,
            'valor': valor_regularizacao,
            'mensagem': 'PIX de regularização gerado. Após pagar, você poderá participar da etapa.'
        })
        
    except Exception as e:
        print(f"[ERRO] Erro ao gerar PIX de regularização: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/equipe/gerar-pix', methods=['POST'])
def etapa_equipe_gerar_pix():
    """Valida a situação da equipe e retorna o que fazer (regularizar, escolher, ou já inscrever)"""
    try:
        dados = request.json
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id') or obter_equipe_id_request()
        carro_id = dados.get('carro_id')
        tipo_participacao = dados.get('tipo_participacao')
        
        print(f"\n[GERAR PIX ETAPA] Validando situação da equipe")
        print(f"[GERAR PIX ETAPA] Equipe: {equipe_id}, Etapa: {etapa_id}")
        
        # Validar dados
        resultado = api.db.gerar_pix_participacao(equipe_id, etapa_id, tipo_participacao, carro_id)
        
        # Retornar o resultado (pode ter requer_regularizacao ou requer_escolha_pagamento)
        return jsonify(resultado)
        
    except Exception as e:
        print(f"[ERRO] Erro ao validar PIX da etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/gerar-pix-inscricao', methods=['POST'])
def gerar_pix_inscricao():
    """Gera um PIX para inscrição sem débito prévio"""
    try:
        from src.mercado_pago_client import mp_client
        
        dados = request.json
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id') or obter_equipe_id_request()
        carro_id = dados.get('carro_id')
        tipo_participacao = dados.get('tipo_participacao')
        valor_inscricao = dados.get('valor_inscricao')
        
        print(f"\n[PIX INSCRIÇÃO] Gerando PIX de inscrição")
        print(f"[PIX INSCRIÇÃO] Equipe: {equipe_id}, Valor: R$ {valor_inscricao:.2f}")
        
        if not all([etapa_id, equipe_id, carro_id, valor_inscricao, tipo_participacao]):
            return jsonify({'sucesso': False, 'erro': 'Parâmetros obrigatórios faltando'}), 400
        
        # Obter dados da equipe e etapa
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT nome FROM equipes WHERE id = %s', (equipe_id,))
        equipe_result = cursor.fetchone()
        
        if not equipe_result:
            cursor.close()
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404
        
        equipe_nome = equipe_result['nome']
        
        # Obter nome da etapa
        cursor.execute('SELECT nome FROM etapas WHERE id = %s', (etapa_id,))
        etapa_result = cursor.fetchone()
        etapa_nome = etapa_result['nome'] if etapa_result else 'Etapa desconhecida'
        
        cursor.close()
        conn.close()
        
        # Criar transação PIX de inscrição
        dados_adicionais = {
            'tipo': 'inscricao_etapa',
            'tipo_participacao': tipo_participacao,
            'carro_id': carro_id,
            'etapa_id': etapa_id
        }
        
        transacao_id = api.db.criar_transacao_pix(
            equipe_id=equipe_id,
            equipe_nome=equipe_nome,
            tipo_item='inscricao_etapa',
            item_id=etapa_id,
            item_nome=f'Inscrição - {etapa_nome}',
            valor_item=valor_inscricao,
            valor_taxa=0.0,
            carro_id=carro_id,
            dados_adicionais=dados_adicionais
        )
        
        if not transacao_id:
            return jsonify({'sucesso': False, 'erro': 'Erro ao criar transação PIX'}), 500
        
        # Agora gerar o PIX no MercadoPago
        print(f"[PIX INSCRIÇÃO] Gerando QR Code no MercadoPago...")
        mp_resultado = mp_client.gerar_qr_code_pix(
            descricao=f'Inscrição na etapa - {etapa_nome}',
            valor=valor_inscricao,
            referencia=transacao_id
        )
        
        if mp_resultado['sucesso']:
            print(f"[PIX INSCRIÇÃO] ✅ QR Code gerado: {mp_resultado['id']}")
            
            # Atualizar transação com dados do MercadoPago
            api.db.atualizar_transacao_pix(
                transacao_id=transacao_id,
                mercado_pago_id=mp_resultado.get('id'),
                qr_code=mp_resultado.get('qr_code', ''),
                qr_code_url=mp_resultado.get('qr_code_url', '')
            )
        else:
            print(f"[PIX INSCRIÇÃO] ⚠️ Erro ao gerar QR Code: {mp_resultado.get('erro')}")
        
        print(f"[PIX INSCRIÇÃO] ✅ PIX de inscrição criado: {transacao_id}")
        
        return jsonify({
            'sucesso': True,
            'transacao_id': transacao_id,
            'equipe_id': equipe_id,
            'etapa_id': etapa_id,
            'valor': valor_inscricao,
            'mensagem': 'PIX de inscrição gerado.'
        })
        
    except Exception as e:
        print(f"[ERRO] Erro ao gerar PIX de inscrição: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/inscrever-com-debito', methods=['POST'])
def inscrever_com_debito():
    """Inscreve a equipe na etapa sem PIX, adicionando ao débito"""
    try:
        dados = request.json
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id') or obter_equipe_id_request()
        carro_id = dados.get('carro_id')
        tipo_participacao = dados.get('tipo_participacao')
        valor_inscricao = dados.get('valor_inscricao')
        
        print(f"\n[INSCRIÇÃO DÉBITO] Inscrevendo com débito")
        print(f"[INSCRIÇÃO DÉBITO] Equipe: {equipe_id}, Valor: R$ {valor_inscricao:.2f}")
        
        if not all([etapa_id, equipe_id, carro_id, valor_inscricao, tipo_participacao]):
            return jsonify({'sucesso': False, 'erro': 'Parâmetros obrigatórios faltando'}), 400
        
        # 0. Validar: carro deve pertencer à equipe, estar ativo e ter todas as peças
        conn_val = api.db._get_conn()
        cur_val = conn_val.cursor(dictionary=True)
        cur_val.execute('SELECT id, equipe_id, status FROM carros WHERE id = %s', (carro_id,))
        cr = cur_val.fetchone()
        cur_val.close()
        conn_val.close()
        if not cr:
            return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 400
        if str(cr.get('equipe_id', '')) != str(equipe_id):
            return jsonify({'sucesso': False, 'erro': 'Este carro não pertence à sua equipe'}), 400
        if (cr.get('status') or 'repouso').lower() != 'ativo':
            return jsonify({'sucesso': False, 'erro': 'Sua equipe precisa ter um carro ATIVO para participar. Ative um carro na Garagem.'}), 400
        validacao = api.db.validar_pecas_carro(carro_id, equipe_id)
        if not validacao.get('valido'):
            pecas_faltando = validacao.get('pecas_faltando', [])
            nomes = [p.upper().replace('_', '-') for p in pecas_faltando]
            return jsonify({'sucesso': False, 'erro': f'O carro precisa ter todas as peças instaladas. Faltando: {", ".join(nomes)}'}), 400
        
        # 1. Deduzir valor do saldo_pix (vai ficar negativo)
        resultado_saldo = api.db.atualizar_saldo_pix(equipe_id, -valor_inscricao)
        
        if not resultado_saldo['sucesso']:
            print(f"[INSCRIÇÃO DÉBITO] ⚠️ Erro ao atualizar saldo")
            return jsonify({'sucesso': False, 'erro': 'Erro ao atualizar saldo'}), 400
        
        print(f"[INSCRIÇÃO DÉBITO] ✅ Saldo atualizado: R$ {resultado_saldo['novo_saldo']:.2f}")
        
        # 2. Registrar participação na etapa
        conn = api.db._get_conn()
        cursor = conn.cursor()
        
        participacao_id = str(__import__('uuid').uuid4())
        
        cursor.execute('''
            INSERT INTO participacoes_etapas 
            (id, etapa_id, equipe_id, carro_id, status, data_inscricao, data_atualizacao, tipo_participacao)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s)
        ''', (
            participacao_id,
            etapa_id,
            equipe_id,
            carro_id,
            'ativa',
            tipo_participacao
        ))
        
        conn.commit()
        conn.close()
        
        print(f"[INSCRIÇÃO DÉBITO] ✅ Participação registrada: {participacao_id}")
        print(f"[INSCRIÇÃO DÉBITO] ===== INSCRIÇÃO CONCLUÍDA =====\n")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Inscrito na etapa! O valor será cobrado na próxima etapa.',
            'participacao_id': participacao_id,
            'novo_saldo': resultado_saldo.get('novo_saldo', 0)
        })
        
    except Exception as e:
        print(f"[INSCRIÇÃO DÉBITO] ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/etapas/equipe/participar', methods=['POST'])
def participar_etapa_equipe():
    """Inscreve uma equipe em uma etapa com um dos 3 tipos de participação"""
    try:
        dados = request.json
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id')
        carro_id = dados.get('carro_id')
        # Aceitar tanto 'tipo_participacao' quanto 'tipo' para compatibilidade
        tipo_participacao = dados.get('tipo_participacao') or dados.get('tipo', 'dono_vai_andar')
        
        if not etapa_id or not equipe_id or not carro_id:
            return jsonify({'sucesso': False, 'erro': 'Etapa, equipe e carro são obrigatórios'}), 400
        
        # Validar tipos aceitos
        tipos_validos = ['dono_vai_andar', 'tenho_piloto', 'precisa_piloto', 'equipe_completa']
        if tipo_participacao not in tipos_validos:
            return jsonify({'sucesso': False, 'erro': f'Tipo inválido. Aceitos: {tipos_validos}'}), 400
        
        import uuid
        inscricao_id = str(uuid.uuid4())
        resultado = api.db.inscrever_equipe_etapa(inscricao_id, etapa_id, equipe_id, carro_id, tipo_participacao)
        
        # Verificar se precisa regularizar saldo primeiro
        if 'requer_regularizacao' in resultado and resultado['requer_regularizacao']:
            print(f"[ETAPA] ⚠️ Regularização necessária: R$ {resultado['valor_necessario']:.2f}")
            return jsonify(resultado), 200  # Retorna 200 pois não é erro técnico, é situação esperada
        
        if resultado['sucesso']:
            valor_cobrado = resultado.get('valor_cobrado', 0)
            saldo_novo = resultado.get('saldo_novo', 0)
            print(f"[ETAPA] Equipe inscrita em etapa ({tipo_participacao}) - Cobrado: {valor_cobrado}")
            
            # Adicionar mensagem amigável
            resultado['mensagem'] = f"✓ Inscrito com sucesso! Taxa cobrada: {valor_cobrado:.2f} | Saldo: {saldo_novo:.2f}"
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
    except Exception as e:
        print(f"[ERRO] Erro ao inscrever equipe em etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/alocar-piloto-etapa', methods=['POST'])
def alocar_piloto_equipe_etapa():
    """Admin aloca um piloto a uma equipe em uma etapa"""
    try:
        dados = request.json
        participacao_id = dados.get('participacao_id')
        piloto_id = dados.get('piloto_id')
        
        if not participacao_id or not piloto_id:
            return jsonify({'sucesso': False, 'erro': 'Participacao e piloto são obrigatórios'}), 400
        
        resultado = api.db.alocar_piloto_equipe_etapa(participacao_id, piloto_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[ERRO] Erro ao alocar piloto: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/listar-pilotos')
def listar_pilotos():
    """Lista todos os pilotos disponíveis"""
    try:
        pilotos = api.db.listar_pilotos()
        return jsonify(pilotos)
    except Exception as e:
        print(f"[ERRO] Erro ao listar pilotos: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/admin/atualizar-etapa', methods=['POST'])
def atualizar_etapa():
    """Admin atualiza as datas de início e fim de uma etapa"""
    try:
        dados = request.json
        etapa_id = dados.get('etapa_id')
        data_inicio = dados.get('data_inicio')
        data_fim = dados.get('data_fim')
        
        if not etapa_id:
            return jsonify({'sucesso': False, 'erro': 'ID da etapa é obrigatório'}), 400
        
        # Validar se as datas são válidas (se fornecidas)
        if data_inicio and data_fim:
            from datetime import datetime
            try:
                dt_inicio = datetime.fromisoformat(data_inicio.replace('T', ' ').split('.')[0])
                dt_fim = datetime.fromisoformat(data_fim.replace('T', ' ').split('.')[0])
                if dt_fim < dt_inicio:
                    return jsonify({'sucesso': False, 'erro': 'Data de término não pode ser anterior à data de início'}), 400
            except Exception as e:
                print(f"[ERRO] Erro ao validar datas: {e}")
                return jsonify({'sucesso': False, 'erro': 'Formato de data inválido'}), 400
        
        # Atualizar a etapa no banco
        resultado = api.db.atualizar_etapa_datas(etapa_id, data_inicio, data_fim)
        return jsonify(resultado)
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/definir-valor-participacao', methods=['POST'])
@requer_admin
def definir_valor_participacao():
    """Admin define o valor de participação de uma etapa"""
    try:
        dados = request.json
        etapa_id = dados.get('etapa_id')
        valor = dados.get('valor')
        descricao = dados.get('descricao', '')
        
        if not etapa_id or valor is None:
            return jsonify({'sucesso': False, 'erro': 'Etapa e valor são obrigatórios'}), 400
        
        try:
            valor = float(valor)
            if valor < 0:
                return jsonify({'sucesso': False, 'erro': 'Valor não pode ser negativo'}), 400
        except:
            return jsonify({'sucesso': False, 'erro': 'Valor deve ser um número'}), 400
        
        resultado = api.db.definir_valor_participacao_etapa(etapa_id, valor, descricao)
        return jsonify(resultado)
    except Exception as e:
        print(f"[ERRO] Erro ao definir valor: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/obter-valor-participacao/<etapa_id>', methods=['GET'])
def obter_valor_participacao(etapa_id):
    """Retorna o valor de participação de uma etapa"""
    try:
        valor = api.db.obter_valor_participacao_etapa(etapa_id)
        return jsonify({'etapa_id': etapa_id, 'valor': valor})
    except Exception as e:
        print(f"[ERRO] Erro ao obter valor: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/verificar-pecas-carro', methods=['GET'])
@requer_login_api
def verificar_pecas_carro():
    """Verifica se o carro tem todas as peças necessárias"""
    try:
        carro_id = request.args.get('carro_id')
        equipe_id = request.args.get('equipe_id')
        
        if not carro_id or not equipe_id:
            return jsonify({'completo': False, 'erro': 'Carro e equipe são obrigatórios'}), 400
        
        # Peças necessárias
        pecas_necessarias = ['motor', 'cambio', 'suspensao', 'kit_angulo', 'diferencial']
        
        # Verificar cada peça
        pecas_faltando = []
        for tipo in pecas_necessarias:
            tem_peca = api.db.verificar_peca_carro(carro_id, equipe_id, tipo)
            if not tem_peca:
                pecas_faltando.append(f"• {tipo.upper()}")
        
        completo = len(pecas_faltando) == 0
        
        return jsonify({
            'completo': completo,
            'pecas_faltando': pecas_faltando,
            'mensagem': '✓ Carro completo!' if completo else 'Carro incompleto'
        })
    except Exception as e:
        print(f"[ERRO] Erro ao verificar peças: {e}")
        return jsonify({'completo': False, 'erro': str(e)}), 500



@app.route('/api/comprar', methods=['POST'])
@requer_login_api
def comprar():
    """Processa uma compra de peça (cria solicitação pendente)"""
    equipe_id = obter_equipe_id_request()
    if not equipe_id:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    dados = request.json
    tipo = dados.get('tipo')  # 'carro' ou 'peca'
    item_id = dados.get('item_id')  # modelo_id (compatibilidade retroativa)
    variacao_id = dados.get('variacao_id')  # variacao_carro_id (novo)
    carro_id = dados.get('carro_id')  # Opcional: para peças, qual carro instalar
    
    print(f"\n{'='*60}")
    print(f"[COMPRA] Novo pedido")
    print(f"  Equipe ID: {equipe_id}")
    print(f"  Tipo: {tipo}")
    print(f"  Item ID: {item_id}")
    print(f"  Variação ID: {variacao_id}")
    print(f"{'='*60}")
    
    if not all([tipo]):
        return jsonify({'erro': 'Dados incompletos'}), 400
    
    try:
        print(f"[COMPRA] Obtendo equipe...")
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            print(f"[COMPRA] ERRO: Equipe não encontrada!")
            return jsonify({'erro': 'Equipe não encontrada'}), 404
        
        print(f"[COMPRA] Equipe: {equipe.nome} - Saldo: {equipe.doricoins}")
        
        if tipo == 'carro':
            # Comprar carro - pode ser com variação_id (novo) ou item_id (compatibilidade)
            print(f"[COMPRA] Comprando carro...")
            
            if variacao_id:
                # Novo: Usar variação específica
                print(f"[COMPRA] Usando variação {variacao_id}...")
                variacao_dict = api.db.buscar_variacao_carro_por_id(variacao_id)
                print(f"[COMPRA] Variação encontrada: {variacao_dict}")
                
                if not variacao_dict:
                    print(f"[COMPRA] ERRO: Variação não encontrada!")
                    return jsonify({'erro': 'Variação não encontrada'}), 404
                
                modelo_id = variacao_dict['modelo_carro_loja_id']
                carro_modelo = None
                for modelo in api.loja_carros.modelos:
                    if modelo.id == modelo_id:
                        carro_modelo = modelo
                        break
                
                if not carro_modelo:
                    print(f"[COMPRA] ERRO: Modelo do carro não encontrado!")
                    return jsonify({'erro': 'Modelo do carro não encontrado'}), 404
            
            else:
                # Compatibilidade: Usar modelo_id (item_id)
                print(f"[COMPRA] Procurando modelo de carro {item_id}...")
                carro_modelo = None
                for modelo in api.loja_carros.modelos:
                    if modelo.id == item_id:
                        carro_modelo = modelo
                        break

                if not carro_modelo:
                    print(f"[COMPRA] ERRO: Carro não encontrado!")
                    return jsonify({'erro': 'Carro não encontrado'}), 404
                
                # Se há variações, usar a primeira (compatibilidade)
                if carro_modelo.variacoes and len(carro_modelo.variacoes) > 0:
                    variacao_id = carro_modelo.variacoes[0].id
                    print(f"[COMPRA] Usando variação padrão: {variacao_id}")
                else:
                    print(f"[COMPRA] AVISO: Modelo não possui variações definidas!")
                    variacao_id = None

            print(f"[COMPRA] Carro encontrado: {carro_modelo.marca} {carro_modelo.modelo}")
            print(f"[COMPRA] Variação ID após processamento: {variacao_id}")
                
            # Buscar o valor da variação
            variacao_dict = None
            if variacao_id:
                variacao_dict = api.db.buscar_variacao_carro_por_id(variacao_id)
                if not variacao_dict:
                    print(f"[COMPRA] AVISO: Variação {variacao_id} não encontrada no banco!")
            
            preco_variacao = float(variacao_dict.get('valor', carro_modelo.preco)) if variacao_dict else float(carro_modelo.preco)
            print(f"[COMPRA] Preço da variação: R${preco_variacao}")

            # Verificar saldo com base no valor da variação
            if equipe.doricoins < preco_variacao:
                print(f"[COMPRA] ERRO: Saldo insuficiente! Tem: {equipe.doricoins}, Precisa: {preco_variacao}")
                return jsonify({'erro': 'Saldo insuficiente'}), 400

            # Comprar carro com variação
            resultado = api.comprar_carro(equipe_id, carro_modelo.id, variacao_id)

            if resultado:
                print(f"[COMPRA] Carro {carro_modelo.marca} {carro_modelo.modelo} comprado com sucesso!")
                print(f"[COMPRA] Status: repouso (obrigatório)")
                
                # Registrar comissão
                try:
                    comissao_valor = float(api.db.obter_configuracao('comissao_carro') or '10')
                    api.db.registrar_comissao(
                        tipo='compra_carro',
                        valor=comissao_valor,
                        equipe_id=equipe_id,
                        equipe_nome=equipe.nome,
                        descricao=f'Compra de {carro_modelo.marca} {carro_modelo.modelo}'
                    )
                    print(f"[COMISSÃO] Registrada: R$ {comissao_valor} por compra de carro")
                except Exception as e:
                    print(f"[AVISO] Erro ao registrar comissão: {e}")
                
                return jsonify({
                    'sucesso': True,
                    'mensagem': f'Carro {carro_modelo.marca} {carro_modelo.modelo} comprado com sucesso! Adicionado à garagem com status repouso.',
                    'carro_status': 'repouso'
                })
            else:
                print(f"[COMPRA] ERRO: Falha ao comprar carro!")
                return jsonify({'erro': 'Falha ao processar compra do carro'}), 500
        
        elif tipo == 'peca':
            # Comprar peça - cria solicitação pendente
            print(f"[COMPRA] Processando peça...")
            print(f"[COMPRA] Carro ID recebido do body: {carro_id}")
            print(f"[COMPRA] Dados completos: {dados}")
            peca_loja = None
            for peca in api.loja_pecas.pecas:
                if peca.id == item_id:
                    peca_loja = peca
                    break
            
            if not peca_loja:
                print(f"[COMPRA] ERRO: Peça não encontrada!")
                return jsonify({'erro': 'Peça não encontrada'}), 404
            
            # ===== VALIDAÇÃO DE COMPATIBILIDADE =====
            compatibilidade_peca = getattr(peca_loja, 'compatibilidade', 'universal')
            print(f"[COMPRA] Compatibilidade da peça: {compatibilidade_peca}")
            
            # Se a peça não é universal, validar compatibilidade
            if compatibilidade_peca != 'universal':
                # Determinar qual carro será usado
                carro_alvo = None
                
                if carro_id:
                    # Procurar o carro específico nos carros da equipe
                    for c in equipe.carros:
                        if str(c.id) == str(carro_id):
                            carro_alvo = c
                            break
                
                # Se não especificou carro ou não encontrou, usar o ativo
                if not carro_alvo:
                    carro_alvo = equipe.carro
                
                if not carro_alvo:
                    print(f"[COMPRA] ERRO: Equipe não tem carro!")
                    return jsonify({'erro': 'Você precisa ter um carro para comprar peças'}), 400
                
                print(f"[COMPRA] Carro alvo: {carro_alvo.id} ({carro_alvo.marca} {carro_alvo.modelo})")
                print(f"[COMPRA] Compatibilidade da peça: {compatibilidade_peca}")
                
                # Agora permitimos instalar em qualquer carro da garagem
                # A validação de compatibilidade é mais permissiva
                compativel = True  # Por padrão, é compatível
                
                # Se a peça tiver compatibilidade específica, validar se o carro tem modelo_id
                modelo_id_alvo = str(getattr(carro_alvo, 'modelo_id', ''))
                modelo_id_compat = str(compatibilidade_peca)
                
                print(f"[COMPRA] Comparando modelo_id: '{modelo_id_alvo}' com compatibilidade '{modelo_id_compat}'")
                
                # Se o carro tem modelo_id, fazer comparação. Se não tiver, permite mesmo assim
                if modelo_id_alvo and modelo_id_alvo != modelo_id_compat:
                    compativel = False
                    print(f"[COMPRA] INCOMPATÍVEL - Carro não corresponde!")
                else:
                    print(f"[COMPRA] Compatibilidade OK - Pode instalar!")
                
                if not compativel:
                    print(f"[COMPRA] INCOMPATÍVEL!")
                    # Buscar nome do modelo esperado
                    modelo_nome_esperado = "desconhecido"
                    for modelo in api.loja_carros.modelos:
                        if str(modelo.id) == modelo_id_compat:
                            modelo_nome_esperado = f"{modelo.marca} {modelo.modelo}"
                            break
                    return jsonify({
                        'erro': f'A peça {peca_loja.nome} não é compatível com seu carro {carro_alvo.marca} {carro_alvo.modelo}. '
                               f'Esta peça é específica para {modelo_nome_esperado}.'
                    }), 400
                
                print(f"[COMPRA] Peça é compatível com o carro!")
            else:
                print(f"[COMPRA] Peça universal, compatível com qualquer carro")
            
            print(f"[COMPRA] Peça encontrada: {peca_loja.nome}")
            
            # Verificar saldo
            if equipe.doricoins < peca_loja.preco:
                print(f"[COMPRA] ERRO: Saldo insuficiente!")
                return jsonify({'erro': 'Saldo insuficiente'}), 400
            
            # Descontar saldo imediatamente
            equipe.doricoins -= peca_loja.preco
            api.db.salvar_equipe(equipe)
            print(f"[COMPRA] Saldo descontado. Novo saldo: {equipe.doricoins}")
            
            # Criar solicitação de compra de peça (pendente)
            solicitacao_id = str(uuid.uuid4())
            
            print(f"[COMPRA] Solicitação criada:")
            print(f"[COMPRA]   ID: {solicitacao_id}")
            print(f"[COMPRA]   Peça: {peca_loja.nome}")
            print(f"[COMPRA]   Tipo: {peca_loja.tipo}")
            print(f"[COMPRA]   Status: pendente")
            
            # Obter carro_id se foi selecionado
            carro_id = dados.get('carro_id')
            
            # Salvar solicitação no banco de dados (não duplica se já existir pendente mesma peça+carro)
            ok = api.db.salvar_solicitacao_peca(
                id=solicitacao_id,
                equipe_id=equipe_id,
                peca_id=item_id,
                quantidade=1,
                status='pendente',
                carro_id=carro_id
            )
            if not ok:
                erro = getattr(api.db, '_erro_solicitacao_peca', None)
                msg = 'Já existe uma solicitação pendente para esta peça neste carro.' if erro == 'duplicada' else 'Falha ao criar solicitação.'
                return jsonify({'sucesso': False, 'erro': msg}), 400 if erro == 'duplicada' else 500
            
            # Registrar comissão
            try:
                comissao_valor = float(api.db.obter_configuracao('comissao_peca') or '10')
                api.db.registrar_comissao(
                    tipo='compra_peca',
                    valor=comissao_valor,
                    equipe_id=equipe_id,
                    equipe_nome=equipe.nome,
                    descricao=f'Compra de {peca_loja.nome}'
                )
                print(f"[COMISSÃO] Registrada: R$ {comissao_valor} por compra de peça")
            except Exception as e:
                print(f"[AVISO] Erro ao registrar comissão: {e}")
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'Solicitação de {peca_loja.nome} enviada para análise do admin!',
                'solicitacao_id': solicitacao_id
            })
        
        else:
            return jsonify({'erro': 'Tipo de item inválido'}), 400
    
    except Exception as e:
        print(f"[ERRO COMPRA] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao processar compra: {str(e)}'}), 500

@app.route('/api/ativar-carro', methods=['POST'])
@requer_login_api
def ativar_carro_gerar_pix():
    """Gera PIX para ativar um carro já comprado"""
    try:
        from src.mercado_pago_client import mp_client
        
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        
        dados = request.json
        carro_id = dados.get('carro_id') if dados else None
        
        print(f"[ATIVAR CARRO] Request recebido - dados: {dados}, carro_id: {carro_id}")
        
        if not carro_id:
            print(f"[ATIVAR CARRO] ❌ ERRO: carro_id ausente no request")
            return jsonify({'erro': 'ID do carro é obrigatório'}), 400
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        print(f"[ATIVAR CARRO] Equipe carregada: {equipe}")
        if not equipe:
            print(f"[ATIVAR CARRO] ❌ ERRO: Equipe não encontrada")
            return jsonify({'erro': 'Equipe não encontrada'}), 404
        
        # Verificar se o carro existe e pertence à equipe
        carro = None
        print(f"[ATIVAR CARRO] Equipe tem {len(equipe.carros) if hasattr(equipe, 'carros') else 0} carros")
        if hasattr(equipe, 'carros') and isinstance(equipe.carros, list):
            for c in equipe.carros:
                print(f"[ATIVAR CARRO] Verificando carro {c.id} contra {carro_id}")
                if str(c.id) == str(carro_id):
                    carro = c
                    break
        
        if not carro:
            print(f"[ATIVAR CARRO] ❌ ERRO: Carro {carro_id} não encontrado ou não pertence à equipe")
            return jsonify({'erro': 'Carro não encontrado ou não pertence a esta equipe'}), 404
        
        print(f"[ATIVAR CARRO] ✅ Carro encontrado: {carro}")
        
        # Permite ativar carros incompletos - peças não são mais obrigatórias
        print(f"[ATIVAR CARRO] Peças do carro:")
        print(f"[ATIVAR CARRO]   motor: {carro.motor}")
        print(f"[ATIVAR CARRO]   cambio: {carro.cambio}")
        print(f"[ATIVAR CARRO]   suspensao: {carro.suspensao}")
        print(f"[ATIVAR CARRO]   kit_angulo: {carro.kit_angulo}")
        print(f"[ATIVAR CARRO]   diferenciais: {carro.diferenciais}")
        
        # Valor = taxa de ativação + (taxa de instalação por peça × quantidade); usa apenas config (não preço da peça)
        _, quantidade_pecas = api.db.obter_valor_total_pecas_nao_pagas_carro(carro_id, equipe_id)
        valor_ativacao = float(api.db.obter_configuracao('valor_ativacao_carro') or '10')
        valor_instalacao_peca = float(api.db.obter_configuracao('valor_instalacao_peca') or '10')
        valor_pecas = valor_instalacao_peca * quantidade_pecas
        valor_subtotal = valor_ativacao + valor_pecas
        
        print(f"[ATIVAR CARRO] 💸 Peças não pagas no carro: {quantidade_pecas} peça(s)")
        print(f"[ATIVAR CARRO] 💵 Cálculo: Ativação R$ {valor_ativacao} + instalação R$ {valor_instalacao_peca}/peça × {quantidade_pecas} = R$ {valor_subtotal:.2f}")
        
        taxa = mp_client.calcular_taxa(valor_subtotal)
        valor_total = round(valor_subtotal + taxa, 2)
        
        print(f"[ATIVAR CARRO] Taxa PIX: R$ {taxa}")
        print(f"[ATIVAR CARRO] Total a pagar: R$ {valor_total}")
        
        # Verificar se já existe uma transação pendente para este carro
        transacoes_existentes = api.db.listar_transacoes_pix(equipe_id=equipe_id, status='pendente')
        for trans in transacoes_existentes:
            if trans['tipo_item'] == 'carro_ativacao' and str(trans['item_id']) == str(carro_id):
                # Transação pendente já existe - retornar dados RECALCULADOS
                print(f"[ATIVAÇÃO CARRO] Transação pendente encontrada: {trans['id']}")
                print(f"[ATIVAÇÃO CARRO] Valores antigos: R$ {trans['valor_total']} total, R$ {trans['valor_item']} item")
                print(f"[ATIVAÇÃO CARRO] Valores recalculados: R$ {valor_total} total, R$ {valor_subtotal} item")
                print(f"[ATIVAÇÃO CARRO] Peças não pagas: {quantidade_pecas}")
                
                qr_code_url = trans['qr_code_url']
                if trans['qr_code'] and not qr_code_url.startswith('data:'):
                    print(f"[ATIVAÇÃO CARRO] Gerando imagem para código PIX existente...")
                    img_base64 = mp_client.gerar_qr_code_imagem_pix(trans['qr_code'])
                    if img_base64:
                        qr_code_url = f"data:image/png;base64,{img_base64}"
                        api.db.atualizar_transacao_pix(
                            transacao_id=trans['id'],
                            mercado_pago_id=trans.get('id', ''),
                            qr_code=trans['qr_code'],
                            qr_code_url=qr_code_url
                        )
                
                return jsonify({
                    'sucesso': True,
                    'transacao_id': trans['id'],
                    'qr_code_url': qr_code_url,
                    'valor_total': valor_total,
                    'valor_item': valor_subtotal,
                    'valor_ativacao': valor_ativacao,
                    'valor_pecas': valor_pecas,
                    'pecas_nao_pagas': quantidade_pecas,
                    'taxa': taxa,
                    'item_nome': f"Ativar: {carro.marca} {carro.modelo} (+ {quantidade_pecas} peças)",
                    'tipo_item': trans['tipo_item'],
                    'item_id': trans['item_id'],
                    'carro_id': str(carro_id),
                    'ja_existente': True
                })
        
        # Criar nova transação PIX
        transacao_id = api.db.criar_transacao_pix(
            equipe_id=equipe_id,
            equipe_nome=equipe.nome,
            tipo_item='carro_ativacao',
            item_id=carro_id,
            item_nome=f"Ativar: {carro.marca} {carro.modelo} (+ {quantidade_pecas} peças)",
            valor_item=valor_subtotal,
            valor_taxa=taxa
        )
        
        if not transacao_id:
            return jsonify({'erro': 'Erro ao criar transação'}), 500
        
        # Gerar QR Code no MercadoPago
        descricao = f"Ativação de {carro.marca} {carro.modelo} - {equipe.nome}"
        resultado_mp = mp_client.gerar_qr_code_pix(descricao, valor_total, transacao_id)
        
        if not resultado_mp.get('sucesso'):
            return jsonify({'erro': resultado_mp.get('erro', 'Erro ao gerar QR Code')}), 500
        
        # Atualizar transação com dados do MP
        api.db.atualizar_transacao_pix(
            transacao_id=transacao_id,
            mercado_pago_id=resultado_mp.get('id', ''),
            qr_code=resultado_mp.get('qr_code', ''),
            qr_code_url=resultado_mp.get('qr_code_url', '')
        )
        
        print(f"[ATIVAÇÃO CARRO] Gerado PIX para {carro.marca} {carro.modelo} - Valor: R$ {valor_total}")
        
        return jsonify({
            'sucesso': True,
            'transacao_id': transacao_id,
            'qr_code_url': resultado_mp.get('qr_code_url', ''),
            'valor_total': valor_total,
            'valor_item': valor_subtotal,
            'valor_ativacao': valor_ativacao,
            'valor_pecas': valor_pecas,
            'pecas_nao_pagas': quantidade_pecas,
            'taxa': taxa,
            'item_nome': f"Ativar: {carro.marca} {carro.modelo} (+ {quantidade_pecas} peças)",
            'tipo_item': 'carro_ativacao',
            'item_id': carro_id,
            'carro_id': carro_id
        })
    
    except Exception as e:
        print(f"[ERRO ATIVAÇÃO CARRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao processar ativação: {str(e)}'}), 500

@app.route('/api/mudar-carro', methods=['POST'])
@requer_login_api
def solicitar_mudanca_carro():
    """Cria uma solicitação para mudar o carro ativo"""
    equipe_id = obter_equipe_id_request()
    if not equipe_id:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    try:
        dados = request.get_json()
        novo_carro_id = dados.get('carro_id')
        
        if not novo_carro_id:
            return jsonify({'erro': 'ID do carro é obrigatório'}), 400
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'erro': 'Equipe não encontrada'}), 404
        
        # Verificar se o carro já é o ativo
        carro_ativo = equipe.carro
        if carro_ativo and str(carro_ativo.id) == str(novo_carro_id):
            return jsonify({'erro': 'Este carro já está ativo'}), 400
        
        # Buscar o novo carro na lista de carros da equipe
        novo_carro = None
        if hasattr(equipe, 'carros') and isinstance(equipe.carros, list):
            for c in equipe.carros:
                if str(c.id) == str(novo_carro_id):
                    novo_carro = c
                    break
        
        if not novo_carro:
            return jsonify({'erro': 'Carro não encontrado ou não pertence a esta equipe'}), 404
        
        # Criar solicitação de mudança de carro
        solicitacao_id = str(uuid.uuid4())
        
        # Salvar solicitação no banco de dados com ID|Marca|Modelo
        from datetime import datetime
        tipo_carro_value = f"{novo_carro_id}|{novo_carro.marca}|{novo_carro.modelo}"
        api.db.salvar_solicitacao_carro(
            solicitacao_id,
            equipe_id,
            tipo_carro_value,
            'pendente',
            datetime.now().isoformat()
        )
        
        print(f"[MUDANÇA CARRO] Solicitação criada para equipe {equipe_id}: {novo_carro.marca} {novo_carro.modelo}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Solicitação para ativar {novo_carro.marca} {novo_carro.modelo} criada!'
        })
    
    except Exception as e:
        print(f"[ERRO MUDANÇA CARRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao processar solicitação: {str(e)}'}), 500

@app.route('/api/historico/compras')
@requer_login_api
def get_historico_compras():
    """Retorna histórico de compras (todas as solicitações + transações PIX confirmadas)"""
    equipe_id = obter_equipe_id_request()
    if not equipe_id:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    historico = []
    
    try:
        # 1. Carregar solicitações de peças
        solicitacoes_db = api.db.carregar_solicitacoes_pecas(equipe_id)
        for sol in solicitacoes_db:
            historico.append({
                'id': sol.get('id'),
                'tipo': 'solicitacao',
                'peca_nome': sol.get('peca_nome', ''),
                'peca_tipo': sol.get('tipo_peca', ''),
                'preco': sol.get('preco', 0),
                'status': sol.get('status', ''),
                'timestamp': sol.get('data_solicitacao', ''),
                'processado_em': sol.get('processado_em', sol.get('data_solicitacao', ''))
            })
    except Exception as e:
        print(f"[HISTORICO COMPRAS] Erro ao carregar solicitações: {str(e)}")
    
    try:
        # 2. Carregar transações PIX confirmadas (aprovadas)
        transacoes_pix = api.db.listar_transacoes_pix(equipe_id=equipe_id, status='aprovado')
        for trans in transacoes_pix:
            historico.append({
                'id': trans.get('id'),
                'tipo': 'pix_payment',
                'item_nome': trans.get('item_nome', ''),
                'tipo_item': trans.get('tipo_item', ''),
                'preco': trans.get('valor_item', 0),
                'status': 'confirmado',
                'timestamp': trans.get('data_criacao', ''),
                'processado_em': trans.get('data_confirmacao', trans.get('data_criacao', '')),
                'valor_total': trans.get('valor_total', 0)
            })
    except Exception as e:
        print(f"[HISTORICO COMPRAS] Erro ao carregar transações PIX: {str(e)}")
    
    # Ordenar por data (mais recentes primeiro)
    historico.sort(key=lambda x: x.get('processado_em', ''), reverse=True)
    
    # Retornar últimas 20
    return jsonify(historico[-20:])

@app.route('/api/transferencia', methods=['POST'])
@requer_login_api
def transferencia_dinheiro():
    """Transferir dinheiro entre equipes (taxa configurável em Configurações)"""
    equipe_id_origem = obter_equipe_id_request()
    if not equipe_id_origem:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    try:
        dados = request.get_json()
        equipe_id_destino = dados.get('equipe_id_destino')
        valor = float(dados.get('valor', 0))
        taxa_bancaria = float(api.db.obter_configuracao('taxa_transferencia') or '10')
        
        print(f"[TRANSFERÊNCIA] Origem: {equipe_id_origem}, Destino: {equipe_id_destino}, Valor: {valor}")
        
        # Validações
        if not equipe_id_destino:
            return jsonify({'erro': 'Equipe destino não especificada'}), 400
        
        # Comparação robusta - string e lowercase
        origem_str = str(equipe_id_origem).strip().lower()
        destino_str = str(equipe_id_destino).strip().lower()
        
        print(f"[TRANSFERÊNCIA] Comparando: '{origem_str}' vs '{destino_str}'")
        
        if origem_str == destino_str:
            print(f"[TRANSFERÊNCIA] BLOQUEADO: Tentativa de enviar para si mesmo!")
            return jsonify({'erro': 'Não é permitido transferir para sua própria equipe'}), 400
        
        if valor <= 0:
            return jsonify({'erro': 'Valor deve ser maior que zero'}), 400
        
        # Obter equipes
        equipe_origem = api.gerenciador.obter_equipe(equipe_id_origem)
        equipe_destino = api.gerenciador.obter_equipe(equipe_id_destino)
        
        if not equipe_origem:
            return jsonify({'erro': 'Equipe origem não encontrada'}), 404
        
        if not equipe_destino:
            return jsonify({'erro': 'Equipe destino não encontrada'}), 404
        
        # Validar saldo
        if equipe_origem.doricoins < valor:
            return jsonify({'erro': f'Saldo insuficiente. Você tem {equipe_origem.doricoins}'}), 400
        
        # Calcular taxa
        taxa = valor * (taxa_bancaria / 100)
        valor_recebido = valor - taxa
        
        # Registrar transação
        timestamp = datetime.now().isoformat()
        
        # Criar ID único da transferência
        transferencia_id = str(uuid.uuid4())
        
        # Atualizar saldos
        equipe_origem.doricoins -= valor
        equipe_destino.doricoins += valor_recebido
        
        # Registrar no histórico de transferências (usando arquivo JSON)
        transferencia_info = {
            'id': transferencia_id,
            'equipe_origem_id': str(equipe_origem.id),
            'equipe_origem_nome': equipe_origem.nome,
            'equipe_destino_id': str(equipe_destino.id),
            'equipe_destino_nome': equipe_destino.nome,
            'valor_enviado': valor,
            'taxa': taxa,
            'taxa_percentual': taxa_bancaria,
            'valor_recebido': valor_recebido,
            'timestamp': timestamp,
            'status': 'concluido'
        }
        
        # Salvar transferência em arquivo
        pasta_transferencias = "data/transferencias"
        if not os.path.exists(pasta_transferencias):
            os.makedirs(pasta_transferencias)
        
        caminho_transferencia = os.path.join(pasta_transferencias, f"transf_{transferencia_id}.json")
        with open(caminho_transferencia, 'w', encoding='utf-8') as f:
            json.dump(transferencia_info, f, ensure_ascii=False, indent=2)
        
        # Salvar equipes atualizadas
        api.db.salvar_equipe(equipe_origem)
        api.db.salvar_equipe(equipe_destino)
        
        print(f"[TRANSFERÊNCIA] {equipe_origem.nome} → {equipe_destino.nome}: {valor} (-{taxa})")
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Transferência de {valor} realizada! Taxa: {taxa:.2f}',
            'detalhes': {
                'valor_enviado': valor,
                'taxa': taxa,
                'valor_recebido': valor_recebido,
                'saldo_novo': equipe_origem.doricoins
            }
        })
    
    except ValueError as e:
        return jsonify({'erro': 'Valores inválidos'}), 400
    except Exception as e:
        print(f"[ERRO TRANSFERÊNCIA] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': f'Erro ao processar transferência: {str(e)}'}), 500

@app.route('/api/taxa-transferencia', methods=['GET'])
@requer_login_api
def obter_taxa_transferencia():
    """Retorna a taxa de transferência configurada (para preview no frontend)"""
    taxa = float(api.db.obter_configuracao('taxa_transferencia') or '10')
    return jsonify({'taxa': taxa})

@app.route('/api/transferencias/historico', methods=['GET'])
@requer_login_api
def historico_transferencias():
    """Retorna histórico de transferências da equipe (enviadas e recebidas)"""
    equipe_id = obter_equipe_id_request()
    if not equipe_id:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    try:
        historico = []
        pasta_transferencias = "data/transferencias"
        
        if os.path.exists(pasta_transferencias):
            for arquivo in os.listdir(pasta_transferencias):
                if arquivo.startswith('transf_') and arquivo.endswith('.json'):
                    caminho = os.path.join(pasta_transferencias, arquivo)
                    try:
                        with open(caminho, 'r', encoding='utf-8') as f:
                            transf = json.load(f)
                            
                            # Se é da equipe (origem ou destino)
                            if str(transf.get('equipe_origem_id')) == str(equipe_id):
                                historico.append({
                                    'id': transf.get('id'),
                                    'tipo': 'enviado',  # Para CSS/cor vermelha
                                    'outra_equipe': transf.get('equipe_destino_nome'),
                                    'valor': transf.get('valor_enviado'),
                                    'taxa': transf.get('taxa'),
                                    'taxa_percentual': transf.get('taxa_percentual'),
                                    'timestamp': transf.get('timestamp'),
                                    'status': transf.get('status')
                                })
                            elif str(transf.get('equipe_destino_id')) == str(equipe_id):
                                historico.append({
                                    'id': transf.get('id'),
                                    'tipo': 'recebido',  # Para CSS/cor verde
                                    'outra_equipe': transf.get('equipe_origem_nome'),
                                    'valor': transf.get('valor_recebido'),
                                    'taxa': transf.get('taxa'),
                                    'taxa_percentual': transf.get('taxa_percentual'),
                                    'timestamp': transf.get('timestamp'),
                                    'status': transf.get('status')
                                })
                    except:
                        pass
        
        # Ordenar por data (mais recentes primeiro)
        historico.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify(historico[-50:])  # Retornar últimas 50
    
    except Exception as e:
        print(f"[ERRO HISTÓRICO TRANSFERÊNCIAS] {str(e)}")
        return jsonify({'erro': str(e)}), 400

@app.route('/api/equipes/<equipe_id>/nome', methods=['PUT'])
@requer_admin
def atualizar_nome_equipe(equipe_id):
    """Atualiza o nome da equipe (admin only)"""
    try:
        dados = request.get_json()
        novo_nome = dados.get('nome', '').strip()
        
        if not novo_nome or len(novo_nome) < 2:
            return jsonify({'erro': 'Nome deve ter pelo menos 2 caracteres'}), 400
        
        if len(novo_nome) > 50:
            return jsonify({'erro': 'Nome não pode ter mais de 50 caracteres'}), 400
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'erro': 'Equipe não encontrada'}), 404
        
        # Atualizar nome
        equipe.nome = novo_nome
        api.db.salvar_equipe(equipe)
        
        return jsonify({
            'sucesso': True,
            'nome': equipe.nome
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ========== ENDPOINTS DE PILOTOS E EQUIPES ==========

@app.route('/api/equipes/<equipe_id>/gerar-codigo-convite', methods=['POST'])
@requer_login_api
def gerar_codigo_convite(equipe_id):
    """Gera um código de convite para pilotos se vincularem"""
    try:
        equipe_id_session = session.get('equipe_id')
        
        # Verificar se o usuário é dono da equipe
        if equipe_id_session != equipe_id:
            return jsonify({'erro': 'Apenas donos podem gerar códigos para sua equipe'}), 403
        
        equipe = api.db.carregar_equipe(equipe_id)
        if not equipe:
            return jsonify({'erro': 'Equipe não encontrada'}), 404
        
        resultado = api.db.gerar_codigo_convite(equipe_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[API] Erro ao gerar código: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/pilotos/vincular-equipe', methods=['POST'])
@requer_login_api
def vincular_piloto_equipe():
    """Vincula um piloto a uma equipe usando código de convite"""
    try:
        piloto_id = session.get('piloto_id')
        if not piloto_id:
            return jsonify({'erro': 'Piloto não autenticado'}), 401
            
        dados = request.get_json()
        codigo_convite = dados.get('codigo', '').strip().upper()
        
        if not codigo_convite:
            return jsonify({'erro': 'Código de convite é obrigatório'}), 400
        
        resultado = api.db.vincular_piloto_a_equipe(piloto_id, codigo_convite)
        return jsonify(resultado)
    except Exception as e:
        print(f"[API] Erro ao vincular piloto: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/pilotos/minhas-equipes', methods=['GET'])
@requer_login_api
def listar_minhas_equipes():
    """Lista as equipes vinculadas ao piloto logado"""
    try:
        piloto_id = session.get('piloto_id')
        if not piloto_id:
            return jsonify({'erro': 'Piloto não autenticado'}), 401
            
        resultado = api.db.listar_equipes_do_piloto(piloto_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[API] Erro ao listar equipes: {e}")
        return jsonify({'sucesso': False, 'erro': str(e), 'equipes': []}), 500

@app.route('/api/pilotos/<piloto_id>/candidatura-etapa/<etapa_id>', methods=['GET'])
def obter_candidatura_piloto_etapa(piloto_id, etapa_id):
    """Retorna a candidatura atual do piloto para uma etapa (se houver)"""
    try:
        candidatura = api.db.obter_candidatura_piloto_etapa(piloto_id, etapa_id)
        return jsonify({'candidatura': candidatura})
    except Exception as e:
        print(f"[API] Erro ao obter candidatura: {e}")
        return jsonify({'candidatura': None, 'erro': str(e)})

@app.route('/api/equipes/<equipe_id>/pilotos', methods=['GET'])
@requer_login_api
def listar_pilotos_equipe(equipe_id):
    """Lista os pilotos vinculados a uma equipe"""
    try:
        resultado = api.db.listar_pilotos_da_equipe(equipe_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[API] Erro ao listar pilotos: {e}")
        return jsonify({'sucesso': False, 'erro': str(e), 'pilotos': []}), 500

@app.route('/api/pilotos/<piloto_id>/desvincular-equipe/<equipe_id>', methods=['DELETE'])
@requer_login_api
def desvincular_piloto_equipe(piloto_id, equipe_id):
    """Remove o vínculo entre piloto e equipe"""
    try:
        piloto_id_session = session.get('piloto_id')
        
        # Apenas o piloto ou admin podem desvincular
        if piloto_id_session != piloto_id:
            return jsonify({'erro': 'Sem permissão'}), 403
        
        resultado = api.db.desincular_piloto_de_equipe(piloto_id, equipe_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[API] Erro ao desvinc ular: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/status')
def get_status():
    """Retorna status do sistema"""
    return jsonify({
        'sistema': 'online',
        'equipes': len(api.listar_todas_equipes())
    })

@app.route('/api/debug/rotas')
def debug_rotas():
    """Debug: lista todas as rotas registradas"""
    rotas = []
    for rule in app.url_map.iter_rules():
        if 'etapas' in rule.rule or 'pilotos' in rule.rule:
            rotas.append({
                'rota': rule.rule,
                'metodos': list(rule.methods),
                'funcao': rule.endpoint
            })
    return jsonify({'rotas': rotas})

# ============ ROTAS ADMIN =============

@app.route('/api/admin/status')
def admin_status():
    """Status geral do sistema"""
    equipes = api.listar_todas_equipes()
    return jsonify({
        'total_equipes': len(equipes),
        'saldo_total': sum(float(eq.doricoins) for eq in equipes),
        'etapa_atual': getattr(api, 'etapa_atual', 1)
    })

@app.route('/api/admin/equipes')
def admin_equipes():
    """Listar equipes para admin"""
    try:
        equipes = api.listar_todas_equipes()
        dados = []
        for eq in equipes:
            carro_info = "Sem carro"
            if eq.carro and hasattr(eq.carro, 'marca') and hasattr(eq.carro, 'modelo'):
                carro_info = f"{eq.carro.marca} {eq.carro.modelo}"
            dados.append({
                'id': eq.id,
                'nome': eq.nome,
                'serie': getattr(eq, 'serie', 'A'),
                'saldo': eq.doricoins,
                'carro': carro_info
            })
        return jsonify(dados)
    except Exception as e:
        print(f"[ERRO ADMIN EQUIPES] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/carros-disponiveis')
def carros_disponiveis():
    """Listar todos os modelos de carros disponíveis para atribuir a uma equipe"""
    try:
        print("[CARROS DISPONIVEIS] Iniciando...")
        # Retornar modelos da loja
        modelos = api.db.carregar_modelos_loja()
        print(f"[CARROS DISPONIVEIS] Total de modelos carregados: {len(modelos)}")
        
        carros_lista = []
        if modelos:
            for modelo in modelos:
                try:
                    print(f"[CARROS DISPONIVEIS] Processando modelo: {modelo.marca} {modelo.modelo}")
                    carros_lista.append({
                        'id': modelo.id,
                        'marca': modelo.marca,
                        'modelo': modelo.modelo,
                        'preco': float(modelo.preco) if modelo.preco else 0,
                        'classe': getattr(modelo, 'classe', 'N/A')
                    })
                except Exception as e_modelo:
                    print(f"[CARROS DISPONIVEIS] Erro ao processar modelo: {e_modelo}")
        
        print(f"[CARROS DISPONIVEIS] Retornando {len(carros_lista)} modelos")
        return jsonify(carros_lista)
    except Exception as e:
        print(f"[ERRO CARROS DISPONIVEIS] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/cadastrar-equipe', methods=['POST'])
def cadastrar_equipe():
    """Cadastrar nova equipe no sistema"""
    dados = request.json
    try:
        nome = dados.get('nome', 'Equipe Sem Nome')
        doricoins = float(dados.get('doricoins', 10000))
        senha = dados.get('senha', '123456')
        serie = dados.get('serie', 'A')  # Série A ou B - padrão A
        carro_id = dados.get('carro_id')
        if isinstance(carro_id, str):
            carro_id = carro_id.strip() or None
        if not carro_id:
            carro_id = None
        
        # Validar série
        if serie not in ['A', 'B']:
            serie = 'A'
        
        print(f"[CADASTRO EQUIPE] Nome: {nome}, Doricoins: {doricoins}, Série: {serie}, Carro ID: {carro_id!r}")
        
        # Criar equipe via API com a senha e série fornecidas
        equipe = api.criar_equipe_novo(nome=nome, doricoins_iniciais=doricoins, senha=senha, serie=serie)
        print(f"[CADASTRO EQUIPE] Equipe criada: {equipe.id}, Série: {equipe.serie}")
        
        # Atribuir carro se foi selecionado um modelo
        if carro_id:
            print(f"[CADASTRO EQUIPE] Procurando modelo com ID: {carro_id}")
            # Carregar o modelo (template)
            modelos = api.db.carregar_modelos_loja()
            print(f"[CADASTRO EQUIPE] Total de modelos: {len(modelos)}")
            
            modelo_encontrado = None
            for mod in modelos:
                print(f"[CADASTRO EQUIPE] Verificando modelo: {mod.marca} {mod.modelo}, ID: {mod.id}")
                if mod.id == carro_id:
                    modelo_encontrado = mod
                    break
            
            if modelo_encontrado:
                print(f"[CADASTRO EQUIPE] Modelo encontrado: {modelo_encontrado.marca} {modelo_encontrado.modelo}")
                # Próximo numero_carro disponível (coluna é UNIQUE na tabela carros)
                try:
                    conn = api.db._get_conn()
                    cur = conn.cursor()
                    cur.execute('SELECT COALESCE(MAX(numero_carro), 0) + 1 FROM carros')
                    prox_num = cur.fetchone()[0]
                    conn.close()
                except Exception:
                    prox_num = 1
                # Criar uma instância do modelo para a equipe
                # Criar peças padrão com coeficiente de quebra
                motor = Peca(
                    id=str(uuid.uuid4()),
                    nome="Motor Padrão",
                    tipo="motor",
                    durabilidade_maxima=100.0,
                    preco=0,
                    coeficiente_quebra=0.35
                )
                
                cambio = Peca(
                    id=str(uuid.uuid4()),
                    nome="Câmbio Padrão",
                    tipo="cambio",
                    durabilidade_maxima=100.0,
                    preco=0,
                    coeficiente_quebra=0.4
                )
                
                kit_angulo = Peca(
                    id=str(uuid.uuid4()),
                    nome="Kit Ângulo Padrão",
                    tipo="kit_angulo",
                    durabilidade_maxima=100.0,
                    preco=0,
                    coeficiente_quebra=0.3
                )
                
                suspensao = Peca(
                    id=str(uuid.uuid4()),
                    nome="Suspensão Padrão",
                    tipo="suspensao",
                    durabilidade_maxima=100.0,
                    preco=0,
                    coeficiente_quebra=0.45
                )
                
                # Criar carro instance (numero_carro deve ser único na tabela)
                carro_novo = Carro(
                    id=str(uuid.uuid4()),
                    numero_carro=prox_num,
                    marca=modelo_encontrado.marca,
                    modelo=modelo_encontrado.modelo,
                    motor=motor,
                    cambio=cambio,
                    kit_angulo=kit_angulo,
                    suspensao=suspensao,
                    diferenciais=[],
                    pecas_instaladas=[]
                )
                carro_novo.modelo_id = modelo_encontrado.id  # FK carros.modelo_id -> modelos_carro_loja.id
                print(f"[CADASTRO EQUIPE] Carro criado: {carro_novo.id}, modelo_id={carro_novo.modelo_id}")
                
                # Salvar o carro no banco (numero_carro único; falha se ex.: duplicado)
                ok_carro = api.db.salvar_carro(carro_novo, equipe.id)
                if not ok_carro:
                    err = getattr(api.db, '_ultimo_erro_carro', None) or 'Falha ao gravar carro no banco (verifique logs)'
                    print(f"[CADASTRO EQUIPE] ERRO: salvar_carro retornou False: {err}")
                    return jsonify({'sucesso': False, 'erro': str(err)}), 500
                print(f"[CADASTRO EQUIPE] Carro salvo no banco")
                
                # Associar à equipe
                equipe.carro = carro_novo
                equipe.carros = [carro_novo]
                print(f"[CADASTRO EQUIPE] Equipe associada ao carro")
            else:
                print(f"[CADASTRO EQUIPE] Modelo não encontrado!")
                return jsonify({'sucesso': False, 'erro': 'Modelo de carro não encontrado'}), 400
        
        api.db.salvar_equipe(equipe)
        # Garantir que equipes.carro_id fica persistido (UPDATE explícito)
        if equipe.carro:
            try:
                conn = api.db._get_conn()
                cur = conn.cursor()
                cur.execute('UPDATE equipes SET carro_id = %s WHERE id = %s', (equipe.carro.id, equipe.id))
                conn.commit()
                conn.close()
                print(f"[CADASTRO EQUIPE] equipes.carro_id atualizado para {equipe.carro.id}")
            except Exception as ex:
                print(f"[CADASTRO EQUIPE] Aviso ao atualizar carro_id: {ex}")
        print(f"[CADASTRO EQUIPE] Equipe salva no banco")
        
        resp_equipe = {
            'id': equipe.id,
            'nome': equipe.nome,
            'doricoins': equipe.doricoins,
            'senha': senha,
            'carro_id': carro_id
        }
        if getattr(equipe, 'carro', None) and getattr(equipe.carro, 'id', None):
            resp_equipe['carro_instancia_id'] = equipe.carro.id
        return jsonify({
            'sucesso': True,
            'mensagem': f'Equipe {nome} criada com sucesso',
            'equipe': resp_equipe
        })
    except Exception as e:
        print(f"[ERRO CADASTRO EQUIPE] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/deletar-equipe', methods=['POST'])
def deletar_equipe_admin():
    """Deletar uma equipe do sistema"""
    dados = request.json
    try:
        equipe_id = dados.get('id')
        
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'ID da equipe não fornecido'}), 400
        
        # Obter equipe para logging
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404
        
        nome_equipe = equipe.nome
        
        # Deletar equipe via API
        sucesso = api.apagar_equipe(equipe_id)
        
        if sucesso:
            print(f"[EQUIPE DELETADA] {nome_equipe} (ID: {equipe_id})")
            return jsonify({
                'sucesso': True,
                'mensagem': f'Equipe {nome_equipe} deletada com sucesso'
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Erro ao deletar equipe'
            }), 400
    except Exception as e:
        print(f"[ERRO DELETAR EQUIPE] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/editar-equipe', methods=['POST'])
def editar_equipe_admin():
    """Editar dados de uma equipe (nome, doricoins, série)"""
    dados = request.json
    try:
        equipe_id = dados.get('id')
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'ID da equipe não fornecido'}), 400

        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404

        if 'nome' in dados and dados['nome'] is not None:
            novo_nome = str(dados['nome']).strip()
            if len(novo_nome) >= 2:
                equipe.nome = novo_nome
            else:
                return jsonify({'sucesso': False, 'erro': 'Nome deve ter pelo menos 2 caracteres'}), 400

        if 'doricoins' in dados and dados['doricoins'] is not None:
            try:
                equipe.doricoins = float(dados['doricoins'])
                if equipe.doricoins < 0:
                    equipe.doricoins = 0
            except (TypeError, ValueError):
                return jsonify({'sucesso': False, 'erro': 'Saldo inválido'}), 400

        if 'serie' in dados and dados['serie'] is not None:
            serie = str(dados['serie']).upper().strip()
            if serie in ('A', 'B'):
                equipe.serie = serie
            else:
                return jsonify({'sucesso': False, 'erro': 'Série deve ser A ou B'}), 400

        api.db.salvar_equipe(equipe)
        return jsonify({
            'sucesso': True,
            'mensagem': f'Equipe {equipe.nome} atualizada com sucesso',
            'equipe': {'id': equipe.id, 'nome': equipe.nome, 'doricoins': equipe.doricoins, 'serie': getattr(equipe, 'serie', 'A')}
        })
    except Exception as e:
        print(f"[ERRO EDITAR EQUIPE] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/carros')
def listar_carros_admin():
    """Listar todos os modelos de carros da loja para edição"""
    try:
        modelos = []
        
        # Recarregar modelos do banco para garantir sincronização
        modelos_db = api.db.carregar_modelos_loja()
        if modelos_db:
            api.loja_carros.modelos = modelos_db
        
        # Retornar apenas os modelos da loja, não carros de equipes (com variacoes para cada modelo)
        if api.loja_carros and hasattr(api.loja_carros, 'modelos'):
            for modelo in api.loja_carros.modelos:
                variacoes_list = []
                for variacao in getattr(modelo, 'variacoes', []):
                    # Resolver nomes das peças (1 motor, 1 câmbio, 1 suspensão, 1 kit ângulo, 1 diferencial por variação)
                    motor_nome = None
                    if variacao.motor_id:
                        p = api.db.buscar_peca_loja_por_id(variacao.motor_id)
                        motor_nome = p.nome if p else None
                    cambio_nome = None
                    if variacao.cambio_id:
                        p = api.db.buscar_peca_loja_por_id(variacao.cambio_id)
                        cambio_nome = p.nome if p else None
                    suspensao_nome = None
                    if variacao.suspensao_id:
                        p = api.db.buscar_peca_loja_por_id(variacao.suspensao_id)
                        suspensao_nome = p.nome if p else None
                    kit_angulo_nome = None
                    if variacao.kit_angulo_id:
                        p = api.db.buscar_peca_loja_por_id(variacao.kit_angulo_id)
                        kit_angulo_nome = p.nome if p else None
                    diferencial_nome = None
                    if variacao.diferencial_id:
                        p = api.db.buscar_peca_loja_por_id(variacao.diferencial_id)
                        diferencial_nome = p.nome if p else None
                    variacoes_list.append({
                        'id': variacao.id,
                        'modelo_carro_loja_id': variacao.modelo_carro_loja_id,
                        'valor': getattr(variacao, 'valor', 0.0),
                        'motor_id': variacao.motor_id,
                        'cambio_id': variacao.cambio_id,
                        'suspensao_id': variacao.suspensao_id,
                        'kit_angulo_id': variacao.kit_angulo_id,
                        'diferencial_id': variacao.diferencial_id,
                        'motor_nome': motor_nome,
                        'cambio_nome': cambio_nome,
                        'suspensao_nome': suspensao_nome,
                        'kit_angulo_nome': kit_angulo_nome,
                        'diferencial_nome': diferencial_nome,
                    })
                modelos.append({
                    'id': modelo.id,
                    'marca': modelo.marca,
                    'modelo': modelo.modelo,
                    'classe': modelo.classe,
                    'preco': modelo.preco,
                    'descricao': getattr(modelo, 'descricao', ''),
                    'variacoes': variacoes_list,
                    'imagem': getattr(modelo, 'imagem', None),
                    'tem_imagem': bool(getattr(modelo, 'imagem', None))
                })
                
                imagem_attr = getattr(modelo, 'imagem', None)
                if imagem_attr:
                    print(f"[DEBUG IMAGEM] {modelo.modelo}: Tem imagem, tipo={type(imagem_attr).__name__}, tamanho={len(imagem_attr) if isinstance(imagem_attr, (str, bytes)) else 'N/A'}")
                else:
                    print(f"[DEBUG IMAGEM] {modelo.modelo}: SEM IMAGEM")
        
        print(f"[ADMIN] Retornando {len(modelos)} modelos de carros")
        return jsonify(modelos)
    except Exception as e:
        print(f"Erro ao listar carros: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 400

@app.route('/api/admin/pecas')
def listar_pecas_admin():
    """Listar todas as peças da loja"""
    try:
        pecas = []
        if api.loja_pecas and hasattr(api.loja_pecas, 'pecas'):
            for peca in api.loja_pecas.pecas:
                peca_data = {
                    'id': peca.id,
                    'nome': peca.nome,
                    'tipo': peca.tipo,
                    'preco': peca.preco,
                    'durabilidade': peca.durabilidade,
                    'coeficiente_quebra': peca.coeficiente_quebra,
                    'compatibilidade': getattr(peca, 'compatibilidade', 'universal'),
                    'imagem': getattr(peca, 'imagem', None),  # Incluir base64 da imagem
                    'tem_imagem': bool(getattr(peca, 'imagem', None))
                }
                pecas.append(peca_data)
        return jsonify(pecas)
    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@app.route('/api/peca/<peca_id>/imagem')
def obter_imagem_peca(peca_id):
    """Obter imagem em base64 de uma peça"""
    try:
        # Buscar no banco de dados
        conn = api.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT imagem FROM pecas_loja WHERE id = %s', (peca_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return jsonify({'imagem': None}), 200
        
        return jsonify({'imagem': row[0]}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@app.route('/api/carro/<carro_id>/imagem')
def obter_imagem_carro(carro_id):
    """Obter imagem em base64 de um carro"""
    try:
        # Buscar no banco de dados
        conn = api.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT imagem FROM modelos_carro_loja WHERE id = %s', (carro_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return jsonify({'imagem': None}), 200
        
        return jsonify({'imagem': row[0]}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/cadastrar-carro', methods=['POST'])
def cadastrar_carro():
    """Cadastrar novo carro na loja"""
    dados = request.json
    print(f"[CADASTRO CARRO] Dados recebidos (sem imagem para brevidade)")
    try:
        marca = str(dados.get('marca', 'Genérica')).strip()
        modelo = str(dados.get('modelo', 'Modelo')).strip()
        preco_str = dados.get('preco', '0')
        imagem_base64 = dados.get('imagem')  # Receber imagem em base64
        
        # Validar preço
        if not preco_str or preco_str == '':
            return jsonify({'sucesso': False, 'erro': 'Preço é obrigatório'}), 400
        
        preco = float(preco_str)
        classe = str(dados.get('classe', 'basico')).strip()
        descricao = str(dados.get('descricao', f'{marca} {modelo}')).strip()
        
        print(f"[CADASTRO CARRO] Marca: {marca}, Modelo: {modelo}, Preço: {preco}")
        if imagem_base64:
            print(f"[CADASTRO CARRO] Imagem: Recebida, tipo={type(imagem_base64).__name__}, tamanho={len(imagem_base64)}")
            print(f"[CADASTRO CARRO] Preview (primeiros 100 chars): {imagem_base64[:100]}")
        else:
            print(f"[CADASTRO CARRO] Imagem: Não recebida")
        
        # Validar marca e modelo
        if not marca or marca == '':
            return jsonify({'sucesso': False, 'erro': 'Marca é obrigatória'}), 400
        if not modelo or modelo == '':
            return jsonify({'sucesso': False, 'erro': 'Modelo é obrigatório'}), 400
        
        # Cadastrar carro via API (SEM peças - serão adicionadas via variações)
        novo_modelo = api.loja_carros.adicionar_modelo(
            marca=marca,
            modelo=modelo,
            classe=classe,
            preco=preco,
            descricao=descricao
        )
        
        print(f"[CADASTRO CARRO] Modelo criado: {novo_modelo.id}")
        
        # Atualizar o valor da variação V1 padrão que foi criada automaticamente
        if novo_modelo.variacoes and len(novo_modelo.variacoes) > 0:
            novo_modelo.variacoes[0].valor = preco
            print(f"[CADASTRO CARRO] Variação V1 atualizada com valor: R${preco}")
        
        # Salvar no banco com imagem
        if imagem_base64:
            print(f"[CADASTRO CARRO] Salvando imagem: tipo={type(imagem_base64).__name__}, tamanho={len(imagem_base64)}")
        salvo = api.db.salvar_modelo_loja(novo_modelo, imagem_base64=imagem_base64)
        print(f"[CADASTRO CARRO] Salvo no banco: {salvo}")
        
        if not salvo:
            return jsonify({'sucesso': False, 'erro': 'Erro ao salvar no banco'}), 400
        
        # Recarregar modelos na API
        modelos_db = api.db.carregar_modelos_loja()
        if modelos_db:
            api.loja_carros.modelos = modelos_db
            print(f"[CADASTRO CARRO] Modelos recarregados: {len(modelos_db)} modelos")
        
        # Preparar imagem para retorno
        imagem_retorno = imagem_base64
        if imagem_base64 and isinstance(imagem_base64, str) and not imagem_base64.startswith('data:image'):
            imagem_retorno = 'data:image/jpeg;base64,' + imagem_base64
        
        return jsonify({
            'sucesso': True, 
            'mensagem': f'Carro {marca} {modelo} cadastrado com sucesso',
            'carro': {
                'id': novo_modelo.id,
                'marca': novo_modelo.marca,
                'modelo': novo_modelo.modelo,
                'preco': novo_modelo.preco,
                'imagem': imagem_retorno,  # Incluir imagem na resposta
                'tem_imagem': bool(imagem_base64)
            }
        })
    except ValueError as e:
        print(f"[ERRO CADASTRO CARRO] Erro de valor: {str(e)}")
        return jsonify({'sucesso': False, 'erro': f'Dados inválidos: {str(e)}'}), 400
    except Exception as e:
        print(f"[ERRO CADASTRO CARRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/cadastrar-variacao', methods=['POST'])
def cadastrar_variacao():
    """Cadastrar nova variação de carro"""
    dados = request.json
    print(f"[CADASTRO VARIAÇÃO] Dados recebidos")
    try:
        modelo_id = dados.get('modelo_carro_loja_id')
        motor_id = dados.get('motor_id')
        cambio_id = dados.get('cambio_id')
        suspensao_id = dados.get('suspensao_id')
        kit_angulo_id = dados.get('kit_angulo_id')
        diferencial_id = dados.get('diferencial_id')
        valor = dados.get('valor', 0.0)  # Novo parâmetro de valor
        
        if not modelo_id:
            return jsonify({'sucesso': False, 'erro': 'Modelo de carro não fornecido'}), 400
        
        # Validar que o modelo existe
        modelo = api.loja_carros.obter_modelo(modelo_id)
        if not modelo:
            return jsonify({'sucesso': False, 'erro': 'Modelo de carro não encontrado'}), 404
        
        print(f"[CADASTRO VARIAÇÃO] Modelo: {modelo.marca} {modelo.modelo}")
        print(f"[CADASTRO VARIAÇÃO] Motor: {motor_id}, Câmbio: {cambio_id}, Valor: {valor}")
        
        # Validar IDs de peças
        def validar_id_peca(peca_id, tipo_peca):
            if peca_id:
                peca = api.db.buscar_peca_loja_por_id(peca_id)
                if not peca:
                    return False, f"{tipo_peca} com ID {peca_id} não existe"
            return True, None
        
        # Validar todas as peças
        for peca_id, tipo in [(motor_id, "Motor"), (cambio_id, "Câmbio"), 
                              (suspensao_id, "Suspensão"), (kit_angulo_id, "Kit Ângulo"),
                              (diferencial_id, "Diferencial")]:
            if peca_id:
                valido, erro = validar_id_peca(peca_id, tipo)
                if not valido:
                    return jsonify({'sucesso': False, 'erro': erro}), 400
        
        # Adicionar variação usando o método da API
        resultado = api.loja_carros.adicionar_variacao(
            modelo_id=modelo_id,
            motor_id=motor_id,
            cambio_id=cambio_id,
            suspensao_id=suspensao_id,
            kit_angulo_id=kit_angulo_id,
            diferencial_id=diferencial_id,
            valor=valor  # Passar o valor da variação
        )
        
        if resultado:
            print(f"[CADASTRO VARIAÇÃO] Variação adicionada com sucesso")
            
            # Salvar o modelo no banco de dados (persiste a nova variação)
            salvo = api.db.salvar_modelo_loja(modelo)
            if salvo:
                print(f"[CADASTRO VARIAÇÃO] Modelo salvo no banco com a nova variação")
                
                # Recarregar modelos para sincronizar em memória
                modelos_db = api.db.carregar_modelos_loja()
                if modelos_db:
                    api.loja_carros.modelos = modelos_db
                    print(f"[CADASTRO VARIAÇÃO] Modelos recarregados do banco")
                
                return jsonify({
                    'sucesso': True,
                    'mensagem': 'Variação cadastrada com sucesso'
                })
            else:
                return jsonify({'sucesso': False, 'erro': 'Erro ao salvar variação no banco'}), 400
        else:
            return jsonify({'sucesso': False, 'erro': 'Erro ao cadastrar variação'}), 400
    
    except Exception as e:
        print(f"[ERRO CADASTRO VARIAÇÃO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/editar-variacao', methods=['POST'])
def editar_variacao():
    """Editar uma variação de carro existente"""
    dados = request.json
    print(f"[EDITAR VARIAÇÃO] Dados recebidos")
    try:
        variacao_id = dados.get('variacao_id')
        modelo_id = dados.get('modelo_carro_loja_id')
        motor_id = dados.get('motor_id')
        cambio_id = dados.get('cambio_id')
        suspensao_id = dados.get('suspensao_id')
        kit_angulo_id = dados.get('kit_angulo_id')
        diferencial_id = dados.get('diferencial_id')
        valor = dados.get('valor', 0.0)
        
        if not variacao_id or not modelo_id:
            return jsonify({'sucesso': False, 'erro': 'Variação ou modelo não fornecidos'}), 400
        
        print(f"[EDITAR VARIAÇÃO] Variação: {variacao_id}, Modelo: {modelo_id}")
        
        # Validar IDs de peças
        def validar_id_peca(peca_id, tipo_peca):
            if peca_id:
                peca = api.db.buscar_peca_loja_por_id(peca_id)
                if not peca:
                    return False, f"{tipo_peca} com ID {peca_id} não existe"
            return True, None
        
        # Validar todas as peças
        for peca_id, tipo in [(motor_id, "Motor"), (cambio_id, "Câmbio"), 
                              (suspensao_id, "Suspensão"), (kit_angulo_id, "Kit Ângulo"),
                              (diferencial_id, "Diferencial")]:
            if peca_id:
                valido, erro = validar_id_peca(peca_id, tipo)
                if not valido:
                    return jsonify({'sucesso': False, 'erro': erro}), 400
        
        # Buscar e atualizar a variação no banco de dados
        conn = api.db._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE variacoes_carros
            SET motor_id = %s, cambio_id = %s, suspensao_id = %s,
                kit_angulo_id = %s, diferencial_id = %s, valor = %s
            WHERE id = %s
        ''', (motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id, valor, variacao_id))
        
        conn.commit()
        conn.close()
        
        print(f"[EDITAR VARIAÇÃO] Variação atualizada no banco")
        
        # Recarregar modelos para sincronizar em memória
        modelos_db = api.db.carregar_modelos_loja()
        if modelos_db:
            api.loja_carros.modelos = modelos_db
            print(f"[EDITAR VARIAÇÃO] Modelos recarregados do banco")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Variação editada com sucesso'
        })
    
    except Exception as e:
        print(f"[ERRO EDITAR VARIAÇÃO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/editar-carro', methods=['POST'])
def editar_carro():
    """Editar um carro existente"""
    dados = request.json
    try:
        carro_id = dados.get('id')
        marca = dados.get('marca')
        modelo = dados.get('modelo')
        preco = dados.get('preco')
        imagem_base64 = dados.get('imagem')
        
        if not carro_id:
            return jsonify({'sucesso': False, 'erro': 'ID do carro não fornecido'}), 400
        
        # Validar preco
        if preco is None or preco == '' or str(preco).lower() == 'nan':
            return jsonify({'sucesso': False, 'erro': 'Preço inválido'}), 400
        
        # Editar carro via loja_carros (apenas marca, modelo, preco)
        sucesso = api.loja_carros.editar_modelo(
            modelo_id=carro_id,
            marca=marca,
            modelo=modelo,
            preco=float(preco) if preco else None
        )
        
        if sucesso:
            # Salvar no banco e propagar preço para variações
            carro = None
            for c in api.loja_carros.modelos:
                if c.id == carro_id:
                    carro = c
                    break
            if carro:
                preco_novo = float(preco) if preco else carro.preco
                # Atualizar valor das variações para refletir o novo preço (loja e variações)
                for v in getattr(carro, 'variacoes', []):
                    v.valor = preco_novo
                api.db.salvar_modelo_loja(carro, imagem_base64=imagem_base64)
                # Propagar marca e modelo para carros que usam este modelo
                api.db.propagar_modelo_para_carros(carro_id, marca, modelo)
                # Recarregar do banco para garantir sincronização
                modelos_db = api.db.carregar_modelos_loja()
                if modelos_db:
                    api.loja_carros.modelos = modelos_db
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'Carro {marca} {modelo} atualizado com sucesso'
            })
        else:
            return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 400
            
    except Exception as e:
        print(f"[ERRO EDITAR CARRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/deletar-carro', methods=['POST'])
def deletar_carro():
    """Deletar um carro"""
    dados = request.json
    try:
        carro_id = dados.get('id')
        
        if not carro_id:
            return jsonify({'sucesso': False, 'erro': 'ID do carro não fornecido'}), 400
        
        # Deletar carro via loja_carros
        sucesso = api.loja_carros.deletar_modelo(carro_id)
        
        if sucesso:
            # Remover do banco também
            api.db.deletar_modelo_loja(carro_id)
            # Recarregar do banco para garantir sincronização
            modelos_db = api.db.carregar_modelos_loja()
            if modelos_db:
                api.loja_carros.modelos = modelos_db
            
            return jsonify({
                'sucesso': True,
                'mensagem': 'Carro deletado com sucesso'
            })
        else:
            return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 400
            
    except Exception as e:
        print(f"[ERRO DELETAR CARRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/cadastrar-peca', methods=['POST'])
def cadastrar_peca():
    """Cadastrar nova peça na loja"""
    dados = request.json
    try:
        import json as json_module
        
        nome = dados.get('nome', 'Peça')
        tipo = dados.get('tipo', 'motor')
        preco_str = dados.get('preco', '0')
        preco = float(preco_str) if preco_str else 0.0
        durabilidade_str = dados.get('durabilidade', '100.0')
        durabilidade = float(durabilidade_str) if durabilidade_str else 100.0
        coeficiente_quebra_str = dados.get('coeficiente_quebra', '1.0')
        coeficiente_quebra = float(coeficiente_quebra_str) if coeficiente_quebra_str else 1.0
        
        # Aceitar compatibilidade como array ou string
        compatibilidade_raw = dados.get('compatibilidade', 'universal')
        if isinstance(compatibilidade_raw, list):
            compatibilidades = compatibilidade_raw if compatibilidade_raw else ['universal']
        else:
            compatibilidades = [compatibilidade_raw] if compatibilidade_raw else ['universal']
        
        # Converter para JSON
        compatibilidade_json = json_module.dumps({"compatibilidades": compatibilidades})
        
        imagem_base64 = dados.get('imagem')  # Receber imagem em base64
        
        print(f"\n[CADASTRAR PEÇA] Recebido:")
        print(f"  Nome: {nome}")
        print(f"  Tipo: {tipo}")
        print(f"  Compatibilidades: {compatibilidades}")
        print(f"  Imagem: {'Sim' if imagem_base64 else 'Não'}")
        
        # Criar descrição padrão se não fornecida
        descricao = f'{nome} - Tipo: {tipo}'
        
        # Adicionar peça via API
        nova_peca = api.loja_pecas.adicionar_peca(
            nome=nome,
            tipo=tipo,
            preco=preco,
            descricao=descricao,
            compatibilidade=compatibilidade_json,
            durabilidade=durabilidade,
            coeficiente_quebra=coeficiente_quebra
        )
        
        # Salvar no banco com imagem
        sucesso_salvar = api.db.salvar_peca_loja(nova_peca, imagem_base64=imagem_base64)
        print(f"[DEBUG] Salvar peça sucesso: {sucesso_salvar}")
        if not sucesso_salvar:
            raise Exception("Falha ao salvar peça no banco de dados")
        
        print(f"[DEBUG] Peça cadastrada: {nova_peca.id} - {nova_peca.nome}")
        
        # Recarregar peças na API para atualizar a imagem em memória
        pecas_db = api.db.carregar_pecas_loja()
        if pecas_db:
            api.loja_pecas.pecas = pecas_db
            print(f"[CADASTRO PEÇA] Peças recarregadas: {len(pecas_db)} peças")
        
        # Preparar imagem para retorno
        imagem_retorno = imagem_base64
        if imagem_base64 and isinstance(imagem_base64, str) and not imagem_base64.startswith('data:image'):
            imagem_retorno = 'data:image/jpeg;base64,' + imagem_base64
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Peça {nome} cadastrada com sucesso',
            'peca': {
                'id': nova_peca.id,
                'nome': nova_peca.nome,
                'tipo': nova_peca.tipo,
                'preco': nova_peca.preco,
                'imagem': imagem_retorno,  # Incluir imagem na resposta
                'tem_imagem': bool(imagem_base64)
            }
        })
    except Exception as e:
        print(f"[ERRO CADASTRO PEÇA] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/upgrades')
def get_admin_upgrades():
    """Lista upgrades para o painel admin"""
    try:
        upgrades = api.db.carregar_upgrades()
        return jsonify({'upgrades': upgrades})
    except Exception as e:
        return jsonify({'upgrades': [], 'erro': str(e)}), 500

@app.route('/api/admin/cadastrar-upgrade', methods=['POST'])
def cadastrar_upgrade():
    """Cadastra um novo upgrade vinculado a uma peça (com imagem opcional em base64)"""
    dados = request.json
    try:
        peca_loja_id = dados.get('peca_loja_id')
        nome = dados.get('nome', '').strip()
        preco = float(dados.get('preco', 0) or 0)
        descricao = (dados.get('descricao') or '').strip()
        imagem = dados.get('imagem')
        if not peca_loja_id or not nome:
            return jsonify({'sucesso': False, 'erro': 'Informe a peça base e o nome do upgrade'}), 400
        import uuid
        upgrade_id = str(uuid.uuid4())
        if api.db.criar_upgrade(upgrade_id, peca_loja_id, nome, preco, descricao, imagem=imagem):
            return jsonify({'sucesso': True, 'mensagem': f'Upgrade {nome} cadastrado', 'id': upgrade_id})
        return jsonify({'sucesso': False, 'erro': 'Erro ao salvar upgrade'}), 500
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/deletar-upgrade', methods=['POST'])
def deletar_upgrade():
    """Remove um upgrade"""
    dados = request.json
    try:
        upgrade_id = dados.get('id')
        if not upgrade_id:
            return jsonify({'sucesso': False, 'erro': 'ID do upgrade não fornecido'}), 400
        if api.db.deletar_upgrade(upgrade_id):
            return jsonify({'sucesso': True, 'mensagem': 'Upgrade excluído'})
        return jsonify({'sucesso': False, 'erro': 'Erro ao excluir'}), 500
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/reset-pecas-carros', methods=['POST'])
@requer_admin
def reset_pecas_carros():
    """Remove todos os dados das tabelas de peças e carros (loja, peças, carros, upgrades, solicitações)."""
    try:
        resultado = api.db.resetar_pecas_e_carros()
        if resultado.get('sucesso'):
            if hasattr(api, 'loja_pecas') and api.loja_pecas:
                api.loja_pecas.pecas = []
            if hasattr(api, 'loja_carros') and api.loja_carros:
                api.loja_carros.modelos = []
            return jsonify(resultado)
        return jsonify(resultado), 500
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/editar-peca', methods=['POST'])
def editar_peca():
    """Editar uma peça existente"""
    dados = request.json
    try:
        import json as json_module
        
        peca_id = dados.get('id')
        nome = dados.get('nome')
        tipo = dados.get('tipo')
        preco = dados.get('preco')
        durabilidade = dados.get('durabilidade')
        coeficiente_quebra = dados.get('coeficiente_quebra')
        
        # Aceitar compatibilidade como array ou string
        compatibilidade_raw = dados.get('compatibilidade', 'universal')
        if isinstance(compatibilidade_raw, list):
            compatibilidades = compatibilidade_raw if compatibilidade_raw else ['universal']
        else:
            compatibilidades = [compatibilidade_raw] if compatibilidade_raw else ['universal']
        
        # Converter para JSON
        compatibilidade_json = json_module.dumps({"compatibilidades": compatibilidades})
        
        imagem_base64 = dados.get('imagem')
        
        print(f"\n[EDITAR PEÇA] Iniciando edição")
        print(f"[EDITAR PEÇA] ID: {peca_id}")
        print(f"[EDITAR PEÇA] Nome: {nome}")
        print(f"[EDITAR PEÇA] Tipo: {tipo}")
        print(f"[EDITAR PEÇA] Preco: {preco}")
        print(f"[EDITAR PEÇA] Durabilidade: {durabilidade}")
        print(f"[EDITAR PEÇA] Coeficiente: {coeficiente_quebra}")
        print(f"[EDITAR PEÇA] Compatibilidades: {compatibilidades}")
        print(f"[EDITAR PEÇA] Imagem: {'Sim' if imagem_base64 else 'Não'}")
        
        if not peca_id:
            return jsonify({'sucesso': False, 'erro': 'ID da peça não fornecido'}), 400
        
        # Editar peça via loja_pecas
        sucesso = api.loja_pecas.editar_peca(
            peca_id=peca_id,
            nome=nome,
            tipo=tipo,
            preco=float(preco) if preco else None,
            durabilidade=float(durabilidade) if durabilidade else None,
            coeficiente_quebra=float(coeficiente_quebra) if coeficiente_quebra else None,
            compatibilidade=compatibilidade_json
        )
        
        print(f"[EDITAR PEÇA] Retorno de editar_peca: {sucesso}")
        
        if sucesso:
            # Salvar no banco
            peca = api.loja_pecas.obter_peca(peca_id)
            if peca:
                print(f"[EDITAR PEÇA] Peça encontrada: {peca.nome}, compatibilidade: {peca.compatibilidade}")
                api.db.salvar_peca_loja(peca, imagem_base64=imagem_base64)
                # Recarregar do banco para garantir sincronização
                pecas_db = api.db.carregar_pecas_loja()
                if pecas_db:
                    api.loja_pecas.pecas = pecas_db
                    print(f"[EDITAR PEÇA] Peças recarregadas do banco")
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'Peça {nome} atualizada com sucesso'
            })
        else:
            print(f"[EDITAR PEÇA] Peça não encontrada!")
            return jsonify({'sucesso': False, 'erro': 'Peça não encontrada'}), 400
            
    except Exception as e:
        print(f"[ERRO EDITAR PEÇA] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/deletar-peca', methods=['POST'])
def deletar_peca():
    """Deletar uma peça"""
    dados = request.json
    try:
        peca_id = dados.get('id')
        
        if not peca_id:
            return jsonify({'sucesso': False, 'erro': 'ID da peça não fornecido'}), 400
        
        # Deletar peça via loja_pecas
        sucesso = api.loja_pecas.deletar_peca(peca_id)
        
        if sucesso:
            # Remover do banco também
            api.db.deletar_peca_loja(peca_id)
            # Recarregar do banco para garantir sincronização
            pecas_db = api.db.carregar_pecas_loja()
            if pecas_db:
                api.loja_pecas.pecas = pecas_db
            
            return jsonify({
                'sucesso': True,
                'mensagem': 'Peça deletada com sucesso'
            })
        else:
            return jsonify({'sucesso': False, 'erro': 'Peça não encontrada'}), 400
            
    except Exception as e:
        print(f"[ERRO DELETAR PEÇA] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/deletar-imagem-peca', methods=['POST'])
def deletar_imagem_peca():
    """Deletar apenas a imagem de uma peça"""
    dados = request.json
    try:
        peca_id = dados.get('id')
        
        if not peca_id:
            return jsonify({'sucesso': False, 'erro': 'ID da peça não fornecido'}), 400
        
        # Encontrar a peça
        peca = api.loja_pecas.obter_peca(peca_id)
        if not peca:
            return jsonify({'sucesso': False, 'erro': 'Peça não encontrada'}), 400
        
        # Limpar imagem
        peca.imagem = None
        
        # Salvar no banco
        api.db.salvar_peca_loja(peca, imagem_base64=None)
        
        # Recarregar do banco para garantir sincronização
        pecas_db = api.db.carregar_pecas_loja()
        if pecas_db:
            api.loja_pecas.pecas = pecas_db
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Imagem deletada com sucesso'
        })
            
    except Exception as e:
        print(f"[ERRO DELETAR IMAGEM PECA] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/deletar-imagem-carro', methods=['POST'])
def deletar_imagem_carro():
    """Deletar apenas a imagem de um carro"""
    dados = request.json
    try:
        carro_id = dados.get('id')
        
        if not carro_id:
            return jsonify({'sucesso': False, 'erro': 'ID do carro não fornecido'}), 400
        
        # Encontrar o carro
        carro = None
        for c in api.loja_carros.modelos:
            if c.id == carro_id:
                carro = c
                break
        
        if not carro:
            return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 400
        
        # Limpar imagem
        carro.imagem = None
        
        # Salvar no banco
        api.db.salvar_modelo_loja(carro, imagem_base64=None)
        
        # Recarregar do banco para garantir sincronização
        modelos_db = api.db.carregar_modelos_loja()
        if modelos_db:
            api.loja_carros.modelos = modelos_db
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Imagem deletada com sucesso'
        })
            
    except Exception as e:
        print(f"[ERRO DELETAR IMAGEM CARRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/aprovar-solicitacao-ativacao-carro', methods=['POST'])
@requer_admin
def aprovar_solicitacao_ativacao_carro():
    """Aprova uma solicitação de ativação de carro"""
    try:
        dados = request.json
        solicitacao_id = dados.get('solicitacao_id')
        
        if not solicitacao_id:
            return jsonify({'sucesso': False, 'erro': 'ID da solicitação é obrigatório'}), 400
        
        resultado = api.db.aprovar_solicitacao_ativacao_carro(solicitacao_id)
        return jsonify(resultado)
    except Exception as e:
        print(f"[ERRO] Erro ao aprovar solicitação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/equipe/mudar-senha', methods=['POST'])
def mudar_senha_equipe():
    """Mudar a senha de uma equipe"""
    try:
        dados = request.json
        if not dados:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400
            
        equipe_id = dados.get('id')
        nova_senha = dados.get('nova_senha')
        
        if not equipe_id or not nova_senha:
            return jsonify({'sucesso': False, 'erro': 'ID e nova senha são obrigatórios'}), 400
        
        if len(str(nova_senha)) < 4:
            return jsonify({'sucesso': False, 'erro': 'Senha deve ter pelo menos 4 caracteres'}), 400
        
        # Obter equipe
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404
        
        # Mudar a senha (armazenar hash para compatibilidade com login)
        equipe.senha = generate_password_hash(str(nova_senha))
        api.db.salvar_equipe(equipe)
        
        print(f"[SENHA EQUIPE ALTERADA] {equipe.nome} (ID: {equipe_id})")
        return jsonify({
            'sucesso': True,
            'mensagem': f'Senha de {equipe.nome} alterada com sucesso'
        })
    except Exception as e:
        print(f"[ERRO MUDAR SENHA] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

@app.route('/api/admin/solicitacao/<solicitacao_id>')
def obter_solicitacao(solicitacao_id):
    """Obter detalhes de uma solicitação específica com informações do carro do banco"""
    try:
        # Buscar solicitação do banco de dados
        todas_solicitacoes = api.db.executar_query(
            "SELECT * FROM solicitacoes_pecas WHERE id = %s",
            (solicitacao_id,)
        )
        
        if not todas_solicitacoes:
            # Tentar carregar de carros
            todas_solicitacoes = api.db.executar_query(
                "SELECT * FROM solicitacoes_carros WHERE id = %s",
                (solicitacao_id,)
            )
            if not todas_solicitacoes:
                return jsonify({'erro': 'Solicitação não encontrada'}), 404
        
        solicitacao = todas_solicitacoes[0]
        
        # Buscar informações do carro
        carro_id = solicitacao.get('carro_id')
        carro_info = None
        
        if carro_id:
            # Buscar equipe
            equipe_id = solicitacao.get('equipe_id')
            equipe = api.gerenciador.obter_equipe(equipe_id)
            
            if equipe:
                # Procurar o carro na lista de carros da equipe
                for c in equipe.carros:
                    if str(c.id) == str(carro_id):
                        carro_info = {
                            'id': c.id,
                            'numero': c.numero_carro,
                            'marca': c.marca,
                            'modelo': c.modelo,
                            'status': c.status
                        }
                        break
                
                # Se não encontrou, usa o carro principal
                if not carro_info and equipe.carro:
                    carro_info = {
                        'id': equipe.carro.id,
                        'numero': equipe.carro.numero_carro,
                        'marca': equipe.carro.marca,
                        'modelo': equipe.carro.modelo,
                        'status': equipe.carro.status
                    }
        
        return jsonify({
            **solicitacao,
            'carro': carro_info
        })
    
    except Exception as e:
        print(f"[ERRO OBTER SOLICITAÇÃO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/solicitacoes-pecas')
def listar_solicitacoes_pecas():
    """Listar todas as solicitações de compra de peças pendentes do banco de dados"""
    try:
        # Carregar solicitações do banco de dados
        solicitacoes = api.db.carregar_solicitacoes_pecas()
        
        print(f"[SOLICITAÇÕES PECAS] Total carregadas: {len(solicitacoes)}")
        return jsonify(solicitacoes)
    except Exception as e:
        print(f"[ERRO LISTAR SOLICITAÇÕES] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/solicitacoes-carros')
def listar_solicitacoes_carros():
    """Listar todas as solicitações de mudança de carro do banco de dados (apenas carros, com peças de cada carro)"""
    try:
        solicitacoes = api.db.carregar_solicitacoes_carros()
        for sol in solicitacoes:
            carro_id = sol.get('carro_id')
            if not carro_id and sol.get('tipo_carro') and '|' in str(sol.get('tipo_carro', '')):
                carro_id = str(sol['tipo_carro']).split('|')[0]
            sol['pecas'] = api.db.obter_pecas_instaladas_carro(carro_id) if carro_id else []
        print(f"[SOLICITAÇÕES CARROS] Total carregadas: {len(solicitacoes)}")
        return jsonify(solicitacoes)
    except Exception as e:
        print(f"[ERRO LISTAR SOLICITAÇÕES CARROS] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/processar-solicitacao', methods=['POST'])
def processar_solicitacao():
    """Processar (aprovar) uma solicitação de compra de peça ou mudança de carro"""
    dados = request.json
    try:
        solicitacao_id = dados.get('solicitacao_id')
        novo_status = dados.get('status')  # 'instalado', 'guardada', 'reprovado', 'aprovado' (para carros)
        tipo = dados.get('tipo', 'peca')  # 'peca' ou 'carro'
        carro_id_request = dados.get('carro_id')  # Carro selecionado no admin para instalar peça
        
        print(f"\n[PROCESSAR SOLICITAÇÃO] ========== INICIANDO ==========")
        print(f"[PROCESSAR SOLICITAÇÃO] ID: {solicitacao_id}")
        print(f"[PROCESSAR SOLICITAÇÃO] Status: {novo_status}")
        print(f"[PROCESSAR SOLICITAÇÃO] Tipo: {tipo}")
        print(f"[PROCESSAR SOLICITAÇÃO] CarroID Request: '{carro_id_request}' (tipo={type(carro_id_request)}, bool={bool(carro_id_request)})")
        
        print(f"[PROCESSAR SOLICITAÇÃO] Dados validados, continuando...")
        
        # ===== PROCESSAR SOLICITAÇÃO DE CARRO =====
        if tipo == 'carro':
            # Buscar a solicitação de carro
            solicitacoes = api.db.carregar_solicitacoes_carros()
            solicitacao = None
            for sol in solicitacoes:
                if sol['id'] == solicitacao_id:
                    solicitacao = sol
                    break
            
            if not solicitacao:
                return jsonify({'erro': 'Solicitação de carro não encontrada'}), 404
            
            # Atualizar status da solicitação
            sucesso = api.db.atualizar_status_solicitacao_carro(solicitacao_id, novo_status)
            
            if sucesso:
                print(f"[CARRO ATIVADO] Solicitação {solicitacao_id} aprovada")
                return jsonify({
                    'sucesso': True,
                    'mensagem': f'Carro {solicitacao.get("marca", "")} {solicitacao.get("modelo", "")} ativado com sucesso!'
                })
            else:
                return jsonify({'erro': 'Erro ao atualizar status da solicitação de carro'}), 400
        
        # ===== PROCESSAR SOLICITAÇÃO DE PEÇA =====
        else:
            # Buscar a solicitação de peça
            solicitacoes = api.db.carregar_solicitacoes_pecas()
            solicitacao = None
            for sol in solicitacoes:
                if sol['id'] == solicitacao_id:
                    solicitacao = sol
                    break
            
            if not solicitacao:
                return jsonify({'erro': 'Solicitação não encontrada'}), 404
            
            # ===== PROCESSAR INSTALAÇÃO DE PEÇA =====
            if novo_status == 'instalado':
                # Usar carro_id do request se fornecido, senão da solicitação, senão carro ativo da equipe
                carro_id_final = carro_id_request if carro_id_request else solicitacao.get('carro_id')
                if not carro_id_final and solicitacao.get('equipe_id'):
                    try:
                        conn_ac = api.db._get_conn()
                        cur_ac = conn_ac.cursor()
                        cur_ac.execute('''
                            SELECT id FROM carros WHERE equipe_id = %s AND status = %s LIMIT 1
                        ''', (str(solicitacao['equipe_id']), 'ativo'))
                        row_ac = cur_ac.fetchone()
                        conn_ac.close()
                        if row_ac:
                            carro_id_final = row_ac[0]
                    except Exception:
                        pass
                
                print(f"[INSTALAR PEÇA] carro_id_request={carro_id_request}, carro_id_solicitacao={solicitacao.get('carro_id')}, carro_id_final={carro_id_final}")
                
                if not carro_id_final:
                    return jsonify({'erro': 'Nenhum carro selecionado para instalação. A equipe não tem carro ativo.'}), 400
                
                # Atualizar solicitação com carro_id quando não estava preenchido (ex.: inferido pelo carro ativo)
                if not solicitacao.get('carro_id') or carro_id_request:
                    print(f"[INSTALAR PEÇA] Atualizando carro_id da solicitação para {carro_id_final}...")
                    resultado_atualizar = api.db.atualizar_carro_id_solicitacao_peca(solicitacao_id, carro_id_final)
                    print(f"[INSTALAR PEÇA] Resultado da atualização: {resultado_atualizar}")
                
                peca_id = solicitacao['peca_id']
                equipe_id_peca = str(solicitacao.get('equipe_id') or '')
                # Se peca_id é uma peça do armazém (tabela pecas), instalar por id (base) ou upgrade na base
                ok_por_id, msg_por_id = api.db.instalar_peca_por_id_no_carro(peca_id, carro_id_final, equipe_id_peca)
                if ok_por_id:
                    sucesso_status = api.db.atualizar_status_solicitacao_peca(solicitacao_id, 'instalado')
                    if sucesso_status:
                        print(f"[PEÇA INSTALADA] Solicitação {solicitacao_id} (peça armazém) instalada com sucesso")
                        try:
                            if solicitacao.get('equipe_id'):
                                equipe = api.gerenciador.obter_equipe(solicitacao['equipe_id'])
                                comissao_valor = float(api.db.obter_configuracao('comissao_warehouse') or '10')
                                api.db.registrar_comissao(
                                    tipo='instalar_peca',
                                    valor=comissao_valor,
                                    equipe_id=solicitacao['equipe_id'],
                                    equipe_nome=equipe.nome if equipe else 'Desconhecido',
                                    descricao=f'Instalação de {solicitacao.get("peca_nome", "")} do warehouse'
                                )
                        except Exception as e:
                            print(f"[AVISO] Erro ao registrar comissão: {e}")
                        return jsonify({
                            'sucesso': True,
                            'mensagem': f'Peça {solicitacao.get("peca_nome", "")} instalada com sucesso!'
                        })
                    return jsonify({'erro': 'Erro ao atualizar status da solicitação'}), 400
                # Se é upgrade do armazém: vincular à peça base no carro
                if api.db._column_exists('pecas', 'upgrade_id'):
                    conn_u = api.db._get_conn()
                    cur_u = conn_u.cursor()
                    cur_u.execute('SELECT upgrade_id, peca_loja_id FROM pecas WHERE id = %s AND equipe_id = %s', (peca_id, equipe_id_peca))
                    row_u = cur_u.fetchone()
                    conn_u.close()
                    if row_u and row_u[0]:  # é upgrade
                        peca_loja_id_base = row_u[1]
                        base_id = None
                        conn_b = api.db._get_conn()
                        cur_b = conn_b.cursor()
                        cur_b.execute('''
                            SELECT id FROM pecas WHERE carro_id = %s AND equipe_id = %s AND instalado = 1
                              AND peca_loja_id = %s AND (upgrade_id IS NULL OR upgrade_id = '')
                            LIMIT 1
                        ''', (carro_id_final, equipe_id_peca, peca_loja_id_base))
                        rb = cur_b.fetchone()
                        conn_b.close()
                        base_id = rb[0] if rb else None
                        if base_id:
                            ok_up, msg_up = api.db.instalar_upgrade_em_peca(equipe_id_peca, peca_id, base_id, exigir_alvo_no_carro=False)
                            if ok_up:
                                api.db.atualizar_status_solicitacao_peca(solicitacao_id, 'instalado')
                                try:
                                    if solicitacao.get('equipe_id'):
                                        equipe = api.gerenciador.obter_equipe(solicitacao['equipe_id'])
                                        cv = float(api.db.obter_configuracao('comissao_warehouse') or '10')
                                        api.db.registrar_comissao(tipo='instalar_peca', valor=cv, equipe_id=solicitacao['equipe_id'], equipe_nome=equipe.nome if equipe else 'Desconhecido', descricao=f'Instalação de {solicitacao.get("peca_nome", "")} do warehouse')
                                except Exception:
                                    pass
                                return jsonify({'sucesso': True, 'mensagem': f'Upgrade {solicitacao.get("peca_nome", "")} instalado com sucesso!'})
                            return jsonify({'erro': msg_up}), 400
                        return jsonify({'erro': 'Nenhuma peça base correspondente no carro para instalar o upgrade. Instale primeiro a peça base (ex.: motor).'}), 400
                # Senão: peça da loja — criar no armazém se não existir e instalar
                print(f"[INSTALAR PEÇA] Criando peça no armazém: peca_loja_id={peca_id}, equipe_id={equipe_id_peca}")
                try:
                    peca_armazem = api.db.criar_peca_armazem(peca_id, solicitacao['equipe_id'])
                    if not peca_armazem:
                        print(f"[INSTALAR PEÇA] ERRO ao criar peça no armazém")
                        return jsonify({'erro': 'Erro ao criar peça no armazém'}), 400
                    print(f"[INSTALAR PEÇA] Peça criada com sucesso: {peca_armazem}")
                except Exception as e:
                    print(f"[INSTALAR PEÇA] EXCEPTION ao criar peça: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({'erro': f'Erro ao criar peça: {str(e)}'}), 400
                
                print(f"[INSTALAR PEÇA] Instalando peça {peca_id} no carro {carro_id_final}")
                sucesso, mensagem = api.db.instalar_peca_no_carro(peca_id, carro_id_final)
                
                if not sucesso:
                    print(f"[ERRO INSTALAÇÃO] {mensagem}")
                    return jsonify({'erro': mensagem}), 400
                
                # Atualizar status da solicitação
                sucesso_status = api.db.atualizar_status_solicitacao_peca(solicitacao_id, 'instalado')
                
                if sucesso_status:
                    print(f"[PEÇA INSTALADA] Solicitação {solicitacao_id} instalada com sucesso")
                    
                    # Registrar comissão se a peça era do armazém
                    try:
                        # Verificar se é instalação de peça do warehouse (tem equipe_id na solicitação)
                        if solicitacao.get('equipe_id'):
                            equipe = api.gerenciador.obter_equipe(solicitacao['equipe_id'])
                            comissao_valor = float(api.db.obter_configuracao('comissao_warehouse') or '10')
                            api.db.registrar_comissao(
                                tipo='instalar_peca',
                                valor=comissao_valor,
                                equipe_id=solicitacao['equipe_id'],
                                equipe_nome=equipe.nome if equipe else 'Desconhecido',
                                descricao=f'Instalação de {solicitacao["peca_nome"]} do warehouse'
                            )
                            print(f"[COMISSÃO] Registrada: R$ {comissao_valor} por instalação de peça do warehouse")
                    except Exception as e:
                        print(f"[AVISO] Erro ao registrar comissão: {e}")
                    
                    return jsonify({
                        'sucesso': True,
                        'mensagem': f'Peça {solicitacao["peca_nome"]} instalada com sucesso!'
                    })
                else:
                    return jsonify({'erro': 'Erro ao atualizar status da solicitação'}), 400
            
            # ===== PROCESSAR ARMAZENAMENTO DE PEÇA =====
            elif novo_status == 'guardada':
                # Apenas mudar status sem instalar
                sucesso = api.db.atualizar_status_solicitacao_peca(solicitacao_id, 'guardada')
                
                if sucesso:
                    print(f"[PEÇA GUARDADA] Solicitação {solicitacao_id} guardada")
                    return jsonify({
                        'sucesso': True,
                        'mensagem': f'Peça {solicitacao["peca_nome"]} guardada no armazém'
                    })
                else:
                    return jsonify({'erro': 'Erro ao atualizar solicitação'}), 400
            
            # ===== REJEITAR SOLICITAÇÃO =====
            elif novo_status == 'reprovado':
                # Rejeitar a solicitação (devolver dinheiro se necessário)
                sucesso = api.db.atualizar_status_solicitacao_peca(solicitacao_id, 'reprovado')
                
                if sucesso:
                    # Aqui você poderia devolver os doricoins para a equipe
                    print(f"[PEÇA REPROVADA] Solicitação {solicitacao_id} reprovada")
                    return jsonify({
                        'sucesso': True,
                        'mensagem': f'Solicitação de {solicitacao["peca_nome"]} reprovada'
                    })
                else:
                    return jsonify({'erro': 'Erro ao atualizar solicitação'}), 400
            else:
                return jsonify({'erro': 'Status inválido'}), 400
    
    except Exception as e:
        print(f"[ERRO PROCESSAR SOLICITAÇÃO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500

@app.route('/api/admin/etapas')
@requer_admin
def api_admin_etapas():
    """Listar todas as etapas (robusto a formatos variados retornados pelo DB)"""
    try:
        etapas_raw = api.db.listar_etapas()

        etapas = []
        for idx, item in enumerate(etapas_raw or []):
            try:
                # Aceita dicts ou objetos com atributos
                if isinstance(item, dict):
                    eid = item.get('id')
                    nome = item.get('nome')
                    numero = item.get('numero')
                    campeonato_nome = item.get('campeonato_nome', '')
                    serie = item.get('serie')
                    hora_etapa = item.get('hora_etapa')
                else:
                    eid = getattr(item, 'id', None)
                    nome = getattr(item, 'nome', None)
                    numero = getattr(item, 'numero', None)
                    campeonato_nome = getattr(item, 'campeonato_nome', '')
                    serie = getattr(item, 'serie', None)
                    hora_etapa = getattr(item, 'hora_etapa', None)

                etapas.append({
                    'id': eid,
                    'nome': nome,
                    'numero': numero,
                    'campeonato_nome': campeonato_nome or '',
                    'serie': serie,
                    'hora_etapa': hora_etapa
                })
            except Exception as inner_e:
                print(f"[ERRO NORMALIZAR ETAPA] índice={idx} erro={inner_e} item={repr(item)[:200]}")
                import traceback
                traceback.print_exc()
                # pular item problemático
                continue

        return jsonify({'sucesso': True, 'etapas': etapas})

    except Exception as e:
        print(f"[ERRO LISTAR ETAPAS] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# ============ ROTAS ADMIN - COMISSÕES ============

@app.route('/api/admin/comissoes')
@requer_admin
def api_admin_comissoes():
    """Listar todas as comissões"""
    try:
        comissoes = api.db.listar_comissoes(limit=50)
        resumo_raw = api.db.obter_resumo_comissoes()
        
        # Calcular totais por categoria
        total = sum(resumo_raw.values())
        carros = resumo_raw.get('compra_carro', 0) + resumo_raw.get('instalar_peca', 0)
        pecas = resumo_raw.get('compra_peca', 0) + resumo_raw.get('instalar_peca', 0)
        
        resumo = {
            'total': float(total),
            'carros': float(carros),
            'pecas': float(pecas)
        }
        
        return jsonify({
            'sucesso': True,
            'comissoes': comissoes,
            'resumo': resumo
        })
    except Exception as e:
        print(f"[ERRO LISTAR COMISSÕES] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/configuracao/<config_key>', methods=['GET', 'POST'])
@requer_admin
def gerenciar_configuracao(config_key):
    """Obter ou definir uma configuração"""
    try:
        if request.method == 'GET':
            valor = api.db.obter_configuracao(config_key)
            return jsonify({
                'sucesso': True,
                'valor': valor
            })
        else:  # POST
            dados = request.json
            valor = dados.get('valor', '')
            api.db.salvar_configuracao(config_key, valor)
            return jsonify({'sucesso': True})
    except Exception as e:
        print(f"[ERRO CONFIGURAÇÃO] {str(e)}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

# ============ ROTAS PIX / MERCADO PAGO ============

@app.route('/api/gerar-qr-pix', methods=['POST'])
@requer_login_api
def gerar_qr_pix():
    """Gera um QR Code PIX para a compra ou serviço"""
    try:
        from src.mercado_pago_client import mp_client
        
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'erro': 'Não autenticado'}), 401
        
        dados = request.json
        tipo = dados.get('tipo')  # 'carro', 'peca', ou 'warehouse'
        item_id = dados.get('item_id')
        carro_id = dados.get('carro_id')  # Para peças, qual carro instalar
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'erro': 'Equipe não encontrada'}), 404
        
        # Verificar se já existe uma transação pendente para este item
        transacoes_existentes = api.db.listar_transacoes_pix(equipe_id=equipe_id, status='pendente')
        for trans in transacoes_existentes:
            if trans['tipo_item'] == tipo and trans['item_id'] == item_id:
                # Transação pendente já existe - retornar dados existentes
                print(f"[QR PIX] Transação pendente encontrada: {trans['id']}")
                
                # Gerar imagem QR code se não tiver sido feita ainda
                qr_code_url = trans['qr_code_url']
                if trans['qr_code'] and not qr_code_url.startswith('data:'):
                    # O qr_code_url é na verdade o código PIX em texto, gerar imagem
                    print(f"[QR PIX] Gerando imagem para código PIX existente...")
                    from src.mercado_pago_client import mp_client
                    img_base64 = mp_client.gerar_qr_code_imagem_pix(trans['qr_code'])
                    if img_base64:
                        qr_code_url = f"data:image/png;base64,{img_base64}"
                        # Atualizar no banco para não precisar gerar novamente
                        api.db.atualizar_transacao_pix(
                            transacao_id=trans['id'],
                            mercado_pago_id=trans.get('id', ''),
                            qr_code=trans['qr_code'],
                            qr_code_url=qr_code_url
                        )
                        print(f"[QR PIX] Imagem gerada e salva")
                
                return jsonify({
                    'sucesso': True,
                    'transacao_id': trans['id'],
                    'qr_code_url': qr_code_url,
                    'checkout_url': '',
                    'valor_total': trans['valor_total'],
                    'valor_item': trans['valor_item'],
                    'taxa': trans['valor_taxa'],
                    'item_nome': trans['item_nome'],
                    'tipo_item': trans['tipo_item'],
                    'item_id': trans['item_id'],
                    'carro_id': carro_id,
                    'ja_existente': True
                })
        
        # Encontrar o item
        item = None
        item_nome = ""
        valor_pix = 0
        
        # Verificar se há valor customizado (para carrinho)
        valor_custom = dados.get('valor_custom')
        
        # ===== CARROS NÃO GERAM PIX NA COMPRA =====
        if tipo == 'carro':
            # Carros agora geram PIX apenas na ATIVAÇÃO, não na compra
            return jsonify({'erro': 'Carros não geram PIX na compra. Use /api/ativar-carro para ativar e gerar PIX de ativação.'}), 400
        elif tipo == 'peca':
            # Se houver valor customizado (carrinho), usar esse valor
            if valor_custom:
                item_nome = "Carrinho de Peças"
                valor_pix = float(valor_custom)
            else:
                # Compra de peça individual = comissão em PIX (peça custa doricoins, não reais)
                for peca in api.loja_pecas.pecas:
                    if peca.id == item_id:
                        item = peca
                        item_nome = peca.nome
                        # Usar comissão configurada
                        valor_pix = float(api.db.obter_configuracao('comissao_peca') or '10')
                        break
        elif tipo == 'warehouse' or tipo == 'instalacao_armazem':
            # Instalação warehouse = preço de instalação em PIX
            for peca in api.loja_pecas.pecas:
                if peca.id == item_id:
                    item = peca
                    item_nome = f"Instalar: {peca.nome}"
                    # Usar preço de instalação configurado
                    valor_pix = float(api.db.obter_configuracao('preco_instalacao_warehouse') or '10')
                    break
        
        if not item and not valor_custom:
            return jsonify({'erro': 'Item não encontrado'}), 404
        
        # Calcular taxa
        taxa = mp_client.calcular_taxa(valor_pix)
        valor_total = round(valor_pix + taxa, 2)
        # Criar transação no BD
        transacao_id = api.db.criar_transacao_pix(
            equipe_id=equipe_id,
            equipe_nome=equipe.nome,
            tipo_item=tipo,
            item_id=item_id,
            item_nome=item_nome,
            valor_item=valor_pix,
            valor_taxa=taxa,
            carro_id=carro_id
        )
        
        if not transacao_id:
            return jsonify({'erro': 'Erro ao criar transação'}), 500
        
        # Gerar QR Code no MercadoPago
        descricao = f"Compra de {item_nome} - {equipe.nome}"
        resultado_mp = mp_client.gerar_qr_code_pix(descricao, valor_total, transacao_id)
        
        if not resultado_mp.get('sucesso'):
            return jsonify({'erro': resultado_mp.get('erro', 'Erro ao gerar QR Code')}), 500
        
        # Atualizar transação com dados do MP
        api.db.atualizar_transacao_pix(
            transacao_id=transacao_id,
            mercado_pago_id=resultado_mp.get('id', ''),
            qr_code=resultado_mp.get('qr_code', ''),
            qr_code_url=resultado_mp.get('qr_code_url', '')
        )
        
        print(f"[QR PIX] Gerado para {item_nome} - Valor: R$ {valor_total}")
        print(f"[QR PIX] QR Code URL: {resultado_mp.get('qr_code_url', '')[:100] if resultado_mp.get('qr_code_url') else 'VAZIO'}")
        print(f"[QR PIX] Carro ID: {carro_id}")
        
        return jsonify({
            'sucesso': True,
            'transacao_id': transacao_id,
            'qr_code_url': resultado_mp.get('qr_code_url', ''),
            'checkout_url': resultado_mp.get('checkout_url', ''),
            'valor_total': valor_total,
            'valor_item': valor_pix,
            'taxa': taxa,
            'item_nome': item_nome,
            'tipo_item': tipo,
            'item_id': item_id,
            'carro_id': carro_id
        })
    
    except Exception as e:
        print(f"[ERRO] Erro ao gerar QR PIX: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500

@app.route('/api/webhook/mercado-pago', methods=['POST'])
def webhook_mercado_pago():
    """Webhook para receber confirmação de pagamento do MercadoPago"""
    try:
        from src.mercado_pago_client import mp_client
        
        dados = request.json or {}
        
        print(f"\n[WEBHOOK MP] Recebido: {dados}")
        
        # Processar webhook
        resultado = mp_client.processar_webhook(dados)
        
        if resultado.get('sucesso'):
            status = resultado.get('status')
            transacao_id = resultado.get('transacao_id')
            
            if status == 'approved':
                print(f"[WEBHOOK MP] Pagamento APROVADO: {transacao_id}")
                
                # Confirmar transação no BD
                confirmacao = api.db.confirmar_transacao_pix(resultado.get('payment_id', ''))
                
                if confirmacao.get('sucesso'):
                    # Aqui você pode processar a compra automaticamente
                    print(f"[WEBHOOK MP] Transação confirmada: {transacao_id}")
        
        return jsonify({'sucesso': True}), 200
    
    except Exception as e:
        print(f"[ERRO WEBHOOK] {e}")
        return jsonify({'erro': str(e)}), 400

@app.route('/api/transacao-pix/<transacao_id>', methods=['GET'])
@requer_login_api
def obter_transacao_pix(transacao_id):
    """Obtém status de uma transação PIX (consultando BD e MercadoPago se necessário)"""
    try:
        from src.mercado_pago_client import mp_client
        
        transacao = api.db.obter_transacao_pix(transacao_id)
        
        if not transacao:
            return jsonify({'sucesso': False, 'erro': 'Transação não encontrada'}), 404
        
        # Se está pendente no BD, consultar MercadoPago para verificar se foi pago
        if transacao['status'] == 'pendente' and transacao.get('mercado_pago_id'):
            print(f"[TRANSACAO] Status pendente no BD, consultando MercadoPago: {transacao['mercado_pago_id']}")
            
            # Consultar MercadoPago
            pagamento = mp_client.obter_pagamento(transacao['mercado_pago_id'])
            
            if pagamento and pagamento.get('status') == 'approved':
                print(f"[TRANSACAO] MercadoPago confirma: PAGAMENTO APROVADO! Atualizando BD...")
                
                # Atualizar status no BD
                api.db.confirmar_transacao_pix(transacao['mercado_pago_id'])
                
                # Recarregar dados atualizados
                transacao = api.db.obter_transacao_pix(transacao_id)
                print(f"[TRANSACAO] Novo status no BD: {transacao['status']}")
            elif pagamento:
                print(f"[TRANSACAO] MercadoPago status: {pagamento.get('status')}")
        
        return jsonify({'sucesso': True, 'transacao': transacao})
    
    except Exception as e:
        print(f"[ERRO] Erro ao obter transação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


def _processar_multiplas_pecas_armazem_ativo_confirmacao(equipe_id, carro_id, pecas_solicitadas, transacao_id=None):
    """Ao confirmar PIX do modal 'múltiplas peças → carro ativo': se a peça tem 'id' (veio da loja),
    adiciona ao armazém; senão procura no armazém por nome/tipo. Cria uma solicitação pendente por peça.
    Retorna (num_solicitacoes, None) em sucesso ou (0, mensagem_erro) em falha."""
    if not pecas_solicitadas or not carro_id:
        return 0, 'Dados da transação incompletos (pecas/carro_id)'
    pecas_armazem = api.db.carregar_pecas_armazem_equipe(str(equipe_id))
    pecas_loja = api.db.carregar_pecas_loja()
    used_ids = set()
    ids_para_pix = []

    def _achar_armazem(nome, tipo, eh_upgrade):
        for p in pecas_armazem:
            if p['id'] in used_ids:
                continue
            if (p.get('nome') or '').lower() != (nome or '').lower() or (p.get('tipo') or '').lower() != (tipo or '').lower():
                continue
            if eh_upgrade and not p.get('upgrade_id'):
                continue
            if not eh_upgrade and p.get('upgrade_id'):
                continue
            return p
        return None

    for peca_req in pecas_solicitadas:
        peca_nome = peca_req.get('nome')
        peca_tipo = peca_req.get('tipo')
        peca_id_origem = peca_req.get('id')
        peca_armazem_id = None

        if peca_id_origem:
            # Peça veio da loja (compra PIX): adicionar ao armazém
            if (peca_tipo or '').lower() == 'upgrade':
                # IDs de upgrades vêm como "upgrade_<uuid>" da loja; buscar_upgrade_por_id espera só o uuid
                upgrade_id_real = str(peca_id_origem).replace('upgrade_', '', 1) if str(peca_id_origem).startswith('upgrade_') else str(peca_id_origem)
                res = api.db.adicionar_upgrade_armazem(str(equipe_id), upgrade_id_real)
                if not res:
                    return 0, f'Falha ao adicionar upgrade ao armazém: {peca_nome}'
                peca_armazem_id = res
                pecas_armazem = api.db.carregar_pecas_armazem_equipe(str(equipe_id))
            else:
                pl = next((p for p in pecas_loja if str(getattr(p, 'id', p)) == str(peca_id_origem)), None)
                if not pl:
                    return 0, f'Peça da loja não encontrada: id={peca_id_origem}'
                preco = float(getattr(pl, 'preco', 0) or 0)
                durabilidade = int(getattr(pl, 'durabilidade', 100) or 100)
                coef = float(getattr(pl, 'coeficiente_quebra', 1) or 1)
                res = api.db.adicionar_peca_armazem(
                    str(equipe_id), str(peca_id_origem), getattr(pl, 'nome', peca_nome),
                    getattr(pl, 'tipo', peca_tipo or 'motor'), durabilidade, preco, coef
                )
                if not res:
                    return 0, f'Falha ao adicionar peça ao armazém: {peca_nome}'
                peca_armazem_id = res
                pecas_armazem = api.db.carregar_pecas_armazem_equipe(str(equipe_id))
        else:
            for eh_upgrade in (False, True):
                p_arm = _achar_armazem(peca_nome, peca_tipo, eh_upgrade)
                if p_arm:
                    peca_armazem_id = p_arm['id']
                    break
            if not peca_armazem_id:
                return 0, f'Peça não encontrada no armazém nem na loja: {peca_nome} ({peca_tipo})'

        used_ids.add(peca_armazem_id)
        ids_para_pix.append(peca_armazem_id)
        ok = api.db.salvar_solicitacao_peca(str(uuid.uuid4()), equipe_id, peca_armazem_id, 1, 'pendente', carro_id)
        if not ok:
            erro = getattr(api.db, '_erro_solicitacao_peca', None)
            msg = 'Já existe uma solicitação pendente para esta peça neste carro.' if erro == 'duplicada' else f'Falha ao criar solicitação para {peca_nome}.'
            return 0, msg

    if transacao_id and api.db._column_exists('pecas', 'pix_id') and ids_para_pix:
        conn = api.db._get_conn()
        cursor = conn.cursor()
        ph = ','.join(['%s'] * len(ids_para_pix))
        cursor.execute(f'UPDATE pecas SET pix_id = %s WHERE id IN ({ph})', (str(transacao_id),) + tuple(ids_para_pix))
        conn.commit()
        conn.close()
    return len(ids_para_pix), None


@app.route('/api/confirmar-pagamento-manual', methods=['POST'])
@requer_login_api
def confirmar_pagamento_manual():
    """Confirma manualmente um pagamento (para testes sem webhook)"""
    try:
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        dados = request.json
        transacao_id = dados.get('transacao_id')
        
        if not transacao_id:
            return jsonify({'sucesso': False, 'erro': 'transacao_id é obrigatório'}), 400
        
        # Obter a transação
        transacao = api.db.obter_transacao_pix(transacao_id)
        
        if not transacao:
            return jsonify({'sucesso': False, 'erro': 'Transação não encontrada'}), 404
        
        # Verificar se pertence à equipe do usuário
        if transacao['equipe_id'] != equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403
        
        # Verificar se está pendente
        if transacao['status'] != 'pendente':
            return jsonify({'sucesso': False, 'erro': f'Transação não está pendente (status: {transacao["status"]})'}), 400
        
        # Confirmar a transação (atualiza status)
        sucesso = api.db.confirmar_transacao_pix(transacao['mercado_pago_id'] or transacao_id)
        
        if sucesso.get('sucesso'):
            print(f"[CONFIRMAÇÃO MANUAL] Transação {transacao_id} confirmada manualmente")
            
            # Agora processar a compra (carro, peça, etc)
            print(f"[CONFIRMAÇÃO MANUAL] Processando compra: tipo={transacao['tipo_item']}, item_id={transacao['item_id']}")
            
            if transacao['tipo_item'] == 'carro':
                # Buscar variacao_id da transação se foi salvo, senão usar compatibilidade
                variacao_id_trans = transacao.get('variacao_id')
                resultado = api.comprar_carro(equipe_id, transacao['item_id'], variacao_id_trans)
                if resultado:
                    print(f"[CONFIRMAÇÃO MANUAL] Carro comprado com sucesso")
                    return jsonify({'sucesso': True, 'mensagem': 'Carro comprado com sucesso'})
                else:
                    return jsonify({'sucesso': False, 'erro': 'Erro ao comprar carro'}), 400
            
            elif transacao['tipo_item'] == 'peca':
                # Compra de peça da loja - criar no armazém e instalar no carro ativo
                try:
                    print(f"\n[COMPRA PIX LOJA] ===== INICIANDO COMPRA DE PEÇA =====")
                    print(f"[COMPRA PIX LOJA] Transacao ID: {transacao_id}")
                    print(f"[COMPRA PIX LOJA] Equipe: {equipe_id}")
                    print(f"[COMPRA PIX LOJA] Peça ID: {transacao['item_id']}")
                    print(f"[COMPRA PIX LOJA] Carro ID (transacao): {transacao.get('carro_id')}")
                    
                    # Usar carro_id da transação se foi selecionado, senão usar o carro ativo
                    carro_id_peca = transacao.get('carro_id')
                    if not carro_id_peca:
                        equipe = api.db.carregar_equipe(equipe_id)
                        carro_id_peca = equipe.carro.id if equipe and equipe.carro else None
                    
                    print(f"[COMPRA PIX LOJA] Carro final: {carro_id_peca}")
                    
                    if not carro_id_peca:
                        print(f"[COMPRA PIX LOJA] ❌ Nenhum carro selecionado")
                        return jsonify({'sucesso': False, 'erro': 'Nenhum carro selecionado'}), 400
                    
                    # Obter dados da peça da loja
                    peca_loja = api.obter_peca_loja(transacao['item_id'])
                    if not peca_loja:
                        print(f"[COMPRA PIX LOJA] ❌ Peça loja {transacao['item_id']} não encontrada")
                        return jsonify({'sucesso': False, 'erro': 'Peça não encontrada'}), 404
                    
                    peca_tipo = peca_loja.tipo
                    peca_nome = peca_loja.nome
                    print(f"[COMPRA PIX LOJA] ✅ Peça encontrada: {peca_nome} (tipo: {peca_tipo})")
                    
                    # 1. REMOVER TODAS as peças antigas do mesmo tipo do carro ativo
                    cursor = api.db.db.cursor()
                    
                    print(f"[COMPRA PIX LOJA] 🗑️ Procurando peças antigas do tipo '{peca_tipo}'...")
                    cursor.execute('''
                        SELECT id, nome FROM pecas 
                        WHERE carro_id = %s AND tipo = %s AND instalado = 1 AND equipe_id = %s
                    ''', (str(carro_id_peca), peca_tipo, str(equipe_id)))
                    
                    pecas_antigas = cursor.fetchall()
                    print(f"[COMPRA PIX LOJA] Encontradas {len(pecas_antigas)} peça(s) antigas")
                    
                    for peca_id, peca_nome_antiga in pecas_antigas:
                        print(f"[COMPRA PIX LOJA] 🗑️ Removendo: {peca_nome_antiga} (ID: {peca_id})")
                        cursor.execute('''
                            UPDATE pecas 
                            SET carro_id = NULL, instalado = 0, pix_id = NULL
                            WHERE id = %s
                        ''', (str(peca_id),))
                    
                    api.db.db.commit()
                    print(f"[COMPRA PIX LOJA] ✅ {len(pecas_antigas)} peça(s) desinstalada(s)")
                    
                    # 2. CRIAR a peça nova no banco de dados (na tabela pecas como armazém)
                    nova_peca_id = str(__import__('uuid').uuid4())
                    print(f"[COMPRA PIX LOJA] 📦 Criando peça no armazém: {nova_peca_id}")
                    
                    cursor.execute('''
                        INSERT INTO pecas 
                        (id, peca_loja_id, nome, tipo, preco, durabilidade_maxima, durabilidade_atual, instalado, carro_id, equipe_id, data_criacao)
                        VALUES (%s, %s, %s, %s, %s, 100, 100, 0, NULL, %s, NOW())
                    ''', (nova_peca_id, str(transacao['item_id']), peca_nome, peca_tipo, peca_loja.preco, str(equipe_id)))
                    
                    api.db.db.commit()
                    print(f"[COMPRA PIX LOJA] ✅ Peça criada no armazém: {nova_peca_id}")
                    
                    # 3. INSTALAR a peça nova usando a função que trata o banco corretamente
                    print(f"[COMPRA PIX LOJA] Instalando peça no carro...")
                    resultado = api.db.instalar_peca_warehouse(transacao['item_id'], carro_id_peca, equipe_id)
                    
                    if resultado:
                        print(f"[COMPRA PIX LOJA] ✅ Peça instalada com sucesso!")
                        print(f"[COMPRA PIX LOJA] ===== COMPRA CONCLUÍDA COM SUCESSO =====\n")
                        return jsonify({'sucesso': True, 'mensagem': 'Peça instalada com sucesso'})
                    else:
                        print(f"[COMPRA PIX LOJA] ⚠️ Peça criada mas não foi possível instalar")
                        print(f"[COMPRA PIX LOJA] ===== COMPRA CONCLUÍDA (COM AVISO) =====\n")
                        return jsonify({'sucesso': True, 'mensagem': 'Peça adicionada ao armazém (não foi possível instalar no carro)'}), 200
                        
                except Exception as e:
                    print(f"[COMPRA PIX LOJA] ❌ ERRO ao processar compra: {e}")
                    import traceback
                    traceback.print_exc()
                    print(f"[COMPRA PIX LOJA] ===== ERRO FATAL =====\n")
                    return jsonify({'sucesso': False, 'erro': f'Erro ao processar peça: {str(e)}'}), 500
            
            elif transacao['tipo_item'] == 'instalacao_armazem' or transacao['tipo_item'] == 'warehouse':
                # Instalar peça do armazém no carro (peça específica por id, com upgrades)
                print(f"[CONFIRMAÇÃO MANUAL] Instalando peça do armazém...")
                carro_id_instalacao = transacao.get('carro_id') or transacao.get('item_id')
                if not carro_id_instalacao:
                    equipe = api.db.carregar_equipe(equipe_id)
                    carro_id_instalacao = equipe.carro.id if equipe and equipe.carro else None
                dados_json_str = transacao.get('dados_json') or '{}'
                try:
                    dados_json = json.loads(dados_json_str) if isinstance(dados_json_str, str) else dados_json_str
                except Exception:
                    dados_json = {}
                peca_armazem_id = dados_json.get('peca_armazem_id')
                peca_loja_id = dados_json.get('peca_loja_id')
                try:
                    if peca_armazem_id:
                        ok, msg = api.db.instalar_peca_por_id_no_carro(peca_armazem_id, carro_id_instalacao, equipe_id)
                        if ok:
                            print(f"[CONFIRMAÇÃO MANUAL] Peça e upgrades instalados no carro")
                            return jsonify({'sucesso': True, 'mensagem': msg})
                        return jsonify({'sucesso': False, 'erro': msg}), 400
                    if peca_loja_id:
                        resultado = api.db.instalar_peca_warehouse(peca_loja_id, carro_id_instalacao, equipe_id)
                        if resultado:
                            return jsonify({'sucesso': True, 'mensagem': 'Peça instalada com sucesso'})
                        return jsonify({'sucesso': False, 'erro': 'Erro ao instalar peça'}), 400
                except Exception as e:
                    print(f"[CONFIRMAÇÃO MANUAL] ERRO ao instalar peça: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({'sucesso': False, 'erro': str(e)}), 400
                return jsonify({'sucesso': False, 'erro': 'Transação sem peca_armazem_id ou peca_loja_id'}), 400
            
            elif transacao['tipo_item'] == 'multiplas_pecas_armazem_ativo_modal':
                import json as _json
                dados_json_str = transacao.get('dados_json') or '{}'
                try:
                    dados_json = _json.loads(dados_json_str) if isinstance(dados_json_str, str) else dados_json_str
                except Exception:
                    dados_json = {}
                pecas_solicitadas = dados_json.get('pecas', [])
                carro_id = transacao.get('carro_id') or transacao.get('item_id')
                print(f"[CONFIRMAÇÃO MANUAL] multiplas_pecas_armazem_ativo_modal: criando solicitações (com PIX: peças vão ao armazém se tiverem id)...")
                n, err = _processar_multiplas_pecas_armazem_ativo_confirmacao(equipe_id, carro_id, pecas_solicitadas, transacao_id=transacao_id)
                if err:
                    return jsonify({'sucesso': False, 'erro': err}), 400 if 'duplicada' in err else 500
                print(f"[CONFIRMAÇÃO MANUAL] ✅ {n} solicitação(ões) pendente(s) criada(s). Aguardando aprovação do admin.")
                return jsonify({'sucesso': True, 'mensagem': f'{n} solicitação(ões) criada(s). As peças serão instaladas após aprovação do administrador.'})
            
            elif transacao['tipo_item'] == 'carro_ativacao':
                # Ativação de carro já foi criada como solicitação no confirmar_transacao_pix()
                # Agora apenas retornamos sucesso - a ativação real será feita quando admin aprovar
                print(f"\n[ATIVAÇÃO CARRO PIX] ===== SOLICITAÇÃO CRIADA =====")
                print(f"[ATIVAÇÃO CARRO PIX] Transacao ID: {transacao_id}")
                print(f"[ATIVAÇÃO CARRO PIX] Carro ID: {transacao['item_id']}")
                print(f"[ATIVAÇÃO CARRO PIX] ✅ Solicitação criada com sucesso (aguardando aprovação do admin)")
                
                return jsonify({
                    'sucesso': True, 
                    'mensagem': 'Solicitação de ativação criada com sucesso! Aguardando aprovação do administrador.',
                    'transacao_id': transacao_id,
                    'carro_id': transacao['item_id']
                })
            
            elif transacao['tipo_item'] == 'regularizacao_saldo':
                # Regularização de saldo para participação em etapa
                print(f"\n[REGULARIZAÇÃO ETAPA] ===== REGISTRANDO PARTICIPAÇÃO =====")
                print(f"[REGULARIZAÇÃO ETAPA] Transacao ID: {transacao_id}")
                print(f"[REGULARIZAÇÃO ETAPA] Equipe: {equipe_id}")
                print(f"[REGULARIZAÇÃO ETAPA] Etapa ID: {transacao['item_id']}")
                
                try:
                    import json
                    # Extrair dados da participação do dados_json
                    dados_json_str = transacao.get('dados_json', '{}')
                    dados_participacao = json.loads(dados_json_str) if dados_json_str else {}
                    
                    tipo_participacao = dados_participacao.get('tipo_participacao', 'dono_vai_andar')
                    etapa_id = dados_participacao.get('etapa_id') or transacao['item_id']
                    carro_id = dados_participacao.get('carro_id') or transacao.get('carro_id')
                    valor_regularizacao = float(transacao.get('valor_item', 0))
                    
                    print(f"[REGULARIZAÇÃO ETAPA] Tipo participação: {tipo_participacao}")
                    print(f"[REGULARIZAÇÃO ETAPA] Carro ID: {carro_id}")
                    print(f"[REGULARIZAÇÃO ETAPA] Valor regularizado: R$ {valor_regularizacao:.2f}")
                    
                    if not carro_id:
                        return jsonify({'sucesso': False, 'erro': 'Carro não especificado'}), 400
                    
                    # 1. Obter saldo atual para determinar quanto é débito vs inscrição
                    conn = api.db._get_conn()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute('SELECT saldo_pix FROM equipes WHERE id = %s', (equipe_id,))
                    result = cursor.fetchone()
                    saldo_atual = float(result['saldo_pix']) if result else 0.0
                    cursor.close()
                    
                    print(f"[REGULARIZAÇÃO ETAPA] Saldo atual: R$ {saldo_atual:.2f}")
                    
                    # Calcular quanto é débito (quitação) vs inscrição
                    if saldo_atual < 0:
                        # Há débito a quitar
                        valor_quitacao = abs(saldo_atual)  # Quanto deve quitando para chegar a 0
                        valor_inscricao = valor_regularizacao - valor_quitacao
                        
                        print(f"[REGULARIZAÇÃO ETAPA] Débito a quitar: R$ {valor_quitacao:.2f}")
                        print(f"[REGULARIZAÇÃO ETAPA] Valor para inscrição: R$ {valor_inscricao:.2f}")
                        
                        # 2. Atualizar saldo PIX APENAS para quitar o débito (volta a 0)
                        resultado_saldo = api.db.atualizar_saldo_pix(equipe_id, valor_quitacao)
                        
                        if not resultado_saldo['sucesso']:
                            print(f"[REGULARIZAÇÃO ETAPA] ⚠️ Erro ao atualizar saldo: {resultado_saldo.get('erro')}")
                        else:
                            print(f"[REGULARIZAÇÃO ETAPA] ✅ Débito quitado. Novo saldo: R$ {resultado_saldo['novo_saldo']:.2f}")
                    else:
                        # Sem débito - este é caso incomum (não deveria chegar aqui)
                        print(f"[REGULARIZAÇÃO ETAPA] ⚠️ Saldo positivo (sem débito): R$ {saldo_atual:.2f}")
                        resultado_saldo = {'sucesso': True, 'novo_saldo': saldo_atual}
                    
                    # 3. Registrar a equipe na etapa (SEM mexer em saldo_pix adicional)
                    conn = api.db._get_conn()
                    cursor = conn.cursor()
                    
                    participacao_id = str(__import__('uuid').uuid4())
                    
                    cursor.execute('''
                        INSERT INTO participacoes_etapas 
                        (id, etapa_id, equipe_id, carro_id, status, data_inscricao, data_atualizacao, tipo_participacao)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), %s)
                    ''', (
                        participacao_id,
                        etapa_id,
                        equipe_id,
                        carro_id,
                        'ativa',
                        tipo_participacao
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    print(f"[REGULARIZAÇÃO ETAPA] ✅ Participação registrada: {participacao_id}")
                    print(f"[REGULARIZAÇÃO ETAPA] ✅ Inscrição processada (saldo_pix não é afetado)")
                    print(f"[REGULARIZAÇÃO ETAPA] ===== REGISTRO CONCLUÍDO =====\n")
                    
                    return jsonify({
                        'sucesso': True,
                        'mensagem': 'Saldo regularizado e participação registrada com sucesso!',
                        'transacao_id': transacao_id,
                        'etapa_id': etapa_id,
                        'participacao_id': participacao_id,
                        'novo_saldo': resultado_saldo.get('novo_saldo', 0)
                    })
                    
                except Exception as e:
                    print(f"[REGULARIZAÇÃO ETAPA] ❌ ERRO ao registrar participação: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({'sucesso': False, 'erro': f'Erro ao registrar participação: {str(e)}'}), 500
            
            elif transacao['tipo_item'] == 'multiplas_pecas_armazem_ativo_modal':
                print(f"\n[MULTIPLAS PEÇAS CARRO ATIVO] ===== CRIANDO SOLICITAÇÕES (PIX: peças vão ao armazém se tiverem id) =====")
                try:
                    import json
                    dados_json_str = transacao.get('dados_json', '{}')
                    dados_json = json.loads(dados_json_str) if dados_json_str else {}
                    pecas_lista = dados_json.get('pecas', [])
                    carro_id = transacao.get('carro_id') or transacao.get('item_id')
                    n, err = _processar_multiplas_pecas_armazem_ativo_confirmacao(equipe_id, carro_id, pecas_lista, transacao_id=transacao_id)
                    if err:
                        return jsonify({'sucesso': False, 'erro': err}), 400 if 'duplicada' in err else 500
                    if n == 0:
                        return jsonify({'sucesso': True, 'mensagem': 'Nenhuma peça a processar'})
                    print(f"[MULTIPLAS PEÇAS CARRO ATIVO] ✅ {n} solicitação(ões) criada(s)\n")
                    return jsonify({'sucesso': True, 'mensagem': f'{n} solicitação(ões) criada(s)', 'solicitacoes': n})
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return jsonify({'sucesso': False, 'erro': str(e)}), 500
            
            else:
                return jsonify({'sucesso': True, 'mensagem': 'Pagamento confirmado'})
        else:
            return jsonify({'sucesso': False, 'erro': 'Erro ao confirmar transação'}), 500
    
    except Exception as e:
        print(f"[ERRO] Erro ao confirmar pagamento manualmente: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/cancelar-transacao-pix', methods=['POST'])
def cancelar_transacao_pix():
    """Cancela uma transação PIX pendente quando o usuário fecha o modal"""
    try:
        dados = request.get_json()
        transacao_id = dados.get('transacao_id')
        
        if not transacao_id:
            return jsonify({'sucesso': False, 'erro': 'transacao_id é obrigatório'}), 400
        
        # Obter a transação
        transacao = api.db.obter_transacao_pix(transacao_id)
        
        if not transacao:
            print(f"[CANCELAR] Transação {transacao_id} não encontrada (pode ter sido deletada)")
            return jsonify({'sucesso': True, 'mensagem': 'Transação já não existe'})
        
        # Se ainda está pendente, deletar do banco
        if transacao['status'] == 'pendente':
            api.db.deletar_transacao_pix(transacao_id)
            print(f"[CANCELAR] Transação {transacao_id} cancelada e deletada do banco")
            return jsonify({'sucesso': True, 'mensagem': 'Transação cancelada com sucesso'})
        else:
            print(f"[CANCELAR] Transação {transacao_id} não estava pendente (status: {transacao['status']}), ignorando")
            return jsonify({'sucesso': False, 'mensagem': f'Transação não está pendente (status: {transacao["status"]})'}), 400
    
    except Exception as e:
        print(f"[ERRO] Erro ao cancelar transação PIX: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/processar-compra-pix', methods=['POST'])
@requer_login_api
def processar_compra_pix():
    """Processa uma compra após pagamento PIX confirmado"""
    try:
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        dados = request.json
        tipo = dados.get('tipo')  # 'carro', 'peca', 'warehouse'
        item_id = dados.get('item_id')
        variacao_id = dados.get('variacao_id')  # Novo: ID da variação se for carro
        transacao_id = dados.get('transacao_id')
        carro_id = dados.get('carro_id')  # Para peças, qual carro instalar
        
        if not tipo or (not item_id and not variacao_id):
            return jsonify({'sucesso': False, 'erro': 'tipo e (item_id ou variacao_id) são obrigatórios'}), 400
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404
        
        print(f"[COMPRA PIX] Processando: tipo={tipo}, item_id={item_id}, variacao_id={variacao_id}, carro_id={carro_id}, equipe={equipe.nome}")
        
        if tipo == 'carro':
            # Compra de carro - usar variacao_id se disponível
            print(f"[COMPRA PIX] Comprando carro...")
            resultado = api.comprar_carro(equipe_id, item_id, variacao_id)
            if not resultado:
                print(f"[COMPRA PIX] ❌ FALHA ao comprar carro!")
                return jsonify({'sucesso': False, 'erro': 'Falha ao comprar carro'}), 400
            print(f"[COMPRA PIX] ✅ Carro adicionado à equipe {equipe.nome}")
            
        elif tipo == 'peca':
            # Compra de peça com instalação direta no carro
            print(f"[COMPRA PIX] Comprando peça para carro...")
            print(f"  - Equipe: {equipe_id}")
            print(f"  - Peça: {item_id}")
            print(f"  - Carro: {carro_id}")
            
            # Se carro_id não foi selecionado, usar o carro ativo da equipe
            if not carro_id:
                equipe_obj = api.db.carregar_equipe(equipe_id)
                if equipe_obj and equipe_obj.carro:
                    carro_id = equipe_obj.carro.id
                    print(f"[COMPRA PIX] Carro não selecionado, usando carro ativo: {carro_id}")
                else:
                    return jsonify({'sucesso': False, 'erro': 'Nenhum carro ativo selecionado'}), 400
            
            # Obter dados da peça do banco
            peca_encontrada = None
            if api.loja_pecas and hasattr(api.loja_pecas, 'pecas'):
                for peca_obj in api.loja_pecas.pecas:
                    if str(peca_obj.id) == str(item_id):
                        peca_encontrada = {
                            'id': peca_obj.id,
                            'nome': peca_obj.nome,
                            'tipo': getattr(peca_obj, 'tipo', 'motor'),
                            'preco': peca_obj.preco,
                            'durabilidade': getattr(peca_obj, 'durabilidade', 100),
                            'coeficiente_quebra': getattr(peca_obj, 'coeficiente_quebra', 0.1),
                        }
                        break
            
            if not peca_encontrada:
                return jsonify({'sucesso': False, 'erro': 'Peça não encontrada'}), 404
            
            # ✅ VALIDAÇÃO: Verificar se o carro já tem pelo menos uma peça
            try:
                # Descontar do saldo já foi feito antes do PIX, apenas instalar
                resultado_instalar = api.db.adicionar_peca_carro(
                    equipe_id=equipe_id,
                    carro_id=carro_id,
                    peca_loja_id=item_id,
                    nome=peca_encontrada['nome'],
                    tipo=peca_encontrada['tipo'],
                    durabilidade=peca_encontrada['durabilidade'],
                    preco=peca_encontrada['preco'],
                    coeficiente_quebra=peca_encontrada['coeficiente_quebra'],
                    pix_id=transacao_id  # Adicionar o ID do PIX
                )
                
                if not resultado_instalar:
                    print(f"[COMPRA PIX] ❌ FALHA ao instalar peça no carro!")
                    return jsonify({'sucesso': False, 'erro': 'Falha ao instalar peça no carro'}), 500
                
                print(f"[COMPRA PIX] ✅ Peça instalada no carro com sucesso!")
                
                # Registrar na tabela de compras (HISTÓRICO)
                try:
                    conn = api.db._get_conn()
                    cursor = conn.cursor()
                    
                    compra_id = str(uuid.uuid4())
                    
                    cursor.execute('''
                        INSERT INTO solicitacao_compra 
                        (id, equipe_id, tipo, item_id, quantidade, status, data_criacao, data_processamento)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ''', (compra_id, equipe_id, 'PEÇA', item_id, 1, 'CONFIRMADA'))
                    
                    conn.commit()
                    conn.close()
                    
                    print(f"[COMPRA PIX] ✅ Compra registrada na tabela de histórico com ID: {compra_id}")
                except Exception as e:
                    print(f"[COMPRA PIX] ⚠️ Aviso ao registrar compra no histórico: {e}")
                
            except Exception as e:
                print(f"[COMPRA PIX] ❌ ERRO ao processar compra de peça: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': f'Erro ao processar compra: {str(e)}'}), 500
            
            print(f"[COMPRA PIX] ✅ Peça {peca_encontrada['nome']} instalada no carro para equipe {equipe.nome}")
            
        elif tipo == 'warehouse':
            # Instalação warehouse (peça guardada no warehouse)
            solicitacao_id = str(uuid.uuid4())
            print(f"[COMPRA PIX] Criando solicitação de warehouse...")
            print(f"  - ID: {solicitacao_id}")
            print(f"  - Equipe: {equipe_id}")
            print(f"  - Peça: {item_id}")
            print(f"  - Status: guardada")
            
            try:
                resultado_salvar = api.db.salvar_solicitacao_peca(
                    id=solicitacao_id,
                    equipe_id=equipe_id,
                    peca_id=item_id,
                    quantidade=1,
                    status='guardada',  # Já está instalada (guardada no warehouse)
                    carro_id=None
                )
                
                if not resultado_salvar:
                    print(f"[COMPRA PIX] ❌ FALHA: salvar_solicitacao_peca retornou False!")
                    return jsonify({'sucesso': False, 'erro': 'Falha ao criar solicitação de warehouse'}), 500
                
                print(f"[COMPRA PIX] ✅ Solicitação de warehouse criada com sucesso!")
            except Exception as e:
                print(f"[COMPRA PIX] ❌ ERRO ao criar solicitação warehouse: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': f'Erro ao criar solicitação: {str(e)}'}), 500
            
            print(f"[COMPRA PIX] Warehouse instalação {item_id} para equipe {equipe.nome}")
        
        elif tipo == 'instalacao_armazem':
            # Instalação de peça do armazém no carro
            print(f"[COMPRA PIX] Criando solicitação de instalação de peça do armazém...")
            print(f"  - Equipe: {equipe_id}")
            print(f"  - Peça: {item_id}")
            print(f"  - Carro: {carro_id}")
            
            try:
                # Criar solicitação de instalação (como em compra normal)
                solicitacao_id = str(uuid.uuid4())
                ok = api.db.salvar_solicitacao_peca(
                    id=solicitacao_id,
                    equipe_id=equipe_id,
                    peca_id=item_id,
                    quantidade=1,
                    status='pendente',
                    carro_id=carro_id
                )
                if not ok:
                    erro = getattr(api.db, '_erro_solicitacao_peca', None)
                    msg = 'Já existe uma solicitação pendente para esta peça neste carro.' if erro == 'duplicada' else 'Falha ao criar solicitação.'
                    return jsonify({'sucesso': False, 'erro': msg}), 400 if erro == 'duplicada' else 500
                print(f"[COMPRA PIX] ✅ Solicitação de instalação {solicitacao_id} criada com sucesso!")
                
            except Exception as e:
                print(f"[COMPRA PIX] ❌ ERRO ao criar solicitação: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': f'Erro ao criar solicitação: {str(e)}'}), 500
        
        elif tipo == 'multiplas_pecas_armazem':
            # Instalação de múltiplas peças do armazém no carro
            print(f"[COMPRA PIX] Criando solicitações de instalação de múltiplas peças do armazém...")
            print(f"  - Equipe: {equipe_id}")
            print(f"  - Carro: {carro_id}")
            print(f"  - Transação: {transacao_id}")
            
            try:
                # Buscar transação para ver quais peças foram incluídas
                conn = api.db._get_conn()
                cursor = conn.cursor()
                
                # Buscar item_name da transação para extrair nomes das peças
                cursor.execute('''
                    SELECT item_nome FROM transacao_pix WHERE id = %s
                ''', (transacao_id,))
                
                trans_result = cursor.fetchone()
                conn.close()
                
                # Extrair informações das peças do item_nome (formato: "nomepeca1, nomepeca2 → Carro")
                item_nome = trans_result['item_nome'] if trans_result else ''
                
                # Carregar peças do armazém desta equipe
                pecas_armazem = api.db.carregar_pecas_armazem_equipe(str(equipe_id))
                pecas_loja = api.db.carregar_pecas_loja()
                
                # Processar APENAS peças SEM pix_id (não pagas)
                pecas_processadas = 0
                for peca_armazem in pecas_armazem:
                    # Se já tem pix_id, pular
                    if peca_armazem.get('pix_id'):
                        print(f"[COMPRA PIX] Peça {peca_armazem['nome']} já foi paga (pix_id: {peca_armazem.get('pix_id')}), ignorando")
                        continue
                    
                    # Buscar peça na loja para ter o ID
                    peca_loja = None
                    for p in pecas_loja:
                        if p.nome.lower() == peca_armazem['nome'].lower() and p.tipo.lower() == peca_armazem['tipo'].lower():
                            peca_loja = p
                            break
                    
                    if not peca_loja:
                        print(f"[COMPRA PIX] Peça {peca_armazem['nome']} não encontrada na loja, ignorando")
                        continue
                    
                    # Criar solicitação de instalação para cada quantidade (não duplica se já existir pendente)
                    for qtd in range(peca_armazem.get('quantidade', 1)):
                        solicitacao_id = str(uuid.uuid4())
                        ok = api.db.salvar_solicitacao_peca(
                            id=solicitacao_id,
                            equipe_id=equipe_id,
                            peca_id=peca_loja.id,
                            quantidade=1,
                            status='pendente',
                            carro_id=carro_id
                        )
                        if ok:
                            pecas_processadas += 1
                            print(f"[COMPRA PIX] ✅ Solicitação {solicitacao_id} criada para {peca_armazem['nome']}")
                
                if pecas_processadas == 0:
                    print(f"[COMPRA PIX] ⚠️ Nenhuma peça foi processada (todas já pagas)")
                else:
                    print(f"[COMPRA PIX] ✅ {pecas_processadas} solicitações criadas com sucesso!")
                
            except Exception as e:
                print(f"[COMPRA PIX] ❌ ERRO ao criar solicitações: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': f'Erro ao criar solicitações: {str(e)}'}), 500
        
        elif tipo == 'multiplas_pecas_armazem_ativo':
            # Instalação de múltiplas peças do armazém no CARRO ATIVO com PIX condicional
            print(f"[COMPRA PIX] Criando solicitações para carro ativo...")
            print(f"  - Equipe: {equipe_id}")
            print(f"  - Carro: {carro_id}")
            
            try:
                # Carregar peças do armazém
                pecas_armazem = api.db.carregar_pecas_armazem_equipe(str(equipe_id))
                pecas_loja = api.db.carregar_pecas_loja()
                
                solicitacoes_criadas = 0
                
                # Processar cada peça
                for peca_armazem in pecas_armazem:
                    # Buscar peça na loja
                    peca_loja = None
                    for p in pecas_loja:
                        if p.nome.lower() == peca_armazem['nome'].lower() and p.tipo.lower() == peca_armazem['tipo'].lower():
                            peca_loja = p
                            break
                    
                    if not peca_loja:
                        continue
                    
                    # Se peça não tem pix_id (precisa pagar), criar solicitação (não duplica se já existir pendente)
                    if not peca_armazem.get('pix_id'):
                        solicitacao_id = str(uuid.uuid4())
                        ok = api.db.salvar_solicitacao_peca(
                            id=solicitacao_id,
                            equipe_id=equipe_id,
                            peca_id=peca_loja.id,
                            quantidade=1,
                            status='pendente',
                            carro_id=carro_id
                        )
                        if ok:
                            solicitacoes_criadas += 1
                        print(f"[COMPRA PIX] ✅ Solicitação criada para {peca_armazem['nome']}")
                
                print(f"[COMPRA PIX] {solicitacoes_criadas} solicitações criadas para carro ativo")
                
            except Exception as e:
                print(f"[COMPRA PIX] ❌ ERRO ao criar solicitações ativo: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': f'Erro ao criar solicitações: {str(e)}'}), 500
        
        elif tipo == 'multiplas_pecas_armazem_ativo_modal':
            try:
                pecas_solicitadas = dados.get('pecas', [])
                transacao_id = dados.get('transacao_id')
                carro_id_modal = carro_id
                if transacao_id:
                    trans = api.db.obter_transacao_pix(transacao_id)
                    if trans:
                        if not carro_id_modal:
                            carro_id_modal = trans.get('carro_id') or trans.get('item_id')
                        if not pecas_solicitadas and trans.get('dados_json'):
                            import json as _json
                            dj = _json.loads(trans['dados_json']) if isinstance(trans['dados_json'], str) else trans['dados_json']
                            pecas_solicitadas = dj.get('pecas', [])
                n, err = _processar_multiplas_pecas_armazem_ativo_confirmacao(equipe_id, carro_id_modal, pecas_solicitadas, transacao_id=transacao_id)
                if err:
                    return jsonify({'sucesso': False, 'erro': err}), 400 if 'duplicada' in err else 500
                print(f"[PIX CONFIRMADO MODAL] ✅ {n} solicitação(ões) pendente(s) criada(s)")
                return jsonify({'sucesso': True, 'mensagem': f'{n} solicitação(ões) criada(s). Aguardando aprovação do administrador.', 'solicitacoes_criadas': n})
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': str(e)}), 500
        
        elif tipo == 'carro_ativacao':
            # Ativação de carro (sem compra, apenas ativação)
            print(f"[COMPRA PIX] Ativando carro...")
            print(f"  - Equipe: {equipe_id}")
            print(f"  - Carro: {item_id}")
            
            try:
                # Obter o carro a ativar
                carro_encontrado = api.db.carregar_carro(item_id)
                if not carro_encontrado:
                    print(f"[COMPRA PIX] ❌ Carro {item_id} não encontrado")
                    return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 404
                
                # Atualizar carro como ativo no banco
                conn = api.db._get_conn()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE carros 
                    SET status = %s, timestamp_ativo = NOW()
                    WHERE id = %s AND equipe_id = %s
                ''', ('ativo', str(item_id), str(equipe_id)))
                # Marcar todas as peças deste carro como pagas (pix_id = transação) para não cobrar de novo
                if api.db._column_exists('pecas', 'pix_id'):
                    cursor.execute('''
                        UPDATE pecas SET pix_id = %s
                        WHERE carro_id = %s AND equipe_id = %s AND instalado = 1
                    ''', (str(transacao_id), str(item_id), str(equipe_id)))
                conn.commit()
                conn.close()
                
                # Criar solicitação de carro para rastreamento
                solicitacao_id = str(uuid.uuid4())
                tipo_carro = f"{item_id}|{carro_encontrado.marca}|{carro_encontrado.modelo}"
                api.db.salvar_solicitacao_carro(
                    id_solicitacao=solicitacao_id,
                    equipe_id=equipe_id,
                    tipo_carro=tipo_carro,
                    status='pendente',
                    data_solicitacao=datetime.now()
                )
                
                print(f"[COMPRA PIX] ✅ Carro {carro_encontrado.marca} {carro_encontrado.modelo} ativado")
                print(f"[COMPRA PIX] ✅ Solicitação {solicitacao_id} criada com status 'pendente'")
                return jsonify({'sucesso': True, 'mensagem': f'Carro {carro_encontrado.marca} {carro_encontrado.modelo} ativado com sucesso'})
                
            except Exception as e:
                print(f"[COMPRA PIX] ❌ ERRO ao ativar carro: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'sucesso': False, 'erro': f'Erro ao ativar carro: {str(e)}'}), 500
        
        else:
            return jsonify({'sucesso': False, 'erro': f'Tipo de compra inválido: {tipo}'}), 400
        
        return jsonify({'sucesso': True, 'mensagem': 'Compra processada com sucesso'})
    
    except Exception as e:
        print(f"[ERRO] Erro ao processar compra PIX: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/comprar-peca-armazem', methods=['POST'])
@requer_login_api
def comprar_peca_armazem():
    """Compra uma peça e a adiciona diretamente ao armazém (sem PIX)"""
    try:
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        dados = request.json
        peca_id = dados.get('peca_id')
        
        if not peca_id:
            return jsonify({'sucesso': False, 'erro': 'peca_id é obrigatório'}), 400
        
        equipe = api.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return jsonify({'sucesso': False, 'erro': 'Equipe não encontrada'}), 404
        
        # Upgrade: peca_id vem como "upgrade_<uuid>"
        is_upgrade = str(peca_id).startswith('upgrade_')
        upgrade_id_real = str(peca_id).replace('upgrade_', '', 1) if is_upgrade else None
        
        peca_encontrada = None
        if is_upgrade and upgrade_id_real:
            u = api.db.buscar_upgrade_por_id(upgrade_id_real)
            if u:
                peca_encontrada = {
                    'id': peca_id,
                    'nome': u['nome'],
                    'tipo': u['peca_tipo'],
                    'preco': u['preco'],
                    'durabilidade': 100,
                    'coeficiente_quebra': 1.0,
                    'descricao': u.get('descricao', ''),
                    'is_upgrade': True,
                    'upgrade_id_real': upgrade_id_real
                }
        if not peca_encontrada and api.loja_pecas and hasattr(api.loja_pecas, 'pecas'):
            for peca_obj in api.loja_pecas.pecas:
                if str(peca_obj.id) == str(peca_id):
                    peca_encontrada = {
                        'id': peca_obj.id,
                        'nome': peca_obj.nome,
                        'tipo': getattr(peca_obj, 'tipo', 'motor'),
                        'preco': peca_obj.preco,
                        'durabilidade': getattr(peca_obj, 'durabilidade', 100),
                        'coeficiente_quebra': getattr(peca_obj, 'coeficiente_quebra', 0.1),
                        'descricao': getattr(peca_obj, 'descricao', ''),
                        'is_upgrade': False
                    }
                    break
        
        if not peca_encontrada:
            return jsonify({'sucesso': False, 'erro': 'Peça ou upgrade não encontrado'}), 404
        
        # Verificar saldo
        preco = float(peca_encontrada['preco'])
        if equipe.doricoins < preco:
            return jsonify({'sucesso': False, 'erro': 'Saldo insuficiente'}), 400
        
        print(f"[ARMAZÉM] Comprando peça para armazém...")
        print(f"  - Equipe: {equipe.nome} (ID: {equipe_id})")
        print(f"  - Peça: {peca_encontrada['nome']} (ID: {peca_id}, Preço: R${preco:.2f})")
        print(f"  - Saldo atual: R${equipe.doricoins:.2f}")
        
        try:
            # 1. DESCONTAR O VALOR DO SALDO
            novo_saldo = equipe.doricoins - preco
            equipe.doricoins = novo_saldo
            
            # Salvar no banco (via salvar_equipe)
            api.db.salvar_equipe(equipe)
            print(f"[ARMAZÉM] ✅ Saldo descontado: R${preco:.2f}")
            print(f"[ARMAZÉM] Novo saldo: R${novo_saldo:.2f}")
            
            # 2. ADICIONAR AO ARMAZÉM (peça ou upgrade)
            if peca_encontrada.get('is_upgrade'):
                resultado_salvar = api.db.adicionar_upgrade_armazem(equipe_id, peca_encontrada['upgrade_id_real'])
            else:
                resultado_salvar = api.db.adicionar_peca_armazem(
                    equipe_id=equipe_id,
                    peca_loja_id=peca_id,
                    nome=peca_encontrada['nome'],
                    tipo=peca_encontrada['tipo'],
                    durabilidade=peca_encontrada['durabilidade'],
                    preco=preco,
                    coeficiente_quebra=peca_encontrada['coeficiente_quebra']
                )
            
            if not resultado_salvar:
                print(f"[ARMAZÉM] ❌ FALHA ao adicionar ao armazém!")
                return jsonify({'sucesso': False, 'erro': 'Falha ao adicionar ao armazém'}), 500
            
            print(f"[ARMAZÉM] ✅ {'Upgrade' if peca_encontrada.get('is_upgrade') else 'Peça'} adicionado ao armazém com sucesso!")
            
            # 3. REGISTRAR NA TABELA DE COMPRAS (HISTÓRICO)
            try:
                conn = api.db._get_conn()
                cursor = conn.cursor()
                
                import uuid
                compra_id = str(uuid.uuid4())
                
                cursor.execute('''
                    INSERT INTO solicitacao_compra 
                    (id, equipe_id, tipo, item_id, quantidade, status, data_criacao, data_processamento)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ''', (compra_id, equipe_id, 'UPGRADE' if peca_encontrada.get('is_upgrade') else 'PEÇA', peca_id, 1, 'CONFIRMADA'))
                
                conn.commit()
                conn.close()
                
                print(f"[ARMAZÉM] ✅ Compra registrada na tabela de histórico com ID: {compra_id}")
            except Exception as e:
                print(f"[ARMAZÉM] ⚠️ Aviso ao registrar compra no histórico: {e}")
                # Não retorna erro, pois a compra foi concluída mesmo assim
            
            return jsonify({
                'sucesso': True,
                'mensagem': f'Peça adicionada ao armazém com sucesso!',
                'peca_nome': peca_encontrada['nome'],
                'preco': preco,
                'novo_saldo': novo_saldo
            })
            
        except Exception as e:
            print(f"[ARMAZÉM] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'sucesso': False, 'erro': f'Erro ao adicionar peça: {str(e)}'}), 500
        
    except Exception as e:
        print(f"[ERRO] Erro ao comprar peça para armazém: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/test/ativar-carro-direto', methods=['POST'])
@requer_login_api
def test_ativar_carro_direto():
    """[E2E] Define o primeiro carro da equipe como ativo (sem PIX). Só disponível com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        equipe_id = obter_equipe_id_request()
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        conn = api.db._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE carros SET status = %s, timestamp_repouso = NOW() WHERE equipe_id = %s',
            ('repouso', equipe_id)
        )
        cursor.execute(
            '''UPDATE carros SET status = %s, timestamp_ativo = NOW()
               WHERE equipe_id = %s ORDER BY numero_carro ASC LIMIT 1''',
            ('ativo', equipe_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Carro ativado (teste)'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/test/criar-solicitacao-peca', methods=['POST'])
def test_criar_solicitacao_peca():
    """[E2E] Cria uma solicitação de peça pendente. Só disponível com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        dados = request.json or {}
        equipe_id = dados.get('equipe_id')
        peca_id = dados.get('peca_id')
        carro_id = dados.get('carro_id')
        if not equipe_id or not peca_id or not carro_id:
            return jsonify({'erro': 'equipe_id, peca_id e carro_id obrigatórios'}), 400
        sol_id = str(uuid.uuid4())
        ok = api.db.salvar_solicitacao_peca(sol_id, equipe_id, peca_id, 1, 'pendente', carro_id)
        if not ok:
            erro = getattr(api.db, '_erro_solicitacao_peca', None)
            msg = 'Já existe uma solicitação pendente para esta peça neste carro.' if erro == 'duplicada' else 'Falha ao salvar solicitação'
            return jsonify({'erro': msg}), 400 if erro == 'duplicada' else 500
        return jsonify({'sucesso': True, 'solicitacao_id': sol_id})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/test/criar-solicitacao-carro', methods=['POST'])
def test_criar_solicitacao_carro():
    """[E2E] Cria uma solicitação de ativação de carro pendente. Só disponível com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        dados = request.json or {}
        equipe_id = dados.get('equipe_id')
        carro_id = dados.get('carro_id')
        carro_anterior_id = dados.get('carro_anterior_id')
        if not equipe_id or not carro_id:
            return jsonify({'erro': 'equipe_id e carro_id obrigatórios'}), 400
        sol_id = api.db.criar_solicitacao_ativacao_carro(equipe_id, carro_id, carro_anterior_id)
        if not sol_id:
            return jsonify({'erro': 'Falha ao criar solicitação'}), 500
        return jsonify({'sucesso': True, 'solicitacao_id': sol_id})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/test/atualizar-saldo-pix', methods=['POST'])
def test_atualizar_saldo_pix():
    """[E2E] Adiciona saldo_pix à equipe. Só disponível com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        dados = request.json or {}
        equipe_id = dados.get('equipe_id')
        valor = float(dados.get('valor', 0))
        if not equipe_id:
            return jsonify({'erro': 'equipe_id obrigatório'}), 400
        api.db.atualizar_saldo_pix(equipe_id, valor)
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/test/inscrever-candidato-piloto', methods=['POST'])
def test_inscrever_candidato_piloto():
    """[E2E] Inscreve piloto como candidato para equipe em etapa. Só disponível com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        dados = request.json or {}
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id')
        piloto_id = dados.get('piloto_id')
        piloto_nome = dados.get('piloto_nome', '')
        if not all([etapa_id, equipe_id, piloto_id]):
            return jsonify({'erro': 'etapa_id, equipe_id e piloto_id obrigatórios'}), 400
        resultado = api.db.inscrever_piloto_candidato_etapa(etapa_id, equipe_id, piloto_id, piloto_nome)
        if not resultado.get('sucesso'):
            return jsonify(resultado), 400
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/api/test/server-date', methods=['GET'])
def test_server_date():
    """[E2E] Retorna a data atual do servidor (para testes usarem data correta). Só com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    from datetime import datetime
    return jsonify({'data': datetime.now().date().isoformat()})


@app.route('/api/test/garantir-pecas-etapa', methods=['POST'])
def test_garantir_pecas_etapa():
    """[E2E] Garante que todos os carros das participações da etapa tenham peças para desgaste. Só com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        dados = request.json or {}
        etapa_id = dados.get('etapa_id')
        if not etapa_id:
            return jsonify({'erro': 'etapa_id obrigatório'}), 400
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT DISTINCT carro_id FROM participacoes_etapas WHERE etapa_id = %s AND carro_id IS NOT NULL',
            (etapa_id,)
        )
        rows = cursor.fetchall()
        inseridas = 0
        for row in rows:
            carro_id = row.get('carro_id')
            if not carro_id:
                continue
            cursor.execute(
                'SELECT COUNT(*) as n FROM pecas WHERE carro_id = %s AND instalado = 1',
                (carro_id,)
            )
            if cursor.fetchone()['n'] > 0:
                continue
            pecas_tipos = [
                ('motor', 'Motor Padrão', 0.35),
                ('cambio', 'Cambio Padrão', 0.4),
                ('suspensao', 'Suspensao Padrão', 0.45),
                ('kit_angulo', 'Kit Ângulo Padrão', 0.3),
                ('diferencial', 'Diferencial Padrão', 0.4),
            ]
            for tipo, nome, coef in pecas_tipos:
                peca_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO pecas (id, carro_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado)
                    VALUES (%s, %s, %s, %s, 100, 100, 100, %s, 1)
                ''', (peca_id, carro_id, nome, tipo, coef))
                inseridas += 1
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'sucesso': True, 'pecas_inseridas': inseridas})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/test/salvar-notas-etapa', methods=['POST'])
def test_salvar_notas_etapa():
    """[E2E] Define notas para múltiplas equipes de uma etapa de uma vez. Só disponível com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        dados = request.json or {}
        etapa_id = dados.get('etapa_id')
        notas_list = dados.get('notas', [])  # [{equipe_id, nota_linha, nota_angulo, nota_estilo}, ...]
        if not etapa_id or not notas_list:
            return jsonify({'erro': 'etapa_id e notas[] obrigatórios'}), 400
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        for n in notas_list:
            equipe_id = n.get('equipe_id')
            nota_linha = int(n.get('nota_linha', 0))
            nota_angulo = int(n.get('nota_angulo', 0))
            nota_estilo = int(n.get('nota_estilo', 0))
            if not equipe_id:
                continue
            cursor.execute(
                'SELECT piloto_id FROM participacoes_etapas WHERE etapa_id = %s AND equipe_id = %s LIMIT 1',
                (etapa_id, equipe_id)
            )
            p = cursor.fetchone()
            piloto_id = p['piloto_id'] if p and p.get('piloto_id') else None
            cursor.execute(
                'SELECT id_piloto, id_equipe FROM volta WHERE id_etapa = %s AND id_equipe = %s LIMIT 1',
                (etapa_id, equipe_id)
            )
            existe = cursor.fetchone()
            if existe:
                cursor.execute('''
                    UPDATE volta SET nota_linha = %s, nota_angulo = %s, nota_estilo = %s, status = 'finalizado'
                    WHERE id_etapa = %s AND id_equipe = %s
                ''', (nota_linha, nota_angulo, nota_estilo, etapa_id, equipe_id))
            else:
                cursor.execute('''
                    INSERT INTO volta (id_piloto, id_equipe, id_etapa, nota_linha, nota_angulo, nota_estilo, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'finalizado')
                ''', (piloto_id, equipe_id, etapa_id, nota_linha, nota_angulo, nota_estilo))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/test/quebrar-carro-equipe-etapa', methods=['POST'])
def test_quebrar_carro_equipe_etapa():
    """[E2E] Zera durabilidade das peças do carro da equipe na etapa (para testar By run). Só com TEST_E2E=1."""
    if os.environ.get('TEST_E2E') != '1':
        return jsonify({'erro': 'Não disponível'}), 404
    try:
        dados = request.json or {}
        etapa_id = dados.get('etapa_id')
        equipe_id = dados.get('equipe_id')
        if not etapa_id or not equipe_id:
            return jsonify({'erro': 'etapa_id e equipe_id obrigatórios'}), 400
        conn = api.db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT carro_id FROM participacoes_etapas WHERE etapa_id = %s AND equipe_id = %s LIMIT 1',
            (etapa_id, equipe_id)
        )
        row = cursor.fetchone()
        if not row or not row.get('carro_id'):
            conn.close()
            return jsonify({'erro': 'Carro não encontrado'}), 404
        carro_id = row['carro_id']
        cursor.execute('''
            UPDATE pecas SET durabilidade_atual = 0
            WHERE carro_id = %s AND instalado = 1 AND tipo = 'motor' LIMIT 1
        ''', (carro_id,))
        n = cursor.rowcount
        if n == 0:
            cursor.execute('''
                UPDATE pecas SET durabilidade_atual = 0
                WHERE carro_id = %s AND instalado = 1 LIMIT 1
            ''', (carro_id,))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': f'1 peça do carro da equipe {equipe_id} quebrada (carro inoperante)'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/test-pecas')
def test_pecas():
    return jsonify({'status': 'ok', 'test': 'pecas endpoint works'})

# ============ ROTAS DE COMISSÕES ============

@app.route('/api/admin/configuracoes', methods=['GET'])
def get_configuracoes():
    """Retorna as configurações de comissão"""
    try:
        configs = api.db.listar_configuracoes()
        
        return jsonify({
            'configuracoes': configs
        })
    except Exception as e:
        print(f"[ERRO] Erro ao carregar configurações: {e}")
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/configuracoes', methods=['PUT'])
def atualizar_configuracoes():
    """Atualiza as configurações de comissão"""
    try:
        dados = request.json
        chave = dados.get('chave')
        valor = dados.get('valor')
        descricao = dados.get('descricao', '')
        
        if not chave or valor is None:
            return jsonify({'erro': 'Chave e valor são obrigatórios'}), 400
        
        sucesso = api.db.salvar_configuracao(chave, str(valor), descricao)
        
        if sucesso:
            return jsonify({'sucesso': True, 'mensagem': f'Configuração {chave} atualizada'})
        else:
            return jsonify({'erro': 'Erro ao atualizar configuração'}), 500
    except Exception as e:
        print(f"[ERRO] Erro ao atualizar configurações: {e}")
        return jsonify({'erro': str(e)}), 400

@app.route('/api/admin/transacoes-pix', methods=['GET'])
@requer_admin
def listar_transacoes_pix():
    """Lista todas as transações PIX realizadas pelos pilotos (histórico de pagamentos)"""
    try:
        tipo = request.args.get('tipo')  # filtro por tipo_item
        filtro_mes = request.args.get('mes')  # 'este_mes' ou vazio para todos
        filtro_status = request.args.get('status')  # aprovado, pendente, recusado, cancelado
        limit = min(int(request.args.get('limit', 200)), 500)
        
        # Buscar transações PIX do banco
        conn = api.db._get_conn()
        cursor = conn.cursor()
        
        query = """SELECT id, mercado_pago_id, equipe_nome, tipo_item, item_nome, valor_item, valor_taxa, valor_total, status, data_criacao
                   FROM transacoes_pix WHERE 1=1"""
        params = []
        
        if tipo:
            query += " AND tipo_item = %s"
            params.append(tipo)
        
        if filtro_mes == 'este_mes':
            query += " AND MONTH(data_criacao) = MONTH(NOW()) AND YEAR(data_criacao) = YEAR(NOW())"
        
        if filtro_status:
            query += " AND status = %s"
            params.append(filtro_status)
        
        query += " ORDER BY data_criacao DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        transacoes = []
        for r in rows:
            valor_item = float(r[5] or 0)
            valor_taxa = float(r[6] or 0)
            valor_total = float(r[7]) if r[7] is not None else valor_item + valor_taxa
            data_criacao = r[9]
            transacoes.append({
                'id': r[0],
                'mercado_pago_id': r[1],
                'equipe_nome': r[2],
                'tipo': r[3],
                'tipo_item': r[3],
                'item_nome': r[4],
                'valor_item': valor_item,
                'valor_taxa': valor_taxa,
                'valor_total': valor_total,
                'status': r[8] or 'pendente',
                'data_transacao': data_criacao.isoformat() if hasattr(data_criacao, 'isoformat') else str(data_criacao),
                'data_criacao': data_criacao.isoformat() if hasattr(data_criacao, 'isoformat') else str(data_criacao),
            })
        
        return jsonify({
            'transacoes': transacoes,
            'comissoes': transacoes,
            'total': sum(t['valor_total'] for t in transacoes)
        })
    except Exception as e:
        print(f"[ERRO] Erro ao listar comissões: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 400

# ============ INICIALIZAÇÃO DE CONFIGURAÇÕES =====
def inicializar_configuracoes_padrao():
    """Inicializa as configurações padrão de comissão se não existirem"""
    configs_padrao = {
        'taxa_transferencia': ('10', 'Taxa de transferência entre equipes (em %)'),
        'comissao_carro': ('10', 'Comissão para cada carro comprado (em reais)'),
        'comissao_peca': ('10', 'Comissão para cada peça comprada (em reais)'),
        'comissao_warehouse': ('50', 'Comissão warehouse (em reais)'),
        'preco_instalacao_warehouse': ('10', 'Preço para instalar peça do armazém (em reais)'),
        'valor_instalacao_peca': ('10', 'Valor por peça ao ativar carro (peças não pagas)'),
        'valor_ativacao_carro': ('10', 'Valor para troca/ativação de carro (em reais)'),
        'valor_etapa': ('20', 'Valor para participar de uma etapa (em reais)'),
        'dado_dano': ('20', 'Número de faces do dado de dano (ex: 20 = D20) nas passadas'),
        'participacao_etapa_A': ('3000', 'Doricoins por participar da etapa (Série A)'),
        'participacao_etapa_B': ('2000', 'Doricoins por participar da etapa (Série B)'),
        'vitoria_batalha_A': ('1500', 'Doricoins por vitória em batalha a partir da fase 2 (Série A)'),
        'vitoria_batalha_B': ('1000', 'Doricoins por vitória em batalha a partir da fase 2 (Série B)'),
        'premio_campeonato_1': ('0', 'Premiação final campeonato - 1º lugar (doricoins)'),
        'premio_campeonato_2': ('0', 'Premiação final campeonato - 2º lugar (doricoins)'),
        'premio_campeonato_3': ('0', 'Premiação final campeonato - 3º lugar (doricoins)'),
        'premio_campeonato_4': ('0', 'Premiação final campeonato - 4º lugar (doricoins)'),
        'premio_campeonato_5': ('0', 'Premiação final campeonato - 5º lugar (doricoins)'),
    }
    
    try:
        for chave, (valor, descricao) in configs_padrao.items():
            # Verificar se a configuração já existe
            config_existente = api.db.obter_configuracao(chave)
            if not config_existente:
                api.db.salvar_configuracao(chave, valor, descricao)
                print(f"[CONFIG] Inicializada: {chave} = {valor}")
            else:
                print(f"[CONFIG] Já existe: {chave} = {config_existente}")
    except Exception as e:
        print(f"[AVISO] Erro ao inicializar configurações: {e}")

# ====== ENDPOINT APELIDO CARRO ======
@app.route('/api/carro/<carro_id>/apelido', methods=['PUT'])
def atualizar_apelido_carro(carro_id):
    """Atualizar apelido de um carro"""
    try:
        equipe_id = session.get('equipe_id')
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        dados = request.json
        novo_apelido = str(dados.get('apelido', '')).strip()
        
        # Validar que o carro pertence à equipe
        conn = api.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM carros WHERE id = %s AND equipe_id = %s', (carro_id, equipe_id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 404
        
        # Atualizar apelido
        cursor.execute('UPDATE carros SET apelido = %s WHERE id = %s', (novo_apelido if novo_apelido else None, carro_id))
        conn.commit()
        conn.close()
        
        return jsonify({'sucesso': True, 'novo_apelido': novo_apelido}), 200
    except Exception as e:
        print(f'[APELIDO] Erro ao atualizar: {e}')
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

# ====== ENDPOINT IMAGEM DO CARRO ======
UPLOAD_CARROS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'carros')
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

@app.route('/api/carro/<carro_id>/imagem', methods=['POST'])
def upload_imagem_carro(carro_id):
    """Envia imagem do carro (dono da equipe). Arquivo salvo em static/uploads/carros/"""
    try:
        equipe_id = session.get('equipe_id') or request.headers.get('X-Equipe-ID')
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401

        # Validar que o carro pertence à equipe
        conn = api.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM carros WHERE id = %s AND equipe_id = %s', (carro_id, str(equipe_id)))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 404
        conn.close()

        f = request.files.get('imagem')
        if not f or f.filename == '':
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400

        ext = (f.filename.rsplit('.', 1)[-1] or '').lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            ext = 'jpg'
        safe_name = f"{carro_id}.{ext}"
        os.makedirs(UPLOAD_CARROS_DIR, exist_ok=True)
        path_dest = os.path.join(UPLOAD_CARROS_DIR, safe_name)
        f.save(path_dest)

        imagem_url = f"/static/uploads/carros/{safe_name}"
        if api.db._column_exists('carros', 'imagem_url'):
            conn = api.db._get_conn()
            cur = conn.cursor()
            cur.execute('UPDATE carros SET imagem_url = %s WHERE id = %s', (imagem_url, carro_id))
            conn.commit()
            conn.close()

        return jsonify({'sucesso': True, 'imagem_url': imagem_url}), 200
    except Exception as e:
        print(f'[IMAGEM CARRO] Erro: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

# ====== ENDPOINT REMOVER PEÇA DO CARRO ======
@app.route('/api/remover-peca-carro', methods=['POST'])
def remover_peca_carro():
    """Remove uma peça de um carro e adiciona ao armazém ou move para outro carro"""
    try:
        # Tentar obter equipe_id da session ou do header
        equipe_id = session.get('equipe_id') or request.headers.get('X-Equipe-ID')
        if not equipe_id:
            return jsonify({'sucesso': False, 'erro': 'Não autenticado'}), 401
        
        dados = request.json
        carro_id = dados.get('carro_id')
        tipo_peca = dados.get('tipo_peca')  # motor, cambio, suspensao, diferencial, kit_angulo
        novo_carro_id = dados.get('novo_carro_id')  # Se None, vai para armazém; se setado, vai para outro carro
        
        print(f'[REMOVER PEÇA] Carro: {carro_id}, Tipo: {tipo_peca}, Novo Carro: {novo_carro_id}')
        
        # Validar que o carro pertence à equipe
        conn = api.db._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM carros WHERE id = %s AND equipe_id = %s', (carro_id, equipe_id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Carro não encontrado'}), 404
        
        # Se novo_carro_id é fornecido, validar que também pertence à equipe
        if novo_carro_id:
            cursor.execute('SELECT id FROM carros WHERE id = %s AND equipe_id = %s', (novo_carro_id, equipe_id))
            if not cursor.fetchone():
                conn.close()
                return jsonify({'sucesso': False, 'erro': 'Carro de destino não encontrado'}), 404
            
            # Se o carro de destino já tem uma peça deste tipo, ela será desinstalada
            # (removida para o armazém) antes de instalar a nova
            cursor.execute('''
                SELECT id FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1
                LIMIT 1
            ''', (novo_carro_id, tipo_peca))
            peca_antiga_destino = cursor.fetchone()
            if peca_antiga_destino:
                print(f'[REMOVER PEÇA] Desinstalando peça antiga do destino: {peca_antiga_destino[0]}')
                # Desinstalar peça antiga: enviar para armazém
                cursor.execute('''
                    UPDATE pecas 
                    SET carro_id = NULL, instalado = 0
                    WHERE id = %s
                ''', (peca_antiga_destino[0],))

        
        # 1. Buscar a peça BASE instalada deste tipo (não upgrade), para mover base + upgrades juntos
        if api.db._column_exists('pecas', 'upgrade_id'):
            cursor.execute('''
                SELECT id, peca_loja_id FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1
                  AND (upgrade_id IS NULL OR upgrade_id = '')
                LIMIT 1
            ''', (carro_id, tipo_peca))
        else:
            cursor.execute('''
                SELECT id, peca_loja_id FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1
                LIMIT 1
            ''', (carro_id, tipo_peca))
        
        peca_instalada = cursor.fetchone()
        if not peca_instalada:
            conn.close()
            return jsonify({'sucesso': False, 'erro': f'Nenhuma peça {tipo_peca} instalada'}), 404
        
        peca_id, peca_loja_id = peca_instalada
        print(f'[REMOVER PEÇA] Movendo peça base {peca_id} (e upgrades) para {novo_carro_id or "armazém"}')
        
        # 2. Mover peça base E todas com instalado_em_peca_id = peca_id (upgrades desta peça)
        if novo_carro_id:
            cursor.execute('''
                UPDATE pecas SET carro_id = %s, instalado = 1, pix_id = NULL WHERE id = %s
            ''', (novo_carro_id, peca_id))
            if api.db._column_exists('pecas', 'instalado_em_peca_id'):
                cursor.execute('''
                    UPDATE pecas SET carro_id = %s, instalado = 1
                    WHERE instalado_em_peca_id = %s
                ''', (novo_carro_id, peca_id))
            print(f'[REMOVER PEÇA] Peça base e upgrades movidos para carro {novo_carro_id}')
        else:
            cursor.execute('''
                UPDATE pecas SET carro_id = NULL, instalado = 0, pix_id = NULL WHERE id = %s
            ''', (peca_id,))
            if api.db._column_exists('pecas', 'instalado_em_peca_id'):
                cursor.execute('''
                    UPDATE pecas SET carro_id = NULL, instalado = 0
                    WHERE instalado_em_peca_id = %s
                ''', (peca_id,))
            print(f'[REMOVER PEÇA] Peça base e upgrades movidos para armazém')
        
        conn.commit()
        conn.close()
        
        print(f'[REMOVER PEÇA] Peça movida com sucesso!')
        return jsonify({'sucesso': True, 'mensagem': 'Peça movida com sucesso!'}), 200
    
    except Exception as e:
        print(f'[REMOVER PEÇA] Erro: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 400


# ============ ROTAS ADMIN - MIGRATION =============

@app.route('/api/admin/migration/remove-colunas-carros', methods=['POST'])
@requer_admin
def migration_remove_colunas_carros():
    """Remove colunas redundantes da tabela carros"""
    try:
        print("[MIGRATION] Iniciando remoção de colunas da tabela carros...")
        
        # Colunas a remover: motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id
        colunas = ['motor_id', 'cambio_id', 'suspensao_id', 'kit_angulo_id', 'diferencial_id']
        
        conn = api.db._get_conn()
        cursor = conn.cursor()
        
        removidas = []
        erros = []
        
        for coluna in colunas:
            try:
                sql = f"ALTER TABLE carros DROP COLUMN {coluna}"
                print(f"[MIGRATION] Executando: {sql}")
                cursor.execute(sql)
                removidas.append(coluna)
                print(f"[MIGRATION] ✓ Coluna {coluna} removida com sucesso")
            except Exception as e:
                erro_msg = str(e)
                if 'Unknown column' in erro_msg:
                    print(f"[MIGRATION] ⚠ Coluna {coluna} não existe (já foi removida)")
                    removidas.append(coluna)
                else:
                    erros.append({'coluna': coluna, 'erro': erro_msg})
                    print(f"[MIGRATION] ✗ Erro ao remover {coluna}: {erro_msg}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[MIGRATION] Processo finalizado. Removidas: {removidas}, Erros: {len(erros)}")
        
        return jsonify({
            'sucesso': len(erros) == 0,
            'removidas': removidas,
            'erros': erros,
            'mensagem': f'{len(removidas)} coluna(s) removida(s) com sucesso'
        }), 200 if len(erros) == 0 else 206
        
    except Exception as e:
        print(f"[MIGRATION] Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'mensagem': 'Erro ao executar migration'
        }), 500


# ==================== CAMPEONATOS E ETAPAS (registrar sempre, para testes e flask run) ====================

@app.route('/api/admin/criar-campeonato', methods=['POST'])
def criar_campeonato():
    """Cria um novo campeonato"""
    dados = request.json or {}
    try:
        campeonato_id = str(uuid.uuid4())
        nome = dados.get('nome')
        descricao = dados.get('descricao', '')
        serie = dados.get('serie')
        numero_etapas = int(dados.get('numero_etapas', 5))
        if not nome or not serie:
            return jsonify({'sucesso': False, 'erro': 'Nome e série são obrigatórios'}), 400
        if api.db.criar_campeonato(campeonato_id, nome, descricao, serie, numero_etapas):
            return jsonify({'sucesso': True, 'campeonato_id': campeonato_id})
        return jsonify({'sucesso': False, 'erro': 'Erro ao criar campeonato'}), 500
    except Exception as e:
        print(f"[CRIAR CAMPEONATO] Erro: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/admin/listar-campeonatos', methods=['GET'])
def listar_campeonatos():
    """Lista campeonatos com filtros opcionais. Retorna todos para ver colocações e histórico."""
    try:
        serie = request.args.get('serie')
        campeonatos = api.db.listar_campeonatos(serie=serie)
        # Marcar se está em andamento ou concluído
        conn = api.db._get_conn()
        cur = conn.cursor(dictionary=True)
        for c in campeonatos:
            cid = c.get('id', '')
            cur.execute('SELECT COUNT(*) as n FROM etapas WHERE campeonato_id = %s AND status IN ("concluida", "encerrada")', (cid,))
            concluidas = (cur.fetchone() or {}).get('n') or 0
            total = int(c.get('numero_etapas') or 999)
            c['em_andamento'] = concluidas < total
        cur.close()
        conn.close()
        return jsonify({'campeonatos': campeonatos})
    except Exception as e:
        print(f"[LISTAR CAMPEONATOS] Erro: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/admin/cadastrar-etapa', methods=['POST'])
def cadastrar_etapa():
    """Cadastra uma nova etapa"""
    dados = request.json or {}
    try:
        etapa_id = str(uuid.uuid4())
        campeonato_id = dados.get('campeonato_id')
        numero = int(dados.get('numero', 1))
        nome = dados.get('nome', 'Etapa')
        descricao = dados.get('descricao', '')
        data_etapa = dados.get('data_etapa')
        hora_etapa = dados.get('hora_etapa')
        serie = dados.get('serie', '')
        if not campeonato_id or not data_etapa or not hora_etapa or not serie:
            return jsonify({'sucesso': False, 'erro': 'Campeonato, data, hora e série são obrigatórios'}), 400
        if api.db.cadastrar_etapa(etapa_id, campeonato_id, numero, nome, descricao, data_etapa, hora_etapa, serie):
            return jsonify({'sucesso': True, 'etapa_id': etapa_id})
        return jsonify({'sucesso': False, 'erro': 'Erro ao cadastrar etapa'}), 500
    except Exception as e:
        print(f"[CADASTRO ETAPA] Erro: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/admin/listar-etapas', methods=['GET'])
def listar_etapas_filtradas():
    """Lista etapas com filtros opcionais"""
    try:
        serie = request.args.get('serie')
        status = request.args.get('status')
        etapas = api.db.listar_etapas(serie=serie, status=status)
        return jsonify(etapas if isinstance(etapas, list) else [])
    except Exception as e:
        print(f"[LISTAR ETAPAS] Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# Log no startup (visível no Docker com gunicorn/uwsgi) para confirmar rotas
def _log_rotas_startup():
    print("[APP] ========== ROTAS INSTALAR / GARAGEM (startup) ==========", flush=True)
    alvo = "/api/instalar-multiplas-pecas-no-carro-ativo"
    encontrada = False
    for r in app.url_map.iter_rules():
        if 'instalar' in r.rule or 'garagem' in r.rule:
            met = sorted(r.methods - {'HEAD', 'OPTIONS'})
            print(f"[APP]   {r.rule} -> {met}", flush=True)
            if r.rule == alvo and 'POST' in r.methods:
                encontrada = True
    if not encontrada:
        print(f"[APP] ATENÇÃO: Rota POST {alvo} NAO esta no url_map (rebuild da imagem?)", flush=True)
    print("[APP] ==========================================================", flush=True)
_log_rotas_startup()


if __name__ == '__main__':
    import atexit
    import threading
    import io
    
    # Suprimir erros de thread ao encerrar
    original_stderr = sys.stderr
    
    def cleanup_on_exit():
        """Encerrar recursos corretamente ao sair"""
        try:
            # Redirecionar stderr para evitar mensagens de lock
            sys.stderr = io.StringIO()
            
            # Parar monitoramento de compras se existir
            if hasattr(api, 'monitor_compras') and api.monitor_compras:
                try:
                    api.monitor_compras.parar()
                except:
                    pass
            
            # Fechar conexões do banco
            if hasattr(api, 'db'):
                try:
                    # Não há close explícito, mas podemos tentar
                    pass
                except:
                    pass
            
            # Aguardar threads daemon completarem
            active_threads = threading.enumerate()
            for thread in active_threads:
                if thread.daemon and thread != threading.current_thread():
                    try:
                        thread.join(timeout=0.3)
                    except:
                        pass
            
        except:
            pass
        finally:
            sys.stderr = original_stderr
    
    # Registrar função de limpeza
    atexit.register(cleanup_on_exit)
    
    print("\n" + "="*70)
    print("WEB SYSTEM GRANPIX")
    print("="*70)
    print("\nOpening at http://localhost:5000")
    print("   Team Login: Team ID + password (default: 123456)")
    print("   Admin Login: Password = admin123")
    print("   Press CTRL+C to stop\n")
    
    # Inicializar configurações padrão
    print("[INICIALIZAÇÃO] Verificando configurações de comissão...")
    inicializar_configuracoes_padrao()
    
    print("\n[ROTAS REGISTRADAS - API]")
    # Campeonatos e etapas já registrados no nível do módulo (acima)
    
    @app.route('/api/admin/campeonato/<campeonato_id>', methods=['GET'])
    def obter_campeonato(campeonato_id):
        """Obtém um campeonato específico"""
        try:
            campeonato = api.db.obter_campeonato(campeonato_id)
            if campeonato:
                return jsonify(campeonato)
            else:
                return jsonify({}), 404
        except Exception as e:
            print(f"[OBTER CAMPEONATO] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500
    
    @app.route('/api/admin/deletar-campeonato', methods=['POST'])
    def deletar_campeonato():
        """Deleta um campeonato"""
        dados = request.json
        try:
            campeonato_id = dados.get('campeonato_id')
            if not campeonato_id:
                return jsonify({'sucesso': False, 'erro': 'ID do campeonato obrigatório'}), 400
            
            if api.db.deletar_campeonato(campeonato_id):
                return jsonify({'sucesso': True})
            else:
                return jsonify({'sucesso': False, 'erro': 'Campeonato não encontrado'}), 404
        except Exception as e:
            print(f"[DELETAR CAMPEONATO] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    @app.route('/api/admin/pontuacoes-campeonato/<campeonato_id>', methods=['GET'])
    def obter_pontuacoes_campeonato(campeonato_id):
        """Obtém as pontuações de um campeonato"""
        try:
            pontuacoes = api.db.obter_pontuacoes_campeonato(campeonato_id)
            return jsonify({
                'sucesso': True,
                'pontuacoes': pontuacoes
            })
        except Exception as e:
            print(f"[OBTER PONTUACOES] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500
    
    @app.route('/api/admin/atualizar-pontuacao', methods=['POST'])
    def atualizar_pontuacao():
        """Atualiza os pontos de uma equipe em um campeonato"""
        dados = request.json
        try:
            campeonato_id = dados.get('campeonato_id')
            equipe_id = dados.get('equipe_id')
            pontos = int(dados.get('pontos', 0))
            
            if not campeonato_id or not equipe_id:
                return jsonify({'sucesso': False, 'erro': 'Campeonato e equipe obrigatórios'}), 400
            
            if api.db.atualizar_pontuacao_equipe(campeonato_id, equipe_id, pontos):
                return jsonify({'sucesso': True})
            else:
                return jsonify({'sucesso': False, 'erro': 'Erro ao atualizar pontuação'}), 500
        except Exception as e:
            print(f"[ATUALIZAR PONTUACAO] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500
    
    @app.route('/api/admin/atualizar-colocacoes/<campeonato_id>', methods=['POST'])
    def atualizar_colocacoes(campeonato_id):
        """Atualiza as colocações de um campeonato"""
        try:
            if api.db.atualizar_colocacoes_campeonato(campeonato_id):
                pontuacoes = api.db.obter_pontuacoes_campeonato(campeonato_id)
                return jsonify({
                    'sucesso': True,
                    'pontuacoes': pontuacoes
                })
            else:
                return jsonify({'sucesso': False, 'erro': 'Erro ao atualizar colocações'}), 500
        except Exception as e:
            print(f"[ATUALIZAR COLOCACOES] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    # Cadastrar-etapa e listar-etapas já registrados no nível do módulo
    
    @app.route('/api/proxima-etapa/<serie>', methods=['GET'])
    def proxima_etapa(serie):
        """Obter próxima etapa para uma série"""
        try:
            etapa = api.db.obter_proxima_etapa(serie)
            if etapa:
                # Converter datetime para string se necessário
                if 'data_etapa' in etapa and hasattr(etapa['data_etapa'], 'isoformat'):
                    etapa['data_etapa'] = etapa['data_etapa'].isoformat()
                if 'hora_etapa' in etapa and hasattr(etapa['hora_etapa'], 'isoformat'):
                    etapa['hora_etapa'] = etapa['hora_etapa'].isoformat()
                return jsonify(etapa)
            else:
                return jsonify({}), 404
        except Exception as e:
            print(f"[PRÓXIMA ETAPA] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500
    
    @app.route('/api/validar-pecas-etapa', methods=['POST'])
    def validar_pecas_etapa():
        """Valida se o carro tem todas as peças para participar de etapa"""
        dados = request.json
        try:
            carro_id = dados.get('carro_id')
            equipe_id = dados.get('equipe_id')
            
            resultado = api.db.validar_pecas_carro(carro_id, equipe_id)
            return jsonify(resultado)
        except Exception as e:
            print(f"[VALIDAR PEÇAS] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500
    
    @app.route('/api/inscrever-etapa', methods=['POST'])
    def inscrever_etapa():
        """Inscreve equipe em uma etapa"""
        dados = request.json
        try:
            etapa_id = dados.get('etapa_id')
            equipe_id = dados.get('equipe_id')
            carro_id = dados.get('carro_id')
            
            if not all([etapa_id, equipe_id, carro_id]):
                return jsonify({'sucesso': False, 'erro': 'Parâmetros obrigatórios faltando'}), 400
            
            # Validar peças primeiro
            validacao = api.db.validar_pecas_carro(carro_id, equipe_id)
            if not validacao['valido']:
                pecas_texto = ', '.join([p.capitalize() for p in validacao['pecas_faltando']])
                return jsonify({
                    'sucesso': False, 
                    'erro': f'Peças faltando: {pecas_texto}',
                    'pecas_faltando': validacao['pecas_faltando']
                }), 400
            
            # Inscrever
            inscricao_id = str(uuid.uuid4())
            if api.db.inscrever_equipe_etapa(inscricao_id, etapa_id, equipe_id, carro_id):
                return jsonify({'sucesso': True, 'inscricao_id': inscricao_id})
            else:
                return jsonify({'sucesso': False, 'erro': 'Erro ao inscrever'}), 500
        except Exception as e:
            print(f"[INSCREVER ETAPA] Erro: {e}")
            return jsonify({'sucesso': False, 'erro': str(e)}), 500

    for rule in app.url_map.iter_rules():
        if 'api' in rule.rule:
            methods = list(rule.methods - {'OPTIONS', 'HEAD'})
            print(f"  {rule.rule:50} -> {methods}")
    print()
    
    try:
        host = os.environ.get("FLASK_RUN_HOST", "localhost")
        port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
        debug = os.environ.get("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
        app.run(debug=debug, host=host, port=port, use_reloader=debug)
    except KeyboardInterrupt:
        print("\n[ENCERRAMENTO] Encerrando aplicação...")
        cleanup_on_exit()
    except Exception as e:
        print(f"\n[ERRO ENCERRAMENTO] {e}")
        cleanup_on_exit()

