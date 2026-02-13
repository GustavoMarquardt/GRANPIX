"""
Monitor Automático de Compras - Sistema 100% Automático
Quando usuário clica COMPRAR no Excel, processa imediatamente SEM intervenção manual
"""
import threading
import time
import json
import os
from typing import Optional, Set, Dict
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MONITOR_COMPRAS - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MonitorComprasAutomatico:
    """Monitora pasta de solicitações e processa compras automaticamente"""
    
    def __init__(self, processador_compras, pasta_solicitacoes: str = "data/solicitacoes_compra"):
        """
        Inicializa monitor automático de compras
        
        Args:
            processador_compras: Instância de ProcessadorCompras
            pasta_solicitacoes: Pasta onde VBA escreve as solicitações JSON
        """
        self.processador = processador_compras
        self.pasta = pasta_solicitacoes
        os.makedirs(self.pasta, exist_ok=True)
        
        self.arquivo_solicitacoes = os.path.join(self.pasta, "solicitacoes.json")
        
        # Estado do monitor
        self.rodando = False
        self.thread_monitor: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Rastrear solicitações já processadas
        self.processadas: Set[str] = set()
        self.ultima_verificacao = 0
        self.intervalo_verificacao = 0.5  # Verificar a cada 500ms
        
        logger.info(f"🛒 Monitor de Compras Automático inicializado")
        logger.info(f"📂 Pasta monitorada: {self.pasta}")
    
    def iniciar(self) -> None:
        """Inicia o monitor em background"""
        if self.rodando:
            logger.warning("Monitor já está rodando")
            return
        
        self.rodando = True
        self.thread_monitor = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MonitorComprasAutomatico"
        )
        self.thread_monitor.start()
        logger.info("🚀 Monitor de Compras Automático iniciado")
    
    def parar(self) -> None:
        """Para o monitor"""
        if not self.rodando:
            return
        
        logger.info("⛔ Parando Monitor de Compras Automático...")
        self.rodando = False
        if self.thread_monitor:
            try:
                self.thread_monitor.join(timeout=2)
            except:
                pass
        
        logger.info("✓ Monitor de Compras Automático parado")
    
    def _monitor_loop(self) -> None:
        """Loop principal de monitoramento"""
        logger.info("🔄 Thread de monitoramento de compras ativa")
        
        while self.rodando:
            try:
                agora = time.time()
                if agora - self.ultima_verificacao >= self.intervalo_verificacao:
                    self._processar_solicitacoes()
                    self.ultima_verificacao = agora
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(1)
    
    def _processar_solicitacoes(self) -> None:
        """Processa todas as solicitações pendentes"""
        if not os.path.exists(self.arquivo_solicitacoes):
            return
        
        try:
            with open(self.arquivo_solicitacoes, 'r', encoding='utf-8') as f:
                solicitacoes = json.load(f)
            
            if not solicitacoes:
                return
            
            # Processar cada solicitação
            processadas = []
            for i, sol in enumerate(solicitacoes):
                id_sol = f"{sol.get('equipe_id', '')}_{sol.get('tipo', '')}_{i}"
                
                if id_sol in self.processadas:
                    continue
                
                # Processar
                sucesso = self._processar_solicitacao(sol)
                
                if sucesso:
                    self.processadas.add(id_sol)
                    processadas.append(i)
            
            # Remover solicitações processadas
            if processadas:
                # Manter apenas as não processadas
                novas_solicitacoes = [s for j, s in enumerate(solicitacoes) if j not in processadas]
                
                with open(self.arquivo_solicitacoes, 'w', encoding='utf-8') as f:
                    json.dump(novas_solicitacoes, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ {len(processadas)} solicitação(ões) processada(s) e removida(s)")
        
        except json.JSONDecodeError:
            logger.warning("Arquivo de solicitações vazio ou inválido")
        except Exception as e:
            logger.error(f"Erro ao processar solicitações: {e}")
    
    def _processar_solicitacao(self, solicitacao: Dict) -> bool:
        """
        Processa uma solicitação de compra
        
        Args:
            solicitacao: Dicionário com equipe_id, tipo, e id da compra
            
        Returns:
            True se processado com sucesso
        """
        try:
            equipe_id = solicitacao.get('equipe_id')
            tipo = solicitacao.get('tipo')  # 'carro' ou 'peca'
            item_id = solicitacao.get('item_id')
            
            if not all([equipe_id, tipo, item_id]):
                logger.warning(f"Solicitação incompleta: {solicitacao}")
                return False
            
            # Normalizar tipo (lowercase)
            tipo = str(tipo).lower().strip()
            
            # Processar
            if tipo == 'carro':
                sucesso, msg = self.processador.processar_compra_carro(equipe_id, item_id)
            elif tipo == 'peca':
                sucesso, msg = self.processador.processar_compra_peca(equipe_id, item_id)
            else:
                # Tipo desconhecido - silencioso para não poluir logs
                return False
            
            if sucesso:
                logger.info(f"🎉 COMPRA AUTOMÁTICA: {msg}")
            else:
                logger.warning(f"⚠️  Compra falhou: {msg}")
            
            return sucesso
        
        except Exception as e:
            logger.error(f"Erro ao processar solicitação: {e}")
            return False
    
    def obter_status(self) -> Dict:
        """Retorna status do monitor"""
        return {
            'rodando': self.rodando,
            'processadas': len(self.processadas),
            'pasta_monitorada': self.pasta,
            'intervalo': self.intervalo_verificacao
        }
