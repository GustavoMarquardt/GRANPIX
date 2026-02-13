from src.database import DatabaseManager

db = DatabaseManager()
conn = db._get_conn()
cursor = conn.cursor()

print("\n=== ESTRUTURA DA TABELA solicitacoes_pecas ===\n")
cursor.execute('DESCRIBE solicitacoes_pecas')
rows = cursor.fetchall()
for r in rows:
    print(f'{r[0]:20} | {r[1]:30} | NULL={str(r[2]):3}')

print("\n=== DADOS ATUAIS NA TABELA ===\n")
cursor.execute('SELECT id, equipe_id, peca_id, carro_id, status FROM solicitacoes_pecas LIMIT 3')
rows = cursor.fetchall()
for r in rows:
    print(f'ID: {r[0][:8]}... | equipe: {r[1][:8]}... | peca: {r[2]} | carro: {r[3]} | status: {r[4]}')

conn.close()
print("\nDone!")
