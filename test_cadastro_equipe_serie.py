import sys
sys.path.insert(0, '.')

from src.database import DatabaseManager
import uuid

db = DatabaseManager('mysql://root:@localhost:3306/granpix')

print("\n" + "="*60)
print("TESTE - CADASTRO DE EQUIPE COM SÉRIE")
print("="*60)

# 1. Criar uma equipe série A via database.py diretamente
print("\n[1] Criando equipe série A...")
from src.models import Equipe

equipe_a = Equipe(
    id=str(uuid.uuid4()),
    nome=f"Equipe Teste A {uuid.uuid4().hex[:8]}",
    doricoins=10000,
    senha="hash123",
    carro=None,
    carros=[]
)
equipe_a.serie = "A"

if db.salvar_equipe(equipe_a):
    print(f"✓ Equipe série A salva: {equipe_a.nome} (ID: {equipe_a.id})")
else:
    print("✗ Erro ao salvar equipe série A")

# 2. Criar uma equipe série B
print("\n[2] Criando equipe série B...")
equipe_b = Equipe(
    id=str(uuid.uuid4()),
    nome=f"Equipe Teste B {uuid.uuid4().hex[:8]}",
    doricoins=10000,
    senha="hash123",
    carro=None,
    carros=[]
)
equipe_b.serie = "B"

if db.salvar_equipe(equipe_b):
    print(f"✓ Equipe série B salva: {equipe_b.nome} (ID: {equipe_b.id})")
else:
    print("✗ Erro ao salvar equipe série B")

# 3. Carregar as equipes e verificar se a série foi salva
print("\n[3] Carregando equipes e verificando série...")
equipe_a_carregada = db.carregar_equipe(equipe_a.id)
equipe_b_carregada = db.carregar_equipe(equipe_b.id)

if equipe_a_carregada:
    print(f"✓ Equipe A carregada: {equipe_a_carregada.nome}, Série: {equipe_a_carregada.serie}")
    if equipe_a_carregada.serie == "A":
        print("  ✓ Série salva corretamente!")
    else:
        print(f"  ✗ Série incorreta! Esperado: A, Obtido: {equipe_a_carregada.serie}")
else:
    print("✗ Erro ao carregar equipe A")

if equipe_b_carregada:
    print(f"✓ Equipe B carregada: {equipe_b_carregada.nome}, Série: {equipe_b_carregada.serie}")
    if equipe_b_carregada.serie == "B":
        print("  ✓ Série salva corretamente!")
    else:
        print(f"  ✗ Série incorreta! Esperado: B, Obtido: {equipe_b_carregada.serie}")
else:
    print("✗ Erro ao carregar equipe B")

# 4. Listar todas as equipes e verificar série
print("\n[4] Listando todas as equipes...")
todas_equipes = db.carregar_todas_equipes()
print(f"Total de equipes: {len(todas_equipes)}")
for eq in todas_equipes:
    print(f"  - {eq.nome}: série {eq.serie}")

print("\n" + "="*60)
print("TESTE CONCLUÍDO!")
print("="*60 + "\n")
