"""
Sistema de Loja de Carros
Oferece diferentes modelos de carros para compra pelas equipes
Todos os carros são carregados do banco de dados com UUIDs.
Suporta múltiplas variações por modelo (diferentes combinações de motor/câmbio/peças)
"""
from dataclasses import dataclass
from typing import List, Optional
import uuid


@dataclass
class VariacaoCarro:
    """Variação de um modelo de carro (combinação específica de peças/motor)"""
    id: str  # UUID
    modelo_carro_loja_id: str  # FK para ModeloCarro
    motor_id: Optional[str] = None
    cambio_id: Optional[str] = None
    suspensao_id: Optional[str] = None  # ID da peça de suspensão
    kit_angulo_id: Optional[str] = None  # ID do kit ângulo
    diferencial_id: Optional[str] = None  # ID do diferencial
    valor: float = 0.0  # Preço/valor da variação


@dataclass
class ModeloCarro:
    """Modelo de carro disponível na loja"""
    id: str  # UUID
    marca: str
    modelo: str
    classe: str  # basico, intermediario, avancado, premium
    preco: float
    descricao: str
    imagem: Optional[str] = None  # Base64 encoded image
    variacoes: List[VariacaoCarro] = None  # Variações deste modelo
    
    def __post_init__(self):
        if self.variacoes is None:
            self.variacoes = []


class LojaCarros:
    """Gerencia a loja de carros disponíveis"""
    
    def __init__(self, db=None):
        self.db = db
        self.modelos = []
        
        # Carregar modelos do banco de dados
        if self.db:
            modelos_db = self.db.carregar_modelos_loja()
            if modelos_db:
                self.modelos = modelos_db
            else:
                # Se não há modelos no banco, não adiciona modelos padrão
                print("[LOJA CARROS] Nenhum modelo encontrado no banco. Use a API para adicionar modelos.")
    
    def listar_modelos(self) -> List[ModeloCarro]:
        """Retorna lista de todos os modelos disponíveis"""
        return self.modelos
    
    def obter_modelo(self, modelo_id: str) -> ModeloCarro:
        """Obtém um modelo específico"""
        for modelo in self.modelos:
            if modelo.id == modelo_id:
                return modelo
        return None
    
    def adicionar_modelo(self, marca: str, modelo: str, classe: str, preco: float,
                        descricao: str, motor_id: str = None, cambio_id: str = None,
                        suspensao_id: str = None, kit_angulo_id: str = None,
                        diferencial_id: str = None) -> ModeloCarro:
        """Adiciona um novo modelo de carro à loja com uma variação V1 vazia (sem peças)"""
        import uuid
        modelo_id = str(uuid.uuid4())
        variacao_id = str(uuid.uuid4())
        
        # Criar variação V1 vazia (SEM motor, câmbio, suspensão, kit ângulo, diferencial)
        # Os parâmetros motor_id, cambio_id, etc. são ignorados
        variacao = VariacaoCarro(
            id=variacao_id,
            modelo_carro_loja_id=modelo_id,
            motor_id=None,
            cambio_id=None,
            suspensao_id=None,
            kit_angulo_id=None,
            diferencial_id=None
        )
        
        novo_modelo = ModeloCarro(
            id=modelo_id,
            marca=marca,
            modelo=modelo,
            classe=classe,
            preco=preco,
            descricao=descricao,
            variacoes=[variacao]
        )
        
        self.modelos.append(novo_modelo)
        return novo_modelo
    
    def editar_modelo(self, modelo_id: str, marca: str = None, modelo: str = None,
                     preco: float = None) -> bool:
        """Edita um modelo de carro existente"""
        for carro in self.modelos:
            if carro.id == modelo_id:
                if marca is not None:
                    carro.marca = marca
                if modelo is not None:
                    carro.modelo = modelo
                if preco is not None:
                    carro.preco = preco
                return True
        return False
    
    def adicionar_variacao(self, modelo_id: str, motor_id: str = None, cambio_id: str = None,
                          suspensao_id: str = None, kit_angulo_id: str = None, 
                          diferencial_id: str = None, valor: float = 0.0) -> Optional[VariacaoCarro]:
        """Adiciona uma nova variação a um modelo existente"""
        for carro in self.modelos:
            if carro.id == modelo_id:
                variacao_id = str(uuid.uuid4())
                variacao = VariacaoCarro(
                    id=variacao_id,
                    modelo_carro_loja_id=modelo_id,
                    motor_id=motor_id,
                    cambio_id=cambio_id,
                    suspensao_id=suspensao_id,
                    kit_angulo_id=kit_angulo_id,
                    diferencial_id=diferencial_id,
                    valor=valor
                )
                carro.variacoes.append(variacao)
                return variacao
        return None
    
    def deletar_modelo(self, modelo_id: str) -> bool:
        """Deleta um modelo de carro"""
        for i, carro in enumerate(self.modelos):
            if carro.id == modelo_id:
                self.modelos.pop(i)
                return True
        return False
    
    def listar_modelos_formatado(self) -> str:
        """Retorna lista de modelos formatada para exibir"""
        resultado = "\n" + "="*70 + "\n"
        resultado += "                    LOJA DE CARROS\n"
        resultado += "="*70 + "\n"
        
        for i, modelo in enumerate(self.modelos, 1):
            resultado += f"\n[{i}] {modelo.marca} {modelo.modelo} (Classe: {modelo.classe.upper()})\n"
            resultado += f"    Preço: {modelo.preco:.2f} doricoins\n"
            resultado += f"    {modelo.descricao}\n"
            resultado += f"    Variações disponíveis: {len(modelo.variacoes)}\n"
            
            # Mostrar informações das variações
            for j, variacao in enumerate(modelo.variacoes, 1):
                pecas_info = []
                
                if variacao.motor_id:
                    motor_peca = self.db.buscar_peca_loja_por_id(variacao.motor_id) if self.db else None
                    if motor_peca:
                        pecas_info.append(f"Motor: {motor_peca.nome}")
                    else:
                        pecas_info.append("Motor: Padrão")
                else:
                    pecas_info.append("Motor: Padrão")
                
                if variacao.cambio_id:
                    cambio_peca = self.db.buscar_peca_loja_por_id(variacao.cambio_id) if self.db else None
                    if cambio_peca:
                        pecas_info.append(f"Câmbio: {cambio_peca.nome}")
                    else:
                        pecas_info.append("Câmbio: Padrão")
                else:
                    pecas_info.append("Câmbio: Padrão")
                
                resultado += f"      [{j}] {' | '.join(pecas_info)}\n"
        
        resultado += "\n" + "="*70 + "\n"
        return resultado
