import mysql.connector
import sys

def run_migration():
    try:
        # Conectar ao banco
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='granpix'
        )
        cursor = conn.cursor()

        print("Adicionando status 'batalhas' ao ENUM da tabela etapas...")

        # Modificar o ENUM para incluir 'batalhas'
        cursor.execute("""
            ALTER TABLE etapas
            MODIFY COLUMN status ENUM('agendada', 'em_andamento', 'batalhas', 'finalizada') DEFAULT 'agendada'
        """)

        conn.commit()
        print("✅ Migration executada com sucesso!")
        print("Status possíveis da etapa: agendada, em_andamento, batalhas, finalizada")

    except Exception as e:
        print(f"❌ Erro na migration: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()