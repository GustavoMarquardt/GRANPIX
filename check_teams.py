import sqlite3

def check_teams():
    db_path = "data/granpix.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, nome, senha FROM equipes")
        rows = cursor.fetchall()

        print("\nEquipes no banco de dados:")
        for row in rows:
            print(f"ID: {row[0]}, Nome: {row[1]}, Senha: {row[2]}")

    except Exception as e:
        print(f"Erro ao consultar o banco de dados: {e}")

    finally:
        conn.close()

if __name__ == "__main__":
    check_teams()