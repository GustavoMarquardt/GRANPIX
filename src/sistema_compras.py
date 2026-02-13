"""
Monitor de Compras - Processa automaticamente solicitações de compra do Excel
"""
from datetime import datetime
from typing import Dict, Optional
import logging
from .mysql_utils import get_connection, close_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - COMPRAS - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SistemaCompras:
    """Sistema de processamento automático de compras do Excel"""

    def __init__(self, api):
        """
        Inicializa o sistema de compras

        Args:
            api: Instância de APIGranpix
        """
        self.api = api
    
    def _salvar_fila(self, fila: list):
        """Salva a fila de compras no MySQL"""
        try:
            conn = get_connection()
            if not conn:
                return

            cursor = conn.cursor()
            # Limpar fila atual
            cursor.execute("DELETE FROM fila_compras")
            # Inserir novas solicitações
            for item in fila:
                sql = """
                    INSERT INTO fila_compras (equipe_id, tipo, item_id, quantidade, timestamp, status, resultado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    item.get('equipe_id'),
                    item.get('tipo'),
                    item.get('item_id'),
                    item.get('quantidade', 1),
                    item.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    item.get('status', 'pendente'),
                    item.get('resultado', '')
                ))
            conn.commit()
            close_connection(conn)
        except Exception as e:
            logger.error(f"Erro ao salvar fila: {e}")

    def _carregar_fila(self) -> list:
        """Carrega a fila de compras do MySQL"""
        try:
            conn = get_connection()
            if not conn:
                return []

            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM fila_compras ORDER BY timestamp DESC")
            results = cursor.fetchall()
            close_connection(conn)
            return results
        except Exception as e:
            logger.error(f"Erro ao carregar fila: {e}")
            return []
    
    def adicionar_solicitacao_compra(self, equipe_id: str, tipo: str, item_id: str, quantidade: int = 1) -> bool:
        """
        Adiciona uma solicitação de compra à fila no MySQL

        Args:
            equipe_id: ID da equipe
            tipo: 'carro' ou 'peca'
            item_id: ID do item (modelo_id ou peca_id)
            quantidade: Quantidade a comprar

        Returns:
            True se adicionado com sucesso
        """
        try:
            conn = get_connection()
            if not conn:
                return False

            cursor = conn.cursor()
            sql = """
                INSERT INTO fila_compras (equipe_id, tipo, item_id, quantidade, timestamp, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                equipe_id,
                tipo,
                item_id,
                quantidade,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pendente'
            ))
            conn.commit()
            close_connection(conn)

            logger.info(f"📝 Solicitação adicionada: {tipo} {item_id} (Qty: {quantidade}) para equipe {equipe_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar solicitação: {e}")
            return False
    
    def processar_fila(self) -> Dict[str, int]:
        """
        Processa todas as solicitações de compra na fila do MySQL

        Returns:
            Dict com contadores de sucesso/erro
        """
        fila = self._carregar_fila()
        resultado = {
            'processadas': 0,
            'sucesso': 0,
            'erro': 0
        }

        if not fila:
            return resultado

        for solicitacao in fila:
            if solicitacao['status'] != 'pendente':
                continue

            resultado['processadas'] += 1

            try:
                # Processar a compra
                sucesso = self._processar_compra(
                    solicitacao['equipe_id'],
                    solicitacao['tipo'],
                    solicitacao['item_id']
                )

                # Atualizar status no MySQL
                novo_status = 'aprovada' if sucesso else 'rejeitada'
                self._atualizar_status_solicitacao(solicitacao['id'], novo_status)

                if sucesso:
                    resultado['sucesso'] += 1
                    logger.info(f"✅ Compra aprovada: {solicitacao['tipo']} {solicitacao['item_id']}")
                else:
                    resultado['erro'] += 1
                    logger.warning(f"❌ Compra rejeitada: {solicitacao['tipo']} {solicitacao['item_id']}")

            except Exception as e:
                self._atualizar_status_solicitacao(solicitacao['id'], 'erro', str(e))
                resultado['erro'] += 1
                logger.error(f"❌ Erro ao processar compra: {e}")

        return resultado

    def _atualizar_status_solicitacao(self, solicitacao_id: int, status: str, erro_msg: str = ""):
        """Atualiza status da solicitação no MySQL"""
        try:
            conn = get_connection()
            if not conn:
                return

            cursor = conn.cursor()
            sql = "UPDATE fila_compras SET status = %s, resultado = %s WHERE id = %s"
            cursor.execute(sql, (status, erro_msg, solicitacao_id))
            conn.commit()
            close_connection(conn)
        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
    
    def _processar_compra(self, equipe_id: str, tipo: str, item_id: str) -> bool:
        """
        Processa uma compra específica
        
        Args:
            equipe_id: ID da equipe
            tipo: 'carro' ou 'peca'
            item_id: ID do item
            
        Returns:
            True se a compra foi processada com sucesso
        """
        equipe = self.api.obter_info_equipe(equipe_id)
        if not equipe:
            logger.error(f"Equipe {equipe_id} não encontrada")
            return False
        
        if tipo == 'carro':
            return self._processar_compra_carro(equipe, item_id)
        elif tipo == 'peca':
            return self._processar_compra_peca(equipe, item_id)
        else:
            logger.error(f"Tipo de compra desconhecido: {tipo}")
            return False
    
    def _processar_compra_carro(self, equipe, modelo_id: str) -> bool:
        """Processa compra de um carro"""
        # Encontrar modelo na loja
        if not self.api.loja_carros:
            logger.error("Loja de carros não disponível")
            return False
        
        modelo = None
        for m in self.api.loja_carros.modelos:
            if m.id == modelo_id:
                modelo = m
                break
        
        if not modelo:
            logger.error(f"Modelo {modelo_id} não encontrado na loja")
            return False
        
        # Verificar saldo
        if equipe.doricoins < modelo.preco:
            logger.warning(f"Saldo insuficiente: {equipe.doricoins} < {modelo.preco}")
            return False
        
        # Processar compra
        try:
            # Usar método da API que já existe
            sucesso = self.api.comprar_carro(equipe.id, modelo_id)
            
            if sucesso:
                # Disparar auto-export
                if self.api.auto_export_monitor:
                    self.api.auto_export_monitor.registrar_mudanca(equipe.id)
                
                logger.info(f"✅ Carro {modelo.marca} {modelo.modelo} comprado por {equipe.nome}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao comprar carro: {e}")
            return False
    
    def _processar_compra_peca(self, equipe, peca_id: str) -> bool:
        """Processa compra de uma peça"""
        # Encontrar peça na loja
        if not self.api.loja_pecas:
            logger.error("Loja de peças não disponível")
            return False
        
        peca = None
        for p in self.api.loja_pecas.pecas:
            if p.id == peca_id:
                peca = p
                break
        
        if not peca:
            logger.error(f"Peça {peca_id} não encontrada na loja")
            return False
        
        # Verificar saldo
        if equipe.doricoins < peca.preco:
            logger.warning(f"Saldo insuficiente: {equipe.doricoins} < {peca.preco}")
            return False
        
        # Processar compra
        try:
            # Usar método da API que já existe
            sucesso = self.api.comprar_peca(equipe.id, peca_id)
            
            if sucesso:
                # Disparar auto-export
                if self.api.auto_export_monitor:
                    self.api.auto_export_monitor.registrar_mudanca(equipe.id)
                
                logger.info(f"✅ Peça {peca.nome} comprada por {equipe.nome}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao comprar peça: {e}")
            return False
    
    def obter_historico_compras(self, equipe_id: Optional[str] = None) -> list:
        """
        Obtém histórico de compras do MySQL

        Args:
            equipe_id: Se especificado, retorna apenas compras da equipe

        Returns:
            Lista de compras
        """
        try:
            conn = get_connection()
            if not conn:
                return []

            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM fila_compras WHERE 1=1"
            params = []

            if equipe_id:
                query += " AND equipe_id = %s"
                params.append(equipe_id)

            query += " ORDER BY timestamp DESC"
            cursor.execute(query, params)
            results = cursor.fetchall()
            close_connection(conn)
            return results
        except Exception as e:
            logger.error(f"Erro ao obter histórico: {e}")
            return []

    def obter_status_compras(self) -> Dict:
        """Retorna status do sistema de compras usando MySQL"""
        try:
            conn = get_connection()
            if not conn:
                return {'erro': 'Conexão com banco falhou'}

            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM fila_compras
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())

            total = sum(status_counts.values())
            pendentes = status_counts.get('pendente', 0)
            aprovadas = status_counts.get('aprovada', 0)
            rejeitadas = status_counts.get('rejeitada', 0)
            erros = status_counts.get('erro', 0)

            close_connection(conn)

            return {
                'total': total,
                'pendentes': pendentes,
                'aprovadas': aprovadas,
                'rejeitadas': rejeitadas,
                'erros': erros
            }
        except Exception as e:
            logger.error(f"Erro ao obter status: {e}")
            return {'erro': str(e)}
