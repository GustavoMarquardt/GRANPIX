"""
Sistema de Solicitação de Compras via Arquivo
As equipes solicitam compras preenchendo um arquivo CSV/JSON
O sistema monitora e processa automaticamente
"""

import csv
from datetime import datetime
from typing import Optional, Tuple, List
import threading
import time
import logging
from .mysql_utils import get_connection, close_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - COMPRAS - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GerenciadorSolicitacoesCompra:
    """Gerencia solicitações de compra via MySQL"""
    def __init__(self, api, db_config=None):
        self.api = api
        self.db_config = db_config
        self.rodando = False
        self.thread_monitor: Optional[threading.Thread] = None
        logger.info("📋 Gerenciador de Solicitações de Compra inicializado (MySQL)")
    
    def criar_solicitacao_compra(self, equipe_id: str, tipo: str, item_id: str, quantidade: int = 1) -> Tuple[bool, str]:
        """
        Cria uma nova solicitação de compra no MySQL
        """
        try:
            conn = get_connection()
            if not conn:
                return False, "Erro de conexão com o banco de dados."
            cursor = conn.cursor()
            solicitacao_id = f"{equipe_id}_{datetime.now().timestamp()}"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sql = """
                INSERT INTO solicitacoes_compra (id, equipe_id, tipo, item_id, quantidade, timestamp, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (solicitacao_id, equipe_id, tipo, item_id, quantidade, timestamp, 'PENDENTE'))
            conn.commit()
            close_connection(conn)
            msg = f"✅ Solicitação registrada: {tipo} {item_id} (Qty: {quantidade})"
            logger.info(f"Nova solicitação: {equipe_id} - {msg}")
            return True, msg
        except Exception as e:
            logger.error(f"Erro ao criar solicitação: {e}")
            return False, f"❌ Erro: {str(e)}"
    
    def processar_solicitacoes(self) -> int:
        """
        Processa todas as solicitações pendentes do MySQL
        """
        solicitacoes = self._carregar_solicitacoes()
        processadas_count = 0

        for sol in solicitacoes:
            # Adicionar status se não existir (compatibilidade)
            if 'status' not in sol:
                sol['status'] = 'PENDENTE'

            if sol.get('status') == 'PENDENTE':
                sucesso = False
                mensagem = ""

                # Normalizar tipo para uppercase
                tipo = sol.get('tipo', '').upper()

                if tipo == 'CARRO':
                    sucesso, mensagem = self.api.processador_compras.processar_compra_carro(
                        sol['equipe_id'],
                        sol['item_id']
                    )
                elif tipo == 'PEÇA':
                    sucesso, mensagem = self.api.processador_compras.processar_compra_peca(
                        sol['equipe_id'],
                        sol['item_id']
                    )

                if sucesso:
                    sol['status'] = 'PROCESSADA'
                    sol['resultado'] = mensagem
                    self._mover_para_processadas(sol)
                    processadas_count += 1
                    logger.info(f"✅ Solicitação processada: {sol.get('id', 'sem-id')} - {mensagem}")
                else:
                    sol['status'] = 'ERRO'
                    sol['resultado'] = mensagem
                    self._mover_para_processadas(sol)
                    logger.error(f"❌ Erro ao processar: {sol.get('id', 'sem-id')} - {mensagem}")

                # Atualizar status na tabela solicitacoes_compra
                self._atualizar_status_solicitacao(sol['id'], sol['status'], sol.get('resultado', ''))

        return processadas_count
    
    def obter_solicitacoes_pendentes(self, equipe_id: Optional[str] = None) -> List[dict]:
        """Retorna solicitações pendentes do MySQL"""
        return self._carregar_solicitacoes(equipe_id, status='PENDENTE')

    def obter_historico_processadas(self, equipe_id: Optional[str] = None) -> List[dict]:
        """Retorna solicitações processadas do MySQL"""
        return self._carregar_processadas(equipe_id)

    def _carregar_solicitacoes(self, equipe_id: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        """Carrega solicitações do MySQL"""
        try:
            conn = get_connection()
            if not conn:
                return []

            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM solicitacoes_compra WHERE 1=1"
            params = []

            if equipe_id:
                query += " AND equipe_id = %s"
                params.append(equipe_id)

            if status:
                query += " AND status = %s"
                params.append(status)

            query += " ORDER BY timestamp DESC"
            cursor.execute(query, params)
            results = cursor.fetchall()
            close_connection(conn)
            return results
        except Exception as e:
            logger.error(f"Erro ao carregar solicitações: {e}")
            return []

    def _carregar_processadas(self, equipe_id: Optional[str] = None) -> List[dict]:
        """Carrega solicitações processadas do MySQL"""
        try:
            conn = get_connection()
            if not conn:
                return []

            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM solicitacoes_processadas WHERE 1=1"
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
            logger.error(f"Erro ao carregar processadas: {e}")
            return []

    def _mover_para_processadas(self, solicitacao: dict):
        """Move solicitação para tabela de processadas"""
        try:
            conn = get_connection()
            if not conn:
                return

            cursor = conn.cursor()
            sql = """
                INSERT INTO solicitacoes_processadas
                (id, equipe_id, tipo, item_id, quantidade, timestamp, status, resultado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                solicitacao['id'],
                solicitacao['equipe_id'],
                solicitacao['tipo'],
                solicitacao['item_id'],
                solicitacao['quantidade'],
                solicitacao['timestamp'],
                solicitacao['status'],
                solicitacao.get('resultado', '')
            ))
            conn.commit()
            close_connection(conn)
        except Exception as e:
            logger.error(f"Erro ao mover para processadas: {e}")

    def _atualizar_status_solicitacao(self, solicitacao_id: str, status: str, resultado: str = ""):
        """Atualiza status da solicitação"""
        try:
            conn = get_connection()
            if not conn:
                return

            cursor = conn.cursor()
            sql = "UPDATE solicitacoes_compra SET status = %s, resultado = %s WHERE id = %s"
            cursor.execute(sql, (status, resultado, solicitacao_id))
            conn.commit()
            close_connection(conn)
        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
    
    def iniciar_monitoramento(self):
        """Inicia thread de monitoramento"""
        if self.rodando:
            return
        
        self.rodando = True
        self.thread_monitor = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MonitorSolicitacoes"
        )
        self.thread_monitor.start()
        logger.info("🚀 Monitoramento de solicitações iniciado")
    
    def parar_monitoramento(self):
        """Para o monitoramento"""
        self.rodando = False
        if self.thread_monitor:
            self.thread_monitor.join(timeout=5)
        logger.info("⛔ Monitoramento parado")
    
    def _monitor_loop(self):
        """Loop de monitoramento automático"""
        while self.rodando:
            try:
                processadas = self.processar_solicitacoes()
                if processadas > 0:
                    logger.info(f"📊 {processadas} solicitação(ões) processada(s)")
                time.sleep(2)
            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
                time.sleep(1)
    
    def obter_status(self) -> dict:
        """Retorna status do gerenciador usando MySQL"""
        try:
            pendentes = len(self._carregar_solicitacoes(status='PENDENTE'))
            processadas = len(self._carregar_processadas())

            return {
                'banco': 'MySQL',
                'pendentes': pendentes,
                'processadas': processadas,
                'rodando': self.rodando
            }
        except Exception as e:
            logger.error(f"Erro ao obter status: {e}")
            return {
                'banco': 'MySQL',
                'erro': str(e),
                'rodando': self.rodando
            }
    
    def criar_arquivo_template_csv(self, equipe_id: str) -> str:
        """
        Cria um arquivo CSV template para a equipe preencher
        
        Args:
            equipe_id: ID da equipe
            
        Returns:
            Caminho do arquivo
        """
        arquivo_csv = self.pasta_solicitacoes / f"compras_{equipe_id}.csv"
        
        with open(arquivo_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['TIPO', 'ITEM_ID', 'QUANTIDADE', 'DATA'])
            writer.writerow(['CARRO', 'chevrolet-chevette', '1', datetime.now().isoformat()])
            writer.writerow(['PEÇA', 'ohc', '1', datetime.now().isoformat()])
        
        return str(arquivo_csv)
