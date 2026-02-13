import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# ID do carro TESÃO que está em repouso
carro_id = 'd5aaedcf-aacc-4f40-86ee-5a529a4f32af'

print("=" * 80)
print("SINCRONIZANDO PEÇAS DO CARRO TESÃO")
print("=" * 80)

# 1. Verificar estado da tabela carros
print("\n[CARROS] Estado atual:")
cursor.execute('''
    SELECT id, apelido, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id
    FROM carros WHERE id = %s
''', (carro_id,))

carro = cursor.fetchone()
if carro:
    carro_id_db, apelido, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id = carro
    print(f"  Apelido: {apelido}")
    print(f"  Motor ID: {motor_id}")
    print(f"  Câmbio ID: {cambio_id}")
    print(f"  Suspensão ID: {suspensao_id}")
    print(f"  Kit Ângulo ID: {kit_angulo_id}")
    print(f"  Diferencial ID: {diferencial_id}")

# 2. Verificar peças instaladas (instalado = 1)
print("\n[PECAS] Peças com instalado = 1:")
cursor.execute('''
    SELECT id, nome, tipo, carro_id, instalado
    FROM pecas WHERE carro_id = %s AND instalado = 1
''', (carro_id,))

pecas_instaladas = cursor.fetchall()
if pecas_instaladas:
    for peca_id, nome, tipo, carro_id_peca, instalado in pecas_instaladas:
        print(f"  - {nome} (tipo: {tipo}, id: {peca_id}, instalado: {instalado})")
else:
    print("  Nenhuma peça instalada encontrada")

# 3. Verificar peças soltas (carro_id = NULL, instalado = 0)
print("\n[ARMAZÉM] Peças no armazém desse carro (se existirem):")
cursor.execute('''
    SELECT id, nome, tipo, carro_id, instalado
    FROM pecas WHERE carro_id IS NULL AND instalado = 0
    LIMIT 5
''')

pecas_armazem = cursor.fetchall()
if pecas_armazem:
    for peca_id, nome, tipo, carro_id_peca, instalado in pecas_armazem:
        print(f"  - {nome} (tipo: {tipo}, id: {peca_id})")
else:
    print("  Nenhuma peça encontrada")

# 4. Sincronizar: Se há peças instaladas mas motor_id é NULL, atualizar a tabela carros
print("\n[SINCRONIZAÇÃO]")
if pecas_instaladas:
    print("Encontradas peças instaladas na tabela pecas!")
    print("Atualizando colunas da tabela carros...")
    
    # Mapear tipos de peças para colunas
    tipo_map = {
        'motor': 'motor_id',
        'cambio': 'cambio_id',
        'suspensao': 'suspensao_id',
        'kit_angulo': 'kit_angulo_id',
        'diferencial': 'diferencial_id'
    }
    
    # Para cada tipo de peça, buscar a peca_loja_id
    for peca_id, nome, tipo, _, _ in pecas_instaladas:
        cursor.execute('SELECT peca_loja_id FROM pecas WHERE id = %s', (peca_id,))
        peca_row = cursor.fetchone()
        
        if peca_row:
            peca_loja_id = peca_row[0]
            coluna = tipo_map.get(tipo)
            
            if coluna:
                print(f"  Atualizando {coluna} = {peca_loja_id}")
                cursor.execute(f'UPDATE carros SET {coluna} = %s WHERE id = %s', (peca_loja_id, carro_id))
else:
    print("Nenhuma peça instalada encontrada na tabela pecas.")
    print("As colunas motor_id, cambio_id, etc. devem estar NULL.")
    print("✓ Tudo sincronizado!")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("SINCRONIZAÇÃO COMPLETA")
print("=" * 80)
