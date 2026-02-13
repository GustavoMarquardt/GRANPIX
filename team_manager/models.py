"""
Modelos de dados para o sistema de gerenciamento de equipes
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from enum import Enum
import uuid


class TipoPeca(Enum):
    """Tipos de peças disponíveis"""
    MOTOR = "motor"
    CAMBIO = "câmbio"
    SUSPENSAO = "suspensão"
    FREIO = "freio"
    PNEU = "pneu"


class TipoCompra(Enum):
    """Tipos de transações financeiras"""
    COMPRA = "Compra"
    VENDA = "Venda"
    PRÊMIO = "Prêmio Vitória"
    SALÁRIO = "Salário"


@dataclass
class Peca:
    """Modelo de peça do carro"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str = ""
    tipo: TipoPeca = TipoPeca.MOTOR
    saude: float = 100.0  # Percentual 0-100
    preco: float = 0.0
    data_compra: datetime = field(default_factory=datetime.now)
    
    def get_status(self) -> str:
        """Retorna status visual da peça"""
        if self.saude >= 70:
            return "🟢 Bom"
        elif self.saude >= 40:
            return "🟡 Regular"
        else:
            return "🔴 Crítico"


@dataclass
class Compra:
    """Registro de compra/venda"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tipo: TipoCompra = TipoCompra.COMPRA
    descricao: str = ""
    valor: float = 0.0
    data: datetime = field(default_factory=datetime.now)
    saldo_anterior: float = 0.0
    saldo_posterior: float = 0.0


@dataclass
class Piloto:
    """Modelo de piloto"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str = ""
    vitoria: int = 0
    derrota: int = 0
    empate: int = 0
    data_criacao: datetime = field(default_factory=datetime.now)
    
    def get_taxa_vitoria(self) -> float:
        """Calcula taxa de vitória"""
        total = self.vitoria + self.derrota + self.empate
        if total == 0:
            return 0.0
        return (self.vitoria / total) * 100


@dataclass
class Equipe:
    """Modelo de equipe"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str = ""
    saldo: float = 1000.0  # Doricoins
    pilotos: List[Piloto] = field(default_factory=list)
    pecas: List[Peca] = field(default_factory=list)
    historico_compras: List[Compra] = field(default_factory=list)
    data_criacao: datetime = field(default_factory=datetime.now)
    
    def adicionar_piloto(self, piloto: Piloto):
        """Adiciona piloto à equipe"""
        if piloto not in self.pilotos:
            self.pilotos.append(piloto)
    
    def adicionar_peca(self, peca: Peca):
        """Adiciona peça ao carro"""
        if peca not in self.pecas:
            self.pecas.append(peca)
    
    def registrar_compra(self, tipo: TipoCompra, descricao: str, valor: float):
        """Registra uma compra ou venda"""
        saldo_anterior = self.saldo
        
        if tipo == TipoCompra.COMPRA:
            self.saldo -= valor
        elif tipo == TipoCompra.VENDA:
            self.saldo += valor
        elif tipo in [TipoCompra.PRÊMIO, TipoCompra.SALÁRIO]:
            self.saldo += valor
        
        saldo_posterior = self.saldo
        
        compra = Compra(
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            data=datetime.now(),
            saldo_anterior=saldo_anterior,
            saldo_posterior=saldo_posterior
        )
        
        self.historico_compras.append(compra)
        return compra
    
    def get_vitoria_total(self) -> int:
        """Retorna total de vitórias de todos os pilotos"""
        return sum(p.vitoria for p in self.pilotos)
    
    def get_derrota_total(self) -> int:
        """Retorna total de derrotas de todos os pilotos"""
        return sum(p.derrota for p in self.pilotos)
    
    def get_empate_total(self) -> int:
        """Retorna total de empates de todos os pilotos"""
        return sum(p.empate for p in self.pilotos)
    
    def get_saude_media_pecas(self) -> float:
        """Retorna saúde média das peças"""
        if not self.pecas:
            return 100.0
        return sum(p.saude for p in self.pecas) / len(self.pecas)
