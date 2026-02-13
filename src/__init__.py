"""
GRANPIX Racing Championship System
Sistema completo de gerenciamento para campeonato de corrida
"""

__version__ = "1.1.0"
__author__ = "GRANPIX Development Team"
__description__ = "Sistema de gerenciamento de pilotos, equipes, batalhas e recursos para campeonato de corrida"

from .config import (
    PREMIACAO_VITORIA_BATALHA,
    PREMIACAO_POR_ETAPA,
    DESGASTE_BASE_BATALHA,
    MULTIPLICADOR_DESGASTE_EMPATE,
    CHANCE_EMPATE
)
from .api import APIGranpix
from .models import (
    Piloto, Equipe, Carro, Peca, Batalha, Etapa,
    TipoDiferencial, ResultadoBatalha
)
from .database import DatabaseManager
from .team_manager import GerenciadorEquipes
from .battle_system import SistemaBatalha, SistemaDesgaste

__all__ = [
    'APIGranpix',
    'Piloto',
    'Equipe',
    'Carro',
    'Peca',
    'Batalha',
    'Etapa',
    'TipoDiferencial',
    'ResultadoBatalha',
    'DatabaseManager',
    'GerenciadorEquipes',
    'SistemaBatalha',
    'SistemaDesgaste',
    'PREMIACAO_VITORIA_BATALHA',
    'PREMIACAO_EMPATE_BATALHA',
    'PREMIACAO_POR_ETAPA',
    'DESGASTE_BASE_BATALHA',
    'MULTIPLICADOR_DESGASTE_EMPATE',
    'CHANCE_EMPATE',
]
