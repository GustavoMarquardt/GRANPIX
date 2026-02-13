#!/usr/bin/env python3
"""Debug da série de equipes"""

import sys
import os

# Importar a configuração que já tem os imports corretos
exec(open('app.py').read(), globals())

db = Database()
api = API()

print("=" * 60)
print("TESTE DE DEBUG - SÉRIE DE EQUIPES")
print("=" * 60)

# Listar todas as equipes
print("\n1. Carregando todas as equipes:")
equipes = api.listar_todas_equipes()
for eq in equipes:
    print(f"   - {eq.nome} | ID: {eq.id} | Série: {getattr(eq, 'serie', 'NÃO DEFINIDA')}")

print("\n2. Verificando dados no banco:")
conn = db._get_conn()
cursor = conn.cursor()
cursor.execute("SELECT id, nome, serie FROM equipes")
rows = cursor.fetchall()
for row in rows:
    print(f"   - {row[1]} | ID: {row[0]} | Série: {row[2]}")
conn.close()

print("\n3. Criando equipe de teste com série B:")
equipe_teste = api.criar_equipe_novo(
    nome="Test Serie B",
    doricoins_iniciais=50000,
    senha="test123",
    serie="B"
)
print(f"   Equipe criada: {equipe_teste.nome}")
print(f"   Serie no objeto: {getattr(equipe_teste, 'serie', 'NÃO DEFINIDA')}")

print("\n4. Verificando no banco:")
cursor = conn.cursor()
conn = db._get_conn()
cursor.execute("SELECT id, nome, serie FROM equipes WHERE id = %s", (equipe_teste.id,))
row = cursor.fetchone()
if row:
    print(f"   - {row[1]} | ID: {row[0]} | Série no banco: {row[2]}")
else:
    print("   ERRO: Equipe não encontrada no banco!")
conn.close()

print("\n5. Carregando a equipe de volta:")
equipe_carregada = api.obter_info_equipe(equipe_teste.id)
print(f"   Equipe carregada: {equipe_carregada.nome}")
print(f"   Serie carregada: {getattr(equipe_carregada, 'serie', 'NÃO DEFINIDA')}")

print("\n" + "=" * 60)
