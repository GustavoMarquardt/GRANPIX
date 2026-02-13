import sys
import os
sys.path.insert(0, '.')

from src.database import DatabaseManager
import uuid

db = DatabaseManager('mysql://root:@localhost:3306/granpix')

print("\n" + "="*60)
print("TESTE - FILTRO DE SÉRIE EM PONTUACOES_CAMPEONATO")
print("="*60)

# 1. Limpar dados antigos e definir série nas equipes
print("\n[1] Preparando dados das equipes...")
conn = db._get_conn()
cursor = conn.cursor()

# Verificar equipes e suas séries
cursor.execute('SELECT id, nome, serie FROM equipes')
equipes = cursor.fetchall()
print(f"Total de equipes: {len(equipes)}")
for eq in equipes:
    print(f"  - {eq[1]}: série {eq[2]}")

cursor.close()
conn.close()

# 2. Criar campeonato de série A
print("\n[2] Criando campeonato da série A...")
campeonato_a_id = str(uuid.uuid4())
sucesso = db.criar_campeonato(
    campeonato_a_id,
    nome="Campeonato Série A - Filtro Test",
    descricao="Teste de filtro por série",
    serie="A",
    numero_etapas=5
)

if sucesso:
    print(f"✓ Campeonato série A criado com ID: {campeonato_a_id}")
    
    # Verificar quantas equipes foram adicionadas
    pontuacoes_a = db.obter_pontuacoes_campeonato(campeonato_a_id)
    print(f"  - Equipes adicionadas (série A): {len(pontuacoes_a)}")
    for pont in pontuacoes_a:
        print(f"    • {pont['equipe_nome']}")
else:
    print("✗ Erro ao criar campeonato série A")

# 3. Criar campeonato de série B
print("\n[3] Criando campeonato da série B...")
campeonato_b_id = str(uuid.uuid4())
sucesso_b = db.criar_campeonato(
    campeonato_b_id,
    nome="Campeonato Série B - Filtro Test",
    descricao="Teste de filtro por série",
    serie="B",
    numero_etapas=5
)

if sucesso_b:
    print(f"✓ Campeonato série B criado com ID: {campeonato_b_id}")
    
    # Verificar quantas equipes foram adicionadas
    pontuacoes_b = db.obter_pontuacoes_campeonato(campeonato_b_id)
    print(f"  - Equipes adicionadas (série B): {len(pontuacoes_b)}")
    for pont in pontuacoes_b:
        print(f"    • {pont['equipe_nome']}")
else:
    print("✗ Erro ao criar campeonato série B")

print("\n" + "="*60)
print("TESTE CONCLUÍDO!")
if sucesso and sucesso_b:
    print("✓ Ambos campeonatos criados com filtro de série")
else:
    print("⚠ Verifique os dados acima")
print("="*60 + "\n")
