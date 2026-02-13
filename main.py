"""
Inicializador do sistema GRANPIX
Ponto de entrada principal para a aplicacao
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api import APIGranpix
from src.models import ResultadoBatalha


class MenuPrincipal:
    """Interface de menu para o sistema GRANPIX"""

    def menu_etapa(self):
        self.limpar_tela()
        print("\n[=] ETAPA - COMPETIÇÃO [=]")
        try:
            numero_etapa = int(input("\nDigite o número da etapa: "))
            nome_etapa = input("Nome da etapa (opcional): ").strip()
            etapa = self.api.criar_etapa(numero_etapa, nome_etapa)
            print(f"\nEtapa {etapa.numero} criada!")

            # 1. Presença das equipes
            equipes = self.api.listar_todas_equipes()
            print("\nMarque presença das equipes:")
            for equipe in equipes:
                while True:
                    resp = input(f"Equipe '{equipe.nome}' está presente? (s/n): ").strip().lower()
                    if resp in ("s", "n"):
                        presente = resp == "s"
                        self.api.registrar_presenca_etapa(numero_etapa, equipe.id, presente)
                        if presente:
                            print("  [OK] 2000 doricoins creditados!")
                        break
                    else:
                        print("Digite 's' para sim ou 'n' para não.")

            # 2. Coleta de atributos
            print("\nDigite os atributos das equipes presentes:")
            for equipe in equipes:
                if not etapa.equipes_presentes.get(equipe.id):
                    continue
                print(f"\nEquipe: {equipe.nome}")
                while True:
                    try:
                        linha = int(input("  Linha (0-40): "))
                        angulo = int(input("  Angulo (0-30): "))
                        estilo = int(input("  Estilo (0-30): "))
                        if not (0 <= linha <= 40 and 0 <= angulo <= 30 and 0 <= estilo <= 30):
                            print("  [ERRO] Valores fora do intervalo!")
                            continue
                        self.api.registrar_atributos_etapa(numero_etapa, equipe.id, linha, angulo, estilo)
                        break
                    except ValueError:
                        print("  [ERRO] Digite valores válidos!")

            # 3. Ranking
            ranking = self.api.gerar_ranking_etapa(numero_etapa)
            print("\nRANKING DA ETAPA:")
            for pos, equipe_id in enumerate(ranking, 1):
                eq = next((e for e in equipes if e.id == equipe_id), None)
                if eq:
                    total = etapa.atributos_equipes[equipe_id]["total"]
                    print(f"{pos}. {eq.nome} - {total} pontos")

            # 4. Determinar rodadas e executar torneio
            rodadas = self.api.determinar_rodadas_torneio(numero_etapa)
            print(f"\nRODAS DO TORNEIO: {' → '.join(rodadas).upper()}")
            
            input("\nPressione ENTER para iniciar o torneio...")
            
            # Executar cada rodada do torneio
            for idx_rodada, rodada in enumerate(rodadas):
                self.limpar_tela()
                print("\n" + "="*70)
                print(f"ETAPA {numero_etapa}: {rodada.upper()}")
                print("="*70 + "\n")
                
                # Gerar chaveamento para a rodada
                chaveamento = self.api.gerar_chaveamento_rodada(numero_etapa, rodada)
                
                # Mostrar chaveamento SEMPRE antes das batalhas
                print(f"CHAVEAMENTO {rodada.upper()}:\n")
                
                # Mostrar os que passam direto (apenas em rodadas posteriores)
                passam_direto = etapa.rodadas[rodada].get("passam_direto", [])
                if passam_direto:
                    print("PASSAM DIRETO:")
                    for eq_id in passam_direto:
                        eq = next((e for e in equipes if e.id == eq_id), None)
                        if eq and eq_id in ranking:
                            posicao = ranking.index(eq_id) + 1
                            print(f"  ✓ {eq.nome}: {posicao} lugar")
                    print()
                
                # Mostrar todas as batalhas do chaveamento
                if chaveamento:
                    print("BATALHAS:")
                    for idx, (equipe_a_id, equipe_b_id) in enumerate(chaveamento, 1):
                        eq_a = next((e for e in equipes if e.id == equipe_a_id), None)
                        eq_b = next((e for e in equipes if e.id == equipe_b_id), None)
                        
                        if eq_a and eq_b and equipe_a_id in ranking and equipe_b_id in ranking:
                            posicao_a = ranking.index(equipe_a_id) + 1
                            posicao_b = ranking.index(equipe_b_id) + 1
                            
                            print(f"  BATALHA {idx}: {eq_a.nome} vs {eq_b.nome}")
                            print(f"    {eq_a.nome}: {posicao_a} lugar")
                            print(f"    {eq_b.nome}: {posicao_b} lugar")
                
                print()
                input("Pressione ENTER para iniciar as batalhas...")
                self.limpar_tela()
                print("\n" + "="*70)
                print(f"ETAPA {numero_etapa}: {rodada.upper()}")
                print("="*70 + "\n")
                
                # Executar batalhas da rodada
                if chaveamento:
                    print(f"BATALHAS ({rodada.upper()}):\n")
                    
                    for idx, (equipe_a_id, equipe_b_id) in enumerate(chaveamento, 1):
                        eq_a = next((e for e in equipes if e.id == equipe_a_id), None)
                        eq_b = next((e for e in equipes if e.id == equipe_b_id), None)
                        
                        if not eq_a or not eq_b:
                            continue
                        
                        # Obter posição no ranking
                        posicao_a = ranking.index(equipe_a_id) + 1 if equipe_a_id in ranking else "?"
                        posicao_b = ranking.index(equipe_b_id) + 1 if equipe_b_id in ranking else "?"
                        
                        print(f"BATALHA {idx}: {eq_a.nome} vs {eq_b.nome}")
                        print(f"  {eq_a.nome}: {posicao_a} lugar")
                        print(f"  {eq_b.nome}: {posicao_b} lugar")
                        
                        # Exibir dados dos carros
                        self._exibir_carro_batalha(eq_a, eq_b)
                        
                        # Loop até não haver empate
                        while True:
                            # Inicializar variáveis para armazenar peças quebradas de todas as passadas
                            pecas_quebradas_a = []
                            pecas_quebradas_b = []
                            
                            # ===== PASSADA 1 =====
                            input("\nPressione ENTER para a Passada 1...")
                            
                            # Aplicar desgaste da passada 1
                            quebradas_a_p1, d20_a_p1 = eq_a.carro.sofrer_desgaste_batalha(10.0, empate=False)
                            quebradas_b_p1, d20_b_p1 = eq_b.carro.sofrer_desgaste_batalha(10.0, empate=False)
                            
                            # Acumular peças quebradas
                            pecas_quebradas_a.extend(quebradas_a_p1)
                            pecas_quebradas_b.extend(quebradas_b_p1)
                            
                            self.api.db.salvar_equipe(eq_a)
                            self.api.db.salvar_equipe(eq_b)
                            
                            # Exibir Passada 1
                            self.limpar_tela()
                            print("\n" + "="*70)
                            print(f"ETAPA {numero_etapa}: {rodada.upper()}")
                            print("="*70 + "\n")
                            print(f"BATALHA {idx}: {eq_a.nome} vs {eq_b.nome}")
                            print(f"  {eq_a.nome}: {posicao_a} lugar")
                            print(f"  {eq_b.nome}: {posicao_b} lugar")
                            print(f"\n{'='*70}")
                            print(f"PASSADA 1")
                            print(f"{'='*70}\n")
                            
                            self._exibir_carro_batalha(eq_a, eq_b)
                            
                            # Exibir resultados do D20 da Passada 1
                            print(f"\n{'='*70}")
                            print(f"📊 RESULTADOS DO D20 - PASSADA 1")
                            print(f"{'='*70}\n")
                            
                            print(f"{eq_a.nome}:")
                            for nome_peca, (d20_val, desgaste) in d20_a_p1.items():
                                status = "💥" if d20_val == 1 else "   "
                                d20_display = f"D20: {d20_val:2d}" if d20_val != 1 else "D20:  1 (DOBRO!)"
                                print(f"  {status} {nome_peca:25} {d20_display:20} Desgaste: {desgaste:6.2f}%")
                            
                            print(f"\n{eq_b.nome}:")
                            for nome_peca, (d20_val, desgaste) in d20_b_p1.items():
                                status = "💥" if d20_val == 1 else "   "
                                d20_display = f"D20: {d20_val:2d}" if d20_val != 1 else "D20:  1 (DOBRO!)"
                                print(f"  {status} {nome_peca:25} {d20_display:20} Desgaste: {desgaste:6.2f}%")
                            
                            # ===== PASSADA 2 =====
                            input("\nPressione ENTER para a Passada 2...")
                            
                            # Aplicar desgaste da passada 2
                            quebradas_a_p2, d20_a_p2 = eq_a.carro.sofrer_desgaste_batalha(10.0, empate=False)
                            quebradas_b_p2, d20_b_p2 = eq_b.carro.sofrer_desgaste_batalha(10.0, empate=False)
                            
                            # Acumular peças quebradas
                            pecas_quebradas_a.extend(quebradas_a_p2)
                            pecas_quebradas_b.extend(quebradas_b_p2)
                            
                            self.api.db.salvar_equipe(eq_a)
                            self.api.db.salvar_equipe(eq_b)
                            
                            # Exibir Passada 2
                            self.limpar_tela()
                            print("\n" + "="*70)
                            print(f"ETAPA {numero_etapa}: {rodada.upper()}")
                            print("="*70 + "\n")
                            print(f"BATALHA {idx}: {eq_a.nome} vs {eq_b.nome}")
                            print(f"  {eq_a.nome}: {posicao_a} lugar")
                            print(f"  {eq_b.nome}: {posicao_b} lugar")
                            print(f"\n{'='*70}")
                            print(f"PASSADA 2")
                            print(f"{'='*70}\n")
                            
                            self._exibir_carro_batalha(eq_a, eq_b)
                            
                            # Exibir resultados do D20 da Passada 2
                            print(f"\n{'='*70}")
                            print(f"📊 RESULTADOS DO D20 - PASSADA 2")
                            print(f"{'='*70}\n")
                            
                            print(f"{eq_a.nome}:")
                            for nome_peca, (d20_val, desgaste) in d20_a_p2.items():
                                status = "💥" if d20_val == 1 else "   "
                                d20_display = f"D20: {d20_val:2d}" if d20_val != 1 else "D20:  1 (DOBRO!)"
                                print(f"  {status} {nome_peca:25} {d20_display:20} Desgaste: {desgaste:6.2f}%")
                            
                            print(f"\n{eq_b.nome}:")
                            for nome_peca, (d20_val, desgaste) in d20_b_p2.items():
                                status = "💥" if d20_val == 1 else "   "
                                d20_display = f"D20: {d20_val:2d}" if d20_val != 1 else "D20:  1 (DOBRO!)"
                                print(f"  {status} {nome_peca:25} {d20_display:20} Desgaste: {desgaste:6.2f}%")
                            
                            # Perguntar resultado após as 2 passadas
                            resultado_valido = False
                            while not resultado_valido:
                                print(f"\nQual foi o resultado?")
                                print(f"[1] {eq_a.nome} venceu")
                                print(f"[2] {eq_b.nome} venceu")
                                print(f"[3] Empate")
                                opcao = input("Escolha: ").strip()
                                
                                if opcao not in ["1", "2", "3"]:
                                    print("[ERRO] Opção inválida!")
                                    continue
                                
                                houve_empate = opcao == "3"
                                vencedor_id = equipe_a_id if opcao == "1" else equipe_b_id if opcao == "2" else None
                                resultado_valido = True
                            
                            if houve_empate:
                                print(f"\n⚠️  EMPATE! Os pilotos correrão novamente...\n")
                                
                                # Restaurar saúde dos carros para fazer nova tentativa
                                eq_a = self.api.gerenciador.obter_equipe(equipe_a_id)
                                eq_b = self.api.gerenciador.obter_equipe(equipe_b_id)
                                
                                self._exibir_carro_batalha(eq_a, eq_b)
                            else:
                                # Houve vencedor
                                vencedor = eq_a if vencedor_id == equipe_a_id else eq_b
                                
                                print(f"\n🏁 VITÓRIA: {vencedor.nome}!\n")
                                
                                # Mostrar peças que quebraram
                                if pecas_quebradas_a:
                                    print(f"{eq_a.nome} perdeu peças:")
                                    for peca in pecas_quebradas_a:
                                        print(f"  ❌ {peca}")
                                
                                if pecas_quebradas_b:
                                    print(f"{eq_b.nome} perdeu peças:")
                                    for peca in pecas_quebradas_b:
                                        print(f"  ❌ {peca}")
                                
                                # Registrar vitória
                                premio = {
                                    "top32": 1000,
                                    "top16": 1000,
                                    "top8": 1000,
                                    "top4": 1000,
                                    "final": 1000
                                }.get(rodada, 1000)
                                
                                self.api.registrar_vencedor_rodada(numero_etapa, rodada, vencedor_id)
                                print(f"[OK] {vencedor.nome} venceu! +{premio} doricoins\n")
                                break  # Sair do loop de empates
                
                # Se não é a última rodada, avançar para próxima
                if rodada != rodadas[-1]:
                    input("Pressione ENTER para avançar para a próxima rodada...")
            
            # Finalizar torneio
            self.limpar_tela()
            print("\n" + "="*70)
            print(f"ETAPA {numero_etapa} - TORNEIO CONCLUÍDO!")
            print("="*70 + "\n")
            
            # Mostrar campeão
            if rodadas:
                ultima_rodada = rodadas[-1]
                vencedores = etapa.rodadas[ultima_rodada].get("vencedores", [])
                if vencedores:
                    campeao = next((e for e in equipes if e.id == vencedores[0]), None)
                    if campeao:
                        print(f"🏆 CAMPEÃO: {campeao.nome.upper()}\n")

        except Exception as e:
            print(f"[ERRO] {e}")

        input("\nPressione ENTER para voltar ao menu...")
    
    def __init__(self):
        # Configuração MySQL
        MYSQL_CONFIG = "mysql://root:@localhost:3306/granpix"
        
        # Inicializar API com MySQL (sempre)
        self.api = APIGranpix(MYSQL_CONFIG)
        
        self.equipe_selecionada = None
    
    def limpar_tela(self):
        """Limpa a tela do terminal"""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def _criar_barra_progresso(self, valor: float, max_valor: float = 100.0, tamanho: int = 25) -> str:
        """Cria uma barra de progresso visual
        
        Args:
            valor: Valor atual
            max_valor: Valor máximo
            tamanho: Tamanho da barra em caracteres
        
        Returns:
            String com a barra formatada
        """
        percentual = min(100, (valor / max_valor) * 100) if max_valor > 0 else 0
        preenchido = int((tamanho * percentual) / 100)
        vazio = tamanho - preenchido
        
        # Cores baseadas no percentual
        if percentual >= 75:
            cor_inicio = "\033[92m"  # Verde
            cor_fim = "\033[0m"
        elif percentual >= 50:
            cor_inicio = "\033[93m"  # Amarelo
            cor_fim = "\033[0m"
        elif percentual >= 25:
            cor_inicio = "\033[91m"  # Vermelho claro
            cor_fim = "\033[0m"
        else:
            cor_inicio = "\033[91m"  # Vermelho
            cor_fim = "\033[0m"
        
        barra = f"{cor_inicio}{'█' * preenchido}{cor_fim}{'░' * vazio}"
        return f"[{barra}] {percentual:.1f}%"
    
    def _exibir_carro_batalha(self, equipe_a, equipe_b):
        """Exibe os dados dos carros de duas equipes antes de uma batalha"""
        print("\n" + "-"*70)
        print("DADOS DOS CARROS")
        print("-"*70)
        
        # Carro da equipe A
        carro_a = equipe_a.carro
        saude_a = carro_a.calcular_condicao_geral()
        
        print(f"\n{equipe_a.nome.upper()}")
        print(f"  Carro: {carro_a.marca} {carro_a.modelo} (#{carro_a.numero_carro})")
        print(f"  Saúde Geral: {self._criar_barra_progresso(saude_a)}")
        print(f"  Motor:       {self._criar_barra_progresso(carro_a.motor.durabilidade_atual, carro_a.motor.durabilidade_maxima)}")
        print(f"  Câmbio:      {self._criar_barra_progresso(carro_a.cambio.durabilidade_atual, carro_a.cambio.durabilidade_maxima)}")
        print(f"  Kit Ângulo:  {self._criar_barra_progresso(carro_a.kit_angulo.durabilidade_atual, carro_a.kit_angulo.durabilidade_maxima)}")
        print(f"  Suspensão:   {self._criar_barra_progresso(carro_a.suspensao.durabilidade_atual, carro_a.suspensao.durabilidade_maxima)}")
        
        # Peças instaladas da equipe A
        if carro_a.pecas_instaladas:
            print(f"  Peças Instaladas:")
            for peca_info in carro_a.pecas_instaladas:
                print(f"    - {peca_info.get('nome', 'Desconhecida')} ({peca_info.get('tipo', 'N/A')})")
        
        # Carro da equipe B
        carro_b = equipe_b.carro
        saude_b = carro_b.calcular_condicao_geral()
        
        print(f"\n{equipe_b.nome.upper()}")
        print(f"  Carro: {carro_b.marca} {carro_b.modelo} (#{carro_b.numero_carro})")
        print(f"  Saúde Geral: {self._criar_barra_progresso(saude_b)}")
        print(f"  Motor:       {self._criar_barra_progresso(carro_b.motor.durabilidade_atual, carro_b.motor.durabilidade_maxima)}")
        print(f"  Câmbio:      {self._criar_barra_progresso(carro_b.cambio.durabilidade_atual, carro_b.cambio.durabilidade_maxima)}")
        print(f"  Kit Ângulo:  {self._criar_barra_progresso(carro_b.kit_angulo.durabilidade_atual, carro_b.kit_angulo.durabilidade_maxima)}")
        print(f"  Suspensão:   {self._criar_barra_progresso(carro_b.suspensao.durabilidade_atual, carro_b.suspensao.durabilidade_maxima)}")
        
        # Peças instaladas da equipe B
        if carro_b.pecas_instaladas:
            print(f"  Peças Instaladas:")
            for peca_info in carro_b.pecas_instaladas:
                print(f"    - {peca_info.get('nome', 'Desconhecida')} ({peca_info.get('tipo', 'N/A')})")
        
        print("-"*70)
    
    def exibir_menu_principal(self):
        """Exibe o menu principal"""
        self.limpar_tela()
        print("\n" + "="*70)
        print("        GRANPIX RACING CHAMPIONSHIP - SISTEMA PRINCIPAL")
        print("="*70)
        print("\n[1] Gerenciar Equipes")
        print("[2] Gerenciar Pilotos")
        print("[3] Realizar Batalhas")
        print("[4] Ver Status de Carros")
        print("[5] Reparar Carros")
        print("[6] Loja de Carros")
        print("[7] Loja de Pecas")
        print("[8] Administrador - Gerenciar Lojas")
        print("[9] Etapa - Competicao")
        print("[10] Ver Relatorios")
        print("[11] Exportar Dados")
        print("[0] Sair")
        print("\n" + "="*70)
    
    def menu_equipes(self):
        """Menu de gerenciamento de equipes"""
        while True:
            self.limpar_tela()
            print("\n[=] GERENCIAR EQUIPES [=]")
            print("\n[1] Criar Equipe")
            print("[2] Listar Equipes")
            print("[3] Ver Detalhes da Equipe")
            print("[4] Apagar Equipe")
            print("[5] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                try:
                    nome = input("Nome da equipe: ").strip()
                    if not nome:
                        print("[ERRO] Nome nao pode ser vazio!")
                    else:
                        try:
                            doricoins = float(input("Doricoins iniciais (padrao 1000): ") or "1000")
                            equipe = self.api.criar_equipe_novo(nome, doricoins)
                            if equipe:
                                print(f"\n[OK] Equipe '{equipe.nome}' criada com sucesso!")
                            else:
                                print("[ERRO] Erro ao criar equipe!")
                        except ValueError:
                            print("[ERRO] Doricoins deve ser um numero!")
                except Exception as e:
                    print(f"[ERRO] {e}")
                input("Pressione ENTER para continuar...")
            
            elif opcao == "2":
                try:
                    equipes = self.api.listar_todas_equipes()
                    print(f"\nTotal de equipes: {len(equipes)}\n")
                    if equipes:
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome} - {eq.doricoins:.2f} doricoins")
                    else:
                        print("Nenhuma equipe cadastrada.")
                except Exception as e:
                    print(f"[ERRO] Erro ao listar equipes: {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "3":
                try:
                    equipes = self.api.listar_todas_equipes()
                    if not equipes:
                        print("[ERRO] Nenhuma equipe cadastrada!")
                    else:
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome}")
                        try:
                            idx = int(input("\nEscolha a equipe: ")) - 1
                            if 0 <= idx < len(equipes):
                                print(self.api.mostrar_relatorio_equipe(equipes[idx].id))
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite um numero valido!")
                except Exception as e:
                    print(f"[ERRO] Erro ao listar equipes: {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "4":
                try:
                    equipes = self.api.listar_todas_equipes()
                    if not equipes:
                        print("[ERRO] Nenhuma equipe cadastrada!")
                    else:
                        print("\n[!] APAGAR EQUIPE - AVISO: Isso removerá a equipe e todos os seus dados!")
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome}")
                        try:
                            idx = int(input("\nEscolha a equipe para apagar: ")) - 1
                            if 0 <= idx < len(equipes):
                                equipe_selecionada = equipes[idx]
                                confirmacao = input(f"\nConfirma apagar '{equipe_selecionada.nome}' e todos os seus dados? (s/n): ").strip().lower()
                                if confirmacao == "s":
                                    if self.api.apagar_equipe(equipe_selecionada.id):
                                        print(f"\n[OK] Equipe '{equipe_selecionada.nome}' foi apagada com sucesso!")
                                    else:
                                        print("[ERRO] Erro ao apagar equipe!")
                                else:
                                    print("[CANCELADO] Operação cancelada.")
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite um numero valido!")
                except Exception as e:
                    print(f"[ERRO] Erro ao apagar equipe: {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "5":
                break
    
    def menu_pilotos(self):
        """Menu de gerenciamento de pilotos"""
        while True:
            self.limpar_tela()
            print("\n[=] GERENCIAR PILOTOS [=]")
            print("\n[1] Registrar Novo Piloto")
            print("[2] Listar Pilotos de uma Equipe")
            print("[3] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                try:
                    equipes = self.api.listar_todas_equipes()
                    if not equipes:
                        print("[ERRO] Nenhuma equipe cadastrada!")
                    else:
                        print("\nEquipes disponiveis:")
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome}")
                        
                        try:
                            eq_idx = int(input("\nEscolha a equipe: ")) - 1
                            if 0 <= eq_idx < len(equipes):
                                equipe = equipes[eq_idx]
                                nome = input("Nome do piloto: ").strip()
                                if not nome:
                                    print("[ERRO] Nome nao pode ser vazio!")
                                else:
                                    piloto = self.api.registrar_piloto(nome, equipe.id)
                                    print(f"\n[OK] Piloto '{piloto.nome}' registrado com sucesso na equipe '{equipe.nome}'!")
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite um numero valido!")
                except Exception as e:
                    print(f"[ERRO] Erro ao registrar piloto: {e}")
            
            elif opcao == "2":
                try:
                    equipes = self.api.listar_todas_equipes()
                    if not equipes:
                        print("[ERRO] Nenhuma equipe cadastrada!")
                    else:
                        print("\nEquipes disponiveis:")
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome}")
                        try:
                            eq_idx = int(input("\nEscolha a equipe: ")) - 1
                            if 0 <= eq_idx < len(equipes):
                                equipe = equipes[eq_idx]
                                pilotos = self.api.listar_pilotos_equipe(equipe.id)
                                print(f"\nPilotos de {equipe.nome}:")
                                if pilotos:
                                    for p in pilotos:
                                        print(f"  - {p.nome}")
                                else:
                                    print("  Nenhum piloto nesta equipe.")
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite um numero valido!")
                except Exception as e:
                    print(f"[ERRO] Erro ao listar pilotos: {e}")
            
            elif opcao == "3":
                break
            
            input("\nPressione ENTER para continuar...")
    
    def menu_loja_carros(self):
        """Menu de loja de carros"""
        while True:
            self.limpar_tela()
            print(self.api.listar_modelos_carros())
            
            print("[1] Comprar Carro")
            print("[2] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                try:
                    equipes = self.api.listar_todas_equipes()
                    if not equipes:
                        print("[ERRO] Nenhuma equipe cadastrada!")
                    else:
                        print("\nEquipes disponiveis:")
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome} - {eq.doricoins:.2f} doricoins")
                        
                        try:
                            eq_idx = int(input("\nEscolha a equipe: ")) - 1
                            if 0 <= eq_idx < len(equipes):
                                equipe = equipes[eq_idx]
                                
                                # Listar modelos
                                modelos = self.api.loja_carros.listar_modelos()
                                print(f"\nModelos disponiveis:")
                                for i, modelo in enumerate(modelos, 1):
                                    print(f"{i}. {modelo.marca} {modelo.modelo} - {modelo.preco:.2f} doricoins")
                                
                                try:
                                    modelo_idx = int(input("\nEscolha o modelo: ")) - 1
                                    if 0 <= modelo_idx < len(modelos):
                                        modelo = modelos[modelo_idx]
                                        
                                        if equipe.doricoins >= modelo.preco:
                                            if self.api.comprar_carro(equipe.id, modelo.id):
                                                print(f"\n[OK] {modelo.marca} {modelo.modelo} comprado com sucesso!")
                                                print(f"Doricoins restantes: {equipe.doricoins - modelo.preco:.2f}")
                                            else:
                                                print("[ERRO] Erro ao comprar carro!")
                                        else:
                                            print(f"[ERRO] Doricoins insuficientes! Faltam {modelo.preco - equipe.doricoins:.2f}")
                                    else:
                                        print("[ERRO] Modelo invalido!")
                                except ValueError:
                                    print("[ERRO] Digite um numero valido!")
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite um numero valido!")
                except Exception as e:
                    print(f"[ERRO] {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "2":
                break
    
    def menu_admin_loja(self):
        """Menu do administrador para gerenciar a loja de carros"""
        while True:
            self.limpar_tela()
            print("\n[=] ADMINISTRADOR - GERENCIAR LOJA [=]")
            print("\n[1] Listar Carros Cadastrados")
            print("[2] Cadastrar Novo Carro")
            print("[3] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                try:
                    carros = self.api.obter_carros_loja()
                    print("\n" + "="*70)
                    print("                    CARROS CADASTRADOS NA LOJA")
                    print("="*70 + "\n")
                    
                    if not carros:
                        print("Nenhum carro cadastrado ainda.")
                    else:
                        for i, carro in enumerate(carros, 1):
                            print(f"[{i}] {carro.marca} {carro.modelo} (Classe: {carro.classe.upper()})")
                            print(f"    ID: {carro.id}")
                            print(f"    Preco: {carro.preco:.2f} doricoins")
                            print(f"    Descricao: {carro.descricao}")
                            print(f"    Pecas:")
                            print(f"      - Motor: {carro.preco_motor:.2f}")
                            print(f"      - Cambio: {carro.preco_cambio:.2f}")
                            print(f"      - Angulo: {carro.preco_kit_angulo:.2f}")
                            print(f"      - Suspensao: {carro.preco_suspensao:.2f}")
                            print(f"      - Diferencial: {carro.preco_diferencial:.2f}")
                            print()
                except Exception as e:
                    print(f"[ERRO] Erro ao listar carros: {e}")
                input("Pressione ENTER para continuar...")
            
            elif opcao == "2":
                try:
                    self.limpar_tela()
                    print("\n[=] CADASTRAR NOVO CARRO [=]\n")
                    
                    marca = input("Marca do carro: ").strip()
                    modelo = input("Modelo do carro: ").strip()
                    
                    print("\nClasses disponiveis:")
                    print("[1] basico")
                    print("[2] intermediario")
                    print("[3] avancado")
                    print("[4] premium")
                    
                    classe_idx = input("\nEscolha a classe: ").strip()
                    classes = ["basico", "intermediario", "avancado", "premium"]
                    
                    if classe_idx not in ["1", "2", "3", "4"]:
                        print("[ERRO] Classe invalida!")
                    else:
                        classe = classes[int(classe_idx) - 1]
                        
                        preco = float(input("Preco do carro (em doricoins): "))
                        descricao = input("Descricao: ").strip()
                        
                        print("\nPrecos das pecas:")
                        preco_motor = float(input("  Motor: "))
                        preco_cambio = float(input("  Cambio: "))
                        preco_kit_angulo = float(input("  Kit Angulo: "))
                        preco_suspensao = float(input("  Suspensao: "))
                        preco_diferencial = float(input("  Diferencial (opcional, padrao 0): ") or "0")
                        
                        if self.api.cadastrar_carro_loja(
                            marca, modelo, classe, preco, descricao,
                            preco_motor, preco_cambio, preco_kit_angulo,
                            preco_suspensao, preco_diferencial
                        ):
                            print(f"\n[OK] Carro '{marca} {modelo}' cadastrado com sucesso!")
                        else:
                            print("[ERRO] Erro ao cadastrar carro!")
                except ValueError:
                    print("[ERRO] Valores digitados invalidos!")
                except Exception as e:
                    print(f"[ERRO] {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "3":
                break
    
    def _exibir_pecas_por_tipo(self, tipo: str, nome_tipo: str):
        """Exibe pecas de um tipo específico de forma formatada"""
        self.limpar_tela()
        pecas = self.api.obter_pecas_por_tipo(tipo)
        
        print("\n" + "="*70)
        print(f"                    LOJA DE PECAS - {nome_tipo}")
        print("="*70 + "\n")
        
        if not pecas:
            print(f"[ERRO] Nenhuma peca de {nome_tipo} disponível!")
        else:
            for i, peca in enumerate(pecas, 1):
                comp_text = "Universal" if peca.compatibilidade == "universal" else "Especifica"
                
                # Determinar descrição do coeficiente
                if peca.coeficiente_quebra < 0.9:
                    coef_desc = f"RESISTENTE (Coef: {peca.coeficiente_quebra})"
                elif peca.coeficiente_quebra > 1.1:
                    coef_desc = f"FRÁGIL (Coef: {peca.coeficiente_quebra})"
                else:
                    coef_desc = f"PADRÃO (Coef: {peca.coeficiente_quebra})"
                
                print(f"{i}. {peca.nome}")
                print(f"   Preco: {peca.preco:.2f} doricoins")
                print(f"   {peca.descricao}")
                print(f"   Compatibilidade: {comp_text}")
                print(f"   Durabilidade: {coef_desc}\n")
        
        print("="*70)
        input("Pressione ENTER para voltar...")
    
    def menu_loja_pecas(self):
        """Menu de loja de pecas"""
        while True:
            self.limpar_tela()
            print("\n" + "="*70)
            print("                    LOJA DE PECAS")
            print("="*70)
            print("\n[1] Comprar Peca")
            print("[2] Ver Todas as Pecas")
            print("[3] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                try:
                    equipes = self.api.listar_todas_equipes()
                    if not equipes:
                        print("[ERRO] Nenhuma equipe cadastrada!")
                    else:
                        print("\nEquipes disponiveis:")
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome} - {eq.doricoins:.2f} doricoins")
                        
                        try:
                            eq_idx = int(input("\nEscolha a equipe: ")) - 1
                            if 0 <= eq_idx < len(equipes):
                                equipe = equipes[eq_idx]
                                
                                # Listar tipos
                                tipos = ["motor", "cambio", "suspensao", "kit_angulo", "diferencial"]
                                tipo_nomes = ["Motor", "Cambio", "Suspensao", "Kit Angulo", "Diferencial"]
                                
                                print("\nTipos de pecas:")
                                for i, tipo_nome in enumerate(tipo_nomes, 1):
                                    print(f"{i}. {tipo_nome}")
                                
                                try:
                                    tipo_idx = int(input("\nEscolha o tipo: ")) - 1
                                    if 0 <= tipo_idx < len(tipos):
                                        tipo = tipos[tipo_idx]
                                        
                                        pecas = self.api.obter_pecas_por_tipo(tipo)
                                        if not pecas:
                                            print("[ERRO] Nenhuma peca deste tipo disponível!")
                                        else:
                                            print(f"\nPecas de {tipo_nomes[tipo_idx]}:")
                                            for i, peca in enumerate(pecas, 1):
                                                compat = "Universal" if peca.compatibilidade == "universal" else "Especifica"
                                                print(f"{i}. {peca.nome} - {peca.preco:.2f} doricoins ({compat})")
                                            
                                            try:
                                                peca_idx = int(input("\nEscolha a peca: ")) - 1
                                                if 0 <= peca_idx < len(pecas):
                                                    peca = pecas[peca_idx]
                                                    
                                                    if equipe.doricoins >= peca.preco:
                                                        if self.api.comprar_peca(equipe.id, peca.id):
                                                            print(f"\n[OK] {peca.nome} comprada com sucesso!")
                                                            print(f"Doricoins restantes: {equipe.doricoins - peca.preco:.2f}")
                                                        else:
                                                            print("[ERRO] Erro ao comprar peca!")
                                                    else:
                                                        print(f"[ERRO] Doricoins insuficientes! Faltam {peca.preco - equipe.doricoins:.2f}")
                                                else:
                                                    print("[ERRO] Peca invalida!")
                                            except ValueError:
                                                print("[ERRO] Digite um numero valido!")
                                    else:
                                        print("[ERRO] Tipo invalido!")
                                except ValueError:
                                    print("[ERRO] Digite um numero valido!")
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite um numero valido!")
                except Exception as e:
                    print(f"[ERRO] {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "2":
                # Menu para visualizar pecas por tipo
                while True:
                    self.limpar_tela()
                    print("\n" + "="*70)
                    print("                    LOJA DE PECAS - CATALOGO")
                    print("="*70)
                    print("\n[1] Motores")
                    print("[2] Transmissoes/Cambios")
                    print("[3] Suspensoes")
                    print("[4] Kits de Angulo")
                    print("[5] Ver Todas as Pecas")
                    print("[6] Voltar")
                    
                    cat_opcao = input("\nEscolha uma categoria: ").strip()
                    
                    if cat_opcao == "1":
                        try:
                            self._exibir_pecas_por_tipo("motor", "MOTORES")
                        except Exception as e:
                            print(f"[ERRO] {e}")
                            input("Pressione ENTER para continuar...")
                    elif cat_opcao == "2":
                        try:
                            self._exibir_pecas_por_tipo("cambio", "TRANSMISSOES")
                        except Exception as e:
                            print(f"[ERRO] {e}")
                            input("Pressione ENTER para continuar...")
                    elif cat_opcao == "3":
                        try:
                            self._exibir_pecas_por_tipo("suspensao", "SUSPENSOES")
                        except Exception as e:
                            print(f"[ERRO] {e}")
                            input("Pressione ENTER para continuar...")
                    elif cat_opcao == "4":
                        try:
                            self._exibir_pecas_por_tipo("kit_angulo", "KITS DE ANGULO")
                        except Exception as e:
                            print(f"[ERRO] {e}")
                            input("Pressione ENTER para continuar...")
                    elif cat_opcao == "5":
                        self.limpar_tela()
                        print(self.api.loja_pecas.listar_pecas_formatado())
                        input("Pressione ENTER para voltar...")
                    elif cat_opcao == "6":
                        break
                    else:
                        print("[ERRO] Opcao invalida!")
            
            elif opcao == "3":
                break
    
    def menu_admin(self):
        """Menu do administrador para gerenciar lojas"""
        while True:
            self.limpar_tela()
            print("\n[=] ADMINISTRADOR - GERENCIAR LOJAS [=]")
            print("\n[1] Gerenciar Loja de Carros")
            print("[2] Gerenciar Loja de Pecas")
            print("[3] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                self.menu_admin_loja_carros()
            elif opcao == "2":
                self.menu_admin_loja_pecas()
            elif opcao == "3":
                break
    
    def menu_admin_loja_carros(self):
        """Menu do administrador para gerenciar carros"""
        while True:
            self.limpar_tela()
            print("\n[=] ADMINISTRADOR - LOJA DE CARROS [=]")
            print("\n[1] Listar Carros Cadastrados")
            print("[2] Cadastrar Novo Carro")
            print("[3] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                try:
                    carros = self.api.obter_carros_loja()
                    print("\n" + "="*70)
                    print("                    CARROS CADASTRADOS NA LOJA")
                    print("="*70 + "\n")
                    
                    if not carros:
                        print("Nenhum carro cadastrado ainda.")
                    else:
                        for i, carro in enumerate(carros, 1):
                            print(f"[{i}] {carro.marca} {carro.modelo} (Classe: {carro.classe.upper()})")
                            print(f"    ID: {carro.id}")
                            print(f"    Preco: {carro.preco:.2f} doricoins")
                            print(f"    Descricao: {carro.descricao}")
                            print(f"    Pecas:")
                            print(f"      - Motor: {carro.preco_motor:.2f}")
                            print(f"      - Cambio: {carro.preco_cambio:.2f}")
                            print(f"      - Angulo: {carro.preco_kit_angulo:.2f}")
                            print(f"      - Suspensao: {carro.preco_suspensao:.2f}")
                            print(f"      - Diferencial: {carro.preco_diferencial:.2f}")
                            print()
                except Exception as e:
                    print(f"[ERRO] Erro ao listar carros: {e}")
                input("Pressione ENTER para continuar...")
            
            elif opcao == "2":
                try:
                    self.limpar_tela()
                    print("\n[=] CADASTRAR NOVO CARRO [=]\n")
                    
                    marca = input("Marca do carro: ").strip()
                    modelo = input("Modelo do carro: ").strip()
                    
                    print("\nClasses disponiveis:")
                    print("[1] basico")
                    print("[2] intermediario")
                    print("[3] avancado")
                    print("[4] premium")
                    
                    classe_idx = input("\nEscolha a classe: ").strip()
                    classes = ["basico", "intermediario", "avancado", "premium"]
                    
                    if classe_idx not in ["1", "2", "3", "4"]:
                        print("[ERRO] Classe invalida!")
                    else:
                        classe = classes[int(classe_idx) - 1]
                        
                        preco = float(input("Preco do carro (em doricoins): "))
                        descricao = input("Descricao: ").strip()
                        
                        print("\nPrecos das pecas:")
                        preco_motor = float(input("  Motor: "))
                        preco_cambio = float(input("  Cambio: "))
                        preco_kit_angulo = float(input("  Kit Angulo: "))
                        preco_suspensao = float(input("  Suspensao: "))
                        preco_diferencial = float(input("  Diferencial (opcional, padrao 0): ") or "0")
                        
                        if self.api.cadastrar_carro_loja(
                            marca, modelo, classe, preco, descricao,
                            preco_motor, preco_cambio, preco_kit_angulo,
                            preco_suspensao, preco_diferencial
                        ):
                            print(f"\n[OK] Carro '{marca} {modelo}' cadastrado com sucesso!")
                        else:
                            print("[ERRO] Erro ao cadastrar carro!")
                except ValueError:
                    print("[ERRO] Valores digitados invalidos!")
                except Exception as e:
                    print(f"[ERRO] {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "3":
                break
    
    def menu_admin_loja_pecas(self):
        """Menu do administrador para gerenciar pecas"""
        while True:
            self.limpar_tela()
            print("\n[=] ADMINISTRADOR - LOJA DE PECAS [=]")
            print("\n[1] Listar Pecas Cadastradas")
            print("[2] Cadastrar Nova Peca")
            print("[3] Voltar")
            
            opcao = input("\nEscolha uma opcao: ").strip()
            
            if opcao == "1":
                try:
                    print(self.api.loja_pecas.listar_pecas_formatado())
                except Exception as e:
                    print(f"[ERRO] Erro ao listar pecas: {e}")
                input("Pressione ENTER para continuar...")
            
            elif opcao == "2":
                try:
                    self.limpar_tela()
                    print("\n[=] CADASTRAR NOVA PECA [=]\n")
                    
                    nome = input("Nome da peca: ").strip()
                    
                    print("\nTipos de peca:")
                    print("[1] motor")
                    print("[2] cambio")
                    print("[3] suspensao")
                    print("[4] kit_angulo")
                    print("[5] diferencial")
                    
                    tipo_idx = input("\nEscolha o tipo: ").strip()
                    tipos = ["motor", "cambio", "suspensao", "kit_angulo", "diferencial"]
                    
                    if tipo_idx not in ["1", "2", "3", "4", "5"]:
                        print("[ERRO] Tipo invalido!")
                    else:
                        tipo = tipos[int(tipo_idx) - 1]
                        preco = float(input("Preco da peca (em doricoins): "))
                        descricao = input("Descricao: ").strip()
                        
                        print("\nCompatibilidade:")
                        print("[1] Universal (funciona em qualquer carro)")
                        print("[2] Especifica (para carros específicos)")
                        
                        compat_idx = input("\nEscolha: ").strip()
                        
                        if compat_idx == "1":
                            compatibilidade = "universal"
                        elif compat_idx == "2":
                            compatibilidade = input("Digite IDs dos carros (separados por virgula): ").strip()
                        else:
                            print("[ERRO] Opcao invalida!")
                            continue
                        
                        durabilidade = float(input("Durabilidade (padrao 100): ") or "100")
                        
                        coeficiente_quebra = float(input("Coeficiente de quebra (padrao 1.0, ex: 0.5 = 50% menos desgaste, 1.5 = 50% mais desgaste): ") or "1.0")
                        
                        if self.api.cadastrar_peca_loja(
                            nome, tipo, preco, descricao, compatibilidade, durabilidade, coeficiente_quebra
                        ):
                            print(f"\n[OK] Peca '{nome}' cadastrada com sucesso!")
                        else:
                            print("[ERRO] Erro ao cadastrar peca!")
                except ValueError:
                    print("[ERRO] Valores digitados invalidos!")
                except Exception as e:
                    print(f"[ERRO] {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "3":
                break
    
    def executar(self):
        """Executa o loop principal do menu"""
        while True:
            self.exibir_menu_principal()
            opcao = input("Escolha uma opcao: ").strip()
            
            if opcao == "1":
                self.menu_equipes()
            elif opcao == "2":
                self.menu_pilotos()
            elif opcao == "3":
                self.limpar_tela()
                try:
                    equipes = self.api.listar_todas_equipes()
                    pilotos = []
                    for eq in equipes:
                        pilotos.extend(self.api.listar_pilotos_equipe(eq.id))
                    
                    if len(pilotos) < 2:
                        print("[ERRO] Necessario pelo menos 2 pilotos para uma batalha!")
                    else:
                        print("\nPilotos disponiveis:")
                        for i, p in enumerate(pilotos, 1):
                            print(f"{i}. {p.nome}")
                        
                        try:
                            p1_idx = int(input("\nPiloto A: ")) - 1
                            p2_idx = int(input("Piloto B: ")) - 1
                            
                            if 0 <= p1_idx < len(pilotos) and 0 <= p2_idx < len(pilotos) and p1_idx != p2_idx:
                                batalha = self.api.registrar_batalha(pilotos[p1_idx].id, pilotos[p2_idx].id)
                                if batalha:
                                    print(self.api.obter_relatorio_batalha(batalha))
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite numeros validos!")
                except Exception as e:
                    print(f"[ERRO] Erro ao realizar batalha: {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "4":
                self.limpar_tela()
                try:
                    equipes = self.api.listar_todas_equipes()
                    if not equipes:
                        print("[ERRO] Nenhuma equipe cadastrada!")
                    else:
                        print("\nEquipes com carros:")
                        for i, eq in enumerate(equipes, 1):
                            print(f"{i}. {eq.nome} - Carro: {eq.carro.marca} {eq.carro.modelo}")
                        
                        try:
                            idx = int(input("\nEscolha a equipe: ")) - 1
                            if 0 <= idx < len(equipes):
                                print(self.api.relatorio_carro_completo(equipes[idx].carro.id))
                            else:
                                print("[ERRO] Opcao invalida!")
                        except ValueError:
                            print("[ERRO] Digite um numero valido!")
                except Exception as e:
                    print(f"[ERRO] Erro ao listar equipes: {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "5":
                self.limpar_tela()
                print("[INFO] REPARAR CARROS (em desenvolvimento)")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "6":
                self.menu_loja_carros()
            
            elif opcao == "7":
                self.menu_loja_pecas()
            
            elif opcao == "8":
                self.menu_admin()
            
            elif opcao == "9":
                self.menu_etapa()
            
            elif opcao == "10":
                self.limpar_tela()
                try:
                    print(self.api.relatorio_geral())
                except Exception as e:
                    print(f"[ERRO] Erro ao gerar relatorio: {e}")
                input("\nPressione ENTER para continuar...")
            
            elif opcao == "11":
                while True:
                    self.limpar_tela()
                    print("\n[=] EXPORTAR DADOS [=]")
                    print(f"\nStatus: {self.api.obter_status_exportacao()}\n")
                    print("[1] Exportar Equipes para Excel")
                    print("[2] Exportar Equipe Específica para Excel")
                    print("[3] Exportar Backup JSON")
                    print("[4] ⚙️ Configurações de OneDrive")
                    print("[5] Voltar")
                    
                    opcao_export = input("\nEscolha uma opcao: ").strip()
                    
                    if opcao_export == "1":
                        try:
                            arquivos = self.api.exportar_todas_equipes_excel()
                            if arquivos:
                                input("\nPressione ENTER para continuar...")
                            else:
                                input("\nPressione ENTER para continuar...")
                        except Exception as e:
                            print(f"[ERRO] Erro ao exportar equipes: {e}")
                            input("Pressione ENTER para continuar...")
                    
                    elif opcao_export == "2":
                        try:
                            equipes = self.api.listar_todas_equipes()
                            if not equipes:
                                print("[ERRO] Nenhuma equipe cadastrada!")
                            else:
                                for i, eq in enumerate(equipes, 1):
                                    print(f"{i}. {eq.nome}")
                                try:
                                    idx = int(input("\nEscolha a equipe: ")) - 1
                                    if 0 <= idx < len(equipes):
                                        self.api.exportar_equipe_excel(equipes[idx].id)
                                    else:
                                        print("[ERRO] Opcao invalida!")
                                except ValueError:
                                    print("[ERRO] Digite um numero valido!")
                            input("Pressione ENTER para continuar...")
                        except Exception as e:
                            print(f"[ERRO] Erro ao exportar equipe: {e}")
                            input("Pressione ENTER para continuar...")
                    
                    elif opcao_export == "3":
                        try:
                            self.api.exportar_dados()
                            print("\n[OK] Dados exportados para data/backup.json")
                        except Exception as e:
                            print(f"[ERRO] Erro ao exportar dados: {e}")
                        input("Pressione ENTER para continuar...")
                    
                    elif opcao_export == "4":
                        self.limpar_tela()
                        print("\n[=] CONFIGURAÇÕES - ONEDRIVE [=]")
                        print("\n[1] Ativar OneDrive (Sincronização com nuvem)")
                        print("[2] Desativar OneDrive (Usar pasta local)")
                        print("[3] Voltar")
                        
                        opcao_onedrive = input("\nEscolha uma opcao: ").strip()
                        
                        if opcao_onedrive == "1":
                            try:
                                if self.api.ativar_exportacao_onedrive():
                                    print("\n✅ OneDrive ativado com sucesso!")
                                    print("📁 Os arquivos Excel agora sincronizarão com a nuvem em tempo real.")
                                else:
                                    print("\n❌ OneDrive não foi encontrado.")
                                    print("📌 Certifique-se de que o OneDrive está instalado e sincronizado.")
                            except Exception as e:
                                print(f"[ERRO] Erro ao ativar OneDrive: {e}")
                            input("\nPressione ENTER para continuar...")
                        
                        elif opcao_onedrive == "2":
                            try:
                                self.api.desativar_exportacao_onedrive()
                                print("\n✅ OneDrive desativado!")
                                print("📁 Os arquivos Excel serão salvos na pasta local.")
                            except Exception as e:
                                print(f"[ERRO] Erro ao desativar OneDrive: {e}")
                            input("Pressione ENTER para continuar...")
                    
                    elif opcao_export == "5":
                        break
                    
                    else:
                        print("[ERRO] Opcao invalida!")
                        input("Pressione ENTER para continuar...")
            
            elif opcao == "0":
                print("\nAte logo!")
                break


if __name__ == "__main__":
    menu = MenuPrincipal()
    menu.executar()
