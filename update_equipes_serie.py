import sys
sys.path.insert(0, '.')

from src.database import DatabaseManager

db = DatabaseManager('mysql://root:@localhost:3306/granpix')

conn = db._get_conn()
cursor = conn.cursor()

print("[DB] Atualizando séries das equipes...")

# Verificar se há equipes sem série
cursor.execute("SELECT id, nome, serie FROM equipes WHERE serie IS NULL OR serie = ''")
equipes_sem_serie = cursor.fetchall()

if equipes_sem_serie:
    print(f"[DB] Encontradas {len(equipes_sem_serie)} equipes sem série")
    for eq in equipes_sem_serie:
        equipe_id, nome, serie = eq
        print(f"  - {nome}: série atual = {serie}")
        # Definir como série A por padrão
        cursor.execute("UPDATE equipes SET serie = 'A' WHERE id = %s", (equipe_id,))
    conn.commit()
    print(f"[DB] {len(equipes_sem_serie)} equipes atualizadas para série A")
else:
    print("[DB] Todas as equipes têm série definida")

# Listar todas as equipes com suas séries
print("\n[DB] Equipes cadastradas:")
cursor.execute("SELECT nome, serie FROM equipes ORDER BY nome")
for row in cursor.fetchall():
    print(f"  - {row[0]}: série {row[1]}")

cursor.close()
conn.close()
print("\n[DB] Atualização concluída!")
