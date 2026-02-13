"""
Sistema de batalhas e gerenciamento de desgaste
"""
import random
import uuid
from datetime import datetime
from typing import Tuple, List, Dict
from .models import Piloto, Equipe, Batalha, Etapa, ResultadoBatalha, Carro


class SistemaBatalha:
    """Gerencia as batalhas entre pilotos"""
    
    def __init__(self):
        self.batalhas_realizadas: List[Batalha] = []
        self.etapas: List[Etapa] = []
    
    def calcular_chance_vitoria(self, piloto_a: Piloto, piloto_b: Piloto) -> Tuple[float, float]:
        """
        Calcula a chance de vitória para cada piloto (50/50)
        Retorna: (chance_a%, chance_b%)
        """
        return 50.0, 50.0
    
    def determinar_resultado(self, piloto_a: Piloto, piloto_b: Piloto) -> ResultadoBatalha:
        """
        Determina o resultado de uma batalha
        Há 10% de chance de empate, resto distribuído entre vitória A e B
        """
        chance_empate = 10.0
        aleatorio = random.random() * 100
        
        if aleatorio < chance_empate:
            return ResultadoBatalha.EMPATE
        
        chance_a, chance_b = self.calcular_chance_vitoria(piloto_a, piloto_b)
        
        # Normalizar para a faixa de 90% (100% - 10% de empate)
        chance_a = (chance_a / 100) * 90
        chance_b = (chance_b / 100) * 90
        
        if aleatorio < chance_empate + chance_a:
            return ResultadoBatalha.VITORIA_EQUIPE_A
        else:
            return ResultadoBatalha.VITORIA_EQUIPE_B
    
    def criar_batalha(self, piloto_a: Piloto, piloto_b: Piloto, 
                     equipe_a: Equipe, equipe_b: Equipe, 
                     etapa: int) -> Batalha:
        """Cria uma nova batalha"""
        batalha = Batalha(
            id=str(uuid.uuid4()),
            piloto_a_id=piloto_a.id,
            piloto_b_id=piloto_b.id,
            equipe_a_id=equipe_a.id,
            equipe_b_id=equipe_b.id,
            etapa=etapa,
            data=datetime.now()
        )
        return batalha
    
    def executar_batalha_completa(self, piloto_a: Piloto, piloto_b: Piloto,
                                 equipe_a: Equipe, equipe_b: Equipe,
                                 etapa: int) -> Tuple[Batalha, Dict]:
        """
        Executa uma batalha até haver um vencedor.
        Retorna a batalha com resultado final e os resultados dos D20.
        """
        batalha = self.criar_batalha(piloto_a, piloto_b, equipe_a, equipe_b, etapa)
        
        # Continuar até não ser empate
        resultado = ResultadoBatalha.EMPATE
        resultados_d20_empates = {}
        
        while resultado == ResultadoBatalha.EMPATE:
            resultado = self.determinar_resultado(piloto_a, piloto_b)
            if resultado == ResultadoBatalha.EMPATE:
                # Aplicar desgaste por empate nos carros das equipes
                quebradas_a, d20_a = equipe_a.carro.sofrer_desgaste_batalha(batalha.desgaste_base, True)
                quebradas_b, d20_b = equipe_b.carro.sofrer_desgaste_batalha(batalha.desgaste_base, True)
                
                # Guardar resultados dos empates para exibição
                resultados_d20_empates[f"empate_{batalha.empates_ate_vencer}"] = {
                    equipe_a.id: d20_a,
                    equipe_b.id: d20_b
                }
                batalha.empates_ate_vencer += 1
        
        # Executar batalha com resultado final
        resultados_d20_final = batalha.executar_batalha(resultado, piloto_a, piloto_b, equipe_a, equipe_b)
        
        # Combinar resultados dos empates e final
        resultados_completos = {
            "empates": resultados_d20_empates,
            "final": resultados_d20_final
        }
        
        self.batalhas_realizadas.append(batalha)
        
        return batalha, resultados_completos
    
    def relatorio_batalha(self, batalha: Batalha, piloto_a: Piloto, piloto_b: Piloto, equipe_a: Equipe = None, equipe_b: Equipe = None) -> str:
        """Gera um relatório textual da batalha"""
        resultado_texto = ""
        if batalha.resultado == ResultadoBatalha.VITORIA_EQUIPE_A:
            resultado_texto = f"✓ {piloto_a.nome} (VITÓRIA) ganhou {batalha.doricoins_vencedor} doricoins!"
        elif batalha.resultado == ResultadoBatalha.VITORIA_EQUIPE_B:
            resultado_texto = f"✓ {piloto_b.nome} (VITÓRIA) ganhou {batalha.doricoins_vencedor} doricoins!"
        
        desgaste_texto = f"Desgaste aplicado: {batalha.desgaste_base}"
        if batalha.empates_ate_vencer > 0:
            desgaste_adicional = batalha.desgaste_base * batalha.empates_ate_vencer * 1.0  # x1 já que multiplicador é aplicado no executa
            resultado_texto += f"\n  ⚠ Houve {batalha.empates_ate_vencer} empate(s) até vencer (sem prêmio, +{desgaste_adicional:.1f} desgaste por empate)"
            desgaste_texto += f" (desgaste x2 em cada empate)"
        
        # Buscar carros das equipes
        carro_a = equipe_a.carro if equipe_a else None
        carro_b = equipe_b.carro if equipe_b else None
        
        # Valores padrão se carros não forem encontrados
        marca_a = carro_a.marca if carro_a else "Desconhecido"
        modelo_a = carro_a.modelo if carro_a else ""
        condicao_a = carro_a.calcular_condicao_geral() if carro_a else 0.0
        
        marca_b = carro_b.marca if carro_b else "Desconhecido"
        modelo_b = carro_b.modelo if carro_b else ""
        condicao_b = carro_b.calcular_condicao_geral() if carro_b else 0.0
        
        return f"""
╔════════════════════════════════════════╗
║  RESULTADO DA BATALHA - ETAPA {batalha.etapa}
╠════════════════════════════════════════╣
║ Piloto A: {piloto_a.nome}
║   Carro: {marca_a} {modelo_a}
║   Condição do Carro: {condicao_a:.1f}%
║
║ Piloto B: {piloto_b.nome}
║   Carro: {marca_b} {modelo_b}
║   Condição do Carro: {condicao_b:.1f}%
║
╠════════════════════════════════════════╣
║ {resultado_texto}
║ {desgaste_texto}
╚════════════════════════════════════════╝
"""
    
    def relatorio_d20_batalha(self, equipe_a: Equipe, equipe_b: Equipe, resultados_d20: Dict) -> str:
        """Gera um relatório detalhado dos resultados do D20 para cada peça"""
        linhas = []
        linhas.append("\n╔═════════════════════════════════════════════════════════════╗")
        linhas.append("║                  RESULTADO DOS D20 - DESGASTE DAS PEÇAS      ║")
        linhas.append("╠═════════════════════════════════════════════════════════════╣")
        
        # Processar resultado final
        if "final" in resultados_d20:
            final_results = resultados_d20["final"]
            
            # Equipe A
            linhas.append(f"║ {equipe_a.nome:40} ║")
            linhas.append("├─────────────────────────────────────────────────────────────┤")
            if equipe_a.id in final_results:
                quebradas_a, d20_a = final_results[equipe_a.id]
                for nome_peca, (d20_val, desgaste) in d20_a.items():
                    status = "💥" if d20_val == 1 else "   "
                    d20_display = f"D20: {d20_val:2d}" if d20_val != 1 else "D20:  1 (DOBRO!)"
                    linhas.append(f"║ {status} {nome_peca:25} {d20_display:20} Desgaste: {desgaste:6.2f}%  ║")
            
            # Equipe B
            linhas.append("├─────────────────────────────────────────────────────────────┤")
            linhas.append(f"║ {equipe_b.nome:40} ║")
            linhas.append("├─────────────────────────────────────────────────────────────┤")
            if equipe_b.id in final_results:
                quebradas_b, d20_b = final_results[equipe_b.id]
                for nome_peca, (d20_val, desgaste) in d20_b.items():
                    status = "💥" if d20_val == 1 else "   "
                    d20_display = f"D20: {d20_val:2d}" if d20_val != 1 else "D20:  1 (DOBRO!)"
                    linhas.append(f"║ {status} {nome_peca:25} {d20_display:20} Desgaste: {desgaste:6.2f}%  ║")
        
        linhas.append("╚═════════════════════════════════════════════════════════════╝")
        return "\n".join(linhas)


