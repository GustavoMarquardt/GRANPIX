"""
Sistema de Loja de Pecas
Oferece diferentes tipos de pecas para compra pelas equipes
Todas as peças são carregadas do banco de dados com UUIDs.
"""
from dataclasses import dataclass
from typing import List, Optional
import uuid


@dataclass
class PecaLoja:
    """Peca disponível na loja"""
    id: str  # UUID
    nome: str
    tipo: str  # motor, cambio, kit_angulo, suspensao, diferencial
    preco: float
    descricao: str
    compatibilidade: str  # "universal" ou UUID de modelo_loja
    durabilidade: float = 100.0
    coeficiente_quebra: float = 1.0  # Multiplicador de desgaste da peça
    imagem: Optional[str] = None  # Base64 encoded image


class LojaPecas:
    """Gerencia a loja de pecas disponíveis"""
    
    def __init__(self, db=None):
        self.db = db
        self.pecas = []
        
        # Carregar peças do banco de dados
        if self.db:
            pecas_db = self.db.carregar_pecas_loja()
            if pecas_db:
                self.pecas = pecas_db
    
    def listar_pecas(self) -> List[PecaLoja]:
        """Retorna lista de todas as pecas disponíveis"""
        return self.pecas
    
    def obter_peca(self, peca_id: str) -> Optional[PecaLoja]:
        """Obtém uma peca específica"""
        for peca in self.pecas:
            if peca.id == peca_id:
                return peca
        return None
    
    def adicionar_peca(self, nome: str, tipo: str, preco: float,
                      descricao: str, compatibilidade: str,
                      durabilidade: float = 100.0, coeficiente_quebra: float = 1.0) -> PecaLoja:
        """Adiciona uma nova peça à loja com coeficiente de quebra.
        Permite várias peças com mesmo nome/tipo desde que tenham id diferente (ex.: compatibilidade ou preço diferente).
        """
        import uuid

        peca_id = str(uuid.uuid4())
        
        nova_peca = PecaLoja(
            id=peca_id,
            nome=nome,
            tipo=tipo,
            preco=preco,
            descricao=descricao,
            compatibilidade=compatibilidade,
            durabilidade=durabilidade,
            coeficiente_quebra=coeficiente_quebra
        )
        
        self.pecas.append(nova_peca)
        return nova_peca
    
    def editar_peca(self, peca_id: str, nome: str = None, tipo: str = None, 
                   preco: float = None, durabilidade: float = None, 
                   coeficiente_quebra: float = None, compatibilidade: str = None) -> bool:
        """Edita uma peça existente"""
        for peca in self.pecas:
            if peca.id == peca_id:
                if nome is not None:
                    peca.nome = nome
                if tipo is not None:
                    peca.tipo = tipo
                if preco is not None:
                    peca.preco = preco
                if durabilidade is not None:
                    peca.durabilidade = durabilidade
                if coeficiente_quebra is not None:
                    peca.coeficiente_quebra = coeficiente_quebra
                if compatibilidade is not None:
                    peca.compatibilidade = compatibilidade
                return True
        return False
    
    def deletar_peca(self, peca_id: str) -> bool:
        """Deleta uma peça"""
        for i, peca in enumerate(self.pecas):
            if peca.id == peca_id:
                self.pecas.pop(i)
                return True
        return False
    
    def listar_pecas_por_tipo(self, tipo: str) -> List[PecaLoja]:
        """Retorna pecas de um tipo específico"""
        return [p for p in self.pecas if p.tipo == tipo]
    
    def listar_pecas_compativel_carro(self, modelo_carro_id: str) -> List[PecaLoja]:
        """Retorna pecas compatíveis com um carro específico"""
        compativel = []
        for peca in self.pecas:
            if peca.compatibilidade == "universal":
                compativel.append(peca)
            else:
                # Suporta múltiplos IDs separados por vírgula, sem espaços
                ids_compat = [id.strip() for id in str(peca.compatibilidade).split(",") if id.strip()]
                if modelo_carro_id in ids_compat:
                    compativel.append(peca)
        return compativel
    
    def listar_pecas_formatado(self) -> str:
        """Retorna lista de pecas formatada para exibir"""
        resultado = "\n" + "="*70 + "\n"
        resultado += "                    LOJA DE PECAS\n"
        resultado += "="*70 + "\n"
        
        tipos = {}
        for peca in self.pecas:
            if peca.tipo not in tipos:
                tipos[peca.tipo] = []
            tipos[peca.tipo].append(peca)
        
        tipo_nomes = {
            "motor": "MOTORES",
            "cambio": "TRANSMISSOES",
            "suspensao": "SUSPENSOES",
            "kit_angulo": "KITS DE ANGULO",
            "diferencial": "DIFERENCIAIS"
        }
        
        for tipo, nome_display in tipo_nomes.items():
            if tipo in tipos:
                resultado += f"\n[{nome_display}]\n"
                for i, peca in enumerate(tipos[tipo], 1):
                    if peca.compatibilidade == "universal":
                        comp_text = "Universal"
                    else:
                        # Buscar detalhes do modelo no banco de dados
                        modelo = self.db.carregar_modelo_por_id(peca.compatibilidade)
                        if modelo:
                            comp_text = f"{modelo.marca} {modelo.modelo} ({modelo.classe})"
                        else:
                            comp_text = "Desconhecida"

                    # Determinar descrição do coeficiente
                    if peca.coeficiente_quebra < 0.9:
                        coef_desc = f"RESISTENTE (Coef: {peca.coeficiente_quebra})"
                    elif peca.coeficiente_quebra > 1.1:
                        coef_desc = f"FRÁGIL (Coef: {peca.coeficiente_quebra})"
                    else:
                        coef_desc = f"PADRÃO (Coef: {peca.coeficiente_quebra})"

                    resultado += f"  {i}. {peca.nome}\n"
                    resultado += f"     Preco: {peca.preco:.2f} doricoins\n"
                    resultado += f"     {peca.descricao}\n"
                    resultado += f"     Compatibilidade: {comp_text}\n"
                    resultado += f"     Durabilidade: {coef_desc}\n"
        
        resultado += "\n" + "="*70 + "\n"
        return resultado
