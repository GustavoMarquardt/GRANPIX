import sqlite3
from werkzeug.security import generate_password_hash

def add_team():
    db_path = "data/granpix.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Dados da equipe
        equipe_id = "team123"
        nome = "Equipe Teste"
        senha = generate_password_hash("123456")

        # Inserir equipe
        cursor.execute(
            "INSERT INTO equipes (id, nome, senha) VALUES (?, ?, ?)",
            (equipe_id, nome, senha)
        )
        conn.commit()

        print(f"Equipe '{nome}' adicionada com sucesso!")

    except Exception as e:
        print(f"Erro ao adicionar equipe: {e}")

    finally:
        conn.close()

if __name__ == "__main__":
    add_team()