class SistemaDesgaste:
    """Gerencia o desgaste das peças dos carros"""
    
    @staticmethod
    def calcular_desgaste_proporcional(carro: Carro) -> dict:
        """Calcula o desgaste proporcional para cada peça baseado na durabilidade atual"""
        desgastes = {}
        total_durabilidade = sum(p.durabilidade_atual for p in carro.get_todas_pecas())
        
        if total_durabilidade == 0:
            # Se todas as peças estão destruídas, distribui igualmente
            quantidade_pecas = len(carro.get_todas_pecas())
            desgaste_igual = 1.0 / quantidade_pecas if quantidade_pecas > 0 else 0
            for peca in carro.get_todas_pecas():
                desgastes[peca.id] = desgaste_igual
        else:
            # Peças em melhor condição sofrem menos desgaste
            for peca in carro.get_todas_pecas():
                proporcao = peca.durabilidade_atual / total_durabilidade
                desgastes[peca.id] = proporcao
        
        return desgastes
    
    @staticmethod
    def aplicar_desgaste_gradual(carro: Carro, desgaste_base: float, 
                                 multiplicador: float = 1.0) -> None:
        """Aplica desgaste baseado na durabilidade atual das peças"""
        desgastes_prop = SistemaDesgaste.calcular_desgaste_proporcional(carro)
        
        for peca in carro.get_todas_pecas():
            if peca.id in desgastes_prop:
                desgaste = desgaste_base * desgastes_prop[peca.id] * multiplicador
                peca.sofrer_desgaste(desgaste)
    
    @staticmethod
    def relatorio_desgaste(carro: Carro) -> str:
        """Gera um relatório visual do desgaste do carro"""
        linhas = [f"\n📊 DESGASTE DO CARRO {carro.numero_carro} - {carro.marca} {carro.modelo}"]
        linhas.append("=" * 50)
        
        for peca in carro.get_todas_pecas():
            porcentagem = (peca.durabilidade_atual / peca.durabilidade_maxima) * 100
            barra = "█" * int(porcentagem / 10) + "░" * (10 - int(porcentagem / 10))
            status = "🔴" if porcentagem < 30 else "🟡" if porcentagem < 70 else "🟢"
            
            linhas.append(f"{status} {peca.nome:20} [{barra}] {porcentagem:5.1f}%")
        
        condicao_geral = carro.calcular_condicao_geral()
        linhas.append("=" * 50)
        linhas.append(f"Condição Geral: {condicao_geral:.1f}%")
        linhas.append(f"Batalhas: {carro.batidas_totais} | V:{carro.vitoria} D:{carro.derrotas} E:{carro.empates}")
        
        return "\n".join(linhas)
