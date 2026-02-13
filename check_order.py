import mysql.connector

# Conectar ao banco
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='granpix'
)
cursor = conn.cursor(dictionary=True)

# Ver dados das equipes na etapa
cursor.execute('''
    SELECT en.equipe_id, en.nota_linha, en.nota_angulo, en.nota_estilo,
           (COALESCE(en.nota_linha, 0) + COALESCE(en.nota_angulo, 0) + COALESCE(en.nota_estilo, 0)) as total
    FROM etapa_notas en
    WHERE en.etapa_id = '9ade8576-dec0-43d4-a056-8d2adf5924bc'
    ORDER BY total DESC, en.nota_linha DESC
''')

equipes = cursor.fetchall()
print('Equipes ordenadas por pontuação (total desc, linha desc):')
for i, eq in enumerate(equipes, 1):
    equipe_id = eq['equipe_id']
    nota_linha = eq['nota_linha'] or 0
    total = eq['total']
    print(f'{i:2d}. {equipe_id} | Linha: {nota_linha:2d} | Total: {total:2d}')

cursor.close()
conn.close()