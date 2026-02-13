"""
Sistema Principal de Gerenciamento de Equipes
"""
from gerenciador import GerenciadorEquipes
from exportador_excel import ExportadorExcelProfissional
from models import TipoPeca, TipoCompra


class SistemaEquipes:
    """Sistema principal de gerenciamento"""
    
    def __init__(self):
        self.gerenciador = GerenciadorEquipes()
        self.exportador = ExportadorExcelProfissional()
    
    def menu_principal(self):
        """Menu principal"""
        while True:
            self.limpar_tela()
            print("\n" + "="*70)
            print("        SISTEMA DE GERENCIAMENTO DE EQUIPES")
            print("="*70)
            print("\n[1] Criar Equipe")
            print("[2] Gerenciar Equipe")
            print("[3] Exportar Equipes para Excel")
            print("[4] Ver Todas as Equipes")
            print("[0] Sair")
            print("\n" + "="*70)
            
            opcao = input("\nEscolha uma opção: ").strip()
            
            if opcao == "1":
                self.criar_equipe()
            elif opcao == "2":
                self.gerenciar_equipe()
            elif opcao == "3":
                self.exportar_todas()
            elif opcao == "4":
                self.listar_equipes()
            elif opcao == "0":
                print("\nAté logo!")
                break
            else:
                print("[ERRO] Opção inválida!")
                input("Pressione ENTER...")
    
    def criar_equipe(self):
        """Cria nova equipe"""
        self.limpar_tela()
        print("\n[+] CRIAR NOVA EQUIPE")
        print("="*70)
        
        nome = input("Nome da equipe: ").strip()
        if not nome:
            print("[ERRO] Nome não pode estar vazio!")
            input("Pressione ENTER...")
            return
        
        try:
            saldo = float(input("Saldo inicial em doricoins (padrão 1000): ") or "1000")
        except ValueError:
            print("[ERRO] Saldo deve ser um número!")
            input("Pressione ENTER...")
            return
        
        equipe = self.gerenciador.criar_equipe(nome, saldo)
        print(f"\n✓ Equipe '{equipe.nome}' criada com sucesso!")
        print(f"  ID: {equipe.id}")
        print(f"  Saldo: 💰 {equipe.saldo:,.2f}")
        
        input("\nPressione ENTER para continuar...")
    
    def gerenciar_equipe(self):
        """Menu de gerenciamento de equipe"""
        equipes = self.gerenciador.listar_equipes()
        
        if not equipes:
            print("[ERRO] Nenhuma equipe cadastrada!")
            input("Pressione ENTER...")
            return
        
        self.limpar_tela()
        print("\n[*] SELECIONE UMA EQUIPE")
        print("="*70)
        
        for i, eq in enumerate(equipes, 1):
            print(f"{i}. {eq.nome} (Saldo: 💰 {eq.saldo:,.2f})")
        
        try:
            idx = int(input("\nEscolha: ")) - 1
            if 0 <= idx < len(equipes):
                self.menu_equipe(equipes[idx])
            else:
                print("[ERRO] Opção inválida!")
                input("Pressione ENTER...")
        except ValueError:
            print("[ERRO] Digite um número válido!")
            input("Pressione ENTER...")
    
    def menu_equipe(self, equipe):
        """Menu de gerenciamento da equipe"""
        while True:
            self.limpar_tela()
            print(f"\n[=] EQUIPE: {equipe.nome}")
            print("="*70)
            print(f"Saldo: 💰 {equipe.saldo:,.2f}")
            print(f"Pilotos: {len(equipe.pilotos)} | Peças: {len(equipe.pecas)}")
            print(f"Transações: {len(equipe.historico_compras)}")
            print("="*70)
            print("\n[1] Adicionar Piloto")
            print("[2] Adicionar Peça ao Carro")
            print("[3] Registrar Vitória")
            print("[4] Registrar Derrota")
            print("[5] Danificar Peça")
            print("[6] Reparar Peça")
            print("[7] Ver Detalhes")
            print("[8] Exportar para Excel")
            print("[9] Voltar")
            
            opcao = input("\nEscolha: ").strip()
            
            if opcao == "1":
                self.adicionar_piloto(equipe)
            elif opcao == "2":
                self.adicionar_peca(equipe)
            elif opcao == "3":
                self.registrar_vitoria(equipe)
            elif opcao == "4":
                self.registrar_derrota(equipe)
            elif opcao == "5":
                self.danificar_peca(equipe)
            elif opcao == "6":
                self.reparar_peca(equipe)
            elif opcao == "7":
                self.ver_detalhes(equipe)
            elif opcao == "8":
                self.exportar_equipe(equipe)
            elif opcao == "9":
                break
            else:
                print("[ERRO] Opção inválida!")
                input("Pressione ENTER...")
    
    def adicionar_piloto(self, equipe):
        """Adiciona piloto à equipe"""
        self.limpar_tela()
        print(f"\n[+] ADICIONAR PILOTO - {equipe.nome}")
        print("="*70)
        
        nome = input("Nome do piloto: ").strip()
        if not nome:
            print("[ERRO] Nome não pode estar vazio!")
            input("Pressione ENTER...")
            return
        
        piloto = self.gerenciador.adicionar_piloto(equipe.id, nome)
        if piloto:
            print(f"\n✓ Piloto '{piloto.nome}' adicionado!")
        
        input("\nPressione ENTER...")
    
    def adicionar_peca(self, equipe):
        """Adiciona peça ao carro"""
        self.limpar_tela()
        print(f"\n[+] ADICIONAR PEÇA - {equipe.nome}")
        print("="*70)
        print("\nTipos disponíveis:")
        for i, tipo in enumerate(TipoPeca, 1):
            print(f"  {i}. {tipo.value.upper()}")
        
        nome = input("\nNome da peça: ").strip()
        tipo_input = input("Tipo (digite o número): ").strip()
        
        try:
            preco = float(input("Preço: "))
        except ValueError:
            print("[ERRO] Preço deve ser um número!")
            input("Pressione ENTER...")
            return
        
        try:
            tipos = list(TipoPeca)
            idx = int(tipo_input) - 1
            tipo = tipos[idx].name if 0 <= idx < len(tipos) else "MOTOR"
        except:
            tipo = "MOTOR"
        
        peca = self.gerenciador.adicionar_peca(equipe.id, nome, tipo, preco)
        if peca:
            print(f"\n✓ Peça '{peca.nome}' adicionada!")
            print(f"  Preço: 💰 {peca.preco:,.2f}")
            print(f"  Novo saldo: 💰 {equipe.saldo:,.2f}")
        
        input("\nPressione ENTER...")
    
    def registrar_vitoria(self, equipe):
        """Registra vitória de piloto"""
        self.limpar_tela()
        print(f"\n[✓] REGISTRAR VITÓRIA - {equipe.nome}")
        print("="*70)
        
        if not equipe.pilotos:
            print("[ERRO] Nenhum piloto registrado!")
            input("Pressione ENTER...")
            return
        
        for i, piloto in enumerate(equipe.pilotos, 1):
            print(f"{i}. {piloto.nome}")
        
        try:
            idx = int(input("\nEscolha o piloto: ")) - 1
            if 0 <= idx < len(equipe.pilotos):
                try:
                    premio = float(input("Prêmio em doricoins (padrão 100): ") or "100")
                except:
                    premio = 100.0
                
                piloto = equipe.pilotos[idx]
                self.gerenciador.registrar_vitoria(equipe.id, piloto.nome, premio)
                print(f"\n✓ Vitória registrada para {piloto.nome}!")
                print(f"  Prêmio: 💰 {premio:,.2f}")
                print(f"  Novo saldo: 💰 {equipe.saldo:,.2f}")
        except:
            pass
        
        input("\nPressione ENTER...")
    
    def registrar_derrota(self, equipe):
        """Registra derrota de piloto"""
        self.limpar_tela()
        print(f"\n[✗] REGISTRAR DERROTA - {equipe.nome}")
        print("="*70)
        
        if not equipe.pilotos:
            print("[ERRO] Nenhum piloto registrado!")
            input("Pressione ENTER...")
            return
        
        for i, piloto in enumerate(equipe.pilotos, 1):
            print(f"{i}. {piloto.nome}")
        
        try:
            idx = int(input("\nEscolha o piloto: ")) - 1
            if 0 <= idx < len(equipe.pilotos):
                piloto = equipe.pilotos[idx]
                self.gerenciador.registrar_derrota(equipe.id, piloto.nome)
                print(f"\n✓ Derrota registrada para {piloto.nome}!")
        except:
            pass
        
        input("\nPressione ENTER...")
    
    def danificar_peca(self, equipe):
        """Danifica uma peça"""
        self.limpar_tela()
        print(f"\n[!] DANIFICAR PEÇA - {equipe.nome}")
        print("="*70)
        
        if not equipe.pecas:
            print("[ERRO] Nenhuma peça registrada!")
            input("Pressione ENTER...")
            return
        
        for i, peca in enumerate(equipe.pecas, 1):
            print(f"{i}. {peca.nome} ({peca.get_status()}) - Saúde: {peca.saude:.1f}%")
        
        try:
            idx = int(input("\nEscolha a peça: ")) - 1
            dano = float(input("Dano (%): "))
            
            if 0 <= idx < len(equipe.pecas):
                self.gerenciador.danificar_peca(equipe.id, idx, dano)
                print(f"\n✓ Peça danificada!")
                print(f"  Saúde atual: {equipe.pecas[idx].saude:.1f}%")
        except:
            pass
        
        input("\nPressione ENTER...")
    
    def reparar_peca(self, equipe):
        """Repara uma peça"""
        self.limpar_tela()
        print(f"\n[🔧] REPARAR PEÇA - {equipe.nome}")
        print("="*70)
        
        if not equipe.pecas:
            print("[ERRO] Nenhuma peça registrada!")
            input("Pressione ENTER...")
            return
        
        for i, peca in enumerate(equipe.pecas, 1):
            print(f"{i}. {peca.nome} ({peca.get_status()}) - Saúde: {peca.saude:.1f}%")
        
        try:
            idx = int(input("\nEscolha a peça: ")) - 1
            custo = float(input("Custo do reparo: "))
            
            if 0 <= idx < len(equipe.pecas):
                if self.gerenciador.reparar_peca(equipe.id, idx, custo):
                    print(f"\n✓ Peça reparada!")
                    print(f"  Novo saldo: 💰 {equipe.saldo:,.2f}")
                else:
                    print(f"\n✗ Saldo insuficiente!")
        except:
            pass
        
        input("\nPressione ENTER...")
    
    def ver_detalhes(self, equipe):
        """Exibe detalhes da equipe"""
        self.limpar_tela()
        print(f"\n[=] DETALHES - {equipe.nome}")
        print("="*70)
        
        print(f"\n📊 RESUMO:")
        print(f"  Saldo: 💰 {equipe.saldo:,.2f}")
        print(f"  Pilotos: {len(equipe.pilotos)}")
        print(f"  Peças: {len(equipe.pecas)}")
        print(f"  Transações: {len(equipe.historico_compras)}")
        
        if equipe.pilotos:
            print(f"\n👥 PILOTOS:")
            for piloto in equipe.pilotos:
                total = piloto.vitoria + piloto.derrota + piloto.empate
                taxa = piloto.get_taxa_vitoria()
                print(f"  - {piloto.nome}")
                print(f"    ✓ {piloto.vitoria} | ✗ {piloto.derrota} | ⚖ {piloto.empate} | Taxa: {taxa:.1f}%")
        
        if equipe.pecas:
            print(f"\n🔧 PEÇAS:")
            for peca in equipe.pecas:
                print(f"  - {peca.nome} ({peca.tipo.value})")
                print(f"    {peca.get_status()} - Saúde: {peca.saude:.1f}%")
        
        if equipe.historico_compras:
            print(f"\n💳 ÚLTIMAS TRANSAÇÕES:")
            for compra in equipe.historico_compras[-5:]:
                print(f"  - {compra.data.strftime('%d/%m/%Y %H:%M')} | {compra.tipo.value}: 💰 {compra.valor:,.2f}")
        
        input("\nPressione ENTER...")
    
    def exportar_equipe(self, equipe):
        """Exporta equipe para Excel"""
        print("\n📊 Exportando para Excel...")
        try:
            caminho = self.exportador.exportar_equipe(equipe)
            print(f"✓ Arquivo criado: {caminho}")
        except Exception as e:
            print(f"✗ Erro: {e}")
        
        input("\nPressione ENTER...")
    
    def exportar_todas(self):
        """Exporta todas as equipes"""
        equipes = self.gerenciador.listar_equipes()
        if not equipes:
            print("[ERRO] Nenhuma equipe cadastrada!")
            input("Pressione ENTER...")
            return
        
        self.limpar_tela()
        print(f"\n📊 Exportando {len(equipes)} equipe(s)...\n")
        
        self.exportador.exportar_todas_equipes(equipes)
        
        input("\n✓ Exportação concluída! Pressione ENTER...")
    
    def listar_equipes(self):
        """Lista todas as equipes"""
        equipes = self.gerenciador.listar_equipes()
        
        self.limpar_tela()
        print("\n[*] EQUIPES CADASTRADAS")
        print("="*70)
        
        if not equipes:
            print("[ERRO] Nenhuma equipe cadastrada!")
        else:
            for i, eq in enumerate(equipes, 1):
                vitoria = eq.get_vitoria_total()
                derrota = eq.get_derrota_total()
                empate = eq.get_empate_total()
                
                print(f"\n{i}. {eq.nome}")
                print(f"   Saldo: 💰 {eq.saldo:,.2f}")
                print(f"   Pilotos: {len(eq.pilotos)} | Peças: {len(eq.pecas)}")
                print(f"   Estatísticas: ✓ {vitoria} | ✗ {derrota} | ⚖ {empate}")
        
        input("\nPressione ENTER...")
    
    @staticmethod
    def limpar_tela():
        """Limpa a tela"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == "__main__":
    sistema = SistemaEquipes()
    sistema.menu_principal()
