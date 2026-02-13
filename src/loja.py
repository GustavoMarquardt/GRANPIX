"""
Sistema de Loja - Catálogo de Peças e Motores
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class TipoMotor(Enum):
    """Tipos de motor disponíveis"""
    OHC = "ohc"
    AP = "ap"
    EA855 = "ea855"
    GM_8V = "gm_8v"


@dataclass
class PecaMotor:
    """Representa uma peça/motor disponível na loja"""
    codigo_unico: str              # Identificador único
    motor: str                     # Tipo de motor
    descricao: str                 # Descrição da peça
    valor: float                   # Preço em doricoins
    potencia: str = ""             # Ex: "72cv a 5600rpm"
    torque: str = ""               # Ex: "12kgfm a 4800rpm"
    max_rpm: int = 0               # RPM máximo
    peso: float = 0.0              # Peso em kg
    requisitos: str = ""           # Pré-requisitos (peça anterior necessária)
    
    def __str__(self) -> str:
        return f"{self.codigo_unico} - {self.descricao} (R$ {self.valor:.2f})"
    
    def info_completa(self) -> str:
        """Retorna informações completas da peça"""
        info = f"""
╔════════════════════════════════════════╗
║ {self.codigo_unico.upper()}
╠════════════════════════════════════════╣
║ Motor: {self.motor}
║ Descrição: {self.descricao}
║ Valor: R$ {self.valor:.2f}
║ 
║ Especificações:
║   Potência: {self.potencia if self.potencia else 'N/A'}
║   Torque: {self.torque if self.torque else 'N/A'}
║   RPM Máx: {self.max_rpm if self.max_rpm else 'N/A'}
║   Peso: {self.peso if self.peso else 'N/A'} kg
║
║ Requisitos: {self.requisitos if self.requisitos else 'Nenhum'}
╚════════════════════════════════════════╝
"""
        return info


class Loja:
    """Gerencia o catálogo de peças da loja"""
    
    def __init__(self):
        self.pecas: List[PecaMotor] = []
        self._carregar_catalogo()
    
    def _carregar_catalogo(self) -> None:
        """Carrega o catálogo padrão de peças"""
        self.pecas = [
            PecaMotor(
                codigo_unico="ohc",
                motor="ohc",
                descricao="Motor OHC",
                valor=1000.0,
                potencia="72cv a 5600rpm",
                torque="12kgfm a 4800rpm",
                max_rpm=6500,
                peso=0.0,
                requisitos=""
            ),
            PecaMotor(
                codigo_unico="ohc_turbo",
                motor="ohc",
                descricao="Kit Turbo OHC",
                valor=4200.0,
                potencia="190cv a 5600rpm",
                torque="",
                max_rpm=6500,
                peso=0.0,
                requisitos="ohc"
            ),
            PecaMotor(
                codigo_unico="ap",
                motor="ap",
                descricao="Motor AP",
                valor=3000.0,
                potencia="115cv",
                torque="17,5 a 3000",
                max_rpm=6600,
                peso=0.0,
                requisitos=""
            ),
            PecaMotor(
                codigo_unico="ea855",
                motor="ea855",
                descricao="Jeta 2.5 5 cil",
                valor=8000.0,
                potencia="170cv a 5700",
                torque="24,47 a 4250",
                max_rpm=6600,
                peso=0.0,
                requisitos=""
            ),
            PecaMotor(
                codigo_unico="ap_turbo",
                motor="ap",
                descricao="Kit Turbo AP",
                valor=5000.0,
                potencia="250cv",
                torque="",
                max_rpm=6600,
                peso=0.0,
                requisitos="ap"
            ),
            PecaMotor(
                codigo_unico="gm_8v",
                motor="gm_8v",
                descricao="GM 8V 2.2",
                valor=5000.0,
                potencia="126 a 5200",
                torque="20kg a 2800",
                max_rpm=6500,
                peso=0.0,
                requisitos=""
            ),
            PecaMotor(
                codigo_unico="gm_8v_turbo",
                motor="gm_8v",
                descricao="GM 8V 2.2 Turbo",
                valor=5000.0,
                potencia="",
                torque="",
                max_rpm=6500,
                peso=0.0,
                requisitos="gm_8v"
            ),
            PecaMotor(
                codigo_unico="ap_cabeçote",
                motor="ap",
                descricao="Cabeçote Preparado AP",
                valor=3000.0,
                potencia="",
                torque="",
                max_rpm=7200,
                peso=0.0,
                requisitos="ap"
            ),
            PecaMotor(
                codigo_unico="ap_turbo_forjado",
                motor="ap",
                descricao="Peças Forjada AP",
                valor=7000.0,
                potencia="404",
                torque="",
                max_rpm=6700,
                peso=0.0,
                requisitos=""
            ),
        ]
    
    def listar_pecas(self) -> List[PecaMotor]:
        """Retorna todas as peças disponíveis"""
        return self.pecas
    
    def listar_pecas_por_motor(self, tipo_motor: str) -> List[PecaMotor]:
        """Retorna peças de um tipo específico de motor"""
        return [p for p in self.pecas if p.motor == tipo_motor]
    
    def obter_peca(self, codigo: str) -> Optional[PecaMotor]:
        """Obtém uma peça pelo código único"""
        for peca in self.pecas:
            if peca.codigo_unico == codigo:
                return peca
        return None
    
    def verificar_requisito(self, codigo: str, pecas_possuidas: List[str]) -> bool:
        """Verifica se uma peça pode ser comprada (requisitos satisfeitos)"""
        peca = self.obter_peca(codigo)
        if not peca:
            return False
        
        if not peca.requisitos:
            return True
        
        return peca.requisitos in pecas_possuidas
    
    def mostrar_catalogo(self) -> str:
        """Mostra o catálogo completo"""
        catalogo = "\n╔════════════════════════════════════════╗\n"
        catalogo += "║         CATÁLOGO DE PEÇAS             ║\n"
        catalogo += "╠════════════════════════════════════════╣\n"
        
        motores = {}
        for peca in self.pecas:
            if peca.motor not in motores:
                motores[peca.motor] = []
            motores[peca.motor].append(peca)
        
        for tipo_motor, pecas in sorted(motores.items()):
            catalogo += f"║ {tipo_motor.upper():38} ║\n"
            for peca in pecas:
                req_str = f" (req: {peca.requisitos})" if peca.requisitos else ""
                catalogo += f"║ {peca.codigo_unico:15} R$ {peca.valor:7.0f}{req_str:15} ║\n"
            catalogo += "╠════════════════════════════════════════╣\n"
        
        catalogo += "╚════════════════════════════════════════╝\n"
        return catalogo
