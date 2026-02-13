import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# Ver estrutura da tabela pecas
cursor.execute('''DESCRIBE pecas''')
cols = cursor.fetchall()
print('ESTRUTURA DA TABELA PECAS:')
for col in cols:
    print(f'  {col[0]}: {col[1]} (NULL: {col[2]}, KEY: {col[3]}, DEFAULT: {col[4]}, EXTRA: {col[5]})')
print()

# Buscar o motor ap 2.0 para ver todos os registros
cursor.execute('''SELECT id, carro_id, nome FROM pecas WHERE nome = 'ap 2.0' ''')
pecas = cursor.fetchall()
print(f'PEÇAS COM NOME ap 2.0: {len(pecas)} registros')
for peca_id, carro_id, nome in pecas:
    print(f'  ID: {peca_id}, Carro: {carro_id}, Nome: {nome}')
print()

# Buscar o motor 2jz para ver todos os registros
cursor.execute('''SELECT id, carro_id, nome FROM pecas WHERE nome = '2jz' ''')
pecas = cursor.fetchall()
print(f'PEÇAS COM NOME 2jz: {len(pecas)} registros')
for peca_id, carro_id, nome in pecas:
    print(f'  ID: {peca_id}, Carro: {carro_id}, Nome: {nome}')

# Buscar todas as peças com peca_loja_id = 5429d6c3-52cf-48aa-a2c7-0f22d27563bb (ap 2.0)
print()
cursor.execute('''SELECT id, carro_id, nome FROM pecas WHERE peca_loja_id = '5429d6c3-52cf-48aa-a2c7-0f22d27563bb' ''')
pecas = cursor.fetchall()
print(f'PEÇAS COM peca_loja_id = AP 2.0 ID: {len(pecas)} registros')
for peca_id, carro_id, nome in pecas:
    print(f'  ID: {peca_id}, Carro: {carro_id}, Nome: {nome}')

conn.close()
