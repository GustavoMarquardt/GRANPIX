"""
Monitor de Auto-Export - Atualiza Excel automaticamente quando dados mudam no banco
"""
import threading
import time
from typing import Dict, Set, Callable, Optional
from datetime import datetime
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - AUTO_EXPORT - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoExportMonitor:
    """Monitora mudanças no banco de dados e atualiza Excels automaticamente
    
    ⚠️ APENAS EQUIPES: Exporta apenas quando dados da equipe mudam
    (saldo, batalhas, desgaste de peças) - NÃO exporta por mudanças de pilotos
    """
    
    def __init__(self, exportador_excel, db_manager, gerenciador_equipes):
        """
        Inicializa o monitor de auto-export
        
        Args:
            exportador_excel: Instância do ExportadorEquipes
            db_manager: Instância do DatabaseManager
            gerenciador_equipes: Instância do GerenciadorEquipes
        """
        self.exportador = exportador_excel
        self.db = db_manager
        self.gerenciador = gerenciador_equipes
        
        # Rastreamento de mudanças de EQUIPE (não pilotos)
        self.equipes_modificadas: Set[str] = set()
        self.lock = threading.Lock()
        
        # Controle de thread
        self.rodando = False
        self.thread_monitor: Optional[threading.Thread] = None
        
        # Configurações
        self.intervalo_verificacao = 2  # segundos (intervalo para verificar mudanças)
        self.intervalo_export = 5  # segundos (tempo mínimo entre exports da mesma equipe)
        
        logger.info("📊 Auto-Export: APENAS MUDANÇAS DE EQUIPE (saldo, batalhas, desgaste)")
        
        # Timestamp da última exportação por equipe
        self.ultimo_export: Dict[str, float] = {}
        
        # Callbacks customizadas
        self.callbacks: Dict[str, list] = {
            'before_export': [],
            'after_export': [],
            'error': []
        }
    
    def registrar_mudanca(self, equipe_id: str) -> None:
        """
        Registra que uma equipe foi modificada
        
        ⚠️ Use APENAS para mudanças de dados da equipe:
           - Batalhas (vitória/derrota)
           - Saldo alterado
           - Desgaste de peças
        
        ❌ NÃO use para pilotos/adição de pilotos
        
        Args:
            equipe_id: ID da equipe que mudou
        """
        with self.lock:
            self.equipes_modificadas.add(equipe_id)
            logger.info(f"📝 Mudança de EQUIPE registrada: {equipe_id}")
    
    def registrar_mudancas_multiplas(self, equipe_ids: list) -> None:
        """
        Registra mudanças em múltiplas equipes
        
        Args:
            equipe_ids: Lista de IDs de equipes modificadas
        """
        with self.lock:
            self.equipes_modificadas.update(equipe_ids)
            logger.info(f"📝 Mudanças detectadas em {len(equipe_ids)} equipe(s)")
    
    def adicionar_callback(self, evento: str, callback: Callable) -> None:
        """
        Adiciona callback para eventos de export
        
        Args:
            evento: 'before_export', 'after_export' ou 'error'
            callback: Função a chamar
        """
        if evento in self.callbacks:
            self.callbacks[evento].append(callback)
    
    def _executar_callbacks(self, evento: str, equipe_id: str, **kwargs) -> None:
        """Executa callbacks para um evento"""
        for callback in self.callbacks[evento]:
            try:
                callback(equipe_id=equipe_id, **kwargs)
            except Exception as e:
                logger.error(f"Erro ao executar callback {evento}: {e}")
    
    def _pode_exportar(self, equipe_id: str) -> bool:
        """
        Verifica se é hora de exportar (evita muitos exports seguidos)
        
        Args:
            equipe_id: ID da equipe
            
        Returns:
            True se pode exportar, False se está em cooldown
        """
        agora = time.time()
        ultimo = self.ultimo_export.get(equipe_id, 0)
        
        if agora - ultimo < self.intervalo_export:
            return False
        
        return True
    
    def exportar_equipe(self, equipe_id: str, forcar: bool = False) -> bool:
        """
        Exporta uma equipe para Excel
        
        Args:
            equipe_id: ID da equipe
            forcar: Se True, ignora o cooldown
            
        Returns:
            True se exportado com sucesso
        """
        if not forcar and not self._pode_exportar(equipe_id):
            return False
        
        try:
            equipe = self.gerenciador.obter_equipe(equipe_id)
            if not equipe:
                logger.warning(f"Equipe não encontrada: {equipe_id}")
                return False
            
            # Callback antes do export
            self._executar_callbacks('before_export', equipe_id)
            
            # Exportar
            caminho = self.exportador.exportar_equipe(equipe)
            
            # Atualizar timestamp
            self.ultimo_export[equipe_id] = time.time()
            
            # Callback após export
            self._executar_callbacks('after_export', equipe_id, caminho=caminho)
            
            logger.info(f"✅ Equipe exportada: {equipe_id} → {caminho}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao exportar equipe {equipe_id}: {e}")
            self._executar_callbacks('error', equipe_id, erro=str(e))
            return False
    
    def processar_fila(self) -> int:
        """
        Processa todas as equipes que foram modificadas
        
        Returns:
            Número de equipes exportadas
        """
        with self.lock:
            equipes_para_exportar = list(self.equipes_modificadas)
            self.equipes_modificadas.clear()
        
        exportadas = 0
        for equipe_id in equipes_para_exportar:
            if self.exportar_equipe(equipe_id):
                exportadas += 1
        
        return exportadas
    
    def iniciar(self) -> None:
        """Inicia o monitor em background"""
        if self.rodando:
            logger.warning("Monitor já está rodando")
            return
        
        self.rodando = True
        self.thread_monitor = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="AutoExportMonitor"
        )
        self.thread_monitor.start()
        logger.info("🚀 Monitor de Auto-Export iniciado")
    
    def parar(self) -> None:
        """Para o monitor"""
        if not self.rodando:
            return
        
        self.rodando = False
        if self.thread_monitor:
            self.thread_monitor.join(timeout=5)
        
        logger.info("⛔ Monitor de Auto-Export parado")
    
    def _monitor_loop(self) -> None:
        """Loop principal de monitoramento"""
        logger.info("🔄 Thread de monitoramento ativa")
        
        while self.rodando:
            try:
                # Processar fila de mudanças
                exportadas = self.processar_fila()
                
                if exportadas > 0:
                    logger.info(f"📊 {exportadas} equipe(s) sincronizada(s)")
                
                # Aguardar antes de verificar novamente
                time.sleep(self.intervalo_verificacao)
                
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(1)
    
    def exportar_todas_agora(self, forcar: bool = False) -> int:
        """
        Exporta todas as equipes imediatamente
        
        Args:
            forcar: Se True, ignora o cooldown
            
        Returns:
            Número de equipes exportadas
        """
        equipes = self.gerenciador.listar_equipes()
        exportadas = 0
        
        for equipe in equipes:
            if self.exportar_equipe(equipe.id, forcar=forcar):
                exportadas += 1
        
        return exportadas
    
    def obter_status(self) -> Dict:
        """Retorna status atual do monitor"""
        with self.lock:
            pendentes = len(self.equipes_modificadas)
        
        return {
            'rodando': self.rodando,
            'equipes_pendentes': pendentes,
            'ultimo_export': self.ultimo_export.copy(),
            'intervalo_verificacao': self.intervalo_verificacao,
            'intervalo_export': self.intervalo_export
        }


class DecoradorAutoExport:
    """Decorador para adicionar auto-export a métodos que modificam dados"""
    
    def __init__(self, monitor: AutoExportMonitor):
        self.monitor = monitor
    
    def monitora_mudanca_equipe(self, equipe_id_param: str = 'equipe_id'):
        """
        Decorador que registra mudança após o método
        
        Args:
            equipe_id_param: Nome do parâmetro que contém o equipe_id
        """
        def decorador(func):
            def wrapper(*args, **kwargs):
                resultado = func(*args, **kwargs)
                
                # Extrair equipe_id
                equipe_id = kwargs.get(equipe_id_param)
                if not equipe_id and len(args) > 0:
                    # Tenta no primeiro argumento posicional (depois de self)
                    for i, arg in enumerate(args):
                        if isinstance(arg, str) and arg.startswith('eq-'):
                            equipe_id = arg
                            break
                
                if equipe_id:
                    self.monitor.registrar_mudanca(equipe_id)
                
                return resultado
            
            return wrapper
        return decorador
