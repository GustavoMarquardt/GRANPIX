import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# Verificar a estrutura da tabela
cursor.execute('DESCRIBE solicitacoes_pecas;')
colunas = cursor.fetchall()

print('ESTRUTURA DA TABELA solicitacoes_pecas:')
for col in colunas:
    print(f'  {col[0]}: {col[1]}')

# Verificar dados existentes
cursor.execute('SELECT * FROM solicitacoes_pecas LIMIT 1;')
resultado = cursor.fetchone()
if resultado:
    print(f'\nDados exemplo: {resultado}')
else:
    print('\nNenhuma solicitação de peça encontrada')

conn.close()
