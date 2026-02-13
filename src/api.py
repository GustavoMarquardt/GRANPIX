"""
API Principal do Sistema GRANPIX
Interface para gerenciar o sistema completo
"""
from typing import List, Optional, Dict, Tuple
from .models import Piloto, Equipe, Batalha, Etapa, ResultadoBatalha, Carro, Peca
from .database import DatabaseManager
from .team_manager import GerenciadorEquipes
from .battle_system import SistemaBatalha, SistemaDesgaste
from .loja import Loja, PecaMotor
from .loja_carros import LojaCarros
from .loja_pecas import LojaPecas
from .oficina import Oficina
from datetime import datetime
import uuid


class APIGranpix:
    """API Principal do Sistema GRANPIX"""
    
    def __init__(self, db_path: str = "data/granpix.db"):
        self.db = DatabaseManager(db_path)
        self.gerenciador = GerenciadorEquipes(self.db)
        self.batalhas = SistemaBatalha()
        self.etapas_ativas: Dict[int, Etapa] = {}
        self.loja = Loja()
        self.loja_carros = LojaCarros(self.db)
        self.loja_pecas = LojaPecas(self.db)
        self.oficina = Oficina(self.loja)
        
        # Atributos para exportação e monitoramento
        self.auto_export_monitor = None
        self.auto_export_habilitado = False
        self.exportador_excel = None
        self.processador_compras = None
        self.monitor_compras = None
        self.etapa_atual = 1
    
    # ============ EQUIPES ============
    
    def criar_equipe_novo(self, nome: str, doricoins_iniciais: float = 1000.0, senha: str = None, serie: str = 'A') -> Equipe:
        """Cria uma nova equipe no sistema"""
        return self.gerenciador.criar_equipe(nome, doricoins_iniciais, senha, serie)
    
    def listar_todas_equipes(self) -> List[Equipe]:
        """Lista todas as equipes cadastradas"""
        return self.gerenciador.listar_equipes()
    
    def obter_info_equipe(self, equipe_id: str) -> Optional[Equipe]:
        """Obtém informações de uma equipe"""
        return self.gerenciador.obter_equipe(equipe_id)
    
    def mostrar_relatorio_equipe(self, equipe_id: str) -> str:
        """Mostra o relatório completo de uma equipe"""
        return self.gerenciador.relatorio_equipe(equipe_id)
    
    def apagar_equipe(self, equipe_id: str) -> bool:
        """Apaga uma equipe e todos os seus dados associados"""
        try:
            equipe = self.gerenciador.obter_equipe(equipe_id)
            if not equipe:
                return False
            
            # Apagar carro da equipe no banco de dados
            if equipe.carro:
                self.db.apagar_carro(equipe.carro.id)
            
            # Apagar todos os pilotos da equipe no banco de dados
            for piloto in equipe.pilotos:
                self.db.apagar_piloto(piloto.id)
            
            # Apagar equipe do gerenciador
            self.gerenciador.apagar_equipe(equipe_id)
            
            # Apagar equipe do banco de dados
            self.db.apagar_equipe(equipe_id)
            
            return True
        except Exception as e:
            print(f"Erro ao apagar equipe: {e}")
            return False
    
    # ============ PILOTOS ============
    
    def registrar_piloto(self, nome: str, equipe_id: str) -> Piloto:
        """Registra um novo piloto na equipe"""
        piloto = self.gerenciador.criar_piloto(nome, equipe_id)
        return piloto
    
    def alterar_carro_equipe(self, equipe_id: str, marca: str, modelo: str) -> bool:
        """Altera o carro de uma equipe"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return False
        
        equipe.carro.marca = marca
        equipe.carro.modelo = modelo
        self.db.salvar_carro(equipe.carro)
        return True
    
    def obter_info_piloto(self, piloto_id: str) -> Optional[Piloto]:
        """Obtém informações de um piloto"""
        return self.gerenciador.obter_piloto(piloto_id)
    
    def listar_pilotos_equipe(self, equipe_id: str) -> List[Piloto]:
        """Lista todos os pilotos de uma equipe"""
        return self.gerenciador.listar_pilotos_equipe(equipe_id)
    
    def melhorar_atributo_piloto(self, piloto_id: str, atributo: str,
                                quantidade: float) -> bool:
        """Método removido - sistema simplificado"""
        return False
    
    # ============ BATALHAS ============
    
    def registrar_batalha(self, piloto_a_id: str, piloto_b_id: str, 
                         etapa: int = 1, auto_exportar: bool = True) -> Optional[Batalha]:
        """Registra e executa uma batalha entre dois pilotos
        
        Args:
            piloto_a_id: ID do primeiro piloto
            piloto_b_id: ID do segundo piloto
            etapa: Número da etapa (padrão 1)
            auto_exportar: Se True, exporta dados das equipes para Excel automaticamente
            
        Returns:
            Objeto Batalha com resultado
        """
        piloto_a = self.gerenciador.obter_piloto(piloto_a_id)
        piloto_b = self.gerenciador.obter_piloto(piloto_b_id)
        
        if not piloto_a or not piloto_b:
            return None
        
        equipe_a = self.gerenciador.obter_equipe(piloto_a.equipe_id)
        equipe_b = self.gerenciador.obter_equipe(piloto_b.equipe_id)
        
        if not equipe_a or not equipe_b:
            return None
        
        # Executar batalha (loop até vencedor) e obter resultados do D20
        batalha, resultados_d20 = self.batalhas.executar_batalha_completa(piloto_a, piloto_b, equipe_a, equipe_b, etapa)
        
        # Armazenar resultados do D20 para exibição posterior
        self.ultimos_resultados_d20 = resultados_d20
        self.ultima_batalha_equipes = (equipe_a, equipe_b)
        
        # Salvar no banco de dados
        self.db.salvar_batalha(batalha)
        self.db.salvar_piloto(piloto_a)
        self.db.salvar_piloto(piloto_b)
        self.db.salvar_equipe(equipe_a)
        self.db.salvar_equipe(equipe_b)
        
        # Exportar dados das equipes para Excel automaticamente
        if auto_exportar:
            self._exportar_apos_batalha(equipe_a, equipe_b)
        
        return batalha
    
    def _exportar_apos_batalha(self, equipe_a: Equipe, equipe_b: Equipe):
        """Exporta dados das equipes após uma batalha
        
        Args:
            equipe_a: Primeira equipe
            equipe_b: Segunda equipe
        """
        try:
            # Usar auto-export monitor se habilitado
            if self.auto_export_monitor:
                self.auto_export_monitor.registrar_mudancas_multiplas([equipe_a.id, equipe_b.id])
            else:
                # Fallback: exportar silenciosamente (sem prints)
                self.exportador_excel.exportar_equipe_silencioso(equipe_a)
                self.exportador_excel.exportar_equipe_silencioso(equipe_b)
        except Exception as e:
            # Não interromper a batalha se exportação falhar
            print(f"⚠️ Aviso: Erro ao exportar dados das equipes: {e}")
    
    
    def obter_relatorio_batalha(self, batalha: Batalha) -> str:
        """Obtém o relatório textual de uma batalha"""
        piloto_a = self.gerenciador.obter_piloto(batalha.piloto_a_id)
        piloto_b = self.gerenciador.obter_piloto(batalha.piloto_b_id)
        equipe_a = self.gerenciador.obter_equipe(batalha.equipe_a_id)
        equipe_b = self.gerenciador.obter_equipe(batalha.equipe_b_id)
        
        if not piloto_a or not piloto_b:
            return "Pilotos não encontrados!"
        
        return self.batalhas.relatorio_batalha(batalha, piloto_a, piloto_b, equipe_a, equipe_b)
    
    def obter_relatorio_d20_ultima_batalha(self) -> str:
        """Obtém o relatório dos D20 da última batalha simulada"""
        if not hasattr(self, 'ultimos_resultados_d20') or not hasattr(self, 'ultima_batalha_equipes'):
            return "Nenhuma batalha foi simulada ainda!"
        
        equipe_a, equipe_b = self.ultima_batalha_equipes
        return self.batalhas.relatorio_d20_batalha(equipe_a, equipe_b, self.ultimos_resultados_d20)
    
    def simular_temporada(self, equipe_a_id: str, equipe_b_id: str, 
                         numero_batalhas: int = 5) -> str:
        """Simula uma temporada inteira com múltiplas batalhas"""
        equipe_a = self.gerenciador.obter_equipe(equipe_a_id)
        equipe_b = self.gerenciador.obter_equipe(equipe_b_id)
        
        if not equipe_a or not equipe_b or not equipe_a.pilotos or not equipe_b.pilotos:
            return "Equipes ou pilotos não encontrados!"
        
        relatorio = f"\n{'='*60}\n"
        relatorio += f"SIMULAÇÃO DE TEMPORADA: {equipe_a.nome} vs {equipe_b.nome}\n"
        relatorio += f"Batalhas: {numero_batalhas}\n"
        relatorio += f"{'='*60}\n"
        
        for i in range(numero_batalhas):
            piloto_a = equipe_a.pilotos[i % len(equipe_a.pilotos)]
            piloto_b = equipe_b.pilotos[i % len(equipe_b.pilotos)]
            
            batalha = self.registrar_batalha(piloto_a.id, piloto_b.id, etapa=i+1)
            
            if batalha:
                relatorio += f"\nBatalha {i+1}:\n"
                relatorio += f"  {piloto_a.nome} ({equipe_a.nome}) vs {piloto_b.nome} ({equipe_b.nome})\n"
                
                if batalha.resultado == ResultadoBatalha.VITORIA_EQUIPE_A:
                    relatorio += f"  ✓ Vitória: {piloto_a.nome} (+{batalha.doricoins_vencedor} doricoins)\n"
                elif batalha.resultado == ResultadoBatalha.VITORIA_EQUIPE_B:
                    relatorio += f"  ✓ Vitória: {piloto_b.nome} (+{batalha.doricoins_vencedor} doricoins)\n"
                
                if batalha.empates_ate_vencer > 0:
                    relatorio += f"  ⚠ Houve {batalha.empates_ate_vencer} empate(s) (sem prêmio, desgaste x2)\n"
        
        relatorio += f"\n{'='*60}\n"
        relatorio += f"RESULTADO FINAL:\n"
        relatorio += f"{equipe_a.nome}: {equipe_a.doricoins:.2f} doricoins\n"
        relatorio += f"{equipe_b.nome}: {equipe_b.doricoins:.2f} doricoins\n"
        relatorio += f"{'='*60}\n"
        
        return relatorio
    
    # ============ PEÇAS E REPAROS ============
    
    def adicionar_diferencial_carro(self, equipe_id: str, nome: str,
                                   relacao: str) -> bool:
        """Adiciona um diferencial extra ao carro de uma equipe"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return False
        
        return self.gerenciador.adicionar_diferencial(equipe.carro.id, nome, relacao)
    
    def reparar_carro(self, equipe_id: str,
                     percentual: float = 100.0) -> Tuple[bool, str]:
        """Repara o carro de uma equipe"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        
        if not equipe:
            return False, "Equipe não encontrada!"
        
        carro = equipe.carro
        pecas_danificadas = [p for p in carro.get_todas_pecas() 
                            if p.durabilidade_atual < p.durabilidade_maxima]
        
        if not pecas_danificadas:
            return True, "Carro está em perfeito estado!"
        
        custo_total = sum(p.preco for p in pecas_danificadas)
        
        if equipe.doricoins < custo_total:
            return False, f"Doricoins insuficientes! Necessário: {custo_total:.2f}, Disponível: {equipe.doricoins:.2f}"
        
        if self.gerenciador.reparar_carro_equipe(equipe_id, percentual):
            mensagem = f"Carro reparado com sucesso! Custo: {custo_total:.2f} doricoins"
            return True, mensagem
        
        return False, "Erro ao reparar carro!"
    
    def obter_status_carro(self, equipe_id: str) -> str:
        """Obtém o status completo de um carro"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return "Equipe não encontrada!"
        
        return SistemaDesgaste.relatorio_desgaste(equipe.carro)
    
    # ============ ECONOMIA ============
    
    def adicionar_doricoins_equipe(self, equipe_id: str, quantidade: float) -> bool:
        """Adiciona doricoins a uma equipe"""
        return self.gerenciador.adicionar_doricoins(equipe_id, quantidade)
    
    def gastar_doricoins_equipe(self, equipe_id: str, quantidade: float) -> bool:
        """Gasta doricoins de uma equipe"""
        return self.gerenciador.gastar_doricoins(equipe_id, quantidade)
    
    def obter_saldo_equipe(self, equipe_id: str) -> Optional[float]:
        """Obtém o saldo de doricoins de uma equipe"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        return equipe.doricoins if equipe else None
    
    # ============ ETAPAS ============
    
    def completar_etapa(self, numero_etapa: int) -> bool:
        """Completa uma etapa e distribui prêmios"""
        if numero_etapa not in self.etapas_ativas:
            return False
        
        etapa = self.etapas_ativas[numero_etapa]
        equipes = self.gerenciador.listar_equipes()
        
        etapa.calcular_premio_equipes(equipes)
        etapa.completa = True
        etapa.data_fim = datetime.now()
        
        # Salvar equipes com os prêmios atualizados
        for equipe in equipes:
            self.db.salvar_equipe(equipe)
        
        return True
    
    # ============ RELATÓRIOS GERAIS ============
    
    def relatorio_geral(self) -> str:
        """Gera um relatório geral do sistema"""
        equipes = self.gerenciador.listar_equipes()
        pilotos = self.gerenciador.pilotos
        
        relatorio = "\n" + "="*70 + "\n"
        relatorio += " RELATÓRIO GERAL - GRANPIX RACING CHAMPIONSHIP\n"
        relatorio += "="*70 + "\n\n"
        
        relatorio += f"EQUIPES ({len(equipes)}):\n"
        relatorio += "-" * 70 + "\n"
        for equipe in sorted(equipes, key=lambda e: e.doricoins, reverse=True):
            relatorio += f"  {equipe.nome:25} | Doricoins: {equipe.doricoins:12.2f} | Pilotos: {len(equipe.pilotos)}\n"
        
        relatorio += "\n" + self.gerenciador.relatorio_pilotos_ranking()
        relatorio += "\n" + "="*70 + "\n"
        
        return relatorio
    
    # ============ LOJA ============
    
    def listar_pecas_loja(self) -> List[PecaMotor]:
        """Lista todas as peças disponíveis na loja"""
        return self.loja.listar_pecas()
    
    def listar_pecas_por_motor(self, tipo_motor: str) -> List[PecaMotor]:
        """Lista peças de um tipo de motor específico"""
        return self.loja.listar_pecas_por_motor(tipo_motor)
    
    def obter_peca_loja(self, codigo: str) -> Optional[PecaMotor]:
        """Obtém uma peça pelo código"""
        return self.loja.obter_peca(codigo)
    
    def mostrar_catalogo_loja(self) -> str:
        """Mostra o catálogo completo da loja"""
        return self.loja.mostrar_catalogo()
    
    def verificar_requisito_peca(self, codigo_peca: str, pecas_possuidas: List[str]) -> bool:
        """Verifica se um piloto pode comprar uma peça (tem os requisitos)"""
        return self.loja.verificar_requisito(codigo_peca, pecas_possuidas)
    
    # ============ OFICINA ============
    
    def instalar_peca_carro(self, equipe_id: str, codigo_peca: str) -> Tuple[bool, str]:
        """Instala uma peça no carro de uma equipe"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return False, "❌ Equipe não encontrada"
        
        return self.oficina.instalar_peca(equipe.carro, equipe, codigo_peca)
    
    def remover_peca_carro(self, equipe_id: str, codigo_peca: str) -> Tuple[bool, str]:
        """Remove uma peça do carro de uma equipe"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return False, "❌ Equipe não encontrada"
        
        return self.oficina.remover_peca(equipe.carro, equipe, codigo_peca)
    
    def listar_pecas_instaladas(self, equipe_id: str) -> str:
        """Lista as peças instaladas no carro de uma equipe"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return "❌ Equipe não encontrada"
        
        return self.oficina.listar_pecas_carro(equipe.carro)
    
    def obter_relatorio_oficina(self) -> str:
        """Obtém o relatório de serviços da oficina"""
        return self.oficina.relatorio_oficina()
    
    def relatorio_carro_completo(self, carro_id: str) -> str:
        """Retorna relatório completo do carro com peças e desgaste"""
        # Encontrar o carro no banco de dados
        equipes = self.gerenciador.listar_equipes()
        carro = None
        equipe = None
        
        # Se não encontrar em equipes, procurar no cache do gerenciador
        if not equipes:
            # Procurar em todos os carros do gerenciador
            for eq_id, eq in self.gerenciador.equipes.items():
                if eq.carro.id == carro_id:
                    carro = eq.carro
                    equipe = eq
                    break
        else:
            for eq in equipes:
                if eq.carro.id == carro_id:
                    carro = eq.carro
                    equipe = eq
                    break
        
        if not carro:
            return "❌ Carro não encontrado"
        
        info = f"""
╔════════════════════════════════════════════════════════╗
║ RELATÓRIO COMPLETO DO CARRO
╠════════════════════════════════════════════════════════╣
║ Equipe: {equipe.nome}
║ Carro: {carro.marca} {carro.modelo} (#{carro.numero_carro})
║
║ ESTATÍSTICAS:
║   Batalhas: {carro.batidas_totais}
║   Vitórias: {carro.vitoria} | Derrotas: {carro.derrotas} | Empates: {carro.empates}
║   Condição Geral: {carro.calcular_condicao_geral():.1f}%
║
╠════════════════════════════════════════════════════════╣
║ PEÇAS INSTALADAS:
"""
        
        if hasattr(carro, 'pecas_instaladas') and carro.pecas_instaladas:
            custo_total = 0.0
            for i, peca in enumerate(carro.pecas_instaladas, 1):
                nome = peca.get('nome', peca.get('codigo_peca', 'Desconhecida'))
                valor = peca.get('valor_pago', 0.0)
                info += f"║ {i}. {nome:20} R$ {valor:10.2f}\n"
                custo_total += valor
            info += f"║ Investimento Total: R$ {custo_total:30.2f}\n"
        else:
            info += "║ Nenhuma peça instalada\n"
        
        info += "╠════════════════════════════════════════════════════════╣\n"
        info += "║ DESGASTE DAS PEÇAS:\n"
        
        pecas = carro.get_todas_pecas()
        for peca in pecas:
            durabilidade_pct = (peca.durabilidade_atual / peca.durabilidade_maxima) * 100
            barra = "█" * int(durabilidade_pct / 10) + "░" * (10 - int(durabilidade_pct / 10))
            status = "🔴" if durabilidade_pct < 30 else "🟡" if durabilidade_pct < 70 else "🟢"
            info += f"║ {status} {peca.nome:20} [{barra}] {durabilidade_pct:5.1f}%\n"
        
        info += "╚════════════════════════════════════════════════════════╝\n"
        
        return info
    
    def exportar_dados(self, arquivo: str = "data/backup.json") -> bool:
        """Exporta todos os dados para JSON"""
        return self.db.exportar_json(arquivo)
    
    # ============ LOJA DE CARROS ============
    
    def listar_modelos_carros(self) -> str:
        """Lista todos os modelos de carros disponíveis"""
        return self.loja_carros.listar_modelos_formatado()
    
    def comprar_carro(self, equipe_id: str, modelo_id: str = None, variacao_id: str = None) -> bool:
        """Equipe compra um carro novo usando variação"""
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            return False
        
        # Se receber variacao_id, usar isso. Senão, usar modelo_id (compatibilidade retroativa)
        if variacao_id:
            # Buscar variação e modelo
            variacao_dict = self.db.buscar_variacao_carro_por_id(variacao_id)
            if not variacao_dict:
                print(f"[ERRO] Variação não encontrada: {variacao_id}")
                return False
            
            modelo_id = variacao_dict['modelo_carro_loja_id']
            motor_id = variacao_dict.get('motor_id')
            cambio_id = variacao_dict.get('cambio_id')
            suspensao_id = variacao_dict.get('suspensao_id')
            kit_angulo_id = variacao_dict.get('kit_angulo_id')
            diferencial_id = variacao_dict.get('diferencial_id')
        else:
            # Compatibilidade retroativa com modelo_id
            variacao_id = None
            motor_id = None
            cambio_id = None
            suspensao_id = None
            kit_angulo_id = None
            diferencial_id = None
        
        modelo = self.loja_carros.obter_modelo(modelo_id)
        if not modelo:
            print(f"[ERRO] Modelo não encontrado: {modelo_id}")
            return False
        
        # Buscar o valor da variação para uso no débito
        preco = float(modelo.preco)  # Padrão para compatibilidade
        if variacao_id:
            variacao_data = self.db.buscar_variacao_carro_por_id(variacao_id)
            if variacao_data:
                preco = float(variacao_data.get('valor', modelo.preco))
                print(f"[COMPRA] Usando preço da variação: R${preco}")
        
        # Verificar se a equipe tem doricoins suficientes
        if equipe.doricoins < preco:
            print(f"[ERRO] Saldo insuficiente: {equipe.doricoins} < {preco}")
            return False
        
        # ❌ REMOVIDO: Não criar peças padrão quando compra carro
        # O carro agora é criado VAZIO, sem nenhuma peça
        # As peças são adicionadas apenas quando o usuário as compra
        motor = None
        cambio = None
        kit_angulo = None
        suspensao = None
        diferenciais = []
        
        # Determinar o próximo numero_carro para a equipe
        numero_carro = 1
        # Query the db for the max numero_carro for this equipe
        max_numero = self.db.obter_max_numero_carro_equipe(equipe_id)
        if max_numero is not None:
            numero_carro = max_numero + 1
        
        novo_carro = Carro(
            id=str(uuid.uuid4()),
            numero_carro=numero_carro,
            marca=modelo.marca,
            modelo=modelo.modelo,
            motor=motor,
            cambio=cambio,
            kit_angulo=kit_angulo,
            suspensao=suspensao,
            diferenciais=diferenciais,
            modelo_id=modelo.id,  # Importante: referenciar o modelo da loja para compatibilidade de peças
            status='repouso'  # Carros comprados começam em repouso
        )
        
        # Definir os IDs das peças no novo carro
        novo_carro.motor_id = motor.id if motor else ''
        novo_carro.cambio_id = cambio.id if cambio else ''
        novo_carro.kit_angulo_id = kit_angulo.id if kit_angulo else ''
        novo_carro.suspensao_id = suspensao.id if suspensao else ''
        novo_carro.diferencial_id = diferenciais[0].id if diferenciais else ''
        
        # Preencher pecas_instaladas apenas com as peças que existem em pecas_loja
        novo_carro.pecas_instaladas = []
        
        # ❌ COMENTADO: Não adicionar peças padrão ao comprar carro
        # O carro agora é criado VAZIO, sem peças cadastradas
        # As peças são adicionadas apenas quando o usuário compra e instala
        # if motor:
        #     novo_carro.pecas_instaladas.append({'id': motor.id, 'nome': motor.nome, 'tipo': motor.tipo})
        # if cambio:
        #     novo_carro.pecas_instaladas.append({'id': cambio.id, 'nome': cambio.nome, 'tipo': cambio.tipo})
        # if kit_angulo:
        #     novo_carro.pecas_instaladas.append({'id': kit_angulo.id, 'nome': kit_angulo.nome, 'tipo': kit_angulo.tipo})
        # if suspensao:
        #     novo_carro.pecas_instaladas.append({'id': suspensao.id, 'nome': suspensao.nome, 'tipo': suspensao.tipo})
        # for diferencial in diferenciais:
        #     novo_carro.pecas_instaladas.append({'id': diferencial.id, 'nome': diferencial.nome, 'tipo': diferencial.tipo})
        
        # Descontar doricoins baseado no valor da variação
        equipe.doricoins -= float(preco)
        
        # Adicionar novo carro à frota da equipe (comentado para evitar cache issues)
        # if not hasattr(equipe, 'carros'):
        #     equipe.carros = []
        # equipe.carros.append(novo_carro)
        
        # Se não há carro ativo, definir este como ativo (comentado)
        # if not equipe.carro:
        #     equipe.carro = novo_carro
        
        # Salvar no banco de dados com variacao_carro_id
        self.db.salvar_carro(novo_carro, equipe.id, variacao_carro_id=variacao_id)
        self.db.salvar_equipe(equipe)
        
        return True
    
    def cadastrar_carro_loja(self, marca: str, modelo: str, classe: str, preco: float,
                            descricao: str, motor_id: str = None, cambio_id: str = None,
                            suspensao: str = 'original', kit_angulo: str = 'original', 
                            diferencial: str = 'original') -> bool:
        """Cadastra um novo modelo de carro na loja"""
        try:
            novo_modelo = self.loja_carros.adicionar_modelo(
                marca, modelo, classe, preco, descricao,
                motor_id=motor_id, cambio_id=cambio_id, suspensao=suspensao,
                kit_angulo=kit_angulo, diferencial=diferencial
            )
            # Salvar no banco de dados
            self.db.salvar_modelo_loja(novo_modelo)
            return True
        except Exception as e:
            print(f"Erro ao cadastrar carro: {e}")
            return False
    
    def obter_carros_loja(self) -> List:
        """Retorna lista de carros cadastrados na loja"""
        return self.loja_carros.listar_modelos()    
    # ============ LOJA DE PECAS ============
    
    def cadastrar_peca_loja(self, nome: str, tipo: str, preco: float,
                           descricao: str, compatibilidade: str,
                           durabilidade: float = 100.0, coeficiente_quebra: float = 1.0) -> bool:
        """Cadastra uma nova peca na loja com coeficiente de quebra"""
        try:
            nova_peca = self.loja_pecas.adicionar_peca(
                nome, tipo, preco, descricao, compatibilidade, durabilidade, coeficiente_quebra
            )
            # Salvar no banco de dados
            self.db.salvar_peca_loja(nova_peca)
            return True
        except Exception as e:
            print(f"Erro ao cadastrar peca: {e}")
            return False
    
    def obter_pecas_loja(self) -> List:
        """Retorna lista de pecas cadastradas na loja"""
        return self.loja_pecas.listar_pecas()
    
    def obter_pecas_por_tipo(self, tipo: str) -> List:
        """Retorna pecas de um tipo específico"""
        return self.loja_pecas.listar_pecas_por_tipo(tipo)
    
    def obter_pecas_compativel_carro(self, modelo_carro_id: str) -> List:
        """Retorna pecas compatíveis com um carro"""
        return self.loja_pecas.listar_pecas_compativel_carro(modelo_carro_id)
    
    def comprar_peca(self, equipe_id: str, peca_id: str) -> bool:
        """Compra uma peca para a equipe"""
        try:
            equipe = self.gerenciador.obter_equipe(equipe_id)
            peca = self.loja_pecas.obter_peca(peca_id)
            
            if not equipe or not peca:
                return False
            
            if equipe.doricoins < peca.preco:
                print(f"Doricoins insuficientes! Necessario {peca.preco:.2f}, tem {equipe.doricoins:.2f}")
                return False
            
            # Descontar doricoins
            equipe.doricoins -= peca.preco
            
            # Adicionar peca ao carro da equipe
            carro = equipe.carro
            if peca.tipo == "motor":
                carro.motor.preco = peca.preco
                carro.motor.nome = peca.nome
                carro.motor.coeficiente_quebra = peca.coeficiente_quebra
            elif peca.tipo == "cambio":
                carro.cambio.preco = peca.preco
                carro.cambio.nome = peca.nome
                carro.cambio.coeficiente_quebra = peca.coeficiente_quebra
            elif peca.tipo == "suspensao":
                carro.suspensao.preco = peca.preco
                carro.suspensao.nome = peca.nome
                carro.suspensao.coeficiente_quebra = peca.coeficiente_quebra
            elif peca.tipo == "kit_angulo":
                carro.kit_angulo.preco = peca.preco
                carro.kit_angulo.nome = peca.nome
                carro.kit_angulo.coeficiente_quebra = peca.coeficiente_quebra
            elif peca.tipo == "diferencial":
                # Adicionar novo diferencial à lista
                novo_diferencial = Peca(
                    id=peca.id,
                    nome=peca.nome,
                    tipo=peca.tipo,
                    durabilidade_maxima=peca.durabilidade,
                    preco=peca.preco,
                    coeficiente_quebra=peca.coeficiente_quebra
                )
                carro.diferenciais.append(novo_diferencial)
            
            # Adicionar à lista de peças instaladas
            peca_info = {
                "tipo": peca.tipo,
                "nome": peca.nome,
                "valor_pago": peca.preco,
                "codigo_peca": peca.id,
                "coeficiente_quebra": peca.coeficiente_quebra,
                "data_instalacao": str(datetime.now())
            }
            carro.pecas_instaladas.append(peca_info)
            
            # Salvar alterações
            self.db.salvar_carro(carro)
            self.db.salvar_equipe(equipe)
            return True
        except Exception as e:
            print(f"Erro ao comprar peca: {e}")
            return False
    
    # ============ ETAPAS ============
    
    def criar_etapa(self, numero: int, nome: str = "") -> Etapa:
        """Cria uma nova etapa"""
        if not nome:
            nome = f"Etapa {numero}"
        
        etapa = Etapa(
            id=str(uuid.uuid4()),
            numero=numero,
            nome=nome
        )
        
        self.etapas_ativas[numero] = etapa
        return etapa
    
    def registrar_presenca_etapa(self, numero_etapa: int, equipe_id: str, presente: bool) -> bool:
        """Registra a presença de uma equipe em uma etapa"""
        if numero_etapa not in self.etapas_ativas:
            return False
        
        etapa = self.etapas_ativas[numero_etapa]
        etapa.registrar_presenca(equipe_id, presente)
        
        # Se presente, adiciona 2000 doricoins
        if presente:
            equipe = self.gerenciador.obter_equipe(equipe_id)
            if equipe:
                equipe.adicionar_doricoins(2000.0)
                self.db.salvar_equipe(equipe)
        
        return True
    
    def registrar_atributos_etapa(self, numero_etapa: int, equipe_id: str, 
                                 linha: int, angulo: int, estilo: int) -> bool:
        """Registra os atributos de uma equipe para a etapa"""
        if numero_etapa not in self.etapas_ativas:
            return False
        
        etapa = self.etapas_ativas[numero_etapa]
        try:
            etapa.registrar_atributos(equipe_id, linha, angulo, estilo)
            return True
        except ValueError as e:
            print(f"Erro ao registrar atributos: {e}")
            return False
    
    def gerar_ranking_etapa(self, numero_etapa: int) -> List[str]:
        """Gera o ranking das equipes presentes na etapa baseado em atributos
        
        Critério de desempate:
        - Primário: Total de pontos (Linha + Angulo + Estilo)
        - Desempate: Pontuação de Linha
        """
        if numero_etapa not in self.etapas_ativas:
            return []
        
        etapa = self.etapas_ativas[numero_etapa]
        
        # Filtrar apenas equipes presentes
        equipes_presentes = [
            equipe_id for equipe_id, presente in etapa.equipes_presentes.items() 
            if presente and equipe_id in etapa.atributos_equipes
        ]
        
        # Ordenar por total de atributos (decrescente), depois por linha (decrescente)
        ranking = sorted(
            equipes_presentes,
            key=lambda eq_id: (
                etapa.atributos_equipes[eq_id]["total"],
                etapa.atributos_equipes[eq_id].get("linha", 0)
            ),
            reverse=True
        )
        
        etapa.ranking_etapa = ranking
        return ranking
    
    def determinar_rodadas_torneio(self, numero_etapa: int) -> List[str]:
        """Determina quais rodadas devem ser disputadas baseado no número de pilotos
        
        Lógica tipo Shalonge mata-mata:
        - Se tem equipes: começa no maior slot que as acomoda
        - 17+ equipes: TOP 32 → TOP 16 → TOP 8 → TOP 4 → FINAL
        - 9-16 equipes: TOP 16 → TOP 8 → TOP 4 → FINAL
        - 5-8 equipes: TOP 8 → TOP 4 → FINAL
        - 3-4 equipes: TOP 4 → FINAL
        - 2 equipes: FINAL
        """
        if numero_etapa not in self.etapas_ativas:
            return []
        
        etapa = self.etapas_ativas[numero_etapa]
        num_pilotos = len(etapa.ranking_etapa)
        
        rodadas = []
        if num_pilotos > 16:  # 17 ou mais
            rodadas = ["top32", "top16", "top8", "top4", "final"]
        elif num_pilotos > 8:  # 9-16
            rodadas = ["top16", "top8", "top4", "final"]
        elif num_pilotos > 4:  # 5-8
            rodadas = ["top8", "top4", "final"]
        elif num_pilotos > 2:  # 3-4
            rodadas = ["top4", "final"]
        elif num_pilotos >= 2:  # 2
            rodadas = ["final"]
        
        etapa.rodadas_disponiveis = rodadas
        etapa.rodada_atual = rodadas[0] if rodadas else "final"
        
        return rodadas
    
    def gerar_chaveamento_rodada(self, numero_etapa: int, rodada: str) -> List[Tuple[str, str]]:
        """Gera o chaveamento para uma rodada específica do torneio
        
        Lógica tipo seeding real (Shalonge mata-mata):
        - Se há MAIS pilotos que o limite: cria play-in com os piores
        - Se há número ÍMPAR dentro do limite: os melhores passam direto
        - Os restantes competem em pares
        
        Exemplo Top 32 (limite 32):
        - 18 pilotos: 16 melhores passam direto, 17º vs 18º fazem play-in
        - 33 pilotos: 32 melhores competem, 33º é eliminado
        - 31 pilotos: 1º passa direto, 2º-31º competem (15 batalhas)
        - 32 pilotos: todos competem (16 batalhas)
        """
        if numero_etapa not in self.etapas_ativas:
            return []
        
        etapa = self.etapas_ativas[numero_etapa]
        
        # Determinar participantes da rodada
        if rodada not in etapa.rodadas:
            etapa.rodadas[rodada] = {"chaveamento": [], "vencedores": [], "passam_direto": []}
        
        # Se é a primeira rodada, usar ranking
        if rodada == etapa.rodadas_disponiveis[0]:
            participantes = etapa.ranking_etapa[:]
        else:
            # Usar vencedores da rodada anterior + quem passou direto
            rodada_anterior = etapa.rodadas_disponiveis[etapa.rodadas_disponiveis.index(rodada) - 1]
            vencedores = etapa.rodadas[rodada_anterior].get("vencedores", [])
            passou_direto = etapa.rodadas[rodada_anterior].get("passam_direto", [])
            participantes = vencedores + passou_direto
        
        # Determinar tamanho da rodada
        tamanho_rodada = {
            "top32": 32,
            "top16": 16,
            "top8": 8,
            "top4": 4,
            "final": 2
        }.get(rodada, 2)
        
        chaveamento = []
        passam_direto = []
        num_pilotos = len(participantes)
        
        # CASO 1: MAIS pilotos que o limite
        # Exemplo: 18 pilotos no TOP 32 (limite 32)
        # → 16 melhores passam direto, 17º vs 18º fazem play-in
        if num_pilotos > tamanho_rodada:
            passam_direto = participantes[:tamanho_rodada // 2]
            participantes_lutam = participantes[tamanho_rodada // 2:]
            
            # Criar chaveamento apenas com os piores
            for i in range(len(participantes_lutam) // 2):
                primeiro = participantes_lutam[i]
                ultimo = participantes_lutam[-(i + 1)]
                chaveamento.append((primeiro, ultimo))
            
            # Se sobrou um piloto (ímpar), entra nos que passam direto
            if len(participantes_lutam) % 2 == 1:
                passam_direto.append(participantes_lutam[len(participantes_lutam) // 2])
        
        # CASO 2: NÚMERO ÍMPAR dentro do limite
        # Exemplo: 31 pilotos no TOP 32 (limite 32)
        # → 1º passa direto, 2º-31º competem (15 batalhas)
        elif num_pilotos % 2 == 1:
            passam_direto = [participantes[0]]
            participantes_lutam = participantes[1:]
            
            for i in range(len(participantes_lutam) // 2):
                primeiro = participantes_lutam[i]
                ultimo = participantes_lutam[-(i + 1)]
                chaveamento.append((primeiro, ultimo))
        
        # CASO 3: NÚMERO PAR
        # Todos competem em pares
        else:
            for i in range(len(participantes) // 2):
                primeiro = participantes[i]
                ultimo = participantes[-(i + 1)]
                chaveamento.append((primeiro, ultimo))
        
        etapa.rodadas[rodada]["chaveamento"] = chaveamento
        etapa.rodadas[rodada]["passam_direto"] = passam_direto
        
        return chaveamento
    
    def registrar_vencedor_rodada(self, numero_etapa: int, rodada: str, vencedor_id: str) -> bool:
        """Registra um vencedor em uma rodada do torneio"""
        if numero_etapa not in self.etapas_ativas:
            return False
        
        etapa = self.etapas_ativas[numero_etapa]
        
        if rodada not in etapa.rodadas:
            return False
        
        # Adicionar aos vencedores
        if "vencedores" not in etapa.rodadas[rodada]:
            etapa.rodadas[rodada]["vencedores"] = []
        
        etapa.rodadas[rodada]["vencedores"].append(vencedor_id)
        
        # Adicionar prêmio
        equipe = self.gerenciador.obter_equipe(vencedor_id)
        if equipe:
            premio = {
                "top32": 1000,
                "top16": 1000,
                "top8": 1000,
                "top4": 1000,
                "final": 1000
            }.get(rodada, 1000)
            equipe.adicionar_doricoins(premio)
            self.db.salvar_equipe(equipe)
        
        return True
    
    def simular_batalha_com_desgaste(self, equipe_a_id: str, equipe_b_id: str, desgaste_base: float = 10.0) -> tuple:
        """Simula uma batalha entre duas equipes com chance de empate
        
        Retorna:
            (vencedor_id, houve_empate, pecas_quebradas_a, pecas_quebradas_b)
        """
        import random
        
        equipe_a = self.gerenciador.obter_equipe(equipe_a_id)
        equipe_b = self.gerenciador.obter_equipe(equipe_b_id)
        
        if not equipe_a or not equipe_b:
            return None, False, [], []
        
        # Chance de empate: 15%
        houve_empate = random.random() < 0.15
        
        # Aplicar desgaste a ambos os carros
        pecas_quebradas_a = equipe_a.carro.sofrer_desgaste_batalha(desgaste_base, empate=houve_empate)
        pecas_quebradas_b = equipe_b.carro.sofrer_desgaste_batalha(desgaste_base, empate=houve_empate)
        
        # Salvar equipes
        self.db.salvar_equipe(equipe_a)
        self.db.salvar_equipe(equipe_b)
        
        # Se houve empate, retornar None como vencedor
        if houve_empate:
            return None, True, pecas_quebradas_a, pecas_quebradas_b
        
        # Caso contrário, sortear um vencedor aleatoriamente
        vencedor_id = random.choice([equipe_a_id, equipe_b_id])
        return vencedor_id, False, pecas_quebradas_a, pecas_quebradas_b
    
    def proxima_rodada(self, numero_etapa: int) -> bool:
        """Avança para a próxima rodada do torneio"""
        if numero_etapa not in self.etapas_ativas:
            return False
        
        etapa = self.etapas_ativas[numero_etapa]
        
        if not etapa.rodadas_disponiveis:
            return False
        
        idx_rodada_atual = etapa.rodadas_disponiveis.index(etapa.rodada_atual)
        
        if idx_rodada_atual + 1 < len(etapa.rodadas_disponiveis):
            etapa.rodada_atual = etapa.rodadas_disponiveis[idx_rodada_atual + 1]
            return True
        
        return False
    
    def obter_proximos_participantes(self, numero_etapa: int) -> List[str]:
        """Obtém os participantes para a próxima rodada (vencedores + passou direto)"""
        if numero_etapa not in self.etapas_ativas:
            return []
        
        etapa = self.etapas_ativas[numero_etapa]
        rodada_atual = etapa.rodada_atual
        
        if rodada_atual not in etapa.rodadas:
            return []
        
        vencedores = etapa.rodadas[rodada_atual].get("vencedores", [])
        passam_direto = etapa.rodadas[rodada_atual].get("passam_direto", [])
        
        # Ordenar: vencedores primeiro, depois passou direto
        return vencedores + passam_direto

    def executar_etapa(self, numero_etapa: int) -> str:
        """Executa todas as batalhas da etapa - resultado decide pelo usuário"""
        if numero_etapa not in self.etapas_ativas:
            return "Etapa não encontrada"
        
        etapa = self.etapas_ativas[numero_etapa]
        
        if not etapa.chaveamento_mata_mata:
            # Se chaveamento não foi gerado, gera agora
            self.gerar_chaveamento_mata_mata(numero_etapa)
        
        resultado = f"\n{'='*70}\n"
        resultado += f"EXECUTANDO ETAPA {etapa.numero}: {etapa.nome}\n"
        resultado += f"{'='*70}\n\n"
        
        # Armazenar para retornar a lista de vencedores
        vencedores_etapa = []
        
        # Executar cada batalha do chaveamento
        for idx, (equipe_a_id, equipe_b_id) in enumerate(etapa.chaveamento_mata_mata, 1):
            equipe_a = self.gerenciador.obter_equipe(equipe_a_id)
            equipe_b = self.gerenciador.obter_equipe(equipe_b_id)
            
            if not equipe_a or not equipe_b:
                continue
            
            # Obter atributos para exibição
            atributos_a = etapa.atributos_equipes.get(equipe_a_id, {"total": 0})
            atributos_b = etapa.atributos_equipes.get(equipe_b_id, {"total": 0})
            
            resultado += f"BATALHA {idx}: {equipe_a.nome} vs {equipe_b.nome}\n"
            resultado += f"  {equipe_a.nome}: {atributos_a['total']} pontos (Linha: {atributos_a.get('linha', 0)}, Angulo: {atributos_a.get('angulo', 0)}, Estilo: {atributos_a.get('estilo', 0)})\n"
            resultado += f"  {equipe_b.nome}: {atributos_b['total']} pontos (Linha: {atributos_b.get('linha', 0)}, Angulo: {atributos_b.get('angulo', 0)}, Estilo: {atributos_b.get('estilo', 0)})\n"
            
            # Retornar resultado temporário para que o menu pergunte ao usuário
            return resultado
        
        resultado += f"{'='*70}\n"
        resultado += f"ETAPA {etapa.numero} CONCLUÍDA!\n"
        resultado += f"{'='*70}\n"
        
        etapa.completa = True
        
        return resultado
    
    # ============ EXPORTAÇÃO EXCEL ============
    
    def exportar_equipe_excel(self, equipe_id: str) -> bool:
        """Exporta dados de uma equipe para Excel
        
        Args:
            equipe_id: ID da equipe a exportar
            
        Returns:
            True se exportado com sucesso, False caso contrário
        """
        equipe = self.gerenciador.obter_equipe(equipe_id)
        if not equipe:
            print(f"❌ Equipe com ID '{equipe_id}' não encontrada")
            return False
        
        try:
            caminho = self.exportador_excel.exportar_equipe(equipe)
            print(f"✓ Equipe '{equipe.nome}' exportada para: {caminho}")
            return True
        except Exception as e:
            print(f"❌ Erro ao exportar equipe: {e}")
            return False
    
    def exportar_todas_equipes_excel(self) -> List[str]:
        """Exporta dados de todas as equipes para Excel
        
        Returns:
            Lista com caminhos dos arquivos gerados
        """
        equipes = self.gerenciador.listar_equipes()
        if not equipes:
            print("❌ Nenhuma equipe cadastrada para exportar")
            return []
        
        print(f"\n📊 Exportando {len(equipes)} equipe(s)...\n")
        arquivos = self.exportador_excel.exportar_todas_equipes(equipes)
        
        print(f"\n✓ {len(arquivos)} arquivo(s) gerado(s) com sucesso!")
        return arquivos
    
    # ============ ONEDRIVE ============
    
    def ativar_exportacao_onedrive(self) -> bool:
        """Ativa exportação para OneDrive
        
        Returns:
            True se OneDrive foi ativado, False caso contrário
        """
        return self.exportador_excel.ativar_onedrive()
    
    def desativar_exportacao_onedrive(self):
        """Desativa OneDrive e volta para pasta local"""
        self.exportador_excel.desativar_onedrive()
    
    def obter_status_exportacao(self) -> str:
        """Retorna o status atual de exportação
        
        Returns:
            String descrevendo onde os arquivos serão salvos
        """
        return self.exportador_excel.obter_status_onedrive()
    
    # ============ AUTO-EXPORT ============
    
    def ativar_auto_export(self) -> bool:
        """Ativa o sistema de auto-export automático
        
        Returns:
            True se ativado com sucesso
        """
        if not self.auto_export_habilitado and self.auto_export_monitor:
            self.auto_export_monitor.iniciar()
            self.auto_export_habilitado = True
            print("✅ Auto-export ATIVADO - Excel será atualizado em tempo real!")
            return True
        elif self.auto_export_habilitado:
            print("⚠️ Auto-export já está ativado")
            return False
        else:
            print("❌ Auto-export não foi inicializado")
            return False
    
    def desativar_auto_export(self) -> bool:
        """Desativa o sistema de auto-export
        
        Returns:
            True se desativado com sucesso
        """
        if self.auto_export_habilitado and self.auto_export_monitor:
            self.auto_export_monitor.parar()
            self.auto_export_habilitado = False
            print("⛔ Auto-export DESATIVADO")
            return True
        elif not self.auto_export_habilitado:
            print("⚠️ Auto-export já está desativado")
            return False
        else:
            print("❌ Auto-export não foi inicializado")
            return False
    
    def obter_status_auto_export(self) -> dict:
        """Retorna o status atual do auto-export
        
        Returns:
            Dict com status do monitor
        """
        if self.auto_export_monitor:
            status = self.auto_export_monitor.obter_status()
            return status
        return {
            'habilitado': False,
            'erro': 'Auto-export não foi inicializado'
        }
    
    def exportar_todas_equipes_agora(self, forcar: bool = False) -> int:
        """Exporta todas as equipes para Excel imediatamente
        
        Args:
            forcar: Se True, ignora o cooldown entre exports
            
        Returns:
            Número de equipes exportadas com sucesso
        """
        if self.auto_export_monitor:
            return self.auto_export_monitor.exportar_todas_agora(forcar=forcar)
        
        # Fallback manual
        equipes = self.gerenciador.listar_equipes()
        exportadas = 0
        for equipe in equipes:
            try:
                self.exportador_excel.exportar_equipe_silencioso(equipe)
                exportadas += 1
            except Exception as e:
                print(f"Erro ao exportar {equipe.nome}: {e}")
        
        return exportadas
    
    # ============ PROCESSAMENTO DE COMPRAS ============
    
    def ativar_monitor_compras(self) -> bool:
        """Ativa o monitoramento automático de compras
        
        Returns:
            True se ativado com sucesso
        """
        if self.monitor_compras and not self.monitor_compras.rodando:
            self.monitor_compras.iniciar()
            print("✅ Monitor de compras ATIVADO")
            return True
        return False
    
    def desativar_monitor_compras(self) -> bool:
        """Desativa o monitoramento de compras
        
        Returns:
            True se desativado com sucesso
        """
        if self.monitor_compras and self.monitor_compras.rodando:
            self.monitor_compras.parar()
            print("⛔ Monitor de compras DESATIVADO")
            return True
        return False
    
    def obter_status_compras(self) -> dict:
        """Retorna status do sistema de compras"""
        status = {
            'processador': self.processador_compras.obter_status(),
            'monitor': {
                'rodando': self.monitor_compras.rodando if self.monitor_compras else False
            }
        }
        return status
    
    def obter_historico_compras(self, equipe_id: Optional[str] = None) -> list:
        """Retorna histórico de compras
        
        Args:
            equipe_id: Filtrar por equipe (opcional)
            
        Returns:
            Lista de compras
        """
        return self.processador_compras.obter_historico_compras(equipe_id)