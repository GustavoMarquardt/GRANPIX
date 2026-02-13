"""
Extensões de Auto-Export para a API GRANPIX
Adiciona métodos para gerenciar o auto-export de dados
"""


def adicionar_metodos_auto_export(api):
    """
    Adiciona métodos de auto-export à API
    
    Args:
        api: Instância de APIGranpix
    """
    
    # ========== MÉTODOS DE GERENCIAMENTO DO AUTO-EXPORT ==========
    
    def ativar_auto_export(self) -> bool:
        """Ativa o sistema de auto-export"""
        if not self.auto_export_habilitado:
            self.auto_export_monitor = AutoExportMonitor(
                self.exportador_excel,
                self.db,
                self.gerenciador
            )
            self.auto_export_monitor.iniciar()
            self.auto_export_habilitado = True
            print("✅ Auto-export ativado!")
            return True
        return False
    
    def desativar_auto_export(self) -> bool:
        """Desativa o sistema de auto-export"""
        if self.auto_export_habilitado and self.auto_export_monitor:
            self.auto_export_monitor.parar()
            self.auto_export_habilitado = False
            print("⛔ Auto-export desativado!")
            return True
        return False
    
    def obter_status_auto_export(self) -> dict:
        """Retorna o status atual do auto-export"""
        if self.auto_export_monitor:
            status = self.auto_export_monitor.obter_status()
            status['habilitado'] = self.auto_export_habilitado
            return status
        return {'habilitado': False}
    
    def exportar_todas_agora(self, forcar: bool = False) -> int:
        """
        Exporta todas as equipes para Excel imediatamente
        
        Args:
            forcar: Se True, ignora o cooldown entre exports
            
        Returns:
            Número de equipes exportadas
        """
        if self.auto_export_monitor:
            return self.auto_export_monitor.exportar_todas_agora(forcar=forcar)
        
        # Fallback: exportar manualmente se monitor não existe
        equipes = self.gerenciador.listar_equipes()
        exportadas = 0
        for equipe in equipes:
            try:
                self.exportador_excel.exportar_equipe_silencioso(equipe)
                exportadas += 1
            except Exception as e:
                print(f"Erro ao exportar {equipe.nome}: {e}")
        
        return exportadas
    
    # ========== MÉTODOS MODIFICADOS COM AUTO-EXPORT ==========
    
    def criar_equipe_novo_auto(self, nome: str, doricoins_iniciais: float = 1000.0):
        """Cria uma equipe e registra a mudança para auto-export"""
        equipe = self.criar_equipe_novo(nome, doricoins_iniciais)
        if equipe and self.auto_export_monitor:
            self.auto_export_monitor.registrar_mudanca(equipe.id)
        return equipe
    
    def registrar_piloto_auto(self, nome: str, equipe_id: str):
        """Registra um piloto e dispara auto-export"""
        piloto = self.registrar_piloto(nome, equipe_id)
        if piloto and self.auto_export_monitor:
            self.auto_export_monitor.registrar_mudanca(equipe_id)
        return piloto
    
    def registrar_batalha_auto(self, piloto_a_id: str, piloto_b_id: str, 
                              etapa: int = 1) -> bool:
        """Registra batalha e dispara auto-export para ambas as equipes"""
        # Registrar batalha sem auto-export manual
        batalha = self.registrar_batalha(piloto_a_id, piloto_b_id, etapa, auto_exportar=False)
        
        if batalha and self.auto_export_monitor:
            # Registrar mudanças para ambas as equipes
            piloto_a = self.gerenciador.obter_piloto(piloto_a_id)
            piloto_b = self.gerenciador.obter_piloto(piloto_b_id)
            if piloto_a and piloto_b:
                self.auto_export_monitor.registrar_mudancas_multiplas([
                    piloto_a.equipe_id,
                    piloto_b.equipe_id
                ])
        
        return batalha is not None
    
    def comprar_carro_auto(self, equipe_id: str, modelo_id: str) -> bool:
        """Compra carro e dispara auto-export"""
        resultado = self.comprar_carro(equipe_id, modelo_id)
        if resultado and self.auto_export_monitor:
            self.auto_export_monitor.registrar_mudanca(equipe_id)
        return resultado
    
    def comprar_peca_auto(self, equipe_id: str, peca_id: str) -> bool:
        """Compra peça e dispara auto-export"""
        resultado = self.comprar_peca(equipe_id, peca_id)
        if resultado and self.auto_export_monitor:
            self.auto_export_monitor.registrar_mudanca(equipe_id)
        return resultado
    
    def reparar_carro_auto(self, equipe_id: str, id_peca: str) -> bool:
        """Repara carro e dispara auto-export"""
        resultado = self.reparar_carro(equipe_id, id_peca)
        if resultado and self.auto_export_monitor:
            self.auto_export_monitor.registrar_mudanca(equipe_id)
        return resultado
    
    # ========== CALLBACK PARA MONITORAMENTO ==========
    
    def registrar_callback_auto_export(self, evento: str, callback) -> None:
        """
        Registra callback para eventos de auto-export
        
        Args:
            evento: 'before_export', 'after_export' ou 'error'
            callback: Função callback(equipe_id, **kwargs)
        """
        if self.auto_export_monitor:
            self.auto_export_monitor.adicionar_callback(evento, callback)


# Aplicar métodos à classe
from api import APIGranpix
from auto_export_monitor import AutoExportMonitor

APIGranpix.ativar_auto_export = ativar_auto_export
APIGranpix.desativar_auto_export = desativar_auto_export
APIGranpix.obter_status_auto_export = obter_status_auto_export
APIGranpix.exportar_todas_agora = exportar_todas_agora
APIGranpix.criar_equipe_novo_auto = criar_equipe_novo_auto
APIGranpix.registrar_piloto_auto = registrar_piloto_auto
APIGranpix.registrar_batalha_auto = registrar_batalha_auto
APIGranpix.comprar_carro_auto = comprar_carro_auto
APIGranpix.comprar_peca_auto = comprar_peca_auto
APIGranpix.reparar_carro_auto = reparar_carro_auto
APIGranpix.registrar_callback_auto_export = registrar_callback_auto_export
