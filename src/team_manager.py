"""
Sistema de gerenciamento de equipes, pilotos e economia (doricoins)
"""
import uuid
from typing import List, Optional, Dict
from .models import Equipe, Piloto, Carro, Peca, TipoDiferencial
from .database import DatabaseManager
from werkzeug.security import generate_password_hash


class GerenciadorEquipes:
    """Gerencia as equipes, pilotos e operações de doricoins"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        # NÃO usar cache em memória - tudo vem do banco de dados
        # self.equipes: Dict[str, Equipe] = {}
        # self.pilotos: Dict[str, Piloto] = {}
        # self.carros: Dict[str, Carro] = {}
    
    # ============ GERENCIAMENTO DE EQUIPES ============
    
    def _carregar_equipes_banco(self):
        """Método descontinuado - agora tudo vem direto do banco de dados"""
        pass  # Não usar cache em memória
    
    def criar_equipe(self, nome: str, doricoins_iniciais: float = 1000.0, senha: str = None, serie: str = 'A') -> Equipe:
        """Cria uma nova equipe SEM carro padrão (garagem vazia)"""
        # Verificar se já existe equipe com esse nome
        equipes_existentes = self.listar_equipes()
        for e in equipes_existentes:
            if e.nome == nome:
                return e
        
        # Senha padrão é "123456" se não informada
        if senha is None:
            senha = "123456"
        
        # Hash da senha ANTES de salvar
        senha_hash = generate_password_hash(senha)
        
        # Validar série
        if serie not in ['A', 'B']:
            serie = 'A'  # Padrão se inválida
        
        # Criar equipe SEM carro padrão (garagem vazia)
        equipe = Equipe(
            id=str(uuid.uuid4()),
            nome=nome,
            carro=None,  # Sem carro padrão
            carros=[],   # Lista vazia
            doricoins=doricoins_iniciais,
            senha=senha_hash  # Usar senha hasheada
        )
        # Definir série
        equipe.serie = serie
        
        # Salvar APENAS no banco de dados - não usar cache em memória
        self.db.salvar_equipe(equipe)
        return equipe
    
    def obter_equipe(self, equipe_id: str) -> Optional[Equipe]:
        """Obtém uma equipe pelo ID diretamente do banco de dados"""
        return self.db.carregar_equipe(equipe_id)
    
    def listar_equipes(self) -> List[Equipe]:
        """Lista todas as equipes - sempre do banco de dados"""
        # Carregar APENAS do banco de dados
        equipes_db = self.db.carregar_todas_equipes()
        # Retornar apenas dados do banco
        return equipes_db
    
    def deletar_equipe(self, equipe_id: str) -> bool:
        """Deleta uma equipe"""
        # Deletar apenas do banco de dados
        return self.db.deletar_equipe(equipe_id)
    
    def apagar_equipe(self, equipe_id: str) -> bool:
        """Apaga uma equipe do gerenciador"""
        # Deletar apenas do banco de dados
        return self.db.deletar_equipe(equipe_id)
    
    # ============ GERENCIAMENTO DE PILOTOS ============
    
    def criar_piloto(self, nome: str, equipe_id: str) -> Piloto:
        """Cria um novo piloto (usa o carro da equipe)"""
        piloto = Piloto(
            id=str(uuid.uuid4()),
            nome=nome,
            equipe_id=equipe_id
        )
        
        self.pilotos[piloto.id] = piloto
        
        # Adicionar piloto à equipe
        equipe = self.obter_equipe(equipe_id)
        if equipe:
            equipe.adicionar_piloto(piloto)
            self.db.salvar_equipe(equipe)
        
        self.db.salvar_piloto(piloto)
        return piloto
    
    def obter_piloto(self, piloto_id: str) -> Optional[Piloto]:
        """Obtém um piloto pelo ID"""
        return self.pilotos.get(piloto_id)
    
    def listar_pilotos_equipe(self, equipe_id: str) -> List[Piloto]:
        """Lista todos os pilotos de uma equipe"""
        return [p for p in self.pilotos.values() if p.equipe_id == equipe_id]
    
    # ============ GERENCIAMENTO DE CARROS E PEÇAS ============
    
    def criar_carro(self, numero: int, marca: str, modelo: str) -> Carro:
        """Cria um novo carro com as peças padrão"""
        # Criar peças padrão com coeficiente de quebra
        motor = Peca(
            id=str(uuid.uuid4()),
            nome="Motor Turbo",
            tipo="motor",
            durabilidade_maxima=100.0,
            preco=500.0,
            coeficiente_quebra=1.2  # Motores são mais sensíveis
        )
        
        cambio = Peca(
            id=str(uuid.uuid4()),
            nome="Câmbio Manual",
            tipo="cambio",
            durabilidade_maxima=100.0,
            preco=300.0,
            coeficiente_quebra=1.1  # Câmbios sofrem desgaste moderado
        )
        
        kit_angulo = Peca(
            id=str(uuid.uuid4()),
            nome="Kit Ângulo 3 Graus",
            tipo="kit_angulo",
            durabilidade_maxima=100.0,
            preco=400.0,
            coeficiente_quebra=0.9  # Kit de ângulo resiste bem
        )
        
        suspensao = Peca(
            id=str(uuid.uuid4()),
            nome="Suspensão Coilover",
            tipo="suspensao",
            durabilidade_maxima=100.0,
            preco=350.0,
            coeficiente_quebra=1.0  # Suspensão tem desgaste padrão
        )
        
        # Criar 2 diferenciais por padrão
        diferenciais = [
            Peca(
                id=str(uuid.uuid4()),
                nome="Diferencial 1.5 - Traseiro",
                tipo="diferencial",
                durabilidade_maxima=100.0,
                preco=200.0,
                coeficiente_quebra=0.85  # Diferenciais sofrem pouco desgaste
            ),
            Peca(
                id=str(uuid.uuid4()),
                nome="Diferencial 1.3 - Dianteiro",
                tipo="diferencial",
                durabilidade_maxima=100.0,
                preco=200.0,
                coeficiente_quebra=0.85  # Diferenciais sofrem pouco desgaste
            )
        ]
        
        carro = Carro(
            id=str(uuid.uuid4()),
            numero_carro=numero,
            marca=marca,
            modelo=modelo,
            motor=motor,
            cambio=cambio,
            kit_angulo=kit_angulo,
            suspensao=suspensao,
            diferenciais=diferenciais
        )
        
        self.carros[carro.id] = carro
        self.db.salvar_carro(carro)
        return carro
    
    def obter_carro(self, carro_id: str) -> Optional[Carro]:
        """Obtém um carro pelo ID"""
        return self.carros.get(carro_id)
    
    def adicionar_diferencial(self, carro_id: str, nome: str, 
                             relacao: str) -> bool:
        """Adiciona um diferencial extra ao carro"""
        carro = self.obter_carro(carro_id)
        if not carro:
            return False
        
        diferencial = Peca(
            id=str(uuid.uuid4()),
            nome=f"Diferencial {relacao} - {nome}",
            tipo="diferencial",
            durabilidade_maxima=100.0,
            preco=200.0
        )
        
        carro.diferenciais.append(diferencial)
        self.db.salvar_carro(carro)
        return True
    
    # ============ SISTEMA DE DORICOINS ============
    
    def adicionar_doricoins(self, equipe_id: str, quantidade: float) -> bool:
        """Adiciona doricoins a uma equipe"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe:
            return False
        
        equipe.adicionar_doricoins(quantidade)
        self.db.salvar_equipe(equipe)
        return True
    
    def gastar_doricoins(self, equipe_id: str, quantidade: float) -> bool:
        """Gasta doricoins de uma equipe"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe:
            return False
        
        if equipe.gastar_doricoins(quantidade):
            self.db.salvar_equipe(equipe)
            return True
        
        return False
    
    def reparar_carro_equipe(self, equipe_id: str, 
                           percentual: float = 100.0) -> bool:
        """Repara o carro de uma equipe"""
        equipe = self.obter_equipe(equipe_id)
        
        if not equipe:
            return False
        
        if equipe.reparar_carro_equipe(percentual):
            self.db.salvar_equipe(equipe)
            self.db.salvar_carro(equipe.carro)
            return True
        
        return False
    
    # ============ RELATÓRIOS ============
    
    def relatorio_equipe(self, equipe_id: str) -> str:
        """Gera um relatório da equipe"""
        equipe = self.obter_equipe(equipe_id)
        if not equipe:
            return "Equipe não encontrada!"
        
        pilotos = self.listar_pilotos_equipe(equipe_id)
        
        relatorio = f"""
