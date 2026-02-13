"""
Interface Simplificada para Compras no GRANPIX
Facilita integração com Excel ou outros sistemas
"""
import json
import os
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from datetime import datetime


class ComprasGranpix:
    """Interface simplificada para fazer compras no GRANPIX"""
    
    def __init__(self, api=None):
        """
        Inicializa o gerenciador de compras
        
        Args:
            api: Instância de APIGranpix (opcional)
        """
        self.api = api
        self.pasta_solicitacoes = Path("data/solicitacoes_compra")
        self.pasta_solicitacoes.mkdir(parents=True, exist_ok=True)
        self.arquivo_solicitacoes = self.pasta_solicitacoes / "solicitacoes.json"
    
    def comprar_carro(self, equipe_id: str, modelo_carro: str) -> Tuple[bool, str]:
        """
        Solicita a compra de um carro
        
        Args:
            equipe_id: ID da equipe
            modelo_carro: Modelo do carro (ex: 'chevrolet-chevette')
            
        Returns:
            (sucesso, mensagem)
        """
        return self._criar_solicitacao(equipe_id, 'CARRO', modelo_carro)
    
    def comprar_peca(self, equipe_id: str, peca_id: str) -> Tuple[bool, str]:
        """
        Solicita a compra de uma peça
        
        Args:
            equipe_id: ID da equipe
            peca_id: ID da peça (ex: 'ohc')
            
        Returns:
            (sucesso, mensagem)
        """
        return self._criar_solicitacao(equipe_id, 'PEÇA', peca_id)
    
    def _criar_solicitacao(self, equipe_id: str, tipo: str, item_id: str) -> Tuple[bool, str]:
        """Cria uma solicitação de compra"""
        try:
            # Carregar solicitações existentes
            solicitacoes = self._carregar()
            
            # Criar nova solicitação
            solicitacao = {
                "id": f"{equipe_id}_{datetime.now().timestamp()}",
                "equipe_id": equipe_id,
                "tipo": tipo,
                "item_id": item_id,
                "quantidade": 1,
                "timestamp": datetime.now().isoformat(),
                "status": "PENDENTE"
            }
            
            solicitacoes.append(solicitacao)
            self._salvar(solicitacoes)
            
            return True, f"✅ Solicitação de {tipo} '{item_id}' enviada"
            
        except Exception as e:
            return False, f"❌ Erro: {str(e)}"
    
    def obter_pendentes(self, equipe_id: Optional[str] = None) -> List[Dict]:
        """
        Retorna solicitações pendentes
        
        Args:
            equipe_id: ID da equipe (opcional, filtra se fornecido)
            
        Returns:
            Lista de solicitações pendentes
        """
        solicitacoes = self._carregar()
        pendentes = [s for s in solicitacoes if s.get('status') == 'PENDENTE']
        
        if equipe_id:
            pendentes = [s for s in pendentes if s.get('equipe_id') == equipe_id]
        
        return pendentes
    
    def limpar_pendentes(self) -> Tuple[bool, int]:
        """
        Remove todas as solicitações processadas ou com erro
        
        Returns:
            (sucesso, quantidade_removida)
        """
        try:
            # Carregar solicitações
            solicitacoes = self._carregar()
            
            # Manter apenas PENDENTE
            pendentes = [s for s in solicitacoes if s.get('status') == 'PENDENTE']
            
            # Salvar
            self._salvar(pendentes)
            
            removida = len(solicitacoes) - len(pendentes)
            return True, removida
            
        except Exception as e:
            return False, 0
    
    def _carregar(self) -> List[Dict]:
        """Carrega solicitações do arquivo"""
        if not self.arquivo_solicitacoes.exists():
            return []
        
        try:
            with open(self.arquivo_solicitacoes, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _salvar(self, dados: List[Dict]):
        """Salva solicitações no arquivo"""
        with open(self.arquivo_solicitacoes, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)


# Exemplo de uso
if __name__ == "__main__":
    compras = ComprasGranpix()
    
    # Simular compras
    print("=== TESTE COMPRAS GRANPIX ===\n")
    
    equipe_id = "f638670c-9445-4e64-85ff-b4d46dadf8e1"  # S23-GOMES
    
    print("🛒 Comprar Chevrolet Chevette...")
    sucesso, msg = compras.comprar_carro(equipe_id, "chevrolet-chevette")
    print(f"   {msg}\n")
    
    print("🛒 Comprar OHC...")
    sucesso, msg = compras.comprar_peca(equipe_id, "ohc")
    print(f"   {msg}\n")
    
    print("📋 Solicitações Pendentes:")
    pendentes = compras.obter_pendentes()
    for p in pendentes:
        print(f"   - {p['tipo']}: {p['item_id']} (Status: {p['status']})")
    
    print(f"\n✅ Total de pendentes: {len(pendentes)}")
    
    print("\n⏳ Sistema processará em 2-3 segundos...")
