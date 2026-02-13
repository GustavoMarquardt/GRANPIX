"""
Sistema de gerenciamento de equipes
"""
from typing import List, Optional
from models import Equipe, Piloto, Peca, TipoPeca, TipoCompra
import json
import os
from werkzeug.security import generate_password_hash
import uuid


class GerenciadorEquipes:
    """Gerencia equipes, pilotos e peças"""
    
    def __init__(self, arquivo_dados: str = "dados_equipes.json"):
        self.arquivo_dados = arquivo_dados
        self.equipes: List[Equipe] = []
        self.carregar_dados()
    
    def carregar_dados(self):
        """Carrega equipes do arquivo JSON"""
        if os.path.exists(self.arquivo_dados):
            try:
                with open(self.arquivo_dados, 'r', encoding='utf-8') as f:
                    # Implementar carregamento se necessário
                    pass
            except:
                self.equipes = []
        else:
            self.equipes = []
    
    def salvar_dados(self):
        """Salva equipes em arquivo JSON"""
        # Implementar salvamento se necessário
        pass
    
    def criar_equipe(self, nome: str, saldo_inicial: float = 1000.0) -> Equipe:
        """Cria nova equipe"""
        equipe = Equipe(nome=nome, saldo=saldo_inicial)
        self.equipes.append(equipe)
        self.salvar_dados()
        return equipe
    
    def obter_equipe(self, equipe_id: str) -> Optional[Equipe]:
        """Obtém equipe por ID"""
        for eq in self.equipes:
            if eq.id == equipe_id:
                return eq
        return None
    
    def listar_equipes(self) -> List[Equipe]:
        """Lista todas as equipes"""
        return self.equipes
    
    def adicionar_piloto(self, equipe_id: str, nome_piloto: str) -> Optional[Piloto]:
        """Adiciona piloto à equipe"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe:
            return None
        
        piloto = Piloto(nome=nome_piloto)
        equipe.adicionar_piloto(piloto)
        self.salvar_dados()
        return piloto
    
    def adicionar_peca(self, equipe_id: str, nome: str, tipo: str, preco: float) -> Optional[Peca]:
        """Adiciona peça ao carro"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe:
            return None
        
        try:
            tipo_peca = TipoPeca[tipo.upper()]
        except KeyError:
            tipo_peca = TipoPeca.MOTOR
        
        peca = Peca(nome=nome, tipo=tipo_peca, preco=preco)
        equipe.adicionar_peca(peca)
        equipe.registrar_compra(TipoCompra.COMPRA, f"Compra de {nome}", preco)
        self.salvar_dados()
        return peca
    
    def registrar_vitoria(self, equipe_id: str, piloto_nome: str, premio: float = 100.0):
        """Registra vitória de um piloto"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe:
            return
        
        # Encontrar piloto
        piloto = next((p for p in equipe.pilotos if p.nome == piloto_nome), None)
        if piloto:
            piloto.vitoria += 1
            equipe.registrar_compra(TipoCompra.PRÊMIO, f"Prêmio vitória - {piloto_nome}", premio)
            self.salvar_dados()
    
    def registrar_derrota(self, equipe_id: str, piloto_nome: str):
        """Registra derrota de um piloto"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe:
            return
        
        piloto = next((p for p in equipe.pilotos if p.nome == piloto_nome), None)
        if piloto:
            piloto.derrota += 1
            self.salvar_dados()
    
    def danificar_peca(self, equipe_id: str, indice_peca: int, dano: float):
        """Reduz saúde de uma peça"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe or indice_peca >= len(equipe.pecas):
            return
        
        peca = equipe.pecas[indice_peca]
        peca.saude = max(0, peca.saude - dano)
        self.salvar_dados()
    
    def reparar_peca(self, equipe_id: str, indice_peca: int, custo: float) -> bool:
        """Repara uma peça"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe or indice_peca >= len(equipe.pecas):
            return False
        
        if equipe.saldo < custo:
            return False
        
        peca = equipe.pecas[indice_peca]
        peca.saude = 100.0
        equipe.registrar_compra(TipoCompra.COMPRA, f"Reparo de {peca.nome}", custo)
        self.salvar_dados()
        return True

    def adicionar_equipe(self, nome: str, senha: str) -> Equipe:
        """Adiciona uma nova equipe com senha hash"""
        equipe = Equipe(
            id=str(uuid.uuid4()),
            nome=nome,
            senha=generate_password_hash(senha),
            doricoins=0.0,
            pilotos=[],
            historico_batalhas=[],
            carros=[]
        )
        self.equipes.append(equipe)
        self.salvar_dados()
        return equipe