╔══════════════════════════════════════════════╗
║     RELATÓRIO DA EQUIPE: {equipe.nome:26}║
╠══════════════════════════════════════════════╣
║ Doricoins Disponíveis: {equipe.doricoins:23.2f} 💰
║ Total de Batalhas: {len(equipe.historico_batalhas):27}
╠══════════════════════════════════════════════╣
║ PILOTOS ({len(pilotos)}):
"""
        
        for piloto in pilotos:
            relatorio += f"""║
║ 👤 {piloto.nome}
║    Vitórias: {piloto.vitoria} | Derrotas: {piloto.derrotas} | Empates: {piloto.empates}
"""
        
        relatorio += "╚══════════════════════════════════════════════╝\n"
        return relatorio
    
    def relatorio_pilotos_ranking(self) -> str:
        """Gera um ranking dos pilotos"""
        pilotos_ordenados = sorted(
            self.pilotos.values(),
            key=lambda p: (p.vitoria - p.derrotas) / max(1, p.vitoria + p.derrotas + p.empates),
            reverse=True
        )
        
        relatorio = "\n╔══════════════════════════════════════════════╗\n"
        relatorio += "║        RANKING GERAL DE PILOTOS             ║\n"
        relatorio += "╠══════════════════════════════════════════════╣\n"
        
        for i, piloto in enumerate(pilotos_ordenados[:10], 1):
            total = piloto.vitoria + piloto.derrotas + piloto.empates
            taxa_vitoria = (piloto.vitoria / total * 100) if total > 0 else 0
            relatorio += f"║ {i:2d}. {piloto.nome:20} - {taxa_vitoria:5.1f}% V:E {piloto.vitoria}:{piloto.equipe_id[:4]} ║\n"
        
        relatorio += "╚══════════════════════════════════════════════╝\n"
        return relatorio
