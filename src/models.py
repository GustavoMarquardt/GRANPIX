"""
Modelos de dados para o sistema de corrida GRANPIX
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
from datetime import datetime
import random
from .config import (
    PREMIACAO_VITORIA_BATALHA,
    PREMIACAO_POR_ETAPA,
    DESGASTE_BASE_BATALHA
)


class TipoDiferencial(Enum):
    """Tipos de diferenciais disponíveis"""
    OPEN = "aberto"
    LIMITED_SLIP = "deslizamento_limitado"
    HELICAL = "helicoidal"
    SPOOL = "spool"


@dataclass
class Peca:
    """Representa uma peça do carro"""
    id: str
    nome: str
    tipo: str  # "motor", "cambio", "kit_angulo", "suspensao", "diferencial"
    durabilidade_maxima: float  # 0-100%
    durabilidade_atual: float = 100.0
    preco: float = 0.0  # Custo para reparar/substituir
    coeficiente_quebra: float = 1.0  # Multiplicador de desgaste (0.5 = 50% menos desgaste, 1.5 = 50% mais desgaste)
    
    def sofrer_desgaste(self, quantidade: float, d20_resultado: int = None) -> float:
        """Reduz a durabilidade da peça baseado no coeficiente de quebra e resultado do D20
        
        Args:
            quantidade: Valor base de desgaste
            d20_resultado: Resultado do D20 (1-20). Se for 1, desgaste é dobrado
            
        Returns:
            Valor real de desgaste aplicado
        """
        # Se não fornecido, gera um D20
        if d20_resultado is None:
            d20_resultado = random.randint(1, 20)
        
        # Se saiu 1, dobra o desgaste
        desgaste_aplicado = quantidade * self.coeficiente_quebra
        if d20_resultado == 1:
            desgaste_aplicado *= 2
        
        self.durabilidade_atual = max(0, self.durabilidade_atual - desgaste_aplicado)
        return desgaste_aplicado
    
    def reparar(self, percentual: float = 100.0) -> None:
        """Repara a peça até um percentual máximo"""
        self.durabilidade_atual = min(self.durabilidade_maxima, 
                                      self.durabilidade_atual + (self.durabilidade_maxima * percentual / 100))
    
    def needs_repair(self) -> bool:
        """Retorna True se a peça está abaixo de 50% de durabilidade"""
        return (self.durabilidade_atual / self.durabilidade_maxima) < 0.5


@dataclass
class Carro:
    """Representa um carro com todas suas peças"""
    id: str
    numero_carro: int
    marca: str  # "Toyota", "Honda", "Nissan", etc.
    modelo: str
    motor: Peca
    cambio: Peca
    kit_angulo: Peca
    suspensao: Peca
    diferenciais: List[Peca] = field(default_factory=list)  # Pode ter mais de um
    pecas_instaladas: List[dict] = field(default_factory=list)  # Peças compradas e instaladas (mantém compatibilidade)
    batidas_totais: int = 0
    vitoria: int = 0
    derrotas: int = 0
    empates: int = 0
    status: str = 'ativo'  # 'ativo' ou 'repouso'
    timestamp_ativo: str = ''  # Data de quando ficou ativo
    timestamp_repouso: str = ''  # Data de quando foi para repouso
    modelo_id: str = ''  # ID do modelo de carro em modelos_loja (para compatibilidade de peças)
    motor_id: str = ''  # ID da peça motor
    cambio_id: str = ''  # ID da peça cambio
    suspensao_id: str = ''  # ID da peça suspensao
    kit_angulo_id: str = ''  # ID da peça kit_angulo
    diferencial_id: str = ''  # ID da peça diferencial (primeira)
    
    def get_todas_pecas(self) -> List[Peca]:
        """Retorna todas as peças do carro"""
        # Filtrar None para não quebrar cálculos
        return [p for p in [self.motor, self.cambio, self.kit_angulo, self.suspensao] + self.diferenciais if p is not None]
    
    def calcular_condicao_geral(self) -> float:
        """Retorna a condição média do carro (0-100%)"""
        pecas = self.get_todas_pecas()
        if not pecas:
            return 100.0
        media = sum((p.durabilidade_atual / p.durabilidade_maxima * 100) for p in pecas) / len(pecas)
        return media
    
    def sofrer_desgaste_batalha(self, desgaste_base: float, empate: bool = False) -> Tuple[List[str], Dict[str, Tuple[int, float]]]:
        """Aplica desgaste a todas as peças após uma batalha com D20
        
        Args:
            desgaste_base: Valor base de desgaste
            empate: Se True, causa 50% mais desgaste
        
        Returns:
            Tupla contendo:
            - Lista de nomes de peças que quebraram
            - Dicionário com {nome_peca: (resultado_d20, desgaste_aplicado)}
        """
        multiplicador = 1.5 if empate else 1.0  # Empate causa 50% mais desgaste
        pecas_quebradas = []
        resultados_d20 = {}
        
        for peca in self.get_todas_pecas():
            # Gerar D20 para a peça
            d20_resultado = random.randint(1, 20)
            
            # Aplicar desgaste com o D20
            desgaste_real = peca.sofrer_desgaste(desgaste_base * multiplicador, d20_resultado)
            
            # Registrar resultado do D20 e desgaste aplicado
            resultados_d20[peca.nome] = (d20_resultado, desgaste_real)
            
            # Registrar peças que quebraram
            if peca.durabilidade_atual <= 0:
                pecas_quebradas.append(peca.nome)
        
        # Remover peças instaladas que quebraram
        self.pecas_instaladas = [
            p for p in self.pecas_instaladas 
            if p.get('nome', '') not in pecas_quebradas
        ]
        
        self.batidas_totais += 1
        return pecas_quebradas, resultados_d20


@dataclass
class Piloto:
    """Representa um piloto"""
    id: str
    nome: str
    equipe_id: str
    vitoria: int = 0
    derrotas: int = 0
    empates: int = 0


@dataclass
class Equipe:
    """Representa uma equipe de pilotos"""
    id: str
    nome: str
    carro: Carro  # Carro da equipe (compartilhado por todos os pilotos)
    doricoins: float = 0.0  # Moeda do jogo
    pilotos: List[Piloto] = field(default_factory=list)
    historico_batalhas: List[str] = field(default_factory=list)  # IDs das batalhas
    senha: str = ""  # Senha para login na web
    serie: str = ""  # Série: A ou B
    carros: List[Carro] = field(default_factory=list)  # Lista de todos os carros da equipe
    
    def adicionar_piloto(self, piloto: Piloto) -> None:
        """Adiciona um piloto à equipe"""
        if piloto not in self.pilotos:
            self.pilotos.append(piloto)
    
    def remover_piloto(self, piloto_id: str) -> bool:
        """Remove um piloto da equipe"""
        self.pilotos = [p for p in self.pilotos if p.id != piloto_id]
        return True
    
    def adicionar_doricoins(self, quantidade: float) -> None:
        """Adiciona doricoins à equipe"""
        self.doricoins += quantidade
    
    def gastar_doricoins(self, quantidade: float) -> bool:
        """Gasta doricoins (retorna False se não há saldo suficiente)"""
        if self.doricoins >= quantidade:
            self.doricoins -= quantidade
            return True
        return False
    
    def reparar_carro_equipe(self, percentual: float = 100.0) -> bool:
        """Repara o carro da equipe"""
        if not self.carro:
            return False
        
        pecas_com_dano = [p for p in self.carro.get_todas_pecas() if p.durabilidade_atual < p.durabilidade_maxima]
        
        custo_total = sum(p.preco for p in pecas_com_dano)
        
        if self.gastar_doricoins(custo_total):
            for peca in pecas_com_dano:
                peca.reparar(percentual)
            return True
        return False


class ResultadoBatalha(Enum):
    """Possíveis resultados de uma batalha"""
    VITORIA_EQUIPE_A = "vitoria_equipe_a"
    VITORIA_EQUIPE_B = "vitoria_equipe_b"
    EMPATE = "empate"


@dataclass
class Batalha:
    """Representa uma batalha entre pilotos"""
    id: str
    piloto_a_id: str
    piloto_b_id: str
    equipe_a_id: str
    equipe_b_id: str
    etapa: int
    data: datetime
    resultado: Optional[ResultadoBatalha] = None
    empates_ate_vencer: int = 0  # Conta quantos empates ocorreram antes do vencedor
    doricoins_vencedor: float = PREMIACAO_VITORIA_BATALHA  # Doricoins ganhos pelo vencedor
    desgaste_base: float = DESGASTE_BASE_BATALHA           # Desgaste base por batalha
    
    def executar_batalha(self, resultado: ResultadoBatalha, 
                        piloto_a: Piloto, piloto_b: Piloto,
                        equipe_a: Equipe, equipe_b: Equipe) -> Dict[str, tuple]:
        """Executa a lógica da batalha e retorna os resultados dos D20
        
        Returns:
            Dicionário com {equipe_id: (pecas_quebradas, resultados_d20)}
        """
        self.resultado = resultado
        empate = resultado == ResultadoBatalha.EMPATE
        
        # Aplicar desgaste aos carros das equipes e capturar resultados do D20
        quebradas_a, d20_a = equipe_a.carro.sofrer_desgaste_batalha(self.desgaste_base, empate)
        quebradas_b, d20_b = equipe_b.carro.sofrer_desgaste_batalha(self.desgaste_base, empate)
        
        # Armazenar resultados para exibição
        resultados = {
            equipe_a.id: (quebradas_a, d20_a),
            equipe_b.id: (quebradas_b, d20_b)
        }
        
        # Atualizar estatísticas
        if resultado == ResultadoBatalha.VITORIA_EQUIPE_A:
            equipe_a.adicionar_doricoins(self.doricoins_vencedor)
            piloto_a.vitoria += 1
            piloto_b.derrotas += 1
            equipe_a.historico_batalhas.append(self.id)
        elif resultado == ResultadoBatalha.VITORIA_EQUIPE_B:
            equipe_b.adicionar_doricoins(self.doricoins_vencedor)
            piloto_b.vitoria += 1
            piloto_a.derrotas += 1
            equipe_b.historico_batalhas.append(self.id)
        else:  # EMPATE - Sem pagamento, apenas desgaste
            piloto_a.empates += 1
            piloto_b.empates += 1
            self.empates_ate_vencer += 1
        
        return resultados


@dataclass
class Etapa:
    """Representa uma etapa do campeonato"""
    id: str
    numero: int
    nome: str
    batalhas: List[Batalha] = field(default_factory=list)
    data_inicio: datetime = field(default_factory=datetime.now)
    data_fim: Optional[datetime] = None
    completa: bool = False
    equipes_presentes: Dict[str, bool] = field(default_factory=dict)  # equipe_id -> presente
    atributos_equipes: Dict[str, dict] = field(default_factory=dict)  # equipe_id -> {linha, angulo, estilo}
    ranking_etapa: List[str] = field(default_factory=list)  # lista de equipe_ids ordenados
    
    # Sistema de torneio multi-rodada
    rodadas: Dict[str, Dict] = field(default_factory=dict)  # "top32" -> {"chaveamento": [...], "vencedores": [...]}
    rodada_atual: str = "top32"  # top32, top16, top8, top4, final
    rodadas_disponiveis: List[str] = field(default_factory=list)  # ["top32", "top16", ...] baseado no número de pilotos
    
    def adicionar_batalha(self, batalha: Batalha) -> None:
        """Adiciona uma batalha à etapa"""
        if batalha not in self.batalhas:
            self.batalhas.append(batalha)
    
    def registrar_presenca(self, equipe_id: str, presente: bool) -> None:
        """Registra se uma equipe está presente na etapa"""
        self.equipes_presentes[equipe_id] = presente
    
    def registrar_atributos(self, equipe_id: str, linha: int, angulo: int, estilo: int) -> None:
        """Registra os atributos da equipe para a etapa"""
        if not (0 <= linha <= 40 and 0 <= angulo <= 30 and 0 <= estilo <= 30):
            raise ValueError("Valores de atributos fora do intervalo permitido")
        
        self.atributos_equipes[equipe_id] = {
            "linha": linha,
            "angulo": angulo,
            "estilo": estilo,
            "total": linha + angulo + estilo
        }
    
    def calcular_premio_equipes(self, equipes: List[Equipe]) -> None:
        """Calcula e distribui o prêmio por etapa para as equipes"""
        for equipe in equipes:
            equipe.adicionar_doricoins(PREMIACAO_POR_ETAPA)
