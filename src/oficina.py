"""
Sistema de Oficina - Instalação de peças nos carros
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from .models import Carro, Equipe, Piloto
from .loja import PecaMotor, Loja


@dataclass
class PecaInstalada:
    """Representa uma peça instalada em um carro"""
    codigo_peca: str               # Código da peça
    descricao: str                 # Descrição
    valor_pago: float              # Valor pago
    
    def __str__(self) -> str:
        return f"{self.codigo_peca} (R$ {self.valor_pago:.2f})"


class Oficina:
    """Gerencia a instalação de peças nos carros"""
    
    def __init__(self, loja: Loja):
        self.loja = loja
        self.servicos_realizados: List[dict] = []
    
    def instalar_peca(self, carro: Carro, equipe: Equipe, codigo_peca: str) -> Tuple[bool, str]:
        """
        Instala uma peça em um carro
        Retorna: (sucesso: bool, mensagem: str)
        """
        # Obter peça da loja
        peca = self.loja.obter_peca(codigo_peca)
        if not peca:
            return False, f"❌ Peça '{codigo_peca}' não encontrada na loja"
        
        # Verificar se equipe tem saldo suficiente
        if equipe.doricoins < peca.valor:
            return False, f"❌ Saldo insuficiente. Necessário: R$ {peca.valor:.2f}, Disponível: R$ {equipe.doricoins:.2f}"
        
        # Verificar requisitos
        pecas_instaladas = [p.codigo_peca for p in getattr(carro, 'pecas_instaladas', [])]
        if peca.requisitos and peca.requisitos not in pecas_instaladas:
            return False, f"❌ Requisito não atendido. Necessário instalar '{peca.requisitos}' primeiro"
        
        # Inicializar lista de peças se não existir
        if not hasattr(carro, 'pecas_instaladas'):
            carro.pecas_instaladas = []
        
        # Verificar se peça já está instalada
        if any(p.codigo_peca == codigo_peca for p in carro.pecas_instaladas):
            return False, f"⚠ Peça '{codigo_peca}' já está instalada neste carro"
        
        # Subtrair valor dos doricoins da equipe
        equipe.gastar_doricoins(peca.valor)
        
        # Instalar peça
        peca_instalada = PecaInstalada(
            codigo_peca=peca.codigo_unico,
            descricao=peca.descricao,
            valor_pago=peca.valor
        )
        carro.pecas_instaladas.append(peca_instalada)
        
        # Registrar serviço
        self.servicos_realizados.append({
            'carro_id': carro.id,
            'peca': codigo_peca,
            'valor': peca.valor,
            'equipe_id': equipe.id,
            'tipo': 'instalacao'
        })
        
        mensagem = f"✓ Peça '{peca.codigo_unico}' instalada com sucesso! (-R$ {peca.valor:.2f})"
        return True, mensagem
    
    def remover_peca(self, carro: Carro, equipe: Equipe, codigo_peca: str) -> Tuple[bool, str]:
        """
        Remove uma peça de um carro (sem reembolso)
        Retorna: (sucesso: bool, mensagem: str)
        """
        if not hasattr(carro, 'pecas_instaladas'):
            return False, "❌ Nenhuma peça instalada neste carro"
        
        peca_encontrada = None
        for i, peca in enumerate(carro.pecas_instaladas):
            if peca.codigo_peca == codigo_peca:
                peca_encontrada = carro.pecas_instaladas.pop(i)
                break
        
        if not peca_encontrada:
            return False, f"❌ Peça '{codigo_peca}' não está instalada neste carro"
        
        # Registrar serviço
        self.servicos_realizados.append({
            'carro_id': carro.id,
            'peca': codigo_peca,
            'valor': 0.0,
            'equipe_id': equipe.id,
            'tipo': 'remocao'
        })
        
        return True, f"✓ Peça '{codigo_peca}' removida com sucesso"
    
    def listar_pecas_carro(self, carro: Carro) -> str:
        """Lista todas as peças instaladas em um carro"""
        if not hasattr(carro, 'pecas_instaladas') or not carro.pecas_instaladas:
            return "Nenhuma peça instalada"
        
        info = f"\n📦 PEÇAS INSTALADAS - {carro.marca} {carro.modelo} (#{carro.numero_carro})\n"
        info += "=" * 50 + "\n"
        
        custo_total = 0.0
        for i, peca in enumerate(carro.pecas_instaladas, 1):
            info += f"{i}. {peca.codigo_peca:20} R$ {peca.valor_pago:8.2f}\n"
            custo_total += peca.valor_pago
        
        info += "=" * 50 + "\n"
        info += f"Custo total investido: R$ {custo_total:.2f}\n"
        return info
    
    def calcular_bonus_motor(self, carro: Carro) -> dict:
        """
        Calcula bônus de desempenho baseado nas peças instaladas
        Retorna: dict com bônus de potência, torque, RPM
        """
        bonificacoes = {
            'potencia': 0,
            'torque': 0,
            'rpm': 0,
            'peso': 0
        }
        
        if not hasattr(carro, 'pecas_instaladas'):
            return bonificacoes
        
        for peca in carro.pecas_instaladas:
            peca_loja = self.loja.obter_peca(peca.codigo_peca)
            if peca_loja:
                # Exemplo de bonificação (pode ser ajustado)
                if 'turbo' in peca.codigo_peca:
                    bonificacoes['potencia'] += 50
                    bonificacoes['rpm'] += 200
                elif 'cabeçote' in peca.codigo_peca:
                    bonificacoes['rpm'] += 500
        
        return bonificacoes
    
    def relatorio_oficina(self) -> str:
        """Gera relatório de todos os serviços realizados"""
        relatorio = "\n╔════════════════════════════════════════╗\n"
        relatorio += "║       RELATÓRIO DE SERVIÇOS            ║\n"
        relatorio += "╠════════════════════════════════════════╣\n"
        
        if not self.servicos_realizados:
            relatorio += "║ Nenhum serviço realizado               ║\n"
        else:
            valor_total = 0.0
            for servico in self.servicos_realizados:
                tipo = "Instalação" if servico['tipo'] == 'instalacao' else "Remoção"
                valor_total += servico['valor']
                relatorio += f"║ {tipo:20} {servico['peca']:10} R$ {servico['valor']:6.0f}   ║\n"
            
            relatorio += "╠════════════════════════════════════════╣\n"
            relatorio += f"║ Total arrecadado: R$ {valor_total:22.2f} ║\n"
        
        relatorio += "╚════════════════════════════════════════╝\n"
        return relatorio
