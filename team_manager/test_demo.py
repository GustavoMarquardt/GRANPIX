"""
Teste de demonstração do sistema WEB
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from gerenciador import GerenciadorEquipes
from models import TipoPeca


def criar_dados_demo():
    """Cria dados de demonstração"""
    print("=" * 70)
    print("CRIANDO DADOS DE DEMONSTRAÇÃO")
    print("=" * 70)
    
    gerenciador = GerenciadorEquipes()
    
    # Equipe 1
    print("\n[1] Criando Equipe 1...")
    eq1 = gerenciador.criar_equipe("Thunder Racing", 5000)
    
    # Adicionar pilotos
    p1_1 = gerenciador.adicionar_piloto(eq1.id, "Max Verstappen")
    p1_2 = gerenciador.adicionar_piloto(eq1.id, "Lewis Hamilton")
    print(f"  ✓ Pilotos adicionados")
    
    # Adicionar peças
    gerenciador.adicionar_peca(eq1.id, "Motor Turbo V8", "MOTOR", 2000)
    gerenciador.adicionar_peca(eq1.id, "Câmbio Automático", "CAMBIO", 1500)
    gerenciador.adicionar_peca(eq1.id, "Suspensão Esportiva", "SUSPENSAO", 1200)
    print(f"  ✓ Peças adicionadas")
    
    # Registrar algumas batalhas
    gerenciador.registrar_vitoria(eq1.id, "Max Verstappen", 500)
    gerenciador.registrar_vitoria(eq1.id, "Lewis Hamilton", 300)
    gerenciador.registrar_derrota(eq1.id, "Max Verstappen")
    print(f"  ✓ Batalhas registradas")
    
    # Danificar uma peça
    eq1.pecas[0].saude = 75
    eq1.pecas[1].saude = 50
    print(f"  ✓ Peças danificadas simuladas")
    
    # Equipe 2
    print("\n[2] Criando Equipe 2...")
    eq2 = gerenciador.criar_equipe("Dragon Team", 7000)
    
    p2_1 = gerenciador.adicionar_piloto(eq2.id, "Charles Leclerc")
    p2_2 = gerenciador.adicionar_piloto(eq2.id, "Lando Norris")
    print(f"  ✓ Pilotos adicionados")
    
    gerenciador.adicionar_peca(eq2.id, "Motor V12 Ferrari", "MOTOR", 3000)
    gerenciador.adicionar_peca(eq2.id, "Câmbio Manual", "CAMBIO", 800)
    gerenciador.adicionar_peca(eq2.id, "Freios de Carbono", "FREIO", 2500)
    gerenciador.adicionar_peca(eq2.id, "Pneus Pirelli", "PNEU", 600)
    print(f"  ✓ Peças adicionadas")
    
    gerenciador.registrar_vitoria(eq2.id, "Charles Leclerc", 600)
    gerenciador.registrar_derrota(eq2.id, "Lando Norris")
    gerenciador.registrar_derrota(eq2.id, "Charles Leclerc")
    print(f"  ✓ Batalhas registradas")
    
    eq2.pecas[0].saude = 85
    print(f"  ✓ Peças danificadas simuladas")
    
    print("\n✓ Dados de demonstração criados com sucesso!")
    
    return gerenciador



def exportar_e_mostrar():
    """Acesso web do sistema (Excel não é mais necessário)"""
    print("\n" + "=" * 70)
    print("🌐 SISTEMA WEB GRANPIX - ACESSO VIA NAVEGADOR")
    print("=" * 70)
    
    gerenciador = GerenciadorEquipes()
    equipes = gerenciador.listar_equipes()
    
    for eq in equipes:
        print(f"\n  📋 Equipe: {eq.nome}")
        print(f"    💰 Saldo: {eq.saldo:,.2f}")
        print(f"    👥 Pilotos: {len(eq.pilotos)}")
        print(f"    🔧 Peças: {len(eq.pecas)}")
        print(f"    📊 Transações: {len(eq.historico_compras)}")
        if hasattr(eq, 'vitoria'):
            print(f"    ✓ Vitórias: {eq.vitoria}")
        if hasattr(eq, 'derrotas'):
            print(f"    ✗ Derrotas: {eq.derrotas}")
    
    print("\n" + "=" * 70)
    print("✅ ACESSO via NAVEGADOR")
    print("=" * 70)
    print("\n🔐 Login Equipe:")
    print("   - Selecione uma equipe do dropdown")
    print("   - Senha padrão: 123456")
    print("\n👨‍💼 Login Admin:")
    print("   - Senha: admin123")


if __name__ == "__main__":
    try:
        # Criar dados de demo
        gerenciador = criar_dados_demo()
        
        # Mostrar acesso web
        exportar_e_mostrar()
        
        print("\n✨ Sistema web funcionando perfeitamente!")
        print("   Acesse: http://localhost:5000")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
