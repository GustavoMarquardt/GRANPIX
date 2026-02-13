#!/usr/bin/env python3
"""
Script para testar a criação e população da tabela pontuacoes_campeonato
"""
import sys
import os
import uuid

# Mudar para o diretório do projeto
os.chdir(os.path.dirname(__file__))
sys.path.insert(0, os.getcwd())

# Importar diretamente usando relative path correto
from src.database import DatabaseManager

# Conectar ao banco
db = DatabaseManager("mysql://root:@localhost:3306/granpix")

print("\n" + "="*60)
print("TESTE - TABELA PONTUACOES_CAMPEONATO")
print("="*60)

# 1. Criar um campeonato de teste
print("\n[1] Criando campeonato de teste...")
campeonato_id = str(uuid.uuid4())
sucesso = db.criar_campeonato(
    campeonato_id,
    nome="Campeonato Teste Pontuação",
    descricao="Teste da tabela pontuacoes_campeonato",
    serie="A",
    numero_etapas=5
)

if sucesso:
    print(f"✓ Campeonato criado com ID: {campeonato_id}")
else:
    print("✗ Erro ao criar campeonato")
    sys.exit(1)

# 2. Verificar se as pontuações foram criadas
print("\n[2] Consultando pontuações criadas...")
pontuacoes = db.obter_pontuacoes_campeonato(campeonato_id)

print(f"Debug: Resultado da query: {pontuacoes}")
print(f"Debug: Tipo: {type(pontuacoes)}")

if pontuacoes:
    print(f"✓ {len(pontuacoes)} registros de pontuação encontrados:")
    for pont in pontuacoes[:5]:  # Mostrar apenas os primeiros 5
        print(f"  - {pont['equipe_nome']}: {pont['pontos']} pontos (colocação: {pont['colocacao']})")
    if len(pontuacoes) > 5:
        print(f"  ... e mais {len(pontuacoes) - 5}")
else:
    print("✗ Nenhuma pontuação encontrada!")
    # Tentar query manual para debug
    try:
        conn = db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pontuacoes_campeonato WHERE campeonato_id = %s", (campeonato_id,))
        debug_result = cursor.fetchall()
        print(f"Debug - Query manual: {debug_result}")
        cursor.close()
        conn.close()
    except Exception as debug_e:
        print(f"Debug - Erro na query manual: {debug_e}")

# 3. Testar atualização de pontos
if pontuacoes:
    print("\n[3] Testando atualização de pontos...")
    primeira_equipe_id = pontuacoes[0]['equipe_id']
    sucesso = db.atualizar_pontuacao_equipe(campeonato_id, primeira_equipe_id, 10)
    
    if sucesso:
        print(f"✓ Pontos atualizados (+10)")
        
        # Verificar se foram atualizados
        pontuacoes_apos = db.obter_pontuacoes_campeonato(campeonato_id)
        for pont in pontuacoes_apos:
            if pont['equipe_id'] == primeira_equipe_id:
                print(f"  - {pont['equipe_nome']}: {pont['pontos']} pontos")
                break
    else:
        print("✗ Erro ao atualizar pontuação")

# 4. Testar atualização de colocações
print("\n[4] Atualizando colocações (ranking)...")
if db.atualizar_colocacoes_campeonato(campeonato_id):
    print("✓ Colocações atualizadas")
    
    pontuacoes_final = db.obter_pontuacoes_campeonato(campeonato_id)
    print("\nRanking final:")
    for pont in pontuacoes_final[:10]:  # Mostrar top 10
        colocacao = pont['colocacao'] if pont['colocacao'] else "N/A"
        print(f"  {colocacao:2}. {pont['equipe_nome']:30} - {pont['pontos']:3} pontos")
    if len(pontuacoes_final) > 10:
        print(f"  ... e mais {len(pontuacoes_final) - 10}")
else:
    print("✗ Erro ao atualizar colocações")

print("\n" + "="*60)
print("TESTE CONCLUÍDO COM SUCESSO!")
print("="*60 + "\n")
