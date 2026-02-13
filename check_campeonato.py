import sys
sys.path.insert(0, '.')
from src.database import DatabaseManager

db = DatabaseManager('mysql://root:@localhost:3306/granpix')
conn = db._get_conn()
cursor = conn.cursor(dictionary=True)

# Checar o campeonato mais recente
cursor.execute('SELECT * FROM campeonatos ORDER BY data_criacao DESC LIMIT 1')
campeonato = cursor.fetchone()
if campeonato:
    print(f'Campeonato encontrado: {campeonato["id"]} - {campeonato["nome"]}')
else:
    print('Nenhum campeonato encontrado')

# Checar se existe alguma pontuação
cursor.execute('SELECT COUNT(*) as cnt FROM pontuacoes_campeonato')
count_result = cursor.fetchone()
print(f'Registros em pontuacoes_campeonato: {count_result["cnt"]}')

cursor.close()
conn.close()
